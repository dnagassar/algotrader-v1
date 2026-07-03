from datetime import UTC, datetime
from decimal import Decimal
import logging
import requests
import socket

import pytest

from algotrader.config import AlpacaPaperConfig, ConfigValidationError
from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.execution.alpaca_adapter import (
    AlpacaAdapterError,
    AlpacaClientAdapter,
)
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderResponse,
    AlpacaOrderRequest,
    AlpacaOrderSubmissionResponse,
    AlpacaRecentOrderQuery,
    AlpacaPositionResponse,
    V189_SPY_CERTIFICATION_CLIENT_ORDER_ID,
)
import algotrader.execution.alpaca_sdk_client as alpaca_sdk_client_module
from algotrader.execution.alpaca_sdk_client import (
    AlpacaSdkClient,
    AlpacaSdkClientError,
)
from algotrader.execution.alpaca_sdk_client import (
    _create_trading_client,
    _to_sdk_get_orders_request,
    _to_sdk_order_request,
)
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 4, 30, tzinfo=UTC)
SENSITIVE_API_KEY = "sensitive-test-api-key-NEVER-LOG"
SENSITIVE_SECRET_KEY = "sensitive-test-secret-key-NEVER-LOG"
API_ERROR_URL = "https://paper.example.test/v2/orders"


