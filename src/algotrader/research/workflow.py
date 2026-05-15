"""Thin synthetic research workflow composition helper."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from algotrader.research.fixture_manifest import ResearchFixtureManifest
from algotrader.research.replay import (
    SyntheticReplayPoint,
    build_synthetic_replay_snapshot,
)
from algotrader.research.replay_result import (
    SyntheticResearchResult,
    build_synthetic_research_result,
)

__all__ = [
    "build_synthetic_research_workflow_result",
]


def build_synthetic_research_workflow_result(
    manifest: ResearchFixtureManifest,
    points: Iterable[SyntheticReplayPoint],
    asof_date: date,
) -> SyntheticResearchResult:
    """Build a complete metadata-only result from synthetic replay inputs."""

    snapshot = build_synthetic_replay_snapshot(
        manifest=manifest,
        points=points,
        asof_date=asof_date,
    )
    return build_synthetic_research_result(snapshot)
