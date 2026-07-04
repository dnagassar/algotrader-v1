from __future__ import annotations

import ast
import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path

from algotrader.core.types import Bar
from algotrader.orchestration.crypto_universe_refresh import (
    CRYPTO_UNIVERSE_REFRESH_REQUIRED_LABELS,
    CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION,
    normalize_crypto_orderability_record,
    run_crypto_universe_refresh,
)
from algotrader.orchestration.opportunity_router import run_opportunity_router

AS_OF = datetime(2026, 7, 4, 0, 30, tzinfo=UTC)
MODULE_PATH = Path("src/algotrader/orchestration/crypto_universe_refresh.py")


def test_crypto_metadata_normalization_handles_variants_and_blockers() -> None:
    complete = normalize_crypto_orderability_record(
        symbol="SOL/USD",
        metadata={
            "symbol": "SOL/USD",
            "class": "crypto",
            "tradable": True,
            "status": "active",
            "min_order_notional": "10",
            "min_order_size": "0.01",
            "min_trade_increment": "0.000001",
            "price_increment": "0.01",
        },
        source_mode="offline_fixture",
        broker_state_mode="simulated_offline",
    )
    qty_only = normalize_crypto_orderability_record(
        symbol="BTCUSD",
        metadata={
            "symbol": "BTC/USD",
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
            "min_order_size": "0.0002",
            "min_trade_increment": "0.00000001",
            "price_increment": "0.01",
        },
        source_mode="local_replay",
        broker_state_mode="alpaca_paper_observed",
        latest_price=Decimal("50000"),
    )
    missing_increment = normalize_crypto_orderability_record(
        symbol="DOGEUSD",
        metadata={
            "symbol": "DOGE/USD",
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
            "min_notional": "10",
        },
        source_mode="offline_fixture",
    )
    not_observed = normalize_crypto_orderability_record(
        symbol="AVAXUSD",
        metadata=None,
        source_mode="local_replay",
    )
    not_orderable = normalize_crypto_orderability_record(
        symbol="MATICUSD",
        metadata={
            "symbol": "MATIC/USD",
            "asset_class": "crypto",
            "tradable": False,
            "status": "inactive",
            "min_notional": "10",
            "qty_increment": "0.001",
        },
        source_mode="local_replay",
    )

    assert complete["symbol"] == "SOLUSD"
    assert complete["min_notional"] == "10"
    assert complete["min_order_notional"] == "10"
    assert complete["broker_observed_min_notional"] == "10"
    assert complete["broker_observed_min_order_size"] == "0.01"
    assert complete["orderability_status"] == "notional_orderable"
    assert complete["metadata_blockers"] == []
    assert qty_only["min_notional"] == ""
    assert qty_only["broker_observed_min_notional"] == ""
    assert qty_only["broker_observed_min_order_size"] == "0.0002"
    assert qty_only["broker_observed_min_trade_increment"] == "0.00000001"
    assert qty_only["derived_min_order_value"] == "10"
    assert qty_only["orderability_status"] == "qty_orderable_notional_unobserved"
    assert qty_only["orderability_basis"] == "broker_qty_metadata_notional_unobserved"
    assert qty_only["metadata_blockers"] == []
    assert missing_increment["metadata_status"] == "metadata_partial"
    assert missing_increment["orderability_status"] == "metadata_partial"
    assert "metadata_missing_min_order_size" in missing_increment["orderability_blockers"]
    assert "metadata_missing_min_trade_increment" in missing_increment["orderability_blockers"]
    assert not_observed["metadata_status"] == "metadata_not_observed"
    assert "metadata_not_observed" in not_observed["metadata_blockers"]
    assert not_orderable["orderability_status"] == "not_orderable"
    assert "not_orderable" in not_orderable["orderability_blockers"]


