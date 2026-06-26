"""v1.99 authorized bounded SPY paper drill executor.

This module consumes a ready v1.95 approval packet plus the exact operator
authorization phrase, runs the v1.96 fresh read-only paper broker observation,
and then performs at most one bounded SPY paper submit plus at most one same
order cancellation.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from algotrader.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    AlpacaPaperConfig,
)
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaOrderRequest, AlpacaRecentOrderQuery
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.etf_sma_v195_bounded_paper_drill_approval_packet import (
    APPROVAL_PACKET_READY_NO_MUTATION,
    V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE,
)
from algotrader.execution.etf_sma_v196_read_only_broker_observation import (
    PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE,
    PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_NOT_READY,
    PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS,
    PAPER_OBSERVATION_BLOCKED_CREDENTIALS_UNAVAILABLE,
    PAPER_OBSERVATION_BLOCKED_DUPLICATE_CLIENT_ORDER_ID,
    PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH,
    PAPER_OBSERVATION_BLOCKED_LIVE_ENDPOINT_OR_PROFILE,
    PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT,
    PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION,
    PAPER_OBSERVATION_ELIGIBLE,
    extract_projected_future_paper_request_fields,
    run_v196_read_only_broker_observation,
)


V199_RUN_ID = "v199_authorized_bounded_spy_paper_drill"
V199_DEFAULT_OUTPUT_ROOT = "runs/paper_lab/v199_authorized_bounded_spy_paper_drill"
V199_DEFAULT_APPROVAL_PACKET_PATH = (
    "runs/paper_lab/v195_bounded_paper_drill_approval_packet_final_verify/"
    "approval_packet.json"
)
V199_PACKET_VERSION = "v199_authorized_bounded_spy_paper_drill_packet_v1"
V199_MANIFEST_VERSION = "v199_authorized_bounded_spy_paper_drill_manifest_v1"
V199_AUTHORIZATION_PHRASE = V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE
V199_SYMBOL = "SPY"
V199_SIDE = "buy"
V199_ORDER_TYPE = "market"
V199_TIME_IN_FORCE = "day"
V199_MAX_NOTIONAL = Decimal("25.00")
_EXPECTED_ACCOUNT_ENV = "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"

PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED = (
    "paper_drill_submitted_cancel_confirmed"
)
PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL = (
    "paper_drill_submitted_filled_before_cancel"
)
PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED = (
    "paper_drill_submitted_partial_fill_then_cancelled"
)
PAPER_DRILL_SUBMITTED_THEN_REJECTED = "paper_drill_submitted_then_rejected"
PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE = "paper_drill_blocked_pre_submit_gate"
PAPER_DRILL_BLOCKED_EXPECTED_ACCOUNT_MISMATCH = (
    "paper_drill_blocked_expected_account_mismatch"
)
PAPER_DRILL_BLOCKED_LIVE_ENDPOINT_OR_PROFILE = (
    "paper_drill_blocked_live_endpoint_or_profile"
)
PAPER_DRILL_BLOCKED_OPEN_SPY_ORDER_PRESENT = (
    "paper_drill_blocked_open_spy_order_present"
)
PAPER_DRILL_BLOCKED_UNEXPECTED_NON_SPY_POSITION = (
    "paper_drill_blocked_unexpected_non_spy_position"
)
PAPER_DRILL_BLOCKED_DUPLICATE_CLIENT_ORDER_ID = (
    "paper_drill_blocked_duplicate_client_order_id"
)
PAPER_DRILL_BLOCKED_ACCOUNT_NOT_TRADABLE = (
    "paper_drill_blocked_account_not_tradable"
)
PAPER_DRILL_BLOCKED_APPROVAL_PACKET_NOT_READY = (
    "paper_drill_blocked_approval_packet_not_ready"
)
PAPER_DRILL_BLOCKED_BROKER_RESPONSE_AMBIGUOUS = (
    "paper_drill_blocked_broker_response_ambiguous"
)
PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME = "paper_drill_unresolved_order_outcome"
PAPER_DRILL_CANCEL_AMBIGUOUS_RECONCILED = (
    "paper_drill_cancel_ambiguous_reconciled"
)

V199_SAFETY_LABELS = (
    "paper_lab_only",
    "bounded_paper_drill",
    "not_live_authorized",
    "not_live_trading",
    "profit_claim=none",
    "operator_authorized_once",
)

BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]

_TERMINAL_STATUSES = {
    "canceled",
    "cancelled",
    "expired",
    "filled",
    "rejected",
}
_CANCELLED_STATUSES = {"canceled", "cancelled"}
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|secret(?:[_-]?key)?|token)\b"
    r"\s*[:=]\s*[^,\s;)]+"
)
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
_SAFE_MESSAGE_LIMIT = 240

_OBSERVATION_BLOCKER_CLASSIFICATIONS = {
    PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH: (
        PAPER_DRILL_BLOCKED_EXPECTED_ACCOUNT_MISMATCH
    ),
    PAPER_OBSERVATION_BLOCKED_LIVE_ENDPOINT_OR_PROFILE: (
        PAPER_DRILL_BLOCKED_LIVE_ENDPOINT_OR_PROFILE
    ),
    PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT: (
        PAPER_DRILL_BLOCKED_OPEN_SPY_ORDER_PRESENT
    ),
    PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION: (
        PAPER_DRILL_BLOCKED_UNEXPECTED_NON_SPY_POSITION
    ),
    PAPER_OBSERVATION_BLOCKED_DUPLICATE_CLIENT_ORDER_ID: (
        PAPER_DRILL_BLOCKED_DUPLICATE_CLIENT_ORDER_ID
    ),
    PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE: (
        PAPER_DRILL_BLOCKED_ACCOUNT_NOT_TRADABLE
    ),
    PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_NOT_READY: (
        PAPER_DRILL_BLOCKED_APPROVAL_PACKET_NOT_READY
    ),
    PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS: (
        PAPER_DRILL_BLOCKED_BROKER_RESPONSE_AMBIGUOUS
    ),
    PAPER_OBSERVATION_BLOCKED_CREDENTIALS_UNAVAILABLE: (
        PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE
    ),
}


def run_v199_authorized_bounded_spy_paper_drill(
    *,
    approval_packet_path: Path | str = V199_DEFAULT_APPROVAL_PACKET_PATH,
    output_root: Path | str = V199_DEFAULT_OUTPUT_ROOT,
    run_id: str = V199_RUN_ID,
    timestamp: str | None = None,
    authorization_phrase: str = "",
    env: Mapping[str, str] | None = None,
    expected_paper_account_id: str | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    reconciliation_poll_attempts: int = 3,
    reconciliation_poll_interval_seconds: float = 1.0,
) -> dict[str, object]:
    """Execute the one-time bounded SPY paper drill if all gates pass."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    generated_at = timestamp or _utc_now_text()
    normalized_env = _normalized_paper_env(env)
    source_path = Path(approval_packet_path)
    approval_packet = _load_json_object_or_empty(source_path)
    projected = (
        extract_projected_future_paper_request_fields(approval_packet)
        if approval_packet
        else {}
    )
    source_classification = _text(
        approval_packet.get("approval_packet_classification")
    )
    authorization_observed = authorization_phrase == V199_AUTHORIZATION_PHRASE
    expected_account = (
        expected_paper_account_id
        if expected_paper_account_id is not None
        else normalized_env.get(_EXPECTED_ACCOUNT_ENV, "")
    )
    pre_submit_observation: dict[str, object] = {}

    gate_classification, gate_blocker = _pre_observation_gate_blocker(
        source_path=source_path,
        approval_packet=approval_packet,
        source_classification=source_classification,
        projected=projected,
        authorization_observed=authorization_observed,
    )
    if gate_blocker:
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_classification=source_classification,
            authorization_observed=authorization_observed,
            projected=projected,
            pre_submit_observation=pre_submit_observation,
            actual_request={},
            submit_result={},
            cancel_result={},
            final_order={},
            outcome_classification=gate_classification,
            blocker=gate_blocker,
            next_operator_action="resolve_pre_submit_gate_before_any_paper_drill",
            broker_read_performed=False,
        )
        _write_artifacts(root, packet, pre_submit_observation, approval_packet, projected)
        _validate_no_exposure(packet, normalized_env, expected_account)
        return packet

    pre_submit_observation = run_v196_read_only_broker_observation(
        approval_packet_path=source_path,
        output_root=root / "pre_submit_broker_observation",
        run_id=f"{run_id}_pre_submit_observation",
        timestamp=generated_at,
        env=normalized_env,
        expected_paper_account_id=expected_account,
        broker_client_factory=broker_client_factory,
    )
    observation_classification = _text(
        pre_submit_observation.get("eligibility_classification")
    )
    if observation_classification != PAPER_OBSERVATION_ELIGIBLE:
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_classification=source_classification,
            authorization_observed=authorization_observed,
            projected=projected,
            pre_submit_observation=pre_submit_observation,
            actual_request={},
            submit_result={},
            cancel_result={},
            final_order={},
            outcome_classification=_blocked_classification_from_observation(
                observation_classification
            ),
            blocker=_text(pre_submit_observation.get("blocker"))
            or "pre_submit_observation_not_eligible",
            next_operator_action="stop_before_submit_and_review_pre_submit_observation",
            broker_read_performed=_bool(pre_submit_observation.get("broker_read_performed")),
        )
        _write_artifacts(root, packet, pre_submit_observation, approval_packet, projected)
        _validate_no_exposure(packet, normalized_env, expected_account)
        return packet

    request = _alpaca_order_request(projected)
    actual_request = _request_payload(request)
    client_result = _build_broker_client(normalized_env, broker_client_factory)
    if client_result.get("error"):
        packet = _build_packet(
            run_id=run_id,
            timestamp=generated_at,
            output_root=root,
            source_path=source_path,
            source_classification=source_classification,
            authorization_observed=authorization_observed,
            projected=projected,
            pre_submit_observation=pre_submit_observation,
            actual_request=actual_request,
            submit_result={},
            cancel_result={},
            final_order={},
            outcome_classification=PAPER_DRILL_BLOCKED_BROKER_RESPONSE_AMBIGUOUS,
            blocker=_text(client_result.get("error")),
            next_operator_action="review_broker_client_construction_before_any_submit",
            broker_read_performed=True,
        )
        _write_artifacts(root, packet, pre_submit_observation, approval_packet, projected)
        _validate_no_exposure(packet, normalized_env, expected_account)
        return packet

    lifecycle = _submit_cancel_reconcile(
        client=client_result["client"],
        request=request,
        poll_attempts=reconciliation_poll_attempts,
        poll_interval_seconds=reconciliation_poll_interval_seconds,
    )
    packet = _build_packet(
        run_id=run_id,
        timestamp=generated_at,
        output_root=root,
        source_path=source_path,
        source_classification=source_classification,
        authorization_observed=authorization_observed,
        projected=projected,
        pre_submit_observation=pre_submit_observation,
        actual_request=actual_request,
        submit_result=_mapping(lifecycle.get("submit_result")),
        cancel_result=_mapping(lifecycle.get("cancel_result")),
        final_order=_mapping(lifecycle.get("final_order")),
        outcome_classification=_text(lifecycle.get("outcome_classification")),
        blocker=_text(lifecycle.get("blocker")),
        next_operator_action=_text(lifecycle.get("next_operator_action")),
        broker_read_performed=True,
    )
    _write_artifacts(root, packet, pre_submit_observation, approval_packet, projected)
    _validate_no_exposure(packet, normalized_env, expected_account)
    return packet


