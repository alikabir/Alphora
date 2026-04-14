"""Tests for metrics and portfolio accounting."""

from __future__ import annotations

import pandas as pd

from app.metrics import cumulative_return, max_drawdown, summarize_performance
from app.portfolio import PortfolioTracker


def test_metrics_summary_on_known_equity_curve() -> None:
    """Metrics should be deterministic on known inputs."""
    equity_curve = pd.Series([100_000.0, 105_000.0, 102_000.0, 110_000.0])
    summary = summarize_performance(equity_curve)

    assert round(cumulative_return(equity_curve), 4) == 0.1
    assert round(max_drawdown(equity_curve), 4) == -0.0286
    assert "sharpe_ratio" in summary


def test_portfolio_tracker_rebalances_and_records_history() -> None:
    """Portfolio tracker should update holdings, trades, and snapshots."""
    tracker = PortfolioTracker(initial_capital=100_000.0, fee_rate=0.001)
    tracker.rebalance_to_target(timestamp="2024-01-01", ticker="TEST", price=100.0, target_weight=1.0)
    tracker.record_snapshot(timestamp="2024-01-01", price=100.0, signal=1.0)
    tracker.rebalance_to_target(timestamp="2024-01-02", ticker="TEST", price=105.0, target_weight=0.0)
    tracker.record_snapshot(timestamp="2024-01-02", price=105.0, signal=0.0)

    assert len(tracker.trades) == 2
    assert len(tracker.history) == 2
    assert tracker.history[-1].total_equity > 0.0
