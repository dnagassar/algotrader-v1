from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.research.local_daily_bars import LocalDailyBar
from algotrader.research.volatility_filtered_spy_sma_backtest import (
    VOLATILITY_FILTERED_SPY_SMA_BACKTEST_CLASSIFICATIONS,
    VOLATILITY_FILTERED_SPY_SMA_BACKTEST_LABELS,
    VolatilityFilteredSpySmaBacktestConfig,
    build_volatility_filtered_spy_sma_payload,
    build_volatility_filtered_spy_sma_signal_rows,
    compute_volatility_filtered_spy_sma_metrics,
    write_volatility_filtered_spy_sma_artifacts,
)
from algotrader.research.volatility_regime_evidence import (
    build_volatility_regime_observations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "volatility_filtered_spy_sma_backtest.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_volatility_filtered_spy_sma_backtest.ps1"

REQUIRED_ARTIFACTS = {
    "volatility_filtered_spy_sma_backtest.json",
    "volatility_filtered_spy_sma_backtest.md",
    "manifest.json",
}

REQUIRED_JSON_FIELDS = {
    "phase",
    "classification",
    "generated_at",
    "source_data",
    "source_artifacts",
    "baseline_rule",
    "volatility_regime_rule",
    "filtered_candidate_rule",
    "data_inventory",
    "backtest_summary",
    "baseline_metrics",
    "filtered_candidate_metrics",
    "comparison",
    "cost_sensitivity",
    "oos_or_split_summary",
    "evidence",
    "inference",
    "limitations",
    "selected_v2_20_next_action",
    "paper_candidate_count",
    "offline_shadow_candidate_count",
    "safety_labels",
    "broker_access_performed",
    "broker_mutation_performed",
    "paper_submit_performed",
    "live_mutation_performed",
    "market_data_fetch_performed",
    "normal_pytest_offline_credential_free",
}

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "numpy",
    "openai",
    "pandas",
    "requests",
    "socket",
    "urllib",
    "yfinance",
)


def test_signal_rows_reuse_v2_18_no_lookahead_volatility_regime() -> None:
    bars = _bars_from_prices((100, 101, 103, 104, 108, 95, 96, 97, 111, 112))

    rows = build_volatility_filtered_spy_sma_signal_rows(
        bars,
        short_window=2,
        long_window=3,
        rolling_lookback=3,
        quantile_min_history=2,
        low_quantile=0.33,
        high_quantile=0.67,
    )
    observations = build_volatility_regime_observations(
        bars,
        rolling_lookback=3,
        quantile_min_history=2,
        low_quantile=0.33,
        high_quantile=0.67,
    )

    assert len(rows) == len(observations)
    for row, observation in zip(rows, observations):
        assert row["date"] == observation.date.isoformat()
        assert row["volatility_regime"] == observation.regime
        assert row["volatility_realized_annualized"] == observation.realized_volatility
        assert row["volatility_low_threshold"] == observation.low_vol_threshold
        assert row["volatility_high_threshold"] == observation.high_vol_threshold


def test_sma_baseline_signal_uses_adjusted_close_not_raw_close() -> None:
    bars = _bars_from_prices(
        (10, 10, 10, 20, 30),
        raw_closes=(30, 20, 10, 10, 10),
    )

    rows = build_volatility_filtered_spy_sma_signal_rows(
        bars,
        short_window=2,
        long_window=3,
        rolling_lookback=2,
        quantile_min_history=10,
    )

    latest = rows[-1]
    assert latest["sma_short"] == "25"
    assert latest["sma_long"] == "20"
    assert latest["baseline_posture"] == "risk_on"
    assert latest["baseline_target_exposure"] == 1
    assert latest["filtered_target_exposure"] == 1


def test_high_vol_regime_forces_candidate_cash_without_changing_baseline() -> None:
    bars = _bars_from_prices((100, 101, 102, 103, 104, 200, 210, 220))

    rows = build_volatility_filtered_spy_sma_signal_rows(
        bars,
        short_window=2,
        long_window=3,
        rolling_lookback=2,
        quantile_min_history=2,
        low_quantile=0.33,
        high_quantile=0.67,
    )

    forced_rows = [
        row
        for row in rows
        if row["baseline_target_exposure"] == 1
        and row["volatility_regime"] == "high_vol"
    ]
    assert forced_rows
    assert forced_rows[0]["baseline_posture"] == "risk_on"
    assert forced_rows[0]["filtered_posture"] == "forced_cash_high_vol"
    assert forced_rows[0]["filtered_target_exposure"] == 0


