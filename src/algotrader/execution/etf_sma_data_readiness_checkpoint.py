"""Offline ETF/SMA data-readiness checkpoint builder.

This module reads explicit local JSONL artifacts only. It does not load
profiles, read credentials, import broker SDKs, open sockets, or expose broker
mutation behavior.
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
    "ETF_SMA_DATA_READINESS_CHECKPOINT_LABELS",
    "EtfSmaDataReadinessCheckpointConfig",
    "EtfSmaDataReadinessCheckpointWriteResult",
    "build_etf_sma_data_readiness_checkpoint",
    "render_etf_sma_data_readiness_checkpoint_json",
    "render_etf_sma_data_readiness_checkpoint_text",
    "write_etf_sma_data_readiness_checkpoint_jsonl",
]


ETF_SMA_DATA_READINESS_CHECKPOINT_LABELS = (
    "paper_lab_only",
    "data_readiness_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M396 - Offline ETF/SMA data-readiness checkpoint"
_RECORD_TYPE = "etf_sma_data_readiness_checkpoint"
_COMMAND = "etf-sma-data-readiness"
_DEFAULT_SYMBOL = "SPY"
_PROFIT_CLAIM = "none"
_DEFAULT_REQUIRED_USABLE_BARS = 200
_SOURCE_CYCLE_RECORD_TYPES = ("etf_sma_cycle_unified_preview", "etf_sma_cycle")
_SOURCE_BRIEF_RECORD_TYPE = "etf_sma_cycle_operator_brief"
_SOURCE_ARTIFACT_BLOCKER = "missing_or_invalid_cycle_artifact"
_UNEXPECTED_CYCLE_RECORD_TYPE_BLOCKER = "unexpected_cycle_record_type"
_UNEXPECTED_BRIEF_RECORD_TYPE_BLOCKER = "unexpected_brief_record_type"
_SOURCE_SAFETY_BLOCKER = "source_artifact_safety_flags_not_false"
_MISSING_OBSERVED_BARS_BLOCKER = "missing_observed_usable_bars"
_MISSING_USABLE_BARS_BLOCKER = "missing_usable_bars"
_COUNT_DECISION_CONFLICT_BLOCKER = "cycle_count_decision_conflict"
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
    "preview_order_authorized",
)
_REQUIRED_BAR_CANDIDATES = (
    ("required_usable_bars",),
    ("sma_config", "required_bars"),
    ("sma_config", "slow_window"),
    ("sma", "required_bars"),
    ("sma", "slow_window"),
    ("sma_slow_window",),
    ("slow_window",),
    ("required_bars",),
)
_OBSERVED_BAR_CANDIDATES = (
    ("observed_usable_bars",),
    ("usable_bar_count",),
    ("market_data", "usable_bar_count"),
    ("sma", "usable_bar_count"),
)


@dataclass(frozen=True, slots=True)
class EtfSmaDataReadinessCheckpointConfig:
    """Explicit local inputs for one deterministic data-readiness checkpoint."""

    run_id: str
    cycle_log: Path | str
    generated_at: datetime | str
    symbol: str = _DEFAULT_SYMBOL
    brief_log: Path | str | None = None

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
            "brief_log",
            _optional_path(self.brief_log, "brief_log"),
        )
        object.__setattr__(
            self,
            "generated_at",
            _generated_at_text(self.generated_at),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaDataReadinessCheckpointWriteResult:
    """Local JSONL write metadata for a single checkpoint record."""

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
    path: Path | None
    provided: bool
    found: bool
    parsed: bool
    record_count: int
    latest_record: dict[str, object] | None
    error: str

    def summary(self) -> dict[str, object]:
        latest = self.latest_record or {}
        return {
            "path": "" if self.path is None else str(self.path),
            "provided": self.provided,
            "found": self.found,
            "parsed": self.parsed,
            "record_count": self.record_count,
            "latest_run_id": _text(latest.get("run_id")),
            "latest_record_type": _text(latest.get("record_type")),
            "error": self.error,
        }


def build_etf_sma_data_readiness_checkpoint(
    config: EtfSmaDataReadinessCheckpointConfig,
) -> dict[str, object]:
    """Build one fail-closed data-readiness checkpoint from local artifacts."""

    checked_config = _config(config)
    cycle_artifact = _read_jsonl_artifact(checked_config.cycle_log)
    brief_artifact = _read_jsonl_artifact(checked_config.brief_log)
    cycle_record = cycle_artifact.latest_record or {}
    brief_record = brief_artifact.latest_record or {}
    cycle_record_type = _text(cycle_record.get("record_type"))
    brief_record_type = _text(brief_record.get("record_type"))
    cycle_decision = _first_text(
        cycle_record.get("cycle_decision"),
        cycle_record.get("decision"),
        brief_record.get("cycle_decision"),
    )
    cycle_decision_reason = _first_text(
        cycle_record.get("cycle_decision_reason"),
        cycle_record.get("decision_reason"),
        brief_record.get("cycle_decision_reason"),
    )
    required_usable_bars, required_source = _required_usable_bars(
        cycle_record,
        brief_record,
    )
    observed_usable_bars, observed_source = _observed_usable_bars(
        cycle_record,
        brief_record,
    )
    missing_usable_bars = _missing_usable_bars(
        required_usable_bars,
        observed_usable_bars,
    )
    missing_evidence = _missing_evidence(
        cycle_artifact,
        cycle_record,
        observed_usable_bars,
    )
    data_readiness_state = _data_readiness_state(
        cycle_artifact,
        cycle_record_type,
        cycle_decision,
        cycle_decision_reason,
        required_usable_bars,
        observed_usable_bars,
    )
    blockers = _data_readiness_blockers(
        cycle_artifact,
        brief_artifact,
        cycle_record,
        brief_record,
        cycle_record_type,
        brief_record_type,
        cycle_decision,
        cycle_decision_reason,
        data_readiness_state,
        missing_usable_bars,
        observed_usable_bars,
    )
    recommended_next_action = _recommended_next_action(data_readiness_state, blockers)
    broker_action_flags = _broker_action_flags()
    source_safety_flags_preserved = _source_safety_flags_preserved(
        cycle_record,
        brief_record,
    )

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": checked_config.generated_at,
        "as_of": checked_config.generated_at,
        "symbol": checked_config.symbol,
        "scope": "SPY_paper_lab_only",
        "labels": list(ETF_SMA_DATA_READINESS_CHECKPOINT_LABELS),
        "paper_lab_only": True,
        "data_readiness_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "source_cycle_log": str(checked_config.cycle_log),
        "source_brief_log": "" if checked_config.brief_log is None else str(checked_config.brief_log),
        "source_artifacts": {
            "cycle_log": cycle_artifact.summary(),
            "brief_log": brief_artifact.summary(),
        },
        "source_run_ids": {
            "cycle_run_id": _first_text(
                cycle_record.get("run_id"),
                brief_record.get("cycle_run_id"),
            ),
            "brief_run_id": _text(brief_record.get("run_id")),
        },
        "cycle_record_found": cycle_artifact.found,
        "cycle_record_parsed": cycle_artifact.parsed,
        "cycle_record_type": cycle_record_type,
        "cycle_record_type_expected": list(_SOURCE_CYCLE_RECORD_TYPES),
        "cycle_run_id": _first_text(
            cycle_record.get("run_id"),
            brief_record.get("cycle_run_id"),
        ),
        "cycle_generated_at": _first_text(
            cycle_record.get("generated_at"),
            brief_record.get("cycle_generated_at"),
        ),
        "cycle_decision": cycle_decision,
        "cycle_decision_reason": cycle_decision_reason,
        "brief_record_found": brief_artifact.found,
        "brief_record_parsed": brief_artifact.parsed,
        "brief_record_type": brief_record_type,
        "brief_run_id": _text(brief_record.get("run_id")),
        "data_readiness_state": data_readiness_state,
        "required_usable_bars": required_usable_bars,
        "required_usable_bars_source": required_source,
        "observed_usable_bars": observed_usable_bars,
        "observed_usable_bars_source": observed_source,
        "missing_usable_bars": missing_usable_bars,
        "missing_evidence": missing_evidence,
        "available_evidence": _available_evidence(
            cycle_record,
            brief_record,
            required_usable_bars,
            required_source,
            observed_usable_bars,
            observed_source,
        ),
        "recommended_next_action": recommended_next_action,
        "next_allowed_action": recommended_next_action,
        "next_offline_data_action": _next_offline_data_action(
            data_readiness_state,
            recommended_next_action,
        ),
        "blockers": blockers,
        "source_safety_flags_preserved": source_safety_flags_preserved,
        "safety_summary": {
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
            "source_safety_flags_preserved": source_safety_flags_preserved,
            "broker_action_flags": broker_action_flags,
        },
        "broker_action_flags": broker_action_flags,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "forbidden_actions": _forbidden_actions(),
        "next_forbidden_action": _forbidden_actions(),
    }


def render_etf_sma_data_readiness_checkpoint_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_data_readiness_checkpoint_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing data-readiness summary."""

    return "\n".join(
        (
            "ETF/SMA data-readiness checkpoint",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"cycle_record_found: {_bool_text(payload.get('cycle_record_found'))}",
            f"cycle_record_parsed: {_bool_text(payload.get('cycle_record_parsed'))}",
            f"cycle_run_id: {payload.get('cycle_run_id', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"cycle_decision_reason: {payload.get('cycle_decision_reason', '')}",
            f"data_readiness_state: {payload.get('data_readiness_state', '')}",
            f"required_usable_bars: {payload.get('required_usable_bars', '')}",
            f"observed_usable_bars: {_none_text(payload.get('observed_usable_bars'))}",
            f"missing_usable_bars: {_none_text(payload.get('missing_usable_bars'))}",
            f"missing_evidence: {_joined(_string_list(payload.get('missing_evidence')))}",
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


def write_etf_sma_data_readiness_checkpoint_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaDataReadinessCheckpointWriteResult:
    """Write exactly one JSONL checkpoint record, replacing prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_data_readiness_checkpoint_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaDataReadinessCheckpointWriteResult(
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


def _read_jsonl_artifact(path: Path | None) -> _ArtifactRead:
    if path is None:
        return _ArtifactRead(
            path=None,
            provided=False,
            found=False,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="not_provided",
        )
    if not path.exists():
        return _ArtifactRead(
            path=path,
            provided=True,
            found=False,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="path_not_found",
        )
    if not path.is_file():
        return _ArtifactRead(
            path=path,
            provided=True,
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
                provided=True,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"invalid_jsonl_line_{line_number}",
            )
        if not isinstance(payload, Mapping):
            return _ArtifactRead(
                path=path,
                provided=True,
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
            provided=True,
            found=True,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="empty_jsonl",
        )

    return _ArtifactRead(
        path=path,
        provided=True,
        found=True,
        parsed=True,
        record_count=len(records),
        latest_record=records[-1],
        error="",
    )


def _required_usable_bars(
    cycle_record: Mapping[str, object],
    brief_record: Mapping[str, object],
) -> tuple[int, str]:
    value, source = _first_int_from_paths(
        (
            ("cycle_artifact", cycle_record),
            ("brief_artifact", brief_record),
        ),
        _REQUIRED_BAR_CANDIDATES,
    )
    if value is not None:
        return value, source
    return _DEFAULT_REQUIRED_USABLE_BARS, "configured_sma200_default"


def _observed_usable_bars(
    cycle_record: Mapping[str, object],
    brief_record: Mapping[str, object],
) -> tuple[int | None, str]:
    value, source = _first_int_from_paths(
        (
            ("cycle_artifact", cycle_record),
            ("brief_artifact", brief_record),
        ),
        _OBSERVED_BAR_CANDIDATES,
    )
    if value is None:
        return None, ""
    return value, source


def _first_int_from_paths(
    records: tuple[tuple[str, Mapping[str, object]], ...],
    paths: tuple[tuple[str, ...], ...],
) -> tuple[int | None, str]:
    for record_name, record in records:
        for path in paths:
            value = _nested_value(record, path)
            integer = _optional_int(value)
            if integer is not None:
                return integer, f"{record_name}.{'.'.join(path)}"
    return None, ""


def _nested_value(record: Mapping[str, object], path: tuple[str, ...]) -> object:
    value: object = record
    for part in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _missing_usable_bars(
    required_usable_bars: int,
    observed_usable_bars: int | None,
) -> int | None:
    if observed_usable_bars is None:
        return None
    return max(required_usable_bars - observed_usable_bars, 0)


def _missing_evidence(
    cycle_artifact: _ArtifactRead,
    cycle_record: Mapping[str, object],
    observed_usable_bars: int | None,
) -> list[str]:
    missing: list[str] = []
    if not cycle_artifact.parsed:
        missing.append("cycle_artifact_json_object")
    if cycle_artifact.parsed and observed_usable_bars is None:
        missing.extend(
            (
                "cycle_artifact.observed_usable_bars",
                "cycle_artifact.market_data.usable_bar_count",
                "cycle_artifact.sma.usable_bar_count",
            )
        )
    if cycle_artifact.parsed and not _has_any_key(cycle_record, ("cycle_decision", "decision")):
        missing.append("cycle_artifact.cycle_decision")
    return list(_dedupe(tuple(missing)))


def _data_readiness_state(
    cycle_artifact: _ArtifactRead,
    cycle_record_type: str,
    cycle_decision: str,
    cycle_decision_reason: str,
    required_usable_bars: int,
    observed_usable_bars: int | None,
) -> str:
    if not cycle_artifact.parsed:
        return "blocked_missing_or_invalid_cycle_artifact"
    if cycle_record_type not in _SOURCE_CYCLE_RECORD_TYPES:
        return "blocked_unexpected_cycle_record_type"
    if _is_insufficient_history(cycle_decision, cycle_decision_reason):
        if observed_usable_bars is None:
            return "unknown_from_cycle_artifact"
        if observed_usable_bars < required_usable_bars:
            return "insufficient_history"
        return "inconsistent_cycle_artifact"
    if observed_usable_bars is None:
        return "cycle_not_insufficient_history"
    if observed_usable_bars >= required_usable_bars:
        return "ready_from_cycle_artifact"
    return "inconsistent_cycle_artifact"


def _data_readiness_blockers(
    cycle_artifact: _ArtifactRead,
    brief_artifact: _ArtifactRead,
    cycle_record: Mapping[str, object],
    brief_record: Mapping[str, object],
    cycle_record_type: str,
    brief_record_type: str,
    cycle_decision: str,
    cycle_decision_reason: str,
    data_readiness_state: str,
    missing_usable_bars: int | None,
    observed_usable_bars: int | None,
) -> list[str]:
    blockers: list[str] = []
    if not cycle_artifact.parsed:
        blockers.append(_SOURCE_ARTIFACT_BLOCKER)
    if cycle_artifact.parsed and cycle_record_type not in _SOURCE_CYCLE_RECORD_TYPES:
        blockers.append(_UNEXPECTED_CYCLE_RECORD_TYPE_BLOCKER)
    if (
        brief_artifact.provided
        and brief_artifact.parsed
        and brief_record_type != _SOURCE_BRIEF_RECORD_TYPE
    ):
        blockers.append(_UNEXPECTED_BRIEF_RECORD_TYPE_BLOCKER)
    if brief_artifact.provided and not brief_artifact.parsed:
        blockers.append("missing_or_invalid_brief_artifact")
    blockers.extend(_string_list(cycle_record.get("blockers")))
    blockers.extend(_string_list(brief_record.get("blockers")))
    if _is_insufficient_history(cycle_decision, cycle_decision_reason):
        blockers.append("sma_insufficient_history")
    if data_readiness_state == "unknown_from_cycle_artifact" and observed_usable_bars is None:
        blockers.append(_MISSING_OBSERVED_BARS_BLOCKER)
    if missing_usable_bars is not None and missing_usable_bars > 0:
        blockers.append(_MISSING_USABLE_BARS_BLOCKER)
    if data_readiness_state == "inconsistent_cycle_artifact":
        blockers.append(_COUNT_DECISION_CONFLICT_BLOCKER)
    if not _source_safety_flags_preserved(cycle_record, brief_record):
        blockers.append(_SOURCE_SAFETY_BLOCKER)
    return list(_dedupe(tuple(blockers)))


def _recommended_next_action(
    data_readiness_state: str,
    blockers: list[str],
) -> str:
    if _SOURCE_ARTIFACT_BLOCKER in blockers or _UNEXPECTED_CYCLE_RECORD_TYPE_BLOCKER in blockers:
        return "rebuild_or_validate_cycle_artifact_before_data_readiness_review"
    if _SOURCE_SAFETY_BLOCKER in blockers:
        return "rebuild_source_artifacts_with_false_safety_flags_before_review"
    if data_readiness_state == "unknown_from_cycle_artifact":
        return "expose_or_import_deterministic_local_daily_bars_before_next_etf_sma_cycle"
    if data_readiness_state == "insufficient_history":
        return "import_deterministic_local_daily_bars_until_sma200_has_200_usable_asof_bars"
    if data_readiness_state == "inconsistent_cycle_artifact":
        return "rebuild_or_validate_cycle_artifact_before_data_readiness_review"
    return "offline_operator_review_only_no_broker_action"


def _next_offline_data_action(
    data_readiness_state: str,
    recommended_next_action: str,
) -> str:
    if data_readiness_state.startswith("blocked_"):
        return recommended_next_action
    if data_readiness_state in {"unknown_from_cycle_artifact", "insufficient_history"}:
        return recommended_next_action
    if data_readiness_state == "cycle_not_insufficient_history":
        return "preserve_offline_cycle_evidence_for_operator_review"
    if data_readiness_state == "inconsistent_cycle_artifact":
        return recommended_next_action
    return "no_offline_data_import_required_by_this_checkpoint"


def _available_evidence(
    cycle_record: Mapping[str, object],
    brief_record: Mapping[str, object],
    required_usable_bars: int,
    required_source: str,
    observed_usable_bars: int | None,
    observed_source: str,
) -> dict[str, object]:
    return {
        "cycle_decision": _first_text(
            cycle_record.get("cycle_decision"),
            cycle_record.get("decision"),
            brief_record.get("cycle_decision"),
        ),
        "cycle_decision_reason": _first_text(
            cycle_record.get("cycle_decision_reason"),
            cycle_record.get("decision_reason"),
            brief_record.get("cycle_decision_reason"),
        ),
        "cycle_next_allowed_action": _first_text(
            cycle_record.get("cycle_next_allowed_action"),
            brief_record.get("cycle_next_allowed_action"),
        ),
        "m376_terminal": _first_bool(
            cycle_record.get("m376_terminal"),
            brief_record.get("m376_terminal"),
        ),
        "m376_status": _first_text(
            cycle_record.get("m376_status"),
            brief_record.get("m376_status"),
        ),
        "m376_terminal_state": _first_text(
            cycle_record.get("m376_terminal_state"),
            brief_record.get("m376_terminal_state"),
        ),
        "open_order_count": _first_int(
            cycle_record.get("open_order_count"),
            brief_record.get("open_order_count"),
        ),
        "open_order_present": _first_bool(
            cycle_record.get("open_order_present"),
            brief_record.get("open_order_present"),
        ),
        "open_spy_order_present": _first_bool(
            cycle_record.get("open_spy_order_present"),
            brief_record.get("open_spy_order_present"),
        ),
        "spy_position_qty": _first_text(
            cycle_record.get("spy_position_qty"),
            brief_record.get("spy_position_qty"),
        ),
        "required_usable_bars": required_usable_bars,
        "required_usable_bars_source": required_source,
        "observed_usable_bars": observed_usable_bars,
        "observed_usable_bars_source": observed_source,
    }


def _source_safety_flags_preserved(*records: Mapping[str, object]) -> bool:
    for record in records:
        for field_name in _SOURCE_FALSE_FIELDS:
            if field_name in record and record[field_name] is not False:
                return False
        if record.get("live_authorized") is True:
            return False
        if record.get("not_live_authorized") is False:
            return False
    return True


def _forbidden_actions() -> list[str]:
    return [
        "broker_mutation_from_etf_sma_data_readiness_checkpoint",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_data_readiness_checkpoint",
    ]


def _broker_action_flags() -> dict[str, bool]:
    return {
        "submit": False,
        "cancel": False,
        "replace": False,
        "close": False,
        "liquidate": False,
        "mutation": False,
    }


def _is_insufficient_history(cycle_decision: str, cycle_decision_reason: str) -> bool:
    return (
        cycle_decision == "insufficient_history"
        or cycle_decision_reason == "sma_insufficient_history"
    )


def _config(value: object) -> EtfSmaDataReadinessCheckpointConfig:
    if type(value) is not EtfSmaDataReadinessCheckpointConfig:
        raise ValidationError("config must be an EtfSmaDataReadinessCheckpointConfig.")
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


def _optional_path(value: object, field_name: str) -> Path | None:
    if value in (None, ""):
        return None
    return _required_path(value, field_name)


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


def _optional_int(value: object) -> int | None:
    if type(value) is int:
        return value if value >= 0 else None
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _first_int(*values: object) -> int | None:
    for value in values:
        integer = _optional_int(value)
        if integer is not None:
            return integer
    return None


def _first_bool(*values: object) -> bool | None:
    for value in values:
        if value is True:
            return True
        if value is False:
            return False
    return None


def _first_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _none_text(value: object) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _has_any_key(record: Mapping[str, object], keys: tuple[str, ...]) -> bool:
    return any(key in record for key in keys)


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
