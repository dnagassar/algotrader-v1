"""Frozen V5.72 primary-source alpha-candidate tournament."""

from __future__ import annotations

import argparse
from collections import Counter
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
from algotrader.research.local_daily_bars import load_local_daily_bars_csv
from algotrader.research.primary_source_alpha_data_manifest import (
    ALL_SYMBOLS,
    CORE_SYMBOLS,
    SECTOR_SYMBOLS,
)

__all__ = [
    "build_primary_source_alpha_preregistration",
    "run_primary_source_alpha_tournament",
]

PROTOCOL_ID = "v5_72_primary_source_alpha_tournament_v1"
TURN_ID = "spy_turn_of_month_last_plus_first_three"
SECTOR_ID = "nine_sector_long_only_industry_momentum_6x6_proxy"

_PROTOCOL = Path("docs/design/v5_72_primary_source_alpha_tournament_preregistration.md")
_RECEIPT = Path("docs/design/v5_72_primary_source_alpha_tournament_data_receipt.md")
_DATA = Path("runs/v5_72_primary_source_alpha_tournament/canonical_data.csv")
_DATA_MANIFEST = Path(
    "runs/v5_72_primary_source_alpha_tournament/canonical_data_manifest.json"
)
_OUTPUT = Path("runs/v5_72_primary_source_alpha_tournament/evaluation")
_ENGINE = Path("src/algotrader/research/primary_source_alpha_tournament.py")

_PROTOCOL_HASH = "eb3061e74f5444746d19480fc9283f3189b86ebb395369e9ee19a33f3dd8d768"
_RECEIPT_HASH = "827ed0bdeece4bb373eb29517c2c0cf1dd383a89f64be958d1cf1357e22c807c"
_DATA_HASH = "5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2"
_MANIFEST_HASH = "82c1edc7192b9f63b057a4846a0d0540958d9939f6dbabddd793899ca797f0ab"
_START = date(2004, 11, 18)
_END = date(2026, 7, 31)
_OOS_START = date(2009, 1, 2)
_OOS_END = _END
_WINDOWS = (
    ("oos", _OOS_START, _OOS_END),
    ("oos_fold_1", date(2009, 1, 2), date(2014, 12, 31)),
    ("oos_fold_2", date(2015, 1, 2), date(2020, 12, 31)),
    ("oos_fold_3", date(2021, 1, 4), _OOS_END),
)
_RECENT = ("recent_2024", date(2024, 1, 2), _OOS_END)
_SESSION_COUNTS = {
    "all": 5458,
    "oos": 4421,
    "oos_fold_1": 1510,
    "oos_fold_2": 1511,
    "oos_fold_3": 1400,
    "recent_2024": 647,
}
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
    exposure: tuple[float, ...]
    weights: tuple[Mapping[str, float], ...]
    contributions: tuple[Mapping[str, float], ...]


def build_primary_source_alpha_preregistration() -> dict[str, object]:
    """Return the frozen tracked contract without reading generated data."""

    _validate_tracked_inputs()
    return {
        "record_type": "primary_source_alpha_tournament_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "candidate_ids": [TURN_ID, SECTOR_ID],
        "candidate_labels": {
            TURN_ID: "repository_proxy_not_crsp_index_replication",
            SECTOR_ID: "repository_proxy_not_moskowitz_grinblatt_replication",
        },
        "symbols": list(ALL_SYMBOLS),
        "oos_start": _OOS_START.isoformat(),
        "oos_end": _OOS_END.isoformat(),
        "cost_bps_per_one_way_turnover": {
            name: _number(rate * 10000.0) for name, rate in _COSTS.items()
        },
        "protocol_sha256": _PROTOCOL_HASH,
        "receipt_sha256": _RECEIPT_HASH,
        "data_sha256": _DATA_HASH,
        "data_manifest_sha256": _MANIFEST_HASH,
        "parameter_search_performed": False,
        "source_metrics_used": False,
        "validated_alpha_means_shadow_eligible_only": True,
        "paper_or_live_promotion_allowed": False,
        "safety": _safety(),
    }


