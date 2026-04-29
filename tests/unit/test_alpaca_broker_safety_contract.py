import ast
from datetime import UTC, datetime
from decimal import Decimal
import inspect
import os
import socket
import sys

import pytest

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
import algotrader.execution.alpaca_broker as alpaca_broker_module
from algotrader.errors import BrokerNotImplementedError
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.portfolio.state import Account, Position
from algotrader.risk.state import RiskVerdict
from tests.fakes.alpaca import FakeAlpacaClient, RejectingFakeAlpacaClient


NOW = datetime(2026, 4, 28, tzinfo=UTC)


def quote() -> Quote:
    return Quote("AAPL", NOW, bid="100.00", ask="100.10")


def proposed_order() -> ProposedOrder:
    return ProposedOrder("AAPL", OrderSide.BUY, OrderType.MARKET, "1")


class ExplodingEnv(dict):
    def get(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("AlpacaPaperBroker must not read environment values")

    def __getitem__(self, key):  # noqa: ANN001
        raise AssertionError("AlpacaPaperBroker must not read environment values")

    def __contains__(self, key):  # noqa: ANN001
        raise AssertionError("AlpacaPaperBroker must not read environment values")


def test_broker_module_does_not_import_external_alpaca_sdk():
    source = inspect.getsource(alpaca_broker_module)
    tree = ast.parse(source)
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    assert "alpaca" not in imported_modules
    assert "alpaca_trade_api" not in imported_modules
    assert all(not name.startswith("alpaca.") for name in imported_modules)
    assert all(not name.startswith("alpaca_trade_api.") for name in imported_modules)


def test_importing_broker_does_not_load_external_alpaca_modules():
    external_alpaca_modules = [
        name
        for name in sys.modules
        if name == "alpaca"
        or name.startswith("alpaca.")
        or name == "alpaca_trade_api"
        or name.startswith("alpaca_trade_api.")
    ]

    assert external_alpaca_modules == []


def test_constructing_broker_requires_no_credentials(monkeypatch):
    monkeypatch.delenv("APP_PROFILE", raising=False)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_PAPER_BASE_URL", raising=False)

    broker = AlpacaPaperBroker()

    assert isinstance(broker, AlpacaPaperBroker)


def test_constructing_broker_does_not_read_environment(monkeypatch):
    monkeypatch.setattr(os, "environ", ExplodingEnv())
    monkeypatch.setattr(
        os,
        "getenv",
        lambda *args, **kwargs: (_ for _ in ()).throw(  # noqa: ANN002, ANN003
            AssertionError("AlpacaPaperBroker must not read environment values")
        ),
    )

    broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError, match="skeleton only"):
        broker.get_account()


def test_default_broker_has_no_implicit_adapter_or_client():
    broker = AlpacaPaperBroker()

    assert getattr(broker, "_adapter") is None
    assert not hasattr(broker, "_client")


def test_adapter_must_be_injected_for_operational_behavior():
    inert_broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError):
        inert_broker.get_account()

    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    account = broker.get_account()

    assert fake_client.calls == ["get_account"]
    assert isinstance(account, Account)
    assert account.cash == Decimal("100000")


def test_account_and_position_retrieval_work_only_through_injected_fake_adapter():
    fake_client = FakeAlpacaClient()
    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(fake_client))

    account = broker.get_account()
    positions = broker.list_positions()

    assert fake_client.calls == ["get_account", "get_positions"]
    assert isinstance(account, Account)
    assert account.cash == Decimal("100000")
    assert len(positions) == 1
    assert isinstance(positions[0], Position)
    assert positions[0].symbol == "MSFT"
    assert positions[0].quantity == Decimal("3")


def test_accepted_fake_order_returns_translated_broker_result():
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


def test_rejected_fake_order_returns_translated_rejection_result():
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


def test_broker_safety_contract_makes_no_network_calls(monkeypatch):
    def fail_on_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("AlpacaPaperBroker tests must not make network calls")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)
    monkeypatch.setattr(socket, "socket", fail_on_network)

    inert_broker = AlpacaPaperBroker()
    with pytest.raises(BrokerNotImplementedError):
        inert_broker.get_account()

    broker = AlpacaPaperBroker(adapter=AlpacaClientAdapter(FakeAlpacaClient()))
    broker.get_account()
    broker.list_positions()
    broker.submit_order(
        proposed_order(),
        quote(),
        RiskVerdict.allow(order_notional=Decimal("100.10")),
    )
