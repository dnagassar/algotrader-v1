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
    AlpacaRecentOrderQuery,
    AlpacaPositionResponse,
    RECENT_ORDER_QUERY_CONTRACT_VERSION,
)


class FakeAlpacaClient:
    def __init__(self) -> None:
        self.submitted_orders: list[AlpacaOrderRequest] = []
        self.order_queries: list[AlpacaRecentOrderQuery | None] = []

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

    def get_orders(
        self,
        query: AlpacaRecentOrderQuery | None = None,
    ) -> list[dict[str, object]]:
        self.order_queries.append(query)
        return []


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


def test_m355_spy_close_request_is_the_only_allowed_equity_sell_shape():
    request = AlpacaOrderRequest(
        client_order_id="paper-order-close-m355_spy_paper_close_submit",
        symbol="SPY",
        side="sell",
        asset_class="equity",
        qty=Decimal("0.032905647"),
        order_type="market",
        time_in_force="day",
    )

    assert request.symbol == "SPY"
    assert request.side == "sell"
    assert request.asset_class == "equity"
    assert request.qty == Decimal("0.032905647")
    assert request.notional is None
    assert request.time_in_force == "day"

    with pytest.raises(ValueError, match="explicit M355 SPY paper close"):
        AlpacaOrderRequest(
            client_order_id="paper-order-close-other",
            symbol="SPY",
            side="sell",
            asset_class="equity",
            qty=Decimal("0.032905647"),
            order_type="market",
            time_in_force="day",
        )

    with pytest.raises(ValueError, match="explicit M355 SPY paper close"):
        AlpacaOrderRequest(
            client_order_id="paper-order-close-m355_spy_paper_close_submit",
            symbol="SPY",
            side="sell",
            asset_class="equity",
            notional=Decimal("25.00"),
            order_type="market",
            time_in_force="day",
        )


def test_recent_order_query_defaults_are_deterministic_contract():
    query = AlpacaRecentOrderQuery()

    assert query.contract_version == RECENT_ORDER_QUERY_CONTRACT_VERSION
    assert query.status_filter == "open"
    assert query.limit == 100
    assert query.direction == "desc"
    assert query.nested is False
    assert query.symbol_filter == ""
    assert query.asset_class_filter == ""
    assert query.side_filter == ""
    assert query.after is None
    assert query.until is None
    assert query.sort == ""
    assert query.source == "alpaca_sdk_client.get_orders"


def test_fake_alpaca_client_accepts_recent_order_query_without_credentials():
    client = FakeAlpacaClient()
    query = AlpacaRecentOrderQuery(symbol_filter="spy")

    orders = client.get_orders(query)

    assert orders == []
    assert query.symbol_filter == "SPY"
    assert client.order_queries == [query]


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
    client.get_orders(AlpacaRecentOrderQuery())
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
