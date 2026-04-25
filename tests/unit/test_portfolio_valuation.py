from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Quote
from algotrader.errors import MissingQuoteError
from algotrader.portfolio.state import Account, PortfolioState, Position
from algotrader.portfolio.valuation import value_portfolio


NOW = datetime(2026, 4, 25, tzinfo=timezone.utc)


def make_quote(symbol: str, bid: str, ask: str | None = None) -> Quote:
    return Quote(symbol, NOW, bid=bid, ask=ask or bid)


def test_single_long_position_valuation() -> None:
    state = PortfolioState(
        account=Account("1000"),
        positions=(Position("MSFT", "2", "100"),),
    )

    valuation = value_portfolio(state, {"MSFT": make_quote("MSFT", "110")})

    assert valuation.cash == Decimal("1000")
    assert valuation.total_position_market_value == Decimal("220")
    assert valuation.total_market_value == Decimal("1220")
    assert valuation.total_unrealized_pnl == Decimal("20")
    assert valuation.positions[0].market_value == Decimal("220")


def test_multiple_positions_plus_cash() -> None:
    state = PortfolioState(
        account=Account("500"),
        positions=(
            Position("MSFT", "2", "100"),
            Position("AAPL", "1", "50"),
        ),
    )
    quotes = {
        "MSFT": make_quote("MSFT", "110"),
        "AAPL": make_quote("AAPL", "45"),
    }

    valuation = value_portfolio(state, quotes)

    assert valuation.total_position_market_value == Decimal("265")
    assert valuation.total_market_value == Decimal("765")
    assert valuation.total_unrealized_pnl == Decimal("15")


def test_unchanged_price_produces_zero_unrealized_pnl() -> None:
    state = PortfolioState(
        account=Account("0"),
        positions=(Position("MSFT", "2", "100"),),
    )

    valuation = value_portfolio(state, {"MSFT": make_quote("MSFT", "100")})

    assert valuation.total_unrealized_pnl == Decimal("0")


def test_higher_quote_produces_positive_unrealized_pnl() -> None:
    state = PortfolioState(
        account=Account("0"),
        positions=(Position("MSFT", "2", "100"),),
    )

    valuation = value_portfolio(state, {"MSFT": make_quote("MSFT", "105")})

    assert valuation.total_unrealized_pnl == Decimal("10")


def test_lower_quote_produces_negative_unrealized_pnl() -> None:
    state = PortfolioState(
        account=Account("0"),
        positions=(Position("MSFT", "2", "100"),),
    )

    valuation = value_portfolio(state, {"MSFT": make_quote("MSFT", "95")})

    assert valuation.total_unrealized_pnl == Decimal("-10")


def test_missing_quote_is_explicit_error() -> None:
    state = PortfolioState(
        account=Account("0"),
        positions=(Position("MSFT", "2", "100"),),
    )

    with pytest.raises(MissingQuoteError):
        value_portfolio(state, {})
