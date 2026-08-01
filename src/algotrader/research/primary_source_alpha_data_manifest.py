"""Outcome-blind canonical-data receipt builder for the V5.72 tournament."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    LocalDailyBar,
    load_local_daily_bars_csv,
)

__all__ = [
    "ALL_SYMBOLS",
    "CORE_SYMBOLS",
    "SECTOR_SYMBOLS",
    "PrimarySourceAlphaDataManifestConfig",
    "build_primary_source_alpha_data_manifest",
    "main",
]

CORE_SYMBOLS = ("SPY", "QQQ", "IWM", "TLT", "GLD")
SECTOR_SYMBOLS = ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY")
ALL_SYMBOLS = (*CORE_SYMBOLS, *SECTOR_SYMBOLS)

_START = date(2004, 11, 18)
_END = date(2026, 7, 31)
_PROTOCOL = Path("docs/design/v5_72_primary_source_alpha_tournament_preregistration.md")
_PROTOCOL_SHA256 = "eb3061e74f5444746d19480fc9283f3189b86ebb395369e9ee19a33f3dd8d768"
_PRIOR_DATA = Path("runs/v5_71_diversified_etf_absolute_trend/canonical_data.csv")
_PRIOR_DATA_SHA256 = "5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec"
_PRIOR_MANIFEST = Path(
    "runs/v5_71_diversified_etf_absolute_trend/data_acquisition/"
    "canonical_data_manifest.json"
)
_PRIOR_MANIFEST_SHA256 = "627119a769e38053c32ab7709f88672ab6dba5db9725cb4b2545a7bad77b177e"
_DEFAULT_ROOT = Path("runs/v5_72_primary_source_alpha_tournament")


@dataclass(frozen=True, slots=True)
class PrimarySourceAlphaDataManifestConfig:
    output_manifest: Path | str = _DEFAULT_ROOT / "canonical_data_manifest.json"
    combined_output_csv: Path | str = _DEFAULT_ROOT / "canonical_data.csv"
    prior_data: Path | str = _PRIOR_DATA
    prior_manifest: Path | str = _PRIOR_MANIFEST
    sector_root: Path | str = _DEFAULT_ROOT / "canonical_sectors"
    protocol_path: Path | str = _PROTOCOL
    expected_protocol_sha256: str = _PROTOCOL_SHA256
    expected_prior_data_sha256: str = _PRIOR_DATA_SHA256
    expected_prior_manifest_sha256: str = _PRIOR_MANIFEST_SHA256
    start: date = _START
    end: date = _END

    def __post_init__(self) -> None:
        for name in (
            "output_manifest",
            "combined_output_csv",
            "prior_data",
            "prior_manifest",
            "sector_root",
            "protocol_path",
        ):
            object.__setattr__(self, name, Path(getattr(self, name)))
        for name in (
            "expected_protocol_sha256",
            "expected_prior_data_sha256",
            "expected_prior_manifest_sha256",
        ):
            value = str(getattr(self, name)).strip().lower()
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValidationError(f"{name} must be a lowercase SHA-256 value.")
            object.__setattr__(self, name, value)
        if self.start >= self.end:
            raise ValidationError("start must precede end.")


def build_primary_source_alpha_data_manifest(
    config: PrimarySourceAlphaDataManifestConfig,
) -> dict[str, object]:
    """Validate exact source bytes and write one 14-symbol canonical snapshot."""

    pins = {
        "protocol": (config.protocol_path, config.expected_protocol_sha256),
        "prior_data": (config.prior_data, config.expected_prior_data_sha256),
        "prior_manifest": (
            config.prior_manifest,
            config.expected_prior_manifest_sha256,
        ),
    }
    actual_pins: dict[str, str] = {}
    for name, (path, expected) in pins.items():
        actual = _required_hash(path, name)
        if actual != expected:
            raise ValidationError(f"{name} SHA-256 does not match the frozen pin.")
        actual_pins[name] = actual

    bars_by_symbol: dict[str, tuple[LocalDailyBar, ...]] = {}
    records: list[dict[str, object]] = []
    for symbol in ALL_SYMBOLS:
        path = (
            config.prior_data
            if symbol in CORE_SYMBOLS
            else config.sector_root
            / f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv"
        )
        result = load_local_daily_bars_csv(path, symbol=symbol)
        bars = tuple(
            bar for bar in result.usable_bars if config.start <= bar.date <= config.end
        )
        if not bars:
            raise ValidationError(f"{symbol} has no admitted rows.")
        if bars[0].date != config.start or bars[-1].date != config.end:
            raise ValidationError(
                f"{symbol} must cover {config.start.isoformat()} through "
                f"{config.end.isoformat()} exactly."
            )
        dates = tuple(bar.date for bar in bars)
        if len(dates) != len(set(dates)):
            raise ValidationError(f"{symbol} contains duplicate dates.")
        bars_by_symbol[symbol] = bars
        records.append(
            {
                "symbol": symbol,
                "provider_symbol": symbol,
                "provider_symbol_mapping": f"{symbol}->{symbol}",
                "source_path": str(path),
                "source_file_sha256": _required_hash(path, symbol),
                "normalized_symbol_sha256": _symbol_hash(bars),
                "row_count": len(bars),
                "first_date": bars[0].date.isoformat(),
                "last_date": bars[-1].date.isoformat(),
                "validation_status": "valid",
            }
        )

    common_dates = tuple(bar.date for bar in bars_by_symbol[ALL_SYMBOLS[0]])
    for symbol in ALL_SYMBOLS[1:]:
        if tuple(bar.date for bar in bars_by_symbol[symbol]) != common_dates:
            raise ValidationError(f"{symbol} common-session sequence differs.")

    _write_combined(config.combined_output_csv, bars_by_symbol)
    payload: dict[str, object] = {
        "record_type": "primary_source_alpha_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_72_primary_source_alpha_tournament_v1",
        "symbols": list(ALL_SYMBOLS),
        "core_symbols": list(CORE_SYMBOLS),
        "sector_symbols": list(SECTOR_SYMBOLS),
        "provider": "tiingo_eod",
        "provider_field": "adjClose",
        "canonical_field": "adjusted_close",
        "adjustment_semantics": "provider_split_and_dividend_adjusted_close",
        "adjusted_ohlcv_claimed": False,
        "point_in_time_vintage_claimed": False,
        "execution_price_claimed": False,
        "start": config.start.isoformat(),
        "end": config.end.isoformat(),
        "common_session_count": len(common_dates),
        "common_first_session": common_dates[0].isoformat(),
        "common_last_session": common_dates[-1].isoformat(),
        "combined_row_count": sum(len(value) for value in bars_by_symbol.values()),
        "combined_output_csv": str(config.combined_output_csv),
        "combined_output_sha256": _required_hash(
            config.combined_output_csv, "combined_output_csv"
        ),
        "frozen_pins": actual_pins,
        "symbol_data": records,
        "safety": {
            "outcome_metrics_computed": False,
            "candidate_ranking_performed": False,
            "network_access_performed_by_manifest": False,
            "credential_access_performed_by_manifest": False,
            "broker_access_performed": False,
            "paper_mutation_performed": False,
            "live_authorized": False,
            "live_activity_performed": False,
        },
    }
    _write_json(config.output_manifest, payload)
    return payload


def _write_combined(
    path: Path,
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(LOCAL_DAILY_BARS_CSV_COLUMNS)
        for symbol in ALL_SYMBOLS:
            for bar in bars_by_symbol[symbol]:
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


def _symbol_hash(bars: tuple[LocalDailyBar, ...]) -> str:
    digest = hashlib.sha256()
    for bar in bars:
        digest.update(
            (
                f"{bar.symbol},{bar.date.isoformat()},{_decimal_text(bar.adjusted_close)}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def _decimal_text(value: object) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _required_hash(path: Path, label: str) -> str:
    if not path.is_file():
        raise ValidationError(f"{label} file is missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-manifest", default=str(_DEFAULT_ROOT / "canonical_data_manifest.json"))
    parser.add_argument("--combined-output-csv", default=str(_DEFAULT_ROOT / "canonical_data.csv"))
    parser.add_argument("--prior-data", default=str(_PRIOR_DATA))
    parser.add_argument("--prior-manifest", default=str(_PRIOR_MANIFEST))
    parser.add_argument("--sector-root", default=str(_DEFAULT_ROOT / "canonical_sectors"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_primary_source_alpha_data_manifest(
            PrimarySourceAlphaDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
                prior_data=args.prior_data,
                prior_manifest=args.prior_manifest,
                sector_root=args.sector_root,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"primary_source_alpha_data_manifest_status=blocked:{exc}")
        return 2
    print("primary_source_alpha_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
