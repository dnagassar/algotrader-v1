"""Deterministic pre-trade risk engine."""

from __future__ import annotations

from decimal import Decimal

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.core.validation import decimal_value
from algotrader.errors import ValidationError
from algotrader.portfolio.state import PortfolioState
from algotrader.risk.config import RiskConfig
from algotrader.risk.state import RiskVerdict


class RiskEngine:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def check(
        self,
        order: ProposedOrder,
        portfolio: PortfolioState,
        quote: Quote,
    ) -> RiskVerdict:
        """Validate a proposed order and fail closed on bad inputs."""

        try:
            return self._check(order, portfolio, quote)
        except Exception as exc:
            return RiskVerdict.reject(
                "invalid_risk_input",
                detail=str(exc),
            )

    def _check(
        self,
        order: ProposedOrder,
        portfolio: PortfolioState,
        quote: Quote,
    ) -> RiskVerdict:
        if not isinstance(order, ProposedOrder):
            raise ValidationError("order must be a ProposedOrder.")
        if not isinstance(portfolio, PortfolioState):
            raise ValidationError("portfolio must be a PortfolioState.")
        if not isinstance(quote, Quote):
            raise ValidationError("quote must be a Quote.")
        if order.symbol != quote.symbol:
            return RiskVerdict.reject("symbol_mismatch")

        side = _order_side(order)
        order_type = _order_type(order)
        quantity = _order_quantity(order)

        if quantity <= 0:
            return RiskVerdict.reject("invalid_quantity")
        if not self.config.allow_fractional_shares and _is_fractional(quantity):
            return RiskVerdict.reject("fractional_not_allowed")

        existing_position = portfolio.position(order.symbol)
        if side == OrderSide.SELL:
            held_quantity = (
                existing_position.quantity if existing_position else Decimal("0")
            )
            if quantity > held_quantity:
                reason = (
                    "short_selling_not_supported"
                    if self.config.allow_short
                    else "short_not_allowed"
                )
                return RiskVerdict.reject(reason)

        order_notional = _order_notional(order, quote, side, order_type, quantity)
        if order_notional > self.config.max_order_notional:
            return RiskVerdict.reject(
                "max_order_notional_exceeded",
                order_notional=order_notional,
            )

        if side == OrderSide.BUY and order_notional > portfolio.account.cash:
            return RiskVerdict.reject(
                "insufficient_cash",
                order_notional=order_notional,
            )

        if (
            side == OrderSide.BUY
            and self.config.max_positions is not None
            and (existing_position is None or existing_position.is_flat)
            and _open_position_count(portfolio) >= self.config.max_positions
        ):
            return RiskVerdict.reject("max_positions_exceeded")

        return RiskVerdict.allow(order_notional)


def _order_side(order: ProposedOrder) -> OrderSide:
    try:
        return OrderSide(order.side)
    except ValueError as exc:
        raise ValidationError("order side must be supported.") from exc


def _order_type(order: ProposedOrder) -> OrderType:
    try:
        return OrderType(order.order_type)
    except ValueError as exc:
        raise ValidationError("order type must be supported.") from exc


def _order_quantity(order: ProposedOrder) -> Decimal:
    return decimal_value(order.quantity, "quantity")


def _is_fractional(quantity: Decimal) -> bool:
    return quantity != quantity.to_integral_value()


def _open_position_count(portfolio: PortfolioState) -> int:
    return sum(1 for position in portfolio.positions if not position.is_flat)


def _order_notional(
    order: ProposedOrder,
    quote: Quote,
    side: OrderSide,
    order_type: OrderType,
    quantity: Decimal,
) -> Decimal:
    if order_type == OrderType.MARKET:
        price = quote.ask if side == OrderSide.BUY else quote.bid
    else:
        if order.limit_price is None:
            raise ValidationError("limit orders require limit_price.")
        price = decimal_value(order.limit_price, "limit_price")

    if price <= 0:
        raise ValidationError("order price must be greater than zero.")

    return quantity * price
