"""Small demo script for downloading and storing market data."""

from __future__ import annotations

import logging

from app.config import Settings
from app.data_loader import MarketDataLoader


def main() -> None:
    """Run a small end-to-end storage demo against the configured PostgreSQL database."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    settings = Settings()
    loader = MarketDataLoader(database_url=settings.database_url)

    loader.initialize_database()
    stored = loader.fetch_and_store_data(
        ticker=settings.default_symbol,
        start_date=settings.default_start,
        end_date=settings.default_end,
    )
    loaded = loader.load_data_from_db(
        ticker=settings.default_symbol,
        start_date=settings.default_start,
        end_date=settings.default_end,
    )

    print(f"Downloaded rows: {len(stored)}")
    print(f"Loaded rows from database: {len(loaded)}")
    if not loaded.empty:
        print(loaded.tail().to_string())


if __name__ == "__main__":
    main()
