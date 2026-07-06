from __future__ import annotations

import ast
from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.execution.tomorrow_crypto_trader_demo import (
    MAX_NOTIONAL_PER_ORDER,
    MAX_TOTAL_DEMO_EXPOSURE,
    REQUIRED_ARTIFACTS,
    REQUIRED_SAFETY_LABELS,
    run_tomorrow_crypto_trader_demo,
    validate_tomorrow_crypto_trader_demo,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "src" / "algotrader" / "execution" / "tomorrow_crypto_trader_demo.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_tomorrow_crypto_trader_demo.ps1"
VALIDATOR_SCRIPT_PATH = (
    PROJECT_ROOT / "scripts" / "validate_tomorrow_crypto_trader_demo.ps1"
)
AS_OF = datetime(2026, 7, 6, 14, 30, tzinfo=UTC)
SENSITIVE_KEY = "SENTINEL_ALPACA_SECRET_DO_NOT_PRINT"


def test_simbroker_end_to_end_run_writes_valid_artifact_packet(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )

    assert packet["mode"] == "SimBroker"
    assert packet["broker_mode"] == "simulation_broker"
    assert packet["decision"] == "offline_simulated_trade_only"
    assert packet["selected_candidate"]["symbol"] == "BTCUSD"
    assert packet["selected_candidate"]["data_gate_passed"] is True
    assert packet["selected_candidate"]["orderability_gate_passed"] is True
    assert packet["selected_candidate"]["risk_gate_passed"] is True
    assert packet["final_blocker_status"] == "none"
    assert packet["safety"]["broker_read_occurred"] is False
    assert packet["safety"]["broker_mutation_occurred"] is False
    assert packet["safety"]["paper_submit_occurred"] is False
    assert packet["safety"]["simulation_mutation_occurred"] is True
    assert packet["safety"]["network_used"] is False
    assert set(REQUIRED_SAFETY_LABELS) <= set(packet["safety_labels"])

    for artifact_name in REQUIRED_ARTIFACTS:
        assert (output_root / artifact_name).is_file()

    events = [
        json.loads(line)
        for line in (output_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_types = {event["event_type"] for event in events}
    assert "simulation_order_submitted" in event_types
    assert "simulation_order_filled" in event_types
    assert "simulation_reconciliation_checked" in event_types

    validation = validate_tomorrow_crypto_trader_demo(output_root)
    assert validation["validation_status"] == "passed", validation["errors"]


def test_simbroker_caps_are_enforced_in_selected_fill(tmp_path: Path) -> None:
    packet = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "latest",
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )

    fill = packet["fill_ledger"][0]
    portfolio = packet["portfolio_snapshot"]

    assert _decimal(fill["notional"]) <= MAX_NOTIONAL_PER_ORDER
    assert _decimal(portfolio["gross_exposure"]) <= MAX_TOTAL_DEMO_EXPOSURE
    assert len(portfolio["positions"]) == 1
    assert portfolio["positions"][0]["symbol"] == "BTCUSD"


def test_duplicate_client_order_id_blocks_before_simulated_fill(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "first"
    first = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    client_order_id = first["execution_intent"]["client_order_id"]

    second = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "second",
        mode="SimBroker",
        as_of=AS_OF,
        existing_client_order_ids=(client_order_id,),
        write_artifacts=True,
    )

    assert second["decision"] == "blocked_duplicate_client_order_id"
    assert "duplicate_client_order_id" in second["final_blocker_status"]
    assert second["fill_ledger"] == []
    assert second["safety"]["simulation_mutation_occurred"] is False


def test_simbroker_artifacts_do_not_capture_loaded_credential_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_KEY)
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", f"{SENSITIVE_KEY}_SECRET")
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    emitted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    )

    assert packet["safety"]["credential_values_exposed"] is False
    assert SENSITIVE_KEY not in emitted
    assert f"{SENSITIVE_KEY}_SECRET" not in emitted


