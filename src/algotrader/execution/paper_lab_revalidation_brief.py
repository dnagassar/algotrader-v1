"""Read-only paper-lab run-log revalidation brief."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import json
from json import JSONDecodeError
from pathlib import Path
import re
from typing import Any

from .paper_lab_observation_log import (
    EVENT_TYPES,
    PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
    PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
    PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
    PAPER_LAB_SNAPSHOT_UNAVAILABLE,
)


STATE_USABLE_FOR_MANUAL_REVIEW = "usable_for_manual_review"
STATE_INSUFFICIENT_OBSERVATION = "insufficient_observation"
STATE_OBSERVATION_UNAVAILABLE = "observation_unavailable"
STATE_INVALID_RUN_LOG = "invalid_run_log"

_OBSERVATION_EVENT_TYPES = {
    "account": PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
    "positions": PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
    "orders": PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
}
_SAFE_ORDER_STATUS_FIELDS = (
    "symbol",
    "side",
    "normalized_status",
    "raw_status",
    "asset_class",
    "order_type",
    "time_in_force",
    "submitted_at",
    "filled_at",
)
_REDACTION_MARKERS = ("credentials_redacted", "<redacted>")
_SECRET_TEXT_RE = re.compile(
    r"(api[_-]?key|secret|token|password|credential|authorization|bearer|https?://)",
    re.IGNORECASE,
)
_SAFE_CODE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
_SAFE_MONEY_RE = re.compile(r"^-?[0-9][0-9,]*(\.[0-9]+)?$")


def build_paper_lab_revalidation_brief(
    run_log_path: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, object]:
    """Summarize a local paper-lab JSONL run log without side effects."""

    records, invalid_reasons = _read_jsonl_records(run_log_path)
    run_ids = _run_ids(records)
    selected_run_id = _selected_run_id(records, run_id)
    selected_records = _selected_records(records, selected_run_id)

    if invalid_reasons:
        return _brief_payload(
            STATE_INVALID_RUN_LOG,
            records=records,
            selected_records=selected_records,
            selected_run_id=selected_run_id,
            run_ids=run_ids,
            invalid_reasons=invalid_reasons,
        )

    unavailable_events = _unavailable_or_error_events(selected_records)
    missing_observations = _missing_observations(selected_records)
    if unavailable_events:
        state = STATE_OBSERVATION_UNAVAILABLE
    elif missing_observations:
        state = STATE_INSUFFICIENT_OBSERVATION
    else:
        state = STATE_USABLE_FOR_MANUAL_REVIEW

    return _brief_payload(
        state,
        records=records,
        selected_records=selected_records,
        selected_run_id=selected_run_id,
        run_ids=run_ids,
        invalid_reasons=(),
    )


def render_paper_lab_revalidation_brief_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact deterministic text brief."""

    labels = _mapping(payload.get("advisory_labels"))
    observations = _mapping(payload.get("observations"))
    account = _mapping(payload.get("account"))
    positions = _mapping(payload.get("positions"))
    recent_orders = _mapping(payload.get("recent_orders"))

    lines = [
        "Paper lab revalidation brief",
        f"state: {_text(payload.get('state'))}",
        f"usable_for_manual_review: {_bool_text(payload.get('usable_for_manual_review'))}",
        f"paper_lab_only: {_bool_text(labels.get('paper_lab_only'))}",
        f"not_live_authorized: {_bool_text(labels.get('not_live_authorized'))}",
        f"manual_review_required: {_bool_text(labels.get('manual_review_required'))}",
        f"profit_claim: {_text(labels.get('profit_claim'))}",
        f"manual_review_note: {_text(payload.get('manual_review_note'))}",
        f"next_probe_note: {_text(payload.get('next_probe_note'))}",
        f"run_ids: {_joined(payload.get('run_ids'))}",
        f"selected_run_id: {_text(payload.get('selected_run_id')) or 'none'}",
        f"record_count: {_text(payload.get('record_count'))}",
        f"selected_record_count: {_text(payload.get('selected_record_count'))}",
    ]
    lines.extend(_event_count_lines(_mapping(payload.get("event_counts"))))
    lines.extend(
        [
            f"account_observed: {_bool_text(observations.get('account'))}",
            f"positions_observed: {_bool_text(observations.get('positions'))}",
            f"orders_observed: {_bool_text(observations.get('orders'))}",
            f"missing_observations: {_joined(payload.get('missing_observations'))}",
        ]
    )
    if account.get("observed"):
        lines.append(
            "account_cash: "
            f"{_text(account.get('cash'))} {_text(account.get('currency'))}".strip()
        )
    else:
        lines.append("account_cash: unavailable")

    lines.extend(
        [
            f"position_count: {_text(positions.get('position_count'))}",
            f"position_symbols: {_joined(positions.get('symbols'))}",
            f"recent_order_count: {_text(recent_orders.get('count'))}",
        ]
    )
    for status in _sequence(recent_orders.get("statuses")):
        if not isinstance(status, Mapping):
            continue
        lines.append(f"recent_order_status: {_status_text(status)}")

    unavailable_events = _sequence(payload.get("unavailable_events"))
    if unavailable_events:
        for event in unavailable_events:
            if isinstance(event, Mapping):
                lines.append(f"unavailable_event: {_event_text(event)}")
    else:
        lines.append("unavailable_events: none")

    invalid_reasons = _sequence(payload.get("invalid_reasons"))
    if invalid_reasons:
        lines.append(f"invalid_reasons: {_joined(invalid_reasons)}")

    lines.append(
        f"redaction_markers_found: {_joined(payload.get('redaction_markers_found'))}"
    )
    return "\n".join(lines)


