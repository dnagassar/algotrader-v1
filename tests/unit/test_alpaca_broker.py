from datetime import datetime, timezone

import pytest

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import BrokerNotImplementedError
from algotrader.execution import AlpacaPaperBroker
from algotrader.execution.alpaca_broker import AlpacaPaperBroker as DirectImport
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 4, 27, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def order() -> ProposedOrder:
    return ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")


def test_alpaca_paper_broker_can_be_imported() -> None:
    assert AlpacaPaperBroker is DirectImport


def test_alpaca_paper_broker_instantiates_without_credentials() -> None:
    broker = AlpacaPaperBroker()

    assert isinstance(broker, AlpacaPaperBroker)


def test_submit_order_fails_clearly_without_network_calls() -> None:
    broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError, match="skeleton only"):
        broker.submit_order(order(), quote(), RiskVerdict.allow(order_notional=100))


def test_get_account_fails_clearly_without_network_calls() -> None:
    broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError, match="performs no network calls"):
        broker.get_account()


def test_get_positions_fails_clearly_without_network_calls() -> None:
    broker = AlpacaPaperBroker()

    with pytest.raises(BrokerNotImplementedError, match="does not use credentials"):
        broker.get_positions()
