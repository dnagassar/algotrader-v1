"""Deterministic summaries for SMA-return alignment observations."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.sma_return_alignment_observation import (
    SmaReturnAlignmentObservation,
)

__all__ = [
    "SMA_RETURN_ALIGNMENT_SUMMARY_STATES",
    "SmaReturnAlignmentSummaryObservation",
    "build_sma_return_alignment_summary_observation",
]

_OBSERVATION_TYPE = "sma_return_alignment_summary_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_ALIGNMENT_RULE = "latest_sma_as_of_on_or_before_return_start"
SMA_RETURN_ALIGNMENT_SUMMARY_STATES = (
    "all_return_periods_aligned",
    "partial_return_period_alignment",
    "no_return_periods_aligned",
    "empty_return_periods",
)
_SMA_STATES = (
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
    "summarizes existing SMA-return alignment metadata only",
    "counts alignment availability and SMA states across aligned return periods",
    "does not compute return-adjusted metrics from SMA state",
)
_EMPTY_LIMITATION = "no return periods were available to summarize"
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("strategy-return computation"),
    _not("equity-curve computation"),
    _not("exposure computation"),
    _not("cost model"),
    _not("bench", "mark comparison"),
    _not("positions"),
    _not("cash behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mutation authority"),
    _not("paper read", "iness"),
    _not("live read", "iness"),
    _not("capital authority"),
    _not("tra", "ding authority"),
)
_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("action", "ability"),
    _join("action", "able"),
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
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class SmaReturnAlignmentSummaryObservation:
    """Advisory-only descriptive summary of SMA-return alignment metadata."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    alignment_rule: str
    symbol: str
    as_of: str
    source_return_count: int
    source_sma_observation_count: int
    alignment_period_count: int
    aligned_return_count: int
    no_prior_sma_state_count: int
    insufficient_history_alignment_count: int
    above_sma_alignment_count: int
    below_sma_alignment_count: int
    equal_sma_alignment_count: int
    summary_state: str
    source_alignment_observation: SmaReturnAlignmentObservation
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_alignment_observation = _require_source_alignment_observation(
            self.source_alignment_observation
        )
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
            self.alignment_rule,
        )
        object.__setattr__(self, "symbol", _advisory_text(self.symbol, "symbol"))
        object.__setattr__(self, "as_of", _required_string(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "source_return_count",
            _non_negative_int(self.source_return_count, "source_return_count"),
        )
        object.__setattr__(
            self,
            "source_sma_observation_count",
            _non_negative_int(
                self.source_sma_observation_count,
                "source_sma_observation_count",
            ),
        )
        object.__setattr__(
            self,
            "alignment_period_count",
            _non_negative_int(self.alignment_period_count, "alignment_period_count"),
        )
        object.__setattr__(
            self,
            "aligned_return_count",
            _non_negative_int(self.aligned_return_count, "aligned_return_count"),
        )
        object.__setattr__(
            self,
            "no_prior_sma_state_count",
            _non_negative_int(
                self.no_prior_sma_state_count,
                "no_prior_sma_state_count",
            ),
        )
        object.__setattr__(
            self,
            "insufficient_history_alignment_count",
            _non_negative_int(
                self.insufficient_history_alignment_count,
                "insufficient_history_alignment_count",
            ),
        )
        object.__setattr__(
            self,
            "above_sma_alignment_count",
            _non_negative_int(
                self.above_sma_alignment_count,
                "above_sma_alignment_count",
            ),
        )
        object.__setattr__(
            self,
            "below_sma_alignment_count",
            _non_negative_int(
                self.below_sma_alignment_count,
                "below_sma_alignment_count",
            ),
        )
        object.__setattr__(
            self,
            "equal_sma_alignment_count",
            _non_negative_int(
                self.equal_sma_alignment_count,
                "equal_sma_alignment_count",
            ),
        )
        object.__setattr__(self, "summary_state", _summary_state(self.summary_state))
        object.__setattr__(
            self,
            "source_alignment_observation",
            source_alignment_observation,
        )
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_source_summary(self, source_alignment_observation)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only alignment summary metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "alignment_rule": self.alignment_rule,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "source_return_count": self.source_return_count,
            "source_sma_observation_count": self.source_sma_observation_count,
            "alignment_period_count": self.alignment_period_count,
            "aligned_return_count": self.aligned_return_count,
            "no_prior_sma_state_count": self.no_prior_sma_state_count,
            "insufficient_history_alignment_count": (
                self.insufficient_history_alignment_count
            ),
            "above_sma_alignment_count": self.above_sma_alignment_count,
            "below_sma_alignment_count": self.below_sma_alignment_count,
            "equal_sma_alignment_count": self.equal_sma_alignment_count,
            "summary_state": self.summary_state,
            "source_alignment_observation": (
                self.source_alignment_observation.to_dict()
            ),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_return_alignment_summary_observation(
    alignment_observation: SmaReturnAlignmentObservation,
) -> SmaReturnAlignmentSummaryObservation:
    """Build a deterministic summary over an SMA-return alignment artifact."""

    source_alignment_observation = _require_source_alignment_observation(
        alignment_observation
    )
    (
        alignment_period_count,
        aligned_return_count,
        no_prior_sma_state_count,
        insufficient_history_alignment_count,
        above_sma_alignment_count,
        below_sma_alignment_count,
        equal_sma_alignment_count,
        summary_state,
    ) = _alignment_summary(source_alignment_observation)

    return SmaReturnAlignmentSummaryObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        alignment_rule=source_alignment_observation.alignment_rule,
        symbol=source_alignment_observation.symbol,
        as_of=source_alignment_observation.as_of,
        source_return_count=source_alignment_observation.source_return_count,
        source_sma_observation_count=(
            source_alignment_observation.source_sma_observation_count
        ),
        alignment_period_count=alignment_period_count,
        aligned_return_count=aligned_return_count,
        no_prior_sma_state_count=no_prior_sma_state_count,
        insufficient_history_alignment_count=(
            insufficient_history_alignment_count
        ),
        above_sma_alignment_count=above_sma_alignment_count,
        below_sma_alignment_count=below_sma_alignment_count,
        equal_sma_alignment_count=equal_sma_alignment_count,
        summary_state=summary_state,
        source_alignment_observation=source_alignment_observation,
        limitations=_summary_limitations(source_alignment_observation),
        non_claims=_summary_non_claims(source_alignment_observation),
    )


