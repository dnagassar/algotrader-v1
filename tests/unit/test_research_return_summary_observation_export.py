from __future__ import annotations

import json

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_summary_observation_brief import (
    ResearchReturnSummaryObservationBriefExport,
    export_research_return_summary_observation_brief,
    render_research_return_summary_observation_brief_text,
)
from tests.fixtures.research_return_summary_observation import (
    build_synthetic_research_return_summary_observation_brief,
    expected_synthetic_research_return_summary_observation_brief_dict,
)


def test_export_matches_expected_payload_json_and_rendered_text() -> None:
    brief = build_synthetic_research_return_summary_observation_brief()
    expected_payload = expected_synthetic_research_return_summary_observation_brief_dict()

    exported = export_research_return_summary_observation_brief(brief)

    assert type(exported) is ResearchReturnSummaryObservationBriefExport
    assert exported.payload == expected_payload
    assert exported.json_text == json.dumps(
        expected_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json.loads(exported.json_text) == expected_payload
    assert exported.rendered_text == (
        render_research_return_summary_observation_brief_text(brief)
    )


def test_export_payload_is_a_fresh_primitive_copy() -> None:
    brief = build_synthetic_research_return_summary_observation_brief()
    exported = export_research_return_summary_observation_brief(brief)
    first_payload = exported.payload
    second_payload = exported.payload

    assert first_payload == second_payload
    assert first_payload is not second_payload

    first_payload["title"] = "changed copied payload"
    first_payload["summary_observations"][0]["symbol"] = "CHANGED"
    first_payload["limitations"].append("changed copied payload")

    assert exported.payload == expected_synthetic_research_return_summary_observation_brief_dict()
    assert brief.to_dict() == expected_synthetic_research_return_summary_observation_brief_dict()


def test_repeated_exports_are_byte_deterministic() -> None:
    first = export_research_return_summary_observation_brief(
        build_synthetic_research_return_summary_observation_brief()
    )
    second = export_research_return_summary_observation_brief(
        build_synthetic_research_return_summary_observation_brief()
    )

    assert first == second
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert first.rendered_text.encode("utf-8") == (
        second.rendered_text.encode("utf-8")
    )


def test_export_rejects_non_summary_brief_inputs() -> None:
    for value in (None, object(), {}):
        with pytest.raises(ValidationError, match="ResearchReturnSummaryObservationBrief"):
            export_research_return_summary_observation_brief(value)
