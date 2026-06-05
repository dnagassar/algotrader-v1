"""Strict local CSV loading for deterministic daily bars.

The loader in this module is deliberately plain local file I/O. It does not
download data, inspect credentials, import broker adapters, or normalize from
remote provider formats.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from algotrader.core.types import Bar
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "LOCAL_DAILY_BARS_CSV_COLUMNS",
    "LocalDailyBar",
    "LocalDailyBarsCsvResult",
    "load_local_daily_bars_csv",
]


LOCAL_DAILY_BARS_CSV_COLUMNS = (
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)


@dataclass(frozen=True, slots=True)
class LocalDailyBar:
    """One validated local daily bar from the strict CSV schema."""

    symbol: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(self, "date", _plain_date(self.date, "date"))
        object.__setattr__(self, "open", _positive_decimal(self.open, "open"))
        object.__setattr__(self, "high", _positive_decimal(self.high, "high"))
        object.__setattr__(self, "low", _positive_decimal(self.low, "low"))
        object.__setattr__(self, "close", _positive_decimal(self.close, "close"))
        object.__setattr__(
            self,
            "adjusted_close",
            _positive_decimal(self.adjusted_close, "adjusted_close"),
        )
        object.__setattr__(self, "volume", _non_negative_int(self.volume, "volume"))
        _validate_ohlc(self)

    def to_core_bar(self) -> Bar:
        """Return the existing core Bar shape at UTC midnight for this date."""

        return Bar(
            symbol=self.symbol,
            timestamp=datetime.combine(self.date, time.min, tzinfo=UTC),
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=Decimal(self.volume),
        )


@dataclass(frozen=True, slots=True)
class LocalDailyBarsCsvResult:
    """Validated local CSV bars and deterministic readiness metadata."""

    path: Path
    symbol: str
    as_of_date: date | None
    bars: tuple[LocalDailyBar, ...]
    usable_bars: tuple[LocalDailyBar, ...]
    total_row_count: int
    matching_symbol_row_count: int
    ignored_wrong_symbol_row_count: int
    ignored_future_bar_count: int
    input_sorted_by_date: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path_value(self.path, "path"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        if self.as_of_date is not None:
            object.__setattr__(
                self,
                "as_of_date",
                _plain_date(self.as_of_date, "as_of_date"),
            )
        object.__setattr__(self, "bars", _bar_tuple(self.bars, "bars"))
        object.__setattr__(
            self,
            "usable_bars",
            _bar_tuple(self.usable_bars, "usable_bars"),
        )
        for field_name in (
            "total_row_count",
            "matching_symbol_row_count",
            "ignored_wrong_symbol_row_count",
            "ignored_future_bar_count",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_negative_int(getattr(self, field_name), field_name),
            )
        if type(self.input_sorted_by_date) is not bool:
            raise ValidationError("input_sorted_by_date must be a bool.")
        _validate_result(self)

    @property
    def observed_usable_bars(self) -> int:
        return len(self.usable_bars)

    def to_core_bars(self) -> tuple[Bar, ...]:
        """Return usable bars in the existing immutable core Bar shape."""

        return tuple(bar.to_core_bar() for bar in self.usable_bars)

    def source_metadata(self) -> dict[str, object]:
        """Return deterministic JSON-safe local CSV source metadata."""

        return {
            "type": "local_daily_bars_csv",
            "path": str(self.path),
            "schema": list(LOCAL_DAILY_BARS_CSV_COLUMNS),
            "symbol": self.symbol,
            "as_of_date": None if self.as_of_date is None else self.as_of_date.isoformat(),
            "total_row_count": self.total_row_count,
            "matching_symbol_row_count": self.matching_symbol_row_count,
            "usable_bar_count": self.observed_usable_bars,
            "ignored_wrong_symbol_row_count": self.ignored_wrong_symbol_row_count,
            "ignored_future_bar_count": self.ignored_future_bar_count,
            "input_sorted_by_date": self.input_sorted_by_date,
            "sorted_output": True,
        }


def load_local_daily_bars_csv(
    path: str | Path,
    *,
    symbol: str,
    as_of: date | datetime | str | None = None,
) -> LocalDailyBarsCsvResult:
    """Load requested-symbol bars from a strict local daily-bars CSV."""

    csv_path = _local_csv_path(path)
    requested_symbol = symbol_value(symbol)
    as_of_date = _as_of_date(as_of)
    bars: list[LocalDailyBar] = []
    total_row_count = 0
    ignored_wrong_symbol_row_count = 0
    previous_input_date: date | None = None
    input_sorted_by_date = True
    seen_dates: set[date] = set()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        _validate_csv_columns(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            total_row_count += 1
            if None in row:
                raise ValidationError(f"CSV row {row_number} has too many values.")
            row_symbol = symbol_value(_required_text(row["symbol"], f"row {row_number} symbol"))
            if row_symbol != requested_symbol:
                ignored_wrong_symbol_row_count += 1
                continue
            bar = _bar_from_row(row, row_number=row_number, symbol=row_symbol)
            if bar.date in seen_dates:
                raise ValidationError(
                    f"CSV row {row_number} duplicates date {bar.date.isoformat()} "
                    f"for symbol {requested_symbol}."
                )
            if previous_input_date is not None and bar.date < previous_input_date:
                input_sorted_by_date = False
            previous_input_date = bar.date
            seen_dates.add(bar.date)
            bars.append(bar)

    sorted_bars = tuple(sorted(bars, key=lambda item: item.date))
    usable_bars = tuple(
        bar for bar in sorted_bars if as_of_date is None or bar.date <= as_of_date
    )

    return LocalDailyBarsCsvResult(
        path=csv_path,
        symbol=requested_symbol,
        as_of_date=as_of_date,
        bars=sorted_bars,
        usable_bars=usable_bars,
        total_row_count=total_row_count,
        matching_symbol_row_count=len(sorted_bars),
        ignored_wrong_symbol_row_count=ignored_wrong_symbol_row_count,
        ignored_future_bar_count=len(sorted_bars) - len(usable_bars),
        input_sorted_by_date=input_sorted_by_date,
    )


def _bar_from_row(
    row: dict[str, str],
    *,
    row_number: int,
    symbol: str,
) -> LocalDailyBar:
    return LocalDailyBar(
        symbol=symbol,
        date=_parse_date(row["date"], f"row {row_number} date"),
        open=_parse_decimal(row["open"], f"row {row_number} open"),
        high=_parse_decimal(row["high"], f"row {row_number} high"),
        low=_parse_decimal(row["low"], f"row {row_number} low"),
        close=_parse_decimal(row["close"], f"row {row_number} close"),
        adjusted_close=_parse_decimal(
            row["adjusted_close"],
            f"row {row_number} adjusted_close",
        ),
        volume=_parse_volume(row["volume"], f"row {row_number} volume"),
    )


def _local_csv_path(path: str | Path) -> Path:
    csv_path = _path_value(path, "daily_bars_csv")
    if isinstance(path, str) and "://" in path:
        raise ValidationError("daily_bars_csv must be a local CSV path.")
    if csv_path.suffix.lower() != ".csv":
        raise ValidationError("daily_bars_csv must reference a CSV file.")
    if not csv_path.is_file():
        raise ValidationError("daily_bars_csv must reference an existing local CSV file.")
    return csv_path


def _path_value(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _validate_csv_columns(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValidationError("daily_bars_csv must include a header row.")

    columns = tuple(fieldnames)
    if len(set(columns)) != len(columns):
        raise ValidationError("daily_bars_csv must not contain duplicate columns.")

    missing_columns = tuple(
        column for column in LOCAL_DAILY_BARS_CSV_COLUMNS if column not in columns
    )
    if missing_columns:
        raise ValidationError(
            "daily_bars_csv is missing required columns: "
            f"{', '.join(missing_columns)}."
        )

    extra_columns = tuple(
        column for column in columns if column not in LOCAL_DAILY_BARS_CSV_COLUMNS
    )
    if extra_columns:
        raise ValidationError(
            f"daily_bars_csv has unsupported columns: {', '.join(extra_columns)}."
        )


def _as_of_date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("as_of must be timezone-aware.")
        return value.date()
    if type(value) is date:
        return value
    if type(value) is str:
        text = _required_text(value, "as_of")
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return _parse_date(text, "as_of")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("as_of must be an ISO date or timestamp.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError("as_of must be timezone-aware.")
        return parsed.date()
    raise ValidationError("as_of must be an ISO date or timezone-aware timestamp.")


def _parse_date(value: str, field_name: str) -> date:
    text = _required_text(value, field_name)
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date.")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date.") from exc
    if parsed.isoformat() != text:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date.")
    return parsed


def _parse_decimal(value: str, field_name: str) -> Decimal:
    text = _required_text(value, field_name)
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a Decimal string.") from exc
    return _positive_decimal(parsed, field_name)


def _parse_volume(value: str, field_name: str) -> int:
    text = _required_text(value, field_name)
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an integer string.") from exc
    if str(parsed) != text:
        raise ValidationError(f"{field_name} must be an integer string.")
    return _non_negative_int(parsed, field_name)


def _required_text(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")
    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite() or value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return value


def _bar_tuple(
    bars: Iterable[LocalDailyBar],
    field_name: str,
) -> tuple[LocalDailyBar, ...]:
    try:
        items = tuple(bars)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be iterable.") from exc
    for index, bar in enumerate(items):
        if type(bar) is not LocalDailyBar:
            raise ValidationError(f"{field_name}[{index}] must be a LocalDailyBar.")
    return items


def _validate_ohlc(bar: LocalDailyBar) -> None:
    if bar.high < bar.open or bar.high < bar.close or bar.high < bar.low:
        raise ValidationError("high must be greater than or equal to open, close, and low.")
    if bar.low > bar.open or bar.low > bar.close or bar.low > bar.high:
        raise ValidationError("low must be less than or equal to open, close, and high.")


def _validate_result(result: LocalDailyBarsCsvResult) -> None:
    if result.matching_symbol_row_count != len(result.bars):
        raise ValidationError("matching_symbol_row_count must equal bars count.")
    if result.observed_usable_bars != len(result.usable_bars):
        raise ValidationError("observed_usable_bars must equal usable bars count.")
    if result.ignored_future_bar_count != len(result.bars) - len(result.usable_bars):
        raise ValidationError("ignored_future_bar_count is inconsistent.")
    if (
        result.ignored_wrong_symbol_row_count + result.matching_symbol_row_count
        != result.total_row_count
    ):
        raise ValidationError("symbol row counts must equal total_row_count.")
    for previous, current in zip(result.bars, result.bars[1:]):
        if current.date <= previous.date:
            raise ValidationError("bars must be strictly increasing after sorting.")
    usable_dates = {bar.date for bar in result.usable_bars}
    all_dates = {bar.date for bar in result.bars}
    if not usable_dates.issubset(all_dates):
        raise ValidationError("usable_bars must be a subset of bars.")
