"""Offline checkpoint evidence for operator-owned local daily bars.

This module performs deterministic local file I/O only. It reuses the strict
local daily-bars CSV reader and does not load profiles, inspect credentials,
import broker adapters, open sockets, or expose broker mutation behavior.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    load_local_daily_bars_csv,
)

__all__ = [
    "LOCAL_DAILY_BARS_CHECKPOINT_LABELS",
    "LocalDailyBarsCheckpointConfig",
    "LocalDailyBarsCheckpointWriteResult",
    "build_local_daily_bars_checkpoint",
    "render_local_daily_bars_checkpoint_json",
    "render_local_daily_bars_checkpoint_text",
    "write_local_daily_bars_checkpoint_jsonl",
]


LOCAL_DAILY_BARS_CHECKPOINT_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M399 - Offline local daily bars validation checkpoint"
_RECORD_TYPE = "local_daily_bars_checkpoint"
_COMMAND = "local-daily-bars-checkpoint"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_REQUIRED_USABLE_BARS = 200
_PROFIT_CLAIM = "none"
_FALSE_SAFETY_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class LocalDailyBarsCheckpointConfig:
    """Explicit local inputs for one deterministic daily-bars checkpoint."""

    run_id: str
    daily_bars_csv: Path | str
    as_of: date | datetime | str
    symbol: str = _DEFAULT_SYMBOL
    required_usable_bars: int = _DEFAULT_REQUIRED_USABLE_BARS

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "daily_bars_csv",
            _required_path(self.daily_bars_csv, "daily_bars_csv"),
        )
        if self.as_of is None:
            raise ValidationError("as_of is required.")
        object.__setattr__(
            self,
            "required_usable_bars",
            _positive_int(self.required_usable_bars, "required_usable_bars"),
        )


@dataclass(frozen=True, slots=True)
class LocalDailyBarsCheckpointWriteResult:
    """Local JSONL write metadata for a single checkpoint record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_actions_performed: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if self.newline_terminated is not True:
            raise ValidationError("newline_terminated must be true.")
        for field_name in _FALSE_SAFETY_FIELDS:
            if getattr(self, field_name) is not False:
                raise ValidationError(f"{field_name} must be false.")

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


def build_local_daily_bars_checkpoint(
    config: LocalDailyBarsCheckpointConfig,
) -> dict[str, object]:
    """Build one fail-closed checkpoint from a strict local daily-bars CSV."""

    checked_config = _config(config)
    bars = load_local_daily_bars_csv(
        checked_config.daily_bars_csv,
        symbol=checked_config.symbol,
        as_of=checked_config.as_of,
    )
    observed_columns = _observed_columns(bars.path)
    usable_bar_count = bars.observed_usable_bars
    missing_usable_bars = max(
        checked_config.required_usable_bars - usable_bar_count,
        0,
    )
    readiness_state = "ready" if missing_usable_bars == 0 else "insufficient_history"
    readiness_reason = (
        "sma_usable_bars_ready"
        if readiness_state == "ready"
        else "sma_insufficient_history"
    )
    blockers = [] if readiness_state == "ready" else ["missing_usable_bars"]
    broker_action_flags = _broker_action_flags()

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "symbol": checked_config.symbol,
        "as_of": "" if bars.as_of_date is None else bars.as_of_date.isoformat(),
        "scope": "SPY_paper_lab_only",
        "labels": list(LOCAL_DAILY_BARS_CHECKPOINT_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "daily_bars_csv": str(bars.path),
        "csv_schema": list(LOCAL_DAILY_BARS_CSV_COLUMNS),
        "required_columns": list(LOCAL_DAILY_BARS_CSV_COLUMNS),
        "observed_columns": observed_columns,
        "total_row_count": bars.total_row_count,
        "row_count_for_symbol": bars.matching_symbol_row_count,
        "wrong_symbol_row_count_ignored": bars.ignored_wrong_symbol_row_count,
        "usable_bar_count": usable_bar_count,
        "first_bar_date": _first_usable_date(bars.usable_bars),
        "last_bar_date": _last_usable_date(bars.usable_bars),
        "future_bar_count_excluded": bars.ignored_future_bar_count,
        "duplicate_date_count": 0,
        "input_sorted_by_date": bars.input_sorted_by_date,
        "required_usable_bars": checked_config.required_usable_bars,
        "missing_usable_bars": missing_usable_bars,
        "readiness_state": readiness_state,
        "readiness_reason": readiness_reason,
        "blockers": blockers,
        "safety_summary": {
            "paper_lab_only": True,
            "broker_mutation_allowed": False,
            "not_live_authorized": True,
            "live_authorized": False,
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "broker_actions_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "broker_action_flags": broker_action_flags,
        },
        "broker_action_flags": broker_action_flags,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "forbidden_actions": _forbidden_actions(),
        "next_forbidden_action": _forbidden_actions(),
    }


def render_local_daily_bars_checkpoint_json(payload: Mapping[str, object]) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_local_daily_bars_checkpoint_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-facing local daily-bars summary."""

    return "\n".join(
        (
            "Local daily bars checkpoint",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"as_of: {payload.get('as_of', '')}",
            f"daily_bars_csv: {payload.get('daily_bars_csv', '')}",
            f"row_count_for_symbol: {payload.get('row_count_for_symbol', '')}",
            f"usable_bar_count: {payload.get('usable_bar_count', '')}",
            f"required_usable_bars: {payload.get('required_usable_bars', '')}",
            f"missing_usable_bars: {payload.get('missing_usable_bars', '')}",
            "future_bar_count_excluded: "
            f"{payload.get('future_bar_count_excluded', '')}",
            f"readiness_state: {payload.get('readiness_state', '')}",
            f"readiness_reason: {payload.get('readiness_reason', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_actions_performed: "
            f"{_bool_text(payload.get('broker_actions_performed'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_local_daily_bars_checkpoint_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> LocalDailyBarsCheckpointWriteResult:
    """Write exactly one JSONL checkpoint record, replacing prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_local_daily_bars_checkpoint_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return LocalDailyBarsCheckpointWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _observed_columns(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            return [str(column) for column in next(reader)]
        except StopIteration as exc:
            raise ValidationError("daily_bars_csv must include a header row.") from exc


def _first_usable_date(bars: tuple[object, ...]) -> str:
    if not bars:
        return ""
    return str(getattr(bars[0], "date")).strip()


def _last_usable_date(bars: tuple[object, ...]) -> str:
    if not bars:
        return ""
    return str(getattr(bars[-1], "date")).strip()


def _forbidden_actions() -> list[str]:
    return [
        "broker_mutation_from_local_daily_bars_checkpoint",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_local_daily_bars_checkpoint",
    ]


def _broker_action_flags() -> dict[str, bool]:
    return {
        "submit": False,
        "cancel": False,
        "replace": False,
        "close": False,
        "liquidate": False,
        "mutation": False,
    }


def _config(value: object) -> LocalDailyBarsCheckpointConfig:
    if type(value) is not LocalDailyBarsCheckpointConfig:
        raise ValidationError("config must be a LocalDailyBarsCheckpointConfig.")
    return value


def _required_path(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _output_path(value: object) -> Path:
    path = _required_path(value, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
