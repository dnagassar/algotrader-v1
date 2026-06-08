"""Offline validation gate for unified ETF/SMA cycle readiness packets.

This module reads one explicit local JSONL packet and writes one validation
record. It does not import runtime config, broker SDKs, credentials, sockets,
or broker mutation behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "EtfSmaCyclePacketValidationConfig",
    "EtfSmaCyclePacketValidationWriteResult",
    "build_etf_sma_cycle_packet_validation",
    "render_etf_sma_cycle_packet_validation_json",
    "render_etf_sma_cycle_packet_validation_text",
    "write_etf_sma_cycle_packet_validation_jsonl",
]


_MILESTONE = "M442 - Offline unified cycle packet validator"
_RECORD_TYPE = "etf_sma_cycle_packet_validation"
_COMMAND = "etf-sma-cycle-packet-validator"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_MAX_AGE_HOURS = Decimal("24")
_DEFAULT_VALIDATED_AT = "1970-01-01T00:00:00+00:00"
_PROFIT_CLAIM = "none"
_ACCEPTED_HOLD_NOOP_STATE = "accepted_current_cycle_hold_noop"
_ACCEPTED_OBSERVE_STATE = "accepted_current_cycle_observe_only"
_BLOCKED_STATE = "blocked_unified_cycle_packet_validation"
_OBSERVE_HOLD_NOOP_ACTION = "observe_hold_noop"
_OPERATOR_REVIEW_ACTION = "operator_review_only"
_RESOLVE_BLOCKERS_ACTION = "resolve_validation_blockers"
_POSTURES = frozenset(("risk_on", "risk_off", "insufficient_history"))
_WRITE_RESULT_FALSE_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaCyclePacketValidationConfig:
    """Explicit local inputs for one deterministic packet validation."""

    run_id: str
    source_packet_path: Path | str
    validated_at: datetime | str | None = None
    max_age_hours: Decimal | int | str = _DEFAULT_MAX_AGE_HOURS

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_packet_path",
            _required_path(self.source_packet_path, "source_packet_path"),
        )
        object.__setattr__(
            self,
            "validated_at",
            _optional_timestamp_text(self.validated_at, "validated_at"),
        )
        object.__setattr__(
            self,
            "max_age_hours",
            _positive_decimal(self.max_age_hours, "max_age_hours"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaCyclePacketValidationWriteResult:
    """Local JSONL write metadata for a single validation record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    paper_action_authorized: bool
    submit_authorized: bool
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
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        for field_name in _WRITE_RESULT_FALSE_FIELDS:
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
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _PacketRead:
    path: Path
    found: bool
    parsed: bool
    record_count: int
    record: dict[str, object] | None
    error: str
    sha256: str


def build_etf_sma_cycle_packet_validation(
    config: EtfSmaCyclePacketValidationConfig,
) -> dict[str, object]:
    """Build one fail-closed validation record from a local cycle packet."""

    checked_config = _config(config)
    packet_read = _read_packet(checked_config.source_packet_path)
    source_record = packet_read.record or {}
    source_as_of = _text(source_record.get("as_of"))
    source_as_of_at = _parse_timestamp(source_as_of)
    validated_at = checked_config.validated_at
    if validated_at is None and source_as_of_at is not None:
        validated_at = source_as_of
    elif validated_at is None:
        validated_at = _DEFAULT_VALIDATED_AT
    validated_at_at = _parse_timestamp(validated_at)

    blockers = _validation_blockers(
        packet_read=packet_read,
        source_record=source_record,
        source_as_of_at=source_as_of_at,
        validated_at_at=validated_at_at,
        max_age_hours=checked_config.max_age_hours,
    )
    cycle_decision = _text(source_record.get("cycle_decision"))
    validation_state = _validation_state(blockers, cycle_decision)

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "source_packet_path": str(packet_read.path),
        "source_packet_sha256": packet_read.sha256,
        "source_packet_found": packet_read.found,
        "source_packet_parsed": packet_read.parsed,
        "source_packet_record_count": packet_read.record_count,
        "source_packet_error": packet_read.error,
        "source_as_of": source_as_of,
        "validated_at": validated_at,
        "max_age_hours": str(checked_config.max_age_hours),
        "symbol": _text(source_record.get("symbol")),
        "usable_spy_bars": _strict_int(source_record.get("usable_spy_bars")),
        "sma50": _json_scalar(source_record.get("sma50", "")),
        "sma200": _json_scalar(source_record.get("sma200", "")),
        "posture": _text(source_record.get("posture")),
        "cycle_decision": cycle_decision,
        "current_spy_position_qty": _current_spy_position_qty(source_record),
        "open_order_count": _strict_int(source_record.get("open_order_count")),
        "unexpected_non_spy_position_present": _bool_or_none(
            source_record.get("unexpected_non_spy_position_present")
        ),
        "validation_state": validation_state,
        "validation_blockers": blockers,
        "paper_action_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": _PROFIT_CLAIM,
        "recommended_operator_action": _recommended_operator_action(
            blockers,
            cycle_decision,
        ),
    }


