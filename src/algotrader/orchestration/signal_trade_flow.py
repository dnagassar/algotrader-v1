"""Connect deterministic signal generation to trade-flow orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from algotrader.core.types import Bar, ProposedOrder, Quote
from algotrader.execution.simulator import ExecutionResult
from algotrader.portfolio.state import PortfolioState
from algotrader.portfolio.valuation import PortfolioValuation
from algotrader.risk.config import RiskConfig
from algotrader.signals.simple_rule import generate_momentum_buy_order

from .trade_flow import TradeFlowResult, evaluate_and_execute

SignalTradeFlowStatus = Literal["no_signal", "rejected", "open", "filled", "error"]
SignalRule = Callable[
    [Bar, Quote, Decimal | str, Decimal | str],
    ProposedOrder | None,
]


@dataclass(frozen=True, slots=True)
class SignalTradeFlowResult:
    status: SignalTradeFlowStatus
    order: ProposedOrder | None
    portfolio: PortfolioState | None
    trade_flow: TradeFlowResult | None = None
    message: str = ""

    @property
    def execution(self) -> ExecutionResult | None:
        return self.trade_flow.execution if self.trade_flow else None

    @property
    def valuation(self) -> PortfolioValuation | None:
        return self.trade_flow.valuation if self.trade_flow else None


def generate_evaluate_and_execute(
    previous_bar: Bar,
    quote: Quote,
    portfolio: PortfolioState,
    risk_config: RiskConfig | None = None,
    threshold: Decimal | str = Decimal("0.01"),
    quantity: Decimal | str = Decimal("1"),
    order_id: str = "paper-order-1",
    signal_rule: SignalRule = generate_momentum_buy_order,
) -> SignalTradeFlowResult:
    """Generate a signal order and run it through the deterministic trade flow."""

    try:
        order = signal_rule(previous_bar, quote, threshold, quantity)
        if order is None:
            return SignalTradeFlowResult(
                status="no_signal",
                order=None,
                portfolio=portfolio if isinstance(portfolio, PortfolioState) else None,
            )

        trade_flow = evaluate_and_execute(
            order=order,
            portfolio=portfolio,
            quote=quote,
            risk_config=risk_config,
            order_id=order_id,
        )
        return SignalTradeFlowResult(
            status=trade_flow.status,
            order=order,
            portfolio=trade_flow.portfolio,
            trade_flow=trade_flow,
        )
    except Exception as exc:
        return SignalTradeFlowResult(
            status="error",
            order=None,
            portfolio=portfolio if isinstance(portfolio, PortfolioState) else None,
            message=str(exc),
        )
