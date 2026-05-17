"""Pure adapter from candidate source snapshots to advisory dossiers."""

from __future__ import annotations

from algotrader.advisory.candidate_snapshot import CandidateDossierSnapshot
from algotrader.advisory.operating_brief import ResearchCandidateDossier
from algotrader.errors import ValidationError

__all__ = [
    "candidate_snapshot_to_research_candidate_dossier",
]


def candidate_snapshot_to_research_candidate_dossier(
    snapshot: CandidateDossierSnapshot,
) -> ResearchCandidateDossier:
    """Adapt validated candidate snapshot metadata into an advisory dossier."""
    if not isinstance(snapshot, CandidateDossierSnapshot):
        raise ValidationError("snapshot must be a CandidateDossierSnapshot.")

    return ResearchCandidateDossier(
        candidate_id=snapshot.candidate_id,
        title=snapshot.title,
        summary=snapshot.summary,
        advisory_label=snapshot.proposed_label,
        uncertainty_factors=snapshot.uncertainty_factors,
        failure_modes=snapshot.failure_modes,
        next_questions=snapshot.next_questions,
        limitations=snapshot.limitations,
    )
