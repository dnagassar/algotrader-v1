"""Strict local SPY daily-bars canonicalization for ETF/SMA evidence."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_backtest_stats import (
    EtfSmaBacktestStatsConfig,
    build_etf_sma_backtest_stats,
)
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    LocalDailyBarsCsvResult,
    load_local_daily_bars_csv,
)

__all__ = [
    "ETF_SMA_LOCAL_BARS_CANONICALIZATION_LABELS",
    "EtfSmaLocalBarsCanonicalizationConfig",
    "build_etf_sma_local_bars_canonicalization",
    "render_etf_sma_local_bars_canonicalization_json",
    "render_etf_sma_local_bars_canonicalization_text",
    "write_etf_sma_local_bars_canonicalization_jsonl",
]


ETF_SMA_LOCAL_BARS_CANONICALIZATION_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_RECORD_TYPE = "etf_sma_local_bars_canonicalization"
_SCHEMA_VERSION = "1"
_COMMAND = "etf-sma-local-bars-canonicalize"
_STRATEGY = "spy_etf_sma_50_200_daily_long_only"
_SYMBOL = "SPY"
_MINIMUM_REQUIRED_USABLE_BARS = 201
_CANONICALIZED = "canonicalized_strict_local_operator_bars"
_BLOCKED_NO_VALID = "blocked_no_valid_extended_local_operator_bars"
_PERFORMANCE_READY = "local_operator_bars_ready_for_refresh"
_PERFORMANCE_INSUFFICIENT_RETURNS = "insufficient_post_signal_returns"
_M402_NOTE = (
    "M402 200-bar fixture is insufficient: it reaches the 200-bar SMA warmup "
    "but cannot evaluate a post-signal return."
)
_M378_NOTE = (
    "M378 sample schema date,symbol,close is not operator evidence unless "
    "independently proven otherwise."
)
_EXCLUDED_DIR_PARTS = frozenset(
    (
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "node_modules",
        "site-packages",
        "dist",
        "build",
        "htmlcov",
        "tmp",
        "temp",
        "test_tmp",
        "pytest_tmp",
    )
)
_FORBIDDEN_PROVENANCE_TOKENS = (
    "fixture",
    "sample",
    "synthetic",
    "test",
    "tests",
    "demo",
    "mock",
    "fake",
)
_OPERATOR_PROVENANCE_TOKENS = (
    "operator",
    "operator_evidence",
    "manual",
    "manually_acquired",
    "local_operator",
)


@dataclass(frozen=True, slots=True)
class EtfSmaLocalBarsCanonicalizationConfig:
    """Inputs for one deterministic local-bars canonicalization artifact."""

    run_id: str
    candidate_root: Path | str
    source_refresh_log: Path | str
    run_log: Path | str
    canonical_output: Path | str
    symbol: str = _SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "candidate_root",
            _directory_path(self.candidate_root, "candidate_root"),
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


def build_etf_sma_local_bars_canonicalization(
    config: EtfSmaLocalBarsCanonicalizationConfig,
) -> dict[str, object]:
    """Search local CSVs, catalog candidates, and canonicalize one valid source."""

    checked_config = _config(config)
    source_refresh = _source_refresh_metadata(checked_config.source_refresh_log)
    candidates = tuple(_candidate_paths(checked_config))
    candidate_records = tuple(
        _classify_candidate(path, checked_config)
        for path in candidates
    )
    accepted = tuple(
        candidate for candidate in candidate_records if candidate["accepted"] is True
    )

    selected = accepted[0] if accepted else None
    if selected is not None:
        source_path = Path(str(selected["absolute_path"]))
        csv_result = load_local_daily_bars_csv(source_path, symbol=checked_config.symbol)
        _write_canonical_csv(csv_result, checked_config.canonical_output)
        canonicalization_state = _CANONICALIZED
        performance_evidence_state = _PERFORMANCE_READY
        blockers: tuple[str, ...] = ()
        accepted_source = str(selected["path"])
        canonical_output_written = True
        usable_bar_count = int(selected["usable_bar_count"])
        evaluated_return_count = int(selected["evaluated_return_count"])
    else:
        canonicalization_state = _BLOCKED_NO_VALID
        performance_evidence_state = _PERFORMANCE_INSUFFICIENT_RETURNS
        blockers = _blocked_reasons(candidate_records)
        accepted_source = None
        canonical_output_written = False
        usable_bar_count = _max_int(candidate_records, "usable_bar_count")
        evaluated_return_count = _max_int(candidate_records, "evaluated_return_count")

    return _payload(
        checked_config,
        source_refresh=source_refresh,
        candidate_records=candidate_records,
        canonicalization_state=canonicalization_state,
        performance_evidence_state=performance_evidence_state,
        blockers=blockers,
        accepted_source=accepted_source,
        canonical_output_written=canonical_output_written,
        usable_bar_count=usable_bar_count,
        evaluated_return_count=evaluated_return_count,
    )


def render_etf_sma_local_bars_canonicalization_json(
    payload: Mapping[str, object],
) -> str:
    """Return one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_local_bars_canonicalization_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing canonicalization summary."""

    return "\n".join(
        (
            "ETF/SMA local-bars canonicalization",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"candidate_root: {payload.get('candidate_root', '')}",
            f"source_refresh_log: {payload.get('source_refresh_log', '')}",
            f"canonical_output: {payload.get('canonical_output', '')}",
            f"canonicalization_state: {payload.get('canonicalization_state', '')}",
            "performance_evidence_state: "
            f"{payload.get('performance_evidence_state', '')}",
            f"candidate_count: {payload.get('candidate_count', '')}",
            f"accepted_source: {payload.get('accepted_source', '')}",
            f"usable_bar_count: {payload.get('usable_bar_count', '')}",
            f"evaluated_return_count: {payload.get('evaluated_return_count', '')}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"broker_network_access: {_bool_text(payload.get('broker_network_access'))}",
            f"credential_access: {_bool_text(payload.get('credential_access'))}",
        )
    )


def write_etf_sma_local_bars_canonicalization_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one JSONL record, replacing any previous file."""

    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_etf_sma_local_bars_canonicalization_json(payload))
        stream.write("\n")


