from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "refresh_multi_symbol_crypto_history.ps1"
SENSITIVE_KEY = "wrapper-key-not-for-output"
SENSITIVE_SECRET = "wrapper-secret-not-for-output"


def test_refresh_multi_symbol_crypto_history_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Builds a guarded multi-symbol crypto OHLC history refresh packet",
        '[ValidateSet("dry_run", "offline_fixture", "market_data_fetch")]',
        '[string]$Symbols = "BTCUSD,ETHUSD,SOLUSD,ADAUSD"',
        '[string]$OutputPath = "runs\\operator_input\\crypto_paper_bars.csv"',
        "crypto_history_refresh_read_only_market_data=true",
        "crypto_history_refresh_no_submit_enforced=true",
        "APP_PROFILE_is_paper",
        "ALPACA_API_KEY_loaded",
        "ALPACA_API_SECRET_KEY_loaded",
        "ALPACA_SECRET_KEY_loaded",
        "APCA_API_KEY_ID_loaded",
        "APCA_API_SECRET_KEY_loaded",
        "APCA_API_BASE_URL_is_live",
        "APCA_API_BASE_URL_is_paper",
        "preflight_live_endpoint_indicator",
        "crypto_history_refresh_paper_submit_occurred=false",
        "crypto_history_refresh_broker_mutation_occurred=false",
        "algotrader.execution.crypto_history_refresh_adapter",
        "--market-data-fetch-authorized",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "[switch]$Submit" not in script
    assert "--submit" not in script


def test_refresh_multi_symbol_crypto_history_invokes_dry_run_module(
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
            "-Mode",
            "dry_run",
            "-OutputPath",
            str(tmp_path / "history.csv"),
            "-PacketPath",
            str(tmp_path / "packet.json"),
            "-AsOfTimestamp",
            "2026-07-09T00:00:00+00:00",
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
    assert "crypto_history_refresh_command=refresh_multi_symbol_crypto_history" in result.stdout
    assert "APP_PROFILE_is_paper=false" in result.stdout
    assert "APCA_API_KEY_ID_loaded=false" in result.stdout
    assert "APCA_API_BASE_URL_is_live=false" in result.stdout
    assert "APCA_API_BASE_URL_is_paper=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.execution.crypto_history_refresh_adapter" in args
    assert "--mode dry_run" in args
    assert "--symbols BTCUSD,ETHUSD,SOLUSD,ADAUSD" in args
    assert "--output-path" in args
    assert "--as-of 2026-07-09T00:00:00+00:00" in args
    assert "--format json" in args
    assert "--allow-network" not in args
    assert "--market-data-fetch-authorized" not in args


def test_refresh_multi_symbol_crypto_history_adds_fetch_flags_only_when_authorized(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["APP_PROFILE"] = "paper"
    env["APCA_API_KEY_ID"] = SENSITIVE_KEY
    env["APCA_API_SECRET_KEY"] = SENSITIVE_SECRET
    env["APCA_API_BASE_URL"] = "https://paper-api.alpaca.markets"
    env["ALPACA_PAPER_BASE_URL"] = "https://paper-api.alpaca.markets"

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
    assert "APP_PROFILE_is_paper=true" in result.stdout
    assert "APCA_API_KEY_ID_loaded=true" in result.stdout
    assert "APCA_API_BASE_URL_is_live=false" in result.stdout
    assert "APCA_API_BASE_URL_is_paper=true" in result.stdout
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined
    args = capture_path.read_text(encoding="utf-8")
    assert "--mode market_data_fetch" in args
    assert "--allow-network --market-data-fetch-authorized" in args
    assert "--submit" not in args


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"classification\":\"dry_run_ready\"}\r\n"
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
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify refresh wrapper")
    return powershell
