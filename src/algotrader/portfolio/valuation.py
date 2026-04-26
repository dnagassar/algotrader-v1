"""Pure portfolio valuation using current quotes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from algotrader.core.types import Quote
from algotrader.core.validation import symbol_value
from algotrader.errors import MissingQuoteError, ValidationError
from algotrader.portfolio.state import PortfolioState, Position

QuoteInput = Mapping[str, Quote] | Quote


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
    quotes: QuoteInput,
) -> PortfolioValuation:
    quote_by_symbol = normalize_quote_map(quotes)
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


def normalize_quote_map(quotes: QuoteInput) -> dict[str, Quote]:
    """Return quotes keyed by normalized symbol, rejecting ambiguous input."""

    if isinstance(quotes, Quote):
        return {quotes.symbol: quotes}

    if not isinstance(quotes, Mapping):
        raise ValidationError("quotes must be a Quote or mapping of symbol to Quote.")

    quote_by_symbol: dict[str, Quote] = {}
    for key, quote in quotes.items():
        if not isinstance(key, str):
            raise ValidationError("quote map keys must be symbol strings.")
        if not isinstance(quote, Quote):
            raise ValidationError("quote map values must be Quote instances.")

        symbol = symbol_value(key)
        if symbol != quote.symbol:
            raise ValidationError("quote map key must match quote symbol.")
        if symbol in quote_by_symbol:
            raise ValidationError(f"duplicate quote for {symbol}.")

        quote_by_symbol[symbol] = quote

    return quote_by_symbol


def _required_quote(symbol: str, quotes: Mapping[str, Quote]) -> Quote:
    try:
        return quotes[symbol]
    except KeyError as exc:
        raise MissingQuoteError(f"Missing quote for {symbol}.") from exc
