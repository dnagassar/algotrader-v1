from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.research.research_hypothesis_triage import (
    RESEARCH_HYPOTHESIS_TRIAGE_LABELS,
    ResearchHypothesisTriageConfig,
    run_research_hypothesis_triage,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src" / "algotrader" / "research" / "research_hypothesis_triage.py"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_research_hypothesis_triage.ps1"

REQUIRED_ARTIFACTS = {
    "research_hypothesis_triage.json",
    "research_hypothesis_triage.md",
    "manifest.json",
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


def test_triage_selects_volatility_regime_family_from_fixture_artifacts(
    tmp_path: Path,
) -> None:
    challenger_root = tmp_path / "challenger"
    preview_root = tmp_path / "preview"
    output_root = tmp_path / "triage"
    _write_fixture_artifacts(challenger_root, preview_root)

    payload = run_research_hypothesis_triage(
        ResearchHypothesisTriageConfig(
            challenger_root=challenger_root,
            preview_review_root=preview_root,
            output_root=output_root,
        )
    )

    assert {path.name for path in output_root.iterdir()} == REQUIRED_ARTIFACTS
    assert payload["phase"] == "v2.17_research_hypothesis_triage_next_family_selection"
    assert payload["classification"] == "next_family_selected_for_offline_research"
    assert payload["generated_at"] == "2026-06-26T00:00:00Z"
    assert payload["selected_next_family"] == "volatility-regime filter"
    assert payload["paper_candidate_count"] == 0
    assert payload["offline_shadow_candidate_count"] == 0
    assert payload["broker_access_performed"] is False
    assert payload["paper_submit_performed"] is False
    assert set(RESEARCH_HYPOTHESIS_TRIAGE_LABELS) <= set(payload["safety_labels"])

    taxonomy = payload["failure_taxonomy"]
    assert "relative_momentum_top1_126d_monthly" in taxonomy["oos_failure"]["candidate_ids"]
    assert "relative_momentum_equal_weight_top2_126d_monthly" in taxonomy["edge_broken"]["candidate_ids"]
    assert "relative_momentum_top1_126d_monthly" in taxonomy["high_cost_sensitivity"]["candidate_ids"]
    assert "relative_momentum_top1_126d_monthly" in taxonomy["anti_overfit_rejection"]["candidate_ids"]
    assert "spy_sma_10_50_long_only" in taxonomy["paper_promotion_blocked"]["candidate_ids"]

    assert payload["evidence_inventory"]["candidate_record_count"] == 4
    assert payload["evidence_inventory"]["records_malformed"] == []
    assert payload["evidence_inventory"]["records_incomplete"] == []
    assert payload["family_scores"][0]["family"] == "volatility-regime filter"
    assert payload["family_scores"][0]["rank"] == 1

    written = json.loads(
        (output_root / "research_hypothesis_triage.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert written["selected_next_family"] == "volatility-regime filter"
    assert manifest["artifact_count"] == len(REQUIRED_ARTIFACTS) - 1
    assert {artifact["name"] for artifact in manifest["artifacts"]} == (
        REQUIRED_ARTIFACTS - {"manifest.json"}
    )


def test_triage_blocks_selection_when_required_artifacts_are_missing(
    tmp_path: Path,
) -> None:
    payload = run_research_hypothesis_triage(
        ResearchHypothesisTriageConfig(
            challenger_root=tmp_path / "missing_challenger",
            preview_review_root=tmp_path / "missing_preview",
            output_root=tmp_path / "triage",
        )
    )

    assert payload["classification"] == "triage_blocked_artifacts_missing"
    assert payload["selected_next_family"] is None
    assert set(payload["evidence_inventory"]["records_unavailable"]) >= {
        "challenger_results",
        "preview_candidate_review",
    }
    assert payload["broker_mutation_performed"] is False
    assert (tmp_path / "triage" / "research_hypothesis_triage.json").exists()


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


def test_research_hypothesis_triage_module_imports_no_broker_network_llm_or_runtime_dependencies() -> None:
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


def test_run_research_hypothesis_triage_script_contract_and_invocation(
    tmp_path: Path,
) -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    for fragment in (
        "Runs deterministic offline v2.17 research hypothesis triage",
        "does not read a broker",
        "fetch market data",
        "Credential values are never printed",
        "TIINGO_API_KEY",
        "runs\\strategy_challengers\\research_hypothesis_triage_latest",
        "preflight_APP_PROFILE_is_paper",
        "preflight_TIINGO_API_KEY_loaded",
        "preflight_RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled",
        "algotrader.research.research_hypothesis_triage",
    ):
        assert fragment in script

    output_root = tmp_path / "triage out"
    challenger_root = tmp_path / "challenger with spaces"
    preview_root = tmp_path / "preview with spaces"
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
            "-ChallengerRoot",
            str(challenger_root),
            "-PreviewReviewRoot",
            str(preview_root),
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
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.research.research_hypothesis_triage" in args
    assert "--challenger-root" in args
    assert str(challenger_root) in args
    assert "--preview-review-root" in args
    assert str(preview_root) in args
    assert "--output-root" in args
    assert str(output_root) in args


def test_run_research_hypothesis_triage_script_blocks_loaded_credentials(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["APP_PROFILE"] = "paper"
    env["TIINGO_API_KEY"] = "set-but-not-printed"

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
    assert "set-but-not-printed" not in result.stdout
    assert not capture_path.exists()


def _write_fixture_artifacts(challenger_root: Path, preview_root: Path) -> None:
    challenger_root.mkdir(parents=True, exist_ok=True)
    preview_root.mkdir(parents=True, exist_ok=True)
    results = [
        _candidate_result(
            "spy_sma_10_50_long_only",
            "sma_crossover_long_only",
            "SPY",
            classification="reject",
            reasons=["drawdown_improvement_with_severe_return_degradation"],
            cost_status="highly_sensitive",
        ),
        _candidate_result(
            "spy_sma_100_200_long_only",
            "sma_crossover_long_only",
            "SPY",
            classification="keep_researching",
            reasons=["mixed_or_small_baseline_comparison"],
            cost_status="survived",
        ),
        _candidate_result(
            "relative_momentum_top1_126d_monthly",
            "etf_relative_momentum_basket",
            "ETF_BASKET",
            classification="reject",
            reasons=["materially_worse_return_and_drawdown_than_baseline"],
            cost_status="highly_sensitive",
        ),
        _candidate_result(
            "relative_momentum_equal_weight_top2_126d_monthly",
            "etf_relative_momentum_basket",
            "ETF_BASKET",
            classification="keep_researching",
            reasons=["full_sample_edge_failed_out_of_sample"],
            cost_status="edge_broken",
        ),
    ]
    rollups = [
        {
            "candidate_id": result["candidate_id"],
            "paper_candidate_allowed": False,
            "paper_candidate_blockers": [
                "v2_16_no_paper_promotion",
                "cross_asset_oos_or_cost_not_confirmed",
            ],
        }
        for result in results
    ]
    challenger_payload = {
        "record_type": "strategy_challenger_factory",
        "schema_version": "1",
        "factory_id": "fixture_strategy_challenger_factory",
        "run_id": "fixture_run",
        "as_of_end": "2026-06-26",
        "labels": ["research_only", "offline_only", "not_live_authorized", "profit_claim=none"],
        "symbols": ["SPY", "QQQ", "IWM", "TLT", "GLD"],
        "results": results,
        "promotion_recommendations": {
            "classification_recommendation": "preview_only_research_followup",
            "classification_counts": {
                "keep_researching": 2,
                "paper_candidate": 0,
                "preview_only": 0,
                "reject": 2,
            },
            "paper_candidate_count": 0,
            "cross_asset_validation": {"candidate_rollups": rollups},
        },
        "cross_asset_validation": {"candidate_rollups": rollups},
        "safety": {
            "broker_access_attempted": False,
            "broker_mutation_performed": False,
            "credential_access_attempted": False,
            "live_mutation_performed": False,
            "network_access_attempted": False,
            "paper_submit_performed": False,
        },
    }
    (challenger_root / "challenger_results.json").write_text(
        json.dumps(challenger_payload),
        encoding="utf-8",
    )
    (challenger_root / "promotion_recommendations.json").write_text(
        json.dumps(challenger_payload["promotion_recommendations"]),
        encoding="utf-8",
    )
    (challenger_root / "cross_asset_validation.json").write_text(
        json.dumps({"cross_asset_validation": {"candidate_rollups": rollups}}),
        encoding="utf-8",
    )
    preview_payload = {
        "record_type": "preview_candidate_review",
        "schema_version": "1",
        "review_id": "fixture_preview_review",
        "overall_recommendation": "reject_all_preview_only",
        "preview_candidate_count": 1,
        "paper_candidate_count": 0,
        "offline_shadow_candidates": [],
        "candidate_reviews": [
            {
                "candidate_id": "relative_momentum_top1_126d_monthly",
                "final_review_classification": "reject_preview",
                "anti_overfit_reasons": [
                    "severe_return_degradation",
                    "fragile_concentrated_unstable_edge",
                ],
            }
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
    (preview_root / "preview_candidate_review.json").write_text(
        json.dumps(preview_payload),
        encoding="utf-8",
    )
    (preview_root / "anti_overfit_flags.json").write_text(
        json.dumps({"candidate_flags": []}),
        encoding="utf-8",
    )
    (preview_root / "offline_shadow_candidates.json").write_text(
        json.dumps({"offline_shadow_candidates": []}),
        encoding="utf-8",
    )


def _candidate_result(
    candidate_id: str,
    strategy_family: str,
    symbol: str,
    *,
    classification: str,
    reasons: list[str],
    cost_status: str,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "strategy_family": strategy_family,
        "symbol": symbol,
        "role": "challenger",
        "metrics_status": "valid",
        "promotion_classification": classification,
        "promotion_reasons": reasons,
        "oos_status": "failed",
        "out_of_sample_validation": {
            "validation_passed": False,
            "validation_failed": True,
            "primary_window_passed": False,
            "primary_window_failed": True,
        },
        "cost_sensitivity_status": cost_status,
        "cost_sensitivity_summary": {
            "edge_broken_by_moderate_cost": cost_status == "edge_broken",
            "returns_highly_cost_sensitive": cost_status == "highly_sensitive",
        },
    }


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo research_hypothesis_triage_status=completed\r\n"
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
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_research_hypothesis_triage.ps1")
    return powershell
