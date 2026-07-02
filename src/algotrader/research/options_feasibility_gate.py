"""Offline feasibility gate for future defined-risk options research.

This module is intentionally a research contract only. It does not create
orders, model broker payloads, import execution adapters, read credentials, or
perform network access.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from algotrader.errors import ValidationError

OptionsFeasibilityStatus = Literal[
    "options_not_authorized",
    "feasibility_only",
    "defined_risk_required",
    "data_requirements_missing",
    "broker_capability_unverified",
    "risk_model_missing",
    "approval_required_before_preview",
    "mutation_forbidden",
    "live_options_trading_forbidden",
    "separate_options_adapter_required",
]
OptionsFeasibilityClassification = Literal["blocked", "feasibility_only"]

DEFINED_RISK_OPTION_STRUCTURES = (
    "long_premium",
    "defined_risk_spread",
)
FORBIDDEN_OPTION_STRUCTURES = (
    "naked_short_option",
    "undefined_risk_spread",
    "unbounded_risk",
    "ratio_spread_unbounded",
    "short_straddle",
    "short_strangle",
)
OPTIONS_FEASIBILITY_REQUIRED_CONTROLS = (
    "explicit_user_authorization",
    "verified_options_market_data_source",
    "deterministic_contract_selection_rules",
    "max_loss_calculation",
    "liquidity_check",
    "spread_check",
    "open_interest_check",
    "assignment_exercise_risk_handling",
    "broker_capability_verification",
    "separate_options_adapter_registry",
    "live_options_trading_prohibited",
)

__all__ = [
    "DEFINED_RISK_OPTION_STRUCTURES",
    "FORBIDDEN_OPTION_STRUCTURES",
    "OPTIONS_FEASIBILITY_REQUIRED_CONTROLS",
    "OptionsFeasibilityClassification",
    "OptionsFeasibilityDecision",
    "OptionsFeasibilityInput",
    "OptionsFeasibilityStatus",
    "evaluate_options_feasibility",
]


@dataclass(frozen=True, slots=True)
class OptionsFeasibilityInput:
    """Operator-supplied proof flags before any options preview work."""

    structure_category: str = "long_premium"
    explicit_user_authorization: bool = False
    verified_options_market_data_source: bool = False
    deterministic_contract_selection_rules: bool = False
    max_loss_calculation: bool = False
    liquidity_check: bool = False
    spread_check: bool = False
    open_interest_check: bool = False
    assignment_exercise_risk_handling: bool = False
    broker_capability_verification: bool = False
    separate_options_adapter_registry: bool = False
    live_options_trading_prohibited: bool = True
    paper_action_requested: bool = False
    broker_mutation_requested: bool = False
    live_action_requested: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "structure_category",
            _required_string(self.structure_category, "structure_category").lower(),
        )
        for field_name in (
            "explicit_user_authorization",
            "verified_options_market_data_source",
            "deterministic_contract_selection_rules",
            "max_loss_calculation",
            "liquidity_check",
            "spread_check",
            "open_interest_check",
            "assignment_exercise_risk_handling",
            "broker_capability_verification",
            "separate_options_adapter_registry",
            "live_options_trading_prohibited",
            "paper_action_requested",
            "broker_mutation_requested",
            "live_action_requested",
        ):
            value = getattr(self, field_name)
            if type(value) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")


@dataclass(frozen=True, slots=True)
class OptionsFeasibilityDecision:
    """Deterministic gate receipt for options feasibility review."""

    classification: OptionsFeasibilityClassification
    statuses: tuple[OptionsFeasibilityStatus, ...]
    structure_category: str
    defined_risk_structure: bool
    minimum_controls_satisfied: bool
    blocked: bool
    missing_controls: tuple[str, ...]
    blockers: tuple[str, ...]
    required_controls: tuple[str, ...]
    defined_risk_structures: tuple[str, ...]
    forbidden_structures: tuple[str, ...]
    paper_preview_candidate: bool = False
    paper_mutation_candidate: bool = False
    broker_mutation_allowed: bool = False
    live_options_trading_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "classification",
            _choice(self.classification, _CLASSIFICATIONS, "classification"),
        )
        object.__setattr__(
            self,
            "statuses",
            tuple(
                _choice(status, _STATUSES, "statuses[]")
                for status in _string_tuple(self.statuses, "statuses")
            ),
        )
        object.__setattr__(
            self,
            "structure_category",
            _required_string(self.structure_category, "structure_category"),
        )
        for field_name in (
            "defined_risk_structure",
            "minimum_controls_satisfied",
            "blocked",
            "paper_preview_candidate",
            "paper_mutation_candidate",
            "broker_mutation_allowed",
            "live_options_trading_allowed",
        ):
            value = getattr(self, field_name)
            if type(value) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        object.__setattr__(
            self,
            "missing_controls",
            _string_tuple(self.missing_controls, "missing_controls"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "required_controls",
            _string_tuple(self.required_controls, "required_controls"),
        )
        object.__setattr__(
            self,
            "defined_risk_structures",
            _string_tuple(self.defined_risk_structures, "defined_risk_structures"),
        )
        object.__setattr__(
            self,
            "forbidden_structures",
            _string_tuple(self.forbidden_structures, "forbidden_structures"),
        )
        if self.paper_preview_candidate:
            raise ValidationError("options feasibility cannot create preview candidates.")
        if self.paper_mutation_candidate:
            raise ValidationError("options feasibility cannot create mutation candidates.")
        if self.broker_mutation_allowed:
            raise ValidationError("options feasibility cannot allow broker mutation.")
        if self.live_options_trading_allowed:
            raise ValidationError("live options trading must remain forbidden.")
        if self.minimum_controls_satisfied and self.missing_controls:
            raise ValidationError(
                "minimum_controls_satisfied requires no missing_controls."
            )
        if self.classification == "feasibility_only" and self.blocked:
            raise ValidationError("feasibility_only classification cannot be blocked.")

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only feasibility metadata."""

        return {
            "classification": self.classification,
            "statuses": list(self.statuses),
            "structure_category": self.structure_category,
            "defined_risk_structure": self.defined_risk_structure,
            "minimum_controls_satisfied": self.minimum_controls_satisfied,
            "blocked": self.blocked,
            "missing_controls": list(self.missing_controls),
            "blockers": list(self.blockers),
            "required_controls": list(self.required_controls),
            "defined_risk_structures": list(self.defined_risk_structures),
            "forbidden_structures": list(self.forbidden_structures),
            "paper_preview_candidate": self.paper_preview_candidate,
            "paper_mutation_candidate": self.paper_mutation_candidate,
            "broker_mutation_allowed": self.broker_mutation_allowed,
            "live_options_trading_allowed": self.live_options_trading_allowed,
        }


