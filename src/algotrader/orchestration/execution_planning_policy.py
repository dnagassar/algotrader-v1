"""Pure pre-broker execution-planning policy result boundary."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.orchestration.execution_planning_flow import ExecutionPlan
from algotrader.orchestration.risk_execution_flow import ExecutionIntent

MAX_INTENTS_PER_PLAN_EXCEEDED_REASON = "max_intents_per_plan_exceeded"

__all__ = [
    "MAX_INTENTS_PER_PLAN_EXCEEDED_REASON",
    "MaxAcceptedIntentsPolicyConfig",
    "PlanningPolicyResult",
    "SkippedExecutionIntent",
    "apply_max_intents_execution_planning_policy",
    "apply_noop_execution_planning_policy",
]


@dataclass(frozen=True, slots=True)
class MaxAcceptedIntentsPolicyConfig:
    """Explicit deterministic cap for accepted intents in one plan."""

    max_accepted_intents: int

    def __post_init__(self) -> None:
        if type(self.max_accepted_intents) is not int:
            raise ValidationError(
                "max_accepted_intents must be an integer greater than or equal to 1."
            )
        if self.max_accepted_intents < 1:
            raise ValidationError(
                "max_accepted_intents must be an integer greater than or equal to 1."
            )


@dataclass(frozen=True, slots=True)
class SkippedExecutionIntent:
    """Traceable policy skip shape for an execution intent."""

    intent: ExecutionIntent
    reason: str


@dataclass(frozen=True, slots=True)
class PlanningPolicyResult:
    """Immutable pre-broker result for execution-planning policy decisions."""

    accepted_intents: tuple[ExecutionIntent, ...]
    skipped_intents: tuple[SkippedExecutionIntent, ...]


def apply_max_intents_execution_planning_policy(
    plan: ExecutionPlan,
    config: MaxAcceptedIntentsPolicyConfig,
) -> PlanningPolicyResult:
    """Accept the first configured number of intents and skip the rest."""

    accepted_intents = plan.intents[: config.max_accepted_intents]
    skipped_intents = tuple(
        SkippedExecutionIntent(
            intent=skipped_intent,
            reason=MAX_INTENTS_PER_PLAN_EXCEEDED_REASON,
        )
        for skipped_intent in plan.intents[config.max_accepted_intents :]
    )
    return PlanningPolicyResult(
        accepted_intents=accepted_intents,
        skipped_intents=skipped_intents,
    )


def apply_noop_execution_planning_policy(
    plan: ExecutionPlan,
) -> PlanningPolicyResult:
    """Accept every intent in the plan without applying real policy decisions."""

    return PlanningPolicyResult(
        accepted_intents=plan.intents,
        skipped_intents=(),
    )
