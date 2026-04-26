from datetime import datetime, timezone
from decimal import Decimal

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.execution.fake_broker import LocalBroker
from algotrader.portfolio.state import Account, PortfolioState
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 4, 26, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def portfolio(cash: str = "1000") -> PortfolioState:
    return PortfolioState(account=Account(cash))


def approved_risk(order: ProposedOrder, state: PortfolioState) -> RiskVerdict:
    return RiskEngine(RiskConfig(max_order_notional="1000")).check(
        order,
        state,
        quote(),
    )


def rejected_risk() -> RiskVerdict:
    return RiskVerdict.reject("contract_rejected")


def broker_factory():
    """Swap this factory to compare future broker adapters against the contract."""

    return LocalBroker


def test_broker_exposes_account_and_positions() -> None:
    broker = broker_factory()(portfolio())

    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_positions() == ()


def test_broker_refuses_submission_without_required_risk_approval() -> None:
    broker = broker_factory()(portfolio())
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    result = broker.submit_order(order, quote())

    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is False
    assert result.reason == "risk_approval_required"
    assert result.execution is None
    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_positions() == ()


def test_broker_refuses_submission_with_rejected_risk_verdict() -> None:
    broker = broker_factory()(portfolio())
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    result = broker.submit_order(order, quote(), rejected_risk())

    assert result.accepted is False
    assert result.reason == "contract_rejected"
    assert result.execution is None
    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_positions() == ()


def test_broker_accepts_approved_order_and_returns_structured_result() -> None:
    state = portfolio()
    broker = broker_factory()(state)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    result = broker.submit_order(order, quote(), approved_risk(order, state))

    assert isinstance(result, BrokerOrderResult)
    assert result.accepted is True
    assert result.reason == ""
    assert result.execution is not None
    assert result.portfolio is not None


def test_broker_fills_marketable_order_with_local_paper_behavior() -> None:
    state = portfolio()
    broker = broker_factory()(state)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    result = broker.submit_order(order, quote(), approved_risk(order, state))

    assert result.filled is True
    assert result.execution.fill.price == Decimal("100.10")
    assert broker.get_account().cash == Decimal("899.90")
    assert broker.get_positions()[0].quantity == Decimal("1")
    assert broker.get_positions()[0].average_price == Decimal("100.10")


def test_broker_does_not_mutate_for_unfilled_limit_order() -> None:
    state = portfolio()
    broker = broker_factory()(state)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.LIMIT, "1", "100.09")

    result = broker.submit_order(order, quote(), approved_risk(order, state))

    assert result.accepted is True
    assert result.filled is False
    assert result.execution.fill is None
    assert broker.get_account().cash == Decimal("1000")
    assert broker.get_positions() == ()


def test_broker_preserves_deterministic_order_ids_when_supplied() -> None:
    state = portfolio()
    broker = broker_factory()(state)
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")

    first = broker.submit_order(
        order,
        quote(),
        approved_risk(order, state),
        order_id="contract-order-1",
    )

    assert first.execution.ack.order_id == "contract-order-1"
    assert first.execution.fill.order_id == "contract-order-1"
