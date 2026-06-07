"""Offline ETF/SMA evidence rollup from local research artifacts only.

This module reads caller-supplied JSONL artifacts. It does not read operator
input files directly, load profiles or credentials, import broker SDKs, open
network connections, or expose a broker mutation path.
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
    "ETF_SMA_EVIDENCE_ROLLUP_LABELS",
    "EtfSmaEvidenceRollupConfig",
    "EtfSmaEvidenceRollupWriteResult",
    "build_etf_sma_evidence_rollup",
    "render_etf_sma_evidence_rollup_json",
    "render_etf_sma_evidence_rollup_text",
    "write_etf_sma_evidence_rollup_jsonl",
]


ETF_SMA_EVIDENCE_ROLLUP_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M413"
_RECORD_TYPE = "etf_sma_evidence_rollup"
_COMMAND = "etf-sma-evidence-rollup"
_STRATEGY = "spy_etf_sma_50_200_daily_long_only"
_DEFAULT_SYMBOL = "SPY"
_PROFIT_CLAIM = "none"
_MANUAL_RECORD_TYPE = "etf_sma_local_bars_manual_import"
_REFRESH_RECORD_TYPE = "etf_sma_local_bars_backtest_refresh"
_BRIEF_RECORD_TYPE = "etf_sma_operating_brief"
_BRIEF_MILESTONE = "M412"
_SUCCESS_STATE = "offline_evidence_rollup_ready"
_BLOCKED_STATE = "blocked_invalid_offline_evidence"
_CONSISTENT_STATE = "m411_m412_artifacts_consistent"
_BLOCKED_CONSISTENCY_STATE = "blocked_invalid_source_artifacts"
_MANUAL_READY = "canonical_local_operator_bars_ready"
_REFRESHED = "backtest_evidence_refreshed"
_PERFORMANCE_EVALUATED = "post_signal_returns_evaluated"
_BRIEF_READY = "m411_evidence_summarized"
_DATA_BASIS = "raw_close_price_return"
_EVIDENCE_SCOPE = "signal_backtest_pipeline_only"
_RAW_CLOSE_LIMITATION = (
    "Evidence is raw-close price-return evidence only; M413 does not infer "
    "adjusted-close, dividend, split, or total-return evidence."
)
_OPERATOR_DATA_BOUNDARY = (
    "M413 reads M411 and M412 JSONL artifacts only and does not read .data "
    "operator inputs directly."
)
_NEXT_ALLOWED_ACTIONS = (
    "offline_adjusted_close_evidence_upgrade",
    "offline_total_return_evidence_upgrade",
    "scheduled_preview_only_brief",
    "read_only_broker_reconciliation_separate_milestone",
)
_WRITE_RESULT_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "broker_network_access",
    "credential_access",
    "network_access_attempted",
    "credential_access_attempted",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
)
_SOURCE_FALSE_FIELDS = frozenset(
    (
        "submitted",
        "mutated",
        "submit_authorized",
        "submit_path_allowed",
        "paper_submit_approved",
        "paper_submit_authorized",
        "broker_mutation_allowed",
        "broker_mutation_authorized",
        "broker_action_performed",
        "broker_actions_performed",
        "broker_network_access",
        "credential_access",
        "network_access_attempted",
        "credential_access_attempted",
        "market_data_fetch_performed",
        "live_authorized",
    )
)
_SUMMARY_FIELDS = (
    "usable_bar_count",
    "evaluated_return_count",
    "entry_count",
    "exit_count",
    "trade_count",
    "final_posture",
    "final_exposure",
    "final_decision",
)
_CONSISTENCY_FIELDS = (
    *_SUMMARY_FIELDS,
    "profit_claim",
)
_INT_SUMMARY_FIELDS = (
    "usable_bar_count",
    "evaluated_return_count",
    "entry_count",
    "exit_count",
    "trade_count",
    "final_exposure",
)
_RAW_CLOSE_ONLY_BOOL_FIELDS = frozenset(
    (
        "raw_close_price_return_evidence_only",
        "raw_close_only",
    )
)
_ADJUSTED_OR_TOTAL_RETURN_TRUE_FIELDS = frozenset(
    (
        "adjusted_close_evidence",
        "adjusted_close_evidence_only",
        "adjusted_close_price_return_evidence",
        "adjusted_close_price_return_evidence_only",
        "total_return_evidence",
        "total_return_evidence_only",
        "total_return_price_return_evidence",
        "total_return_price_return_evidence_only",
    )
)
_RAW_CLOSE_BASIS_FIELDS = frozenset(
    (
        "data_basis",
        "evidence_basis",
        "performance_basis",
        "performance_evidence_basis",
        "return_basis",
        "return_construction_basis",
    )
)


@dataclass(frozen=True, slots=True)
class EtfSmaEvidenceRollupConfig:
    """Explicit local artifact inputs for one offline ETF/SMA evidence rollup."""

    run_id: str
    manual_import_log: Path | str
    backtest_refresh_log: Path | str
    operating_brief_log: Path | str
    generated_at: datetime | str
    symbol: str = _DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "manual_import_log",
            _required_path(self.manual_import_log, "manual_import_log"),
        )
        object.__setattr__(
            self,
            "backtest_refresh_log",
            _required_path(self.backtest_refresh_log, "backtest_refresh_log"),
        )
        object.__setattr__(
            self,
            "operating_brief_log",
            _required_path(self.operating_brief_log, "operating_brief_log"),
        )
        object.__setattr__(
            self,
            "generated_at",
            _generated_at_text(self.generated_at),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaEvidenceRollupWriteResult:
    """Local JSONL write metadata for a single evidence-rollup record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_actions_performed: bool
    broker_network_access: bool
    credential_access: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    paper_submit_authorized: bool
    broker_mutation_authorized: bool
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
            "broker_network_access": self.broker_network_access,
            "credential_access": self.credential_access,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "paper_submit_authorized": self.paper_submit_authorized,
            "broker_mutation_authorized": self.broker_mutation_authorized,
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
            "latest_milestone": _text(latest.get("milestone")),
            "error": self.error,
        }


