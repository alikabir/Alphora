"""Shared strategy abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


REQUIRED_MARKET_COLUMNS: tuple[str, ...] = ("Open", "High", "Low", "Close", "Volume")


class StrategyBase(ABC):
    """Abstract base class for target-position trading strategies."""

    name: str = "Strategy"

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return an index-aligned target position series in the range [0, 1]."""

    @staticmethod
    def validate_market_data(data: pd.DataFrame) -> None:
        """Validate the minimum market data structure strategies rely on."""
        if data.empty:
            raise ValueError("Input market data cannot be empty.")

        missing_columns = [column for column in REQUIRED_MARKET_COLUMNS if column not in data.columns]
        if missing_columns:
            raise ValueError(f"Input market data is missing columns: {missing_columns}")
