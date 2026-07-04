from __future__ import annotations

import ast
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.orchestration.crypto_qty_sizing_preview import (
    CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS,
    CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION,
    run_crypto_qty_sizing_preview,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path("src/algotrader/orchestration/crypto_qty_sizing_preview.py")
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_qty_sizing_preview.ps1"
AS_OF = datetime(2026, 7, 4, 0, 30, tzinfo=UTC)
SENSITIVE_KEY = "crypto-sizing-key-value-not-for-output"


def test_selected_crypto_candidate_produces_preview_ready_sizing(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path)

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
        preview_notional_cap="25",
    )
    preview = packet["sizing_preview"]

    assert preview["sizing_status"] == "preview_ready"
    assert preview["selected_candidate_id"] == (
        "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview"
    )
    assert preview["selected_symbol"] == "BTCUSD"
    assert preview["selected_strategy"] == "crypto_vol_adjusted_momentum_24h_preview"
    assert preview["selected_backing"] == "paper_read_only_artifact_backed"
    assert preview["orderability_status"] == "qty_orderable_notional_unobserved"
    assert preview["latest_price"] == "100000"
    assert preview["preview_notional_cap"] == "25"
    assert preview["raw_qty"] == "0.00025"
    assert preview["rounded_qty"] == "0.00025"
    assert preview["derived_preview_value"] == "25"
    assert preview["derived_min_order_value"] == "1"
    assert preview["blockers"] == []
    assert set(CRYPTO_QTY_SIZING_PREVIEW_REQUIRED_LABELS) <= set(preview["labels"])
    assert "real_paper_read_backed" in preview["labels"]
    assert "qty_orderable_notional_unobserved" in preview["labels"]

    artifact_paths = packet["artifact_paths"]
    assert (paths["output_root"] / "sizing_preview.json").is_file()
    assert (paths["output_root"] / "sizing_preview.md").is_file()
    assert (paths["output_root"] / "operating_record.jsonl").is_file()
    assert (paths["output_root"] / "manifest.json").is_file()
    written = json.loads(
        Path(artifact_paths["sizing_preview_json"]).read_text(encoding="utf-8")
    )
    brief = Path(artifact_paths["sizing_preview_md"]).read_text(encoding="utf-8")
    assert written["paper_submit_authorized"] is False
    assert "no-submit preview only" in brief
    assert "not a guarantee of broker acceptance" in brief


def test_no_trade_router_decision_blocks_sizing(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path, decision="no_trade")

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )
    preview = packet["sizing_preview"]

    assert preview["sizing_status"] == "blocked"
    assert preview["selected_candidate_id"] == ""
    assert preview["blockers"] == [
        "router_decision_no_trade",
        "missing_selected_candidate",
    ]


def test_fixture_backed_candidate_blocks_outside_fixture_mode(tmp_path: Path) -> None:
    paths = _write_preview_inputs(
        tmp_path,
        source_mode="offline_fixture",
        backing="fixture_backed",
    )

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )

    assert packet["sizing_preview"]["sizing_status"] == "blocked"
    assert "fixture_backed_candidate" in packet["sizing_preview"]["blockers"]


def test_stale_candidate_blocks_sizing(tmp_path: Path) -> None:
    paths = _write_preview_inputs(
        tmp_path,
        candidate_updates={"freshness_status": "stale_data"},
        history_updates={"freshness_status": "stale_data"},
    )

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )

    assert packet["sizing_preview"]["sizing_status"] == "blocked"
    assert "stale_candidate" in packet["sizing_preview"]["blockers"]


def test_missing_latest_price_blocks_sizing(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path, latest_price="")

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )

    assert packet["sizing_preview"]["sizing_status"] == "blocked"
    assert "missing_latest_price" in packet["sizing_preview"]["blockers"]


def test_missing_min_order_size_blocks_sizing(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path, min_order_size="")

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )

    assert packet["sizing_preview"]["sizing_status"] == "blocked"
    assert "missing_min_order_size" in packet["sizing_preview"]["blockers"]


def test_missing_min_trade_increment_blocks_sizing(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path, min_trade_increment="")

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )

    assert packet["sizing_preview"]["sizing_status"] == "blocked"
    assert "missing_min_trade_increment" in packet["sizing_preview"]["blockers"]


def test_qty_rounds_down_to_min_trade_increment(tmp_path: Path) -> None:
    paths = _write_preview_inputs(
        tmp_path,
        latest_price="3",
        min_order_size="0.1",
        min_trade_increment="0.1",
    )

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
        preview_notional_cap="10",
    )
    preview = packet["sizing_preview"]

    assert preview["sizing_status"] == "preview_ready"
    assert preview["raw_qty"] == "3.333333333333333333333333333"
    assert preview["rounded_qty"] == "3.3"
    assert preview["derived_preview_value"] == "9.9"


