"""Deterministic fixed-parameter SPY trend-pullback challenger backtest."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
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
from algotrader.research.price_snapshot import HistoricalPriceBar, HistoricalPriceSnapshot

__all__ = [
    "DEFAULT_TREND_PULLBACK_DAILY_BARS_CSV",
    "DEFAULT_TREND_PULLBACK_OUTPUT_ROOT",
    "TREND_PULLBACK_DECISIONS",
    "build_spy_trend_pullback_backtest_packet",
    "classify_trend_pullback_decision",
    "main",
    "render_spy_trend_pullback_decision_brief",
    "write_spy_trend_pullback_backtest_artifacts",
]


DEFAULT_TREND_PULLBACK_DAILY_BARS_CSV = Path(
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
DEFAULT_TREND_PULLBACK_OUTPUT_ROOT = Path(
    "runs/strategy_challengers/trend_pullback/latest"
)
DEFAULT_TREND_PULLBACK_RUN_ID = "v3_9_spy_trend_pullback_fixed_parameter_backtest"

TREND_PULLBACK_DECISIONS = (
    "reject_candidate",
    "keep_shadow",
    "needs_regime_filter",
    "needs_longer_oos",
    "promote_to_paper_preview_candidate",
)

_SCHEMA_VERSION = "1"
_RECORD_TYPE_SUMMARY = "spy_trend_pullback_backtest_summary"
_RECORD_TYPE_WINDOW = "spy_trend_pullback_backtest_window"
_RECORD_TYPE_TRADE = "spy_trend_pullback_backtest_trade"
_SYMBOL = "SPY"
_BASIS = "adjusted_close"
_TIMEFRAME = "daily"
_TRADING_DAYS_PER_YEAR = Decimal("252")
_CALENDAR_DAYS_PER_YEAR = 365.25
_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_DEFAULT_INITIAL_EQUITY = Decimal("10000")
_DEFAULT_FEE_BPS = Decimal("0")
_DEFAULT_SLIPPAGE_BPS = Decimal("1")

_CANDIDATE_STRATEGY_ID = "spy_trend_pullback_sma50_200_sma20_recovery_fixed_shadow"
_SMA_STRATEGY_ID = "spy_sma_50_200_training_wheel"
_BUY_AND_HOLD_STRATEGY_ID = "spy_buy_and_hold_comparator"
_REJECTED_RSI_STRATEGY_ID = "spy_rsi_14_mean_reversion_rejected_comparator"
_STRATEGY_ORDER = (
    _BUY_AND_HOLD_STRATEGY_ID,
    _SMA_STRATEGY_ID,
    _REJECTED_RSI_STRATEGY_ID,
    _CANDIDATE_STRATEGY_ID,
)

_SMA_SHORT_WINDOW = 50
_SMA_LONG_WINDOW = 200
_PULLBACK_SMA_WINDOW = 20
_RECOVERY_EXIT_SMA_WINDOW = 50
_RSI_LOOKBACK_WINDOW = 14
_RSI_OVERSOLD_THRESHOLD = Decimal("30")
_RSI_OVERBOUGHT_THRESHOLD = Decimal("70")
_THREE_YEAR_ROW_COUNT = 252 * 3
_FIVE_YEAR_ROW_COUNT = 252 * 5
_MINIMUM_DECISION_QUALITY_ROWS = _THREE_YEAR_ROW_COUNT

_LABELS = (
    "paper_lab_only",
    "offline_only",
    "research_only",
    "fixed_parameter_trend_pullback_backtest",
    "accepted_adjusted_spy_daily_bars",
    "trend_pullback_shadow_only_no_promotion",
    "not_live_authorized",
    "profit_claim=none",
)


@dataclass(frozen=True, slots=True)
class _WindowSlice:
    window_id: str
    window_role: str
    description: str
    start_index: int
    end_index: int

    @property
    def row_count(self) -> int:
        return self.end_index - self.start_index

    def to_dict(self, bars: tuple[LocalDailyBar, ...]) -> dict[str, object]:
        if self.end_index > len(bars):
            raise ValidationError("window exceeds available bars.")
        return {
            "window_id": self.window_id,
            "window_role": self.window_role,
            "description": self.description,
            "start_index": self.start_index,
            "end_index_exclusive": self.end_index,
            "start_date": bars[self.start_index].date.isoformat(),
            "end_date": bars[self.end_index - 1].date.isoformat(),
            "row_count": self.row_count,
        }


@dataclass(frozen=True, slots=True)
class _IndicatorSeries:
    rsi: tuple[Decimal | None, ...]
    sma_pullback: tuple[Decimal | None, ...]
    sma_short: tuple[Decimal | None, ...]
    sma_long: tuple[Decimal | None, ...]


def build_spy_trend_pullback_backtest_packet(
    *,
    daily_bars_csv: Path | str = DEFAULT_TREND_PULLBACK_DAILY_BARS_CSV,
    as_of_date: date | datetime | str | None = None,
    run_id: str = DEFAULT_TREND_PULLBACK_RUN_ID,
    initial_equity: Decimal | str = _DEFAULT_INITIAL_EQUITY,
    fee_bps: Decimal | str = _DEFAULT_FEE_BPS,
    slippage_bps: Decimal | str = _DEFAULT_SLIPPAGE_BPS,
) -> dict[str, object]:
    """Build fixed-parameter v3.9 trend-pullback summaries without writing."""

    checked_run_id = _required_string(run_id, "run_id")
    assumptions = DailyBacktestAssumptions(
        initial_equity=_positive_decimal(initial_equity, "initial_equity"),
        fee_bps=_non_negative_decimal(fee_bps, "fee_bps"),
        slippage_bps=_non_negative_decimal(slippage_bps, "slippage_bps"),
    )
    csv_result = load_local_daily_bars_csv(
        daily_bars_csv,
        symbol=_SYMBOL,
        as_of=as_of_date,
    )
    bars = csv_result.usable_bars
    if not bars:
        raise ValidationError("daily_bars_csv must contain at least one usable SPY bar.")

    indicators = _indicator_series(bars)
    exposures_by_strategy = _build_strategy_exposures(bars, indicators)
    window_summaries: list[dict[str, object]] = []
    trade_records: list[dict[str, object]] = []
    for window in _window_slices(len(bars)):
        window_summary, window_trades = _build_window_backtest(
            run_id=checked_run_id,
            bars=bars,
            window=window,
            assumptions=assumptions,
            indicators=indicators,
            exposures_by_strategy=exposures_by_strategy,
        )
        window_summaries.append(window_summary)
        trade_records.extend(window_trades)

    final_decision = classify_trend_pullback_decision(
        window_summaries,
        source_usable_bar_count=len(bars),
    )
    decision_counts = Counter(
        str(window["decision_classification"]) for window in window_summaries
    )
    summary = {
        "record_type": _RECORD_TYPE_SUMMARY,
        "schema_version": _SCHEMA_VERSION,
        "run_id": checked_run_id,
        "backtest_status": "complete",
        "classification_recommendation": final_decision,
        "final_decision": final_decision,
        "decision_options": list(TREND_PULLBACK_DECISIONS),
        "decision_rationale": _decision_rationale(
            final_decision,
            window_summaries,
            len(bars),
        ),
        "evidence_result": (
            "decision_quality_evidence"
            if len(bars) >= _MINIMUM_DECISION_QUALITY_ROWS
            else "architecture_capability"
        ),
        "decision_quality_evidence": len(bars) >= _MINIMUM_DECISION_QUALITY_ROWS,
        "architecture_capability": True,
        "process_overhead": False,
        "strategy": _strategy_policy_payload(),
        "comparators": _comparators_payload(),
        "oos_policy": _oos_policy_payload(),
        "cost_assumptions": _assumptions_payload(assumptions),
        "source_data": {
            **csv_result.source_metadata(),
            "basis": _BASIS,
        },
        "window_count": len(window_summaries),
        "decision_counts": dict(sorted(decision_counts.items())),
        "windows": window_summaries,
        "trade_record_count": len(trade_records),
        "router_preview": {
            "included": True,
            "strategy_id": _CANDIDATE_STRATEGY_ID,
            "promotion_status": "shadow_only",
            "paper_mutation_allowed": False,
            "reason": "candidate is unvalidated and mutation-ineligible",
        },
        "labels": list(_LABELS),
        "profit_claim": "none",
        "trend_pullback_promotion_status": "shadow_only",
        "trend_pullback_mutation_eligibility": False,
        "strategy_promotion_performed": False,
        "paper_preview_promotion_performed": False,
        "paper_mutation_promotion_performed": False,
        "threshold_change_performed": False,
        "threshold_optimization_performed": False,
        "parameter_search_performed": False,
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }
    return {
        "summary": summary,
        "backtest_by_window": window_summaries,
        "trades": trade_records,
    }


def classify_trend_pullback_decision(
    window_summaries: Iterable[Mapping[str, object]],
    *,
    source_usable_bar_count: int,
) -> str:
    """Map deterministic window evidence to one fixed v3.9 decision."""

    if not isinstance(source_usable_bar_count, int) or isinstance(
        source_usable_bar_count,
        bool,
    ):
        raise ValidationError("source_usable_bar_count must be an integer.")
    if source_usable_bar_count < _MINIMUM_DECISION_QUALITY_ROWS:
        return "needs_longer_oos"

    windows = tuple(_mapping(item, "window_summary") for item in window_summaries)
    if len(windows) < 3:
        return "needs_longer_oos"

    evidence_windows = tuple(
        window
        for window in windows
        if str(window.get("window_role"))
        in {"test", "holdout", "chronological_test", "oos_holdout"}
    ) or windows
    decisions = tuple(
        _decision_value(window.get("decision_classification"))
        for window in evidence_windows
    )
    counts = Counter(decisions)

    if counts.get("needs_longer_oos", 0) > 0:
        return "needs_longer_oos"
    if counts.get("reject_candidate", 0) == len(decisions):
        return "reject_candidate"
    if (
        counts.get("promote_to_paper_preview_candidate", 0) == len(decisions)
        and len(decisions) >= 3
    ):
        return "promote_to_paper_preview_candidate"
    if (
        counts.get("reject_candidate", 0) > 0
        or counts.get("needs_regime_filter", 0) > 0
        or (
            counts.get("promote_to_paper_preview_candidate", 0) > 0
            and counts.get("keep_shadow", 0) > 0
        )
    ):
        return "needs_regime_filter"
    return "keep_shadow"


def write_spy_trend_pullback_backtest_artifacts(
    packet: Mapping[str, object],
    output_root: Path | str = DEFAULT_TREND_PULLBACK_OUTPUT_ROOT,
) -> dict[str, Path]:
    """Write the v3.9 trend-pullback decision packet under ignored runs/."""

    summary = _mapping(packet.get("summary"), "summary")
    windows = _mapping_list(packet.get("backtest_by_window"), "backtest_by_window")
    trades = _mapping_list(packet.get("trades"), "trades")
    root = _path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)

    summary_path = root / "backtest_summary.json"
    trades_path = root / "backtest_trades.jsonl"
    by_window_path = root / "backtest_by_window.jsonl"
    brief_path = root / "decision_brief.md"

    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    trades_path.write_text(
        "".join(_json_dumps(record) + "\n" for record in trades),
        encoding="utf-8",
        newline="\n",
    )
    by_window_path.write_text(
        "".join(_json_dumps(record) + "\n" for record in windows),
        encoding="utf-8",
        newline="\n",
    )
    brief_path.write_text(
        render_spy_trend_pullback_decision_brief(summary),
        encoding="utf-8",
        newline="\n",
    )

    return {
        "backtest_summary_json": summary_path,
        "backtest_trades_jsonl": trades_path,
        "backtest_by_window_jsonl": by_window_path,
        "decision_brief_md": brief_path,
    }


def render_spy_trend_pullback_decision_brief(summary: Mapping[str, object]) -> str:
    """Render the compact operator-facing trend-pullback decision brief."""

    windows = _mapping_list(summary["windows"], "windows")
    strategy = _mapping(summary["strategy"], "strategy")
    cost_assumptions = _mapping(summary["cost_assumptions"], "cost_assumptions")
    lines = [
        "# v3.9 Fixed-Parameter SPY Trend-Pullback Backtest Decision Gate",
        "",
        f"run_id: {summary['run_id']}",
        f"classification_recommendation: {summary['classification_recommendation']}",
        f"final_decision: {summary['final_decision']}",
        f"evidence_result: {summary['evidence_result']}",
        f"decision_rationale: {summary['decision_rationale']}",
        "",
        "## Fixed Parameters",
        "",
        f"- symbol: {strategy['symbol']}",
        f"- basis: {strategy['basis']}",
        f"- trend_filter: {strategy['trend_filter']}",
        f"- pullback_trigger: {strategy['pullback_trigger']}",
        f"- exit_rule: {strategy['exit_rule']}",
        (
            "- threshold_optimization_performed: "
            f"{str(summary['threshold_optimization_performed']).lower()}"
        ),
        (
            "- parameter_search_performed: "
            f"{str(summary['parameter_search_performed']).lower()}"
        ),
        "",
        "## Cost Assumptions",
        "",
        f"- initial_equity: {cost_assumptions['initial_equity']}",
        f"- fee_bps: {cost_assumptions['fee_bps']}",
        f"- slippage_bps: {cost_assumptions['slippage_bps']}",
        f"- total_cost_bps_per_transition: {cost_assumptions['total_cost_bps_per_transition']}",
        "",
        "## Window Metrics",
        "",
        (
            "| window | dates | rows | candidate total return | "
            "candidate max drawdown | candidate Sharpe-like | exposure % | "
            "trades | decision |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for window in windows:
        metrics = _mapping(window["metrics_by_strategy"], "metrics_by_strategy")
        candidate = _mapping(metrics[_CANDIDATE_STRATEGY_ID], "candidate_metrics")
        lines.append(
            "| {window_id} | {start} to {end} | {rows} | {total_return} | "
            "{max_drawdown} | {sharpe} | {exposure} | {trades} | {decision} |".format(
                window_id=window["window_id"],
                start=window["start_date"],
                end=window["end_date"],
                rows=window["row_count"],
                total_return=candidate["total_return"],
                max_drawdown=candidate["max_drawdown"],
                sharpe=candidate["sharpe_like_score"],
                exposure=candidate["exposure_percentage"],
                trades=candidate["trade_count"],
                decision=window["decision_classification"],
            )
        )

    lines.extend(
        [
            "",
            "## Safety",
            "",
            (
                "- trend_pullback_promotion_status: "
                f"{summary['trend_pullback_promotion_status']}"
            ),
            (
                "- trend_pullback_mutation_eligibility: "
                f"{str(summary['trend_pullback_mutation_eligibility']).lower()}"
            ),
            (
                "- paper_mutation_promotion_performed: "
                f"{str(summary['paper_mutation_promotion_performed']).lower()}"
            ),
            f"- broker_read_performed: {str(summary['broker_read_performed']).lower()}",
            f"- broker_mutation_performed: {str(summary['broker_mutation_performed']).lower()}",
            f"- paper_submit_performed: {str(summary['paper_submit_performed']).lower()}",
            f"- live_endpoint_used: {str(summary['live_endpoint_used']).lower()}",
            f"- network_fetch_performed: {str(summary['network_fetch_performed']).lower()}",
            f"- profit_claim: {summary['profit_claim']}",
            "",
            (
                "This packet is fixed-parameter, offline-only, and shadow-only. "
                "It does not optimize thresholds, promote the challenger to paper "
                "mutation, read broker state, submit orders, or contact a live endpoint."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spy-trend-pullback-backtest",
        description=(
            "Run the fixed-parameter SPY trend-pullback challenger backtest using "
            "local adjusted daily bars only."
        ),
    )
    parser.add_argument(
        "--daily-bars-csv",
        default=str(DEFAULT_TREND_PULLBACK_DAILY_BARS_CSV),
    )
    parser.add_argument("--output-root", default=str(DEFAULT_TREND_PULLBACK_OUTPUT_ROOT))
    parser.add_argument("--run-id", default=DEFAULT_TREND_PULLBACK_RUN_ID)
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument("--initial-equity", default=str(_DEFAULT_INITIAL_EQUITY))
    parser.add_argument("--fee-bps", default=str(_DEFAULT_FEE_BPS))
    parser.add_argument("--slippage-bps", default=str(_DEFAULT_SLIPPAGE_BPS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        packet = build_spy_trend_pullback_backtest_packet(
            daily_bars_csv=args.daily_bars_csv,
            as_of_date=args.as_of_date,
            run_id=args.run_id,
            initial_equity=args.initial_equity,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
        )
        paths = write_spy_trend_pullback_backtest_artifacts(packet, args.output_root)
    except ValidationError as exc:
        print(f"blocked: {exc}")
        return 2

    summary = _mapping(packet["summary"], "summary")
    print("spy_trend_pullback_backtest_status=completed")
    print(f"classification_recommendation={summary['classification_recommendation']}")
    print(f"final_decision={summary['final_decision']}")
    print(f"window_count={summary['window_count']}")
    print("broker_read_performed=false")
    print("broker_mutation_performed=false")
    print("paper_submit_performed=false")
    print("network_fetch_performed=false")
    for name, path in paths.items():
        print(f"{name}={path.as_posix()}")
    return 0


def _build_window_backtest(
    *,
    run_id: str,
    bars: tuple[LocalDailyBar, ...],
    window: _WindowSlice,
    assumptions: DailyBacktestAssumptions,
    indicators: _IndicatorSeries,
    exposures_by_strategy: Mapping[str, tuple[DailyExposure, ...]],
) -> tuple[dict[str, object], tuple[dict[str, object], ...]]:
    window_bars = bars[window.start_index : window.end_index]
    snapshot = _snapshot(window_bars)
    metrics_by_strategy: dict[str, dict[str, object]] = {}
    trade_records: list[dict[str, object]] = []
    for strategy_id in _STRATEGY_ORDER:
        exposures = exposures_by_strategy[strategy_id][window.start_index : window.end_index]
        result = run_daily_backtest(snapshot, exposures, assumptions)
        strategy_trades = _trade_records(
            run_id=run_id,
            window=window,
            strategy_id=strategy_id,
            bars=window_bars,
            exposures=exposures,
            result=result,
            indicators=indicators,
            indicator_offset=window.start_index,
        )
        trade_records.extend(strategy_trades)
        metrics_by_strategy[strategy_id] = _metrics_payload(
            strategy_id=strategy_id,
            window=window,
            bars=window_bars,
            exposures=exposures,
            result=result,
            assumptions=assumptions,
        )

    comparisons = _window_comparisons(metrics_by_strategy)
    summary_base = {
        "record_type": _RECORD_TYPE_WINDOW,
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        **window.to_dict(bars),
        "symbol": _SYMBOL,
        "basis": _BASIS,
        "metrics_by_strategy": metrics_by_strategy,
        "comparisons": comparisons,
        "cost_assumptions": _assumptions_payload(assumptions),
        "trade_record_count": len(trade_records),
        "parameter_policy": _parameter_policy_payload(),
        "labels": list(_LABELS),
        "profit_claim": "none",
        "trend_pullback_mutation_eligibility": False,
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }
    decision = _classify_window(summary_base)
    summary = {
        **summary_base,
        "decision_classification": decision,
        "decision_rationale": _window_decision_rationale(decision, summary_base),
    }
    return summary, tuple(trade_records)


def _metrics_payload(
    *,
    strategy_id: str,
    window: _WindowSlice,
    bars: tuple[LocalDailyBar, ...],
    exposures: tuple[DailyExposure, ...],
    result: DailyBacktestResult,
    assumptions: DailyBacktestAssumptions,
) -> dict[str, object]:
    holding_stats = _holding_stats(bars, exposures)
    returns = tuple(point.strategy_return_after_costs for point in result.points)
    annualized_return = _annualized_return(
        result.total_return,
        bars[0].date,
        bars[-1].date,
    )
    annualized_volatility = _annualized_volatility(returns)
    sharpe_like = _ratio_or_none(annualized_return, annualized_volatility)
    transaction_cost_return = sum(
        (point.transaction_cost for point in result.points),
        _ZERO,
    )
    exposure_percentage = result.exposure_ratio * _HUNDRED
    return {
        "strategy_id": strategy_id,
        "strategy_label": _strategy_label(strategy_id),
        "strategy_role": _strategy_role(strategy_id),
        "symbol": _SYMBOL,
        "basis": _BASIS,
        "timeframe": _TIMEFRAME,
        "window_id": window.window_id,
        "start_date": bars[0].date.isoformat(),
        "end_date": bars[-1].date.isoformat(),
        "row_count": len(bars),
        "initial_equity": _decimal_text(result.starting_equity),
        "ending_equity": _decimal_text(result.ending_equity),
        "total_return": _decimal_text(result.total_return),
        "cagr": _optional_decimal_text(annualized_return),
        "annualized_return": _optional_decimal_text(annualized_return),
        "annualized_volatility": _optional_decimal_text(annualized_volatility),
        "sharpe_like_score": _optional_decimal_text(sharpe_like),
        "risk_adjusted_proxy": _optional_decimal_text(sharpe_like),
        "max_drawdown": _decimal_text(result.max_drawdown),
        "exposure_ratio": _decimal_text(result.exposure_ratio),
        "exposure_percentage": _decimal_text(exposure_percentage),
        "trade_count": _transition_count(exposures),
        "turnover": _decimal_text(result.turnover),
        "win_count": holding_stats["win_count"],
        "loss_count": holding_stats["loss_count"],
        "flat_count": holding_stats["flat_count"],
        "holding_period_count": holding_stats["holding_period_count"],
        "average_holding_period_days": holding_stats["average_holding_period_days"],
        "open_position_at_end": holding_stats["open_position_at_end"],
        "win_loss_basis": "closed_and_marked_to_window_end_for_open_position",
        "cost_assumptions": _assumptions_payload(assumptions),
        "total_transaction_cost_return_fraction": _decimal_text(
            transaction_cost_return,
        ),
        "long_only": True,
        "cash_allowed": True,
        "shorting_allowed": False,
        "leverage_allowed": False,
        "options_allowed": False,
    }


def _trade_records(
    *,
    run_id: str,
    window: _WindowSlice,
    strategy_id: str,
    bars: tuple[LocalDailyBar, ...],
    exposures: tuple[DailyExposure, ...],
    result: DailyBacktestResult,
    indicators: _IndicatorSeries,
    indicator_offset: int,
) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    previous_exposure = _ZERO
    sequence = 0
    for index, (bar, exposure, point) in enumerate(zip(bars, exposures, result.points)):
        current_exposure = exposure.exposure
        if current_exposure == previous_exposure:
            previous_exposure = current_exposure
            continue
        action = "buy" if current_exposure > previous_exposure else "sell_close"
        absolute_index = indicator_offset + index
        records.append(
            {
                "record_type": _RECORD_TYPE_TRADE,
                "schema_version": _SCHEMA_VERSION,
                "run_id": run_id,
                "window_id": window.window_id,
                "strategy_id": strategy_id,
                "trade_sequence": sequence,
                "date": bar.date.isoformat(),
                "action": action,
                "from_exposure": _decimal_text(previous_exposure),
                "to_exposure": _decimal_text(current_exposure),
                "adjusted_close": _decimal_text(bar.adjusted_close),
                "transaction_cost_return_fraction": _decimal_text(
                    point.transaction_cost,
                ),
                "rsi": _optional_decimal_text(indicators.rsi[absolute_index]),
                "sma20": _optional_decimal_text(indicators.sma_pullback[absolute_index]),
                "sma50": _optional_decimal_text(indicators.sma_short[absolute_index]),
                "sma200": _optional_decimal_text(indicators.sma_long[absolute_index]),
                "reason": _trade_reason(
                    strategy_id=strategy_id,
                    action=action,
                    adjusted_close=bar.adjusted_close,
                    rsi=indicators.rsi[absolute_index],
                    sma20=indicators.sma_pullback[absolute_index],
                    sma50=indicators.sma_short[absolute_index],
                    sma200=indicators.sma_long[absolute_index],
                    index=index,
                ),
                "profit_claim": "none",
                "broker_read_performed": False,
                "broker_mutation_performed": False,
                "paper_submit_performed": False,
                "live_endpoint_used": False,
                "network_fetch_performed": False,
            }
        )
        sequence += 1
        previous_exposure = current_exposure
    return tuple(records)


def _holding_stats(
    bars: tuple[LocalDailyBar, ...],
    exposures: tuple[DailyExposure, ...],
) -> dict[str, object]:
    previous = _ZERO
    entry_date: date | None = None
    entry_price: Decimal | None = None
    wins = 0
    losses = 0
    flats = 0
    durations: list[int] = []

    for bar, exposure in zip(bars, exposures):
        current = exposure.exposure
        if previous == _ZERO and current > _ZERO:
            entry_date = bar.date
            entry_price = bar.adjusted_close
        elif previous > _ZERO and current == _ZERO and entry_date is not None:
            assert entry_price is not None
            holding_return = (bar.adjusted_close / entry_price) - _ONE
            if holding_return > _ZERO:
                wins += 1
            elif holding_return < _ZERO:
                losses += 1
            else:
                flats += 1
            durations.append((bar.date - entry_date).days)
            entry_date = None
            entry_price = None
        previous = current

    open_position = previous > _ZERO and entry_date is not None
    if open_position:
        assert entry_price is not None
        holding_return = (bars[-1].adjusted_close / entry_price) - _ONE
        if holding_return > _ZERO:
            wins += 1
        elif holding_return < _ZERO:
            losses += 1
        else:
            flats += 1
        durations.append((bars[-1].date - entry_date).days)

    count = wins + losses + flats
    average = None
    if durations:
        average = _decimal_text(
            sum(Decimal(item) for item in durations) / Decimal(len(durations))
        )
    return {
        "win_count": wins,
        "loss_count": losses,
        "flat_count": flats,
        "holding_period_count": count,
        "average_holding_period_days": average,
        "open_position_at_end": open_position,
    }


def _window_comparisons(
    metrics_by_strategy: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    candidate = _mapping(
        metrics_by_strategy[_CANDIDATE_STRATEGY_ID],
        "candidate_metrics",
    )
    sma = _mapping(metrics_by_strategy[_SMA_STRATEGY_ID], "sma_metrics")
    buy_hold = _mapping(
        metrics_by_strategy[_BUY_AND_HOLD_STRATEGY_ID],
        "buy_hold_metrics",
    )
    rejected_rsi = _mapping(
        metrics_by_strategy[_REJECTED_RSI_STRATEGY_ID],
        "rejected_rsi_metrics",
    )
    return {
        "candidate_vs_buy_and_hold": _comparison_payload(
            candidate=candidate,
            benchmark=buy_hold,
            benchmark_id=_BUY_AND_HOLD_STRATEGY_ID,
        ),
        "candidate_vs_sma": _comparison_payload(
            candidate=candidate,
            benchmark=sma,
            benchmark_id=_SMA_STRATEGY_ID,
        ),
        "candidate_vs_rejected_rsi": _comparison_payload(
            candidate=candidate,
            benchmark=rejected_rsi,
            benchmark_id=_REJECTED_RSI_STRATEGY_ID,
        ),
        "sma_vs_buy_and_hold": _comparison_payload(
            candidate=sma,
            benchmark=buy_hold,
            benchmark_id=_BUY_AND_HOLD_STRATEGY_ID,
        ),
        "rejected_rsi_vs_buy_and_hold": _comparison_payload(
            candidate=rejected_rsi,
            benchmark=buy_hold,
            benchmark_id=_BUY_AND_HOLD_STRATEGY_ID,
        ),
    }


def _comparison_payload(
    *,
    candidate: Mapping[str, object],
    benchmark: Mapping[str, object],
    benchmark_id: str,
) -> dict[str, object]:
    total_delta = _metric_decimal(candidate, "total_return") - _metric_decimal(
        benchmark,
        "total_return",
    )
    annualized_delta = _optional_metric_delta(
        candidate,
        benchmark,
        "annualized_return",
    )
    drawdown_delta = _metric_decimal(candidate, "max_drawdown") - _metric_decimal(
        benchmark,
        "max_drawdown",
    )
    sharpe_delta = _optional_metric_delta(candidate, benchmark, "sharpe_like_score")
    return {
        "candidate_strategy_id": candidate["strategy_id"],
        "benchmark_strategy_id": benchmark_id,
        "benchmark": benchmark_id,
        "total_return_delta": _decimal_text(total_delta),
        "annualized_return_delta": _optional_decimal_text(annualized_delta),
        "max_drawdown_delta": _decimal_text(drawdown_delta),
        "sharpe_like_score_delta": _optional_decimal_text(sharpe_delta),
        "underperformed_total_return": total_delta < _ZERO,
        "overperformed_total_return": total_delta > _ZERO,
        "total_return_relation": _relation(total_delta),
        "risk_adjusted_relation": _optional_relation(sharpe_delta),
    }


def _classify_window(window_summary: Mapping[str, object]) -> str:
    if _int_value(window_summary["row_count"], "row_count") < _SMA_LONG_WINDOW:
        return "needs_longer_oos"

    metrics = _mapping(window_summary["metrics_by_strategy"], "metrics_by_strategy")
    comparisons = _mapping(window_summary["comparisons"], "comparisons")
    candidate = _mapping(metrics[_CANDIDATE_STRATEGY_ID], "candidate_metrics")
    candidate_vs_buy = _mapping(
        comparisons["candidate_vs_buy_and_hold"],
        "candidate_vs_buy_and_hold",
    )
    candidate_vs_sma = _mapping(comparisons["candidate_vs_sma"], "candidate_vs_sma")

    candidate_total_return = _metric_decimal(candidate, "total_return")
    candidate_trade_count = _int_value(candidate["trade_count"], "trade_count")
    candidate_exposure = _metric_decimal(candidate, "exposure_percentage")
    total_delta_buy = _metric_decimal(candidate_vs_buy, "total_return_delta")
    total_delta_sma = _metric_decimal(candidate_vs_sma, "total_return_delta")
    drawdown_delta_buy = _metric_decimal(candidate_vs_buy, "max_drawdown_delta")
    drawdown_delta_sma = _metric_decimal(candidate_vs_sma, "max_drawdown_delta")
    sharpe_delta_buy = _optional_metric_decimal(
        candidate_vs_buy,
        "sharpe_like_score_delta",
    )
    sharpe_delta_sma = _optional_metric_decimal(
        candidate_vs_sma,
        "sharpe_like_score_delta",
    )

    no_candidate_evidence = candidate_trade_count == 0 or candidate_exposure == _ZERO
    if no_candidate_evidence:
        return "keep_shadow"

    underperformed_both = total_delta_buy < _ZERO and total_delta_sma < _ZERO
    sharpe_worse_both = (
        sharpe_delta_buy is not None
        and sharpe_delta_sma is not None
        and sharpe_delta_buy < _ZERO
        and sharpe_delta_sma < _ZERO
    )
    severe_return_degradation = (
        candidate_total_return < _ZERO
        or (total_delta_buy <= Decimal("-0.05") and total_delta_sma <= Decimal("-0.05"))
    )
    if underperformed_both and (sharpe_worse_both or severe_return_degradation):
        return "reject_candidate"

    strong = (
        candidate_total_return > _ZERO
        and total_delta_buy >= _ZERO
        and total_delta_sma >= _ZERO
        and drawdown_delta_buy <= _ZERO
        and drawdown_delta_sma <= _ZERO
        and (sharpe_delta_buy is None or sharpe_delta_buy >= _ZERO)
        and (sharpe_delta_sma is None or sharpe_delta_sma >= _ZERO)
    )
    if strong:
        return "promote_to_paper_preview_candidate"

    if (
        (total_delta_buy > _ZERO and total_delta_sma <= _ZERO)
        or (total_delta_buy <= _ZERO and total_delta_sma > _ZERO)
        or (drawdown_delta_buy < _ZERO and total_delta_buy < _ZERO)
        or (drawdown_delta_sma < _ZERO and total_delta_sma < _ZERO)
        or (sharpe_delta_buy is not None and sharpe_delta_sma is not None
            and sharpe_delta_buy * sharpe_delta_sma < _ZERO)
    ):
        return "needs_regime_filter"

    return "keep_shadow"


def _window_decision_rationale(
    decision: str,
    window_summary: Mapping[str, object],
) -> str:
    comparisons = _mapping(window_summary["comparisons"], "comparisons")
    buy = _mapping(comparisons["candidate_vs_buy_and_hold"], "candidate_vs_buy_and_hold")
    sma = _mapping(comparisons["candidate_vs_sma"], "candidate_vs_sma")
    return (
        f"{decision}: trend-pullback total-return deltas were "
        f"{buy['total_return_delta']} versus buy-and-hold and "
        f"{sma['total_return_delta']} versus SMA50/200; Sharpe-like deltas were "
        f"{buy['sharpe_like_score_delta']} and {sma['sharpe_like_score_delta']}."
    )


def _decision_rationale(
    decision: str,
    windows: Sequence[Mapping[str, object]],
    source_usable_bar_count: int,
) -> str:
    counts = Counter(str(window["decision_classification"]) for window in windows)
    if decision == "needs_longer_oos":
        return (
            f"Only {source_usable_bar_count} usable bars were available; "
            f"{_MINIMUM_DECISION_QUALITY_ROWS} are required for decision-quality OOS."
        )
    return f"Window decision counts: {dict(sorted(counts.items()))}."


def _indicator_series(bars: tuple[LocalDailyBar, ...]) -> _IndicatorSeries:
    closes = tuple(bar.adjusted_close for bar in bars)
    return _IndicatorSeries(
        rsi=_rolling_rsi(closes, _RSI_LOOKBACK_WINDOW),
        sma_pullback=_rolling_sma(closes, _PULLBACK_SMA_WINDOW),
        sma_short=_rolling_sma(closes, _SMA_SHORT_WINDOW),
        sma_long=_rolling_sma(closes, _SMA_LONG_WINDOW),
    )


def _build_strategy_exposures(
    bars: tuple[LocalDailyBar, ...],
    indicators: _IndicatorSeries,
) -> dict[str, tuple[DailyExposure, ...]]:
    buy_hold = tuple(DailyExposure(bar.date, _ONE) for bar in bars)
    sma: list[DailyExposure] = []
    rejected_rsi: list[DailyExposure] = []
    candidate: list[DailyExposure] = []
    rsi_current = _ZERO
    candidate_current = _ZERO
    for index, bar in enumerate(bars):
        sma50 = indicators.sma_short[index]
        sma200 = indicators.sma_long[index]
        sma20 = indicators.sma_pullback[index]
        adjusted_close = bar.adjusted_close
        trend_favorable = sma50 is not None and sma200 is not None and sma50 > sma200

        sma_exposure = _ONE if trend_favorable else _ZERO
        sma.append(DailyExposure(bar.date, sma_exposure))

        rsi_value = indicators.rsi[index]
        if rsi_value is None:
            rsi_current = _ZERO
        elif rsi_value <= _RSI_OVERSOLD_THRESHOLD:
            rsi_current = _ONE
        elif rsi_value >= _RSI_OVERBOUGHT_THRESHOLD:
            rsi_current = _ZERO
        rejected_rsi.append(DailyExposure(bar.date, rsi_current))

        if not trend_favorable:
            candidate_current = _ZERO
        elif candidate_current > _ZERO:
            if sma50 is not None and adjusted_close >= sma50:
                candidate_current = _ZERO
        elif sma20 is not None and adjusted_close <= sma20:
            candidate_current = _ONE
        candidate.append(DailyExposure(bar.date, candidate_current))

    return {
        _BUY_AND_HOLD_STRATEGY_ID: buy_hold,
        _SMA_STRATEGY_ID: tuple(sma),
        _REJECTED_RSI_STRATEGY_ID: tuple(rejected_rsi),
        _CANDIDATE_STRATEGY_ID: tuple(candidate),
    }


def _rolling_sma(
    closes: tuple[Decimal, ...],
    window: int,
) -> tuple[Decimal | None, ...]:
    values: list[Decimal | None] = []
    running = _ZERO
    for index, close in enumerate(closes):
        running += close
        if index >= window:
            running -= closes[index - window]
        values.append(None if index + 1 < window else running / Decimal(window))
    return tuple(values)


def _rolling_rsi(
    closes: tuple[Decimal, ...],
    lookback_window: int,
) -> tuple[Decimal | None, ...]:
    latest_rsi: list[Decimal | None] = []
    gains = [_ZERO for _ in closes]
    losses = [_ZERO for _ in closes]
    for index in range(1, len(closes)):
        delta = closes[index] - closes[index - 1]
        gains[index] = delta if delta > _ZERO else _ZERO
        losses[index] = -delta if delta < _ZERO else _ZERO

    running_gain = _ZERO
    running_loss = _ZERO
    for index in range(len(closes)):
        running_gain += gains[index]
        running_loss += losses[index]
        if index > lookback_window:
            running_gain -= gains[index - lookback_window]
            running_loss -= losses[index - lookback_window]
        if index < lookback_window:
            latest_rsi.append(None)
            continue

        average_gain = running_gain / Decimal(lookback_window)
        average_loss = running_loss / Decimal(lookback_window)
        if average_gain == _ZERO and average_loss == _ZERO:
            latest_rsi.append(Decimal("50"))
        elif average_loss == _ZERO:
            latest_rsi.append(_HUNDRED)
        else:
            relative_strength = average_gain / average_loss
            latest_rsi.append(_HUNDRED - (_HUNDRED / (_ONE + relative_strength)))
    return tuple(latest_rsi)


def _window_slices(source_row_count: int) -> tuple[_WindowSlice, ...]:
    if not isinstance(source_row_count, int) or isinstance(source_row_count, bool):
        raise ValidationError("source_row_count must be an integer.")
    if source_row_count <= 0:
        raise ValidationError("source_row_count must be positive.")

    windows = [
        _WindowSlice(
            window_id="full_available_reference",
            window_role="reference",
            description="Full available accepted SPY adjusted daily bars",
            start_index=0,
            end_index=source_row_count,
        )
    ]
    if source_row_count >= 2:
        split_index = source_row_count // 2
        windows.extend(
            (
                _WindowSlice(
                    window_id="chronological_earlier_half",
                    window_role="train_reference",
                    description="Earlier chronological half; fixed-parameter reference only",
                    start_index=0,
                    end_index=split_index,
                ),
                _WindowSlice(
                    window_id="chronological_later_half",
                    window_role="chronological_test",
                    description="Later chronological half; no parameters tuned on earlier half",
                    start_index=split_index,
                    end_index=source_row_count,
                ),
            )
        )
    if source_row_count >= _THREE_YEAR_ROW_COUNT:
        windows.append(
            _WindowSlice(
                window_id="recent_3y_holdout",
                window_role="holdout",
                description="Most recent 756 accepted bars, approximately 3 trading years",
                start_index=source_row_count - _THREE_YEAR_ROW_COUNT,
                end_index=source_row_count,
            )
        )
    if source_row_count >= _FIVE_YEAR_ROW_COUNT:
        start = source_row_count - _FIVE_YEAR_ROW_COUNT
        split = start + (_FIVE_YEAR_ROW_COUNT // 2)
        windows.extend(
            (
                _WindowSlice(
                    window_id="trailing_5y_earlier_half",
                    window_role="train_reference",
                    description="Earlier half of the most recent 1260 accepted bars",
                    start_index=start,
                    end_index=split,
                ),
                _WindowSlice(
                    window_id="trailing_5y_later_half",
                    window_role="test",
                    description="Later half of the most recent 1260 accepted bars",
                    start_index=split,
                    end_index=source_row_count,
                ),
            )
        )
    return tuple(windows)


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


def _strategy_policy_payload() -> dict[str, object]:
    return {
        "strategy_id": _CANDIDATE_STRATEGY_ID,
        "strategy_family": "trend_pullback",
        "symbol": _SYMBOL,
        "basis": _BASIS,
        "timeframe": _TIMEFRAME,
        "trend_filter": "SMA50 > SMA200",
        "trend_short_window": _SMA_SHORT_WINDOW,
        "trend_long_window": _SMA_LONG_WINDOW,
        "pullback_sma_window": _PULLBACK_SMA_WINDOW,
        "recovery_exit_sma_window": _RECOVERY_EXIT_SMA_WINDOW,
        "parameters_evaluated": {
            "trend_filter": ["SMA50 > SMA200"],
            "pullback_sma_window": [_PULLBACK_SMA_WINDOW],
            "recovery_exit_sma_window": [_RECOVERY_EXIT_SMA_WINDOW],
        },
        "pullback_trigger": "SMA50 > SMA200 and adjusted_close <= SMA20",
        "entry_rule": "enter long from cash when trend is favorable and adjusted_close <= SMA20",
        "exit_rule": "exit to cash when SMA50 <= SMA200 or adjusted_close >= SMA50",
        "neutral_rule": "hold prior long/cash state while trend remains favorable",
        "insufficient_history_rule": "cash until SMA200, SMA50, and SMA20 are available",
        "long_only": True,
        "shorting_allowed": False,
        "leverage_allowed": False,
        "options_allowed": False,
        "promotion_status": "shadow_only",
        "mutation_eligible": False,
        "parameter_source": (
            "Predeclared v3.9 fixed parameters; no threshold tuning, "
            "optimization, or parameter search performed."
        ),
    }


def _parameter_policy_payload() -> dict[str, object]:
    return {
        "review_type": "fixed_parameter_trend_pullback_backtest",
        "trend_filter": "SMA50 > SMA200",
        "trend_short_window": _SMA_SHORT_WINDOW,
        "trend_long_window": _SMA_LONG_WINDOW,
        "pullback_sma_window": _PULLBACK_SMA_WINDOW,
        "recovery_exit_sma_window": _RECOVERY_EXIT_SMA_WINDOW,
        "parameters_evaluated": {
            "trend_filter": ["SMA50 > SMA200"],
            "pullback_sma_window": [_PULLBACK_SMA_WINDOW],
            "recovery_exit_sma_window": [_RECOVERY_EXIT_SMA_WINDOW],
        },
        "optimization_performed": False,
        "parameter_search_performed": False,
        "threshold_optimization_performed": False,
        "threshold_change_performed": False,
    }


def _comparators_payload() -> list[dict[str, object]]:
    return [
        {
            "strategy_id": _BUY_AND_HOLD_STRATEGY_ID,
            "strategy_label": "Buy-and-hold SPY",
            "basis": _BASIS,
            "exposure_rule": "long exposure is 1 on every evaluated bar",
            "role": "buy_and_hold_comparator",
        },
        {
            "strategy_id": _SMA_STRATEGY_ID,
            "strategy_label": "SMA50/200 training-wheel baseline",
            "basis": _BASIS,
            "short_window": _SMA_SHORT_WINDOW,
            "long_window": _SMA_LONG_WINDOW,
            "risk_on_rule": "SMA50 > SMA200",
            "risk_off_rule": "SMA50 <= SMA200",
            "role": "training_wheel_baseline",
        },
        {
            "strategy_id": _REJECTED_RSI_STRATEGY_ID,
            "strategy_label": "Rejected fixed RSI-14 mean-reversion candidate",
            "basis": _BASIS,
            "rsi_period": _RSI_LOOKBACK_WINDOW,
            "oversold_threshold": _decimal_text(_RSI_OVERSOLD_THRESHOLD),
            "overbought_threshold": _decimal_text(_RSI_OVERBOUGHT_THRESHOLD),
            "role": "rejected_shadow_comparator",
            "rejection_source": "v3.8 fixed-parameter SPY RSI OOS decision gate",
        },
    ]


def _oos_policy_payload() -> dict[str, object]:
    return {
        "method": "fixed_chronological_splits_no_parameter_tuning",
        "minimum_decision_quality_rows": _MINIMUM_DECISION_QUALITY_ROWS,
        "windows": [
            "full_available_reference",
            "chronological_earlier_half",
            "chronological_later_half",
            "recent_3y_holdout",
            "trailing_5y_earlier_half",
            "trailing_5y_later_half",
        ],
        "threshold_optimization_performed": False,
        "parameter_search_performed": False,
    }


def _assumptions_payload(assumptions: DailyBacktestAssumptions) -> dict[str, object]:
    return {
        "initial_equity": _decimal_text(assumptions.initial_equity),
        "fee_bps": _decimal_text(assumptions.fee_bps),
        "slippage_bps": _decimal_text(assumptions.slippage_bps),
        "total_cost_bps_per_transition": _decimal_text(
            assumptions.fee_bps + assumptions.slippage_bps,
        ),
        "cost_model": (
            "daily_backtest applies abs(exposure_delta) * "
            "total_cost_bps_per_transition / 10000"
        ),
    }


def _strategy_label(strategy_id: str) -> str:
    if strategy_id == _BUY_AND_HOLD_STRATEGY_ID:
        return "Buy-and-hold SPY"
    if strategy_id == _SMA_STRATEGY_ID:
        return "SMA50/200 training-wheel baseline"
    if strategy_id == _REJECTED_RSI_STRATEGY_ID:
        return "Rejected fixed RSI-14 mean-reversion shadow comparator"
    if strategy_id == _CANDIDATE_STRATEGY_ID:
        return "Fixed SPY trend-pullback shadow challenger"
    raise ValidationError(f"unsupported strategy_id: {strategy_id}")


def _strategy_role(strategy_id: str) -> str:
    if strategy_id == _BUY_AND_HOLD_STRATEGY_ID:
        return "buy_and_hold_comparator"
    if strategy_id == _SMA_STRATEGY_ID:
        return "training_wheel_baseline"
    if strategy_id == _REJECTED_RSI_STRATEGY_ID:
        return "rejected_shadow_comparator"
    if strategy_id == _CANDIDATE_STRATEGY_ID:
        return "shadow_candidate"
    raise ValidationError(f"unsupported strategy_id: {strategy_id}")


def _trade_reason(
    *,
    strategy_id: str,
    action: str,
    adjusted_close: Decimal,
    rsi: Decimal | None,
    sma20: Decimal | None,
    sma50: Decimal | None,
    sma200: Decimal | None,
    index: int,
) -> str:
    if strategy_id == _BUY_AND_HOLD_STRATEGY_ID:
        return "buy_and_hold_initial_long" if index == 0 else "buy_and_hold_reentry"
    if strategy_id == _SMA_STRATEGY_ID:
        if sma50 is None or sma200 is None:
            return "sma_insufficient_history_window_start"
        if index == 0:
            return "window_start_existing_sma_state"
        return "sma50_above_sma200" if action == "buy" else "sma50_not_above_sma200"
    if strategy_id == _REJECTED_RSI_STRATEGY_ID:
        if rsi is None:
            return "rsi_insufficient_history_window_start"
        if index == 0:
            return "window_start_existing_rejected_rsi_state"
        if action == "buy":
            if rsi <= _RSI_OVERSOLD_THRESHOLD:
                return "rsi_at_or_below_oversold_threshold_rejected_comparator"
            return "rsi_state_reentry_rejected_comparator"
        if rsi >= _RSI_OVERBOUGHT_THRESHOLD:
            return "rsi_at_or_above_overbought_threshold_rejected_comparator"
        return "rsi_state_exit_rejected_comparator"
    if strategy_id == _CANDIDATE_STRATEGY_ID:
        if sma20 is None or sma50 is None or sma200 is None:
            return "trend_pullback_insufficient_history_window_start"
        if index == 0:
            return "window_start_existing_trend_pullback_state"
        trend_favorable = sma50 > sma200
        if action == "buy" and trend_favorable and adjusted_close <= sma20:
            return "trend_favorable_adjusted_close_at_or_below_sma20"
        if action == "sell_close" and not trend_favorable:
            return "trend_filter_off_sma50_not_above_sma200"
        if action == "sell_close" and adjusted_close >= sma50:
            return "adjusted_close_at_or_above_sma50_recovery_exit"
        return "trend_pullback_state_transition"
    raise ValidationError(f"unsupported strategy_id: {strategy_id}")


def _annualized_return(
    total_return: Decimal,
    start_date: date,
    end_date: date,
) -> Decimal | None:
    day_count = (end_date - start_date).days
    if day_count <= 0:
        return None
    base = float(_ONE + total_return)
    if base <= 0:
        return None
    return _decimal_from_float(math.pow(base, _CALENDAR_DAYS_PER_YEAR / day_count) - 1)


def _annualized_volatility(returns: tuple[Decimal, ...]) -> Decimal | None:
    if len(returns) < 2:
        return None
    values = [float(item) for item in returns]
    return _decimal_from_float(stdev(values) * math.sqrt(float(_TRADING_DAYS_PER_YEAR)))


def _ratio_or_none(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= _ZERO:
        return None
    return numerator / denominator


def _transition_count(exposures: tuple[DailyExposure, ...]) -> int:
    transitions = 0
    previous = _ZERO
    for exposure in exposures:
        if exposure.exposure != previous:
            transitions += 1
        previous = exposure.exposure
    return transitions


def _relation(delta: Decimal) -> str:
    if delta > _ZERO:
        return "overperformed"
    if delta < _ZERO:
        return "underperformed"
    return "matched"


def _optional_relation(delta: Decimal | None) -> str:
    if delta is None:
        return "not_available"
    return _relation(delta)


def _optional_metric_delta(
    candidate: Mapping[str, object],
    benchmark: Mapping[str, object],
    field_name: str,
) -> Decimal | None:
    candidate_value = _optional_metric_decimal(candidate, field_name)
    benchmark_value = _optional_metric_decimal(benchmark, field_name)
    if candidate_value is None or benchmark_value is None:
        return None
    return candidate_value - benchmark_value


def _metric_decimal(metrics: Mapping[str, object], field_name: str) -> Decimal:
    value = metrics.get(field_name)
    if value is None:
        raise ValidationError(f"{field_name} is required.")
    return _decimal_value(value, field_name)


def _optional_metric_decimal(
    metrics: Mapping[str, object],
    field_name: str,
) -> Decimal | None:
    value = metrics.get(field_name)
    if value is None:
        return None
    return _decimal_value(value, field_name)


def _positive_decimal(value: Decimal | str, field_name: str) -> Decimal:
    checked = _decimal_value(value, field_name)
    if checked <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return checked


def _non_negative_decimal(value: Decimal | str, field_name: str) -> Decimal:
    checked = _decimal_value(value, field_name)
    if checked < _ZERO:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return checked


def _decimal_value(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        checked = value
    elif isinstance(value, str):
        try:
            checked = Decimal(value.strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{field_name} must be decimal-compatible.") from exc
    else:
        raise ValidationError(f"{field_name} must be a Decimal or string.")
    if not checked.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return checked


def _int_value(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    return value


def _decision_value(value: object) -> str:
    if not isinstance(value, str) or value not in TREND_PULLBACK_DECISIONS:
        raise ValidationError("decision_classification must be a supported decision.")
    return value


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _mapping_list(value: object, field_name: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list.")
    return [_mapping(item, f"{field_name}[]") for item in value]


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        if not value.strip():
            raise ValidationError(f"{field_name} is required.")
        if "://" in value:
            raise ValidationError(f"{field_name} must be a local path.")
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a path.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _decimal_from_float(value: float) -> Decimal:
    if not math.isfinite(value):
        raise ValidationError("metric must be finite.")
    return Decimal(f"{value:.12f}")


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _json_dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"))


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
