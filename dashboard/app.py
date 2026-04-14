"""Minimal Streamlit dashboard for QuantLab backtests."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.backtest import BacktestResult, BacktestEngine
from app.config import Settings
from app.data_loader import MarketDataLoader
from strategies import MomentumStrategy, RSIMeanReversionStrategy, SMACrossoverStrategy
from strategies.base import StrategyBase


STRATEGY_OPTIONS: tuple[str, ...] = ("SMA Crossover", "RSI Mean Reversion", "Momentum")


def format_pct(value: float) -> str:
    """Format a decimal value as a percentage string."""
    return f"{value * 100:.2f}%"


def build_strategy(strategy_name: str) -> StrategyBase:
    """Build a strategy from sidebar inputs."""
    st.sidebar.markdown("### Strategy Parameters")

    if strategy_name == "SMA Crossover":
        fast_window = st.sidebar.slider("Fast Window", min_value=5, max_value=50, value=20)
        slow_window = st.sidebar.slider("Slow Window", min_value=20, max_value=200, value=50)
        return SMACrossoverStrategy(fast_window=fast_window, slow_window=slow_window)

    if strategy_name == "RSI Mean Reversion":
        rsi_window = st.sidebar.slider("RSI Window", min_value=5, max_value=30, value=14)
        oversold = st.sidebar.slider("Oversold Threshold", min_value=10, max_value=40, value=30)
        overbought = st.sidebar.slider("Overbought Threshold", min_value=60, max_value=90, value=70)
        return RSIMeanReversionStrategy(
            rsi_window=rsi_window,
            oversold_threshold=float(oversold),
            overbought_threshold=float(overbought),
        )

    lookback_period = st.sidebar.slider("Lookback Period", min_value=5, max_value=120, value=20)
    threshold = st.sidebar.number_input("Momentum Threshold", min_value=-1.0, max_value=1.0, value=0.0, step=0.01)
    return MomentumStrategy(lookback_period=lookback_period, threshold=float(threshold))


def build_drawdown_series(equity_curve: pd.Series) -> pd.Series:
    """Build a drawdown series from an equity curve."""
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    drawdown.name = "drawdown"
    return drawdown


def render_metric_cards(metrics: dict[str, float]) -> None:
    """Render a compact row of backtest metrics."""
    total_return, annualized_return, volatility = st.columns(3)
    sharpe_ratio, max_drawdown, win_rate = st.columns(3)

    total_return.metric("Total Return", format_pct(metrics["total_return"]))
    annualized_return.metric("Annualized Return", format_pct(metrics["annualized_return"]))
    volatility.metric("Volatility", format_pct(metrics["volatility"]))
    sharpe_ratio.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    max_drawdown.metric("Max Drawdown", format_pct(metrics["max_drawdown"]))
    win_rate.metric("Win Rate", format_pct(metrics["win_rate"]))


def render_recent_trades(result: BacktestResult) -> None:
    """Render the recent trades table."""
    st.subheader("Recent Trades")
    if result.trades.empty:
        st.info("No trades were generated for the selected configuration.")
        return

    recent_trades = result.trades.copy().tail(10)
    st.dataframe(recent_trades, use_container_width=True)


def run_backtest(
    ticker: str,
    start_date: date,
    end_date: date,
    strategy_name: str,
    initial_capital: float,
    fee_rate: float,
    settings: Settings,
) -> tuple[pd.DataFrame, BacktestResult]:
    """Load market data and run the requested backtest."""
    loader = MarketDataLoader(database_url=settings.database_url)
    strategy = build_strategy(strategy_name)
    data = loader.fetch_market_data(ticker=ticker, start_date=start_date.isoformat(), end_date=end_date.isoformat())
    engine = BacktestEngine(initial_capital=initial_capital, fee_rate=fee_rate)
    result = engine.run(data=data, strategy=strategy)
    return data, result


def main() -> None:
    """Render the QuantLab dashboard."""
    settings = Settings()

    st.set_page_config(page_title="QuantLab", layout="wide")
    st.title("QuantLab")
    st.caption("Minimal research dashboard for strategy backtests")

    st.sidebar.header("Backtest Setup")
    ticker = st.sidebar.text_input("Ticker", value=settings.default_symbol).upper().strip()
    start_date = st.sidebar.date_input("Start Date", value=pd.Timestamp(settings.default_start))
    end_date = st.sidebar.date_input("End Date", value=pd.Timestamp(settings.default_end))
    strategy_name = st.sidebar.selectbox("Strategy", options=STRATEGY_OPTIONS)
    initial_capital = st.sidebar.number_input(
        "Initial Capital",
        min_value=1_000.0,
        value=float(settings.initial_capital),
        step=1_000.0,
    )
    transaction_cost = st.sidebar.number_input(
        "Transaction Cost",
        min_value=0.0,
        max_value=0.05,
        value=float(settings.fee_rate),
        step=0.0005,
        format="%.4f",
    )

    run_clicked = st.sidebar.button("Run Backtest", type="primary", use_container_width=True)

    if not run_clicked:
        st.info("Choose a ticker, date range, strategy, and transaction cost to run a backtest.")
        return

    if not ticker:
        st.error("Please provide a ticker symbol.")
        return

    if start_date >= end_date:
        st.error("The start date must be earlier than the end date.")
        return

    try:
        data, result = run_backtest(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            strategy_name=strategy_name,
            initial_capital=float(initial_capital),
            fee_rate=float(transaction_cost),
            settings=settings,
        )
    except Exception as exc:
        st.error(f"Backtest failed: {exc}")
        return

    drawdown = build_drawdown_series(result.equity_curve)

    render_metric_cards(result.metrics)

    left, right = st.columns(2)
    with left:
        st.subheader("Equity Curve")
        st.line_chart(result.equity_curve, use_container_width=True)

    with right:
        st.subheader("Drawdown")
        st.area_chart(drawdown, use_container_width=True)

    render_recent_trades(result)

    with st.expander("Diagnostics", expanded=False):
        st.dataframe(
            data.tail(15)[["Open", "High", "Low", "Close", "Adj Close", "Volume"]],
            use_container_width=True,
        )
        st.dataframe(result.portfolio_history.tail(15), use_container_width=True)


if __name__ == "__main__":
    main()
