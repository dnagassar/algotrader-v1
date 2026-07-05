from __future__ import annotations

import ast
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.orchestration.crypto_paper_submit_approval_packet import (
    CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_FALSE_FLAGS,
    CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_LABELS,
    CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUESTED_SCOPE,
    CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION,
    run_crypto_paper_submit_approval_packet,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(
    "src/algotrader/orchestration/crypto_paper_submit_approval_packet.py"
)
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_paper_submit_approval_packet.ps1"
AS_OF = datetime(2026, 7, 4, 18, 30, 45, 237580, tzinfo=UTC)
SENSITIVE_KEY = "crypto-approval-packet-key-value-not-for-output"


def test_valid_v56_dry_run_produces_ready_for_operator_review_packet(
    tmp_path: Path,
) -> None:
    paths = _write_dry_run(tmp_path)

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
    )

    assert packet["approval_packet_status"] == "ready_for_operator_review"
    assert packet["approval_state"] == "not_authorized"
    assert packet["source_approval_state"] == "not_authorized"
    assert packet["broker_action_permitted"] is False
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["requested_future_authorization_scope"] == (
        CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUESTED_SCOPE
    )
    assert packet["selected_candidate_id"] == (
        "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview"
    )
    assert packet["symbol"] == "BTCUSD"
    assert packet["asset_class"] == "crypto"
    assert packet["intended_action"] == "buy_preview"
    assert packet["rounded_qty"] == "0.000396783"
    assert packet["derived_preview_value"] == "24.999991017147"
    assert packet["preview_cap"] == "25"
    assert packet["dry_run_id"] == "dryrun_19bfe1c5645e29869a393564"
    assert packet["pre_broker_order_id"] == "prebroker_a22db5ec89a3d81457712c6b"
    assert packet["idempotency_key"] == (
        "crypto_paper_oms_dry_run:"
        "19bfe1c5645e29869a393564a22db5ec89a3d81457712c6b89e9137fa9f3ddeb"
    )
    assert packet["blockers"] == []
    assert set(CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_LABELS) <= set(
        packet["labels"]
    )
    assert "real_local_artifact_backed" in packet["labels"]
    assert packet["profit_claim"] == "none"

    written = json.loads(
        (paths["output_root"] / "paper_submit_approval_packet.json").read_text(
            encoding="utf-8"
        )
    )
    brief = (
        paths["output_root"] / "paper_submit_approval_packet.md"
    ).read_text(encoding="utf-8")
    assert written["schema_version"] == (
        CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION
    )
    assert written["approval_packet_status"] == "ready_for_operator_review"
    assert "No paper submit is authorized by this packet" in brief
    assert "Authorized for v5.8" in brief


def test_invalid_dry_run_blocks_approval_packet(tmp_path: Path) -> None:
    paths = _write_dry_run(
        tmp_path,
        updates={"dry_run_status": "blocked_invalid_handoff"},
    )

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
    )

    assert packet["approval_packet_status"] == "blocked"
    assert "dry_run_status_not_blocked_not_authorized" in packet["blockers"]
    assert packet["approval_state"] == "not_authorized"
    assert packet["paper_submit_authorized"] is False


@pytest.mark.parametrize(
    ("field_name", "expected_blocker"),
    (
        ("dry_run_id", "missing_dry_run_id"),
        ("pre_broker_order_id", "missing_pre_broker_order_id"),
        ("idempotency_key", "missing_idempotency_key"),
    ),
)
def test_missing_identity_fields_block_packet(
    tmp_path: Path,
    field_name: str,
    expected_blocker: str,
) -> None:
    paths = _write_dry_run(tmp_path, updates={field_name: ""})

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
    )

    assert packet["approval_packet_status"] == "blocked"
    assert expected_blocker in packet["blockers"]
    assert packet["paper_submit_authorized"] is False


