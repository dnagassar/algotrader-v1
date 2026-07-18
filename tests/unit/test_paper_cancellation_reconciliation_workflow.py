from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import socket

import pytest

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaAccountResponse, AlpacaOrderResponse
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
    CancellationReconciliationStatus,
)
from algotrader.execution.order_journal import (
    CancelIntent,
    CancelJournalState,
    OrderJournalState,
    OrderReservation,
    SqliteOrderJournal,
)
from algotrader.execution.paper_cancellation_observation import (
    PAPER_CANCELLATION_OBSERVATION_MODE,
    PAPER_CANCELLATION_OBSERVATION_OPERATION,
    PaperCancellationObservationBlocker,
    PaperCancellationObservationRequest,
    build_paper_cancellation_observation_authorization,
)
from algotrader.execution.paper_cancellation_observation_sdk import (
    build_paper_cancellation_sdk_reader,
)
from algotrader.execution.paper_cancellation_reconciliation_workflow import (
    PaperCancellationReconciliationWorkflowStatus,
    reconcile_exact_paper_cancellation,
)


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
OBSERVED_AT = NOW + timedelta(seconds=11)
EXPECTED_ACCOUNT_ID = "expected-paper-account"


class FakeSdkReadClient:
    def __init__(
        self,
        *,
        account_id: str = EXPECTED_ACCOUNT_ID,
        client_order_id: str = "client-order-1",
        broker_order_id: str = "broker-order-1",
        order_error: Exception | None = None,
    ) -> None:
        self.account_id = account_id
        self.client_order_id = client_order_id
        self.broker_order_id = broker_order_id
        self.order_error = order_error
        self.calls: list[str] = []

    def get_account(self) -> AlpacaAccountResponse:
        self.calls.append("get_account")
        return AlpacaAccountResponse(
            account_id=self.account_id,
            status="ACTIVE",
            cash=Decimal("100000"),
            buying_power=Decimal("200000"),
            equity=Decimal("100000"),
        )

    def get_order_by_id(self, broker_order_id: str) -> AlpacaOrderResponse:
        self.calls.append(f"get_order_by_id:{broker_order_id}")
        if self.order_error is not None:
            raise self.order_error
        return AlpacaOrderResponse(
            order_id=self.broker_order_id,
            client_order_id=self.client_order_id,
            symbol="BTC/USD",
            side="buy",
            status="canceled",
            qty=Decimal("0.01"),
            asset_class="crypto",
            filled_qty=Decimal("0"),
        )


class FailingLocalJournal(SqliteOrderJournal):
    def reconcile_unresolved_cancel_observation(self, **kwargs: object):
        raise OSError("local transaction unavailable")


def _config() -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="offline-fake-key",
        alpaca_secret_key="offline-fake-secret",
        alpaca_paper_base_url=DEFAULT_ALPACA_PAPER_BASE_URL,
    )


def _identity() -> CancellationReconciliationIdentity:
    return CancellationReconciliationIdentity(
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
    )


def _authorization_and_request(**request_changes: object):
    identity = _identity()
    authorization = build_paper_cancellation_observation_authorization(
        mode=PAPER_CANCELLATION_OBSERVATION_MODE,
        operation=PAPER_CANCELLATION_OBSERVATION_OPERATION,
        cancel_intent_id=identity.cancel_intent_id,
        client_order_id=identity.client_order_id,
        broker_order_id=identity.broker_order_id,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        authorized=True,
    )
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
    values.update(request_changes)
    return authorization, PaperCancellationObservationRequest(**values)


def _sdk_reader(
    raw_client: FakeSdkReadClient,
    *,
    observed_at: datetime = OBSERVED_AT,
):
    def factory(config: AlpacaPaperConfig) -> AlpacaSdkClient:
        return AlpacaSdkClient(config, sdk_client=raw_client)

    return build_paper_cancellation_sdk_reader(
        _config(),
        _identity(),
        client_factory=factory,
        clock=lambda: observed_at,
    )


