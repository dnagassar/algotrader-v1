from __future__ import annotations

from datetime import UTC, datetime, timedelta

from algotrader.execution.durable_cancel import (
    DurableCancelCoordinator,
    DurableCancelEvidence,
    DurableCancelIdentity,
    DurableCancelLease,
    DurableCancelObservation,
)
from algotrader.execution.order_journal import (
    CancelJournalState,
    SqliteOrderJournal,
)


NOW = datetime(2026, 7, 12, 14, 0, tzinfo=UTC)


def test_observed_cancel_is_persisted_and_callback_runs_once(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableCancelEvidence(True, True),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=lambda: calls.append("cancel") or {"status": "canceled"},
        observe=lambda response: DurableCancelObservation(response["status"]),
    )

    assert outcome.observed is True
    assert outcome.broker_called is True
    assert outcome.record is not None
    assert outcome.record.state is CancelJournalState.CANCELED
    assert calls == ["cancel"]


def test_cancel_not_allowed_leaves_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableCancelEvidence(False, True),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "cancel_not_allowed"
    assert calls == []
    assert coordinator.journal.get_cancel_intent(
        identity.cancel_intent_id
    ).state is CancelJournalState.RESERVED


def test_stale_snapshot_leaves_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableCancelEvidence(True, False),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "required_snapshot_not_fresh"
    assert calls == []


def test_operator_pause_and_stop_leave_callback_untouched(tmp_path) -> None:
    for stop_requested in (False, True):
        coordinator, identity, lease = _prepared(
            tmp_path / ("stop" if stop_requested else "pause")
        )
        coordinator.journal.set_runtime_control(
            trading_enabled=stop_requested,
            reason="operator control",
            occurred_at=NOW,
            stop_requested=stop_requested,
        )
        calls: list[str] = []

        outcome = coordinator.execute(
            identity=identity,
            lease=lease,
            evidence=DurableCancelEvidence(True, True),
            occurred_at=NOW + timedelta(seconds=1),
            cancel=lambda: calls.append("cancel"),
            observe=lambda _: DurableCancelObservation("canceled"),
        )

        assert outcome.status == "blocked"
        assert outcome.blocker == (
            "stop_requested" if stop_requested else "trading_disabled"
        )
        assert calls == []


def test_stale_fencing_token_leaves_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    stale = DurableCancelLease(
        lease_name=lease.lease_name,
        owner_run_id=lease.owner_run_id,
        lease_token="stale-token",
        fencing_generation=lease.fencing_generation,
    )
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=stale,
        evidence=DurableCancelEvidence(True, True),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "runtime_lease_fencing_mismatch"
    assert calls == []


def test_cancel_exception_is_redacted_and_persisted_unknown(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    error = RuntimeError("secret-value")

    def _raise() -> None:
        raise error

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableCancelEvidence(True, True),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=_raise,
        observe=lambda _: DurableCancelObservation("canceled"),
        sanitize_exception=lambda exc: str(exc).replace(
            "secret-value", "<redacted>"
        ),
    )

    reopened = SqliteOrderJournal(coordinator.journal.path).get_cancel_intent(
        identity.cancel_intent_id
    )
    assert outcome.ambiguous is True
    assert outcome.exception is error
    assert outcome.safe_error_message == "<redacted>"
    assert reopened is not None
    assert reopened.state is CancelJournalState.UNKNOWN
    assert reopened.safe_to_recancel is False


def test_observation_failure_is_persisted_unknown(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableCancelEvidence(True, True),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=lambda: {"status": "canceled"},
        observe=lambda _: (_ for _ in ()).throw(RuntimeError("mapping failed")),
    )

    assert outcome.ambiguous is True
    assert outcome.broker_called is True
    assert outcome.response == {"status": "canceled"}
    assert outcome.record is not None
    assert outcome.record.state is CancelJournalState.UNKNOWN


def test_identity_mismatch_leaves_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    mismatched = DurableCancelIdentity(
        cancel_intent_id=identity.cancel_intent_id,
        client_order_id=identity.client_order_id,
        broker_order_id="different-broker-order",
        reservation_run_id=identity.reservation_run_id,
        reason=identity.reason,
    )
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=mismatched,
        lease=lease,
        evidence=DurableCancelEvidence(True, True),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "cancel_broker_order_identity_mismatch"
    assert calls == []


def test_crash_rerun_cannot_invoke_second_cancel(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    first_calls: list[str] = []
    first = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableCancelEvidence(True, True),
        occurred_at=NOW + timedelta(seconds=1),
        cancel=lambda: first_calls.append("cancel") or {"status": "accepted"},
        observe=lambda response: DurableCancelObservation(response["status"]),
    )
    reopened = DurableCancelCoordinator(SqliteOrderJournal(coordinator.journal.path))
    duplicate = reopened.reserve(identity, NOW + timedelta(seconds=61))
    rerun_lease = reopened.acquire_lease(
        lease_name="cancel-worker",
        owner_run_id="cancel-run-2",
        occurred_at=NOW + timedelta(seconds=61),
        ttl_seconds=60,
    )
    second_calls: list[str] = []
    second = reopened.execute(
        identity=identity,
        lease=rerun_lease,
        evidence=DurableCancelEvidence(True, True),
        occurred_at=NOW + timedelta(seconds=62),
        cancel=lambda: second_calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert first.observed is True
    assert first_calls == ["cancel"]
    assert duplicate.acquired is False
    assert duplicate.status == "existing_same_intent"
    assert duplicate.record.safe_to_recancel is False
    assert second.status == "blocked"
    assert second.blocker == "cancel_intent_not_cancel_ready"
    assert second_calls == []


def _prepared(tmp_path):  # noqa: ANN001
    journal = SqliteOrderJournal(tmp_path / "cancel.sqlite3")
    coordinator = DurableCancelCoordinator(journal)
    identity = DurableCancelIdentity(
        cancel_intent_id="cancel-broker-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
        reservation_run_id="cancel-run-1",
        reason="stale_open_order",
    )
    reservation = coordinator.reserve(identity, NOW)
    lease = coordinator.acquire_lease(
        lease_name="cancel-worker",
        owner_run_id=identity.reservation_run_id,
        occurred_at=NOW,
        ttl_seconds=60,
    )
    assert reservation.acquired is True
    assert lease.acquired is True
    return coordinator, identity, lease