def run_primary_source_alpha_tournament(
    output_root: Path | str = _OUTPUT,
) -> dict[str, object]:
    """Run the exact frozen tournament and write deterministic artifacts."""

    preregistration = build_primary_source_alpha_preregistration()
    data = _load_data()
    turn_actions, turn_targets = _turn_of_month_actions(data.dates)
    sector_actions = _sector_momentum_actions(data)
    first = _evaluate(data, turn_actions, turn_targets, sector_actions)
    second = _evaluate(data, turn_actions, turn_targets, sector_actions)
    if _json_bytes(first) != _json_bytes(second):
        raise ValidationError("independent in-memory replay was not byte-identical.")
    decisions = _decisions(first)
    accepted = [item for item in decisions.values() if item["all_gates_passed"]]
    result: dict[str, object] = {
        "record_type": "primary_source_alpha_tournament_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": preregistration,
        "data_admission": {
            "data_sha256": _DATA_HASH,
            "manifest_sha256": _MANIFEST_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "common_session_count": len(data.dates),
            "first_session": data.dates[0].isoformat(),
            "last_session": data.dates[-1].isoformat(),
            "adjustment_semantics": "provider_split_and_dividend_adjusted_close",
        },
        "evaluation": first,
        "candidate_decisions": decisions,
        "tournament_decision": {
            "route": "alpha_candidates_found" if accepted else "no_candidate_passed",
            "validated_alpha_candidate_count": len(accepted),
            "validated_alpha_candidate_ids": [
                item["candidate_id"] for item in accepted
            ],
            "paper_promotion_allowed": False,
            "live_authorized": False,
        },
        "source_metric_trust": {
            "external_performance_trusted": False,
            "source_metrics_used_for_ranking_or_gates": False,
        },
        "safety": _safety(),
    }
    root = _local_path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    prereg_path = root / "preregistration.json"
    result_path = root / "evaluation_results.json"
    summary_path = root / "evaluation_summary.md"
    _write_json(prereg_path, preregistration)
    _write_json(result_path, result)
    _write_text(summary_path, _summary(result))
    manifest = {
        "record_type": "primary_source_alpha_tournament_artifact_manifest",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "inputs": {
            "protocol_sha256": _PROTOCOL_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "data_sha256": _DATA_HASH,
            "data_manifest_sha256": _MANIFEST_HASH,
            "engine_sha256": _hash(_ENGINE),
        },
        "artifacts": [_artifact(path) for path in (prereg_path, result_path, summary_path)],
        "safety": _safety(),
    }
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)
    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_sha256"] = _hash(manifest_path)
    return completed


def _load_data() -> _Data:
    if _hash(_DATA) != _DATA_HASH:
        raise ValidationError("canonical data SHA-256 mismatch.")
    if _hash(_DATA_MANIFEST) != _MANIFEST_HASH:
        raise ValidationError("canonical data manifest SHA-256 mismatch.")
    manifest = _load_json(_DATA_MANIFEST)
    if manifest.get("symbols") != list(ALL_SYMBOLS):
        raise ValidationError("manifest symbols do not match the frozen universe.")
    if manifest.get("combined_output_sha256") != _DATA_HASH:
        raise ValidationError("manifest combined hash does not match the frozen data.")
    if manifest.get("common_session_count") != _SESSION_COUNTS["all"]:
        raise ValidationError("manifest common-session count mismatch.")
    safety = manifest.get("safety")
    if not isinstance(safety, dict) or safety.get("outcome_metrics_computed") is not False:
        raise ValidationError("manifest outcome-blind safety claim is missing.")

    by_symbol: dict[str, dict[date, float]] = {}
    for symbol in ALL_SYMBOLS:
        result = load_local_daily_bars_csv(_DATA, symbol=symbol, as_of=_END)
        bars = result.usable_bars
        if len(bars) != _SESSION_COUNTS["all"]:
            raise ValidationError(f"{symbol} row count mismatch.")
        if bars[0].date != _START or bars[-1].date != _END:
            raise ValidationError(f"{symbol} coverage mismatch.")
        by_symbol[symbol] = {bar.date: float(bar.adjusted_close) for bar in bars}
    dates = tuple(by_symbol[ALL_SYMBOLS[0]])
    if dates != tuple(sorted(dates)):
        raise ValidationError("canonical sessions are not increasing.")
    for symbol in ALL_SYMBOLS[1:]:
        if tuple(by_symbol[symbol]) != dates:
            raise ValidationError(f"{symbol} session sequence mismatch.")
    _validate_windows(dates)
    return _Data(
        dates=dates,
        prices={symbol: tuple(by_symbol[symbol][item] for item in dates) for symbol in ALL_SYMBOLS},
    )


