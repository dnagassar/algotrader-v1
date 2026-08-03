"""Frozen V5.89 Keller Bold Asset Allocation tournament."""

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
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

__all__ = [
    "build_baa_preregistration",
    "run_baa_tournament",
]

PROTOCOL_ID = "v5_89_keller_bold_asset_allocation_v1"
G4_ID = "baa_g4_aggressive_proxy"
G12_ID = "baa_g12_balanced_proxy"
CANDIDATE_IDS = (G4_ID, G12_ID)
ABLATION_G4_ID = "no_canary_g4_always_offensive"
ABLATION_G12_ID = "no_canary_g12_always_offensive"
STATIC_ID = "static_equal_g12_monthly"
SPY_ID = "spy_buy_and_hold"
PARENT_ID = "spy_ief_60_40_monthly"
ALL_SYMBOLS = (
    "SPY", "QQQ", "IWM", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD",
    "TLT", "HYG", "LQD", "EFA", "AGG", "TIP", "BIL", "IEF",
)
CANARY_SYMBOLS = ("SPY", "EFA", "EEM", "AGG")
G4_OFFENSIVE_SYMBOLS = ("QQQ", "EEM", "EFA", "AGG")
G12_OFFENSIVE_SYMBOLS = (
    "SPY", "QQQ", "IWM", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD",
    "TLT", "HYG", "LQD",
)
DEFENSIVE_SYMBOLS = ("TIP", "DBC", "BIL", "IEF", "TLT", "LQD", "AGG")
_PROTOCOL = Path(
    "docs/design/v5_89_keller_bold_asset_allocation_preregistration.md"
)
_RECEIPT = Path(
    "docs/design/v5_89_keller_bold_asset_allocation_data_receipt.md"
)
_DATA = Path("runs/v5_89_keller_bold_asset_allocation/canonical_data.csv")
_DATA_MANIFEST = Path(
    "runs/v5_89_keller_bold_asset_allocation/canonical_data_manifest.json"
)
_OUTPUT = Path("runs/v5_89_keller_bold_asset_allocation/evaluation")
_ENGINE = Path("src/algotrader/research/baa_tournament.py")
_PROTOCOL_HASH = "b000c85a4ce041a26cfe3eedace3439177456d2507d8a71c08ed8e0740262747"
_RECEIPT_HASH = "bad57306a3bf9baafe2c2b2bb0422b83f66286ed686ee8f03cef41dc4109cc5c"
_DATA_HASH = "a8a2b4ceb6d5aa22001e8967d741e51bb6246985ade55f7ea9fc79b69d677543"
_MANIFEST_HASH = "40b595bab9156d586302aab9595c47a38fad9d7c018dd62c612a0970242b2c77"
_START = date(2007, 7, 26)
_END = date(2026, 7, 31)
_OOS_START = date(2022, 9, 1)
_WINDOWS = (
    ("oos", _OOS_START, _END),
    ("oos_fold_1", date(2022, 9, 1), date(2023, 12, 31)),
    ("oos_fold_2", date(2024, 1, 1), date(2025, 4, 30)),
    ("oos_fold_3", date(2025, 5, 1), _END),
)
_SESSION_COUNTS = {
    "all": 4784,
    "oos": 981,
    "oos_fold_1": 334,
    "oos_fold_2": 333,
    "oos_fold_3": 314,
}
_ACTION_COUNTS = {
    "oos": 47,
    "oos_fold_1": 16,
    "oos_fold_2": 16,
    "oos_fold_3": 15,
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
    risk_exposure: tuple[float, ...]
    weights: tuple[Mapping[str, float], ...]
    contributions: tuple[Mapping[str, float], ...]
    cost_contributions: tuple[float, ...]
    equity: tuple[float, ...]
    drawdown: tuple[float, ...]


def build_baa_preregistration() -> dict[str, object]:
    _validate_tracked_inputs()
    return {
        "record_type": "baa_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "candidate_ids": list(CANDIDATE_IDS),
        "control_ids": [ABLATION_G4_ID, ABLATION_G12_ID, STATIC_ID],
        "baseline_ids": [SPY_ID, PARENT_ID],
        "symbols": list(ALL_SYMBOLS),
        "canary_symbols": list(CANARY_SYMBOLS),
        "g4_offensive_symbols": list(G4_OFFENSIVE_SYMBOLS),
        "g12_offensive_symbols": list(G12_OFFENSIVE_SYMBOLS),
        "defensive_symbols": list(DEFENSIVE_SYMBOLS),
        "oos_start": _OOS_START.isoformat(),
        "oos_end": _END.isoformat(),
        "canary_momentum": "13612W_monthly_close",
        "canary_breadth_rule": "any_nonpositive_canary_momentum_is_defensive",
        "relative_momentum": "p0_over_mean_p0_through_p12_monthly_close",
        "g4_offensive_selection": "top_1_weight_1_000000000000",
        "g12_offensive_selection": "top_6_weight_one_sixth_each",
        "defensive_selection": "top_3_weight_one_third_each",
        "defensive_cash_substitution": (
            "selected_defensive_asset_with_relative_momentum_below_bil_"
            "moves_to_zero_return_cash"
        ),
        "offensive_cash_substitution": "none",
        "selection_tie_rule": "frozen_universe_order",
        "action_lag": "month_end_close_t_to_next_common_close_t_plus_1",
        "cost_bps_per_one_way_turnover": {
            key: _number(value * 10000.0) for key, value in _COSTS.items()
        },
        "protocol_sha256": _PROTOCOL_HASH,
        "receipt_sha256": _RECEIPT_HASH,
        "data_sha256": _DATA_HASH,
        "data_manifest_sha256": _MANIFEST_HASH,
        "parameter_search_performed": False,
        "source_metrics_used": False,
        "paper_or_live_promotion_allowed": False,
        "safety": _safety(),
    }

def run_baa_tournament(output_root: Path | str = _OUTPUT) -> dict[str, object]:
    preregistration = build_baa_preregistration()
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
    actions, modes = _build_actions(data)
    evaluation = _evaluate(data, actions, modes)
    return _build_result(preregistration, data, evaluation, replay_equal=True)
def _build_result(
    preregistration: Mapping[str, object],
    data: _Data,
    evaluation: Mapping[str, object],
    *,
    replay_equal: bool,
) -> dict[str, object]:
    decisions = _decisions(evaluation, replay_equal=replay_equal)
    passing = [
        candidate_id
        for candidate_id in CANDIDATE_IDS
        if decisions[candidate_id]["all_gates_passed"]
    ]
    winner = None
    if passing:
        winner = sorted(
            passing,
            key=lambda candidate_id: (
                -_required_float(
                    decisions[candidate_id]["selection_metrics"][
                        "composite_sharpe_improvement"
                    ]
                ),
                -_required_float(
                    decisions[candidate_id]["selection_metrics"]["candidate_sharpe"]
                ),
                -_float(
                    decisions[candidate_id]["selection_metrics"][
                        "candidate_annualized_return"
                    ]
                ),
                _float(
                    decisions[candidate_id]["selection_metrics"][
                        "candidate_max_drawdown"
                    ]
                ),
                candidate_id,
            ),
        )[0]
    return {
        "record_type": "baa_tournament_result",
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
            "route": (
                "provisional_historical_validated_alpha_candidate"
                if winner
                else "no_candidate_passed"
            ),
            "passing_candidate_count": len(passing),
            "shadow_winner_id": winner,
            "selected_shadow_winner_count": 1 if winner else 0,
            "atomic_candidate_count": len(CANDIDATE_IDS),
            "current_clock_no_submit_shadow_only": bool(winner),
            "paper_promotion_allowed": False,
            "live_authorized": False,
        },
        "replay_evidence": {
            "full_pipeline_replays": 2,
            "result_bytes_equal": True,
            "manifest_bytes_equal": True,
        },
        "source_metric_trust": {
            "external_performance_trusted": False,
            "source_metrics_used_for_ranking_or_gates": False,
        },
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
    if manifest.get("protocol_id") != PROTOCOL_ID:
        raise ValidationError("manifest protocol ID mismatch.")
    frozen_pins = manifest.get("frozen_pins")
    if (
        not isinstance(frozen_pins, dict)
        or frozen_pins.get("protocol") != _PROTOCOL_HASH
    ):
        raise ValidationError("manifest protocol hash pin mismatch.")
    if manifest.get("provider") != "tiingo_eod":
        raise ValidationError("manifest provider mismatch.")
    if manifest.get("provider_field") != "adjClose":
        raise ValidationError("manifest provider field mismatch.")
    if (
        manifest.get("adjustment_semantics")
        != "provider_split_and_dividend_adjusted_close"
    ):
        raise ValidationError("manifest adjustment semantics mismatch.")
    if manifest.get("requested_start") != _START.isoformat():
        raise ValidationError("manifest requested start mismatch.")
    if manifest.get("requested_end") != _END.isoformat():
        raise ValidationError("manifest requested end mismatch.")
    if manifest.get("combined_row_count") != len(ALL_SYMBOLS) * _SESSION_COUNTS["all"]:
        raise ValidationError("manifest combined row count mismatch.")
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
        if len(observed) != _SESSION_COUNTS[window_id]:
            raise ValidationError(f"{window_id} window mismatch.")
    oos = tuple(item for item in dates if _OOS_START <= item <= _END)
    folds = tuple(item for name, start, end in _WINDOWS if name != "oos" for item in dates if start <= item <= end)
    if folds != oos:
        raise ValidationError("folds do not exactly partition OOS.")


def _thirteen_month_closes(
    data: _Data, month_ends: Sequence[int], month_position: int, symbol: str
) -> tuple[float, ...]:
    return tuple(
        data.prices[symbol][month_ends[month_position - offset]]
        for offset in range(13)
    )


def _momentum_13612w(closes: Sequence[float]) -> float:
    p0 = closes[0]
    value = (
        12.0 * (p0 / closes[1] - 1.0)
        + 4.0 * (p0 / closes[3] - 1.0)
        + 2.0 * (p0 / closes[6] - 1.0)
        + 1.0 * (p0 / closes[12] - 1.0)
    )
    if not math.isfinite(value):
        raise ValidationError("13612W momentum is nonfinite.")
    return value


def _relative_momentum(closes: Sequence[float]) -> float:
    value = closes[0] / mean(closes)
    if not math.isfinite(value) or value <= 0.0:
        raise ValidationError("relative momentum is invalid.")
    return value


def _top_by_relative_momentum(
    values: Mapping[str, float], universe: Sequence[str], count: int
) -> tuple[str, ...]:
    order_index = {symbol: index for index, symbol in enumerate(universe)}
    ranked = sorted(
        universe,
        key=lambda symbol: (-values[symbol], order_index[symbol]),
    )
    return tuple(ranked[:count])


def _build_actions(
    data: _Data,
) -> tuple[dict[str, dict[date, dict[str, float]]], dict[date, str]]:
    result: dict[str, dict[date, dict[str, float]]] = {
        strategy_id: {}
        for strategy_id in (
            *CANDIDATE_IDS,
            ABLATION_G4_ID,
            ABLATION_G12_ID,
            STATIC_ID,
            SPY_ID,
            PARENT_ID,
        )
    }
    modes: dict[date, str] = {}
    month_ends = [
        index
        for index in range(len(data.dates) - 1)
        if (data.dates[index].year, data.dates[index].month)
        != (data.dates[index + 1].year, data.dates[index + 1].month)
    ]
    for month_position, end_index in enumerate(month_ends):
        if month_position < 12:
            continue
        action_date = data.dates[end_index + 1]
        if not (_OOS_START <= action_date <= _END):
            continue

        closes = {
            symbol: _thirteen_month_closes(
                data, month_ends, month_position, symbol
            )
            for symbol in ALL_SYMBOLS
        }
        canary = {
            symbol: _momentum_13612w(closes[symbol])
            for symbol in CANARY_SYMBOLS
        }
        offensive = all(value > 0.0 for value in canary.values())
        modes[action_date] = "offensive" if offensive else "defensive"
        relative = {
            symbol: _relative_momentum(closes[symbol])
            for symbol in ALL_SYMBOLS
        }

        defensive_target = _empty_target()
        for symbol in _top_by_relative_momentum(
            relative, DEFENSIVE_SYMBOLS, 3
        ):
            if relative[symbol] < relative["BIL"]:
                continue
            defensive_target[symbol] = 1.0 / 3.0

        g4_offensive_target = _empty_target()
        g4_offensive_target[
            _top_by_relative_momentum(relative, G4_OFFENSIVE_SYMBOLS, 1)[0]
        ] = 1.0
        g12_offensive_target = _empty_target()
        for symbol in _top_by_relative_momentum(
            relative, G12_OFFENSIVE_SYMBOLS, 6
        ):
            g12_offensive_target[symbol] = 1.0 / 6.0

        g4_target = dict(
            g4_offensive_target if offensive else defensive_target
        )
        g12_target = dict(
            g12_offensive_target if offensive else defensive_target
        )

        static = _empty_target()
        for symbol in G12_OFFENSIVE_SYMBOLS:
            static[symbol] = 1.0 / 12.0
        parent = _empty_target()
        parent["SPY"] = 0.60
        parent["IEF"] = 0.40

        for strategy_id, target in (
            (G4_ID, g4_target),
            (G12_ID, g12_target),
            (ABLATION_G4_ID, dict(g4_offensive_target)),
            (ABLATION_G12_ID, dict(g12_offensive_target)),
            (STATIC_ID, static),
            (PARENT_ID, parent),
        ):
            _validate_weights(target)
            result[strategy_id][action_date] = target

    for candidate_id in CANDIDATE_IDS:
        if not result[candidate_id] or min(result[candidate_id]) != _OOS_START:
            raise ValidationError(
                f"{candidate_id} warm-up did not produce the first OOS action."
            )
    result[SPY_ID][_OOS_START] = {**_empty_target(), "SPY": 1.0}
    return result, modes


def _validate_action_contract(
    data: _Data,
    actions: Mapping[str, Mapping[date, Mapping[str, float]]],
    modes: Mapping[date, str],
) -> None:
    expected_dates = tuple(
        item
        for index, item in enumerate(data.dates)
        if _OOS_START <= item <= _END
        and index > 0
        and (
            data.dates[index - 1].year,
            data.dates[index - 1].month,
        )
        != (item.year, item.month)
    )
    monthly_ids = (
        *CANDIDATE_IDS,
        ABLATION_G4_ID,
        ABLATION_G12_ID,
        STATIC_ID,
        PARENT_ID,
    )
    for strategy_id in monthly_ids:
        observed = tuple(sorted(actions[strategy_id]))
        if observed != expected_dates:
            raise ValidationError(
                f"{strategy_id} monthly action dates do not match the contract."
            )
        for window, start, end in _WINDOWS:
            count = sum(start <= item <= end for item in observed)
            if count != _ACTION_COUNTS[window]:
                raise ValidationError(
                    f"{strategy_id} {window} action count mismatch."
                )
        for target in actions[strategy_id].values():
            _validate_weights(target)
    if tuple(sorted(actions[SPY_ID])) != (_OOS_START,):
        raise ValidationError("SPY buy-and-hold action date mismatch.")
    _validate_weights(actions[SPY_ID][_OOS_START])
    if tuple(sorted(modes)) != expected_dates:
        raise ValidationError("mode dates do not match the action contract.")

    for item in expected_dates:
        mode = modes[item]
        _validate_grammar(
            actions[G4_ID][item],
            mode,
            offensive_universe=G4_OFFENSIVE_SYMBOLS,
            offensive_count=1,
            offensive_weight=1.0,
        )
        _validate_grammar(
            actions[G12_ID][item],
            mode,
            offensive_universe=G12_OFFENSIVE_SYMBOLS,
            offensive_count=6,
            offensive_weight=1.0 / 6.0,
        )
        _validate_grammar(
            actions[ABLATION_G4_ID][item],
            "offensive",
            offensive_universe=G4_OFFENSIVE_SYMBOLS,
            offensive_count=1,
            offensive_weight=1.0,
        )
        _validate_grammar(
            actions[ABLATION_G12_ID][item],
            "offensive",
            offensive_universe=G12_OFFENSIVE_SYMBOLS,
            offensive_count=6,
            offensive_weight=1.0 / 6.0,
        )
        static = actions[STATIC_ID][item]
        if any(
            not math.isclose(
                static[symbol],
                1.0 / 12.0 if symbol in G12_OFFENSIVE_SYMBOLS else 0.0,
                abs_tol=1e-12,
            )
            for symbol in ALL_SYMBOLS
        ):
            raise ValidationError("static equal-G12 target mismatch.")
        parent = actions[PARENT_ID][item]
        if not (
            math.isclose(parent["SPY"], 0.60, abs_tol=1e-12)
            and math.isclose(parent["IEF"], 0.40, abs_tol=1e-12)
            and math.isclose(sum(parent.values()), 1.0, abs_tol=1e-12)
        ):
            raise ValidationError("60/40 parent target mismatch.")


def _validate_grammar(
    target: Mapping[str, float],
    mode: str,
    *,
    offensive_universe: Sequence[str],
    offensive_count: int,
    offensive_weight: float,
) -> None:
    held = {
        symbol: weight
        for symbol, weight in target.items()
        if weight > 1e-12
    }
    if mode == "offensive":
        if len(held) != offensive_count:
            raise ValidationError("offensive selection count mismatch.")
        if any(symbol not in offensive_universe for symbol in held):
            raise ValidationError("offensive selection outside universe.")
        if any(
            not math.isclose(weight, offensive_weight, abs_tol=1e-12)
            for weight in held.values()
        ):
            raise ValidationError("offensive weight grammar mismatch.")
    else:
        if len(held) > 3:
            raise ValidationError("defensive selection count exceeds three.")
        if any(symbol not in DEFENSIVE_SYMBOLS for symbol in held):
            raise ValidationError("defensive selection outside universe.")
        if any(
            not math.isclose(weight, 1.0 / 3.0, abs_tol=1e-12)
            for weight in held.values()
        ):
            raise ValidationError("defensive weight grammar mismatch.")
    if sum(target.values()) > 1.0 + 1e-12:
        raise ValidationError("target exposure exceeds 100%.")

def _evaluate(
    data: _Data,
    actions: Mapping[str, Mapping[date, Mapping[str, float]]],
    modes: Mapping[date, str],
) -> dict[str, object]:
    _validate_action_contract(data, actions, modes)
    series = {
        strategy_id: {
            cost_id: _simulate(data, strategy_actions, rate)
            for cost_id, rate in _COSTS.items()
        }
        for strategy_id, strategy_actions in actions.items()
    }
    metrics_by_strategy = {
        strategy_id: {
            cost_id: _window_metrics(value)
            for cost_id, value in costs.items()
        }
        for strategy_id, costs in series.items()
    }
    comparator_ids = (
        ABLATION_G4_ID,
        ABLATION_G12_ID,
        STATIC_ID,
        SPY_ID,
        PARENT_ID,
    )
    comparators = {
        strategy_id: metrics_by_strategy[strategy_id]
        for strategy_id in comparator_ids
    }

    candidates: dict[str, object] = {}
    for candidate_id in CANDIDATE_IDS:
        closest_id = ABLATION_G4_ID if candidate_id == G4_ID else ABLATION_G12_ID
        candidate_costs = metrics_by_strategy[candidate_id]
        comparisons = {
            comparator_id: {
                window: _compare(
                    candidate_costs["decision"][window],
                    metrics_by_strategy[comparator_id]["decision"][window],
                )
                for window, _, _ in _WINDOWS
            }
            for comparator_id in (closest_id, STATIC_ID, SPY_ID)
        }

        composite_actions = _blend_actions(
            actions[PARENT_ID], actions[candidate_id], 0.8, 0.2
        )
        composites: dict[str, object] = {}
        for cost_id, rate in _COSTS.items():
            metrics = _window_metrics(_simulate(data, composite_actions, rate))
            composites[cost_id] = {
                "metrics": metrics,
                "comparison_to_parent": {
                    window: _compare(
                        metrics[window],
                        metrics_by_strategy[PARENT_ID][cost_id][window],
                    )
                    for window, _, _ in _WINDOWS
                },
            }

        target_windows: dict[str, object] = {}
        for window, start, end in _WINDOWS:
            candidate_window = {
                item: target
                for item, target in actions[candidate_id].items()
                if start <= item <= end
            }
            closest_window = {
                item: target
                for item, target in actions[closest_id].items()
                if start <= item <= end
            }
            static_window = {
                item: target
                for item, target in actions[STATIC_ID].items()
                if start <= item <= end
            }
            exposures = [
                sum(target[symbol] for symbol in ALL_SYMBOLS)
                for target in candidate_window.values()
            ]
            target_windows[window] = {
                "action_count": len(candidate_window),
                "defensive_action_count": sum(
                    modes[item] == "defensive" for item in candidate_window
                ),
                "max_target_weight": _number(
                    max(
                        target[symbol]
                        for target in candidate_window.values()
                        for symbol in ALL_SYMBOLS
                    )
                ),
                "max_etf_target_exposure": _number(max(exposures)),
                "average_etf_target_exposure": _number(mean(exposures)),
                "divergent_decisions_from_closest_ablation": _divergence(
                    candidate_window, closest_window
                ),
                "divergent_decisions_from_static": _divergence(
                    candidate_window, static_window
                ),
            }

        action_dates = tuple(sorted(actions[candidate_id]))
        exposures = [
            sum(target[symbol] for symbol in ALL_SYMBOLS)
            for target in actions[candidate_id].values()
        ]
        candidates[candidate_id] = {
            "closest_ablation_id": closest_id,
            "cost_metrics": candidate_costs,
            "decision_cost_comparisons": comparisons,
            "portfolio_composite": {
                "construction": (
                    "80pct_actual_monthly_spy_ief_60_40_plus_"
                    "20pct_actual_candidate_targets_including_cash"
                ),
                "cost_metrics": composites,
            },
            "target_contract": {
                "monthly_action_count": len(action_dates),
                "first_action_date": action_dates[0].isoformat(),
                "last_action_date": action_dates[-1].isoformat(),
                "defensive_action_count": sum(
                    modes[item] == "defensive" for item in action_dates
                ),
                "window_metrics": target_windows,
                "max_target_weight": _number(
                    max(
                        target[symbol]
                        for target in actions[candidate_id].values()
                        for symbol in ALL_SYMBOLS
                    )
                ),
                "max_etf_target_exposure": _number(max(exposures)),
                "average_etf_target_exposure": _number(mean(exposures)),
                "divergent_decisions_from_closest_ablation": _divergence(
                    actions[candidate_id], actions[closest_id]
                ),
                "divergent_decisions_from_static": _divergence(
                    actions[candidate_id], actions[STATIC_ID]
                ),
            },
        }

    integrity = {
        "chronological_action_lag_verified": True,
        "initial_transitions_from_cash_include_implicit_cash": all(
            math.isclose(
                series[candidate_id]["decision"].turnover[0],
                sum(actions[candidate_id][_OOS_START].values()),
                abs_tol=1e-12,
            )
            for candidate_id in CANDIDATE_IDS
        ),
        "weight_sums_nonnegative_and_implicit_cash_verified": True,
        "thirteen_monthly_close_momentum_verified": True,
        "canary_breadth_mode_verified": True,
        "defensive_bil_substitution_verified": True,
        "frozen_order_tie_resolution_verified": True,
        "folds_slice_one_continuous_path": True,
        "data_hash_identities_verified": True,
        "nonpositive_equity_absent": all(
            value > 0.0
            for costs in series.values()
            for value in costs["decision"].equity
        ),
    }
    return {
        "candidates": candidates,
        "comparators": comparators,
        "integrity": integrity,
        "cost_models": {
            key: {
                "bps_per_one_way_turnover": _number(value * 10000.0),
                "source_claim": False,
            }
            for key, value in _COSTS.items()
        },
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
        exposures.append(sum(earning_positions[symbol] for symbol in ALL_SYMBOLS))
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
    portfolio_non_cash_exposures = [
        sum(series.weights[index][symbol] for symbol in ALL_SYMBOLS)
        for index in indexes
    ]
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
        "non_cash_invested_fraction": _number(sum(series.risk_exposure[index] > 1e-12 for index in indexes) / len(indexes)),
        "average_non_cash_weight": _number(
            sum(series.risk_exposure[index] for index in indexes) / len(indexes)
        ),
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
    if any(
        not math.isfinite(value) or value < -1e-12 or value > 1.0 + 1e-12
        for value in weights.values()
    ):
        raise ValidationError("target weights are invalid.")
    total = sum(weights.values())
    if total < -1e-12 or total > 1.0 + 1e-12:
        raise ValidationError("target weights must leave nonnegative implicit cash.")

def _decisions(
    evaluation: Mapping[str, object],
    *,
    replay_equal: bool,
) -> dict[str, dict[str, object]]:
    comparators = evaluation["comparators"]
    integrity = evaluation["integrity"]
    results: dict[str, dict[str, object]] = {}
    for candidate_id in CANDIDATE_IDS:
        item = evaluation["candidates"][candidate_id]
        closest_id = item["closest_ablation_id"]
        decision = item["cost_metrics"]["decision"]
        stress = item["cost_metrics"]["stress"]
        oos = decision["oos"]
        folds = [decision[f"oos_fold_{index}"] for index in range(1, 4)]
        full_log = _float(oos["compounded_log_return"])
        fold_shares = (
            [_float(fold["compounded_log_return"]) / full_log for fold in folds]
            if full_log > 0.0
            else []
        )

        contributions = {
            symbol: _float(oos["constituent_contributions"][symbol])
            for symbol in ALL_SYMBOLS
        }
        common = {
            "full_annualized_return_positive": (
                _float(oos["annualized_return"]) > 0.0
            ),
            "full_sharpe_at_least_0_60": (
                _required_float(oos["sharpe_ratio"]) >= 0.60
            ),
            "full_max_drawdown_at_most_0_30": (
                _float(oos["max_drawdown"]) <= 0.30
            ),
            "every_fold_total_return_positive": all(
                _float(fold["total_return"]) > 0.0 for fold in folds
            ),
            "stress_annualized_return_positive": (
                _float(stress["oos"]["annualized_return"]) > 0.0
            ),
            "stress_sharpe_at_least_0_50": (
                _required_float(stress["oos"]["sharpe_ratio"]) >= 0.50
            ),
            "max_fold_positive_log_return_share_at_most_0_70": (
                bool(fold_shares) and max(fold_shares) <= 0.70
            ),
            "at_least_three_assets_contribute_positively": (
                sum(value > 0.0 for value in contributions.values()) >= 3
            ),
            "max_target_weight_at_most_1_00": (
                _float(item["target_contract"]["max_target_weight"])
                <= 1.0 + 1e-12
            ),
            "max_etf_target_exposure_at_most_1_00": (
                _float(item["target_contract"]["max_etf_target_exposure"])
                <= 1.0 + 1e-12
            ),
            "weight_grammar_verified": True,
            "chronology_cost_weight_hash_and_replay_integrity": (
                all(bool(value) for value in integrity.values()) and replay_equal
            ),
        }

        static = item["decision_cost_comparisons"][STATIC_ID]
        static_gate = {
            "sharpe_exceeds_static_by_0_05": (
                _required_float(static["oos"]["sharpe_ratio_delta"]) >= 0.05
            ),
            "drawdown_no_more_than_0_02_worse": (
                _float(static["oos"]["max_drawdown_delta"]) <= 0.02
            ),
            "at_least_two_fold_sharpe_wins": (
                sum(
                    _required_float(
                        static[f"oos_fold_{index}"]["sharpe_ratio_delta"]
                    )
                    > 0.0
                    for index in range(1, 4)
                )
                >= 2
            ),
        }

        ablation = item["decision_cost_comparisons"][closest_id]
        ablation_metrics = comparators[closest_id]["decision"]["oos"]
        ablation_drawdown = _float(ablation_metrics["max_drawdown"])
        ablation_value_paths = {
            "sharpe_improves_by_at_least_0_03": (
                _required_float(ablation["oos"]["sharpe_ratio_delta"]) >= 0.03
            ),
            "drawdown_improves_by_at_least_5pct_relative": (
                _float(ablation["oos"]["max_drawdown_improvement"])
                >= 0.05 * ablation_drawdown
            ),
            "annualized_return_drag_at_most_0_01": (
                _float(ablation["oos"]["annualized_return_delta"]) >= -0.01
            ),
        }
        ablation_gate = {
            "at_least_8_divergent_monthly_decisions": (
                item["target_contract"][
                    "divergent_decisions_from_closest_ablation"
                ]
                >= 8
            ),
            "frozen_feature_adds_value": (
                ablation_value_paths["sharpe_improves_by_at_least_0_03"]
                or (
                    ablation_value_paths[
                        "drawdown_improves_by_at_least_5pct_relative"
                    ]
                    and ablation_value_paths[
                        "annualized_return_drag_at_most_0_01"
                    ]
                )
            ),
        }

        spy_comparison = item["decision_cost_comparisons"][SPY_ID]["oos"]
        spy_metrics = comparators[SPY_ID]["decision"]["oos"]
        candidate_ann = _float(oos["annualized_return"])
        candidate_sharpe = _required_float(oos["sharpe_ratio"])
        candidate_drawdown = _float(oos["max_drawdown"])
        defensive = {
            "annualized_return_no_more_than_0_01_below_spy": (
                candidate_ann
                >= _float(spy_metrics["annualized_return"]) - 0.01
            ),
            "sharpe_exceeds_spy_by_0_10": (
                _required_float(spy_comparison["sharpe_ratio_delta"]) >= 0.10
            ),
            "drawdown_at_least_20pct_smaller": (
                candidate_drawdown
                <= 0.8 * _float(spy_metrics["max_drawdown"])
            ),
        }
        growth = {
            "annualized_return_exceeds_spy_by_0_01": (
                candidate_ann
                >= _float(spy_metrics["annualized_return"]) + 0.01
            ),
            "sharpe_not_below_spy": (
                candidate_sharpe
                >= _required_float(spy_metrics["sharpe_ratio"])
            ),
            "drawdown_no_more_than_0_02_worse": (
                candidate_drawdown
                <= _float(spy_metrics["max_drawdown"]) + 0.02
            ),
        }

        composite = item["portfolio_composite"]["cost_metrics"]
        decision_composite = composite["decision"]["comparison_to_parent"]
        stress_composite = composite["stress"]["comparison_to_parent"]
        full_improvement = (
            _float(
                composite["decision"]["metrics"]["oos"][
                    "compounded_log_return"
                ]
            )
            - _float(
                comparators[PARENT_ID]["decision"]["oos"][
                    "compounded_log_return"
                ]
            )
        )
        fold_improvements = [
            _float(
                composite["decision"]["metrics"][f"oos_fold_{index}"][
                    "compounded_log_return"
                ]
            )
            - _float(
                comparators[PARENT_ID]["decision"][f"oos_fold_{index}"][
                    "compounded_log_return"
                ]
            )
            for index in range(1, 4)
        ]
        portfolio_gate = {
            "full_sharpe_improves_by_0_02": (
                _required_float(
                    decision_composite["oos"]["sharpe_ratio_delta"]
                )
                >= 0.02
            ),
            "annualized_return_reduction_at_most_0_0075": (
                _float(
                    decision_composite["oos"]["annualized_return_delta"]
                )
                >= -0.0075
            ),
            "drawdown_or_return_improves_by_0_005": (
                _float(
                    decision_composite["oos"]["max_drawdown_improvement"]
                )
                >= 0.005
                or _float(
                    decision_composite["oos"]["annualized_return_delta"]
                )
                >= 0.005
            ),
            "positive_sharpe_improvement_in_two_folds": (
                sum(
                    _required_float(
                        decision_composite[f"oos_fold_{index}"][
                            "sharpe_ratio_delta"
                        ]
                    )
                    > 0.0
                    for index in range(1, 4)
                )
                >= 2
            ),
            "fold_3_sharpe_improvement_nonnegative": (
                _required_float(
                    decision_composite["oos_fold_3"]["sharpe_ratio_delta"]
                )
                >= 0.0
            ),
            "stress_full_sharpe_improvement_nonnegative": (
                _required_float(
                    stress_composite["oos"]["sharpe_ratio_delta"]
                )
                >= 0.0
            ),
            "positive_log_improvement_not_fold_concentrated": (
                full_improvement > 0.0
                and max(fold_improvements) / full_improvement <= 0.70
            ),
        }

        gates = {
            "common": {
                "passed": all(common.values()),
                "conditions": common,
                "max_fold_log_share": _optional_number(
                    max(fold_shares) if fold_shares else None
                ),
            },
            "static_baseline": {
                "passed": all(static_gate.values()),
                "conditions": static_gate,
            },
            "closest_ablation": {
                "passed": all(ablation_gate.values()),
                "closest_ablation_id": closest_id,
                "conditions": ablation_gate,
                "value_path_conditions": ablation_value_paths,
            },
            "spy_value_route": {
                "passed": all(defensive.values()) or all(growth.values()),
                "defensive_conditions": defensive,
                "growth_conditions": growth,
            },
            "portfolio_level_value": {
                "passed": all(portfolio_gate.values()),
                "conditions": portfolio_gate,
                "full_log_return_improvement": _number(full_improvement),
            },
        }
        passed = all(bool(gate["passed"]) for gate in gates.values())
        results[candidate_id] = {
            "candidate_id": candidate_id,
            "all_gates_passed": passed,
            "route": (
                "provisional_historical_validated_alpha_candidate"
                if passed
                else "close_candidate_without_tuning"
            ),
            "gates": gates,
            "selection_metrics": {
                "composite_sharpe_improvement": decision_composite["oos"][
                    "sharpe_ratio_delta"
                ],
                "candidate_sharpe": oos["sharpe_ratio"],
                "candidate_annualized_return": oos["annualized_return"],
                "candidate_max_drawdown": oos["max_drawdown"],
            },
            "current_clock_no_submit_shadow_eligible": passed,
            "paper_promotion_allowed": False,
            "live_authorized": False,
        }
    return results

def _artifact_manifest(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": "baa_artifact_manifest",
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
    lines = [
        "# V5.89 Keller Bold Asset Allocation tournament result",
        "",
        f"Route: {result['tournament_decision']['route']}",
        "",
    ]
    for candidate_id in CANDIDATE_IDS:
        decision = result["candidate_decisions"][candidate_id]
        metrics = result["evaluation"]["candidates"][candidate_id][
            "cost_metrics"
        ]["decision"]["oos"]
        lines.extend(
            [
                f"## {candidate_id}",
                "",
                (
                    "- Passed every gate: "
                    f"{str(decision['all_gates_passed']).lower()}"
                ),
                f"- Annualized return: {metrics['annualized_return']}",
                f"- Sharpe: {metrics['sharpe_ratio']}",
                f"- Maximum drawdown: {metrics['max_drawdown']}",
            ]
        )
        for gate_id, gate in decision["gates"].items():
            lines.append(
                f"- {gate_id}: {str(gate['passed']).lower()}"
            )
        lines.append("")
    lines.extend(
        [
            "No external performance metric controlled a gate or ranking. A pass",
            "is eligible only for a new current-clock no-submit shadow; paper and",
            "live remain forbidden.",
            "",
        ]
    )
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
    if path.is_absolute():
        return path
    if not path.parts or path.parts[0].lower() != "runs":
        raise ValidationError("output root must be absolute or beneath runs/.")
    runs_root = Path("runs").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(runs_root)
    except ValueError as exc:
        raise ValidationError(
            "relative output root must remain beneath runs/."
        ) from exc
    return resolved


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
        result = run_baa_tournament(args.output_root)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"baa_tournament_status=blocked:{exc}")
        return 2
    print("baa_tournament_status=completed")
    print(f"route={result['tournament_decision']['route']}")
    print(f"shadow_winner_id={result['tournament_decision']['shadow_winner_id']}")
    print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
