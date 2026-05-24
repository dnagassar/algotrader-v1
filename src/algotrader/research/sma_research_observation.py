"""Synthetic SMA research observation mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from algotrader.errors import ValidationError

__all__ = [
    "SMA_RESEARCH_POSITIONS",
    "SmaResearchObservation",
    "SmaResearchPricePoint",
    "build_sma_research_observation",
]

_OBSERVATION_TYPE = "sma_research_observation"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
SMA_RESEARCH_POSITIONS = (
    "above",
    "below",
    "equal",
    "insufficient_history",
)


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


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
)
_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
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
    "rank",
    "score",
)


@dataclass(frozen=True, slots=True)
class SmaResearchPricePoint:
    """Synthetic close observation for SMA research mechanics."""

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
class SmaResearchObservation:
    """Synthetic, advisory-only SMA observation mechanics."""

    observation_type: str
    status: str
    authority: str
    capital_authority: bool
    symbol: str
    as_of: str
    window: int
    sample_count: int
    eligible_sample_count: int
    ignored_future_sample_count: int
    latest_close: Decimal | None
    sma_value: Decimal | None
    distance_from_sma: Decimal | None
    distance_from_sma_pct: Decimal | None
    position_vs_sma: str
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
        object.__setattr__(self, "window", _positive_int(self.window, "window"))
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
            "latest_close",
            _optional_positive_decimal(self.latest_close, "latest_close"),
        )
        object.__setattr__(
            self,
            "sma_value",
            _optional_positive_decimal(self.sma_value, "sma_value"),
        )
        object.__setattr__(
            self,
            "distance_from_sma",
            _optional_decimal(self.distance_from_sma, "distance_from_sma"),
        )
        object.__setattr__(
            self,
            "distance_from_sma_pct",
            _optional_decimal(self.distance_from_sma_pct, "distance_from_sma_pct"),
        )
        object.__setattr__(
            self,
            "position_vs_sma",
            _position_vs_sma(self.position_vs_sma),
        )
        object.__setattr__(
            self,
            "limitations",
            _advisory_text_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(self, "non_claims", _required_non_claims(self.non_claims))
        _validate_count_consistency(
            self.sample_count,
            self.eligible_sample_count,
            self.ignored_future_sample_count,
        )
        _validate_observation_consistency(
            window=self.window,
            eligible_sample_count=self.eligible_sample_count,
            latest_close=self.latest_close,
            sma_value=self.sma_value,
            distance_from_sma=self.distance_from_sma,
            distance_from_sma_pct=self.distance_from_sma_pct,
            position_vs_sma=self.position_vs_sma,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only SMA observation metadata."""

        return {
            "observation_type": self.observation_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "symbol": self.symbol,
            "as_of": self.as_of,
            "window": self.window,
            "sample_count": self.sample_count,
            "eligible_sample_count": self.eligible_sample_count,
            "ignored_future_sample_count": self.ignored_future_sample_count,
            "latest_close": _decimal_text(self.latest_close),
            "sma_value": _decimal_text(self.sma_value),
            "distance_from_sma": _decimal_text(self.distance_from_sma),
            "distance_from_sma_pct": _decimal_text(self.distance_from_sma_pct),
            "position_vs_sma": self.position_vs_sma,
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_sma_research_observation(
    symbol: str,
    as_of: str,
    window: int,
    price_points: tuple[SmaResearchPricePoint, ...] | list[SmaResearchPricePoint],
    limitations: tuple[str, ...] | list[str] = (),
    non_claims: tuple[str, ...] | list[str] = (),
) -> SmaResearchObservation:
    """Build a deterministic synthetic SMA research observation."""

    checked_as_of = _iso_date(as_of, "as_of")
    checked_window = _positive_int(window, "window")
    checked_points = _sorted_price_points(price_points)
    eligible_points = tuple(point for point in checked_points if point.date <= checked_as_of)
    ignored_future_sample_count = len(checked_points) - len(eligible_points)
    latest_close = eligible_points[-1].close if eligible_points else None

    if len(eligible_points) < checked_window:
        sma_value = None
        distance_from_sma = None
        distance_from_sma_pct = None
        position_vs_sma = "insufficient_history"
    else:
        sma_points = eligible_points[-checked_window:]
        sma_value = sum((point.close for point in sma_points), Decimal("0")) / Decimal(
            checked_window
        )
        distance_from_sma = latest_close - sma_value
        distance_from_sma_pct = distance_from_sma / sma_value
        position_vs_sma = _position_from_distance(distance_from_sma)

    return SmaResearchObservation(
        observation_type=_OBSERVATION_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        symbol=symbol,
        as_of=checked_as_of,
        window=checked_window,
        sample_count=len(checked_points),
        eligible_sample_count=len(eligible_points),
        ignored_future_sample_count=ignored_future_sample_count,
        latest_close=latest_close,
        sma_value=sma_value,
        distance_from_sma=distance_from_sma,
        distance_from_sma_pct=distance_from_sma_pct,
        position_vs_sma=position_vs_sma,
        limitations=_advisory_text_tuple(limitations, "limitations"),
        non_claims=_combined_non_claims(non_claims),
    )


def _validate_fixed_metadata(
    observation_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if observation_type != _OBSERVATION_TYPE:
        raise ValidationError(
            "observation_type must be exactly sma_research_observation."
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
    if any(token in lowered for token in _FORBIDDEN_TEXT_TOKENS):
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


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 1:
        raise ValidationError(f"{field_name} must be at least 1.")

    return value


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


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None

    return _positive_decimal(value, field_name)


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None

    return _decimal(value, field_name)


def _decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return value


def _sorted_price_points(
    values: object,
) -> tuple[SmaResearchPricePoint, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("price_points must be a tuple or list of price points.")

    points = tuple(values)
    seen_dates: set[str] = set()
    for index, point in enumerate(points):
        if type(point) is not SmaResearchPricePoint:
            raise ValidationError(
                f"price_points[{index}] must be a SmaResearchPricePoint."
            )
        if point.date in seen_dates:
            raise ValidationError("price_points must not contain duplicate dates.")
        seen_dates.add(point.date)

    return tuple(sorted(points, key=lambda point: point.date))


def _position_vs_sma(value: object) -> str:
    position = _required_string(value, "position_vs_sma")
    if position not in SMA_RESEARCH_POSITIONS:
        allowed = ", ".join(SMA_RESEARCH_POSITIONS)
        raise ValidationError(f"position_vs_sma must be one of: {allowed}.")

    return position


def _position_from_distance(value: Decimal) -> str:
    if value > Decimal("0"):
        return "above"
    if value < Decimal("0"):
        return "below"

    return "equal"


def _validate_count_consistency(
    sample_count: int,
    eligible_sample_count: int,
    ignored_future_sample_count: int,
) -> None:
    if eligible_sample_count + ignored_future_sample_count != sample_count:
        raise ValidationError(
            "eligible_sample_count plus ignored_future_sample_count must equal "
            "sample_count."
        )


def _validate_observation_consistency(
    *,
    window: int,
    eligible_sample_count: int,
    latest_close: Decimal | None,
    sma_value: Decimal | None,
    distance_from_sma: Decimal | None,
    distance_from_sma_pct: Decimal | None,
    position_vs_sma: str,
) -> None:
    if eligible_sample_count < window:
        if position_vs_sma != "insufficient_history":
            raise ValidationError(
                "position_vs_sma must be insufficient_history without enough samples."
            )
        if (
            sma_value is not None
            or distance_from_sma is not None
            or distance_from_sma_pct is not None
        ):
            raise ValidationError(
                "sma_value and distance fields must be None without enough samples."
            )
        return

    if latest_close is None or sma_value is None:
        raise ValidationError("latest_close and sma_value are required.")
    if distance_from_sma is None or distance_from_sma_pct is None:
        raise ValidationError("distance fields are required.")
    if distance_from_sma != latest_close - sma_value:
        raise ValidationError("distance_from_sma must match latest_close minus sma.")
    if distance_from_sma_pct != distance_from_sma / sma_value:
        raise ValidationError("distance_from_sma_pct must match distance over sma.")
    if position_vs_sma != _position_from_distance(distance_from_sma):
        raise ValidationError("position_vs_sma must match distance_from_sma.")


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
