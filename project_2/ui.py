import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from calculations import build_holdings_table, calculate_performance_metrics
from charts import build_dashboard_figure
from data import fetch_price_history, get_current_prices, load_all_tickers

REQUIRED_COLUMNS = ["Ticker", "Shares Owned", "Price Paid ($)", "Weight (%)"]


def read_holdings_input():
    input_method = st.radio(
        "How do you want to enter your portfolio?",
        ["Upload a CSV file", "Type it in manually"],
        horizontal=True,
    )
    if input_method == "Upload a CSV file":
        st.caption("CSV must have these exact column headers: " + ", ".join(REQUIRED_COLUMNS))
        template_csv = pd.DataFrame({
            "Ticker": ["AAPL", "MSFT", "SPY"],
            "Shares Owned": [10.0, 5.0, 8.0],
            "Price Paid ($)": [150.0, 280.0, 400.0],
            "Weight (%)": [40, 35, 25],
        }).to_csv(index=False)
        st.download_button("Download CSV template", template_csv, file_name="portfolio_template.csv")
        uploaded_file = st.file_uploader("Upload your portfolio CSV", type=["csv"])
        if uploaded_file is None:
            return None
        try:
            csv_data = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"Couldn't read that file: {exc}")
            st.stop()
        missing = [column for column in REQUIRED_COLUMNS if column not in csv_data.columns]
        if missing:
            st.error(f"CSV is missing required column(s): {', '.join(missing)}")
            st.stop()
        holdings_input = csv_data[REQUIRED_COLUMNS]
        st.write("Preview of what was uploaded:")
        st.dataframe(holdings_input, use_container_width=True, hide_index=True)
        return holdings_input

    st.caption("Add a row per asset. Weight (%) is just for your own reference.")
    return st.data_editor(
        pd.DataFrame(columns=REQUIRED_COLUMNS),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Ticker": st.column_config.SelectboxColumn(
                "Ticker",
                options=load_all_tickers(),
                help="Start typing to search - thousands of US-listed tickers.",
                required=True,
            ),
        },
    )


def run_analysis(holdings_input, benchmark_ticker, history_period):
    if holdings_input is None or len(holdings_input) == 0:
        st.warning("Upload a CSV or add at least one holding before running the analysis.")
        st.stop()
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
    for column in ["Shares Owned", "Price Paid ($)", "Weight (%)"]:
        holdings_input[column] = pd.to_numeric(holdings_input[column], errors="coerce")
    if holdings_input[["Shares Owned", "Price Paid ($)", "Weight (%)"]].isna().any().any():
        st.error("Shares Owned, Price Paid ($), and Weight (%) must contain valid numbers.")
        st.stop()

    with st.spinner("Fetching prices..."):
        try:
            all_tickers = list(dict.fromkeys(tickers + [benchmark_ticker]))
            price_history = fetch_price_history(all_tickers, history_period)
            current_prices = get_current_prices(tickers)
        except Exception as exc:
            st.error(f"Couldn't fetch market data: {exc}")
            st.stop()

    st.subheader("2. Profit / Loss")
    try:
        holdings_df, total_value = build_holdings_table(holdings_input, current_prices)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    st.dataframe(holdings_df, use_container_width=True, hide_index=True)
    total_cost = holdings_df["Cost Basis Total"].sum()
    total_pl = holdings_df["Profit/Loss ($)"].sum()
    total_pl_pct = total_pl / total_cost * 100 if total_cost else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Portfolio Value", f"${total_value:,.2f}")
    m2.metric("Total Profit/Loss", f"${total_pl:,.2f}", f"{total_pl_pct:.2f}%")
    m3.metric("Total Cost Basis", f"${total_cost:,.2f}")

    st.subheader("3. Performance Metrics")
    _, cumulative_return, metrics = calculate_performance_metrics(price_history[tickers], holdings_df)
    p1, p2, p3 = st.columns(3)
    p1.metric("Annualized Return", f'{metrics["Annualized Return"]}%')
    p2.metric("Annualized Volatility", f'{metrics["Annualized Volatility"]}%')
    p3.metric("Sharpe Ratio", metrics["Sharpe Ratio"] if metrics["Sharpe Ratio"] is not None else "N/A")

    st.subheader("4. Dashboard")
    figure = build_dashboard_figure(price_history, cumulative_return, benchmark_ticker, tickers, holdings_df)
    st.pyplot(figure)
    plt.close(figure)


def run_app():
    st.set_page_config(page_title="Portfolio Manager", layout="wide")
    st.markdown(
        """<style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        </style>""",
        unsafe_allow_html=True,
    )
    st.title("Portfolio Manager")
    st.write(
        "Enter what you own below, then click **Run Analysis**. "
        "This tool reports your current profit/loss and performance - "
        "it does not recommend trades."
    )
    st.subheader("1. Your Holdings")
    holdings_input = read_holdings_input()
    col_a, col_b = st.columns(2)
    with col_a:
        benchmark_ticker = st.text_input("Benchmark ticker", value="SPY")
    with col_b:
        history_period = st.selectbox("History period", ["6mo", "1y", "2y", "5y"], index=1)
    if st.button("Run Analysis", type="primary"):
        run_analysis(holdings_input, benchmark_ticker, history_period)
