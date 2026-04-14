"""Simple moving average crossover strategy."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from strategies.base import StrategyBase


@dataclass(slots=True)
class SMACrossoverStrategy(StrategyBase):
    """Go long when the fast SMA is above the slow SMA."""

    fast_window: int = 20
    slow_window: int = 50
    name: str = "SMA Crossover"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate long-only signals from moving-average crossovers."""
        self.validate_market_data(data)
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window.")

        close = data["Close"].astype(float)
        fast_sma = close.rolling(window=self.fast_window, min_periods=self.fast_window).mean()
        slow_sma = close.rolling(window=self.slow_window, min_periods=self.slow_window).mean()
        signal = (fast_sma > slow_sma).astype(float).fillna(0.0)
        signal.name = "signal"
        return signal
