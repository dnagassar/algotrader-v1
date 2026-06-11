from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_SCRIPT = PROJECT_ROOT / "scripts" / "run_daily_lab_acceptance.ps1"
SENSITIVE_TEST_VALUE = "secret-value-for-acceptance-test"


def test_daily_lab_acceptance_script_declares_offline_guard_contract() -> None:
    script = ACCEPTANCE_SCRIPT.read_text(encoding="utf-8")

    assert "scripts/verify_offline.ps1" in script
    assert "etf-sma-daily-soak-golden-check" in script
    assert "APP_PROFILE" in script
    assert "ALPACA_API_KEY" in script
    assert "ALPACA_API_SECRET_KEY" in script
    assert "ALPACA_SECRET_KEY" in script
    assert "APCA_API_KEY_ID" in script
    assert "APCA_API_SECRET_KEY" in script
    assert "git ls-files" in script
    assert "git diff --cached" in script
    assert "DAILY LAB ACCEPTANCE SUMMARY" in script


def test_daily_lab_acceptance_happy_path() -> None:
    # Use a short date range (2025-06-01 to 2025-06-02) to keep the test fast
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-File",
            str(ACCEPTANCE_SCRIPT),
            "-StartDate",
            "2025-06-01",
            "-EndDate",
            "2025-06-02",
        ],
        cwd=PROJECT_ROOT,
        env=_scrubbed_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "APP_PROFILE_is_paper: False" in result.stdout
    assert "ALPACA_API_KEY_loaded: False" in result.stdout
    assert "APCA_API_SECRET_KEY_loaded: False" in result.stdout
    assert "Running offline verification" in result.stdout
    assert "Verifier Status:              PASS" in result.stdout
    assert "Golden Acceptance Status:     ACCEPTED" in result.stdout
    assert "Release Gate Status:          ACCEPTED" in result.stdout
    assert "Pre-Gate Validation Findings:  0" in result.stdout
    assert "Post-Gate Validation Findings: 0" in result.stdout
    assert "Output Root:                  runs/daily_soak" in result.stdout
    assert "live_trading_authorized:      False" in result.stdout
    assert "paper_submit_authorized:     False" in result.stdout
    assert "broker_mutation_authorized:   False" in result.stdout
    assert "paper_broker_reads_authorized: False" in result.stdout
    assert "network_access_authorized:   False" in result.stdout
    assert "credential_loading_authorized: False" in result.stdout
    assert "Tracked/Staged check:       PASS (No generated runs artifacts are tracked or staged)" in result.stdout


def test_daily_lab_acceptance_blocks_loaded_credentials_without_printing_values() -> None:
    env = _scrubbed_env()
    env["ALPACA_API_KEY"] = SENSITIVE_TEST_VALUE

    result = subprocess.run(
        [_powershell(), "-NoProfile", "-File", str(ACCEPTANCE_SCRIPT)],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined_output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "ALPACA_API_KEY_loaded: True" in result.stdout
    assert "broker credential environment variable" in combined_output
    assert SENSITIVE_TEST_VALUE not in combined_output


def test_daily_lab_acceptance_blocks_paper_profile() -> None:
    env = _scrubbed_env()
    env["APP_PROFILE"] = "paper"

    result = subprocess.run(
        [_powershell(), "-NoProfile", "-File", str(ACCEPTANCE_SCRIPT)],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined_output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "APP_PROFILE_is_paper: True" in result.stdout
    assert "APP_PROFILE is paper" in combined_output


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify daily lab acceptance script")
    return powershell


def _scrubbed_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "PYTEST_ADDOPTS",
    ):
        env.pop(name, None)
    return env