def render_etf_sma_cycle_packet_validation_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_cycle_packet_validation_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing validation summary."""

    blockers = _string_list(payload.get("validation_blockers"))
    blocker_text = ", ".join(blockers) if blockers else "none"
    return "\n".join(
        (
            "ETF/SMA cycle packet validation",
            f"run_id: {payload.get('run_id', '')}",
            f"source_packet_path: {payload.get('source_packet_path', '')}",
            f"source_as_of: {payload.get('source_as_of', '')}",
            f"validated_at: {payload.get('validated_at', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"usable_spy_bars: {payload.get('usable_spy_bars', '')}",
            f"posture: {payload.get('posture', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"validation_state: {payload.get('validation_state', '')}",
            f"validation_blockers: {blocker_text}",
            "paper_action_authorized: "
            f"{_bool_text(payload.get('paper_action_authorized'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            "recommended_operator_action: "
            f"{payload.get('recommended_operator_action', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"profit_claim: {payload.get('profit_claim', '')}",
        )
    )


def write_etf_sma_cycle_packet_validation_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaCyclePacketValidationWriteResult:
    """Write exactly one JSONL validation record, replacing prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_cycle_packet_validation_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaCyclePacketValidationWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        paper_action_authorized=False,
        submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _validation_blockers(
    *,
    packet_read: _PacketRead,
    source_record: Mapping[str, object],
    source_as_of_at: datetime | None,
    validated_at_at: datetime | None,
    max_age_hours: Decimal,
) -> list[str]:
    source_blockers = _source_packet_blockers(packet_read)
    if source_blockers:
        return source_blockers

    blockers: list[str] = []
    if _text(source_record.get("symbol")) != _DEFAULT_SYMBOL:
        blockers.append("symbol_not_spy")

    usable_bars = _strict_int(source_record.get("usable_spy_bars"))
    if usable_bars is None or usable_bars < 200:
        blockers.append("usable_spy_bars_missing_or_below_200")

    if not _decimal_like(source_record.get("sma50")):
        blockers.append("sma50_missing_or_nonnumeric")
    if not _decimal_like(source_record.get("sma200")):
        blockers.append("sma200_missing_or_nonnumeric")

    if _text(source_record.get("posture")) not in _POSTURES:
        blockers.append("posture_missing_or_invalid")
    if not _text(source_record.get("cycle_decision")):
        blockers.append("cycle_decision_missing")

    for field_name in (
        "submitted",
        "mutated",
        "broker_action_performed",
        "live_authorized",
    ):
        if source_record.get(field_name) is not False:
            blockers.append(f"{field_name}_not_false")

    if _text(source_record.get("profit_claim")) != _PROFIT_CLAIM:
        blockers.append("profit_claim_not_none")

    unexpected_non_spy = source_record.get("unexpected_non_spy_position_present")
    if unexpected_non_spy is True:
        blockers.append("unexpected_non_spy_position_present")
    elif unexpected_non_spy is not False:
        blockers.append("unexpected_non_spy_position_missing")

    open_order_count = _strict_int(source_record.get("open_order_count"))
    if open_order_count is None or open_order_count > 0:
        blockers.append("open_order_count_missing_or_positive")

    packet_blockers = _source_record_blockers(source_record.get("blockers"))
    if packet_blockers is None:
        blockers.append("source_blockers_missing_or_invalid")
    elif packet_blockers:
        blockers.append("source_blockers_present")

    if source_as_of_at is None:
        blockers.append("source_as_of_missing_or_unparseable")
    elif validated_at_at is None:
        blockers.append("validated_at_missing_or_unparseable")
    elif source_as_of_at > validated_at_at:
        blockers.append("source_as_of_after_validated_at")
    else:
        age_seconds = Decimal(str((validated_at_at - source_as_of_at).total_seconds()))
        max_age_seconds = max_age_hours * Decimal("3600")
        if age_seconds > max_age_seconds:
            blockers.append("source_as_of_stale")

    return blockers