def evaluate_options_feasibility(
    gate_input: OptionsFeasibilityInput | None = None,
) -> OptionsFeasibilityDecision:
    """Evaluate offline feasibility controls for future options preview review."""

    checked_input = OptionsFeasibilityInput() if gate_input is None else _input(gate_input)
    missing_controls = _missing_controls(checked_input)
    defined_risk_structure = (
        checked_input.structure_category in DEFINED_RISK_OPTION_STRUCTURES
    )
    action_requested = (
        checked_input.paper_action_requested
        or checked_input.broker_mutation_requested
        or checked_input.live_action_requested
    )
    statuses: list[OptionsFeasibilityStatus] = [
        "mutation_forbidden",
        "live_options_trading_forbidden",
    ]
    blockers: list[str] = []

    if not checked_input.explicit_user_authorization:
        statuses.extend(("options_not_authorized", "approval_required_before_preview"))
        blockers.append("explicit_user_authorization_required")
    if defined_risk_structure:
        statuses.append("feasibility_only")
    else:
        statuses.append("defined_risk_required")
        blockers.append(f"defined_risk_required:{checked_input.structure_category}")
    if checked_input.structure_category in FORBIDDEN_OPTION_STRUCTURES:
        blockers.append(f"forbidden_structure:{checked_input.structure_category}")
    if _data_controls_missing(checked_input):
        statuses.append("data_requirements_missing")
    if _risk_controls_missing(checked_input):
        statuses.append("risk_model_missing")
    if not checked_input.broker_capability_verification:
        statuses.append("broker_capability_unverified")
    if not checked_input.separate_options_adapter_registry:
        statuses.append("separate_options_adapter_required")
    if not checked_input.live_options_trading_prohibited:
        blockers.append("live_options_trading_prohibition_required")
    if action_requested:
        blockers.append("options_action_request_forbidden")

    blockers.extend(f"missing_control:{control}" for control in missing_controls)
    minimum_controls_satisfied = (
        defined_risk_structure
        and not missing_controls
        and checked_input.live_options_trading_prohibited
        and not action_requested
    )
    blocked = not minimum_controls_satisfied

    return OptionsFeasibilityDecision(
        classification="blocked" if blocked else "feasibility_only",
        statuses=tuple(_dedupe(statuses)),
        structure_category=checked_input.structure_category,
        defined_risk_structure=defined_risk_structure,
        minimum_controls_satisfied=minimum_controls_satisfied,
        blocked=blocked,
        missing_controls=missing_controls,
        blockers=tuple(_dedupe(blockers)),
        required_controls=OPTIONS_FEASIBILITY_REQUIRED_CONTROLS,
        defined_risk_structures=DEFINED_RISK_OPTION_STRUCTURES,
        forbidden_structures=FORBIDDEN_OPTION_STRUCTURES,
    )


