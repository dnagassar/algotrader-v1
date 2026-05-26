"""Expected manifest fixtures for the SMA return pipeline export snapshot."""

from __future__ import annotations

import json

from algotrader.research.research_observation_manifest import (
    build_research_observation_manifest,
)
from tests.fixtures.sma_return_research_pipeline_observation_export import (
    expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict,
)

__all__ = [
    "expected_sma_return_research_pipeline_export_snapshot_manifest_dict",
    "expected_sma_return_research_pipeline_export_snapshot_manifest_json",
]

_OBSERVATION_NAME = "sma_return_research_pipeline_observation_export_snapshot"


def expected_sma_return_research_pipeline_export_snapshot_manifest_dict() -> (
    dict[str, object]
):
    """Return the expected metadata manifest for the SMA export snapshot."""

    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    return build_research_observation_manifest(
        ((_OBSERVATION_NAME, payload),)
    ).to_dict()


def expected_sma_return_research_pipeline_export_snapshot_manifest_json() -> str:
    """Return compact JSON for the expected SMA export snapshot manifest."""

    return json.dumps(
        expected_sma_return_research_pipeline_export_snapshot_manifest_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
