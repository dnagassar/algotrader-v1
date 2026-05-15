"""Descriptive metrics for synthetic replay snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.replay import SyntheticReplaySnapshot

__all__ = [
    "SyntheticReplaySummary",
    "summarize_synthetic_replay_snapshot",
]


@dataclass(frozen=True, slots=True)
class SyntheticReplaySummary:
    """Small descriptive summary for synthetic replay snapshot metadata."""

    point_count: int
    return_count: int
    starting_value: Decimal | None
    ending_value: Decimal | None
    cumulative_simple_return: Decimal | None
    min_return: Decimal | None
    max_return: Decimal | None
    mean_return: Decimal | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "point_count", _count(self.point_count, "point_count"))
        object.__setattr__(
            self,
            "return_count",
            _count(self.return_count, "return_count"),
        )
        object.__setattr__(
            self,
            "starting_value",
            _optional_decimal(self.starting_value, "starting_value"),
        )
        object.__setattr__(
            self,
            "ending_value",
            _optional_decimal(self.ending_value, "ending_value"),
        )
        object.__setattr__(
            self,
            "cumulative_simple_return",
            _optional_decimal(
                self.cumulative_simple_return,
                "cumulative_simple_return",
            ),
        )
        object.__setattr__(
            self,
            "min_return",
            _optional_decimal(self.min_return, "min_return"),
        )
        object.__setattr__(
            self,
            "max_return",
            _optional_decimal(self.max_return, "max_return"),
        )
        object.__setattr__(
            self,
            "mean_return",
            _optional_decimal(self.mean_return, "mean_return"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible summary metadata."""
        return {
            "point_count": self.point_count,
            "return_count": self.return_count,
            "starting_value": _serialize_optional_decimal(self.starting_value),
            "ending_value": _serialize_optional_decimal(self.ending_value),
            "cumulative_simple_return": _serialize_optional_decimal(
                self.cumulative_simple_return
            ),
            "min_return": _serialize_optional_decimal(self.min_return),
            "max_return": _serialize_optional_decimal(self.max_return),
            "mean_return": _serialize_optional_decimal(self.mean_return),
        }


def summarize_synthetic_replay_snapshot(
    snapshot: SyntheticReplaySnapshot,
) -> SyntheticReplaySummary:
    """Summarize an existing synthetic replay snapshot descriptively."""

    checked_snapshot = _snapshot(snapshot)
    available_points = checked_snapshot.available_points
    returns = checked_snapshot.returns
    point_count = len(available_points)
    return_count = len(returns)

    starting_value = available_points[0].value if available_points else None
    ending_value = available_points[-1].value if available_points else None

    cumulative_simple_return: Decimal | None = None
    min_return: Decimal | None = None
    max_return: Decimal | None = None
    mean_return: Decimal | None = None

    if returns:
        if starting_value is None or ending_value is None:
            raise ValidationError("returns require available point values.")
        if starting_value == Decimal("0"):
            raise ValidationError(
                "starting_value must be non-zero when returns are present."
            )
        cumulative_simple_return = (ending_value / starting_value) - Decimal("1")
        min_return = min(returns)
        max_return = max(returns)
        mean_return = sum(returns, Decimal("0")) / Decimal(return_count)

    return SyntheticReplaySummary(
        point_count=point_count,
        return_count=return_count,
        starting_value=starting_value,
        ending_value=ending_value,
        cumulative_simple_return=cumulative_simple_return,
        min_return=min_return,
        max_return=max_return,
        mean_return=mean_return,
    )


def _snapshot(value: SyntheticReplaySnapshot) -> SyntheticReplaySnapshot:
    if not isinstance(value, SyntheticReplaySnapshot):
        raise ValidationError("snapshot must be a SyntheticReplaySnapshot.")

    return value


def _count(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")

    return value


def _optional_decimal(value: Decimal | None, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal or None.")

    return value


def _serialize_optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
