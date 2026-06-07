"""Offline M421 adjusted-basis promotion packet builder."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

__all__ = [
    "EtfSmaAdjustedBasisPromotionPacketConfig",
    "build_etf_sma_adjusted_basis_promotion_packet",
    "render_etf_sma_adjusted_basis_promotion_packet_json",
    "render_etf_sma_adjusted_basis_promotion_packet_text",
    "write_etf_sma_adjusted_basis_promotion_packet_jsonl",
]


@dataclass(frozen=True)
class EtfSmaAdjustedBasisPromotionPacketConfig:
    """Configuration for the offline M421 basis-promotion packet."""

    run_id: str
    symbol: str
    source_m417_artifact: str | Path
    source_m420_artifact: str | Path


_COMMAND = "etf-sma-adjusted-basis-promotion-packet"
_RECORD_TYPE = "etf_sma_adjusted_basis_promotion_packet"
_SCHEMA_VERSION = "1"
_MILESTONE = "M421"
_PROMOTION_READY_STATUS = "ready_to_promote_adjusted_matched_window_basis"
_PROMOTION_BLOCKED_STATUS = "blocked_adjusted_matched_window_basis_promotion"
_COMPARISON_BASIS = "matched_window"
_RAW_BASIS = "raw_close_price_return"
_ADJUSTED_BASIS = "adjusted_close_price_return"
_BASELINE_RECOMMENDATION = "adjusted_close_matched_window"
_M417_RECORD_TYPE = "etf_sma_regime_slice_evidence"
_M420_RECORD_TYPE = "etf_sma_adjusted_matched_window_validation"
_M420_STATUS = "completed_adjusted_matched_window_validation"
_EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT = 1055
_EXPECTED_FULL_ADJUSTED_HISTORY_COUNT = 8195
_EXPECTED_RETURN_CONCLUSION_CHANGES: tuple[str, ...] = ()
_EXPECTED_DRAWDOWN_CONCLUSION_CHANGES = ("recovery_2023",)
_EXPECTED_SLICE_CONTRACT = (
    ("full_evaluated_window", "2022-03-21", "2026-06-05", 1055),
    ("stress_2022", "2022-03-21", "2022-12-30", 197),
    ("recovery_2023", "2022-12-30", "2023-12-29", 250),
    ("bull_2024", "2023-12-29", "2024-12-31", 252),
    ("whipsaw_2025", "2024-12-31", "2025-12-31", 250),
    ("ytd_2026", "2025-12-31", "2026-06-05", 106),
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_ADDITIONAL_SAFETY_FALSE_FIELDS = (
    "submit_authorized",
    "submit_path_allowed",
    "paper_submit_approved",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "credential_access",
    "broker_network_access",
    "broker_actions_performed",
    "market_data_fetch_performed",
)
_SLICE_METRIC_FIELDS = (
    "strategy_total_return",
    "benchmark_total_return",
    "strategy_max_drawdown",
    "benchmark_max_drawdown",
)


def build_etf_sma_adjusted_basis_promotion_packet(
    config: EtfSmaAdjustedBasisPromotionPacketConfig,
) -> dict[str, object]:
    """Build the deterministic offline M421 adjusted-basis promotion packet."""

    raw_path = Path(config.source_m417_artifact)
    adjusted_path = Path(config.source_m420_artifact)
    payload = _base_payload(config, raw_path, adjusted_path)

    raw_record, raw_load_error = _load_single_jsonl_record(raw_path, "raw")
    adjusted_record, adjusted_load_error = _load_single_jsonl_record(
        adjusted_path,
        "adjusted",
    )
    blockers = [error for error in (raw_load_error, adjusted_load_error) if error]
    if blockers:
        return _blocked_payload(payload, blockers)

    raw_blockers = _validate_raw_m417a_contract(raw_record, config.symbol)
    adjusted_blockers = _validate_adjusted_m420_contract(
        adjusted_record,
        config.symbol,
    )
    blockers.extend(raw_blockers)
    blockers.extend(adjusted_blockers)
    if blockers:
        return _blocked_payload(payload, blockers)

    raw_slices = _summarize_slices(
        _payload_mapping_list(raw_record, "regime_slices"),
        data_basis=_RAW_BASIS,
    )
    adjusted_slices = _summarize_slices(
        _payload_mapping_list(adjusted_record, "regime_slices"),
        data_basis=_ADJUSTED_BASIS,
    )
    comparisons = _compare_slices(raw_slices, adjusted_slices)
    return_changes = tuple(
        item["slice_name"]
        for item in comparisons
        if item["return_conclusion_unchanged"] is False
    )
    drawdown_changes = tuple(
        item["slice_name"]
        for item in comparisons
        if item["drawdown_conclusion_unchanged"] is False
    )
    same_slice_counts = all(
        item["same_evaluated_return_count"] is True for item in comparisons
    )
    same_slice_dates = all(item["same_slice_dates"] is True for item in comparisons)
    conclusion_delta_blockers: list[str] = []
    if return_changes != _EXPECTED_RETURN_CONCLUSION_CHANGES:
        conclusion_delta_blockers.append("unexpected_return_conclusion_deltas")
    if drawdown_changes != _EXPECTED_DRAWDOWN_CONCLUSION_CHANGES:
        conclusion_delta_blockers.append("unexpected_drawdown_conclusion_deltas")
    if not _m420_embedded_comparison_matches(adjusted_record, comparisons):
        conclusion_delta_blockers.append("m420_embedded_comparison_mismatch")
    if not same_slice_counts:
        conclusion_delta_blockers.append("raw_adjusted_slice_counts_differ")
    if not same_slice_dates:
        conclusion_delta_blockers.append("raw_adjusted_slice_dates_differ")
    if conclusion_delta_blockers:
        payload.update(_comparison_payload(comparisons, return_changes, drawdown_changes))
        return _blocked_payload(payload, conclusion_delta_blockers)

    payload.update(
        {
            "promotion_status": _PROMOTION_READY_STATUS,
            "raw_artifact_valid": True,
            "adjusted_artifact_valid": True,
            "same_slice_counts": True,
            "same_slice_dates": True,
            "m417a_slice_counts_unchanged": True,
            "matched_total_interval_count": _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT,
            "matched_evaluated_return_count": _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT,
            "full_adjusted_history_evaluated_return_count": (
                _EXPECTED_FULL_ADJUSTED_HISTORY_COUNT
            ),
            "adjusted_basis_verified": True,
            "source_adjusted_safety_flags_clean": True,
            "baseline_recommendation": _BASELINE_RECOMMENDATION,
            "preferred_offline_baseline_ready": True,
            "promotion_decision_reason": (
                "adjusted matched-window evidence preserves return conclusions, "
                "keeps M417A slice dates/counts fixed, and enumerates the sole "
                "drawdown conclusion delta."
            ),
            "raw_source_contract": _slice_contract(raw_slices),
            "adjusted_source_contract": _slice_contract(adjusted_slices),
        }
    )
    payload.update(_comparison_payload(comparisons, return_changes, drawdown_changes))
    return payload


def render_etf_sma_adjusted_basis_promotion_packet_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_adjusted_basis_promotion_packet_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        f"promotion_status: {payload['promotion_status']}",
        f"comparison_basis: {payload['comparison_basis']}",
        f"raw_basis: {payload['raw_basis']}",
        f"adjusted_basis: {payload['adjusted_basis']}",
        f"same_slice_counts: {_bool_text(payload.get('same_slice_counts'))}",
        f"same_slice_dates: {_bool_text(payload.get('same_slice_dates'))}",
        "return_conclusions_unchanged: "
        f"{_bool_text(payload.get('return_conclusions_unchanged'))}",
        "drawdown_conclusion_changes: "
        f"{','.join(_payload_string_tuple(payload.get('drawdown_conclusion_changes')))}",
        "basis_delta_review_required: "
        f"{_bool_text(payload.get('basis_delta_review_required'))}",
        f"baseline_recommendation: {payload['baseline_recommendation']}",
        f"trade_recommendation: {payload['trade_recommendation']}",
        f"profit_claim: {payload['profit_claim']}",
    ]
    blockers = _payload_string_tuple(payload.get("blockers"))
    if blockers:
        lines.append(f"blockers: {','.join(blockers)}")
    return "\n".join(lines)


def write_etf_sma_adjusted_basis_promotion_packet_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_adjusted_basis_promotion_packet_json(payload) + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaAdjustedBasisPromotionPacketConfig,
    raw_path: Path,
    adjusted_path: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "comparison_basis": _COMPARISON_BASIS,
        "raw_basis": _RAW_BASIS,
        "adjusted_basis": _ADJUSTED_BASIS,
        "source_raw_artifact": str(raw_path),
        "source_adjusted_artifact": str(adjusted_path),
        "promotion_status": _PROMOTION_BLOCKED_STATUS,
        "raw_artifact_valid": False,
        "adjusted_artifact_valid": False,
        "same_slice_counts": False,
        "same_slice_dates": False,
        "m417a_slice_counts_unchanged": False,
        "matched_total_interval_count": 0,
        "matched_evaluated_return_count": 0,
        "full_adjusted_history_evaluated_return_count": 0,
        "return_conclusions_unchanged": False,
        "return_conclusion_changes": [],
        "drawdown_conclusion_changes": [],
        "basis_delta_review_required": False,
        "baseline_recommendation": _BASELINE_RECOMMENDATION,
        "preferred_offline_baseline_ready": False,
        "trade_recommendation": "none",
        "operator_trade_recommendation": "none",
        "profit_claim": "none",
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "paper_lab_only": True,
        "research_only": True,
        "signal_evaluation_only": True,
        "broker_mutation_status": "none",
        "network_broker_access_status": "not_attempted",
        "credential_access_status": "not_attempted",
        "blockers": [],
    }
    payload.update(_safety_false_fields())
    return payload


def _blocked_payload(
    payload: dict[str, object],
    blockers: Sequence[str],
) -> dict[str, object]:
    clean_blockers = [str(blocker) for blocker in blockers if str(blocker)]
    payload.update(
        {
            "promotion_status": _PROMOTION_BLOCKED_STATUS,
            "preferred_offline_baseline_ready": False,
            "blockers": clean_blockers,
            "blocked_reason": clean_blockers[0] if clean_blockers else "blocked",
            "trade_recommendation": "none",
            "operator_trade_recommendation": "none",
            "profit_claim": "none",
        }
    )
    payload.update(_safety_false_fields())
    return payload


def _load_single_jsonl_record(
    path: Path,
    source_name: str,
) -> tuple[dict[str, object], str | None]:
    if not path.exists():
        return {}, f"source_{source_name}_artifact_not_found"

    records: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}, f"source_{source_name}_artifact_unreadable"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            return {}, f"source_{source_name}_artifact_invalid_json"
        if not isinstance(decoded, dict):
            return {}, f"source_{source_name}_artifact_record_not_object"
        records.append(decoded)

    if not records:
        return {}, f"source_{source_name}_artifact_empty"
    if len(records) != 1:
        return {}, f"ambiguous_source_{source_name}_artifact_record_count"
    return records[0], None


def _validate_raw_m417a_contract(
    raw_record: Mapping[str, object],
    symbol: str,
) -> list[str]:
    blockers: list[str] = []
    if raw_record.get("record_type") != _M417_RECORD_TYPE:
        blockers.append("raw_artifact_not_m417a_regime_slice_evidence")
    if raw_record.get("data_basis") != _RAW_BASIS:
        blockers.append("raw_artifact_basis_not_raw_close")
    if raw_record.get("symbol") != symbol:
        blockers.append("raw_artifact_symbol_mismatch")
    if _mapping_int(raw_record, "evaluated_return_count") != (
        _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT
    ):
        blockers.append("raw_full_interval_count_mismatch")

    slices = _payload_mapping_list(raw_record, "regime_slices")
    blockers.extend(_validate_slice_contract(slices, source_name="raw"))
    blockers.extend(_validate_slice_metrics(slices, source_name="raw"))
    if raw_record.get("profit_claim", "none") != "none":
        blockers.append("raw_artifact_profit_claim_not_none")
    return blockers


def _validate_adjusted_m420_contract(
    adjusted_record: Mapping[str, object],
    symbol: str,
) -> list[str]:
    blockers: list[str] = []
    if adjusted_record.get("record_type") != _M420_RECORD_TYPE:
        blockers.append("adjusted_artifact_not_m420_matched_window_validation")
    if adjusted_record.get("milestone") != "M420":
        blockers.append("adjusted_artifact_milestone_not_m420")
    if adjusted_record.get("basis_validation_status") != _M420_STATUS:
        blockers.append("adjusted_artifact_not_completed_matched_window_validation")
    if adjusted_record.get("symbol") != symbol:
        blockers.append("adjusted_artifact_symbol_mismatch")
    if adjusted_record.get("data_basis") != _ADJUSTED_BASIS:
        blockers.append("adjusted_basis_label_not_adjusted_or_total_return")
    if adjusted_record.get("price_field") != "adjusted_close":
        blockers.append("adjusted_price_field_not_adjusted_close")
    if adjusted_record.get("adjusted_close_available") is not True:
        blockers.append("adjusted_close_unavailable")
    if adjusted_record.get("same_slice_counts") is not True:
        blockers.append("adjusted_same_slice_counts_not_true")
    if adjusted_record.get("same_slice_dates") is not True:
        blockers.append("adjusted_same_slice_dates_not_true")
    if adjusted_record.get("m417a_slice_counts_unchanged") is not True:
        blockers.append("adjusted_m417a_slice_counts_not_unchanged")
    if _mapping_int(adjusted_record, "matched_total_interval_count") != (
        _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT
    ):
        blockers.append("adjusted_matched_total_interval_count_mismatch")
    if _mapping_int(adjusted_record, "evaluated_return_count") != (
        _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT
    ):
        blockers.append("adjusted_matched_evaluated_return_count_mismatch")
    if _mapping_int(adjusted_record, "full_history_evaluated_return_count") != (
        _EXPECTED_FULL_ADJUSTED_HISTORY_COUNT
    ):
        blockers.append("adjusted_full_history_count_mismatch")
    if adjusted_record.get("returns_fabricated") is not False:
        blockers.append("adjusted_returns_fabricated_flag_dirty")
    if adjusted_record.get("no_fabricated_returns") is not True:
        blockers.append("adjusted_no_fabricated_returns_not_true")
    if adjusted_record.get("trade_recommendation") != "none":
        blockers.append("adjusted_trade_recommendation_not_none")
    if adjusted_record.get("profit_claim") != "none":
        blockers.append("adjusted_profit_claim_not_none")

    source_inspection = _payload_mapping(
        adjusted_record.get("adjusted_close_source_inspection"),
    )
    if source_inspection.get("valid") is not True:
        blockers.append("adjusted_close_source_inspection_not_valid")
    if source_inspection.get("adjusted_close_available") is not True:
        blockers.append("adjusted_close_source_inspection_unavailable")
    if _mapping_int(source_inspection, "close_adjusted_close_diff_count") <= 0:
        blockers.append("adjusted_close_mirrors_raw_close_or_unverified")

    for field_name in _SAFETY_FALSE_FIELDS:
        if adjusted_record.get(field_name) is not False:
            blockers.append(f"adjusted_safety_flag_dirty_{field_name}")

    slices = _payload_mapping_list(adjusted_record, "regime_slices")
    blockers.extend(_validate_slice_contract(slices, source_name="adjusted"))
    blockers.extend(_validate_slice_metrics(slices, source_name="adjusted"))
    return blockers


def _validate_slice_contract(
    slices: Sequence[Mapping[str, object]],
    *,
    source_name: str,
) -> list[str]:
    blockers: list[str] = []
    by_name = {str(item.get("slice_name", "")): item for item in slices}
    expected_names = tuple(item[0] for item in _EXPECTED_SLICE_CONTRACT)
    if tuple(by_name.keys()) != expected_names:
        blockers.append(f"{source_name}_slice_names_or_order_mismatch")

    for name, start_date, end_date, count in _EXPECTED_SLICE_CONTRACT:
        item = by_name.get(name)
        if item is None:
            blockers.append(f"{source_name}_missing_slice_{name}")
            continue
        if item.get("slice_start_date") != start_date:
            blockers.append(f"{source_name}_slice_start_date_mismatch_{name}")
        if item.get("slice_end_date") != end_date:
            blockers.append(f"{source_name}_slice_end_date_mismatch_{name}")
        if _mapping_int(item, "evaluated_return_count") != count:
            blockers.append(f"{source_name}_slice_count_mismatch_{name}")
    return blockers


def _validate_slice_metrics(
    slices: Sequence[Mapping[str, object]],
    *,
    source_name: str,
) -> list[str]:
    blockers: list[str] = []
    for item in slices:
        name = str(item.get("slice_name", "unknown"))
        if item.get("data_basis") not in (_RAW_BASIS, _ADJUSTED_BASIS):
            blockers.append(f"{source_name}_slice_basis_invalid_{name}")
        if item.get("profit_claim", "none") != "none":
            blockers.append(f"{source_name}_slice_profit_claim_not_none_{name}")
        for field_name in _SLICE_METRIC_FIELDS:
            try:
                _mapping_decimal(item, field_name)
            except ValueError:
                blockers.append(f"{source_name}_slice_metric_invalid_{name}")
                break
    return blockers


def _summarize_slices(
    slices: Sequence[Mapping[str, object]],
    *,
    data_basis: str,
) -> list[dict[str, object]]:
    by_name = {str(item["slice_name"]): item for item in slices}
    return [
        _slice_summary(by_name[name], data_basis=data_basis)
        for name, _, _, _ in _EXPECTED_SLICE_CONTRACT
    ]


def _slice_summary(
    item: Mapping[str, object],
    *,
    data_basis: str,
) -> dict[str, object]:
    return {
        "slice_name": str(item["slice_name"]),
        "slice_start_date": str(item["slice_start_date"]),
        "slice_end_date": str(item["slice_end_date"]),
        "evaluated_return_count": _mapping_int(item, "evaluated_return_count"),
        "data_basis": data_basis,
        "strategy_total_return": str(item["strategy_total_return"]),
        "benchmark_total_return": str(item["benchmark_total_return"]),
        "strategy_max_drawdown": str(item["strategy_max_drawdown"]),
        "benchmark_max_drawdown": str(item["benchmark_max_drawdown"]),
        "return_conclusion": _return_conclusion(item),
        "drawdown_conclusion": _drawdown_conclusion(item),
        "trade_recommendation": "none",
        "profit_claim": "none",
    }


def _compare_slices(
    raw_slices: Sequence[Mapping[str, object]],
    adjusted_slices: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    adjusted_by_name = {str(item["slice_name"]): item for item in adjusted_slices}
    comparisons: list[dict[str, object]] = []
    for raw_item in raw_slices:
        name = str(raw_item["slice_name"])
        adjusted_item = adjusted_by_name[name]
        same_count = (
            raw_item["evaluated_return_count"]
            == adjusted_item["evaluated_return_count"]
        )
        same_dates = (
            raw_item["slice_start_date"] == adjusted_item["slice_start_date"]
            and raw_item["slice_end_date"] == adjusted_item["slice_end_date"]
        )
        same_return_conclusion = (
            raw_item["return_conclusion"] == adjusted_item["return_conclusion"]
        )
        same_drawdown_conclusion = (
            raw_item["drawdown_conclusion"] == adjusted_item["drawdown_conclusion"]
        )
        comparison = {
            "slice_name": name,
            "status": "compared",
            "same_evaluated_return_count": same_count,
            "same_slice_dates": same_dates,
            "raw_evaluated_return_count": raw_item["evaluated_return_count"],
            "adjusted_evaluated_return_count": adjusted_item[
                "evaluated_return_count"
            ],
            "raw_strategy_total_return": raw_item["strategy_total_return"],
            "adjusted_strategy_total_return": adjusted_item[
                "strategy_total_return"
            ],
            "strategy_total_return_delta": _decimal_delta_text(
                adjusted_item["strategy_total_return"],
                raw_item["strategy_total_return"],
            ),
            "raw_benchmark_total_return": raw_item["benchmark_total_return"],
            "adjusted_benchmark_total_return": adjusted_item[
                "benchmark_total_return"
            ],
            "benchmark_total_return_delta": _decimal_delta_text(
                adjusted_item["benchmark_total_return"],
                raw_item["benchmark_total_return"],
            ),
            "raw_strategy_max_drawdown": raw_item["strategy_max_drawdown"],
            "adjusted_strategy_max_drawdown": adjusted_item[
                "strategy_max_drawdown"
            ],
            "strategy_max_drawdown_delta": _decimal_delta_text(
                adjusted_item["strategy_max_drawdown"],
                raw_item["strategy_max_drawdown"],
            ),
            "raw_benchmark_max_drawdown": raw_item["benchmark_max_drawdown"],
            "adjusted_benchmark_max_drawdown": adjusted_item[
                "benchmark_max_drawdown"
            ],
            "benchmark_max_drawdown_delta": _decimal_delta_text(
                adjusted_item["benchmark_max_drawdown"],
                raw_item["benchmark_max_drawdown"],
            ),
            "raw_return_conclusion": raw_item["return_conclusion"],
            "adjusted_return_conclusion": adjusted_item["return_conclusion"],
            "return_conclusion_unchanged": same_return_conclusion,
            "raw_drawdown_conclusion": raw_item["drawdown_conclusion"],
            "adjusted_drawdown_conclusion": adjusted_item["drawdown_conclusion"],
            "drawdown_conclusion_unchanged": same_drawdown_conclusion,
        }
        comparisons.append(comparison)
    return comparisons


def _comparison_payload(
    comparisons: Sequence[Mapping[str, object]],
    return_changes: Sequence[str],
    drawdown_changes: Sequence[str],
) -> dict[str, object]:
    return {
        "per_slice_comparisons": [dict(item) for item in comparisons],
        "matched_slice_comparisons": [dict(item) for item in comparisons],
        "return_conclusions_unchanged": len(return_changes) == 0,
        "return_conclusion_changes": list(return_changes),
        "drawdown_conclusion_changes": list(drawdown_changes),
        "basis_delta_review_required": bool(return_changes or drawdown_changes),
        "basis_delta_explanations": _basis_delta_explanations(comparisons),
        "full_window_return_deltas": _full_window_return_deltas(comparisons),
        "conclusion_deltas_fully_enumerated": True,
    }


def _basis_delta_explanations(
    comparisons: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    explanations: list[dict[str, object]] = []
    for item in comparisons:
        if item["return_conclusion_unchanged"] is False:
            explanations.append(
                {
                    "slice_name": item["slice_name"],
                    "changed_field": "return_conclusion",
                    "raw_conclusion": item["raw_return_conclusion"],
                    "adjusted_conclusion": item["adjusted_return_conclusion"],
                    "explanation": (
                        "Adjusted close uses the same matched dates/counts but "
                        "changes the return comparison for this slice."
                    ),
                }
            )
        if item["drawdown_conclusion_unchanged"] is False:
            explanations.append(
                {
                    "slice_name": item["slice_name"],
                    "changed_field": "drawdown_conclusion",
                    "raw_conclusion": item["raw_drawdown_conclusion"],
                    "adjusted_conclusion": item["adjusted_drawdown_conclusion"],
                    "explanation": (
                        "Adjusted close keeps the matched window fixed while "
                        "distribution-adjusted prices move the drawdown "
                        "comparison across the raw-close conclusion boundary."
                    ),
                }
            )
    return explanations


def _full_window_return_deltas(
    comparisons: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    full_window = next(
        item
        for item in comparisons
        if item["slice_name"] == "full_evaluated_window"
    )
    return {
        "strategy_total_return": {
            "raw": full_window["raw_strategy_total_return"],
            "adjusted": full_window["adjusted_strategy_total_return"],
            "delta": full_window["strategy_total_return_delta"],
        },
        "benchmark_total_return": {
            "raw": full_window["raw_benchmark_total_return"],
            "adjusted": full_window["adjusted_benchmark_total_return"],
            "delta": full_window["benchmark_total_return_delta"],
        },
    }


def _m420_embedded_comparison_matches(
    adjusted_record: Mapping[str, object],
    comparisons: Sequence[Mapping[str, object]],
) -> bool:
    embedded = _payload_mapping_list(adjusted_record, "matched_slice_comparisons")
    if not embedded:
        return True

    embedded_by_name = {str(item.get("slice_name", "")): item for item in embedded}
    for comparison in comparisons:
        item = embedded_by_name.get(str(comparison["slice_name"]))
        if item is None:
            return False
        for field_name in (
            "raw_strategy_total_return",
            "adjusted_strategy_total_return",
            "raw_benchmark_total_return",
            "adjusted_benchmark_total_return",
            "raw_strategy_max_drawdown",
            "adjusted_strategy_max_drawdown",
            "raw_return_conclusion",
            "adjusted_return_conclusion",
            "raw_drawdown_conclusion",
            "adjusted_drawdown_conclusion",
            "return_conclusion_unchanged",
            "drawdown_conclusion_unchanged",
        ):
            if item.get(field_name) != comparison[field_name]:
                return False
    return True


def _slice_contract(slices: Sequence[Mapping[str, object]]) -> dict[str, object]:
    return {
        "total_interval_count": _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT,
        "slices": [
            {
                "slice_name": item["slice_name"],
                "slice_start_date": item["slice_start_date"],
                "slice_end_date": item["slice_end_date"],
                "evaluated_return_count": item["evaluated_return_count"],
            }
            for item in slices
        ],
    }


def _return_conclusion(item: Mapping[str, object]) -> str:
    strategy_return = _mapping_decimal(item, "strategy_total_return")
    benchmark_return = _mapping_decimal(item, "benchmark_total_return")
    if strategy_return > benchmark_return:
        return "strategy_return_above_benchmark"
    if strategy_return < benchmark_return:
        return "strategy_return_below_benchmark"
    return "strategy_return_matches_benchmark"


def _drawdown_conclusion(item: Mapping[str, object]) -> str:
    strategy_drawdown = _mapping_decimal(item, "strategy_max_drawdown")
    benchmark_drawdown = _mapping_decimal(item, "benchmark_max_drawdown")
    if strategy_drawdown > benchmark_drawdown:
        return "strategy_drawdown_above_benchmark"
    if strategy_drawdown < benchmark_drawdown:
        return "strategy_drawdown_below_benchmark"
    return "strategy_drawdown_matches_benchmark"


def _payload_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _payload_mapping_list(
    payload: Mapping[str, object],
    key: str,
) -> list[dict[str, object]]:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []

    records: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            records.append(dict(item))
    return records


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _mapping_int(payload: Mapping[str, object], key: str) -> int:
    try:
        value = payload.get(key)
        if isinstance(value, bool):
            return 0
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _mapping_decimal(payload: Mapping[str, object], key: str) -> Decimal:
    try:
        return Decimal(str(payload[key]))
    except (KeyError, InvalidOperation, ValueError) as exc:
        raise ValueError(key) from exc


def _decimal_delta_text(adjusted_value: object, raw_value: object) -> str:
    return str(Decimal(str(adjusted_value)) - Decimal(str(raw_value)))


def _safety_false_fields() -> dict[str, bool]:
    return {
        field_name: False
        for field_name in _SAFETY_FALSE_FIELDS + _ADDITIONAL_SAFETY_FALSE_FIELDS
    }


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
