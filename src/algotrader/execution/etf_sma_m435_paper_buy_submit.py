"""M435 operator-authorized tiny SPY paper buy submit milestone."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaOrderRequest, AlpacaRecentOrderQuery
from algotrader.execution.alpaca_mapper import broker_order_result_receipt_metadata
from algotrader.execution.order_journal import (
    OrderReservation,
    RuntimeLeaseResult,
    SqliteOrderJournal,
)
from algotrader.execution.paper_lab_snapshot import (
    account_observation_payload,
    order_observation_payloads,
    position_observation_payloads,
    position_symbols,
    recent_order_query_payload,
)
from algotrader.risk.state import RiskVerdict

M435_APPROVAL_PHRASE = "APPROVE_M435_TINY_SPY_PAPER_BUY_SUBMIT"
M435_CLIENT_ORDER_ID = "paper-order-m435_spy_etf_sma_tiny_buy_submit"
M435_DEFAULT_RUN_ID = "m435_tiny_spy_paper_buy_submit"
M435_DEFAULT_SOURCE_M434_ARTIFACT_PATH = (
    "runs/paper_lab/m434_offline_paper_buy_submit_approval_packet.jsonl"
)
M435_DEFAULT_OUTPUT_PATH = "runs/paper_lab/m435_tiny_spy_paper_buy_submit.jsonl"
M435_EXECUTION_PLAN_ID = "m435_tiny_spy_paper_buy_submit_plan_v1"
M435_COMMAND = "etf-sma-m435-paper-buy-submit"
M435_LABELS = (
    "paper_lab_only",
    "m435_operator_authorized_tiny_spy_paper_buy_submit",
    "not_live_authorized",
    "profit_claim=none",
)

_M434_RECORD_TYPE = "etf_sma_m434_offline_paper_buy_submit_approval_packet"
_M434_READY_APPROVAL_DECISION = "ready_for_explicit_operator_authorization"
_M434_READY_NEXT_MILESTONE = "M435_operator_authorized_tiny_spy_paper_buy_submit"
_MILESTONE = "M435"
_SYMBOL = "SPY"
_ASSET_CLASS = "equity"
_SIDE = "buy"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_MAX_NOTIONAL = Decimal("25.00")
_PROFIT_CLAIM = "none"
_MARKET_SESSION_MAX_AGE = timedelta(minutes=15)
_PRE_SUBMIT_RECONCILIATION_MAX_AGE = timedelta(minutes=5)
_FUTURE_TOLERANCE = timedelta(seconds=60)
_LEASE_NAME = "m435-paper-buy-submit"
_LEASE_TTL_SECONDS = 300
_RECONCILIATION_OBSERVED_AT_UNSET = object()
_M434_FALSE_FIELDS = (
    "submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_read_only",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class M435EquitySessionStatus:
    """Operator-provided regular equity session status evidence."""

    status: str
    source: str = ""
    observed_at: str = ""

    def __post_init__(self) -> None:
        status = str(self.status).strip().lower()
        if status not in {"open", "closed", "unavailable"}:
            raise ValidationError("equity session status is invalid.")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "source", str(self.source).strip())
        object.__setattr__(self, "observed_at", str(self.observed_at).strip())

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    def to_dict(self) -> dict[str, object]:
        return {
            "is_open": self.is_open,
            "observed_at": self.observed_at,
            "source": self.source,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class M435Gate:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {"detail": self.detail, "passed": self.passed}


def run_m435_tiny_spy_paper_buy_submit(
    *,
    source_m434_artifact_path: str | Path = M435_DEFAULT_SOURCE_M434_ARTIFACT_PATH,
    output_artifact_path: str | Path | None = M435_DEFAULT_OUTPUT_PATH,
    run_id: str = M435_DEFAULT_RUN_ID,
    operator_approval: str = "",
    equity_session_status: M435EquitySessionStatus,
    paper_profile_gate_passed: bool,
    evaluated_at: str | datetime = "",
    pre_submit_reconciliation_observed_at: object = (
        _RECONCILIATION_OBSERVED_AT_UNSET
    ),
    market_session_max_age: timedelta = _MARKET_SESSION_MAX_AGE,
    pre_submit_reconciliation_max_age: timedelta = (
        _PRE_SUBMIT_RECONCILIATION_MAX_AGE
    ),
    future_tolerance: timedelta = _FUTURE_TOLERANCE,
    paper_profile_gate_detail: str = "",
    live_url_detected: bool = False,
    halt_gate_passed: bool = True,
    halt_gate_detail: str = "halt_not_set",
    reconciliation_clock: Callable[[], object] | None = None,
    broker_factory: Callable[[], Any] | None = None,
    redactor: Callable[[str], str] | None = None,
) -> dict[str, object]:
    """Validate M435 gates and call the paper broker at most once."""

    source_path = _path(source_m434_artifact_path, "source_m434_artifact_path")
    output_path = (
        None
        if output_artifact_path is None
        else _path(output_artifact_path, "output_artifact_path")
    )
    journal_path = _m435_order_journal_path(output_path=output_path)
    checked_run_id = _required_string(run_id, "run_id")
    checked_session = _session_status(equity_session_status)
    checked_market_session_max_age = _nonnegative_timedelta(
        market_session_max_age,
        "market_session_max_age",
    )
    checked_pre_submit_reconciliation_max_age = _nonnegative_timedelta(
        pre_submit_reconciliation_max_age,
        "pre_submit_reconciliation_max_age",
    )
    checked_future_tolerance = _nonnegative_timedelta(
        future_tolerance,
        "future_tolerance",
    )
    evaluation_clock, evaluation_clock_blockers = _evaluation_clock(evaluated_at)
    sanitize = redactor or (lambda value: value)
    operator_approval_present = operator_approval == M435_APPROVAL_PHRASE

    source_record, source_blockers = _load_and_validate_m434_source(source_path)
    prior_artifact_blockers = _existing_m435_submit_blockers(output_path)
    market_session_blockers = _market_session_blockers(
        checked_session,
        evaluated_at_utc=evaluation_clock,
        evaluated_at_blockers=evaluation_clock_blockers,
        max_age=checked_market_session_max_age,
        future_tolerance=checked_future_tolerance,
    )
    initial_gates = _initial_gates(
        operator_approval_present=operator_approval_present,
        paper_profile_gate_passed=paper_profile_gate_passed,
        paper_profile_gate_detail=paper_profile_gate_detail,
        live_url_detected=live_url_detected,
        halt_gate_passed=halt_gate_passed,
        halt_gate_detail=halt_gate_detail,
        market_session_blockers=market_session_blockers,
        source_blockers=source_blockers,
        prior_artifact_blockers=prior_artifact_blockers,
    )
    blockers = _gate_blockers(initial_gates)
    payload = _base_payload(
        run_id=checked_run_id,
        evaluated_at=_timestamp_text(evaluation_clock, evaluated_at),
        source_path=source_path,
        source_record=source_record,
        output_path=output_path,
        order_journal_path=journal_path,
        operator_approval_present=operator_approval_present,
        equity_session_status=checked_session,
        live_url_detected=live_url_detected,
        gates=initial_gates,
        blockers=blockers,
    )
    if blockers:
        return _finalize_blocked_payload(payload, blockers)

    if broker_factory is None:
        blockers = ("broker_factory_missing",)
        return _finalize_blocked_payload(
            {**payload, "blockers": list(blockers)},
            blockers,
        )

    try:
        broker = broker_factory()
    except Exception as exc:  # pragma: no cover - exercised by fakes in tests
        message = sanitize(str(exc))
        return _finalize_blocked_payload(
            {
                **payload,
                "broker_error": True,
                "error": "broker_factory_failed",
                "message": message,
                "redacted_exception_message": message,
            },
            ("broker_factory_failed",),
        )

    pre_reconciliation = _observe_reconciliation(
        broker,
        phase="pre_submit",
        observed_at=_reconciliation_observed_at(
            reconciliation_clock=reconciliation_clock
        ),
        redactor=sanitize,
    )
    fresh_blockers = _dedupe(
        (
            *_fresh_reconciliation_blockers(
                pre_reconciliation,
                evaluated_at_utc=evaluation_clock,
                evaluated_at_blockers=evaluation_clock_blockers,
                max_age=checked_pre_submit_reconciliation_max_age,
                future_tolerance=checked_future_tolerance,
            ),
            *_explicit_pre_submit_reconciliation_blockers(
                pre_submit_reconciliation_observed_at,
                evaluated_at_utc=evaluation_clock,
                evaluated_at_blockers=evaluation_clock_blockers,
                max_age=checked_pre_submit_reconciliation_max_age,
                future_tolerance=checked_future_tolerance,
            ),
        )
    )
    payload = {
        **payload,
        "blockers": list(fresh_blockers),
        "error": _error_from_blockers(fresh_blockers),
        "pre_submit_reconciliation": pre_reconciliation,
        "pre_submit_snapshot": pre_reconciliation,
    }
    if fresh_blockers:
        return _finalize_blocked_payload(payload, fresh_blockers)

    if evaluation_clock is None or journal_path is None:
        blockers = ("durable_submit_journal_unavailable",)
        return _finalize_blocked_payload(
            {
                **payload,
                "blockers": list(blockers),
                "order_journal_error": "journal_path_or_evaluation_clock_missing",
            },
            blockers,
        )

    journal, lease, claim_status, claim_blockers = _claim_durable_submit(
        journal_path=journal_path,
        run_id=checked_run_id,
        occurred_at=evaluation_clock,
    )
    payload = {**payload, **claim_status, "blockers": list(claim_blockers)}
    if claim_blockers or journal is None or lease is None:
        return _finalize_blocked_payload(payload, claim_blockers)

    try:
        submit_payload = _submit_once(
            broker,
            payload,
            redactor=sanitize,
            order_journal=journal,
            occurred_at=evaluation_clock,
        )
    finally:
        try:
            lease_released = journal.release_runtime_lease(
                lease_name=_LEASE_NAME,
                owner_run_id=checked_run_id,
                lease_token=lease.lease_token,
            )
        except Exception:
            lease_released = False
    submit_payload = {
        **submit_payload,
        "order_journal_lease_released": lease_released,
    }
    if submit_payload.get("submit_call_count") == 1:
        submit_payload = {
            **submit_payload,
            "post_submit_reconciliation": _observe_reconciliation(
                broker,
                phase="post_submit",
                observed_at=_reconciliation_observed_at(
                    reconciliation_clock=reconciliation_clock
                ),
                redactor=sanitize,
            ),
        }
        submit_payload = _attach_matching_post_submit_order(submit_payload)
    return _finalize_submit_payload(submit_payload)


def render_m435_paper_buy_submit_json(payload: Mapping[str, object]) -> str:
    """Render one deterministic JSONL record."""

    return json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
    )


def render_m435_paper_buy_submit_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable M435 summary."""

    blockers = _string_items(payload.get("blockers"))
    pre_reconciliation = _mapping_or_empty(payload.get("pre_submit_reconciliation"))
    post_reconciliation = _mapping_or_empty(payload.get("post_submit_reconciliation"))
    session = _mapping_or_empty(payload.get("market_session"))
    return "\n".join(
        [
            "M435 tiny SPY paper buy submit",
            f"run_id: {_text(payload.get('run_id'))}",
            f"evaluated_at: {_display_timestamp(payload.get('evaluated_at')) or 'none'}",
            f"source_m434_artifact: {_text(payload.get('source_m434_artifact'))}",
            "operator_approval_present: "
            f"{_bool_text(payload.get('operator_approval_present'))}",
            f"market_session_status: {_text(session.get('status')) or 'unavailable'}",
            f"market_session_source: {_text(session.get('source')) or 'none'}",
            "market_session_observed_at: "
            f"{_display_timestamp(session.get('observed_at')) or 'none'}",
            f"ok: {_bool_text(payload.get('ok'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"broker_action_performed: {_bool_text(payload.get('broker_action_performed'))}",
            f"submit_call_count: {_text(payload.get('submit_call_count'))}",
            f"client_order_id: {_text(payload.get('client_order_id'))}",
            f"broker_order_id: {_text(payload.get('broker_order_id')) or 'none'}",
            f"broker_status: {_text(payload.get('broker_status')) or 'none'}",
            "pre_submit_reconciliation_observed_at: "
            f"{_display_timestamp(pre_reconciliation.get('observed_at')) or 'none'}",
            "post_submit_reconciliation_observed_at: "
            f"{_display_timestamp(post_reconciliation.get('observed_at')) or 'none'}",
            f"cash: {_text(pre_reconciliation.get('cash')) or 'none'}",
            f"currency: {_text(pre_reconciliation.get('currency')) or 'none'}",
            f"position_count: {_text(pre_reconciliation.get('position_count')) or '0'}",
            "open_order_count: "
            f"{_text(pre_reconciliation.get('open_order_count')) or '0'}",
            f"blockers: {', '.join(blockers) if blockers else 'none'}",
            "profit_claim: none",
            "live_authorized: false",
        ]
    )