def _seed_unresolved(
    path: Path,
    *,
    journal_type: type[SqliteOrderJournal] = SqliteOrderJournal,
    claim_cancel: bool = True,
) -> SqliteOrderJournal:
    journal = journal_type(path)
    journal.reserve(
        OrderReservation(
            client_order_id="client-order-1",
            execution_plan_id="plan-1",
            run_id="order-run-1",
            symbol="BTCUSD",
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
    if not claim_cancel:
        return journal

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


def _records(journal: SqliteOrderJournal):
    return (
        journal.get("client-order-1"),
        journal.get_cancel_intent("cancel-intent-1"),
    )


def test_exact_fake_sdk_observation_converges_both_journals_once_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    paused = journal.set_runtime_control(
        trading_enabled=False,
        stop_requested=True,
        reason="operator_pause",
        occurred_at=NOW + timedelta(seconds=5),
    )
    raw_client = FakeSdkReadClient()
    reader = _sdk_reader(raw_client)
    authorization, request = _authorization_and_request()

    def blocked_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("network access is forbidden in this test")

    monkeypatch.setattr(socket, "socket", blocked_socket)
    result = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=reader,
    )

    assert result.status is PaperCancellationReconciliationWorkflowStatus.CONVERGED
    assert result.blocker == ""
    assert result.local_journal_updated is True
    assert result.reconciliation_result is not None
    assert (
        result.reconciliation_result.status
        is CancellationReconciliationStatus.CONVERGED
    )
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]
    order, cancel = _records(journal)
    assert order is not None and order.state is OrderJournalState.CANCELED
    assert cancel is not None and cancel.state is CancelJournalState.CANCELED
    assert journal.get_runtime_control() == paused

    payload = result.to_dict()
    assert payload["exact_order_reader_invoked"] is True
    assert payload["exact_order_read_count"] == 1
    assert payload["observation_validated"] is True
    assert payload["reconciliation_invoked"] is True
    assert payload["injected_observation_consumed"] is True
    assert payload["local_journal_updated"] is True
    assert payload["retry_permitted"] is False
    for field_name in (
        "target_selection_performed",
        "polling_performed",
        "runtime_control_changed",
        "credential_values_accessed_by_workflow",
        "network_client_constructed_by_workflow",
        "broker_sdk_imported_by_workflow",
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


def test_pre_read_rejection_neither_reads_nor_mutates_journal(tmp_path: Path) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    before = _records(journal)
    raw_client = FakeSdkReadClient()
    reader = _sdk_reader(raw_client)
    authorization, request = _authorization_and_request(
        observation_permitted=False
    )

    result = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=reader,
    )

    assert (
        result.status
        is PaperCancellationReconciliationWorkflowStatus.OBSERVATION_BLOCKED
    )
    assert result.blocker == "observation_not_permitted"
    assert result.observation_result.read_count == 0
    assert result.reconciliation_result is None
    assert reader.consumed is False
    assert raw_client.calls == []
    assert _records(journal) == before


@pytest.mark.parametrize(
    ("raw_changes", "observed_at", "expected_blocker"),
    [
        (
            {"account_id": "different-account"},
            OBSERVED_AT,
            "expected_paper_account_mismatch",
        ),
        (
            {"client_order_id": "different-client-order"},
            OBSERVED_AT,
            "client_order_id_mismatch",
        ),
        (
            {"broker_order_id": "different-broker-order"},
            OBSERVED_AT,
            "broker_order_id_mismatch",
        ),
        ({}, NOW + timedelta(seconds=9), "observation_before_request"),
    ],
)
def test_post_read_rejection_never_reaches_local_reconciliation(
    tmp_path: Path,
    raw_changes: dict[str, str],
    observed_at: datetime,
    expected_blocker: str,
) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    before = _records(journal)
    raw_client = FakeSdkReadClient(**raw_changes)
    reader = _sdk_reader(raw_client, observed_at=observed_at)
    authorization, request = _authorization_and_request()

    result = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=reader,
    )

    assert (
        result.status
        is PaperCancellationReconciliationWorkflowStatus.OBSERVATION_BLOCKED
    )
    assert result.blocker == expected_blocker
    assert result.observation_result.read_count == 1
    assert result.reconciliation_result is None
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]
    assert _records(journal) == before


