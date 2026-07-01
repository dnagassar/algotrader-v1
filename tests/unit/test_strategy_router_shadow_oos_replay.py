from __future__ import annotations

import ast
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.errors import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "run_strategy_router_shadow_oos_replay.py"
)


def test_multiple_oos_replay_windows_are_deterministic(tmp_path: Path) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_uptrend.csv",
        [100 + index for index in range(1300)],
    )

    first = module.build_strategy_router_shadow_oos_replay(
        daily_bars_csv=csv_path,
        run_id="unit_oos_replay",
    )
    second = module.build_strategy_router_shadow_oos_replay(
        daily_bars_csv=csv_path,
        run_id="unit_oos_replay",
    )

    assert first == second
    windows = {
        window["window_id"]: window
        for window in first["replay_summary_by_window"]
    }
    assert {
        "recent_260",
        "trailing_3_years",
        "trailing_5_years",
        "full_available",
        "chronological_earlier_half",
        "chronological_later_half",
    } <= set(windows)
    assert windows["recent_260"]["row_count"] == 260
    assert windows["trailing_3_years"]["row_count"] == 756
    assert windows["trailing_5_years"]["row_count"] == 1260
    assert windows["full_available"]["row_count"] == 1300
    assert first["summary"]["window_count"] == 6


def test_oos_packet_writes_required_artifacts(tmp_path: Path) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_artifacts.csv",
        [100 + index for index in range(1300)],
    )

    packet = module.build_strategy_router_shadow_oos_replay(
        daily_bars_csv=csv_path,
        run_id="unit_oos_artifacts",
    )
    paths = module.write_strategy_router_shadow_oos_replay_artifacts(
        packet,
        tmp_path / "runs" / "strategy_router_shadow_replay" / "oos" / "latest",
    )

    assert paths["summary_json"].name == "summary.json"
    assert paths["replay_summary_by_window_jsonl"].name == (
        "replay_summary_by_window.jsonl"
    )
    assert paths["conflict_summary_by_window_jsonl"].name == (
        "conflict_summary_by_window.jsonl"
    )
    assert paths["brief_md"].name == "brief.md"
    assert json.loads(paths["summary_json"].read_text(encoding="utf-8"))[
        "rsi_promotion_status"
    ] == "shadow_only"
    assert len(_read_jsonl(paths["replay_summary_by_window_jsonl"])) == 6
    assert len(_read_jsonl(paths["conflict_summary_by_window_jsonl"])) == 6
    brief = paths["brief_md"].read_text(encoding="utf-8")
    assert "RSI remains shadow_only and mutation-ineligible" in brief
    assert "does not optimize thresholds" in brief


def test_rsi_remains_shadow_only_and_mutation_ineligible_by_window(
    tmp_path: Path,
) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_descending.csv",
        [1500 - index for index in range(1300)],
    )

    packet = module.build_strategy_router_shadow_oos_replay(
        daily_bars_csv=csv_path,
        run_id="unit_shadow_ineligible",
    )

    assert packet["summary"]["rsi_promotion_status"] == "shadow_only"
    assert packet["summary"]["rsi_mutation_eligibility"] is False
    assert packet["summary"]["rsi_mutation_eligible_count"] == 0
    for window in packet["replay_summary_by_window"]:
        assert window["rsi_promotion_status"] == "shadow_only"
        assert window["rsi_mutation_eligibility"] is False
        assert window["rsi_mutation_eligible_count"] == 0
        assert window["rsi_oversold_count"] > 0
        assert window["shadow_blocked_count"] > 0