def build_etf_sma_evidence_rollup(
    config: EtfSmaEvidenceRollupConfig,
) -> dict[str, object]:
    """Build one fail-closed evidence rollup from explicit local artifacts."""

    checked_config = _config(config)
    manual_artifact = _read_jsonl_artifact(checked_config.manual_import_log)
    refresh_artifact = _read_jsonl_artifact(checked_config.backtest_refresh_log)
    brief_artifact = _read_jsonl_artifact(checked_config.operating_brief_log)

    manual_record = manual_artifact.latest_record or {}
    refresh_record = refresh_artifact.latest_record or {}
    brief_record = brief_artifact.latest_record or {}

    consistency = _artifact_consistency(manual_record, refresh_record, brief_record)
    blockers = _dedupe(
        (
            *_artifact_blockers(
                "manual_import",
                manual_artifact,
                expected_record_type=_MANUAL_RECORD_TYPE,
            ),
            *_artifact_blockers(
                "backtest_refresh",
                refresh_artifact,
                expected_record_type=_REFRESH_RECORD_TYPE,
            ),
            *_artifact_blockers(
                "operating_brief",
                brief_artifact,
                expected_record_type=_BRIEF_RECORD_TYPE,
                expected_milestone=_BRIEF_MILESTONE,
            ),
            *_manual_record_blockers(manual_record),
            *_refresh_record_blockers(refresh_record),
            *_brief_record_blockers(brief_record),
            *_consistency_blockers(consistency),
        )
    )
    summary_values = _summary_values(manual_record, refresh_record, brief_record)
    raw_close_limitation = _first_text(
        brief_record.get("raw_close_limitation"),
        _RAW_CLOSE_LIMITATION,
    )
    rollup_state = _BLOCKED_STATE if blockers else _SUCCESS_STATE
    artifact_consistency_state = (
        _CONSISTENT_STATE if not blockers else _BLOCKED_CONSISTENCY_STATE
    )
    operator_data_provenance_status = (
        "m411_manual_import_artifact_operator_bars_ready"
        if not blockers
        else "blocked_m411_m412_artifact_boundary_invalid"
    )

    payload: dict[str, object] = {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": checked_config.generated_at,
        "as_of": checked_config.generated_at,
        "symbol": checked_config.symbol,
        "strategy": _STRATEGY,
        "rollup_state": rollup_state,
        "labels": list(ETF_SMA_EVIDENCE_ROLLUP_LABELS),
        "source_artifacts": {
            "manual_import_log": manual_artifact.summary(),
            "backtest_refresh_log": refresh_artifact.summary(),
            "operating_brief_log": brief_artifact.summary(),
        },
        "artifact_consistency_state": artifact_consistency_state,
        "artifact_consistency": consistency,
        "operator_data_provenance_status": operator_data_provenance_status,
        "operator_data_source_boundary": _OPERATOR_DATA_BOUNDARY,
        "data_basis": _DATA_BASIS,
        "raw_close_limitation": raw_close_limitation,
        "raw_close_price_return_evidence_only": True,
        "evidence_scope": _EVIDENCE_SCOPE,
        "evidence_scope_details": [
            "signal/backtest/pipeline evidence only",
            "raw-close price-return evidence only",
            "no profitability claim",
            "no paper submit authorization",
            "no live authorization",
            "offline local JSONL artifacts only",
        ],
        "manual_import_state": _text(manual_record.get("manual_import_state")),
        "refresh_state": _first_text(
            refresh_record.get("refresh_state"),
            manual_record.get("refresh_state"),
            brief_record.get("refresh_state"),
        ),
        "performance_evidence_state": _first_text(
            refresh_record.get("performance_evidence_state"),
            manual_record.get("performance_evidence_state"),
            brief_record.get("performance_evidence_state"),
        ),
        "brief_state": _text(brief_record.get("brief_state")),
        "source_summaries": {
            "manual_import": _manual_summary(manual_record),
            "backtest_refresh": _refresh_summary(refresh_record),
            "operating_brief": _brief_summary(brief_record),
        },
        "broker_position_state": "not_observed_in_m413",
        "open_order_state": "not_observed_in_m413",
        "paper_action_recommendation": "none",
        "profit_claim": _PROFIT_CLAIM,
        "paper_submit_authorized": False,
        "live_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_network_access": False,
        "credential_access": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_mutation_authorized": False,
        "market_data_fetch_performed": False,
        "blockers": list(blockers),
        "next_allowed_actions": list(_NEXT_ALLOWED_ACTIONS),
    }
    payload.update(summary_values)
    return payload