def test_read_failure_is_non_retryable_and_never_mutates_journal(tmp_path: Path) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    before = _records(journal)
    raw_client = FakeSdkReadClient(order_error=OSError("offline fake failure"))
    reader = _sdk_reader(raw_client)
    authorization, request = _authorization_and_request()

    first = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=reader,
    )
    second = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=reader,
    )

    for result in (first, second):
        assert (
            result.status
            is PaperCancellationReconciliationWorkflowStatus.OBSERVATION_BLOCKED
        )
        assert result.observation_result.blocker is PaperCancellationObservationBlocker.READ_FAILED
        assert result.reconciliation_result is None
        assert result.to_dict()["retry_permitted"] is False
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]
    assert _records(journal) == before


def test_local_validation_failure_consumes_observation_but_updates_neither_record(
    tmp_path: Path,
) -> None:
    journal = _seed_unresolved(
        tmp_path / "orders.sqlite3",
        claim_cancel=False,
    )
    before = _records(journal)
    raw_client = FakeSdkReadClient()
    authorization, request = _authorization_and_request()

    result = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=_sdk_reader(raw_client),
    )

    assert (
        result.status
        is PaperCancellationReconciliationWorkflowStatus.RECONCILIATION_BLOCKED
    )
    assert result.blocker == "cancel_intent_not_reconciliation_ready"
    assert result.observation_result.observed is True
    assert result.reconciliation_result is not None
    assert result.reconciliation_result.local_journal_updated is False
    assert _records(journal) == before


def test_local_transaction_exception_is_sanitized_and_updates_nothing(
    tmp_path: Path,
) -> None:
    journal = _seed_unresolved(
        tmp_path / "orders.sqlite3",
        journal_type=FailingLocalJournal,
    )
    before = _records(journal)
    authorization, request = _authorization_and_request()

    result = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=_sdk_reader(FakeSdkReadClient()),
    )

    assert (
        result.status
        is PaperCancellationReconciliationWorkflowStatus.RECONCILIATION_BLOCKED
    )
    assert result.blocker == "local_journal_unavailable"
    assert result.reconciliation_result is not None
    assert result.reconciliation_result.error_type == "OSError"
    assert _records(journal) == before


def test_invalid_composition_inputs_fail_before_reader_invocation(tmp_path: Path) -> None:
    calls: list[str] = []

    def reader(broker_order_id: str) -> object:
        calls.append(broker_order_id)
        return object()

    authorization, request = _authorization_and_request()
    with pytest.raises(ValidationError, match="SqliteOrderJournal"):
        reconcile_exact_paper_cancellation(
            object(),  # type: ignore[arg-type]
            _identity(),
            authorization,
            request,
            read_exact_order=reader,  # type: ignore[arg-type]
        )
    assert calls == []


def test_workflow_result_is_immutable_and_exposes_no_action_surface(
    tmp_path: Path,
) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    authorization, request = _authorization_and_request()
    result = reconcile_exact_paper_cancellation(
        journal,
        _identity(),
        authorization,
        request,
        read_exact_order=_sdk_reader(FakeSdkReadClient()),
    )

    with pytest.raises(FrozenInstanceError):
        result.status = (  # type: ignore[misc]
            PaperCancellationReconciliationWorkflowStatus.OBSERVATION_BLOCKED
        )
    for capability in (
        "submit_order",
        "cancel_order",
        "replace_order",
        "close_position",
        "liquidate",
        "get_orders",
        "unresolved_cancel_intents",
    ):
        assert not hasattr(result, capability)
