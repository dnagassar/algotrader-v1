from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_summary_observation_brief import (
    ResearchReturnSummaryObservationBrief,
    build_research_return_summary_observation_brief,
    render_research_return_summary_observation_brief_text,
)
from tests.fixtures.research_return_summary_observation import (
    build_synthetic_insufficient_research_return_summary_observation,
    build_synthetic_research_return_summary_observation,
    build_synthetic_research_return_summary_observation_brief,
    expected_synthetic_research_return_summary_observation_brief_dict,
)


_BRIEF_ID = (
    "research-return-summary-observation-brief:synthetic:"
    "broad-etf-return-summary"
)
_TITLE = "Synthetic broad ETF return summary observation brief"
_SUMMARY = (
    "Brief is advisory-only synthetic close-to-close return summary "
    "observation content."
)


def test_builds_summary_brief_with_exact_source_identity() -> None:
    primary = build_synthetic_research_return_summary_observation()
    insufficient = build_synthetic_insufficient_research_return_summary_observation()

    brief = build_research_return_summary_observation_brief(
        brief_id=_BRIEF_ID,
        title=_TITLE,
        summary=_SUMMARY,
        summary_observations=(primary, insufficient),
    )

    assert type(brief) is ResearchReturnSummaryObservationBrief
    assert brief.summary_observations == (primary, insufficient)
    assert brief.summary_observations[0] is primary
    assert brief.summary_observations[1] is insufficient
    assert brief.to_dict() == (
        expected_synthetic_research_return_summary_observation_brief_dict()
    )


def test_fixed_metadata_field_order_and_serialization_are_pinned() -> None:
    brief = build_synthetic_research_return_summary_observation_brief()
    payload = brief.to_dict()

    assert tuple(field.name for field in fields(ResearchReturnSummaryObservationBrief)) == (
        "brief_type",
        "status",
        "authority",
        "capital_authority",
        "brief_id",
        "title",
        "summary",
        "summary_observations",
        "limitations",
        "non_claims",
    )
    assert tuple(payload) == (
        "brief_type",
        "status",
        "authority",
        "capital_authority",
        "brief_id",
        "title",
        "summary",
        "summary_observation_count",
        "summary_observations",
        "limitations",
        "non_claims",
    )
    assert payload["brief_type"] == "research_return_summary_observation_brief"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False


def test_repeated_summary_brief_builds_are_json_deterministic() -> None:
    first = build_synthetic_research_return_summary_observation_brief()
    second = build_synthetic_research_return_summary_observation_brief()

    assert first == second
    assert first is not second
    assert first.to_dict() == second.to_dict()
    assert json.dumps(first.to_dict(), sort_keys=True, separators=(",", ":")) == (
        json.dumps(second.to_dict(), sort_keys=True, separators=(",", ":"))
    )


def test_rendered_text_contains_summary_and_nested_source_observation() -> None:
    rendered = render_research_return_summary_observation_brief_text(
        build_synthetic_research_return_summary_observation_brief()
    )

    assert "Research Return Summary Observation Brief" in rendered
    assert "summary_observation_count: 2" in rendered
    assert "summary_state: returns_summarized" in rendered
    assert "summary_state: insufficient_return_history" in rendered
    assert "source_return_count: 3" in rendered
    assert "source_return_count: 0" in rendered
    assert "min_simple_return: -0.1" in rendered
    assert "max_simple_return: 0.05" in rendered
    assert "mean_simple_return: -0.01666666666666666666666666667" in rendered
    assert "Return Point 1" in rendered
    assert "- none; insufficient_return_history has no close-to-close return points." in (
        rendered
    )


def test_summary_brief_rejects_invalid_inputs_and_duplicates() -> None:
    primary = build_synthetic_research_return_summary_observation()

    with pytest.raises(ValidationError, match="summary_observations"):
        build_research_return_summary_observation_brief(
            brief_id=_BRIEF_ID,
            title=_TITLE,
            summary=_SUMMARY,
            summary_observations=(),
        )
    with pytest.raises(ValidationError, match="duplicate"):
        build_research_return_summary_observation_brief(
            brief_id=_BRIEF_ID,
            title=_TITLE,
            summary=_SUMMARY,
            summary_observations=(primary, primary),
        )
    with pytest.raises(ValidationError, match="summary_observations"):
        build_research_return_summary_observation_brief(
            brief_id=_BRIEF_ID,
            title=_TITLE,
            summary=_SUMMARY,
            summary_observations=(object(),),
        )


def test_summary_brief_is_frozen_slotted_and_has_no_from_dict() -> None:
    brief = build_synthetic_research_return_summary_observation_brief()

    assert hasattr(ResearchReturnSummaryObservationBrief, "__slots__")
    assert not hasattr(ResearchReturnSummaryObservationBrief, "from_dict")
    assert not hasattr(brief, "from_dict")
    with pytest.raises(FrozenInstanceError):
        brief.title = "changed"
