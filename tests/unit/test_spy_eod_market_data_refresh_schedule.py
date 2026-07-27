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
WRAPPER = PROJECT_ROOT / "scripts" / "run_spy_read_only_network_executor.ps1"
NAMESPACE = {"task": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def test_spy_eod_refresh_schedule_supports_powershell_string_registration() -> None:
    declaration = SCHEDULE.read_text(encoding="utf-8").splitlines()[0]

    assert declaration == '<?xml version="1.0"?>'


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


def test_spy_eod_refresh_schedule_is_isolated_and_drives_the_ledgered_seam() -> None:
    root = ET.parse(SCHEDULE).getroot()
    arguments = _text(root, ".//task:Arguments")

    # V5.51 repointed the unattended path from the bare adapter script to the
    # seam wrapper, so the template's own RestartOnFailure retries are subject
    # to the seam's four-attempt-per-session ledger cap instead of bypassing it
    # with no shared attempt memory. The refresh parameters this test used to
    # read off the command line now live in the seam's frozen
    # ETFAdjustedDataRefreshConfig -- see
    # test_autonomy_read_only_network_executor.py::
    # test_seam_freezes_the_read_only_tiingo_refresh_configuration.
    assert "run_spy_read_only_network_executor.ps1" in arguments
    assert "refresh_spy_adjusted_data.ps1" not in arguments
    assert "run_spy_paper_mutation_supervisor.ps1" not in arguments
    assert "paper-autopilot-supervisor" not in arguments


def test_spy_eod_refresh_wrapper_invokes_the_seam_with_one_utc_capture() -> None:
    wrapper = WRAPPER.read_text(encoding="utf-8")

    # The contract freezes the invocation form as PowerShell's call operator
    # against the literal captured string, so the timestamp reaches Python as
    # one argument exactly as captured.
    assert (
        "& python -m algotrader.execution.autonomy_read_only_network_executor"
        " --as-of $asOfUtc --apply --format json"
    ) in wrapper
    # Exactly one timestamp source, captured once: a second resolution inside
    # the Python process could straddle the session cutoff and silently target
    # a different NYSE session than the one the wrapper started for.
    assert wrapper.count("UtcNow") == 1
    assert "Get-Date" not in wrapper
    # The wrapper carries no credential of its own; the seam resolves it.
    assert "TIINGO_API_KEY" not in wrapper
    assert "run_spy_paper_mutation_supervisor" not in wrapper


def _text(root: ET.Element, path: str) -> str:
    element = root.find(path, NAMESPACE)
    assert element is not None
    assert element.text is not None
    return element.text
