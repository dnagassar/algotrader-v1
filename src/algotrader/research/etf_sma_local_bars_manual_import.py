"""Manual local SPY daily-bars import with explicit provenance attestation."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_local_bars_backtest_refresh import (
    EtfSmaLocalBarsBacktestRefreshConfig,
    build_etf_sma_local_bars_backtest_refresh,
    write_etf_sma_local_bars_backtest_refresh_jsonl,
)
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    LocalDailyBar,
)

__all__ = [
    "ETF_SMA_LOCAL_BARS_MANUAL_IMPORT_LABELS",
    "EtfSmaLocalBarsManualImportConfig",
    "build_etf_sma_local_bars_manual_import",
    "render_etf_sma_local_bars_manual_import_json",
    "render_etf_sma_local_bars_manual_import_text",
    "write_etf_sma_local_bars_manual_import_jsonl",
]


ETF_SMA_LOCAL_BARS_MANUAL_IMPORT_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_RECORD_TYPE = "etf_sma_local_bars_manual_import"
_SCHEMA_VERSION = "1"
_COMMAND = "etf-sma-local-bars-manual-import"
_STRATEGY = "spy_etf_sma_50_200_daily_long_only"
_SYMBOL = "SPY"
_MINIMUM_REQUIRED_USABLE_BARS = 201
_MANUAL_READY = "canonical_local_operator_bars_ready"
_MANUAL_BLOCKED = "blocked_manual_operator_data_missing_or_invalid"
_REFRESHED = "backtest_evidence_refreshed"
_PERFORMANCE_EVALUATED = "post_signal_returns_evaluated"
_PERFORMANCE_INSUFFICIENT_RETURNS = "insufficient_post_signal_returns"
_ZERO_TEXT = "0"
_DEFAULT_STARTING_EQUITY = "25.00"
_SOURCE_REFRESH_RECORD_TYPE = "etf_sma_local_bars_canonicalization"
_SOURCE_REFRESH_COMMAND = "etf-sma-local-bars-canonicalize"
_SOURCE_BACKTEST_RECORD_TYPE = "etf_sma_backtest_stats"
_SOURCE_BACKTEST_COMMAND = "etf-sma-backtest-stats"
_SOURCE_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "submit_authorized",
    "paper_submit_approved",
    "broker_mutation_authorized",
    "live_authorized",
    "credential_access_attempted",
    "network_access_attempted",
)
_PROVENANCE_REQUIRED_FIELDS = (
    "symbol",
    "input_csv",
    "source_description",
    "source_type",
    "operator_attested",
    "attested_by",
    "attested_at",
    "data_vendor_or_origin",
    "acquisition_method",
    "contains_synthetic_data",
    "contains_fixture_data",
    "contains_sample_data",
    "contains_test_data",
    "adjustment_policy",
    "timeframe",
    "expected_schema",
    "notes",
)
_PROVENANCE_FALSE_FLAGS = (
    "contains_synthetic_data",
    "contains_fixture_data",
    "contains_sample_data",
    "contains_test_data",
)
_PROVENANCE_STRING_FIELDS = (
    "symbol",
    "input_csv",
    "source_description",
    "source_type",
    "attested_by",
    "attested_at",
    "data_vendor_or_origin",
    "acquisition_method",
    "adjustment_policy",
    "timeframe",
    "expected_schema",
)
_AMBIGUOUS_TEXT_VALUES = frozenset(
    ("", "ambiguous", "n/a", "na", "none", "null", "tbd", "todo", "unknown")
)
_FORBIDDEN_PROVENANCE_VALUES = frozenset(
    ("demo", "fake", "fixture", "generated", "mock", "sample", "synthetic", "test")
)
_DAILY_TIMEFRAME_VALUES = frozenset(
    ("1_day", "1d", "d", "daily", "daily_bars", "day", "one_day")
)
_COLUMN_ALIASES = {
    "symbol": frozenset(("symbol", "ticker", "ticker_symbol")),
    "date": frozenset(("date", "day", "trading_date")),
    "open": frozenset(("open", "open_price")),
    "high": frozenset(("high", "high_price")),
    "low": frozenset(("low", "low_price")),
    "close": frozenset(("close", "close_price")),
    "adjusted_close": frozenset(
        (
            "adj_close",
            "adjclose",
            "adjusted_close",
            "adjusted_close_price",
            "close_adjusted",
        )
    ),
    "volume": frozenset(("vol", "volume")),
}


@dataclass(frozen=True, slots=True)
class EtfSmaLocalBarsManualImportConfig:
    """Explicit local files for one manual SPY daily-bars import attempt."""

    run_id: str
    source_refresh_log: Path | str
    source_backtest_log: Path | str
    run_log: Path | str
    canonical_output: Path | str
    refresh_run_log: Path | str
    input_csv: Path | str | None = None
    provenance_manifest: Path | str | None = None
    symbol: str = _SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "input_csv",
            _optional_path(self.input_csv, "input_csv", required_suffix=".csv"),
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
            "source_refresh_log",
            _path_value(
                self.source_refresh_log,
                "source_refresh_log",
                required_suffix=".jsonl",
            ),
        )
        object.__setattr__(
            self,
            "source_backtest_log",
            _path_value(
                self.source_backtest_log,
                "source_backtest_log",
                required_suffix=".jsonl",
            ),
        )
        object.__setattr__(
            self,
            "run_log",
            _path_value(self.run_log, "run_log", required_suffix=".jsonl"),
        )
        object.__setattr__(
            self,
            "canonical_output",
            _path_value(
                self.canonical_output,
                "canonical_output",
                required_suffix=".csv",
            ),
        )
        object.__setattr__(
            self,
            "refresh_run_log",
            _path_value(
                self.refresh_run_log,
                "refresh_run_log",
                required_suffix=".jsonl",
            ),
        )


@dataclass(frozen=True, slots=True)
class _ProvenanceValidation:
    supplied: bool
    valid: bool
    manifest: dict[str, object]
    blockers: tuple[str, ...]
    manifest_sha256: str | None
    normalized_input_csv: str | None


@dataclass(frozen=True, slots=True)
class _DataValidation:
    valid: bool
    blockers: tuple[str, ...]
    bars: tuple[LocalDailyBar, ...]
    input_sha256: str | None
    schema: str
    columns: tuple[str, ...]
    column_mapping: dict[str, str]
    source_row_count: int
    usable_bar_count: int
    matching_symbol_row_count: int
    non_spy_row_count: int
    input_sorted_by_date: bool | None
    duplicate_dates: bool
    malformed_rows: bool
    missing_or_invalid_close: bool
    non_positive_close: bool
    symbol_source: str


def build_etf_sma_local_bars_manual_import(
    config: EtfSmaLocalBarsManualImportConfig,
) -> dict[str, object]:
    """Validate local provenance and bars, then refresh evidence when admissible."""

    checked_config = _config(config)
    source_refresh = _source_log_metadata(
        checked_config.source_refresh_log,
        field_name="source_refresh_log",
        expected_record_type=_SOURCE_REFRESH_RECORD_TYPE,
        expected_command=_SOURCE_REFRESH_COMMAND,
    )
    source_backtest = _source_log_metadata(
        checked_config.source_backtest_log,
        field_name="source_backtest_log",
        expected_record_type=_SOURCE_BACKTEST_RECORD_TYPE,
        expected_command=_SOURCE_BACKTEST_COMMAND,
    )
    provenance = _validate_provenance_manifest(checked_config)
    data = _validate_input_csv(checked_config, provenance)

    blockers = _dedupe(
        (
            *tuple(source_refresh["blockers"]),
            *tuple(source_backtest["blockers"]),
            *provenance.blockers,
            *data.blockers,
        )
    )
    if blockers:
        return _payload(
            checked_config,
            source_refresh=source_refresh,
            source_backtest=source_backtest,
            provenance=provenance,
            data=data,
            manual_import_state=_MANUAL_BLOCKED,
            performance_evidence_state=_PERFORMANCE_INSUFFICIENT_RETURNS,
            canonical_csv_written=False,
            refresh_rerun_performed=False,
            refresh_payload=None,
            blockers=blockers,
        )

    _write_canonical_csv(data.bars, checked_config.canonical_output)
    refresh_payload = build_etf_sma_local_bars_backtest_refresh(
        EtfSmaLocalBarsBacktestRefreshConfig(
            run_id=checked_config.run_id,
            symbol=checked_config.symbol,
            source_backtest_log=checked_config.source_backtest_log,
            candidate_daily_bars_csv=checked_config.canonical_output,
        )
    )
    write_etf_sma_local_bars_backtest_refresh_jsonl(
        refresh_payload,
        checked_config.refresh_run_log,
    )
    refresh_blockers: tuple[str, ...] = ()
    if refresh_payload.get("refresh_state") != _REFRESHED:
        refresh_blockers = ("refresh_rerun_not_refreshed",)
    if refresh_payload.get("performance_evidence_state") != _PERFORMANCE_EVALUATED:
        refresh_blockers = (*refresh_blockers, "refresh_evidence_not_evaluated")

    return _payload(
        checked_config,
        source_refresh=source_refresh,
        source_backtest=source_backtest,
        provenance=provenance,
        data=data,
        manual_import_state=(
            _MANUAL_READY if not refresh_blockers else _MANUAL_BLOCKED
        ),
        performance_evidence_state=str(
            refresh_payload.get("performance_evidence_state")
            or _PERFORMANCE_INSUFFICIENT_RETURNS
        ),
        canonical_csv_written=True,
        refresh_rerun_performed=True,
        refresh_payload=refresh_payload,
        blockers=refresh_blockers,
    )


def render_etf_sma_local_bars_manual_import_json(
    payload: Mapping[str, object],
) -> str:
    """Return one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_local_bars_manual_import_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing manual import summary."""

    return "\n".join(
        (
            "ETF/SMA local-bars manual import",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"input_csv: {payload.get('input_csv', '')}",
            f"provenance_manifest: {payload.get('provenance_manifest', '')}",
            f"manual_import_state: {payload.get('manual_import_state', '')}",
            f"refresh_state: {payload.get('refresh_state', '')}",
            "performance_evidence_state: "
            f"{payload.get('performance_evidence_state', '')}",
            f"usable_bar_count: {payload.get('usable_bar_count', '')}",
            f"evaluated_return_count: {payload.get('evaluated_return_count', '')}",
            f"canonical_csv_written: {_bool_text(payload.get('canonical_csv_written'))}",
            "refresh_rerun_performed: "
            f"{_bool_text(payload.get('refresh_rerun_performed'))}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"broker_network_access: {_bool_text(payload.get('broker_network_access'))}",
            f"credential_access: {_bool_text(payload.get('credential_access'))}",
        )
    )


def write_etf_sma_local_bars_manual_import_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one JSONL record, replacing any previous file."""

    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_etf_sma_local_bars_manual_import_json(payload))
        stream.write("\n")


