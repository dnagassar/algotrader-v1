"""Synthetic advisory operating brief fixture for deterministic tests."""

from __future__ import annotations

from datetime import date

from algotrader.advisory import (
    AdvisoryLabel,
    OperatingBrief,
    OperatingBriefBoardSummary,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    build_operating_brief_board_summary,
)

__all__ = [
    "build_synthetic_advisory_operating_brief",
    "build_synthetic_advisory_operating_brief_summary",
    "expected_synthetic_operating_brief_board_summary_markdown",
    "expected_synthetic_operating_brief_markdown",
]


def build_synthetic_advisory_operating_brief() -> OperatingBrief:
    """Return one canonical local-only advisory operating brief example."""
    return OperatingBrief(
        brief_id="synthetic_advisory_operating_brief_2026_01_15",
        as_of_date=date(2026, 1, 15),
        dossiers=(
            ResearchCandidateDossier(
                candidate_id="synthetic_research_candidate",
                title="Synthetic research queue dossier",
                summary=(
                    "Synthetic local-only notes describe an unresolved advisory idea "
                    "for future review."
                ),
                advisory_label=AdvisoryLabel.RESEARCH_ONLY,
                uncertainty_factors=(
                    "Synthetic source notes have not been reconciled against an "
                    "approved evidence checklist.",
                ),
                failure_modes=(
                    "The advisory thesis may be invalid if source assumptions are "
                    "incomplete.",
                ),
                next_questions=(
                    "Which synthetic evidence artifact would be required before "
                    "watchlist review?",
                ),
                limitations=("Local fixture only; no external claim is made.",),
            ),
            ResearchCandidateDossier(
                candidate_id="synthetic_watchlist_candidate",
                title="Synthetic watchlist dossier",
                summary=(
                    "Synthetic local-only notes keep the candidate visible while "
                    "review details remain incomplete."
                ),
                advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
                uncertainty_factors=(
                    "The review question is illustrative and may omit required "
                    "production controls.",
                ),
                failure_modes=(
                    "The watchlist reason may become stale before a human review.",
                ),
                next_questions=(
                    "What additional synthetic review note would remove the "
                    "watchlist blocker?",
                ),
                limitations=(
                    "Advisory label is authoritative even when support metadata is "
                    "more permissive.",
                ),
            ),
            ResearchCandidateDossier(
                candidate_id="synthetic_paper_candidate",
                title="Synthetic paper eligibility dossier",
                summary=(
                    "Synthetic local-only notes show paper metadata support with "
                    "higher review still blocked."
                ),
                advisory_label=AdvisoryLabel.PAPER_ELIGIBLE,
                uncertainty_factors=(
                    "Paper metadata depends on a synthetic evidence package only.",
                ),
                failure_modes=(
                    "Paper support may overstate readiness if evidence gaps are "
                    "missed.",
                ),
                next_questions=(
                    "Which synthetic constraint must pass before probe metadata is "
                    "considered?",
                ),
                limitations=(
                    "Paper label is metadata only and does not imply higher "
                    "readiness.",
                ),
            ),
            ResearchCandidateDossier(
                candidate_id="synthetic_live_probe_candidate",
                title="Synthetic live probe eligibility dossier",
                summary=(
                    "Synthetic local-only notes show probe metadata support while "
                    "final authorization remains blocked."
                ),
                advisory_label=AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
                uncertainty_factors=(
                    "Probe readiness is based on synthetic controls rather than "
                    "deployed operations.",
                ),
                failure_modes=(
                    "Probe controls may fail to expose missing review constraints.",
                ),
                next_questions=(
                    "Which synthetic approval note would be required before live "
                    "authorization?",
                ),
                limitations=(
                    "Probe label is metadata only and does not imply final "
                    "authorization.",
                ),
            ),
            ResearchCandidateDossier(
                candidate_id="synthetic_live_authorized_candidate",
                title="Synthetic live authorization dossier",
                summary=(
                    "Synthetic local-only notes show constructor-gated live "
                    "authorization metadata only."
                ),
                advisory_label=AdvisoryLabel.LIVE_AUTHORIZED,
                uncertainty_factors=(
                    "Live authorization metadata is synthetic and does not establish "
                    "real readiness.",
                ),
                failure_modes=(
                    "Authorization metadata may be misread as permission outside "
                    "this local fixture.",
                ),
                next_questions=(
                    "Which synthetic review owner would re-check the gate metadata?",
                ),
                limitations=(
                    "Live label remains advisory metadata only and is not action "
                    "authority.",
                ),
            ),
        ),
        strategy_statuses=(
            StrategyEligibilityStatus(
                candidate_id="synthetic_research_candidate",
                mandate_id=None,
                mandate_approved=False,
                evidence_approved=False,
                evidence_refs=(),
                paper_eligible=False,
                live_probe_eligible=False,
                live_authorized=False,
                blocking_reasons=(
                    "Synthetic mandate review is not approved.",
                    "Synthetic evidence checklist is incomplete.",
                ),
                limitations=(
                    "Strategy metadata is illustrative and cannot authorize action.",
                ),
            ),
            StrategyEligibilityStatus(
                candidate_id="synthetic_watchlist_candidate",
                mandate_id="synthetic_strategy_mandate_live_001",
                mandate_approved=True,
                evidence_approved=True,
                evidence_refs=("synthetic_watchlist_evidence_ref_001",),
                paper_eligible=True,
                live_probe_eligible=True,
                live_authorized=True,
                blocking_reasons=(),
                limitations=(
                    "Strategy metadata is intentionally more permissive than the "
                    "watchlist label.",
                ),
            ),
            StrategyEligibilityStatus(
                candidate_id="synthetic_paper_candidate",
                mandate_id="synthetic_strategy_mandate_paper_001",
                mandate_approved=True,
                evidence_approved=True,
                evidence_refs=("synthetic_paper_evidence_ref_001",),
                paper_eligible=True,
                live_probe_eligible=False,
                live_authorized=False,
                blocking_reasons=(
                    "Synthetic probe mandate review is not approved.",
                ),
                limitations=("Paper strategy metadata is not live readiness.",),
            ),
            StrategyEligibilityStatus(
                candidate_id="synthetic_live_probe_candidate",
                mandate_id="synthetic_strategy_mandate_probe_001",
                mandate_approved=True,
                evidence_approved=True,
                evidence_refs=("synthetic_probe_evidence_ref_001",),
                paper_eligible=True,
                live_probe_eligible=True,
                live_authorized=False,
                blocking_reasons=(
                    "Synthetic live authorization review is not approved.",
                ),
                limitations=(
                    "Probe strategy metadata is not final authorization.",
                ),
            ),
            StrategyEligibilityStatus(
                candidate_id="synthetic_live_authorized_candidate",
                mandate_id="synthetic_strategy_mandate_live_002",
                mandate_approved=True,
                evidence_approved=True,
                evidence_refs=("synthetic_live_evidence_ref_001",),
                paper_eligible=True,
                live_probe_eligible=True,
                live_authorized=True,
                blocking_reasons=(),
                limitations=("Live strategy status is synthetic metadata only.",),
            ),
        ),
        risk_statuses=(
            RiskAuthorityStatus(
                candidate_id="synthetic_research_candidate",
                authority_id=None,
                paper_allowed=False,
                live_probe_allowed=False,
                live_authorized=False,
                blocking_reasons=("Synthetic risk review is not approved.",),
                limitations=(
                    "Risk metadata is illustrative and cannot authorize action.",
                ),
            ),
            RiskAuthorityStatus(
                candidate_id="synthetic_watchlist_candidate",
                authority_id="synthetic_risk_authority_live_001",
                paper_allowed=True,
                live_probe_allowed=True,
                live_authorized=True,
                blocking_reasons=(),
                limitations=(
                    "Risk metadata is intentionally more permissive than the "
                    "watchlist label.",
                ),
            ),
            RiskAuthorityStatus(
                candidate_id="synthetic_paper_candidate",
                authority_id="synthetic_risk_authority_paper_001",
                paper_allowed=True,
                live_probe_allowed=False,
                live_authorized=False,
                blocking_reasons=(
                    "Synthetic probe authority review is not approved.",
                ),
                limitations=("Paper risk metadata is not live readiness.",),
            ),
            RiskAuthorityStatus(
                candidate_id="synthetic_live_probe_candidate",
                authority_id="synthetic_risk_authority_probe_001",
                paper_allowed=True,
                live_probe_allowed=True,
                live_authorized=False,
                blocking_reasons=(
                    "Synthetic live authority review is not approved.",
                ),
                limitations=("Probe risk metadata is not final authorization.",),
            ),
            RiskAuthorityStatus(
                candidate_id="synthetic_live_authorized_candidate",
                authority_id="synthetic_risk_authority_live_002",
                paper_allowed=True,
                live_probe_allowed=True,
                live_authorized=True,
                blocking_reasons=(),
                limitations=("Live risk status is synthetic metadata only.",),
            ),
        ),
        limitations=(
            "Synthetic local-only fixture; no external data source is consulted.",
            "Labels, blockers, uncertainty, and non-claims are examples for "
            "deterministic tests only.",
            "No profitability, readiness, or external suitability claim is made.",
        ),
    )


