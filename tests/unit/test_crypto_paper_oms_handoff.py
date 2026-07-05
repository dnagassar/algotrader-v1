from __future__ import annotations

import ast
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.orchestration.crypto_paper_oms_handoff import (
    CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_FALSE_FLAGS,
    CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS,
    CRYPTO_PAPER_OMS_HANDOFF_SCHEMA_VERSION,
    run_crypto_paper_oms_handoff,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path("src/algotrader/orchestration/crypto_paper_oms_handoff.py")
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_paper_oms_handoff.ps1"
AS_OF = datetime(2026, 7, 4, 0, 30, tzinfo=UTC)
SENSITIVE_KEY = "crypto-handoff-key-value-not-for-output"


def test_valid_v54_sizing_preview_produces_approval_required_handoff(
    tmp_path: Path,
) -> None:
    paths = _write_sizing_preview(tmp_path)

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "approval_required"
    assert packet["approval_state"] == "not_authorized"
    assert packet["intended_action"] == "buy_preview"
    assert packet["asset_class"] == "crypto"
    assert packet["symbol"] == "BTCUSD"
    assert packet["strategy_id"] == "crypto_vol_adjusted_momentum_24h_preview"
    assert packet["selected_candidate_id"] == (
        "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview"
    )
    assert packet["selected_backing"] == "real_local_artifact_backed"
    assert packet["orderability_status"] == "qty_orderable_notional_unobserved"
    assert packet["latest_price"] == "63006.709"
    assert packet["preview_notional_cap"] == "25"
    assert packet["rounded_qty"] == "0.000396783"
    assert packet["derived_preview_value"] == "24.999991017147"
    assert packet["max_preview_value"] == "25"
    assert packet["blockers"] == []
    assert set(CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_LABELS) <= set(packet["labels"])
    assert "real_local_artifact_backed" in packet["labels"]

    written = json.loads(
        (paths["output_root"] / "paper_oms_handoff.json").read_text("utf-8")
    )
    brief = (paths["output_root"] / "paper_oms_handoff.md").read_text("utf-8")
    assert written["paper_submit_authorized"] is False
    assert written["execution_plan"]["submit_allowed"] is False
    assert "does not submit or authorize submission" in brief
    assert "exact next operator action" in brief


def test_blocked_sizing_preview_produces_blocked_handoff(tmp_path: Path) -> None:
    paths = _write_sizing_preview(
        tmp_path,
        updates={"sizing_status": "blocked", "blockers": ["missing_latest_price"]},
    )

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert packet["intended_action"] == "no_action"
    assert "upstream_sizing_blocked" in packet["blockers"]
    assert "missing_latest_price" in packet["blockers"]


def test_no_trade_or_router_missing_input_blocks_handoff(tmp_path: Path) -> None:
    paths = _write_sizing_preview(
        tmp_path,
        updates={
            "router_decision": "no_trade",
            "selected_candidate_id": "",
            "selected_symbol": "",
        },
    )

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "router_decision_no_trade" in packet["blockers"]
    assert "missing_selected_candidate" in packet["blockers"]


def test_fixture_backed_candidate_blocks_outside_fixture_mode(tmp_path: Path) -> None:
    paths = _write_sizing_preview(
        tmp_path,
        updates={
            "selected_backing": "fixture_backed",
            "labels": _labels(backing="fixture_backed"),
        },
    )

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "fixture_backed_candidate" in packet["blockers"]


def test_missing_rounded_qty_blocks_handoff(tmp_path: Path) -> None:
    paths = _write_sizing_preview(tmp_path, updates={"rounded_qty": ""})

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "missing_or_invalid_rounded_qty" in packet["blockers"]


def test_derived_preview_value_above_cap_blocks_handoff(tmp_path: Path) -> None:
    paths = _write_sizing_preview(
        tmp_path,
        updates={"derived_preview_value": "25.01"},
    )

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "derived_preview_value_exceeds_cap" in packet["blockers"]


def test_missing_required_safety_labels_blocks_handoff(tmp_path: Path) -> None:
    labels = [label for label in _labels() if label != "no_submit_mode"]
    paths = _write_sizing_preview(tmp_path, updates={"labels": labels})

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "missing_required_safety_labels" in packet["blockers"]
    assert "no_submit_mode" in packet["missing_required_labels"]


def test_true_paper_submit_authorized_blocks_handoff(tmp_path: Path) -> None:
    paths = _write_sizing_preview(tmp_path, updates={"paper_submit_authorized": True})

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "paper_submit_authorized_true" in packet["blockers"]


def test_true_broker_mutation_performed_blocks_handoff(tmp_path: Path) -> None:
    paths = _write_sizing_preview(
        tmp_path,
        updates={"broker_mutation_performed": True},
    )

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "broker_mutation_performed_true" in packet["blockers"]


def test_true_live_mutation_performed_blocks_handoff(tmp_path: Path) -> None:
    paths = _write_sizing_preview(tmp_path, updates={"live_mutation_performed": True})

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )

    assert packet["handoff_status"] == "blocked"
    assert "live_mutation_performed_true" in packet["blockers"]


def test_required_no_submit_no_mutation_live_flags_remain_false(
    tmp_path: Path,
) -> None:
    paths = _write_sizing_preview(tmp_path)

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )
    manifest = json.loads((paths["output_root"] / "manifest.json").read_text("utf-8"))

    payloads = (packet, packet["execution_intent"], packet["execution_plan"], manifest)
    for payload in payloads:
        for field_name in CRYPTO_PAPER_OMS_HANDOFF_REQUIRED_FALSE_FLAGS:
            assert payload[field_name] is False
    assert packet["broker_read_performed_current_run"] is False
    assert packet["network_access_attempted"] is False
    assert packet["live_endpoint_touched"] is False
    assert packet["profit_claim"] == "none"
    assert manifest["profit_claim"] == "none"


