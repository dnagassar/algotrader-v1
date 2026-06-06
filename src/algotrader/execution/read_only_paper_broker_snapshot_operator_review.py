"""Offline operator review for read-only paper broker snapshot artifacts.

This module consumes a local read-only broker snapshot/reconciliation JSONL
artifact and writes one sanitized operator-review packet. It performs no broker
calls, credential loading, runtime config loading, or network access.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND",
    "ReadOnlyPaperBrokerSnapshotOperatorReviewConfig",
    "ReadOnlyPaperBrokerSnapshotOperatorReviewWriteResult",
    "build_read_only_paper_broker_snapshot_operator_review",
    "render_read_only_paper_broker_snapshot_operator_review_json",
    "render_read_only_paper_broker_snapshot_operator_review_text",
    "write_read_only_paper_broker_snapshot_operator_review_jsonl",
]


READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND = (
    "paper-lab-read-only-broker-snapshot-operator-review"
)

_MILESTONE = (
    "M405 - Offline Operator Review Packet for M404 Read-Only Broker Snapshot"
)
_RECORD_TYPE = "paper_lab_read_only_broker_snapshot_operator_review"
_SCHEMA_VERSION = 1
_SOURCE_RECORD_TYPE = "read_only_paper_broker_snapshot_reconciliation"
_SOURCE_COMMAND = "paper-lab-read-only-broker-snapshot-reconciliation"
_SOURCE_READY_RECONCILIATION_STATE = "ready_for_operator_review"
_CLEAN_REVIEW_STATE = "operator_review_complete"
_BLOCKED_REVIEW_STATE = "blocked_operator_review"
_CLEAN_RESULT = "clean_flat_no_open_orders"
_CLEAN_NEXT_ACTION = "no_submit_operator_review_complete"
_BLOCKED_NEXT_ACTION = "resolve_blockers_before_any_paper_submit_review"
_PROFIT_CLAIM = "none"
_LABELS = (
    "paper_lab_only",
    "operator_review_only",
    "offline_review_only",
    "not_live_authorized",
    "profit_claim=none",
)
_BROKER_ACTION_FLAGS = {
    "submit": False,
    "cancel": False,
    "replace": False,
    "close": False,
    "liquidate": False,
    "mutation": False,
}
_SOURCE_REQUIRED_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "submit_authorized",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "broker_mutation_allowed",
    "paper_execution_authorized",
    "broker_action_performed",
    "broker_actions_performed",
    "live_authorized",
)
_OUTPUT_FALSE_FIELDS = (
    "paper_execution_authorized",
    "paper_submit_authorized",
    "submit_authorized",
    "broker_mutation_authorized",
    "broker_mutation_allowed",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_OPEN_ORDER_STATUSES = frozenset(
    {
        "accepted",
        "accepted_for_bidding",
        "calculated",
        "held",
        "new",
        "open",
        "partially_filled",
        "pending_cancel",
        "pending_new",
        "pending_replace",
    }
)


@dataclass(frozen=True, slots=True)
class ReadOnlyPaperBrokerSnapshotOperatorReviewConfig:
    """Explicit local inputs for one offline operator-review packet."""

    run_id: str
    source_snapshot_log: Path | str
    run_log: Path | str
    generated_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_snapshot_log",
            _local_jsonl_path(self.source_snapshot_log, "source_snapshot_log"),
        )
        object.__setattr__(self, "run_log", _output_jsonl_path(self.run_log))
        if self.generated_at is not None:
            object.__setattr__(
                self,
                "generated_at",
                _timezone_aware_timestamp(self.generated_at, "generated_at"),
            )


@dataclass(frozen=True, slots=True)
class ReadOnlyPaperBrokerSnapshotOperatorReviewWriteResult:
    """Local JSONL write metadata for the single M405 review record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    paper_execution_authorized: bool
    submit_authorized: bool
    broker_mutation_authorized: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_actions_performed: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_jsonl_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if self.newline_terminated is not True:
            raise ValidationError("newline_terminated must be true.")
        for field_name in (
            "paper_execution_authorized",
            "submit_authorized",
            "broker_mutation_authorized",
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_actions_performed",
            "network_access_attempted",
            "credential_access_attempted",
            "live_authorized",
        ):
            if getattr(self, field_name) is not False:
                raise ValidationError(f"{field_name} must be false.")

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "paper_execution_authorized": self.paper_execution_authorized,
            "submit_authorized": self.submit_authorized,
            "broker_mutation_authorized": self.broker_mutation_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _SourceRecordLoad:
    record: Mapping[str, object] | None
    record_count: int
    record_line: int
    blockers: tuple[str, ...]


