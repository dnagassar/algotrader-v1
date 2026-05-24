"""Deterministic synthetic SMA research observation brief container fixtures."""

from __future__ import annotations

from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
    build_sma_research_observation_brief,
)
from tests.fixtures.sma_research_observation_brief_section import (
    build_synthetic_sma_research_observation_brief_section,
    expected_synthetic_sma_research_observation_brief_section_dict,
)

__all__ = [
    "build_synthetic_sma_research_observation_brief",
    "expected_synthetic_sma_research_observation_brief_dict",
]

_BRIEF_ID = "sma-research-observation-brief:synthetic:broad-etf-sma"
_TITLE = "Synthetic broad ETF SMA research observation brief"
_SUMMARY = (
    "Brief is advisory-only synthetic SMA observation content for broad ETF "
    "SMA mechanics."
)


def build_synthetic_sma_research_observation_brief() -> SmaResearchObservationBrief:
    """Return the deterministic synthetic SMA observation brief container."""

    section = build_synthetic_sma_research_observation_brief_section()
    return build_sma_research_observation_brief(
        brief_id=_BRIEF_ID,
        title=_TITLE,
        summary=_SUMMARY,
        sections=(section,),
    )


def expected_synthetic_sma_research_observation_brief_dict() -> dict[str, object]:
    """Return the exact primitive synthetic SMA observation brief payload."""

    section = expected_synthetic_sma_research_observation_brief_section_dict()
    return {
        "brief_type": "sma_research_observation_brief",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "brief_id": _BRIEF_ID,
        "title": _TITLE,
        "summary": _SUMMARY,
        "section_count": 1,
        "sections": [section],
        "limitations": list(section["limitations"]),
        "non_claims": list(section["non_claims"]),
    }
