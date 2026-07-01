"""Deterministic diagnostics for strategy-router shadow replay packets."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


DEFAULT_REPLAY_JSONL = Path("runs/strategy_router_shadow_replay/latest/replay.jsonl")
DEFAULT_OUTPUT_ROOT = Path("runs/strategy_router_shadow_replay/latest")

CLASSIFIER_SCHEMA_VERSION = "1"
REPLAY_ROW_RECORD_TYPE = "strategy_router_shadow_replay_row"
CLASSIFICATION_ROW_RECORD_TYPE = "strategy_router_shadow_conflict_classification_row"
CLASSIFICATION_SUMMARY_RECORD_TYPE = (
    "strategy_router_shadow_conflict_classification_summary"
)

BUCKETS = (
    "sma_risk_on_rsi_overbought_conflict",
    "sma_risk_off_rsi_oversold_conflict",
    "rsi_shadow_trade_candidate_blocked",
    "rsi_neutral_sma_active_disagreement",
    "router_conflict_block",
    "adapter_registry_shadow_block",
    "no_action_alignment",
    "other_router_observation",
)

RECOMMENDATION_CATEGORIES = (
    "keep_shadow",
    "needs_longer_replay",
    "needs_oos_backtest",
    "needs_threshold_review",
    "reject_candidate",
)

_SAFETY_FALSE_FIELDS = (
    "broker_read_performed",
    "broker_mutation_performed",
    "paper_submit_performed",
    "live_endpoint_used",
    "network_fetch_performed",
)

_CONFLICT_BUCKETS = (
    "sma_risk_on_rsi_overbought_conflict",
    "sma_risk_off_rsi_oversold_conflict",
    "router_conflict_block",
)

_SHADOW_BLOCK_BUCKETS = (
    "rsi_shadow_trade_candidate_blocked",
    "adapter_registry_shadow_block",
)

_PRIMARY_BUCKET_ORDER = (
    "sma_risk_on_rsi_overbought_conflict",
    "sma_risk_off_rsi_oversold_conflict",
    "router_conflict_block",
    "rsi_shadow_trade_candidate_blocked",
    "rsi_neutral_sma_active_disagreement",
    "adapter_registry_shadow_block",
    "no_action_alignment",
)


def build_strategy_router_shadow_conflict_classification(
    replay_jsonl: str | Path = DEFAULT_REPLAY_JSONL,
) -> dict[str, object]:
    """Read a replay JSONL packet and return deterministic classifications."""

    path = _local_path(replay_jsonl, "replay_jsonl")
    rows = read_strategy_router_shadow_replay_rows(path)
    return classify_strategy_router_shadow_replay_rows(
        rows,
        source_replay_jsonl=path,
    )


def read_strategy_router_shadow_replay_rows(
    replay_jsonl: str | Path = DEFAULT_REPLAY_JSONL,
) -> tuple[Mapping[str, object], ...]:
    """Read and validate replay rows from a local JSONL artifact."""

    path = _local_path(replay_jsonl, "replay_jsonl")
    if not path.exists():
        raise ValidationError(f"replay_jsonl does not exist: {path}")
    if not path.is_file():
        raise ValidationError(f"replay_jsonl must be a file: {path}")

    rows: list[Mapping[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except JSONDecodeError as exc:
            raise ValidationError(
                f"replay_jsonl line {line_number} must be valid JSON."
            ) from exc
        row = _mapping(payload, f"replay_jsonl line {line_number}")
        _validate_replay_row(row, line_number=line_number)
        rows.append(row)

    if not rows:
        raise ValidationError("replay_jsonl must contain at least one replay row.")
    return tuple(rows)


def classify_strategy_router_shadow_replay_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    source_replay_jsonl: str | Path | None = None,
) -> dict[str, object]:
    """Classify replay rows into deterministic conflict and shadow-block buckets."""

    checked_rows = tuple(_mapping(row, "rows[]") for row in rows)
    if not checked_rows:
        raise ValidationError("rows must contain at least one replay row.")

    classified_rows = tuple(
        _classify_replay_row(row, row_number=index)
        for index, row in enumerate(checked_rows, 1)
    )
    summary = _build_summary(
        classified_rows,
        source_replay_jsonl=source_replay_jsonl,
    )
    return {"records": list(classified_rows), "summary": summary}


def write_strategy_router_shadow_conflict_artifacts(
    classification: Mapping[str, object],
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Path]:
    """Write summary JSON, classified row JSONL, and markdown brief artifacts."""

    records = _record_list(classification.get("records"))
    summary = _mapping(classification.get("summary"), "summary")
    root = _local_path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)

    summary_path = root / "conflict_summary.json"
    rows_path = root / "conflict_rows.jsonl"
    brief_path = root / "conflict_brief.md"

    rows_path.write_text(
        "".join(_compact_json(record) + "\n" for record in records),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    brief_path.write_text(
        render_strategy_router_shadow_conflict_brief(summary),
        encoding="utf-8",
    )

    return {
        "conflict_summary_json": summary_path,
        "conflict_rows_jsonl": rows_path,
        "conflict_brief_md": brief_path,
    }


def render_strategy_router_shadow_conflict_brief(
    summary: Mapping[str, object],
) -> str:
    """Render the compact operator-facing conflict classifier brief."""

    bucket_counts = _mapping(summary["bucket_counts"], "bucket_counts")
    conflict_summary = _mapping(
        summary["conflict_bucket_summary"],
        "conflict_bucket_summary",
    )
    shadow_summary = _mapping(
        summary["shadow_blocked_bucket_summary"],
        "shadow_blocked_bucket_summary",
    )
    recommendations = _mapping(
        summary["recommendation_categories"],
        "recommendation_categories",
    )

    lines = [
        "# Strategy Router Shadow Conflict Classifier",
        "",
        f"run_id: {summary['run_id']}",
        f"source_replay_jsonl: {summary['source_replay_jsonl']}",
        f"classification_recommendation: {summary['classification_recommendation']}",
        f"evidence_classification: {summary['evidence_classification']}",
        "",
        "## Replay Diagnostics",
        "",
        f"- row_count: {summary['row_count']}",
        f"- replay_start_date: {summary['replay_start_date']}",
        f"- replay_end_date: {summary['replay_end_date']}",
        f"- conflict_row_count: {summary['conflict_row_count']}",
        f"- shadow_blocked_row_count: {summary['shadow_blocked_row_count']}",
        (
            "- rsi_shadow_mutation_eligible_count: "
            f"{summary['rsi_shadow_mutation_eligible_count']}"
        ),
        f"- bucket_counts: {json.dumps(bucket_counts, sort_keys=True)}",
        "",
        "## Conflict Buckets",
        "",
        *_render_bucket_lines(conflict_summary),
        "",
        "## Shadow-Blocked Buckets",
        "",
        *_render_bucket_lines(shadow_summary),
        "",
        "## Recommendation Categories",
        "",
        *_render_recommendation_lines(recommendations),
        "",
        "## Safety",
        "",
        f"- rsi_promotion_status: {summary['rsi_promotion_status']}",
        f"- rsi_mutation_eligibility: {str(summary['rsi_mutation_eligibility']).lower()}",
        f"- strategy_promotion_performed: {str(summary['strategy_promotion_performed']).lower()}",
        f"- threshold_change_performed: {str(summary['threshold_change_performed']).lower()}",
        f"- broker_read_performed: {str(summary['broker_read_performed']).lower()}",
        f"- broker_mutation_performed: {str(summary['broker_mutation_performed']).lower()}",
        f"- paper_submit_performed: {str(summary['paper_submit_performed']).lower()}",
        f"- live_endpoint_used: {str(summary['live_endpoint_used']).lower()}",
        f"- network_fetch_performed: {str(summary['network_fetch_performed']).lower()}",
        f"- profit_claim: {summary['profit_claim']}",
        "",
        (
            "This classifier is a deterministic diagnostic over an existing offline "
            "replay packet. It makes no profit or alpha claim, does not promote RSI, "
            "does not change thresholds, and does not touch broker state."
        ),
        "",
    ]
    return "\n".join(lines)


def _classify_replay_row(
    row: Mapping[str, object],
    *,
    row_number: int,
) -> dict[str, object]:
    _validate_replay_row(row, line_number=row_number)
    sma = _mapping(row["sma_strategy"], "sma_strategy")
    rsi = _mapping(row["rsi_strategy"], "rsi_strategy")
    router = _mapping(row["router_decision"], "router_decision")
    adapter = _mapping(row["adapter_resolution"], "adapter_resolution")

    data_as_of = _required_string(row["data_as_of"], "data_as_of")
    candidate_conflict = _required_bool(row["candidate_conflict"], "candidate_conflict")
    candidate_disagreement = _required_bool(
        row["candidate_disagreement"],
        "candidate_disagreement",
    )
    rsi_shadow_blocked = _required_bool(
        row["rsi_shadow_blocked_from_mutation"],
        "rsi_shadow_blocked_from_mutation",
    )
    final_mutation_eligibility = _required_bool(
        row["final_mutation_eligibility"],
        "final_mutation_eligibility",
    )

    sma_posture = _required_string(sma["posture"], "sma_strategy.posture")
    rsi_posture = _required_string(rsi["posture"], "rsi_strategy.posture")
    sma_state = _signal_state(sma, "sma_strategy")
    rsi_state = _signal_state(rsi, "rsi_strategy")
    sma_action = _required_string(
        sma["intended_action"],
        "sma_strategy.intended_action",
    )
    rsi_action = _required_string(
        rsi["intended_action"],
        "rsi_strategy.intended_action",
    )
    rsi_promotion_status = _required_string(
        rsi["promotion_status"],
        "rsi_strategy.promotion_status",
    )
    router_status = _required_string(
        router["route_status"],
        "router_decision.route_status",
    )
    router_reason = _required_string(router["reason"], "router_decision.reason")
    adapter_status = _required_string(
        adapter["resolution_status"],
        "adapter_resolution.resolution_status",
    )
    adapter_reason = _required_string(adapter["reason"], "adapter_resolution.reason")
    blocked_signal_ids = _string_list(
        router.get("blocked_signal_ids", ()),
        "router_decision.blocked_signal_ids",
    )

    rsi_mutation_eligible = (
        rsi_promotion_status == "paper_mutation_candidate"
        and rsi_shadow_blocked is False
    )
    diagnostic_buckets = _diagnostic_buckets(
        candidate_conflict=candidate_conflict,
        candidate_disagreement=candidate_disagreement,
        rsi_shadow_blocked=rsi_shadow_blocked,
        sma_posture=sma_posture,
        rsi_posture=rsi_posture,
        sma_state=sma_state,
        rsi_state=rsi_state,
        sma_action=sma_action,
        rsi_action=rsi_action,
        router_status=router_status,
        blocked_signal_ids=blocked_signal_ids,
        adapter_status=adapter_status,
        adapter_reason=adapter_reason,
    )
    primary_bucket = _primary_bucket(diagnostic_buckets)

    return {
        "record_type": CLASSIFICATION_ROW_RECORD_TYPE,
        "schema_version": CLASSIFIER_SCHEMA_VERSION,
        "source_record_type": row["record_type"],
        "run_id": row.get("run_id", ""),
        "row_number": row_number,
        "data_as_of": data_as_of,
        "date": data_as_of[:10],
        "primary_bucket": primary_bucket,
        "diagnostic_buckets": list(diagnostic_buckets),
        "candidate_conflict": candidate_conflict,
        "candidate_disagreement": candidate_disagreement,
        "rsi_shadow_blocked_from_mutation": rsi_shadow_blocked,
        "rsi_mutation_eligible": rsi_mutation_eligible,
        "final_mutation_eligibility": final_mutation_eligibility,
        "sma_posture": sma_posture,
        "sma_signal_state": sma_state,
        "sma_intended_action": sma_action,
        "rsi_posture": rsi_posture,
        "rsi_signal_state": rsi_state,
        "rsi_intended_action": rsi_action,
        "rsi_promotion_status": rsi_promotion_status,
        "router_route_status": router_status,
        "router_reason": router_reason,
        "router_blocked_signal_ids": blocked_signal_ids,
        "adapter_resolution_status": adapter_status,
        "adapter_reason": adapter_reason,
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }


def _diagnostic_buckets(
    *,
    candidate_conflict: bool,
    candidate_disagreement: bool,
    rsi_shadow_blocked: bool,
    sma_posture: str,
    rsi_posture: str,
    sma_state: str,
    rsi_state: str,
    sma_action: str,
    rsi_action: str,
    router_status: str,
    blocked_signal_ids: tuple[str, ...],
    adapter_status: str,
    adapter_reason: str,
) -> tuple[str, ...]:
    buckets: list[str] = []

    if (
        candidate_conflict
        and sma_posture == "bullish_risk_on"
        and rsi_posture == "overbought_cash_candidate"
    ):
        buckets.append("sma_risk_on_rsi_overbought_conflict")
    if (
        candidate_conflict
        and sma_posture == "defensive_risk_off"
        and rsi_posture == "oversold_buy_candidate"
    ):
        buckets.append("sma_risk_off_rsi_oversold_conflict")
    if candidate_conflict and (blocked_signal_ids or router_status == "blocked"):
        buckets.append("router_conflict_block")
    if rsi_state == "trade_candidate" and rsi_shadow_blocked:
        buckets.append("rsi_shadow_trade_candidate_blocked")
    if (
        rsi_posture == "neutral_no_trade"
        and sma_state == "trade_candidate"
        and candidate_disagreement
    ):
        buckets.append("rsi_neutral_sma_active_disagreement")
    if adapter_status == "blocked" and _looks_like_shadow_adapter_block(
        adapter_reason,
        rsi_shadow_blocked=rsi_shadow_blocked,
    ):
        buckets.append("adapter_registry_shadow_block")
    if (
        not candidate_conflict
        and not candidate_disagreement
        and sma_action == "no_action"
        and rsi_action == "no_action"
    ):
        buckets.append("no_action_alignment")

    if not buckets:
        buckets.append("other_router_observation")
    return tuple(_dedupe_in_order(buckets))


def _build_summary(
    classified_rows: tuple[Mapping[str, object], ...],
    *,
    source_replay_jsonl: str | Path | None,
) -> dict[str, object]:
    primary_counts = Counter(str(row["primary_bucket"]) for row in classified_rows)
    bucket_counts: Counter[str] = Counter()
    bucket_dates: dict[str, list[str]] = {bucket: [] for bucket in BUCKETS}
    primary_dates: dict[str, list[str]] = {bucket: [] for bucket in BUCKETS}

    for row in classified_rows:
        date_value = str(row["date"])
        primary_bucket = str(row["primary_bucket"])
        if primary_bucket in primary_dates:
            primary_dates[primary_bucket].append(date_value)
        for bucket in _string_list(row["diagnostic_buckets"], "diagnostic_buckets"):
            bucket_counts[bucket] += 1
            bucket_dates.setdefault(bucket, []).append(date_value)

    row_count = len(classified_rows)
    conflict_row_count = sum(
        1 for row in classified_rows if row["candidate_conflict"] is True
    )
    shadow_blocked_row_count = sum(
        1
        for row in classified_rows
        if row["rsi_shadow_blocked_from_mutation"] is True
    )
    rsi_shadow_mutation_eligible_count = sum(
        1
        for row in classified_rows
        if row["rsi_shadow_blocked_from_mutation"] is True
        and row["rsi_mutation_eligible"] is True
    )
    run_ids = _dedupe_in_order(str(row.get("run_id", "")) for row in classified_rows)
    run_id = run_ids[0] if len(run_ids) == 1 else "mixed"

    recommendation_categories = _recommendation_categories(
        row_count=row_count,
        conflict_row_count=conflict_row_count,
        shadow_blocked_row_count=shadow_blocked_row_count,
    )
    secondary_recommendations = [
        category
        for category in RECOMMENDATION_CATEGORIES
        if category != "keep_shadow"
        and _mapping(recommendation_categories[category], category)["applies"] is True
    ]

    return {
        "record_type": CLASSIFICATION_SUMMARY_RECORD_TYPE,
        "schema_version": CLASSIFIER_SCHEMA_VERSION,
        "run_id": run_id,
        "source_replay_jsonl": "" if source_replay_jsonl is None else str(source_replay_jsonl),
        "classification_status": "complete",
        "classification_recommendation": "keep_shadow",
        "secondary_recommendations": secondary_recommendations,
        "recommendation_categories": recommendation_categories,
        "evidence_classification": "decision_quality_evidence",
        "architecture_capability": True,
        "process_overhead": False,
        "row_count": row_count,
        "replay_start_date": str(classified_rows[0]["date"]),
        "replay_end_date": str(classified_rows[-1]["date"]),
        "conflict_row_count": conflict_row_count,
        "shadow_blocked_row_count": shadow_blocked_row_count,
        "rsi_shadow_mutation_eligible_count": rsi_shadow_mutation_eligible_count,
        "primary_bucket_counts": _ordered_counts(primary_counts),
        "bucket_counts": _ordered_counts(bucket_counts),
        "bucket_representative_dates": _representative_dates(bucket_dates),
        "primary_bucket_representative_dates": _representative_dates(primary_dates),
        "conflict_bucket_summary": _bucket_summary(
            bucket_counts,
            bucket_dates,
            _CONFLICT_BUCKETS,
        ),
        "shadow_blocked_bucket_summary": _bucket_summary(
            bucket_counts,
            bucket_dates,
            _SHADOW_BLOCK_BUCKETS,
        ),
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
        "strategy_promotion_performed": False,
        "threshold_change_performed": False,
        "rsi_promotion_status": "shadow_only",
        "rsi_mutation_eligibility": False,
        "labels": [
            "paper_lab_only",
            "offline_only",
            "strategy_router_shadow_conflict_classifier",
            "rsi_shadow_only_no_promotion",
            "not_live_authorized",
            "profit_claim=none",
        ],
    }


def _recommendation_categories(
    *,
    row_count: int,
    conflict_row_count: int,
    shadow_blocked_row_count: int,
) -> dict[str, dict[str, object]]:
    return {
        "keep_shadow": {
            "applies": True,
            "reason": "RSI is shadow_only and remains mutation-ineligible.",
        },
        "needs_longer_replay": {
            "applies": row_count < 504,
            "reason": "Replay is shorter than roughly two trading years.",
        },
        "needs_oos_backtest": {
            "applies": shadow_blocked_row_count > 0 or conflict_row_count > 0,
            "reason": "Action-bearing RSI shadow rows require out-of-sample replay before any promotion discussion.",
        },
        "needs_threshold_review": {
            "applies": conflict_row_count > 0,
            "reason": "RSI trade candidates conflict with the promoted SMA path in the replay window.",
        },
        "reject_candidate": {
            "applies": False,
            "reason": "Router diagnostics alone are not a rejection test.",
        },
    }


def _validate_replay_row(row: Mapping[str, object], *, line_number: int) -> None:
    prefix = f"replay_jsonl line {line_number}"
    if row.get("record_type") != REPLAY_ROW_RECORD_TYPE:
        raise ValidationError(f"{prefix} must be a {REPLAY_ROW_RECORD_TYPE}.")
    for field_name in (
        "data_as_of",
        "sma_strategy",
        "rsi_strategy",
        "router_decision",
        "adapter_resolution",
        "candidate_disagreement",
        "candidate_conflict",
        "rsi_shadow_blocked_from_mutation",
        "final_mutation_eligibility",
        "profit_claim",
    ):
        if field_name not in row:
            raise ValidationError(f"{prefix} missing required field: {field_name}.")

    if row["profit_claim"] != "none":
        raise ValidationError(f"{prefix} must not contain a profit claim.")

    for field_name in _SAFETY_FALSE_FIELDS:
        if field_name not in row:
            raise ValidationError(f"{prefix} missing required field: {field_name}.")
        if row[field_name] is not False:
            raise ValidationError(f"{prefix} has unsafe field set: {field_name}.")

    sma = _mapping(row["sma_strategy"], f"{prefix}.sma_strategy")
    rsi = _mapping(row["rsi_strategy"], f"{prefix}.rsi_strategy")
    router = _mapping(row["router_decision"], f"{prefix}.router_decision")
    adapter = _mapping(row["adapter_resolution"], f"{prefix}.adapter_resolution")

    for container_name, container, field_names in (
        (
            "sma_strategy",
            sma,
            ("posture", "intended_action", "promotion_status"),
        ),
        (
            "rsi_strategy",
            rsi,
            ("posture", "intended_action", "promotion_status"),
        ),
        ("router_decision", router, ("route_status", "reason")),
        ("adapter_resolution", adapter, ("resolution_status", "reason")),
    ):
        for field_name in field_names:
            if field_name not in container:
                raise ValidationError(
                    f"{prefix}.{container_name} missing required field: {field_name}."
                )
            _required_string(
                container[field_name],
                f"{prefix}.{container_name}.{field_name}",
            )

    _signal_state(sma, f"{prefix}.sma_strategy")
    _signal_state(rsi, f"{prefix}.rsi_strategy")
    _required_bool(row["candidate_disagreement"], f"{prefix}.candidate_disagreement")
    _required_bool(row["candidate_conflict"], f"{prefix}.candidate_conflict")
    _required_bool(
        row["rsi_shadow_blocked_from_mutation"],
        f"{prefix}.rsi_shadow_blocked_from_mutation",
    )
    _required_bool(
        row["final_mutation_eligibility"],
        f"{prefix}.final_mutation_eligibility",
    )


def _signal_state(container: Mapping[str, object], field_name: str) -> str:
    if "signal_state" in container:
        return _required_string(container["signal_state"], f"{field_name}.signal_state")
    if "state" in container:
        return _required_string(container["state"], f"{field_name}.state")
    raise ValidationError(f"{field_name} missing required field: signal_state.")


def _looks_like_shadow_adapter_block(
    adapter_reason: str,
    *,
    rsi_shadow_blocked: bool,
) -> bool:
    return rsi_shadow_blocked and (
        adapter_reason.startswith("strategy_router_")
        or "shadow_only" in adapter_reason
        or "promotion_status_not_paper_mutation_candidate" in adapter_reason
    )


def _primary_bucket(diagnostic_buckets: tuple[str, ...]) -> str:
    for bucket in _PRIMARY_BUCKET_ORDER:
        if bucket in diagnostic_buckets:
            return bucket
    return "other_router_observation"


def _bucket_summary(
    bucket_counts: Counter[str],
    bucket_dates: Mapping[str, list[str]],
    bucket_names: tuple[str, ...],
) -> dict[str, dict[str, object]]:
    return {
        bucket: {
            "count": bucket_counts.get(bucket, 0),
            "representative_dates": bucket_dates.get(bucket, [])[:5],
        }
        for bucket in bucket_names
    }


def _ordered_counts(counter: Counter[str]) -> dict[str, int]:
    return {bucket: counter.get(bucket, 0) for bucket in BUCKETS}


def _representative_dates(bucket_dates: Mapping[str, list[str]]) -> dict[str, list[str]]:
    return {bucket: bucket_dates.get(bucket, [])[:5] for bucket in BUCKETS}


def _render_bucket_lines(summary: Mapping[str, object]) -> list[str]:
    lines: list[str] = []
    for bucket, payload in summary.items():
        details = _mapping(payload, bucket)
        dates = ", ".join(_string_list(details["representative_dates"], bucket))
        dates_text = dates if dates else "none"
        lines.append(f"- {bucket}: count={details['count']}; representative_dates={dates_text}")
    return lines


def _render_recommendation_lines(
    recommendations: Mapping[str, object],
) -> list[str]:
    lines: list[str] = []
    for category in RECOMMENDATION_CATEGORIES:
        payload = _mapping(recommendations[category], category)
        applies = str(payload["applies"]).lower()
        lines.append(f"- {category}: applies={applies}; reason={payload['reason']}")
    return lines


def _record_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError("records must be a list.")
    return [_mapping(item, "records[]") for item in value]


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _string_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{field_name} must be a list of strings.")
    return tuple(_required_string(item, f"{field_name}[]") for item in value)


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _required_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a boolean.")
    return value


def _local_path(value: str | Path, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif type(value) is str and value.strip():
        if "://" in value:
            raise ValidationError(f"{field_name} must be a local path.")
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a local path.")
    return path


def _dedupe_in_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            items.append(value)
    return tuple(items)


def _compact_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