class APIError(Exception):
    """Fake Alpaca APIError shape for offline diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 422,
        code: str = "42210000",
    ) -> None:
        super().__init__(message)
        self._message = message
        self._status_code = status_code
        self._code = code

    @property
    def message(self) -> str:
        return self._message

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def code(self) -> str:
        return self._code


class FakeSdkTradingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.order_queries: list[AlpacaRecentOrderQuery] = []
        self.submitted_orders: list[AlpacaOrderRequest] = []

    def get_account(self) -> AlpacaAccountResponse:
        self.calls.append("get_account")
        return AlpacaAccountResponse(
            account_id="paper-account-1",
            status="ACTIVE",
            cash=Decimal("100000"),
            buying_power=Decimal("200000"),
            equity=Decimal("100000"),
        )

    def get_all_assets(self) -> list[dict[str, object]]:
        self.calls.append("get_all_assets")
        return [
            {
                "symbol": "BTC/USD",
                "asset_class": "crypto",
                "tradable": True,
                "status": "active",
            }
        ]

    def get_all_positions(self) -> list[AlpacaPositionResponse]:
        self.calls.append("get_all_positions")
        return [
            AlpacaPositionResponse(
                symbol="MSFT",
                qty=Decimal("3"),
                market_value=Decimal("300.30"),
                average_entry_price=Decimal("100.10"),
            )
        ]

    def submit_order(
        self, request: AlpacaOrderRequest
    ) -> AlpacaOrderSubmissionResponse:
        self.calls.append("submit_order")
        self.submitted_orders.append(request)
        return AlpacaOrderSubmissionResponse(
            order_id="broker-order-1",
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            side=request.side,
            qty=request.qty,
            status="accepted",
            submitted_at=NOW,
        )

    def get_orders(
        self,
        query: AlpacaRecentOrderQuery,
    ) -> list[AlpacaOrderResponse]:
        self.calls.append("get_orders")
        self.order_queries.append(query)
        return [
            AlpacaOrderResponse(
                order_id="broker-order-1",
                client_order_id="client-order-1",
                symbol="MSFT",
                side="buy",
                status="accepted",
                qty=Decimal("1"),
                asset_class="equity",
            )
        ]


class FailingSdkTradingClient(FakeSdkTradingClient):
    def submit_order(self, request: AlpacaOrderRequest):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_orders.append(request)
        raise RuntimeError(f"{SENSITIVE_API_KEY} submit failed locally")


class FailingApiErrorSdkTradingClient(FakeSdkTradingClient):
    def submit_order(self, request):  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_orders.append(request)
        raise APIError(
            f"invalid crypto order at {API_ERROR_URL} token={SENSITIVE_SECRET_KEY}"
        )


def valid_config(
    api_key: str = "test-api-key",
    secret_key: str = "test-secret-key",
) -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key=api_key,
        alpaca_secret_key=secret_key,
        alpaca_paper_base_url="https://paper.example.test",
    )


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def proposed_order() -> ProposedOrder:
    return ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")


def test_alpaca_sdk_client_requires_paper_profile_before_factory_creation() -> None:
    factory_calls: list[AlpacaPaperConfig] = []
    config = AlpacaPaperConfig(
        app_profile="dev",
        alpaca_api_key="test-api-key",
        alpaca_secret_key="test-secret-key",
        alpaca_paper_base_url="https://paper.example.test",
    )

    def factory(config: AlpacaPaperConfig) -> FakeSdkTradingClient:
        factory_calls.append(config)
        return FakeSdkTradingClient()

    with pytest.raises(ConfigValidationError, match="APP_PROFILE=paper"):
        AlpacaSdkClient(config, sdk_client_factory=factory)

    assert factory_calls == []


def test_alpaca_sdk_client_constructs_with_valid_paper_config_factory() -> None:
    factory_calls: list[AlpacaPaperConfig] = []
    config = valid_config()

    def factory(config: AlpacaPaperConfig) -> FakeSdkTradingClient:
        factory_calls.append(config)
        return FakeSdkTradingClient()

    client = AlpacaSdkClient(config, sdk_client_factory=factory)

    assert isinstance(client, AlpacaSdkClient)
    assert factory_calls == [config]
    assert client.raw_trading_client.__class__.__name__ == "FakeSdkTradingClient"


def test_alpaca_sdk_client_delegates_protocol_methods_to_sdk_client() -> None:
    fake_sdk_client = FakeSdkTradingClient()
    client = AlpacaSdkClient(valid_config(), sdk_client=fake_sdk_client)
    request = AlpacaOrderRequest(
        client_order_id="deterministic-order-1",
        symbol="MSFT",
        side="buy",
        qty=Decimal("1"),
    )

    account = client.get_account()
    assets = client.list_assets()
    positions = client.get_positions()
    result = client.submit_order(request)

    assert account.account_id == "paper-account-1"
    assert assets[0]["symbol"] == "BTC/USD"
    assert positions[0].symbol == "MSFT"
    assert result.client_order_id == "deterministic-order-1"
    assert fake_sdk_client.calls == [
        "get_account",
        "get_all_assets",
        "get_all_positions",
        "submit_order",
    ]
    assert fake_sdk_client.submitted_orders == [request]


def test_alpaca_sdk_client_remains_compatible_with_existing_adapter() -> None:
    fake_sdk_client = FakeSdkTradingClient()
    client = AlpacaSdkClient(valid_config(), sdk_client=fake_sdk_client)
    adapter = AlpacaClientAdapter(client)

    account = adapter.get_account()
    assets = adapter.list_assets()
    positions = adapter.list_positions()
    result = adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="adapter-order-1",
    )

    assert account.cash == Decimal("100000")
    assert assets[0]["asset_class"] == "crypto"
    assert positions[0].symbol == "MSFT"
    assert result.accepted is True
    assert fake_sdk_client.submitted_orders[0].client_order_id == "adapter-order-1"


def test_alpaca_sdk_client_forwards_internal_recent_order_query_to_fake_client() -> None:
    fake_sdk_client = FakeSdkTradingClient()
    client = AlpacaSdkClient(valid_config(), sdk_client=fake_sdk_client)
    query = AlpacaRecentOrderQuery(symbol_filter="msft")

    orders = client.get_orders(query)

    assert orders[0].symbol == "MSFT"
    assert fake_sdk_client.calls == ["get_orders"]
    assert fake_sdk_client.order_queries == [query]


def test_recent_order_query_uses_sdk_get_orders_request_shape() -> None:
    query = AlpacaRecentOrderQuery(symbol_filter="BTCUSD", side_filter="buy")

    sdk_query = _to_sdk_get_orders_request(query)

    assert sdk_query.__class__.__name__ == "GetOrdersRequest"
    assert sdk_query.status.value == "open"
    assert sdk_query.limit == 100
    assert sdk_query.direction.value == "desc"
    assert sdk_query.nested is False
    assert sdk_query.side.value == "buy"
    assert sdk_query.symbols == ["BTCUSD"]


def test_crypto_notional_request_uses_sdk_market_shape_without_qty() -> None:
    request = AlpacaOrderRequest(
        client_order_id="paper-order-probe-crypto-shape",
        symbol="BTCUSD",
        side="buy",
        asset_class="crypto",
        notional=Decimal("1.00"),
        time_in_force="gtc",
    )

    sdk_request = _to_sdk_order_request(request)

    assert sdk_request.__class__.__name__ == "MarketOrderRequest"
    assert sdk_request.symbol == "BTCUSD"
    assert sdk_request.client_order_id == "paper-order-probe-crypto-shape"
    assert sdk_request.qty is None
    assert Decimal(str(sdk_request.notional)) == Decimal("1.0")
    assert sdk_request.side.value == "buy"
    assert sdk_request.type.value == "market"
    assert sdk_request.time_in_force.value == "gtc"


def test_v189_certification_request_uses_sdk_limit_shape() -> None:
    request = AlpacaOrderRequest(
        client_order_id=V189_SPY_CERTIFICATION_CLIENT_ORDER_ID,
        symbol="SPY",
        side="sell",
        asset_class="equity",
        qty=Decimal("0.0001"),
        order_type="limit",
        time_in_force="day",
        limit_price=Decimal("650.01"),
    )

    sdk_request = _to_sdk_order_request(request)

    assert sdk_request.__class__.__name__ == "LimitOrderRequest"
    assert sdk_request.symbol == "SPY"
    assert sdk_request.client_order_id == V189_SPY_CERTIFICATION_CLIENT_ORDER_ID
    assert Decimal(str(sdk_request.qty)) == Decimal("0.0001")
    assert sdk_request.notional is None
    assert Decimal(str(sdk_request.limit_price)) == Decimal("650.01")
    assert sdk_request.side.value == "sell"
    assert sdk_request.type.value == "limit"
    assert sdk_request.time_in_force.value == "day"


def test_alpaca_sdk_client_reports_sanitized_submit_stage() -> None:
    fake_sdk_client = FailingSdkTradingClient()
    client = AlpacaSdkClient(
        valid_config(api_key=SENSITIVE_API_KEY),
        sdk_client_factory=lambda _: fake_sdk_client,
    )
    request = AlpacaOrderRequest(
        client_order_id="paper-order-probe-crypto-submit-failure",
        symbol="BTCUSD",
        side="buy",
        asset_class="crypto",
        notional=Decimal("1.00"),
        time_in_force="gtc",
    )

    with pytest.raises(AlpacaSdkClientError) as exc_info:
        client.submit_order(request)

    message = str(exc_info.value)
    assert exc_info.value.error_stage == "submit_call_failed_before_response"
    assert "asset_class=crypto" in message
    assert "symbol=BTCUSD" in message
    assert "time_in_force=gtc" in message
    assert "sizing_mode=notional" in message
    assert "cause_type=RuntimeError" in message
    assert SENSITIVE_API_KEY not in message


def test_alpaca_sdk_client_reports_sanitized_api_error_diagnostics() -> None:
    fake_sdk_client = FailingApiErrorSdkTradingClient()
    client = AlpacaSdkClient(
        valid_config(api_key=SENSITIVE_API_KEY, secret_key=SENSITIVE_SECRET_KEY),
        sdk_client_factory=lambda _: fake_sdk_client,
    )
    request = AlpacaOrderRequest(
        client_order_id="paper-order-probe-crypto-api-error",
        symbol="BTCUSD",
        side="buy",
        asset_class="crypto",
        notional=Decimal("1.00"),
        time_in_force="gtc",
    )

    with pytest.raises(AlpacaSdkClientError) as exc_info:
        client.submit_order(request)

    message = str(exc_info.value)
    diagnostics = exc_info.value.diagnostics
    assert exc_info.value.error_stage == "submit_call_failed_before_response"
    assert diagnostics["submit_stage"] == "submit_call_failed_before_response"
    assert diagnostics["exception_class"] == "APIError"
    assert diagnostics["status_code"] == 422
    assert diagnostics["alpaca_error_code"] == "42210000"
    assert diagnostics["sanitized_message"] == (
        "invalid crypto order at <redacted_url> token=<redacted>"
    )
    assert diagnostics["request_shape"] == {
        "asset_class": "crypto",
        "symbol": "BTCUSD",
        "side": "buy",
        "order_type": "market",
        "time_in_force": "gtc",
        "sizing_mode": "notional",
    }
    assert "api_status_code=422" in message
    assert "alpaca_error_code=42210000" in message
    assert "api_error_message=invalid crypto order" in message
    assert API_ERROR_URL not in message
    assert SENSITIVE_API_KEY not in message
    assert SENSITIVE_SECRET_KEY not in message


def test_alpaca_sdk_client_reports_sanitized_request_construction_stage(
    monkeypatch,
) -> None:
    fake_sdk_client = FakeSdkTradingClient()
    client = AlpacaSdkClient(
        valid_config(api_key=SENSITIVE_API_KEY),
        sdk_client_factory=lambda _: fake_sdk_client,
    )
    request = AlpacaOrderRequest(
        client_order_id="paper-order-probe-crypto-build-failure",
        symbol="BTCUSD",
        side="buy",
        asset_class="crypto",
        notional=Decimal("1.00"),
        time_in_force="gtc",
    )

    def fail_request_build(request: AlpacaOrderRequest):  # noqa: ANN001
        raise ValueError(f"{SENSITIVE_API_KEY} build failed locally")

    monkeypatch.setattr(
        alpaca_sdk_client_module,
        "_to_sdk_order_request",
        fail_request_build,
    )

    with pytest.raises(AlpacaSdkClientError) as exc_info:
        client.submit_order(request)

    message = str(exc_info.value)
    assert exc_info.value.error_stage == "request_construction_failed"
    assert "asset_class=crypto" in message
    assert "symbol=BTCUSD" in message
    assert "cause_type=ValueError" in message
    assert SENSITIVE_API_KEY not in message
    assert fake_sdk_client.calls == []


def test_adapter_surfaces_sanitized_sdk_submit_stage_without_response() -> None:
    client = AlpacaSdkClient(
        valid_config(api_key=SENSITIVE_API_KEY),
        sdk_client_factory=lambda _: FailingSdkTradingClient(),
    )
    adapter = AlpacaClientAdapter(client)
    request = AlpacaOrderRequest(
        client_order_id="paper-order-probe-crypto-adapter-failure",
        symbol="BTCUSD",
        side="buy",
        asset_class="crypto",
        notional=Decimal("1.00"),
        time_in_force="gtc",
    )

    with pytest.raises(AlpacaAdapterError) as exc_info:
        adapter.submit_order_request(
            request,
            risk_verdict=RiskVerdict.allow(order_notional=request.notional),
        )

    message = str(exc_info.value)
    assert "failed before response: submit_order()" in message
    assert "cause_type=AlpacaSdkClientError" in message
    assert "submit_call_failed_before_response" in message
    assert "asset_class=crypto" in message
    assert "symbol=BTCUSD" in message
    assert SENSITIVE_API_KEY not in message


def test_adapter_preserves_sdk_api_error_diagnostics_without_response() -> None:
    client = AlpacaSdkClient(
        valid_config(api_key=SENSITIVE_API_KEY, secret_key=SENSITIVE_SECRET_KEY),
        sdk_client_factory=lambda _: FailingApiErrorSdkTradingClient(),
    )
    adapter = AlpacaClientAdapter(client)
    request = AlpacaOrderRequest(
        client_order_id="paper-order-probe-crypto-adapter-api-error",
        symbol="BTCUSD",
        side="buy",
        asset_class="crypto",
        notional=Decimal("1.00"),
        time_in_force="gtc",
    )

    with pytest.raises(AlpacaAdapterError) as exc_info:
        adapter.submit_order_request(
            request,
            risk_verdict=RiskVerdict.allow(order_notional=request.notional),
        )

    message = str(exc_info.value)
    diagnostics = exc_info.value.diagnostics
    assert "failed before response: submit_order()" in message
    assert diagnostics["submit_stage"] == "submit_call_failed_before_response"
    assert diagnostics["exception_class"] == "APIError"
    assert diagnostics["status_code"] == 422
    assert diagnostics["alpaca_error_code"] == "42210000"
    assert diagnostics["sanitized_message"] == (
        "invalid crypto order at <redacted_url> token=<redacted>"
    )
    assert API_ERROR_URL not in message
    assert SENSITIVE_API_KEY not in message
    assert SENSITIVE_SECRET_KEY not in message


def test_alpaca_sdk_client_construction_makes_no_network_calls(monkeypatch) -> None:
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("wrapper construction must not call the network")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)
    monkeypatch.setattr(socket, "socket", fail_on_network)

    factory_calls: list[AlpacaPaperConfig] = []
    config = valid_config()

    def factory(config: AlpacaPaperConfig) -> FakeSdkTradingClient:
        factory_calls.append(config)
        return FakeSdkTradingClient()

    client = AlpacaSdkClient(config, sdk_client_factory=factory)

    assert isinstance(client, AlpacaSdkClient)
    assert factory_calls == [config]


def test_default_trading_client_factory_constructs_without_network(
    monkeypatch,
) -> None:
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network call attempted")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)
    monkeypatch.setattr(socket, "socket", fail_on_network)
    monkeypatch.setattr(requests.sessions.Session, "request", fail_on_network)

    client = _create_trading_client(valid_config())

    assert client is not None
    assert client.__class__.__name__ == "TradingClient"


def test_alpaca_sdk_client_does_not_expose_sensitive_config_surfaces(
    caplog,
    capsys,
) -> None:
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="alpaca")
    caplog.set_level(logging.DEBUG, logger="httpx")
    fake_sdk_client = FakeSdkTradingClient()
    config = valid_config(
        api_key=SENSITIVE_API_KEY,
        secret_key=SENSITIVE_SECRET_KEY,
    )

    client = AlpacaSdkClient(config, sdk_client=fake_sdk_client)

    invalid_config = AlpacaPaperConfig(
        app_profile="dev",
        alpaca_api_key=SENSITIVE_API_KEY,
        alpaca_secret_key=SENSITIVE_SECRET_KEY,
        alpaca_paper_base_url="https://paper.example.test",
    )
    with pytest.raises(ConfigValidationError) as exc_info:
        AlpacaSdkClient(invalid_config, sdk_client_factory=lambda _: fake_sdk_client)

    readiness_failure_config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key=SENSITIVE_API_KEY,
        alpaca_secret_key="",
        alpaca_paper_base_url="https://paper.example.test",
    )
    with pytest.raises(ConfigValidationError) as readiness_exc_info:
        AlpacaSdkClient(
            readiness_failure_config,
            sdk_client_factory=lambda _: fake_sdk_client,
        )

    with pytest.raises(ValueError) as conflict_info:
        AlpacaSdkClient(
            config,
            sdk_client=fake_sdk_client,
            sdk_client_factory=lambda _: fake_sdk_client,
        )

    captured = capsys.readouterr()
    surfaces = "\n".join(
        [
            repr(config),
            str(config),
            repr(client),
            str(client),
            str(exc_info.value),
            str(readiness_exc_info.value),
            str(conflict_info.value),
            captured.out,
            captured.err,
            "\n".join(record.getMessage() for record in caplog.records),
        ]
    )

    assert SENSITIVE_API_KEY not in surfaces
    assert SENSITIVE_SECRET_KEY not in surfaces