def render_v199_paper_drill_brief(packet: Mapping[str, object]) -> str:
    """Render a compact operator brief without credentials or account ids."""

    request = _mapping(packet.get("projected_request_fields"))
    actual = _mapping(packet.get("actual_submitted_request_fields"))
    return "\n".join(
        (
            "# v1.99 Authorized Bounded SPY Paper Drill",
            "",
            f"- Outcome classification: `{packet.get('outcome_classification', '')}`",
            f"- Blocker: `{packet.get('blocker', '')}`",
            f"- Source approval packet: `{packet.get('source_approval_packet_path', '')}`",
            f"- Source approval classification: `{packet.get('source_approval_classification', '')}`",
            f"- Authorization phrase observed: `{_bool_text(packet.get('explicit_authorization_phrase_observed'))}`",
            f"- Projected symbol / side: `{request.get('symbol', '')}` / `{request.get('side', '')}`",
            f"- Projected order type / TIF: `{request.get('order_type', '')}` / `{request.get('time_in_force', '')}`",
            f"- Projected notional / quantity / cap: `{request.get('notional', '')}` / `{request.get('quantity', '')}` / `{request.get('cap', '')}`",
            f"- Client order id: `{packet.get('deterministic_client_order_id', '')}`",
            f"- Pre-submit observation: `{packet.get('pre_submit_observation_classification', '')}`",
            f"- Expected account configured / matched / mode: `{_bool_text(packet.get('expected_account_configured'))}` / `{_bool_text(packet.get('expected_account_matched'))}` / `{packet.get('expected_account_match_mode', '')}`",
            f"- Account status / tradable: `{packet.get('account_status', '')}` / `{_bool_text(packet.get('account_tradable'))}`",
            f"- Open SPY order before submit: `{_bool_text(packet.get('open_spy_order_observed'))}`",
            f"- Unexpected non-SPY position before submit: `{_bool_text(packet.get('unexpected_non_spy_position_observed'))}`",
            f"- Duplicate client order id before submit: `{_bool_text(packet.get('duplicate_client_order_id_observed'))}`",
            f"- Submit attempted / status: `{_bool_text(packet.get('submit_attempted'))}` / `{packet.get('submit_status', '')}`",
            f"- Actual submitted request: `{actual}`",
            f"- Cancel attempted / confirmed: `{_bool_text(packet.get('cancel_attempted'))}` / `{_bool_text(packet.get('cancel_confirmed'))}`",
            f"- Fill status: `{packet.get('fill_status', '')}`",
            f"- Final broker/order status: `{packet.get('final_broker_order_status', '')}`",
            f"- Broker read / mutation: `{_bool_text(packet.get('broker_read_performed'))}` / `{_bool_text(packet.get('broker_mutation_performed'))}`",
            f"- Paper submit / cancel: `{_bool_text(packet.get('paper_submit_performed'))}` / `{_bool_text(packet.get('paper_cancel_performed'))}`",
            f"- Live read / mutation / trading: `{_bool_text(packet.get('live_read_performed'))}` / `{_bool_text(packet.get('live_mutation_performed'))}` / `{_bool_text(packet.get('live_trading_performed'))}`",
            f"- Next operator action: `{packet.get('next_operator_action', '')}`",
            "",
        )
    )


