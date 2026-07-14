from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from algotrader.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    AlpacaPaperConfig,
    ConfigValidationError,
)
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaAccountResponse, AlpacaOrderResponse
from algotrader.execution.alpaca_sdk_client import (
    AlpacaSdkClient,
    AlpacaSdkClientReadError,
)
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
)
from algotrader.execution.paper_cancellation_observation import (
    PAPER_CANCELLATION_OBSERVATION_MODE,
    PAPER_CANCELLATION_OBSERVATION_OPERATION,
    PaperCancellationObservationRequest,
    PaperCancellationObservationStatus,
    build_paper_cancellation_observation_authorization,
    observe_exact_paper_cancellation,
)
from algotrader.execution.paper_cancellation_observation_sdk import (
    PaperCancellationSdkReadError,
    build_paper_cancellation_sdk_reader,
)


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
OBSERVED_AT = NOW + timedelta(seconds=11)
SENSITIVE_KEY = "sdk-reader-sensitive-key-never-log"
SENSITIVE_SECRET = "sdk-reader-sensitive-secret-never-log"
EXPECTED_ACCOUNT_ID = "expected-paper-account"


class FakeSdkReadClient:
    def __init__(
        self,
        *,
        account_error: Exception | None = None,
        order_error: Exception | None = None,
        client_order_id: str = "client-order-1",
    ) -> None:
        self.account_error = account_error
        self.order_error = order_error
        self.client_order_id = client_order_id
        self.calls: list[str] = []

    def get_account(self) -> AlpacaAccountResponse:
        self.calls.append("get_account")
        if self.account_error is not None:
            raise self.account_error
        return AlpacaAccountResponse(
            account_id=EXPECTED_ACCOUNT_ID,
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
            order_id="broker-order-1",
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


def _identity() -> CancellationReconciliationIdentity:
    return CancellationReconciliationIdentity(
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
    )


def _reader(raw_client: FakeSdkReadClient):
    def factory(config: AlpacaPaperConfig) -> AlpacaSdkClient:
        return AlpacaSdkClient(config, sdk_client=raw_client)

    return build_paper_cancellation_sdk_reader(
        _config(),
        _identity(),
        client_factory=factory,
        clock=lambda: OBSERVED_AT,
    )


def _authorized_request():
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
    request = PaperCancellationObservationRequest(
        expected_authorization_id=authorization.authorization_id,
        occurred_at=NOW + timedelta(seconds=10),
        expected_account_id=EXPECTED_ACCOUNT_ID,
        observation_permitted=True,
        network_access_permitted=True,
        paper_profile_ready=True,
        api_key_present=True,
        secret_key_present=True,
        paper_endpoint_validated=True,
        live_endpoint_detected=False,
    )
    return identity, authorization, request


def test_sdk_reader_plugs_into_authorized_boundary_once() -> None:
    raw_client = FakeSdkReadClient()
    reader = _reader(raw_client)
    identity, authorization, request = _authorized_request()

    result = observe_exact_paper_cancellation(
        identity,
        authorization,
        request,
        read_exact_order=reader,
    )

    assert result.status is PaperCancellationObservationStatus.OBSERVED
    assert result.observation is not None
    assert result.observation.broker_status == "canceled"
    assert result.observation.filled_quantity == Decimal("0")
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]
    assert (reader.consumed, reader.invocation_count) == (True, 1)
    assert (reader.account_read_count, reader.order_read_count) == (1, 1)


def test_sdk_client_exact_order_read_validates_delegates_and_sanitizes() -> None:
    raw_client = FakeSdkReadClient()
    client = AlpacaSdkClient(_config(), sdk_client=raw_client)

    assert client.get_order_by_id(" broker-order-1 ").order_id == "broker-order-1"
    with pytest.raises(ValueError, match="broker_order_id is required"):
        client.get_order_by_id(" ")
    assert raw_client.calls == ["get_order_by_id:broker-order-1"]

    raw_client.order_error = RuntimeError(
        f"order failed key={SENSITIVE_KEY} secret={SENSITIVE_SECRET}"
    )
    with pytest.raises(AlpacaSdkClientReadError) as exc_info:
        client.get_order_by_id("broker-order-1")
    rendered = str(exc_info.value)
    assert SENSITIVE_KEY not in rendered
    assert SENSITIVE_SECRET not in rendered


