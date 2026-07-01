from __future__ import annotations

import ast
import json
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.research.spy_rsi_oos_backtest import (
    build_spy_rsi_oos_backtest_packet,
    classify_rsi_oos_decision,
    write_spy_rsi_oos_backtest_artifacts,
)
from algotrader.signals.spy_rsi_mean_reversion import (
    SPYRsiMeanReversionSignalConfig,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src" / "algotrader" / "research" / "spy_rsi_oos_backtest.py"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_spy_rsi_oos_backtest.ps1"

REQUIRED_METRIC_FIELDS = {
    "start_date",
    "end_date",
    "row_count",
    "total_return",
    "cagr",
    "annualized_return",
    "max_drawdown",
    "sharpe_like_score",
    "risk_adjusted_proxy",
    "exposure_percentage",
    "trade_count",
    "win_count",
    "loss_count",
    "average_holding_period_days",
    "cost_assumptions",
}


def test_fixed_rsi_parameters_match_existing_signal_defaults(tmp_path: Path) -> None:
    csv_path = _write_price_csv(tmp_path / "spy.csv", _oscillating_prices(1300))
    packet = build_spy_rsi_oos_backtest_packet(daily_bars_csv=csv_path)
    strategy = packet["summary"]["strategy"]
    signal_defaults = SPYRsiMeanReversionSignalConfig(
        as_of=datetime(2026, 1, 2, tzinfo=UTC)
    )

    assert strategy["symbol"] == "SPY"
    assert strategy["basis"] == "adjusted_close"
    assert strategy["rsi_period"] == signal_defaults.lookback_window == 14
    assert Decimal(strategy["oversold_threshold"]) == signal_defaults.oversold_threshold
    assert Decimal(strategy["overbought_threshold"]) == signal_defaults.overbought_threshold
    assert strategy["thresholds_evaluated"] == {
        "oversold": ["30"],
        "overbought": ["70"],
    }


def test_no_threshold_optimization_or_parameter_search_occurs(tmp_path: Path) -> None:
    csv_path = _write_price_csv(tmp_path / "spy.csv", _oscillating_prices(1300))

    summary = build_spy_rsi_oos_backtest_packet(daily_bars_csv=csv_path)["summary"]

    assert summary["threshold_optimization_performed"] is False
    assert summary["parameter_search_performed"] is False
    assert summary["threshold_change_performed"] is False
    assert summary["strategy_promotion_performed"] is False
    assert summary["paper_mutation_promotion_performed"] is False
    for window in summary["windows"]:
        policy = window["threshold_policy"]
        assert policy["thresholds_evaluated"] == {
            "oversold": ["30"],
            "overbought": ["70"],
        }
        assert policy["optimization_performed"] is False
        assert policy["parameter_search_performed"] is False
        assert policy["rsi_period_tuning_performed"] is False


def test_oos_windows_are_deterministic_and_chronological(tmp_path: Path) -> None:
    csv_path = _write_price_csv(tmp_path / "spy.csv", _oscillating_prices(1300))

    first = build_spy_rsi_oos_backtest_packet(daily_bars_csv=csv_path)
    second = build_spy_rsi_oos_backtest_packet(daily_bars_csv=csv_path)

    assert first == second
    windows = {window["window_id"]: window for window in first["backtest_by_window"]}
    assert list(windows) == [
        "full_available_reference",
        "chronological_earlier_half",
        "chronological_later_half",
        "recent_3y_holdout",
        "trailing_5y_earlier_half",
        "trailing_5y_later_half",
    ]
    assert windows["chronological_earlier_half"]["row_count"] == 650
    assert windows["chronological_later_half"]["row_count"] == 650
    assert windows["recent_3y_holdout"]["row_count"] == 756
    assert windows["trailing_5y_earlier_half"]["row_count"] == 630
    assert windows["trailing_5y_later_half"]["row_count"] == 630
    assert windows["chronological_earlier_half"]["end_index_exclusive"] == (
        windows["chronological_later_half"]["start_index"]
    )


def test_summary_includes_required_comparators_metrics_and_decision(
    tmp_path: Path,
) -> None:
    csv_path = _write_price_csv(tmp_path / "spy.csv", _oscillating_prices(1300))

    packet = build_spy_rsi_oos_backtest_packet(daily_bars_csv=csv_path)
    summary = packet["summary"]

    assert summary["final_decision"] in {
        "reject_candidate",
        "keep_shadow",
        "needs_regime_filter",
        "needs_longer_oos",
        "promote_to_paper_preview_candidate",
    }
    assert {item["strategy_id"] for item in summary["comparators"]} == {
        "spy_buy_and_hold_comparator",
        "spy_sma_50_200_training_wheel",
    }
    for window in packet["backtest_by_window"]:
        metrics = window["metrics_by_strategy"]
        assert set(metrics) == {
            "spy_buy_and_hold_comparator",
            "spy_sma_50_200_training_wheel",
            "spy_rsi_14_mean_reversion_fixed_shadow",
        }
        for item in metrics.values():
            assert REQUIRED_METRIC_FIELDS <= set(item)
        assert set(window["comparisons"]) == {
            "rsi_vs_buy_and_hold",
            "rsi_vs_sma",
            "sma_vs_buy_and_hold",
        }
        assert window["decision_classification"] in summary["decision_options"]
        assert window["broker_read_performed"] is False
        assert window["broker_mutation_performed"] is False
        assert window["paper_submit_performed"] is False
        assert window["network_fetch_performed"] is False


def test_decision_mapping_is_deterministic_for_poor_mixed_strong_and_short_oos() -> None:
    strong = _window("promote_to_paper_preview_candidate")
    poor = _window("reject_candidate")
    keep = _window("keep_shadow")

    assert (
        classify_rsi_oos_decision((poor, poor, poor), source_usable_bar_count=1300)
        == "reject_candidate"
    )
    assert (
        classify_rsi_oos_decision((strong, poor, keep), source_usable_bar_count=1300)
        == "needs_regime_filter"
    )
    assert (
        classify_rsi_oos_decision((strong, strong, strong), source_usable_bar_count=1300)
        == "promote_to_paper_preview_candidate"
    )
    assert (
        classify_rsi_oos_decision((keep, keep, keep), source_usable_bar_count=1300)
        == "keep_shadow"
    )
    assert (
        classify_rsi_oos_decision((strong, strong, strong), source_usable_bar_count=500)
        == "needs_longer_oos"
    )


def test_artifacts_are_written_under_ignored_runs_contract(tmp_path: Path) -> None:
    csv_path = _write_price_csv(tmp_path / "spy.csv", _oscillating_prices(1300))
    packet = build_spy_rsi_oos_backtest_packet(daily_bars_csv=csv_path)
    output_root = tmp_path / "runs" / "strategy_challengers" / "rsi_oos" / "latest"

    paths = write_spy_rsi_oos_backtest_artifacts(packet, output_root)

    assert {path.name for path in paths.values()} == {
        "backtest_summary.json",
        "backtest_trades.jsonl",
        "backtest_by_window.jsonl",
        "decision_brief.md",
    }
    summary = json.loads(paths["backtest_summary_json"].read_text(encoding="utf-8"))
    windows = _read_jsonl(paths["backtest_by_window_jsonl"])
    trades = _read_jsonl(paths["backtest_trades_jsonl"])
    brief = paths["decision_brief_md"].read_text(encoding="utf-8")
    assert summary["classification_recommendation"] == packet["summary"][
        "classification_recommendation"
    ]
    assert len(windows) == packet["summary"]["window_count"]
    assert trades
    assert "fixed-parameter" in brief
    assert "does not optimize thresholds" in brief
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    git_result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert git_result.returncode == 0, git_result.stderr
    assert git_result.stdout.strip() == ""


def test_module_introduces_no_broker_network_or_order_imports() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(MODULE_PATH))
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
    imports = _import_references(tree)
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert not any(
        imported == prefix or imported.startswith(f"{prefix}.")
        for imported in imports
        for prefix in forbidden_prefixes
    )
    assert call_names.isdisjoint(forbidden_calls)


