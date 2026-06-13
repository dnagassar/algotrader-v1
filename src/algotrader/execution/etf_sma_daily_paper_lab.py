"""Assistant v1 daily ETF/SMA paper-lab command center.

This module is completely offline, deterministic, credential-free,
network-free, and broker-free. It generates the first operator-facing daily
assistant packet for the controlled SPY SMA 50/200 paper-lab strategy.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)

__all__ = [
    "EtfSmaDailyPaperLabConfig",
    "run_etf_sma_daily_paper_lab",
    "build_etf_sma_daily_paper_lab",
    "validate_etf_sma_daily_paper_lab_packet",
]

_DEFAULT_SYMBOL = "SPY"
_DEFAULT_BARS_CSV = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
_STRATEGY_NAME = "SPY daily long-only ETF SMA 50/200 trend filter"
_SCHEMA_VERSION = "1"
_ASSISTANT_VERSION = "assistant_v1"
_ASSISTANT_PACKET_VERSION = "assistant_v1.1"
_PACKET_TYPE = "daily_trading_research_command_center"
_COMMAND = "etf-sma-daily-paper-lab"
_SCRIPT = "scripts/run_daily_paper_lab.ps1"
_BRIEF_FILENAME = "operating_brief.md"
_RECORD_FILENAME = "operating_record.jsonl"
_MANIFEST_FILENAME = "manifest.jsonl"
_HISTORY_LEDGER_FILENAME = "history_ledger.jsonl"
_HISTORY_ENTRY_VERSION = "assistant_v1.2_history_entry"
_REQUIRED_LABELS = [
    "paper_lab_only",
    "signal_evaluation_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "offline_only",
    "broker_state_not_observed",
    "paper_submit_not_authorized",
]
_EXPECTED_ARTIFACTS = (
    ("operating_brief", _BRIEF_FILENAME),
    ("operating_record", _RECORD_FILENAME),
    ("manifest", _MANIFEST_FILENAME),
)
_REQUIRED_PACKET_FIELDS = (
    "input_data_path",
    "as_of_date",
    "active_strategy_name",
    "posture",
    "sma_posture_status",
    "preview_decision",
    "blocker_status",
    "broker_state_mode",
    "next_operator_action",
    "safety_labels",
    "assistant_packet_version",
    "history_ledger_path",
    "history_delta",
)
_REQUIRED_MANIFEST_FIELDS = (
    "input_data_path",
    "as_of_date",
    "active_strategy_name",
    "posture",
    "sma_posture_status",
    "preview_decision",
    "blocker_status",
    "broker_state_mode",
    "paper_submit_authorized",
    "paper_submit_authorization_status",
    "next_operator_action",
    "safety_labels",
    "assistant_packet_version",
    "validation_status",
    "missing_required_fields",
    "artifact_presence_status",
    "history_ledger_path",
    "history_delta",
)
_REQUIRED_DELTA_FIELDS = (
    "previous_packet_found",
    "previous_as_of_date",
    "current_as_of_date",
    "posture_changed",
    "previous_posture",
    "current_posture",
    "preview_decision_changed",
    "previous_preview_decision",
    "current_preview_decision",
    "blocker_status_changed",
    "previous_blocker_status",
    "current_blocker_status",
    "validation_status_changed",
    "previous_validation_status",
    "current_validation_status",
    "broker_state_mode_changed",
    "previous_broker_state_mode",
    "current_broker_state_mode",
    "research_board_changed",
    "research_board_delta_status",
    "next_operator_action_changed",
    "delta_summary_text",
)
_BRIEF_REQUIRED_VALUE_FIELDS = (
    "input_data_path",
    "as_of_date",
    "active_strategy_name",
    "sma_posture_status",
    "preview_decision",
    "blocker_status",
    "broker_state_mode",
    "next_operator_action",
)
_NOT_AUTHORIZED_STATUSES = {
    "not_authorized",
    "paper_submit_not_authorized",
}


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPaperLabConfig:
    """Configuration for the Assistant v1 daily paper-lab loop."""

    output_root: Path | str
    bars_csv: Path | str = _DEFAULT_BARS_CSV
    as_of_date: str | None = None
    symbol: str = _DEFAULT_SYMBOL
    sma_fast_window: int = 50
    sma_slow_window: int = 200

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _required_path(self.output_root, "output_root"))
        object.__setattr__(self, "bars_csv", _required_path(self.bars_csv, "bars_csv"))
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        if self.sma_fast_window <= 0:
            raise ValidationError("sma_fast_window must be positive.")
        if self.sma_slow_window <= 0:
            raise ValidationError("sma_slow_window must be positive.")
        if self.sma_fast_window >= self.sma_slow_window:
            raise ValidationError("sma_fast_window must be less than sma_slow_window.")


def run_etf_sma_daily_paper_lab(config: EtfSmaDailyPaperLabConfig) -> dict[str, Any]:
    """Execute the daily assistant command and write the packet artifacts."""
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    history_ledger_path = output_root / _HISTORY_LEDGER_FILENAME
    history_entries = _read_history_ledger(history_ledger_path)
    previous_history_entry = history_entries[-1] if history_entries else None

    payload = build_etf_sma_daily_paper_lab(config)
    _apply_history_delta(payload, previous_history_entry)

    _write_packet_artifacts(output_root=output_root, payload=payload)
    validation = validate_etf_sma_daily_paper_lab_packet(output_root, packet=payload)
    _apply_packet_validation(payload, validation)
    _apply_history_delta(payload, previous_history_entry)

    history_entry = _build_history_entry(
        payload=payload,
        sequence_number=len(history_entries) + 1,
    )
    _append_history_entry(history_ledger_path, history_entry)
    payload["history_ledger_entry"] = dict(history_entry)
    payload["executive_dashboard"]["history_ledger_entry_sequence"] = history_entry[
        "sequence_number"
    ]
    _write_packet_artifacts(output_root=output_root, payload=payload)

    return payload


def validate_etf_sma_daily_paper_lab_packet(
    output_root: Path | str,
    *,
    packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a generated Assistant v1.1 daily paper-lab packet."""
    root = Path(output_root)
    artifact_presence_status = _artifact_presence_status(root)
    packet_payload = packet
    read_failures: list[str] = []

    if packet_payload is None:
        packet_payload, read_failures = _read_packet_record(root / _RECORD_FILENAME)

    missing_required_fields: list[str] = []
    missing_required_fields.extend(read_failures)
    if packet_payload is None:
        missing_required_fields.append("operating_record.packet")
    else:
        missing_required_fields.extend(_missing_packet_fields(packet_payload))
        missing_required_fields.extend(_missing_manifest_fields(root, packet_payload))
        missing_required_fields.extend(_missing_brief_references(root, packet_payload))

    validation_status = (
        "pass"
        if (
            artifact_presence_status["status"] == "pass"
            and not missing_required_fields
        )
        else "fail"
    )
    return {
        "assistant_packet_version": _ASSISTANT_PACKET_VERSION,
        "validation_status": validation_status,
        "missing_required_fields": missing_required_fields,
        "artifact_presence_status": artifact_presence_status,
    }


