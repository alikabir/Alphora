"""Tests for starter strategies."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies import MomentumStrategy, RSIMeanReversionStrategy, SMACrossoverStrategy


def make_market_data(length: int = 80) -> pd.DataFrame:
    """Create deterministic OHLCV data for tests."""
    index = pd.date_range("2024-01-01", periods=length, freq="D")
    close = np.linspace(100.0, 140.0, num=length)
    return pd.DataFrame(
        {
            "Open": close - 1.0,
            "High": close + 1.0,
            "Low": close - 2.0,
            "Close": close,
            "Adj Close": close,
            "Volume": np.full(length, 1_000_000),
            "ticker": "TEST",
        },
        index=index,
    )


def test_sma_crossover_returns_index_aligned_signals() -> None:
    """SMA crossover should output a clean long-only signal series."""
    data = make_market_data()
    strategy = SMACrossoverStrategy(fast_window=5, slow_window=10)
    signals = strategy.generate_signals(data)

    assert signals.index.equals(data.index)
    assert set(signals.unique()).issubset({0.0, 1.0})
    assert float(signals.iloc[-1]) == 1.0


def test_rsi_mean_reversion_returns_index_aligned_signals() -> None:
    """RSI strategy should preserve alignment and long-only outputs."""
    data = make_market_data()
    strategy = RSIMeanReversionStrategy()
    signals = strategy.generate_signals(data)

    assert signals.index.equals(data.index)
    assert set(signals.unique()).issubset({0.0, 1.0})


def test_momentum_returns_index_aligned_signals() -> None:
    """Momentum should turn long for rising series above the threshold."""
    data = make_market_data()
    strategy = MomentumStrategy(lookback_period=5, threshold=0.0)
    signals = strategy.generate_signals(data)

    assert signals.index.equals(data.index)
    assert set(signals.unique()).issubset({0.0, 1.0})
    assert float(signals.iloc[-1]) == 1.0