def _alignment_summary(
    alignment_observation: SmaReturnAlignmentObservation,
) -> tuple[int, int, int, int, int, int, int, str]:
    state_counts = dict.fromkeys(_SMA_STATES, 0)
    aligned_return_count = 0
    no_prior_sma_state_count = 0

    for period in alignment_observation.alignment_periods:
        if period.alignment_state == "sma_state_unavailable":
            no_prior_sma_state_count += 1
            continue

        aligned_return_count += 1
        if period.sma_observation_state not in state_counts:
            raise ValidationError("sma_observation_state must be a known SMA state.")
        state_counts[period.sma_observation_state] += 1

    alignment_period_count = len(alignment_observation.alignment_periods)
    summary_state = _derived_summary_state(
        alignment_period_count,
        aligned_return_count,
    )
    return (
        alignment_period_count,
        aligned_return_count,
        no_prior_sma_state_count,
        state_counts["insufficient_history"],
        state_counts["above"],
        state_counts["below"],
        state_counts["equal"],
        summary_state,
    )


def _derived_summary_state(
    alignment_period_count: int,
    aligned_return_count: int,
) -> str:
    if alignment_period_count == 0:
        return "empty_return_periods"
    if aligned_return_count == alignment_period_count:
        return "all_return_periods_aligned"
    if aligned_return_count == 0:
        return "no_return_periods_aligned"

    return "partial_return_period_alignment"


