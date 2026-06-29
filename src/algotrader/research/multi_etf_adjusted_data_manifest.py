"""Local adjusted daily data discovery and manifest for the approved ETF basket.

This module is offline-only. It reads already-local canonical CSV files,
validates them through the strict daily-bars loader, writes a combined
multi-symbol canonical CSV for downstream research, and records explicit
``data_refresh_required`` status for missing or invalid symbols.
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    LocalDailyBar,
    load_local_daily_bars_csv,
)

__all__ = [
    "APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS",
    "MultiEtfAdjustedDataManifestConfig",
    "build_multi_etf_adjusted_data_manifest",
    "main",
    "render_multi_etf_adjusted_data_manifest_json",
    "run_multi_etf_adjusted_data_manifest",
    "write_multi_etf_adjusted_data_manifest_json",
]


APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS = ("SPY", "QQQ", "IWM", "TLT", "GLD")

_RECORD_TYPE = "multi_etf_adjusted_data_manifest"
_SCHEMA_VERSION = "1"
_COMMAND = "multi-etf-adjusted-data-manifest"
_DEFAULT_OUTPUT_MANIFEST = Path("runs/operator_input/multi_etf_adjusted_data_manifest.json")
_DEFAULT_COMBINED_OUTPUT_CSV = Path(
    "runs/operator_input/multi_etf_adjusted_daily_canonical.csv"
)
_DEFAULT_CANONICAL_PATHS = {
    "SPY": Path("runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"),
    "QQQ": Path("runs/operator_input/qqq_daily_tiingo_adjusted_canonical.csv"),
    "IWM": Path("runs/operator_input/iwm_daily_tiingo_adjusted_canonical.csv"),
    "TLT": Path("runs/operator_input/tlt_daily_tiingo_adjusted_canonical.csv"),
    "GLD": Path("runs/operator_input/gld_daily_tiingo_adjusted_canonical.csv"),
}
_ADJUSTED_CLOSE_BASIS = "adjusted_close_price_return"
_LABELS = (
    "research_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
)
_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class MultiEtfAdjustedDataManifestConfig:
    """Inputs for one local multi-ETF adjusted-data manifest build."""

    output_manifest: Path | str = _DEFAULT_OUTPUT_MANIFEST
    combined_output_csv: Path | str = _DEFAULT_COMBINED_OUTPUT_CSV
    symbols: Iterable[str] | str = APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS
    canonical_paths: Mapping[str, Path | str] | None = None
    as_of: date | str | None = None
    expected_latest_bar_date: date | str | None = None
    run_id: str = "multi_etf_adjusted_data_manifest"

    def __post_init__(self) -> None:
        symbols = _symbol_tuple(self.symbols)
        object.__setattr__(
            self,
            "output_manifest",
            _path(self.output_manifest, "output_manifest"),
        )
        object.__setattr__(
            self,
            "combined_output_csv",
            _csv_path(self.combined_output_csv, "combined_output_csv"),
        )
        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(
            self,
            "canonical_paths",
            _canonical_paths(self.canonical_paths, symbols),
        )
        object.__setattr__(self, "as_of", _optional_date(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "expected_latest_bar_date",
            _optional_date(self.expected_latest_bar_date, "expected_latest_bar_date"),
        )
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))


def run_multi_etf_adjusted_data_manifest(
    config: MultiEtfAdjustedDataManifestConfig,
) -> dict[str, object]:
    """Build and write the combined CSV plus manifest JSON."""

    checked_config = _config(config)
    payload = build_multi_etf_adjusted_data_manifest(checked_config)
    write_multi_etf_adjusted_data_manifest_json(payload, checked_config.output_manifest)
    return payload


def build_multi_etf_adjusted_data_manifest(
    config: MultiEtfAdjustedDataManifestConfig,
) -> dict[str, object]:
    """Validate local canonical inputs and write a combined canonical CSV."""

    checked_config = _config(config)
    symbol_records: list[dict[str, object]] = []
    combined_bars: list[LocalDailyBar] = []

    for symbol in checked_config.symbols:
        path = checked_config.canonical_paths[symbol]
        record, bars = _symbol_record(
            symbol,
            path=path,
            as_of=checked_config.as_of,
            expected_latest_bar_date=checked_config.expected_latest_bar_date,
        )
        symbol_records.append(record)
        combined_bars.extend(bars)

    _write_combined_canonical_csv(checked_config.combined_output_csv, combined_bars)
    combined_sha256 = _sha256_file(checked_config.combined_output_csv)
    valid_symbols = [
        str(record["symbol"])
        for record in symbol_records
        if record.get("validation_status") == "valid"
    ]
    refresh_required_symbols = [
        str(record["symbol"])
        for record in symbol_records
        if record.get("data_refresh_status") == "data_refresh_required"
    ]
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "labels": list(_LABELS),
        "symbols": list(checked_config.symbols),
        "approved_symbols": list(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS),
        "valid_symbols": valid_symbols,
        "refresh_required_symbols": refresh_required_symbols,
        "missing_symbols": [
            str(record["symbol"])
            for record in symbol_records
            if record.get("validation_status") == "missing_data"
        ],
        "invalid_symbols": [
            str(record["symbol"])
            for record in symbol_records
            if record.get("validation_status") == "invalid"
        ],
        "symbol_count": len(checked_config.symbols),
        "valid_symbol_count": len(valid_symbols),
        "refresh_required_symbol_count": len(refresh_required_symbols),
        "as_of": _date_text(checked_config.as_of),
        "expected_latest_bar_date": _date_text(checked_config.expected_latest_bar_date),
        "output_manifest": str(checked_config.output_manifest),
        "combined_output_csv": str(checked_config.combined_output_csv),
        "combined_output_sha256": combined_sha256,
        "combined_row_count": len(combined_bars),
        "adjusted_close_basis": _ADJUSTED_CLOSE_BASIS,
        "symbol_data": symbol_records,
        "safety": _safety_payload(),
    }


def write_multi_etf_adjusted_data_manifest_json(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one sorted JSON manifest file."""

    path = _path(output_path, "output_manifest")
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_multi_etf_adjusted_data_manifest_json(payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def render_multi_etf_adjusted_data_manifest_json(payload: Mapping[str, object]) -> str:
    """Render deterministic compact manifest JSON."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def _symbol_record(
    symbol: str,
    *,
    path: Path,
    as_of: date | None,
    expected_latest_bar_date: date | None,
) -> tuple[dict[str, object], tuple[LocalDailyBar, ...]]:
    base = {
        "symbol": symbol,
        "data_path": str(path),
        "adjusted_close_basis": _ADJUSTED_CLOSE_BASIS,
        "requested_as_of": _date_text(as_of),
        "expected_latest_bar_date": _date_text(expected_latest_bar_date),
    }
    if not path.exists() or not path.is_file():
        return (
            {
                **base,
                "sha256": "",
                "row_count": 0,
                "source_total_row_count": 0,
                "earliest_date": "",
                "latest_date": "",
                "duplicate_date_status": "not_evaluated_missing_data",
                "validation_status": "missing_data",
                "data_availability_status": "missing_data",
                "data_refresh_status": "data_refresh_required",
                "freshness_status": "not_evaluated_missing_data",
                "validation_error": "canonical_adjusted_daily_csv_missing",
            },
            (),
        )

    try:
        csv_result = load_local_daily_bars_csv(path, symbol=symbol, as_of=as_of)
    except ValidationError as exc:
        return (
            {
                **base,
                "sha256": _sha256_file(path),
                "row_count": 0,
                "source_total_row_count": 0,
                "earliest_date": "",
                "latest_date": "",
                "duplicate_date_status": "not_evaluated_invalid_data",
                "validation_status": "invalid",
                "data_availability_status": "unavailable",
                "data_refresh_status": "data_refresh_required",
                "freshness_status": "not_evaluated_invalid_data",
                "validation_error": str(exc),
            },
            (),
        )

    usable_bars = csv_result.usable_bars
    if not usable_bars:
        return (
            {
                **base,
                "sha256": _sha256_file(path),
                "row_count": 0,
                "source_total_row_count": csv_result.total_row_count,
                "earliest_date": "",
                "latest_date": "",
                "duplicate_date_status": "no_duplicate_dates",
                "validation_status": "missing_data",
                "data_availability_status": "missing_data",
                "data_refresh_status": "data_refresh_required",
                "freshness_status": "not_evaluated_no_usable_bars",
                "validation_error": "no_usable_symbol_rows",
            },
            (),
        )

    latest_date = usable_bars[-1].date
    return (
        {
            **base,
            "sha256": _sha256_file(path),
            "row_count": len(usable_bars),
            "source_total_row_count": csv_result.total_row_count,
            "earliest_date": usable_bars[0].date.isoformat(),
            "latest_date": latest_date.isoformat(),
            "duplicate_date_status": "no_duplicate_dates",
            "validation_status": "valid",
            "data_availability_status": "available",
            "data_refresh_status": "not_required",
            "freshness_status": _freshness_status(latest_date, expected_latest_bar_date),
            "validation_error": "",
        },
        usable_bars,
    )


def _write_combined_canonical_csv(path: Path, bars: Sequence[LocalDailyBar]) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(bars, key=lambda item: (item.symbol, item.date))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(LOCAL_DAILY_BARS_CSV_COLUMNS)
        for bar in rows:
            writer.writerow(
                (
                    bar.symbol,
                    bar.date.isoformat(),
                    _decimal_text(bar.open),
                    _decimal_text(bar.high),
                    _decimal_text(bar.low),
                    _decimal_text(bar.close),
                    _decimal_text(bar.adjusted_close),
                    str(bar.volume),
                )
            )


def _freshness_status(latest_date: date, expected_latest_bar_date: date | None) -> str:
    if expected_latest_bar_date is None:
        return "not_evaluated"
    if latest_date >= expected_latest_bar_date:
        return "current"
    return "stale"


def _safety_payload() -> dict[str, object]:
    return {
        "research_only": True,
        "offline_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
    }


def _canonical_paths(
    value: Mapping[str, Path | str] | None,
    symbols: tuple[str, ...],
) -> dict[str, Path]:
    paths = dict(_DEFAULT_CANONICAL_PATHS)
    if value is not None:
        for raw_symbol, raw_path in value.items():
            symbol = _approved_symbol(raw_symbol)
            paths[symbol] = _csv_path(raw_path, f"canonical_paths[{symbol}]")
    return {symbol: _csv_path(paths[symbol], f"canonical_paths[{symbol}]") for symbol in symbols}


def _symbol_tuple(value: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_items = tuple(item for item in value.split(","))
    else:
        try:
            raw_items = tuple(value)
        except TypeError as exc:
            raise ValidationError("symbols must be a comma string or iterable.") from exc
    symbols: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        symbol = _approved_symbol(raw_item)
        if symbol in seen:
            continue
        symbols.append(symbol)
        seen.add(symbol)
    if not symbols:
        raise ValidationError("symbols must contain at least one symbol.")
    return tuple(symbols)


def _approved_symbol(value: object) -> str:
    text = _required_string(value, "symbol").upper()
    if text not in APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS:
        raise ValidationError(
            "symbol must be one of "
            + ",".join(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS)
            + "."
        )
    return text


def _config(value: object) -> MultiEtfAdjustedDataManifestConfig:
    if not isinstance(value, MultiEtfAdjustedDataManifestConfig):
        raise ValidationError("config must be a MultiEtfAdjustedDataManifestConfig.")
    return value


def _csv_path(value: Path | str, field_name: str) -> Path:
    path = _path(value, field_name)
    if path.suffix.lower() != ".csv":
        raise ValidationError(f"{field_name} must reference a CSV file.")
    return path


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        if "://" in value:
            raise ValidationError(f"{field_name} must be a local path.")
        path = Path(_required_string(value, field_name))
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _optional_date(value: date | str | None, field_name: str) -> date | None:
    if value is None:
        return None
    if type(value) is date:
        return value
    if isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a plain date.")
    if isinstance(value, str):
        text = _required_string(value, field_name)
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.") from exc
    raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.")


def _date_text(value: date | None) -> str:
    return "" if value is None else value.isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _decimal_text(value: object) -> str:
    return format(value, "f")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="multi-etf-adjusted-data-manifest")
    parser.add_argument("--output-manifest", default=str(_DEFAULT_OUTPUT_MANIFEST))
    parser.add_argument("--combined-output-csv", default=str(_DEFAULT_COMBINED_OUTPUT_CSV))
    parser.add_argument(
        "--symbols",
        default=",".join(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS),
        help="Comma-separated approved ETF symbols.",
    )
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--expected-latest-bar-date", default=None)
    parser.add_argument(
        "--canonical-path",
        action="append",
        default=(),
        help="Optional SYMBOL=path override. May be supplied more than once.",
    )
    return parser


def _canonical_path_overrides(values: Sequence[str]) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for value in values:
        text = _required_string(value, "canonical_path")
        if "=" not in text:
            raise ValidationError("canonical_path must use SYMBOL=path.")
        raw_symbol, raw_path = text.split("=", 1)
        overrides[_approved_symbol(raw_symbol)] = _csv_path(raw_path, "canonical_path")
    return overrides


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = run_multi_etf_adjusted_data_manifest(
            MultiEtfAdjustedDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
                symbols=args.symbols,
                canonical_paths=_canonical_path_overrides(args.canonical_path),
                as_of=args.as_of,
                expected_latest_bar_date=args.expected_latest_bar_date,
            )
        )
    except ValidationError as exc:
        print(f"multi_etf_adjusted_data_manifest_error: {exc}")
        return 2
    print("multi_etf_adjusted_data_manifest_status=completed")
    print(f"output_manifest={payload['output_manifest']}")
    print("valid_symbols=" + ",".join(str(item) for item in payload["valid_symbols"]))
    print(
        "refresh_required_symbols="
        + ",".join(str(item) for item in payload["refresh_required_symbols"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
