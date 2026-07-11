"""Deterministic pre-trade risk engine."""

from __future__ import annotations

from decimal import Decimal

from algotrader.core.types import OrderSide, OrderType, ProposedOrder, Quote
from algotrader.core.validation import decimal_value
from algotrader.errors import ValidationError
from algotrader.portfolio.state import PortfolioState
from algotrader.risk.config import RiskConfig
from algotrader.risk.context import RiskContext
from algotrader.risk.state import RiskVerdict


class RiskEngine:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def check(
        self,
        order: ProposedOrder,
        portfolio: PortfolioState,
        quote: Quote,
        context: RiskContext | None = None,
    ) -> RiskVerdict:
        """Validate a proposed order and fail closed on bad inputs."""

        try:
            return self._check(order, portfolio, quote, context)
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
        context: RiskContext | None,
    ) -> RiskVerdict:
        if not isinstance(order, ProposedOrder):
            raise ValidationError("order must be a ProposedOrder.")
        if not isinstance(portfolio, PortfolioState):
            raise ValidationError("portfolio must be a PortfolioState.")
        if not isinstance(quote, Quote):
            raise ValidationError("quote must be a Quote.")
        if order.symbol != quote.symbol:
            return RiskVerdict.reject("symbol_mismatch")
        if not portfolio.risk.trading_enabled:
            return RiskVerdict.reject(
                "trading_disabled",
                detail=portfolio.risk.reason or "",
            )
        context_blocker = self._context_blocker(quote, context)
        if context_blocker is not None:
            return context_blocker

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
        if side == OrderSide.BUY and order_notional > self.config.max_order_notional:
            return RiskVerdict.reject(
                "max_order_notional_exceeded",
                order_notional=order_notional,
            )

        available_cash = portfolio.account.cash - self.config.cash_reserve
        if side == OrderSide.BUY and order_notional > available_cash:
            return RiskVerdict.reject(
                "insufficient_cash",
                order_notional=order_notional,
            )

        if context is not None:
            contextual = self._contextual_notional_checks(
                side=side,
                order_notional=order_notional,
                context=context,
            )
            if contextual is not None:
                return contextual

        if (
            side == OrderSide.BUY
            and self.config.max_positions is not None
            and (existing_position is None or existing_position.is_flat)
            and _open_position_count(portfolio) >= self.config.max_positions
        ):
            return RiskVerdict.reject("max_positions_exceeded")

        return RiskVerdict.allow(order_notional)

    def _context_blocker(
        self,
        quote: Quote,
        context: RiskContext | None,
    ) -> RiskVerdict | None:
        if context is None:
            return None
        if not isinstance(context, RiskContext):
            raise ValidationError("context must be a RiskContext.")
        if context.operator_paused:
            return RiskVerdict.reject("operator_paused")
        if not context.account_tradable:
            return RiskVerdict.reject("account_not_tradable")
        if context.account_trading_blocked:
            return RiskVerdict.reject("account_trading_blocked")
        if not context.data_current:
            return RiskVerdict.reject("market_data_stale")
        if not context.market_session_open:
            return RiskVerdict.reject("market_session_closed")
        if self.config.max_quote_age_seconds is not None:
            age_seconds = (context.as_of - quote.timestamp).total_seconds()
            if age_seconds < 0:
                return RiskVerdict.reject("quote_from_future")
            if age_seconds > self.config.max_quote_age_seconds:
                return RiskVerdict.reject("quote_stale")
        if self.config.max_spread_bps is not None:
            midpoint = (quote.bid + quote.ask) / Decimal("2")
            spread_bps = (quote.ask - quote.bid) / midpoint * Decimal("10000")
            if spread_bps > self.config.max_spread_bps:
                return RiskVerdict.reject("spread_too_wide")
        loss_blocker = self._loss_blocker(context)
        if loss_blocker is not None:
            return loss_blocker
        return None

    def _loss_blocker(self, context: RiskContext) -> RiskVerdict | None:
        if self.config.max_daily_loss is not None:
            if context.equity is None or context.start_of_day_equity is None:
                return RiskVerdict.reject("daily_loss_context_missing")
            if context.start_of_day_equity - context.equity > self.config.max_daily_loss:
                return RiskVerdict.reject("max_daily_loss_exceeded")
        if self.config.max_drawdown is not None:
            if context.equity is None or context.high_watermark_equity is None:
                return RiskVerdict.reject("drawdown_context_missing")
            if context.high_watermark_equity - context.equity > self.config.max_drawdown:
                return RiskVerdict.reject("max_drawdown_exceeded")
        return None

    def _contextual_notional_checks(
        self,
        *,
        side: OrderSide,
        order_notional: Decimal,
        context: RiskContext,
    ) -> RiskVerdict | None:
        if side == OrderSide.BUY and context.buying_power is not None:
            available = (
                context.buying_power
                - context.open_order_notional
                - self.config.buying_power_reserve
            )
            if order_notional > available:
                return RiskVerdict.reject(
                    "insufficient_buying_power",
                    order_notional=order_notional,
                )
        direction = Decimal("1") if side == OrderSide.BUY else Decimal("-1")
        projected_gross = max(
            Decimal("0"),
            context.gross_exposure + direction * order_notional,
        )
        projected_symbol = max(
            Decimal("0"),
            context.symbol_exposure + direction * order_notional,
        )
        if (
            self.config.max_gross_exposure is not None
            and projected_gross > self.config.max_gross_exposure
        ):
            return RiskVerdict.reject("max_gross_exposure_exceeded")
        if (
            self.config.max_symbol_exposure is not None
            and projected_symbol > self.config.max_symbol_exposure
        ):
            return RiskVerdict.reject("max_symbol_exposure_exceeded")
        return None


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
