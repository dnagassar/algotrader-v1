"""Local offline ETF/SMA execution-preview JSONL artifact writer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.orchestration.etf_sma_execution_preview_bridge import (
    ETF_SMA_EXECUTION_PREVIEW_LABELS,
    EtfSmaExecutionPreview,
)
from algotrader.signals.etf_sma_evaluator import (
    ETF_SMA_SIGNAL_LABELS,
    EtfSmaSignalResult,
)

__all__ = [
    "ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS",
    "EtfSmaPreviewJsonlArtifactConfig",
    "EtfSmaPreviewJsonlRecord",
    "EtfSmaPreviewJsonlWriteResult",
    "build_etf_sma_preview_jsonl_record",
    "render_etf_sma_preview_jsonl_record",
    "write_etf_sma_preview_jsonl_artifact",
]

ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS = (
    "paper_lab_only",
    "offline_execution_preview_only",
    "local_preview_jsonl_artifact_only",
    "not_live_authorized",
    "profit_claim=none",
)

_ARTIFACT_VERSION = "etf_sma_preview_jsonl_artifact_v1"
_RECORD_TYPE = "etf_sma_preview_jsonl_record"
_PROFIT_CLAIM = "none"
_SOURCE_NEXT_ACTION = "m347_local_etf_sma_preview_jsonl_artifact_no_broker_action"
_NEXT_ACTION = "m348_fresh_read_only_paper_snapshot_before_broker_facing_preview"
_ACCEPTED_STATUS = "accepted_for_offline_preview"
_SKIPPED_STATUS = "skipped_from_offline_preview"
_ALLOWLISTED = "allowlisted"
_NOT_ALLOWLISTED = "not_allowlisted"
_FORBIDDEN_LIVE_AUTHORIZATION_VALUES = {
    "authorized_for_live_trading",
    "live_authorized",
    "live_authorized=true",
    "live_trading_authorized",
}


@dataclass(frozen=True, slots=True)
class EtfSmaPreviewJsonlArtifactConfig:
    """Explicit local file-write configuration for the M347 artifact."""

    output_path: Path | str
    append: bool = False
    create_parent_dirs: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "output_path",
            _output_path(self.output_path),
        )
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(
            self,
            "create_parent_dirs",
            _bool(self.create_parent_dirs, "create_parent_dirs"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaPreviewJsonlRecord:
    """Immutable local JSONL record derived from one M346 preview result."""

    artifact_version: str
    record_type: str
    source_preview: EtfSmaExecutionPreview
    symbol: str
    source_signal_symbol: str
    asset_class: str
    strategy_type: str
    timeframe: str
    as_of: datetime
    signal_posture: str
    preview_status: str
    accepted_for_offline_preview: bool
    skipped: bool
    skip_reason: str
    decision_reason: str
    short_window: int
    long_window: int
    max_notional: Decimal
    allowlist: tuple[str, ...]
    allowlist_decision: str
    intended_side: str | None
    intended_order_style: str | None
    preview_notional: Decimal | None
    labels: tuple[str, ...]
    source_preview_labels: tuple[str, ...]
    source_signal_labels: tuple[str, ...]
    profit_claim: str
    broker_action_performed: bool
    broker_preview_performed: bool
    submit_allowed: bool
    capital_mutated: bool
    broker_mutated: bool
    source_bridge_mutated: bool
    next_action: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_version",
            _fixed_string(
                self.artifact_version,
                _ARTIFACT_VERSION,
                "artifact_version",
            ),
        )
        object.__setattr__(
            self,
            "record_type",
            _fixed_string(self.record_type, _RECORD_TYPE, "record_type"),
        )
        object.__setattr__(
            self,
            "source_preview",
            _source_preview(self.source_preview),
        )
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "source_signal_symbol",
            symbol_value(self.source_signal_symbol),
        )
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, "equity", "asset_class"),
        )
        object.__setattr__(
            self,
            "strategy_type",
            _non_empty_string(self.strategy_type, "strategy_type"),
        )
        object.__setattr__(
            self,
            "timeframe",
            _fixed_string(self.timeframe, "daily", "timeframe"),
        )
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "signal_posture",
            _non_empty_string(self.signal_posture, "signal_posture"),
        )
        object.__setattr__(
            self,
            "preview_status",
            _preview_status(self.preview_status),
        )
        object.__setattr__(
            self,
            "accepted_for_offline_preview",
            _bool(
                self.accepted_for_offline_preview,
                "accepted_for_offline_preview",
            ),
        )
        object.__setattr__(self, "skipped", _bool(self.skipped, "skipped"))
        object.__setattr__(
            self,
            "skip_reason",
            _string(self.skip_reason, "skip_reason"),
        )
        object.__setattr__(
            self,
            "decision_reason",
            _non_empty_string(self.decision_reason, "decision_reason"),
        )
        object.__setattr__(
            self,
            "short_window",
            _positive_int(self.short_window, "short_window"),
        )
        object.__setattr__(
            self,
            "long_window",
            _positive_int(self.long_window, "long_window"),
        )
        object.__setattr__(
            self,
            "max_notional",
            _positive_decimal(self.max_notional, "max_notional"),
        )
        object.__setattr__(self, "allowlist", _symbol_tuple(self.allowlist))
        object.__setattr__(
            self,
            "allowlist_decision",
            _allowlist_decision(self.allowlist_decision),
        )
        object.__setattr__(
            self,
            "intended_side",
            _optional_string(self.intended_side, "intended_side"),
        )
        object.__setattr__(
            self,
            "intended_order_style",
            _optional_string(self.intended_order_style, "intended_order_style"),
        )
        object.__setattr__(
            self,
            "preview_notional",
            _optional_positive_decimal(
                self.preview_notional,
                "preview_notional",
            ),
        )
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS,
                "labels",
            ),
        )
        object.__setattr__(
            self,
            "source_preview_labels",
            _fixed_string_tuple(
                self.source_preview_labels,
                ETF_SMA_EXECUTION_PREVIEW_LABELS,
                "source_preview_labels",
            ),
        )
        object.__setattr__(
            self,
            "source_signal_labels",
            _fixed_string_tuple(
                self.source_signal_labels,
                ETF_SMA_SIGNAL_LABELS,
                "source_signal_labels",
            ),
        )
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"),
        )
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(
                self.broker_action_performed,
                "broker_action_performed",
            ),
        )
        object.__setattr__(
            self,
            "broker_preview_performed",
            _false_bool(
                self.broker_preview_performed,
                "broker_preview_performed",
            ),
        )
        object.__setattr__(
            self,
            "submit_allowed",
            _false_bool(self.submit_allowed, "submit_allowed"),
        )
        object.__setattr__(
            self,
            "capital_mutated",
            _false_bool(self.capital_mutated, "capital_mutated"),
        )
        object.__setattr__(
            self,
            "broker_mutated",
            _false_bool(self.broker_mutated, "broker_mutated"),
        )
        object.__setattr__(
            self,
            "source_bridge_mutated",
            _false_bool(self.source_bridge_mutated, "source_bridge_mutated"),
        )
        object.__setattr__(
            self,
            "next_action",
            _fixed_string(self.next_action, _NEXT_ACTION, "next_action"),
        )
        _validate_record_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only JSONL payload metadata."""

        return {
            "artifact_version": self.artifact_version,
            "record_type": self.record_type,
            "symbol": self.symbol,
            "source_signal_symbol": self.source_signal_symbol,
            "asset_class": self.asset_class,
            "strategy_type": self.strategy_type,
            "timeframe": self.timeframe,
            "as_of": self.as_of.isoformat(),
            "signal_posture": self.signal_posture,
            "preview_status": self.preview_status,
            "accepted_for_offline_preview": self.accepted_for_offline_preview,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "decision_reason": self.decision_reason,
            "short_window": self.short_window,
            "long_window": self.long_window,
            "max_notional": str(self.max_notional),
            "allowlist": list(self.allowlist),
            "allowlist_decision": self.allowlist_decision,
            "intended_side": self.intended_side,
            "intended_order_style": self.intended_order_style,
            "preview_notional": _decimal_text(self.preview_notional),
            "labels": list(self.labels),
            "source_preview_labels": list(self.source_preview_labels),
            "source_signal_labels": list(self.source_signal_labels),
            "profit_claim": self.profit_claim,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "submit_allowed": self.submit_allowed,
            "capital_mutated": self.capital_mutated,
            "broker_mutated": self.broker_mutated,
            "source_bridge_mutated": self.source_bridge_mutated,
            "next_action": self.next_action,
            "source_preview": self.source_preview.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaPreviewJsonlWriteResult:
    """Result metadata for one local JSONL artifact write."""

    output_path: Path
    record_count: int
    bytes_written: int
    append: bool
    created_parent_dirs: bool
    newline_terminated: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    submit_allowed: bool
    capital_mutated: bool
    broker_mutated: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        object.__setattr__(
            self,
            "record_count",
            _fixed_int(self.record_count, 1, "record_count"),
        )
        object.__setattr__(
            self,
            "bytes_written",
            _positive_int(self.bytes_written, "bytes_written"),
        )
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(
            self,
            "created_parent_dirs",
            _bool(self.created_parent_dirs, "created_parent_dirs"),
        )
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(
                self.broker_action_performed,
                "broker_action_performed",
            ),
        )
        object.__setattr__(
            self,
            "broker_preview_performed",
            _false_bool(
                self.broker_preview_performed,
                "broker_preview_performed",
            ),
        )
        object.__setattr__(
            self,
            "submit_allowed",
            _false_bool(self.submit_allowed, "submit_allowed"),
        )
        object.__setattr__(
            self,
            "capital_mutated",
            _false_bool(self.capital_mutated, "capital_mutated"),
        )
        object.__setattr__(
            self,
            "broker_mutated",
            _false_bool(self.broker_mutated, "broker_mutated"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return primitive local write metadata."""

        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "append": self.append,
            "created_parent_dirs": self.created_parent_dirs,
            "newline_terminated": self.newline_terminated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "submit_allowed": self.submit_allowed,
            "capital_mutated": self.capital_mutated,
            "broker_mutated": self.broker_mutated,
        }


def build_etf_sma_preview_jsonl_record(
    source_preview: EtfSmaExecutionPreview,
) -> EtfSmaPreviewJsonlRecord:
    """Build one deterministic local JSONL record from an M346 preview."""

    checked_preview = _source_preview(source_preview)
    signal = checked_preview.source_signal_result
    preview_status = (
        _ACCEPTED_STATUS
        if checked_preview.accepted_for_offline_preview
        else _SKIPPED_STATUS
    )
    allowlist_decision = (
        _ALLOWLISTED if checked_preview.symbol in checked_preview.allowlist else _NOT_ALLOWLISTED
    )

    return EtfSmaPreviewJsonlRecord(
        artifact_version=_ARTIFACT_VERSION,
        record_type=_RECORD_TYPE,
        source_preview=checked_preview,
        symbol=checked_preview.symbol,
        source_signal_symbol=signal.symbol,
        asset_class=checked_preview.asset_class,
        strategy_type=signal.strategy_type,
        timeframe=signal.timeframe,
        as_of=checked_preview.as_of,
        signal_posture=checked_preview.signal_posture,
        preview_status=preview_status,
        accepted_for_offline_preview=checked_preview.accepted_for_offline_preview,
        skipped=checked_preview.skipped,
        skip_reason=checked_preview.skip_reason,
        decision_reason=checked_preview.decision_reason,
        short_window=signal.short_window,
        long_window=signal.long_window,
        max_notional=checked_preview.max_notional,
        allowlist=checked_preview.allowlist,
        allowlist_decision=allowlist_decision,
        intended_side=checked_preview.intended_side,
        intended_order_style=checked_preview.intended_order_style,
        preview_notional=checked_preview.preview_notional,
        labels=ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS,
        source_preview_labels=checked_preview.labels,
        source_signal_labels=signal.labels,
        profit_claim=_PROFIT_CLAIM,
        broker_action_performed=False,
        broker_preview_performed=False,
        submit_allowed=False,
        capital_mutated=False,
        broker_mutated=False,
        source_bridge_mutated=checked_preview.mutated,
        next_action=_NEXT_ACTION,
    )


def render_etf_sma_preview_jsonl_record(
    record: EtfSmaPreviewJsonlRecord,
) -> str:
    """Render one newline-terminated deterministic JSON object."""

    checked_record = _record(record)
    return json.dumps(
        checked_record.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def write_etf_sma_preview_jsonl_artifact(
    source_preview: EtfSmaExecutionPreview,
    config: EtfSmaPreviewJsonlArtifactConfig,
) -> EtfSmaPreviewJsonlWriteResult:
    """Write one local JSONL artifact record to an explicit caller path."""

    checked_config = _config(config)
    record = build_etf_sma_preview_jsonl_record(source_preview)
    line = render_etf_sma_preview_jsonl_record(record)
    created_parent_dirs = _prepare_output_parent(checked_config.output_path, checked_config)
    _write_line(checked_config.output_path, line, append=checked_config.append)

    return EtfSmaPreviewJsonlWriteResult(
        output_path=checked_config.output_path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        append=checked_config.append,
        created_parent_dirs=created_parent_dirs,
        newline_terminated=line.endswith("\n"),
        broker_action_performed=False,
        broker_preview_performed=False,
        submit_allowed=False,
        capital_mutated=False,
        broker_mutated=False,
    )


def _config(value: object) -> EtfSmaPreviewJsonlArtifactConfig:
    if type(value) is not EtfSmaPreviewJsonlArtifactConfig:
        raise ValidationError(
            "config must be an EtfSmaPreviewJsonlArtifactConfig."
        )

    return value


def _record(value: object) -> EtfSmaPreviewJsonlRecord:
    if type(value) is not EtfSmaPreviewJsonlRecord:
        raise ValidationError("record must be an EtfSmaPreviewJsonlRecord.")

    return value


def _source_preview(value: object) -> EtfSmaExecutionPreview:
    if type(value) is not EtfSmaExecutionPreview:
        raise ValidationError(
            "source_preview must be an EtfSmaExecutionPreview."
        )

    _validate_source_preview_safety(value)
    return value


def _validate_source_preview_safety(preview: EtfSmaExecutionPreview) -> None:
    signal = preview.source_signal_result
    if type(signal) is not EtfSmaSignalResult:
        raise ValidationError("source preview signal result is required.")

    _reject_live_authorization(preview.labels, "source_preview_labels")
    _reject_live_authorization(signal.labels, "source_signal_labels")
    if preview.labels != ETF_SMA_EXECUTION_PREVIEW_LABELS:
        raise ValidationError("source_preview_labels must match M346 labels.")
    if signal.labels != ETF_SMA_SIGNAL_LABELS:
        raise ValidationError("source_signal_labels must match M345 labels.")
    if preview.profit_claim != _PROFIT_CLAIM:
        raise ValidationError("source preview profit_claim must be none.")
    if signal.profit_claim != _PROFIT_CLAIM:
        raise ValidationError("source signal profit_claim must be none.")

    if preview.broker_action_performed is not False:
        raise ValidationError("source preview broker_action_performed must be false.")
    if preview.broker_preview_performed is not False:
        raise ValidationError("source preview broker_preview_performed must be false.")
    if preview.submit_allowed is not False:
        raise ValidationError("source preview submit_allowed must be false.")
    if preview.mutated is not False:
        raise ValidationError("source preview mutated must be false.")
    if signal.broker_action_performed is not False:
        raise ValidationError("source signal broker_action_performed must be false.")
    if signal.submit_allowed is not False:
        raise ValidationError("source signal submit_allowed must be false.")
    if preview.next_action != _SOURCE_NEXT_ACTION:
        raise ValidationError("source preview next_action must point to M347.")

    if preview.symbol != signal.symbol:
        raise ValidationError("source preview symbol must match signal symbol.")
    if preview.asset_class != signal.asset_class:
        raise ValidationError("source preview asset_class must match signal asset_class.")
    if preview.as_of != signal.as_of:
        raise ValidationError("source preview as_of must match signal as_of.")
    if preview.signal_posture != signal.posture:
        raise ValidationError("source preview posture must match signal posture.")
    if preview.accepted_for_offline_preview == preview.skipped:
        raise ValidationError("source preview skipped must invert accepted status.")
    if preview.accepted_for_offline_preview and preview.skip_reason != "":
        raise ValidationError("accepted source preview skip_reason must be empty.")
    if preview.skipped and preview.skip_reason == "":
        raise ValidationError("skipped source preview skip_reason is required.")


def _validate_record_consistency(record: EtfSmaPreviewJsonlRecord) -> None:
    preview = record.source_preview
    signal = preview.source_signal_result
    expected_status = (
        _ACCEPTED_STATUS if preview.accepted_for_offline_preview else _SKIPPED_STATUS
    )
    expected_allowlist_decision = (
        _ALLOWLISTED if preview.symbol in preview.allowlist else _NOT_ALLOWLISTED
    )

    if record.symbol != preview.symbol:
        raise ValidationError("symbol must match source preview symbol.")
    if record.source_signal_symbol != signal.symbol:
        raise ValidationError("source_signal_symbol must match source signal symbol.")
    if record.asset_class != preview.asset_class:
        raise ValidationError("asset_class must match source preview asset_class.")
    if record.strategy_type != signal.strategy_type:
        raise ValidationError("strategy_type must match source signal strategy_type.")
    if record.timeframe != signal.timeframe:
        raise ValidationError("timeframe must match source signal timeframe.")
    if record.as_of != preview.as_of:
        raise ValidationError("as_of must match source preview as_of.")
    if record.signal_posture != preview.signal_posture:
        raise ValidationError("signal_posture must match source preview posture.")
    if record.preview_status != expected_status:
        raise ValidationError("preview_status must match source preview status.")
    if record.accepted_for_offline_preview != preview.accepted_for_offline_preview:
        raise ValidationError("accepted_for_offline_preview must match source preview.")
    if record.skipped != preview.skipped:
        raise ValidationError("skipped must match source preview skipped status.")
    if record.skip_reason != preview.skip_reason:
        raise ValidationError("skip_reason must match source preview skip_reason.")
    if record.decision_reason != preview.decision_reason:
        raise ValidationError("decision_reason must match source preview decision_reason.")
    if record.short_window != signal.short_window:
        raise ValidationError("short_window must match source signal short_window.")
    if record.long_window != signal.long_window:
        raise ValidationError("long_window must match source signal long_window.")
    if record.max_notional != preview.max_notional:
        raise ValidationError("max_notional must match source preview max_notional.")
    if record.allowlist != preview.allowlist:
        raise ValidationError("allowlist must match source preview allowlist.")
    if record.allowlist_decision != expected_allowlist_decision:
        raise ValidationError("allowlist_decision must match source preview symbol.")
    if record.intended_side != preview.intended_side:
        raise ValidationError("intended_side must match source preview intended_side.")
    if record.intended_order_style != preview.intended_order_style:
        raise ValidationError(
            "intended_order_style must match source preview intended_order_style."
        )
    if record.preview_notional != preview.preview_notional:
        raise ValidationError("preview_notional must match source preview value.")


def _output_path(value: object) -> Path:
    if type(value) is str:
        if value.strip() == "":
            raise ValidationError("output_path is required.")
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("output_path must be a pathlib.Path or string.")

    if str(path).strip() in ("", ".") or path.name == "":
        raise ValidationError("output_path must name a local JSONL file.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")

    return path


def _prepare_output_parent(
    output_path: Path,
    config: EtfSmaPreviewJsonlArtifactConfig,
) -> bool:
    parent = output_path.parent
    created_parent_dirs = False
    if parent.exists():
        return created_parent_dirs
    if not config.create_parent_dirs:
        raise ValidationError(
            "output_path parent directory does not exist; "
            "set create_parent_dirs=True to create it."
        )

    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValidationError(
            f"etf_sma_preview_jsonl_parent_create_failed: {exc.__class__.__name__}"
        ) from None

    return True


def _write_line(output_path: Path, line: str, *, append: bool) -> None:
    mode = "a" if append else "x"
    try:
        with output_path.open(mode, encoding="utf-8", newline="\n") as handle:
            handle.write(line)
    except FileExistsError:
        raise ValidationError(
            "output_path already exists; set append=True to append explicitly."
        ) from None
    except OSError as exc:
        raise ValidationError(
            f"etf_sma_preview_jsonl_write_failed: {exc.__class__.__name__}"
        ) from None


def _utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")

    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _positive_decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be a positive Decimal.")

    return value


def _optional_positive_decimal(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None

    return _positive_decimal(value, field_name)


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")

    return value


def _fixed_int(value: object, expected: int, field_name: str) -> int:
    if type(value) is not int or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")

    return value


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a boolean.")

    return value


def _true_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool or value is not True:
        raise ValidationError(f"{field_name} must be true.")

    return value


def _false_bool(value: object, field_name: str) -> bool:
    if type(value) is not bool or value is not False:
        raise ValidationError(f"{field_name} must be false.")

    return value


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")

    return value


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")

    return value


def _non_empty_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if text == "":
        raise ValidationError(f"{field_name} is required.")

    return text


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None

    return _non_empty_string(value, field_name)


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    for item in items:
        _non_empty_string(item, field_name)
    _reject_live_authorization(items, field_name)
    if items != expected:
        raise ValidationError(f"{field_name} must match the required values.")

    return items


def _symbol_tuple(values: object) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError("allowlist must be a tuple or list of symbols.")

    symbols = tuple(symbol_value(symbol) for symbol in values)
    if not symbols:
        raise ValidationError("allowlist must not be empty.")

    return symbols


def _preview_status(value: object) -> str:
    if type(value) is not str or value not in (_ACCEPTED_STATUS, _SKIPPED_STATUS):
        raise ValidationError("preview_status must be accepted or skipped.")

    return value


def _allowlist_decision(value: object) -> str:
    if type(value) is not str or value not in (_ALLOWLISTED, _NOT_ALLOWLISTED):
        raise ValidationError("allowlist_decision must be allowlisted or not_allowlisted.")

    return value


def _reject_live_authorization(values: object, field_name: str) -> None:
    if type(values) is str:
        checked_values = (values,)
    elif type(values) in (list, tuple):
        checked_values = tuple(values)
    else:
        raise ValidationError(f"{field_name} must be a string or string tuple.")

    for value in checked_values:
        text = _non_empty_string(value, field_name).strip().lower()
        if (
            text in _FORBIDDEN_LIVE_AUTHORIZATION_VALUES
            or text.startswith("live_authorized=")
        ):
            raise ValidationError(f"{field_name} must not include live authorization.")


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return str(value)
