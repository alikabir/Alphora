"""Simple backtesting engine for long/flat strategy evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.metrics import summarize_performance, win_rate
from strategies.base import StrategyBase


@dataclass(slots=True)
class BacktestResult:
    """Structured output for a completed backtest run."""

    signals: pd.Series
    positions: pd.Series
    daily_returns: pd.Series
    equity_curve: pd.Series
    portfolio_history: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


@dataclass(slots=True)
class BacktestEngine:
    """Run a simple long/flat backtest driven by target position signals."""

    initial_capital: float = 100_000.0
    fee_rate: float = 0.001
    ticker_column: str = "ticker"
    close_column: str = "Close"

    def run(self, data: pd.DataFrame, strategy: StrategyBase) -> BacktestResult:
        """Execute a strategy on OHLCV data and calculate portfolio results."""
        strategy.validate_market_data(data)
        close_prices = data[self.close_column].astype(float)
        signals = strategy.generate_signals(data).reindex(data.index).fillna(0.0).clip(0.0, 1.0)
        signals.name = "signal"
        positions = signals.shift(1).fillna(0.0).astype(float)
        positions.name = "position"

        asset_returns = close_prices.pct_change().fillna(0.0)
        asset_returns.name = "asset_return"
        position_changes = positions.diff().abs().fillna(positions.abs())
        position_changes.name = "turnover"

        gross_returns = positions * asset_returns
        transaction_costs = position_changes * self.fee_rate
        net_returns = gross_returns - transaction_costs
        net_returns.name = "daily_return"

        equity_curve = (1.0 + net_returns).cumprod() * float(self.initial_capital)
        equity_curve.name = "equity"

        ticker = self._resolve_ticker(data)
        portfolio_history = pd.DataFrame(
            {
                "close": close_prices,
                "signal": signals,
                "position": positions,
                "asset_return": asset_returns,
                "daily_return": net_returns,
                "equity": equity_curve,
            }
        )

        trades = self._build_trades_table(
            close_prices=close_prices,
            positions=positions,
            position_changes=position_changes,
            equity_curve=equity_curve,
            ticker=ticker,
        )
        metrics = summarize_performance(equity_curve)
        if not trades.empty and "pnl_pct" in trades.columns:
            completed_trade_returns = trades.loc[trades["side"] == "SELL", "pnl_pct"].astype(float)
            metrics["win_rate"] = win_rate(completed_trade_returns)

        return BacktestResult(
            signals=signals,
            positions=positions,
            daily_returns=net_returns,
            equity_curve=equity_curve,
            portfolio_history=portfolio_history,
            trades=trades,
            metrics=metrics,
        )

    def _build_trades_table(
        self,
        close_prices: pd.Series,
        positions: pd.Series,
        position_changes: pd.Series,
        equity_curve: pd.Series,
        ticker: str,
    ) -> pd.DataFrame:
        """Build a round-trip-oriented trade log from position changes."""
        trade_rows: list[dict[str, float | str]] = []
        open_trade: dict[str, float | str] | None = None

        for timestamp in close_prices.index:
            new_position = float(positions.loc[timestamp])
            turnover = float(position_changes.loc[timestamp])
            if turnover == 0.0:
                continue

            price = float(close_prices.loc[timestamp])
            equity = float(equity_curve.loc[timestamp])
            quantity = equity / price if new_position > 0.0 else 0.0

            if new_position > 0.0:
                entry_cost = equity * self.fee_rate
                open_trade = {
                    "timestamp": str(timestamp),
                    "ticker": ticker,
                    "side": "BUY",
                    "price": price,
                    "quantity": quantity,
                    "transaction_cost": entry_cost,
                    "pnl": 0.0,
                    "pnl_pct": 0.0,
                }
                trade_rows.append(open_trade.copy())
                continue

            entry_price = float(open_trade["price"]) if open_trade else price
            exit_cost = equity * self.fee_rate
            gross_pnl = float((price - entry_price) * float(open_trade["quantity"])) if open_trade else 0.0
            total_cost = float(open_trade["transaction_cost"]) + exit_cost if open_trade else exit_cost
            pnl = gross_pnl - total_cost
            pnl_pct = (pnl / (entry_price * float(open_trade["quantity"]))) if open_trade else 0.0
            trade_rows.append(
                {
                    "timestamp": str(timestamp),
                    "ticker": ticker,
                    "side": "SELL",
                    "price": price,
                    "quantity": float(open_trade["quantity"]) if open_trade else 0.0,
                    "transaction_cost": exit_cost,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                }
            )
            open_trade = None

        return pd.DataFrame(trade_rows)

    def _resolve_ticker(self, data: pd.DataFrame) -> str:
        """Resolve the instrument label from either `ticker` or legacy `symbol` columns."""
        for column in (self.ticker_column, "symbol"):
            if column in data.columns:
                return str(data[column].iloc[0]).upper()
        return "UNKNOWN"
