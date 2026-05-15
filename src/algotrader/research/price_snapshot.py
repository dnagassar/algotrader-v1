"""Local deterministic historical price snapshot loading utilities."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from algotrader.errors import ValidationError

__all__ = [
    "HistoricalPriceBar",
    "HistoricalPriceSnapshot",
    "load_historical_price_snapshot_csv",
    "price_snapshot_fingerprint",
]

_REQUIRED_COLUMNS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)
_OPTIONAL_COLUMNS = ("symbol",)
_ALLOWED_COLUMNS = _REQUIRED_COLUMNS + _OPTIONAL_COLUMNS


@dataclass(frozen=True, slots=True)
class HistoricalPriceBar:
    """Validated daily historical price bar loaded from a local snapshot."""

    symbol: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _symbol_value(self.symbol, "symbol"))
        object.__setattr__(self, "date", _plain_date_value(self.date, "date"))
        object.__setattr__(self, "open", _positive_decimal_value(self.open, "open"))
        object.__setattr__(self, "high", _positive_decimal_value(self.high, "high"))
        object.__setattr__(self, "low", _positive_decimal_value(self.low, "low"))
        object.__setattr__(self, "close", _positive_decimal_value(self.close, "close"))
        object.__setattr__(
            self,
            "adjusted_close",
            _positive_decimal_value(self.adjusted_close, "adjusted_close"),
        )
        object.__setattr__(self, "volume", _volume_value(self.volume, "volume"))
        _validate_ohlc_relationships(self)


@dataclass(frozen=True, slots=True)
class HistoricalPriceSnapshot:
    """Immutable daily historical price bars for one symbol."""

    symbol: str
    bars: tuple[HistoricalPriceBar, ...]

    def __post_init__(self) -> None:
        symbol = _symbol_value(self.symbol, "symbol")
        bars = _bar_tuple(self.bars)
        _validate_snapshot_bars(symbol, bars)

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "bars", bars)


def load_historical_price_snapshot_csv(
    path: str | Path,
    symbol: str,
) -> HistoricalPriceSnapshot:
    """Load a local CSV file into a validated historical price snapshot."""

    csv_path = _local_csv_path(path)
    snapshot_symbol = _symbol_value(symbol, "symbol")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_csv_columns(reader.fieldnames)
        bars = tuple(
            _bar_from_row(row=row, row_number=row_number, symbol=snapshot_symbol)
            for row_number, row in enumerate(reader, start=2)
        )

    if not bars:
        raise ValidationError("CSV file must contain at least one data row.")

    return HistoricalPriceSnapshot(symbol=snapshot_symbol, bars=bars)


def price_snapshot_fingerprint(snapshot: HistoricalPriceSnapshot) -> str:
    """Return a deterministic sha256 fingerprint for snapshot content."""

    if not isinstance(snapshot, HistoricalPriceSnapshot):
        raise ValidationError("snapshot must be a HistoricalPriceSnapshot.")

    payload = {
        "symbol": snapshot.symbol,
        "bars": [
            {
                "symbol": bar.symbol,
                "date": bar.date.isoformat(),
                "open": _decimal_fingerprint_value(bar.open),
                "high": _decimal_fingerprint_value(bar.high),
                "low": _decimal_fingerprint_value(bar.low),
                "close": _decimal_fingerprint_value(bar.close),
                "adjusted_close": _decimal_fingerprint_value(bar.adjusted_close),
                "volume": bar.volume,
            }
            for bar in snapshot.bars
        ],
    }
    encoded_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded_payload).hexdigest()


def _symbol_value(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty symbol.")

    normalized = value.strip().upper()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty symbol.")

    return normalized


def _plain_date_value(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _positive_decimal_value(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite() or value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")

    return value


def _volume_value(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")

    return value


def _validate_ohlc_relationships(bar: HistoricalPriceBar) -> None:
    if bar.high < bar.open or bar.high < bar.close or bar.high < bar.low:
        raise ValidationError("high must be greater than or equal to open, close, and low.")
    if bar.low > bar.open or bar.low > bar.close or bar.low > bar.high:
        raise ValidationError("low must be less than or equal to open, close, and high.")


def _bar_tuple(
    bars: Iterable[HistoricalPriceBar],
) -> tuple[HistoricalPriceBar, ...]:
    try:
        bar_items = tuple(bars)
    except TypeError as exc:
        raise ValidationError("bars must be an iterable of HistoricalPriceBar.") from exc

    if not bar_items:
        raise ValidationError("bars must contain at least one HistoricalPriceBar.")

    for bar in bar_items:
        if not isinstance(bar, HistoricalPriceBar):
            raise ValidationError("bars must contain HistoricalPriceBar values.")

    return bar_items


def _validate_snapshot_bars(
    symbol: str,
    bars: tuple[HistoricalPriceBar, ...],
) -> None:
    seen_dates: set[date] = set()
    previous_date: date | None = None

    for bar in bars:
        if bar.symbol != symbol:
            raise ValidationError("all bars must match the snapshot symbol.")
        if bar.date in seen_dates:
            raise ValidationError("bars must not contain duplicate dates.")
        if previous_date is not None and bar.date <= previous_date:
            raise ValidationError("bars must be strictly increasing by date.")

        seen_dates.add(bar.date)
        previous_date = bar.date


def _local_csv_path(path: str | Path) -> Path:
    if not isinstance(path, (str, Path)):
        raise ValidationError("path must be a local CSV path.")
    if isinstance(path, str) and "://" in path:
        raise ValidationError("path must be a local CSV path.")

    csv_path = Path(path)
    if csv_path.suffix.lower() != ".csv":
        raise ValidationError("path must reference a CSV file.")
    if not csv_path.is_file():
        raise ValidationError("path must reference an existing local CSV file.")

    return csv_path


def _validate_csv_columns(fieldnames: list[str] | None) -> bool:
    if fieldnames is None:
        raise ValidationError("CSV file must include a header row.")

    columns = tuple(fieldnames)
    if len(set(columns)) != len(columns):
        raise ValidationError("CSV file must not contain duplicate columns.")

    missing_columns = tuple(column for column in _REQUIRED_COLUMNS if column not in columns)
    if missing_columns:
        raise ValidationError(
            f"CSV file is missing required columns: {', '.join(missing_columns)}."
        )

    extra_columns = tuple(column for column in columns if column not in _ALLOWED_COLUMNS)
    if extra_columns:
        raise ValidationError(f"CSV file has unsupported columns: {', '.join(extra_columns)}.")

    return "symbol" in columns


def _bar_from_row(
    row: dict[str, str],
    row_number: int,
    symbol: str,
) -> HistoricalPriceBar:
    if None in row:
        raise ValidationError(f"CSV row {row_number} has too many values.")

    if "symbol" in row:
        row_symbol = _symbol_value(row["symbol"], f"row {row_number} symbol")
        if row_symbol != symbol:
            raise ValidationError(f"CSV row {row_number} symbol does not match snapshot symbol.")

    return HistoricalPriceBar(
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


def _parse_date(value: str, field_name: str) -> date:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an ISO date.")

    text = value.strip()
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise ValidationError(f"{field_name} must be an ISO date.")

    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO date.") from exc

    if parsed.isoformat() != text:
        raise ValidationError(f"{field_name} must be an ISO date.")

    return parsed


def _parse_decimal(value: str, field_name: str) -> Decimal:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a Decimal string.")

    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must be a Decimal string.")

    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a Decimal string.") from exc

    return _positive_decimal_value(parsed, field_name)


def _parse_volume(value: str, field_name: str) -> int:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an integer string.")

    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must be an integer string.")

    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an integer string.") from exc

    return _volume_value(parsed, field_name)


def _decimal_fingerprint_value(value: Decimal) -> str:
    return format(value.normalize(), "f")
