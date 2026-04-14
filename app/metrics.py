"""Performance metrics for strategy evaluation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_returns(equity_curve: pd.Series) -> pd.Series:
    """Compute periodic returns from an equity curve."""
    returns = equity_curve.pct_change().fillna(0.0)
    returns.name = "returns"
    return returns


def win_rate(trade_returns: pd.Series) -> float:
    """Compute the fraction of profitable round-trip trades."""
    if trade_returns.empty:
        return 0.0
    return float((trade_returns > 0.0).mean())


def cumulative_return(equity_curve: pd.Series) -> float:
    """Compute total return over the full backtest period."""
    if equity_curve.empty:
        return 0.0
    starting_equity = float(equity_curve.iloc[0])
    ending_equity = float(equity_curve.iloc[-1])
    if starting_equity == 0.0:
        return 0.0
    return (ending_equity / starting_equity) - 1.0


def annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Compute annualized return from periodic returns."""
    if returns.empty:
        return 0.0
    compounded = float((1.0 + returns).prod())
    periods = len(returns)
    if periods == 0 or compounded <= 0:
        return 0.0
    return compounded ** (periods_per_year / periods) - 1.0


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Compute annualized volatility."""
    if len(returns) < 2:
        return 0.0
    return float(returns.std(ddof=0) * np.sqrt(periods_per_year))


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """Compute the annualized Sharpe ratio."""
    if returns.empty:
        return 0.0
    excess_returns = returns - (risk_free_rate / periods_per_year)
    volatility = annualized_volatility(excess_returns, periods_per_year=periods_per_year)
    if volatility == 0.0:
        return 0.0
    return float(excess_returns.mean() * periods_per_year / volatility)


def max_drawdown(equity_curve: pd.Series) -> float:
    """Compute the maximum drawdown from an equity curve."""
    if equity_curve.empty:
        return 0.0
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    return float(drawdown.min())


def summarize_performance(equity_curve: pd.Series) -> dict[str, float]:
    """Return a compact performance summary for a completed backtest."""
    returns = compute_returns(equity_curve)
    return {
        "total_return": cumulative_return(equity_curve),
        "annualized_return": annualized_return(returns),
        "volatility": annualized_volatility(returns),
        "sharpe_ratio": sharpe_ratio(returns),
        "max_drawdown": max_drawdown(equity_curve),
        "win_rate": 0.0,
    }
