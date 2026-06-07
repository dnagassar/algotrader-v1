"""Offline M422 preferred ETF/SMA baseline manifest builder."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

__all__ = [
    "EtfSmaPreferredBaselineManifestConfig",
    "build_etf_sma_preferred_baseline_manifest",
    "render_etf_sma_preferred_baseline_manifest_json",
    "render_etf_sma_preferred_baseline_manifest_text",
    "write_etf_sma_preferred_baseline_manifest_jsonl",
]


@dataclass(frozen=True)
class EtfSmaPreferredBaselineManifestConfig:
    """Configuration for the offline M422 preferred-baseline manifest."""

    run_id: str
    symbol: str
    source_promotion_packet: str | Path


_COMMAND = "etf-sma-preferred-baseline-manifest"
_RECORD_TYPE = "etf_sma_preferred_baseline_manifest"
_SCHEMA_VERSION = "1"
_MILESTONE = "M422"
_BASELINE_SOURCE_MILESTONE = "M421"
_MANIFEST_ACTIVE_STATUS = "preferred_baseline_active"
_MANIFEST_BLOCKED_STATUS = "blocked_preferred_baseline_manifest"
_SOURCE_RECORD_TYPE = "etf_sma_adjusted_basis_promotion_packet"
_SOURCE_PROMOTION_STATUS = "ready_to_promote_adjusted_matched_window_basis"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_COMPARISON_BASIS = "matched_window"
_LEGACY_RAW_BASIS = "raw_close_price_return"
_LEGACY_RAW_BASELINE_STATUS = "superseded_for_offline_comparison"
_DOWNSTREAM_USE = "offline_etf_sma_comparison_baseline"
_EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT = 1055
_EXPECTED_RETURN_CONCLUSION_CHANGES: tuple[str, ...] = ()
_EXPECTED_KNOWN_BASIS_DELTA_SLICES = ("recovery_2023",)
_SOURCE_REQUIRED_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
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
_MANIFEST_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SOURCE_NONE_FIELDS = (
    "trade_recommendation",
    "operator_trade_recommendation",
    "profit_claim",
)


def build_etf_sma_preferred_baseline_manifest(
    config: EtfSmaPreferredBaselineManifestConfig,
) -> dict[str, object]:
    """Build the deterministic offline M422 preferred-baseline manifest."""

    source_path = Path(config.source_promotion_packet)
    payload = _base_payload(config, source_path)
    source_record, load_error = _load_single_jsonl_record(source_path)
    if load_error:
        return _blocked_payload(payload, [load_error])

    payload["source_promotion_status"] = str(
        source_record.get("promotion_status", "unknown")
    )
    blockers = _validate_source_promotion_packet(source_record, config.symbol)
    if blockers:
        return _blocked_payload(payload, blockers)

    known_delta_slices = _payload_string_tuple(
        source_record.get("drawdown_conclusion_changes")
    )
    payload.update(
        {
            "manifest_status": _MANIFEST_ACTIVE_STATUS,
            "source_promotion_packet_valid": True,
            "source_promotion_status": _SOURCE_PROMOTION_STATUS,
            "preferred_baseline_active": True,
            "same_slice_counts": True,
            "same_slice_dates": True,
            "m417a_slice_counts_unchanged": True,
            "matched_total_interval_count": _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT,
            "return_conclusions_unchanged": True,
            "return_conclusion_changes": list(_EXPECTED_RETURN_CONCLUSION_CHANGES),
            "known_basis_delta_count": len(known_delta_slices),
            "known_basis_delta_slices": list(known_delta_slices),
            "basis_delta_review_required": True,
            "blockers": [],
        }
    )
    payload.update(_manifest_false_fields())
    return payload


def render_etf_sma_preferred_baseline_manifest_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_preferred_baseline_manifest_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        f"manifest_status: {payload['manifest_status']}",
        f"symbol: {payload['symbol']}",
        f"preferred_baseline: {payload['preferred_baseline']}",
        f"preferred_basis: {payload['preferred_basis']}",
        f"comparison_basis: {payload['comparison_basis']}",
        f"baseline_source_milestone: {payload['baseline_source_milestone']}",
        f"source_promotion_status: {payload['source_promotion_status']}",
        f"same_slice_counts: {_bool_text(payload.get('same_slice_counts'))}",
        f"same_slice_dates: {_bool_text(payload.get('same_slice_dates'))}",
        "m417a_slice_counts_unchanged: "
        f"{_bool_text(payload.get('m417a_slice_counts_unchanged'))}",
        "return_conclusions_unchanged: "
        f"{_bool_text(payload.get('return_conclusions_unchanged'))}",
        "known_basis_delta_slices: "
        f"{','.join(_payload_string_tuple(payload.get('known_basis_delta_slices')))}",
        "basis_delta_review_required: "
        f"{_bool_text(payload.get('basis_delta_review_required'))}",
        f"trade_recommendation: {payload['trade_recommendation']}",
        f"profit_claim: {payload['profit_claim']}",
    ]
    blockers = _payload_string_tuple(payload.get("blockers"))
    if blockers:
        lines.append(f"blockers: {','.join(blockers)}")
    return "\n".join(lines)


def write_etf_sma_preferred_baseline_manifest_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_preferred_baseline_manifest_json(payload) + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaPreferredBaselineManifestConfig,
    source_path: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "manifest_status": _MANIFEST_BLOCKED_STATUS,
        "preferred_baseline": _PREFERRED_BASELINE,
        "preferred_basis": _PREFERRED_BASIS,
        "comparison_basis": _COMPARISON_BASIS,
        "baseline_source_milestone": _BASELINE_SOURCE_MILESTONE,
        "source_promotion_packet": str(source_path),
        "source_promotion_packet_valid": False,
        "source_promotion_status": "unknown",
        "preferred_baseline_active": False,
        "legacy_raw_basis": _LEGACY_RAW_BASIS,
        "legacy_raw_baseline_status": _LEGACY_RAW_BASELINE_STATUS,
        "same_slice_counts": False,
        "same_slice_dates": False,
        "m417a_slice_counts_unchanged": False,
        "matched_total_interval_count": 0,
        "return_conclusions_unchanged": False,
        "return_conclusion_changes": [],
        "known_basis_delta_count": 0,
        "known_basis_delta_slices": [],
        "basis_delta_review_required": False,
        "downstream_use": _DOWNSTREAM_USE,
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
    payload.update(_manifest_false_fields())
    return payload


def _blocked_payload(
    payload: dict[str, object],
    blockers: Sequence[str],
) -> dict[str, object]:
    clean_blockers = [str(blocker) for blocker in blockers if str(blocker)]
    payload.update(
        {
            "manifest_status": _MANIFEST_BLOCKED_STATUS,
            "source_promotion_packet_valid": False,
            "preferred_baseline_active": False,
            "blockers": clean_blockers,
            "blocked_reason": clean_blockers[0] if clean_blockers else "blocked",
            "trade_recommendation": "none",
            "operator_trade_recommendation": "none",
            "profit_claim": "none",
        }
    )
    payload.update(_manifest_false_fields())
    return payload


def _load_single_jsonl_record(path: Path) -> tuple[dict[str, object], str | None]:
    if not path.exists():
        return {}, "source_promotion_packet_not_found"

    records: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}, "source_promotion_packet_unreadable"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            return {}, "source_promotion_packet_invalid_json"
        if not isinstance(decoded, dict):
            return {}, "source_promotion_packet_record_not_object"
        records.append(decoded)

    if not records:
        return {}, "source_promotion_packet_empty"
    if len(records) != 1:
        return {}, "ambiguous_source_promotion_packet_record_count"
    return records[0], None


def _validate_source_promotion_packet(
    source_record: Mapping[str, object],
    symbol: str,
) -> list[str]:
    blockers: list[str] = []
    if source_record.get("record_type") != _SOURCE_RECORD_TYPE:
        blockers.append("source_promotion_packet_record_type_mismatch")
    if source_record.get("milestone") != _BASELINE_SOURCE_MILESTONE:
        blockers.append("source_promotion_packet_milestone_not_m421")
    if source_record.get("symbol") != symbol:
        blockers.append("source_promotion_packet_symbol_mismatch")
    if source_record.get("promotion_status") != _SOURCE_PROMOTION_STATUS:
        blockers.append("source_promotion_status_not_ready")
    if source_record.get("baseline_recommendation") != _PREFERRED_BASELINE:
        blockers.append("source_baseline_recommendation_not_adjusted_matched_window")
    if source_record.get("comparison_basis") != _COMPARISON_BASIS:
        blockers.append("source_comparison_basis_not_matched_window")
    if source_record.get("raw_basis") != _LEGACY_RAW_BASIS:
        blockers.append("source_raw_basis_not_raw_close")
    if source_record.get("adjusted_basis") != _PREFERRED_BASIS:
        blockers.append("source_adjusted_basis_not_adjusted_close")
    if source_record.get("preferred_offline_baseline_ready") is not True:
        blockers.append("source_preferred_offline_baseline_not_ready")
    if source_record.get("same_slice_counts") is not True:
        blockers.append("source_same_slice_counts_not_true")
    if source_record.get("same_slice_dates") is not True:
        blockers.append("source_same_slice_dates_not_true")
    if source_record.get("m417a_slice_counts_unchanged") is not True:
        blockers.append("source_m417a_slice_counts_not_unchanged")
    if _mapping_int(source_record, "matched_total_interval_count") != (
        _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT
    ):
        blockers.append("source_matched_total_interval_count_mismatch")
    if source_record.get("return_conclusions_unchanged") is not True:
        blockers.append("source_return_conclusions_not_unchanged")
    if _payload_string_tuple(source_record.get("return_conclusion_changes")) != (
        _EXPECTED_RETURN_CONCLUSION_CHANGES
    ):
        blockers.append("source_return_conclusion_changes_not_empty")
    if _payload_string_tuple(source_record.get("drawdown_conclusion_changes")) != (
        _EXPECTED_KNOWN_BASIS_DELTA_SLICES
    ):
        blockers.append("source_drawdown_conclusion_changes_mismatch")
    if source_record.get("basis_delta_review_required") is not True:
        blockers.append("source_basis_delta_review_not_required")

    blockers.extend(_validate_source_safety(source_record))
    return blockers


def _validate_source_safety(source_record: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    for field_name in _SOURCE_REQUIRED_FALSE_FIELDS:
        if field_name not in source_record:
            blockers.append(f"source_safety_flag_missing_{field_name}")
        elif source_record.get(field_name) is not False:
            blockers.append(f"source_safety_flag_dirty_{field_name}")

    for field_name in _SOURCE_NONE_FIELDS:
        if source_record.get(field_name) != "none":
            blockers.append(f"source_{field_name}_not_none")

    if source_record.get("no_trade_recommendation") is not True:
        blockers.append("source_no_trade_recommendation_not_true")
    if source_record.get("not_live_authorized") is not True:
        blockers.append("source_not_live_authorized_not_true")
    if source_record.get("broker_mutation_status") != "none":
        blockers.append("source_broker_mutation_status_not_none")
    if source_record.get("network_broker_access_status") != "not_attempted":
        blockers.append("source_network_access_status_not_not_attempted")
    if source_record.get("credential_access_status") != "not_attempted":
        blockers.append("source_credential_access_status_not_not_attempted")
    return blockers


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


def _manifest_false_fields() -> dict[str, bool]:
    return {field_name: False for field_name in _MANIFEST_FALSE_FIELDS}


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
