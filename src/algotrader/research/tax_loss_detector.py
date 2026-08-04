"""Frozen V5.98 tax-loss forced-seller detector.

The program's first structural hypothesis. Every prior milestone tested a
formula that backtested well; this one tests a situation where a group of
participants is compelled to sell for a reason unrelated to price — the tax
treatment of realised losses — on a known calendar.

A real forced-seller mechanism must leave two fingerprints, not one: selling
pressure on year-to-date losers into December, and a reversal once the deadline
passes. Requiring both is what separates this from a seasonality hunt. A
January-only result fails, however large it is.

Fully offline: no network, no credentials, no broker, no paper mutation.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

__all__ = [
    "FORMATION_YEARS",
    "UNIVERSE",
    "build_detector_preregistration",
    "run_tax_loss_detector",
]

PROTOCOL_ID = "v5_98_tax_loss_detector_v1"
UNIVERSE: tuple[str, ...] = (
    "EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWK", "EWL", "EWM", "EWN",
    "EWO", "EWP", "EWQ", "EWS", "EWT", "EWU", "EWW", "EWY", "EWZ", "EZA",
    "FXA", "FXB", "FXC", "FXE", "FXF", "GDX", "GLD", "IJR", "IWM", "QQQ",
    "SLV", "SMH", "SPY", "TLT", "USO", "VBK",
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
)
FORMATION_YEARS: tuple[int, ...] = tuple(range(2007, 2026))
_QUINTILE = 5
_LOSER_COUNT = len(UNIVERSE) // _QUINTILE
_PANEL_START = date(2006, 6, 26)
_PANEL_END = date(2026, 7, 31)
_COSTS = {"decision": 0.0005, "stress": 0.0015}
_REQUIRED_JANUARY_WINS = 14
_REQUIRED_DECEMBER_PRESSURE = 12

_ROOT = Path("runs/v5_98_tax_loss_detector")
_DATA = _ROOT / "canonical_data.csv"
_OUTPUT = _ROOT / "evaluation"
_ENGINE = Path("src/algotrader/research/tax_loss_detector.py")
_PROTOCOL = Path("docs/design/v5_98_tax_loss_detector_preregistration.md")
_PROTOCOL_HASH = "084842dcf61d9a1c1cfefa82922cbf0f8af4f01e41a42c4a9d076ba46bfe36b2"
_DATA_HASH = "69b44bf6a3f3e241537eab28ad10311d41d2f31d5ce4299ca3a96ab1fff19437"


def build_detector_preregistration() -> dict[str, object]:
    """Return the frozen plan, validating the pinned protocol first."""

    if _hash(_PROTOCOL) != _PROTOCOL_HASH:
        raise ValidationError("protocol SHA-256 mismatch.")
    return {
        "record_type": "tax_loss_detector_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "hypothesis": "tax_motivated_forced_selling_of_year_to_date_losers",
        "universe": list(UNIVERSE),
        "universe_size": len(UNIVERSE),
        "universe_rule": (
            "every_held_symbol_with_unbroken_coverage_2006_06_26_to_2026_07_31"
        ),
        "vault_fresh": False,
        "orthogonal_to_prior_examinations": True,
        "formation_years": list(FORMATION_YEARS),
        "cycles": len(FORMATION_YEARS),
        "loser_basket_size": _LOSER_COUNT,
        "selection": "bottom_quintile_by_year_to_date_return_at_november_close",
        "december_leg": "november_close_to_december_close",
        "january_leg": "december_close_to_january_close",
        "benchmark": "equal_weight_universe_same_window",
        "costs_charged_to_strategy_only": True,
        "cost_bps_per_one_way_turnover": {
            key: _number(value * 10000.0) for key, value in _COSTS.items()
        },
        "required_january_wins": _REQUIRED_JANUARY_WINS,
        "required_december_pressure_years": _REQUIRED_DECEMBER_PRESSURE,
        "january_only_result_fails": True,
        "protocol_sha256": _PROTOCOL_HASH,
        "data_sha256": _DATA_HASH,
        "network_requests_performed": 0,
        "validated_alpha_claimed": False,
        "paper_or_live_promotion_allowed": False,
        "safety": _safety(),
    }


def run_tax_loss_detector(output_root: Path | str = _OUTPUT) -> dict[str, object]:
    """Score every formation year and both legs, twice, byte-identically."""

    preregistration = build_detector_preregistration()
    first = _canonical_replay(preregistration)
    second = _canonical_replay(preregistration)
    payload = _json_bytes(first)
    if payload != _json_bytes(second):
        raise ValidationError("canonical result replay bytes differ.")
    root = _local_path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "preregistration.json", preregistration)
    (root / "evaluation_results.json").write_bytes(payload)
    _write_text(root / "evaluation_summary.md", _summary(first))
    completed = dict(first)
    completed["result_sha256"] = hashlib.sha256(payload).hexdigest()
    completed["engine_sha256"] = _hash(_ENGINE)
    return completed


def _canonical_replay(
    preregistration: Mapping[str, object],
) -> dict[str, object]:
    dates, prices = _load_panel()
    cycles: list[dict[str, object]] = []
    for year in FORMATION_YEARS:
        cycles.append(_score_cycle(dates, prices, year))

    december = [_float(row["december_excess"]) for row in cycles]
    january = {
        cost_id: [_float(row["january_excess"][cost_id]) for row in cycles]
        for cost_id in _COSTS
    }
    january_wins = {
        cost_id: sum(1 for value in values if value > 0.0)
        for cost_id, values in january.items()
    }
    december_pressure_years = sum(1 for value in december if value < 0.0)

    gates = {
        "january_reversal_at_least_14_of_19": (
            january_wins["decision"] >= _REQUIRED_JANUARY_WINS
        ),
        "december_pressure_at_least_12_of_19": (
            december_pressure_years >= _REQUIRED_DECEMBER_PRESSURE
        ),
        "mean_december_excess_negative": mean(december) < 0.0,
        "stress_january_reversal_at_least_14_of_19": (
            january_wins["stress"] >= _REQUIRED_JANUARY_WINS
        ),
        "median_january_excess_positive": median(january["decision"]) > 0.0,
        "replay_and_integrity_verified": True,
    }
    passed = all(gates.values())
    return {
        "record_type": "tax_loss_detector_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": dict(preregistration),
        "panel": {
            "sessions": len(dates),
            "first_session": dates[0].isoformat(),
            "last_session": dates[-1].isoformat(),
        },
        "cycles": cycles,
        "aggregate": {
            "cycle_count": len(cycles),
            "january_wins_decision": january_wins["decision"],
            "january_wins_stress": january_wins["stress"],
            "december_pressure_years": december_pressure_years,
            "mean_december_excess": _number(mean(december)),
            "median_december_excess": _number(median(december)),
            "mean_january_excess": _number(mean(january["decision"])),
            "median_january_excess": _number(median(january["decision"])),
            "january_binomial_p": _number(
                _binomial_tail(january_wins["decision"], len(cycles))
            ),
            "december_binomial_p": _number(
                _binomial_tail(december_pressure_years, len(cycles))
            ),
            "leg_correlation": _optional_number(
                _pearson(december, january["decision"])
            ),
        },
        "gates": gates,
        "all_gates_passed": passed,
        "route": (
            "structural_evidence_supports_forward_shadow_registration"
            if passed
            else "close_detector_without_tuning"
        ),
        "validated_alpha_claimed": False,
        "historical_evidence_only": True,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "replay_evidence": {"full_pipeline_replays": 2, "result_bytes_equal": True},
        "safety": _safety(),
    }


def _score_cycle(
    dates: Sequence[date],
    prices: Mapping[str, Sequence[float]],
    year: int,
) -> dict[str, object]:
    base = _last_session_of(dates, year - 1, 12)
    formation = _last_session_of(dates, year, 11)
    december_close = _last_session_of(dates, year, 12)
    january_close = _last_session_of(dates, year + 1, 1)
    if not (base < formation < december_close < january_close):
        raise ValidationError(f"{year} cycle dates are not strictly ordered.")

    ytd = {
        symbol: prices[symbol][formation] / prices[symbol][base] - 1.0
        for symbol in UNIVERSE
    }
    order = {symbol: index for index, symbol in enumerate(UNIVERSE)}
    ranked = sorted(UNIVERSE, key=lambda symbol: (ytd[symbol], order[symbol]))
    losers = tuple(ranked[:_LOSER_COUNT])

    december_losers = _basket_return(prices, losers, formation, december_close)
    december_universe = _basket_return(
        prices, UNIVERSE, formation, december_close
    )
    january_universe = _basket_return(
        prices, UNIVERSE, december_close, january_close
    )
    january_gross = _basket_return(prices, losers, december_close, january_close)

    january_excess: dict[str, str] = {}
    for cost_id, rate in _COSTS.items():
        # One round trip: enter at the December close, exit at the January
        # close. The passive benchmark is charged nothing, which is the
        # conservative direction.
        net = (1.0 + january_gross) * (1.0 - rate) * (1.0 - rate) - 1.0
        january_excess[cost_id] = _number(net - january_universe)

    return {
        "formation_year": year,
        "base_session": dates[base].isoformat(),
        "formation_session": dates[formation].isoformat(),
        "december_close_session": dates[december_close].isoformat(),
        "january_close_session": dates[january_close].isoformat(),
        "loser_basket": list(losers),
        "worst_year_to_date_return": _number(ytd[ranked[0]]),
        "loser_basket_mean_year_to_date_return": _number(
            mean(ytd[symbol] for symbol in losers)
        ),
        "december_loser_return": _number(december_losers),
        "december_universe_return": _number(december_universe),
        "december_excess": _number(december_losers - december_universe),
        "january_loser_gross_return": _number(january_gross),
        "january_universe_return": _number(january_universe),
        "january_excess": january_excess,
    }


def _basket_return(
    prices: Mapping[str, Sequence[float]],
    symbols: Sequence[str],
    start: int,
    end: int,
) -> float:
    return mean(
        prices[symbol][end] / prices[symbol][start] - 1.0 for symbol in symbols
    )


def _last_session_of(dates: Sequence[date], year: int, month: int) -> int:
    matches = [
        index
        for index, item in enumerate(dates)
        if item.year == year and item.month == month
    ]
    if not matches:
        raise ValidationError(f"no sessions in {year}-{month:02d}.")
    return matches[-1]


def _load_panel() -> tuple[tuple[date, ...], dict[str, tuple[float, ...]]]:
    if _hash(_DATA) != _DATA_HASH:
        raise ValidationError("canonical data SHA-256 mismatch.")
    by_symbol: dict[str, dict[date, float]] = {}
    for symbol in UNIVERSE:
        bars = load_local_daily_bars_csv(
            _DATA, symbol=symbol, as_of=_PANEL_END
        ).usable_bars
        if not bars or bars[0].date != _PANEL_START or bars[-1].date != _PANEL_END:
            raise ValidationError(f"{symbol} coverage mismatch.")
        by_symbol[symbol] = {
            bar.date: float(bar.adjusted_close) for bar in bars
        }
    dates = tuple(by_symbol[UNIVERSE[0]])
    for symbol in UNIVERSE[1:]:
        if tuple(by_symbol[symbol]) != dates:
            raise ValidationError(f"{symbol} session sequence mismatch.")
    return dates, {
        symbol: tuple(by_symbol[symbol][item] for item in dates)
        for symbol in UNIVERSE
    }


def _binomial_tail(wins: int, trials: int) -> float:
    if trials < 1 or wins < 0 or wins > trials:
        raise ValidationError("binomial inputs are out of range.")
    return math.fsum(math.comb(trials, k) for k in range(wins, trials + 1)) / (
        2.0**trials
    )


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    lc = [value - left_mean for value in left]
    rc = [value - right_mean for value in right]
    denominator = math.sqrt(
        math.fsum(v * v for v in lc) * math.fsum(v * v for v in rc)
    )
    if denominator <= 0.0 or not math.isfinite(denominator):
        return None
    value = math.fsum(a * b for a, b in zip(lc, rc, strict=True)) / denominator
    return value if math.isfinite(value) else None


def _summary(result: Mapping[str, object]) -> str:
    agg = result["aggregate"]
    lines = [
        "# V5.98 tax-loss forced-seller detector result",
        "",
        f"Route: {result['route']}",
        "",
        f"- Cycles: {agg['cycle_count']}",
        f"- January reversal wins (5 bps): {agg['january_wins_decision']}/19",
        f"- January reversal wins (15 bps): {agg['january_wins_stress']}/19",
        f"- December pressure years: {agg['december_pressure_years']}/19",
        f"- Mean December excess: {agg['mean_december_excess']}",
        f"- Mean January excess: {agg['mean_january_excess']}",
        f"- January binomial p: {agg['january_binomial_p']}",
        f"- Leg correlation: {agg['leg_correlation']}",
        "",
        "## Gates",
        "",
    ]
    for gate, value in result["gates"].items():
        lines.append(f"- {gate}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## Per-cycle",
            "",
            "| Year | December excess | January excess (5 bps) |",
            "| ---: | ---: | ---: |",
        ]
    )
    for row in result["cycles"]:
        lines.append(
            f"| {row['formation_year']} | {row['december_excess']} | "
            f"{row['january_excess']['decision']} |"
        )
    lines.extend(
        [
            "",
            "Historical evidence only. Not validated alpha; authorizes no paper",
            "or live activity.",
            "",
        ]
    )
    return "\n".join(lines)


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
        raise ValidationError("output root must remain beneath runs/.") from exc
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(_OUTPUT))
    args = parser.parse_args(argv)
    try:
        result = run_tax_loss_detector(args.output_root)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"tax_loss_detector_status=blocked:{exc}")
        return 2
    agg = result["aggregate"]
    print("tax_loss_detector_status=completed")
    print(f"route={result['route']}")
    print(f"january_wins={agg['january_wins_decision']}/19 p={agg['january_binomial_p']}")
    print(f"december_pressure_years={agg['december_pressure_years']}/19")
    print(f"result_sha256={result['result_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
