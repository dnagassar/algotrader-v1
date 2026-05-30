"""Deterministic JSONL observations for local paper-lab CLI runs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4


PAPER_ACCOUNT_OBSERVED = "paper_account_observed"
PAPER_POSITIONS_OBSERVED = "paper_positions_observed"
PAPER_ORDER_PREVIEWED = "paper_order_previewed"
PAPER_ORDER_SUBMIT_REQUESTED = "paper_order_submit_requested"
PAPER_ORDER_SUBMIT_ATTEMPTED = "paper_order_submit_attempted"
PAPER_ORDER_SUBMIT_FAILED = "paper_order_submit_failed"
PAPER_ORDER_RECEIPT_OBSERVED = "paper_order_receipt_observed"
PAPER_ORDER_RESPONSE_PARSE_FAILED = "paper_order_response_parse_failed"
PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED = (
    "paper_order_post_submit_account_observed"
)
PAPER_LAB_SNAPSHOT_REQUESTED = "paper_lab_snapshot_requested"
PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED = "paper_lab_snapshot_account_observed"
PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED = "paper_lab_snapshot_positions_observed"
PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED = "paper_lab_snapshot_orders_observed"
PAPER_LAB_SNAPSHOT_UNAVAILABLE = "paper_lab_snapshot_unavailable"

EVENT_TYPES = (
    PAPER_ACCOUNT_OBSERVED,
    PAPER_POSITIONS_OBSERVED,
    PAPER_ORDER_PREVIEWED,
    PAPER_ORDER_SUBMIT_REQUESTED,
    PAPER_ORDER_SUBMIT_ATTEMPTED,
    PAPER_ORDER_SUBMIT_FAILED,
    PAPER_ORDER_RECEIPT_OBSERVED,
    PAPER_ORDER_RESPONSE_PARSE_FAILED,
    PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED,
    PAPER_LAB_SNAPSHOT_REQUESTED,
    PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
    PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
    PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
    PAPER_LAB_SNAPSHOT_UNAVAILABLE,
)

REDACTION_MARKER = "credentials_redacted"

_SAFE_RUN_ID_RE = re.compile(r"[^A-Za-z0-9_.:-]+")
_MAX_RUN_ID_LENGTH = 96


class PaperLabRunLogError(RuntimeError):
    """Raised when a paper-lab run log cannot be written safely."""


@dataclass(frozen=True)
class PaperLabObservationEvent:
    """Small local observation record before JSONL serialization."""

    run_id: str
    command: str
    event_type: str
    fields: Mapping[str, Any] = field(default_factory=dict)

    def to_record(
        self,
        *,
        secret_values: Iterable[str | None] = (),
    ) -> dict[str, Any]:
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported paper-lab event type: {self.event_type}")

        record: dict[str, Any] = {
            "command": self.command,
            "event_type": self.event_type,
            "redaction": REDACTION_MARKER,
            "run_id": self.run_id,
        }
        record.update(self.fields)
        return _redact_value(_json_safe(record), secret_values)


def resolve_run_id(run_id: str | None = None) -> str:
    """Return a safe caller-provided run id or a local generated id."""

    if run_id is None or not str(run_id).strip():
        return generate_run_id()

    safe = _SAFE_RUN_ID_RE.sub("_", str(run_id).strip())
    safe = safe[:_MAX_RUN_ID_LENGTH].strip("._:-")
    return safe or generate_run_id()


def generate_run_id() -> str:
    return f"paper-lab-{uuid4().hex}"


def ensure_run_log_path(path: str | Path) -> Path:
    """Validate that a run-log path can be appended to."""

    log_path = Path(path)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", newline=""):
            pass
    except OSError as exc:
        raise PaperLabRunLogError(
            f"paper_lab_run_log_write_failed: {exc.__class__.__name__}"
        ) from None

    return log_path


def append_jsonl_records(
    path: str | Path,
    records: Sequence[Mapping[str, Any]],
) -> None:
    """Append deterministic JSONL records to an explicit run-log path."""

    if not records:
        return

    log_path = ensure_run_log_path(path)
    try:
        with log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(render_jsonl_records(records))
    except OSError as exc:
        raise PaperLabRunLogError(
            f"paper_lab_run_log_write_failed: {exc.__class__.__name__}"
        ) from None


def render_jsonl_records(records: Sequence[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    )


def make_account_smoke_events(
    *,
    run_id: str,
    payload: Mapping[str, Any],
    secret_values: Iterable[str | None] = (),
) -> tuple[dict[str, Any], ...]:
    command = str(payload.get("command", "paper-account-smoke"))
    account_fields = {
        **_state_fields(payload),
        "account": payload.get("account"),
        "error": _optional_text(payload.get("error")),
        "error_type": _optional_text(payload.get("error_type")),
        "gate_summary": _gate_summary(payload.get("gates")),
        "message": _optional_text(payload.get("message")),
        "ok": bool(payload.get("ok", False)),
        "position_count": payload.get("position_count", 0),
    }
    events = [
        PaperLabObservationEvent(
            run_id=run_id,
            command=command,
            event_type=PAPER_ACCOUNT_OBSERVED,
            fields=account_fields,
        ).to_record(secret_values=secret_values)
    ]

    if payload.get("ok"):
        position_fields = {
            **_state_fields(payload),
            "gate_summary": _gate_summary(payload.get("gates")),
            "ok": True,
            "position_count": payload.get("position_count", 0),
            "positions": payload.get("positions", ()),
        }
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_POSITIONS_OBSERVED,
                fields=position_fields,
            ).to_record(secret_values=secret_values)
        )

    return tuple(events)


def make_order_probe_initial_events(
    *,
    run_id: str,
    payload: Mapping[str, Any],
    secret_values: Iterable[str | None] = (),
) -> tuple[dict[str, Any], ...]:
    command = str(payload.get("command", "paper-order-probe"))
    events = [
        PaperLabObservationEvent(
            run_id=run_id,
            command=command,
            event_type=PAPER_ORDER_PREVIEWED,
            fields=_order_fields(payload),
        ).to_record(secret_values=secret_values)
    ]
    if payload.get("submit_requested"):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_ORDER_SUBMIT_REQUESTED,
                fields=_order_fields(payload),
            ).to_record(secret_values=secret_values)
        )

    return tuple(events)


def make_order_probe_submit_events(
    *,
    run_id: str,
    payload: Mapping[str, Any],
    secret_values: Iterable[str | None] = (),
) -> tuple[dict[str, Any], ...]:
    command = str(payload.get("command", "paper-order-probe"))
    events: list[dict[str, Any]] = []

    if payload.get("submit_attempted"):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_ORDER_SUBMIT_ATTEMPTED,
                fields=_order_fields(payload),
            ).to_record(secret_values=secret_values)
        )

    if payload.get("broker_response_received") and payload.get(
        "broker_response_parsed"
    ):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_ORDER_RECEIPT_OBSERVED,
                fields=_order_fields(payload),
            ).to_record(secret_values=secret_values)
        )

    if payload.get("error") == "broker_response_parse_failed":
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_ORDER_RESPONSE_PARSE_FAILED,
                fields=_order_fields(payload),
            ).to_record(secret_values=secret_values)
        )
    elif payload.get("broker_error") and payload.get("error"):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_ORDER_SUBMIT_FAILED,
                fields=_order_fields(payload),
            ).to_record(secret_values=secret_values)
        )

    post_submit_account = payload.get("post_submit_account")
    if isinstance(post_submit_account, Mapping):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED,
                fields={
                    **_order_fields(payload),
                    "account": post_submit_account,
                    "position_count": payload.get("post_submit_position_count", 0),
                    "positions": payload.get("post_submit_positions", ()),
                },
            ).to_record(secret_values=secret_values)
        )

    return tuple(events)


def make_paper_lab_snapshot_events(
    *,
    run_id: str,
    payload: Mapping[str, Any],
    secret_values: Iterable[str | None] = (),
) -> tuple[dict[str, Any], ...]:
    command = str(payload.get("command", "paper-lab-snapshot"))
    events = [
        PaperLabObservationEvent(
            run_id=run_id,
            command=command,
            event_type=PAPER_LAB_SNAPSHOT_REQUESTED,
            fields=_snapshot_fields(payload),
        ).to_record(secret_values=secret_values)
    ]
    if payload.get("account_observation_available"):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
                fields={
                    **_snapshot_fields(payload),
                    "account": payload.get("account"),
                },
            ).to_record(secret_values=secret_values)
        )
    if payload.get("positions_observation_available"):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
                fields={
                    **_snapshot_fields(payload),
                    "position_count": payload.get("position_count", 0),
                    "position_symbols": payload.get("position_symbols", ()),
                    "positions": payload.get("positions", ()),
                },
            ).to_record(secret_values=secret_values)
        )
    if payload.get("orders_observation_available"):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
                fields={
                    **_snapshot_fields(payload),
                    "recent_order_count": payload.get("recent_order_count", 0),
                    "recent_orders": payload.get("recent_orders", ()),
                },
            ).to_record(secret_values=secret_values)
        )
    if payload.get("unavailable_observations"):
        events.append(
            PaperLabObservationEvent(
                run_id=run_id,
                command=command,
                event_type=PAPER_LAB_SNAPSHOT_UNAVAILABLE,
                fields=_snapshot_fields(payload),
            ).to_record(secret_values=secret_values)
        )

    return tuple(events)


def _order_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    request = payload.get("proposed_order_request")
    request_payload = request if isinstance(request, Mapping) else {}
    broker_result = payload.get("broker_result")
    broker_result_payload = broker_result if isinstance(broker_result, Mapping) else {}
    fields = {
        **_state_fields(payload),
        "asset_class": _text(
            payload.get("asset_class") or request_payload.get("asset_class") or "equity"
        ),
        "client_order_id": _text(request_payload.get("client_order_id")),
        "broker_normalized_status": _optional_text(
            payload.get("broker_normalized_status")
            or broker_result_payload.get("normalized_status")
        ),
        "broker_raw_reason": _optional_text(
            payload.get("broker_raw_reason") or broker_result_payload.get("raw_reason")
        ),
        "broker_raw_status": _optional_text(
            payload.get("broker_raw_status") or broker_result_payload.get("raw_status")
        ),
        "error": _optional_text(payload.get("error")),
        "error_type": _optional_text(payload.get("error_type")),
        "gate_summary": _gate_summary(payload.get("gates")),
        "market_session_note": _optional_text(payload.get("market_session_note")),
        "max_notional": _text(payload.get("max_notional")),
        "message": _optional_text(payload.get("message")),
        "notional": _text(
            request_payload.get("notional") or payload.get("requested_notional")
        ),
        "order_type": _text(request_payload.get("order_type")),
        "preview_only": bool(payload.get("preview_only", False)),
        "qty": _text(request_payload.get("qty") or payload.get("requested_qty")),
        "redacted_exception_message": _optional_text(
            payload.get("redacted_exception_message")
        ),
        "side": _text(request_payload.get("side") or payload.get("side")),
        "sizing_mode": _text(payload.get("sizing_mode")),
        "symbol": _text(request_payload.get("symbol") or payload.get("symbol")),
        "submission_disabled_reason": _optional_text(
            payload.get("submission_disabled_reason")
        ),
        "time_in_force": _text(request_payload.get("time_in_force")),
    }
    if broker_result is not None:
        fields["broker_result"] = broker_result
    return fields


def _snapshot_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "account_observation_available": bool(
            payload.get("account_observation_available", False)
        ),
        "error": _optional_text(payload.get("error")),
        "gate_summary": _gate_summary(payload.get("gates")),
        "mutated": bool(payload.get("mutated", False)),
        "ok": bool(payload.get("ok", False)),
        "orders_observation_available": bool(
            payload.get("orders_observation_available", False)
        ),
        "position_count": payload.get("position_count", 0),
        "position_symbols": payload.get("position_symbols", ()),
        "positions_observation_available": bool(
            payload.get("positions_observation_available", False)
        ),
        "recent_order_count": payload.get("recent_order_count", 0),
        "submitted": bool(payload.get("submitted", False)),
        "unavailable_observations": payload.get("unavailable_observations", ()),
        "unavailable_reasons": payload.get("unavailable_reasons", {}),
    }


def _state_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "accepted": payload.get("accepted"),
        "broker_response_parsed": bool(payload.get("broker_response_parsed", False)),
        "broker_response_received": bool(
            payload.get("broker_response_received", False)
        ),
        "filled": payload.get("filled"),
        "submitted": payload.get("submitted", False),
        "submit_attempted": bool(payload.get("submit_attempted", False)),
        "submit_requested": bool(payload.get("submit_requested", False)),
    }


def _gate_summary(gates: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(gates, Mapping):
        return {}

    summary: dict[str, dict[str, Any]] = {}
    for gate_name, gate_value in gates.items():
        if not isinstance(gate_value, Mapping):
            continue
        summary[str(gate_name)] = {
            "detail": _text(gate_value.get("detail")),
            "passed": bool(gate_value.get("passed", False)),
        }
    return summary


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    return str(value)


def _redact_value(value: Any, secret_values: Iterable[str | None]) -> Any:
    secrets = tuple(str(secret) for secret in secret_values if secret)
    if isinstance(value, Mapping):
        return {
            key: _redact_value(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item, secrets) for item in value]
    if isinstance(value, str):
        redacted = value
        for secret in secrets:
            redacted = redacted.replace(secret, "<redacted>")
        return redacted

    return value


def _optional_text(value: Any) -> str:
    return _text(value) if value else ""


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


__all__ = [
    "EVENT_TYPES",
    "PAPER_ACCOUNT_OBSERVED",
    "PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED",
    "PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED",
    "PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED",
    "PAPER_LAB_SNAPSHOT_REQUESTED",
    "PAPER_LAB_SNAPSHOT_UNAVAILABLE",
    "PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED",
    "PAPER_ORDER_PREVIEWED",
    "PAPER_ORDER_RECEIPT_OBSERVED",
    "PAPER_ORDER_RESPONSE_PARSE_FAILED",
    "PAPER_ORDER_SUBMIT_FAILED",
    "PAPER_ORDER_SUBMIT_ATTEMPTED",
    "PAPER_ORDER_SUBMIT_REQUESTED",
    "PAPER_POSITIONS_OBSERVED",
    "PaperLabObservationEvent",
    "PaperLabRunLogError",
    "append_jsonl_records",
    "ensure_run_log_path",
    "generate_run_id",
    "make_account_smoke_events",
    "make_order_probe_initial_events",
    "make_order_probe_submit_events",
    "make_paper_lab_snapshot_events",
    "render_jsonl_records",
    "resolve_run_id",
]
