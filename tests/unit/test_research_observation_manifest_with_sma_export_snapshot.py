from __future__ import annotations

import hashlib
import json

from algotrader.research.research_observation_manifest import (
    build_research_observation_manifest,
)
from tests.fixtures.research_observation_manifest import (
    expected_sma_return_research_pipeline_export_snapshot_manifest_dict,
    expected_sma_return_research_pipeline_export_snapshot_manifest_json,
)
from tests.fixtures.sma_return_research_pipeline_observation_export import (
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict,
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json,
)


OBSERVATION_NAME = "sma_return_research_pipeline_observation_export_snapshot"


def test_sma_export_snapshot_manifest_fixture_builds_one_stable_entry() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    entry = manifest["entries"][0]

    assert manifest["manifest_type"] == "research_observation_manifest"
    assert manifest["schema_version"] == "1"
    assert manifest["advisory_scope"] == "research_observation_metadata_only"
    assert manifest["entry_count"] == 1
    assert len(manifest["entries"]) == 1
    assert entry["observation_name"] == OBSERVATION_NAME
    assert entry["observation_type"] == payload["observation_type"]
    assert entry["payload_key_count"] == len(payload)


def test_sma_export_snapshot_manifest_digest_matches_payload_hash() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    entry = manifest["entries"][0]

    assert entry["payload_digest_sha256"] == _payload_digest(payload)


def test_sma_manifest_fixture_matches_generic_manifest_to_dict_output() -> None:
    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    expected_manifest = build_research_observation_manifest(
        ((OBSERVATION_NAME, payload),)
    )

    assert (
        expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
        == expected_manifest.to_dict()
    )


def test_sma_manifest_fixture_json_is_compact_sorted_and_round_trippable() -> None:
    manifest = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    manifest_json = (
        expected_sma_return_research_pipeline_export_snapshot_manifest_json()
    )

    assert manifest_json == _compact_json(manifest)
    assert json.loads(manifest_json) == manifest
    assert _primitive_only(manifest)


def test_sma_manifest_fixture_repeated_calls_are_deterministic() -> None:
    first = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    second = expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    first_json = (
        expected_sma_return_research_pipeline_export_snapshot_manifest_json()
    )
    second_json = (
        expected_sma_return_research_pipeline_export_snapshot_manifest_json()
    )

    assert first == second
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_sma_export_snapshot_expected_payload_remains_unchanged() -> None:
    before = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    before_json = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json()
    )

    expected_sma_return_research_pipeline_export_snapshot_manifest_dict()
    expected_sma_return_research_pipeline_export_snapshot_manifest_json()

    after = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    after_json = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json()
    )

    assert before == after
    assert before_json == after_json
    assert before_json == _compact_json(before)
    assert json.loads(before_json) == before


def _payload_digest(payload: dict[str, object]) -> str:
    serialized = _compact_json(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool, float):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False
