from datetime import datetime, timezone
from decimal import Decimal

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.execution.local_broker import LocalBroker
from algotrader.portfolio.state import Account, PortfolioState
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine


NOW = datetime(2026, 4, 26, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def risk_verdict(order: ProposedOrder, portfolio: PortfolioState):
    return RiskEngine(RiskConfig(max_order_notional="1000")).check(
        order,
        portfolio,
        quote(),
    )


def test_fake_broker_import_path_reexports_local_broker() -> None:
    from algotrader.execution.fake_broker import LocalBroker as CompatLocalBroker

    assert CompatLocalBroker is LocalBroker


def test_broker_accepts_risk_approved_order_and_fills_locally() -> None:
    portfolio = PortfolioState(account=Account("1000"))
    broker = LocalBroker(portfolio)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "2")

    result = broker.submit_order(order, quote(), risk_verdict(order, portfolio))

    assert result.accepted is True
    assert result.filled is True
    assert broker.get_account().cash == Decimal("799.80")
    assert broker.get_positions()[0].quantity == Decimal("2")


def test_broker_refuses_submission_without_risk_approval() -> None:
    portfolio = PortfolioState(account=Account("1000"))
    broker = LocalBroker(portfolio)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "2")

    result = broker.submit_order(order, quote())

    assert result.accepted is False
    assert result.reason == "risk_approval_required"
    assert result.execution is None
    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_positions() == ()


def test_get_account_returns_current_local_account() -> None:
    portfolio = PortfolioState(account=Account("1000"))
    broker = LocalBroker(portfolio)

    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_account().currency == "USD"


def test_get_positions_returns_positions_after_fill() -> None:
    portfolio = PortfolioState(account=Account("1000"))
    broker = LocalBroker(portfolio)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    broker.submit_order(order, quote(), risk_verdict(order, portfolio))

    positions = broker.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "MSFT"
    assert positions[0].quantity == Decimal("1")


def test_unfilled_limit_order_does_not_mutate_positions() -> None:
    portfolio = PortfolioState(account=Account("1000"))
    broker = LocalBroker(portfolio)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.LIMIT, "1", "100.09")

    result = broker.submit_order(order, quote(), risk_verdict(order, portfolio))

    assert result.accepted is True
    assert result.filled is False
    assert result.execution.fill is None
    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_positions() == ()
