"""Fixed-parameter alpha candidate batch scout for local SPY daily data."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import stdev

from algotrader.errors import ValidationError
from algotrader.research.daily_backtest import (
    DailyBacktestAssumptions,
    DailyBacktestResult,
    DailyExposure,
    run_daily_backtest,
)
from algotrader.research.local_daily_bars import LocalDailyBar, load_local_daily_bars_csv
from algotrader.research.price_snapshot import (
    HistoricalPriceBar,
    HistoricalPriceSnapshot,
    price_snapshot_fingerprint,
)

__all__ = [
    "ALPHA_CANDIDATE_BATCH_SCOUT_DECISIONS",
    "AlphaCandidateDefinition",
    "alpha_candidate_mutation_policy",
    "build_alpha_candidate_batch_packet",
    "build_fixed_alpha_candidate_definitions",
    "write_alpha_candidate_batch_artifacts",
]


DEFAULT_ALPHA_CANDIDATE_BATCH_DAILY_BARS_CSV = Path(
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
DEFAULT_ALPHA_CANDIDATE_BATCH_QQQ_DAILY_BARS_CSV = Path(
    "runs/operator_input/qqq_daily_tiingo_adjusted_canonical.csv"
)
DEFAULT_ALPHA_CANDIDATE_BATCH_OUTPUT_ROOT = Path(
    "runs/strategy_challengers/alpha_candidate_batch_scout/latest"
)
DEFAULT_ALPHA_CANDIDATE_BATCH_RUN_ID = "v4_0_alpha_candidate_batch_scout"

ALPHA_CANDIDATE_BATCH_SCOUT_DECISIONS = (
    "reject_candidate",
    "keep_shadow",
    "needs_regime_filter",
    "needs_longer_oos",
    "promote_to_paper_preview_candidate",
)

_SCHEMA_VERSION = "1"
_PHASE = "v4.0_alpha_candidate_batch_scout"
_SYMBOL = "SPY"
_QQQ = "QQQ"
_BASIS = "adjusted_close"
_TIMEFRAME = "daily"
_TRADING_DAYS_PER_YEAR = Decimal("252")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_HALF = Decimal("0.5")
_HUNDRED = Decimal("100")
_DEFAULT_INITIAL_EQUITY = Decimal("10000")
_DEFAULT_FEE_BPS = Decimal("0")
_DEFAULT_SLIPPAGE_BPS = Decimal("1")
_SMA_SHORT_WINDOW = 50
_SMA_LONG_WINDOW = 200
_SMA_SLOPE_WINDOW = 20
_PULLBACK_SMA_WINDOW = 20
_RSI_LOOKBACK_WINDOW = 14
_RSI_OVERSOLD_THRESHOLD = Decimal("30")
_RSI_OVERBOUGHT_THRESHOLD = Decimal("70")
_MEAN_REVERSION_RSI_WINDOW = 2
_MEAN_REVERSION_RSI_ENTRY = Decimal("10")
_MEAN_REVERSION_RSI_EXIT = Decimal("70")
_VOL_LOOKBACK_WINDOW = 20
_VOL_HIGH_THRESHOLD = Decimal("0.25")
_BREAKOUT_LOOKBACK_WINDOW = 252
_BREAKOUT_TRAILING_LOW_WINDOW = 63
_DRAWDOWN_LOOKBACK_WINDOW = 252
_DRAWDOWN_CASH_TRIGGER = Decimal("-0.20")
_DRAWDOWN_RECOVERY_TRIGGER = Decimal("-0.10")
_RELATIVE_STRENGTH_LOOKBACK_WINDOW = 126
_THREE_YEAR_ROW_COUNT = 252 * 3
_FIVE_YEAR_ROW_COUNT = 252 * 5
_MINIMUM_WINDOW_ROWS = _SMA_LONG_WINDOW
_MINIMUM_DECISION_QUALITY_ROWS = _FIVE_YEAR_ROW_COUNT

_BUY_AND_HOLD_STRATEGY_ID = "spy_buy_and_hold_comparator"
_SMA_STRATEGY_ID = "spy_sma_50_200_training_wheel"
_REJECTED_RSI_STRATEGY_ID = "spy_rsi_14_mean_reversion_rejected_comparator"
_REJECTED_TREND_PULLBACK_STRATEGY_ID = (
    "spy_trend_pullback_sma50_200_sma20_recovery_rejected_comparator"
)

_CANDIDATE_ORDER = (
    "spy_vol_scaled_trend_20d_fixed",
    "spy_breakout_252d_trailing_63d_fixed",
    "spy_drawdown_recovery_252d_20_10_fixed",
    "spy_ma200_slope_20d_filter_fixed",
    "spy_rsi2_mean_reversion_trend_filter_fixed",
    "spy_vs_qqq_relative_strength_126d_fixed",
)

_COMPARATOR_ORDER = (
    _BUY_AND_HOLD_STRATEGY_ID,
    _SMA_STRATEGY_ID,
    _REJECTED_RSI_STRATEGY_ID,
    _REJECTED_TREND_PULLBACK_STRATEGY_ID,
)

_STRATEGY_ORDER = _COMPARATOR_ORDER + _CANDIDATE_ORDER

_LABELS = (
    "paper_lab_only",
    "research_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
)


@dataclass(frozen=True, slots=True)
class AlphaCandidateDefinition:
    """Immutable fixed-parameter strategy candidate declaration."""

    candidate_id: str
    label: str
    family: str
    parameters: tuple[tuple[str, object], ...]
    entry_rule: str
    exit_rule: str
    insufficient_history_rule: str
    data_dependencies: tuple[str, ...] = (_SYMBOL,)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _required_string(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(self, "label", _required_string(self.label, "label"))
        object.__setattr__(self, "family", _required_string(self.family, "family"))
        object.__setattr__(
            self,
            "parameters",
            _parameter_tuple(self.parameters),
        )
        object.__setattr__(
            self,
            "entry_rule",
            _required_string(self.entry_rule, "entry_rule"),
        )
        object.__setattr__(self, "exit_rule", _required_string(self.exit_rule, "exit_rule"))
        object.__setattr__(
            self,
            "insufficient_history_rule",
            _required_string(
                self.insufficient_history_rule,
                "insufficient_history_rule",
            ),
        )
        object.__setattr__(
            self,
            "data_dependencies",
            tuple(_required_string(item, "data_dependency") for item in self.data_dependencies),
        )

    @property
    def parameter_values(self) -> dict[str, object]:
        """Return JSON-safe fixed parameter values."""
        return {name: _json_safe(value) for name, value in self.parameters}

    @property
    def parameters_evaluated(self) -> dict[str, list[object]]:
        """Return the single evaluated value per fixed parameter."""
        return {name: [_json_safe(value)] for name, value in self.parameters}

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic artifact representation."""
        return {
            "candidate_id": self.candidate_id,
            "label": self.label,
            "family": self.family,
            "fixed_parameter": True,
            "parameter_values": self.parameter_values,
            "parameters_evaluated": self.parameters_evaluated,
            "parameter_search_performed": False,
            "threshold_optimization_performed": False,
            "entry_rule": self.entry_rule,
            "exit_rule": self.exit_rule,
            "insufficient_history_rule": self.insufficient_history_rule,
            "data_dependencies": list(self.data_dependencies),
            "mutation_policy": alpha_candidate_mutation_policy("keep_shadow"),
        }


@dataclass(frozen=True, slots=True)
class _WindowSlice:
    window_id: str
    window_label: str
    window_role: str
    start_index: int
    end_index: int
    description: str

    @property
    def row_count(self) -> int:
        return self.end_index - self.start_index


