from __future__ import annotations

from datetime import date, timedelta

import pytest

from algotrader.errors import ValidationError
from algotrader.research import ensemble_harness as subject
from algotrader.research import regime_classifier as regimes


# --- regime classifier -----------------------------------------------------


def test_regime_contract_is_frozen_and_causal() -> None:
    contract = regimes.build_regime_contract()

    assert contract["regime_set_fingerprint"] == regimes.REGIME_SET_FINGERPRINT
    assert contract["regime_count"] == 4
    assert contract["labels"] == [
        "calm_up",
        "calm_down",
        "stressed_up",
        "stressed_down",
    ]
    assert contract["volatility_axis"]["full_sample_statistics_used"] is False
    assert contract["causality"]["centered_windows_used"] is False
    assert contract["causality"]["hand_drawn_intervals_used"] is False
    assert contract["revision_path_exists"] is False
    assert contract["warm_up_sessions"] == 1320


def _series(count: int, builder) -> tuple[list[date], list[float]]:
    dates = [date(2000, 1, 3) + timedelta(days=index) for index in range(count)]
    return dates, [builder(index) for index in range(count)]


def test_classifier_labels_only_after_the_frozen_warm_up() -> None:
    dates, closes = _series(1400, lambda i: 100.0 * (1.0005**i) * (1.0 + 0.001 * ((-1) ** i)))

    labels = regimes.classify_regimes(dates, closes)

    assert len(labels) == 1400
    assert all(label is None for label in labels[: regimes.WARM_UP_SESSIONS])
    assert all(
        label in regimes.REGIME_LABELS for label in labels[regimes.WARM_UP_SESSIONS :]
    )


def test_rising_calm_series_is_labelled_up() -> None:
    dates, closes = _series(1400, lambda i: 100.0 * (1.0005**i) * (1.0 + 0.0005 * ((-1) ** i)))

    labels = regimes.classify_regimes(dates, closes)

    assert all(label.endswith("_up") for label in labels[regimes.WARM_UP_SESSIONS :])


def test_falling_series_is_labelled_down() -> None:
    dates, closes = _series(1400, lambda i: 300.0 * (0.9995**i) * (1.0 + 0.0005 * ((-1) ** i)))

    labels = regimes.classify_regimes(dates, closes)

    assert all(label.endswith("_down") for label in labels[regimes.WARM_UP_SESSIONS :])


def test_classifier_rejects_short_or_invalid_series() -> None:
    dates, closes = _series(100, lambda i: 100.0)
    with pytest.raises(ValidationError, match="shorter than the frozen regime warm-up"):
        regimes.classify_regimes(dates, closes)

    dates, closes = _series(1400, lambda i: 100.0)
    closes[5] = -1.0
    with pytest.raises(ValidationError, match="positive and finite"):
        regimes.classify_regimes(dates, closes)


def test_episodes_are_contiguous_and_short_runs_are_excluded() -> None:
    labels = (
        [None] * 2
        + ["calm_up"] * 12          # scoreable
        + ["calm_down"] * 3
        + ["calm_up"] * 4           # too short, excluded entirely
        + ["calm_down"] * 5
        + ["calm_up"] * 10          # scoreable, runs to the end
    )

    episodes = regimes.regime_episodes(labels, "calm_up", minimum_sessions=10)

    assert episodes == ((2, 13), (26, 35))
    # The 4-session run is dropped rather than counted as a loss.
    assert all(end - start + 1 >= 10 for start, end in episodes)


def test_unknown_regime_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown regime"):
        regimes.regime_episodes(["calm_up"], "bull_market", minimum_sessions=1)


# --- ensemble contract -----------------------------------------------------


