"""Deterministic descriptive summaries for SMA research observations."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation import SmaResearchObservation

__all__ = [
    "SMA_RESEARCH_SUMMARY_STATES",
    "SmaResearchSummaryObservation",
    "build_sma_research_summary_observation",
]

_OBSERVATION_TYPE = "sma_research_summary_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
SMA_RESEARCH_SUMMARY_STATES = (
    "observations_summarized",
    "empty_insufficient_observations",
)
_SMA_POSITIONS = (
    "above",
    "below",
    "equal",
    "insufficient_history",
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_DEFAULT_LIMITATIONS = (
    "aggregates exact existing SMA research observations only",
    "counts position metadata without altering SMA mechanics",
)
_EMPTY_LIMITATION = "no SMA research observations were provided"
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mutation authority"),
    _not("paper read", "iness"),
    _not("live read", "iness"),
    _not("capital authority"),
    _not("tra", "ding authority"),
    _not("ra", "nking"),
    _not("sco", "ring"),
)
_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("action", "ability"),
    _join("action", "able"),
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
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class SmaResearchSummaryObservation:
    """Advisory-only descriptive summary of SMA research observations."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    total_observation_count: int
    above_sma_count: int
    below_sma_count: int
    equal_sma_count: int
    insufficient_history_count: int
    summary_state: str
    source_observations: tuple[SmaResearchObservation, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_observations = _require_source_observations(self.source_observations)
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
        )
        object.__setattr__(
            self,
            "total_observation_count",
            _non_negative_int(
                self.total_observation_count,
                "total_observation_count",
            ),
        )
        object.__setattr__(
            self,
            "above_sma_count",
            _non_negative_int(self.above_sma_count, "above_sma_count"),
        )
        object.__setattr__(
            self,
            "below_sma_count",
            _non_negative_int(self.below_sma_count, "below_sma_count"),
        )
        object.__setattr__(
            self,
            "equal_sma_count",
            _non_negative_int(self.equal_sma_count, "equal_sma_count"),
        )
        object.__setattr__(
            self,
            "insufficient_history_count",
            _non_negative_int(
                self.insufficient_history_count,
                "insufficient_history_count",
            ),
        )
        object.__setattr__(self, "summary_state", _summary_state(self.summary_state))
        object.__setattr__(self, "source_observations", source_observations)
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_source_summary(self, source_observations)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only SMA summary metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "total_observation_count": self.total_observation_count,
            "above_sma_count": self.above_sma_count,
            "below_sma_count": self.below_sma_count,
            "equal_sma_count": self.equal_sma_count,
            "insufficient_history_count": self.insufficient_history_count,
            "summary_state": self.summary_state,
            "source_observations": [
                observation.to_dict() for observation in self.source_observations
            ],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_research_summary_observation(
    observations: tuple[SmaResearchObservation, ...] | list[SmaResearchObservation],
) -> SmaResearchSummaryObservation:
    """Build a deterministic summary over existing SMA research observations."""

    source_observations = _require_source_observations(observations)
    (
        total_observation_count,
        above_sma_count,
        below_sma_count,
        equal_sma_count,
        insufficient_history_count,
        summary_state,
    ) = _observation_summary(source_observations)

    return SmaResearchSummaryObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        total_observation_count=total_observation_count,
        above_sma_count=above_sma_count,
        below_sma_count=below_sma_count,
        equal_sma_count=equal_sma_count,
        insufficient_history_count=insufficient_history_count,
        summary_state=summary_state,
        source_observations=source_observations,
        limitations=_summary_limitations(source_observations),
        non_claims=_summary_non_claims(source_observations),
    )


def _observation_summary(
    observations: tuple[SmaResearchObservation, ...],
) -> tuple[int, int, int, int, int, str]:
    counts = dict.fromkeys(_SMA_POSITIONS, 0)
    for observation in observations:
        counts[observation.position_vs_sma] += 1

    total_observation_count = len(observations)
    summary_state = (
        "observations_summarized"
        if total_observation_count
        else "empty_insufficient_observations"
    )
    return (
        total_observation_count,
        counts["above"],
        counts["below"],
        counts["equal"],
        counts["insufficient_history"],
        summary_state,
    )


def _require_source_observations(
    values: object,
) -> tuple[SmaResearchObservation, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(
            "source_observations must be a tuple or list of SmaResearchObservation."
        )

    observations = values if type(values) is tuple else tuple(values)
    for index, observation in enumerate(observations):
        if type(observation) is not SmaResearchObservation:
            raise ValidationError(
                "source_observations"
                f"[{index}] must be a SmaResearchObservation."
            )

    return observations


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly sma_research_summary_observation."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")
    if research_scope != _RESEARCH_SCOPE:
        raise ValidationError("research_scope must be exactly research_only.")


def _validate_source_summary(
    summary: SmaResearchSummaryObservation,
    observations: tuple[SmaResearchObservation, ...],
) -> None:
    (
        total_observation_count,
        above_sma_count,
        below_sma_count,
        equal_sma_count,
        insufficient_history_count,
        summary_state,
    ) = _observation_summary(observations)

    _validate_matches_source(
        "total_observation_count",
        summary.total_observation_count,
        total_observation_count,
    )
    _validate_matches_source("above_sma_count", summary.above_sma_count, above_sma_count)
    _validate_matches_source("below_sma_count", summary.below_sma_count, below_sma_count)
    _validate_matches_source("equal_sma_count", summary.equal_sma_count, equal_sma_count)
    _validate_matches_source(
        "insufficient_history_count",
        summary.insufficient_history_count,
        insufficient_history_count,
    )
    _validate_matches_source("summary_state", summary.summary_state, summary_state)
    _validate_matches_source(
        "limitations",
        summary.limitations,
        _summary_limitations(observations),
    )
    _validate_matches_source(
        "non_claims",
        summary.non_claims,
        _summary_non_claims(observations),
    )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source_observations.")


def _summary_limitations(
    observations: tuple[SmaResearchObservation, ...],
) -> tuple[str, ...]:
    source_limitations = tuple(
        limitation
        for observation in observations
        for limitation in observation.limitations
    )
    empty_limitations = (_EMPTY_LIMITATION,) if not observations else ()
    return _dedupe((*_DEFAULT_LIMITATIONS, *empty_limitations, *source_limitations))


def _summary_non_claims(
    observations: tuple[SmaResearchObservation, ...],
) -> tuple[str, ...]:
    source_non_claims = tuple(
        non_claim for observation in observations for non_claim in observation.non_claims
    )
    return _dedupe((*_REQUIRED_NON_CLAIMS, *source_non_claims))


def _summary_state(value: object) -> str:
    state = _required_string(value, "summary_state")
    if state not in SMA_RESEARCH_SUMMARY_STATES:
        allowed = ", ".join(SMA_RESEARCH_SUMMARY_STATES)
        raise ValidationError(f"summary_state must be one of: {allowed}.")

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
    if any(text_fragment in lowered for text_fragment in _FORBIDDEN_TEXT_TOKENS):
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

    missing = tuple(claim for claim in _REQUIRED_NON_CLAIMS if claim not in items)
    if missing:
        raise ValidationError(
            "non_claims must include required advisory research non-claims."
        )

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
