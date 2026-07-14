from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
    CancellationReconciliationObservation,
    CancellationReconciliationStatus,
    reconcile_unresolved_cancellation,
)
from algotrader.execution.order_journal import (
    CancelIntent,
    CancelJournalState,
    OrderJournalState,
    OrderReservation,
    SqliteOrderJournal,
)


NOW = datetime(2026, 7, 13, 15, 0, tzinfo=UTC)


def _identity(*, broker_order_id: str = "broker-1") -> CancellationReconciliationIdentity:
    return CancellationReconciliationIdentity(
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id=broker_order_id,
    )


def _observation(
    *,
    broker_order_id: str = "broker-1",
    broker_status: str = "canceled",
    observed_at: datetime = NOW + timedelta(seconds=10),
    filled_quantity: str | None = "0",
    filled_average_price: str | None = None,
) -> CancellationReconciliationObservation:
    return CancellationReconciliationObservation(
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id=broker_order_id,
        broker_status=broker_status,
        observed_at=observed_at,
        filled_quantity=filled_quantity,
        filled_average_price=filled_average_price,
    )


def _seed_unresolved(
    path: Path,
    *,
    order_broker_id: str = "broker-1",
    cancel_broker_id: str = "broker-1",
    mark_ambiguous: bool = True,
) -> SqliteOrderJournal:
    journal = SqliteOrderJournal(path)
    journal.reserve(
        OrderReservation(
            client_order_id="client-order-1",
            execution_plan_id="plan-1",
            run_id="order-run-1",
            symbol="SPY",
            side="buy",
            quantity=None,
            notional="25",
        ),
        NOW,
    )
    journal.record_broker_observation(
        "client-order-1",
        NOW + timedelta(seconds=1),
        broker_order_id=order_broker_id,
        broker_status="accepted",
        filled_quantity="0",
    )
    journal.reserve_cancel_intent(
        CancelIntent(
            cancel_intent_id="cancel-intent-1",
            client_order_id="client-order-1",
            broker_order_id=cancel_broker_id,
            run_id="cancel-run-1",
            reason="stale_open_order",
        ),
        NOW + timedelta(seconds=2),
    )
    lease = journal.acquire_runtime_lease(
        lease_name="cancel-worker",
        owner_run_id="cancel-run-1",
        occurred_at=NOW + timedelta(seconds=2),
        ttl_seconds=60,
        lease_token="lease-token-1",
    )
    journal.claim_pre_mutation_cancel(
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id=cancel_broker_id,
        reservation_run_id="cancel-run-1",
        lease_name=lease.lease_name,
        lease_owner_run_id=lease.owner_run_id,
        lease_token=lease.lease_token,
        fencing_generation=lease.fencing_generation,
        cancel_allowed=True,
        snapshot_fresh=True,
        occurred_at=NOW + timedelta(seconds=3),
    )
    journal.release_runtime_lease(
        lease_name=lease.lease_name,
        owner_run_id=lease.owner_run_id,
        lease_token=lease.lease_token,
    )
    if mark_ambiguous:
        journal.mark_cancel_ambiguous(
            "cancel-intent-1",
            NOW + timedelta(seconds=4),
            reason="timeout_without_response",
        )
    return journal


