"""Deterministic synthetic research return observation brief fixtures."""

from __future__ import annotations

from algotrader.research.research_return_observation_brief import (
    ResearchReturnObservationBriefItem,
    build_research_return_observation_brief_item,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
    build_synthetic_research_return_series_observation,
    expected_synthetic_insufficient_research_return_series_observation_dict,
    expected_synthetic_research_return_series_observation_dict,
)

__all__ = [
    "build_synthetic_research_return_observation_brief_item",
    "expected_synthetic_research_return_observation_brief_item_dict",
    "build_synthetic_insufficient_research_return_observation_brief_item",
    "expected_synthetic_insufficient_research_return_observation_brief_item_dict",
]

_PRIMARY_HEADLINE = (
    "Research return observation SYNTH_ETF 2026-01-20: returns_constructed."
)
_PRIMARY_SUMMARY = (
    "Research return observation metadata records returns_constructed for "
    "SYNTH_ETF as of 2026-01-20 using close_to_close_simple_return on "
    "synthetic_close, 4 eligible sample(s), 1 later sample(s) ignored, "
    "3 return(s), positive count 1, negative count 1, and zero count 1."
)
_INSUFFICIENT_HEADLINE = (
    "Research return observation SYNTH_ETF 2026-01-20: "
    "insufficient_return_history."
)
_INSUFFICIENT_SUMMARY = (
    "Research return observation metadata records insufficient_return_history "
    "for SYNTH_ETF as of 2026-01-20 using close_to_close_simple_return on "
    "synthetic_close, 1 eligible sample(s), 1 later sample(s) ignored, "
    "0 return(s), positive count 0, negative count 0, and zero count 0."
)


def build_synthetic_research_return_observation_brief_item() -> (
    ResearchReturnObservationBriefItem
):
    """Return the deterministic synthetic return observation brief item."""

    observation = build_synthetic_research_return_series_observation()
    return build_research_return_observation_brief_item(observation)


def expected_synthetic_research_return_observation_brief_item_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic return observation brief payload."""

    source_observation = expected_synthetic_research_return_series_observation_dict()
    return {
        "item_type": "research_return_observation_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "headline": _PRIMARY_HEADLINE,
        "summary": _PRIMARY_SUMMARY,
        "mechanical_state": "returns_constructed",
        "positive_return_count": 1,
        "negative_return_count": 1,
        "zero_return_count": 1,
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def build_synthetic_insufficient_research_return_observation_brief_item() -> (
    ResearchReturnObservationBriefItem
):
    """Return the deterministic insufficient-history return observation brief item."""

    observation = build_synthetic_insufficient_research_return_series_observation()
    return build_research_return_observation_brief_item(observation)


def expected_synthetic_insufficient_research_return_observation_brief_item_dict() -> (
    dict[str, object]
):
    """Return the exact primitive insufficient-history return brief payload."""

    source_observation = (
        expected_synthetic_insufficient_research_return_series_observation_dict()
    )
    return {
        "item_type": "research_return_observation_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "headline": _INSUFFICIENT_HEADLINE,
        "summary": _INSUFFICIENT_SUMMARY,
        "mechanical_state": "insufficient_return_history",
        "positive_return_count": 0,
        "negative_return_count": 0,
        "zero_return_count": 0,
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }
