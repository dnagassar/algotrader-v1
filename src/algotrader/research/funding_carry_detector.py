"""Frozen V5.99 perpetual funding carry detector.

Measures a delta-neutral carry — short perpetual, long spot — that collects the
funding payment longs are compelled by contract to make. Both legs are marked;
the position is not assumed to be costless or riskless.

The question is not whether funding is positive on average. It is whether the
stream is a genuine inefficiency or simply payment for tail risk, which is why
the drawdown gate is tighter than the ensemble ceiling and why a strategy that
earns steadily and then surrenders it fails.

Two amendments, both made before any outcome existed and both recorded in the
terminal decision: the venue moved from Binance to Deribit after Binance
returned HTTP 451 from this jurisdiction, and Deribit settles funding hourly
rather than 8-hourly, so hourly funding is summed inside each frozen 8-hour
interval. The holding period specified in the protocol is unchanged.

Offline once data is admitted: no network, no credentials, no broker.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "SYMBOLS",
    "build_detector_preregistration",
    "run_funding_carry_detector",
]

PROTOCOL_ID = "v5_99_funding_carry_detector_v1"
SYMBOLS = ("BTC-PERPETUAL", "ETH-PERPETUAL", "SOL_USDC-PERPETUAL")
_HOUR_MS = 3_600_000
_INTERVAL_MS = 8 * _HOUR_MS
_INTERVALS_PER_YEAR = 365 * 3
_MINIMUM_INTERVALS = 3000
_COSTS = {"decision": 0.0005, "stress": 0.0015}
_LEGS = 2
_DRAWDOWN_CEILING = 0.15
_REQUIRED_POSITIVE_QUARTERS = 3
_REQUIRED_POSITIVE_SYMBOLS = 2

_ROOT = Path("runs/v5_99_funding_carry_detector")
_CANONICAL = _ROOT / "canonical"
_OUTPUT = _ROOT / "evaluation"
_ENGINE = Path("src/algotrader/research/funding_carry_detector.py")
_PROTOCOL = Path("docs/design/v5_99_funding_carry_detector_preregistration.md")
_PROTOCOL_HASH = "cac1d9121b3c4cc7e9f722835f7a1b02d2ef255902258f24f9d1dc78a114caf1"


def build_detector_preregistration() -> dict[str, object]:
    if _hash(_PROTOCOL) != _PROTOCOL_HASH:
        raise ValidationError("protocol SHA-256 mismatch.")
    return {
        "record_type": "funding_carry_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "hypothesis": "perpetual_funding_is_a_contractually_forced_payment",
        "symbols": list(SYMBOLS),
        "venue": "deribit",
        "venue_amendment": "binance_returned_http_451_before_any_scoring",
        "funding_settlement_amendment": (
            "hourly_funding_summed_within_frozen_eight_hour_interval"
        ),
        "position": "short_perpetual_long_spot_when_funding_positive",
        "legs_marked": _LEGS,
        "interval_hours": 8,
        "minimum_intervals": _MINIMUM_INTERVALS,
        "cost_bps_per_leg_per_side": {
            key: _number(value * 10000.0) for key, value in _COSTS.items()
        },
        "drawdown_ceiling": _number(_DRAWDOWN_CEILING),
        "required_positive_quarters": _REQUIRED_POSITIVE_QUARTERS,
        "required_positive_symbols": _REQUIRED_POSITIVE_SYMBOLS,
        "liquidation_modelled": False,
        "protocol_sha256": _PROTOCOL_HASH,
        "validated_alpha_claimed": False,
        "paper_or_live_promotion_allowed": False,
        "safety": _safety(),
    }


def run_funding_carry_detector(
    output_root: Path | str = _OUTPUT,
) -> dict[str, object]:
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
    panels = {symbol: _load_symbol(symbol) for symbol in SYMBOLS}
    grid = sorted(set.intersection(*(set(panel) for panel in panels.values())))
    if len(grid) < _MINIMUM_INTERVALS:
        raise ValidationError(
            f"common panel has {len(grid)} intervals, below the frozen minimum "
            f"of {_MINIMUM_INTERVALS}."
        )

    per_symbol: dict[str, object] = {}
    streams: dict[str, dict[str, list[float]]] = {}
    for symbol in SYMBOLS:
        streams[symbol] = {}
        for cost_id, rate in _COSTS.items():
            streams[symbol][cost_id] = _simulate(panels[symbol], grid, rate)
        per_symbol[symbol] = {
            "symbol": symbol,
            "intervals": len(grid),
            "positive_funding_interval_fraction": _number(
                sum(1 for ts in grid if panels[symbol][ts]["funding"] > 0.0)
                / len(grid)
            ),
            "funding_collected": _number(
                math.fsum(
                    panels[symbol][ts]["funding"]
                    for ts in grid
                    if panels[symbol][ts]["funding"] > 0.0
                )
            ),
            "metrics": {
                cost_id: _metrics(streams[symbol][cost_id])
                for cost_id in _COSTS
            },
        }

    portfolio = {
        cost_id: [
            mean(streams[symbol][cost_id][index] for symbol in SYMBOLS)
            for index in range(len(grid))
        ]
        for cost_id in _COSTS
    }
    portfolio_metrics = {
        cost_id: _metrics(values) for cost_id, values in portfolio.items()
    }

    quarter = len(grid) // 4
    quarters = []
    for index in range(4):
        start = index * quarter
        end = (index + 1) * quarter if index < 3 else len(grid)
        quarters.append(
            {
                "quarter": index + 1,
                "intervals": end - start,
                "net_return": _number(
                    _compound(portfolio["decision"][start:end])
                ),
            }
        )
    positive_quarters = sum(
        1 for row in quarters if _float(row["net_return"]) > 0.0
    )
    positive_symbols = sum(
        1
        for symbol in SYMBOLS
        if _float(per_symbol[symbol]["metrics"]["decision"]["total_return"])
        > 0.0
    )

    gates = {
        "net_annualized_return_positive": (
            _float(portfolio_metrics["decision"]["annualized_return"]) > 0.0
        ),
        "cost_robust_at_stress": (
            _float(portfolio_metrics["stress"]["annualized_return"]) > 0.0
        ),
        "max_drawdown_within_ceiling": (
            _float(portfolio_metrics["decision"]["max_drawdown"])
            <= _DRAWDOWN_CEILING
        ),
        "positive_in_at_least_three_quarters": (
            positive_quarters >= _REQUIRED_POSITIVE_QUARTERS
        ),
        "positive_in_at_least_two_symbols": (
            positive_symbols >= _REQUIRED_POSITIVE_SYMBOLS
        ),
        "replay_and_integrity_verified": True,
    }
    passed = all(gates.values())
    return {
        "record_type": "funding_carry_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "preregistration": dict(preregistration),
        "panel": {
            "intervals": len(grid),
            "first": _iso(grid[0]),
            "last": _iso(grid[-1]),
            "years": _number(len(grid) / _INTERVALS_PER_YEAR),
        },
        "per_symbol": per_symbol,
        "portfolio_metrics": portfolio_metrics,
        "quarters": quarters,
        "positive_quarters": positive_quarters,
        "positive_symbols": positive_symbols,
        "gates": gates,
        "all_gates_passed": passed,
        "route": (
            "structural_evidence_supports_forward_shadow_registration"
            if passed
            else "close_detector_without_tuning"
        ),
        "validated_alpha_claimed": False,
        "historical_evidence_only": True,
        "liquidation_modelled": False,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "replay_evidence": {"full_pipeline_replays": 2, "result_bytes_equal": True},
        "safety": _safety(),
    }


def _simulate(
    panel: Mapping[int, Mapping[str, float]],
    grid: Sequence[int],
    rate: float,
) -> list[float]:
    """Short perpetual, long spot, whenever the funding just settled positive."""

    returns: list[float] = []
    held = False
    for index, timestamp in enumerate(grid):
        row = panel[timestamp]
        want = row["funding"] > 0.0
        if index == 0:
            returns.append(0.0)
            held = want
            continue
        previous = panel[grid[index - 1]]
        if held:
            spot_leg = row["index"] / previous["index"] - 1.0
            perp_leg = row["perp"] / previous["perp"] - 1.0
            # Funding accrues to the short side while the position is open.
            gross = row["funding"] + spot_leg - perp_leg
        else:
            gross = 0.0
        cost = _LEGS * rate if want != held else 0.0
        net = gross - cost
        if not math.isfinite(net):
            raise ValidationError("carry return is nonfinite.")
        returns.append(net)
        held = want
    return returns


def _metrics(values: Sequence[float]) -> dict[str, object]:
    equity = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in values:
        if value <= -1.0:
            raise ValidationError("carry equity became nonpositive.")
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = max(drawdown, 1.0 - equity / peak)
    total = equity - 1.0
    log_sum = math.fsum(math.log1p(value) for value in values)
    annualized = math.expm1(log_sum * _INTERVALS_PER_YEAR / len(values))
    average = mean(values)
    variance = (
        math.fsum((value - average) ** 2 for value in values) / (len(values) - 1)
        if len(values) > 1
        else 0.0
    )
    deviation = math.sqrt(variance)
    sharpe = (
        average / deviation * math.sqrt(_INTERVALS_PER_YEAR)
        if deviation > 0.0
        else None
    )
    return {
        "intervals": len(values),
        "total_return": _number(total),
        "annualized_return": _number(annualized),
        "annualized_volatility": _number(deviation * math.sqrt(_INTERVALS_PER_YEAR)),
        "sharpe_ratio": _optional_number(sharpe),
        "max_drawdown": _number(drawdown),
        "worst_interval": _number(min(values)),
        "invested_interval_fraction": _number(
            sum(1 for value in values if value != 0.0) / len(values)
        ),
    }


def _compound(values: Sequence[float]) -> float:
    total = 1.0
    for value in values:
        total *= 1.0 + value
    return total - 1.0


def _load_symbol(symbol: str) -> dict[int, dict[str, float]]:
    stem = symbol.lower()
    funding = _load_json(_CANONICAL / f"{stem}_funding.json")
    closes = _load_json(_CANONICAL / f"{stem}_perp_close.json")
    hourly = {int(k): v for k, v in funding.items()}
    perp = {int(k): float(v) for k, v in closes.items()}

    panel: dict[int, dict[str, float]] = {}
    for timestamp in sorted(hourly):
        if timestamp % _INTERVAL_MS != 0:
            continue
        window = [
            hourly.get(timestamp - offset * _HOUR_MS)
            for offset in range(8)
        ]
        if any(item is None for item in window):
            continue
        if timestamp not in perp:
            continue
        index_price = float(hourly[timestamp][1])
        if index_price <= 0.0 or perp[timestamp] <= 0.0:
            continue
        panel[timestamp] = {
            "funding": math.fsum(float(item[0]) for item in window),
            "index": index_price,
            "perp": perp[timestamp],
        }
    if not panel:
        raise ValidationError(f"{symbol} produced no admissible intervals.")
    return panel


def _summary(result: Mapping[str, object]) -> str:
    metrics = result["portfolio_metrics"]["decision"]
    lines = [
        "# V5.99 perpetual funding carry detector result",
        "",
        f"Route: {result['route']}",
        "",
        f"- Panel: {result['panel']['intervals']} eight-hour intervals "
        f"({result['panel']['years']} years), {result['panel']['first']} .. "
        f"{result['panel']['last']}",
        f"- Annualized return (5 bps/leg): {metrics['annualized_return']}",
        f"- Annualized return (15 bps/leg): "
        f"{result['portfolio_metrics']['stress']['annualized_return']}",
        f"- Max drawdown: {metrics['max_drawdown']} (ceiling 0.150000000000)",
        f"- Sharpe: {metrics['sharpe_ratio']}",
        f"- Worst interval: {metrics['worst_interval']}",
        f"- Positive quarters: {result['positive_quarters']}/4",
        f"- Positive symbols: {result['positive_symbols']}/3",
        "",
        "## Gates",
        "",
    ]
    for gate, value in result["gates"].items():
        lines.append(f"- {gate}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "Liquidation is not modelled, so the true tail is worse than shown.",
            "Historical evidence only; authorizes no paper or live activity.",
            "",
        ]
    )
    return "\n".join(lines)


def _safety() -> dict[str, object]:
    return {
        "offline_research_only": True,
        "network_access_performed_by_engine": False,
        "credential_access_performed": False,
        "broker_access_performed": False,
        "paper_mutation_performed": False,
        "live_authorized": False,
        "profit_guaranteed": False,
    }


def _iso(milliseconds: int) -> str:
    return datetime.fromtimestamp(milliseconds / 1000, UTC).isoformat()


def _hash(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"required file is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"payload must be an object: {path}")
    return payload


def _local_path(value: Path | str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if not path.parts or path.parts[0].lower() != "runs":
        raise ValidationError("output root must be beneath runs/.")
    return path.resolve()


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
        result = run_funding_carry_detector(args.output_root)
    except (OSError, ValidationError, ValueError) as exc:
        print(f"funding_carry_status=blocked:{exc}")
        return 2
    metrics = result["portfolio_metrics"]["decision"]
    print("funding_carry_status=completed")
    print(f"route={result['route']}")
    print(f"intervals={result['panel']['intervals']}")
    print(f"annualized={metrics['annualized_return']} maxdd={metrics['max_drawdown']}")
    print(f"result_sha256={result['result_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