def test_run_spy_rsi_oos_backtest_script_contract_and_preflight(tmp_path: Path) -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    for fragment in (
        "fixed-parameter SPY RSI OOS backtest gate",
        "does not read a broker",
        "mutate broker state",
        "Credential values are never printed",
        "runs\\strategy_challengers\\rsi_oos\\latest",
        "runs\\operator_input\\m446_spy_daily_tiingo_adjusted_canonical.csv",
        "preflight_APP_PROFILE_is_paper",
        "preflight_credential_variables_loaded",
        "algotrader.research.spy_rsi_oos_backtest",
    ):
        assert fragment in script

    output_root = tmp_path / "rsi oos"
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
    assert "-m algotrader.research.spy_rsi_oos_backtest" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--daily-bars-csv" in args
    assert str(bars_csv) in args
    assert "--as-of-date 2026-01-02" in args


def test_run_spy_rsi_oos_backtest_script_blocks_loaded_credentials(
    tmp_path: Path,
) -> None:
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


def _window(decision: str) -> dict[str, object]:
    return {
        "window_id": decision,
        "window_role": "test",
        "decision_classification": decision,
    }


def _write_price_csv(path: Path, prices: tuple[Decimal, ...]) -> Path:
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
    return path


def _oscillating_prices(count: int) -> tuple[Decimal, ...]:
    price = Decimal("100")
    prices: list[Decimal] = []
    for index in range(count):
        if index % 60 < 30:
            price += Decimal("0.60")
        else:
            price -= Decimal("0.55")
        if price < Decimal("20"):
            price = Decimal("20")
        prices.append(price)
    return tuple(prices)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _import_references(tree: ast.AST) -> list[str]:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo spy_rsi_oos_backtest_status=completed\r\n"
        "echo broker_mutation_performed=false\r\n"
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
        pytest.skip("PowerShell is required to verify run_spy_rsi_oos_backtest.ps1")
    return powershell
