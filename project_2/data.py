import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

COMMON_TICKERS = ["AAPL", "MSFT", "SPY"]


def _is_inr_ticker(ticker):
    return ticker.upper().endswith((".NS", ".BO"))


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_usd_to_inr_rate():
    try:
        data = yf.download(
            "INR=X",
            period="5d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )["Close"]
        if isinstance(data, pd.DataFrame):
            data = data.iloc[:, 0]
        recent_rates = data.dropna()
    except Exception as exc:
        raise ValueError("Yahoo Finance could not return the USD to INR exchange rate.") from exc

    if recent_rates.empty:
        raise ValueError("No USD to INR exchange rate was found.")
    rate = float(recent_rates.iloc[-1])
    if not np.isfinite(rate) or rate <= 0:
        raise ValueError("Yahoo Finance returned an invalid USD to INR exchange rate.")
    return rate


def _convert_prices_to_inr(data, tickers):
    usd_tickers = [ticker for ticker in tickers if not _is_inr_ticker(ticker)]
    if usd_tickers:
        data = data.copy()
        data[usd_tickers] = data[usd_tickers] * get_usd_to_inr_rate()
    return data


@st.cache_data(ttl=30 * 60, show_spinner=False)
def search_ticker(query_text: str):
    if not query_text.strip():
        return []

    search = yf.Search(query_text.strip(), max_results=5)
    matches = []
    for item in search.quotes:
        matches.append(
            {
                "Ticker": item.get("symbol"),
                "Full Name": item.get("longname") or item.get("shortname"),
                "Quote Type": item.get("quoteType"),
                "Exchange": item.get("exchange"),
            }
        )
    return matches


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


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_price_history(tickers, period):
    data = yf.download(
        tickers,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    data = _convert_prices_to_inr(data, tickers)
    data = data.dropna(how="all")
    if data.empty:
        raise ValueError("Yahoo Finance returned no historical prices.")
    missing = [ticker for ticker in tickers if ticker not in data.columns]
    if missing:
        raise ValueError(f"No historical data was found for: {', '.join(missing)}")
    return data


@st.cache_data(ttl=5 * 60, show_spinner=False)
def get_current_prices(tickers):
    try:
        data = yf.download(
            tickers,
            period="5d",
            auto_adjust=False,
            progress=False,
            threads=True,
        )["Close"]
    except Exception as exc:
        raise ValueError("Yahoo Finance could not return current prices.") from exc

    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    data = _convert_prices_to_inr(data, tickers)

    prices = {}
    for ticker in tickers:
        if ticker not in data.columns:
            raise ValueError(f"No current price was found for {ticker}.")
        recent_prices = data[ticker].dropna()
        if recent_prices.empty:
            raise ValueError(f"No current price was found for {ticker}.")
        price = float(recent_prices.iloc[-1])
        if not np.isfinite(price) or price <= 0:
            raise ValueError(f"No valid current price was found for {ticker}.")
        prices[ticker] = price
    return prices
