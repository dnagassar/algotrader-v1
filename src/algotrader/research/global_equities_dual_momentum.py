"""Frozen V5.73 global-equities dual-momentum ETF-proxy evaluation."""

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

__all__ = ["build_global_equities_dual_momentum_preregistration", "run_global_equities_dual_momentum"]

PROTOCOL_ID = "v5_73_global_equities_dual_momentum_v1"
CANDIDATE_ID = "global_equities_dual_momentum_12m_proxy"
SYMBOLS = ("SPY", "VEU", "BIL", "AGG", "QQQ", "IWM", "TLT", "GLD")
CORE_SYMBOLS = ("SPY", "QQQ", "IWM", "TLT", "GLD")

_PROTOCOL = Path("docs/design/v5_73_global_equities_dual_momentum_preregistration.md")
_RECEIPT = Path("docs/design/v5_73_global_equities_dual_momentum_data_receipt.md")
_BASE_DATA = Path("runs/v5_72_primary_source_alpha_tournament/canonical_data.csv")
_BASE_MANIFEST = Path("runs/v5_72_primary_source_alpha_tournament/canonical_data_manifest.json")
_ROOT = Path("runs/v5_73_global_equities_dual_momentum")
_NEW_PATHS = {
    symbol: _ROOT / "canonical" / f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv"
    for symbol in ("VEU", "BIL", "AGG")
}
_OUTPUT = _ROOT / "evaluation"
_ENGINE = Path("src/algotrader/research/global_equities_dual_momentum.py")

_PROTOCOL_HASH = "27de22520bccd1ac61063717ec718ed0bda6aef6ed8233d21846e60450a642d0"
_RECEIPT_HASH = "0c5c2126ad954efffc5eba7c7bf9500f7b53747f1d3febce44e1e845a1a08818"
_BASE_DATA_HASH = "5a4d8c0fea3ca879011239067f76c6375012f30835e0d579f329f018176b77e2"
_BASE_MANIFEST_HASH = "82c1edc7192b9f63b057a4846a0d0540958d9939f6dbabddd793899ca797f0ab"
_SPY_NORMALIZED_HASH = "ac5fc6752e7aedd8e922782dbd780e53cbac52a0fb8a38f50742e6c803a31a77"
_NEW_HASHES = {
    "VEU": "8c5ca3ee9d5d9a696c87cbd7d61b13c33b4a2010fe56becc08aeab11971cb5b4",
    "BIL": "8d45ab5e0a0ebeeb8447b2e12b368f631b91fe97bd3b3fdc736bda391b8753c5",
    "AGG": "1140e1fd5a23a0919cff020e4f53e041d415bcde179a88146bd0aced4b86fc7a",
}
_START = date(2007, 6, 1)
_END = date(2026, 7, 31)
_OOS_START = date(2013, 1, 2)
_WINDOWS = (
    ("oos", _OOS_START, _END),
    ("oos_fold_1", date(2013, 1, 2), date(2017, 6, 30)),
    ("oos_fold_2", date(2017, 7, 3), date(2022, 1, 3)),
    ("oos_fold_3", date(2022, 1, 4), _END),
)
_COUNTS = {"all": 4822, "oos": 3415, "oos_fold_1": 1133, "oos_fold_2": 1135, "oos_fold_3": 1147}
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


def build_global_equities_dual_momentum_preregistration() -> dict[str, object]:
    _validate_tracked()
    return {
        "record_type": "global_equities_dual_momentum_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "candidate_id": CANDIDATE_ID,
        "methodology_label": "repository_etf_proxy_not_antonacci_index_replication",
        "signal": "12_complete_month_relative_SPY_VEU_then_strict_winner_vs_BIL_else_AGG",
        "action_lag": "first_common_session_after_month_end",
        "symbols": ["SPY", "VEU", "BIL", "AGG"],
        "cost_bps_per_one_way_turnover": {name: _number(rate * 10000.0) for name, rate in _COSTS.items()},
        "protocol_sha256": _PROTOCOL_HASH,
        "receipt_sha256": _RECEIPT_HASH,
        "parameter_search_performed": False,
        "source_metrics_used": False,
        "maximum_route": "new_untouched_no_submit_shadow",
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "safety": _safety(),
    }


