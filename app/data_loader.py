"""Market data loading and PostgreSQL persistence utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
import pandas as pd
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
import yfinance as yf

from app.models import Base, HistoricalMarketData


logger = logging.getLogger(__name__)
REQUIRED_COLUMNS: tuple[str, ...] = ("Open", "High", "Low", "Close", "Adj Close", "Volume")


@dataclass(slots=True)
class MarketDataLoader:
    """Download historical market data and persist it to PostgreSQL."""

    database_url: str | None = None

    def get_engine(self) -> Engine:
        """Create and return a SQLAlchemy engine."""
        if not self.database_url:
            raise ValueError("A database URL is required for PostgreSQL operations.")
        return create_engine(self.database_url, future=True)

    def initialize_database(self) -> None:
        """Create database tables if they do not already exist."""
        try:
            engine = self.get_engine()
            Base.metadata.create_all(engine)
            logger.info("Initialized QuantLab database schema.")
        except SQLAlchemyError as exc:
            logger.exception("Failed to initialize database schema.")
            raise RuntimeError("Unable to initialize the database schema.") from exc

    def fetch_market_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Download daily OHLCV data for a ticker and normalize the result."""
        try:
            logger.info("Downloading market data for ticker=%s from %s to %s.", ticker, start_date, end_date)
            data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, progress=False)
        except Exception as exc:
            logger.exception("Market data download failed for ticker=%s.", ticker)
            raise RuntimeError(f"Unable to download market data for ticker={ticker!r}.") from exc

        if data.empty:
            logger.warning("No market data returned for ticker=%s.", ticker)
            raise ValueError(f"No market data returned for ticker={ticker!r}.")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        normalized = data.loc[:, [column for column in REQUIRED_COLUMNS if column in data.columns]].copy()
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in normalized.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        normalized.index = pd.to_datetime(normalized.index)
        normalized.index.name = "date"
        normalized["ticker"] = ticker.upper()
        return normalized

    def save_market_data(self, data: pd.DataFrame) -> int:
        """Upsert normalized market data into PostgreSQL."""
        if data.empty:
            logger.info("Skipping database write because the market data frame is empty.")
            return 0

        frame = self._prepare_storage_frame(data)
        records = frame.to_dict(orient="records")

        statement = insert(HistoricalMarketData).values(records)
        upsert_statement = statement.on_conflict_do_update(
            index_elements=["ticker", "date"],
            set_={
                "open": statement.excluded.open,
                "high": statement.excluded.high,
                "low": statement.excluded.low,
                "close": statement.excluded.close,
                "adj_close": statement.excluded.adj_close,
                "volume": statement.excluded.volume,
                "updated_at": func.now(),
            },
        )

        try:
            engine = self.get_engine()
            with Session(engine) as session:
                session.execute(upsert_statement)
                session.commit()
        except SQLAlchemyError as exc:
            logger.exception("Failed to upsert %s market data rows.", len(records))
            raise RuntimeError("Unable to store market data in PostgreSQL.") from exc

        logger.info("Stored %s market data rows for ticker=%s.", len(records), frame.iloc[0]["ticker"])
        return len(records)

    def fetch_and_store_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Download market data for a ticker and upsert it into PostgreSQL."""
        data = self.fetch_market_data(ticker=ticker, start_date=start_date, end_date=end_date)
        self.save_market_data(data)
        return data

    def load_data_from_db(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Load market data for a ticker and date range from PostgreSQL."""
        try:
            engine = self.get_engine()
            statement = (
                select(HistoricalMarketData)
                .where(HistoricalMarketData.ticker == ticker.upper())
                .where(HistoricalMarketData.date >= self._coerce_date(start_date))
                .where(HistoricalMarketData.date <= self._coerce_date(end_date))
                .order_by(HistoricalMarketData.date.asc())
            )
            with Session(engine) as session:
                rows = session.execute(statement).scalars().all()
        except SQLAlchemyError as exc:
            logger.exception("Failed to load market data for ticker=%s from PostgreSQL.", ticker)
            raise RuntimeError("Unable to load market data from PostgreSQL.") from exc

        if not rows:
            logger.info("No stored market data found for ticker=%s.", ticker)
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume", "ticker"])

        frame = pd.DataFrame(
            [
                {
                    "date": row.date,
                    "Open": row.open,
                    "High": row.high,
                    "Low": row.low,
                    "Close": row.close,
                    "Adj Close": row.adj_close,
                    "Volume": row.volume,
                    "ticker": row.ticker,
                }
                for row in rows
            ]
        )
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date")
        frame.index.name = "date"
        return frame

    @staticmethod
    def _prepare_storage_frame(data: pd.DataFrame) -> pd.DataFrame:
        """Convert a normalized market-data frame into database-ready columns."""
        MarketDataLoader.validate_market_data(data)
        frame = data.reset_index().rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        frame["ticker"] = frame["ticker"].astype(str).str.upper()
        frame["volume"] = frame["volume"].fillna(0).astype(int)
        return frame.loc[:, ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]]

    @staticmethod
    def validate_market_data(data: pd.DataFrame) -> None:
        """Validate the minimum structure required for storage and backtests."""
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
        if missing_columns:
            raise ValueError(f"Market data is missing columns: {missing_columns}")

        if data.empty:
            raise ValueError("Market data cannot be empty.")

    @staticmethod
    def _coerce_date(value: str | date | datetime) -> date:
        """Coerce a string or datetime-like value to a plain date."""
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return pd.Timestamp(value).date()


def fetch_and_store_data(
    ticker: str,
    start_date: str,
    end_date: str,
    database_url: str | None = None,
) -> pd.DataFrame:
    """Convenience function to download market data and upsert it into PostgreSQL."""
    loader = MarketDataLoader(database_url=database_url)
    return loader.fetch_and_store_data(ticker=ticker, start_date=start_date, end_date=end_date)


def load_data_from_db(
    ticker: str,
    start_date: str,
    end_date: str,
    database_url: str | None = None,
) -> pd.DataFrame:
    """Convenience function to load market data from PostgreSQL."""
    loader = MarketDataLoader(database_url=database_url)
    return loader.load_data_from_db(ticker=ticker, start_date=start_date, end_date=end_date)