def render_etf_sma_evidence_rollup_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_evidence_rollup_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-facing ETF/SMA evidence rollup summary."""

    return "\n".join(
        (
            "SPY ETF/SMA evidence rollup",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"rollup_state: {payload.get('rollup_state', '')}",
            "artifact_consistency_state: "
            f"{payload.get('artifact_consistency_state', '')}",
            f"data_basis: {payload.get('data_basis', '')}",
            f"evidence_scope: {payload.get('evidence_scope', '')}",
            f"manual_import_state: {payload.get('manual_import_state', '')}",
            f"refresh_state: {payload.get('refresh_state', '')}",
            f"brief_state: {payload.get('brief_state', '')}",
            "performance_evidence_state: "
            f"{payload.get('performance_evidence_state', '')}",
            f"usable_bar_count: {payload.get('usable_bar_count', '')}",
            f"evaluated_return_count: {payload.get('evaluated_return_count', '')}",
            f"final_posture: {payload.get('final_posture', '')}",
            f"final_exposure: {payload.get('final_exposure', '')}",
            f"final_decision: {payload.get('final_decision', '')}",
            f"paper_action_recommendation: {payload.get('paper_action_recommendation', '')}",
            "paper_submit_authorized: "
            f"{_bool_text(payload.get('paper_submit_authorized'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
        )
    )


def write_etf_sma_evidence_rollup_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaEvidenceRollupWriteResult:
    """Write exactly one JSONL record, replacing any prior file contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_evidence_rollup_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaEvidenceRollupWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        broker_network_access=False,
        credential_access=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        paper_submit_authorized=False,
        broker_mutation_authorized=False,
        live_authorized=False,
    )


def _artifact_blockers(
    prefix: str,
    artifact: _ArtifactRead,
    *,
    expected_record_type: str,
    expected_milestone: str | None = None,
) -> tuple[str, ...]:
    if not artifact.found:
        return (f"{prefix}_artifact_path_not_found",)
    if not artifact.parsed or artifact.latest_record is None:
        return (f"{prefix}_artifact_{artifact.error}",)
    record_type = _text(artifact.latest_record.get("record_type"))
    if record_type != expected_record_type:
        return (f"{prefix}_artifact_unexpected_record_type",)
    if expected_milestone is not None:
        milestone = _text(artifact.latest_record.get("milestone"))
        if milestone != expected_milestone:
            return (f"{prefix}_artifact_unexpected_milestone",)
    return ()


