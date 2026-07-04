"""Deterministic crypto universe/history/orderability refresh packet."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from algotrader.core.time import require_utc_datetime
from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.orchestration.opportunity_router import (
    classify_bar_history,
    normalize_crypto_asset_metadata,
)
from algotrader.signals.crypto_trend import normalize_crypto_symbol

CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION = "v5_1_crypto_universe_refresh_v1"
CRYPTO_UNIVERSE_REFRESH_DEFAULT_OUTPUT_ROOT = Path("runs/crypto_universe_refresh/latest")
CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV = Path("runs/operator_input/crypto_paper_bars.csv")
CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS = Path(
    "runs/crypto_paper_visibility/latest/latest_status.json"
)
CRYPTO_UNIVERSE_REFRESH_REQUIRED_LABELS = (
    "paper_lab_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_submit_mode",
)
CRYPTO_UNIVERSE_REFRESH_OFFLINE_LABELS = (
    *CRYPTO_UNIVERSE_REFRESH_REQUIRED_LABELS,
    "offline_only",
)
CRYPTO_UNIVERSE_REFRESH_LOCAL_REPLAY_LABELS = (
    *CRYPTO_UNIVERSE_REFRESH_REQUIRED_LABELS,
    "offline_only",
    "local_replay",
)
CRYPTO_UNIVERSE_REFRESH_PAPER_READ_LABELS = (
    *CRYPTO_UNIVERSE_REFRESH_REQUIRED_LABELS,
    "paper_read_only",
)

RefreshMode = Literal["offline_fixture", "local_replay", "paper_read_only"]

__all__ = [
    "CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV",
    "CRYPTO_UNIVERSE_REFRESH_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS",
    "CRYPTO_UNIVERSE_REFRESH_REQUIRED_LABELS",
    "CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION",
    "CryptoRefreshInputs",
    "build_crypto_universe_refresh_packet",
    "main",
    "normalize_crypto_orderability_record",
    "render_operating_brief",
    "run_crypto_universe_refresh",
    "write_crypto_universe_refresh_artifacts",
]


@dataclass(frozen=True, slots=True)
class CryptoRefreshInputs:
    """Local-only inputs used to produce one crypto refresh packet."""

    mode: RefreshMode
    source_mode: str
    source_path: str
    broker_state_mode: str
    symbols: tuple[str, ...]
    metadata_by_symbol: Mapping[str, Mapping[str, object] | None]
    bars_by_symbol: Mapping[str, tuple[Bar, ...]]
    input_blockers: tuple[str, ...]
    broker_read_observed: bool
    local_artifact_discovery: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_mode", _required_string(self.source_mode, "source_mode"))
        object.__setattr__(self, "source_path", str(self.source_path))
        object.__setattr__(
            self,
            "broker_state_mode",
            _broker_state_mode(self.broker_state_mode),
        )
        object.__setattr__(self, "symbols", _symbol_tuple(self.symbols))
        metadata: dict[str, Mapping[str, object] | None] = {}
        for symbol, value in self.metadata_by_symbol.items():
            metadata[normalize_crypto_symbol(symbol)] = value
        object.__setattr__(self, "metadata_by_symbol", MappingProxyType(metadata))
        bars: dict[str, tuple[Bar, ...]] = {}
        for symbol, values in self.bars_by_symbol.items():
            bars[normalize_crypto_symbol(symbol)] = tuple(values)
        object.__setattr__(self, "bars_by_symbol", MappingProxyType(bars))
        object.__setattr__(
            self,
            "input_blockers",
            _dedupe(_string_sequence(self.input_blockers)),
        )
        if type(self.broker_read_observed) is not bool:
            raise ValidationError("broker_read_observed must be a boolean.")
        object.__setattr__(
            self,
            "local_artifact_discovery",
            MappingProxyType(dict(self.local_artifact_discovery or {})),
        )


def run_crypto_universe_refresh(
    *,
    output_root: Path | str = CRYPTO_UNIVERSE_REFRESH_DEFAULT_OUTPUT_ROOT,
    mode: RefreshMode = "offline_fixture",
    bars_csv: Path | str = CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV,
    crypto_visibility_status: Path | str = CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS,
    as_of: datetime | str | None = None,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Build the deterministic refresh packet and optionally write artifacts."""

    as_of_value = _utc_datetime(as_of or datetime.now(UTC), "as_of")
    refresh_mode = _refresh_mode(mode)
    inputs = _refresh_inputs(
        mode=refresh_mode,
        bars_csv=Path(bars_csv),
        crypto_visibility_status=Path(crypto_visibility_status),
        as_of=as_of_value,
    )
    root = Path(output_root)
    packet = build_crypto_universe_refresh_packet(
        inputs=inputs,
        as_of=as_of_value,
        output_root=root,
    )
    if write_artifacts:
        packet["artifact_paths"] = write_crypto_universe_refresh_artifacts(root, packet)
    return packet


