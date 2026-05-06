"""Pure pre-execution selectors for risk evaluation rows."""

from __future__ import annotations

from collections.abc import Iterable

from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation

__all__ = ["select_risk_approved_evaluations"]


def select_risk_approved_evaluations(
    evaluations: Iterable[SignalRiskEvaluation],
) -> tuple[SignalRiskEvaluation, ...]:
    """Return risk-approved rows in input order without creating execution intent."""

    return tuple(
        evaluation
        for evaluation in evaluations
        if evaluation.status == "risk_approved"
    )
