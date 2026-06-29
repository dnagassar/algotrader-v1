from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research.preview_candidate_review import (
    PREVIEW_CANDIDATE_REVIEW_LABELS,
    PreviewCandidateReviewConfig,
    build_preview_candidate_review_payload,
    run_preview_candidate_review,
    validate_preview_review_classification,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src" / "algotrader" / "research" / "preview_candidate_review.py"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_preview_candidate_review.ps1"

REQUIRED_ARTIFACTS = {
    "preview_candidate_review.json",
    "preview_candidate_review.md",
    "anti_overfit_flags.json",
    "offline_shadow_candidates.json",
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


def test_review_loads_preview_only_candidates_from_fixture_artifacts(tmp_path: Path) -> None:
    input_root = tmp_path / "challenger"
    output_root = tmp_path / "review"
    _write_fixture_artifacts(
        input_root,
        [
            _candidate_result("candidate_a", "SPY", classification="keep_researching"),
            _candidate_result("candidate_a", "QQQ", return_delta="0.08"),
            _candidate_result("candidate_b", "SPY", classification="reject"),
        ],
    )

    payload = run_preview_candidate_review(
        PreviewCandidateReviewConfig(input_root=input_root, output_root=output_root)
    )

    assert {path.name for path in output_root.iterdir()} == REQUIRED_ARTIFACTS
    assert payload["preview_result_count"] == 1
    assert payload["preview_candidate_count"] == 1
    assert payload["paper_candidate_count"] == 0
    assert payload["safety"]["broker_access_attempted"] is False
    review = payload["candidate_reviews"][0]
    assert review["candidate_id"] == "candidate_a"
    assert review["symbols_evaluated"] == ["QQQ", "SPY"]
    assert review["preview_symbols"] == ["QQQ"]
    assert set(PREVIEW_CANDIDATE_REVIEW_LABELS) <= set(review["safety_labels"])

    review_json = json.loads(
        (output_root / "preview_candidate_review.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert review_json["candidate_reviews"] == payload["candidate_reviews"]
    assert manifest["artifact_count"] == len(REQUIRED_ARTIFACTS) - 1
    assert {artifact["name"] for artifact in manifest["artifacts"]} == (
        REQUIRED_ARTIFACTS - {"manifest.json"}
    )


def test_review_handles_no_preview_only_candidates(tmp_path: Path) -> None:
    input_root = tmp_path / "challenger"
    _write_fixture_artifacts(
        input_root,
        [
            _candidate_result("candidate_a", "SPY", classification="keep_researching"),
            _candidate_result("candidate_b", "QQQ", classification="reject"),
        ],
    )

    payload = run_preview_candidate_review(
        PreviewCandidateReviewConfig(input_root=input_root, output_root=tmp_path / "review")
    )

    assert payload["preview_result_count"] == 0
    assert payload["candidate_reviews"] == []
    assert payload["overall_recommendation"] == "reject_all_preview_only"


def test_anti_overfit_flags_detect_single_symbol_edge() -> None:
    payload = _build_payload(
        [
            _candidate_result("candidate_single", "SPY"),
            _candidate_result(
                "candidate_single",
                "QQQ",
                classification="keep_researching",
                oos_status="failed",
                return_delta="-0.01",
            ),
        ]
    )

    flags = _review_by_id(payload, "candidate_single")["anti_overfit_flags"]
    assert flags["single_symbol_edge_flag"] is True
    assert flags["concentrated_edge_flag"] is True


def test_anti_overfit_flags_detect_high_churn() -> None:
    payload = _build_payload(
        [_candidate_result("candidate_churn", "SPY", transition_count=140)]
    )

    review = _review_by_id(payload, "candidate_churn")
    assert review["anti_overfit_flags"]["high_churn_flag"] is True
    assert review["transition_churn_summary"]["high_churn_symbols"] == ["SPY"]


def test_anti_overfit_flags_detect_cost_fragility() -> None:
    payload = _build_payload(
        [
            _candidate_result(
                "candidate_cost",
                "SPY",
                cost_status="highly_sensitive",
                cost_fragile=True,
            )
        ]
    )

    review = _review_by_id(payload, "candidate_cost")
    assert review["anti_overfit_flags"]["cost_fragility_flag"] is True
    assert review["cost_sensitivity_summary"]["fragile_symbols"] == ["SPY"]


def test_anti_overfit_flags_detect_severe_return_degradation() -> None:
    payload = _build_payload(
        [
            _candidate_result(
                "candidate_degraded",
                "SPY",
                return_delta="-0.08",
                oos_window_delta="-0.25",
            )
        ]
    )

    review = _review_by_id(payload, "candidate_degraded")
    assert review["anti_overfit_flags"]["severe_return_degradation_flag"] is True
    assert review["final_review_classification"] == "reject_preview"


def test_candidate_cannot_become_paper_candidate_in_preview_review() -> None:
    with pytest.raises(ValidationError):
        validate_preview_review_classification("paper_candidate")


def test_offline_shadow_candidate_classification_works_on_controlled_fixture_data() -> None:
    payload = _build_payload(
        [
            _candidate_result("candidate_shadow", "SPY", return_delta="0.10"),
            _candidate_result("candidate_shadow", "QQQ", return_delta="0.09"),
        ]
    )

    review = _review_by_id(payload, "candidate_shadow")
    assert review["anti_overfit_flags"] == {
        "baseline_similarity_flag": False,
        "concentrated_edge_flag": False,
        "cost_fragility_flag": False,
        "high_churn_flag": False,
        "severe_return_degradation_flag": False,
        "single_symbol_edge_flag": False,
        "window_instability_flag": False,
    }
    assert review["final_review_classification"] == "offline_shadow_candidate"
    assert payload["overall_recommendation"] == "promote_to_offline_shadow_candidate"
    assert payload["offline_shadow_candidates"][0]["candidate_id"] == "candidate_shadow"


def test_overall_recommendation_reject_all_preview_only() -> None:
    payload = _build_payload(
        [
            _candidate_result(
                "candidate_reject",
                "SPY",
                return_delta="-0.10",
                oos_window_delta="-0.30",
            )
        ]
    )

    assert payload["overall_recommendation"] == "reject_all_preview_only"


def test_overall_recommendation_keep_researching_selected() -> None:
    payload = _build_payload(
        [
            _candidate_result(
                "candidate_keep",
                "SPY",
                cost_status="highly_sensitive",
                cost_fragile=True,
                transition_count=20,
            )
        ]
    )

    review = _review_by_id(payload, "candidate_keep")
    assert review["final_review_classification"] == "keep_researching"
    assert payload["overall_recommendation"] == "keep_researching_selected"


def test_overall_recommendation_promote_to_offline_shadow_candidate() -> None:
    payload = _build_payload(
        [
            _candidate_result("candidate_shadow", "SPY", return_delta="0.10"),
            _candidate_result("candidate_shadow", "QQQ", return_delta="0.09"),
        ]
    )

    assert payload["overall_recommendation"] == "promote_to_offline_shadow_candidate"
    assert payload["paper_candidate_count"] == 0
    assert {
        review["final_review_classification"]
        for review in payload["candidate_reviews"]
    } == {"offline_shadow_candidate"}


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


def test_preview_candidate_review_module_imports_no_broker_network_llm_or_runtime_dependencies() -> None:
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


def test_run_preview_candidate_review_script_contract_and_invocation(tmp_path: Path) -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    for fragment in (
        "Runs the deterministic offline preview-only candidate review",
        "does not",
        "mutate broker state",
        "contact the network",
        "Credential values are never printed",
        "runs\\strategy_challengers\\latest",
        "preflight_APP_PROFILE_is_paper",
        "preflight_RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled",
        "algotrader.research.preview_candidate_review",
    ):
        assert fragment in script

    output_root = tmp_path / "review out"
    input_root = tmp_path / "input with spaces"
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
            "-InputRoot",
            str(input_root),
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
    assert "-m algotrader.research.preview_candidate_review" in args
    assert "--input-root" in args
    assert str(input_root) in args
    assert "--output-root" in args
    assert str(output_root) in args


def test_run_preview_candidate_review_script_blocks_loaded_credentials(tmp_path: Path) -> None:
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


def _build_payload(results: list[dict[str, object]]) -> dict[str, object]:
    return build_preview_candidate_review_payload(_input_payload(results))


def _write_fixture_artifacts(root: Path, results: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = _challenger_results(results)
    (root / "challenger_results.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    (root / "promotion_recommendations.json").write_text(
        json.dumps(payload["promotion_recommendations"]),
        encoding="utf-8",
    )
    (root / "strategy_review_packet.json").write_text(
        json.dumps(
            {
                "record_type": "strategy_challenger_review_packet",
                "candidates": [
                    {
                        "candidate_id": result["candidate_id"],
                        "symbol": result["symbol"],
                        "operator_takeaway": "fixture takeaway",
                    }
                    for result in results
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "cross_asset_validation.json").write_text(
        json.dumps(
            {
                "cross_asset_validation": {
                    "candidate_rollups": _candidate_rollups(results),
                }
            }
        ),
        encoding="utf-8",
    )


def _input_payload(results: list[dict[str, object]]) -> dict[str, object]:
    challenger = _challenger_results(results)
    return {
        "challenger_results": challenger,
        "promotion_recommendations": challenger["promotion_recommendations"],
        "strategy_review_packet": {
            "candidates": [
                {
                    "candidate_id": result["candidate_id"],
                    "symbol": result["symbol"],
                    "operator_takeaway": "fixture takeaway",
                }
                for result in results
            ]
        },
        "cross_asset_validation": {"candidate_rollups": _candidate_rollups(results)},
    }


def _challenger_results(results: list[dict[str, object]]) -> dict[str, object]:
    preview_count = sum(
        1 for result in results if result["promotion_classification"] == "preview_only"
    )
    return {
        "record_type": "strategy_challenger_factory",
        "schema_version": "1",
        "factory_id": "fixture_strategy_challenger_factory",
        "run_id": "fixture_run",
        "labels": ["research_only", "offline_only", "not_live_authorized", "profit_claim=none"],
        "operating_baseline_symbol": "SPY",
        "symbols": sorted({str(result["symbol"]) for result in results}),
        "results": results,
        "promotion_recommendations": {
            "classification_recommendation": "preview_only_research_followup"
            if preview_count
            else "no_promotion",
            "preview_only_count": preview_count,
            "paper_candidate_count": 0,
        },
        "cross_asset_validation": {"candidate_rollups": _candidate_rollups(results)},
        "safety": {
            "broker_access_attempted": False,
            "broker_mutation_performed": False,
            "paper_submit_performed": False,
            "live_mutation_performed": False,
        },
    }


def _candidate_result(
    candidate_id: str,
    symbol: str,
    *,
    classification: str = "preview_only",
    oos_status: str = "passed",
    cost_status: str = "survived",
    return_delta: str = "0.10",
    drawdown_delta: str = "-0.01",
    sharpe_delta: str = "0.10",
    transition_count: int = 20,
    cost_fragile: bool = False,
    oos_window_delta: str | None = None,
) -> dict[str, object]:
    if oos_window_delta is None:
        oos_window_delta = return_delta
    oos_passed = oos_status == "passed"
    edge_broken = cost_status == "edge_broken" or cost_fragile
    highly_sensitive = cost_status == "highly_sensitive" or cost_fragile
    failed_window_count = 0 if oos_passed else 1
    passed_window_count = 2 if oos_passed else 1
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "role": "challenger",
        "metrics_status": "valid",
        "promotion_classification": classification,
        "promotion_reasons": ["fixture_preview_reason"]
        if classification == "preview_only"
        else [],
        "baseline_candidate_id": "spy_sma_50_200_baseline",
        "baseline_total_return_delta": return_delta,
        "baseline_max_drawdown_delta": drawdown_delta,
        "baseline_sharpe_ratio_delta": sharpe_delta,
        "benchmark_baseline_comparison": {
            "same_as_baseline": False,
        },
        "total_return": "0.20",
        "max_drawdown": "0.10",
        "transition_count": transition_count,
        "oos_status": oos_status,
        "out_of_sample_validation": {
            "validation_passed": oos_passed,
            "validation_failed": not oos_passed,
            "passed_window_count": passed_window_count,
            "failed_window_count": failed_window_count,
            "primary_window_passed": oos_passed,
            "primary_window_failed": not oos_passed,
            "window_results": [
                {
                    "window_id": "later_test",
                    "passed": oos_passed,
                    "failed": not oos_passed,
                    "total_return_delta": oos_window_delta,
                    "max_drawdown_delta": drawdown_delta,
                    "sharpe_ratio_delta": sharpe_delta,
                },
                {
                    "window_id": "walk_forward_1",
                    "passed": True,
                    "failed": False,
                    "total_return_delta": return_delta,
                    "max_drawdown_delta": drawdown_delta,
                    "sharpe_ratio_delta": sharpe_delta,
                },
            ],
        },
        "cost_sensitivity_status": cost_status,
        "cost_sensitivity_summary": {
            "edge_broken_by_moderate_cost": edge_broken,
            "returns_highly_cost_sensitive": highly_sensitive,
            "moderate_cost_return_degradation": "0.04" if cost_fragile else "0.005",
            "moderate_cost_edge_degradation": "0.02" if cost_fragile else "0.001",
            "zero_cost_baseline_total_return_delta": return_delta,
            "moderate_cost_baseline_total_return_delta": "-0.01"
            if edge_broken
            else return_delta,
        },
    }


def _candidate_rollups(results: list[dict[str, object]]) -> list[dict[str, object]]:
    rollups = []
    for candidate_id in sorted({str(result["candidate_id"]) for result in results}):
        candidate_results = [
            result for result in results if result["candidate_id"] == candidate_id
        ]
        rollups.append(
            {
                "candidate_id": candidate_id,
                "symbols_with_valid_metrics": sorted(
                    {str(result["symbol"]) for result in candidate_results}
                ),
                "oos_passed_symbols": sorted(
                    {
                        str(result["symbol"])
                        for result in candidate_results
                        if result["oos_status"] == "passed"
                    }
                ),
                "oos_failed_symbols": sorted(
                    {
                        str(result["symbol"])
                        for result in candidate_results
                        if result["oos_status"] == "failed"
                    }
                ),
                "cost_survived_symbols": sorted(
                    {
                        str(result["symbol"])
                        for result in candidate_results
                        if result["cost_sensitivity_status"] == "survived"
                    }
                ),
                "cost_broken_symbols": sorted(
                    {
                        str(result["symbol"])
                        for result in candidate_results
                        if result["cost_sensitivity_status"] != "survived"
                    }
                ),
                "paper_candidate_allowed": False,
                "paper_candidate_blockers": ["v2_15_review_forbids_paper_promotion"],
            }
        )
    return rollups


def _review_by_id(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    for review in payload["candidate_reviews"]:
        if review["candidate_id"] == candidate_id:
            return review
    raise AssertionError(candidate_id)


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo preview_candidate_review_status=completed\r\n"
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
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_preview_candidate_review.ps1")
    return powershell