def write_m435_paper_buy_submit_artifact(
    payload: Mapping[str, object],
    output_path: str | Path = M435_DEFAULT_OUTPUT_PATH,
) -> dict[str, object]:
    """Append one M435 JSONL evidence record to the ignored run artifact."""

    path = _path(output_path, "output_path")
    line = render_m435_paper_buy_submit_json(payload) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
    except OSError as exc:
        raise ValidationError(
            f"M435 paper buy submit artifact write failed: {exc.__class__.__name__}."
        ) from None
    return {
        "bytes_written": len(line.encode("utf-8")),
        "newline_terminated": True,
        "output_path": str(path),
        "record_count": 1,
    }


def _base_payload(
    *,
    run_id: str,
    evaluated_at: str,
    source_path: Path,
    source_record: Mapping[str, object] | None,
    output_path: Path | None,
    order_journal_path: Path | None,
    operator_approval_present: bool,
    equity_session_status: M435EquitySessionStatus,
    live_url_detected: bool,
    gates: Sequence[M435Gate],
    blockers: Sequence[str],
) -> dict[str, object]:
    return {
        "accepted": None,
        "blockers": list(blockers),
        "broker_action_performed": False,
        "broker_error": False,
        "broker_order_id": "",
        "broker_status": "",
        "client_order_id": M435_CLIENT_ORDER_ID,
        "command": M435_COMMAND,
        "credentials_redacted": True,
        "error": _error_from_blockers(blockers),
        "evaluated_at": evaluated_at,
        "filled_average_price": "",
        "filled_quantity": "",
        "gates": {gate.name: gate.to_dict() for gate in gates},
        "labels": list(M435_LABELS),
        "live_authorized": False,
        "live_url_detected": live_url_detected,
        "market_session": equity_session_status.to_dict(),
        "message": "",
        "milestone": _MILESTONE,
        "mutated": False,
        "not_live_authorized": True,
        "operator_approval_present": operator_approval_present,
        "order_journal_claimed": False,
        "order_journal_error": "",
        "order_journal_lease_acquired": False,
        "order_journal_lease_released": False,
        "order_journal_path": (
            "" if order_journal_path is None else str(order_journal_path)
        ),
        "order_journal_reservation_status": "not_attempted",
        "order_journal_state": "",
        "order_intent": _order_intent(),
        "paper_lab_only": True,
        "paper_only": True,
        "post_submit_reconciliation": None,
        "pre_submit_reconciliation": None,
        "pre_submit_snapshot": None,
        "profit_claim": _PROFIT_CLAIM,
        "redaction": "credentials_redacted",
        "required_single_attempt_submit": True,
        "run_id": run_id,
        "source_m433_artifact": _source_value(source_record, "source_m433_artifact"),
        "source_m433_readiness_decision": _source_value(
            source_record,
            "source_m433_readiness_decision",
        ),
        "source_m434_approval_decision": _source_value(
            source_record,
            "approval_decision",
        ),
        "source_m434_artifact": str(source_path),
        "source_m434_next_required_milestone": _source_value(
            source_record,
            "next_required_milestone",
        ),
        "submit_authorized": False,
        "submitted": False,
        "submitted_at": "",
        "submit_call_count": 0,
        "target_output_artifact": "" if output_path is None else str(output_path),
    }


