"""Developer preview helpers for synthetic advisory content bundle exports."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.candidate_research_brief import (
    CandidateResearchBrief,
    build_candidate_research_brief,
)
from algotrader.research.candidate_research_brief_item import (
    build_candidate_research_brief_item,
)
from algotrader.research.candidate_research_brief_section import (
    build_candidate_research_brief_section,
)
from algotrader.research.candidate_result_dossier import (
    build_candidate_research_result_dossier,
)
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_package import (
    build_research_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)
from algotrader.research.risk_authority_brief import (
    RiskAuthorityBrief,
    build_risk_authority_brief,
)
from algotrader.research.risk_authority_brief_item import (
    build_risk_authority_brief_item,
)
from algotrader.research.risk_authority_brief_section import (
    build_risk_authority_brief_section,
)
from algotrader.research.risk_authority_status import build_risk_authority_status
from algotrader.research.strategy_eligibility_brief import (
    StrategyEligibilityBrief,
    build_strategy_eligibility_brief,
)
from algotrader.research.strategy_eligibility_brief_item import (
    build_strategy_eligibility_brief_item,
)
from algotrader.research.strategy_eligibility_brief_section import (
    build_strategy_eligibility_brief_section,
)
from algotrader.research.strategy_eligibility_status import (
    build_strategy_eligibility_status,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_content_bundle",
    "build_synthetic_advisory_operating_brief_content_bundle_with_risk",
    "render_advisory_operating_brief_content_bundle_preview",
]

_PREVIEW_FORMATS = ("text", "json")


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


def _join(*parts: str) -> str:
    return "".join(parts)


_RETURN_INPUT_NON_CLAIMS = (
    _not("source approval"),
    _not("data approval"),
    _not("endpoint approval"),
    _not("universe approval"),
    _not("bench", "mark approval"),
    _not("ca", "sh proxy approval"),
    _not("methodology approval"),
    _not("evidence approval"),
    _not("return-construction approval"),
    _not("no-lookahead approval"),
    _not("stra", "tegy validation"),
    _not("tra", "ding readiness"),
)
_STRATEGY_REASONS = (
    "synthetic strategy metadata is scoped to research review",
    "eligibility status is provided for advisory composition tests",
)
_STRATEGY_EVIDENCE_REFS = (
    "synthetic-evidence-ref-001",
    "synthetic-advisory-metadata-ref-001",
)
_STRATEGY_BLOCKERS = (
    "validation review has not been completed",
    "readiness review has not been completed",
)
_STRATEGY_REQUIRED_NEXT_STEPS = (
    "complete independent methodology review before any readiness claim",
    "collect validation evidence before any approval claim",
)
_STRATEGY_LIMITATIONS = (
    "synthetic metadata only",
    "no profitability evidence is represented",
    "no approval or readiness decision is represented",
)
_STRATEGY_NON_CLAIMS = (
    _not("validation"),
    _not("paper readiness"),
    _not("live readiness"),
    _not("a tra", "ding recommendation"),
    _not("allo", "cation authority"),
    _not("or", "der authority"),
    _not("profitability evidence"),
    _not("approval"),
    _not("capital authority"),
)
_RISK_REASONS = (
    "synthetic risk authority status is scoped to advisory composition tests",
    "risk-capital authority remains absent for this synthetic candidate",
)
_RISK_BLOCKERS = (
    "external risk review has not been completed",
    "capital authorization path is not represented",
)
_RISK_REQUIRED_NEXT_STEPS = (
    "complete independent risk governance review before any authority change",
    "record advisory-only evidence before composing downstream briefs",
)
_RISK_LIMITATIONS = (
    "synthetic metadata only",
    _join(
        "no approval, readiness, recommendation, allo",
        "cation, or",
        "der placement, bro",
        "ker access, port",
        "folio mutation, capital authority, or tra",
        "ding authority is represented",
    ),
    _join("fixture output is not connected to run", "time or ac", "count state"),
)
_RISK_NON_CLAIMS = (
    _not("risk approval"),
    _not("allo", "cation authority"),
    _not("or", "der authority"),
    _not("paper readiness"),
    _not("live readiness"),
    _not("bro", "ker authority"),
    _not("port", "folio mutation authority"),
    _not("capital authority"),
    _not("tra", "ding authority"),
    _not("a tra", "ding recommendation"),
    _not("or", "der placement"),
    _not("bro", "ker access"),
    _not("port", "folio mutation"),
)
_RISK_EVIDENCE_REFS = (
    "synthetic-risk-authority-status-evidence-001",
    "phase-169-risk-authority-status-contract",
)
_RISK_RELATED_STRATEGY_IDS = ("synthetic-risk-authority-strategy-001",)


def build_synthetic_advisory_operating_brief_content_bundle() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic synthetic advisory content bundle preview."""

    candidate_brief = _build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = _build_synthetic_strategy_eligibility_brief()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
    )


