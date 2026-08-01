"""Frozen V5.71 diversified ETF absolute-trend evaluation."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import stdev
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

__all__ = [
    "build_diversified_etf_absolute_trend_preregistration",
    "run_diversified_etf_absolute_trend",
]

PROTOCOL_ID = "v5_71_diversified_etf_absolute_trend_v1"
CANDIDATE_ID = "diversified_etf_absolute_trend_10m"
STATIC_EQUAL_WEIGHT_ID = "static_equal_weight"
SPY_BUY_AND_HOLD_ID = "spy_buy_and_hold"
SYMBOLS = ("SPY", "QQQ", "IWM", "TLT", "GLD")

_PROTOCOL = Path("docs/design/v5_71_diversified_etf_absolute_trend_preregistration.md")
_RECEIPT = Path("docs/design/v5_71_diversified_etf_absolute_trend_data_receipt.md")
_DATA = Path("runs/v5_71_diversified_etf_absolute_trend/canonical_data.csv")
_DATA_MANIFEST = Path(
    "runs/v5_71_diversified_etf_absolute_trend/data_acquisition/"
    "canonical_data_manifest.json"
)
_OUTPUT_ROOT = Path("runs/v5_71_diversified_etf_absolute_trend/evaluation")
_ENGINE = Path("src/algotrader/research/diversified_etf_absolute_trend.py")

_PROTOCOL_HASH = "afa4254ceac06f643fd51fd2df63364ce14a38f01ba8392e664d8e478bc57d17"
_RECEIPT_HASH = "ca782882cb499ea2e956fc36658df4f76f88fff06b4a69b293ced4a70c213525"
_DATA_HASH = "5e7a7da8519e37faa72787dc41c7e847e5749f74f9cd43dc8009cb2807b8e0ec"
_DATA_MANIFEST_HASH = "627119a769e38053c32ab7709f88672ab6dba5db9725cb4b2545a7bad77b177e"
_SYMBOL_HASHES = {
    "SPY": "9ba2d58f5c1c58096fd473eaad1ea370e6023c63b524a21d286e4d5effaef5fb",
    "QQQ": "8347790292da6048d954fec5276a2c80f6d4dbbfab1458c2cca3b41deb5d3713",
    "IWM": "30fcd9f37609089337a4454ca248d097851179e8fa646489af10b132746fae7d",
    "TLT": "5ce0e67de4c1be5e5e85b292444bc5aac0ce937587a7fc60ca00e402f67dbfae",
    "GLD": "1986eef43145ea6ae1f51cbc7decfb9d711bd740b18d207bd6ecc50a4e86f88e",
}

_DATA_START = date(2004, 11, 18)
_DATA_END = date(2026, 7, 31)
_TRAIN_START = date(2005, 9, 1)
_TRAIN_END = date(2015, 12, 31)
_OOS_START = date(2016, 1, 4)
_OOS_END = date(2026, 7, 31)
_WINDOWS = (
    ("training", _TRAIN_START, _TRAIN_END, "training"),
    ("oos", _OOS_START, _OOS_END, "out_of_sample"),
    ("oos_fold_1", date(2016, 1, 4), date(2019, 6, 28), "walk_forward"),
    ("oos_fold_2", date(2019, 7, 1), date(2022, 12, 30), "walk_forward"),
    ("oos_fold_3", date(2023, 1, 3), date(2026, 7, 31), "walk_forward"),
)
_REQUIRED_SESSION_COUNTS = {
    "all": 5458,
    "training": 2601,
    "oos": 2659,
    "oos_fold_1": 878,
    "oos_fold_2": 884,
    "oos_fold_3": 897,
}
_ZERO = Decimal("0")
_ONE = Decimal("1")
_SLEEVE_WEIGHT = Decimal("0.20")
_WEIGHT_TOLERANCE = Decimal("0.000000000001")
_COSTS = {
    "zero": Decimal("0"),
    "moderate": Decimal("2") / Decimal("10000"),
    "severe": Decimal("5") / Decimal("10000"),
}


@dataclass(frozen=True, slots=True)
class _AlignedData:
    dates: tuple[date, ...]
    prices: Mapping[str, tuple[Decimal, ...]]
    data_sha256: str
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class _Record:
    date: date
    strategy_return: Decimal
    turnover: Decimal
    exposure: Decimal
    weights_after_close: Mapping[str, Decimal]
    contributions: Mapping[str, Decimal]


@dataclass(frozen=True, slots=True)
class _Simulation:
    records: tuple[_Record, ...]


def build_diversified_etf_absolute_trend_preregistration() -> dict[str, object]:
    """Build the committed outcome-blind contract without reading market data."""

    _validate_tracked_dependencies()
    return {
        "record_type": "diversified_etf_absolute_trend_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "candidate_id": CANDIDATE_ID,
        "methodology_label": "repository_proxy_not_faber_replication",
        "symbols": list(SYMBOLS),
        "lookback_months": 10,
        "sleeve_weight": _text(_SLEEVE_WEIGHT),
        "signal": "month_end_adjusted_close_strictly_above_trailing_10_month_sma",
        "action_lag": "apply_after_next_common_session_close",
        "cash_accrual": "zero_return_placeholder",
        "cost_bps_per_one_way_turnover": {
            name: _text(rate * Decimal("10000")) for name, rate in _COSTS.items()
        },
        "windows": [
            {
                "window_id": window_id,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "role": role,
            }
            for window_id, start, end, role in _WINDOWS
        ],
        "protocol_sha256": _PROTOCOL_HASH,
        "receipt_sha256": _RECEIPT_HASH,
        "data_sha256": _DATA_HASH,
        "data_manifest_sha256": _DATA_MANIFEST_HASH,
        "parameter_search_performed": False,
        "source_metrics_used": False,
        "terminal_routes": [
            "preview_review",
            "close_diversified_etf_absolute_trend",
        ],
        "paper_promotion_allowed": False,
        "safety": _safety(),
    }


def run_diversified_etf_absolute_trend(
    output_root: Path | str = _OUTPUT_ROOT,
) -> dict[str, object]:
    """Run the exact frozen evaluation and write deterministic local artifacts."""

    preregistration = build_diversified_etf_absolute_trend_preregistration()
    data = _load_aligned_data()
    schedules = _target_schedules(data)
    first_core = _build_core_result(data, schedules)
    second_core = _build_core_result(data, schedules)
    if _json_bytes(first_core) != _json_bytes(second_core):
        raise ValidationError("independent in-memory replay was not byte-identical.")
    gates = _evaluate_gates(first_core)
    all_passed = all(bool(item["passed"]) for item in gates.values())
    route = "preview_review" if all_passed else "close_diversified_etf_absolute_trend"
    result = {
        "record_type": "diversified_etf_absolute_trend_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": preregistration,
        "data_admission": {
            "data_sha256": data.data_sha256,
            "manifest_sha256": data.manifest_sha256,
            "receipt_sha256": _RECEIPT_HASH,
            "common_session_count": len(data.dates),
            "first_session": data.dates[0].isoformat(),
            "last_session": data.dates[-1].isoformat(),
            "symbol_sha256": dict(_SYMBOL_HASHES),
            "adjusted_close_basis": "adjusted_close_price_return",
        },
        "evaluation": first_core,
        "gates": gates,
        "terminal_decision": {
            "candidate_id": CANDIDATE_ID,
            "all_gates_passed": all_passed,
            "route": route,
            "preview_review_allowed": all_passed,
            "failure_closes_exact_candidate": not all_passed,
            "paper_promotion_allowed": False,
        },
        "safety": _safety(),
    }
    root = _path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)
    preregistration_path = root / "preregistration.json"
    result_path = root / "evaluation_results.json"
    summary_path = root / "evaluation_summary.md"
    _write_json(preregistration_path, preregistration)
    _write_json(result_path, result)
    _write_text(summary_path, _summary(result))
    manifest = {
        "record_type": "diversified_etf_absolute_trend_artifact_manifest",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "artifacts": [_artifact(path) for path in (preregistration_path, result_path, summary_path)],
        "inputs": {
            "protocol_sha256": _PROTOCOL_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "data_sha256": _DATA_HASH,
            "data_manifest_sha256": _DATA_MANIFEST_HASH,
            "engine_sha256": _hash(_ENGINE),
        },
        "safety": _safety(),
    }
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)
    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_sha256"] = _hash(manifest_path)
    return completed


def _load_aligned_data() -> _AlignedData:
    data_hash = _hash(_DATA)
    manifest_hash = _hash(_DATA_MANIFEST)
    if data_hash != _DATA_HASH:
        raise ValidationError("canonical data SHA-256 mismatch.")
    if manifest_hash != _DATA_MANIFEST_HASH:
        raise ValidationError("canonical data manifest SHA-256 mismatch.")
    manifest = _load_json(_DATA_MANIFEST)
    if manifest.get("valid_symbols") != list(SYMBOLS):
        raise ValidationError("manifest valid_symbols do not match the frozen universe.")
    if manifest.get("refresh_required_symbols") != []:
        raise ValidationError("manifest reports refresh-required symbols.")
    if manifest.get("combined_output_sha256") != _DATA_HASH:
        raise ValidationError("manifest combined data hash mismatch.")
    if manifest.get("adjusted_close_basis") != "adjusted_close_price_return":
        raise ValidationError("manifest adjusted-close basis mismatch.")
    prices_by_symbol: dict[str, dict[date, Decimal]] = {}
    for symbol in SYMBOLS:
        loaded = load_local_daily_bars_csv(_DATA, symbol=symbol, as_of=_DATA_END)
        bars = loaded.usable_bars
        if len(bars) != _REQUIRED_SESSION_COUNTS["all"]:
            raise ValidationError(f"{symbol} row count does not match the receipt.")
        if bars[0].date != _DATA_START or bars[-1].date != _DATA_END:
            raise ValidationError(f"{symbol} coverage does not match the receipt.")
        prices_by_symbol[symbol] = {bar.date: bar.adjusted_close for bar in bars}
    common = set(prices_by_symbol[SYMBOLS[0]])
    for symbol in SYMBOLS[1:]:
        common.intersection_update(prices_by_symbol[symbol])
    dates = tuple(sorted(common))
    if len(dates) != _REQUIRED_SESSION_COUNTS["all"]:
        raise ValidationError("common-session count does not match the receipt.")
    if dates[0] != _DATA_START or dates[-1] != _DATA_END:
        raise ValidationError("common-session coverage does not match the receipt.")
    if any(len(prices_by_symbol[symbol]) != len(dates) for symbol in SYMBOLS):
        raise ValidationError("symbol sessions are not exactly aligned.")
    prices = {
        symbol: tuple(prices_by_symbol[symbol][on_date] for on_date in dates)
        for symbol in SYMBOLS
    }
    _validate_windows(dates)
    return _AlignedData(dates, prices, data_hash, manifest_hash)


def _validate_windows(dates: tuple[date, ...]) -> None:
    for window_id, start, end, _role in _WINDOWS:
        observed = tuple(item for item in dates if start <= item <= end)
        if len(observed) != _REQUIRED_SESSION_COUNTS[window_id]:
            raise ValidationError(f"{window_id} session count does not match receipt.")
        if observed[0] != start or observed[-1] != end:
            raise ValidationError(f"{window_id} endpoints do not match protocol.")
    oos = tuple(item for item in dates if _OOS_START <= item <= _OOS_END)
    folds = tuple(
        item
        for window_id, start, end, _role in _WINDOWS
        if window_id.startswith("oos_fold_")
        for item in dates
        if start <= item <= end
    )
    if folds != oos:
        raise ValidationError("walk-forward folds do not exactly partition OOS.")


def _target_schedules(
    data: _AlignedData,
) -> dict[str, Mapping[date, Mapping[str, Decimal]]]:
    month_end_indexes = tuple(
        index
        for index, on_date in enumerate(data.dates)
        if index == len(data.dates) - 1
        or (data.dates[index + 1].year, data.dates[index + 1].month)
        != (on_date.year, on_date.month)
    )
    candidate: dict[date, Mapping[str, Decimal]] = {}
    for month_position, signal_index in enumerate(month_end_indexes):
        if month_position < 9 or signal_index + 1 >= len(data.dates):
            continue
        action_date = data.dates[signal_index + 1]
        target: dict[str, Decimal] = {}
        lookback_indexes = month_end_indexes[month_position - 9 : month_position + 1]
        for symbol in SYMBOLS:
            values = tuple(data.prices[symbol][index] for index in lookback_indexes)
            average = sum(values, _ZERO) / Decimal("10")
            target[symbol] = _SLEEVE_WEIGHT if values[-1] > average else _ZERO
        candidate[action_date] = target
    if not candidate or next(iter(candidate)) != _TRAIN_START:
        raise ValidationError("first eligible action date does not match protocol.")
    equal_weight = {symbol: _SLEEVE_WEIGHT for symbol in SYMBOLS}
    static = {on_date: dict(equal_weight) for on_date in candidate}
    spy = {
        next(iter(candidate)): {
            symbol: (_ONE if symbol == "SPY" else _ZERO) for symbol in SYMBOLS
        }
    }
    return {
        CANDIDATE_ID: candidate,
        STATIC_EQUAL_WEIGHT_ID: static,
        SPY_BUY_AND_HOLD_ID: spy,
    }


def _build_core_result(
    data: _AlignedData,
    schedules: Mapping[str, Mapping[date, Mapping[str, Decimal]]],
) -> dict[str, object]:
    metrics: dict[str, object] = {}
    for cost_name, cost_rate in _COSTS.items():
        strategies: dict[str, object] = {}
        for strategy_id, schedule in schedules.items():
            simulation = _simulate(data, schedule, cost_rate)
            strategies[strategy_id] = {
                window_id: _metrics(simulation, window_id, start, end, role)
                for window_id, start, end, role in _WINDOWS
            }
        metrics[cost_name] = strategies
    moderate = metrics["moderate"]
    comparisons = {
        "static_equal_weight": {
            window_id: _compare(
                moderate[CANDIDATE_ID][window_id],
                moderate[STATIC_EQUAL_WEIGHT_ID][window_id],
            )
            for window_id, *_rest in _WINDOWS
        },
        "spy_buy_and_hold": {
            window_id: _compare(
                moderate[CANDIDATE_ID][window_id],
                moderate[SPY_BUY_AND_HOLD_ID][window_id],
            )
            for window_id, *_rest in _WINDOWS
        },
    }
    return {
        "cost_models": {
            name: {
                "total_cost_bps_per_one_way_turnover": _text(rate * Decimal("10000")),
                "local_assumption_not_source_claim": True,
            }
            for name, rate in _COSTS.items()
        },
        "metrics": metrics,
        "moderate_cost_comparisons": comparisons,
        "independent_in_memory_replay_equal": True,
        "parameter_search_performed": False,
        "source_metrics_used": False,
    }


def _simulate(
    data: _AlignedData,
    schedule: Mapping[date, Mapping[str, Decimal]],
    cost_rate: Decimal,
) -> _Simulation:
    weights = {symbol: _ZERO for symbol in SYMBOLS}
    records: list[_Record] = []
    for index in range(1, len(data.dates)):
        on_date = data.dates[index]
        asset_returns = {
            symbol: (data.prices[symbol][index] / data.prices[symbol][index - 1]) - _ONE
            for symbol in SYMBOLS
        }
        exposure = sum(weights.values(), _ZERO)
        contributions = {
            symbol: weights[symbol] * asset_returns[symbol] for symbol in SYMBOLS
        }
        gross_return = sum(contributions.values(), _ZERO)
        growth = _ONE + gross_return
        if growth <= _ZERO:
            raise ValidationError("portfolio growth became nonpositive.")
        drifted = {
            symbol: weights[symbol] * (_ONE + asset_returns[symbol]) / growth
            for symbol in SYMBOLS
        }
        turnover = _ZERO
        if on_date in schedule:
            target = dict(schedule[on_date])
            _validate_weights(target)
            turnover = sum(
                (abs(target[symbol] - drifted[symbol]) for symbol in SYMBOLS),
                _ZERO,
            )
            weights_after = target
        else:
            weights_after = drifted
        cost_fraction = turnover * cost_rate
        if cost_fraction >= _ONE:
            raise ValidationError("modeled transaction cost consumed the portfolio.")
        net_return = growth * (_ONE - cost_fraction) - _ONE
        records.append(
            _Record(
                date=on_date,
                strategy_return=net_return,
                turnover=turnover,
                exposure=exposure,
                weights_after_close=weights_after,
                contributions=contributions,
            )
        )
        weights = weights_after
    return _Simulation(tuple(records))


def _metrics(
    simulation: _Simulation,
    window_id: str,
    start: date,
    end: date,
    role: str,
) -> dict[str, object]:
    records = tuple(record for record in simulation.records if start <= record.date <= end)
    if len(records) != _REQUIRED_SESSION_COUNTS[window_id]:
        raise ValidationError(f"{window_id} simulation session count mismatch.")
    equity = _ONE
    peak = _ONE
    worst_drawdown = _ZERO
    returns: list[Decimal] = []
    turnover = _ZERO
    invested = 0
    exposure_sum = _ZERO
    contributions = {symbol: _ZERO for symbol in SYMBOLS}
    held: set[str] = set()
    for record in records:
        equity *= _ONE + record.strategy_return
        if equity <= _ZERO:
            raise ValidationError("window equity became nonpositive.")
        peak = max(peak, equity)
        worst_drawdown = min(worst_drawdown, equity / peak - _ONE)
        returns.append(record.strategy_return)
        turnover += record.turnover
        exposure_sum += record.exposure
        if record.exposure > _WEIGHT_TOLERANCE:
            invested += 1
        for symbol in SYMBOLS:
            contributions[symbol] += record.contributions[symbol]
            if record.weights_after_close[symbol] > _WEIGHT_TOLERANCE:
                held.add(symbol)
    total_return = equity - _ONE
    annualized_return = _annualized_return(total_return, records[0].date, records[-1].date)
    volatility = _annualized_volatility(tuple(returns))
    sharpe = None if volatility is None or volatility <= _ZERO else annualized_return / volatility
    day_count = (records[-1].date - records[0].date).days
    annualized_turnover = turnover * Decimal("365.25") / Decimal(day_count)
    absolute_total = sum((abs(value) for value in contributions.values()), _ZERO)
    shares = {
        symbol: None if absolute_total == _ZERO else abs(value) / absolute_total
        for symbol, value in contributions.items()
    }
    max_share = max((value for value in shares.values() if value is not None), default=None)
    positive = sorted(symbol for symbol, value in contributions.items() if value > _ZERO)
    return {
        "window_id": window_id,
        "role": role,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "session_count": len(records),
        "total_return": _text(total_return),
        "annualized_return": _text(annualized_return),
        "annualized_volatility": _optional_text(volatility),
        "sharpe_ratio": _optional_text(sharpe),
        "max_drawdown": _text(-worst_drawdown),
        "one_way_turnover": _text(turnover),
        "annualized_one_way_turnover": _text(annualized_turnover),
        "invested_session_fraction": _text(Decimal(invested) / Decimal(len(records))),
        "average_gross_exposure": _text(exposure_sum / Decimal(len(records))),
        "constituent_contributions": {
            symbol: _text(value) for symbol, value in contributions.items()
        },
        "absolute_contribution_shares": {
            symbol: _optional_text(value) for symbol, value in shares.items()
        },
        "symbols_held": sorted(held),
        "positive_contribution_symbols": positive,
        "max_absolute_contribution_share": _optional_text(max_share),
    }


def _compare(candidate: Mapping[str, object], baseline: Mapping[str, object]) -> dict[str, object]:
    candidate_sharpe = _optional_decimal(candidate["sharpe_ratio"])
    baseline_sharpe = _optional_decimal(baseline["sharpe_ratio"])
    return {
        "annualized_return_delta": _text(
            _decimal(candidate["annualized_return"])
            - _decimal(baseline["annualized_return"])
        ),
        "max_drawdown_delta": _text(
            _decimal(candidate["max_drawdown"])
            - _decimal(baseline["max_drawdown"])
        ),
        "max_drawdown_improvement": _text(
            _decimal(baseline["max_drawdown"])
            - _decimal(candidate["max_drawdown"])
        ),
        "sharpe_ratio_delta": _optional_text(
            None
            if candidate_sharpe is None or baseline_sharpe is None
            else candidate_sharpe - baseline_sharpe
        ),
    }


def _evaluate_gates(core: Mapping[str, object]) -> dict[str, dict[str, object]]:
    metrics = core["metrics"]
    moderate = metrics["moderate"][CANDIDATE_ID]
    severe = metrics["severe"][CANDIDATE_ID]
    comparisons = core["moderate_cost_comparisons"]
    oos = moderate["oos"]
    data_replay = bool(core["independent_in_memory_replay_equal"])
    viability_conditions = {
        "oos_total_return_positive": _decimal(oos["total_return"]) > _ZERO,
        "oos_annualized_return_positive": _decimal(oos["annualized_return"]) > _ZERO,
        "oos_max_drawdown_at_most_0_30": _decimal(oos["max_drawdown"]) <= Decimal("0.30"),
        "all_fold_returns_positive": all(
            _decimal(moderate[f"oos_fold_{index}"]["total_return"]) > _ZERO
            for index in range(1, 4)
        ),
        "all_fold_drawdowns_at_most_0_25": all(
            _decimal(moderate[f"oos_fold_{index}"]["max_drawdown"]) <= Decimal("0.25")
            for index in range(1, 4)
        ),
    }
    static_oos = comparisons["static_equal_weight"]["oos"]
    static_sharpe = _required_optional_decimal(
        static_oos["sharpe_ratio_delta"], "static OOS Sharpe delta"
    )
    return_path = (
        _decimal(static_oos["annualized_return_delta"]) >= _ZERO
        and _decimal(static_oos["max_drawdown_delta"]) <= Decimal("0.02")
        and static_sharpe >= Decimal("-0.05")
    )
    risk_path = (
        _decimal(static_oos["annualized_return_delta"]) >= Decimal("-0.02")
        and _decimal(static_oos["max_drawdown_improvement"]) >= Decimal("0.05")
        and static_sharpe >= Decimal("0.10")
    )
    fold_static_sharpe_passes = sum(
        _required_optional_decimal(
            comparisons["static_equal_weight"][f"oos_fold_{index}"]["sharpe_ratio_delta"],
            f"static fold {index} Sharpe delta",
        )
        >= _ZERO
        for index in range(1, 4)
    )
    static_conditions = {
        "return_dominant_path": return_path,
        "risk_dominant_path": risk_path,
        "one_full_oos_value_path": return_path or risk_path,
        "at_least_two_fold_sharpe_wins": fold_static_sharpe_passes >= 2,
    }
    spy_oos = comparisons["spy_buy_and_hold"]["oos"]
    spy_sharpe = _required_optional_decimal(spy_oos["sharpe_ratio_delta"], "SPY OOS Sharpe delta")
    spy_conditions = {
        "sharpe_delta_nonnegative": spy_sharpe >= _ZERO,
        "drawdown_improvement_at_least_0_05": (
            _decimal(spy_oos["max_drawdown_improvement"]) >= Decimal("0.05")
        ),
        "annualized_return_delta_at_least_minus_0_03": (
            _decimal(spy_oos["annualized_return_delta"]) >= Decimal("-0.03")
        ),
    }
    severe_oos = severe["oos"]
    friction_conditions = {
        "severe_oos_total_return_positive": _decimal(severe_oos["total_return"]) > _ZERO,
        "severe_annualized_return_degradation_at_most_0_005": (
            _decimal(oos["annualized_return"])
            - _decimal(severe_oos["annualized_return"])
            <= Decimal("0.005")
        ),
        "moderate_annualized_turnover_at_most_4": (
            _decimal(oos["annualized_one_way_turnover"]) <= Decimal("4")
        ),
    }
    max_share = _required_optional_decimal(
        oos["max_absolute_contribution_share"], "OOS max contribution share"
    )
    diversification_conditions = {
        "all_five_symbols_held": oos["symbols_held"] == sorted(SYMBOLS),
        "at_least_three_positive_contributors": (
            len(oos["positive_contribution_symbols"]) >= 3
        ),
        "max_contribution_share_at_most_0_60": max_share <= Decimal("0.60"),
    }
    return {
        "data_and_replay_integrity": {
            "passed": data_replay,
            "conditions": {"independent_in_memory_replay_byte_identical": data_replay},
        },
        "oos_viability": {
            "passed": all(viability_conditions.values()),
            "conditions": viability_conditions,
        },
        "static_equal_weight_value": {
            "passed": static_conditions["one_full_oos_value_path"]
            and static_conditions["at_least_two_fold_sharpe_wins"],
            "conditions": static_conditions,
            "full_oos_comparison": static_oos,
            "fold_sharpe_pass_count": fold_static_sharpe_passes,
        },
        "spy_value": {
            "passed": all(spy_conditions.values()),
            "conditions": spy_conditions,
            "full_oos_comparison": spy_oos,
        },
        "friction_stability": {
            "passed": all(friction_conditions.values()),
            "conditions": friction_conditions,
        },
        "diversification": {
            "passed": all(diversification_conditions.values()),
            "conditions": diversification_conditions,
        },
    }


def _validate_tracked_dependencies() -> None:
    for path, expected, label in (
        (_PROTOCOL, _PROTOCOL_HASH, "protocol"),
        (_RECEIPT, _RECEIPT_HASH, "data receipt"),
    ):
        if _hash(path) != expected:
            raise ValidationError(f"{label} SHA-256 mismatch.")


def _validate_weights(weights: Mapping[str, Decimal]) -> None:
    if set(weights) != set(SYMBOLS):
        raise ValidationError("target weights must contain the exact frozen universe.")
    if any(value < _ZERO or value > _ONE for value in weights.values()):
        raise ValidationError("target weights must be between zero and one.")
    if sum(weights.values(), _ZERO) > _ONE + _WEIGHT_TOLERANCE:
        raise ValidationError("target weights cannot exceed full investment.")


def _annualized_return(total_return: Decimal, start: date, end: date) -> Decimal:
    day_count = (end - start).days
    if day_count <= 0 or _ONE + total_return <= _ZERO:
        raise ValidationError("annualized return requires a positive span and equity.")
    return Decimal(str(math.pow(float(_ONE + total_return), 365.25 / day_count) - 1.0))


def _annualized_volatility(returns: tuple[Decimal, ...]) -> Decimal | None:
    if len(returns) < 2:
        return None
    return Decimal(str(stdev(float(value) for value in returns) * math.sqrt(252.0)))


def _summary(result: Mapping[str, object]) -> str:
    oos = result["evaluation"]["metrics"]["moderate"][CANDIDATE_ID]["oos"]
    static = result["evaluation"]["moderate_cost_comparisons"]["static_equal_weight"]["oos"]
    spy = result["evaluation"]["moderate_cost_comparisons"]["spy_buy_and_hold"]["oos"]
    lines = [
        "# V5.71 Diversified ETF Absolute-Trend Evaluation",
        "",
        f"- Terminal route: `{result['terminal_decision']['route']}`",
        f"- All gates passed: `{str(result['terminal_decision']['all_gates_passed']).lower()}`",
        "- Methodology label: `repository_proxy_not_faber_replication`",
        "- Paper promotion allowed: `false`",
        "",
        "## Moderate-cost full OOS",
        "",
        f"- Total return: `{oos['total_return']}`",
        f"- Annualized return: `{oos['annualized_return']}`",
        f"- Maximum drawdown: `{oos['max_drawdown']}`",
        f"- Sharpe ratio: `{oos['sharpe_ratio']}`",
        f"- Annualized one-way turnover: `{oos['annualized_one_way_turnover']}`",
        f"- Static-EW annualized-return delta: `{static['annualized_return_delta']}`",
        f"- Static-EW Sharpe delta: `{static['sharpe_ratio_delta']}`",
        f"- SPY annualized-return delta: `{spy['annualized_return_delta']}`",
        f"- SPY Sharpe delta: `{spy['sharpe_ratio_delta']}`",
        "",
        "## Gates",
        "",
    ]
    for gate_id, gate in result["gates"].items():
        lines.append(f"- `{gate_id}`: `{str(gate['passed']).lower()}`")
    lines.extend(
        [
            "",
            "No source performance metric controlled this result. No broker, paper, or live action occurred.",
            "",
        ]
    )
    return "\n".join(lines)


def _safety() -> dict[str, object]:
    return {
        "offline_replay": True,
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
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _hash(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str) and value.strip() and "://" not in value:
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a local path.")
    return path


def _decimal(value: object) -> Decimal:
    if not isinstance(value, (str, int, Decimal)):
        raise ValidationError("metric value must be decimal-compatible.")
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValidationError("metric value must be decimal-compatible.") from exc


def _optional_decimal(value: object) -> Decimal | None:
    return None if value is None else _decimal(value)


def _required_optional_decimal(value: object, label: str) -> Decimal:
    parsed = _optional_decimal(value)
    if parsed is None:
        raise ValidationError(f"{label} is required.")
    return parsed


def _text(value: Decimal) -> str:
    return format(value, "f")


def _optional_text(value: Decimal | None) -> str | None:
    return None if value is None else _text(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="diversified-etf-absolute-trend")
    parser.add_argument("--output-root", default=str(_OUTPUT_ROOT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = run_diversified_etf_absolute_trend(args.output_root)
    except ValidationError as exc:
        print(f"diversified_etf_absolute_trend_status=blocked:{exc}")
        return 2
    if args.format == "json":
        print(json.dumps(_json_safe(result), sort_keys=True, separators=(",", ":")))
    else:
        print("diversified_etf_absolute_trend_status=completed")
        print(f"terminal_route={result['terminal_decision']['route']}")
        print(f"all_gates_passed={str(result['terminal_decision']['all_gates_passed']).lower()}")
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