def _validate_windows(dates: tuple[date, ...]) -> None:
    for window_id, start, end in (*_WINDOWS, _RECENT):
        observed = tuple(item for item in dates if start <= item <= end)
        if len(observed) != _SESSION_COUNTS[window_id]:
            raise ValidationError(f"{window_id} session count mismatch.")
        if observed[0] != start or observed[-1] != end:
            raise ValidationError(f"{window_id} endpoints mismatch.")
    oos = tuple(item for item in dates if _OOS_START <= item <= _OOS_END)
    folds = tuple(
        item
        for window_id, start, end in _WINDOWS
        if window_id.startswith("oos_fold_")
        for item in dates
        if start <= item <= end
    )
    if folds != oos:
        raise ValidationError("OOS folds do not exactly partition OOS.")


def _turn_of_month_actions(
    dates: tuple[date, ...],
) -> tuple[dict[date, dict[str, float]], dict[date, dict[str, float]]]:
    month_dates: dict[tuple[int, int], list[date]] = {}
    for item in dates:
        month_dates.setdefault((item.year, item.month), []).append(item)
    invested = {values[-1] for values in month_dates.values()}
    for values in month_dates.values():
        invested.update(values[:3])
    targets: dict[date, dict[str, float]] = {}
    actions: dict[date, dict[str, float]] = {}
    prior = -1.0
    for item in dates[1:]:
        exposure = 1.0 if item in invested else 0.0
        target = {symbol: (exposure if symbol == "SPY" else 0.0) for symbol in ALL_SYMBOLS}
        targets[item] = target
        if exposure != prior:
            actions[item] = target
            prior = exposure
    return actions, targets


def _sector_momentum_actions(data: _Data) -> dict[date, dict[str, float]]:
    month_end_indexes = [
        index
        for index, item in enumerate(data.dates)
        if index == len(data.dates) - 1
        or (data.dates[index + 1].year, data.dates[index + 1].month)
        != (item.year, item.month)
    ]
    cohorts: list[tuple[str, str, str]] = []
    actions: dict[date, dict[str, float]] = {}
    for position, end_index in enumerate(month_end_indexes):
        if position < 6 or end_index + 1 >= len(data.dates):
            continue
        start_index = month_end_indexes[position - 6]
        ranks = sorted(
            (
                (data.prices[symbol][end_index] / data.prices[symbol][start_index] - 1.0, symbol)
                for symbol in SECTOR_SYMBOLS
            ),
            key=lambda item: (-item[0], item[1]),
        )
        cohorts.append(tuple(item[1] for item in ranks[:3]))
        if len(cohorts) > 6:
            cohorts.pop(0)
        if len(cohorts) < 6:
            continue
        counts = Counter(symbol for cohort in cohorts for symbol in cohort)
        target = {symbol: 0.0 for symbol in ALL_SYMBOLS}
        for symbol, count in counts.items():
            target[symbol] = count / 18.0
        actions[data.dates[end_index + 1]] = target
    first_oos = actions.get(_OOS_START)
    if first_oos is None or not math.isclose(sum(first_oos.values()), 1.0, abs_tol=1e-12):
        raise ValidationError("sector warm-up does not produce six active cohorts at OOS start.")
    return actions


