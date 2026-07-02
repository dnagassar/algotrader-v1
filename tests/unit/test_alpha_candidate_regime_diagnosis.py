from __future__ import annotations

import ast
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.research.alpha_candidate_regime_diagnosis import (
    REGIME_DIAGNOSIS_DECISIONS,
    TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS,
    build_top_two_regime_diagnosis_packet,
    write_top_two_regime_diagnosis_artifacts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "alpha_candidate_regime_diagnosis.py"
)

EXPECTED_TOP_TWO = (
    "spy_vol_scaled_trend_20d_fixed",
    "spy_drawdown_recovery_252d_20_10_fixed",
)

FORBIDDEN_NON_TOP_TWO = {
    "spy_breakout_252d_trailing_63d_fixed",
    "spy_ma200_slope_20d_filter_fixed",
    "spy_rsi2_mean_reversion_trend_filter_fixed",
    "spy_vs_qqq_relative_strength_126d_fixed",
}

EXPECTED_WINDOW_IDS = (
    "full_available_reference",
    "chronological_earlier_half",
    "chronological_later_half",
    "trailing_5y_earlier_half",
    "trailing_5y_later_half",
    "recent_3y_holdout",
)

EXPECTED_REGIME_IDS = {
    "spy_vol_scaled_trend_20d_fixed": {
        "all_rows",
        "sma50_gt_sma200",
        "sma50_lte_sma200",
        "sma50_200_unavailable",
        "vol20_high_gt_25pct",
        "vol20_normal_lte_25pct",
        "vol20_unavailable",
    },
    "spy_drawdown_recovery_252d_20_10_fixed": {
        "all_rows",
        "sma50_gt_sma200",
        "sma50_lte_sma200",
        "sma50_200_unavailable",
        "drawdown_recovered_ge_minus_10pct",
        "drawdown_between_minus_20_and_minus_10pct",
        "drawdown_deep_le_minus_20pct",
        "drawdown_unavailable",
    },
}

REQUIRED_RECORD_FIELDS = {
    "candidate_id",
    "fixed_parameters",
    "parameters_evaluated",
    "parameter_search_performed",
    "threshold_optimization_performed",
    "window_id",
    "regime_type",
    "regime_id",
    "metrics",
    "comparator_metrics",
    "delta_vs_buy_and_hold",
    "delta_vs_sma50_200",
    "regime_where_it_helped",
    "regime_where_it_harmed",
    "final_decision",
    "mutation_policy",
}

REQUIRED_METRIC_FIELDS = {
    "bar_count",
    "total_return",
    "max_drawdown",
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


def test_only_the_requested_top_two_candidates_are_diagnosed(tmp_path: Path) -> None:
    spy_path = _write_fixture_input(tmp_path)

    packet = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )

    summary = packet["summary"]
    records = packet["candidate_regime_by_window"]
    assert tuple(summary["analyzed_candidate_ids"]) == EXPECTED_TOP_TWO
    assert tuple(summary["analyzed_candidate_ids"]) == TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS
    assert summary["candidate_count"] == 2
    assert {item["candidate_id"] for item in summary["candidate_decisions"]} == set(
        EXPECTED_TOP_TWO
    )
    assert {record["candidate_id"] for record in records} == set(EXPECTED_TOP_TWO)
    assert {record["candidate_id"] for record in records}.isdisjoint(
        FORBIDDEN_NON_TOP_TWO
    )


def test_regime_bucket_definitions_are_deterministic(tmp_path: Path) -> None:
    spy_path = _write_fixture_input(tmp_path)

    first = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )
    second = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )

    assert first["summary"]["regime_definitions"] == second["summary"]["regime_definitions"]
    assert first["summary"]["windows"] == second["summary"]["windows"]
    assert tuple(window["window_id"] for window in first["summary"]["windows"]) == (
        EXPECTED_WINDOW_IDS
    )
    for candidate_id, expected_regime_ids in EXPECTED_REGIME_IDS.items():
        definitions = first["summary"]["regime_definitions"][candidate_id]
        assert {item["regime_id"] for item in definitions} == expected_regime_ids

    first_keys = _record_keys(first["candidate_regime_by_window"])
    second_keys = _record_keys(second["candidate_regime_by_window"])
    assert first_keys == second_keys


def test_no_parameter_optimization_occurs(tmp_path: Path) -> None:
    spy_path = _write_fixture_input(tmp_path)

    packet = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )

    policy = packet["summary"]["optimization_policy"]
    assert policy["optimization_performed"] is False
    assert policy["parameter_search_performed"] is False
    assert policy["threshold_optimization_performed"] is False
    assert set(policy["parameter_sets_evaluated_per_candidate"].values()) == {1}
    for record in packet["candidate_regime_by_window"]:
        assert record["parameter_search_performed"] is False
        assert record["threshold_optimization_performed"] is False
        assert all(len(values) == 1 for values in record["parameters_evaluated"].values())


def test_final_decisions_are_deterministic_and_exactly_one_per_candidate(
    tmp_path: Path,
) -> None:
    spy_path = _write_fixture_input(tmp_path)

    first = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )
    second = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )

    first_decisions = first["summary"]["candidate_decisions"]
    second_decisions = second["summary"]["candidate_decisions"]
    assert first_decisions == second_decisions
    assert len(first_decisions) == 2
    assert {item["candidate_id"] for item in first_decisions} == set(EXPECTED_TOP_TWO)
    for item in first_decisions:
        assert item["final_decision"] in REGIME_DIAGNOSIS_DECISIONS


