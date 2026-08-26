# Portfolio Manager

Portfolio Manager is a Python app made by Me that helps users understand how their investments are performing. It shows the current value of a portfolio, profit or loss, and useful performance information.

This is a learning project made with Python and Streamlit.

## What the App Does

- Accepts portfolio data from a CSV file or from a table in the app.
- Lets users search for a company or ticker symbol, such as `Apple` or `AAPL`.
- Shows the full company name, ticker, security type, and exchange.
- Gets historical and current prices from Yahoo Finance.
- Calculates the total portfolio value.
- Calculates profit or loss for each holding and for the whole portfolio.
- Calculates annualized return, annualized volatility, and the Sharpe ratio.
- Compares the portfolio with a benchmark, such as `SPY` which can be changed as per the user wants.
- Displays charts for allocation, profit/loss, asset correlation, and portfolio performance.

## Skills Used
### Python,Pandas,Matplotlib,Numpy

## Skills learned/Researched on
### Streamlit,Caching and performance

## Project Files

```text
project_2/
├── calculations.py       # Portfolio and performance calculations
├── charts.py             # Chart creation
├── data.py               # Yahoo Finance data and caching
├── portfolio_manager.py  # App entry point
└── ui.py                 # Streamlit interface
```

## How to Run the App

1. Install the required packages:

	pip install -r project_2/requirements.txt

2. Start the app:

	streamlit run project_2/portfolio_manager.py

3. Open the local URL shown in the terminal.

## Three-Day Research

### Day 1: Understanding Portfolio Data

I researched the information needed to track investments. The important values are the ticker symbol, number of shares, price paid, and current market price. I also learned that market value can be calculated with:

```text
Market value = number of shares x current price
```

### Day 2: Finding Financial Data

I researched ways to get stock prices in Python. I chose `yfinance` because it can search for securities and download price history from Yahoo Finance. I also researched how to handle missing or invalid ticker data.

### Day 3: Measuring Performance

I researched common portfolio measurements. The app uses profit/loss, annualized return, annualized volatility, the Sharpe ratio, and correlation between assets. I also researched Streamlit caching and batched downloads to help reduce waiting time.

## Important Note From Me

This app is for learning and analysis only. It does not give financial advice or recommend trades. Yahoo Finance data may be delayed, and cached prices may be a few minutes old.