def _evaluate(
    data: _Data,
    turn_actions: Mapping[date, Mapping[str, float]],
    turn_targets: Mapping[date, Mapping[str, float]],
    sector_actions: Mapping[date, Mapping[str, float]],
) -> dict[str, object]:
    asset_returns = _asset_returns(data)
    baselines = _baseline_series(data, asset_returns, turn_targets)
    candidates: dict[str, object] = {}
    for candidate_id, actions in ((TURN_ID, turn_actions), (SECTOR_ID, sector_actions)):
        cost_payload: dict[str, object] = {}
        series_by_cost: dict[str, _Series] = {}
        for cost_id, rate in _COSTS.items():
            series = _simulate(data.dates[1:], asset_returns, actions, rate)
            series_by_cost[cost_id] = series
            windows = _window_metrics(series, include_recent=candidate_id == TURN_ID)
            cost_payload[cost_id] = windows
        decision_metrics = cost_payload["decision"]
        comparator_ids = (
            ("spy_buy_and_hold", "exposure_matched_spy_cash")
            if candidate_id == TURN_ID
            else ("static_nine_sector_equal_weight", "spy_buy_and_hold")
        )
        comparisons = {
            comparator_id: {
                window_id: _compare(
                    decision_metrics[window_id], baselines[comparator_id][window_id]
                )
                for window_id in decision_metrics
            }
            for comparator_id in comparator_ids
        }
        composite = _composite_series(
            baselines["cross_asset_core_series"], series_by_cost["decision"]
        )
        composite_metrics = _window_metrics(composite, include_recent=False)
        core_metrics = baselines["cross_asset_core"]
        candidates[candidate_id] = {
            "cost_metrics": cost_payload,
            "decision_cost_comparisons": comparisons,
            "target_contract": {
                "oos_action_count": sum(
                    _OOS_START <= action_date <= _OOS_END for action_date in actions
                ),
                "max_oos_action_target_weight": _number(
                    max(
                        weight
                        for action_date, target in actions.items()
                        if _OOS_START <= action_date <= _OOS_END
                        for weight in target.values()
                    )
                ),
            },
            "portfolio_composite": {
                "construction": "80pct_static_cross_asset_core_plus_20pct_actual_candidate_sleeve",
                "metrics": composite_metrics,
                "comparison_to_core": {
                    window_id: _compare(composite_metrics[window_id], core_metrics[window_id])
                    for window_id in composite_metrics
                },
                "candidate_target_changed_session_count": len(actions),
            },
        }
    return {
        "candidates": candidates,
        "baselines": {key: value for key, value in baselines.items() if not key.endswith("_series")},
        "cost_models": {
            key: {"bps_per_one_way_turnover": _number(value * 10000.0), "source_claim": False}
            for key, value in _COSTS.items()
        },
        "independent_in_memory_replay_equal": True,
        "parameter_search_performed": False,
        "source_metrics_used": False,
    }


def _asset_returns(data: _Data) -> dict[str, tuple[float, ...]]:
    return {
        symbol: tuple(
            data.prices[symbol][index] / data.prices[symbol][index - 1] - 1.0
            for index in range(1, len(data.dates))
        )
        for symbol in ALL_SYMBOLS
    }


def _baseline_series(
    data: _Data,
    asset_returns: Mapping[str, tuple[float, ...]],
    turn_targets: Mapping[date, Mapping[str, float]],
) -> dict[str, object]:
    dates = data.dates[1:]
    oos_targets = [turn_targets[item]["SPY"] for item in dates if _OOS_START <= item <= _OOS_END]
    fraction = sum(oos_targets) / len(oos_targets)

    def constant(weights: Mapping[str, float]) -> _Series:
        returns = tuple(
            sum(weights.get(symbol, 0.0) * asset_returns[symbol][index] for symbol in ALL_SYMBOLS)
            for index in range(len(dates))
        )
        return _simple_series(dates, returns, weights)

    spy = constant({"SPY": 1.0})
    sectors = constant({symbol: 1.0 / len(SECTOR_SYMBOLS) for symbol in SECTOR_SYMBOLS})
    exposure = constant({"SPY": fraction})
    core = constant({symbol: 1.0 / len(CORE_SYMBOLS) for symbol in CORE_SYMBOLS})
    return {
        "spy_buy_and_hold": _window_metrics(spy, include_recent=True),
        "static_nine_sector_equal_weight": _window_metrics(sectors, include_recent=False),
        "exposure_matched_spy_cash": {
            **_window_metrics(exposure, include_recent=True),
            "calendar_derived_spy_weight": _number(fraction),
        },
        "cross_asset_core": _window_metrics(core, include_recent=False),
        "cross_asset_core_series": core,
    }


def _simple_series(
    dates: tuple[date, ...],
    returns: tuple[float, ...],
    weights: Mapping[str, float],
) -> _Series:
    full_weights = {symbol: float(weights.get(symbol, 0.0)) for symbol in ALL_SYMBOLS}
    exposure = sum(full_weights.values())
    return _Series(
        dates,
        returns,
        tuple(0.0 for _ in dates),
        tuple(exposure for _ in dates),
        tuple(dict(full_weights) for _ in dates),
        tuple({symbol: full_weights[symbol] * 0.0 for symbol in ALL_SYMBOLS} for _ in dates),
    )


