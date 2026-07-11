from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.order_journal import (
    OrderJournalState,
    OrderReservation,
    SqliteOrderJournal,
)


NOW = datetime(2026, 7, 11, 14, 0, tzinfo=UTC)


def _reservation(
    *,
    plan_id: str = "plan-1",
    run_id: str = "run-1",
    notional: str = "25",
) -> OrderReservation:
    return OrderReservation(
        client_order_id="pa-spy-buy-1",
        execution_plan_id=plan_id,
        run_id=run_id,
        symbol="SPY",
        side="buy",
        quantity=None,
        notional=notional,
    )


def test_reservation_is_durable_and_duplicate_safe(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    journal = SqliteOrderJournal(path)

    first = journal.reserve(_reservation(), NOW)
    reopened = SqliteOrderJournal(path)
    second = reopened.reserve(_reservation(run_id="run-2"), NOW + timedelta(seconds=1))

    assert first.acquired is True
    assert first.record.state == OrderJournalState.RESERVED
    assert second.acquired is False
    assert second.status == "existing_same_request"
    assert second.record.run_id == "run-1"
    assert second.record.safe_to_resubmit is False


def test_client_order_id_conflict_fails_closed(tmp_path: Path) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")
    journal.reserve(_reservation(), NOW)

    conflict = journal.reserve(
        _reservation(plan_id="different-plan", notional="20"),
        NOW + timedelta(seconds=1),
    )

    assert conflict.acquired is False
    assert conflict.status == "client_order_id_conflict"
    assert conflict.record.execution_plan_id == "plan-1"


def test_ambiguous_submit_survives_restart_and_is_unresolved(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = SqliteOrderJournal(path)
    journal.reserve(_reservation(), NOW)
    journal.mark_submit_attempted("pa-spy-buy-1", NOW + timedelta(seconds=1))
    journal.mark_submit_ambiguous(
        "pa-spy-buy-1",
        NOW + timedelta(seconds=2),
        reason="timeout_without_response",
    )

    reopened = SqliteOrderJournal(path)
    record = reopened.get("pa-spy-buy-1")

    assert record is not None
    assert record.state == OrderJournalState.UNKNOWN
    assert record.ambiguity_reason == "timeout_without_response"
    assert record.terminal is False
    assert reopened.unresolved("SPY") == (record,)


def test_partial_then_terminal_fill_is_persisted(tmp_path: Path) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")
    journal.reserve(_reservation(), NOW)
    journal.mark_submit_attempted("pa-spy-buy-1", NOW + timedelta(seconds=1))

    partial = journal.record_broker_observation(
        "pa-spy-buy-1",
        NOW + timedelta(seconds=2),
        broker_order_id="broker-1",
        broker_status="partially_filled",
        filled_quantity="0.1",
        filled_average_price="100",
    )
    filled = journal.record_broker_observation(
        "pa-spy-buy-1",
        NOW + timedelta(seconds=3),
        broker_order_id="broker-1",
        broker_status="filled",
        filled_quantity="0.25",
        filled_average_price="100.05",
    )

    assert partial.state == OrderJournalState.PARTIALLY_FILLED
    assert partial.terminal is False
    assert filled.state == OrderJournalState.FILLED
    assert filled.terminal is True
    assert journal.unresolved("SPY") == ()


def test_terminal_state_cannot_regress_to_open(tmp_path: Path) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")
    journal.reserve(_reservation(), NOW)
    journal.mark_submit_attempted("pa-spy-buy-1", NOW + timedelta(seconds=1))
    journal.record_broker_observation(
        "pa-spy-buy-1",
        NOW + timedelta(seconds=2),
        broker_order_id="broker-1",
        broker_status="filled",
        filled_quantity="0.25",
        filled_average_price="100",
    )

    with pytest.raises(ValidationError, match="terminal"):
        journal.record_broker_observation(
            "pa-spy-buy-1",
            NOW + timedelta(seconds=3),
            broker_order_id="broker-1",
            broker_status="open",
            filled_quantity="0.25",
            filled_average_price="100",
        )


def test_operator_pause_is_durable_across_restart(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = SqliteOrderJournal(path)

    paused = journal.set_runtime_control(
        trading_enabled=False,
        reason="operator emergency stop",
        occurred_at=NOW,
    )
    reopened = SqliteOrderJournal(path).get_runtime_control()

    assert paused.trading_enabled is False
    assert paused.to_dict()["operator_paused"] is True
    assert reopened == paused

    resumed = SqliteOrderJournal(path).set_runtime_control(
        trading_enabled=True,
        reason="operator reviewed and resumed",
        occurred_at=NOW + timedelta(minutes=5),
    )

    assert resumed.trading_enabled is True
    assert resumed.reason == "operator reviewed and resumed"


def test_runtime_lease_blocks_concurrency_and_allows_expired_takeover(
    tmp_path: Path,
) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")

    first = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        occurred_at=NOW,
        ttl_seconds=60,
    )
    concurrent = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-2",
        occurred_at=NOW + timedelta(seconds=30),
        ttl_seconds=60,
    )
    takeover = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-2",
        occurred_at=NOW + timedelta(seconds=61),
        ttl_seconds=60,
    )

    assert first.acquired is True
    assert concurrent.acquired is False
    assert concurrent.blocker == "runtime_instance_already_active"
    assert takeover.acquired is True
    assert journal.release_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-2",
        lease_token=takeover.lease_token,
    ) is True


