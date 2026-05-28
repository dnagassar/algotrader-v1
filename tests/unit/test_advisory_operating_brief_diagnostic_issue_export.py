from __future__ import annotations

import json

from algotrader.research.advisory_operating_brief_diagnostic_issue import (
    build_advisory_operating_brief_diagnostic_issues,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary,
)
from tests.fixtures.advisory_operating_brief_diagnostic_issue import (
    build_synthetic_advisory_operating_brief_diagnostic_issues,
    expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts,
    expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts,
    expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_json,
    expected_synthetic_advisory_operating_brief_diagnostic_issue_json,
)


EXPECTED_ISSUE_KEYS = [
    "source_branch",
    "issue_code",
    "issue_state",
    "diagnostic_message",
    "blocking_controls",
    "limitations",
]
EXPECTED_BRANCHES = [
    "research_data_source_readiness",
    "research_data_source_readiness_summary",
]
EXPECTED_MESSAGES = [
    "Readiness branch reports missing diagnostic controls.",
    "Readiness summary branch reports missing diagnostic controls.",
]
EXPECTED_BLOCKING_CONTROLS = [
    "terms_review_documented",
    "snapshot_provenance_defined",
    "redistribution_policy_reviewed",
    "adjustment_policy_defined",
    "fixture_policy_review_documented",
]
FORBIDDEN_SNAPSHOT_KEYS = {
    "allocation",
    "approval",
    "approved",
    "authorization",
    "authorized",
    "backtest",
    "broker",
    "created_at",
    "credential",
    "dashboard",
    "digest",
    "fill",
    "generated_at",
    "order",
    "portfolio",
    "priority",
    "rank",
    "ranking",
    "raw_data",
    "raw_payload",
    "recommendation",
    "runtime",
    "score",
    "severity",
    "socket",
    "timestamp",
    "usable_for_backtest",
    "validated_for_trading",
    "vendor",
    "wrapper",
}
FORBIDDEN_TEXT_TERMS = (
    "approval",
    "approved",
    "authorization",
    "authorized",
    "priority",
    "ranking",
    "ready_to_trade",
    "recommendation",
    "scoring",
    "severity",
    "validated_for_trading",
    "usable_for_backtest",
)


def test_fixture_builds_deterministic_issues_from_synthetic_bundle() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    direct_issues = build_advisory_operating_brief_diagnostic_issues(bundle)
    fixture_issues = build_synthetic_advisory_operating_brief_diagnostic_issues()

    assert fixture_issues == direct_issues
    assert [issue.source_branch for issue in fixture_issues] == EXPECTED_BRANCHES
    assert [issue.issue_code for issue in fixture_issues] == [
        "missing_diagnostic_controls",
        "missing_diagnostic_controls",
    ]
    assert [issue.issue_state for issue in fixture_issues] == [
        "candidate_only",
        "candidate_only",
    ]


def test_snapshot_dicts_equal_each_issue_to_dict_payload() -> None:
    issues = build_synthetic_advisory_operating_brief_diagnostic_issues()
    snapshot = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )

    assert snapshot == [issue.to_dict() for issue in issues]
    assert snapshot == expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts()
    assert [list(issue_payload) for issue_payload in snapshot] == [
        EXPECTED_ISSUE_KEYS,
        EXPECTED_ISSUE_KEYS,
    ]


def test_snapshot_json_is_compact_sorted_and_deterministic() -> None:
    payload = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )
    first_json = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_json()
    )
    second_json = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_json()
    )
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert first_json == second_json == expected_json
    assert first_json == expected_synthetic_advisory_operating_brief_diagnostic_issue_json()
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert json.loads(first_json) == payload
    assert "\n" not in first_json
    assert ": " not in first_json
    assert first_json != json.dumps(payload, sort_keys=True)


def test_snapshot_contains_expected_diagnostic_issue_fields() -> None:
    snapshot = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )

    assert len(snapshot) == 2
    assert [issue["source_branch"] for issue in snapshot] == EXPECTED_BRANCHES
    assert [issue["issue_code"] for issue in snapshot] == [
        "missing_diagnostic_controls",
        "missing_diagnostic_controls",
    ]
    assert [issue["issue_state"] for issue in snapshot] == [
        "candidate_only",
        "candidate_only",
    ]
    assert [issue["diagnostic_message"] for issue in snapshot] == EXPECTED_MESSAGES
    assert [issue["blocking_controls"] for issue in snapshot] == [
        EXPECTED_BLOCKING_CONTROLS,
        EXPECTED_BLOCKING_CONTROLS,
    ]
    assert snapshot[0]["limitations"] == [
        "Fixture is synthetic metadata only and not connected to real data.",
        "Fixture carries no observations, values, or external source content.",
    ]
    assert snapshot[1]["limitations"] == [
        "Fixture carries no observations, values, or external source content.",
        "Fixture is synthetic metadata only and not connected to real data.",
    ]


def test_snapshot_preserves_builder_order_without_severity_or_priority_ranking() -> (
    None
):
    snapshot = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )

    assert [issue["source_branch"] for issue in snapshot] == EXPECTED_BRANCHES
    assert [issue["diagnostic_message"] for issue in snapshot] == EXPECTED_MESSAGES
    assert "severity" not in _payload_keys(snapshot)
    assert "priority" not in _payload_keys(snapshot)
    assert "rank" not in _payload_keys(snapshot)


def test_snapshot_excludes_raw_timestamps_digest_wrappers_and_operating_fields() -> (
    None
):
    snapshot = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )
    snapshot_keys = _payload_keys(snapshot)
    snapshot_text = json.dumps(snapshot, sort_keys=True).lower()

    assert FORBIDDEN_SNAPSHOT_KEYS.isdisjoint(snapshot_keys)
    assert all(term not in snapshot_text for term in FORBIDDEN_TEXT_TERMS)


def test_repeated_fixture_builds_and_snapshots_are_equal() -> None:
    first_issues = build_synthetic_advisory_operating_brief_diagnostic_issues()
    second_issues = build_synthetic_advisory_operating_brief_diagnostic_issues()
    first_snapshot = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )
    second_snapshot = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )

    assert first_issues == second_issues
    assert first_issues is not second_issues
    assert first_snapshot == second_snapshot
    assert first_snapshot is not second_snapshot


def test_snapshot_payloads_are_primitive_round_trippable_fresh_copies() -> None:
    first = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )
    second = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )
    compact_json = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_json()
    )

    assert _primitive_only(first)
    assert json.loads(compact_json) == first
    assert first[0]["blocking_controls"] is not second[0]["blocking_controls"]
    assert first[0]["limitations"] is not second[0]["limitations"]

    first[0]["blocking_controls"].append("mutated primitive copy")
    first[0]["limitations"].append("mutated primitive copy")

    assert second[0]["blocking_controls"] == EXPECTED_BLOCKING_CONTROLS
    assert second[0]["limitations"] == [
        "Fixture is synthetic metadata only and not connected to real data.",
        "Fixture carries no observations, values, or external source content.",
    ]


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
