from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.alpha_candidate_batch_scout import (
    ALPHA_CANDIDATE_BATCH_SCOUT_DECISIONS,
    alpha_candidate_mutation_policy,
    build_alpha_candidate_batch_packet,
    build_fixed_alpha_candidate_definitions,
    write_alpha_candidate_batch_artifacts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "src" / "algotrader" / "research" / "alpha_candidate_batch_scout.py"
)

EXPECTED_CANDIDATE_IDS = (
    "spy_vol_scaled_trend_20d_fixed",
    "spy_breakout_252d_trailing_63d_fixed",
    "spy_drawdown_recovery_252d_20_10_fixed",
    "spy_ma200_slope_20d_filter_fixed",
    "spy_rsi2_mean_reversion_trend_filter_fixed",
    "spy_vs_qqq_relative_strength_126d_fixed",
)

EXPECTED_WINDOW_IDS = (
    "full_available_reference",
    "chronological_earlier_half",
    "chronological_later_half",
    "trailing_5y_earlier_half",
    "trailing_5y_later_half",
    "recent_3y_holdout",
)

REQUIRED_WINDOW_RECORD_FIELDS = {
    "candidate_id",
    "fixed_parameters",
    "parameters_evaluated",
    "window_id",
    "metrics",
    "comparator_metrics",
    "delta_vs_buy_and_hold",
    "delta_vs_sma50_200",
    "decision_bucket",
    "mutation_policy",
}

REQUIRED_METRIC_FIELDS = {
    "total_return",
    "annualized_return",
    "max_drawdown",
    "sharpe_like_score",
    "exposure_pct",
    "trade_count",
    "average_holding_period_days",
    "cost_slippage_assumptions",
}

FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.broker",
    "alpaca",
    "requests",
    "urllib",
    "httpx",
    "socket",
)


def test_candidate_definitions_are_fixed_and_predeclared() -> None:
    candidates = build_fixed_alpha_candidate_definitions()

    assert isinstance(candidates, tuple)
    assert 4 <= len(candidates) <= 8
    assert tuple(candidate.candidate_id for candidate in candidates) == EXPECTED_CANDIDATE_IDS
    with pytest.raises(FrozenInstanceError):
        candidates[0].candidate_id = "mutated"  # type: ignore[misc]

    for candidate in candidates:
        payload = candidate.to_dict()
        assert payload["fixed_parameter"] is True
        assert payload["parameter_search_performed"] is False
        assert payload["threshold_optimization_performed"] is False
        assert candidate.parameters
        assert all(
            len(values) == 1 for values in candidate.parameters_evaluated.values()
        )


def test_no_optimization_occurs_in_batch_packet(tmp_path: Path) -> None:
    spy_path, qqq_path = _write_fixture_inputs(tmp_path)

    packet = build_alpha_candidate_batch_packet(
        daily_bars_csv=spy_path,
        qqq_daily_bars_csv=qqq_path,
    )

    policy = packet["summary"]["optimization_policy"]  # type: ignore[index]
    assert policy["optimization_performed"] is False
    assert policy["parameter_search_performed"] is False
    assert policy["threshold_optimization_performed"] is False
    assert set(policy["parameter_sets_evaluated_per_candidate"].values()) == {1}
    for record in packet["candidate_by_window"]:
        assert record["parameter_search_performed"] is False
        assert record["threshold_optimization_performed"] is False
        assert all(len(values) == 1 for values in record["parameters_evaluated"].values())


def test_windows_are_deterministic_and_chronological(tmp_path: Path) -> None:
    spy_path, qqq_path = _write_fixture_inputs(tmp_path)

    first = build_alpha_candidate_batch_packet(
        daily_bars_csv=spy_path,
        qqq_daily_bars_csv=qqq_path,
    )
    second = build_alpha_candidate_batch_packet(
        daily_bars_csv=spy_path,
        qqq_daily_bars_csv=qqq_path,
    )

    first_windows = first["summary"]["windows"]  # type: ignore[index]
    second_windows = second["summary"]["windows"]  # type: ignore[index]
    assert first_windows == second_windows
    assert tuple(window["window_id"] for window in first_windows) == EXPECTED_WINDOW_IDS
    for window in first_windows:
        assert window["row_count"] > 0
        assert window["start_date"] <= window["end_date"]


def test_decisions_are_deterministic_and_exactly_one_per_candidate(
    tmp_path: Path,
) -> None:
    spy_path, qqq_path = _write_fixture_inputs(tmp_path)

    first = build_alpha_candidate_batch_packet(
        daily_bars_csv=spy_path,
        qqq_daily_bars_csv=qqq_path,
    )
    second = build_alpha_candidate_batch_packet(
        daily_bars_csv=spy_path,
        qqq_daily_bars_csv=qqq_path,
    )

    first_ranked = first["summary"]["ranked_candidates"]  # type: ignore[index]
    second_ranked = second["summary"]["ranked_candidates"]  # type: ignore[index]
    assert first_ranked == second_ranked
    assert len(first_ranked) == len(EXPECTED_CANDIDATE_IDS)
    assert {item["candidate_id"] for item in first_ranked} == set(EXPECTED_CANDIDATE_IDS)
    for item in first_ranked:
        assert item["final_decision"] in ALPHA_CANDIDATE_BATCH_SCOUT_DECISIONS
        assert isinstance(item["final_decision"], str)


def test_rejected_and_preview_candidates_cannot_mutate() -> None:
    rejected = alpha_candidate_mutation_policy("reject_candidate")
    preview = alpha_candidate_mutation_policy("promote_to_paper_preview_candidate")

    for policy in (rejected, preview):
        assert policy["broker_read_allowed"] is False
        assert policy["broker_mutation_allowed"] is False
        assert policy["paper_submit_allowed"] is False
        assert policy["paper_mutation_allowed"] is False
        assert policy["live_endpoint_allowed"] is False
    assert rejected["paper_preview_only"] is False
    assert preview["paper_preview_only"] is True
    assert preview["promotion_scope"] == "paper_preview_candidate_only"


def test_output_artifacts_contain_required_fields(tmp_path: Path) -> None:
    spy_path, qqq_path = _write_fixture_inputs(tmp_path)
    packet = build_alpha_candidate_batch_packet(
        daily_bars_csv=spy_path,
        qqq_daily_bars_csv=qqq_path,
    )

    paths = write_alpha_candidate_batch_artifacts(packet, tmp_path / "runs" / "batch")

    assert set(paths) == {
        "batch_summary_json",
        "candidate_by_window_jsonl",
        "decision_brief_md",
        "rejected_candidates_jsonl",
        "promoted_preview_candidates_jsonl",
    }
    summary = json.loads(paths["batch_summary_json"].read_text(encoding="utf-8"))
    records = _read_jsonl(paths["candidate_by_window_jsonl"])
    promoted_records = _read_jsonl(paths["promoted_preview_candidates_jsonl"])
    brief = paths["decision_brief_md"].read_text(encoding="utf-8")

    assert summary["candidate_count"] == len(EXPECTED_CANDIDATE_IDS)
    assert summary["window_count"] == len(EXPECTED_WINDOW_IDS)
    assert summary["safety"]["broker_mutation_performed"] is False
    assert summary["safety"]["network_access_attempted"] is False
    assert len(records) == len(EXPECTED_CANDIDATE_IDS) * len(EXPECTED_WINDOW_IDS)
    assert "No parameter search or threshold optimization was performed." in brief
    for record in records:
        assert REQUIRED_WINDOW_RECORD_FIELDS <= set(record)
        assert REQUIRED_METRIC_FIELDS <= set(record["metrics"])
        assert {
            "spy_buy_and_hold_comparator",
            "spy_sma_50_200_training_wheel",
            "spy_rsi_14_mean_reversion_rejected_comparator",
            "spy_trend_pullback_sma50_200_sma20_recovery_rejected_comparator",
        } <= set(record["comparator_metrics"])
        assert record["decision_bucket"] in ALPHA_CANDIDATE_BATCH_SCOUT_DECISIONS
        assert record["mutation_policy"]["paper_mutation_allowed"] is False
    if summary["promoted_preview_candidate_count"] == 0:
        assert promoted_records[0]["record_type"].endswith("_empty")
        assert promoted_records[0]["reason"]


def test_alpha_candidate_batch_scout_imports_no_broker_network_or_runtime_dependencies() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    imports = _import_references(tree)
    assert not any(
        imported == forbidden or imported.startswith(f"{forbidden}.")
        for imported in imports
        for forbidden in FORBIDDEN_IMPORT_PREFIXES
    )
    forbidden_calls = {"submit_order", "cancel_order", "replace_order", "close_position"}
    calls = {_call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assert calls.isdisjoint(forbidden_calls)


def _write_fixture_inputs(tmp_path: Path) -> tuple[Path, Path]:
    spy_prices = _fixture_prices(1500, start=Decimal("100"), drift=Decimal("0.08"))
    qqq_prices = _fixture_prices(1500, start=Decimal("95"), drift=Decimal("0.11"))
    spy_path = tmp_path / "spy_daily.csv"
    qqq_path = tmp_path / "qqq_daily.csv"
    _write_price_csv(spy_path, "SPY", spy_prices)
    _write_price_csv(qqq_path, "QQQ", qqq_prices)
    return spy_path, qqq_path


def _fixture_prices(
    count: int,
    *,
    start: Decimal,
    drift: Decimal,
) -> tuple[Decimal, ...]:
    price = start
    prices: list[Decimal] = []
    for index in range(count):
        if 420 <= index < 500:
            price -= Decimal("0.34")
        elif 980 <= index < 1060:
            price -= Decimal("0.28")
        elif index % 41 == 0:
            price -= Decimal("0.92")
        else:
            price += drift
        if price < Decimal("20"):
            price = Decimal("20")
        prices.append(price.quantize(Decimal("0.0001")))
    return tuple(prices)


def _write_price_csv(path: Path, symbol: str, prices: tuple[Decimal, ...]) -> None:
    start_date = date(2018, 1, 2)
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for index, price in enumerate(prices):
        current_date = start_date + timedelta(days=index)
        high = price + Decimal("0.50")
        low = price - Decimal("0.50")
        rows.append(
            "{symbol},{date},{open},{high},{low},{close},{adjusted},1000".format(
                symbol=symbol,
                date=current_date.isoformat(),
                open=price,
                high=high,
                low=low,
                close=price,
                adjusted=price,
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _import_references(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return imports


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""
