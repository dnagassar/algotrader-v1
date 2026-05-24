"""Deterministic synthetic SMA research observation brief fixtures."""

from __future__ import annotations

from algotrader.research.sma_research_observation_brief import (
    SmaResearchObservationBriefItem,
    build_sma_research_observation_brief_item,
)
from tests.fixtures.sma_research_observation import (
    build_synthetic_insufficient_history_sma_research_observation,
    build_synthetic_sma_research_observation,
    expected_synthetic_insufficient_history_sma_research_observation_dict,
    expected_synthetic_sma_research_observation_dict,
)

__all__ = [
    "build_synthetic_sma_research_observation_brief_item",
    "expected_synthetic_sma_research_observation_brief_item_dict",
    "build_synthetic_insufficient_history_sma_research_observation_brief_item",
    "expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict",
]

_PRIMARY_HEADLINE = (
    "SMA observation SYNTH_ETF 2026-01-20: above_sma_observation."
)
_PRIMARY_SUMMARY = (
    "SMA observation metadata records above_sma_observation for SYNTH_ETF "
    "as of 2026-01-20 with window 3, 3 eligible sample(s), 1 later sample(s) "
    "ignored, latest close 110.00, SMA 100.00, distance 10.00, and distance "
    "pct 0.1."
)
_INSUFFICIENT_HEADLINE = (
    "SMA observation SYNTH_ETF 2026-01-20: insufficient_history."
)
_INSUFFICIENT_SUMMARY = (
    "SMA observation metadata records insufficient_history for SYNTH_ETF "
    "as of 2026-01-20 with window 3, 2 eligible sample(s), 1 later sample(s) "
    "ignored, latest close 101.00, SMA none, distance none, and distance "
    "pct none."
)


def build_synthetic_sma_research_observation_brief_item() -> (
    SmaResearchObservationBriefItem
):
    """Return the deterministic synthetic SMA observation brief item."""

    observation = build_synthetic_sma_research_observation()
    return build_sma_research_observation_brief_item(observation)


def expected_synthetic_sma_research_observation_brief_item_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic SMA observation brief item payload."""

    source_observation = expected_synthetic_sma_research_observation_dict()
    return {
        "item_type": "sma_research_observation_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "headline": _PRIMARY_HEADLINE,
        "summary": _PRIMARY_SUMMARY,
        "mechanical_state": "above_sma_observation",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def build_synthetic_insufficient_history_sma_research_observation_brief_item() -> (
    SmaResearchObservationBriefItem
):
    """Return the deterministic insufficient-history SMA observation brief item."""

    observation = build_synthetic_insufficient_history_sma_research_observation()
    return build_sma_research_observation_brief_item(observation)


def expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict() -> (
    dict[str, object]
):
    """Return the exact primitive insufficient-history SMA brief item payload."""

    source_observation = (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )
    return {
        "item_type": "sma_research_observation_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "headline": _INSUFFICIENT_HEADLINE,
        "summary": _INSUFFICIENT_SUMMARY,
        "mechanical_state": "insufficient_history",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }
