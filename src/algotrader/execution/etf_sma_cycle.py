"""Offline ETF/SMA cycle artifact builder.

The command surface in this module is intentionally local-only: it consumes
caller-supplied bars and optional JSONL observations, then writes one cycle
record. It does not import broker SDKs, open sockets, or read credentials.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
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
    "ETF_SMA_CYCLE_LABELS",
    "EtfSmaCycleBrokerState",
    "EtfSmaCycleConfig",
    "EtfSmaCycleOpenOrder",
    "EtfSmaCyclePosition",
    "build_etf_sma_cycle",
    "build_etf_sma_cycle_from_offline_inputs",
    "load_etf_sma_cycle_bars_csv",
    "load_etf_sma_cycle_reconciliation_state",
    "render_etf_sma_cycle_json",
    "render_etf_sma_cycle_text",
    "write_etf_sma_cycle_jsonl",
]


ETF_SMA_CYCLE_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M382 - Unified offline ETF/SMA cycle preview command"
_RECORD_TYPE = "etf_sma_cycle"
_COMMAND = "etf-sma-cycle"
_STRATEGY_NAME = "etf_sma_cycle"
_STRATEGY_VERSION = "v1"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_ALLOWED_SYMBOLS = ("SPY",)
_DEFAULT_FAST_WINDOW = 50
_DEFAULT_SLOW_WINDOW = 200
_DEFAULT_PAPER_CAP = Decimal("25")
_EMPTY_AS_OF = datetime(1970, 1, 1, tzinfo=UTC)
_PROFIT_CLAIM = "none"
_ASSET_CLASS = "equity"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_DEFAULT_BARS_CSV = Path("data/local/spy_daily_bars.csv")


@dataclass(frozen=True, slots=True)
class EtfSmaCyclePosition:
    """Offline position observation for one symbol."""

    symbol: str
    quantity: Decimal | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        quantity = _required_decimal(self.quantity, "quantity")
        if quantity < Decimal("0"):
            raise ValidationError("quantity must be non-negative.")
        object.__setattr__(self, "quantity", quantity)

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "quantity": _decimal_text(self.quantity),
        }


@dataclass(frozen=True, slots=True)
class EtfSmaCycleOpenOrder:
    """Offline open-order observation for one symbol."""

    symbol: str
    client_order_id: str = ""
    broker_order_id: str = ""
    status: str = ""
    side: str = ""
    quantity: str = ""
    filled_quantity: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        for field_name in (
            "client_order_id",
            "broker_order_id",
            "status",
            "side",
            "quantity",
            "filled_quantity",
        ):
            object.__setattr__(
                self,
                field_name,
                _string(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "status": self.status,
            "side": self.side,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaCycleBrokerState:
    """Offline account, position, and open-order state."""

    source: str = "offline_input"
    account_observation_available: bool = False
    positions_observation_available: bool = True
    orders_observation_available: bool = True
    cash: Decimal | str | None = None
    currency: str | None = None
    positions: tuple[EtfSmaCyclePosition, ...] = ()
    open_orders: tuple[EtfSmaCycleOpenOrder, ...] = ()
    open_order_count: int | None = None
    m376_order: Mapping[str, object] | None = None
    source_blockers: tuple[str, ...] = ()
    observed_at: datetime | str | None = None
    submitted: bool = False
    mutated: bool = False
    broker_action_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _required_string(self.source, "source"))
        for field_name in (
            "account_observation_available",
            "positions_observation_available",
            "orders_observation_available",
            "submitted",
            "mutated",
            "broker_action_performed",
        ):
            object.__setattr__(
                self,
                field_name,
                _bool(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "cash", _optional_decimal(self.cash, "cash"))
        object.__setattr__(self, "currency", _optional_string(self.currency, "currency"))
        object.__setattr__(
            self,
            "positions",
            _position_tuple(self.positions),
        )
        object.__setattr__(
            self,
            "open_orders",
            _open_order_tuple(self.open_orders),
        )
        if self.open_order_count is None:
            object.__setattr__(self, "open_order_count", len(self.open_orders))
        else:
            object.__setattr__(
                self,
                "open_order_count",
                _non_negative_int(self.open_order_count, "open_order_count"),
            )
        if self.m376_order is not None and not isinstance(self.m376_order, Mapping):
            raise ValidationError("m376_order must be a mapping.")
        object.__setattr__(
            self,
            "m376_order",
            None if self.m376_order is None else dict(self.m376_order),
        )
        object.__setattr__(
            self,
            "source_blockers",
            _string_tuple(self.source_blockers, "source_blockers", allow_empty=True),
        )
        if self.observed_at is not None:
            object.__setattr__(
                self,
                "observed_at",
                _parse_timestamp(self.observed_at, "observed_at"),
            )

    @property
    def broker_state_available(self) -> bool:
        return self.positions_observation_available and self.orders_observation_available

    def quantity_for_symbol(self, symbol: str) -> Decimal | None:
        checked_symbol = symbol_value(symbol)
        total = Decimal("0")
        found = False
        for position in self.positions:
            if position.symbol == checked_symbol:
                found = True
                total += position.quantity
        return total if found else None

    def has_symbol_position(self, symbol: str) -> bool:
        quantity = self.quantity_for_symbol(symbol)
        return quantity is not None and quantity > Decimal("0")

    def unexpected_position_symbols(self, symbol: str) -> tuple[str, ...]:
        checked_symbol = symbol_value(symbol)
        return tuple(
            position.symbol
            for position in self.positions
            if position.symbol != checked_symbol and position.quantity > Decimal("0")
        )

    def has_open_order_for_symbol(self, symbol: str) -> bool:
        checked_symbol = symbol_value(symbol)
        if any(order.symbol == checked_symbol for order in self.open_orders):
            return True
        return self.open_order_count is not None and self.open_order_count > 0

    def to_dict(self, symbol: str) -> dict[str, object]:
        checked_symbol = symbol_value(symbol)
        symbol_quantity = self.quantity_for_symbol(checked_symbol)
        return {
            "source": self.source,
            "broker_state_available": self.broker_state_available,
            "account_observation_available": self.account_observation_available,
            "positions_observation_available": self.positions_observation_available,
            "orders_observation_available": self.orders_observation_available,
            "cash": _decimal_text(self.cash),
            "currency": self.currency,
            "positions": [position.to_dict() for position in self.positions],
            "position_symbols": [position.symbol for position in self.positions],
            "symbol_position_quantity": _decimal_text(symbol_quantity),
            "open_order_count": self.open_order_count,
            "open_orders": [order.to_dict() for order in self.open_orders],
            "open_order_symbols": [order.symbol for order in self.open_orders],
            "open_order_client_order_ids": [
                order.client_order_id for order in self.open_orders if order.client_order_id
            ],
            "open_order_broker_order_ids": [
                order.broker_order_id for order in self.open_orders if order.broker_order_id
            ],
            "open_order_statuses": [
                order.status for order in self.open_orders if order.status
            ],
            "open_order_sides": [order.side for order in self.open_orders if order.side],
            "open_order_quantities": [
                order.quantity for order in self.open_orders if order.quantity
            ],
            "open_order_filled_quantities": [
                order.filled_quantity
                for order in self.open_orders
                if order.filled_quantity
            ],
            "m376_order": _json_safe(self.m376_order),
            "source_blockers": list(self.source_blockers),
            "observed_at": (
                None
                if self.observed_at is None
                else self.observed_at.isoformat()
            ),
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
        }


@dataclass(frozen=True, slots=True)
class EtfSmaCycleConfig:
    """Configuration for one offline ETF/SMA cycle artifact."""

    run_id: str
    symbol: str = _DEFAULT_SYMBOL
    milestone: str = _MILESTONE
    as_of: datetime | str | None = None
    fast_window: int = _DEFAULT_FAST_WINDOW
    slow_window: int = _DEFAULT_SLOW_WINDOW
    paper_cap: Decimal | str = _DEFAULT_PAPER_CAP
    bars_source: str = ""
    bars_input_available: bool = False
    market_data_csv: Path | str | None = None
    order_reconciliation_log: Path | str | None = None
    cash: Decimal | str | None = None
    position_qty: Decimal | str | None = None
    open_order_count: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(self, "milestone", _required_string(self.milestone, "milestone"))
        if self.as_of is not None:
            object.__setattr__(self, "as_of", _parse_timestamp(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "fast_window",
            _positive_int(self.fast_window, "fast_window"),
        )
        object.__setattr__(
            self,
            "slow_window",
            _positive_int(self.slow_window, "slow_window"),
        )
        if self.fast_window >= self.slow_window:
            raise ValidationError("fast_window must be less than slow_window.")
        object.__setattr__(
            self,
            "paper_cap",
            _positive_decimal(self.paper_cap, "paper_cap"),
        )
        object.__setattr__(
            self,
            "bars_source",
            _string(self.bars_source, "bars_source"),
        )
        object.__setattr__(
            self,
            "bars_input_available",
            _bool(self.bars_input_available, "bars_input_available"),
        )
        object.__setattr__(
            self,
            "market_data_csv",
            _optional_path(self.market_data_csv, "market_data_csv"),
        )
        object.__setattr__(
            self,
            "order_reconciliation_log",
            _optional_path(self.order_reconciliation_log, "order_reconciliation_log"),
        )
        object.__setattr__(self, "cash", _optional_decimal(self.cash, "cash"))
        object.__setattr__(
            self,
            "position_qty",
            _optional_decimal(self.position_qty, "position_qty"),
        )
        object.__setattr__(
            self,
            "open_order_count",
            (
                None
                if self.open_order_count is None
                else _non_negative_int(self.open_order_count, "open_order_count")
            ),
        )


def build_etf_sma_cycle(
    bars: Iterable[Bar],
    broker_state: EtfSmaCycleBrokerState,
    config: EtfSmaCycleConfig,
) -> dict[str, object]:
    """Build one primitive-only offline cycle record."""

    checked_config = _config(config)
    checked_state = _broker_state(broker_state)
    checked_bars = _bar_tuple(bars, checked_config.symbol)
    as_of = _cycle_as_of(checked_config, checked_state, checked_bars)
    signal = evaluate_etf_sma_signal(
        checked_bars,
        EtfSmaSignalConfig(
            as_of=as_of,
            symbol=checked_config.symbol,
            short_window=checked_config.fast_window,
            long_window=checked_config.slow_window,
        ),
    )
    sma_posture = _cycle_posture(signal)
    blockers = _cycle_blockers(checked_config, checked_state)
    decision, decision_reason, preview_order = _decision_shape(
        sma_posture,
        checked_config,
        checked_state,
        blockers,
    )
    next_forbidden_action = _next_forbidden_action(blockers)
    state_payload = checked_state.to_dict(checked_config.symbol)
    symbol_position_quantity = checked_state.quantity_for_symbol(checked_config.symbol)

    return {
        "milestone": checked_config.milestone,
        "run_id": checked_config.run_id,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "strategy": {
            "name": _STRATEGY_NAME,
            "version": _STRATEGY_VERSION,
        },
        "strategy_name": _STRATEGY_NAME,
        "strategy_version": _STRATEGY_VERSION,
        "symbol": checked_config.symbol,
        "allowlist": _allowlist_result(checked_config.symbol),
        "allowlist_result": _allowlist_result(checked_config.symbol),
        "labels": list(ETF_SMA_CYCLE_LABELS),
        "paper_lab_only": True,
        "signal_evaluation_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "as_of": as_of.isoformat(),
        "evaluated_at": as_of.isoformat(),
        "sma_config": {
            "fast_window": checked_config.fast_window,
            "slow_window": checked_config.slow_window,
            "required_bars": checked_config.slow_window,
        },
        "sma_status": _sma_status(signal),
        "sma_posture": sma_posture,
        "sma": _sma_payload(signal),
        "market_data": {
            "source": checked_config.bars_source,
            "input_available": checked_config.bars_input_available,
            "total_bar_count": signal.total_bar_count,
            "usable_bar_count": signal.usable_bar_count,
            "ignored_future_bar_count": signal.ignored_future_bar_count,
        },
        "bars_source": checked_config.bars_source,
        "bars_input_available": checked_config.bars_input_available,
        "broker_state": state_payload,
        "broker_state_source": checked_state.source,
        "broker_state_available": checked_state.broker_state_available,
        "account_observation_available": checked_state.account_observation_available,
        "positions_observation_available": checked_state.positions_observation_available,
        "orders_observation_available": checked_state.orders_observation_available,
        "cash": _decimal_text(checked_state.cash),
        "positions": state_payload["positions"],
        "position_symbols": state_payload["position_symbols"],
        "spy_position_quantity": _decimal_text(symbol_position_quantity),
        "open_order_count": checked_state.open_order_count,
        "open_order_symbols": state_payload["open_order_symbols"],
        "open_order_client_order_ids": state_payload["open_order_client_order_ids"],
        "open_order_broker_order_ids": state_payload["open_order_broker_order_ids"],
        "open_order_statuses": state_payload["open_order_statuses"],
        "open_order_sides": state_payload["open_order_sides"],
        "open_order_quantities": state_payload["open_order_quantities"],
        "open_order_filled_quantities": state_payload["open_order_filled_quantities"],
        "m376_order_summary": _json_safe(checked_state.m376_order),
        "decision": decision,
        "decision_reason": decision_reason,
        "blockers": list(blockers),
        "next_allowed_action": _next_allowed_action(blockers),
        "next_forbidden_action": next_forbidden_action,
        "preview_order": _json_safe(preview_order),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_mutation_allowed": False,
        "live_authorized": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
    }


def build_etf_sma_cycle_from_offline_inputs(
    config: EtfSmaCycleConfig,
) -> dict[str, object]:
    """Load local inputs named in config and build one cycle record."""

    checked_config = _config(config)
    bars, bars_source, bars_available = _load_configured_bars(checked_config)
    broker_state = _load_configured_broker_state(checked_config)
    core_config = EtfSmaCycleConfig(
        run_id=checked_config.run_id,
        symbol=checked_config.symbol,
        milestone=checked_config.milestone,
        as_of=checked_config.as_of,
        fast_window=checked_config.fast_window,
        slow_window=checked_config.slow_window,
        paper_cap=checked_config.paper_cap,
        bars_source=bars_source,
        bars_input_available=bars_available,
    )
    return build_etf_sma_cycle(bars, broker_state, core_config)


def load_etf_sma_cycle_bars_csv(
    path: Path | str,
    *,
    symbol: str = _DEFAULT_SYMBOL,
) -> tuple[Bar, ...]:
    """Load deterministic daily bars from a local CSV path."""

    checked_path = _path(path, "path")
    checked_symbol = symbol_value(symbol)
    if not checked_path.exists():
        raise ValidationError("market_data_csv was not found.")
    bars: list[Bar] = []
    with checked_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            bars.append(_bar_from_mapping(row, checked_symbol))
    return tuple(bars)


def load_etf_sma_cycle_reconciliation_state(
    path: Path | str,
    *,
    symbol: str = _DEFAULT_SYMBOL,
) -> EtfSmaCycleBrokerState:
    """Load offline broker state from the latest reconciliation JSONL record."""

    checked_path = _path(path, "order_reconciliation_log")
    checked_symbol = symbol_value(symbol)
    if not checked_path.exists():
        return EtfSmaCycleBrokerState(
            source=str(checked_path),
            positions_observation_available=False,
            orders_observation_available=False,
            source_blockers=("order_reconciliation_unavailable",),
        )
    record = _read_latest_jsonl_mapping(checked_path)
    blockers = _reconciliation_blockers(record)
    positions = _reconciliation_positions(record, checked_symbol)
    open_orders = _reconciliation_open_orders(record, checked_symbol)
    open_order_count = _optional_int(
        record.get("open_order_count"),
        "open_order_count",
    )
    if open_order_count is None:
        open_order_count = len(open_orders)
    observed_at = _first_text(
        record.get("evaluated_at"),
        record.get("observed_submitted_at"),
        record.get("generated_at"),
    )
    return EtfSmaCycleBrokerState(
        source=str(checked_path),
        account_observation_available=_bool_or(
            record.get("account_observation_available"),
            False,
        ),
        positions_observation_available=_bool_or(
            record.get("positions_observation_available"),
            bool(record.get("spy_position_qty") not in (None, "")),
        ),
        orders_observation_available=_bool_or(
            record.get("orders_observation_available"),
            record.get("open_order_count") is not None,
        ),
        cash=record.get("cash"),
        currency=_text(record.get("currency")) or None,
        positions=positions,
        open_orders=open_orders,
        open_order_count=open_order_count,
        m376_order=_m376_order_summary(record, blockers),
        source_blockers=blockers,
        observed_at=observed_at or None,
        submitted=_bool_or(record.get("submitted"), False),
        mutated=_bool_or(record.get("mutated"), False),
        broker_action_performed=_bool_or(
            record.get("broker_action_performed"),
            False,
        ),
    )


def render_etf_sma_cycle_json(payload: Mapping[str, object]) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_cycle_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-facing text summary."""

    blockers = payload.get("blockers")
    forbidden = payload.get("next_forbidden_action")
    return "\n".join(
        (
            "ETF/SMA offline cycle",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"sma_posture: {payload.get('sma_posture', '')}",
            f"decision: {payload.get('decision', '')}",
            f"decision_reason: {payload.get('decision_reason', '')}",
            f"blockers: {_joined(blockers)}",
            f"next_allowed_action: {payload.get('next_allowed_action', '')}",
            f"next_forbidden_action: {_joined(forbidden)}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
        )
    )


