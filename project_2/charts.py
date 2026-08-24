import matplotlib.pyplot as plt


def build_dashboard_figure(
    price_history,
    cumulative_returns,
    benchmark_ticker,
    tickers,
    holdings_df,
):
    figure, axes = plt.subplots(2, 2, figsize=(14, 9))
    allocation = holdings_df.set_index("Ticker")["Current Weight (%)"]
    profit_loss = holdings_df.set_index("Ticker")["Profit/Loss ($)"]

    axes[0, 0].pie(
        allocation,
        labels=allocation.index,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"width": 0.45},
    )
    axes[0, 0].set_title("Current Portfolio Allocation")

    bar_colors = ["green" if value >= 0 else "red" for value in profit_loss]
    axes[0, 1].bar(profit_loss.index, profit_loss.values, color=bar_colors)
    axes[0, 1].axhline(0, color="black", linewidth=0.8)
    axes[0, 1].set(title="Profit/Loss by Holding", ylabel="Profit/Loss ($)")
    axes[0, 1].tick_params(axis="x", rotation=45)

    correlation_matrix = price_history[tickers].pct_change().dropna().corr()
    heatmap = axes[1, 0].imshow(correlation_matrix, cmap="coolwarm", vmin=-1, vmax=1)
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
                round(correlation_matrix.iloc[row_index, column_index], 2),
                ha="center",
                va="center",
            )
    figure.colorbar(heatmap, ax=axes[1, 0])

    benchmark_returns = price_history[benchmark_ticker].pct_change().dropna()
    benchmark_cumulative_returns = (1 + benchmark_returns).cumprod() - 1
    axes[1, 1].plot(cumulative_returns.index, cumulative_returns.values * 100, label="My Portfolio")
    axes[1, 1].plot(
        benchmark_cumulative_returns.index,
        benchmark_cumulative_returns.values * 100,
        label=f"Benchmark ({benchmark_ticker})",
        linestyle="--",
    )
    axes[1, 1].set(title="Cumulative Return: Portfolio vs. Benchmark", ylabel="Return (%)")
    axes[1, 1].legend()

    plt.tight_layout()
    return figure