def _pre_observation_gate_blocker(
    *,
    source_path: Path,
    approval_packet: Mapping[str, object],
    source_classification: str,
    projected: Mapping[str, object],
    authorization_observed: bool,
) -> tuple[str, str]:
    if not source_path.exists() or not approval_packet:
        return PAPER_DRILL_BLOCKED_APPROVAL_PACKET_NOT_READY, "approval_packet_missing"
    if source_classification != APPROVAL_PACKET_READY_NO_MUTATION:
        return (
            PAPER_DRILL_BLOCKED_APPROVAL_PACKET_NOT_READY,
            "approval_packet_not_ready",
        )
    if not authorization_observed:
        return (
            PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE,
            "authorization_phrase_missing_or_mismatch",
        )
    request_blocker = _projected_request_blocker(projected)
    if request_blocker:
        return PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE, request_blocker
    return "", ""


def _projected_request_blocker(projected: Mapping[str, object]) -> str:
    symbol = _text(projected.get("symbol")).upper()
    side = _text(projected.get("side")).lower()
    order_type = _text(projected.get("order_type")).lower()
    time_in_force = _text(projected.get("time_in_force")).lower()
    client_order_id = _text(projected.get("client_order_id"))
    deterministic_client_order_id = _text(
        projected.get("deterministic_client_order_id")
    )
    notional = _text(projected.get("notional"))
    quantity = _text(projected.get("quantity"))
    cap = _mapping(projected.get("cap"))
    cap_kind = _text(cap.get("maximum_notional_or_quantity_kind")).lower()
    cap_value = _decimal_or_none(cap.get("maximum_notional_or_quantity"))

    if symbol != V199_SYMBOL:
        return "projected_symbol_outside_authorized_spy_scope"
    if side != V199_SIDE:
        return "projected_side_outside_authorized_buy_scope"
    if order_type != V199_ORDER_TYPE:
        return "projected_order_type_outside_authorized_market_scope"
    if time_in_force != V199_TIME_IN_FORCE:
        return "projected_time_in_force_outside_authorized_day_scope"
    if not client_order_id:
        return "projected_client_order_id_missing"
    if deterministic_client_order_id and deterministic_client_order_id != client_order_id:
        return "projected_client_order_id_not_deterministic"
    if notional and quantity:
        return "projected_request_has_both_notional_and_quantity"
    if not notional and not quantity:
        return "projected_notional_or_quantity_missing"
    if quantity:
        return "projected_quantity_request_not_authorized_for_v199_notional_drill"
    notional_value = _decimal_or_none(notional)
    if notional_value is None or notional_value <= Decimal("0"):
        return "projected_notional_missing_or_invalid"
    if cap_kind != "notional" or cap_value is None:
        return "projected_notional_cap_missing_or_invalid"
    if notional_value > cap_value:
        return "projected_notional_exceeds_v195_cap"
    if cap_value > V199_MAX_NOTIONAL:
        return "projected_cap_exceeds_v199_max_notional"
    return ""


