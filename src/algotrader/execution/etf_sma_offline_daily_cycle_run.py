"""Offline daily runner for the ETF/SMA cycle packet chain.

This module composes M441, M442, and M443 in memory, then emits one M444
manifest over the local child JSONL artifacts. It never imports runtime config,
broker SDKs, credentials, sockets, or broker mutation behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

from .etf_sma_cycle_packet_validator import (
    EtfSmaCyclePacketValidationConfig,
    build_etf_sma_cycle_packet_validation,
    write_etf_sma_cycle_packet_validation_jsonl,
)
from .etf_sma_cycle_unified_preview import (
    EtfSmaCycleUnifiedPreviewConfig,
    build_etf_sma_cycle_unified_preview,
    write_etf_sma_cycle_unified_preview_jsonl,
)
from .etf_sma_daily_validated_cycle_summary import (
    EtfSmaDailyValidatedCycleSummaryConfig,
    build_etf_sma_daily_validated_cycle_summary,
    write_etf_sma_daily_validated_cycle_summary_jsonl,
)

__all__ = [
    "EtfSmaOfflineDailyCycleRunConfig",
    "EtfSmaOfflineDailyCycleRunWriteResult",
    "build_etf_sma_offline_daily_cycle_run_manifest",
    "render_etf_sma_offline_daily_cycle_run_json",
    "render_etf_sma_offline_daily_cycle_run_text",
    "run_etf_sma_offline_daily_cycle_run",
    "write_etf_sma_offline_daily_cycle_run_jsonl",
]


_MILESTONE = "M444 - Offline daily cycle chain runner"
_RECORD_TYPE = "etf_sma_offline_daily_cycle_run_manifest"
_COMMAND = "etf-sma-offline-daily-cycle-run"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_RUN_ID = "m444_offline_daily_cycle_run"
_DEFAULT_ORDER_RECONCILIATION_LOG = (
    "runs/paper_lab/m439_m436_spy_buy_fresh_read_only_reconciliation.jsonl"
)
_READINESS_RUN_ID = "m441_unified_etf_sma_cycle_readiness_packet"
_VALIDATION_RUN_ID = "m442_unified_cycle_packet_validation"
_SUMMARY_RUN_ID = "m443_daily_validated_cycle_summary"
_MAX_AGE_HOURS = "24"
_ACCEPTED_DAILY_CHAIN_STATE = "accepted_observe_hold_noop"
_BLOCKED_DAILY_CHAIN_STATE = "blocked_offline_daily_cycle_run"
_EXPECTED_CYCLE_DECISION = "hold/noop"
_EXPECTED_VALIDATION_STATE = "accepted_current_cycle_hold_noop"
_EXPECTED_DAILY_WRAPPER_STATE = "accepted_observe_hold_noop"
_EXPECTED_OPERATOR_ACTION = "observe_hold_noop"
_PROFIT_CLAIM = "none"
_FALSE_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_OPTIONAL_FALSE_FIELDS = (
    "broker_actions_performed",
    "broker_access_attempted",
    "broker_mutation_authorized",
    "broker_mutation_allowed",
)
_OUTPUT_FALSE_FIELDS = (
    *_FALSE_FIELDS,
    "broker_actions_performed",
)


@dataclass(frozen=True, slots=True)
class EtfSmaOfflineDailyCycleRunConfig:
    """Explicit local inputs for one deterministic M444 chain run."""

    run_id: str = _DEFAULT_RUN_ID
    validated_at: datetime | str = ""
    daily_bars_csv: Path | str = ""
    readiness_output_jsonl: Path | str = ""
    validation_output_jsonl: Path | str = ""
    summary_output_jsonl: Path | str = ""
    manifest_output_jsonl: Path | str = ""
    order_reconciliation_log: Path | str = _DEFAULT_ORDER_RECONCILIATION_LOG
    symbol: str = _DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "validated_at",
            _required_timestamp_text(self.validated_at, "validated_at"),
        )
        object.__setattr__(
            self,
            "daily_bars_csv",
            _required_path(self.daily_bars_csv, "daily_bars_csv"),
        )
        object.__setattr__(
            self,
            "readiness_output_jsonl",
            _required_path(
                self.readiness_output_jsonl,
                "readiness_output_jsonl",
            ),
        )
        object.__setattr__(
            self,
            "validation_output_jsonl",
            _required_path(
                self.validation_output_jsonl,
                "validation_output_jsonl",
            ),
        )
        object.__setattr__(
            self,
            "summary_output_jsonl",
            _required_path(self.summary_output_jsonl, "summary_output_jsonl"),
        )
        object.__setattr__(
            self,
            "manifest_output_jsonl",
            _required_path(self.manifest_output_jsonl, "manifest_output_jsonl"),
        )
        object.__setattr__(
            self,
            "order_reconciliation_log",
            _required_path(
                self.order_reconciliation_log,
                "order_reconciliation_log",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            _required_string(self.symbol, "symbol").upper(),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaOfflineDailyCycleRunWriteResult:
    """Local JSONL write metadata for a single M444 manifest record."""

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
class _ArtifactRead:
    path: Path
    found: bool
    parsed: bool
    record_count: int
    record: dict[str, object] | None
    error: str
    sha256: str


def run_etf_sma_offline_daily_cycle_run(
    config: EtfSmaOfflineDailyCycleRunConfig,
) -> dict[str, object]:
    """Run the local M441 -> M442 -> M443 chain and write one M444 manifest."""

    checked_config = _config(config)
    runner_blockers: list[str] = []

    try:
        readiness_payload = build_etf_sma_cycle_unified_preview(
            EtfSmaCycleUnifiedPreviewConfig(
                run_id=_READINESS_RUN_ID,
                symbol=checked_config.symbol,
                generated_at=checked_config.validated_at,
                order_reconciliation_log=checked_config.order_reconciliation_log,
                daily_bars_csv=checked_config.daily_bars_csv,
            )
        )
        write_etf_sma_cycle_unified_preview_jsonl(
            readiness_payload,
            checked_config.readiness_output_jsonl,
        )
    except ValidationError as exc:
        runner_blockers.append(f"readiness_step_failed:{_clean_error(exc)}")

    try:
        validation_payload = build_etf_sma_cycle_packet_validation(
            EtfSmaCyclePacketValidationConfig(
                run_id=_VALIDATION_RUN_ID,
                source_packet_path=checked_config.readiness_output_jsonl,
                validated_at=checked_config.validated_at,
                max_age_hours=_MAX_AGE_HOURS,
            )
        )
        write_etf_sma_cycle_packet_validation_jsonl(
            validation_payload,
            checked_config.validation_output_jsonl,
        )
    except ValidationError as exc:
        runner_blockers.append(f"validation_step_failed:{_clean_error(exc)}")

    try:
        summary_payload = build_etf_sma_daily_validated_cycle_summary(
            EtfSmaDailyValidatedCycleSummaryConfig(
                run_id=_SUMMARY_RUN_ID,
                validation_jsonl_path=checked_config.validation_output_jsonl,
                validated_at=checked_config.validated_at,
            )
        )
        write_etf_sma_daily_validated_cycle_summary_jsonl(
            summary_payload,
            checked_config.summary_output_jsonl,
        )
    except ValidationError as exc:
        runner_blockers.append(f"summary_step_failed:{_clean_error(exc)}")

    manifest = build_etf_sma_offline_daily_cycle_run_manifest(
        checked_config,
        runner_blockers=runner_blockers,
    )
    write_etf_sma_offline_daily_cycle_run_jsonl(
        manifest,
        checked_config.manifest_output_jsonl,
    )
    return manifest


def build_etf_sma_offline_daily_cycle_run_manifest(
    config: EtfSmaOfflineDailyCycleRunConfig,
    *,
    runner_blockers: Iterable[str] = (),
) -> dict[str, object]:
    """Build one fail-closed manifest from local M441, M442, and M443 artifacts."""

    checked_config = _config(config)
    readiness = _read_jsonl_artifact(checked_config.readiness_output_jsonl)
    validation = _read_jsonl_artifact(checked_config.validation_output_jsonl)
    summary = _read_jsonl_artifact(checked_config.summary_output_jsonl)
    readiness_record = readiness.record or {}
    validation_record = validation.record or {}
    summary_record = summary.record or {}

    chain_blockers = _manifest_blockers(
        runner_blockers=tuple(_string_list(tuple(runner_blockers))),
        readiness=readiness,
        validation=validation,
        summary=summary,
    )

    readiness_cycle_decision = _text(readiness_record.get("cycle_decision"))
    validation_cycle_decision = _text(validation_record.get("cycle_decision"))
    summary_cycle_decision = _text(summary_record.get("cycle_decision"))
    validation_state = _text(validation_record.get("validation_state"))
    daily_wrapper_state = _text(summary_record.get("daily_wrapper_state"))
    recommended_operator_action = _first_text(
        summary_record.get("recommended_operator_action"),
        validation_record.get("recommended_operator_action"),
    )
    daily_chain_state = (
        _ACCEPTED_DAILY_CHAIN_STATE
        if not chain_blockers
        else _BLOCKED_DAILY_CHAIN_STATE
    )

    return {
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": checked_config.run_id,
        "validated_at": checked_config.validated_at,
        "daily_chain_state": daily_chain_state,
        "readiness_output_path": str(readiness.path),
        "readiness_output_sha256": readiness.sha256,
        "readiness_record_count": readiness.record_count,
        "validation_output_path": str(validation.path),
        "validation_output_sha256": validation.sha256,
        "validation_record_count": validation.record_count,
        "summary_output_path": str(summary.path),
        "summary_output_sha256": summary.sha256,
        "summary_record_count": summary.record_count,
        "symbol": _first_text(
            summary_record.get("symbol"),
            validation_record.get("symbol"),
            readiness_record.get("symbol"),
        ),
        "usable_spy_bars": _first_scalar(
            summary_record.get("usable_spy_bars"),
            validation_record.get("usable_spy_bars"),
            readiness_record.get("usable_spy_bars"),
        ),
        "sma50": _first_scalar(
            summary_record.get("sma50"),
            validation_record.get("sma50"),
            readiness_record.get("sma50"),
        ),
        "sma200": _first_scalar(
            summary_record.get("sma200"),
            validation_record.get("sma200"),
            readiness_record.get("sma200"),
        ),
        "posture": _first_scalar(
            summary_record.get("posture"),
            validation_record.get("posture"),
            readiness_record.get("posture"),
        ),
        "readiness_cycle_decision": readiness_cycle_decision,
        "validation_cycle_decision": validation_cycle_decision,
        "summary_cycle_decision": summary_cycle_decision,
        "validation_state": validation_state,
        "daily_wrapper_state": daily_wrapper_state,
        "recommended_operator_action": recommended_operator_action,
        "paper_action_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "live_authorized": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "profit_claim": _PROFIT_CLAIM,
        "chain_blockers": chain_blockers,
    }


def render_etf_sma_offline_daily_cycle_run_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_offline_daily_cycle_run_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing M444 manifest summary."""

    blockers = _string_list(payload.get("chain_blockers"))
    blocker_text = ", ".join(blockers) if blockers else "none"
    return "\n".join(
        (
            "ETF/SMA offline daily cycle run",
            f"run_id: {payload.get('run_id', '')}",
            f"validated_at: {payload.get('validated_at', '')}",
            f"daily_chain_state: {payload.get('daily_chain_state', '')}",
            f"readiness_output_path: {payload.get('readiness_output_path', '')}",
            f"validation_output_path: {payload.get('validation_output_path', '')}",
            f"summary_output_path: {payload.get('summary_output_path', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"usable_spy_bars: {payload.get('usable_spy_bars', '')}",
            f"posture: {payload.get('posture', '')}",
            "readiness_cycle_decision: "
            f"{payload.get('readiness_cycle_decision', '')}",
            f"validation_state: {payload.get('validation_state', '')}",
            f"daily_wrapper_state: {payload.get('daily_wrapper_state', '')}",
            "recommended_operator_action: "
            f"{payload.get('recommended_operator_action', '')}",
            f"paper_action_authorized: {_bool_text(payload.get('paper_action_authorized'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"chain_blockers: {blocker_text}",
        )
    )


