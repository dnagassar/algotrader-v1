"""Metadata-only synthetic research replay result packages."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.replay import SyntheticReplaySnapshot
from algotrader.research.replay_metrics import (
    SyntheticReplaySummary,
    summarize_synthetic_replay_snapshot,
)

__all__ = [
    "SyntheticResearchResult",
    "build_synthetic_research_result",
]


@dataclass(frozen=True, slots=True)
class SyntheticResearchResult:
    """Combined synthetic replay snapshot and descriptive summary metadata."""

    snapshot: SyntheticReplaySnapshot
    summary: SyntheticReplaySummary

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot", _snapshot(self.snapshot))
        object.__setattr__(self, "summary", _summary(self.summary))

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible synthetic result metadata."""
        return {
            "snapshot": self.snapshot.to_dict(),
            "summary": self.summary.to_dict(),
        }


def build_synthetic_research_result(
    snapshot: SyntheticReplaySnapshot,
) -> SyntheticResearchResult:
    """Build a metadata-only result package from an existing replay snapshot."""

    checked_snapshot = _snapshot(snapshot)
    return SyntheticResearchResult(
        snapshot=checked_snapshot,
        summary=summarize_synthetic_replay_snapshot(checked_snapshot),
    )


def _snapshot(value: SyntheticReplaySnapshot) -> SyntheticReplaySnapshot:
    if not isinstance(value, SyntheticReplaySnapshot):
        raise ValidationError("snapshot must be a SyntheticReplaySnapshot.")

    return value


def _summary(value: SyntheticReplaySummary) -> SyntheticReplaySummary:
    if not isinstance(value, SyntheticReplaySummary):
        raise ValidationError("summary must be a SyntheticReplaySummary.")

    return value
