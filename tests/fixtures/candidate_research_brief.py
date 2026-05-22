"""Synthetic candidate research brief fixture."""

from __future__ import annotations

from algotrader.research.candidate_research_brief import (
    CandidateResearchBrief,
    build_candidate_research_brief,
)
from tests.fixtures.candidate_research_brief_section import (
    build_synthetic_candidate_research_brief_section,
)

__all__ = [
    "build_synthetic_candidate_research_brief",
    "expected_synthetic_candidate_research_brief_dict",
]


def build_synthetic_candidate_research_brief() -> CandidateResearchBrief:
    """Return the deterministic synthetic candidate research brief."""

    section = build_synthetic_candidate_research_brief_section()
    return build_candidate_research_brief((section,))


def expected_synthetic_candidate_research_brief_dict() -> dict[str, object]:
    """Return the stable primitive brief payload emitted by the contract."""

    return build_synthetic_candidate_research_brief().to_dict()
