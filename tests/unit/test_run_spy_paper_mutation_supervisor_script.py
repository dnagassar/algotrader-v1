from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "run_spy_paper_mutation_supervisor.ps1"
VISIBILITY_SCRIPT = PROJECT_ROOT / "scripts" / "run_spy_daily_visibility_cycle.ps1"


def test_run_spy_paper_mutation_supervisor_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the SPY paper-only mutation supervisor",
        "[string]$OutputRoot = \"runs\\paper_mutation_supervisor\\latest\"",
        "[string]$HistoryRoot = \"runs\\paper_mutation_supervisor\\history\"",
        "paper-autopilot-operator",
        "--output-root",
        "--history-root",
        "--bars-csv",
        "--max-notional",
        "[switch]$NoSubmit",
        "--no-submit",
        "preflight_expected_account_id_loaded",
        "preflight_no_submit_mode",
        "preflight_operating_mode",
        "preflight_paper_submit_authorization_scope=bounded_supervisor_run_only",
        "preflight_live_authorized=false",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script


def test_run_spy_daily_visibility_cycle_script_contract() -> None:
    script = VISIBILITY_SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the official SPY daily visibility cycle in no-submit mode",
        "[string]$OutputRoot = \"runs\\spy_daily_visibility\\latest\"",
        "[string]$HistoryRoot = \"runs\\spy_daily_visibility\\history\"",
        "run_spy_paper_mutation_supervisor.ps1",
        "visibility_cycle_operating_mode=visibility/no_submit",
        "visibility_cycle_no_submit_enforced=true",
        "visibility_cycle_data_path=accepted_daily_bars_validation",
        "visibility_cycle_broker_state_not_observed_blocker=blocked/broker_state_not_observed",
        "visibility_cycle_broker_state_not_observed_next_operator_action=configure_verified_paper_profile_then_rerun",
        "visibility_cycle_broker_mutation_performed=false",
        "visibility_cycle_paper_submit_performed=false",
        "visibility_cycle_live_mutation_performed=false",
        "-NoSubmit",
    )
    for fragment in expected_fragments:
        assert fragment in script


def test_run_spy_paper_mutation_supervisor_invokes_operator_cli(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper mutation supervisor latest"
    history_root = tmp_path / "paper mutation supervisor history"
    bars_csv = tmp_path / "bars with spaces.csv"
    bars_csv.write_text("date,symbol,close\n2026-01-01,SPY,100\n", encoding="utf-8")
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
            "-HistoryRoot",
            str(history_root),
            "-BarsCsv",
            str(bars_csv),
            "-AsOfDate",
            "2026-01-01",
            "-Format",
            "json",
            "-NoSubmit",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "preflight_APP_PROFILE_is_paper=true" in result.stdout
    assert "preflight_expected_account_id_loaded=true" in result.stdout
    assert "preflight_no_submit_mode=true" in result.stdout
    assert "preflight_operating_mode=visibility/no_submit" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.cli paper-autopilot-operator" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--history-root" in args
    assert str(history_root) in args
    assert "--bars-csv" in args
    assert str(bars_csv) in args
    assert "--as-of-date 2026-01-01" in args
    assert "--no-submit" in args
    assert "--format json" in args


def test_run_spy_daily_visibility_cycle_invokes_supervisor_with_no_submit(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "spy daily visibility latest"
    history_root = tmp_path / "spy daily visibility history"
    bars_csv = tmp_path / "bars with spaces.csv"
    bars_csv.write_text("date,symbol,close\n2026-01-01,SPY,100\n", encoding="utf-8")
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(VISIBILITY_SCRIPT),
            "-OutputRoot",
            str(output_root),
            "-HistoryRoot",
            str(history_root),
            "-BarsCsv",
            str(bars_csv),
            "-AsOfDate",
            "2026-01-01",
            "-Format",
            "json",
            "-NoSubmit",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "visibility_cycle_command=run_spy_daily_visibility_cycle" in result.stdout
    assert "visibility_cycle_operating_mode=visibility/no_submit" in result.stdout
    assert "visibility_cycle_no_submit_requested=true" in result.stdout
    assert "visibility_cycle_no_submit_enforced=true" in result.stdout
    assert (
        "visibility_cycle_broker_state_not_observed_next_operator_action="
        "configure_verified_paper_profile_then_rerun"
    ) in result.stdout
    assert "preflight_no_submit_mode=true" in result.stdout
    assert "preflight_operating_mode=visibility/no_submit" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.cli paper-autopilot-operator" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--history-root" in args
    assert str(history_root) in args
    assert "--bars-csv" in args
    assert str(bars_csv) in args
    assert "--as-of-date 2026-01-01" in args
    assert "--no-submit" in args
    assert "--format json" in args


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"operator_exit_code\":0}\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    env["APP_PROFILE"] = "paper"
    env["APCA_API_KEY_ID"] = "set-but-not-printed"
    env["APCA_API_SECRET_KEY"] = "set-but-not-printed"
    env["ALPACA_EXPECTED_PAPER_ACCOUNT_ID"] = "set-but-not-printed"
    env["ALPACA_PAPER_BASE_URL"] = "https://paper-api.alpaca.markets"
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip(
            "PowerShell is required to verify scripts/run_spy_paper_mutation_supervisor.ps1"
        )
    return powershell