def _brief_payload(
    state: str,
    *,
    records: Sequence[Mapping[str, Any]],
    selected_records: Sequence[Mapping[str, Any]],
    selected_run_id: str,
    run_ids: Sequence[str],
    invalid_reasons: Sequence[str],
) -> dict[str, object]:
    observations = _observations(selected_records)
    missing_observations = _missing_observations(selected_records)
    unavailable_events = _unavailable_or_error_events(selected_records)
    usable = state == STATE_USABLE_FOR_MANUAL_REVIEW
    return {
        "account": _latest_account(selected_records),
        "advisory_labels": {
            "manual_review_required": True,
            "not_live_authorized": True,
            "paper_lab_only": True,
            "profit_claim": "none",
        },
        "command": "paper-lab-revalidation-brief",
        "event_counts": _event_counts(selected_records),
        "invalid_reasons": list(invalid_reasons),
        "manual_review_note": (
            "manual review required before any further paper probe"
        ),
        "missing_observations": list(missing_observations),
        "next_probe_note": "next manual paper probe remains outside this command",
        "observations": observations,
        "positions": _latest_positions(selected_records),
        "recent_orders": _latest_recent_orders(selected_records),
        "record_count": len(records),
        "redaction_markers_found": _redaction_markers(selected_records),
        "run_ids": list(run_ids),
        "selected_record_count": len(selected_records),
        "selected_run_id": _safe_run_id(selected_run_id),
        "state": state,
        "unavailable_events": unavailable_events,
        "usable_for_manual_review": usable,
    }


def _read_jsonl_records(
    run_log_path: str | Path,
) -> tuple[list[Mapping[str, Any]], tuple[str, ...]]:
    path = Path(run_log_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], (f"read_failed:{exc.__class__.__name__}",)

    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except JSONDecodeError:
            return records, (f"line {line_number}: JSONDecodeError",)
        if not isinstance(record, Mapping):
            return records, (f"line {line_number}: record_must_be_object",)
        records.append(record)

    return records, ()


def _selected_run_id(
    records: Sequence[Mapping[str, Any]],
    requested_run_id: str | None,
) -> str:
    if requested_run_id is not None:
        return str(requested_run_id)

    for record in reversed(records):
        run_id = record.get("run_id")
        if run_id:
            return str(run_id)

    return ""


def _selected_records(
    records: Sequence[Mapping[str, Any]],
    selected_run_id: str,
) -> tuple[Mapping[str, Any], ...]:
    if not selected_run_id:
        return ()

    return tuple(
        record for record in records if str(record.get("run_id", "")) == selected_run_id
    )


