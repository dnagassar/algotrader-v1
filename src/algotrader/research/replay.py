"""Metadata-only synthetic research replay snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.asof import AsofObservation, iter_asof_available
from algotrader.research.fixture_manifest import ResearchFixtureManifest
from algotrader.research.return_construction import close_to_close_returns

__all__ = [
    "SyntheticReplayPoint",
    "SyntheticReplaySnapshot",
    "build_synthetic_replay_snapshot",
]


@dataclass(frozen=True, slots=True)
class SyntheticReplayPoint:
    """One synthetic observation/value pair for replay metadata."""

    observation: AsofObservation
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.observation, AsofObservation):
            raise ValidationError("observation must be an AsofObservation.")
        if not isinstance(self.value, Decimal):
            raise ValidationError("value must be a Decimal.")


@dataclass(frozen=True, slots=True)
class SyntheticReplaySnapshot:
    """Metadata-only synthetic replay snapshot for one as-of date."""

    manifest: ResearchFixtureManifest
    asof_date: date
    available_points: tuple[SyntheticReplayPoint, ...]
    returns: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest", _manifest(self.manifest))
        object.__setattr__(self, "asof_date", _plain_date(self.asof_date, "asof_date"))
        object.__setattr__(
            self,
            "available_points",
            _point_sequence(self.available_points, "available_points"),
        )
        object.__setattr__(self, "returns", _decimal_sequence(self.returns, "returns"))

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible replay metadata."""
        return {
            "manifest": self.manifest.to_dict(),
            "asof_date": _serialize_plain_date(self.asof_date, "asof_date"),
            "available_points": [
                {
                    "observation_date": _serialize_plain_date(
                        point.observation.observation_date,
                        "observation_date",
                    ),
                    "available_after": _serialize_plain_date(
                        point.observation.available_after,
                        "available_after",
                    ),
                    "value": str(point.value),
                }
                for point in self.available_points
            ],
            "returns": [str(value) for value in self.returns],
        }


def build_synthetic_replay_snapshot(
    manifest: ResearchFixtureManifest,
    points: Iterable[SyntheticReplayPoint],
    asof_date: date,
) -> SyntheticReplaySnapshot:
    """Build a deterministic metadata-only snapshot from synthetic inputs."""

    checked_manifest = _manifest(manifest)
    checked_asof_date = _plain_date(asof_date, "asof_date")
    point_items = _point_sequence(points, "points")

    observations = tuple(point.observation for point in point_items)
    available_observations = iter_asof_available(observations, checked_asof_date)
    available_observation_ids = frozenset(
        id(observation) for observation in available_observations
    )
    available_points = tuple(
        point
        for point in point_items
        if id(point.observation) in available_observation_ids
    )
    values = tuple(point.value for point in available_points)
    returns: tuple[Decimal, ...]
    if len(values) < 2:
        returns = ()
    else:
        returns = close_to_close_returns(values)

    return SyntheticReplaySnapshot(
        manifest=checked_manifest,
        asof_date=checked_asof_date,
        available_points=available_points,
        returns=returns,
    )


def _manifest(value: ResearchFixtureManifest) -> ResearchFixtureManifest:
    if not isinstance(value, ResearchFixtureManifest):
        raise ValidationError("manifest must be a ResearchFixtureManifest.")

    return value


def _plain_date(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")

    return value


def _point_sequence(
    values: Iterable[SyntheticReplayPoint],
    field_name: str,
) -> tuple[SyntheticReplayPoint, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{field_name} must be an iterable of SyntheticReplayPoint.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of SyntheticReplayPoint."
        ) from exc

    for index, value in enumerate(items):
        if not isinstance(value, SyntheticReplayPoint):
            raise ValidationError(
                f"{field_name}[{index}] must be a SyntheticReplayPoint."
            )

    return items


def _decimal_sequence(
    values: Iterable[Decimal],
    field_name: str,
) -> tuple[Decimal, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{field_name} must be an iterable of Decimal values.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of Decimal values."
        ) from exc

    for index, value in enumerate(items):
        if not isinstance(value, Decimal):
            raise ValidationError(f"{field_name}[{index}] must be a Decimal.")

    return items


def _serialize_plain_date(value: date, field_name: str) -> str:
    plain_date = _plain_date(value, field_name)
    return plain_date.isoformat()
