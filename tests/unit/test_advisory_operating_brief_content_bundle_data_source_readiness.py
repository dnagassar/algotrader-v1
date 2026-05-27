from __future__ import annotations

import json

from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness,
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict,
)
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_dict,
)


FORBIDDEN_FIELD_TERMS = (
    "broker",
    "order",
    "fill",
    "portfolio",
    "backtest",
    "runtime",
    "vendor",
    "network",
    "credential",
)

EXPECTED_BRANCH_LINES = (
    "Research Data Source Readiness Diagnostics",
    "",
    "Research Data Source Readiness Diagnostic 1",
    "contract_type: research_data_source_readiness",
    "schema_version: 1",
    "source_id: synthetic-broad-etf-source-candidate",
    "source_name: Synthetic broad ETF source candidate",
    "asset_class_scope:",
    "- equity_etf",
    "intended_use: pipeline_validation_only",
    "readiness_state: candidate_only",
    "required_controls:",
    "- terms_review_documented",
    "- snapshot_provenance_defined",
    "- redistribution_policy_reviewed",
    "- adjustment_policy_defined",
    "- fixture_policy_review_documented",
    "- no_lookahead_protocol_defined",
    "satisfied_controls:",
    "- no_lookahead_protocol_defined",
    "missing_controls:",
    "- terms_review_documented",
    "- snapshot_provenance_defined",
    "- redistribution_policy_reviewed",
    "- adjustment_policy_defined",
    "- fixture_policy_review_documented",
    "evidence_refs:",
    "- synthetic_phase_271_readiness_fixture",
    "- internal_control_gap_note",
    "limitations:",
    "- Fixture is synthetic metadata only and not connected to real data.",
    "- Fixture carries no observations, values, or external source content.",
    "non_claims:",
    "- no source approval",
    "- no data ingestion approval",
    "- no trading authority",
    "- no capital authority",
    "- no data-source authorization",
)


def test_readiness_branch_is_absent_from_existing_default_fixture() -> None:
    payload = build_synthetic_advisory_operating_brief_content_bundle().to_dict()

    assert "research_data_source_readiness" not in payload
    assert "research_data_source_readiness_count" not in payload


def test_readiness_branch_payload_is_explicit_and_preserves_missing_controls() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )
    payload = bundle.to_dict()
    expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict()
    )
    readiness = expected_synthetic_research_data_source_readiness()
    readiness_payload = expected_synthetic_research_data_source_readiness_dict()

    assert payload == expected
    assert payload["research_data_source_readiness_count"] == 1
    assert payload["research_data_source_readiness"] == [readiness_payload]
    assert payload["research_data_source_readiness"][0]["missing_controls"] == list(
        readiness.missing_controls
    )
    assert readiness.missing_controls


def test_readiness_branch_export_uses_compact_sorted_json() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )
    exported = export_advisory_operating_brief_content_bundle(bundle)
    expected_payload = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict()
    )
    expected_json = json.dumps(
        expected_payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    assert exported.payload == expected_payload
    assert exported.json_text == expected_json
    assert json.loads(exported.json_text) == expected_payload
    assert "\n" not in exported.json_text
    assert '": ' not in exported.json_text


def test_readiness_branch_renderer_pins_diagnostic_text_segment() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert _readiness_branch_lines(rendered) == EXPECTED_BRANCH_LINES
    assert "metadata_ready" not in rendered
    assert "source approval" in rendered
    assert "- no source approval" in rendered


def test_readiness_branch_outputs_are_byte_for_byte_deterministic() -> None:
    first = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )
    second = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )

    assert first.payload == second.payload
    assert first.json_text == second.json_text
    assert first.rendered_text == second.rendered_text
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")


def test_readiness_branch_adds_no_runtime_trading_or_vendor_fields() -> None:
    payload = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    ).to_dict()
    field_names = _serialized_keys(payload)

    assert _matching_field_terms(field_names, FORBIDDEN_FIELD_TERMS) == []


def _readiness_branch_lines(rendered: str) -> tuple[str, ...]:
    lines = tuple(rendered.splitlines())
    start = lines.index("Research Data Source Readiness Diagnostics")
    end = lines.index("Limitations", start)

    return lines[start : end - 1]


def _serialized_keys(value: object) -> set[str]:
    if type(value) is dict:
        return {
            key
            for dict_key, item in value.items()
            for key in {dict_key, *_serialized_keys(item)}
        }
    if type(value) is list:
        return {
            key
            for item in value
            for key in _serialized_keys(item)
        }

    return set()


def _matching_field_terms(
    field_names: set[str],
    forbidden_terms: tuple[str, ...],
) -> list[str]:
    return sorted(
        {
            term
            for field_name in field_names
            for term in forbidden_terms
            if term in field_name.lower()
        }
    )