def test_alpaca_paper_mode_refuses_without_exact_authorization() -> None:
    packet = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=False,
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert packet["decision"] == "blocked_not_authorized"
    assert packet["safety"]["paper_submit_authorized"] is False
    assert packet["safety"]["broker_mutation_authorized"] is False
    assert packet["safety"]["broker_mutation_occurred"] is False


def test_alpaca_paper_mode_blocks_bad_profile_and_missing_credentials() -> None:
    dev_packet = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment={"APP_PROFILE": "dev"},
        as_of=AS_OF,
        write_artifacts=False,
    )
    paper_no_creds = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment={"APP_PROFILE": "paper"},
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert dev_packet["decision"] == "blocked_not_paper_profile"
    assert paper_no_creds["decision"] == "blocked_credentials_not_loaded"


def test_alpaca_paper_mode_blocks_ambiguous_state_and_min_notional_uncertainty() -> None:
    env = {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": True,
        "APCA_API_SECRET_KEY": True,
    }

    preexisting = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment=env,
        alpaca_paper_snapshot={"positions": [{"symbol": "BTCUSD", "qty": "1"}]},
        as_of=AS_OF,
        write_artifacts=False,
    )
    ambiguous = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment=env,
        alpaca_paper_snapshot={"current_run_attribution_complete": False},
        as_of=AS_OF,
        write_artifacts=False,
    )
    min_notional = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment=env,
        alpaca_paper_snapshot={
            "current_run_attribution_complete": True,
            "min_notional_verified": False,
            "qty_increment_verified": True,
        },
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert preexisting["decision"] == "blocked_unexpected_preexisting_position_or_order"
    assert ambiguous["decision"] == "blocked_paper_state_ambiguous"
    assert min_notional["decision"] == "blocked_min_notional_or_increment_not_verified"


def test_validator_fails_on_missing_required_label(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    record_path = output_root / "operating_record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["safety_labels"] = [
        label
        for label in record["safety_labels"]
        if label != "credential_values_exposed=false"
    ]
    record_path.write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "operating_record_missing_label:credential_values_exposed=false" in validation[
        "errors"
    ]


def test_module_has_no_broker_sdk_or_network_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
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
    )
    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported_modules
        for prefix in forbidden_prefixes
    )


def test_scripts_expose_simbroker_and_validator_contracts() -> None:
    run_script = SCRIPT_PATH.read_text(encoding="utf-8")
    validator_script = VALIDATOR_SCRIPT_PATH.read_text(encoding="utf-8")

    for fragment in (
        '[string]$OutputRoot = "runs\\crypto_trader_demo\\latest"',
        '[ValidateSet("SimBroker", "AlpacaPaper")]',
        "[switch]$AllowAlpacaPaperMutation",
        "tomorrow_crypto_trader_demo_broker_mode=simulation_broker",
        "tomorrow_crypto_trader_demo_status=blocked_not_authorized",
        "Credential values are never printed",
        "algotrader.execution.tomorrow_crypto_trader_demo",
        "--allow-alpaca-paper-mutation",
    ):
        assert fragment in run_script
    for fragment in (
        "validate_tomorrow_crypto_trader_demo",
        "tomorrow_crypto_trader_demo_validator_network_used=false",
        "--validate-only",
    ):
        assert fragment in validator_script

    assert "close_all" not in run_script
    assert "liquidate" not in run_script
    assert "--live" not in run_script


def test_script_refuses_alpaca_paper_without_authorization_flag(tmp_path: Path) -> None:
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
            "-Mode",
            "AlpacaPaper",
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
    assert "tomorrow_crypto_trader_demo_status=blocked_not_authorized" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    manifest = json.loads(Path(packet["artifact_paths"]["manifest"]).read_text("utf-8"))
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert manifest["generated_under_runs"] is True
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"decision\":\"offline_simulated_trade_only\"}\r\n"
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
        pytest.skip("PowerShell is required to verify run_tomorrow_crypto_trader_demo.ps1")
    return powershell


def _decimal(value: object):
    from decimal import Decimal

    return Decimal(str(value))
