"""Immutable account and portfolio state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from algotrader.core.types import Fill, OrderSide
from algotrader.core.validation import decimal_value, non_negative, symbol_value
from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class Account:
    cash: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        object.__setattr__(self, "cash", decimal_value(self.cash, "cash"))
        non_negative(self.cash, "cash")

        currency = self.currency.strip().upper()
        if not currency:
            raise ValidationError("currency is required.")
        object.__setattr__(self, "currency", currency)


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    quantity: Decimal
    average_price: Decimal

    @property
    def is_flat(self) -> bool:
        return self.quantity == 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(self, "quantity", decimal_value(self.quantity, "quantity"))
        object.__setattr__(
            self,
            "average_price",
            decimal_value(self.average_price, "average_price"),
        )
        non_negative(self.average_price, "average_price")


@dataclass(frozen=True, slots=True)
class RiskState:
    trading_enabled: bool = True
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PortfolioState:
    account: Account
    positions: tuple[Position, ...] = ()
    risk: RiskState = RiskState()
    timestamp: datetime | None = None

    def position(self, symbol: str) -> Position | None:
        normalized = symbol_value(symbol)
        return next(
            (position for position in self.positions if position.symbol == normalized),
            None,
        )


def apply_fill(state: PortfolioState, fill: Fill) -> PortfolioState:
    """Return a new portfolio state after applying a fill."""

    existing = state.position(fill.symbol)
    current_quantity = existing.quantity if existing else Decimal("0")
    current_average = existing.average_price if existing else Decimal("0")

    if fill.side == OrderSide.BUY:
        new_cash = state.account.cash - fill.notional
        if new_cash < 0:
            raise ValidationError("fill would make cash negative.")
        new_quantity = current_quantity + fill.quantity
        new_average = (
            (current_quantity * current_average + fill.notional) / new_quantity
            if new_quantity
            else Decimal("0")
        )
    else:
        if fill.quantity > current_quantity:
            raise ValidationError("sell fill exceeds current position.")
        new_cash = state.account.cash + fill.notional
        new_quantity = current_quantity - fill.quantity
        new_average = current_average if new_quantity else Decimal("0")

    updated = Position(fill.symbol, new_quantity, new_average)
    positions = tuple(
        position for position in state.positions if position.symbol != updated.symbol
    )
    if not updated.is_flat:
        positions = (*positions, updated)

    return PortfolioState(
        account=Account(new_cash, state.account.currency),
        positions=positions,
        risk=state.risk,
        timestamp=fill.timestamp,
    )
