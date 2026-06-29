from __future__ import annotations

import ast
import json
import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.research.strategy_challenger_factory import (
    STRATEGY_CHALLENGER_FACTORY_LABELS,
    StrategyChallengerFactoryConfig,
    build_default_strategy_challenger_candidates,
    build_strategy_challenger_payload,
    classify_strategy_challenger_promotion,
    run_strategy_challenger_factory,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src" / "algotrader" / "research" / "strategy_challenger_factory.py"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_strategy_challenger_factory.ps1"

REQUIRED_ARTIFACTS = {
    "challenger_results.json",
    "challenger_results.jsonl",
    "challenger_summary.md",
    "promotion_recommendations.json",
    "strategy_review_packet.json",
    "strategy_review_packet.md",
    "validation_windows.json",
    "cost_sensitivity.json",
    "manifest.json",
}

REQUIRED_RESULT_FIELDS = {
    "candidate_id",
    "baseline_candidate_id",
    "strategy_family",
    "strategy_hypothesis",
    "symbol",
    "timeframe",
    "data_path",
    "data_sha256",
    "as_of_start",
    "as_of_end",
    "total_bars",
    "usable_bars",
    "annualized_return",
    "cagr",
    "total_return",
    "max_drawdown",
    "volatility",
    "annualized_volatility",
    "sharpe_ratio",
    "risk_adjusted_score",
    "trade_count",
    "transition_count",
    "exposure_percentage",
    "benchmark_baseline_comparison",
    "benchmark_buy_and_hold_comparison",
    "buy_and_hold_total_return_delta",
    "buy_and_hold_max_drawdown_delta",
    "buy_and_hold_sharpe_ratio_delta",
    "validation_windows_evaluated",
    "cost_assumptions_evaluated",
    "full_sample_metrics",
    "validation_window_metrics",
    "out_of_sample_metrics",
    "out_of_sample_validation",
    "cost_adjusted_metrics",
    "cost_sensitivity_summary",
    "limitations",
    "promotion_classification",
    "labels",
}

REQUIRED_REVIEW_CANDIDATE_FIELDS = {
    "candidate_id",
    "strategy_hypothesis",
    "metrics_summary",
    "oos_result",
    "cost_sensitivity_result",
    "baseline_comparison",
    "benchmark_comparison",
    "promotion_classification",
    "promotion_reasons",
    "promotion_rationale",
    "operator_takeaway",
    "limitations",
    "safety_labels",
}

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
    "pandas",
    "requests",
    "socket",
    "urllib",
    "vectorbt",
    "yfinance",
)


def test_default_candidate_set_is_broader_but_controlled() -> None:
    candidates = build_default_strategy_challenger_candidates()
    ids = {candidate.candidate_id for candidate in candidates}
    challenger_ids = {
        candidate.candidate_id
        for candidate in candidates
        if candidate.role == "challenger"
    }

    assert "spy_sma_50_200_baseline" in ids
    assert {
        "spy_sma_20_100_long_only",
        "spy_sma_10_50_long_only",
        "spy_sma_50_150_long_only",
        "spy_sma_100_200_long_only",
        "spy_tsmom_252_long_only",
        "spy_drawdown_20pct_risk_off",
    } <= challenger_ids
    assert "spy_buy_and_hold_comparator" in ids
    assert len(challenger_ids) >= 3
    assert len(candidates) <= 9


