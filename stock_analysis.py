import yfinance as yf
import pandas as pd
import numpy as np

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_kd(high, low, close, window=9):
    low_min = low.rolling(window=window).min()
    high_max = high.rolling(window=window).max()
    rsv = 100 * (close - low_min) / (high_max - low_min)
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    return k, d

def calculate_macd(close):
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist

def calculate_atr(high, low, close, window=14):
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(window=window).mean()

def calculate_adx(high, low, close, window=14):
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)
    
    tr = calculate_atr(high, low, close, window=window)
    
    plus_di = 100 * (plus_dm.rolling(window=window).mean() / tr)
    minus_di = 100 * (minus_dm.rolling(window=window).mean() / tr)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=window).mean()
    return adx

def detect_divergence(price, indicator, window=10):
    if len(price) < window: return "None"
    
    msg = []
    try:
        if (price.iloc[-1] > price.iloc[-window]) and (indicator.iloc[-1] < indicator.iloc[-window]):
             msg.append("Top Divergence (Bearish)")
        if (price.iloc[-1] < price.iloc[-window]) and (indicator.iloc[-1] > indicator.iloc[-window]):
             msg.append("Bottom Divergence (Bullish)")
    except:
        pass
        
    return ", ".join(msg) if msg else "None"

def analyze_pattern(open_p, high, low, close):
    """
    Basic Candlestick Pattern Detection
    """
    entity = abs(close - open_p)
    upper_shadow = high - max(close, open_p)
    lower_shadow = min(close, open_p) - low
    total_len = high - low
    
    if total_len == 0: return "十字星 (Doji)"
    
    pat = []
    
    # 1. Entity Color
    if close > open_p:
        pat.append("紅K")
    elif close < open_p:
        pat.append("黑K")
    else:
        pat.append("十字")
        
    # 2. Shadow logic
    if upper_shadow > entity * 2:
        pat.append("長上影線")
    if lower_shadow > entity * 2:
        pat.append("長下影線")
        
    # 3. Specific Patterns
    if entity < total_len * 0.1:
        return "十字星變盤線 (Doji)"
    if (lower_shadow > entity * 2) and (upper_shadow < entity * 0.5):
        return "錘頭/吊人 (Hammer/Hanging Man)"
    if (upper_shadow > entity * 2) and (lower_shadow < entity * 0.5):
        return "流星/倒錘 (Shooting Star)"
        
    return " ".join(pat)

def calculate_pivots(high, low, close):
    """
    Calculates Pivot Points (Classic & CDP) for the NEXT trading day.
    """
    # 1. Classic Pivot Points
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    
    # 2. CDP (Contrarian Operating Logic) - Popular in Taiwan
    # AH = Super High (Pressure), NH = Normal High (Sell), NL = Normal Low (Buy), AL = Super Low (Support)
    cdp = (high + low + 2*close) / 4
    pt = high - low
    ah = cdp + pt
    nh = cdp * 2 - low
    nl = cdp * 2 - high
    al = cdp - pt
    
    return {
        "pivot": pivot, "r1": r1, "s1": s1, "r2": r2, "s2": s2,
        "cdp": cdp, "ah": ah, "nh": nh, "nl": nl, "al": al
    }

def calculate_quant_score(metrics):
    """
    Calculates a 0-10 score based on quantitative factors.
    Weights: Trend(40%), Momentum(30%), Risk/Structure(30%)
    """
    score = 0
    
    # 1. Trend (40%)
    if metrics['ma20'] > metrics['ma60']: score += 2  # Bullish Alignment
    if metrics['close'] > metrics['ma20']: score += 1 # Above Monthly
    if metrics['close'] > metrics['ma60']: score += 1 # Above Quarterly
    
    # 2. Momentum (30%)
    # RSI
    if 50 <= metrics['rsi'] <= 70: score += 1.5   # Healthy Bull
    elif 40 <= metrics['rsi'] < 50: score += 0.5  # Weak
    elif metrics['rsi'] > 80: score -= 0.5        # Overbought Danger
    
    # MACD
    if metrics['macd_hist'] > 0 and metrics['macd_hist'] > metrics['macd_hist_prev']: score += 1.5 # Accelerating
    elif metrics['macd_hist'] > 0: score += 1.0 # Positive
    
    # 3. Structure & Volume (30%)
    if metrics['volume'] > metrics['mv5']: score += 1 # Volume Support
    if metrics['bb_width'] > 10: score += 1  # Volatility Expansion (Trend)
    if "紅K" in metrics['pattern']: score += 1
    elif "黑K" in metrics['pattern']: score -= 1
    
    # Cap at 10, Min at 0
    return max(0, min(10, score))

