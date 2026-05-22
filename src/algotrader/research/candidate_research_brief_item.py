"""Advisory display item for candidate research result metadata."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
)

__all__ = [
    "CandidateResearchBriefItem",
    "build_candidate_research_brief_item",
]

_ITEM_TYPE = "candidate_research_result"
_ADVISORY_STATUS = "candidate_only"


@dataclass(frozen=True, slots=True)
class CandidateResearchBriefItem:
    """Metadata-only advisory item derived from a candidate result dossier."""

    dossier: CandidateResearchResultDossier
    item_type: str
    status: str
    headline: str
    summary_points: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        checked_dossier = _dossier(self.dossier)
        _validate_item_type(self.item_type)
        _validate_status(self.status)
        _required_string(self.headline, "headline")
        _required_string_tuple(self.summary_points, "summary_points")
        _validate_limitations(
            checked_dossier,
            _required_string_tuple(self.limitations, "limitations"),
        )
        _validate_non_claims(
            checked_dossier,
            _required_string_tuple(self.non_claims, "non_claims"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive brief item metadata."""

        manifest = self.dossier.result.snapshot.manifest
        return {
            "item_type": self.item_type,
            "status": self.status,
            "headline": self.headline,
            "summary_points": list(self.summary_points),
            "package_fingerprint": self.dossier.package.fingerprint,
            "package_snapshot_id": self.dossier.package.snapshot.snapshot_id,
            "result_snapshot_manifest_fixture_id": manifest.fixture_id,
            "result_snapshot_manifest_checksum": manifest.checksum,
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_candidate_research_brief_item(
    dossier: CandidateResearchResultDossier,
) -> CandidateResearchBriefItem:
    """Build a deterministic advisory brief item from an existing dossier."""

    checked_dossier = _dossier(dossier)
    manifest = checked_dossier.result.snapshot.manifest
    snapshot_id = checked_dossier.package.snapshot.snapshot_id

    return CandidateResearchBriefItem(
        dossier=checked_dossier,
        item_type=_ITEM_TYPE,
        status=_ADVISORY_STATUS,
        headline=f"Candidate research result metadata for {snapshot_id}",
        summary_points=(
            f"package snapshot id: {snapshot_id}",
            f"package fingerprint: {checked_dossier.package.fingerprint}",
            f"result manifest fixture id: {manifest.fixture_id}",
            f"result manifest checksum: {manifest.checksum}",
        ),
        limitations=checked_dossier.limitations,
        non_claims=checked_dossier.non_claims,
    )


def _dossier(value: object) -> CandidateResearchResultDossier:
    if not isinstance(value, CandidateResearchResultDossier):
        raise ValidationError("dossier must be a CandidateResearchResultDossier.")

    return value


def _validate_item_type(value: object) -> None:
    if value != _ITEM_TYPE:
        raise ValidationError("item_type must be exactly candidate_research_result.")


def _validate_status(value: object) -> None:
    if value != _ADVISORY_STATUS:
        raise ValidationError("status must be exactly candidate_only.")


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _required_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValidationError(f"{field_name} must be a non-empty tuple of strings.")

    if not values:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValidationError(f"{field_name}[{index}] must be a string.")
        if value != value.strip() or not value:
            raise ValidationError(f"{field_name}[{index}] must be a non-empty string.")

    return values


def _validate_limitations(
    dossier: CandidateResearchResultDossier,
    limitations: tuple[str, ...],
) -> None:
    missing = tuple(value for value in dossier.limitations if value not in limitations)
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"limitations must carry forward dossier limitations: {missing_text}."
        )


def _validate_non_claims(
    dossier: CandidateResearchResultDossier,
    non_claims: tuple[str, ...],
) -> None:
    missing = tuple(value for value in dossier.non_claims if value not in non_claims)
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"non_claims must carry forward dossier advisory non-claims: {missing_text}."
        )

    positive_claims = tuple(value for value in non_claims if not value.startswith("not "))
    if positive_claims:
        raise ValidationError("non_claims entries must be negative statements.")
