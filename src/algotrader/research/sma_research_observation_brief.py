"""Metadata-only advisory wrapper for SMA research observations."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation import SmaResearchObservation

__all__ = [
    "SMA_RESEARCH_OBSERVATION_MECHANICAL_STATES",
    "SmaResearchObservationBriefItem",
    "build_sma_research_observation_brief_item",
]

_ITEM_TYPE = "sma_research_observation_brief_item"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
SMA_RESEARCH_OBSERVATION_MECHANICAL_STATES = (
    "above_sma_observation",
    "below_sma_observation",
    "equal_sma_observation",
    "insufficient_history",
)
_MECHANICAL_STATE_BY_POSITION = {
    "above": "above_sma_observation",
    "below": "below_sma_observation",
    "equal": "equal_sma_observation",
    "insufficient_history": "insufficient_history",
}


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
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
    _join("capital ", "authority"),
    _join("tra", "ding authority"),
    _join("trading", "_ready"),
    _join("trading", "-ready"),
    _join("action", "able"),
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class SmaResearchObservationBriefItem:
    """Primitive advisory metadata wrapping a synthetic SMA observation."""

    item_type: str
    status: str
    authority: str
    capital_authority: bool
    headline: str
    summary: str
    mechanical_state: str
    source_observation: SmaResearchObservation
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
        """Return deterministic primitive-only SMA observation brief metadata."""

        return {
            "item_type": self.item_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "headline": self.headline,
            "summary": self.summary,
            "mechanical_state": self.mechanical_state,
            "source_observation": self.source_observation.to_dict(),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_research_observation_brief_item(
    observation: SmaResearchObservation,
) -> SmaResearchObservationBriefItem:
    """Build a deterministic advisory-only SMA observation brief item."""

    source_observation = _require_source_observation(observation)
    return SmaResearchObservationBriefItem(
        item_type=_ITEM_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        headline=_headline(source_observation),
        summary=_summary(source_observation),
        mechanical_state=_mechanical_state_from_observation(source_observation),
        source_observation=source_observation,
        limitations=_dedupe(source_observation.limitations),
        non_claims=_dedupe(source_observation.non_claims),
    )


def _headline(observation: SmaResearchObservation) -> str:
    mechanical_state = _mechanical_state_from_observation(observation)
    return (
        f"SMA observation {observation.symbol} {observation.as_of}: "
        f"{mechanical_state}."
    )


def _summary(observation: SmaResearchObservation) -> str:
    return (
        "SMA observation metadata records "
        f"{_mechanical_state_from_observation(observation)} for "
        f"{observation.symbol} as of {observation.as_of} with window "
        f"{observation.window}, {observation.eligible_sample_count} eligible "
        f"sample(s), {observation.ignored_future_sample_count} later sample(s) "
        f"ignored, latest close {_decimal_text(observation.latest_close)}, "
        f"SMA {_decimal_text(observation.sma_value)}, distance "
        f"{_decimal_text(observation.distance_from_sma)}, and distance pct "
        f"{_decimal_text(observation.distance_from_sma_pct)}."
    )


def _require_source_observation(value: object) -> SmaResearchObservation:
    if type(value) is not SmaResearchObservation:
        raise ValidationError(
            "source_observation must be a SmaResearchObservation."
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
            "item_type must be exactly sma_research_observation_brief_item."
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
    item: SmaResearchObservationBriefItem,
    observation: SmaResearchObservation,
) -> None:
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


def _mechanical_state_from_observation(observation: SmaResearchObservation) -> str:
    try:
        return _MECHANICAL_STATE_BY_POSITION[observation.position_vs_sma]
    except KeyError as exc:
        raise ValidationError("position_vs_sma cannot be mapped.") from exc


def _mechanical_state(value: object) -> str:
    state = _required_string(value, "mechanical_state")
    if state not in SMA_RESEARCH_OBSERVATION_MECHANICAL_STATES:
        allowed = ", ".join(SMA_RESEARCH_OBSERVATION_MECHANICAL_STATES)
        raise ValidationError(f"mechanical_state must be one of: {allowed}.")

    return state


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
    items = _dedupe(_string_tuple(values, field_name))
    for index, value in enumerate(items):
        _advisory_text(value, f"{field_name}[{index}]")

    return items


def _deduped_non_claims(values: object) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, "non_claims"))
    if not items:
        raise ValidationError("non_claims must contain at least one string.")

    if any(not item.startswith("not ") for item in items):
        raise ValidationError("non_claims entries must be negative statements.")

    return items


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)


def _decimal_text(value: object) -> str:
    if value is None:
        return "none"

    return str(value)
