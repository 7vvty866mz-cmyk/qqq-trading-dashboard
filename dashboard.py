import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import time

PUSHOVER_USER = "u5k14oxzojtauzt5r947m8fx1o4wmj"
PUSHOVER_TOKEN = "amdrdrhxqq4c2f8ebp5itjo7z4fhyb"

def send_alert(msg):
    try:
        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": msg}
        )
    except:
        pass

ACCOUNT_SIZE = 100000

st.set_page_config(layout="wide")
st.title("QQQ Trading Dashboard")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 60:
    st.session_state.last_refresh = time.time()
    st.rerun()

st.write("Auto refresh every 60 seconds")

@st.cache_data
def load_data():
    qqq = yf.download("QQQ", period="6mo")
    spy = yf.download("SPY", period="6mo")

    qqq = qqq.reset_index()
    spy = spy.reset_index()

    spy = spy[["Date", "Close"]]
    spy = spy.rename(columns={"Close": "SPY_Close"})

    df = pd.merge(qqq, spy, on="Date")
    return df

df = load_data()

df["EMA20"] = df["Close"].ewm(span=20).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()
df["SPY_EMA50"] = df["SPY_Close"].ewm(span=50).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = -delta.clip(upper=0).rolling(14).mean()
rs = gain / loss

df["RSI"] = 100 - (100 / (1 + rs))
df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

equity = ACCOUNT_SIZE
in_trade = False
equity_curve = [ACCOUNT_SIZE] * len(df)

for i in range(50, len(df)):
    price = df["Close"].iloc[i]
    atr = df["ATR"].iloc[i]

    if pd.isna(atr):
        continue

    market = df["SPY_Close"].iloc[i] > df["SPY_EMA50"].iloc[i]
    trend = df["EMA20"].iloc[i] > df["EMA50"].iloc[i]
    breakout = price > df["Close"].rolling(5).max().iloc[i-1]
    momentum = 55 < df["RSI"].iloc[i] < 70

    if not in_trade and market and trend and breakout and momentum:
        entry = price
        stop = entry - (atr * 2)
        highest = price
        in_trade = True

    if in_trade:
        if price > highest:
            highest = price

        stop = max(stop, highest - (atr * 3))

        if price <= stop:
            equity += price - entry
            in_trade = False

    equity_curve[i] = equity

df["Equity"] = equity_curve

latest = df.iloc[-1]

if "last_signal" not in st.session_state:
    st.session_state.last_signal = 0

signal = 0

if latest["Close"] > latest["EMA50"] and latest["RSI"] > 55:
    signal = 1

if signal == 1 and st.session_state.last_signal != 1:
    send_alert("BUY SIGNAL: " + str(round(latest["Close"], 2)))
    st.session_state.last_signal = 1

if signal == 0:
    st.session_state.last_signal = 0

st.subheader("Equity Curve")
st.line_chart(df.set_index("Date")[["Equity"]])

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["Date"],
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"]
))

st.plotly_chart(fig)
