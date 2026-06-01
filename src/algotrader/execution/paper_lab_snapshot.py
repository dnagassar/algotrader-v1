"""Pure serializers for read-only paper-lab snapshot observations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


_RECENT_ORDER_QUERY_CONTRACT_FIELDS = (
    "recent_order_query_limit",
    "recent_order_query_status_filter",
    "recent_order_query_asset_class_filter",
    "recent_order_query_symbol_filter",
    "recent_order_query_side_filter",
    "recent_order_query_after",
    "recent_order_query_until",
    "recent_order_query_sort",
    "recent_order_query_direction",
    "recent_order_query_nested",
    "recent_order_query_source",
    "recent_order_query_contract_version",
)
_RECENT_ORDER_QUERY_REQUIRED_FIELDS = (
    "recent_order_query_limit",
    "recent_order_query_status_filter",
    "recent_order_query_direction",
    "recent_order_query_nested",
    "recent_order_query_source",
    "recent_order_query_contract_version",
)


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


def empty_recent_order_query_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "recent_order_query_after": None,
        "recent_order_query_asset_class_filter": "",
        "recent_order_query_contract_version": "",
        "recent_order_query_direction": "",
        "recent_order_query_limit": None,
        "recent_order_query_nested": None,
        "recent_order_query_side_filter": "",
        "recent_order_query_sort": "",
        "recent_order_query_source": "",
        "recent_order_query_status_filter": "",
        "recent_order_query_symbol_filter": "",
        "recent_order_query_until": None,
    }
    return _with_query_metadata_completeness(payload)


def recent_order_query_payload(query: Any) -> dict[str, object]:
    payload: dict[str, object] = {
        "recent_order_query_after": _optional_time_text(_field(query, "after")),
        "recent_order_query_asset_class_filter": _text(
            _field(query, "asset_class_filter")
        ),
        "recent_order_query_contract_version": _text(
            _field(query, "contract_version")
        ),
        "recent_order_query_direction": _text(_field(query, "direction")),
        "recent_order_query_limit": _field(query, "limit"),
        "recent_order_query_nested": _field(query, "nested"),
        "recent_order_query_side_filter": _text(_field(query, "side_filter")),
        "recent_order_query_sort": _text(_field(query, "sort")),
        "recent_order_query_source": _text(_field(query, "source")),
        "recent_order_query_status_filter": _text(_field(query, "status_filter")),
        "recent_order_query_symbol_filter": _text(_field(query, "symbol_filter")),
        "recent_order_query_until": _optional_time_text(_field(query, "until")),
    }
    return _with_query_metadata_completeness(payload)


def position_symbols(positions: Iterable[Mapping[str, str]]) -> tuple[str, ...]:
    return tuple(position["symbol"] for position in positions)


def _order_observation_payload(order: Any) -> dict[str, str]:
    payload = {
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
    for field_name, output_name in (
        ("created_at", "created_at"),
        ("filled_quantity", "filled_quantity"),
        ("filled_average_price", "filled_average_price"),
    ):
        value = (
            _time_text(_field(order, field_name))
            if field_name == "created_at"
            else _text(_field(order, field_name))
        )
        if value:
            payload[output_name] = value
    for field_name in ("order_id", "client_order_id"):
        value = _text(_field(order, field_name))
        if value:
            payload[field_name] = value

    return payload


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


def _optional_time_text(value: Any) -> str | None:
    if value is None:
        return None
    return _time_text(value)


def _with_query_metadata_completeness(
    payload: dict[str, object],
) -> dict[str, object]:
    missing_fields = _recent_order_query_metadata_missing_fields(payload)
    return {
        **payload,
        "recent_order_query_metadata_complete": not missing_fields,
        "recent_order_query_metadata_missing_fields": list(missing_fields),
    }


def _recent_order_query_metadata_missing_fields(
    payload: Mapping[str, object],
) -> tuple[str, ...]:
    missing_fields: list[str] = []
    for field_name in _RECENT_ORDER_QUERY_CONTRACT_FIELDS:
        if field_name not in payload:
            missing_fields.append(field_name)
            continue
        if field_name in _RECENT_ORDER_QUERY_REQUIRED_FIELDS and _is_missing_value(
            payload[field_name]
        ):
            missing_fields.append(field_name)

    return tuple(missing_fields)


def _is_missing_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)

    return str(value)


__all__ = [
    "account_observation_payload",
    "empty_recent_order_query_payload",
    "order_observation_payloads",
    "position_observation_payloads",
    "position_symbols",
    "recent_order_query_payload",
]
