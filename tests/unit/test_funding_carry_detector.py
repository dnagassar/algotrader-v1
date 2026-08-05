"""Scoring-path coverage for the V5.99 funding carry detector.

Every test here uses synthetic panels whose correct answer is computable by
hand. Real-data tests can only check structure; they cannot tell you the
arithmetic is right, which is exactly how three measurement defects reached
production in this session.
"""

from __future__ import annotations

import pytest

from algotrader.errors import ValidationError
from algotrader.research import funding_carry_detector as subject

_INTERVAL = subject._INTERVAL_MS


def _panel(rows):
    """Build a panel from (funding, index, perp) triples on the 8h grid."""

    return {
        _INTERVAL * (index + 1): {
            "funding": funding,
            "index": index_price,
            "perp": perp_price,
        }
        for index, (funding, index_price, perp_price) in enumerate(rows)
    }


# --- the V5.99 defect, now a permanent guard -------------------------------


def test_signal_to_noise_blocks_unsynchronised_prices() -> None:
    """Regression for V5.99: basis noise ~100x funding produced a fake result.

    The engine reported -6.3% annualised on data where the two price legs were
    stamped at different instants. That number was meaningless. The ratio is
    now a precondition, so the same data blocks instead of scoring.
    """

    # Funding is tiny and steady; the two legs wander apart by ~1% per interval.
    rows = []
    for index in range(50):
        drift = 1.0 + 0.01 * (1 if index % 2 == 0 else -1)
        rows.append((0.00005, 100.0, 100.0 * drift))
    panel = _panel(rows)

    with pytest.raises(ValidationError, match="basis noise swamps"):
        subject.validate_signal_to_noise(panel)


def test_signal_to_noise_accepts_synchronised_prices() -> None:
    rows = [(0.0002, 100.0 + index, 100.0 + index) for index in range(50)]

    report = subject.validate_signal_to_noise(_panel(rows))

    assert report["sufficient"] is True
    assert float(report["basis_to_funding_ratio"]) <= 10.0
    assert float(report["mean_absolute_basis"]) == pytest.approx(0.0, abs=1e-12)


def test_signal_to_noise_rejects_a_panel_with_no_funding() -> None:
    rows = [(0.0, 100.0, 100.0) for _ in range(20)]
    with pytest.raises(ValidationError, match="no funding signal"):
        subject.validate_signal_to_noise(_panel(rows))


def test_signal_to_noise_needs_at_least_two_intervals() -> None:
    with pytest.raises(ValidationError, match="too short"):
        subject.validate_signal_to_noise(_panel([(0.0001, 100.0, 100.0)]))


# --- known-answer arithmetic ----------------------------------------------


def test_perfectly_hedged_carry_returns_funding_minus_costs() -> None:
    """With perp == index the basis vanishes, so the answer is exact by hand."""

    # Funding positive throughout, both legs identical and moving together.
    rows = [(0.001, 100.0 * (1.02**index), 100.0 * (1.02**index))
            for index in range(6)]
    panel = _panel(rows)
    grid = sorted(panel)

    returns = subject._simulate(panel, grid, 0.0)

    # Interval 0 establishes the position and books nothing.
    assert returns[0] == pytest.approx(0.0)
    # Every later interval collects funding exactly; the price move cancels.
    for value in returns[1:]:
        assert value == pytest.approx(0.001, abs=1e-12)


def test_entry_cost_is_two_legs_and_charged_once() -> None:
    # Funding turns positive at interval 1 and stays positive.
    rows = [(-0.001, 100.0, 100.0)] + [(0.001, 100.0, 100.0) for _ in range(4)]
    panel = _panel(rows)
    grid = sorted(panel)

    returns = subject._simulate(panel, grid, 0.0005)

    # Interval 1 flips flat -> held: two legs at 5 bps, plus no carry yet.
    assert returns[1] == pytest.approx(-2 * 0.0005, abs=1e-12)
    # Interval 2 is already held, so it collects funding with no further cost.
    assert returns[2] == pytest.approx(0.001, abs=1e-12)
    assert returns[3] == pytest.approx(0.001, abs=1e-12)


