from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_backtest import (
    ETF_SMA_BACKTEST_LABELS,
    ETF_SMA_EXECUTION_LAG_CONTRACT,
    EtfSmaBacktestBar,
    EtfSmaBacktestConfig,
    build_etf_sma_backtest,
    build_etf_sma_backtest_from_csv,
    render_etf_sma_backtest_json,
    write_etf_sma_backtest_artifact,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_backtest.py")
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "requests",
    "socket",
    "urllib",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "download",
    "liquidate",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_fewer_than_200_bars_produces_insufficient_history_and_no_trades() -> None:
    payload = build_etf_sma_backtest(_bars(199 * ("100",)), _config())

    assert payload["bar_count"] == 199
    assert payload["trades"] == []
    assert {row["posture"] for row in payload["posture_history"]} == {
        "insufficient_history"
    }
    assert payload["stats"]["insufficient_history_days"] == 199
    assert payload["stats"]["final_position_state"] == "flat"


def test_sma50_above_sma200_produces_risk_on_after_sufficient_history() -> None:
    payload = build_etf_sma_backtest(_bars(150 * ("100",) + 50 * ("200",)), _config())

    postures = payload["posture_history"]
    assert postures[198]["posture"] == "insufficient_history"
    assert postures[199]["posture"] == "risk_on"
    assert postures[199]["sma_fast"] == "200"
    assert postures[199]["sma_slow"] == "125"


def test_sma50_not_above_sma200_produces_risk_off() -> None:
    payload = build_etf_sma_backtest(_bars(200 * ("100",)), _config())

    assert payload["posture_history"][-1]["posture"] == "risk_off"
    assert payload["posture_history"][-1]["sma_fast"] == "100"
    assert payload["posture_history"][-1]["sma_slow"] == "100"
    assert payload["trades"] == []


def test_backtest_starts_flat_and_enters_after_no_lookahead_lag() -> None:
    payload = build_etf_sma_backtest(
        _bars(150 * ("100",) + 50 * ("200",) + ("220",)),
        _config(),
    )

    assert payload["execution_lag_contract"] == ETF_SMA_EXECUTION_LAG_CONTRACT
    assert payload["equity_curve"][199]["position_state"] == "flat"
    assert payload["equity_curve"][199]["position_quantity"] == "0"
    assert payload["trades"] == [
        {
            "as_of": "2026-07-20",
            "date": "2026-07-20",
            "action": "buy",
            "reason": "insufficient_history_to_risk_on",
            "target_as_of": "2026-07-19",
            "modeled_fill_price": "220",
            "quantity": "4.545454545454545454545454545",
            "notional": "1000",
            "cash_after": "0",
            "portfolio_value_after": "1000",
        }
    ]
    assert payload["equity_curve"][200]["position_state"] == "long"


def test_risk_on_to_risk_off_transition_creates_deterministic_sell_trade() -> None:
    payload = build_etf_sma_backtest(
        _bars(("10", "10", "20", "20", "5", "4")),
        _config(fast_window=2, slow_window=3),
    )

    assert [trade["action"] for trade in payload["trades"]] == ["buy", "sell"]
    sell = payload["trades"][1]
    assert sell["as_of"] == "2026-01-06"
    assert sell["reason"] == "risk_on_to_risk_off"
    assert sell["target_as_of"] == "2026-01-05"
    assert sell["modeled_fill_price"] == "4"
    assert sell["cash_after"] == "200"
    assert payload["stats"]["sell_count"] == 1
    assert payload["stats"]["final_position_state"] == "flat"


def test_artifact_includes_no_submit_or_live_authority_flags() -> None:
    payload = build_etf_sma_backtest(_bars(200 * ("100",)), _config())

    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["live_authorized"] is False
    assert payload["profit_claim"] == "none"
    assert set(ETF_SMA_BACKTEST_LABELS).issubset(set(payload["labels"]))


def test_research_module_imports_no_execution_broker_network_llm_or_runtime_deps() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_missing_csv_is_blocked_deterministically_without_fetching(tmp_path) -> None:
    missing_path = tmp_path / "missing.csv"

    payload = build_etf_sma_backtest_from_csv(
        _config(bars_source=str(missing_path))
    )

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["block_reason"] == "bars_csv_missing"
    assert payload["bars_input_available"] is False
    assert payload["market_data_fetch_performed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["bar_count"] == 0
    assert payload["trades"] == []


def test_rerunning_same_fixture_produces_byte_stable_artifact(tmp_path) -> None:
    bars_csv = tmp_path / "spy_daily.csv"
    _write_csv(bars_csv, 150 * ("100",) + 50 * ("200",) + ("220", "240"))
    config = _config(bars_source=str(bars_csv))

    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"
    write_etf_sma_backtest_artifact(
        build_etf_sma_backtest_from_csv(config),
        output_a,
    )
    write_etf_sma_backtest_artifact(
        build_etf_sma_backtest_from_csv(config),
        output_b,
    )

    assert output_a.read_bytes() == output_b.read_bytes()
    assert json.loads(output_a.read_text(encoding="utf-8")) == json.loads(
        output_b.read_text(encoding="utf-8")
    )


def test_cli_writes_backtest_before_runtime_config_loading(monkeypatch, tmp_path, capsys) -> None:
    bars_csv = tmp_path / "spy_daily.csv"
    run_log = tmp_path / "backtest.jsonl"
    _write_csv(bars_csv, 150 * ("100",) + 50 * ("200",) + ("220", "240"))

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("offline backtest must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            "etf-sma-backtest",
            "--symbol",
            "SPY",
            "--bars-csv",
            str(bars_csv),
            "--run-log",
            str(run_log),
            "--run-id",
            "unit_spy_sma_backtest",
            "--initial-cash",
            "1000",
            "--fast-window",
            "50",
            "--slow-window",
            "200",
            "--format",
            "json",
        ]
    ) == 0

    stdout = capsys.readouterr().out
    payload = json.loads(run_log.read_text(encoding="utf-8"))
    assert json.loads(stdout) == payload
    assert payload["run_id"] == "unit_spy_sma_backtest"
    assert payload["bars_input_available"] is True
    assert payload["stats"]["trade_count"] == 1


def _config(
    *,
    bars_source: str = "local.csv",
    fast_window: int = 50,
    slow_window: int = 200,
) -> EtfSmaBacktestConfig:
    return EtfSmaBacktestConfig(
        run_id="unit_spy_sma_backtest",
        symbol="SPY",
        bars_source=bars_source,
        initial_cash=Decimal("1000"),
        fast_window=fast_window,
        slow_window=slow_window,
    )


def _bars(values: tuple[str, ...]) -> tuple[EtfSmaBacktestBar, ...]:
    start = date(2026, 1, 1)
    return tuple(
        EtfSmaBacktestBar(
            (start + timedelta(days=index)).isoformat(),
            Decimal(value),
        )
        for index, value in enumerate(values)
    )


def _write_csv(path: Path, values: tuple[str, ...]) -> None:
    lines = ["date,symbol,close"]
    for bar in _bars(values):
        lines.append(f"{bar.as_of},SPY,{bar.close}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _import_references() -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _call_names() -> set[str]:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