def build_synthetic_advisory_operating_brief_summary() -> (
    OperatingBriefBoardSummary
):
    """Return a board summary built from a new canonical synthetic brief."""
    return build_operating_brief_board_summary(
        build_synthetic_advisory_operating_brief()
    )


def expected_synthetic_operating_brief_markdown() -> str:
    """Return the pinned OperatingBrief Markdown for the synthetic fixture."""
    return _EXPECTED_OPERATING_BRIEF_MARKDOWN


def expected_synthetic_operating_brief_board_summary_markdown() -> str:
    """Return the pinned OperatingBriefBoardSummary Markdown fixture."""
    return _EXPECTED_OPERATING_BRIEF_BOARD_SUMMARY_MARKDOWN


_EXPECTED_OPERATING_BRIEF_MARKDOWN = """# Advisory Operating Brief

As-of date: 2026-01-15

Advisory status:
This brief is advisory metadata only. It is not a trading recommendation, not a signal, not an order request, and not live-trading authority.

## Candidate Dossiers

### 1. synthetic_research_candidate

- Candidate id: synthetic_research_candidate
- Title: Synthetic research queue dossier
- Advisory label: research_only
- Thesis/context: Synthetic local-only notes describe an unresolved advisory idea for future review.
- Uncertainty:
  - Synthetic source notes have not been reconciled against an approved evidence checklist.
- Failure modes:
  - The advisory thesis may be invalid if source assumptions are incomplete.
- Next questions / research needs:
  - Which synthetic evidence artifact would be required before watchlist review?
- Limitations / non-claims:
  - Local fixture only; no external claim is made.

### 2. synthetic_watchlist_candidate

- Candidate id: synthetic_watchlist_candidate
- Title: Synthetic watchlist dossier
- Advisory label: watchlist_only
- Thesis/context: Synthetic local-only notes keep the candidate visible while review details remain incomplete.
- Uncertainty:
  - The review question is illustrative and may omit required production controls.
- Failure modes:
  - The watchlist reason may become stale before a human review.
- Next questions / research needs:
  - What additional synthetic review note would remove the watchlist blocker?
- Limitations / non-claims:
  - Advisory label is authoritative even when support metadata is more permissive.

### 3. synthetic_paper_candidate

- Candidate id: synthetic_paper_candidate
- Title: Synthetic paper eligibility dossier
- Advisory label: paper_eligible
- Thesis/context: Synthetic local-only notes show paper metadata support with higher review still blocked.
- Uncertainty:
  - Paper metadata depends on a synthetic evidence package only.
- Failure modes:
  - Paper support may overstate readiness if evidence gaps are missed.
- Next questions / research needs:
  - Which synthetic constraint must pass before probe metadata is considered?
- Limitations / non-claims:
  - Paper label is metadata only and does not imply higher readiness.

### 4. synthetic_live_probe_candidate

- Candidate id: synthetic_live_probe_candidate
- Title: Synthetic live probe eligibility dossier
- Advisory label: live_probe_eligible
- Thesis/context: Synthetic local-only notes show probe metadata support while final authorization remains blocked.
- Uncertainty:
  - Probe readiness is based on synthetic controls rather than deployed operations.
- Failure modes:
  - Probe controls may fail to expose missing review constraints.
- Next questions / research needs:
  - Which synthetic approval note would be required before live authorization?
- Limitations / non-claims:
  - Probe label is metadata only and does not imply final authorization.

### 5. synthetic_live_authorized_candidate

- Candidate id: synthetic_live_authorized_candidate
- Title: Synthetic live authorization dossier
- Advisory label: live_authorized
- Thesis/context: Synthetic local-only notes show constructor-gated live authorization metadata only.
- Uncertainty:
  - Live authorization metadata is synthetic and does not establish real readiness.
- Failure modes:
  - Authorization metadata may be misread as permission outside this local fixture.
- Next questions / research needs:
  - Which synthetic review owner would re-check the gate metadata?
- Limitations / non-claims:
  - Live label remains advisory metadata only and is not action authority.

## Strategy Eligibility

### 1. synthetic_research_candidate

- Candidate id: synthetic_research_candidate
- Mandate id: not set
- Mandate approved: false
- Evidence approved: false
- Evidence refs:
  - None recorded.
- Eligibility flags:
  - paper_eligible: false
  - live_probe_eligible: false
  - live_authorized: false
- Blocking reasons:
  - Synthetic mandate review is not approved.
  - Synthetic evidence checklist is incomplete.
- Limitations:
  - Strategy metadata is illustrative and cannot authorize action.

### 2. synthetic_watchlist_candidate

- Candidate id: synthetic_watchlist_candidate
- Mandate id: synthetic_strategy_mandate_live_001
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_watchlist_evidence_ref_001
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: true
  - live_authorized: true
- Blocking reasons:
  - None recorded.
- Limitations:
  - Strategy metadata is intentionally more permissive than the watchlist label.

### 3. synthetic_paper_candidate

- Candidate id: synthetic_paper_candidate
- Mandate id: synthetic_strategy_mandate_paper_001
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_paper_evidence_ref_001
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: false
  - live_authorized: false
- Blocking reasons:
  - Synthetic probe mandate review is not approved.
- Limitations:
  - Paper strategy metadata is not live readiness.

### 4. synthetic_live_probe_candidate

- Candidate id: synthetic_live_probe_candidate
- Mandate id: synthetic_strategy_mandate_probe_001
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_probe_evidence_ref_001
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: true
  - live_authorized: false
- Blocking reasons:
  - Synthetic live authorization review is not approved.
- Limitations:
  - Probe strategy metadata is not final authorization.

### 5. synthetic_live_authorized_candidate

- Candidate id: synthetic_live_authorized_candidate
- Mandate id: synthetic_strategy_mandate_live_002
- Mandate approved: true
- Evidence approved: true
- Evidence refs:
  - synthetic_live_evidence_ref_001
- Eligibility flags:
  - paper_eligible: true
  - live_probe_eligible: true
  - live_authorized: true
- Blocking reasons:
  - None recorded.
- Limitations:
  - Live strategy status is synthetic metadata only.

## Risk Authority

### 1. synthetic_research_candidate

- Candidate id: synthetic_research_candidate
- Authority id: not set
- Authority flags:
  - paper_allowed: false
  - live_probe_allowed: false
  - live_authorized: false
- Blocking reasons:
  - Synthetic risk review is not approved.
- Limitations:
  - Risk metadata is illustrative and cannot authorize action.

### 2. synthetic_watchlist_candidate

- Candidate id: synthetic_watchlist_candidate
- Authority id: synthetic_risk_authority_live_001
- Authority flags:
  - paper_allowed: true
  - live_probe_allowed: true
  - live_authorized: true
- Blocking reasons:
  - None recorded.
- Limitations:
  - Risk metadata is intentionally more permissive than the watchlist label.

### 3. synthetic_paper_candidate

- Candidate id: synthetic_paper_candidate
- Authority id: synthetic_risk_authority_paper_001
- Authority flags:
  - paper_allowed: true
  - live_probe_allowed: false
  - live_authorized: false
- Blocking reasons:
  - Synthetic probe authority review is not approved.
- Limitations:
  - Paper risk metadata is not live readiness.

### 4. synthetic_live_probe_candidate

- Candidate id: synthetic_live_probe_candidate
- Authority id: synthetic_risk_authority_probe_001
- Authority flags:
  - paper_allowed: true
  - live_probe_allowed: true
  - live_authorized: false
- Blocking reasons:
  - Synthetic live authority review is not approved.
- Limitations:
  - Probe risk metadata is not final authorization.

### 5. synthetic_live_authorized_candidate

- Candidate id: synthetic_live_authorized_candidate
- Authority id: synthetic_risk_authority_live_002
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


_EXPECTED_OPERATING_BRIEF_BOARD_SUMMARY_MARKDOWN = """# Advisory Operating Board Summary