def write_etf_sma_offline_daily_cycle_run_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaOfflineDailyCycleRunWriteResult:
    """Write exactly one M444 manifest JSONL record, replacing prior contents."""

    checked_payload = dict(payload)
    _validate_output_safety_fields(checked_payload)
    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_offline_daily_cycle_run_json(checked_payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaOfflineDailyCycleRunWriteResult(
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


def _manifest_blockers(
    *,
    runner_blockers: tuple[str, ...],
    readiness: _ArtifactRead,
    validation: _ArtifactRead,
    summary: _ArtifactRead,
) -> list[str]:
    blockers: list[str] = list(runner_blockers)
    blockers.extend(_artifact_blockers("readiness", readiness))
    blockers.extend(_artifact_blockers("validation", validation))
    blockers.extend(_artifact_blockers("summary", summary))

    records = (
        ("readiness", readiness.record or {}),
        ("validation", validation.record or {}),
        ("summary", summary.record or {}),
    )
    for label, record in records:
        if not record:
            continue
        blockers.extend(_child_blockers(label, record))
        blockers.extend(_unsafe_flag_blockers(label, record))
        if _text(record.get("profit_claim")) not in ("", _PROFIT_CLAIM):
            blockers.append(f"{label}_profit_claim_not_none")

    readiness_cycle_decision = _text((readiness.record or {}).get("cycle_decision"))
    validation_cycle_decision = _text((validation.record or {}).get("cycle_decision"))
    summary_cycle_decision = _text((summary.record or {}).get("cycle_decision"))
    if readiness.record and validation.record:
        if readiness_cycle_decision != validation_cycle_decision:
            blockers.append("readiness_validation_cycle_decision_mismatch")
    if validation.record and summary.record:
        if validation_cycle_decision != summary_cycle_decision:
            blockers.append("validation_summary_cycle_decision_mismatch")
    if readiness.record and readiness_cycle_decision != _EXPECTED_CYCLE_DECISION:
        blockers.append("readiness_cycle_decision_not_hold_noop")

    validation_state = _text((validation.record or {}).get("validation_state"))
    if validation.record and validation_state != _EXPECTED_VALIDATION_STATE:
        blockers.append("validation_state_not_accepted_current_cycle_hold_noop")

    daily_wrapper_state = _text((summary.record or {}).get("daily_wrapper_state"))
    if summary.record and daily_wrapper_state != _EXPECTED_DAILY_WRAPPER_STATE:
        blockers.append("daily_wrapper_state_not_accepted_observe_hold_noop")

    recommended_operator_action = _first_text(
        (summary.record or {}).get("recommended_operator_action"),
        (validation.record or {}).get("recommended_operator_action"),
    )
    if summary.record and recommended_operator_action != _EXPECTED_OPERATOR_ACTION:
        blockers.append("recommended_operator_action_not_observe_hold_noop")

    return list(_dedupe(tuple(blockers)))


def _artifact_blockers(label: str, artifact: _ArtifactRead) -> list[str]:
    if not artifact.found:
        return [f"{label}_output_missing"]
    if not artifact.parsed:
        return [f"{label}_output_invalid_jsonl"]
    if artifact.record_count == 0:
        return [f"{label}_output_zero_records"]
    if artifact.record_count > 1:
        return [f"{label}_output_multiple_records"]
    if artifact.record is None:
        return [f"{label}_output_missing_record"]
    return []


def _child_blockers(label: str, record: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    for field_name in (
        "blockers",
        "validation_blockers",
        "daily_wrapper_blockers",
        "chain_blockers",
    ):
        values = _string_list(record.get(field_name))
        if values:
            blockers.append(f"{label}_{field_name}_present")
    return blockers


def _unsafe_flag_blockers(label: str, record: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    for field_name in (*_FALSE_FIELDS, *_OPTIONAL_FALSE_FIELDS):
        if record.get(field_name) is True:
            blockers.append(f"{label}_{field_name}_true")
    return blockers


def _read_jsonl_artifact(path: Path) -> _ArtifactRead:
    if not path.exists():
        return _ArtifactRead(
            path=path,
            found=False,
            parsed=False,
            record_count=0,
            record=None,
            error="path_not_found",
            sha256="",
        )
    if not path.is_file():
        return _ArtifactRead(
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
        return _ArtifactRead(
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
            return _ArtifactRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                record=None,
                error=f"invalid_jsonl_line_{line_number}",
                sha256=sha256,
            )
        if not isinstance(payload, Mapping):
            return _ArtifactRead(
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
        return _ArtifactRead(
            path=path,
            found=True,
            parsed=True,
            record_count=len(records),
            record=None,
            error="record_count_not_one",
            sha256=sha256,
        )
    return _ArtifactRead(
        path=path,
        found=True,
        parsed=True,
        record_count=1,
        record=records[0],
        error="",
        sha256=sha256,
    )


def _config(
    config: EtfSmaOfflineDailyCycleRunConfig,
) -> EtfSmaOfflineDailyCycleRunConfig:
    if not isinstance(config, EtfSmaOfflineDailyCycleRunConfig):
        raise ValidationError("config must be an EtfSmaOfflineDailyCycleRunConfig.")
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
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
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


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _first_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _first_scalar(*values: object) -> object:
    for value in values:
        if value not in (None, ""):
            return _json_scalar(value)
    return ""


def _json_scalar(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _clean_error(exc: ValidationError) -> str:
    return " ".join(str(exc).split())


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_json_safe(item) for item in value]
    return value
