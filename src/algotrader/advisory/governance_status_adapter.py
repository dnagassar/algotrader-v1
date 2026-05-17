"""Pure adapters from governance snapshots to advisory status metadata."""

from __future__ import annotations

from algotrader.advisory.operating_brief import (
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
)
from algotrader.errors import ValidationError
from algotrader.governance import RiskAuthoritySnapshot, StrategyMandateSnapshot

__all__ = [
    "risk_authority_snapshot_to_risk_authority_status",
    "strategy_mandate_snapshot_to_strategy_eligibility_status",
]


def strategy_mandate_snapshot_to_strategy_eligibility_status(
    snapshot: StrategyMandateSnapshot,
    *,
    candidate_id: str,
) -> StrategyEligibilityStatus:
    """Adapt a strategy mandate snapshot into advisory strategy status."""
    if not isinstance(snapshot, StrategyMandateSnapshot):
        raise ValidationError("snapshot must be a StrategyMandateSnapshot.")

    return StrategyEligibilityStatus(
        candidate_id=_required_string(candidate_id, "candidate_id"),
        mandate_id=snapshot.mandate_id,
        mandate_approved=snapshot.mandate_approved,
        evidence_approved=snapshot.evidence_approved,
        evidence_refs=(
            snapshot.validated_research_artifact_ids
            + snapshot.validated_signal_definition_ids
        ),
        paper_eligible=snapshot.paper_eligible,
        live_probe_eligible=snapshot.live_probe_eligible,
        live_authorized=snapshot.live_authorized,
        blocking_reasons=snapshot.blocking_reasons,
        limitations=snapshot.limitations,
    )


def risk_authority_snapshot_to_risk_authority_status(
    snapshot: RiskAuthoritySnapshot,
    *,
    candidate_id: str,
) -> RiskAuthorityStatus:
    """Adapt a risk authority snapshot into advisory risk authority status."""
    if not isinstance(snapshot, RiskAuthoritySnapshot):
        raise ValidationError("snapshot must be a RiskAuthoritySnapshot.")

    return RiskAuthorityStatus(
        candidate_id=_required_string(candidate_id, "candidate_id"),
        authority_id=snapshot.authority_id,
        paper_allowed=snapshot.paper_allowed,
        live_probe_allowed=snapshot.live_probe_allowed,
        live_authorized=snapshot.live_allowed,
        blocking_reasons=snapshot.blocking_reasons,
        limitations=snapshot.limitations,
    )


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized
