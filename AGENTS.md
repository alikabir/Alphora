# AGENTS.md

## Repository Purpose

Alphora is a modular quant trading research and backtesting scaffold focused on clean Python 3.11 code, readable abstractions, and easy local experimentation.

## Working Agreements

- Keep the repo importable from the repository root.
- Favor small, testable modules with explicit type hints and docstrings.
- Preserve the separation of concerns between:
  - `app/` for reusable platform code
  - `strategies/` for signal-generation logic
  - `dashboard/` for user-facing Streamlit code
  - `sql/` for database schema and SQL assets
  - `tests/` for deterministic automated coverage
- Prefer deterministic tests built from in-memory `pandas` data over network-dependent integration tests.
- Avoid adding new dependencies unless they materially improve the platform.

## Module Responsibilities

- `app/config.py`: environment-aware defaults and settings
- `app/data_loader.py`: price retrieval and persistence helpers
- `app/backtest.py`: backtest orchestration and result packaging
- `app/metrics.py`: performance calculations
- `app/portfolio.py`: holdings, cash, equity, and trade tracking
- `strategies/base.py`: strategy protocol and validation helpers
- `strategies/*.py`: concrete signal-generation strategies
- `dashboard/app.py`: interactive local dashboard

## Extension Guidance

- New strategies should inherit from `StrategyBase` and return index-aligned target position signals.
- Backtest behavior changes should keep portfolio accounting deterministic and covered by tests.
- Schema changes in `sql/` should be mirrored in loader persistence logic when applicable.
