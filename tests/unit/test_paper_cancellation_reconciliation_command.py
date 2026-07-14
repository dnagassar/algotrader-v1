from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import socket

import pytest

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.errors import ValidationError
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
from algotrader.execution.paper_cancellation_reconciliation_command import (
    PaperCancellationReconciliationCommandRequest,
    PaperCancellationReconciliationCommandStatus,
    main,
    run_exact_paper_cancellation_reconciliation_command,
)


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
OBSERVED_AT = NOW + timedelta(seconds=11)
EXPECTED_ACCOUNT_ID = "exact-expected-paper-account"
SENSITIVE_KEY = "command-sensitive-key-never-render"
SENSITIVE_SECRET = "command-sensitive-secret-never-render"


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


class ExplodingEnvironment(dict[str, str]):
    def get(self, key: str, default: object = None) -> str:  # type: ignore[override]
        raise AssertionError("environment must not be read")


def _authorization():
    return build_paper_cancellation_observation_authorization(
        mode=PAPER_CANCELLATION_OBSERVATION_MODE,
        operation=PAPER_CANCELLATION_OBSERVATION_OPERATION,
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        authorized=True,
    )


def _write_authorization(path: Path) -> None:
    path.write_text(
        json.dumps(_authorization().to_dict(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _env(**changes: str) -> dict[str, str]:
    values = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": SENSITIVE_KEY,
        "ALPACA_SECRET_KEY": SENSITIVE_SECRET,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }
    values.update(changes)
    return values


def _request(
    authorization_path: Path,
    journal_path: Path,
    **changes: object,
) -> PaperCancellationReconciliationCommandRequest:
    values: dict[str, object] = {
        "authorization_artifact_path": authorization_path,
        "journal_path": journal_path,
        "cancel_intent_id": "cancel-intent-1",
        "client_order_id": "client-order-1",
        "broker_order_id": "broker-order-1",
        "expected_authorization_id": _authorization().authorization_id,
        "occurred_at": NOW + timedelta(seconds=10),
        "expected_account_id": EXPECTED_ACCOUNT_ID,
        "operator_binding_permitted": True,
        "network_access_permitted": True,
    }
    values.update(changes)
    return PaperCancellationReconciliationCommandRequest(**values)


def _seed_unresolved(path: Path) -> SqliteOrderJournal:
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


def _client_factory(raw_client: FakeSdkReadClient, calls: list[AlpacaPaperConfig]):
    def factory(config: AlpacaPaperConfig) -> AlpacaSdkClient:
        calls.append(config)
        return AlpacaSdkClient(config, sdk_client=raw_client)

    return factory


def test_default_permissions_block_before_artifact_environment_or_client(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path / "missing-authorization.json",
        tmp_path / "missing.sqlite3",
        operator_binding_permitted=False,
        network_access_permitted=False,
    )

    def forbidden_loader(path: Path | str):
        raise AssertionError(f"artifact loader must not run: {path}")

    def forbidden_client(config: AlpacaPaperConfig) -> AlpacaSdkClient:
        raise AssertionError(f"client must not be constructed: {config!r}")

    result = run_exact_paper_cancellation_reconciliation_command(
        request,
        env=ExplodingEnvironment(),
        client_factory=forbidden_client,
        authorization_loader=forbidden_loader,
    )

    assert result.status is PaperCancellationReconciliationCommandStatus.BLOCKED_BEFORE_OPERATOR
    assert result.blocker == "operator_binding_not_permitted"
    assert result.authorization_artifact_loaded is False
    assert result.paper_configuration_loaded is False
    assert result.process_environment_read is False
    assert result.operator_invoked is False
    assert not request.authorization_artifact_path.exists()
    assert not request.journal_path.exists()


def test_network_permission_is_a_separate_pre_artifact_gate(tmp_path: Path) -> None:
    request = _request(
        tmp_path / "missing-authorization.json",
        tmp_path / "missing.sqlite3",
        network_access_permitted=False,
    )

    def forbidden_loader(path: Path | str):
        raise AssertionError(f"artifact loader must not run: {path}")

    result = run_exact_paper_cancellation_reconciliation_command(
        request,
        env=ExplodingEnvironment(),
        authorization_loader=forbidden_loader,
    )

    assert result.blocker == "network_access_not_permitted"
    assert result.authorization_artifact_loaded is False
    assert result.operator_invoked is False


def test_invalid_artifact_is_sanitized_before_environment_or_operator(
    tmp_path: Path,
) -> None:
    path = tmp_path / "authorization.json"
    sensitive_payload = "artifact-secret-that-must-not-render"
    path.write_text(sensitive_payload, encoding="utf-8")
    result = run_exact_paper_cancellation_reconciliation_command(
        _request(path, tmp_path / "missing.sqlite3"),
        env=ExplodingEnvironment(),
    )

    assert result.blocker == "authorization_artifact_invalid"
    assert result.authorization_artifact_loaded is False
    assert result.paper_configuration_loaded is False
    assert result.operator_invoked is False
    assert sensitive_payload not in str(result.to_dict())


@pytest.mark.parametrize(
    ("env", "expected_blocker"),
    [
        ({}, "paper_profile_required"),
        (_env(APP_PROFILE="dev"), "paper_profile_required"),
        (
            {
                key: value
                for key, value in _env().items()
                if key != "ALPACA_API_KEY"
            },
            "paper_api_key_required",
        ),
        (
            {
                key: value
                for key, value in _env().items()
                if key != "ALPACA_SECRET_KEY"
            },
            "paper_secret_key_required",
        ),
        (
            _env(ALPACA_PAPER_BASE_URL="https://api.alpaca.markets"),
            "exact_paper_endpoint_required",
        ),
    ],
)
def test_canonical_paper_configuration_gates_before_journal_and_client(
    tmp_path: Path,
    env: dict[str, str],
    expected_blocker: str,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    _write_authorization(authorization_path)
    client_calls: list[AlpacaPaperConfig] = []

    result = run_exact_paper_cancellation_reconciliation_command(
        _request(authorization_path, tmp_path / "missing.sqlite3"),
        env=env,
        client_factory=_client_factory(FakeSdkReadClient(), client_calls),
    )

    assert result.status is PaperCancellationReconciliationCommandStatus.OPERATOR_BLOCKED
    assert result.blocker == expected_blocker
    assert result.authorization_artifact_loaded is True
    assert result.paper_configuration_loaded is True
    assert result.process_environment_read is False
    assert result.operator_invoked is True
    assert client_calls == []


@pytest.mark.parametrize(
    ("request_changes", "expected_blocker"),
    [
        ({"expected_authorization_id": "different-auth"}, "authorization_id_mismatch"),
        ({"cancel_intent_id": "different-cancel"}, "cancel_intent_id_mismatch"),
        ({"client_order_id": "different-client"}, "client_order_id_mismatch"),
        ({"broker_order_id": "different-broker"}, "broker_order_id_mismatch"),
        (
            {"occurred_at": NOW + timedelta(minutes=5)},
            "authorization_expired",
        ),
    ],
)
def test_expired_or_mismatched_exact_evidence_blocks_before_local_or_client(
    tmp_path: Path,
    request_changes: dict[str, object],
    expected_blocker: str,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    _write_authorization(authorization_path)
    client_calls: list[AlpacaPaperConfig] = []

    result = run_exact_paper_cancellation_reconciliation_command(
        _request(
            authorization_path,
            tmp_path / "missing.sqlite3",
            **request_changes,
        ),
        env=_env(),
        client_factory=_client_factory(FakeSdkReadClient(), client_calls),
    )

    assert result.blocker == expected_blocker
    assert result.operator_result is not None
    assert result.operator_result.local_target_checked is False
    assert result.operator_result.reader_constructed is False
    assert client_calls == []


def test_missing_journal_blocks_before_client_construction(tmp_path: Path) -> None:
    authorization_path = tmp_path / "authorization.json"
    _write_authorization(authorization_path)
    client_calls: list[AlpacaPaperConfig] = []

    result = run_exact_paper_cancellation_reconciliation_command(
        _request(authorization_path, tmp_path / "missing.sqlite3"),
        env=_env(),
        client_factory=_client_factory(FakeSdkReadClient(), client_calls),
    )

    assert result.blocker == "local_journal_path_missing"
    assert result.operator_result is not None
    assert result.operator_result.local_target_checked is False
    assert result.operator_result.reader_constructed is False
    assert client_calls == []


def test_command_converges_once_with_fake_sdk_offline_and_preserves_runtime_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    journal_path = tmp_path / "orders.sqlite3"
    _write_authorization(authorization_path)
    journal = _seed_unresolved(journal_path)
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
    request = _request(authorization_path, journal_path)
    result = run_exact_paper_cancellation_reconciliation_command(
        request,
        env=_env(),
        client_factory=_client_factory(raw_client, factory_calls),
        reader_clock=lambda: OBSERVED_AT,
    )

    assert result.status is PaperCancellationReconciliationCommandStatus.CONVERGED
    assert result.blocker == ""
    assert result.authorization_artifact_loaded is True
    assert result.paper_configuration_loaded is True
    assert result.process_environment_read is False
    assert result.operator_invoked is True
    assert len(factory_calls) == 1
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]
    order = journal.get("client-order-1")
    cancel = journal.get_cancel_intent("cancel-intent-1")
    assert order is not None and order.state is OrderJournalState.CANCELED
    assert cancel is not None and cancel.state is CancelJournalState.CANCELED
    assert journal.get_runtime_control() == paused

    payload = result.to_dict()
    assert payload["broker_read_callback_invoked"] is True
    assert payload["retry_permitted"] is False
    for field_name in (
        "authorization_minted",
        "credential_values_serialized",
        "target_selection_performed",
        "unresolved_intents_enumerated",
        "polling_performed",
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


def test_reader_failure_is_sanitized_nonretryable_and_does_not_converge(
    tmp_path: Path,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    journal_path = tmp_path / "orders.sqlite3"
    _write_authorization(authorization_path)
    journal = _seed_unresolved(journal_path)
    before = (
        journal.get("client-order-1"),
        journal.get_cancel_intent("cancel-intent-1"),
    )
    raw_client = FakeSdkReadClient(
        order_error=OSError(f"fake read failed {SENSITIVE_SECRET}")
    )

    result = run_exact_paper_cancellation_reconciliation_command(
        _request(authorization_path, journal_path),
        env=_env(),
        client_factory=_client_factory(raw_client, []),
        reader_clock=lambda: OBSERVED_AT,
    )

    assert result.status is PaperCancellationReconciliationCommandStatus.OPERATOR_BLOCKED
    assert result.blocker == "exact_order_read_failed"
    assert result.to_dict()["retry_permitted"] is False
    assert (
        journal.get("client-order-1"),
        journal.get_cancel_intent("cancel-intent-1"),
    ) == before
    rendered = str(result.to_dict())
    assert SENSITIVE_KEY not in rendered
    assert SENSITIVE_SECRET not in rendered


def test_request_requires_account_and_result_surface_has_no_trading_capability(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError):
        _request(
            tmp_path / "authorization.json",
            tmp_path / "journal.sqlite3",
            expected_account_id="",
        )

    request = _request(
        tmp_path / "authorization.json",
        tmp_path / "journal.sqlite3",
        operator_binding_permitted=False,
    )
    result = run_exact_paper_cancellation_reconciliation_command(request, env={})
    assert EXPECTED_ACCOUNT_ID not in repr(request)
    assert EXPECTED_ACCOUNT_ID not in repr(result)
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
        "retry",
    ):
        assert not hasattr(result, capability)


def test_main_sanitizes_invalid_request_without_environment_read(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "--authorization-artifact",
            "missing.json",
            "--journal-path",
            "missing.sqlite3",
            "--cancel-intent-id",
            "cancel-intent-1",
            "--client-order-id",
            "client-order-1",
            "--broker-order-id",
            " ",
            "--expected-authorization-id",
            "authorization-1",
            "--expected-paper-account-id",
            EXPECTED_ACCOUNT_ID,
            "--occurred-at",
            (NOW + timedelta(seconds=10)).isoformat(),
        ]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "invalid_request"
    assert payload["process_environment_read"] is False
    assert payload["operator_invoked"] is False
    assert EXPECTED_ACCOUNT_ID not in str(payload)