def test_no_candidate_is_promoted_to_paper_mutation(tmp_path: Path) -> None:
    spy_path = _write_fixture_input(tmp_path)

    packet = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )

    for item in packet["summary"]["candidate_decisions"]:
        policy = item["mutation_policy"]
        assert policy["broker_read_allowed"] is False
        assert policy["broker_mutation_allowed"] is False
        assert policy["paper_submit_allowed"] is False
        assert policy["paper_mutation_allowed"] is False
        assert policy["live_endpoint_allowed"] is False
    for record in packet["candidate_regime_by_window"]:
        assert record["mutation_policy"]["paper_mutation_allowed"] is False


def test_regime_diagnosis_imports_no_broker_network_or_runtime_dependencies() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    imports = _import_references(tree)
    assert not any(
        imported == forbidden or imported.startswith(f"{forbidden}.")
        for imported in imports
        for forbidden in FORBIDDEN_IMPORT_PREFIXES
    )
    forbidden_calls = {
        "cancel_order",
        "close_position",
        "connect",
        "create_order",
        "liquidate",
        "replace_order",
        "request",
        "submit_order",
        "urlopen",
    }
    calls = {_call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assert calls.isdisjoint(forbidden_calls)


def test_output_artifacts_contain_required_fields(tmp_path: Path) -> None:
    spy_path = _write_fixture_input(tmp_path)
    packet = build_top_two_regime_diagnosis_packet(
        daily_bars_csv=spy_path,
        prior_batch_summary_json=None,
    )

    paths = write_top_two_regime_diagnosis_artifacts(
        packet,
        tmp_path / "runs" / "regime",
    )

    assert set(paths) == {
        "regime_diagnosis_summary_json",
        "candidate_regime_by_window_jsonl",
        "decision_brief_md",
    }
    assert paths["regime_diagnosis_summary_json"].name == "regime_diagnosis_summary.json"
    assert paths["candidate_regime_by_window_jsonl"].name == (
        "candidate_regime_by_window.jsonl"
    )
    assert paths["decision_brief_md"].name == "decision_brief.md"

    summary = json.loads(paths["regime_diagnosis_summary_json"].read_text(encoding="utf-8"))
    records = _read_jsonl(paths["candidate_regime_by_window_jsonl"])
    brief = paths["decision_brief_md"].read_text(encoding="utf-8")

    assert summary["candidate_count"] == 2
    assert summary["safety"]["broker_read_performed"] is False
    assert summary["safety"]["broker_mutation_performed"] is False
    assert summary["safety"]["network_access_attempted"] is False
    assert "No parameter search or threshold optimization was performed." in brief
    assert len(records) == sum(
        len(EXPECTED_REGIME_IDS[candidate_id]) * len(EXPECTED_WINDOW_IDS)
        for candidate_id in EXPECTED_TOP_TWO
    )
    for record in records:
        assert REQUIRED_RECORD_FIELDS <= set(record)
        assert REQUIRED_METRIC_FIELDS <= set(record["metrics"])
        assert {
            "spy_buy_and_hold_comparator",
            "spy_sma_50_200_training_wheel",
        } == set(record["comparator_metrics"])
        assert record["final_decision"] in REGIME_DIAGNOSIS_DECISIONS
        assert record["mutation_policy"]["paper_mutation_allowed"] is False


def _write_fixture_input(tmp_path: Path) -> Path:
    path = tmp_path / "spy_daily.csv"
    prices = _fixture_prices(1500)
    _write_price_csv(path, prices)
    return path


def _fixture_prices(count: int) -> tuple[Decimal, ...]:
    price = Decimal("100")
    prices: list[Decimal] = []
    for index in range(count):
        if 280 <= index < 360:
            price *= Decimal("0.991")
        elif 360 <= index < 620:
            price *= Decimal("1.0035")
        elif 830 <= index < 900:
            price *= Decimal("0.986")
        elif 900 <= index < 1120:
            price *= Decimal("1.0028")
        elif 1210 <= index < 1260:
            price *= Decimal("1.020") if index % 2 == 0 else Decimal("0.982")
        elif index % 43 == 0:
            price *= Decimal("0.992")
        else:
            price *= Decimal("1.0007")
        if price < Decimal("20"):
            price = Decimal("20")
        prices.append(price.quantize(Decimal("0.0001")))
    return tuple(prices)


def _write_price_csv(path: Path, prices: tuple[Decimal, ...]) -> None:
    start_date = date(2018, 1, 2)
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for index, price in enumerate(prices):
        current_date = start_date + timedelta(days=index)
        high = price + Decimal("0.50")
        low = price - Decimal("0.50")
        rows.append(
            "{symbol},{date},{open},{high},{low},{close},{adjusted},1000".format(
                symbol="SPY",
                date=current_date.isoformat(),
                open=price,
                high=high,
                low=low,
                close=price,
                adjusted=price,
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _record_keys(records: object) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (
                str(record["candidate_id"]),
                str(record["window_id"]),
                str(record["regime_id"]),
            )
            for record in records
        )
    )


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
