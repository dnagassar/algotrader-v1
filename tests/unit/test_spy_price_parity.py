import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest


MODULE_PATH = Path("scripts/research/check_spy_price_parity.py")
MODULE_NAME = "check_spy_price_parity_for_tests"
LOCAL_SNAPSHOT_COLUMNS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)


def load_parity() -> ModuleType:
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def write_csv(
    path: Path,
    rows: tuple[dict[str, str], ...],
    *,
    columns: tuple[str, ...] = ("date", "close"),
) -> Path:
    lines = [",".join(columns)]
    lines.extend(",".join(row.get(column, "") for column in columns) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_reference_csv(path: Path, *date_close_pairs: tuple[str, str]) -> Path:
    return write_csv(
        path,
        tuple({"date": item_date, "close": close} for item_date, close in date_close_pairs),
    )


def write_local_snapshot_csv(path: Path, *date_close_pairs: tuple[str, str]) -> Path:
    rows = []
    for index, (item_date, close) in enumerate(date_close_pairs, start=1):
        rows.append(
            {
                "date": item_date,
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "adjusted_close": close,
                "volume": str(1000 + index),
            }
        )

    return write_csv(path, tuple(rows), columns=LOCAL_SNAPSHOT_COLUMNS)


def test_calendar_year_price_return_uses_last_over_first_minus_one(
    tmp_path: Path,
) -> None:
    parity = load_parity()
    path = write_reference_csv(
        tmp_path / "prices.csv",
        ("2026-01-02", "100"),
        ("2026-06-01", "105"),
        ("2026-12-31", "125"),
    )

    returns = parity.calendar_year_price_returns(parity.load_daily_close_csv(path))

    assert returns == (
        parity.CalendarYearPriceReturn(year=2026, price_return=Decimal("0.25")),
    )


def test_parity_diff_is_reported_in_basis_points(tmp_path: Path) -> None:
    parity = load_parity()
    local_path = write_local_snapshot_csv(
        tmp_path / "local.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "110"),
    )
    reference_path = write_reference_csv(
        tmp_path / "reference.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "105"),
    )

    rows = parity.compare_calendar_year_price_returns(
        parity.load_daily_close_csv(local_path),
        parity.load_daily_close_csv(reference_path),
    )
    report = parity.run_spy_price_parity(local_path, reference_path)

    assert rows[0].difference_bps == Decimal("500")
    assert "| 2026 | 0.1000000000 | 0.0500000000 | 500.0000 |" in report


def test_only_overlapping_years_are_compared(tmp_path: Path) -> None:
    parity = load_parity()
    local_path = write_local_snapshot_csv(
        tmp_path / "local.csv",
        ("2024-01-02", "50"),
        ("2024-12-31", "55"),
        ("2025-01-02", "100"),
        ("2025-12-31", "110"),
    )
    reference_path = write_reference_csv(
        tmp_path / "reference.csv",
        ("2025-01-02", "100"),
        ("2025-12-31", "105"),
        ("2026-01-02", "200"),
        ("2026-12-31", "220"),
    )

    rows = parity.compare_calendar_year_price_returns(
        parity.load_daily_close_csv(local_path),
        parity.load_daily_close_csv(reference_path),
    )
    report = parity.run_spy_price_parity(local_path, reference_path)

    assert tuple(row.year for row in rows) == (2025,)
    assert "| 2024 |" not in report
    assert "| 2025 |" in report
    assert "| 2026 |" not in report


def test_duplicate_dates_are_rejected(tmp_path: Path) -> None:
    parity = load_parity()
    local_path = write_local_snapshot_csv(
        tmp_path / "local.csv",
        ("2026-01-02", "100"),
        ("2026-01-02", "101"),
    )
    reference_path = write_reference_csv(
        tmp_path / "reference.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "110"),
    )

    with pytest.raises(parity.PriceParityError, match="duplicate dates"):
        parity.run_spy_price_parity(local_path, reference_path)


def test_non_positive_close_is_rejected(tmp_path: Path) -> None:
    parity = load_parity()
    local_path = write_local_snapshot_csv(
        tmp_path / "local.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "0"),
    )
    reference_path = write_reference_csv(
        tmp_path / "reference.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "110"),
    )

    with pytest.raises(parity.PriceParityError, match="greater than zero"):
        parity.run_spy_price_parity(local_path, reference_path)


def test_missing_required_columns_are_rejected(tmp_path: Path) -> None:
    parity = load_parity()
    local_path = write_csv(
        tmp_path / "local.csv",
        ({"date": "2026-01-02", "open": "100"},),
        columns=("date", "open"),
    )
    reference_path = write_reference_csv(
        tmp_path / "reference.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "110"),
    )

    with pytest.raises(parity.PriceParityError, match="missing required columns"):
        parity.run_spy_price_parity(local_path, reference_path)


def test_script_output_labels_price_return_not_total_return(tmp_path: Path) -> None:
    parity = load_parity()
    local_path = write_local_snapshot_csv(
        tmp_path / "local.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "110"),
    )
    reference_path = write_reference_csv(
        tmp_path / "reference.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "105"),
    )

    report = parity.run_spy_price_parity(local_path, reference_path)

    assert "local_price_return" in report
    assert "reference_price_return" in report
    assert "price-return basis only" in report
    assert "total_return" not in report
    assert "total return" not in report.lower()


def test_script_does_not_require_data_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parity = load_parity()
    local_path = write_local_snapshot_csv(
        tmp_path / "local_snapshot.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "110"),
    )
    reference_path = write_reference_csv(
        tmp_path / "manual_reference.csv",
        ("2026-01-02", "100"),
        ("2026-12-31", "105"),
    )

    assert not (tmp_path / ".data").exists()

    exit_code = parity.main((str(local_path), str(reference_path)))
    captured = capsys.readouterr()

    assert exit_code == 0
    assert str(local_path.resolve()) in captured.out
    assert str(reference_path.resolve()) in captured.out
    assert captured.err == ""
    assert not (tmp_path / ".data").exists()
