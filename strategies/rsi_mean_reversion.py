"""RSI-based mean reversion strategy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from strategies.base import StrategyBase


@dataclass(slots=True)
class RSIMeanReversionStrategy(StrategyBase):
    """Go long on oversold conditions and exit on overbought conditions."""

    rsi_window: int = 14
    oversold_threshold: float = 30.0
    overbought_threshold: float = 70.0
    name: str = "RSI Mean Reversion"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate long-only signals based on RSI thresholds."""
        self.validate_market_data(data)
        close = data["Close"].astype(float)
        delta = close.diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_gain = gains.rolling(window=self.rsi_window, min_periods=self.rsi_window).mean()
        avg_loss = losses.rolling(window=self.rsi_window, min_periods=self.rsi_window).mean()
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi = rsi.fillna(50.0)

        signal = pd.Series(0.0, index=data.index, name="signal")
        current_position = 0.0
        for timestamp, value in rsi.items():
            if value <= self.oversold_threshold:
                current_position = 1.0
            elif value >= self.overbought_threshold:
                current_position = 0.0
            signal.loc[timestamp] = current_position
        return signal
