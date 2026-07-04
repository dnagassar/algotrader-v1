from __future__ import annotations

import ast
import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.orchestration.opportunity_router import (
    OPPORTUNITY_ROUTER_REQUIRED_LABELS,
    OPPORTUNITY_ROUTER_SCHEMA_VERSION,
    OpportunityCandidate,
    build_crypto_opportunity_candidates_for_symbol,
    build_spy_sma_opportunity_candidate,
    classify_bar_history,
    normalize_crypto_asset_metadata,
    route_opportunities,
    run_opportunity_router,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)


AS_OF = datetime(2026, 7, 4, 0, 30, tzinfo=UTC)
MODULE_PATH = Path("src/algotrader/orchestration/opportunity_router.py")


def test_opportunity_candidate_validation_requires_profit_claim_label() -> None:
    with pytest.raises(ValidationError, match="profit_claim=none label"):
        _candidate(labels=("paper_lab_only", "not_live_authorized", "no_submit_mode"))


def test_spy_sma_candidate_adaptation_is_backtest_supported_and_selectable_in_simulation() -> None:
    result = evaluate_etf_sma_signal(
        _daily_bars("SPY", AS_OF, count=220, posture="up"),
        EtfSmaSignalConfig(as_of=AS_OF, symbol="SPY"),
    )

    candidate = build_spy_sma_opportunity_candidate(
        result,
        broker_state_mode="simulated_offline",
        orderability_status="orderable",
        as_of=AS_OF,
    )
    decision = route_opportunities((candidate,), as_of=AS_OF).to_dict()

    assert candidate.candidate_id == "equity:SPY:spy_sma_50_200_training_wheel"
    assert candidate.asset_class == "equity"
    assert candidate.signal_status == "trade_candidate"
    assert candidate.evidence_tier == "backtest_supported"
    assert set(OPPORTUNITY_ROUTER_REQUIRED_LABELS) <= set(candidate.labels)
    assert decision["decision"] == "selected"
    assert decision["selected_candidate_id"] == candidate.candidate_id


def test_crypto_candidate_source_adapts_non_btc_symbol_and_first_pass_strategies() -> None:
    metadata = normalize_crypto_asset_metadata(
        {
            "symbol": "ETH/USD",
            "asset_class": "crypto",
            "tradable": "true",
            "status": "active",
            "min_order_notional": "10",
            "min_order_size": "0.0001",
            "qty_increment": "0.0001",
            "price_increment": "0.01",
        }
    )

    candidates = build_crypto_opportunity_candidates_for_symbol(
        symbol="ETH/USD",
        bars=_bars("ETHUSD", AS_OF, count=80, posture="up", step=Decimal("2")),
        as_of=AS_OF,
        asset_metadata=metadata,
        broker_state_mode="alpaca_paper_observed",
    )
    decision = route_opportunities(candidates, as_of=AS_OF).to_dict()

    assert {candidate.symbol for candidate in candidates} == {"ETHUSD"}
    assert {candidate.strategy_id for candidate in candidates} == {
        "crypto_sma_20_50_training_wheel_preview",
        "crypto_vol_adjusted_momentum_24h_preview",
        "crypto_breakout_reversion_20h_flag_preview",
    }
    assert all(candidate.evidence_tier == "signal_only" for candidate in candidates)
    assert decision["decision"] == "selected"
    assert decision["selected_symbol"] == "ETHUSD"


def test_metadata_variant_normalization_marks_missing_gaps_without_assuming_tradability() -> None:
    complete = normalize_crypto_asset_metadata(
        {
            "symbol": "SOL/USD",
            "class": "crypto",
            "tradable": True,
            "min_order_notional": "10",
            "min_trade_increment": "0.000001",
            "price_increment": "0.01",
        }
    )
    missing = build_crypto_opportunity_candidates_for_symbol(
        symbol="SOLUSD",
        bars=_bars("SOLUSD", AS_OF, count=80, posture="up"),
        as_of=AS_OF,
        asset_metadata={"symbol": "SOLUSD", "asset_class": "crypto", "tradable": True},
        broker_state_mode="alpaca_paper_observed",
    )

    assert complete["symbol"] == "SOLUSD"
    assert complete["min_notional"] == "10"
    assert complete["min_trade_increment"] == "0.000001"
    assert complete["price_increment"] == "0.01"
    assert all(candidate.orderability_status == "metadata_missing" for candidate in missing)
    assert all("metadata_missing" in candidate.blockers for candidate in missing)