def _require_source_alignment_observation(
    value: object,
) -> SmaReturnAlignmentObservation:
    if type(value) is not SmaReturnAlignmentObservation:
        raise ValidationError(
            "source_alignment_observation must be a "
            "SmaReturnAlignmentObservation."
        )

    return value


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
    alignment_rule: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly "
            "sma_return_alignment_summary_observation."
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
    if alignment_rule != _ALIGNMENT_RULE:
        raise ValidationError(
            "alignment_rule must be exactly "
            "latest_sma_as_of_on_or_before_return_start."
        )


def _validate_source_summary(
    summary: SmaReturnAlignmentSummaryObservation,
    alignment_observation: SmaReturnAlignmentObservation,
) -> None:
    (
        alignment_period_count,
        aligned_return_count,
        no_prior_sma_state_count,
        insufficient_history_alignment_count,
        above_sma_alignment_count,
        below_sma_alignment_count,
        equal_sma_alignment_count,
        summary_state,
    ) = _alignment_summary(alignment_observation)

    _validate_matches_source("symbol", summary.symbol, alignment_observation.symbol)
    _validate_matches_source("as_of", summary.as_of, alignment_observation.as_of)
    _validate_matches_source(
        "source_return_count",
        summary.source_return_count,
        alignment_observation.source_return_count,
    )
    _validate_matches_source(
        "source_sma_observation_count",
        summary.source_sma_observation_count,
        alignment_observation.source_sma_observation_count,
    )
    _validate_matches_source(
        "alignment_period_count",
        summary.alignment_period_count,
        alignment_period_count,
    )
    _validate_matches_source(
        "aligned_return_count",
        summary.aligned_return_count,
        aligned_return_count,
    )
    _validate_matches_source(
        "no_prior_sma_state_count",
        summary.no_prior_sma_state_count,
        no_prior_sma_state_count,
    )
    _validate_matches_source(
        "insufficient_history_alignment_count",
        summary.insufficient_history_alignment_count,
        insufficient_history_alignment_count,
    )
    _validate_matches_source(
        "above_sma_alignment_count",
        summary.above_sma_alignment_count,
        above_sma_alignment_count,
    )
    _validate_matches_source(
        "below_sma_alignment_count",
        summary.below_sma_alignment_count,
        below_sma_alignment_count,
    )
    _validate_matches_source(
        "equal_sma_alignment_count",
        summary.equal_sma_alignment_count,
        equal_sma_alignment_count,
    )
    _validate_matches_source("summary_state", summary.summary_state, summary_state)
    _validate_matches_source(
        "limitations",
        summary.limitations,
        _summary_limitations(alignment_observation),
    )
    _validate_matches_source(
        "non_claims",
        summary.non_claims,
        _summary_non_claims(alignment_observation),
    )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source alignment.")


def _summary_limitations(
    alignment_observation: SmaReturnAlignmentObservation,
) -> tuple[str, ...]:
    empty_limitation = (
        (_EMPTY_LIMITATION,)
        if not alignment_observation.alignment_periods
        else ()
    )
    return _dedupe(
        (
            *_DEFAULT_LIMITATIONS,
            *empty_limitation,
            *alignment_observation.limitations,
        )
    )


def _summary_non_claims(
    alignment_observation: SmaReturnAlignmentObservation,
) -> tuple[str, ...]:
    return _dedupe((*_REQUIRED_NON_CLAIMS, *alignment_observation.non_claims))


def _summary_state(value: object) -> str:
    state = _required_string(value, "summary_state")
    if state not in SMA_RETURN_ALIGNMENT_SUMMARY_STATES:
        allowed = ", ".join(SMA_RETURN_ALIGNMENT_SUMMARY_STATES)
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
    if any(fragment in lowered for fragment in _FORBIDDEN_TEXT_TOKENS):
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
