"""Metadata-only source snapshots for future advisory candidate dossiers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.advisory.operating_brief import AdvisoryLabel
from algotrader.errors import ValidationError

__all__ = [
    "CandidateDossierSnapshot",
]


@dataclass(frozen=True, slots=True)
class CandidateDossierSnapshot:
    """Upstream metadata source for a future ResearchCandidateDossier."""

    candidate_id: str
    as_of_date: date
    title: str
    summary: str
    source_type: str
    source_ids: tuple[str, ...]
    proposed_label: AdvisoryLabel
    label_source: str
    label_rationale: tuple[str, ...]
    strategy_id: str
    mandate_id: str
    universe_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    uncertainty_factors: tuple[str, ...]
    failure_modes: tuple[str, ...]
    next_questions: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive candidate snapshot metadata."""
        return {
            "candidate_id": self.candidate_id,
            "as_of_date": _serialize_plain_date(self.as_of_date),
            "title": self.title,
            "summary": self.summary,
            "source_type": self.source_type,
            "source_ids": list(self.source_ids),
            "proposed_label": self.proposed_label.value,
            "label_source": self.label_source,
            "label_rationale": list(self.label_rationale),
            "strategy_id": self.strategy_id,
            "mandate_id": self.mandate_id,
            "universe_refs": list(self.universe_refs),
            "evidence_refs": list(self.evidence_refs),
            "uncertainty_factors": list(self.uncertainty_factors),
            "failure_modes": list(self.failure_modes),
            "next_questions": list(self.next_questions),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _required_string(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
        )
        object.__setattr__(self, "title", _required_string(self.title, "title"))
        object.__setattr__(
            self,
            "summary",
            _required_string(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "source_type",
            _source_type(self.source_type),
        )
        object.__setattr__(
            self,
            "source_ids",
            _string_tuple(self.source_ids, "source_ids"),
        )
        object.__setattr__(
            self,
            "proposed_label",
            _proposed_label(self.proposed_label),
        )
        object.__setattr__(
            self,
            "label_source",
            _label_source(self.label_source),
        )
        object.__setattr__(
            self,
            "label_rationale",
            _string_tuple(self.label_rationale, "label_rationale"),
        )
        object.__setattr__(
            self,
            "strategy_id",
            _string_or_empty(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "mandate_id",
            _string_or_empty(self.mandate_id, "mandate_id"),
        )
        object.__setattr__(
            self,
            "universe_refs",
            _string_tuple(self.universe_refs, "universe_refs"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self,
            "uncertainty_factors",
            _string_tuple(self.uncertainty_factors, "uncertainty_factors"),
        )
        object.__setattr__(
            self,
            "failure_modes",
            _string_tuple(self.failure_modes, "failure_modes"),
        )
        object.__setattr__(
            self,
            "next_questions",
            _string_tuple(self.next_questions, "next_questions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _string_tuple(self.non_claims, "non_claims"),
        )
        _validate_non_claim_language(self.non_claims)
        _validate_label_authority(self)


_ALLOWED_SOURCE_TYPES = frozenset(
    (
        "synthetic",
        "manual",
        "external_research",
        "governance_snapshot",
        "research_log",
        "other",
    )
)

_ALLOWED_LABEL_SOURCES = frozenset(
    (
        "deterministic_governance",
        "deterministic_risk",
        "human_review",
        "synthetic_fixture",
        "external_research_proposed",
        "ai_proposed",
        "other",
    )
)

_ELEVATED_LABELS = frozenset(
    (
        AdvisoryLabel.PAPER_ELIGIBLE,
        AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
        AdvisoryLabel.LIVE_AUTHORIZED,
    )
)

_ELEVATED_LABEL_SOURCES = frozenset(
    (
        "deterministic_governance",
        "deterministic_risk",
        "human_review",
        "synthetic_fixture",
    )
)

_RESTRICTED_NON_CLAIM_TERMS = frozenset(
    (
        "buy",
        "hold",
        "recommendation",
        "sell",
        "trade",
        "trading",
    )
)


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _string_or_empty(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value.strip()


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")
    return value


def _serialize_plain_date(value: object) -> str:
    if type(value) is not date:
        raise ValidationError("as_of_date must be a date.")
    return value.isoformat()


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValidationError(f"{field_name} must be an iterable of strings.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be an iterable of strings.") from exc

    return tuple(
        _required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def _source_type(value: object) -> str:
    source_type = _required_string(value, "source_type")
    if source_type not in _ALLOWED_SOURCE_TYPES:
        raise ValidationError("source_type must be an allowed source type.")
    return source_type


def _label_source(value: object) -> str:
    label_source = _required_string(value, "label_source")
    if label_source not in _ALLOWED_LABEL_SOURCES:
        raise ValidationError("label_source must be an allowed label source.")
    return label_source


def _proposed_label(value: object) -> AdvisoryLabel:
    if type(value) is not AdvisoryLabel:
        raise ValidationError("proposed_label must be an AdvisoryLabel.")
    return value


def _validate_non_claim_language(non_claims: tuple[str, ...]) -> None:
    for non_claim in non_claims:
        words = frozenset(
            part.strip(".,;:!?()[]{}").lower() for part in non_claim.split()
        )
        for term in _RESTRICTED_NON_CLAIM_TERMS:
            if term in words:
                raise ValidationError(
                    "non_claims must not contain trading recommendation language."
                )


def _validate_label_authority(snapshot: CandidateDossierSnapshot) -> None:
    if snapshot.proposed_label not in _ELEVATED_LABELS:
        return

    if snapshot.label_source not in _ELEVATED_LABEL_SOURCES:
        raise ValidationError(
            f"{snapshot.proposed_label.value} requires deterministic or reviewed "
            "label_source."
        )

    if not snapshot.strategy_id:
        raise ValidationError(f"{snapshot.proposed_label.value} requires strategy_id.")
    if not snapshot.non_claims:
        raise ValidationError(f"{snapshot.proposed_label.value} requires non_claims.")

    if snapshot.proposed_label in (
        AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
        AdvisoryLabel.LIVE_AUTHORIZED,
    ) and not snapshot.mandate_id:
        raise ValidationError(f"{snapshot.proposed_label.value} requires mandate_id.")

    if (
        snapshot.proposed_label == AdvisoryLabel.LIVE_AUTHORIZED
        and not snapshot.evidence_refs
    ):
        raise ValidationError("live_authorized requires evidence_refs.")
