from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algotrader.core.types import Fill, OrderSide
from algotrader.errors import ValidationError
from algotrader.portfolio.state import Account, PortfolioState, Position, apply_fill


NOW = datetime(2026, 4, 28, tzinfo=timezone.utc)


def test_buy_fill_that_overdraws_cash_fails_without_mutating_state() -> None:
    state = PortfolioState(account=Account("50"))
    fill = Fill("order-1", "MSFT", OrderSide.BUY, "1", "100", NOW)

    with pytest.raises(ValidationError, match="cash negative"):
        apply_fill(state, fill)

    assert state.account.cash == Decimal("50")
    assert state.positions == ()


def test_sell_fill_that_exceeds_position_fails_without_mutating_state() -> None:
    state = PortfolioState(
        account=Account("50"),
        positions=(Position("MSFT", "1", "100"),),
    )
    fill = Fill("order-1", "MSFT", OrderSide.SELL, "2", "100", NOW)

    with pytest.raises(ValidationError, match="exceeds current position"):
        apply_fill(state, fill)

    assert state.account.cash == Decimal("50")
    assert state.positions == (Position("MSFT", "1", "100"),)
