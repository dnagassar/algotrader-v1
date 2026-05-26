from __future__ import annotations

import hashlib
import json

from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)
from algotrader.research.research_observation_manifest import (
    ResearchObservationManifest,
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
