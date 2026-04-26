"""Named deterministic demo scenarios for the local trading core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.orchestration.signal_trade_flow import (
    SignalTradeFlowResult,
    generate_evaluate_and_execute,
)
from algotrader.portfolio.state import Account, PortfolioState

ScenarioName = str
SCENARIO_NAMES: tuple[ScenarioName, ...] = (
    "approved_and_filled",
    "rejected_insufficient_cash",
    "no_signal",
    "unfilled_limit_order",
)

_TIMESTAMP = datetime(2026, 4, 25, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    name: ScenarioName
    result: SignalTradeFlowResult


def run_scenario(name: ScenarioName) -> ScenarioResult:
    try:
        scenario = _SCENARIOS[name]
    except KeyError as exc:
        expected = ", ".join(SCENARIO_NAMES)
        raise ValidationError(
            f"Unknown scenario {name!r}. Expected one of: {expected}."
        ) from exc

    return ScenarioResult(name=name, result=scenario())


def _previous_bar() -> Bar:
    return Bar("MSFT", _TIMESTAMP, "99", "101", "98", "100", "1000")


def _quote(bid: str = "101.00", ask: str = "101.01") -> Quote:
    return Quote("MSFT", _TIMESTAMP, bid=bid, ask=ask)


def _portfolio(cash: str) -> PortfolioState:
    return PortfolioState(account=Account(cash))


def _approved_and_filled() -> SignalTradeFlowResult:
    return generate_evaluate_and_execute(
        previous_bar=_previous_bar(),
        quote=_quote(),
        portfolio=_portfolio("1000"),
    )


def _rejected_insufficient_cash() -> SignalTradeFlowResult:
    return generate_evaluate_and_execute(
        previous_bar=_previous_bar(),
        quote=_quote(),
        portfolio=_portfolio("50"),
    )


def _no_signal() -> SignalTradeFlowResult:
    return generate_evaluate_and_execute(
        previous_bar=_previous_bar(),
        quote=_quote(bid="100.90", ask="101.00"),
        portfolio=_portfolio("1000"),
    )


def _unfilled_limit_order() -> SignalTradeFlowResult:
    return generate_evaluate_and_execute(
        previous_bar=_previous_bar(),
        quote=_quote(),
        portfolio=_portfolio("1000"),
        signal_rule=_unfillable_limit_signal,
    )


def _unfillable_limit_signal(
    previous_bar: Bar,
    quote: Quote,
    threshold: Decimal | str,
    quantity: Decimal | str,
) -> ProposedOrder:
    return ProposedOrder(
        symbol=quote.symbol,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        limit_price=quote.ask - Decimal("0.01"),
    )


_SCENARIOS = {
    "approved_and_filled": _approved_and_filled,
    "rejected_insufficient_cash": _rejected_insufficient_cash,
    "no_signal": _no_signal,
    "unfilled_limit_order": _unfilled_limit_order,
}
