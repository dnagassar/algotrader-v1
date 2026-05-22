"""Synthetic candidate research brief item fixture."""

from __future__ import annotations

from algotrader.research.candidate_research_brief_item import (
    CandidateResearchBriefItem,
    build_candidate_research_brief_item,
)
from tests.fixtures.candidate_result_dossier import (
    build_synthetic_candidate_research_result_dossier,
)

__all__ = [
    "build_synthetic_candidate_research_brief_item",
    "expected_synthetic_candidate_research_brief_item_dict",
]


def build_synthetic_candidate_research_brief_item() -> (
    CandidateResearchBriefItem
):
    """Return the deterministic synthetic candidate research brief item."""

    dossier = build_synthetic_candidate_research_result_dossier()
    return build_candidate_research_brief_item(dossier)


def expected_synthetic_candidate_research_brief_item_dict() -> (
    dict[str, object]
):
    """Return the stable primitive brief item payload emitted by the contract."""

    return build_synthetic_candidate_research_brief_item().to_dict()
