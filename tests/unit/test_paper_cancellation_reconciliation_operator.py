from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import socket

import pytest

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.execution.alpaca_client import AlpacaAccountResponse, AlpacaOrderResponse
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
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
    build_paper_cancellation_observation_authorization,
)
from algotrader.execution.paper_cancellation_reconciliation_operator import (
    PaperCancellationReconciliationOperatorRequest,
    PaperCancellationReconciliationOperatorStatus,
    run_exact_paper_cancellation_reconciliation_operator,
)


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
OBSERVED_AT = NOW + timedelta(seconds=11)
EXPECTED_ACCOUNT_ID = "expected-paper-account"
SENSITIVE_KEY = "operator-binding-sensitive-key-never-log"
SENSITIVE_SECRET = "operator-binding-sensitive-secret-never-log"


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


def _config(**changes: object) -> AlpacaPaperConfig:
    values: dict[str, object] = {
        "app_profile": "paper",
        "alpaca_api_key": SENSITIVE_KEY,
        "alpaca_secret_key": SENSITIVE_SECRET,
        "alpaca_paper_base_url": DEFAULT_ALPACA_PAPER_BASE_URL,
    }
    values.update(changes)
    return AlpacaPaperConfig(**values)


def _authorization(*, authorized: bool = True):
    return build_paper_cancellation_observation_authorization(
        mode=PAPER_CANCELLATION_OBSERVATION_MODE,
        operation=PAPER_CANCELLATION_OBSERVATION_OPERATION,
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        authorized=authorized,
    )


def _request(
    journal_path: Path,
    *,
    authorization_id: str | None = None,
    **changes: object,
) -> PaperCancellationReconciliationOperatorRequest:
    values: dict[str, object] = {
        "journal_path": journal_path,
        "cancel_intent_id": "cancel-intent-1",
        "client_order_id": "client-order-1",
        "broker_order_id": "broker-order-1",
        "expected_authorization_id": (
            authorization_id or _authorization().authorization_id
        ),
        "occurred_at": NOW + timedelta(seconds=10),
        "expected_account_id": EXPECTED_ACCOUNT_ID,
        "operator_binding_permitted": True,
        "network_access_permitted": True,
    }
    values.update(changes)
    return PaperCancellationReconciliationOperatorRequest(**values)


def _seed_unresolved(path: Path, *, claim_cancel: bool = True) -> SqliteOrderJournal:
    journal = SqliteOrderJournal(path)
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


def _client_factory(raw_client: FakeSdkReadClient, calls: list[AlpacaPaperConfig]):
    def factory(config: AlpacaPaperConfig) -> AlpacaSdkClient:
        calls.append(config)
        return AlpacaSdkClient(config, sdk_client=raw_client)

    return factory


def test_default_request_is_blocked_before_journal_or_reader(tmp_path: Path) -> None:
    authorization = _authorization()
    request = PaperCancellationReconciliationOperatorRequest(
        journal_path=tmp_path / "missing.sqlite3",
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
        expected_authorization_id=authorization.authorization_id,
        occurred_at=NOW + timedelta(seconds=10),
        expected_account_id=EXPECTED_ACCOUNT_ID,
    )
    factory_calls: list[AlpacaPaperConfig] = []

    result = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        authorization,
        request,
        client_factory=_client_factory(FakeSdkReadClient(), factory_calls),
    )

    assert (
        result.status
        is PaperCancellationReconciliationOperatorStatus.BLOCKED_BEFORE_READER
    )
    assert result.blocker == "observation_not_permitted"
    assert result.local_target_checked is False
    assert result.reader_constructed is False
    assert result.workflow_result is None
    assert factory_calls == []
    assert not request.journal_path.exists()


def test_network_permission_is_a_separate_default_false_gate(tmp_path: Path) -> None:
    authorization = _authorization()
    request = _request(
        tmp_path / "missing.sqlite3",
        network_access_permitted=False,
    )
    factory_calls: list[AlpacaPaperConfig] = []

    result = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        authorization,
        request,
        client_factory=_client_factory(FakeSdkReadClient(), factory_calls),
    )

    assert result.blocker == "network_access_not_permitted"
    assert result.reader_constructed is False
    assert factory_calls == []


@pytest.mark.parametrize(
    ("config", "authorization", "request_changes", "expected_blocker"),
    [
        (_config(), None, {}, "authorization_missing"),
        (
            _config(),
            _authorization(authorized=False),
            {},
            "authorization_not_granted",
        ),
        (_config(app_profile="dev"), _authorization(), {}, "paper_profile_required"),
        (_config(alpaca_api_key=None), _authorization(), {}, "paper_api_key_required"),
        (
            _config(alpaca_secret_key=None),
            _authorization(),
            {},
            "paper_secret_key_required",
        ),
        (
            _config(alpaca_paper_base_url="https://api.alpaca.markets"),
            _authorization(),
            {},
            "exact_paper_endpoint_required",
        ),
        (_config(), _authorization(), {"expected_account_id": ""}, "expected_paper_account_required"),
        (
            _config(),
            _authorization(),
            {"expected_authorization_id": "different-authorization"},
            "authorization_id_mismatch",
        ),
    ],
)
def test_authorization_and_config_gates_block_before_local_or_client_access(
    tmp_path: Path,
    config: AlpacaPaperConfig,
    authorization: object,
    request_changes: dict[str, object],
    expected_blocker: str,
) -> None:
    request = _request(tmp_path / "missing.sqlite3", **request_changes)
    factory_calls: list[AlpacaPaperConfig] = []

    result = run_exact_paper_cancellation_reconciliation_operator(
        config,
        authorization,  # type: ignore[arg-type]
        request,
        client_factory=_client_factory(FakeSdkReadClient(), factory_calls),
    )

    assert result.blocker == expected_blocker
    assert result.local_target_checked is False
    assert result.reader_constructed is False
    assert factory_calls == []
    assert not request.journal_path.exists()


