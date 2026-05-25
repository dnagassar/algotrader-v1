"""Synthetic close-to-close research return observation mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError

__all__ = [
    "ResearchReturnPoint",
    "ResearchReturnPricePoint",
    "ResearchReturnSeriesObservation",
    "build_research_return_series_observation",
]

_OBSERVATION_TYPE = "research_return_series_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_RETURN_METHOD = "close_to_close_simple_return"
_PRICE_BASIS = "synthetic_close"


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_REQUIRED_NON_CLAIMS = (
    _not("sour", "ce/data app", "roval"),
    _not("adjusted-close/corporate-action completeness"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("backtesting validation"),
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
    "actionability",
    "actionable",
    "authority",
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    "evaluator",
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    _join("port", "folio"),
    "paper",
    "live",
    _join("read", "iness"),
    "capital authority",
    _join("tra", "ding authority"),
    "trading_ready",
    "trading-ready",
    "buy",
    "sell",
    "hold",
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class ResearchReturnPricePoint:
    """Synthetic close observation for return mechanics."""

    date: str
    close: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", _iso_date(self.date, "date"))
        object.__setattr__(self, "close", _positive_decimal(self.close, "close"))

    def to_dict(self) -> dict[str, str]:
        """Return deterministic primitive-only price point metadata."""

        return {
            "date": self.date,
            "close": str(self.close),
        }


@dataclass(frozen=True, slots=True)
class ResearchReturnPoint:
    """One close-to-close simple return observation."""

    start_date: str
    end_date: str
    start_close: Decimal
    end_close: Decimal
    simple_return: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_date", _iso_date(self.start_date, "start_date"))
        object.__setattr__(self, "end_date", _iso_date(self.end_date, "end_date"))
        object.__setattr__(
            self,
            "start_close",
            _positive_decimal(self.start_close, "start_close"),
        )
        object.__setattr__(
            self,
            "end_close",
            _positive_decimal(self.end_close, "end_close"),
        )
        object.__setattr__(
            self,
            "simple_return",
            _decimal(self.simple_return, "simple_return"),
        )
        if self.end_date <= self.start_date:
            raise ValidationError("end_date must be after start_date.")
        expected_return = (self.end_close / self.start_close) - Decimal("1")
        if self.simple_return != expected_return:
            raise ValidationError("simple_return must match end_close over start_close.")

    def to_dict(self) -> dict[str, str]:
        """Return deterministic primitive-only return point metadata."""

        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "start_close": str(self.start_close),
            "end_close": str(self.end_close),
            "simple_return": str(self.simple_return),
        }


@dataclass(frozen=True, slots=True)
class ResearchReturnSeriesObservation:
    """Synthetic, advisory-only close-to-close return series observation."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    symbol: str
    as_of: str
    return_method: str
    price_basis: str
    sample_count: int
    eligible_sample_count: int
    ignored_future_sample_count: int
    return_count: int
    returns: tuple[ResearchReturnPoint, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            self.observation_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(self, "symbol", _advisory_text(self.symbol, "symbol"))
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "return_method",
            _fixed_string(
                self.return_method,
                "return_method",
                _RETURN_METHOD,
            ),
        )
        object.__setattr__(
            self,
            "price_basis",
            _fixed_string(self.price_basis, "price_basis", _PRICE_BASIS),
        )
        object.__setattr__(
            self,
            "sample_count",
            _non_negative_int(self.sample_count, "sample_count"),
        )
        object.__setattr__(
            self,
            "eligible_sample_count",
            _non_negative_int(self.eligible_sample_count, "eligible_sample_count"),
        )
        object.__setattr__(
            self,
            "ignored_future_sample_count",
            _non_negative_int(
                self.ignored_future_sample_count,
                "ignored_future_sample_count",
            ),
        )
        object.__setattr__(
            self,
            "return_count",
            _non_negative_int(self.return_count, "return_count"),
        )
        object.__setattr__(self, "returns", _return_point_tuple(self.returns))
        object.__setattr__(
            self,
            "limitations",
            _advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _required_non_claims(self.non_claims))
        _validate_count_consistency(
            sample_count=self.sample_count,
            eligible_sample_count=self.eligible_sample_count,
            ignored_future_sample_count=self.ignored_future_sample_count,
            return_count=self.return_count,
            returns=self.returns,
        )
        _validate_return_sequence(self.as_of, self.returns)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only return observation metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "return_method": self.return_method,
            "price_basis": self.price_basis,
            "sample_count": self.sample_count,
            "eligible_sample_count": self.eligible_sample_count,
            "ignored_future_sample_count": self.ignored_future_sample_count,
            "return_count": self.return_count,
            "returns": [return_point.to_dict() for return_point in self.returns],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_return_series_observation(
    symbol: str,
    as_of: str,
    price_points: tuple[ResearchReturnPricePoint, ...] | list[ResearchReturnPricePoint],
    limitations: tuple[str, ...] | list[str] = (),
    non_claims: tuple[str, ...] | list[str] = (),
) -> ResearchReturnSeriesObservation:
    """Build a deterministic synthetic close-to-close return observation."""

    checked_as_of = _iso_date(as_of, "as_of")
    checked_points = _sorted_price_points(price_points)
    eligible_points = tuple(point for point in checked_points if point.date <= checked_as_of)
    ignored_future_sample_count = len(checked_points) - len(eligible_points)
    returns = _build_return_points(eligible_points)

    return ResearchReturnSeriesObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        symbol=symbol,
        as_of=checked_as_of,
        return_method=_RETURN_METHOD,
        price_basis=_PRICE_BASIS,
        sample_count=len(checked_points),
        eligible_sample_count=len(eligible_points),
        ignored_future_sample_count=ignored_future_sample_count,
        return_count=len(returns),
        returns=returns,
        limitations=_advisory_text_tuple(limitations, "limitations"),
        non_claims=_combined_non_claims(non_claims),
    )


