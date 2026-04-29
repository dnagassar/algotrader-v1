from datetime import UTC, datetime
from decimal import Decimal
from importlib import import_module
import socket

import pytest

from algotrader.errors import BrokerNotImplementedError
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderRequest,
    AlpacaOrderSubmissionResponse,
    AlpacaPositionResponse,
)


class FakeAlpacaClient:
    def __init__(self) -> None:
        self.submitted_orders: list[AlpacaOrderRequest] = []

    def get_account(self) -> AlpacaAccountResponse:
        return AlpacaAccountResponse(
            account_id="paper-account-1",
            status="ACTIVE",
            cash=Decimal("100000"),
            buying_power=Decimal("200000"),
            equity=Decimal("100000"),
        )

    def get_positions(self) -> list[AlpacaPositionResponse]:
        return [
            AlpacaPositionResponse(
                symbol="AAPL",
                qty=Decimal("5"),
                market_value=Decimal("950"),
                average_entry_price=Decimal("180"),
            )
        ]

    def submit_order(
        self, request: AlpacaOrderRequest
    ) -> AlpacaOrderSubmissionResponse:
        self.submitted_orders.append(request)
        return AlpacaOrderSubmissionResponse(
            order_id="broker-order-1",
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            side=request.side,
            qty=request.qty,
            status="accepted",
            submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_fake_alpaca_client_can_return_account_like_data():
    client = FakeAlpacaClient()

    account = client.get_account()

    assert account.account_id == "paper-account-1"
    assert account.status == "ACTIVE"
    assert account.cash == Decimal("100000")
    assert account.buying_power == Decimal("200000")
    assert account.equity == Decimal("100000")
    assert account.currency == "USD"


def test_fake_alpaca_client_can_return_position_like_data():
    client = FakeAlpacaClient()

    positions = client.get_positions()

    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].qty == Decimal("5")
    assert positions[0].market_value == Decimal("950")
    assert positions[0].average_entry_price == Decimal("180")
    assert positions[0].side == "long"


def test_fake_alpaca_client_can_return_order_submission_like_data():
    client = FakeAlpacaClient()
    request = AlpacaOrderRequest(
        client_order_id="deterministic-order-1",
        symbol="AAPL",
        side="buy",
        qty=Decimal("1"),
    )

    response = client.submit_order(request)

    assert response.order_id == "broker-order-1"
    assert response.client_order_id == "deterministic-order-1"
    assert response.symbol == "AAPL"
    assert response.side == "buy"
    assert response.qty == Decimal("1")
    assert response.status == "accepted"
    assert client.submitted_orders == [request]


def test_fake_alpaca_client_requires_no_credentials(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

    client = FakeAlpacaClient()

    assert client.get_account().status == "ACTIVE"


def test_fake_alpaca_client_makes_no_network_calls(monkeypatch):
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network calls are not allowed in fake client tests")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    client = FakeAlpacaClient()

    client.get_account()
    client.get_positions()
    client.submit_order(
        AlpacaOrderRequest(
            client_order_id="deterministic-order-1",
            symbol="AAPL",
            side="buy",
            qty=Decimal("1"),
        )
    )


def _load_alpaca_paper_broker_class():
    module_names = (
        "algotrader.execution.alpaca_broker",
        "algotrader.brokers.alpaca",
        "algotrader.alpaca_broker",
    )

    for module_name in module_names:
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            continue

        broker_class = getattr(module, "AlpacaPaperBroker", None)
        if broker_class is not None:
            return broker_class

    pytest.fail("AlpacaPaperBroker skeleton could not be found")


def test_existing_alpaca_paper_broker_skeleton_remains_inert():
    broker_class = _load_alpaca_paper_broker_class()
    broker = broker_class()

    with pytest.raises(BrokerNotImplementedError):
        broker.get_account()

    with pytest.raises(BrokerNotImplementedError):
        broker.get_positions()