def test_summary_by_window_contains_required_fields(tmp_path: Path) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_required_fields.csv",
        [100 + index for index in range(1300)],
    )

    packet = module.build_strategy_router_shadow_oos_replay(
        daily_bars_csv=csv_path,
    )

    required_fields = {
        "start_date",
        "end_date",
        "row_count",
        "sma_counts",
        "sma_risk_on_count",
        "sma_risk_off_count",
        "rsi_counts",
        "rsi_oversold_count",
        "rsi_overbought_count",
        "rsi_neutral_count",
        "rsi_insufficient_count",
        "conflict_count",
        "shadow_blocked_count",
        "candidate_disagreement_count",
        "final_mutation_eligible_count",
        "rsi_mutation_eligible_count",
        "representative_conflict_dates",
        "threshold_review",
        "recommendation_bucket",
        "broker_read_performed",
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_endpoint_used",
        "network_fetch_performed",
    }
    for window in packet["replay_summary_by_window"]:
        assert required_fields <= set(window)
        assert window["recommendation_bucket"] in {
            "keep_shadow",
            "needs_oos_backtest",
            "needs_regime_review",
            "needs_threshold_review",
            "reject_candidate",
        }
        assert window["broker_read_performed"] is False
        assert window["broker_mutation_performed"] is False
        assert window["paper_submit_performed"] is False
        assert window["live_endpoint_used"] is False
        assert window["network_fetch_performed"] is False


def test_threshold_review_is_fixed_frequency_only_without_optimization(
    tmp_path: Path,
) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_fixed_threshold.csv",
        _oscillating_prices(1300),
    )

    packet = module.build_strategy_router_shadow_oos_replay(
        daily_bars_csv=csv_path,
    )

    policy = packet["summary"]["threshold_policy"]
    assert policy["review_type"] == "fixed_threshold_frequency_only"
    assert policy["rsi_lookback_window"] == 14
    assert policy["oversold_threshold"] == "30"
    assert policy["overbought_threshold"] == "70"
    assert policy["thresholds_evaluated"] == {
        "oversold": ["30"],
        "overbought": ["70"],
    }
    assert policy["optimization_performed"] is False
    assert policy["parameter_search_performed"] is False
    assert policy["rsi_period_tuning_performed"] is False
    assert policy["threshold_change_performed"] is False

    for window in packet["replay_summary_by_window"]:
        review = window["threshold_review"]
        assert review["thresholds_evaluated"] == {
            "oversold": ["30"],
            "overbought": ["70"],
        }
        assert review["optimization_performed"] is False
        assert review["parameter_search_performed"] is False
        assert review["rsi_period_tuning_performed"] is False


def test_missing_or_short_data_fails_cleanly(tmp_path: Path) -> None:
    module = _load_module()
    short_csv = _write_spy_daily_csv(
        tmp_path / "spy_short.csv",
        [100 + index for index in range(259)],
    )

    with pytest.raises(ValidationError, match="at least 260 usable SPY bars"):
        module.build_strategy_router_shadow_oos_replay(daily_bars_csv=short_csv)

    with pytest.raises(ValidationError, match="existing local CSV file"):
        module.build_strategy_router_shadow_oos_replay(
            daily_bars_csv=tmp_path / "missing.csv",
        )


def test_oos_script_introduces_no_broker_network_or_order_imports() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    forbidden_prefixes = (
        "algotrader.execution",
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )
    forbidden_calls = {
        "cancel_order",
        "close_position",
        "connect",
        "create_order",
        "delete_order",
        "liquidate",
        "request",
        "socket.socket",
        "submit_order",
        "urlopen",
    }
    import_modules = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]
    import_modules.extend(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in import_modules
        for prefix in forbidden_prefixes
    )
    assert call_names.isdisjoint(forbidden_calls)
    assert "submit_order" not in text


def _load_module() -> ModuleType:
    module_name = "run_strategy_router_shadow_oos_replay"
    spec = importlib.util.spec_from_file_location(
        module_name,
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_spy_daily_csv(path: Path, adjusted_prices: list[int]) -> Path:
    start = date(2020, 1, 1)
    lines = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for index, adjusted_price in enumerate(adjusted_prices):
        day = start + timedelta(days=index)
        lines.append(
            "SPY,"
            f"{day.isoformat()},"
            "1000,1000,1000,1000,"
            f"{adjusted_price},1000"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _oscillating_prices(count: int) -> list[int]:
    price = 500
    prices: list[int] = []
    for index in range(count):
        if index % 80 < 40:
            price += 2
        else:
            price -= 2
        prices.append(price)
    return prices


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