@pytest.mark.parametrize(
    ("field_name", "expected_blocker"),
    (
        ("broker_action_permitted", "broker_action_permitted_true"),
        ("paper_submit_authorized", "paper_submit_authorized_true"),
        ("paper_submit_performed", "paper_submit_performed_true"),
        ("broker_mutation_performed", "broker_mutation_performed_true"),
        ("live_mutation_performed", "live_mutation_performed_true"),
        ("live_endpoint_touched", "live_endpoint_touched_true"),
    ),
)
def test_true_submit_mutation_or_live_flags_block_packet(
    tmp_path: Path,
    field_name: str,
    expected_blocker: str,
) -> None:
    paths = _write_dry_run(tmp_path, updates={field_name: True})

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
    )

    assert packet["approval_packet_status"] == "blocked"
    assert expected_blocker in packet["blockers"]
    assert packet["broker_action_permitted"] is False
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["live_mutation_performed"] is False


def test_missing_required_labels_blocks_packet(tmp_path: Path) -> None:
    labels = [label for label in _labels() if label != "no_submit_mode"]
    paths = _write_dry_run(tmp_path, updates={"labels": labels})

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
    )

    assert packet["approval_packet_status"] == "blocked"
    assert "missing_required_safety_labels" in packet["blockers"]
    assert "no_submit_mode" in packet["missing_required_labels"]
    assert "paper_submit_approval_packet_only" in packet["labels"]


def test_required_operator_phrase_includes_identity_qty_and_cap(
    tmp_path: Path,
) -> None:
    paths = _write_dry_run(tmp_path)

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
        write_artifacts=False,
    )

    phrase = str(packet["required_operator_phrase"])
    assert str(packet["dry_run_id"]) in phrase
    assert str(packet["pre_broker_order_id"]) in phrase
    assert str(packet["rounded_qty"]) in phrase
    assert str(packet["preview_cap"]) in phrase
    assert str(packet["symbol"]) in phrase
    assert "exactly one paper order submit attempt" in phrase
    assert "does not authorize live trading" in phrase


def test_generated_packet_does_not_authorize_submit(tmp_path: Path) -> None:
    paths = _write_dry_run(tmp_path)

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
    )
    manifest = json.loads((paths["output_root"] / "manifest.json").read_text("utf-8"))
    operating_record = json.loads(
        (paths["output_root"] / "operating_record.jsonl").read_text("utf-8")
    )

    payloads = (packet, manifest, operating_record)
    for payload in payloads:
        assert payload["approval_state"] == "not_authorized"
        assert payload["broker_action_permitted"] is False
        for field_name in CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_REQUIRED_FALSE_FLAGS:
            assert payload[field_name] is False
    assert packet["paper_cancel_authorized"] is False
    assert packet["paper_cancel_performed"] is False
    assert packet["broker_read_performed_current_run"] is False
    assert packet["network_access_attempted"] is False
    assert packet["profit_claim"] == "none"
    assert "current_paper_submit" in packet["disallowed_actions"]


