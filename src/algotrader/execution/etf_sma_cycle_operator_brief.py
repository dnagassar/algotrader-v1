"""Offline operator brief for unified ETF/SMA cycle artifacts.

This module reads one caller-supplied local JSONL artifact only. It never loads
profiles, reads credentials, imports broker SDKs, opens sockets, or exposes any
broker mutation behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_CYCLE_OPERATOR_BRIEF_LABELS",
    "EtfSmaCycleOperatorBriefConfig",
    "EtfSmaCycleOperatorBriefWriteResult",
    "build_etf_sma_cycle_operator_brief",
    "render_etf_sma_cycle_operator_brief_json",
    "render_etf_sma_cycle_operator_brief_text",
    "write_etf_sma_cycle_operator_brief_jsonl",
]


ETF_SMA_CYCLE_OPERATOR_BRIEF_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M395 - ETF/SMA cycle operator brief/checkpoint"
_RECORD_TYPE = "etf_sma_cycle_operator_brief"
_COMMAND = "etf-sma-cycle-brief"
_SOURCE_RECORD_TYPE = "etf_sma_cycle_unified_preview"
_DEFAULT_SYMBOL = "SPY"
_PROFIT_CLAIM = "none"
_SOURCE_ARTIFACT_BLOCKER = "missing_or_invalid_cycle_artifact"
_UNEXPECTED_RECORD_TYPE_BLOCKER = "unexpected_cycle_record_type"
_SOURCE_SAFETY_BLOCKER = "source_artifact_safety_flags_not_false"
_WRITE_RESULT_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SOURCE_FALSE_FIELDS = (
    *_WRITE_RESULT_FALSE_FIELDS,
    "broker_mutation_allowed",
)
_FORBIDDEN_RECOMMENDATION_TERMS = (
    "broker",
    "cancel",
    "close",
    "delete",
    "liquidate",
    "live",
    "replace",
    "retry",
    "submit",
)


@dataclass(frozen=True, slots=True)
class EtfSmaCycleOperatorBriefConfig:
    """Explicit local inputs for one deterministic operator brief."""

    run_id: str
    cycle_log: Path | str
    generated_at: datetime | str
    symbol: str = _DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "cycle_log",
            _required_path(self.cycle_log, "cycle_log"),
        )
        object.__setattr__(
            self,
            "generated_at",
            _generated_at_text(self.generated_at),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaCycleOperatorBriefWriteResult:
    """Local JSONL write metadata for a single operator brief record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_actions_performed: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        for field_name in _WRITE_RESULT_FALSE_FIELDS:
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _ArtifactRead:
    path: Path
    found: bool
    parsed: bool
    record_count: int
    latest_record: dict[str, object] | None
    error: str

    def summary(self) -> dict[str, object]:
        latest = self.latest_record or {}
        return {
            "path": str(self.path),
            "found": self.found,
            "parsed": self.parsed,
            "record_count": self.record_count,
            "latest_run_id": _text(latest.get("run_id")),
            "latest_record_type": _text(latest.get("record_type")),
            "error": self.error,
        }


