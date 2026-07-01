from __future__ import annotations

import ast
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.errors import ValidationError
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "research" / "run_strategy_router_shadow_replay.py"


def test_replay_uses_local_adjusted_data_and_writes_required_artifacts(
    tmp_path: Path,
) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_adjusted.csv",
        [100 + index for index in range(220)],
        raw_close=999,
    )

    replay = module.build_strategy_router_shadow_replay(
        daily_bars_csv=csv_path,
        replay_row_count=3,
        run_id="unit_shadow_replay",
    )
    paths = module.write_strategy_router_shadow_replay_artifacts(
        replay,
        tmp_path / "runs" / "strategy_router_shadow_replay" / "latest",
    )

    summary = replay["summary"]
    records = replay["records"]
    assert summary["row_count"] == 3
    assert summary["source_data"]["path"] == str(csv_path)
    assert summary["source_data"]["basis"] == "accepted_adjusted_close"
    assert records[-1]["sma_strategy"]["latest_close"] == "319"
    assert records[-1]["rsi_strategy"]["latest_close"] == "319"
    assert records[-1]["sma_strategy"]["latest_close"] != "999"

    replay_jsonl = paths["replay_jsonl"]
    summary_json = paths["summary_json"]
    brief_md = paths["brief_md"]
    assert replay_jsonl.name == "replay.jsonl"
    assert summary_json.name == "summary.json"
    assert brief_md.name == "brief.md"
    assert len(_read_jsonl(replay_jsonl)) == 3
    assert json.loads(summary_json.read_text(encoding="utf-8"))["row_count"] == 3
    brief = brief_md.read_text(encoding="utf-8")
    assert "profit_claim: none" in brief
    assert "RSI remains shadow_only" in brief


def test_shadow_only_rsi_cannot_produce_mutation_when_sma_has_no_action(
    tmp_path: Path,
) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_descending.csv",
        [120 - index for index in range(20)],
    )

    replay = module.build_strategy_router_shadow_replay(
        daily_bars_csv=csv_path,
        replay_row_count=1,
    )

    summary = replay["summary"]
    record = replay["records"][0]
    assert summary["sma_counts"] == {"risk_on": 0, "risk_off": 0, "no_action": 1}
    assert summary["rsi_counts"] == {
        "oversold": 1,
        "overbought": 0,
        "neutral": 0,
        "insufficient": 0,
    }
    assert summary["paper_mutation_eligible_count"] == 0
    assert summary["shadow_blocked_count"] == 1
    assert record["rsi_strategy"]["promotion_status"] == "shadow_only"
    assert record["rsi_shadow_blocked_from_mutation"] is True
    assert record["final_mutation_eligibility"] is False
    assert record["router_decision"]["reason"] == "all_candidates_blocked"
    assert record["router_decision"]["blocked_signal_ids"] == [
        SMA_TRAINING_WHEEL_STRATEGY_ID,
        SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
    ]


def test_router_conflict_and_disagreement_handling_is_deterministic(
    tmp_path: Path,
) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_uptrend.csv",
        [100 + index for index in range(220)],
    )

    first = module.build_strategy_router_shadow_replay(
        daily_bars_csv=csv_path,
        replay_row_count=1,
    )
    second = module.build_strategy_router_shadow_replay(
        daily_bars_csv=csv_path,
        replay_row_count=1,
    )

    assert first == second
    record = first["records"][0]
    assert record["sma_strategy"]["intended_action"] == "buy"
    assert record["rsi_strategy"]["intended_action"] == "sell_close"
    assert record["candidate_disagreement"] is True
    assert record["candidate_conflict"] is True
    assert record["router_decision"]["selected_signal_id"] == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert record["router_decision"]["blocked_signal_ids"] == [
        SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID
    ]
    assert record["final_mutation_eligibility"] is True


def test_output_summary_has_required_fields(tmp_path: Path) -> None:
    module = _load_module()
    csv_path = _write_spy_daily_csv(
        tmp_path / "spy_summary.csv",
        [100 + index for index in range(220)],
    )

    summary = module.build_strategy_router_shadow_replay(
        daily_bars_csv=csv_path,
        replay_row_count=2,
    )["summary"]

    required_fields = {
        "replay_start_date",
        "replay_end_date",
        "row_count",
        "sma_counts",
        "sma_risk_on_count",
        "sma_risk_off_count",
        "sma_no_action_count",
        "rsi_counts",
        "rsi_oversold_count",
        "rsi_overbought_count",
        "rsi_neutral_count",
        "rsi_insufficient_count",
        "candidate_disagreement_count",
        "conflict_count",
        "paper_mutation_eligible_count",
        "shadow_blocked_count",
        "labels",
    }
    assert required_fields <= set(summary)
    assert "profit_claim=none" in summary["labels"]
    assert summary["profit_claim"] == "none"
    assert summary["broker_read_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert summary["paper_submit_performed"] is False
    assert summary["live_endpoint_used"] is False
    assert summary["network_fetch_performed"] is False


def test_replay_rejects_remote_daily_bars_path() -> None:
    module = _load_module()

    with pytest.raises(ValidationError, match="local CSV path"):
        module.build_strategy_router_shadow_replay(
            daily_bars_csv="https://example.test/spy.csv",
            replay_row_count=1,
        )


def test_script_introduces_no_broker_network_or_order_imports() -> None:
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
        "connect",
        "create_order",
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
    spec = importlib.util.spec_from_file_location(
        "run_strategy_router_shadow_replay",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_spy_daily_csv(
    path: Path,
    adjusted_prices: list[int],
    *,
    raw_close: int = 1000,
) -> Path:
    start = date(2025, 1, 1)
    lines = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for index, adjusted_price in enumerate(adjusted_prices):
        day = start + timedelta(days=index)
        lines.append(
            "SPY,"
            f"{day.isoformat()},"
            f"{raw_close},{raw_close},{raw_close},{raw_close},"
            f"{adjusted_price},1000"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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
