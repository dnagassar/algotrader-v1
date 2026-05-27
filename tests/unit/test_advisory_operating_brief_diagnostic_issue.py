from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_diagnostic_issue import (
    AdvisoryOperatingBriefDiagnosticIssue,
    build_advisory_operating_brief_diagnostic_issues,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary,
)


EXPECTED_KEYS = [
    "source_branch",
    "issue_code",
    "issue_state",
    "diagnostic_message",
    "blocking_controls",
    "limitations",
]
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
FORBIDDEN_OUTPUT_TERMS = (
    "approval",
    "approved",
    "authorization",
    "authorized",
    "trade",
    "trading",
    "ranking",
    "score",
    "recommendation",
    "allocation",
    "ready_to_trade",
)


def test_builds_issues_from_synthetic_bundle_readiness_and_summary() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    readiness = bundle.research_data_source_readiness[0]
    summary = bundle.research_data_source_readiness_summaries[0]
    issues = build_advisory_operating_brief_diagnostic_issues(bundle)

    assert tuple(type(issue) for issue in issues) == (
        AdvisoryOperatingBriefDiagnosticIssue,
        AdvisoryOperatingBriefDiagnosticIssue,
    )
    assert tuple(issue.source_branch for issue in issues) == (
        "research_data_source_readiness",
        "research_data_source_readiness_summary",
    )
    assert tuple(issue.issue_code for issue in issues) == (
        "missing_diagnostic_controls",
        "missing_diagnostic_controls",
    )
    assert tuple(issue.issue_state for issue in issues) == (
        readiness.readiness_state,
        summary.summary_state,
    )


def test_missing_controls_are_carried_as_diagnostic_controls_not_approvals() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    readiness = bundle.research_data_source_readiness[0]
    issues = build_advisory_operating_brief_diagnostic_issues(bundle)

    assert issues[0].blocking_controls == readiness.missing_controls
    assert issues[1].blocking_controls == readiness.missing_controls
    assert issues[0].blocking_controls == (
        "terms_review_documented",
        "snapshot_provenance_defined",
        "redistribution_policy_reviewed",
        "adjustment_policy_defined",
        "fixture_policy_review_documented",
    )
    assert "approval" not in _compact_sorted_json(issues[0].to_dict()).lower()
    assert "approval" not in _compact_sorted_json(issues[1].to_dict()).lower()


def test_limitations_are_preserved_deterministically() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    readiness = bundle.research_data_source_readiness[0]
    summary = bundle.research_data_source_readiness_summaries[0]
    issues = build_advisory_operating_brief_diagnostic_issues(bundle)

    assert issues[0].limitations == readiness.limitations
    assert issues[1].limitations == summary.diagnostic_limitations
    assert issues[0].limitations == (
        "Fixture is synthetic metadata only and not connected to real data.",
        "Fixture carries no observations, values, or external source content.",
    )
    assert issues[1].limitations == (
        "Fixture carries no observations, values, or external source content.",
        "Fixture is synthetic metadata only and not connected to real data.",
    )


