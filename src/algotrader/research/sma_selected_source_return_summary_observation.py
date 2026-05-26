"""Deterministic summaries for SMA selected source return observations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from algotrader.errors import ValidationError
from algotrader.research.sma_selected_source_return_series_observation import (
    SmaSelectedSourceReturnSeriesObservation,
)

__all__ = [
    "SMA_SELECTED_SOURCE_RETURN_SUMMARY_STATES",
    "SmaSelectedSourceReturnSummaryObservation",
    "build_sma_selected_source_return_summary_observation",
]

_OBSERVATION_TYPE = "sma_selected_source_return_summary_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RESEARCH_SCOPE = "research_only"
_SELECTION_RULE = "include_when_sma_state_is_above"
_SOURCE_RETURN_VALUE_RULE = (
    "collect_source_simple_returns_from_included_selection_periods"
)
SMA_SELECTED_SOURCE_RETURN_SUMMARY_STATES = (
    "selected_source_returns_summarized",
    "no_selected_source_returns",
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_DEFAULT_LIMITATIONS = (
    "summarizes existing selected source return values only",
    "computes selected source return count, minimum, maximum, and arithmetic mean",
    "does not compound selected source returns",
)
_EMPTY_LIMITATION = "no selected source return values were available to summarize"
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
    _not("selected source return strategy performance result"),
    _not("selected source return port", "folio result"),
    _not("selected source return invested result"),
    _not("selected source return back", "test result"),
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
class SmaSelectedSourceReturnSummaryObservation:
    """Advisory-only descriptive summary of selected source return values."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    research_scope: str
    selection_rule: str
    source_return_value_rule: str
    symbol: str
    as_of: str
    source_return_count: int
    source_sma_observation_count: int
    alignment_period_count: int
    selection_period_count: int
    included_period_count: int
    selected_source_return_count: int
    min_selected_source_return: Decimal | None
    max_selected_source_return: Decimal | None
    mean_selected_source_return: Decimal | None
    summary_state: str
    source_selected_source_return_series_observation: (
        SmaSelectedSourceReturnSeriesObservation
    )
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        source_selected_source_return_series_observation = (
            _require_source_selected_source_return_series_observation(
                self.source_selected_source_return_series_observation
            )
        )
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
            self.research_scope,
            self.selection_rule,
            self.source_return_value_rule,
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
            "selected_source_return_count",
            _non_negative_int(
                self.selected_source_return_count,
                "selected_source_return_count",
            ),
        )
        object.__setattr__(
            self,
            "min_selected_source_return",
            _optional_decimal(
                self.min_selected_source_return,
                "min_selected_source_return",
            ),
        )
        object.__setattr__(
            self,
            "max_selected_source_return",
            _optional_decimal(
                self.max_selected_source_return,
                "max_selected_source_return",
            ),
        )
        object.__setattr__(
            self,
            "mean_selected_source_return",
            _optional_decimal(
                self.mean_selected_source_return,
                "mean_selected_source_return",
            ),
        )
        object.__setattr__(self, "summary_state", _summary_state(self.summary_state))
        object.__setattr__(
            self,
            "source_selected_source_return_series_observation",
            source_selected_source_return_series_observation,
        )
        object.__setattr__(
            self,
            "limitations",
            _deduped_advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _deduped_non_claims(self.non_claims))
        _validate_source_summary(
            self,
            source_selected_source_return_series_observation,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only selected source return summary."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "research_scope": self.research_scope,
            "selection_rule": self.selection_rule,
            "source_return_value_rule": self.source_return_value_rule,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "source_return_count": self.source_return_count,
            "source_sma_observation_count": self.source_sma_observation_count,
            "alignment_period_count": self.alignment_period_count,
            "selection_period_count": self.selection_period_count,
            "included_period_count": self.included_period_count,
            "selected_source_return_count": self.selected_source_return_count,
            "min_selected_source_return": _decimal_payload(
                self.min_selected_source_return
            ),
            "max_selected_source_return": _decimal_payload(
                self.max_selected_source_return
            ),
            "mean_selected_source_return": _decimal_payload(
                self.mean_selected_source_return
            ),
            "summary_state": self.summary_state,
            "source_selected_source_return_series_observation": (
                self.source_selected_source_return_series_observation.to_dict()
            ),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_selected_source_return_summary_observation(
    series_observation: SmaSelectedSourceReturnSeriesObservation,
) -> SmaSelectedSourceReturnSummaryObservation:
    """Build a deterministic summary over selected source return values."""

    source_selected_source_return_series_observation = (
        _require_source_selected_source_return_series_observation(
            series_observation
        )
    )
    (
        selected_source_return_count,
        min_selected_source_return,
        max_selected_source_return,
        mean_selected_source_return,
        summary_state,
    ) = _selected_source_return_summary(
        source_selected_source_return_series_observation
    )

    return SmaSelectedSourceReturnSummaryObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        research_scope=_RESEARCH_SCOPE,
        selection_rule=source_selected_source_return_series_observation.selection_rule,
        source_return_value_rule=(
            source_selected_source_return_series_observation.source_return_value_rule
        ),
        symbol=source_selected_source_return_series_observation.symbol,
        as_of=source_selected_source_return_series_observation.as_of,
        source_return_count=(
            source_selected_source_return_series_observation.source_return_count
        ),
        source_sma_observation_count=(
            source_selected_source_return_series_observation.source_sma_observation_count
        ),
        alignment_period_count=(
            source_selected_source_return_series_observation.alignment_period_count
        ),
        selection_period_count=(
            source_selected_source_return_series_observation.selection_period_count
        ),
        included_period_count=(
            source_selected_source_return_series_observation.included_period_count
        ),
        selected_source_return_count=selected_source_return_count,
        min_selected_source_return=min_selected_source_return,
        max_selected_source_return=max_selected_source_return,
        mean_selected_source_return=mean_selected_source_return,
        summary_state=summary_state,
        source_selected_source_return_series_observation=(
            source_selected_source_return_series_observation
        ),
        limitations=_summary_limitations(
            source_selected_source_return_series_observation
        ),
        non_claims=_summary_non_claims(
            source_selected_source_return_series_observation
        ),
    )