def test_exact_canceled_observation_converges_both_journals_atomically(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _seed_unresolved(path)

    result = reconcile_unresolved_cancellation(
        journal,
        _identity(),
        _observation(),
    )

    assert result.status is CancellationReconciliationStatus.CONVERGED
    assert result.blocker == ""
    assert result.local_journal_updated is True
    assert result.order_record is not None
    assert result.order_record.state is OrderJournalState.CANCELED
    assert result.order_record.broker_order_id == "broker-1"
    assert result.cancel_record is not None
    assert result.cancel_record.state is CancelJournalState.CANCELED
    assert result.cancel_record.broker_status == "canceled"
    assert result.cancel_record.ambiguity_reason == ""
    assert SqliteOrderJournal(path).get("client-order-1") == result.order_record
    assert (
        SqliteOrderJournal(path).get_cancel_intent("cancel-intent-1")
        == result.cancel_record
    )
    assert SqliteOrderJournal(path).unresolved_cancel_intents() == ()

    payload = result.to_dict()
    assert payload["injected_observation_count"] == 1
    assert payload["injected_observation_consumed"] is True
    assert payload["retry_permitted"] is False
    assert payload["safe_to_recancel"] is False
    for field_name in (
        "broker_read_performed",
        "broker_mutation_performed",
        "network_accessed",
        "credentials_accessed",
        "runtime_control_changed",
        "target_selection_performed",
        "submit_attempted",
        "cancel_attempted",
        "replace_attempted",
        "close_attempted",
        "liquidation_attempted",
        "live_authorized",
    ):
        assert payload[field_name] is False


@pytest.mark.parametrize(
    ("field_name", "changed_value", "blocker"),
    (
        (
            "cancel_intent_id",
            "different-cancel-intent",
            "cancel_intent_identity_mismatch",
        ),
        (
            "client_order_id",
            "different-client-order",
            "client_order_identity_mismatch",
        ),
        (
            "broker_order_id",
            "different-broker-order",
            "broker_order_identity_mismatch",
        ),
    ),
)
def test_injected_observation_requires_all_three_exact_identities(
    tmp_path: Path,
    field_name: str,
    changed_value: str,
    blocker: str,
) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    before_order = journal.get("client-order-1")
    before_cancel = journal.get_cancel_intent("cancel-intent-1")
    observation = replace(_observation(), **{field_name: changed_value})

    result = reconcile_unresolved_cancellation(
        journal,
        _identity(),
        observation,
    )

    assert result.status is CancellationReconciliationStatus.BLOCKED
    assert result.blocker == blocker
    assert result.local_journal_updated is False
    assert journal.get("client-order-1") == before_order
    assert journal.get_cancel_intent("cancel-intent-1") == before_cancel


def test_local_order_and_cancel_identity_must_also_match_exactly(
    tmp_path: Path,
) -> None:
    journal = _seed_unresolved(
        tmp_path / "orders.sqlite3",
        order_broker_id="broker-1",
        cancel_broker_id="broker-2",
    )
    before_order = journal.get("client-order-1")
    before_cancel = journal.get_cancel_intent("cancel-intent-1")

    result = reconcile_unresolved_cancellation(
        journal,
        _identity(broker_order_id="broker-2"),
        _observation(broker_order_id="broker-2"),
    )

    assert result.status is CancellationReconciliationStatus.BLOCKED
    assert result.blocker == "order_broker_identity_mismatch"
    assert journal.get("client-order-1") == before_order
    assert journal.get_cancel_intent("cancel-intent-1") == before_cancel


def test_pending_cancel_and_filled_states_converge_deterministically(
    tmp_path: Path,
) -> None:
    pending = _seed_unresolved(tmp_path / "pending.sqlite3")
    pending_result = reconcile_unresolved_cancellation(
        pending,
        _identity(),
        _observation(broker_status="pending_cancel"),
    )

    assert pending_result.order_record is not None
    assert pending_result.order_record.state is OrderJournalState.OPEN
    assert pending_result.cancel_record is not None
    assert pending_result.cancel_record.state is CancelJournalState.CANCEL_ACCEPTED
    assert pending_result.cancel_record.safe_to_recancel is False

    filled = _seed_unresolved(tmp_path / "filled.sqlite3")
    filled_result = reconcile_unresolved_cancellation(
        filled,
        _identity(),
        _observation(
            broker_status="filled",
            filled_quantity="0.25",
            filled_average_price="100",
        ),
    )

    assert filled_result.order_record is not None
    assert filled_result.order_record.state is OrderJournalState.FILLED
    assert filled_result.cancel_record is not None
    assert filled_result.cancel_record.state is CancelJournalState.UNKNOWN
    assert filled_result.cancel_record.broker_status == "unknown"
    assert filled_result.cancel_record.ambiguity_reason == ""
    assert filled_result.to_dict()["retry_permitted"] is False


def test_reserved_terminal_and_stale_targets_are_not_reconciled(
    tmp_path: Path,
) -> None:
    reserved_path = tmp_path / "reserved.sqlite3"
    reserved = SqliteOrderJournal(reserved_path)
    reserved.reserve(
        OrderReservation(
            client_order_id="client-order-1",
            execution_plan_id="plan-1",
            run_id="order-run-1",
            symbol="SPY",
            side="buy",
            quantity=None,
            notional="25",
        ),
        NOW,
    )
    reserved.record_broker_observation(
        "client-order-1",
        NOW + timedelta(seconds=1),
        broker_order_id="broker-1",
        broker_status="accepted",
        filled_quantity="0",
    )
    reserved.reserve_cancel_intent(
        CancelIntent(
            cancel_intent_id="cancel-intent-1",
            client_order_id="client-order-1",
            broker_order_id="broker-1",
            run_id="cancel-run-1",
            reason="stale_open_order",
        ),
        NOW + timedelta(seconds=2),
    )

    reserved_result = reconcile_unresolved_cancellation(
        reserved,
        _identity(),
        _observation(),
    )
    assert reserved_result.blocker == "cancel_intent_not_reconciliation_ready"

    terminal = _seed_unresolved(tmp_path / "terminal.sqlite3")
    first = reconcile_unresolved_cancellation(
        terminal,
        _identity(),
        _observation(),
    )
    second = reconcile_unresolved_cancellation(
        terminal,
        _identity(),
        _observation(observed_at=NOW + timedelta(seconds=11)),
    )
    assert first.status is CancellationReconciliationStatus.CONVERGED
    assert second.status is CancellationReconciliationStatus.BLOCKED
    assert second.blocker == "cancel_intent_already_terminal"
    assert second.to_dict()["retry_permitted"] is False

    stale = _seed_unresolved(tmp_path / "stale.sqlite3")
    before_order = stale.get("client-order-1")
    before_cancel = stale.get_cancel_intent("cancel-intent-1")
    stale_result = reconcile_unresolved_cancellation(
        stale,
        _identity(),
        _observation(observed_at=NOW + timedelta(seconds=3)),
    )
    assert stale_result.blocker == "cancellation_reconciliation_observation_stale"
    assert stale.get("client-order-1") == before_order
    assert stale.get_cancel_intent("cancel-intent-1") == before_cancel


def test_reconciliation_preserves_paused_runtime_control(tmp_path: Path) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    paused = journal.set_runtime_control(
        trading_enabled=False,
        stop_requested=True,
        reason="operator_pause",
        occurred_at=NOW + timedelta(seconds=5),
    )

    result = reconcile_unresolved_cancellation(
        journal,
        _identity(),
        _observation(),
    )

    assert result.status is CancellationReconciliationStatus.CONVERGED
    assert journal.get_runtime_control() == paused
    assert result.to_dict()["runtime_control_changed"] is False


def test_reconciliation_contracts_are_immutable_and_validate_inputs() -> None:
    identity = _identity()
    observation = _observation(broker_status="OrderStatus.CANCELED")

    assert observation.broker_status == "canceled"
    with pytest.raises(FrozenInstanceError):
        identity.cancel_intent_id = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        replace(observation, observed_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError, match="non-negative"):
        replace(observation, filled_quantity="-0.01")
    with pytest.raises(ValidationError, match="greater than zero"):
        replace(observation, filled_average_price="0")
