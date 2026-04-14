"""Smoke tests for package imports."""

from app.backtest import BacktestEngine, BacktestResult
from app.config import Settings
from app.data_loader import MarketDataLoader, fetch_and_store_data, load_data_from_db
from app.metrics import summarize_performance
from app.models import HistoricalMarketData
from app.portfolio import PortfolioTracker
from strategies import MomentumStrategy, RSIMeanReversionStrategy, SMACrossoverStrategy


def test_core_imports_are_available() -> None:
    """Ensure the core public imports remain stable."""
    assert Settings is not None
    assert MarketDataLoader is not None
    assert BacktestEngine is not None
    assert BacktestResult is not None
    assert summarize_performance is not None
    assert HistoricalMarketData is not None
    assert PortfolioTracker is not None
    assert fetch_and_store_data is not None
    assert load_data_from_db is not None
    assert SMACrossoverStrategy is not None
    assert RSIMeanReversionStrategy is not None
    assert MomentumStrategy is not None
