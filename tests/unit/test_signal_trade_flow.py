from datetime import datetime, timezone
from decimal import Decimal

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.orchestration.signal_trade_flow import generate_evaluate_and_execute
from algotrader.portfolio.state import Account, PortfolioState


NOW = datetime(2026, 4, 25, tzinfo=timezone.utc)


def previous_bar() -> Bar:
    return Bar("MSFT", NOW, "99", "101", "98", "100", "1000")


def quote(ask: str = "101.01") -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask=ask)


def test_no_signal_returns_no_action_result() -> None:
    portfolio = PortfolioState(account=Account("1000"))

    result = generate_evaluate_and_execute(
        previous_bar=previous_bar(),
        quote=quote("101.00"),
        portfolio=portfolio,
    )

    assert result.status == "no_signal"
    assert result.order is None
    assert result.execution is None
    assert result.portfolio == portfolio


def test_signal_order_can_be_rejected_by_risk() -> None:
    portfolio = PortfolioState(account=Account("50"))

    result = generate_evaluate_and_execute(
        previous_bar=previous_bar(),
        quote=quote(),
        portfolio=portfolio,
    )

    assert result.status == "rejected"
    assert result.order is not None
    assert result.trade_flow.risk.reason == "insufficient_cash"
    assert result.execution is None
    assert result.portfolio == portfolio


def test_signal_order_runs_fill_path() -> None:
    portfolio = PortfolioState(account=Account("1000"))

    result = generate_evaluate_and_execute(
        previous_bar=previous_bar(),
        quote=quote(),
        portfolio=portfolio,
    )

    assert result.status == "filled"
    assert result.order.side == OrderSide.BUY
    assert result.execution.filled is True
    assert result.portfolio.account.cash == Decimal("898.99")
    assert result.portfolio.position("MSFT").quantity == Decimal("1")
    assert result.valuation.total_market_value == Decimal("998.99")


def test_signal_order_can_remain_open_without_portfolio_mutation() -> None:
    def limit_signal(
        previous_bar: Bar,
        quote: Quote,
        threshold: Decimal | str,
        quantity: Decimal | str,
    ) -> ProposedOrder:
        return ProposedOrder(
            "MSFT",
            OrderSide.BUY,
            OrderType.LIMIT,
            quantity,
            limit_price="101.00",
        )

    portfolio = PortfolioState(account=Account("1000"))

    result = generate_evaluate_and_execute(
        previous_bar=previous_bar(),
        quote=quote("101.01"),
        portfolio=portfolio,
        signal_rule=limit_signal,
    )

    assert result.status == "open"
    assert result.execution.fill is None
    assert result.portfolio == portfolio
    assert result.valuation.total_market_value == Decimal("1000")


def test_invalid_input_fails_safely_and_clearly() -> None:
    portfolio = PortfolioState(account=Account("1000"))

    result = generate_evaluate_and_execute(
        previous_bar=None,
        quote=quote(),
        portfolio=portfolio,
    )

    assert result.status == "error"
    assert result.order is None
    assert result.execution is None
    assert result.portfolio == portfolio
    assert "previous_bar" in result.message
