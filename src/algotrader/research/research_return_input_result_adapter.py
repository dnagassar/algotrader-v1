"""Adapter from return-input packages to synthetic research results."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.replay_result import (
    SyntheticResearchResult,
    build_synthetic_research_result,
)
from algotrader.research.research_return_input_package import ResearchReturnInputPackage
from algotrader.research.research_return_input_replay_adapter import (
    build_synthetic_replay_snapshot_from_return_input_package,
)

__all__ = [
    "build_synthetic_research_result_from_return_input_package",
]


def build_synthetic_research_result_from_return_input_package(
    package: ResearchReturnInputPackage,
) -> SyntheticResearchResult:
    """Build a candidate-only synthetic result from a verified package.

    This remains synthetic and candidate only. It does not approve source,
    methodology, no-lookahead status, strategy validity, trading readiness, or
    downstream use.
    """

    checked_package = _package(package)
    snapshot = build_synthetic_replay_snapshot_from_return_input_package(
        checked_package
    )
    return build_synthetic_research_result(snapshot)


def _package(value: ResearchReturnInputPackage) -> ResearchReturnInputPackage:
    if not isinstance(value, ResearchReturnInputPackage):
        raise ValidationError("package must be a ResearchReturnInputPackage.")

    return value