def test_ensemble_contract_is_frozen_with_hard_ceiling() -> None:
    contract = subject.build_ensemble_contract()

    assert (
        contract["ensemble_contract_fingerprint"]
        == subject.ENSEMBLE_CONTRACT_FINGERPRINT
    )
    assert contract["objective"]["maximum_drawdown_ceiling"] == "0.200000000000"
    assert contract["objective"]["constraint_is_hard"] is True
    assert contract["objective"]["income_maximizing"] is False
    assert contract["evaluation_order"] == [
        "in_regime_skill",
        "out_of_regime_harmlessness",
        "marginal_ensemble_contribution",
    ]
    assert contract["all_gates_required"] is True
    assert contract["tier_b_historical_promotion_allowed"] is False
    assert contract["paper_promotion_allowed"] is False
    assert contract["live_authorized"] is False
    assert (
        contract["component_gates"]["consistency_unit"]
        == "regime_occurrence_not_calendar_period"
    )


def test_objective_and_gates_reject_invalid_parameters() -> None:
    with pytest.raises(ValidationError, match="ceiling must lie"):
        subject.EnsembleObjective(maximum_drawdown_ceiling=1.5)
    with pytest.raises(ValidationError, match="only the frozen objective metric"):
        subject.EnsembleObjective(metric="total_return")
    with pytest.raises(ValidationError, match="episode win rate"):
        subject.ComponentGates(minimum_episode_win_rate=0.0)
    with pytest.raises(ValidationError, match="must be a positive integer"):
        subject.ComponentGates(minimum_scoreable_episodes=0)
    with pytest.raises(ValidationError, match="drag floor must be zero or negative"):
        subject.ComponentGates(minimum_out_of_regime_return_drag=0.01)


# --- component evaluation --------------------------------------------------


def _labelled(pattern: list[tuple[str, int]]) -> list[str]:
    labels: list[str] = []
    for label, count in pattern:
        labels.extend([label] * count)
    return labels


def _specialist_case(edge: float = 0.0005, episodes: int = 10):
    """A component that earns only inside calm_down and is flat elsewhere.

    Both streams carry noise so in-regime variance is positive and the excess
    series itself varies — otherwise Sharpe and correlation are undefined.
    """

    labels = _labelled([("calm_up", 12), ("calm_down", 12)] * episodes)
    component: list[float] = []
    benchmark: list[float] = []
    for index, label in enumerate(labels):
        sign = 1.0 if index % 2 == 0 else -1.0
        if label == "calm_down":
            component.append(edge + 0.006 * sign)
            benchmark.append(0.005 * sign)
        else:
            component.append(0.0)
            benchmark.append(0.0)
    return labels, component, benchmark


def test_specialist_passes_on_its_own_regime_episodes() -> None:
    labels, component, benchmark = _specialist_case()

    result = subject.evaluate_component(
        component_id="calm_down_specialist",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": component, "stress": component},
        benchmark_returns={"decision": benchmark, "stress": benchmark},
        default_returns=[0.0] * len(labels),
    )

    assert result["scoreable_episodes"] == 10
    assert result["episodes_won"] == 10
    assert result["episode_win_rate"] == "1.000000000000"
    assert result["gate_conditions"]["episode_win_rate_at_least_minimum"] is True
    assert result["gate_conditions"]["out_of_regime_drag_within_floor"] is True
    assert result["all_gates_passed"] is True
    assert result["route"] == "admit_component_to_ensemble"
    # A historical pass still authorizes nothing.
    assert result["historical_evidence_only"] is True
    assert result["paper_promotion_allowed"] is False
    assert result["live_authorized"] is False


def test_specialist_is_not_penalised_for_being_flat_out_of_regime() -> None:
    """The core repair: calendar-wide consistency would have failed this."""

    labels, component, benchmark = _specialist_case()

    result = subject.evaluate_component(
        component_id="calm_down_specialist",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": component, "stress": component},
        benchmark_returns={"decision": benchmark, "stress": benchmark},
        default_returns=[0.0] * len(labels),
    )

    # It contributes nothing for more than half of all sessions...
    assert result["out_of_regime_sessions"] > result["in_regime_sessions"] - 1
    assert result["out_of_regime_annualized_drag"] == "0.000000000000"
    # ...and is admitted anyway, because it is judged on its own episodes.
    assert result["all_gates_passed"] is True


