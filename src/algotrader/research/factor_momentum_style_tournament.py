"""Frozen V5.84 factor-momentum style-proxy tournament."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.factor_momentum_style_data_manifest import ALL_SYMBOLS, RISK_SYMBOLS
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

__all__ = ["build_factor_momentum_style_preregistration", "run_factor_momentum_style_tournament"]

PROTOCOL_ID = "v5_84_factor_momentum_style_proxy_v1"
A_ID = "style_factor_momentum_timeseries_12m"
B_ID = "style_factor_momentum_cross_section_top2_12m"
C_ID = "style_factor_momentum_ensemble_50_50"
CANDIDATE_IDS = (A_ID, B_ID, C_ID)
STATIC_ID = "static_equal_style_monthly"
RANK_ID = "rank_only_top2_12m"
SHY_ID = "shy_buy_and_hold"
SPY_ID = "spy_buy_and_hold"
PARENT_ID = "spy_ief_60_40_monthly"
_PROTOCOL = Path("docs/design/v5_84_factor_style_ensemble_preregistration.md")
_RECEIPT = Path("docs/design/v5_84_factor_style_ensemble_data_receipt.md")
_DATA = Path("runs/v5_84_factor_momentum_style_proxy/canonical_data.csv")
_DATA_MANIFEST = Path("runs/v5_84_factor_momentum_style_proxy/canonical_data_manifest.json")
_OUTPUT = Path("runs/v5_84_factor_momentum_style_proxy/evaluation")
_ENGINE = Path("src/algotrader/research/factor_momentum_style_tournament.py")
_PROTOCOL_HASH = "3ec0d6359cb4280e24a60fab8a9c04a18ac727f231fb89bd3526a9f0c4aa8361"
_RECEIPT_HASH = "dd95e69f73c59bad79f183fc620d719424de3b00c54955ca6bd6e39000b3fc4e"
_DATA_HASH = "c54d53450cd523677e9f72a7a3ba001295c738a7a388b37ff2a3d1f5bf361919"
_MANIFEST_HASH = "ee0063bbb19f6c05b593b8519a0864d2224fe93061ca674f62412c736733d790"
_START = date(2011, 5, 5)
_END = date(2026, 7, 31)
_OOS_START = date(2013, 1, 2)
_WINDOWS = (
    ("oos", _OOS_START, _END),
    ("oos_fold_1", date(2013, 1, 2), date(2016, 12, 30)),
    ("oos_fold_2", date(2017, 1, 3), date(2020, 12, 31)),
    ("oos_fold_3", date(2021, 1, 4), _END),
)
_SESSION_COUNTS = {"all": 3832, "oos": 3415, "oos_fold_1": 1008, "oos_fold_2": 1007, "oos_fold_3": 1400}
_COSTS = {"zero": 0.0, "decision": 0.0005, "stress": 0.0015}


@dataclass(frozen=True, slots=True)
class _Data:
    dates: tuple[date, ...]
    prices: Mapping[str, tuple[float, ...]]


@dataclass(frozen=True, slots=True)
class _Series:
    dates: tuple[date, ...]
    returns: tuple[float, ...]
    turnover: tuple[float, ...]
    risk_exposure: tuple[float, ...]
    weights: tuple[Mapping[str, float], ...]
    contributions: tuple[Mapping[str, float], ...]
    cost_contributions: tuple[float, ...]
    equity: tuple[float, ...]
    drawdown: tuple[float, ...]


def build_factor_momentum_style_preregistration() -> dict[str, object]:
    _validate_tracked_inputs()
    return {
        "record_type": "factor_momentum_style_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "candidate_ids": list(CANDIDATE_IDS),
        "control_ids": [STATIC_ID, RANK_ID, SHY_ID],
        "baseline_ids": [SPY_ID, PARENT_ID],
        "symbols": list(ALL_SYMBOLS),
        "oos_start": _OOS_START.isoformat(),
        "oos_end": _END.isoformat(),
        "signal_lookback_sessions": 252,
        "action_lag": "month_end_close_t_to_next_common_close_t_plus_1",
        "cost_bps_per_one_way_turnover": {key: _number(value * 10000.0) for key, value in _COSTS.items()},
        "protocol_sha256": _PROTOCOL_HASH,
        "receipt_sha256": _RECEIPT_HASH,
        "data_sha256": _DATA_HASH,
        "data_manifest_sha256": _MANIFEST_HASH,
        "parameter_search_performed": False,
        "source_metrics_used": False,
        "paper_or_live_promotion_allowed": False,
        "safety": _safety(),
    }


def run_factor_momentum_style_tournament(output_root: Path | str = _OUTPUT) -> dict[str, object]:
    preregistration = build_factor_momentum_style_preregistration()
    result_a = _canonical_replay(preregistration)
    result_b = _canonical_replay(preregistration)
    result_bytes = _json_bytes(result_a)
    if result_bytes != _json_bytes(result_b):
        raise ValidationError("canonical result replay bytes differ.")
    manifest_a = _artifact_manifest(result_a)
    manifest_b = _artifact_manifest(result_b)
    manifest_bytes = _json_bytes(manifest_a)
    if manifest_bytes != _json_bytes(manifest_b):
        raise ValidationError("canonical manifest replay bytes differ.")
    root = _local_path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "preregistration.json", preregistration)
    (root / "evaluation_results.json").write_bytes(result_bytes)
    _write_text(root / "evaluation_summary.md", _summary(result_a))
    (root / "manifest.json").write_bytes(manifest_bytes)
    completed = dict(result_a)
    completed["artifact_manifest"] = manifest_a
    completed["artifact_manifest_sha256"] = _hash(root / "manifest.json")
    return completed


def _canonical_replay(preregistration: Mapping[str, object]) -> dict[str, object]:
    data = _load_data()
    actions = _build_actions(data)
    evaluation = _evaluate(data, actions)
    return _build_result(preregistration, data, evaluation, replay_equal=True)
def _build_result(preregistration: Mapping[str, object], data: _Data, evaluation: Mapping[str, object], *, replay_equal: bool) -> dict[str, object]:
    decisions = _decisions(evaluation, replay_equal=replay_equal)
    eligible = [item for item in decisions.values() if item["all_gates_passed"]]
    ranked = sorted(eligible, key=lambda item: (
        -_float(item["selection_metrics"]["composite_sharpe_improvement"]),
        -_float(item["selection_metrics"]["candidate_sharpe"]),
        -_float(item["selection_metrics"]["candidate_annualized_return"]),
        _float(item["selection_metrics"]["candidate_max_drawdown"]),
        str(item["candidate_id"]),
    ))
    winner = str(ranked[0]["candidate_id"]) if ranked else None
    return {
        "record_type": "factor_momentum_style_tournament_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": dict(preregistration),
        "data_admission": {
            "data_sha256": _DATA_HASH,
            "manifest_sha256": _MANIFEST_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "common_session_count": len(data.dates),
            "first_session": data.dates[0].isoformat(),
            "last_session": data.dates[-1].isoformat(),
            "adjustment_semantics": "provider_split_and_dividend_adjusted_close",
        },
        "evaluation": dict(evaluation),
        "candidate_decisions": decisions,
        "tournament_decision": {
            "route": "provisional_historical_validated_alpha_candidate" if winner else "no_candidate_passed",
            "passing_candidate_count": len(ranked),
            "shadow_winner_id": winner,
            "selected_shadow_winner_count": 1 if winner else 0,
            "current_clock_no_submit_shadow_only": bool(winner),
            "paper_promotion_allowed": False,
            "live_authorized": False,
        },
        "replay_evidence": {"full_pipeline_replays": 2, "result_bytes_equal": True, "manifest_bytes_equal": True},
        "source_metric_trust": {"external_performance_trusted": False, "source_metrics_used_for_ranking_or_gates": False},
        "safety": _safety(),
    }


def _load_data() -> _Data:
    if _hash(_DATA) != _DATA_HASH:
        raise ValidationError("canonical data SHA-256 mismatch.")
    if _hash(_DATA_MANIFEST) != _MANIFEST_HASH:
        raise ValidationError("canonical data manifest SHA-256 mismatch.")
    manifest = _load_json(_DATA_MANIFEST)
    if manifest.get("symbols") != list(ALL_SYMBOLS):
        raise ValidationError("manifest symbols do not match the frozen universe.")
    if manifest.get("combined_output_sha256") != _DATA_HASH:
        raise ValidationError("manifest combined hash mismatch.")
    if manifest.get("common_session_count") != _SESSION_COUNTS["all"]:
        raise ValidationError("manifest common-session count mismatch.")
    safety = manifest.get("safety")
    if not isinstance(safety, dict) or safety.get("outcome_metrics_computed") is not False:
        raise ValidationError("manifest outcome-blind safety claim is missing.")
    by_symbol: dict[str, dict[date, float]] = {}
    for symbol in ALL_SYMBOLS:
        bars = load_local_daily_bars_csv(_DATA, symbol=symbol, as_of=_END).usable_bars
        if len(bars) != _SESSION_COUNTS["all"] or bars[0].date != _START or bars[-1].date != _END:
            raise ValidationError(f"{symbol} coverage mismatch.")
        by_symbol[symbol] = {bar.date: float(bar.adjusted_close) for bar in bars}
    dates = tuple(by_symbol[ALL_SYMBOLS[0]])
    for symbol in ALL_SYMBOLS[1:]:
        if tuple(by_symbol[symbol]) != dates:
            raise ValidationError(f"{symbol} session sequence mismatch.")
    _validate_windows(dates)
    return _Data(dates, {symbol: tuple(by_symbol[symbol][item] for item in dates) for symbol in ALL_SYMBOLS})


def _validate_windows(dates: tuple[date, ...]) -> None:
    if len(dates) != _SESSION_COUNTS["all"] or dates[0] != _START or dates[-1] != _END:
        raise ValidationError("full window mismatch.")
    for window_id, start, end in _WINDOWS:
        observed = tuple(item for item in dates if start <= item <= end)
        if len(observed) != _SESSION_COUNTS[window_id] or observed[0] != start or observed[-1] != end:
            raise ValidationError(f"{window_id} window mismatch.")
    oos = tuple(item for item in dates if _OOS_START <= item <= _END)
    folds = tuple(item for name, start, end in _WINDOWS if name != "oos" for item in dates if start <= item <= end)
    if folds != oos:
        raise ValidationError("folds do not exactly partition OOS.")


def _build_actions(data: _Data) -> dict[str, dict[date, dict[str, float]]]:
    result = {key: {} for key in (*CANDIDATE_IDS, STATIC_ID, RANK_ID, SHY_ID, SPY_ID, PARENT_ID)}
    month_ends = [index for index in range(len(data.dates) - 1) if (data.dates[index].year, data.dates[index].month) != (data.dates[index + 1].year, data.dates[index + 1].month)]
    for end_index in month_ends:
        if end_index < 252 or end_index + 1 >= len(data.dates):
            continue
        action_date = data.dates[end_index + 1]
        if not (_OOS_START <= action_date <= _END):
            continue
        momentum = {symbol: data.prices[symbol][end_index] / data.prices[symbol][end_index - 252] - 1.0 for symbol in RISK_SYMBOLS}
        eligible = [symbol for symbol in RISK_SYMBOLS if momentum[symbol] > 0.0]
        a = _empty_target()
        if eligible:
            weight = min(1.0 / len(eligible), 0.35)
            for symbol in eligible:
                a[symbol] = weight
            a["SHY"] = 1.0 - len(eligible) * weight
        else:
            a["SHY"] = 1.0
        ranked = sorted(RISK_SYMBOLS, key=lambda symbol: (-momentum[symbol], symbol))
        selected = [symbol for symbol in ranked[:2] if momentum[symbol] > 0.0]
        b = _empty_target()
        for symbol in selected:
            b[symbol] = 0.5
        b["SHY"] = 1.0 - 0.5 * len(selected)
        c = {symbol: 0.5 * a[symbol] + 0.5 * b[symbol] for symbol in ALL_SYMBOLS}
        rank = _empty_target()
        rank[ranked[0]] = 0.5
        rank[ranked[1]] = 0.5
        static = _empty_target()
        for symbol in RISK_SYMBOLS:
            static[symbol] = 1.0 / len(RISK_SYMBOLS)
        parent = _empty_target()
        parent["SPY"] = 0.6
        parent["IEF"] = 0.4
        for strategy_id, target in ((A_ID, a), (B_ID, b), (C_ID, c), (RANK_ID, rank), (STATIC_ID, static), (PARENT_ID, parent)):
            _validate_weights(target)
            result[strategy_id][action_date] = target
    if not result[A_ID] or min(result[A_ID]) != _OOS_START:
        raise ValidationError("warm-up did not produce the exact first OOS action.")
    result[SHY_ID][_OOS_START] = {**_empty_target(), "SHY": 1.0}
    result[SPY_ID][_OOS_START] = {**_empty_target(), "SPY": 1.0}
    return result


def _evaluate(data: _Data, actions: Mapping[str, Mapping[date, Mapping[str, float]]]) -> dict[str, object]:
    series = {
        strategy_id: {cost_id: _simulate(data, strategy_actions, rate) for cost_id, rate in _COSTS.items()}
        for strategy_id, strategy_actions in actions.items()
    }
    comparator_ids = (STATIC_ID, RANK_ID, SHY_ID, SPY_ID, PARENT_ID)
    comparators = {
        strategy_id: {cost_id: _window_metrics(value) for cost_id, value in costs.items()}
        for strategy_id, costs in series.items() if strategy_id in comparator_ids
    }
    candidates: dict[str, object] = {}
    for candidate_id in CANDIDATE_IDS:
        candidate_costs = {cost_id: _window_metrics(value) for cost_id, value in series[candidate_id].items()}
        composites: dict[str, object] = {}
        for cost_id, rate in _COSTS.items():
            composite_actions = _blend_actions(actions[PARENT_ID], actions[candidate_id], 0.8, 0.2)
            metrics = _window_metrics(_simulate(data, composite_actions, rate))
            composites[cost_id] = {
                "metrics": metrics,
                "comparison_to_parent": {window: _compare(metrics[window], comparators[PARENT_ID][cost_id][window]) for window, _, _ in _WINDOWS},
            }
        action_dates = tuple(sorted(actions[candidate_id]))
        candidates[candidate_id] = {
            "cost_metrics": candidate_costs,
            "decision_cost_comparisons": {
                comparator_id: {window: _compare(candidate_costs["decision"][window], comparators[comparator_id]["decision"][window]) for window, _, _ in _WINDOWS}
                for comparator_id in (STATIC_ID, RANK_ID, SPY_ID)
            },
            "portfolio_composite": {
                "construction": "80pct_actual_monthly_spy_ief_60_40_plus_20pct_actual_candidate_targets",
                "cost_metrics": composites,
            },
            "target_contract": {
                "monthly_action_count": len(action_dates),
                "first_action_date": action_dates[0].isoformat(),
                "last_action_date": action_dates[-1].isoformat(),
                "max_target_weight": _number(max(weight for target in actions[candidate_id].values() for weight in target.values())),
                "divergent_decisions_from_static": _divergence(actions[candidate_id], actions[STATIC_ID]),
                "divergent_decisions_from_rank_only": _divergence(actions[candidate_id], actions[RANK_ID]),
                "divergent_decisions_from_a": _divergence(actions[candidate_id], actions[A_ID]),
                "divergent_decisions_from_b": _divergence(actions[candidate_id], actions[B_ID]),
            },
        }
    integrity = {
        "chronological_action_lag_verified": True,
        "first_oos_initial_transition_turnover_is_one": all(math.isclose(series[candidate_id]["decision"].turnover[0], 1.0, abs_tol=1e-12) for candidate_id in CANDIDATE_IDS),
        "weight_sums_and_nonnegative_constraints_verified": True,
        "a_risk_cap_at_most_0_35": max(target[symbol] for target in actions[A_ID].values() for symbol in RISK_SYMBOLS) <= 0.35 + 1e-12,
        "b_selected_weight_at_most_0_50": max(target[symbol] for target in actions[B_ID].values() for symbol in RISK_SYMBOLS) <= 0.5 + 1e-12,
        "folds_slice_one_continuous_path": True,
        "data_hash_identities_verified": True,
        "nonpositive_equity_absent": True,
    }
    return {
        "candidates": candidates,
        "comparators": comparators,
        "integrity": integrity,
        "cost_models": {key: {"bps_per_one_way_turnover": _number(value * 10000.0), "source_claim": False} for key, value in _COSTS.items()},
        "parameter_search_performed": False,
        "source_metrics_used": False,
    }


def _simulate(data: _Data, actions: Mapping[date, Mapping[str, float]], cost_rate: float) -> _Series:
    positions = {symbol: 0.0 for symbol in ALL_SYMBOLS}
    dates = tuple(item for item in data.dates if _OOS_START <= item <= _END)
    index_by_date = {item: index for index, item in enumerate(data.dates)}
    returns: list[float] = []
    turnovers: list[float] = []
    exposures: list[float] = []
    weights: list[Mapping[str, float]] = []
    contributions: list[Mapping[str, float]] = []
    cost_contributions: list[float] = []
    equities: list[float] = []
    drawdowns: list[float] = []
    equity = 1.0
    peak = 1.0
    for item in dates:
        index = index_by_date[item]
        earning_positions = dict(positions)
        asset_returns = {symbol: data.prices[symbol][index] / data.prices[symbol][index - 1] - 1.0 for symbol in ALL_SYMBOLS}
        interval_contributions = {symbol: earning_positions[symbol] * asset_returns[symbol] for symbol in ALL_SYMBOLS}
        gross = sum(interval_contributions.values())
        if gross <= -1.0:
            raise ValidationError("portfolio equity became nonpositive before action.")
        drifted = {symbol: positions[symbol] * (1.0 + asset_returns[symbol]) / (1.0 + gross) for symbol in ALL_SYMBOLS}
        turnover = 0.0
        if item in actions:
            target = {symbol: float(actions[item].get(symbol, 0.0)) for symbol in ALL_SYMBOLS}
            _validate_weights(target)
            prior_cash = 1.0 - sum(drifted.values())
            target_cash = 1.0 - sum(target.values())
            turnover = 0.5 * (sum(abs(target[symbol] - drifted[symbol]) for symbol in ALL_SYMBOLS) + abs(target_cash - prior_cash))
            positions = target
        else:
            positions = drifted
        cost_contribution = -turnover * cost_rate * (1.0 + gross)
        net = gross + cost_contribution
        if net <= -1.0 or not math.isfinite(net):
            raise ValidationError("portfolio equity became nonpositive or nonfinite.")
        equity *= 1.0 + net
        peak = max(peak, equity)
        drawdown = 1.0 - equity / peak
        returns.append(net)
        turnovers.append(turnover)
        exposures.append(sum(earning_positions[symbol] for symbol in RISK_SYMBOLS))
        weights.append(earning_positions)
        contributions.append(interval_contributions)
        cost_contributions.append(cost_contribution)
        equities.append(equity)
        drawdowns.append(drawdown)
    return _Series(dates, tuple(returns), tuple(turnovers), tuple(exposures), tuple(weights), tuple(contributions), tuple(cost_contributions), tuple(equities), tuple(drawdowns))


def _window_metrics(series: _Series) -> dict[str, object]:
    return {window: _metrics(series, window, start, end) for window, start, end in _WINDOWS}


def _metrics(series: _Series, window: str, start: date, end: date) -> dict[str, object]:
    indexes = [index for index, item in enumerate(series.dates) if start <= item <= end]
    if len(indexes) != _SESSION_COUNTS[window]:
        raise ValidationError(f"{window} metric session count mismatch.")
    values = [series.returns[index] for index in indexes]
    log_return = sum(math.log1p(value) for value in values)
    total_return = math.exp(log_return) - 1.0
    annualized_return = math.exp(log_return * 252.0 / len(values)) - 1.0
    volatility = stdev(values) * math.sqrt(252.0) if len(values) > 1 else 0.0
    sharpe = mean(values) / stdev(values) * math.sqrt(252.0) if len(values) > 1 and stdev(values) > 0.0 else None
    held = [symbol for symbol in ALL_SYMBOLS if any(series.weights[index][symbol] > 1e-12 for index in indexes)]
    start_equity = 1.0 if indexes[0] == 0 else series.equity[indexes[0] - 1]
    def scaled(index: int, component: float) -> float:
        prior_equity = 1.0 if index == 0 else series.equity[index - 1]
        return prior_equity / start_equity * component
    asset_contributions = {
        symbol: sum(scaled(index, series.contributions[index][symbol]) for index in indexes)
        for symbol in ALL_SYMBOLS
    }
    cost_contribution = sum(scaled(index, series.cost_contributions[index]) for index in indexes)
    reconciliation_error = sum(asset_contributions.values()) + cost_contribution - total_return
    if not math.isclose(reconciliation_error, 0.0, abs_tol=1e-10):
        raise ValidationError(f"{window} contribution reconciliation failed.")
    average_weights = {symbol: sum(series.weights[index][symbol] for index in indexes) / len(indexes) for symbol in ALL_SYMBOLS}
    return {
        "window_id": window,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "session_count": len(indexes),
        "total_return": _number(total_return),
        "annualized_return": _number(annualized_return),
        "annualized_volatility": _number(volatility),
        "sharpe_ratio": _optional_number(sharpe),
        "max_drawdown": _number(max(series.drawdown[index] for index in indexes)),
        "annualized_one_way_turnover": _number(sum(series.turnover[index] for index in indexes) * 252.0 / len(indexes)),
        "risk_asset_invested_fraction": _number(sum(series.risk_exposure[index] > 1e-12 for index in indexes) / len(indexes)),
        "average_risk_asset_weight": _number(sum(series.risk_exposure[index] for index in indexes) / len(indexes)),
        "symbols_held": held,
        "average_asset_weight": {symbol: _number(value) for symbol, value in average_weights.items()},
        "constituent_contributions": {symbol: _number(value) for symbol, value in asset_contributions.items()},
        "transaction_cost_contribution": _number(cost_contribution),
        "contribution_reconciliation_error": _number(reconciliation_error),
        "compounded_log_return": _number(log_return),
    }


def _blend_actions(left: Mapping[date, Mapping[str, float]], right: Mapping[date, Mapping[str, float]], left_weight: float, right_weight: float) -> dict[date, dict[str, float]]:
    if tuple(sorted(left)) != tuple(sorted(right)):
        raise ValidationError("composite action dates are not identical.")
    result = {item: {symbol: left_weight * left[item][symbol] + right_weight * right[item][symbol] for symbol in ALL_SYMBOLS} for item in sorted(left)}
    for target in result.values():
        _validate_weights(target)
    return result


def _divergence(left: Mapping[date, Mapping[str, float]], right: Mapping[date, Mapping[str, float]]) -> int:
    if tuple(sorted(left)) != tuple(sorted(right)):
        raise ValidationError("target paths are not date-aligned.")
    return sum(any(not math.isclose(left[item][symbol], right[item][symbol], abs_tol=1e-12) for symbol in ALL_SYMBOLS) for item in left)


def _compare(candidate: Mapping[str, object], baseline: Mapping[str, object]) -> dict[str, object]:
    left = _optional_float(candidate["sharpe_ratio"])
    right = _optional_float(baseline["sharpe_ratio"])
    return {
        "total_return_delta": _number(_float(candidate["total_return"]) - _float(baseline["total_return"])),
        "annualized_return_delta": _number(_float(candidate["annualized_return"]) - _float(baseline["annualized_return"])),
        "sharpe_ratio_delta": _optional_number(None if left is None or right is None else left - right),
        "max_drawdown_delta": _number(_float(candidate["max_drawdown"]) - _float(baseline["max_drawdown"])),
        "max_drawdown_improvement": _number(_float(baseline["max_drawdown"]) - _float(candidate["max_drawdown"])),
    }


def _empty_target() -> dict[str, float]:
    return {symbol: 0.0 for symbol in ALL_SYMBOLS}


def _validate_weights(weights: Mapping[str, float]) -> None:
    if set(weights) != set(ALL_SYMBOLS):
        raise ValidationError("target symbols differ from the frozen universe.")
    if any(not math.isfinite(value) or value < -1e-12 or value > 1.0 + 1e-12 for value in weights.values()):
        raise ValidationError("target weights are invalid.")
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-12):
        raise ValidationError("target weights must sum to one.")


def _decisions(evaluation: Mapping[str, object], *, replay_equal: bool) -> dict[str, dict[str, object]]:
    candidates = evaluation["candidates"]
    comparators = evaluation["comparators"]
    integrity = evaluation["integrity"]
    result: dict[str, dict[str, object]] = {}
    for candidate_id in CANDIDATE_IDS:
        item = candidates[candidate_id]
        decision = item["cost_metrics"]["decision"]
        stress = item["cost_metrics"]["stress"]
        oos = decision["oos"]
        folds = [decision[f"oos_fold_{index}"] for index in range(1, 4)]
        full_log = _float(oos["compounded_log_return"])
        fold_shares = [_float(fold["compounded_log_return"]) / full_log for fold in folds] if full_log > 0.0 else []
        common = {
            "full_annualized_return_positive": _float(oos["annualized_return"]) > 0.0,
            "full_sharpe_at_least_0_60": _required_float(oos["sharpe_ratio"]) >= 0.60,
            "full_max_drawdown_at_most_0_30": _float(oos["max_drawdown"]) <= 0.30,
            "every_fold_total_return_positive": all(_float(fold["total_return"]) > 0.0 for fold in folds),
            "stress_annualized_return_positive": _float(stress["oos"]["annualized_return"]) > 0.0,
            "stress_sharpe_at_least_0_50": _required_float(stress["oos"]["sharpe_ratio"]) >= 0.50,
            "max_fold_positive_log_return_share_at_most_0_70": bool(fold_shares) and max(fold_shares) <= 0.70,
            "all_risk_style_proxies_held": all(symbol in oos["symbols_held"] for symbol in RISK_SYMBOLS),
            "chronology_cost_weight_hash_and_replay_integrity": all(bool(value) for value in integrity.values()) and replay_equal,
        }
        static = item["decision_cost_comparisons"][STATIC_ID]
        style = {
            "sharpe_exceeds_static_by_0_05": _required_float(static["oos"]["sharpe_ratio_delta"]) >= 0.05,
            "drawdown_no_more_than_0_02_worse": _float(static["oos"]["max_drawdown_delta"]) <= 0.02,
            "at_least_two_fold_sharpe_wins": sum(_required_float(static[f"oos_fold_{index}"]["sharpe_ratio_delta"]) > 0.0 for index in range(1, 4)) >= 2,
        }
        spy_comparison = item["decision_cost_comparisons"][SPY_ID]["oos"]
        spy_metrics = comparators[SPY_ID]["decision"]["oos"]
        candidate_ann = _float(oos["annualized_return"])
        candidate_sharpe = _required_float(oos["sharpe_ratio"])
        candidate_dd = _float(oos["max_drawdown"])
        defensive = {
            "annualized_return_no_more_than_0_01_below_spy": candidate_ann >= _float(spy_metrics["annualized_return"]) - 0.01,
            "sharpe_exceeds_spy_by_0_10": _required_float(spy_comparison["sharpe_ratio_delta"]) >= 0.10,
            "drawdown_at_least_20pct_smaller": candidate_dd <= 0.8 * _float(spy_metrics["max_drawdown"]),
        }
        growth = {
            "annualized_return_exceeds_spy_by_0_01": candidate_ann >= _float(spy_metrics["annualized_return"]) + 0.01,
            "sharpe_not_below_spy": candidate_sharpe >= _required_float(spy_metrics["sharpe_ratio"]),
            "drawdown_no_more_than_0_02_worse": candidate_dd <= _float(spy_metrics["max_drawdown"]) + 0.02,
        }
        distinct = {"passed": True, "conditions": {"candidate_specific_distinctness": True}}
        if candidate_id == B_ID:
            rank = item["decision_cost_comparisons"][RANK_ID]["oos"]
            rank_drawdown = _float(comparators[RANK_ID]["decision"]["oos"]["max_drawdown"])
            b_conditions = {
                "diverges_from_rank_only": item["target_contract"]["divergent_decisions_from_rank_only"] > 0,
                "sharpe_or_drawdown_rule_value": _required_float(rank["sharpe_ratio_delta"]) >= 0.03 or (_float(rank["max_drawdown_improvement"]) >= 0.05 * rank_drawdown and _float(rank["annualized_return_delta"]) >= -0.01),
            }
            distinct = {"passed": all(b_conditions.values()), "conditions": b_conditions}
        elif candidate_id == C_ID:
            c_conditions = {
                "at_least_12_divergent_decisions_from_a": item["target_contract"]["divergent_decisions_from_a"] >= 12,
                "at_least_12_divergent_decisions_from_b": item["target_contract"]["divergent_decisions_from_b"] >= 12,
            }
            distinct = {"passed": all(c_conditions.values()), "conditions": c_conditions}
        composite = item["portfolio_composite"]["cost_metrics"]
        decision_comp = composite["decision"]["comparison_to_parent"]
        stress_comp = composite["stress"]["comparison_to_parent"]
        full_improvement = _float(composite["decision"]["metrics"]["oos"]["compounded_log_return"]) - _float(comparators[PARENT_ID]["decision"]["oos"]["compounded_log_return"])
        fold_improvements = [
            _float(composite["decision"]["metrics"][f"oos_fold_{index}"]["compounded_log_return"]) - _float(comparators[PARENT_ID]["decision"][f"oos_fold_{index}"]["compounded_log_return"])
            for index in range(1, 4)
        ]
        portfolio_conditions = {
            "full_sharpe_improves_by_0_02": _required_float(decision_comp["oos"]["sharpe_ratio_delta"]) >= 0.02,
            "annualized_return_reduction_at_most_0_0075": _float(decision_comp["oos"]["annualized_return_delta"]) >= -0.0075,
            "drawdown_or_return_improves_by_0_005": _float(decision_comp["oos"]["max_drawdown_improvement"]) >= 0.005 or _float(decision_comp["oos"]["annualized_return_delta"]) >= 0.005,
            "positive_sharpe_improvement_in_two_folds": sum(_required_float(decision_comp[f"oos_fold_{index}"]["sharpe_ratio_delta"]) > 0.0 for index in range(1, 4)) >= 2,
            "fold_3_sharpe_improvement_nonnegative": _required_float(decision_comp["oos_fold_3"]["sharpe_ratio_delta"]) >= 0.0,
            "stress_full_sharpe_improvement_nonnegative": _required_float(stress_comp["oos"]["sharpe_ratio_delta"]) >= 0.0,
            "positive_log_improvement_not_fold_concentrated": full_improvement > 0.0 and max(fold_improvements) / full_improvement <= 0.70,
        }
        gates = {
            "common": {"passed": all(common.values()), "conditions": common, "max_fold_log_share": _optional_number(max(fold_shares) if fold_shares else None)},
            "style_baseline": {"passed": all(style.values()), "conditions": style},
            "spy_value_route": {"passed": all(defensive.values()) or all(growth.values()), "defensive_conditions": defensive, "growth_conditions": growth},
            "candidate_distinctness": distinct,
            "portfolio_level_value": {"passed": all(portfolio_conditions.values()), "conditions": portfolio_conditions, "full_log_return_improvement": _number(full_improvement)},
        }
        passed = all(bool(gate["passed"]) for gate in gates.values())
        result[candidate_id] = {
            "candidate_id": candidate_id,
            "all_gates_passed": passed,
            "route": "provisional_historical_validated_alpha_candidate" if passed else "close_candidate_without_tuning",
            "gates": gates,
            "selection_metrics": {
                "composite_sharpe_improvement": decision_comp["oos"]["sharpe_ratio_delta"],
                "candidate_sharpe": oos["sharpe_ratio"],
                "candidate_annualized_return": oos["annualized_return"],
                "candidate_max_drawdown": oos["max_drawdown"],
            },
            "current_clock_no_submit_shadow_eligible": passed,
            "paper_promotion_allowed": False,
            "live_authorized": False,
        }
    return result


def _artifact_manifest(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": "factor_momentum_style_artifact_manifest",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "inputs": {
            "protocol_sha256": _PROTOCOL_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "data_sha256": _DATA_HASH,
            "data_manifest_sha256": _MANIFEST_HASH,
            "engine_sha256": _hash(_ENGINE),
        },
        "evaluation_result_sha256": hashlib.sha256(_json_bytes(result)).hexdigest(),
        "result_bytes_equal": True,
        "manifest_bytes_equal": True,
        "safety": _safety(),
    }


def _summary(result: Mapping[str, object]) -> str:
    lines = ["# V5.84 factor-momentum style tournament result", "", f"Route: `{result['tournament_decision']['route']}`", ""]
    for candidate_id in CANDIDATE_IDS:
        decision = result["candidate_decisions"][candidate_id]
        metrics = result["evaluation"]["candidates"][candidate_id]["cost_metrics"]["decision"]["oos"]
        lines.extend([
            f"## {candidate_id}", "",
            f"- Passed every gate: `{str(decision['all_gates_passed']).lower()}`",
            f"- Annualized return: `{metrics['annualized_return']}`",
            f"- Sharpe: `{metrics['sharpe_ratio']}`",
            f"- Maximum drawdown: `{metrics['max_drawdown']}`",
        ])
        for gate_id, gate in decision["gates"].items():
            lines.append(f"- `{gate_id}`: `{str(gate['passed']).lower()}`")
        lines.append("")
    lines.extend([
        "No external performance metric controlled a gate or ranking. A pass is only",
        "eligible for a new current-clock no-submit shadow; paper and live remain forbidden.",
        "",
    ])
    return "\n".join(lines)


def _validate_tracked_inputs() -> None:
    if _hash(_PROTOCOL) != _PROTOCOL_HASH:
        raise ValidationError("protocol SHA-256 mismatch.")
    if _hash(_RECEIPT) != _RECEIPT_HASH:
        raise ValidationError("data receipt SHA-256 mismatch.")


def _safety() -> dict[str, object]:
    return {
        "offline_research_only": True,
        "network_access_performed_by_engine": False,
        "credential_access_performed_by_engine": False,
        "broker_access_performed": False,
        "paper_mutation_performed": False,
        "paper_authorized": False,
        "live_authorized": False,
        "live_activity_performed": False,
        "source_metrics_used": False,
        "profit_guaranteed": False,
    }


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON payload must be an object: {path}")
    return payload


def _hash(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_path(value: Path | str) -> Path:
    path = Path(value)
    if path.is_absolute() or (path.parts and path.parts[0].lower() == "runs"):
        return path
    raise ValidationError("output root must be absolute or beneath runs/.")


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.write_bytes(_json_bytes(value))


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValidationError("metric is nonfinite.")
    if abs(value) < 5e-13:
        value = 0.0
    return f"{value:.12f}"


def _optional_number(value: float | None) -> str | None:
    return None if value is None else _number(value)


def _float(value: object) -> float:
    parsed = float(str(value))
    if not math.isfinite(parsed):
        raise ValidationError("metric is nonfinite.")
    return parsed


def _optional_float(value: object) -> float | None:
    return None if value is None else _float(value)


def _required_float(value: object) -> float:
    return float("-inf") if value is None else _float(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(_OUTPUT))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_factor_momentum_style_tournament(args.output_root)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"factor_momentum_style_tournament_status=blocked:{exc}")
        return 2
    print("factor_momentum_style_tournament_status=completed")
    print(f"route={result['tournament_decision']['route']}")
    print(f"shadow_winner_id={result['tournament_decision']['shadow_winner_id']}")
    print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
