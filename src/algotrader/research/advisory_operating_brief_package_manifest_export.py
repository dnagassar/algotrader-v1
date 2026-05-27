"""Package-level research observation manifest export helper."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)

__all__ = [
    "export_advisory_operating_brief_package_research_observation_manifest",
]


def export_advisory_operating_brief_package_research_observation_manifest(
    package: AdvisoryOperatingBriefPackage,
) -> dict[str, object]:
    """Return the existing package manifest primitive payload."""

    if type(package) is not AdvisoryOperatingBriefPackage:
        raise ValidationError(
            "package must be exactly an AdvisoryOperatingBriefPackage."
        )

    manifest = package.research_observation_manifest
    if manifest is None:
        raise ValidationError(
            "package.research_observation_manifest must be present."
        )

    return manifest.to_dict()
