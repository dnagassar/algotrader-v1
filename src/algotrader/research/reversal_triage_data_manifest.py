"""Outcome-blind canonical-data admission for the V5.93 reversal triage."""

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
    "ReversalTriageDataManifestConfig",
    "SymbolSourceSpec",
    "build_reversal_triage_data_manifest",
    "main",
]

ALL_SYMBOLS = (
    "BWX", "DBA", "DBB", "DBO", "EMB", "FXA", "FXB", "FXC", "FXE",
    "FXF", "FXY", "IGOV", "MBB", "MUB", "PFF", "SLV", "UNG", "USO",
)
MINIMUM_COMMON_SESSIONS = 3000
_START = date(2005, 1, 3)
_END = date(2026, 7, 31)
_PROTOCOL = Path(
    "docs/design/v5_93_nonequity_reversal_triage_preregistration.md"
)
_PROTOCOL_SHA256 = "0cc32975be515949fe64f053cd63e5e1917eb1cd0429fdb6dd31a2e02694cd62"
_DEFAULT_ROOT = Path("runs/v5_93_nonequity_reversal_triage")


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
        "BWX",
        "042699a781e0e16b1cc140e46b0e5c4d7a8ee4cbcf737611ae9a039e2dafff41",
        "2d28007984c32fcf739a435350c787b15bf4aaad69c05d6eca2e4a45dc2b4d78",
        "436999cd45ded0d8777c6064bff828c4730eec084b79c5e885d4fcf8f54b8de3",
    ),
    _new(
        "DBA",
        "45c7de2766268e29b6a73aaa93311768e3b416217585401a6153c476fd182f10",
        "a4f3249fdcf666f485014de47c80180c3f27549cf8d6f4e58269e7ff3e5391b9",
        "b993dadb176a3f04eeab99a6e300aafae5aba5caa59505af6cb299bdb11c893e",
    ),
    _new(
        "DBB",
        "cb7fa9c47a7b26dc74dc11ff6c10c624b90722cb07ce773116f711baa2ae4ff9",
        "da08eff526407d704ec2e719948ac70a9e75c170a4b420363f537b334f70b301",
        "73c87c404ebbe813819e245294d69ce258ee2fd8c90a103a0e39fcac438d7e24",
    ),
    _new(
        "DBO",
        "1a601651c7fc958522f1083b89490e7adde659bc86ca48b0003d735901b87fef",
        "85bae7d9866bdcd9f05aa05fc73151df6d0f8602177b8042bb7f898c22320f8e",
        "14775866b255bff24e09b6c6c3f746de0c9316508daf6d0cb800021c029c6e29",
    ),
    _new(
        "EMB",
        "a1eb2e10eb84da64530c8335a26743de05e85a9df8df2d94ef3f70ac5c8369ae",
        "aa147a53244c8ad224cab47f8fe0acf8489e9aaa8ca111e5b9d54069f95a1e7f",
        "8a10647058343ac451f6aaa725cf88427b09b3b540ceddec43ef01e869404fb3",
    ),
    _new(
        "FXA",
        "d561996a739ce88dc2ea0cae2696c3e14a73e6f75088dd556a96c22d1a76162f",
        "b82750955df32cf118358b6db888308f367aadb3a536aed13bd9efb8b062f541",
        "051cf0dabc5b02eef0b98305eb5d8700ae8fb532c6df134cd76fd8eb490e5aa8",
    ),
    _new(
        "FXB",
        "db046cfe9fab6a21ac88205f266e11a4e3cc44283736a4431fade52217d98e42",
        "e4cd0162833d34fdbefbdd586c9815ff526d0071bbce345644f4de52854c5c71",
        "7a4b623f6078c68c96f721fc69e4247938874a55388af52e560928ca4d64dbfb",
    ),
    _new(
        "FXC",
        "f591310eef6faf05601c6262aef3d8ac718d9ed6defa60785548be7ae5b249e9",
        "9e5251e230a3abf7be089a8c3504cb1fbcffa3e9ab649f18b2af2797b9a5a64a",
        "5a1f587ebceafcdbd6728d80a8e4727ae3fc89d118016b387e296798fd74b097",
    ),
    _new(
        "FXE",
        "abf20d4063fcdbb79d94c1596f5244a996a31f019b1c4069c6b44cc21672d332",
        "f3437558ac12651bd7c79366b969a6b780b88cea19e38c285faa524f46163026",
        "1c697629079f4d73f7ec4e88a0ce2d327bf4788ece83c76b340096f9a8d5c98a",
    ),
    _new(
        "FXF",
        "175014bc4056951d9fd162adb080f23df8187df9da54d0a2bf69b4a9a4fb626c",
        "8aaf0fee16656a938dafdc82d3f2ff799e99041e39538742b6d0d6552a3d2262",
        "1f6bbbac7f9703c09b57f990a6c623fad3508b239692fad9a0da13f700f1a0ee",
    ),
    _new(
        "FXY",
        "3599044ae965742df2cdce0a7df4422cc48c7801a022d856bc793405e9398191",
        "c0e7c27bd99e46c7361a5608a48de776cbeab9299621e6ed0d9798b77dc01426",
        "206221b9870f8ff44397fecc554030b21c34f065d81828724bf7e184296d3e6d",
    ),
    _new(
        "IGOV",
        "3172d644a5ba402856af909358f5f57664b420f4b3825c7741800825102c7ca8",
        "b519cbfbd86286348b8c68725e63a043e90c5db61b6d93d1834958ba9d64aa10",
        "0600250c30969bfaf89f7ccc700a70198006ac8928533c1181076bc89550320a",
    ),
    _new(
        "MBB",
        "c850b272babca0a197cb02f7fb0874485a1695cf08c67f9faae0662ef611f75f",
        "27419e637c522080d7fca0ede89b0bba1a265b378f085a8e578aee3cadbabc78",
        "46542a69dfe14bfcc43ac6a5750f5a750c71003b79f1cb865d77b9354961df47",
    ),
    _new(
        "MUB",
        "3fc088973a9e6bd3264e403e0cf4450618ef9b75faf8580b0a187120a238fc6f",
        "e3503bb05c0ec72cfc1946c9db23a36ad6215beab006d1f469dfdcbb6c345fc8",
        "a56b0d869db8a4b2a3c804471ec888a876a4e624b4e70b43c0df4e418dafd508",
    ),
    _new(
        "PFF",
        "cfb5c926d365725be9eeb32d4a2f74cee4be0fff4cda562739f2783c8ef1287a",
        "33157d3a64a0e6e8fa771cf28465d71462e73a3842b89101645f517a32fd011c",
        "99f2c134b04e4a3560eeb25a48b2f869cee3dc5c6fc434d1050c2494579720e6",
    ),
    _new(
        "SLV",
        "9dc82da862adbc0499bfc6125429c87f8fdd60a6314a69de29820729a151ddfb",
        "aeb40e576340eb3d3a18ed237cb7d3031181a8d92c4221f34ba00d43d5aa88b3",
        "0f6451009b88237ebb2a6dcce102f8650e1fd500739f338d1dd8acc61a598927",
    ),
    _new(
        "UNG",
        "0d7efb37f2715024e62d6cb161ce49a49a8211e95624bb9fa9b9faeabbc2147a",
        "5a574bd36407e355ba71fbad5f621d918c89c7a7f7383f655fecb17a38fab63d",
        "b5addb1e80a8f3d54a58c1fd72cf65ab0c5ed09880ab75ae256c5a1b1c574984",
    ),
    _new(
        "USO",
        "34dcf78f72dc4586d3449f7369222d9752663680a8cf23632ffb665177788643",
        "b7751df9552ddc446d1b9f15c5caf97bf1e59e7dbf96bd2d657f08c5be560b4d",
        "67cdf9ec9f70516fdbe6ee3b962b525683254c39ca596e7e6debea8f50a6f55d",
    ),
)


@dataclass(frozen=True, slots=True)
class ReversalTriageDataManifestConfig:
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


def build_reversal_triage_data_manifest(
    config: ReversalTriageDataManifestConfig,
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
        "record_type": "reversal_triage_data_manifest",
        "schema_version": "1",
        "protocol_id": "v5_93_nonequity_reversal_triage_v1",
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
    config: ReversalTriageDataManifestConfig,
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
        payload = build_reversal_triage_data_manifest(
            ReversalTriageDataManifestConfig(
                output_manifest=args.output_manifest,
                combined_output_csv=args.combined_output_csv,
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"reversal_triage_data_manifest_status=blocked:{exc}")
        return 2
    print("reversal_triage_data_manifest_status=completed")
    print(f"common_session_count={payload['common_session_count']}")
    print(f"combined_output_sha256={payload['combined_output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
