from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEDULE = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "crypto_tournament_v2_oos_scheduler_task.xml"
)
NAMESPACE = {"task": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def test_task_xml_declaration() -> None:
    declaration = SCHEDULE.read_text(encoding="utf-8").splitlines()[0]
    assert declaration == '<?xml version="1.0"?>'


def test_task_xml_scheduler_settings() -> None:
    root = ET.parse(SCHEDULE).getroot()

    assert _text(root, ".//task:URI") == "\\crypto-tournament-v2-oos-scheduler"
    assert _text(root, ".//task:MultipleInstancesPolicy") == "IgnoreNew"
    assert _text(root, ".//task:StartWhenAvailable") == "true"
    assert _text(root, ".//task:RunOnlyIfNetworkAvailable") == "true"
    assert root.find(".//task:RestartOnFailure", NAMESPACE) is None
    assert _text(root, ".//task:ExecutionTimeLimit") == "PT15M"
    assert _text(root, ".//task:Priority") == "7"
    assert _text(root, ".//task:Settings/task:Enabled") == "false"
    assert _text(root, ".//task:AllowStartOnDemand") == "false"

    # Triggers
    assert _text(root, ".//task:StartBoundary") == "2026-07-18T00:05:00Z"
    assert _text(root, ".//task:Interval") == "PT1H"


def test_task_xml_actions() -> None:
    root = ET.parse(SCHEDULE).getroot()
    arguments = _text(root, ".//task:Arguments")
    command = _text(root, ".//task:Command")
    working_dir = _text(root, ".//task:WorkingDirectory")

    assert command == "powershell.exe"
    assert "run_v535_unattended_readonly.ps1" in arguments
    assert "-Mode run_once" in arguments
    assert "-SchedulerEnabled" in arguments
    assert "-MarketDataReadAuthorized" in arguments
    assert "-PaperBrokerReadAuthorized" in arguments
    assert "-AllowNetwork" in arguments
    assert "%REPO_ROOT%" in arguments
    assert working_dir == "%REPO_ROOT%"
    assert "ALPACA_API_KEY" not in arguments
    assert "ALPACA_SECRET_KEY" not in arguments


def test_registration_helper_preview_runs_successfully() -> None:
    script_path = PROJECT_ROOT / "scripts" / "register_crypto_tournament_v2_oos_scheduler_task.ps1"
    
    # Run in preview mode (default, no switches)
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    
    assert result.returncode == 0
    assert "SCHEDULED TASK REGISTRATION PREVIEW" in result.stdout
    assert "crypto-tournament-v2-oos-scheduler" in result.stdout
    assert "Note: No task was registered on the machine" in result.stdout


def _text(root: ET.Element, path: str) -> str:
    element = root.find(path, NAMESPACE)
    assert element is not None
    assert element.text is not None
    return element.text
