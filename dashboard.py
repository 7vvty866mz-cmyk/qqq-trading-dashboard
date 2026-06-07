import streamlit as st

import yfinance as yf

import pandas as pd

import plotly.graph_objects as go

import requests

import time



# -------------------

# 🔔 PUSHOVER SETTINGS

# -------------------

PUSHOVER_USER = "u5k14oxzojtauzt5r947m8fx1o4wmj"

PUSHOVER_TOKEN = "amdrdrhxqq4c2f8ebp5itjo7z4fhyb"



def send_alert(message):

    requests.post(

        "https://api.pushover.net/1/messages.json",

        data={"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": message}

    )



# -------------------

# SETTINGS

# -------------------

STOP_LOSS_PCT = 0.02

TRAILING_STOP_PCT = 0.02

RISK_PER_TRADE = 0.01   # 1% of capital



ACCOUNT_SIZE = 100000   # adjust this!



# -------------------

# APP CONFIG

# -------------------

st.set_page_config(layout="wide")

st.title("QQQ Trading Dashboard")



# -------------------

# AUTO REFRESH

# -------------------

refresh_interval = 60



if "last_refresh" not in st.session_state:

    st.session_state.last_refresh = time.time()



if time.time() - st.session_state.last_refresh > refresh_interval:

    st.session_state.last_refresh = time.time()

    st.rerun()



st.write("Auto-refreshing every 60 seconds")



# -------------------

# LOAD DATA

# -------------------

@st.cache_data

def load_data():

    df = yf.download("QQQ", period="6mo", interval="1d")

    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    df = df.reset_index()

    df = df[["Date","Open","High","Low","Close","Volume"]]



    for col in ["Open","High","Low","Close"]:

        df[col] = pd.to_numeric(df[col], errors="coerce")



    return df.dropna()



df = load_data()



# -------------------

# INDICATORS

# -------------------

df["EMA20"] = df["Close"].ewm(span=20).mean()

df["EMA50"] = df["Close"].ewm(span=50).mean()



delta = df["Close"].diff()

gain = delta.clip(lower=0).rolling(14).mean()

loss = -delta.clip(upper=0).rolling(14).mean()

rs = gain / loss

df["RSI"] = 100 - (100 / (1 + rs))



# -------------------

# SIGNAL

# -------------------

df["Signal"] = 0



for i in range(1, len(df)):

    if df["Close"].iloc[i] > df["EMA50"].iloc[i] and df["RSI"].iloc[i] > 55:

        df.loc[i, "Signal"] = 1



latest = df.iloc[-1]

price = latest["Close"]



# -------------------

# TRADE STATE

# -------------------

if "in_trade" not in st.session_state:

    st.session_state.in_trade = False

    st.session_state.entry_price = 0

    st.session_state.stop_price = 0

    st.session_state.highest_price = 0

    st.session_state.position_size = 0

    st.session_state.trades = []



# -------------------

# ENTRY WITH POSITION SIZING

# -------------------

if latest["Signal"] == 1 and not st.session_state.in_trade:



    entry = price

    stop = price * (1 - STOP_LOSS_PCT)



    risk_per_share = entry - stop

    total_risk = ACCOUNT_SIZE * RISK_PER_TRADE



    position_size = int(total_risk / risk_per_share)



    st.session_state.in_trade = True

    st.session_state.entry_price = entry

    st.session_state.stop_price = stop

    st.session_state.highest_price = price

    st.session_state.position_size = position_size



    send_alert(f"BUY QQQ | Price: {entry:.2f} | Size: {position_size}")



# -------------------

# TRAILING STOP + EXIT

# -------------------

exit_signal = False



if st.session_state.in_trade:



    if price > st.session_state.highest_price:

        st.session_state.highest_price = price



    new_stop = st.session_state.highest_price * (1 - TRAILING_STOP_PCT)



    if new_stop > st.session_state.stop_price:

        st.session_state.stop_price = new_stop



    if price <= st.session_state.stop_price:



        exit_signal = True

        entry = st.session_state.entry_price

        size = st.session_state.position_size



        pnl = (price - entry) * size



        st.session_state.trades.append({

            "Entry": round(entry,2),

            "Exit": round(price,2),

            "Size": size,

            "PnL": round(pnl,2)

        })



        st.session_state.in_trade = False



        send_alert(f"EXIT | Price: {price:.2f} | PnL: {pnl:.2f}")



# -------------------

# UI

# -------------------

st.subheader("Trade Status")



if st.session_state.in_trade:

    st.success("IN TRADE")

    st.write(f"Entry: {st.session_state.entry_price:.2f}")

    st.write(f"Size: {st.session_state.position_size}")

    st.write(f"Stop: {st.session_state.stop_price:.2f}")



else:

    st.write("No active trade")



# -------------------

# PERFORMANCE

# -------------------

st.subheader("Performance")



if len(st.session_state.trades) > 0:

    trades_df = pd.DataFrame(st.session_state.trades)



    total_pnl = trades_df["PnL"].sum()

    win_rate = (trades_df["PnL"] > 0).mean() * 100



    st.metric("Total PnL", f"{total_pnl:.2f}")

    st.metric("Win Rate", f"{win_rate:.1f}%")



    st.dataframe(trades_df)

else:

    st.write("No trades yet")



# -------------------

# CHART

# -------------------

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

