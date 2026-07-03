from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "refresh_crypto_paper_bars.ps1"
SENSITIVE_KEY = "script-paper-key-value-not-for-output"
SENSITIVE_SECRET = "script-paper-secret-value-not-for-output"


def test_refresh_crypto_paper_bars_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Refreshes BTCUSD crypto bars for the no-submit crypto paper visibility lane",
        "[string]$CanonicalCsv = \"runs\\operator_input\\crypto_paper_bars.csv\"",
        "crypto_bars_refresh_read_only_market_data=true",
        "crypto_bars_refresh_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_paper_credentials_present",
        "preflight_live_endpoint_indicator",
        "crypto_bars_refresh_paper_submit_performed=false",
        "crypto_bars_refresh_broker_mutation_performed=false",
        "crypto_bars_refresh_live_mutation_performed=false",
        "scripts\\research\\fetch_alpaca_crypto_bars.py",
        "--allow-network",
        "--market-data-fetch-authorized",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "[switch]$Submit" not in script
    assert "--submit" not in script


def test_refresh_crypto_paper_bars_invokes_read_only_fetcher(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.json"
    canonical_csv = tmp_path / "crypto bars.csv"
    run_log = tmp_path / "manifest.jsonl"
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
            "-RawResponsePath",
            str(raw_path),
            "-CanonicalCsv",
            str(canonical_csv),
            "-RunLog",
            str(run_log),
            "-ObservedAt",
            "2026-07-03T02:00:00+00:00",
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
    assert "crypto_bars_refresh_command=refresh_crypto_paper_bars" in result.stdout
    assert "crypto_bars_refresh_read_only_market_data=true" in result.stdout
    assert "preflight_APP_PROFILE_is_paper=true" in result.stdout
    assert "preflight_APCA_API_KEY_ID_present=true" in result.stdout
    assert "preflight_APCA_API_SECRET_KEY_present=true" in result.stdout
    assert "preflight_paper_credentials_present=true" in result.stdout
    assert "preflight_live_endpoint_indicator=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "scripts\\research\\fetch_alpaca_crypto_bars.py" in args
    assert "--raw-response-path" in args
    assert str(raw_path) in args
    assert "--canonical-csv" in args
    assert str(canonical_csv) in args
    assert "--run-log" in args
    assert str(run_log) in args
    assert "--observed-at 2026-07-03T02:00:00+00:00" in args
    assert "--allow-network --market-data-fetch-authorized" in args
    assert "--submit" not in args
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_refresh_crypto_paper_bars_stops_without_authorization(tmp_path: Path) -> None:
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
    assert "crypto_bars_refresh_stop_reason=market_data_fetch_authorization_required" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_refresh_crypto_paper_bars_stops_on_live_endpoint(tmp_path: Path) -> None:
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
            "-MarketDataFetchAuthorized",
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
    assert "crypto_bars_refresh_stop_reason=live_endpoint_indicator" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"intake_state\":\"accepted_fresh_crypto_bars\"}\r\n"
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
        pytest.skip("PowerShell is required to verify crypto bars refresh wrapper")
    return powershell
