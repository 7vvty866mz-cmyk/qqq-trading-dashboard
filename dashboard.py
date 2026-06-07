import streamlit as st

import yfinance as yf

import pandas as pd

import plotly.graph_objects as go

import requests

import time



PUSHOVER_USER = "u5k14oxzojtauzt5r947m8fx1o4wmj"

PUSHOVER_TOKEN = "amdrdrhxqq4c2f8ebp5itjo7z4fhyb"



def send_alert(message):

    requests.post(

        "https://api.pushover.net/1/messages.json",

        data={"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": message}

    )



ACCOUNT_SIZE = 100000

RISK_PER_TRADE = 0.01

ATR_MULT = 2.0

TRAIL_MULT = 2.0



st.set_page_config(layout="wide")

st.title("QQQ Smart Trading Dashboard")



if "last_refresh" not in st.session_state:

    st.session_state.last_refresh = time.time()



if time.time() - st.session_state.last_refresh > 60:

    st.session_state.last_refresh = time.time()

    st.rerun()



st.write("Auto refresh every 60 seconds")



@st.cache_data

def load_data():

    qqq = yf.download("QQQ", period="6mo", interval="1d")

    spy = yf.download("SPY", period="6mo", interval="1d")



    qqq.columns = [c[0] if isinstance(c, tuple) else c for c in qqq.columns]

    spy.columns = [c[0] if isinstance(c, tuple) else c for c in spy.columns]



    qqq = qqq.reset_index()

    spy = spy.reset_index()



    spy = spy[["Date","Close"]]

    spy = spy.rename(columns={"Close":"SPY_Close"})



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



df["Buy"] = 0

df["Sell"] = 0



equity = ACCOUNT_SIZE

equity_curve = [ACCOUNT_SIZE] * len(df)



in_trade = False



for i in range(50, len(df)):



    price = df["Close"].iloc[i]

    atr = df["ATR"].iloc[i]



    if pd.isna(atr):

        continue



    market = df["SPY_Close"].iloc[i] > df["SPY_EMA50"].iloc[i]

    trend = price > df["EMA50"].iloc[i]

    breakout = price > df["Close"].rolling(5).max().iloc[i-1]

    momentum = 55 < df["RSI"].iloc[i] < 70



    if not in_trade and market and trend and breakout and momentum:



        entry = price

        highest = price

        stop = entry - (atr * ATR_MULT)



        risk = entry - stop

        size = int((equity * RISK_PER_TRADE) / risk) if risk > 0 else 0



        in_trade = True

        df.loc[i, "Buy"] = 1



    if in_trade:



        if price > highest:

            highest = price



        new_stop = highest - (atr * TRAIL_MULT)



        if new_stop > stop:

            stop = new_stop



        if price <= stop:



            pnl = (price - entry) * size

            equity += pnl



            df.loc[i, "Sell"] = 1

            in_trade = False



    equity_curve[i] = equity



df["Equity"] = equity_curve



latest = df.iloc[-1]



if "last_signal" not in st.session_state:

    st.session_state.last_signal = 0



live_signal = 0



if latest["SPY_Close"] > latest["SPY_EMA50"] and latest["Close"] > latest["EMA50"] and latest["RSI"] > 55:

    live_signal = 1



if live_signal == 1 and st.session_state.last_signal != 1:

    send_alert("LIVE BUY SIGNAL: " + str(round(latest["Close"],2)))

    st.session_state.last_signal = 1



if live_signal == 0:

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



buy_df = df[df["Buy"] == 1]

fig.add_trace(go.Scatter(

    x=buy_df["Date"],

    y=buy_df["Close"],

    mode="markers",

    marker=dict(color="green"),

    name="Buy"

))



sell_df = df[df["Sell"] == 1]

fig.add_trace(go.Scatter(

    x=sell_df["Date"],

    y=sell_df["Close"],

    mode="markers",

    marker=dict(color="red"),

    name="Sell"

))



st.plotly_chart(fig)

