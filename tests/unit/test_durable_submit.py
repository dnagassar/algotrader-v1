from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from algotrader.execution.durable_submit import (
    DurableBrokerObservation,
    DurableSubmitCoordinator,
    DurableSubmitEvidence,
    DurableSubmitIdentity,
    DurableSubmitLease,
)
from algotrader.execution.order_journal import OrderJournalState, SqliteOrderJournal


NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def test_observed_submit_is_claimed_and_persisted_once(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(True, True),
        occurred_at=NOW,
        submit=lambda: calls.append("submit") or {"status": "accepted"},
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
    )

    assert outcome.observed is True
    assert outcome.broker_called is True
    assert outcome.record is not None
    assert outcome.record.state is OrderJournalState.ACCEPTED
    assert calls == ["submit"]


def test_failed_evidence_leaves_submit_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(False, True),
        occurred_at=NOW,
        submit=lambda: calls.append("submit"),
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "canonical_risk_not_allowed"
    assert outcome.broker_called is False
    assert calls == []


def test_runtime_stop_leaves_submit_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    coordinator.journal.set_runtime_control(
        trading_enabled=True,
        reason="running",
        occurred_at=NOW,
        stop_requested=True,
    )
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(True, True),
        occurred_at=NOW,
        submit=lambda: calls.append("submit"),
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "stop_requested"
    assert calls == []


def test_runtime_pause_leaves_submit_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    coordinator.journal.set_runtime_control(
        trading_enabled=False,
        reason="operator pause",
        occurred_at=NOW,
    )
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(True, True),
        occurred_at=NOW,
        submit=lambda: calls.append("submit"),
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "trading_disabled"
    assert calls == []


def test_stale_snapshot_leaves_submit_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(True, False),
        occurred_at=NOW,
        submit=lambda: calls.append("submit"),
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "required_snapshot_not_fresh"
    assert calls == []


def test_stale_fencing_token_leaves_submit_callback_untouched(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    stale = DurableSubmitLease(
        lease_name=lease.lease_name,
        owner_run_id=lease.owner_run_id,
        lease_token="stale-token",
        fencing_generation=lease.fencing_generation,
    )
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=identity,
        lease=stale,
        evidence=DurableSubmitEvidence(True, True),
        occurred_at=NOW,
        submit=lambda: calls.append("submit"),
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "runtime_lease_fencing_mismatch"
    assert calls == []


def test_submit_exception_is_redacted_and_persisted_unknown(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)

    def _raise() -> None:
        raise RuntimeError("secret-value")

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(True, True),
        occurred_at=NOW,
        submit=_raise,
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
        sanitize_exception=lambda exc: str(exc).replace("secret-value", "<redacted>"),
    )

    assert outcome.ambiguous is True
    assert outcome.safe_error_message == "<redacted>"
    assert outcome.record is not None
    assert outcome.record.state is OrderJournalState.UNKNOWN


def test_observation_failure_is_persisted_unknown(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)

    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(True, True),
        occurred_at=NOW,
        submit=lambda: {"status": "accepted"},
        observe=lambda _: (_ for _ in ()).throw(RuntimeError("mapping failed")),
    )

    assert outcome.ambiguous is True
    assert outcome.blocker == "broker_observation_persistence_failed"
    assert outcome.record is not None
    assert outcome.record.state is OrderJournalState.UNKNOWN


def test_identity_mismatch_blocks_before_submit(tmp_path) -> None:
    coordinator, identity, lease = _prepared(tmp_path)
    mismatched = DurableSubmitIdentity(
        client_order_id=identity.client_order_id,
        execution_plan_id="different-plan",
        reservation_run_id=identity.reservation_run_id,
        symbol=identity.symbol,
        side=identity.side,
        quantity=identity.quantity,
        notional=identity.notional,
    )
    calls: list[str] = []

    outcome = coordinator.execute(
        identity=mismatched,
        lease=lease,
        evidence=DurableSubmitEvidence(True, True),
        occurred_at=NOW,
        submit=lambda: calls.append("submit"),
        observe=lambda _: DurableBrokerObservation("broker-1", "accepted"),
    )

    assert outcome.status == "blocked"
    assert outcome.blocker == "immutable_execution_plan_identity_mismatch"
    assert calls == []


def _prepared(tmp_path):
    coordinator = DurableSubmitCoordinator(
        SqliteOrderJournal(tmp_path / "orders.sqlite3")
    )
    identity = DurableSubmitIdentity(
        client_order_id="client-order-1",
        execution_plan_id="plan-1",
        reservation_run_id="run-1",
        symbol="SPY",
        side="buy",
        quantity=None,
        notional=Decimal("25"),
    )
    reservation = coordinator.reserve(identity, NOW)
    assert reservation.acquired is True
    lease = coordinator.acquire_lease(
        lease_name="test-submit",
        owner_run_id="run-1",
        occurred_at=NOW,
        ttl_seconds=60,
    )
    assert lease.acquired is True
    return coordinator, identity, lease
