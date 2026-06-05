"""Offline intake and canonicalization for operator-supplied daily bars.

The intake command performs strict local file I/O only. It reuses the M398/M399
local daily-bars validator and writes deterministic local CSV plus JSONL
manifest evidence without broker, credential, or network behavior.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    LocalDailyBar,
    load_local_daily_bars_csv,
)

__all__ = [
    "LOCAL_DAILY_BARS_INTAKE_LABELS",
    "LocalDailyBarsIntakeConfig",
    "LocalDailyBarsIntakeManifestWriteResult",
    "build_local_daily_bars_intake_manifest",
    "render_local_daily_bars_intake_manifest_json",
    "render_local_daily_bars_intake_manifest_text",
    "write_local_daily_bars_intake_manifest_jsonl",
]


LOCAL_DAILY_BARS_INTAKE_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M400 - Offline operator local SPY daily bars intake and manifest"
_RECORD_TYPE = "local_daily_bars_intake_manifest"
_COMMAND = "local-daily-bars-intake"
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
class LocalDailyBarsIntakeConfig:
    """Explicit local inputs for one offline daily-bars intake."""

    run_id: str
    input_csv: Path | str
    output_csv: Path | str
    as_of: date | datetime | str
    symbol: str = _DEFAULT_SYMBOL
    required_usable_bars: int = _DEFAULT_REQUIRED_USABLE_BARS

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "input_csv",
            _input_csv_path(self.input_csv),
        )
        object.__setattr__(
            self,
            "output_csv",
            _output_csv_path(self.output_csv),
        )
        if self.as_of is None:
            raise ValidationError("as_of is required.")
        object.__setattr__(
            self,
            "required_usable_bars",
            _positive_int(self.required_usable_bars, "required_usable_bars"),
        )


@dataclass(frozen=True, slots=True)
class LocalDailyBarsIntakeManifestWriteResult:
    """Local JSONL write metadata for a single intake manifest record."""

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
        object.__setattr__(self, "output_path", _manifest_path(self.output_path))
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


def build_local_daily_bars_intake_manifest(
    config: LocalDailyBarsIntakeConfig,
) -> dict[str, object]:
    """Validate, canonicalize, and return one deterministic intake manifest."""

    checked_config = _config(config)
    input_sha256 = _sha256_file(checked_config.input_csv)
    bars = load_local_daily_bars_csv(
        checked_config.input_csv,
        symbol=checked_config.symbol,
        as_of=checked_config.as_of,
    )
    observed_columns = _observed_columns(checked_config.input_csv)
    accepted_bars = bars.usable_bars
    _write_canonical_csv(checked_config.output_csv, accepted_bars)
    output_sha256 = _sha256_file(checked_config.output_csv)

    usable_bar_count = len(accepted_bars)
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
        "scope": f"{checked_config.symbol}_paper_lab_only",
        "labels": list(LOCAL_DAILY_BARS_INTAKE_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "input_csv": str(checked_config.input_csv),
        "output_csv": str(checked_config.output_csv),
        "csv_schema": list(LOCAL_DAILY_BARS_CSV_COLUMNS),
        "required_columns": list(LOCAL_DAILY_BARS_CSV_COLUMNS),
        "observed_columns": observed_columns,
        "input_sha256": input_sha256,
        "output_sha256": output_sha256,
        "input_row_count": bars.total_row_count,
        "accepted_row_count": usable_bar_count,
        "wrong_symbol_row_count": bars.ignored_wrong_symbol_row_count,
        "future_bar_count_excluded": bars.ignored_future_bar_count,
        "duplicate_date_count": 0,
        "first_bar_date": _first_bar_date(accepted_bars),
        "last_bar_date": _last_bar_date(accepted_bars),
        "input_sorted_by_date": bars.input_sorted_by_date,
        "canonical_sorted_by_date": True,
        "required_usable_bars": checked_config.required_usable_bars,
        "usable_bar_count": usable_bar_count,
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


def render_local_daily_bars_intake_manifest_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_local_daily_bars_intake_manifest_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing intake summary."""

    return "\n".join(
        (
            "Local daily bars intake manifest",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"as_of: {payload.get('as_of', '')}",
            f"input_csv: {payload.get('input_csv', '')}",
            f"output_csv: {payload.get('output_csv', '')}",
            f"input_row_count: {payload.get('input_row_count', '')}",
            f"accepted_row_count: {payload.get('accepted_row_count', '')}",
            "wrong_symbol_row_count: "
            f"{payload.get('wrong_symbol_row_count', '')}",
            "future_bar_count_excluded: "
            f"{payload.get('future_bar_count_excluded', '')}",
            f"usable_bar_count: {payload.get('usable_bar_count', '')}",
            f"required_usable_bars: {payload.get('required_usable_bars', '')}",
            f"missing_usable_bars: {payload.get('missing_usable_bars', '')}",
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


def write_local_daily_bars_intake_manifest_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> LocalDailyBarsIntakeManifestWriteResult:
    """Write exactly one JSONL intake manifest record, replacing prior contents."""

    path = _manifest_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_local_daily_bars_intake_manifest_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(line)
    return LocalDailyBarsIntakeManifestWriteResult(
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


def _write_canonical_csv(path: Path, bars: tuple[LocalDailyBar, ...]) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(LOCAL_DAILY_BARS_CSV_COLUMNS)
        for bar in bars:
            writer.writerow(_canonical_row(bar))


def _canonical_row(bar: LocalDailyBar) -> tuple[str, str, str, str, str, str, str, str]:
    return (
        bar.symbol,
        bar.date.isoformat(),
        _decimal_text(bar.open),
        _decimal_text(bar.high),
        _decimal_text(bar.low),
        _decimal_text(bar.close),
        _decimal_text(bar.adjusted_close),
        str(bar.volume),
    )


def _observed_columns(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            return [str(column) for column in next(reader)]
        except StopIteration as exc:
            raise ValidationError("input_csv must include a header row.") from exc


def _input_csv_path(value: object) -> Path:
    path = _local_csv_path(value, "input_csv")
    if not path.is_file():
        raise ValidationError("input_csv must reference an existing local CSV file.")
    return path


def _output_csv_path(value: object) -> Path:
    path = _local_csv_path(value, "output_csv")
    if path.exists() and path.is_dir():
        raise ValidationError("output_csv must not be a directory.")
    return path


def _manifest_path(value: object) -> Path:
    path = _required_path(value, "run_log")
    if path.exists() and path.is_dir():
        raise ValidationError("run_log must not be a directory.")
    return path


def _local_csv_path(value: object, field_name: str) -> Path:
    path = _required_path(value, field_name)
    if type(value) is str and "://" in value:
        raise ValidationError(f"{field_name} must be a local CSV path.")
    if path.suffix.lower() != ".csv":
        raise ValidationError(f"{field_name} must reference a CSV file.")
    return path


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


def _first_bar_date(bars: tuple[LocalDailyBar, ...]) -> str:
    if not bars:
        return ""
    return bars[0].date.isoformat()


def _last_bar_date(bars: tuple[LocalDailyBar, ...]) -> str:
    if not bars:
        return ""
    return bars[-1].date.isoformat()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _config(value: object) -> LocalDailyBarsIntakeConfig:
    if type(value) is not LocalDailyBarsIntakeConfig:
        raise ValidationError("config must be a LocalDailyBarsIntakeConfig.")
    return value


def _forbidden_actions() -> list[str]:
    return [
        "broker_mutation_from_local_daily_bars_intake",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_local_daily_bars_intake",
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
