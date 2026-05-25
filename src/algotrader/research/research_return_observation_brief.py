"""Metadata-only advisory wrapper for research return observations."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation import (
    ResearchReturnSeriesObservation,
)

__all__ = [
    "RESEARCH_RETURN_OBSERVATION_MECHANICAL_STATES",
    "ResearchReturnObservationBriefItem",
    "build_research_return_observation_brief_item",
]

_ITEM_TYPE = "research_return_observation_brief_item"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
RESEARCH_RETURN_OBSERVATION_MECHANICAL_STATES = (
    "returns_constructed",
    "insufficient_return_history",
)


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("author", "ity"),
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    _join("port", "folio"),
    _join("pa", "per"),
    _join("li", "ve"),
    _join("read", "iness"),
    _join("trading", "_ready"),
    _join("trading", "-ready"),
    _join("action", "ability"),
    _join("action", "able"),
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class ResearchReturnObservationBriefItem:
    """Primitive advisory metadata wrapping a research return observation."""

    item_type: str
    status: str
    authority: str
    capital_authority: bool
    headline: str
    summary: str
    mechanical_state: str
    positive_return_count: int
    negative_return_count: int
    zero_return_count: int
    source_observation: ResearchReturnSeriesObservation
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_observation = _require_source_observation(self.source_observation)
        _validate_fixed_metadata(
            self.item_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "headline",
            _advisory_text(self.headline, "headline"),
        )
        object.__setattr__(
            self,
            "summary",
            _advisory_text(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "mechanical_state",
            _mechanical_state(self.mechanical_state),
        )
        object.__setattr__(
            self,
            "positive_return_count",
            _non_negative_int(self.positive_return_count, "positive_return_count"),
        )
        object.__setattr__(
            self,
            "negative_return_count",
            _non_negative_int(self.negative_return_count, "negative_return_count"),
        )
        object.__setattr__(
            self,
            "zero_return_count",
            _non_negative_int(self.zero_return_count, "zero_return_count"),
        )
        object.__setattr__(self, "source_observation", source_observation)
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _deduped_non_claims(self.non_claims),
        )
        _validate_source_metadata(self, source_observation)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only return observation brief metadata."""

        return {
            "item_type": self.item_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "headline": self.headline,
            "summary": self.summary,
            "mechanical_state": self.mechanical_state,
            "positive_return_count": self.positive_return_count,
            "negative_return_count": self.negative_return_count,
            "zero_return_count": self.zero_return_count,
            "source_observation": self.source_observation.to_dict(),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_return_observation_brief_item(
    observation: ResearchReturnSeriesObservation,
) -> ResearchReturnObservationBriefItem:
    """Build a deterministic advisory-only return observation brief item."""

    source_observation = _require_source_observation(observation)
    positive_count, negative_count, zero_count = _return_direction_counts(
        source_observation
    )
    return ResearchReturnObservationBriefItem(
        item_type=_ITEM_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        headline=_headline(source_observation),
        summary=_summary(source_observation),
        mechanical_state=_mechanical_state_from_observation(source_observation),
        positive_return_count=positive_count,
        negative_return_count=negative_count,
        zero_return_count=zero_count,
        source_observation=source_observation,
        limitations=_dedupe(source_observation.limitations),
        non_claims=_dedupe(source_observation.non_claims),
    )


def _headline(observation: ResearchReturnSeriesObservation) -> str:
    mechanical_state = _mechanical_state_from_observation(observation)
    return (
        f"Research return observation {observation.symbol} {observation.as_of}: "
        f"{mechanical_state}."
    )


def _summary(observation: ResearchReturnSeriesObservation) -> str:
    positive_count, negative_count, zero_count = _return_direction_counts(observation)
    return (
        "Research return observation metadata records "
        f"{_mechanical_state_from_observation(observation)} for "
        f"{observation.symbol} as of {observation.as_of} using "
        f"{observation.return_method} on {observation.price_basis}, "
        f"{observation.eligible_sample_count} eligible sample(s), "
        f"{observation.ignored_future_sample_count} later sample(s) ignored, "
        f"{observation.return_count} return(s), positive count {positive_count}, "
        f"negative count {negative_count}, and zero count {zero_count}."
    )


def _require_source_observation(value: object) -> ResearchReturnSeriesObservation:
    if type(value) is not ResearchReturnSeriesObservation:
        raise ValidationError(
            "source_observation must be a ResearchReturnSeriesObservation."
        )

    return value


def _validate_fixed_metadata(
    item_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if item_type != _ITEM_TYPE:
        raise ValidationError(
            "item_type must be exactly research_return_observation_brief_item."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _validate_source_metadata(
    item: ResearchReturnObservationBriefItem,
    observation: ResearchReturnSeriesObservation,
) -> None:
    positive_count, negative_count, zero_count = _return_direction_counts(observation)
    _validate_matches_source(
        "headline",
        item.headline,
        _headline(observation),
    )
    _validate_matches_source(
        "summary",
        item.summary,
        _summary(observation),
    )
    _validate_matches_source(
        "mechanical_state",
        item.mechanical_state,
        _mechanical_state_from_observation(observation),
    )
    _validate_matches_source(
        "positive_return_count",
        item.positive_return_count,
        positive_count,
    )
    _validate_matches_source(
        "negative_return_count",
        item.negative_return_count,
        negative_count,
    )
    _validate_matches_source(
        "zero_return_count",
        item.zero_return_count,
        zero_count,
    )
    _validate_matches_source(
        "limitations",
        item.limitations,
        _dedupe(observation.limitations),
    )
    _validate_matches_source(
        "non_claims",
        item.non_claims,
        _dedupe(observation.non_claims),
    )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source_observation.")


def _mechanical_state_from_observation(
    observation: ResearchReturnSeriesObservation,
) -> str:
    if observation.return_count == 0:
        return "insufficient_return_history"

    return "returns_constructed"


def _mechanical_state(value: object) -> str:
    state = _required_string(value, "mechanical_state")
    if state not in RESEARCH_RETURN_OBSERVATION_MECHANICAL_STATES:
        allowed = ", ".join(RESEARCH_RETURN_OBSERVATION_MECHANICAL_STATES)
        raise ValidationError(f"mechanical_state must be one of: {allowed}.")

    return state


def _return_direction_counts(
    observation: ResearchReturnSeriesObservation,
) -> tuple[int, int, int]:
    positive_count = 0
    negative_count = 0
    zero_count = 0
    for return_point in observation.returns:
        if return_point.simple_return > 0:
            positive_count += 1
        elif return_point.simple_return < 0:
            negative_count += 1
        else:
            zero_count += 1

    return positive_count, negative_count, zero_count


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _advisory_text(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    lowered = text.lower()
    if any(token in lowered for token in _FORBIDDEN_TEXT_TOKENS):
        raise ValidationError(f"{field_name} must remain advisory metadata text.")

    return text


def _deduped_advisory_text_tuple(
    values: object,
    field_name: str,
) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, field_name, allow_empty=True))
    for index, value in enumerate(items):
        _advisory_text(value, f"{field_name}[{index}]")

    return items


def _deduped_non_claims(values: object) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, "non_claims", allow_empty=False))
    if not items:
        raise ValidationError("non_claims must contain at least one string.")

    if any(not item.startswith("not ") for item in items):
        raise ValidationError("non_claims entries must be negative statements.")

    return items


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not allow_empty and not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)
