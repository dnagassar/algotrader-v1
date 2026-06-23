from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DAILY_PAPER_LAB_CYCLE_SCRIPT = (
    PROJECT_ROOT / "scripts" / "run_daily_paper_lab_cycle.ps1"
)


def test_run_daily_paper_lab_cycle_script_contract() -> None:
    script = RUN_DAILY_PAPER_LAB_CYCLE_SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the canonical daily paper-lab operating cycle",
        "[string]$BrokerSnapshotLog",
        "BrokerStateMode\", \"alpaca_paper_read_only\"",
        "\"-OperationalOnly\"",
        "\"-Format\", \"json\"",
        "show_daily_paper_lab_status.ps1",
        "latest_run.json",
        "exit $DailyExitCode",
        "does not read a broker",
        "load credentials",
        "contact the network",
    )
    for fragment in expected_fragments:
        assert fragment in script


def test_run_daily_paper_lab_cycle_prints_receipt_and_handles_paths_with_spaces(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper lab latest"
    broker_snapshot = tmp_path / "broker snapshots" / "reconciliation log.jsonl"
    broker_snapshot.parent.mkdir(parents=True)
    broker_snapshot.write_text("{}", encoding="utf-8")
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(
        tmp_path,
        capture_path,
        output_root=output_root,
        daily_exit_code=0,
        receipt_exit_code=0,
    )

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_DAILY_PAPER_LAB_CYCLE_SCRIPT),
            "-OutputRoot",
            str(output_root),
            "-BrokerSnapshotLog",
            str(broker_snapshot),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "validation_status=passed" in result.stdout
    assert "broker_mutation_performed=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.cli etf-sma-daily-paper-lab" in args
    assert "--broker-state-mode alpaca_paper_read_only" in args
    assert "--broker-snapshot-log" in args
    assert str(broker_snapshot) in args
    assert "--operational-only" in args
    assert "-m algotrader.execution.daily_paper_lab_status_receipt" in args
    assert "--output-root" in args
    assert str(output_root) in args


def test_run_daily_paper_lab_cycle_propagates_daily_exit_after_receipt(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "paper_lab_latest"
    broker_snapshot = tmp_path / "reconciliation.jsonl"
    broker_snapshot.write_text("{}", encoding="utf-8")
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(
        tmp_path,
        capture_path,
        output_root=output_root,
        daily_exit_code=7,
        receipt_exit_code=0,
    )

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_DAILY_PAPER_LAB_CYCLE_SCRIPT),
            "-OutputRoot",
            str(output_root),
            "-BrokerSnapshotLog",
            str(broker_snapshot),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 7
    assert "validation_status=passed" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.cli etf-sma-daily-paper-lab" in args
    assert "-m algotrader.execution.daily_paper_lab_status_receipt" in args


def _fake_python_env(
    tmp_path: Path,
    capture_path: Path,
    *,
    output_root: Path,
    daily_exit_code: int,
    receipt_exit_code: int,
) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo %* | find \"daily_paper_lab_status_receipt\" > nul\r\n"
        "if not errorlevel 1 (\r\n"
        "  echo validation_status=passed\r\n"
        "  echo broker_read_performed=false\r\n"
        "  echo broker_mutation_performed=false\r\n"
        "  exit /B %FAKE_RECEIPT_EXIT_CODE%\r\n"
        ")\r\n"
        "echo %* | find \"etf-sma-daily-paper-lab\" > nul\r\n"
        "if not errorlevel 1 (\r\n"
        "  if not exist \"%FAKE_OUTPUT_ROOT%\" mkdir \"%FAKE_OUTPUT_ROOT%\"\r\n"
        "  > \"%FAKE_OUTPUT_ROOT%\\latest_run.json\" echo {\"latest_run_version\":\"test\"}\r\n"
        "  exit /B %FAKE_DAILY_EXIT_CODE%\r\n"
        ")\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )

    env = _scrubbed_env()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    env["FAKE_OUTPUT_ROOT"] = str(output_root)
    env["FAKE_DAILY_EXIT_CODE"] = str(daily_exit_code)
    env["FAKE_RECEIPT_EXIT_CODE"] = str(receipt_exit_code)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify scripts/run_daily_paper_lab_cycle.ps1")
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
