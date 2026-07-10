from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.execution.crypto_history_refresh_adapter import (
    CryptoHistoryRefreshConfig,
)
from algotrader.orchestration.crypto_repair_forward_oos_accrual import (
    run_crypto_repair_forward_oos_accrual,
)
from algotrader.orchestration.crypto_research_pipeline import (
    CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION,
    run_crypto_research_pipeline,
)
from algotrader.research.crypto_strategy_evidence_battery import (
    CRYPTO_STRATEGY_CANDIDATE_FACTORY_VERSION,
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
    DEFAULT_FRESH_OOS_REPAIR_CANDIDATE,
    build_crypto_strategy_candidate_factory,
)


CUTOFF = datetime(2026, 7, 9, 16, 0, tzinfo=UTC)


def test_multi_asset_pipeline_builds_auditable_scanner_and_fixed_registry(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    availability = tmp_path / "availability.json"
    _write_history(history, _history_rows())
    _write_availability(availability)

    packet = _run(tmp_path, history, availability=availability)

    assert packet["schema_version"] == CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION
    assert packet["universe"]["scanned_symbols"] == list(
        DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    )
    assert packet["universe"]["rows_per_symbol"] == {
        symbol: 80 for symbol in sorted(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS)
    }
    scanner_records = packet["scanner"]["records"]
    assert {record["symbol"] for record in scanner_records} == set(
        DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    )
    assert all(record["usable_bar_count"] == 80 for record in scanner_records)
    assert all(record["freshness_status"] == "fresh" for record in scanner_records)
    assert all(
        record["liquidity_proxy"]["status"]
        == "positive_volume_observed_not_a_liquidity_guarantee"
        for record in scanner_records
    )
    assert all(
        record["regime_characteristics"]["status"] == "classified"
        for record in scanner_records
    )

    factory = packet["strategy_factory"]
    assert factory["factory_version"] == CRYPTO_STRATEGY_CANDIDATE_FACTORY_VERSION
    assert factory["fixed_candidate_count_per_symbol"] == 5
    assert factory["dynamic_parameter_optimization"] is False
    assert factory["post_hoc_retuning"] is False
    assert factory["candidate_set_mutation_allowed"] is False

    registry = packet["ranked_candidate_registry"]
    assert packet["candidate_counts"]["considered"] == 20
    assert packet["candidate_counts"]["ranked"] == 20
    assert packet["candidate_counts"]["not_planning_eligible"] == 20
    assert [item["registry_rank"] for item in registry] == list(range(1, 21))
    assert len({item["candidate_id"] for item in registry}) == 20
    assert len({item["candidate_fingerprint"] for item in registry}) == 20
    assert all(len(item["candidate_fingerprint"]) == 64 for item in registry)
    assert all(
        item["no_submit_planning_eligibility"]
        in {"eligible_for_no_submit_plan", "not_eligible"}
        for item in registry
    )

    artifact_paths = packet["artifact_paths"]
    assert Path(artifact_paths["operator_packet_json"]).is_file()
    assert Path(artifact_paths["operator_packet_markdown"]).is_file()
    assert Path(artifact_paths["candidate_registry"]).is_file()
    assert Path(artifact_paths["normalized_history"]).is_file()


def test_ranking_and_candidate_fingerprints_are_deterministic(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    availability = tmp_path / "availability.json"
    _write_history(history, _history_rows())
    _write_availability(availability)

    first = _run(tmp_path / "first", history, availability=availability)
    second = _run(tmp_path / "second", history, availability=availability)

    first_registry = _registry_projection(first)
    second_registry = _registry_projection(second)
    assert second_registry == first_registry
    assert second["candidate_counts"] == first["candidate_counts"]
    assert second["strategy_factory"] == first["strategy_factory"]

    earlier = _run(
        tmp_path / "earlier",
        history,
        availability=availability,
        discovery_cutoff=CUTOFF - timedelta(hours=1),
    )
    earlier_fingerprints = {
        item["candidate_id"]: item["candidate_fingerprint"]
        for item in earlier["ranked_candidate_registry"]
    }
    assert all(
        earlier_fingerprints[item["candidate_id"]]
        != item["candidate_fingerprint"]
        for item in first["ranked_candidate_registry"]
    )


def test_scanner_rejections_propagate_to_every_symbol_candidate(
    tmp_path: Path,
) -> None:
    history = tmp_path / "partial_history.csv"
    rows = _history_rows(rows_by_symbol={"SOLUSD": 20})
    _write_history(history, rows)

    packet = _run(tmp_path, history)

    sol_scan = next(
        item for item in packet["scanner"]["records"] if item["symbol"] == "SOLUSD"
    )
    assert sol_scan["research_scan_status"] == "excluded"
    assert "insufficient_evidence_history" in sol_scan["rejection_reasons"]
    sol_candidates = [
        item
        for item in packet["ranked_candidate_registry"]
        if item["candidate_id"].startswith("crypto:SOLUSD:")
    ]
    assert len(sol_candidates) == 5
    assert all(
        "insufficient_history" in item["rejection_reasons"]
        or "signal_status_insufficient_history" in item["rejection_reasons"]
        for item in sol_candidates
    )
    assert all(
        item["no_submit_planning_eligibility"] == "not_eligible"
        for item in sol_candidates
    )


def test_existing_ada_candidate_routes_to_awaiting_fresh_oos_and_no_submit(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    _write_history(history, _history_rows())

    packet = _run(tmp_path, history)

    ada = next(
        item
        for item in packet["ranked_candidate_registry"]
        if item["candidate_id"] == DEFAULT_FRESH_OOS_REPAIR_CANDIDATE
    )
    assert ada["evidence_status"] == "awaiting_fresh_oos"
    assert ada["forward_oos_status"] == "awaiting_fresh_oos"
    assert ada["forward_oos_rows_remaining"] == 26
    assert ada["no_submit_planning_eligibility"] == "not_eligible"
    assert "awaiting_fresh_oos_rows" in ada["rejection_reasons"]
    assert len(ada["candidate_fingerprint"]) == 64

    frozen = packet["frozen_candidates"]
    assert len(frozen) == 1
    assert frozen[0]["candidate_id"] == DEFAULT_FRESH_OOS_REPAIR_CANDIDATE
    assert frozen[0]["classification"] == "awaiting_fresh_oos"
    assert frozen[0]["rows_still_required"] == 26
    assert frozen[0]["paper_planning_eligibility"] == "not_eligible"
    assert len(frozen[0]["frozen_candidate_fingerprint"]) == 64
    assert packet["forward_oos"]["oos_rows"] == 0
    assert packet["no_submit_planning"]["paper_submit_authorized"] is False


def test_pipeline_side_effect_contract_is_offline_and_no_submit(tmp_path: Path) -> None:
    history = tmp_path / "history.csv"
    _write_history(history, _history_rows())

    packet = _run(tmp_path, history)
    side_effects = packet["side_effects"]

    for field_name in (
        "paper_submit_authorized",
        "broker_mutation_authorized",
        "live_authorized",
        "broker_read_occurred",
        "broker_mutation_occurred",
        "paper_submit_occurred",
        "paper_cancel_occurred",
        "paper_replace_occurred",
        "paper_close_occurred",
        "paper_liquidate_occurred",
        "live_endpoint_touched",
        "credential_values_accessed",
        "credential_values_exposed",
        "market_data_fetch_occurred",
        "network_access_attempted",
        "broker_sdk_imported",
        "runs_tracked",
    ):
        assert side_effects[field_name] is False
    assert side_effects["local_files_written"] is True
    assert packet["no_submit_planning"]["broker_execution_eligibility"] == "not_eligible"
    assert packet["profit_claim"] == "none"


def test_pipeline_consumes_forward_oos_without_overwriting_refresh_state(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.csv"
    delta = tmp_path / "forward_oos_delta.csv"
    state_root = tmp_path / "forward_oos"
    runtime_as_of = CUTOFF + timedelta(hours=9)
    _write_history(history, _history_rows())
    run_crypto_repair_forward_oos_accrual(
        output_root=state_root,
        discovery_history_path=history,
        as_of=CUTOFF,
    )
    _write_history(delta, _future_ada_rows(8))
    config = CryptoHistoryRefreshConfig(
        mode="market_data_fetch",
        output_path=delta,
        packet_path=state_root / "refresh" / "refresh_packet.json",
        raw_response_path=state_root / "refresh" / "raw_crypto_bars.json",
        as_of=runtime_as_of,
        market_data_fetch_authorized=True,
        allow_network=True,
    )

    def _refresh(_: CryptoHistoryRefreshConfig) -> dict[str, object]:
        return {
            "classification": "insufficient_real_crypto_history",
            "mode": "market_data_fetch",
            "output_path": str(delta),
            "packet_path": str(config.packet_path),
            "raw_response_path": str(config.raw_response_path),
            "market_data_fetch_occurred": True,
            "network_access_attempted": True,
        }

    refresh_packet = run_crypto_repair_forward_oos_accrual(
        output_root=state_root,
        discovery_history_path=history,
        refresh_config=config,
        refresh_runner=_refresh,
        as_of=runtime_as_of,
    )
    operating_path = Path(refresh_packet["artifact_paths"]["operating_packet_json"])
    accrued_path = Path(refresh_packet["artifact_paths"]["accrued_oos"])
    operating_before = operating_path.read_bytes()
    accrued_before = accrued_path.read_bytes()

    packet = run_crypto_research_pipeline(
        history,
        as_of=runtime_as_of,
        output_root=tmp_path / "pipeline",
        forward_oos_state_root=state_root,
    )

    assert operating_path.read_bytes() == operating_before
    assert accrued_path.read_bytes() == accrued_before
    assert packet["classification"] == "research_only_awaiting_fresh_oos"
    assert packet["forward_oos"]["oos_rows"] == 8
    assert packet["forward_oos"]["rows_still_required"] == 18
    assert packet["forward_oos"]["paper_planning_eligibility"] == "not_eligible"
    ada = next(
        item
        for item in packet["ranked_candidate_registry"]
        if item["candidate_id"] == DEFAULT_FRESH_OOS_REPAIR_CANDIDATE
    )
    assert ada["no_submit_planning_eligibility"] == "not_eligible"
    preserved = json.loads(operating_path.read_text(encoding="utf-8"))
    assert preserved["refresh"]["mode"] == "market_data_fetch"
    assert preserved["refresh"]["status"] == "insufficient_real_crypto_history"
    assert preserved["market_data_fetch_occurred"] is True


def test_factory_descriptor_reuses_exact_fixed_evidence_specs() -> None:
    factory = build_crypto_strategy_candidate_factory()

    assert [
        item["strategy_id"] for item in factory["base_candidates"]
    ] == [
        "trend_momentum_1",
        "breakout_4",
        "moving_average_regime_3_6",
        "volatility_filter_4",
    ]
    assert [
        item["strategy_id"]
        for item in factory["diagnostic_repair_candidates"]
    ] == ["trend_momentum_24h_repair"]


def test_powershell_runner_exposes_only_offline_local_replay() -> None:
    script = Path("scripts/run_crypto_research_pipeline.ps1").read_text(
        encoding="utf-8"
    )

    assert "algotrader.orchestration.crypto_research_pipeline" in script
    assert "--allow-network" not in script
    assert "market_data_fetch" not in script
    assert "submit" in script.lower()
    assert "ForwardOosRecoverySourcePath" in script
    assert "runs\\operator_input\\crypto_paper_bars.csv" not in script


def _run(
    root: Path,
    history: Path,
    *,
    availability: Path | None = None,
    discovery_cutoff: datetime = CUTOFF,
) -> dict[str, object]:
    state_root = root / "forward_oos"
    run_crypto_repair_forward_oos_accrual(
        output_root=state_root,
        discovery_history_path=history,
        as_of=CUTOFF,
        discovery_cutoff=discovery_cutoff,
    )
    return run_crypto_research_pipeline(
        history,
        as_of=CUTOFF,
        output_root=root / "pipeline",
        availability_json_path=availability,
        discovery_cutoff=discovery_cutoff,
        forward_oos_state_root=state_root,
    )


def _registry_projection(
    packet: dict[str, object],
) -> list[tuple[object, ...]]:
    return [
        (
            item["registry_rank"],
            item["candidate_id"],
            item["candidate_fingerprint"],
            item["evidence_status"],
            item["forward_oos_status"],
            item["forward_oos_rows_remaining"],
            item["no_submit_planning_eligibility"],
            tuple(item["rejection_reasons"]),
        )
        for item in packet["ranked_candidate_registry"]
    ]


def _history_rows(
    *,
    rows_by_symbol: dict[str, int] | None = None,
) -> tuple[dict[str, str], ...]:
    counts = rows_by_symbol or {}
    rows: list[dict[str, str]] = []
    for symbol_index, symbol in enumerate(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS):
        count = counts.get(symbol, 80)
        start = CUTOFF - timedelta(hours=count - 1)
        base = Decimal("100") + Decimal(symbol_index * 25)
        for index in range(count):
            drift = Decimal(index) * Decimal("0.25")
            cycle = Decimal((index % 7) - 3) * Decimal("0.10")
            close = base + drift + cycle
            rows.append(
                {
                    "timestamp": (start + timedelta(hours=index)).isoformat(),
                    "symbol": symbol,
                    "open": str(close),
                    "high": str(close + Decimal("1")),
                    "low": str(close - Decimal("1")),
                    "close": str(close),
                    "volume": str(Decimal("10") + Decimal(index)),
                    "source": "recorded_local_history",
                }
            )
    return tuple(rows)


def _future_ada_rows(count: int) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for index in range(count):
        close = Decimal("200") + Decimal(index)
        rows.append(
            {
                "timestamp": (
                    CUTOFF + timedelta(hours=index + 1)
                ).isoformat(),
                "symbol": "ADAUSD",
                "open": str(close),
                "high": str(close + Decimal("1")),
                "low": str(close - Decimal("1")),
                "close": str(close),
                "volume": "10",
                "source": "alpaca_market_data_crypto_bars_v1beta3",
            }
        )
    return tuple(rows)


def _write_history(path: Path, rows: tuple[dict[str, str], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "timestamp",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "source",
            ),
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_availability(path: Path) -> None:
    records = [
        {
            "symbol": symbol,
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
            "min_notional": "10",
            "min_order_size": "0.001",
            "min_trade_increment": "0.001",
            "orderability_status": "orderable",
        }
        for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    ]
    path.write_text(
        json.dumps(
            {
                "broker_state_mode": "simulated_offline",
                "records": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
