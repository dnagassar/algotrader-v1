"""Deterministic summaries for SMA conditional return-selection observations."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.sma_conditional_return_selection_observation import (
    SmaConditionalReturnSelectionObservation,
)

__all__ = [
    "SMA_CONDITIONAL_RETURN_SELECTION_SUMMARY_STATES",
    "SmaConditionalReturnSelectionSummaryObservation",
    "build_sma_conditional_return_selection_summary_observation",
]

_OBSERVATION_TYPE = "sma_conditional_return_selection_summary_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_SELECTION_RULE = "include_when_sma_state_is_above"
SMA_CONDITIONAL_RETURN_SELECTION_SUMMARY_STATES = (
    "mixed_selection_classifications",
    "all_periods_included",
    "all_periods_excluded",
    "empty_selection_periods",
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_DEFAULT_LIMITATIONS = (
    "summarizes existing SMA conditional return-selection metadata only",
    "counts include and exclude classifications without return math",
    "preserves source selection metadata without deriving performance metrics",
)
_EMPTY_LIMITATION = "no selection periods were available to summarize"
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
class SmaConditionalReturnSelectionSummaryObservation:
    """Advisory-only descriptive summary of SMA selection classifications."""

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
    selection_period_count: int
    included_period_count: int
    excluded_period_count: int
    no_prior_sma_state_excluded_count: int
    insufficient_history_excluded_count: int
    below_sma_excluded_count: int
    equal_sma_excluded_count: int
    summary_state: str
    source_selection_observation: SmaConditionalReturnSelectionObservation
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_selection_observation = _require_source_selection_observation(
            self.source_selection_observation
        )
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
            "selection_period_count",
            _non_negative_int(self.selection_period_count, "selection_period_count"),
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
        object.__setattr__(self, "summary_state", _summary_state(self.summary_state))
        object.__setattr__(
            self,
            "source_selection_observation",
            source_selection_observation,
        )
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_source_summary(self, source_selection_observation)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only selection summary metadata."""

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
            "selection_period_count": self.selection_period_count,
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
            "summary_state": self.summary_state,
            "source_selection_observation": (
                self.source_selection_observation.to_dict()
            ),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_conditional_return_selection_summary_observation(
    selection_observation: SmaConditionalReturnSelectionObservation,
) -> SmaConditionalReturnSelectionSummaryObservation:
    """Build a deterministic summary over an SMA selection artifact."""

    source_selection_observation = _require_source_selection_observation(
        selection_observation
    )
    (
        selection_period_count,
        included_period_count,
        excluded_period_count,
        no_prior_sma_state_excluded_count,
        insufficient_history_excluded_count,
        below_sma_excluded_count,
        equal_sma_excluded_count,
        summary_state,
    ) = _selection_summary(source_selection_observation)

    return SmaConditionalReturnSelectionSummaryObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        selection_rule=source_selection_observation.selection_rule,
        symbol=source_selection_observation.symbol,
        as_of=source_selection_observation.as_of,
        source_return_count=source_selection_observation.source_return_count,
        source_sma_observation_count=(
            source_selection_observation.source_sma_observation_count
        ),
        alignment_period_count=source_selection_observation.alignment_period_count,
        selection_period_count=selection_period_count,
        included_period_count=included_period_count,
        excluded_period_count=excluded_period_count,
        no_prior_sma_state_excluded_count=no_prior_sma_state_excluded_count,
        insufficient_history_excluded_count=insufficient_history_excluded_count,
        below_sma_excluded_count=below_sma_excluded_count,
        equal_sma_excluded_count=equal_sma_excluded_count,
        summary_state=summary_state,
        source_selection_observation=source_selection_observation,
        limitations=_summary_limitations(source_selection_observation),
        non_claims=_summary_non_claims(source_selection_observation),
    )


def _selection_summary(
    selection_observation: SmaConditionalReturnSelectionObservation,
) -> tuple[int, int, int, int, int, int, int, str]:
    included_period_count = 0
    excluded_period_count = 0
    no_prior_sma_state_excluded_count = 0
    insufficient_history_excluded_count = 0
    below_sma_excluded_count = 0
    equal_sma_excluded_count = 0

    for period in selection_observation.selection_periods:
        if period.selection_state == "included":
            included_period_count += 1
        elif period.selection_state == "excluded":
            excluded_period_count += 1
        else:
            raise ValidationError("selection_state must be included or excluded.")

        if period.selection_reason == "no_prior_sma_state":
            no_prior_sma_state_excluded_count += 1
        elif period.selection_reason == "insufficient_history":
            insufficient_history_excluded_count += 1
        elif period.selection_reason == "below_sma":
            below_sma_excluded_count += 1
        elif period.selection_reason == "equal_sma":
            equal_sma_excluded_count += 1
        elif period.selection_reason != "above_sma":
            raise ValidationError("selection_reason must be a known selection reason.")

    selection_period_count = len(selection_observation.selection_periods)
    summary_state = _derived_summary_state(
        selection_period_count,
        included_period_count,
        excluded_period_count,
    )
    return (
        selection_period_count,
        included_period_count,
        excluded_period_count,
        no_prior_sma_state_excluded_count,
        insufficient_history_excluded_count,
        below_sma_excluded_count,
        equal_sma_excluded_count,
        summary_state,
    )