def test_reader_blocks_wrong_identity_and_reuse_before_extra_io() -> None:
    raw_client = FakeSdkReadClient()
    reader = _reader(raw_client)

    with pytest.raises(PaperCancellationSdkReadError) as wrong:
        reader("different-order")
    assert wrong.value.error_stage == "broker_order_identity_mismatch"
    assert reader.consumed is False
    assert raw_client.calls == []

    reader("broker-order-1")
    with pytest.raises(PaperCancellationSdkReadError) as reused:
        reader("broker-order-1")
    assert reused.value.error_stage == "reader_already_consumed"
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]


@pytest.mark.parametrize(
    ("field", "stage", "calls"),
    [
        ("account_error", "account_read_failed", ["get_account"]),
        (
            "order_error",
            "exact_order_read_failed",
            ["get_account", "get_order_by_id:broker-order-1"],
        ),
    ],
)
def test_failures_consume_once_stop_and_hide_sensitive_text(
    field: str,
    stage: str,
    calls: list[str],
) -> None:
    raw_client = FakeSdkReadClient(
        **{field: RuntimeError(f"failure {SENSITIVE_KEY} {SENSITIVE_SECRET}")}
    )
    reader = _reader(raw_client)

    with pytest.raises(PaperCancellationSdkReadError) as exc_info:
        reader("broker-order-1")

    assert exc_info.value.error_stage == stage
    assert SENSITIVE_KEY not in str(exc_info.value)
    assert SENSITIVE_SECRET not in str(exc_info.value)
    assert reader.consumed is True
    assert reader.invocation_count == 1
    assert raw_client.calls == calls


@pytest.mark.parametrize(
    "config",
    [
        _config(app_profile="dev"),
        _config(alpaca_api_key=None),
        _config(alpaca_secret_key=None),
        _config(alpaca_paper_base_url="https://different-paper.example.test"),
        _config(alpaca_paper_base_url="https://api.alpaca.markets"),
    ],
)
def test_builder_rejects_unsafe_config_before_factory(config: AlpacaPaperConfig) -> None:
    factory_calls: list[AlpacaPaperConfig] = []

    def factory(value: AlpacaPaperConfig) -> FakeSdkReadClient:
        factory_calls.append(value)
        return FakeSdkReadClient()

    with pytest.raises((ConfigValidationError, ValidationError)):
        build_paper_cancellation_sdk_reader(
            config,
            _identity(),
            client_factory=factory,
        )
    assert factory_calls == []


def test_builder_and_reader_surfaces_hide_credentials_and_mutation() -> None:
    def failing_factory(config: AlpacaPaperConfig) -> FakeSdkReadClient:
        raise RuntimeError(f"factory {SENSITIVE_KEY} {SENSITIVE_SECRET}")

    with pytest.raises(PaperCancellationSdkReadError) as exc_info:
        build_paper_cancellation_sdk_reader(
            _config(),
            _identity(),
            client_factory=failing_factory,
        )
    assert SENSITIVE_KEY not in str(exc_info.value)
    assert SENSITIVE_SECRET not in str(exc_info.value)

    reader = _reader(FakeSdkReadClient())
    assert SENSITIVE_KEY not in repr(reader)
    assert SENSITIVE_SECRET not in repr(reader)
    assert not hasattr(reader, "raw_trading_client")
    for capability in (
        "submit_order",
        "cancel_order",
        "replace_order",
        "close_position",
        "liquidate",
        "get_orders",
    ):
        assert not hasattr(reader, capability)


def test_response_identity_mismatch_is_blocked_after_one_read() -> None:
    raw_client = FakeSdkReadClient(client_order_id="different-client-order")
    reader = _reader(raw_client)
    identity, authorization, request = _authorized_request()

    result = observe_exact_paper_cancellation(
        identity,
        authorization,
        request,
        read_exact_order=reader,
    )

    assert result.status is PaperCancellationObservationStatus.BLOCKED
    assert result.blocker is not None
    assert result.blocker.value == "client_order_id_mismatch"
    assert result.read_count == 1
    assert raw_client.calls == ["get_account", "get_order_by_id:broker-order-1"]
