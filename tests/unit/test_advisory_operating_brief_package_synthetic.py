from __future__ import annotations

import hashlib
import json

from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)
from algotrader.research.research_data_source_readiness_summary import (
    build_research_data_source_readiness_summary,
)
from algotrader.research.research_observation_manifest import (
    ResearchObservationManifest,
)
from tests.fixtures.advisory_operating_brief_diagnostic_issue import (
    expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts,
)
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_dict,
    expected_synthetic_research_data_source_readiness_summary_dict,
)


_OBSERVATION_NAME = "sma_return_research_pipeline_observation"
_FORBIDDEN_MANIFEST_TERMS = (
    "approval",
    "approved",
    "readiness",
    "recommend",
    "recommendation",
    "broker",
    "account",
    "order",
    "fill",
    "portfolio",
    "cash",
    "equity",
    "pnl",
    "allocation",
    "trading authority",
    "trading_ready",
    "trading-ready",
    "credential",
    "path",
    "file",
)
_FORBIDDEN_READINESS_FIELD_TERMS = (
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
_FORBIDDEN_DIAGNOSTIC_ISSUE_VOCABULARY = (
    "ranking",
    "scoring",
    "recommend",
    "recommendation",
    "approval",
    "approved",
)
_FORBIDDEN_ADVISORY_SECTION_VOCABULARY = (
    "ranking",
    "scoring",
    "recommend",
    "recommendation",
    "approval",
    "approved",
)
_FORBIDDEN_ADVISORY_VIEW_VOCABULARY = (
    "ranking",
    "scoring",
    "recommend",
    "recommendation",
    "approval",
    "approved",
)


def test_synthetic_preview_includes_one_named_research_manifest_entry() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest
    payload = package.to_dict()
    manifest_payload = _dict(payload["research_observation_manifest"])
    entries = _list(manifest_payload["entries"])

    assert type(manifest) is ResearchObservationManifest
    assert manifest.entry_count == 1
    assert len(entries) == 1
    assert manifest.entries[0].observation_name == _OBSERVATION_NAME
    assert entries[0]["observation_name"] == _OBSERVATION_NAME
    assert manifest_payload == manifest.to_dict()


def test_synthetic_manifest_digest_matches_sma_observation_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest
    observation = package.sma_return_research_pipeline_observation

    assert manifest is not None
    assert observation is not None

    observation_payload = observation.to_dict()
    entry = manifest.entries[0]

    assert entry.observation_name == _OBSERVATION_NAME
    assert entry.observation_type == observation_payload["observation_type"]
    assert entry.payload_key_count == len(observation_payload)
    assert entry.payload_digest_sha256 == _payload_digest(observation_payload)
    assert package.to_dict()["sma_return_research_pipeline_observation"] == (
        observation_payload
    )


def test_repeated_synthetic_payload_and_sorted_json_are_byte_deterministic() -> None:
    first = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    second = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    first_json = _compact_sorted_json(first)
    second_json = _compact_sorted_json(second)

    assert first == second
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert json.loads(first_json) == first


def test_synthetic_preview_includes_data_source_readiness_branch() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    payload = package.to_dict()
    content_bundle = _dict(payload["content_bundle"])
    content_bundle_export = _dict(payload["content_bundle_export"])
    readiness_payload = expected_synthetic_research_data_source_readiness_dict()
    summary_payload = expected_synthetic_research_data_source_readiness_summary_dict(
        build_research_data_source_readiness_summary
    )
    readiness = expected_synthetic_research_data_source_readiness()
    package_readiness = package.content_bundle.research_data_source_readiness[0]
    package_summary = package.content_bundle.research_data_source_readiness_summaries[
        0
    ]

    assert content_bundle["research_data_source_readiness_count"] == 1
    assert content_bundle["research_data_source_readiness"] == [readiness_payload]
    assert content_bundle["research_data_source_readiness_summary_count"] == 1
    assert content_bundle["research_data_source_readiness_summaries"] == [
        summary_payload
    ]
    assert content_bundle_export["payload"] == content_bundle
    assert '"research_data_source_readiness"' in content_bundle_export["json_text"]
    assert (
        '"research_data_source_readiness_summaries"'
        in content_bundle_export["json_text"]
    )
    assert "Research Data Source Readiness Diagnostics" in content_bundle_export[
        "rendered_text"
    ]
    assert "Research Data Source Readiness Summary Diagnostics" in (
        content_bundle_export["rendered_text"]
    )
    assert package_readiness.to_dict() == readiness_payload
    assert package_summary.to_dict() == summary_payload
    assert package_summary.source_readiness is package_readiness
    assert package_summary.missing_control_count == len(
        package_readiness.missing_controls
    )
    assert readiness_payload["missing_controls"] == list(readiness.missing_controls)
    assert readiness_payload["missing_controls"] == list(
        package_readiness.missing_controls
    )
    assert readiness_payload["missing_controls"] == [
        control
        for control in readiness_payload["required_controls"]
        if control not in readiness_payload["satisfied_controls"]
    ]
    assert readiness.missing_controls


def test_synthetic_preview_includes_diagnostic_issues_branch_deterministically() -> None:
    first_payload = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    second_payload = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    content_bundle = _dict(first_payload["content_bundle"])
    second_content_bundle = _dict(second_payload["content_bundle"])
    content_bundle_export = _dict(first_payload["content_bundle_export"])
    expected_issues = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts()
    )
    issue_payload = {"diagnostic_issues": content_bundle["diagnostic_issues"]}
    second_issue_payload = {
        "diagnostic_issues": second_content_bundle["diagnostic_issues"]
    }
    issue_json = _compact_sorted_json(issue_payload)
    second_issue_json = _compact_sorted_json(second_issue_payload)

    assert content_bundle["diagnostic_issue_count"] == len(expected_issues)
    assert content_bundle["diagnostic_issues"] == expected_issues
    assert second_content_bundle["diagnostic_issues"] == expected_issues
    assert content_bundle_export["payload"] == content_bundle
    assert '"diagnostic_issues"' in content_bundle_export["json_text"]
    assert "Diagnostic Issues" in content_bundle_export["rendered_text"]
    assert issue_json == second_issue_json
    assert issue_json.encode("utf-8") == second_issue_json.encode("utf-8")
    assert json.loads(issue_json) == issue_payload


