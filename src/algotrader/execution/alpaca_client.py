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
class AlpacaOrderRequest:
    client_order_id: str
    symbol: str
    side: str
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
        if self.side.strip().lower() != "buy":
            raise ValueError("Alpaca paper order requests are buy-only.")
        if self.order_type.strip().lower() != "market":
            raise ValueError("Alpaca paper order requests are market-only.")
        if self.time_in_force.strip().lower() != "day":
            raise ValueError("Alpaca paper order requests are day-only.")
        if self.limit_price is not None:
            raise ValueError("Alpaca paper market order requests must not use limit_price.")

        has_qty = self.qty is not None
        has_notional = self.notional is not None
        if has_qty == has_notional:
            raise ValueError(
                "Alpaca paper order requests require exactly one of qty or notional."
            )

        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        object.__setattr__(self, "side", self.side.strip().lower())
        object.__setattr__(self, "order_type", self.order_type.strip().lower())
        object.__setattr__(self, "time_in_force", self.time_in_force.strip().lower())

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
    "AlpacaOrderRequest",
    "AlpacaOrderSubmissionResponse",
    "AlpacaPositionResponse",
]