def _simulate(
    dates: tuple[date, ...],
    asset_returns: Mapping[str, tuple[float, ...]],
    actions: Mapping[date, Mapping[str, float]],
    cost_rate: float,
) -> _Series:
    drifted = {symbol: 0.0 for symbol in ALL_SYMBOLS}
    returns: list[float] = []
    turnover_values: list[float] = []
    exposure_values: list[float] = []
    weights_values: list[Mapping[str, float]] = []
    contributions_values: list[Mapping[str, float]] = []
    for index, item in enumerate(dates):
        turnover = 0.0
        current = drifted
        if item in actions:
            target = {symbol: float(actions[item].get(symbol, 0.0)) for symbol in ALL_SYMBOLS}
            _validate_weights(target)
            prior_cash = 1.0 - sum(drifted.values())
            target_cash = 1.0 - sum(target.values())
            turnover = 0.5 * (
                sum(abs(target[symbol] - drifted[symbol]) for symbol in ALL_SYMBOLS)
                + abs(target_cash - prior_cash)
            )
            current = target
        exposure = sum(current.values())
        contributions = {
            symbol: current[symbol] * asset_returns[symbol][index] for symbol in ALL_SYMBOLS
        }
        gross = sum(contributions.values())
        cost = turnover * cost_rate
        net = (1.0 - cost) * (1.0 + gross) - 1.0
        if net <= -1.0 or gross <= -1.0:
            raise ValidationError("portfolio equity became nonpositive.")
        drifted = {
            symbol: current[symbol] * (1.0 + asset_returns[symbol][index]) / (1.0 + gross)
            for symbol in ALL_SYMBOLS
        }
        returns.append(net)
        turnover_values.append(turnover)
        exposure_values.append(exposure)
        weights_values.append(current)
        contributions_values.append(contributions)
    return _Series(
        dates,
        tuple(returns),
        tuple(turnover_values),
        tuple(exposure_values),
        tuple(weights_values),
        tuple(contributions_values),
    )


def _composite_series(core: _Series, candidate: _Series) -> _Series:
    if core.dates != candidate.dates:
        raise ValidationError("composite sleeves are not date-aligned.")
    returns = tuple(0.8 * left + 0.2 * right for left, right in zip(core.returns, candidate.returns))
    weights = tuple(
        {
            symbol: 0.8 * core.weights[index][symbol] + 0.2 * candidate.weights[index][symbol]
            for symbol in ALL_SYMBOLS
        }
        for index in range(len(core.dates))
    )
    return _Series(
        core.dates,
        returns,
        tuple(0.2 * value for value in candidate.turnover),
        tuple(0.8 + 0.2 * value for value in candidate.exposure),
        weights,
        tuple({symbol: 0.0 for symbol in ALL_SYMBOLS} for _ in core.dates),
    )


def _window_metrics(series: _Series, *, include_recent: bool) -> dict[str, object]:
    windows = list(_WINDOWS)
    if include_recent:
        windows.append(_RECENT)
    return {
        window_id: _metrics(series, window_id, start, end)
        for window_id, start, end in windows
    }


