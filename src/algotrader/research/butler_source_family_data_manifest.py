"""Outcome-blind canonical-data admission for the V5.88 Butler source family."""

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
    "CANDIDATE_SYMBOLS",
    "DEFAULT_SOURCES",
    "ButlerSourceFamilyDataManifestConfig",
    "SymbolSourceSpec",
    "build_butler_source_family_data_manifest",
    "main",
]

CANDIDATE_SYMBOLS = (
    "DBC", "EEM", "EWJ", "GLD", "ICF", "IEF", "RWX", "TLT", "VGK", "VTI",
)
ALL_SYMBOLS = (*CANDIDATE_SYMBOLS, "SPY")
_START = date(2007, 7, 26)
_END = date(2026, 7, 31)
_PROTOCOL = Path(
    "docs/design/v5_88_butler_exhibit3_4_source_family_preregistration.md"
)
_PROTOCOL_SHA256 = "fecab8bc4233afc71fd95324c913a0380b72607e14232f2e20663327b27fa0ff"
_DEFAULT_ROOT = Path("runs/v5_88_butler_exhibit3_4_source_family")


@dataclass(frozen=True, slots=True)
class SymbolSourceSpec:
    symbol: str
    source_path: Path | str
    source_sha256: str
    provenance_kind: str
    evidence_path: Path | str
    evidence_sha256: str
    raw_response_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        object.__setattr__(self, "source_path", Path(self.source_path))
        object.__setattr__(self, "evidence_path", Path(self.evidence_path))
        for name in ("source_sha256", "evidence_sha256", "raw_response_sha256"):
            value = getattr(self, name)
            if value is not None:
                normalized = str(value).strip().lower()
                if len(normalized) != 64 or any(
                    char not in "0123456789abcdef" for char in normalized
                ):
                    raise ValidationError(f"{name} must be lowercase SHA-256.")
                object.__setattr__(self, name, normalized)
        if self.provenance_kind not in {"prior_receipt", "new_refresh"}:
            raise ValidationError("provenance_kind must be prior_receipt or new_refresh.")
        if (self.provenance_kind == "new_refresh") != (
            self.raw_response_sha256 is not None
        ):
            raise ValidationError("only a new refresh may pin a raw response.")


def _prior(
    symbol: str,
    source_path: str,
    source_hash: str,
    receipt_path: str,
    receipt_hash: str,
) -> SymbolSourceSpec:
    return SymbolSourceSpec(
        symbol, source_path, source_hash, "prior_receipt", receipt_path, receipt_hash
    )


def _new(
    symbol: str, source_hash: str, refresh_hash: str, raw_hash: str
) -> SymbolSourceSpec:
    stem = symbol.lower()
    return SymbolSourceSpec(
        symbol,
        _DEFAULT_ROOT / "canonical" / f"{stem}_daily_tiingo_adjusted_canonical.csv",
        source_hash,
        "new_refresh",
        _DEFAULT_ROOT / "data_acquisition" / f"{stem}_refresh_manifest.jsonl",
        refresh_hash,
        raw_hash,
    )