def build_etf_sma_cycle_operator_brief(
    config: EtfSmaCycleOperatorBriefConfig,
) -> dict[str, object]:
    """Build one fail-closed operator brief from a local unified cycle artifact."""

    checked_config = _config(config)
    cycle_artifact = _read_jsonl_artifact(checked_config.cycle_log)
    cycle_record = cycle_artifact.latest_record or {}
    source_metadata = cycle_artifact.summary()
    cycle_record_type = _text(cycle_record.get("record_type"))
    cycle_next_allowed_action = _text(cycle_record.get("cycle_next_allowed_action"))
    open_order_count = _first_int(cycle_record.get("open_order_count"))
    open_order_present = cycle_record.get("open_order_present") is True
    open_spy_order_present = cycle_record.get("open_spy_order_present") is True
    m376_terminal = cycle_record.get("m376_terminal") is True
    m376_terminal_state = _text(cycle_record.get("m376_terminal_state"))
    blockers = _operator_blockers(
        cycle_artifact,
        cycle_record,
        cycle_record_type,
        m376_terminal,
        m376_terminal_state,
        open_order_count,
        open_order_present,
        open_spy_order_present,
    )
    recommended_next_action = _recommended_next_action(
        blockers,
        cycle_next_allowed_action,
    )
    operator_brief_status = "blocked" if blockers else "review_only"

    state_summary = {
        "operator_brief_status": operator_brief_status,
        "cycle_decision": _text(cycle_record.get("cycle_decision")),
        "cycle_decision_reason": _text(cycle_record.get("cycle_decision_reason")),
        "cycle_next_allowed_action": cycle_next_allowed_action,
        "recommended_next_action": recommended_next_action,
        "m376_terminal": m376_terminal,
        "m376_status": _text(cycle_record.get("m376_status")),
        "m376_terminal_state": m376_terminal_state,
        "open_order_count": open_order_count,
        "open_order_present": open_order_present,
        "open_spy_order_present": open_spy_order_present,
        "spy_position_qty": _text(cycle_record.get("spy_position_qty")),
        "blockers": blockers,
    }
    safety_summary = {
        "paper_lab_only": True,
        "broker_mutation_allowed": False,
        "not_live_authorized": True,
        "live_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "source_safety_flags_preserved": _source_safety_flags_preserved(
            cycle_record
        ),
    }

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": checked_config.generated_at,
        "as_of": checked_config.generated_at,
        "symbol": checked_config.symbol,
        "scope": "SPY_paper_lab_only",
        "labels": list(ETF_SMA_CYCLE_OPERATOR_BRIEF_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "source_cycle_log": str(checked_config.cycle_log),
        "source_cycle_artifact": source_metadata,
        "source_artifacts": {
            "cycle_log": source_metadata,
        },
        "cycle_record_found": cycle_artifact.found,
        "cycle_record_parsed": cycle_artifact.parsed,
        "cycle_record_type": cycle_record_type,
        "cycle_record_type_expected": _SOURCE_RECORD_TYPE,
        "cycle_run_id": _text(cycle_record.get("run_id")),
        "cycle_generated_at": _text(cycle_record.get("generated_at")),
        "cycle_decision": _text(cycle_record.get("cycle_decision")),
        "cycle_decision_reason": _text(cycle_record.get("cycle_decision_reason")),
        "cycle_next_allowed_action": cycle_next_allowed_action,
        "cycle_next_allowed_action_safe": _safe_action(cycle_next_allowed_action),
        "operator_brief_status": operator_brief_status,
        "state_summary": state_summary,
        "safety_summary": safety_summary,
        "operator_summary": _operator_summary(
            operator_brief_status,
            state_summary,
        ),
        "recommended_next_action": recommended_next_action,
        "next_allowed_action": recommended_next_action,
        "blockers": blockers,
        "m376_terminal": m376_terminal,
        "m376_status": _text(cycle_record.get("m376_status")),
        "m376_observed_status": _text(cycle_record.get("m376_observed_status")),
        "m376_terminal_state": m376_terminal_state,
        "m376_terminal_reason": _text(cycle_record.get("m376_terminal_reason")),
        "m376_terminal_state_conflict": (
            cycle_record.get("m376_terminal_state_conflict") is True
        ),
        "m376_nonterminal": cycle_record.get("m376_nonterminal") is True,
        "m376_order_nonterminal": (
            cycle_record.get("m376_order_nonterminal") is True
        ),
        "open_order_count": open_order_count,
        "open_order_present": open_order_present,
        "open_spy_order_present": open_spy_order_present,
        "spy_position_qty": _text(cycle_record.get("spy_position_qty")),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "forbidden_actions": _forbidden_actions(cycle_record),
        "next_forbidden_action": _forbidden_actions(cycle_record),
    }


def render_etf_sma_cycle_operator_brief_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_cycle_operator_brief_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing brief summary."""

    return "\n".join(
        (
            "ETF/SMA cycle operator brief",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"operator_brief_status: {payload.get('operator_brief_status', '')}",
            f"cycle_record_found: {_bool_text(payload.get('cycle_record_found'))}",
            f"cycle_record_parsed: {_bool_text(payload.get('cycle_record_parsed'))}",
            f"cycle_run_id: {payload.get('cycle_run_id', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"cycle_decision_reason: {payload.get('cycle_decision_reason', '')}",
            f"m376_status: {payload.get('m376_status', '')}",
            f"m376_terminal_state: {payload.get('m376_terminal_state', '')}",
            f"open_order_count: {payload.get('open_order_count', '')}",
            f"open_order_present: {_bool_text(payload.get('open_order_present'))}",
            "open_spy_order_present: "
            f"{_bool_text(payload.get('open_spy_order_present'))}",
            f"spy_position_qty: {payload.get('spy_position_qty', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            f"recommended_next_action: {payload.get('recommended_next_action', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_actions_performed: "
            f"{_bool_text(payload.get('broker_actions_performed'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_etf_sma_cycle_operator_brief_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaCycleOperatorBriefWriteResult:
    """Write exactly one JSONL brief record, replacing any prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_cycle_operator_brief_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaCycleOperatorBriefWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _read_jsonl_artifact(path: Path) -> _ArtifactRead:
    if not path.exists():
        return _ArtifactRead(
            path=path,
            found=False,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="path_not_found",
        )
    if not path.is_file():
        return _ArtifactRead(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="path_not_file",
        )

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return _ArtifactRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"invalid_jsonl_line_{line_number}",
            )
        if not isinstance(payload, Mapping):
            return _ArtifactRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"jsonl_record_{line_number}_not_object",
            )
        records.append(dict(payload))

    if not records:
        return _ArtifactRead(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="empty_jsonl",
        )

    return _ArtifactRead(
        path=path,
        found=True,
        parsed=True,
        record_count=len(records),
        latest_record=records[-1],
        error="",
    )


