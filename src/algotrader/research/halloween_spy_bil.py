"""Frozen V5.76 Halloween SPY/BIL seasonal ETF-proxy evaluation."""

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
from algotrader.research.local_daily_bars import LocalDailyBar, load_local_daily_bars_csv

__all__ = ["build_halloween_spy_bil_preregistration", "run_halloween_spy_bil"]

PROTOCOL_ID = "v5_76_halloween_spy_bil_v1"
CANDIDATE_ID = "halloween_spy_bil_seasonal_proxy"
CANDIDATE_SYMBOLS = ("SPY", "BIL")
CORE = ("SPY", "QQQ", "IWM", "TLT", "GLD")
SYMBOLS = tuple(dict.fromkeys((*CANDIDATE_SYMBOLS, *CORE)))

_PROTOCOL = Path("docs/design/v5_76_halloween_spy_bil_preregistration.md")
_RECEIPT = Path("docs/design/v5_76_halloween_spy_bil_data_receipt.md")
_V573_RECEIPT = Path("docs/design/v5_73_global_equities_dual_momentum_data_receipt.md")
_BASE_DATA = Path("runs/v5_72_primary_source_alpha_tournament/canonical_data.csv")
_BASE_MANIFEST = Path("runs/v5_72_primary_source_alpha_tournament/canonical_data_manifest.json")
_BIL_PATH = Path("runs/v5_73_global_equities_dual_momentum/canonical/bil_daily_tiingo_adjusted_canonical.csv")
_ROOT = Path("runs/v5_76_halloween_spy_bil")
_OUTPUT = _ROOT / "evaluation"
_ENGINE = Path("src/algotrader/research/halloween_spy_bil.py")