def test_rounded_qty_below_min_order_size_blocks(tmp_path: Path) -> None:
    paths = _write_preview_inputs(
        tmp_path,
        latest_price="100000",
        min_order_size="0.00002",
        min_trade_increment="0.000001",
    )

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
        preview_notional_cap="1",
    )

    assert packet["sizing_preview"]["sizing_status"] == "blocked"
    assert packet["sizing_preview"]["rounded_qty"] == "0.00001"
    assert "below_min_order_size" in packet["sizing_preview"]["blockers"]


def test_qty_orderable_notional_unobserved_preserves_missing_broker_min_notional(
    tmp_path: Path,
) -> None:
    paths = _write_preview_inputs(tmp_path, min_notional="")

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )
    preview = packet["sizing_preview"]

    assert preview["orderability_status"] == "qty_orderable_notional_unobserved"
    assert preview["broker_observed_min_notional"] == ""
    assert "qty_orderable_notional_unobserved" in preview["labels"]


def test_derived_min_order_value_is_derived_not_broker_observed(
    tmp_path: Path,
) -> None:
    paths = _write_preview_inputs(
        tmp_path,
        latest_price="63000",
        min_order_size="0.000016026",
        min_notional="",
    )

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )
    preview = packet["sizing_preview"]

    assert preview["broker_observed_min_notional"] == ""
    assert preview["derived_min_order_value"] == "1.009638"


def test_required_no_submit_no_mutation_live_flags_are_false(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path)

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )
    preview = packet["sizing_preview"]
    manifest = json.loads((paths["output_root"] / "manifest.json").read_text("utf-8"))

    for payload in (preview, packet["safety"], manifest):
        assert payload["paper_submit_authorized"] is False
        assert payload["paper_submit_performed"] is False
        assert payload["broker_mutation_performed"] is False
        assert payload["live_mutation_performed"] is False
    assert preview["profit_claim"] == "none"
    assert manifest["profit_claim"] == "none"


