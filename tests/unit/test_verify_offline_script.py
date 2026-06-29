from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERIFY_OFFLINE_SCRIPT = PROJECT_ROOT / "scripts" / "verify_offline.ps1"
SENSITIVE_TEST_VALUE = "secret-value-for-verify-offline-test"


def test_verify_offline_script_declares_offline_guard_contract() -> None:
    script = VERIFY_OFFLINE_SCRIPT.read_text(encoding="utf-8")

    assert "tests/unit/test_dependency_direction.py" in script
    assert "tests/unit/test_broker_mutation_surface_invariant.py" in script
    assert "tests/unit/test_default_pytest_network_guard.py" in script
    assert "tests/unit/test_strategy_challenger_factory.py" in script
    assert "python\" (@(\"-m\", \"pytest\") + $GuardTestPaths)" in script
    assert "\"python\" @(\"-m\", \"pytest\")" in script
    assert "git\" @(\"diff\", \"--check\")" in script
    assert "git\" @(\"ls-files\", \"runs\")" in script
    assert "git\" @(\"ls-files\", \"runs/daily\")" in script
    assert "git\" @(\"ls-files\", \"runs/daily_soak\")" in script
    assert "git\" @(\"ls-files\", \"runs/paper_autopilot\")" in script
    assert "git\" @(\"ls-files\", \"runs/strategy_challengers\")" in script
    assert "ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled" in script
    assert "PYTEST_ADDOPTS_allow_network" in script
    assert "RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled" in script
    assert "load_env.ps1" not in script
    assert "Set-Item -Path \"Env:" not in script


def test_verify_offline_default_mode_runs_targeted_checks_without_credentials() -> None:
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-File", str(VERIFY_OFFLINE_SCRIPT)],
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
    assert "ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled: False" in result.stdout
    assert "PYTEST_ADDOPTS_allow_network: False" in result.stdout
    assert "RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled: False" in result.stdout
    assert "targeted offline safety guard tests" in result.stdout
    assert "Skipped. Re-run with -Full" in result.stdout
    assert "PASS" in result.stdout


def test_verify_offline_blocks_loaded_credentials_without_printing_values() -> None:
    env = _scrubbed_env()
    env["ALPACA_API_KEY"] = SENSITIVE_TEST_VALUE

    result = subprocess.run(
        [_powershell(), "-NoProfile", "-File", str(VERIFY_OFFLINE_SCRIPT)],
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
    assert "Offline verification blocked" in combined_output
    assert SENSITIVE_TEST_VALUE not in combined_output


def test_verify_offline_blocks_network_escape_hatch() -> None:
    env = _scrubbed_env()
    env["ALGO_TRADER_ALLOW_NETWORK_TESTS"] = "1"

    result = subprocess.run(
        [_powershell(), "-NoProfile", "-File", str(VERIFY_OFFLINE_SCRIPT)],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined_output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled: True" in result.stdout
    assert "network test escape hatch is enabled" in combined_output


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify scripts/verify_offline.ps1")
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