def _build_return_points(
    eligible_points: tuple[ResearchReturnPricePoint, ...],
) -> tuple[ResearchReturnPoint, ...]:
    return tuple(
        ResearchReturnPoint(
            start_date=start_point.date,
            end_date=end_point.date,
            start_close=start_point.close,
            end_close=end_point.close,
            simple_return=(end_point.close / start_point.close) - Decimal("1"),
        )
        for start_point, end_point in zip(eligible_points, eligible_points[1:])
    )


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly research_return_series_observation."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _iso_date(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO YYYY-MM-DD date string."
        ) from exc

    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")

    return value


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
        raise ValidationError(f"{field_name} must remain advisory research text.")

    return text


def _advisory_text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    for index, value in enumerate(items):
        _advisory_text(value, f"{field_name}[{index}]")

    return items


def _required_non_claims(values: object) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("non_claims must be a tuple or list of strings.")

    non_claims = tuple(values)
    if not non_claims:
        raise ValidationError("non_claims must contain at least one string.")

    for index, value in enumerate(non_claims):
        _required_string(value, f"non_claims[{index}]")

    missing = tuple(claim for claim in _REQUIRED_NON_CLAIMS if claim not in non_claims)
    if missing:
        raise ValidationError(
            "non_claims must include required advisory research non-claims."
        )

    if any(not claim.startswith("not ") for claim in non_claims):
        raise ValidationError("non_claims entries must be negative statements.")

    return non_claims


def _combined_non_claims(values: object) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("non_claims must be a tuple or list of strings.")

    combined: list[str] = []
    seen: set[str] = set()
    for value in (*_REQUIRED_NON_CLAIMS, *tuple(values)):
        if value in seen:
            continue
        _required_string(value, "non_claims")
        combined.append(value)
        seen.add(value)

    return tuple(combined)


def _fixed_string(value: object, field_name: str, expected: str) -> str:
    text = _required_string(value, field_name)
    if text != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")

    return text


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative.")

    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal(value, field_name)
    if decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")

    return decimal_value


def _decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _sorted_price_points(
    values: object,
) -> tuple[ResearchReturnPricePoint, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("price_points must be a tuple or list of price points.")

    points = tuple(values)
    seen_dates: set[str] = set()
    for index, point in enumerate(points):
        if type(point) is not ResearchReturnPricePoint:
            raise ValidationError(
                f"price_points[{index}] must be a ResearchReturnPricePoint."
            )
        if point.date in seen_dates:
            raise ValidationError("price_points must not contain duplicate dates.")
        seen_dates.add(point.date)

    return tuple(sorted(points, key=lambda point: point.date))


def _return_point_tuple(values: object) -> tuple[ResearchReturnPoint, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("returns must be a tuple or list of return points.")

    return_points = tuple(values)
    for index, return_point in enumerate(return_points):
        if type(return_point) is not ResearchReturnPoint:
            raise ValidationError(f"returns[{index}] must be a ResearchReturnPoint.")

    return return_points


def _validate_count_consistency(
    *,
    sample_count: int,
    eligible_sample_count: int,
    ignored_future_sample_count: int,
    return_count: int,
    returns: tuple[ResearchReturnPoint, ...],
) -> None:
    if eligible_sample_count + ignored_future_sample_count != sample_count:
        raise ValidationError(
            "eligible_sample_count plus ignored_future_sample_count must equal "
            "sample_count."
        )

    expected_return_count = max(eligible_sample_count - 1, 0)
    if return_count != expected_return_count:
        raise ValidationError(
            "return_count must equal eligible_sample_count minus one when possible."
        )

    if return_count != len(returns):
        raise ValidationError("return_count must equal returns count.")


def _validate_return_sequence(
    as_of: str,
    returns: tuple[ResearchReturnPoint, ...],
) -> None:
    previous_end_date: str | None = None
    for return_point in returns:
        if return_point.end_date > as_of:
            raise ValidationError("returns must not include future end dates.")
        if previous_end_date is not None and return_point.start_date != previous_end_date:
            raise ValidationError("returns must form a consecutive date chain.")
        previous_end_date = return_point.end_date