def _write_packet_artifacts(
    *,
    output_root: Path,
    payload: Mapping[str, Any],
) -> None:
    record_file = output_root / _RECORD_FILENAME
    record_line = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":")) + "\n"
    record_file.write_text(record_line, encoding="utf-8", newline="\n")

    brief_file = output_root / _BRIEF_FILENAME
    brief_file.write_text(_render_brief_markdown(payload), encoding="utf-8", newline="\n")

    manifest_file = output_root / _MANIFEST_FILENAME
    manifest_data = _build_manifest(output_root, payload)
    manifest_line = json.dumps(manifest_data, sort_keys=True, separators=(",", ":")) + "\n"
    manifest_file.write_text(manifest_line, encoding="utf-8", newline="\n")


def _apply_packet_validation(
    payload: dict[str, Any],
    validation: Mapping[str, Any],
) -> None:
    payload["assistant_packet_version"] = str(validation["assistant_packet_version"])
    payload["validation_status"] = str(validation["validation_status"])
    payload["missing_required_fields"] = list(validation["missing_required_fields"])
    payload["artifact_presence_status"] = dict(validation["artifact_presence_status"])
    payload["executive_dashboard"]["validation_status"] = payload["validation_status"]
    payload["executive_dashboard"]["missing_required_fields"] = list(
        payload["missing_required_fields"]
    )
    payload["executive_dashboard"]["artifact_presence_status"] = dict(
        payload["artifact_presence_status"]
    )


