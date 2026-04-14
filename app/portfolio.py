"""Portfolio accounting models used by the backtest engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Trade:
    """A single executed trade."""

    timestamp: str
    ticker: str
    side: str
    quantity: float
    price: float
    fee: float
    cash_after: float


@dataclass(slots=True)
class PortfolioSnapshot:
    """Daily snapshot of portfolio state."""

    timestamp: str
    cash: float
    position_units: float
    market_value: float
    total_equity: float
    signal: float


@dataclass(slots=True)
class PortfolioTracker:
    """Track cash, holdings, equity, and executed trades."""

    initial_capital: float
    fee_rate: float = 0.001
    cash: float = field(init=False)
    position_units: float = field(default=0.0, init=False)
    trades: list[Trade] = field(default_factory=list, init=False)
    history: list[PortfolioSnapshot] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        """Initialize cash from the starting capital."""
        self.cash = float(self.initial_capital)

    def rebalance_to_target(self, timestamp: str, ticker: str, price: float, target_weight: float) -> None:
        """Rebalance the portfolio to a long-only target weight."""
        if price <= 0:
            raise ValueError("Price must be positive for portfolio updates.")

        target_weight = float(max(0.0, min(1.0, target_weight)))
        current_equity = self.total_equity(price)
        if target_weight > 0.0:
            target_notional = (current_equity * target_weight) / (1.0 + self.fee_rate)
        else:
            target_notional = 0.0
        target_units = target_notional / price
        delta_units = target_units - self.position_units

        if abs(delta_units) < 1e-12:
            return

        trade_notional = delta_units * price
        fee = abs(trade_notional) * self.fee_rate
        self.cash -= trade_notional + fee
        self.position_units = target_units

        self.trades.append(
            Trade(
                timestamp=timestamp,
                ticker=ticker,
                side="BUY" if delta_units > 0 else "SELL",
                quantity=abs(delta_units),
                price=price,
                fee=fee,
                cash_after=self.cash,
            )
        )

    def record_snapshot(self, timestamp: str, price: float, signal: float) -> None:
        """Record a time-indexed snapshot of the portfolio."""
        market_value = self.position_units * price
        self.history.append(
            PortfolioSnapshot(
                timestamp=timestamp,
                cash=self.cash,
                position_units=self.position_units,
                market_value=market_value,
                total_equity=self.cash + market_value,
                signal=float(signal),
            )
        )

    def total_equity(self, price: float) -> float:
        """Return the current total equity given a mark price."""
        return self.cash + self.position_units * price