def _candidate_paths(
    config: EtfSmaLocalBarsCanonicalizationConfig,
) -> tuple[Path, ...]:
    root = config.candidate_root
    canonical_output = _resolved(config.canonical_output)
    paths: list[Path] = []
    for current_root, directory_names, file_names in os.walk(root):
        directory_names[:] = sorted(
            name
            for name in directory_names
            if not _excluded_dir_name(name)
        )
        current_path = Path(current_root)
        if _has_excluded_part(_relative_parts(current_path, root)):
            continue
        for file_name in sorted(file_names):
            path = current_path / file_name
            if path.suffix.lower() != ".csv":
                continue
            if _resolved(path) == canonical_output:
                continue
            paths.append(path)
    return tuple(sorted(paths, key=lambda item: _display_path(item, root).lower()))


def _classify_candidate(
    path: Path,
    config: EtfSmaLocalBarsCanonicalizationConfig,
) -> dict[str, object]:
    relative_path = _display_path(path, config.candidate_root)
    header, row_count, header_error = _csv_header_and_count(path)
    schema = "strict_local_daily_bars_csv" if header == LOCAL_DAILY_BARS_CSV_COLUMNS else (
        "unreadable_csv" if header_error else "unsupported_csv_schema"
    )
    rejection_reasons: list[str] = []
    provenance = _provenance_assessment(relative_path)
    if provenance["rejection_reason"]:
        rejection_reasons.append(str(provenance["rejection_reason"]))
    if header_error:
        rejection_reasons.append(f"csv_unreadable:{_blocker_text(header_error)}")
    if header is not None and header != LOCAL_DAILY_BARS_CSV_COLUMNS:
        rejection_reasons.append("unsupported_schema:not_strict_local_daily_bars_csv")

    usable_bar_count = 0
    matching_symbol_row_count = 0
    ignored_wrong_symbol_row_count = 0
    evaluated_return_count = 0
    input_sorted_by_date: bool | None = None
    duplicate_dates = False
    malformed_rows = False
    missing_or_invalid_close = False
    non_positive_close = False
    symbol_compatible = False
    date_ordering = "unknown"
    stats_backtest_state = ""
    stats_performance_evidence_state = ""

    if header == LOCAL_DAILY_BARS_CSV_COLUMNS:
        try:
            csv_result = load_local_daily_bars_csv(path, symbol=config.symbol)
        except ValidationError as exc:
            reason, flags = _validation_rejection(str(exc))
            rejection_reasons.append(reason)
            duplicate_dates = flags["duplicate_dates"]
            malformed_rows = flags["malformed_rows"]
            missing_or_invalid_close = flags["missing_or_invalid_close"]
            non_positive_close = flags["non_positive_close"]
        else:
            row_count = csv_result.total_row_count
            usable_bar_count = csv_result.observed_usable_bars
            matching_symbol_row_count = csv_result.matching_symbol_row_count
            ignored_wrong_symbol_row_count = csv_result.ignored_wrong_symbol_row_count
            input_sorted_by_date = csv_result.input_sorted_by_date
            symbol_compatible = (
                csv_result.matching_symbol_row_count > 0
                and csv_result.ignored_wrong_symbol_row_count == 0
            )
            date_ordering = (
                "ascending" if csv_result.input_sorted_by_date else "not_ascending"
            )
            if not csv_result.input_sorted_by_date:
                rejection_reasons.append("date_order_not_ascending")
            if csv_result.ignored_wrong_symbol_row_count:
                rejection_reasons.append("non_spy_rows_present")
            if csv_result.matching_symbol_row_count == 0:
                rejection_reasons.append("no_spy_rows")
            if usable_bar_count < _MINIMUM_REQUIRED_USABLE_BARS:
                rejection_reasons.append(
                    "insufficient_usable_bars:"
                    f"{usable_bar_count}<{_MINIMUM_REQUIRED_USABLE_BARS}"
                )
            stats = _stats_probe(path, config, csv_result)
            stats_backtest_state = str(stats["backtest_state"])
            stats_performance_evidence_state = str(
                stats["performance_evidence_state"]
            )
            evaluated_return_count = int(stats["evaluated_return_count"])
            if (
                usable_bar_count >= _MINIMUM_REQUIRED_USABLE_BARS
                and evaluated_return_count <= 0
            ):
                rejection_reasons.append("missing_post_signal_return_evaluation")

    rejection_reasons = list(_dedupe(tuple(rejection_reasons)))
    return {
        "path": relative_path,
        "absolute_path": str(path),
        "schema": schema,
        "columns": [] if header is None else list(header),
        "source_row_count": row_count,
        "usable_bar_count": usable_bar_count,
        "minimum_required_usable_bars": _MINIMUM_REQUIRED_USABLE_BARS,
        "matching_symbol_row_count": matching_symbol_row_count,
        "ignored_wrong_symbol_row_count": ignored_wrong_symbol_row_count,
        "symbol_compatible": symbol_compatible,
        "input_sorted_by_date": input_sorted_by_date,
        "date_ordering": date_ordering,
        "duplicate_dates": duplicate_dates,
        "malformed_rows": malformed_rows,
        "missing_or_invalid_close": missing_or_invalid_close,
        "non_positive_close": non_positive_close,
        "provenance_risk": provenance["risk"],
        "provenance_markers": list(provenance["markers"]),
        "stats_backtest_state": stats_backtest_state,
        "stats_performance_evidence_state": stats_performance_evidence_state,
        "evaluated_return_count": evaluated_return_count,
        "accepted": not rejection_reasons,
        "rejection_reasons": rejection_reasons,
    }