def _metrics(series: _Series, window_id: str, start: date, end: date) -> dict[str, object]:
    indexes = [index for index, item in enumerate(series.dates) if start <= item <= end]
    if len(indexes) != _SESSION_COUNTS[window_id]:
        raise ValidationError(f"{window_id} metric session count mismatch.")
    values = [series.returns[index] for index in indexes]
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in values:
        equity *= 1.0 + value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, 1.0 - equity / peak)
    total_return = equity - 1.0
    annualized_return = math.pow(equity, 252.0 / len(values)) - 1.0
    volatility = stdev(values) * math.sqrt(252.0) if len(values) > 1 else 0.0
    sharpe = mean(values) / stdev(values) * math.sqrt(252.0) if len(values) > 1 and stdev(values) > 0 else None
    contribution_totals = {
        symbol: sum(series.contributions[index].get(symbol, 0.0) for index in indexes)
        for symbol in ALL_SYMBOLS
    }
    positive_total = sum(max(0.0, value) for value in contribution_totals.values())
    positive_shares = {
        symbol: (max(0.0, value) / positive_total if positive_total > 0.0 else None)
        for symbol, value in contribution_totals.items()
    }
    max_positive_share = max(
        (value for value in positive_shares.values() if value is not None),
        default=None,
    )
    held = sorted(
        symbol
        for symbol in ALL_SYMBOLS
        if any(series.weights[index].get(symbol, 0.0) > 1e-12 for index in indexes)
    )
    max_weight = max(
        series.weights[index].get(symbol, 0.0)
        for index in indexes
        for symbol in ALL_SYMBOLS
    )
    return {
        "window_id": window_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "session_count": len(values),
        "total_return": _number(total_return),
        "annualized_return": _number(annualized_return),
        "annualized_volatility": _number(volatility),
        "sharpe_ratio": _optional_number(sharpe),
        "max_drawdown": _number(max_drawdown),
        "annualized_one_way_turnover": _number(sum(series.turnover[index] for index in indexes) * 252.0 / len(indexes)),
        "invested_session_fraction": _number(sum(series.exposure[index] > 1e-12 for index in indexes) / len(indexes)),
        "average_gross_exposure": _number(sum(series.exposure[index] for index in indexes) / len(indexes)),
        "symbols_held": held,
        "max_realized_weight": _number(max_weight),
        "constituent_contributions": {symbol: _number(value) for symbol, value in contribution_totals.items()},
        "positive_contribution_shares": {symbol: _optional_number(value) for symbol, value in positive_shares.items()},
        "max_positive_contribution_share": _optional_number(max_positive_share),
        "compounded_log_return": _number(math.log1p(total_return)),
    }


def _compare(candidate: Mapping[str, object], baseline: Mapping[str, object]) -> dict[str, object]:
    candidate_sharpe = _optional_float(candidate["sharpe_ratio"])
    baseline_sharpe = _optional_float(baseline["sharpe_ratio"])
    return {
        "total_return_delta": _number(_float(candidate["total_return"]) - _float(baseline["total_return"])),
        "annualized_return_delta": _number(_float(candidate["annualized_return"]) - _float(baseline["annualized_return"])),
        "sharpe_ratio_delta": _optional_number(None if candidate_sharpe is None or baseline_sharpe is None else candidate_sharpe - baseline_sharpe),
        "max_drawdown_delta": _number(_float(candidate["max_drawdown"]) - _float(baseline["max_drawdown"])),
        "max_drawdown_improvement": _number(_float(baseline["max_drawdown"]) - _float(candidate["max_drawdown"])),
    }


