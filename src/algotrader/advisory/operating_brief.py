"""Immutable advisory metadata contracts for future operating briefs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from algotrader.errors import ValidationError

__all__ = [
    "AdvisoryLabel",
    "OperatingBrief",
    "ResearchCandidateDossier",
    "RiskAuthorityStatus",
    "StrategyEligibilityStatus",
]


class AdvisoryLabel(StrEnum):
    """Advisory-only label for a candidate dossier.

    `live_authorized` is metadata only; it never grants authority to execute,
    allocate, submit, size, or mutate portfolio state.
    """

    RESEARCH_ONLY = "research_only"
    WATCHLIST_ONLY = "watchlist_only"
    PAPER_ELIGIBLE = "paper_eligible"
    LIVE_PROBE_ELIGIBLE = "live_probe_eligible"
    LIVE_AUTHORIZED = "live_authorized"


@dataclass(frozen=True, slots=True)
class ResearchCandidateDossier:
    """Metadata-only description of a possible research candidate."""

    candidate_id: str
    title: str
    summary: str
    advisory_label: AdvisoryLabel
    uncertainty_factors: tuple[str, ...]
    failure_modes: tuple[str, ...]
    next_questions: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive advisory metadata."""
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "summary": self.summary,
            "advisory_label": self.advisory_label.value,
            "uncertainty_factors": list(self.uncertainty_factors),
            "failure_modes": list(self.failure_modes),
            "next_questions": list(self.next_questions),
            "limitations": list(self.limitations),
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _required_string(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(self, "title", _required_string(self.title, "title"))
        object.__setattr__(
            self,
            "summary",
            _required_string(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "advisory_label",
            _advisory_label(self.advisory_label),
        )
        object.__setattr__(
            self,
            "uncertainty_factors",
            _required_string_tuple(
                self.uncertainty_factors,
                "uncertainty_factors",
            ),
        )
        object.__setattr__(
            self,
            "failure_modes",
            _required_string_tuple(self.failure_modes, "failure_modes"),
        )
        object.__setattr__(
            self,
            "next_questions",
            _required_string_tuple(self.next_questions, "next_questions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _required_string_tuple(self.limitations, "limitations"),
        )


@dataclass(frozen=True, slots=True)
class StrategyEligibilityStatus:
    """Metadata-only strategy mandate and evidence status for a candidate."""

    candidate_id: str
    mandate_id: str | None
    mandate_approved: bool
    evidence_approved: bool
    evidence_refs: tuple[str, ...]
    paper_eligible: bool
    live_probe_eligible: bool
    live_authorized: bool
    blocking_reasons: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive strategy eligibility metadata."""
        return {
            "candidate_id": self.candidate_id,
            "mandate_id": self.mandate_id,
            "mandate_approved": self.mandate_approved,
            "evidence_approved": self.evidence_approved,
            "evidence_refs": list(self.evidence_refs),
            "paper_eligible": self.paper_eligible,
            "live_probe_eligible": self.live_probe_eligible,
            "live_authorized": self.live_authorized,
            "blocking_reasons": list(self.blocking_reasons),
            "limitations": list(self.limitations),
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _required_string(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "mandate_id",
            _optional_required_string(self.mandate_id, "mandate_id"),
        )
        object.__setattr__(
            self,
            "mandate_approved",
            _bool_value(self.mandate_approved, "mandate_approved"),
        )
        object.__setattr__(
            self,
            "evidence_approved",
            _bool_value(self.evidence_approved, "evidence_approved"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self,
            "paper_eligible",
            _bool_value(self.paper_eligible, "paper_eligible"),
        )
        object.__setattr__(
            self,
            "live_probe_eligible",
            _bool_value(self.live_probe_eligible, "live_probe_eligible"),
        )
        object.__setattr__(
            self,
            "live_authorized",
            _bool_value(self.live_authorized, "live_authorized"),
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _string_tuple(self.blocking_reasons, "blocking_reasons"),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        _validate_strategy_eligibility(self)


@dataclass(frozen=True, slots=True)
class RiskAuthorityStatus:
    """Metadata-only risk authority status for a candidate."""

    candidate_id: str
    authority_id: str | None
    paper_allowed: bool
    live_probe_allowed: bool
    live_authorized: bool
    blocking_reasons: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive risk authority metadata."""
        return {
            "candidate_id": self.candidate_id,
            "authority_id": self.authority_id,
            "paper_allowed": self.paper_allowed,
            "live_probe_allowed": self.live_probe_allowed,
            "live_authorized": self.live_authorized,
            "blocking_reasons": list(self.blocking_reasons),
            "limitations": list(self.limitations),
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _required_string(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "authority_id",
            _optional_required_string(self.authority_id, "authority_id"),
        )
        object.__setattr__(
            self,
            "paper_allowed",
            _bool_value(self.paper_allowed, "paper_allowed"),
        )
        object.__setattr__(
            self,
            "live_probe_allowed",
            _bool_value(self.live_probe_allowed, "live_probe_allowed"),
        )
        object.__setattr__(
            self,
            "live_authorized",
            _bool_value(self.live_authorized, "live_authorized"),
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _string_tuple(self.blocking_reasons, "blocking_reasons"),
        )
        object.__setattr__(
            self,
            "limitations",
            _required_string_tuple(self.limitations, "limitations"),
        )
        _validate_risk_authority(self)


@dataclass(frozen=True, slots=True)
class OperatingBrief:
    """Advisory-only bundle of candidate and authority metadata."""

    brief_id: str
    as_of_date: date
    dossiers: tuple[ResearchCandidateDossier, ...]
    strategy_statuses: tuple[StrategyEligibilityStatus, ...]
    risk_statuses: tuple[RiskAuthorityStatus, ...]
    limitations: tuple[str, ...]
    advisory_only: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive operating brief metadata."""
        return {
            "brief_id": self.brief_id,
            "as_of_date": _serialize_plain_date(self.as_of_date),
            "dossiers": [dossier.to_dict() for dossier in self.dossiers],
            "strategy_statuses": [
                status.to_dict() for status in self.strategy_statuses
            ],
            "risk_statuses": [status.to_dict() for status in self.risk_statuses],
            "limitations": list(self.limitations),
            "advisory_only": self.advisory_only,
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "brief_id",
            _required_string(self.brief_id, "brief_id"),
        )
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
        )
        object.__setattr__(
            self,
            "dossiers",
            _dossier_tuple(self.dossiers),
        )
        object.__setattr__(
            self,
            "strategy_statuses",
            _strategy_status_tuple(self.strategy_statuses),
        )
        object.__setattr__(
            self,
            "risk_statuses",
            _risk_status_tuple(self.risk_statuses),
        )
        object.__setattr__(
            self,
            "limitations",
            _required_string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "advisory_only",
            _required_true(self.advisory_only, "advisory_only"),
        )
        _validate_operating_brief(self)


_ACTIONABLE_LABELS = frozenset(
    (
        AdvisoryLabel.PAPER_ELIGIBLE,
        AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
        AdvisoryLabel.LIVE_AUTHORIZED,
    )
)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _optional_required_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _advisory_label(value: object) -> AdvisoryLabel:
    try:
        return AdvisoryLabel(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("advisory_label must be a supported AdvisoryLabel.") from exc


def _bool_value(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


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


def _required_string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    items = _string_tuple(values, field_name)
    if not items:
        raise ValidationError(f"{field_name} must include at least one entry.")
    return items


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")
    return value


def _serialize_plain_date(value: object) -> str:
    if type(value) is not date:
        raise ValidationError("as_of_date must be a date.")
    return value.isoformat()


def _required_true(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be exactly True.")
    return value


def _dossier_tuple(
    dossiers: Iterable[ResearchCandidateDossier],
) -> tuple[ResearchCandidateDossier, ...]:
    try:
        items = tuple(dossiers)
    except TypeError as exc:
        raise ValidationError(
            "dossiers must be an iterable of ResearchCandidateDossier."
        ) from exc

    for dossier in items:
        if not isinstance(dossier, ResearchCandidateDossier):
            raise ValidationError("dossiers must contain ResearchCandidateDossier.")

    return items


def _strategy_status_tuple(
    statuses: Iterable[StrategyEligibilityStatus],
) -> tuple[StrategyEligibilityStatus, ...]:
    try:
        items = tuple(statuses)
    except TypeError as exc:
        raise ValidationError(
            "strategy_statuses must be an iterable of StrategyEligibilityStatus."
        ) from exc

    for status in items:
        if not isinstance(status, StrategyEligibilityStatus):
            raise ValidationError(
                "strategy_statuses must contain StrategyEligibilityStatus."
            )

    return items


def _risk_status_tuple(
    statuses: Iterable[RiskAuthorityStatus],
) -> tuple[RiskAuthorityStatus, ...]:
    try:
        items = tuple(statuses)
    except TypeError as exc:
        raise ValidationError(
            "risk_statuses must be an iterable of RiskAuthorityStatus."
        ) from exc

    for status in items:
        if not isinstance(status, RiskAuthorityStatus):
            raise ValidationError("risk_statuses must contain RiskAuthorityStatus.")

    return items


def _validate_strategy_eligibility(status: StrategyEligibilityStatus) -> None:
    if status.mandate_approved and status.mandate_id is None:
        raise ValidationError("mandate_id is required when mandate_approved is True.")
    if status.evidence_approved and not status.evidence_refs:
        raise ValidationError("evidence_refs are required when evidence is approved.")

    if status.live_authorized and not status.live_probe_eligible:
        raise ValidationError("live_authorized requires live_probe_eligible.")
    if status.live_probe_eligible and not status.paper_eligible:
        raise ValidationError("live_probe_eligible requires paper_eligible.")

    eligibility_flags = (
        status.paper_eligible,
        status.live_probe_eligible,
        status.live_authorized,
    )
    if any(eligibility_flags) and not (
        status.mandate_approved and status.evidence_approved
    ):
        raise ValidationError(
            "strategy eligibility requires approved mandate and evidence."
        )
    if any(eligibility_flags) and status.mandate_id is None:
        raise ValidationError("strategy eligibility requires mandate_id.")
    if not status.live_authorized and not status.blocking_reasons:
        raise ValidationError(
            "blocking_reasons are required unless strategy is live_authorized."
        )


def _validate_risk_authority(status: RiskAuthorityStatus) -> None:
    if status.live_authorized and not status.live_probe_allowed:
        raise ValidationError("live_authorized requires live_probe_allowed.")
    if status.live_probe_allowed and not status.paper_allowed:
        raise ValidationError("live_probe_allowed requires paper_allowed.")

    authority_flags = (
        status.paper_allowed,
        status.live_probe_allowed,
        status.live_authorized,
    )
    if any(authority_flags) and status.authority_id is None:
        raise ValidationError("risk authority permission requires authority_id.")
    if not status.live_authorized and not status.blocking_reasons:
        raise ValidationError(
            "blocking_reasons are required unless risk authority is live_authorized."
        )


def _validate_operating_brief(brief: OperatingBrief) -> None:
    dossier_ids = _unique_candidate_ids(brief.dossiers, "dossiers")
    strategy_by_candidate = _unique_candidate_mapping(
        brief.strategy_statuses,
        "strategy_statuses",
    )
    risk_by_candidate = _unique_candidate_mapping(
        brief.risk_statuses,
        "risk_statuses",
    )

    _reject_unknown_status_candidates(dossier_ids, strategy_by_candidate, "strategy")
    _reject_unknown_status_candidates(dossier_ids, risk_by_candidate, "risk")

    for dossier in brief.dossiers:
        if dossier.advisory_label in _ACTIONABLE_LABELS:
            strategy_status = strategy_by_candidate.get(dossier.candidate_id)
            risk_status = risk_by_candidate.get(dossier.candidate_id)
            if strategy_status is None:
                raise ValidationError(
                    "actionable advisory labels require strategy eligibility support."
                )
            if risk_status is None:
                raise ValidationError(
                    "actionable advisory labels require risk authority support."
                )
            _validate_actionable_label_support(
                dossier.advisory_label,
                strategy_status,
                risk_status,
            )


def _unique_candidate_ids(
    dossiers: tuple[ResearchCandidateDossier, ...],
    field_name: str,
) -> frozenset[str]:
    seen: set[str] = set()
    for dossier in dossiers:
        if dossier.candidate_id in seen:
            raise ValidationError(f"{field_name} contains duplicate candidate_id.")
        seen.add(dossier.candidate_id)
    return frozenset(seen)


def _unique_candidate_mapping(
    statuses: tuple[StrategyEligibilityStatus, ...] | tuple[RiskAuthorityStatus, ...],
    field_name: str,
) -> dict[str, StrategyEligibilityStatus | RiskAuthorityStatus]:
    mapping: dict[str, StrategyEligibilityStatus | RiskAuthorityStatus] = {}
    for status in statuses:
        if status.candidate_id in mapping:
            raise ValidationError(f"{field_name} contains duplicate candidate_id.")
        mapping[status.candidate_id] = status
    return mapping


def _reject_unknown_status_candidates(
    dossier_ids: frozenset[str],
    statuses: dict[str, StrategyEligibilityStatus | RiskAuthorityStatus],
    status_name: str,
) -> None:
    unknown_ids = tuple(
        candidate_id for candidate_id in statuses if candidate_id not in dossier_ids
    )
    if unknown_ids:
        unknown = ", ".join(unknown_ids)
        raise ValidationError(f"{status_name} status candidate is not in dossiers: {unknown}.")


def _validate_actionable_label_support(
    label: AdvisoryLabel,
    strategy_status: StrategyEligibilityStatus,
    risk_status: RiskAuthorityStatus,
) -> None:
    if not (strategy_status.mandate_approved and strategy_status.evidence_approved):
        raise ValidationError(
            "actionable advisory labels require approved mandate and evidence."
        )

    if label == AdvisoryLabel.PAPER_ELIGIBLE:
        if not (strategy_status.paper_eligible and risk_status.paper_allowed):
            raise ValidationError(
                "paper_eligible requires strategy and risk paper support."
            )
    elif label == AdvisoryLabel.LIVE_PROBE_ELIGIBLE:
        if not (strategy_status.live_probe_eligible and risk_status.live_probe_allowed):
            raise ValidationError(
                "live_probe_eligible requires strategy and risk live probe support."
            )
    elif label == AdvisoryLabel.LIVE_AUTHORIZED:
        if not (strategy_status.live_authorized and risk_status.live_authorized):
            raise ValidationError(
                "live_authorized requires strategy and risk live authorization."
            )
