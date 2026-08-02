"""Outcome-blind canonical-data receipt builder for V5.84."""

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
    "RISK_SYMBOLS",
    "FactorMomentumStyleDataManifestConfig",
    "build_factor_momentum_style_data_manifest",
    "main",
]

RISK_SYMBOLS = ("IWD", "IWF", "RSP", "VBR", "VIG", "SPLV")
ALL_SYMBOLS = (*RISK_SYMBOLS, "SHY", "SPY", "IEF")
_START = date(2011, 5, 5)
_END = date(2026, 7, 31)
_PROTOCOL = Path("docs/design/v5_84_factor_style_ensemble_preregistration.md")
_PROTOCOL_SHA256 = "3ec0d6359cb4280e24a60fab8a9c04a18ac727f231fb89bd3526a9f0c4aa8361"
_DEFAULT_ROOT = Path("runs/v5_84_factor_momentum_style_proxy")


@dataclass(frozen=True, slots=True)
class FactorMomentumStyleDataManifestConfig:
    output_manifest: Path | str = _DEFAULT_ROOT / "canonical_data_manifest.json"
    combined_output_csv: Path | str = _DEFAULT_ROOT / "canonical_data.csv"
    canonical_root: Path | str = _DEFAULT_ROOT / "canonical_symbols"
    acquisition_root: Path | str = _DEFAULT_ROOT / "data_acquisition"
    protocol_path: Path | str = _PROTOCOL
    expected_protocol_sha256: str = _PROTOCOL_SHA256
    start: date = _START
    end: date = _END

    def __post_init__(self) -> None:
        for name in (
            "output_manifest",
            "combined_output_csv",
            "canonical_root",
            "acquisition_root",
            "protocol_path",
        ):
            object.__setattr__(self, name, Path(getattr(self, name)))
        value = str(self.expected_protocol_sha256).strip().lower()
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValidationError("expected_protocol_sha256 must be lowercase SHA-256.")
        object.__setattr__(self, "expected_protocol_sha256", value)
        if self.start >= self.end:
            raise ValidationError("start must precede end.")


