"""Offline adjusted-close evidence gate for the SPY ETF/SMA pipeline.

This module reads only explicit local files supplied by the caller. It does not
load profiles or credentials, import broker SDKs, open network connections,
discover operator data directories, or expose a broker mutation path.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_ADJUSTED_CLOSE_EVIDENCE_GATE_LABELS",
    "EtfSmaAdjustedCloseEvidenceGateConfig",
    "EtfSmaAdjustedCloseEvidenceGateWriteResult",
    "build_etf_sma_adjusted_close_evidence_gate",
    "render_etf_sma_adjusted_close_evidence_gate_json",
    "render_etf_sma_adjusted_close_evidence_gate_text",
    "write_etf_sma_adjusted_close_evidence_gate_jsonl",
]


ETF_SMA_ADJUSTED_CLOSE_EVIDENCE_GATE_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M414"
_RECORD_TYPE = "etf_sma_adjusted_close_evidence_gate"
_COMMAND = "etf-sma-adjusted-close-evidence-gate"
_PRIOR_RECORD_TYPE = "etf_sma_evidence_rollup"
_PRIOR_MILESTONE = "M413"
_STRATEGY = "spy_etf_sma_50_200_daily_long_only"
_DEFAULT_SYMBOL = "SPY"
_PRIOR_DATA_BASIS = "raw_close_price_return"
_TARGET_DATA_BASIS = "adjusted_close_price_return"
_EVIDENCE_SCOPE = "signal_backtest_pipeline_only"
_PROFIT_CLAIM = "none"
_TOTAL_RETURN_CLAIM = "none"
_READY_STATE = "adjusted_close_evidence_gate_ready"
_MISSING_INPUT_STATE = "blocked_missing_adjusted_close_operator_input"
_INVALID_OPERATOR_INPUT_STATE = "blocked_invalid_adjusted_close_operator_input"
_INVALID_PRIOR_STATE = "blocked_invalid_prior_evidence_rollup"
_STRICT_CSV_COLUMNS_WITH_MANIFEST_SYMBOL = (
    "date",
    "close",
    "adjusted_close",
    "volume",
)
_STRICT_CSV_COLUMNS_WITH_SYMBOL = (
    "symbol",
    "date",
    "close",
    "adjusted_close",
    "volume",
)
_MANIFEST_REQUIRED_FIELDS = (
    "symbol",
    "input_csv",
    "expected_input_sha256",
    "data_basis",
    "adjustment_policy",
    "source_notes",
    "operator_attested",
    "attested_by",
    "attested_at",
    "timeframe",
    "contains_synthetic_data",
    "contains_fixture_data",
    "contains_sample_data",
    "contains_test_data",
)
_MANIFEST_STRING_FIELDS = (
    "symbol",
    "input_csv",
    "expected_input_sha256",
    "data_basis",
    "adjustment_policy",
    "source_notes",
    "attested_by",
    "attested_at",
    "timeframe",
)
_MANIFEST_FALSE_FLAGS = (
    "contains_synthetic_data",
    "contains_fixture_data",
    "contains_sample_data",
    "contains_test_data",
)
_MANIFEST_FORBIDDEN_TEXT_FIELDS = (
    "adjustment_policy",
    "source_notes",
    "source_description",
    "source_type",
    "data_vendor_or_origin",
    "acquisition_method",
    "notes",
)
_AMBIGUOUS_TEXT_VALUES = frozenset(
    ("", "ambiguous", "n/a", "na", "none", "null", "tbd", "todo", "unknown")
)
_FORBIDDEN_PROVENANCE_TERMS = frozenset(
    (
        "codex",
        "demo",
        "fake",
        "fixture",
        "generated",
        "mock",
        "sample",
        "synthetic",
        "test",
    )
)
_DAILY_TIMEFRAME_VALUES = frozenset(
    ("1_day", "1d", "d", "daily", "daily_bars", "day", "one_day")
)
_PRIOR_FALSE_FIELDS = frozenset(
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
_NEXT_ALLOWED_ACTIONS_BLOCKED = (
    "operator_supply_adjusted_close_csv_and_manifest",
    "offline_adjusted_close_import_separate_run",
    "offline_total_return_requirements_packet",
    "scheduled_preview_only_brief",
)
_NEXT_ALLOWED_ACTIONS_READY = (
    "offline_adjusted_close_import_separate_run",
    "offline_total_return_requirements_packet",
    "scheduled_preview_only_brief",
)


@dataclass(frozen=True, slots=True)
class EtfSmaAdjustedCloseEvidenceGateConfig:
    """Explicit local inputs for one adjusted-close evidence gate evaluation."""

    run_id: str
    run_log: Path | str
    evidence_rollup_log: Path | str
    generated_at: datetime | str
    adjusted_bars_csv: Path | str | None = None
    provenance_manifest: Path | str | None = None
    symbol: str = _DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(self, "run_log", _jsonl_path(self.run_log, "run_log"))
        object.__setattr__(
            self,
            "evidence_rollup_log",
            _jsonl_path(self.evidence_rollup_log, "evidence_rollup_log"),
        )
        object.__setattr__(
            self,
            "adjusted_bars_csv",
            _optional_path(
                self.adjusted_bars_csv,
                "adjusted_bars_csv",
                required_suffix=".csv",
            ),
        )
        object.__setattr__(
            self,
            "provenance_manifest",
            _optional_path(
                self.provenance_manifest,
                "provenance_manifest",
                required_suffix=".json",
            ),
        )
        object.__setattr__(
            self,
            "generated_at",
            _generated_at_text(self.generated_at),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaAdjustedCloseEvidenceGateWriteResult:
    """Local JSONL write metadata for a single adjusted-close gate record."""

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
            "latest_rollup_state": _text(latest.get("rollup_state")),
            "latest_data_basis": _text(latest.get("data_basis")),
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class _ManifestValidation:
    supplied: bool
    found: bool
    parsed: bool
    valid: bool
    manifest: dict[str, object]
    blockers: tuple[str, ...]
    manifest_sha256: str | None
    normalized_input_csv: str | None

    def summary(self) -> dict[str, object]:
        return {
            "supplied": self.supplied,
            "found": self.found,
            "parsed": self.parsed,
            "valid": self.valid,
            "manifest_sha256": self.manifest_sha256,
            "expected_input_sha256": self.manifest.get("expected_input_sha256"),
            "data_basis": self.manifest.get("data_basis"),
            "symbol": self.manifest.get("symbol"),
            "operator_attested": self.manifest.get("operator_attested"),
            "attested_by": self.manifest.get("attested_by"),
            "attested_at": self.manifest.get("attested_at"),
            "adjustment_policy": self.manifest.get("adjustment_policy"),
            "source_notes": self.manifest.get("source_notes"),
            "timeframe": self.manifest.get("timeframe"),
            "normalized_input_csv": self.normalized_input_csv,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class _DataValidation:
    supplied: bool
    found: bool
    valid: bool
    blockers: tuple[str, ...]
    input_sha256: str | None
    schema: str
    columns: tuple[str, ...]
    source_row_count: int
    usable_bar_count: int
    symbol_source: str
    input_sorted_by_date: bool | None
    duplicate_dates: bool
    malformed_rows: bool
    missing_or_invalid_close: bool
    missing_or_invalid_adjusted_close: bool
    non_positive_close: bool
    non_positive_adjusted_close: bool
    missing_or_invalid_volume: bool
    non_spy_row_count: int

    def summary(self) -> dict[str, object]:
        return {
            "supplied": self.supplied,
            "found": self.found,
            "valid": self.valid,
            "input_sha256": self.input_sha256,
            "schema": self.schema,
            "columns": list(self.columns),
            "accepted_schemas": [
                list(_STRICT_CSV_COLUMNS_WITH_MANIFEST_SYMBOL),
                list(_STRICT_CSV_COLUMNS_WITH_SYMBOL),
            ],
            "source_row_count": self.source_row_count,
            "usable_bar_count": self.usable_bar_count,
            "symbol_source": self.symbol_source,
            "input_sorted_by_date": self.input_sorted_by_date,
            "duplicate_dates": self.duplicate_dates,
            "malformed_rows": self.malformed_rows,
            "missing_or_invalid_close": self.missing_or_invalid_close,
            "missing_or_invalid_adjusted_close": self.missing_or_invalid_adjusted_close,
            "non_positive_close": self.non_positive_close,
            "non_positive_adjusted_close": self.non_positive_adjusted_close,
            "missing_or_invalid_volume": self.missing_or_invalid_volume,
            "non_spy_row_count": self.non_spy_row_count,
            "blockers": list(self.blockers),
        }


def build_etf_sma_adjusted_close_evidence_gate(
    config: EtfSmaAdjustedCloseEvidenceGateConfig,
) -> dict[str, object]:
    """Build one fail-closed adjusted-close evidence gate record."""

    checked_config = _config(config)
    prior_artifact = _read_jsonl_artifact(checked_config.evidence_rollup_log)
    prior_record = prior_artifact.latest_record or {}
    prior_blockers = _prior_evidence_rollup_blockers(prior_artifact)
    input_pairing_blockers = _operator_input_pairing_blockers(checked_config)

    provenance = _empty_manifest_validation()
    data = _empty_data_validation()
    if checked_config.adjusted_bars_csv is not None and checked_config.provenance_manifest is not None:
        provenance = _validate_provenance_manifest(checked_config)
        data = _validate_adjusted_bars_csv(checked_config)
        provenance = _validate_provenance_input_sha256(provenance, data.input_sha256)

    missing_adjusted_input = (
        checked_config.adjusted_bars_csv is None
        and checked_config.provenance_manifest is None
    )
    operator_blockers = (
        ("missing_adjusted_close_operator_input",)
        if missing_adjusted_input
        else input_pairing_blockers
    )
    blockers = _dedupe(
        (
            *prior_blockers,
            *operator_blockers,
            *provenance.blockers,
            *data.blockers,
        )
    )
    state = _gate_state(
        prior_blockers=prior_blockers,
        missing_adjusted_input=missing_adjusted_input,
        operator_input_blocked=bool(
            operator_blockers or provenance.blockers or data.blockers
        ),
    )
    adjusted_close_evidence_available = state == _READY_STATE
    next_allowed_actions = (
        _NEXT_ALLOWED_ACTIONS_READY
        if adjusted_close_evidence_available
        else _NEXT_ALLOWED_ACTIONS_BLOCKED
    )

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "run_log": str(checked_config.run_log),
        "generated_at": checked_config.generated_at,
        "as_of": checked_config.generated_at,
        "symbol": checked_config.symbol,
        "strategy": _STRATEGY,
        "labels": list(ETF_SMA_ADJUSTED_CLOSE_EVIDENCE_GATE_LABELS),
        "adjusted_close_gate_state": state,
        "source_artifacts": {
            "evidence_rollup_log": prior_artifact.summary(),
            "adjusted_bars_csv": data.summary(),
            "provenance_manifest": provenance.summary(),
        },
        "prior_evidence_rollup_state": _prior_evidence_rollup_state(prior_artifact),
        "prior_evidence_rollup_declared_data_basis": _text(
            prior_record.get("data_basis")
        ),
        "prior_data_basis": _PRIOR_DATA_BASIS,
        "target_data_basis": _TARGET_DATA_BASIS,
        "total_return_claim": _TOTAL_RETURN_CLAIM,
        "profit_claim": _PROFIT_CLAIM,
        "evidence_scope": _EVIDENCE_SCOPE,
        "evidence_scope_details": [
            "signal/backtest/pipeline evidence only",
            "adjusted-close price-return evidence intake gate only",
            "no total-return claim",
            "no profitability claim",
            "no paper submit authorization",
            "no live authorization",
            "offline local files only",
        ],
        "raw_close_limitation_preserved": True,
        "raw_close_limitation": (
            "M414 preserves M413 as raw-close price-return evidence only and "
            "does not relabel it as adjusted-close or total-return evidence."
        ),
        "adjusted_close_evidence_available": adjusted_close_evidence_available,
        "operator_input_required": not adjusted_close_evidence_available,
        "operator_input_boundary": (
            "M414 reads adjusted-close CSV/provenance only when explicit CLI "
            "paths are supplied; it does not auto-discover .data files."
        ),
        "blockers": list(blockers),
        "next_allowed_actions": list(next_allowed_actions),
        "paper_submit_authorized": False,
        "live_authorized": False,
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "submit_path_allowed": False,
        "paper_submit_approved": False,
        "broker_mutation_authorized": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_network_access": False,
        "credential_access": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "market_data_fetch_performed": False,
        "paper_lab_only": True,
        "research_only": True,
        "signal_evaluation_only": True,
        "not_live_authorized": True,
    }


def render_etf_sma_adjusted_close_evidence_gate_json(
    payload: Mapping[str, object],
) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_adjusted_close_evidence_gate_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing adjusted-close evidence gate summary."""

    return "\n".join(
        (
            "SPY ETF/SMA adjusted-close evidence gate",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            "adjusted_close_gate_state: "
            f"{payload.get('adjusted_close_gate_state', '')}",
            "prior_evidence_rollup_state: "
            f"{payload.get('prior_evidence_rollup_state', '')}",
            f"prior_data_basis: {payload.get('prior_data_basis', '')}",
            f"target_data_basis: {payload.get('target_data_basis', '')}",
            "adjusted_close_evidence_available: "
            f"{_bool_text(payload.get('adjusted_close_evidence_available'))}",
            "operator_input_required: "
            f"{_bool_text(payload.get('operator_input_required'))}",
            f"evidence_scope: {payload.get('evidence_scope', '')}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"total_return_claim: {payload.get('total_return_claim', '')}",
            "paper_submit_authorized: "
            f"{_bool_text(payload.get('paper_submit_authorized'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
        )
    )


