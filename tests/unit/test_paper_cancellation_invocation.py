from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.durable_cancel import (
    DurableCancelCoordinator,
    DurableCancelObservation,
)
from algotrader.execution.order_journal import (
    CancelJournalState,
    OrderJournalRecord,
    OrderJournalState,
    SqliteOrderJournal,
)
from algotrader.execution.paper_cancellation_admission import (
    CANCELLATION_OPERATION,
    PAPER_CANCELLATION_MODE,
    PaperCancellationAdmissionRequest,
    build_operator_cancellation_authorization_evidence,
    evaluate_paper_cancellation_admission,
)
from algotrader.execution.paper_cancellation_handoff_preview import (
    DurableCancellationHandoffRequest,
    preview_durable_cancellation_handoff,
)
from algotrader.execution.paper_cancellation_invocation import (
    MAXIMUM_CANCELLATION_LEASE_TTL_SECONDS,
    PAPER_CANCELLATION_INVOCATION_LEASE_NAME,
    PAPER_CANCELLATION_INVOCATION_VERSION,
    PaperCancellationInvocationBlocker,
    PaperCancellationInvocationRequest,
    PaperCancellationInvocationStatus,
    invoke_admitted_paper_cancellation,
)
from algotrader.orchestration.cancellation_planning_flow import (
    build_cancellation_plan,
)
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationPlanningResult,
    CancellationPlanningStatus,
)


NOW = datetime(2026, 7, 13, 16, 0, tzinfo=UTC)


def _record() -> OrderJournalRecord:
    return OrderJournalRecord(
        client_order_id="client-1",
        execution_plan_id="execution-plan-1",
        run_id="reservation-run-1",
        symbol="SPY",
        side="buy",
        quantity=None,
        notional=Decimal("25"),
        state=OrderJournalState.ACCEPTED,
        broker_order_id="broker-1",
        broker_status="accepted",
        filled_quantity=Decimal("0"),
        filled_average_price=None,
        ambiguity_reason="",
        created_at=NOW - timedelta(minutes=30),
        updated_at=NOW - timedelta(minutes=1),
    )


def _handoff():  # noqa: ANN202
    record = _record()
    plan = build_cancellation_plan(
        client_order_id=record.client_order_id,
        broker_order_id=record.broker_order_id,
        symbol=record.symbol,
        broker_status=record.broker_status,
        observed_at=record.updated_at,
        reason="aged local order review",
    )
    planning = CancellationPlanningResult(
        status=CancellationPlanningStatus.PLANNED,
        plan=plan,
        blocker=None,
    )
    return preview_durable_cancellation_handoff(
        planning,
        record,
        DurableCancellationHandoffRequest(
            as_of=NOW,
            maximum_record_age_seconds=300,
            handoff_permitted=True,
        ),
    )


def _admission(*, authorized: bool = True):  # noqa: ANN202
    handoff = _handoff()
    authorization = None
    if authorized:
        assert handoff.identity is not None
        authorization = build_operator_cancellation_authorization_evidence(
            mode=PAPER_CANCELLATION_MODE,
            operation=CANCELLATION_OPERATION,
            source_plan_id=handoff.source_plan_id,
            cancel_intent_id=handoff.identity.cancel_intent_id,
            client_order_id=handoff.identity.client_order_id,
            broker_order_id=handoff.identity.broker_order_id,
            issued_at=NOW - timedelta(minutes=1),
            expires_at=NOW + timedelta(minutes=2),
            authorized=True,
        )
    return evaluate_paper_cancellation_admission(
        handoff,
        authorization,
        PaperCancellationAdmissionRequest(
            evaluated_at=NOW,
            trading_enabled=True,
            stop_requested=False,
            snapshot_fresh=True,
        ),
    )


def _request(admission, **changes: object):  # noqa: ANN001, ANN202
    values: dict[str, object] = {
        "expected_admission_id": admission.admission_id,
        "occurred_at": NOW + timedelta(seconds=1),
        "lease_ttl_seconds": 60,
        "snapshot_fresh": True,
        "invocation_permitted": True,
        "lease_token": "deterministic-test-token",
    }
    values.update(changes)
    return PaperCancellationInvocationRequest(**values)  # type: ignore[arg-type]


def _coordinator(tmp_path) -> DurableCancelCoordinator:  # noqa: ANN001
    return DurableCancelCoordinator(SqliteOrderJournal(tmp_path / "cancel.sqlite3"))