def build_crypto_universe_refresh_packet(
    *,
    inputs: CryptoRefreshInputs,
    as_of: datetime,
    output_root: Path | str,
) -> dict[str, object]:
    """Build primitive-only refresh payloads for all required artifacts."""

    as_of_value = _utc_datetime(as_of, "as_of")
    root = Path(output_root)
    if inputs.mode == "paper_read_only":
        labels = CRYPTO_UNIVERSE_REFRESH_PAPER_READ_LABELS
    elif inputs.mode == "local_replay":
        labels = CRYPTO_UNIVERSE_REFRESH_LOCAL_REPLAY_LABELS
    else:
        labels = CRYPTO_UNIVERSE_REFRESH_OFFLINE_LABELS
    symbols = tuple(
        sorted(
            set(inputs.symbols)
            | set(inputs.metadata_by_symbol)
            | set(inputs.bars_by_symbol)
        )
    )
    metadata_records: list[dict[str, object]] = []
    history_records: list[dict[str, object]] = []
    router_symbol_records: list[dict[str, object]] = []
    top_blockers: Counter[str] = Counter(inputs.input_blockers)

    for symbol in symbols:
        bars = inputs.bars_by_symbol.get(symbol, ())
        data_path = _history_data_path(root, symbol)
        metadata = normalize_crypto_orderability_record(
            symbol=symbol,
            metadata=inputs.metadata_by_symbol.get(symbol),
            source_mode=inputs.source_mode,
            broker_state_mode=inputs.broker_state_mode,
            latest_price=_latest_close_price(bars, as_of_value),
        )
        history = _history_record(
            symbol=symbol,
            bars=bars,
            as_of=as_of_value,
            data_path=data_path,
            source_mode=inputs.source_mode,
        )
        symbol_blockers = _dedupe(
            (
                *_string_sequence(metadata.get("metadata_blockers")),
                *_string_sequence(metadata.get("orderability_blockers")),
                *_string_sequence(history.get("blockers")),
            )
        )
        if inputs.broker_state_mode == "broker_state_not_observed":
            symbol_blockers = _dedupe((*symbol_blockers, "broker_state_not_observed"))
        for blocker in symbol_blockers:
            top_blockers[blocker] += 1
        metadata_records.append(metadata)
        history_records.append(history)
        router_symbol_records.append(
            {
                "symbol": symbol,
                "asset_class": "crypto",
                "source_mode": inputs.source_mode,
                "input_backing": _input_backing(inputs.source_mode),
                "broker_state_mode": inputs.broker_state_mode,
                "metadata_status": metadata["metadata_status"],
                "orderability_status": metadata["orderability_status"],
                "history_status": history["history_status"],
                "freshness_status": history["freshness_status"],
                "data_quality_status": history["data_quality_status"],
                "data_path": data_path,
                "metadata_blockers": metadata["metadata_blockers"],
                "orderability_blockers": metadata["orderability_blockers"],
                "history_blockers": history["blockers"],
                "blockers": list(symbol_blockers),
                "local_replay_classifications": [],
            }
        )

    metadata_valid = [
        record
        for record in metadata_records
        if _is_orderability_ready(_text(record["orderability_status"]))
    ]
    history_valid = [
        record
        for record in history_records
        if record["data_quality_status"] == "valid"
        and record["history_status"] == "sufficient_history"
        and record["freshness_status"] == "fresh"
    ]
    metadata_valid_symbols = {str(record["symbol"]) for record in metadata_valid}
    history_valid_symbols = {str(record["symbol"]) for record in history_valid}
    selectable_broker = inputs.broker_state_mode in {
        "alpaca_paper_observed",
        "paper_observed",
        "simulated_offline",
    }
    eligible_input_symbols = sorted(
        metadata_valid_symbols & history_valid_symbols if selectable_broker else set()
    )
    for record in router_symbol_records:
        symbol = str(record.get("symbol", ""))
        record["local_replay_classifications"] = list(
            _local_replay_classifications(
                metadata=_matching_record(metadata_records, symbol),
                history=_matching_record(history_records, symbol),
                symbol_blockers=_string_sequence(record.get("blockers")),
                router_ready=symbol in eligible_input_symbols,
            )
        )
    artifact_discovery = inputs.local_artifact_discovery
    orderability_counts = Counter(
        _text(record.get("orderability_status")) for record in metadata_records
    )
    summary = {
        "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
        "as_of": as_of_value.isoformat(),
        "mode": inputs.mode,
        "source_mode": inputs.source_mode,
        "source_path": inputs.source_path,
        "symbol_count": len(symbols),
        "symbols": list(symbols),
        "valid_metadata_count": len(metadata_valid),
        "valid_history_count": len(history_valid),
        "eligible_input_symbol_count": len(eligible_input_symbols),
        "eligible_input_symbols": eligible_input_symbols,
        "orderability_status_counts": dict(sorted(orderability_counts.items())),
        "notional_orderable_metadata_count": orderability_counts.get("notional_orderable", 0),
        "qty_orderable_metadata_count": (
            orderability_counts.get("qty_orderable", 0)
            + orderability_counts.get("qty_orderable_notional_unobserved", 0)
        ),
        "derived_min_order_value_count": sum(
            1 for record in metadata_records if _text(record.get("derived_min_order_value"))
        ),
        "top_blockers": _top_blockers(top_blockers),
        "broker_state_mode": inputs.broker_state_mode,
        "broker_read_observed": inputs.broker_read_observed,
        "labels": list(labels),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "local_artifacts_discovered": list(
            _mapping_sequence(artifact_discovery.get("discovered_artifacts"))
        ),
        "local_artifacts_accepted": list(
            _mapping_sequence(artifact_discovery.get("accepted_artifacts"))
        ),
        "local_artifacts_rejected": list(
            _mapping_sequence(artifact_discovery.get("rejected_artifacts"))
        ),
        "local_artifacts_discovered_count": int(
            artifact_discovery.get("discovered_artifact_count") or 0
        ),
        "local_artifacts_accepted_count": int(
            artifact_discovery.get("accepted_artifact_count") or 0
        ),
        "local_artifacts_rejected_count": int(
            artifact_discovery.get("rejected_artifact_count") or 0
        ),
    }
    crypto_universe = {
        **summary,
        "asset_class": "crypto",
        "metadata_symbol_count": len(metadata_records),
        "history_symbol_count": len(history_records),
        "metadata_gap_symbols": [
            str(record["symbol"])
            for record in metadata_records
            if record["metadata_status"] == "metadata_not_observed"
        ],
    }
    orderability = {
        "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
        "as_of": as_of_value.isoformat(),
        "asset_class": "crypto",
        "mode": inputs.mode,
        "source_mode": inputs.source_mode,
        "broker_state_mode": inputs.broker_state_mode,
        "records": metadata_records,
        "valid_metadata_count": len(metadata_valid),
        "orderable_symbol_count": len(metadata_valid),
        "orderability_status_counts": dict(sorted(orderability_counts.items())),
        "notional_orderable_metadata_count": orderability_counts.get("notional_orderable", 0),
        "qty_orderable_metadata_count": (
            orderability_counts.get("qty_orderable", 0)
            + orderability_counts.get("qty_orderable_notional_unobserved", 0)
        ),
        "top_blockers": _top_blockers(
            Counter(
                blocker
                for record in metadata_records
                for blocker in _string_sequence(record.get("orderability_blockers"))
            )
        ),
    }
    history_manifest = {
        "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
        "as_of": as_of_value.isoformat(),
        "asset_class": "crypto",
        "mode": inputs.mode,
        "source_mode": inputs.source_mode,
        "records": history_records,
        "valid_history_count": len(history_valid),
    }
    quality_report = {
        "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
        "as_of": as_of_value.isoformat(),
        "asset_class": "crypto",
        "mode": inputs.mode,
        "source_mode": inputs.source_mode,
        "symbol_count": len(symbols),
        "valid_history_count": len(history_valid),
        "records": history_records,
        "top_blockers": _top_blockers(
            Counter(
                blocker
                for record in history_records
                for blocker in _string_sequence(record.get("blockers"))
            )
        ),
    }
    router_input_manifest = {
        "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
        "as_of": as_of_value.isoformat(),
        "asset_class": "crypto",
        "mode": inputs.mode,
        "source_mode": inputs.source_mode,
        "source_path": inputs.source_path,
        "broker_state_mode": inputs.broker_state_mode,
        "broker_read_observed": inputs.broker_read_observed,
        "symbols": list(symbols),
        "router_ready_symbols": eligible_input_symbols,
        "crypto_universe_path": "crypto_universe.json",
        "crypto_orderability_metadata_path": "crypto_orderability_metadata.json",
        "crypto_history_manifest_path": "crypto_history_manifest.json",
        "crypto_history_quality_report_path": "crypto_history_quality_report.json",
        "records": router_symbol_records,
        "labels": list(labels),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "local_artifact_discovery": dict(artifact_discovery),
    }
    return {
        "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
        "as_of": as_of_value.isoformat(),
        "mode": inputs.mode,
        "summary": summary,
        "crypto_universe": crypto_universe,
        "crypto_orderability_metadata": orderability,
        "crypto_history_manifest": history_manifest,
        "crypto_history_quality_report": quality_report,
        "crypto_router_input_manifest": router_input_manifest,
        "bars_by_symbol": {
            symbol: tuple(inputs.bars_by_symbol.get(symbol, ())) for symbol in symbols
        },
        "safety": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "live_mutation_performed": False,
            "network_access_attempted": False,
            "broker_read_performed_current_run": (
                inputs.mode == "paper_read_only" and inputs.broker_read_observed
            ),
            "profit_claim": "none",
            "labels": list(labels),
        },
    }


