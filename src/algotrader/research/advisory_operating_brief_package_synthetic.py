"""Synthetic advisory operating brief package preview builder."""

from __future__ import annotations

from decimal import Decimal

from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation,
)
from algotrader.research.advisory_operating_brief_diagnostic_issue import (
    build_advisory_operating_brief_diagnostic_issues,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_section import (
    build_advisory_operating_brief_sections,
)
from algotrader.research.advisory_operating_brief_view import (
    build_advisory_operating_brief_view,
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
from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
    build_research_data_source_readiness,
)
from algotrader.research.research_data_source_readiness_summary import (
    ResearchDataSourceReadinessSummary,
    build_research_data_source_readiness_summary,
)
from algotrader.research.research_return_observation import (
    ResearchReturnPricePoint,
    ResearchReturnSeriesObservation,
    build_research_return_series_observation,
)
from algotrader.research.research_observation_manifest import (
    build_research_observation_manifest,
)
from algotrader.research.sma_conditional_return_selection_observation import (
    build_sma_conditional_return_selection_observation,
)
from algotrader.research.sma_conditional_return_selection_summary_observation import (
    build_sma_conditional_return_selection_summary_observation,
)
from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_return_alignment_observation import (
    build_sma_return_alignment_observation,
)
from algotrader.research.sma_return_alignment_summary_observation import (
    build_sma_return_alignment_summary_observation,
)
from algotrader.research.sma_return_research_pipeline_observation import (
    SmaReturnResearchPipelineObservation,
    build_sma_return_research_pipeline_observation,
)
from algotrader.research.sma_selected_source_return_series_observation import (
    build_sma_selected_source_return_series_observation,
)
from algotrader.research.sma_selected_source_return_summary_observation import (
    build_sma_selected_source_return_summary_observation,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_package_preview",
]

_PACKAGE_ID = "advisory-operating-brief-package:synthetic:2026-01-20"
_TITLE = "Synthetic advisory operating brief package"
_SUMMARY = "Advisory-only synthetic operating brief package content."
_AS_OF = "2026-01-20"


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


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
_SMA_RETURN_PIPELINE_SYMBOL = "SYNTH_ETF"
_SMA_RETURN_PIPELINE_AS_OF = "2026-01-20"
_SMA_RETURN_PIPELINE_WINDOW = 2
_SMA_RETURN_PIPELINE_SMA_LIMITATIONS = (
    "synthetic SMA states for alignment fixture only",
    "fixed as-of samples exercise no-lookahead alignment",
)
_SMA_RETURN_PIPELINE_RETURN_LIMITATIONS = (
    "synthetic broad ETF close series for return mechanics only",
    "fixed close samples with later samples ignored by the builder",
    "candidate-only advisory research metadata with no system connection",
)
_SMA_RETURN_PIPELINE_EXTRA_NON_CLAIMS = (
    _not("meth", "odology app", "roval"),
)
_DATA_SOURCE_REQUIRED_CONTROLS = (
    "terms_review_documented",
    "snapshot_provenance_defined",
    "redistribution_policy_reviewed",
    "adjustment_policy_defined",
    "fixture_policy_review_documented",
    "no_lookahead_protocol_defined",
)
_DATA_SOURCE_SATISFIED_CONTROLS = ("no_lookahead_protocol_defined",)
_DATA_SOURCE_EVIDENCE_REFS = (
    _join("synthetic_phase_271_read", "iness_fixture"),
    "internal_control_gap_note",
)
_DATA_SOURCE_LIMITATIONS = (
    "Fixture is synthetic metadata only and not connected to real data.",
    "Fixture carries no observations, values, or external source content.",
)
_DATA_SOURCE_NON_CLAIMS = (
    _join("no source app", "roval"),
    _join("no data ingestion app", "roval"),
    _join("no tra", "ding authority"),
    "no capital authority",
    "no data-source authorization",
)


def build_synthetic_advisory_operating_brief_package_preview() -> (
    AdvisoryOperatingBriefPackage
):
    """Return the deterministic synthetic advisory package preview."""

    content_bundle = _build_synthetic_package_content_bundle()
    sma_return_research_pipeline_observation = (
        _build_synthetic_sma_return_research_pipeline_observation()
    )
    return build_advisory_operating_brief_package(
        package_id=_PACKAGE_ID,
        title=_TITLE,
        summary=_SUMMARY,
        as_of=_AS_OF,
        content_bundle=content_bundle,
        sma_return_research_pipeline_observation=sma_return_research_pipeline_observation,
        research_observation_manifest=build_research_observation_manifest(
            (
                (
                    "sma_return_research_pipeline_observation",
                    sma_return_research_pipeline_observation.to_dict(),
                ),
            )
        ),
    )


def _build_synthetic_package_content_bundle() -> AdvisoryOperatingBriefContentBundle:
    source = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation(
            include_risk_authority=True,
            include_research_queue=True,
            include_sma_research_observation=True,
            include_sma_research_summary_observation=True,
            include_research_return_observation=True,
        )
    )
    data_source_readiness = _build_package_research_data_source_readiness()
    data_source_readiness_summary = (
        _build_package_research_data_source_readiness_summary(
            data_source_readiness
        )
    )
    base_bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        risk_authority_briefs=source.risk_authority_briefs,
        research_queue_briefs=(_build_package_research_queue_brief(source),),
        sma_research_observation_briefs=source.sma_research_observation_briefs,
        sma_research_summary_observations=(
            source.sma_research_summary_observations
        ),
        research_return_observation_briefs=source.research_return_observation_briefs,
        research_return_summary_observation_briefs=(
            source.research_return_summary_observation_briefs
        ),
        research_data_source_readiness=(
            data_source_readiness,
        ),
        research_data_source_readiness_summaries=(
            data_source_readiness_summary,
        ),
    )
    diagnostic_issues = build_advisory_operating_brief_diagnostic_issues(
        base_bundle
    )
    diagnostic_bundle = build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=base_bundle.candidate_research_briefs,
        strategy_eligibility_briefs=base_bundle.strategy_eligibility_briefs,
        risk_authority_briefs=base_bundle.risk_authority_briefs,
        research_queue_briefs=base_bundle.research_queue_briefs,
        sma_research_observation_briefs=base_bundle.sma_research_observation_briefs,
        sma_research_summary_observations=(
            base_bundle.sma_research_summary_observations
        ),
        research_return_observation_briefs=(
            base_bundle.research_return_observation_briefs
        ),
        research_return_summary_observation_briefs=(
            base_bundle.research_return_summary_observation_briefs
        ),
        research_data_source_readiness=base_bundle.research_data_source_readiness,
        research_data_source_readiness_summaries=(
            base_bundle.research_data_source_readiness_summaries
        ),
        diagnostic_issues=diagnostic_issues,
    )
    advisory_sections = build_advisory_operating_brief_sections(
        diagnostic_bundle
    )
    advisory_view = build_advisory_operating_brief_view(advisory_sections)
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=base_bundle.candidate_research_briefs,
        strategy_eligibility_briefs=base_bundle.strategy_eligibility_briefs,
        risk_authority_briefs=base_bundle.risk_authority_briefs,
        research_queue_briefs=base_bundle.research_queue_briefs,
        sma_research_observation_briefs=base_bundle.sma_research_observation_briefs,
        sma_research_summary_observations=(
            base_bundle.sma_research_summary_observations
        ),
        research_return_observation_briefs=(
            base_bundle.research_return_observation_briefs
        ),
        research_return_summary_observation_briefs=(
            base_bundle.research_return_summary_observation_briefs
        ),
        research_data_source_readiness=base_bundle.research_data_source_readiness,
        research_data_source_readiness_summaries=(
            base_bundle.research_data_source_readiness_summaries
        ),
        diagnostic_issues=diagnostic_issues,
        advisory_sections=advisory_sections,
        advisory_view=advisory_view,
    )


