"""Scoring-path coverage for the V5.98 tax-loss detector.

Synthetic panels with hand-computable answers. The V5.96 and V5.97 defects both
survived because the only checks were structural — counts, dates, shapes — and
nothing pinned the arithmetic.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from algotrader.errors import ValidationError
from algotrader.research import tax_loss_detector as subject


def _sessions(start: date, end: date) -> list[date]:
    """Every weekday between two dates, which is enough to have month-ends."""

    out, cursor = [], start
    while cursor <= end:
        if cursor.weekday() < 5:
            out.append(cursor)
        cursor += timedelta(days=1)
    return out


def test_universe_and_quintile_are_frozen() -> None:
    assert len(subject.UNIVERSE) == 45
    assert subject._LOSER_COUNT == 9
    assert subject.FORMATION_YEARS[0] == 2007
    assert subject.FORMATION_YEARS[-1] == 2025
    assert len(subject.FORMATION_YEARS) == 19
    # The universe order is the frozen tie-break, so it must not be a set.
    assert isinstance(subject.UNIVERSE, tuple)
    assert len(set(subject.UNIVERSE)) == 45


def test_binomial_tail_is_exact_at_the_preregistered_threshold() -> None:
    # 14 of 19 was the frozen primary gate; 13 was declared insufficient.
    assert subject._binomial_tail(14, 19) == pytest.approx(0.03178, abs=1e-5)
    assert subject._binomial_tail(13, 19) == pytest.approx(0.08353, abs=1e-5)
    assert subject._binomial_tail(19, 19) == pytest.approx(1.0 / 2**19)
    assert subject._binomial_tail(0, 19) == pytest.approx(1.0)
    with pytest.raises(ValidationError, match="out of range"):
        subject._binomial_tail(3, 0)


def test_last_session_of_month_picks_the_final_session() -> None:
    dates = _sessions(date(2020, 11, 1), date(2021, 2, 5))

    november = subject._last_session_of(dates, 2020, 11)
    december = subject._last_session_of(dates, 2020, 12)
    january = subject._last_session_of(dates, 2021, 1)

    assert dates[november] == date(2020, 11, 30)
    assert dates[december] == date(2020, 12, 31)
    assert dates[january] == date(2021, 1, 29)
    assert november < december < january


def test_missing_month_blocks_rather_than_guessing() -> None:
    dates = _sessions(date(2020, 11, 1), date(2020, 11, 30))
    with pytest.raises(ValidationError, match="no sessions"):
        subject._last_session_of(dates, 2020, 12)


def test_basket_return_is_the_equal_weight_mean() -> None:
    prices = {"A": (100.0, 110.0), "B": (100.0, 90.0), "C": (50.0, 50.0)}

    assert subject._basket_return(prices, ("A", "B"), 0, 1) == pytest.approx(0.0)
    assert subject._basket_return(prices, ("A",), 0, 1) == pytest.approx(0.10)
    assert subject._basket_return(prices, ("A", "B", "C"), 0, 1) == pytest.approx(
        0.0, abs=1e-12
    )


def _cycle_panel(ytd_moves, december_moves, january_moves):
    """Build a 45-symbol panel with prescribed moves in each leg."""

    dates = _sessions(date(2019, 12, 1), date(2021, 2, 5))
    base = subject._last_session_of(dates, 2019, 12)
    formation = subject._last_session_of(dates, 2020, 11)
    december = subject._last_session_of(dates, 2020, 12)
    january = subject._last_session_of(dates, 2021, 1)

    prices = {}
    for index, symbol in enumerate(subject.UNIVERSE):
        series = [100.0] * len(dates)
        ytd, dec, jan = ytd_moves[index], december_moves[index], january_moves[index]
        for position in range(len(dates)):
            value = 100.0
            if position > base:
                value *= 1.0 + ytd
            if position > formation:
                value *= 1.0 + dec
            if position > december:
                value *= 1.0 + jan
            series[position] = value
        prices[symbol] = tuple(series)
    return dates, prices


def test_losers_are_the_bottom_quintile_by_year_to_date_return() -> None:
    # First nine symbols fall on the year; the rest rise.
    ytd = [-0.50 if index < 9 else 0.20 for index in range(45)]
    dates, prices = _cycle_panel(ytd, [0.0] * 45, [0.0] * 45)

    cycle = subject._score_cycle(dates, prices, 2020)

    assert cycle["loser_basket"] == list(subject.UNIVERSE[:9])
    assert float(cycle["loser_basket_mean_year_to_date_return"]) == pytest.approx(
        -0.50, abs=1e-12
    )


def test_december_and_january_excess_are_exact() -> None:
    ytd = [-0.50 if index < 9 else 0.20 for index in range(45)]
    # Losers fall a further 10% in December and rebound 20% in January.
    december = [-0.10 if index < 9 else 0.0 for index in range(45)]
    january = [0.20 if index < 9 else 0.0 for index in range(45)]
    dates, prices = _cycle_panel(ytd, december, january)

    cycle = subject._score_cycle(dates, prices, 2020)

    # December: losers -10%, universe mean = 9/45 * -10% = -2%.
    assert float(cycle["december_loser_return"]) == pytest.approx(-0.10, abs=1e-12)
    assert float(cycle["december_universe_return"]) == pytest.approx(-0.02, abs=1e-12)
    assert float(cycle["december_excess"]) == pytest.approx(-0.08, abs=1e-12)
    # January: losers +20%, universe mean = 9/45 * 20% = +4%.
    assert float(cycle["january_loser_gross_return"]) == pytest.approx(0.20, abs=1e-12)
    assert float(cycle["january_universe_return"]) == pytest.approx(0.04, abs=1e-12)


def test_january_costs_are_a_round_trip_charged_only_to_the_strategy() -> None:
    ytd = [-0.50 if index < 9 else 0.20 for index in range(45)]
    january = [0.20 if index < 9 else 0.0 for index in range(45)]
    dates, prices = _cycle_panel(ytd, [0.0] * 45, january)

    cycle = subject._score_cycle(dates, prices, 2020)

    rate = subject._COSTS["decision"]
    expected_net = (1.0 + 0.20) * (1.0 - rate) * (1.0 - rate) - 1.0
    expected_excess = expected_net - 0.04
    assert float(cycle["january_excess"]["decision"]) == pytest.approx(
        expected_excess, abs=1e-12
    )
    # Stress costs must reduce the excess further, never improve it.
    assert float(cycle["january_excess"]["stress"]) < float(
        cycle["january_excess"]["decision"]
    )


def test_cycle_dates_are_strictly_ordered_and_causal() -> None:
    ytd = [-0.50 if index < 9 else 0.20 for index in range(45)]
    dates, prices = _cycle_panel(ytd, [0.0] * 45, [0.0] * 45)

    cycle = subject._score_cycle(dates, prices, 2020)

    assert cycle["base_session"] == "2019-12-31"
    assert cycle["formation_session"] == "2020-11-30"
    assert cycle["december_close_session"] == "2020-12-31"
    assert cycle["january_close_session"] == "2021-01-29"
    # Selection happens strictly before either leg is measured.
    assert cycle["base_session"] < cycle["formation_session"]
    assert cycle["formation_session"] < cycle["december_close_session"]
    assert cycle["december_close_session"] < cycle["january_close_session"]


def test_january_move_cannot_influence_loser_selection() -> None:
    """A huge January move must not change who was ranked a loser in November."""

    ytd = [-0.50 if index < 9 else 0.20 for index in range(45)]
    dates, prices = _cycle_panel(ytd, [0.0] * 45, [0.0] * 45)
    baseline = subject._score_cycle(dates, prices, 2020)

    # Give the winners an enormous January rally; selection must be unchanged.
    january = [0.0 if index < 9 else 5.0 for index in range(45)]
    dates2, prices2 = _cycle_panel(ytd, [0.0] * 45, january)
    perturbed = subject._score_cycle(dates2, prices2, 2020)

    assert perturbed["loser_basket"] == baseline["loser_basket"]
    assert perturbed["december_excess"] == baseline["december_excess"]


def test_preregistration_declares_its_contamination_honestly() -> None:
    payload = subject.build_detector_preregistration()

    assert payload["universe_size"] == 45
    assert payload["cycles"] == 19
    assert payload["loser_basket_size"] == 9
    # The universe is reused, and the protocol says so rather than claiming Tier A.
    assert payload["vault_fresh"] is False
    assert payload["orthogonal_to_prior_examinations"] is True
    assert payload["january_only_result_fails"] is True
    assert payload["network_requests_performed"] == 0
    assert payload["validated_alpha_claimed"] is False
    assert payload["safety"]["network_access_performed"] is False
    assert payload["safety"]["live_authorized"] is False
