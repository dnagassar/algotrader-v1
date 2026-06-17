from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DAILY_PAPER_LAB_SCRIPT = PROJECT_ROOT / "scripts" / "run_daily_paper_lab.ps1"


def test_run_daily_paper_lab_script_declares_broker_state_mode_scaffold() -> None:
    script = RUN_DAILY_PAPER_LAB_SCRIPT.read_text(encoding="utf-8")

    assert "[string]$BrokerStateMode = \"broker_state_not_observed\"" in script
    assert (
        "[ValidateSet(\"broker_state_not_observed\", \"offline_fixture\", "
        "\"alpaca_paper_read_only\")]"
    ) in script
    assert "--broker-state-mode\", $BrokerStateMode" in script
    assert "scaffold-only and performs no broker read" in script


def test_run_daily_paper_lab_script_preserves_offline_credential_precheck() -> None:
    script = RUN_DAILY_PAPER_LAB_SCRIPT.read_text(encoding="utf-8")

    assert "APP_PROFILE" in script
    assert "ALPACA_API_KEY" in script
    assert "ALPACA_API_SECRET_KEY" in script
    assert "ALPACA_SECRET_KEY" in script
    assert "APCA_API_KEY_ID" in script
    assert "APCA_API_SECRET_KEY" in script
    assert "Test-ProcessEnvironmentVariableLoaded" in script
    assert "Daily paper-lab assistant must run offline only without credentials" in script


def test_run_daily_paper_lab_script_prints_operator_entry_points() -> None:
    script = RUN_DAILY_PAPER_LAB_SCRIPT.read_text(encoding="utf-8")

    assert "Mission Control generated." in script
    assert "Open first: $IndexPath" in script
    assert "Operator review: $OperatorReviewPath" in script
    assert "Latest run summary: $LatestRunPath" in script
    assert "Validation: $ValidationPath" in script
    assert "Data refresh bridge: $DataRefreshBridgePath" in script
    assert "Data refresh checklist: $DataRefreshChecklistPath" in script
    assert "Paper submit authorized: false" in script
    assert "Live authorized: false" in script
    assert "Broker read performed: false" in script
    assert "Broker mutation performed: false" in script
    assert "Broker-state mode: $BrokerStateModeText" in script
    assert "latest_run.json" in script
    assert "data_refresh_bridge.json" in script
    assert "data_refresh_operator_checklist.md" in script
