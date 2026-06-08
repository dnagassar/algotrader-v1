"""Offline M429 authorized adjusted-baseline ETF/SMA backtest replay."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_backtest_stats import (
    EtfSmaAdjustedBasisValidationConfig,
    build_etf_sma_adjusted_basis_validation,
)

__all__ = [
    "DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_REPLAY_PATH",
    "DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_SNAPSHOT_PATH",
    "DEFAULT_M417_SOURCE_ARTIFACT_PATH",
    "DEFAULT_THRU_M420_ADJUSTED_DAILY_BARS_CSV_PATH",
    "EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig",
    "build_etf_sma_authorized_adjusted_baseline_backtest_replay",
    "render_etf_sma_authorized_adjusted_baseline_backtest_replay_json",
    "render_etf_sma_authorized_adjusted_baseline_backtest_replay_text",
    "write_etf_sma_authorized_adjusted_baseline_backtest_replay_jsonl",
]


DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_SNAPSHOT_PATH = (
    Path("runs")
    / "paper_lab"
    / "m428_authorized_adjusted_baseline_backtest_snapshot.jsonl"
)
DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_REPLAY_PATH = (
    Path("runs")
    / "paper_lab"
    / "m429_authorized_adjusted_baseline_backtest_replay.jsonl"
)
DEFAULT_M417_SOURCE_ARTIFACT_PATH = (
    Path("runs") / "paper_lab" / "m417_spy_etf_sma_regime_slice_evidence.jsonl"
)
DEFAULT_THRU_M420_ADJUSTED_DAILY_BARS_CSV_PATH = (
    Path("runs")
    / "operator_input"
    / "spy_daily_tiingo_adjusted_canonical_20260607.csv"
)


@dataclass(frozen=True)
class EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig:
    """Configuration for the offline M429 backtest replay."""

    run_id: str
    symbol: str
    snapshot_path: (
        str | Path
    ) = DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_SNAPSHOT_PATH
    source_m417_artifact: str | Path = DEFAULT_M417_SOURCE_ARTIFACT_PATH
    daily_bars_csv: str | Path = DEFAULT_THRU_M420_ADJUSTED_DAILY_BARS_CSV_PATH


_COMMAND = "etf-sma-authorized-adjusted-baseline-backtest-replay"
_RECORD_TYPE = "etf_sma_authorized_adjusted_baseline_backtest_replay"
_SCHEMA_VERSION = "1"
_MILESTONE = "M429"
_SNAPSHOT_SOURCE_MILESTONE = "M428"
_LOCAL_REPLAY_SOURCE_MILESTONE = "M420"
_MATERIALIZED_STATUS = "authorized_adjusted_baseline_backtest_replayed"
_BLOCKED_STATUS = "blocked_authorized_snapshot_required"
_INPUT_SNAPSHOT_STATUS = (
    "authorized_adjusted_baseline_backtest_snapshot_materialized"
)
_INPUT_METRICS_STATUS = "authorized_adjusted_baseline_metrics_materialized"
_M420_REPLAY_STATUS = "completed_adjusted_matched_window_validation"
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
_METRICS_SOURCE_MILESTONE = "M427"
_SOURCE_EVIDENCE_MILESTONE = "M421"
_SNAPSHOT_SCOPE = "authorized_adjusted_baseline_metrics_only"
_REPLAY_SCOPE = "authorized_adjusted_close_matched_window"
_STRATEGY_FAMILY = "etf_sma_50_200"
_BENCHMARK_BUY_AND_HOLD = "buy_and_hold"
_BENCHMARK_BASIS = "adjusted_close_price_return_buy_and_hold"
_M417_RECORD_TYPE = "etf_sma_regime_slice_evidence"
_M417_MILESTONE = "M417"
_M420_RECORD_TYPE = "etf_sma_adjusted_matched_window_validation"
_SNAPSHOT_REQUIRED_STRING_FIELDS = (
    ("milestone", _SNAPSHOT_SOURCE_MILESTONE),
    ("backtest_snapshot_status", _INPUT_SNAPSHOT_STATUS),
    ("input_metrics_status", _INPUT_METRICS_STATUS),
    ("active_preferred_baseline", _PREFERRED_BASELINE),
    ("active_preferred_basis", _PREFERRED_BASIS),
    ("comparison_basis", _COMPARISON_BASIS),
    ("baseline_source_milestone", _BASELINE_SOURCE_MILESTONE),
    ("guard_source_milestone", _GUARD_SOURCE_MILESTONE),
    ("authorization_source_milestone", _AUTHORIZATION_SOURCE_MILESTONE),
    ("stub_source_milestone", _STUB_SOURCE_MILESTONE),
    ("summary_source_milestone", _SUMMARY_SOURCE_MILESTONE),
    ("metrics_source_milestone", _METRICS_SOURCE_MILESTONE),
    ("source_evidence_milestone", _SOURCE_EVIDENCE_MILESTONE),
    ("snapshot_scope", _SNAPSHOT_SCOPE),
    ("trade_recommendation", "none"),
    ("profit_claim", "none"),
)
_SNAPSHOT_TRUE_FIELDS = (
    "downstream_comparison_authorized",
    "backtest_snapshot_materialized",
)
_SNAPSHOT_FALSE_FIELDS = (
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
_LOCAL_REPLAY_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "submit_authorized",
    "submit_path_allowed",
    "paper_submit_approved",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "credential_access",
    "credential_access_attempted",
    "broker_network_access",
    "network_access_attempted",
    "broker_action_performed",
    "broker_actions_performed",
    "market_data_fetch_performed",
)
_REPLAY_REQUIRED_STRING_FIELDS = (
    ("record_type", _M420_RECORD_TYPE),
    ("milestone", _LOCAL_REPLAY_SOURCE_MILESTONE),
    ("basis_validation_status", _M420_REPLAY_STATUS),
    ("data_basis", _PREFERRED_BASIS),
    ("symbol", _EXPECTED_SYMBOL),
    ("trade_recommendation", "none"),
    ("profit_claim", "none"),
)
_REPLAY_REQUIRED_TRUE_FIELDS = (
    "match_source_slice_contract",
    "same_slice_counts",
    "same_slice_dates",
    "m417a_slice_counts_unchanged",
    "no_fabricated_returns",
)
_REPLAY_REQUIRED_FALSE_FIELDS = ("returns_fabricated",)


def build_etf_sma_authorized_adjusted_baseline_backtest_replay(
    config: EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig,
) -> dict[str, object]:
    """Build one fail-closed replay from an authorized M428 snapshot."""

    snapshot_path = Path(config.snapshot_path)
    source_m417_artifact = Path(config.source_m417_artifact)
    daily_bars_csv = Path(config.daily_bars_csv)
    payload = _base_payload(
        config,
        snapshot_path=snapshot_path,
        source_m417_artifact=source_m417_artifact,
        daily_bars_csv=daily_bars_csv,
    )
    blockers: list[str] = []
    if config.symbol != _EXPECTED_SYMBOL:
        blockers.append("unsupported_symbol")

    snapshot_record, snapshot_blockers = _load_single_jsonl_record(
        snapshot_path,
        "input_snapshot",
    )
    blockers.extend(snapshot_blockers)
    if snapshot_record is not None:
        blockers.extend(_validate_snapshot_record(snapshot_record, config.symbol))

    if blockers:
        return _blocked_payload(payload, blockers)
    if snapshot_record is None:
        return _blocked_payload(payload, ("input_snapshot_artifact_empty",))

    input_blockers = _validate_local_replay_inputs(
        source_m417_artifact,
        daily_bars_csv,
    )
    if input_blockers:
        return _blocked_payload(payload, input_blockers)

    replay_record, replay_blockers = _build_local_replay(
        config,
        source_m417_artifact=source_m417_artifact,
        daily_bars_csv=daily_bars_csv,
        snapshot_record=snapshot_record,
    )
    if replay_blockers:
        return _blocked_payload(payload, replay_blockers)
    if replay_record is None:
        return _blocked_payload(payload, ("local_replay_unavailable",))

    metric_matches = _snapshot_replay_metric_matches(
        snapshot_record,
        replay_record,
    )
    payload.update(
        {
            "backtest_replay_status": _MATERIALIZED_STATUS,
            "input_snapshot_status": snapshot_record[
                "backtest_snapshot_status"
            ],
            "downstream_comparison_authorized": True,
            "backtest_replayed": True,
            "active_preferred_baseline": snapshot_record[
                "active_preferred_baseline"
            ],
            "active_preferred_basis": snapshot_record["active_preferred_basis"],
            "comparison_basis": snapshot_record["comparison_basis"],
            "matched_total_interval_count": replay_record[
                "matched_total_interval_count"
            ],
            "known_basis_delta_slices": list(
                _payload_string_tuple(snapshot_record["known_basis_delta_slices"])
            ),
            "known_basis_delta_slice_count": snapshot_record[
                "known_basis_delta_slice_count"
            ],
            "baseline_source_milestone": snapshot_record[
                "baseline_source_milestone"
            ],
            "guard_source_milestone": snapshot_record["guard_source_milestone"],
            "authorization_source_milestone": snapshot_record[
                "authorization_source_milestone"
            ],
            "stub_source_milestone": snapshot_record["stub_source_milestone"],
            "summary_source_milestone": snapshot_record[
                "summary_source_milestone"
            ],
            "metrics_source_milestone": snapshot_record[
                "metrics_source_milestone"
            ],
            "snapshot_source_milestone": _SNAPSHOT_SOURCE_MILESTONE,
            "source_evidence_milestone": snapshot_record[
                "source_evidence_milestone"
            ],
            "local_replay_source_milestone": _LOCAL_REPLAY_SOURCE_MILESTONE,
            "input_replay_status": replay_record["basis_validation_status"],
            "replay_scope": _REPLAY_SCOPE,
            "strategy_family": _STRATEGY_FAMILY,
            "strategy": replay_record.get("strategy"),
            "data_basis": replay_record["data_basis"],
            "benchmark_basis": _benchmark_basis(replay_record),
            "benchmark": replay_record.get("benchmark"),
            "replay_helper": "build_etf_sma_adjusted_basis_validation",
            "replay_helper_mode": "match_source_slice_contract",
            "metrics_recomputed": False,
            "new_market_data_loaded": False,
            "trade_recommendation": "none",
            "profit_claim": "none",
            "blockers": [],
            "snapshot_replay_metric_match": all(metric_matches.values()),
            "snapshot_replay_metric_match_fields": sorted(metric_matches),
        }
    )
    payload.update(_replay_evidence_fields(replay_record))
    payload.update(_safety_false_fields())
    return payload


def render_etf_sma_authorized_adjusted_baseline_backtest_replay_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_authorized_adjusted_baseline_backtest_replay_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        f"backtest_replay_status: {payload['backtest_replay_status']}",
        "downstream_comparison_authorized: "
        f"{_bool_text(payload.get('downstream_comparison_authorized'))}",
        f"backtest_replayed: {_bool_text(payload.get('backtest_replayed'))}",
        f"symbol: {payload['symbol']}",
        f"input_snapshot_path: {payload['input_snapshot_path']}",
        f"source_m417_artifact: {payload['source_m417_artifact']}",
        f"daily_bars_csv: {payload['daily_bars_csv']}",
    ]
    if payload.get("backtest_replayed") is True:
        lines.extend(
            [
                f"input_snapshot_status: {payload['input_snapshot_status']}",
                f"input_replay_status: {payload['input_replay_status']}",
                f"replay_scope: {payload['replay_scope']}",
                f"data_basis: {payload['data_basis']}",
                f"evaluated_return_count: {payload['evaluated_return_count']}",
                f"start_date: {payload['start_date']}",
                f"end_date: {payload['end_date']}",
                f"strategy_total_return: {payload['strategy_total_return']}",
                f"max_drawdown: {payload['max_drawdown']}",
                f"trade_count: {payload['trade_count']}",
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


def write_etf_sma_authorized_adjusted_baseline_backtest_replay_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_authorized_adjusted_baseline_backtest_replay_json(payload)
        + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig,
    *,
    snapshot_path: Path,
    source_m417_artifact: Path,
    daily_bars_csv: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "input_snapshot_path": str(snapshot_path),
        "source_m417_artifact": str(source_m417_artifact),
        "daily_bars_csv": str(daily_bars_csv),
        "backtest_replay_status": _BLOCKED_STATUS,
        "downstream_comparison_authorized": False,
        "backtest_replayed": False,
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
    clean_blockers = list(dict.fromkeys(str(item) for item in blockers if str(item)))
    payload.update(
        {
            "backtest_replay_status": _BLOCKED_STATUS,
            "downstream_comparison_authorized": False,
            "backtest_replayed": False,
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


def _validate_snapshot_record(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    symbol_blocker = _validate_expected_string_field(
        record,
        "symbol",
        symbol,
        "input_snapshot",
    )
    if symbol_blocker is not None:
        blockers.append(symbol_blocker)

    for field_name, expected in _SNAPSHOT_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "input_snapshot",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _SNAPSHOT_TRUE_FIELDS:
        blocker = _validate_required_true_field(
            record,
            field_name,
            "input_snapshot",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _SNAPSHOT_FALSE_FIELDS:
        blocker = _validate_required_false_field(
            record,
            field_name,
            "input_snapshot",
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
            "input_snapshot",
        )
        if blocker is not None:
            blockers.append(blocker)

    slices_blocker = _validate_expected_string_list_field(
        record,
        "known_basis_delta_slices",
        _EXPECTED_KNOWN_BASIS_DELTA_SLICES,
        "input_snapshot",
    )
    if slices_blocker is not None:
        blockers.append(slices_blocker)

    for field_name in _SAFETY_FALSE_FIELDS:
        blocker = _validate_false_safety_field(
            record,
            field_name,
            "input_snapshot",
        )
        if blocker is not None:
            blockers.append(blocker)

    return tuple(blockers)


def _validate_local_replay_inputs(
    source_m417_artifact: Path,
    daily_bars_csv: Path,
) -> tuple[str, ...]:
    blockers: list[str] = []
    source_record, source_blockers = _load_single_jsonl_record(
        source_m417_artifact,
        "source_m417",
    )
    blockers.extend(source_blockers)
    if source_record is not None:
        blockers.extend(_validate_source_m417_record(source_record))

    if not daily_bars_csv.exists():
        blockers.append("daily_bars_csv_not_found")
    elif not daily_bars_csv.is_file():
        blockers.append("daily_bars_csv_path_not_file")

    return tuple(blockers)


def _validate_source_m417_record(record: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    for field_name, expected in (
        ("record_type", _M417_RECORD_TYPE),
        ("milestone", _M417_MILESTONE),
        ("symbol", _EXPECTED_SYMBOL),
    ):
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "source_m417",
        )
        if blocker is not None:
            blockers.append(blocker)

    return tuple(blockers)


def _build_local_replay(
    config: EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig,
    *,
    source_m417_artifact: Path,
    daily_bars_csv: Path,
    snapshot_record: Mapping[str, object],
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    try:
        replay_record = build_etf_sma_adjusted_basis_validation(
            EtfSmaAdjustedBasisValidationConfig(
                run_id=config.run_id,
                source_m417_artifact=source_m417_artifact,
                daily_bars_csv=daily_bars_csv,
                symbol=config.symbol,
                match_source_slice_contract=True,
            )
        )
    except (OSError, ValueError, ValidationError) as exc:
        return None, (f"local_replay_helper_error_{exc.__class__.__name__}",)

    blockers = list(_validate_replay_record(replay_record))
    blockers.extend(_snapshot_replay_metric_mismatch_blockers(snapshot_record, replay_record))
    if blockers:
        return None, tuple(blockers)
    return replay_record, ()


def _validate_replay_record(record: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    for field_name, expected in _REPLAY_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "local_replay",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _REPLAY_REQUIRED_TRUE_FIELDS:
        blocker = _validate_required_true_field(record, field_name, "local_replay")
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _REPLAY_REQUIRED_FALSE_FIELDS:
        blocker = _validate_required_false_field(
            record,
            field_name,
            "local_replay",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name, expected in (
        ("matched_total_interval_count", _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT),
        ("evaluated_return_count", _EXPECTED_MATCHED_TOTAL_INTERVAL_COUNT),
    ):
        blocker = _validate_expected_int_field(
            record,
            field_name,
            expected,
            "local_replay",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _LOCAL_REPLAY_SAFETY_FALSE_FIELDS:
        blocker = _validate_false_safety_field(
            record,
            field_name,
            "local_replay",
        )
        if blocker is not None:
            blockers.append(blocker)

    blocked_reason = record.get("blocked_reason")
    if blockers and isinstance(blocked_reason, str) and blocked_reason:
        blockers.append(f"local_replay_{_blocker_token(blocked_reason)}")

    return tuple(blockers)


def _snapshot_replay_metric_mismatch_blockers(
    snapshot_record: Mapping[str, object],
    replay_record: Mapping[str, object],
) -> tuple[str, ...]:
    blockers: list[str] = []
    for field_name, matched in _snapshot_replay_metric_matches(
        snapshot_record,
        replay_record,
    ).items():
        if not matched:
            blockers.append(f"local_replay_mismatch_{field_name}")
    return tuple(blockers)


def _snapshot_replay_metric_matches(
    snapshot_record: Mapping[str, object],
    replay_record: Mapping[str, object],
) -> dict[str, bool]:
    matches: dict[str, bool] = {}
    _compare_optional_field(
        matches,
        "matched_evaluated_return_count",
        snapshot_record,
        replay_record,
        "evaluated_return_count",
    )
    _compare_optional_field(
        matches,
        "full_adjusted_history_evaluated_return_count",
        snapshot_record,
        replay_record,
        "full_history_evaluated_return_count",
    )

    deltas = _payload_mapping(snapshot_record.get("full_window_return_deltas"))
    strategy_delta = _payload_mapping(deltas.get("strategy_total_return"))
    if "adjusted" in strategy_delta and "strategy_total_return" in replay_record:
        matches["strategy_total_return"] = (
            replay_record["strategy_total_return"] == strategy_delta["adjusted"]
        )

    benchmark_delta = _payload_mapping(deltas.get("benchmark_total_return"))
    if "adjusted" in benchmark_delta and "benchmark_total_return" in replay_record:
        matches["benchmark_total_return"] = (
            replay_record["benchmark_total_return"] == benchmark_delta["adjusted"]
        )

    full_comparison = _full_window_snapshot_comparison(snapshot_record)
    for snapshot_field, replay_field, result_field in (
        (
            "adjusted_strategy_max_drawdown",
            "strategy_max_drawdown",
            "strategy_max_drawdown",
        ),
        (
            "adjusted_benchmark_max_drawdown",
            "benchmark_max_drawdown",
            "benchmark_max_drawdown",
        ),
    ):
        if snapshot_field in full_comparison and replay_field in replay_record:
            matches[result_field] = (
                full_comparison[snapshot_field] == replay_record[replay_field]
            )

    return matches


def _full_window_snapshot_comparison(
    snapshot_record: Mapping[str, object],
) -> Mapping[str, object]:
    comparisons = snapshot_record.get("matched_slice_comparisons")
    if not isinstance(comparisons, Sequence) or isinstance(
        comparisons,
        (str, bytes),
    ):
        return {}
    for item in comparisons:
        if isinstance(item, Mapping) and item.get("slice_name") == (
            "full_evaluated_window"
        ):
            return item
    return {}


def _compare_optional_field(
    matches: dict[str, bool],
    result_field: str,
    snapshot_record: Mapping[str, object],
    replay_record: Mapping[str, object],
    replay_field: str,
) -> None:
    if result_field in snapshot_record and replay_field in replay_record:
        matches[result_field] = (
            snapshot_record[result_field] == replay_record[replay_field]
        )


def _replay_evidence_fields(record: Mapping[str, object]) -> dict[str, object]:
    fields: dict[str, object] = {}
    _copy_field(fields, "evaluated_return_count", record)
    _copy_field(fields, "full_history_evaluated_return_count", record)
    _copy_renamed_field(fields, "start_date", record, "evaluated_start_date")
    _copy_renamed_field(fields, "end_date", record, "evaluated_end_date")
    _copy_field(fields, "strategy_total_return", record)
    _copy_renamed_field(fields, "max_drawdown", record, "strategy_max_drawdown")
    _copy_field(fields, "benchmark_total_return", record)
    _copy_field(fields, "benchmark_max_drawdown", record)
    _copy_field(fields, "excess_return", record)
    _copy_field(fields, "exposure_fraction", record)
    _copy_field(fields, "trade_count", record)
    if "trade_count" in record:
        fields["trades_count"] = _copy_json_value(record["trade_count"])
    _copy_field(fields, "entry_count", record)
    _copy_field(fields, "exit_count", record)
    _copy_field(fields, "regime_slice_count", record)
    if "regime_slices" in record:
        fields["replayed_regime_slices"] = _copy_json_value(
            record["regime_slices"]
        )
    if "matched_slice_diagnostics" in record:
        diagnostics = _payload_sequence(record["matched_slice_diagnostics"])
        fields["matched_slice_diagnostics_count"] = len(diagnostics)
        fields["matched_slice_diagnostics"] = _copy_json_value(diagnostics)
    if "matched_slice_comparisons" in record:
        comparisons = _payload_sequence(record["matched_slice_comparisons"])
        fields["matched_slice_comparisons_count"] = len(comparisons)
        fields["matched_slice_comparisons"] = _copy_json_value(comparisons)
    fields["replay_evidence_fields"] = sorted(fields)
    return fields


def _benchmark_basis(record: Mapping[str, object]) -> str:
    if record.get("benchmark") == _BENCHMARK_BUY_AND_HOLD:
        return _BENCHMARK_BASIS
    return "none"


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


def _copy_field(
    target: dict[str, object],
    field_name: str,
    record: Mapping[str, object],
) -> None:
    if field_name in record:
        target[field_name] = _copy_json_value(record[field_name])


def _copy_renamed_field(
    target: dict[str, object],
    target_field: str,
    record: Mapping[str, object],
    source_field: str,
) -> None:
    if source_field in record:
        target[target_field] = _copy_json_value(record[source_field])


def _copy_json_value(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True))


def _payload_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _payload_sequence(value: object) -> list[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return []


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _safety_false_fields() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


def _blocker_token(value: str) -> str:
    return "".join(
        character if character.isalnum() or character == "_" else "_"
        for character in value.strip().lower()
    ).strip("_")


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