def build_factor_momentum_style_data_manifest(
    config: FactorMomentumStyleDataManifestConfig,
) -> dict[str, object]:
    """Validate exact Tiingo receipts and write one common-session snapshot."""

    protocol_hash = _required_hash(config.protocol_path, "protocol")
    if protocol_hash != config.expected_protocol_sha256:
        raise ValidationError("protocol SHA-256 does not match the frozen pin.")

    bars_by_symbol: dict[str, tuple[LocalDailyBar, ...]] = {}
    records: list[dict[str, object]] = []
    for symbol in ALL_SYMBOLS:
        stem = symbol.lower()
        data_path = config.canonical_root / f"{stem}_daily_tiingo_adjusted_canonical.csv"
        log_path = config.acquisition_root / f"{stem}_refresh_manifest.jsonl"
        data_hash = _required_hash(data_path, symbol)
        log_hash = _required_hash(log_path, f"{symbol} refresh log")
        receipt = _last_json_record(log_path, symbol)
        _validate_refresh_receipt(receipt, symbol, data_hash, config)

        loaded = load_local_daily_bars_csv(data_path, symbol=symbol)
        bars = tuple(
            bar for bar in loaded.usable_bars if config.start <= bar.date <= config.end
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
                "source_path": str(data_path),
                "source_file_sha256": data_hash,
                "source_refresh_log": str(log_path),
                "source_refresh_log_sha256": log_hash,
                "raw_provider_response_path": str(receipt["raw_provider_response_path"]),
                "raw_provider_response_sha256": str(receipt["source_sha256"]),
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
        "record_type": "factor_momentum_style_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_84_factor_momentum_style_proxy_v1",
        "symbols": list(ALL_SYMBOLS),
        "risk_symbols": list(RISK_SYMBOLS),
        "defensive_symbol": "SHY",
        "baseline_symbols": ["SPY", "IEF"],
        "provider": "tiingo_eod",
        "provider_field": "adjClose",
        "canonical_field": "adjusted_close",
        "adjustment_semantics": "provider_split_and_dividend_adjusted_close",
        "adjusted_ohlcv_claimed": False,
        "point_in_time_vintage_claimed": False,
        "execution_price_claimed": False,
        "requested_start": config.start.isoformat(),
        "requested_end": config.end.isoformat(),
        "common_session_count": len(common_dates),
        "common_first_session": common_dates[0].isoformat(),
        "common_last_session": common_dates[-1].isoformat(),
        "combined_row_count": sum(len(value) for value in bars_by_symbol.values()),
        "combined_output_csv": str(config.combined_output_csv),
        "combined_output_sha256": _required_hash(
            config.combined_output_csv, "combined output"
        ),
        "frozen_pins": {"protocol": protocol_hash},
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


def _validate_refresh_receipt(
    receipt: Mapping[str, object],
    symbol: str,
    data_hash: str,
    config: FactorMomentumStyleDataManifestConfig,
) -> None:
    required = {
        "provider": "tiingo",
        "symbol": symbol,
        "mode": "live_market_data_fetch",
        "refresh_state": "accepted_adjusted_spy_data_refresh",
        "request_start_date": config.start.isoformat(),
        "request_end_date": config.end.isoformat(),
        "date_range_start": config.start.isoformat(),
        "date_range_end": config.end.isoformat(),
        "canonical_csv_sha256": data_hash,
        "http_outcome_category": "success",
        "market_data_token_env_var": "TIINGO_API_KEY",
    }
    for field, expected in required.items():
        if receipt.get(field) != expected:
            raise ValidationError(f"{symbol} refresh receipt {field} mismatch.")
    if receipt.get("network_method_allowlist") != ["GET"]:
        raise ValidationError(f"{symbol} refresh receipt method is not GET-only.")
    if receipt.get("network_destination_allowlist_enforced") is not True:
        raise ValidationError(f"{symbol} destination allowlist was not enforced.")
    mapping = receipt.get("provider_column_mapping")
    if not isinstance(mapping, Mapping) or mapping.get("adjusted_close") != "adjClose":
        raise ValidationError(f"{symbol} adjusted-close mapping mismatch.")
    for field in (
        "token_value_recorded",
        "market_data_token_value_printed",
        "market_data_token_value_written",
        "broker_credential_lookup_attempted",
        "broker_access_attempted",
        "broker_mutation_attempted",
        "paper_submit_attempted",
        "live_authorized",
    ):
        if receipt.get(field) is not False:
            raise ValidationError(f"{symbol} unsafe receipt field: {field}.")
    raw_path = Path(str(receipt.get("raw_provider_response_path", "")))
    if _required_hash(raw_path, f"{symbol} raw response") != receipt.get("source_sha256"):
        raise ValidationError(f"{symbol} raw response SHA-256 mismatch.")


def _last_json_record(path: Path, symbol: str) -> Mapping[str, object]:
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
        payload = json.loads(lines[-1])
    except (IndexError, OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{symbol} refresh log is invalid.") from exc
    if not isinstance(payload, Mapping):
        raise ValidationError(f"{symbol} refresh log record is invalid.")
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
            f"{bar.symbol},{bar.date.isoformat()},{_decimal_text(bar.adjusted_close)}\n".encode()
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    parser.add_argument("--canonical-root", default=str(_DEFAULT_ROOT / "canonical_symbols"))
    parser.add_argument("--acquisition-root", default=str(_DEFAULT_ROOT / "data_acquisition"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_factor_momentum_style_data_manifest(
            FactorMomentumStyleDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
                canonical_root=args.canonical_root,
                acquisition_root=args.acquisition_root,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"factor_momentum_style_data_manifest_status=blocked:{exc}")
        return 2
    print("factor_momentum_style_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
