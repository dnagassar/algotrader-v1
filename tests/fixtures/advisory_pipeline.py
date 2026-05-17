"""Synthetic advisory snapshot-to-renderer pipeline fixture for tests."""

from __future__ import annotations

from datetime import date

from algotrader.advisory import (
    AdvisoryLabel,
    CandidateDossierSnapshot,
    OperatingBrief,
    OperatingBriefBoardSummary,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    assemble_operating_brief_from_parts,
    build_operating_brief_board_summary,
    candidate_snapshot_to_research_candidate_dossier,
    risk_authority_snapshot_to_risk_authority_status,
    strategy_mandate_snapshot_to_strategy_eligibility_status,
)
from algotrader.governance import RiskAuthoritySnapshot, StrategyMandateSnapshot

__all__ = [
    "build_synthetic_advisory_board_summary_from_pipeline",
    "build_synthetic_advisory_dossiers_from_snapshots",
    "build_synthetic_advisory_operating_brief_from_pipeline",
    "build_synthetic_candidate_snapshots",
    "build_synthetic_risk_authority_snapshots",
    "build_synthetic_risk_statuses_from_snapshots",
    "build_synthetic_strategy_mandate_snapshots",
    "build_synthetic_strategy_statuses_from_snapshots",
    "expected_synthetic_pipeline_board_summary_markdown",
    "expected_synthetic_pipeline_operating_brief_markdown",
]