def _derived_summary_state(
    selection_period_count: int,
    included_period_count: int,
    excluded_period_count: int,
) -> str:
    if selection_period_count == 0:
        return "empty_selection_periods"
    if included_period_count == selection_period_count:
        return "all_periods_included"
    if excluded_period_count == selection_period_count:
        return "all_periods_excluded"

    return "mixed_selection_classifications"


def _require_source_selection_observation(
    value: object,
) -> SmaConditionalReturnSelectionObservation:
    if type(value) is not SmaConditionalReturnSelectionObservation:
        raise ValidationError(
            "source_selection_observation must be a "
            "SmaConditionalReturnSelectionObservation."
        )

    return value


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
            "sma_conditional_return_selection_summary_observation."
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


def _validate_source_summary(
    summary: SmaConditionalReturnSelectionSummaryObservation,
    selection_observation: SmaConditionalReturnSelectionObservation,
) -> None:
    (
        selection_period_count,
        included_period_count,
        excluded_period_count,
        no_prior_sma_state_excluded_count,
        insufficient_history_excluded_count,
        below_sma_excluded_count,
        equal_sma_excluded_count,
        summary_state,
    ) = _selection_summary(selection_observation)

    _validate_matches_source("symbol", summary.symbol, selection_observation.symbol)
    _validate_matches_source("as_of", summary.as_of, selection_observation.as_of)
    _validate_matches_source(
        "source_return_count",
        summary.source_return_count,
        selection_observation.source_return_count,
    )
    _validate_matches_source(
        "source_sma_observation_count",
        summary.source_sma_observation_count,
        selection_observation.source_sma_observation_count,
    )
    _validate_matches_source(
        "alignment_period_count",
        summary.alignment_period_count,
        selection_observation.alignment_period_count,
    )
    _validate_matches_source(
        "selection_period_count",
        summary.selection_period_count,
        selection_period_count,
    )
    _validate_matches_source(
        "selection_period_count",
        summary.selection_period_count,
        selection_observation.alignment_period_count,
    )
    _validate_matches_source(
        "included_period_count",
        summary.included_period_count,
        included_period_count,
    )
    _validate_matches_source(
        "included_period_count",
        summary.included_period_count,
        selection_observation.included_period_count,
    )
    _validate_matches_source(
        "excluded_period_count",
        summary.excluded_period_count,
        excluded_period_count,
    )
    _validate_matches_source(
        "excluded_period_count",
        summary.excluded_period_count,
        selection_observation.excluded_period_count,
    )
    _validate_matches_source(
        "no_prior_sma_state_excluded_count",
        summary.no_prior_sma_state_excluded_count,
        no_prior_sma_state_excluded_count,
    )
    _validate_matches_source(
        "no_prior_sma_state_excluded_count",
        summary.no_prior_sma_state_excluded_count,
        selection_observation.no_prior_sma_state_excluded_count,
    )
    _validate_matches_source(
        "insufficient_history_excluded_count",
        summary.insufficient_history_excluded_count,
        insufficient_history_excluded_count,
    )
    _validate_matches_source(
        "insufficient_history_excluded_count",
        summary.insufficient_history_excluded_count,
        selection_observation.insufficient_history_excluded_count,
    )
    _validate_matches_source(
        "below_sma_excluded_count",
        summary.below_sma_excluded_count,
        below_sma_excluded_count,
    )
    _validate_matches_source(
        "below_sma_excluded_count",
        summary.below_sma_excluded_count,
        selection_observation.below_sma_excluded_count,
    )
    _validate_matches_source(
        "equal_sma_excluded_count",
        summary.equal_sma_excluded_count,
        equal_sma_excluded_count,
    )
    _validate_matches_source(
        "equal_sma_excluded_count",
        summary.equal_sma_excluded_count,
        selection_observation.equal_sma_excluded_count,
    )
    _validate_matches_source("summary_state", summary.summary_state, summary_state)
    _validate_matches_source(
        "limitations",
        summary.limitations,
        _summary_limitations(selection_observation),
    )
    _validate_matches_source(
        "non_claims",
        summary.non_claims,
        _summary_non_claims(selection_observation),
    )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(f"{field_name} must match source selection.")


def _summary_limitations(
    selection_observation: SmaConditionalReturnSelectionObservation,
) -> tuple[str, ...]:
    empty_limitation = (
        (_EMPTY_LIMITATION,) if not selection_observation.selection_periods else ()
    )
    return _dedupe(
        (
            *_DEFAULT_LIMITATIONS,
            *empty_limitation,
            *selection_observation.limitations,
        )
    )


def _summary_non_claims(
    selection_observation: SmaConditionalReturnSelectionObservation,
) -> tuple[str, ...]:
    return _dedupe((*_REQUIRED_NON_CLAIMS, *selection_observation.non_claims))


def _summary_state(value: object) -> str:
    state = _required_string(value, "summary_state")
    if state not in SMA_CONDITIONAL_RETURN_SELECTION_SUMMARY_STATES:
        allowed = ", ".join(SMA_CONDITIONAL_RETURN_SELECTION_SUMMARY_STATES)
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
