"""Expected payload fixtures for the SMA return pipeline export snapshot."""

from __future__ import annotations

import json

from tests.fixtures.sma_return_research_pipeline_observation import (
    expected_synthetic_sma_return_research_pipeline_observation_dict,
)

__all__ = [
    "expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict",
    "expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json",
]


def expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict() -> (
    dict[str, object]
):
    """Return the expected primitive Phase 252 export snapshot payload."""

    return expected_synthetic_sma_return_research_pipeline_observation_dict()


def expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_json() -> (
    str
):
    """Return compact JSON for the expected Phase 252 export snapshot payload."""

    payload = (
        expected_synthetic_sma_return_research_pipeline_observation_export_snapshot_dict()
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
