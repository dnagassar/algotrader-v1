"""Top-two v4.0 alpha candidate regime diagnosis using local SPY data."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import stdev

from algotrader.errors import ValidationError
from algotrader.research.alpha_candidate_batch_scout import (
    DEFAULT_ALPHA_CANDIDATE_BATCH_DAILY_BARS_CSV,
    DEFAULT_ALPHA_CANDIDATE_BATCH_OUTPUT_ROOT,
    AlphaCandidateDefinition,
    _drawdown_recovery_exposures,
    _indicator_series,
    _snapshot,
    _vol_scaled_trend_exposures,
    _window_slices,
    build_fixed_alpha_candidate_definitions,
)
from algotrader.research.daily_backtest import (
    DailyBacktestAssumptions,
    DailyBacktestPoint,
    DailyExposure,
    run_daily_backtest,
)
from algotrader.research.local_daily_bars import LocalDailyBar, load_local_daily_bars_csv

__all__ = [
    "REGIME_DIAGNOSIS_DECISIONS",
    "TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS",
    "build_top_two_regime_diagnosis_packet",
    "regime_diagnosis_mutation_policy",
    "render_top_two_regime_diagnosis_brief",
    "write_top_two_regime_diagnosis_artifacts",
]


DEFAULT_REGIME_DIAGNOSIS_OUTPUT_ROOT = (
    DEFAULT_ALPHA_CANDIDATE_BATCH_OUTPUT_ROOT.parent / "top_two_regime_diagnosis" / "latest"
)
DEFAULT_REGIME_DIAGNOSIS_RUN_ID = "v4_1_top_two_regime_filter_diagnosis"
DEFAULT_PRIOR_BATCH_SUMMARY_JSON = DEFAULT_ALPHA_CANDIDATE_BATCH_OUTPUT_ROOT / "batch_summary.json"

TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS = (
    "spy_vol_scaled_trend_20d_fixed",
    "spy_drawdown_recovery_252d_20_10_fixed",
)

REGIME_DIAGNOSIS_DECISIONS = (
    "reject_candidate",
    "keep_shadow",
    "needs_oos_backtest",
    "promote_to_paper_preview_candidate",
)

_SCHEMA_VERSION = "1"
_PHASE = "v4.1_top_two_regime_filter_diagnosis"
_SYMBOL = "SPY"
_BASIS = "adjusted_close"
_TIMEFRAME = "daily"
_BUY_AND_HOLD_STRATEGY_ID = "spy_buy_and_hold_comparator"
_SMA_STRATEGY_ID = "spy_sma_50_200_training_wheel"
_SMA_SHORT_WINDOW = 50
_SMA_LONG_WINDOW = 200
_VOL_LOOKBACK_WINDOW = 20
_VOL_HIGH_THRESHOLD = Decimal("0.25")
_DRAWDOWN_LOOKBACK_WINDOW = 252
_DRAWDOWN_CASH_TRIGGER = Decimal("-0.20")
_DRAWDOWN_RECOVERY_TRIGGER = Decimal("-0.10")
_TRADING_DAYS_PER_YEAR = Decimal("252")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_DEFAULT_INITIAL_EQUITY = Decimal("10000")
_DEFAULT_FEE_BPS = Decimal("0")
_DEFAULT_SLIPPAGE_BPS = Decimal("1")
_MIN_EFFECT_ROWS = 40
_KEY_WINDOW_IDS = (
    "chronological_later_half",
    "trailing_5y_later_half",
    "recent_3y_holdout",
)
_UNAVAILABLE_REGIME_IDS = (
    "sma50_200_unavailable",
    "vol20_unavailable",
    "drawdown_unavailable",
)
_LABELS = (
    "paper_lab_only",
    "research_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
)


@dataclass(frozen=True, slots=True)
class _RegimeDefinition:
    regime_type: str
    regime_id: str
    regime_label: str
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "regime_type": self.regime_type,
            "regime_id": self.regime_id,
            "regime_label": self.regime_label,
            "description": self.description,
        }


def regime_diagnosis_mutation_policy(decision: str) -> dict[str, object]:
    """Return the non-mutating policy for a v4.1 regime diagnosis decision."""
    checked_decision = _decision_value(decision)
    return {
        "decision_bucket": checked_decision,
        "broker_read_allowed": False,
        "broker_mutation_allowed": False,
        "paper_submit_allowed": False,
        "paper_mutation_allowed": False,
        "live_endpoint_allowed": False,
        "paper_preview_only": checked_decision == "promote_to_paper_preview_candidate",
        "promotion_scope": (
            "paper_preview_candidate_only"
            if checked_decision == "promote_to_paper_preview_candidate"
            else "research_shadow_only"
        ),
    }


def build_top_two_regime_diagnosis_packet(
    *,
    daily_bars_csv: Path | str = DEFAULT_ALPHA_CANDIDATE_BATCH_DAILY_BARS_CSV,
    prior_batch_summary_json: Path | str | None = DEFAULT_PRIOR_BATCH_SUMMARY_JSON,
    run_id: str = DEFAULT_REGIME_DIAGNOSIS_RUN_ID,
) -> dict[str, object]:
    """Diagnose only the v4.0 top-two needs-regime-filter candidates."""
    checked_run_id = _required_string(run_id, "run_id")
    spy_path = _path(daily_bars_csv, "daily_bars_csv")
    spy_result = load_local_daily_bars_csv(spy_path, symbol=_SYMBOL)
    bars = spy_result.usable_bars
    if len(bars) < 2:
        raise ValidationError("At least two SPY daily bars are required.")

    candidates = _top_two_candidate_definitions()
    indicators = _indicator_series(bars)
    assumptions = DailyBacktestAssumptions(
        initial_equity=_DEFAULT_INITIAL_EQUITY,
        fee_bps=_DEFAULT_FEE_BPS,
        slippage_bps=_DEFAULT_SLIPPAGE_BPS,
    )
    exposures_by_strategy = _top_two_strategy_exposures(bars=bars, indicators=indicators)
    windows = _window_slices(len(bars))

    records: list[dict[str, object]] = []
    for window in windows:
        window_bars = bars[window.start_index : window.end_index]
        window_snapshot = _snapshot(window_bars)
        window_results: dict[str, tuple[DailyBacktestPoint, ...]] = {}
        window_exposures: dict[str, tuple[DailyExposure, ...]] = {}

        for strategy_id, exposures in exposures_by_strategy.items():
            sliced_exposures = exposures[window.start_index : window.end_index]
            window_exposures[strategy_id] = sliced_exposures
            window_results[strategy_id] = run_daily_backtest(
                window_snapshot,
                sliced_exposures,
                assumptions,
            ).points

        for candidate in candidates:
            candidate_points = window_results[candidate.candidate_id]
            candidate_exposures = window_exposures[candidate.candidate_id]
            comparator_points = {
                _BUY_AND_HOLD_STRATEGY_ID: window_results[_BUY_AND_HOLD_STRATEGY_ID],
                _SMA_STRATEGY_ID: window_results[_SMA_STRATEGY_ID],
            }
            comparator_exposures = {
                _BUY_AND_HOLD_STRATEGY_ID: window_exposures[_BUY_AND_HOLD_STRATEGY_ID],
                _SMA_STRATEGY_ID: window_exposures[_SMA_STRATEGY_ID],
            }
            for regime in _regime_definitions_for_candidate(candidate.candidate_id):
                mask = _regime_mask(
                    regime=regime,
                    bars=bars,
                    indicators=indicators,
                    start_index=window.start_index,
                    end_index=window.end_index,
                )
                metrics = _attribution_metrics(
                    points=candidate_points,
                    exposures=candidate_exposures,
                    mask=mask,
                    assumptions=assumptions,
                )
                comparator_metrics = {
                    strategy_id: _attribution_metrics(
                        points=comparator_points[strategy_id],
                        exposures=comparator_exposures[strategy_id],
                        mask=mask,
                        assumptions=assumptions,
                    )
                    for strategy_id in (_BUY_AND_HOLD_STRATEGY_ID, _SMA_STRATEGY_ID)
                }
                delta_vs_buy = _comparison_payload(
                    candidate_metrics=metrics,
                    benchmark_metrics=comparator_metrics[_BUY_AND_HOLD_STRATEGY_ID],
                    benchmark_id=_BUY_AND_HOLD_STRATEGY_ID,
                )
                delta_vs_sma = _comparison_payload(
                    candidate_metrics=metrics,
                    benchmark_metrics=comparator_metrics[_SMA_STRATEGY_ID],
                    benchmark_id=_SMA_STRATEGY_ID,
                )
                effect = _regime_effect(
                    metrics=metrics,
                    delta_vs_buy_and_hold=delta_vs_buy,
                    delta_vs_sma50_200=delta_vs_sma,
                )
                records.append(
                    {
                        "record_type": "alpha_candidate_regime_diagnosis_candidate_regime_window",
                        "schema_version": _SCHEMA_VERSION,
                        "phase": _PHASE,
                        "run_id": checked_run_id,
                        "candidate_id": candidate.candidate_id,
                        "candidate_label": candidate.label,
                        "candidate_family": candidate.family,
                        "fixed_parameters": candidate.parameter_values,
                        "parameters_evaluated": candidate.parameters_evaluated,
                        "parameter_search_performed": False,
                        "threshold_optimization_performed": False,
                        "window_id": window.window_id,
                        "window_label": window.window_label,
                        "window_role": window.window_role,
                        "window_start_date": window_bars[0].date.isoformat(),
                        "window_end_date": window_bars[-1].date.isoformat(),
                        "window_row_count": window.row_count,
                        "regime_type": regime.regime_type,
                        "regime_id": regime.regime_id,
                        "regime_label": regime.regime_label,
                        "regime_description": regime.description,
                        "regime_bar_count": metrics["bar_count"],
                        "metrics": metrics,
                        "comparator_metrics": comparator_metrics,
                        "delta_vs_buy_and_hold": delta_vs_buy,
                        "delta_vs_sma50_200": delta_vs_sma,
                        "regime_effect": effect,
                        "regime_where_it_helped": regime.regime_id
                        if effect == "helped"
                        else None,
                        "regime_where_it_harmed": regime.regime_id
                        if effect == "harmed"
                        else None,
                    }
                )

    candidate_decisions = _candidate_decisions(candidates=candidates, records=records)
    decision_by_candidate = {
        str(item["candidate_id"]): item for item in candidate_decisions
    }
    for record in records:
        decision = _mapping(decision_by_candidate[str(record["candidate_id"])], "decision")
        final_decision = str(decision["final_decision"])
        record["final_decision"] = final_decision
        record["final_decision_rationale"] = decision["final_decision_rationale"]
        record["mutation_policy"] = regime_diagnosis_mutation_policy(final_decision)

    decision_counts = Counter(str(item["final_decision"]) for item in candidate_decisions)
    summary = {
        "record_type": "alpha_candidate_regime_diagnosis_summary",
        "schema_version": _SCHEMA_VERSION,
        "phase": _PHASE,
        "run_id": checked_run_id,
        "classification_recommendation": _classification_recommendation(candidate_decisions),
        "decision_options": list(REGIME_DIAGNOSIS_DECISIONS),
        "candidate_count": len(candidates),
        "analyzed_candidate_ids": list(TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS),
        "excluded_candidate_policy": (
            "Only the requested top-two v4.0 needs_regime_filter candidates were "
            "diagnosed; non-top-two candidates received no exposure, backtest, or "
            "regime analysis in this phase."
        ),
        "labels": list(_LABELS),
        "source_data": {
            "symbol": _SYMBOL,
            "basis": _BASIS,
            "timeframe": _TIMEFRAME,
            "daily_bars_csv": str(spy_path),
            "row_count": len(bars),
            "start_date": bars[0].date.isoformat(),
            "end_date": bars[-1].date.isoformat(),
            "local_csv_metadata": spy_result.source_metadata(),
        },
        "prior_v4_0_results": _prior_v4_0_payload(prior_batch_summary_json),
        "windows": [_window_payload(window, bars) for window in windows],
        "regime_definitions": _regime_definition_payload(candidates),
        "candidate_decisions": candidate_decisions,
        "final_decision_counts": dict(sorted(decision_counts.items())),
        "optimization_policy": _optimization_policy_payload(candidates),
        "decision_quality": _decision_quality_payload(candidate_decisions),
        "promotion_constraints": {
            "paper_mutation_promotion_allowed": False,
            "paper_preview_candidate_is_not_paper_mutation": True,
            "promotion_requires_stable_cost_aware_regime_specific_evidence": True,
            "mixed_or_fragile_evidence_defaults_to_shadow_or_oos": True,
        },
        "safety": _safety_payload(),
        "artifact_contract": {
            "summary_json": "regime_diagnosis_summary.json",
            "candidate_regime_by_window_jsonl": "candidate_regime_by_window.jsonl",
            "decision_brief_md": "decision_brief.md",
        },
    }
    return {
        "summary": summary,
        "candidate_regime_by_window": records,
    }


def write_top_two_regime_diagnosis_artifacts(
    packet: Mapping[str, object],
    output_root: Path | str = DEFAULT_REGIME_DIAGNOSIS_OUTPUT_ROOT,
) -> dict[str, Path]:
    """Write v4.1 regime diagnosis artifacts under an ignored runs tree."""
    root = _path_for_output(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)
    summary = _mapping(packet["summary"], "summary")
    records = _mapping_list(
        packet["candidate_regime_by_window"],
        "candidate_regime_by_window",
    )

    summary_path = root / "regime_diagnosis_summary.json"
    by_window_path = root / "candidate_regime_by_window.jsonl"
    brief_path = root / "decision_brief.md"

    summary_path.write_text(_json_dumps(summary) + "\n", encoding="utf-8", newline="\n")
    by_window_path.write_text(
        "".join(_json_dumps(record) + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )
    brief_path.write_text(
        render_top_two_regime_diagnosis_brief(summary),
        encoding="utf-8",
        newline="\n",
    )

    return {
        "regime_diagnosis_summary_json": summary_path,
        "candidate_regime_by_window_jsonl": by_window_path,
        "decision_brief_md": brief_path,
    }


def render_top_two_regime_diagnosis_brief(summary: Mapping[str, object]) -> str:
    """Render the operator-readable v4.1 decision brief."""
    decisions = _mapping_list(summary.get("candidate_decisions", []), "candidate_decisions")
    windows = _mapping_list(summary.get("windows", []), "windows")
    source = _mapping(summary.get("source_data", {}), "source_data")
    lines = [
        "# v4.1 Top-2 Regime Filter Diagnosis",
        "",
        "## Classification Recommendation",
        "",
        f"- recommendation: {summary.get('classification_recommendation')}",
        "- evidence_type: decision-quality regime diagnosis and local architecture capability",
        "- paper_mutation_promotion_performed: False",
        "- broker_network_access: none",
        "- profit_claim: none",
        "",
        "## Source Data",
        "",
        f"- SPY rows: {source.get('row_count')} from {source.get('start_date')} to {source.get('end_date')}",
        "- data access: existing local adjusted daily CSV only",
        "",
        "## Top-Two Candidates",
        "",
        "| candidate_id | final_decision | helped_regimes | harmed_regimes | rationale |",
        "| --- | --- | --- | --- | --- |",
    ]
    for decision in decisions:
        helped = ", ".join(str(item) for item in decision.get("regimes_where_helped", []))
        harmed = ", ".join(str(item) for item in decision.get("regimes_where_harmed", []))
        lines.append(
            "| {candidate_id} | {final_decision} | {helped} | {harmed} | {rationale} |".format(
                candidate_id=decision.get("candidate_id"),
                final_decision=decision.get("final_decision"),
                helped=_markdown_value(helped or "none"),
                harmed=_markdown_value(harmed or "none"),
                rationale=_markdown_value(decision.get("final_decision_rationale")),
            )
        )

    lines.extend(
        [
            "",
            "## Windows",
            "",
            "| window_id | role | rows | start | end |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for window in windows:
        lines.append(
            "| {window_id} | {role} | {rows} | {start} | {end} |".format(
                window_id=window.get("window_id"),
                role=window.get("window_role"),
                rows=window.get("row_count"),
                start=window.get("start_date"),
                end=window.get("end_date"),
            )
        )

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- No parameter search or threshold optimization was performed.",
            "- No broker read, broker mutation, paper submit, live endpoint, or network fetch was performed.",
            "- SMA50/200 remains the only paper-mutation-capable training-wheel strategy.",
            "- Any preview-candidate decision is research-only and cannot mutate broker state.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for local v4.1 artifact generation."""
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose only the v4.0 top-two needs_regime_filter candidates using "
            "local SPY adjusted daily data."
        )
    )
    parser.add_argument(
        "--daily-bars-csv",
        default=str(DEFAULT_ALPHA_CANDIDATE_BATCH_DAILY_BARS_CSV),
        help="Local SPY adjusted daily bars CSV.",
    )
    parser.add_argument(
        "--prior-batch-summary-json",
        default=str(DEFAULT_PRIOR_BATCH_SUMMARY_JSON),
        help="Optional local v4.0 batch summary JSON if available.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_REGIME_DIAGNOSIS_OUTPUT_ROOT),
        help="Ignored runs output directory.",
    )
    parser.add_argument(
        "--run-id",
        default=DEFAULT_REGIME_DIAGNOSIS_RUN_ID,
        help="Deterministic run id to include in artifacts.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local top-two regime diagnosis and write artifacts."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        packet = build_top_two_regime_diagnosis_packet(
            daily_bars_csv=args.daily_bars_csv,
            prior_batch_summary_json=args.prior_batch_summary_json,
            run_id=args.run_id,
        )
        paths = write_top_two_regime_diagnosis_artifacts(packet, args.output_root)
    except ValidationError as exc:
        print(f"alpha_candidate_regime_diagnosis_error={exc}")
        return 2

    print("alpha_candidate_regime_diagnosis_status=completed")
    for name, path in paths.items():
        print(f"{name}={path}")
    return 0


def _top_two_candidate_definitions() -> tuple[AlphaCandidateDefinition, ...]:
    definitions = {
        candidate.candidate_id: candidate
        for candidate in build_fixed_alpha_candidate_definitions()
    }
    missing = tuple(
        candidate_id
        for candidate_id in TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS
        if candidate_id not in definitions
    )
    if missing:
        raise ValidationError(f"Missing fixed candidate definitions: {missing}.")
    return tuple(
        definitions[candidate_id]
        for candidate_id in TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS
    )


def _top_two_strategy_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: object,
) -> dict[str, tuple[DailyExposure, ...]]:
    return {
        _BUY_AND_HOLD_STRATEGY_ID: tuple(
            DailyExposure(bar.date, _ONE) for bar in bars
        ),
        _SMA_STRATEGY_ID: tuple(
            DailyExposure(
                bar.date,
                _ONE
                if _sma_risk_on(indicators, index)
                else _ZERO,
            )
            for index, bar in enumerate(bars)
        ),
        "spy_vol_scaled_trend_20d_fixed": _vol_scaled_trend_exposures(
            bars=bars,
            indicators=indicators,
        ),
        "spy_drawdown_recovery_252d_20_10_fixed": _drawdown_recovery_exposures(
            bars=bars,
            indicators=indicators,
        ),
    }