def _initial_gates(
    *,
    operator_approval_present: bool,
    paper_profile_gate_passed: bool,
    paper_profile_gate_detail: str,
    live_url_detected: bool,
    halt_gate_passed: bool,
    halt_gate_detail: str,
    market_session_blockers: Sequence[str],
    source_blockers: Sequence[str],
    prior_artifact_blockers: Sequence[str],
) -> tuple[M435Gate, ...]:
    return (
        M435Gate(
            "m434_source_gate",
            not source_blockers,
            "m434_source_ready" if not source_blockers else ",".join(source_blockers),
        ),
        M435Gate(
            "operator_approval_gate",
            operator_approval_present,
            (
                "exact_m435_operator_approval_present"
                if operator_approval_present
                else "operator_approval_phrase_mismatch"
            ),
        ),
        M435Gate(
            "paper_profile_gate",
            paper_profile_gate_passed,
            paper_profile_gate_detail
            or (
                "paper_profile_ready"
                if paper_profile_gate_passed
                else "paper_profile_required"
            ),
        ),
        M435Gate(
            "live_url_gate",
            not live_url_detected,
            "paper_url_confirmed" if not live_url_detected else "live_url_detected",
        ),
        M435Gate(
            "halt_gate",
            halt_gate_passed,
            halt_gate_detail if halt_gate_passed else "ALGOTRADER_PAPER_HALT=1",
        ),
        M435Gate(
            "market_session_gate",
            not market_session_blockers,
            (
                "market_session_fresh_open"
                if not market_session_blockers
                else ",".join(market_session_blockers)
            ),
        ),
        M435Gate(
            "prior_m435_artifact_gate",
            not prior_artifact_blockers,
            (
                "no_prior_m435_submit_detected"
                if not prior_artifact_blockers
                else ",".join(prior_artifact_blockers)
            ),
        ),
    )


