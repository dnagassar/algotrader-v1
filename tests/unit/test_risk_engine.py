from datetime import datetime, timedelta, timezone
from decimal import Decimal

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.portfolio.state import Account, PortfolioState, Position, RiskState
from algotrader.risk.config import RiskConfig
from algotrader.risk.context import RiskContext
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


def test_portfolio_kill_switch_rejects_before_order_checks() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(
        account=Account("500"),
        risk=RiskState(trading_enabled=False, reason="operator_pause"),
    )

    verdict = engine().check(order, portfolio, quote())

    assert verdict.allowed is False
    assert verdict.reason == "trading_disabled"
    assert verdict.detail == "operator_pause"


def test_runtime_operator_pause_and_account_flags_fail_closed() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))

    paused = engine().check(
        order,
        portfolio,
        quote(),
        RiskContext(as_of=NOW, operator_paused=True),
    )
    blocked = engine().check(
        order,
        portfolio,
        quote(),
        RiskContext(as_of=NOW, account_trading_blocked=True),
    )

    assert paused.reason == "operator_paused"
    assert blocked.reason == "account_trading_blocked"


def test_buying_power_reserves_open_orders_and_operator_buffer() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))
    risk_config = RiskConfig(
        max_order_notional="1000",
        buying_power_reserve="25",
    )
    context = RiskContext(
        as_of=NOW,
        buying_power="150",
        open_order_notional="30",
    )

    verdict = RiskEngine(risk_config).check(order, portfolio, quote(), context)

    assert verdict.allowed is False
    assert verdict.reason == "insufficient_buying_power"


def test_projected_exposure_caps_are_enforced() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))
    risk_config = RiskConfig(
        max_order_notional="1000",
        max_gross_exposure="150",
        max_symbol_exposure="120",
    )
    context = RiskContext(
        as_of=NOW,
        gross_exposure="100",
        symbol_exposure="50",
    )

    verdict = RiskEngine(risk_config).check(order, portfolio, quote(), context)

    assert verdict.allowed is False
    assert verdict.reason == "max_gross_exposure_exceeded"


def test_daily_loss_and_drawdown_limits_require_observed_equity() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))
    risk_config = RiskConfig(max_daily_loss="50", max_drawdown="75")

    missing = RiskEngine(risk_config).check(
        order,
        portfolio,
        quote(),
        RiskContext(as_of=NOW),
    )
    exceeded = RiskEngine(risk_config).check(
        order,
        portfolio,
        quote(),
        RiskContext(
            as_of=NOW,
            equity="900",
            start_of_day_equity="960",
            high_watermark_equity="980",
        ),
    )

    assert missing.reason == "daily_loss_context_missing"
    assert exceeded.reason == "max_daily_loss_exceeded"


def test_stale_quote_and_wide_spread_are_rejected() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "1")
    portfolio = PortfolioState(account=Account("500"))
    stale_config = RiskConfig(max_quote_age_seconds=30)
    spread_config = RiskConfig(max_spread_bps="50")

    stale = RiskEngine(stale_config).check(
        order,
        portfolio,
        quote(),
        RiskContext(as_of=NOW + timedelta(seconds=31)),
    )
    wide = RiskEngine(spread_config).check(
        order,
        portfolio,
        Quote("MSFT", NOW, bid="100", ask="101"),
        RiskContext(as_of=NOW),
    )

    assert stale.reason == "quote_stale"
    assert wide.reason == "spread_too_wide"