def write_etf_sma_cycle_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> Path:
    """Write exactly one JSONL record, replacing any previous local artifact."""

    path = _path(output_path, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_cycle_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return path


def _load_configured_bars(
    config: EtfSmaCycleConfig,
) -> tuple[tuple[Bar, ...], str, bool]:
    path = config.market_data_csv or _DEFAULT_BARS_CSV
    source = str(path)
    if not path.exists():
        return (), source, False
    return load_etf_sma_cycle_bars_csv(path, symbol=config.symbol), source, True


def _load_configured_broker_state(
    config: EtfSmaCycleConfig,
) -> EtfSmaCycleBrokerState:
    if config.order_reconciliation_log is not None:
        state = load_etf_sma_cycle_reconciliation_state(
            config.order_reconciliation_log,
            symbol=config.symbol,
        )
        if config.cash is not None and state.cash is None:
            return EtfSmaCycleBrokerState(
                source=state.source,
                account_observation_available=True,
                positions_observation_available=state.positions_observation_available,
                orders_observation_available=state.orders_observation_available,
                cash=config.cash,
                currency=state.currency,
                positions=state.positions,
                open_orders=state.open_orders,
                open_order_count=state.open_order_count,
                m376_order=state.m376_order,
                source_blockers=state.source_blockers,
                observed_at=state.observed_at,
                submitted=state.submitted,
                mutated=state.mutated,
                broker_action_performed=state.broker_action_performed,
            )
        return state

    if config.position_qty is None or config.open_order_count is None:
        return EtfSmaCycleBrokerState(
            source="offline_input_missing",
            positions_observation_available=False,
            orders_observation_available=False,
            source_blockers=("broker_state_unavailable",),
        )

    positions: tuple[EtfSmaCyclePosition, ...] = ()
    if config.position_qty > Decimal("0"):
        positions = (
            EtfSmaCyclePosition(
                symbol=config.symbol,
                quantity=config.position_qty,
            ),
        )
    open_orders: tuple[EtfSmaCycleOpenOrder, ...] = ()
    if config.open_order_count > 0:
        open_orders = (EtfSmaCycleOpenOrder(symbol=config.symbol),)
    return EtfSmaCycleBrokerState(
        source="explicit_offline_input",
        account_observation_available=config.cash is not None,
        positions_observation_available=True,
        orders_observation_available=True,
        cash=config.cash,
        positions=positions,
        open_orders=open_orders,
        open_order_count=config.open_order_count,
    )


def _decision_shape(
    sma_posture: str,
    config: EtfSmaCycleConfig,
    state: EtfSmaCycleBrokerState,
    blockers: tuple[str, ...],
) -> tuple[str, str, dict[str, object] | None]:
    if "symbol_not_allowlisted" in blockers:
        return "blocked/symbol_not_allowlisted", "symbol_not_allowlisted", None
    if "broker_state_unavailable" in blockers:
        return "blocked/broker_state_unavailable", "broker_state_unavailable", None
    if "open_order_present" in blockers:
        return "blocked/open_order_present", "open_order_present", None
    if "unexpected_non_spy_position" in blockers:
        return (
            "blocked/unexpected_non_spy_position",
            "unexpected_non_spy_position",
            None,
        )
    if blockers:
        return f"blocked/{blockers[0]}", blockers[0], None
    if sma_posture == "insufficient_history":
        return "insufficient_history", "sma_insufficient_history", None
    if sma_posture == "risk_on":
        if state.has_symbol_position(config.symbol):
            return "hold/noop", "risk_on_existing_position", None
        return "buy_preview", "risk_on_no_position", _buy_preview_order(config)
    if state.has_symbol_position(config.symbol):
        quantity = state.quantity_for_symbol(config.symbol)
        if quantity is None:
            raise ValidationError("sell preview requires position quantity.")
        return "sell_preview", "risk_off_existing_position", _sell_preview_order(
            config,
            quantity,
        )
    return "hold/noop", "risk_off_no_position", None


def _cycle_blockers(
    config: EtfSmaCycleConfig,
    state: EtfSmaCycleBrokerState,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not _allowlist_result(config.symbol)["allowed"]:
        blockers.append("symbol_not_allowlisted")
    if not state.broker_state_available:
        blockers.append("broker_state_unavailable")
    if state.unexpected_position_symbols(config.symbol):
        blockers.append("unexpected_non_spy_position")
    blockers.extend(state.source_blockers)
    if state.has_open_order_for_symbol(config.symbol):
        blockers.append("open_order_present")
    if state.submitted:
        blockers.append("offline_input_submitted_not_false")
    if state.mutated:
        blockers.append("offline_input_mutated_not_false")
    if state.broker_action_performed:
        blockers.append("offline_input_broker_action_not_false")
    return _dedupe(tuple(blockers))


def _next_allowed_action(blockers: tuple[str, ...]) -> str:
    if "broker_state_unavailable" in blockers:
        return "read_only_reconciliation_before_any_spy_submit"
    if "m376_order_nonterminal" in blockers or "open_order_present" in blockers:
        return "offline_work_or_read_only_reconciliation"
    return "offline_research_or_operator_review_only"


def _next_forbidden_action(blockers: tuple[str, ...]) -> list[str]:
    actions = [
        "broker_mutation_from_etf_sma_cycle",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_cycle",
    ]
    if "m376_order_nonterminal" in blockers or "open_order_present" in blockers:
        actions.append("spy_submit_until_m376_terminal")
    if "broker_state_unavailable" in blockers:
        actions.extend(
            (
                "spy_submit_until_order_state_known",
                "spy_submit_before_read_only_reconciliation",
            )
        )
    return list(_dedupe(tuple(actions)))


def _allowlist_result(symbol: str) -> dict[str, object]:
    checked_symbol = symbol_value(symbol)
    allowed = checked_symbol in _DEFAULT_ALLOWED_SYMBOLS
    return {
        "allowed": allowed,
        "symbol": checked_symbol,
        "allowed_symbols": list(_DEFAULT_ALLOWED_SYMBOLS),
        "reason": "symbol_allowlisted" if allowed else "symbol_not_allowlisted",
    }


def _cycle_as_of(
    config: EtfSmaCycleConfig,
    state: EtfSmaCycleBrokerState,
    bars: tuple[Bar, ...],
) -> datetime:
    if config.as_of is not None:
        return config.as_of
    if bars:
        return max(bar.timestamp for bar in bars)
    if state.observed_at is not None:
        return state.observed_at
    return _EMPTY_AS_OF


def _cycle_posture(signal: EtfSmaSignalResult) -> str:
    if signal.posture == "bullish_risk_on":
        return "risk_on"
    if signal.posture == "defensive_risk_off":
        return "risk_off"
    return "insufficient_history"


def _sma_status(signal: EtfSmaSignalResult) -> str:
    if signal.posture == "insufficient_history":
        return "insufficient_history"
    return "evaluated"


def _sma_payload(signal: EtfSmaSignalResult) -> dict[str, object]:
    payload = signal.to_dict()
    payload["fast_window"] = signal.short_window
    payload["slow_window"] = signal.long_window
    payload["required_bars"] = signal.long_window
    payload["fast_sma"] = _decimal_text(signal.short_sma)
    payload["slow_sma"] = _decimal_text(signal.long_sma)
    payload["cycle_posture"] = _cycle_posture(signal)
    return payload


def _buy_preview_order(config: EtfSmaCycleConfig) -> dict[str, object]:
    return {
        "asset_class": _ASSET_CLASS,
        "symbol": config.symbol,
        "side": "buy",
        "order_type": _ORDER_TYPE,
        "time_in_force": _TIME_IN_FORCE,
        "notional": _decimal_text(config.paper_cap),
        "preview_only": True,
    }


def _sell_preview_order(
    config: EtfSmaCycleConfig,
    quantity: Decimal,
) -> dict[str, object]:
    return {
        "asset_class": _ASSET_CLASS,
        "symbol": config.symbol,
        "side": "sell",
        "order_type": _ORDER_TYPE,
        "time_in_force": _TIME_IN_FORCE,
        "quantity": _decimal_text(quantity),
        "preview_only": True,
    }


def _reconciliation_blockers(record: Mapping[str, object]) -> tuple[str, ...]:
    blockers = list(_string_tuple(record.get("blockers", ()), "blockers", allow_empty=True))
    if _m376_nonterminal_open(record, tuple(blockers)):
        blockers.extend(("m376_order_nonterminal", "open_order_present"))
    elif _open_order_present(record):
        blockers.append("open_order_present")
    return _dedupe(tuple(blockers))


def _m376_order_summary(
    record: Mapping[str, object],
    blockers: tuple[str, ...],
) -> dict[str, object]:
    terminal_state = _text(record.get("terminal_state")) or "unknown"
    state = "unknown"
    if _m376_nonterminal_open(record, blockers):
        state = "nonterminal_open"
    elif terminal_state == "terminal":
        state = "terminal"
    return {
        "source_supplied": True,
        "run_id": _text(record.get("run_id")),
        "symbol": _text(record.get("symbol")),
        "client_order_id": _text(record.get("client_order_id")),
        "broker_order_id": _text(record.get("broker_order_id")),
        "expected_side": _text(record.get("expected_side")),
        "expected_qty": _text(record.get("expected_qty")),
        "observed_status": _text(record.get("observed_status")),
        "observed_side": _text(record.get("observed_side")),
        "observed_qty": _text(record.get("observed_qty")),
        "observed_filled_qty": _text(record.get("observed_filled_qty")),
        "spy_position_qty": _text(record.get("spy_position_qty")),
        "open_order_count": _optional_int(record.get("open_order_count"), "open_order_count"),
        "terminal_state": terminal_state,
        "terminal_reason": _text(record.get("terminal_reason")),
        "reconciliation_decision": _text(record.get("reconciliation_decision")),
        "state": state,
        "blockers": list(blockers),
        "next_spy_submit_blocked": _bool_or(
            record.get("next_spy_submit_blocked"),
            bool(blockers),
        ),
        "submitted": _bool_or(record.get("submitted"), False),
        "mutated": _bool_or(record.get("mutated"), False),
        "broker_action_performed": _bool_or(
            record.get("broker_action_performed"),
            False,
        ),
        "live_authorized": _bool_or(record.get("live_authorized"), False),
    }


def _reconciliation_positions(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[EtfSmaCyclePosition, ...]:
    positions: list[EtfSmaCyclePosition] = []
    spy_qty = _optional_decimal(record.get("spy_position_qty"), "spy_position_qty")
    if spy_qty is not None and spy_qty > Decimal("0"):
        positions.append(EtfSmaCyclePosition(symbol=symbol, quantity=spy_qty))
    non_spy_positions = record.get("non_spy_positions")
    if isinstance(non_spy_positions, Sequence) and not isinstance(
        non_spy_positions,
        (str, bytes),
    ):
        for item in non_spy_positions:
            if isinstance(item, Mapping):
                item_symbol = _text(item.get("symbol"))
                quantity = _optional_decimal(item.get("quantity"), "quantity")
                if item_symbol and quantity is not None and quantity > Decimal("0"):
                    positions.append(
                        EtfSmaCyclePosition(symbol=item_symbol, quantity=quantity)
                    )
    return tuple(positions)


def _reconciliation_open_orders(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[EtfSmaCycleOpenOrder, ...]:
    symbols = _string_list(record.get("open_order_symbols"))
    client_ids = _string_list(record.get("open_order_client_order_ids"))
    broker_ids = _string_list(record.get("open_order_broker_order_ids"))
    statuses = _string_list(record.get("open_order_statuses"))
    sides = _string_list(record.get("open_order_sides"))
    quantities = _string_list(record.get("open_order_quantities"))
    filled_quantities = _string_list(record.get("open_order_filled_quantities"))
    open_order_count = _optional_int(record.get("open_order_count"), "open_order_count")
    count = max(
        len(symbols),
        len(client_ids),
        len(broker_ids),
        len(statuses),
        len(sides),
        len(quantities),
        len(filled_quantities),
        open_order_count or 0,
    )
    orders: list[EtfSmaCycleOpenOrder] = []
    for index in range(count):
        order_symbol = _item_or_default(symbols, index, symbol)
        orders.append(
            EtfSmaCycleOpenOrder(
                symbol=order_symbol,
                client_order_id=_item_or_default(client_ids, index, ""),
                broker_order_id=_item_or_default(broker_ids, index, ""),
                status=_item_or_default(statuses, index, ""),
                side=_item_or_default(sides, index, ""),
                quantity=_item_or_default(quantities, index, ""),
                filled_quantity=_item_or_default(filled_quantities, index, ""),
            )
        )
    return tuple(orders)


def _m376_nonterminal_open(
    record: Mapping[str, object],
    blockers: tuple[str, ...],
) -> bool:
    return (
        record.get("terminal_state") == "nonterminal"
        or record.get("reconciliation_decision") == "m376_nonterminal_open"
        or "m376_order_nonterminal" in blockers
    )


def _open_order_present(record: Mapping[str, object]) -> bool:
    open_order_count = _optional_int(record.get("open_order_count"), "open_order_count")
    spy_open_order_count = _optional_int(
        record.get("spy_open_order_count"),
        "spy_open_order_count",
    )
    return (
        (open_order_count is not None and open_order_count > 0)
        or (spy_open_order_count is not None and spy_open_order_count > 0)
        or bool(_string_list(record.get("open_order_symbols")))
    )


def _bar_from_mapping(row: Mapping[str, object], symbol: str) -> Bar:
    close = _required_decimal(_row_value(row, "close"), "close")
    open_value = _optional_row_decimal(row, "open") or close
    high = _optional_row_decimal(row, "high") or max(open_value, close)
    low = _optional_row_decimal(row, "low") or min(open_value, close)
    volume = _optional_row_decimal(row, "volume") or Decimal("0")
    row_symbol = _row_value(row, "symbol")
    return Bar(
        symbol=symbol if row_symbol in (None, "") else symbol_value(str(row_symbol)),
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
            return _parse_timestamp(value, field_name)
    raise ValidationError("bar timestamp/date is required.")


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


def _read_latest_jsonl_mapping(path: Path) -> dict[str, object]:
    latest: dict[str, object] | None = None
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    f"order_reconciliation_log line {line_number} is not valid JSON."
                ) from exc
            if not isinstance(payload, Mapping):
                raise ValidationError(
                    f"order_reconciliation_log line {line_number} must be an object."
                )
            latest = dict(payload)
    if latest is None:
        raise ValidationError("order_reconciliation_log must contain a JSON object.")
    return latest


def _bar_tuple(values: Iterable[Bar], symbol: str) -> tuple[Bar, ...]:
    try:
        bars = tuple(values)
    except TypeError as exc:
        raise ValidationError("bars must be iterable.") from exc
    checked_symbol = symbol_value(symbol)
    seen_dates: set[object] = set()
    for index, bar in enumerate(bars):
        if not isinstance(bar, Bar):
            raise ValidationError(f"bars[{index}] must be a Bar.")
        if bar.symbol != checked_symbol:
            raise ValidationError("bars must contain only the configured symbol.")
        timestamp = _parse_timestamp(bar.timestamp, "timestamp")
        bar_date = timestamp.date()
        if bar_date in seen_dates:
            raise ValidationError("bars must not contain duplicate daily dates.")
        seen_dates.add(bar_date)
    return tuple(sorted(bars, key=lambda item: item.timestamp))


def _position_tuple(value: object) -> tuple[EtfSmaCyclePosition, ...]:
    if type(value) not in (tuple, list):
        raise ValidationError("positions must be a tuple or list.")
    positions = tuple(value)
    for index, position in enumerate(positions):
        if type(position) is not EtfSmaCyclePosition:
            raise ValidationError(f"positions[{index}] must be an EtfSmaCyclePosition.")
    return positions


def _open_order_tuple(value: object) -> tuple[EtfSmaCycleOpenOrder, ...]:
    if type(value) not in (tuple, list):
        raise ValidationError("open_orders must be a tuple or list.")
    open_orders = tuple(value)
    for index, order in enumerate(open_orders):
        if type(order) is not EtfSmaCycleOpenOrder:
            raise ValidationError(f"open_orders[{index}] must be an EtfSmaCycleOpenOrder.")
    return open_orders


def _config(value: object) -> EtfSmaCycleConfig:
    if type(value) is not EtfSmaCycleConfig:
        raise ValidationError("config must be an EtfSmaCycleConfig.")
    return value


def _broker_state(value: object) -> EtfSmaCycleBrokerState:
    if type(value) is not EtfSmaCycleBrokerState:
        raise ValidationError("broker_state must be an EtfSmaCycleBrokerState.")
    return value


def _parse_timestamp(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = _required_string(str(value), field_name)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _path(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _optional_path(value: object, field_name: str) -> Path | None:
    if value is None:
        return None
    return _path(value, field_name)


def _required_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _optional_decimal(value, field_name)
    if decimal_value is None:
        raise ValidationError(f"{field_name} must be a decimal.")
    return decimal_value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _required_decimal(value, field_name)
    if decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return decimal_value


def _optional_decimal(value: object, field_name: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a decimal.") from exc
    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return decimal_value


def _optional_int(value: object, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    try:
        integer = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be an integer.") from exc
    if integer < 0:
        raise ValidationError(f"{field_name} must be non-negative.")
    return integer


def _non_negative_int(value: object, field_name: str) -> int:
    integer = _optional_int(value, field_name)
    if integer is None:
        raise ValidationError(f"{field_name} must be an integer.")
    return integer


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be positive.")
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _string(value, field_name)


def _required_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if text == "" or text != text.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value


def _text(value: object) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def _first_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _string_tuple(
    value: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if value in (None, ""):
        values: tuple[object, ...] = ()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = tuple(value)
    else:
        raise ValidationError(f"{field_name} must be a sequence.")
    strings = tuple(_required_string(str(item), field_name) for item in values)
    if not allow_empty and not strings:
        raise ValidationError(f"{field_name} must not be empty.")
    return strings


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _bool_or(value: object, default: bool) -> bool:
    if value is True:
        return True
    if value is False:
        return False
    return default


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _item_or_default(values: tuple[str, ...], index: int, default: str) -> str:
    if index < len(values):
        return values[index]
    return default


def _row_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _joined(value: object) -> str:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = [str(item) for item in value if str(item)]
        return ",".join(items) if items else "none"
    text = _text(value)
    return text or "none"


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


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