As-of date: 2026-01-15

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

- synthetic_research_candidate

### Watchlist Only (watchlist_only)

- synthetic_watchlist_candidate

### Paper Eligible (paper_eligible)

- synthetic_paper_candidate

### Live Probe Eligible (live_probe_eligible)

- synthetic_live_probe_candidate

### Live Authorized (live_authorized)

- synthetic_live_authorized_candidate

## Research Queue

- synthetic_research_candidate

## Watchlist

- synthetic_watchlist_candidate

## Paper-Eligible Board IDs

- synthetic_paper_candidate

## Live-Probe-Eligible Board IDs

- synthetic_live_probe_candidate

## Live-Authorized Metadata

Live-authorized board ids are metadata only and do not create trading authority.

### Board IDs

- synthetic_live_authorized_candidate

### Source Status

- synthetic_research_candidate: advisory_label=research_only; strategy_status_present=true; strategy_live_authorized=false; risk_status_present=true; risk_live_authorized=false; label_live_authorized=false
- synthetic_watchlist_candidate: advisory_label=watchlist_only; strategy_status_present=true; strategy_live_authorized=true; risk_status_present=true; risk_live_authorized=true; label_live_authorized=false
- synthetic_paper_candidate: advisory_label=paper_eligible; strategy_status_present=true; strategy_live_authorized=false; risk_status_present=true; risk_live_authorized=false; label_live_authorized=false
- synthetic_live_probe_candidate: advisory_label=live_probe_eligible; strategy_status_present=true; strategy_live_authorized=false; risk_status_present=true; risk_live_authorized=false; label_live_authorized=false
- synthetic_live_authorized_candidate: advisory_label=live_authorized; strategy_status_present=true; strategy_live_authorized=true; risk_status_present=true; risk_live_authorized=true; label_live_authorized=true