def _run_ids(records: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    run_ids: list[str] = []
    seen: set[str] = set()
    for record in records:
        run_id = record.get("run_id")
        if not run_id:
            continue
        raw_run_id = str(run_id)
        if raw_run_id in seen:
            continue
        seen.add(raw_run_id)
        run_ids.append(_safe_run_id(raw_run_id))

    return tuple(run_ids)


def _observations(records: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    event_types = {_safe_event_type(record.get("event_type")) for record in records}
    return {
        name: event_type in event_types
        for name, event_type in _OBSERVATION_EVENT_TYPES.items()
    }


def _missing_observations(
    records: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    observations = _observations(records)
    return tuple(
        name for name in ("account", "positions", "orders") if not observations[name]
    )


def _latest_account(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED)
    account = _mapping(record.get("account") if record else None)
    if not account:
        return {"cash": "", "currency": "", "observed": False}

    return {
        "cash": _safe_money(account.get("cash")),
        "currency": _safe_code(account.get("currency")),
        "observed": True,
    }


def _latest_positions(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED)
    if record is None:
        return {"observed": False, "position_count": 0, "symbols": []}

    symbols = _safe_symbols(record.get("position_symbols"))
    if not symbols:
        symbols = _symbols_from_positions(record.get("positions"))
    return {
        "observed": True,
        "position_count": _safe_count(record.get("position_count"), len(symbols)),
        "symbols": list(symbols),
    }


def _latest_recent_orders(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED)
    if record is None:
        return {"count": 0, "observed": False, "statuses": []}

    orders = _sequence(record.get("recent_orders"))
    statuses = [
        _safe_order_status(order) for order in orders if isinstance(order, Mapping)
    ]
    return {
        "count": _safe_count(record.get("recent_order_count"), len(statuses)),
        "observed": True,
        "statuses": statuses,
    }


def _latest_record(
    records: Sequence[Mapping[str, Any]],
    event_type: str,
) -> Mapping[str, Any] | None:
    for record in reversed(records):
        if _safe_event_type(record.get("event_type")) == event_type:
            return record

    return None


def _event_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counter = Counter(_safe_event_type(record.get("event_type")) for record in records)
    ordered: dict[str, int] = {}
    for event_type in EVENT_TYPES:
        if counter[event_type]:
            ordered[event_type] = counter[event_type]
    for event_type in sorted(set(counter) - set(EVENT_TYPES)):
        if counter[event_type]:
            ordered[event_type] = counter[event_type]

    return ordered


def _unavailable_or_error_events(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for record in records:
        event_type = _safe_event_type(record.get("event_type"))
        error = _safe_code(record.get("error"))
        if not (
            event_type == PAPER_LAB_SNAPSHOT_UNAVAILABLE
            or event_type.endswith(("_failed", "_unavailable", "_parse_failed"))
            or bool(error)
        ):
            continue
        event: dict[str, object] = {"event_type": event_type}
        if error:
            event["error"] = error
        unavailable_observations = _safe_observation_names(
            record.get("unavailable_observations")
        )
        if unavailable_observations:
            event["unavailable_observations"] = list(unavailable_observations)
        reasons = _safe_unavailable_reasons(record.get("unavailable_reasons"))
        if reasons:
            event["unavailable_reasons"] = reasons
        error_type = _safe_code(record.get("error_type"))
        if error_type:
            event["error_type"] = error_type
        events.append(event)

    return events


def _safe_unavailable_reasons(value: Any) -> dict[str, dict[str, str]]:
    reasons = _mapping(value)
    safe_reasons: dict[str, dict[str, str]] = {}
    for name, reason in reasons.items():
        reason_payload = _mapping(reason)
        safe_name = _safe_observation_name(name)
        if not safe_name:
            continue
        detail: dict[str, str] = {}
        error_type = _safe_code(reason_payload.get("error_type"))
        if error_type:
            detail["error_type"] = error_type
        markers = _markers_in_value(reason_payload.get("message"))
        if markers:
            detail["message"] = ",".join(markers)
        if detail:
            safe_reasons[safe_name] = detail

    return safe_reasons


def _safe_order_status(order: Mapping[str, Any]) -> dict[str, str]:
    return {
        field: _safe_status_value(order.get(field))
        for field in _SAFE_ORDER_STATUS_FIELDS
        if field in order
    }


def _safe_symbols(value: Any) -> tuple[str, ...]:
    return tuple(
        symbol
        for symbol in (_safe_symbol(item) for item in _sequence(value))
        if symbol
    )


def _symbols_from_positions(value: Any) -> tuple[str, ...]:
    symbols: list[str] = []
    for position in _sequence(value):
        if not isinstance(position, Mapping):
            continue
        symbol = _safe_symbol(position.get("symbol"))
        if symbol:
            symbols.append(symbol)

    return tuple(symbols)


def _safe_observation_names(value: Any) -> tuple[str, ...]:
    return tuple(
        name
        for name in (_safe_observation_name(item) for item in _sequence(value))
        if name
    )


def _safe_observation_name(value: Any) -> str:
    text = _text(value)
    if text in {"account", "positions", "orders", "broker"}:
        return text

    return ""


def _safe_count(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int) and value >= 0:
        return value
    text = _text(value)
    if text.isdigit():
        return int(text)

    return fallback


def _safe_run_id(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if _is_secret_like(text):
        return "<redacted>"

    return text[:96]


def _safe_symbol(value: Any) -> str:
    text = _text(value).upper()
    if not _SAFE_CODE_RE.fullmatch(text) or _is_secret_like(text):
        return ""

    return text


def _safe_event_type(value: Any) -> str:
    text = _text(value)
    if not text:
        return "missing_event_type"
    if not _SAFE_CODE_RE.fullmatch(text) or _is_secret_like(text):
        return "redacted_event_type"

    return text


def _safe_status_value(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if _is_secret_like(text):
        return "<redacted>"

    return text[:160]


def _safe_code(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if not _SAFE_CODE_RE.fullmatch(text) or _is_secret_like(text):
        return "<redacted>"

    return text


def _safe_money(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if _SAFE_MONEY_RE.fullmatch(text):
        return text

    return "<redacted>"


def _redaction_markers(records: Sequence[Mapping[str, Any]]) -> list[str]:
    markers: set[str] = set()
    for record in records:
        markers.update(_markers_in_value(record))

    return sorted(markers)


def _markers_in_value(value: Any) -> tuple[str, ...]:
    markers: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            markers.update(_markers_in_value(item))
    elif isinstance(value, list):
        for item in value:
            markers.update(_markers_in_value(item))
    elif isinstance(value, str):
        for marker in _REDACTION_MARKERS:
            if marker in value:
                markers.add(marker)

    return tuple(sorted(markers))


def _event_count_lines(event_counts: Mapping[str, object]) -> list[str]:
    if not event_counts:
        return ["event_counts: none"]

    return [
        f"event_count: {event_type}={event_counts[event_type]}"
        for event_type in event_counts
    ]


def _status_text(status: Mapping[str, Any]) -> str:
    return " ".join(
        f"{field}={_text(status.get(field))}"
        for field in _SAFE_ORDER_STATUS_FIELDS
        if field in status
    )


def _event_text(event: Mapping[str, Any]) -> str:
    parts = [f"event_type={_text(event.get('event_type'))}"]
    if event.get("error"):
        parts.append(f"error={_text(event.get('error'))}")
    if event.get("error_type"):
        parts.append(f"error_type={_text(event.get('error_type'))}")
    observations = _joined(event.get("unavailable_observations"))
    if observations != "none":
        parts.append(f"unavailable_observations={observations}")
    reasons = _mapping(event.get("unavailable_reasons"))
    if reasons:
        parts.append(f"unavailable_reasons={_reason_text(reasons)}")

    return " ".join(parts)


def _reason_text(reasons: Mapping[str, object]) -> str:
    parts: list[str] = []
    for name in sorted(reasons):
        detail = _mapping(reasons[name])
        reason_parts = [f"{key}:{detail[key]}" for key in sorted(detail)]
        parts.append(f"{name}({','.join(reason_parts)})")

    return ";".join(parts)


def _joined(value: Any) -> str:
    items = [_text(item) for item in _sequence(value) if _text(item)]
    return ",".join(items) if items else "none"


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value

    return {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if value is None or isinstance(value, (str, bytes)):
        return ()
    if isinstance(value, Sequence):
        return tuple(value)

    return ()


def _is_secret_like(value: str) -> bool:
    return bool(_SECRET_TEXT_RE.search(value))


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _text(value: Any) -> str:
    if value is None:
        return ""

    return str(value)


__all__ = [
    "STATE_INSUFFICIENT_OBSERVATION",
    "STATE_INVALID_RUN_LOG",
    "STATE_OBSERVATION_UNAVAILABLE",
    "STATE_USABLE_FOR_MANUAL_REVIEW",
    "build_paper_lab_revalidation_brief",
    "render_paper_lab_revalidation_brief_text",
]