def test_history_classifier_reports_missing_stale_insufficient_and_duplicate_data() -> None:
    missing = classify_bar_history(
        symbol="BTCUSD",
        asset_class="crypto",
        bars=(),
        as_of=AS_OF,
        required_bar_count=50,
        max_bar_age=timedelta(hours=2),
        data_path="memory",
        source_mode="test",
    )
    stale = classify_bar_history(
        symbol="BTCUSD",
        asset_class="crypto",
        bars=_bars("BTCUSD", AS_OF - timedelta(days=3), count=60, posture="up"),
        as_of=AS_OF,
        required_bar_count=50,
        max_bar_age=timedelta(hours=2),
        data_path="memory",
        source_mode="test",
    )
    insufficient = classify_bar_history(
        symbol="BTCUSD",
        asset_class="crypto",
        bars=_bars("BTCUSD", AS_OF, count=10, posture="up"),
        as_of=AS_OF,
        required_bar_count=50,
        max_bar_age=timedelta(hours=2),
        data_path="memory",
        source_mode="test",
    )
    duplicate_bars = (
        *_bars("BTCUSD", AS_OF, count=5, posture="up"),
        _bars("BTCUSD", AS_OF, count=5, posture="up")[-1],
    )
    duplicate = classify_bar_history(
        symbol="BTCUSD",
        asset_class="crypto",
        bars=duplicate_bars,
        as_of=AS_OF,
        required_bar_count=5,
        max_bar_age=timedelta(hours=2),
        data_path="memory",
        source_mode="test",
    )

    assert missing.history_status == "missing_history"
    assert missing.freshness_status == "missing_data"
    assert stale.freshness_status == "stale_data"
    assert insufficient.history_status == "insufficient_history"
    assert duplicate.data_quality_status == "duplicate_timestamps"
    assert duplicate.duplicate_timestamps


def test_router_ranking_and_tie_breaking_are_deterministic() -> None:
    later = _candidate(candidate_id="crypto:BTCUSD:z_strategy")
    earlier = _candidate(candidate_id="crypto:BTCUSD:a_strategy")

    first = route_opportunities((later, earlier), as_of=AS_OF).to_dict()
    second = route_opportunities((later, earlier), as_of=AS_OF).to_dict()

    assert first == second
    assert first["selected_candidate_id"] == "crypto:BTCUSD:a_strategy"


def test_blocked_candidate_cannot_be_selected_even_with_higher_score() -> None:
    blocked = _candidate(
        candidate_id="crypto:BTCUSD:blocked_high_score",
        blocker_status="blocked",
        blockers=("stale_data",),
        freshness_status="stale_data",
        score_components={
            "broker_state": Decimal("10"),
            "data_quality": Decimal("15"),
            "evidence": Decimal("25"),
            "orderability": Decimal("5"),
            "safety": Decimal("5"),
            "signal": Decimal("40"),
            "signal_strength": Decimal("5"),
        },
    )
    eligible = _candidate(candidate_id="crypto:BTCUSD:eligible_lower_score")

    decision = route_opportunities((blocked, eligible), as_of=AS_OF).to_dict()

    assert decision["decision"] == "selected"
    assert decision["selected_candidate_id"] == eligible.candidate_id
    assert blocked.candidate_id in decision["categories"]["blocked"]


def test_router_returns_no_trade_when_all_candidates_blocked() -> None:
    blocked = _candidate(
        blocker_status="blocked",
        blockers=("broker_state_not_observed",),
        broker_state_mode="broker_state_not_observed",
    )

    decision = route_opportunities((blocked,), as_of=AS_OF).to_dict()

    assert decision["decision"] == "no_trade"
    assert decision["selected_candidate_id"] is None
    assert decision["paper_submit_performed"] is False
    assert "broker_state_not_observed" in decision["categories"]


def test_selected_candidate_includes_required_safety_labels() -> None:
    selected = route_opportunities((_candidate(),), as_of=AS_OF).selected_candidate

    assert selected is not None
    assert set(OPPORTUNITY_ROUTER_REQUIRED_LABELS) <= set(selected.labels)
    assert "research_only" in selected.labels
    assert selected.profit_claim == "none"


