"""Local-only SPY close-price parity check against a manual reference CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


_CLOSE_COLUMNS = ("close", "price_close", "price-close")
_BPS = Decimal("10000")
_RETURN_PLACES = Decimal("0.0000000001")
_BPS_PLACES = Decimal("0.0001")
_DISCLAIMER = (
    "Advisory parity check only; price-return basis only; not validation; "
    "not trading advice."
)


class PriceParityError(ValueError):
    """Raised when the local parity inputs cannot be compared safely."""


@dataclass(frozen=True, slots=True)
class DailyClose:
    date: date
    close: Decimal


@dataclass(frozen=True, slots=True)
class CalendarYearPriceReturn:
    year: int
    price_return: Decimal


@dataclass(frozen=True, slots=True)
class PriceParityRow:
    year: int
    local_price_return: Decimal
    reference_price_return: Decimal
    difference_bps: Decimal


def run_spy_price_parity(
    local_csv_path: str | Path,
    reference_csv_path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> str:
    """Compare explicit local and reference CSVs and return a markdown report."""
    checked_local_path = _input_csv_path(local_csv_path, "local snapshot CSV")
    checked_reference_path = _input_csv_path(reference_csv_path, "reference CSV")
    checked_output_path = _output_path_value(output_path)
    local_closes = load_daily_close_csv(
        checked_local_path,
        label="local snapshot CSV",
    )
    reference_closes = load_daily_close_csv(
        checked_reference_path,
        label="reference CSV",
    )
    rows = compare_calendar_year_price_returns(local_closes, reference_closes)
    report = render_parity_report(
        local_csv_path=checked_local_path,
        reference_csv_path=checked_reference_path,
        rows=rows,
    )

    if checked_output_path is not None:
        try:
            checked_output_path.write_text(report, encoding="utf-8")
        except OSError as exc:
            raise PriceParityError(f"output markdown could not be written: {exc}") from exc

    return report


def load_daily_close_csv(
    path: str | Path,
    *,
    label: str = "CSV file",
) -> tuple[DailyClose, ...]:
    """Load one explicit local CSV path into validated daily close rows."""
    checked_path = _input_csv_path(path, label)

    try:
        with checked_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            date_column, close_column = _date_and_close_columns(
                reader.fieldnames,
                label,
            )
            rows = tuple(
                _daily_close_from_row(
                    row=row,
                    row_number=row_number,
                    date_column=date_column,
                    close_column=close_column,
                    label=label,
                )
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise PriceParityError(f"{label} could not be read: {exc}") from exc

    if not rows:
        raise PriceParityError(f"{label} must contain at least one data row.")
    _validate_daily_close_order(rows, label)

    return rows


def calendar_year_price_returns(
    rows: Sequence[DailyClose],
) -> tuple[CalendarYearPriceReturn, ...]:
    """Return last-close / first-close - 1 for each calendar year."""
    checked_rows = _daily_close_tuple(rows)
    grouped_rows: dict[int, list[DailyClose]] = {}
    for row in checked_rows:
        grouped_rows.setdefault(row.date.year, []).append(row)

    return tuple(
        CalendarYearPriceReturn(
            year=year,
            price_return=(year_rows[-1].close / year_rows[0].close) - Decimal("1"),
        )
        for year, year_rows in sorted(grouped_rows.items())
    )


def compare_calendar_year_price_returns(
    local_rows: Sequence[DailyClose],
    reference_rows: Sequence[DailyClose],
) -> tuple[PriceParityRow, ...]:
    """Compare only calendar years present in both close-price series."""
    local_returns = {
        item.year: item.price_return
        for item in calendar_year_price_returns(local_rows)
    }
    reference_returns = {
        item.year: item.price_return
        for item in calendar_year_price_returns(reference_rows)
    }
    overlapping_years = sorted(set(local_returns).intersection(reference_returns))
    if not overlapping_years:
        raise PriceParityError("No overlapping calendar years to compare.")

    return tuple(
        PriceParityRow(
            year=year,
            local_price_return=local_returns[year],
            reference_price_return=reference_returns[year],
            difference_bps=(local_returns[year] - reference_returns[year]) * _BPS,
        )
        for year in overlapping_years
    )


def render_parity_report(
    *,
    local_csv_path: str | Path,
    reference_csv_path: str | Path,
    rows: Sequence[PriceParityRow],
) -> str:
    """Render a small markdown parity table without raw input data."""
    checked_rows = tuple(rows)
    if not checked_rows:
        raise PriceParityError("parity report requires at least one comparison row.")

    lines = [
        "# SPY Price Parity Check",
        "",
        f"Local snapshot CSV: {Path(local_csv_path)}",
        f"External reference CSV: {Path(reference_csv_path)}",
        "",
        _DISCLAIMER,
        "",
        "| year | local_price_return | reference_price_return | difference_bps |",
        "| ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        (
            f"| {row.year} | "
            f"{_decimal_text(row.local_price_return, _RETURN_PLACES)} | "
            f"{_decimal_text(row.reference_price_return, _RETURN_PLACES)} | "
            f"{_decimal_text(row.difference_bps, _BPS_PLACES)} |"
        )
        for row in checked_rows
    )
    lines.append("")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare local SPY close-price calendar-year returns with a "
            "manually supplied external reference CSV."
        ),
    )
    parser.add_argument("local_csv_path", help="Explicit local snapshot CSV path.")
    parser.add_argument(
        "reference_csv_path",
        help="Explicit manually supplied external reference CSV path.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional markdown output path. Stdout is used when omitted.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        report = run_spy_price_parity(
            args.local_csv_path,
            args.reference_csv_path,
            output_path=args.output,
        )
    except PriceParityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output is None:
        sys.stdout.write(report)

    return 0


def _input_csv_path(path: str | Path, label: str) -> Path:
    if isinstance(path, str) and not path.strip():
        raise PriceParityError(f"{label} path is required.")
    if isinstance(path, str) and "://" in path:
        raise PriceParityError(f"{label} path must be a local CSV path.")
    if not isinstance(path, (str, Path)):
        raise PriceParityError(f"{label} path must be a local CSV path.")

    checked_path = Path(path).expanduser().resolve()
    if checked_path.suffix.lower() != ".csv":
        raise PriceParityError(f"{label} path must reference a CSV file.")
    if not checked_path.is_file():
        raise PriceParityError(f"{label} path must reference an existing local CSV file.")

    return checked_path


def _output_path_value(output_path: str | Path | None) -> Path | None:
    if output_path is None:
        return None
    if isinstance(output_path, str) and not output_path.strip():
        raise PriceParityError("output path is required when --output is provided.")
    if isinstance(output_path, str) and "://" in output_path:
        raise PriceParityError("output path must be a local markdown path.")
    if not isinstance(output_path, (str, Path)):
        raise PriceParityError("output path must be a local markdown path.")

    checked_path = Path(output_path).expanduser().resolve()
    if checked_path.suffix.lower() not in (".md", ".markdown"):
        raise PriceParityError("output path must reference a markdown file.")
    if checked_path.exists() and checked_path.is_dir():
        raise PriceParityError("output path must reference a markdown file, not a directory.")
    if not checked_path.parent.is_dir():
        raise PriceParityError("output directory must already exist.")

    return checked_path


def _date_and_close_columns(
    fieldnames: Sequence[str] | None,
    label: str,
) -> tuple[str, str]:
    if fieldnames is None:
        raise PriceParityError(f"{label} must include a header row.")

    normalized_columns = tuple(_column_name(column) for column in fieldnames)
    if len(set(normalized_columns)) != len(normalized_columns):
        raise PriceParityError(f"{label} must not contain duplicate columns.")

    column_lookup = dict(zip(normalized_columns, fieldnames, strict=True))
    missing_columns: list[str] = []
    if "date" not in column_lookup:
        missing_columns.append("date")

    close_columns = tuple(column for column in _CLOSE_COLUMNS if column in column_lookup)
    if not close_columns:
        missing_columns.append("close")
    if missing_columns:
        raise PriceParityError(
            f"{label} is missing required columns: {', '.join(missing_columns)}."
        )
    if len(close_columns) > 1:
        allowed = ", ".join(_CLOSE_COLUMNS)
        raise PriceParityError(
            f"{label} must include only one close column from: {allowed}."
        )

    return column_lookup["date"], column_lookup[close_columns[0]]


def _daily_close_from_row(
    *,
    row: dict[str, str],
    row_number: int,
    date_column: str,
    close_column: str,
    label: str,
) -> DailyClose:
    if None in row:
        raise PriceParityError(f"{label} row {row_number} has too many values.")

    return DailyClose(
        date=_date_value(row[date_column], f"{label} row {row_number} date"),
        close=_positive_decimal_value(
            row[close_column],
            f"{label} row {row_number} close",
        ),
    )


def _validate_daily_close_order(rows: tuple[DailyClose, ...], label: str) -> None:
    seen_dates: set[date] = set()
    previous_date: date | None = None
    for row in rows:
        if row.date in seen_dates:
            raise PriceParityError(f"{label} must not contain duplicate dates.")
        if previous_date is not None and row.date <= previous_date:
            raise PriceParityError(f"{label} dates must be strictly increasing.")

        seen_dates.add(row.date)
        previous_date = row.date


def _daily_close_tuple(rows: Sequence[DailyClose]) -> tuple[DailyClose, ...]:
    try:
        checked_rows = tuple(rows)
    except TypeError as exc:
        raise PriceParityError("daily close rows must be a sequence.") from exc
    if not checked_rows:
        raise PriceParityError("daily close rows must not be empty.")
    for row in checked_rows:
        if not isinstance(row, DailyClose):
            raise PriceParityError("daily close rows must contain DailyClose values.")

    return checked_rows


def _column_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PriceParityError("CSV columns must be non-empty strings.")

    return value.strip().lower()


def _date_value(value: str, field_name: str) -> date:
    if not isinstance(value, str):
        raise PriceParityError(f"{field_name} must be a YYYY-MM-DD date.")

    text = value.strip()
    if text != value or len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise PriceParityError(f"{field_name} must be a YYYY-MM-DD date.")

    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise PriceParityError(f"{field_name} must be a YYYY-MM-DD date.") from exc
    if parsed.isoformat() != text:
        raise PriceParityError(f"{field_name} must be a YYYY-MM-DD date.")

    return parsed


def _positive_decimal_value(value: str, field_name: str) -> Decimal:
    if not isinstance(value, str):
        raise PriceParityError(f"{field_name} must be a Decimal string.")

    text = value.strip()
    if text != value or not text:
        raise PriceParityError(f"{field_name} must be a Decimal string.")

    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise PriceParityError(f"{field_name} must be a Decimal string.") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise PriceParityError(f"{field_name} must be greater than zero.")

    return parsed


def _decimal_text(value: Decimal, places: Decimal) -> str:
    return format(value.quantize(places), "f")


if __name__ == "__main__":
    raise SystemExit(main())
