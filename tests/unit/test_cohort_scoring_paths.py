"""Scoring-path coverage for the V5.96 and V5.97 cohort engines.

These two engines shipped the session's first two measurement defects — daily
labels scored against monthly actions, then a double lag when that was
repaired. Both survived because the engines only had structural checks. The
tests here pin the arithmetic and the causal ordering on synthetic panels whose
answers are computable by hand.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from algotrader.errors import ValidationError
from algotrader.research import cohort2_scoring as cohort2
from algotrader.research import tier_a_cohort_scoring as cohort1


def _month_grid(months: int, start: date = date(2020, 1, 1)) -> list[date]:
    """Two sessions per month so every month has an unambiguous month-end."""

    out, cursor = [], start
    for _ in range(months):
        last = (
            date(cursor.year, 12, 31)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1) - timedelta(days=1)
        )
        out.append(date(cursor.year, cursor.month, 15))
        out.append(last)
        cursor = last + timedelta(days=1)
    return out


def _flat_prices(dates, symbols, per_symbol=None):
    return {
        symbol: tuple(
            (per_symbol or {}).get(symbol, [100.0] * len(dates))[index]
            for index in range(len(dates))
        )
        for symbol in symbols
    }


# --- conditional basket arithmetic -----------------------------------------


def test_basket_holds_only_after_a_month_end_in_the_declared_regime() -> None:
    dates = _month_grid(6)
    assets = ("A", "B")
    prices = _flat_prices(dates, assets)
    # Regime active from the very first month-end onward.
    labels = ["calm_up"] * len(dates)

    returns = cohort2._conditional_basket(
        dates, prices, assets, labels, "calm_up", 0.0
    )

    assert len(returns) == len(dates)
    # Flat prices, so every booked return is zero and nothing is invented.
    assert all(value == pytest.approx(0.0) for value in returns)


def test_basket_earns_the_equal_weight_move_while_held() -> None:
    dates = _month_grid(4)
    assets = ("A", "B")
    moves = {
        "A": [100.0] * 3 + [110.0] * (len(dates) - 3),
        "B": [100.0] * len(dates),
    }
    prices = _flat_prices(dates, assets, moves)
    labels = ["calm_up"] * len(dates)

    returns = cohort2._conditional_basket(
        dates, prices, assets, labels, "calm_up", 0.0
    )

    # A rises 10% at index 3 while held at 1/2 weight; B is flat.
    assert returns[3] == pytest.approx(0.05, abs=1e-12)


def test_basket_stays_flat_when_the_regime_is_never_active() -> None:
    dates = _month_grid(5)
    assets = ("A", "B")
    moves = {"A": [100.0 * (1.05**i) for i in range(len(dates))],
             "B": [100.0 * (1.05**i) for i in range(len(dates))]}
    prices = _flat_prices(dates, assets, moves)
    labels = ["stressed_down"] * len(dates)

    returns = cohort2._conditional_basket(
        dates, prices, assets, labels, "calm_up", 0.0
    )

    # Declared regime never occurs, so the sleeve books nothing at all despite
    # a strongly rising basket. This is the property that makes out-of-regime
    # drag meaningful.
    assert all(value == pytest.approx(0.0) for value in returns)


def test_benchmark_mode_holds_continuously_regardless_of_labels() -> None:
    dates = _month_grid(4)
    assets = ("A",)
    moves = {"A": [100.0] * 3 + [110.0] * (len(dates) - 3)}
    prices = _flat_prices(dates, assets, moves)
    labels = ["stressed_down"] * len(dates)

    returns = cohort2._conditional_basket(dates, prices, assets, labels, None, 0.0)

    # active_regime=None means "always held", so the move is captured even
    # though the label never matches anything.
    assert returns[3] == pytest.approx(0.10, abs=1e-12)


def test_entry_turnover_is_charged_once_at_the_first_action() -> None:
    dates = _month_grid(4)
    assets = ("A",)
    prices = _flat_prices(dates, assets)
    labels = ["calm_up"] * len(dates)

    free = cohort2._conditional_basket(dates, prices, assets, labels, "calm_up", 0.0)
    charged = cohort2._conditional_basket(
        dates, prices, assets, labels, "calm_up", 0.0005
    )

    difference = [c - f for c, f in zip(charged, free, strict=True)]
    # Exactly one interval bears the entry cost; the rest are unaffected.
    assert sum(1 for value in difference if abs(value) > 1e-12) == 1
    assert min(difference) == pytest.approx(-0.0005, abs=1e-12)


def test_basket_weights_are_exactly_equal_across_assets() -> None:
    """One asset moving must contribute exactly 1/n of its own return."""

    for count in (2, 3, 5):
        assets = tuple(chr(ord("A") + index) for index in range(count))
        dates = _month_grid(4)
        moves = {assets[0]: [100.0] * 3 + [110.0] * (len(dates) - 3)}
        prices = _flat_prices(dates, assets, moves)
        labels = ["calm_up"] * len(dates)

        returns = cohort2._conditional_basket(
            dates, prices, assets, labels, "calm_up", 0.0
        )

        assert returns[3] == pytest.approx(0.10 / count, abs=1e-12)


def test_total_wipeout_is_refused_rather_than_compounded() -> None:
    dates = _month_grid(3)
    assets = ("A",)
    # A price of zero is a -100% move; equity would vanish, so it must block.
    moves = {"A": [100.0, 100.0, 100.0, 100.0, 0.0, 0.0]}
    prices = _flat_prices(dates, assets, moves)
    labels = ["calm_up"] * len(dates)

    with pytest.raises(ValidationError, match="nonpositive"):
        cohort2._conditional_basket(dates, prices, assets, labels, "calm_up", 0.0)


# --- the V5.97 double-lag regression ---------------------------------------


def test_targets_form_on_raw_labels_not_effective_labels() -> None:
    """Regression for the V5.97 double lag.

    Passing effective labels into target formation lagged the component a
    second time, because effective labels already point at the prior
    month-end. It swung one component's Sharpe edge from -0.118 to +0.353.
    """

    from algotrader.research.regime_classifier import effective_action_labels

    dates = _month_grid(6)
    assets = ("A",)
    prices = _flat_prices(dates, assets)
    raw = ["calm_up"] * len(dates)
    effective = list(effective_action_labels(dates, raw))

    on_raw = cohort2._conditional_basket(dates, prices, assets, raw, "calm_up", 0.0005)
    on_effective = cohort2._conditional_basket(
        dates, prices, assets, effective, "calm_up", 0.0005
    )

    entry_on_raw = next(i for i, v in enumerate(on_raw) if v != 0.0)
    entry_on_effective = next(i for i, v in enumerate(on_effective) if v != 0.0)
    # Forming on effective labels delays entry by a full action, which is the
    # defect. The engine must use raw labels for formation.
    assert entry_on_effective > entry_on_raw


# --- frozen cohort declarations --------------------------------------------


def test_cohort_one_declares_four_components_across_four_regimes() -> None:
    assert cohort1.PLANNED_COMPONENT_COUNT == 4
    assert cohort1.REGIME_COUNT == 4
    assert len(cohort1.COMPONENTS) == 4
    assert cohort1.ADJUSTED_ALPHA == pytest.approx(0.05 / 16)
    regimes = {regime for _, regime, _ in cohort1.COMPONENTS}
    assert len(regimes) == 4, "each component must claim a distinct regime"


def test_cohort_two_excludes_the_unoccupied_regime() -> None:
    assert cohort2.PLANNED_COMPONENT_COUNT == 3
    assert cohort2.REGIME_COUNT == 4, "divisor keeps the frozen regime count"
    assert cohort2.ADJUSTED_ALPHA == pytest.approx(0.05 / 12)
    regimes = {regime for _, regime, _ in cohort2.COMPONENTS}
    # calm_down failed the occupancy precondition and hosts nothing.
    assert "calm_down" not in regimes
    assert len(regimes) == 3


def test_cohort_two_enforces_minimum_occupancy() -> None:
    assert cohort2.MINIMUM_REGIME_EPISODES == 8
    assert cohort2.MINIMUM_EPISODE_SESSIONS == 10


def test_no_component_reuses_another_cohorts_assets() -> None:
    first = {asset for _, _, assets in cohort1.COMPONENTS for asset in assets}
    second = {asset for _, _, assets in cohort2.COMPONENTS for asset in assets}
    assert not (first & second), "cohort 2 must not reuse scored assets"
