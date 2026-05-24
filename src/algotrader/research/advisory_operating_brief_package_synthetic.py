"""Synthetic advisory operating brief package preview builder."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_package_preview",
]

_PACKAGE_ID = "advisory-operating-brief-package:synthetic:2026-01-20"
_TITLE = "Synthetic advisory operating brief package"
_SUMMARY = "Advisory-only synthetic operating brief package content."
_AS_OF = "2026-01-20"


def build_synthetic_advisory_operating_brief_package_preview() -> (
    AdvisoryOperatingBriefPackage
):
    """Return the deterministic synthetic advisory package preview."""

    content_bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue(
            include_risk_authority=True,
        )
    )
    return build_advisory_operating_brief_package(
        package_id=_PACKAGE_ID,
        title=_TITLE,
        summary=_SUMMARY,
        as_of=_AS_OF,
        content_bundle=content_bundle,
    )
