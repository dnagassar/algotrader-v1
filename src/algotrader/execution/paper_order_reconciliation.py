"""Read-only paper order reconciliation artifacts.

This module accepts caller-supplied broker observations through a narrow
read-only interface. It does not import broker SDKs and does not expose any
broker mutation path.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError


PAPER_ORDER_RECONCILIATION_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)
PAPER_ORDER_RECONCILIATION_MILESTONE = (
    "M379 - Read-only M376 exact order reconciliation and SPY cycle-preview lineage"
)
PAPER_ORDER_RECONCILIATION_DECISIONS = (
    "m376_terminal_filled",
    "m376_terminal_nonfilled",
    "m376_nonterminal_open",
    "m376_not_found",
    "m376_ambiguous",
    "broker_unavailable",
)

_ORDER_SOURCES = (
    ("open", "open"),
    ("all", "all"),
    ("closed", "closed"),
)
_EXPECTED_SIZING_MODES = {"qty", "notional"}
_SOURCE_PRIORITY = {"open": 0, "all": 1, "closed": 2}
_TERMINAL_STATUSES = {"filled", "canceled", "cancelled", "expired", "rejected"}
_NONTERMINAL_STATUSES = {
    "accepted",
    "held",
    "new",
    "open",
    "partially_filled",
    "pending_cancel",
    "pending_new",
    "submitted",
}
_EMPTY_OBSERVED_FIELDS = {
    "observed_status": "",
    "observed_symbol": "",
    "observed_side": "",
    "observed_qty": "",
    "observed_filled_qty": "",
    "observed_remaining_qty": "",
    "observed_avg_fill_price": "",
    "observed_submitted_at": "",
    "observed_filled_at": "",
    "observed_canceled_at": "",
    "observed_expired_at": "",
}


OrderQueryFactory = Callable[[str], object]
Redactor = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class PaperOrderReconciliationConfig:
    """Parameterized read-only reconciliation request."""

    run_id: str
    symbol: str
    client_order_id: str
    broker_order_id: str
    expected_side: str
    expected_qty: Decimal | str
    expected_sizing_mode: str = "qty"
    milestone: str = PAPER_ORDER_RECONCILIATION_MILESTONE
    profile_gate_passed: bool = False
    profile_gate_detail: str = ""
    paper_profile_ready: bool = False
    live_url_detected: bool = False
    order_history_coverage_complete: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "milestone", _required_string(self.milestone, "milestone"))
        object.__setattr__(self, "symbol", symbol_value(str(self.symbol)))
        object.__setattr__(
            self,
            "client_order_id",
            _required_string(self.client_order_id, "client_order_id"),
        )
        object.__setattr__(
            self,
            "broker_order_id",
            _required_string(self.broker_order_id, "broker_order_id"),
        )
        side = _required_string(self.expected_side, "expected_side").lower()
        if side not in {"buy", "sell"}:
            raise ValidationError("expected_side must be buy or sell.")
        object.__setattr__(self, "expected_side", side)
        object.__setattr__(
            self,
            "expected_qty",
            _positive_decimal(self.expected_qty, "expected_qty"),
        )
        sizing_mode = _required_string(
            self.expected_sizing_mode,
            "expected_sizing_mode",
        ).lower()
        if sizing_mode not in _EXPECTED_SIZING_MODES:
            raise ValidationError("expected_sizing_mode must be qty or notional.")
        object.__setattr__(self, "expected_sizing_mode", sizing_mode)
        object.__setattr__(
            self,
            "profile_gate_passed",
            _bool(self.profile_gate_passed, "profile_gate_passed"),
        )
        object.__setattr__(
            self,
            "profile_gate_detail",
            _string(self.profile_gate_detail, "profile_gate_detail"),
        )
        object.__setattr__(
            self,
            "paper_profile_ready",
            _bool(self.paper_profile_ready, "paper_profile_ready"),
        )
        object.__setattr__(
            self,
            "live_url_detected",
            _bool(self.live_url_detected, "live_url_detected"),
        )
        object.__setattr__(
            self,
            "order_history_coverage_complete",
            _bool(
                self.order_history_coverage_complete,
                "order_history_coverage_complete",
            ),
        )


@dataclass(frozen=True, slots=True)
class PaperOrderReconciliationWriteResult:
    """Local JSONL write metadata."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool

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
        object.__setattr__(self, "submitted", _false_bool(self.submitted, "submitted"))
        object.__setattr__(self, "mutated", _false_bool(self.mutated, "mutated"))
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(self.broker_action_performed, "broker_action_performed"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
        }