def normalize_crypto_orderability_record(
    *,
    symbol: str,
    metadata: Mapping[str, object] | object | None,
    source_mode: str,
    broker_state_mode: str = "broker_state_not_observed",
    latest_price: Decimal | str | None = None,
) -> dict[str, object]:
    """Normalize one symbol's allowlisted orderability metadata."""

    normalized_symbol = normalize_crypto_symbol(symbol)
    base: dict[str, object] = {
        "symbol": normalized_symbol,
        "asset_class": "crypto",
        "source_mode": _required_string(source_mode, "source_mode"),
        "broker_state_mode": _broker_state_mode(broker_state_mode),
        "tradable": None,
        "status": "",
        "min_notional": "",
        "min_order_notional": "",
        "min_order_size": "",
        "min_trade_increment": "",
        "price_increment": "",
        "qty_increment": "",
        "broker_observed_min_notional": "",
        "broker_observed_min_order_size": "",
        "broker_observed_min_trade_increment": "",
        "broker_observed_price_increment": "",
        "derived_min_order_value": "",
        "orderability_basis": "",
    }
    if metadata is None:
        return {
            **base,
            "metadata_status": "metadata_not_observed",
            "metadata_blockers": ["metadata_missing", "metadata_not_observed"],
            "orderability_status": "metadata_missing",
            "orderability_blockers": ["metadata_missing", "metadata_not_observed"],
            "orderability_basis": "metadata_not_observed",
        }

    raw = _allowed_metadata_payload(metadata)
    raw_symbol = _text(raw.get("symbol"))
    if raw_symbol and normalize_crypto_symbol(raw_symbol) != normalized_symbol:
        return {
            **base,
            "metadata_status": "metadata_invalid",
            "metadata_blockers": ["metadata_missing", "metadata_symbol_mismatch"],
            "orderability_status": "metadata_missing",
            "orderability_blockers": ["metadata_missing", "metadata_symbol_mismatch"],
            "orderability_basis": "metadata_symbol_mismatch",
        }
    payload = {"symbol": normalized_symbol, **raw}
    try:
        normalized = normalize_crypto_asset_metadata(payload)
    except ValidationError:
        return {
            **base,
            "metadata_status": "metadata_invalid",
            "metadata_blockers": ["metadata_missing", "metadata_invalid"],
            "orderability_status": "metadata_missing",
            "orderability_blockers": ["metadata_missing", "metadata_invalid"],
            "orderability_basis": "metadata_invalid",
        }

    min_order_notional = _first_text(raw, "min_order_notional")
    record = {
        **base,
        "tradable": normalized.get("tradable"),
        "status": _text(normalized.get("status")),
        "min_notional": _text(normalized.get("min_notional")),
        "min_order_notional": min_order_notional,
        "min_order_size": _text(normalized.get("min_order_size")),
        "min_trade_increment": _text(normalized.get("min_trade_increment")),
        "price_increment": _text(normalized.get("price_increment")),
        "qty_increment": _text(normalized.get("qty_increment")),
    }
    record["broker_observed_min_notional"] = _text(record.get("min_notional"))
    record["broker_observed_min_order_size"] = _text(record.get("min_order_size"))
    record["broker_observed_min_trade_increment"] = _text(record.get("min_trade_increment"))
    record["broker_observed_price_increment"] = _text(record.get("price_increment"))
    record["derived_min_order_value"] = _derived_min_order_value(
        latest_price=latest_price,
        min_order_size=record.get("min_order_size"),
    )
    orderability_status, blockers, basis = _orderability_status_and_blockers(record)
    metadata_blockers = tuple(
        blocker for blocker in blockers if blocker.startswith("metadata_")
    )
    if _is_orderability_ready(orderability_status):
        metadata_status = "metadata_observed"
    elif "metadata_invalid" in blockers:
        metadata_status = "metadata_invalid"
    elif "metadata_missing" in blockers:
        metadata_status = "metadata_partial"
    else:
        metadata_status = "metadata_observed"
    return {
        **record,
        "metadata_status": metadata_status,
        "metadata_blockers": list(metadata_blockers),
        "orderability_status": orderability_status,
        "orderability_blockers": list(blockers),
        "orderability_basis": basis,
    }


