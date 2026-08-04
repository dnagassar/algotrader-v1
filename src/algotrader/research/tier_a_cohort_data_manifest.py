"""Outcome-blind canonical-data admission for the V5.96 Tier A cohort."""

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
    "MINIMUM_COMMON_SESSIONS",
    "DEFAULT_SOURCES",
    "TierACohortDataManifestConfig",
    "SymbolSourceSpec",
    "build_tier_a_cohort_data_manifest",
    "main",
]

ALL_SYMBOLS = (
    "VGLT", "EDV", "GOVT", "USMV", "SPHD", "NOBL",
    "VCSH", "BKLN", "FLOT", "MTUM", "SMH", "VBK", "SPY",
)
MINIMUM_COMMON_SESSIONS = 2600
_START = date(2005, 1, 3)
_END = date(2026, 7, 31)
_PROTOCOL = Path(
    "docs/design/v5_96_tier_a_component_cohort_preregistration.md"
)
_PROTOCOL_SHA256 = "8e8b3bdcce81ad93f6787ee2a6081855ef92bb94f299bd416a75be556d4f6fcb"
_DEFAULT_ROOT = Path("runs/v5_96_tier_a_component_cohort")


@dataclass(frozen=True, slots=True)
class SymbolSourceSpec:
    symbol: str
    source_path: Path | str
    source_sha256: str
    evidence_path: Path | str
    evidence_sha256: str
    raw_response_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        object.__setattr__(self, "source_path", Path(self.source_path))
        object.__setattr__(self, "evidence_path", Path(self.evidence_path))
        for name in ("source_sha256", "evidence_sha256", "raw_response_sha256"):
            value = str(getattr(self, name)).strip().lower()
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value
            ):
                raise ValidationError(f"{name} must be lowercase SHA-256.")
            object.__setattr__(self, name, value)


def _new(
    symbol: str, source_hash: str, refresh_hash: str, raw_hash: str
) -> SymbolSourceSpec:
    stem = symbol.lower()
    return SymbolSourceSpec(
        symbol,
        _DEFAULT_ROOT / "canonical" / f"{stem}_daily_tiingo_adjusted_canonical.csv",
        source_hash,
        _DEFAULT_ROOT / "data_acquisition" / f"{stem}_refresh_manifest.jsonl",
        refresh_hash,
        raw_hash,
    )


DEFAULT_SOURCES = (
    _new(
        "VGLT",
        "833783cf2de8975a0577b69d814d6f8581fbbe7a2cb3f8dcf0d173bf8f4bc3a4",
        "4a589d181669474d9318d77c6e6231bd88466d9350fd5c90ec4f4aa450f1174d",
        "25f37ef1e62157f7dd90a4b7e393f3376c55eedd1d8efabdf29b8269a0b56fcf",
    ),
    _new(
        "EDV",
        "f8460369f8b1537293e2daa8b02f8533ba12b13f4da02d304ae231d6700d8d04",
        "6d04657233cc1f1f34524f99e1f8582ed71f7bbe2d6a3b2849ff822f59c78567",
        "25e30d6509f22510d7bb390ad77fcc05f8f1eef49fa8927971aa1a88d2c734ad",
    ),
    _new(
        "GOVT",
        "a632c06840ee43bef738fffa345c5de90790dd4c148e37477a1222c67d010c31",
        "182ba330cf2e1679d01105c60741569e4f53520fcf98ba49bd28beb5f0555be5",
        "cdf83a2f2dca4449d87567b3e56ce8a343ef42de78d5793a3d394f219ea0ed53",
    ),
    _new(
        "USMV",
        "0644b45534dae6f9f64639a52d8c67e380ee6ca250a7fe466e07d6af3a185e14",
        "47f045dafd433844defcf8d669804224116e91dded29f85b4fe3bf0111cf0b3e",
        "dd92712bd21491cffe028d188251c350065e1dbbb055e6b400d55f795d861e96",
    ),
    _new(
        "SPHD",
        "cff256bdff29e08343cb7f736cf04641b8adc1acbb76ac71aa43c52052f4ed4b",
        "e8b40f4c2e4aead35e7458e1bda38523abb03868cfe48d8b3e34a59a85fcf520",
        "b1617c7fff7e8c2c64d86fd364920d9750c38cd130d207dbc43672b1215d5ff1",
    ),
    _new(
        "NOBL",
        "83d9a504398664bd746005cccb6358923d18abfd24d1430bbc1439a54166c162",
        "36780addc036151e470cc4b7ab8d71e700438adfb1a62f7b3e48dd1925b00bb2",
        "83b1e8d074d5867e842cbeedbb88bc2a2f2e6cc7cefa375a06c9415d6ef60a7a",
    ),
    _new(
        "VCSH",
        "fbce59d266b428619132065abecc95dcde7fe14c06da1563acba148bc45206d3",
        "2409affc81c060bcef7b751c4d12b860cb9ba4162c1ed827d8e0f892ea3d757f",
        "12fa5b6c875f40dd56ad248860e583f1b974e443927a475f65723bffd649d5eb",
    ),
    _new(
        "BKLN",
        "699861df5f8b86bb1a8188b10009b0ba65f03778675d93a970b1486f016d5377",
        "4ca930d4cb0de243963b2a4001724acee7753414175d48522f9064d764fd8b48",
        "01dfaacba8080c4da53fe7a246d9d6cc9647af353dfa3eebc613ceaea6205a57",
    ),
    _new(
        "FLOT",
        "db31d1079b636657471b027f74aab9fe8bd44096a14b5b5f16ea7d06d5cf5c5d",
        "97f5e79511cc2574887beedd164e5ecc0f03e37322c204dcccfa1030880c3f5a",
        "2bfbdd11755be40899af2d11f83322e1615e2cf13abfe24c3506393a38e0426c",
    ),
    _new(
        "MTUM",
        "80a1eef669c1f292514e29a6f13595fa6607454e0822cdcbd1472f41a3290c09",
        "852aaf48fd3aa109ea9fb285f2759a7258f54dcee111f4e53c9af229b49baad6",
        "f6c68056593a55880363168fd617dda5a06c0b2880f2b2131e3912fbaa1abc2f",
    ),
    _new(
        "SMH",
        "0a3d6ad941cde2887633cc676bfd16a893302e7968f99836e2d0fa011285255c",
        "fa856a632e28364dc6b835d91b8b8316e0552d49aa6e22f7bb3d44fa55673183",
        "381f19e155a1bd7e93a398d906fcabd97209d7af37abb19b90d244d5798e2d63",
    ),
    _new(
        "VBK",
        "8f27876773061bae95a820082e2c10b549a9bc57adb21a285c90782ec921f20e",
        "4be66eb7e585e970383e44880585aa04c86758da3e017bb5ba91e04e149a5713",
        "ba6f4ce28621fd0470384ceb3da22f2078e2abf2e019c5719942790b8e0b8221",
    ),
    _new(
        "SPY",
        "9fad36221834b82d08f3efe8a10f2b34b643e48bc65c9a01152188f95dbfd592",
        "7cf4665b316bd0496f8e428e12e4338991abdb0e82ccd17a2d6ac2e009478f41",
        "7a4ee6c7694115c5de78328de102777b77a574eb9c705a62c89284ccd61605d2",
    ),
)