def test_insufficient_history_rows_stay_cash() -> None:
    rows = build_volatility_filtered_spy_sma_signal_rows(
        _bars_from_prices((100, 101, 102, 103)),
        short_window=2,
        long_window=5,
        rolling_lookback=2,
        quantile_min_history=10,
    )

    assert {row["baseline_posture"] for row in rows} == {"insufficient_history"}
    assert {row["filtered_posture"] for row in rows} == {"insufficient_history"}
    assert {row["baseline_target_exposure"] for row in rows} == {0}
    assert {row["filtered_target_exposure"] for row in rows} == {0}


def test_metrics_apply_prior_day_exposure_and_count_forced_cash_days() -> None:
    rows = (
        _signal_row(0, "2026-01-01", "100", "insufficient_history", 0, "insufficient_history", 0),
        _signal_row(1, "2026-01-02", "100", "risk_on", 1, "risk_on", 1),
        _signal_row(2, "2026-01-03", "110", "risk_on", 1, "forced_cash_high_vol", 0, "high_vol"),
        _signal_row(3, "2026-01-04", "121", "risk_on", 1, "risk_on", 1),
    )

    baseline = compute_volatility_filtered_spy_sma_metrics(
        rows,
        exposure_key="baseline_target_exposure",
    )
    filtered = compute_volatility_filtered_spy_sma_metrics(
        rows,
        exposure_key="filtered_target_exposure",
    )

    assert baseline["total_return"] == "0.21"
    assert baseline["exposure_days"] == 2
    assert baseline["trade_count"] == 1
    assert filtered["total_return"] == "0.1"
    assert filtered["exposure_days"] == 1
    assert filtered["trade_count"] == 2
    assert filtered["high_vol_forced_cash_days"] == 1
    assert filtered["evaluated_return_count"] == 2


