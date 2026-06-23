from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DAILY_PAPER_LAB_SCRIPT = PROJECT_ROOT / "scripts" / "run_daily_paper_lab.ps1"


def test_run_daily_paper_lab_script_preserves_offline_launcher_contract() -> None:
    script = RUN_DAILY_PAPER_LAB_SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "[string]$BrokerStateMode = \"broker_state_not_observed\"",
        (
            "[ValidateSet(\"broker_state_not_observed\", \"offline_fixture\", "
            "\"alpaca_paper_read_only\")]"
        ),
        "--broker-state-mode\", $BrokerStateMode",
        "BrokerSnapshotLog",
        "--broker-snapshot-log",
        ".PARAMETER OperationalOnly",
        "[switch]$OperationalOnly",
        ".PARAMETER FullResearchPacket",
        "[switch]$FullResearchPacket",
        "$UseOperationalOnly = $OperationalOnly -or (-not $FullResearchPacket)",
        "--operational-only",
        ".PARAMETER RunDate",
        "[string]$RunDate",
        "--run-date",
        "Distinct from AsOfDate",
        "the daily lab command itself performs no broker read",
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "Test-ProcessEnvironmentVariableLoaded",
        "Daily paper-lab assistant must run offline only without credentials",
        "Mission Control generated.",
        "Open first: $IndexPath",
        "Operator review: $OperatorReviewPath",
        "Latest run summary: $LatestRunPath",
        "Validation: $ValidationPath",
        "Data refresh bridge: $DataRefreshBridgePath",
        "Data refresh dry run: $DataRefreshDryRunPath",
        "Data refresh dry-run status: $DataRefreshDryRunStatusText",
        "Data refresh CSV present: $DataRefreshInputCsvPresentText",
        "Data refresh ingest performed: $DataRefreshIngestPerformedText",
        "Data refresh checklist: $DataRefreshChecklistPath",
        "Paper submit authorized: false",
        "Live authorized: false",
        "Broker read performed: false",
        "Broker mutation performed: false",
        "Broker-state mode: $BrokerStateModeText",
        "Forward signal evidence ledger status: $ForwardSignalEvidenceLedgerStatusText",
        "Exact next operator action: $ExactNextOperatorActionText",
        "latest_run.json",
        "data_refresh_bridge.json",
        "data_refresh_dry_run.json",
        "data_refresh_operator_checklist.md",
    )
    for fragment in expected_fragments:
        assert fragment in script

def test_run_daily_paper_lab_script_propagates_python_exit_code() -> None:
    script = RUN_DAILY_PAPER_LAB_SCRIPT.read_text(encoding="utf-8")

    python_call_index = script.index("& python @CliArgs")
    capture_index = script.index("$ExitCode = $LASTEXITCODE")
    final_exit_index = script.rindex("exit $ExitCode")

    assert python_call_index < capture_index < final_exit_index
    assert 'if ($ExitCode -eq 0 -and $Format -eq "text")' in script
    assert "exit 0" not in script


def test_run_daily_paper_lab_script_translates_run_date_to_cli_arg(
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
            str(RUN_DAILY_PAPER_LAB_SCRIPT),
            "-OutputRoot",
            str(tmp_path / "paper_lab_out"),
            "-AsOfDate",
            "2026-06-18",
            "-RunDate",
            "2026-06-20",
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

    assert result.returncode == 0, result.stdout + result.stderr
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.cli etf-sma-daily-paper-lab" in args
    assert "--as-of-date 2026-06-18" in args
    assert "--run-date 2026-06-20" in args
    assert "--operational-only" in args


def test_run_daily_paper_lab_script_omits_run_date_cli_arg_when_absent(
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
            str(RUN_DAILY_PAPER_LAB_SCRIPT),
            "-OutputRoot",
            str(tmp_path / "paper_lab_out"),
            "-AsOfDate",
            "2026-06-18",
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

    assert result.returncode == 0, result.stdout + result.stderr
    args = capture_path.read_text(encoding="utf-8")
    assert "--as-of-date 2026-06-18" in args
    assert "--run-date" not in args
    assert "--operational-only" in args


def test_run_daily_paper_lab_script_full_research_packet_omits_operational_flag(
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
            str(RUN_DAILY_PAPER_LAB_SCRIPT),
            "-OutputRoot",
            str(tmp_path / "paper_lab_out"),
            "-AsOfDate",
            "2026-06-18",
            "-Format",
            "json",
            "-FullResearchPacket",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.cli etf-sma-daily-paper-lab" in args
    assert "--operational-only" not in args


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        "> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )

    env = _scrubbed_env()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify scripts/run_daily_paper_lab.ps1")
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
    ):
        env.pop(name, None)
    return env