def reconcile_paper_order(
    config: PaperOrderReconciliationConfig,
    *,
    broker: object | None,
    query_factory: OrderQueryFactory,
    redactor: Redactor | None = None,
    broker_error: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build one conservative read-only reconciliation payload."""

    checked_config = _config(config)
    checked_redactor = redactor or (lambda value: value)
    payload = _base_payload(checked_config)
    broker_unavailable_reason = dict(broker_error or {})
    if not checked_config.profile_gate_passed:
        broker_unavailable_reason = {
            "error_type": "ConfigValidationError",
            "message": checked_config.profile_gate_detail,
        }

    if broker is None or broker_unavailable_reason:
        reason = "paper_profile_required"
        if checked_config.profile_gate_passed:
            reason = "broker_observation_unavailable"
        return _finalize_payload(
            {
                **payload,
                "unavailable_observations": [
                    "account",
                    "positions",
                    "orders",
                ],
                "unavailable_reasons": {
                    "broker": _json_safe(broker_unavailable_reason)
                }
                if broker_unavailable_reason
                else {},
            },
            exact_source="unavailable",
            terminal_state="unknown",
            terminal_reason=reason,
            mismatches=(),
            blockers=(reason, "broker_observation_unavailable"),
            decision="broker_unavailable",
            next_blocked=True,
            reason=reason,
        )

    observed = _observe_broker(
        broker,
        checked_config,
        query_factory,
        checked_redactor,
    )
    payload = {**payload, **observed.context_payload}
    return _with_order_classification(
        payload,
        checked_config,
        observed,
    )


def render_paper_order_reconciliation_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_paper_order_reconciliation_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable summary."""

    lines = [
        "Paper order reconciliation",
        f"run_id: {payload['run_id']}",
        f"milestone: {payload['milestone']}",
        f"symbol: {payload['symbol']}",
        f"client_order_id: {payload['client_order_id']}",
        f"broker_order_id: {payload['broker_order_id']}",
        f"exact_order_found: {_bool_text(bool(payload['exact_order_found']))}",
        f"exact_order_source: {payload['exact_order_source']}",
        f"observed_status: {payload['observed_status'] or 'none'}",
        f"terminal_state: {payload['terminal_state']}",
        f"reconciliation_decision: {payload['reconciliation_decision']}",
        f"next_spy_submit_blocked: {_bool_text(bool(payload['next_spy_submit_blocked']))}",
        f"reason: {payload['reason']}",
        f"blockers: {_joined(payload.get('blockers', []))}",
        f"spy_position_qty: {payload.get('spy_position_qty') or 'none'}",
        f"open_order_count: {payload.get('open_order_count')}",
        f"submitted: {_bool_text(bool(payload['submitted']))}",
        f"mutated: {_bool_text(bool(payload['mutated']))}",
        "broker_action_performed: "
        f"{_bool_text(bool(payload['broker_action_performed']))}",
    ]
    return "\n".join(lines)


def write_paper_order_reconciliation_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
    *,
    append: bool = True,
    create_parent_dirs: bool = True,
) -> PaperOrderReconciliationWriteResult:
    """Write one deterministic JSONL reconciliation record."""

    path = _output_path(output_path)
    parent = path.parent
    if str(parent) not in ("", ".") and not parent.exists():
        if not create_parent_dirs:
            raise ValidationError("output parent directory does not exist.")
        parent.mkdir(parents=True, exist_ok=True)

    line = render_paper_order_reconciliation_json(payload) + "\n"
    mode = "a" if append else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as stream:
            stream.write(line)
    except FileExistsError:
        raise ValidationError("output path exists; append must be true.") from None

    return PaperOrderReconciliationWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
    )


@dataclass(frozen=True, slots=True)
class _BrokerObservation:
    context_payload: dict[str, object]
    source_orders: Mapping[str, tuple[dict[str, object], ...]]
    source_available: Mapping[str, bool]


