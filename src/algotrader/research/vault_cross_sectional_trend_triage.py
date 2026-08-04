"""Frozen V5.91 vault cross-sectional trend triage.

One exactly specified absolute-trend rule is applied identically to eighteen
single-country equity markets this repository had never acquired. The test is
cross-sectional breadth, not any single market: in how many markets does the
rule beat that market's own buy-and-hold?

This buys statistical power from breadth instead of from calendar time. It
remains a historical result — uncontaminated by our selection, not by the
clock — so a pass argues only for a forward-shadow registration.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

__all__ = [
    "build_vault_triage_preregistration",
    "run_vault_cross_sectional_trend_triage",
]

PROTOCOL_ID = "v5_91_vault_cross_sectional_trend_triage_v1"
RULE_ID = "absolute_trend_200_session_sma_monthly"
BENCHMARK_ID = "per_market_buy_and_hold"
MARKETS = (
    "EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWK", "EWL", "EWM",
    "EWN", "EWO", "EWP", "EWQ", "EWS", "EWU", "EWW", "EWY", "EWZ",
)
_PROTOCOL = Path(
    "docs/design/v5_91_vault_cross_sectional_trend_triage_preregistration.md"
)
_RECEIPT = Path(
    "docs/design/v5_91_vault_cross_sectional_trend_triage_data_receipt.md"
)
_ROOT = Path("runs/v5_91_vault_cross_sectional_trend_triage")
_DATA = _ROOT / "canonical_data.csv"
_DATA_MANIFEST = _ROOT / "canonical_data_manifest.json"
_OUTPUT = _ROOT / "evaluation"
_ENGINE = Path("src/algotrader/research/vault_cross_sectional_trend_triage.py")
_PROTOCOL_HASH = "a1d9c90face12c565dc2b434aaa8ad5ea59754fec29c90bba761279a72938f12"
_RECEIPT_HASH = "5038958d293e10c9f61b97ab2697a4cb685196cb38a77eeb7314823cab7eea65"
_DATA_HASH = "af28aa4d21084d62b0936b5127a8e43624482bea2c511db7cdafb8d25c637ca6"
_MANIFEST_HASH = "5139ad556a405337514438688f2a2a436ce2a604730433314be3df9b310e3929"

_SMA_WINDOW = 200
_END = date(2026, 7, 31)
_POST_2007_START = date(2008, 1, 1)
_SESSION_COUNT = 6550
_SCORED_SESSION_COUNT = 6350
_DECISIONS_PER_MARKET = 303
_COSTS = {"zero": 0.0, "decision": 0.0005, "stress": 0.0015}
_REQUIRED_SHARPE_WINS = 13
_REQUIRED_DRAWDOWN_WINS = 13
_REQUIRED_POST_2007_WINS = 12
_TRADING_DAYS = 252.0


@dataclass(frozen=True, slots=True)
class _Series:
    dates: tuple[date, ...]
    returns: tuple[float, ...]
    equity: tuple[float, ...]
    drawdown: tuple[float, ...]
    turnover: tuple[float, ...]


def build_vault_triage_preregistration() -> dict[str, object]:
    _validate_tracked_inputs()
    return {
        "record_type": "vault_triage_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "rule_id": RULE_ID,
        "benchmark_id": BENCHMARK_ID,
        "markets": list(MARKETS),
        "market_count": len(MARKETS),
        "signal": "adjusted_close_above_trailing_200_session_simple_moving_average",
        "signal_frequency": "final_common_session_of_each_calendar_month",
        "target_grammar": "one_hundred_percent_market_or_zero_return_cash",
        "action_lag": "month_end_close_t_to_next_common_close_t_plus_1",
        "warm_up_sessions": _SMA_WINDOW,
        "scored_sessions": _SCORED_SESSION_COUNT,
        "decisions_per_market": _DECISIONS_PER_MARKET,
        "total_decisions": _DECISIONS_PER_MARKET * len(MARKETS),
        "cost_bps_per_one_way_turnover": {
            key: _number(value * 10000.0) for key, value in _COSTS.items()
        },
        "primary_gate": {
            "statistic": "markets_where_rule_sharpe_exceeds_buy_and_hold_sharpe",
            "cost_model": "decision",
            "required_wins": _REQUIRED_SHARPE_WINS,
            "market_count": len(MARKETS),
            "one_sided_binomial_p_at_threshold": "0.048126220703",
            "independence_assumed_and_overstated": True,
        },
        "secondary_gates": {
            "stress_sharpe_wins_required": _REQUIRED_SHARPE_WINS,
            "drawdown_wins_required": _REQUIRED_DRAWDOWN_WINS,
            "median_sharpe_improvement_positive_required": True,
            "post_2007_sharpe_wins_required": _REQUIRED_POST_2007_WINS,
        },
        "protocol_sha256": _PROTOCOL_HASH,
        "receipt_sha256": _RECEIPT_HASH,
        "data_sha256": _DATA_HASH,
        "data_manifest_sha256": _MANIFEST_HASH,
        "parameter_search_performed": False,
        "source_metrics_used": False,
        "validated_alpha_claimed": False,
        "paper_or_live_promotion_allowed": False,
        "safety": _safety(),
    }


def run_vault_cross_sectional_trend_triage(
    output_root: Path | str = _OUTPUT,
) -> dict[str, object]:
    preregistration = build_vault_triage_preregistration()
    first = _canonical_replay(preregistration)
    second = _canonical_replay(preregistration)
    result_bytes = _json_bytes(first)
    if result_bytes != _json_bytes(second):
        raise ValidationError("canonical result replay bytes differ.")
    manifest_a = _artifact_manifest(first)
    if _json_bytes(manifest_a) != _json_bytes(_artifact_manifest(second)):
        raise ValidationError("canonical manifest replay bytes differ.")
    root = _local_path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "preregistration.json", preregistration)
    (root / "evaluation_results.json").write_bytes(result_bytes)
    _write_text(root / "evaluation_summary.md", _summary(first))
    (root / "manifest.json").write_bytes(_json_bytes(manifest_a))
    completed = dict(first)
    completed["artifact_manifest"] = manifest_a
    completed["artifact_manifest_sha256"] = _hash(root / "manifest.json")
    return completed


def _canonical_replay(
    preregistration: Mapping[str, object],
) -> dict[str, object]:
    dates, prices = _load_data()
    per_market: dict[str, object] = {}
    excess_by_market: dict[str, list[float]] = {}
    for market in MARKETS:
        per_market[market], excess_by_market[market] = _evaluate_market(
            market, dates, prices[market]
        )
    return _build_result(preregistration, dates, per_market, excess_by_market)


def _evaluate_market(
    market: str,
    dates: Sequence[date],
    closes: Sequence[float],
) -> tuple[dict[str, object], list[float]]:
    actions = _build_actions(dates, closes)
    if len(actions) != _DECISIONS_PER_MARKET:
        raise ValidationError(f"{market} decision count mismatch.")
    scored = tuple(dates[_SMA_WINDOW:])
    if len(scored) != _SCORED_SESSION_COUNT:
        raise ValidationError(f"{market} scored session count mismatch.")

    rule_costs: dict[str, object] = {}
    benchmark_costs: dict[str, object] = {}
    excess: list[float] = []
    for cost_id, rate in _COSTS.items():
        rule = _simulate(dates, closes, actions, rate)
        benchmark = _simulate(
            dates, closes, {scored[0]: 1.0}, rate
        )
        rule_costs[cost_id] = _window_metrics(rule)
        benchmark_costs[cost_id] = _window_metrics(benchmark)
        if cost_id == "decision":
            excess = [
                rule.returns[index] - benchmark.returns[index]
                for index in range(len(rule.returns))
            ]
    months_on = sum(1 for value in actions.values() if value > 0.0)
    return (
        {
            "market": market,
            "rule_cost_metrics": rule_costs,
            "benchmark_cost_metrics": benchmark_costs,
            "decision_count": len(actions),
            "months_invested": months_on,
            "months_in_cash": len(actions) - months_on,
            "invested_month_fraction": _number(months_on / len(actions)),
        },
        excess,
    )


def _build_actions(
    dates: Sequence[date],
    closes: Sequence[float],
) -> dict[date, float]:
    actions: dict[date, float] = {}
    for index in range(len(dates) - 1):
        if (dates[index].year, dates[index].month) == (
            dates[index + 1].year,
            dates[index + 1].month,
        ):
            continue
        if index < _SMA_WINDOW - 1:
            continue
        window = closes[index - _SMA_WINDOW + 1 : index + 1]
        if len(window) != _SMA_WINDOW:
            raise ValidationError("moving-average window is incomplete.")
        average = mean(window)
        if not math.isfinite(average) or average <= 0.0:
            raise ValidationError("moving average is invalid.")
        actions[dates[index + 1]] = 1.0 if closes[index] > average else 0.0
    return actions


def _simulate(
    dates: Sequence[date],
    closes: Sequence[float],
    actions: Mapping[date, float],
    cost_rate: float,
) -> _Series:
    scored = tuple(dates[_SMA_WINDOW:])
    index_by_date = {item: index for index, item in enumerate(dates)}
    position = 0.0
    equity = 1.0
    peak = 1.0
    returns: list[float] = []
    equities: list[float] = []
    drawdowns: list[float] = []
    turnovers: list[float] = []
    for item in scored:
        index = index_by_date[item]
        asset_return = closes[index] / closes[index - 1] - 1.0
        gross = position * asset_return
        if gross <= -1.0:
            raise ValidationError("equity became nonpositive before action.")
        drifted = position * (1.0 + asset_return) / (1.0 + gross)
        turnover = 0.0
        if item in actions:
            target = float(actions[item])
            if target < 0.0 or target > 1.0:
                raise ValidationError("target weight left the unit interval.")
            turnover = abs(target - drifted)
            position = target
        else:
            position = drifted
        cost = -turnover * cost_rate * (1.0 + gross)
        net = gross + cost
        if net <= -1.0 or not math.isfinite(net):
            raise ValidationError("equity became nonpositive or nonfinite.")
        equity *= 1.0 + net
        peak = max(peak, equity)
        returns.append(net)
        equities.append(equity)
        drawdowns.append(1.0 - equity / peak)
        turnovers.append(turnover)
    return _Series(
        scored, tuple(returns), tuple(equities), tuple(drawdowns), tuple(turnovers)
    )


def _window_metrics(series: _Series) -> dict[str, object]:
    full = _metrics(series, range(len(series.returns)))
    post_indexes = [
        index
        for index, item in enumerate(series.dates)
        if item >= _POST_2007_START
    ]
    return {"full": full, "post_2007": _metrics(series, post_indexes)}


def _metrics(series: _Series, indexes: Sequence[int]) -> dict[str, object]:
    values = [series.returns[index] for index in indexes]
    if len(values) < 2:
        raise ValidationError("metric window is too short.")
    log_return = math.fsum(math.log1p(value) for value in values)
    deviation = stdev(values)
    sharpe = (
        mean(values) / deviation * math.sqrt(_TRADING_DAYS)
        if deviation > 0.0
        else None
    )
    start_equity = 1.0 if indexes[0] == 0 else series.equity[indexes[0] - 1]
    peak = start_equity
    max_drawdown = 0.0
    for index in indexes:
        peak = max(peak, series.equity[index])
        max_drawdown = max(max_drawdown, 1.0 - series.equity[index] / peak)
    return {
        "session_count": len(values),
        "start": series.dates[indexes[0]].isoformat(),
        "end": series.dates[indexes[-1]].isoformat(),
        "total_return": _number(math.expm1(log_return)),
        "annualized_return": _number(
            math.expm1(log_return * _TRADING_DAYS / len(values))
        ),
        "annualized_volatility": _number(deviation * math.sqrt(_TRADING_DAYS)),
        "sharpe_ratio": _optional_number(sharpe),
        "max_drawdown": _number(max_drawdown),
        "annualized_one_way_turnover": _number(
            math.fsum(series.turnover[index] for index in indexes)
            * _TRADING_DAYS
            / len(values)
        ),
    }


def _build_result(
    preregistration: Mapping[str, object],
    dates: Sequence[date],
    per_market: Mapping[str, object],
    excess_by_market: Mapping[str, Sequence[float]],
) -> dict[str, object]:
    comparisons: dict[str, object] = {}
    sharpe_wins = 0
    stress_wins = 0
    drawdown_wins = 0
    post_wins = 0
    sharpe_deltas: list[float] = []
    for market in MARKETS:
        item = per_market[market]
        rule = item["rule_cost_metrics"]
        benchmark = item["benchmark_cost_metrics"]
        delta = _required(rule["decision"]["full"]["sharpe_ratio"]) - _required(
            benchmark["decision"]["full"]["sharpe_ratio"]
        )
        stress_delta = _required(
            rule["stress"]["full"]["sharpe_ratio"]
        ) - _required(benchmark["stress"]["full"]["sharpe_ratio"])
        drawdown_improvement = _float(
            benchmark["decision"]["full"]["max_drawdown"]
        ) - _float(rule["decision"]["full"]["max_drawdown"])
        post_delta = _required(
            rule["decision"]["post_2007"]["sharpe_ratio"]
        ) - _required(benchmark["decision"]["post_2007"]["sharpe_ratio"])
        sharpe_deltas.append(delta)
        sharpe_wins += delta > 0.0
        stress_wins += stress_delta > 0.0
        drawdown_wins += drawdown_improvement > 0.0
        post_wins += post_delta > 0.0
        comparisons[market] = {
            "sharpe_delta": _number(delta),
            "stress_sharpe_delta": _number(stress_delta),
            "max_drawdown_improvement": _number(drawdown_improvement),
            "annualized_return_delta": _number(
                _float(rule["decision"]["full"]["annualized_return"])
                - _float(benchmark["decision"]["full"]["annualized_return"])
            ),
            "post_2007_sharpe_delta": _number(post_delta),
            "sharpe_win": bool(delta > 0.0),
            "drawdown_win": bool(drawdown_improvement > 0.0),
        }

    gates = {
        "primary_sharpe_wins_at_least_13": sharpe_wins >= _REQUIRED_SHARPE_WINS,
        "stress_sharpe_wins_at_least_13": stress_wins >= _REQUIRED_SHARPE_WINS,
        "drawdown_wins_at_least_13": drawdown_wins >= _REQUIRED_DRAWDOWN_WINS,
        "median_sharpe_improvement_positive": median(sharpe_deltas) > 0.0,
        "post_2007_sharpe_wins_at_least_12": post_wins >= _REQUIRED_POST_2007_WINS,
        "replay_and_integrity_verified": True,
    }
    passed = all(gates.values())
    return {
        "record_type": "vault_cross_sectional_trend_triage_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": dict(preregistration),
        "data_admission": {
            "data_sha256": _DATA_HASH,
            "manifest_sha256": _MANIFEST_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "common_session_count": len(dates),
            "first_session": dates[0].isoformat(),
            "last_session": dates[-1].isoformat(),
        },
        "per_market": dict(per_market),
        "comparisons": comparisons,
        "cross_section": {
            "market_count": len(MARKETS),
            "sharpe_wins": sharpe_wins,
            "stress_sharpe_wins": stress_wins,
            "drawdown_wins": drawdown_wins,
            "post_2007_sharpe_wins": post_wins,
            "median_sharpe_delta": _number(median(sharpe_deltas)),
            "mean_sharpe_delta": _number(mean(sharpe_deltas)),
            "one_sided_binomial_p": _number(
                _binomial_tail(sharpe_wins, len(MARKETS))
            ),
            "mean_pairwise_excess_correlation": _number(
                _mean_pairwise_correlation(excess_by_market)
            ),
            "independence_assumed_and_overstated": True,
        },
        "gates": gates,
        "all_gates_passed": passed,
        "route": (
            "cross_sectional_evidence_supports_forward_shadow_registration"
            if passed
            else "close_triage_without_tuning"
        ),
        "validated_alpha_claimed": False,
        "historical_not_forward_evidence": True,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "replay_evidence": {
            "full_pipeline_replays": 2,
            "result_bytes_equal": True,
            "manifest_bytes_equal": True,
        },
        "safety": _safety(),
    }


def _binomial_tail(wins: int, trials: int) -> float:
    return math.fsum(math.comb(trials, k) for k in range(wins, trials + 1)) / (
        2.0**trials
    )


def _mean_pairwise_correlation(
    excess_by_market: Mapping[str, Sequence[float]],
) -> float:
    series = [list(excess_by_market[market]) for market in MARKETS]
    values: list[float] = []
    for left in range(len(series)):
        for right in range(left + 1, len(series)):
            correlation = _pearson(series[left], series[right])
            if correlation is not None:
                values.append(correlation)
    return mean(values) if values else 0.0


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
    numerator = math.fsum(
        x * y for x, y in zip(left_centered, right_centered, strict=True)
    )
    correlation = numerator / denominator
    return correlation if math.isfinite(correlation) else None


def _load_data() -> tuple[tuple[date, ...], dict[str, tuple[float, ...]]]:
    if _hash(_DATA) != _DATA_HASH:
        raise ValidationError("canonical data SHA-256 mismatch.")
    if _hash(_DATA_MANIFEST) != _MANIFEST_HASH:
        raise ValidationError("canonical data manifest SHA-256 mismatch.")
    manifest = _load_json(_DATA_MANIFEST)
    if manifest.get("symbols") != list(MARKETS):
        raise ValidationError("manifest symbols do not match the frozen universe.")
    if manifest.get("combined_output_sha256") != _DATA_HASH:
        raise ValidationError("manifest combined hash mismatch.")
    if manifest.get("protocol_id") != PROTOCOL_ID:
        raise ValidationError("manifest protocol ID mismatch.")
    if manifest.get("common_session_count") != _SESSION_COUNT:
        raise ValidationError("manifest common-session count mismatch.")
    frozen = manifest.get("frozen_pins")
    if not isinstance(frozen, dict) or frozen.get("protocol") != _PROTOCOL_HASH:
        raise ValidationError("manifest protocol pin mismatch.")
    safety = manifest.get("safety")
    if not isinstance(safety, dict) or safety.get("outcome_metrics_computed") is not False:
        raise ValidationError("manifest outcome-blind safety claim is missing.")

    by_symbol: dict[str, dict[date, float]] = {}
    for market in MARKETS:
        bars = load_local_daily_bars_csv(
            _DATA, symbol=market, as_of=_END
        ).usable_bars
        if len(bars) != _SESSION_COUNT or bars[-1].date != _END:
            raise ValidationError(f"{market} coverage mismatch.")
        by_symbol[market] = {bar.date: float(bar.adjusted_close) for bar in bars}
    dates = tuple(by_symbol[MARKETS[0]])
    for market in MARKETS[1:]:
        if tuple(by_symbol[market]) != dates:
            raise ValidationError(f"{market} session sequence mismatch.")
    return dates, {
        market: tuple(by_symbol[market][item] for item in dates)
        for market in MARKETS
    }


def _artifact_manifest(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": "vault_triage_artifact_manifest",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "inputs": {
            "protocol_sha256": _PROTOCOL_HASH,
            "receipt_sha256": _RECEIPT_HASH,
            "data_sha256": _DATA_HASH,
            "data_manifest_sha256": _MANIFEST_HASH,
            "engine_sha256": _hash(_ENGINE),
        },
        "evaluation_result_sha256": hashlib.sha256(
            _json_bytes(result)
        ).hexdigest(),
        "result_bytes_equal": True,
        "manifest_bytes_equal": True,
        "safety": _safety(),
    }


def _summary(result: Mapping[str, object]) -> str:
    cross = result["cross_section"]
    lines = [
        "# V5.91 vault cross-sectional trend triage result",
        "",
        f"Route: {result['route']}",
        "",
        f"- Markets: {cross['market_count']}",
        f"- Sharpe wins (5 bps): {cross['sharpe_wins']}",
        f"- Sharpe wins (15 bps): {cross['stress_sharpe_wins']}",
        f"- Drawdown wins (5 bps): {cross['drawdown_wins']}",
        f"- Post-2007 Sharpe wins: {cross['post_2007_sharpe_wins']}",
        f"- Median Sharpe delta: {cross['median_sharpe_delta']}",
        f"- One-sided binomial p: {cross['one_sided_binomial_p']}",
        (
            "- Mean pairwise excess correlation: "
            f"{cross['mean_pairwise_excess_correlation']}"
        ),
        "",
        "## Gates",
        "",
    ]
    for gate_id, value in result["gates"].items():
        lines.append(f"- {gate_id}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "This is historical breadth evidence on markets never previously",
            "acquired here. It is not validated alpha and authorizes no paper",
            "or live activity.",
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
    resolved = path.resolve()
    try:
        resolved.relative_to(Path("runs").resolve())
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
    return (
        json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


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


def _required(value: object) -> float:
    if value is None:
        raise ValidationError("a required Sharpe ratio was undefined.")
    return _float(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(_OUTPUT))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_vault_cross_sectional_trend_triage(args.output_root)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"vault_triage_status=blocked:{exc}")
        return 2
    cross = result["cross_section"]
    print("vault_triage_status=completed")
    print(f"route={result['route']}")
    print(f"sharpe_wins={cross['sharpe_wins']}/{cross['market_count']}")
    print(f"binomial_p={cross['one_sided_binomial_p']}")
    print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
