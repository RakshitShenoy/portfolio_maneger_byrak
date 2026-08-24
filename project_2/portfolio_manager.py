import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
#importing the required libraries for data manipulation, visualization, and fetching financial data.

COMMON_TICKERS = ["AAPL", "MSFT", "SPY"]


#------section 1
# DATA FUNCTIONS
# These use yahoo finance to fetch historical and current prices. They are not pure functions
# they just fetch numbers and hand back a DataFrame/dict.
#-------

#this is so that the user knows what ticker they are entering
@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)  # refresh daily
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
        return sorted(str(s).strip() for s in all_symbols if str(s).strip())
    except Exception:
        # fallback if the feed is unreachable — better than a broken dropdown
        return COMMON_TICKERS

# price history fetching for the currnt date and downloading history of stock
# droping/removing all the empty rows and coloums of data for a eaiser analysis
# also making sure to raise an error if data is empty
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

# getting current price of the stock and raising error if invalid input such as 0 or infinite or other values
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


# ------section 2
# CALCULATIONS
# Pure functions - given data in, they hand a result back. This
# makes them easy to test and easy to reuse outside Streamlit too.
# -------



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
            "Ticker": ticker, "Shares": shares, "Price Paid": round(cost_basis, 2),
            "Current Price": round(price_now, 2), "Market Value": round(market_value, 2),
            "Cost Basis Total": round(cost_total, 2), "Profit/Loss ($)": round(profit_loss, 2),
            "Profit/Loss (%)": round(profit_loss / cost_total * 100, 2) if cost_total else 0.0,
            "Weight Entered (%)": row["Weight (%)"],
        })
    df = pd.DataFrame(rows)
    total_value = df["Market Value"].sum()
    if not np.isfinite(total_value) or total_value <= 0:
        raise ValueError("The portfolio must have a positive total market value.")
    df["Current Weight (%)"] = round(df["Market Value"] / total_value * 100, 2)
    return df, total_value


def calculate_performance_metrics(price_history, holdings_df, risk_free_rate=0.04):
    # daily_returns = daily percentage changes for each asset
    daily_returns = price_history.pct_change().dropna()

    # portfolio_weights = current holding weights as decimals
    portfolio_weights = pd.Series(
        holdings_df["Current Weight (%)"].values / 100,
        index=holdings_df["Ticker"].values,
    )[daily_returns.columns]

    # portfolio_returns = combined daily portfolio returns
    portfolio_returns = daily_returns.dot(portfolio_weights)

    # cumulative_returns = total portfolio growth over time
    cumulative_returns = (1 + portfolio_returns).cumprod() - 1

    # annualized_volatility = yearly portfolio risk
    annualized_volatility = portfolio_returns.std() * np.sqrt(252)

    # annualized_return = estimated yearly return
    annualized_return = (1 + portfolio_returns.mean()) ** 252 - 1

    # sharpe_ratio = return earned per unit of risk
    sharpe_ratio = (
        (annualized_return - risk_free_rate) / annualized_volatility
        if annualized_volatility > 0
        else np.nan
    )

    metrics = {
        "Annualized Return": round(annualized_return * 100, 2),
        "Annualized Volatility": round(annualized_volatility * 100, 2),
        "Sharpe Ratio": (
            round(sharpe_ratio, 2)
            if np.isfinite(sharpe_ratio)
            else None
        ),
    }

    return portfolio_returns, cumulative_returns, metrics

