"""Offline M426 authorized preferred-baseline ETF/SMA comparison summary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

__all__ = [
    "DEFAULT_AUTHORIZATION_CONSUMED_COMPARISON_STUB_PATH",
    "DEFAULT_AUTHORIZED_PREFERRED_BASELINE_COMPARISON_SUMMARY_PATH",
    "EtfSmaAuthorizedComparisonSummaryConfig",
    "build_etf_sma_authorized_comparison_summary",
    "render_etf_sma_authorized_comparison_summary_json",
    "render_etf_sma_authorized_comparison_summary_text",
    "write_etf_sma_authorized_comparison_summary_jsonl",
]


DEFAULT_AUTHORIZATION_CONSUMED_COMPARISON_STUB_PATH = (
    Path("runs")
    / "paper_lab"
    / "m425_authorization_consumed_etf_sma_comparison_stub.jsonl"
)
DEFAULT_AUTHORIZED_PREFERRED_BASELINE_COMPARISON_SUMMARY_PATH = (
    Path("runs")
    / "paper_lab"
    / "m426_authorized_preferred_baseline_comparison_summary.jsonl"
)


@dataclass(frozen=True)
class EtfSmaAuthorizedComparisonSummaryConfig:
    """Configuration for the offline M426 authorized comparison summary."""

    run_id: str
    symbol: str
    stub_path: str | Path = DEFAULT_AUTHORIZATION_CONSUMED_COMPARISON_STUB_PATH


_COMMAND = "etf-sma-authorized-comparison-summary"
_RECORD_TYPE = "etf_sma_authorized_preferred_baseline_comparison_summary"
_SCHEMA_VERSION = "1"
_MILESTONE = "M426"
_STUB_SOURCE_MILESTONE = "M425"
_AUTHORIZED_STATUS = "authorized_preferred_baseline_summary_evaluated"
_BLOCKED_STATUS = "blocked_authorized_stub_required"
_INPUT_STUB_STATUS = "authorized_comparison_stub_evaluated"
_EXPECTED_SYMBOL = "SPY"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_COMPARISON_BASIS = "matched_window"
_EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT = 1055
_EXPECTED_KNOWN_BASIS_DELTA_SLICES = ("recovery_2023",)
_BASELINE_SOURCE_MILESTONE = "M422"
_GUARD_SOURCE_MILESTONE = "M423"
_AUTHORIZATION_SOURCE_MILESTONE = "M424"
_SUMMARY_SCOPE = "authorized_stub_only"
_STUB_REQUIRED_STRING_FIELDS = (
    ("comparison_stub_status", _INPUT_STUB_STATUS),
    ("active_preferred_baseline", _PREFERRED_BASELINE),
    ("active_preferred_basis", _PREFERRED_BASIS),
    ("comparison_basis", _COMPARISON_BASIS),
    ("baseline_source_milestone", _BASELINE_SOURCE_MILESTONE),
    ("guard_source_milestone", _GUARD_SOURCE_MILESTONE),
    ("authorization_source_milestone", _AUTHORIZATION_SOURCE_MILESTONE),
    ("milestone", _STUB_SOURCE_MILESTONE),
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


def build_etf_sma_authorized_comparison_summary(
    config: EtfSmaAuthorizedComparisonSummaryConfig,
) -> dict[str, object]:
    """Build one fail-closed summary from an authorized M425 comparison stub."""

    stub_path = Path(config.stub_path)
    payload = _base_payload(config, stub_path)
    blockers: list[str] = []
    if config.symbol != _EXPECTED_SYMBOL:
        blockers.append("unsupported_symbol")

    stub_record, load_blockers = _load_single_stub_record(stub_path)
    blockers.extend(load_blockers)
    if stub_record is not None:
        blockers.extend(_validate_stub_record(stub_record, config.symbol))

    if blockers:
        return _blocked_payload(payload, blockers)

    if stub_record is None:
        return _blocked_payload(payload, ("comparison_stub_artifact_empty",))

    known_basis_delta_slices = list(
        _payload_string_tuple(stub_record.get("known_basis_delta_slices"))
    )
    payload.update(
        {
            "comparison_summary_status": _AUTHORIZED_STATUS,
            "input_stub_status": stub_record["comparison_stub_status"],
            "downstream_comparison_authorized": True,
            "summary_performed": True,
            "summary_scope": _SUMMARY_SCOPE,
            "active_preferred_baseline": stub_record["active_preferred_baseline"],
            "active_preferred_basis": stub_record["active_preferred_basis"],
            "comparison_basis": stub_record["comparison_basis"],
            "matched_total_interval_count": stub_record[
                "matched_total_interval_count"
            ],
            "known_basis_delta_slices": known_basis_delta_slices,
            "known_basis_delta_slice_count": len(known_basis_delta_slices),
            "baseline_source_milestone": stub_record["baseline_source_milestone"],
            "guard_source_milestone": stub_record["guard_source_milestone"],
            "authorization_source_milestone": stub_record[
                "authorization_source_milestone"
            ],
            "stub_source_milestone": _STUB_SOURCE_MILESTONE,
            "metrics_recomputed": False,
            "new_performance_metrics_computed": False,
            "trade_recommendation": "none",
            "profit_claim": "none",
            "blockers": [],
        }
    )
    payload.update(_safety_false_fields())
    return payload


def render_etf_sma_authorized_comparison_summary_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_authorized_comparison_summary_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        f"comparison_summary_status: {payload['comparison_summary_status']}",
        "downstream_comparison_authorized: "
        f"{_bool_text(payload.get('downstream_comparison_authorized'))}",
        f"summary_performed: {_bool_text(payload.get('summary_performed'))}",
        f"symbol: {payload['symbol']}",
        f"stub_path: {payload['stub_path']}",
    ]
    if payload.get("summary_performed") is True:
        lines.extend(
            [
                f"input_stub_status: {payload['input_stub_status']}",
                "active_preferred_baseline: "
                f"{payload['active_preferred_baseline']}",
                f"active_preferred_basis: {payload['active_preferred_basis']}",
                f"comparison_basis: {payload['comparison_basis']}",
                "known_basis_delta_slices: "
                f"{','.join(_payload_string_tuple(payload.get('known_basis_delta_slices')))}",
            ]
        )

    blockers = _payload_string_tuple(payload.get("blockers"))
    if blockers:
        lines.append(f"blockers: {','.join(blockers)}")

    lines.extend(
        [
            f"summary_scope: {payload['summary_scope']}",
            f"metrics_recomputed: {_bool_text(payload.get('metrics_recomputed'))}",
            "new_performance_metrics_computed: "
            f"{_bool_text(payload.get('new_performance_metrics_computed'))}",
            f"trade_recommendation: {payload['trade_recommendation']}",
            f"profit_claim: {payload['profit_claim']}",
        ]
    )
    return "\n".join(lines)


def write_etf_sma_authorized_comparison_summary_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_authorized_comparison_summary_json(payload) + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaAuthorizedComparisonSummaryConfig,
    stub_path: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "stub_path": str(stub_path),
        "comparison_summary_status": _BLOCKED_STATUS,
        "downstream_comparison_authorized": False,
        "summary_performed": False,
        "summary_scope": _SUMMARY_SCOPE,
        "metrics_recomputed": False,
        "new_performance_metrics_computed": False,
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
            "comparison_summary_status": _BLOCKED_STATUS,
            "downstream_comparison_authorized": False,
            "summary_performed": False,
            "blockers": clean_blockers,
            "blocked_reason": clean_blockers[0] if clean_blockers else "blocked",
            "metrics_recomputed": False,
            "new_performance_metrics_computed": False,
            "trade_recommendation": "none",
            "operator_trade_recommendation": "none",
            "profit_claim": "none",
        }
    )
    payload.update(_safety_false_fields())
    return payload


def _load_single_stub_record(
    path: Path,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if not path.exists():
        return None, ("comparison_stub_artifact_not_found",)
    if not path.is_file():
        return None, ("comparison_stub_artifact_path_not_file",)

    records: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, ("comparison_stub_artifact_unreadable",)

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            return None, (f"comparison_stub_artifact_invalid_json_line_{line_number}",)
        if not isinstance(decoded, dict):
            return None, (f"comparison_stub_artifact_record_{line_number}_not_object",)
        records.append(decoded)

    if not records:
        return None, ("comparison_stub_artifact_empty",)
    if len(records) != 1:
        return None, ("ambiguous_comparison_stub_artifact_record_count",)
    return records[0], ()


def _validate_stub_record(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    symbol_blocker = _validate_expected_string_field(record, "symbol", symbol)
    if symbol_blocker is not None:
        blockers.append(symbol_blocker)

    for field_name, expected in _STUB_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(record, field_name, expected)
        if blocker is not None:
            blockers.append(blocker)

    for field_name in ("downstream_comparison_authorized", "evaluation_performed"):
        blocker = _validate_required_true_field(record, field_name)
        if blocker is not None:
            blockers.append(blocker)

    count_blocker = _validate_expected_int_field(
        record,
        "matched_total_interval_count",
        _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT,
    )
    if count_blocker is not None:
        blockers.append(count_blocker)

    slices_blocker = _validate_expected_string_list_field(
        record,
        "known_basis_delta_slices",
        _EXPECTED_KNOWN_BASIS_DELTA_SLICES,
    )
    if slices_blocker is not None:
        blockers.append(slices_blocker)

    for field_name in _SAFETY_FALSE_FIELDS:
        blocker = _validate_false_safety_field(record, field_name)
        if blocker is not None:
            blockers.append(blocker)

    return tuple(blockers)


def _validate_expected_string_field(
    record: Mapping[str, object],
    field_name: str,
    expected: str,
) -> str | None:
    if field_name not in record:
        return f"comparison_stub_missing_{field_name}"
    value = record[field_name]
    if type(value) is not str:
        return f"comparison_stub_malformed_{field_name}"
    if value != expected:
        return f"comparison_stub_unexpected_{field_name}"
    return None


def _validate_required_true_field(
    record: Mapping[str, object],
    field_name: str,
) -> str | None:
    if field_name not in record:
        return f"comparison_stub_missing_{field_name}"
    value = record[field_name]
    if value is not True and value is not False:
        return f"comparison_stub_malformed_{field_name}"
    if value is not True:
        return f"comparison_stub_{field_name}_not_true"
    return None


def _validate_expected_int_field(
    record: Mapping[str, object],
    field_name: str,
    expected: int,
) -> str | None:
    if field_name not in record:
        return f"comparison_stub_missing_{field_name}"
    value = record[field_name]
    if type(value) is not int:
        return f"comparison_stub_malformed_{field_name}"
    if value != expected:
        return f"comparison_stub_unexpected_{field_name}"
    return None


def _validate_expected_string_list_field(
    record: Mapping[str, object],
    field_name: str,
    expected: tuple[str, ...],
) -> str | None:
    if field_name not in record:
        return f"comparison_stub_missing_{field_name}"
    value = record[field_name]
    if type(value) is not list or any(type(item) is not str for item in value):
        return f"comparison_stub_malformed_{field_name}"
    if tuple(value) != expected:
        return f"comparison_stub_unexpected_{field_name}"
    return None


def _validate_false_safety_field(
    record: Mapping[str, object],
    field_name: str,
) -> str | None:
    if field_name not in record:
        return f"comparison_stub_safety_flag_missing_{field_name}"
    value = record[field_name]
    if value is True:
        return f"comparison_stub_safety_flag_dirty_{field_name}"
    if value is not False:
        return f"comparison_stub_safety_flag_malformed_{field_name}"
    return None


def _safety_false_fields() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