def _base_payload(config: PaperOrderReconciliationConfig) -> dict[str, object]:
    profile_gate_status = "passed" if config.profile_gate_passed else "blocked"
    return {
        "run_id": config.run_id,
        "milestone": config.milestone,
        "symbol": config.symbol,
        "client_order_id": config.client_order_id,
        "broker_order_id": config.broker_order_id,
        "expected_side": config.expected_side,
        "expected_qty": str(config.expected_qty),
        "expected_sizing_mode": config.expected_sizing_mode,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
        "labels": list(PAPER_ORDER_RECONCILIATION_LABELS),
        "profile_gate": {
            "status": profile_gate_status,
            "passed": config.profile_gate_passed,
            "detail": config.profile_gate_detail,
        },
        "paper_profile_ready": config.paper_profile_ready,
        "live_url_detected": config.live_url_detected,
        "credentials_redacted": True,
        "order_history_coverage_complete": config.order_history_coverage_complete,
        "account_observation_available": False,
        "positions_observation_available": False,
        "orders_observation_available": False,
        "order_observation_available": False,
        "open_order_count": 0,
        "open_order_symbols": [],
        "open_order_client_order_ids": [],
        "open_order_broker_order_ids": [],
        "open_order_statuses": [],
        "open_order_sides": [],
        "open_order_quantities": [],
        "open_order_filled_quantities": [],
        "spy_position_qty": "",
        "non_spy_positions": [],
        "unexpected_non_spy_position_present": False,
        "unavailable_observations": [],
        "unavailable_reasons": {},
    }


def _observe_broker(
    broker: object,
    config: PaperOrderReconciliationConfig,
    query_factory: OrderQueryFactory,
    redactor: Redactor,
) -> _BrokerObservation:
    context: dict[str, object] = {}
    unavailable: list[str] = []
    unavailable_reasons: dict[str, object] = {}

    try:
        _call_read_only(broker, "get_account")
        context["account_observation_available"] = True
    except Exception as exc:  # pragma: no cover - exercised through fake failures
        unavailable.append("account")
        unavailable_reasons["account"] = _exception_payload(exc, redactor)
        context["account_observation_available"] = False

    try:
        positions = tuple(_call_read_only(broker, "get_positions") or ())
        position_payload = _position_context_payload(positions, config.symbol)
        context.update(position_payload)
        context["positions_observation_available"] = True
    except Exception as exc:  # pragma: no cover - exercised through fake failures
        unavailable.append("positions")
        unavailable_reasons["positions"] = _exception_payload(exc, redactor)
        context.update(
            {
                "positions_observation_available": False,
                "spy_position_qty": "",
                "non_spy_positions": [],
                "unexpected_non_spy_position_present": False,
            }
        )

    source_orders: dict[str, tuple[dict[str, object], ...]] = {}
    source_available: dict[str, bool] = {}
    for source, status_filter in _ORDER_SOURCES:
        try:
            query = query_factory(status_filter)
            rows = tuple(_call_read_only(broker, "get_recent_orders", query) or ())
            source_orders[source] = tuple(
                _order_payload(row, source=source) for row in rows
            )
            source_available[source] = True
        except Exception as exc:  # pragma: no cover - exercised through fake failures
            source_orders[source] = ()
            source_available[source] = False
            unavailable.append(f"{source}_orders")
            unavailable_reasons[f"{source}_orders"] = _exception_payload(exc, redactor)

    open_orders = source_orders.get("open", ())
    open_available = source_available.get("open") is True
    context.update(_open_order_context_payload(open_orders, config.symbol))
    context["orders_observation_available"] = open_available
    context["order_observation_available"] = any(source_available.values())
    context["unavailable_observations"] = _dedupe(unavailable)
    context["unavailable_reasons"] = unavailable_reasons
    return _BrokerObservation(
        context_payload=context,
        source_orders=source_orders,
        source_available=source_available,
    )