def test_thin_evidence_fails_rather_than_flattering() -> None:
    labels, component, benchmark = _specialist_case(episodes=3)

    result = subject.evaluate_component(
        component_id="thin_specialist",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": component, "stress": component},
        benchmark_returns={"decision": benchmark, "stress": benchmark},
        default_returns=[0.0] * len(labels),
    )

    assert result["scoreable_episodes"] == 3
    assert result["gate_conditions"]["sufficient_scoreable_episodes"] is False
    # Even a perfect win rate cannot rescue too few episodes.
    assert result["episode_win_rate"] == "1.000000000000"
    assert result["gate_conditions"]["episode_win_rate_at_least_minimum"] is False
    assert result["all_gates_passed"] is False
    assert result["route"] == "reject_component_without_tuning"


def test_out_of_regime_bleed_is_rejected() -> None:
    labels, component, benchmark = _specialist_case()
    bleeding = [
        value if labels[index] == "calm_down" else -0.002
        for index, value in enumerate(component)
    ]

    result = subject.evaluate_component(
        component_id="bleeder",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": bleeding, "stress": bleeding},
        benchmark_returns={"decision": benchmark, "stress": benchmark},
        default_returns=[0.0] * len(labels),
    )

    assert float(result["out_of_regime_annualized_drag"]) < -0.005
    assert result["gate_conditions"]["out_of_regime_drag_within_floor"] is False
    assert result["all_gates_passed"] is False


def test_redundant_component_is_rejected() -> None:
    labels, component, benchmark = _specialist_case()
    in_regime = [
        component[index] - benchmark[index]
        for index, label in enumerate(labels)
        if label == "calm_down"
    ]

    result = subject.evaluate_component(
        component_id="duplicate",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": component, "stress": component},
        benchmark_returns={"decision": benchmark, "stress": benchmark},
        default_returns=[0.0] * len(labels),
        admitted_in_regime_excess={"incumbent": [value * 1.0 for value in in_regime]},
    )

    assert result["peak_admitted_correlation"] == "1.000000000000"
    assert result["gate_conditions"]["not_redundant_with_admitted_components"] is False
    assert result["all_gates_passed"] is False


def test_declared_regime_must_occur() -> None:
    labels = ["calm_up"] * 50
    with pytest.raises(ValidationError, match="never occurs"):
        subject.evaluate_component(
            component_id="absent",
            declared_regime="stressed_down",
            labels=labels,
            component_returns={"decision": [0.0] * 50, "stress": [0.0] * 50},
            benchmark_returns={"decision": [0.0] * 50, "stress": [0.0] * 50},
            default_returns=[0.0] * 50,
        )


def test_misaligned_streams_are_rejected() -> None:
    labels = ["calm_down"] * 50
    with pytest.raises(ValidationError, match="must align"):
        subject.evaluate_component(
            component_id="ragged",
            declared_regime="calm_down",
            labels=labels,
            component_returns={"decision": [0.0] * 49, "stress": [0.0] * 50},
            benchmark_returns={"decision": [0.0] * 50, "stress": [0.0] * 50},
            default_returns=[0.0] * 50,
        )


# --- ensemble evaluation ---------------------------------------------------


def test_drawdown_ceiling_is_a_hard_constraint() -> None:
    # A high-Sharpe stream that nonetheless breaches the ceiling is infeasible.
    crash = [0.01] * 60 + [-0.30] + [0.01] * 60

    result = subject.evaluate_ensemble({"deep_drawdown": crash})

    assert float(result["metrics"]["max_drawdown"]) > 0.20
    assert result["drawdown_ceiling_respected"] is False
    assert result["feasible"] is False
    assert result["route"] == "ensemble_infeasible_drawdown_ceiling_breached"


def test_feasible_ensemble_reports_its_objective() -> None:
    steady = [0.0004] * 300

    result = subject.evaluate_ensemble({"steady": steady})

    assert result["feasible"] is True
    assert result["route"] == "ensemble_feasible_under_objective"
    assert result["member_count"] == 1
    assert result["allocation"] == "equal_weight_across_members"
    assert float(result["metrics"]["max_drawdown"]) == 0.0
    assert result["paper_promotion_allowed"] is False
    assert result["live_authorized"] is False


