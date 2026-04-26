"""Pure orchestration for the deterministic paper-trading path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from algotrader.core.types import ProposedOrder, Quote
from algotrader.execution.simulator import ExecutionResult, simulate_order
from algotrader.portfolio.state import PortfolioState, apply_fill
from algotrader.portfolio.valuation import PortfolioValuation, value_portfolio
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine
from algotrader.risk.state import RiskVerdict

TradeFlowStatus = Literal["rejected", "filled", "open", "error"]


@dataclass(frozen=True, slots=True)
class TradeFlowResult:
    status: TradeFlowStatus
    risk: RiskVerdict
    portfolio: PortfolioState | None
    execution: ExecutionResult | None = None
    valuation: PortfolioValuation | None = None

    @property
    def allowed(self) -> bool:
        return self.risk.allowed

    @property
    def filled(self) -> bool:
        return self.execution is not None and self.execution.filled


def evaluate_and_execute(
    order: ProposedOrder,
    portfolio: PortfolioState,
    quote: Quote,
    risk_config: RiskConfig | None = None,
    order_id: str = "paper-order-1",
) -> TradeFlowResult:
    """Risk-check, simulate, apply fills, and value the resulting portfolio."""

    risk = RiskEngine(risk_config).check(order, portfolio, quote)
    if not risk.allowed:
        return TradeFlowResult(
            status="rejected",
            risk=risk,
            portfolio=portfolio if isinstance(portfolio, PortfolioState) else None,
        )

    try:
        execution = simulate_order(order, quote, order_id)
        updated_portfolio = portfolio
        status: TradeFlowStatus = "open"

        if execution.fill is not None:
            updated_portfolio = apply_fill(portfolio, execution.fill)
            status = "filled"

        valuation = value_portfolio(updated_portfolio, {quote.symbol: quote})
        return TradeFlowResult(
            status=status,
            risk=risk,
            portfolio=updated_portfolio,
            execution=execution,
            valuation=valuation,
        )
    except Exception as exc:
        return TradeFlowResult(
            status="error",
            risk=RiskVerdict.reject("trade_flow_error", detail=str(exc)),
            portfolio=portfolio if isinstance(portfolio, PortfolioState) else None,
        )