def _decisions(evaluation: Mapping[str, object]) -> dict[str, dict[str, object]]:
    decisions: dict[str, dict[str, object]] = {}
    candidates = evaluation["candidates"]
    baselines = evaluation["baselines"]
    for candidate_id in (TURN_ID, SECTOR_ID):
        item = candidates[candidate_id]
        decision = item["cost_metrics"]["decision"]
        stress = item["cost_metrics"]["stress"]
        oos = decision["oos"]
        folds = [decision[f"oos_fold_{index}"] for index in range(1, 4)]
        full_log = _float(oos["compounded_log_return"])
        max_fold_share = max(_float(fold["compounded_log_return"]) / full_log for fold in folds)
        common_conditions = {
            "full_and_all_fold_returns_positive_at_5bps": _float(oos["total_return"]) > 0.0 and all(_float(fold["total_return"]) > 0.0 for fold in folds),
            "full_sharpe_at_least_0_50_at_5bps": _required_float(oos["sharpe_ratio"]) >= 0.50,
            "stress_annualized_return_positive": _float(stress["oos"]["annualized_return"]) > 0.0,
            "stress_annualized_degradation_at_most_0_02": _float(oos["annualized_return"]) - _float(stress["oos"]["annualized_return"]) <= 0.02,
            "max_fold_log_return_share_at_most_0_70": max_fold_share <= 0.70,
            "deterministic_replay_and_metric_integrity": bool(evaluation["independent_in_memory_replay_equal"]),
            "source_metrics_unused": evaluation["source_metrics_used"] is False,
        }
        comparisons = item["decision_cost_comparisons"]
        if candidate_id == TURN_ID:
            spy = comparisons["spy_buy_and_hold"]["oos"]
            matched = comparisons["exposure_matched_spy_cash"]
            fold_wins = sum(
                _float(matched[f"oos_fold_{index}"]["total_return_delta"]) > 0.0
                and _required_float(matched[f"oos_fold_{index}"]["sharpe_ratio_delta"]) > 0.0
                for index in range(1, 4)
            )
            recent = matched["recent_2024"]
            specific = {
                "full_sharpe_exceeds_spy_by_0_10": _required_float(spy["sharpe_ratio_delta"]) >= 0.10,
                "full_sharpe_exceeds_exposure_match_by_0_10": _required_float(matched["oos"]["sharpe_ratio_delta"]) >= 0.10,
                "annualized_return_exceeds_exposure_match_by_0_01": _float(matched["oos"]["annualized_return_delta"]) >= 0.01,
                "drawdown_no_more_than_0_02_worse_than_exposure_match": _float(matched["oos"]["max_drawdown_delta"]) <= 0.02,
                "at_least_two_fold_return_and_sharpe_wins": fold_wins >= 2,
                "recent_net_positive_and_beats_exposure_match": _float(decision["recent_2024"]["total_return"]) > 0.0 and _float(recent["total_return_delta"]) > 0.0,
                "invested_fraction_between_0_12_and_0_25": 0.12 <= _float(oos["invested_session_fraction"]) <= 0.25,
            }
        else:
            static = comparisons["static_nine_sector_equal_weight"]
            spy = comparisons["spy_buy_and_hold"]
            fold_wins = sum(
                _float(static[f"oos_fold_{index}"]["total_return_delta"]) > 0.0
                and _float(spy[f"oos_fold_{index}"]["total_return_delta"]) > 0.0
                for index in range(1, 4)
            )
            better_drawdown = min(
                _float(baselines["static_nine_sector_equal_weight"]["oos"]["max_drawdown"]),
                _float(baselines["spy_buy_and_hold"]["oos"]["max_drawdown"]),
            )
            specific = {
                "annualized_return_exceeds_static_and_spy_by_0_01": _float(static["oos"]["annualized_return_delta"]) >= 0.01 and _float(spy["oos"]["annualized_return_delta"]) >= 0.01,
                "sharpe_exceeds_static_and_spy_by_0_10": _required_float(static["oos"]["sharpe_ratio_delta"]) >= 0.10 and _required_float(spy["oos"]["sharpe_ratio_delta"]) >= 0.10,
                "drawdown_no_more_than_0_02_worse_than_better_comparator": _float(oos["max_drawdown"]) <= better_drawdown + 0.02,
                "at_least_two_fold_total_return_wins_against_both": fold_wins >= 2,
                "stress_annualized_edge_over_static_positive": _float(stress["oos"]["annualized_return"]) - _float(baselines["static_nine_sector_equal_weight"]["oos"]["annualized_return"]) > 0.0,
                "all_nine_sectors_held": all(symbol in oos["symbols_held"] for symbol in SECTOR_SYMBOLS),
                "max_target_weight_at_most_one_third": _float(item["target_contract"]["max_oos_action_target_weight"]) <= 1.0 / 3.0 + 1e-12,
                "max_positive_contribution_share_at_most_0_45": _required_float(oos["max_positive_contribution_share"]) <= 0.45,
            }
        portfolio = item["portfolio_composite"]["comparison_to_core"]["oos"]
        portfolio_conditions = {
            "sharpe_improves_by_0_02": _required_float(portfolio["sharpe_ratio_delta"]) >= 0.02,
            "annualized_return_no_more_than_0_01_lower": _float(portfolio["annualized_return_delta"]) >= -0.01,
            "drawdown_or_return_improves_by_0_005": _float(portfolio["max_drawdown_improvement"]) >= 0.005 or _float(portfolio["annualized_return_delta"]) >= 0.005,
            "candidate_changes_actual_targets": item["portfolio_composite"]["candidate_target_changed_session_count"] > 0,
        }
        gates = {
            "common_integrity": {"passed": all(common_conditions.values()), "conditions": common_conditions, "max_fold_log_return_share": _number(max_fold_share)},
            "candidate_specific_alpha": {"passed": all(specific.values()), "conditions": specific},
            "portfolio_level_value": {"passed": all(portfolio_conditions.values()), "conditions": portfolio_conditions},
        }
        passed = all(gate["passed"] for gate in gates.values())
        decisions[candidate_id] = {
            "candidate_id": candidate_id,
            "all_gates_passed": passed,
            "route": "validated_alpha_candidate" if passed else "close_candidate",
            "gates": gates,
            "shadow_eligibility": passed,
            "paper_promotion_allowed": False,
            "live_authorized": False,
        }
    return decisions