def _blocked_classification_from_observation(observation_classification: str) -> str:
    return _OBSERVATION_BLOCKER_CLASSIFICATIONS.get(
        observation_classification,
        PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE,
    )


def _build_broker_client(
    env: Mapping[str, str],
    broker_client_factory: BrokerClientFactory | None,
) -> dict[str, object]:
    config = _paper_config_from_env(env)
    try:
        client = (broker_client_factory or AlpacaSdkClient)(config)
    except Exception as exc:  # pragma: no cover - real SDK construction path
        return {"client": None, "error": _safe_exception_message(exc)}
    return {"client": client, "error": ""}


def _submit_cancel_reconcile(
    *,
    client: Any,
    request: AlpacaOrderRequest,
    poll_attempts: int,
    poll_interval_seconds: float,
) -> dict[str, object]:
    submit_result: dict[str, object]
    submit_ambiguous = False
    cancel_result: dict[str, object] = {
        "cancel_attempted": False,
        "cancel_confirmed": False,
        "cancel_ambiguous": False,
    }

    try:
        submit_response = client.submit_order(request)
        submit_order = _order_payload(submit_response)
        submit_result = {
            "submit_attempted": True,
            "submit_accepted": _submit_accepted(submit_order),
            "submit_status": _order_status(submit_order),
            "submit_error": "",
            "submit_error_type": "",
            "submitted_order": submit_order,
        }
    except Exception as exc:
        submit_ambiguous = True
        submit_result = {
            "submit_attempted": True,
            "submit_accepted": None,
            "submit_status": "ambiguous",
            "submit_error": _safe_exception_message(exc),
            "submit_error_type": exc.__class__.__name__,
            "submitted_order": {},
        }

    latest = _lookup_by_client_order_id(
        client,
        client_order_id=request.client_order_id,
        symbol=request.symbol,
    )
    if not latest:
        latest = _mapping(submit_result.get("submitted_order"))

    if not latest:
        return {
            "submit_result": submit_result,
            "cancel_result": cancel_result,
            "final_order": {},
            "outcome_classification": PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME,
            "blocker": (
                "submit_response_ambiguous_client_order_id_lookup_not_found"
                if submit_ambiguous
                else "submitted_order_not_found_by_client_order_id"
            ),
            "next_operator_action": "operator_reconcile_client_order_id_before_any_future_drill",
        }

    status = _order_status(latest)
    if status == "rejected":
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=PAPER_DRILL_SUBMITTED_THEN_REJECTED,
            blocker="none",
            next_action="review_rejected_paper_order_before_any_future_drill",
        )
    if status == "filled":
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL,
            blocker="none",
            next_action="record_fill_and_operator_reconcile_position_before_next_milestone",
        )
    if status in _CANCELLED_STATUSES:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result={**cancel_result, "cancel_confirmed": True},
            final_order=latest,
            outcome=_classify_final_order(latest, cancel_ambiguous=False),
            blocker="none",
            next_action="review_terminal_cancelled_order_before_any_future_drill",
        )

    order_id = _text(latest.get("order_id"))
    if not order_id:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME,
            blocker="submitted_order_id_missing_for_same_order_cancel",
            next_action="operator_reconcile_missing_broker_order_id_before_any_future_drill",
        )

    cancel_ambiguous = False
    cancel_response_payload: dict[str, object] = {}
    try:
        cancel_response_payload = _generic_payload(
            _request_order_cancellation(client, order_id)
        )
    except Exception as exc:
        cancel_ambiguous = True
        cancel_response_payload = {
            "error_type": exc.__class__.__name__,
            "message": _safe_exception_message(exc),
        }

    cancel_result = {
        "cancel_attempted": True,
        "cancel_confirmed": False,
        "cancel_ambiguous": cancel_ambiguous,
        "cancel_response": cancel_response_payload,
    }
    final_order = _poll_lookup_by_client_order_id(
        client,
        client_order_id=request.client_order_id,
        symbol=request.symbol,
        attempts=poll_attempts,
        interval_seconds=poll_interval_seconds,
    )
    if not final_order:
        final_order = latest

    final_outcome = _classify_final_order(
        final_order,
        cancel_ambiguous=cancel_ambiguous,
    )
    return _lifecycle_result(
        submit_result=submit_result,
        cancel_result={
            **cancel_result,
            "cancel_confirmed": final_outcome
            in {
                PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED,
                PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED,
                PAPER_DRILL_CANCEL_AMBIGUOUS_RECONCILED,
            },
        },
        final_order=final_order,
        outcome=final_outcome,
        blocker="none" if final_outcome != PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME else (
            "cancel_ambiguous_unresolved"
            if cancel_ambiguous
            else "order_not_terminal_after_cancel_reconciliation"
        ),
        next_action=(
            "review_terminal_drill_artifacts_before_any_future_drill"
            if final_outcome != PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME
            else "operator_reconcile_unresolved_order_before_any_future_drill"
        ),
    )