@dataclass(frozen=True, slots=True)
class _IndicatorSeries:
    sma20: tuple[Decimal | None, ...]
    sma50: tuple[Decimal | None, ...]
    sma200: tuple[Decimal | None, ...]
    rsi2: tuple[Decimal | None, ...]
    rsi14: tuple[Decimal | None, ...]
    annualized_vol20: tuple[Decimal | None, ...]
    prior_high252: tuple[Decimal | None, ...]
    prior_low63: tuple[Decimal | None, ...]


def build_fixed_alpha_candidate_definitions() -> tuple[AlphaCandidateDefinition, ...]:
    """Return the predeclared v4.0 fixed candidate batch."""
    return (
        AlphaCandidateDefinition(
            candidate_id="spy_vol_scaled_trend_20d_fixed",
            label="SPY volatility-scaled SMA50/200 trend",
            family="volatility_scaled_trend",
            parameters=(
                ("short_sma_window", _SMA_SHORT_WINDOW),
                ("long_sma_window", _SMA_LONG_WINDOW),
                ("realized_volatility_window", _VOL_LOOKBACK_WINDOW),
                ("high_volatility_annualized_threshold", _VOL_HIGH_THRESHOLD),
                ("high_volatility_exposure", _HALF),
            ),
            entry_rule=(
                "Long SPY when SMA50 > SMA200; use 0.5 exposure when fixed 20-day "
                "annualized realized volatility is above 25%."
            ),
            exit_rule="Cash when SMA50 <= SMA200.",
            insufficient_history_rule="Cash until SMA200 and 20-day volatility are available.",
        ),
        AlphaCandidateDefinition(
            candidate_id="spy_breakout_252d_trailing_63d_fixed",
            label="SPY 252-day breakout with 63-day trailing low exit",
            family="breakout_trailing_high",
            parameters=(
                ("breakout_prior_high_window", _BREAKOUT_LOOKBACK_WINDOW),
                ("trailing_low_exit_window", _BREAKOUT_TRAILING_LOW_WINDOW),
            ),
            entry_rule="Enter long when adjusted_close is above the prior 252-day high.",
            exit_rule="Exit when adjusted_close is below the prior 63-day low.",
            insufficient_history_rule="Cash until the 252-day breakout window is available.",
        ),
        AlphaCandidateDefinition(
            candidate_id="spy_drawdown_recovery_252d_20_10_fixed",
            label="SPY 252-day drawdown recovery hysteresis",
            family="drawdown_recovery",
            parameters=(
                ("rolling_high_window", _DRAWDOWN_LOOKBACK_WINDOW),
                ("cash_trigger_drawdown", _DRAWDOWN_CASH_TRIGGER),
                ("recovery_reentry_drawdown", _DRAWDOWN_RECOVERY_TRIGGER),
            ),
            entry_rule=(
                "Enter or re-enter long when drawdown from prior 252-day high has "
                "recovered to -10% or better."
            ),
            exit_rule="Exit to cash when drawdown from prior 252-day high reaches -20% or worse.",
            insufficient_history_rule="Cash until the 252-day high window is available.",
        ),
        AlphaCandidateDefinition(
            candidate_id="spy_ma200_slope_20d_filter_fixed",
            label="SPY MA200 positive 20-day slope filter",
            family="moving_average_slope_filter",
            parameters=(
                ("trend_sma_window", _SMA_LONG_WINDOW),
                ("slope_lookback_days", _SMA_SLOPE_WINDOW),
            ),
            entry_rule="Long SPY when adjusted_close > SMA200 and SMA200 is above its value 20 bars ago.",
            exit_rule="Cash when adjusted_close <= SMA200 or SMA200 slope is non-positive.",
            insufficient_history_rule="Cash until SMA200 and the 20-day SMA200 slope are available.",
        ),
        AlphaCandidateDefinition(
            candidate_id="spy_rsi2_mean_reversion_trend_filter_fixed",
            label="SPY RSI2 mean reversion with SMA50/200 trend filter",
            family="mean_reversion_with_trend_filter",
            parameters=(
                ("trend_short_sma_window", _SMA_SHORT_WINDOW),
                ("trend_long_sma_window", _SMA_LONG_WINDOW),
                ("rsi_window", _MEAN_REVERSION_RSI_WINDOW),
                ("rsi_entry_threshold", _MEAN_REVERSION_RSI_ENTRY),
                ("rsi_exit_threshold", _MEAN_REVERSION_RSI_EXIT),
            ),
            entry_rule="Enter long when SMA50 > SMA200 and RSI2 <= 10.",
            exit_rule="Exit when SMA50 <= SMA200 or RSI2 >= 70.",
            insufficient_history_rule="Cash until SMA200, SMA50, and RSI2 are available.",
        ),
        AlphaCandidateDefinition(
            candidate_id="spy_vs_qqq_relative_strength_126d_fixed",
            label="SPY vs QQQ 126-day relative strength gate",
            family="relative_strength_filter",
            parameters=(
                ("relative_strength_lookback_days", _RELATIVE_STRENGTH_LOOKBACK_WINDOW),
                ("trend_short_sma_window", _SMA_SHORT_WINDOW),
                ("trend_long_sma_window", _SMA_LONG_WINDOW),
            ),
            entry_rule=(
                "Long SPY when SMA50 > SMA200 and SPY 126-day return is greater than "
                "or equal to QQQ 126-day return."
            ),
            exit_rule="Cash when the trend filter fails or QQQ leads SPY on the fixed lookback.",
            insufficient_history_rule=(
                "Cash until SPY SMA200 and both SPY/QQQ 126-day returns are available."
            ),
            data_dependencies=(_SYMBOL, _QQQ),
        ),
    )


def alpha_candidate_mutation_policy(decision: str) -> dict[str, object]:
    """Return the mutation guard that applies to any batch-scout decision."""
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


