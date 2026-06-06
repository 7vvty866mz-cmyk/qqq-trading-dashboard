import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("QQQ Options Trading Dashboard")

@st.cache_data
def load_data():
    qqq = yf.download("QQQ", period="6mo", interval="1d")
    spy = yf.download("SPY", period="6mo", interval="1d")

    qqq.columns = [col[0] if isinstance(col, tuple) else col for col in qqq.columns]
    spy.columns = [col[0] if isinstance(col, tuple) else col for col in spy.columns]

    qqq = qqq.reset_index()
    spy = spy.reset_index()

    qqq = qqq[["Date", "Open", "High", "Low", "Close", "Volume"]]
    spy = spy[["Date", "Close"]]

    spy = spy.rename(columns={"Close": "SPY_Close"})

    df = pd.merge(qqq, spy, on="Date", how="inner")

    for col in ["Open", "High", "Low", "Close", "SPY_Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()

    df["RS"] = df["Close"].values / df["SPY_Close"].values

    return df

df = load_data()

-----------------------

INDICATORS

-----------------------

df["EMA20"] = df["Close"].ewm(span=20).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = -delta.clip(upper=0).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()
df["ATR_pct"] = df["ATR"].values / df["Close"].values

df["RS_Score"] = df["RS"] / df["RS"].rolling(20).mean()

df["Score"] = (
    0.35 * (df["RSI"] / 100) +
    0.25 * (df["Close"] / df["Close"].rolling(5).max()) +
    0.20 * (1 - df["ATR_pct"]) +
    0.20 * df["RS_Score"]
)

df = df.fillna(0)

-----------------------

SIGNAL LOGIC

-----------------------

signals = []

latest = df.iloc[-1]
prev = df.iloc[-2]

bullish = latest["Close"] > latest["EMA50"]

pullback = prev["Close"] < prev["EMA20"] and latest["Close"] > latest["EMA20"]

breakout = latest["Close"] > df["Close"].rolling(5).max().iloc[-2]

if bullish and (pullback or breakout) and latest["RSI"] > 55:
    signals.append({
        "Type": "BUY CALL",
        "Price": round(latest["Close"], 2),
        "RSI": round(latest["RSI"], 1),
        "Score": round(latest["Score"], 2)
    })

signal_df = pd.DataFrame(signals)

-----------------------

UI

-----------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("Trade Signals")
    if not signal_df.empty:
        st.dataframe(signal_df)
    else:
        st.write("No signals")

with col2:
    st.subheader("Market Info")
    st.metric("QQQ Price", f"${latest['Close']:.2f}")
    st.metric("RSI", f"{latest['RSI']:.1f}")
    st.metric("Score", f"{latest['Score']:.2f}")
    st.metric("Relative Strength", f"{latest['RS']:.3f}")

-----------------------

CANDLESTICK CHART

-----------------------

st.subheader("Candlestick Chart")

fig = go.Figure(data=[
    go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )
])

Add EMAs

fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA20"], name="EMA20"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA50"], name="EMA50"))

st.plotly_chart(fig, use_container_width=True)

-----------------------

EXTRA CHARTS

-----------------------

st.subheader("RSI")
st.line_chart(df.set_index("Date")[["RSI"]])

st.subheader("Relative Strength")
st.line_chart(df.set_index("Date")[["RS"]])

