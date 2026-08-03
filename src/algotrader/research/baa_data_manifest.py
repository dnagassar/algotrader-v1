"""Outcome-blind canonical-data admission for the V5.89 BAA family."""

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
    "DEFAULT_SOURCES",
    "BaaDataManifestConfig",
    "SymbolSourceSpec",
    "build_baa_data_manifest",
    "main",
]

ALL_SYMBOLS = (
    "SPY", "QQQ", "IWM", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD",
    "TLT", "HYG", "LQD", "EFA", "AGG", "TIP", "BIL", "IEF",
)
_START = date(2007, 7, 26)
_END = date(2026, 7, 31)
_PROTOCOL = Path(
    "docs/design/v5_89_keller_bold_asset_allocation_preregistration.md"
)
_PROTOCOL_SHA256 = "b000c85a4ce041a26cfe3eedace3439177456d2507d8a71c08ed8e0740262747"
_DEFAULT_ROOT = Path("runs/v5_89_keller_bold_asset_allocation")


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
        "SPY",
        "383f2ddcd43d3d585c4d24be417b91776e10b582b41087db86d644e5d7fc9fef",
        "f3c2779d6025d6cca6f2ea0f79ed9568b22912c0b612df51a4a3390ae7622d8e",
        "e5a78e4ba70ec26502f0cdd4dc94f17d9ef18a8becc94c14ee18ade96f2e96d6",
    ),
    _new(
        "QQQ",
        "cd683b96bc2cd6ffb39bfc7ad9ee695268aa530add66f4dcc0040fa1f6e0b0e3",
        "f1b668e558dc5366016215a3e18d62c92ddd4f3d7cac5504a10ba05c0539cff1",
        "18b45d59462789755c23b932f5ecb37821102aa70c122d0a0f59e2a1252aaf9a",
    ),
    _new(
        "IWM",
        "c75a4065ce23430cee30ffef8b96da6aeccc70ad8b8f42f9cbaf9771c9fbd549",
        "2ca19fde0bc0641cae6f398fb6c3d16069e8613bb4f4e4998242214a47012766",
        "f0af66cf2b8d3778a223211c143fa0a6c119ceda00722bcf0fe71289bf5c391c",
    ),
    _new(
        "VGK",
        "6238676b6bface8c8154ab414d7028ab312a1ac94f23f761f4ecd91e0b6c412f",
        "baeae12681e30c599018cf13b7c81a962bcaee2c2ebbb91faae0a2bb0229b669",
        "f368ea42889510781d030c53ea7f48e1127617d98d48335175074e7d9ffca691",
    ),
    _new(
        "EWJ",
        "b6686f3ff8510c80b721a839f2488a656986c705a72c58cfa4c3d41548632eba",
        "ad6954a10a11f4da0b5990eebccda65ccbed13dfbee15695b7e218d704ff03a4",
        "0cfe38bc81f4152d0b3b8da5b8e5b085da93536bc09b50d8a12a27f86c3f3d01",
    ),
    _new(
        "EEM",
        "91399fabb12e98237f6cf245b8a3212b9f8ed046dfb53b75d44ffd6d712aa698",
        "132120b89717a5c8454cffe15cf7d39513386b6ed6b106973db51bfefb19b72b",
        "39a28911a912dbf545324760612de123f518b63f6e9e5c77c8bbc93a5c392207",
    ),
    _new(
        "VNQ",
        "3ea541bde00148955b1f5185a0650921b4bf0ef25defc2ce921565d1a3b11d68",
        "52261dffa9ebd67b76daaaba578c81766c23ab8c7f20668462cf43c312a55cf9",
        "73343d14e8286c08a3ed5659abe0337560c56ade922e572bd8961edaed3166d4",
    ),
    _new(
        "DBC",
        "8720fa2256e971ae5004b5fb92d095d699d122fe68d51f37d61a9665cb8054b1",
        "f14dc4b14e8a563a1432e7346cb62b2c87a513cb837f61c207d91a077330bec5",
        "5476ceb2660b462e77e003ee3a089b1e3e902631eca912b275ada0470ca47128",
    ),
    _new(
        "GLD",
        "7fee8321dfa858da976a1da6aeac83d1875e95a1f54abd47123931d0a04a764c",
        "6ad0dfece0e54557a21c34808aabcc14c3f8a725589aad5045c1c316691ed283",
        "ee4b5257fed29fbbbc0af069f6bc25f32971002fbee48052325ce280756dacf6",
    ),
    _new(
        "TLT",
        "ec35809d72b44728d4776a750b698d7280319d227dce1579544793f07c7b4560",
        "8ce45600d3ec61040a15d87a519d8406c977dcfe54afaf834f80661d9ab0d3fd",
        "da7d94c93090ce725716d65dfd36c0695ae5234615a13d33344dd0015735295e",
    ),
    _new(
        "HYG",
        "04b0cbb73fc14817d4e3bfebed7227eb47925c4872db186bfd050feacb68805f",
        "e3afac27481b4e46539fe761ebc38000ad8608f3e5186250e427acc08f891930",
        "7f63adc011a8cb5b30e081749d7b3d2a71520de0898703ea77700cf9d1023d9c",
    ),
    _new(
        "LQD",
        "07e189cb7b9c6db2a7caedd7464e66d27d55d6ccd6ea0c4969553e50f9bc01d6",
        "17110fc419782092319b714dd1d85580ead6b8fdaa6605cb5c73763a615ea2bc",
        "6efc5a3a44fb752f750ce7b459fc44ea8d413b8cdec7a85a818baafa6e854be9",
    ),
    _new(
        "EFA",
        "46ef2fb2ea993d93996326e194fb192e79c67463d2e34fe3221269516a093dad",
        "2ae5501fb3c3570b80452e1f3bc26176c374a317fbe7bd4ffc2f14e07ca46c15",
        "d846679edf169ce9c2767a1b51e82d6fd7e98ced35b806864de3aa5171584f45",
    ),
    _new(
        "AGG",
        "42b9eb79269a140e354e15aa0f26b6c11bd778124a22d452ff2682c8e58eb21a",
        "5b54fc6db704146958d31de6efd769b6b0cf7b7f0c423a065fbc4a69cb2e6408",
        "3c4dead828e7f715c3fa944a47bca87a37c5d128d8b7dfcd28238d1724e254e1",
    ),
    _new(
        "TIP",
        "e6c15c66c1550ba60a43099635dd325ccdf9cb8a40ef906abee49c48e6408989",
        "b6728925e83fd35847fe910b634b58c97d102ee9ae0e01b18f29e09ddd5f9890",
        "eec3219a26c9a52b2835d4ef0779e8c84a2a830085cf026b6fe7c8902be90ef2",
    ),
    _new(
        "BIL",
        "716babf36b3851b17afcb28980e51c91fa2a8c82bf8df80ad498b15b853271cf",
        "e201f5bb7cad5b483a9ccb6056a20ea96a36238dabdd714c760cd33c18262862",
        "d71e66af701a7a3e62c77833f3817cee7a56424dc4808412243cea55cb52aad5",
    ),
    _new(
        "IEF",
        "091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f",
        "892a407ad476f5907faa20396f3063e2a62e9c0ef752f124c20b0dc7c348a700",
        "445f5f8a0f33b5837ba80bde621091410eb4b1dddead7f2d3947c938c3a5f1e7",
    ),
)


