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
