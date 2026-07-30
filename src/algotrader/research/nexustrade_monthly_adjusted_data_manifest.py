"""Offline canonical-data contract for the NexusTrade monthly stock universe.

The module reads per-symbol Tiingo EOD canonical CSV files that were produced
by the repository's explicitly gated read-only market-data adapter.  It never
loads credentials or opens a network connection.  It verifies the exact
symbol/date contract, hashes every input, compares every symbol with SPY's
observed Tiingo EOD session set, and writes one deterministic combined CSV plus
one compact provenance manifest.
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import io
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
    "NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS",
    "NexusTradeMonthlyAdjustedDataManifestConfig",
    "TIINGO_PROVIDER_SYMBOL_BY_CANONICAL",
    "build_nexustrade_monthly_adjusted_data_manifest",
    "main",
    "run_nexustrade_monthly_adjusted_data_manifest",
]


NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS = (
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "GS",
    "JPM",
    "BRK-B",
    "COST",
    "SPY",
)
TIINGO_PROVIDER_SYMBOL_BY_CANONICAL = {
    symbol: symbol for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS
}

_RECORD_TYPE = "nexustrade_monthly_adjusted_data_manifest"
_SCHEMA_VERSION = "1"
_PROVIDER = "tiingo"
_REFERENCE_SYMBOL = "SPY"
_DEFAULT_DATA_START = date(2019, 1, 2)
_DEFAULT_TRAIN_START = date(2021, 12, 31)
_DEFAULT_TRAIN_END = date(2024, 3, 24)
_DEFAULT_OOS_START = date(2024, 3, 24)
_DEFAULT_OOS_END = date(2025, 3, 28)
_DEFAULT_MINIMUM_PRETRAINING_SESSIONS = 365
_DEFAULT_OUTPUT_MANIFEST = Path(
    "runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json"
)
_DEFAULT_COMBINED_OUTPUT_CSV = Path(
    "runs/operator_input/multi_etf_adjusted_daily_canonical.csv"
)
_TIINGO_EOD_DOCUMENTATION = "https://www.tiingo.com/documentation/end-of-day"
_TIINGO_SYMBOLOGY_DOCUMENTATION = "https://www.tiingo.com/documentation/general"
_HASH_CHUNK_SIZE = 1024 * 1024


def _default_canonical_paths() -> dict[str, Path]:
    return {
        symbol: (
            Path("runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv")
            if symbol == "SPY"
            else Path(
                "runs/operator_input/"
                f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv"
            )
        )
        for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS
    }


@dataclass(frozen=True, slots=True)
class NexusTradeMonthlyAdjustedDataManifestConfig:
    """Exact local data inputs and chronological coverage contract."""

    output_manifest: Path | str = _DEFAULT_OUTPUT_MANIFEST
    combined_output_csv: Path | str = _DEFAULT_COMBINED_OUTPUT_CSV
    canonical_paths: Mapping[str, Path | str] | None = None
    data_start: date | str = _DEFAULT_DATA_START
    train_start: date | str = _DEFAULT_TRAIN_START
    train_end: date | str = _DEFAULT_TRAIN_END
    oos_start: date | str = _DEFAULT_OOS_START
    oos_end: date | str = _DEFAULT_OOS_END
    minimum_pretraining_sessions: int = _DEFAULT_MINIMUM_PRETRAINING_SESSIONS
    run_id: str = "v5_63_nexustrade_canonical_data"

    def __post_init__(self) -> None:
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
        object.__setattr__(
            self,
            "canonical_paths",
            _canonical_paths(self.canonical_paths),
        )
        for field_name in (
            "data_start",
            "train_start",
            "train_end",
            "oos_start",
            "oos_end",
        ):
            object.__setattr__(
                self,
                field_name,
                _plain_date(getattr(self, field_name), field_name),
            )
        if not (
            self.data_start < self.train_start
            <= self.train_end
            <= self.oos_start
            <= self.oos_end
        ):
            raise ValidationError(
                "date contract must satisfy "
                "data_start < train_start <= train_end <= oos_start <= oos_end."
            )
        minimum = self.minimum_pretraining_sessions
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            raise ValidationError(
                "minimum_pretraining_sessions must be a positive integer."
            )
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))


def run_nexustrade_monthly_adjusted_data_manifest(
    config: NexusTradeMonthlyAdjustedDataManifestConfig,
) -> dict[str, object]:
    """Validate, write a combined CSV when complete, and persist the manifest."""

    checked = _config(config)
    payload, combined_bytes = _build_manifest_and_combined_bytes(checked)
    if combined_bytes is not None:
        _write_bytes_atomic(checked.combined_output_csv, combined_bytes)
        payload["combined_output_sha256"] = _sha256_bytes(combined_bytes)
        payload["combined_output_written"] = True
    _write_json_atomic(checked.output_manifest, payload)
    return payload


def build_nexustrade_monthly_adjusted_data_manifest(
    config: NexusTradeMonthlyAdjustedDataManifestConfig,
) -> dict[str, object]:
    """Build the deterministic manifest without writing files."""

    payload, _ = _build_manifest_and_combined_bytes(_config(config))
    return payload


def _build_manifest_and_combined_bytes(
    config: NexusTradeMonthlyAdjustedDataManifestConfig,
) -> tuple[dict[str, object], bytes | None]:
    loaded: dict[str, tuple[LocalDailyBar, ...]] = {}
    load_errors: dict[str, str] = {}
    input_hashes: dict[str, str] = {}

    for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS:
        path = config.canonical_paths[symbol]
        if not path.is_file():
            load_errors[symbol] = "canonical_adjusted_daily_csv_missing"
            input_hashes[symbol] = ""
            continue
        input_hashes[symbol] = _sha256_file(path)
        try:
            loaded[symbol] = load_local_daily_bars_csv(
                path,
                symbol=symbol,
                as_of=config.oos_end,
            ).usable_bars
        except ValidationError as exc:
            load_errors[symbol] = str(exc)

    reference_dates = _contract_dates(
        loaded.get(_REFERENCE_SYMBOL, ()),
        start=config.data_start,
        end=config.oos_end,
    )
    reference_date_set = set(reference_dates)
    reference_ready = bool(reference_dates)

    symbol_records: list[dict[str, object]] = []
    combined_bars: list[LocalDailyBar] = []
    for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS:
        bars = loaded.get(symbol, ())
        contract_bars = tuple(
            bar for bar in bars if config.data_start <= bar.date <= config.oos_end
        )
        dates = tuple(bar.date for bar in contract_bars)
        date_set = set(dates)
        missing_reference_dates = sorted(reference_date_set - date_set)
        unexpected_dates = sorted(date_set - reference_date_set)
        weekend_dates = tuple(value for value in dates if value.weekday() >= 5)
        pretraining_dates = tuple(value for value in dates if value < config.train_start)
        train_dates = tuple(
            value for value in dates if config.train_start <= value <= config.train_end
        )
        oos_dates = tuple(
            value for value in dates if config.oos_start <= value <= config.oos_end
        )
        calendar_warmup_start = config.train_start - timedelta(days=365)

        blockers: list[str] = []
        if symbol in load_errors:
            blockers.append(load_errors[symbol])
        if not contract_bars:
            blockers.append("no_rows_in_required_contract")
        if contract_bars and contract_bars[0].date > config.data_start:
            blockers.append("required_data_start_not_covered")
        if contract_bars and contract_bars[-1].date < config.oos_end:
            blockers.append("required_oos_end_not_covered")
        if not reference_ready:
            blockers.append("spy_reference_session_set_unavailable")
        if missing_reference_dates:
            blockers.append("missing_spy_reference_sessions")
        if unexpected_dates:
            blockers.append("unexpected_non_spy_reference_dates")
        if weekend_dates:
            blockers.append("weekend_rows_present")
        if len(pretraining_dates) < config.minimum_pretraining_sessions:
            blockers.append("insufficient_pretraining_sessions")
        if not contract_bars or contract_bars[0].date > calendar_warmup_start:
            blockers.append("insufficient_365_calendar_day_warmup_coverage")
        if not train_dates:
            blockers.append("source_training_window_has_no_sessions")
        if not oos_dates:
            blockers.append("source_oos_window_has_no_sessions")

        record = {
            "symbol": symbol,
            "provider_symbol": TIINGO_PROVIDER_SYMBOL_BY_CANONICAL[symbol],
            "provider_symbol_mapping": (
                f"{symbol}->{TIINGO_PROVIDER_SYMBOL_BY_CANONICAL[symbol]}"
            ),
            "canonical_path": str(config.canonical_paths[symbol]),
            "canonical_sha256": input_hashes.get(symbol, ""),
            "source_row_count_through_oos_end": len(bars),
            "contract_row_count": len(contract_bars),
            "earliest_contract_date": _first_date(dates),
            "latest_contract_date": _last_date(dates),
            "pretraining_session_count": len(pretraining_dates),
            "training_session_count": len(train_dates),
            "oos_session_count": len(oos_dates),
            "missing_reference_session_count": len(missing_reference_dates),
            "missing_reference_sessions": _date_list(missing_reference_dates),
            "unexpected_date_count": len(unexpected_dates),
            "unexpected_dates": _date_list(unexpected_dates),
            "weekend_row_count": len(weekend_dates),
            "supports_365_calendar_day_warmup": (
                bool(contract_bars)
                and contract_bars[0].date <= calendar_warmup_start
            ),
            "supports_minimum_pretraining_sessions": (
                len(pretraining_dates) >= config.minimum_pretraining_sessions
            ),
            "session_validation_status": (
                "matches_tiingo_spy_observed_sessions"
                if reference_ready
                and not missing_reference_dates
                and not unexpected_dates
                and not weekend_dates
                else "session_validation_failed"
            ),
            "validation_status": "valid" if not blockers else "blocked",
            "blockers": blockers,
        }
        symbol_records.append(record)
        if not blockers:
            combined_bars.extend(contract_bars)

    ready = all(record["validation_status"] == "valid" for record in symbol_records)
    combined_bytes = _serialize_combined_csv(combined_bars) if ready else None
    return (
        {
            "record_type": _RECORD_TYPE,
            "schema_version": _SCHEMA_VERSION,
            "run_id": config.run_id,
            "provider": _PROVIDER,
            "provider_documentation": {
                "eod_adjustment_semantics": _TIINGO_EOD_DOCUMENTATION,
                "symbology": _TIINGO_SYMBOLOGY_DOCUMENTATION,
            },
            "provider_adjustment_semantics": (
                "Tiingo EOD adjusted prices use the documented CRSP-standard "
                "method incorporating split and dividend adjustments."
            ),
            "canonical_price_field": "adjusted_close",
            "canonical_price_source_field": "adjClose",
            "raw_provider_fields_preserved": [
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
            "adjusted_ohlcv_claimed": False,
            "symbols": list(NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS),
            "provider_symbol_map": dict(TIINGO_PROVIDER_SYMBOL_BY_CANONICAL),
            "brk_b_mapping": "BRK-B->BRK-B",
            "data_start": config.data_start.isoformat(),
            "train_start": config.train_start.isoformat(),
            "train_end": config.train_end.isoformat(),
            "oos_start": config.oos_start.isoformat(),
            "oos_end": config.oos_end.isoformat(),
            "minimum_pretraining_sessions": config.minimum_pretraining_sessions,
            "authentic_indicator_warmup_semantics_resolved": False,
            "warmup_coverage_contract": (
                "data supports both at least 365 calendar days and at least "
                f"{config.minimum_pretraining_sessions} observed SPY sessions "
                "before source training; the source interpretation remains unknown"
            ),
            "session_reference_symbol": _REFERENCE_SYMBOL,
            "session_reference_basis": "Tiingo SPY observed EOD dates",
            "session_reference_start": _first_date(reference_dates),
            "session_reference_end": _last_date(reference_dates),
            "session_reference_count": len(reference_dates),
            "session_reference_ready": reference_ready,
            "canonical_data_ready": ready,
            "valid_symbols": [
                str(record["symbol"])
                for record in symbol_records
                if record["validation_status"] == "valid"
            ],
            "blocked_symbols": [
                str(record["symbol"])
                for record in symbol_records
                if record["validation_status"] != "valid"
            ],
            "symbol_data": symbol_records,
            "combined_output_csv": str(config.combined_output_csv),
            "combined_output_written": False,
            "combined_output_sha256": "",
            "combined_row_count": len(combined_bars) if ready else 0,
            "source_metrics_trust": "untrusted_external_evidence",
            "source_metrics_used_for_ranking": False,
            "source_metrics_used_for_promotion": False,
            "limitations": [
                "SPY observed Tiingo dates are the cross-symbol session reference; "
                "this artifact does not claim an independent official exchange calendar.",
                "The source historical bar mode, slippage assumption, and warm-up "
                "clock remain unresolved.",
            ],
            "safety": {
                "research_only": True,
                "offline_manifest_build": True,
                "network_access_attempted": False,
                "credential_access_attempted": False,
                "broker_access_attempted": False,
                "broker_mutation_performed": False,
                "paper_mutation_performed": False,
                "live_authorized": False,
                "profit_claim": "none",
            },
        },
        combined_bytes,
    )


def _canonical_paths(
    value: Mapping[str, Path | str] | None,
) -> dict[str, Path]:
    defaults = _default_canonical_paths()
    if value is None:
        return defaults
    if set(value) != set(NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS):
        raise ValidationError(
            "canonical_paths must contain exactly the NexusTrade monthly symbols."
        )
    return {
        symbol: _csv_path(value[symbol], f"canonical_paths[{symbol}]")
        for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS
    }


def _contract_dates(
    bars: Sequence[LocalDailyBar],
    *,
    start: date,
    end: date,
) -> tuple[date, ...]:
    return tuple(bar.date for bar in bars if start <= bar.date <= end)


def _serialize_combined_csv(bars: Sequence[LocalDailyBar]) -> bytes:
    symbol_rank = {
        symbol: index
        for index, symbol in enumerate(NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS)
    }
    ordered = sorted(bars, key=lambda bar: (symbol_rank[bar.symbol], bar.date))
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(LOCAL_DAILY_BARS_CSV_COLUMNS)
    for bar in ordered:
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
    return stream.getvalue().encode("utf-8")


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    data = (
        json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    _write_bytes_atomic(path, data)


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _first_date(values: Sequence[date]) -> str:
    return values[0].isoformat() if values else ""


def _last_date(values: Sequence[date]) -> str:
    return values[-1].isoformat() if values else ""


def _date_list(values: Sequence[date]) -> list[str]:
    return [value.isoformat() for value in values]


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _config(
    value: object,
) -> NexusTradeMonthlyAdjustedDataManifestConfig:
    if not isinstance(value, NexusTradeMonthlyAdjustedDataManifestConfig):
        raise ValidationError(
            "config must be a NexusTradeMonthlyAdjustedDataManifestConfig."
        )
    return value


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str) and "://" not in value:
        path = Path(_required_string(value, field_name))
    else:
        raise ValidationError(f"{field_name} must be a local path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _csv_path(value: Path | str, field_name: str) -> Path:
    path = _path(value, field_name)
    if path.suffix.lower() != ".csv":
        raise ValidationError(f"{field_name} must reference a CSV file.")
    return path


def _plain_date(value: date | str, field_name: str) -> date:
    if type(value) is date:
        return value
    if isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a plain date.")
    if isinstance(value, str):
        text = _required_string(value, field_name)
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(
                f"{field_name} must be a YYYY-MM-DD date."
            ) from exc
    raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.")


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


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
    parser = argparse.ArgumentParser(
        prog="python -m "
        "algotrader.research.nexustrade_monthly_adjusted_data_manifest"
    )
    parser.add_argument("--output-manifest", default=str(_DEFAULT_OUTPUT_MANIFEST))
    parser.add_argument(
        "--combined-output-csv",
        default=str(_DEFAULT_COMBINED_OUTPUT_CSV),
    )
    parser.add_argument("--data-start", default=_DEFAULT_DATA_START.isoformat())
    parser.add_argument("--train-start", default=_DEFAULT_TRAIN_START.isoformat())
    parser.add_argument("--train-end", default=_DEFAULT_TRAIN_END.isoformat())
    parser.add_argument("--oos-start", default=_DEFAULT_OOS_START.isoformat())
    parser.add_argument("--oos-end", default=_DEFAULT_OOS_END.isoformat())
    parser.add_argument(
        "--minimum-pretraining-sessions",
        type=int,
        default=_DEFAULT_MINIMUM_PRETRAINING_SESSIONS,
    )
    parser.add_argument(
        "--canonical-path",
        action="append",
        default=[],
        help="Optional SYMBOL=path override; supply all twelve symbols or none.",
    )
    return parser


def _canonical_path_overrides(values: Sequence[str]) -> Mapping[str, Path] | None:
    if not values:
        return None
    paths: dict[str, Path] = {}
    for value in values:
        text = _required_string(value, "canonical_path")
        if "=" not in text:
            raise ValidationError("canonical_path must use SYMBOL=path.")
        symbol, raw_path = text.split("=", 1)
        checked_symbol = symbol.strip().upper()
        if checked_symbol not in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS:
            raise ValidationError("canonical_path symbol is not approved.")
        if checked_symbol in paths:
            raise ValidationError("canonical_path symbols must be unique.")
        paths[checked_symbol] = _csv_path(raw_path, "canonical_path")
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = run_nexustrade_monthly_adjusted_data_manifest(
            NexusTradeMonthlyAdjustedDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
                canonical_paths=_canonical_path_overrides(args.canonical_path),
                data_start=args.data_start,
                train_start=args.train_start,
                train_end=args.train_end,
                oos_start=args.oos_start,
                oos_end=args.oos_end,
                minimum_pretraining_sessions=args.minimum_pretraining_sessions,
            )
        )
    except ValidationError as exc:
        print(f"nexustrade_monthly_adjusted_data_manifest_error: {exc}")
        return 2
    print(
        "nexustrade_monthly_adjusted_data_manifest_status="
        + ("ready" if payload["canonical_data_ready"] else "blocked")
    )
    print("valid_symbols=" + ",".join(str(item) for item in payload["valid_symbols"]))
    print(
        "blocked_symbols="
        + ",".join(str(item) for item in payload["blocked_symbols"])
    )
    return 0 if payload["canonical_data_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
