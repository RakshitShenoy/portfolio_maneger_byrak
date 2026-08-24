import numpy as np
import pandas as pd


def build_holdings_table(holdings_input, current_prices):
    rows = []
    for _, row in holdings_input.iterrows():
        ticker, shares = row["Ticker"], float(row["Shares Owned"])
        cost_basis, price_now = float(row["Price Paid ($)"]), current_prices[ticker]
        if not np.isfinite(shares) or shares <= 0:
            raise ValueError(f"Shares Owned for {ticker} must be greater than zero.")
        if not np.isfinite(cost_basis) or cost_basis < 0:
            raise ValueError(f"Price Paid ($) for {ticker} must be zero or greater.")
        market_value = shares * price_now
        cost_total = shares * cost_basis
        profit_loss = market_value - cost_total
        rows.append({
            "Ticker": ticker,
            "Shares": shares,
            "Price Paid": round(cost_basis, 2),
            "Current Price": round(price_now, 2),
            "Market Value": round(market_value, 2),
            "Cost Basis Total": round(cost_total, 2),
            "Profit/Loss ($)": round(profit_loss, 2),
            "Profit/Loss (%)": round(profit_loss / cost_total * 100, 2) if cost_total else 0.0,
            "Weight Entered (%)": row["Weight (%)"],
        })
    holdings_df = pd.DataFrame(rows)
    total_value = holdings_df["Market Value"].sum()
    if not np.isfinite(total_value) or total_value <= 0:
        raise ValueError("The portfolio must have a positive total market value.")
    holdings_df["Current Weight (%)"] = round(holdings_df["Market Value"] / total_value * 100, 2)
    return holdings_df, total_value


def calculate_performance_metrics(price_history, holdings_df, risk_free_rate=0.04):
    daily_returns = price_history.pct_change().dropna()
    portfolio_weights = pd.Series(
        holdings_df["Current Weight (%)"].values / 100,
        index=holdings_df["Ticker"].values,
    )[daily_returns.columns]
    portfolio_returns = daily_returns.dot(portfolio_weights)
    cumulative_returns = (1 + portfolio_returns).cumprod() - 1
    annualized_volatility = portfolio_returns.std() * np.sqrt(252)
    annualized_return = (1 + portfolio_returns.mean()) ** 252 - 1
    sharpe_ratio = (
        (annualized_return - risk_free_rate) / annualized_volatility
        if annualized_volatility > 0
        else np.nan
    )
    metrics = {
        "Annualized Return": round(annualized_return * 100, 2),
        "Annualized Volatility": round(annualized_volatility * 100, 2),
        "Sharpe Ratio": round(sharpe_ratio, 2) if np.isfinite(sharpe_ratio) else None,
    }
    return portfolio_returns, cumulative_returns, metrics