def build_alpha_candidate_batch_packet(
    *,
    daily_bars_csv: Path | str = DEFAULT_ALPHA_CANDIDATE_BATCH_DAILY_BARS_CSV,
    qqq_daily_bars_csv: Path | str = DEFAULT_ALPHA_CANDIDATE_BATCH_QQQ_DAILY_BARS_CSV,
    run_id: str = DEFAULT_ALPHA_CANDIDATE_BATCH_RUN_ID,
) -> dict[str, object]:
    """Evaluate the fixed candidate batch against local adjusted daily data."""
    checked_run_id = _required_string(run_id, "run_id")
    spy_path = _path(daily_bars_csv, "daily_bars_csv")
    qqq_path = _path(qqq_daily_bars_csv, "qqq_daily_bars_csv")
    spy_result = load_local_daily_bars_csv(spy_path, symbol=_SYMBOL)
    qqq_result = load_local_daily_bars_csv(qqq_path, symbol=_QQQ)
    bars = spy_result.usable_bars
    qqq_bars = qqq_result.usable_bars
    if len(bars) < 2:
        raise ValidationError("At least two SPY daily bars are required.")

    candidates = build_fixed_alpha_candidate_definitions()
    candidate_ids = tuple(candidate.candidate_id for candidate in candidates)
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    assumptions = DailyBacktestAssumptions(
        initial_equity=_DEFAULT_INITIAL_EQUITY,
        fee_bps=_DEFAULT_FEE_BPS,
        slippage_bps=_DEFAULT_SLIPPAGE_BPS,
    )
    indicators = _indicator_series(bars)
    qqq_closes_by_date = {bar.date: bar.adjusted_close for bar in qqq_bars}
    exposures_by_strategy = _build_strategy_exposures(
        bars=bars,
        indicators=indicators,
        qqq_closes_by_date=qqq_closes_by_date,
    )
    windows = _window_slices(len(bars))
    candidate_window_records: list[dict[str, object]] = []
    comparator_window_records: list[dict[str, object]] = []

    for window in windows:
        window_bars = bars[window.start_index : window.end_index]
        snapshot = _snapshot(window_bars)
        metrics_by_strategy: dict[str, dict[str, object]] = {}

        for strategy_id in _STRATEGY_ORDER:
            exposures = exposures_by_strategy[strategy_id][window.start_index : window.end_index]
            result = run_daily_backtest(snapshot, exposures, assumptions)
            metrics_by_strategy[strategy_id] = _metrics_payload(
                result=result,
                exposures=exposures,
                window=window,
                assumptions=assumptions,
            )

        for comparator_id in _COMPARATOR_ORDER:
            comparator_window_records.append(
                _comparator_window_record(
                    run_id=checked_run_id,
                    window=window,
                    metrics=metrics_by_strategy[comparator_id],
                    strategy_id=comparator_id,
                )
            )

        for candidate_id in candidate_ids:
            candidate = candidate_by_id[candidate_id]
            metrics = metrics_by_strategy[candidate_id]
            comparisons = _window_comparisons(
                candidate_metrics=metrics,
                metrics_by_strategy=metrics_by_strategy,
            )
            decision = _classify_window(
                candidate_metrics=metrics,
                comparisons=comparisons,
                row_count=window.row_count,
            )
            candidate_window_records.append(
                {
                    "record_type": "alpha_candidate_batch_scout_candidate_window",
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
                    "row_count": window.row_count,
                    "metrics": metrics,
                    "comparator_metrics": {
                        strategy_id: metrics_by_strategy[strategy_id]
                        for strategy_id in _COMPARATOR_ORDER
                    },
                    "delta_vs_buy_and_hold": comparisons["delta_vs_buy_and_hold"],
                    "delta_vs_sma50_200": comparisons["delta_vs_sma50_200"],
                    "delta_vs_rejected_rsi14": comparisons["delta_vs_rejected_rsi14"],
                    "delta_vs_rejected_trend_pullback": comparisons[
                        "delta_vs_rejected_trend_pullback"
                    ],
                    "decision_bucket": decision,
                    "decision_rationale": _window_decision_rationale(
                        decision=decision,
                        comparisons=comparisons,
                    ),
                    "mutation_policy": alpha_candidate_mutation_policy(decision),
                }
            )

    ranked_candidates = _ranked_candidate_results(
        candidates=candidates,
        candidate_window_records=candidate_window_records,
        source_row_count=len(bars),
    )
    final_decision_counts = Counter(
        str(candidate["final_decision"]) for candidate in ranked_candidates
    )
    promoted = [
        candidate
        for candidate in ranked_candidates
        if candidate["final_decision"] == "promote_to_paper_preview_candidate"
    ]
    rejected = [
        candidate
        for candidate in ranked_candidates
        if candidate["final_decision"] == "reject_candidate"
    ]

    summary = {
        "record_type": "alpha_candidate_batch_scout_summary",
        "schema_version": _SCHEMA_VERSION,
        "phase": _PHASE,
        "run_id": checked_run_id,
        "classification_recommendation": (
            "review_promoted_preview_candidates"
            if promoted
            else "no_preview_candidate_promotion_from_batch"
        ),
        "candidate_count": len(candidates),
        "comparator_count": len(_COMPARATOR_ORDER),
        "window_count": len(windows),
        "labels": list(_LABELS),
        "source_data": {
            "symbol": _SYMBOL,
            "basis": _BASIS,
            "timeframe": _TIMEFRAME,
            "daily_bars_csv": str(spy_path),
            "row_count": len(bars),
            "start_date": bars[0].date.isoformat(),
            "end_date": bars[-1].date.isoformat(),
            "snapshot_sha256": price_snapshot_fingerprint(_snapshot(bars)),
            "optional_relative_strength_symbol": _QQQ,
            "qqq_daily_bars_csv": str(qqq_path),
            "qqq_row_count": len(qqq_bars),
            "qqq_start_date": qqq_bars[0].date.isoformat() if qqq_bars else None,
            "qqq_end_date": qqq_bars[-1].date.isoformat() if qqq_bars else None,
        },
        "cost_slippage_assumptions": _assumptions_payload(assumptions),
        "optimization_policy": _optimization_policy_payload(candidates),
        "safety": _safety_payload(),
        "decision_options": list(ALPHA_CANDIDATE_BATCH_SCOUT_DECISIONS),
        "promotion_constraints": {
            "paper_mutation_promotion_performed": False,
            "paper_preview_candidate_is_not_paper_mutation": True,
            "paper_submit_performed": False,
            "live_endpoint_used": False,
        },
        "comparators": _comparators_payload(),
        "candidates": [candidate.to_dict() for candidate in candidates],
        "windows": [_window_payload(window, bars) for window in windows],
        "ranked_candidates": ranked_candidates,
        "final_decision_counts": dict(sorted(final_decision_counts.items())),
        "rejected_candidate_count": len(rejected),
        "promoted_preview_candidate_count": len(promoted),
        "decision_quality": _decision_quality_payload(ranked_candidates),
    }

    return {
        "summary": summary,
        "candidate_by_window": candidate_window_records,
        "comparator_by_window": comparator_window_records,
        "rejected_candidates": rejected,
        "promoted_preview_candidates": promoted,
    }


def write_alpha_candidate_batch_artifacts(
    packet: Mapping[str, object],
    output_root: Path | str = DEFAULT_ALPHA_CANDIDATE_BATCH_OUTPUT_ROOT,
) -> dict[str, Path]:
    """Write the v4.0 batch scout artifacts under an ignored runs tree."""
    root = _path_for_output(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)
    summary = _mapping(packet["summary"], "summary")
    candidate_by_window = _mapping_list(packet["candidate_by_window"], "candidate_by_window")
    rejected_candidates = _mapping_list(packet["rejected_candidates"], "rejected_candidates")
    promoted_preview_candidates = _mapping_list(
        packet["promoted_preview_candidates"],
        "promoted_preview_candidates",
    )

    summary_path = root / "batch_summary.json"
    by_window_path = root / "candidate_by_window.jsonl"
    brief_path = root / "decision_brief.md"
    rejected_path = root / "rejected_candidates.jsonl"
    promoted_path = root / "promoted_preview_candidates.jsonl"

    summary_path.write_text(_json_dumps(summary) + "\n", encoding="utf-8", newline="\n")
    by_window_path.write_text(
        "".join(_json_dumps(record) + "\n" for record in candidate_by_window),
        encoding="utf-8",
        newline="\n",
    )
    brief_path.write_text(
        render_alpha_candidate_batch_decision_brief(summary),
        encoding="utf-8",
        newline="\n",
    )
    rejected_path.write_text(
        "".join(_json_dumps(record) + "\n" for record in rejected_candidates),
        encoding="utf-8",
        newline="\n",
    )
    promoted_path.write_text(
        _promoted_preview_jsonl_text(promoted_preview_candidates),
        encoding="utf-8",
        newline="\n",
    )

    return {
        "batch_summary_json": summary_path,
        "candidate_by_window_jsonl": by_window_path,
        "decision_brief_md": brief_path,
        "rejected_candidates_jsonl": rejected_path,
        "promoted_preview_candidates_jsonl": promoted_path,
    }


