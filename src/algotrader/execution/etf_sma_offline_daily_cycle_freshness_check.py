"""Offline freshness gate for an accepted ETF/SMA daily cycle manifest.

This module reads one local M444 manifest plus one local adjusted SPY daily-bars
CSV and emits one M445 freshness record. It does not import runtime config,
broker SDKs, credentials, sockets, or broker mutation behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
from io import StringIO
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaOfflineDailyCycleFreshnessCheckConfig",
    "EtfSmaOfflineDailyCycleFreshnessCheckWriteResult",
    "build_etf_sma_offline_daily_cycle_freshness_check",
    "render_etf_sma_offline_daily_cycle_freshness_check_json",
    "render_etf_sma_offline_daily_cycle_freshness_check_text",
    "run_etf_sma_offline_daily_cycle_freshness_check",
    "write_etf_sma_offline_daily_cycle_freshness_check_jsonl",
]


_MILESTONE = "M445"
_RECORD_TYPE = "etf_sma_offline_daily_cycle_freshness_check"
_COMMAND = "etf-sma-offline-daily-cycle-freshness-check"
_DEFAULT_RUN_ID = "m445_offline_daily_cycle_freshness_check"
_DEFAULT_SOURCE_M444_PATH = (
    "runs/paper_lab/m444_offline_daily_cycle_run_manifest.jsonl"
)
_DEFAULT_DAILY_BARS_CSV_PATH = (
    "runs/operator_input/spy_daily_tiingo_adjusted_canonical_20260607.csv"
)
_DEFAULT_OUTPUT_JSONL = (
    "runs/paper_lab/m445_offline_daily_cycle_freshness_check.jsonl"
)
_FRESHNESS_ACCEPTED_CURRENT = "accepted_current_local_bars"
_FRESHNESS_ACCEPTED_AHEAD = "accepted_local_bars_ahead_of_expected"
_FRESHNESS_BLOCKED_STALE = "blocked_stale_local_bars"
_FRESHNESS_BLOCKED_M444 = "blocked_m444_manifest"
_FRESHNESS_BLOCKED_CSV = "blocked_daily_bars_csv"
_EXPECTED_DAILY_CHAIN_STATE = "accepted_observe_hold_noop"
_EXPECTED_CYCLE_DECISION = "hold/noop"
_EXPECTED_VALIDATION_STATE = "accepted_current_cycle_hold_noop"
_EXPECTED_DAILY_WRAPPER_STATE = "accepted_observe_hold_noop"
_EXPECTED_OPERATOR_ACTION = "observe_hold_noop"
_PROFIT_CLAIM = "none"
_OUTPUT_FALSE_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "live_authorized",
    "network_access_attempted",
    "credential_access_attempted",
)
_OPTIONAL_M444_FALSE_FIELDS = (
    "broker_actions_performed",
    "broker_access_attempted",
    "broker_mutation_authorized",
    "broker_mutation_allowed",
)


@dataclass(frozen=True, slots=True)
class EtfSmaOfflineDailyCycleFreshnessCheckConfig:
    """Explicit local inputs for one deterministic M445 freshness check."""

    run_id: str = _DEFAULT_RUN_ID
    source_m444_path: Path | str = _DEFAULT_SOURCE_M444_PATH
    source_daily_bars_csv_path: Path | str = _DEFAULT_DAILY_BARS_CSV_PATH
    output_jsonl: Path | str = _DEFAULT_OUTPUT_JSONL
    expected_latest_bar_date: date | str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_m444_path",
            _required_path(self.source_m444_path, "source_m444_path"),
        )
        object.__setattr__(
            self,
            "source_daily_bars_csv_path",
            _required_path(
                self.source_daily_bars_csv_path,
                "source_daily_bars_csv_path",
            ),
        )
        object.__setattr__(
            self,
            "output_jsonl",
            _required_path(self.output_jsonl, "output_jsonl"),
        )
        object.__setattr__(
            self,
            "expected_latest_bar_date",
            _required_date_text(
                self.expected_latest_bar_date,
                "expected_latest_bar_date",
            ),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaOfflineDailyCycleFreshnessCheckWriteResult:
    """Local JSONL write metadata for a single M445 freshness record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    paper_action_authorized: bool
    submit_authorized: bool
    paper_submit_authorized: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        for field_name in _OUTPUT_FALSE_FIELDS:
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "paper_action_authorized": self.paper_action_authorized,
            "submit_authorized": self.submit_authorized,
            "paper_submit_authorized": self.paper_submit_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _M444Read:
    path: Path
    found: bool
    parsed: bool
    record_count: int
    record: dict[str, object] | None
    error: str
    sha256: str


@dataclass(frozen=True, slots=True)
class _DailyBarsCsvRead:
    path: Path
    found: bool
    parsed: bool
    row_count: int
    latest_bar_date: str
    error: str
    sha256: str