def test_exit_cost_is_charged_when_funding_turns_negative() -> None:
    rows = [(0.001, 100.0, 100.0) for _ in range(3)] + [(-0.001, 100.0, 100.0)]
    panel = _panel(rows)
    grid = sorted(panel)

    returns = subject._simulate(panel, grid, 0.0005)

    # Timing semantics, pinned deliberately: funding stamped at t settles the
    # period ENDING at t, so a position held into the exit interval pays that
    # interval's funding. Here it has flipped negative, so the short side pays
    # 0.001 and is then charged two legs to close.
    assert returns[-1] == pytest.approx(-0.001 - 2 * 0.0005, abs=1e-12)


def test_no_position_is_held_while_funding_is_negative() -> None:
    rows = [(-0.002, 100.0, 100.0) for _ in range(5)]
    panel = _panel(rows)
    grid = sorted(panel)

    returns = subject._simulate(panel, grid, 0.0005)

    # Never entered, so nothing is earned and nothing is charged.
    assert all(value == pytest.approx(0.0) for value in returns)


def test_basis_move_against_the_short_leg_is_a_loss() -> None:
    """A perp gapping above spot hurts the short-perp leg, as it must."""

    rows = [(0.001, 100.0, 100.0), (0.001, 100.0, 105.0)]
    panel = _panel(rows)
    grid = sorted(panel)

    returns = subject._simulate(panel, grid, 0.0)

    # spot flat, perp +5%, short perp loses 5%, funding adds 0.1%.
    assert returns[1] == pytest.approx(0.001 - 0.05, abs=1e-12)


def test_signal_uses_only_information_available_at_the_interval() -> None:
    """Funding settled at t decides the holding for t onward, never earlier."""

    rows = [(-0.001, 100.0, 100.0), (-0.001, 100.0, 100.0),
            (0.005, 100.0, 100.0), (0.005, 100.0, 100.0)]
    panel = _panel(rows)
    grid = sorted(panel)

    returns = subject._simulate(panel, grid, 0.0)

    # The large funding at interval 2 cannot leak into intervals 0 or 1.
    assert returns[0] == pytest.approx(0.0)
    assert returns[1] == pytest.approx(0.0)
    assert returns[3] == pytest.approx(0.005, abs=1e-12)


# --- metrics ---------------------------------------------------------------


def test_metrics_are_exact_on_a_known_series() -> None:
    metrics = subject._metrics([0.10, -0.10])

    # 1.10 * 0.90 = 0.99
    assert float(metrics["total_return"]) == pytest.approx(-0.01, abs=1e-12)
    # Peak 1.10 then 0.99 -> drawdown 1 - 0.99/1.10.
    assert float(metrics["max_drawdown"]) == pytest.approx(0.1, abs=1e-12)
    assert float(metrics["worst_interval"]) == pytest.approx(-0.10)
    assert metrics["intervals"] == 2


def test_metrics_reject_a_wipeout() -> None:
    with pytest.raises(ValidationError, match="nonpositive"):
        subject._metrics([-1.0])


def test_compound_matches_sequential_multiplication() -> None:
    assert subject._compound([0.1, 0.1]) == pytest.approx(0.21, abs=1e-12)
    assert subject._compound([]) == pytest.approx(0.0)


def test_preregistration_records_both_amendments_and_zero_authority() -> None:
    payload = subject.build_detector_preregistration()

    assert payload["venue"] == "deribit"
    assert "451" in payload["venue_amendment"]
    assert "eight_hour_interval" in payload["funding_settlement_amendment"]
    assert payload["liquidation_modelled"] is False
    assert payload["validated_alpha_claimed"] is False
    assert payload["paper_or_live_promotion_allowed"] is False
    assert payload["safety"]["live_authorized"] is False
    assert payload["safety"]["broker_access_performed"] is False
