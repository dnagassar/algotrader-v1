"""Offline M430 authorized adjusted-close ETF/SMA posture snapshot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.etf_sma_authorized_adjusted_baseline_backtest_replay import (
    DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_REPLAY_PATH,
)
from algotrader.research.local_daily_bars import (
    LocalDailyBar,
    load_local_daily_bars_csv,
)

__all__ = [
    "DEFAULT_AUTHORIZED_ADJUSTED_CLOSE_SMA_POSTURE_SNAPSHOT_PATH",
    "EtfSmaAuthorizedAdjustedClosePostureSnapshotConfig",
    "build_etf_sma_authorized_adjusted_close_posture_snapshot",
    "render_etf_sma_authorized_adjusted_close_posture_snapshot_json",
    "render_etf_sma_authorized_adjusted_close_posture_snapshot_text",
    "write_etf_sma_authorized_adjusted_close_posture_snapshot_jsonl",
]


DEFAULT_AUTHORIZED_ADJUSTED_CLOSE_SMA_POSTURE_SNAPSHOT_PATH = (
    Path("runs")
    / "paper_lab"
    / "m430_authorized_adjusted_close_sma_posture_snapshot.jsonl"
)


@dataclass(frozen=True)
class EtfSmaAuthorizedAdjustedClosePostureSnapshotConfig:
    """Configuration for the offline M430 posture snapshot."""

    run_id: str
    symbol: str = "SPY"
    replay_path: (
        str | Path
    ) = DEFAULT_AUTHORIZED_ADJUSTED_BASELINE_BACKTEST_REPLAY_PATH


_COMMAND = "etf-sma-authorized-adjusted-close-posture-snapshot"
_RECORD_TYPE = "etf_sma_authorized_adjusted_close_posture_snapshot"
_SCHEMA_VERSION = "1"
_MILESTONE = "M430"
_INPUT_REPLAY_MILESTONE = "M429"
_SUCCESS_STATUS = "authorized_adjusted_close_sma_posture_computed"
_INSUFFICIENT_STATUS = "insufficient_adjusted_history"
_BLOCKED_STATUS = "blocked_authorized_replay_required"
_INPUT_REPLAY_STATUS = "authorized_adjusted_baseline_backtest_replayed"
_INPUT_SNAPSHOT_STATUS = "authorized_adjusted_baseline_backtest_snapshot_materialized"
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
_SNAPSHOT_SOURCE_MILESTONE = "M428"
_SOURCE_EVIDENCE_MILESTONE = "M421"
_REPLAY_SCOPE = "authorized_adjusted_close_matched_window"
_STRATEGY_FAMILY = "etf_sma_50_200"
_SHORT_WINDOW = 50
_LONG_WINDOW = 200
_POSTURE_INSUFFICIENT = "insufficient_history"
_POSTURE_RISK_ON = "risk_on"
_POSTURE_RISK_OFF = "risk_off"
_ZERO = Decimal("0")
_REPLAY_REQUIRED_STRING_FIELDS = (
    ("milestone", _INPUT_REPLAY_MILESTONE),
    ("backtest_replay_status", _INPUT_REPLAY_STATUS),
    ("input_snapshot_status", _INPUT_SNAPSHOT_STATUS),
    ("active_preferred_baseline", _PREFERRED_BASELINE),
    ("active_preferred_basis", _PREFERRED_BASIS),
    ("comparison_basis", _COMPARISON_BASIS),
    ("baseline_source_milestone", _BASELINE_SOURCE_MILESTONE),
    ("guard_source_milestone", _GUARD_SOURCE_MILESTONE),
    ("authorization_source_milestone", _AUTHORIZATION_SOURCE_MILESTONE),
    ("stub_source_milestone", _STUB_SOURCE_MILESTONE),
    ("summary_source_milestone", _SUMMARY_SOURCE_MILESTONE),
    ("metrics_source_milestone", _METRICS_SOURCE_MILESTONE),
    ("snapshot_source_milestone", _SNAPSHOT_SOURCE_MILESTONE),
    ("source_evidence_milestone", _SOURCE_EVIDENCE_MILESTONE),
    ("replay_scope", _REPLAY_SCOPE),
    ("strategy_family", _STRATEGY_FAMILY),
    ("data_basis", _PREFERRED_BASIS),
    ("trade_recommendation", "none"),
    ("profit_claim", "none"),
)
_REPLAY_REQUIRED_TRUE_FIELDS = (
    "downstream_comparison_authorized",
    "backtest_replayed",
)
_REPLAY_REQUIRED_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
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
_POSTURE_FALSE_FIELDS = (
    "order_decision_computed",
    "paper_preview_computed",
    "broker_state_loaded",
    "new_market_data_loaded",
)
_SUCCESS_CONTEXT_FIELDS = (
    "input_replay_status",
    "active_preferred_baseline",
    "active_preferred_basis",
    "comparison_basis",
    "baseline_source_milestone",
    "guard_source_milestone",
    "authorization_source_milestone",
    "stub_source_milestone",
    "summary_source_milestone",
    "metrics_source_milestone",
    "snapshot_source_milestone",
    "replay_source_milestone",
    "source_evidence_milestone",
    "strategy_family",
    "data_basis",
)


def build_etf_sma_authorized_adjusted_close_posture_snapshot(
    config: EtfSmaAuthorizedAdjustedClosePostureSnapshotConfig,
) -> dict[str, object]:
    """Build one fail-closed latest adjusted-close SMA posture snapshot."""

    replay_path = Path(config.replay_path)
    payload = _base_payload(config, replay_path=replay_path)
    blockers: list[str] = []
    if config.symbol != _EXPECTED_SYMBOL:
        blockers.append("unsupported_symbol")

    replay_record, replay_blockers = _load_single_jsonl_record(
        replay_path,
        "input_replay",
    )
    blockers.extend(replay_blockers)
    if replay_record is not None:
        blockers.extend(_validate_replay_record(replay_record, config.symbol))

    if blockers:
        return _blocked_payload(payload, blockers)
    if replay_record is None:
        return _blocked_payload(payload, ("input_replay_artifact_empty",))

    daily_bars_csv = _daily_bars_csv_path(replay_record)
    if daily_bars_csv is None:
        return _blocked_payload(payload, ("input_replay_missing_daily_bars_csv",))

    bars, local_input_blockers = _load_adjusted_bars(daily_bars_csv, config.symbol)
    if local_input_blockers:
        return _blocked_payload(payload, local_input_blockers)

    if not bars:
        return _blocked_payload(payload, ("local_adjusted_close_input_empty",))

    latest_bar = bars[-1]
    sma50 = _sma(bars, _SHORT_WINDOW)
    sma200 = _sma(bars, _LONG_WINDOW)
    sufficient_history = len(bars) >= _LONG_WINDOW
    sma_posture = _POSTURE_INSUFFICIENT
    posture_status = _INSUFFICIENT_STATUS
    if sufficient_history and sma50 is not None and sma200 is not None:
        sma_posture = _POSTURE_RISK_ON if sma50 > sma200 else _POSTURE_RISK_OFF
        posture_status = _SUCCESS_STATUS

    payload.update(
        {
            "posture_snapshot_status": posture_status,
            "input_replay_status": replay_record["backtest_replay_status"],
            "downstream_comparison_authorized": True,
            "posture_computed": True,
            "active_preferred_baseline": replay_record["active_preferred_baseline"],
            "active_preferred_basis": replay_record["active_preferred_basis"],
            "comparison_basis": replay_record["comparison_basis"],
            "baseline_source_milestone": replay_record["baseline_source_milestone"],
            "guard_source_milestone": replay_record["guard_source_milestone"],
            "authorization_source_milestone": replay_record[
                "authorization_source_milestone"
            ],
            "stub_source_milestone": replay_record["stub_source_milestone"],
            "summary_source_milestone": replay_record["summary_source_milestone"],
            "metrics_source_milestone": replay_record["metrics_source_milestone"],
            "snapshot_source_milestone": replay_record["snapshot_source_milestone"],
            "replay_source_milestone": _INPUT_REPLAY_MILESTONE,
            "source_evidence_milestone": replay_record["source_evidence_milestone"],
            "strategy_family": replay_record["strategy_family"],
            "data_basis": replay_record["data_basis"],
            "as_of_date": latest_bar.date.isoformat(),
            "latest_available_bar_date": latest_bar.date.isoformat(),
            "adjusted_close": _decimal_text(latest_bar.adjusted_close),
            "usable_adjusted_bar_count": len(bars),
            "sma_short_window": _SHORT_WINDOW,
            "sma_long_window": _LONG_WINDOW,
            "sma50": _optional_decimal_text(sma50),
            "sma200": _optional_decimal_text(sma200),
            "sma_posture": sma_posture,
            "sufficient_history": sufficient_history,
            "daily_bars_csv": str(daily_bars_csv),
            "adjusted_close_input_helper": "load_local_daily_bars_csv",
            "adjusted_close_input_source": "m429_daily_bars_csv",
            "blockers": [],
        }
    )
    payload.update(_posture_false_fields())
    payload.update(_safety_false_fields())
    return payload


def render_etf_sma_authorized_adjusted_close_posture_snapshot_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_authorized_adjusted_close_posture_snapshot_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        f"posture_snapshot_status: {payload['posture_snapshot_status']}",
        "downstream_comparison_authorized: "
        f"{_bool_text(payload.get('downstream_comparison_authorized'))}",
        f"posture_computed: {_bool_text(payload.get('posture_computed'))}",
        f"symbol: {payload['symbol']}",
        f"input_replay_path: {payload['input_replay_path']}",
    ]
    if payload.get("posture_computed") is True:
        lines.extend(
            [
                f"daily_bars_csv: {payload['daily_bars_csv']}",
                f"as_of_date: {payload['as_of_date']}",
                f"latest_available_bar_date: {payload['latest_available_bar_date']}",
                f"adjusted_close: {payload['adjusted_close']}",
                f"usable_adjusted_bar_count: {payload['usable_adjusted_bar_count']}",
                f"sma50: {payload['sma50']}",
                f"sma200: {payload['sma200']}",
                f"sma_posture: {payload['sma_posture']}",
                f"sufficient_history: {_bool_text(payload['sufficient_history'])}",
            ]
        )

    blockers = _payload_string_tuple(payload.get("blockers"))
    if blockers:
        lines.append(f"blockers: {','.join(blockers)}")

    lines.extend(
        [
            "order_decision_computed: "
            f"{_bool_text(payload.get('order_decision_computed'))}",
            "paper_preview_computed: "
            f"{_bool_text(payload.get('paper_preview_computed'))}",
            f"trade_recommendation: {payload['trade_recommendation']}",
            f"profit_claim: {payload['profit_claim']}",
        ]
    )
    return "\n".join(lines)


def write_etf_sma_authorized_adjusted_close_posture_snapshot_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_authorized_adjusted_close_posture_snapshot_json(payload)
        + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaAuthorizedAdjustedClosePostureSnapshotConfig,
    *,
    replay_path: Path,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "input_replay_path": str(replay_path),
        "posture_snapshot_status": _BLOCKED_STATUS,
        "downstream_comparison_authorized": False,
        "posture_computed": False,
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
    payload.update(_posture_false_fields())
    payload.update(_safety_false_fields())
    return payload


def _blocked_payload(
    payload: dict[str, object],
    blockers: Sequence[str],
) -> dict[str, object]:
    clean_blockers = list(dict.fromkeys(str(item) for item in blockers if str(item)))
    payload.update(
        {
            "posture_snapshot_status": _BLOCKED_STATUS,
            "downstream_comparison_authorized": False,
            "posture_computed": False,
            "blockers": clean_blockers,
            "blocked_reason": clean_blockers[0] if clean_blockers else "blocked",
            "trade_recommendation": "none",
            "operator_trade_recommendation": "none",
            "profit_claim": "none",
        }
    )
    payload.update(_posture_false_fields())
    payload.update(_safety_false_fields())
    for field_name in _SUCCESS_CONTEXT_FIELDS:
        payload.pop(field_name, None)
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


def _validate_replay_record(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    symbol_blocker = _validate_expected_string_field(
        record,
        "symbol",
        symbol,
        "input_replay",
    )
    if symbol_blocker is not None:
        blockers.append(symbol_blocker)

    for field_name, expected in _REPLAY_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "input_replay",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _REPLAY_REQUIRED_TRUE_FIELDS:
        blocker = _validate_required_true_field(record, field_name, "input_replay")
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _REPLAY_REQUIRED_FALSE_FIELDS:
        blocker = _validate_required_false_field(record, field_name, "input_replay")
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
            "input_replay",
        )
        if blocker is not None:
            blockers.append(blocker)

    slices_blocker = _validate_expected_string_list_field(
        record,
        "known_basis_delta_slices",
        _EXPECTED_KNOWN_BASIS_DELTA_SLICES,
        "input_replay",
    )
    if slices_blocker is not None:
        blockers.append(slices_blocker)

    return tuple(blockers)


def _daily_bars_csv_path(record: Mapping[str, object]) -> Path | None:
    value = record.get("daily_bars_csv")
    if type(value) is not str or not value.strip():
        return None
    if "://" in value:
        return None
    return Path(value)


def _load_adjusted_bars(
    daily_bars_csv: Path,
    symbol: str,
) -> tuple[tuple[LocalDailyBar, ...], tuple[str, ...]]:
    if not daily_bars_csv.exists():
        return (), ("local_adjusted_close_input_not_found",)
    if not daily_bars_csv.is_file():
        return (), ("local_adjusted_close_input_path_not_file",)

    try:
        csv_result = load_local_daily_bars_csv(daily_bars_csv, symbol=symbol)
    except ValidationError as exc:
        return (), (f"local_adjusted_close_input_error_{_blocker_token(str(exc))}",)
    except OSError:
        return (), ("local_adjusted_close_input_unreadable",)

    blockers: list[str] = []
    if csv_result.input_sorted_by_date is not True:
        blockers.append("ambiguous_local_adjusted_close_input_unsorted_dates")
    if csv_result.ignored_wrong_symbol_row_count != 0:
        blockers.append("ambiguous_local_adjusted_close_input_symbol_rows")
    bars = csv_result.usable_bars
    if not bars:
        blockers.append("local_adjusted_close_input_empty")
    if bars and all(bar.close == bar.adjusted_close for bar in bars):
        blockers.append("local_adjusted_close_input_not_adjusted")
    return bars, tuple(blockers)


def _sma(bars: tuple[LocalDailyBar, ...], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    return sum((bar.adjusted_close for bar in bars[-window:]), _ZERO) / Decimal(
        window
    )


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


def _posture_false_fields() -> dict[str, bool]:
    return {field_name: False for field_name in _POSTURE_FALSE_FIELDS}


def _safety_false_fields() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


def _decimal_text(value: Decimal) -> str:
    return str(value)


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _blocker_token(value: str) -> str:
    return "".join(
        character if character.isalnum() or character == "_" else "_"
        for character in value.strip().lower()
    ).strip("_")


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
