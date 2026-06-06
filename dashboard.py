import streamlit as st
import yfinance as yf
import pandas as pd

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(layout="wide")
st.title("QQQ Options Trading Dashboard")

# -----------------------------
# LOAD DATA (CLEAN + SAFE)
# -----------------------------
@st.cache_data
def load_data():
    df = yf.download("QQQ", period="6mo", interval="1d")

    df = df.reset_index()

    # Keep only needed columns
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

    # Ensure clean numeric values
    df["Close"] = df["Close"].astype(float)
    df["High"] = df["High"].astype(float)
    df["Low"] = df["Low"].astype(float)

    return df


df = load_data()

# -----------------------------
# INDICATORS
# -----------------------------
df["EMA20"] = df["Close"].ewm(span=20).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()

# RSI
delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = -delta.clip(upper=0).rolling(14).mean()

rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# ATR
df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()
df["ATR_pct"] = df["ATR"] / df["Close"]

# Simple momentum score (stable version)
df["Score"] = (
    0.4 * (df["RSI"] / 100) +
    0.3 * (df["Close"] / df["Close"].rolling(5).max()) +
    0.3 * (1 - df["ATR_pct"])
)

df["Score"] = df["Score"].clip(0, 1)

# -----------------------------
# SIGNAL LOGIC
# -----------------------------
signals = []

latest = df.iloc[-1]
prev = df.iloc[-2]

bullish = (
    latest["Close"] > latest["EMA50"]
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
        "Price": round(latest["Close"], 2),
        "RSI": round(latest["RSI"], 1),
        "Score": round(latest["Score"], 2)
    }
    signals.append(signal)

signal_df = pd.DataFrame(signals) if signals else pd.DataFrame()

# -----------------------------
# UI
# -----------------------------
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
    st.metric("Momentum Score", f"{latest['Score']:.2f}")

# -----------------------------
# CHART
# -----------------------------
st.subheader("Price Chart")
st.line_chart(df.set_index("Date")[["Close", "EMA20", "EMA50"]])

# -----------------------------
# PERFORMANCE TRACKER
# -----------------------------
st.subheader("Performance")
start = st.number_input("Starting Capital", value=100000)
current = st.number_input("Current Capital", value=110000)

st.metric("Return", f"{(current - start) / start * 100:.2f}%")
