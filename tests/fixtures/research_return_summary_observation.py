"""Deterministic synthetic research return summary observation fixtures."""

from __future__ import annotations

from algotrader.research.research_return_summary_observation import (
    ResearchReturnSummaryObservation,
    build_research_return_summary_observation,
)
from algotrader.research.research_return_summary_observation_brief import (
    ResearchReturnSummaryObservationBrief,
    build_research_return_summary_observation_brief,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
    build_synthetic_research_return_series_observation,
    expected_synthetic_insufficient_research_return_series_observation_dict,
    expected_synthetic_research_return_series_observation_dict,
)

__all__ = [
    "build_synthetic_research_return_summary_observation",
    "expected_synthetic_research_return_summary_observation_dict",
    "build_synthetic_insufficient_research_return_summary_observation",
    "expected_synthetic_insufficient_research_return_summary_observation_dict",
    "build_synthetic_research_return_summary_observation_brief",
    "expected_synthetic_research_return_summary_observation_brief_dict",
]

_BRIEF_ID = (
    "research-return-summary-observation-brief:synthetic:"
    "broad-etf-return-summary"
)
_BRIEF_TITLE = "Synthetic broad ETF return summary observation brief"
_BRIEF_SUMMARY = (
    "Brief is advisory-only synthetic close-to-close return summary "
    "observation content."
)


def build_synthetic_research_return_summary_observation() -> (
    ResearchReturnSummaryObservation
):
    """Return the deterministic synthetic return summary observation."""

    return build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )


def expected_synthetic_research_return_summary_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive synthetic return summary payload."""

    source_observation = expected_synthetic_research_return_series_observation_dict()
    return {
        "observation_type": "research_return_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "return_method": "close_to_close_simple_return",
        "price_basis": "synthetic_close",
        "source_return_count": 3,
        "positive_return_count": 1,
        "negative_return_count": 1,
        "zero_return_count": 1,
        "min_simple_return": "-0.1",
        "max_simple_return": "0.05",
        "mean_simple_return": "-0.01666666666666666666666666667",
        "summary_state": "returns_summarized",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def build_synthetic_insufficient_research_return_summary_observation() -> (
    ResearchReturnSummaryObservation
):
    """Return a deterministic synthetic summary with too little return history."""

    return build_research_return_summary_observation(
        build_synthetic_insufficient_research_return_series_observation()
    )


def expected_synthetic_insufficient_research_return_summary_observation_dict() -> (
    dict[str, object]
):
    """Return the exact primitive insufficient-history summary payload."""

    source_observation = (
        expected_synthetic_insufficient_research_return_series_observation_dict()
    )
    return {
        "observation_type": "research_return_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "return_method": "close_to_close_simple_return",
        "price_basis": "synthetic_close",
        "source_return_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 0,
        "zero_return_count": 0,
        "min_simple_return": None,
        "max_simple_return": None,
        "mean_simple_return": None,
        "summary_state": "insufficient_return_history",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def build_synthetic_research_return_summary_observation_brief() -> (
    ResearchReturnSummaryObservationBrief
):
    """Return the deterministic synthetic return summary observation brief."""

    return build_research_return_summary_observation_brief(
        brief_id=_BRIEF_ID,
        title=_BRIEF_TITLE,
        summary=_BRIEF_SUMMARY,
        summary_observations=(
            build_synthetic_research_return_summary_observation(),
            build_synthetic_insufficient_research_return_summary_observation(),
        ),
    )


def expected_synthetic_research_return_summary_observation_brief_dict() -> (
    dict[str, object]
):
    """Return the exact primitive summary observation brief payload."""

    primary = expected_synthetic_research_return_summary_observation_dict()
    insufficient = (
        expected_synthetic_insufficient_research_return_summary_observation_dict()
    )
    limitations = _combined_expected_values(primary, insufficient, "limitations")
    non_claims = _combined_expected_values(primary, insufficient, "non_claims")

    return {
        "brief_type": "research_return_summary_observation_brief",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "brief_id": _BRIEF_ID,
        "title": _BRIEF_TITLE,
        "summary": _BRIEF_SUMMARY,
        "summary_observation_count": 2,
        "summary_observations": [primary, insufficient],
        "limitations": limitations,
        "non_claims": non_claims,
    }


def _combined_expected_values(
    first: dict[str, object],
    second: dict[str, object],
    field_name: str,
) -> list[str]:
    values: list[str] = []
    for payload in (first, second):
        for value in payload[field_name]:
            if value in values:
                continue
            values.append(value)

    return values
