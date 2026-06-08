"""Offline M428 authorized adjusted-baseline ETF/SMA backtest snapshot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

__all__ = [
    "DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_SNAPSHOT_PATH",
    "DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_METRICS_MATERIALIZATION_PATH",
    "EtfSmaAuthorizedAdjustedBaselineBacktestSnapshotConfig",
    "build_etf_sma_authorized_adjusted_baseline_backtest_snapshot",
    "render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_json",
    "render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_text",
    "write_etf_sma_authorized_adjusted_baseline_backtest_snapshot_jsonl",
]


DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_METRICS_MATERIALIZATION_PATH = (
    Path("runs")
    / "paper_lab"
    / "m427_authorized_adjusted_baseline_metrics_materialization.jsonl"
)
DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_SNAPSHOT_PATH = (
    Path("runs")
    / "paper_lab"
    / "m428_authorized_adjusted_baseline_backtest_snapshot.jsonl"
)


@dataclass(frozen=True)
class EtfSmaAuthorizedAdjustedBaselineBacktestSnapshotConfig:
    """Configuration for the offline M428 backtest snapshot."""

    run_id: str
    symbol: str
    metrics_path: (
        str | Path
    ) = DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_METRICS_MATERIALIZATION_PATH


_COMMAND = "etf-sma-authorized-adjusted-baseline-backtest-snapshot"
_RECORD_TYPE = "etf_sma_authorized_adjusted_baseline_backtest_snapshot"
_SCHEMA_VERSION = "1"
_MILESTONE = "M428"
_METRICS_SOURCE_MILESTONE = "M427"
_MATERIALIZED_STATUS = (
    "authorized_adjusted_baseline_backtest_snapshot_materialized"
)
_BLOCKED_STATUS = "blocked_authorized_metrics_required"
_INPUT_METRICS_STATUS = "authorized_adjusted_baseline_metrics_materialized"
_INPUT_SUMMARY_STATUS = "authorized_preferred_baseline_summary_evaluated"
_EXPECTED_SYMBOL = "SPY"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_COMPARISON_BASIS = "matched_window"
_EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT = 1055
_EXPECTED_KNOWN_BASIS_DELTA_SLICES = ("recovery_2023",)
_BASELINE_SOURCE_MILESTONE = "M422"
_GUARD_SOURCE_MILESTONE = "M423"
_AUTHORIZATION_SOURCE_MILESTONE = "M424"
_STUB_SOURCE_MILESTONE = "M425"
_SUMMARY_SOURCE_MILESTONE = "M426"
_SOURCE_EVIDENCE_MILESTONE = "M421"
_SNAPSHOT_SCOPE = "authorized_adjusted_baseline_metrics_only"
_METRICS_REQUIRED_STRING_FIELDS = (
    ("milestone", _METRICS_SOURCE_MILESTONE),
    ("metrics_materialization_status", _INPUT_METRICS_STATUS),
    ("input_summary_status", _INPUT_SUMMARY_STATUS),
    ("metrics_source_basis", _PREFERRED_BASIS),
    ("active_preferred_baseline", _PREFERRED_BASELINE),
    ("active_preferred_basis", _PREFERRED_BASIS),
    ("comparison_basis", _COMPARISON_BASIS),
    ("baseline_source_milestone", _BASELINE_SOURCE_MILESTONE),
    ("guard_source_milestone", _GUARD_SOURCE_MILESTONE),
    ("authorization_source_milestone", _AUTHORIZATION_SOURCE_MILESTONE),
    ("stub_source_milestone", _STUB_SOURCE_MILESTONE),
    ("summary_source_milestone", _SUMMARY_SOURCE_MILESTONE),
    ("source_evidence_milestone", _SOURCE_EVIDENCE_MILESTONE),
    ("trade_recommendation", "none"),
    ("profit_claim", "none"),
)
_METRICS_TRUE_FIELDS = (
    "downstream_comparison_authorized",
    "metrics_materialized",
)
_METRICS_FALSE_FIELDS = (
    "metrics_recomputed",
    "new_market_data_loaded",
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_OPTIONAL_NORMALIZED_METRIC_FIELDS = (
    "full_window_return_deltas",
    "matched_slice_comparisons",
    "basis_delta_explanations",
    "return_conclusion_changes",
    "return_conclusions_unchanged",
    "drawdown_conclusion_changes",
    "basis_delta_review_required",
    "matched_evaluated_return_count",
    "full_adjusted_history_evaluated_return_count",
)


def build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
    config: EtfSmaAuthorizedAdjustedBaselineBacktestSnapshotConfig,
) -> dict[str, object]:
    """Build one fail-closed backtest snapshot from authorized M427 metrics."""

    metrics_path = Path(config.metrics_path)
    payload = _base_payload(config, metrics_path)
    blockers: list[str] = []
    if config.symbol != _EXPECTED_SYMBOL:
        blockers.append("unsupported_symbol")

    metrics_record, metrics_blockers = _load_single_jsonl_record(
        metrics_path,
        "input_metrics",
    )
    blockers.extend(metrics_blockers)
    if metrics_record is not None:
        blockers.extend(_validate_metrics_record(metrics_record, config.symbol))

    if blockers:
        return _blocked_payload(payload, blockers)
    if metrics_record is None:
        return _blocked_payload(payload, ("input_metrics_artifact_empty",))

    normalized_metrics = _normalized_metric_payload(metrics_record)
    known_basis_delta_slices = list(
        _payload_string_tuple(metrics_record.get("known_basis_delta_slices"))
    )
    payload.update(
        {
            "backtest_snapshot_status": _MATERIALIZED_STATUS,
            "input_metrics_status": metrics_record[
                "metrics_materialization_status"
            ],
            "downstream_comparison_authorized": True,
            "backtest_snapshot_materialized": True,
            "active_preferred_baseline": metrics_record[
                "active_preferred_baseline"
            ],
            "active_preferred_basis": metrics_record["active_preferred_basis"],
            "comparison_basis": metrics_record["comparison_basis"],
            "matched_total_interval_count": metrics_record[
                "matched_total_interval_count"
            ],
            "known_basis_delta_slices": known_basis_delta_slices,
            "known_basis_delta_slice_count": len(known_basis_delta_slices),
            "baseline_source_milestone": metrics_record[
                "baseline_source_milestone"
            ],
            "guard_source_milestone": metrics_record["guard_source_milestone"],
            "authorization_source_milestone": metrics_record[
                "authorization_source_milestone"
            ],
            "stub_source_milestone": metrics_record["stub_source_milestone"],
            "summary_source_milestone": metrics_record["summary_source_milestone"],
            "metrics_source_milestone": _METRICS_SOURCE_MILESTONE,
            "source_evidence_milestone": metrics_record[
                "source_evidence_milestone"
            ],
            "snapshot_scope": _SNAPSHOT_SCOPE,
            "metrics_recomputed": False,
            "new_market_data_loaded": False,
            "trade_recommendation": "none",
            "profit_claim": "none",
            "blockers": [],
        }
    )
    payload.update(normalized_metrics)
    payload["normalized_metric_fields"] = sorted(normalized_metrics)
    payload.update(_safety_false_fields())
    return payload


def render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        "backtest_snapshot_status: "
        f"{payload['backtest_snapshot_status']}",
        "downstream_comparison_authorized: "
        f"{_bool_text(payload.get('downstream_comparison_authorized'))}",
        "backtest_snapshot_materialized: "
        f"{_bool_text(payload.get('backtest_snapshot_materialized'))}",
        f"symbol: {payload['symbol']}",
        f"input_metrics_path: {payload['input_metrics_path']}",
    ]
    if payload.get("backtest_snapshot_materialized") is True:
        lines.extend(
            [
                f"input_metrics_status: {payload['input_metrics_status']}",
                f"snapshot_scope: {payload['snapshot_scope']}",
                "normalized_metric_fields: "
                f"{','.join(_payload_string_tuple(payload.get('normalized_metric_fields')))}",
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


def write_etf_sma_authorized_adjusted_baseline_backtest_snapshot_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_json(payload)
        + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaAuthorizedAdjustedBaselineBacktestSnapshotConfig,
    metrics_path: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "input_metrics_path": str(metrics_path),
        "backtest_snapshot_status": _BLOCKED_STATUS,
        "downstream_comparison_authorized": False,
        "backtest_snapshot_materialized": False,
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
            "backtest_snapshot_status": _BLOCKED_STATUS,
            "downstream_comparison_authorized": False,
            "backtest_snapshot_materialized": False,
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


def _validate_metrics_record(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    symbol_blocker = _validate_expected_string_field(
        record,
        "symbol",
        symbol,
        "input_metrics",
    )
    if symbol_blocker is not None:
        blockers.append(symbol_blocker)

    for field_name, expected in _METRICS_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "input_metrics",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _METRICS_TRUE_FIELDS:
        blocker = _validate_required_true_field(
            record,
            field_name,
            "input_metrics",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _METRICS_FALSE_FIELDS:
        blocker = _validate_required_false_field(
            record,
            field_name,
            "input_metrics",
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
            "input_metrics",
        )
        if blocker is not None:
            blockers.append(blocker)

    slices_blocker = _validate_expected_string_list_field(
        record,
        "known_basis_delta_slices",
        _EXPECTED_KNOWN_BASIS_DELTA_SLICES,
        "input_metrics",
    )
    if slices_blocker is not None:
        blockers.append(slices_blocker)

    for field_name in _SAFETY_FALSE_FIELDS:
        blocker = _validate_false_safety_field(
            record,
            field_name,
            "input_metrics",
        )
        if blocker is not None:
            blockers.append(blocker)

    return tuple(blockers)


def _normalized_metric_payload(
    record: Mapping[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field_name in _OPTIONAL_NORMALIZED_METRIC_FIELDS:
        if field_name in record:
            payload[field_name] = _copy_json_value(record[field_name])
    return payload


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


def _validate_required_false_field(
    record: Mapping[str, object],
    field_name: str,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if value is not True and value is not False:
        return f"{prefix}_malformed_{field_name}"
    if value is not False:
        return f"{prefix}_{field_name}_not_false"
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


def _copy_json_value(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True))


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _safety_false_fields() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
