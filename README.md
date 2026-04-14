# Alphora

QuantLab is a modular Python 3.11 quant trading research and backtesting platform. It includes historical market-data storage for PostgreSQL, reusable strategy abstractions, a lightweight backtest engine, performance metrics, portfolio tracking, and a Streamlit dashboard for quick local exploration.

## Features

- Modular research-oriented package layout
- `yfinance` market data loading with PostgreSQL upsert support
- Three starter strategies:
  - SMA crossover
  - RSI mean reversion
  - Momentum
- Backtest engine with portfolio tracking and trade logging
- Performance metrics for total return, annualized return, volatility, Sharpe ratio, max drawdown, and win rate
- Streamlit dashboard for ticker-driven experiments
- Pytest suite covering imports, strategies, portfolio behavior, metrics, and backtest flow

## Project Structure

```text
QuantLab/
|-- app/
|-- dashboard/
|-- notebooks/
|-- sql/
|-- strategies/
|-- tests/
|-- AGENTS.md
|-- README.md
`-- requirements.txt
```

## Prerequisites

- Python 3.11
- PostgreSQL 14+ if you want to persist market data locally

## Setup

1. Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Upgrade `pip` and install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Configure PostgreSQL access with an environment variable:

```powershell
$env:QUANTLAB_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/quantlab"
```

4. Initialize the storage schema:

```powershell
psql -d quantlab -f sql/market_data_schema.sql
```

5. Optional: create the SQLAlchemy-managed tables from Python instead:

```powershell
python demo_data_storage.py
```

## Running Tests

```powershell
pytest
```

## Running the Dashboard

```powershell
streamlit run dashboard/app.py
```

The dashboard lets you choose a ticker, date range, strategy configuration, and transaction cost, then displays performance cards, an equity curve, a drawdown chart, and recent trades.

## Example Usage

```python
from app.backtest import BacktestEngine
from app.config import Settings
from app.data_loader import MarketDataLoader
from strategies.sma_crossover import SMACrossoverStrategy

settings = Settings()
loader = MarketDataLoader(database_url=settings.database_url)
data = loader.fetch_market_data(ticker="AAPL", start_date="2022-01-01", end_date="2024-01-01")

strategy = SMACrossoverStrategy(fast_window=20, slow_window=50)
engine = BacktestEngine(initial_capital=settings.initial_capital, fee_rate=settings.fee_rate)
result = engine.run(data=data, strategy=strategy)

print(result.metrics)
print(result.equity_curve.tail())
```

## Data Storage Demo

```powershell
python demo_data_storage.py
```

The demo script creates the SQLAlchemy tables, downloads data with `yfinance`, upserts it into PostgreSQL, and loads the stored rows back into a pandas DataFrame.

## Final Local Run Checklist

1. Install Python 3.11 and PostgreSQL.
2. Create and activate a virtual environment.
3. Run `pip install -r requirements.txt`.
4. Set `QUANTLAB_DATABASE_URL`.
5. Run `pytest`.
6. Run `streamlit run dashboard/app.py`.

## Notes

- The starter engine assumes long-only target signals in the range `[0.0, 1.0]`.
- The market data schema is designed for daily OHLCV bars and can be extended for intraday data later.
- `notebooks/` is reserved for research exploration and intentionally kept lightweight in the initial scaffold.