def _lifecycle_result(
    *,
    submit_result: Mapping[str, object],
    cancel_result: Mapping[str, object],
    final_order: Mapping[str, object],
    outcome: str,
    blocker: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "submit_result": dict(submit_result),
        "cancel_result": dict(cancel_result),
        "final_order": dict(final_order),
        "outcome_classification": outcome,
        "blocker": blocker,
        "next_operator_action": next_action,
    }


def _classify_final_order(
    order: Mapping[str, object],
    *,
    cancel_ambiguous: bool,
) -> str:
    status = _order_status(order)
    filled_qty = _decimal_or_none(
        order.get("filled_quantity") or order.get("filled_qty")
    ) or Decimal("0")
    if status == "rejected":
        return PAPER_DRILL_SUBMITTED_THEN_REJECTED
    if status == "filled":
        return PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL
    if status in _CANCELLED_STATUSES and filled_qty > Decimal("0"):
        return PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED
    if status in _CANCELLED_STATUSES and cancel_ambiguous:
        return PAPER_DRILL_CANCEL_AMBIGUOUS_RECONCILED
    if status in _CANCELLED_STATUSES:
        return PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED
    return PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME


def _lookup_by_client_order_id(
    client: Any,
    *,
    client_order_id: str,
    symbol: str,
) -> dict[str, object]:
    raw_client = _raw_trading_client(client)
    for method_name in ("get_order_by_client_id", "get_order_by_client_order_id"):
        method = getattr(raw_client, method_name, None)
        if callable(method):
            try:
                order = method(client_order_id)
            except Exception:
                order = None
            if order is not None:
                return _order_payload(order)

    try:
        orders = client.get_orders(
            AlpacaRecentOrderQuery(
                status_filter="all",
                limit=100,
                symbol_filter=symbol,
            )
        )
    except Exception:
        return {}

    matches = [
        _order_payload(order)
        for order in orders
        if _text(_field(order, "client_order_id")) == client_order_id
    ]
    if len(matches) != 1:
        return {}
    return matches[0]


def _poll_lookup_by_client_order_id(
    client: Any,
    *,
    client_order_id: str,
    symbol: str,
    attempts: int,
    interval_seconds: float,
) -> dict[str, object]:
    checked_attempts = max(1, int(attempts))
    checked_interval = max(0.0, float(interval_seconds))
    latest: dict[str, object] = {}
    for index in range(checked_attempts):
        latest = _lookup_by_client_order_id(
            client,
            client_order_id=client_order_id,
            symbol=symbol,
        )
        if latest and _order_status(latest) in _TERMINAL_STATUSES:
            return latest
        if index + 1 < checked_attempts and checked_interval > 0:
            time.sleep(checked_interval)
    return latest


def _request_order_cancellation(client: Any, order_id: str) -> object:
    raw_client = _raw_trading_client(client)
    for method_name in ("cancel_order_by_id", "cancel_order"):
        method = getattr(raw_client, method_name, None)
        if callable(method):
            return method(order_id)
    raise RuntimeError("paper client does not expose same-order cancellation")


def _raw_trading_client(client: Any) -> Any:
    raw = getattr(client, "raw_trading_client", None)
    return raw if raw is not None else client


def _alpaca_order_request(projected: Mapping[str, object]) -> AlpacaOrderRequest:
    notional = _decimal_or_none(projected.get("notional"))
    quantity = _decimal_or_none(projected.get("quantity"))
    return AlpacaOrderRequest(
        client_order_id=_text(projected.get("client_order_id")),
        symbol=_text(projected.get("symbol")),
        side=_text(projected.get("side")),
        asset_class="equity",
        qty=quantity,
        notional=notional,
        order_type=_text(projected.get("order_type")),
        time_in_force=_text(projected.get("time_in_force")),
    )