@dataclass(frozen=True, slots=True)
class TierACohortDataManifestConfig:
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


def build_tier_a_cohort_data_manifest(
    config: TierACohortDataManifestConfig,
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
        provenance = _validate_refresh(source, source_hash, config)

        loaded = load_local_daily_bars_csv(source.source_path, symbol=source.symbol)
        bars = tuple(
            bar for bar in loaded.usable_bars if config.start <= bar.date <= config.end
        )
        if not bars:
            raise ValidationError(f"{source.symbol} has no admitted rows.")
        if bars[-1].date != config.end:
            raise ValidationError(
                f"{source.symbol} must extend through {config.end.isoformat()}."
            )
        if bars[0].date < config.start:
            raise ValidationError(
                f"{source.symbol} starts before the requested window."
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

    common_all = {
        symbol: {bar.date for bar in bars}
        for symbol, bars in bars_by_symbol.items()
    }
    common_dates = tuple(
        sorted(set.intersection(*common_all.values()))
    )
    if not common_dates:
        raise ValidationError("common-session intersection is empty.")
    if common_dates[-1] != config.end:
        raise ValidationError("common-session window must end at the request end.")
    if len(common_dates) < MINIMUM_COMMON_SESSIONS:
        raise ValidationError(
            "common-session intersection is shorter than the frozen minimum of "
            f"{MINIMUM_COMMON_SESSIONS} sessions."
        )
    trimmed: dict[str, tuple[LocalDailyBar, ...]] = {}
    common_set = set(common_dates)
    for symbol, bars in bars_by_symbol.items():
        kept = tuple(bar for bar in bars if bar.date in common_set)
        if tuple(bar.date for bar in kept) != common_dates:
            raise ValidationError(f"{symbol} common-session sequence differs.")
        trimmed[symbol] = kept

    _write_combined(config.combined_output_csv, trimmed)
    payload: dict[str, object] = {
        "record_type": "tier_a_cohort_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_96_tier_a_component_cohort_v1",
        "symbols": list(ALL_SYMBOLS),
        "minimum_common_sessions": MINIMUM_COMMON_SESSIONS,
        "benchmark_rule": "per_market_buy_and_hold",
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
        "per_symbol_raw_row_counts": {
            symbol: len(bars) for symbol, bars in bars_by_symbol.items()
        },
        "combined_row_count": sum(len(value) for value in trimmed.values()),
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
    config: TierACohortDataManifestConfig,
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
        payload = build_tier_a_cohort_data_manifest(
            TierACohortDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"tier_a_cohort_data_manifest_status=blocked:{exc}")
        return 2
    print("tier_a_cohort_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
