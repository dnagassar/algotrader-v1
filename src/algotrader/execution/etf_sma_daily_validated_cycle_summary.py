"""Offline daily wrapper for accepted ETF/SMA cycle validation artifacts.

This module reads one explicit local M442 validation JSONL record and writes
one daily operating summary. It does not import runtime config, broker SDKs,
credentials, sockets, or broker mutation behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaDailyValidatedCycleSummaryConfig",
    "EtfSmaDailyValidatedCycleSummaryWriteResult",
    "build_etf_sma_daily_validated_cycle_summary",
    "render_etf_sma_daily_validated_cycle_summary_json",
    "render_etf_sma_daily_validated_cycle_summary_text",
    "write_etf_sma_daily_validated_cycle_summary_jsonl",
]


_MILESTONE = "M443 - Offline daily validated cycle wrapper"
_RECORD_TYPE = "etf_sma_daily_validated_cycle_summary"
_COMMAND = "etf-sma-daily-validated-cycle-summary"
_ACCEPTED_DAILY_WRAPPER_STATE = "accepted_observe_hold_noop"
_BLOCKED_DAILY_WRAPPER_STATE = "blocked_daily_validated_cycle_summary"
_ACCEPTED_VALIDATION_STATE = "accepted_current_cycle_hold_noop"
_EXPECTED_CYCLE_DECISION = "hold/noop"
_EXPECTED_OPERATOR_ACTION = "observe_hold_noop"
_PROFIT_CLAIM = "none"
_SOURCE_FALSE_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "live_authorized",
    "network_access_attempted",
    "credential_access_attempted",
)
_OPTIONAL_SOURCE_FALSE_FIELDS = (
    "broker_access_attempted",
    "broker_mutation_authorized",
    "broker_mutation_allowed",
)
_OUTPUT_FALSE_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaDailyValidatedCycleSummaryConfig:
    """Explicit local inputs for one deterministic daily validation wrapper."""

    run_id: str
    validation_jsonl_path: Path | str
    validated_at: datetime | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "validation_jsonl_path",
            _required_path(self.validation_jsonl_path, "validation_jsonl_path"),
        )
        object.__setattr__(
            self,
            "validated_at",
            _required_timestamp_text(self.validated_at, "validated_at"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaDailyValidatedCycleSummaryWriteResult:
    """Local JSONL write metadata for a single daily wrapper record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    paper_action_authorized: bool
    submit_authorized: bool
    paper_submit_authorized: bool
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
        for field_name in _OUTPUT_FALSE_FIELDS:
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
            "paper_action_authorized": self.paper_action_authorized,
            "submit_authorized": self.submit_authorized,
            "paper_submit_authorized": self.paper_submit_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _ValidationRead:
    path: Path
    found: bool
    parsed: bool
    record_count: int
    record: dict[str, object] | None
    error: str
    sha256: str


def build_etf_sma_daily_validated_cycle_summary(
    config: EtfSmaDailyValidatedCycleSummaryConfig,
) -> dict[str, object]:
    """Build one accepted-only daily wrapper summary from a local M442 record."""

    checked_config = _config(config)
    validation_read = _read_validation_jsonl(checked_config.validation_jsonl_path)
    source_record = validation_read.record or {}
    validation_blockers = _source_validation_blockers_value(
        source_record.get("validation_blockers")
    )
    wrapper_blockers = _daily_wrapper_blockers(
        validation_read=validation_read,
        source_record=source_record,
        validation_blockers=validation_blockers,
    )
    daily_wrapper_state = (
        _ACCEPTED_DAILY_WRAPPER_STATE
        if not wrapper_blockers
        else _BLOCKED_DAILY_WRAPPER_STATE
    )

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "source_validation_path": str(validation_read.path),
        "source_validation_sha256": validation_read.sha256,
        "source_validation_found": validation_read.found,
        "source_validation_parsed": validation_read.parsed,
        "source_validation_record_count": validation_read.record_count,
        "source_validation_error": validation_read.error,
        "validated_at": checked_config.validated_at,
        "daily_wrapper_state": daily_wrapper_state,
        "daily_wrapper_blockers": wrapper_blockers,
        "validation_state": _text(source_record.get("validation_state")),
        "validation_blockers": list(validation_blockers or ()),
        "symbol": _json_scalar(source_record.get("symbol", "")),
        "sma50": _json_scalar(source_record.get("sma50", "")),
        "sma200": _json_scalar(source_record.get("sma200", "")),
        "posture": _json_scalar(source_record.get("posture", "")),
        "cycle_decision": _text(source_record.get("cycle_decision")),
        "current_spy_position_qty": _json_scalar(
            source_record.get("current_spy_position_qty", "")
        ),
        "open_order_count": _json_scalar(source_record.get("open_order_count", "")),
        "unexpected_non_spy_position_present": _bool_or_none(
            source_record.get("unexpected_non_spy_position_present")
        ),
        "source_as_of": _text(source_record.get("source_as_of")),
        "recommended_operator_action": _text(
            source_record.get("recommended_operator_action")
        ),
        "paper_action_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": _PROFIT_CLAIM,
    }