@dataclass(frozen=True, slots=True)
class BaaDataManifestConfig:
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


def build_baa_data_manifest(
    config: BaaDataManifestConfig,
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

    common_all = {
        symbol: {bar.date for bar in bars}
        for symbol, bars in bars_by_symbol.items()
    }
    common_dates = tuple(
        sorted(set.intersection(*common_all.values()))
    )
    if not common_dates:
        raise ValidationError("common-session intersection is empty.")
    if common_dates[0] != config.start or common_dates[-1] != config.end:
        raise ValidationError("common-session boundary mismatch.")
    trimmed: dict[str, tuple[LocalDailyBar, ...]] = {}
    common_set = set(common_dates)
    for symbol, bars in bars_by_symbol.items():
        kept = tuple(bar for bar in bars if bar.date in common_set)
        if tuple(bar.date for bar in kept) != common_dates:
            raise ValidationError(f"{symbol} common-session sequence differs.")
        trimmed[symbol] = kept

    _write_combined(config.combined_output_csv, trimmed)
    payload: dict[str, object] = {
        "record_type": "baa_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_89_keller_bold_asset_allocation_v1",
        "symbols": list(ALL_SYMBOLS),
        "canary_symbols": ["SPY", "EFA", "EEM", "AGG"],
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
    config: BaaDataManifestConfig,
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
        payload = build_baa_data_manifest(
            BaaDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"baa_data_manifest_status=blocked:{exc}")
        return 2
    print("baa_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
