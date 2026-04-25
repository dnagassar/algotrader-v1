"""Small immutable domain models for market data and orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from algotrader.errors import ValidationError


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(StrEnum):
    OPEN = "open"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELED = "canceled"


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a decimal value.") from exc


def _positive(value: Decimal, field_name: str) -> None:
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")


def _non_negative(value: Decimal, field_name: str) -> None:
    if value < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")


def _symbol(value: str) -> str:
    symbol = value.strip().upper()
    if not symbol:
        raise ValidationError("symbol is required.")
    return symbol


def _timestamp(value: datetime) -> None:
    if not isinstance(value, datetime):
        raise ValidationError("timestamp must be a datetime.")


@dataclass(frozen=True, slots=True)
class Bar:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        _timestamp(self.timestamp)

        for field_name in ("open", "high", "low", "close", "volume"):
            object.__setattr__(
                self,
                field_name,
                _decimal(getattr(self, field_name), field_name),
            )

        for field_name in ("open", "high", "low", "close"):
            _positive(getattr(self, field_name), field_name)
        _non_negative(self.volume, "volume")

        if self.high < self.low:
            raise ValidationError("high must be greater than or equal to low.")
        if self.high < max(self.open, self.close):
            raise ValidationError("high must cover open and close.")
        if self.low > min(self.open, self.close):
            raise ValidationError("low must cover open and close.")


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    bid_size: Decimal = Decimal("0")
    ask_size: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        _timestamp(self.timestamp)

        for field_name in ("bid", "ask", "bid_size", "ask_size"):
            object.__setattr__(
                self,
                field_name,
                _decimal(getattr(self, field_name), field_name),
            )

        _positive(self.bid, "bid")
        _positive(self.ask, "ask")
        _non_negative(self.bid_size, "bid_size")
        _non_negative(self.ask_size, "ask_size")

        if self.bid > self.ask:
            raise ValidationError("bid must be less than or equal to ask.")


@dataclass(frozen=True, slots=True)
class ProposedOrder:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None = None
    client_order_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _symbol(self.symbol))

        try:
            object.__setattr__(self, "side", OrderSide(self.side))
            object.__setattr__(self, "order_type", OrderType(self.order_type))
        except ValueError as exc:
            raise ValidationError("order side and type must be supported.") from exc

        object.__setattr__(self, "quantity", _decimal(self.quantity, "quantity"))
        _positive(self.quantity, "quantity")

        if self.limit_price is not None:
            object.__setattr__(
                self,
                "limit_price",
                _decimal(self.limit_price, "limit_price"),
            )
            _positive(self.limit_price, "limit_price")

        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValidationError("limit orders require limit_price.")
        if self.order_type == OrderType.MARKET and self.limit_price is not None:
            raise ValidationError("market orders must not include limit_price.")


@dataclass(frozen=True, slots=True)
class OrderAck:
    order_id: str
    order: ProposedOrder
    status: OrderStatus
    timestamp: datetime
    message: str = ""

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValidationError("order_id is required.")
        _timestamp(self.timestamp)

        try:
            object.__setattr__(self, "status", OrderStatus(self.status))
        except ValueError as exc:
            raise ValidationError("order status must be supported.") from exc


@dataclass(frozen=True, slots=True)
class Fill:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    timestamp: datetime

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValidationError("order_id is required.")
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        _timestamp(self.timestamp)

        try:
            object.__setattr__(self, "side", OrderSide(self.side))
        except ValueError as exc:
            raise ValidationError("order side must be supported.") from exc

        object.__setattr__(self, "quantity", _decimal(self.quantity, "quantity"))
        object.__setattr__(self, "price", _decimal(self.price, "price"))
        _positive(self.quantity, "quantity")
        _positive(self.price, "price")