def _missing_controls(gate_input: OptionsFeasibilityInput) -> tuple[str, ...]:
    missing: list[str] = []
    if not gate_input.explicit_user_authorization:
        missing.append("explicit_user_authorization")
    if not gate_input.verified_options_market_data_source:
        missing.append("verified_options_market_data_source")
    if not gate_input.deterministic_contract_selection_rules:
        missing.append("deterministic_contract_selection_rules")
    if not gate_input.max_loss_calculation:
        missing.append("max_loss_calculation")
    if not gate_input.liquidity_check:
        missing.append("liquidity_check")
    if not gate_input.spread_check:
        missing.append("spread_check")
    if not gate_input.open_interest_check:
        missing.append("open_interest_check")
    if not gate_input.assignment_exercise_risk_handling:
        missing.append("assignment_exercise_risk_handling")
    if not gate_input.broker_capability_verification:
        missing.append("broker_capability_verification")
    if not gate_input.separate_options_adapter_registry:
        missing.append("separate_options_adapter_registry")
    if not gate_input.live_options_trading_prohibited:
        missing.append("live_options_trading_prohibited")
    return tuple(missing)


def _data_controls_missing(gate_input: OptionsFeasibilityInput) -> bool:
    return not (
        gate_input.verified_options_market_data_source
        and gate_input.deterministic_contract_selection_rules
        and gate_input.liquidity_check
        and gate_input.spread_check
        and gate_input.open_interest_check
    )


def _risk_controls_missing(gate_input: OptionsFeasibilityInput) -> bool:
    return not (
        gate_input.max_loss_calculation
        and gate_input.assignment_exercise_risk_handling
    )


def _input(value: object) -> OptionsFeasibilityInput:
    if type(value) is not OptionsFeasibilityInput:
        raise ValidationError("gate_input must be an OptionsFeasibilityInput.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _choice(value: object, allowed: tuple[str, ...], field_name: str) -> str:
    if type(value) is not str or value not in allowed:
        allowed_text = ", ".join(allowed)
        raise ValidationError(f"{field_name} must be one of: {allowed_text}.")
    return value


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    return tuple(_required_string(value, f"{field_name}[]") for value in values)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        item = _required_string(value, "value")
        if item not in seen:
            seen.add(item)
            items.append(item)
    return tuple(items)


_STATUSES = (
    "options_not_authorized",
    "feasibility_only",
    "defined_risk_required",
    "data_requirements_missing",
    "broker_capability_unverified",
    "risk_model_missing",
    "approval_required_before_preview",
    "mutation_forbidden",
    "live_options_trading_forbidden",
    "separate_options_adapter_required",
)
_CLASSIFICATIONS = ("blocked", "feasibility_only")