def _build_packet(
    *,
    run_id: str,
    timestamp: str,
    output_root: Path,
    source_path: Path,
    source_classification: str,
    authorization_observed: bool,
    projected: Mapping[str, object],
    pre_submit_observation: Mapping[str, object],
    actual_request: Mapping[str, object],
    submit_result: Mapping[str, object],
    cancel_result: Mapping[str, object],
    final_order: Mapping[str, object],
    outcome_classification: str,
    blocker: str,
    next_operator_action: str,
    broker_read_performed: bool,
) -> dict[str, object]:
    projected_summary = _projected_request_summary(projected)
    submit_attempted = _bool(submit_result.get("submit_attempted"))
    cancel_attempted = _bool(cancel_result.get("cancel_attempted"))
    final_status = _order_status(final_order)
    submit_status = _text(submit_result.get("submit_status"))
    return {
        "packet_version": V199_PACKET_VERSION,
        "run_id": run_id,
        "timestamp": timestamp,
        "generated_at": timestamp,
        "source_approval_packet_path": str(source_path),
        "source_approval_classification": source_classification,
        "explicit_authorization_phrase_observed": authorization_observed,
        "projected_request_fields": projected_summary,
        "actual_submitted_request_fields": dict(actual_request),
        "symbol": _text(projected.get("symbol")).upper(),
        "side": _text(projected.get("side")).lower(),
        "order_type": _text(projected.get("order_type")).lower(),
        "time_in_force": _text(projected.get("time_in_force")).lower(),
        "notional": _text(projected.get("notional")),
        "quantity": _text(projected.get("quantity")),
        "cap": projected_summary.get("cap", ""),
        "deterministic_client_order_id": _text(
            projected.get("deterministic_client_order_id")
            or projected.get("client_order_id")
        ),
        "client_order_id": _text(projected.get("client_order_id")),
        "pre_submit_observation_classification": _text(
            pre_submit_observation.get("eligibility_classification")
        ),
        "expected_account_configured": _bool(
            pre_submit_observation.get("expected_account_configured")
        ),
        "expected_account_matched": _bool_or_none(
            pre_submit_observation.get("expected_account_matched")
        ),
        "expected_account_match_mode": _text(
            pre_submit_observation.get("expected_account_match_mode")
        ),
        "account_status": _text(pre_submit_observation.get("account_status")),
        "account_tradable": _bool(pre_submit_observation.get("account_tradable")),
        "open_spy_order_observed": _bool(
            pre_submit_observation.get("open_spy_order_observed")
        ),
        "unexpected_non_spy_position_observed": _bool(
            pre_submit_observation.get("unexpected_non_spy_position_observed")
        ),
        "duplicate_client_order_id_observed": _bool(
            pre_submit_observation.get("duplicate_client_order_id_observed")
        ),
        "submit_attempted": submit_attempted,
        "submit_accepted": submit_result.get("submit_accepted"),
        "submit_rejected": submit_status == "rejected",
        "submit_status": submit_status,
        "submit_accepted_rejected_status": _submit_accepted_rejected_status(
            submit_result.get("submit_accepted"),
            submit_status,
        ),
        "submit_error_type": _text(submit_result.get("submit_error_type")),
        "cancel_attempted": cancel_attempted,
        "cancel_confirmed": _bool(cancel_result.get("cancel_confirmed")),
        "cancel_ambiguous": _bool(cancel_result.get("cancel_ambiguous")),
        "fill_status": _fill_status(final_order),
        "final_broker_order_status": final_status,
        "final_order_status": final_status,
        "final_order": dict(final_order),
        "outcome_classification": outcome_classification,
        "blocker": blocker or "none",
        "broker_read_performed": broker_read_performed,
        "broker_mutation_performed": submit_attempted or cancel_attempted,
        "paper_submit_performed": submit_attempted,
        "paper_cancel_performed": cancel_attempted,
        "live_read_performed": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "paper_lab_only": True,
        "bounded_paper_drill": True,
        "not_live_authorized": True,
        "not_live_trading": True,
        "profit_claim": "none",
        "operator_authorized_once": authorization_observed,
        "credential_values_exposed": False,
        "account_identifiers_serialized": False,
        "next_operator_action": next_operator_action,
        "safety_labels": list(V199_SAFETY_LABELS),
        "artifact_paths": _artifact_paths(output_root),
    }


def _projected_request_summary(projected: Mapping[str, object]) -> dict[str, object]:
    cap = _mapping(projected.get("cap"))
    return {
        "symbol": _text(projected.get("symbol")).upper(),
        "side": _text(projected.get("side")).lower(),
        "order_type": _text(projected.get("order_type")).lower(),
        "time_in_force": _text(projected.get("time_in_force")).lower(),
        "notional": _text(projected.get("notional")),
        "quantity": _text(projected.get("quantity")),
        "cap": _text(cap.get("maximum_notional_or_quantity")),
        "cap_kind": _text(cap.get("maximum_notional_or_quantity_kind")),
        "client_order_id": _text(projected.get("client_order_id")),
        "deterministic_client_order_id": _text(
            projected.get("deterministic_client_order_id")
        ),
    }


