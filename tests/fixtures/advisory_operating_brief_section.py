"""Synthetic advisory operating brief section fixture."""

from __future__ import annotations

import json

from algotrader.research.advisory_operating_brief_content_bundle import (
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_section import (
    AdvisoryOperatingBriefSection,
    build_advisory_operating_brief_sections,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary,
)
from tests.fixtures.advisory_operating_brief_diagnostic_issue import (
    build_synthetic_advisory_operating_brief_diagnostic_issues,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_sections",
    "expected_synthetic_advisory_operating_brief_section_dicts",
    "expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts",
    "expected_synthetic_advisory_operating_brief_section_export_snapshot_json",
    "expected_synthetic_advisory_operating_brief_section_json",
]


def build_synthetic_advisory_operating_brief_sections() -> (
    tuple[AdvisoryOperatingBriefSection, ...]
):
    """Return deterministic section records from the synthetic content bundle."""

    source = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    issues = build_synthetic_advisory_operating_brief_diagnostic_issues()
    bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        research_data_source_readiness=source.research_data_source_readiness,
        research_data_source_readiness_summaries=(
            source.research_data_source_readiness_summaries
        ),
        diagnostic_issues=issues,
    )

    return build_advisory_operating_brief_sections(bundle)


def expected_synthetic_advisory_operating_brief_section_dicts() -> (
    list[dict[str, object]]
):
    """Return the synthetic section records as primitive metadata."""

    return [
        section.to_dict()
        for section in build_synthetic_advisory_operating_brief_sections()
    ]


def expected_synthetic_advisory_operating_brief_section_json() -> str:
    """Return compact sorted-key JSON for the synthetic section records."""

    payload = expected_synthetic_advisory_operating_brief_section_dicts()

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts() -> (
    list[dict[str, object]]
):
    """Return the synthetic section export snapshot."""

    return expected_synthetic_advisory_operating_brief_section_dicts()


def expected_synthetic_advisory_operating_brief_section_export_snapshot_json() -> (
    str
):
    """Return compact sorted-key JSON for the section export snapshot."""

    payload = (
        expected_synthetic_advisory_operating_brief_section_export_snapshot_dicts()
    )

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