def _validate_provenance_manifest(
    config: EtfSmaLocalBarsManualImportConfig,
) -> _ProvenanceValidation:
    path = config.provenance_manifest
    if path is None:
        return _ProvenanceValidation(
            supplied=False,
            valid=False,
            manifest={},
            blockers=("provenance_manifest_missing",),
            manifest_sha256=None,
            normalized_input_csv=None,
        )
    if not path.is_file():
        return _ProvenanceValidation(
            supplied=True,
            valid=False,
            manifest={},
            blockers=("provenance_manifest_not_found",),
            manifest_sha256=None,
            normalized_input_csv=None,
        )

    blockers: list[str] = []
    manifest_sha256 = _sha256_file(path)
    try:
        manifest = _read_json_object(path, "provenance_manifest")
    except ValidationError as exc:
        return _ProvenanceValidation(
            supplied=True,
            valid=False,
            manifest={},
            blockers=(f"provenance_manifest:{_blocker_text(str(exc))}",),
            manifest_sha256=manifest_sha256,
            normalized_input_csv=None,
        )

    missing = tuple(field for field in _PROVENANCE_REQUIRED_FIELDS if field not in manifest)
    blockers.extend(f"missing_provenance_field:{field}" for field in missing)

    for field in _PROVENANCE_STRING_FIELDS:
        if field in manifest:
            try:
                value = _required_string(manifest[field], field)
            except ValidationError:
                blockers.append(f"invalid_provenance_field:{field}")
                continue
            normalized = _token(value)
            if normalized in _AMBIGUOUS_TEXT_VALUES:
                blockers.append(f"ambiguous_provenance_field:{field}")

    if manifest.get("symbol") != _SYMBOL:
        blockers.append("manifest_symbol_not_spy")
    if manifest.get("operator_attested") is not True:
        blockers.append("operator_attested_not_true")
    for field in _PROVENANCE_FALSE_FLAGS:
        if manifest.get(field) is not False:
            blockers.append(f"{field}_not_false")

    source_type = manifest.get("source_type")
    if type(source_type) is str and _token(source_type) in _FORBIDDEN_PROVENANCE_VALUES:
        blockers.append("provenance_rejected_generated_sample_fixture_test_synthetic")
    acquisition_method = manifest.get("acquisition_method")
    if (
        type(acquisition_method) is str
        and _token(acquisition_method) in _FORBIDDEN_PROVENANCE_VALUES
    ):
        blockers.append("provenance_rejected_generated_sample_fixture_test_synthetic")

    timeframe = manifest.get("timeframe")
    if type(timeframe) is str and _token(timeframe) not in _DAILY_TIMEFRAME_VALUES:
        blockers.append("timeframe_not_daily")

    attested_at = manifest.get("attested_at")
    if type(attested_at) is str and not _valid_iso_date_or_timestamp(attested_at):
        blockers.append("attested_at_not_iso_date_or_timestamp")

    normalized_input_csv: str | None = None
    if config.input_csv is not None and type(manifest.get("input_csv")) is str:
        provided = _normalized_compare_path(config.input_csv)
        manifest_values = {
            _normalized_compare_path(Path(str(manifest["input_csv"]))),
            _normalized_compare_path(Path(str(manifest["input_csv"])), base=path.parent),
        }
        normalized_input_csv = str(provided)
        if provided not in manifest_values:
            blockers.append("manifest_input_csv_path_mismatch")
    elif config.input_csv is not None:
        blockers.append("manifest_input_csv_path_mismatch")

    return _ProvenanceValidation(
        supplied=True,
        valid=not blockers,
        manifest=manifest,
        blockers=_dedupe(tuple(blockers)),
        manifest_sha256=manifest_sha256,
        normalized_input_csv=normalized_input_csv,
    )


