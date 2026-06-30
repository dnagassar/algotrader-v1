from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.research.local_daily_bars import LocalDailyBar
from algotrader.research.volatility_regime_evidence import (
    VOLATILITY_REGIME_EVIDENCE_LABELS,
    VolatilityRegimeEvidenceConfig,
    build_volatility_regime_observations,
    classify_realized_volatility_series,
    compute_realized_volatility_series,
    run_volatility_regime_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src" / "algotrader" / "research" / "volatility_regime_evidence.py"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_volatility_regime_evidence.ps1"

REQUIRED_ARTIFACTS = {
    "volatility_regime_evidence.json",
    "volatility_regime_evidence.md",
    "manifest.json",
}

REQUIRED_JSON_FIELDS = {
    "phase",
    "classification",
    "generated_at",
    "source_data",
    "source_artifacts",
    "regime_rule",
    "data_inventory",
    "regime_summary",
    "latest_regimes",
    "failure_context_bridge",
    "regime_conditioned_diagnostics",
    "evidence",
    "inference",
    "selected_v2_19_next_action",
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


def test_realized_volatility_computation_uses_fixed_rolling_sample_stdev() -> None:
    realized = compute_realized_volatility_series(
        (0.01, 0.02, 0.03),
        lookback=3,
    )

    assert realized[0] is None
    assert realized[1] is None
    assert realized[2] == pytest.approx(0.01 * math.sqrt(252))


def test_no_lookahead_regime_classification_uses_prior_thresholds_only() -> None:
    classifications = classify_realized_volatility_series(
        (0.10, 0.20, 0.15),
        quantile_min_history=2,
        low_quantile=0.50,
        high_quantile=0.75,
    )

    assert classifications[0].regime == "insufficient_history"
    assert classifications[1].regime == "insufficient_history"
    assert classifications[2].low_vol_threshold == pytest.approx(0.10)
    assert classifications[2].high_vol_threshold == pytest.approx(0.20)
    assert classifications[2].regime == "normal_vol"


def test_insufficient_history_handling_marks_rows_before_thresholds_exist() -> None:
    bars = _bars_from_prices("SPY", (100, 101, 102, 103))

    observations = build_volatility_regime_observations(
        bars,
        rolling_lookback=3,
        quantile_min_history=2,
        low_quantile=0.33,
        high_quantile=0.67,
    )

    assert [item.regime for item in observations] == [
        "insufficient_history",
        "insufficient_history",
        "insufficient_history",
        "insufficient_history",
    ]
    assert observations[-1].realized_volatility is not None
    assert observations[-1].low_vol_threshold is None
    assert observations[-1].high_vol_threshold is None


def test_packet_schema_required_labels_and_artifacts(tmp_path: Path) -> None:
    data_manifest, paths = _write_data_fixture(tmp_path, ("SPY",))
    challenger, preview, triage = _write_prior_artifacts(tmp_path)
    output_root = tmp_path / "volatility packet"

    payload = run_volatility_regime_evidence(
        VolatilityRegimeEvidenceConfig(
            output_root=output_root,
            data_manifest=data_manifest,
            challenger_results_path=challenger,
            preview_review_path=preview,
            triage_path=triage,
            symbols=("SPY",),
            canonical_paths=paths,
            rolling_lookback=3,
            quantile_min_history=3,
            low_quantile=0.33,
            high_quantile=0.67,
        )
    )

    assert {path.name for path in output_root.iterdir()} == REQUIRED_ARTIFACTS
    assert REQUIRED_JSON_FIELDS <= set(payload)
    assert payload["phase"] == "v2.18_deterministic_volatility_regime_offline_evidence_packet"
    assert payload["paper_candidate_count"] == 0
    assert payload["offline_shadow_candidate_count"] == 0
    assert payload["broker_access_performed"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["paper_submit_performed"] is False
    assert payload["live_mutation_performed"] is False
    assert payload["market_data_fetch_performed"] is False
    assert set(VOLATILITY_REGIME_EVIDENCE_LABELS) <= set(payload["safety_labels"])
    assert "SPY" in payload["latest_regimes"]
    assert payload["regime_rule"]["lookahead_policy"].startswith("thresholds for each date exclude")

    written = json.loads(
        (output_root / "volatility_regime_evidence.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert written["classification"] == payload["classification"]
    assert manifest["artifact_count"] == 2
    assert {artifact["name"] for artifact in manifest["artifacts"]} == (
        REQUIRED_ARTIFACTS - {"manifest.json"}
    )


def test_missing_artifact_or_data_behavior_blocks_without_broker_access(tmp_path: Path) -> None:
    payload = run_volatility_regime_evidence(
        VolatilityRegimeEvidenceConfig(
            output_root=tmp_path / "out",
            data_manifest=tmp_path / "missing_manifest.json",
            challenger_results_path=tmp_path / "missing_challenger.json",
            preview_review_path=tmp_path / "missing_preview.json",
            triage_path=tmp_path / "missing_triage.json",
            symbols=("SPY",),
            rolling_lookback=3,
            quantile_min_history=3,
        )
    )

    assert payload["classification"] == "volatility_regime_blocked_missing_artifacts"
    assert payload["source_data"]["data_manifest"]["status"] == "missing"
    assert payload["data_inventory"]["symbols_found"] == []
    assert payload["broker_access_performed"] is False
    assert payload["market_data_fetch_performed"] is False
    assert (tmp_path / "out" / "volatility_regime_evidence.json").exists()


def test_volatility_regime_evidence_imports_no_broker_network_or_provider_dependencies() -> None:
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


def test_run_volatility_regime_evidence_script_contract_and_preflight(
    tmp_path: Path,
) -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    for fragment in (
        "Runs deterministic offline v2.18 volatility-regime evidence",
        "does not read a broker",
        "fetch market data",
        "Credential values are never printed",
        "TIINGO_API_KEY",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "runs\\strategy_challengers\\volatility_regime_evidence_latest",
        "preflight_APP_PROFILE_is_paper",
        "preflight_TIINGO_API_KEY_loaded",
        "preflight_ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled",
        "algotrader.research.volatility_regime_evidence",
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
    assert "preflight_ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.research.volatility_regime_evidence" in args
    assert "--data-manifest" in args
    assert str(tmp_path / "manifest.json") in args
    assert "--output-root" in args
    assert str(tmp_path / "out with spaces") in args


def test_run_volatility_regime_evidence_script_blocks_loaded_credentials_and_network_flag(
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


def _write_data_fixture(
    root: Path,
    symbols: tuple[str, ...],
) -> tuple[Path, dict[str, Path]]:
    paths = {
        symbol: _write_symbol_csv(
            root,
            symbol,
            (
                100,
                101,
                103,
                104,
                108,
                95,
                96,
                97,
                111,
                112,
                113,
                100,
                101,
                102,
            ),
        )
        for symbol in symbols
    }
    manifest = {
        "record_type": "multi_etf_adjusted_data_manifest",
        "schema_version": "1",
        "valid_symbols": list(symbols),
        "symbol_data": [
            {
                "symbol": symbol,
                "data_path": str(path),
                "row_count": 14,
                "earliest_date": "2026-01-01",
                "latest_date": "2026-01-14",
                "validation_status": "valid",
                "data_refresh_status": "not_required",
            }
            for symbol, path in paths.items()
        ],
        "safety": {
            "broker_access_attempted": False,
            "broker_mutation_performed": False,
            "credential_access_attempted": False,
            "live_mutation_performed": False,
            "network_access_attempted": False,
            "paper_submit_performed": False,
        },
    }
    manifest_path = root / "multi_etf_adjusted_data_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, paths


def _write_symbol_csv(root: Path, symbol: str, prices: tuple[int, ...]) -> Path:
    path = root / f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv"
    start = date(2026, 1, 1)
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for offset, price in enumerate(prices):
        on_date = start + timedelta(days=offset)
        rows.append(f"{symbol},{on_date.isoformat()},{price},{price},{price},{price},{price},1000")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _write_prior_artifacts(root: Path) -> tuple[Path, Path, Path]:
    challenger = {
        "record_type": "strategy_challenger_factory",
        "schema_version": "1",
        "results": [
            {
                "candidate_id": "spy_sma_50_200_baseline",
                "strategy_family": "sma_crossover_long_only",
                "symbol": "SPY",
                "exposure_percentage": "75.0",
                "trade_count": 31,
                "oos_status": "failed",
                "cost_sensitivity_status": "survived",
                "promotion_classification": "keep_researching",
            },
            {
                "candidate_id": "relative_momentum_top1_126d_monthly",
                "strategy_family": "etf_relative_momentum_basket",
                "symbol": "ETF_BASKET",
                "oos_status": "failed",
                "cost_sensitivity_status": "highly_sensitive",
                "promotion_classification": "reject",
            },
        ],
        "promotion_recommendations": {"paper_candidate_count": 0},
        "safety": _safe_source_flags(),
    }
    preview = {
        "record_type": "preview_candidate_review",
        "schema_version": "1",
        "overall_recommendation": "reject_all_preview_only",
        "candidate_reviews": [
            {
                "candidate_id": "relative_momentum_top1_126d_monthly",
                "final_review_classification": "reject_preview",
            }
        ],
        "paper_candidate_count": 0,
        "safety": _safe_source_flags(),
    }
    triage = {
        "record_type": "research_hypothesis_triage",
        "schema_version": "1",
        "phase": "v2.17_research_hypothesis_triage_next_family_selection",
        "classification": "next_family_selected_for_offline_research",
        "selected_next_family": "volatility-regime filter",
        "failure_taxonomy": {
            "oos_failure": {"count": 2, "candidate_ids": ["spy_sma_50_200_baseline"]},
            "high_cost_sensitivity": {
                "count": 1,
                "candidate_ids": ["relative_momentum_top1_126d_monthly"],
            },
            "anti_overfit_rejection": {"count": 1, "candidate_ids": []},
            "paper_promotion_blocked": {"count": 2, "candidate_ids": []},
        },
        "v2_18_next_action": {
            "selected_family": "volatility-regime filter",
            "title": "Build deterministic volatility-regime offline evidence packet",
        },
        "safety": _safe_source_flags(),
    }
    challenger_path = root / "challenger_results.json"
    preview_path = root / "preview_candidate_review.json"
    triage_path = root / "research_hypothesis_triage.json"
    challenger_path.write_text(json.dumps(challenger), encoding="utf-8")
    preview_path.write_text(json.dumps(preview), encoding="utf-8")
    triage_path.write_text(json.dumps(triage), encoding="utf-8")
    return challenger_path, preview_path, triage_path


def _safe_source_flags() -> dict[str, bool]:
    return {
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "credential_access_attempted": False,
        "live_mutation_performed": False,
        "network_access_attempted": False,
        "paper_submit_performed": False,
    }


def _bars_from_prices(symbol: str, prices: tuple[int, ...]) -> tuple[LocalDailyBar, ...]:
    start = date(2026, 1, 1)
    bars = []
    for offset, raw_price in enumerate(prices):
        price = Decimal(raw_price)
        bars.append(
            LocalDailyBar(
                symbol=symbol,
                date=start + timedelta(days=offset),
                open=price,
                high=price,
                low=price,
                close=price,
                adjusted_close=price,
                volume=1000,
            )
        )
    return tuple(bars)


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo volatility_regime_evidence_status=completed\r\n"
        "echo broker_access_performed=false\r\n"
        "echo broker_mutation_performed=false\r\n"
        "echo paper_submit_performed=false\r\n"
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
        "TIINGO_API_KEY",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_volatility_regime_evidence.ps1")
    return powershell
