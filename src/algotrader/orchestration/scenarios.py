"""Named deterministic demo scenarios for the local trading core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.errors import ValidationError
from algotrader.execution.broker_base import BrokerOrderResult
from algotrader.execution.fake_broker import LocalBroker
from algotrader.orchestration.signal_trade_flow import (
    SignalTradeFlowResult,
    generate_evaluate_and_execute,
)
from algotrader.portfolio.state import Account, PortfolioState
from algotrader.portfolio.valuation import PortfolioValuation, value_portfolio
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine
from algotrader.risk.state import RiskVerdict
from algotrader.signals.simple_rule import generate_momentum_buy_order

ScenarioName = str
SCENARIO_NAMES: tuple[ScenarioName, ...] = (
    "approved_and_filled",
    "rejected_insufficient_cash",
    "no_signal",
    "unfilled_limit_order",
)
BROKER_SCENARIO_NAMES: tuple[ScenarioName, ...] = (
    "broker_approved_and_filled",
    "broker_rejected_insufficient_cash",
    "broker_unfilled_limit_order",
)
BrokerScenarioStatus = Literal["no_signal", "rejected", "open", "filled", "error"]

_TIMESTAMP = datetime(2026, 4, 25, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    name: ScenarioName
    result: SignalTradeFlowResult


@dataclass(frozen=True, slots=True)
class BrokerScenarioResult:
    name: ScenarioName
    status: BrokerScenarioStatus
    order: ProposedOrder | None
    risk: RiskVerdict | None
    broker_result: BrokerOrderResult | None
    portfolio: PortfolioState
    valuation: PortfolioValuation | None = None
    submitted: bool = False
    message: str = ""


def run_scenario(name: ScenarioName) -> ScenarioResult:
    try:
        scenario = _SCENARIOS[name]
    except KeyError as exc:
        expected = ", ".join(SCENARIO_NAMES)
        raise ValidationError(
            f"Unknown scenario {name!r}. Expected one of: {expected}."
        ) from exc

    return ScenarioResult(name=name, result=scenario())


def run_broker_scenario(name: ScenarioName) -> BrokerScenarioResult:
    try:
        scenario = _BROKER_SCENARIOS[name]
    except KeyError as exc:
        expected = ", ".join(BROKER_SCENARIO_NAMES)
        raise ValidationError(
            f"Unknown broker scenario {name!r}. Expected one of: {expected}."
        ) from exc

    return scenario()


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


def _broker_approved_and_filled() -> BrokerScenarioResult:
    return _run_broker_flow(
        name="broker_approved_and_filled",
        previous_bar=_previous_bar(),
        quote=_quote(),
        portfolio=_portfolio("1000"),
    )


def _broker_rejected_insufficient_cash() -> BrokerScenarioResult:
    return _run_broker_flow(
        name="broker_rejected_insufficient_cash",
        previous_bar=_previous_bar(),
        quote=_quote(),
        portfolio=_portfolio("50"),
    )


def _broker_unfilled_limit_order() -> BrokerScenarioResult:
    return _run_broker_flow(
        name="broker_unfilled_limit_order",
        previous_bar=_previous_bar(),
        quote=_quote(),
        portfolio=_portfolio("1000"),
        signal_rule=_unfillable_limit_signal,
    )


def _run_broker_flow(
    name: ScenarioName,
    previous_bar: Bar,
    quote: Quote,
    portfolio: PortfolioState,
    signal_rule=generate_momentum_buy_order,
) -> BrokerScenarioResult:
    try:
        order = signal_rule(previous_bar, quote, Decimal("0.01"), Decimal("1"))
        if order is None:
            return BrokerScenarioResult(
                name=name,
                status="no_signal",
                order=None,
                risk=None,
                broker_result=None,
                portfolio=portfolio,
            )

        risk = RiskEngine(RiskConfig()).check(order, portfolio, quote)
        if not risk.allowed:
            return BrokerScenarioResult(
                name=name,
                status="rejected",
                order=order,
                risk=risk,
                broker_result=None,
                portfolio=portfolio,
                submitted=False,
            )

        broker = LocalBroker(portfolio)
        broker_result = broker.submit_order(order, quote, risk)
        updated_portfolio = broker_result.portfolio or portfolio
        status: BrokerScenarioStatus = (
            "filled"
            if broker_result.filled
            else "open"
            if broker_result.accepted
            else "rejected"
        )
        valuation = value_portfolio(updated_portfolio, quote)

        return BrokerScenarioResult(
            name=name,
            status=status,
            order=order,
            risk=risk,
            broker_result=broker_result,
            portfolio=updated_portfolio,
            valuation=valuation,
            submitted=True,
        )
    except Exception as exc:
        return BrokerScenarioResult(
            name=name,
            status="error",
            order=None,
            risk=None,
            broker_result=None,
            portfolio=portfolio,
            message=str(exc),
        )


_SCENARIOS = {
    "approved_and_filled": _approved_and_filled,
    "rejected_insufficient_cash": _rejected_insufficient_cash,
    "no_signal": _no_signal,
    "unfilled_limit_order": _unfilled_limit_order,
}

_BROKER_SCENARIOS = {
    "broker_approved_and_filled": _broker_approved_and_filled,
    "broker_rejected_insufficient_cash": _broker_rejected_insufficient_cash,
    "broker_unfilled_limit_order": _broker_unfilled_limit_order,
}