# building a dashboard with price returns bechmarks stock and holdings
# so user can understand the history and performance of their portfolio 
# and also compare it with the benchmark performance
# also ploting the nessesarry charts as per the visualization requirements of the user
def build_dashboard_figure(
    price_history,
    cumulative_returns,
    benchmark_ticker,
    tickers,
    holdings_df,
):
    # figure = complete dashboard
    # axes = four chart areas
    figure, axes = plt.subplots(2, 2, figsize=(14, 9))

    # allocation = current portfolio allocation percentages
    allocation = holdings_df.set_index("Ticker")["Current Weight (%)"]

    # profit_loss = profit or loss for each holding
    profit_loss = holdings_df.set_index("Ticker")["Profit/Loss ($)"]

    axes[0, 0].pie(
        allocation,
        labels=allocation.index,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"width": 0.45},
    )
    axes[0, 0].set_title("Current Portfolio Allocation")

    # bar_colors = green for profit and red for loss
    bar_colors = [
        "green" if value >= 0 else "red"
        for value in profit_loss
    ]

    axes[0, 1].bar(
        profit_loss.index,
        profit_loss.values,
        color=bar_colors,
    )
    axes[0, 1].axhline(0, color="black", linewidth=0.8)
    axes[0, 1].set(
        title="Profit/Loss by Holding",
        ylabel="Profit/Loss ($)",
    )
    axes[0, 1].tick_params(axis="x", rotation=45)

    # correlation_matrix = relationship between asset returns
    correlation_matrix = (
        price_history[tickers]
        .pct_change()
        .dropna()
        .corr()
    )

    heatmap = axes[1, 0].imshow(
        correlation_matrix,
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
    )

    axes[1, 0].set(
        xticks=range(len(correlation_matrix)),
        yticks=range(len(correlation_matrix)),
        xticklabels=correlation_matrix.columns,
        yticklabels=correlation_matrix.columns,
        title="Asset Correlation Heatmap",
    )
    axes[1, 0].tick_params(axis="x", rotation=45)

    for row_index in range(len(correlation_matrix)):
        for column_index in range(len(correlation_matrix)):
            axes[1, 0].text(
                column_index,
                row_index,
                round(
                    correlation_matrix.iloc[
                        row_index, column_index
                    ],
                    2,
                ),
                ha="center",
                va="center",
            )

    figure.colorbar(heatmap, ax=axes[1, 0])

    # benchmark_returns = daily benchmark returns
    benchmark_returns = (
        price_history[benchmark_ticker]
        .pct_change()
        .dropna()
    )

    # benchmark_cumulative_returns = total benchmark growth
    benchmark_cumulative_returns = (
        (1 + benchmark_returns).cumprod() - 1
    )

    axes[1, 1].plot(
        cumulative_returns.index,
        cumulative_returns.values * 100,
        label="My Portfolio",
    )
    axes[1, 1].plot(
        benchmark_cumulative_returns.index,
        benchmark_cumulative_returns.values * 100,
        label=f"Benchmark ({benchmark_ticker})",
        linestyle="--",
    )
    axes[1, 1].set(
        title="Cumulative Return: Portfolio vs. Benchmark",
        ylabel="Return (%)",
    )
    axes[1, 1].legend()

    plt.tight_layout()
    return figure


# ------section 3
# STREAMLIT PAGE LAYOUT
# Everything below this is the gui and app related
# -------

st.set_page_config(page_title="Portfolio Manager", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Portfolio Manager")
st.write(
    "Enter what you own below, then click **Run Analysis**. "
    "This tool reports your current profit/loss and performance - "
    "it does not recommend trades."
)

# ---- Step 1: user types in their holdings ----
st.subheader("1. Your Holdings")

REQUIRED_COLUMNS = ["Ticker", "Shares Owned", "Price Paid ($)", "Weight (%)"]

input_method = st.radio(
    "How do you want to enter your portfolio?",
    ["Upload a CSV file", "Type it in manually"],
    horizontal=True,
)

holdings_input = None

if input_method == "Upload a CSV file":
    st.caption(
        "CSV must have these exact column headers: "
        "Ticker, Shares Owned, Price Paid ($), Weight (%)"
    )

    # Let the user grab a template so their column names match exactly
    # this was entierly generated by claude and is not a real portfolio template
    template_csv = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT", "SPY"],
        "Shares Owned": [10.0, 5.0, 8.0],
        "Price Paid ($)": [150.0, 280.0, 400.0],
        "Weight (%)": [40, 35, 25],
    }).to_csv(index=False)
    st.download_button(
        "Download CSV template", template_csv, file_name="portfolio_template.csv"
    )

    uploaded_file = st.file_uploader("Upload your portfolio CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            csv_data = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Couldn't read that file: {e}")
            st.stop()

        missing = [c for c in REQUIRED_COLUMNS if c not in csv_data.columns]
        if missing:
            st.error(f"CSV is missing required column(s): {', '.join(missing)}")
            st.stop()

        holdings_input = csv_data[REQUIRED_COLUMNS]
        st.write("Preview of what was uploaded:")
        st.dataframe(holdings_input, use_container_width=True, hide_index=True)