def build_synthetic_candidate_snapshots() -> tuple[CandidateDossierSnapshot, ...]:
    """Return deterministic source snapshots for the advisory pipeline fixture."""
    return (
        CandidateDossierSnapshot(
            candidate_id="synthetic_pipeline_research_only",
            as_of_date=date(2026, 1, 16),
            title="Synthetic pipeline research-only dossier",
            summary=(
                "Synthetic fixture notes keep this candidate in research review "
                "while basic questions remain open."
            ),
            source_type="synthetic",
            source_ids=("synthetic_pipeline_source_research_001",),
            proposed_label=AdvisoryLabel.RESEARCH_ONLY,
            label_source="synthetic_fixture",
            label_rationale=(
                "Synthetic fixture keeps the candidate at research-only review.",
            ),
            strategy_id="",
            mandate_id="",
            universe_refs=("synthetic_pipeline_universe_research",),
            evidence_refs=(),
            uncertainty_factors=(
                "Synthetic source notes have not been reconciled with a review checklist.",
            ),
            failure_modes=(
                "The research premise may be incomplete if fixture assumptions conflict.",
            ),
            next_questions=(
                "Which synthetic evidence note should be reviewed first?",
            ),
            limitations=(
                "Research-only label has no prepared strategy or risk support.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        CandidateDossierSnapshot(
            candidate_id="synthetic_pipeline_watchlist_only",
            as_of_date=date(2026, 1, 16),
            title="Synthetic pipeline watchlist-only dossier",
            summary=(
                "Synthetic fixture notes keep this candidate visible while its "
                "label remains intentionally non-actionable."
            ),
            source_type="synthetic",
            source_ids=("synthetic_pipeline_source_watchlist_001",),
            proposed_label=AdvisoryLabel.WATCHLIST_ONLY,
            label_source="synthetic_fixture",
            label_rationale=(
                "Synthetic fixture pins the watchlist label despite permissive support metadata.",
            ),
            strategy_id="synthetic_pipeline_strategy_watchlist_live",
            mandate_id="synthetic_pipeline_mandate_watchlist_live",
            universe_refs=("synthetic_pipeline_universe_watchlist",),
            evidence_refs=("synthetic_pipeline_evidence_watchlist_live",),
            uncertainty_factors=(
                "Optional support metadata is more permissive than the source label.",
            ),
            failure_modes=(
                "Readers may overstate the optional support metadata if the label is ignored.",
            ),
            next_questions=(
                "Which synthetic label review would be required before promotion?",
            ),
            limitations=(
                "Watchlist label remains authoritative over optional support metadata.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        CandidateDossierSnapshot(
            candidate_id="synthetic_pipeline_paper_eligible",
            as_of_date=date(2026, 1, 16),
            title="Synthetic pipeline paper-eligible dossier",
            summary=(
                "Synthetic fixture notes show paper metadata support while probe "
                "and live gates remain blocked."
            ),
            source_type="synthetic",
            source_ids=("synthetic_pipeline_source_paper_001",),
            proposed_label=AdvisoryLabel.PAPER_ELIGIBLE,
            label_source="synthetic_fixture",
            label_rationale=(
                "Synthetic fixture grants paper-only advisory metadata.",
            ),
            strategy_id="synthetic_pipeline_strategy_paper",
            mandate_id="synthetic_pipeline_mandate_paper",
            universe_refs=("synthetic_pipeline_universe_paper",),
            evidence_refs=("synthetic_pipeline_evidence_paper",),
            uncertainty_factors=(
                "Paper support depends on synthetic evidence references only.",
            ),
            failure_modes=(
                "Paper support may miss a required synthetic probe constraint.",
            ),
            next_questions=(
                "Which synthetic control would be needed before probe review?",
            ),
            limitations=(
                "Paper label is advisory metadata only and does not imply higher readiness.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        CandidateDossierSnapshot(
            candidate_id="synthetic_pipeline_live_probe_eligible",
            as_of_date=date(2026, 1, 16),
            title="Synthetic pipeline live-probe-eligible dossier",
            summary=(
                "Synthetic fixture notes show live-probe metadata support while "
                "final authorization remains blocked."
            ),
            source_type="synthetic",
            source_ids=("synthetic_pipeline_source_probe_001",),
            proposed_label=AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
            label_source="synthetic_fixture",
            label_rationale=(
                "Synthetic fixture grants probe-only advisory metadata.",
            ),
            strategy_id="synthetic_pipeline_strategy_probe",
            mandate_id="synthetic_pipeline_mandate_probe",
            universe_refs=("synthetic_pipeline_universe_probe",),
            evidence_refs=("synthetic_pipeline_evidence_probe",),
            uncertainty_factors=(
                "Probe support remains based on synthetic review assumptions.",
            ),
            failure_modes=(
                "Probe support may fail if the final authorization gate changes.",
            ),
            next_questions=(
                "Which synthetic approval note would resolve the final blocker?",
            ),
            limitations=(
                "Probe label is advisory metadata only and not final authorization.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        CandidateDossierSnapshot(
            candidate_id="synthetic_pipeline_live_authorized",
            as_of_date=date(2026, 1, 16),
            title="Synthetic pipeline live-authorized dossier",
            summary=(
                "Synthetic fixture notes show constructor-gated live authorization "
                "metadata with matching prepared support."
            ),
            source_type="synthetic",
            source_ids=("synthetic_pipeline_source_live_001",),
            proposed_label=AdvisoryLabel.LIVE_AUTHORIZED,
            label_source="synthetic_fixture",
            label_rationale=(
                "Synthetic fixture grants live-authorized advisory metadata.",
            ),
            strategy_id="synthetic_pipeline_strategy_live",
            mandate_id="synthetic_pipeline_mandate_live",
            universe_refs=("synthetic_pipeline_universe_live",),
            evidence_refs=("synthetic_pipeline_evidence_live",),
            uncertainty_factors=(
                "Live authorization metadata is synthetic and limited to this fixture.",
            ),
            failure_modes=(
                "Live authorization metadata may be misread outside this fixture.",
            ),
            next_questions=(
                "Which synthetic reviewer would re-check the gate metadata?",
            ),
            limitations=(
                "Live label remains advisory metadata and does not create capital authority.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
    )


def build_synthetic_strategy_mandate_snapshots() -> (
    tuple[StrategyMandateSnapshot, ...]
):
    """Return deterministic strategy snapshots needed by the fixture assembly."""
    return (
        StrategyMandateSnapshot(
            strategy_id="synthetic_pipeline_strategy_watchlist_live",
            mandate_id="synthetic_pipeline_mandate_watchlist_live",
            as_of_date=date(2026, 1, 16),
            mandate_approved=True,
            evidence_approved=True,
            paper_eligible=True,
            live_probe_eligible=True,
            live_authorized=True,
            validated_research_artifact_ids=(
                "synthetic_pipeline_strategy_watchlist_artifact",
            ),
            validated_signal_definition_ids=(
                "synthetic_pipeline_strategy_watchlist_definition",
            ),
            required_evidence=(
                "Synthetic watchlist evidence packet is present.",
            ),
            promotion_requirements=(
                "Synthetic label review must explicitly change the candidate label.",
            ),
            revocation_triggers=(
                "Synthetic watchlist evidence packet is withdrawn.",
            ),
            blocking_reasons=(),
            limitations=(
                "Strategy metadata is intentionally more permissive than the watchlist label.",
            ),
            uncertainty_factors=(
                "Permissive strategy metadata is optional support for a non-actionable label.",
            ),
            failure_modes=(
                "The support metadata may be mistaken for label promotion.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        StrategyMandateSnapshot(
            strategy_id="synthetic_pipeline_strategy_paper",
            mandate_id="synthetic_pipeline_mandate_paper",
            as_of_date=date(2026, 1, 16),
            mandate_approved=True,
            evidence_approved=True,
            paper_eligible=True,
            live_probe_eligible=False,
            live_authorized=False,
            validated_research_artifact_ids=(
                "synthetic_pipeline_strategy_paper_artifact",
            ),
            validated_signal_definition_ids=(
                "synthetic_pipeline_strategy_paper_definition",
            ),
            required_evidence=("Synthetic paper evidence packet is present.",),
            promotion_requirements=(
                "Synthetic probe mandate review must be approved.",
            ),
            revocation_triggers=(
                "Synthetic paper evidence packet is withdrawn.",
            ),
            blocking_reasons=(
                "Synthetic probe mandate review remains closed.",
            ),
            limitations=("Paper strategy metadata is not probe readiness.",),
            uncertainty_factors=(
                "Paper evidence may not cover probe review constraints.",
            ),
            failure_modes=(
                "A missing synthetic constraint could invalidate paper support.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        StrategyMandateSnapshot(
            strategy_id="synthetic_pipeline_strategy_probe",
            mandate_id="synthetic_pipeline_mandate_probe",
            as_of_date=date(2026, 1, 16),
            mandate_approved=True,
            evidence_approved=True,
            paper_eligible=True,
            live_probe_eligible=True,
            live_authorized=False,
            validated_research_artifact_ids=(
                "synthetic_pipeline_strategy_probe_artifact",
            ),
            validated_signal_definition_ids=(
                "synthetic_pipeline_strategy_probe_definition",
            ),
            required_evidence=("Synthetic probe evidence packet is present.",),
            promotion_requirements=(
                "Synthetic final mandate review must be approved.",
            ),
            revocation_triggers=(
                "Synthetic probe evidence packet is withdrawn.",
            ),
            blocking_reasons=(
                "Synthetic final mandate review remains closed.",
            ),
            limitations=("Probe strategy metadata is not final authorization.",),
            uncertainty_factors=(
                "Probe evidence may not cover final authorization review constraints.",
            ),
            failure_modes=(
                "A final review gap could invalidate probe support.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        StrategyMandateSnapshot(
            strategy_id="synthetic_pipeline_strategy_live",
            mandate_id="synthetic_pipeline_mandate_live",
            as_of_date=date(2026, 1, 16),
            mandate_approved=True,
            evidence_approved=True,
            paper_eligible=True,
            live_probe_eligible=True,
            live_authorized=True,
            validated_research_artifact_ids=(
                "synthetic_pipeline_strategy_live_artifact",
            ),
            validated_signal_definition_ids=(
                "synthetic_pipeline_strategy_live_definition",
            ),
            required_evidence=("Synthetic live evidence packet is present.",),
            promotion_requirements=(
                "Synthetic periodic re-check remains documented.",
            ),
            revocation_triggers=(
                "Synthetic live evidence packet is withdrawn.",
            ),
            blocking_reasons=(),
            limitations=("Live strategy status is synthetic metadata only.",),
            uncertainty_factors=(
                "Live strategy metadata depends on synthetic evidence references.",
            ),
            failure_modes=(
                "The synthetic evidence packet may be misapplied outside this fixture.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
    )


def build_synthetic_risk_authority_snapshots() -> tuple[RiskAuthoritySnapshot, ...]:
    """Return deterministic risk snapshots needed by the fixture assembly."""
    return (
        RiskAuthoritySnapshot(
            authority_id="synthetic_pipeline_authority_watchlist_live",
            strategy_id="synthetic_pipeline_strategy_watchlist_live",
            as_of_date=date(2026, 1, 16),
            paper_allowed=True,
            live_probe_allowed=True,
            live_allowed=True,
            kill_switch_active=False,
            risk_policy_ids=("synthetic_pipeline_risk_policy_watchlist",),
            active_constraints=("Synthetic watchlist constraints are documented.",),
            promotion_requirements=(
                "Synthetic label review must explicitly change the candidate label.",
            ),
            revocation_triggers=(
                "Synthetic watchlist risk note is withdrawn.",
            ),
            blocking_reasons=(),
            limitations=(
                "Risk metadata is intentionally more permissive than the watchlist label.",
            ),
            uncertainty_factors=(
                "Permissive risk metadata is optional support for a non-actionable label.",
            ),
            failure_modes=(
                "The support metadata may be mistaken for label promotion.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        RiskAuthoritySnapshot(
            authority_id="synthetic_pipeline_authority_paper",
            strategy_id="synthetic_pipeline_strategy_paper",
            as_of_date=date(2026, 1, 16),
            paper_allowed=True,
            live_probe_allowed=False,
            live_allowed=False,
            kill_switch_active=False,
            risk_policy_ids=("synthetic_pipeline_risk_policy_paper",),
            active_constraints=("Synthetic paper constraint is documented.",),
            promotion_requirements=(
                "Synthetic probe authority review must be approved.",
            ),
            revocation_triggers=("Synthetic paper risk note is withdrawn.",),
            blocking_reasons=(
                "Synthetic probe authority review remains closed.",
            ),
            limitations=("Paper risk metadata is not probe readiness.",),
            uncertainty_factors=(
                "Paper authority may not cover probe review constraints.",
            ),
            failure_modes=(
                "A missing synthetic risk constraint could invalidate paper support.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        RiskAuthoritySnapshot(
            authority_id="synthetic_pipeline_authority_probe",
            strategy_id="synthetic_pipeline_strategy_probe",
            as_of_date=date(2026, 1, 16),
            paper_allowed=True,
            live_probe_allowed=True,
            live_allowed=False,
            kill_switch_active=False,
            risk_policy_ids=("synthetic_pipeline_risk_policy_probe",),
            active_constraints=("Synthetic probe constraint is documented.",),
            promotion_requirements=(
                "Synthetic final authority review must be approved.",
            ),
            revocation_triggers=("Synthetic probe risk note is withdrawn.",),
            blocking_reasons=(
                "Synthetic final authority review remains closed.",
            ),
            limitations=("Probe risk metadata is not final authorization.",),
            uncertainty_factors=(
                "Probe authority may not cover final review constraints.",
            ),
            failure_modes=(
                "A final risk review gap could invalidate probe support.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
        RiskAuthoritySnapshot(
            authority_id="synthetic_pipeline_authority_live",
            strategy_id="synthetic_pipeline_strategy_live",
            as_of_date=date(2026, 1, 16),
            paper_allowed=True,
            live_probe_allowed=True,
            live_allowed=True,
            kill_switch_active=False,
            risk_policy_ids=("synthetic_pipeline_risk_policy_live",),
            active_constraints=("Synthetic live constraint is documented.",),
            promotion_requirements=(
                "Synthetic periodic re-check remains documented.",
            ),
            revocation_triggers=("Synthetic live risk note is withdrawn.",),
            blocking_reasons=(),
            limitations=("Live risk status is synthetic metadata only.",),
            uncertainty_factors=(
                "Live risk metadata depends on synthetic policy references.",
            ),
            failure_modes=(
                "The synthetic risk packet may be misapplied outside this fixture.",
            ),
            non_claims=("No capital instruction is represented.",),
        ),
    )


def build_synthetic_advisory_dossiers_from_snapshots() -> (
    tuple[ResearchCandidateDossier, ...]
):
    """Adapt synthetic candidate snapshots into prepared advisory dossiers."""
    return tuple(
        candidate_snapshot_to_research_candidate_dossier(snapshot)
        for snapshot in build_synthetic_candidate_snapshots()
    )


def build_synthetic_strategy_statuses_from_snapshots() -> (
    tuple[StrategyEligibilityStatus, ...]
):
    """Adapt synthetic strategy snapshots with explicit candidate ids."""
    snapshots = build_synthetic_strategy_mandate_snapshots()
    return (
        strategy_mandate_snapshot_to_strategy_eligibility_status(
            snapshots[0],
            candidate_id="synthetic_pipeline_watchlist_only",
        ),
        strategy_mandate_snapshot_to_strategy_eligibility_status(
            snapshots[1],
            candidate_id="synthetic_pipeline_paper_eligible",
        ),
        strategy_mandate_snapshot_to_strategy_eligibility_status(
            snapshots[2],
            candidate_id="synthetic_pipeline_live_probe_eligible",
        ),
        strategy_mandate_snapshot_to_strategy_eligibility_status(
            snapshots[3],
            candidate_id="synthetic_pipeline_live_authorized",
        ),
    )


def build_synthetic_risk_statuses_from_snapshots() -> (
    tuple[RiskAuthorityStatus, ...]
):
    """Adapt synthetic risk snapshots with explicit candidate ids."""
    snapshots = build_synthetic_risk_authority_snapshots()
    return (
        risk_authority_snapshot_to_risk_authority_status(
            snapshots[0],
            candidate_id="synthetic_pipeline_watchlist_only",
        ),
        risk_authority_snapshot_to_risk_authority_status(
            snapshots[1],
            candidate_id="synthetic_pipeline_paper_eligible",
        ),
        risk_authority_snapshot_to_risk_authority_status(
            snapshots[2],
            candidate_id="synthetic_pipeline_live_probe_eligible",
        ),
        risk_authority_snapshot_to_risk_authority_status(
            snapshots[3],
            candidate_id="synthetic_pipeline_live_authorized",
        ),
    )


def build_synthetic_advisory_operating_brief_from_pipeline() -> OperatingBrief:
    """Assemble the synthetic fixture from already prepared advisory parts."""
    return assemble_operating_brief_from_parts(
        as_of_date=date(2026, 1, 16),
        dossiers=build_synthetic_advisory_dossiers_from_snapshots(),
        strategy_statuses=build_synthetic_strategy_statuses_from_snapshots(),
        risk_statuses=build_synthetic_risk_statuses_from_snapshots(),
    )


def build_synthetic_advisory_board_summary_from_pipeline() -> (
    OperatingBriefBoardSummary
):
    """Build a board summary from a new synthetic pipeline operating brief."""
    return build_operating_brief_board_summary(
        build_synthetic_advisory_operating_brief_from_pipeline()
    )


def expected_synthetic_pipeline_operating_brief_markdown() -> str:
    """Return the pinned OperatingBrief Markdown for the pipeline fixture."""
    return _EXPECTED_SYNTHETIC_PIPELINE_OPERATING_BRIEF_MARKDOWN


def expected_synthetic_pipeline_board_summary_markdown() -> str:
    """Return the pinned OperatingBriefBoardSummary Markdown fixture."""
    return _EXPECTED_SYNTHETIC_PIPELINE_BOARD_SUMMARY_MARKDOWN


_EXPECTED_SYNTHETIC_PIPELINE_OPERATING_BRIEF_MARKDOWN = """# Advisory Operating Brief

As-of date: 2026-01-16

Advisory status:
This brief is advisory metadata only. It is not a trading recommendation, not a signal, not an order request, and not live-trading authority.

## Candidate Dossiers

### 1. synthetic_pipeline_research_only

- Candidate id: synthetic_pipeline_research_only
- Title: Synthetic pipeline research-only dossier
- Advisory label: research_only
- Thesis/context: Synthetic fixture notes keep this candidate in research review while basic questions remain open.
- Uncertainty:
  - Synthetic source notes have not been reconciled with a review checklist.
- Failure modes:
  - The research premise may be incomplete if fixture assumptions conflict.
- Next questions / research needs:
  - Which synthetic evidence note should be reviewed first?
- Limitations / non-claims:
  - Research-only label has no prepared strategy or risk support.

### 2. synthetic_pipeline_watchlist_only

- Candidate id: synthetic_pipeline_watchlist_only
- Title: Synthetic pipeline watchlist-only dossier
- Advisory label: watchlist_only
- Thesis/context: Synthetic fixture notes keep this candidate visible while its label remains intentionally non-actionable.
- Uncertainty:
  - Optional support metadata is more permissive than the source label.
- Failure modes:
  - Readers may overstate the optional support metadata if the label is ignored.
- Next questions / research needs:
  - Which synthetic label review would be required before promotion?
- Limitations / non-claims:
  - Watchlist label remains authoritative over optional support metadata.

### 3. synthetic_pipeline_paper_eligible

- Candidate id: synthetic_pipeline_paper_eligible
- Title: Synthetic pipeline paper-eligible dossier
- Advisory label: paper_eligible
- Thesis/context: Synthetic fixture notes show paper metadata support while probe and live gates remain blocked.
- Uncertainty:
  - Paper support depends on synthetic evidence references only.
- Failure modes:
  - Paper support may miss a required synthetic probe constraint.
- Next questions / research needs:
  - Which synthetic control would be needed before probe review?
- Limitations / non-claims:
  - Paper label is advisory metadata only and does not imply higher readiness.

### 4. synthetic_pipeline_live_probe_eligible

- Candidate id: synthetic_pipeline_live_probe_eligible
- Title: Synthetic pipeline live-probe-eligible dossier
- Advisory label: live_probe_eligible
- Thesis/context: Synthetic fixture notes show live-probe metadata support while final authorization remains blocked.
- Uncertainty:
  - Probe support remains based on synthetic review assumptions.
- Failure modes:
  - Probe support may fail if the final authorization gate changes.
- Next questions / research needs:
  - Which synthetic approval note would resolve the final blocker?
- Limitations / non-claims:
  - Probe label is advisory metadata only and not final authorization.

### 5. synthetic_pipeline_live_authorized

- Candidate id: synthetic_pipeline_live_authorized
- Title: Synthetic pipeline live-authorized dossier
- Advisory label: live_authorized
- Thesis/context: Synthetic fixture notes show constructor-gated live authorization metadata with matching prepared support.
- Uncertainty:
  - Live authorization metadata is synthetic and limited to this fixture.
- Failure modes:
  - Live authorization metadata may be misread outside this fixture.
- Next questions / research needs:
  - Which synthetic reviewer would re-check the gate metadata?
- Limitations / non-claims:
  - Live label remains advisory metadata and does not create capital authority.

## Strategy Eligibility

### 1. synthetic_pipeline_watchlist_only

- Candidate id: synthetic_pipeline_watchlist_only
- Mandate id: synthetic_pipeline_mandate_watchlist_live
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_pipeline_strategy_watchlist_artifact
  - synthetic_pipeline_strategy_watchlist_definition
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: true
  - live_authorized: true
- Blocking reasons:
  - None recorded.
- Limitations:
  - Strategy metadata is intentionally more permissive than the watchlist label.

### 2. synthetic_pipeline_paper_eligible

- Candidate id: synthetic_pipeline_paper_eligible
- Mandate id: synthetic_pipeline_mandate_paper
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_pipeline_strategy_paper_artifact
  - synthetic_pipeline_strategy_paper_definition
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: false
  - live_authorized: false
- Blocking reasons:
  - Synthetic probe mandate review remains closed.
- Limitations:
  - Paper strategy metadata is not probe readiness.

### 3. synthetic_pipeline_live_probe_eligible

- Candidate id: synthetic_pipeline_live_probe_eligible
- Mandate id: synthetic_pipeline_mandate_probe
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_pipeline_strategy_probe_artifact
  - synthetic_pipeline_strategy_probe_definition
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: true
  - live_authorized: false
- Blocking reasons:
  - Synthetic final mandate review remains closed.
- Limitations:
  - Probe strategy metadata is not final authorization.

### 4. synthetic_pipeline_live_authorized

- Candidate id: synthetic_pipeline_live_authorized
- Mandate id: synthetic_pipeline_mandate_live
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_pipeline_strategy_live_artifact
  - synthetic_pipeline_strategy_live_definition
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: true
  - live_authorized: true
- Blocking reasons:
  - None recorded.
- Limitations:
  - Live strategy status is synthetic metadata only.

## Risk Authority

### 1. synthetic_pipeline_watchlist_only

- Candidate id: synthetic_pipeline_watchlist_only
- Authority id: synthetic_pipeline_authority_watchlist_live
- Authority flags:
  - paper_allowed: true
  - live_probe_allowed: true
  - live_authorized: true
- Blocking reasons:
  - None recorded.
- Limitations:
  - Risk metadata is intentionally more permissive than the watchlist label.

### 2. synthetic_pipeline_paper_eligible

- Candidate id: synthetic_pipeline_paper_eligible
- Authority id: synthetic_pipeline_authority_paper
- Authority flags:
  - paper_allowed: true
  - live_probe_allowed: false
  - live_authorized: false
- Blocking reasons:
  - Synthetic probe authority review remains closed.
- Limitations:
  - Paper risk metadata is not probe readiness.

### 3. synthetic_pipeline_live_probe_eligible

- Candidate id: synthetic_pipeline_live_probe_eligible
- Authority id: synthetic_pipeline_authority_probe
- Authority flags:
  - paper_allowed: true
  - live_probe_allowed: true
  - live_authorized: false
- Blocking reasons:
  - Synthetic final authority review remains closed.
- Limitations:
  - Probe risk metadata is not final authorization.

### 4. synthetic_pipeline_live_authorized

- Candidate id: synthetic_pipeline_live_authorized
- Authority id: synthetic_pipeline_authority_live
- Authority flags:
  - paper_allowed: true
  - live_probe_allowed: true
  - live_authorized: true
- Blocking reasons:
  - None recorded.
- Limitations:
  - Live risk status is synthetic metadata only.

## Non-Claims

- The brief does not validate profitability.
- `paper_eligible` does not imply live readiness.
- `live_probe_eligible` is operational eligibility only.
- `live_authorized` must remain constructor-gated by strategy eligibility and risk authority.
- The brief does not create broker, portfolio, order, fill, execution, or runtime behavior.
"""


_EXPECTED_SYNTHETIC_PIPELINE_BOARD_SUMMARY_MARKDOWN = """# Advisory Operating Board Summary

As-of date: 2026-01-16

Advisory status:
This board is advisory metadata only. It is not a trading recommendation, not a signal, not an order request, and not live-trading authority.

## Candidate Counts

- research_only: 1
- watchlist_only: 1
- paper_eligible: 1
- live_probe_eligible: 1
- live_authorized: 1

## Candidate Groups

### Research Only (research_only)

- synthetic_pipeline_research_only

### Watchlist Only (watchlist_only)

- synthetic_pipeline_watchlist_only

### Paper Eligible (paper_eligible)

- synthetic_pipeline_paper_eligible

### Live Probe Eligible (live_probe_eligible)

- synthetic_pipeline_live_probe_eligible

### Live Authorized (live_authorized)

- synthetic_pipeline_live_authorized

## Research Queue

- synthetic_pipeline_research_only

## Watchlist

- synthetic_pipeline_watchlist_only

## Paper-Eligible Board IDs

- synthetic_pipeline_paper_eligible

## Live-Probe-Eligible Board IDs

- synthetic_pipeline_live_probe_eligible

## Live-Authorized Metadata

Live-authorized board ids are metadata only and do not create trading authority.

### Board IDs

- synthetic_pipeline_live_authorized

### Source Status

- synthetic_pipeline_research_only: advisory_label=research_only; strategy_status_present=false; strategy_live_authorized=false; risk_status_present=false; risk_live_authorized=false; label_live_authorized=false
- synthetic_pipeline_watchlist_only: advisory_label=watchlist_only; strategy_status_present=true; strategy_live_authorized=true; risk_status_present=true; risk_live_authorized=true; label_live_authorized=false
- synthetic_pipeline_paper_eligible: advisory_label=paper_eligible; strategy_status_present=true; strategy_live_authorized=false; risk_status_present=true; risk_live_authorized=false; label_live_authorized=false
- synthetic_pipeline_live_probe_eligible: advisory_label=live_probe_eligible; strategy_status_present=true; strategy_live_authorized=false; risk_status_present=true; risk_live_authorized=false; label_live_authorized=false
- synthetic_pipeline_live_authorized: advisory_label=live_authorized; strategy_status_present=true; strategy_live_authorized=true; risk_status_present=true; risk_live_authorized=true; label_live_authorized=true

## Strategy Blockers

- synthetic_pipeline_paper_eligible: mandate_id=synthetic_pipeline_mandate_paper; Synthetic probe mandate review remains closed.
- synthetic_pipeline_live_probe_eligible: mandate_id=synthetic_pipeline_mandate_probe; Synthetic final mandate review remains closed.

## Risk Blockers

- synthetic_pipeline_paper_eligible: authority_id=synthetic_pipeline_authority_paper; Synthetic probe authority review remains closed.
- synthetic_pipeline_live_probe_eligible: authority_id=synthetic_pipeline_authority_probe; Synthetic final authority review remains closed.

## Uncertainty

- synthetic_pipeline_research_only: Synthetic source notes have not been reconciled with a review checklist.
- synthetic_pipeline_watchlist_only: Optional support metadata is more permissive than the source label.
- synthetic_pipeline_paper_eligible: Paper support depends on synthetic evidence references only.
- synthetic_pipeline_live_probe_eligible: Probe support remains based on synthetic review assumptions.
- synthetic_pipeline_live_authorized: Live authorization metadata is synthetic and limited to this fixture.

## Failure Modes

- synthetic_pipeline_research_only: The research premise may be incomplete if fixture assumptions conflict.
- synthetic_pipeline_watchlist_only: Readers may overstate the optional support metadata if the label is ignored.
- synthetic_pipeline_paper_eligible: Paper support may miss a required synthetic probe constraint.
- synthetic_pipeline_live_probe_eligible: Probe support may fail if the final authorization gate changes.
- synthetic_pipeline_live_authorized: Live authorization metadata may be misread outside this fixture.

## Limitations

### Brief

- Advisory metadata only.

### Candidate

- synthetic_pipeline_research_only: Research-only label has no prepared strategy or risk support.
- synthetic_pipeline_watchlist_only: Watchlist label remains authoritative over optional support metadata.
- synthetic_pipeline_paper_eligible: Paper label is advisory metadata only and does not imply higher readiness.
- synthetic_pipeline_live_probe_eligible: Probe label is advisory metadata only and not final authorization.
- synthetic_pipeline_live_authorized: Live label remains advisory metadata and does not create capital authority.

### Strategy

- synthetic_pipeline_watchlist_only: mandate_id=synthetic_pipeline_mandate_watchlist_live; Strategy metadata is intentionally more permissive than the watchlist label.
- synthetic_pipeline_paper_eligible: mandate_id=synthetic_pipeline_mandate_paper; Paper strategy metadata is not probe readiness.
- synthetic_pipeline_live_probe_eligible: mandate_id=synthetic_pipeline_mandate_probe; Probe strategy metadata is not final authorization.
- synthetic_pipeline_live_authorized: mandate_id=synthetic_pipeline_mandate_live; Live strategy status is synthetic metadata only.

### Risk

- synthetic_pipeline_watchlist_only: authority_id=synthetic_pipeline_authority_watchlist_live; Risk metadata is intentionally more permissive than the watchlist label.
- synthetic_pipeline_paper_eligible: authority_id=synthetic_pipeline_authority_paper; Paper risk metadata is not probe readiness.
- synthetic_pipeline_live_probe_eligible: authority_id=synthetic_pipeline_authority_probe; Probe risk metadata is not final authorization.
- synthetic_pipeline_live_authorized: authority_id=synthetic_pipeline_authority_live; Live risk status is synthetic metadata only.

## Non-Claims

- The board does not validate profitability.
- The board does not rank or score candidates.
- The board does not create trading recommendations.
- `paper_eligible` does not imply live readiness.
- `live_probe_eligible` is operational eligibility only.
- `live_authorized` remains constructor-gated by strategy eligibility and risk authority.
- The board does not create broker, portfolio, order, fill, execution, or runtime behavior.
### Source Summary Non-Claims

- This summary is advisory metadata only.
- It reports existing labels, blockers, uncertainty, failure modes, and limitations only.
- It does not create live action authority or validate profitability.
- It does not discover candidates or change their source status.
"""
