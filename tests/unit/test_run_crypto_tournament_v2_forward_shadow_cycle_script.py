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
    / "run_crypto_tournament_v2_forward_shadow_cycle.ps1"
)


def test_forward_shadow_cycle_script_is_selected_state_only_and_no_submit() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    for fragment in (
        "initialize",
        "status",
        "readiness",
        "market_data_fetch",
        "selected_symbol_source=frozen_shadow_state",
        "crypto_tournament_v2_forward_shadow_no_submit=true",
        "paper_mutation_authorized=false",
        "credential_values_exposed=false",
        "broker_read_occurred=false",
        "paper_submit_occurred=false",
        "algotrader.orchestration.crypto_tournament_v2_forward_shadow",
        "--market-data-fetch-authorized",
        "--allow-network",
    ):
        assert fragment in source
    assert "[string]$Symbol" not in source
    assert "BTCUSD" not in source
    assert "ETHUSD" not in source
    assert "SOLUSD" not in source
    assert "[switch]$Submit" not in source
    assert "--submit" not in source


def test_forward_shadow_status_never_forwards_network_flags(tmp_path: Path) -> None:
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
            "-Mode",
            "status",
            "-AsOf",
            "2026-08-13T00:00:00+00:00",
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
    assert "selected_symbol_source=frozen_shadow_state" in result.stdout
    assert "APP_PROFILE_is_paper=false" in result.stdout
    args = capture.read_text(encoding="utf-8")
    assert (
        "-m algotrader.orchestration."
        "crypto_tournament_v2_forward_shadow"
    ) in args
    assert "--mode status" in args
    assert "--allow-network" not in args
    assert "--market-data-fetch-authorized" not in args


def test_forward_shadow_fetch_requires_both_switches_before_python(
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
            "-Mode",
            "market_data_fetch",
            "-MarketDataFetchAuthorized",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "requires -MarketDataFetchAuthorized and -AllowNetwork" in (
        result.stdout + result.stderr
    )
    assert not capture.exists()


def test_forward_shadow_fetch_rejects_live_profile_before_python(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture)
    env["APP_PROFILE"] = "live"
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Mode",
            "market_data_fetch",
            "-MarketDataFetchAuthorized",
            "-AllowNetwork",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Live profile or endpoint indicator blocks" in (
        result.stdout + result.stderr
    )
    assert not capture.exists()


def _fake_python_env(tmp_path: Path, capture: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"classification\":\"status\"}\r\n"
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
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is required for wrapper verification")
    return executable