def _operator_blockers(
    cycle_artifact: _ArtifactRead,
    cycle_record: Mapping[str, object],
    cycle_record_type: str,
    m376_terminal: bool,
    m376_terminal_state: str,
    open_order_count: int | None,
    open_order_present: bool,
    open_spy_order_present: bool,
) -> list[str]:
    blockers: list[str] = []
    if not cycle_artifact.parsed:
        blockers.append(_SOURCE_ARTIFACT_BLOCKER)
    if cycle_artifact.parsed and cycle_record_type != _SOURCE_RECORD_TYPE:
        blockers.append(_UNEXPECTED_RECORD_TYPE_BLOCKER)
    blockers.extend(_string_list(cycle_record.get("blockers")))
    if cycle_artifact.parsed and not m376_terminal:
        blockers.append("m376_not_terminal")
    if m376_terminal_state == "nonterminal" or cycle_record.get("m376_nonterminal") is True:
        blockers.append("m376_order_nonterminal")
    if open_order_present or (open_order_count is not None and open_order_count > 0):
        blockers.append("open_order_present")
    if open_spy_order_present:
        blockers.append("open_spy_order_present")
    if not _source_safety_flags_preserved(cycle_record):
        blockers.append(_SOURCE_SAFETY_BLOCKER)
    return list(_dedupe(tuple(blockers)))


def _recommended_next_action(
    blockers: list[str],
    cycle_next_allowed_action: str,
) -> str:
    if any(
        blocker in blockers
        for blocker in (
            "m376_not_terminal",
            "m376_order_nonterminal",
            "open_order_present",
            "open_spy_order_present",
        )
    ):
        return "offline_work_or_read_only_reconciliation"
    if blockers:
        return "rebuild_or_validate_cycle_artifact_before_operator_review"
    if _safe_action(cycle_next_allowed_action):
        return cycle_next_allowed_action
    return "offline_research_or_operator_review_only"


def _safe_action(value: str) -> bool:
    normalized = value.lower()
    if not normalized:
        return False
    return not any(term in normalized for term in _FORBIDDEN_RECOMMENDATION_TERMS)


def _operator_summary(
    operator_brief_status: str,
    state_summary: Mapping[str, object],
) -> str:
    if operator_brief_status == "blocked":
        blockers = _joined(_string_list(state_summary.get("blockers")))
        return f"blocked checkpoint; no broker action allowed; blockers={blockers}"
    return (
        "review-only checkpoint; M376 terminal state and open-order state "
        "permit offline research or operator review only"
    )


def _forbidden_actions(cycle_record: Mapping[str, object]) -> list[str]:
    actions = [
        "broker_mutation_from_etf_sma_cycle_operator_brief",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_operator_brief",
        "delete_from_operator_brief",
        "retry_from_operator_brief",
        *_string_list(cycle_record.get("forbidden_actions")),
        *_string_list(cycle_record.get("next_forbidden_action")),
    ]
    return list(_dedupe(tuple(actions)))


def _source_safety_flags_preserved(cycle_record: Mapping[str, object]) -> bool:
    for field_name in _SOURCE_FALSE_FIELDS:
        if field_name in cycle_record and cycle_record[field_name] is not False:
            return False
    return True


def _config(value: object) -> EtfSmaCycleOperatorBriefConfig:
    if type(value) is not EtfSmaCycleOperatorBriefConfig:
        raise ValidationError("config must be an EtfSmaCycleOperatorBriefConfig.")
    return value


def _generated_at_text(value: object) -> str:
    if value is None:
        raise ValidationError("generated_at is required.")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("generated_at must be timezone-aware.")
        return value.isoformat()
    if type(value) is str:
        text = _required_string(value, "generated_at")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("generated_at must be ISO-8601.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError("generated_at must be timezone-aware.")
        return parsed.isoformat()
    raise ValidationError("generated_at must be a datetime or ISO string.")


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


def _output_path(value: object) -> Path:
    path = _required_path(value, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _first_int(value: object) -> int | None:
    if type(value) is int:
        return value
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