def _validate_input_csv(
    config: EtfSmaLocalBarsManualImportConfig,
    provenance: _ProvenanceValidation,
) -> _DataValidation:
    path = config.input_csv
    empty = _empty_data_validation()
    if path is None:
        return _replace_data_validation(empty, blockers=("input_csv_missing",))
    if not path.is_file():
        return _replace_data_validation(
            empty,
            blockers=("input_csv_not_found",),
            input_sha256=None,
        )

    input_sha256 = _sha256_file(path)
    blockers: list[str] = []
    bars: list[LocalDailyBar] = []
    source_row_count = 0
    matching_symbol_row_count = 0
    non_spy_row_count = 0
    input_sorted_by_date: bool | None = True
    duplicate_dates = False
    malformed_rows = False
    missing_or_invalid_close = False
    non_positive_close = False
    previous_date: date | None = None
    seen_dates: set[date] = set()
    columns: tuple[str, ...] = ()
    column_mapping: dict[str, str] = {}
    schema = "unread"
    symbol_source = "unknown"

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = tuple(reader.fieldnames or ())
            column_mapping, schema, mapping_blockers = _column_mapping(
                columns,
                provenance,
            )
            blockers.extend(mapping_blockers)
            symbol_source = "symbol_column" if "symbol" in column_mapping else "manifest_symbol"
            if mapping_blockers:
                return _replace_data_validation(
                    empty,
                    blockers=_dedupe(tuple(blockers)),
                    input_sha256=input_sha256,
                    schema=schema,
                    columns=columns,
                    column_mapping=column_mapping,
                    input_sorted_by_date=input_sorted_by_date,
                    symbol_source=symbol_source,
                )

            for row_number, row in enumerate(reader, start=2):
                source_row_count += 1
                if None in row:
                    malformed_rows = True
                    blockers.append("malformed_csv_row")
                    continue

                row_symbol = _SYMBOL
                symbol_column = column_mapping.get("symbol")
                if symbol_column is not None:
                    try:
                        row_symbol = _required_string(row[symbol_column], "symbol").upper()
                    except ValidationError:
                        malformed_rows = True
                        blockers.append("malformed_symbol")
                        continue
                if row_symbol != _SYMBOL:
                    non_spy_row_count += 1
                    blockers.append("non_spy_rows_present")
                    continue

                try:
                    bar = _bar_from_row(row, column_mapping, row_number=row_number)
                except ValidationError as exc:
                    malformed_rows = True
                    reason, close_invalid, close_non_positive = _csv_validation_reason(
                        str(exc)
                    )
                    blockers.append(reason)
                    missing_or_invalid_close = (
                        missing_or_invalid_close or close_invalid
                    )
                    non_positive_close = non_positive_close or close_non_positive
                    continue

                matching_symbol_row_count += 1
                if bar.date in seen_dates:
                    duplicate_dates = True
                    blockers.append("duplicate_dates")
                if previous_date is not None and bar.date <= previous_date:
                    input_sorted_by_date = False
                    blockers.append("date_order_not_ascending")
                previous_date = bar.date
                seen_dates.add(bar.date)
                bars.append(bar)
    except OSError:
        return _replace_data_validation(
            empty,
            blockers=("input_csv_unreadable",),
            input_sha256=input_sha256,
        )

    if matching_symbol_row_count == 0:
        blockers.append("no_spy_rows")
    if len(bars) < _MINIMUM_REQUIRED_USABLE_BARS:
        blockers.append(
            f"insufficient_usable_bars:{len(bars)}<{_MINIMUM_REQUIRED_USABLE_BARS}"
        )

    return _DataValidation(
        valid=not blockers,
        blockers=_dedupe(tuple(blockers)),
        bars=tuple(bars),
        input_sha256=input_sha256,
        schema=schema,
        columns=columns,
        column_mapping=column_mapping,
        source_row_count=source_row_count,
        usable_bar_count=len(bars),
        matching_symbol_row_count=matching_symbol_row_count,
        non_spy_row_count=non_spy_row_count,
        input_sorted_by_date=input_sorted_by_date,
        duplicate_dates=duplicate_dates,
        malformed_rows=malformed_rows,
        missing_or_invalid_close=missing_or_invalid_close,
        non_positive_close=non_positive_close,
        symbol_source=symbol_source,
    )


