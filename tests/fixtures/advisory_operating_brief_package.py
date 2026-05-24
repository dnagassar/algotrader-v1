"""Synthetic advisory operating brief package fixture."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_package",
    "expected_synthetic_advisory_operating_brief_package_dict",
]

def build_synthetic_advisory_operating_brief_package() -> (
    AdvisoryOperatingBriefPackage
):
    """Return the deterministic synthetic advisory operating brief package."""

    return build_synthetic_advisory_operating_brief_package_preview()


def expected_synthetic_advisory_operating_brief_package_dict() -> dict[str, object]:
    """Return the exact primitive package payload emitted by the fixture."""

    package = build_synthetic_advisory_operating_brief_package()
    return package.to_dict()