def test_issue_ordering_is_deterministic() -> None:
    first = build_advisory_operating_brief_diagnostic_issues(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    second = build_advisory_operating_brief_diagnostic_issues(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )

    assert tuple(issue.source_branch for issue in first) == (
        "research_data_source_readiness",
        "research_data_source_readiness_summary",
    )
    assert tuple(issue.to_dict() for issue in first) == tuple(
        issue.to_dict() for issue in second
    )


def test_issue_record_is_frozen_slotted_and_has_pinned_field_order() -> None:
    issue = build_advisory_operating_brief_diagnostic_issues(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )[0]

    assert is_dataclass(AdvisoryOperatingBriefDiagnosticIssue)
    assert AdvisoryOperatingBriefDiagnosticIssue.__dataclass_params__.frozen is True
    assert hasattr(AdvisoryOperatingBriefDiagnosticIssue, "__slots__")
    assert not hasattr(issue, "__dict__")
    assert tuple(field.name for field in fields(AdvisoryOperatingBriefDiagnosticIssue)) == (
        "source_branch",
        "issue_code",
        "issue_state",
        "diagnostic_message",
        "blocking_controls",
        "limitations",
    )
    with pytest.raises(FrozenInstanceError):
        issue.issue_state = "blocked"
    with pytest.raises((AttributeError, TypeError)):
        issue.extra_field = "not allowed"


def test_to_dict_is_primitive_only_deterministic_and_copying() -> None:
    issue = build_advisory_operating_brief_diagnostic_issues(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )[0]
    first = issue.to_dict()
    second = issue.to_dict()

    assert list(first) == EXPECTED_KEYS
    assert first == second
    assert _primitive_only(first)
    assert first["blocking_controls"] is not second["blocking_controls"]
    assert first["limitations"] is not second["limitations"]

    first["blocking_controls"].append("mutated_copy")
    first["limitations"].append("mutated copy")
    assert second == issue.to_dict()


def test_repeated_builds_are_equal() -> None:
    first_bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    second_bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    first = build_advisory_operating_brief_diagnostic_issues(first_bundle)
    second = build_advisory_operating_brief_diagnostic_issues(second_bundle)

    assert first == second
    assert first is not second
    assert tuple(issue.to_dict() for issue in first) == tuple(
        issue.to_dict() for issue in second
    )


def test_default_synthetic_bundle_has_no_diagnostic_issues() -> None:
    issues = build_advisory_operating_brief_diagnostic_issues(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert issues == ()


def test_subclasses_lookalikes_and_invalid_issue_values_are_rejected() -> None:
    class BundleLookalike:
        research_data_source_readiness = ()
        research_data_source_readiness_summaries = ()

    with pytest.raises(ValidationError, match="content_bundle"):
        build_advisory_operating_brief_diagnostic_issues(BundleLookalike())

    payload = _direct_issue_payload()
    for field_name, value in (
        ("source_branch", "candidate_research_briefs"),
        ("issue_code", "other_issue"),
        ("issue_state", ""),
        ("diagnostic_message", " "),
        ("blocking_controls", ()),
        ("blocking_controls", [""]),
        ("limitations", ()),
        ("limitations", [""]),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            AdvisoryOperatingBriefDiagnosticIssue(**mutated)


def test_no_runtime_vendor_or_trading_fields_are_introduced() -> None:
    payload = [
        issue.to_dict()
        for issue in build_advisory_operating_brief_diagnostic_issues(
            build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
        )
    ]
    field_names = _payload_keys(payload)

    assert _matching_field_terms(field_names, FORBIDDEN_FIELD_TERMS) == []
    assert "source_readiness" not in field_names
    assert "wrapper" not in field_names


def test_forbidden_approval_and_trading_vocabulary_is_absent() -> None:
    payload = [
        issue.to_dict()
        for issue in build_advisory_operating_brief_diagnostic_issues(
            build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
        )
    ]
    text = _compact_sorted_json(payload).lower()

    assert _matching_terms(text, FORBIDDEN_OUTPUT_TERMS) == []


def test_compact_sorted_json_is_byte_deterministic() -> None:
    issues = build_advisory_operating_brief_diagnostic_issues(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    first_json = _compact_sorted_json(
        [issue.to_dict() for issue in issues]
    ).encode("utf-8")
    second_json = _compact_sorted_json(
        [issue.to_dict() for issue in issues]
    ).encode("utf-8")

    assert first_json == second_json
    assert json.loads(first_json.decode("utf-8")) == [
        issue.to_dict() for issue in issues
    ]


def _direct_issue_payload() -> dict[str, object]:
    return {
        "source_branch": "research_data_source_readiness",
        "issue_code": "missing_diagnostic_controls",
        "issue_state": "candidate_only",
        "diagnostic_message": "Readiness branch reports missing diagnostic controls.",
        "blocking_controls": ("terms_review_documented",),
        "limitations": ("diagnostic metadata only",),
    }


def _compact_sorted_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (bool, int, float, str):
        return True
    if type(value) is list:
        return all(_primitive_only(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


def _payload_keys(value: object) -> set[str]:
    if type(value) is dict:
        keys: set[str] = set()
        for key, nested_value in value.items():
            keys.add(key)
            keys.update(_payload_keys(nested_value))
        return keys

    if type(value) is list:
        keys: set[str] = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


def _matching_field_terms(
    field_names: set[str],
    forbidden_terms: tuple[str, ...],
) -> list[str]:
    matches: list[str] = []
    for field_name in sorted(field_names):
        for term in forbidden_terms:
            if term in field_name.lower():
                matches.append(field_name)
                break

    return matches


def _matching_terms(text: str, forbidden_terms: tuple[str, ...]) -> list[str]:
    return [term for term in forbidden_terms if term in text]
