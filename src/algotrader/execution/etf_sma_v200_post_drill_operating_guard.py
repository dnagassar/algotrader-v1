"""v2.00 post-drill operating guard from a local v1.99 drill packet.

This module reads caller-supplied local JSON artifacts only. It does not load
profiles, inspect credentials, import broker SDKs, open sockets, or expose any
broker mutation path.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


V200_RUN_ID = "v200_post_drill_operating_guard"
V200_DEFAULT_OUTPUT_ROOT = "runs/paper_lab/v200_post_drill_operating_guard"
V200_DEFAULT_SOURCE_PACKET_PATH = (
    "runs/paper_lab/v199_authorized_bounded_spy_paper_drill_authorized_retry/"
    "paper_drill_packet.json"
)
V200_PACKET_VERSION = "v200_post_drill_operating_guard_packet_v1"
V200_MANIFEST_VERSION = "v200_post_drill_operating_guard_manifest_v1"

POST_DRILL_GUARD_READY = "post_drill_guard_ready"
POST_DRILL_GUARD_BLOCKED_PACKET_MISSING = (
    "post_drill_guard_blocked_packet_missing"
)
POST_DRILL_GUARD_BLOCKED_PACKET_MALFORMED = (
    "post_drill_guard_blocked_packet_malformed"
)
POST_DRILL_GUARD_BLOCKED_UNRESOLVED_OUTCOME = (
    "post_drill_guard_blocked_unresolved_outcome"
)
POST_DRILL_GUARD_BLOCKED_LIVE_ACTIVITY = (
    "post_drill_guard_blocked_live_activity"
)
POST_DRILL_GUARD_BLOCKED_UNEXPECTED_MUTATION_STATE = (
    "post_drill_guard_blocked_unexpected_mutation_state"
)

PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED = (
    "paper_drill_submitted_cancel_confirmed"
)
PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL = (
    "paper_drill_submitted_filled_before_cancel"
)
PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED = (
    "paper_drill_submitted_partial_fill_then_cancelled"
)
PAPER_DRILL_SUBMITTED_THEN_REJECTED = "paper_drill_submitted_then_rejected"
PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE = "paper_drill_blocked_pre_submit_gate"
PAPER_DRILL_BLOCKED_EXPECTED_ACCOUNT_MISMATCH = (
    "paper_drill_blocked_expected_account_mismatch"
)
PAPER_DRILL_BLOCKED_LIVE_ENDPOINT_OR_PROFILE = (
    "paper_drill_blocked_live_endpoint_or_profile"
)
PAPER_DRILL_BLOCKED_OPEN_SPY_ORDER_PRESENT = (
    "paper_drill_blocked_open_spy_order_present"
)
PAPER_DRILL_BLOCKED_UNEXPECTED_NON_SPY_POSITION = (
    "paper_drill_blocked_unexpected_non_spy_position"
)
PAPER_DRILL_BLOCKED_DUPLICATE_CLIENT_ORDER_ID = (
    "paper_drill_blocked_duplicate_client_order_id"
)
PAPER_DRILL_BLOCKED_ACCOUNT_NOT_TRADABLE = (
    "paper_drill_blocked_account_not_tradable"
)
PAPER_DRILL_BLOCKED_APPROVAL_PACKET_NOT_READY = (
    "paper_drill_blocked_approval_packet_not_ready"
)
PAPER_DRILL_BLOCKED_BROKER_RESPONSE_AMBIGUOUS = (
    "paper_drill_blocked_broker_response_ambiguous"
)
PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME = "paper_drill_unresolved_order_outcome"
PAPER_DRILL_CANCEL_AMBIGUOUS_RECONCILED = (
    "paper_drill_cancel_ambiguous_reconciled"
)

RECOGNIZED_V199_PAPER_DRILL_OUTCOMES = (
    PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED,
    PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL,
    PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED,
    PAPER_DRILL_SUBMITTED_THEN_REJECTED,
    PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE,
    PAPER_DRILL_BLOCKED_EXPECTED_ACCOUNT_MISMATCH,
    PAPER_DRILL_BLOCKED_LIVE_ENDPOINT_OR_PROFILE,
    PAPER_DRILL_BLOCKED_OPEN_SPY_ORDER_PRESENT,
    PAPER_DRILL_BLOCKED_UNEXPECTED_NON_SPY_POSITION,
    PAPER_DRILL_BLOCKED_DUPLICATE_CLIENT_ORDER_ID,
    PAPER_DRILL_BLOCKED_ACCOUNT_NOT_TRADABLE,
    PAPER_DRILL_BLOCKED_APPROVAL_PACKET_NOT_READY,
    PAPER_DRILL_BLOCKED_BROKER_RESPONSE_AMBIGUOUS,
    PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME,
    PAPER_DRILL_CANCEL_AMBIGUOUS_RECONCILED,
)

POST_DRILL_GUARD_SAFETY_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "not_live_trading",
    "profit_claim=none",
    "post_drill_guard",
    "paper_submit_authorized=false",
)

_LIVE_ACTIVITY_FIELDS = (
    "live_read_performed",
    "live_mutation_performed",
    "live_trading_performed",
)
_READY_FINAL_ORDER_STATUSES = {"canceled", "cancelled"}
_READY_NEXT_OPERATOR_ACTION = (
    "new_explicit_operator_authorization_required_before_any_future_paper_action"
)
_BLOCKED_NEXT_OPERATOR_ACTION = (
    "repair_or_review_v199_drill_packet_before_any_future_paper_action"
)


@dataclass(frozen=True, slots=True)
class _SourceRead:
    path: Path
    found: bool
    parsed: bool
    payload: dict[str, object]
    error: str


def run_v200_post_drill_operating_guard(
    *,
    source_paper_drill_packet_path: Path | str = V200_DEFAULT_SOURCE_PACKET_PATH,
    output_root: Path | str = V200_DEFAULT_OUTPUT_ROOT,
    run_id: str = V200_RUN_ID,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Consume a local v1.99 drill packet and write the post-drill guard state."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    source_path = _resolve_source_packet_path(source_paper_drill_packet_path)
    source_read = _read_source_packet(source_path)
    packet = build_v200_post_drill_operating_guard_packet(
        source_read=source_read,
        output_root=root,
        run_id=run_id,
        timestamp=timestamp or _utc_now_text(),
    )
    _write_artifacts(root, packet)
    return packet


def build_v200_post_drill_operating_guard_packet(
    *,
    source_read: _SourceRead,
    output_root: Path,
    run_id: str,
    timestamp: str,
) -> dict[str, object]:
    """Build one guard packet from an already-read local v1.99 packet."""

    source = source_read.payload
    classification, blocker, blockers = _classify_source(source_read)
    latest = _latest_drill_summary(source)
    last_authorization_consumed = classification == POST_DRILL_GUARD_READY
    next_operator_action = (
        _READY_NEXT_OPERATOR_ACTION
        if classification == POST_DRILL_GUARD_READY
        else _BLOCKED_NEXT_OPERATOR_ACTION
    )

    packet: dict[str, object] = {
        "packet_version": V200_PACKET_VERSION,
        "run_id": _text(run_id),
        "timestamp": _text(timestamp),
        "generated_at": _text(timestamp),
        "post_drill_guard_classification": classification,
        "outcome_classification": classification,
        "blocker": blocker,
        "blockers": blockers,
        "source_v199_paper_drill_packet_path": str(source_read.path),
        "source_paper_drill_packet_found": source_read.found,
        "source_paper_drill_packet_parsed": source_read.parsed,
        "source_paper_drill_packet_error": source_read.error,
        "source_paper_drill_outcome": latest["outcome_classification"],
        "last_paper_drill_outcome": latest["outcome_classification"],
        "latest_bounded_paper_drill": latest,
        "symbol": latest["symbol"],
        "side": latest["side"],
        "order_type": latest["order_type"],
        "time_in_force": latest["time_in_force"],
        "notional": latest["notional"],
        "quantity": latest["quantity"],
        "cap": latest["cap"],
        "client_order_id": latest["client_order_id"],
        "deterministic_client_order_id": latest["deterministic_client_order_id"],
        "submit_attempted_from_source_packet": latest["submit_attempted"],
        "submit_status_from_source_packet": latest["submit_status"],
        "cancel_attempted_from_source_packet": latest["cancel_attempted"],
        "cancel_confirmed_from_source_packet": latest["cancel_confirmed"],
        "fill_status_from_source_packet": latest["fill_status"],
        "final_broker_order_status_from_source_packet": latest[
            "final_broker_order_status"
        ],
        "source_broker_read_performed": latest["broker_read_performed"],
        "source_broker_mutation_performed": latest["broker_mutation_performed"],
        "source_paper_submit_performed": latest["paper_submit_performed"],
        "source_paper_cancel_performed": latest["paper_cancel_performed"],
        "source_live_read_performed": latest["live_read_performed"],
        "source_live_mutation_performed": latest["live_mutation_performed"],
        "source_live_trading_performed": latest["live_trading_performed"],
        "authorization_consumed_evidence_present": (
            _authorization_consumed_evidence_present(source)
        ),
        "last_authorization_consumed": last_authorization_consumed,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "next_paper_action_requires_new_authorization": True,
        "next_operator_action": next_operator_action,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "not_live_trading": True,
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "live_read_performed": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "credential_values_exposed": False,
        "account_identifiers_serialized": False,
        "safety_labels": list(POST_DRILL_GUARD_SAFETY_LABELS),
        "artifact_paths": _artifact_paths(output_root),
    }
    return packet


def render_v200_post_drill_guard_brief(packet: Mapping[str, object]) -> str:
    """Render a compact operator brief for Mission Control / daily lab use."""

    latest = _mapping(packet.get("latest_bounded_paper_drill"))
    return "\n".join(
        (
            "# v2.00 Post-Drill Operating Guard",
            "",
            f"- Classification: `{packet.get('post_drill_guard_classification', '')}`",
            f"- Blocker: `{packet.get('blocker', '')}`",
            f"- Source v1.99 packet: `{packet.get('source_v199_paper_drill_packet_path', '')}`",
            f"- Source outcome: `{packet.get('source_paper_drill_outcome', '')}`",
            f"- Symbol / side: `{latest.get('symbol', '')}` / `{latest.get('side', '')}`",
            f"- Order type / TIF: `{latest.get('order_type', '')}` / `{latest.get('time_in_force', '')}`",
            f"- Notional / quantity / cap: `{latest.get('notional', '')}` / `{latest.get('quantity', '')}` / `{latest.get('cap', '')}`",
            f"- Client order id: `{latest.get('client_order_id', '')}`",
            f"- Submit attempted / status: `{_bool_text(latest.get('submit_attempted'))}` / `{latest.get('submit_status', '')}`",
            f"- Cancel attempted / confirmed: `{_bool_text(latest.get('cancel_attempted'))}` / `{_bool_text(latest.get('cancel_confirmed'))}`",
            f"- Fill / final order status: `{latest.get('fill_status', '')}` / `{latest.get('final_broker_order_status', '')}`",
            f"- Source broker read / mutation: `{_bool_text(latest.get('broker_read_performed'))}` / `{_bool_text(latest.get('broker_mutation_performed'))}`",
            f"- Source paper submit / cancel: `{_bool_text(latest.get('paper_submit_performed'))}` / `{_bool_text(latest.get('paper_cancel_performed'))}`",
            f"- Source live read / mutation / trading: `{_bool_text(latest.get('live_read_performed'))}` / `{_bool_text(latest.get('live_mutation_performed'))}` / `{_bool_text(latest.get('live_trading_performed'))}`",
            f"- Authorization consumed: `{_bool_text(packet.get('last_authorization_consumed'))}`",
            f"- Paper submit authorized now: `{_bool_text(packet.get('paper_submit_authorized'))}`",
            f"- Paper cancel authorized now: `{_bool_text(packet.get('paper_cancel_authorized'))}`",
            f"- New authorization required: `{_bool_text(packet.get('next_paper_action_requires_new_authorization'))}`",
            f"- Next operator action: `{packet.get('next_operator_action', '')}`",
            f"- Safety labels: `{', '.join(_string_sequence(packet.get('safety_labels')))}`",
            "",
        )
    )


def _classify_source(source_read: _SourceRead) -> tuple[str, str, list[str]]:
    source = source_read.payload
    if not source_read.found:
        return _blocked(
            POST_DRILL_GUARD_BLOCKED_PACKET_MISSING,
            "source_v199_paper_drill_packet_missing",
        )
    if not source_read.parsed:
        return _blocked(
            POST_DRILL_GUARD_BLOCKED_PACKET_MALFORMED,
            source_read.error or "source_v199_paper_drill_packet_malformed",
        )

    live_fields = [
        field_name for field_name in _LIVE_ACTIVITY_FIELDS if source.get(field_name) is True
    ]
    if live_fields:
        return _blocked(
            POST_DRILL_GUARD_BLOCKED_LIVE_ACTIVITY,
            f"source_packet_live_activity:{','.join(live_fields)}",
        )

    outcome = _text(source.get("outcome_classification"))
    if outcome not in RECOGNIZED_V199_PAPER_DRILL_OUTCOMES:
        return _blocked(
            POST_DRILL_GUARD_BLOCKED_UNRESOLVED_OUTCOME,
            "source_packet_unrecognized_v199_outcome",
        )
    if outcome != PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED:
        return _blocked(
            POST_DRILL_GUARD_BLOCKED_UNRESOLVED_OUTCOME,
            "source_packet_outcome_not_post_drill_ready",
        )

    if not _authorization_consumed_evidence_present(source):
        return _blocked(
            POST_DRILL_GUARD_BLOCKED_UNEXPECTED_MUTATION_STATE,
            "missing_authorization_consumed_evidence",
        )

    state_blocker = _ready_source_state_blocker(source)
    if state_blocker:
        return _blocked(
            POST_DRILL_GUARD_BLOCKED_UNEXPECTED_MUTATION_STATE,
            state_blocker,
        )

    return POST_DRILL_GUARD_READY, "none", []


def _ready_source_state_blocker(source: Mapping[str, object]) -> str:
    latest = _latest_drill_summary(source)
    if latest["symbol"] != "SPY":
        return "source_symbol_outside_spy_scope"
    if latest["side"] != "buy":
        return "source_side_outside_buy_scope"
    if latest["order_type"] != "market":
        return "source_order_type_outside_market_scope"
    if latest["time_in_force"] != "day":
        return "source_time_in_force_outside_day_scope"
    if not latest["client_order_id"]:
        return "source_client_order_id_missing"
    deterministic_id = _text(latest["deterministic_client_order_id"])
    if deterministic_id and deterministic_id != latest["client_order_id"]:
        return "source_client_order_id_not_deterministic"
    if latest["submit_attempted"] is not True:
        return "source_submit_attempted_not_true"
    if latest["submit_status"] != "accepted":
        return "source_submit_status_not_accepted"
    if latest["cancel_attempted"] is not True:
        return "source_cancel_attempted_not_true"
    if latest["cancel_confirmed"] is not True:
        return "source_cancel_confirmed_not_true"
    if latest["fill_status"] != "unfilled":
        return "source_fill_status_not_unfilled"
    if latest["final_broker_order_status"] not in _READY_FINAL_ORDER_STATUSES:
        return "source_final_order_status_not_canceled"
    for field_name in (
        "broker_read_performed",
        "broker_mutation_performed",
        "paper_submit_performed",
        "paper_cancel_performed",
    ):
        if latest[field_name] is not True:
            return f"source_{field_name}_not_true"
    return ""


def _authorization_consumed_evidence_present(source: Mapping[str, object]) -> bool:
    labels = set(_string_sequence(source.get("safety_labels")))
    return (
        source.get("explicit_authorization_phrase_observed") is True
        and source.get("operator_authorized_once") is True
        and "operator_authorized_once" in labels
    )


def _latest_drill_summary(source: Mapping[str, object]) -> dict[str, object]:
    actual = _mapping(source.get("actual_submitted_request_fields"))
    projected = _mapping(source.get("projected_request_fields"))
    return {
        "packet_version": _text(source.get("packet_version")),
        "run_id": _text(source.get("run_id")),
        "timestamp": _first_text(source.get("timestamp"), source.get("generated_at")),
        "outcome_classification": _text(source.get("outcome_classification")),
        "symbol": _first_text(
            source.get("symbol"),
            actual.get("symbol"),
            projected.get("symbol"),
        ).upper(),
        "side": _first_text(source.get("side"), actual.get("side"), projected.get("side")).lower(),
        "order_type": _first_text(
            source.get("order_type"),
            actual.get("order_type"),
            projected.get("order_type"),
        ).lower(),
        "time_in_force": _first_text(
            source.get("time_in_force"),
            actual.get("time_in_force"),
            projected.get("time_in_force"),
        ).lower(),
        "notional": _first_text(
            source.get("notional"),
            actual.get("notional"),
            projected.get("notional"),
        ),
        "quantity": _first_text(
            source.get("quantity"),
            actual.get("quantity"),
            projected.get("quantity"),
        ),
        "cap": _first_text(source.get("cap"), projected.get("cap")),
        "client_order_id": _first_text(
            source.get("client_order_id"),
            actual.get("client_order_id"),
            projected.get("client_order_id"),
        ),
        "deterministic_client_order_id": _first_text(
            source.get("deterministic_client_order_id"),
            projected.get("deterministic_client_order_id"),
        ),
        "submit_attempted": source.get("submit_attempted") is True,
        "submit_status": _text(source.get("submit_status")).lower(),
        "cancel_attempted": source.get("cancel_attempted") is True,
        "cancel_confirmed": source.get("cancel_confirmed") is True,
        "fill_status": _text(source.get("fill_status")).lower(),
        "final_broker_order_status": _text(
            source.get("final_broker_order_status")
            or source.get("final_order_status")
        ).lower(),
        "broker_read_performed": source.get("broker_read_performed") is True,
        "broker_mutation_performed": source.get("broker_mutation_performed") is True,
        "paper_submit_performed": source.get("paper_submit_performed") is True,
        "paper_cancel_performed": source.get("paper_cancel_performed") is True,
        "live_read_performed": source.get("live_read_performed") is True,
        "live_mutation_performed": source.get("live_mutation_performed") is True,
        "live_trading_performed": source.get("live_trading_performed") is True,
    }


def _read_source_packet(path: Path) -> _SourceRead:
    if not path.exists():
        return _SourceRead(
            path=path,
            found=False,
            parsed=False,
            payload={},
            error="path_not_found",
        )
    if not path.is_file():
        return _SourceRead(
            path=path,
            found=True,
            parsed=False,
            payload={},
            error="path_not_file",
        )
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _SourceRead(
            path=path,
            found=True,
            parsed=False,
            payload={},
            error="invalid_json",
        )
    except OSError:
        return _SourceRead(
            path=path,
            found=True,
            parsed=False,
            payload={},
            error="unreadable_file",
        )
    if not isinstance(parsed, Mapping):
        return _SourceRead(
            path=path,
            found=True,
            parsed=False,
            payload={},
            error="json_payload_not_object",
        )
    return _SourceRead(
        path=path,
        found=True,
        parsed=True,
        payload=dict(parsed),
        error="",
    )


def _write_artifacts(root: Path, packet: Mapping[str, object]) -> None:
    packet_path = root / "post_drill_guard_packet.json"
    brief_path = root / "post_drill_guard_brief.md"
    record_path = root / "post_drill_guard_record.jsonl"
    manifest_path = root / "manifest.jsonl"

    _write_json(packet_path, packet)
    brief_path.write_text(
        render_v200_post_drill_guard_brief(packet),
        encoding="utf-8",
        newline="\n",
    )
    record_path.write_text(
        json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "manifest_version": V200_MANIFEST_VERSION,
        "run_id": packet["run_id"],
        "generated_at": packet["generated_at"],
        "post_drill_guard_classification": packet[
            "post_drill_guard_classification"
        ],
        "source_v199_paper_drill_packet_path": packet[
            "source_v199_paper_drill_packet_path"
        ],
        "source_paper_drill_outcome": packet["source_paper_drill_outcome"],
        "last_authorization_consumed": packet["last_authorization_consumed"],
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "next_paper_action_requires_new_authorization": True,
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "live_read_performed": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "artifacts": {
            "post_drill_guard_packet": _artifact_entry(packet_path),
            "post_drill_guard_brief": _artifact_entry(brief_path),
            "post_drill_guard_record": _artifact_entry(record_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_paths(root: Path) -> dict[str, str]:
    return {
        "post_drill_guard_packet": str(root / "post_drill_guard_packet.json"),
        "post_drill_guard_brief": str(root / "post_drill_guard_brief.md"),
        "post_drill_guard_record": str(root / "post_drill_guard_record.jsonl"),
        "manifest": str(root / "manifest.jsonl"),
    }


def _blocked(classification: str, blocker: str) -> tuple[str, str, list[str]]:
    return classification, blocker, [blocker]


def _resolve_source_packet_path(value: Path | str) -> Path:
    path = Path(value)
    if path.exists() and path.is_dir():
        return path / "paper_drill_packet.json"
    return path


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_entry(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _first_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false" if value is False else ""


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "POST_DRILL_GUARD_BLOCKED_LIVE_ACTIVITY",
    "POST_DRILL_GUARD_BLOCKED_PACKET_MALFORMED",
    "POST_DRILL_GUARD_BLOCKED_PACKET_MISSING",
    "POST_DRILL_GUARD_BLOCKED_UNEXPECTED_MUTATION_STATE",
    "POST_DRILL_GUARD_BLOCKED_UNRESOLVED_OUTCOME",
    "POST_DRILL_GUARD_READY",
    "POST_DRILL_GUARD_SAFETY_LABELS",
    "RECOGNIZED_V199_PAPER_DRILL_OUTCOMES",
    "V200_DEFAULT_OUTPUT_ROOT",
    "V200_DEFAULT_SOURCE_PACKET_PATH",
    "V200_RUN_ID",
    "build_v200_post_drill_operating_guard_packet",
    "render_v200_post_drill_guard_brief",
    "run_v200_post_drill_operating_guard",
]
