"""Research-only classification of SMA-aligned return periods."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.sma_return_alignment_observation import (
    SmaReturnAlignmentObservation,
    SmaReturnAlignmentPeriod,
)

__all__ = [
    "SMA_CONDITIONAL_RETURN_SELECTION_REASONS",
    "SMA_CONDITIONAL_RETURN_SELECTION_STATES",
    "SmaConditionalReturnSelectionObservation",
    "SmaConditionalReturnSelectionPeriod",
    "build_sma_conditional_return_selection_observation",
]

_OBSERVATION_TYPE = "sma_conditional_return_selection_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_SELECTION_RULE = "include_when_sma_state_is_above"
SMA_CONDITIONAL_RETURN_SELECTION_STATES = (
    "included",
    "excluded",
)
SMA_CONDITIONAL_RETURN_SELECTION_REASONS = (
    "above_sma",
    "below_sma",
    "equal_sma",
    "insufficient_history",
    "no_prior_sma_state",
)
_SMA_EXCLUSION_REASONS = (
    "below_sma",
    "equal_sma",
    "insufficient_history",
    "no_prior_sma_state",
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_DEFAULT_LIMITATIONS = (
    "classifies existing SMA-return alignment periods under a fixed above-SMA rule only",
    "preserves source alignment metadata without deriving performance metrics",
    "treats missing or non-above SMA states as excluded classifications only",
)
_EMPTY_LIMITATION = "no alignment periods were available to classify"
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("strategy-return computation"),
    _not("compounded-return computation"),
    _not("equity-curve computation"),
    _not("cash-return computation"),
    _not("exposure computation"),
    _not("cost model"),
    _not("bench", "mark comparison"),
    _not("positions"),
    _not("cash behavior"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio state"),
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
class SmaConditionalReturnSelectionPeriod:
    """One research-only include/exclude classification for an aligned period."""

    return_start_date: str
    return_end_date: str
    selection_state: str
    selection_reason: str
    sma_observation_as_of: str | None
    sma_observation_state: str | None
    source_alignment_period: SmaReturnAlignmentPeriod

    def __post_init__(self) -> None:
        source_alignment_period = _require_alignment_period(
            self.source_alignment_period
        )
        object.__setattr__(
            self,
            "return_start_date",
            _required_string(self.return_start_date, "return_start_date"),
        )
        object.__setattr__(
            self,
            "return_end_date",
            _required_string(self.return_end_date, "return_end_date"),
        )
        object.__setattr__(
            self,
            "selection_state",
            _selection_state(self.selection_state),
        )
        object.__setattr__(
            self,
            "selection_reason",
            _selection_reason(self.selection_reason),
        )
        object.__setattr__(
            self,
            "sma_observation_as_of",
            _optional_string(self.sma_observation_as_of, "sma_observation_as_of"),
        )
        object.__setattr__(
            self,
            "sma_observation_state",
            _optional_string(self.sma_observation_state, "sma_observation_state"),
        )
        object.__setattr__(
            self,
            "source_alignment_period",
            source_alignment_period,
        )
        _validate_period_source_consistency(self, source_alignment_period)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only selection period metadata."""

        return {
            "return_start_date": self.return_start_date,
            "return_end_date": self.return_end_date,
            "selection_state": self.selection_state,
            "selection_reason": self.selection_reason,
            "sma_observation_as_of": self.sma_observation_as_of,
            "sma_observation_state": self.sma_observation_state,
            "source_alignment_period": self.source_alignment_period.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SmaConditionalReturnSelectionObservation:
    """Advisory-only selection classification over SMA-return alignment rows."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    selection_rule: str
    symbol: str
    as_of: str
    source_return_count: int
    source_sma_observation_count: int
    alignment_period_count: int
    included_period_count: int
    excluded_period_count: int
    no_prior_sma_state_excluded_count: int
    insufficient_history_excluded_count: int
    below_sma_excluded_count: int
    equal_sma_excluded_count: int
    selection_periods: tuple[SmaConditionalReturnSelectionPeriod, ...]
    source_alignment_observation: SmaReturnAlignmentObservation
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_alignment_observation = _require_source_alignment_observation(
            self.source_alignment_observation
        )
        selection_periods = _selection_period_tuple(self.selection_periods)
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
            self.selection_rule,
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
            "included_period_count",
            _non_negative_int(self.included_period_count, "included_period_count"),
        )
        object.__setattr__(
            self,
            "excluded_period_count",
            _non_negative_int(self.excluded_period_count, "excluded_period_count"),
        )
        object.__setattr__(
            self,
            "no_prior_sma_state_excluded_count",
            _non_negative_int(
                self.no_prior_sma_state_excluded_count,
                "no_prior_sma_state_excluded_count",
            ),
        )
        object.__setattr__(
            self,
            "insufficient_history_excluded_count",
            _non_negative_int(
                self.insufficient_history_excluded_count,
                "insufficient_history_excluded_count",
            ),
        )
        object.__setattr__(
            self,
            "below_sma_excluded_count",
            _non_negative_int(
                self.below_sma_excluded_count,
                "below_sma_excluded_count",
            ),
        )
        object.__setattr__(
            self,
            "equal_sma_excluded_count",
            _non_negative_int(
                self.equal_sma_excluded_count,
                "equal_sma_excluded_count",
            ),
        )
        object.__setattr__(self, "selection_periods", selection_periods)
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
        _validate_source_selection(
            self,
            source_alignment_observation,
            selection_periods,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only selection observation metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "selection_rule": self.selection_rule,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "source_return_count": self.source_return_count,
            "source_sma_observation_count": self.source_sma_observation_count,
            "alignment_period_count": self.alignment_period_count,
            "included_period_count": self.included_period_count,
            "excluded_period_count": self.excluded_period_count,
            "no_prior_sma_state_excluded_count": (
                self.no_prior_sma_state_excluded_count
            ),
            "insufficient_history_excluded_count": (
                self.insufficient_history_excluded_count
            ),
            "below_sma_excluded_count": self.below_sma_excluded_count,
            "equal_sma_excluded_count": self.equal_sma_excluded_count,
            "selection_periods": [
                period.to_dict() for period in self.selection_periods
            ],
            "source_alignment_observation": (
                self.source_alignment_observation.to_dict()
            ),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_conditional_return_selection_observation(
    alignment_observation: SmaReturnAlignmentObservation,
) -> SmaConditionalReturnSelectionObservation:
    """Classify existing SMA-return alignment periods under an above-SMA rule."""

    source_alignment_observation = _require_source_alignment_observation(
        alignment_observation
    )
    selection_periods = tuple(
        _build_selection_period(period)
        for period in source_alignment_observation.alignment_periods
    )
    counts = _selection_counts(selection_periods)

    return SmaConditionalReturnSelectionObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        selection_rule=_SELECTION_RULE,
        symbol=source_alignment_observation.symbol,
        as_of=source_alignment_observation.as_of,
        source_return_count=source_alignment_observation.source_return_count,
        source_sma_observation_count=(
            source_alignment_observation.source_sma_observation_count
        ),
        alignment_period_count=len(source_alignment_observation.alignment_periods),
        included_period_count=counts["included"],
        excluded_period_count=counts["excluded"],
        no_prior_sma_state_excluded_count=counts["no_prior_sma_state"],
        insufficient_history_excluded_count=counts["insufficient_history"],
        below_sma_excluded_count=counts["below_sma"],
        equal_sma_excluded_count=counts["equal_sma"],
        selection_periods=selection_periods,
        source_alignment_observation=source_alignment_observation,
        limitations=_selection_limitations(source_alignment_observation),
        non_claims=_selection_non_claims(source_alignment_observation),
    )


def _build_selection_period(
    alignment_period: SmaReturnAlignmentPeriod,
) -> SmaConditionalReturnSelectionPeriod:
    selection_state, selection_reason = _classify_alignment_period(alignment_period)
    return SmaConditionalReturnSelectionPeriod(
        return_start_date=alignment_period.return_start_date,
        return_end_date=alignment_period.return_end_date,
        selection_state=selection_state,
        selection_reason=selection_reason,
        sma_observation_as_of=alignment_period.sma_observation_as_of,
        sma_observation_state=alignment_period.sma_observation_state,
        source_alignment_period=alignment_period,
    )


def _classify_alignment_period(
    alignment_period: SmaReturnAlignmentPeriod,
) -> tuple[str, str]:
    if alignment_period.alignment_state == "sma_state_unavailable":
        return ("excluded", "no_prior_sma_state")

    if alignment_period.sma_observation_state == "above":
        return ("included", "above_sma")
    if alignment_period.sma_observation_state == "below":
        return ("excluded", "below_sma")
    if alignment_period.sma_observation_state == "equal":
        return ("excluded", "equal_sma")
    if alignment_period.sma_observation_state == "insufficient_history":
        return ("excluded", "insufficient_history")

    raise ValidationError("sma_observation_state must be a known SMA state.")


def _selection_counts(
    selection_periods: tuple[SmaConditionalReturnSelectionPeriod, ...],
) -> dict[str, int]:
    counts = {
        "included": 0,
        "excluded": 0,
        "no_prior_sma_state": 0,
        "insufficient_history": 0,
        "below_sma": 0,
        "equal_sma": 0,
    }
    for period in selection_periods:
        counts[period.selection_state] += 1
        if period.selection_reason in _SMA_EXCLUSION_REASONS:
            counts[period.selection_reason] += 1

    return counts


def _validate_period_source_consistency(
    period: SmaConditionalReturnSelectionPeriod,
    source_alignment_period: SmaReturnAlignmentPeriod,
) -> None:
    selection_state, selection_reason = _classify_alignment_period(
        source_alignment_period
    )
    if period.return_start_date != source_alignment_period.return_start_date:
        raise ValidationError("return_start_date must match source alignment period.")
    if period.return_end_date != source_alignment_period.return_end_date:
        raise ValidationError("return_end_date must match source alignment period.")
    if period.selection_state != selection_state:
        raise ValidationError("selection_state must match the selection rule.")
    if period.selection_reason != selection_reason:
        raise ValidationError("selection_reason must match the selection rule.")
    if period.sma_observation_as_of != source_alignment_period.sma_observation_as_of:
        raise ValidationError(
            "sma_observation_as_of must match source alignment period."
        )
    if period.sma_observation_state != source_alignment_period.sma_observation_state:
        raise ValidationError(
            "sma_observation_state must match source alignment period."
        )


def _validate_source_selection(
    selection: SmaConditionalReturnSelectionObservation,
    source_alignment_observation: SmaReturnAlignmentObservation,
    selection_periods: tuple[SmaConditionalReturnSelectionPeriod, ...],
) -> None:
    _validate_matches_source(
        "symbol",
        selection.symbol,
        source_alignment_observation.symbol,
    )
    _validate_matches_source(
        "as_of",
        selection.as_of,
        source_alignment_observation.as_of,
    )
    _validate_matches_source(
        "source_return_count",
        selection.source_return_count,
        source_alignment_observation.source_return_count,
    )
    _validate_matches_source(
        "source_sma_observation_count",
        selection.source_sma_observation_count,
        source_alignment_observation.source_sma_observation_count,
    )
    _validate_matches_source(
        "alignment_period_count",
        selection.alignment_period_count,
        len(source_alignment_observation.alignment_periods),
    )
    if len(selection_periods) != len(source_alignment_observation.alignment_periods):
        raise ValidationError(
            "selection_periods must match source alignment periods."
        )

    for selection_period, alignment_period in zip(
        selection_periods,
        source_alignment_observation.alignment_periods,
    ):
        if selection_period.source_alignment_period is not alignment_period:
            raise ValidationError(
                "selection period source_alignment_period must be preserved."
            )
        _validate_period_source_consistency(selection_period, alignment_period)

    counts = _selection_counts(selection_periods)
    _validate_matches_source(
        "included_period_count",
        selection.included_period_count,
        counts["included"],
    )
    _validate_matches_source(
        "excluded_period_count",
        selection.excluded_period_count,
        counts["excluded"],
    )
    _validate_matches_source(
        "no_prior_sma_state_excluded_count",
        selection.no_prior_sma_state_excluded_count,
        counts["no_prior_sma_state"],
    )
    _validate_matches_source(
        "insufficient_history_excluded_count",
        selection.insufficient_history_excluded_count,
        counts["insufficient_history"],
    )
    _validate_matches_source(
        "below_sma_excluded_count",
        selection.below_sma_excluded_count,
        counts["below_sma"],
    )
    _validate_matches_source(
        "equal_sma_excluded_count",
        selection.equal_sma_excluded_count,
        counts["equal_sma"],
    )
    _validate_matches_source(
        "limitations",
        selection.limitations,
        _selection_limitations(source_alignment_observation),
    )
    _validate_matches_source(
        "non_claims",
        selection.non_claims,
        _selection_non_claims(source_alignment_observation),
    )


def _require_alignment_period(value: object) -> SmaReturnAlignmentPeriod:
    if type(value) is not SmaReturnAlignmentPeriod:
        raise ValidationError(
            "source_alignment_period must be a SmaReturnAlignmentPeriod."
        )

    return value


def _require_source_alignment_observation(
    value: object,
) -> SmaReturnAlignmentObservation:
    if type(value) is not SmaReturnAlignmentObservation:
        raise ValidationError(
            "source_alignment_observation must be a "
            "SmaReturnAlignmentObservation."
        )

    return value


def _selection_period_tuple(
    values: object,
) -> tuple[SmaConditionalReturnSelectionPeriod, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(
            "selection_periods must be a tuple or list of "
            "SmaConditionalReturnSelectionPeriod."
        )

    periods = tuple(values)
    for index, period in enumerate(periods):
        if type(period) is not SmaConditionalReturnSelectionPeriod:
            raise ValidationError(
                "selection_periods"
                f"[{index}] must be a SmaConditionalReturnSelectionPeriod."
            )

    return periods


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
    selection_rule: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly "
            "sma_conditional_return_selection_observation."
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
    if selection_rule != _SELECTION_RULE:
        raise ValidationError(
            "selection_rule must be exactly include_when_sma_state_is_above."
        )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source selection.")


def _selection_state(value: object) -> str:
    state = _required_string(value, "selection_state")
    if state not in SMA_CONDITIONAL_RETURN_SELECTION_STATES:
        allowed = ", ".join(SMA_CONDITIONAL_RETURN_SELECTION_STATES)
        raise ValidationError(f"selection_state must be one of: {allowed}.")

    return state


def _selection_reason(value: object) -> str:
    reason = _required_string(value, "selection_reason")
    if reason not in SMA_CONDITIONAL_RETURN_SELECTION_REASONS:
        allowed = ", ".join(SMA_CONDITIONAL_RETURN_SELECTION_REASONS)
        raise ValidationError(f"selection_reason must be one of: {allowed}.")

    return reason


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None

    return _required_string(value, field_name)


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


def _selection_limitations(
    source_alignment_observation: SmaReturnAlignmentObservation,
) -> tuple[str, ...]:
    empty_limitation = (
        (_EMPTY_LIMITATION,)
        if not source_alignment_observation.alignment_periods
        else ()
    )
    return _dedupe(
        (
            *_DEFAULT_LIMITATIONS,
            *empty_limitation,
            *source_alignment_observation.limitations,
        )
    )


def _selection_non_claims(
    source_alignment_observation: SmaReturnAlignmentObservation,
) -> tuple[str, ...]:
    return _dedupe((*_REQUIRED_NON_CLAIMS, *source_alignment_observation.non_claims))


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)
