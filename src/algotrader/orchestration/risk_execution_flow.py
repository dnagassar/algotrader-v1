"""Pure pre-execution selectors for risk evaluation rows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation

__all__ = [
    "ExecutionIntent",
    "build_execution_intents_from_risk_approved",
    "select_risk_approved_evaluations",
]


@dataclass(frozen=True, slots=True)
class ExecutionIntent:
    """Internal pre-submission execution candidate."""

    source_evaluation: SignalRiskEvaluation


def select_risk_approved_evaluations(
    evaluations: Iterable[SignalRiskEvaluation],
) -> tuple[SignalRiskEvaluation, ...]:
    """Return risk-approved rows in input order without creating execution intent."""

    return tuple(
        evaluation
        for evaluation in evaluations
        if evaluation.status == "risk_approved"
    )


def build_execution_intents_from_risk_approved(
    evaluations: Iterable[SignalRiskEvaluation],
) -> tuple[ExecutionIntent, ...]:
    """Build immutable internal intents from risk-approved rows only."""

    return tuple(
        ExecutionIntent(source_evaluation=evaluation)
        for evaluation in select_risk_approved_evaluations(evaluations)
    )
