"""Deterministic local NYSE session identity used by the paper supervisor.

This is deliberately a local calendar abstraction, not a broker clock or a
network calendar.  Its only role is to decide whether a completed US equity
session is eligible for an offline supervisor cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from algotrader.errors import ValidationError

__all__ = [
    "ExchangeSession",
    "NyseExchangeSessionCalendar",
]

_NEW_YORK = ZoneInfo("America/New_York")
_REGULAR_OPEN = time(9, 30)
_REGULAR_CLOSE = time(16, 0)
_EARLY_CLOSE = time(13, 0)


@dataclass(frozen=True, slots=True)
class ExchangeSession:
    """One named NYSE session with its deterministic close boundary."""

    session_date: date
    opens_at: datetime
    closes_at: datetime
    early_close: bool

    @property
    def identity(self) -> str:
        return f"NYSE:{self.session_date.isoformat()}"

    def completed_at(self, observed_at: datetime) -> bool:
        return _utc(observed_at, "observed_at") >= self.closes_at


class NyseExchangeSessionCalendar:
    """Repository-owned deterministic NYSE calendar for the SPY daily lane."""

    def session_for_date(self, session_date: date) -> ExchangeSession | None:
        if not isinstance(session_date, date):
            raise ValidationError("session_date must be a date.")
        if session_date.weekday() >= 5 or session_date in _full_day_holidays(
            session_date.year
        ):
            return None
        early_close = session_date in _early_close_dates(session_date.year)
        close = _EARLY_CLOSE if early_close else _REGULAR_CLOSE
        return ExchangeSession(
            session_date=session_date,
            opens_at=datetime.combine(session_date, _REGULAR_OPEN, _NEW_YORK).astimezone(
                UTC
            ),
            closes_at=datetime.combine(session_date, close, _NEW_YORK).astimezone(UTC),
            early_close=early_close,
        )

    def latest_completed_session(self, observed_at: datetime) -> ExchangeSession | None:
        current = _utc(observed_at, "observed_at").astimezone(_NEW_YORK).date()
        session = self.session_for_date(current)
        if session is not None and session.completed_at(observed_at):
            return session
        return None

    def latest_completed_session_on_or_before(
        self,
        observed_at: datetime,
        *,
        max_lookback_days: int = 10,
    ) -> ExchangeSession | None:
        """Return the latest completed session across weekends and holidays."""
        observed_utc = _utc(observed_at, "observed_at")
        if (
            isinstance(max_lookback_days, bool)
            or not isinstance(max_lookback_days, int)
            or not 1 <= max_lookback_days <= 31
        ):
            raise ValidationError("max_lookback_days must be an integer from 1 to 31.")
        current = observed_utc.astimezone(_NEW_YORK).date()
        for days_back in range(max_lookback_days + 1):
            session = self.session_for_date(current - timedelta(days=days_back))
            if session is not None and session.completed_at(observed_utc):
                return session
        return None


def _full_day_holidays(year: int) -> frozenset[date]:
    new_years = _observed(date(year, 1, 1))
    mlk = _nth_weekday(year, 1, weekday=0, occurrence=3)
    presidents = _nth_weekday(year, 2, weekday=0, occurrence=3)
    good_friday = _easter_sunday(year) - timedelta(days=2)
    memorial = _last_weekday(year, 5, weekday=0)
    juneteenth = _observed(date(year, 6, 19))
    independence = _observed(date(year, 7, 4))
    labor = _nth_weekday(year, 9, weekday=0, occurrence=1)
    thanksgiving = _nth_weekday(year, 11, weekday=3, occurrence=4)
    christmas = _observed(date(year, 12, 25))
    return frozenset(
        {
            new_years,
            mlk,
            presidents,
            good_friday,
            memorial,
            juneteenth,
            independence,
            labor,
            thanksgiving,
            christmas,
        }
    )


def _early_close_dates(year: int) -> frozenset[date]:
    thanksgiving = _nth_weekday(year, 11, weekday=3, occurrence=4)
    candidates = {
        thanksgiving + timedelta(days=1),
        date(year, 7, 3),
        date(year, 12, 24),
    }
    full_holidays = _full_day_holidays(year)
    return frozenset(
        candidate
        for candidate in candidates
        if candidate.weekday() < 5 and candidate not in full_holidays
    )


def _observed(value: date) -> date:
    if value.weekday() == 5:
        return value - timedelta(days=1)
    if value.weekday() == 6:
        return value + timedelta(days=1)
    return value


def _nth_weekday(year: int, month: int, *, weekday: int, occurrence: int) -> date:
    candidate = date(year, month, 1)
    offset = (weekday - candidate.weekday()) % 7
    return candidate + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, *, weekday: int) -> date:
    if month == 12:
        candidate = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        candidate = date(year, month + 1, 1) - timedelta(days=1)
    return candidate - timedelta(days=(candidate.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    """Gregorian computus, kept local so default tests never need a calendar SDK."""

    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValidationError(f"{field_name} must be a timezone-aware datetime.")
    return value.astimezone(UTC)