def build_read_only_paper_broker_snapshot_operator_review(
    config: ReadOnlyPaperBrokerSnapshotOperatorReviewConfig,
) -> dict[str, object]:
    """Build one sanitized offline M405 operator-review packet."""

    checked_config = _config(config)
    source_load = _load_latest_source_record(checked_config.source_snapshot_log)
    source_record = dict(source_load.record or {})

    position_summary = _position_observation_summary(source_record)
    open_order_summary = _open_order_observation_summary(source_record)
    recent_order_summary = _recent_order_context_summary(source_record)

    blockers = _dedupe(
        (
            *source_load.blockers,
            *_source_identity_blockers(source_record),
            *_source_safety_blockers(source_record),
            *_source_readiness_blockers(
                source_record,
                position_summary=position_summary,
                open_order_summary=open_order_summary,
            ),
            *_recent_open_context_blockers(source_record),
        )
    )

    clean = len(blockers) == 0
    review_state = _CLEAN_REVIEW_STATE if clean else _BLOCKED_REVIEW_STATE
    operator_review_result = (
        _CLEAN_RESULT if clean else f"blocked_{blockers[0]}"
    )
    next_action = _CLEAN_NEXT_ACTION if clean else _BLOCKED_NEXT_ACTION
    generated_at = checked_config.generated_at or _text(
        source_record.get("generated_at")
    )

    payload = {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": generated_at,
        "source_snapshot_log": str(checked_config.source_snapshot_log),
        "source_snapshot_record_count": source_load.record_count,
        "source_snapshot_record_line": source_load.record_line,
        "source_run_id": _text(source_record.get("run_id")),
        "source_reconciliation_state": _text(
            source_record.get("reconciliation_state")
        ),
        "review_state": review_state,
        "operator_review_result": operator_review_result,
        "next_action": next_action,
        "blockers": list(blockers),
        "position_observation_summary": position_summary,
        "open_order_observation_summary": open_order_summary,
        "recent_order_context_summary": recent_order_summary,
        "safety_attestations": _safety_attestations(),
        "operator_decision": {
            "paper_submit_approved": False,
            "paper_submit_requires_separate_milestone": True,
            "broker_observed_state_clean": clean,
        },
        "paper_lab_only": True,
        "operator_review_only": True,
        "offline_review_only": True,
        "read_only_broker_snapshot_operator_review": True,
        "labels": list(_LABELS),
        "profit_claim": _PROFIT_CLAIM,
        "not_live_authorized": True,
        "paper_execution_authorized": False,
        "paper_submit_authorized": False,
        "submit_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_action_flags": dict(_BROKER_ACTION_FLAGS),
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "forbidden_actions": _forbidden_actions(),
        "next_forbidden_action": _forbidden_actions(),
    }
    _validate_output_safety_fields(payload)
    return payload


