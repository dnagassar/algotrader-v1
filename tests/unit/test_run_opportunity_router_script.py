from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "run_opportunity_router.ps1"
SENSITIVE_KEY = "opportunity-router-key-value-not-for-output"


def test_run_opportunity_router_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the offline multi-asset opportunity router in no-submit mode",
        '[string]$OutputRoot = "runs\\opportunity_router\\latest"',
        '[string]$CryptoBarsCsv = "runs\\operator_input\\crypto_paper_bars.csv"',
        "opportunity_router_mode=offline/no_submit",
        "opportunity_router_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "opportunity_router_paper_submit_authorized=false",
        "opportunity_router_paper_submit_performed=false",
        "opportunity_router_broker_mutation_performed=false",
        "opportunity_router_live_mutation_performed=false",
        "algotrader.orchestration.opportunity_router",
        "--output-root",
        "--crypto-bars-csv",
        "--crypto-visibility-status",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "--submit" not in script
    assert "paper_submit_authorized=true" not in script


def test_run_opportunity_router_script_invokes_offline_module(tmp_path: Path) -> None:
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
            str(tmp_path / "router latest"),
            "-SpyBarsCsv",
            str(tmp_path / "spy.csv"),
            "-CryptoBarsCsv",
            str(tmp_path / "crypto.csv"),
            "-CryptoVisibilityStatus",
            str(tmp_path / "crypto_status.json"),
            "-AsOfTimestamp",
            "2026-07-04T00:30:00+00:00",
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
    assert "opportunity_router_command=run_opportunity_router" in result.stdout
    assert "opportunity_router_no_submit_enforced=true" in result.stdout
    assert "preflight_credential_variables_loaded=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.orchestration.opportunity_router" in args
    assert "--output-root" in args
    assert "--spy-bars-csv" in args
    assert "--crypto-bars-csv" in args
    assert "--crypto-visibility-status" in args
    assert "--as-of 2026-07-04T00:30:00+00:00" in args
    assert "--format json" in args
    assert "--submit" not in args


def test_run_opportunity_router_script_blocks_loaded_credentials(tmp_path: Path) -> None:
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
    assert "opportunity_router_status=blocked_unsafe_environment" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"decision\":\"no_trade\",\"paper_submit_performed\":false}\r\n"
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
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_opportunity_router.ps1")
    return powershell