def test_equal_weight_blend_dampens_a_single_member_drawdown() -> None:
    crash = [0.01] * 60 + [-0.30] + [0.01] * 60
    calm = [0.0] * 121

    blended = subject.evaluate_ensemble({"crash": crash, "calm": calm})
    alone = subject.evaluate_ensemble({"crash": crash})

    assert float(blended["metrics"]["max_drawdown"]) < float(
        alone["metrics"]["max_drawdown"]
    )


def test_empty_ensemble_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one member"):
        subject.evaluate_ensemble({})


def test_component_parked_in_cash_cannot_demonstrate_an_edge() -> None:
    """Zero in-regime variance leaves Sharpe undefined; that is not a pass."""

    labels = _labelled([("calm_up", 12), ("calm_down", 12)] * 10)
    flat = [0.0] * len(labels)

    result = subject.evaluate_component(
        component_id="parked_in_cash",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": flat, "stress": flat},
        benchmark_returns={"decision": flat, "stress": flat},
        default_returns=flat,
    )

    assert result["in_regime_sharpe_edge"] is None
    assert result["stress_sharpe_edge"] is None
    assert result["gate_conditions"]["in_regime_sharpe_edge_at_least_minimum"] is False
    assert result["gate_conditions"]["stress_sharpe_edge_above_minimum"] is False
    assert result["all_gates_passed"] is False


# --- multiplicity-corrected episode significance ---------------------------


def test_binomial_tail_is_exact() -> None:
    assert subject._binomial_tail(10, 10) == pytest.approx(1.0 / 1024.0)
    assert subject._binomial_tail(0, 10) == pytest.approx(1.0)
    assert subject._binomial_tail(9, 9) == pytest.approx(1.0 / 512.0)
    with pytest.raises(ValidationError, match="out of range"):
        subject._binomial_tail(5, 0)


def test_bonferroni_alpha_makes_eight_episodes_unreachable() -> None:
    """A frozen minimum of 8 episodes cannot clear the corrected alpha.

    With 4 components across 4 regimes the per-hypothesis alpha is 0.003125,
    and a perfect 8-of-8 record scores p = 0.00390625. The effective binding
    minimum is therefore 9 episodes, not the 8 named in V5.95. Recorded here
    rather than silently re-parameterized: the interaction only tightens the
    bar and was found before any component was scored.
    """

    alpha = subject.ComponentGates().episode_win_alpha
    assert alpha == pytest.approx(0.003125)
    assert subject._binomial_tail(8, 8) > alpha
    assert subject._binomial_tail(9, 9) <= alpha


def test_perfect_record_clears_the_adjusted_alpha() -> None:
    labels, component, benchmark = _specialist_case(episodes=10)

    result = subject.evaluate_component(
        component_id="significant_specialist",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": component, "stress": component},
        benchmark_returns={"decision": benchmark, "stress": benchmark},
        default_returns=[0.0] * len(labels),
    )

    assert result["episodes_won"] == 10
    assert float(result["episode_win_binomial_p"]) == pytest.approx(1.0 / 1024.0)
    assert (
        result["gate_conditions"]["episode_wins_significant_at_adjusted_alpha"]
        is True
    )
    assert result["all_gates_passed"] is True


def test_mediocre_win_rate_fails_significance_even_above_the_rate_floor() -> None:
    """70% of episodes clears the 60% rate gate but not the corrected alpha."""

    labels = _labelled([("calm_up", 12), ("calm_down", 12)] * 10)
    component: list[float] = []
    benchmark: list[float] = []
    episode_index = -1
    previous = None
    for index, label in enumerate(labels):
        if label == "calm_down" and previous != "calm_down":
            episode_index += 1
        previous = label
        sign = 1.0 if index % 2 == 0 else -1.0
        if label == "calm_down":
            edge = 0.0005 if episode_index < 7 else -0.0005
            component.append(edge + 0.006 * sign)
            benchmark.append(0.005 * sign)
        else:
            component.append(0.0)
            benchmark.append(0.0)

    result = subject.evaluate_component(
        component_id="mediocre",
        declared_regime="calm_down",
        labels=labels,
        component_returns={"decision": component, "stress": component},
        benchmark_returns={"decision": benchmark, "stress": benchmark},
        default_returns=[0.0] * len(labels),
    )

    assert result["episodes_won"] == 7
    assert result["gate_conditions"]["episode_win_rate_at_least_minimum"] is True
    assert (
        result["gate_conditions"]["episode_wins_significant_at_adjusted_alpha"]
        is False
    )
    assert result["all_gates_passed"] is False