def _with_order_classification(
    payload: dict[str, object],
    config: PaperOrderReconciliationConfig,
    observed: _BrokerObservation,
) -> dict[str, object]:
    source_available = observed.source_available
    all_orders = tuple(
        order
        for source, _status_filter in _ORDER_SOURCES
        for order in observed.source_orders.get(source, ())
    )
    related = tuple(order for order in all_orders if _related_order(order, config))
    unique_related = _unique_related_orders(related)
    exact_matches = tuple(
        order for order in unique_related if not _order_mismatches(order, config)
    )
    context_blockers = _context_blockers(payload, config.symbol)

    if not any(source_available.values()):
        return _finalize_payload(
            payload,
            exact_source="unavailable",
            terminal_state="unknown",
            terminal_reason="order_observation_unavailable",
            mismatches=(),
            blockers=(
                "order_observation_unavailable",
                *context_blockers,
            ),
            decision="broker_unavailable",
            next_blocked=True,
            reason="order_observation_unavailable",
        )

    if not unique_related:
        blockers = ["exact_order_not_found", *context_blockers]
        if not config.order_history_coverage_complete:
            blockers.append("order_history_coverage_incomplete")
        return _finalize_payload(
            payload,
            exact_source="not_found",
            terminal_state="unknown",
            terminal_reason="exact_order_not_found",
            mismatches=(),
            blockers=tuple(blockers),
            decision="m376_not_found",
            next_blocked=True,
            reason="exact_order_not_found",
        )

    if len(exact_matches) != 1 or len(unique_related) != 1:
        mismatches = _combined_mismatches(unique_related, config)
        blockers = ["multiple_conflicting_matches", "order_state_ambiguous"]
        if mismatches:
            blockers.append("order_identity_mismatch")
        blockers.extend(context_blockers)
        return _finalize_payload(
            payload,
            order=_best_observed_order(unique_related),
            exact_source="ambiguous",
            terminal_state="unknown",
            terminal_reason="multiple_conflicting_matches",
            mismatches=mismatches,
            blockers=tuple(blockers),
            decision="m376_ambiguous",
            next_blocked=True,
            reason="multiple_conflicting_matches",
        )

    exact_order = exact_matches[0]
    terminal_state, terminal_reason = _terminal_classification(exact_order)
    exact_source = _best_source(exact_order)
    if terminal_state == "unknown":
        blockers = (
            "order_state_ambiguous",
            *context_blockers,
        )
        return _finalize_payload(
            payload,
            order=exact_order,
            exact_source=exact_source,
            terminal_state=terminal_state,
            terminal_reason=terminal_reason,
            mismatches=(),
            blockers=blockers,
            decision="m376_ambiguous",
            next_blocked=True,
            reason=terminal_reason,
        )

    if terminal_state == "nonterminal":
        blockers = (
            "m376_order_nonterminal",
            *context_blockers,
        )
        return _finalize_payload(
            payload,
            order=exact_order,
            exact_source=exact_source,
            terminal_state=terminal_state,
            terminal_reason=terminal_reason,
            mismatches=(),
            blockers=blockers,
            decision="m376_nonterminal_open",
            next_blocked=True,
            reason=terminal_reason,
        )

    decision = (
        "m376_terminal_filled"
        if exact_order.get("status") == "filled"
        else "m376_terminal_nonfilled"
    )
    blockers = tuple(context_blockers)
    return _finalize_payload(
        payload,
        order=exact_order,
        exact_source=exact_source,
        terminal_state=terminal_state,
        terminal_reason=terminal_reason,
        mismatches=(),
        blockers=blockers,
        decision=decision,
        next_blocked=bool(blockers),
        reason=blockers[0] if blockers else terminal_reason,
    )


def _finalize_payload(
    payload: dict[str, object],
    *,
    exact_source: str,
    terminal_state: str,
    terminal_reason: str,
    mismatches: tuple[str, ...],
    blockers: tuple[str, ...],
    decision: str,
    next_blocked: bool,
    reason: str,
    order: Mapping[str, object] | None = None,
) -> dict[str, object]:
    observed_fields = _observed_fields(order)
    exact_found = order is not None and not mismatches and exact_source != "ambiguous"
    return {
        **payload,
        **observed_fields,
        "exact_order_found": exact_found,
        "exact_order_source": exact_source,
        "terminal_state": terminal_state,
        "terminal_reason": terminal_reason,
        "mismatches": list(_dedupe(mismatches)),
        "blockers": list(_dedupe(blockers)),
        "reconciliation_decision": _decision(decision),
        "next_spy_submit_blocked": bool(next_blocked),
        "reason": reason,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
    }