def render_etf_sma_daily_validated_cycle_summary_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_daily_validated_cycle_summary_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing daily wrapper summary."""

    blockers = _string_list(payload.get("daily_wrapper_blockers"))
    blocker_text = ", ".join(blockers) if blockers else "none"
    return "\n".join(
        (
            "ETF/SMA daily validated cycle summary",
            f"run_id: {payload.get('run_id', '')}",
            f"source_validation_path: {payload.get('source_validation_path', '')}",
            f"source_validation_record_count: "
            f"{payload.get('source_validation_record_count', '')}",
            f"validated_at: {payload.get('validated_at', '')}",
            f"source_as_of: {payload.get('source_as_of', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"posture: {payload.get('posture', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"validation_state: {payload.get('validation_state', '')}",
            f"daily_wrapper_state: {payload.get('daily_wrapper_state', '')}",
            f"daily_wrapper_blockers: {blocker_text}",
            "recommended_operator_action: "
            f"{payload.get('recommended_operator_action', '')}",
            "paper_action_authorized: "
            f"{_bool_text(payload.get('paper_action_authorized'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"profit_claim: {payload.get('profit_claim', '')}",
        )
    )


def write_etf_sma_daily_validated_cycle_summary_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaDailyValidatedCycleSummaryWriteResult:
    """Write exactly one JSONL daily wrapper record, replacing prior contents."""

    checked_payload = dict(payload)
    _validate_output_safety_fields(checked_payload)
    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_daily_validated_cycle_summary_json(checked_payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaDailyValidatedCycleSummaryWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        paper_action_authorized=False,
        submit_authorized=False,
        paper_submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _daily_wrapper_blockers(
    *,
    validation_read: _ValidationRead,
    source_record: Mapping[str, object],
    validation_blockers: tuple[str, ...] | None,
) -> list[str]:
    source_blockers = _source_validation_read_blockers(validation_read)
    if source_blockers:
        return source_blockers

    blockers: list[str] = []
    if _text(source_record.get("validation_state")) != _ACCEPTED_VALIDATION_STATE:
        blockers.append("validation_state_not_accepted_current_cycle_hold_noop")

    if validation_blockers is None:
        blockers.append("validation_blockers_missing_or_invalid")
    elif validation_blockers:
        blockers.append("validation_blockers_present")

    for field_name in _SOURCE_FALSE_FIELDS:
        if source_record.get(field_name) is not False:
            blockers.append(f"{field_name}_not_false")
    for field_name in _OPTIONAL_SOURCE_FALSE_FIELDS:
        if source_record.get(field_name) is True:
            blockers.append(f"{field_name}_not_false")

    if _text(source_record.get("cycle_decision")) != _EXPECTED_CYCLE_DECISION:
        blockers.append("cycle_decision_not_hold_noop")
    if _text(source_record.get("recommended_operator_action")) != (
        _EXPECTED_OPERATOR_ACTION
    ):
        blockers.append("recommended_operator_action_not_observe_hold_noop")
    if _text(source_record.get("profit_claim")) != _PROFIT_CLAIM:
        blockers.append("profit_claim_not_none")

    return blockers


def _source_validation_read_blockers(validation_read: _ValidationRead) -> list[str]:
    if not validation_read.found:
        return ["source_validation_missing"]
    if not validation_read.parsed:
        return ["source_validation_invalid_jsonl"]
    if validation_read.record_count == 0:
        return ["source_validation_zero_records"]
    if validation_read.record_count > 1:
        return ["source_validation_multiple_records"]
    if validation_read.record is None:
        return ["source_validation_missing_record"]
    return []


def _read_validation_jsonl(path: Path) -> _ValidationRead:
    if not path.exists():
        return _ValidationRead(
            path=path,
            found=False,
            parsed=False,
            record_count=0,
            record=None,
            error="path_not_found",
            sha256="",
        )
    if not path.is_file():
        return _ValidationRead(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            record=None,
            error="path_not_file",
            sha256="",
        )

    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _ValidationRead(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            record=None,
            error="utf8_decode_error",
            sha256=sha256,
        )

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return _ValidationRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                record=None,
                error=f"invalid_jsonl_line_{line_number}",
                sha256=sha256,
            )
        if not isinstance(payload, Mapping):
            return _ValidationRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                record=None,
                error=f"non_object_jsonl_line_{line_number}",
                sha256=sha256,
            )
        records.append(dict(payload))

    if len(records) != 1:
        return _ValidationRead(
            path=path,
            found=True,
            parsed=True,
            record_count=len(records),
            record=None,
            error="record_count_not_one",
            sha256=sha256,
        )
    return _ValidationRead(
        path=path,
        found=True,
        parsed=True,
        record_count=1,
        record=records[0],
        error="",
        sha256=sha256,
    )


def _config(
    config: EtfSmaDailyValidatedCycleSummaryConfig,
) -> EtfSmaDailyValidatedCycleSummaryConfig:
    if not isinstance(config, EtfSmaDailyValidatedCycleSummaryConfig):
        raise ValidationError(
            "config must be an EtfSmaDailyValidatedCycleSummaryConfig."
        )
    return config


def _validate_output_safety_fields(payload: Mapping[str, object]) -> None:
    for field_name in _OUTPUT_FALSE_FIELDS:
        _false_bool(payload.get(field_name), field_name)
    if _text(payload.get("profit_claim")) != _PROFIT_CLAIM:
        raise ValidationError("profit_claim must be none.")


def _required_string(value: object, field_name: str) -> str:
    text = _text(value)
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        path = Path(str(value))
    if not str(path):
        raise ValidationError(f"{field_name} is required.")
    return path


def _output_path(value: Path | str) -> Path:
    path = value if isinstance(value, Path) else Path(str(value))
    if not str(path):
        raise ValidationError("output_path is required.")
    return path


def _required_timestamp_text(value: datetime | str, field_name: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(f"{field_name} must be timezone-aware.")
        return value.isoformat()
    text = _text(value)
    if not text:
        raise ValidationError(f"{field_name} is required.")
    if _parse_timestamp(text) is None:
        raise ValidationError(f"{field_name} must be a timezone-aware ISO-8601 value.")
    return text


def _parse_timestamp(value: object) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _source_validation_blockers_value(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    return tuple(_text(item) for item in value if _text(item))


def _json_scalar(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _bool_or_none(value: object) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_json_safe(item) for item in value]
    return value