def test_order_journal_backup_and_restore(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    backup_path = tmp_path / "orders.sqlite3.bak"
    journal = SqliteOrderJournal(path)

    journal.reserve(_reservation(), NOW)
    journal.set_runtime_control(
        trading_enabled=False,
        reason="operator pause",
        occurred_at=NOW,
    )

    journal.backup(backup_path)
    assert backup_path.is_file()

    # Modify original
    journal.set_runtime_control(
        trading_enabled=True,
        reason="resume",
        occurred_at=NOW + timedelta(seconds=1),
    )

    # Restore backup
    journal.restore(backup_path)

    # Verify control state is restored to False
    control = journal.get_runtime_control()
    assert control.trading_enabled is False
    assert control.reason == "operator pause"


def test_lease_ownership_and_fencing(tmp_path: Path) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")

    # 1. Clean acquisition
    res1 = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        occurred_at=NOW,
        ttl_seconds=60,
    )
    assert res1.acquired is True
    assert res1.lease_token != ""
    assert res1.fencing_generation == 1

    # 2. Non-owner cannot release
    released = journal.release_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        lease_token="invalid-token",
    )
    assert released is False

    # 3. Nonexpired lease cannot be forcibly reclaimed by another owner
    res2 = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-2",
        occurred_at=NOW + timedelta(seconds=30),
        ttl_seconds=60,
    )
    assert res2.acquired is False
    assert res2.blocker == "runtime_instance_already_active"

    # 4. Heartbeat/renew requires matching token
    renew = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        occurred_at=NOW + timedelta(seconds=30),
        ttl_seconds=60,
        lease_token=res1.lease_token,
    )
    assert renew.acquired is True
    assert renew.lease_token == res1.lease_token
    assert renew.fencing_generation == 1

    # 5. Heartbeat/renew fails with mismatched token
    renew_fail = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        occurred_at=NOW + timedelta(seconds=30),
        ttl_seconds=60,
        lease_token="mismatched-token",
    )
    assert renew_fail.acquired is False

    # 6. Expired lease can be reclaimed, generation increments
    reclaim = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-3",
        occurred_at=NOW + timedelta(seconds=120),
        ttl_seconds=60,
    )
    assert reclaim.acquired is True
    assert reclaim.lease_token != res1.lease_token
    assert reclaim.fencing_generation == 2

    # 7. Owner can release its own lease
    released_ok = journal.release_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-3",
        lease_token=reclaim.lease_token,
    )
    assert released_ok is True


def test_release_preserves_monotonic_fencing_generation(tmp_path: Path) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")
    first = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="first",
        occurred_at=NOW,
        ttl_seconds=60,
    )
    assert journal.release_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="first",
        lease_token=first.lease_token,
    ) is True

    second = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="second",
        occurred_at=NOW + timedelta(seconds=1),
        ttl_seconds=60,
    )

    assert second.acquired is True
    assert second.fencing_generation == first.fencing_generation + 1