def run_etf_sma_offline_daily_cycle_freshness_check(
    config: EtfSmaOfflineDailyCycleFreshnessCheckConfig,
) -> dict[str, object]:
    """Build and write one deterministic M445 freshness-check record."""

    checked_config = _config(config)
    payload = build_etf_sma_offline_daily_cycle_freshness_check(checked_config)
    write_etf_sma_offline_daily_cycle_freshness_check_jsonl(
        payload,
        checked_config.output_jsonl,
    )
    return payload


def build_etf_sma_offline_daily_cycle_freshness_check(
    config: EtfSmaOfflineDailyCycleFreshnessCheckConfig,
) -> dict[str, object]:
    """Build one fail-closed freshness record from local M444 and CSV inputs."""

    checked_config = _config(config)
    source_m444 = _read_m444_jsonl(checked_config.source_m444_path)
    daily_bars_csv = _read_daily_bars_csv(
        checked_config.source_daily_bars_csv_path,
    )
    m444_record = source_m444.record or {}

    m444_blockers = _m444_blockers(source_m444)
    csv_blockers = _daily_bars_csv_blockers(daily_bars_csv)
    latest_local_bar_date = daily_bars_csv.latest_bar_date
    expected_latest_bar_date = checked_config.expected_latest_bar_date
    freshness_blockers = [*m444_blockers, *csv_blockers]
    freshness_warnings: list[str] = []

    if m444_blockers:
        freshness_state = _FRESHNESS_BLOCKED_M444
    elif csv_blockers:
        freshness_state = _FRESHNESS_BLOCKED_CSV
    else:
        latest_date = _parse_date(latest_local_bar_date)
        expected_date = _parse_date(expected_latest_bar_date)
        if latest_date is None or expected_date is None:
            freshness_state = _FRESHNESS_BLOCKED_CSV
            freshness_blockers.append("latest_local_bar_date_unparseable")
        elif latest_date < expected_date:
            freshness_state = _FRESHNESS_BLOCKED_STALE
            freshness_blockers.append("latest_local_bar_date_before_expected")
        elif latest_date > expected_date:
            freshness_state = _FRESHNESS_ACCEPTED_AHEAD
            freshness_warnings.append("latest_local_bar_date_after_expected")
        else:
            freshness_state = _FRESHNESS_ACCEPTED_CURRENT

    return {
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": checked_config.run_id,
        "freshness_state": freshness_state,
        "expected_latest_bar_date": expected_latest_bar_date,
        "latest_local_bar_date": latest_local_bar_date,
        "source_m444_path": str(source_m444.path),
        "source_m444_sha256": source_m444.sha256,
        "source_daily_bars_csv_path": str(daily_bars_csv.path),
        "source_daily_bars_csv_sha256": daily_bars_csv.sha256,
        "daily_chain_state": _text(m444_record.get("daily_chain_state")),
        "readiness_cycle_decision": _text(
            m444_record.get("readiness_cycle_decision")
        ),
        "validation_state": _text(m444_record.get("validation_state")),
        "daily_wrapper_state": _text(m444_record.get("daily_wrapper_state")),
        "recommended_operator_action": _text(
            m444_record.get("recommended_operator_action")
        ),
        "freshness_blockers": list(_dedupe(tuple(freshness_blockers))),
        "freshness_warnings": freshness_warnings,
        "paper_action_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "profit_claim": _PROFIT_CLAIM,
    }


