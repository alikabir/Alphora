"""Tests for the PostgreSQL market data storage layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.data_loader import MarketDataLoader, fetch_and_store_data, load_data_from_db


def make_download_frame() -> pd.DataFrame:
    """Create a deterministic yfinance-like data frame."""
    index = pd.date_range("2024-01-01", periods=3, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 102.0, 103.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.5, 101.5, 102.5],
            "Adj Close": [100.4, 101.4, 102.4],
            "Volume": [1_000, 1_100, 1_200],
        },
        index=index,
    )


def test_fetch_market_data_normalizes_yfinance_output(monkeypatch) -> None:
    """Downloaded data should be normalized into QuantLab's expected shape."""
    monkeypatch.setattr("app.data_loader.yf.download", lambda *args, **kwargs: make_download_frame())
    loader = MarketDataLoader(database_url="postgresql+psycopg2://user:pass@localhost:5432/quantlab")

    result = loader.fetch_market_data(ticker="aapl", start_date="2024-01-01", end_date="2024-01-31")

    assert list(result.columns) == ["Open", "High", "Low", "Close", "Adj Close", "Volume", "ticker"]
    assert result.index.name == "date"
    assert set(result["ticker"]) == {"AAPL"}


def test_prepare_storage_frame_matches_model_shape() -> None:
    """Storage normalization should match the SQLAlchemy model fields."""
    raw = make_download_frame()
    raw["ticker"] = "MSFT"
    raw.index.name = "date"

    frame = MarketDataLoader._prepare_storage_frame(raw)

    assert list(frame.columns) == ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]
    assert frame["ticker"].tolist() == ["MSFT", "MSFT", "MSFT"]
    assert isinstance(frame.iloc[0]["date"], date)


def test_fetch_and_store_data_calls_save(monkeypatch) -> None:
    """The combined helper should download then persist the normalized frame."""
    expected = make_download_frame()
    expected["ticker"] = "NVDA"
    expected.index.name = "date"
    loader = MarketDataLoader(database_url="postgresql+psycopg2://user:pass@localhost:5432/quantlab")
    captured: dict[str, pd.DataFrame] = {}

    def fake_fetch(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        assert ticker == "NVDA"
        assert start_date == "2024-01-01"
        assert end_date == "2024-01-10"
        return expected

    def fake_save(self, data: pd.DataFrame) -> int:
        captured["data"] = data
        return len(data)

    monkeypatch.setattr(MarketDataLoader, "fetch_market_data", fake_fetch)
    monkeypatch.setattr(MarketDataLoader, "save_market_data", fake_save)

    result = loader.fetch_and_store_data("NVDA", "2024-01-01", "2024-01-10")

    assert result.equals(expected)
    assert captured["data"].equals(expected)


def test_convenience_functions_delegate_to_loader(monkeypatch) -> None:
    """Module-level helpers should delegate to the loader instance methods."""
    expected = make_download_frame()
    expected["ticker"] = "TSLA"
    expected.index.name = "date"

    monkeypatch.setattr(
        MarketDataLoader,
        "fetch_and_store_data",
        lambda self, ticker, start_date, end_date: expected,
    )
    monkeypatch.setattr(
        MarketDataLoader,
        "load_data_from_db",
        lambda self, ticker, start_date, end_date: expected,
    )

    stored = fetch_and_store_data("TSLA", "2024-01-01", "2024-01-03", database_url="postgresql://example")
    loaded = load_data_from_db("TSLA", "2024-01-01", "2024-01-03", database_url="postgresql://example")

    assert stored.equals(expected)
    assert loaded.equals(expected)


def test_load_data_from_db_builds_expected_dataframe(monkeypatch) -> None:
    """Database rows should be converted into the expected OHLCV frame shape."""

    @dataclass
    class FakeRow:
        ticker: str
        date: date
        open: float
        high: float
        low: float
        close: float
        adj_close: float
        volume: int

    class FakeScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class FakeExecuteResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return FakeScalarResult(self._rows)

    class FakeSession:
        def __init__(self, rows):
            self._rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement):
            del statement
            return FakeExecuteResult(self._rows)

    rows = [
        FakeRow("AMD", date(2024, 1, 1), 100.0, 101.0, 99.0, 100.5, 100.4, 1_000),
        FakeRow("AMD", date(2024, 1, 2), 101.0, 102.0, 100.0, 101.5, 101.4, 1_100),
    ]

    monkeypatch.setattr(MarketDataLoader, "get_engine", lambda self: object())
    monkeypatch.setattr("app.data_loader.Session", lambda engine: FakeSession(rows))
    loader = MarketDataLoader(database_url="postgresql+psycopg2://user:pass@localhost:5432/quantlab")

    result = loader.load_data_from_db("AMD", "2024-01-01", "2024-01-02")

    assert list(result.columns) == ["Open", "High", "Low", "Close", "Adj Close", "Volume", "ticker"]
    assert result.index.name == "date"
    assert result.iloc[-1]["Close"] == 101.5