def test_exact_admission_invokes_durable_callback_once_and_releases_lease(
    tmp_path,
) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)
    calls: list[str] = []

    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: calls.append("cancel") or {"status": "canceled"},
        observe=lambda response: DurableCancelObservation(response["status"]),
    )

    assert result.status is PaperCancellationInvocationStatus.OBSERVED
    assert result.blocker == ""
    assert result.broker_called is True
    assert result.reservation_acquired is True
    assert result.lease_acquired is True
    assert result.lease_released is True
    assert result.record_state == CancelJournalState.CANCELED.value
    assert calls == ["cancel"]
    assert admission.identity is not None
    persisted = coordinator.journal.get_cancel_intent(
        admission.identity.cancel_intent_id
    )
    assert persisted is not None
    assert persisted.state is CancelJournalState.CANCELED

    payload = result.to_dict()
    assert payload["invocation_version"] == PAPER_CANCELLATION_INVOCATION_VERSION
    assert payload["source_admission_id"] == admission.admission_id
    assert payload["source_authorization_id"] == admission.authorization_id
    assert payload["broker_callback_invoked"] is True
    assert payload["live_authorized"] is False
    assert payload["no_submit"] is True
    assert "response" not in payload
    assert "exception" not in payload
    assert "lease_token" not in payload


@pytest.mark.parametrize(
    ("authorized", "changes", "expected"),
    [
        (
            False,
            {},
            PaperCancellationInvocationBlocker.ADMISSION_NOT_ADMITTED,
        ),
        (
            True,
            {"expected_admission_id": "wrong-admission"},
            PaperCancellationInvocationBlocker.ADMISSION_ID_MISMATCH,
        ),
        (
            True,
            {"invocation_permitted": False},
            PaperCancellationInvocationBlocker.INVOCATION_NOT_PERMITTED,
        ),
        (
            True,
            {"snapshot_fresh": False},
            PaperCancellationInvocationBlocker.SNAPSHOT_NOT_FRESH,
        ),
        (
            True,
            {"occurred_at": NOW - timedelta(seconds=1)},
            PaperCancellationInvocationBlocker.INVOCATION_BEFORE_ADMISSION,
        ),
        (
            True,
            {"occurred_at": NOW + timedelta(minutes=2)},
            PaperCancellationInvocationBlocker.AUTHORIZATION_NOT_CURRENT,
        ),
    ],
)
def test_every_pre_invocation_gate_blocks_without_journal_or_callback(
    tmp_path,
    authorized: bool,
    changes: dict[str, object],
    expected: PaperCancellationInvocationBlocker,
) -> None:  # noqa: ANN001
    admission = _admission(authorized=authorized)
    coordinator = _coordinator(tmp_path)
    calls: list[str] = []

    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission, **changes),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert result.status is PaperCancellationInvocationStatus.BLOCKED
    assert result.blocker == expected.value
    assert result.coordinator_invoked is False
    assert result.broker_called is False
    assert calls == []
    assert coordinator.journal.cancel_intents() == ()


def test_callback_validation_precedes_every_journal_mutation(tmp_path) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)

    with pytest.raises(ValidationError, match="cancel and observe"):
        invoke_admitted_paper_cancellation(
            admission,
            coordinator,
            _request(admission),
            cancel=object(),  # type: ignore[arg-type]
            observe=lambda _: DurableCancelObservation("canceled"),
        )
    with pytest.raises(ValidationError, match="sanitize_exception"):
        invoke_admitted_paper_cancellation(
            admission,
            coordinator,
            _request(admission),
            cancel=lambda: None,
            observe=lambda _: DurableCancelObservation("canceled"),
            sanitize_exception=object(),  # type: ignore[arg-type]
        )

    assert coordinator.journal.cancel_intents() == ()


def test_current_runtime_pause_still_blocks_after_valid_admission(tmp_path) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)
    coordinator.journal.set_runtime_control(
        trading_enabled=False,
        reason="operator pause after admission",
        occurred_at=NOW,
        stop_requested=False,
    )
    calls: list[str] = []

    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert result.status is PaperCancellationInvocationStatus.BLOCKED
    assert result.blocker == "trading_disabled"
    assert result.coordinator_invoked is True
    assert result.lease_released is True
    assert result.broker_called is False
    assert calls == []


def test_runtime_lease_contention_blocks_callback(tmp_path) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)
    held = coordinator.acquire_lease(
        lease_name=PAPER_CANCELLATION_INVOCATION_LEASE_NAME,
        owner_run_id="other-run",
        occurred_at=NOW,
        ttl_seconds=60,
        lease_token="other-token",
    )
    assert held.acquired is True
    calls: list[str] = []

    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert result.status is PaperCancellationInvocationStatus.BLOCKED
    assert result.coordinator_invoked is True
    assert result.reservation_status == "reserved"
    assert result.lease_acquired is False
    assert result.broker_called is False
    assert calls == []


