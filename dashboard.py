import streamlit as st

import yfinance as yf

import pandas as pd



st.set_page_config(layout="wide")

st.title("QQQ Options Trading Dashboard")



@st.cache_data

def load_data():

    df = yf.download("QQQ", period="6mo", interval="1d")



    # Flatten columns (fixes MultiIndex issues)

    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]



    df = df.reset_index()



    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]



    # Convert everything to float safely

    for col in ["Open", "High", "Low", "Close"]:

        df[col] = pd.to_numeric(df[col], errors="coerce")



    df = df.dropna()



    return df



df = load_data()



# -------------------------

# INDICATORS (SAFE VERSION)

# -------------------------



df["EMA20"] = df["Close"].ewm(span=20).mean()

df["EMA50"] = df["Close"].ewm(span=50).mean()



# RSI (safe)

delta = df["Close"].diff()

gain = delta.clip(lower=0).rolling(14).mean()

loss = -delta.clip(upper=0).rolling(14).mean()

rs = gain / loss

df["RSI"] = 100 - (100 / (1 + rs))



# ATR SAFE FIX

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()



df["ATR_pct"] = df["ATR"].values / df["Close"].values



# Simple score

df["Score"] = (

    0.4 * (df["RSI"] / 100) +

    0.3 * (df["Close"] / df["Close"].rolling(5).max()) +

    0.3 * (1 - df["ATR_pct"])

)



df = df.fillna(0)



# -------------------------

# SIGNALS

# -------------------------



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



# -------------------------

# UI

# -------------------------



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



# -------------------------

# CHART

# -------------------------



st.subheader("Chart")

st.line_chart(df.set_index("Date")[["Close", "EMA20", "EMA50"]])