def _stats_probe(
    path: Path,
    config: EtfSmaLocalBarsCanonicalizationConfig,
    csv_result: LocalDailyBarsCsvResult,
) -> dict[str, object]:
    if csv_result.ignored_wrong_symbol_row_count:
        return {
            "backtest_state": "",
            "performance_evidence_state": "",
            "evaluated_return_count": 0,
        }
    if csv_result.input_sorted_by_date is not True:
        return {
            "backtest_state": "",
            "performance_evidence_state": "",
            "evaluated_return_count": 0,
        }
    try:
        payload = build_etf_sma_backtest_stats(
            EtfSmaBacktestStatsConfig(
                run_id=config.run_id,
                symbol=config.symbol,
                daily_bars_csv=path,
            )
        )
    except ValidationError:
        return {
            "backtest_state": "",
            "performance_evidence_state": "",
            "evaluated_return_count": 0,
        }
    return {
        "backtest_state": str(payload.get("backtest_state", "")),
        "performance_evidence_state": str(
            payload.get("performance_evidence_state", "")
        ),
        "evaluated_return_count": _int_value(
            payload.get("evaluated_return_count"),
            "evaluated_return_count",
        ),
    }


def _payload(
    config: EtfSmaLocalBarsCanonicalizationConfig,
    *,
    source_refresh: Mapping[str, object],
    candidate_records: tuple[dict[str, object], ...],
    canonicalization_state: str,
    performance_evidence_state: str,
    blockers: tuple[str, ...],
    accepted_source: str | None,
    canonical_output_written: bool,
    usable_bar_count: int,
    evaluated_return_count: int,
) -> dict[str, object]:
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "strategy": _STRATEGY,
        "labels": list(ETF_SMA_LOCAL_BARS_CANONICALIZATION_LABELS),
        "candidate_root": str(config.candidate_root),
        "candidate_roots_searched": [str(config.candidate_root)],
        "source_refresh_log": str(config.source_refresh_log),
        "source_refresh": dict(source_refresh),
        "canonical_output": str(config.canonical_output),
        "canonical_output_written": canonical_output_written,
        "canonicalization_state": canonicalization_state,
        "performance_evidence_state": performance_evidence_state,
        "minimum_required_usable_bars": _MINIMUM_REQUIRED_USABLE_BARS,
        "usable_bar_count": usable_bar_count,
        "evaluated_return_count": evaluated_return_count,
        "candidate_count": len(candidate_records),
        "accepted_source": accepted_source,
        "accepted_source_is_real_local_operator_data": accepted_source is not None,
        "fixture_sample_synthetic_test_data_used_as_operator_evidence": False,
        "operator_evidence_synthetic": False,
        "blockers": list(blockers),
        "blocker_notes": [_M402_NOTE, _M378_NOTE],
        "candidates": [
            _candidate_public_record(candidate) for candidate in candidate_records
        ],
        "data_provenance": {
            "local_files_only": True,
            "local_csv_only": True,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "operator_evidence_synthetic": False,
            "fixture_sample_synthetic_test_data_used_as_operator_evidence": False,
        },
        "profit_claim": "none",
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
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


