import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("QQQ Options Trading Dashboard")

@st.cache_data
def load_data():
    qqq = yf.download("QQQ", period="6mo", interval="1d")
    spy = yf.download("SPY", period="6mo", interval="1d")
    df = qqq.copy()
    df["SPY"] = spy["Close"]
    return df

df = load_data()

df["EMA20"] = df["Close"].ewm(span=20).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()
df["EMA200"] = df["Close"].ewm(span=200).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = -delta.clip(upper=0).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

df["RS"] = df["Close"] / df["SPY"]
df["Breakout"] = df["Close"] / df["Close"].rolling(5).max()

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()
df["ATR_pct"] = df["ATR"] / df["Close"]

df["ML_Score"] = (
    0.35 * (df["RSI"] / 100) +
    0.25 * df["Breakout"] +
    0.20 * (df["RS"] / df["RS"].rolling(20).mean()) +
    0.20 * (1 - df["ATR_pct"])
)

df["ML_Score"] = df["ML_Score"].clip(0, 1)

signals = []

latest = df.iloc[-1]
prev = df.iloc[-2]

bullish = (
    latest["Close"] > latest["EMA50"] and
    latest["EMA50"] > latest["EMA200"]
)

pullback = (
    prev["Close"] < prev["EMA20"] and
    latest["Close"] > latest["EMA20"]
)

breakout = (
    latest["Close"] > df["Close"].rolling(5).max().iloc[-2]
)

if bullish and (pullback or breakout) and latest["RSI"] > 55:
    signal = {
        "Type": "BUY CALL",
        "Entry": round(latest["Close"], 2),
        "Strike": round(latest["Close"] * 0.99),
        "DTE": 10,
        "RSI": round(latest["RSI"], 1),
        "ML Score": round(latest["ML_Score"], 2)
    }
    signals.append(signal)

signal_df = pd.DataFrame(signals) if signals else pd.DataFrame()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Trade Signals")
    if not signal_df.empty:
        st.dataframe(signal_df)
    else:
        st.write("No signals")

with col2:
    st.subheader("Market")
    st.metric("QQQ Price", f"${latest['Close']:.2f}")
    st.metric("RSI", f"{latest['RSI']:.1f}")
    st.metric("ML Score", f"{latest['ML_Score']:.2f}")

st.subheader("Chart")
st.line_chart(df[["Close", "EMA20", "EMA50"]])

st.subheader("Performance")
start = st.number_input("Start", value=100000)
current = st.number_input("Current", value=110000)
st.metric("Return", f"{(current-start)/start*100:.2f}%")