def test_factory_runs_with_fixture_data_and_emits_required_artifacts(tmp_path: Path) -> None:
    data_path = tmp_path / "spy_fixture.csv"
    _write_trend_then_drawdown_csv(data_path)
    output_root = tmp_path / "strategy_challengers" / "latest"

    payload = run_strategy_challenger_factory(
        StrategyChallengerFactoryConfig(output_root=output_root, data_path=data_path)
    )

    assert {path.name for path in output_root.iterdir()} == REQUIRED_ARTIFACTS
    results_json = json.loads((output_root / "challenger_results.json").read_text(encoding="utf-8"))
    jsonl_results = [
        json.loads(line)
        for line in (output_root / "challenger_results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert results_json["results"] == jsonl_results
    assert payload["promotion_recommendations"] == results_json["promotion_recommendations"]

    candidate_ids = {result["candidate_id"] for result in jsonl_results}
    assert "spy_sma_50_200_baseline" in candidate_ids
    challenger_ids = {
        result["candidate_id"]
        for result in jsonl_results
        if result["role"] == "challenger"
    }
    assert len(challenger_ids) >= 3
    for result in jsonl_results:
        assert REQUIRED_RESULT_FIELDS <= set(result)
        assert set(STRATEGY_CHALLENGER_FACTORY_LABELS) <= set(result["labels"])

    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_count"] == 8
    assert {artifact["name"] for artifact in manifest["artifacts"]} == REQUIRED_ARTIFACTS - {"manifest.json"}
    assert manifest["safety"]["broker_mutation_performed"] is False
    assert manifest["safety"]["live_mutation_performed"] is False

    validation_windows = json.loads(
        (output_root / "validation_windows.json").read_text(encoding="utf-8")
    )
    assert validation_windows["validation_windows"] == payload["validation_windows"]
    cost_sensitivity = json.loads(
        (output_root / "cost_sensitivity.json").read_text(encoding="utf-8")
    )
    assert cost_sensitivity["cost_assumptions"] == payload["cost_assumptions"]
    assert [item["cost_id"] for item in payload["cost_assumptions"]] == [
        "zero_cost",
        "low_cost_1bp",
        "moderate_cost_5bps",
    ]
    assert {item["candidate_id"] for item in cost_sensitivity["results"]} == candidate_ids

    review_packet = json.loads(
        (output_root / "strategy_review_packet.json").read_text(encoding="utf-8")
    )
    assert review_packet["benchmark_candidate_id"] == "spy_buy_and_hold_comparator"
    assert len(review_packet["candidates"]) == len(jsonl_results)
    for candidate in review_packet["candidates"]:
        assert REQUIRED_REVIEW_CANDIDATE_FIELDS <= set(candidate)
        assert set(STRATEGY_CHALLENGER_FACTORY_LABELS) <= set(candidate["safety_labels"])


def test_validation_windows_are_deterministic_and_chronological(tmp_path: Path) -> None:
    data_path = tmp_path / "spy_fixture.csv"
    _write_trend_then_drawdown_csv(data_path)

    first_payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out1", data_path=data_path)
    )
    second_payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out2", data_path=data_path)
    )

    assert first_payload["validation_windows"] == second_payload["validation_windows"]
    windows = first_payload["validation_windows"]
    assert [window["window_id"] for window in windows] == [
        "full_sample",
        "early_train",
        "later_test",
        "walk_forward_1",
        "walk_forward_2",
        "walk_forward_3",
    ]
    assert {window["window_id"] for window in windows} <= set(
        _result_by_id(first_payload, "spy_sma_20_100_long_only")["validation_windows_evaluated"]
    )

    early = _window_by_id(windows, "early_train")
    later = _window_by_id(windows, "later_test")
    assert early["start_index"] == 0
    assert early["end_index_exclusive"] == later["start_index"]
    assert later["end_index_exclusive"] == _window_by_id(windows, "full_sample")["end_index_exclusive"]

    walk_forward_windows = [
        _window_by_id(windows, "walk_forward_1"),
        _window_by_id(windows, "walk_forward_2"),
        _window_by_id(windows, "walk_forward_3"),
    ]
    for previous, current in zip(walk_forward_windows, walk_forward_windows[1:]):
        assert previous["end_index_exclusive"] == current["start_index"]
    assert all(window["as_of_start"] <= window["as_of_end"] for window in windows)


def test_candidate_metrics_are_produced_per_validation_window(tmp_path: Path) -> None:
    data_path = tmp_path / "spy_fixture.csv"
    _write_trend_then_drawdown_csv(data_path)

    payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out", data_path=data_path)
    )

    window_ids = {window["window_id"] for window in payload["validation_windows"]}
    for result in payload["results"]:
        if result["metrics_status"] != "valid":
            continue
        metrics_by_window = {
            metric["window_id"]: metric for metric in result["validation_window_metrics"]
        }
        assert set(metrics_by_window) == window_ids
        assert result["full_sample_metrics"]["window_id"] == "full_sample"
        assert result["out_of_sample_metrics"]["primary_window_id"] == "later_test"
        assert {metric["window_id"] for metric in result["out_of_sample_metrics"]["windows"]} == {
            "later_test",
            "walk_forward_1",
            "walk_forward_2",
            "walk_forward_3",
        }
        for metric in metrics_by_window.values():
            assert metric["metrics_status"] == "valid"
            assert "total_return" in metric
            assert "max_drawdown" in metric
            assert "sharpe_ratio" in metric
            assert "transition_count" in metric
            assert "exposure_percentage" in metric
            assert "baseline_comparison" in metric


