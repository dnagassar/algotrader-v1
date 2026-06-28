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
    build_strategy_challenger_payload,
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
    "manifest.json",
}

REQUIRED_RESULT_FIELDS = {
    "candidate_id",
    "strategy_family",
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
    "limitations",
    "promotion_classification",
    "labels",
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
    challenger_ids = candidate_ids - {"spy_sma_50_200_baseline"}
    assert len(challenger_ids) >= 2
    for result in jsonl_results:
        assert REQUIRED_RESULT_FIELDS <= set(result)
        assert set(STRATEGY_CHALLENGER_FACTORY_LABELS) <= set(result["labels"])

    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_count"] == 4
    assert {artifact["name"] for artifact in manifest["artifacts"]} == REQUIRED_ARTIFACTS - {"manifest.json"}
    assert manifest["safety"]["broker_mutation_performed"] is False
    assert manifest["safety"]["live_mutation_performed"] is False


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