def _summary(result: Mapping[str, object]) -> str:
    lines = [
        "# V5.72 Primary-Source Alpha Tournament",
        "",
        f"- Tournament route: `{result['tournament_decision']['route']}`",
        f"- Validated candidate count: `{result['tournament_decision']['validated_alpha_candidate_count']}`",
        "- Paper promotion allowed: `false`",
        "- Live authorized: `false`",
        "",
    ]
    for candidate_id in (TURN_ID, SECTOR_ID):
        decision = result["candidate_decisions"][candidate_id]
        metrics = result["evaluation"]["candidates"][candidate_id]["cost_metrics"]["decision"]["oos"]
        lines.extend(
            [
                f"## {candidate_id}",
                "",
                f"- Route: `{decision['route']}`",
                f"- Total return: `{metrics['total_return']}`",
                f"- Annualized return: `{metrics['annualized_return']}`",
                f"- Sharpe: `{metrics['sharpe_ratio']}`",
                f"- Maximum drawdown: `{metrics['max_drawdown']}`",
                "",
            ]
        )
        for gate_id, gate in decision["gates"].items():
            lines.append(f"- `{gate_id}`: `{str(gate['passed']).lower()}`")
        lines.append("")
    lines.extend(
        [
            "No external performance metric controlled a gate or ranking. A pass is",
            "eligible only for a new untouched no-submit shadow protocol.",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_weights(weights: Mapping[str, float]) -> None:
    if set(weights) != set(ALL_SYMBOLS):
        raise ValidationError("target weights must contain the exact frozen universe.")
    if any(not math.isfinite(value) or value < -1e-12 or value > 1.0 + 1e-12 for value in weights.values()):
        raise ValidationError("target weights must be finite and between zero and one.")
    if sum(weights.values()) > 1.0 + 1e-12:
        raise ValidationError("target weights exceed full investment.")


def _validate_tracked_inputs() -> None:
    if _hash(_PROTOCOL) != _PROTOCOL_HASH:
        raise ValidationError("protocol SHA-256 mismatch.")
    if _hash(_RECEIPT) != _RECEIPT_HASH:
        raise ValidationError("data receipt SHA-256 mismatch.")


def _safety() -> dict[str, object]:
    return {
        "offline_research_only": True,
        "credential_access": False,
        "network_access": False,
        "nexustrade_access": False,
        "broker_access": False,
        "account_order_position_access": False,
        "paper_mutation": False,
        "live_activity": False,
        "paper_promotion_allowed": False,
        "live_authorized": False,
    }


def _artifact(path: Path) -> dict[str, object]:
    return {"path": str(path), "sha256": _hash(path), "byte_count": path.stat().st_size}


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON artifact must contain an object: {path}")
    return value


def _hash(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local_path(value: Path | str) -> Path:
    if isinstance(value, Path):
        return value
    if not isinstance(value, str) or not value.strip() or "://" in value:
        raise ValidationError("output_root must be a local path.")
    return Path(value)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    _write_text(path, json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")) + "\n")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValidationError("metric must be finite.")
    return format(value, ".16g")


def _optional_number(value: float | None) -> str | None:
    return None if value is None else _number(value)


def _float(value: object) -> float:
    if not isinstance(value, (str, int, float)):
        raise ValidationError("metric is not numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError("metric is not finite.")
    return result


def _optional_float(value: object) -> float | None:
    return None if value is None else _float(value)


def _required_float(value: object) -> float:
    result = _optional_float(value)
    if result is None:
        raise ValidationError("required metric is missing.")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="primary-source-alpha-tournament")
    parser.add_argument("--output-root", default=str(_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_primary_source_alpha_tournament(args.output_root)
    except ValidationError as exc:
        print(f"primary_source_alpha_tournament_status=blocked:{exc}")
        return 2
    if args.format == "json":
        print(json.dumps(_json_safe(result), sort_keys=True, separators=(",", ":")))
    else:
        print("primary_source_alpha_tournament_status=completed")
        print(f"terminal_route={result['tournament_decision']['route']}")
        print(f"validated_alpha_candidate_count={result['tournament_decision']['validated_alpha_candidate_count']}")
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
