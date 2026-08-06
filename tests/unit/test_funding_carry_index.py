"""Coverage for the V6.05 synthetic carry index.

Every panel here has a hand-computable answer. The construction is frozen by the
preregistration while the forward-shadow window is open, so these tests are the
thing that keeps it frozen.
"""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import funding_carry_index as subject
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

_INTERVAL_MS = 8 * 60 * 60 * 1000


def _stamp(day: int, slot: int = 0) -> int:
    base = datetime(2026, 1, day, 0, 0, tzinfo=UTC)
    return int(base.timestamp() * 1000) + slot * _INTERVAL_MS


def _panel(entries):
    return {stamp: dict(values) for stamp, values in entries}


def test_a_flat_book_earns_exactly_its_funding() -> None:
    """Prices unchanged, so the whole return is the funding the short receives."""

    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": 0.001, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 2), {"funding": 0.001, "index": 100.0, "perp": 100.0}),
    ])

    rows = subject.build_carry_index(panel, symbol="BTCCARRY")

    assert len(rows) == 1
    assert rows[0].intervals == 2
    assert rows[0].funding == pytest.approx(0.002)
    assert rows[0].basis == pytest.approx(0.0)
    # 1000 * 1.001 * 1.001
    assert rows[0].index_value == pytest.approx(1000.0 * 1.001 * 1.001)


def test_basis_uses_the_delta_neutral_expression_from_v6_00() -> None:
    """Short perp, long index: gain when the index outruns the perpetual."""

    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": 0.0, "index": 101.0, "perp": 100.0}),
    ])

    rows = subject.build_carry_index(panel, symbol="BTCCARRY")

    # (101/100 - 1) - (100/100 - 1) = +0.01
    assert rows[0].basis == pytest.approx(0.01)
    assert rows[0].index_value == pytest.approx(1010.0)


def test_a_perpetual_outrunning_the_index_costs_the_short() -> None:
    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": 0.0, "index": 100.0, "perp": 101.0}),
    ])

    rows = subject.build_carry_index(panel, symbol="BTCCARRY")

    assert rows[0].basis == pytest.approx(-0.01)
    assert rows[0].index_value < subject.CARRY_INDEX_BASE


def test_holding_costs_nothing_and_only_renewal_is_charged() -> None:
    """The entire hypothesis is that not trading is what makes this work."""

    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 2), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(2, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
    ])

    rows = subject.build_carry_index(panel, symbol="BTCCARRY")

    # Both sessions are in the same month, so nothing is charged at all.
    assert [row.session for row in rows] == [date(2026, 1, 1), date(2026, 1, 2)]
    assert [row.renewed for row in rows] == [False, False]
    assert all(row.cost == 0.0 for row in rows)
    assert rows[-1].index_value == pytest.approx(subject.CARRY_INDEX_BASE)


def test_a_month_boundary_charges_two_legs_once() -> None:
    january = datetime(2026, 1, 31, 0, 0, tzinfo=UTC)
    february = datetime(2026, 2, 1, 0, 0, tzinfo=UTC)
    panel = _panel([
        (int(january.timestamp() * 1000), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (int(january.timestamp() * 1000) + _INTERVAL_MS,
         {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (int(february.timestamp() * 1000) - _INTERVAL_MS,
         {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (int(february.timestamp() * 1000), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
    ])

    rows = subject.build_carry_index(panel, symbol="BTCCARRY", cost_bps_per_leg=5.0)

    february_rows = [row for row in rows if row.session.month == 2]
    assert february_rows and february_rows[0].renewed is True
    # 5 bps a leg, two legs.
    assert february_rows[0].cost == pytest.approx(0.001)


def test_a_gap_in_the_venue_data_is_skipped_not_compounded_across() -> None:
    """A missing interval is missing evidence, not a zero return."""

    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        # slot 1 absent
        (_stamp(1, 2), {"funding": 0.5, "index": 100.0, "perp": 100.0}),
    ])

    rows = subject.build_carry_index(panel, symbol="BTCCARRY")

    # The only candidate interval spans a hole, so no session is produced.
    assert rows == ()


def test_a_session_with_no_complete_interval_is_absent_not_flat() -> None:
    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(3, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
    ])

    rows = subject.build_carry_index(panel, symbol="BTCCARRY")

    assert [row.session for row in rows] == [date(2026, 1, 1)]


def test_a_book_that_wipes_out_is_refused_rather_than_reported() -> None:
    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": -2.0, "index": 100.0, "perp": 100.0}),
    ])

    with pytest.raises(ValidationError, match="non-positive"):
        subject.build_carry_index(panel, symbol="BTCCARRY")


def test_too_short_a_panel_is_refused() -> None:
    with pytest.raises(ValidationError, match="too short"):
        subject.build_carry_index(
            {_stamp(1, 0): {"funding": 0.0, "index": 1.0, "perp": 1.0}},
            symbol="BTCCARRY",
        )


def test_negative_costs_are_refused() -> None:
    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
    ])

    with pytest.raises(ValidationError, match="must not be negative"):
        subject.build_carry_index(panel, symbol="BTCCARRY", cost_bps_per_leg=-1.0)


# --- the benchmark and the written artifact --------------------------------


def test_the_cash_benchmark_is_flat() -> None:
    rows = subject.build_cash_series([date(2026, 1, 2), date(2026, 1, 1)])

    assert [row.session for row in rows] == [date(2026, 1, 1), date(2026, 1, 2)]
    assert {row.index_value for row in rows} == {subject.CARRY_INDEX_BASE}
    assert all(row.symbol == subject.CASH_SYMBOL for row in rows)


def test_written_bars_load_back_through_the_strict_loader(tmp_path: Path) -> None:
    """The forward shadow reads this file, so it must satisfy that loader."""

    panel = _panel([
        (_stamp(1, 0), {"funding": 0.0, "index": 100.0, "perp": 100.0}),
        (_stamp(1, 1), {"funding": 0.001, "index": 100.0, "perp": 100.0}),
        (_stamp(2, 0), {"funding": 0.001, "index": 100.0, "perp": 100.0}),
    ])
    carry = subject.build_carry_index(panel, symbol="BTCCARRY")
    cash = subject.build_cash_series([row.session for row in carry])
    target = tmp_path / "carry.csv"

    receipt = subject.write_canonical_daily_bars(target, [*carry, *cash])

    assert receipt["symbols"] == ["BTCCARRY", "USDCASH"]
    loaded = load_local_daily_bars_csv(target, symbol="BTCCARRY")
    assert len(loaded.usable_bars) == len(carry)
    # A synthetic index has no intraday range; all four prices are the level.
    first = loaded.usable_bars[0]
    assert first.open == first.high == first.low == first.close


def test_writing_refuses_a_duplicated_session(tmp_path: Path) -> None:
    row = subject.CarryIndexRow(
        symbol="BTCCARRY", session=date(2026, 1, 1), index_value=1000.0,
        intervals=1, funding=0.0, basis=0.0, cost=0.0, renewed=False,
    )

    with pytest.raises(ValidationError, match="duplicate session"):
        subject.write_canonical_daily_bars(tmp_path / "x.csv", [row, row])


def test_writing_nothing_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="no rows"):
        subject.write_canonical_daily_bars(tmp_path / "x.csv", [])