def test_offline_fixture_manifest_generation_and_artifact_integrity(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_universe_refresh" / "latest"

    packet = run_crypto_universe_refresh(
        output_root=output_root,
        mode="offline_fixture",
        as_of=AS_OF,
        write_artifacts=True,
    )
    paths = packet["artifact_paths"]
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    router_input = packet["crypto_router_input_manifest"]
    summary = packet["summary"]

    assert packet["schema_version"] == CRYPTO_UNIVERSE_REFRESH_SCHEMA_VERSION
    assert summary["symbol_count"] == 4
    assert summary["valid_metadata_count"] >= 2
    assert summary["valid_history_count"] >= 1
    assert router_input["router_ready_symbols"] == ["BTCUSD"]
    assert set(CRYPTO_UNIVERSE_REFRESH_REQUIRED_LABELS) <= set(router_input["labels"])
    assert router_input["paper_submit_performed"] is False
    assert router_input["broker_mutation_performed"] is False
    assert router_input["live_mutation_performed"] is False
    assert (output_root / "history" / "BTCUSD.csv").is_file()

    expected = {
        "crypto_universe.json",
        "crypto_orderability_metadata.json",
        "crypto_history_manifest.json",
        "crypto_history_quality_report.json",
        "crypto_router_input_manifest.json",
        "operating_brief.md",
        "operating_record.jsonl",
        "manifest.json",
    }
    assert expected == {Path(path).name for path in paths.values()}
    assert set(manifest["required_artifacts"]) == {
        "crypto_history_manifest",
        "crypto_history_quality_report",
        "crypto_orderability_metadata",
        "crypto_router_input_manifest",
        "crypto_universe",
        "operating_brief",
        "operating_record",
    }
    assert manifest["history_data_files"]["BTCUSD.csv"]["sha256"]


def test_local_replay_normalizes_existing_visibility_and_bars(tmp_path: Path) -> None:
    bars_csv = tmp_path / "crypto_bars.csv"
    status_json = tmp_path / "latest_status.json"
    output_root = tmp_path / "runs" / "crypto_universe_refresh" / "latest"
    _write_crypto_csv(bars_csv, "ETHUSD", count=80)
    status_json.write_text(
        json.dumps(
            {
                "broker_state_mode": "alpaca_paper_observed",
                "capability_source": "simulated",
                "crypto_capability": {
                    "eligible_crypto_symbols": ["ETH/USD", "DOGE/USD", "MATIC/USD"],
                    "selected_symbol": "ETH/USD",
                    "selected_symbol_tradable": True,
                    "min_order_size": "0.0001",
                    "min_trade_increment": "0.0001",
                    "min_notional": "10",
                },
                "asset_metadata": {
                    "ETH/USD": {
                        "asset_class": "crypto",
                        "tradable": True,
                        "status": "active",
                        "min_order_notional": "10",
                        "min_order_size": "0.0001",
                        "min_trade_increment": "0.0001",
                    },
                    "DOGE/USD": {
                        "asset_class": "crypto",
                        "tradable": True,
                        "status": "active",
                        "min_notional": "10",
                    },
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    packet = run_crypto_universe_refresh(
        output_root=output_root,
        mode="local_replay",
        bars_csv=bars_csv,
        crypto_visibility_status=status_json,
        as_of=AS_OF,
        write_artifacts=True,
    )
    metadata = {
        record["symbol"]: record
        for record in packet["crypto_orderability_metadata"]["records"]
    }
    history = {
        record["symbol"]: record for record in packet["crypto_history_manifest"]["records"]
    }

    assert packet["summary"]["symbol_count"] == 3
    assert packet["summary"]["local_artifacts_discovered_count"] == 2
    assert packet["summary"]["local_artifacts_accepted_count"] == 2
    assert metadata["ETHUSD"]["orderability_status"] == "notional_orderable"
    assert metadata["DOGEUSD"]["orderability_status"] == "metadata_partial"
    assert metadata["MATICUSD"]["metadata_status"] == "metadata_not_observed"
    assert history["ETHUSD"]["history_status"] == "sufficient_history"
    assert history["DOGEUSD"]["missing_history_blocker"] is True
    assert history["MATICUSD"]["missing_data_blocker"] is True
    router_records = {
        record["symbol"]: record
        for record in packet["crypto_router_input_manifest"]["records"]
    }
    assert packet["crypto_router_input_manifest"]["router_ready_symbols"] == ["ETHUSD"]
    assert "local_replay" in packet["crypto_router_input_manifest"]["labels"]
    assert "router_ready" in router_records["ETHUSD"]["local_replay_classifications"]
    assert "metadata_missing" in router_records["DOGEUSD"]["local_replay_classifications"]
    assert "local_artifact_missing" in router_records["MATICUSD"]["local_replay_classifications"]


def test_local_replay_reports_missing_artifacts_without_repo_fallback(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_universe_refresh" / "missing"

    packet = run_crypto_universe_refresh(
        output_root=output_root,
        mode="local_replay",
        bars_csv=tmp_path / "missing_crypto_bars.csv",
        crypto_visibility_status=tmp_path / "missing_latest_status.json",
        as_of=AS_OF,
        write_artifacts=True,
    )
    summary = packet["summary"]
    record = packet["crypto_router_input_manifest"]["records"][0]
    blockers = {item["blocker"] for item in summary["top_blockers"]}

    assert summary["local_artifacts_discovered_count"] == 0
    assert summary["local_artifacts_accepted_count"] == 0
    assert summary["local_artifacts_rejected_count"] == 2
    assert summary["eligible_input_symbol_count"] == 0
    assert "local_artifact_missing" in blockers
    assert "metadata_missing" in record["local_replay_classifications"]
    assert "history_missing" in record["local_replay_classifications"]
    assert "router_blocked" in record["local_replay_classifications"]


def test_local_replay_rejects_malformed_artifacts(tmp_path: Path) -> None:
    bars_csv = tmp_path / "crypto_bars.csv"
    status_json = tmp_path / "latest_status.json"
    output_root = tmp_path / "runs" / "crypto_universe_refresh" / "malformed"
    bars_csv.write_text(
        "timestamp,symbol,asset_class,open,high,low,close,volume\n"
        "not-a-date,BTCUSD,crypto,1,1,1,1,1\n",
        encoding="utf-8",
    )
    status_json.write_text("{not-json", encoding="utf-8")

    packet = run_crypto_universe_refresh(
        output_root=output_root,
        mode="local_replay",
        bars_csv=bars_csv,
        crypto_visibility_status=status_json,
        as_of=AS_OF,
        write_artifacts=True,
    )
    rejected = packet["summary"]["local_artifacts_rejected"]
    reasons = {record["rejection_reason"] for record in rejected}

    assert packet["summary"]["local_artifacts_discovered_count"] == 2
    assert packet["summary"]["local_artifacts_accepted_count"] == 0
    assert "malformed_json_artifact" in reasons
    assert "no_crypto_bars" in reasons


def test_router_consumes_refresh_manifest_and_selects_fixture_crypto(tmp_path: Path) -> None:
    refresh_root = tmp_path / "runs" / "crypto_universe_refresh" / "latest"
    router_root = tmp_path / "runs" / "opportunity_router" / "latest"
    run_crypto_universe_refresh(
        output_root=refresh_root,
        mode="offline_fixture",
        as_of=AS_OF,
        write_artifacts=True,
    )

    packet = run_opportunity_router(
        output_root=router_root,
        spy_bars_csv=tmp_path / "missing_spy.csv",
        crypto_router_input_manifest=refresh_root / "crypto_router_input_manifest.json",
        as_of=AS_OF,
        write_artifacts=True,
    )
    decision = packet["router_decision"]

    assert decision["decision"] == "selected"
    assert decision["selected_asset_class"] == "crypto"
    assert decision["selected_symbol"] == "BTCUSD"
    assert decision["selected_candidate_backing"] == "fixture_backed"
    assert decision["selected_candidate"]["candidate_backing"] == "fixture_backed"
    assert decision["eligible_candidate_count"] >= 1
    assert any(
        candidate["symbol"] == "ETHUSD" and candidate["blocker_status"] == "blocked"
        for candidate in packet["candidates"]
    )
    assert (router_root / "manifest.json").is_file()


def test_router_consumes_local_replay_manifest_and_marks_real_local_backing(
    tmp_path: Path,
) -> None:
    bars_csv = tmp_path / "crypto_bars.csv"
    status_json = tmp_path / "latest_status.json"
    refresh_root = tmp_path / "runs" / "crypto_universe_refresh" / "local_replay"
    router_root = tmp_path / "runs" / "opportunity_router" / "local_replay"
    _write_crypto_csv(bars_csv, "ETHUSD", count=80)
    status_json.write_text(
        json.dumps(
            {
                "broker_state_mode": "alpaca_paper_observed",
                "eligible_crypto_symbols": ["ETH/USD"],
                "asset_metadata": {
                    "ETH/USD": {
                        "asset_class": "crypto",
                        "tradable": True,
                        "status": "active",
                        "min_notional": "10",
                        "min_order_size": "0.0001",
                        "min_trade_increment": "0.0001",
                    }
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    run_crypto_universe_refresh(
        output_root=refresh_root,
        mode="local_replay",
        bars_csv=bars_csv,
        crypto_visibility_status=status_json,
        as_of=AS_OF,
        write_artifacts=True,
    )

    packet = run_opportunity_router(
        output_root=router_root,
        spy_bars_csv=tmp_path / "missing_spy.csv",
        crypto_router_input_manifest=refresh_root / "crypto_router_input_manifest.json",
        as_of=AS_OF,
        write_artifacts=True,
    )
    decision = packet["router_decision"]

    assert decision["decision"] == "selected"
    assert decision["selected_asset_class"] == "crypto"
    assert decision["selected_symbol"] == "ETHUSD"
    assert decision["selected_candidate_backing"] == "real_local_artifact_backed"
    assert "local_replay" in decision["labels"]
    assert "real_local_artifact_backed" in decision["selected_candidate"]["labels"]
    assert packet["safety"]["paper_submit_performed"] is False


def test_router_returns_no_trade_when_all_refreshed_crypto_inputs_blocked(
    tmp_path: Path,
) -> None:
    bars_csv = tmp_path / "empty_crypto_bars.csv"
    status_json = tmp_path / "latest_status.json"
    refresh_root = tmp_path / "runs" / "crypto_universe_refresh" / "latest"
    _write_empty_crypto_csv(bars_csv)
    status_json.write_text(
        json.dumps(
            {
                "broker_state_mode": "alpaca_paper_observed",
                "crypto_capability": {"eligible_crypto_symbols": ["ETH/USD"]},
                "asset_metadata": {
                    "ETH/USD": {
                        "asset_class": "crypto",
                        "tradable": True,
                        "status": "active",
                        "min_notional": "10",
                        "min_order_size": "0.0001",
                        "min_trade_increment": "0.0001",
                    }
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    run_crypto_universe_refresh(
        output_root=refresh_root,
        mode="local_replay",
        bars_csv=bars_csv,
        crypto_visibility_status=status_json,
        as_of=AS_OF,
        write_artifacts=True,
    )

    packet = run_opportunity_router(
        output_root=tmp_path / "runs" / "opportunity_router" / "blocked",
        spy_bars_csv=tmp_path / "missing_spy.csv",
        crypto_router_input_manifest=refresh_root / "crypto_router_input_manifest.json",
        as_of=AS_OF,
        write_artifacts=True,
    )
    decision = packet["router_decision"]
    blockers = {item["blocker"] for item in decision["top_blockers"]}

    assert decision["decision"] == "no_trade"
    assert decision["selected_candidate_id"] is None
    assert "missing_data" in blockers
    assert "missing_history" in blockers


def test_refresh_history_report_detects_stale_insufficient_and_duplicate_data(
    tmp_path: Path,
) -> None:
    bars_csv = tmp_path / "crypto_bars.csv"
    status_json = tmp_path / "latest_status.json"
    output_root = tmp_path / "runs" / "crypto_universe_refresh" / "latest"
    _write_mixed_crypto_csv(bars_csv)
    metadata = {
        symbol: {
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
            "min_notional": "10",
            "min_order_size": "0.0001",
            "min_trade_increment": "0.0001",
        }
        for symbol in ("STALE/USD", "SHORT/USD", "DUP/USD")
    }
    status_json.write_text(
        json.dumps(
            {
                "broker_state_mode": "alpaca_paper_observed",
                "eligible_crypto_symbols": ["STALE/USD", "SHORT/USD", "DUP/USD"],
                "asset_metadata": metadata,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    packet = run_crypto_universe_refresh(
        output_root=output_root,
        mode="local_replay",
        bars_csv=bars_csv,
        crypto_visibility_status=status_json,
        as_of=AS_OF,
        write_artifacts=True,
    )
    history = {
        record["symbol"]: record
        for record in packet["crypto_history_quality_report"]["records"]
    }

    assert history["STALEUSD"]["freshness_status"] == "stale_data"
    assert history["STALEUSD"]["stale_data_blocker"] is True
    assert history["SHORTUSD"]["history_status"] == "insufficient_history"
    assert history["SHORTUSD"]["insufficient_history_blocker"] is True
    assert history["DUPUSD"]["duplicate_timestamp_status"] == "duplicate_timestamps_present"
    assert "duplicate_timestamps" in history["DUPUSD"]["blockers"]
    router_records = {
        record["symbol"]: record
        for record in packet["crypto_router_input_manifest"]["records"]
    }
    assert "history_stale" in router_records["STALEUSD"]["local_replay_classifications"]
    assert "insufficient_history" in router_records["SHORTUSD"]["local_replay_classifications"]


def test_crypto_universe_refresh_has_no_broker_network_or_mutation_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_prefixes = (
        "algotrader.execution",
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )
    imports = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]
    imports.extend(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    text = MODULE_PATH.read_text(encoding="utf-8")

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imports
        for prefix in forbidden_prefixes
    )
    assert "submit_order" not in text
    assert "cancel_order" not in text
    assert "replace_order" not in text
    assert "liquidate" not in text


def test_run_crypto_universe_refresh_script_contract() -> None:
    script = Path("scripts/run_crypto_universe_refresh.ps1").read_text(encoding="utf-8")

    assert '[string]$Mode = "offline_fixture"' in script
    assert '[string]$OutputRoot = "runs\\crypto_universe_refresh\\latest"' in script
    assert "crypto_universe_refresh_no_submit_enforced=true" in script
    assert "Credential values are never printed" in script
    assert "blocked_unsafe_environment" in script
    assert "run_crypto_paper_visibility_cycle.ps1" in script
    assert '"-m", "algotrader.orchestration.crypto_universe_refresh"' in script
    assert "paper_submit_performed=false" in script
    assert "broker_mutation_performed=false" in script
    assert "live_mutation_performed=false" in script


def _bars(
    symbol: str,
    as_of: datetime,
    *,
    count: int,
    posture: str = "up",
) -> tuple[Bar, ...]:
    first = as_of - timedelta(hours=count - 1)
    bars: list[Bar] = []
    for index in range(count):
        price = Decimal("100") + Decimal(index)
        if posture == "down":
            price = Decimal("500") - Decimal(index)
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=first + timedelta(hours=index),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1000"),
            )
        )
    return tuple(bars)


def _write_crypto_csv(path: Path, symbol: str, *, count: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume"))
        for bar in _bars(symbol, AS_OF, count=count):
            writer.writerow(
                (
                    bar.timestamp.isoformat(),
                    bar.symbol,
                    "crypto",
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                )
            )


def _write_empty_crypto_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume"))


def _write_mixed_crypto_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume"))
        for bar in _bars("STALEUSD", AS_OF - timedelta(days=2), count=80):
            _write_bar_row(writer, bar)
        for bar in _bars("SHORTUSD", AS_OF, count=10):
            _write_bar_row(writer, bar)
        duplicate_bars = (*_bars("DUPUSD", AS_OF, count=80), _bars("DUPUSD", AS_OF, count=80)[-1])
        for bar in duplicate_bars:
            _write_bar_row(writer, bar)


def _write_bar_row(writer: csv.writer, bar: Bar) -> None:
    writer.writerow(
        (
            bar.timestamp.isoformat(),
            bar.symbol,
            "crypto",
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
        )
    )
