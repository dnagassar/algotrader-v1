from datetime import UTC, datetime, timedelta
from pathlib import Path

from algotrader.execution.paper_autopilot_control import (
    PaperAutopilotControlConfig,
    run_paper_autopilot_control,
)


NOW = datetime(2026, 7, 11, 15, 0, tzinfo=UTC)


def test_pause_status_and_resume_are_durable_and_offline(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"

    paused = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="pause",
            reason="operator stop",
        ),
        timestamp=NOW,
    )
    status = run_paper_autopilot_control(
        PaperAutopilotControlConfig(journal_path=path, action="status"),
    )
    resumed = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="resume",
            reason="operator reviewed state",
        ),
        timestamp=NOW + timedelta(minutes=5),
    )

    assert paused["operator_paused"] is True
    assert status["operator_paused"] is True
    assert resumed["trading_enabled"] is True
    assert resumed["reason"] == "operator reviewed state"
    for result in (paused, status, resumed):
        assert result["network_access_attempted"] is False
        assert result["broker_access_attempted"] is False
        assert result["broker_mutation_performed"] is False
        assert result["live_authorized"] is False


def test_control_backup_and_restore(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    backup = tmp_path / "state" / "orders.sqlite3.bak"

    run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="pause",
            reason="operator pause",
        ),
        timestamp=NOW,
    )

    res_backup = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="backup",
            backup_path=backup,
        ),
        timestamp=NOW,
    )
    assert res_backup["backup_successful"] is True
    assert backup.is_file()

    run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="resume",
            reason="resume",
        ),
        timestamp=NOW + timedelta(seconds=1),
    )

    res_restore = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="restore",
            backup_path=backup,
        ),
        timestamp=NOW + timedelta(seconds=2),
    )
    assert res_restore["restore_successful"] is True

    status = run_paper_autopilot_control(
        PaperAutopilotControlConfig(journal_path=path, action="status"),
    )
    assert status["operator_paused"] is True
    assert status["reason"] == "operator pause"


def test_control_start_and_stop(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"

    res_start = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="start",
            reason="operator started supervisor",
        ),
        timestamp=NOW,
    )
    assert res_start["trading_enabled"] is True
    assert res_start["lease_acquired"] is True

    res_stop = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="stop",
            reason="operator stopped supervisor",
        ),
        timestamp=NOW + timedelta(seconds=1),
    )
    assert res_stop["trading_enabled"] is False
    assert res_stop["lease_released"] is True


class FakeClient:
    def get_account(self):
        class Account:
            id = "paper-account-id"
            status = "ACTIVE"
            currency = "USD"
            cash = "1000.0"
            buying_power = "2000.0"
            equity = "1000.0"
            last_equity = "1000.0"
            tradable = True
            trading_blocked = False
        return Account()
    def get_positions(self):
        return []
    def get_orders(self, query=None):
        return []


def test_control_reconcile(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "fake_key",
        "ALPACA_SECRET_KEY": "fake_secret",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "paper-account-id",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
    }

    res = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="reconcile",
        ),
        env=env,
        broker_client_factory=lambda cfg: FakeClient(),
        timestamp=NOW,
    )
    assert res["reconciled_count"] == 0
    assert res["unresolved_order_count"] == 0


def test_control_one_cycle(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "fake_key",
        "ALPACA_SECRET_KEY": "fake_secret",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "paper-account-id",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
    }

    bars_file = tmp_path / "bars.csv"
    bars_file.write_text(
        "date,open,high,low,close,volume\n2026-07-10,100,101,99,100.5,1000\n",
        encoding="utf-8",
    )

    def dummy_lab_runner(cfg):
        return {
            "preview_decision": "hold",
            "blocker_status": "none",
            "next_operator_action": "continue",
            "latest_bar_date": "2026-07-10",
            "data_freshness_status": "accepted_data_current",
            "data_refresh_status": "no_refresh_required",
            "expected_latest_bar_date": "2026-07-10",
        }

    res = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="one-cycle",
            bars_csv=bars_file,
            output_root=tmp_path / "latest",
        ),
        env=env,
        broker_client_factory=lambda cfg: FakeClient(),
        daily_lab_runner=dummy_lab_runner,
        timestamp=NOW,
    )
    assert "one_cycle_result" in res
    assert res["one_cycle_result"]["loop_exit_code"] == 0
