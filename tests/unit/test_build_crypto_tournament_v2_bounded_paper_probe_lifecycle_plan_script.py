from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / (
    "build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan.ps1"
)


def test_sealed_planner_script_is_offline_and_has_no_sensitive_arguments() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    for fragment in (
        "credential-free, network-free, broker-free, and mutation-free",
        "crypto_tournament_v2_lifecycle_planner_offline=true",
        "credential_values_exposed=false",
        "network_access_attempted=false",
        "broker_read_occurred=false",
        "broker_mutation_occurred=false",
        "paper_mutation_authorized=false",
        "capital_allocation_authorized=false",
        "live_authorized=false",
        "crypto_tournament_v2_bounded_paper_probe_lifecycle",
    ):
        assert fragment in source
    for forbidden in (
        "[switch]$AllowNetwork",
        "--allow-network",
        "--expected-paper-account-id",
        "--as-of",
        "--submit",
        "--cancel",
        "--replace",
        "--close",
        "--liquidate",
    ):
        assert forbidden not in source


def test_sealed_planner_script_forwards_only_local_paths(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture, exit_code=0)
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-ShadowRoot",
            "shadow",
            "-OutputRoot",
            "output",
            "-VenueOrderabilityPath",
            "venue.json",
            "-VenueRuntimeVisibilityPath",
            "visibility.json",
            "-SafetyKernelSourcePath",
            "kernel.py",
            "-SafetyCertifierSourcePath",
            "certifier.py",
            "-SafetyFocusedTestSourcePath",
            "focused-test.py",
            "-SafetyCertificationReceiptPath",
            "safety.json",
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
    args = capture.read_text(encoding="utf-8")
    for fragment in (
        "--shadow-root shadow",
        "--output-root output",
        "--venue-orderability-path venue.json",
        "--venue-runtime-visibility-path visibility.json",
        "--safety-kernel-source-path kernel.py",
        "--safety-certifier-source-path certifier.py",
        "--safety-focused-test-source-path focused-test.py",
        "--safety-certification-receipt-path safety.json",
    ):
        assert args.count(fragment) == 1
    assert "--as-of" not in args
    assert "--expected-paper-account-id" not in args


@pytest.mark.parametrize(
    ("name", "value", "message", "sensitive"),
    (
        (
            "APP_PROFILE",
            " PaPeR ",
            "APP_PROFILE=paper or live is not allowed",
            False,
        ),
        (
            "ALPACA_SECRET_KEY",
            "must-never-be-printed",
            "requires a credential-free process",
            True,
        ),
        (
            "ALLOW_NETWORK_TESTS",
            "1",
            "rejects network-test flags",
            False,
        ),
    ),
)
def test_sealed_planner_script_rejects_nonoffline_process_before_python(
    tmp_path: Path,
    name: str,
    value: str,
    message: str,
    sensitive: bool,
) -> None:
    capture = tmp_path / "blocked-args.txt"
    env = _fake_python_env(tmp_path, capture, exit_code=0)
    env[name] = value

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
    assert result.returncode != 0
    assert message in combined
    assert not capture.exists()
    if sensitive:
        assert value not in combined


def test_sealed_planner_script_propagates_child_exit_code(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "exit-args.txt"
    env = _fake_python_env(tmp_path, capture, exit_code=7)

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

    assert result.returncode == 7
    assert capture.is_file()


def _fake_python_env(
    tmp_path: Path,
    capture: Path,
    *,
    exit_code: int,
) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"classification\":\"fixture\"}\r\n"
        f"exit /B {exit_code}\r\n",
        encoding="utf-8",
        newline="",
    )
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture)
    env["APP_PROFILE"] = "dev"
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is required for wrapper verification")
    return executable