def _column_mapping(
    columns: tuple[str, ...],
    provenance: _ProvenanceValidation,
) -> tuple[dict[str, str], str, tuple[str, ...]]:
    if not columns:
        return {}, "missing_header", ("schema_missing_header",)
    if len(set(columns)) != len(columns):
        return {}, "duplicate_columns", ("schema_duplicate_columns",)

    normalized_columns = {_column_token(column): column for column in columns}
    if len(normalized_columns) != len(columns):
        return {}, "duplicate_normalized_columns", ("schema_duplicate_columns",)

    blockers: list[str] = []
    mapping: dict[str, str] = {}
    for field, aliases in _COLUMN_ALIASES.items():
        matches = [
            original
            for normalized, original in normalized_columns.items()
            if normalized in aliases
        ]
        if len(matches) > 1:
            blockers.append(f"schema_ambiguous_column_mapping:{field}")
        elif matches:
            mapping[field] = matches[0]

    for required in ("date", "open", "high", "low", "volume"):
        if required not in mapping:
            blockers.append(f"schema_missing_required_column:{required}")
    if "close" not in mapping and "adjusted_close" not in mapping:
        blockers.append("schema_missing_required_column:close_or_adjusted_close")
    elif "close" not in mapping:
        mapping["close"] = mapping["adjusted_close"]
    elif "adjusted_close" not in mapping:
        mapping["adjusted_close"] = mapping["close"]

    strict = columns == LOCAL_DAILY_BARS_CSV_COLUMNS
    schema = "strict_local_daily_bars_csv" if strict else "mappable_daily_bars_csv"
    expected_schema = provenance.manifest.get("expected_schema")
    if (
        type(expected_schema) is str
        and "strict" in _token(expected_schema)
        and not strict
    ):
        blockers.append("manifest_expected_schema_mismatch:strict_local_daily_bars_csv")

    return mapping, schema, _dedupe(tuple(blockers))