# Hardcoded mapping for popular stocks to ensure Chinese display
# yfinance often returns English names, this serves as a reliable override.
TW_STOCK_NAMES = {
    "^TWII": "加權指數",
    "2330.TW": "台積電", "2330": "台積電",
    "2317.TW": "鴻海", "2317": "鴻海",
    "2454.TW": "聯發科", "2454": "聯發科",
    "2303.TW": "聯電", "2303": "聯電",
    "2308.TW": "台達電", "2308": "台達電",
    "2881.TW": "富邦金", "2881": "富邦金",
    "2882.TW": "國泰金", "2882": "國泰金",
    "2886.TW": "兆豐金", "2886": "兆豐金",
    "2891.TW": "中信金", "2891": "中信金",
    "1301.TW": "台塑", "1301": "台塑",
    "1303.TW": "南亞", "1303": "南亞",
    "2002.TW": "中鋼", "2002": "中鋼",
    "2603.TW": "長榮", "2603": "長榮",
    "2609.TW": "陽明", "2609": "陽明",
    "2615.TW": "萬海", "2615": "萬海",
    "3008.TW": "大立光", "3008": "大立光",
    "3034.TW": "聯詠", "3034": "聯詠",
    "3037.TW": "欣興", "3037": "欣興",
    "3045.TW": "台灣大", "3045": "台灣大",
    "2412.TW": "中華電", "2412": "中華電",
    "2382.TW": "廣達", "2382": "廣達",
    "3231.TW": "緯創", "3231": "緯創",
    "2357.TW": "華碩", "2357": "華碩",
    "6669.TW": "緯穎", "6669": "緯穎",
    "2376.TW": "技嘉", "2376": "技嘉",
    "2383.TW": "台光電", "2383": "台光電",
    "NVDA": "輝達 (NVIDIA)",
    "AAPL": "蘋果 (Apple)",
    "TSM": "台積電ADR",
    "AMD": "超微 (AMD)",
    "INTC": "英特爾 (Intel)"
}

def analyze_stock(ticker):
    """
    Fetches data and calculates indicators.
    Returns: (DataFrame, Dictionary of latest metrics)
    """
    try:
        # Fetch data
        df = yf.download(ticker, period="1y", progress=False) 
        if df.empty: return None, None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 1. Lookup Name in Dictionary First (Fast & Reliable)
        stock_name = TW_STOCK_NAMES.get(ticker, ticker)
        
        # 2. If not found, try yfinance info (Fallback, slower)
        if stock_name == ticker:
            try:
                t = yf.Ticker(ticker)
                info = t.info 
                stock_name = info.get('longName') or info.get('shortName') or ticker
            except:
                pass
            
        # Indicators
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        df['MA5'] = close.rolling(window=5).mean()
        df['MA20'] = close.rolling(window=20).mean()
        df['MA60'] = close.rolling(window=60).mean()
        
        df['BB_Mid'] = df['MA20']
        df['BB_Std'] = close.rolling(window=20).std()
        df['BB_Up'] = df['BB_Mid'] + 2 * df['BB_Std']
        df['BB_Low'] = df['BB_Mid'] - 2 * df['BB_Std']
        
        df['K'], df['D'] = calculate_kd(high, low, close)
        df['RSI'] = calculate_rsi(close)
        df['MACD'], df['Signal'], df['Hist'] = calculate_macd(close)
        df['ATR'] = calculate_atr(high, low, close)
        df['ADX'] = calculate_adx(high, low, close)
        
        # Volume Indicators
        vol = df['Volume']
        df['MV5'] = vol.rolling(window=5).mean()
        df['MV20'] = vol.rolling(window=20).mean()

        # Latest Metrics
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        metrics = {
            "date": latest.name.date(),
            "symbol": ticker,
            "name": stock_name,
            # OHLC
            "open": latest['Open'],
            "high": latest['High'],
            "low": latest['Low'],
            "close": latest['Close'],
            "prev_close": prev['Close'],
            
            # Volume
            "volume": latest['Volume'],
            "mv5": latest['MV5'],
            "mv20": latest['MV20'],
            "vol_change": (latest['Volume'] - prev['Volume']) / prev['Volume'] * 100 if prev['Volume'] > 0 else 0,
            
        # Trend
            "ma5": latest['MA5'],
            "ma20": latest['MA20'],
            "ma60": latest['MA60'],
            "bias_ma20": (latest['Close'] - latest['MA20']) / latest['MA20'] * 100,
            "bias_ma60": (latest['Close'] - latest['MA60']) / latest['MA60'] * 100,
            "trend": "Bullish" if latest['MA20'] > latest['MA60'] else "Bearish",
            
            # Oscillators
            "k": latest['K'],
            "d": latest['D'],
            "rsi": latest['RSI'],
            "macd": latest['MACD'],
            "macd_hist": latest['Hist'],
            # Need previous hist for momentum score
            "macd_hist_prev": df.iloc[-2]['Hist'], 
            
            # Risk
            "bb_up": latest['BB_Up'],
            "bb_low": latest['BB_Low'],
            "bb_width": (latest['BB_Up'] - latest['BB_Low']) / latest['BB_Mid'] * 100, 
            "atr": latest['ATR'],
            "adx": latest['ADX'],
            "stop_loss": latest['Close'] - 2 * latest['ATR'],
            "div_rsi": detect_divergence(close, df['RSI']),
            "div_macd": detect_divergence(close, df['Hist']),
            
            # Pattern
            "pattern": analyze_pattern(latest['Open'], latest['High'], latest['Low'], latest['Close'])
        }
        
        # Add Extended Metrics (Score & Pivots)
        metrics['pivots'] = calculate_pivots(latest['High'], latest['Low'], latest['Close'])
        metrics['score'] = calculate_quant_score(metrics)
        
        return df, metrics

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None, None

if __name__ == "__main__":
    # Test run
    df, metrics = analyze_stock("2330.TW")
    if metrics:
        print(f"Analysis for {metrics['date']}: Close={metrics['close']:.2f}, Trend={metrics['trend']}")