def build_etf_sma_daily_paper_lab(config: EtfSmaDailyPaperLabConfig) -> dict[str, Any]:
    """Load inputs and build the Assistant v1 daily paper-lab payload."""
    bars_path = Path(config.bars_csv)
    bars = _load_bars(bars_path, config.symbol)

    if config.as_of_date:
        as_of_str = config.as_of_date.strip()
        try:
            as_of_dt = datetime.combine(
                datetime.fromisoformat(as_of_str).date(),
                datetime.min.time(),
                tzinfo=timezone.utc,
            )
        except ValueError as exc:
            raise ValidationError(
                f"as_of_date must be in YYYY-MM-DD format: {config.as_of_date}"
            ) from exc
        as_of_source = "explicit_config"
    else:
        if not bars:
            raise ValidationError("No usable bars found to derive default as-of date.")
        as_of_dt = max(bar.timestamp for bar in bars)
        as_of_str = as_of_dt.strftime("%Y-%m-%d")
        as_of_source = "latest_input_bar"

    latest_input_bar_date = max(bar.timestamp for bar in bars).strftime("%Y-%m-%d")
    signal = evaluate_etf_sma_signal(
        bars,
        EtfSmaSignalConfig(
            as_of=as_of_dt,
            symbol=config.symbol,
            short_window=config.sma_fast_window,
            long_window=config.sma_slow_window,
        ),
    )

    posture = signal.posture
    sma_fast_value = _decimal_text(signal.short_sma)
    sma_slow_value = _decimal_text(signal.long_sma)
    preview_decision = _preview_decision(posture)
    next_operator_action = _next_operator_action(posture, config.sma_slow_window)
    blocker_status = "broker_state_not_observed"
    broker_state_mode = "broker_state_not_observed"
    output_root = Path(config.output_root)
    artifact_paths = _artifact_paths(output_root)
    sma_status = _sma_status(
        posture=posture,
        fast_window=config.sma_fast_window,
        slow_window=config.sma_slow_window,
        usable_bar_count=signal.usable_bar_count,
    )
    data_freshness = _data_freshness(
        as_of_date=as_of_str,
        latest_input_bar_date=latest_input_bar_date,
    )
    research_lab = _research_lab(
        config=config,
        as_of_date=as_of_str,
        posture=posture,
        sma_status=sma_status,
        sma_fast_value=sma_fast_value,
        sma_slow_value=sma_slow_value,
    )

    payload: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "assistant_version": _ASSISTANT_VERSION,
        "assistant_packet_version": _ASSISTANT_PACKET_VERSION,
        "packet_type": _PACKET_TYPE,
        "command": _COMMAND,
        "script": _SCRIPT,
        "run_id": f"daily_paper_lab_{as_of_str}",
        "input_data_path": _normalize_path(bars_path),
        "input_data_sha256": _sha256_file(bars_path),
        "as_of_date": as_of_str,
        "as_of_source": as_of_source,
        "latest_input_bar_date": latest_input_bar_date,
        "active_strategy_name": _STRATEGY_NAME,
        "strategy_name": _STRATEGY_NAME,
        "symbol": config.symbol,
        "sma_fast_window": config.sma_fast_window,
        "sma_slow_window": config.sma_slow_window,
        "sma_fast_value": sma_fast_value,
        "sma_slow_value": sma_slow_value,
        "sma_posture_status": sma_status,
        "posture": posture,
        "preview_decision": preview_decision,
        "decision": preview_decision,
        "current_recommendation": _current_recommendation(posture),
        "blocker_status": blocker_status,
        "blockers": [blocker_status],
        "broker_state_mode": broker_state_mode,
        "broker_state_observed": False,
        "broker_state_claim": (
            "No broker positions or open orders were read; this packet makes no "
            "position or order-state claim."
        ),
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "paper_submit_authorization_reason": "operator_has_not_authorized_submit",
        "next_operator_action": next_operator_action,
        "labels": list(_REQUIRED_LABELS),
        "safety_labels": list(_REQUIRED_LABELS),
        "data_freshness": data_freshness,
        "validation_status": "pending",
        "missing_required_fields": [],
        "artifact_presence_status": {
            "status": "not_evaluated",
            "missing_artifacts": [],
            "empty_artifacts": [],
            "artifacts": {},
        },
        "system_health": "offline_assistant_packet_ready",
        "artifact_paths": artifact_paths,
        "history_ledger_path": artifact_paths["history_ledger"],
        "history_delta": _empty_history_delta(as_of_str),
        "history_ledger_entry": {},
        "artifacts": {
            "assistant_brief": artifact_paths["assistant_brief"],
            "operating_brief": artifact_paths["assistant_brief"],
            "operating_record": artifact_paths["operating_record"],
            "manifest": artifact_paths["manifest"],
            "history_ledger": artifact_paths["history_ledger"],
        },
        "sma": {
            "symbol": signal.symbol,
            "fast_window": signal.short_window,
            "slow_window": signal.long_window,
            "fast_value": sma_fast_value,
            "slow_value": sma_slow_value,
            "latest_close": _decimal_text(signal.latest_close),
            "total_bar_count": signal.total_bar_count,
            "usable_bar_count": signal.usable_bar_count,
            "ignored_future_bar_count": signal.ignored_future_bar_count,
            "posture": posture,
            "status": sma_status,
        },
        "research_lab": research_lab,
        "executive_dashboard": {
            "data_freshness": data_freshness,
            "validation_status": "pending",
            "missing_required_fields": [],
            "artifact_presence_status": {
                "status": "not_evaluated",
                "missing_artifacts": [],
                "empty_artifacts": [],
                "artifacts": {},
            },
            "artifact_paths": artifact_paths,
            "history_ledger_path": artifact_paths["history_ledger"],
            "history_ledger_entry_sequence": None,
            "system_health": "offline_assistant_packet_ready",
            "safety_labels": list(_REQUIRED_LABELS),
            "next_operator_action": next_operator_action,
        },
    }
    payload["executive_summary"] = {
        "plain_english_status": _plain_english_status(payload),
        "current_recommendation": payload["current_recommendation"],
        "current_blocker": blocker_status,
        "daniel_action_required": _daniel_action_required(posture),
    }
    return payload


def _load_bars(path: Path, symbol: str) -> list[Bar]:
    if not path.exists():
        raise ValidationError(f"Bars CSV not found: {path}")
    bars = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            bars.append(_parse_row_to_bar(row, symbol))
    return bars


def _row_value(row: Mapping[str, object], field_name: str) -> object:
    for key, value in row.items():
        if str(key).strip().lower() == field_name:
            return value
    return None


