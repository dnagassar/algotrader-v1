"""Immutable account and portfolio state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from algotrader.core.types import Fill, OrderSide
from algotrader.errors import ValidationError


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a decimal value.") from exc


def _non_negative(value: Decimal, field_name: str) -> None:
    if value < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")


def _symbol(value: str) -> str:
    symbol = value.strip().upper()
    if not symbol:
        raise ValidationError("symbol is required.")
    return symbol


@dataclass(frozen=True, slots=True)
class Account:
    cash: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        object.__setattr__(self, "cash", _decimal(self.cash, "cash"))
        _non_negative(self.cash, "cash")

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
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(self, "quantity", _decimal(self.quantity, "quantity"))
        object.__setattr__(
            self,
            "average_price",
            _decimal(self.average_price, "average_price"),
        )
        _non_negative(self.average_price, "average_price")


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
        normalized = _symbol(symbol)
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
