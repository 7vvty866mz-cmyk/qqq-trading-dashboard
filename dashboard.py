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



    qqq = qqq[["Date","Open","High","Low","Close","Volume"]]  

    spy = spy[["Date","Close"]]  



    spy = spy.rename(columns={"Close":"SPY_Close"})  



    df = pd.merge(qqq, spy, on="Date")  



    for col in ["Open","High","Low","Close","SPY_Close"]:  

        df[col] = pd.to_numeric(df[col], errors="coerce")  



    df = df.dropna()  



    df["RS"] = df["Close"].values / df["SPY_Close"].values  



    return df  



df = load_data()  



# Indicators  

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



df["Score"] = (df["RSI"]/100)*0.4 + (df["Close"]/df["Close"].rolling(5).max())*0.3 + (1-df["ATR_pct"])*0.2 + df["RS_Score"]*0.1  



df = df.fillna(0)  



# SIGNAL GENERATION  

df["Signal"] = 0  



for i in range(1, len(df)):  

    bullish = df["Close"].iloc[i] > df["EMA50"].iloc[i]  

    pullback = df["Close"].iloc[i-1] < df["EMA20"].iloc[i-1] and df["Close"].iloc[i] > df["EMA20"].iloc[i]  

    breakout = df["Close"].iloc[i] > df["Close"].rolling(5).max().iloc[i-1]  



    if bullish and (pullback or breakout) and df["RSI"].iloc[i] > 55:  

        df.loc[i, "Signal"] = 1  



latest = df.iloc[-1]  



# UI  

col1, col2 = st.columns(2)  



with col1:  

    st.subheader("Signals")  

    if latest["Signal"] == 1:  

        st.success("✅ BUY CALL SIGNAL")  

    else:  

        st.write("No signal")  



with col2:  

    st.subheader("Market")  

    st.metric("Price", f"${latest['Close']:.2f}")  

    st.metric("RSI", f"{latest['RSI']:.1f}")  

    st.metric("Score", f"{latest['Score']:.2f}")  



# CANDLE CHART WITH SIGNAL MARKERS  

st.subheader("Candlestick Chart with Signals")  



fig = go.Figure()  



fig.add_trace(go.Candlestick(  

    x=df["Date"],  

    open=df["Open"],  

    high=df["High"],  

    low=df["Low"],  

    close=df["Close"],  

    name="Price"  

))  



# EMAs  

fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA20"], name="EMA20"))  

fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA50"], name="EMA50"))  



# BUY markers  

buy_signals = df[df["Signal"] == 1]  



fig.add_trace(go.Scatter(  

    x=buy_signals["Date"],  

    y=buy_signals["Close"],  

    mode="markers",  

    marker=dict(symbol="triangle-up", size=12),  

    name="Buy Signal"  

))  



st.plotly_chart(fig)  



# Extra Charts  

st.subheader("RSI")  

st.line_chart(df.set_index("Date")[["RSI"]])  



st.subheader("Relative Strength")  

st.line_chart(df.set_index("Date")[["RS"]])  
