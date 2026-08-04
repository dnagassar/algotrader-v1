"""Outcome-blind canonical-data admission for the V5.92 volatility triage."""

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
    "VolatilityTriageDataManifestConfig",
    "SymbolSourceSpec",
    "build_volatility_triage_data_manifest",
    "main",
]

ALL_SYMBOLS = (
    "ARGT", "ECH", "EDEN", "EFNL", "EIDO", "EIRL", "EIS", "ENZL", "EPHE",
    "EPOL", "EPU", "EWT", "EZA", "GREK", "INDA", "NORW", "THD", "TUR",
)
MINIMUM_COMMON_SESSIONS = 3000
_START = date(2000, 1, 3)
_END = date(2026, 7, 31)
_PROTOCOL = Path(
    "docs/design/v5_92_vault_volatility_managed_triage_preregistration.md"
)
_PROTOCOL_SHA256 = "156a609fde58a25dec43fa539edb7d9156079b28505f10a167daff7f416eea62"
_DEFAULT_ROOT = Path("runs/v5_92_vault_volatility_managed_triage")


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
        "ARGT",
        "a5ab7f01e4577a9675bb9faafc30f388398bade05ff0c995ea6e33651d797c41",
        "23306fb3864566e65175ef7e4f48c371e66414a0c42c24a03d12dfd13064e2c0",
        "d6fdc6e1d24a1eced7e9f0e6c5f13d96d3bf095c005e0d14a2d9080a74461287",
    ),
    _new(
        "ECH",
        "17df5d176b3daa2418499d7321805681422668b2a5bf610058d8b1272b154f3d",
        "f2f59a7dcae2e41518ee21c64774647c42f36f9460f112898228254c35c8a0d0",
        "41f5ab4a5da5da286cbc8f619a38d8767fccdcf81da3be49ff25c8cdf6369106",
    ),
    _new(
        "EDEN",
        "2d54ff18e495cddec0fa3ed398230a0984ebc4e38688f9b85353a7acf4ee3e8a",
        "4a74ef59a6fb65225a95a80d1fe77395b04f8df588461af24aa179b4cb51180f",
        "8c4898e7b693cfcc43aabf9e0b7c71a2888202fd7057b25e0d3166eb26e96125",
    ),
    _new(
        "EFNL",
        "10d413a1202fe9ae6aad862112dafe94495caf9650c96245d5afe42e00c07290",
        "c4462cf24138023627d789f897e66c0be35aa070a0ba696c6d460c9b19c1cbeb",
        "e335dfc3c860a11605c0ad5d78f3a55fdb25c8589e23fe0b8736baf2b71d9cba",
    ),
    _new(
        "EIDO",
        "ed9ea34c39ef0ce259440f53a94c049ea99fb9df1c8a87243dc9b23c15c3d560",
        "c0ef2aa3b650d077e0fe146e6bfb26b0265a7d48aff69dd7f6d578ef94b81d97",
        "7af1f12660673f394ff491899015fca31413c6aaff5eb6ba8a2373460b60bce4",
    ),
    _new(
        "EIRL",
        "24743db9c151b54ec30d146bad3d34fafcaa2d7173d794ed36424e688d2b5950",
        "044a3dcdc985feb913ca2b64dd7e74e7ac018333689693f923b5d4a9ffab9d7f",
        "40c188e73c1fcdb2c6bf55c7cb71dcfb58d633cd923f9b0e8c0fcad0c2f0517b",
    ),
    _new(
        "EIS",
        "02c103b33bf1e37e0689e01a631245095291e3440e8f90a3aa94f9dd3946aa4b",
        "44dbcf2fb08ed6f0d50b426d7ea94e3fd4818c8b8749fe5bd74945d4fe2620f6",
        "942c4760730392c2c92610c6021e429adb03191aa827eaf41768de5cfa892f8e",
    ),
    _new(
        "ENZL",
        "e3d5b22ecdbad0bb7a2d20047c6259b0bf66553e076715fb76ba627c00aa8117",
        "e1b7fc47d0fce7a7f72cee82af2127192abfd7480e12812b46ebe9f7f6e74006",
        "54da661877c6c07b34dffaed39d54a5804329a0257d70ef0102a564c4ffe8f94",
    ),
    _new(
        "EPHE",
        "0244f9c44e7876fb9545f5d7c5ce84625ea9269215767bd6eebd48a98109fc5f",
        "ce632212f921a6caf37d1b11ed51e007c9b44e957c63522b49c12575bccbba21",
        "048334150c4dc88df17cb9c699549d10e62114735bad6441262d9ba73585f8a7",
    ),
    _new(
        "EPOL",
        "8a49cecedfb3e3cffa6330bb4a73f0f0833878275cf7fb3e1531ece38c0d618e",
        "8707f7c8845b83588d5e03b32c7d39ed613ff0c75227b8ec7812a8742fa41bc1",
        "58c55c59fc29bb3c29df80128d353bb283cb45af14544c4b1e48b3154e01d5af",
    ),
    _new(
        "EPU",
        "abbbc0bdcc614b924f5aab0f1c0c635f0223784b6a35bf5e34009e4f6226aa8c",
        "6fff75a1784a1aaaef967f88c66edc765e1cebf627350f37212ff50d7e1b5fc4",
        "bbb298a40d1fd0973b90460c25dfc0ecd7b7316a7b94f27be23c386ef533548b",
    ),
    _new(
        "EWT",
        "b25e59b8ca48c27c96d34c0cb9f730e160d2e6c32a214f36274ee2e86bc38faf",
        "06c0ca561e3254eba17162d56898da1b58adb32a5fe2bfc25c598aa16eba48ec",
        "23ded0953f3e627446972fa69cba02e393a07c0ee1987fc6be5a44fd32561a5c",
    ),
    _new(
        "EZA",
        "7059826ac2ce34b57481048b3b12d92f7e8aa6e5c74f256110518707d55a06d6",
        "35386f2784ecca03546ddea64705353ca0be21e056f820065132428c99bb95dd",
        "d695a259d1369659591c1f4b69609ba56b0824177334733a3f2dc021112a5bd5",
    ),
    _new(
        "GREK",
        "ba20f8f1656e32c5281df8fde0da38f8ced0c6896e8f05e3b8acaab520475bfa",
        "4c35be13451ef99300856cc7879ba8e1c8d21a31878b73fcd059ca5422eae8e3",
        "8f4aa33580af448d737938e1fa924e0edb7e1ca01208fb13a1268625db4ac148",
    ),
    _new(
        "INDA",
        "5d061a4f5c180e058fadac447ac434f9f8ed4f6e034501ed96b9d5355cc2c562",
        "c74433679abb50aecec9edd120a6f957eb494cc8dd8e5bf5d575ed36ecda5c82",
        "d8bfc4d6b7d9628af2d04849aab9b01437392f66c1a75a6185ab5491bbe4be8b",
    ),
    _new(
        "NORW",
        "83d4e0bbd7c45ae83a7d384fdaae68c5e915ecb6228dcec1ee98a759c7bbcebc",
        "bc8c30bf53d3e678b162c2be2e5b250cbaf7779b5bdf62898fab74cc7e0e0078",
        "bdf00b511bcb6640a22e09ca52bdee3e5cf3b786db5da318ae807ae0b18b0e1c",
    ),
    _new(
        "THD",
        "1cc020d76fb11365896b698bf0d786ea3c33f150bdda7cdafb95f1af643edcae",
        "56df60303a30737d4282e72d1215d5a8e0cfa7d8c5eeb17f2d8a106aa4b24f6b",
        "4bb4833a7fb0d8af5ee5ab2285d9c705de8bd1b14862a20d0609e70d12d37f2f",
    ),
    _new(
        "TUR",
        "b9d265e0d53ffcc41e96bd86071a2bc63e88debc5eae0a259bd85df6d9d7001d",
        "2f3a98fc99afa9f60722f2c44e10cc0354dc9b6d90f3f27153e303ce80a1819a",
        "7d026c54718f4919c64d13e83c8c5cc7176a5951740d899e9a21e8610017d7f3",
    ),
)


@dataclass(frozen=True, slots=True)
class VolatilityTriageDataManifestConfig:
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


def build_volatility_triage_data_manifest(
    config: VolatilityTriageDataManifestConfig,
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
        "record_type": "volatility_triage_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_92_vault_volatility_managed_triage_v1",
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
    config: VolatilityTriageDataManifestConfig,
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
        payload = build_volatility_triage_data_manifest(
            VolatilityTriageDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"volatility_triage_data_manifest_status=blocked:{exc}")
        return 2
    print("volatility_triage_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