def _gate_blockers(gates: Sequence[M435Gate]) -> tuple[str, ...]:
    blockers: list[str] = []
    for gate in gates:
        if not gate.passed:
            blockers.append(f"{gate.name}_failed")
            blockers.extend(_split_blocker_detail(gate.detail))
    return _dedupe(blockers)


def _market_session_blockers(
    session_status: M435EquitySessionStatus,
    *,
    evaluated_at_utc: datetime | None,
    evaluated_at_blockers: Sequence[str],
    max_age: timedelta,
    future_tolerance: timedelta,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if session_status.status != "open":
        blockers.append("market_session_not_open")
    if session_status.status == "open" and not session_status.source:
        blockers.append("market_session_source_missing")
    blockers.extend(
        _freshness_blockers(
            session_status.observed_at,
            evaluated_at_utc=evaluated_at_utc,
            evaluated_at_blockers=evaluated_at_blockers,
            missing_blocker="market_session_observed_at_missing",
            timezone_naive_blocker="market_session_observed_at_timezone_naive",
            invalid_blocker="market_session_observed_at_invalid",
            stale_blocker="market_session_status_stale",
            future_blocker="market_session_status_future_dated",
            max_age=max_age,
            future_tolerance=future_tolerance,
        )
    )
    return _dedupe(blockers)


def _freshness_blockers(
    observed_at: object,
    *,
    evaluated_at_utc: datetime | None,
    evaluated_at_blockers: Sequence[str],
    missing_blocker: str,
    timezone_naive_blocker: str,
    invalid_blocker: str,
    stale_blocker: str,
    future_blocker: str,
    max_age: timedelta,
    future_tolerance: timedelta,
) -> tuple[str, ...]:
    observed_at_utc, observed_at_blockers = _timestamp_to_utc(
        observed_at,
        missing_blocker=missing_blocker,
        timezone_naive_blocker=timezone_naive_blocker,
        invalid_blocker=invalid_blocker,
    )
    if observed_at_blockers:
        return observed_at_blockers
    if evaluated_at_blockers:
        return tuple(evaluated_at_blockers)
    if observed_at_utc is None or evaluated_at_utc is None:
        return ()
    if observed_at_utc - evaluated_at_utc > future_tolerance:
        return (future_blocker,)
    if evaluated_at_utc - observed_at_utc > max_age:
        return (stale_blocker,)
    return ()


def _fresh_reconciliation_blockers(
    reconciliation: Mapping[str, object],
    *,
    evaluated_at_utc: datetime | None,
    evaluated_at_blockers: Sequence[str],
    max_age: timedelta,
    future_tolerance: timedelta,
) -> tuple[str, ...]:
    blockers: list[str] = list(
        _freshness_blockers(
            reconciliation.get("observed_at"),
            evaluated_at_utc=evaluated_at_utc,
            evaluated_at_blockers=evaluated_at_blockers,
            missing_blocker="pre_submit_reconciliation_observed_at_missing",
            timezone_naive_blocker=(
                "pre_submit_reconciliation_observed_at_timezone_naive"
            ),
            invalid_blocker="pre_submit_reconciliation_observed_at_invalid",
            stale_blocker="pre_submit_reconciliation_stale",
            future_blocker="pre_submit_reconciliation_future_dated",
            max_age=max_age,
            future_tolerance=future_tolerance,
        )
    )
    _append_if(
        blockers,
        reconciliation.get("account_observation_available") is not True,
        "fresh_account_observation_unavailable",
    )
    _append_if(
        blockers,
        reconciliation.get("positions_observation_available") is not True,
        "fresh_positions_observation_unavailable",
    )
    _append_if(
        blockers,
        reconciliation.get("orders_observation_available") is not True,
        "fresh_orders_observation_unavailable",
    )
    currency = _text(reconciliation.get("currency")).upper()
    _append_if(blockers, currency != "USD", "fresh_account_currency_not_usd")
    cash = _decimal_payload(reconciliation.get("cash"))
    if cash is None:
        blockers.append("fresh_cash_missing_or_invalid")
    elif cash < _MAX_NOTIONAL:
        blockers.append("fresh_cash_insufficient_for_25_notional")
    position_count = _int_payload(reconciliation.get("position_count"))
    if position_count is None:
        blockers.append("fresh_position_count_missing_or_invalid")
    elif position_count != 0:
        blockers.append("fresh_position_count_not_zero")
    position_symbols_payload = _string_items(reconciliation.get("position_symbols"))
    if position_symbols_payload:
        blockers.append("fresh_position_symbols_present")
    if any(symbol.upper() != _SYMBOL for symbol in position_symbols_payload):
        blockers.append("fresh_non_spy_position_present")
    _append_if(
        blockers,
        reconciliation.get("spy_absent_or_zero") is not True,
        "fresh_spy_position_not_absent_or_zero",
    )
    open_order_count = _int_payload(reconciliation.get("open_order_count"))
    if open_order_count is None:
        blockers.append("fresh_open_order_count_missing_or_invalid")
    elif open_order_count != 0:
        blockers.append("fresh_open_orders_present")
    _append_if(
        blockers,
        reconciliation.get("recent_order_metadata_available") is not True,
        "fresh_recent_order_metadata_unavailable",
    )
    _append_if(
        blockers,
        reconciliation.get("duplicate_m435_client_order_id_found") is True,
        "fresh_duplicate_m435_client_order_id_found",
    )
    _append_if(
        blockers,
        bool(reconciliation.get("unavailable_observations")),
        "fresh_unavailable_observations_present",
    )
    return _dedupe(blockers)


def _explicit_pre_submit_reconciliation_blockers(
    observed_at: object,
    *,
    evaluated_at_utc: datetime | None,
    evaluated_at_blockers: Sequence[str],
    max_age: timedelta,
    future_tolerance: timedelta,
) -> tuple[str, ...]:
    if observed_at is _RECONCILIATION_OBSERVED_AT_UNSET:
        return ()
    return _freshness_blockers(
        observed_at,
        evaluated_at_utc=evaluated_at_utc,
        evaluated_at_blockers=evaluated_at_blockers,
        missing_blocker="pre_submit_reconciliation_observed_at_missing",
        timezone_naive_blocker="pre_submit_reconciliation_observed_at_timezone_naive",
        invalid_blocker="pre_submit_reconciliation_observed_at_invalid",
        stale_blocker="pre_submit_reconciliation_stale",
        future_blocker="pre_submit_reconciliation_future_dated",
        max_age=max_age,
        future_tolerance=future_tolerance,
    )


def _observe_reconciliation(
    broker: Any,
    *,
    phase: str,
    observed_at: str | datetime = "",
    redactor: Callable[[str], str],
) -> dict[str, object]:
    unavailable: list[str] = []
    unavailable_reasons: dict[str, object] = {}
    reconciliation: dict[str, object] = {
        "account_observation_available": False,
        "broker_action_flags": {
            "cancel": False,
            "close": False,
            "liquidate": False,
            "mutation": False,
            "replace": False,
            "submit": False,
        },
        "broker_action_performed": False,
        "cash": "",
        "currency": "",
        "duplicate_m435_client_order_id_found": False,
        "duplicate_m435_client_order_id_matches": [],
        "mutated": False,
        "observed_at": _timestamp_text(None, observed_at),
        "open_order_count": 0,
        "open_orders": [],
        "orders_observation_available": False,
        "phase": phase,
        "position_count": 0,
        "position_symbols": [],
        "positions": [],
        "positions_observation_available": False,
        "read_only_broker_observation": True,
        "recent_order_count": 0,
        "recent_order_metadata_available": False,
        "recent_orders": [],
        "spy_absent_or_zero": False,
        "submitted": False,
        "unavailable_observations": unavailable,
        "unavailable_reasons": unavailable_reasons,
    }
    try:
        account = account_observation_payload(broker.get_account())
        reconciliation.update(
            {
                "account_observation_available": True,
                "account_summary": {
                    "cash": account.get("cash", ""),
                    "currency": account.get("currency", ""),
                },
                "cash": account.get("cash", ""),
                "currency": account.get("currency", ""),
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        _mark_unavailable(unavailable, unavailable_reasons, "account", exc, redactor)

    try:
        positions = position_observation_payloads(broker.get_positions())
        symbols = position_symbols(positions)
        reconciliation.update(
            {
                "position_count": len(positions),
                "position_symbols": list(symbols),
                "positions": list(positions),
                "positions_observation_available": True,
                "spy_absent_or_zero": _spy_absent_or_zero(positions),
            }
        )
    except Exception as exc:  # pragma: no cover - fake failure safety path
        _mark_unavailable(unavailable, unavailable_reasons, "positions", exc, redactor)

    open_orders, open_query = _observe_orders(
        broker,
        status_filter="open",
        symbol_filter="",
        side_filter="",
        redactor=redactor,
        unavailable=unavailable,
        unavailable_reasons=unavailable_reasons,
        unavailable_name=f"{phase}_open_orders",
    )
    recent_orders, recent_query = _observe_orders(
        broker,
        status_filter="all",
        symbol_filter=_SYMBOL,
        side_filter=_SIDE,
        redactor=redactor,
        unavailable=unavailable,
        unavailable_reasons=unavailable_reasons,
        unavailable_name=f"{phase}_recent_spy_buy_orders",
    )
    duplicate_matches = _orders_matching_client_order_id(
        (*open_orders, *recent_orders),
        M435_CLIENT_ORDER_ID,
    )
    open_query_available = open_query.get("recent_order_query_available") is True
    recent_query_available = recent_query.get("recent_order_query_available") is True
    open_metadata_complete = (
        open_query.get("recent_order_query_metadata_complete") is True
    )
    recent_metadata_complete = (
        recent_query.get("recent_order_query_metadata_complete") is True
    )
    reconciliation.update(
        {
            f"{phase}_open_order_query": open_query,
            f"{phase}_recent_spy_buy_order_query": recent_query,
            "duplicate_m435_client_order_id_found": bool(duplicate_matches),
            "duplicate_m435_client_order_id_matches": duplicate_matches,
            "open_order_count": len(open_orders),
            "open_orders": list(open_orders),
            "orders_observation_available": (
                open_query_available and recent_query_available
            ),
            "recent_order_count": len(recent_orders),
            "recent_order_metadata_available": (
                open_query_available
                and recent_query_available
                and open_metadata_complete
                and recent_metadata_complete
            ),
            "recent_orders": list(recent_orders),
        }
    )
    return reconciliation


def _observe_orders(
    broker: Any,
    *,
    status_filter: str,
    symbol_filter: str,
    side_filter: str,
    redactor: Callable[[str], str],
    unavailable: list[str],
    unavailable_reasons: dict[str, object],
    unavailable_name: str,
) -> tuple[tuple[dict[str, str], ...], dict[str, object]]:
    query = AlpacaRecentOrderQuery(
        status_filter=status_filter,
        limit=100,
        asset_class_filter=_ASSET_CLASS,
        symbol_filter=symbol_filter,
        side_filter=side_filter,
    )
    query_payload = {
        **recent_order_query_payload(query),
        "recent_order_query_attempted": True,
        "recent_order_query_available": False,
        "recent_order_query_returned_count": 0,
    }
    try:
        orders = order_observation_payloads(broker.get_recent_orders(query))
    except Exception as exc:  # pragma: no cover - fake failure safety path
        _mark_unavailable(
            unavailable,
            unavailable_reasons,
            unavailable_name,
            exc,
            redactor,
        )
        return (), query_payload
    return (
        orders,
        {
            **query_payload,
            "recent_order_query_available": True,
            "recent_order_query_returned_count": len(orders),
        },
    )


def _submit_once(
    broker: Any,
    payload: Mapping[str, object],
    *,
    redactor: Callable[[str], str],
    order_journal: SqliteOrderJournal,
    occurred_at: datetime,
) -> dict[str, object]:
    request = AlpacaOrderRequest(
        client_order_id=M435_CLIENT_ORDER_ID,
        symbol=_SYMBOL,
        side=_SIDE,
        asset_class=_ASSET_CLASS,
        notional=_MAX_NOTIONAL,
        order_type=_ORDER_TYPE,
        time_in_force=_TIME_IN_FORCE,
    )
    try:
        result = broker.submit_order_request(
            request,
            risk_verdict=RiskVerdict(
                allowed=True,
                reason="explicit_m435_tiny_spy_paper_buy_submit",
                detail="paper_lab_plumbing_test_not_profit_evidence",
            ),
        )
    except Exception as exc:
        message = redactor(str(exc))
        journal_error = ""
        try:
            journal_record = order_journal.mark_submit_ambiguous(
                M435_CLIENT_ORDER_ID,
                occurred_at,
                reason=exc.__class__.__name__,
            )
        except Exception as journal_exc:
            journal_record = None
            journal_error = journal_exc.__class__.__name__
        return {
            **payload,
            "accepted": None,
            "blockers": [],
            "broker_action_performed": True,
            "broker_error": True,
            "error": "m435_submit_ambiguous_after_single_call",
            "error_type": exc.__class__.__name__,
            "message": message,
            "mutated": True,
            "order_journal_error": journal_error,
            "order_journal_state": (
                "submit_attempted"
                if journal_record is None
                else journal_record.state.value
            ),
            "redacted_exception_message": message,
            "state": "ambiguous_after_single_submit_stop_no_retry",
            "submit_authorized": True,
            "submitted": True,
            "submit_call_count": 1,
        }

    metadata = broker_order_result_receipt_metadata(result)
    accepted = bool(result.accepted)
    journal_error = ""
    try:
        journal_record = order_journal.record_broker_observation(
            M435_CLIENT_ORDER_ID,
            occurred_at,
            broker_order_id=metadata["order_id"],
            broker_status=(
                metadata["normalized_status"]
                or ("accepted" if accepted else "rejected")
            ),
            filled_quantity=metadata["filled_quantity"] or None,
            filled_average_price=metadata["filled_average_price"] or None,
        )
    except Exception as exc:
        journal_error = exc.__class__.__name__
        try:
            journal_record = order_journal.mark_submit_ambiguous(
                M435_CLIENT_ORDER_ID,
                occurred_at,
                reason="broker_observation_persistence_failed",
            )
        except Exception:
            journal_record = None
        accepted = False
    return {
        **payload,
        "accepted": accepted,
        "blockers": [],
        "broker_action_performed": True,
        "broker_error": False,
        "broker_order_id": metadata["order_id"],
        "broker_status": metadata["normalized_status"],
        "client_order_id": metadata["client_order_id"] or M435_CLIENT_ORDER_ID,
        "error": (
            "m435_journal_observation_failed"
            if journal_error
            else ""
            if accepted
            else "m435_submit_rejected_no_retry"
        ),
        "filled": result.filled,
        "filled_average_price": metadata["filled_average_price"],
        "filled_quantity": metadata["filled_quantity"],
        "message": str(result.reason) if not accepted else "",
        "mutated": True,
        "order_journal_error": journal_error,
        "order_journal_state": (
            "submit_attempted"
            if journal_record is None
            else journal_record.state.value
        ),
        "raw_reason": metadata["raw_reason"],
        "raw_status": metadata["raw_status"],
        "state": (
            "paper_buy_submit_accepted_pending_reconciliation"
            if accepted
            else "paper_buy_submit_rejected_no_retry"
        ),
        "submit_authorized": True,
        "submitted": True,
        "submit_call_count": 1,
    }


def _m435_order_journal_path(
    *,
    output_path: Path | None,
) -> Path | None:
    if output_path is None:
        return None
    return output_path.with_name(f"{output_path.stem}_order_journal.sqlite3")


def _claim_durable_submit(
    *,
    journal_path: Path,
    run_id: str,
    occurred_at: datetime,
) -> tuple[
    SqliteOrderJournal | None,
    RuntimeLeaseResult | None,
    dict[str, object],
    tuple[str, ...],
]:
    status: dict[str, object] = {
        "order_journal_claimed": False,
        "order_journal_error": "",
        "order_journal_lease_acquired": False,
        "order_journal_lease_released": False,
        "order_journal_reservation_status": "not_attempted",
        "order_journal_state": "",
    }
    journal = SqliteOrderJournal(journal_path)
    try:
        journal.initialize()
        lease = journal.acquire_runtime_lease(
            lease_name=_LEASE_NAME,
            owner_run_id=run_id,
            occurred_at=occurred_at,
            ttl_seconds=_LEASE_TTL_SECONDS,
        )
    except Exception as exc:
        status["order_journal_error"] = exc.__class__.__name__
        return None, None, status, ("durable_submit_journal_unavailable",)

    status["order_journal_lease_acquired"] = lease.acquired
    if not lease.acquired:
        return journal, lease, status, ("durable_submit_lease_unavailable",)

    try:
        reservation = journal.reserve(
            OrderReservation(
                client_order_id=M435_CLIENT_ORDER_ID,
                execution_plan_id=M435_EXECUTION_PLAN_ID,
                run_id=run_id,
                symbol=_SYMBOL,
                side=_SIDE,
                quantity=None,
                notional=_MAX_NOTIONAL,
            ),
            occurred_at,
        )
        status["order_journal_reservation_status"] = reservation.status
        status["order_journal_state"] = reservation.record.state.value
        if not reservation.acquired:
            blocker = (
                "durable_submit_identity_conflict"
                if reservation.status == "client_order_id_conflict"
                else "durable_submit_already_reserved"
            )
            status["order_journal_lease_released"] = journal.release_runtime_lease(
                lease_name=_LEASE_NAME,
                owner_run_id=run_id,
                lease_token=lease.lease_token,
            )
            return journal, lease, status, (blocker,)

        claim = journal.claim_pre_mutation_submit(
            client_order_id=M435_CLIENT_ORDER_ID,
            execution_plan_id=M435_EXECUTION_PLAN_ID,
            reservation_run_id=run_id,
            lease_name=_LEASE_NAME,
            lease_owner_run_id=run_id,
            lease_token=lease.lease_token,
            fencing_generation=lease.fencing_generation,
            canonical_risk_allowed=True,
            snapshot_fresh=True,
            occurred_at=occurred_at,
        )
    except Exception as exc:
        status["order_journal_error"] = exc.__class__.__name__
        try:
            status["order_journal_lease_released"] = journal.release_runtime_lease(
                lease_name=_LEASE_NAME,
                owner_run_id=run_id,
                lease_token=lease.lease_token,
            )
        except Exception:
            pass
        return journal, lease, status, ("durable_pre_mutation_claim_failed",)

    status.update(
        {
            "order_journal_claimed": True,
            "order_journal_state": claim.state.value,
        }
    )
    return journal, lease, status, ()


def _attach_matching_post_submit_order(
    payload: Mapping[str, object],
) -> dict[str, object]:
    post = _mapping_or_empty(payload.get("post_submit_reconciliation"))
    orders = (
        *_mapping_items(post.get("open_orders")),
        *_mapping_items(post.get("recent_orders")),
    )
    matches = _orders_matching_client_order_id(orders, M435_CLIENT_ORDER_ID)
    if not matches:
        return dict(payload)
    first = matches[0]
    submitted_at = _text(first.get("submitted_at"))
    return {
        **payload,
        "post_submit_matching_order": first,
        "post_submit_matching_order_found": True,
        "submitted_at": submitted_at or _text(payload.get("submitted_at")),
    }


def _finalize_blocked_payload(
    payload: Mapping[str, object],
    blockers: Sequence[str],
) -> dict[str, object]:
    deduped = _dedupe(blockers)
    return {
        **payload,
        "blockers": list(deduped),
        "broker_action_performed": False,
        "error": _text(payload.get("error")) or _error_from_blockers(deduped),
        "mutated": False,
        "ok": False,
        "submit_authorized": False,
        "submitted": False,
        "submit_call_count": 0,
    }


def _finalize_submit_payload(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        **payload,
        "ok": payload.get("accepted") is True,
        "profit_claim": _PROFIT_CLAIM,
    }


def _load_and_validate_m434_source(
    path: Path,
) -> tuple[Mapping[str, object] | None, tuple[str, ...]]:
    try:
        records = _jsonl_records(path)
    except ValidationError as exc:
        return None, (str(exc),)
    if len(records) != 1:
        return None, ("m434_artifact_expected_exactly_one_record",)
    record = records[0]
    return record, _m434_source_blockers(record)


def _m434_source_blockers(record: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    expected = {
        "record_type": _M434_RECORD_TYPE,
        "milestone": "M434",
        "approval_scope": "offline_paper_buy_submit_approval_packet",
        "approval_decision": _M434_READY_APPROVAL_DECISION,
        "next_required_milestone": _M434_READY_NEXT_MILESTONE,
        "symbol": _SYMBOL,
        "side": _SIDE,
        "asset_class": _ASSET_CLASS,
        "intended_order_type": _ORDER_TYPE,
        "intended_time_in_force": _TIME_IN_FORCE,
        "paper_only": True,
        "operator_approval_required": True,
        "required_single_attempt_submit": True,
        "trade_recommendation": "none",
        "profit_claim": _PROFIT_CLAIM,
    }
    for field_name, expected_value in expected.items():
        _append_if(
            blockers,
            record.get(field_name) != expected_value,
            f"m434_{field_name}_invalid",
        )
    if _string_items(record.get("blockers")):
        blockers.append("m434_blockers_present")
    for field_name in _M434_FALSE_FIELDS:
        _append_if(
            blockers,
            record.get(field_name) is not False,
            f"m434_{field_name}_not_false",
        )
    labels = _string_items(record.get("labels"))
    for label in ("paper_lab_only", "not_live_authorized", "profit_claim=none"):
        if label not in labels:
            blockers.append(f"m434_label_missing_{label}")
    return _dedupe(blockers)


def _existing_m435_submit_blockers(path: Path | None) -> tuple[str, ...]:
    if path is None or not path.exists():
        return ()
    try:
        records = _jsonl_records(path)
    except ValidationError:
        return ("m435_existing_artifact_unreadable",)
    for record in records:
        if record.get("client_order_id") != M435_CLIENT_ORDER_ID:
            continue
        if record.get("submitted") is True or _int_payload(record.get("submit_call_count")):
            return ("m435_prior_submit_or_submit_call_detected",)
    return ()


def _jsonl_records(path: Path) -> tuple[Mapping[str, object], ...]:
    if not path.exists() or not path.is_file():
        raise ValidationError("source artifact must be an existing file")
    records: list[Mapping[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(
            f"source artifact could not be read: {exc.__class__.__name__}"
        ) from None
    for raw_line in lines:
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValidationError("source artifact contains invalid JSON") from exc
        if not isinstance(payload, Mapping):
            raise ValidationError("source artifact records must be JSON objects")
        records.append(dict(payload))
    return tuple(records)


def _order_intent() -> dict[str, object]:
    return {
        "asset_class": _ASSET_CLASS,
        "notional": str(_MAX_NOTIONAL),
        "order_type": _ORDER_TYPE,
        "side": _SIDE,
        "symbol": _SYMBOL,
        "time_in_force": _TIME_IN_FORCE,
    }


def _mark_unavailable(
    unavailable: list[str],
    reasons: dict[str, object],
    name: str,
    exc: Exception,
    redactor: Callable[[str], str],
) -> None:
    unavailable.append(name)
    reasons[name] = {
        "error_type": exc.__class__.__name__,
        "message": redactor(str(exc)),
    }


def _orders_matching_client_order_id(
    orders: Sequence[Mapping[str, object]],
    client_order_id: str,
) -> list[dict[str, object]]:
    return [
        dict(order)
        for order in orders
        if _text(order.get("client_order_id")) == client_order_id
    ]


def _spy_absent_or_zero(positions: Sequence[Mapping[str, object]]) -> bool:
    spy_positions = [
        position
        for position in positions
        if _text(position.get("symbol")).strip().upper() == _SYMBOL
    ]
    if not spy_positions:
        return True
    for position in spy_positions:
        quantity = _decimal_payload(
            position.get("quantity", position.get("qty", ""))
        )
        if quantity is None or quantity != Decimal("0"):
            return False
    return True


def _split_blocker_detail(detail: object) -> tuple[str, ...]:
    return tuple(item for item in _text(detail).split(",") if item)


def _append_if(
    blockers: list[str],
    condition: bool,
    blocker: str,
) -> None:
    if condition:
        blockers.append(blocker)


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)


def _evaluation_clock(value: object) -> tuple[datetime | None, tuple[str, ...]]:
    return _timestamp_to_utc(
        value,
        missing_blocker="evaluation_clock_missing",
        timezone_naive_blocker="evaluation_clock_timezone_naive",
        invalid_blocker="evaluation_clock_invalid",
    )


def _reconciliation_observed_at(
    *,
    reconciliation_clock: Callable[[], object] | None,
) -> object:
    clock = reconciliation_clock or _system_utc_now
    return clock()


def _system_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp_to_utc(
    value: object,
    *,
    missing_blocker: str,
    timezone_naive_blocker: str,
    invalid_blocker: str,
) -> tuple[datetime | None, tuple[str, ...]]:
    if value in (None, ""):
        return None, (missing_blocker,)
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(_isoformat_z_to_offset(str(value)))
        except ValueError:
            return None, (invalid_blocker,)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, (timezone_naive_blocker,)
    return parsed.astimezone(timezone.utc), ()


def _isoformat_z_to_offset(value: str) -> str:
    return f"{value[:-1]}+00:00" if value.endswith("Z") else value


def _timestamp_text(parsed_utc: datetime | None, original: object) -> str:
    if parsed_utc is not None:
        return parsed_utc.isoformat()
    if isinstance(original, datetime):
        return original.isoformat()
    return _text(original).strip()


def _display_timestamp(value: object) -> str:
    parsed_utc, _ = _timestamp_to_utc(
        value,
        missing_blocker="timestamp_missing",
        timezone_naive_blocker="timestamp_timezone_naive",
        invalid_blocker="timestamp_invalid",
    )
    return _timestamp_text(parsed_utc, value)


def _nonnegative_timedelta(value: object, field_name: str) -> timedelta:
    if type(value) is not timedelta or value.total_seconds() < 0:
        raise ValidationError(f"{field_name} must be a non-negative timedelta.")
    return value


def _session_status(value: object) -> M435EquitySessionStatus:
    if type(value) is not M435EquitySessionStatus:
        raise ValidationError("equity_session_status must be M435EquitySessionStatus.")
    return value


def _path(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a Path or string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} must not be empty.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _source_value(
    source_record: Mapping[str, object] | None,
    field_name: str,
) -> str:
    if source_record is None:
        return ""
    return _text(source_record.get(field_name))


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_items(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _string_items(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _int_payload(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    return None


def _decimal_payload(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _error_from_blockers(blockers: Sequence[str]) -> str:
    deduped = _dedupe(blockers)
    return "" if not deduped else deduped[0]


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


__all__ = [
    "M435_APPROVAL_PHRASE",
    "M435_CLIENT_ORDER_ID",
    "M435_COMMAND",
    "M435_DEFAULT_OUTPUT_PATH",
    "M435_DEFAULT_RUN_ID",
    "M435_DEFAULT_SOURCE_M434_ARTIFACT_PATH",
    "M435EquitySessionStatus",
    "render_m435_paper_buy_submit_json",
    "render_m435_paper_buy_submit_text",
    "run_m435_tiny_spy_paper_buy_submit",
    "write_m435_paper_buy_submit_artifact",
]
