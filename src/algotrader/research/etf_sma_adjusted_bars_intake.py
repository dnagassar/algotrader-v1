"""Offline intake for operator-supplied SPY adjusted/total-return bars.

This module performs explicit local file I/O only. It does not load runtime
profiles, read credentials, import broker adapters, fetch market data, or
expose any broker mutation path.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_ADJUSTED_BARS_INTAKE_LABELS",
    "ETF_SMA_ADJUSTED_BARS_INTAKE_REQUIRED_COLUMNS",
    "ETF_SMA_ADJUSTED_BARS_INTAKE_ACCEPTED_BASIS_COLUMNS",
    "EtfSmaAdjustedBarsIntakeConfig",
    "EtfSmaAdjustedBarsIntakeWriteResult",
    "build_etf_sma_adjusted_bars_intake",
    "render_etf_sma_adjusted_bars_intake_json",
    "render_etf_sma_adjusted_bars_intake_text",
    "write_etf_sma_adjusted_bars_intake_jsonl",
]


ETF_SMA_ADJUSTED_BARS_INTAKE_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)
ETF_SMA_ADJUSTED_BARS_INTAKE_REQUIRED_COLUMNS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
)
ETF_SMA_ADJUSTED_BARS_INTAKE_ACCEPTED_BASIS_COLUMNS = (
    "adjusted_close",
    "total_return_close",
    "total_return_compatible_close",
)

_MILESTONE = "M419"
_RECORD_TYPE = "etf_sma_adjusted_bars_intake"
_COMMAND = "etf-sma-adjusted-bars-intake"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_RUN_ID = "m419_spy_adjusted_bars_intake"
_DEFAULT_CANONICAL_FILENAME = "m419_spy_adjusted_bars_canonical.csv"
_STATUS_MISSING = "blocked_missing_operator_supplied_adjusted_bars"
_STATUS_INVALID = "blocked_invalid_adjusted_bars"
_STATUS_READY = "ready_for_m418_adjusted_basis_rerun"
_CANONICAL_COLUMNS = (
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)
_FALSE_SAFETY_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "broker_network_access",
    "credential_access",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "market_data_fetch_performed",
    "returns_fabricated",
)


@dataclass(frozen=True, slots=True)
class EtfSmaAdjustedBarsIntakeConfig:
    """Explicit local inputs for one M419 adjusted-bars intake."""

    run_log: Path | str
    run_id: str = _DEFAULT_RUN_ID
    input_csv: Path | str | None = None
    canonical_csv: Path | str | None = None
    symbol: str = _DEFAULT_SYMBOL
    operator_attested_provenance: bool = False
    source_name: str = ""
    source_notes: str = ""
    attested_by: str = ""
    attested_at: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        run_log = _jsonl_path(self.run_log, "run_log")
        object.__setattr__(self, "run_log", run_log)
        object.__setattr__(self, "input_csv", _optional_csv_path(self.input_csv))
        object.__setattr__(
            self,
            "canonical_csv",
            _canonical_csv_path(self.canonical_csv, run_log=run_log),
        )
        object.__setattr__(
            self,
            "operator_attested_provenance",
            _bool_value(
                self.operator_attested_provenance,
                "operator_attested_provenance",
            ),
        )
        object.__setattr__(self, "source_name", _optional_string(self.source_name))
        object.__setattr__(self, "source_notes", _optional_string(self.source_notes))
        object.__setattr__(self, "attested_by", _optional_string(self.attested_by))
        object.__setattr__(self, "attested_at", _optional_string(self.attested_at))


@dataclass(frozen=True, slots=True)
class EtfSmaAdjustedBarsIntakeWriteResult:
    """Local JSONL write metadata for a single M419 intake report."""

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
    broker_network_access: bool
    credential_access: bool
    paper_submit_authorized: bool
    broker_mutation_authorized: bool
    live_authorized: bool
    market_data_fetch_performed: bool
    returns_fabricated: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _jsonl_path(self.output_path, "output_path"))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if self.newline_terminated is not True:
            raise ValidationError("newline_terminated must be true.")
        for field_name in _FALSE_SAFETY_FIELDS:
            if getattr(self, field_name) is not False:
                raise ValidationError(f"{field_name} must be false.")

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
            "broker_network_access": self.broker_network_access,
            "credential_access": self.credential_access,
            "paper_submit_authorized": self.paper_submit_authorized,
            "broker_mutation_authorized": self.broker_mutation_authorized,
            "live_authorized": self.live_authorized,
            "market_data_fetch_performed": self.market_data_fetch_performed,
            "returns_fabricated": self.returns_fabricated,
        }


@dataclass(frozen=True, slots=True)
class _CanonicalRow:
    symbol: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int


@dataclass(frozen=True, slots=True)
class _CsvValidation:
    found: bool
    input_sha256: str
    observed_columns: tuple[str, ...]
    basis_column: str
    basis_label: str
    rows: tuple[_CanonicalRow, ...]
    source_row_count: int
    duplicate_dates: bool
    input_sorted_by_date: bool
    blockers: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.blockers


@dataclass(frozen=True, slots=True)
class _ProvenanceValidation:
    valid: bool
    operator_attested: bool
    source_name: str
    source_notes: str
    attested_by: str
    attested_at: str
    blockers: tuple[str, ...]


def build_etf_sma_adjusted_bars_intake(
    config: EtfSmaAdjustedBarsIntakeConfig,
) -> dict[str, object]:
    """Validate and canonicalize one operator-supplied adjusted-bars CSV."""

    checked_config = _config(config)
    input_csv = checked_config.input_csv
    if input_csv is None or not input_csv.is_file():
        return _base_payload(
            checked_config,
            intake_status=_STATUS_MISSING,
            blockers=("missing_or_unreadable_operator_supplied_adjusted_bars_csv",),
            rejected_basis_reason="operator_supplied_adjusted_bars_csv_missing",
        )

    csv_validation = _validate_csv(checked_config)
    if not csv_validation.found:
        return _base_payload(
            checked_config,
            intake_status=_STATUS_MISSING,
            blockers=("missing_or_unreadable_operator_supplied_adjusted_bars_csv",),
            input_sha256=csv_validation.input_sha256,
            observed_columns=csv_validation.observed_columns,
            rejected_basis_reason="operator_supplied_adjusted_bars_csv_unreadable",
        )
    provenance = _validate_provenance(checked_config)
    blockers = _dedupe((*csv_validation.blockers, *provenance.blockers))
    if blockers:
        return _payload_from_validation(
            checked_config,
            csv_validation,
            provenance,
            intake_status=_STATUS_INVALID,
            blockers=blockers,
            rejected_basis_reason=_rejected_basis_reason(blockers),
            canonical_sha256="",
            canonical_csv_written=False,
        )

    _write_canonical_csv(checked_config.canonical_csv, csv_validation.rows)
    canonical_sha256 = _sha256_file(checked_config.canonical_csv)
    return _payload_from_validation(
        checked_config,
        csv_validation,
        provenance,
        intake_status=_STATUS_READY,
        blockers=(),
        accepted_basis_reason=(
            "operator_supplied_basis_distinct_from_raw_close_and_canonicalized"
        ),
        canonical_sha256=canonical_sha256,
        canonical_csv_written=True,
    )


def render_etf_sma_adjusted_bars_intake_json(payload: Mapping[str, object]) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_adjusted_bars_intake_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-facing M419 intake summary."""

    return "\n".join(
        (
            "SPY adjusted bars intake",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"input_csv: {payload.get('input_csv', '')}",
            f"canonical_csv: {payload.get('canonical_csv', '')}",
            f"intake_status: {payload.get('intake_status', '')}",
            f"basis_label: {payload.get('basis_label', '')}",
            f"source_row_count: {payload.get('source_row_count', '')}",
            f"accepted_row_count: {payload.get('accepted_row_count', '')}",
            f"date_range_start: {payload.get('date_range_start', '')}",
            f"date_range_end: {payload.get('date_range_end', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
        )
    )


