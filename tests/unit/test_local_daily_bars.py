from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    load_local_daily_bars_csv,
)


AS_OF = "2026-06-05T00:00:00+00:00"


def test_load_local_daily_bars_counts_only_requested_symbol_before_as_of(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "spy_daily_bars.csv",
        [
            _row("SPY", "2026-06-04", 100),
            _row("QQQ", "2026-06-04", 200),
            _row("SPY", "2026-06-06", 101),
        ],
    )

    result = load_local_daily_bars_csv(csv_path, symbol="SPY", as_of=AS_OF)

    assert result.total_row_count == 3
    assert result.matching_symbol_row_count == 2
    assert result.ignored_wrong_symbol_row_count == 1
    assert result.ignored_future_bar_count == 1
    assert result.observed_usable_bars == 1
    assert [bar.date.isoformat() for bar in result.usable_bars] == ["2026-06-04"]
    assert [bar.symbol for bar in result.usable_bars] == ["SPY"]


def test_load_local_daily_bars_sorts_requested_symbol_rows(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "unsorted_spy_daily_bars.csv",
        [
            _row("SPY", "2026-06-03", 103),
            _row("SPY", "2026-06-01", 101),
            _row("SPY", "2026-06-02", 102),
        ],
    )

    result = load_local_daily_bars_csv(csv_path, symbol="SPY", as_of=AS_OF)

    assert result.input_sorted_by_date is False
    assert [bar.date.isoformat() for bar in result.usable_bars] == [
        "2026-06-01",
        "2026-06-02",
        "2026-06-03",
    ]


def test_load_local_daily_bars_duplicate_requested_symbol_dates_fail_closed(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "duplicate_spy_daily_bars.csv",
        [
            _row("SPY", "2026-06-04", 100),
            _row("SPY", "2026-06-04", 101),
        ],
    )

    with pytest.raises(ValidationError, match="duplicates date 2026-06-04"):
        load_local_daily_bars_csv(csv_path, symbol="SPY", as_of=AS_OF)


def test_load_local_daily_bars_missing_required_columns_fail_closed(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = tmp_path / "missing_columns.csv"
    csv_path.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "SPY,2026-06-04,100,101,99,100,1000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="adjusted_close"):
        load_local_daily_bars_csv(csv_path, symbol="SPY", as_of=AS_OF)


def test_load_local_daily_bars_missing_path_fails_closed(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValidationError, match="existing local CSV"):
        load_local_daily_bars_csv(
            tmp_path / "missing_spy_daily_bars.csv",
            symbol="SPY",
            as_of=AS_OF,
        )


def _write_daily_bars_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    lines.extend(",".join(row[column] for column in LOCAL_DAILY_BARS_CSV_COLUMNS) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _row(symbol: str, day: str, price: int) -> dict[str, str]:
    parsed = date.fromisoformat(day)
    assert parsed.isoformat() == day
    return {
        "symbol": symbol,
        "date": day,
        "open": str(price),
        "high": str(price + 1),
        "low": str(price - 1),
        "close": str(price),
        "adjusted_close": str(price),
        "volume": "1000",
    }