def write_crypto_universe_refresh_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the refresh packet."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    history_root = root / "history"
    history_root.mkdir(parents=True, exist_ok=True)
    bars_by_symbol = packet.get("bars_by_symbol")
    if isinstance(bars_by_symbol, Mapping):
        for symbol, bars in bars_by_symbol.items():
            _write_bars_csv(history_root / f"{normalize_crypto_symbol(symbol)}.csv", bars)

    paths = {
        "crypto_universe": root / "crypto_universe.json",
        "crypto_orderability_metadata": root / "crypto_orderability_metadata.json",
        "crypto_history_manifest": root / "crypto_history_manifest.json",
        "crypto_history_quality_report": root / "crypto_history_quality_report.json",
        "crypto_router_input_manifest": root / "crypto_router_input_manifest.json",
        "operating_brief": root / "operating_brief.md",
        "operating_record": root / "operating_record.jsonl",
    }
    _write_json(paths["crypto_universe"], _mapping(packet.get("crypto_universe")))
    _write_json(
        paths["crypto_orderability_metadata"],
        _mapping(packet.get("crypto_orderability_metadata")),
    )
    _write_json(paths["crypto_history_manifest"], _mapping(packet.get("crypto_history_manifest")))
    _write_json(
        paths["crypto_history_quality_report"],
        _mapping(packet.get("crypto_history_quality_report")),
    )
    _write_json(
        paths["crypto_router_input_manifest"],
        _mapping(packet.get("crypto_router_input_manifest")),
    )
    paths["operating_brief"].write_text(
        render_operating_brief(packet) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths["operating_record"].write_text(
        json.dumps(
            {
                "record_type": "crypto_universe_refresh",
                "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
                "as_of": packet.get("as_of", ""),
                "summary": packet.get("summary", {}),
                "safety": packet.get("safety", {}),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest_path = root / "manifest.json"
    manifest = {
        "schema_version": CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
        "as_of": packet.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: {
                "path": str(path),
                "sha256": _file_sha256(path),
            }
            for key, path in sorted(paths.items())
        },
        "history_data_files": {
            path.name: {
                "path": str(path),
                "sha256": _file_sha256(path),
            }
            for path in sorted(history_root.glob("*.csv"))
        },
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "network_access_attempted": False,
        "generated_under_runs": "runs" in root.parts,
        "labels": list(_string_sequence(_mapping(packet.get("safety")).get("labels"))),
    }
    _write_json(manifest_path, manifest)
    return {**{key: str(path) for key, path in paths.items()}, "manifest": str(manifest_path)}


def render_operating_brief(packet: Mapping[str, object]) -> str:
    """Render a compact operator-facing refresh brief."""

    summary = _mapping(packet.get("summary"))
    safety = _mapping(packet.get("safety"))
    top_blockers = _mapping_sequence(summary.get("top_blockers"))
    return "\n".join(
        [
            "# Crypto Universe Refresh",
            "",
            f"- schema_version: `{packet.get('schema_version', '')}`",
            f"- mode: `{summary.get('mode', '')}`",
            f"- source_mode: `{summary.get('source_mode', '')}`",
            f"- as_of: `{summary.get('as_of', '')}`",
            f"- symbols_inspected: {summary.get('symbol_count', 0)}",
            f"- valid_metadata_count: {summary.get('valid_metadata_count', 0)}",
            f"- valid_history_count: {summary.get('valid_history_count', 0)}",
            f"- eligible_input_symbol_count: {summary.get('eligible_input_symbol_count', 0)}",
            f"- local_artifacts_discovered: {summary.get('local_artifacts_discovered_count', 0)}",
            f"- local_artifacts_accepted: {summary.get('local_artifacts_accepted_count', 0)}",
            f"- local_artifacts_rejected: {summary.get('local_artifacts_rejected_count', 0)}",
            f"- top_blockers: `{_brief_blockers(top_blockers)}`",
            f"- broker_state_mode: `{summary.get('broker_state_mode', '')}`",
            f"- broker_read_observed: `{_bool_text(summary.get('broker_read_observed'))}`",
            f"- paper_submit_performed: `{_bool_text(safety.get('paper_submit_performed'))}`",
            f"- broker_mutation_performed: `{_bool_text(safety.get('broker_mutation_performed'))}`",
            f"- live_mutation_performed: `{_bool_text(safety.get('live_mutation_performed'))}`",
            f"- labels: `{', '.join(_string_sequence(safety.get('labels')))}`",
        ]
    )


def _refresh_inputs(
    *,
    mode: RefreshMode,
    bars_csv: Path,
    crypto_visibility_status: Path,
    as_of: datetime,
) -> CryptoRefreshInputs:
    if mode == "offline_fixture":
        return _offline_fixture_inputs(as_of)
    return _local_replay_inputs(
        mode=mode,
        bars_csv=bars_csv,
        crypto_visibility_status=crypto_visibility_status,
    )


def _offline_fixture_inputs(as_of: datetime) -> CryptoRefreshInputs:
    as_of_value = _utc_datetime(as_of, "as_of")
    bars_by_symbol = {
        "BTCUSD": _fixture_bars("BTCUSD", as_of_value, count=80, posture="up"),
        "ETHUSD": (),
        "SOLUSD": _fixture_bars(
            "SOLUSD",
            as_of_value - timedelta(days=2),
            count=80,
            posture="up",
        ),
        "ADAUSD": _fixture_bars("ADAUSD", as_of_value, count=10, posture="up"),
    }
    metadata_by_symbol: dict[str, Mapping[str, object] | None] = {
        "BTCUSD": {
            "symbol": "BTC/USD",
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
            "min_order_notional": "10",
            "min_order_size": "0.0001",
            "min_trade_increment": "0.0001",
            "price_increment": "0.01",
        },
        "ETHUSD": None,
        "SOLUSD": {
            "symbol": "SOL/USD",
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
            "min_notional": "10",
            "min_order_size": "0.001",
            "min_trade_increment": "0.001",
            "price_increment": "0.01",
        },
        "ADAUSD": {
            "symbol": "ADA/USD",
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
            "min_notional": "10",
        },
    }
    return CryptoRefreshInputs(
        mode="offline_fixture",
        source_mode="offline_fixture",
        source_path="deterministic_offline_fixture",
        broker_state_mode="simulated_offline",
        symbols=("BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD"),
        metadata_by_symbol=metadata_by_symbol,
        bars_by_symbol=bars_by_symbol,
        input_blockers=(),
        broker_read_observed=False,
    )


def _local_replay_inputs(
    *,
    mode: RefreshMode,
    bars_csv: Path,
    crypto_visibility_status: Path,
) -> CryptoRefreshInputs:
    discovery = _discover_local_replay_artifacts(
        bars_csv=bars_csv,
        crypto_visibility_status=crypto_visibility_status,
        include_repo_roots=(
            bars_csv == CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV
            and crypto_visibility_status == CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS
        ),
    )
    selected_visibility_path = Path(
        str(discovery.get("selected_visibility_artifact") or crypto_visibility_status)
    )
    selected_bars_path = Path(str(discovery.get("selected_bars_artifact") or bars_csv))
    status = _read_local_replay_status(selected_visibility_path)
    bars_by_symbol = _read_crypto_bars_by_symbol(selected_bars_path)
    capability = _mapping(status.get("crypto_capability"))
    metadata_by_symbol = _metadata_by_symbol_from_status(status, capability)
    symbols = _symbols_from_status_and_bars(status, capability, metadata_by_symbol, bars_by_symbol)
    broker_state_mode = _broker_state_mode(status.get("broker_state_mode"))
    broker_read_observed = _bool_value(status.get("broker_read_performed")) is True
    capability_broker_read = _bool_value(capability.get("broker_read_performed")) is True
    broker_read_observed = broker_read_observed or capability_broker_read
    source_mode = "local_replay"
    blockers = list(_string_sequence(status.get("blockers")))
    blockers.extend(_string_sequence(discovery.get("blockers")))
    if not selected_visibility_path.is_file():
        blockers.append("local_artifact_missing")
        blockers.append("metadata_missing")
    if not selected_bars_path.is_file():
        blockers.append("local_artifact_missing")
        blockers.append("history_missing")
    if mode == "paper_read_only":
        source_mode = "paper_read_only"
        if not broker_read_observed:
            raise ValidationError(
                "paper_read_only refresh requires an observed paper-read visibility artifact."
            )
        if broker_state_mode not in {"alpaca_paper_observed", "paper_observed"}:
            raise ValidationError(
                "paper_read_only refresh requires paper-observed broker_state_mode."
            )
    return CryptoRefreshInputs(
        mode=mode,
        source_mode=source_mode,
        source_path=(
            f"visibility={selected_visibility_path};history={selected_bars_path}"
        ),
        broker_state_mode=broker_state_mode,
        symbols=symbols,
        metadata_by_symbol=metadata_by_symbol,
        bars_by_symbol=bars_by_symbol,
        input_blockers=tuple(blockers),
        broker_read_observed=broker_read_observed,
        local_artifact_discovery=discovery,
    )


def _discover_local_replay_artifacts(
    *,
    bars_csv: Path,
    crypto_visibility_status: Path,
    include_repo_roots: bool,
) -> dict[str, object]:
    candidate_paths = _local_replay_candidate_paths(
        bars_csv=bars_csv,
        crypto_visibility_status=crypto_visibility_status,
        include_repo_roots=include_repo_roots,
    )
    discovered: list[dict[str, object]] = []
    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    for path in candidate_paths:
        artifact_type = _local_replay_artifact_type(path)
        if not artifact_type:
            continue
        record = {
            "path": str(path),
            "artifact_type": artifact_type,
            "classification": "real_local_replay_candidate",
        }
        if not path.is_file():
            if path in {bars_csv, crypto_visibility_status}:
                rejected.append(
                    {
                        **record,
                        "exists": False,
                        "classification": "local_artifact_missing",
                        "rejection_reason": "local_artifact_missing",
                    }
                )
            continue
        discovered.append({**record, "exists": True})
        if artifact_type == "crypto_bars":
            accepted_record, rejected_record = _inspect_crypto_bars_artifact(path, record)
        else:
            accepted_record, rejected_record = _inspect_crypto_status_artifact(path, record)
        if accepted_record:
            accepted.append(accepted_record)
        if rejected_record:
            rejected.append(rejected_record)

    selected_visibility = _select_local_replay_artifact(
        accepted,
        artifact_type="crypto_visibility_status",
        preferred_path=crypto_visibility_status,
    )
    selected_bars = _select_local_replay_artifact(
        accepted,
        artifact_type="crypto_bars",
        preferred_path=bars_csv,
    )
    blockers: list[str] = []
    if not selected_visibility:
        blockers.extend(("local_artifact_missing", "metadata_missing"))
    if not selected_bars:
        blockers.extend(("local_artifact_missing", "history_missing"))
    return {
        "discovery_mode": "local_replay",
        "discovery_roots": [str(root) for root in _local_replay_roots(include_repo_roots)],
        "discovered_artifacts": discovered,
        "accepted_artifacts": accepted,
        "rejected_artifacts": rejected,
        "discovered_artifact_count": len(discovered),
        "accepted_artifact_count": len(accepted),
        "rejected_artifact_count": len(rejected),
        "selected_visibility_artifact": selected_visibility,
        "selected_bars_artifact": selected_bars,
        "blockers": list(_dedupe(blockers)),
    }


def _local_replay_candidate_paths(
    *,
    bars_csv: Path,
    crypto_visibility_status: Path,
    include_repo_roots: bool,
) -> tuple[Path, ...]:
    paths: list[Path] = [crypto_visibility_status, bars_csv]
    for root in _local_replay_roots(include_repo_roots):
        if not root.is_dir():
            continue
        for pattern in ("*.json", "*.jsonl", "*.csv"):
            paths.extend(
                path
                for path in sorted(root.rglob(pattern))
                if _local_replay_artifact_type(path)
            )
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return tuple(result)


def _local_replay_roots(include_repo_roots: bool) -> tuple[Path, ...]:
    if not include_repo_roots:
        return ()
    return (
        Path("runs/operator_input"),
        Path("runs/crypto_paper_visibility"),
        Path("runs/crypto_paper_mutation_drill"),
        Path("runs/broker_snapshots"),
        Path("runs/paper_broker_snapshots"),
        Path(".data"),
    )


def _local_replay_artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    lowered = str(path).replace("\\", "/").lower()
    if suffix == ".csv" and ("crypto" in lowered or path.name.lower().endswith("bars.csv")):
        return "crypto_bars"
    if suffix in {".json", ".jsonl"} and (
        "crypto" in lowered
        or "status" in path.name.lower()
        or path.name.lower() in {"latest_status.json", "supervisor_receipt.jsonl", "drill_receipt.jsonl"}
    ):
        return "crypto_visibility_status"
    return ""


def _inspect_crypto_bars_artifact(
    path: Path,
    record: Mapping[str, object],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    try:
        bars_by_symbol = _read_crypto_bars_by_symbol(path)
    except ValidationError as exc:
        return None, {
            **dict(record),
            "exists": True,
            "classification": "local_artifact_rejected",
            "rejection_reason": f"malformed_crypto_bars:{exc}",
        }
    if not bars_by_symbol:
        return None, {
            **dict(record),
            "exists": True,
            "classification": "local_artifact_rejected",
            "rejection_reason": "no_crypto_bars",
        }
    return {
        **dict(record),
        "exists": True,
        "classification": "real_local_replay_candidate",
        "accepted_reason": "crypto_bars_observed",
        "symbol_count": len(bars_by_symbol),
        "symbols": sorted(bars_by_symbol),
    }, None


def _inspect_crypto_status_artifact(
    path: Path,
    record: Mapping[str, object],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    payload, rejection_reason = _read_json_or_jsonl_mapping(path)
    if payload is None:
        return None, {
            **dict(record),
            "exists": True,
            "classification": "local_artifact_rejected",
            "rejection_reason": rejection_reason,
        }
    if not _is_crypto_status_payload(payload):
        return None, {
            **dict(record),
            "exists": True,
            "classification": "local_artifact_rejected",
            "rejection_reason": "not_crypto_status_artifact",
        }
    symbols = _symbols_from_status_and_bars(
        payload,
        _mapping(payload.get("crypto_capability")),
        _metadata_by_symbol_from_status(payload, _mapping(payload.get("crypto_capability"))),
        {},
    )
    return {
        **dict(record),
        "exists": True,
        "classification": "real_local_replay_candidate",
        "accepted_reason": "crypto_status_observed",
        "symbol_count": len(symbols),
        "symbols": list(symbols),
    }, None


def _read_json_or_jsonl_mapping(path: Path) -> tuple[Mapping[str, object] | None, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, "unreadable_artifact"
    try:
        if path.suffix.lower() == ".jsonl":
            for line in text.splitlines():
                if line.strip():
                    payload = json.loads(line)
                    break
            else:
                return None, "empty_jsonl_artifact"
        else:
            payload = json.loads(text)
    except json.JSONDecodeError:
        return None, "malformed_json_artifact"
    if not isinstance(payload, Mapping):
        return None, "json_artifact_not_object"
    return payload, ""


def _read_local_replay_status(path: Path) -> Mapping[str, object]:
    payload, _reason = _read_json_or_jsonl_mapping(path)
    return payload or {}


def _is_crypto_status_payload(payload: Mapping[str, object]) -> bool:
    capability = _mapping(payload.get("crypto_capability"))
    return (
        _first_text(payload, "asset_class", "universe") == "crypto"
        or bool(capability)
        or bool(_string_sequence(payload.get("eligible_crypto_symbols")))
        or bool(_first_text(payload, "selected_symbol", "symbol"))
    )


def _select_local_replay_artifact(
    accepted: Sequence[Mapping[str, object]],
    *,
    artifact_type: str,
    preferred_path: Path,
) -> str:
    candidates = [
        record
        for record in accepted
        if _text(record.get("artifact_type")) == artifact_type
    ]
    if not candidates:
        return ""
    selected = max(
        candidates,
        key=lambda record: _local_replay_artifact_score(record, preferred_path),
    )
    return _text(selected.get("path"))


def _local_replay_artifact_score(
    record: Mapping[str, object],
    preferred_path: Path,
) -> tuple[int, str]:
    path_text = _text(record.get("path"))
    normalized = path_text.replace("\\", "/").lower()
    score = 0
    if path_text == str(preferred_path):
        score += 100
    if "/latest/" in normalized:
        score += 30
    if "runs/operator_input" in normalized:
        score += 25
    if "runs/crypto_paper_visibility" in normalized:
        score += 25
    if Path(path_text).name.lower() == "latest_status.json":
        score += 10
    return score, path_text


def _history_record(
    *,
    symbol: str,
    bars: Iterable[Bar],
    as_of: datetime,
    data_path: str,
    source_mode: str,
) -> dict[str, object]:
    bar_tuple = tuple(bars)
    quality = classify_bar_history(
        symbol=symbol,
        asset_class="crypto",
        bars=bar_tuple,
        as_of=as_of,
        required_bar_count=50,
        max_bar_age=timedelta(hours=2),
        data_path=data_path,
        source_mode=source_mode,
    )
    timestamps = tuple(_utc_datetime(bar.timestamp, "timestamp") for bar in bar_tuple)
    earliest = min(timestamps, default=None)
    latest = max(
        (timestamp for timestamp in timestamps if timestamp <= _utc_datetime(as_of, "as_of")),
        default=None,
    )
    blockers = list(quality.blockers)
    if quality.data_quality_status == "missing_data":
        blockers = list(_dedupe(("missing_data", *blockers)))
    return {
        **quality.to_dict(),
        "earliest_timestamp": "" if earliest is None else earliest.isoformat(),
        "latest_timestamp": "" if latest is None else latest.isoformat(),
        "duplicate_timestamp_status": (
            "duplicate_timestamps_present"
            if quality.duplicate_timestamps
            else "no_duplicate_timestamps"
        ),
        "missing_timestamp_status": "not_observed_in_normalized_bars",
        "missing_data_status": (
            "missing_data" if quality.data_quality_status == "missing_data" else "not_missing"
        ),
        "sufficient_history_status": (
            "sufficient_history"
            if quality.history_status == "sufficient_history"
            else quality.history_status
        ),
        "freshness_status": quality.freshness_status,
        "stale_data_blocker": "stale_data" in blockers,
        "missing_data_blocker": "missing_data" in blockers,
        "missing_history_blocker": "missing_history" in blockers,
        "insufficient_history_blocker": "insufficient_history" in blockers,
        "blockers": blockers,
    }


def _matching_record(records: Sequence[Mapping[str, object]], symbol: str) -> Mapping[str, object]:
    normalized = normalize_crypto_symbol(symbol)
    for record in records:
        symbol_text = _first_text(record, "symbol")
        if symbol_text and normalize_crypto_symbol(symbol_text) == normalized:
            return record
    return {}


def _input_backing(source_mode: str) -> str:
    if source_mode == "offline_fixture":
        return "fixture_backed"
    if source_mode == "local_replay":
        return "real_local_artifact_backed"
    if source_mode == "paper_read_only":
        return "paper_read_only_artifact_backed"
    return "unknown"


def _local_replay_classifications(
    *,
    metadata: Mapping[str, object],
    history: Mapping[str, object],
    symbol_blockers: Sequence[str],
    router_ready: bool,
) -> tuple[str, ...]:
    classifications: list[str] = []
    if _first_text(metadata, "source_mode") == "local_replay" or _first_text(history, "source_mode") == "local_replay":
        classifications.append("real_local_replay_candidate")
    metadata_status = _first_text(metadata, "metadata_status")
    orderability_status = _first_text(metadata, "orderability_status")
    metadata_blockers = set(_string_sequence(metadata.get("metadata_blockers"))) | set(
        _string_sequence(metadata.get("orderability_blockers"))
    )
    history_status = _first_text(history, "history_status")
    freshness_status = _first_text(history, "freshness_status")
    data_quality_status = _first_text(history, "data_quality_status")
    if (
        metadata_status
        in {"", "metadata_not_observed", "metadata_incomplete", "metadata_invalid", "metadata_partial"}
        or orderability_status in {"metadata_missing", "metadata_partial"}
        or "metadata_missing" in metadata_blockers
    ):
        classifications.append("metadata_missing")
    if history_status == "missing_history" or data_quality_status == "missing_data":
        classifications.append("history_missing")
    if freshness_status == "stale_data":
        classifications.append("history_stale")
    if history_status == "insufficient_history":
        classifications.append("insufficient_history")
    if "local_artifact_missing" in set(symbol_blockers) or (
        "metadata_missing" in classifications and "history_missing" in classifications
    ):
        classifications.append("local_artifact_missing")
    if router_ready:
        classifications.append("router_ready")
    elif symbol_blockers:
        classifications.append("router_blocked")
    return _dedupe(classifications)


def _metadata_by_symbol_from_status(
    status: Mapping[str, object],
    capability: Mapping[str, object],
) -> dict[str, Mapping[str, object] | None]:
    metadata: dict[str, Mapping[str, object] | None] = {}
    asset_records = status.get("asset_metadata")
    if isinstance(asset_records, Mapping):
        for raw_symbol, raw_metadata in asset_records.items():
            symbol = normalize_crypto_symbol(raw_symbol)
            metadata[symbol] = (
                {"symbol": symbol, **dict(raw_metadata)}
                if isinstance(raw_metadata, Mapping)
                else None
            )
    asset_list = status.get("crypto_assets")
    if isinstance(asset_list, Sequence) and not isinstance(asset_list, (str, bytes)):
        for item in asset_list:
            if isinstance(item, Mapping):
                symbol_text = _first_text(item, "symbol", "name")
                if symbol_text:
                    metadata[normalize_crypto_symbol(symbol_text)] = item

    selected_symbol = _first_text(capability, "selected_symbol") or _first_text(
        status,
        "selected_symbol",
    )
    if selected_symbol:
        symbol = normalize_crypto_symbol(selected_symbol)
        metadata.setdefault(
            symbol,
            {
                "symbol": symbol,
                "asset_class": "crypto",
                "tradable": _first_nonempty(
                    _first_text(capability, "selected_symbol_tradable"),
                    _first_text(status, "selected_symbol_tradable"),
                ),
                "status": "active",
                "marginable": _first_nonempty(
                    _first_text(capability, "selected_symbol_marginable"),
                    _first_text(status, "selected_symbol_marginable"),
                ),
                "fractionable": _first_nonempty(
                    _first_text(capability, "selected_symbol_fractionable"),
                    _first_text(status, "selected_symbol_fractionable"),
                ),
                "min_order_size": _first_nonempty(
                    _first_text(capability, "min_order_size"),
                    _first_text(status, "min_order_size"),
                ),
                "min_trade_increment": _first_nonempty(
                    _first_text(capability, "min_trade_increment"),
                    _first_text(status, "min_trade_increment"),
                ),
                "qty_increment": _first_nonempty(
                    _first_text(capability, "min_order_increment"),
                    _first_text(status, "min_order_increment"),
                ),
                "min_notional": _first_nonempty(
                    _first_text(capability, "min_notional"),
                    _first_text(status, "min_notional"),
                ),
            },
        )
    return dict(sorted(metadata.items()))


def _symbols_from_status_and_bars(
    status: Mapping[str, object],
    capability: Mapping[str, object],
    metadata_by_symbol: Mapping[str, object],
    bars_by_symbol: Mapping[str, tuple[Bar, ...]],
) -> tuple[str, ...]:
    symbols: list[str] = []
    for value in (
        capability.get("eligible_crypto_symbols"),
        status.get("eligible_crypto_symbols"),
        status.get("symbols"),
    ):
        symbols.extend(_string_sequence(value))
    selected = _first_text(capability, "selected_symbol") or _first_text(
        status,
        "selected_symbol",
    )
    if selected:
        symbols.append(selected)
    symbols.extend(metadata_by_symbol)
    symbols.extend(bars_by_symbol)
    return _symbol_tuple(symbols or ("BTCUSD",))


def _read_crypto_bars_by_symbol(path: Path) -> dict[str, tuple[Bar, ...]]:
    if not path.is_file():
        return {}
    rows = _read_csv_rows(path)
    by_symbol: dict[str, list[Bar]] = {}
    for row in rows:
        symbol_text = _first_text(row, "symbol", "S")
        if not symbol_text:
            continue
        symbol = normalize_crypto_symbol(symbol_text)
        timestamp_text = _first_text(row, "timestamp", "datetime", "date", "t")
        if not timestamp_text:
            continue
        try:
            timestamp = _parse_timestamp(timestamp_text)
            close = _positive_decimal(
                _first_nonempty(_first_text(row, "close"), _first_text(row, "c")),
                "close",
            )
            open_price = _positive_decimal(
                _first_nonempty(_first_text(row, "open"), _first_text(row, "o"), str(close)),
                "open",
            )
            high = _positive_decimal(
                _first_nonempty(_first_text(row, "high"), _first_text(row, "h"), str(close)),
                "high",
            )
            low = _positive_decimal(
                _first_nonempty(_first_text(row, "low"), _first_text(row, "l"), str(close)),
                "low",
            )
            volume = _nonnegative_decimal(
                _first_nonempty(_first_text(row, "volume"), _first_text(row, "v"), "0"),
                "volume",
            )
        except ValidationError:
            continue
        by_symbol.setdefault(symbol, []).append(
            Bar(
                symbol=symbol,
                timestamp=timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return {symbol: tuple(values) for symbol, values in sorted(by_symbol.items())}


def _write_bars_csv(path: Path, bars: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume"))
        if not isinstance(bars, Iterable) or isinstance(bars, (str, bytes)):
            return
        for bar in bars:
            if not isinstance(bar, Bar):
                continue
            writer.writerow(
                (
                    _utc_datetime(bar.timestamp, "timestamp").isoformat(),
                    normalize_crypto_symbol(bar.symbol),
                    "crypto",
                    _decimal_text(bar.open),
                    _decimal_text(bar.high),
                    _decimal_text(bar.low),
                    _decimal_text(bar.close),
                    _decimal_text(bar.volume),
                )
            )


def _latest_close_price(bars: Iterable[Bar], as_of: datetime) -> Decimal | None:
    as_of_value = _utc_datetime(as_of, "as_of")
    usable = [
        bar
        for bar in bars
        if isinstance(bar, Bar)
        and _utc_datetime(bar.timestamp, "timestamp") <= as_of_value
    ]
    if not usable:
        return None
    latest = max(usable, key=lambda bar: _utc_datetime(bar.timestamp, "timestamp"))
    return latest.close


def _fixture_bars(
    symbol: str,
    as_of: datetime,
    *,
    count: int,
    posture: str,
) -> tuple[Bar, ...]:
    first = _utc_datetime(as_of, "as_of") - timedelta(hours=count - 1)
    bars: list[Bar] = []
    for index in range(count):
        price = Decimal("100") + Decimal(index)
        if posture == "down":
            price = Decimal("500") - Decimal(index)
        timestamp = first + timedelta(hours=index)
        bars.append(
            Bar(
                symbol=normalize_crypto_symbol(symbol),
                timestamp=timestamp,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1000"),
            )
        )
    return tuple(bars)


def _orderability_status_and_blockers(
    record: Mapping[str, object],
) -> tuple[str, tuple[str, ...], str]:
    blockers: list[str] = []
    tradable = record.get("tradable")
    if tradable is False:
        blockers.append("not_orderable")
    elif tradable is not True:
        blockers.append("metadata_missing")
        blockers.append("metadata_missing_tradable")
    status = _text(record.get("status")).lower()
    if not status:
        blockers.append("metadata_missing")
        blockers.append("metadata_missing_status")
    elif status not in {"active", "tradable"}:
        blockers.append("not_orderable")

    if not _text(record.get("min_order_size")):
        blockers.append("metadata_missing")
        blockers.append("metadata_missing_min_order_size")
    elif not _has_positive_decimal(record.get("min_order_size"), "min_order_size"):
        blockers.append("metadata_invalid")
        blockers.append("metadata_invalid_min_order_size")

    if not _text(record.get("min_trade_increment")):
        blockers.append("metadata_missing")
        blockers.append("metadata_missing_min_trade_increment")
    elif not _has_positive_decimal(record.get("min_trade_increment"), "min_trade_increment"):
        blockers.append("metadata_invalid")
        blockers.append("metadata_invalid_min_trade_increment")

    min_notional = _text(record.get("min_notional"))
    if min_notional and not _has_positive_decimal(min_notional, "min_notional"):
        blockers.append("metadata_invalid")
        blockers.append("metadata_invalid_min_notional")

    blockers = list(_dedupe(blockers))
    if "not_orderable" in blockers:
        return "not_orderable", tuple(blockers), "broker_marked_not_orderable"
    if blockers:
        return "metadata_partial", tuple(blockers), "metadata_observed_but_partial"
    if min_notional:
        return "notional_orderable", (), "broker_notional_and_qty_metadata"
    return (
        "qty_orderable_notional_unobserved",
        (),
        "broker_qty_metadata_notional_unobserved",
    )


def _is_orderability_ready(status: str) -> bool:
    return status in _ORDERABILITY_READY_STATUSES


def _has_positive_decimal(value: object, field_name: str) -> bool:
    if not _text(value):
        return False
    try:
        _positive_decimal(value, field_name)
    except ValidationError:
        return False
    return True


def _derived_min_order_value(
    *,
    latest_price: Decimal | str | None,
    min_order_size: object,
) -> str:
    if latest_price is None or not _text(min_order_size):
        return ""
    try:
        return _decimal_text(
            _positive_decimal(latest_price, "latest_price")
            * _positive_decimal(min_order_size, "min_order_size")
        )
    except ValidationError:
        return ""


def _allowed_metadata_payload(value: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return _allowed_metadata_fields(value)
    model_dump = getattr(value, "model_dump", None)
    data: Mapping[str, object] = {}
    if callable(model_dump):
        try:
            dumped = model_dump(mode="json")
        except TypeError:
            dumped = model_dump()
        if isinstance(dumped, Mapping):
            data = dumped
    result = _allowed_metadata_fields(data)
    for field in _METADATA_FIELDS:
        if field in result:
            continue
        try:
            item = getattr(value, field)
        except Exception:
            continue
        if item is not None and not callable(item):
            result[field] = item
    return result


def _allowed_metadata_fields(data: Mapping[str, object]) -> dict[str, object]:
    allowed: dict[str, object] = {}
    for key, value in data.items():
        field = _METADATA_LOOKUP.get(_field_lookup_key(key))
        if field is not None and value is not None:
            allowed[field] = value
    return allowed


def _read_csv_rows(path: Path) -> tuple[Mapping[str, str], ...]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ValidationError(f"unable to read CSV: {path}") from exc
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValidationError("CSV header is required.")
    return tuple(dict(row) for row in reader)


def _read_json_mapping(path: Path) -> Mapping[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _history_data_path(root: Path, symbol: str) -> str:
    return str(Path("history") / f"{normalize_crypto_symbol(symbol)}.csv")


def _top_blockers(counter: Counter[str]) -> list[dict[str, object]]:
    return [
        {"blocker": blocker, "count": count}
        for blocker, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        if blocker
    ][:10]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_timestamp(value: object) -> datetime:
    text = _required_string(value, "timestamp")
    try:
        if "T" in text:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError("timestamp must be ISO formatted.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _refresh_mode(value: object) -> RefreshMode:
    if value in {"offline_fixture", "local_replay", "paper_read_only"}:
        return value  # type: ignore[return-value]
    raise ValidationError("mode must be offline_fixture, local_replay, or paper_read_only.")


def _broker_state_mode(value: object) -> str:
    text = _text(value)
    if not text:
        return "broker_state_not_observed"
    if text in _BROKER_STATE_MODES:
        return text
    lowered = text.lower()
    if "observed" in lowered and "paper" in lowered:
        return "alpaca_paper_observed"
    if "not_observed" in lowered:
        return "broker_state_not_observed"
    if "live" in lowered:
        return "blocked_live_endpoint_indicator"
    return "unknown"


def _symbol_tuple(values: Iterable[object]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError("symbols must be an iterable.")
    symbols = [normalize_crypto_symbol(value) for value in values]
    return tuple(sorted(dict.fromkeys(symbols)))


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    wanted = {_field_lookup_key(field_name) for field_name in field_names}
    for key, value in row.items():
        if _field_lookup_key(key) in wanted:
            return _text(value)
    return ""


def _first_nonempty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    enum_value = getattr(value, "value", None)
    if type(enum_value) is str:
        return enum_value.strip()
    return str(value).strip()


def _bool_value(value: object) -> bool | None:
    if type(value) is bool:
        return value
    text = _text(value).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _required_string(value, "value")
        if text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be a UTC ISO timestamp.") from exc
    else:
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include timezone information.")
    try:
        return require_utc_datetime(parsed.astimezone(UTC))
    except ValidationError as exc:
        raise ValidationError(f"{field_name} must be a UTC datetime.") from exc


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _positive_decimal(value: object, field_name: str) -> Decimal:
    parsed = _decimal_value(value, field_name)
    if parsed <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return parsed


def _nonnegative_decimal(value: object, field_name: str) -> Decimal:
    parsed = _decimal_value(value, field_name)
    if parsed < Decimal("0"):
        raise ValidationError(f"{field_name} must be non-negative.")
    return parsed


def _decimal_value(value: object, field_name: str) -> Decimal:
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a finite Decimal.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be a finite Decimal.")
    return parsed


def _decimal_text(value: object) -> str:
    return format(_decimal_value(value, "decimal").normalize(), "f")


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _field_lookup_key(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _brief_blockers(values: Sequence[Mapping[str, object]]) -> str:
    if not values:
        return "none"
    return ", ".join(
        f"{item.get('blocker', '')}:{item.get('count', '')}" for item in values[:5]
    )


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crypto-universe-refresh",
        description="Build local crypto universe/history/orderability refresh artifacts.",
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_UNIVERSE_REFRESH_DEFAULT_OUTPUT_ROOT),
        help="Output directory for ignored refresh artifacts.",
    )
    parser.add_argument(
        "--mode",
        choices=("offline_fixture", "local_replay", "paper_read_only"),
        default="offline_fixture",
        help="Refresh mode.",
    )
    parser.add_argument(
        "--bars-csv",
        default=str(CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV),
        help="Local crypto bars CSV for local replay.",
    )
    parser.add_argument(
        "--crypto-visibility-status",
        default=str(CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS),
        help="Local crypto visibility latest_status.json for local replay.",
    )
    parser.add_argument("--as-of", default="", help="UTC ISO timestamp override.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args(argv)

    packet = run_crypto_universe_refresh(
        output_root=args.output_root,
        mode=_refresh_mode(args.mode),
        bars_csv=args.bars_csv,
        crypto_visibility_status=args.crypto_visibility_status,
        as_of=args.as_of or datetime.now(UTC),
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        summary = _mapping(packet.get("summary"))
        artifacts = _mapping(packet.get("artifact_paths"))
        print(f"crypto_universe_refresh_status=complete")
        print(f"refresh_mode={summary.get('mode', '')}")
        print(f"symbols_inspected={summary.get('symbol_count', 0)}")
        print(f"valid_metadata_count={summary.get('valid_metadata_count', 0)}")
        print(f"valid_history_count={summary.get('valid_history_count', 0)}")
        print(f"eligible_input_symbol_count={summary.get('eligible_input_symbol_count', 0)}")
        print(f"local_artifacts_discovered_count={summary.get('local_artifacts_discovered_count', 0)}")
        print(f"local_artifacts_accepted_count={summary.get('local_artifacts_accepted_count', 0)}")
        print(f"local_artifacts_rejected_count={summary.get('local_artifacts_rejected_count', 0)}")
        print(f"broker_read_observed={_bool_text(summary.get('broker_read_observed'))}")
        print(f"paper_submit_performed=false")
        print(f"broker_mutation_performed=false")
        print(f"live_mutation_performed=false")
        print(f"artifact_crypto_router_input_manifest={artifacts.get('crypto_router_input_manifest', '')}")
    return 0


_BROKER_STATE_MODES = (
    "alpaca_paper_observed",
    "paper_observed",
    "simulated_offline",
    "broker_state_not_observed",
    "offline_preview_only",
    "blocked_live_endpoint_indicator",
    "unknown",
)
_ORDERABILITY_READY_STATUSES = (
    "orderable",
    "notional_orderable",
    "qty_orderable",
    "qty_orderable_notional_unobserved",
)
_METADATA_FIELDS = (
    "symbol",
    "name",
    "asset_class",
    "class",
    "tradable",
    "status",
    "marginable",
    "fractionable",
    "min_notional",
    "min_order_notional",
    "min_order_size",
    "min_trade_increment",
    "min_order_increment",
    "price_increment",
    "qty_increment",
)
_METADATA_LOOKUP = {_field_lookup_key(field): field for field in _METADATA_FIELDS}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