def test_artifact_manifest_integrity_and_operating_artifacts(tmp_path: Path) -> None:
    spy_csv = tmp_path / "spy.csv"
    crypto_csv = tmp_path / "crypto.csv"
    status_json = tmp_path / "crypto_status.json"
    output_root = tmp_path / "runs" / "opportunity_router" / "latest"
    _write_spy_csv(spy_csv)
    _write_crypto_csv(crypto_csv, "ETHUSD")
    status_json.write_text(
        json.dumps(
            {
                "broker_state_mode": "alpaca_paper_observed",
                "capability_source": "simulated",
                "crypto_capability": {
                    "eligible_crypto_symbols": ["ETH/USD", "BTC/USD"],
                    "selected_symbol": "ETH/USD",
                    "selected_symbol_tradable": True,
                    "selected_symbol_marginable": False,
                    "selected_symbol_fractionable": True,
                    "min_order_size": "0.0001",
                    "min_trade_increment": "0.0001",
                    "min_notional": "10",
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    packet = run_opportunity_router(
        output_root=output_root,
        spy_bars_csv=spy_csv,
        crypto_bars_csv=crypto_csv,
        crypto_visibility_status=status_json,
        as_of=AS_OF,
        write_artifacts=True,
    )
    artifact_paths = packet["artifact_paths"]
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))

    expected = {
        "opportunity_candidates.json",
        "opportunity_candidates.csv",
        "router_decision.json",
        "operating_brief.md",
        "operating_record.jsonl",
        "universe_manifest.json",
        "strategy_manifest.json",
        "data_quality_report.json",
        "manifest.json",
    }
    assert expected == {Path(path).name for path in artifact_paths.values()}
    assert manifest["schema_version"] == OPPORTUNITY_ROUTER_SCHEMA_VERSION
    assert set(manifest["required_artifacts"]) == {
        "data_quality_report",
        "operating_brief",
        "operating_record",
        "opportunity_candidates_csv",
        "opportunity_candidates_json",
        "router_decision",
        "strategy_manifest",
        "universe_manifest",
    }
    assert packet["router_decision"]["paper_submit_authorized"] is False
    assert packet["router_decision"]["broker_mutation_performed"] is False
    assert packet["router_decision"]["live_mutation_performed"] is False
    assert "ETHUSD" in packet["router_decision"]["candidate_count_by_asset_class"].values() or (
        packet["router_decision"]["candidate_count_by_asset_class"]["crypto"] == 6
    )


def test_opportunity_router_has_no_broker_network_or_mutation_imports() -> None:
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


def test_generated_runs_files_are_ignored_and_not_tracked() -> None:
    assert "runs/" in Path(".gitignore").read_text(encoding="utf-8")
    if shutil.which("git") is None:
        pytest.skip("git is required for tracked-runs invariant")

    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def _candidate(
    *,
    candidate_id: str = "crypto:BTCUSD:eligible",
    labels: tuple[str, ...] = (
        "paper_lab_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "offline_only",
    ),
    blocker_status: str = "eligible",
    blockers: tuple[str, ...] = (),
    freshness_status: str = "fresh",
    broker_state_mode: str = "simulated_offline",
    score_components: dict[str, Decimal] | None = None,
) -> OpportunityCandidate:
    components = score_components or {
        "broker_state": Decimal("10"),
        "data_quality": Decimal("15"),
        "evidence": Decimal("10"),
        "orderability": Decimal("5"),
        "safety": Decimal("5"),
        "signal": Decimal("40"),
        "signal_strength": Decimal("0"),
    }
    return OpportunityCandidate(
        candidate_id=candidate_id,
        as_of=AS_OF,
        asset_class="crypto",
        symbol="BTCUSD",
        venue="alpaca_crypto",
        source="test",
        strategy_id=candidate_id.rsplit(":", 1)[-1],
        strategy_family="test_strategy",
        signal_direction="long",
        signal_status="trade_candidate",
        evidence_tier="signal_only",
        data_quality_status="valid",
        history_status="sufficient_history",
        freshness_status=freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status="orderable",
        blocker_status=blocker_status,
        blockers=blockers,
        risk_notes=("router_score_is_not_expected_profit",),
        score_components=components,
        router_score=sum(components.values(), Decimal("0")),
        labels=labels,
    )


def _bars(
    symbol: str,
    as_of: datetime,
    *,
    count: int,
    posture: str,
    step: Decimal = Decimal("1"),
) -> tuple[Bar, ...]:
    first = as_of - timedelta(hours=count - 1)
    bars: list[Bar] = []
    for index in range(count):
        price = Decimal("100") + Decimal(index) * step
        if posture == "down":
            price = Decimal("500") - Decimal(index) * step
        timestamp = first + timedelta(hours=index)
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=timestamp,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1000"),
            )
        )
    return tuple(bars)


def _daily_bars(
    symbol: str,
    as_of: datetime,
    *,
    count: int,
    posture: str,
) -> tuple[Bar, ...]:
    first = as_of - timedelta(days=count - 1)
    bars: list[Bar] = []
    for index in range(count):
        price = Decimal("100") + Decimal(index)
        if posture == "down":
            price = Decimal("500") - Decimal(index)
        timestamp = first + timedelta(days=index)
        bars.append(
            Bar(
                symbol=symbol,
                timestamp=timestamp,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1000"),
            )
        )
    return tuple(bars)


def _write_spy_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"))
        first = AS_OF.date() - timedelta(days=219)
        for index in range(220):
            price = Decimal("100") + Decimal(index)
            writer.writerow(("SPY", (first + timedelta(days=index)).isoformat(), price, price, price, price, price, 1000))


def _write_crypto_csv(path: Path, symbol: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("timestamp", "symbol", "asset_class", "open", "high", "low", "close", "volume"))
        for bar in _bars(symbol, AS_OF, count=80, posture="up", step=Decimal("2")):
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
