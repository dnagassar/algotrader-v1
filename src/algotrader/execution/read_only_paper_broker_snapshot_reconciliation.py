"""Read-only paper broker snapshot reconciliation for operator review.

This module is pure artifact construction. Broker calls, profile gates, and
credential handling stay at the CLI/broker boundary and feed sanitized
observations into this deterministic record builder.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND",
    "READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID",
    "ReadOnlyPaperBrokerSnapshotObservation",
    "ReadOnlyPaperBrokerSnapshotReconciliationConfig",
    "ReadOnlyPaperBrokerSnapshotReconciliationWriteResult",
    "build_read_only_paper_broker_snapshot_reconciliation",
    "render_read_only_paper_broker_snapshot_reconciliation_json",
    "render_read_only_paper_broker_snapshot_reconciliation_text",
    "write_read_only_paper_broker_snapshot_reconciliation_jsonl",
]


READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND = (
    "paper-lab-read-only-broker-snapshot-reconciliation"
)
READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID = (
    "m403_read_only_paper_broker_snapshot_reconciliation"
)

_MILESTONE = "M403"
_MILESTONE_NAME = (
    "M403 - Separate read-only paper broker snapshot/reconciliation for "
    "operator review"
)
_RECORD_TYPE = "read_only_paper_broker_snapshot_reconciliation"
_DEFAULT_SYMBOL = "SPY"
_SOURCE_READY_REVIEW_STATE = "ready_for_operator_review"
_SOURCE_READY_CYCLE_DECISION = "buy_preview"
_PROFIT_CLAIM = "none"
_BROKER_ACTION_FLAGS = {
    "submit": False,
    "cancel": False,
    "replace": False,
    "close": False,
    "liquidate": False,
    "mutation": False,
}
_LABELS = (
    "paper_lab_only",
    "read_only_broker_observation",
    "operator_review_only",
    "not_live_authorized",
    "profit_claim=none",
)
_FALSE_SAFETY_FIELDS = (
    "paper_execution_authorized",
    "paper_submit_authorized",
    "submit_authorized",
    "broker_mutation_authorized",
    "broker_mutation_allowed",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class ReadOnlyPaperBrokerSnapshotReconciliationConfig:
    """Local artifact inputs for one read-only broker reconciliation record."""

    run_id: str
    source_review_packet_path: Path | str
    run_log: Path | str
    generated_at: str
    symbol: str = _DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "source_review_packet_path",
            _input_jsonl_path(
                self.source_review_packet_path,
                "source_review_packet_path",
            ),
        )
        object.__setattr__(self, "run_log", _output_jsonl_path(self.run_log))
        object.__setattr__(
            self,
            "generated_at",
            _timezone_aware_timestamp(self.generated_at, "generated_at"),
        )


@dataclass(frozen=True, slots=True)
class ReadOnlyPaperBrokerSnapshotObservation:
    """Sanitized broker observations collected by a gated paper command."""

    paper_profile_gate_passed: bool
    profile_gate_detail: str = ""
    live_url_detected: bool = False
    account_observed: bool = False
    positions_observed: bool = False
    orders_observed: bool = False
    recent_orders_observed: bool = False
    account: Mapping[str, object] | None = None
    positions: tuple[Mapping[str, object], ...] = ()
    open_orders: tuple[Mapping[str, object], ...] = ()
    recent_orders: tuple[Mapping[str, object], ...] = ()
    unavailable_observations: tuple[str, ...] = ()
    unavailable_reasons: Mapping[str, object] | None = None
    network_access_attempted: bool = False
    credential_access_attempted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "paper_profile_gate_passed",
            _bool(self.paper_profile_gate_passed, "paper_profile_gate_passed"),
        )
        object.__setattr__(
            self,
            "profile_gate_detail",
            _string(self.profile_gate_detail, "profile_gate_detail"),
        )
        object.__setattr__(
            self,
            "live_url_detected",
            _bool(self.live_url_detected, "live_url_detected"),
        )
        for field_name in (
            "account_observed",
            "positions_observed",
            "orders_observed",
            "recent_orders_observed",
            "network_access_attempted",
            "credential_access_attempted",
        ):
            object.__setattr__(self, field_name, _bool(getattr(self, field_name), field_name))

        if self.account is not None and not isinstance(self.account, Mapping):
            raise ValidationError("account must be a mapping when provided.")
        if self.account_observed and self.account is None:
            raise ValidationError("account must be provided when account_observed is true.")

        object.__setattr__(
            self,
            "account",
            _json_safe(dict(self.account)) if self.account is not None else None,
        )
        object.__setattr__(self, "positions", _mapping_tuple(self.positions, "positions"))
        object.__setattr__(
            self,
            "open_orders",
            _mapping_tuple(self.open_orders, "open_orders"),
        )
        object.__setattr__(
            self,
            "recent_orders",
            _mapping_tuple(self.recent_orders, "recent_orders"),
        )
        object.__setattr__(
            self,
            "unavailable_observations",
            _string_tuple(
                self.unavailable_observations,
                "unavailable_observations",
            ),
        )
        object.__setattr__(
            self,
            "unavailable_reasons",
            _json_safe(dict(self.unavailable_reasons or {})),
        )


@dataclass(frozen=True, slots=True)
class ReadOnlyPaperBrokerSnapshotReconciliationWriteResult:
    """Local JSONL write metadata for the single M403 record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    paper_execution_authorized: bool
    submit_authorized: bool
    broker_mutation_authorized: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_actions_performed: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_jsonl_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if self.newline_terminated is not True:
            raise ValidationError("newline_terminated must be true.")
        for field_name in (
            "paper_execution_authorized",
            "submit_authorized",
            "broker_mutation_authorized",
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_actions_performed",
            "live_authorized",
        ):
            if getattr(self, field_name) is not False:
                raise ValidationError(f"{field_name} must be false.")
        object.__setattr__(
            self,
            "network_access_attempted",
            _bool(self.network_access_attempted, "network_access_attempted"),
        )
        object.__setattr__(
            self,
            "credential_access_attempted",
            _bool(self.credential_access_attempted, "credential_access_attempted"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "paper_execution_authorized": self.paper_execution_authorized,
            "submit_authorized": self.submit_authorized,
            "broker_mutation_authorized": self.broker_mutation_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


def build_read_only_paper_broker_snapshot_reconciliation(
    config: ReadOnlyPaperBrokerSnapshotReconciliationConfig,
    observation: ReadOnlyPaperBrokerSnapshotObservation,
) -> dict[str, object]:
    """Build one conservative M403 read-only broker observation record."""

    checked_config = _config(config)
    checked_observation = _observation(observation)
    source_record, source_record_count, source_record_line = _load_latest_jsonl_record(
        checked_config.source_review_packet_path
    )
    source_review_state = _payload_text(source_record, "review_state")
    source_cycle_decision = _payload_text(source_record, "cycle_decision")
    source_run_id = _payload_text(source_record, "run_id")
    source_symbol = _payload_text(source_record, "symbol")

    account = dict(checked_observation.account or {})
    positions = [dict(position) for position in checked_observation.positions]
    open_orders = [dict(order) for order in checked_observation.open_orders]
    recent_orders = [dict(order) for order in checked_observation.recent_orders]

    position_symbols = _symbols(positions)
    spy_positions = _by_symbol(positions, checked_config.symbol)
    unexpected_non_spy_positions = [
        dict(position)
        for position in positions
        if _symbol_text(position) != checked_config.symbol
    ]
    open_spy_orders = _by_symbol(open_orders, checked_config.symbol)
    recent_spy_orders = _by_symbol(recent_orders, checked_config.symbol)

    source_blockers = _source_blockers(
        source_review_state=source_review_state,
        source_cycle_decision=source_cycle_decision,
        source_symbol=source_symbol,
        requested_symbol=checked_config.symbol,
    )
    observation_blockers = _observation_blockers(checked_observation)
    state, broker_state, next_action = _classify(
        observation=checked_observation,
        source_blockers=source_blockers,
        observation_blockers=observation_blockers,
        open_spy_order_count=len(open_spy_orders),
        unexpected_non_spy_positions=unexpected_non_spy_positions,
    )
    blockers = _dedupe(
        (
            *source_blockers,
            *observation_blockers,
            *(
                ("open_spy_order_present",)
                if open_spy_orders
                else ()
            ),
            *(
                ("unexpected_non_spy_position",)
                if unexpected_non_spy_positions
                else ()
            ),
        )
    )

    broker_action_flags = dict(_BROKER_ACTION_FLAGS)
    payload = {
        "milestone": _MILESTONE,
        "milestone_name": _MILESTONE_NAME,
        "record_type": _RECORD_TYPE,
        "command": READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
        "run_id": checked_config.run_id,
        "symbol": checked_config.symbol,
        "generated_at": checked_config.generated_at,
        "source_review_packet_path": str(checked_config.source_review_packet_path),
        "source_review_packet_record_count": source_record_count,
        "source_review_packet_record_line": source_record_line,
        "source_review_run_id": source_run_id,
        "source_review_symbol": source_symbol,
        "source_review_state": source_review_state,
        "source_cycle_decision": source_cycle_decision,
        "paper_profile_gate_passed": checked_observation.paper_profile_gate_passed,
        "paper_profile_gate_detail": checked_observation.profile_gate_detail,
        "paper_profile_ready": checked_observation.paper_profile_gate_passed,
        "profile_gate": {
            "passed": checked_observation.paper_profile_gate_passed,
            "status": (
                "passed"
                if checked_observation.paper_profile_gate_passed
                else "blocked"
            ),
            "detail": checked_observation.profile_gate_detail,
            "live_url_detected": checked_observation.live_url_detected,
        },
        "live_url_detected": checked_observation.live_url_detected,
        "account_observed": checked_observation.account_observed,
        "positions_observed": checked_observation.positions_observed,
        "orders_observed": checked_observation.orders_observed,
        "open_orders_observed": checked_observation.orders_observed,
        "recent_orders_observed": checked_observation.recent_orders_observed,
        "account": account if checked_observation.account_observed else None,
        "positions": positions,
        "open_orders": open_orders,
        "recent_orders": recent_orders,
        "cash": _text(account.get("cash")),
        "buying_power": _text(account.get("buying_power")),
        "currency": _text(account.get("currency")),
        "position_count": len(positions),
        "position_symbols": position_symbols,
        "spy_position_present": bool(spy_positions),
        "spy_position_qty": _position_quantity_text(spy_positions),
        "unexpected_non_spy_positions": unexpected_non_spy_positions,
        "open_order_count": len(open_orders),
        "open_order_symbols": _symbols(open_orders),
        "open_spy_orders": open_spy_orders,
        "open_spy_order_count": len(open_spy_orders),
        "recent_order_count": len(recent_orders),
        "recent_order_symbols": _symbols(recent_orders),
        "recent_spy_orders": recent_spy_orders,
        "recent_spy_order_count": len(recent_spy_orders),
        "broker_observation_state": broker_state,
        "reconciliation_state": state,
        "blockers": list(blockers),
        "next_action": next_action,
        "unavailable_observations": list(checked_observation.unavailable_observations),
        "unavailable_reasons": dict(checked_observation.unavailable_reasons or {}),
        "paper_lab_only": True,
        "operator_review_only": True,
        "read_only_broker_observation": True,
        "labels": list(_LABELS),
        "profit_claim": _PROFIT_CLAIM,
        "not_live_authorized": True,
        "paper_execution_authorized": False,
        "paper_submit_authorized": False,
        "submit_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_action_flags": broker_action_flags,
        "network_access_attempted": checked_observation.network_access_attempted,
        "credential_access_attempted": (
            checked_observation.credential_access_attempted
        ),
        "live_authorized": False,
        "forbidden_actions": _forbidden_actions(),
        "next_forbidden_action": _forbidden_actions(),
    }
    _validate_false_safety_fields(payload)
    return payload


def render_read_only_paper_broker_snapshot_reconciliation_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_read_only_paper_broker_snapshot_reconciliation_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing broker snapshot summary."""

    return "\n".join(
        (
            "Read-only paper broker snapshot reconciliation",
            f"milestone: {payload.get('milestone', '')}",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"source_review_state: {payload.get('source_review_state', '')}",
            f"source_cycle_decision: {payload.get('source_cycle_decision', '')}",
            "paper_profile_gate_passed: "
            f"{_bool_text(payload.get('paper_profile_gate_passed'))}",
            f"account_observed: {_bool_text(payload.get('account_observed'))}",
            f"positions_observed: {_bool_text(payload.get('positions_observed'))}",
            f"orders_observed: {_bool_text(payload.get('orders_observed'))}",
            "recent_orders_observed: "
            f"{_bool_text(payload.get('recent_orders_observed'))}",
            "cash / buying_power / currency: "
            f"{_none_text(payload.get('cash'))} / "
            f"{_none_text(payload.get('buying_power'))} / "
            f"{_none_text(payload.get('currency'))}",
            f"position_symbols: {_joined(_string_tuple(payload.get('position_symbols'), 'position_symbols'))}",
            "SPY position present / qty: "
            f"{_bool_text(payload.get('spy_position_present'))} / "
            f"{_none_text(payload.get('spy_position_qty'))}",
            "unexpected_non_spy_positions: "
            f"{_joined(_position_symbol_tuple(payload.get('unexpected_non_spy_positions')))}",
            f"open_order_count: {_none_text(payload.get('open_order_count'))}",
            f"open_spy_order_count: {_none_text(payload.get('open_spy_order_count'))}",
            f"recent_order_count: {_none_text(payload.get('recent_order_count'))}",
            f"recent_spy_order_count: {_none_text(payload.get('recent_spy_order_count'))}",
            f"broker_observation_state: {payload.get('broker_observation_state', '')}",
            f"reconciliation_state: {payload.get('reconciliation_state', '')}",
            f"blockers: {_joined(_string_tuple(payload.get('blockers'), 'blockers'))}",
            f"next_action: {payload.get('next_action', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_mutation_authorized: "
            f"{_bool_text(payload.get('broker_mutation_authorized'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_read_only_paper_broker_snapshot_reconciliation_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> ReadOnlyPaperBrokerSnapshotReconciliationWriteResult:
    """Write exactly one M403 JSONL record, replacing prior contents."""

    path = _output_jsonl_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    checked_payload = dict(payload)
    _validate_false_safety_fields(checked_payload)
    line = render_read_only_paper_broker_snapshot_reconciliation_json(
        checked_payload
    ) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return ReadOnlyPaperBrokerSnapshotReconciliationWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        paper_execution_authorized=False,
        submit_authorized=False,
        broker_mutation_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=_bool(
            checked_payload.get("network_access_attempted"),
            "network_access_attempted",
        ),
        credential_access_attempted=_bool(
            checked_payload.get("credential_access_attempted"),
            "credential_access_attempted",
        ),
        live_authorized=False,
    )


def _load_latest_jsonl_record(path: Path) -> tuple[Mapping[str, object], int, int]:
    if not path.exists() or not path.is_file():
        raise ValidationError(
            "source_review_packet_path must reference an existing JSONL file."
        )

    records: list[tuple[int, Mapping[str, object]]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                "source_review_packet_path contains invalid JSON at "
                f"line {line_number}."
            ) from exc
        if not isinstance(parsed, Mapping):
            raise ValidationError(
                f"source_review_packet_path line {line_number} must contain a JSON object."
            )
        records.append((line_number, parsed))

    if not records:
        raise ValidationError(
            "source_review_packet_path must contain at least one JSON object."
        )

    selected_line, selected_record = records[-1]
    return selected_record, len(records), selected_line


def _source_blockers(
    *,
    source_review_state: str,
    source_cycle_decision: str,
    source_symbol: str,
    requested_symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if source_review_state != _SOURCE_READY_REVIEW_STATE:
        blockers.append("source_review_state_not_ready_for_operator_review")
    if source_cycle_decision != _SOURCE_READY_CYCLE_DECISION:
        blockers.append("source_cycle_decision_not_buy_preview")
    if source_symbol and source_symbol != requested_symbol:
        blockers.append("source_symbol_mismatch")
    if requested_symbol != _DEFAULT_SYMBOL:
        blockers.append("symbol_not_spy")
    if source_symbol and source_symbol != _DEFAULT_SYMBOL:
        blockers.append("source_symbol_not_spy")
    return _dedupe(tuple(blockers))


def _observation_blockers(
    observation: ReadOnlyPaperBrokerSnapshotObservation,
) -> tuple[str, ...]:
    if not observation.paper_profile_gate_passed:
        return ("paper_profile_gate_failed",)

    unavailable = list(observation.unavailable_observations)
    if (
        not observation.account_observed
        and not observation.positions_observed
        and not observation.orders_observed
        and not observation.recent_orders_observed
    ):
        return _dedupe(("broker_observation_unavailable", *unavailable))

    blockers: list[str] = []
    if not observation.account_observed:
        blockers.append("account_observation_unavailable")
    if not observation.positions_observed:
        blockers.append("positions_observation_unavailable")
    if not observation.orders_observed:
        blockers.append("open_orders_observation_unavailable")
    if not observation.recent_orders_observed:
        blockers.append("recent_orders_observation_unavailable")
    blockers.extend(unavailable)
    return _dedupe(tuple(blockers))


def _classify(
    *,
    observation: ReadOnlyPaperBrokerSnapshotObservation,
    source_blockers: tuple[str, ...],
    observation_blockers: tuple[str, ...],
    open_spy_order_count: int,
    unexpected_non_spy_positions: list[dict[str, object]],
) -> tuple[str, str, str]:
    if not observation.paper_profile_gate_passed:
        return (
            "blocked_profile_gate_failed",
            "profile_gate_failed",
            "fix_paper_profile_or_credentials_then_rerun_read_only_snapshot_reconciliation",
        )
    if "broker_observation_unavailable" in observation_blockers:
        return (
            "blocked_broker_unavailable",
            "broker_unavailable",
            "resolve_broker_access_then_rerun_read_only_snapshot_reconciliation",
        )
    if source_blockers or observation_blockers:
        return (
            "blocked_observation_incomplete",
            "observation_incomplete",
            "rerun_read_only_snapshot_reconciliation_after_resolving_missing_observations",
        )
    if open_spy_order_count:
        return (
            "blocked_open_order_present",
            "observed",
            "operator_review_open_spy_orders_without_canceling_before_any_submit",
        )
    if unexpected_non_spy_positions:
        return (
            "blocked_unexpected_non_spy_position",
            "observed",
            "operator_review_unexpected_non_spy_positions_without_closing_before_any_submit",
        )
    return (
        "ready_for_operator_review",
        "observed",
        "operator_may_consider_separate_paper_submit_milestone_with_explicit_approval",
    )


def _by_symbol(
    rows: Iterable[Mapping[str, object]],
    symbol: str,
) -> list[dict[str, object]]:
    return [dict(row) for row in rows if _symbol_text(row) == symbol]


def _symbols(rows: Iterable[Mapping[str, object]]) -> list[str]:
    return sorted(
        {
            symbol
            for row in rows
            if (symbol := _symbol_text(row))
        }
    )


def _symbol_text(row: Mapping[str, object]) -> str:
    return _text(row.get("symbol")).strip().upper()


def _position_quantity_text(positions: list[dict[str, object]]) -> str:
    if not positions:
        return "0"
    return _text(
        positions[0].get("quantity", positions[0].get("qty", ""))
    )


def _position_symbol_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    symbols: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            symbol = _symbol_text(item)
            if symbol:
                symbols.append(symbol)
    return tuple(symbols)


def _forbidden_actions() -> list[str]:
    return [
        "broker_mutation_from_read_only_paper_broker_snapshot_reconciliation",
        "paper_submit_from_read_only_paper_broker_snapshot_reconciliation",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_snapshot_reconciliation",
    ]


def _validate_false_safety_fields(payload: Mapping[str, object]) -> None:
    for field_name in _FALSE_SAFETY_FIELDS:
        if payload.get(field_name) is not False:
            raise ValidationError(f"{field_name} must be false.")
    flags = payload.get("broker_action_flags")
    if not isinstance(flags, Mapping):
        raise ValidationError("broker_action_flags must be present.")
    for action in ("submit", "cancel", "replace", "close", "liquidate", "mutation"):
        if flags.get(action) is not False:
            raise ValidationError(f"broker_action_flags.{action} must be false.")


def _config(value: object) -> ReadOnlyPaperBrokerSnapshotReconciliationConfig:
    if type(value) is not ReadOnlyPaperBrokerSnapshotReconciliationConfig:
        raise ValidationError(
            "config must be a ReadOnlyPaperBrokerSnapshotReconciliationConfig."
        )
    return value


def _observation(value: object) -> ReadOnlyPaperBrokerSnapshotObservation:
    if type(value) is not ReadOnlyPaperBrokerSnapshotObservation:
        raise ValidationError(
            "observation must be a ReadOnlyPaperBrokerSnapshotObservation."
        )
    return value


def _input_jsonl_path(value: object, field_name: str) -> Path:
    path = _local_jsonl_path(value, field_name)
    if not path.exists() or not path.is_file():
        raise ValidationError(f"{field_name} must reference an existing JSONL file.")
    return path


def _output_jsonl_path(value: object) -> Path:
    path = _local_jsonl_path(value, "run_log")
    if path.exists() and path.is_dir():
        raise ValidationError("run_log must not be a directory.")
    return path


def _local_jsonl_path(value: object, field_name: str) -> Path:
    path = _required_path(value, field_name)
    if type(value) is str and "://" in value:
        raise ValidationError(f"{field_name} must be a local JSONL path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must reference a JSONL file.")
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


def _timezone_aware_timestamp(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return text


def _payload_text(payload: Mapping[str, object], field_name: str) -> str:
    return _text(payload.get(field_name))


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be bool.")
    return value


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        raise ValidationError(f"{field_name} must be a sequence of strings.")
    return tuple(str(item) for item in value if str(item))


def _mapping_tuple(
    value: object,
    field_name: str,
) -> tuple[dict[str, object], ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        raise ValidationError(f"{field_name} must be a sequence of mappings.")
    rows: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValidationError(f"{field_name} must contain only mappings.")
        rows.append(_json_safe(dict(item)))
    return tuple(rows)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_json_safe(item) for item in value]
    if type(value) is list:
        return [_json_safe(item) for item in value]
    return value


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _none_text(value: object) -> str:
    if value in (None, ""):
        return "unknown"
    return str(value)


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
