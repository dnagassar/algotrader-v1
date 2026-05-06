"""Pure pre-broker execution planning batch container."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.orchestration.risk_execution_flow import ExecutionIntent

__all__ = [
    "ExecutionPlan",
    "build_execution_plan",
]


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Immutable batch container for internal execution intents."""

    intents: tuple[ExecutionIntent, ...]


def build_execution_plan(intents: Iterable[ExecutionIntent]) -> ExecutionPlan:
    """Build an immutable pre-broker plan from execution intents."""

    return ExecutionPlan(intents=tuple(intents))
