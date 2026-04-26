from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.signals.simple_rule import generate_momentum_buy_order


NOW = datetime(2026, 4, 25, tzinfo=timezone.utc)


def previous_bar() -> Bar:
    return Bar("MSFT", NOW, "99", "101", "98", "100", "1000")


def quote(ask: str, symbol: str = "MSFT") -> Quote:
    return Quote(symbol, NOW, bid="100", ask=ask)


def test_rule_produces_order_when_threshold_is_crossed() -> None:
    order = generate_momentum_buy_order(previous_bar(), quote("101.01"))

    assert isinstance(order, ProposedOrder)
    assert order.symbol == "MSFT"
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.MARKET
    assert order.quantity == Decimal("1")


def test_rule_returns_none_when_threshold_is_not_met() -> None:
    order = generate_momentum_buy_order(previous_bar(), quote("101.00"))

    assert order is None


def test_rule_handles_missing_inputs_clearly() -> None:
    with pytest.raises(ValidationError):
        generate_momentum_buy_order(None, quote("101.01"))


def test_rule_rejects_symbol_mismatch() -> None:
    with pytest.raises(ValidationError):
        generate_momentum_buy_order(previous_bar(), quote("101.01", symbol="AAPL"))


def test_rule_rejects_invalid_quantity() -> None:
    with pytest.raises(ValidationError):
        generate_momentum_buy_order(previous_bar(), quote("101.01"), quantity="0")
