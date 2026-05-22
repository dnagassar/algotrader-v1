"""Exact arithmetic checks for prepared research return input snapshots."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.return_construction import close_to_close_returns

__all__ = [
    "validate_research_return_input_snapshot_consistency",
]


def validate_research_return_input_snapshot_consistency(
    snapshot: ResearchReturnInputSnapshot,
) -> ResearchReturnInputSnapshot:
    """Validate exact arithmetic consistency for an already-prepared snapshot.

    The check introduces no rounding, tolerance, inference, or approval; it
    only compares stored returns against the existing return mechanics.
    """

    if not isinstance(snapshot, ResearchReturnInputSnapshot):
        raise ValidationError("snapshot must be a ResearchReturnInputSnapshot.")

    expected_returns = close_to_close_returns(snapshot.close_values)
    if snapshot.close_to_close_returns != expected_returns:
        raise ValidationError(
            "close_to_close_returns must match close_values arithmetic."
        )

    return snapshot