def _manual_record_blockers(record: Mapping[str, object]) -> tuple[str, ...]:
    if not record:
        return ()
    blockers: list[str] = []
    if _text(record.get("symbol")) != _DEFAULT_SYMBOL:
        blockers.append("manual_import_artifact_symbol_invalid")
    if _text(record.get("manual_import_state")) != _MANUAL_READY:
        blockers.append("manual_import_artifact_manual_import_state_invalid")
    if record.get("canonical_csv_written") is not True:
        blockers.append("manual_import_artifact_canonical_csv_written_not_true")
    if record.get("refresh_rerun_performed") is not True:
        blockers.append("manual_import_artifact_refresh_rerun_performed_not_true")
    if record.get("operator_evidence_synthetic") is True:
        blockers.append("manual_import_artifact_operator_evidence_synthetic_true")
    if record.get("fixture_sample_synthetic_test_data_used_as_operator_evidence") is True:
        blockers.append("manual_import_artifact_fixture_sample_evidence_true")
    blockers.extend(_shared_source_record_blockers("manual_import_artifact", record))
    return tuple(blockers)


def _refresh_record_blockers(record: Mapping[str, object]) -> tuple[str, ...]:
    if not record:
        return ()
    blockers: list[str] = []
    if _text(record.get("symbol")) != _DEFAULT_SYMBOL:
        blockers.append("backtest_refresh_artifact_symbol_invalid")
    if _text(record.get("backtest_state")) != "completed":
        blockers.append("backtest_refresh_artifact_backtest_state_invalid")
    blockers.extend(_shared_source_record_blockers("backtest_refresh_artifact", record))
    return tuple(blockers)


def _brief_record_blockers(record: Mapping[str, object]) -> tuple[str, ...]:
    if not record:
        return ()
    blockers: list[str] = []
    if _text(record.get("symbol")) != _DEFAULT_SYMBOL:
        blockers.append("operating_brief_artifact_symbol_invalid")
    if _text(record.get("brief_state")) != _BRIEF_READY:
        blockers.append("operating_brief_artifact_brief_state_invalid")
    if _text(record.get("manual_import_state")) != _MANUAL_READY:
        blockers.append("operating_brief_artifact_manual_import_state_invalid")
    blockers.extend(_shared_source_record_blockers("operating_brief_artifact", record))
    return tuple(blockers)


