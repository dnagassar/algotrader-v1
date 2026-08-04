"""Frozen V5.97 Tier A cohort 2 scoring on the repaired harness.

Scores four regime-conditional components under the V5.95 ensemble contract.
Each component holds an equal-weight basket of its declared assets while its
declared regime is active and zero-return cash otherwise; its benchmark is the
same basket held continuously.

That benchmark choice is the point. A component cannot win by holding good
assets — it wins only if *conditioning on its regime* beats holding those same
assets always, which isolates the regime claim from the asset-selection claim.

Regimes are classified from SPY over its full history so the 1,320-session
warm-up is consumed before the component panel begins. No component's own data
contributes to its regime labels.

Two V5.96 defects are repaired here. Scoring conditions on **effective action
labels** — the label observed at the prior month-end, which is the one that set
the target now in force — so a component is never graded across an episode it
did not hold. And every declared regime must first clear an outcome-blind
occupancy precondition, so an untestable regime cannot consume a cohort slot.

This module is local and research-only. It cannot load credentials, reach a
network or broker, mutate a paper account, or authorize live capital.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.ensemble_harness import (
    ComponentGates,
    EnsembleObjective,
    build_ensemble_contract,
    evaluate_component,
    evaluate_ensemble,
)
from algotrader.research.local_daily_bars import load_local_daily_bars_csv
from algotrader.research.regime_classifier import (
    REFERENCE_SYMBOL,
    build_regime_contract,
    classify_regimes,
    effective_action_labels,
    regime_occupancy,
)

__all__ = [
    "COHORT_ID",
    "COMPONENTS",
    "build_cohort_preregistration",
    "run_cohort2_scoring",
]

PROTOCOL_ID = "v5_97_tier_a_cohort_2_v1"
COHORT_ID = "tier_a_cohort_2"
COMPONENTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("precious_metals_crisis_hedge", "stressed_down", ("GDX", "GDXJ", "PPLT")),
    ("convertible_crossover_credit", "stressed_up", ("CWB", "ANGL", "EMLC")),
    ("value_size_factor_tilt", "calm_up", ("VLUE", "SIZE", "IJR")),
)
PLANNED_COMPONENT_COUNT = 3
MINIMUM_REGIME_EPISODES = 8
MINIMUM_EPISODE_SESSIONS = 10
REGIME_COUNT = 4
FAMILY_WISE_ALPHA = 0.05
ADJUSTED_ALPHA = FAMILY_WISE_ALPHA / (PLANNED_COMPONENT_COUNT * REGIME_COUNT)

_ROOT = Path("runs/v5_97_tier_a_cohort_2")
_DATA = _ROOT / "canonical_data.csv"
_DATA_MANIFEST = _ROOT / "canonical_data_manifest.json"
_SPY_CANONICAL = _ROOT / "canonical" / "spy_daily_tiingo_adjusted_canonical.csv"
_OUTPUT = _ROOT / "evaluation"
_ENGINE = Path("src/algotrader/research/cohort2_scoring.py")
_PROTOCOL = Path(
    "docs/design/v5_97_harness_repair_and_cohort_2_preregistration.md"
)
_PROTOCOL_HASH = "b3ce4c78cbf8c79c06984d5d0daa3376e767fd000818034eb4765f1457947e30"
_DATA_HASH = "e0ac633cc86e5886dd0be9feed9524034fbbba8a34ec9f106a72ec9e7ddce671"
_MANIFEST_HASH = "cfad5075f0b23f469cf5670fecbdfec2c298e912d16f265b8d259cf38547e51d"
_PANEL_SESSIONS = 3342
_END = date(2026, 7, 31)
_COSTS = {"decision": 0.0005, "stress": 0.0015}


def build_cohort_preregistration() -> dict[str, object]:
    """Return the frozen cohort plan, validating every pinned input."""

    if _hash(_PROTOCOL) != _PROTOCOL_HASH:
        raise ValidationError("protocol SHA-256 mismatch.")
    ensemble = build_ensemble_contract()
    regime = build_regime_contract()
    return {
        "record_type": "tier_a_cohort_2_preregistration",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "cohort_id": COHORT_ID,
        "planned_component_count": PLANNED_COMPONENT_COUNT,
        "regime_count": REGIME_COUNT,
        "hypotheses": PLANNED_COMPONENT_COUNT * REGIME_COUNT,
        "family_wise_alpha": _number(FAMILY_WISE_ALPHA),
        "bonferroni_adjusted_alpha": _number(ADJUSTED_ALPHA),
        "components": [
            {
                "component_id": component_id,
                "declared_regime": regime_id,
                "assets": list(assets),
                "benchmark": "equal_weight_buy_and_hold_of_same_assets",
            }
            for component_id, regime_id, assets in COMPONENTS
        ],
        "tier": "A",
        "protocol_sha256": _PROTOCOL_HASH,
        "data_sha256": _DATA_HASH,
        "data_manifest_sha256": _MANIFEST_HASH,
        "ensemble_contract_fingerprint": ensemble[
            "ensemble_contract_fingerprint"
        ],
        "regime_set_fingerprint": regime["regime_set_fingerprint"],
        "validated_alpha_claimed": False,
        "paper_or_live_promotion_allowed": False,
        "safety": _safety(),
    }


def run_cohort2_scoring(
    output_root: Path | str = _OUTPUT,
) -> dict[str, object]:
    """Score every cohort member and the resulting ensemble."""

    preregistration = build_cohort_preregistration()
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
    raw_labels = _panel_raw_labels(dates)
    # Targets form on raw month-end labels; scoring conditions on the effective
    # labels those targets imply, so holding and conditioning coincide exactly.
    labels = list(effective_action_labels(dates, raw_labels))
    occupancy = regime_occupancy(
        labels,
        minimum_episodes=MINIMUM_REGIME_EPISODES,
        minimum_episode_sessions=MINIMUM_EPISODE_SESSIONS,
    )
    for _, regime_id, _ in COMPONENTS:
        if not occupancy[regime_id].sufficient:
            raise ValidationError(
                f"{regime_id} fails the occupancy precondition; no component "
                "may be declared against a regime that barely occurs."
            )
    gates = ComponentGates(episode_win_alpha=ADJUSTED_ALPHA)
    objective = EnsembleObjective()

    default = [0.0] * len(dates)
    evaluations: dict[str, object] = {}
    admitted_excess: dict[str, list[float]] = {}
    members: dict[str, list[float]] = {}
    admitted: list[str] = []

    for component_id, regime_id, assets in COMPONENTS:
        component_streams: dict[str, list[float]] = {}
        benchmark_streams: dict[str, list[float]] = {}
        for cost_id, rate in _COSTS.items():
            component_streams[cost_id] = _conditional_basket(
                dates, prices, assets, raw_labels, regime_id, rate
            )
            benchmark_streams[cost_id] = _conditional_basket(
                dates, prices, assets, raw_labels, None, rate
            )
        result = evaluate_component(
            component_id=component_id,
            declared_regime=regime_id,
            labels=labels,
            component_returns=component_streams,
            benchmark_returns=benchmark_streams,
            default_returns=default,
            admitted_in_regime_excess={
                key: value for key, value in admitted_excess.items()
            },
            ensemble_member_returns=dict(members),
            objective=objective,
            gates=gates,
        )
        evaluations[component_id] = result
        if result["all_gates_passed"]:
            admitted.append(component_id)
            members[component_id] = component_streams["decision"]
            admitted_excess[component_id] = [
                component_streams["decision"][index]
                - benchmark_streams["decision"][index]
                for index, label in enumerate(labels)
                if label == regime_id
            ]

    ensemble = (
        evaluate_ensemble(members, objective=objective) if members else None
    )
    return {
        "record_type": "tier_a_cohort_2_result",
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "cohort_id": COHORT_ID,
        "preregistration": dict(preregistration),
        "regime_occupancy": {
            key: value.as_payload() for key, value in occupancy.items()
        },
        "panel": {
            "sessions": len(dates),
            "first_session": dates[0].isoformat(),
            "last_session": dates[-1].isoformat(),
            "regime_session_counts": {
                label: sum(1 for value in labels if value == label)
                for label in sorted({value for value in labels if value})
            },
        },
        "component_evaluations": evaluations,
        "admitted_component_ids": admitted,
        "admitted_component_count": len(admitted),
        "ensemble": ensemble,
        "route": (
            "cohort_admitted_at_least_one_component"
            if admitted
            else "cohort_closed_no_component_admitted"
        ),
        "validated_alpha_claimed": False,
        "historical_evidence_only": True,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "replay_evidence": {"full_pipeline_replays": 2, "result_bytes_equal": True},
        "safety": _safety(),
    }


def _conditional_basket(
    dates: Sequence[date],
    prices: Mapping[str, Sequence[float]],
    assets: Sequence[str],
    labels: Sequence[str | None],
    active_regime: str | None,
    cost_rate: float,
) -> list[float]:
    """Equal-weight basket held while active, or always when regime is None.

    Targets are formed at each month-end and take effect at the next session,
    so no label or price from the earning session influences its own weight.
    """

    weight = 1.0 / len(assets)
    month_end = {
        index
        for index in range(len(dates) - 1)
        if (dates[index].year, dates[index].month)
        != (dates[index + 1].year, dates[index + 1].month)
    }
    targets: dict[int, float] = {}
    for index in range(len(dates) - 1):
        if index not in month_end:
            continue
        if active_regime is None:
            targets[index + 1] = weight
        else:
            label = labels[index]
            targets[index + 1] = weight if label == active_regime else 0.0

    positions = {symbol: 0.0 for symbol in assets}
    returns: list[float] = []
    for index in range(len(dates)):
        if index == 0:
            returns.append(0.0)
            continue
        asset_returns = {
            symbol: prices[symbol][index] / prices[symbol][index - 1] - 1.0
            for symbol in assets
        }
        gross = math.fsum(
            positions[symbol] * asset_returns[symbol] for symbol in assets
        )
        if gross <= -1.0:
            raise ValidationError("basket equity became nonpositive.")
        drifted = {
            symbol: positions[symbol] * (1.0 + asset_returns[symbol]) / (1.0 + gross)
            for symbol in assets
        }
        turnover = 0.0
        if index in targets:
            target = {symbol: targets[index] for symbol in assets}
            prior_cash = 1.0 - math.fsum(drifted.values())
            target_cash = 1.0 - math.fsum(target.values())
            turnover = 0.5 * (
                math.fsum(
                    abs(target[symbol] - drifted[symbol]) for symbol in assets
                )
                + abs(target_cash - prior_cash)
            )
            positions = target
        else:
            positions = drifted
        cost = -turnover * cost_rate * (1.0 + gross)
        net = gross + cost
        if net <= -1.0 or not math.isfinite(net):
            raise ValidationError("basket return is nonpositive or nonfinite.")
        returns.append(net)
    return returns


def _panel_raw_labels(dates: Sequence[date]) -> list[str | None]:
    """Raw daily regime labels for the panel, from SPY's full history.

    Targets form on these at month-end. Scoring conditions on the effective
    labels they imply, which is what `effective_action_labels` derives.
    """

    bars = load_local_daily_bars_csv(
        _SPY_CANONICAL, symbol=REFERENCE_SYMBOL, as_of=_END
    ).usable_bars
    reference_dates = [bar.date for bar in bars]
    reference_closes = [float(bar.adjusted_close) for bar in bars]
    labels = classify_regimes(reference_dates, reference_closes)
    by_date = dict(zip(reference_dates, labels, strict=True))
    raw = [by_date.get(item) for item in dates]
    if any(value is None for value in raw):
        raise ValidationError(
            "panel extends outside the labelled regime window; the warm-up "
            "was not consumed before the component panel begins."
        )
    return raw


def _load_panel() -> tuple[tuple[date, ...], dict[str, tuple[float, ...]]]:
    if _hash(_DATA) != _DATA_HASH:
        raise ValidationError("canonical data SHA-256 mismatch.")
    if _hash(_DATA_MANIFEST) != _MANIFEST_HASH:
        raise ValidationError("canonical data manifest SHA-256 mismatch.")
    manifest = _load_json(_DATA_MANIFEST)
    if manifest.get("common_session_count") != _PANEL_SESSIONS:
        raise ValidationError("manifest common-session count mismatch.")
    symbols = tuple(str(value) for value in manifest["symbols"])
    by_symbol: dict[str, dict[date, float]] = {}
    for symbol in symbols:
        bars = load_local_daily_bars_csv(_DATA, symbol=symbol, as_of=_END).usable_bars
        if len(bars) != _PANEL_SESSIONS:
            raise ValidationError(f"{symbol} coverage mismatch.")
        by_symbol[symbol] = {bar.date: float(bar.adjusted_close) for bar in bars}
    dates = tuple(by_symbol[symbols[0]])
    for symbol in symbols[1:]:
        if tuple(by_symbol[symbol]) != dates:
            raise ValidationError(f"{symbol} session sequence mismatch.")
    return dates, {
        symbol: tuple(by_symbol[symbol][item] for item in dates)
        for symbol in symbols
    }


def _summary(result: Mapping[str, object]) -> str:
    lines = [
        "# V5.97 Tier A cohort 2 result",
        "",
        f"Route: {result['route']}",
        "",
        f"- Panel sessions: {result['panel']['sessions']}",
        f"- Admitted components: {result['admitted_component_count']} of 3",
        "",
        "## Components",
        "",
    ]
    for component_id, _, _ in COMPONENTS:
        item = result["component_evaluations"][component_id]
        lines.extend(
            [
                f"### {component_id} ({item['declared_regime']})",
                "",
                f"- Passed: {str(item['all_gates_passed']).lower()}",
                f"- In-regime Sharpe edge: {item['in_regime_sharpe_edge']}",
                f"- Episodes: {item['episodes_won']}/{item['scoreable_episodes']}",
                f"- Episode binomial p: {item['episode_win_binomial_p']}",
                f"- Out-of-regime drag: {item['out_of_regime_annualized_drag']}",
                "",
            ]
        )
        for gate, value in item["gate_conditions"].items():
            lines.append(f"  - {gate}: {str(value).lower()}")
        lines.append("")
    lines.extend(
        [
            "Historical evidence only. Not validated alpha; authorizes no paper",
            "or live activity.",
            "",
        ]
    )
    return "\n".join(lines)


def _safety() -> dict[str, object]:
    return {
        "offline_research_only": True,
        "network_access_performed_by_engine": False,
        "credential_access_performed_by_engine": False,
        "broker_access_performed": False,
        "paper_mutation_performed": False,
        "live_authorized": False,
        "profit_guaranteed": False,
    }


def _hash(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON payload must be an object: {path}")
    return payload


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
    return f"{value:.12f}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(_OUTPUT))
    args = parser.parse_args(argv)
    try:
        result = run_cohort2_scoring(args.output_root)
    except (OSError, ValidationError, ValueError, RuntimeError) as exc:
        print(f"cohort2_status=blocked:{exc}")
        return 2
    print("cohort2_status=completed")
    print(f"route={result['route']}")
    print(f"admitted={result['admitted_component_count']}/3")
    print(f"result_sha256={result['result_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
