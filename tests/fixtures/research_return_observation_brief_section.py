"""Deterministic synthetic research return observation brief section fixtures."""

from __future__ import annotations

from algotrader.research.research_return_observation_brief_section import (
    ResearchReturnObservationBriefSection,
    build_research_return_observation_brief_section,
)
from tests.fixtures.research_return_observation_brief import (
    build_synthetic_insufficient_research_return_observation_brief_item,
    build_synthetic_research_return_observation_brief_item,
    expected_synthetic_insufficient_research_return_observation_brief_item_dict,
    expected_synthetic_research_return_observation_brief_item_dict,
)

__all__ = [
    "build_synthetic_research_return_observation_brief_section",
    "expected_synthetic_research_return_observation_brief_section_dict",
]

_SECTION_ID = (
    "research-return-observation-section:synthetic:broad-etf-return-construction"
)
_TITLE = "Synthetic broad ETF return observation summary"
_SUMMARY = (
    "Section is advisory-only synthetic close-to-close return observation content."
)


def build_synthetic_research_return_observation_brief_section() -> (
    ResearchReturnObservationBriefSection
):
    """Return the deterministic synthetic return observation brief section."""

    primary_item = build_synthetic_research_return_observation_brief_item()
    insufficient_item = (
        build_synthetic_insufficient_research_return_observation_brief_item()
    )
    return build_research_return_observation_brief_section(
        section_id=_SECTION_ID,
        title=_TITLE,
        summary=_SUMMARY,
        items=(primary_item, insufficient_item),
    )


def expected_synthetic_research_return_observation_brief_section_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic return observation section payload."""

    primary_item = expected_synthetic_research_return_observation_brief_item_dict()
    insufficient_item = (
        expected_synthetic_insufficient_research_return_observation_brief_item_dict()
    )
    return {
        "section_type": "research_return_observation_brief_section",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "section_id": _SECTION_ID,
        "title": _TITLE,
        "summary": _SUMMARY,
        "item_count": 2,
        "items": [primary_item, insufficient_item],
        "limitations": _combined_text_values(
            primary_item["limitations"],
            insufficient_item["limitations"],
        ),
        "non_claims": _combined_text_values(
            primary_item["non_claims"],
            insufficient_item["non_claims"],
        ),
    }


def _combined_text_values(first: object, second: object) -> list[str]:
    values: list[str] = []
    for group in (first, second):
        for value in group:
            if value in values:
                continue
            values.append(value)

    return values
