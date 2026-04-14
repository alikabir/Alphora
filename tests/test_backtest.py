"""Scenario tests for the core backtest engine."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.backtest import BacktestEngine
from strategies.base import StrategyBase
from strategies.sma_crossover import SMACrossoverStrategy


def make_market_data(close_prices: list[float]) -> pd.DataFrame:
    """Create deterministic OHLCV market data from close prices."""
    close = np.array(close_prices, dtype=float)
    index = pd.date_range("2024-01-01", periods=len(close), freq="D")
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Adj Close": close,
            "Volume": np.full(len(close), 100_000),
            "ticker": "TEST",
        },
        index=index,
    )


@dataclass(slots=True)
class FixedSignalStrategy(StrategyBase):
    """Return a fixed long/flat signal series for testing."""

    fixed_signal: float = 0.0
    name: str = "Fixed Signal"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return a constant signal aligned to the provided index."""
        self.validate_market_data(data)
        return pd.Series(self.fixed_signal, index=data.index, dtype=float, name="signal")


def test_no_trade_case_keeps_equity_flat() -> None:
    """No-trade strategies should keep equity unchanged and record no trades."""
    data = make_market_data([100.0, 101.0, 102.0, 103.0])
    engine = BacktestEngine(initial_capital=10_000.0, fee_rate=0.001)
    result = engine.run(data=data, strategy=FixedSignalStrategy(fixed_signal=0.0))

    assert result.trades.empty
    assert (result.positions == 0.0).all()
    assert (result.equity_curve == 10_000.0).all()
    assert result.metrics["total_return"] == 0.0
    assert result.metrics["win_rate"] == 0.0


def test_always_long_case_tracks_market_with_initial_transaction_cost() -> None:
    """An always-long strategy should follow price changes after entry."""
    data = make_market_data([100.0, 110.0, 121.0, 133.1])
    engine = BacktestEngine(initial_capital=10_000.0, fee_rate=0.001)
    result = engine.run(data=data, strategy=FixedSignalStrategy(fixed_signal=1.0))

    assert len(result.trades) == 1
    assert result.trades.iloc[0]["side"] == "BUY"
    assert result.positions.iloc[0] == 0.0
    assert (result.positions.iloc[1:] == 1.0).all()
    assert result.equity_curve.iloc[-1] > 10_000.0
    assert result.metrics["total_return"] > 0.0


def test_crossover_signal_case_generates_round_trip_trades() -> None:
    """A crossover strategy should generate long/flat transitions and completed trades."""
    data = make_market_data(
        [100.0, 99.0, 98.0, 97.0, 98.0, 100.0, 103.0, 105.0, 103.0, 100.0, 97.0, 95.0]
    )
    engine = BacktestEngine(initial_capital=25_000.0, fee_rate=0.001)
    strategy = SMACrossoverStrategy(fast_window=2, slow_window=4)
    result = engine.run(data=data, strategy=strategy)

    assert not result.trades.empty
    assert "BUY" in set(result.trades["side"])
    assert "SELL" in set(result.trades["side"])
    assert result.metrics["win_rate"] >= 0.0
    assert len(result.equity_curve) == len(data)


def test_transaction_cost_reduces_final_equity() -> None:
    """Higher transaction costs should reduce final equity for the same signals."""
    data = make_market_data([100.0, 103.0, 101.0, 104.0, 102.0, 106.0, 103.0, 107.0])
    strategy = SMACrossoverStrategy(fast_window=2, slow_window=3)

    low_cost_result = BacktestEngine(initial_capital=10_000.0, fee_rate=0.0).run(data=data, strategy=strategy)
    high_cost_result = BacktestEngine(initial_capital=10_000.0, fee_rate=0.01).run(data=data, strategy=strategy)

    assert high_cost_result.equity_curve.iloc[-1] < low_cost_result.equity_curve.iloc[-1]
    assert high_cost_result.metrics["total_return"] < low_cost_result.metrics["total_return"]