def _write_artifacts(
    root: Path,
    packet: Mapping[str, object],
    pre_submit_observation: Mapping[str, object],
    approval_packet: Mapping[str, object],
    projected: Mapping[str, object],
) -> None:
    packet_path = root / "paper_drill_packet.json"
    brief_path = root / "paper_drill_brief.md"
    record_path = root / "paper_drill_record.jsonl"
    pre_submit_path = root / "pre_submit_broker_observation_packet.json"
    approval_snapshot_path = root / "approval_packet_snapshot.json"
    manifest_path = root / "manifest.jsonl"

    _write_json(packet_path, packet)
    brief_path.write_text(
        render_v199_paper_drill_brief(packet),
        encoding="utf-8",
        newline="\n",
    )
    record_path.write_text(
        json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_json(pre_submit_path, pre_submit_observation or _empty_pre_submit_observation())
    _write_json(
        approval_snapshot_path,
        _approval_packet_snapshot(approval_packet, projected),
    )
    manifest = {
        "manifest_version": V199_MANIFEST_VERSION,
        "run_id": packet["run_id"],
        "generated_at": packet["generated_at"],
        "outcome_classification": packet["outcome_classification"],
        "broker_read_performed": packet["broker_read_performed"],
        "broker_mutation_performed": packet["broker_mutation_performed"],
        "paper_submit_performed": packet["paper_submit_performed"],
        "paper_cancel_performed": packet["paper_cancel_performed"],
        "live_read_performed": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "artifacts": {
            "paper_drill_packet": _artifact_entry(packet_path),
            "paper_drill_brief": _artifact_entry(brief_path),
            "paper_drill_record": _artifact_entry(record_path),
            "pre_submit_broker_observation_packet": _artifact_entry(pre_submit_path),
            "approval_packet_snapshot": _artifact_entry(approval_snapshot_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_paths(root: Path) -> dict[str, str]:
    return {
        "paper_drill_packet": str(root / "paper_drill_packet.json"),
        "paper_drill_brief": str(root / "paper_drill_brief.md"),
        "paper_drill_record": str(root / "paper_drill_record.jsonl"),
        "pre_submit_broker_observation_packet": str(
            root / "pre_submit_broker_observation_packet.json"
        ),
        "approval_packet_snapshot": str(root / "approval_packet_snapshot.json"),
        "manifest": str(root / "manifest.jsonl"),
    }


def _approval_packet_snapshot(
    approval_packet: Mapping[str, object],
    projected: Mapping[str, object],
) -> dict[str, object]:
    return {
        "packet_version": _text(approval_packet.get("packet_version")),
        "run_id": _text(approval_packet.get("run_id")),
        "generated_at": _text(
            approval_packet.get("generated_at") or approval_packet.get("created_at")
        ),
        "approval_packet_classification": _text(
            approval_packet.get("approval_packet_classification")
        ),
        "approval_packet_is_authorization": (
            approval_packet.get("approval_packet_is_authorization") is True
        ),
        "required_future_authorization_phrase_present": bool(
            _text(approval_packet.get("required_future_authorization_phrase"))
        ),
        "projected_broker_request_status": _text(
            approval_packet.get("projected_broker_request_status")
        ),
        "projected_fields_are_projected_only": (
            approval_packet.get("projected_fields_are_projected_only") is True
        ),
        "broker_request_sent": approval_packet.get("broker_request_sent") is True,
        "paper_submit_performed": approval_packet.get("paper_submit_performed") is True,
        "broker_mutation_performed": (
            approval_packet.get("broker_mutation_performed") is True
        ),
        "projected_request_fields": _projected_request_summary(projected),
        "safety_labels": [
            label
            for label in _string_sequence(approval_packet.get("safety_labels"))
            if "credential" not in label.lower()
        ],
    }


def _empty_pre_submit_observation() -> dict[str, object]:
    return {
        "eligibility_classification": "",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "live_read_performed": False,
        "live_mutation_performed": False,
    }


def _request_payload(request: AlpacaOrderRequest) -> dict[str, object]:
    return {
        "asset_class": request.asset_class,
        "client_order_id": request.client_order_id,
        "symbol": request.symbol,
        "side": request.side,
        "order_type": request.order_type,
        "time_in_force": request.time_in_force,
        "notional": _decimal_text(request.notional),
        "quantity": _decimal_text(request.qty),
    }


def _order_payload(value: object) -> dict[str, object]:
    data = _object_data(value)
    return {
        "order_id": _text(_first_present(data, "order_id", "id", "broker_order_id")),
        "client_order_id": _text(_first_present(data, "client_order_id")),
        "symbol": _text(_first_present(data, "symbol")).upper(),
        "asset_class": _normalized_text(_first_present(data, "asset_class")),
        "side": _normalized_text(_first_present(data, "side")),
        "order_type": _normalized_text(_first_present(data, "order_type", "type")),
        "time_in_force": _normalized_text(_first_present(data, "time_in_force")),
        "status": _normalize_status(
            _first_present(data, "normalized_status", "status", "raw_status")
        ),
        "notional": _decimal_text(
            _first_decimal(data, "notional", "order_notional")
        ),
        "quantity": _decimal_text(
            _first_decimal(data, "quantity", "qty", "order_quantity")
        ),
        "filled_quantity": _decimal_text(
            _first_decimal(data, "filled_quantity", "filled_qty")
        ),
        "filled_average_price": _decimal_text(
            _first_decimal(
                data,
                "filled_average_price",
                "filled_avg_price",
                "avg_fill_price",
            )
        ),
        "submitted_at": _time_text(_first_present(data, "submitted_at", "created_at")),
        "filled_at": _time_text(_first_present(data, "filled_at")),
        "canceled_at": _time_text(
            _first_present(data, "canceled_at", "cancelled_at")
        ),
    }


def _submit_accepted(order: Mapping[str, object]) -> bool:
    status = _order_status(order)
    return bool(order) and status not in {"", "rejected"}


def _submit_accepted_rejected_status(
    accepted: object,
    submit_status: str,
) -> str:
    if accepted is True:
        return "accepted"
    if accepted is False or submit_status == "rejected":
        return "rejected"
    if submit_status:
        return submit_status
    return "not_attempted"


def _order_status(order: Mapping[str, object]) -> str:
    return _normalize_status(order.get("status"))


def _fill_status(order: Mapping[str, object]) -> str:
    status = _order_status(order)
    filled_qty = _decimal_or_none(
        order.get("filled_quantity") or order.get("filled_qty")
    ) or Decimal("0")
    if status == "filled":
        return "filled"
    if filled_qty > Decimal("0"):
        return "partial_fill"
    return "unfilled"


def _generic_payload(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    data = _object_data(value)
    return {key: _json_safe(item) for key, item in data.items()}


def _load_json_object_or_empty(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid approval packet: {exc.__class__.__name__}.") from None
    if not isinstance(parsed, dict):
        raise ValidationError("approval packet JSON payload must be an object.")
    return parsed


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_entry(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _paper_config_from_env(env: Mapping[str, str]) -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile=env.get("APP_PROFILE", ""),
        alpaca_api_key=env.get("ALPACA_API_KEY"),
        alpaca_secret_key=env.get("ALPACA_SECRET_KEY"),
        alpaca_paper_base_url=env.get(
            "ALPACA_PAPER_BASE_URL",
            DEFAULT_ALPACA_PAPER_BASE_URL,
        ),
    )


def _normalized_paper_env(env: Mapping[str, str] | None) -> dict[str, str]:
    source = dict(os.environ if env is None else env)
    normalized = {str(key): str(value) for key, value in source.items()}
    if not normalized.get("ALPACA_API_KEY") and normalized.get("APCA_API_KEY_ID"):
        normalized["ALPACA_API_KEY"] = normalized["APCA_API_KEY_ID"]
    if not normalized.get("ALPACA_SECRET_KEY"):
        normalized["ALPACA_SECRET_KEY"] = (
            normalized.get("ALPACA_API_SECRET_KEY")
            or normalized.get("APCA_API_SECRET_KEY")
            or ""
        )
    return normalized


def _validate_no_exposure(
    packet: Mapping[str, object],
    env: Mapping[str, str],
    expected_account: str | None,
) -> None:
    rendered = json.dumps(packet, sort_keys=True, default=str)
    forbidden_values = [
        env.get("ALPACA_API_KEY", ""),
        env.get("ALPACA_SECRET_KEY", ""),
        env.get("ALPACA_API_SECRET_KEY", ""),
        env.get("APCA_API_KEY_ID", ""),
        env.get("APCA_API_SECRET_KEY", ""),
        expected_account or "",
    ]
    for value in forbidden_values:
        text = _text(value)
        if len(text) >= 6 and text in rendered:
            raise ValidationError("sensitive credential or account value exposure detected.")


def _object_data(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    names = (
        "account_id",
        "asset_class",
        "avg_fill_price",
        "average_fill_price",
        "broker_order_id",
        "canceled_at",
        "cancelled_at",
        "client_order_id",
        "created_at",
        "filled_at",
        "filled_average_price",
        "filled_avg_price",
        "filled_qty",
        "filled_quantity",
        "id",
        "notional",
        "normalized_status",
        "order_id",
        "order_notional",
        "order_quantity",
        "order_type",
        "quantity",
        "qty",
        "raw_status",
        "side",
        "status",
        "submitted_at",
        "symbol",
        "time_in_force",
        "type",
    )
    return {name: getattr(value, name) for name in names if hasattr(value, name)}


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(name, "")
    if is_dataclass(value):
        field_names = {field.name for field in fields(value)}
        return getattr(value, name) if name in field_names else ""
    return getattr(value, name, "")


def _first_present(data: Mapping[str, object], *names: str) -> object:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return ""


def _first_decimal(data: Mapping[str, object], *names: str) -> Decimal | None:
    for name in names:
        value = data.get(name)
        decimal_value = _decimal_or_none(value)
        if decimal_value is not None:
            return decimal_value
    return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return decimal_value if decimal_value.is_finite() else None


def _decimal_text(value: object) -> str:
    decimal_value = _decimal_or_none(value)
    return "" if decimal_value is None else str(decimal_value)


def _normalized_text(value: object) -> str:
    return _text(value).lower()


def _normalize_status(value: object) -> str:
    text = _text(value).lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def _safe_exception_message(exc: Exception) -> str:
    message = str(exc)
    sanitized = _URL_PATTERN.sub("<redacted_url>", message)
    sanitized = _BEARER_TOKEN_PATTERN.sub("Bearer <redacted>", sanitized)
    sanitized = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=<redacted>",
        sanitized,
    )
    sanitized = " ".join(sanitized.split())
    if len(sanitized) > _SAFE_MESSAGE_LIMIT:
        return f"{sanitized[:_SAFE_MESSAGE_LIMIT].rstrip()}..."
    return sanitized


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _time_text(value: object) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value).strip()


def _bool(value: object) -> bool:
    return value is True


def _bool_or_none(value: object) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _bool_text(value: object) -> str:
    return "true" if value is True else "false" if value is False else ""


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


__all__ = [
    "PAPER_DRILL_BLOCKED_ACCOUNT_NOT_TRADABLE",
    "PAPER_DRILL_BLOCKED_APPROVAL_PACKET_NOT_READY",
    "PAPER_DRILL_BLOCKED_BROKER_RESPONSE_AMBIGUOUS",
    "PAPER_DRILL_BLOCKED_DUPLICATE_CLIENT_ORDER_ID",
    "PAPER_DRILL_BLOCKED_EXPECTED_ACCOUNT_MISMATCH",
    "PAPER_DRILL_BLOCKED_LIVE_ENDPOINT_OR_PROFILE",
    "PAPER_DRILL_BLOCKED_OPEN_SPY_ORDER_PRESENT",
    "PAPER_DRILL_BLOCKED_PRE_SUBMIT_GATE",
    "PAPER_DRILL_BLOCKED_UNEXPECTED_NON_SPY_POSITION",
    "PAPER_DRILL_CANCEL_AMBIGUOUS_RECONCILED",
    "PAPER_DRILL_SUBMITTED_CANCEL_CONFIRMED",
    "PAPER_DRILL_SUBMITTED_FILLED_BEFORE_CANCEL",
    "PAPER_DRILL_SUBMITTED_PARTIAL_FILL_THEN_CANCELLED",
    "PAPER_DRILL_SUBMITTED_THEN_REJECTED",
    "PAPER_DRILL_UNRESOLVED_ORDER_OUTCOME",
    "V199_AUTHORIZATION_PHRASE",
    "V199_DEFAULT_APPROVAL_PACKET_PATH",
    "V199_DEFAULT_OUTPUT_ROOT",
    "V199_RUN_ID",
    "render_v199_paper_drill_brief",
    "run_v199_authorized_bounded_spy_paper_drill",
]
