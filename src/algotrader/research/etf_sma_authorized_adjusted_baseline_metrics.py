"""Offline M427 authorized adjusted-baseline ETF/SMA metrics materialization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

__all__ = [
    "DEFAULT_ADJUSTED_BASIS_PROMOTION_PACKET_PATH",
    "DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_METRICS_MATERIALIZATION_PATH",
    "DEFAULT_AUTHORIZED_PREFERRED_BASELINE_COMPARISON_SUMMARY_PATH",
    "EtfSmaAuthorizedAdjustedBaselineMetricsConfig",
    "build_etf_sma_authorized_adjusted_baseline_metrics",
    "render_etf_sma_authorized_adjusted_baseline_metrics_json",
    "render_etf_sma_authorized_adjusted_baseline_metrics_text",
    "write_etf_sma_authorized_adjusted_baseline_metrics_jsonl",
]


DEFAULT_AUTHORIZED_PREFERRED_BASELINE_COMPARISON_SUMMARY_PATH = (
    Path("runs")
    / "paper_lab"
    / "m426_authorized_preferred_baseline_comparison_summary.jsonl"
)
DEFAULT_ADJUSTED_BASIS_PROMOTION_PACKET_PATH = (
    Path("runs") / "paper_lab" / "m421_spy_adjusted_basis_promotion_packet.jsonl"
)
DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_METRICS_MATERIALIZATION_PATH = (
    Path("runs")
    / "paper_lab"
    / "m427_authorized_adjusted_baseline_metrics_materialization.jsonl"
)


@dataclass(frozen=True)
class EtfSmaAuthorizedAdjustedBaselineMetricsConfig:
    """Configuration for the offline M427 metrics materialization."""

    run_id: str
    symbol: str
    summary_path: (
        str | Path
    ) = DEFAULT_AUTHORIZED_PREFERRED_BASELINE_COMPARISON_SUMMARY_PATH
    source_evidence_path: str | Path = DEFAULT_ADJUSTED_BASIS_PROMOTION_PACKET_PATH


_COMMAND = "etf-sma-authorized-adjusted-baseline-metrics"
_RECORD_TYPE = "etf_sma_authorized_adjusted_baseline_metrics_materialization"
_SCHEMA_VERSION = "1"
_MILESTONE = "M427"
_SUMMARY_SOURCE_MILESTONE = "M426"
_SOURCE_EVIDENCE_MILESTONE = "M421"
_MATERIALIZED_STATUS = "authorized_adjusted_baseline_metrics_materialized"
_BLOCKED_STATUS = "blocked_authorized_summary_required"
_INPUT_SUMMARY_STATUS = "authorized_preferred_baseline_summary_evaluated"
_INPUT_STUB_STATUS = "authorized_comparison_stub_evaluated"
_SOURCE_PROMOTION_STATUS = "ready_to_promote_adjusted_matched_window_basis"
_EXPECTED_SYMBOL = "SPY"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_RAW_BASIS = "raw_close_price_return"
_COMPARISON_BASIS = "matched_window"
_EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT = 1055
_EXPECTED_FULL_ADJUSTED_HISTORY_COUNT = 8195
_EXPECTED_KNOWN_BASIS_DELTA_SLICES = ("recovery_2023",)
_BASELINE_SOURCE_MILESTONE = "M422"
_GUARD_SOURCE_MILESTONE = "M423"
_AUTHORIZATION_SOURCE_MILESTONE = "M424"
_STUB_SOURCE_MILESTONE = "M425"
_MATERIALIZATION_SCOPE = "existing_local_evidence_only"
_SUMMARY_REQUIRED_STRING_FIELDS = (
    ("milestone", _SUMMARY_SOURCE_MILESTONE),
    ("comparison_summary_status", _INPUT_SUMMARY_STATUS),
    ("input_stub_status", _INPUT_STUB_STATUS),
    ("active_preferred_baseline", _PREFERRED_BASELINE),
    ("active_preferred_basis", _PREFERRED_BASIS),
    ("comparison_basis", _COMPARISON_BASIS),
    ("baseline_source_milestone", _BASELINE_SOURCE_MILESTONE),
    ("guard_source_milestone", _GUARD_SOURCE_MILESTONE),
    ("authorization_source_milestone", _AUTHORIZATION_SOURCE_MILESTONE),
    ("stub_source_milestone", _STUB_SOURCE_MILESTONE),
    ("trade_recommendation", "none"),
    ("profit_claim", "none"),
)
_SOURCE_EVIDENCE_REQUIRED_STRING_FIELDS = (
    ("milestone", _SOURCE_EVIDENCE_MILESTONE),
    ("promotion_status", _SOURCE_PROMOTION_STATUS),
    ("comparison_basis", _COMPARISON_BASIS),
    ("raw_basis", _RAW_BASIS),
    ("adjusted_basis", _PREFERRED_BASIS),
    ("baseline_recommendation", _PREFERRED_BASELINE),
    ("trade_recommendation", "none"),
    ("profit_claim", "none"),
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SOURCE_EVIDENCE_FALSE_FIELDS = (
    *_SAFETY_FALSE_FIELDS,
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
_EXPECTED_SLICE_NAMES = (
    "full_evaluated_window",
    "stress_2022",
    "recovery_2023",
    "bull_2024",
    "whipsaw_2025",
    "ytd_2026",
)
_SLICE_COMPARISON_REQUIRED_FIELDS = (
    "slice_name",
    "status",
    "same_evaluated_return_count",
    "same_slice_dates",
    "raw_evaluated_return_count",
    "adjusted_evaluated_return_count",
    "raw_strategy_total_return",
    "adjusted_strategy_total_return",
    "strategy_total_return_delta",
    "raw_benchmark_total_return",
    "adjusted_benchmark_total_return",
    "benchmark_total_return_delta",
    "raw_strategy_max_drawdown",
    "adjusted_strategy_max_drawdown",
    "strategy_max_drawdown_delta",
    "raw_benchmark_max_drawdown",
    "adjusted_benchmark_max_drawdown",
    "benchmark_max_drawdown_delta",
    "raw_return_conclusion",
    "adjusted_return_conclusion",
    "return_conclusion_unchanged",
    "raw_drawdown_conclusion",
    "adjusted_drawdown_conclusion",
    "drawdown_conclusion_unchanged",
)


def build_etf_sma_authorized_adjusted_baseline_metrics(
    config: EtfSmaAuthorizedAdjustedBaselineMetricsConfig,
) -> dict[str, object]:
    """Build one fail-closed metrics record from authorized local evidence."""

    summary_path = Path(config.summary_path)
    evidence_path = Path(config.source_evidence_path)
    payload = _base_payload(config, summary_path, evidence_path)
    blockers: list[str] = []
    if config.symbol != _EXPECTED_SYMBOL:
        blockers.append("unsupported_symbol")

    summary_record, summary_blockers = _load_single_jsonl_record(
        summary_path,
        "authorized_summary",
    )
    blockers.extend(summary_blockers)
    if summary_record is not None:
        blockers.extend(_validate_summary_record(summary_record, config.symbol))

    evidence_record: dict[str, object] | None = None
    metric_payload: dict[str, object] = {}
    metric_blockers: tuple[str, ...] = ()
    if not blockers:
        evidence_record, evidence_blockers = _load_single_jsonl_record(
            evidence_path,
            "source_evidence",
        )
        blockers.extend(evidence_blockers)
        if evidence_record is not None:
            blockers.extend(_validate_source_evidence_record(evidence_record))
            metric_payload, metric_blockers = _materialized_metric_payload(
                evidence_record
            )
            blockers.extend(metric_blockers)

    if blockers:
        return _blocked_payload(payload, blockers)

    if summary_record is None:
        return _blocked_payload(payload, ("authorized_summary_artifact_empty",))
    if evidence_record is None:
        return _blocked_payload(payload, ("source_evidence_artifact_empty",))
    if not metric_payload:
        return _blocked_payload(payload, ("source_evidence_metrics_not_materialized",))

    known_basis_delta_slices = list(
        _payload_string_tuple(summary_record.get("known_basis_delta_slices"))
    )
    payload.update(
        {
            "metrics_materialization_status": _MATERIALIZED_STATUS,
            "input_summary_status": summary_record["comparison_summary_status"],
            "downstream_comparison_authorized": True,
            "metrics_materialized": True,
            "metrics_materialization_scope": _MATERIALIZATION_SCOPE,
            "metrics_source_basis": _PREFERRED_BASIS,
            "active_preferred_baseline": summary_record[
                "active_preferred_baseline"
            ],
            "active_preferred_basis": summary_record["active_preferred_basis"],
            "comparison_basis": summary_record["comparison_basis"],
            "matched_total_interval_count": summary_record[
                "matched_total_interval_count"
            ],
            "known_basis_delta_slices": known_basis_delta_slices,
            "known_basis_delta_slice_count": len(known_basis_delta_slices),
            "baseline_source_milestone": summary_record[
                "baseline_source_milestone"
            ],
            "guard_source_milestone": summary_record["guard_source_milestone"],
            "authorization_source_milestone": summary_record[
                "authorization_source_milestone"
            ],
            "stub_source_milestone": summary_record["stub_source_milestone"],
            "summary_source_milestone": _SUMMARY_SOURCE_MILESTONE,
            "source_evidence_milestone": _SOURCE_EVIDENCE_MILESTONE,
            "source_evidence_status": evidence_record["promotion_status"],
            "metrics_recomputed": False,
            "new_market_data_loaded": False,
            "trade_recommendation": "none",
            "profit_claim": "none",
            "blockers": [],
        }
    )
    payload.update(metric_payload)
    payload["metrics_materialized_fields"] = sorted(metric_payload)
    payload.update(_safety_false_fields())
    return payload


def render_etf_sma_authorized_adjusted_baseline_metrics_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_authorized_adjusted_baseline_metrics_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        "metrics_materialization_status: "
        f"{payload['metrics_materialization_status']}",
        "downstream_comparison_authorized: "
        f"{_bool_text(payload.get('downstream_comparison_authorized'))}",
        f"metrics_materialized: {_bool_text(payload.get('metrics_materialized'))}",
        f"symbol: {payload['symbol']}",
        f"summary_path: {payload['summary_path']}",
        f"source_evidence_path: {payload['source_evidence_path']}",
    ]
    if payload.get("metrics_materialized") is True:
        lines.extend(
            [
                f"input_summary_status: {payload['input_summary_status']}",
                "metrics_source_basis: "
                f"{payload['metrics_source_basis']}",
                "source_evidence_milestone: "
                f"{payload['source_evidence_milestone']}",
                "metrics_materialized_fields: "
                f"{','.join(_payload_string_tuple(payload.get('metrics_materialized_fields')))}",
            ]
        )

    blockers = _payload_string_tuple(payload.get("blockers"))
    if blockers:
        lines.append(f"blockers: {','.join(blockers)}")

    lines.extend(
        [
            f"metrics_recomputed: {_bool_text(payload.get('metrics_recomputed'))}",
            "new_market_data_loaded: "
            f"{_bool_text(payload.get('new_market_data_loaded'))}",
            f"trade_recommendation: {payload['trade_recommendation']}",
            f"profit_claim: {payload['profit_claim']}",
        ]
    )
    return "\n".join(lines)


def write_etf_sma_authorized_adjusted_baseline_metrics_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_authorized_adjusted_baseline_metrics_json(payload) + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaAuthorizedAdjustedBaselineMetricsConfig,
    summary_path: Path,
    evidence_path: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "summary_path": str(summary_path),
        "source_evidence_path": str(evidence_path),
        "metrics_materialization_status": _BLOCKED_STATUS,
        "downstream_comparison_authorized": False,
        "metrics_materialized": False,
        "metrics_recomputed": False,
        "new_market_data_loaded": False,
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
            "metrics_materialization_status": _BLOCKED_STATUS,
            "downstream_comparison_authorized": False,
            "metrics_materialized": False,
            "blockers": clean_blockers,
            "blocked_reason": clean_blockers[0] if clean_blockers else "blocked",
            "metrics_recomputed": False,
            "new_market_data_loaded": False,
            "trade_recommendation": "none",
            "operator_trade_recommendation": "none",
            "profit_claim": "none",
        }
    )
    payload.update(_safety_false_fields())
    return payload


def _load_single_jsonl_record(
    path: Path,
    artifact_name: str,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if not path.exists():
        return None, (f"{artifact_name}_artifact_not_found",)
    if not path.is_file():
        return None, (f"{artifact_name}_artifact_path_not_file",)

    records: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, (f"{artifact_name}_artifact_unreadable",)

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            return None, (
                f"{artifact_name}_artifact_invalid_json_line_{line_number}",
            )
        if not isinstance(decoded, dict):
            return None, (
                f"{artifact_name}_artifact_record_{line_number}_not_object",
            )
        records.append(decoded)

    if not records:
        return None, (f"{artifact_name}_artifact_empty",)
    if len(records) != 1:
        return None, (f"ambiguous_{artifact_name}_artifact_record_count",)
    return records[0], ()


def _validate_summary_record(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    symbol_blocker = _validate_expected_string_field(
        record,
        "symbol",
        symbol,
        "authorized_summary",
    )
    if symbol_blocker is not None:
        blockers.append(symbol_blocker)

    for field_name, expected in _SUMMARY_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "authorized_summary",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in ("downstream_comparison_authorized", "summary_performed"):
        blocker = _validate_required_true_field(
            record,
            field_name,
            "authorized_summary",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name, expected in (
        ("matched_total_interval_count", _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT),
        ("known_basis_delta_slice_count", len(_EXPECTED_KNOWN_BASIS_DELTA_SLICES)),
    ):
        blocker = _validate_expected_int_field(
            record,
            field_name,
            expected,
            "authorized_summary",
        )
        if blocker is not None:
            blockers.append(blocker)

    slices_blocker = _validate_expected_string_list_field(
        record,
        "known_basis_delta_slices",
        _EXPECTED_KNOWN_BASIS_DELTA_SLICES,
        "authorized_summary",
    )
    if slices_blocker is not None:
        blockers.append(slices_blocker)

    for field_name in _SAFETY_FALSE_FIELDS:
        blocker = _validate_false_safety_field(
            record,
            field_name,
            "authorized_summary",
        )
        if blocker is not None:
            blockers.append(blocker)

    return tuple(blockers)


def _validate_source_evidence_record(record: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    symbol_blocker = _validate_expected_string_field(
        record,
        "symbol",
        _EXPECTED_SYMBOL,
        "source_evidence",
    )
    if symbol_blocker is not None:
        blockers.append(symbol_blocker)

    for field_name, expected in _SOURCE_EVIDENCE_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "source_evidence",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in (
        "preferred_offline_baseline_ready",
        "same_slice_counts",
        "same_slice_dates",
        "m417a_slice_counts_unchanged",
        "return_conclusions_unchanged",
        "basis_delta_review_required",
    ):
        blocker = _validate_required_true_field(
            record,
            field_name,
            "source_evidence",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name, expected in (
        ("matched_total_interval_count", _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT),
        ("matched_evaluated_return_count", _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT),
        (
            "full_adjusted_history_evaluated_return_count",
            _EXPECTED_FULL_ADJUSTED_HISTORY_COUNT,
        ),
    ):
        blocker = _validate_expected_int_field(
            record,
            field_name,
            expected,
            "source_evidence",
        )
        if blocker is not None:
            blockers.append(blocker)

    slices_blocker = _validate_expected_string_list_field(
        record,
        "drawdown_conclusion_changes",
        _EXPECTED_KNOWN_BASIS_DELTA_SLICES,
        "source_evidence",
    )
    if slices_blocker is not None:
        blockers.append(slices_blocker)

    return_changes_blocker = _validate_expected_string_list_field(
        record,
        "return_conclusion_changes",
        (),
        "source_evidence",
    )
    if return_changes_blocker is not None:
        blockers.append(return_changes_blocker)

    for field_name in _SOURCE_EVIDENCE_FALSE_FIELDS:
        blocker = _validate_false_safety_field(
            record,
            field_name,
            "source_evidence",
        )
        if blocker is not None:
            blockers.append(blocker)

    return tuple(blockers)


def _materialized_metric_payload(
    record: Mapping[str, object],
) -> tuple[dict[str, object], tuple[str, ...]]:
    payload: dict[str, object] = {}
    blockers: list[str] = []

    for field_name in (
        "matched_evaluated_return_count",
        "full_adjusted_history_evaluated_return_count",
    ):
        value = record.get(field_name)
        if type(value) is int:
            payload[field_name] = value
        else:
            blockers.append(f"source_evidence_metric_missing_{field_name}")

    for field_name in (
        "return_conclusions_unchanged",
        "basis_delta_review_required",
    ):
        value = record.get(field_name)
        if type(value) is bool:
            payload[field_name] = value
        else:
            blockers.append(f"source_evidence_metric_missing_{field_name}")

    for field_name in (
        "return_conclusion_changes",
        "drawdown_conclusion_changes",
    ):
        value = record.get(field_name)
        if type(value) is list and all(type(item) is str for item in value):
            payload[field_name] = list(value)
        else:
            blockers.append(f"source_evidence_metric_missing_{field_name}")

    full_window_deltas = _payload_mapping(record.get("full_window_return_deltas"))
    if full_window_deltas:
        payload["full_window_return_deltas"] = _copy_json_mapping(
            full_window_deltas
        )
    else:
        blockers.append("source_evidence_metric_missing_full_window_return_deltas")

    matched_slice_comparisons = _payload_mapping_list(
        record,
        "matched_slice_comparisons",
    )
    matched_slice_names = tuple(
        str(item.get("slice_name", "")) for item in matched_slice_comparisons
    )
    if matched_slice_names != _EXPECTED_SLICE_NAMES:
        blockers.append("source_evidence_metric_unexpected_matched_slice_comparisons")
    elif not _slice_comparisons_complete(matched_slice_comparisons):
        blockers.append("source_evidence_metric_incomplete_matched_slice_comparisons")
    else:
        payload["matched_slice_comparisons"] = [
            _copy_json_mapping(item) for item in matched_slice_comparisons
        ]

    basis_delta_explanations = _payload_mapping_list(
        record,
        "basis_delta_explanations",
    )
    if basis_delta_explanations:
        payload["basis_delta_explanations"] = [
            _copy_json_mapping(item) for item in basis_delta_explanations
        ]

    return payload, tuple(blockers)


def _validate_expected_string_field(
    record: Mapping[str, object],
    field_name: str,
    expected: str,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if type(value) is not str:
        return f"{prefix}_malformed_{field_name}"
    if value != expected:
        return f"{prefix}_unexpected_{field_name}"
    return None


def _validate_required_true_field(
    record: Mapping[str, object],
    field_name: str,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if value is not True and value is not False:
        return f"{prefix}_malformed_{field_name}"
    if value is not True:
        return f"{prefix}_{field_name}_not_true"
    return None


def _validate_expected_int_field(
    record: Mapping[str, object],
    field_name: str,
    expected: int,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if type(value) is not int:
        return f"{prefix}_malformed_{field_name}"
    if value != expected:
        return f"{prefix}_unexpected_{field_name}"
    return None


def _validate_expected_string_list_field(
    record: Mapping[str, object],
    field_name: str,
    expected: tuple[str, ...],
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if type(value) is not list or any(type(item) is not str for item in value):
        return f"{prefix}_malformed_{field_name}"
    if tuple(value) != expected:
        return f"{prefix}_unexpected_{field_name}"
    return None


def _validate_false_safety_field(
    record: Mapping[str, object],
    field_name: str,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_safety_flag_missing_{field_name}"
    value = record[field_name]
    if value is True:
        return f"{prefix}_safety_flag_dirty_{field_name}"
    if value is not False:
        return f"{prefix}_safety_flag_malformed_{field_name}"
    return None


def _slice_comparisons_complete(
    records: Sequence[Mapping[str, object]],
) -> bool:
    for record in records:
        if any(field_name not in record for field_name in _SLICE_COMPARISON_REQUIRED_FIELDS):
            return False
    return True


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


def _copy_json_mapping(value: Mapping[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(dict(value), sort_keys=True))


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _safety_false_fields() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