def _observed_fields(order: Mapping[str, object] | None) -> dict[str, object]:
    if order is None:
        return dict(_EMPTY_OBSERVED_FIELDS)
    return {
        "observed_status": str(order.get("status", "")),
        "observed_symbol": str(order.get("symbol", "")),
        "observed_side": str(order.get("side", "")),
        "observed_qty": str(order.get("qty", "")),
        "observed_filled_qty": str(order.get("filled_qty", "")),
        "observed_remaining_qty": str(order.get("remaining_qty", "")),
        "observed_avg_fill_price": str(order.get("avg_fill_price", "")),
        "observed_submitted_at": str(order.get("submitted_at", "")),
        "observed_filled_at": str(order.get("filled_at", "")),
        "observed_canceled_at": str(order.get("canceled_at", "")),
        "observed_expired_at": str(order.get("expired_at", "")),
    }


def _position_context_payload(
    positions: Iterable[object],
    symbol: str,
) -> dict[str, object]:
    spy_qty = ""
    non_spy: list[str] = []
    for position in positions:
        data = _object_data(position)
        position_symbol = _normalized_symbol(_first_present(data, "symbol"))
        if not position_symbol:
            continue
        quantity = _text(
            _first_present(
                data,
                "quantity",
                "qty",
            )
        )
        if position_symbol == symbol:
            spy_qty = quantity
        elif position_symbol not in non_spy:
            non_spy.append(position_symbol)
    return {
        "spy_position_qty": spy_qty,
        "non_spy_positions": non_spy,
        "unexpected_non_spy_position_present": bool(non_spy),
    }


def _open_order_context_payload(
    open_orders: tuple[dict[str, object], ...],
    symbol: str,
) -> dict[str, object]:
    return {
        "open_order_count": len(open_orders),
        "open_order_symbols": _order_values(open_orders, "symbol", unique=True),
        "open_order_client_order_ids": _order_values(open_orders, "client_order_id"),
        "open_order_broker_order_ids": _order_values(open_orders, "order_id"),
        "open_order_statuses": _order_values(open_orders, "status"),
        "open_order_sides": _order_values(open_orders, "side"),
        "open_order_quantities": _order_values(open_orders, "qty"),
        "open_order_filled_quantities": _order_values(
            open_orders,
            "filled_qty",
            drop_empty=True,
        ),
        "spy_open_order_count": sum(
            1 for order in open_orders if order.get("symbol") == symbol
        ),
    }