def run_global_equities_dual_momentum(output_root: Path | str = _OUTPUT) -> dict[str, object]:
    preregistration = build_global_equities_dual_momentum_preregistration()
    data = _load_data()
    actions = _actions(data)
    first = _evaluate(data, actions)
    second = _evaluate(data, actions)
    if _json_bytes(first) != _json_bytes(second):
        raise ValidationError("independent in-memory replay was not byte-identical.")
    gates = _gates(first)
    passed = all(gate["passed"] for gate in gates.values())
    result: dict[str, object] = {
        "record_type": "global_equities_dual_momentum_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": preregistration,
        "data_admission": {
            "base_data_sha256": _BASE_DATA_HASH,
            "base_manifest_sha256": _BASE_MANIFEST_HASH,
            "spy_normalized_symbol_sha256": _SPY_NORMALIZED_HASH,
            "new_symbol_sha256": dict(_NEW_HASHES),
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
            "route": "validated_alpha_candidate" if passed else "close_global_equities_dual_momentum_12m_proxy",
            "shadow_eligibility": passed,
            "paper_promotion_allowed": False,
            "live_authorized": False,
        },
        "source_metric_trust": {"external_performance_trusted": False, "source_metrics_used_for_gates": False},
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
        "record_type": "global_equities_dual_momentum_artifact_manifest",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "inputs": {
            "protocol_sha256": _PROTOCOL_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "base_data_sha256": _BASE_DATA_HASH,
            "base_manifest_sha256": _BASE_MANIFEST_HASH,
            "engine_sha256": _hash(_ENGINE),
            "new_symbol_sha256": dict(_NEW_HASHES),
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
    if _hash(_BASE_DATA) != _BASE_DATA_HASH or _hash(_BASE_MANIFEST) != _BASE_MANIFEST_HASH:
        raise ValidationError("imported V5.72 data or manifest hash mismatch.")
    bars_by_symbol: dict[str, tuple[LocalDailyBar, ...]] = {}
    for symbol in CORE_SYMBOLS:
        bars = load_local_daily_bars_csv(_BASE_DATA, symbol=symbol, as_of=_END).usable_bars
        selected = tuple(bar for bar in bars if _START <= bar.date <= _END)
        bars_by_symbol[symbol] = selected
    if _normalized_hash(load_local_daily_bars_csv(_BASE_DATA, symbol="SPY", as_of=_END).usable_bars) != _SPY_NORMALIZED_HASH:
        raise ValidationError("imported normalized SPY hash mismatch.")
    for symbol, path in _NEW_PATHS.items():
        if _hash(path) != _NEW_HASHES[symbol]:
            raise ValidationError(f"{symbol} canonical hash mismatch.")
        bars_by_symbol[symbol] = load_local_daily_bars_csv(path, symbol=symbol, as_of=_END).usable_bars
    dates = tuple(bar.date for bar in bars_by_symbol["SPY"])
    if len(dates) != _COUNTS["all"] or dates[0] != _START or dates[-1] != _END:
        raise ValidationError("common coverage does not match the receipt.")
    for symbol in SYMBOLS:
        bars = bars_by_symbol[symbol]
        if tuple(bar.date for bar in bars) != dates:
            raise ValidationError(f"{symbol} common-session sequence mismatch.")
    _validate_windows(dates)
    return _Data(dates, {symbol: tuple(float(bar.adjusted_close) for bar in bars_by_symbol[symbol]) for symbol in SYMBOLS})


def _validate_windows(dates: tuple[date, ...]) -> None:
    for window_id, start, end in _WINDOWS:
        observed = tuple(item for item in dates if start <= item <= end)
        if len(observed) != _COUNTS[window_id] or observed[0] != start or observed[-1] != end:
            raise ValidationError(f"{window_id} receipt coverage mismatch.")
    oos = tuple(item for item in dates if _OOS_START <= item <= _END)
    folds = tuple(item for window_id, start, end in _WINDOWS if window_id.startswith("oos_fold_") for item in dates if start <= item <= end)
    if folds != oos:
        raise ValidationError("OOS folds do not exactly partition OOS.")


def _actions(data: _Data) -> dict[date, str]:
    month_ends = [
        index for index, item in enumerate(data.dates)
        if index == len(data.dates) - 1 or (data.dates[index + 1].year, data.dates[index + 1].month) != (item.year, item.month)
    ]
    actions: dict[date, str] = {}
    for position, end_index in enumerate(month_ends):
        if position < 12 or end_index + 1 >= len(data.dates):
            continue
        start_index = month_ends[position - 12]
        returns = {
            symbol: data.prices[symbol][end_index] / data.prices[symbol][start_index] - 1.0
            for symbol in ("SPY", "VEU", "BIL")
        }
        equity = sorted(("SPY", "VEU"), key=lambda symbol: (-returns[symbol], symbol))[0]
        actions[data.dates[end_index + 1]] = equity if returns[equity] > returns["BIL"] else "AGG"
    if _OOS_START not in actions:
        raise ValidationError("first OOS monthly action is missing.")
    return actions


def _evaluate(data: _Data, actions: Mapping[date, str]) -> dict[str, object]:
    asset_returns = {
        symbol: tuple(data.prices[symbol][index] / data.prices[symbol][index - 1] - 1.0 for index in range(1, len(data.dates)))
        for symbol in SYMBOLS
    }
    dates = data.dates[1:]
    candidates: dict[str, object] = {}
    series_by_cost: dict[str, _Series] = {}
    for cost_id, rate in _COSTS.items():
        series = _simulate(dates, asset_returns, actions, rate)
        series_by_cost[cost_id] = series
        candidates[cost_id] = _window_metrics(series)
    spy = _constant_series(dates, asset_returns, {"SPY": 1.0})
    balanced = _constant_series(dates, asset_returns, {symbol: 1.0 / 3.0 for symbol in ("SPY", "VEU", "AGG")})
    core = _constant_series(dates, asset_returns, {symbol: 0.2 for symbol in CORE_SYMBOLS})
    baselines = {
        "spy_buy_and_hold": _window_metrics(spy),
        "static_spy_veu_agg_equal_weight": _window_metrics(balanced),
        "cross_asset_core": _window_metrics(core),
    }
    decision = candidates["decision"]
    comparisons = {
        baseline_id: {window_id: _compare(decision[window_id], metrics[window_id]) for window_id, *_ in _WINDOWS}
        for baseline_id, metrics in baselines.items()
    }
    composite = _composite(core, series_by_cost["decision"])
    composite_metrics = _window_metrics(composite)
    oos_action_dates = sorted(item for item in actions if _OOS_START <= item <= _END)
    oos_holdings = [actions[item] for item in oos_action_dates]
    changes = sum(left != right for left, right in zip(oos_holdings, oos_holdings[1:]))
    return {
        "candidate_cost_metrics": candidates,
        "baselines": baselines,
        "decision_cost_comparisons": comparisons,
        "target_contract": {
            "oos_monthly_action_count": len(oos_action_dates),
            "oos_target_change_count": changes,
            "annualized_target_changes": _number(changes * 252.0 / _COUNTS["oos"]),
            "symbols_targeted": sorted(set(oos_holdings)),
            "single_asset_target_exclusivity": True,
        },
        "portfolio_composite": {
            "construction": "80pct_static_cross_asset_core_plus_20pct_actual_candidate_sleeve",
            "metrics": composite_metrics,
            "comparison_to_core": {window_id: _compare(composite_metrics[window_id], baselines["cross_asset_core"][window_id]) for window_id, *_ in _WINDOWS},
        },
        "independent_in_memory_replay_equal": True,
        "parameter_search_performed": False,
        "source_metrics_used": False,
    }


def _simulate(dates: tuple[date, ...], asset_returns: Mapping[str, tuple[float, ...]], actions: Mapping[date, str], cost_rate: float) -> _Series:
    holding = ""
    values: list[float] = []
    turnover: list[float] = []
    exposure: list[float] = []
    holdings: list[str] = []
    for index, item in enumerate(dates):
        turn = 0.0
        if item in actions:
            target = actions[item]
            if target not in ("SPY", "VEU", "AGG"):
                raise ValidationError("GEM action target is invalid.")
            if target != holding:
                turn = 1.0 if holding else 1.0
                holding = target
        gross = asset_returns[holding][index] if holding else 0.0
        net = (1.0 - turn * cost_rate) * (1.0 + gross) - 1.0
        values.append(net)
        turnover.append(turn)
        exposure.append(1.0 if holding else 0.0)
        holdings.append(holding)
    return _Series(dates, tuple(values), tuple(turnover), tuple(exposure), tuple(holdings))


def _constant_series(dates: tuple[date, ...], asset_returns: Mapping[str, tuple[float, ...]], weights: Mapping[str, float]) -> _Series:
    values = tuple(sum(weight * asset_returns[symbol][index] for symbol, weight in weights.items()) for index in range(len(dates)))
    return _Series(dates, values, tuple(0.0 for _ in dates), tuple(sum(weights.values()) for _ in dates), tuple("static" for _ in dates))


def _composite(core: _Series, candidate: _Series) -> _Series:
    if core.dates != candidate.dates:
        raise ValidationError("composite sleeves are not aligned.")
    return _Series(
        core.dates,
        tuple(0.8 * left + 0.2 * right for left, right in zip(core.returns, candidate.returns)),
        tuple(0.2 * value for value in candidate.turnover),
        tuple(0.8 + 0.2 * value for value in candidate.exposure),
        candidate.holdings,
    )


def _window_metrics(series: _Series) -> dict[str, object]:
    return {window_id: _metrics(series, window_id, start, end) for window_id, start, end in _WINDOWS}


def _metrics(series: _Series, window_id: str, start: date, end: date) -> dict[str, object]:
    indexes = [index for index, item in enumerate(series.dates) if start <= item <= end]
    if len(indexes) != _COUNTS[window_id]:
        raise ValidationError(f"{window_id} metric count mismatch.")
    returns = [series.returns[index] for index in indexes]
    equity = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = max(drawdown, 1.0 - equity / peak)
    total = equity - 1.0
    annualized = math.pow(equity, 252.0 / len(returns)) - 1.0
    daily_stdev = stdev(returns)
    sharpe = mean(returns) / daily_stdev * math.sqrt(252.0) if daily_stdev > 0.0 else None
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
        "annualized_one_way_turnover": _number(sum(series.turnover[index] for index in indexes) * 252.0 / len(indexes)),
        "invested_session_fraction": _number(sum(series.exposure[index] > 0.0 for index in indexes) / len(indexes)),
        "compounded_log_return": _number(math.log1p(total)),
    }


def _compare(candidate: Mapping[str, object], baseline: Mapping[str, object]) -> dict[str, object]:
    candidate_sharpe = _required_float(candidate["sharpe_ratio"])
    baseline_sharpe = _required_float(baseline["sharpe_ratio"])
    return {
        "total_return_delta": _number(_float(candidate["total_return"]) - _float(baseline["total_return"])),
        "annualized_return_delta": _number(_float(candidate["annualized_return"]) - _float(baseline["annualized_return"])),
        "sharpe_ratio_delta": _number(candidate_sharpe - baseline_sharpe),
        "max_drawdown_delta": _number(_float(candidate["max_drawdown"]) - _float(baseline["max_drawdown"])),
        "max_drawdown_improvement": _number(_float(baseline["max_drawdown"]) - _float(candidate["max_drawdown"])),
    }


def _gates(evaluation: Mapping[str, object]) -> dict[str, dict[str, object]]:
    decision = evaluation["candidate_cost_metrics"]["decision"]
    stress = evaluation["candidate_cost_metrics"]["stress"]
    oos = decision["oos"]
    folds = [decision[f"oos_fold_{index}"] for index in range(1, 4)]
    full_log = _float(oos["compounded_log_return"])
    max_fold_share = max(_float(fold["compounded_log_return"]) / full_log for fold in folds)
    common = {
        "full_and_all_fold_returns_positive": _float(oos["total_return"]) > 0.0 and all(_float(fold["total_return"]) > 0.0 for fold in folds),
        "full_sharpe_at_least_0_65": _required_float(oos["sharpe_ratio"]) >= 0.65,
        "stress_return_positive": _float(stress["oos"]["annualized_return"]) > 0.0,
        "stress_degradation_at_most_0_01": _float(oos["annualized_return"]) - _float(stress["oos"]["annualized_return"]) <= 0.01,
        "max_fold_log_share_at_most_0_70": max_fold_share <= 0.70,
        "replay_and_signal_integrity": bool(evaluation["independent_in_memory_replay_equal"]) and evaluation["target_contract"]["single_asset_target_exclusivity"],
        "source_metrics_unused": evaluation["source_metrics_used"] is False,
    }
    spy = evaluation["decision_cost_comparisons"]["spy_buy_and_hold"]
    balanced = evaluation["decision_cost_comparisons"]["static_spy_veu_agg_equal_weight"]
    fold_sharpe_wins = sum(_float(spy[f"oos_fold_{index}"]["sharpe_ratio_delta"]) > 0.0 for index in range(1, 4))
    changes = _float(evaluation["target_contract"]["annualized_target_changes"])
    specific = {
        "sharpe_exceeds_spy_by_0_05": _float(spy["oos"]["sharpe_ratio_delta"]) >= 0.05,
        "drawdown_improves_spy_by_0_05": _float(spy["oos"]["max_drawdown_improvement"]) >= 0.05,
        "annualized_return_within_0_025_of_spy": _float(spy["oos"]["annualized_return_delta"]) >= -0.025,
        "sharpe_exceeds_balanced_by_0_05": _float(balanced["oos"]["sharpe_ratio_delta"]) >= 0.05,
        "annualized_return_within_0_01_of_balanced": _float(balanced["oos"]["annualized_return_delta"]) >= -0.01,
        "at_least_two_fold_sharpe_wins_vs_spy": fold_sharpe_wins >= 2,
        "all_three_target_assets_used": evaluation["target_contract"]["symbols_targeted"] == ["AGG", "SPY", "VEU"],
        "annualized_target_changes_between_0_5_and_6": 0.5 <= changes <= 6.0,
    }
    composite = evaluation["portfolio_composite"]["comparison_to_core"]["oos"]
    portfolio = {
        "sharpe_improves_by_0_02": _float(composite["sharpe_ratio_delta"]) >= 0.02,
        "annualized_return_no_more_than_0_01_lower": _float(composite["annualized_return_delta"]) >= -0.01,
        "drawdown_or_return_improves_by_0_005": _float(composite["max_drawdown_improvement"]) >= 0.005 or _float(composite["annualized_return_delta"]) >= 0.005,
    }
    return {
        "common_integrity": {"passed": all(common.values()), "conditions": common, "max_fold_log_return_share": _number(max_fold_share)},
        "candidate_specific_alpha": {"passed": all(specific.values()), "conditions": specific},
        "portfolio_level_value": {"passed": all(portfolio.values()), "conditions": portfolio},
    }


def _summary(result: Mapping[str, object]) -> str:
    metrics = result["evaluation"]["candidate_cost_metrics"]["decision"]["oos"]
    lines = [
        "# V5.73 Global-Equities Dual Momentum",
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
    for gate_id, gate in result["gates"].items():
        lines.append(f"- `{gate_id}`: `{str(gate['passed']).lower()}`")
    lines.extend(["", "No external performance metric controlled a gate. A pass is no-submit-shadow eligible only.", ""])
    return "\n".join(lines)


def _normalized_hash(bars: Sequence[LocalDailyBar]) -> str:
    digest = hashlib.sha256()
    for bar in bars:
        digest.update(f"{bar.symbol},{bar.date.isoformat()},{format(bar.adjusted_close, 'f')}\n".encode("utf-8"))
    return digest.hexdigest()


def _validate_tracked() -> None:
    if _hash(_PROTOCOL) != _PROTOCOL_HASH:
        raise ValidationError("protocol SHA-256 mismatch.")
    if _hash(_RECEIPT) != _RECEIPT_HASH:
        raise ValidationError("data receipt SHA-256 mismatch.")


def _safety() -> dict[str, object]:
    return {"offline_research_only": True, "credential_access": False, "network_access": False, "broker_access": False, "paper_mutation": False, "live_activity": False, "paper_promotion_allowed": False, "live_authorized": False}


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
        raise ValidationError("output_root must be a local path.")
    return Path(value)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    _write_text(path, json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")) + "\n")


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
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode("utf-8")


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
        raise ValidationError("required metric is missing.")
    return _float(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="global-equities-dual-momentum")
    parser.add_argument("--output-root", default=str(_OUTPUT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_global_equities_dual_momentum(args.output_root)
    except ValidationError as exc:
        print(f"global_equities_dual_momentum_status=blocked:{exc}")
        return 2
    if args.format == "json":
        print(json.dumps(_json_safe(result), sort_keys=True, separators=(",", ":")))
    else:
        print("global_equities_dual_momentum_status=completed")
        print(f"terminal_route={result['terminal_decision']['route']}")
        print(f"all_gates_passed={str(result['terminal_decision']['all_gates_passed']).lower()}")
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
