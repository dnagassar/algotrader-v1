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
    / "run_crypto_tournament_v2_forward_oos.ps1"
)


def test_v2_script_contract_is_no_submit_and_three_symbol_only() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    for fragment in (
        "initialize",
        "status",
        "readiness",
        "market_data_fetch",
        "BTCUSD,ETHUSD,SOLUSD",
        "crypto_tournament_v2_no_submit=true",
        "crypto_tournament_v2_paper_mutation_authorized=false",
        "credential_values_exposed=false",
        "broker_mutation_occurred=false",
        "paper_submit_occurred=false",
        "algotrader.orchestration.crypto_tournament_v2_forward_oos",
        "--market-data-fetch-authorized",
        "--allow-network",
    ):
        assert fragment in source
    assert "[switch]$Submit" not in source
    assert "--submit" not in source
    assert "ADAUSD" not in source


def test_v2_status_invocation_does_not_forward_network_flags(
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
            "status",
            "-AsOf",
            "2026-07-15T12:00:00+00:00",
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
    assert "crypto_tournament_v2_symbols=BTCUSD,ETHUSD,SOLUSD" in (
        result.stdout
    )
    assert "APP_PROFILE_is_paper=false" in result.stdout
    args = capture.read_text(encoding="utf-8")
    assert (
        "-m algotrader.orchestration."
        "crypto_tournament_v2_forward_oos"
    ) in args
    assert "--mode status" in args
    assert "--allow-network" not in args
    assert "--market-data-fetch-authorized" not in args


def test_v2_fetch_requires_both_explicit_switches(
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


def _fake_python_env(
    tmp_path: Path,
    capture: Path,
) -> dict[str, str]:
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