def test_synthetic_diagnostic_issues_add_no_trading_fields_or_positive_terms() -> None:
    payload = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    content_bundle = _dict(payload["content_bundle"])
    issue_payloads = _list(content_bundle["diagnostic_issues"])
    field_names = _serialized_keys(issue_payloads)
    compact = _compact_sorted_json({"diagnostic_issues": issue_payloads}).lower()

    assert _matching_field_terms(
        field_names,
        _FORBIDDEN_READINESS_FIELD_TERMS,
    ) == []
    for term in _FORBIDDEN_DIAGNOSTIC_ISSUE_VOCABULARY:
        assert term not in compact


def test_synthetic_preview_includes_advisory_sections_branch_deterministically() -> None:
    first_package = build_synthetic_advisory_operating_brief_package_preview()
    second_package = build_synthetic_advisory_operating_brief_package_preview()
    first_payload = first_package.to_dict()
    second_payload = second_package.to_dict()
    content_bundle = _dict(first_payload["content_bundle"])
    second_content_bundle = _dict(second_payload["content_bundle"])
    content_bundle_export = _dict(first_payload["content_bundle_export"])
    section_payloads = _list(content_bundle["advisory_sections"])
    second_section_payloads = _list(second_content_bundle["advisory_sections"])
    section_json = _compact_sorted_json({"advisory_sections": section_payloads})
    second_section_json = _compact_sorted_json(
        {"advisory_sections": second_section_payloads}
    )

    assert content_bundle["advisory_section_count"] == len(
        first_package.content_bundle.advisory_sections
    )
    assert content_bundle["advisory_sections"] == [
        section.to_dict()
        for section in first_package.content_bundle.advisory_sections
    ]
    assert second_content_bundle["advisory_sections"] == [
        section.to_dict()
        for section in second_package.content_bundle.advisory_sections
    ]
    assert [section["section_key"] for section in section_payloads] == [
        section.section_key
        for section in first_package.content_bundle.advisory_sections
    ]
    assert content_bundle_export["payload"] == content_bundle
    assert '"advisory_sections"' in content_bundle_export["json_text"]
    assert "Advisory Sections" in content_bundle_export["rendered_text"]
    assert section_json == second_section_json
    assert section_json.encode("utf-8") == second_section_json.encode("utf-8")
    assert json.loads(section_json) == {"advisory_sections": section_payloads}


