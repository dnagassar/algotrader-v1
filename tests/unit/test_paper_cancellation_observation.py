from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
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
from algotrader.execution.paper_cancellation_observation import (
    MAXIMUM_OBSERVATION_AUTHORIZATION_TTL_SECONDS,
    PAPER_CANCELLATION_OBSERVATION_MODE,
    PAPER_CANCELLATION_OBSERVATION_OPERATION,
    PaperCancellationBrokerOrderObservation,
    PaperCancellationObservationAuthorization,
    PaperCancellationObservationBlocker,
    PaperCancellationObservationRequest,
    PaperCancellationObservationResult,
    PaperCancellationObservationStatus,
    build_paper_cancellation_observation_authorization,
    observe_exact_paper_cancellation,
)


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
EXPECTED_ACCOUNT_ID = "expected-paper-account-sensitive"


class FakeExactOrderReader:
    def __init__(
        self,
        observation: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self.observation = observation or _broker_observation()
        self.error = error
        self.calls: list[str] = []

    def __call__(self, broker_order_id: str) -> object:
        self.calls.append(broker_order_id)
        if self.error is not None:
            raise self.error
        return self.observation


def _identity(**changes: str) -> CancellationReconciliationIdentity:
    values = {
        "cancel_intent_id": "cancel-intent-1",
        "client_order_id": "client-order-1",
        "broker_order_id": "broker-order-1",
    }
    values.update(changes)
    return CancellationReconciliationIdentity(**values)


def _authorization(
    *,
    mode: str = PAPER_CANCELLATION_OBSERVATION_MODE,
    operation: str = PAPER_CANCELLATION_OBSERVATION_OPERATION,
    cancel_intent_id: str = "cancel-intent-1",
    client_order_id: str = "client-order-1",
    broker_order_id: str = "broker-order-1",
    issued_at: datetime = NOW,
    expires_at: datetime = NOW + timedelta(minutes=5),
    authorized: bool = True,
) -> PaperCancellationObservationAuthorization:
    return build_paper_cancellation_observation_authorization(
        mode=mode,
        operation=operation,
        cancel_intent_id=cancel_intent_id,
        client_order_id=client_order_id,
        broker_order_id=broker_order_id,
        issued_at=issued_at,
        expires_at=expires_at,
        authorized=authorized,
    )


def _request(
    authorization: PaperCancellationObservationAuthorization,
    **changes: object,
) -> PaperCancellationObservationRequest:
    values: dict[str, object] = {
        "expected_authorization_id": authorization.authorization_id,
        "occurred_at": NOW + timedelta(seconds=10),
        "expected_account_id": EXPECTED_ACCOUNT_ID,
        "observation_permitted": True,
        "network_access_permitted": True,
        "paper_profile_ready": True,
        "api_key_present": True,
        "secret_key_present": True,
        "paper_endpoint_validated": True,
        "live_endpoint_detected": False,
    }
    values.update(changes)
    return PaperCancellationObservationRequest(**values)


def _broker_observation(
    **changes: object,
) -> PaperCancellationBrokerOrderObservation:
    values: dict[str, object] = {
        "account_id": EXPECTED_ACCOUNT_ID,
        "cancel_intent_id": "cancel-intent-1",
        "client_order_id": "client-order-1",
        "broker_order_id": "broker-order-1",
        "broker_status": "canceled",
        "observed_at": NOW + timedelta(seconds=11),
        "filled_quantity": "0",
        "filled_average_price": None,
    }
    values.update(changes)
    return PaperCancellationBrokerOrderObservation(**values)


def test_exact_authorized_read_produces_one_reconciliation_observation() -> None:
    identity = _identity()
    authorization = _authorization()
    request = _request(authorization)
    reader = FakeExactOrderReader()

    result = observe_exact_paper_cancellation(
        identity,
        authorization,
        request,
        read_exact_order=reader,
    )

    assert result.status is PaperCancellationObservationStatus.OBSERVED
    assert result.observed is True
    assert result.blocker is None
    assert reader.calls == ["broker-order-1"]
    assert result.read_callback_invoked is True
    assert result.read_count == 1
    assert result.account_identity_matched is True
    assert result.observation is not None
    assert result.observation.cancel_intent_id == identity.cancel_intent_id
    assert result.observation.client_order_id == identity.client_order_id
    assert result.observation.broker_order_id == identity.broker_order_id
    assert result.observation.broker_status == "canceled"

    payload = result.to_dict()
    assert payload["retry_permitted"] is False
    assert payload["target_selection_performed"] is False
    assert payload["polling_performed"] is False
    assert payload["local_journal_updated"] is False
    assert payload["reconciliation_invoked"] is False
    for field_name in (
        "credential_values_accessed_by_boundary",
        "network_client_constructed_by_boundary",
        "broker_sdk_imported_by_boundary",
        "broker_mutation_authorized",
        "broker_mutation_performed",
        "submit_attempted",
        "cancel_attempted",
        "replace_attempted",
        "close_attempted",
        "liquidation_attempted",
        "live_authorized",
    ):
        assert payload[field_name] is False
    serialized = json.dumps(payload, sort_keys=True)
    assert EXPECTED_ACCOUNT_ID not in serialized


@pytest.mark.parametrize(
    ("case", "expected_blocker"),
    (
        ("authorization_missing", PaperCancellationObservationBlocker.AUTHORIZATION_MISSING),
        ("authorization_denied", PaperCancellationObservationBlocker.AUTHORIZATION_NOT_GRANTED),
        ("authorization_id", PaperCancellationObservationBlocker.AUTHORIZATION_ID_MISMATCH),
        ("mode", PaperCancellationObservationBlocker.AUTHORIZATION_MODE_MISMATCH),
        ("operation", PaperCancellationObservationBlocker.AUTHORIZATION_OPERATION_MISMATCH),
        ("not_yet_valid", PaperCancellationObservationBlocker.AUTHORIZATION_NOT_YET_VALID),
        ("expired", PaperCancellationObservationBlocker.AUTHORIZATION_EXPIRED),
        ("cancel_intent", PaperCancellationObservationBlocker.CANCEL_INTENT_ID_MISMATCH),
        ("client_order", PaperCancellationObservationBlocker.CLIENT_ORDER_ID_MISMATCH),
        ("broker_order", PaperCancellationObservationBlocker.BROKER_ORDER_ID_MISMATCH),
        ("observation_permission", PaperCancellationObservationBlocker.OBSERVATION_NOT_PERMITTED),
        ("network_permission", PaperCancellationObservationBlocker.NETWORK_ACCESS_NOT_PERMITTED),
        ("profile", PaperCancellationObservationBlocker.PAPER_PROFILE_REQUIRED),
        ("api_key", PaperCancellationObservationBlocker.API_KEY_REQUIRED),
        ("secret_key", PaperCancellationObservationBlocker.SECRET_KEY_REQUIRED),
        ("paper_endpoint", PaperCancellationObservationBlocker.EXACT_PAPER_ENDPOINT_REQUIRED),
        ("live_endpoint", PaperCancellationObservationBlocker.LIVE_ENDPOINT_DETECTED),
        ("expected_account", PaperCancellationObservationBlocker.EXPECTED_ACCOUNT_REQUIRED),
    ),
)
def test_every_pre_read_gate_blocks_without_invoking_reader(
    case: str,
    expected_blocker: PaperCancellationObservationBlocker,
) -> None:
    identity = _identity()
    authorization: PaperCancellationObservationAuthorization | None = _authorization()
    request_changes: dict[str, object] = {}
    if case == "authorization_missing":
        authorization = None
    elif case == "authorization_denied":
        authorization = _authorization(authorized=False)
    elif case == "authorization_id":
        request_changes["expected_authorization_id"] = "forged-authorization"
    elif case == "mode":
        authorization = _authorization(mode="live")
    elif case == "operation":
        authorization = _authorization(operation="cancel")
    elif case == "not_yet_valid":
        request_changes["occurred_at"] = NOW - timedelta(seconds=1)
    elif case == "expired":
        request_changes["occurred_at"] = NOW + timedelta(minutes=5)
    elif case == "cancel_intent":
        identity = _identity(cancel_intent_id="different-cancel-intent")
    elif case == "client_order":
        identity = _identity(client_order_id="different-client-order")
    elif case == "broker_order":
        identity = _identity(broker_order_id="different-broker-order")
    elif case == "observation_permission":
        request_changes["observation_permitted"] = False
    elif case == "network_permission":
        request_changes["network_access_permitted"] = False
    elif case == "profile":
        request_changes["paper_profile_ready"] = False
    elif case == "api_key":
        request_changes["api_key_present"] = False
    elif case == "secret_key":
        request_changes["secret_key_present"] = False
    elif case == "paper_endpoint":
        request_changes["paper_endpoint_validated"] = False
    elif case == "live_endpoint":
        request_changes["live_endpoint_detected"] = True
    elif case == "expected_account":
        request_changes["expected_account_id"] = ""
    assert authorization is None or isinstance(
        authorization,
        PaperCancellationObservationAuthorization,
    )
    request_source = _authorization() if authorization is None else authorization
    request = _request(request_source, **request_changes)
    reader = FakeExactOrderReader()

    result = observe_exact_paper_cancellation(
        identity,
        authorization,
        request,
        read_exact_order=reader,
    )

    assert result.status is PaperCancellationObservationStatus.BLOCKED
    assert result.blocker is expected_blocker
    assert reader.calls == []
    assert result.read_count == 0
    assert result.observation is None
    assert result.to_dict()["retry_permitted"] is False


@pytest.mark.parametrize(
    ("observation_changes", "expected_blocker"),
    (
        (
            {"account_id": "different-account"},
            PaperCancellationObservationBlocker.ACCOUNT_IDENTITY_MISMATCH,
        ),
        (
            {"cancel_intent_id": "different-cancel-intent"},
            PaperCancellationObservationBlocker.CANCEL_INTENT_ID_MISMATCH,
        ),
        (
            {"client_order_id": "different-client-order"},
            PaperCancellationObservationBlocker.CLIENT_ORDER_ID_MISMATCH,
        ),
        (
            {"broker_order_id": "different-broker-order"},
            PaperCancellationObservationBlocker.BROKER_ORDER_ID_MISMATCH,
        ),
        (
            {"observed_at": NOW + timedelta(seconds=9)},
            PaperCancellationObservationBlocker.OBSERVATION_BEFORE_REQUEST,
        ),
        (
            {"observed_at": NOW + timedelta(minutes=5)},
            PaperCancellationObservationBlocker.AUTHORIZATION_EXPIRED_DURING_OBSERVATION,
        ),
    ),
)
def test_post_read_account_identity_and_time_mismatches_fail_closed_once(
    observation_changes: dict[str, object],
    expected_blocker: PaperCancellationObservationBlocker,
) -> None:
    authorization = _authorization()
    reader = FakeExactOrderReader(_broker_observation(**observation_changes))

    result = observe_exact_paper_cancellation(
        _identity(),
        authorization,
        _request(authorization),
        read_exact_order=reader,
    )

    assert result.status is PaperCancellationObservationStatus.BLOCKED
    assert result.blocker is expected_blocker
    assert reader.calls == ["broker-order-1"]
    assert result.read_count == 1
    assert result.observation is None
    assert result.to_dict()["retry_permitted"] is False


def test_read_failure_and_invalid_contract_are_non_retryable() -> None:
    authorization = _authorization()
    request = _request(authorization)
    failed_reader = FakeExactOrderReader(error=TimeoutError("sensitive detail"))

    failed = observe_exact_paper_cancellation(
        _identity(),
        authorization,
        request,
        read_exact_order=failed_reader,
    )
    invalid_reader = FakeExactOrderReader(observation={"status": "canceled"})
    invalid = observe_exact_paper_cancellation(
        _identity(),
        authorization,
        request,
        read_exact_order=invalid_reader,
    )

    assert failed.blocker is PaperCancellationObservationBlocker.READ_FAILED
    assert failed.error_type == "TimeoutError"
    assert failed_reader.calls == ["broker-order-1"]
    assert "sensitive detail" not in json.dumps(failed.to_dict())
    assert invalid.blocker is PaperCancellationObservationBlocker.OBSERVATION_CONTRACT_INVALID
    assert invalid.error_type == "ValidationError"
    assert invalid_reader.calls == ["broker-order-1"]
    assert failed.to_dict()["retry_permitted"] is False
    assert invalid.to_dict()["retry_permitted"] is False


def test_observation_feeds_existing_reconciler_without_boundary_journal_access(
    tmp_path: Path,
) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    authorization = _authorization()
    observation_result = observe_exact_paper_cancellation(
        _identity(),
        authorization,
        _request(authorization),
        read_exact_order=FakeExactOrderReader(),
    )

    assert observation_result.observation is not None
    reconciliation = reconcile_unresolved_cancellation(
        journal,
        _identity(),
        observation_result.observation,
    )

    assert reconciliation.status is CancellationReconciliationStatus.CONVERGED
    assert reconciliation.order_record is not None
    assert reconciliation.order_record.state is OrderJournalState.CANCELED
    assert reconciliation.cancel_record is not None
    assert reconciliation.cancel_record.state is CancelJournalState.CANCELED


def test_authorization_and_requests_are_bounded_immutable_and_value_safe() -> None:
    authorization = _authorization()
    request = _request(authorization)
    observation = _broker_observation(broker_status="OrderStatus.CANCELED")

    assert MAXIMUM_OBSERVATION_AUTHORIZATION_TTL_SECONDS == 300
    assert authorization == _authorization()
    assert observation.broker_status == "canceled"
    assert EXPECTED_ACCOUNT_ID not in json.dumps(request.to_dict())
    assert EXPECTED_ACCOUNT_ID not in repr(request)
    assert EXPECTED_ACCOUNT_ID not in repr(observation)
    with pytest.raises(FrozenInstanceError):
        authorization.authorized = False  # type: ignore[misc]
    with pytest.raises(ValidationError, match="authorization_id"):
        replace(authorization, authorization_id="forged")
    with pytest.raises(ValidationError, match="exceeds the maximum"):
        _authorization(expires_at=NOW + timedelta(seconds=301))
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        replace(request, occurred_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError, match="must be a boolean"):
        replace(request, network_access_permitted=1)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="non-negative"):
        replace(observation, filled_quantity="-0.01")