def test_manifest_integrity(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path)

    packet = run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )
    manifest_path = Path(packet["artifact_paths"]["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == CRYPTO_QTY_SIZING_PREVIEW_SCHEMA_VERSION
    assert set(manifest["required_artifacts"]) == {
        "operating_record",
        "sizing_preview_json",
        "sizing_preview_md",
    }
    for artifact in manifest["required_artifacts"].values():
        assert Path(artifact["path"]).is_file()
        assert artifact["sha256"]
    assert set(manifest["input_artifacts"]) == {
        "crypto_history_manifest",
        "crypto_orderability_metadata",
        "crypto_router_input_manifest",
        "opportunity_candidates",
        "router_decision",
    }


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    paths = _write_preview_inputs(tmp_path)

    run_crypto_qty_sizing_preview(
        router_decision_path=paths["router_decision"],
        opportunity_candidates_path=paths["opportunity_candidates"],
        crypto_router_input_manifest_path=paths["crypto_router_input_manifest"],
        output_root=paths["output_root"],
    )
    manifest = json.loads((paths["output_root"] / "manifest.json").read_text("utf-8"))
    git_result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert manifest["generated_under_runs"] is True
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert git_result.returncode == 0, git_result.stderr
    assert git_result.stdout.strip() == ""


def test_normal_pytest_path_remains_offline_broker_free_network_free() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden_prefixes = (
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "algotrader.execution",
        "algotrader.broker",
        "algotrader.brokers",
        "algotrader.runtime",
    )
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported_modules
        for prefix in forbidden_prefixes
    )
    assert call_names.isdisjoint(
        {"submit_order", "create_order", "request", "urlopen"}
    )


def test_run_crypto_qty_sizing_preview_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the deterministic crypto qty sizing preview in no-submit mode",
        '[string]$OutputRoot = "runs\\crypto_qty_sizing_preview\\latest"',
        '[string]$RouterDecision = "runs\\opportunity_router\\paper_read_repair_latest\\router_decision.json"',
        "crypto_qty_sizing_preview_mode=offline/no_submit",
        "crypto_qty_sizing_preview_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "crypto_qty_sizing_preview_paper_submit_authorized=false",
        "crypto_qty_sizing_preview_paper_submit_performed=false",
        "crypto_qty_sizing_preview_broker_mutation_performed=false",
        "crypto_qty_sizing_preview_live_mutation_performed=false",
        "algotrader.orchestration.crypto_qty_sizing_preview",
        "--router-decision",
        "--opportunity-candidates",
        "--crypto-router-input-manifest",
        "--preview-notional-cap",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "--submit" not in script
    assert "paper_submit_authorized=true" not in script


def test_run_crypto_qty_sizing_preview_script_invokes_offline_module(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-OutputRoot",
            str(tmp_path / "preview latest"),
            "-RouterDecision",
            str(tmp_path / "router_decision.json"),
            "-OpportunityCandidates",
            str(tmp_path / "opportunity_candidates.json"),
            "-CryptoRouterInputManifest",
            str(tmp_path / "crypto_router_input_manifest.json"),
            "-PreviewNotionalCap",
            "12.50",
            "-AllowFixtureBacked",
            "-Format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "crypto_qty_sizing_preview_no_submit_enforced=true" in result.stdout
    assert "preflight_credential_variables_loaded=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.orchestration.crypto_qty_sizing_preview" in args
    assert "--output-root" in args
    assert "--router-decision" in args
    assert "--opportunity-candidates" in args
    assert "--crypto-router-input-manifest" in args
    assert "--preview-notional-cap 12.50" in args
    assert "--allow-fixture-backed" in args
    assert "--format json" in args
    assert "--submit" not in args


def test_run_crypto_qty_sizing_preview_script_blocks_loaded_credentials(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["ALPACA_API_KEY"] = SENSITIVE_KEY

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "preflight_credential_variables_loaded=true" in result.stdout
    assert "crypto_qty_sizing_preview_status=blocked_unsafe_environment" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def _write_preview_inputs(
    tmp_path: Path,
    *,
    decision: str = "selected",
    source_mode: str = "paper_read_only",
    backing: str = "paper_read_only_artifact_backed",
    latest_price: str = "100000",
    min_order_size: str = "0.00001",
    min_trade_increment: str = "0.00000001",
    min_notional: str = "",
    orderability_status: str = "qty_orderable_notional_unobserved",
    candidate_updates: Mapping[str, object] | None = None,
    metadata_updates: Mapping[str, object] | None = None,
    history_updates: Mapping[str, object] | None = None,
) -> dict[str, Path]:
    router_root = tmp_path / "runs" / "opportunity_router" / "paper_read_repair_latest"
    refresh_root = (
        tmp_path / "runs" / "crypto_universe_refresh" / "paper_read_repair_latest"
    )
    output_root = tmp_path / "runs" / "crypto_qty_sizing_preview" / "latest"
    history_root = refresh_root / "history"
    router_root.mkdir(parents=True)
    refresh_root.mkdir(parents=True)
    history_root.mkdir(parents=True)

    symbol = "BTCUSD"
    candidate_id = f"crypto:{symbol}:crypto_vol_adjusted_momentum_24h_preview"
    candidate = {
        "candidate_id": candidate_id,
        "as_of": AS_OF.isoformat(),
        "asset_class": "crypto",
        "symbol": symbol,
        "venue": "alpaca_crypto",
        "source": source_mode,
        "strategy_id": "crypto_vol_adjusted_momentum_24h_preview",
        "strategy_family": "crypto_volatility_adjusted_momentum_preview",
        "signal_direction": "long",
        "signal_status": "trade_candidate",
        "evidence_tier": "paper_read_backed_preview",
        "data_quality_status": "valid",
        "history_status": "sufficient_history",
        "freshness_status": "fresh",
        "broker_state_mode": "alpaca_paper_observed",
        "orderability_status": orderability_status,
        "blocker_status": "eligible",
        "blockers": [],
        "risk_notes": ["tiny_notional_preview_only"],
        "score_components": {"orderability": "5"},
        "router_score": "5",
        "labels": [
            "paper_lab_only",
            "signal_evaluation_only",
            "not_live_authorized",
            "profit_claim=none",
            "no_submit_mode",
            "paper_read_only" if source_mode == "paper_read_only" else backing,
        ],
        "profit_claim": "none",
        "candidate_backing": backing,
    }
    if candidate_updates:
        candidate.update(candidate_updates)

    selected_candidate = candidate if decision == "selected" else None
    router_decision = {
        "schema_version": "test_opportunity_router",
        "as_of": AS_OF.isoformat(),
        "decision": decision,
        "selected_candidate_id": candidate_id if decision == "selected" else None,
        "selected_candidate": selected_candidate,
        "selected_symbol": symbol if decision == "selected" else "",
        "selected_asset_class": "crypto" if decision == "selected" else "",
        "selected_strategy_id": candidate["strategy_id"] if decision == "selected" else "",
        "selected_candidate_backing": backing if decision == "selected" else "",
        "selected_router_score": "5" if decision == "selected" else "",
        "selection_reason": (
            "highest_ranked_eligible_candidate"
            if decision == "selected"
            else "no_trade_all_candidates_blocked"
        ),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "profit_claim": "none",
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }
    opportunity_candidates = {
        "schema_version": "test_opportunity_candidates",
        "as_of": AS_OF.isoformat(),
        "candidates": [candidate],
    }

    history_csv = history_root / f"{symbol}.csv"
    if latest_price:
        history_csv.write_text(
            "\n".join(
                [
                    "timestamp,symbol,asset_class,open,high,low,close,volume",
                    f"{AS_OF.isoformat()},{symbol},crypto,{latest_price},{latest_price},{latest_price},{latest_price},1000",
                ]
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

    metadata = {
        "symbol": symbol,
        "asset_class": "crypto",
        "source_mode": source_mode,
        "broker_state_mode": "alpaca_paper_observed",
        "tradable": True,
        "status": "active",
        "min_notional": min_notional,
        "min_order_notional": min_notional,
        "min_order_size": min_order_size,
        "min_trade_increment": min_trade_increment,
        "price_increment": "0.01",
        "qty_increment": min_trade_increment,
        "broker_observed_min_notional": min_notional,
        "broker_observed_min_order_size": min_order_size,
        "broker_observed_min_trade_increment": min_trade_increment,
        "broker_observed_price_increment": "0.01",
        "derived_min_order_value": "",
        "metadata_status": "metadata_observed",
        "metadata_blockers": [],
        "orderability_status": orderability_status,
        "orderability_blockers": [],
        "orderability_basis": "broker_qty_metadata_notional_unobserved",
    }
    if metadata_updates:
        metadata.update(metadata_updates)
    orderability_metadata = {
        "schema_version": "test_crypto_universe_refresh",
        "as_of": AS_OF.isoformat(),
        "asset_class": "crypto",
        "records": [metadata],
    }

    history_record = {
        "symbol": symbol,
        "asset_class": "crypto",
        "data_path": str(Path("history") / f"{symbol}.csv"),
        "source_mode": source_mode,
        "bar_count": 80,
        "usable_bar_count": 80,
        "required_bar_count": 50,
        "latest_timestamp": AS_OF.isoformat() if latest_price else "",
        "data_quality_status": "valid" if latest_price else "missing_data",
        "history_status": "sufficient_history" if latest_price else "missing_history",
        "freshness_status": "fresh" if latest_price else "missing_data",
        "blockers": [] if latest_price else ["missing_data"],
    }
    if history_updates:
        history_record.update(history_updates)
    history_manifest = {
        "schema_version": "test_crypto_universe_refresh",
        "as_of": AS_OF.isoformat(),
        "asset_class": "crypto",
        "records": [history_record],
    }

    router_input_manifest = {
        "schema_version": "test_crypto_universe_refresh",
        "as_of": AS_OF.isoformat(),
        "asset_class": "crypto",
        "mode": source_mode,
        "source_mode": source_mode,
        "source_path": "unit_test_fixture",
        "broker_state_mode": "alpaca_paper_observed",
        "broker_read_observed": source_mode == "paper_read_only",
        "symbols": [symbol],
        "router_ready_symbols": [symbol],
        "crypto_orderability_metadata_path": "crypto_orderability_metadata.json",
        "crypto_history_manifest_path": "crypto_history_manifest.json",
        "records": [
            {
                "symbol": symbol,
                "asset_class": "crypto",
                "source_mode": source_mode,
                "input_backing": backing,
                "broker_state_mode": "alpaca_paper_observed",
                "metadata_status": metadata["metadata_status"],
                "orderability_status": metadata["orderability_status"],
                "history_status": history_record["history_status"],
                "freshness_status": history_record["freshness_status"],
                "data_quality_status": history_record["data_quality_status"],
                "data_path": history_record["data_path"],
                "blockers": [],
            }
        ],
        "labels": [backing],
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
    }

    _write_json(router_root / "router_decision.json", router_decision)
    _write_json(router_root / "opportunity_candidates.json", opportunity_candidates)
    _write_json(refresh_root / "crypto_router_input_manifest.json", router_input_manifest)
    _write_json(refresh_root / "crypto_orderability_metadata.json", orderability_metadata)
    _write_json(refresh_root / "crypto_history_manifest.json", history_manifest)

    return {
        "router_decision": router_root / "router_decision.json",
        "opportunity_candidates": router_root / "opportunity_candidates.json",
        "crypto_router_input_manifest": refresh_root
        / "crypto_router_input_manifest.json",
        "output_root": output_root,
    }


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
        "echo {\"sizing_status\":\"preview_ready\",\"paper_submit_performed\":false}\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    env["APP_PROFILE"] = "dev"
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_crypto_qty_sizing_preview.ps1")
    return powershell
