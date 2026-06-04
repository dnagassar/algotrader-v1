"""SPY ETF/SMA daily paper-lab cycle preview artifact.

This module is local and deterministic: it evaluates caller-supplied bars,
combines explicit read-only paper observations, and renders one preview record.
It does not import broker SDKs or provide any broker mutation path.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.core.types import Bar
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)

__all__ = [
    "ETF_SMA_CYCLE_PREVIEW_DECISIONS",
    "ETF_SMA_CYCLE_PREVIEW_LABELS",
    "EtfSmaCycleBrokerObservation",
    "EtfSmaCyclePreview",
    "EtfSmaCyclePreviewConfig",
    "EtfSmaCyclePreviewWriteConfig",
    "EtfSmaCyclePreviewWriteResult",
    "build_etf_sma_cycle_preview",
    "load_etf_sma_cycle_bars_csv",
    "load_etf_sma_cycle_bars_jsonl",
    "render_etf_sma_cycle_preview_json",
    "render_etf_sma_cycle_preview_text",
    "write_etf_sma_cycle_preview",
]


ETF_SMA_CYCLE_PREVIEW_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)
ETF_SMA_CYCLE_PREVIEW_DECISIONS = (
    "buy_preview",
    "hold",
    "sell_preview",
    "blocked",
    "insufficient_history",
)

_PREVIEW_VERSION = "etf_sma_cycle_preview_v1"
_RECORD_TYPE = "etf_sma_cycle_preview"
_COMMAND = "etf-sma-cycle-preview"
_SYMBOL = "SPY"
_ASSET_CLASS = "equity"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_PROFIT_CLAIM = "none"
_DEFAULT_MAX_NOTIONAL = Decimal("25.00")
_EMPTY_AS_OF = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class EtfSmaCycleBrokerObservation:
    """Read-only paper account, position, and open-order state."""

    paper_profile_gate_passed: bool = False
    account_observation_available: bool = False
    positions_observation_available: bool = False
    orders_observation_available: bool = False
    cash: Decimal | str | None = None
    currency: str | None = None
    position_count: int | None = None
    position_symbols: tuple[str, ...] = ()
    spy_position_quantity: Decimal | str | None = None
    open_order_count: int | None = None
    open_order_symbols: tuple[str, ...] = ()
    unavailable_observations: tuple[str, ...] = ()
    unavailable_reasons: Mapping[str, object] | None = None
    submitted: bool = False
    mutated: bool = False
    broker_action_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "paper_profile_gate_passed",
            _bool(self.paper_profile_gate_passed, "paper_profile_gate_passed"),
        )
        for field_name in (
            "account_observation_available",
            "positions_observation_available",
            "orders_observation_available",
            "submitted",
            "mutated",
            "broker_action_performed",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))
        object.__setattr__(self, "cash", _optional_decimal(self.cash, "cash"))
        object.__setattr__(self, "currency", _optional_string(self.currency, "currency"))
        object.__setattr__(
            self,
            "position_count",
            _optional_non_negative_int(self.position_count, "position_count"),
        )
        object.__setattr__(
            self,
            "position_symbols",
            _symbol_tuple(self.position_symbols, "position_symbols", allow_empty=True),
        )
        object.__setattr__(
            self,
            "spy_position_quantity",
            _optional_decimal(
                self.spy_position_quantity,
                "spy_position_quantity",
            ),
        )
        object.__setattr__(
            self,
            "open_order_count",
            _optional_non_negative_int(self.open_order_count, "open_order_count"),
        )
        object.__setattr__(
            self,
            "open_order_symbols",
            _symbol_tuple(self.open_order_symbols, "open_order_symbols", allow_empty=True),
        )
        object.__setattr__(
            self,
            "unavailable_observations",
            _string_tuple(
                self.unavailable_observations,
                "unavailable_observations",
                allow_empty=True,
            ),
        )
        reasons = self.unavailable_reasons or {}
        if not isinstance(reasons, Mapping):
            raise ValidationError("unavailable_reasons must be a mapping.")
        object.__setattr__(self, "unavailable_reasons", dict(reasons))

    @property
    def broker_observation_available(self) -> bool:
        return (
            self.paper_profile_gate_passed
            and self.account_observation_available
            and self.positions_observation_available
            and self.orders_observation_available
        )

    @property
    def has_spy_position(self) -> bool:
        return (
            self.spy_position_quantity is not None
            and self.spy_position_quantity > Decimal("0")
        )

    def blockers(self, symbol: str = _SYMBOL) -> tuple[str, ...]:
        checked_symbol = _spy_symbol(symbol)
        blockers: list[str] = []
        if not self.paper_profile_gate_passed:
            blockers.append("paper_profile_required")
        if not self.account_observation_available:
            blockers.append("account_observation_unavailable")
        if not self.positions_observation_available:
            blockers.append("positions_observation_unavailable")
        if not self.orders_observation_available:
            blockers.append("orders_observation_unavailable")
        if self.unavailable_observations:
            blockers.append("broker_observations_unavailable")
        if any(position_symbol != checked_symbol for position_symbol in self.position_symbols):
            blockers.append("unexpected_non_spy_position")
        if (
            self.spy_position_quantity is not None
            and self.spy_position_quantity < Decimal("0")
        ):
            blockers.append("spy_position_quantity_negative")
        if self.open_order_count is not None and self.open_order_count > 0:
            blockers.append("open_order_present")
        if self.submitted:
            blockers.append("observation_submitted_not_false")
        if self.mutated:
            blockers.append("observation_mutated_not_false")
        if self.broker_action_performed:
            blockers.append("observation_broker_action_not_false")
        return _dedupe(tuple(blockers))

    def to_dict(self) -> dict[str, object]:
        return {
            "paper_profile_gate_passed": self.paper_profile_gate_passed,
            "account_observation_available": self.account_observation_available,
            "positions_observation_available": self.positions_observation_available,
            "orders_observation_available": self.orders_observation_available,
            "broker_observation_available": self.broker_observation_available,
            "cash": _decimal_text(self.cash),
            "currency": self.currency,
            "position_count": self.position_count,
            "position_symbols": list(self.position_symbols),
            "spy_position_quantity": _decimal_text(self.spy_position_quantity),
            "open_order_count": self.open_order_count,
            "open_order_symbols": list(self.open_order_symbols),
            "unavailable_observations": list(self.unavailable_observations),
            "unavailable_reasons": _json_safe(self.unavailable_reasons),
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaCyclePreviewConfig:
    """Static preview-only constraints for the SPY cycle command."""

    run_id: str
    symbol: str = _SYMBOL
    asset_class: str = _ASSET_CLASS
    max_notional: Decimal | str = _DEFAULT_MAX_NOTIONAL
    order_type: str = _ORDER_TYPE
    time_in_force: str = _TIME_IN_FORCE
    bars_source: str = ""
    bars_input_available: bool = True
    as_of: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "max_notional",
            _positive_decimal(self.max_notional, "max_notional"),
        )
        object.__setattr__(
            self,
            "order_type",
            _fixed_string(self.order_type, _ORDER_TYPE, "order_type"),
        )
        object.__setattr__(
            self,
            "time_in_force",
            _fixed_string(self.time_in_force, _TIME_IN_FORCE, "time_in_force"),
        )
        object.__setattr__(self, "bars_source", _string(self.bars_source, "bars_source"))
        object.__setattr__(
            self,
            "bars_input_available",
            _bool(self.bars_input_available, "bars_input_available"),
        )
        if self.as_of is not None:
            object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))


@dataclass(frozen=True, slots=True)
class EtfSmaCyclePreview:
    """Immutable primitive-renderable cycle preview record."""

    preview_version: str
    record_type: str
    command: str
    run_id: str
    symbol: str
    asset_class: str
    labels: tuple[str, ...]
    paper_lab_only: bool
    not_live_authorized: bool
    profit_claim: str
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_preview_performed: bool
    sma_status: str
    sma_posture: str
    sma: EtfSmaSignalResult
    bars_source: str
    bars_input_available: bool
    broker_observation: EtfSmaCycleBrokerObservation
    account_observation_available: bool
    positions_observation_available: bool
    orders_observation_available: bool
    cash: Decimal | None
    spy_position_quantity: Decimal | None
    open_order_count: int | None
    blockers: tuple[str, ...]
    decision: str
    decision_reason: str
    preview_order: dict[str, object] | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "preview_version",
            _fixed_string(self.preview_version, _PREVIEW_VERSION, "preview_version"),
        )
        object.__setattr__(
            self,
            "record_type",
            _fixed_string(self.record_type, _RECORD_TYPE, "record_type"),
        )
        object.__setattr__(self, "command", _fixed_string(self.command, _COMMAND, "command"))
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "asset_class",
            _fixed_string(self.asset_class, _ASSET_CLASS, "asset_class"),
        )
        object.__setattr__(
            self,
            "labels",
            _fixed_string_tuple(
                self.labels,
                ETF_SMA_CYCLE_PREVIEW_LABELS,
                "labels",
            ),
        )
        object.__setattr__(self, "paper_lab_only", _true_bool(self.paper_lab_only, "paper_lab_only"))
        object.__setattr__(
            self,
            "not_live_authorized",
            _true_bool(self.not_live_authorized, "not_live_authorized"),
        )
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, _PROFIT_CLAIM, "profit_claim"),
        )
        for field_name in (
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_preview_performed",
        ):
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "sma_status",
            _sma_status(self.sma_status),
        )
        object.__setattr__(
            self,
            "sma_posture",
            _required_string(self.sma_posture, "sma_posture"),
        )
        if type(self.sma) is not EtfSmaSignalResult:
            raise ValidationError("sma must be an EtfSmaSignalResult.")
        object.__setattr__(self, "bars_source", _string(self.bars_source, "bars_source"))
        object.__setattr__(
            self,
            "bars_input_available",
            _bool(self.bars_input_available, "bars_input_available"),
        )
        if type(self.broker_observation) is not EtfSmaCycleBrokerObservation:
            raise ValidationError(
                "broker_observation must be an EtfSmaCycleBrokerObservation."
            )
        for field_name in (
            "account_observation_available",
            "positions_observation_available",
            "orders_observation_available",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))
        object.__setattr__(self, "cash", _optional_decimal(self.cash, "cash"))
        object.__setattr__(
            self,
            "spy_position_quantity",
            _optional_decimal(
                self.spy_position_quantity,
                "spy_position_quantity",
            ),
        )
        object.__setattr__(
            self,
            "open_order_count",
            _optional_non_negative_int(self.open_order_count, "open_order_count"),
        )
        object.__setattr__(
            self,
            "blockers",
            _string_tuple(self.blockers, "blockers", allow_empty=True),
        )
        object.__setattr__(self, "decision", _decision(self.decision))
        object.__setattr__(
            self,
            "decision_reason",
            _required_string(self.decision_reason, "decision_reason"),
        )
        object.__setattr__(
            self,
            "preview_order",
            _optional_preview_order(self.preview_order, self.decision),
        )
        _validate_preview_consistency(self)

    def to_dict(self) -> dict[str, object]:
        payload = {
            "preview_version": self.preview_version,
            "record_type": self.record_type,
            "command": self.command,
            "run_id": self.run_id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "labels": list(self.labels),
            "paper_lab_only": self.paper_lab_only,
            "not_live_authorized": self.not_live_authorized,
            "profit_claim": self.profit_claim,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_preview_performed": self.broker_preview_performed,
            "sma_status": self.sma_status,
            "sma_posture": self.sma_posture,
            "sma": self.sma.to_dict(),
            "bars_source": self.bars_source,
            "bars_input_available": self.bars_input_available,
            "broker_observation": self.broker_observation.to_dict(),
            "account_observation_available": self.account_observation_available,
            "positions_observation_available": self.positions_observation_available,
            "orders_observation_available": self.orders_observation_available,
            "cash": _decimal_text(self.cash),
            "spy_position_quantity": _decimal_text(self.spy_position_quantity),
            "open_order_count": self.open_order_count,
            "blockers": list(self.blockers),
            "decision": self.decision,
            "decision_reason": self.decision_reason,
        }
        if self.preview_order is not None:
            payload["preview_order"] = _json_safe(self.preview_order)
        return payload


@dataclass(frozen=True, slots=True)
class EtfSmaCyclePreviewWriteConfig:
    """Explicit JSONL write configuration for a single preview record."""

    output_path: Path | str
    append: bool = True
    create_parent_dirs: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        object.__setattr__(self, "append", _bool(self.append, "append"))
        object.__setattr__(
            self,
            "create_parent_dirs",
            _bool(self.create_parent_dirs, "create_parent_dirs"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaCyclePreviewWriteResult:
    """Local JSONL write metadata."""

    output_path: Path
    record_count: int
    bytes_written: int
    append: bool
    created_parent_dirs: bool
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool

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
        for field_name in ("submitted", "mutated", "broker_action_performed"):
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
            "append": self.append,
            "created_parent_dirs": self.created_parent_dirs,
            "newline_terminated": self.newline_terminated,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
        }


def build_etf_sma_cycle_preview(
    bars: Iterable[Bar],
    broker_observation: EtfSmaCycleBrokerObservation,
    config: EtfSmaCyclePreviewConfig,
) -> EtfSmaCyclePreview:
    """Evaluate bars and broker observations into one preview-only decision."""

    checked_config = _config(config)
    checked_observation = _observation(broker_observation)
    checked_bars = _bar_tuple(bars)
    as_of = checked_config.as_of or _latest_bar_timestamp(checked_bars)
    signal = evaluate_etf_sma_signal(
        checked_bars,
        EtfSmaSignalConfig(as_of=as_of, symbol=checked_config.symbol),
    )
    blockers = checked_observation.blockers(checked_config.symbol)
    decision, reason, preview_order = _decision_shape(
        signal,
        checked_observation,
        checked_config,
        blockers,
    )
    return EtfSmaCyclePreview(
        preview_version=_PREVIEW_VERSION,
        record_type=_RECORD_TYPE,
        command=_COMMAND,
        run_id=checked_config.run_id,
        symbol=checked_config.symbol,
        asset_class=checked_config.asset_class,
        labels=ETF_SMA_CYCLE_PREVIEW_LABELS,
        paper_lab_only=True,
        not_live_authorized=True,
        profit_claim=_PROFIT_CLAIM,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_preview_performed=False,
        sma_status=_signal_status(signal),
        sma_posture=signal.posture,
        sma=signal,
        bars_source=checked_config.bars_source,
        bars_input_available=checked_config.bars_input_available,
        broker_observation=checked_observation,
        account_observation_available=(
            checked_observation.account_observation_available
        ),
        positions_observation_available=(
            checked_observation.positions_observation_available
        ),
        orders_observation_available=checked_observation.orders_observation_available,
        cash=checked_observation.cash,
        spy_position_quantity=checked_observation.spy_position_quantity,
        open_order_count=checked_observation.open_order_count,
        blockers=blockers,
        decision=decision,
        decision_reason=reason,
        preview_order=preview_order,
    )


def load_etf_sma_cycle_bars_csv(
    path: Path | str,
    *,
    symbol: str = _SYMBOL,
) -> tuple[Bar, ...]:
    """Load daily bars from CSV, returning an empty series if the file is absent."""

    checked_path = _input_path(path)
    checked_symbol = _spy_symbol(symbol)
    if not checked_path.exists():
        return ()
    with checked_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return tuple(_bar_from_mapping(row, checked_symbol) for row in reader)


def load_etf_sma_cycle_bars_jsonl(
    path: Path | str,
    *,
    symbol: str = _SYMBOL,
) -> tuple[Bar, ...]:
    """Load daily bars from JSONL, returning an empty series if the file is absent."""

    checked_path = _input_path(path)
    checked_symbol = _spy_symbol(symbol)
    if not checked_path.exists():
        return ()
    bars: list[Bar] = []
    with checked_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    f"bars_jsonl line {line_number} is not valid JSON."
                ) from exc
            if not isinstance(row, Mapping):
                raise ValidationError(
                    f"bars_jsonl line {line_number} must be a JSON object."
                )
            bars.append(_bar_from_mapping(row, checked_symbol))
    return tuple(bars)


def render_etf_sma_cycle_preview_json(preview: EtfSmaCyclePreview) -> str:
    """Render one newline-free deterministic JSON object."""

    checked_preview = _preview(preview)
    return json.dumps(
        checked_preview.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )


def render_etf_sma_cycle_preview_text(preview: EtfSmaCyclePreview) -> str:
    """Render a compact operator-readable summary."""

    checked_preview = _preview(preview)
    lines = [
        "SPY ETF/SMA cycle preview",
        f"run_id: {checked_preview.run_id}",
        f"symbol: {checked_preview.symbol}",
        f"sma_posture: {checked_preview.sma_posture}",
        f"sma_status: {checked_preview.sma_status}",
        f"decision: {checked_preview.decision}",
        f"decision_reason: {checked_preview.decision_reason}",
        f"blockers: {_joined(checked_preview.blockers)}",
        "account_observation_available: "
        f"{_bool_text(checked_preview.account_observation_available)}",
        "positions_observation_available: "
        f"{_bool_text(checked_preview.positions_observation_available)}",
        "orders_observation_available: "
        f"{_bool_text(checked_preview.orders_observation_available)}",
        f"cash: {_decimal_text(checked_preview.cash) or 'none'}",
        "spy_position_quantity: "
        f"{_decimal_text(checked_preview.spy_position_quantity) or 'none'}",
        f"open_order_count: {checked_preview.open_order_count}",
        f"submitted: {_bool_text(checked_preview.submitted)}",
        f"mutated: {_bool_text(checked_preview.mutated)}",
        "broker_action_performed: "
        f"{_bool_text(checked_preview.broker_action_performed)}",
    ]
    if checked_preview.preview_order is not None:
        preview_order = checked_preview.preview_order
        lines.extend(
            (
                f"preview_side: {preview_order['side']}",
                f"preview_order_type: {preview_order['order_type']}",
                f"preview_time_in_force: {preview_order['time_in_force']}",
            )
        )
        if preview_order.get("notional") is not None:
            lines.append(f"preview_notional: {preview_order['notional']}")
        if preview_order.get("quantity") is not None:
            lines.append(f"preview_quantity: {preview_order['quantity']}")
    return "\n".join(lines)


def write_etf_sma_cycle_preview(
    preview: EtfSmaCyclePreview,
    config: EtfSmaCyclePreviewWriteConfig,
) -> EtfSmaCyclePreviewWriteResult:
    """Write one deterministic JSONL preview record."""

    checked_preview = _preview(preview)
    checked_config = _write_config(config)
    line = render_etf_sma_cycle_preview_json(checked_preview) + "\n"
    created_parent_dirs = _prepare_output_parent(checked_config.output_path, checked_config)
    mode = "a" if checked_config.append else "x"
    try:
        with checked_config.output_path.open(mode, encoding="utf-8", newline="\n") as stream:
            stream.write(line)
    except FileExistsError:
        raise ValidationError("output path exists; append must be true.") from None
    return EtfSmaCyclePreviewWriteResult(
        output_path=checked_config.output_path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        append=checked_config.append,
        created_parent_dirs=created_parent_dirs,
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
    )


def _decision_shape(
    signal: EtfSmaSignalResult,
    observation: EtfSmaCycleBrokerObservation,
    config: EtfSmaCyclePreviewConfig,
    blockers: tuple[str, ...],
) -> tuple[str, str, dict[str, object] | None]:
    if blockers:
        return "blocked", blockers[0], None
    if signal.posture == "insufficient_history":
        return "insufficient_history", "sma_insufficient_history", None

    if signal.posture == "bullish_risk_on":
        if observation.has_spy_position:
            return "hold", "bullish_existing_spy_position", None
        return "buy_preview", "bullish_no_spy_position", _buy_preview_order(config)

    if observation.has_spy_position:
        quantity = observation.spy_position_quantity
        if quantity is None:
            raise ValidationError("sell preview requires observed SPY quantity.")
        return "sell_preview", "risk_off_existing_spy_position", _sell_preview_order(
            config,
            quantity,
        )
    return "hold", "risk_off_no_spy_position", None


def _buy_preview_order(config: EtfSmaCyclePreviewConfig) -> dict[str, object]:
    return {
        "asset_class": config.asset_class,
        "notional": str(config.max_notional),
        "order_type": config.order_type,
        "side": "buy",
        "symbol": config.symbol,
        "time_in_force": config.time_in_force,
    }


def _sell_preview_order(
    config: EtfSmaCyclePreviewConfig,
    quantity: Decimal,
) -> dict[str, object]:
    return {
        "asset_class": config.asset_class,
        "order_type": config.order_type,
        "quantity": str(quantity),
        "side": "sell",
        "symbol": config.symbol,
        "time_in_force": config.time_in_force,
    }


def _signal_status(signal: EtfSmaSignalResult) -> str:
    if signal.posture == "insufficient_history":
        return "insufficient_history"
    return "evaluated"


def _bar_from_mapping(row: Mapping[str, object], symbol: str) -> Bar:
    close = _required_decimal(_row_value(row, "close"), "close")
    open_value = _optional_row_decimal(row, "open") or close
    high = _optional_row_decimal(row, "high") or max(open_value, close)
    low = _optional_row_decimal(row, "low") or min(open_value, close)
    volume = _optional_row_decimal(row, "volume") or Decimal("0")
    row_symbol = _row_value(row, "symbol")
    return Bar(
        symbol=symbol if row_symbol in (None, "") else _spy_symbol(str(row_symbol)),
        timestamp=_row_timestamp(row),
        open=open_value,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _row_timestamp(row: Mapping[str, object]) -> datetime:
    for field_name in ("timestamp", "datetime", "date"):
        value = _row_value(row, field_name)
        if value not in (None, ""):
            return _parse_timestamp(str(value))
    raise ValidationError("bar timestamp/date is required.")


def _parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValidationError("bar timestamp/date is required.")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("bar timestamp/date must be ISO-8601.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _row_value(row: Mapping[str, object], field_name: str) -> object:
    for key, value in row.items():
        if str(key).strip().lower() == field_name:
            return value
    return None


def _optional_row_decimal(row: Mapping[str, object], field_name: str) -> Decimal | None:
    value = _row_value(row, field_name)
    if value in (None, ""):
        return None
    return _required_decimal(value, field_name)


def _required_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_from_value(value)
    if decimal_value is None:
        raise ValidationError(f"{field_name} must be a decimal.")
    return decimal_value


def _bar_tuple(values: Iterable[Bar]) -> tuple[Bar, ...]:
    try:
        bars = tuple(values)
    except TypeError as exc:
        raise ValidationError("bars must be iterable.") from exc
    for index, bar in enumerate(bars):
        if not isinstance(bar, Bar):
            raise ValidationError(f"bars[{index}] must be a Bar.")
    return bars


def _latest_bar_timestamp(bars: tuple[Bar, ...]) -> datetime:
    if not bars:
        return _EMPTY_AS_OF
    return max(bar.timestamp for bar in bars)


def _validate_preview_consistency(preview: EtfSmaCyclePreview) -> None:
    if preview.sma_posture != preview.sma.posture:
        raise ValidationError("sma_posture must match SMA result.")
    if preview.account_observation_available != (
        preview.broker_observation.account_observation_available
    ):
        raise ValidationError("account observation availability mismatch.")
    if preview.positions_observation_available != (
        preview.broker_observation.positions_observation_available
    ):
        raise ValidationError("positions observation availability mismatch.")
    if preview.orders_observation_available != (
        preview.broker_observation.orders_observation_available
    ):
        raise ValidationError("orders observation availability mismatch.")
    if preview.cash != preview.broker_observation.cash:
        raise ValidationError("cash must match broker observation.")
    if preview.spy_position_quantity != preview.broker_observation.spy_position_quantity:
        raise ValidationError("SPY quantity must match broker observation.")
    if preview.open_order_count != preview.broker_observation.open_order_count:
        raise ValidationError("open_order_count must match broker observation.")

    has_order = preview.preview_order is not None
    if preview.decision in ("buy_preview", "sell_preview"):
        if not has_order:
            raise ValidationError("preview decision requires preview_order.")
    elif has_order:
        raise ValidationError("non-preview decision must not include preview_order.")
    if preview.decision == "blocked" and not preview.blockers:
        raise ValidationError("blocked decision requires blockers.")
    if preview.decision != "blocked" and preview.blockers:
        raise ValidationError("non-blocked decision must not include blockers.")


def _optional_preview_order(
    value: object,
    decision: str,
) -> dict[str, object] | None:
    if value is None:
        return None
    if type(value) is not dict:
        raise ValidationError("preview_order must be a dict.")
    expected = {
        "asset_class": _ASSET_CLASS,
        "order_type": _ORDER_TYPE,
        "symbol": _SYMBOL,
        "time_in_force": _TIME_IN_FORCE,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValidationError(f"preview_order {key} is invalid.")
    if decision == "buy_preview":
        if value.get("side") != "buy":
            raise ValidationError("buy preview_order side is invalid.")
        notional = _decimal_from_value(value.get("notional"))
        if notional is None or notional <= Decimal("0"):
            raise ValidationError("buy preview_order notional is invalid.")
        if "quantity" in value:
            raise ValidationError("buy preview_order must not include quantity.")
    elif decision == "sell_preview":
        if value.get("side") != "sell":
            raise ValidationError("sell preview_order side is invalid.")
        quantity = _decimal_from_value(value.get("quantity"))
        if quantity is None or quantity <= Decimal("0"):
            raise ValidationError("sell preview_order quantity is invalid.")
        if "notional" in value:
            raise ValidationError("sell preview_order must not include notional.")
    else:
        raise ValidationError("only preview decisions may include preview_order.")
    return dict(value)


def _prepare_output_parent(
    path: Path,
    config: EtfSmaCyclePreviewWriteConfig,
) -> bool:
    parent = path.parent
    if str(parent) in ("", ".") or parent.exists():
        return False
    if not config.create_parent_dirs:
        raise ValidationError("output parent directory does not exist.")
    parent.mkdir(parents=True, exist_ok=True)
    return True


def _config(value: object) -> EtfSmaCyclePreviewConfig:
    if type(value) is not EtfSmaCyclePreviewConfig:
        raise ValidationError("config must be an EtfSmaCyclePreviewConfig.")
    return value


def _observation(value: object) -> EtfSmaCycleBrokerObservation:
    if type(value) is not EtfSmaCycleBrokerObservation:
        raise ValidationError(
            "broker_observation must be an EtfSmaCycleBrokerObservation."
        )
    return value


def _preview(value: object) -> EtfSmaCyclePreview:
    if type(value) is not EtfSmaCyclePreview:
        raise ValidationError("preview must be an EtfSmaCyclePreview.")
    return value


def _write_config(value: object) -> EtfSmaCyclePreviewWriteConfig:
    if type(value) is not EtfSmaCyclePreviewWriteConfig:
        raise ValidationError("config must be an EtfSmaCyclePreviewWriteConfig.")
    return value


def _decision(value: object) -> str:
    if type(value) is not str or value not in ETF_SMA_CYCLE_PREVIEW_DECISIONS:
        raise ValidationError("decision is invalid.")
    return value


def _sma_status(value: object) -> str:
    if type(value) is not str or value not in ("evaluated", "insufficient_history"):
        raise ValidationError("sma_status is invalid.")
    return value


def _spy_symbol(value: object) -> str:
    symbol = symbol_value(str(value))
    if symbol != _SYMBOL:
        raise ValidationError("symbol must be SPY for this paper-lab cycle.")
    return symbol


def _symbol_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=allow_empty)
    return tuple(symbol_value(item) for item in items)


def _fixed_string_tuple(
    values: object,
    expected: tuple[str, ...],
    field_name: str,
) -> tuple[str, ...]:
    items = _string_tuple(values, field_name, allow_empty=False)
    if items != expected:
        raise ValidationError(f"{field_name} must match required labels.")
    return items


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a list or tuple.")
    items = tuple(_required_string(item, field_name) for item in values)
    if not items and not allow_empty:
        raise ValidationError(f"{field_name} must not be empty.")
    return items


def _output_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("output_path must be a path string.")
    if str(path).strip() == "":
        raise ValidationError("output_path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _input_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("input path must be a path string.")
    if str(path).strip() == "":
        raise ValidationError("input path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("input path must not be a directory.")
    return path


def _utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware UTC.")
    if value.utcoffset() != datetime(1970, 1, 1, tzinfo=UTC).utcoffset():
        raise ValidationError(f"{field_name} must be timezone-aware UTC.")
    return value


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    decimal_value = _decimal_from_value(value)
    if decimal_value is None:
        raise ValidationError(f"{field_name} must be a Decimal.")
    return decimal_value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _optional_decimal(value, field_name)
    if decimal_value is None or decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return decimal_value


def _decimal_from_value(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return decimal_value if decimal_value.is_finite() else None


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_non_negative_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _fixed_int(value: object, expected: int, field_name: str) -> int:
    if type(value) is not int or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be positive.")
    return value


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    if type(value) is not str or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _required_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if text == "" or text != text.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
