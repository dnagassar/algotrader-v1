from datetime import UTC, datetime
from decimal import Decimal
import logging
import socket

import pytest

from algotrader.config import AlpacaPaperConfig, ConfigValidationError
from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderRequest,
    AlpacaOrderSubmissionResponse,
    AlpacaPositionResponse,
)
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 4, 30, tzinfo=UTC)
SENSITIVE_SECRET = "sensitive-test-api-key-NEVER-LOG"


class FakeSdkTradingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
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


def valid_config(api_key: str = "test-api-key") -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key=api_key,
        alpaca_secret_key="test-secret-key",
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
    positions = client.get_positions()
    result = client.submit_order(request)

    assert account.account_id == "paper-account-1"
    assert positions[0].symbol == "MSFT"
    assert result.client_order_id == "deterministic-order-1"
    assert fake_sdk_client.calls == [
        "get_account",
        "get_all_positions",
        "submit_order",
    ]
    assert fake_sdk_client.submitted_orders == [request]


def test_alpaca_sdk_client_remains_compatible_with_existing_adapter() -> None:
    fake_sdk_client = FakeSdkTradingClient()
    client = AlpacaSdkClient(valid_config(), sdk_client=fake_sdk_client)
    adapter = AlpacaClientAdapter(client)

    account = adapter.get_account()
    positions = adapter.list_positions()
    result = adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="adapter-order-1",
    )

    assert account.cash == Decimal("100000")
    assert positions[0].symbol == "MSFT"
    assert result.accepted is True
    assert fake_sdk_client.submitted_orders[0].client_order_id == "adapter-order-1"


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


def test_alpaca_sdk_client_does_not_expose_sensitive_config_surfaces(
    caplog,
    capsys,
) -> None:
    caplog.set_level(logging.DEBUG)
    fake_sdk_client = FakeSdkTradingClient()
    config = valid_config(api_key=SENSITIVE_SECRET)

    client = AlpacaSdkClient(config, sdk_client=fake_sdk_client)

    invalid_config = AlpacaPaperConfig(
        app_profile="dev",
        alpaca_api_key=SENSITIVE_SECRET,
        alpaca_secret_key="test-secret-key",
        alpaca_paper_base_url="https://paper.example.test",
    )
    with pytest.raises(ConfigValidationError) as exc_info:
        AlpacaSdkClient(invalid_config, sdk_client_factory=lambda _: fake_sdk_client)

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
            str(conflict_info.value),
            captured.out,
            captured.err,
            "\n".join(record.getMessage() for record in caplog.records),
        ]
    )

    assert SENSITIVE_SECRET not in surfaces