def test_cost_sensitivity_penalizes_high_transition_strategies(tmp_path: Path) -> None:
    data_path = tmp_path / "choppy_spy.csv"
    _write_price_csv(data_path, _regime_flip_prices(count=900, regime=35))

    payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out", data_path=data_path)
    )

    baseline = _result_by_id(payload, "spy_sma_50_200_baseline")
    high_transition = _result_by_id(payload, "spy_sma_10_50_long_only")
    assert high_transition["transition_count"] > baseline["transition_count"]
    assert Decimal(
        high_transition["cost_sensitivity_summary"]["moderate_cost_return_degradation"]
    ) > Decimal(baseline["cost_sensitivity_summary"]["moderate_cost_return_degradation"])

    zero_cost = _cost_metrics_by_id(high_transition, "zero_cost")
    moderate_cost = _cost_metrics_by_id(high_transition, "moderate_cost_5bps")
    assert Decimal(moderate_cost["full_sample_metrics"]["total_return"]) < Decimal(
        zero_cost["full_sample_metrics"]["total_return"]
    )


def test_promotion_classification_rejects_insufficient_history(tmp_path: Path) -> None:
    data_path = tmp_path / "short_spy.csv"
    _write_price_csv(data_path, _linear_prices(40, start=Decimal("100"), step=Decimal("0.1")))

    payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out", data_path=data_path)
    )

    results = payload["results"]
    assert results
    assert {result["promotion_classification"] for result in results} == {"reject"}
    assert all("insufficient_history" in result["blockers"] for result in results)


def test_promotion_classification_keeps_baseline_researching(tmp_path: Path) -> None:
    data_path = tmp_path / "valid_spy.csv"
    _write_trend_then_drawdown_csv(data_path)

    payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out", data_path=data_path)
    )

    baseline = _result_by_id(payload, "spy_sma_50_200_baseline")
    assert baseline["promotion_classification"] == "keep_researching"
    assert "current_baseline_reference" in baseline["promotion_reasons"]


def test_buy_and_hold_comparator_is_not_auto_paper_candidate(tmp_path: Path) -> None:
    data_path = tmp_path / "valid_spy.csv"
    _write_trend_then_drawdown_csv(data_path)

    payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out", data_path=data_path)
    )

    comparator = _result_by_id(payload, "spy_buy_and_hold_comparator")
    assert comparator["role"] == "benchmark_comparator"
    assert comparator["promotion_classification"] == "keep_researching"
    assert "benchmark_buy_and_hold_comparator" in comparator["promotion_reasons"]
    assert comparator["benchmark_buy_and_hold_comparison"]["baseline_candidate_id"] == (
        "spy_buy_and_hold_comparator"
    )
    assert comparator["benchmark_buy_and_hold_comparison"]["same_as_baseline"] is True
    assert payload["promotion_recommendations"]["best_candidate_id"] != (
        "spy_buy_and_hold_comparator"
    )


def test_review_packet_explains_reject_and_keep_researching(tmp_path: Path) -> None:
    valid_data_path = tmp_path / "valid_spy.csv"
    _write_trend_then_drawdown_csv(valid_data_path)
    valid_output = tmp_path / "valid_out"

    run_strategy_challenger_factory(
        StrategyChallengerFactoryConfig(output_root=valid_output, data_path=valid_data_path)
    )
    valid_packet = json.loads(
        (valid_output / "strategy_review_packet.json").read_text(encoding="utf-8")
    )
    baseline = _review_candidate_by_id(valid_packet, "spy_sma_50_200_baseline")
    assert baseline["promotion_classification"] == "keep_researching"
    assert baseline["promotion_rationale"].startswith("Keep researching because")
    assert "current baseline reference" in baseline["operator_takeaway"]

    short_data_path = tmp_path / "short_spy.csv"
    _write_price_csv(
        short_data_path,
        _linear_prices(40, start=Decimal("100"), step=Decimal("0.1")),
    )
    short_output = tmp_path / "short_out"

    run_strategy_challenger_factory(
        StrategyChallengerFactoryConfig(output_root=short_output, data_path=short_data_path)
    )
    short_packet = json.loads(
        (short_output / "strategy_review_packet.json").read_text(encoding="utf-8")
    )
    assert any(
        candidate["promotion_classification"] == "reject"
        and candidate["promotion_rationale"].startswith("Rejected because")
        and "insufficient history" in candidate["operator_takeaway"]
        for candidate in short_packet["candidates"]
    )


