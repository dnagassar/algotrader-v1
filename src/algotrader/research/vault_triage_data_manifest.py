"""Outcome-blind canonical-data admission for the V5.91 vault triage."""

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
    "VaultTriageDataManifestConfig",
    "SymbolSourceSpec",
    "build_vault_triage_data_manifest",
    "main",
]

ALL_SYMBOLS = (
    "EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWK", "EWL", "EWM",
    "EWN", "EWO", "EWP", "EWQ", "EWS", "EWU", "EWW", "EWY", "EWZ",
)
MINIMUM_COMMON_SESSIONS = 5000
_START = date(1996, 4, 1)
_END = date(2026, 7, 31)
_PROTOCOL = Path(
    "docs/design/v5_91_vault_cross_sectional_trend_triage_preregistration.md"
)
_PROTOCOL_SHA256 = "a1d9c90face12c565dc2b434aaa8ad5ea59754fec29c90bba761279a72938f12"
_DEFAULT_ROOT = Path("runs/v5_91_vault_cross_sectional_trend_triage")


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
        "EWA",
        "3806bd46e9112c01408862bf8ad539a0a8cae72fce983c629bb80396b8637253",
        "7fe16bee7d3f11bf83a92b15494ddd7b6b89d8fad64d87034760c202581c96c1",
        "52184f8718fba5d9da93fb62bde1f8590d7b915f48705a8efa4299ad2a2b9727",
    ),
    _new(
        "EWC",
        "f25f2b0b966b0cec3d90f26be0dd9c3d89b71f0cb9e6c15325201462065ab4e4",
        "fb8df7e76f981ac787d9d3f59b896f0dbafdfa0c9c6eaf518758ac5c739fee79",
        "0ed3aeff913efb07705c19ff7341a84fac8302f71f9a36104efb70daa0429358",
    ),
    _new(
        "EWD",
        "b936eff6dbc895831074543646dd0f8f3a4214360feed0166482f76687e610a1",
        "3e0d7c5364ed2920e95c8c006e33d24018aa7a18974d3deaa115ee98ca9a85fb",
        "bf4ceaae744aafcd74f5fc1ee2bbc255e87d9ad72031a394f89448c81fcfce3a",
    ),
    _new(
        "EWG",
        "1569eee127b3feb6909dadc2aeb4b72f7df3eaa2db7a39856c00a3655e32bcd6",
        "06de361dc3dfbf4c8fab5feaa471c54e1614cea4da3576e971a647a409c65616",
        "91571fbb8c1c5c5f3b079322b16d49125c238b602383fafdf905e9fc6ee44dee",
    ),
    _new(
        "EWH",
        "57be6eb6b7b2f9aa8e883ea3b19236d036de724c2b4dafd6ff238e152491a153",
        "6b1663df77440505e4a7df3370dd3b2fb993d23ebe391ff1f5cc8a13f4040c0a",
        "629bdf0400b7b090b306301b0c6545b63d16ec8bc421b3d9a961456654746eb6",
    ),
    _new(
        "EWI",
        "41a415e11223bc33f60c25dcac6b0cb0f77dfa1544329c7189f5c4031a0e948e",
        "b28122325f1b0057cf850fdabf597209622f997e479b7a09c8d067bba02a84bb",
        "a481551b1a2eb88433959b7348f39e2c714ca183e76f0d3ba93a407eda130d63",
    ),
    _new(
        "EWK",
        "c383942fd5a493abaec9f9e23042dd6961ce4917c41b6e691aa4ae8f7e6c9057",
        "2906e4cd2732e6dfec5bc3841987e19ce878d2960c90482bcebd60dab520ccbc",
        "9585a66d6d0808cee6dd60c678c5b05048ce4bfc7d31314a821a80e910ef6adb",
    ),
    _new(
        "EWL",
        "9715b8025a4323cdede40b54ee3374e8e0273b18f704fd1cd8059a5eac09170b",
        "1eb657879077f10095b649038362ae5f1047d14bad80c3ab6e327046c7b40e7b",
        "15c11e788d9fb43ae792d0f2f05f6d4539cd0ce78f7bd0bc333ec02041a4455f",
    ),
    _new(
        "EWM",
        "8e6081789bb3d71cc95c04b04213622549b3c73042b3226f1668d941f9e93a31",
        "5c7e8834a83f086dd1903fa15ca21782c849ef5823ca7a1fe225bda31f49f540",
        "37372407e8d4bb2bb87727abe4176020aedc7331e8671733e2728b8d81641527",
    ),
    _new(
        "EWN",
        "57595d0e1abd16b686fc6cc842991b57d542ba0a0f2f883a7b92f1f9d6255259",
        "2703cf4e3e902d02724a999bab268bacfaaf49e766982a4644d7df652b2aba9a",
        "1ce9a9730a4399f72d629b0144a853320d7ff2b7102c2e72f7fea1c23067ead7",
    ),
    _new(
        "EWO",
        "62ab8d06b52611eabbdfda0c2a4a7641cf4c25056d57062d27568a9d825ec883",
        "df042e418618650bd8409e94996a2e1ac0d00cbf89b58ddc40352a68f1c2600c",
        "c388542d9d48b1137b32557161c93ccf23c044e33d4f097fece4fea5c4872c27",
    ),
    _new(
        "EWP",
        "d61660a1b62f04d4ccb3801629ee4ce77b10b9bc2db65ec076a1d9a8a5215542",
        "a6d16fcb35199141d347528916e832943416ef16a09aa739e4f7e76c8bb4d10e",
        "d953bfa48661e8bcca26b1071a1e7325fcc0e316707bb0d6a543fa58635a1f1d",
    ),
    _new(
        "EWQ",
        "c0568972157336f4b5ee815a8dd1690ae9a6bb66554abbd56466f617a8f7d431",
        "6ffd7e960dd11bf785515d99263b478239557ba3e5e21ded2637e449769565e0",
        "9ffbd3871dac546cdaaefab4e388f4871156e2b34ab305b2647e3789e97f01ab",
    ),
    _new(
        "EWS",
        "e17afbe5f6f3556017d2e6a5263ba35be322c71af279c2e1bce53953e7a3a4e3",
        "5d163ab11639b499fce87b4f9848e686f5e346af9dde577af870cf53ced1327e",
        "86d36dc7853f4b2b28aa83c8f82c07bde9c715040e09f1981812bc219abc253a",
    ),
    _new(
        "EWU",
        "12e0131c0d31daca12751041de103f096edb03f91fe64e74fbf419a17ab59587",
        "ca8385a928cedbbe5b5f3c3cfc1531c1a473af4bde6e6a9f266abcbc3f5132b0",
        "ebb5773fa4b3bdc0fc76cd9cb869464fbaec99505c78cf8d485fceac52b78096",
    ),
    _new(
        "EWW",
        "e1070479ca65519c3704897ebf1d7a8446c91c14d7f25da404fa2b079f3a8785",
        "89c8f19d6a71d3f100f3cfeac6e4793c3ec3468500552e49a24a583ddf524f26",
        "da5ad4624c55e4743b67fef383c3d71c7019ee333f7512e629535d9e412f98d0",
    ),
    _new(
        "EWY",
        "78ad369d12021615bdc715e7dd9e2c99a3602e411e9d7e9774251b6af9ce57ce",
        "78bc24945d98ba3de3dcaf69022f3aa5dbf9f114e1957cc6fb467d07641b2a2f",
        "ba45a0b141dbdfc4f0d3941f31359132735bac219e32e0eb12d690e6352149bc",
    ),
    _new(
        "EWZ",
        "d0d971a65e133758fae37af68ad45fb00b88d6efc192d8a942b71da8af678291",
        "037ca1cef1eb3183c10fb085d3db22e9aec673bdb0ea3bc868f32febef95a51a",
        "6e119a21fada70fd9cb6d295789a43fa9315c6ad1c365f9096186feb08de7c75",
    ),
)


@dataclass(frozen=True, slots=True)
class VaultTriageDataManifestConfig:
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


def build_vault_triage_data_manifest(
    config: VaultTriageDataManifestConfig,
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
        "record_type": "vault_triage_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_91_vault_cross_sectional_trend_triage_v1",
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
    config: VaultTriageDataManifestConfig,
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
        payload = build_vault_triage_data_manifest(
            VaultTriageDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"vault_triage_data_manifest_status=blocked:{exc}")
        return 2
    print("vault_triage_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
