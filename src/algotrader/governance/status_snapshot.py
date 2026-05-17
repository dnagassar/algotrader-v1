"""Immutable governance status snapshots for future advisory inputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError

__all__ = [
    "RiskAuthoritySnapshot",
    "StrategyMandateSnapshot",
]


@dataclass(frozen=True, slots=True)
class StrategyMandateSnapshot:
    """Metadata-only strategy mandate status."""

    strategy_id: str
    mandate_id: str
    as_of_date: date
    mandate_approved: bool
    evidence_approved: bool
    paper_eligible: bool
    live_probe_eligible: bool
    live_authorized: bool
    validated_research_artifact_ids: tuple[str, ...]
    validated_signal_definition_ids: tuple[str, ...]
    required_evidence: tuple[str, ...]
    promotion_requirements: tuple[str, ...]
    revocation_triggers: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    uncertainty_factors: tuple[str, ...]
    failure_modes: tuple[str, ...]
    non_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive strategy mandate metadata."""
        return {
            "strategy_id": self.strategy_id,
            "mandate_id": self.mandate_id,
            "as_of_date": _serialize_plain_date(self.as_of_date),
            "mandate_approved": self.mandate_approved,
            "evidence_approved": self.evidence_approved,
            "paper_eligible": self.paper_eligible,
            "live_probe_eligible": self.live_probe_eligible,
            "live_authorized": self.live_authorized,
            "validated_research_artifact_ids": list(
                self.validated_research_artifact_ids
            ),
            "validated_signal_definition_ids": list(
                self.validated_signal_definition_ids
            ),
            "required_evidence": list(self.required_evidence),
            "promotion_requirements": list(self.promotion_requirements),
            "revocation_triggers": list(self.revocation_triggers),
            "blocking_reasons": list(self.blocking_reasons),
            "limitations": list(self.limitations),
            "uncertainty_factors": list(self.uncertainty_factors),
            "failure_modes": list(self.failure_modes),
            "non_claims": list(self.non_claims),
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strategy_id",
            _required_string(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "mandate_id",
            _required_string(self.mandate_id, "mandate_id"),
        )
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
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
            "validated_research_artifact_ids",
            _string_tuple(
                self.validated_research_artifact_ids,
                "validated_research_artifact_ids",
            ),
        )
        object.__setattr__(
            self,
            "validated_signal_definition_ids",
            _string_tuple(
                self.validated_signal_definition_ids,
                "validated_signal_definition_ids",
            ),
        )
        object.__setattr__(
            self,
            "required_evidence",
            _string_tuple(self.required_evidence, "required_evidence"),
        )
        object.__setattr__(
            self,
            "promotion_requirements",
            _string_tuple(self.promotion_requirements, "promotion_requirements"),
        )
        object.__setattr__(
            self,
            "revocation_triggers",
            _string_tuple(self.revocation_triggers, "revocation_triggers"),
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
            "non_claims",
            _string_tuple(self.non_claims, "non_claims"),
        )
        _validate_strategy_mandate_snapshot(self)


@dataclass(frozen=True, slots=True)
class RiskAuthoritySnapshot:
    """Metadata-only risk authority status."""

    authority_id: str
    strategy_id: str
    as_of_date: date
    paper_allowed: bool
    live_probe_allowed: bool
    live_allowed: bool
    kill_switch_active: bool
    risk_policy_ids: tuple[str, ...]
    active_constraints: tuple[str, ...]
    promotion_requirements: tuple[str, ...]
    revocation_triggers: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    uncertainty_factors: tuple[str, ...]
    failure_modes: tuple[str, ...]
    non_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive risk authority metadata."""
        return {
            "authority_id": self.authority_id,
            "strategy_id": self.strategy_id,
            "as_of_date": _serialize_plain_date(self.as_of_date),
            "paper_allowed": self.paper_allowed,
            "live_probe_allowed": self.live_probe_allowed,
            "live_allowed": self.live_allowed,
            "kill_switch_active": self.kill_switch_active,
            "risk_policy_ids": list(self.risk_policy_ids),
            "active_constraints": list(self.active_constraints),
            "promotion_requirements": list(self.promotion_requirements),
            "revocation_triggers": list(self.revocation_triggers),
            "blocking_reasons": list(self.blocking_reasons),
            "limitations": list(self.limitations),
            "uncertainty_factors": list(self.uncertainty_factors),
            "failure_modes": list(self.failure_modes),
            "non_claims": list(self.non_claims),
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "authority_id",
            _required_string(self.authority_id, "authority_id"),
        )
        object.__setattr__(
            self,
            "strategy_id",
            _required_string(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
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
            "live_allowed",
            _bool_value(self.live_allowed, "live_allowed"),
        )
        object.__setattr__(
            self,
            "kill_switch_active",
            _bool_value(self.kill_switch_active, "kill_switch_active"),
        )
        object.__setattr__(
            self,
            "risk_policy_ids",
            _string_tuple(self.risk_policy_ids, "risk_policy_ids"),
        )
        object.__setattr__(
            self,
            "active_constraints",
            _string_tuple(self.active_constraints, "active_constraints"),
        )
        object.__setattr__(
            self,
            "promotion_requirements",
            _string_tuple(self.promotion_requirements, "promotion_requirements"),
        )
        object.__setattr__(
            self,
            "revocation_triggers",
            _string_tuple(self.revocation_triggers, "revocation_triggers"),
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
            "non_claims",
            _string_tuple(self.non_claims, "non_claims"),
        )
        _validate_risk_authority_snapshot(self)


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _bool_value(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


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


def _validate_strategy_mandate_snapshot(snapshot: StrategyMandateSnapshot) -> None:
    if snapshot.live_probe_eligible and not snapshot.paper_eligible:
        raise ValidationError("live_probe_eligible requires paper_eligible.")
    if snapshot.live_authorized and not snapshot.mandate_approved:
        raise ValidationError("live_authorized requires mandate_approved.")
    if snapshot.live_authorized and not snapshot.evidence_approved:
        raise ValidationError("live_authorized requires evidence_approved.")
    if snapshot.live_authorized and not snapshot.paper_eligible:
        raise ValidationError("live_authorized requires paper_eligible.")
    if snapshot.live_authorized and not snapshot.live_probe_eligible:
        raise ValidationError("live_authorized requires live_probe_eligible.")
    if snapshot.live_authorized and snapshot.blocking_reasons:
        raise ValidationError("live_authorized cannot include blocking_reasons.")


def _validate_risk_authority_snapshot(snapshot: RiskAuthoritySnapshot) -> None:
    if snapshot.live_probe_allowed and not snapshot.paper_allowed:
        raise ValidationError("live_probe_allowed requires paper_allowed.")
    if snapshot.live_allowed and not snapshot.paper_allowed:
        raise ValidationError("live_allowed requires paper_allowed.")
    if snapshot.live_allowed and not snapshot.live_probe_allowed:
        raise ValidationError("live_allowed requires live_probe_allowed.")
    if snapshot.live_allowed and snapshot.kill_switch_active:
        raise ValidationError("live_allowed cannot be true when kill_switch_active.")
    if snapshot.live_allowed and snapshot.blocking_reasons:
        raise ValidationError("live_allowed cannot include blocking_reasons.")
