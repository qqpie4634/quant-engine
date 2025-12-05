import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import stock_analysis
import importlib

# Force reload of backend module to ensure latest code changes (e.g. new metrics) are applied
importlib.reload(stock_analysis)

st.set_page_config(page_title="機構級量化分析引擎", layout="wide", page_icon="🏛️")

# Custom CSS for "Institutional" look
st.markdown("""
<style>
    .big-font { font-size:20px !important; }
    .metric-card { background-color: #0E1117; border: 1px solid #30333D; padding: 20px; border-radius: 10px; }
    .report-box { background-color: #1c1f26; padding: 20px; border-radius: 5px; border-left: 5px solid #4CAF50; }
    .score-box { text-align: center; padding: 10px; border-radius: 10px; margin-bottom: 20px; }
    .bull-score { background-color: rgba(76, 175, 80, 0.2); border: 1px solid #4CAF50; color: #4CAF50; }
    .bear-score { background-color: rgba(244, 67, 54, 0.2); border: 1px solid #f44336; color: #f44336; }
    .neutral-score { background-color: rgba(255, 193, 7, 0.2); border: 1px solid #FFC107; color: #FFC107; }
    
    /* Enhance Tabs Visibility */
    div[data-baseweb="tab-list"] p { font-size: 20px !important; font-weight: bold !important; }
    div[data-baseweb="tab-list"] button { padding: 10px 20px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 機構級量化分析引擎 (Institutional Quant Engine)")
st.markdown("### 數據驅動 (Data-Driven) | 嚴謹邏輯 (Rigorous Logic) | 風險優先 (Risk First)")

# Sidebar
with st.sidebar:
    st.header("⚙️ 參數設定")
    ticker_input = st.text_input("輸入代號 (如 2330, NVDA, 台指期)", value="2330")
    run_btn = st.button("🚀 啟動量化分析", type="primary")
    
    st.divider()
    st.info("💡 貼心小幫手：\n1. 台股直接輸入代號 (如 2330)\n2. 輸入 '台指期' 或 'TX' 可分析大盤")

def process_ticker(input_str):
    """
    Smartly converts user input to yfinance ticker.
    """
    input_str = input_str.strip().upper()
    
    # 1. Futures Mapping (Proxy)
    if input_str in ["TX", "WTX", "台指期", "FUTURES", "TAIEX"]:
        return "^TWII", "台指期 (Proxy: 加權指數)"
        
    # 2. Taiwan Stock Shortcut (4 digits)
    if input_str.isdigit() and len(input_str) == 4:
        # Default assumption: simple ticker input -> likely Taiwan Stock
        return f"{input_str}.TW", f"{input_str}"
        
    # 3. Default
    return input_str, input_str

def generate_rule_based_report(metrics, ticker_display_name):
    """
    Generates a text report based on quantitative metrics.
    """
    # 1. Market Structure Logic
    trend_str = "多頭排列 (Bullish)" if metrics['trend'] == "Bullish" else "空頭/盤整 (Bearish/Sideways)"
    adx_str = "趨勢強勁" if metrics['adx'] > 25 else "趨勢不明/盤整"
    
    # 2. Indicator Logic
    kd_status = "高檔過熱" if metrics['k'] > 80 else "低檔超賣" if metrics['k'] < 20 else "中性"
    macd_status = "多頭掌控" if metrics['macd_hist'] > 0 else "空頭掌控"
    
    # 3. Pivots data
    p = metrics['pivots']
    
    report = f"""
## {ticker_display_name} 自動化量化決策報告
**分析日期:** {metrics['date']}

### 1. 市場結構判定
* **趨勢方向:** **{trend_str}** (MA20 vs MA60)
* **K線型態:** {metrics['pattern']}
* **關鍵乖離:** MA20乖離 {metrics['bias_ma20']:.2f}% | MA60乖離 {metrics['bias_ma60']:.2f}%

### 2. 技術指標掃描
* **動能 (MACD/KD):** {macd_status} (Hist={metrics['macd_hist']:.2f}) | KD狀態: {kd_status} (K={metrics['k']:.2f})
* **強弱 (RSI):** RSI={metrics['rsi']:.2f} (若 <30 超賣, >70 超買)
* **通道狀態:** Bandwidth={metrics['bb_width']:.2f}% ({(lambda w: "壓縮待變" if w < 10 else "正常擴張")(metrics['bb_width'])})

### 3. 🎯 CDP 逆勢操作系統 (明日當沖參考)
| 關鍵點位 | 價格 |戰術意義 |
| :--- | :--- | :--- |
| **AH (最高壓力)** | **{p['ah']:.2f}** | 強力賣點/追價極限 |
| **NH (賣出點)** | {p['nh']:.2f} | 分批獲利了結 |
| **CDP (中軸)** | {p['cdp']:.2f} | 多空分水嶺 |
| **NL (買進點)** | {p['nl']:.2f} | 回檔佈局點 |
| **AL (最低支撐)** | **{p['al']:.2f}** | 強力買點/停損極限 |

### 4. ⚖️ 劇本模擬 (Scenario Analysis)
* ☀️ **樂觀劇本 (Bull Case):** 若帶量突破 **{p['nh']:.2f}**，目標挑戰布林上軌 **{metrics['bb_up']:.2f}**。
* 🌧️ **悲觀劇本 (Bear Case):** 若跌破季線 **{metrics['ma60']:.2f}** 或 AL **{p['al']:.2f}**，下看 ATR 停損位 **{metrics['stop_loss']:.2f}**。
    """
    return report

def generate_ai_prompt(metrics, ticker):
    # Determine Volume Status
    vol_status = "價漲量增 (攻擊)" if (metrics['close'] > metrics['prev_close'] and metrics['volume'] > metrics['mv5']) else \
                 "價漲量縮 (惜售)" if (metrics['close'] > metrics['prev_close'] and metrics['volume'] < metrics['mv5']) else \
                 "價跌量增 (出貨)" if (metrics['close'] < metrics['prev_close'] and metrics['volume'] > metrics['mv5']) else \
                 "價跌量縮 (觀望)"
    
    ticker_name = f"{ticker} {metrics.get('name', '')}"
    
    prompt = f"""
### 🏛️ 華爾街避險基金策略師分析系統 (Wall Street Hedge Fund Analyst Prompt)

#### 1. System Prompt (請複製到 System Role)

你是一位擁有 20 年經驗的華爾街避險基金 (Hedge Fund) 首席策略師。你的專長是結合「量化技術分析」、「籌碼博弈理論」與「基本面催化劑」來尋找超額報酬 (Alpha)。

**你的行為準則：**
1. **風格冷靜專業：** 不使用誇張形容詞，只用數據和邏輯說話。
2. **風險厭惡 (Risk Averse)：** 看重「風險報酬比」，若風險過高建議觀望。
3. **數據導向：** 所有推論基於提供數據，嚴禁憑空臆測。
4. **操作明確：** 進出場點位必須具體。

---

#### 2. User Prompt (請複製到 User Message)

請針對以下標的 **{ticker_name}** 進行深度策略分析。

**【第一維度：核心量價數據 (Price & Volume)】**
- **分析日期:** {metrics['date']}
- **收盤數據:** 收盤價 {metrics['close']:.2f} (漲跌幅: {((metrics['close'] - metrics['prev_close']) / metrics['prev_close'] * 100):.2f}%)
- **K線型態:** {metrics['pattern']} (Open={metrics['open']:.2f}, High={metrics['high']:.2f}, Low={metrics['low']:.2f})
- **成交量能:** 當日成交量 {metrics['volume']:,} 張 (5日均量: {metrics['mv5']:,})
- **量價關係:** {vol_status}

**【第二維度：技術趨勢架構 (Trend & Momentum)】**
- **均線排列:** MA5={metrics['ma5']:.2f}, MA20={metrics['ma20']:.2f}, MA60={metrics['ma60']:.2f} (MA20乖離: {metrics['bias_ma20']:.2f}%)
- **趨勢狀態:** {metrics['trend']} (MA20 vs MA60)
- **波動區間 (Bollinger):** 上軌={metrics['bb_up']:.2f}, 下軌={metrics['bb_low']:.2f} (帶寬狀態: {metrics['bb_width']:.2f}%)
- **動能指標:** KD(K={metrics['k']:.2f}, D={metrics['d']:.2f}), RSI={metrics['rsi']:.2f} (背離訊號: {metrics['div_rsi']}), MACD柱狀體={metrics['macd_hist']:.2f}
- **風險指標 (ATR):** {metrics['atr']:.2f} (建議停損位: {metrics['stop_loss']:.2f})
- **多空評分:** {metrics.get('score', 0):.1f}/10

**【第三維度：籌碼博弈與情緒 (Chips & Sentiment)】**
- **法人動向:** (請自行聯網搜尋：外資今日買賣超張數 / 投信買賣超張數)
- **散戶情緒:** (請自行聯網搜尋：融資餘額變化)
- **衍生品避險:** (請自行聯網搜尋：{ticker} 期貨或選擇權大額交易人部位)

**【第四維度：基本面與外部環境 (Fundamentals & Environment)】**
- **產業/外部連動:** (請自行聯網搜尋：與該股連動的美股/ETF表現，如 TSUD/SOXX)
- **核心基本面:** (請自行聯網搜尋：近期營收 YoY / 本益比)
- **最新消息/催化劑:** (請自行聯網搜尋：{ticker} 近 3 日重大新聞)

---

**【你的任務 (Mission)】**

請綜合上述四個維度的數據 (量化數據已提供，質化數據請聯網補充)，撰寫一份決策報告：

**1. 多空位階總結 (Executive Summary)**
   - 用一句精煉的話定義目前走勢（例如：籌碼換手後的初升段）。
   - 給予評級：**[強力買進 / 拉回佈局 / 中性觀望 / 反彈減碼 / 放空]**。

**2. 深度邏輯推演 (Deep Dive Diagnosis)**
   - **矛盾對決：** 若「技術面」與「籌碼面」衝突，請指出誰是雜訊。
   - **量價解讀：** 分析當前成交量是否足以支撐股價。

**3. 實戰交易計畫 (Actionable Trading Plan)**
   - **關鍵點位：** 標出最重要的支撐與壓力價位 (可參考 CDP: AH={metrics['pivots']['ah']:.2f}, AL={metrics['pivots']['al']:.2f})。
   - **進場策略 (Entry):** 設定具體的「安全進場區間」。
   - **獲利目標 (Take Profit):** 設定 T1 (短線) 與 T2 (波段) 目標價。
   - **停損防守 (Stop Loss):** 設定一個基於技術面跌破的具體價格。

請保持輸出格式整潔，重點數據請加粗顯示。
"""
    return prompt.strip()

if run_btn:
    real_ticker, user_input_display = process_ticker(ticker_input)
    
    with st.spinner(f"正在運算 {user_input_display} ({real_ticker}) 的機構級模型..."):
        df, metrics = stock_analysis.analyze_stock(real_ticker)
        
        if metrics:
            if real_ticker == "^TWII":
                st.warning("⚠️ 注意：因免費數據源限制，目前使用『加權指數 (^TWII)』作為台指期走勢的替代分析參考。")
            
            # Construct Display Name with Fetched Chinese Name
            stock_name = metrics.get('name', '')
            # If name is same as ticker (fetch failed), just use ticker
            full_display_name = f"{metrics['symbol']} {stock_name}" if stock_name != metrics['symbol'] else f"{metrics['symbol']}"
            
            # 1. Scorecard Section (NEW)
            st.subheader("📊 Bull/Bear Scorecard (多空評分卡)")
            score = metrics.get('score', 5.0)
            score_class = "bull-score" if score >= 7 else "bear-score" if score <= 3 else "neutral-score"
            st.markdown(f'<div class="score-box {score_class}">\n'
                        f'   <h2 style="margin:0;">量化綜效評分 (QUANT SCORE): {score:.1f}/10</h2>\n'
                        f'</div>', unsafe_allow_html=True)
            st.progress(score/10)
            
            # Layout: KPI row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("收盤價 (Close)", f"{metrics['close']:.2f}", 
                        delta=f"{(metrics['close']-metrics['prev_close']):.2f} ({(metrics['close']-metrics['prev_close'])/metrics['prev_close']*100:.1f}%)")
            col2.metric("趨勢 (Trend)", f"{metrics['trend']}")
            col3.metric("量能狀態 (Vol)", f"{metrics['volume']/metrics['mv5']:.1f}x 均量", 
                        delta=f"{metrics['vol_change']:.1f}% vs 昨日", delta_color="off")
            col4.metric("K線型態 (Pattern)", metrics['pattern'])
            
            # Chart
            st.subheader(f"📊 {full_display_name} 股價走勢與布林通道")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index,
                            open=df['Open'], high=df['High'],
                            low=df['Low'], close=df['Close'], name='OHLC'))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1), name='MA20 (月線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Up'], line=dict(color='gray', dash='dash'), name='布林上軌'))
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='gray', dash='dash'), name='布林下軌'))
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            # Divide into Tabs for Report vs AI Bridge
            tab1, tab2 = st.tabs(["📄 即時策略報告", "🤖 AI 橋接咒語 (Institutional Grade)"])
            
            with tab1:
                st.markdown('<div class="report-box">', unsafe_allow_html=True)
                report_md = generate_rule_based_report(metrics, full_display_name)
                st.markdown(report_md)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with tab2:
                st.markdown("### 🧬 AI 橋接咒語 (Prompt Bridge)")
                st.info("此 Prompt 為「華爾街機構級」終極模板，包含 System Prompt, CDP 點位與完整數據。請全部複製貼給 LLM。")
                prompt = generate_ai_prompt(metrics, full_display_name)
                st.code(prompt, language="text")
                
        else:
            st.error(f"無法獲取數據 {real_ticker}。請檢查代號是否正確。")
