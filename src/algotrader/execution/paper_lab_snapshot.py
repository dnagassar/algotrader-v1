"""Pure serializers for read-only paper-lab snapshot observations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


def account_observation_payload(account: Any) -> dict[str, str]:
    payload = {
        "cash": _text(_field(account, "cash")),
        "currency": _text(_field(account, "currency")),
    }
    for field_name in ("account_id", "status", "buying_power", "equity"):
        value = _field(account, field_name)
        if value is not None:
            payload[field_name] = _text(value)

    return payload


def position_observation_payloads(positions: Iterable[Any]) -> tuple[dict[str, str], ...]:
    rows = [
        {
            "average_price": _text(_field(position, "average_price")),
            "quantity": _text(_field(position, "quantity")),
            "symbol": _text(_field(position, "symbol")).upper(),
        }
        for position in positions
    ]
    return tuple(sorted(rows, key=lambda row: row["symbol"]))


def order_observation_payloads(orders: Iterable[Any]) -> tuple[dict[str, str], ...]:
    return tuple(_order_observation_payload(order) for order in orders)


def position_symbols(positions: Iterable[Mapping[str, str]]) -> tuple[str, ...]:
    return tuple(position["symbol"] for position in positions)


def _order_observation_payload(order: Any) -> dict[str, str]:
    return {
        "asset_class": _text(_field(order, "asset_class")),
        "filled_at": _time_text(_field(order, "filled_at")),
        "normalized_status": _text(_field(order, "normalized_status")),
        "notional": _text(_field(order, "notional")),
        "order_type": _text(_field(order, "order_type")),
        "quantity": _text(
            _first_present(
                _field(order, "quantity"),
                _field(order, "qty"),
            )
        ),
        "raw_status": _text(_field(order, "raw_status")),
        "side": _text(_field(order, "side")),
        "submitted_at": _time_text(_field(order, "submitted_at")),
        "symbol": _text(_field(order, "symbol")).upper(),
        "time_in_force": _text(_field(order, "time_in_force")),
    }


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    if is_dataclass(value):
        names = {field.name for field in fields(value)}
        if name in names:
            return getattr(value, name)
        return None
    return getattr(value, name, None)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value

    return None


def _time_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)

    return str(value)


__all__ = [
    "account_observation_payload",
    "order_observation_payloads",
    "position_observation_payloads",
    "position_symbols",
]