def write_etf_sma_adjusted_close_evidence_gate_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaAdjustedCloseEvidenceGateWriteResult:
    """Write exactly one JSONL record, replacing any prior file contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_adjusted_close_evidence_gate_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaAdjustedCloseEvidenceGateWriteResult(
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


def _prior_evidence_rollup_blockers(artifact: _ArtifactRead) -> tuple[str, ...]:
    if not artifact.found:
        return ("evidence_rollup_artifact_path_not_found",)
    if not artifact.parsed or artifact.latest_record is None:
        return (f"evidence_rollup_artifact_{artifact.error}",)

    record = artifact.latest_record
    blockers: list[str] = []
    if _text(record.get("record_type")) != _PRIOR_RECORD_TYPE:
        blockers.append("evidence_rollup_artifact_unexpected_record_type")
    if _text(record.get("milestone")) != _PRIOR_MILESTONE:
        blockers.append("evidence_rollup_artifact_unexpected_milestone")
    if _text(record.get("profit_claim")) != _PROFIT_CLAIM:
        blockers.append("prior_evidence_rollup_profit_claim_not_none")
    if _text(record.get("data_basis")) != _PRIOR_DATA_BASIS:
        blockers.append("prior_evidence_rollup_data_basis_not_raw_close")
    blockers.extend(_prior_false_field_blockers("prior_evidence_rollup", record))
    return _dedupe(blockers)


def _prior_false_field_blockers(
    prefix: str,
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    blockers: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            if key_text in _PRIOR_FALSE_FIELDS and item is not False:
                blockers.append(f"{prefix}_{_path_suffix(child_path)}_not_false")
            blockers.extend(_prior_false_field_blockers(prefix, item, child_path))
    elif isinstance(value, list | tuple):
        for item in value:
            blockers.extend(_prior_false_field_blockers(prefix, item, path))
    return tuple(blockers)


def _operator_input_pairing_blockers(
    config: EtfSmaAdjustedCloseEvidenceGateConfig,
) -> tuple[str, ...]:
    if config.adjusted_bars_csv is not None and config.provenance_manifest is None:
        return ("adjusted_bars_csv_without_provenance_manifest",)
    if config.adjusted_bars_csv is None and config.provenance_manifest is not None:
        return ("provenance_manifest_without_adjusted_bars_csv",)
    return ()


def _validate_provenance_manifest(
    config: EtfSmaAdjustedCloseEvidenceGateConfig,
) -> _ManifestValidation:
    path = config.provenance_manifest
    if path is None:
        return _empty_manifest_validation()
    if not path.is_file():
        return _ManifestValidation(
            supplied=True,
            found=False,
            parsed=False,
            valid=False,
            manifest={},
            blockers=("provenance_manifest_not_found",),
            manifest_sha256=None,
            normalized_input_csv=None,
        )

    manifest_sha256 = _sha256_file(path)
    try:
        manifest = _read_json_object(path, "provenance_manifest")
    except ValidationError as exc:
        return _ManifestValidation(
            supplied=True,
            found=True,
            parsed=False,
            valid=False,
            manifest={},
            blockers=(f"provenance_manifest:{_blocker_text(str(exc))}",),
            manifest_sha256=manifest_sha256,
            normalized_input_csv=None,
        )

    blockers: list[str] = []
    blockers.extend(
        f"missing_provenance_field:{field}"
        for field in _MANIFEST_REQUIRED_FIELDS
        if field not in manifest
    )

    for field in _MANIFEST_STRING_FIELDS:
        if field not in manifest:
            continue
        try:
            value = _required_string(manifest[field], field)
        except ValidationError:
            blockers.append(f"invalid_provenance_field:{field}")
            continue
        if field != "expected_input_sha256" and _token(value) in _AMBIGUOUS_TEXT_VALUES:
            blockers.append(f"ambiguous_provenance_field:{field}")

    if manifest.get("symbol") != _DEFAULT_SYMBOL:
        blockers.append("manifest_symbol_not_spy")
    if manifest.get("operator_attested") is not True:
        blockers.append("operator_attested_not_true")
    for field in _MANIFEST_FALSE_FLAGS:
        if manifest.get(field) is not False:
            blockers.append(f"{field}_not_false")

    expected_hash = manifest.get("expected_input_sha256")
    if "expected_input_sha256" not in manifest:
        blockers.append("missing_expected_input_sha256")
    elif type(expected_hash) is not str or not _valid_lower_sha256(expected_hash):
        blockers.append("invalid_expected_input_sha256")

    if manifest.get("data_basis") != _TARGET_DATA_BASIS:
        blockers.append("manifest_data_basis_not_adjusted_close_price_return")

    total_return_claim = manifest.get("total_return_claim")
    if total_return_claim is not None and _text(total_return_claim) != _TOTAL_RETURN_CLAIM:
        blockers.append("manifest_total_return_claim_not_none")

    if any(
        _provenance_text_has_forbidden_term(manifest.get(field))
        for field in _MANIFEST_FORBIDDEN_TEXT_FIELDS
    ):
        blockers.append("provenance_rejected_generated_sample_fixture_test_synthetic_codex")

    timeframe = manifest.get("timeframe")
    if type(timeframe) is str and _token(timeframe) not in _DAILY_TIMEFRAME_VALUES:
        blockers.append("timeframe_not_daily")

    attested_at = manifest.get("attested_at")
    if type(attested_at) is str and not _valid_iso_date_or_timestamp(attested_at):
        blockers.append("attested_at_not_iso_date_or_timestamp")

    normalized_input_csv: str | None = None
    if config.adjusted_bars_csv is not None and type(manifest.get("input_csv")) is str:
        provided = _normalized_compare_path(config.adjusted_bars_csv)
        manifest_values = {
            _normalized_compare_path(Path(str(manifest["input_csv"]))),
            _normalized_compare_path(Path(str(manifest["input_csv"])), base=path.parent),
        }
        normalized_input_csv = str(provided)
        if provided not in manifest_values:
            blockers.append("manifest_input_csv_path_mismatch")
    elif config.adjusted_bars_csv is not None:
        blockers.append("manifest_input_csv_path_mismatch")

    deduped_blockers = _dedupe(blockers)
    return _ManifestValidation(
        supplied=True,
        found=True,
        parsed=True,
        valid=not deduped_blockers,
        manifest=manifest,
        blockers=deduped_blockers,
        manifest_sha256=manifest_sha256,
        normalized_input_csv=normalized_input_csv,
    )


def _validate_provenance_input_sha256(
    provenance: _ManifestValidation,
    input_sha256: str | None,
) -> _ManifestValidation:
    if not provenance.supplied or not provenance.manifest:
        return provenance

    blockers = list(provenance.blockers)
    expected = provenance.manifest.get("expected_input_sha256")
    if type(expected) is str and _valid_lower_sha256(expected):
        if input_sha256 is None:
            blockers.append("expected_input_sha256_unverified")
        elif expected != input_sha256:
            blockers.append("expected_input_sha256_mismatch")

    deduped_blockers = _dedupe(blockers)
    return _ManifestValidation(
        supplied=provenance.supplied,
        found=provenance.found,
        parsed=provenance.parsed,
        valid=not deduped_blockers,
        manifest=provenance.manifest,
        blockers=deduped_blockers,
        manifest_sha256=provenance.manifest_sha256,
        normalized_input_csv=provenance.normalized_input_csv,
    )


def _validate_adjusted_bars_csv(
    config: EtfSmaAdjustedCloseEvidenceGateConfig,
) -> _DataValidation:
    path = config.adjusted_bars_csv
    empty = _empty_data_validation()
    if path is None:
        return empty
    if not path.is_file():
        return _replace_data_validation(
            empty,
            supplied=True,
            found=False,
            blockers=("adjusted_bars_csv_not_found",),
        )

    input_sha256 = _sha256_file(path)
    blockers: list[str] = []
    columns: tuple[str, ...] = ()
    schema = "unread"
    source_row_count = 0
    usable_bar_count = 0
    input_sorted_by_date: bool | None = True
    duplicate_dates = False
    malformed_rows = False
    missing_or_invalid_close = False
    missing_or_invalid_adjusted_close = False
    non_positive_close = False
    non_positive_adjusted_close = False
    missing_or_invalid_volume = False
    non_spy_row_count = 0
    previous_date: date | None = None
    seen_dates: set[date] = set()

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = tuple(reader.fieldnames or ())
            schema, schema_blockers = _strict_adjusted_close_schema(columns)
            blockers.extend(schema_blockers)
            symbol_source = (
                "symbol_column"
                if columns == _STRICT_CSV_COLUMNS_WITH_SYMBOL
                else "manifest_symbol"
            )
            if schema_blockers:
                return _replace_data_validation(
                    empty,
                    supplied=True,
                    found=True,
                    blockers=_dedupe(blockers),
                    input_sha256=input_sha256,
                    schema=schema,
                    columns=columns,
                    symbol_source=symbol_source,
                    input_sorted_by_date=input_sorted_by_date,
                )

            for row_number, row in enumerate(reader, start=2):
                source_row_count += 1
                if None in row:
                    malformed_rows = True
                    blockers.append("malformed_csv_row")
                    continue

                if "symbol" in columns:
                    try:
                        row_symbol = _required_string(
                            row["symbol"],
                            f"row {row_number} symbol",
                        )
                    except ValidationError:
                        malformed_rows = True
                        blockers.append("malformed_symbol")
                        continue
                    if row_symbol != _DEFAULT_SYMBOL:
                        non_spy_row_count += 1
                        blockers.append("non_spy_rows_present")
                        continue

                try:
                    parsed_date = _parse_date(
                        _cell(row, "date"),
                        f"row {row_number} date",
                    )
                    _parse_positive_decimal(
                        _cell(row, "close"),
                        f"row {row_number} close",
                    )
                    _parse_positive_decimal(
                        _cell(row, "adjusted_close"),
                        f"row {row_number} adjusted_close",
                    )
                    _parse_non_negative_decimal(
                        _cell(row, "volume"),
                        f"row {row_number} volume",
                    )
                except ValidationError as exc:
                    malformed_rows = True
                    reason = _csv_validation_reason(str(exc))
                    blockers.append(reason)
                    missing_or_invalid_close = (
                        missing_or_invalid_close
                        or reason == "missing_or_invalid_close"
                    )
                    missing_or_invalid_adjusted_close = (
                        missing_or_invalid_adjusted_close
                        or reason == "missing_or_invalid_adjusted_close"
                    )
                    non_positive_close = non_positive_close or reason == "non_positive_close"
                    non_positive_adjusted_close = (
                        non_positive_adjusted_close
                        or reason == "non_positive_adjusted_close"
                    )
                    missing_or_invalid_volume = (
                        missing_or_invalid_volume
                        or reason == "missing_or_invalid_volume"
                    )
                    continue

                if parsed_date in seen_dates:
                    duplicate_dates = True
                    blockers.append("duplicate_dates")
                if previous_date is not None and parsed_date <= previous_date:
                    input_sorted_by_date = False
                    blockers.append("date_order_not_ascending")
                previous_date = parsed_date
                seen_dates.add(parsed_date)
                usable_bar_count += 1
    except OSError:
        return _replace_data_validation(
            empty,
            supplied=True,
            found=True,
            blockers=("adjusted_bars_csv_unreadable",),
            input_sha256=input_sha256,
        )

    if source_row_count == 0:
        blockers.append("adjusted_bars_csv_no_rows")

    return _DataValidation(
        supplied=True,
        found=True,
        valid=not blockers,
        blockers=_dedupe(blockers),
        input_sha256=input_sha256,
        schema=schema,
        columns=columns,
        source_row_count=source_row_count,
        usable_bar_count=usable_bar_count,
        symbol_source=symbol_source,
        input_sorted_by_date=input_sorted_by_date,
        duplicate_dates=duplicate_dates,
        malformed_rows=malformed_rows,
        missing_or_invalid_close=missing_or_invalid_close,
        missing_or_invalid_adjusted_close=missing_or_invalid_adjusted_close,
        non_positive_close=non_positive_close,
        non_positive_adjusted_close=non_positive_adjusted_close,
        missing_or_invalid_volume=missing_or_invalid_volume,
        non_spy_row_count=non_spy_row_count,
    )


def _strict_adjusted_close_schema(
    columns: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    if columns == _STRICT_CSV_COLUMNS_WITH_MANIFEST_SYMBOL:
        return "strict_adjusted_close_csv_manifest_symbol", ()
    if columns == _STRICT_CSV_COLUMNS_WITH_SYMBOL:
        return "strict_adjusted_close_csv_symbol_column", ()
    return "non_strict_or_ambiguous_adjusted_close_csv", (
        "adjusted_bars_csv_schema_non_strict_or_ambiguous",
    )


def _gate_state(
    *,
    prior_blockers: tuple[str, ...],
    missing_adjusted_input: bool,
    operator_input_blocked: bool,
) -> str:
    if prior_blockers:
        return _INVALID_PRIOR_STATE
    if missing_adjusted_input:
        return _MISSING_INPUT_STATE
    if operator_input_blocked:
        return _INVALID_OPERATOR_INPUT_STATE
    return _READY_STATE


def _prior_evidence_rollup_state(artifact: _ArtifactRead) -> str:
    if not artifact.found:
        return "missing"
    if not artifact.parsed or artifact.latest_record is None:
        return f"invalid:{artifact.error}"
    return _text(artifact.latest_record.get("rollup_state"))


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


def _read_json_object(path: Path, field_name: str) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{field_name} must be a JSON object.") from exc
    except OSError as exc:
        raise ValidationError(f"{field_name} could not be read.") from exc
    if type(value) is not dict:
        raise ValidationError(f"{field_name} must be a JSON object.")
    return dict(value)


def _empty_manifest_validation() -> _ManifestValidation:
    return _ManifestValidation(
        supplied=False,
        found=False,
        parsed=False,
        valid=False,
        manifest={},
        blockers=(),
        manifest_sha256=None,
        normalized_input_csv=None,
    )


def _empty_data_validation() -> _DataValidation:
    return _DataValidation(
        supplied=False,
        found=False,
        valid=False,
        blockers=(),
        input_sha256=None,
        schema="unread",
        columns=(),
        source_row_count=0,
        usable_bar_count=0,
        symbol_source="unknown",
        input_sorted_by_date=None,
        duplicate_dates=False,
        malformed_rows=False,
        missing_or_invalid_close=False,
        missing_or_invalid_adjusted_close=False,
        non_positive_close=False,
        non_positive_adjusted_close=False,
        missing_or_invalid_volume=False,
        non_spy_row_count=0,
    )


def _replace_data_validation(
    value: _DataValidation,
    *,
    supplied: bool | None = None,
    found: bool | None = None,
    blockers: Iterable[str] | None = None,
    input_sha256: str | None = None,
    schema: str | None = None,
    columns: tuple[str, ...] | None = None,
    symbol_source: str | None = None,
    input_sorted_by_date: bool | None = None,
) -> _DataValidation:
    deduped_blockers = (
        value.blockers if blockers is None else _dedupe(tuple(blockers))
    )
    return _DataValidation(
        supplied=value.supplied if supplied is None else supplied,
        found=value.found if found is None else found,
        valid=False,
        blockers=deduped_blockers,
        input_sha256=value.input_sha256 if input_sha256 is None else input_sha256,
        schema=value.schema if schema is None else schema,
        columns=value.columns if columns is None else columns,
        source_row_count=value.source_row_count,
        usable_bar_count=value.usable_bar_count,
        symbol_source=value.symbol_source if symbol_source is None else symbol_source,
        input_sorted_by_date=(
            value.input_sorted_by_date
            if input_sorted_by_date is None
            else input_sorted_by_date
        ),
        duplicate_dates=value.duplicate_dates,
        malformed_rows=value.malformed_rows,
        missing_or_invalid_close=value.missing_or_invalid_close,
        missing_or_invalid_adjusted_close=value.missing_or_invalid_adjusted_close,
        non_positive_close=value.non_positive_close,
        non_positive_adjusted_close=value.non_positive_adjusted_close,
        missing_or_invalid_volume=value.missing_or_invalid_volume,
        non_spy_row_count=value.non_spy_row_count,
    )


def _config(
    value: EtfSmaAdjustedCloseEvidenceGateConfig,
) -> EtfSmaAdjustedCloseEvidenceGateConfig:
    if not isinstance(value, EtfSmaAdjustedCloseEvidenceGateConfig):
        raise ValidationError(
            "config must be an EtfSmaAdjustedCloseEvidenceGateConfig."
        )
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _spy_symbol(value: object) -> str:
    symbol = symbol_value(value)
    if symbol != _DEFAULT_SYMBOL:
        raise ValidationError("M414 ETF/SMA adjusted-close evidence gate supports SPY only.")
    return symbol


def _jsonl_path(value: Path | str, field_name: str) -> Path:
    path = _path_value(value, field_name)
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must point to a .jsonl file.")
    return path


def _optional_path(
    value: object,
    field_name: str,
    *,
    required_suffix: str,
) -> Path | None:
    if value is None:
        return None
    if type(value) is str and value.strip() == "":
        return None
    path = _path_value(value, field_name)
    if path.suffix.lower() != required_suffix:
        raise ValidationError(f"{field_name} must point to a {required_suffix} file.")
    return path


def _path_value(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif type(value) is str:
        if not value.strip():
            raise ValidationError(f"{field_name} is required.")
        if "://" in value:
            raise ValidationError(f"{field_name} must be a local path.")
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a path.")
    return path


def _output_path(value: Path | str) -> Path:
    path = _jsonl_path(value, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _generated_at_text(value: datetime | str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("generated_at must be timezone-aware.")
        return value.isoformat()
    if type(value) is str:
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


def _cell(row: Mapping[str, str], column: str) -> str:
    value = row[column]
    if type(value) is not str:
        raise ValidationError(f"{column} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{column} must be a non-empty string.")
    return text


def _parse_date(value: str, field_name: str) -> date:
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date.") from exc
    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date.")
    return parsed


def _parse_positive_decimal(value: str, field_name: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a Decimal string.") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return parsed


def _parse_non_negative_decimal(value: str, field_name: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a Decimal string.") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return parsed


def _csv_validation_reason(message: str) -> str:
    lowered = message.lower()
    if "adjusted_close must be greater than zero" in lowered:
        return "non_positive_adjusted_close"
    if "adjusted_close must be" in lowered:
        return "missing_or_invalid_adjusted_close"
    if "close must be greater than zero" in lowered:
        return "non_positive_close"
    if "close must be" in lowered:
        return "missing_or_invalid_close"
    if "volume must be" in lowered:
        return "missing_or_invalid_volume"
    if "date must be" in lowered:
        return "malformed_date"
    return f"malformed_csv:{_blocker_text(message)}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_compare_path(path: Path, *, base: Path | None = None) -> Path:
    candidate = path
    if not candidate.is_absolute() and base is not None:
        candidate = base / candidate
    return candidate.resolve(strict=False)


def _valid_lower_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _valid_iso_date_or_timestamp(value: str) -> bool:
    text = value.strip()
    try:
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            date.fromisoformat(text)
        else:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _provenance_text_has_forbidden_term(value: object) -> bool:
    if type(value) is str:
        return any(term in _FORBIDDEN_PROVENANCE_TERMS for term in _text_terms(value))
    return False


def _text_terms(value: str) -> tuple[str, ...]:
    normalized = "".join(
        character if character.isalnum() else "_" for character in value.lower()
    )
    return tuple(term for term in normalized.split("_") if term)


def _token(value: str) -> str:
    return "_".join(value.strip().lower().split())


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


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


def _blocker_text(value: str) -> str:
    return "_".join(value.lower().replace(".", "").replace(",", "").split())


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
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
