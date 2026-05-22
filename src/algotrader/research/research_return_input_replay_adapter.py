"""Adapter from return-input packages to synthetic replay snapshots."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.asof import AsofObservation
from algotrader.research.fixture_manifest import ResearchFixtureManifest
from algotrader.research.replay import SyntheticReplayPoint, SyntheticReplaySnapshot
from algotrader.research.research_return_input_package import ResearchReturnInputPackage
from algotrader.research.research_return_input_provenance import (
    build_research_return_input_provenance,
)

__all__ = [
    "build_synthetic_replay_snapshot_from_return_input_package",
]


def build_synthetic_replay_snapshot_from_return_input_package(
    package: ResearchReturnInputPackage,
) -> SyntheticReplaySnapshot:
    """Copy prepared package dates, close values, and returns into replay metadata.

    The target replay contract has no package field. The adapted manifest carries
    the snapshot id and fingerprint provenance, while its limitations describe
    the candidate availability metadata used to satisfy ``AsofObservation``.
    """

    checked_package = _package(package)
    source_snapshot = checked_package.snapshot
    available_points = tuple(
        SyntheticReplayPoint(
            observation=AsofObservation(
                observation_date=observation_date,
                available_after=observation_date,
            ),
            value=close_value,
        )
        for observation_date, close_value in zip(
            source_snapshot.observation_dates,
            source_snapshot.close_values,
        )
    )

    return SyntheticReplaySnapshot(
        manifest=_manifest(checked_package),
        asof_date=source_snapshot.observation_dates[-1],
        available_points=available_points,
        returns=source_snapshot.close_to_close_returns,
    )


def _package(value: ResearchReturnInputPackage) -> ResearchReturnInputPackage:
    if not isinstance(value, ResearchReturnInputPackage):
        raise ValidationError("package must be a ResearchReturnInputPackage.")

    return value


def _manifest(package: ResearchReturnInputPackage) -> ResearchFixtureManifest:
    source_snapshot = package.snapshot
    provenance = build_research_return_input_provenance(package)
    return ResearchFixtureManifest(
        fixture_id=provenance.manifest_fixture_id,
        fixture_kind="derived",
        description="Synthetic replay snapshot adapted from return input package.",
        source_name="return input package",
        source_type="synthetic",
        retrieval_date=None,
        data_start=source_snapshot.observation_dates[0],
        data_end=source_snapshot.observation_dates[-1],
        fields=(
            "observation_date",
            "prepared_close_value",
            "prepared_close_to_close_return",
        ),
        checksum=provenance.manifest_checksum,
        normal_pytest_eligible=True,
        redistribution_safe=True,
        limitations=(
            "manifest derived from return input package metadata",
            "available_after mirrors observation_date",
            "returns copied from package close_to_close_returns",
        ),
        non_claims=source_snapshot.non_claims,
    )