def test_reservation_failure_is_typed_and_never_calls_callback(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)
    calls: list[str] = []

    def fail_reservation(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("journal unavailable")

    monkeypatch.setattr(coordinator, "reserve", fail_reservation)
    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert result.status is PaperCancellationInvocationStatus.BLOCKED
    assert result.blocker == (
        PaperCancellationInvocationBlocker.DURABLE_RESERVATION_FAILED.value
    )
    assert result.authorization_current is True
    assert result.error_type == "RuntimeError"
    assert result.broker_called is False
    assert calls == []


def test_lease_failure_preserves_reservation_and_never_calls_callback(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)
    calls: list[str] = []

    def fail_lease(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("lease unavailable")

    monkeypatch.setattr(coordinator, "acquire_lease", fail_lease)
    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert result.status is PaperCancellationInvocationStatus.BLOCKED
    assert result.blocker == (
        PaperCancellationInvocationBlocker.DURABLE_LEASE_FAILED.value
    )
    assert result.authorization_current is True
    assert result.reservation_status == "reserved"
    assert result.reservation_acquired is True
    assert result.error_type == "RuntimeError"
    assert result.broker_called is False
    assert calls == []


def test_release_failure_preserves_observed_outcome(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)

    def fail_release(_lease):  # noqa: ANN001, ANN202
        raise RuntimeError("release unavailable")

    monkeypatch.setattr(coordinator, "release_lease", fail_release)
    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: {"status": "canceled"},
        observe=lambda response: DurableCancelObservation(response["status"]),
    )

    assert result.status is PaperCancellationInvocationStatus.OBSERVED
    assert result.broker_called is True
    assert result.lease_acquired is True
    assert result.lease_released is False
    assert result.lease_release_error_type == "RuntimeError"


def test_crash_safe_rerun_cannot_invoke_second_callback(tmp_path) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)
    first_calls: list[str] = []
    first = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: first_calls.append("cancel") or {"status": "canceled"},
        observe=lambda response: DurableCancelObservation(response["status"]),
    )
    reopened = DurableCancelCoordinator(SqliteOrderJournal(coordinator.journal.path))
    second_calls: list[str] = []
    second = invoke_admitted_paper_cancellation(
        admission,
        reopened,
        _request(
            admission,
            occurred_at=NOW + timedelta(seconds=2),
            lease_token="rerun-token",
        ),
        cancel=lambda: second_calls.append("cancel"),
        observe=lambda _: DurableCancelObservation("canceled"),
    )

    assert first.status is PaperCancellationInvocationStatus.OBSERVED
    assert first_calls == ["cancel"]
    assert second.status is PaperCancellationInvocationStatus.BLOCKED
    assert second.blocker == "cancel_intent_not_cancel_ready"
    assert second.reservation_status == "existing_same_intent"
    assert second.broker_called is False
    assert second_calls == []


def test_cancel_exception_is_ambiguous_redacted_and_lease_released(tmp_path) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)

    def fail_cancel() -> None:
        raise RuntimeError("secret-value")

    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=fail_cancel,
        observe=lambda _: DurableCancelObservation("canceled"),
        sanitize_exception=lambda exc: str(exc).replace(
            "secret-value",
            "<redacted>",
        ),
    )

    assert result.status is PaperCancellationInvocationStatus.AMBIGUOUS
    assert result.blocker == "cancel_response_ambiguous"
    assert result.broker_called is True
    assert result.safe_error_message == "<redacted>"
    assert result.record_state == CancelJournalState.UNKNOWN.value
    assert result.lease_released is True


def test_observation_failure_is_ambiguous_and_not_retried(tmp_path) -> None:  # noqa: ANN001
    admission = _admission()
    coordinator = _coordinator(tmp_path)
    calls: list[str] = []

    result = invoke_admitted_paper_cancellation(
        admission,
        coordinator,
        _request(admission),
        cancel=lambda: calls.append("cancel") or {"status": "canceled"},
        observe=lambda _: (_ for _ in ()).throw(RuntimeError("mapping failed")),
    )

    assert result.status is PaperCancellationInvocationStatus.AMBIGUOUS
    assert result.blocker == "cancel_observation_persistence_failed"
    assert result.broker_called is True
    assert result.record_state == CancelJournalState.UNKNOWN.value
    assert calls == ["cancel"]


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_admission_id": ""},
        {"occurred_at": NOW.replace(tzinfo=None)},
        {"occurred_at": object()},
        {"lease_ttl_seconds": 0},
        {"lease_ttl_seconds": MAXIMUM_CANCELLATION_LEASE_TTL_SECONDS + 1},
        {"lease_ttl_seconds": True},
        {"snapshot_fresh": 1},
        {"invocation_permitted": 1},
        {"lease_token": ""},
    ],
)
def test_invocation_request_rejects_implicit_or_invalid_gate_evidence(
    changes: dict[str, object],
) -> None:
    admission = _admission()
    with pytest.raises(ValidationError):
        _request(admission, **changes)


def test_admission_carries_immutable_authorization_validity_for_invocation() -> None:
    admission = _admission()

    assert admission.authorization_issued_at == NOW - timedelta(minutes=1)
    assert admission.authorization_expires_at == NOW + timedelta(minutes=2)
    assert admission.to_dict()["authorization_issued_at"] == (
        NOW - timedelta(minutes=1)
    ).isoformat()
    assert admission.to_dict()["authorization_expires_at"] == (
        NOW + timedelta(minutes=2)
    ).isoformat()
    with pytest.raises(FrozenInstanceError):
        admission.authorization_expires_at = NOW  # type: ignore[misc]
    with pytest.raises(ValidationError, match="validity"):
        replace(admission, authorization_expires_at=NOW)
