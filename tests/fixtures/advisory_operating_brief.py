"""Synthetic advisory operating brief fixture."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief import (
    AdvisoryOperatingBrief,
    build_advisory_operating_brief,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
)

__all__ = [
    "build_synthetic_advisory_operating_brief",
    "expected_synthetic_advisory_operating_brief_dict",
]


def build_synthetic_advisory_operating_brief() -> AdvisoryOperatingBrief:
    """Return the deterministic synthetic advisory operating brief."""

    candidate_research_brief = build_synthetic_candidate_research_brief()
    return build_advisory_operating_brief((candidate_research_brief,))


def expected_synthetic_advisory_operating_brief_dict() -> dict[str, object]:
    """Return the stable primitive operating brief payload."""

    return build_synthetic_advisory_operating_brief().to_dict()
