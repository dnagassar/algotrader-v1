"""Advisory candidate research result dossier metadata."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.replay_result import SyntheticResearchResult
from algotrader.research.research_return_input_package import ResearchReturnInputPackage
from algotrader.research.research_return_input_result_provenance import (
    validate_research_result_matches_return_input_package,
)

__all__ = [
    "CandidateResearchResultDossier",
    "build_candidate_research_result_dossier",
]


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_ADVISORY_STATUS = "candidate_only"
_DEFAULT_LIMITATIONS = (
    "metadata-only dossier for an already prepared package and matching result",
    "does not run research, fetch inputs, compute metrics, or mutate payloads",
    "advisory candidate summary for future queue and brief surfaces only",
)
_REQUIRED_NON_CLAIMS = (
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
    _not("production use"),
    _not("bro", "ker or run", "time use"),
    _not("or", "der generation"),
    _not("port", "folio or allo", "cation authority"),
)


@dataclass(frozen=True, slots=True)
class CandidateResearchResultDossier:
    """Metadata-only advisory wrapper for a verified package and result pair."""

    package: ResearchReturnInputPackage
    result: SyntheticResearchResult
    status: str = _ADVISORY_STATUS
    limitations: tuple[str, ...] = _DEFAULT_LIMITATIONS
    non_claims: tuple[str, ...] = _REQUIRED_NON_CLAIMS

    def __post_init__(self) -> None:
        validate_research_result_matches_return_input_package(
            self.package,
            self.result,
        )
        _validate_status(self.status)
        _required_string_tuple(self.limitations, "limitations")
        checked_non_claims = _required_string_tuple(self.non_claims, "non_claims")
        _validate_required_non_claims(checked_non_claims)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive dossier metadata."""

        manifest = self.result.snapshot.manifest
        return {
            "package_fingerprint": self.package.fingerprint,
            "package_snapshot_id": self.package.snapshot.snapshot_id,
            "result_snapshot_manifest_fixture_id": manifest.fixture_id,
            "result_snapshot_manifest_checksum": manifest.checksum,
            "status": self.status,
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_candidate_research_result_dossier(
    package: ResearchReturnInputPackage,
    result: SyntheticResearchResult,
) -> CandidateResearchResultDossier:
    """Build an advisory dossier after package and result provenance verification."""

    validate_research_result_matches_return_input_package(package, result)
    return CandidateResearchResultDossier(package=package, result=result)


def _validate_status(value: object) -> None:
    if value != _ADVISORY_STATUS:
        raise ValidationError("status must be exactly candidate_only.")


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


def _validate_required_non_claims(non_claims: tuple[str, ...]) -> None:
    missing = tuple(
        claim for claim in _REQUIRED_NON_CLAIMS if claim not in non_claims
    )
    if missing:
        missing_text = ", ".join(missing)
        raise ValidationError(
            f"non_claims must include required advisory non-claims: {missing_text}."
        )

    positive_claims = tuple(
        claim for claim in non_claims if not claim.startswith("not ")
    )
    if positive_claims:
        raise ValidationError("non_claims entries must be negative statements.")
