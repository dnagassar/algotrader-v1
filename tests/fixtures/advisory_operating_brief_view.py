"""Synthetic advisory operating brief view fixture."""

from __future__ import annotations

import json

from algotrader.research.advisory_operating_brief_view import (
    AdvisoryOperatingBriefView,
    build_advisory_operating_brief_view,
)
from tests.fixtures.advisory_operating_brief_section import (
    build_synthetic_advisory_operating_brief_sections,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_view",
    "expected_synthetic_advisory_operating_brief_view_dict",
    "expected_synthetic_advisory_operating_brief_view_export_snapshot_dict",
    "expected_synthetic_advisory_operating_brief_view_export_snapshot_json",
    "expected_synthetic_advisory_operating_brief_view_json",
]


def build_synthetic_advisory_operating_brief_view() -> (
    AdvisoryOperatingBriefView
):
    """Return a deterministic view from synthetic advisory section records."""

    sections = build_synthetic_advisory_operating_brief_sections()

    return build_advisory_operating_brief_view(sections)


def expected_synthetic_advisory_operating_brief_view_dict() -> (
    dict[str, object]
):
    """Return the synthetic advisory view as primitive metadata."""

    view = build_synthetic_advisory_operating_brief_view()

    return view.to_dict()


def expected_synthetic_advisory_operating_brief_view_json() -> str:
    """Return compact sorted-key JSON for the synthetic advisory view."""

    payload = expected_synthetic_advisory_operating_brief_view_dict()

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def expected_synthetic_advisory_operating_brief_view_export_snapshot_dict() -> (
    dict[str, object]
):
    """Return the synthetic advisory view export snapshot."""

    return expected_synthetic_advisory_operating_brief_view_dict()


def expected_synthetic_advisory_operating_brief_view_export_snapshot_json() -> (
    str
):
    """Return compact sorted-key JSON for the advisory view export snapshot."""

    payload = expected_synthetic_advisory_operating_brief_view_export_snapshot_dict()

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
