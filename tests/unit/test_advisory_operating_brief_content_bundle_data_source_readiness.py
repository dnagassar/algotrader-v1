from __future__ import annotations

import json

import pytest

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from algotrader.research.research_data_source_readiness_summary import (
    ResearchDataSourceReadinessSummary,
    build_research_data_source_readiness_summary,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary,
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict,
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary_dict,
)
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_dict,
    expected_synthetic_research_data_source_readiness_summary,
    expected_synthetic_research_data_source_readiness_summary_dict,
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
EXPECTED_SUMMARY_BRANCH_LINES = (
    "Research Data Source Readiness Summary Diagnostics",
    "",
    "Research Data Source Readiness Summary Diagnostic 1",
    "summary_type: research_data_source_readiness_summary",
    "schema_version: 1",
    "summary_scope: advisory_metadata_only",
    "summary_state: candidate_only",
    "required_control_count: 6",
    "satisfied_control_count: 1",
    "missing_control_count: 5",
    "diagnostic_limitations:",
    "- Fixture carries no observations, values, or external source content.",
    "- Fixture is synthetic metadata only and not connected to real data.",
)


def test_readiness_branch_is_absent_from_existing_default_fixture() -> None:
    payload = build_synthetic_advisory_operating_brief_content_bundle().to_dict()

    assert "research_data_source_readiness" not in payload
    assert "research_data_source_readiness_count" not in payload
    assert "research_data_source_readiness_summaries" not in payload
    assert "research_data_source_readiness_summary_count" not in payload


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


def test_summary_branch_payload_is_explicit_and_absent_by_default() -> None:
    default_payload = build_synthetic_advisory_operating_brief_content_bundle().to_dict()
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary()
    )
    payload = bundle.to_dict()
    expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary_dict()
    )
    summary_payload = expected_synthetic_research_data_source_readiness_summary_dict(
        build_research_data_source_readiness_summary
    )

    assert "research_data_source_readiness_summaries" not in default_payload
    assert "research_data_source_readiness_summary_count" not in default_payload
    assert payload == expected
    assert payload["research_data_source_readiness_summary_count"] == 1
    assert payload["research_data_source_readiness_summaries"] == [summary_payload]
    assert "research_data_source_readiness" not in payload
    assert "research_data_source_readiness_count" not in payload


def test_summary_branch_rejects_subclasses_lookalikes_and_non_summaries() -> None:
    class SummaryLookalike:
        summary_type = "research_data_source_readiness_summary"
        schema_version = "1"
        summary_scope = "advisory_metadata_only"
        summary_state = "candidate_only"
        required_control_count = 1
        satisfied_control_count = 0
        missing_control_count = 1
        diagnostic_limitations = ("diagnostic metadata only",)

        def to_dict(self) -> dict[str, object]:
            return {
                "summary_type": self.summary_type,
                "schema_version": self.schema_version,
                "summary_scope": self.summary_scope,
                "summary_state": self.summary_state,
                "required_control_count": self.required_control_count,
                "satisfied_control_count": self.satisfied_control_count,
                "missing_control_count": self.missing_control_count,
                "diagnostic_limitations": list(self.diagnostic_limitations),
            }

    class SummarySubclass(ResearchDataSourceReadinessSummary):
        pass

    source_bundle = build_synthetic_advisory_operating_brief_content_bundle()
    summary = expected_synthetic_research_data_source_readiness_summary(
        build_research_data_source_readiness_summary
    )
    subclass = SummarySubclass(
        summary_type=summary.summary_type,
        schema_version=summary.schema_version,
        summary_scope=summary.summary_scope,
        summary_state=summary.summary_state,
        required_control_count=summary.required_control_count,
        satisfied_control_count=summary.satisfied_control_count,
        missing_control_count=summary.missing_control_count,
        diagnostic_limitations=summary.diagnostic_limitations,
        source_readiness=summary.source_readiness,
    )

    for value in (None, object(), {}, SummaryLookalike(), subclass):
        with pytest.raises(ValidationError, match="ResearchDataSourceReadinessSummary"):
            build_advisory_operating_brief_content_bundle(
                candidate_research_briefs=source_bundle.candidate_research_briefs,
                strategy_eligibility_briefs=(
                    source_bundle.strategy_eligibility_briefs
                ),
                research_data_source_readiness_summaries=(value,),
            )

    with pytest.raises(ValidationError, match="ResearchDataSourceReadinessSummary"):
        AdvisoryOperatingBriefContentBundle(
            bundle_type=source_bundle.bundle_type,
            status=source_bundle.status,
            authority=source_bundle.authority,
            capital_authority=source_bundle.capital_authority,
            title=source_bundle.title,
            summary=source_bundle.summary,
            candidate_research_briefs=source_bundle.candidate_research_briefs,
            strategy_eligibility_briefs=source_bundle.strategy_eligibility_briefs,
            limitations=source_bundle.limitations,
            non_claims=source_bundle.non_claims,
            research_data_source_readiness_summaries=(subclass,),
        )


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


def test_summary_branch_export_serializes_through_summary_to_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary()
    )
    summary = bundle.research_data_source_readiness_summaries[0]
    original_to_dict = ResearchDataSourceReadinessSummary.to_dict
    expected_summary_payload = original_to_dict(summary)
    calls: list[ResearchDataSourceReadinessSummary] = []

    def tracking_to_dict(
        self: ResearchDataSourceReadinessSummary,
    ) -> dict[str, object]:
        calls.append(self)
        return original_to_dict(self)

    monkeypatch.setattr(
        ResearchDataSourceReadinessSummary,
        "to_dict",
        tracking_to_dict,
    )

    exported = export_advisory_operating_brief_content_bundle(bundle)

    assert calls == [summary, summary]
    assert exported.payload["research_data_source_readiness_summaries"] == [
        expected_summary_payload
    ]
    assert json.loads(exported.json_text)["research_data_source_readiness_summaries"] == [
        expected_summary_payload
    ]


def test_readiness_branch_renderer_pins_diagnostic_text_segment() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert _readiness_branch_lines(rendered) == EXPECTED_BRANCH_LINES
    assert "metadata_ready" not in rendered
    assert "source approval" in rendered
    assert "- no source approval" in rendered


def test_summary_branch_renderer_pins_diagnostic_text_segment() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary()
    )
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)

    assert _readiness_summary_branch_lines(rendered) == EXPECTED_SUMMARY_BRANCH_LINES
    assert "Research Data Source Readiness Diagnostics" not in rendered
    assert "source_readiness:" not in rendered
    assert "source_readiness" not in _serialized_keys(bundle.to_dict())
    assert "ready_to_trade" not in rendered


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


def test_summary_branch_outputs_are_byte_for_byte_deterministic() -> None:
    first = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary()
    )
    second = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary()
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


def test_summary_branch_adds_no_runtime_trading_or_vendor_fields() -> None:
    payload = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary()
    ).to_dict()
    field_names = _serialized_keys(payload)

    assert _matching_field_terms(field_names, FORBIDDEN_FIELD_TERMS) == []


def _readiness_branch_lines(rendered: str) -> tuple[str, ...]:
    lines = tuple(rendered.splitlines())
    start = lines.index("Research Data Source Readiness Diagnostics")
    end = lines.index("Limitations", start)

    return lines[start : end - 1]


def _readiness_summary_branch_lines(rendered: str) -> tuple[str, ...]:
    lines = tuple(rendered.splitlines())
    start = lines.index("Research Data Source Readiness Summary Diagnostics")
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
