"""Synthetic candidate research brief section fixture."""

from __future__ import annotations

from algotrader.research.candidate_research_brief_section import (
    CandidateResearchBriefSection,
    build_candidate_research_brief_section,
)
from tests.fixtures.candidate_research_brief_item import (
    build_synthetic_candidate_research_brief_item,
)

__all__ = [
    "build_synthetic_candidate_research_brief_section",
    "expected_synthetic_candidate_research_brief_section_dict",
]


def build_synthetic_candidate_research_brief_section() -> (
    CandidateResearchBriefSection
):
    """Return the deterministic synthetic candidate research brief section."""

    item = build_synthetic_candidate_research_brief_item()
    return build_candidate_research_brief_section((item,))


def expected_synthetic_candidate_research_brief_section_dict() -> (
    dict[str, object]
):
    """Return the stable primitive section payload emitted by the contract."""

    return build_synthetic_candidate_research_brief_section().to_dict()
