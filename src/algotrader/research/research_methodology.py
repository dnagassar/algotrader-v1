"""Metadata-only research methodology candidate contracts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import TypeVar

from algotrader.errors import ValidationError

__all__ = [
    "ACTION_TIMING_POLICIES",
    "APPROVAL_STATES",
    "CADENCE_POLICIES",
    "COMPARISON_RULES",
    "COST_ASSUMPTION_POLICIES",
    "COST_POLICIES",
    "LOOKAHEAD_POLICIES",
    "METHODOLOGY_TYPES",
    "PARAMETER_TYPES",
    "REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS",
    "RULE_FAMILIES",
    "ResearchMethodologyCandidate",
    "ResearchMethodologyScopeSnapshot",
    "ResearchParameterSetCandidate",
]


APPROVAL_STATES = ("candidate_only", "blocked", "deferred")
METHODOLOGY_TYPES = (
    "synthetic",
    "moving_average_trend_candidate",
    "buy_and_hold_baseline_candidate",
    "other",
)
RULE_FAMILIES = (
    "synthetic",
    "simple_moving_average_candidate",
    "baseline_candidate",
    "other",
)
PARAMETER_TYPES = (
    "synthetic",
    "single_window_candidate",
    "sensitivity_grid_candidate",
    "baseline_candidate",
    "other",
)
CADENCE_POLICIES = (
    "synthetic_only",
    "daily_close_candidate",
    "monthly_close_candidate",
    "unresolved",
    "other",
)
ACTION_TIMING_POLICIES = (
    "synthetic_previous_exposure",
    "next_session_candidate",
    "next_rebalance_candidate",
    "same_close_metadata_only",
    "unresolved",
    "other",
)
LOOKAHEAD_POLICIES = (
    "synthetic_no_lookahead",
    "candidate_as_of_protocol_required",
    "unresolved",
    "other",
)
COMPARISON_RULES = (
    "value_gt_moving_average",
    "value_gte_moving_average_candidate",
    "baseline_always_exposed",
    "synthetic_only",
    "other",
)
COST_POLICIES = (
    "zero_cost_placeholder",
    "synthetic_cost_candidate",
    "real_cost_policy_required",
    "unresolved",
    "other",
)
COST_ASSUMPTION_POLICIES = COST_POLICIES
REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS = (
    "not methodology approval",
    "not parameter approval",
    "not strategy validation",
    "not signal approval",
    "not evaluator approval",
    "not trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "no real data ingestion",
    "no source/universe/benchmark/cash proxy approval",
)

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ResearchMethodologyCandidate:
    """Candidate-only methodology metadata for future research planning."""

    methodology_id: str
    methodology_name: str
    methodology_type: str
    approval_state: str
    rule_family: str
    rule_description: str
    cadence_policy: str
    action_timing_policy: str
    lookahead_policy: str
    return_construction_policy: str
    adjustment_policy: str
    cost_policy: str
    linked_scope_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "methodology_id",
            _required_string(self.methodology_id, "methodology_id"),
        )
        object.__setattr__(
            self,
            "methodology_name",
            _required_string(self.methodology_name, "methodology_name"),
        )
        object.__setattr__(
            self,
            "methodology_type",
            _allowed_string(
                self.methodology_type,
                "methodology_type",
                METHODOLOGY_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(
            self,
            "rule_family",
            _allowed_string(self.rule_family, "rule_family", RULE_FAMILIES),
        )
        object.__setattr__(
            self,
            "rule_description",
            _required_string(self.rule_description, "rule_description"),
        )
        object.__setattr__(
            self,
            "cadence_policy",
            _allowed_string(
                self.cadence_policy,
                "cadence_policy",
                CADENCE_POLICIES,
            ),
        )
        object.__setattr__(
            self,
            "action_timing_policy",
            _allowed_string(
                self.action_timing_policy,
                "action_timing_policy",
                ACTION_TIMING_POLICIES,
            ),
        )
        object.__setattr__(
            self,
            "lookahead_policy",
            _allowed_string(
                self.lookahead_policy,
                "lookahead_policy",
                LOOKAHEAD_POLICIES,
            ),
        )
        object.__setattr__(
            self,
            "return_construction_policy",
            _required_string(
                self.return_construction_policy,
                "return_construction_policy",
            ),
        )
        object.__setattr__(
            self,
            "adjustment_policy",
            _required_string(self.adjustment_policy, "adjustment_policy"),
        )
        object.__setattr__(
            self,
            "cost_policy",
            _allowed_string(self.cost_policy, "cost_policy", COST_POLICIES),
        )
        object.__setattr__(
            self,
            "linked_scope_ids",
            _string_tuple(self.linked_scope_ids, "linked_scope_ids"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive methodology metadata."""

        return {
            "methodology_id": self.methodology_id,
            "methodology_name": self.methodology_name,
            "methodology_type": self.methodology_type,
            "approval_state": self.approval_state,
            "rule_family": self.rule_family,
            "rule_description": self.rule_description,
            "cadence_policy": self.cadence_policy,
            "action_timing_policy": self.action_timing_policy,
            "lookahead_policy": self.lookahead_policy,
            "return_construction_policy": self.return_construction_policy,
            "adjustment_policy": self.adjustment_policy,
            "cost_policy": self.cost_policy,
            "linked_scope_ids": list(self.linked_scope_ids),
            "evidence_refs": list(self.evidence_refs),
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


@dataclass(frozen=True, slots=True)
class ResearchParameterSetCandidate:
    """Candidate-only parameter-set metadata for future research planning."""

    parameter_set_id: str
    methodology_id: str
    parameter_set_name: str
    parameter_type: str
    approval_state: str
    moving_average_windows: tuple[int, ...]
    cadence_policy: str
    action_timing_policy: str
    comparison_rule: str
    cost_assumption_policy: str
    sensitivity_notes: tuple[str, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "parameter_set_id",
            _required_string(self.parameter_set_id, "parameter_set_id"),
        )
        object.__setattr__(
            self,
            "methodology_id",
            _required_string(self.methodology_id, "methodology_id"),
        )
        object.__setattr__(
            self,
            "parameter_set_name",
            _required_string(self.parameter_set_name, "parameter_set_name"),
        )
        object.__setattr__(
            self,
            "parameter_type",
            _allowed_string(
                self.parameter_type,
                "parameter_type",
                PARAMETER_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(
            self,
            "moving_average_windows",
            _positive_int_tuple(
                self.moving_average_windows,
                "moving_average_windows",
            ),
        )
        object.__setattr__(
            self,
            "cadence_policy",
            _allowed_string(
                self.cadence_policy,
                "cadence_policy",
                CADENCE_POLICIES,
            ),
        )
        object.__setattr__(
            self,
            "action_timing_policy",
            _allowed_string(
                self.action_timing_policy,
                "action_timing_policy",
                ACTION_TIMING_POLICIES,
            ),
        )
        object.__setattr__(
            self,
            "comparison_rule",
            _allowed_string(
                self.comparison_rule,
                "comparison_rule",
                COMPARISON_RULES,
            ),
        )
        object.__setattr__(
            self,
            "cost_assumption_policy",
            _allowed_string(
                self.cost_assumption_policy,
                "cost_assumption_policy",
                COST_ASSUMPTION_POLICIES,
            ),
        )
        object.__setattr__(
            self,
            "sensitivity_notes",
            _string_tuple(self.sensitivity_notes, "sensitivity_notes"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive parameter metadata."""

        return {
            "parameter_set_id": self.parameter_set_id,
            "methodology_id": self.methodology_id,
            "parameter_set_name": self.parameter_set_name,
            "parameter_type": self.parameter_type,
            "approval_state": self.approval_state,
            "moving_average_windows": list(self.moving_average_windows),
            "cadence_policy": self.cadence_policy,
            "action_timing_policy": self.action_timing_policy,
            "comparison_rule": self.comparison_rule,
            "cost_assumption_policy": self.cost_assumption_policy,
            "sensitivity_notes": list(self.sensitivity_notes),
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


@dataclass(frozen=True, slots=True)
class ResearchMethodologyScopeSnapshot:
    """Candidate-only methodology scope snapshot metadata."""

    methodology_scope_id: str
    as_of_date: date
    approval_state: str
    methodology_candidates: tuple[ResearchMethodologyCandidate, ...]
    parameter_set_candidates: tuple[ResearchParameterSetCandidate, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "methodology_scope_id",
            _required_string(self.methodology_scope_id, "methodology_scope_id"),
        )
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(
            self,
            "methodology_candidates",
            _candidate_tuple(
                self.methodology_candidates,
                "methodology_candidates",
                ResearchMethodologyCandidate,
            ),
        )
        object.__setattr__(
            self,
            "parameter_set_candidates",
            _candidate_tuple(
                self.parameter_set_candidates,
                "parameter_set_candidates",
                ResearchParameterSetCandidate,
            ),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )
        _validate_unique_candidate_ids(
            self.methodology_candidates,
            "methodology_candidates",
            "methodology_id",
        )
        _validate_unique_candidate_ids(
            self.parameter_set_candidates,
            "parameter_set_candidates",
            "parameter_set_id",
        )
        _validate_parameter_methodology_links(
            self.methodology_candidates,
            self.parameter_set_candidates,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive snapshot metadata."""

        return {
            "methodology_scope_id": self.methodology_scope_id,
            "as_of_date": self.as_of_date.isoformat(),
            "approval_state": self.approval_state,
            "methodology_candidates": [
                candidate.to_dict() for candidate in self.methodology_candidates
            ],
            "parameter_set_candidates": [
                candidate.to_dict() for candidate in self.parameter_set_candidates
            ],
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


def _required_string(value: str, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return normalized


def _allowed_string(
    value: str,
    field_name: str,
    allowed_values: tuple[str, ...],
) -> str:
    normalized = _required_string(value, field_name)
    if normalized not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValidationError(f"{field_name} must be one of: {allowed}.")

    return normalized


def _plain_date(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

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
        raise ValidationError(f"{field_name} must contain at least one string.")

    return items


def _required_non_claims(values: Iterable[str]) -> tuple[str, ...]:
    items = _required_string_tuple(values, "non_claims")
    missing = tuple(
        claim for claim in REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS if claim not in items
    )
    if missing:
        raise ValidationError(
            "non_claims must include required research methodology non-claims."
        )

    return items


def _positive_int_tuple(values: Iterable[int], field_name: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{field_name} must be an iterable of positive integers.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of positive integers."
        ) from exc

    if not items:
        raise ValidationError(f"{field_name} must contain at least one window.")

    for index, value in enumerate(items):
        if type(value) is not int:
            raise ValidationError(f"{field_name}[{index}] must be a positive integer.")
        if value <= 0:
            raise ValidationError(f"{field_name}[{index}] must be a positive integer.")

    if len(frozenset(items)) != len(items):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return items


def _candidate_tuple(
    values: Iterable[_T],
    field_name: str,
    expected_type: type[_T],
) -> tuple[_T, ...]:
    if isinstance(values, str):
        raise ValidationError(
            f"{field_name} must be an iterable of {expected_type.__name__} values."
        )

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of {expected_type.__name__} values."
        ) from exc

    if not items:
        raise ValidationError(f"{field_name} must contain at least one candidate.")

    for item in items:
        if not isinstance(item, expected_type):
            raise ValidationError(
                f"{field_name} must contain {expected_type.__name__} values."
            )

    return items


def _validate_unique_candidate_ids(
    candidates: Iterable[object],
    field_name: str,
    id_field_name: str,
) -> None:
    ids: list[str] = []
    for candidate in candidates:
        try:
            candidate_id = getattr(candidate, id_field_name)
        except AttributeError as exc:
            raise ValidationError(f"{field_name} contains malformed candidates.") from exc

        ids.append(_required_string(candidate_id, id_field_name))

    if len(frozenset(ids)) != len(ids):
        raise ValidationError(f"{field_name} must not contain duplicate ids.")


def _validate_parameter_methodology_links(
    methodology_candidates: Iterable[ResearchMethodologyCandidate],
    parameter_set_candidates: Iterable[ResearchParameterSetCandidate],
) -> None:
    methodology_ids = frozenset(
        candidate.methodology_id for candidate in methodology_candidates
    )
    for candidate in parameter_set_candidates:
        if candidate.methodology_id not in methodology_ids:
            raise ValidationError(
                "parameter_set_candidates must reference methodology candidate ids."
            )