_PROTOCOL_HASH = "e306ef9f20803778f86857521977578b02aa7af13ca7033baa09dbdbd4cfdf82"
_RECEIPT_HASH = "f08edaf8f93adc040afbfbc6583741ae7c6518358961194790f8e5a01772a3ad"
_V573_RECEIPT_HASH = "0c5c2126ad954efffc5eba7c7bf9500f7b53747f1d3febce44e1e845a1a08818"
_BASE_DATA_HASH = "5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2"
_BASE_MANIFEST_HASH = "82c1edc7192b9f63b057a4846a0d0540958d9939f6dbabddd793899ca797f0ab"
_SPY_HASH = "ac5fc6752e7aedd8e922782dbd780e53cbac52a0fb8a38f50742e6c803a31a77"
_BIL_HASH = "8d45ab5e0a0ebeeb8447b2e12b368f631b91fe97bd3b3fdc736bda391b8753c5"
_START = date(2007, 6, 1)
_END = date(2026, 7, 31)
_OOS_START = date(2008, 1, 2)
_WINDOWS = (
    ("oos", _OOS_START, _END),
    ("oos_fold_1", date(2008, 1, 2), date(2013, 12, 31)),
    ("oos_fold_2", date(2014, 1, 2), date(2019, 12, 31)),
    ("oos_fold_3", date(2020, 1, 2), _END),
    ("post_2021_publication", date(2021, 1, 4), _END),
)
_COUNTS = {
    "all": 4822,
    "oos": 4674,
    "oos_fold_1": 1511,
    "oos_fold_2": 1510,
    "oos_fold_3": 1653,
    "post_2021_publication": 1400,
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
    holdings: tuple[str, ...]
    contributions: tuple[Mapping[str, float], ...]


def build_halloween_spy_bil_preregistration() -> dict[str, object]:
    _validate_tracked()
    return {
        "record_type": "halloween_spy_bil_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "candidate_id": CANDIDATE_ID,
        "methodology_label": "repository_spy_bil_proxy_not_country_index_replication",
        "symbols": list(CANDIDATE_SYMBOLS),
        "spy_months": [11, 12, 1, 2, 3, 4],
        "bil_months": [5, 6, 7, 8, 9, 10],
        "action_timing": "before_return_ending_on_first_common_session_of_may_and_november",
        "cost_bps_per_one_way_turnover": {
            name: _number(rate * 10000.0) for name, rate in _COSTS.items()
        },
        "protocol_sha256": _PROTOCOL_HASH,
        "receipt_sha256": _RECEIPT_HASH,
        "parameter_search_performed": False,
        "source_metrics_used": False,
        "maximum_route": "new_untouched_no_submit_shadow",
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "safety": _safety(),
    }


def run_halloween_spy_bil(output_root: Path | str = _OUTPUT) -> dict[str, object]:
    preregistration = build_halloween_spy_bil_preregistration()
    data = _load_data()
    actions = _seasonal_actions(data.dates[1:])
    first = _evaluate(data, actions)
    second = _evaluate(data, actions)
    if _json_bytes(first) != _json_bytes(second):
        raise ValidationError("independent in-memory replay was not byte-identical.")
    gates = _gates(first)
    passed = all(gate["passed"] for gate in gates.values())
    result: dict[str, object] = {
        "record_type": "halloween_spy_bil_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": preregistration,
        "data_admission": {
            "base_data_sha256": _BASE_DATA_HASH,
            "base_manifest_sha256": _BASE_MANIFEST_HASH,
            "spy_normalized_symbol_sha256": _SPY_HASH,
            "bil_canonical_sha256": _BIL_HASH,
            "v5_73_receipt_sha256": _V573_RECEIPT_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "common_session_count": len(data.dates),
            "first_session": data.dates[0].isoformat(),
            "last_session": data.dates[-1].isoformat(),
            "adjustment_semantics": "provider_split_and_dividend_adjusted_close",
        },
        "evaluation": first,
        "gates": gates,
        "terminal_decision": {
            "candidate_id": CANDIDATE_ID,
            "all_gates_passed": passed,
            "route": (
                "validated_alpha_candidate"
                if passed
                else "close_halloween_spy_bil_seasonal_proxy"
            ),
            "shadow_eligibility": passed,
            "paper_promotion_allowed": False,
            "live_authorized": False,
        },
        "source_metric_trust": {
            "external_performance_trusted": False,
            "source_metrics_used_for_gates": False,
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
        "record_type": "halloween_spy_bil_artifact_manifest",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "inputs": {
            "protocol_sha256": _PROTOCOL_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "v5_73_receipt_sha256": _V573_RECEIPT_HASH,
            "base_data_sha256": _BASE_DATA_HASH,
            "base_manifest_sha256": _BASE_MANIFEST_HASH,
            "spy_normalized_symbol_sha256": _SPY_HASH,
            "bil_canonical_sha256": _BIL_HASH,
            "engine_sha256": _hash(_ENGINE),
        },
        "artifacts": [_artifact(path) for path in (prereg_path, result_path, summary_path)],
        "terminal_authority": {
            "route": result["terminal_decision"]["route"],
            "maximum_route": "new_untouched_no_submit_shadow" if passed else "deny",
            "shadow_preregistration_eligible": passed,
            "shadow_activated": False,
            "shadow_complete": False,
            "paper_promotion_allowed": False,
            "broker_action_authorized": False,
            "live_authorized": False,
        },
        "safety": _safety(),
    }
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)
    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_sha256"] = _hash(manifest_path)
    return completed


def _load_data() -> _Data:
    _validate_tracked()
    if _hash(_BASE_DATA) != _BASE_DATA_HASH or _hash(_BASE_MANIFEST) != _BASE_MANIFEST_HASH:
        raise ValidationError("imported V5.72 data or manifest hash mismatch.")
    if _hash(_V573_RECEIPT) != _V573_RECEIPT_HASH or _hash(_BIL_PATH) != _BIL_HASH:
        raise ValidationError("imported V5.73 receipt or BIL canonical hash mismatch.")
    by_symbol: dict[str, tuple[LocalDailyBar, ...]] = {}
    for symbol in CORE:
        bars = load_local_daily_bars_csv(_BASE_DATA, symbol=symbol, as_of=_END).usable_bars
        by_symbol[symbol] = tuple(bar for bar in bars if _START <= bar.date <= _END)
    if (
        _normalized_hash(
            load_local_daily_bars_csv(_BASE_DATA, symbol="SPY", as_of=_END).usable_bars
        )
        != _SPY_HASH
    ):
        raise ValidationError("normalized SPY hash mismatch.")
    by_symbol["BIL"] = load_local_daily_bars_csv(
        _BIL_PATH, symbol="BIL", as_of=_END
    ).usable_bars
    dates = tuple(bar.date for bar in by_symbol["SPY"])
    if len(dates) != _COUNTS["all"] or dates[0] != _START or dates[-1] != _END:
        raise ValidationError("common coverage mismatch.")
    for symbol in SYMBOLS:
        if tuple(bar.date for bar in by_symbol[symbol]) != dates:
            raise ValidationError(f"{symbol} common-session sequence mismatch.")
    _validate_windows(dates)
    return _Data(
        dates,
        {
            symbol: tuple(float(bar.adjusted_close) for bar in by_symbol[symbol])
            for symbol in SYMBOLS
        },
    )


def _validate_windows(dates: tuple[date, ...]) -> None:
    for window_id, start, end in _WINDOWS:
        observed = tuple(item for item in dates if start <= item <= end)
        if (
            len(observed) != _COUNTS[window_id]
            or observed[0] != start
            or observed[-1] != end
        ):
            raise ValidationError(f"{window_id} coverage mismatch.")
    oos = tuple(item for item in dates if _OOS_START <= item <= _END)
    folds = tuple(
        item
        for window_id, start, end in _WINDOWS
        if window_id.startswith("oos_fold_")
        for item in dates
        if start <= item <= end
    )
    if folds != oos:
        raise ValidationError("OOS folds do not partition OOS.")


def _calendar_target(item: date) -> str:
    return "SPY" if item.month in (11, 12, 1, 2, 3, 4) else "BIL"


def _seasonal_actions(dates: tuple[date, ...]) -> dict[date, Mapping[str, float]]:
    actions: dict[date, Mapping[str, float]] = {}
    prior = ""
    for item in dates:
        target = _calendar_target(item)
        if target != prior:
            actions[item] = {target: 1.0}
            prior = target
    return actions


def _annual_balanced_actions(
    dates: tuple[date, ...],
) -> dict[date, Mapping[str, float]]:
    actions: dict[date, Mapping[str, float]] = {}
    prior_year: int | None = None
    for item in dates:
        if item.year != prior_year:
            actions[item] = {"SPY": 0.5, "BIL": 0.5}
            prior_year = item.year
    return actions


def _evaluate(
    data: _Data, actions: Mapping[date, Mapping[str, float]]
) -> dict[str, object]:
    asset_returns = {
        symbol: tuple(
            data.prices[symbol][index] / data.prices[symbol][index - 1] - 1.0
            for index in range(1, len(data.dates))
        )
        for symbol in SYMBOLS
    }
    dates = data.dates[1:]
    cost_metrics: dict[str, object] = {}
    series_by_cost: dict[str, _Series] = {}
    for cost_id, rate in _COSTS.items():
        series = _simulate_allocations(
            dates, asset_returns, actions, rate, CANDIDATE_SYMBOLS
        )
        series_by_cost[cost_id] = series
        cost_metrics[cost_id] = _window_metrics(series)
    spy = _constant(dates, asset_returns, {"SPY": 1.0})
    bil = _constant(dates, asset_returns, {"BIL": 1.0})
    balanced = _simulate_allocations(
        dates,
        asset_returns,
        _annual_balanced_actions(dates),
        0.0,
        CANDIDATE_SYMBOLS,
    )
    core = _constant(dates, asset_returns, {symbol: 0.2 for symbol in CORE})
    baselines = {
        "spy_buy_and_hold": _window_metrics(spy),
        "bil_buy_and_hold": _window_metrics(bil),
        "annual_rebalanced_spy_bil_50_50": _window_metrics(balanced),
        "cross_asset_core": _window_metrics(core),
    }
    decision = cost_metrics["decision"]
    comparisons = {
        baseline_id: {
            window_id: _compare(decision[window_id], metrics[window_id])
            for window_id, *_ in _WINDOWS
        }
        for baseline_id, metrics in baselines.items()
    }
    composite = _composite(core, series_by_cost["decision"])
    composite_metrics = _window_metrics(composite)
    oos_actions = [
        (item, next(iter(actions[item])))
        for item in sorted(actions)
        if _OOS_START <= item <= _END
    ]
    first_by_month: dict[tuple[int, int], date] = {}
    for item in dates:
        first_by_month.setdefault((item.year, item.month), item)
    switch_integrity = all(
        item == first_by_month[(item.year, item.month)]
        and item.month in (5, 11)
        and symbol == _calendar_target(item)
        for item, symbol in oos_actions
    )
    state_integrity = all(
        series_by_cost["decision"].holdings[index] == _calendar_target(item)
        for index, item in enumerate(dates)
    )
    return {
        "candidate_cost_metrics": cost_metrics,
        "baselines": baselines,
        "decision_cost_comparisons": comparisons,
        "target_contract": {
            "oos_switch_count": len(oos_actions),
            "oos_switches": [
                {"date": item.isoformat(), "target": symbol}
                for item, symbol in oos_actions
            ],
            "symbols_held_oos": decision["oos"]["symbols_held"],
            "calendar_state_integrity": state_integrity,
            "first_common_may_november_switch_integrity": switch_integrity,
            "continuous_state_across_folds": True,
        },
        "portfolio_composite": {
            "construction": "80pct_static_cross_asset_core_plus_20pct_actual_candidate",
            "metrics": composite_metrics,
            "comparison_to_core": {
                window_id: _compare(
                    composite_metrics[window_id],
                    baselines["cross_asset_core"][window_id],
                )
                for window_id, *_ in _WINDOWS
            },
        },
        "independent_in_memory_replay_equal": True,
        "parameter_search_performed": False,
        "source_metrics_used": False,
    }


def _simulate_allocations(
    dates: tuple[date, ...],
    asset_returns: Mapping[str, tuple[float, ...]],
    actions: Mapping[date, Mapping[str, float]],
    cost_rate: float,
    symbols: tuple[str, ...],
) -> _Series:
    weights = {symbol: 0.0 for symbol in symbols}
    values: list[float] = []
    turns: list[float] = []
    exposures: list[float] = []
    holdings: list[str] = []
    contributions: list[Mapping[str, float]] = []
    for index, item in enumerate(dates):
        turn = 0.0
        if item in actions:
            supplied = actions[item]
            if not supplied or any(symbol not in symbols for symbol in supplied):
                raise ValidationError("invalid allocation target.")
            target = {symbol: float(supplied.get(symbol, 0.0)) for symbol in symbols}
            if any(value < 0.0 for value in target.values()) or sum(target.values()) > 1.0:
                raise ValidationError("allocation target weights are invalid.")
            prior_cash = 1.0 - sum(weights.values())
            target_cash = 1.0 - sum(target.values())
            turn = 0.5 * (
                sum(abs(target[symbol] - weights[symbol]) for symbol in symbols)
                + abs(target_cash - prior_cash)
            )
            weights = target
        daily = {
            symbol: weights[symbol] * asset_returns[symbol][index] for symbol in symbols
        }
        gross = sum(daily.values())
        if 1.0 + gross <= 0.0:
            raise ValidationError("daily gross return is invalid.")
        net = (1.0 - turn * cost_rate) * (1.0 + gross) - 1.0
        values.append(net)
        turns.append(turn)
        exposures.append(sum(weights.values()))
        holdings.append("|".join(symbol for symbol in symbols if weights[symbol] > 0.0))
        contributions.append(
            {symbol: daily.get(symbol, 0.0) for symbol in CANDIDATE_SYMBOLS}
        )
        weights = {
            symbol: weights[symbol] * (1.0 + asset_returns[symbol][index]) / (1.0 + gross)
            for symbol in symbols
        }
    return _Series(
        dates,
        tuple(values),
        tuple(turns),
        tuple(exposures),
        tuple(holdings),
        tuple(contributions),
    )


def _constant(
    dates: tuple[date, ...],
    asset_returns: Mapping[str, tuple[float, ...]],
    weights: Mapping[str, float],
) -> _Series:
    values = tuple(
        sum(weight * asset_returns[symbol][index] for symbol, weight in weights.items())
        for index in range(len(dates))
    )
    empty = tuple({symbol: 0.0 for symbol in CANDIDATE_SYMBOLS} for _ in dates)
    return _Series(
        dates,
        values,
        tuple(0.0 for _ in dates),
        tuple(sum(weights.values()) for _ in dates),
        tuple("static" for _ in dates),
        empty,
    )


def _composite(core: _Series, candidate: _Series) -> _Series:
    return _Series(
        core.dates,
        tuple(
            0.8 * left + 0.2 * right
            for left, right in zip(core.returns, candidate.returns)
        ),
        tuple(0.2 * value for value in candidate.turnover),
        tuple(0.8 + 0.2 * value for value in candidate.exposure),
        candidate.holdings,
        candidate.contributions,
    )


def _window_metrics(series: _Series) -> dict[str, object]:
    return {
        window_id: _metrics(series, window_id, start, end)
        for window_id, start, end in _WINDOWS
    }


def _metrics(
    series: _Series, window_id: str, start: date, end: date
) -> dict[str, object]:
    indexes = [
        index for index, item in enumerate(series.dates) if start <= item <= end
    ]
    if len(indexes) != _COUNTS[window_id]:
        raise ValidationError(f"{window_id} metric count mismatch.")
    returns = [series.returns[index] for index in indexes]
    equity, peak, drawdown = 1.0, 1.0, 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = max(drawdown, 1.0 - equity / peak)
    total = equity - 1.0
    annualized = math.pow(equity, 252.0 / len(returns)) - 1.0
    daily_stdev = stdev(returns)
    sharpe = mean(returns) / daily_stdev * math.sqrt(252.0) if daily_stdev > 0.0 else None
    contribution_totals = {
        symbol: sum(series.contributions[index][symbol] for index in indexes)
        for symbol in CANDIDATE_SYMBOLS
    }
    held = sorted(
        {
            symbol
            for index in indexes
            for symbol in series.holdings[index].split("|")
            if symbol and symbol != "static"
        }
    )
    return {
        "window_id": window_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "session_count": len(returns),
        "total_return": _number(total),
        "annualized_return": _number(annualized),
        "annualized_volatility": _number(daily_stdev * math.sqrt(252.0)),
        "sharpe_ratio": _optional_number(sharpe),
        "max_drawdown": _number(drawdown),
        "annualized_one_way_turnover": _number(
            sum(series.turnover[index] for index in indexes) * 252.0 / len(indexes)
        ),
        "compounded_log_return": _number(math.log1p(total)),
        "symbols_held": held,
        "constituent_contributions": {
            symbol: _number(value) for symbol, value in contribution_totals.items()
        },
    }


def _compare(
    candidate: Mapping[str, object], baseline: Mapping[str, object]
) -> dict[str, object]:
    return {
        "total_return_delta": _number(
            _float(candidate["total_return"]) - _float(baseline["total_return"])
        ),
        "annualized_return_delta": _number(
            _float(candidate["annualized_return"])
            - _float(baseline["annualized_return"])
        ),
        "sharpe_ratio_delta": _number(
            _required_float(candidate["sharpe_ratio"])
            - _required_float(baseline["sharpe_ratio"])
        ),
        "max_drawdown_delta": _number(
            _float(candidate["max_drawdown"]) - _float(baseline["max_drawdown"])
        ),
        "max_drawdown_improvement": _number(
            _float(baseline["max_drawdown"]) - _float(candidate["max_drawdown"])
        ),
    }


def _gates(evaluation: Mapping[str, object]) -> dict[str, dict[str, object]]:
    decision = evaluation["candidate_cost_metrics"]["decision"]
    stress = evaluation["candidate_cost_metrics"]["stress"]
    oos = decision["oos"]
    folds = [decision[f"oos_fold_{index}"] for index in range(1, 4)]
    full_log = _float(oos["compounded_log_return"])
    max_fold_share = (
        max(_float(fold["compounded_log_return"]) / full_log for fold in folds)
        if full_log > 0.0
        else 1.0
    )
    contract = evaluation["target_contract"]
    common = {
        "full_and_all_fold_returns_positive": _float(oos["total_return"]) > 0.0
        and all(_float(fold["total_return"]) > 0.0 for fold in folds),
        "full_sharpe_at_least_0_75": _required_float(oos["sharpe_ratio"]) >= 0.75,
        "stress_return_positive": _float(stress["oos"]["annualized_return"]) > 0.0,
        "stress_degradation_at_most_0_01": (
            _float(oos["annualized_return"])
            - _float(stress["oos"]["annualized_return"])
            <= 0.01
        ),
        "max_fold_log_share_at_most_0_70": max_fold_share <= 0.70,
        "calendar_switch_drift_and_replay_integrity": all(
            (
                contract["calendar_state_integrity"],
                contract["first_common_may_november_switch_integrity"],
                contract["continuous_state_across_folds"],
                evaluation["independent_in_memory_replay_equal"],
            )
        ),
        "source_metrics_unused": evaluation["source_metrics_used"] is False,
    }
    balanced = evaluation["decision_cost_comparisons"][
        "annual_rebalanced_spy_bil_50_50"
    ]
    spy = evaluation["decision_cost_comparisons"]["spy_buy_and_hold"]
    fold_wins = sum(
        _float(balanced[f"oos_fold_{index}"]["total_return_delta"]) > 0.0
        and _float(balanced[f"oos_fold_{index}"]["sharpe_ratio_delta"]) > 0.0
        for index in range(1, 4)
    )
    specific = {
        "annualized_return_exceeds_balanced_by_0_01": _float(
            balanced["oos"]["annualized_return_delta"]
        )
        >= 0.01,
        "sharpe_exceeds_balanced_and_spy_by_0_10": (
            _float(balanced["oos"]["sharpe_ratio_delta"]) >= 0.10
            and _float(spy["oos"]["sharpe_ratio_delta"]) >= 0.10
        ),
        "drawdown_improves_spy_by_0_10_and_near_balanced": (
            _float(spy["oos"]["max_drawdown_improvement"]) >= 0.10
            and _float(balanced["oos"]["max_drawdown_improvement"]) >= -0.02
        ),
        "at_least_two_fold_return_and_sharpe_wins": fold_wins >= 2,
        "post_2021_positive_and_beats_balanced": (
            _float(decision["post_2021_publication"]["total_return"]) > 0.0
            and _float(
                balanced["post_2021_publication"]["total_return_delta"]
            )
            > 0.0
        ),
        "stress_positive_and_above_balanced": (
            _float(stress["oos"]["annualized_return"]) > 0.0
            and _float(stress["oos"]["annualized_return"])
            > _float(
                evaluation["baselines"]["annual_rebalanced_spy_bil_50_50"]["oos"][
                    "annualized_return"
                ]
            )
        ),
        "both_symbols_held_oos": set(contract["symbols_held_oos"])
        == set(CANDIDATE_SYMBOLS),
    }
    composite = evaluation["portfolio_composite"]["comparison_to_core"]["oos"]
    portfolio = {
        "sharpe_improves_by_0_02": _float(composite["sharpe_ratio_delta"]) >= 0.02,
        "annualized_return_no_more_than_0_01_lower": _float(
            composite["annualized_return_delta"]
        )
        >= -0.01,
        "drawdown_or_return_improves_by_0_005": _float(
            composite["max_drawdown_improvement"]
        )
        >= 0.005
        or _float(composite["annualized_return_delta"]) >= 0.005,
    }
    return {
        "common_integrity": {
            "passed": all(common.values()),
            "conditions": common,
            "max_fold_log_return_share": _number(max_fold_share),
        },
        "candidate_specific_alpha": {
            "passed": all(specific.values()),
            "conditions": specific,
        },
        "portfolio_level_value": {
            "passed": all(portfolio.values()),
            "conditions": portfolio,
        },
    }


def _summary(result: Mapping[str, object]) -> str:
    metrics = result["evaluation"]["candidate_cost_metrics"]["decision"]["oos"]
    lines = [
        "# V5.76 Halloween SPY/BIL",
        "",
        f"- Route: `{result['terminal_decision']['route']}`",
        f"- All gates passed: `{str(result['terminal_decision']['all_gates_passed']).lower()}`",
        f"- Total return: `{metrics['total_return']}`",
        f"- Annualized return: `{metrics['annualized_return']}`",
        f"- Sharpe: `{metrics['sharpe_ratio']}`",
        f"- Maximum drawdown: `{metrics['max_drawdown']}`",
        "- Paper promotion allowed: `false`",
        "- Live authorized: `false`",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- `{gate_id}`: `{str(gate['passed']).lower()}`"
        for gate_id, gate in result["gates"].items()
    )
    lines.extend(
        [
            "",
            "No external performance metric controlled a gate. A pass is no-submit-shadow eligible only.",
            "",
        ]
    )
    return "\n".join(lines)


def _normalized_hash(bars: Sequence[LocalDailyBar]) -> str:
    digest = hashlib.sha256()
    for bar in bars:
        digest.update(
            f"{bar.symbol},{bar.date.isoformat()},{format(bar.adjusted_close, 'f')}\n".encode(
                "utf-8"
            )
        )
    return digest.hexdigest()


def _validate_tracked() -> None:
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
        "broker_action_authorized": False,
        "paper_mutation": False,
        "live_activity": False,
        "paper_promotion_allowed": False,
        "live_authorized": False,
    }