def _build_package_research_data_source_readiness() -> ResearchDataSourceReadiness:
    return build_research_data_source_readiness(
        source_id="synthetic-broad-etf-source-candidate",
        source_name="Synthetic broad ETF source candidate",
        asset_class_scope=("equity_etf",),
        intended_use="pipeline_validation_only",
        readiness_state="candidate_only",
        required_controls=_DATA_SOURCE_REQUIRED_CONTROLS,
        satisfied_controls=_DATA_SOURCE_SATISFIED_CONTROLS,
        evidence_refs=_DATA_SOURCE_EVIDENCE_REFS,
        limitations=_DATA_SOURCE_LIMITATIONS,
        non_claims=_DATA_SOURCE_NON_CLAIMS,
    )


def _build_package_research_data_source_readiness_summary(
    source_readiness: ResearchDataSourceReadiness,
) -> ResearchDataSourceReadinessSummary:
    return build_research_data_source_readiness_summary(source_readiness)


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


def _build_synthetic_sma_return_research_pipeline_observation() -> (
    SmaReturnResearchPipelineObservation
):
    alignment = build_sma_return_alignment_observation(
        _build_sma_return_pipeline_sma_observations(),
        _build_sma_return_pipeline_return_observation(),
    )
    alignment_summary = build_sma_return_alignment_summary_observation(alignment)
    selection = build_sma_conditional_return_selection_observation(alignment)
    selection_summary = build_sma_conditional_return_selection_summary_observation(
        selection
    )
    selected_series = build_sma_selected_source_return_series_observation(selection)
    selected_summary = build_sma_selected_source_return_summary_observation(
        selected_series
    )
    return build_sma_return_research_pipeline_observation(
        alignment,
        alignment_summary,
        selection,
        selection_summary,
        selected_series,
        selected_summary,
    )