## Strategy Blockers

- synthetic_research_candidate: mandate_id=not set; Synthetic mandate review is not approved.; Synthetic evidence checklist is incomplete.
- synthetic_paper_candidate: mandate_id=synthetic_strategy_mandate_paper_001; Synthetic probe mandate review is not approved.
- synthetic_live_probe_candidate: mandate_id=synthetic_strategy_mandate_probe_001; Synthetic live authorization review is not approved.

## Risk Blockers

- synthetic_research_candidate: authority_id=not set; Synthetic risk review is not approved.
- synthetic_paper_candidate: authority_id=synthetic_risk_authority_paper_001; Synthetic probe authority review is not approved.
- synthetic_live_probe_candidate: authority_id=synthetic_risk_authority_probe_001; Synthetic live authority review is not approved.

## Uncertainty

- synthetic_research_candidate: Synthetic source notes have not been reconciled against an approved evidence checklist.
- synthetic_watchlist_candidate: The review question is illustrative and may omit required production controls.
- synthetic_paper_candidate: Paper metadata depends on a synthetic evidence package only.
- synthetic_live_probe_candidate: Probe readiness is based on synthetic controls rather than deployed operations.
- synthetic_live_authorized_candidate: Live authorization metadata is synthetic and does not establish real readiness.

## Failure Modes

