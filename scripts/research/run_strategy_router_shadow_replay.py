"""Generate offline SMA/RSI shadow replay evidence for the strategy router."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
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
from algotrader.signals.etf_sma_evaluator import (  # noqa: E402
    EtfSmaSignalConfig,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)
from algotrader.signals.spy_rsi_mean_reversion import (  # noqa: E402
    SPYRsiMeanReversionSignalConfig,
    SPYRsiMeanReversionSignalResult,
    evaluate_spy_rsi_mean_reversion_signal,
)


DEFAULT_DAILY_BARS_CSV = (
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
DEFAULT_OUTPUT_ROOT = "runs/strategy_router_shadow_replay/latest"
DEFAULT_RUN_ID = "v3_5_strategy_router_shadow_replay"
DEFAULT_REPLAY_ROW_COUNT = 260

REPLAY_LABELS = (
    "paper_lab_only",
    "offline_only",
    "strategy_router_shadow_replay",
    "accepted_adjusted_spy_daily_bars",
    "rsi_shadow_only_no_promotion",
    "not_live_authorized",
    "profit_claim=none",
)

_RECORD_TYPE_ROW = "strategy_router_shadow_replay_row"
_RECORD_TYPE_SUMMARY = "strategy_router_shadow_replay_summary"
_SCHEMA_VERSION = "1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run-strategy-router-shadow-replay",
        description=(
            "Generate local-only SMA50/200 plus RSI14 shadow router replay evidence."
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
        "--replay-row-count",
        type=int,
        default=DEFAULT_REPLAY_ROW_COUNT,
        help="Number of latest accepted SPY daily bars to replay.",
    )
    parser.add_argument(
        "--as-of-date",
        default=None,
        help="Optional ISO date limiting accepted bars before selecting the replay window.",
    )
    return parser


def build_strategy_router_shadow_replay(
    *,
    daily_bars_csv: str | Path,
    replay_row_count: int = DEFAULT_REPLAY_ROW_COUNT,
    as_of_date: str | date | datetime | None = None,
    run_id: str = DEFAULT_RUN_ID,
) -> dict[str, object]:
    """Build deterministic replay records and summary from local adjusted bars."""

    checked_run_id = _required_string(run_id, "run_id")
    checked_replay_row_count = _positive_int(replay_row_count, "replay_row_count")
    csv_result = load_local_daily_bars_csv(
        daily_bars_csv,
        symbol="SPY",
        as_of=as_of_date,
    )
    if not csv_result.usable_bars:
        raise ValidationError("daily_bars_csv must contain at least one usable SPY bar.")

    source_bars = csv_result.usable_bars
    replay_bars = source_bars[-checked_replay_row_count:]
    adjusted_core_bars = tuple(_adjusted_core_bar(bar) for bar in source_bars)

    rows = tuple(
        _build_replay_row(
            run_id=checked_run_id,
            replay_bar=bar,
            adjusted_core_bars=adjusted_core_bars,
        )
        for bar in replay_bars
    )
    summary = _build_summary(
        run_id=checked_run_id,
        daily_bars_csv=csv_result.path,
        source_total_row_count=csv_result.total_row_count,
        source_matching_symbol_row_count=csv_result.matching_symbol_row_count,
        source_usable_bar_count=csv_result.observed_usable_bars,
        source_ignored_wrong_symbol_row_count=csv_result.ignored_wrong_symbol_row_count,
        source_ignored_future_bar_count=csv_result.ignored_future_bar_count,
        rows=rows,
    )
    return {"records": list(rows), "summary": summary}


def write_strategy_router_shadow_replay_artifacts(
    replay: Mapping[str, object],
    output_root: str | Path,
) -> dict[str, Path]:
    """Write replay JSONL, summary JSON, and markdown brief artifacts."""

    records = _record_list(replay.get("records"))
    summary = _summary_mapping(replay.get("summary"))
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    replay_path = root / "replay.jsonl"
    summary_path = root / "summary.json"
    brief_path = root / "brief.md"

    replay_path.write_text(
        "".join(_compact_json(record) + "\n" for record in records),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    brief_path.write_text(render_strategy_router_shadow_replay_brief(summary), encoding="utf-8")

    return {
        "replay_jsonl": replay_path,
        "summary_json": summary_path,
        "brief_md": brief_path,
    }


def render_strategy_router_shadow_replay_brief(
    summary: Mapping[str, object],
) -> str:
    """Render the compact operator-facing markdown brief."""

    lines = [
        "# Strategy Router Shadow Replay Evidence Packet",
        "",
        f"run_id: {summary['run_id']}",
        f"classification_recommendation: {summary['classification_recommendation']}",
        f"evidence_classification: {summary['evidence_classification']}",
        "",
        "## Replay Summary",
        "",
        f"- replay_start_date: {summary['replay_start_date']}",
        f"- replay_end_date: {summary['replay_end_date']}",
        f"- row_count: {summary['row_count']}",
        f"- sma_counts: {json.dumps(summary['sma_counts'], sort_keys=True)}",
        f"- rsi_counts: {json.dumps(summary['rsi_counts'], sort_keys=True)}",
        f"- candidate_disagreement_count: {summary['candidate_disagreement_count']}",
        f"- conflict_count: {summary['conflict_count']}",
        f"- paper_mutation_eligible_count: {summary['paper_mutation_eligible_count']}",
        f"- shadow_blocked_count: {summary['shadow_blocked_count']}",
        "",
        "## Safety",
        "",
        f"- broker_read_performed: {str(summary['broker_read_performed']).lower()}",
        f"- broker_mutation_performed: {str(summary['broker_mutation_performed']).lower()}",
        f"- paper_submit_performed: {str(summary['paper_submit_performed']).lower()}",
        f"- live_endpoint_used: {str(summary['live_endpoint_used']).lower()}",
        f"- network_fetch_performed: {str(summary['network_fetch_performed']).lower()}",
        f"- profit_claim: {summary['profit_claim']}",
        "",
        "## Notes",
        "",
        (
            "This packet evaluates router behavior only. RSI remains shadow_only; "
            "the packet makes no profit or alpha claim and grants no paper or live "
            "trading authority."
        ),
        "",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        replay = build_strategy_router_shadow_replay(
            daily_bars_csv=args.daily_bars_csv,
            replay_row_count=args.replay_row_count,
            as_of_date=args.as_of_date,
            run_id=args.run_id,
        )
        paths = write_strategy_router_shadow_replay_artifacts(
            replay,
            args.output_root,
        )
    except ValidationError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2

    summary = _summary_mapping(replay["summary"])
    print(f"replay_status={summary['replay_status']}")
    print(f"row_count={summary['row_count']}")
    print(f"paper_mutation_eligible_count={summary['paper_mutation_eligible_count']}")
    print(f"shadow_blocked_count={summary['shadow_blocked_count']}")
    for name, path in paths.items():
        print(f"{name}={path.as_posix()}")
    return 0


def _build_replay_row(
    *,
    run_id: str,
    replay_bar: LocalDailyBar,
    adjusted_core_bars: tuple[Bar, ...],
) -> dict[str, object]:
    as_of = datetime.combine(replay_bar.date, time.min, tzinfo=UTC)
    sma_result = evaluate_etf_sma_signal(
        adjusted_core_bars,
        EtfSmaSignalConfig(as_of=as_of, symbol="SPY"),
    )
    rsi_result = evaluate_spy_rsi_mean_reversion_signal(
        adjusted_core_bars,
        SPYRsiMeanReversionSignalConfig(as_of=as_of),
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
        "source_adjusted_close": _decimal_text(replay_bar.adjusted_close),
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


def _build_summary(
    *,
    run_id: str,
    daily_bars_csv: Path,
    source_total_row_count: int,
    source_matching_symbol_row_count: int,
    source_usable_bar_count: int,
    source_ignored_wrong_symbol_row_count: int,
    source_ignored_future_bar_count: int,
    rows: tuple[Mapping[str, object], ...],
) -> dict[str, object]:
    if not rows:
        raise ValidationError("replay must contain at least one row.")

    sma_counts = {"risk_on": 0, "risk_off": 0, "no_action": 0}
    rsi_counts = {"oversold": 0, "overbought": 0, "neutral": 0, "insufficient": 0}
    route_reason_counts: dict[str, int] = {}

    for row in rows:
        sma_strategy = _mapping(row["sma_strategy"], "sma_strategy")
        rsi_strategy = _mapping(row["rsi_strategy"], "rsi_strategy")
        router_decision = _mapping(row["router_decision"], "router_decision")
        sma_counts[_sma_count_key(str(sma_strategy["posture"]))] += 1
        rsi_counts[_rsi_count_key(str(rsi_strategy["posture"]))] += 1
        reason = str(router_decision["reason"])
        route_reason_counts[reason] = route_reason_counts.get(reason, 0) + 1

    start = str(rows[0]["data_as_of"])[:10]
    end = str(rows[-1]["data_as_of"])[:10]
    candidate_disagreement_count = sum(
        1 for row in rows if row["candidate_disagreement"] is True
    )
    conflict_count = sum(1 for row in rows if row["candidate_conflict"] is True)
    paper_mutation_eligible_count = sum(
        1 for row in rows if row["final_mutation_eligibility"] is True
    )
    shadow_blocked_count = sum(
        1 for row in rows if row["rsi_shadow_blocked_from_mutation"] is True
    )

    return {
        "record_type": _RECORD_TYPE_SUMMARY,
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "replay_status": "complete",
        "classification_recommendation": "keep_rsi_shadow_only",
        "evidence_classification": "decision_quality_evidence_and_architecture_capability",
        "replay_start_date": start,
        "replay_end_date": end,
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
        "candidate_disagreement_count": candidate_disagreement_count,
        "conflict_count": conflict_count,
        "paper_mutation_eligible_count": paper_mutation_eligible_count,
        "shadow_blocked_count": shadow_blocked_count,
        "route_reason_counts": route_reason_counts,
        "strategy_ids": [
            SMA_TRAINING_WHEEL_STRATEGY_ID,
            SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
        ],
        "labels": list(REPLAY_LABELS),
        "profit_claim": "none",
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
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
        "rsi_promotion_status": "shadow_only",
        "rsi_mutation_eligibility": False,
    }


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


def _record_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError("records must be a list.")
    return [_mapping(item, "records[]") for item in value]


def _summary_mapping(value: object) -> Mapping[str, object]:
    return _mapping(value, "summary")


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _compact_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(main())