def _source_packet_blockers(packet_read: _PacketRead) -> list[str]:
    if not packet_read.found:
        return ["source_packet_missing"]
    if not packet_read.parsed:
        return ["source_packet_invalid_jsonl"]
    if packet_read.record_count == 0:
        return ["source_packet_zero_records"]
    if packet_read.record_count > 1:
        return ["source_packet_multiple_records"]
    if packet_read.record is None:
        return ["source_packet_missing_record"]
    return []


def _validation_state(blockers: Sequence[str], cycle_decision: str) -> str:
    if blockers:
        return _BLOCKED_STATE
    if cycle_decision == "hold/noop":
        return _ACCEPTED_HOLD_NOOP_STATE
    return _ACCEPTED_OBSERVE_STATE


def _recommended_operator_action(blockers: Sequence[str], cycle_decision: str) -> str:
    if blockers:
        return _RESOLVE_BLOCKERS_ACTION
    if cycle_decision == "hold/noop":
        return _OBSERVE_HOLD_NOOP_ACTION
    return _OPERATOR_REVIEW_ACTION


def _read_packet(path: Path) -> _PacketRead:
    if not path.exists():
        return _PacketRead(
            path=path,
            found=False,
            parsed=False,
            record_count=0,
            record=None,
            error="path_not_found",
            sha256="",
        )
    if not path.is_file():
        return _PacketRead(
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
        return _PacketRead(
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
            return _PacketRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                record=None,
                error=f"invalid_jsonl_line_{line_number}",
                sha256=sha256,
            )
        if not isinstance(payload, Mapping):
            return _PacketRead(
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
        return _PacketRead(
            path=path,
            found=True,
            parsed=True,
            record_count=len(records),
            record=None,
            error="record_count_not_one",
            sha256=sha256,
        )
    return _PacketRead(
        path=path,
        found=True,
        parsed=True,
        record_count=1,
        record=records[0],
        error="",
        sha256=sha256,
    )


def _config(
    config: EtfSmaCyclePacketValidationConfig,
) -> EtfSmaCyclePacketValidationConfig:
    if not isinstance(config, EtfSmaCyclePacketValidationConfig):
        raise ValidationError("config must be an EtfSmaCyclePacketValidationConfig.")
    return config


def _required_string(value: object, field_name: str) -> str:
    text = _text(value)
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        path = Path(str(value))
    if not str(path):
        raise ValidationError(f"{field_name} is required.")
    return path


def _output_path(value: Path | str) -> Path:
    path = value if isinstance(value, Path) else Path(str(value))
    if not str(path):
        raise ValidationError("output_path is required.")
    return path


def _optional_timestamp_text(value: datetime | str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(f"{field_name} must be timezone-aware.")
        return value.isoformat()
    text = _text(value)
    if not text:
        return None
    if _parse_timestamp(text) is None:
        raise ValidationError(f"{field_name} must be a timezone-aware ISO-8601 value.")
    return text


def _parse_timestamp(value: object) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _positive_decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be positive.")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{field_name} must be numeric.") from None
    if not parsed.is_finite() or parsed <= 0:
        raise ValidationError(f"{field_name} must be positive.")
    return parsed


def _decimal_like(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    text = _text(value)
    if not text:
        return False
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return False
    return parsed.is_finite()


def _strict_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        text = str(value).strip()
        parsed = int(text)
    except (TypeError, ValueError):
        return None
    if text != str(parsed):
        return None
    return parsed


def _source_record_blockers(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    return tuple(_text(item) for item in value if _text(item))


def _current_spy_position_qty(source_record: Mapping[str, object]) -> object:
    if "current_spy_position_qty" in source_record:
        return _json_scalar(source_record.get("current_spy_position_qty"))
    return _json_scalar(source_record.get("spy_position_qty", ""))


def _json_scalar(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _bool_or_none(value: object) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_json_safe(item) for item in value]
    return value
