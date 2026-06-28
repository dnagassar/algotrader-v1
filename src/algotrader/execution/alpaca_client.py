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
RECENT_ORDER_QUERY_CONTRACT_VERSION = "paper_recent_order_query_v1"
_M355_SPY_CLOSE_CLIENT_ORDER_ID = "paper-order-close-m355_spy_paper_close_submit"
PAPER_AUTOPILOT_SPY_CLOSE_CLIENT_ORDER_ID_PREFIX = "pa-v207-spy-close-"
V189_SPY_CERTIFICATION_CLIENT_ORDER_ID = "paper-certification-v189-spy-sell-limit"
_RECENT_ORDER_QUERY_STATUSES = ("", "open", "closed", "all")
_RECENT_ORDER_QUERY_DIRECTIONS = ("", "asc", "desc")
_RECENT_ORDER_QUERY_SIDES = ("", "buy", "sell")


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
    created_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    filled_qty: Optional[Decimal] = None
    filled_avg_price: Optional[Decimal] = None


@dataclass(frozen=True)
class AlpacaRecentOrderQuery:
    status_filter: str = "open"
    limit: Optional[int] = 100
    asset_class_filter: str = ""
    symbol_filter: str = ""
    side_filter: str = ""
    after: Optional[datetime] = None
    until: Optional[datetime] = None
    sort: str = ""
    direction: str = "desc"
    nested: Optional[bool] = False
    source: str = "alpaca_sdk_client.get_orders"
    contract_version: str = RECENT_ORDER_QUERY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        status_filter = self.status_filter.strip().lower()
        asset_class_filter = self.asset_class_filter.strip().lower()
        symbol_filter = self.symbol_filter.strip().upper()
        side_filter = self.side_filter.strip().lower()
        sort = self.sort.strip().lower()
        direction = self.direction.strip().lower()

        if status_filter not in _RECENT_ORDER_QUERY_STATUSES:
            raise ValueError("recent order query status_filter is unsupported.")
        if side_filter not in _RECENT_ORDER_QUERY_SIDES:
            raise ValueError("recent order query side_filter is unsupported.")
        if direction not in _RECENT_ORDER_QUERY_DIRECTIONS:
            raise ValueError("recent order query direction is unsupported.")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("recent order query limit must be positive.")
        if self.nested is not None and not isinstance(self.nested, bool):
            raise ValueError("recent order query nested must be bool or None.")

        object.__setattr__(self, "status_filter", status_filter)
        object.__setattr__(self, "asset_class_filter", asset_class_filter)
        object.__setattr__(self, "symbol_filter", symbol_filter)
        object.__setattr__(self, "side_filter", side_filter)
        object.__setattr__(self, "sort", sort)
        object.__setattr__(self, "direction", direction)


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
        normalized_symbol = self.symbol.strip().upper()
        has_qty = self.qty is not None
        has_notional = self.notional is not None
        v189_spy_certification = (
            asset_class == "equity"
            and normalized_symbol == "SPY"
            and self.client_order_id == V189_SPY_CERTIFICATION_CLIENT_ORDER_ID
            and side == "sell"
            and order_type == "limit"
            and time_in_force == "day"
            and has_qty
            and not has_notional
            and self.limit_price is not None
        )
        m355_spy_close = (
            asset_class == "equity"
            and normalized_symbol == "SPY"
            and self.client_order_id == _M355_SPY_CLOSE_CLIENT_ORDER_ID
            and has_qty
            and not has_notional
        )
        paper_autopilot_spy_close = (
            asset_class == "equity"
            and normalized_symbol == "SPY"
            and self.client_order_id.startswith(
                PAPER_AUTOPILOT_SPY_CLOSE_CLIENT_ORDER_ID_PREFIX
            )
            and has_qty
            and not has_notional
        )
        if side not in {"buy", "sell"}:
            raise ValueError("Alpaca paper order requests require buy or sell side.")
        if side == "sell" and not (
            asset_class == "crypto" and normalized_symbol == "BTCUSD"
            or m355_spy_close
            or paper_autopilot_spy_close
            or v189_spy_certification
        ):
            raise ValueError(
                "Alpaca paper sell requests are restricted to BTCUSD crypto "
                "close probes, the explicit M355 SPY paper close, or the "
                "paper-autopilot SPY close namespace, or the v1.89 SPY paper "
                "certification sell-limit drill."
            )
        if order_type not in {"market", "limit"}:
            raise ValueError("Alpaca paper order requests require market or limit type.")
        if order_type == "limit" and not v189_spy_certification:
            raise ValueError(
                "Alpaca paper limit requests are restricted to the v1.89 SPY "
                "paper certification drill."
            )
        if time_in_force not in _TIME_IN_FORCE_BY_ASSET_CLASS[asset_class]:
            raise ValueError(
                "Alpaca paper order requests use asset-class-specific time_in_force."
            )
        if order_type == "market" and self.limit_price is not None:
            raise ValueError("Alpaca paper market order requests must not use limit_price.")
        if order_type == "limit" and self.limit_price is None:
            raise ValueError("Alpaca paper limit order requests require limit_price.")

        if has_qty == has_notional:
            raise ValueError(
                "Alpaca paper order requests require exactly one of qty or notional."
            )

        object.__setattr__(self, "symbol", normalized_symbol)
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
        if self.limit_price is not None:
            limit_price = _positive_decimal(self.limit_price, "limit_price")
            object.__setattr__(self, "limit_price", limit_price)


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
    filled_qty: Optional[Decimal] = None
    filled_avg_price: Optional[Decimal] = None


class AlpacaClient(Protocol):
    """Minimal client protocol a future Alpaca adapter must satisfy."""

    def get_account(self) -> AlpacaAccountResponse:
        ...

    def get_positions(self) -> Sequence[AlpacaPositionResponse]:
        ...

    def get_orders(
        self,
        query: AlpacaRecentOrderQuery | None = None,
    ) -> Sequence[AlpacaOrderResponse]:
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
    "AlpacaRecentOrderQuery",
    "AlpacaPositionResponse",
    "PAPER_AUTOPILOT_SPY_CLOSE_CLIENT_ORDER_ID_PREFIX",
    "RECENT_ORDER_QUERY_CONTRACT_VERSION",
    "V189_SPY_CERTIFICATION_CLIENT_ORDER_ID",
]
