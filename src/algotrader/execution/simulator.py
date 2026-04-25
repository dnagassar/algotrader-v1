"""Pure paper execution simulator."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.core.types import (
    Fill,
    OrderAck,
    OrderSide,
    OrderStatus,
    OrderType,
    ProposedOrder,
    Quote,
)
from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    ack: OrderAck
    fill: Fill | None = None

    @property
    def filled(self) -> bool:
        return self.fill is not None


def simulate_order(order: ProposedOrder, quote: Quote, order_id: str) -> ExecutionResult:
    if order.symbol != quote.symbol:
        raise ValidationError("order and quote symbols must match.")

    fill_price = _fill_price(order, quote)
    if fill_price is None:
        return ExecutionResult(
            ack=OrderAck(
                order_id=order_id,
                order=order,
                status=OrderStatus.OPEN,
                timestamp=quote.timestamp,
                message="limit not marketable",
            ),
        )

    fill = Fill(
        order_id=order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=order.quantity,
        price=fill_price,
        timestamp=quote.timestamp,
    )
    return ExecutionResult(
        ack=OrderAck(
            order_id=order_id,
            order=order,
            status=OrderStatus.FILLED,
            timestamp=quote.timestamp,
        ),
        fill=fill,
    )


def _fill_price(order: ProposedOrder, quote: Quote):
    if order.order_type == OrderType.MARKET:
        return quote.ask if order.side == OrderSide.BUY else quote.bid

    if order.side == OrderSide.BUY and order.limit_price >= quote.ask:
        return quote.ask
    if order.side == OrderSide.SELL and order.limit_price <= quote.bid:
        return quote.bid

    return None
