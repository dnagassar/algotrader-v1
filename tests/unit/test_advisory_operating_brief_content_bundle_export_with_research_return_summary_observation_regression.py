from __future__ import annotations

import json

from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation,
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation_dict,
)


_EXPECTED_PAYLOAD = (
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation_dict()
)
_EXPECTED_JSON_TEXT = json.dumps(
    _EXPECTED_PAYLOAD,
    sort_keys=True,
    separators=(",", ":"),
)


def test_summary_branch_export_matches_expected_bundle_views() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation()
    )
    expected_rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    exported = export_advisory_operating_brief_content_bundle(bundle)

    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert json.loads(exported.json_text) == _EXPECTED_PAYLOAD
    assert exported.rendered_text == expected_rendered
    assert bundle.to_dict() == _EXPECTED_PAYLOAD


def test_summary_branch_order_and_counts_are_pinned() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation()
    )
    payload = exported.payload
    lines = tuple(exported.rendered_text.splitlines())

    assert tuple(payload) == tuple(_EXPECTED_PAYLOAD)
    assert payload["research_return_observation_brief_count"] == 1
    assert payload["research_return_summary_observation_brief_count"] == 1
    assert _index(payload, "research_return_observation_briefs") < _index(
        payload,
        "research_return_summary_observation_briefs",
    )
    assert _index(payload, "research_return_summary_observation_briefs") < _index(
        payload,
        "limitations",
    )
    assert lines.index("Research Return Observation Briefs") < lines.index(
        "Research Return Summary Observation Briefs"
    )
    assert lines.index("Research Return Summary Observation Briefs") < lines.index(
        "Limitations"
    )


def test_summary_branch_payload_and_rendered_fields_are_pinned() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation()
    )
    payload = exported.payload
    summary_brief = _dict(_list(payload["research_return_summary_observation_briefs"])[0])
    primary, insufficient = (
        _dict(item) for item in _list(summary_brief["summary_observations"])
    )
    rendered = exported.rendered_text

    assert summary_brief["brief_type"] == "research_return_summary_observation_brief"
    assert summary_brief["summary_observation_count"] == 2
    assert primary["summary_state"] == "returns_summarized"
    assert insufficient["summary_state"] == "insufficient_return_history"
    assert primary["source_return_count"] == 3
    assert insufficient["source_return_count"] == 0
    assert primary["positive_return_count"] == 1
    assert primary["negative_return_count"] == 1
    assert primary["zero_return_count"] == 1
    assert primary["min_simple_return"] == "-0.1"
    assert primary["max_simple_return"] == "0.05"
    assert primary["mean_simple_return"] == "-0.01666666666666666666666666667"
    assert insufficient["min_simple_return"] is None
    assert insufficient["max_simple_return"] is None
    assert insufficient["mean_simple_return"] is None
    assert primary["source_observation"]["returns"][0]["simple_return"] == "0.05"
    assert insufficient["source_observation"]["returns"] == []
    assert "research_return_summary_observation_brief_count: 1" in rendered
    assert "Research Return Summary Observation Brief 1" in rendered
    assert "summary_state: returns_summarized" in rendered
    assert "summary_state: insufficient_return_history" in rendered
    assert "mean_simple_return: -0.01666666666666666666666666667" in rendered
    assert "- none; insufficient_return_history has no close-to-close return points." in (
        rendered
    )


def test_summary_branch_export_is_byte_deterministic() -> None:
    first = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation()
    )
    second = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation()
    )

    assert first == second
    assert first.payload == second.payload == _EXPECTED_PAYLOAD
    assert first.json_text == second.json_text == _EXPECTED_JSON_TEXT
    assert first.rendered_text == second.rendered_text


def _index(payload: dict[str, object], key: str) -> int:
    return tuple(payload).index(key)


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)
    return value
