"""Offline classification for paper-lab snapshot observation records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


CLASSIFICATION_TERMINAL_FILLED = "terminal_filled"
CLASSIFICATION_TERMINAL_CANCELED_OR_EXPIRED = "terminal_canceled_or_expired"
CLASSIFICATION_STILL_OPEN_OR_ACCEPTED_AFTER_FULL_SESSION = (
    "still_open_or_accepted_after_full_session"
)
CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE = "ambiguous_or_incomplete"

_FILLED_STATUSES = frozenset(("filled",))
_TERMINAL_NON_FILLED_STATUSES = frozenset(
    (
        "canceled",
        "cancelled",
        "done_for_day",
        "expired",
        "rejected",
        "stopped",
        "suspended",
    )
)
_ACTIVE_STATUSES = frozenset(
    (
        "accepted",
        "new",
        "open",
        "partially_filled",
        "pending_new",
        "pending_replace",
        "submitted",
    )
)
_KNOWN_STATUSES = (
    _FILLED_STATUSES | _TERMINAL_NON_FILLED_STATUSES | _ACTIVE_STATUSES
)
_REQUIRED_TRUE_FLAGS = (
    "orders_observation_available",
    "positions_observation_available",
)
_OPTIONAL_TRUE_FLAGS = (
    "account_observation_available",
    "recent_order_query_available",
)
_ORDER_COLLECTION_FIELDS = (
    "recent_orders",
    "orders",
    "open_orders",
    "order_observations",
)
_POSITION_COLLECTION_FIELDS = (
    "positions",
    "current_positions",
)
_ORDER_STATUS_FIELDS = (
    "normalized_status",
    "status",
    "broker_normalized_status",
    "raw_status",
    "broker_raw_status",
)
_ORDER_FILLED_QUANTITY_FIELDS = (
    "filled_qty",
    "filled_quantity",
    "filledQty",
    "filledQuantity",
)
_ORDER_FILLED_AT_FIELDS = (
    "filled_at",
    "filledAt",
)
_POSITION_QUANTITY_FIELDS = (
    "quantity",
    "qty",
)


@dataclass(frozen=True, slots=True)
class PaperSnapshotClassification:
    classification: str
    reason: str
    target_order_found: bool
    target_position_found: bool
    metadata_complete: bool
    mutated: bool | None
    submitted: bool | None
    order_status: str
    filled_qty: str
    filled_at: str
    position_qty: str
    missing_fields: tuple[str, ...]


def classify_paper_snapshot_record(
    record: Mapping[str, Any],
    *,
    broker_order_id: str = "",
    client_order_id: str = "",
    symbol: str = "",
) -> PaperSnapshotClassification:
    """Classify one already-produced paper-lab snapshot record."""

    if not isinstance(record, Mapping):
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="record_not_mapping",
            missing_fields=("record",),
        )

    missing_fields = _record_missing_fields(record)
    mutated = _flag_value(record, "mutated")
    submitted = _flag_value(record, "submitted")
    orders = _mapping_rows(_first_present(record, _ORDER_COLLECTION_FIELDS))
    target_order = _target_order(
        orders,
        broker_order_id=broker_order_id,
        client_order_id=client_order_id,
        symbol=symbol,
    )
    order_status = ""
    filled_qty = ""
    filled_at = ""
    if target_order is not None:
        order_status = _normalize_order_status(
            _first_present(target_order, _ORDER_STATUS_FIELDS)
        )
        filled_qty = _text(_first_present(target_order, _ORDER_FILLED_QUANTITY_FIELDS))
        filled_at = _text(_first_present(target_order, _ORDER_FILLED_AT_FIELDS))

    position_symbol = symbol or _text(target_order.get("symbol") if target_order else "")
    target_position, target_position_found = _target_position(record, position_symbol)
    position_qty = (
        _text(_first_present(target_position, _POSITION_QUANTITY_FIELDS))
        if target_position is not None
        else ""
    )

    if mutated is not False:
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="mutated_missing_or_true",
            target_order_found=target_order is not None,
            target_position_found=target_position_found,
            metadata_complete=False,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
            missing_fields=_append_missing(missing_fields, "mutated"),
        )

    if submitted is not False:
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="submitted_missing_or_true",
            target_order_found=target_order is not None,
            target_position_found=target_position_found,
            metadata_complete=False,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
            missing_fields=_append_missing(missing_fields, "submitted"),
        )

    if _has_broker_error(record):
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="broker_response_error",
            target_order_found=target_order is not None,
            target_position_found=target_position_found,
            metadata_complete=False,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
            missing_fields=missing_fields,
        )

    if missing_fields:
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="required_observation_or_metadata_incomplete",
            target_order_found=target_order is not None,
            target_position_found=target_position_found,
            metadata_complete=False,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
            missing_fields=missing_fields,
        )

    if target_order is None:
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="target_order_not_found",
            target_position_found=target_position_found,
            metadata_complete=True,
            mutated=mutated,
            submitted=submitted,
            position_qty=position_qty,
        )

    if not order_status:
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="order_status_missing",
            target_order_found=True,
            target_position_found=target_position_found,
            metadata_complete=False,
            mutated=mutated,
            submitted=submitted,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
            missing_fields=("order_status",),
        )

    if order_status not in _KNOWN_STATUSES:
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="order_status_unknown",
            target_order_found=True,
            target_position_found=target_position_found,
            metadata_complete=False,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
            missing_fields=("order_status",),
        )

    conflict_fields = _filled_quantity_status_conflict_fields(
        status=order_status,
        filled_qty=filled_qty,
        filled_at=filled_at,
    )
    if conflict_fields:
        return _classification(
            classification=CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
            reason="filled_quantity_status_conflict",
            target_order_found=True,
            target_position_found=target_position_found,
            metadata_complete=False,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
            missing_fields=conflict_fields,
        )

    if order_status in _FILLED_STATUSES:
        return _classification(
            classification=CLASSIFICATION_TERMINAL_FILLED,
            reason="filled_order_with_complete_metadata",
            target_order_found=True,
            target_position_found=target_position_found,
            metadata_complete=True,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
        )

    if order_status in _TERMINAL_NON_FILLED_STATUSES:
        return _classification(
            classification=CLASSIFICATION_TERMINAL_CANCELED_OR_EXPIRED,
            reason="terminal_non_filled_order_with_complete_metadata",
            target_order_found=True,
            target_position_found=target_position_found,
            metadata_complete=True,
            mutated=mutated,
            submitted=submitted,
            order_status=order_status,
            filled_qty=filled_qty,
            filled_at=filled_at,
            position_qty=position_qty,
        )

    return _classification(
        classification=CLASSIFICATION_STILL_OPEN_OR_ACCEPTED_AFTER_FULL_SESSION,
        reason="active_order_with_complete_metadata",
        target_order_found=True,
        target_position_found=target_position_found,
        metadata_complete=True,
        mutated=mutated,
        submitted=submitted,
        order_status=order_status,
        filled_qty=filled_qty,
        filled_at=filled_at,
        position_qty=position_qty,
    )


def _classification(
    *,
    classification: str,
    reason: str,
    target_order_found: bool = False,
    target_position_found: bool = False,
    metadata_complete: bool = False,
    mutated: bool | None = None,
    submitted: bool | None = None,
    order_status: str = "",
    filled_qty: str = "",
    filled_at: str = "",
    position_qty: str = "",
    missing_fields: Sequence[str] = (),
) -> PaperSnapshotClassification:
    return PaperSnapshotClassification(
        classification=classification,
        reason=reason,
        target_order_found=target_order_found,
        target_position_found=target_position_found,
        metadata_complete=metadata_complete,
        mutated=mutated,
        submitted=submitted,
        order_status=order_status,
        filled_qty=filled_qty,
        filled_at=filled_at,
        position_qty=position_qty,
        missing_fields=tuple(dict.fromkeys(missing_fields)),
    )


def _record_missing_fields(record: Mapping[str, Any]) -> tuple[str, ...]:
    missing_fields: list[str] = []

    for field_name in _REQUIRED_TRUE_FLAGS:
        if _flag_value(record, field_name) is not True:
            missing_fields.append(field_name)

    for field_name in _OPTIONAL_TRUE_FLAGS:
        if field_name in record and _flag_value(record, field_name) is not True:
            missing_fields.append(field_name)

    if _flag_value(record, "recent_order_query_metadata_complete") is not True:
        missing_fields.append("recent_order_query_metadata_complete")

    missing_fields.extend(_metadata_missing_fields(record))
    if _sequence_has_items(record.get("unavailable_observations")):
        missing_fields.append("unavailable_observations")
    if _mapping_has_items(record.get("unavailable_reasons")):
        missing_fields.append("unavailable_reasons")

    return tuple(dict.fromkeys(missing_fields))


def _metadata_missing_fields(record: Mapping[str, Any]) -> tuple[str, ...]:
    value = record.get("recent_order_query_metadata_missing_fields", ())
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, Sequence):
        return tuple(_text(item) for item in value if _text(item))
    if value:
        return ("recent_order_query_metadata_missing_fields",)
    return ()


def _target_order(
    orders: Sequence[Mapping[str, Any]],
    *,
    broker_order_id: str,
    client_order_id: str,
    symbol: str,
) -> Mapping[str, Any] | None:
    for order in orders:
        if _matches_target_order(
            order,
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
            symbol=symbol,
        ):
            return order
    return None


def _matches_target_order(
    order: Mapping[str, Any],
    *,
    broker_order_id: str,
    client_order_id: str,
    symbol: str,
) -> bool:
    broker_target = _text(broker_order_id)
    client_target = _text(client_order_id)
    symbol_target = _normalize_symbol(symbol)

    broker_match = _target_matches_any(
        broker_target,
        order,
        ("broker_order_id", "order_id", "id"),
    )
    client_match = _target_matches_any(client_target, order, ("client_order_id",))

    if broker_target or client_target:
        if not (broker_match or client_match):
            return False
        order_symbol = _normalize_symbol(order.get("symbol"))
        return not symbol_target or not order_symbol or order_symbol == symbol_target

    order_symbol = _normalize_symbol(order.get("symbol"))
    return bool(symbol_target and order_symbol == symbol_target)


def _target_matches_any(
    target: str,
    row: Mapping[str, Any],
    fields: Sequence[str],
) -> bool:
    if not target:
        return False
    return any(_text(row.get(field_name)) == target for field_name in fields)


def _target_position(
    record: Mapping[str, Any],
    symbol: str,
) -> tuple[Mapping[str, Any] | None, bool]:
    target_symbol = _normalize_symbol(symbol)
    if not target_symbol:
        return None, False

    for position in _mapping_rows(_first_present(record, _POSITION_COLLECTION_FIELDS)):
        if _normalize_symbol(position.get("symbol")) == target_symbol:
            return position, True

    position_symbols = record.get("position_symbols", ())
    if isinstance(position_symbols, str):
        position_symbols = (position_symbols,)
    if isinstance(position_symbols, Sequence):
        for position_symbol in position_symbols:
            if _normalize_symbol(position_symbol) == target_symbol:
                return None, True

    return None, False


def _first_present(record: Mapping[str, Any], fields: Sequence[str]) -> Any:
    for field_name in fields:
        value = record.get(field_name)
        if value not in (None, ""):
            return value
    return None


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(row for row in value if isinstance(row, Mapping))
    return ()


def _normalize_order_status(value: Any) -> str:
    text = _text(value).strip().lower()
    if not text:
        return ""
    text = text.replace("-", "_").replace(" ", "_")
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text


def _filled_quantity_status_conflict_fields(
    *,
    status: str,
    filled_qty: str,
    filled_at: str,
) -> tuple[str, ...]:
    state = _quantity_state(filled_qty)

    if state in ("invalid", "negative"):
        return ("filled_qty",)

    if status in _FILLED_STATUSES:
        fields: list[str] = []
        if state != "positive":
            fields.append("filled_qty")
        if not filled_at:
            fields.append("filled_at")
        return tuple(fields)

    if status in _TERMINAL_NON_FILLED_STATUSES and state == "positive":
        return ("filled_qty",)

    if status == "partially_filled":
        return () if state == "positive" else ("filled_qty",)

    if status in _ACTIVE_STATUSES and state == "positive":
        return ("filled_qty",)

    return ()


def _quantity_state(value: str) -> str:
    text = _text(value).strip().replace(",", "")
    if not text:
        return "missing"
    try:
        quantity = Decimal(text)
    except InvalidOperation:
        return "invalid"
    if quantity < 0:
        return "negative"
    if quantity > 0:
        return "positive"
    return "zero"


def _has_broker_error(record: Mapping[str, Any]) -> bool:
    return (
        bool(_text(record.get("error")))
        or bool(_text(record.get("error_type")))
        or _flag_value(record, "broker_error") is True
    )


def _append_missing(missing_fields: Sequence[str], field_name: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*missing_fields, field_name)))


def _flag_value(record: Mapping[str, Any], field_name: str) -> bool | None:
    if field_name not in record:
        return None
    value = record[field_name]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("false", "0", "no"):
            return False
        if normalized in ("true", "1", "yes"):
            return True
    return None


def _sequence_has_items(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and bool(value)
    )


def _mapping_has_items(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(value)


def _normalize_symbol(value: Any) -> str:
    return _text(value).strip().upper()


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


__all__ = [
    "CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE",
    "CLASSIFICATION_STILL_OPEN_OR_ACCEPTED_AFTER_FULL_SESSION",
    "CLASSIFICATION_TERMINAL_CANCELED_OR_EXPIRED",
    "CLASSIFICATION_TERMINAL_FILLED",
    "PaperSnapshotClassification",
    "classify_paper_snapshot_record",
]
