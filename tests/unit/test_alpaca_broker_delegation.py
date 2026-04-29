from datetime import UTC, datetime
from decimal import Decimal
import socket

import pytest

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.execution.alpaca_adapter import (
    AlpacaAdapterError,
    AlpacaClientAdapter,
)
from algotrader.execution.alpaca_broker import (
    AlpacaPaperBroker,
    BrokerNotImplementedError,
)
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


def test_alpaca_paper_broker_without_adapter_remains_inert():
    broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError):
        broker.get_account()

    with pytest.raises(BrokerNotImplementedError):
        broker.get_positions()


def test_alpaca_paper_broker_submit_order_without_adapter_remains_inert():
    broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError):
        broker.submit_order(
            proposed_order(),
            quote(),
            RiskVerdict.allow(order_notional=Decimal("100.10")),
        )


def test_broker_get_account_delegates_to_injected_fake_adapter():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    account = broker.get_account()

    assert fake_client.calls == ["get_account"]
    assert isinstance(account, Account)
    assert account.cash == Decimal("100000")
    assert account.currency == "USD"


def test_broker_list_positions_delegates_to_injected_fake_adapter():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    positions = broker.list_positions()

    assert fake_client.calls == ["get_positions"]
    assert isinstance(positions, tuple)
    assert len(positions) == 1
    assert isinstance(positions[0], Position)
    assert positions[0].symbol == "MSFT"
    assert positions[0].quantity == Decimal("3")
    assert positions[0].average_price == Decimal("100.10")


def test_broker_get_positions_delegates_to_injected_fake_adapter():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    positions = broker.get_positions()

    assert fake_client.calls == ["get_positions"]
    assert isinstance(positions, tuple)
    assert len(positions) == 1
    assert isinstance(positions[0], Position)


def test_broker_submit_order_uses_canonical_signature():
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
    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is True
    assert result.reason == ""
    assert result.execution is None
    assert result.portfolio is None


def test_broker_submit_order_rejected_path_delegates_through_adapter_mapper():
    fake_client = RejectingFakeAlpacaClient()
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


def test_broker_submit_order_risk_rejected_path_does_not_call_client():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    result = broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.reject("risk_test_rejected"),
    )

    assert fake_client.calls == []
    assert result.accepted is False
    assert result.reason == "risk_test_rejected"


def test_broker_fake_adapter_failures_surface_clearly():
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(FailingFakeAlpacaClient()))

    with pytest.raises(AlpacaAdapterError, match="get_account"):
        broker.get_account()


def test_broker_fake_adapter_path_requires_no_credentials_or_environment(
    monkeypatch,
):
    monkeypatch.delenv("APP_PROFILE", raising=False)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_PAPER_BASE_URL", raising=False)

    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(FakeAlpacaClient()))

    assert broker.get_account().cash == Decimal("100000")


def test_broker_fake_adapter_path_makes_no_network_calls(monkeypatch):
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network calls are not allowed in broker adapter tests")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(FakeAlpacaClient()))

    broker.get_account()
    broker.list_positions()
    broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
    )
