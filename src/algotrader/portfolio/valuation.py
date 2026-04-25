"""Pure portfolio valuation using current quotes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from algotrader.core.types import Quote
from algotrader.errors import MissingQuoteError, ValidationError
from algotrader.portfolio.state import PortfolioState, Position


@dataclass(frozen=True, slots=True)
class PositionValuation:
    symbol: str
    quantity: Decimal
    average_price: Decimal
    mark_price: Decimal
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal
    quote_timestamp: datetime


@dataclass(frozen=True, slots=True)
class PortfolioValuation:
    cash: Decimal
    positions: tuple[PositionValuation, ...]
    total_position_market_value: Decimal
    total_market_value: Decimal
    total_unrealized_pnl: Decimal


def value_position(position: Position, quote: Quote) -> PositionValuation:
    """Value a long position at the current bid."""

    if position.symbol != quote.symbol:
        raise ValidationError("position and quote symbols must match.")
    if position.quantity < 0:
        raise ValidationError("valuation only supports long positions.")

    mark_price = quote.bid
    market_value = position.quantity * mark_price
    cost_basis = position.quantity * position.average_price

    return PositionValuation(
        symbol=position.symbol,
        quantity=position.quantity,
        average_price=position.average_price,
        mark_price=mark_price,
        market_value=market_value,
        cost_basis=cost_basis,
        unrealized_pnl=market_value - cost_basis,
        quote_timestamp=quote.timestamp,
    )


def value_portfolio(
    state: PortfolioState,
    quotes: Mapping[str, Quote],
) -> PortfolioValuation:
    quote_by_symbol = {quote.symbol: quote for quote in quotes.values()}
    position_values = tuple(
        value_position(position, _required_quote(position.symbol, quote_by_symbol))
        for position in state.positions
        if not position.is_flat
    )
    total_position_market_value = sum(
        (value.market_value for value in position_values),
        Decimal("0"),
    )
    total_unrealized_pnl = sum(
        (value.unrealized_pnl for value in position_values),
        Decimal("0"),
    )

    return PortfolioValuation(
        cash=state.account.cash,
        positions=position_values,
        total_position_market_value=total_position_market_value,
        total_market_value=state.account.cash + total_position_market_value,
        total_unrealized_pnl=total_unrealized_pnl,
    )


def _required_quote(symbol: str, quotes: Mapping[str, Quote]) -> Quote:
    try:
        return quotes[symbol]
    except KeyError as exc:
        raise MissingQuoteError(f"Missing quote for {symbol}.") from exc