def test_synthetic_advisory_sections_add_no_trading_fields_or_positive_terms() -> None:
    payload = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    content_bundle = _dict(payload["content_bundle"])
    section_payloads = _list(content_bundle["advisory_sections"])
    field_names = _serialized_keys(section_payloads)
    compact = _compact_sorted_json({"advisory_sections": section_payloads}).lower()

    assert _matching_field_terms(
        field_names,
        _FORBIDDEN_READINESS_FIELD_TERMS,
    ) == []
    for term in _FORBIDDEN_ADVISORY_SECTION_VOCABULARY:
        assert term not in compact


def test_synthetic_preview_includes_advisory_view_branch_deterministically() -> None:
    first_package = build_synthetic_advisory_operating_brief_package_preview()
    second_package = build_synthetic_advisory_operating_brief_package_preview()
    first_payload = first_package.to_dict()
    second_payload = second_package.to_dict()
    content_bundle = _dict(first_payload["content_bundle"])
    second_content_bundle = _dict(second_payload["content_bundle"])
    content_bundle_export = _dict(first_payload["content_bundle_export"])
    advisory_view = first_package.content_bundle.advisory_view
    second_advisory_view = second_package.content_bundle.advisory_view
    view_payload = _dict(content_bundle["advisory_view"])
    second_view_payload = _dict(second_content_bundle["advisory_view"])
    view_json = _compact_sorted_json({"advisory_view": view_payload})
    second_view_json = _compact_sorted_json(
        {"advisory_view": second_view_payload}
    )

    assert advisory_view is not None
    assert second_advisory_view is not None
    assert view_payload == advisory_view.to_dict()
    assert second_view_payload == second_advisory_view.to_dict()
    assert view_payload["section_keys"] == [
        section.section_key
        for section in first_package.content_bundle.advisory_sections
    ]
    assert view_payload["section_count"] == len(
        first_package.content_bundle.advisory_sections
    )
    assert content_bundle_export["payload"] == content_bundle
    assert '"advisory_view"' in content_bundle_export["json_text"]
    assert "Advisory View" in content_bundle_export["rendered_text"]
    assert view_json == second_view_json
    assert view_json.encode("utf-8") == second_view_json.encode("utf-8")
    assert json.loads(view_json) == {"advisory_view": view_payload}


def test_synthetic_advisory_view_adds_no_trading_fields_or_positive_terms() -> None:
    payload = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    content_bundle = _dict(payload["content_bundle"])
    view_payload = _dict(content_bundle["advisory_view"])
    field_names = _serialized_keys(view_payload)
    compact = _compact_sorted_json({"advisory_view": view_payload}).lower()

    assert _matching_field_terms(
        field_names,
        _FORBIDDEN_READINESS_FIELD_TERMS,
    ) == []
    for term in _FORBIDDEN_ADVISORY_VIEW_VOCABULARY:
        assert term not in compact


def test_synthetic_preview_readiness_branch_has_no_runtime_trading_or_vendor_fields() -> (
    None
):
    payload = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    content_bundle = _dict(payload["content_bundle"])
    readiness_payload = _list(content_bundle["research_data_source_readiness"])[0]
    summary_payload = _list(
        content_bundle["research_data_source_readiness_summaries"]
    )[0]
    field_names = _serialized_keys(readiness_payload)
    summary_field_names = _serialized_keys(summary_payload)

    assert _matching_field_terms(
        field_names,
        _FORBIDDEN_READINESS_FIELD_TERMS,
    ) == []
    assert _matching_field_terms(
        summary_field_names,
        _FORBIDDEN_READINESS_FIELD_TERMS,
    ) == []


def test_manifest_payload_adds_no_authority_or_trading_language() -> None:
    payload = build_synthetic_advisory_operating_brief_package_preview().to_dict()
    manifest_payload = _dict(payload["research_observation_manifest"])
    compact = _compact_sorted_json(manifest_payload).lower()

    for term in _FORBIDDEN_MANIFEST_TERMS:
        assert term not in compact


def _payload_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        _compact_sorted_json(payload).encode("utf-8")
    ).hexdigest()


def _compact_sorted_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


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
