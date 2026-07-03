from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_paper_visibility_cycle.ps1"
SENSITIVE_KEY = "script-paper-key-value-not-for-output"
SENSITIVE_SECRET = "script-paper-secret-value-not-for-output"


def test_run_crypto_paper_visibility_cycle_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the crypto paper visibility cycle in no-submit mode",
        "[string]$OutputRoot = \"runs\\crypto_paper_visibility\\latest\"",
        "[string]$BarsCsv = \"runs\\operator_input\\crypto_paper_bars.csv\"",
        "crypto_visibility_operating_mode=visibility/no_submit",
        "crypto_visibility_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "ALPACA_API_KEY",
        "APCA_API_SECRET_KEY",
        "preflight_$($Name)_present",
        "preflight_paper_endpoint_exact_match_indicator",
        "preflight_live_endpoint_indicator",
        "crypto_visibility_paper_submit_performed=false",
        "crypto_visibility_broker_mutation_performed=false",
        "crypto_visibility_live_mutation_performed=false",
        "algotrader.execution.crypto_paper_visibility_operator",
        "--output-root",
        "--bars-csv",
        "--format",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "[switch]$Submit" not in script
    assert "--submit" not in script


def test_run_crypto_paper_visibility_cycle_invokes_read_only_operator(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "crypto visibility latest"
    bars_csv = tmp_path / "crypto bars.csv"
    bars_csv.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2026-07-03T02:00:00+00:00,BTCUSD,1,1,1,1,1\n",
        encoding="utf-8",
    )
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
            str(output_root),
            "-BarsCsv",
            str(bars_csv),
            "-AsOfTimestamp",
            "2026-07-03T02:00:00+00:00",
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
    assert "crypto_visibility_command=run_crypto_paper_visibility_cycle" in result.stdout
    assert "crypto_visibility_operating_mode=visibility/no_submit" in result.stdout
    assert "crypto_visibility_no_submit_enforced=true" in result.stdout
    assert "preflight_APP_PROFILE_is_paper=true" in result.stdout
    assert "preflight_APCA_API_KEY_ID_present=true" in result.stdout
    assert "preflight_APCA_API_SECRET_KEY_present=true" in result.stdout
    assert "preflight_paper_endpoint_exact_match_indicator=true" in result.stdout
    assert "preflight_live_endpoint_indicator=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.execution.crypto_paper_visibility_operator" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--bars-csv" in args
    assert str(bars_csv) in args
    assert "--timestamp 2026-07-03T02:00:00+00:00" in args
    assert "--format json" in args
    assert "--submit" not in args
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_run_crypto_paper_visibility_cycle_stops_on_live_endpoint(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["ALPACA_PAPER_BASE_URL"] = "https://api.alpaca.markets"

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
    assert "preflight_live_endpoint_indicator=true" in result.stdout
    assert "crypto_visibility_stop_reason=live_endpoint_indicator" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_run_crypto_paper_visibility_cycle_stops_on_apca_live_endpoint(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["APCA_API_BASE_URL"] = "https://api.alpaca.markets"

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
    assert "preflight_live_endpoint_indicator=true" in result.stdout
    assert "crypto_visibility_stop_reason=live_endpoint_indicator" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"broker_read_performed\":false,\"paper_submit_performed\":false}\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    env["APP_PROFILE"] = "paper"
    env["APCA_API_KEY_ID"] = SENSITIVE_KEY
    env["APCA_API_SECRET_KEY"] = SENSITIVE_SECRET
    env["ALPACA_PAPER_BASE_URL"] = "https://paper-api.alpaca.markets"
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify crypto visibility wrapper")
    return powershell
