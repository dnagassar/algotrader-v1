"""One tiny deterministic quote-vs-close signal rule."""

from __future__ import annotations

from decimal import Decimal

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.core.validation import decimal_value
from algotrader.errors import ValidationError


def generate_momentum_buy_order(
    previous_bar: Bar,
    quote: Quote,
    threshold: Decimal | str = Decimal("0.01"),
    quantity: Decimal | str = Decimal("1"),
) -> ProposedOrder | None:
    """Buy when the current ask is above the previous close by threshold."""

    if not isinstance(previous_bar, Bar):
        raise ValidationError("previous_bar must be a Bar.")
    if not isinstance(quote, Quote):
        raise ValidationError("quote must be a Quote.")
    if previous_bar.symbol != quote.symbol:
        raise ValidationError("previous_bar and quote symbols must match.")

    threshold_value = decimal_value(threshold, "threshold")
    quantity_value = decimal_value(quantity, "quantity")

    if threshold_value < 0:
        raise ValidationError("threshold must be zero or greater.")
    if quantity_value <= 0:
        raise ValidationError("quantity must be greater than zero.")

    trigger_price = previous_bar.close * (Decimal("1") + threshold_value)
    if quote.ask <= trigger_price:
        return None

    return ProposedOrder(
        symbol=quote.symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=quantity_value,
    )