def render_read_only_paper_broker_snapshot_operator_review_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_read_only_paper_broker_snapshot_operator_review_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing M405 review summary."""

    position_summary = _mapping(payload.get("position_observation_summary"))
    open_order_summary = _mapping(payload.get("open_order_observation_summary"))
    recent_order_summary = _mapping(payload.get("recent_order_context_summary"))
    return "\n".join(
        (
            "Read-only paper broker snapshot operator review",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"source_run_id: {payload.get('source_run_id', '')}",
            "source_reconciliation_state: "
            f"{payload.get('source_reconciliation_state', '')}",
            f"review_state: {payload.get('review_state', '')}",
            f"operator_review_result: {payload.get('operator_review_result', '')}",
            f"next_action: {payload.get('next_action', '')}",
            f"blockers: {_joined(_string_tuple(payload.get('blockers')))}",
            "positions_observed / position_count / spy_position_present: "
            f"{_bool_text(position_summary.get('positions_observed'))} / "
            f"{_none_text(position_summary.get('position_count'))} / "
            f"{_bool_text(position_summary.get('spy_position_present'))}",
            "open_orders_observed / open_order_count / open_spy_order_count: "
            f"{_bool_text(open_order_summary.get('open_orders_observed'))} / "
            f"{_none_text(open_order_summary.get('open_order_count'))} / "
            f"{_none_text(open_order_summary.get('open_spy_order_count'))}",
            "recent_orders_observed / recent_order_count / recent_spy_order_count: "
            f"{_bool_text(recent_order_summary.get('recent_orders_observed'))} / "
            f"{_none_text(recent_order_summary.get('recent_order_count'))} / "
            f"{_none_text(recent_order_summary.get('recent_spy_order_count'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_mutation_authorized: "
            f"{_bool_text(payload.get('broker_mutation_authorized'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_read_only_paper_broker_snapshot_operator_review_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> ReadOnlyPaperBrokerSnapshotOperatorReviewWriteResult:
    """Write exactly one M405 JSONL record, replacing prior contents."""

    path = _output_jsonl_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    checked_payload = dict(payload)
    _validate_output_safety_fields(checked_payload)
    line = render_read_only_paper_broker_snapshot_operator_review_json(
        checked_payload
    ) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return ReadOnlyPaperBrokerSnapshotOperatorReviewWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        paper_execution_authorized=False,
        submit_authorized=False,
        broker_mutation_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _load_latest_source_record(path: Path) -> _SourceRecordLoad:
    if not path.exists() or not path.is_file():
        return _SourceRecordLoad(
            record=None,
            record_count=0,
            record_line=0,
            blockers=("source_snapshot_log_missing",),
        )

    lines = path.read_text(encoding="utf-8").splitlines()
    non_empty = [
        (line_number, raw_line.strip())
        for line_number, raw_line in enumerate(lines, start=1)
        if raw_line.strip()
    ]
    if not non_empty:
        return _SourceRecordLoad(
            record=None,
            record_count=0,
            record_line=0,
            blockers=("source_snapshot_log_empty",),
        )

    line_number, latest_line = non_empty[-1]
    try:
        parsed = json.loads(latest_line)
    except json.JSONDecodeError:
        return _SourceRecordLoad(
            record=None,
            record_count=len(non_empty),
            record_line=line_number,
            blockers=("source_snapshot_log_invalid_json",),
        )
    if not isinstance(parsed, Mapping):
        return _SourceRecordLoad(
            record=None,
            record_count=len(non_empty),
            record_line=line_number,
            blockers=("source_snapshot_record_not_object",),
        )

    return _SourceRecordLoad(
        record=parsed,
        record_count=len(non_empty),
        record_line=line_number,
        blockers=(),
    )


def _source_identity_blockers(source_record: Mapping[str, object]) -> tuple[str, ...]:
    if not source_record:
        return ()

    blockers: list[str] = []
    if source_record.get("record_type") != _SOURCE_RECORD_TYPE:
        blockers.append("source_record_type_unexpected")
    if source_record.get("command") != _SOURCE_COMMAND:
        blockers.append("source_command_unexpected")
    return tuple(blockers)


def _source_safety_blockers(source_record: Mapping[str, object]) -> tuple[str, ...]:
    if not source_record:
        return ()

    blockers: list[str] = []
    for field_name in _SOURCE_REQUIRED_FALSE_FIELDS:
        value = source_record.get(field_name)
        if value is True:
            blockers.append(f"source_{field_name}_true")
        elif value is not False:
            blockers.append(f"source_{field_name}_missing_or_not_false")

    if source_record.get("read_only_broker_observation") is not True:
        blockers.append("source_read_only_broker_observation_missing_or_false")

    flags = source_record.get("broker_action_flags")
    if isinstance(flags, Mapping):
        for action in ("submit", "cancel", "replace", "close", "liquidate", "mutation"):
            if flags.get(action) is True:
                blockers.append(f"source_broker_action_flag_{action}_true")
    return _dedupe(tuple(blockers))


def _source_readiness_blockers(
    source_record: Mapping[str, object],
    *,
    position_summary: Mapping[str, object],
    open_order_summary: Mapping[str, object],
) -> tuple[str, ...]:
    if not source_record:
        return ()

    blockers: list[str] = []
    if source_record.get("reconciliation_state") != _SOURCE_READY_RECONCILIATION_STATE:
        blockers.append("source_reconciliation_state_not_ready_for_operator_review")

    source_blockers = _string_tuple(source_record.get("blockers"))
    if source_blockers:
        blockers.append("source_blockers_present")

    if position_summary.get("positions_observed") is not True:
        blockers.append("positions_not_observed")

    position_count = position_summary.get("position_count")
    if position_count != 0:
        blockers.append(
            "position_count_nonzero"
            if isinstance(position_count, int)
            else "position_count_missing_or_not_zero"
        )

    if source_record.get("spy_position_present") is True:
        blockers.append("spy_position_present")
    elif source_record.get("spy_position_present") is not False:
        blockers.append("spy_position_present_missing_or_not_false")

    if open_order_summary.get("open_orders_observed") is not True:
        blockers.append("open_orders_not_observed")

    open_order_count = open_order_summary.get("open_order_count")
    if open_order_count != 0:
        blockers.append(
            "open_order_count_nonzero"
            if isinstance(open_order_count, int)
            else "open_order_count_missing_or_not_zero"
        )

    open_spy_order_count = open_order_summary.get("open_spy_order_count")
    if open_spy_order_count != 0:
        blockers.append(
            "open_spy_order_count_nonzero"
            if isinstance(open_spy_order_count, int)
            else "open_spy_order_count_missing_or_not_zero"
        )

    return _dedupe(tuple(blockers))


def _position_observation_summary(
    source_record: Mapping[str, object],
) -> dict[str, object]:
    return {
        "positions_observed": source_record.get("positions_observed") is True,
        "position_count": _payload_int_or_none(source_record.get("position_count")),
        "position_symbols": list(
            _symbols_from_summary_or_rows(
                source_record,
                summary_key="position_symbols",
                rows_key="positions",
            )
        ),
        "spy_position_present": source_record.get("spy_position_present") is True,
    }


def _open_order_observation_summary(
    source_record: Mapping[str, object],
) -> dict[str, object]:
    return {
        "open_orders_observed": source_record.get("open_orders_observed") is True,
        "open_order_count": _payload_int_or_none(source_record.get("open_order_count")),
        "open_order_symbols": list(
            _symbols_from_summary_or_rows(
                source_record,
                summary_key="open_order_symbols",
                rows_key="open_orders",
            )
        ),
        "open_spy_order_count": _payload_int_or_none(
            source_record.get("open_spy_order_count")
        ),
    }


def _recent_order_context_summary(
    source_record: Mapping[str, object],
) -> dict[str, object]:
    recent_order_symbols = _symbols_from_summary_or_rows(
        source_record,
        summary_key="recent_order_symbols",
        rows_key="recent_orders",
    )
    recent_order_count = _payload_int_or_none(source_record.get("recent_order_count"))
    if recent_order_count is None:
        recent_order_count = len(_mapping_list(source_record.get("recent_orders")))
    recent_spy_order_count = _payload_int_or_none(
        source_record.get("recent_spy_order_count")
    )
    if recent_spy_order_count is None:
        recent_spy_order_count = sum(1 for symbol in recent_order_symbols if symbol == "SPY")

    return {
        "recent_orders_observed": source_record.get("recent_orders_observed") is True,
        "recent_order_count": recent_order_count,
        "recent_order_symbols": list(recent_order_symbols),
        "recent_spy_order_count": recent_spy_order_count,
        "recent_orders_are_context_only": True,
    }


def _recent_open_context_blockers(
    source_record: Mapping[str, object],
) -> tuple[str, ...]:
    if not source_record:
        return ()

    blockers: list[str] = []
    for order in _mapping_list(source_record.get("recent_orders")):
        status = _text(order.get("status")).strip().lower()
        if status in _OPEN_ORDER_STATUSES:
            blockers.append("recent_order_context_contains_open_status")
            if _text(order.get("symbol")).strip().upper() == "SPY":
                blockers.append("recent_spy_order_context_contains_open_status")
    return _dedupe(tuple(blockers))


def _symbols_from_summary_or_rows(
    source_record: Mapping[str, object],
    *,
    summary_key: str,
    rows_key: str,
) -> tuple[str, ...]:
    summary_symbols = _string_tuple(source_record.get(summary_key))
    if summary_symbols:
        return tuple(sorted({symbol.strip().upper() for symbol in summary_symbols if symbol}))

    rows = _mapping_list(source_record.get(rows_key))
    return tuple(
        sorted(
            {
                symbol
                for row in rows
                if (symbol := _text(row.get("symbol")).strip().upper())
            }
        )
    )


def _safety_attestations() -> dict[str, object]:
    return {
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "credential_access_attempted": False,
        "network_access_attempted": False,
        "offline_review_only": True,
    }


def _forbidden_actions() -> list[str]:
    return [
        "paper_submit_from_read_only_broker_snapshot_operator_review",
        "broker_mutation_from_read_only_broker_snapshot_operator_review",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_operator_review",
    ]


def _validate_output_safety_fields(payload: Mapping[str, object]) -> None:
    for field_name in _OUTPUT_FALSE_FIELDS:
        if payload.get(field_name) is not False:
            raise ValidationError(f"{field_name} must be false.")
    flags = payload.get("broker_action_flags")
    if not isinstance(flags, Mapping):
        raise ValidationError("broker_action_flags must be present.")
    for action in ("submit", "cancel", "replace", "close", "liquidate", "mutation"):
        if flags.get(action) is not False:
            raise ValidationError(f"broker_action_flags.{action} must be false.")

    safety_attestations = payload.get("safety_attestations")
    if not isinstance(safety_attestations, Mapping):
        raise ValidationError("safety_attestations must be present.")
    for field_name in (
        "submitted",
        "mutated",
        "submit_authorized",
        "broker_mutation_authorized",
        "live_authorized",
        "credential_access_attempted",
        "network_access_attempted",
    ):
        if safety_attestations.get(field_name) is not False:
            raise ValidationError(f"safety_attestations.{field_name} must be false.")
    if safety_attestations.get("offline_review_only") is not True:
        raise ValidationError("safety_attestations.offline_review_only must be true.")


def _config(value: object) -> ReadOnlyPaperBrokerSnapshotOperatorReviewConfig:
    if type(value) is not ReadOnlyPaperBrokerSnapshotOperatorReviewConfig:
        raise ValidationError(
            "config must be a ReadOnlyPaperBrokerSnapshotOperatorReviewConfig."
        )
    return value


def _local_jsonl_path(value: object, field_name: str) -> Path:
    path = _required_path(value, field_name)
    if type(value) is str and "://" in value:
        raise ValidationError(f"{field_name} must be a local JSONL path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must reference a JSONL file.")
    return path


def _output_jsonl_path(value: object) -> Path:
    path = _local_jsonl_path(value, "run_log")
    if path.exists() and path.is_dir():
        raise ValidationError("run_log must not be a directory.")
    return path


def _required_path(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _timezone_aware_timestamp(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return text


def _payload_int_or_none(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    return None


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _mapping_list(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    rows: list[Mapping[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append(item)
    return tuple(rows)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_json_safe(item) for item in value]
    if type(value) is list:
        return [_json_safe(item) for item in value]
    return value


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _none_text(value: object) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