def _artifact(path: Path) -> dict[str, object]:
    return {"path": str(path), "sha256": _hash(path), "byte_count": path.stat().st_size}


def _hash(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local_path(value: Path | str) -> Path:
    if isinstance(value, Path):
        return value
    if not isinstance(value, str) or not value.strip() or "://" in value:
        raise ValidationError("output_root must be local.")
    return Path(value)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    _write_text(
        path, json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")) + "\n"
    )


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        _json_safe(value), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValidationError("metric is not finite.")
    return format(value, ".16g")


def _optional_number(value: float | None) -> str | None:
    return None if value is None else _number(value)


def _float(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError("metric is not finite.")
    return result


def _required_float(value: object) -> float:
    if value is None:
        raise ValidationError("required metric missing.")
    return _float(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="halloween-spy-bil")
    parser.add_argument("--output-root", default=str(_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_halloween_spy_bil(args.output_root)
    except ValidationError as exc:
        print(f"halloween_spy_bil_status=blocked:{exc}")
        return 2
    if args.format == "json":
        print(json.dumps(_json_safe(result), sort_keys=True, separators=(",", ":")))
    else:
        print("halloween_spy_bil_status=completed")
        print(f"terminal_route={result['terminal_decision']['route']}")
        print(
            "all_gates_passed="
            f"{str(result['terminal_decision']['all_gates_passed']).lower()}"
        )
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