def build_synthetic_advisory_operating_brief_content_bundle_with_risk() -> (
    AdvisoryOperatingBriefContentBundle
):
    """Return the deterministic synthetic advisory content bundle with risk."""

    candidate_brief = _build_synthetic_candidate_research_brief()
    strategy_eligibility_brief = _build_synthetic_strategy_eligibility_brief()
    risk_authority_brief = _build_synthetic_risk_authority_brief()
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=(candidate_brief,),
        strategy_eligibility_briefs=(strategy_eligibility_brief,),
        risk_authority_briefs=(risk_authority_brief,),
    )


def render_advisory_operating_brief_content_bundle_preview(
    output_format: str = "text",
    *,
    include_risk_authority: bool = False,
) -> str:
    """Return the deterministic synthetic advisory content bundle export."""

    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_risk()
        if include_risk_authority
        else build_synthetic_advisory_operating_brief_content_bundle()
    )
    exported = export_advisory_operating_brief_content_bundle(
        bundle
    )
    if output_format == "text":
        return exported.rendered_text
    if output_format == "json":
        return exported.json_text

    expected = ", ".join(_PREVIEW_FORMATS)
    raise ValueError(
        "unsupported advisory operating brief content bundle preview format: "
        f"{output_format!r}. Expected one of: {expected}."
    )


def _build_synthetic_candidate_research_brief() -> CandidateResearchBrief:
    snapshot = _build_synthetic_research_return_input_snapshot()
    package = build_research_return_input_package(snapshot)
    result = build_synthetic_research_result_from_return_input_package(package)
    dossier = build_candidate_research_result_dossier(package, result)
    item = build_candidate_research_brief_item(dossier)
    section = build_candidate_research_brief_section((item,))
    return build_candidate_research_brief((section,))


def _build_synthetic_research_return_input_snapshot() -> (
    ResearchReturnInputSnapshot
):
    return ResearchReturnInputSnapshot(
        snapshot_id="synthetic_return_input_snapshot_fixture_001",
        symbol="SYNRET121X",
        observation_dates=(
            date(2099, 1, 3),
            date(2099, 1, 4),
            date(2099, 1, 7),
        ),
        close_values=(
            Decimal("10.0000"),
            Decimal("10.5000"),
            Decimal("9.9750"),
        ),
        close_to_close_returns=(
            Decimal("0.05"),
            Decimal("-0.05"),
        ),
        return_basis="synthetic_prepared_close_to_close_simple_return_input",
        adjustment_policy="synthetic_prepared_values_no_external_adjustments",
        synthetic_only=True,
        candidate_only=True,
        non_claims=_RETURN_INPUT_NON_CLAIMS,
    )


def _build_synthetic_strategy_eligibility_brief() -> StrategyEligibilityBrief:
    status = build_strategy_eligibility_status(
        strategy_id="synthetic-strategy-eligibility-001",
        strategy_name="Synthetic strategy eligibility research fixture",
        eligibility_state="research_only",
        reasons=_STRATEGY_REASONS,
        evidence_refs=_STRATEGY_EVIDENCE_REFS,
        blockers=_STRATEGY_BLOCKERS,
        required_next_steps=_STRATEGY_REQUIRED_NEXT_STEPS,
        limitations=_STRATEGY_LIMITATIONS,
        non_claims=_STRATEGY_NON_CLAIMS,
    )
    item = build_strategy_eligibility_brief_item(status)
    section = build_strategy_eligibility_brief_section((item,))
    return build_strategy_eligibility_brief((section,))


def _build_synthetic_risk_authority_brief() -> RiskAuthorityBrief:
    status = build_risk_authority_status(
        authority_state="not_authorized",
        reasons=_RISK_REASONS,
        blockers=_RISK_BLOCKERS,
        required_next_steps=_RISK_REQUIRED_NEXT_STEPS,
        limitations=_RISK_LIMITATIONS,
        non_claims=_RISK_NON_CLAIMS,
        evidence_refs=_RISK_EVIDENCE_REFS,
        related_strategy_ids=_RISK_RELATED_STRATEGY_IDS,
    )
    item = build_risk_authority_brief_item(status)
    section = build_risk_authority_brief_section((item,))
    return build_risk_authority_brief((section,))
