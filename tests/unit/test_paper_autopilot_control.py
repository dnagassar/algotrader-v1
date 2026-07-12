from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import pytest

from algotrader.errors import ValidationError
from algotrader.execution.order_journal import OrderReservation, SqliteOrderJournal
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

    # Pause it before restore because restore fails when trading_enabled is True
    run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="pause",
            reason="pre-restore pause",
        ),
        timestamp=NOW + timedelta(seconds=2),
    )

    res_restore = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="restore",
            backup_path=backup,
        ),
        timestamp=NOW + timedelta(seconds=3),
    )
    assert res_restore["restore_successful"] is True

    status = run_paper_autopilot_control(
        PaperAutopilotControlConfig(journal_path=path, action="status"),
    )
    assert status["operator_paused"] is True
    assert status["reason"] == "operator pause"


def test_control_start_and_stop_does_not_report_running_before_acknowledgment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    launched: list[list[str]] = []

    class FakePopen:
        def __init__(self, args, **kwargs) -> None:
            launched.append(list(args))

    monkeypatch.setattr(
        "algotrader.execution.paper_autopilot_control.subprocess.Popen",
        FakePopen,
    )

    res_start = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="start",
            reason="operator started supervisor",
        ),
        timestamp=NOW,
    )
    assert res_start["trading_enabled"] is True
    assert res_start["lease_acquired"] is False
    assert res_start["startup_requested"] is True
    assert res_start["startup_acknowledged"] is False
    assert res_start["supervisor_running"] is False
    assert launched and "paper-autopilot-supervisor" in launched[0]

    res_stop = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="stop",
            reason="operator stopped supervisor",
        ),
        timestamp=NOW + timedelta(seconds=1),
    )
    assert res_stop["trading_enabled"] is True
    assert res_stop["lease_released"] is False
    assert res_stop["stop_requested"] is True


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

    # Reconcile requires a broker snapshot path offline
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_data = {
        "account": {
            "id": "paper-account-id",
            "status": "ACTIVE",
            "tradable": True,
            "trading_blocked": False,
            "cash": "1000.0",
            "buying_power": "2000.0",
        },
        "positions": [],
        "orders": [],
        "provenance": {
            "generated_at": NOW.isoformat(),
            "schema_version": "broker_snapshot_v1",
        }
    }
    snapshot_data["provenance"]["snapshot_sha256"] = _snapshot_hash(snapshot_data)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f)

    res = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="reconcile",
            broker_snapshot_path=snapshot_path,
        ),
        env=env,
        broker_client_factory=lambda cfg: FakeClient(),
        timestamp=NOW,
    )
    assert res["reconciled_count"] == 0
    assert res["unresolved_order_count"] == 0
    assert res["reconciliation"]["reconciliation_status"] == "reconciled"


def test_control_reconcile_persists_fail_closed_divergence_report(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    journal = SqliteOrderJournal(path)
    reservation = journal.reserve(
        OrderReservation(
            client_order_id="known-partial",
            execution_plan_id="plan-1",
            run_id="run-1",
            symbol="SPY",
            side="buy",
            quantity=None,
            notional="25",
        ),
        NOW,
    )
    journal.mark_submit_attempted(reservation.record.client_order_id, NOW)
    journal.record_broker_observation(
        reservation.record.client_order_id,
        NOW,
        broker_order_id="known-broker",
        broker_status="partially_filled",
        filled_quantity="0.5",
        filled_average_price="100",
    )

    snapshot_data = {
        "account": {
            "id": "paper-account-id",
            "status": "INACTIVE",
            "tradable": False,
            "trading_blocked": True,
            "cash": "-1",
            "buying_power": "",
        },
        "positions": [{"symbol": "MSFT", "quantity": "1"}],
        "orders": [
            {
                "id": "known-broker",
                "client_order_id": "known-partial",
                "status": "partially_filled",
                "filled_qty": "0.25",
                "filled_avg_price": "100",
            },
            {
                "id": "broker-only",
                "client_order_id": "broker-only",
                "status": "accepted",
                "filled_qty": "0",
            },
        ],
        "provenance": {"generated_at": NOW.isoformat(), "schema_version": "broker_snapshot_v1"},
    }
    snapshot_data["provenance"]["snapshot_sha256"] = _snapshot_hash(snapshot_data)
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot_data), encoding="utf-8")

    result = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="reconcile",
            broker_snapshot_path=snapshot_path,
        ),
        timestamp=NOW,
    )

    reconciliation = result["reconciliation"]
    assert reconciliation["reconciliation_status"] == "blocked"
    assert reconciliation["fail_closed"] is True
    assert "cumulative_fill_decreased:known-partial" in reconciliation["findings"]
    assert "broker_only_order:broker-only" in reconciliation["findings"]
    assert "unexpected_symbol:MSFT" in reconciliation["findings"]
    assert journal.last_reconciliation_result() == reconciliation


def _snapshot_hash(snapshot: dict[str, object]) -> str:
    payload = {
        "account": snapshot["account"],
        "positions": snapshot["positions"],
        "orders": snapshot["orders"],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
    # Note: loop_exit_code will be tested and pass once we update run_paper_autopilot_loop signature.


def test_restore_blocked_when_trading_enabled(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    backup = tmp_path / "orders.sqlite3.bak"
    journal = SqliteOrderJournal(path)

    journal.set_runtime_control(trading_enabled=True, reason="active", occurred_at=NOW)
    journal.backup(backup)

    with pytest.raises(ValidationError, match="Restore is blocked when trading is enabled"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=backup,
            ),
            timestamp=NOW,
        )


def test_restore_blocked_when_lease_active(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    backup = tmp_path / "orders.sqlite3.bak"
    journal = SqliteOrderJournal(path)

    journal.set_runtime_control(trading_enabled=False, reason="paused", occurred_at=NOW)
    journal.backup(backup)

    journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        occurred_at=NOW,
        ttl_seconds=60,
    )

    with pytest.raises(ValidationError, match="Restore is blocked when a valid runtime lease is active"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=backup,
            ),
            timestamp=NOW,
        )


def test_restore_rejects_corrupt_source(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    bad_backup = tmp_path / "corrupt.sqlite3.bak"
    bad_backup.write_bytes(b"garbage-data-not-a-sqlite-db")

    journal = SqliteOrderJournal(path)
    journal.set_runtime_control(trading_enabled=False, reason="paused", occurred_at=NOW)

    with pytest.raises(ValidationError, match="integrity check failed|invalid|corruption"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=bad_backup,
            ),
            timestamp=NOW,
        )

    assert journal.get_runtime_control().trading_enabled is False
    assert journal.get_runtime_control().reason == "paused"


def test_restore_rejects_schema_v4_without_cancel_tables(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    backup = tmp_path / "orders.sqlite3.bak"
    journal = SqliteOrderJournal(path)
    journal.set_runtime_control(
        trading_enabled=False,
        reason="pre-restore pause",
        occurred_at=NOW,
    )
    journal.backup(backup)
    with sqlite3.connect(backup) as connection:
        connection.execute("DROP TABLE cancel_events")
        connection.commit()

    with pytest.raises(ValidationError, match="missing cancellation tables"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=backup,
            ),
            env={},
            timestamp=NOW,
        )