def write_etf_sma_adjusted_bars_intake_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaAdjustedBarsIntakeWriteResult:
    """Write exactly one deterministic M419 JSONL report."""

    path = _jsonl_path(output_path, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_adjusted_bars_intake_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(line)
    return EtfSmaAdjustedBarsIntakeWriteResult(
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
        broker_network_access=False,
        credential_access=False,
        paper_submit_authorized=False,
        broker_mutation_authorized=False,
        live_authorized=False,
        market_data_fetch_performed=False,
        returns_fabricated=False,
    )


def _validate_csv(config: EtfSmaAdjustedBarsIntakeConfig) -> _CsvValidation:
    input_csv = config.input_csv
    if input_csv is None:
        raise ValidationError("input_csv is required for CSV validation.")

    try:
        input_sha256 = _sha256_file(input_csv)
    except OSError:
        return _CsvValidation(
            found=False,
            input_sha256="",
            observed_columns=(),
            basis_column="",
            basis_label="",
            rows=(),
            source_row_count=0,
            duplicate_dates=False,
            input_sorted_by_date=True,
            blockers=("input_csv_unreadable",),
        )
    blockers: list[str] = []
    rows: list[_CanonicalRow] = []
    observed_columns: tuple[str, ...] = ()
    basis_column = ""
    basis_label = ""
    source_row_count = 0
    duplicate_dates = False
    input_sorted_by_date = True
    previous_date: date | None = None
    seen_dates: set[date] = set()
    all_basis_values_mirror_close = True

    try:
        with input_csv.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            observed_columns = tuple(reader.fieldnames or ())
            schema_blockers = _schema_blockers(observed_columns)
            blockers.extend(schema_blockers)
            basis_column = _basis_column(observed_columns)
            basis_label = _basis_label(basis_column)
            if schema_blockers:
                return _CsvValidation(
                    found=True,
                    input_sha256=input_sha256,
                    observed_columns=observed_columns,
                    basis_column=basis_column,
                    basis_label=basis_label,
                    rows=(),
                    source_row_count=0,
                    duplicate_dates=False,
                    input_sorted_by_date=True,
                    blockers=_dedupe(blockers),
                )

            for row_number, row in enumerate(reader, start=2):
                source_row_count += 1
                if None in row:
                    blockers.append("malformed_csv_row")
                    continue

                parsed = _canonical_row_from_input(
                    row,
                    row_number=row_number,
                    command_symbol=config.symbol,
                    basis_column=basis_column,
                    blockers=blockers,
                )
                if parsed is None:
                    continue

                if parsed.symbol != _DEFAULT_SYMBOL or config.symbol != _DEFAULT_SYMBOL:
                    blockers.append("symbol_scope_must_be_spy")
                if parsed.date in seen_dates:
                    duplicate_dates = True
                    blockers.append("duplicate_dates")
                if previous_date is not None and parsed.date <= previous_date:
                    input_sorted_by_date = False
                    blockers.append("date_order_not_ascending")
                previous_date = parsed.date
                seen_dates.add(parsed.date)
                if parsed.adjusted_close != parsed.close:
                    all_basis_values_mirror_close = False
                rows.append(parsed)
    except OSError:
        return _CsvValidation(
            found=False,
            input_sha256=input_sha256,
            observed_columns=observed_columns,
            basis_column=basis_column,
            basis_label=basis_label,
            rows=(),
            source_row_count=source_row_count,
            duplicate_dates=duplicate_dates,
            input_sorted_by_date=input_sorted_by_date,
            blockers=("input_csv_unreadable",),
        )

    if source_row_count == 0:
        blockers.append("no_daily_rows")
    if rows and all_basis_values_mirror_close:
        blockers.append("basis_values_mirror_close")

    return _CsvValidation(
        found=True,
        input_sha256=input_sha256,
        observed_columns=observed_columns,
        basis_column=basis_column,
        basis_label=basis_label,
        rows=tuple(rows),
        source_row_count=source_row_count,
        duplicate_dates=duplicate_dates,
        input_sorted_by_date=input_sorted_by_date,
        blockers=_dedupe(blockers),
    )


def _schema_blockers(columns: tuple[str, ...]) -> tuple[str, ...]:
    blockers: list[str] = []
    if not columns:
        return ("missing_header_row",)
    if len(set(columns)) != len(columns):
        blockers.append("duplicate_columns")
    missing_required = tuple(
        column for column in ETF_SMA_ADJUSTED_BARS_INTAKE_REQUIRED_COLUMNS if column not in columns
    )
    if missing_required:
        blockers.append(f"missing_required_columns:{','.join(missing_required)}")
    if not _basis_column(columns):
        blockers.append("missing_adjusted_or_total_return_field")
    return tuple(blockers)


def _canonical_row_from_input(
    row: Mapping[str, str],
    *,
    row_number: int,
    command_symbol: str,
    basis_column: str,
    blockers: list[str],
) -> _CanonicalRow | None:
    try:
        parsed_symbol = (
            symbol_value(_required_cell(row, "symbol", row_number))
            if "symbol" in row
            else command_symbol
        )
        parsed_date = _parse_date(_required_cell(row, "date", row_number), row_number)
        parsed_open = _parse_positive_decimal(
            _required_cell(row, "open", row_number),
            row_number,
            "open",
        )
        parsed_high = _parse_positive_decimal(
            _required_cell(row, "high", row_number),
            row_number,
            "high",
        )
        parsed_low = _parse_positive_decimal(
            _required_cell(row, "low", row_number),
            row_number,
            "low",
        )
        parsed_close = _parse_positive_decimal(
            _required_cell(row, "close", row_number),
            row_number,
            "close",
        )
        parsed_basis = _parse_positive_decimal(
            _required_cell(row, basis_column, row_number),
            row_number,
            basis_column,
        )
        parsed_volume = _parse_non_negative_int(
            _required_cell(row, "volume", row_number),
            row_number,
            "volume",
        )
    except ValidationError as exc:
        blockers.append(_row_blocker(str(exc)))
        return None

    return _CanonicalRow(
        symbol=parsed_symbol,
        date=parsed_date,
        open=parsed_open,
        high=parsed_high,
        low=parsed_low,
        close=parsed_close,
        adjusted_close=parsed_basis,
        volume=parsed_volume,
    )


def _validate_provenance(config: EtfSmaAdjustedBarsIntakeConfig) -> _ProvenanceValidation:
    provenance_fields_supplied = bool(config.source_name and config.source_notes)
    valid = config.operator_attested_provenance or provenance_fields_supplied
    blockers = () if valid else ("missing_provenance_or_operator_attestation",)
    return _ProvenanceValidation(
        valid=valid,
        operator_attested=config.operator_attested_provenance,
        source_name=config.source_name,
        source_notes=config.source_notes,
        attested_by=config.attested_by,
        attested_at=config.attested_at,
        blockers=blockers,
    )


def _payload_from_validation(
    config: EtfSmaAdjustedBarsIntakeConfig,
    csv_validation: _CsvValidation,
    provenance: _ProvenanceValidation,
    *,
    intake_status: str,
    blockers: tuple[str, ...],
    canonical_sha256: str,
    canonical_csv_written: bool,
    accepted_basis_reason: str = "",
    rejected_basis_reason: str = "",
) -> dict[str, object]:
    rows = csv_validation.rows
    return _base_payload(
        config,
        intake_status=intake_status,
        blockers=blockers,
        input_sha256=csv_validation.input_sha256,
        canonical_sha256=canonical_sha256,
        observed_columns=csv_validation.observed_columns,
        basis_column=csv_validation.basis_column,
        basis_label=csv_validation.basis_label,
        source_row_count=csv_validation.source_row_count,
        accepted_row_count=len(rows),
        date_range_start=_first_date(rows),
        date_range_end=_last_date(rows),
        duplicate_dates=csv_validation.duplicate_dates,
        input_sorted_by_date=csv_validation.input_sorted_by_date,
        provenance=provenance,
        accepted_basis_reason=accepted_basis_reason,
        rejected_basis_reason=rejected_basis_reason,
        canonical_csv_written=canonical_csv_written,
    )


def _base_payload(
    config: EtfSmaAdjustedBarsIntakeConfig,
    *,
    intake_status: str,
    blockers: tuple[str, ...],
    input_sha256: str = "",
    canonical_sha256: str = "",
    observed_columns: tuple[str, ...] = (),
    basis_column: str = "",
    basis_label: str = "",
    source_row_count: int = 0,
    accepted_row_count: int = 0,
    date_range_start: str = "",
    date_range_end: str = "",
    duplicate_dates: bool = False,
    input_sorted_by_date: bool | None = None,
    provenance: _ProvenanceValidation | None = None,
    accepted_basis_reason: str = "",
    rejected_basis_reason: str = "",
    canonical_csv_written: bool = False,
) -> dict[str, object]:
    provenance_summary = _provenance_summary(provenance, config)
    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": config.run_id,
        "run_log": str(config.run_log),
        "symbol": config.symbol,
        "strategy": "spy_etf_sma_50_200_daily_long_only",
        "labels": list(ETF_SMA_ADJUSTED_BARS_INTAKE_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
        "trade_recommendation": "none",
        "input_csv": "" if config.input_csv is None else str(config.input_csv),
        "source_filename": "" if config.input_csv is None else config.input_csv.name,
        "canonical_csv": str(config.canonical_csv),
        "canonical_csv_written": canonical_csv_written,
        "required_columns": list(ETF_SMA_ADJUSTED_BARS_INTAKE_REQUIRED_COLUMNS),
        "optional_symbol_column": "symbol",
        "accepted_adjusted_or_total_return_fields": list(
            ETF_SMA_ADJUSTED_BARS_INTAKE_ACCEPTED_BASIS_COLUMNS
        ),
        "canonical_columns": list(_CANONICAL_COLUMNS),
        "observed_columns": list(observed_columns),
        "intake_status": intake_status,
        "validation_status": (
            "accepted" if intake_status == _STATUS_READY else "blocked"
        ),
        "basis_column": basis_column,
        "basis_label": basis_label,
        "accepted_basis_reason": accepted_basis_reason,
        "rejected_basis_reason": rejected_basis_reason,
        "input_sha256": input_sha256,
        "canonical_sha256": canonical_sha256,
        "fingerprint": input_sha256,
        "source_row_count": source_row_count,
        "accepted_row_count": accepted_row_count,
        "row_count": accepted_row_count,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "duplicate_dates": duplicate_dates,
        "input_sorted_by_date": input_sorted_by_date,
        "provenance": provenance_summary,
        "no_fabricated_evidence": True,
        "preview_only_handoff": {
            "m418_command": "etf-sma-adjusted-basis-validation",
            "canonical_csv": str(config.canonical_csv),
            "ready_for_m418": intake_status == _STATUS_READY,
            "run_m418_automatically": False,
        },
        "blockers": list(blockers),
        "next_action": _next_action(intake_status),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_network_access": False,
        "credential_access": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "market_data_fetch_performed": False,
        "returns_fabricated": False,
        "forbidden_actions": [
            "broker_mutation_from_m419_intake",
            "live_trading",
            "paper_or_live_submit_cancel_replace_close_liquidate",
            "network_market_data_fetch",
            "credential_access",
        ],
    }


def _write_canonical_csv(path: Path, rows: tuple[_CanonicalRow, ...]) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(_CANONICAL_COLUMNS)
        for row in rows:
            writer.writerow(
                (
                    row.symbol,
                    row.date.isoformat(),
                    _decimal_text(row.open),
                    _decimal_text(row.high),
                    _decimal_text(row.low),
                    _decimal_text(row.close),
                    _decimal_text(row.adjusted_close),
                    str(row.volume),
                )
            )


def _basis_column(columns: tuple[str, ...]) -> str:
    for column in ETF_SMA_ADJUSTED_BARS_INTAKE_ACCEPTED_BASIS_COLUMNS:
        if column in columns:
            return column
    return ""


def _basis_label(column: str) -> str:
    if column == "adjusted_close":
        return "adjusted_close_price_return"
    if column:
        return "total_return_compatible_price_return"
    return ""


def _provenance_summary(
    provenance: _ProvenanceValidation | None,
    config: EtfSmaAdjustedBarsIntakeConfig,
) -> dict[str, object]:
    if provenance is None:
        return {
            "valid": False,
            "operator_attested": config.operator_attested_provenance,
            "source_name": config.source_name,
            "source_notes": config.source_notes,
            "attested_by": config.attested_by,
            "attested_at": config.attested_at,
            "blockers": [],
        }
    return {
        "valid": provenance.valid,
        "operator_attested": provenance.operator_attested,
        "source_name": provenance.source_name,
        "source_notes": provenance.source_notes,
        "attested_by": provenance.attested_by,
        "attested_at": provenance.attested_at,
        "blockers": list(provenance.blockers),
    }


def _rejected_basis_reason(blockers: tuple[str, ...]) -> str:
    if "basis_values_mirror_close" in blockers:
        return "adjusted_or_total_return_basis_mirrors_raw_close"
    if "missing_adjusted_or_total_return_field" in blockers:
        return "missing_adjusted_or_total_return_basis_field"
    if "missing_provenance_or_operator_attestation" in blockers:
        return "missing_provenance_or_operator_attestation"
    return "operator_supplied_adjusted_bars_failed_validation"


def _next_action(intake_status: str) -> str:
    if intake_status == _STATUS_READY:
        return "operator_preview_m418_adjusted_basis_rerun_with_canonical_csv"
    return "operator_supply_valid_adjusted_or_total_return_spy_daily_bars_csv"


def _first_date(rows: tuple[_CanonicalRow, ...]) -> str:
    if not rows:
        return ""
    return rows[0].date.isoformat()


def _last_date(rows: tuple[_CanonicalRow, ...]) -> str:
    if not rows:
        return ""
    return rows[-1].date.isoformat()


def _required_cell(row: Mapping[str, str], column: str, row_number: int) -> str:
    value = row[column]
    if type(value) is not str:
        raise ValidationError(f"row {row_number} {column} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"row {row_number} {column} is required.")
    return text


def _parse_date(value: str, row_number: int) -> date:
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValidationError(f"row {row_number} date must be an ISO YYYY-MM-DD date.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"row {row_number} date must be an ISO YYYY-MM-DD date."
        ) from exc
    if parsed.isoformat() != value:
        raise ValidationError(f"row {row_number} date must be an ISO YYYY-MM-DD date.")
    return parsed


def _parse_positive_decimal(value: str, row_number: int, column: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(
            f"row {row_number} {column} must be a Decimal string."
        ) from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValidationError(f"row {row_number} {column} must be greater than zero.")
    return parsed


def _parse_non_negative_int(value: str, row_number: int, column: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValidationError(
            f"row {row_number} {column} must be an integer string."
        ) from exc
    if str(parsed) != value or parsed < 0:
        raise ValidationError(f"row {row_number} {column} must be zero or greater.")
    return parsed


def _row_blocker(message: str) -> str:
    lowered = message.lower()
    if "adjusted_close must be greater than zero" in lowered:
        return "nonpositive_adjusted_close"
    if "total_return_close must be greater than zero" in lowered:
        return "nonpositive_adjusted_close"
    if "total_return_compatible_close must be greater than zero" in lowered:
        return "nonpositive_adjusted_close"
    if "close must be greater than zero" in lowered:
        return "nonpositive_close"
    if "date must be" in lowered:
        return "invalid_date"
    if "adjusted_close" in lowered or "total_return" in lowered:
        return "missing_or_invalid_adjusted_close"
    if "close" in lowered:
        return "missing_or_invalid_close"
    return f"invalid_row:{_blocker_text(message)}"


def _jsonl_path(value: object, field_name: str) -> Path:
    path = _path_value(value, field_name)
    if isinstance(value, str) and "://" in value:
        raise ValidationError(f"{field_name} must be a local path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must point to a .jsonl file.")
    return path


def _optional_csv_path(value: object) -> Path | None:
    if value is None:
        return None
    if type(value) is str and not value.strip():
        return None
    path = _path_value(value, "input_csv")
    if type(value) is str and "://" in value:
        raise ValidationError("input_csv must be a local CSV path.")
    if path.suffix.lower() != ".csv":
        raise ValidationError("input_csv must reference a CSV file.")
    return path


def _canonical_csv_path(value: object, *, run_log: Path) -> Path:
    if value is None or (type(value) is str and not value.strip()):
        path = run_log.parent / _DEFAULT_CANONICAL_FILENAME
    else:
        path = _path_value(value, "canonical_csv")
    if type(value) is str and "://" in value:
        raise ValidationError("canonical_csv must be a local CSV path.")
    if path.suffix.lower() != ".csv":
        raise ValidationError("canonical_csv must reference a CSV file.")
    if path.exists() and path.is_dir():
        raise ValidationError("canonical_csv must not be a directory.")
    return path


def _path_value(value: object, field_name: str) -> Path:
    if type(value) is str:
        if not value.strip():
            raise ValidationError(f"{field_name} is required.")
        return Path(value)
    if isinstance(value, Path):
        return value
    raise ValidationError(f"{field_name} must be a path.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _optional_string(value: object) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValidationError("optional string fields must be strings.")
    return value.strip()


def _bool_value(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _config(value: object) -> EtfSmaAdjustedBarsIntakeConfig:
    if type(value) is not EtfSmaAdjustedBarsIntakeConfig:
        raise ValidationError("config must be an EtfSmaAdjustedBarsIntakeConfig.")
    return value


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"


def _blocker_text(value: str) -> str:
    return "_".join(value.lower().replace(".", "").replace(",", "").split())
