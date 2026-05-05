"""Pure bridge from screener-ordered signal outputs to risk verdicts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from algotrader.core.types import Bar, ProposedOrder, Quote
from algotrader.orchestration.screener_signal_flow import ScreenerSignalEvaluation
from algotrader.portfolio.state import PortfolioState
from algotrader.risk.config import RiskConfig
from algotrader.risk.engine import RiskEngine
from algotrader.risk.state import RiskVerdict

SignalRiskStatus = Literal["no_signal", "risk_rejected", "risk_approved"]

__all__ = [
    "SignalRiskEvaluation",
    "SignalRiskStatus",
    "evaluate_risk_for_screener_signals",
]


@dataclass(frozen=True, slots=True)
class SignalRiskEvaluation:
    symbol: str
    previous_bar: Bar
    quote: Quote
    order: ProposedOrder | None
    risk: RiskVerdict | None
    status: SignalRiskStatus


def evaluate_risk_for_screener_signals(
    evaluations: Iterable[ScreenerSignalEvaluation],
    portfolio: PortfolioState,
    risk_config: RiskConfig | None = None,
) -> tuple[SignalRiskEvaluation, ...]:
    """Evaluate proposed signal outputs against risk without execution."""

    risk_engine = RiskEngine(risk_config)
    risk_evaluations: list[SignalRiskEvaluation] = []

    for evaluation in evaluations:
        if evaluation.order is None:
            risk = None
            status: SignalRiskStatus = "no_signal"
        else:
            risk = risk_engine.check(evaluation.order, portfolio, evaluation.quote)
            status = "risk_approved" if risk.allowed else "risk_rejected"

        risk_evaluations.append(
            SignalRiskEvaluation(
                symbol=evaluation.symbol,
                previous_bar=evaluation.previous_bar,
                quote=evaluation.quote,
                order=evaluation.order,
                risk=risk,
                status=status,
            )
        )

    return tuple(risk_evaluations)