def test_actual_v1_to_v2_then_v3_migration_preserves_records(tmp_path: Path) -> None:
    path = tmp_path / "v1.sqlite3"
    _write_v1_journal(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO orders(
                client_order_id, execution_plan_id, run_id, symbol, side, quantity,
                notional, state, created_at, updated_at
            ) VALUES('legacy-order', 'legacy-plan', 'legacy-run', 'SPY', 'buy', NULL,
                     '25', 'reserved', ?, ?)
            """,
            (NOW.isoformat(), NOW.isoformat()),
        )
        connection.commit()

    journal = SqliteOrderJournal(path)
    journal.initialize()

    legacy = journal.get("legacy-order")
    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM journal_metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
        control_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(runtime_control)")
        }
        lease_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(runtime_leases)")
        }
        cycle_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'supervisor_cycles'"
        ).fetchone()

    assert legacy is not None and legacy.execution_plan_id == "legacy-plan"
    assert version == "3"
    assert {"stop_requested", "heartbeat_at"}.issubset(control_columns)
    assert {"lease_token", "fencing_generation"}.issubset(lease_columns)
    assert cycle_table is not None


def test_failed_v1_migration_rolls_back_and_source_remains_usable(tmp_path: Path) -> None:
    path = tmp_path / "bad-v1.sqlite3"
    _write_v1_journal(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "ALTER TABLE runtime_leases ADD COLUMN lease_token TEXT NOT NULL DEFAULT ''"
        )
        connection.execute(
            "INSERT INTO runtime_control(singleton_id, trading_enabled, reason, updated_at) VALUES(1, 0, 'paused', ?)",
            (NOW.isoformat(),),
        )
        connection.commit()

    with pytest.raises(ValidationError, match="schema migration failed"):
        SqliteOrderJournal(path).initialize()

    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM journal_metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
        paused = connection.execute(
            "SELECT trading_enabled, reason FROM runtime_control WHERE singleton_id = 1"
        ).fetchone()

    assert version == "1"
    assert paused == (0, "paused")


def test_future_and_corrupt_schema_versions_fail_closed(tmp_path: Path) -> None:
    future = tmp_path / "future.sqlite3"
    journal = SqliteOrderJournal(future)
    journal.initialize()
    with sqlite3.connect(future) as connection:
        connection.execute(
            "UPDATE journal_metadata SET value = '99' WHERE key = 'schema_version'"
        )
        connection.commit()
    with pytest.raises(ValidationError, match="unsupported"):
        SqliteOrderJournal(future).initialize()

    corrupt = tmp_path / "corrupt.sqlite3"
    with sqlite3.connect(corrupt) as connection:
        connection.execute("CREATE TABLE journal_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO journal_metadata(key, value) VALUES('schema_version', 'not-a-number')"
        )
        connection.commit()
    with pytest.raises(ValidationError, match="corrupt"):
        SqliteOrderJournal(corrupt).initialize()


def _write_v1_journal(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE journal_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO journal_metadata(key, value) VALUES('schema_version', '1');
            CREATE TABLE orders (
                client_order_id TEXT PRIMARY KEY, execution_plan_id TEXT NOT NULL,
                run_id TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
                quantity TEXT, notional TEXT, state TEXT NOT NULL,
                broker_order_id TEXT NOT NULL DEFAULT '', broker_status TEXT NOT NULL DEFAULT '',
                filled_quantity TEXT, filled_average_price TEXT,
                ambiguity_reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE order_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, client_order_id TEXT NOT NULL,
                event_type TEXT NOT NULL, state TEXT NOT NULL, occurred_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE runtime_control (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                trading_enabled INTEGER NOT NULL, reason TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE runtime_leases (
                lease_name TEXT PRIMARY KEY, owner_run_id TEXT NOT NULL,
                acquired_at TEXT NOT NULL, expires_at TEXT NOT NULL
            );
            """
        )