def test_missing_or_ineligible_local_target_blocks_before_client(tmp_path: Path) -> None:
    authorization = _authorization()
    missing_path = tmp_path / "missing.sqlite3"
    calls: list[AlpacaPaperConfig] = []
    missing = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        authorization,
        _request(missing_path),
        client_factory=_client_factory(FakeSdkReadClient(), calls),
    )
    assert missing.blocker == "local_journal_path_missing"
    assert missing.local_target_checked is False

    reserved_path = tmp_path / "reserved.sqlite3"
    _seed_unresolved(reserved_path, claim_cancel=False)
    reserved = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        authorization,
        _request(reserved_path),
        client_factory=_client_factory(FakeSdkReadClient(), calls),
    )
    assert reserved.blocker == "cancel_intent_not_reconciliation_ready"
    assert reserved.local_target_checked is True
    assert reserved.reader_constructed is False
    assert calls == []


def test_exact_operator_binding_converges_once_with_fake_sdk_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _seed_unresolved(path)
    paused = journal.set_runtime_control(
        trading_enabled=False,
        stop_requested=True,
        reason="operator_pause",
        occurred_at=NOW + timedelta(seconds=5),
    )
    raw_client = FakeSdkReadClient()
    factory_calls: list[AlpacaPaperConfig] = []

    def blocked_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("network access is forbidden in this test")

    monkeypatch.setattr(socket, "socket", blocked_socket)
    result = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        _authorization(),
        _request(path),
        client_factory=_client_factory(raw_client, factory_calls),
        reader_clock=lambda: OBSERVED_AT,
    )

    assert result.status is PaperCancellationReconciliationOperatorStatus.CONVERGED
    assert result.blocker == ""
    assert result.local_target_checked is True
    assert result.reader_constructed is True
    assert len(factory_calls) == 1
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]
    order, cancel = _records(journal)
    assert order is not None and order.state is OrderJournalState.CANCELED
    assert cancel is not None and cancel.state is CancelJournalState.CANCELED
    assert journal.get_runtime_control() == paused

    payload = result.to_dict()
    assert payload["authorization_minted"] is False
    assert payload["preexisting_authorization_evaluated"] is True
    assert payload["read_client_constructed"] is True
    assert payload["workflow_invoked"] is True
    assert payload["exact_order_reader_invoked"] is True
    assert payload["local_journal_updated"] is True
    assert payload["retry_permitted"] is False
    for field_name in (
        "target_selection_performed",
        "unresolved_intents_enumerated",
        "polling_performed",
        "environment_read",
        "credential_values_serialized",
        "runtime_control_changed",
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
    rendered = str(payload)
    assert EXPECTED_ACCOUNT_ID not in rendered
    assert SENSITIVE_KEY not in rendered
    assert SENSITIVE_SECRET not in rendered


@pytest.mark.parametrize(
    ("raw_client", "expected_blocker"),
    [
        (
            FakeSdkReadClient(account_id="different-account"),
            "expected_paper_account_mismatch",
        ),
        (
            FakeSdkReadClient(client_order_id="different-client-order"),
            "client_order_id_mismatch",
        ),
        (
            FakeSdkReadClient(order_error=OSError("offline fake failure")),
            "exact_order_read_failed",
        ),
    ],
)
def test_read_and_identity_failures_are_nonretryable_and_do_not_mutate(
    tmp_path: Path,
    raw_client: FakeSdkReadClient,
    expected_blocker: str,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _seed_unresolved(path)
    before = _records(journal)
    calls: list[AlpacaPaperConfig] = []

    result = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        _authorization(),
        _request(path),
        client_factory=_client_factory(raw_client, calls),
        reader_clock=lambda: OBSERVED_AT,
    )

    assert (
        result.status
        is PaperCancellationReconciliationOperatorStatus.WORKFLOW_BLOCKED
    )
    assert result.blocker == expected_blocker
    assert result.reader_constructed is True
    assert result.workflow_result is not None
    assert result.workflow_result.reconciliation_result is None
    assert result.to_dict()["retry_permitted"] is False
    assert _records(journal) == before


def test_reader_construction_failure_is_sanitized_after_exact_local_check(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    _seed_unresolved(path)

    def failing_factory(config: AlpacaPaperConfig) -> AlpacaSdkClient:
        raise RuntimeError(f"factory {SENSITIVE_KEY} {SENSITIVE_SECRET}")

    result = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        _authorization(),
        _request(path),
        client_factory=failing_factory,
    )

    assert result.blocker == "exact_reader_construction_failed"
    assert result.local_target_checked is True
    assert result.reader_constructed is False
    assert result.error_type == "PaperCancellationSdkReadError"
    rendered = str(result.to_dict())
    assert SENSITIVE_KEY not in rendered
    assert SENSITIVE_SECRET not in rendered


def test_request_and_result_are_immutable_and_hide_account_identity(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path / "missing.sqlite3")
    result = run_exact_paper_cancellation_reconciliation_operator(
        _config(),
        _authorization(),
        replace(request, operator_binding_permitted=False),
    )

    assert EXPECTED_ACCOUNT_ID not in repr(request)
    assert EXPECTED_ACCOUNT_ID not in repr(result)
    with pytest.raises(FrozenInstanceError):
        request.client_order_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.blocker = "changed"  # type: ignore[misc]
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
