from __future__ import annotations

import json

from algotrader.research.research_return_summary_observation import (
    ResearchReturnSummaryObservation,
)
from algotrader.research.research_return_summary_observation_brief import (
    ResearchReturnSummaryObservationBrief,
)
from tests.fixtures.research_return_summary_observation import (
    build_synthetic_insufficient_research_return_summary_observation,
    build_synthetic_research_return_summary_observation,
    build_synthetic_research_return_summary_observation_brief,
    expected_synthetic_insufficient_research_return_summary_observation_dict,
    expected_synthetic_research_return_summary_observation_brief_dict,
    expected_synthetic_research_return_summary_observation_dict,
)


def test_summary_observation_fixture_matches_expected_dict_exactly() -> None:
    summary = build_synthetic_research_return_summary_observation()
    expected = expected_synthetic_research_return_summary_observation_dict()

    assert type(summary) is ResearchReturnSummaryObservation
    assert summary.to_dict() == expected
    assert tuple(summary.to_dict()) == tuple(expected)
    assert summary.summary_state == "returns_summarized"
    assert summary.source_return_count == 3
    assert summary.positive_return_count == 1
    assert summary.negative_return_count == 1
    assert summary.zero_return_count == 1


def test_insufficient_summary_fixture_matches_expected_dict_exactly() -> None:
    summary = build_synthetic_insufficient_research_return_summary_observation()
    expected = (
        expected_synthetic_insufficient_research_return_summary_observation_dict()
    )

    assert type(summary) is ResearchReturnSummaryObservation
    assert summary.to_dict() == expected
    assert tuple(summary.to_dict()) == tuple(expected)
    assert summary.summary_state == "insufficient_return_history"
    assert summary.source_return_count == 0
    assert summary.min_simple_return is None
    assert summary.max_simple_return is None
    assert summary.mean_simple_return is None


def test_summary_brief_fixture_matches_expected_dict_exactly() -> None:
    brief = build_synthetic_research_return_summary_observation_brief()
    expected = expected_synthetic_research_return_summary_observation_brief_dict()

    assert type(brief) is ResearchReturnSummaryObservationBrief
    assert brief.to_dict() == expected
    assert tuple(brief.to_dict()) == tuple(expected)
    assert len(brief.summary_observations) == 2
    assert brief.summary_observations[0].summary_state == "returns_summarized"
    assert brief.summary_observations[1].summary_state == (
        "insufficient_return_history"
    )


def test_fixture_payloads_are_primitive_fresh_and_json_deterministic() -> None:
    first = expected_synthetic_research_return_summary_observation_brief_dict()
    second = expected_synthetic_research_return_summary_observation_brief_dict()
    first_json = json.dumps(first, sort_keys=True, separators=(",", ":"))
    second_json = json.dumps(second, sort_keys=True, separators=(",", ":"))

    assert first == second
    assert first is not second
    assert first["summary_observations"] is not second["summary_observations"]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]
    assert first_json == second_json

    first["summary_observations"][0]["limitations"].append("mutated copy")
    first["non_claims"].append("not mutated copy")

    assert second == expected_synthetic_research_return_summary_observation_brief_dict()