def _bar_from_row(
    row: dict[str, str],
    column_mapping: Mapping[str, str],
    *,
    row_number: int,
) -> LocalDailyBar:
    return LocalDailyBar(
        symbol=_SYMBOL,
        date=_parse_date(_cell(row, column_mapping["date"]), f"row {row_number} date"),
        open=_parse_decimal(_cell(row, column_mapping["open"]), f"row {row_number} open"),
        high=_parse_decimal(_cell(row, column_mapping["high"]), f"row {row_number} high"),
        low=_parse_decimal(_cell(row, column_mapping["low"]), f"row {row_number} low"),
        close=_parse_decimal(
            _cell(row, column_mapping["close"]),
            f"row {row_number} close",
        ),
        adjusted_close=_parse_decimal(
            _cell(row, column_mapping["adjusted_close"]),
            f"row {row_number} adjusted_close",
        ),
        volume=_parse_volume(
            _cell(row, column_mapping["volume"]),
            f"row {row_number} volume",
        ),
    )


def _payload(
    config: EtfSmaLocalBarsManualImportConfig,
    *,
    source_refresh: Mapping[str, object],
    source_backtest: Mapping[str, object],
    provenance: _ProvenanceValidation,
    data: _DataValidation,
    manual_import_state: str,
    performance_evidence_state: str,
    canonical_csv_written: bool,
    refresh_rerun_performed: bool,
    refresh_payload: Mapping[str, object] | None,
    blockers: tuple[str, ...],
) -> dict[str, object]:
    refresh = dict(refresh_payload or {})
    starting_equity = str(
        refresh.get("starting_equity")
        or source_backtest.get("starting_equity")
        or _DEFAULT_STARTING_EQUITY
    )
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "strategy": _STRATEGY,
        "labels": list(ETF_SMA_LOCAL_BARS_MANUAL_IMPORT_LABELS),
        "input_csv": None if config.input_csv is None else str(config.input_csv),
        "provenance_manifest": (
            None
            if config.provenance_manifest is None
            else str(config.provenance_manifest)
        ),
        "source_refresh_log": str(config.source_refresh_log),
        "source_refresh": dict(source_refresh),
        "source_backtest_log": str(config.source_backtest_log),
        "source_backtest": dict(source_backtest),
        "run_log": str(config.run_log),
        "canonical_output": str(config.canonical_output),
        "refresh_run_log": str(config.refresh_run_log),
        "manual_import_state": manual_import_state,
        "canonical_csv_written": canonical_csv_written,
        "refresh_rerun_performed": refresh_rerun_performed,
        "refresh_state": refresh.get("refresh_state"),
        "backtest_state": refresh.get("backtest_state"),
        "performance_evidence_state": performance_evidence_state,
        "minimum_required_usable_bars": _MINIMUM_REQUIRED_USABLE_BARS,
        "source_bar_count": _int_or_default(refresh.get("source_bar_count"), data.source_row_count),
        "usable_bar_count": _int_or_default(refresh.get("usable_bar_count"), data.usable_bar_count),
        "evaluated_return_count": _int_or_default(
            refresh.get("evaluated_return_count"),
            0,
        ),
        "starting_equity": starting_equity,
        "ending_equity": str(refresh.get("ending_equity") or starting_equity),
        "total_return": str(refresh.get("total_return") or _ZERO_TEXT),
        "max_drawdown": str(refresh.get("max_drawdown") or _ZERO_TEXT),
        "exposure_fraction": str(refresh.get("exposure_fraction") or _ZERO_TEXT),
        "trade_count": _int_or_default(refresh.get("trade_count"), 0),
        "entry_count": _int_or_default(refresh.get("entry_count"), 0),
        "exit_count": _int_or_default(refresh.get("exit_count"), 0),
        "final_exposure": _int_or_default(refresh.get("final_exposure"), 0),
        "final_posture": str(refresh.get("final_posture") or "insufficient_history"),
        "final_decision": str(refresh.get("final_decision") or manual_import_state),
        "blockers": list(blockers),
        "provenance_validation": {
            "manifest_supplied": provenance.supplied,
            "manifest_operator_supplied": provenance.supplied,
            "manifest_template_used": False,
            "valid": provenance.valid,
            "manifest_sha256": provenance.manifest_sha256,
            "operator_attested": provenance.manifest.get("operator_attested"),
            "attested_by": provenance.manifest.get("attested_by"),
            "attested_at": provenance.manifest.get("attested_at"),
            "source_type": provenance.manifest.get("source_type"),
            "data_vendor_or_origin": provenance.manifest.get(
                "data_vendor_or_origin"
            ),
            "acquisition_method": provenance.manifest.get("acquisition_method"),
            "adjustment_policy": provenance.manifest.get("adjustment_policy"),
            "timeframe": provenance.manifest.get("timeframe"),
            "expected_schema": provenance.manifest.get("expected_schema"),
            "contains_synthetic_data": provenance.manifest.get(
                "contains_synthetic_data"
            ),
            "contains_fixture_data": provenance.manifest.get("contains_fixture_data"),
            "contains_sample_data": provenance.manifest.get("contains_sample_data"),
            "contains_test_data": provenance.manifest.get("contains_test_data"),
            "normalized_input_csv": provenance.normalized_input_csv,
        },
        "data_validation": {
            "valid": data.valid,
            "input_sha256": data.input_sha256,
            "schema": data.schema,
            "columns": list(data.columns),
            "canonical_schema": list(LOCAL_DAILY_BARS_CSV_COLUMNS),
            "column_mapping": dict(sorted(data.column_mapping.items())),
            "symbol_source": data.symbol_source,
            "source_row_count": data.source_row_count,
            "matching_symbol_row_count": data.matching_symbol_row_count,
            "non_spy_row_count": data.non_spy_row_count,
            "usable_bar_count": data.usable_bar_count,
            "input_sorted_by_date": data.input_sorted_by_date,
            "duplicate_dates": data.duplicate_dates,
            "malformed_rows": data.malformed_rows,
            "missing_or_invalid_close": data.missing_or_invalid_close,
            "non_positive_close": data.non_positive_close,
        },
        "data_provenance": {
            "local_files_only": True,
            "local_csv_only": True,
            "operator_attested": provenance.manifest.get("operator_attested") is True,
            "operator_evidence_synthetic": False,
            "fixture_sample_synthetic_test_data_used_as_operator_evidence": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
        },
        "refresh_summary": {
            "refresh_state": refresh.get("refresh_state"),
            "performance_evidence_state": refresh.get("performance_evidence_state"),
            "usable_bar_count": refresh.get("usable_bar_count"),
            "evaluated_return_count": refresh.get("evaluated_return_count"),
            "trade_count": refresh.get("trade_count"),
            "entry_count": refresh.get("entry_count"),
            "exit_count": refresh.get("exit_count"),
            "final_posture": refresh.get("final_posture"),
            "final_exposure": refresh.get("final_exposure"),
            "final_decision": refresh.get("final_decision"),
        },
        "posture_history": list(refresh.get("posture_history") or []),
        "equity_curve": list(refresh.get("equity_curve") or []),
        "events": list(refresh.get("events") or []),
        "fixture_sample_synthetic_test_data_used_as_operator_evidence": False,
        "operator_evidence_synthetic": False,
        "profit_claim": "none",
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "submit_path_allowed": False,
        "paper_submit_approved": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "broker_network_access": False,
        "credential_access": False,
        "credential_access_attempted": False,
        "network_access_attempted": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "market_data_fetch_performed": False,
        "paper_lab_only": True,
        "research_only": True,
        "signal_evaluation_only": True,
        "not_live_authorized": True,
    }


