"""Deterministic synthetic research return observation brief container fixtures."""

from __future__ import annotations

from algotrader.research.research_return_observation_brief_container import (
    ResearchReturnObservationBrief,
    build_research_return_observation_brief,
)
from tests.fixtures.research_return_observation_brief_section import (
    build_synthetic_research_return_observation_brief_section,
    expected_synthetic_research_return_observation_brief_section_dict,
)

__all__ = [
    "build_synthetic_research_return_observation_brief",
    "expected_synthetic_research_return_observation_brief_dict",
]

_BRIEF_ID = (
    "research-return-observation-brief:synthetic:broad-etf-return-construction"
)
_TITLE = "Synthetic broad ETF return observation brief"
_SUMMARY = (
    "Brief is advisory-only synthetic close-to-close return observation content."
)


def build_synthetic_research_return_observation_brief() -> (
    ResearchReturnObservationBrief
):
    """Return the deterministic synthetic return observation brief container."""

    section = build_synthetic_research_return_observation_brief_section()
    return build_research_return_observation_brief(
        brief_id=_BRIEF_ID,
        title=_TITLE,
        summary=_SUMMARY,
        sections=(section,),
    )


def expected_synthetic_research_return_observation_brief_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic return observation brief payload."""

    section = expected_synthetic_research_return_observation_brief_section_dict()
    return {
        "brief_type": "research_return_observation_brief",
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
