from datetime import datetime, timezone
from decimal import Decimal

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.portfolio.state import Account, PortfolioState, Position
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine


NOW = datetime(2026, 4, 25, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def engine(max_order_notional: str = "1000") -> RiskEngine:
    return RiskEngine(RiskConfig(max_order_notional=max_order_notional))


def test_valid_order_passes() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))

    verdict = engine().check(order, portfolio, quote())

    assert verdict.allowed is True
    assert verdict.reason == ""
    assert verdict.order_notional == Decimal("100.10")


def test_order_rejected_for_insufficient_cash() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("50"))

    verdict = engine().check(order, portfolio, quote())

    assert verdict.allowed is False
    assert verdict.reason == "insufficient_cash"


def test_order_rejected_for_exceeding_max_order_notional() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))

    verdict = engine(max_order_notional="50").check(order, portfolio, quote())

    assert verdict.allowed is False
    assert verdict.reason == "max_order_notional_exceeded"


def test_short_order_rejected() -> None:
    order = ProposedOrder("MSFT", OrderSide.SELL, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))

    verdict = engine().check(order, portfolio, quote())

    assert verdict.allowed is False
    assert verdict.reason == "short_not_allowed"


def test_allow_short_true_still_rejects_short_selling_until_modeled_end_to_end() -> None:
    order = ProposedOrder("MSFT", OrderSide.SELL, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))
    risk_config = RiskConfig(max_order_notional="1000", allow_short=True)

    verdict = RiskEngine(risk_config).check(order, portfolio, quote())

    assert verdict.allowed is False
    assert verdict.reason == "short_selling_not_supported"


def test_invalid_quantity_rejected() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    object.__setattr__(order, "quantity", Decimal("0"))
    portfolio = PortfolioState(account=Account("500"))

    verdict = engine().check(order, portfolio, quote())

    assert verdict.allowed is False
    assert verdict.reason == "invalid_quantity"


def test_bad_inputs_do_not_fail_open() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(
        account=Account("500"),
        positions=(Position("MSFT", "1", "100"),),
    )

    verdict = engine().check(order, portfolio, quote=None)

    assert verdict.allowed is False
    assert verdict.reason == "invalid_risk_input"
