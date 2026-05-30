"""Offline Alpaca client boundary for future paper broker integration.

This module intentionally does not import alpaca-py, instantiate clients, load
credentials, or perform network calls. It only defines the small internal shape
that a future adapter can satisfy.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Protocol


_TIME_IN_FORCE_BY_ASSET_CLASS = {
    "equity": ("day",),
    "crypto": ("gtc", "ioc"),
    "option": ("day",),
}


@dataclass(frozen=True)
class AlpacaAccountResponse:
    account_id: str
    status: str
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    currency: str = "USD"


@dataclass(frozen=True)
class AlpacaPositionResponse:
    symbol: str
    qty: Decimal
    market_value: Decimal
    average_entry_price: Decimal
    side: str = "long"


@dataclass(frozen=True)
class AlpacaOrderResponse:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    status: str
    qty: Optional[Decimal] = None
    notional: Optional[Decimal] = None
    asset_class: str = ""
    order_type: str = "market"
    time_in_force: str = ""
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


@dataclass(frozen=True)
class AlpacaOrderRequest:
    client_order_id: str
    symbol: str
    side: str
    asset_class: str = "equity"
    qty: Optional[Decimal] = None
    notional: Optional[Decimal] = None
    order_type: str = "market"
    time_in_force: str = "day"
    limit_price: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if not self.client_order_id.strip():
            raise ValueError("client_order_id is required.")
        if not self.symbol.strip():
            raise ValueError("symbol is required.")
        side = self.side.strip().lower()
        asset_class = self.asset_class.strip().lower()
        order_type = self.order_type.strip().lower()
        time_in_force = self.time_in_force.strip().lower()
        if asset_class not in _TIME_IN_FORCE_BY_ASSET_CLASS:
            raise ValueError("Alpaca paper order requests require a supported asset_class.")
        if side != "buy":
            raise ValueError("Alpaca paper order requests are buy-only.")
        if order_type != "market":
            raise ValueError("Alpaca paper order requests are market-only.")
        if time_in_force not in _TIME_IN_FORCE_BY_ASSET_CLASS[asset_class]:
            raise ValueError(
                "Alpaca paper order requests use asset-class-specific time_in_force."
            )
        if self.limit_price is not None:
            raise ValueError("Alpaca paper market order requests must not use limit_price.")

        has_qty = self.qty is not None
        has_notional = self.notional is not None
        if has_qty == has_notional:
            raise ValueError(
                "Alpaca paper order requests require exactly one of qty or notional."
            )

        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "asset_class", asset_class)
        object.__setattr__(self, "order_type", order_type)
        object.__setattr__(self, "time_in_force", time_in_force)

        if self.qty is not None:
            qty = _positive_decimal(self.qty, "qty")
            object.__setattr__(self, "qty", qty)
        if self.notional is not None:
            notional = _positive_decimal(self.notional, "notional")
            object.__setattr__(self, "notional", notional)


@dataclass(frozen=True)
class AlpacaOrderSubmissionResponse:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    qty: Optional[Decimal]
    status: str
    submitted_at: datetime
    notional: Optional[Decimal] = None


class AlpacaClient(Protocol):
    """Minimal client protocol a future Alpaca adapter must satisfy."""

    def get_account(self) -> AlpacaAccountResponse:
        ...

    def get_positions(self) -> Sequence[AlpacaPositionResponse]:
        ...

    def get_orders(self) -> Sequence[AlpacaOrderResponse]:
        ...

    def submit_order(
        self, request: AlpacaOrderRequest
    ) -> AlpacaOrderSubmissionResponse:
        ...


def _positive_decimal(value: Decimal, field_name: str) -> Decimal:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_name} must be a valid decimal.") from None

    if decimal_value <= 0:
        raise ValueError(f"{field_name} must be positive.")

    return decimal_value


__all__ = [
    "AlpacaAccountResponse",
    "AlpacaClient",
    "AlpacaOrderResponse",
    "AlpacaOrderRequest",
    "AlpacaOrderSubmissionResponse",
    "AlpacaPositionResponse",
]