else:  # Type it in manually option
    st.caption("Add a row per asset. Weight (%) is just for your own reference.")

    default_data = pd.DataFrame(columns=REQUIRED_COLUMNS)

    holdings_input = st.data_editor(
        default_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Ticker": st.column_config.SelectboxColumn(
                "Ticker",
                options=load_all_tickers(),
                help="Start typing to search — thousands of US-listed tickers.",
                required=True,
            ),
        },
    )

col_a, col_b = st.columns(2)
with col_a:
    benchmark_ticker = st.text_input("Benchmark ticker", value="SPY")
with col_b:
    history_period = st.selectbox(
        "History period", ["6mo", "1y", "2y", "5y"], index=1
    )

run_clicked = st.button("Run Analysis", type="primary")

# ---- Step 2-4: only run once the button is clicked ----
if run_clicked:
    if holdings_input is None or len(holdings_input) == 0:
        st.warning("Upload a CSV or add at least one holding before running the analysis.")
        st.stop()

    # Clean up whatever the user typed or uploaded
    holdings_input = holdings_input.dropna(subset=["Ticker"]).copy()
    holdings_input["Ticker"] = holdings_input["Ticker"].astype(str).str.upper().str.strip()
    benchmark_ticker = benchmark_ticker.strip().upper()
    tickers = holdings_input["Ticker"].tolist()

    if len(tickers) == 0 or not benchmark_ticker:
        st.warning("Add at least one holding before running the analysis.")
        st.stop()

    if holdings_input["Ticker"].duplicated().any():
        st.error("Each ticker may appear only once. Combine duplicate positions before running the analysis.")
        st.stop()

    numeric_columns = ["Shares Owned", "Price Paid ($)", "Weight (%)"]
    for column in numeric_columns:
        holdings_input[column] = pd.to_numeric(holdings_input[column], errors="coerce")
    if holdings_input[numeric_columns].isna().any().any():
        st.error("Shares Owned, Price Paid ($), and Weight (%) must contain valid numbers.")
        st.stop()

    with st.spinner("Fetching prices..."):
        all_tickers = list(dict.fromkeys(tickers + [benchmark_ticker]))
        try:
            price_history = fetch_price_history(all_tickers, history_period)
            current_prices = get_current_prices(tickers)
        except Exception as e:
            st.error(f"Couldn't fetch market data: {e}")
            st.stop()
    # graphs and other outputs are genrated once analysis 
    # is clicked and data is fetched successfully
    # --- Profit / Loss ---
    st.subheader("2. Profit / Loss")
    try:
        holdings_df, total_value = build_holdings_table(holdings_input, current_prices)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    st.dataframe(holdings_df, use_container_width=True, hide_index=True)

    total_cost = holdings_df["Cost Basis Total"].sum()
    total_pl = holdings_df["Profit/Loss ($)"].sum()
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Portfolio Value", f"${total_value:,.2f}")
    m2.metric("Total Profit/Loss", f"${total_pl:,.2f}", f"{total_pl_pct:.2f}%")
    m3.metric("Total Cost Basis", f"${total_cost:,.2f}")

    # --- Performance metrics ---
    st.subheader("3. Performance Metrics")
    _, cumulative_return, metrics = calculate_performance_metrics(
        price_history[tickers],
        holdings_df,
        risk_free_rate=0.04,
    )
    p1, p2, p3 = st.columns(3)
    p1.metric("Annualized Return", f'{metrics["Annualized Return"]}%')
    p2.metric("Annualized Volatility", f'{metrics["Annualized Volatility"]}%')
    p3.metric("Sharpe Ratio", metrics["Sharpe Ratio"] if metrics["Sharpe Ratio"] is not None else "N/A")

    # --- Dashboard charts ---
    st.subheader("4. Dashboard")
    fig = build_dashboard_figure(
        price_history, cumulative_return, benchmark_ticker, tickers, holdings_df
    )
    st.pyplot(fig)
    plt.close(fig)
# end of the code.this took around 3 office days of work or approx 6-7 days