def _candidate_public_record(candidate: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in candidate.items()
        if key != "absolute_path"
    }


def _write_canonical_csv(
    csv_result: LocalDailyBarsCsvResult,
    output_path: Path,
) -> None:
    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LOCAL_DAILY_BARS_CSV_COLUMNS)
        writer.writeheader()
        for bar in csv_result.usable_bars:
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


def _csv_header_and_count(path: Path) -> tuple[tuple[str, ...] | None, int, str | None]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            try:
                header = tuple(next(reader))
            except StopIteration:
                return None, 0, "empty_csv"
            row_count = sum(1 for _row in reader)
    except OSError as exc:
        return None, 0, str(exc)
    return header, row_count, None


def _provenance_assessment(relative_path: str) -> dict[str, object]:
    text = _token_text(relative_path)
    forbidden = tuple(
        token for token in _FORBIDDEN_PROVENANCE_TOKENS if token in text
    )
    operator_markers = tuple(
        token for token in _OPERATOR_PROVENANCE_TOKENS if token in text
    )
    if forbidden:
        return {
            "risk": "fixture_sample_synthetic_test_demo",
            "markers": forbidden,
            "rejection_reason": "provenance_rejected_fixture_sample_synthetic_test_demo",
        }
    if not operator_markers:
        return {
            "risk": "ambiguous_provenance",
            "markers": (),
            "rejection_reason": "provenance_rejected_ambiguous_not_operator_evidence",
        }
    return {
        "risk": "clear_local_operator_path",
        "markers": operator_markers,
        "rejection_reason": "",
    }


def _validation_rejection(message: str) -> tuple[str, dict[str, bool]]:
    lowered = message.lower()
    flags = {
        "duplicate_dates": False,
        "malformed_rows": False,
        "missing_or_invalid_close": False,
        "non_positive_close": False,
    }
    if "duplicates date" in lowered:
        flags["duplicate_dates"] = True
        return "duplicate_dates", flags
    if "too many values" in lowered:
        flags["malformed_rows"] = True
        return "malformed_csv_row", flags
    if "missing required columns" in lowered:
        flags["malformed_rows"] = True
        return "schema_missing_required_columns", flags
    if "unsupported columns" in lowered:
        flags["malformed_rows"] = True
        return "schema_unsupported_columns", flags
    if "close must be greater than zero" in lowered:
        flags["missing_or_invalid_close"] = True
        flags["non_positive_close"] = True
        return "non_positive_close", flags
    if "close must be" in lowered:
        flags["missing_or_invalid_close"] = True
        return "missing_or_invalid_close", flags
    return f"malformed_csv:{_blocker_text(message)}", flags