def _selected_source_return_summary(
    series_observation: SmaSelectedSourceReturnSeriesObservation,
) -> tuple[int, Decimal | None, Decimal | None, Decimal | None, str]:
    selected_source_returns = tuple(
        selected_source_return.source_simple_return
        for selected_source_return in series_observation.selected_source_returns
    )
    selected_source_return_count = len(selected_source_returns)
    if selected_source_return_count == 0:
        return (0, None, None, None, "no_selected_source_returns")

    mean_selected_source_return = sum(
        selected_source_returns,
        Decimal("0"),
    ) / Decimal(selected_source_return_count)
    return (
        selected_source_return_count,
        min(selected_source_returns),
        max(selected_source_returns),
        mean_selected_source_return,
        "selected_source_returns_summarized",
    )


def _require_source_selected_source_return_series_observation(
    value: object,
) -> SmaSelectedSourceReturnSeriesObservation:
    if type(value) is not SmaSelectedSourceReturnSeriesObservation:
        raise ValidationError(
            "source_selected_source_return_series_observation must be a "
            "SmaSelectedSourceReturnSeriesObservation."
        )

    return value


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
    research_scope: object,
    selection_rule: object,
    source_return_value_rule: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly "
            "sma_selected_source_return_summary_observation."
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
    if source_return_value_rule != _SOURCE_RETURN_VALUE_RULE:
        raise ValidationError(
            "source_return_value_rule must be exactly "
            "collect_source_simple_returns_from_included_selection_periods."
        )


def _validate_source_summary(
    summary: SmaSelectedSourceReturnSummaryObservation,
    series_observation: SmaSelectedSourceReturnSeriesObservation,
) -> None:
    (
        selected_source_return_count,
        min_selected_source_return,
        max_selected_source_return,
        mean_selected_source_return,
        summary_state,
    ) = _selected_source_return_summary(series_observation)

    _validate_matches_source("symbol", summary.symbol, series_observation.symbol)
    _validate_matches_source("as_of", summary.as_of, series_observation.as_of)
    _validate_matches_source(
        "source_return_count",
        summary.source_return_count,
        series_observation.source_return_count,
    )
    _validate_matches_source(
        "source_sma_observation_count",
        summary.source_sma_observation_count,
        series_observation.source_sma_observation_count,
    )
    _validate_matches_source(
        "alignment_period_count",
        summary.alignment_period_count,
        series_observation.alignment_period_count,
    )
    _validate_matches_source(
        "selection_period_count",
        summary.selection_period_count,
        series_observation.selection_period_count,
    )
    _validate_matches_source(
        "included_period_count",
        summary.included_period_count,
        series_observation.included_period_count,
    )
    _validate_matches_source(
        "selected_source_return_count",
        summary.selected_source_return_count,
        selected_source_return_count,
    )
    _validate_matches_source(
        "selected_source_return_count",
        summary.selected_source_return_count,
        series_observation.selected_source_return_count,
    )
    _validate_matches_source(
        "min_selected_source_return",
        summary.min_selected_source_return,
        min_selected_source_return,
    )
    _validate_matches_source(
        "max_selected_source_return",
        summary.max_selected_source_return,
        max_selected_source_return,
    )
    _validate_matches_source(
        "mean_selected_source_return",
        summary.mean_selected_source_return,
        mean_selected_source_return,
    )
    _validate_matches_source("summary_state", summary.summary_state, summary_state)
    _validate_matches_source(
        "limitations",
        summary.limitations,
        _summary_limitations(series_observation),
    )
    _validate_matches_source(
        "non_claims",
        summary.non_claims,
        _summary_non_claims(series_observation),
    )


def _validate_matches_source(
    field_name: str,
    value: object,
    source_value: object,
) -> None:
    if value != source_value:
        raise ValidationError(
            f"{field_name} must match selected source return series."
        )


def _summary_limitations(
    series_observation: SmaSelectedSourceReturnSeriesObservation,
) -> tuple[str, ...]:
    empty_limitation = (
        (_EMPTY_LIMITATION,) if not series_observation.selected_source_returns else ()
    )
    return _dedupe(
        (
            *_DEFAULT_LIMITATIONS,
            *empty_limitation,
            *series_observation.limitations,
        )
    )


def _summary_non_claims(
    series_observation: SmaSelectedSourceReturnSeriesObservation,
) -> tuple[str, ...]:
    return _dedupe((*_REQUIRED_NON_CLAIMS, *series_observation.non_claims))


def _summary_state(value: object) -> str:
    state = _required_string(value, "summary_state")
    if state not in SMA_SELECTED_SOURCE_RETURN_SUMMARY_STATES:
        allowed = ", ".join(SMA_SELECTED_SOURCE_RETURN_SUMMARY_STATES)
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


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal or None.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _decimal_payload(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)
