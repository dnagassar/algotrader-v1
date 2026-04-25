from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Bar, Fill, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.portfolio.state import (
    Account,
    PortfolioState,
    Position,
    RiskState,
    apply_fill,
)


NOW = datetime(2026, 4, 25, tzinfo=timezone.utc)


def test_market_data_models_validate_and_normalize_symbols() -> None:
    bar = Bar("msft", NOW, "100", "105", "99", "101", "1000")
    quote = Quote("msft", NOW, bid="100.00", ask="100.05")

    assert bar.symbol == "MSFT"
    assert bar.close == Decimal("101")
    assert quote.symbol == "MSFT"
    assert quote.bid == Decimal("100.00")


def test_quote_rejects_crossed_market() -> None:
    with pytest.raises(ValidationError):
        Quote("MSFT", NOW, bid="101", ask="100")


def test_order_requires_limit_price_for_limit_orders() -> None:
    with pytest.raises(ValidationError):
        ProposedOrder("MSFT", OrderSide.BUY, OrderType.LIMIT, "10")


def test_portfolio_models_create_small_state() -> None:
    state = PortfolioState(
        account=Account("100000"),
        positions=(Position("msft", "2", "100"),),
        risk=RiskState(trading_enabled=True),
        timestamp=NOW,
    )

    assert state.account.cash == Decimal("100000")
    assert state.position("MSFT").quantity == Decimal("2")


def test_apply_fill_returns_updated_portfolio_state() -> None:
    state = PortfolioState(account=Account("1000"))
    fill = Fill("order-1", "MSFT", OrderSide.BUY, "2", "100", NOW)

    updated = apply_fill(state, fill)

    assert state.position("MSFT") is None
    assert updated.account.cash == Decimal("800")
    assert updated.position("MSFT").quantity == Decimal("2")
    assert updated.position("MSFT").average_price == Decimal("100")