DEFAULT_SOURCES = (
    _prior(
        "DBC",
        "runs/v5_75_faber_global_relative_strength/canonical/dbc_daily_tiingo_adjusted_canonical.csv",
        "8720fa2256e971ae5004b5fb92d095d699d122fe68d51f37d61a9665cb8054b1",
        "docs/design/v5_75_faber_global_relative_strength_data_receipt.md",
        "5e99265971996f1821f384bb8121a8b8252b73bdef27b3bd9b215bceeff4f2e7",
    ),
    _new(
        "EEM",
        "91399fabb12e98237f6cf245b8a3212b9f8ed046dfb53b75d44ffd6d712aa698",
        "513bd730d72960c64220f82faea6ade2590b6269449b76e0a3dc93b15535f0ba",
        "39a28911a912dbf545324760612de123f518b63f6e9e5c77c8bbc93a5c392207",
    ),
    _new(
        "EWJ",
        "b6686f3ff8510c80b721a839f2488a656986c705a72c58cfa4c3d41548632eba",
        "c7c10f624d27728df9f325de96b765b4faa33b9cf95ad61d576fa1734f4cf9d2",
        "0cfe38bc81f4152d0b3b8da5b8e5b085da93536bc09b50d8a12a27f86c3f3d01",
    ),
    _prior(
        "GLD",
        "runs/v5_71_diversified_etf_absolute_trend/data_acquisition/canonical/gld_daily_tiingo_adjusted_canonical.csv",
        "1986eef43145ea6ae1f51cbc7decfb9d711bd740b18d207bd6ecc50a4e86f88e",
        "docs/design/v5_71_diversified_etf_absolute_trend_data_receipt.md",
        "ca782882cb499ea2e956fc36658df4f76f88fff06b4a69b293ced4a70c213525",
    ),
    _new(
        "ICF",
        "87edf99724c815051ce0b5fbeebc69300c18f3f7e2364be9d716bab61020f0c2",
        "a42bf38ff50abb01176c096c7c778b3fd26ac615950487262c3e4272535e8556",
        "6aa8dfe2560ae8e6c5a40977b2672221414f7fbdb55141c49ee183c4abb2cfbf",
    ),
    _prior(
        "IEF",
        "runs/v5_74_vigilant_asset_allocation_g4/canonical/ief_daily_tiingo_adjusted_canonical.csv",
        "091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f",
        "docs/design/v5_74_vigilant_asset_allocation_g4_data_receipt.md",
        "59595161f75c4b5e85a261d281cb722d596f95869e2b943940da010ce925b37f",
    ),
    _new(
        "RWX",
        "da397276843490828bb7d0bc1d9a467f84b95f3f4998f3e855eaec19aa6bdc50",
        "388bc760208c2c150951b35774307ceb3b578e1a3e39a893316f6ee2d75475d6",
        "f41ff68985cf50fa4639b20af21804ba2cdfa90431d4d6b629916f1755646554",
    ),
    _prior(
        "TLT",
        "runs/v5_71_diversified_etf_absolute_trend/data_acquisition/canonical/tlt_daily_tiingo_adjusted_canonical.csv",
        "5ce0e67de4c1be5e5e85b292444bc5aac0ce937587a7fc60ca00e402f67dbfae",
        "docs/design/v5_71_diversified_etf_absolute_trend_data_receipt.md",
        "ca782882cb499ea2e956fc36658df4f76f88fff06b4a69b293ced4a70c213525",
    ),
    _new(
        "VGK",
        "6238676b6bface8c8154ab414d7028ab312a1ac94f23f761f4ecd91e0b6c412f",
        "87cba5e33cf1024c58ed954086d140499d555e6990344d96b6dc965f17e8da0f",
        "f368ea42889510781d030c53ea7f48e1127617d98d48335175074e7d9ffca691",
    ),
    _prior(
        "VTI",
        "runs/v5_87_keller_flexible_asset_allocation/canonical/vti_daily_tiingo_adjusted_canonical.csv",
        "e8af3a7ea965e72861210be889b390b046684c1f82fff14f94274b453df1af47",
        "docs/design/v5_87_keller_flexible_asset_allocation_data_receipt.md",
        "c338615d6079557b3a5d98dd0414cef7a15f03e06812841af5ddadb63f30fa60",
    ),
    _prior(
        "SPY",
        "runs/v5_71_diversified_etf_absolute_trend/data_acquisition/canonical/spy_daily_tiingo_adjusted_canonical.csv",
        "9ba2d58f5c1c58096fd473eaad1ea370e6023c63b524a21d286e4d5effaef5fb",
        "docs/design/v5_71_diversified_etf_absolute_trend_data_receipt.md",
        "ca782882cb499ea2e956fc36658df4f76f88fff06b4a69b293ced4a70c213525",
    ),
)


