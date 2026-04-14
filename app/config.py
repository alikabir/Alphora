"""Configuration helpers for QuantLab."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    """Application settings with sensible local defaults."""

    database_url: str = os.getenv(
        "QUANTLAB_DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/quantlab",
    )
    initial_capital: float = 100_000.0
    fee_rate: float = 0.001
    default_symbol: str = "AAPL"
    default_start: str = "2020-01-01"
    default_end: str = "2024-01-01"