def _parse_row_to_bar(row: Mapping[str, object], symbol: str) -> Bar:
    close_val = _row_value(row, "close")
    if close_val in (None, ""):
        raise ValidationError("close price is required in CSV.")
    raw_close = Decimal(str(close_val))

    adj_close_val = _row_value(row, "adjusted_close")
    if adj_close_val not in (None, ""):
        close = Decimal(str(adj_close_val))
        factor = close / raw_close if raw_close != Decimal("0") else Decimal("1")
    else:
        close = raw_close
        factor = Decimal("1")

    open_val = _row_value(row, "open")
    open_price = Decimal(str(open_val)) if open_val not in (None, "") else raw_close

    high_val = _row_value(row, "high")
    high = Decimal(str(high_val)) if high_val not in (None, "") else max(open_price, raw_close)

    low_val = _row_value(row, "low")
    low = Decimal(str(low_val)) if low_val not in (None, "") else min(open_price, raw_close)

    volume_val = _row_value(row, "volume")
    volume = Decimal(str(volume_val)) if volume_val not in (None, "") else Decimal("0")

    open_price = open_price * factor
    high = high * factor
    low = low * factor

    high = max(high, open_price, close)
    low = min(low, open_price, close)

    dt_val = None
    for date_field in ("date", "timestamp", "datetime"):
        val = _row_value(row, date_field)
        if val not in (None, ""):
            dt_val = str(val).strip()
            break

    if not dt_val:
        raise ValidationError("date/timestamp is required in CSV.")

    try:
        if "T" in dt_val:
            dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        else:
            dt = datetime.combine(datetime.fromisoformat(dt_val).date(), datetime.min.time())
    except ValueError as exc:
        raise ValidationError(f"Invalid date format: {dt_val}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    row_symbol = _row_value(row, "symbol")
    symbol_str = symbol if row_symbol in (None, "") else str(row_symbol).strip().upper()

    return Bar(
        symbol=symbol_str,
        timestamp=dt,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    return path


def _normalize_path(path: Path | str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _artifact_paths(output_root: Path) -> dict[str, str]:
    return {
        "assistant_brief": _normalize_path(output_root / _BRIEF_FILENAME),
        "operating_record": _normalize_path(output_root / _RECORD_FILENAME),
        "manifest": _normalize_path(output_root / _MANIFEST_FILENAME),
        "history_ledger": _normalize_path(output_root / _HISTORY_LEDGER_FILENAME),
    }


def _read_history_ledger(path: Path) -> list[Mapping[str, Any]]:
    if not path.exists():
        return []

    entries: list[Mapping[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"History ledger is not readable: {path}") from exc

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"History ledger line {index} is not parseable JSON: {path}"
            ) from exc
        if not isinstance(entry, Mapping):
            raise ValidationError(
                f"History ledger line {index} is not a JSON object: {path}"
            )
        entries.append(entry)
    return entries


def _append_history_entry(path: Path, entry: Mapping[str, Any]) -> None:
    line = json.dumps(_json_safe(entry), sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(line)


def _apply_history_delta(
    payload: dict[str, Any],
    previous_history_entry: Mapping[str, Any] | None,
) -> None:
    delta = _build_history_delta(payload, previous_history_entry)
    payload["history_delta"] = delta
    payload["executive_dashboard"]["history_delta"] = dict(delta)
    payload["executive_dashboard"]["delta_summary_text"] = delta["delta_summary_text"]


def _empty_history_delta(current_as_of_date: str) -> dict[str, Any]:
    return {
        "previous_packet_found": False,
        "previous_as_of_date": None,
        "current_as_of_date": current_as_of_date,
        "posture_changed": False,
        "previous_posture": None,
        "current_posture": None,
        "preview_decision_changed": False,
        "previous_preview_decision": None,
        "current_preview_decision": None,
        "blocker_status_changed": False,
        "previous_blocker_status": None,
        "current_blocker_status": None,
        "validation_status_changed": False,
        "previous_validation_status": None,
        "current_validation_status": None,
        "broker_state_mode_changed": False,
        "previous_broker_state_mode": None,
        "current_broker_state_mode": None,
        "research_board_changed": False,
        "research_board_delta_status": "not_evaluated",
        "next_operator_action_changed": False,
        "previous_next_operator_action": None,
        "current_next_operator_action": None,
        "delta_summary_text": "History delta has not been evaluated yet.",
    }


def _build_history_delta(
    payload: Mapping[str, Any],
    previous_history_entry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    previous_packet_found = previous_history_entry is not None
    previous = previous_history_entry or {}

    previous_as_of_date = _history_value(previous, "as_of_date")
    current_as_of_date = str(payload["as_of_date"])
    previous_posture = _history_value(previous, "posture")
    current_posture = str(payload["posture"])
    previous_preview_decision = _history_value(previous, "preview_decision")
    current_preview_decision = str(payload["preview_decision"])
    previous_blocker_status = _history_value(previous, "blocker_status")
    current_blocker_status = str(payload["blocker_status"])
    previous_validation_status = _history_value(previous, "validation_status")
    current_validation_status = str(payload["validation_status"])
    previous_broker_state_mode = _history_value(previous, "broker_state_mode")
    current_broker_state_mode = str(payload["broker_state_mode"])
    previous_next_operator_action = _history_value(previous, "next_operator_action")
    current_next_operator_action = str(payload["next_operator_action"])
    previous_research_board_fingerprint = _history_value(
        previous,
        "research_board_fingerprint",
    )
    current_research_board_fingerprint = _research_board_fingerprint(payload)

    posture_changed = _history_changed(
        previous_packet_found,
        previous_posture,
        current_posture,
    )
    preview_decision_changed = _history_changed(
        previous_packet_found,
        previous_preview_decision,
        current_preview_decision,
    )
    blocker_status_changed = _history_changed(
        previous_packet_found,
        previous_blocker_status,
        current_blocker_status,
    )
    validation_status_changed = _history_changed(
        previous_packet_found,
        previous_validation_status,
        current_validation_status,
    )
    broker_state_mode_changed = _history_changed(
        previous_packet_found,
        previous_broker_state_mode,
        current_broker_state_mode,
    )
    research_board_changed = _history_changed(
        previous_packet_found,
        previous_research_board_fingerprint,
        current_research_board_fingerprint,
    )
    next_operator_action_changed = _history_changed(
        previous_packet_found,
        previous_next_operator_action,
        current_next_operator_action,
    )

    if not previous_packet_found:
        research_board_delta_status = "no_previous_packet"
    elif research_board_changed:
        research_board_delta_status = "changed"
    else:
        research_board_delta_status = "unchanged"

    delta: dict[str, Any] = {
        "previous_packet_found": previous_packet_found,
        "previous_as_of_date": previous_as_of_date,
        "current_as_of_date": current_as_of_date,
        "posture_changed": posture_changed,
        "previous_posture": previous_posture,
        "current_posture": current_posture,
        "preview_decision_changed": preview_decision_changed,
        "previous_preview_decision": previous_preview_decision,
        "current_preview_decision": current_preview_decision,
        "blocker_status_changed": blocker_status_changed,
        "previous_blocker_status": previous_blocker_status,
        "current_blocker_status": current_blocker_status,
        "validation_status_changed": validation_status_changed,
        "previous_validation_status": previous_validation_status,
        "current_validation_status": current_validation_status,
        "broker_state_mode_changed": broker_state_mode_changed,
        "previous_broker_state_mode": previous_broker_state_mode,
        "current_broker_state_mode": current_broker_state_mode,
        "research_board_changed": research_board_changed,
        "research_board_delta_status": research_board_delta_status,
        "previous_research_board_fingerprint": previous_research_board_fingerprint,
        "current_research_board_fingerprint": current_research_board_fingerprint,
        "next_operator_action_changed": next_operator_action_changed,
        "previous_next_operator_action": previous_next_operator_action,
        "current_next_operator_action": current_next_operator_action,
    }
    delta["delta_summary_text"] = _delta_summary_text(delta)
    return delta


def _history_value(entry: Mapping[str, Any], field_name: str) -> str | None:
    value = entry.get(field_name)
    if value is None:
        return None
    return str(value)


def _history_changed(
    previous_packet_found: bool,
    previous_value: str | None,
    current_value: str | None,
) -> bool:
    return previous_packet_found and previous_value != current_value


def _delta_summary_text(delta: Mapping[str, Any]) -> str:
    if not delta["previous_packet_found"]:
        return (
            "No prior packet was found in this output root history; this is the "
            "first observed packet in the selected history."
        )

    changes: list[str] = []
    if delta["previous_as_of_date"] != delta["current_as_of_date"]:
        changes.append(
            "as-of date moved from "
            f"{delta['previous_as_of_date']} to {delta['current_as_of_date']}"
        )
    if delta["posture_changed"]:
        changes.append(
            "posture changed from "
            f"{delta['previous_posture']} to {delta['current_posture']}"
        )
    if delta["preview_decision_changed"]:
        changes.append(
            "preview decision changed from "
            f"{delta['previous_preview_decision']} to "
            f"{delta['current_preview_decision']}"
        )
    if delta["blocker_status_changed"]:
        changes.append(
            "blocker status changed from "
            f"{delta['previous_blocker_status']} to {delta['current_blocker_status']}"
        )
    if delta["validation_status_changed"]:
        changes.append(
            "validation status changed from "
            f"{delta['previous_validation_status']} to "
            f"{delta['current_validation_status']}"
        )
    if delta["broker_state_mode_changed"]:
        changes.append(
            "broker-state mode changed from "
            f"{delta['previous_broker_state_mode']} to "
            f"{delta['current_broker_state_mode']}"
        )
    if delta["research_board_changed"]:
        changes.append("research board changed")
    if delta["next_operator_action_changed"]:
        changes.append(
            "next operator action changed from "
            f"{delta['previous_next_operator_action']} to "
            f"{delta['current_next_operator_action']}"
        )

    if not changes:
        return (
            "Prior packet found; no tracked posture, decision, blocker, validation, "
            "broker-state, research-board, or operator-action fields changed."
        )
    return "Prior packet found; " + "; ".join(changes) + "."


def _build_history_entry(
    *,
    payload: Mapping[str, Any],
    sequence_number: int,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "history_entry_version": _HISTORY_ENTRY_VERSION,
        "sequence_number": sequence_number,
        "run_id": payload["run_id"],
        "as_of_date": payload["as_of_date"],
        "active_strategy_name": payload["active_strategy_name"],
        "input_data_path": payload["input_data_path"],
        "input_data_sha256": payload["input_data_sha256"],
        "posture": payload["posture"],
        "sma_posture_status": payload["sma_posture_status"],
        "preview_decision": payload["preview_decision"],
        "blocker_status": payload["blocker_status"],
        "validation_status": payload["validation_status"],
        "broker_state_mode": payload["broker_state_mode"],
        "broker_state_observed": payload["broker_state_observed"],
        "paper_submit_authorized": payload["paper_submit_authorized"],
        "paper_submit_authorization_status": payload[
            "paper_submit_authorization_status"
        ],
        "research_board_status": _research_board_status(payload),
        "research_board_fingerprint": _research_board_fingerprint(payload),
        "next_operator_action": payload["next_operator_action"],
        "delta_summary_text": payload["history_delta"]["delta_summary_text"],
        "safety_labels": list(payload["safety_labels"]),
    }
    entry["packet_summary_sha256"] = _history_entry_digest(entry)
    return entry


def _history_entry_digest(entry: Mapping[str, Any]) -> str:
    digest_source = {
        key: value
        for key, value in entry.items()
        if key != "packet_summary_sha256"
    }
    encoded = json.dumps(
        _json_safe(digest_source),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _research_board_status(payload: Mapping[str, Any]) -> str:
    research_lab = payload.get("research_lab")
    if not isinstance(research_lab, Mapping):
        return "research_lab_missing"
    candidate_board = research_lab.get("candidate_strategy_board")
    if not isinstance(candidate_board, list) or not candidate_board:
        return "candidate_strategy_board_empty"
    statuses = []
    for item in candidate_board:
        if isinstance(item, Mapping):
            statuses.append(str(item.get("status", "status_missing")))
        else:
            statuses.append("candidate_entry_not_object")
    return ",".join(statuses)


def _research_board_fingerprint(payload: Mapping[str, Any]) -> str:
    research_lab = payload.get("research_lab")
    candidate_board: Any = []
    if isinstance(research_lab, Mapping):
        candidate_board = research_lab.get("candidate_strategy_board", [])
    encoded = json.dumps(
        _json_safe(candidate_board),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_presence_status(output_root: Path) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    missing_artifacts: list[str] = []
    empty_artifacts: list[str] = []

    for kind, filename in _EXPECTED_ARTIFACTS:
        path = output_root / filename
        exists = path.exists() and path.is_file()
        non_empty = exists and path.stat().st_size > 0
        if not exists:
            missing_artifacts.append(kind)
        elif not non_empty:
            empty_artifacts.append(kind)
        artifacts[kind] = {
            "path": _normalize_path(path),
            "exists": exists,
            "non_empty": non_empty,
        }

    return {
        "status": "pass" if not missing_artifacts and not empty_artifacts else "fail",
        "missing_artifacts": missing_artifacts,
        "empty_artifacts": empty_artifacts,
        "artifacts": artifacts,
    }


def _read_packet_record(path: Path) -> tuple[Mapping[str, Any] | None, list[str]]:
    return _read_jsonl_mapping(path, "operating_record")


def _read_manifest_record(path: Path) -> tuple[Mapping[str, Any] | None, list[str]]:
    return _read_jsonl_mapping(path, "manifest")


def _read_jsonl_mapping(
    path: Path,
    artifact_name: str,
) -> tuple[Mapping[str, Any] | None, list[str]]:
    if not path.exists():
        return None, []
    try:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        return None, [f"{artifact_name}.readable"]
    if len(lines) != 1:
        return None, [f"{artifact_name}.single_jsonl_record"]
    try:
        record = json.loads(lines[0])
    except json.JSONDecodeError:
        return None, [f"{artifact_name}.parseable_jsonl"]
    if not isinstance(record, Mapping):
        return None, [f"{artifact_name}.record_object"]
    return record, []


def _missing_packet_fields(packet: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    for field_name in _REQUIRED_PACKET_FIELDS:
        if not _has_required_value(packet.get(field_name)):
            missing.append(field_name)

    if (
        "assistant_packet_version" not in missing
        and packet.get("assistant_packet_version") != _ASSISTANT_PACKET_VERSION
    ):
        missing.append("assistant_packet_version")
    if not _paper_submit_not_authorized(packet):
        missing.append("paper_submit_authorized_false_or_not_authorized")
    if packet.get("broker_state_observed") is not False:
        missing.append("broker_state_observed_false")
    if packet.get("broker_state_mode") not in {
        "broker_state_not_observed",
        "offline_preview_only",
    }:
        missing.append("broker_state_mode_offline_or_not_observed")

    labels = packet.get("safety_labels")
    if not isinstance(labels, list) or not labels:
        if "safety_labels" not in missing:
            missing.append("safety_labels")
    else:
        for label in _REQUIRED_LABELS:
            if label not in labels:
                missing.append(f"safety_labels.{label}")
    missing.extend(
        _missing_history_delta_fields("history_delta", packet.get("history_delta"))
    )
    return missing


def _missing_manifest_fields(
    output_root: Path,
    packet: Mapping[str, Any],
) -> list[str]:
    manifest, failures = _read_manifest_record(output_root / _MANIFEST_FILENAME)
    if manifest is None:
        return failures

    missing: list[str] = list(failures)
    for field_name in _REQUIRED_MANIFEST_FIELDS:
        if field_name == "missing_required_fields":
            if field_name not in manifest or not isinstance(
                manifest.get(field_name),
                list,
            ):
                missing.append(f"manifest.{field_name}")
        elif not _has_required_value(manifest.get(field_name)):
            missing.append(f"manifest.{field_name}")
    if not _paper_submit_not_authorized(manifest):
        missing.append("manifest.paper_submit_authorized_false_or_not_authorized")
    missing.extend(
        _missing_history_delta_fields(
            "manifest.history_delta",
            manifest.get("history_delta"),
        )
    )

    for field_name in (
        "input_data_path",
        "as_of_date",
        "active_strategy_name",
        "posture",
        "sma_posture_status",
        "preview_decision",
        "blocker_status",
        "broker_state_mode",
        "next_operator_action",
        "assistant_packet_version",
        "history_ledger_path",
    ):
        if field_name in packet and manifest.get(field_name) != packet.get(field_name):
            missing.append(f"manifest.{field_name}.matches_record")

    if (
        isinstance(packet.get("history_delta"), Mapping)
        and isinstance(manifest.get("history_delta"), Mapping)
        and dict(manifest["history_delta"]) != dict(packet["history_delta"])
    ):
        missing.append("manifest.history_delta.matches_record")

    return missing


def _missing_history_delta_fields(prefix: str, delta: Any) -> list[str]:
    if not isinstance(delta, Mapping):
        return [prefix]

    missing: list[str] = []
    for field_name in _REQUIRED_DELTA_FIELDS:
        if field_name not in delta:
            missing.append(f"{prefix}.{field_name}")

    summary_text = delta.get("delta_summary_text")
    if not isinstance(summary_text, str) or not summary_text.strip():
        if f"{prefix}.delta_summary_text" not in missing:
            missing.append(f"{prefix}.delta_summary_text")
    return missing


def _missing_brief_references(
    output_root: Path,
    packet: Mapping[str, Any],
) -> list[str]:
    brief_path = output_root / _BRIEF_FILENAME
    if not brief_path.exists():
        return []
    try:
        brief_text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return ["operating_brief.readable"]

    missing: list[str] = []
    for field_name in _BRIEF_REQUIRED_VALUE_FIELDS:
        value = packet.get(field_name)
        if _has_required_value(value) and str(value) not in brief_text:
            missing.append(f"operating_brief.{field_name}")

    if (
        "paper_submit_authorized=false" not in brief_text
        and "not_authorized" not in brief_text
    ):
        missing.append("operating_brief.paper_submit_authorized_false_or_not_authorized")
    for label in _REQUIRED_LABELS:
        if label not in brief_text:
            missing.append(f"operating_brief.safety_labels.{label}")
    delta = packet.get("history_delta")
    if isinstance(delta, Mapping):
        delta_summary = delta.get("delta_summary_text")
        if (
            isinstance(delta_summary, str)
            and delta_summary.strip()
            and delta_summary not in brief_text
        ):
            missing.append("operating_brief.history_delta.delta_summary_text")
    return missing


def _has_required_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _paper_submit_not_authorized(packet: Mapping[str, Any]) -> bool:
    status = str(packet.get("paper_submit_authorization_status", "")).strip()
    return packet.get("paper_submit_authorized") is False or status in _NOT_AUTHORIZED_STATUSES


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    return value


def _preview_decision(posture: str) -> str:
    if posture == "insufficient_history":
        return "insufficient_history"
    if posture == "bullish_risk_on":
        return "offline_preview_bullish_risk_on"
    return "offline_preview_defensive_risk_off"


def _next_operator_action(posture: str, slow_window: int) -> str:
    if posture == "insufficient_history":
        return f"provide_at_least_{slow_window}_usable_daily_bars_before_preview_use"
    return "review_assistant_brief_no_broker_action"


def _current_recommendation(posture: str) -> str:
    if posture == "insufficient_history":
        return (
            "Do not submit orders. The SMA preview is blocked until enough "
            "daily bars are available."
        )
    return (
        "Treat this as an offline research preview only. Do not submit paper or "
        "live orders from this packet."
    )


def _sma_status(
    *,
    posture: str,
    fast_window: int,
    slow_window: int,
    usable_bar_count: int,
) -> str:
    if posture == "insufficient_history":
        return (
            f"insufficient_history: {usable_bar_count} usable bars is fewer than "
            f"the {slow_window}-bar slow SMA requirement"
        )
    if posture == "bullish_risk_on":
        return f"risk_on: SMA{fast_window} is above SMA{slow_window}"
    return f"risk_off: SMA{fast_window} is at or below SMA{slow_window}"


def _data_freshness(*, as_of_date: str, latest_input_bar_date: str) -> dict[str, Any]:
    if as_of_date == latest_input_bar_date:
        status = "as_of_matches_latest_input_bar"
    elif as_of_date < latest_input_bar_date:
        status = "as_of_before_latest_input_bar"
    else:
        status = "as_of_after_latest_input_bar"
    return {
        "status": status,
        "as_of_date": as_of_date,
        "latest_input_bar_date": latest_input_bar_date,
        "freshness_basis": "input_csv_latest_bar_only",
        "wall_clock_staleness": "not_evaluated_by_offline_command",
    }


def _research_lab(
    *,
    config: EtfSmaDailyPaperLabConfig,
    as_of_date: str,
    posture: str,
    sma_status: str,
    sma_fast_value: str | None,
    sma_slow_value: str | None,
) -> dict[str, Any]:
    fast_value = sma_fast_value if sma_fast_value is not None else "not_available"
    slow_value = sma_slow_value if sma_slow_value is not None else "not_available"
    return {
        "active_strategy_evidence": [
            f"{config.symbol} daily bars loaded from {_normalize_path(config.bars_csv)}",
            (
                f"SMA {config.sma_fast_window}/{config.sma_slow_window} evaluated "
                f"as of {as_of_date}"
            ),
            f"posture={posture}",
            f"sma_status={sma_status}",
            f"sma_fast_value={fast_value}",
            f"sma_slow_value={slow_value}",
        ],
        "candidate_strategy_board": [
            {
                "candidate_name": "candidate_strategy_board_seed",
                "status": "placeholder_not_implemented",
                "hypothesis": (
                    "No alternate strategy hypothesis is active in Assistant v1.1; "
                    "SPY SMA 50/200 remains the only controlled test strategy."
                ),
                "required_evidence": [
                    "operator_and_GPT_approved_candidate_definition",
                    "offline_backtest_or_replay_evidence",
                    "dependency_direction_and_safety_review",
                    "paper_lab_only_promotion_packet",
                ],
                "next_research_action": (
                    "draft_candidate_hypothesis_for_GPT_review_before_any_strategy_code"
                ),
                "promotion_blockers": [
                    "no_candidate_strategy_selected",
                    "no_offline_evidence_collected",
                    "no_approval_to_expand_strategy_catalog",
                ],
            }
        ],
        "confidence_status": "confidence_not_yet_quantified",
        "missing_evidence": [
            "broker_state_not_observed",
            "multi_day_assistant_packet_history_not_yet_accumulated",
            "strategy_confidence_not_yet_quantified",
        ],
        "next_research_action": "accumulate_daily_assistant_packets_after_input_data_refresh",
    }


def _plain_english_status(payload: Mapping[str, Any]) -> str:
    fast_window = payload["sma_fast_window"]
    slow_window = payload["sma_slow_window"]
    as_of_date = payload["as_of_date"]
    posture = payload["posture"]
    if posture == "bullish_risk_on":
        return (
            f"As of {as_of_date}, SPY is risk-on under the SMA "
            f"{fast_window}/{slow_window} test."
        )
    if posture == "defensive_risk_off":
        return (
            f"As of {as_of_date}, SPY is risk-off under the SMA "
            f"{fast_window}/{slow_window} test."
        )
    return (
        f"As of {as_of_date}, the SMA {fast_window}/{slow_window} test has "
        "insufficient usable history."
    )


def _daniel_action_required(posture: str) -> str:
    if posture == "insufficient_history":
        return "Yes: provide enough daily input bars before relying on the preview."
    return (
        "No broker action is required. Daniel can review the packet and refresh "
        "input data outside this command when needed."
    )


def _render_brief_markdown(payload: dict[str, Any]) -> str:
    labels_list = "\n".join(f"* `{label}`" for label in payload["safety_labels"])
    artifact_lines = "\n".join(
        f"* **{name}**: `{path}`"
        for name, path in payload["artifact_paths"].items()
    )
    evidence_lines = "\n".join(
        f"* {item}" for item in payload["research_lab"]["active_strategy_evidence"]
    )
    missing_evidence_lines = "\n".join(
        f"* {item}" for item in payload["research_lab"]["missing_evidence"]
    )
    candidate_lines = _render_candidate_strategy_board(
        payload["research_lab"]["candidate_strategy_board"]
    )
    freshness = payload["data_freshness"]
    delta = payload["history_delta"]
    missing_required_fields = payload["missing_required_fields"]
    missing_required_fields_text = (
        "[]" if not missing_required_fields else ", ".join(missing_required_fields)
    )

    return f"""# Daily Trading Research Command Center

## Executive summary
* **Recommendation**: {payload["current_recommendation"]}
* **Evidence**: {payload["executive_summary"]["plain_english_status"]} Preview decision: `{payload["preview_decision"]}`.
* **Risks / blockers**: {payload["blocker_status"]}. {payload["broker_state_claim"]} Paper submit authorization is `{payload["paper_submit_authorization_status"]}` (`paper_submit_authorized=false`).
* **Delta since prior packet**: {delta["delta_summary_text"]}
* **Daniel action**: {payload["executive_summary"]["daniel_action_required"]}

## Trading desk brief
* **Active strategy**: {payload["active_strategy_name"]}
* **Market/posture state**: {payload["sma_posture_status"]}
* **Preview decision**: {payload["preview_decision"]}
* **Blocker status**: {payload["blocker_status"]}
* **Paper submit authorization status**: {payload["paper_submit_authorization_status"]} (`paper_submit_authorized=false`)
* **Broker-state mode**: {payload["broker_state_mode"]}
* **As-of date**: {payload["as_of_date"]}
* **Input data path**: `{payload["input_data_path"]}`

## Research lab section
* **Active strategy evidence**:
{evidence_lines}
* **Candidate strategy board**:
{candidate_lines}
* **Confidence status**: {payload["research_lab"]["confidence_status"]}
* **Missing evidence**:
{missing_evidence_lines}
* **Next research action**: {payload["research_lab"]["next_research_action"]}

## Executive dashboard
* **Data freshness**: {freshness["status"]} (latest input bar: {freshness["latest_input_bar_date"]}; basis: {freshness["freshness_basis"]}; wall-clock staleness: {freshness["wall_clock_staleness"]})
* **Validation status**: {payload["validation_status"]}
* **Assistant packet version**: {payload["assistant_packet_version"]}
* **Previous packet found**: {str(delta["previous_packet_found"]).lower()}
* **History ledger path**: `{payload["history_ledger_path"]}`
* **Missing required fields**: {missing_required_fields_text}
* **Artifact presence status**: {payload["artifact_presence_status"]["status"]}
* **Artifact paths**:
{artifact_lines}
* **System health**: {payload["system_health"]}
* **Safety labels**:
{labels_list}
* **Next operator action**: {payload["next_operator_action"]}
"""


def _render_candidate_strategy_board(candidate_board: list[Mapping[str, Any]]) -> str:
    if not candidate_board:
        return "* No candidate strategy placeholders are present."
    lines = [
        "| Candidate | Status | Hypothesis | Required evidence | Next research action | Promotion blockers |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in candidate_board:
        lines.append(
            "| "
            f"`{item['candidate_name']}` | "
            f"`{item['status']}` | "
            f"{item['hypothesis']} | "
            f"{', '.join(item['required_evidence'])} | "
            f"{item['next_research_action']} | "
            f"{', '.join(item['promotion_blockers'])} |"
        )
    return "\n".join(lines)


def _build_manifest(output_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    indexed_artifacts = {
        "assistant_brief": _artifact_metadata(output_root / _BRIEF_FILENAME),
        "operating_record": _artifact_metadata(output_root / _RECORD_FILENAME),
    }
    history_ledger_path = output_root / _HISTORY_LEDGER_FILENAME
    if history_ledger_path.exists():
        indexed_artifacts["history_ledger"] = _artifact_metadata(history_ledger_path)
    history_delta = dict(payload["history_delta"])
    return {
        "schema_version": _SCHEMA_VERSION,
        "assistant_version": _ASSISTANT_VERSION,
        "assistant_packet_version": payload["assistant_packet_version"],
        "manifest_type": "daily_trading_research_command_center_index",
        "command": _COMMAND,
        "script": _SCRIPT,
        "run_id": payload["run_id"],
        "as_of_date": payload["as_of_date"],
        "active_strategy_name": payload["active_strategy_name"],
        "input_data_path": payload["input_data_path"],
        "input_data_sha256": payload["input_data_sha256"],
        "posture": payload["posture"],
        "sma_posture_status": payload["sma_posture_status"],
        "preview_decision": payload["preview_decision"],
        "blocker_status": payload["blocker_status"],
        "broker_state_mode": payload["broker_state_mode"],
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "next_operator_action": payload["next_operator_action"],
        "safety_labels": list(_REQUIRED_LABELS),
        "validation_status": payload["validation_status"],
        "missing_required_fields": list(payload["missing_required_fields"]),
        "artifact_presence_status": dict(payload["artifact_presence_status"]),
        "artifact_paths": dict(payload["artifact_paths"]),
        "history_ledger_path": payload["history_ledger_path"],
        "history_delta": history_delta,
        "previous_packet_found": history_delta["previous_packet_found"],
        "previous_as_of_date": history_delta["previous_as_of_date"],
        "current_as_of_date": history_delta["current_as_of_date"],
        "posture_changed": history_delta["posture_changed"],
        "preview_decision_changed": history_delta["preview_decision_changed"],
        "blocker_status_changed": history_delta["blocker_status_changed"],
        "validation_status_changed": history_delta["validation_status_changed"],
        "broker_state_mode_changed": history_delta["broker_state_mode_changed"],
        "research_board_changed": history_delta["research_board_changed"],
        "next_operator_action_changed": history_delta[
            "next_operator_action_changed"
        ],
        "delta_summary_text": history_delta["delta_summary_text"],
        "indexed_artifacts": indexed_artifacts,
    }


def _artifact_metadata(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": _normalize_path(path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
