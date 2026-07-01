"""Generate longer-window SMA/RSI shadow replay evidence packets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Sequence


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from algotrader.core.types import Bar  # noqa: E402
from algotrader.errors import ValidationError  # noqa: E402
from algotrader.orchestration.strategy_adapter_registry import (  # noqa: E402
    resolve_strategy_route_adapter,
)
from algotrader.orchestration.strategy_router import (  # noqa: E402
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
    route_strategy_signals,
    strategy_signal_from_etf_sma_result,
    strategy_signal_from_spy_rsi_mean_reversion_result,
)
from algotrader.research.local_daily_bars import (  # noqa: E402
    LocalDailyBar,
    load_local_daily_bars_csv,
)
from algotrader.research.strategy_router_shadow_conflict_classifier import (  # noqa: E402
    classify_strategy_router_shadow_replay_rows,
)
from algotrader.signals.etf_sma_evaluator import (  # noqa: E402
    ETF_SMA_SIGNAL_LABELS,
    EtfSmaSignalResult,
)
from algotrader.signals.spy_rsi_mean_reversion import (  # noqa: E402
    SPY_RSI_MEAN_REVERSION_LABELS,
    SPYRsiMeanReversionSignalResult,
)


DEFAULT_DAILY_BARS_CSV = (
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
DEFAULT_OUTPUT_ROOT = "runs/strategy_router_shadow_replay/oos/latest"
DEFAULT_RUN_ID = "v3_7_strategy_router_shadow_oos_replay"
DEFAULT_RECENT_ROW_COUNT = 260
TRADING_DAYS_PER_YEAR = 252
THREE_YEAR_ROW_COUNT = TRADING_DAYS_PER_YEAR * 3
FIVE_YEAR_ROW_COUNT = TRADING_DAYS_PER_YEAR * 5

REPLAY_LABELS = (
    "paper_lab_only",
    "offline_only",
    "strategy_router_shadow_replay",
    "strategy_router_shadow_oos_replay",
    "accepted_adjusted_spy_daily_bars",
    "rsi_shadow_only_no_promotion",
    "not_live_authorized",
    "profit_claim=none",
)

RECOMMENDATION_BUCKETS = (
    "keep_shadow",
    "needs_oos_backtest",
    "needs_regime_review",
    "needs_threshold_review",
    "reject_candidate",
)

_RECORD_TYPE_ROW = "strategy_router_shadow_replay_row"
_RECORD_TYPE_WINDOW_SUMMARY = "strategy_router_shadow_oos_window_summary"
_RECORD_TYPE_SUMMARY = "strategy_router_shadow_oos_summary"
_SCHEMA_VERSION = "1"

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_RSI_LOOKBACK_WINDOW = 14
_RSI_OVERSOLD_THRESHOLD = Decimal("30")
_RSI_OVERBOUGHT_THRESHOLD = Decimal("70")
_SMA_SHORT_WINDOW = 50
_SMA_LONG_WINDOW = 200
_SPARSE_THRESHOLD_FREQUENCY = Decimal("0.01")
_NOISY_THRESHOLD_FREQUENCY = Decimal("0.35")

_SMA_NEXT_ACTION = (
    "m346_offline_etf_sma_signal_to_risk_execution_preview_bridge_no_broker_action"
)
_SMA_LIMITATIONS = (
    "signal evaluation only",
    "not live authorized",
    "not a profitability claim",
    "not risk approval",
    "not execution authority",
    "no broker action performed",
    "no submit allowed",
    "separate offline bridge milestone required before any downstream preview",
)
_RSI_NEXT_ACTION = "shadow_route_only_no_broker_action"
_RSI_LIMITATIONS = (
    "shadow signal evaluation only",
    "not live authorized",
    "not a profitability claim",
    "not risk approval",
    "not execution authority",
    "no broker action performed",
    "no submit allowed",
    "requires explicit future promotion before paper mutation eligibility",
)

_CONFLICT_BUCKETS = (
    "sma_risk_on_rsi_overbought_conflict",
    "sma_risk_off_rsi_oversold_conflict",
    "router_conflict_block",
)


@dataclass(frozen=True, slots=True)
class _WindowSlice:
    window_id: str
    description: str
    start_index: int
    end_index: int
    window_type: str

    @property
    def row_count(self) -> int:
        return self.end_index - self.start_index


@dataclass(frozen=True, slots=True)
class _RollingMetrics:
    short_sma: tuple[Decimal | None, ...]
    long_sma: tuple[Decimal | None, ...]
    latest_rsi: tuple[Decimal | None, ...]
    average_gain: tuple[Decimal | None, ...]
    average_loss: tuple[Decimal | None, ...]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-strategy-router-shadow-oos-replay",
        description=(
            "Generate local-only longer-window SMA50/200 plus RSI14 shadow replay "
            "evidence without threshold optimization."
        ),
    )
    parser.add_argument(
        "--daily-bars-csv",
        default=DEFAULT_DAILY_BARS_CSV,
        help="Existing strict local SPY adjusted daily-bars CSV.",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Ignored runtime artifact directory.",
    )
    parser.add_argument(
        "--run-id",
        default=DEFAULT_RUN_ID,
        help="Deterministic run identifier stored in artifacts.",
    )
    parser.add_argument(
        "--as-of-date",
        default=None,
        help="Optional ISO date limiting accepted bars before selecting windows.",
    )
    return parser


def build_strategy_router_shadow_oos_replay(
    *,
    daily_bars_csv: str | Path,
    as_of_date: str | date | datetime | None = None,
    run_id: str = DEFAULT_RUN_ID,
) -> dict[str, object]:
    """Build deterministic longer-window shadow replay summaries."""

    checked_run_id = _required_string(run_id, "run_id")
    csv_result = load_local_daily_bars_csv(
        daily_bars_csv,
        symbol="SPY",
        as_of=as_of_date,
    )
    source_bars = csv_result.usable_bars
    if len(source_bars) < DEFAULT_RECENT_ROW_COUNT:
        raise ValidationError(
            "daily_bars_csv must contain at least 260 usable SPY bars for v3.7 replay."
        )

    core_bars = tuple(_adjusted_core_bar(bar) for bar in source_bars)
    metrics = _rolling_metrics(core_bars)
    all_rows = tuple(
        _build_replay_row(
            run_id=checked_run_id,
            source_bar=bar,
            core_bar=core_bars[index],
            index=index,
            total_source_bar_count=len(source_bars),
            metrics=metrics,
        )
        for index, bar in enumerate(source_bars)
    )

    window_summaries: list[dict[str, object]] = []
    conflict_summaries: list[dict[str, object]] = []
    windows = _window_slices(len(source_bars))
    for window in windows:
        rows = all_rows[window.start_index : window.end_index]
        window_summary = _build_window_summary(
            run_id=checked_run_id,
            window=window,
            rows=rows,
            source_path=csv_result.path,
        )
        classification = classify_strategy_router_shadow_replay_rows(
            rows,
            source_replay_jsonl=f"in_memory:{window.window_id}",
        )
        conflict_summary = _build_conflict_summary_by_window(
            window=window,
            classification_summary=_mapping(
                classification["summary"],
                "classification.summary",
            ),
        )
        window_summaries.append(window_summary)
        conflict_summaries.append(conflict_summary)

    summary = _build_oos_summary(
        run_id=checked_run_id,
        daily_bars_csv=csv_result.path,
        source_total_row_count=csv_result.total_row_count,
        source_matching_symbol_row_count=csv_result.matching_symbol_row_count,
        source_usable_bar_count=csv_result.observed_usable_bars,
        source_ignored_wrong_symbol_row_count=csv_result.ignored_wrong_symbol_row_count,
        source_ignored_future_bar_count=csv_result.ignored_future_bar_count,
        windows=tuple(window_summaries),
        conflicts=tuple(conflict_summaries),
    )
    return {
        "summary": summary,
        "replay_summary_by_window": window_summaries,
        "conflict_summary_by_window": conflict_summaries,
    }


def write_strategy_router_shadow_oos_replay_artifacts(
    packet: Mapping[str, object],
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Path]:
    """Write v3.7 summary JSON, by-window JSONL files, and markdown brief."""

    summary = _mapping(packet.get("summary"), "summary")
    replay_summaries = _mapping_list(
        packet.get("replay_summary_by_window"),
        "replay_summary_by_window",
    )
    conflict_summaries = _mapping_list(
        packet.get("conflict_summary_by_window"),
        "conflict_summary_by_window",
    )
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    summary_path = root / "summary.json"
    replay_summary_path = root / "replay_summary_by_window.jsonl"
    conflict_summary_path = root / "conflict_summary_by_window.jsonl"
    brief_path = root / "brief.md"

    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    replay_summary_path.write_text(
        "".join(_compact_json(record) + "\n" for record in replay_summaries),
        encoding="utf-8",
    )
    conflict_summary_path.write_text(
        "".join(_compact_json(record) + "\n" for record in conflict_summaries),
        encoding="utf-8",
    )
    brief_path.write_text(render_strategy_router_shadow_oos_brief(summary), encoding="utf-8")

    return {
        "summary_json": summary_path,
        "replay_summary_by_window_jsonl": replay_summary_path,
        "conflict_summary_by_window_jsonl": conflict_summary_path,
        "brief_md": brief_path,
    }


def render_strategy_router_shadow_oos_brief(summary: Mapping[str, object]) -> str:
    """Render a compact operator-facing v3.7 OOS replay brief."""

    windows = _mapping_list(summary["windows"], "windows")
    lines = [
        "# v3.7 Strategy Router Shadow OOS Replay",
        "",
        f"run_id: {summary['run_id']}",
        f"classification_recommendation: {summary['classification_recommendation']}",
        f"evidence_classification: {summary['evidence_classification']}",
        f"overall_recommendation_bucket: {summary['overall_recommendation_bucket']}",
        "",
        "## Window Summary",
        "",
    ]
    for window in windows:
        threshold_review = _mapping(window["threshold_review"], "threshold_review")
        lines.extend(
            [
                f"### {window['window_id']}",
                "",
                f"- start_date: {window['start_date']}",
                f"- end_date: {window['end_date']}",
                f"- row_count: {window['row_count']}",
                f"- sma_counts: {json.dumps(window['sma_counts'], sort_keys=True)}",
                f"- rsi_counts: {json.dumps(window['rsi_counts'], sort_keys=True)}",
                f"- conflict_count: {window['conflict_count']}",
                f"- shadow_blocked_count: {window['shadow_blocked_count']}",
                f"- candidate_disagreement_count: {window['candidate_disagreement_count']}",
                f"- rsi_mutation_eligible_count: {window['rsi_mutation_eligible_count']}",
                (
                    "- fixed_threshold_trigger_frequency: "
                    f"{threshold_review['fixed_threshold_trigger_frequency']}"
                ),
                f"- recommendation_bucket: {window['recommendation_bucket']}",
                "",
            ]
        )

    threshold_policy = _mapping(summary["threshold_policy"], "threshold_policy")
    lines.extend(
        [
            "## Threshold Review",
            "",
            f"- review_type: {threshold_policy['review_type']}",
            f"- rsi_lookback_window: {threshold_policy['rsi_lookback_window']}",
            f"- oversold_threshold: {threshold_policy['oversold_threshold']}",
            f"- overbought_threshold: {threshold_policy['overbought_threshold']}",
            (
                "- optimization_performed: "
                f"{str(threshold_policy['optimization_performed']).lower()}"
            ),
            (
                "- parameter_search_performed: "
                f"{str(threshold_policy['parameter_search_performed']).lower()}"
            ),
            "",
            "## Safety",
            "",
            f"- rsi_promotion_status: {summary['rsi_promotion_status']}",
            f"- rsi_mutation_eligibility: {str(summary['rsi_mutation_eligibility']).lower()}",
            f"- strategy_promotion_performed: {str(summary['strategy_promotion_performed']).lower()}",
            f"- broker_read_performed: {str(summary['broker_read_performed']).lower()}",
            f"- broker_mutation_performed: {str(summary['broker_mutation_performed']).lower()}",
            f"- paper_submit_performed: {str(summary['paper_submit_performed']).lower()}",
            f"- live_endpoint_used: {str(summary['live_endpoint_used']).lower()}",
            f"- network_fetch_performed: {str(summary['network_fetch_performed']).lower()}",
            f"- profit_claim: {summary['profit_claim']}",
            "",
            (
                "RSI remains shadow_only and mutation-ineligible. This packet reports "
                "fixed-threshold trigger frequency only; it does not optimize thresholds, "
                "tune period length, or claim profitability."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        packet = build_strategy_router_shadow_oos_replay(
            daily_bars_csv=args.daily_bars_csv,
            as_of_date=args.as_of_date,
            run_id=args.run_id,
        )
        paths = write_strategy_router_shadow_oos_replay_artifacts(
            packet,
            args.output_root,
        )
    except ValidationError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    summary = _mapping(packet["summary"], "summary")
    print(f"replay_status={summary['replay_status']}")
    print(f"window_count={summary['window_count']}")
    print(f"overall_recommendation_bucket={summary['overall_recommendation_bucket']}")
    print(f"rsi_mutation_eligible_count={summary['rsi_mutation_eligible_count']}")
    for name, path in paths.items():
        print(f"{name}={path.as_posix()}")
    return 0


def _build_replay_row(
    *,
    run_id: str,
    source_bar: LocalDailyBar,
    core_bar: Bar,
    index: int,
    total_source_bar_count: int,
    metrics: _RollingMetrics,
) -> dict[str, object]:
    as_of = datetime.combine(source_bar.date, time.min, tzinfo=UTC)
    usable_bar_count = index + 1
    sma_result = _sma_result(
        as_of=as_of,
        latest_close=core_bar.close,
        short_sma=metrics.short_sma[index],
        long_sma=metrics.long_sma[index],
        total_source_bar_count=total_source_bar_count,
        usable_bar_count=usable_bar_count,
    )
    rsi_result = _rsi_result(
        as_of=as_of,
        latest_close=core_bar.close,
        latest_rsi=metrics.latest_rsi[index],
        average_gain=metrics.average_gain[index],
        average_loss=metrics.average_loss[index],
        total_source_bar_count=total_source_bar_count,
        usable_bar_count=usable_bar_count,
    )
    sma_signal = strategy_signal_from_etf_sma_result(sma_result)
    rsi_signal = strategy_signal_from_spy_rsi_mean_reversion_result(rsi_result)
    route_receipt = route_strategy_signals((sma_signal, rsi_signal))
    adapter_resolution = resolve_strategy_route_adapter(route_receipt)

    rsi_shadow_blocker = (
        f"{SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID}:"
        "promotion_status_not_paper_mutation_candidate:shadow_only"
    )
    candidate_disagreement = _candidate_disagreement(sma_signal, rsi_signal)
    candidate_conflict = _candidate_conflict(sma_signal, rsi_signal)
    rsi_shadow_blocked = rsi_shadow_blocker in route_receipt.blockers
    final_mutation_eligibility = adapter_resolution.paper_mutation_allowed

    return {
        "record_type": _RECORD_TYPE_ROW,
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "data_as_of": as_of.isoformat(),
        "source_adjusted_close": _decimal_text(source_bar.adjusted_close),
        "sma_strategy": _sma_strategy_payload(sma_result, sma_signal.to_dict()),
        "rsi_strategy": _rsi_strategy_payload(rsi_result, rsi_signal.to_dict()),
        "router_decision": route_receipt.to_dict(),
        "adapter_resolution": adapter_resolution.to_dict(),
        "candidate_disagreement": candidate_disagreement,
        "candidate_conflict": candidate_conflict,
        "rsi_shadow_blocked_from_mutation": rsi_shadow_blocked,
        "final_mutation_eligibility": final_mutation_eligibility,
        "labels": list(REPLAY_LABELS),
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }


def _build_window_summary(
    *,
    run_id: str,
    window: _WindowSlice,
    rows: tuple[Mapping[str, object], ...],
    source_path: Path,
) -> dict[str, object]:
    if not rows:
        raise ValidationError(f"window {window.window_id} must contain at least one row.")

    sma_counts = {"risk_on": 0, "risk_off": 0, "no_action": 0}
    rsi_counts = {"oversold": 0, "overbought": 0, "neutral": 0, "insufficient": 0}
    route_reason_counts: Counter[str] = Counter()
    final_mutation_eligible_count = 0
    rsi_mutation_eligible_count = 0
    shadow_blocked_count = 0
    candidate_disagreement_count = 0
    conflict_count = 0
    representative_conflict_dates: list[str] = []
    representative_shadow_blocked_dates: list[str] = []

    for row in rows:
        sma_strategy = _mapping(row["sma_strategy"], "sma_strategy")
        rsi_strategy = _mapping(row["rsi_strategy"], "rsi_strategy")
        router_decision = _mapping(row["router_decision"], "router_decision")
        sma_counts[_sma_count_key(str(sma_strategy["posture"]))] += 1
        rsi_counts[_rsi_count_key(str(rsi_strategy["posture"]))] += 1
        route_reason_counts[str(router_decision["reason"])] += 1

        if row["final_mutation_eligibility"] is True:
            final_mutation_eligible_count += 1
        if row["rsi_shadow_blocked_from_mutation"] is True:
            shadow_blocked_count += 1
            if len(representative_shadow_blocked_dates) < 5:
                representative_shadow_blocked_dates.append(str(row["data_as_of"])[:10])
        if row["candidate_disagreement"] is True:
            candidate_disagreement_count += 1
        if row["candidate_conflict"] is True:
            conflict_count += 1
            if len(representative_conflict_dates) < 5:
                representative_conflict_dates.append(str(row["data_as_of"])[:10])

        rsi_mutation_eligible = (
            str(rsi_strategy["promotion_status"]) == "paper_mutation_candidate"
            and row["rsi_shadow_blocked_from_mutation"] is False
        )
        if rsi_mutation_eligible:
            rsi_mutation_eligible_count += 1

    if rsi_mutation_eligible_count != 0:
        raise ValidationError("RSI shadow rows must remain mutation-ineligible.")

    threshold_review = _threshold_frequency_review(
        row_count=len(rows),
        oversold_count=rsi_counts["oversold"],
        overbought_count=rsi_counts["overbought"],
    )
    recommendation_bucket = _window_recommendation_bucket(
        conflict_count=conflict_count,
        shadow_blocked_count=shadow_blocked_count,
        threshold_review=threshold_review,
    )

    return {
        "record_type": _RECORD_TYPE_WINDOW_SUMMARY,
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "window_id": window.window_id,
        "window_type": window.window_type,
        "description": window.description,
        "start_date": str(rows[0]["data_as_of"])[:10],
        "end_date": str(rows[-1]["data_as_of"])[:10],
        "row_count": len(rows),
        "sma_counts": sma_counts,
        "sma_risk_on_count": sma_counts["risk_on"],
        "sma_risk_off_count": sma_counts["risk_off"],
        "sma_no_action_count": sma_counts["no_action"],
        "rsi_counts": rsi_counts,
        "rsi_oversold_count": rsi_counts["oversold"],
        "rsi_overbought_count": rsi_counts["overbought"],
        "rsi_neutral_count": rsi_counts["neutral"],
        "rsi_insufficient_count": rsi_counts["insufficient"],
        "conflict_count": conflict_count,
        "shadow_blocked_count": shadow_blocked_count,
        "candidate_disagreement_count": candidate_disagreement_count,
        "final_mutation_eligible_count": final_mutation_eligible_count,
        "rsi_mutation_eligible_count": rsi_mutation_eligible_count,
        "rsi_promotion_status": "shadow_only",
        "rsi_mutation_eligibility": False,
        "representative_conflict_dates": representative_conflict_dates,
        "representative_shadow_blocked_dates": representative_shadow_blocked_dates,
        "route_reason_counts": dict(sorted(route_reason_counts.items())),
        "threshold_review": threshold_review,
        "recommendation_bucket": recommendation_bucket,
        "recommendation_buckets_allowed": list(RECOMMENDATION_BUCKETS),
        "source_data": {
            "type": "local_daily_bars_csv",
            "basis": "accepted_adjusted_close",
            "path": str(source_path),
            "symbol": "SPY",
        },
        "labels": list(REPLAY_LABELS),
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }


def _build_conflict_summary_by_window(
    *,
    window: _WindowSlice,
    classification_summary: Mapping[str, object],
) -> dict[str, object]:
    bucket_counts = _mapping(classification_summary["bucket_counts"], "bucket_counts")
    bucket_dates = _mapping(
        classification_summary["bucket_representative_dates"],
        "bucket_representative_dates",
    )
    conflict_counts = {
        bucket: bucket_counts.get(bucket, 0)
        for bucket in _CONFLICT_BUCKETS
    }
    representative_dates = {
        bucket: bucket_dates.get(bucket, [])
        for bucket in _CONFLICT_BUCKETS
    }
    return {
        "record_type": "strategy_router_shadow_oos_conflict_summary",
        "schema_version": _SCHEMA_VERSION,
        "run_id": classification_summary["run_id"],
        "window_id": window.window_id,
        "window_type": window.window_type,
        "start_date": classification_summary["replay_start_date"],
        "end_date": classification_summary["replay_end_date"],
        "row_count": classification_summary["row_count"],
        "conflict_count": classification_summary["conflict_row_count"],
        "shadow_blocked_count": classification_summary["shadow_blocked_row_count"],
        "candidate_disagreement_bucket_count": bucket_counts.get(
            "rsi_neutral_sma_active_disagreement",
            0,
        ),
        "rsi_shadow_mutation_eligible_count": classification_summary[
            "rsi_shadow_mutation_eligible_count"
        ],
        "conflict_counts": conflict_counts,
        "representative_conflict_dates": representative_dates,
        "bucket_counts": bucket_counts,
        "primary_bucket_counts": classification_summary["primary_bucket_counts"],
        "classification_recommendation": classification_summary[
            "classification_recommendation"
        ],
        "secondary_recommendations": classification_summary[
            "secondary_recommendations"
        ],
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }


def _build_oos_summary(
    *,
    run_id: str,
    daily_bars_csv: Path,
    source_total_row_count: int,
    source_matching_symbol_row_count: int,
    source_usable_bar_count: int,
    source_ignored_wrong_symbol_row_count: int,
    source_ignored_future_bar_count: int,
    windows: tuple[Mapping[str, object], ...],
    conflicts: tuple[Mapping[str, object], ...],
) -> dict[str, object]:
    recommendation_counts = Counter(str(window["recommendation_bucket"]) for window in windows)
    overall_recommendation_bucket = _overall_recommendation_bucket(recommendation_counts)
    rsi_mutation_eligible_count = sum(
        int(window["rsi_mutation_eligible_count"]) for window in windows
    )
    if rsi_mutation_eligible_count != 0:
        raise ValidationError("RSI must remain mutation-ineligible in all windows.")

    return {
        "record_type": _RECORD_TYPE_SUMMARY,
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "replay_status": "complete",
        "classification_recommendation": "keep_rsi_shadow_only",
        "overall_recommendation_bucket": overall_recommendation_bucket,
        "recommendation_bucket_counts": dict(sorted(recommendation_counts.items())),
        "evidence_classification": "decision_quality_evidence_and_architecture_capability",
        "architecture_capability": True,
        "process_overhead": False,
        "window_count": len(windows),
        "windows": list(windows),
        "conflict_summaries": list(conflicts),
        "source_data": {
            "type": "local_daily_bars_csv",
            "basis": "accepted_adjusted_close",
            "path": str(daily_bars_csv),
            "symbol": "SPY",
            "total_row_count": source_total_row_count,
            "matching_symbol_row_count": source_matching_symbol_row_count,
            "usable_bar_count": source_usable_bar_count,
            "ignored_wrong_symbol_row_count": source_ignored_wrong_symbol_row_count,
            "ignored_future_bar_count": source_ignored_future_bar_count,
        },
        "threshold_policy": _threshold_policy(),
        "rsi_promotion_status": "shadow_only",
        "rsi_mutation_eligibility": False,
        "rsi_mutation_eligible_count": rsi_mutation_eligible_count,
        "strategy_promotion_performed": False,
        "threshold_change_performed": False,
        "threshold_optimization_performed": False,
        "parameter_search_performed": False,
        "labels": list(REPLAY_LABELS),
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }


def _window_slices(source_row_count: int) -> tuple[_WindowSlice, ...]:
    windows = [
        _WindowSlice(
            window_id="recent_260",
            description="Most recent 260 accepted SPY adjusted daily bars",
            start_index=source_row_count - DEFAULT_RECENT_ROW_COUNT,
            end_index=source_row_count,
            window_type="trailing_bar_count",
        )
    ]
    if source_row_count >= THREE_YEAR_ROW_COUNT:
        windows.append(
            _WindowSlice(
                window_id="trailing_3_years",
                description="Most recent 756 accepted bars, approximately 3 trading years",
                start_index=source_row_count - THREE_YEAR_ROW_COUNT,
                end_index=source_row_count,
                window_type="trailing_trading_years",
            )
        )
    if source_row_count >= FIVE_YEAR_ROW_COUNT:
        windows.append(
            _WindowSlice(
                window_id="trailing_5_years",
                description="Most recent 1260 accepted bars, approximately 5 trading years",
                start_index=source_row_count - FIVE_YEAR_ROW_COUNT,
                end_index=source_row_count,
                window_type="trailing_trading_years",
            )
        )
    windows.append(
        _WindowSlice(
            window_id="full_available",
            description="Full available accepted SPY adjusted daily bars",
            start_index=0,
            end_index=source_row_count,
            window_type="full_available",
        )
    )
    if source_row_count >= DEFAULT_RECENT_ROW_COUNT * 2:
        split_index = source_row_count // 2
        windows.extend(
            (
                _WindowSlice(
                    window_id="chronological_earlier_half",
                    description="Earlier chronological half of accepted bars",
                    start_index=0,
                    end_index=split_index,
                    window_type="chronological_split",
                ),
                _WindowSlice(
                    window_id="chronological_later_half",
                    description="Later chronological half of accepted bars",
                    start_index=split_index,
                    end_index=source_row_count,
                    window_type="chronological_split",
                ),
            )
        )
    return tuple(windows)


def _rolling_metrics(core_bars: tuple[Bar, ...]) -> _RollingMetrics:
    closes = tuple(bar.close for bar in core_bars)
    short_sma = _rolling_sma(closes, _SMA_SHORT_WINDOW)
    long_sma = _rolling_sma(closes, _SMA_LONG_WINDOW)
    latest_rsi, average_gain, average_loss = _rolling_rsi(closes, _RSI_LOOKBACK_WINDOW)
    return _RollingMetrics(
        short_sma=short_sma,
        long_sma=long_sma,
        latest_rsi=latest_rsi,
        average_gain=average_gain,
        average_loss=average_loss,
    )


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
) -> tuple[
    tuple[Decimal | None, ...],
    tuple[Decimal | None, ...],
    tuple[Decimal | None, ...],
]:
    latest_rsi: list[Decimal | None] = []
    average_gain: list[Decimal | None] = []
    average_loss: list[Decimal | None] = []
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
            average_gain.append(None)
            average_loss.append(None)
            continue

        gain = running_gain / Decimal(lookback_window)
        loss = running_loss / Decimal(lookback_window)
        average_gain.append(gain)
        average_loss.append(loss)
        if gain == _ZERO and loss == _ZERO:
            latest_rsi.append(Decimal("50"))
        elif loss == _ZERO:
            latest_rsi.append(_HUNDRED)
        else:
            relative_strength = gain / loss
            latest_rsi.append(_HUNDRED - (_HUNDRED / (_ONE + relative_strength)))

    return tuple(latest_rsi), tuple(average_gain), tuple(average_loss)


def _sma_result(
    *,
    as_of: datetime,
    latest_close: Decimal,
    short_sma: Decimal | None,
    long_sma: Decimal | None,
    total_source_bar_count: int,
    usable_bar_count: int,
) -> EtfSmaSignalResult:
    if usable_bar_count < _SMA_LONG_WINDOW:
        posture = "insufficient_history"
    elif short_sma is not None and long_sma is not None and short_sma > long_sma:
        posture = "bullish_risk_on"
    else:
        posture = "defensive_risk_off"
    return EtfSmaSignalResult(
        symbol="SPY",
        asset_class="equity",
        strategy_type="long_only_broad_etf_sma_trend_filter",
        timeframe="daily",
        as_of=as_of,
        short_window=_SMA_SHORT_WINDOW,
        long_window=_SMA_LONG_WINDOW,
        total_bar_count=total_source_bar_count,
        usable_bar_count=usable_bar_count,
        ignored_future_bar_count=total_source_bar_count - usable_bar_count,
        latest_close=latest_close,
        short_sma=short_sma,
        long_sma=long_sma,
        posture=posture,
        labels=ETF_SMA_SIGNAL_LABELS,
        profit_claim="none",
        broker_action_performed=False,
        submit_allowed=False,
        next_action=_SMA_NEXT_ACTION,
        limitations=_SMA_LIMITATIONS,
    )


def _rsi_result(
    *,
    as_of: datetime,
    latest_close: Decimal,
    latest_rsi: Decimal | None,
    average_gain: Decimal | None,
    average_loss: Decimal | None,
    total_source_bar_count: int,
    usable_bar_count: int,
) -> SPYRsiMeanReversionSignalResult:
    if usable_bar_count < _RSI_LOOKBACK_WINDOW + 1:
        posture = "insufficient_history"
        blockers = ("insufficient_history",)
    elif latest_rsi is not None and latest_rsi <= _RSI_OVERSOLD_THRESHOLD:
        posture = "oversold_buy_candidate"
        blockers = ()
    elif latest_rsi is not None and latest_rsi >= _RSI_OVERBOUGHT_THRESHOLD:
        posture = "overbought_cash_candidate"
        blockers = ()
    else:
        posture = "neutral_no_trade"
        blockers = ()
    return SPYRsiMeanReversionSignalResult(
        symbol="SPY",
        asset_class="equity",
        strategy_type="mean_reversion",
        timeframe="daily",
        as_of=as_of,
        lookback_window=_RSI_LOOKBACK_WINDOW,
        oversold_threshold=_RSI_OVERSOLD_THRESHOLD,
        overbought_threshold=_RSI_OVERBOUGHT_THRESHOLD,
        total_bar_count=total_source_bar_count,
        usable_bar_count=usable_bar_count,
        ignored_future_bar_count=total_source_bar_count - usable_bar_count,
        latest_close=latest_close,
        latest_rsi=latest_rsi,
        average_gain=average_gain,
        average_loss=average_loss,
        posture=posture,
        labels=SPY_RSI_MEAN_REVERSION_LABELS,
        blockers=blockers,
        profit_claim="none",
        broker_action_performed=False,
        submit_allowed=False,
        next_action=_RSI_NEXT_ACTION,
        limitations=_RSI_LIMITATIONS,
    )


def _sma_strategy_payload(
    result: EtfSmaSignalResult,
    signal_payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        "strategy_id": signal_payload["strategy_id"],
        "strategy_family": signal_payload["strategy_family"],
        "symbol": signal_payload["symbol"],
        "posture": result.posture,
        "state": signal_payload["signal_state"],
        "signal_state": signal_payload["signal_state"],
        "intended_action": signal_payload["intended_action"],
        "intended_side": signal_payload["intended_side"],
        "promotion_status": signal_payload["promotion_status"],
        "usable_bar_count": result.usable_bar_count,
        "latest_close": _decimal_text(result.latest_close),
        "short_sma": _decimal_text(result.short_sma),
        "long_sma": _decimal_text(result.long_sma),
        "labels": signal_payload["labels"],
        "blockers": signal_payload["blockers"],
    }


def _rsi_strategy_payload(
    result: SPYRsiMeanReversionSignalResult,
    signal_payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        "strategy_id": signal_payload["strategy_id"],
        "strategy_family": signal_payload["strategy_family"],
        "symbol": signal_payload["symbol"],
        "posture": result.posture,
        "state": signal_payload["signal_state"],
        "signal_state": signal_payload["signal_state"],
        "intended_action": signal_payload["intended_action"],
        "intended_side": signal_payload["intended_side"],
        "promotion_status": signal_payload["promotion_status"],
        "usable_bar_count": result.usable_bar_count,
        "latest_close": _decimal_text(result.latest_close),
        "latest_rsi": _decimal_text(result.latest_rsi),
        "average_gain": _decimal_text(result.average_gain),
        "average_loss": _decimal_text(result.average_loss),
        "labels": signal_payload["labels"],
        "blockers": signal_payload["blockers"],
        "submit_allowed": result.submit_allowed,
        "broker_action_performed": result.broker_action_performed,
    }


def _threshold_frequency_review(
    *,
    row_count: int,
    oversold_count: int,
    overbought_count: int,
) -> dict[str, object]:
    trigger_count = oversold_count + overbought_count
    frequency = Decimal(trigger_count) / Decimal(row_count)
    if trigger_count == 0 or frequency < _SPARSE_THRESHOLD_FREQUENCY:
        frequency_status = "too_sparse_future_review_only"
        future_review_recommended = True
    elif frequency > _NOISY_THRESHOLD_FREQUENCY:
        frequency_status = "too_noisy_future_review_only"
        future_review_recommended = True
    else:
        frequency_status = "observed_without_review_trigger"
        future_review_recommended = False
    return {
        "review_type": "fixed_threshold_frequency_only",
        "rsi_lookback_window": _RSI_LOOKBACK_WINDOW,
        "oversold_threshold": _decimal_text(_RSI_OVERSOLD_THRESHOLD),
        "overbought_threshold": _decimal_text(_RSI_OVERBOUGHT_THRESHOLD),
        "thresholds_evaluated": {
            "oversold": [_decimal_text(_RSI_OVERSOLD_THRESHOLD)],
            "overbought": [_decimal_text(_RSI_OVERBOUGHT_THRESHOLD)],
        },
        "trigger_count": trigger_count,
        "oversold_count": oversold_count,
        "overbought_count": overbought_count,
        "fixed_threshold_trigger_frequency": _ratio_text(frequency),
        "frequency_status": frequency_status,
        "future_threshold_review_recommended": future_review_recommended,
        "optimization_performed": False,
        "parameter_search_performed": False,
        "rsi_period_tuning_performed": False,
        "profit_claim": "none",
    }


def _threshold_policy() -> dict[str, object]:
    return {
        "review_type": "fixed_threshold_frequency_only",
        "rsi_lookback_window": _RSI_LOOKBACK_WINDOW,
        "oversold_threshold": _decimal_text(_RSI_OVERSOLD_THRESHOLD),
        "overbought_threshold": _decimal_text(_RSI_OVERBOUGHT_THRESHOLD),
        "thresholds_evaluated": {
            "oversold": [_decimal_text(_RSI_OVERSOLD_THRESHOLD)],
            "overbought": [_decimal_text(_RSI_OVERBOUGHT_THRESHOLD)],
        },
        "optimization_performed": False,
        "parameter_search_performed": False,
        "rsi_period_tuning_performed": False,
        "threshold_change_performed": False,
        "profit_claim": "none",
    }


def _window_recommendation_bucket(
    *,
    conflict_count: int,
    shadow_blocked_count: int,
    threshold_review: Mapping[str, object],
) -> str:
    if conflict_count > 0 or shadow_blocked_count > 0:
        return "needs_oos_backtest"
    if threshold_review["future_threshold_review_recommended"] is True:
        return "needs_threshold_review"
    return "keep_shadow"


def _overall_recommendation_bucket(counts: Counter[str]) -> str:
    for bucket in (
        "reject_candidate",
        "needs_oos_backtest",
        "needs_regime_review",
        "needs_threshold_review",
    ):
        if counts.get(bucket, 0) > 0:
            return bucket
    return "keep_shadow"


def _adjusted_core_bar(bar: LocalDailyBar) -> Bar:
    adjusted_close = bar.adjusted_close
    return Bar(
        symbol=bar.symbol,
        timestamp=datetime.combine(bar.date, time.min, tzinfo=UTC),
        open=adjusted_close,
        high=adjusted_close,
        low=adjusted_close,
        close=adjusted_close,
        volume=Decimal(bar.volume),
    )


def _candidate_disagreement(first: object, second: object) -> bool:
    return (
        getattr(first, "signal_state"),
        getattr(first, "intended_action"),
        getattr(first, "intended_side"),
    ) != (
        getattr(second, "signal_state"),
        getattr(second, "intended_action"),
        getattr(second, "intended_side"),
    )


def _candidate_conflict(first: object, second: object) -> bool:
    if getattr(first, "signal_state") != "trade_candidate":
        return False
    if getattr(second, "signal_state") != "trade_candidate":
        return False
    return (
        getattr(first, "symbol"),
        getattr(first, "intended_action"),
        getattr(first, "intended_side"),
    ) != (
        getattr(second, "symbol"),
        getattr(second, "intended_action"),
        getattr(second, "intended_side"),
    )


def _sma_count_key(posture: str) -> str:
    if posture == "bullish_risk_on":
        return "risk_on"
    if posture == "defensive_risk_off":
        return "risk_off"
    if posture == "insufficient_history":
        return "no_action"
    raise ValidationError(f"unsupported SMA posture: {posture}")


def _rsi_count_key(posture: str) -> str:
    if posture == "oversold_buy_candidate":
        return "oversold"
    if posture == "overbought_cash_candidate":
        return "overbought"
    if posture == "neutral_no_trade":
        return "neutral"
    if posture == "insufficient_history":
        return "insufficient"
    raise ValidationError(f"unsupported RSI posture: {posture}")


def _mapping_list(value: object, field_name: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list.")
    return [_mapping(item, f"{field_name}[]") for item in value]


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _ratio_text(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


def _compact_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(main())
