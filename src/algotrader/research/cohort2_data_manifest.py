"""Outcome-blind canonical-data admission for the V5.97 Tier A cohort 2."""

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
    "Cohort2DataManifestConfig",
    "SymbolSourceSpec",
    "build_cohort2_data_manifest",
    "main",
]

ALL_SYMBOLS = (
    "GDX", "GDXJ", "PPLT", "CWB", "ANGL",
    "EMLC", "VLUE", "SIZE", "IJR", "SPY",
)
MINIMUM_COMMON_SESSIONS = 2600
_START = date(2005, 1, 3)
_END = date(2026, 7, 31)
_PROTOCOL = Path(
    "docs/design/v5_97_harness_repair_and_cohort_2_preregistration.md"
)
_PROTOCOL_SHA256 = "b3ce4c78cbf8c79c06984d5d0daa3376e767fd000818034eb4765f1457947e30"
_DEFAULT_ROOT = Path("runs/v5_97_tier_a_cohort_2")


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
        "GDX",
        "342ea21efd8d1ff6475066090d4d575eb0a55f4b2d677a4531d5e5d3a9367be7",
        "b59b0a9cc7211394ac201ae43b86f7ae0f205514e90ed22694d73db2cd93c8dd",
        "65b482367e57ce3a21b6fd041c612898a12994034958e77f140d8f7754661f4d",
    ),
    _new(
        "GDXJ",
        "38fe6b841e55bf45b0722856e0d62c9f439db49de60e94000ae8d0ce92d7ae18",
        "0dad988bb1a4b629d4e63af077f26ef8b50046a48a194d59b01aed471c55e24f",
        "fefae5d40fbf3b8421e48a5f138ea275a6e408dab1aa54d4ba63151ffce95edd",
    ),
    _new(
        "PPLT",
        "717b296fda7908bf0617403a3990ec2cd467d60427f86d88e014587ff38aa0f6",
        "ebd0a973c02bffa2195708b48eb8e6c760f9e5baa6f29017e1cbb741a45a8912",
        "3869c2f0944c2f3d213a4bf264063690dca494baa80df800f8d5a6973be10ed2",
    ),
    _new(
        "CWB",
        "58d3701333a1aa7db8fbf810d6b9c976345c3e8b5ec20f5252f563b68dec9ba7",
        "cd9f040a3b666b76aa54c8c13c401f332fa5c4e99bfd682be015f53e73ab75ed",
        "f8daa34374afecd84603aee8b6e040065367843acd88a5134411161d6e1eefd5",
    ),
    _new(
        "ANGL",
        "39f6fbd470669d61ba9eef3d1aec3d0c6b98ac4316f59bf6db01b0fb147f0bb7",
        "56e679b2f229b13547f684dd07f1382fac9994f2d1ea388f4c40ed0747c2373b",
        "857c2b4d3d19449d580db189805ec665e9e2dcb47d46c7383ae85c71b3262a0a",
    ),
    _new(
        "EMLC",
        "2d8d79b901a2138d9c2ef2c8ce0d304bf2936f6cf54aa887db2b9af131737896",
        "fcabd307f606bbb8e328aa76423f5478543017a480e8e13462b2848b8d67b615",
        "a6b547a84e8058dac366f087ead7721095d919d798aaaa949be08e13b7f2b1d6",
    ),
    _new(
        "VLUE",
        "3b4af05d712562816378a0e9640174e49d183bc17e10cf1b7e161101501e7b3d",
        "9051cf7fde06ad0584f0330726d3e9bef81abe894c35cd4ae6cecb4ab09d3d09",
        "1ad8b107c3b4c2ec181499494515ff95112cf1f86fd17183a85a78f8cf7a3544",
    ),
    _new(
        "SIZE",
        "13be3b138308d229408c6a055609437f67779f8632e959b8b779f769f50de2cb",
        "0b2e6e2960347e5e341e66cc7f8f0980849858230089812a0b4a62b489c69d8f",
        "cb2bdc8b907364756abe43602752149c0b94df31ee4145d7c76edaaab03d681b",
    ),
    _new(
        "IJR",
        "48d5dad600e486b34205d69d57ac2c711d2d394327db054d83b63793ad0fd3d2",
        "350b7e1e423e8e44570dd2da0c38f4b577182010e1bedc28517ecad9f6dd1b78",
        "5e6a723f5fe57bb8e3c691e77a05aa088d79b1e42f481faf68cbfb9e7a6353f4",
    ),
    _new(
        "SPY",
        "9fad36221834b82d08f3efe8a10f2b34b643e48bc65c9a01152188f95dbfd592",
        "80196749501496d95ca0e42ebff91c98dce190db2feb8d1a505ad2a3f2cc2647",
        "7a4ee6c7694115c5de78328de102777b77a574eb9c705a62c89284ccd61605d2",
    ),
)


@dataclass(frozen=True, slots=True)
class Cohort2DataManifestConfig:
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


def build_cohort2_data_manifest(
    config: Cohort2DataManifestConfig,
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
        "record_type": "cohort2_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_97_tier_a_cohort_2_v1",
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
    config: Cohort2DataManifestConfig,
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
        payload = build_cohort2_data_manifest(
            Cohort2DataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"cohort2_data_manifest_status=blocked:{exc}")
        return 2
    print("cohort2_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