def _candidate_decisions(
    *,
    candidates: tuple[AlphaCandidateDefinition, ...],
    records: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for candidate in candidates:
        candidate_records = [
            record
            for record in records
            if record["candidate_id"] == candidate.candidate_id
        ]
        decision, rationale, coherent = _final_candidate_decision(candidate_records)
        helped = sorted(
            {
                str(record["regime_id"])
                for record in candidate_records
                if record["regime_effect"] == "helped"
            }
        )
        harmed = sorted(
            {
                str(record["regime_id"])
                for record in candidate_records
                if record["regime_effect"] == "harmed"
            }
        )
        results.append(
            {
                "candidate_id": candidate.candidate_id,
                "candidate_label": candidate.label,
                "candidate_family": candidate.family,
                "fixed_parameters": candidate.parameter_values,
                "parameters_evaluated": candidate.parameters_evaluated,
                "final_decision": decision,
                "final_decision_rationale": rationale,
                "coherent_regime_roles": coherent,
                "regimes_where_helped": helped,
                "regimes_where_harmed": harmed,
                "window_effect_counts": _candidate_effect_counts(candidate_records),
                "mutation_policy": regime_diagnosis_mutation_policy(decision),
            }
        )
    return results


def _final_candidate_decision(
    records: Sequence[Mapping[str, object]],
) -> tuple[str, str, list[str]]:
    key_overall = [
        record
        for record in records
        if record["window_id"] in _KEY_WINDOW_IDS and record["regime_id"] == "all_rows"
    ]
    key_diagnostics = [
        record
        for record in records
        if record["window_id"] in _KEY_WINDOW_IDS
        and record["regime_id"] not in ("all_rows", *_UNAVAILABLE_REGIME_IDS)
        and int(record["regime_bar_count"]) >= _MIN_EFFECT_ROWS
    ]
    helped = [record for record in key_diagnostics if record["regime_effect"] == "helped"]
    harmed = [record for record in key_diagnostics if record["regime_effect"] == "harmed"]
    coherent = _coherent_regime_roles(key_diagnostics)

    if (
        len(key_overall) == len(_KEY_WINDOW_IDS)
        and all(record["regime_effect"] == "helped" for record in key_overall)
        and coherent
        and not harmed
    ):
        return (
            "promote_to_paper_preview_candidate",
            (
                "Stable cost-aware overall and regime-specific evidence improved "
                "risk-adjusted behavior in all key windows; preview only, no paper "
                "mutation."
            ),
            coherent,
        )

    if coherent and len(harmed) <= len(helped):
        return (
            "needs_oos_backtest",
            (
                "At least one deterministic regime helped across multiple key "
                "windows, including recent evidence, but the evidence is not strong "
                "enough for preview quarantine."
            ),
            coherent,
        )

    if not helped and (
        harmed
        or all(_underperformed_both_comparators(record) for record in key_overall)
    ):
        return (
            "reject_candidate",
            (
                "No supported key-window regime showed help and the candidate either "
                "harmed regimes or underperformed both comparators overall."
            ),
            coherent,
        )

    return (
        "keep_shadow",
        (
            "Regime evidence is mixed or fragile; keep as research shadow only and "
            "do not advance to paper-preview quarantine."
        ),
        coherent,
    )


def _coherent_regime_roles(records: Sequence[Mapping[str, object]]) -> list[str]:
    coherent: list[str] = []
    regime_ids = sorted({str(record["regime_id"]) for record in records})
    for regime_id in regime_ids:
        regime_records = [
            record for record in records if str(record["regime_id"]) == regime_id
        ]
        helped_count = sum(1 for record in regime_records if record["regime_effect"] == "helped")
        harmed_count = sum(1 for record in regime_records if record["regime_effect"] == "harmed")
        has_recent = any(record["window_id"] == "recent_3y_holdout" for record in regime_records)
        if helped_count >= 2 and harmed_count == 0 and has_recent:
            coherent.append(regime_id)
    return coherent


def _candidate_effect_counts(records: Sequence[Mapping[str, object]]) -> dict[str, object]:
    counts = Counter(str(record["regime_effect"]) for record in records)
    return dict(sorted(counts.items()))


def _classification_recommendation(
    candidate_decisions: Sequence[Mapping[str, object]],
) -> str:
    decisions = {str(item["final_decision"]) for item in candidate_decisions}
    if "promote_to_paper_preview_candidate" in decisions:
        return "review_preview_candidate_quarantine_without_paper_mutation"
    if "needs_oos_backtest" in decisions:
        return "run_targeted_oos_backtest_for_regime_candidate"
    if decisions == {"reject_candidate"}:
        return "reject_top_two_candidates"
    return "keep_shadow_research_only"


def _regime_definitions_for_candidate(candidate_id: str) -> tuple[_RegimeDefinition, ...]:
    common = (
        _RegimeDefinition(
            regime_type="overall_window",
            regime_id="all_rows",
            regime_label="all rows",
            description="All rows in the deterministic window.",
        ),
        _RegimeDefinition(
            regime_type="sma50_200_trend",
            regime_id="sma50_gt_sma200",
            regime_label="SMA50 > SMA200",
            description="Risk-on trend regime using the existing SMA50/200 definition.",
        ),
        _RegimeDefinition(
            regime_type="sma50_200_trend",
            regime_id="sma50_lte_sma200",
            regime_label="SMA50 <= SMA200",
            description="Risk-off trend regime when both SMAs are available.",
        ),
        _RegimeDefinition(
            regime_type="sma50_200_trend",
            regime_id="sma50_200_unavailable",
            regime_label="SMA50/200 unavailable",
            description="Insufficient history for the SMA50/200 trend regime.",
        ),
    )
    if candidate_id == "spy_vol_scaled_trend_20d_fixed":
        return common + (
            _RegimeDefinition(
                regime_type="volatility_regime",
                regime_id="vol20_high_gt_25pct",
                regime_label="20-day annualized volatility > 25%",
                description="High-volatility regime from the candidate's fixed definition.",
            ),
            _RegimeDefinition(
                regime_type="volatility_regime",
                regime_id="vol20_normal_lte_25pct",
                regime_label="20-day annualized volatility <= 25%",
                description="Normal-volatility regime from the candidate's fixed definition.",
            ),
            _RegimeDefinition(
                regime_type="volatility_regime",
                regime_id="vol20_unavailable",
                regime_label="20-day volatility unavailable",
                description="Insufficient history for the fixed volatility definition.",
            ),
        )
    if candidate_id == "spy_drawdown_recovery_252d_20_10_fixed":
        return common + (
            _RegimeDefinition(
                regime_type="drawdown_bucket",
                regime_id="drawdown_recovered_ge_minus_10pct",
                regime_label="drawdown >= -10%",
                description="Recovered or near-high bucket from prior 252-day high.",
            ),
            _RegimeDefinition(
                regime_type="drawdown_bucket",
                regime_id="drawdown_between_minus_20_and_minus_10pct",
                regime_label="-20% < drawdown < -10%",
                description="Middle drawdown bucket between the fixed cash and reentry triggers.",
            ),
            _RegimeDefinition(
                regime_type="drawdown_bucket",
                regime_id="drawdown_deep_le_minus_20pct",
                regime_label="drawdown <= -20%",
                description="Deep drawdown bucket at or beyond the fixed cash trigger.",
            ),
            _RegimeDefinition(
                regime_type="drawdown_bucket",
                regime_id="drawdown_unavailable",
                regime_label="252-day prior high unavailable",
                description="Insufficient history for the fixed drawdown definition.",
            ),
        )
    raise ValidationError(f"Unsupported top-two candidate id: {candidate_id}.")


def _regime_mask(
    *,
    regime: _RegimeDefinition,
    bars: tuple[LocalDailyBar, ...],
    indicators: object,
    start_index: int,
    end_index: int,
) -> tuple[bool, ...]:
    result: list[bool] = []
    for index in range(start_index, end_index):
        result.append(_regime_includes_index(regime, bars, indicators, index))
    return tuple(result)


def _regime_includes_index(
    regime: _RegimeDefinition,
    bars: tuple[LocalDailyBar, ...],
    indicators: object,
    index: int,
) -> bool:
    if regime.regime_id == "all_rows":
        return True

    sma50 = getattr(indicators, "sma50")[index]
    sma200 = getattr(indicators, "sma200")[index]
    if regime.regime_id == "sma50_gt_sma200":
        return sma50 is not None and sma200 is not None and sma50 > sma200
    if regime.regime_id == "sma50_lte_sma200":
        return sma50 is not None and sma200 is not None and sma50 <= sma200
    if regime.regime_id == "sma50_200_unavailable":
        return sma50 is None or sma200 is None

    vol20 = getattr(indicators, "annualized_vol20")[index]
    if regime.regime_id == "vol20_high_gt_25pct":
        return vol20 is not None and vol20 > _VOL_HIGH_THRESHOLD
    if regime.regime_id == "vol20_normal_lte_25pct":
        return vol20 is not None and vol20 <= _VOL_HIGH_THRESHOLD
    if regime.regime_id == "vol20_unavailable":
        return vol20 is None

    prior_high = getattr(indicators, "prior_high252")[index]
    if prior_high is None:
        return regime.regime_id == "drawdown_unavailable"
    drawdown = (bars[index].adjusted_close / prior_high) - _ONE
    if regime.regime_id == "drawdown_recovered_ge_minus_10pct":
        return drawdown >= _DRAWDOWN_RECOVERY_TRIGGER
    if regime.regime_id == "drawdown_between_minus_20_and_minus_10pct":
        return _DRAWDOWN_CASH_TRIGGER < drawdown < _DRAWDOWN_RECOVERY_TRIGGER
    if regime.regime_id == "drawdown_deep_le_minus_20pct":
        return drawdown <= _DRAWDOWN_CASH_TRIGGER
    if regime.regime_id == "drawdown_unavailable":
        return False

    raise ValidationError(f"Unsupported regime id: {regime.regime_id}.")


def _sma_risk_on(indicators: object, index: int) -> bool:
    sma50 = getattr(indicators, "sma50")[index]
    sma200 = getattr(indicators, "sma200")[index]
    return sma50 is not None and sma200 is not None and sma50 > sma200


def _attribution_metrics(
    *,
    points: tuple[DailyBacktestPoint, ...],
    exposures: tuple[DailyExposure, ...],
    mask: Sequence[bool],
    assumptions: DailyBacktestAssumptions,
) -> dict[str, object]:
    if len(points) != len(exposures) or len(points) != len(mask):
        raise ValidationError("points, exposures, and regime mask must align.")

    indexes = tuple(index for index, include in enumerate(mask) if include)
    if not indexes:
        return _empty_metrics(assumptions)

    equity = _ONE
    peak = _ONE
    worst_drawdown = _ZERO
    returns: list[Decimal] = []
    for index in indexes:
        daily_return = points[index].strategy_return_after_costs
        returns.append(daily_return)
        equity *= _ONE + daily_return
        if equity > peak:
            peak = equity
        drawdown = (equity / peak) - _ONE
        if drawdown < worst_drawdown:
            worst_drawdown = drawdown

    total_return = equity - _ONE
    exposure_ratio = sum((points[index].exposure for index in indexes), _ZERO) / Decimal(
        len(indexes)
    )
    holding = _holding_stats(points=points, mask=mask)
    return {
        "bar_count": len(indexes),
        "total_return": total_return,
        "annualized_return": _annualized_return(total_return, len(indexes)),
        "max_drawdown": -worst_drawdown,
        "sharpe_like_score": _sharpe_like_score(tuple(returns)),
        "exposure_ratio": exposure_ratio,
        "exposure_pct": exposure_ratio * _HUNDRED,
        "trade_count": _transition_count(exposures=exposures, mask=mask),
        "average_holding_period_days": holding["average_holding_period_days"],
        "holding_period_count": holding["holding_period_count"],
        "daily_return_count": len(returns),
        "cost_slippage_assumptions": _assumptions_payload(assumptions),
    }


def _empty_metrics(assumptions: DailyBacktestAssumptions) -> dict[str, object]:
    return {
        "bar_count": 0,
        "total_return": None,
        "annualized_return": None,
        "max_drawdown": None,
        "sharpe_like_score": None,
        "exposure_ratio": None,
        "exposure_pct": None,
        "trade_count": 0,
        "average_holding_period_days": None,
        "holding_period_count": 0,
        "daily_return_count": 0,
        "cost_slippage_assumptions": _assumptions_payload(assumptions),
    }


def _comparison_payload(
    *,
    candidate_metrics: Mapping[str, object],
    benchmark_metrics: Mapping[str, object],
    benchmark_id: str,
) -> dict[str, object]:
    total_delta = _optional_metric_delta(candidate_metrics, benchmark_metrics, "total_return")
    annualized_delta = _optional_metric_delta(
        candidate_metrics,
        benchmark_metrics,
        "annualized_return",
    )
    drawdown_delta = _optional_metric_delta(
        candidate_metrics,
        benchmark_metrics,
        "max_drawdown",
    )
    sharpe_delta = _optional_metric_delta(
        candidate_metrics,
        benchmark_metrics,
        "sharpe_like_score",
    )
    return {
        "benchmark_id": benchmark_id,
        "total_return_delta": total_delta,
        "total_return_relation": _optional_relation(total_delta),
        "annualized_return_delta": annualized_delta,
        "annualized_return_relation": _optional_relation(annualized_delta),
        "max_drawdown_delta": drawdown_delta,
        "max_drawdown_relation": _optional_drawdown_relation(drawdown_delta),
        "max_drawdown_delta_interpretation": "negative_is_lower_drawdown",
        "sharpe_like_score_delta": sharpe_delta,
        "sharpe_like_score_relation": _optional_relation(sharpe_delta),
    }


def _regime_effect(
    *,
    metrics: Mapping[str, object],
    delta_vs_buy_and_hold: Mapping[str, object],
    delta_vs_sma50_200: Mapping[str, object],
) -> str:
    if int(metrics["bar_count"]) < _MIN_EFFECT_ROWS:
        return "insufficient_regime_observations"

    improved_buy = _risk_adjusted_improved(delta_vs_buy_and_hold)
    improved_sma = _risk_adjusted_improved(delta_vs_sma50_200)
    harmed_buy = _risk_adjusted_harmed(delta_vs_buy_and_hold)
    harmed_sma = _risk_adjusted_harmed(delta_vs_sma50_200)

    if (improved_buy or improved_sma) and not (harmed_buy and harmed_sma):
        return "helped"
    if harmed_buy and harmed_sma:
        return "harmed"
    return "mixed"


def _risk_adjusted_improved(delta: Mapping[str, object]) -> bool:
    total = _optional_metric_decimal(delta, "total_return_delta")
    drawdown = _optional_metric_decimal(delta, "max_drawdown_delta")
    sharpe = _optional_metric_decimal(delta, "sharpe_like_score_delta")
    if total is None or drawdown is None:
        return False
    return (
        total >= _ZERO
        and drawdown <= _ZERO
        and (sharpe is None or sharpe >= _ZERO)
    ) or (drawdown < _ZERO and sharpe is not None and sharpe > _ZERO)


def _risk_adjusted_harmed(delta: Mapping[str, object]) -> bool:
    total = _optional_metric_decimal(delta, "total_return_delta")
    drawdown = _optional_metric_decimal(delta, "max_drawdown_delta")
    sharpe = _optional_metric_decimal(delta, "sharpe_like_score_delta")
    if total is None or drawdown is None:
        return False
    return (
        total < _ZERO
        and drawdown >= _ZERO
        and (sharpe is None or sharpe < _ZERO)
    )


def _underperformed_both_comparators(record: Mapping[str, object]) -> bool:
    return _risk_adjusted_harmed(_mapping(record["delta_vs_buy_and_hold"], "buy")) and (
        _risk_adjusted_harmed(_mapping(record["delta_vs_sma50_200"], "sma"))
    )


def _transition_count(
    *,
    exposures: tuple[DailyExposure, ...],
    mask: Sequence[bool],
) -> int:
    count = 0
    for index, include in enumerate(mask):
        if not include:
            continue
        previous = _ZERO if index == 0 else exposures[index - 1].exposure
        if exposures[index].exposure != previous:
            count += 1
    return count


def _holding_stats(
    *,
    points: tuple[DailyBacktestPoint, ...],
    mask: Sequence[bool],
) -> dict[str, object]:
    durations: list[int] = []
    current_duration = 0
    for point, include in zip(points, mask):
        if include and point.exposure > _ZERO:
            current_duration += 1
        elif current_duration:
            durations.append(current_duration)
            current_duration = 0
    if current_duration:
        durations.append(current_duration)

    average = None
    if durations:
        average = sum(Decimal(value) for value in durations) / Decimal(len(durations))
    return {
        "holding_period_count": len(durations),
        "average_holding_period_days": average,
    }


def _annualized_return(total_return: Decimal, point_count: int) -> Decimal | None:
    if point_count <= 1:
        return None
    if total_return <= -_ONE:
        return None
    exponent = float(_TRADING_DAYS_PER_YEAR / Decimal(point_count - 1))
    return _decimal_from_float((float(_ONE + total_return) ** exponent) - 1.0)


def _sharpe_like_score(daily_returns: tuple[Decimal, ...]) -> Decimal | None:
    if len(daily_returns) < 2:
        return None
    values = [float(item) for item in daily_returns]
    volatility = stdev(values)
    if volatility == 0:
        return None
    average = sum(values) / len(values)
    return _decimal_from_float((average / volatility) * math.sqrt(252.0))


def _prior_v4_0_payload(prior_batch_summary_json: Path | str | None) -> dict[str, object]:
    if prior_batch_summary_json is None:
        return {"available": False, "used_for_candidate_scope": False}
    path = Path(prior_batch_summary_json)
    if not path.is_file():
        return {
            "available": False,
            "used_for_candidate_scope": False,
            "path": str(path),
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("prior_batch_summary_json must be readable JSON.") from exc
    ranked = _mapping_list(payload.get("ranked_candidates", []), "ranked_candidates")
    prior_candidates = [
        {
            "candidate_id": item.get("candidate_id"),
            "rank": item.get("rank"),
            "final_decision": item.get("final_decision"),
            "aggregate_score": item.get("aggregate_score"),
        }
        for item in ranked
        if item.get("candidate_id") in TOP_TWO_REGIME_DIAGNOSIS_CANDIDATE_IDS
    ]
    return {
        "available": True,
        "used_for_candidate_scope": True,
        "path": str(path),
        "phase": payload.get("phase"),
        "classification_recommendation": payload.get("classification_recommendation"),
        "top_two_prior_results": prior_candidates,
    }


def _window_payload(window: object, bars: tuple[LocalDailyBar, ...]) -> dict[str, object]:
    window_bars = bars[window.start_index : window.end_index]
    return {
        "window_id": window.window_id,
        "window_label": window.window_label,
        "window_role": window.window_role,
        "start_index": window.start_index,
        "end_index_exclusive": window.end_index,
        "row_count": window.row_count,
        "start_date": window_bars[0].date.isoformat(),
        "end_date": window_bars[-1].date.isoformat(),
        "description": window.description,
    }


def _regime_definition_payload(
    candidates: tuple[AlphaCandidateDefinition, ...],
) -> dict[str, object]:
    return {
        candidate.candidate_id: [
            regime.to_dict()
            for regime in _regime_definitions_for_candidate(candidate.candidate_id)
        ]
        for candidate in candidates
    }


def _optimization_policy_payload(
    candidates: tuple[AlphaCandidateDefinition, ...],
) -> dict[str, object]:
    return {
        "fixed_parameter_declaration": "predeclared_before_testing",
        "parameter_search_performed": False,
        "threshold_optimization_performed": False,
        "optimization_performed": False,
        "parameter_sets_evaluated_per_candidate": {
            candidate.candidate_id: 1 for candidate in candidates
        },
        "parameters_evaluated": {
            candidate.candidate_id: candidate.parameters_evaluated for candidate in candidates
        },
    }


def _decision_quality_payload(
    candidate_decisions: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    promoted = [
        item
        for item in candidate_decisions
        if item["final_decision"] == "promote_to_paper_preview_candidate"
    ]
    rejected = [
        item for item in candidate_decisions if item["final_decision"] == "reject_candidate"
    ]
    oos = [
        item for item in candidate_decisions if item["final_decision"] == "needs_oos_backtest"
    ]
    return {
        "decision_quality_evidence_produced": True,
        "architecture_capability_produced": True,
        "process_overhead_only": False,
        "search_space_narrowed": True,
        "promoted_preview_candidate_count": len(promoted),
        "rejected_candidate_count": len(rejected),
        "needs_oos_backtest_count": len(oos),
        "alpha_or_profit_claim": "none",
    }


def _safety_payload() -> dict[str, object]:
    return {
        "broker_access_attempted": False,
        "broker_read_performed": False,
        "broker_mutation_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_attempted": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "paper_mutation_promotion_performed": False,
        "llm_in_trading_hot_path": False,
        "research_only": True,
        "offline_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
    }


def _assumptions_payload(assumptions: DailyBacktestAssumptions) -> dict[str, object]:
    return {
        "initial_equity": assumptions.initial_equity,
        "fee_bps": assumptions.fee_bps,
        "slippage_bps": assumptions.slippage_bps,
        "total_cost_bps_per_full_exposure_transition": (
            assumptions.fee_bps + assumptions.slippage_bps
        ),
        "cost_model": (
            "regime attribution uses daily_backtest after-cost returns; "
            "daily_backtest applies abs(exposure_delta) * "
            "(fee_bps + slippage_bps) / 10000"
        ),
    }


def _optional_metric_delta(
    first: Mapping[str, object],
    second: Mapping[str, object],
    field_name: str,
) -> Decimal | None:
    first_value = _optional_metric_decimal(first, field_name)
    second_value = _optional_metric_decimal(second, field_name)
    if first_value is None or second_value is None:
        return None
    return first_value - second_value


def _optional_metric_decimal(
    value: Mapping[str, object],
    field_name: str,
) -> Decimal | None:
    if field_name not in value:
        raise ValidationError(f"{field_name} is missing.")
    raw = value[field_name]
    if raw is None:
        return None
    return _decimal_value(raw, field_name)


def _optional_relation(delta: Decimal | None) -> str:
    if delta is None:
        return "not_supported"
    if delta > _ZERO:
        return "above"
    if delta < _ZERO:
        return "below"
    return "equal"


def _optional_drawdown_relation(delta: Decimal | None) -> str:
    if delta is None:
        return "not_supported"
    if delta < _ZERO:
        return "lower_drawdown"
    if delta > _ZERO:
        return "higher_drawdown"
    return "equal_drawdown"


def _decision_value(value: object) -> str:
    text = _required_string(value, "decision")
    if text not in REGIME_DIAGNOSIS_DECISIONS:
        raise ValidationError("decision must be a supported regime diagnosis decision.")
    return text


def _path(value: Path | str, field_name: str) -> Path:
    if not isinstance(value, (str, Path)):
        raise ValidationError(f"{field_name} must be a local path.")
    if isinstance(value, str) and "://" in value:
        raise ValidationError(f"{field_name} must be a local path.")
    path = Path(value)
    if not path.is_file():
        raise ValidationError(f"{field_name} must reference an existing local file.")
    return path


def _path_for_output(value: Path | str, field_name: str) -> Path:
    if not isinstance(value, (str, Path)):
        raise ValidationError(f"{field_name} must be a local path.")
    if isinstance(value, str) and "://" in value:
        raise ValidationError(f"{field_name} must be a local path.")
    return Path(value)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _mapping_list(value: object, field_name: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list.")
    if not all(isinstance(item, Mapping) for item in value):
        raise ValidationError(f"{field_name} must contain mappings.")
    return value


def _decimal_value(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        checked = value
    elif isinstance(value, str):
        try:
            checked = Decimal(value)
        except InvalidOperation as exc:
            raise ValidationError(f"{field_name} must be a Decimal string.") from exc
    else:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not checked.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return checked


def _decimal_from_float(value: float) -> Decimal:
    if not math.isfinite(value):
        raise ValidationError("float metric must be finite.")
    return Decimal(str(round(value, 10)))


def _decimal_text(value: Decimal) -> str:
    return str(_decimal_value(value, "decimal"))


def _json_dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _markdown_value(value: object) -> str:
    text = str(value).replace("|", "/").replace("\n", " ")
    return text


if __name__ == "__main__":
    raise SystemExit(main())