def test_manifest_integrity(tmp_path: Path) -> None:
    paths = _write_sizing_preview(tmp_path)

    packet = run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
        output_root=paths["output_root"],
    )
    manifest_path = Path(packet["artifact_paths"]["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == CRYPTO_PAPER_OMS_HANDOFF_SCHEMA_VERSION
    assert set(manifest["required_artifacts"]) == {
        "operating_record",
        "paper_oms_handoff_json",
        "paper_oms_handoff_md",
    }
    for artifact in manifest["required_artifacts"].values():
        assert Path(artifact["path"]).is_file()
        assert artifact["sha256"]
        assert artifact["size"] > 0
    assert set(manifest["input_artifacts"]) == {"sizing_preview"}
    assert manifest["input_artifacts"]["sizing_preview"]["sha256"]


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    paths = _write_sizing_preview(tmp_path)

    run_crypto_paper_oms_handoff(
        sizing_preview_path=paths["sizing_preview"],
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
        {
            "cancel_order",
            "close_position",
            "create_order",
            "liquidate",
            "replace_order",
            "request",
            "submit_order",
            "urlopen",
        }
    )


def test_run_crypto_paper_oms_handoff_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the crypto Paper OMS approval handoff in no-submit mode",
        '[string]$OutputRoot = "runs\\crypto_paper_oms_handoff\\latest"',
        '[string]$SizingPreview = "runs\\crypto_qty_sizing_preview\\latest\\sizing_preview.json"',
        "crypto_paper_oms_handoff_mode=offline/no_submit",
        "crypto_paper_oms_handoff_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_APP_PROFILE_is_live",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "crypto_paper_oms_handoff_paper_submit_authorized=false",
        "crypto_paper_oms_handoff_paper_submit_performed=false",
        "crypto_paper_oms_handoff_broker_mutation_performed=false",
        "crypto_paper_oms_handoff_live_mutation_performed=false",
        "algotrader.orchestration.crypto_paper_oms_handoff",
        "--sizing-preview",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "--submit" not in script
    assert "paper_submit_authorized=true" not in script


def test_run_crypto_paper_oms_handoff_script_invokes_offline_module(
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
            str(tmp_path / "handoff latest"),
            "-SizingPreview",
            str(tmp_path / "sizing_preview.json"),
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
    assert "crypto_paper_oms_handoff_no_submit_enforced=true" in result.stdout
    assert "preflight_credential_variables_loaded=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.orchestration.crypto_paper_oms_handoff" in args
    assert "--output-root" in args
    assert "--sizing-preview" in args
    assert "--allow-fixture-backed" in args
    assert "--format json" in args
    assert "--submit" not in args


def test_run_crypto_paper_oms_handoff_script_blocks_loaded_credentials(
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
    assert "crypto_paper_oms_handoff_status=blocked_unsafe_environment" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def _write_sizing_preview(
    tmp_path: Path,
    *,
    updates: dict[str, object] | None = None,
) -> dict[str, Path]:
    root = tmp_path / "runs" / "crypto_qty_sizing_preview" / "latest"
    output_root = tmp_path / "runs" / "crypto_paper_oms_handoff" / "latest"
    root.mkdir(parents=True)
    sizing_preview = _sizing_preview()
    if updates:
        sizing_preview.update(updates)
    _write_json(root / "sizing_preview.json", sizing_preview)
    return {
        "sizing_preview": root / "sizing_preview.json",
        "output_root": output_root,
    }


def _sizing_preview() -> dict[str, object]:
    symbol = "BTCUSD"
    return {
        "schema_version": "v5_4_crypto_qty_sizing_preview_v1",
        "as_of": AS_OF.isoformat(),
        "router_decision_source": (
            "runs/opportunity_router/paper_read_repair_latest/router_decision.json"
        ),
        "selected_candidate_id": (
            f"crypto:{symbol}:crypto_vol_adjusted_momentum_24h_preview"
        ),
        "selected_symbol": symbol,
        "selected_strategy": "crypto_vol_adjusted_momentum_24h_preview",
        "selected_backing": "real_local_artifact_backed",
        "orderability_status": "qty_orderable_notional_unobserved",
        "orderability_basis": "broker_qty_metadata_notional_unobserved",
        "broker_observed_min_notional": "",
        "broker_observed_min_order_size": "0.00001",
        "broker_observed_min_trade_increment": "0.000000001",
        "broker_observed_price_increment": "0.01",
        "latest_price": "63006.709",
        "preview_notional_cap": "25",
        "raw_qty": "0.0003967831425697857032970885688",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "derived_min_order_value": "0.63006709",
        "sizing_status": "preview_ready",
        "blockers": [],
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "profit_claim": "none",
        "labels": _labels(),
        "selection_reason": "highest_ranked_eligible_candidate",
        "router_decision": "selected",
        "paper_submit_performed_current_run": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "live_endpoint_touched": False,
        "next_operator_action": (
            "operator_review_sizing_preview_before_any_paper_submit_authorization"
        ),
    }


def _labels(*, backing: str = "real_local_artifact_backed") -> list[str]:
    return [
        "paper_lab_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "sizing_preview_only",
        backing,
    ]


def _write_json(path: Path, payload: dict[str, object]) -> None:
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
        "echo {\"handoff_status\":\"approval_required\",\"paper_submit_performed\":false}\r\n"
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
        pytest.skip("PowerShell is required to verify run_crypto_paper_oms_handoff.ps1")
    return powershell