def render_alpha_candidate_batch_decision_brief(summary: Mapping[str, object]) -> str:
    """Render the operator-readable v4.0 decision brief."""
    ranked = _mapping_list(summary.get("ranked_candidates", []), "ranked_candidates")
    windows = _mapping_list(summary.get("windows", []), "windows")
    source = _mapping(summary.get("source_data", {}), "source_data")
    lines = [
        "# v4.0 Alpha Candidate Batch Scout",
        "",
        "## Classification Recommendation",
        "",
        f"- recommendation: {summary.get('classification_recommendation')}",
        "- evidence_type: decision-quality batch evidence and architecture capability",
        "- paper_mutation_promotion_performed: False",
        "- profit_claim: none",
        "",
        "## Source Data",
        "",
        f"- SPY rows: {source.get('row_count')} from {source.get('start_date')} to {source.get('end_date')}",
        f"- QQQ rows: {source.get('qqq_row_count')} from {source.get('qqq_start_date')} to {source.get('qqq_end_date')}",
        "- data access: existing local adjusted daily CSV files only",
        "",
        "## Fixed Candidate Batch",
        "",
        "| rank | candidate_id | decision | aggregate_score | primary_reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for candidate in ranked:
        lines.append(
            "| {rank} | {candidate_id} | {decision} | {score} | {reason} |".format(
                rank=candidate.get("rank"),
                candidate_id=candidate.get("candidate_id"),
                decision=candidate.get("final_decision"),
                score=candidate.get("aggregate_score"),
                reason=_markdown_value(candidate.get("final_decision_rationale")),
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
            "- A preview-candidate decision remains research-only and cannot mutate broker state.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for local artifact generation."""
    parser = argparse.ArgumentParser(
        description="Evaluate fixed v4.0 SPY alpha candidates using local daily data."
    )
    parser.add_argument(
        "--daily-bars-csv",
        default=str(DEFAULT_ALPHA_CANDIDATE_BATCH_DAILY_BARS_CSV),
        help="Local SPY adjusted daily bars CSV.",
    )
    parser.add_argument(
        "--qqq-daily-bars-csv",
        default=str(DEFAULT_ALPHA_CANDIDATE_BATCH_QQQ_DAILY_BARS_CSV),
        help="Local QQQ adjusted daily bars CSV for the optional relative-strength candidate.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_ALPHA_CANDIDATE_BATCH_OUTPUT_ROOT),
        help="Ignored runs output directory.",
    )
    parser.add_argument("--run-id", default=DEFAULT_ALPHA_CANDIDATE_BATCH_RUN_ID)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local batch scout and write artifacts."""
    args = build_parser().parse_args(argv)
    try:
        packet = build_alpha_candidate_batch_packet(
            daily_bars_csv=args.daily_bars_csv,
            qqq_daily_bars_csv=args.qqq_daily_bars_csv,
            run_id=args.run_id,
        )
        paths = write_alpha_candidate_batch_artifacts(packet, args.output_root)
    except ValidationError as exc:
        print(f"alpha_candidate_batch_scout_error={exc}")
        return 2

    summary = _mapping(packet["summary"], "summary")
    print("alpha_candidate_batch_scout_status=completed")
    print(f"classification_recommendation={summary['classification_recommendation']}")
    print(f"candidate_count={summary['candidate_count']}")
    print(f"promoted_preview_candidate_count={summary['promoted_preview_candidate_count']}")
    print(f"output_root={Path(args.output_root)}")
    print(f"batch_summary_json={paths['batch_summary_json']}")
    return 0


def _build_strategy_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
    qqq_closes_by_date: Mapping[date, Decimal],
) -> dict[str, tuple[DailyExposure, ...]]:
    closes = tuple(bar.adjusted_close for bar in bars)
    exposures: dict[str, tuple[DailyExposure, ...]] = {
        _BUY_AND_HOLD_STRATEGY_ID: tuple(DailyExposure(bar.date, _ONE) for bar in bars),
        _SMA_STRATEGY_ID: tuple(
            DailyExposure(
                bar.date,
                _ONE
                if indicators.sma50[index] is not None
                and indicators.sma200[index] is not None
                and indicators.sma50[index] > indicators.sma200[index]
                else _ZERO,
            )
            for index, bar in enumerate(bars)
        ),
    }
    exposures[_REJECTED_RSI_STRATEGY_ID] = _rsi_mean_reversion_exposures(
        bars=bars,
        rsi=indicators.rsi14,
        oversold=_RSI_OVERSOLD_THRESHOLD,
        overbought=_RSI_OVERBOUGHT_THRESHOLD,
    )
    exposures[_REJECTED_TREND_PULLBACK_STRATEGY_ID] = _trend_pullback_exposures(
        bars=bars,
        indicators=indicators,
    )
    exposures["spy_vol_scaled_trend_20d_fixed"] = _vol_scaled_trend_exposures(
        bars=bars,
        indicators=indicators,
    )
    exposures["spy_breakout_252d_trailing_63d_fixed"] = _breakout_trailing_exposures(
        bars=bars,
        indicators=indicators,
    )
    exposures["spy_drawdown_recovery_252d_20_10_fixed"] = _drawdown_recovery_exposures(
        bars=bars,
        indicators=indicators,
    )
    exposures["spy_ma200_slope_20d_filter_fixed"] = _ma200_slope_filter_exposures(
        bars=bars,
        indicators=indicators,
    )
    exposures["spy_rsi2_mean_reversion_trend_filter_fixed"] = _rsi2_trend_filter_exposures(
        bars=bars,
        indicators=indicators,
    )
    exposures["spy_vs_qqq_relative_strength_126d_fixed"] = _relative_strength_exposures(
        bars=bars,
        closes=closes,
        indicators=indicators,
        qqq_closes_by_date=qqq_closes_by_date,
    )
    return exposures


def _rsi_mean_reversion_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    rsi: tuple[Decimal | None, ...],
    oversold: Decimal,
    overbought: Decimal,
) -> tuple[DailyExposure, ...]:
    holding = False
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        rsi_value = rsi[index]
        if rsi_value is None:
            holding = False
        elif holding and rsi_value >= overbought:
            holding = False
        elif not holding and rsi_value <= oversold:
            holding = True
        exposures.append(DailyExposure(bar.date, _ONE if holding else _ZERO))
    return tuple(exposures)


def _trend_pullback_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
) -> tuple[DailyExposure, ...]:
    holding = False
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        sma20 = indicators.sma20[index]
        sma50 = indicators.sma50[index]
        sma200 = indicators.sma200[index]
        trend_on = sma50 is not None and sma200 is not None and sma50 > sma200
        if not trend_on or sma20 is None or sma50 is None:
            holding = False
        elif holding and bar.adjusted_close >= sma50:
            holding = False
        elif not holding and bar.adjusted_close <= sma20:
            holding = True
        exposures.append(DailyExposure(bar.date, _ONE if holding else _ZERO))
    return tuple(exposures)


def _vol_scaled_trend_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
) -> tuple[DailyExposure, ...]:
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        sma50 = indicators.sma50[index]
        sma200 = indicators.sma200[index]
        vol20 = indicators.annualized_vol20[index]
        trend_on = sma50 is not None and sma200 is not None and sma50 > sma200
        if not trend_on or vol20 is None:
            exposure = _ZERO
        elif vol20 > _VOL_HIGH_THRESHOLD:
            exposure = _HALF
        else:
            exposure = _ONE
        exposures.append(DailyExposure(bar.date, exposure))
    return tuple(exposures)


def _breakout_trailing_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
) -> tuple[DailyExposure, ...]:
    holding = False
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        prior_high = indicators.prior_high252[index]
        prior_low = indicators.prior_low63[index]
        if prior_high is None:
            holding = False
        elif not holding and bar.adjusted_close > prior_high:
            holding = True
        elif holding and prior_low is not None and bar.adjusted_close < prior_low:
            holding = False
        exposures.append(DailyExposure(bar.date, _ONE if holding else _ZERO))
    return tuple(exposures)


def _drawdown_recovery_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
) -> tuple[DailyExposure, ...]:
    holding = False
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        prior_high = indicators.prior_high252[index]
        if prior_high is None:
            holding = False
        else:
            drawdown = (bar.adjusted_close / prior_high) - _ONE
            if drawdown <= _DRAWDOWN_CASH_TRIGGER:
                holding = False
            elif drawdown >= _DRAWDOWN_RECOVERY_TRIGGER:
                holding = True
        exposures.append(DailyExposure(bar.date, _ONE if holding else _ZERO))
    return tuple(exposures)


def _ma200_slope_filter_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
) -> tuple[DailyExposure, ...]:
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        sma200 = indicators.sma200[index]
        prior_sma200 = (
            None if index < _SMA_SLOPE_WINDOW else indicators.sma200[index - _SMA_SLOPE_WINDOW]
        )
        exposure = (
            _ONE
            if sma200 is not None
            and prior_sma200 is not None
            and bar.adjusted_close > sma200
            and sma200 > prior_sma200
            else _ZERO
        )
        exposures.append(DailyExposure(bar.date, exposure))
    return tuple(exposures)


def _rsi2_trend_filter_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
) -> tuple[DailyExposure, ...]:
    holding = False
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        sma50 = indicators.sma50[index]
        sma200 = indicators.sma200[index]
        rsi2 = indicators.rsi2[index]
        trend_on = sma50 is not None and sma200 is not None and sma50 > sma200
        if not trend_on or rsi2 is None:
            holding = False
        elif holding and rsi2 >= _MEAN_REVERSION_RSI_EXIT:
            holding = False
        elif not holding and rsi2 <= _MEAN_REVERSION_RSI_ENTRY:
            holding = True
        exposures.append(DailyExposure(bar.date, _ONE if holding else _ZERO))
    return tuple(exposures)


def _relative_strength_exposures(
    *,
    bars: tuple[LocalDailyBar, ...],
    closes: tuple[Decimal, ...],
    indicators: _IndicatorSeries,
    qqq_closes_by_date: Mapping[date, Decimal],
) -> tuple[DailyExposure, ...]:
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        sma50 = indicators.sma50[index]
        sma200 = indicators.sma200[index]
        trend_on = sma50 is not None and sma200 is not None and sma50 > sma200
        if not trend_on or index < _RELATIVE_STRENGTH_LOOKBACK_WINDOW:
            exposures.append(DailyExposure(bar.date, _ZERO))
            continue

        prior_bar = bars[index - _RELATIVE_STRENGTH_LOOKBACK_WINDOW]
        qqq_now = qqq_closes_by_date.get(bar.date)
        qqq_prior = qqq_closes_by_date.get(prior_bar.date)
        if qqq_now is None or qqq_prior is None:
            exposure = _ZERO
        else:
            spy_return = (closes[index] / closes[index - _RELATIVE_STRENGTH_LOOKBACK_WINDOW]) - _ONE
            qqq_return = (qqq_now / qqq_prior) - _ONE
            exposure = _ONE if spy_return >= qqq_return else _ZERO
        exposures.append(DailyExposure(bar.date, exposure))
    return tuple(exposures)


def _metrics_payload(
    *,
    result: DailyBacktestResult,
    exposures: tuple[DailyExposure, ...],
    window: _WindowSlice,
    assumptions: DailyBacktestAssumptions,
) -> dict[str, object]:
    daily_returns = tuple(point.strategy_return_after_costs for point in result.points[1:])
    holding = _holding_stats(result.points)
    return {
        "window_id": window.window_id,
        "total_return": result.total_return,
        "annualized_return": _annualized_return(result.total_return, len(result.points)),
        "max_drawdown": result.max_drawdown,
        "sharpe_like_score": _sharpe_like_score(daily_returns),
        "exposure_ratio": result.exposure_ratio,
        "exposure_pct": result.exposure_ratio * _HUNDRED,
        "trade_count": _transition_count(exposures),
        "average_holding_period_days": holding["average_holding_period_days"],
        "holding_period_count": holding["holding_period_count"],
        "turnover": result.turnover,
        "daily_return_count": len(daily_returns),
        "cost_slippage_assumptions": _assumptions_payload(assumptions),
    }


def _window_comparisons(
    *,
    candidate_metrics: Mapping[str, object],
    metrics_by_strategy: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    return {
        "delta_vs_buy_and_hold": _comparison_payload(
            candidate_metrics=candidate_metrics,
            benchmark_metrics=metrics_by_strategy[_BUY_AND_HOLD_STRATEGY_ID],
            benchmark_id=_BUY_AND_HOLD_STRATEGY_ID,
        ),
        "delta_vs_sma50_200": _comparison_payload(
            candidate_metrics=candidate_metrics,
            benchmark_metrics=metrics_by_strategy[_SMA_STRATEGY_ID],
            benchmark_id=_SMA_STRATEGY_ID,
        ),
        "delta_vs_rejected_rsi14": _comparison_payload(
            candidate_metrics=candidate_metrics,
            benchmark_metrics=metrics_by_strategy[_REJECTED_RSI_STRATEGY_ID],
            benchmark_id=_REJECTED_RSI_STRATEGY_ID,
        ),
        "delta_vs_rejected_trend_pullback": _comparison_payload(
            candidate_metrics=candidate_metrics,
            benchmark_metrics=metrics_by_strategy[_REJECTED_TREND_PULLBACK_STRATEGY_ID],
            benchmark_id=_REJECTED_TREND_PULLBACK_STRATEGY_ID,
        ),
    }


def _comparison_payload(
    *,
    candidate_metrics: Mapping[str, object],
    benchmark_metrics: Mapping[str, object],
    benchmark_id: str,
) -> dict[str, object]:
    total_delta = _metric_decimal(candidate_metrics, "total_return") - _metric_decimal(
        benchmark_metrics,
        "total_return",
    )
    annualized_delta = _optional_metric_delta(
        candidate_metrics,
        benchmark_metrics,
        "annualized_return",
    )
    drawdown_delta = _metric_decimal(candidate_metrics, "max_drawdown") - _metric_decimal(
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
        "total_return_relation": _relation(total_delta),
        "annualized_return_delta": annualized_delta,
        "annualized_return_relation": _optional_relation(annualized_delta),
        "max_drawdown_delta": drawdown_delta,
        "max_drawdown_relation": _drawdown_relation(drawdown_delta),
        "max_drawdown_delta_interpretation": "negative_is_lower_drawdown",
        "sharpe_like_score_delta": sharpe_delta,
        "sharpe_like_score_relation": _optional_relation(sharpe_delta),
    }


def _classify_window(
    *,
    candidate_metrics: Mapping[str, object],
    comparisons: Mapping[str, object],
    row_count: int,
) -> str:
    if row_count < _MINIMUM_WINDOW_ROWS:
        return "needs_longer_oos"

    exposure = _metric_decimal(candidate_metrics, "exposure_ratio")
    if exposure <= _ZERO:
        return "reject_candidate"

    buy = _mapping(comparisons["delta_vs_buy_and_hold"], "delta_vs_buy_and_hold")
    sma = _mapping(comparisons["delta_vs_sma50_200"], "delta_vs_sma50_200")
    total_buy = _metric_decimal(buy, "total_return_delta")
    total_sma = _metric_decimal(sma, "total_return_delta")
    drawdown_buy = _metric_decimal(buy, "max_drawdown_delta")
    drawdown_sma = _metric_decimal(sma, "max_drawdown_delta")
    sharpe_buy = _optional_metric_decimal(buy, "sharpe_like_score_delta")
    sharpe_sma = _optional_metric_decimal(sma, "sharpe_like_score_delta")

    sharpe_better = (
        sharpe_buy is not None
        and sharpe_sma is not None
        and sharpe_buy >= _ZERO
        and sharpe_sma >= _ZERO
    )
    if (
        total_buy >= _ZERO
        and total_sma >= _ZERO
        and drawdown_buy <= _ZERO
        and drawdown_sma <= _ZERO
        and sharpe_better
    ):
        return "promote_to_paper_preview_candidate"

    if (
        total_buy <= Decimal("-0.05")
        and total_sma <= Decimal("-0.05")
        and (sharpe_buy is None or sharpe_buy < _ZERO)
        and (sharpe_sma is None or sharpe_sma < _ZERO)
    ):
        return "reject_candidate"

    if drawdown_buy <= Decimal("-0.05") and (total_buy < _ZERO or total_sma < _ZERO):
        return "needs_regime_filter"

    if (
        (total_buy > _ZERO and total_sma <= _ZERO)
        or (total_buy <= _ZERO and total_sma > _ZERO)
        or (
            sharpe_buy is not None
            and sharpe_sma is not None
            and sharpe_buy * sharpe_sma < _ZERO
        )
    ):
        return "keep_shadow"

    return "keep_shadow"


def _ranked_candidate_results(
    *,
    candidates: tuple[AlphaCandidateDefinition, ...],
    candidate_window_records: Sequence[Mapping[str, object]],
    source_row_count: int,
) -> list[dict[str, object]]:
    records_by_candidate: dict[str, list[Mapping[str, object]]] = {}
    for record in candidate_window_records:
        records_by_candidate.setdefault(str(record["candidate_id"]), []).append(record)

    results: list[dict[str, object]] = []
    for candidate in candidates:
        records = records_by_candidate[candidate.candidate_id]
        decision = _final_candidate_decision(records, source_row_count=source_row_count)
        score = _aggregate_score(records)
        counts = Counter(str(record["decision_bucket"]) for record in records)
        result = {
            "candidate_id": candidate.candidate_id,
            "candidate_label": candidate.label,
            "candidate_family": candidate.family,
            "fixed_parameters": candidate.parameter_values,
            "final_decision": decision,
            "decision_counts": dict(sorted(counts.items())),
            "aggregate_score": score,
            "rank_score_inputs": _rank_score_inputs(records),
            "final_decision_rationale": _final_decision_rationale(decision, records),
            "window_decisions": [
                {
                    "window_id": record["window_id"],
                    "decision_bucket": record["decision_bucket"],
                    "total_return": _mapping(record["metrics"], "metrics")["total_return"],
                    "delta_vs_buy_and_hold": _mapping(
                        record["delta_vs_buy_and_hold"],
                        "delta_vs_buy_and_hold",
                    )["total_return_delta"],
                    "delta_vs_sma50_200": _mapping(
                        record["delta_vs_sma50_200"],
                        "delta_vs_sma50_200",
                    )["total_return_delta"],
                }
                for record in records
            ],
            "mutation_policy": alpha_candidate_mutation_policy(decision),
        }
        results.append(result)

    results.sort(key=_candidate_sort_key)
    for rank, result in enumerate(results, start=1):
        result["rank"] = rank
    return results


def _final_candidate_decision(
    records: Sequence[Mapping[str, object]],
    *,
    source_row_count: int,
) -> str:
    if source_row_count < _MINIMUM_DECISION_QUALITY_ROWS:
        return "needs_longer_oos"

    by_window = {str(record["window_id"]): str(record["decision_bucket"]) for record in records}
    counts = Counter(by_window.values())
    key_window_ids = (
        "chronological_later_half",
        "recent_3y_holdout",
        "trailing_5y_later_half",
    )
    key_decisions = tuple(by_window.get(window_id, "needs_longer_oos") for window_id in key_window_ids)

    if all(item == "promote_to_paper_preview_candidate" for item in key_decisions) and not (
        counts["reject_candidate"]
        or counts["needs_regime_filter"]
        or counts["needs_longer_oos"]
    ):
        return "promote_to_paper_preview_candidate"

    if (
        counts["reject_candidate"] >= 3
        or (
            by_window.get("chronological_later_half") == "reject_candidate"
            and by_window.get("recent_3y_holdout") == "reject_candidate"
        )
    ):
        return "reject_candidate"

    if counts["needs_regime_filter"] >= 2:
        return "needs_regime_filter"

    if counts["needs_longer_oos"] >= 2:
        return "needs_longer_oos"

    return "keep_shadow"


def _aggregate_score(records: Sequence[Mapping[str, object]]) -> Decimal:
    values: list[Decimal] = []
    for record in records:
        buy = _mapping(record["delta_vs_buy_and_hold"], "delta_vs_buy_and_hold")
        sma = _mapping(record["delta_vs_sma50_200"], "delta_vs_sma50_200")
        total_buy = _metric_decimal(buy, "total_return_delta")
        total_sma = _metric_decimal(sma, "total_return_delta")
        drawdown_buy = _metric_decimal(buy, "max_drawdown_delta")
        sharpe_buy = _optional_metric_decimal(buy, "sharpe_like_score_delta") or _ZERO
        sharpe_sma = _optional_metric_decimal(sma, "sharpe_like_score_delta") or _ZERO
        drawdown_penalty = max(drawdown_buy, _ZERO)
        values.append(total_buy + total_sma + sharpe_buy + sharpe_sma - drawdown_penalty)
    if not values:
        return _ZERO
    return sum(values, _ZERO) / Decimal(len(values))


def _rank_score_inputs(records: Sequence[Mapping[str, object]]) -> dict[str, object]:
    full = next(
        record for record in records if record["window_id"] == "full_available_reference"
    )
    recent = next(record for record in records if record["window_id"] == "recent_3y_holdout")
    return {
        "full_available_total_return": _mapping(full["metrics"], "metrics")["total_return"],
        "recent_3y_total_return": _mapping(recent["metrics"], "metrics")["total_return"],
        "full_available_delta_vs_sma50_200": _mapping(
            full["delta_vs_sma50_200"],
            "delta_vs_sma50_200",
        )["total_return_delta"],
        "recent_3y_delta_vs_sma50_200": _mapping(
            recent["delta_vs_sma50_200"],
            "delta_vs_sma50_200",
        )["total_return_delta"],
    }


def _candidate_sort_key(candidate: Mapping[str, object]) -> tuple[int, Decimal, str]:
    priority = {
        "promote_to_paper_preview_candidate": 0,
        "keep_shadow": 1,
        "needs_regime_filter": 2,
        "needs_longer_oos": 3,
        "reject_candidate": 4,
    }
    decision = str(candidate["final_decision"])
    return (
        priority.get(decision, 9),
        -_decimal_value(candidate["aggregate_score"], "aggregate_score"),
        str(candidate["candidate_id"]),
    )


def _final_decision_rationale(
    decision: str,
    records: Sequence[Mapping[str, object]],
) -> str:
    counts = Counter(str(record["decision_bucket"]) for record in records)
    if decision == "promote_to_paper_preview_candidate":
        return (
            "Stable cost-aware risk-adjusted evidence exceeded buy-and-hold and "
            "SMA50/200 across key holdout windows; preview only, no paper mutation."
        )
    if decision == "reject_candidate":
        return f"Rejected because window evidence was poor or fragile: {dict(sorted(counts.items()))}."
    if decision == "needs_regime_filter":
        return (
            "Risk-control evidence was mixed; drawdown behavior may need a separate "
            f"regime filter before any further preview work: {dict(sorted(counts.items()))}."
        )
    if decision == "needs_longer_oos":
        return f"Insufficient decision-quality rows or windows: {dict(sorted(counts.items()))}."
    return f"Mixed evidence; keep as shadow research only: {dict(sorted(counts.items()))}."


def _window_decision_rationale(
    *,
    decision: str,
    comparisons: Mapping[str, object],
) -> str:
    buy = _mapping(comparisons["delta_vs_buy_and_hold"], "delta_vs_buy_and_hold")
    sma = _mapping(comparisons["delta_vs_sma50_200"], "delta_vs_sma50_200")
    return (
        f"{decision}: total-return deltas were {buy['total_return_delta']} versus "
        f"buy-and-hold and {sma['total_return_delta']} versus SMA50/200; "
        f"Sharpe-like deltas were {buy['sharpe_like_score_delta']} and "
        f"{sma['sharpe_like_score_delta']}."
    )


def _indicator_series(bars: tuple[LocalDailyBar, ...]) -> _IndicatorSeries:
    closes = tuple(bar.adjusted_close for bar in bars)
    daily_returns = _daily_returns(closes)
    return _IndicatorSeries(
        sma20=_rolling_sma(closes, _PULLBACK_SMA_WINDOW),
        sma50=_rolling_sma(closes, _SMA_SHORT_WINDOW),
        sma200=_rolling_sma(closes, _SMA_LONG_WINDOW),
        rsi2=_rolling_rsi(closes, _MEAN_REVERSION_RSI_WINDOW),
        rsi14=_rolling_rsi(closes, _RSI_LOOKBACK_WINDOW),
        annualized_vol20=_rolling_annualized_volatility(
            daily_returns,
            _VOL_LOOKBACK_WINDOW,
        ),
        prior_high252=_rolling_prior_high(closes, _BREAKOUT_LOOKBACK_WINDOW),
        prior_low63=_rolling_prior_low(closes, _BREAKOUT_TRAILING_LOW_WINDOW),
    )


def _rolling_sma(
    values: tuple[Decimal, ...],
    window: int,
) -> tuple[Decimal | None, ...]:
    result: list[Decimal | None] = []
    rolling_total = _ZERO
    for index, value in enumerate(values):
        rolling_total += value
        if index >= window:
            rolling_total -= values[index - window]
        if index + 1 < window:
            result.append(None)
        else:
            result.append(rolling_total / Decimal(window))
    return tuple(result)


def _rolling_rsi(
    closes: tuple[Decimal, ...],
    window: int,
) -> tuple[Decimal | None, ...]:
    result: list[Decimal | None] = [None] * len(closes)
    if len(closes) <= window:
        return tuple(result)

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for index in range(1, len(closes)):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, _ZERO))
        losses.append(abs(min(change, _ZERO)))
        if len(gains) < window:
            continue
        window_gains = gains[-window:]
        window_losses = losses[-window:]
        average_gain = sum(window_gains, _ZERO) / Decimal(window)
        average_loss = sum(window_losses, _ZERO) / Decimal(window)
        if average_loss == _ZERO:
            result[index] = _HUNDRED
        else:
            relative_strength = average_gain / average_loss
            result[index] = _HUNDRED - (_HUNDRED / (_ONE + relative_strength))
    return tuple(result)


def _daily_returns(closes: tuple[Decimal, ...]) -> tuple[Decimal | None, ...]:
    returns: list[Decimal | None] = [None]
    for index in range(1, len(closes)):
        returns.append((closes[index] / closes[index - 1]) - _ONE)
    return tuple(returns)


def _rolling_annualized_volatility(
    returns: tuple[Decimal | None, ...],
    window: int,
) -> tuple[Decimal | None, ...]:
    result: list[Decimal | None] = []
    for index, _value in enumerate(returns):
        if index + 1 < window:
            result.append(None)
            continue
        sample = returns[index - window + 1 : index + 1]
        if any(item is None for item in sample):
            result.append(None)
            continue
        values = [float(item) for item in sample if item is not None]
        if len(values) < 2:
            result.append(None)
        else:
            result.append(_decimal_from_float(stdev(values) * math.sqrt(252.0)))
    return tuple(result)


def _rolling_prior_high(
    values: tuple[Decimal, ...],
    window: int,
) -> tuple[Decimal | None, ...]:
    result: list[Decimal | None] = []
    for index, _value in enumerate(values):
        if index < window:
            result.append(None)
        else:
            result.append(max(values[index - window : index]))
    return tuple(result)


def _rolling_prior_low(
    values: tuple[Decimal, ...],
    window: int,
) -> tuple[Decimal | None, ...]:
    result: list[Decimal | None] = []
    for index, _value in enumerate(values):
        if index < window:
            result.append(None)
        else:
            result.append(min(values[index - window : index]))
    return tuple(result)


def _window_slices(source_row_count: int) -> tuple[_WindowSlice, ...]:
    if source_row_count < 2:
        raise ValidationError("source_row_count must be at least 2.")
    midpoint = source_row_count // 2
    recent_start = max(0, source_row_count - _THREE_YEAR_ROW_COUNT)
    trailing_5y_start = max(0, source_row_count - _FIVE_YEAR_ROW_COUNT)
    trailing_5y_midpoint = trailing_5y_start + (
        (source_row_count - trailing_5y_start) // 2
    )
    return (
        _WindowSlice(
            window_id="full_available_reference",
            window_label="full available",
            window_role="reference",
            start_index=0,
            end_index=source_row_count,
            description="Full available local adjusted SPY history.",
        ),
        _WindowSlice(
            window_id="chronological_earlier_half",
            window_label="earlier half",
            window_role="chronological_split",
            start_index=0,
            end_index=midpoint,
            description="Earlier chronological half; parameters are fixed before evaluation.",
        ),
        _WindowSlice(
            window_id="chronological_later_half",
            window_label="later half",
            window_role="chronological_split",
            start_index=midpoint,
            end_index=source_row_count,
            description="Later chronological half; no parameter tuning from earlier half.",
        ),
        _WindowSlice(
            window_id="trailing_5y_earlier_half",
            window_label="trailing 5y earlier half",
            window_role="trailing_5y_split",
            start_index=trailing_5y_start,
            end_index=trailing_5y_midpoint,
            description="Earlier half of the trailing five-year row window.",
        ),
        _WindowSlice(
            window_id="trailing_5y_later_half",
            window_label="trailing 5y later half",
            window_role="trailing_5y_split",
            start_index=trailing_5y_midpoint,
            end_index=source_row_count,
            description="Later half of the trailing five-year row window.",
        ),
        _WindowSlice(
            window_id="recent_3y_holdout",
            window_label="recent 3y",
            window_role="holdout",
            start_index=recent_start,
            end_index=source_row_count,
            description="Most recent three-year row window.",
        ),
    )


def _snapshot(bars: tuple[LocalDailyBar, ...]) -> HistoricalPriceSnapshot:
    return HistoricalPriceSnapshot(
        symbol=_SYMBOL,
        bars=tuple(
            HistoricalPriceBar(
                symbol=bar.symbol,
                date=bar.date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                adjusted_close=bar.adjusted_close,
                volume=bar.volume,
            )
            for bar in bars
        ),
    )


def _holding_stats(points: tuple[object, ...]) -> dict[str, object]:
    durations: list[int] = []
    current_duration = 0
    for point in points:
        exposure = _decimal_value(getattr(point, "exposure"), "point exposure")
        if exposure > _ZERO:
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


def _transition_count(exposures: tuple[DailyExposure, ...]) -> int:
    previous_exposure = _ZERO
    count = 0
    for exposure in exposures:
        if exposure.exposure != previous_exposure:
            count += 1
        previous_exposure = exposure.exposure
    return count


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


def _comparator_window_record(
    *,
    run_id: str,
    window: _WindowSlice,
    metrics: Mapping[str, object],
    strategy_id: str,
) -> dict[str, object]:
    return {
        "record_type": "alpha_candidate_batch_scout_comparator_window",
        "schema_version": _SCHEMA_VERSION,
        "phase": _PHASE,
        "run_id": run_id,
        "strategy_id": strategy_id,
        "strategy_label": _strategy_label(strategy_id),
        "strategy_role": _strategy_role(strategy_id),
        "window_id": window.window_id,
        "window_role": window.window_role,
        "row_count": window.row_count,
        "metrics": dict(metrics),
    }


def _comparators_payload() -> list[dict[str, object]]:
    return [
        {
            "strategy_id": _BUY_AND_HOLD_STRATEGY_ID,
            "strategy_label": "Buy-and-hold SPY",
            "role": "buy_and_hold_comparator",
            "symbol": _SYMBOL,
            "price_basis": _BASIS,
        },
        {
            "strategy_id": _SMA_STRATEGY_ID,
            "strategy_label": "SMA50/200 training-wheel baseline",
            "role": "paper_mutation_capable_training_wheel_baseline",
            "short_window": _SMA_SHORT_WINDOW,
            "long_window": _SMA_LONG_WINDOW,
            "risk_on_rule": "SMA50 > SMA200",
            "risk_off_rule": "SMA50 <= SMA200",
        },
        {
            "strategy_id": _REJECTED_RSI_STRATEGY_ID,
            "strategy_label": "Rejected RSI-14 mean-reversion comparator",
            "role": "rejected_shadow_comparator",
            "rsi_period": _RSI_LOOKBACK_WINDOW,
            "oversold_threshold": _decimal_text(_RSI_OVERSOLD_THRESHOLD),
            "overbought_threshold": _decimal_text(_RSI_OVERBOUGHT_THRESHOLD),
            "rejection_source": "v3.8 fixed-parameter SPY RSI OOS decision gate",
        },
        {
            "strategy_id": _REJECTED_TREND_PULLBACK_STRATEGY_ID,
            "strategy_label": "Rejected fixed SPY trend-pullback comparator",
            "role": "rejected_shadow_comparator",
            "trend_filter": "SMA50 > SMA200",
            "pullback_sma_window": _PULLBACK_SMA_WINDOW,
            "recovery_exit_sma_window": _SMA_SHORT_WINDOW,
            "rejection_source": "v3.9 fixed-parameter SPY trend-pullback backtest",
        },
    ]


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
    ranked_candidates: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    promoted = [
        item
        for item in ranked_candidates
        if item.get("final_decision") == "promote_to_paper_preview_candidate"
    ]
    rejected = [
        item for item in ranked_candidates if item.get("final_decision") == "reject_candidate"
    ]
    return {
        "decision_quality_evidence_produced": True,
        "architecture_capability_produced": True,
        "process_overhead_only": False,
        "search_space_narrowed": bool(promoted or rejected),
        "promoted_preview_candidate_count": len(promoted),
        "rejected_candidate_count": len(rejected),
        "alpha_or_profit_claim": "none",
    }


def _window_payload(window: _WindowSlice, bars: tuple[LocalDailyBar, ...]) -> dict[str, object]:
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


def _assumptions_payload(assumptions: DailyBacktestAssumptions) -> dict[str, object]:
    return {
        "initial_equity": assumptions.initial_equity,
        "fee_bps": assumptions.fee_bps,
        "slippage_bps": assumptions.slippage_bps,
        "total_cost_bps_per_full_exposure_transition": (
            assumptions.fee_bps + assumptions.slippage_bps
        ),
        "cost_model": (
            "daily_backtest applies abs(exposure_delta) * "
            "(fee_bps + slippage_bps) / 10000"
        ),
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


def _promoted_preview_jsonl_text(
    promoted_preview_candidates: Sequence[Mapping[str, object]],
) -> str:
    if promoted_preview_candidates:
        return "".join(_json_dumps(record) + "\n" for record in promoted_preview_candidates)
    empty_record = {
        "record_type": "alpha_candidate_batch_scout_promoted_preview_candidates_empty",
        "schema_version": _SCHEMA_VERSION,
        "phase": _PHASE,
        "candidate_count": 0,
        "reason": (
            "No candidate met the stable, cost-aware, cross-window preview-candidate "
            "standard without mixed or poor evidence."
        ),
        "paper_mutation_allowed": False,
    }
    return _json_dumps(empty_record) + "\n"


def _strategy_label(strategy_id: str) -> str:
    labels = {
        _BUY_AND_HOLD_STRATEGY_ID: "Buy-and-hold SPY",
        _SMA_STRATEGY_ID: "SMA50/200 training-wheel baseline",
        _REJECTED_RSI_STRATEGY_ID: "Rejected RSI-14 mean-reversion comparator",
        _REJECTED_TREND_PULLBACK_STRATEGY_ID: "Rejected trend-pullback comparator",
    }
    return labels.get(strategy_id, strategy_id)


def _strategy_role(strategy_id: str) -> str:
    if strategy_id == _BUY_AND_HOLD_STRATEGY_ID:
        return "buy_and_hold_comparator"
    if strategy_id == _SMA_STRATEGY_ID:
        return "training_wheel_baseline_comparator"
    return "rejected_shadow_comparator"


def _relation(delta: Decimal) -> str:
    if delta > _ZERO:
        return "above"
    if delta < _ZERO:
        return "below"
    return "equal"


def _drawdown_relation(delta: Decimal) -> str:
    if delta < _ZERO:
        return "lower_drawdown"
    if delta > _ZERO:
        return "higher_drawdown"
    return "equal_drawdown"


def _optional_relation(delta: Decimal | None) -> str:
    if delta is None:
        return "not_supported"
    return _relation(delta)


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


def _metric_decimal(value: Mapping[str, object], field_name: str) -> Decimal:
    result = _optional_metric_decimal(value, field_name)
    if result is None:
        raise ValidationError(f"{field_name} must be a supported Decimal metric.")
    return result


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


def _parameter_tuple(
    value: Iterable[tuple[str, object]],
) -> tuple[tuple[str, object], ...]:
    if isinstance(value, (str, bytes)):
        raise ValidationError("parameters must be key/value tuples.")
    try:
        items = tuple(value)
    except TypeError as exc:
        raise ValidationError("parameters must be key/value tuples.") from exc
    if not items:
        raise ValidationError("parameters must not be empty.")

    seen_names: set[str] = set()
    checked: list[tuple[str, object]] = []
    for item in items:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValidationError("parameters must be key/value tuples.")
        name = _required_string(item[0], "parameter name")
        if name in seen_names:
            raise ValidationError("parameter names must be unique.")
        seen_names.add(name)
        checked.append((name, _parameter_value(item[1], name)))
    return tuple(checked)


def _parameter_value(value: object, field_name: str) -> object:
    if isinstance(value, (str, int, Decimal)):
        return value
    raise ValidationError(f"{field_name} must be a fixed primitive parameter value.")


def _decision_value(value: object) -> str:
    text = _required_string(value, "decision")
    if text not in ALPHA_CANDIDATE_BATCH_SCOUT_DECISIONS:
        raise ValidationError("decision must be a supported alpha candidate batch decision.")
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
