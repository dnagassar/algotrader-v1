from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "run_crypto_tournament_v2_bounded_paper_probe_review.ps1"
)


def test_review_script_is_offline_no_submit_and_no_authority() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    for fragment in (
        "credential-free, network-free, broker-free, no-submit",
        "crypto_tournament_v2_bounded_paper_probe_review_offline=true",
        "credential_values_exposed=false",
        "network_access_attempted=false",
        "broker_read_occurred=false",
        "broker_mutation_occurred=false",
        "paper_probe_authorized=false",
        "capital_allocation_authorized=false",
        "live_authorized=false",
        "crypto_tournament_v2_bounded_paper_probe_review",
    ):
        assert fragment in source
    for forbidden in (
        "[switch]$AllowNetwork",
        "[switch]$Submit",
        "--allow-network",
        "--submit",
        "--cancel",
        "--replace",
        "--liquidate",
    ):
        assert forbidden not in source


def test_review_script_forwards_only_local_evidence_arguments(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture)
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
            "-CapabilityRoot",
            "capabilities",
            "-OutputRoot",
            "review",
            "-AsOf",
            "2026-08-20T00:00:00+00:00",
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
    assert "bounded_paper_probe_review_offline=true" in result.stdout
    args = capture.read_text(encoding="utf-8")
    assert (
        "-m algotrader.orchestration."
        "crypto_tournament_v2_bounded_paper_probe_review"
    ) in args
    assert "--shadow-root shadow" in args
    assert "--capability-root capabilities" in args
    assert "--output-root review" in args
    assert "--as-of 2026-08-20T00:00:00+00:00" in args
    assert "--allow-network" not in args


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
            "ALPACA_API_SECRET_KEY",
            "loaded-but-never-printed",
            "requires a credential-free process",
            True,
        ),
        (
            "ALLOW_NETWORK_TESTS",
            "enabled",
            "rejects network-test flags",
            False,
        ),
        (
            "APCA_API_BASE_URL",
            "https://api.alpaca.markets",
            "rejects live endpoint indicators",
            True,
        ),
    ),
)
def test_review_script_rejects_nonoffline_process_before_python(
    tmp_path: Path,
    name: str,
    value: str,
    message: str,
    sensitive: bool,
) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture)
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

    assert result.returncode != 0
    assert message in result.stdout + result.stderr
    assert not capture.exists()
    if sensitive:
        assert value not in result.stdout + result.stderr


def _fake_python_env(tmp_path: Path, capture: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"classification\":\"waiting\"}\r\n"
        "exit /B 0\r\n",
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
