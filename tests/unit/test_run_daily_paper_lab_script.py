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