def test_manifest_integrity(tmp_path: Path) -> None:
    paths = _write_dry_run(tmp_path)

    packet = run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
        output_root=paths["output_root"],
    )
    manifest_path = Path(packet["artifact_paths"]["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == (
        CRYPTO_PAPER_SUBMIT_APPROVAL_PACKET_SCHEMA_VERSION
    )
    assert set(manifest["required_artifacts"]) == {
        "operating_record",
        "paper_submit_approval_packet_json",
        "paper_submit_approval_packet_md",
    }
    for artifact in manifest["required_artifacts"].values():
        assert Path(artifact["path"]).is_file()
        assert artifact["sha256"]
        assert artifact["size"] > 0
    assert set(manifest["input_artifacts"]) == {"paper_oms_dry_run"}
    assert manifest["input_artifacts"]["paper_oms_dry_run"]["sha256"]
    assert manifest["manifest"]["path"].endswith("manifest.json")


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    paths = _write_dry_run(tmp_path)

    run_crypto_paper_submit_approval_packet(
        dry_run_path=paths["dry_run"],
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


def test_run_crypto_paper_submit_approval_packet_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Builds the crypto paper-submit approval packet in no-submit mode",
        '[string]$OutputRoot = "runs\\crypto_paper_submit_approval_packet\\latest"',
        '[string]$DryRunPath = "runs\\crypto_paper_oms_dry_run\\latest\\paper_oms_dry_run.json"',
        "crypto_paper_submit_approval_packet_mode=offline/no_submit_operator_review",
        "crypto_paper_submit_approval_packet_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_APP_PROFILE_is_live",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "crypto_paper_submit_approval_packet_paper_submit_authorized=false",
        "crypto_paper_submit_approval_packet_paper_submit_performed=false",
        "crypto_paper_submit_approval_packet_broker_mutation_performed=false",
        "crypto_paper_submit_approval_packet_live_mutation_performed=false",
        "algotrader.orchestration.crypto_paper_submit_approval_packet",
        "--dry-run-path",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "--submit" not in script
    assert "paper_submit_authorized=true" not in script


def test_run_crypto_paper_submit_approval_packet_script_invokes_offline_module(
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
            str(tmp_path / "approval packet latest"),
            "-DryRunPath",
            str(tmp_path / "paper_oms_dry_run.json"),
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
    assert (
        "crypto_paper_submit_approval_packet_no_submit_enforced=true"
        in result.stdout
    )
    assert "preflight_credential_variables_loaded=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.orchestration.crypto_paper_submit_approval_packet" in args
    assert "--output-root" in args
    assert "--dry-run-path" in args
    assert "--format json" in args
    assert "--submit" not in args


def test_run_crypto_paper_submit_approval_packet_script_blocks_loaded_credentials(
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
    assert (
        "crypto_paper_submit_approval_packet_status=blocked_unsafe_environment"
        in result.stdout
    )
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def _write_dry_run(
    tmp_path: Path,
    *,
    updates: dict[str, object] | None = None,
) -> dict[str, Path]:
    root = tmp_path / "runs" / "crypto_paper_oms_dry_run" / "latest"
    output_root = tmp_path / "runs" / "crypto_paper_submit_approval_packet" / "latest"
    root.mkdir(parents=True)
    dry_run = _dry_run()
    if updates:
        dry_run.update(updates)
    _write_json(root / "paper_oms_dry_run.json", dry_run)
    return {
        "dry_run": root / "paper_oms_dry_run.json",
        "output_root": output_root,
    }


def _dry_run() -> dict[str, object]:
    symbol = "BTCUSD"
    return {
        "schema_version": "v5_6_crypto_paper_oms_dry_run_v1",
        "as_of": AS_OF.isoformat(),
        "dry_run_status": "blocked_not_authorized",
        "approval_state": "not_authorized",
        "broker_action_permitted": False,
        "intended_action": "buy_preview",
        "asset_class": "crypto",
        "symbol": symbol,
        "selected_candidate_id": (
            f"crypto:{symbol}:crypto_vol_adjusted_momentum_24h_preview"
        ),
        "selected_strategy": "crypto_vol_adjusted_momentum_24h_preview",
        "selected_backing": "real_local_artifact_backed",
        "latest_price": "63006.709",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "preview_cap": "25",
        "dry_run_id": "dryrun_19bfe1c5645e29869a393564",
        "pre_broker_order_id": "prebroker_a22db5ec89a3d81457712c6b",
        "idempotency_key": (
            "crypto_paper_oms_dry_run:"
            "19bfe1c5645e29869a393564a22db5ec89a3d81457712c6b89e9137fa9f3ddeb"
        ),
        "blockers": [],
        "source_blockers": [],
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": _labels(),
    }


def _labels() -> list[str]:
    return [
        "paper_lab_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "sizing_preview_only",
        "qty_orderable_notional_unobserved",
        "real_local_artifact_backed",
        "paper_oms_handoff_only",
        "approval_required",
        "paper_oms_dry_run_only",
        "pre_broker_preview_only",
        "not_submittable",
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
        "echo {\"approval_packet_status\":\"ready_for_operator_review\",\"paper_submit_authorized\":false}\r\n"
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
        pytest.skip(
            "PowerShell is required to verify "
            "run_crypto_paper_submit_approval_packet.ps1"
        )
    return powershell