def _context_blockers(
    payload: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if payload.get("account_observation_available") is not True:
        blockers.append("account_observation_unavailable")
    if payload.get("positions_observation_available") is not True:
        blockers.append("positions_observation_unavailable")
    if payload.get("orders_observation_available") is not True:
        blockers.append("orders_observation_unavailable")
    if payload.get("unexpected_non_spy_position_present") is True:
        blockers.append("unexpected_non_spy_position")
    open_symbols = payload.get("open_order_symbols")
    if isinstance(open_symbols, list) and symbol in open_symbols:
        blockers.append("open_order_present")
    return tuple(blockers)


def _order_payload(value: object, *, source: str) -> dict[str, object]:
    data = _object_data(value)
    qty = _decimal_text(
        _first_decimal(
            data,
            "qty",
            "quantity",
            "order_quantity",
        )
    )
    filled_qty = _decimal_text(
        _first_decimal(data, "filled_qty", "filled_quantity")
    )
    remaining_qty = _decimal_text(
        _first_decimal(data, "remaining_qty", "remaining_quantity")
    )
    if not remaining_qty:
        remaining_qty = _computed_remaining_qty(qty, filled_qty)
    status = _normalized_status(
        _first_present(
            data,
            "normalized_status",
            "status",
            "raw_status",
        )
    )
    return {
        "source": source,
        "sources": (source,),
        "order_id": _text(_first_present(data, "order_id", "id", "broker_order_id")),
        "client_order_id": _text(_first_present(data, "client_order_id")),
        "symbol": _normalized_symbol(_first_present(data, "symbol")),
        "side": _text(_first_present(data, "side")).lower(),
        "qty": qty,
        "filled_qty": filled_qty,
        "remaining_qty": remaining_qty,
        "avg_fill_price": _decimal_text(
            _first_decimal(
                data,
                "filled_avg_price",
                "filled_average_price",
                "avg_fill_price",
                "average_fill_price",
            )
        ),
        "status": status,
        "submitted_at": _time_text(
            _first_present(data, "submitted_at", "created_at")
        ),
        "filled_at": _time_text(_first_present(data, "filled_at")),
        "canceled_at": _time_text(
            _first_present(data, "canceled_at", "cancelled_at")
        ),
        "expired_at": _time_text(_first_present(data, "expired_at")),
    }


def _related_order(
    order: Mapping[str, object],
    config: PaperOrderReconciliationConfig,
) -> bool:
    return (
        order.get("client_order_id") == config.client_order_id
        or order.get("order_id") == config.broker_order_id
    )


def _unique_related_orders(
    orders: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    grouped: dict[tuple[object, ...], dict[str, object]] = {}
    for order in orders:
        signature = _order_signature(order)
        if signature not in grouped:
            grouped[signature] = dict(order)
            continue
        sources = tuple(grouped[signature].get("sources", ()))
        grouped[signature]["sources"] = _dedupe(
            (*sources, str(order.get("source", "")))
        )
    return tuple(grouped.values())


def _order_signature(order: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(
        order.get(field_name, "")
        for field_name in (
            "order_id",
            "client_order_id",
            "symbol",
            "side",
            "qty",
            "filled_qty",
            "remaining_qty",
            "avg_fill_price",
            "status",
            "submitted_at",
            "filled_at",
            "canceled_at",
            "expired_at",
        )
    )


def _order_mismatches(
    order: Mapping[str, object],
    config: PaperOrderReconciliationConfig,
) -> tuple[str, ...]:
    mismatches: list[str] = []
    if order.get("client_order_id") != config.client_order_id:
        mismatches.append("client_order_id_mismatch")
    if order.get("order_id") != config.broker_order_id:
        mismatches.append("broker_order_id_mismatch")
    if order.get("symbol") != config.symbol:
        mismatches.append("symbol_mismatch")
    if order.get("side") != config.expected_side:
        mismatches.append("side_mismatch")
    mismatches.extend(_quantity_mismatches(order, config))
    return tuple(mismatches)


def _quantity_mismatches(
    order: Mapping[str, object],
    config: PaperOrderReconciliationConfig,
) -> tuple[str, ...]:
    observed_qty = _optional_decimal(order.get("qty"))
    if config.expected_sizing_mode == "qty":
        return () if observed_qty == config.expected_qty else ("qty_mismatch",)

    mismatches: list[str] = []
    observed_filled_qty = _optional_decimal(order.get("filled_qty"))
    if observed_filled_qty != config.expected_qty:
        mismatches.append("filled_qty_mismatch")
    if observed_qty is not None and observed_qty != config.expected_qty:
        mismatches.append("qty_mismatch")
    return tuple(mismatches)


def _combined_mismatches(
    orders: tuple[dict[str, object], ...],
    config: PaperOrderReconciliationConfig,
) -> tuple[str, ...]:
    return _dedupe(
        tuple(
            mismatch
            for order in orders
            for mismatch in _order_mismatches(order, config)
        )
    )


def _best_observed_order(
    orders: tuple[dict[str, object], ...],
) -> dict[str, object] | None:
    if not orders:
        return None
    return sorted(orders, key=lambda order: _source_rank(_best_source(order)))[0]


def _best_source(order: Mapping[str, object]) -> str:
    sources = tuple(str(source) for source in order.get("sources", ()))
    if not sources:
        return str(order.get("source", "ambiguous"))
    return sorted(sources, key=_source_rank)[0]


def _source_rank(source: str) -> int:
    return _SOURCE_PRIORITY.get(source, 99)


def _terminal_classification(order: Mapping[str, object]) -> tuple[str, str]:
    status = str(order.get("status", ""))
    qty = _optional_decimal(order.get("qty"))
    filled_qty = _optional_decimal(order.get("filled_qty"))
    remaining_qty = _optional_decimal(order.get("remaining_qty"))
    if not status:
        return "unknown", "order_status_missing"
    if qty is not None and filled_qty is not None and filled_qty > qty:
        return "unknown", "filled_quantity_exceeds_quantity"
    if remaining_qty is not None and remaining_qty < Decimal("0"):
        return "unknown", "remaining_quantity_negative"
    if status in _TERMINAL_STATUSES:
        if status == "filled":
            if qty is not None and filled_qty is not None and filled_qty < qty:
                return "unknown", "filled_status_quantity_conflict"
            return "terminal", "status_filled"
        return "terminal", f"status_{status}_terminal"
    if status in _NONTERMINAL_STATUSES:
        if (
            status not in {"partially_filled"}
            and qty is not None
            and filled_qty is not None
            and qty > Decimal("0")
            and filled_qty >= qty
        ):
            return "unknown", "active_status_filled_quantity_conflict"
        return "nonterminal", f"status_{status}_active"
    return "unknown", "order_status_unknown"


def _call_read_only(
    broker: object,
    method_name: str,
    *args: object,
) -> object:
    method = getattr(broker, method_name, None)
    if method is None or not callable(method):
        raise ValidationError(f"broker read-only method {method_name} is unavailable.")
    return method(*args)


def _object_data(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    names = (
        "avg_fill_price",
        "average_fill_price",
        "broker_order_id",
        "canceled_at",
        "cancelled_at",
        "client_order_id",
        "created_at",
        "expired_at",
        "filled_at",
        "filled_average_price",
        "filled_avg_price",
        "filled_qty",
        "filled_quantity",
        "id",
        "normalized_status",
        "order_id",
        "order_quantity",
        "quantity",
        "qty",
        "raw_status",
        "remaining_qty",
        "remaining_quantity",
        "side",
        "status",
        "submitted_at",
        "symbol",
    )
    return {name: getattr(value, name) for name in names if hasattr(value, name)}


def _first_present(data: Mapping[str, object], *names: str) -> object:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return ""


def _first_decimal(data: Mapping[str, object], *names: str) -> Decimal | None:
    for name in names:
        value = data.get(name)
        decimal_value = _optional_decimal(value)
        if decimal_value is not None:
            return decimal_value
    return None


def _computed_remaining_qty(qty: str, filled_qty: str) -> str:
    quantity = _optional_decimal(qty)
    filled = _optional_decimal(filled_qty)
    if quantity is None or filled is None:
        return ""
    return str(quantity - filled)


def _order_values(
    orders: tuple[Mapping[str, object], ...],
    field_name: str,
    *,
    unique: bool = False,
    drop_empty: bool = False,
) -> list[str]:
    values: list[str] = []
    for order in orders:
        value = str(order.get(field_name, ""))
        if drop_empty and not value:
            continue
        if unique and value in values:
            continue
        values.append(value)
    return values


def _exception_payload(exc: Exception, redactor: Redactor) -> dict[str, object]:
    return {
        "error_type": exc.__class__.__name__,
        "message": redactor(str(exc)),
    }


def _config(value: object) -> PaperOrderReconciliationConfig:
    if type(value) is not PaperOrderReconciliationConfig:
        raise ValidationError("config must be a PaperOrderReconciliationConfig.")
    return value


def _decision(value: str) -> str:
    if value not in PAPER_ORDER_RECONCILIATION_DECISIONS:
        raise ValidationError("reconciliation_decision is invalid.")
    return value


def _normalized_symbol(value: object) -> str:
    text = str(value).strip()
    return symbol_value(text) if text else ""


def _normalized_status(value: object) -> str:
    text = str(value).strip().lower()
    if not text:
        return ""
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def _time_text(value: object) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _decimal_text(value: Decimal | None) -> str:
    return "" if value is None else str(value)


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return decimal_value if decimal_value.is_finite() else None


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _optional_decimal(value)
    if decimal_value is None or decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return decimal_value


def _output_path(value: Path | str) -> Path:
    path = value if isinstance(value, Path) else Path(str(value))
    if str(path).strip() == "":
        raise ValidationError("output_path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _required_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if not text or text != text.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


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


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
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


def _joined(values: object) -> str:
    if not isinstance(values, Iterable) or isinstance(values, str):
        return "none"
    items = [str(value) for value in values if str(value)]
    return ",".join(items) if items else "none"


__all__ = [
    "PAPER_ORDER_RECONCILIATION_DECISIONS",
    "PAPER_ORDER_RECONCILIATION_LABELS",
    "PAPER_ORDER_RECONCILIATION_MILESTONE",
    "PaperOrderReconciliationConfig",
    "PaperOrderReconciliationWriteResult",
    "reconcile_paper_order",
    "render_paper_order_reconciliation_json",
    "render_paper_order_reconciliation_text",
    "write_paper_order_reconciliation_jsonl",
]
