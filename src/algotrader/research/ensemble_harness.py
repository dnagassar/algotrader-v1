"""Frozen V5.95 regime-conditional ensemble harness.

Evaluates a component against three questions, in order: does it beat its
benchmark inside the regime it claims, is it harmless outside that regime, and
does adding it improve the ensemble under a hard drawdown ceiling. All three
are required — passing only the first is the failure mode that produces
impressive components and mediocre portfolios.

The consistency test is the specific repair the V5.94 restructure exists to
make. Consistency is measured across *occurrences of the regime*, never across
calendar periods, so a bear-regime component is judged on bear-market episodes
and is never penalized for sitting flat during states it does not claim. The
prior harness measured the opposite and therefore rejected specialists by
construction.

The harness consumes per-session return streams rather than target weights, so
components keep their own simulators and this module owns only scoring,
gating, and the ensemble objective.

This module is local and research-only. It cannot load credentials, reach a
network or broker, mutate a paper account, or authorize live capital.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from statistics import mean, stdev

from algotrader.errors import ValidationError
from algotrader.research.regime_classifier import (
    REGIME_LABELS,
    build_regime_contract,
    regime_episodes,
)

__all__ = [
    "ENSEMBLE_CONTRACT_FINGERPRINT",
    "ENSEMBLE_CONTRACT_VERSION",
    "ComponentGates",
    "EnsembleObjective",
    "build_ensemble_contract",
    "evaluate_component",
    "evaluate_ensemble",
]

ENSEMBLE_CONTRACT_VERSION = "v5_95_ensemble_contract_v1"
ENSEMBLE_CONTRACT_FINGERPRINT = "817bb394ec681d733592c75f5095a433b213a75d5cc7b78658bb6fc4a1d511ca"
_TRADING_DAYS = 252.0
_DECISION = "decision"
_STRESS = "stress"


@dataclass(frozen=True, slots=True)
class EnsembleObjective:
    """Maximize Sharpe subject to a hard drawdown ceiling."""

    maximum_drawdown_ceiling: float = 0.20
    metric: str = "annualized_sharpe_ratio"

    def __post_init__(self) -> None:
        if not (0.0 < self.maximum_drawdown_ceiling < 1.0):
            raise ValidationError("drawdown ceiling must lie in (0, 1).")
        if self.metric != "annualized_sharpe_ratio":
            raise ValidationError("only the frozen objective metric is supported.")

    def as_payload(self) -> dict[str, object]:
        return {
            "metric": self.metric,
            "maximum_drawdown_ceiling": _number(self.maximum_drawdown_ceiling),
            "constraint_is_hard": True,
            "income_maximizing": False,
        }


@dataclass(frozen=True, slots=True)
class ComponentGates:
    """Thresholds frozen by the V5.95 preregistration."""

    minimum_in_regime_sharpe_edge: float = 0.10
    minimum_stress_sharpe_edge: float = 0.0
    minimum_episode_win_rate: float = 0.60
    minimum_scoreable_episodes: int = 8
    minimum_episode_sessions: int = 10
    minimum_out_of_regime_return_drag: float = -0.005
    maximum_admitted_correlation: float = 0.70
    minimum_marginal_sharpe_improvement: float = 0.02

    def __post_init__(self) -> None:
        if not (0.0 < self.minimum_episode_win_rate <= 1.0):
            raise ValidationError("episode win rate must lie in (0, 1].")
        for name in ("minimum_scoreable_episodes", "minimum_episode_sessions"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValidationError(f"{name} must be a positive integer.")
        if not (0.0 < self.maximum_admitted_correlation <= 1.0):
            raise ValidationError("correlation ceiling must lie in (0, 1].")
        if self.minimum_out_of_regime_return_drag > 0.0:
            raise ValidationError(
                "out-of-regime drag floor must be zero or negative."
            )

    def as_payload(self) -> dict[str, object]:
        return {
            "minimum_in_regime_sharpe_edge": _number(
                self.minimum_in_regime_sharpe_edge
            ),
            "minimum_stress_sharpe_edge": _number(self.minimum_stress_sharpe_edge),
            "minimum_episode_win_rate": _number(self.minimum_episode_win_rate),
            "minimum_scoreable_episodes": self.minimum_scoreable_episodes,
            "minimum_episode_sessions": self.minimum_episode_sessions,
            "minimum_out_of_regime_return_drag": _number(
                self.minimum_out_of_regime_return_drag
            ),
            "maximum_admitted_correlation": _number(
                self.maximum_admitted_correlation
            ),
            "minimum_marginal_sharpe_improvement": _number(
                self.minimum_marginal_sharpe_improvement
            ),
            "consistency_unit": "regime_occurrence_not_calendar_period",
        }


def build_ensemble_contract(
    *,
    objective: EnsembleObjective | None = None,
    gates: ComponentGates | None = None,
) -> dict[str, object]:
    """Return the frozen ensemble contract, refusing any drift."""

    resolved_objective = objective or EnsembleObjective()
    resolved_gates = gates or ComponentGates()
    regime = build_regime_contract()
    contract: dict[str, object] = {
        "record_type": "ensemble_contract",
        "contract_version": ENSEMBLE_CONTRACT_VERSION,
        "objective": resolved_objective.as_payload(),
        "component_gates": resolved_gates.as_payload(),
        "regime_set_fingerprint": regime["regime_set_fingerprint"],
        "regime_labels": list(REGIME_LABELS),
        "evaluation_order": [
            "in_regime_skill",
            "out_of_regime_harmlessness",
            "marginal_ensemble_contribution",
        ],
        "all_gates_required": True,
        "tier_b_historical_promotion_allowed": False,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "safety": _safety(),
    }
    fingerprint = _stable_hash(contract)
    if fingerprint != ENSEMBLE_CONTRACT_FINGERPRINT:
        raise RuntimeError(f"ensemble contract drift detected: {fingerprint}")
    contract["ensemble_contract_fingerprint"] = fingerprint
    return contract


def evaluate_component(
    *,
    component_id: str,
    declared_regime: str,
    labels: Sequence[str | None],
    component_returns: Mapping[str, Sequence[float]],
    benchmark_returns: Mapping[str, Sequence[float]],
    default_returns: Sequence[float],
    admitted_in_regime_excess: Mapping[str, Sequence[float]] | None = None,
    ensemble_member_returns: Mapping[str, Sequence[float]] | None = None,
    objective: EnsembleObjective | None = None,
    gates: ComponentGates | None = None,
) -> dict[str, object]:
    """Score one component-in-regime against every frozen gate."""

    resolved_objective = objective or EnsembleObjective()
    resolved_gates = gates or ComponentGates()
    if declared_regime not in REGIME_LABELS:
        raise ValidationError(f"unknown declared regime: {declared_regime}")
    for cost_id in (_DECISION, _STRESS):
        if cost_id not in component_returns or cost_id not in benchmark_returns:
            raise ValidationError(f"missing {cost_id} return stream.")
    length = len(labels)
    for stream in (
        *component_returns.values(),
        *benchmark_returns.values(),
        default_returns,
    ):
        if len(stream) != length:
            raise ValidationError("every return stream must align with labels.")

    in_regime = [index for index, label in enumerate(labels) if label == declared_regime]
    out_regime = [
        index
        for index, label in enumerate(labels)
        if label is not None and label != declared_regime
    ]
    if not in_regime:
        raise ValidationError("declared regime never occurs in this window.")

    decision_edge = _sharpe_edge(
        component_returns[_DECISION], benchmark_returns[_DECISION], in_regime
    )
    stress_edge = _sharpe_edge(
        component_returns[_STRESS], benchmark_returns[_STRESS], in_regime
    )

    episodes = regime_episodes(
        labels, declared_regime, minimum_sessions=resolved_gates.minimum_episode_sessions
    )
    episode_rows = []
    wins = 0
    for start, end in episodes:
        span = range(start, end + 1)
        component = _compound(component_returns[_DECISION], span)
        benchmark = _compound(benchmark_returns[_DECISION], span)
        won = component > benchmark
        wins += won
        episode_rows.append(
            {
                "start_index": start,
                "end_index": end,
                "sessions": end - start + 1,
                "component_return": _number(component),
                "benchmark_return": _number(benchmark),
                "won": bool(won),
            }
        )
    win_rate = wins / len(episodes) if episodes else 0.0

    out_drag = (
        _annualized(component_returns[_DECISION], out_regime)
        - _annualized(default_returns, out_regime)
        if out_regime
        else 0.0
    )

    in_regime_excess = [
        component_returns[_DECISION][index] - benchmark_returns[_DECISION][index]
        for index in in_regime
    ]
    correlations: dict[str, str] = {}
    peak_correlation = 0.0
    for other_id, other in (admitted_in_regime_excess or {}).items():
        if len(other) != len(in_regime_excess):
            raise ValidationError(
                f"admitted excess for {other_id} does not align with this regime."
            )
        value = _pearson(in_regime_excess, other)
        if value is not None:
            correlations[other_id] = _number(value)
            peak_correlation = max(peak_correlation, abs(value))

    members = dict(ensemble_member_returns or {})
    before = _ensemble_metrics(members) if members else None
    after = _ensemble_metrics({**members, component_id: component_returns[_DECISION]})
    after_value = after["sharpe_ratio_value"]
    before_value = before["sharpe_ratio_value"] if before is not None else None
    if after_value is None or (before is not None and before_value is None):
        marginal = None
    elif before is None:
        marginal = after_value
    else:
        marginal = after_value - before_value
    feasible = after["max_drawdown_value"] <= resolved_objective.maximum_drawdown_ceiling

    conditions = {
        "in_regime_sharpe_edge_at_least_minimum": (
            decision_edge is not None
            and decision_edge >= resolved_gates.minimum_in_regime_sharpe_edge
        ),
        "stress_sharpe_edge_above_minimum": (
            stress_edge is not None
            and stress_edge > resolved_gates.minimum_stress_sharpe_edge
        ),
        "sufficient_scoreable_episodes": (
            len(episodes) >= resolved_gates.minimum_scoreable_episodes
        ),
        "episode_win_rate_at_least_minimum": (
            len(episodes) >= resolved_gates.minimum_scoreable_episodes
            and win_rate >= resolved_gates.minimum_episode_win_rate
        ),
        "out_of_regime_drag_within_floor": (
            out_drag >= resolved_gates.minimum_out_of_regime_return_drag
        ),
        "not_redundant_with_admitted_components": (
            peak_correlation <= resolved_gates.maximum_admitted_correlation
        ),
        "marginal_sharpe_improvement_at_least_minimum": (
            marginal is not None
            and marginal >= resolved_gates.minimum_marginal_sharpe_improvement
        ),
        "ensemble_drawdown_within_ceiling": feasible,
    }
    passed = all(conditions.values())
    return {
        "record_type": "component_in_regime_evaluation",
        "component_id": component_id,
        "declared_regime": declared_regime,
        "in_regime_sessions": len(in_regime),
        "out_of_regime_sessions": len(out_regime),
        "in_regime_sharpe_edge": _optional_number(decision_edge),
        "stress_sharpe_edge": _optional_number(stress_edge),
        "scoreable_episodes": len(episodes),
        "episodes_won": wins,
        "episode_win_rate": _number(win_rate),
        "episodes": episode_rows,
        "out_of_regime_annualized_drag": _number(out_drag),
        "admitted_correlations": correlations,
        "peak_admitted_correlation": _number(peak_correlation),
        "ensemble_before": before,
        "ensemble_after": after,
        "marginal_sharpe_improvement": _optional_number(marginal),
        "gate_conditions": conditions,
        "all_gates_passed": passed,
        "route": (
            "admit_component_to_ensemble"
            if passed
            else "reject_component_without_tuning"
        ),
        "consistency_unit": "regime_occurrence_not_calendar_period",
        "historical_evidence_only": True,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "safety": _safety(),
    }


def evaluate_ensemble(
    member_returns: Mapping[str, Sequence[float]],
    *,
    objective: EnsembleObjective | None = None,
) -> dict[str, object]:
    """Score the ensemble under the frozen objective and hard ceiling."""

    resolved = objective or EnsembleObjective()
    if not member_returns:
        raise ValidationError("an ensemble requires at least one member.")
    metrics = _ensemble_metrics(member_returns)
    feasible = metrics["max_drawdown_value"] <= resolved.maximum_drawdown_ceiling
    return {
        "record_type": "ensemble_evaluation",
        "objective": resolved.as_payload(),
        "member_ids": sorted(member_returns),
        "member_count": len(member_returns),
        "allocation": "equal_weight_across_members",
        "metrics": metrics,
        "drawdown_ceiling_respected": feasible,
        "feasible": feasible,
        "route": (
            "ensemble_feasible_under_objective"
            if feasible
            else "ensemble_infeasible_drawdown_ceiling_breached"
        ),
        "historical_evidence_only": True,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "safety": _safety(),
    }


def _ensemble_metrics(
    member_returns: Mapping[str, Sequence[float]],
) -> dict[str, object]:
    streams = list(member_returns.values())
    length = len(streams[0])
    if any(len(stream) != length for stream in streams):
        raise ValidationError("ensemble members must align.")
    blended = [
        math.fsum(stream[index] for stream in streams) / len(streams)
        for index in range(length)
    ]
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in blended:
        if value <= -1.0 or not math.isfinite(value):
            raise ValidationError("ensemble return is nonpositive or nonfinite.")
        equity *= 1.0 + value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, 1.0 - equity / peak)
    sharpe = _sharpe(blended, range(length))
    annualized = _annualized(blended, range(length))
    return {
        "session_count": length,
        "sharpe_ratio": _optional_number(sharpe),
        "sharpe_ratio_value": sharpe,
        "annualized_return": _number(annualized),
        "max_drawdown": _number(max_drawdown),
        "max_drawdown_value": max_drawdown,
        "total_return": _number(equity - 1.0),
    }


def _sharpe_edge(
    component: Sequence[float],
    benchmark: Sequence[float],
    indexes: Sequence[int],
) -> float | None:
    """None when either Sharpe is undefined, e.g. zero in-regime variance.

    A component with no in-regime variance has not demonstrated an edge, so the
    gate treats None as failure rather than inventing a number for it.
    """

    left = _sharpe(component, indexes)
    right = _sharpe(benchmark, indexes)
    if left is None or right is None:
        return None
    return left - right


def _sharpe(values: Sequence[float], indexes: Sequence[int]) -> float | None:
    selected = [values[index] for index in indexes]
    if len(selected) < 2:
        return None
    deviation = stdev(selected)
    if deviation <= 0.0:
        return None
    return mean(selected) / deviation * math.sqrt(_TRADING_DAYS)


def _annualized(values: Sequence[float], indexes: Sequence[int]) -> float:
    selected = [values[index] for index in indexes]
    if not selected:
        return 0.0
    log_sum = math.fsum(math.log1p(value) for value in selected)
    return math.expm1(log_sum * _TRADING_DAYS / len(selected))


def _compound(values: Sequence[float], indexes: Sequence[int]) -> float:
    total = 1.0
    for index in indexes:
        total *= 1.0 + values[index]
    return total - 1.0


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    denominator = math.sqrt(
        math.fsum(value * value for value in left_centered)
        * math.fsum(value * value for value in right_centered)
    )
    if denominator <= 0.0 or not math.isfinite(denominator):
        return None
    correlation = (
        math.fsum(x * y for x, y in zip(left_centered, right_centered, strict=True))
        / denominator
    )
    return correlation if math.isfinite(correlation) else None


def _safety() -> dict[str, object]:
    return {
        "offline_research_only": True,
        "network_access_performed": False,
        "credential_access_performed": False,
        "broker_access_performed": False,
        "paper_mutation_performed": False,
        "live_authorized": False,
        "profit_guaranteed": False,
    }


def _stable_hash(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValidationError("metric is nonfinite.")
    if abs(value) < 5e-13:
        value = 0.0
    return f"{value:.12f}"


def _optional_number(value: float | None) -> str | None:
    return None if value is None else _number(value)
