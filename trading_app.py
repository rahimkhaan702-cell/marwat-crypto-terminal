import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone
import time

# Page Config (TradingView Pro Terminal Look)
st.set_page_config(page_title="Marwat TradingView Pro Terminal", layout="wide", page_icon="📈")

# Custom Styling for Terminal & Buttons
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        font-weight: bold;
        border-radius: 6px;
        height: 48px;
        font-size: 16px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    </style>
""", unsafe_allow_html=True)

# Session State for Paper Trading & Portfolio
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.0
if 'positions' not in st.session_state:
    st.session_state.positions = []
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

# Header
st.title("📈 Marwat TradingView Pro Crypto Terminal")

# ==================== SIDEBAR: ALL CRYPTO COINS & SETTINGS ====================
st.sidebar.header("🪙 Crypto Market & Settings")

crypto_coins = {
    "Bitcoin (BTC)": "BTC-USD",
    "Ethereum (ETH)": "ETH-USD",
    "Solana (SOL)": "SOL-USD",
    "Binance Coin (BNB)": "BNB-USD",
    "Ripple (XRP)": "XRP-USD",
    "Cardano (ADA)": "ADA-USD",
    "Dogecoin (DOGE)": "DOGE-USD",
    "Avalanche (AVAX)": "AVAX-USD",
    "Polkadot (DOT)": "DOT-USD",
    "Chainlink (LINK)": "LINK-USD",
    "Polygon (POL)": "POL-USD",
    "Shiba Inu (SHIB)": "SHIB-USD",
    "Gold Futures (GC=F)": "GC=F"
}

selected_coin_name = st.sidebar.selectbox("Coin Select Karein:", list(crypto_coins.keys()))
asset_choice = crypto_coins[selected_coin_name]

timeframe = st.sidebar.selectbox("Timeframe:", ("1m", "5m", "15m", "1h"), index=1)
auto_refresh = st.sidebar.checkbox("🔄 Auto-Refresh (Every 10s)", value=False)

st.sidebar.markdown("---")
st.sidebar.header("🧮 Risk & Lot Calculator")
calc_balance = st.sidebar.number_input("Account Balance ($)", value=st.session_state.balance, step=100.0)
risk_pct = st.sidebar.number_input("Risk Per Trade (%)", value=1.0, step=0.5)
sl_pips = st.sidebar.number_input("Stop Loss (Points)", value=20.0, step=5.0)

risk_amount = calc_balance * (risk_pct / 100)
recommended_lot = round(risk_amount / (sl_pips * 10), 2) if sl_pips > 0 else 0.01

st.sidebar.success(f"Risk Amount: **${risk_amount:.2f}**")
st.sidebar.info(f"Suggested Lot Size: **{recommended_lot:.2f}**")

# ==================== CANDLE COUNTDOWN TIMER LOGIC ====================
def get_candle_countdown(tf):
    now = datetime.now(timezone.utc)
    tf_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}.get(tf, 300)
    elapsed = (now.minute * 60 + now.second) % tf_seconds
    remaining = tf_seconds - elapsed
    mins, secs = divmod(remaining, 60)
    return f"{mins:02d}:{secs:02d}"

# ==================== DATA FETCHING & INDICATORS ====================
data = yf.download(tickers=asset_choice, period="2d", interval=timeframe, progress=False)

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Extract clean series
    open_s = data['Open'].iloc[:, 0] if isinstance(data['Open'], pd.DataFrame) else data['Open']
    high_s = data['High'].iloc[:, 0] if isinstance(data['High'], pd.DataFrame) else data['High']
    low_s = data['Low'].iloc[:, 0] if isinstance(data['Low'], pd.DataFrame) else data['Low']
    close_s = data['Close'].iloc[:, 0] if isinstance(data['Close'], pd.DataFrame) else data['Close']

    # Technical Indicators (Dual 34 EMA, 50, 200 EMA & RSI)
    ema34_h = high_s.ewm(span=34, adjust=False).mean()
    ema34_l = low_s.ewm(span=34, adjust=False).mean()
    ema50 = close_s.ewm(span=50, adjust=False).mean()
    ema200 = close_s.ewm(span=200, adjust=False).mean()

    delta = close_s.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    latest_close = float(close_s.iloc[-1])
    latest_ema_h = float(ema34_h.iloc[-1])
    latest_ema_l = float(ema34_l.iloc[-1])
    latest_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    countdown_str = get_candle_countdown(timeframe)

    # ==================== TOP METRICS BAR ====================
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(f"{selected_coin_name} Price", f"${latest_close:,.4f}" if latest_close < 1 else f"${latest_close:,.2f}")
    m2.metric("Demo Equity", f"${st.session_state.balance:,.2f}")
    m3.metric("RSI (14)", f"{latest_rsi:.1f}", delta="Overbought (>70)" if latest_rsi > 70 else ("Oversold (<30)" if latest_rsi < 30 else "Neutral"))
    m4.metric("Candle Timer", f"⏳ {countdown_str}")
    
    if latest_close > latest_ema_h:
        m5.success("BULLISH TREND")
    elif latest_close < latest_ema_l:
        m5.error("BEARISH TREND")
    else:
        m5.warning("IN 34 EMA CHANNEL")

    # ==================== BUY / SELL EXECUTION PANEL ====================
    st.markdown("---")
    exec_col1, exec_col2, exec_col3, exec_col4 = st.columns([1.2, 1.5, 1.5, 1])
    
    with exec_col1:
        trade_lot = st.number_input("Order Lots", min_value=0.01, max_value=50.0, value=max(0.01, recommended_lot), step=0.01)
    
    with exec_col2:
        st.write("")
        if st.button(f"🟢 BUY {selected_coin_name}"):
            st.session_state.positions.append({
                "id": len(st.session_state.positions) + 1,
                "asset": selected_coin_name,
                "type": "BUY",
                "lot": trade_lot,
                "entry": latest_close,
                "time": datetime.now().strftime("%H:%M:%S")
            })
            st.toast(f"BUY Executed: {trade_lot} Lots of {selected_coin_name}", icon="✅")

    with exec_col3:
        st.write("")
        if st.button(f"🔴 SELL {selected_coin_name}"):
            st.session_state.positions.append({
                "id": len(st.session_state.positions) + 1,
                "asset": selected_coin_name,
                "type": "SELL",
                "lot": trade_lot,
                "entry": latest_close,
                "time": datetime.now().strftime("%H:%M:%S")
            })
            st.toast(f"SELL Executed: {trade_lot} Lots of {selected_coin_name}", icon="🚨")

    with exec_col4:
        st.write("")
        if st.button("🔄 Refresh Data"):
            st.rerun()

    # ==================== LIVE OPEN POSITIONS & P&L ====================
    if st.session_state.positions:
        st.subheader("📊 Open Positions & Live P&L Tracker")
        for idx, pos in enumerate(st.session_state.positions):
            p_col1, p_col2, p_col3, p_col4, p_col5, p_col6 = st.columns([1.5, 1, 1, 1.5, 1.5, 1])
            
            # Live P&L Calculation based on real-time price movement
            price_diff = (latest_close - pos['entry']) if pos['type'] == "BUY" else (pos['entry'] - latest_close)
            pnl = price_diff * pos['lot'] * 10
            
            p_col1.write(f"**{pos['asset']}** ({pos['time']})")
            p_col2.markdown(f":green[**BUY**]" if pos['type'] == "BUY" else f":red[**SELL**]")
            p_col3.write(f"Lot: **{pos['lot']}**")
            p_col4.write(f"Entry: `${pos['entry']:,.2f}`")
            p_col5.markdown(f":green[**+${pnl:.2f}**]" if pnl >= 0 else f":red[**-${abs(pnl):.2f}**]")
            
            if p_col6.button("❌ Close", key=f"close_{idx}"):
                st.session_state.balance += pnl
                st.session_state.trade_history.append({**pos, "exit": latest_close, "pnl": round(pnl, 2)})
                st.session_state.positions.pop(idx)
                st.rerun()

    # ==================== TRADINGVIEW STYLE SUBPLOT CHART ====================
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.75, 0.25]
    )

    # Row 1: Candlestick + EMAs
    fig.add_trace(go.Candlestick(
        x=data.index[-120:], open=open_s[-120:], high=high_s[-120:],
        low=low_s[-120:], close=close_s[-120:], name="Price"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=data.index[-120:], y=ema34_h[-120:], line=dict(color='#00E676', width=1.5), name='34 EMA High'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index[-120:], y=ema34_l[-120:], line=dict(color='#FF5252', width=1.5), name='34 EMA Low'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index[-120:], y=ema50[-120:], line=dict(color='#29B6F6', width=1.2, dash='dot'), name='50 EMA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index[-120:], y=ema200[-120:], line=dict(color='#FFA726', width=2), name='200 EMA'), row=1, col=1)

    # Row 2: RSI Subplot
    fig.add_trace(go.Scatter(x=data.index[-120:], y=rsi[-120:], line=dict(color='#AB47BC', width=1.8), name='RSI (14)'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=680,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==================== CLOSED TRADE JOURNAL ====================
    if st.session_state.trade_history:
        with st.expander("📜 Closed Trade History Journal"):
            st.dataframe(pd.DataFrame(st.session_state.trade_history), use_container_width=True)

else:
    st.error("Market data load nahi ho saka. Internet connection check karein.")

# Auto Refresh
if auto_refresh:
    time.sleep(10)
    st.rerun()