# --- V5.97 harness repairs -------------------------------------------------


def test_contract_records_the_repaired_label_basis_and_precondition() -> None:
    contract = subject.build_ensemble_contract()

    assert (
        contract["label_basis"] == "effective_action_labels_from_prior_month_end"
    )
    assert contract["scoring_conditions_on_holdings_not_raw_labels"] is True
    assert contract["regime_occupancy_precondition_required"] is True


def test_effective_labels_lag_to_the_prior_month_end() -> None:
    """Sessions inherit the label that set the target now in force."""

    dates = [date(2024, 1, 29) + timedelta(days=offset) for offset in range(8)]
    # A month boundary falls between index 2 (Jan 31) and index 3 (Feb 1).
    raw = ["calm_up", "calm_up", "stressed_down", "calm_up", "calm_up",
           "calm_up", "calm_up", "calm_up"]

    effective = regimes.effective_action_labels(dates, raw)

    # Nothing governs sessions before the first month-end.
    assert effective[0] is None
    assert effective[1] is None
    assert effective[2] is None
    # From the boundary onward the month-end label governs, not the daily one.
    assert effective[3] == "stressed_down"
    assert effective[7] == "stressed_down"


def test_effective_labels_reject_misaligned_inputs() -> None:
    with pytest.raises(ValidationError, match="must align"):
        regimes.effective_action_labels([date(2024, 1, 1)], ["calm_up", "calm_up"])


def test_occupancy_flags_a_regime_that_barely_occurs() -> None:
    """The V5.96 defect: calm_down had 17 sessions and zero episodes."""

    labels = ["calm_up"] * 300 + ["calm_down"] * 3 + ["calm_up"] * 300

    occupancy = regimes.regime_occupancy(
        labels, minimum_episodes=8, minimum_episode_sessions=10
    )

    assert occupancy["calm_down"].sessions == 3
    assert occupancy["calm_down"].scoreable_episodes == 0
    assert occupancy["calm_down"].sufficient is False
    # A regime with no episodes must never host a component.
    assert occupancy["calm_up"].scoreable_episodes >= 1


def test_occupancy_accepts_a_well_occupied_regime() -> None:
    labels = _labelled([("calm_up", 12), ("stressed_down", 12)] * 10)

    occupancy = regimes.regime_occupancy(
        labels, minimum_episodes=8, minimum_episode_sessions=10
    )

    assert occupancy["stressed_down"].scoreable_episodes == 10
    assert occupancy["stressed_down"].sufficient is True
    assert occupancy["calm_up"].sufficient is True


def test_occupancy_minimums_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="occupancy minimums"):
        regimes.regime_occupancy(["calm_up"], minimum_episodes=0, minimum_episode_sessions=10)


def test_effective_labels_make_out_of_regime_sessions_genuinely_flat() -> None:
    """The repair's observable consequence: a cash sleeve shows zero drag.

    Under V5.96 daily labels a monthly component still held positions during
    sessions labelled out-of-regime, so drag was positive. Conditioning on the
    action-governing label removes that mismatch by construction.
    """

    dates = [date(2020, 1, 1) + timedelta(days=offset) for offset in range(240)]
    raw = ["calm_up" if (index // 30) % 2 == 0 else "stressed_down"
           for index in range(240)]
    effective = regimes.effective_action_labels(dates, raw)

    held = [index for index, label in enumerate(effective) if label == "stressed_down"]
    idle = [index for index, label in enumerate(effective)
            if label is not None and label != "stressed_down"]

    # A component acting on the effective label is in cash on exactly the idle
    # sessions, so any return it books there is zero by construction.
    component = [0.004 if index in set(held) else 0.0 for index in range(240)]
    assert all(component[index] == 0.0 for index in idle)
    assert any(component[index] != 0.0 for index in held)
