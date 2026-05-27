import json

from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_dict,
    expected_synthetic_research_data_source_readiness_export_snapshot_dict,
    expected_synthetic_research_data_source_readiness_export_snapshot_json,
    expected_synthetic_research_data_source_readiness_json,
)


EXPECTED_KEYS = [
    "contract_type",
    "schema_version",
    "source_id",
    "source_name",
    "asset_class_scope",
    "intended_use",
    "readiness_state",
    "required_controls",
    "satisfied_controls",
    "missing_controls",
    "evidence_refs",
    "limitations",
    "non_claims",
]

EXPECTED_MISSING_CONTROLS = [
    "terms_review_documented",
    "snapshot_provenance_defined",
    "redistribution_policy_reviewed",
    "adjustment_policy_defined",
    "fixture_policy_review_documented",
]

LIST_KEYS = (
    "asset_class_scope",
    "required_controls",
    "satisfied_controls",
    "missing_controls",
    "evidence_refs",
    "limitations",
    "non_claims",
)

EXTRA_EXPORT_KEYS = {
    "snapshot_type",
    "snapshot_id",
    "payload_digest_sha256",
    "created_at",
    "generated_at",
    "timestamp",
    "as_of",
    "source_url",
    "raw_payload",
}


def test_export_snapshot_dict_is_exact_fixture_to_dict_payload() -> None:
    readiness = expected_synthetic_research_data_source_readiness()
    payload = expected_synthetic_research_data_source_readiness_export_snapshot_dict()

    assert payload == readiness.to_dict()
    assert payload == expected_synthetic_research_data_source_readiness_dict()
    assert list(payload) == EXPECTED_KEYS


def test_export_snapshot_json_is_existing_compact_sorted_json() -> None:
    payload = expected_synthetic_research_data_source_readiness_export_snapshot_dict()
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert (
        expected_synthetic_research_data_source_readiness_export_snapshot_json()
        == expected_json
    )
    assert (
        expected_synthetic_research_data_source_readiness_export_snapshot_json()
        == expected_synthetic_research_data_source_readiness_json()
    )


def test_export_snapshot_json_is_byte_for_byte_deterministic() -> None:
    first = expected_synthetic_research_data_source_readiness_export_snapshot_json()
    second = expected_synthetic_research_data_source_readiness_export_snapshot_json()

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")
    assert "\n" not in first
    assert '": ' not in first
    assert ', "' not in first


def test_export_snapshot_payload_is_primitive_json_round_trippable() -> None:
    payload = expected_synthetic_research_data_source_readiness_export_snapshot_dict()
    compact_json = (
        expected_synthetic_research_data_source_readiness_export_snapshot_json()
    )

    assert _primitive_only(payload)
    assert json.loads(compact_json) == payload
    assert json.dumps(
        json.loads(compact_json),
        sort_keys=True,
        separators=(",", ":"),
    ) == compact_json


def test_export_snapshot_returns_fresh_equal_payloads() -> None:
    first = expected_synthetic_research_data_source_readiness_export_snapshot_dict()
    second = expected_synthetic_research_data_source_readiness_export_snapshot_dict()

    assert first == second
    assert first is not second
    for key in LIST_KEYS:
        assert type(first[key]) is list
        assert type(second[key]) is list
        assert first[key] is not second[key]


def test_export_snapshot_preserves_builder_computed_missing_controls() -> None:
    readiness = expected_synthetic_research_data_source_readiness()
    payload = expected_synthetic_research_data_source_readiness_export_snapshot_dict()

    assert readiness.missing_controls == tuple(EXPECTED_MISSING_CONTROLS)
    assert payload["missing_controls"] == list(readiness.missing_controls)
    assert payload["missing_controls"] == EXPECTED_MISSING_CONTROLS


def test_export_snapshot_adds_no_wrapper_clock_digest_or_raw_fields() -> None:
    payload = expected_synthetic_research_data_source_readiness_export_snapshot_dict()

    assert set(payload).isdisjoint(EXTRA_EXPORT_KEYS)


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
