"""Synthetic advisory operating brief package fixture."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_package",
    "expected_synthetic_advisory_operating_brief_package_dict",
]

_PACKAGE_ID = "advisory-operating-brief-package:synthetic:2026-01-20"
_TITLE = "Synthetic advisory operating brief package"
_SUMMARY = "Advisory-only synthetic operating brief package content."
_AS_OF = "2026-01-20"


def build_synthetic_advisory_operating_brief_package() -> (
    AdvisoryOperatingBriefPackage
):
    """Return the deterministic synthetic advisory operating brief package."""

    content_bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    )
    return build_advisory_operating_brief_package(
        package_id=_PACKAGE_ID,
        title=_TITLE,
        summary=_SUMMARY,
        as_of=_AS_OF,
        content_bundle=content_bundle,
    )


def expected_synthetic_advisory_operating_brief_package_dict() -> dict[str, object]:
    """Return the exact primitive package payload emitted by the fixture."""

    package = build_synthetic_advisory_operating_brief_package()
    return package.to_dict()