def test_packet_schema_required_labels_and_artifacts(tmp_path: Path) -> None:
    data_manifest = _write_data_fixture(tmp_path)
    volatility_evidence = _write_volatility_evidence_fixture(tmp_path)
    validation_windows = _write_validation_windows_fixture(tmp_path, row_count=280)
    cost_sensitivity = _write_cost_sensitivity_fixture(tmp_path)
    output_root = tmp_path / "volatility filtered packet"

    payload = build_volatility_filtered_spy_sma_payload(
        VolatilityFilteredSpySmaBacktestConfig(
            output_root=output_root,
            data_manifest=data_manifest,
            volatility_regime_evidence_path=volatility_evidence,
            validation_windows_path=validation_windows,
            cost_sensitivity_path=cost_sensitivity,
        )
    )
    paths = write_volatility_filtered_spy_sma_artifacts(payload, output_root=output_root)

    assert {path.name for path in output_root.iterdir()} == REQUIRED_ARTIFACTS
    assert set(paths) == {"json", "markdown", "manifest"}
    assert REQUIRED_JSON_FIELDS <= set(payload)
    assert payload["phase"] == "v2.19_spy_sma50_200_fixed_volatility_regime_filter_offline_backtest"
    assert payload["classification"] in VOLATILITY_FILTERED_SPY_SMA_BACKTEST_CLASSIFICATIONS
    assert payload["paper_candidate_count"] == 0
    assert payload["offline_shadow_candidate_count"] == 0
    assert payload["broker_access_performed"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["paper_submit_performed"] is False
    assert payload["live_mutation_performed"] is False
    assert payload["market_data_fetch_performed"] is False
    assert payload["normal_pytest_offline_credential_free"] is True
    assert set(VOLATILITY_FILTERED_SPY_SMA_BACKTEST_LABELS) <= set(payload["safety_labels"])
    assert payload["source_data"]["spy_daily_bars"]["status"] == "available"
    assert payload["baseline_rule"]["price_basis"] == "adjusted_close"
    assert payload["volatility_regime_rule"]["lookahead_policy"].startswith("Current realized")
    assert payload["filtered_candidate_rule"]["parameter_search_performed"] is False
    assert payload["cost_sensitivity"]["status"] == "computed"
    assert payload["oos_or_split_summary"]["status"] == "computed"

    written = json.loads(paths["json"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert written["classification"] == payload["classification"]
    assert {Path(item["path"]).name for item in manifest["artifacts"]} == (
        REQUIRED_ARTIFACTS - {"manifest.json"}
    )


def test_missing_data_or_artifact_behavior_blocks_without_broker_access(tmp_path: Path) -> None:
    output_root = tmp_path / "out"

    payload = build_volatility_filtered_spy_sma_payload(
        VolatilityFilteredSpySmaBacktestConfig(
            output_root=output_root,
            data_manifest=tmp_path / "missing_manifest.json",
            volatility_regime_evidence_path=tmp_path / "missing_evidence.json",
            validation_windows_path=tmp_path / "missing_validation_windows.json",
            cost_sensitivity_path=tmp_path / "missing_cost_sensitivity.json",
        )
    )
    paths = write_volatility_filtered_spy_sma_artifacts(payload, output_root=output_root)

    assert payload["classification"] == "volatility_filtered_sma_blocked_missing_data"
    assert payload["source_data"]["data_manifest"]["status"] == "missing"
    assert payload["source_data"]["spy_daily_bars"]["status"] == "missing_manifest"
    assert payload["broker_access_performed"] is False
    assert payload["market_data_fetch_performed"] is False
    assert paths["json"].exists()


def test_volatility_filtered_spy_sma_imports_no_broker_network_or_provider_dependencies() -> None:
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
        if any(
            imported == prefix or imported.startswith(f"{prefix}.")
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        )
    ]
    assert violations == []


def test_run_volatility_filtered_spy_sma_script_contract_and_preflight(
    tmp_path: Path,
) -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    for fragment in (
        "Runs deterministic offline v2.19 SPY SMA50/200 volatility-filter backtest",
        "does not read a broker",
        "fetch market data",
        "Credential values are never printed",
        "TIINGO_API_KEY",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "runs\\strategy_challengers\\volatility_filtered_spy_sma_latest",
        "preflight_APP_PROFILE_is_paper",
        "preflight_TIINGO_API_KEY_loaded",
        "preflight_ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled",
        "algotrader.research.volatility_filtered_spy_sma_backtest",
    ):
        assert fragment in script

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
            str(tmp_path / "out with spaces"),
            "-DataManifest",
            str(tmp_path / "manifest.json"),
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
    assert "preflight_TIINGO_API_KEY_loaded=false" in result.stdout
    assert "preflight_ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.research.volatility_filtered_spy_sma_backtest" in args
    assert "--data-manifest" in args
    assert str(tmp_path / "manifest.json") in args
    assert "--output-root" in args
    assert str(tmp_path / "out with spaces") in args


def test_run_volatility_filtered_spy_sma_script_blocks_loaded_credentials_and_network_flag(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["APP_PROFILE"] = "paper"
    env["TIINGO_API_KEY"] = "set-but-not-printed"
    env["ALGO_TRADER_ALLOW_NETWORK_TESTS"] = "1"

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
    assert "preflight_TIINGO_API_KEY_loaded=true" in result.stdout
    assert "preflight_ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled=true" in result.stdout
    assert "set-but-not-printed" not in result.stdout
    assert not capture_path.exists()


def _signal_row(
    index: int,
    on_date: str,
    adjusted_close: str,
    baseline_posture: str,
    baseline_target: int,
    filtered_posture: str,
    filtered_target: int,
    volatility_regime: str = "normal_vol",
) -> dict[str, object]:
    return {
        "index": index,
        "symbol": "SPY",
        "date": on_date,
        "adjusted_close": adjusted_close,
        "sma_short": None,
        "sma_long": None,
        "baseline_posture": baseline_posture,
        "baseline_target_exposure": baseline_target,
        "volatility_regime": volatility_regime,
        "volatility_realized_annualized": None,
        "volatility_low_threshold": None,
        "volatility_high_threshold": None,
        "filtered_posture": filtered_posture,
        "filtered_target_exposure": filtered_target,
    }


def _write_data_fixture(root: Path) -> Path:
    csv_path = root / "spy_daily_tiingo_adjusted_canonical.csv"
    _write_symbol_csv(csv_path, _fixture_prices(280))
    manifest = {
        "record_type": "multi_etf_adjusted_data_manifest",
        "schema_version": "1",
        "source": "unit_test_fixture",
        "generated_at": "2026-01-01T00:00:00Z",
        "expected_latest_date": "2026-10-07",
        "valid_symbols": ["SPY"],
        "symbol_data": {
            "SPY": {
                "symbol": "SPY",
                "data_path": str(csv_path),
                "row_count": 280,
                "earliest_date": "2026-01-01",
                "latest_date": "2026-10-07",
                "validation_status": "valid",
            }
        },
    }
    manifest_path = root / "multi_etf_adjusted_data_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _write_volatility_evidence_fixture(root: Path) -> Path:
    payload = {
        "phase": "v2.18_deterministic_volatility_regime_offline_evidence_packet",
        "classification": "volatility_regime_candidate_worth_offline_backtest",
        "generated_at": "2026-01-01T00:00:00Z",
        "regime_rule": {"lookahead_policy": "prior realized volatility only"},
        "latest_regimes": {"SPY": {"regime": "normal_vol", "date": "2026-10-07"}},
        "selected_v2_19_next_action": "Run fixed SPY SMA volatility filter backtest.",
        "safety_labels": [
            "research_only",
            "offline_only",
            "not_live_authorized",
            "paper_submit_authorized=false",
            "profit_claim=none",
            "broker_state_not_required",
            "no_strategy_promoted",
            "no_broker_access",
            "no_market_data_fetch",
        ],
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "market_data_fetch_performed": False,
    }
    path = root / "volatility_regime_evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_validation_windows_fixture(root: Path, *, row_count: int) -> Path:
    half = row_count // 2
    payload = {
        "validation_window_method": "fixture_full_plus_half_split",
        "validation_windows": [
            {
                "window_id": "full_sample",
                "role": "full_sample",
                "symbol": "SPY",
                "start_index": 0,
                "end_index_exclusive": row_count,
                "start_date": "2026-01-01",
                "end_date": "2026-10-07",
            },
            {
                "window_id": "early_train",
                "role": "train",
                "symbol": "SPY",
                "start_index": 0,
                "end_index_exclusive": half,
                "start_date": "2026-01-01",
                "end_date": "2026-05-20",
            },
            {
                "window_id": "later_test",
                "role": "test",
                "symbol": "SPY",
                "start_index": half,
                "end_index_exclusive": row_count,
                "start_date": "2026-05-21",
                "end_date": "2026-10-07",
            },
        ],
    }
    path = root / "validation_windows.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_cost_sensitivity_fixture(root: Path) -> Path:
    payload = {
        "cost_assumptions": [
            {
                "cost_assumption_id": "zero_cost",
                "fee_bps_per_transition": "0",
                "slippage_bps_per_transition": "0",
                "total_cost_bps_per_transition": "0",
            },
            {
                "cost_assumption_id": "moderate_cost_5bps",
                "fee_bps_per_transition": "1",
                "slippage_bps_per_transition": "4",
                "total_cost_bps_per_transition": "5",
            },
        ]
    }
    path = root / "cost_sensitivity.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fixture_prices(count: int) -> tuple[Decimal, ...]:
    prices: list[Decimal] = []
    price = Decimal("100")
    for index in range(count):
        if index in {230, 231, 232, 233}:
            price += Decimal("18") if index % 2 == 0 else Decimal("-10")
        else:
            price += Decimal("0.25")
        prices.append(price)
    return tuple(prices)


def _write_symbol_csv(path: Path, prices: tuple[Decimal, ...]) -> None:
    start = date(2026, 1, 1)
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for offset, price in enumerate(prices):
        on_date = start + timedelta(days=offset)
        rows.append(
            f"SPY,{on_date.isoformat()},{price},{price},{price},{price},{price},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _bars_from_prices(
    adjusted_closes: tuple[int, ...],
    *,
    raw_closes: tuple[int, ...] | None = None,
) -> tuple[LocalDailyBar, ...]:
    start = date(2026, 1, 1)
    raw_values = raw_closes or adjusted_closes
    bars = []
    for offset, (raw_price, adjusted_price) in enumerate(zip(raw_values, adjusted_closes)):
        raw = Decimal(raw_price)
        adjusted = Decimal(adjusted_price)
        high = max(raw, adjusted)
        low = min(raw, adjusted)
        bars.append(
            LocalDailyBar(
                symbol="SPY",
                date=start + timedelta(days=offset),
                open=raw,
                high=high,
                low=low,
                close=raw,
                adjusted_close=adjusted,
                volume=1000,
            )
        )
    return tuple(bars)


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo volatility_filtered_spy_sma_backtest_status=completed\r\n"
        "echo broker_access_performed=false\r\n"
        "echo broker_mutation_performed=false\r\n"
        "echo paper_submit_performed=false\r\n"
        "echo live_mutation_performed=false\r\n"
        "echo market_data_fetch_performed=false\r\n"
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
        "TIINGO_API_KEY",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify the v2.19 runner script")
    return powershell
