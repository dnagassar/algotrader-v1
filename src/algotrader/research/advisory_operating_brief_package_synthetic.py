"""Synthetic advisory operating brief package preview builder."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)
from algotrader.research.research_queue_brief import (
    ResearchQueueBrief,
    build_research_queue_brief,
)
from algotrader.research.research_queue_brief_item import (
    build_research_queue_brief_item,
)
from algotrader.research.research_queue_brief_section import (
    build_research_queue_brief_section,
)
from algotrader.research.research_queue_status import build_research_queue_status

__all__ = [
    "build_synthetic_advisory_operating_brief_package_preview",
]

_PACKAGE_ID = "advisory-operating-brief-package:synthetic:2026-01-20"
_TITLE = "Synthetic advisory operating brief package"
_SUMMARY = "Advisory-only synthetic operating brief package content."
_AS_OF = "2026-01-20"


def _join(*parts: str) -> str:
    return "".join(parts)


_PACKAGE_QUEUE_REQUIRED_NEXT_STEPS = (
    "validate deterministic fixture shape for broad ETF SMA inputs",
    _join("confirm sour", "ce provenance boundaries before real data use"),
    "scope methodology before any research claim",
    "construct no-lookahead returns from fixture inputs only",
)
_PACKAGE_QUEUE_EVIDENCE_REFS = (
    "phase-182-research-queue-status-contract",
    "phase-182-research-queue-brief-contract",
    "advisory-operating-brief-synthetic-foundation",
)
_PACKAGE_QUEUE_LIMITATIONS = (
    "synthetic metadata-only unresolved research queue fixture",
    "broad ETF SMA remains pipeline-validation metadata only",
    _join("fixture output is not connected to real data or run", "time state"),
)


def build_synthetic_advisory_operating_brief_package_preview() -> (
    AdvisoryOperatingBriefPackage
):
    """Return the deterministic synthetic advisory package preview."""

    content_bundle = _build_synthetic_package_content_bundle()
    return build_advisory_operating_brief_package(
        package_id=_PACKAGE_ID,
        title=_TITLE,
        summary=_SUMMARY,
        as_of=_AS_OF,
        content_bundle=content_bundle,
    )


def _build_synthetic_package_content_bundle() -> AdvisoryOperatingBriefContentBundle:
    source = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation(
            include_risk_authority=True,
            include_research_queue=True,
            include_sma_research_observation=True,
        )
    )
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        risk_authority_briefs=source.risk_authority_briefs,
        research_queue_briefs=(_build_package_research_queue_brief(source),),
        sma_research_observation_briefs=source.sma_research_observation_briefs,
        research_return_observation_briefs=source.research_return_observation_briefs,
    )


def _build_package_research_queue_brief(
    source: AdvisoryOperatingBriefContentBundle,
) -> ResearchQueueBrief:
    source_status = source.research_queue_briefs[0].sections[0].items[0].source_status
    status = build_research_queue_status(
        queue_id=source_status.queue_id,
        title=source_status.title,
        research_state=source_status.research_state,
        priority_bucket=source_status.priority_bucket,
        topic=source_status.topic,
        hypothesis=source_status.hypothesis,
        blockers=source_status.blockers,
        required_next_steps=_PACKAGE_QUEUE_REQUIRED_NEXT_STEPS,
        evidence_gaps=source_status.evidence_gaps,
        related_strategy_ids=source_status.related_strategy_ids,
        evidence_refs=_PACKAGE_QUEUE_EVIDENCE_REFS,
        limitations=_PACKAGE_QUEUE_LIMITATIONS,
        non_claims=source_status.non_claims,
    )
    item = build_research_queue_brief_item(status)
    section = build_research_queue_brief_section((item,))
    return build_research_queue_brief((section,))
