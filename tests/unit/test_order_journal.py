from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

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


def test_force_release_runtime_lease(tmp_path: Path) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")
    journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        occurred_at=NOW,
        ttl_seconds=60,
    )

    # Force release
    released = journal.force_release_runtime_lease(lease_name="paper-autopilot")
    assert released is True

    # Check if we can acquire again with different owner
    second = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-2",
        occurred_at=NOW,
        ttl_seconds=60,
    )
    assert second.acquired is True
