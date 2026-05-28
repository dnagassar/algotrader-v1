"""Synthetic advisory operating brief diagnostic issue fixture."""

from __future__ import annotations

import json

from algotrader.research.advisory_operating_brief_diagnostic_issue import (
    AdvisoryOperatingBriefDiagnosticIssue,
    build_advisory_operating_brief_diagnostic_issues,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_diagnostic_issues",
    "expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts",
    "expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts",
    "expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_json",
    "expected_synthetic_advisory_operating_brief_diagnostic_issue_json",
]


def build_synthetic_advisory_operating_brief_diagnostic_issues() -> (
    tuple[AdvisoryOperatingBriefDiagnosticIssue, ...]
):
    """Return deterministic diagnostic issues from the synthetic content bundle."""

    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    return build_advisory_operating_brief_diagnostic_issues(bundle)


def expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts() -> (
    list[dict[str, object]]
):
    """Return the synthetic diagnostic issue records as primitive metadata."""

    return [
        issue.to_dict()
        for issue in build_synthetic_advisory_operating_brief_diagnostic_issues()
    ]


def expected_synthetic_advisory_operating_brief_diagnostic_issue_json() -> str:
    """Return compact sorted-key JSON for the synthetic diagnostic issues."""

    payload = expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts()

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts() -> (
    list[dict[str, object]]
):
    """Return the synthetic diagnostic issue export snapshot."""

    return expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts()


def expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_json() -> (
    str
):
    """Return compact sorted-key JSON for the diagnostic issue export snapshot."""

    payload = (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_export_snapshot_dicts()
    )

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
