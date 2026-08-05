"""Coverage for the survivorship inflation measurement.

Every case has a hand-computable answer. The ticker-reuse admission rule is
pinned hardest, because admitting a reused ticker is the failure this whole
line of work exists to prevent.
"""

from __future__ import annotations

from datetime import date

import pytest

from algotrader.errors import ValidationError
from algotrader.research import survivorship_inflation as subject


def _ret(symbol: str, value: float, *, years: float = 5.0, dead: date | None = None):
    return subject.SymbolReturn(
        symbol=symbol, annualized_return=value, years=years, delisted_on=dead
    )


def test_inflation_is_the_gap_between_survivors_and_everything() -> None:
    observations = [
        _ret("EWA", 0.10),
        _ret("EWC", 0.20),
        _ret("DEAD1", -0.30, dead=date(2020, 5, 1)),
    ]

    result = subject.measure_survivorship_inflation(observations)

    assert result.survivor_count == 2
    assert result.delisted_count == 1
    assert result.survivor_mean == pytest.approx(0.15)
    assert result.combined_mean == pytest.approx(0.0)
    assert result.inflation == pytest.approx(0.15)


def test_a_universe_with_no_casualties_shows_no_inflation() -> None:
    result = subject.measure_survivorship_inflation([_ret("A", 0.1), _ret("B", 0.2)])

    assert result.delisted_count == 0
    assert result.inflation == pytest.approx(0.0)


def test_the_result_is_always_labelled_a_lower_bound() -> None:
    """Securities absent from the price source cannot enter the calculation."""

    payload = subject.measure_survivorship_inflation(
        [_ret("A", 0.1), _ret("D", -0.5, dead=date(2021, 1, 1))]
    ).as_payload()

    assert payload["is_lower_bound"] is True


def test_a_minimum_history_filter_applies_to_both_groups() -> None:
    observations = [
        _ret("A", 0.10, years=6.0),
        _ret("B", 0.90, years=0.2),
        _ret("D", -0.40, years=0.1, dead=date(2020, 1, 1)),
    ]

    result = subject.measure_survivorship_inflation(observations, minimum_years=1.0)

    assert result.survivor_count == 1
    assert result.delisted_count == 0
    assert result.survivor_mean == pytest.approx(0.10)


def test_measuring_without_any_survivor_is_refused() -> None:
    with pytest.raises(ValidationError, match="no surviving symbols"):
        subject.measure_survivorship_inflation([_ret("D", 0.1, dead=date(2020, 1, 1))])


# --- the ticker-reuse rule, pinned -----------------------------------------


def test_a_series_starting_after_the_delisting_is_discarded() -> None:
    """HAO delisted in 2019; the series on offer begins in 2024 under another
    issuer entirely. Admitting it would splice two securities."""

    verdict = subject.admit_symbol_observation(
        symbol="HAO",
        first_bar=date(2024, 1, 26),
        last_bar=date(2026, 8, 4),
        delisted_on=date(2019, 2, 28),
    )

    assert verdict["admitted"] is False
    assert verdict["reason"] == "ticker_reused_after_delisting"


def test_a_delisted_series_is_truncated_at_its_delisting() -> None:
    verdict = subject.admit_symbol_observation(
        symbol="FRN",
        first_bar=date(2008, 6, 13),
        last_bar=date(2020, 2, 14),
        delisted_on=date(2020, 2, 14),
    )

    assert verdict["admitted"] is True
    assert verdict["admit_through"] == "2020-02-14"


def test_a_live_symbol_needs_no_truncation() -> None:
    verdict = subject.admit_symbol_observation(
        symbol="SPY",
        first_bar=date(1993, 1, 29),
        last_bar=date(2026, 8, 4),
        delisted_on=None,
    )

    assert verdict["admitted"] is True
    assert verdict["admit_through"] is None


def test_a_security_still_trading_after_its_form25_is_not_a_casualty() -> None:
    """NORW filed a Form 25 in 2021 and has an unbroken series through 2026.

    Form 25 notifies removal from a listing, which an exchange transfer also
    triggers. Counting that as a death would put a live fund's arbitrarily
    truncated return into the dead pool and overstate the measured inflation.
    """

    verdict = subject.admit_symbol_observation(
        symbol="NORW",
        first_bar=date(2009, 8, 19),
        last_bar=date(2026, 8, 4),
        delisted_on=date(2021, 10, 22),
    )

    assert verdict["admitted"] is False
    assert verdict["reason"] == "continued_trading_after_delisting"
    assert verdict["traded_through"] == "2026-08-04"


def test_a_short_data_tail_after_the_filing_is_still_a_delisting() -> None:
    """Settlement and final NAV bars land days after the notice, not months."""

    verdict = subject.admit_symbol_observation(
        symbol="FRN",
        first_bar=date(2008, 6, 13),
        last_bar=date(2020, 3, 2),
        delisted_on=date(2020, 2, 14),
    )

    assert verdict["admitted"] is True
    assert verdict["reason"] == "truncated_at_delisting"


def test_a_symbol_the_vendor_does_not_serve_is_not_invented() -> None:
    verdict = subject.admit_symbol_observation(
        symbol="SIVB", first_bar=None, last_bar=None, delisted_on=date(2023, 5, 2)
    )

    assert verdict["admitted"] is False
    assert verdict["reason"] == "no_price_history"


# --- arithmetic ------------------------------------------------------------


def test_annualized_return_is_the_compound_rate() -> None:
    assert subject.annualized_return(100.0, 200.0, 1.0) == pytest.approx(1.0)
    assert subject.annualized_return(100.0, 100.0, 5.0) == pytest.approx(0.0)
    assert subject.annualized_return(100.0, 121.0, 2.0) == pytest.approx(0.10)


def test_degenerate_inputs_are_refused_rather_than_returned() -> None:
    with pytest.raises(ValidationError):
        subject.annualized_return(0.0, 10.0, 1.0)
    with pytest.raises(ValidationError):
        subject.annualized_return(10.0, 10.0, 0.0)


def test_groups_are_summarised_separately() -> None:
    observations = [
        _ret("EWA", 0.10),
        _ret("EWC", 0.20),
        _ret("DEAD1", -0.30, dead=date(2020, 5, 1)),
        _ret("SPY", 0.12),
    ]

    summary = subject.summarize_by_group(
        observations,
        {"country": ["EWA", "EWC", "DEAD1"], "broad": ["SPY"]},
    )

    assert summary["country"]["inflation_annualized"] == pytest.approx(0.15)
    assert summary["broad"]["delisted_count"] == 0
