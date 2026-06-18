from __future__ import annotations

from pathlib import Path


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
        "latest_run.json",
        "data_refresh_bridge.json",
        "data_refresh_dry_run.json",
        "data_refresh_operator_checklist.md",
    )
    for fragment in expected_fragments:
        assert fragment in script