def _shared_source_record_blockers(
    prefix: str,
    record: Mapping[str, object],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if _text(record.get("refresh_state")) != _REFRESHED:
        blockers.append(f"{prefix}_refresh_state_invalid")
    if _text(record.get("performance_evidence_state")) != _PERFORMANCE_EVALUATED:
        blockers.append(f"{prefix}_performance_evidence_state_invalid")
    blockers.extend(_profit_claim_blockers(prefix, record))
    blockers.extend(_source_blocker_list_blockers(prefix, record))
    blockers.extend(_source_false_field_blockers(prefix, record))
    blockers.extend(_raw_close_evidence_blockers(prefix, record))
    return tuple(blockers)


def _source_false_field_blockers(
    prefix: str,
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    blockers: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            if key_text in _SOURCE_FALSE_FIELDS and item is not False:
                blockers.append(f"{prefix}_{_path_suffix(child_path)}_not_false")
            blockers.extend(_source_false_field_blockers(prefix, item, child_path))
    elif isinstance(value, list | tuple):
        for item in value:
            blockers.extend(_source_false_field_blockers(prefix, item, path))
    return tuple(blockers)


def _profit_claim_blockers(
    prefix: str,
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    blockers: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            if key_text == "profit_claim" and _text(item) != _PROFIT_CLAIM:
                blockers.append(
                    f"{prefix}_{_path_suffix(child_path)}_not_none"
                )
            blockers.extend(_profit_claim_blockers(prefix, item, child_path))
    elif isinstance(value, list | tuple):
        for item in value:
            if isinstance(item, str) and item.startswith("profit_claim="):
                if item != "profit_claim=none":
                    blockers.append(f"{prefix}_{_path_suffix(path)}_profit_claim_label_not_none")
            else:
                blockers.extend(_profit_claim_blockers(prefix, item, path))
    return tuple(blockers)


def _source_blocker_list_blockers(
    prefix: str,
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    blockers: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            if key_text == "blockers" and _string_list(item):
                blockers.append(f"{prefix}_{_path_suffix(child_path)}_present")
            blockers.extend(_source_blocker_list_blockers(prefix, item, child_path))
    elif isinstance(value, list | tuple):
        for item in value:
            blockers.extend(_source_blocker_list_blockers(prefix, item, path))
    return tuple(blockers)


def _raw_close_evidence_blockers(
    prefix: str,
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    blockers: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            suffix = _path_suffix(child_path)
            if key_text in _RAW_CLOSE_ONLY_BOOL_FIELDS and item is not True:
                blockers.append(f"{prefix}_{suffix}_not_true")
            if key_text in _ADJUSTED_OR_TOTAL_RETURN_TRUE_FIELDS and item is True:
                blockers.append(f"{prefix}_{suffix}_not_allowed")
            if key_text in _RAW_CLOSE_BASIS_FIELDS and _basis_claims_non_raw_close(item):
                blockers.append(f"{prefix}_{suffix}_not_raw_close")
            if key_text == "adjustment_policy" and _adjustment_policy_claims_non_raw_close(item):
                blockers.append(f"{prefix}_{suffix}_not_raw_close")
            blockers.extend(_raw_close_evidence_blockers(prefix, item, child_path))
    elif isinstance(value, list | tuple):
        for item in value:
            blockers.extend(_raw_close_evidence_blockers(prefix, item, path))
    return tuple(blockers)


def _basis_claims_non_raw_close(value: object) -> bool:
    text = _normalized_text(value)
    if not text:
        return False
    if "raw_close" in text or "raw close" in text:
        return False
    return "adjusted_close" in text or "adjusted close" in text or "total_return" in text or "total return" in text


def _adjustment_policy_claims_non_raw_close(value: object) -> bool:
    text = _normalized_text(value)
    if not text:
        return False
    if "raw_close" in text or "raw close" in text:
        return False
    return "adjusted_close" in text or "adjusted close" in text or "total_return" in text or "total return" in text


def _artifact_consistency(
    manual_record: Mapping[str, object],
    refresh_record: Mapping[str, object],
    brief_record: Mapping[str, object],
) -> dict[str, object]:
    checks = (
        ("manual_refresh", manual_record, refresh_record),
        ("manual_brief", manual_record, brief_record),
        ("refresh_brief", refresh_record, brief_record),
    )
    mismatches: list[str] = []
    missing_fields: list[str] = []
    for pair_name, left, right in checks:
        for field_name in _CONSISTENCY_FIELDS:
            left_value = _normalized_summary_value(field_name, left.get(field_name))
            right_value = _normalized_summary_value(field_name, right.get(field_name))
            if left_value is None or right_value is None:
                missing_fields.append(f"{pair_name}.{field_name}")
            elif left_value != right_value:
                mismatches.append(f"{pair_name}.{field_name}")
    return {
        "checked_pairs": [check[0] for check in checks],
        "checked_fields": list(_CONSISTENCY_FIELDS),
        "matching_evidence": not mismatches and not missing_fields,
        "mismatches": mismatches,
        "missing_fields": missing_fields,
    }


def _consistency_blockers(consistency: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    for field_path in _string_list(consistency.get("mismatches")):
        blockers.append(f"{field_path.replace('.', '_')}_mismatch")
    for field_path in _string_list(consistency.get("missing_fields")):
        blockers.append(f"{field_path.replace('.', '_')}_missing")
    return tuple(blockers)


def _summary_values(
    manual_record: Mapping[str, object],
    refresh_record: Mapping[str, object],
    brief_record: Mapping[str, object],
) -> dict[str, object]:
    values: dict[str, object] = {}
    for field_name in _SUMMARY_FIELDS:
        value = _normalized_summary_value(
            field_name,
            _first_non_none(
                brief_record.get(field_name),
                refresh_record.get(field_name),
                manual_record.get(field_name),
            ),
        )
        values[field_name] = value
    return values


def _manual_summary(record: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": _text(record.get("record_type")),
        "run_id": _text(record.get("run_id")),
        "manual_import_state": _text(record.get("manual_import_state")),
        "refresh_state": _text(record.get("refresh_state")),
        "performance_evidence_state": _text(record.get("performance_evidence_state")),
        "canonical_csv_written": record.get("canonical_csv_written") is True,
        "refresh_rerun_performed": record.get("refresh_rerun_performed") is True,
        "operator_evidence_synthetic": record.get("operator_evidence_synthetic") is True,
        "profit_claim": _text(record.get("profit_claim")),
        "submitted": record.get("submitted") is True,
        "mutated": record.get("mutated") is True,
        "broker_network_access": record.get("broker_network_access") is True,
        "credential_access": record.get("credential_access") is True,
    }


def _refresh_summary(record: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": _text(record.get("record_type")),
        "run_id": _text(record.get("run_id")),
        "refresh_state": _text(record.get("refresh_state")),
        "backtest_state": _text(record.get("backtest_state")),
        "performance_evidence_state": _text(record.get("performance_evidence_state")),
        "profit_claim": _text(record.get("profit_claim")),
        "submitted": record.get("submitted") is True,
        "mutated": record.get("mutated") is True,
        "network_access_attempted": record.get("network_access_attempted") is True,
        "credential_access_attempted": record.get("credential_access_attempted") is True,
    }


def _brief_summary(record: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": _text(record.get("record_type")),
        "run_id": _text(record.get("run_id")),
        "milestone": _text(record.get("milestone")),
        "brief_state": _text(record.get("brief_state")),
        "refresh_state": _text(record.get("refresh_state")),
        "performance_evidence_state": _text(record.get("performance_evidence_state")),
        "profit_claim": _text(record.get("profit_claim")),
        "submitted": record.get("submitted") is True,
        "mutated": record.get("mutated") is True,
        "broker_network_access": record.get("broker_network_access") is True,
        "credential_access": record.get("credential_access") is True,
        "paper_submit_authorized": record.get("paper_submit_authorized") is True,
        "live_authorized": record.get("live_authorized") is True,
    }


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
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return _ArtifactRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"invalid_jsonl_line_{line_number}",
            )
        if not isinstance(row, Mapping):
            return _ArtifactRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"jsonl_record_{line_number}_not_object",
            )
        records.append(dict(row))

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


def _config(config: EtfSmaEvidenceRollupConfig) -> EtfSmaEvidenceRollupConfig:
    if not isinstance(config, EtfSmaEvidenceRollupConfig):
        raise ValidationError("config must be an EtfSmaEvidenceRollupConfig.")
    return config


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _spy_symbol(value: object) -> str:
    symbol = symbol_value(value)
    if symbol != _DEFAULT_SYMBOL:
        raise ValidationError("M413 ETF/SMA evidence rollup supports SPY only.")
    return symbol


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        if not value.strip():
            raise ValidationError(f"{field_name} is required.")
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must point to a .jsonl file.")
    return path


def _output_path(value: Path | str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        if not value.strip():
            raise ValidationError("output_path is required.")
        path = Path(value)
    else:
        raise ValidationError("output_path must be a path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError("output_path must point to a .jsonl file.")
    return path


def _generated_at_text(value: datetime | str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("generated_at must be timezone-aware.")
        return value.isoformat()
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValidationError("generated_at is required.")
        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(
                "generated_at must be a timezone-aware ISO-8601 timestamp."
            ) from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError("generated_at must be timezone-aware.")
        return normalized
    raise ValidationError("generated_at must be a timezone-aware ISO-8601 timestamp.")


def _normalized_summary_value(field_name: str, value: object) -> object | None:
    if value is None:
        return None
    if field_name in _INT_SUMMARY_FIELDS:
        return _optional_int(value)
    return _text(value) or None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _first_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _first_non_none(*values: object) -> object:
    for value in values:
        if value is not None:
            return value
    return None


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _normalized_text(value: object) -> str:
    return _text(value).strip().lower().replace("-", "_")


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Iterable):
        return [str(item) for item in value if str(item)]
    return []


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _path_suffix(path: Iterable[str]) -> str:
    cleaned = [part for part in path if part]
    return "_".join(cleaned) if cleaned else "root"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _bool_text(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def _joined(values: Iterable[str]) -> str:
    return ", ".join(values) if values else "none"