def test_controlled_fixture_produces_preview_or_paper_candidate(tmp_path: Path) -> None:
    data_path = tmp_path / "preview_candidate_spy.csv"
    _write_trend_then_drawdown_csv(data_path)

    payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out", data_path=data_path)
    )

    challenger_results = [
        result
        for result in payload["results"]
        if result["candidate_id"] not in {"spy_sma_50_200_baseline", "spy_sma_50_200_cash_risk_off_comparator"}
    ]
    assert any(
        result["promotion_classification"] in {"preview_only", "paper_candidate"}
        for result in challenger_results
    )


def test_promotion_recommendations_exclude_baseline_comparators_from_best_candidate(
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "choppy_spy.csv"
    _write_price_csv(data_path, _regime_flip_prices(count=900, regime=35))

    payload = build_strategy_challenger_payload(
        StrategyChallengerFactoryConfig(output_root=tmp_path / "out", data_path=data_path)
    )

    recommendations = payload["promotion_recommendations"]
    assert recommendations["best_candidate_id"] not in {
        "spy_sma_50_200_baseline",
        "spy_sma_50_200_cash_risk_off_comparator",
        "spy_buy_and_hold_comparator",
    }


def test_candidate_cannot_be_paper_candidate_when_out_of_sample_fails() -> None:
    result = _classification_candidate_result(
        out_of_sample_validation={
            "validation_passed": False,
            "validation_failed": True,
            "passed_window_count": 0,
        }
    )

    classification, reasons = classify_strategy_challenger_promotion(
        result,
        _classification_baseline_result(),
    )

    assert classification == "keep_researching"
    assert "full_sample_edge_failed_out_of_sample" in reasons


def test_candidate_cannot_be_paper_candidate_when_cost_sensitivity_breaks_edge() -> None:
    result = _classification_candidate_result(
        cost_sensitivity_summary={
            "edge_broken_by_moderate_cost": True,
            "returns_highly_cost_sensitive": True,
        }
    )

    classification, reasons = classify_strategy_challenger_promotion(
        result,
        _classification_baseline_result(),
    )

    assert classification == "keep_researching"
    assert "cost_sensitivity_breaks_edge" in reasons


def test_reject_classification_for_severe_return_degradation_despite_drawdown_improvement() -> None:
    result = _classification_candidate_result(
        total_return="-0.02",
        baseline_total_return_delta="-0.08",
        baseline_max_drawdown_delta="-0.03",
        baseline_sharpe_ratio_delta="-0.20",
    )

    classification, reasons = classify_strategy_challenger_promotion(
        result,
        _classification_baseline_result(),
    )

    assert classification == "reject"
    assert "drawdown_improvement_with_severe_return_degradation" in reasons


def test_malformed_data_is_rejected_and_still_writes_artifacts(tmp_path: Path) -> None:
    data_path = tmp_path / "malformed.csv"
    data_path.write_text("symbol,date,close\nSPY,2026-01-02,100\n", encoding="utf-8")
    output_root = tmp_path / "out"

    run_strategy_challenger_factory(
        StrategyChallengerFactoryConfig(output_root=output_root, data_path=data_path)
    )

    results = [
        json.loads(line)
        for line in (output_root / "challenger_results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert results
    assert {result["promotion_classification"] for result in results} == {"reject"}
    assert all(result["data_quality_status"] == "malformed_or_unreadable_local_daily_bars" for result in results)
    assert all(set(STRATEGY_CHALLENGER_FACTORY_LABELS) <= set(result["labels"]) for result in results)


def test_strategy_challenger_module_imports_no_broker_network_llm_or_runtime_dependencies() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    violations = [
        imported
        for imported in imports
        if any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in FORBIDDEN_IMPORT_PREFIXES)
    ]
    assert violations == []


def test_runtime_artifacts_under_runs_remain_untracked_by_policy() -> None:
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_run_strategy_challenger_factory_script_contract_and_invocation(tmp_path: Path) -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    for fragment in (
        "Runs the deterministic offline strategy challenger factory",
        "does not read",
        "mutate broker state",
        "contact",
        "Credential values are never printed",
        "preflight_APP_PROFILE_is_paper",
        "preflight_credential_variables_loaded",
        "algotrader.research.strategy_challenger_factory",
    ):
        assert fragment in script

    output_root = tmp_path / "factory out"
    bars_csv = tmp_path / "bars with spaces.csv"
    bars_csv.write_text("symbol,date,open,high,low,close,adjusted_close,volume\n", encoding="utf-8")
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-OutputRoot",
            str(output_root),
            "-BarsCsv",
            str(bars_csv),
            "-AsOfDate",
            "2026-01-02",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "preflight_APP_PROFILE_is_paper=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.research.strategy_challenger_factory" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--data-path" in args
    assert str(bars_csv) in args
    assert "--as-of-date 2026-01-02" in args


def test_run_strategy_challenger_factory_script_blocks_loaded_credentials(tmp_path: Path) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["APP_PROFILE"] = "paper"
    env["APCA_API_KEY_ID"] = "set-but-not-printed"

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-OutputRoot",
            str(tmp_path / "out"),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "preflight_APP_PROFILE_is_paper=true" in result.stdout
    assert "preflight_credential_variables_loaded=true" in result.stdout
    assert "set-but-not-printed" not in result.stdout
    assert not capture_path.exists()


def _result_by_id(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    for result in payload["results"]:
        if result["candidate_id"] == candidate_id:
            return result
    raise AssertionError(candidate_id)


def _review_candidate_by_id(packet: dict[str, object], candidate_id: str) -> dict[str, object]:
    for candidate in packet["candidates"]:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise AssertionError(candidate_id)


def _window_by_id(windows: list[dict[str, object]], window_id: str) -> dict[str, object]:
    for window in windows:
        if window["window_id"] == window_id:
            return window
    raise AssertionError(window_id)


def _cost_metrics_by_id(result: dict[str, object], cost_id: str) -> dict[str, object]:
    for cost_metrics in result["cost_adjusted_metrics"]:
        if cost_metrics["cost_id"] == cost_id:
            return cost_metrics
    raise AssertionError(cost_id)


def _classification_baseline_result() -> dict[str, object]:
    return {"metrics_status": "valid"}


def _classification_candidate_result(
    *,
    total_return: str = "0.12",
    baseline_total_return_delta: str = "0.08",
    baseline_max_drawdown_delta: str = "0",
    baseline_sharpe_ratio_delta: str = "0.20",
    out_of_sample_validation: dict[str, object] | None = None,
    cost_sensitivity_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "candidate_id": "controlled_candidate",
        "data_quality_status": "valid_local_daily_bars",
        "metrics_status": "valid",
        "usable_bars": 720,
        "required_history_bars": 200,
        "evaluated_return_count": 520,
        "total_return": total_return,
        "annualized_return": "0.08",
        "max_drawdown": "0.12",
        "annualized_volatility": "0.10",
        "sharpe_ratio": "0.80",
        "exposure_percentage": "55",
        "baseline_total_return_delta": baseline_total_return_delta,
        "baseline_max_drawdown_delta": baseline_max_drawdown_delta,
        "baseline_sharpe_ratio_delta": baseline_sharpe_ratio_delta,
        "out_of_sample_validation": out_of_sample_validation
        or {
            "validation_passed": True,
            "validation_failed": False,
            "passed_window_count": 4,
        },
        "cost_sensitivity_summary": cost_sensitivity_summary
        or {
            "edge_broken_by_moderate_cost": False,
            "returns_highly_cost_sensitive": False,
        },
    }


def _write_trend_then_drawdown_csv(path: Path) -> None:
    prices: list[Decimal] = []
    price = Decimal("100")
    for _ in range(220):
        prices.append(price)
        price += Decimal("0.15")
    for _ in range(55):
        prices.append(price)
        price -= Decimal("0.95")
    for _ in range(180):
        prices.append(price)
        price += Decimal("0.30")
    _write_price_csv(path, tuple(prices))


def _linear_prices(count: int, *, start: Decimal, step: Decimal) -> tuple[Decimal, ...]:
    return tuple(start + step * Decimal(index) for index in range(count))


def _regime_flip_prices(count: int, regime: int) -> tuple[Decimal, ...]:
    prices: list[Decimal] = []
    price = Decimal("100")
    direction = Decimal("0.6")
    for index in range(count):
        if index > 0 and index % regime == 0:
            direction = -direction
        price += direction
        if price < Decimal("20"):
            price = Decimal("20")
            direction = abs(direction)
        prices.append(price)
    return tuple(prices)


def _write_price_csv(path: Path, prices: tuple[Decimal, ...]) -> None:
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    start = date(2020, 1, 2)
    for index, price in enumerate(prices):
        on_date = start + timedelta(days=index)
        rows.append(
            "SPY,{date},{price},{price},{price},{price},{price},1000".format(
                date=on_date.isoformat(),
                price=price,
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo strategy_challenger_factory_status=completed\r\n"
        "echo broker_mutation_performed=false\r\n"
        "echo live_mutation_performed=false\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_strategy_challenger_factory.ps1")
    return powershell