def render_etf_sma_offline_daily_cycle_freshness_check_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_offline_daily_cycle_freshness_check_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing M445 freshness summary."""

    blockers = _string_list(payload.get("freshness_blockers"))
    warnings = _string_list(payload.get("freshness_warnings"))
    blocker_text = ", ".join(blockers) if blockers else "none"
    warning_text = ", ".join(warnings) if warnings else "none"
    return "\n".join(
        (
            "ETF/SMA offline daily cycle freshness check",
            f"run_id: {payload.get('run_id', '')}",
            f"freshness_state: {payload.get('freshness_state', '')}",
            f"expected_latest_bar_date: {payload.get('expected_latest_bar_date', '')}",
            f"latest_local_bar_date: {payload.get('latest_local_bar_date', '')}",
            f"source_m444_path: {payload.get('source_m444_path', '')}",
            "source_daily_bars_csv_path: "
            f"{payload.get('source_daily_bars_csv_path', '')}",
            f"daily_chain_state: {payload.get('daily_chain_state', '')}",
            "readiness_cycle_decision: "
            f"{payload.get('readiness_cycle_decision', '')}",
            f"validation_state: {payload.get('validation_state', '')}",
            f"daily_wrapper_state: {payload.get('daily_wrapper_state', '')}",
            "recommended_operator_action: "
            f"{payload.get('recommended_operator_action', '')}",
            f"paper_action_authorized: {_bool_text(payload.get('paper_action_authorized'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            f"paper_submit_authorized: {_bool_text(payload.get('paper_submit_authorized'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"freshness_warnings: {warning_text}",
            f"freshness_blockers: {blocker_text}",
        )
    )


def write_etf_sma_offline_daily_cycle_freshness_check_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaOfflineDailyCycleFreshnessCheckWriteResult:
    """Write exactly one M445 freshness record, replacing prior contents."""

    checked_payload = dict(payload)
    _validate_output_safety_fields(checked_payload)
    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_offline_daily_cycle_freshness_check_json(
        checked_payload
    ) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaOfflineDailyCycleFreshnessCheckWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        paper_action_authorized=False,
        submit_authorized=False,
        paper_submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _m444_blockers(source_m444: _M444Read) -> list[str]:
    blockers = _m444_artifact_blockers(source_m444)
    record = source_m444.record
    if record is None:
        return blockers

    field_expectations = (
        (
            "daily_chain_state",
            _EXPECTED_DAILY_CHAIN_STATE,
            "source_m444_daily_chain_state_not_accepted_observe_hold_noop",
        ),
        (
            "readiness_cycle_decision",
            _EXPECTED_CYCLE_DECISION,
            "source_m444_readiness_cycle_decision_not_hold_noop",
        ),
        (
            "validation_state",
            _EXPECTED_VALIDATION_STATE,
            "source_m444_validation_state_not_accepted_current_cycle_hold_noop",
        ),
        (
            "daily_wrapper_state",
            _EXPECTED_DAILY_WRAPPER_STATE,
            "source_m444_daily_wrapper_state_not_accepted_observe_hold_noop",
        ),
        (
            "recommended_operator_action",
            _EXPECTED_OPERATOR_ACTION,
            "source_m444_recommended_operator_action_not_observe_hold_noop",
        ),
    )
    for field_name, expected_value, blocker in field_expectations:
        if _text(record.get(field_name)) != expected_value:
            blockers.append(blocker)

    for cycle_field in ("validation_cycle_decision", "summary_cycle_decision"):
        cycle_decision = _text(record.get(cycle_field))
        if cycle_decision and cycle_decision != _EXPECTED_CYCLE_DECISION:
            blockers.append(f"source_m444_{cycle_field}_not_hold_noop")

    if _string_list(record.get("chain_blockers")):
        blockers.append("source_m444_chain_blockers_present")

    for field_name in _OUTPUT_FALSE_FIELDS:
        if record.get(field_name) is not False:
            blockers.append(f"source_m444_{field_name}_not_false")
    for field_name in _OPTIONAL_M444_FALSE_FIELDS:
        if record.get(field_name) is True:
            blockers.append(f"source_m444_{field_name}_true")

    if _text(record.get("profit_claim")) != _PROFIT_CLAIM:
        blockers.append("source_m444_profit_claim_not_none")

    return list(_dedupe(tuple(blockers)))


def _m444_artifact_blockers(source_m444: _M444Read) -> list[str]:
    if not source_m444.found:
        return ["source_m444_missing"]
    if not source_m444.parsed:
        return ["source_m444_malformed"]
    if source_m444.record_count == 0:
        return ["source_m444_zero_records"]
    if source_m444.record_count > 1:
        return ["source_m444_multiple_records"]
    if source_m444.record is None:
        return ["source_m444_missing_record"]
    return []


def _daily_bars_csv_blockers(daily_bars_csv: _DailyBarsCsvRead) -> list[str]:
    if not daily_bars_csv.found:
        return ["source_daily_bars_csv_missing"]
    if not daily_bars_csv.parsed:
        if daily_bars_csv.error:
            return [f"source_daily_bars_csv_{daily_bars_csv.error}"]
        return ["source_daily_bars_csv_malformed"]
    if not daily_bars_csv.latest_bar_date:
        return ["source_daily_bars_csv_no_latest_bar_date"]
    return []


def _read_m444_jsonl(path: Path) -> _M444Read:
    if not path.exists():
        return _M444Read(
            path=path,
            found=False,
            parsed=False,
            record_count=0,
            record=None,
            error="path_not_found",
            sha256="",
        )
    if not path.is_file():
        return _M444Read(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            record=None,
            error="path_not_file",
            sha256="",
        )

    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _M444Read(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            record=None,
            error="utf8_decode_error",
            sha256=sha256,
        )

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return _M444Read(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                record=None,
                error=f"invalid_jsonl_line_{line_number}",
                sha256=sha256,
            )
        if not isinstance(payload, Mapping):
            return _M444Read(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                record=None,
                error=f"non_object_jsonl_line_{line_number}",
                sha256=sha256,
            )
        records.append(dict(payload))

    if len(records) != 1:
        return _M444Read(
            path=path,
            found=True,
            parsed=True,
            record_count=len(records),
            record=None,
            error="record_count_not_one",
            sha256=sha256,
        )
    return _M444Read(
        path=path,
        found=True,
        parsed=True,
        record_count=1,
        record=records[0],
        error="",
        sha256=sha256,
    )


def _read_daily_bars_csv(path: Path) -> _DailyBarsCsvRead:
    if not path.exists():
        return _DailyBarsCsvRead(
            path=path,
            found=False,
            parsed=False,
            row_count=0,
            latest_bar_date="",
            error="path_not_found",
            sha256="",
        )
    if not path.is_file():
        return _DailyBarsCsvRead(
            path=path,
            found=True,
            parsed=False,
            row_count=0,
            latest_bar_date="",
            error="path_not_file",
            sha256="",
        )

    data = path.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _DailyBarsCsvRead(
            path=path,
            found=True,
            parsed=False,
            row_count=0,
            latest_bar_date="",
            error="utf8_decode_error",
            sha256=sha256,
        )

    try:
        reader = csv.DictReader(StringIO(text))
    except csv.Error:
        return _DailyBarsCsvRead(
            path=path,
            found=True,
            parsed=False,
            row_count=0,
            latest_bar_date="",
            error="malformed",
            sha256=sha256,
        )
    date_column = _date_column(reader.fieldnames)
    if date_column is None:
        return _DailyBarsCsvRead(
            path=path,
            found=True,
            parsed=False,
            row_count=0,
            latest_bar_date="",
            error="date_column_missing",
            sha256=sha256,
        )

    latest_bar_date: date | None = None
    row_count = 0
    try:
        for row in reader:
            if not _has_row_values(row):
                continue
            row_count += 1
            row_date = _parse_date(_text(row.get(date_column)))
            if row_date is None:
                return _DailyBarsCsvRead(
                    path=path,
                    found=True,
                    parsed=False,
                    row_count=row_count,
                    latest_bar_date="",
                    error="date_value_malformed",
                    sha256=sha256,
                )
            if latest_bar_date is None or row_date > latest_bar_date:
                latest_bar_date = row_date
    except csv.Error:
        return _DailyBarsCsvRead(
            path=path,
            found=True,
            parsed=False,
            row_count=row_count,
            latest_bar_date="",
            error="malformed",
            sha256=sha256,
        )

    if latest_bar_date is None:
        return _DailyBarsCsvRead(
            path=path,
            found=True,
            parsed=False,
            row_count=row_count,
            latest_bar_date="",
            error="no_rows",
            sha256=sha256,
        )
    return _DailyBarsCsvRead(
        path=path,
        found=True,
        parsed=True,
        row_count=row_count,
        latest_bar_date=latest_bar_date.isoformat(),
        error="",
        sha256=sha256,
    )


def _config(
    config: EtfSmaOfflineDailyCycleFreshnessCheckConfig,
) -> EtfSmaOfflineDailyCycleFreshnessCheckConfig:
    if not isinstance(config, EtfSmaOfflineDailyCycleFreshnessCheckConfig):
        raise ValidationError(
            "config must be an EtfSmaOfflineDailyCycleFreshnessCheckConfig."
        )
    return config


def _validate_output_safety_fields(payload: Mapping[str, object]) -> None:
    for field_name in _OUTPUT_FALSE_FIELDS:
        _false_bool(payload.get(field_name), field_name)
    if _text(payload.get("profit_claim")) != _PROFIT_CLAIM:
        raise ValidationError("profit_claim must be none.")


def _required_string(value: object, field_name: str) -> str:
    text = _text(value)
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    if not str(path):
        raise ValidationError(f"{field_name} is required.")
    return path


def _output_path(value: Path | str) -> Path:
    path = value if isinstance(value, Path) else Path(str(value))
    if not str(path):
        raise ValidationError("output_path is required.")
    return path


def _required_date_text(value: date | str, field_name: str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    text = _text(value)
    if not text:
        raise ValidationError(f"{field_name} is required.")
    parsed = _parse_date(text)
    if parsed is None or parsed.isoformat() != text:
        raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.")
    return text


def _parse_date(value: object) -> date | None:
    text = _text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _date_column(fieldnames: Sequence[str] | None) -> str | None:
    if fieldnames is None:
        return None
    for fieldname in fieldnames:
        if fieldname.strip().lower() == "date":
            return fieldname
    return None


def _has_row_values(row: Mapping[str, object]) -> bool:
    return any(_text(value) for value in row.values())


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _string_list(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        text = _text(value)
        return (text,) if text else ()
    if not isinstance(value, Iterable) or isinstance(value, Mapping):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_json_safe(item) for item in value]
    return value
