"""Small immutable domain models for market data and orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from algotrader.core.validation import (
    decimal_value,
    non_negative,
    positive,
    symbol_value,
    timestamp_value,
)
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
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        timestamp_value(self.timestamp)

        for field_name in ("open", "high", "low", "close", "volume"):
            object.__setattr__(
                self,
                field_name,
                decimal_value(getattr(self, field_name), field_name),
            )

        for field_name in ("open", "high", "low", "close"):
            positive(getattr(self, field_name), field_name)
        non_negative(self.volume, "volume")

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
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        timestamp_value(self.timestamp)

        for field_name in ("bid", "ask", "bid_size", "ask_size"):
            object.__setattr__(
                self,
                field_name,
                decimal_value(getattr(self, field_name), field_name),
            )

        positive(self.bid, "bid")
        positive(self.ask, "ask")
        non_negative(self.bid_size, "bid_size")
        non_negative(self.ask_size, "ask_size")

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
        object.__setattr__(self, "symbol", symbol_value(self.symbol))

        try:
            object.__setattr__(self, "side", OrderSide(self.side))
            object.__setattr__(self, "order_type", OrderType(self.order_type))
        except ValueError as exc:
            raise ValidationError("order side and type must be supported.") from exc

        object.__setattr__(self, "quantity", decimal_value(self.quantity, "quantity"))
        positive(self.quantity, "quantity")

        if self.limit_price is not None:
            object.__setattr__(
                self,
                "limit_price",
                decimal_value(self.limit_price, "limit_price"),
            )
            positive(self.limit_price, "limit_price")

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
        timestamp_value(self.timestamp)

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
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        timestamp_value(self.timestamp)

        try:
            object.__setattr__(self, "side", OrderSide(self.side))
        except ValueError as exc:
            raise ValidationError("order side must be supported.") from exc

        object.__setattr__(self, "quantity", decimal_value(self.quantity, "quantity"))
        object.__setattr__(self, "price", decimal_value(self.price, "price"))
        positive(self.quantity, "quantity")
        positive(self.price, "price")
