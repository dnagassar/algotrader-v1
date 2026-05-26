"""Generic primitive export snapshot for research observation manifests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from algotrader.research.research_observation_manifest import (
    build_research_observation_manifest,
)

__all__ = [
    "export_research_observation_manifest_snapshot",
]


def export_research_observation_manifest_snapshot(
    entries: Iterable[object] | Mapping[str, object],
) -> dict[str, object]:
    """Return the generic manifest primitive snapshot for named payload entries."""

    manifest = build_research_observation_manifest(entries)
    return manifest.to_dict()
