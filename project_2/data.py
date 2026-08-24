import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

COMMON_TICKERS = ["AAPL", "MSFT", "SPY"]


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def load_all_tickers():
    try:
        nasdaq = pd.read_csv(
            "http://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
            sep="|",
            on_bad_lines="skip",
        )
        other = pd.read_csv(
            "http://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
            sep="|",
            on_bad_lines="skip",
        )
        nasdaq_symbols = nasdaq.loc[nasdaq["Test Issue"] == "N", "Symbol"]
        other_symbols = other.loc[other["Test Issue"] == "N", "ACT Symbol"]
        all_symbols = pd.concat([nasdaq_symbols, other_symbols]).dropna().unique()
        return sorted(str(symbol).strip() for symbol in all_symbols if str(symbol).strip())
    except Exception:
        return COMMON_TICKERS


@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(tickers, period):
    data = yf.download(tickers, period=period, auto_adjust=True)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    data = data.dropna(how="all")
    if data.empty:
        raise ValueError("Yahoo Finance returned no historical prices.")
    missing = [ticker for ticker in tickers if ticker not in data.columns]
    if missing:
        raise ValueError(f"No historical data was found for: {', '.join(missing)}")
    return data


@st.cache_data(ttl=60, show_spinner=False)
def get_current_prices(tickers):
    prices = {}
    for ticker in tickers:
        try:
            price = yf.Ticker(ticker).fast_info["last_price"]
        except Exception as exc:
            raise ValueError(f"No current price was found for {ticker}.") from exc
        if not np.isfinite(price) or price <= 0:
            raise ValueError(f"No valid current price was found for {ticker}.")
        prices[ticker] = price
    return prices