- synthetic_research_candidate: The advisory thesis may be invalid if source assumptions are incomplete.
- synthetic_watchlist_candidate: The watchlist reason may become stale before a human review.
- synthetic_paper_candidate: Paper support may overstate readiness if evidence gaps are missed.
- synthetic_live_probe_candidate: Probe controls may fail to expose missing review constraints.
- synthetic_live_authorized_candidate: Authorization metadata may be misread as permission outside this local fixture.

## Limitations

### Brief

- Synthetic local-only fixture; no external data source is consulted.
- Labels, blockers, uncertainty, and non-claims are examples for deterministic tests only.
- No profitability, readiness, or external suitability claim is made.

### Candidate

- synthetic_research_candidate: Local fixture only; no external claim is made.
- synthetic_watchlist_candidate: Advisory label is authoritative even when support metadata is more permissive.
- synthetic_paper_candidate: Paper label is metadata only and does not imply higher readiness.
- synthetic_live_probe_candidate: Probe label is metadata only and does not imply final authorization.
- synthetic_live_authorized_candidate: Live label remains advisory metadata only and is not action authority.

### Strategy

- synthetic_research_candidate: mandate_id=not set; Strategy metadata is illustrative and cannot authorize action.
- synthetic_watchlist_candidate: mandate_id=synthetic_strategy_mandate_live_001; Strategy metadata is intentionally more permissive than the watchlist label.
- synthetic_paper_candidate: mandate_id=synthetic_strategy_mandate_paper_001; Paper strategy metadata is not live readiness.
- synthetic_live_probe_candidate: mandate_id=synthetic_strategy_mandate_probe_001; Probe strategy metadata is not final authorization.
- synthetic_live_authorized_candidate: mandate_id=synthetic_strategy_mandate_live_002; Live strategy status is synthetic metadata only.

### Risk

- synthetic_research_candidate: authority_id=not set; Risk metadata is illustrative and cannot authorize action.
- synthetic_watchlist_candidate: authority_id=synthetic_risk_authority_live_001; Risk metadata is intentionally more permissive than the watchlist label.
- synthetic_paper_candidate: authority_id=synthetic_risk_authority_paper_001; Paper risk metadata is not live readiness.
- synthetic_live_probe_candidate: authority_id=synthetic_risk_authority_probe_001; Probe risk metadata is not final authorization.
- synthetic_live_authorized_candidate: authority_id=synthetic_risk_authority_live_002; Live risk status is synthetic metadata only.

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
