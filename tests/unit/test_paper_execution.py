from datetime import datetime, timezone
from decimal import Decimal

from algotrader.core.types import OrderSide, OrderStatus, OrderType, ProposedOrder, Quote
from algotrader.execution.simulator import simulate_order


NOW = datetime(2026, 4, 25, tzinfo=timezone.utc)


def quote() -> Quote:
    return Quote("MSFT", NOW, bid="100.00", ask="100.10")


def test_market_buy_fills_at_ask() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.MARKET, "5")
    result = simulate_order(order, quote(), "order-1")

    assert result.ack.status == OrderStatus.FILLED
    assert result.fill.price == Decimal("100.10")


def test_market_sell_fills_at_bid() -> None:
    order = ProposedOrder("MSFT", OrderSide.SELL, OrderType.MARKET, "5")
    result = simulate_order(order, quote(), "order-1")

    assert result.ack.status == OrderStatus.FILLED
    assert result.fill.price == Decimal("100.00")


def test_limit_buy_fills_when_limit_crosses_ask() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.LIMIT, "5", "100.10")
    result = simulate_order(order, quote(), "order-1")

    assert result.ack.status == OrderStatus.FILLED
    assert result.fill.price == Decimal("100.10")


def test_limit_sell_fills_when_limit_crosses_bid() -> None:
    order = ProposedOrder("MSFT", OrderSide.SELL, OrderType.LIMIT, "5", "100.00")
    result = simulate_order(order, quote(), "order-1")

    assert result.ack.status == OrderStatus.FILLED
    assert result.fill.price == Decimal("100.00")


def test_unfillable_limit_buy_stays_open_without_fill() -> None:
    order = ProposedOrder("MSFT", OrderSide.BUY, OrderType.LIMIT, "5", "100.09")
    result = simulate_order(order, quote(), "order-1")

    assert result.ack.status == OrderStatus.OPEN
    assert result.fill is None


def test_unfillable_limit_sell_stays_open_without_fill() -> None:
    order = ProposedOrder("MSFT", OrderSide.SELL, OrderType.LIMIT, "5", "100.01")
    result = simulate_order(order, quote(), "order-1")

    assert result.ack.status == OrderStatus.OPEN
    assert result.fill is None