def _source_log_metadata(
    path: Path,
    *,
    field_name: str,
    expected_record_type: str,
    expected_command: str,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "path": str(path),
        "status": "unread",
        "valid": False,
        "run_id": None,
        "record_type": None,
        "command": None,
        "symbol": None,
        "profit_claim": None,
        "starting_equity": _DEFAULT_STARTING_EQUITY,
        "blockers": [],
    }
    try:
        record = _last_jsonl_record(path, field_name)
    except ValidationError as exc:
        metadata["status"] = "invalid"
        metadata["blockers"] = [f"{field_name}:{_blocker_text(str(exc))}"]
        return metadata

    blockers: list[str] = []
    identity_valid = (
        record.get("record_type") == expected_record_type
        or record.get("command") == expected_command
    )
    if not identity_valid:
        blockers.append(f"{field_name}_record_type_invalid")
    if record.get("symbol") != _SYMBOL:
        blockers.append(f"{field_name}_symbol_invalid")
    if record.get("profit_claim") != "none":
        blockers.append(f"{field_name}_profit_claim_not_none")
    for safety_field in _SOURCE_SAFETY_FALSE_FIELDS:
        if record.get(safety_field) is not False:
            blockers.append(f"{field_name}_{safety_field}_not_false")

    starting_equity = record.get("starting_equity")
    if starting_equity is not None:
        try:
            _positive_decimal(starting_equity, "starting_equity")
        except ValidationError:
            blockers.append(f"{field_name}_starting_equity_invalid")
        else:
            metadata["starting_equity"] = str(starting_equity)

    metadata.update(
        {
            "status": "loaded",
            "valid": not blockers,
            "run_id": record.get("run_id"),
            "record_type": record.get("record_type"),
            "command": record.get("command"),
            "symbol": record.get("symbol"),
            "profit_claim": record.get("profit_claim"),
            "canonicalization_state": record.get("canonicalization_state"),
            "refresh_state": record.get("refresh_state"),
            "performance_evidence_state": record.get("performance_evidence_state"),
            "usable_bar_count": record.get("usable_bar_count"),
            "evaluated_return_count": record.get("evaluated_return_count"),
            "blockers": blockers,
        }
    )
    return metadata