def _blocked_reasons(
    candidate_records: tuple[Mapping[str, object], ...],
) -> tuple[str, ...]:
    reasons: list[str] = [_BLOCKED_NO_VALID]
    if not candidate_records:
        reasons.append("no_local_csv_candidates_found")
    for candidate in candidate_records:
        for reason in _string_list(candidate.get("rejection_reasons")):
            reasons.append(reason)
    return _dedupe(tuple(reasons))


def _source_refresh_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {
        "path": str(path),
        "status": "unread",
        "run_id": None,
        "refresh_state": None,
        "performance_evidence_state": None,
        "candidate_daily_bars_csv": None,
        "usable_bar_count": None,
        "evaluated_return_count": None,
    }
    try:
        record = _last_jsonl_record(path)
    except ValidationError as exc:
        metadata["status"] = "invalid"
        metadata["error"] = _blocker_text(str(exc))
        return metadata
    metadata.update(
        {
            "status": "loaded",
            "run_id": record.get("run_id"),
            "refresh_state": record.get("refresh_state"),
            "performance_evidence_state": record.get("performance_evidence_state"),
            "candidate_daily_bars_csv": record.get("candidate_daily_bars_csv"),
            "usable_bar_count": record.get("usable_bar_count"),
            "evaluated_return_count": record.get("evaluated_return_count"),
        }
    )
    return metadata


def _last_jsonl_record(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError("source_refresh_log must reference an existing JSONL file.")

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
                        f"source_refresh_log line {line_number} must be JSON."
                    ) from exc
                if type(candidate) is not dict:
                    raise ValidationError(
                        f"source_refresh_log line {line_number} must be an object."
                    )
                last_record = dict(candidate)
    except OSError as exc:
        raise ValidationError("source_refresh_log could not be read.") from exc

    if last_record is None:
        raise ValidationError("source_refresh_log must contain a JSONL record.")
    return last_record


def _config(value: object) -> EtfSmaLocalBarsCanonicalizationConfig:
    if type(value) is not EtfSmaLocalBarsCanonicalizationConfig:
        raise ValidationError(
            "config must be an EtfSmaLocalBarsCanonicalizationConfig."
        )
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
        raise ValidationError("M408 etf-sma-local-bars-canonicalize supports only SPY.")
    return normalized


def _directory_path(value: object, field_name: str) -> Path:
    path = _path_value(value, field_name, required_suffix=None)
    if not path.exists():
        raise ValidationError(f"{field_name} must reference an existing local directory.")
    if not path.is_dir():
        raise ValidationError(f"{field_name} must reference a local directory.")
    return path


def _path_value(
    value: object,
    field_name: str,
    *,
    required_suffix: str | None,
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
    if required_suffix is not None and path.suffix.lower() != required_suffix:
        raise ValidationError(f"{field_name} must reference a {required_suffix} file.")
    return path


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


def _excluded_dir_name(name: str) -> bool:
    return name.lower() in _EXCLUDED_DIR_PARTS


def _has_excluded_part(parts: tuple[str, ...]) -> bool:
    return any(part.lower() in _EXCLUDED_DIR_PARTS for part in parts)


def _relative_parts(path: Path, root: Path) -> tuple[str, ...]:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return path.parts
    return relative.parts


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _resolved(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def _token_text(value: str) -> str:
    text = value.lower()
    for character in ("\\", "/", "-", ".", " "):
        text = text.replace(character, "_")
    return f"_{text}_"


def _string_list(value: object) -> list[str]:
    if type(value) is not list:
        return []
    return [item for item in value if type(item) is str]


def _int_value(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return value


def _max_int(
    candidate_records: tuple[Mapping[str, object], ...],
    field_name: str,
) -> int:
    values = [
        value
        for candidate in candidate_records
        for value in (candidate.get(field_name),)
        if type(value) is int and not isinstance(value, bool)
    ]
    return max(values, default=0)


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