def test_observed_result_rejects_forged_authorization_or_order_identity() -> None:
    authorization = _authorization()
    request = _request(authorization)
    baseline = observe_exact_paper_cancellation(
        _identity(),
        authorization,
        request,
        read_exact_order=FakeExactOrderReader(),
    )

    assert isinstance(baseline, PaperCancellationObservationResult)
    with pytest.raises(ValidationError, match="authorization identity"):
        replace(baseline, authorization_id="forged")
    assert baseline.observation is not None
    with pytest.raises(ValidationError, match="order identity"):
        replace(
            baseline,
            observation=replace(
                baseline.observation,
                client_order_id="different-client-order",
            ),
        )


def test_wrong_runtime_input_types_fail_before_reader() -> None:
    authorization = _authorization()
    request = _request(authorization)
    reader = FakeExactOrderReader()

    with pytest.raises(ValidationError, match="identity"):
        observe_exact_paper_cancellation(  # type: ignore[arg-type]
            object(),
            authorization,
            request,
            read_exact_order=reader,
        )
    with pytest.raises(ValidationError, match="authorization"):
        observe_exact_paper_cancellation(  # type: ignore[arg-type]
            _identity(),
            object(),
            request,
            read_exact_order=reader,
        )
    with pytest.raises(ValidationError, match="request"):
        observe_exact_paper_cancellation(  # type: ignore[arg-type]
            _identity(),
            authorization,
            object(),
            read_exact_order=reader,
        )
    with pytest.raises(ValidationError, match="read_exact_order"):
        observe_exact_paper_cancellation(  # type: ignore[arg-type]
            _identity(),
            authorization,
            request,
            read_exact_order=None,
        )
    assert reader.calls == []


def _seed_unresolved(path: Path) -> SqliteOrderJournal:
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
        broker_order_id="broker-order-1",
        broker_status="accepted",
        filled_quantity="0",
    )
    journal.reserve_cancel_intent(
        CancelIntent(
            cancel_intent_id="cancel-intent-1",
            client_order_id="client-order-1",
            broker_order_id="broker-order-1",
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
        broker_order_id="broker-order-1",
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
    journal.mark_cancel_ambiguous(
        "cancel-intent-1",
        NOW + timedelta(seconds=4),
        reason="timeout_without_response",
    )
    return journal