def _last_jsonl_record(path: Path, field_name: str) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError(f"{field_name} must reference an existing JSONL file.")

    last_record: dict[str, object] | None = None
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    candidate = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValidationError(
                        f"{field_name} line {line_number} must be JSON."
                    ) from exc
                if type(candidate) is not dict:
                    raise ValidationError(
                        f"{field_name} line {line_number} must be an object."
                    )
                last_record = dict(candidate)
    except OSError as exc:
        raise ValidationError(f"{field_name} could not be read.") from exc

    if last_record is None:
        raise ValidationError(f"{field_name} must contain a JSONL record.")
    return last_record


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


def _write_canonical_csv(bars: tuple[LocalDailyBar, ...], output_path: Path) -> None:
    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LOCAL_DAILY_BARS_CSV_COLUMNS)
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "symbol": bar.symbol,
                    "date": bar.date.isoformat(),
                    "open": str(bar.open),
                    "high": str(bar.high),
                    "low": str(bar.low),
                    "close": str(bar.close),
                    "adjusted_close": str(bar.adjusted_close),
                    "volume": str(bar.volume),
                }
            )


def _empty_data_validation() -> _DataValidation:
    return _DataValidation(
        valid=False,
        blockers=(),
        bars=(),
        input_sha256=None,
        schema="unread",
        columns=(),
        column_mapping={},
        source_row_count=0,
        usable_bar_count=0,
        matching_symbol_row_count=0,
        non_spy_row_count=0,
        input_sorted_by_date=None,
        duplicate_dates=False,
        malformed_rows=False,
        missing_or_invalid_close=False,
        non_positive_close=False,
        symbol_source="unknown",
    )


