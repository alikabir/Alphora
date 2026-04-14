"""Simple momentum strategy."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from strategies.base import StrategyBase


@dataclass(slots=True)
class MomentumStrategy(StrategyBase):
    """Go long when trailing returns exceed a threshold."""

    lookback_period: int = 20
    threshold: float = 0.0
    name: str = "Momentum"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate target signals from trailing momentum."""
        self.validate_market_data(data)
        close = data["Close"].astype(float)
        momentum = close.pct_change(periods=self.lookback_period)
        signal = (momentum > self.threshold).astype(float).fillna(0.0)
        signal.name = "signal"
        return signal
