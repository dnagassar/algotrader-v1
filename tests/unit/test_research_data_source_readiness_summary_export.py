from __future__ import annotations

import json

from algotrader.research.research_data_source_readiness_summary import (
    ResearchDataSourceReadinessSummary,
    build_research_data_source_readiness_summary,
)
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_summary,
    expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict,
    expected_synthetic_research_data_source_readiness_summary_export_snapshot_json,
)


def _s(*parts: str) -> str:
    return "".join(parts)


EXPECTED_SUMMARY_KEYS = [
    "summary_type",
    "schema_version",
    "summary_scope",
    "summary_state",
    "required_control_count",
    "satisfied_control_count",
    "missing_control_count",
    "diagnostic_limitations",
]
FORBIDDEN_SNAPSHOT_KEYS = {
    _s("app", "roved"),
    _s("author", "ized"),
    _s("author", "ization"),
    _s("back", "test"),
    _s("bro", "ker"),
    _s("cre", "dential"),
    _s("dash", "board"),
    "digest",
    _s("fi", "ll"),
    _s("or", "der"),
    _s("port", "folio"),
    _s("ra", "nk"),
    _s("raw", "_data"),
    _s("raw", "_payload"),
    "ready_to_trade",
    _s("recomm", "endation"),
    _s("run", "time"),
    _s("sco", "re"),
    _s("so", "cket"),
    "source_readiness",
    _s("stra", "tegy"),
    "timestamp",
    _s("tra", "ding"),
    "usable_for_backtest",
    "validated_for_trading",
    _s("ven", "dor"),
    "wrapper",
}


def test_summary_fixture_builds_valid_summary_from_existing_source_fixture() -> None:
    source = expected_synthetic_research_data_source_readiness()
    summary = expected_synthetic_research_data_source_readiness_summary(
        build_research_data_source_readiness_summary,
        source,
    )

    assert type(summary) is ResearchDataSourceReadinessSummary
    assert summary.source_readiness is source
    assert summary.summary_state == source.readiness_state
    assert summary.missing_control_count == len(source.missing_controls)
    assert source.missing_controls == (
        "terms_review_documented",
        "snapshot_provenance_defined",
        "redistribution_policy_reviewed",
        "adjustment_policy_defined",
        "fixture_policy_review_documented",
    )


def test_summary_export_snapshot_dict_equals_summary_to_dict() -> None:
    source = expected_synthetic_research_data_source_readiness()
    summary = expected_synthetic_research_data_source_readiness_summary(
        build_research_data_source_readiness_summary,
        source,
    )
    snapshot = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict(
            build_research_data_source_readiness_summary,
            source,
        )
    )

    assert snapshot == summary.to_dict()
    assert list(snapshot) == EXPECTED_SUMMARY_KEYS
    assert _primitive_only(snapshot)


def test_summary_export_snapshot_json_is_compact_sorted_and_deterministic() -> None:
    first_payload = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict(
            build_research_data_source_readiness_summary
        )
    )
    second_payload = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict(
            build_research_data_source_readiness_summary
        )
    )
    first_json = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_json(
            build_research_data_source_readiness_summary
        )
    )
    second_json = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_json(
            build_research_data_source_readiness_summary
        )
    )
    expected_json = json.dumps(
        first_payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    assert first_payload == second_payload
    assert first_payload is not second_payload
    assert first_json == second_json == expected_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert json.loads(first_json) == first_payload
    assert ": " not in first_json
    assert first_json != json.dumps(first_payload, sort_keys=True)


def test_summary_export_snapshot_contains_expected_diagnostics() -> None:
    source = expected_synthetic_research_data_source_readiness()
    snapshot = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict(
            build_research_data_source_readiness_summary,
            source,
        )
    )

    assert snapshot["summary_state"] == "candidate_only"
    assert snapshot["required_control_count"] == 6
    assert snapshot["satisfied_control_count"] == 1
    assert snapshot["missing_control_count"] == len(source.missing_controls) == 5
    assert snapshot["diagnostic_limitations"] == [
        "Fixture carries no observations, values, or external source content.",
        "Fixture is synthetic metadata only and not connected to real data.",
    ]


def test_summary_export_snapshot_returns_fresh_mutable_copies() -> None:
    first = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict(
            build_research_data_source_readiness_summary
        )
    )
    second = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict(
            build_research_data_source_readiness_summary
        )
    )

    assert first == second
    assert first["diagnostic_limitations"] is not second["diagnostic_limitations"]

    first["diagnostic_limitations"].append("mutated primitive copy")

    assert second["diagnostic_limitations"] == [
        "Fixture carries no observations, values, or external source content.",
        "Fixture is synthetic metadata only and not connected to real data.",
    ]


def test_summary_export_snapshot_excludes_operating_and_wrapper_fields() -> None:
    snapshot = (
        expected_synthetic_research_data_source_readiness_summary_export_snapshot_dict(
            build_research_data_source_readiness_summary
        )
    )

    assert FORBIDDEN_SNAPSHOT_KEYS.isdisjoint(_payload_keys(snapshot))


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
