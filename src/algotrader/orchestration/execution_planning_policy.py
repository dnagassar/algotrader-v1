"""Pure pre-broker execution-planning policy result boundary."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.orchestration.execution_planning_flow import ExecutionPlan
from algotrader.orchestration.risk_execution_flow import ExecutionIntent

__all__ = [
    "PlanningPolicyResult",
    "SkippedExecutionIntent",
    "apply_noop_execution_planning_policy",
]


@dataclass(frozen=True, slots=True)
class SkippedExecutionIntent:
    """Traceable future policy skip shape for an execution intent."""

    intent: ExecutionIntent
    reason: str


@dataclass(frozen=True, slots=True)
class PlanningPolicyResult:
    """Immutable pre-broker result for execution-planning policy decisions."""

    accepted_intents: tuple[ExecutionIntent, ...]
    skipped_intents: tuple[SkippedExecutionIntent, ...]


def apply_noop_execution_planning_policy(
    plan: ExecutionPlan,
) -> PlanningPolicyResult:
    """Accept every intent in the plan without applying real policy decisions."""

    return PlanningPolicyResult(
        accepted_intents=plan.intents,
        skipped_intents=(),
    )
