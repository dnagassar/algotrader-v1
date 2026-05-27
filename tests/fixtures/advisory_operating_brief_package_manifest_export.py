"""Expected payload fixture for the advisory package manifest export."""

from __future__ import annotations

import json

from algotrader.research.advisory_operating_brief_package_manifest_export import (
    export_advisory_operating_brief_package_research_observation_manifest,
)
from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)

__all__ = [
    "expected_synthetic_advisory_operating_brief_package_manifest_export_dict",
    "expected_synthetic_advisory_operating_brief_package_manifest_export_json",
]


def expected_synthetic_advisory_operating_brief_package_manifest_export_dict() -> (
    dict[str, object]
):
    """Return the exact primitive package manifest export payload."""

    package = build_synthetic_advisory_operating_brief_package_preview()
    return export_advisory_operating_brief_package_research_observation_manifest(
        package
    )


def expected_synthetic_advisory_operating_brief_package_manifest_export_json() -> (
    str
):
    """Return compact JSON for the expected package manifest export payload."""

    payload = (
        expected_synthetic_advisory_operating_brief_package_manifest_export_dict()
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
