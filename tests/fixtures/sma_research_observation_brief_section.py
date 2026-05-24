"""Deterministic synthetic SMA research observation brief section fixtures."""

from __future__ import annotations

from algotrader.research.sma_research_observation_brief_section import (
    SmaResearchObservationBriefSection,
    build_sma_research_observation_brief_section,
)
from tests.fixtures.sma_research_observation_brief import (
    build_synthetic_insufficient_history_sma_research_observation_brief_item,
    build_synthetic_sma_research_observation_brief_item,
    expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict,
    expected_synthetic_sma_research_observation_brief_item_dict,
)

__all__ = [
    "build_synthetic_sma_research_observation_brief_section",
    "expected_synthetic_sma_research_observation_brief_section_dict",
]

_SECTION_ID = "sma-research-observation-section:synthetic:broad-etf-sma"
_TITLE = "Synthetic broad ETF SMA observation summary"
_SUMMARY = (
    "Section is advisory-only synthetic SMA observation content for broad ETF "
    "SMA mechanics."
)


def build_synthetic_sma_research_observation_brief_section() -> (
    SmaResearchObservationBriefSection
):
    """Return the deterministic synthetic SMA observation brief section."""

    primary_item = build_synthetic_sma_research_observation_brief_item()
    insufficient_item = (
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )
    return build_sma_research_observation_brief_section(
        section_id=_SECTION_ID,
        title=_TITLE,
        summary=_SUMMARY,
        items=(primary_item, insufficient_item),
    )


def expected_synthetic_sma_research_observation_brief_section_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic SMA observation section payload."""

    primary_item = expected_synthetic_sma_research_observation_brief_item_dict()
    insufficient_item = (
        expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict()
    )
    return {
        "section_type": "sma_research_observation_brief_section",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "section_id": _SECTION_ID,
        "title": _TITLE,
        "summary": _SUMMARY,
        "item_count": 2,
        "items": [primary_item, insufficient_item],
        "limitations": list(primary_item["limitations"]),
        "non_claims": list(primary_item["non_claims"]),
    }