def _replace_data_validation(
    value: _DataValidation,
    *,
    blockers: tuple[str, ...] | None = None,
    input_sha256: str | None = None,
    schema: str | None = None,
    columns: tuple[str, ...] | None = None,
    column_mapping: dict[str, str] | None = None,
    input_sorted_by_date: bool | None = None,
    symbol_source: str | None = None,
) -> _DataValidation:
    return _DataValidation(
        valid=False,
        blockers=value.blockers if blockers is None else blockers,
        bars=value.bars,
        input_sha256=value.input_sha256 if input_sha256 is None else input_sha256,
        schema=value.schema if schema is None else schema,
        columns=value.columns if columns is None else columns,
        column_mapping=value.column_mapping if column_mapping is None else column_mapping,
        source_row_count=value.source_row_count,
        usable_bar_count=value.usable_bar_count,
        matching_symbol_row_count=value.matching_symbol_row_count,
        non_spy_row_count=value.non_spy_row_count,
        input_sorted_by_date=(
            value.input_sorted_by_date
            if input_sorted_by_date is None
            else input_sorted_by_date
        ),
        duplicate_dates=value.duplicate_dates,
        malformed_rows=value.malformed_rows,
        missing_or_invalid_close=value.missing_or_invalid_close,
        non_positive_close=value.non_positive_close,
        symbol_source=value.symbol_source if symbol_source is None else symbol_source,
    )


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


def _parse_decimal(value: str, field_name: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a Decimal string.") from exc
    return _positive_decimal(parsed, field_name)


def _parse_volume(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an integer string.") from exc
    if str(parsed) != value:
        raise ValidationError(f"{field_name} must be an integer string.")
    if parsed < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return parsed


def _csv_validation_reason(message: str) -> tuple[str, bool, bool]:
    lowered = message.lower()
    if "close must be greater than zero" in lowered:
        return "non_positive_close", True, True
    if "close must be" in lowered:
        return "missing_or_invalid_close", True, False
    if "duplicates date" in lowered:
        return "duplicate_dates", False, False
    if "high must be" in lowered or "low must be" in lowered:
        return "malformed_ohlc", False, False
    return f"malformed_csv:{_blocker_text(message)}", False, False


def _config(value: object) -> EtfSmaLocalBarsManualImportConfig:
    if type(value) is not EtfSmaLocalBarsManualImportConfig:
        raise ValidationError("config must be an EtfSmaLocalBarsManualImportConfig.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _spy_symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    normalized = symbol.upper()
    if normalized != symbol:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if normalized != _SYMBOL:
        raise ValidationError("M409 etf-sma-local-bars-manual-import supports only SPY.")
    return normalized


def _path_value(
    value: object,
    field_name: str,
    *,
    required_suffix: str,
) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    if isinstance(value, str) and "://" in value:
        raise ValidationError(f"{field_name} must be a local path.")
    if path.suffix.lower() != required_suffix:
        raise ValidationError(f"{field_name} must reference a {required_suffix} file.")
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
    return _path_value(value, field_name, required_suffix=required_suffix)


def _output_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("output_path must be a path.")
    if str(path).strip() == "":
        raise ValidationError("output_path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _positive_decimal(value: object, field_name: str) -> Decimal:
    if type(value) is Decimal:
        decimal_value = value
    elif type(value) is str:
        try:
            decimal_value = Decimal(value)
        except InvalidOperation as exc:
            raise ValidationError(f"{field_name} must be a Decimal.") from exc
    else:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not decimal_value.is_finite() or decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be greater than zero.")
    return decimal_value


def _int_or_default(value: object, default: int) -> int:
    if type(value) is int and not isinstance(value, bool) and value >= 0:
        return value
    return default


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


def _column_token(value: str) -> str:
    return _token(value.replace(".", " ").replace("/", " ").replace("-", " "))


def _token(value: str) -> str:
    return "_".join(value.strip().lower().split())


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return tuple(output)


def _blocker_text(value: str) -> str:
    return "_".join(value.lower().replace(".", "").replace(",", "").split())


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"