def _build_sma_return_pipeline_sma_observations() -> (
    tuple[SmaResearchObservation, ...]
):
    return (
        _build_sma_return_pipeline_sma_observation(
            as_of="2026-01-14",
            prices=(
                _sma_return_pipeline_sma_price_point("2026-01-13", "10.00"),
                _sma_return_pipeline_sma_price_point("2026-01-14", "10.00"),
            ),
        ),
        _build_sma_return_pipeline_sma_observation(
            as_of="2026-01-16",
            prices=(
                _sma_return_pipeline_sma_price_point("2026-01-15", "10.00"),
                _sma_return_pipeline_sma_price_point("2026-01-16", "30.00"),
            ),
        ),
        _build_sma_return_pipeline_sma_observation(
            as_of="2026-01-19",
            prices=(
                _sma_return_pipeline_sma_price_point("2026-01-16", "30.00"),
                _sma_return_pipeline_sma_price_point("2026-01-19", "10.00"),
            ),
        ),
        _build_sma_return_pipeline_sma_observation(
            as_of="2026-01-20",
            prices=(
                _sma_return_pipeline_sma_price_point("2026-01-19", "10.00"),
                _sma_return_pipeline_sma_price_point("2026-01-20", "40.00"),
            ),
        ),
    )


def _build_sma_return_pipeline_sma_observation(
    *,
    as_of: str,
    prices: tuple[SmaResearchPricePoint, ...],
) -> SmaResearchObservation:
    return build_sma_research_observation(
        symbol=_SMA_RETURN_PIPELINE_SYMBOL,
        as_of=as_of,
        window=_SMA_RETURN_PIPELINE_WINDOW,
        price_points=prices,
        limitations=_SMA_RETURN_PIPELINE_SMA_LIMITATIONS,
        non_claims=_SMA_RETURN_PIPELINE_EXTRA_NON_CLAIMS,
    )


def _build_sma_return_pipeline_return_observation() -> (
    ResearchReturnSeriesObservation
):
    return build_research_return_series_observation(
        symbol=_SMA_RETURN_PIPELINE_SYMBOL,
        as_of=_SMA_RETURN_PIPELINE_AS_OF,
        price_points=(
            _sma_return_pipeline_return_price_point("2026-01-15", "100.00"),
            _sma_return_pipeline_return_price_point("2026-01-16", "105.00"),
            _sma_return_pipeline_return_price_point("2026-01-19", "94.50"),
            _sma_return_pipeline_return_price_point("2026-01-20", "94.50"),
            _sma_return_pipeline_return_price_point("2026-01-21", "120.00"),
        ),
        limitations=_SMA_RETURN_PIPELINE_RETURN_LIMITATIONS,
        non_claims=_SMA_RETURN_PIPELINE_EXTRA_NON_CLAIMS,
    )


def _sma_return_pipeline_sma_price_point(
    value_date: str,
    close: str,
) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))


def _sma_return_pipeline_return_price_point(
    value_date: str,
    close: str,
) -> ResearchReturnPricePoint:
    return ResearchReturnPricePoint(value_date, Decimal(close))
