from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEDULE = (
    PROJECT_ROOT
    / "docs"
    / "design"
    / "spy_eod_market_data_refresh_scheduled_task.xml"
)
NAMESPACE = {"task": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def test_spy_eod_refresh_schedule_runs_after_tiingo_correction_window() -> None:
    root = ET.parse(SCHEDULE).getroot()

    assert _text(root, ".//task:StartBoundary") == "2026-07-14T20:10:00"
    assert "America/New_York" in _text(root, ".//task:Description")
    days = {
        element.tag.rsplit("}", 1)[-1]
        for element in root.findall(".//task:DaysOfWeek/*", NAMESPACE)
    }
    assert days == {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    assert _text(root, ".//task:MultipleInstancesPolicy") == "IgnoreNew"
    assert _text(root, ".//task:StartWhenAvailable") == "true"
    assert _text(root, ".//task:RunOnlyIfNetworkAvailable") == "true"
    assert _text(root, ".//task:RestartOnFailure/task:Interval") == "PT15M"
    assert _text(root, ".//task:RestartOnFailure/task:Count") == "3"
    assert _text(root, ".//task:ExecutionTimeLimit") == "PT15M"


def test_spy_eod_refresh_schedule_is_one_shot_tiingo_only() -> None:
    root = ET.parse(SCHEDULE).getroot()
    arguments = _text(root, ".//task:Arguments")

    assert "refresh_spy_adjusted_data.ps1" in arguments
    assert "-Provider tiingo" in arguments
    assert "-Mode live_market_data_fetch" in arguments
    assert "-LiveMarketDataFetchAuthorized" in arguments
    assert "-RevisionLookbackDays 10" in arguments
    assert "-StartDate auto" in arguments
    assert "m446_spy_daily_tiingo_adjusted_canonical.csv" in arguments
    assert "tiingo_spy_adjusted_raw_latest.json" in arguments
    assert "run_spy_paper_mutation_supervisor.ps1" not in arguments
    assert "paper-autopilot-supervisor" not in arguments


def _text(root: ET.Element, path: str) -> str:
    element = root.find(path, NAMESPACE)
    assert element is not None
    assert element.text is not None
    return element.text
