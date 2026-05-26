"""Advisory observation metadata for the research return-construction policy."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_return_construction_policy import (
    ResearchReturnConstructionPolicy,
)

__all__ = [
    "ResearchReturnConstructionPolicyObservation",
    "build_research_return_construction_policy_observation",
]

_OBSERVATION_TYPE = "research_return_construction_policy_observation"
_ADVISORY_SCOPE = "policy_contract_observation_only"
_EMPTY_COUNT = 0


@dataclass(frozen=True, slots=True)
class ResearchReturnConstructionPolicyObservation:
    """Deterministic advisory summary of a return-construction policy contract."""

    observation_type: str
    advisory_scope: str
    policy_state: str
    selected_period_count: int
    excluded_period_count: int
    source_return_observation_count: int
    forbidden_output_count: int
    source_policy: ResearchReturnConstructionPolicy

    def __post_init__(self) -> None:
        source_policy = _require_source_policy(self.source_policy)
        _validate_fixed_metadata(self.observation_type, self.advisory_scope)
        object.__setattr__(self, "source_policy", source_policy)
        object.__setattr__(
            self,
            "policy_state",
            _source_policy_state(self.policy_state, source_policy),
        )
        object.__setattr__(
            self,
            "selected_period_count",
            _zero_count(self.selected_period_count, "selected_period_count"),
        )
        object.__setattr__(
            self,
            "excluded_period_count",
            _zero_count(self.excluded_period_count, "excluded_period_count"),
        )
        object.__setattr__(
            self,
            "source_return_observation_count",
            _zero_count(
                self.source_return_observation_count,
                "source_return_observation_count",
            ),
        )
        object.__setattr__(
            self,
            "forbidden_output_count",
            _zero_count(self.forbidden_output_count, "forbidden_output_count"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only policy observation metadata."""

        return {
            "observation_type": self.observation_type,
            "advisory_scope": self.advisory_scope,
            "policy_state": self.policy_state,
            "selected_period_count": self.selected_period_count,
            "excluded_period_count": self.excluded_period_count,
            "source_return_observation_count": (
                self.source_return_observation_count
            ),
            "forbidden_output_count": self.forbidden_output_count,
            "source_policy": self.source_policy.to_dict(),
        }


def build_research_return_construction_policy_observation(
    policy_result_or_policy: ResearchReturnConstructionPolicy,
) -> ResearchReturnConstructionPolicyObservation:
    """Build advisory observation metadata for a Phase 247 policy contract."""

    source_policy = _require_source_policy(policy_result_or_policy)

    return ResearchReturnConstructionPolicyObservation(
        observation_type=_OBSERVATION_TYPE,
        advisory_scope=_ADVISORY_SCOPE,
        policy_state=source_policy.policy_state,
        selected_period_count=_EMPTY_COUNT,
        excluded_period_count=_EMPTY_COUNT,
        source_return_observation_count=_EMPTY_COUNT,
        forbidden_output_count=_EMPTY_COUNT,
        source_policy=source_policy,
    )


def _require_source_policy(value: object) -> ResearchReturnConstructionPolicy:
    if type(value) is not ResearchReturnConstructionPolicy:
        raise ValidationError(
            "source_policy must be a ResearchReturnConstructionPolicy."
        )

    return value


def _validate_fixed_metadata(
    observation_type: object,
    advisory_scope: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly "
            "research_return_construction_policy_observation."
        )
    if advisory_scope != _ADVISORY_SCOPE:
        raise ValidationError(
            "advisory_scope must be exactly policy_contract_observation_only."
        )


def _source_policy_state(
    value: object,
    source_policy: ResearchReturnConstructionPolicy,
) -> str:
    if type(value) is not str:
        raise ValidationError("policy_state must match source policy.")
    if value != source_policy.policy_state:
        raise ValidationError("policy_state must match source policy.")

    return value


def _zero_count(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value != _EMPTY_COUNT:
        raise ValidationError(f"{field_name} must be zero.")

    return value
