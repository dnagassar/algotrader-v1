from datetime import UTC, datetime
from decimal import Decimal
import socket

import pytest

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.execution.alpaca_adapter import (
    AlpacaAdapterError,
    AlpacaClientAdapter,
)
from algotrader.execution.alpaca_client import AlpacaOrderRequest
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position
from algotrader.risk.state import RiskVerdict
from tests.fakes.alpaca import (
    FakeAlpacaClient,
    FailingFakeAlpacaClient,
    RejectingFakeAlpacaClient,
)


NOW = datetime(2026, 4, 28, tzinfo=UTC)


def quote() -> Quote:
    return Quote("AAPL", NOW, bid="100.00", ask="100.10")


def proposed_order() -> ProposedOrder:
    return ProposedOrder("AAPL", OrderSide.BUY, OrderType.MARKET, "1")


class FakeGetAllPositionsClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_all_positions(self) -> list[dict[str, str]]:
        self.calls.append("get_all_positions")
        return [
            {
                "symbol": "MSFT",
                "qty": "2",
                "market_value": "800",
                "average_entry_price": "390",
            }
        ]


def test_adapter_get_account_calls_fake_client_and_returns_internal_account():
    fake_client = FakeAlpacaClient()
    adapter = AlpacaClientAdapter(fake_client)

    account = adapter.get_account()

    assert fake_client.calls == ["get_account"]
    assert isinstance(account, Account)
    assert account.cash == Decimal("100000")
    assert account.currency == "USD"


def test_adapter_list_positions_calls_fake_client_and_returns_internal_positions():
    fake_client = FakeAlpacaClient()
    adapter = AlpacaClientAdapter(fake_client)

    positions = adapter.list_positions()

    assert fake_client.calls == ["get_positions"]
    assert isinstance(positions, tuple)
    assert len(positions) == 1
    assert isinstance(positions[0], Position)
    assert positions[0].symbol == "MSFT"
    assert positions[0].quantity == Decimal("3")
    assert positions[0].average_price == Decimal("100.10")


def test_adapter_list_positions_can_use_get_all_positions_fake_method():
    fake_client = FakeGetAllPositionsClient()
    adapter = AlpacaClientAdapter(fake_client)

    positions = adapter.list_positions()

    assert fake_client.calls == ["get_all_positions"]
    assert len(positions) == 1
    assert isinstance(positions[0], Position)
    assert positions[0].symbol == "MSFT"
    assert positions[0].quantity == Decimal("2")
    assert positions[0].average_price == Decimal("390")


def test_adapter_submit_order_uses_canonical_broker_shape():
    fake_client = FakeAlpacaClient()
    adapter = AlpacaClientAdapter(fake_client)

    result = adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-1",
    )

    assert fake_client.calls == ["submit_order"]
    assert fake_client.submitted_requests == [
        AlpacaOrderRequest(
            client_order_id="deterministic-order-1",
            symbol="AAPL",
            side="buy",
            qty=Decimal("1"),
            order_type="market",
        )
    ]
    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is True
    assert result.reason == ""
    assert result.execution is None
    assert result.portfolio is None


def test_adapter_rejects_duplicate_client_order_id_without_second_client_call():
    fake_client = FakeAlpacaClient()
    adapter = AlpacaClientAdapter(fake_client)

    first = adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-1",
    )
    second = adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-1",
    )

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "duplicate_order_id"
    assert second.execution is None
    assert fake_client.calls == ["submit_order"]
    assert len(fake_client.submitted_requests) == 1
    assert fake_client.submitted_requests[0].client_order_id == "deterministic-order-1"


def test_adapter_rejects_missing_risk_approval_without_calling_client():
    fake_client = FakeAlpacaClient()
    adapter = AlpacaClientAdapter(fake_client)

    result = adapter.submit_order(proposed_order(), quote())

    assert fake_client.calls == []
    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is False
    assert result.reason == "risk_approval_required"


def test_adapter_rejects_failed_risk_verdict_without_calling_client():
    fake_client = FakeAlpacaClient()
    adapter = AlpacaClientAdapter(fake_client)

    result = adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.reject("risk_test_rejected"),
    )

    assert fake_client.calls == []
    assert result.accepted is False
    assert result.reason == "risk_test_rejected"


def test_adapter_rejected_fake_order_response_maps_to_broker_result():
    fake_client = RejectingFakeAlpacaClient()
    adapter = AlpacaClientAdapter(fake_client)

    result = adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-2",
    )

    assert fake_client.calls == ["submit_order"]
    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is False
    assert result.reason == "insufficient buying power"
    assert result.execution is None
    assert result.portfolio is None


def test_adapter_fake_client_call_failures_surface_clearly():
    adapter = AlpacaClientAdapter(FailingFakeAlpacaClient())

    with pytest.raises(AlpacaAdapterError, match="get_account"):
        adapter.get_account()


def test_adapter_requires_no_credentials(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

    adapter = AlpacaClientAdapter(FakeAlpacaClient())

    assert adapter.get_account().cash == Decimal("100000")


def test_adapter_makes_no_network_calls(monkeypatch):
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network calls are not allowed in adapter tests")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    adapter = AlpacaClientAdapter(FakeAlpacaClient())

    adapter.get_account()
    adapter.list_positions()
    adapter.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
    )