@dataclass(frozen=True, slots=True)
class ButlerSourceFamilyDataManifestConfig:
    output_manifest: Path | str = _DEFAULT_ROOT / "canonical_data_manifest.json"
    combined_output_csv: Path | str = _DEFAULT_ROOT / "canonical_data.csv"
    protocol_path: Path | str = _PROTOCOL
    expected_protocol_sha256: str = _PROTOCOL_SHA256
    sources: tuple[SymbolSourceSpec, ...] = DEFAULT_SOURCES
    start: date = _START
    end: date = _END

    def __post_init__(self) -> None:
        for name in ("output_manifest", "combined_output_csv", "protocol_path"):
            object.__setattr__(self, name, Path(getattr(self, name)))
        object.__setattr__(
            self,
            "expected_protocol_sha256",
            _validated_sha(self.expected_protocol_sha256, "expected_protocol_sha256"),
        )
        object.__setattr__(self, "sources", tuple(self.sources))
        if tuple(source.symbol for source in self.sources) != ALL_SYMBOLS:
            raise ValidationError("sources must match the frozen symbol order exactly.")
        if self.start >= self.end:
            raise ValidationError("start must precede end.")


def build_butler_source_family_data_manifest(
    config: ButlerSourceFamilyDataManifestConfig,
) -> dict[str, object]:
    """Validate pinned provenance and write the exact common-session panel."""

    protocol_hash = _required_hash(config.protocol_path, "protocol")
    if protocol_hash != config.expected_protocol_sha256:
        raise ValidationError("protocol SHA-256 does not match the frozen pin.")

    bars_by_symbol: dict[str, tuple[LocalDailyBar, ...]] = {}
    records: list[dict[str, object]] = []
    for source in config.sources:
        source_hash = _required_hash(source.source_path, source.symbol)
        if source_hash != source.source_sha256:
            raise ValidationError(f"{source.symbol} source SHA-256 mismatch.")

        if source.provenance_kind == "new_refresh":
            provenance = _validate_refresh(source, source_hash, config)
        else:
            evidence_hash = _required_hash(
                source.evidence_path, f"{source.symbol} provenance receipt"
            )
            if evidence_hash != source.evidence_sha256:
                raise ValidationError(
                    f"{source.symbol} provenance receipt SHA-256 mismatch."
                )
            provenance = {
                "source_kind": "reused_prior_canonical_evidence",
                "provenance_receipt_path": str(source.evidence_path),
                "provenance_receipt_sha256": evidence_hash,
            }

        loaded = load_local_daily_bars_csv(source.source_path, symbol=source.symbol)
        bars = tuple(
            bar for bar in loaded.usable_bars if config.start <= bar.date <= config.end
        )
        if not bars:
            raise ValidationError(f"{source.symbol} has no admitted rows.")
        if bars[0].date != config.start or bars[-1].date != config.end:
            raise ValidationError(
                f"{source.symbol} must cover {config.start.isoformat()} through "
                f"{config.end.isoformat()} exactly."
            )
        dates = tuple(bar.date for bar in bars)
        if len(dates) != len(set(dates)):
            raise ValidationError(f"{source.symbol} contains duplicate dates.")
        if any(bar.adjusted_close <= 0 for bar in bars):
            raise ValidationError(
                f"{source.symbol} contains nonpositive adjusted close."
            )
        bars_by_symbol[source.symbol] = bars
        records.append(
            {
                "symbol": source.symbol,
                "provider_symbol": source.symbol,
                "provider_symbol_mapping": f"{source.symbol}->{source.symbol}",
                "source_path": str(source.source_path),
                "source_file_sha256": source_hash,
                "normalized_symbol_sha256": _symbol_hash(bars),
                "row_count": len(bars),
                "first_date": bars[0].date.isoformat(),
                "last_date": bars[-1].date.isoformat(),
                "validation_status": "valid",
                **provenance,
            }
        )

    common_dates = tuple(bar.date for bar in bars_by_symbol[ALL_SYMBOLS[0]])
    for symbol in ALL_SYMBOLS[1:]:
        if tuple(bar.date for bar in bars_by_symbol[symbol]) != common_dates:
            raise ValidationError(f"{symbol} common-session sequence differs.")

    _write_combined(config.combined_output_csv, bars_by_symbol)
    payload: dict[str, object] = {
        "record_type": "butler_exhibit3_4_source_family_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_88_butler_exhibit3_4_source_family_v2",
        "symbols": list(ALL_SYMBOLS),
        "candidate_symbols": list(CANDIDATE_SYMBOLS),
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


def _validate_refresh(
    source: SymbolSourceSpec,
    source_hash: str,
    config: ButlerSourceFamilyDataManifestConfig,
) -> dict[str, object]:
    log_hash = _required_hash(source.evidence_path, f"{source.symbol} refresh log")
    if log_hash != source.evidence_sha256:
        raise ValidationError(f"{source.symbol} refresh log SHA-256 mismatch.")
    receipt = _last_json_record(source.evidence_path, source.symbol)
    required = {
        "provider": "tiingo",
        "symbol": source.symbol,
        "mode": "live_market_data_fetch",
        "refresh_state": "accepted_adjusted_spy_data_refresh",
        "request_start_date": config.start.isoformat(),
        "request_end_date": config.end.isoformat(),
        "date_range_start": config.start.isoformat(),
        "date_range_end": config.end.isoformat(),
        "canonical_csv_sha256": source_hash,
        "http_outcome_category": "success",
        "market_data_token_env_var": "TIINGO_API_KEY",
        "source_sha256": source.raw_response_sha256,
    }
    for field, expected in required.items():
        if receipt.get(field) != expected:
            raise ValidationError(
                f"{source.symbol} refresh receipt {field} mismatch."
            )
    if receipt.get("network_method_allowlist") != ["GET"]:
        raise ValidationError(f"{source.symbol} refresh receipt method is not GET-only.")
    if receipt.get("network_destination_allowlist_enforced") is not True:
        raise ValidationError(
            f"{source.symbol} destination allowlist was not enforced."
        )
    mapping = receipt.get("provider_column_mapping")
    if not isinstance(mapping, Mapping) or mapping.get("adjusted_close") != "adjClose":
        raise ValidationError(f"{source.symbol} adjusted-close mapping mismatch.")
    request = receipt.get("provider_request")
    request_required = {
        "method": "GET",
        "scheme": "https",
        "destination_host": "api.tiingo.com",
        "provider_symbol": source.symbol,
        "provider_symbol_mapping": f"{source.symbol}->{source.symbol}",
        "request_start_date": config.start.isoformat(),
        "request_end_date": config.end.isoformat(),
        "destination_allowlist_match": True,
    }
    if not isinstance(request, Mapping):
        raise ValidationError(f"{source.symbol} provider request is missing.")
    for field, expected in request_required.items():
        if request.get(field) != expected:
            raise ValidationError(
                f"{source.symbol} provider request {field} mismatch."
            )
    for field in (
        "token_value_recorded",
        "market_data_token_value_printed",
        "market_data_token_value_written",
        "broker_credential_lookup_attempted",
        "broker_access_attempted",
        "broker_mutation_attempted",
        "paper_submit_attempted",
        "live_authorized",
        "live_trading_performed",
    ):
        if receipt.get(field) is not False:
            raise ValidationError(f"{source.symbol} unsafe receipt field: {field}.")
    raw_path = Path(str(receipt.get("raw_provider_response_path", "")))
    raw_hash = _required_hash(raw_path, f"{source.symbol} raw response")
    if raw_hash != source.raw_response_sha256:
        raise ValidationError(f"{source.symbol} raw response SHA-256 mismatch.")
    return {
        "source_kind": "candidate_specific_authenticated_acquisition",
        "source_refresh_log": str(source.evidence_path),
        "source_refresh_log_sha256": log_hash,
        "raw_provider_response_path": str(raw_path),
        "raw_provider_response_sha256": raw_hash,
    }


def _last_json_record(path: Path, symbol: str) -> Mapping[str, object]:
    try:
        lines = [
            line for line in path.read_text(encoding="utf-8").splitlines() if line
        ]
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


def _validated_sha(value: object, label: str) -> str:
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        raise ValidationError(f"{label} must be lowercase SHA-256.")
    return normalized


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
    parser.add_argument(
        "--output-manifest",
        default=str(_DEFAULT_ROOT / "canonical_data_manifest.json"),
    )
    parser.add_argument(
        "--combined-output-csv",
        default=str(_DEFAULT_ROOT / "canonical_data.csv"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_butler_source_family_data_manifest(
            ButlerSourceFamilyDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"butler_source_family_data_manifest_status=blocked:{exc}")
        return 2
    print("butler_source_family_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())