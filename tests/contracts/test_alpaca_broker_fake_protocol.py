"""External-state-reflecting broker contract for fake-adapter AlpacaPaperBroker."""

from datetime import UTC, datetime
from decimal import Decimal
import socket

import pytest

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import BrokerNotImplementedError
from algotrader.execution.alpaca_adapter import (
    AlpacaAdapterError,
    AlpacaClientAdapter,
)
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position
from algotrader.risk.state import RiskVerdict
from tests.fakes.alpaca import FakeAlpacaClient, FailingFakeAlpacaClient


NOW = datetime(2026, 4, 28, tzinfo=UTC)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def proposed_order() -> ProposedOrder:
    return ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")


def test_alpaca_broker_without_adapter_remains_inert_for_protocol_methods():
    broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError):
        broker.get_account()

    with pytest.raises(BrokerNotImplementedError):
        broker.get_positions()

    with pytest.raises(BrokerNotImplementedError):
        broker.submit_order(
            proposed_order(),
            quote(),
            RiskVerdict.allow(order_notional=Decimal("100.10")),
        )


def test_fake_protocol_broker_get_account_returns_internal_account():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    account = broker.get_account()

    assert fake_client.calls == ["get_account"]
    assert isinstance(account, Account)
    assert account.cash == Decimal("100000")


def test_fake_protocol_broker_get_positions_returns_internal_positions():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    positions = broker.get_positions()

    assert fake_client.calls == ["get_positions"]
    assert isinstance(positions, tuple)
    assert len(positions) == 1
    assert isinstance(positions[0], Position)
    assert positions[0].symbol == "MSFT"
    assert positions[0].quantity == Decimal("3")


def test_fake_protocol_broker_accepts_deterministic_order_model():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    result = broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-1",
    )

    assert fake_client.calls == ["submit_order"]
    assert fake_client.submitted_requests[0].client_order_id == "deterministic-order-1"
    assert fake_client.submitted_requests[0].symbol == "MSFT"
    assert fake_client.submitted_requests[0].side == "buy"
    assert fake_client.submitted_requests[0].qty == Decimal("1")
    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is True
    assert result.reason == ""
    assert result.execution is None
    assert result.portfolio is None


def test_fake_protocol_broker_rejects_duplicate_order_id_without_second_client_call():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    first = broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-1",
    )
    second = broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-1",
    )

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "duplicate_order_id"
    assert second.execution is None
    assert second.portfolio is None
    assert fake_client.calls == ["submit_order"]
    assert len(fake_client.submitted_requests) == 1
    assert fake_client.submitted_requests[0].client_order_id == "deterministic-order-1"


def test_fake_protocol_broker_rejected_order_returns_clear_result():
    fake_client = FakeAlpacaClient(order_status="rejected")
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    result = broker.submit_order(
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


def test_fake_protocol_broker_refuses_missing_risk_approval():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    result = broker.submit_order(proposed_order(), quote())

    assert fake_client.calls == []
    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is False
    assert result.reason == "risk_approval_required"


def test_fake_protocol_broker_refuses_rejected_risk_verdict():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    result = broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.reject("contract_rejected"),
    )

    assert fake_client.calls == []
    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is False
    assert result.reason == "contract_rejected"


def test_fake_protocol_broker_surfaces_adapter_failures_clearly():
    fake_client = FailingFakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    with pytest.raises(AlpacaAdapterError, match="get_account"):
        broker.get_account()


def test_fake_protocol_broker_makes_no_network_calls(monkeypatch):
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("fake-only Alpaca broker protocol tests are offline")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)
    monkeypatch.setattr(socket, "socket", fail_on_network)

    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    broker.get_account()
    broker.get_positions()
    broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
        order_id="deterministic-order-3",
    )
