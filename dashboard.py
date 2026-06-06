import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

-------------------

🔔 PASTE YOUR KEYS HERE

-------------------

PUSHOVER_USER = "PASTE_USER_KEY_HERE"
PUSHOVER_TOKEN = "PASTE_API_TOKEN_HERE"

def send_alert(message):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "message": message
        }
    )

-------------------

APP

-------------------

st.set_page_config(layout="wide")
st.title("QQQ Trading Dashboard")

@st.cache_data
def load_data():
    df = yf.download("QQQ", period="6mo", interval="1d")

    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    df = df.reset_index()

    df = df[["Date","Open","High","Low","Close","Volume"]]

    for col in ["Open","High","Low","Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()
    return df

df = load_data()

-------------------

INDICATORS

-------------------

df["EMA20"] = df["Close"].ewm(span=20).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = -delta.clip(upper=0).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

-------------------

SIGNAL

-------------------

df["Signal"] = 0

for i in range(1, len(df)):
    bullish = df["Close"].iloc[i] > df["EMA50"].iloc[i]
    pullback = df["Close"].iloc[i-1] < df["EMA20"].iloc[i-1] and df["Close"].iloc[i] > df["EMA20"].iloc[i]

    if bullish and pullback and df["RSI"].iloc[i] > 55:
        df.loc[i, "Signal"] = 1

latest = df.iloc[-1]

-------------------

🔔 ALERT

-------------------

if latest["Signal"] == 1:
    msg = f"QQQ BUY SIGNAL | Price: {latest['Close']:.2f} | RSI: {latest['RSI']:.1f}"
    send_alert(msg)

-------------------

UI

-------------------

st.subheader("Signal")
if latest["Signal"] == 1:
    st.success("BUY SIGNAL")
else:
    st.write("No Signal")

st.metric("Price", f"${latest['Close']:.2f}")
st.metric("RSI", f"{latest['RSI']:.1f}")

-------------------

CHART

-------------------

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["Date"],
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"]
))

fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA20"], name="EMA20"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA50"], name="EMA50"))

st.plotly_chart(fig)
