from datetime import datetime, timezone
from decimal import Decimal

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.orchestration.trade_flow import evaluate_and_execute
from algotrader.portfolio.state import Account, PortfolioState
from algotrader.risk.config import RiskConfig


NOW = datetime(2026, 4, 25, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def test_allowed_order_fills_updates_portfolio_and_valuation() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "2")
    portfolio = PortfolioState(account=Account("1000"))

    result = evaluate_and_execute(order, portfolio, quote())

    assert result.status == "filled"
    assert result.risk.allowed is True
    assert result.execution.filled is True
    assert result.portfolio.account.cash == Decimal("799.80")
    assert result.portfolio.position("MSFT").quantity == Decimal("2")
    assert result.valuation.total_market_value == Decimal("999.80")
    assert result.valuation.total_unrealized_pnl == Decimal("-0.20")


def test_rejected_order_has_no_fill_and_keeps_portfolio_unchanged() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "2")
    portfolio = PortfolioState(account=Account("100"))

    result = evaluate_and_execute(order, portfolio, quote())

    assert result.status == "rejected"
    assert result.risk.reason == "insufficient_cash"
    assert result.execution is None
    assert result.portfolio == portfolio
    assert result.valuation is None


def test_unfilled_limit_order_does_not_mutate_portfolio() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.LIMIT, "2", "100.09")
    portfolio = PortfolioState(account=Account("1000"))

    result = evaluate_and_execute(order, portfolio, quote())

    assert result.status == "open"
    assert result.execution.filled is False
    assert result.execution.fill is None
    assert result.portfolio == portfolio
    assert result.valuation.total_market_value == Decimal("1000")


def test_invalid_input_fails_safely_and_clearly() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    risk_config = RiskConfig(max_order_notional="1000")

    result = evaluate_and_execute(order, portfolio=None, quote=quote(), risk_config=risk_config)

    assert result.status == "rejected"
    assert result.risk.allowed is False
    assert result.risk.reason == "invalid_risk_input"
    assert result.portfolio is None
    assert result.execution is None
