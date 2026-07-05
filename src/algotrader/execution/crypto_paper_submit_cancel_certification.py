"""v5.8 operator-authorized BTCUSD paper submit/cancel certification.

This module consumes the approved v5.7 paper-submit approval packet and v5.6
dry-run identity, then performs at most one BTCUSD Alpaca paper submit attempt
and at most one cancellation attempt for that same order.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import (
    AlpacaOrderRequest,
    AlpacaRecentOrderQuery,
    V58_CRYPTO_PAPER_CERTIFICATION_CLIENT_ORDER_ID_PREFIX,
)
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient


CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_SCHEMA_VERSION = (
    "v5_8_crypto_paper_submit_cancel_certification_v1"
)
CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_COMMAND = (
    "run_crypto_paper_submit_cancel_certification"
)
CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_APPROVAL_PACKET = Path(
    "runs/crypto_paper_submit_approval_packet/latest/"
    "paper_submit_approval_packet.json"
)
CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_DRY_RUN = Path(
    "runs/crypto_paper_oms_dry_run/latest/paper_oms_dry_run.json"
)
CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_paper_submit_cancel_certification/latest"
)

V58_DRY_RUN_ID = "dryrun_19bfe1c5645e29869a393564"
V58_PRE_BROKER_ORDER_ID = "prebroker_a22db5ec89a3d81457712c6b"
V58_SYMBOL = "BTCUSD"
V58_APPROVED_QTY = Decimal("0.000396783")
V58_APPROVED_MAX_NOTIONAL = Decimal("25")
V58_APPROVED_CANDIDATE = (
    "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview"
)
V58_AUTHORIZATION_TEXT = (
    "Authorized for v5.8: perform one bounded BTCUSD Alpaca paper "
    "submit/cancel certification using dry_run_id "
    "dryrun_19bfe1c5645e29869a393564, pre_broker_order_id "
    "prebroker_a22db5ec89a3d81457712c6b, qty 0.000396783, max notional "
    "25. This authorizes exactly one paper order submit attempt and its "
    "cancel/reconciliation path only. It does not authorize live trading, "
    "additional orders, replacement, liquidation, close-all, capital changes, "
    "credential exposure, or paid services."
)

ORDER_TYPE_LIMIT = "limit"
SIDE_BUY = "buy"
TIME_IN_FORCE_GTC = "gtc"
LIMIT_DISCOUNT = Decimal("0.50")
PRICE_QUANTUM = Decimal("0.01")

OUTCOME_SUBMITTED_CANCEL_CONFIRMED = "submitted_cancel_confirmed"
OUTCOME_SUBMITTED_ALREADY_FILLED = "submitted_already_filled_before_cancel"
OUTCOME_SUBMIT_REJECTED = "submit_rejected_no_open_order"
OUTCOME_SUBMIT_AMBIGUOUS = "submit_ambiguous"
OUTCOME_CANCEL_AMBIGUOUS = "cancel_ambiguous"
OUTCOME_RECONCILIATION_AMBIGUOUS = "reconciliation_ambiguous"
OUTCOME_BLOCKED_BEFORE_SUBMIT = "blocked_before_submit"

REQUIRED_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
    "bounded_paper_submit_cancel_certification",
    "one_order_attempt_only",
    "btcusd_only",
    "not_live",
    "operator_authorized_v5_8",
)

_CREDENTIAL_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
_SECRET_KEY_CANDIDATES = (
    "ALPACA_SECRET_KEY",
    "ALPACA_API_SECRET_KEY",
    "APCA_API_SECRET_KEY",
)
_EXPECTED_ACCOUNT_ENV_NAMES = (
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
)
_TERMINAL_STATUSES = {"canceled", "cancelled", "expired", "filled", "rejected"}
_CANCELLED_STATUSES = {"canceled", "cancelled"}
_CANCELABLE_STATUSES = {
    "accepted",
    "accepted_for_bidding",
    "new",
    "partially_filled",
    "pending_new",
}
_OPEN_STATUSES = _CANCELABLE_STATUSES | {"pending_cancel"}
_OBJECT_PAYLOAD_FIELDS = (
    "id",
    "account_id",
    "account_number",
    "status",
    "currency",
    "trading_blocked",
    "account_blocked",
    "symbol",
    "asset_class",
    "class",
    "tradable",
    "fractionable",
    "marginable",
    "min_order_size",
    "min_trade_increment",
    "min_order_increment",
    "min_notional",
    "min_order_notional",
    "order_id",
    "client_order_id",
    "side",
    "type",
    "order_type",
    "time_in_force",
    "qty",
    "quantity",
    "notional",
    "limit_price",
    "filled_qty",
    "filled_quantity",
    "filled_avg_price",
    "avg_fill_price",
    "submitted_at",
    "created_at",
    "filled_at",
    "canceled_at",
    "cancelled_at",
    "reject_reason",
    "reason",
    "market_value",
    "average_entry_price",
    "avg_entry_price",
)
_OBJECT_PAYLOAD_FIELD_LOOKUP = {
    re.sub(r"[^a-z0-9]", "", field.lower()): field
    for field in _OBJECT_PAYLOAD_FIELDS
}
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|secret(?:[_-]?key)?|token)\b"
    r"\s*[:=]\s*[^,\s;)]+"
)
_URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
_SAFE_MESSAGE_LIMIT = 240

BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]

__all__ = [
    "CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_COMMAND",
    "CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_APPROVAL_PACKET",
    "CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_DRY_RUN",
    "CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_SCHEMA_VERSION",
    "OUTCOME_BLOCKED_BEFORE_SUBMIT",
    "OUTCOME_CANCEL_AMBIGUOUS",
    "OUTCOME_RECONCILIATION_AMBIGUOUS",
    "OUTCOME_SUBMIT_AMBIGUOUS",
    "OUTCOME_SUBMIT_REJECTED",
    "OUTCOME_SUBMITTED_ALREADY_FILLED",
    "OUTCOME_SUBMITTED_CANCEL_CONFIRMED",
    "V58_AUTHORIZATION_TEXT",
    "V58_APPROVED_MAX_NOTIONAL",
    "V58_APPROVED_QTY",
    "V58_DRY_RUN_ID",
    "V58_PRE_BROKER_ORDER_ID",
    "deterministic_v58_client_order_id",
    "render_crypto_paper_submit_cancel_certification_text",
    "run_crypto_paper_submit_cancel_certification",
]


def run_crypto_paper_submit_cancel_certification(
    *,
    output_root: str | Path = (
        CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_OUTPUT_ROOT
    ),
    approval_packet_path: str | Path = (
        CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_APPROVAL_PACKET
    ),
    dry_run_path: str | Path = CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_DRY_RUN,
    timestamp: datetime | str | None = None,
    env: Mapping[str, str] | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    paper_submit_authorized: bool = False,
    expected_paper_account_id: str | None = None,
    reconciliation_poll_attempts: int = 3,
    reconciliation_poll_interval_seconds: float = 1.0,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    """Run the bounded v5.8 certification, failing closed before submit."""

    generated_at = _utc_datetime(timestamp or datetime.now(UTC), "timestamp")
    root = _path(output_root, "output_root")
    approval_path = _path(approval_packet_path, "approval_packet_path")
    dry_run_source_path = _path(dry_run_path, "dry_run_path")
    source_env = _env_mapping(env)
    expected_account = (
        _clean_text(expected_paper_account_id)
        if expected_paper_account_id is not None
        else _first_nonempty(source_env, _EXPECTED_ACCOUNT_ENV_NAMES)
    )
    preflight = _environment_preflight(
        source_env,
        expected_paper_account_id=expected_account,
    )
    approval_packet = _read_json_mapping_safely(approval_path)
    dry_run = _read_json_mapping_safely(dry_run_source_path)
    client_order_id = deterministic_v58_client_order_id(
        dry_run_id=V58_DRY_RUN_ID,
        pre_broker_order_id=V58_PRE_BROKER_ORDER_ID,
    )
    base = _base_result(
        output_root=root,
        approval_packet_source=approval_path,
        dry_run_source=dry_run_source_path,
        generated_at=generated_at,
        preflight=preflight,
        paper_submit_authorized=paper_submit_authorized,
        expected_paper_account_id_loaded=bool(expected_account),
        client_order_id=client_order_id,
    )

    authorization_blockers = _authorization_blockers(
        approval_packet=approval_packet,
        dry_run=dry_run,
        approval_packet_path=approval_path,
        dry_run_path=dry_run_source_path,
    )
    environment_blockers = _environment_gate_blockers(
        preflight,
        authorized=paper_submit_authorized,
    )
    early_blockers = _dedupe((*authorization_blockers, *environment_blockers))
    if early_blockers:
        return _finalize_result(
            {
                **base,
                "approval_packet_summary": _approval_packet_summary(approval_packet),
                "dry_run_summary": _dry_run_summary(dry_run),
            },
            outcome_classification=OUTCOME_BLOCKED_BEFORE_SUBMIT,
            blockers=early_blockers,
            next_operator_action="repair_v5_8_pre_submit_gate_before_paper_submit",
            write_artifacts=write_artifacts,
        )

    client_result = _build_broker_client(source_env, broker_client_factory)
    client = client_result["client"]
    if client is None:
        return _finalize_result(
            {
                **base,
                "broker_client_error": client_result["error"],
                "approval_packet_summary": _approval_packet_summary(approval_packet),
                "dry_run_summary": _dry_run_summary(dry_run),
            },
            outcome_classification=OUTCOME_BLOCKED_BEFORE_SUBMIT,
            blockers=("paper_broker_client_unavailable",),
            next_operator_action="repair_paper_broker_client_before_v5_8_submit",
            write_artifacts=write_artifacts,
        )

    account_result = _read_account(client)
    account = account_result["account"]
    asset_result = _read_asset(client, V58_SYMBOL)
    asset = asset_result["asset"]
    open_order_result = _read_orders(client, status_filter="open", symbol=V58_SYMBOL)
    open_orders = open_order_result["orders"]
    position_result = _read_positions(client)
    positions = position_result["positions"]
    existing_order = _lookup_by_client_order_id(
        client,
        client_order_id=client_order_id,
        symbol=V58_SYMBOL,
    )
    order_design, design_blockers = _build_order_design(dry_run)
    read_blockers = _read_gate_blockers(
        account=account,
        account_error=account_result["error"],
        expected_paper_account_id=expected_account,
        asset=asset,
        asset_error=asset_result["error"],
        open_orders=open_orders,
        open_order_error=open_order_result["error"],
        positions=positions,
        position_error=position_result["error"],
        existing_order=existing_order,
        client_order_id=client_order_id,
    )
    pre_submit_blockers = _dedupe((*read_blockers, *design_blockers))
    observed = {
        **base,
        "approval_packet_summary": _approval_packet_summary(approval_packet),
        "dry_run_summary": _dry_run_summary(dry_run),
        "account_observation": account,
        "asset_observation": asset,
        "open_order_scan": open_orders,
        "position_scan": positions,
        "existing_client_order_id_order": existing_order,
        "order_design": order_design,
        "broker_read_observed": True,
        "expected_account_matched": _expected_account_matched(
            account,
            expected_account,
        ),
        "pre_submit_gate_blockers": pre_submit_blockers,
    }
    if pre_submit_blockers:
        return _finalize_result(
            observed,
            outcome_classification=OUTCOME_BLOCKED_BEFORE_SUBMIT,
            blockers=pre_submit_blockers,
            next_operator_action="repair_v5_8_broker_read_gate_before_submit",
            write_artifacts=write_artifacts,
        )

    request = AlpacaOrderRequest(
        client_order_id=client_order_id,
        symbol=V58_SYMBOL,
        side=SIDE_BUY,
        asset_class="crypto",
        qty=V58_APPROVED_QTY,
        order_type=ORDER_TYPE_LIMIT,
        time_in_force=TIME_IN_FORCE_GTC,
        limit_price=_decimal_or_none(order_design.get("limit_price")),
    )
    lifecycle = _submit_cancel_reconcile(
        client=client,
        request=request,
        poll_attempts=reconciliation_poll_attempts,
        poll_interval_seconds=reconciliation_poll_interval_seconds,
    )
    final_order = _mapping(lifecycle.get("final_order"))
    residual_position: dict[str, Any] = {}
    if _filled_quantity(final_order) > Decimal("0") or _order_status(final_order) == "filled":
        residual_position = _residual_position(client, V58_SYMBOL)

    return _finalize_result(
        {
            **observed,
            "submitted_request": _request_fields(request),
            "submit_result": _mapping(lifecycle.get("submit_result")),
            "cancel_result": _mapping(lifecycle.get("cancel_result")),
            "reconciliation": {
                "final_order": final_order,
                "final_order_status": _order_status(final_order),
                "filled_qty": _decimal_text(_filled_quantity(final_order)),
                "filled_avg_price": _decimal_text(
                    _decimal_or_none(final_order.get("filled_avg_price"))
                ),
                "residual_position": residual_position,
            },
            "final_order": final_order,
        },
        outcome_classification=_clean_text(lifecycle.get("outcome_classification")),
        blockers=tuple(_text_list(lifecycle.get("blocker"))),
        next_operator_action=_clean_text(lifecycle.get("next_operator_action")),
        write_artifacts=write_artifacts,
    )


def deterministic_v58_client_order_id(
    *,
    dry_run_id: str,
    pre_broker_order_id: str,
) -> str:
    basis = {
        "dry_run_id": _clean_text(dry_run_id),
        "pre_broker_order_id": _clean_text(pre_broker_order_id),
        "symbol": V58_SYMBOL,
        "approved_qty": _decimal_text(V58_APPROVED_QTY),
        "approved_max_notional": _decimal_text(V58_APPROVED_MAX_NOTIONAL),
    }
    encoded = json.dumps(basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:16]
    return (
        V58_CRYPTO_PAPER_CERTIFICATION_CLIENT_ORDER_ID_PREFIX
        + f"{digest}"
    )


def render_crypto_paper_submit_cancel_certification_text(
    result: Mapping[str, Any],
) -> str:
    """Render a compact credential-free operator receipt."""

    preflight = result.get("operator_preflight")
    if not isinstance(preflight, Mapping):
        preflight = {}
    lines = [
        (
            "crypto_paper_submit_cancel_certification_command="
            f"{CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_COMMAND}"
        ),
        "crypto_paper_submit_cancel_certification_scope=alpaca_paper_only_btcusd_one_submit_cancel",
        f"paper_submit_authorized={_bool_text(result.get('paper_submit_authorized'))}",
    ]
    for key in (
        "APP_PROFILE_is_paper",
        "APP_PROFILE_is_live",
        "ALPACA_API_KEY_present",
        "ALPACA_API_SECRET_KEY_present",
        "ALPACA_SECRET_KEY_present",
        "APCA_API_KEY_ID_present",
        "APCA_API_SECRET_KEY_present",
        "paper_credentials_present",
        "expected_paper_account_id_loaded",
        "paper_endpoint_exact_match_indicator",
        "live_endpoint_indicator",
    ):
        lines.append(f"preflight_{key}={_bool_text(preflight.get(key))}")
    lines.extend(
        [
            f"outcome_classification={_clean_text(result.get('outcome_classification'))}",
            f"blockers={','.join(_text_list(result.get('blockers')))}",
            f"symbol={_clean_text(result.get('symbol'))}",
            f"approved_qty={_clean_text(result.get('approved_qty'))}",
            f"submitted_qty={_clean_text(result.get('submitted_qty'))}",
            f"approved_max_notional={_clean_text(result.get('approved_max_notional'))}",
            f"estimated_submit_notional={_clean_text(result.get('estimated_submit_notional'))}",
            f"order_type={_clean_text(result.get('order_type'))}",
            f"side={_clean_text(result.get('side'))}",
            f"time_in_force={_clean_text(result.get('time_in_force'))}",
            f"limit_price={_clean_text(result.get('limit_price'))}",
            f"client_order_id={_clean_text(result.get('client_order_id'))}",
            f"submit_attempt_count={_clean_text(result.get('submit_attempt_count'))}",
            f"cancel_attempt_count={_clean_text(result.get('cancel_attempt_count'))}",
            f"submit_status={_clean_text(result.get('submit_status'))}",
            f"cancel_status={_clean_text(result.get('cancel_status'))}",
            f"final_order_status={_clean_text(result.get('final_order_status'))}",
            f"reconciliation_status={_clean_text(result.get('reconciliation_status'))}",
            f"broker_read_observed={_bool_text(result.get('broker_read_observed'))}",
            f"paper_submit_performed={_bool_text(result.get('paper_submit_performed'))}",
            f"paper_cancel_performed={_bool_text(result.get('paper_cancel_performed'))}",
            f"broker_mutation_performed={_bool_text(result.get('broker_mutation_performed'))}",
            f"live_endpoint_touched={_bool_text(result.get('live_endpoint_touched'))}",
            f"live_mutation_performed={_bool_text(result.get('live_mutation_performed'))}",
            f"credential_values_exposed={_bool_text(result.get('credential_values_exposed'))}",
            f"next_operator_action={_clean_text(result.get('next_operator_action'))}",
        ]
    )
    artifacts = result.get("artifact_paths")
    if isinstance(artifacts, Mapping):
        for key in (
            "certification_result_json",
            "certification_result_md",
            "operating_record",
            "manifest",
        ):
            lines.append(f"artifact_{key}={_clean_text(artifacts.get(key))}")
    return "\n".join(lines)


def _base_result(
    *,
    output_root: Path,
    approval_packet_source: Path,
    dry_run_source: Path,
    generated_at: datetime,
    preflight: Mapping[str, bool],
    paper_submit_authorized: bool,
    expected_paper_account_id_loaded: bool,
    client_order_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_SCHEMA_VERSION,
        "operator_command": CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_COMMAND,
        "as_of": generated_at.isoformat(),
        "output_root": str(output_root),
        "approved_authorization_text": V58_AUTHORIZATION_TEXT,
        "approval_packet_source": str(approval_packet_source),
        "dry_run_source": str(dry_run_source),
        "dry_run_id": V58_DRY_RUN_ID,
        "pre_broker_order_id": V58_PRE_BROKER_ORDER_ID,
        "symbol": V58_SYMBOL,
        "candidate": V58_APPROVED_CANDIDATE,
        "approved_qty": _decimal_text(V58_APPROVED_QTY),
        "submitted_qty": "",
        "approved_max_notional": _decimal_text(V58_APPROVED_MAX_NOTIONAL),
        "estimated_submit_notional": "",
        "order_type": ORDER_TYPE_LIMIT,
        "side": SIDE_BUY,
        "time_in_force": TIME_IN_FORCE_GTC,
        "limit_price": "",
        "client_order_id": client_order_id,
        "submit_attempt_count": 0,
        "cancel_attempt_count": 0,
        "paper_submit_authorized": bool(paper_submit_authorized),
        "paper_cancel_authorized": bool(paper_submit_authorized),
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "broker_read_observed": False,
        "operator_preflight": dict(preflight),
        "expected_paper_account_id_loaded": expected_paper_account_id_loaded,
        "submit_status": "not_attempted",
        "cancel_status": "not_attempted",
        "final_order_status": "",
        "reconciliation_status": "not_started",
        "outcome_classification": OUTCOME_BLOCKED_BEFORE_SUBMIT,
        "blockers": [],
        "labels": list(REQUIRED_LABELS),
        "next_operator_action": "",
        "submit_call_count_max": 1,
        "retry_submit_allowed": False,
        "second_order_submit_allowed": False,
        "replace_allowed": False,
        "close_or_liquidate_allowed": False,
        "profit_claim": "none",
    }


def _authorization_blockers(
    *,
    approval_packet: Mapping[str, Any],
    dry_run: Mapping[str, Any],
    approval_packet_path: Path,
    dry_run_path: Path,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not approval_packet:
        blockers.append("approval_packet_unreadable")
    if not dry_run:
        blockers.append("dry_run_unreadable")
    if blockers:
        return tuple(blockers)

    if _clean_text(approval_packet.get("required_operator_phrase")) != V58_AUTHORIZATION_TEXT:
        blockers.append("approved_authorization_text_mismatch")
    if _clean_text(approval_packet.get("approval_packet_status")) != "ready_for_operator_review":
        blockers.append("approval_packet_not_ready_for_operator_review")
    if _clean_text(approval_packet.get("approval_state")) != "not_authorized":
        blockers.append("approval_packet_state_not_not_authorized")
    if _clean_text(dry_run.get("dry_run_status")) != "blocked_not_authorized":
        blockers.append("dry_run_status_not_blocked_not_authorized")
    if _clean_text(dry_run.get("approval_state")) != "not_authorized":
        blockers.append("dry_run_approval_state_not_not_authorized")

    _require_text_field(
        blockers,
        approval_packet,
        "dry_run_id",
        V58_DRY_RUN_ID,
        "approval_packet_dry_run_id_mismatch",
    )
    _require_text_field(
        blockers,
        dry_run,
        "dry_run_id",
        V58_DRY_RUN_ID,
        "dry_run_id_mismatch",
    )
    _require_text_field(
        blockers,
        approval_packet,
        "pre_broker_order_id",
        V58_PRE_BROKER_ORDER_ID,
        "approval_packet_pre_broker_order_id_mismatch",
    )
    _require_text_field(
        blockers,
        dry_run,
        "pre_broker_order_id",
        V58_PRE_BROKER_ORDER_ID,
        "dry_run_pre_broker_order_id_mismatch",
    )
    _require_text_field(
        blockers,
        approval_packet,
        "symbol",
        V58_SYMBOL,
        "approval_packet_symbol_not_BTCUSD",
    )
    _require_text_field(
        blockers,
        dry_run,
        "symbol",
        V58_SYMBOL,
        "dry_run_symbol_not_BTCUSD",
    )
    _require_text_field(
        blockers,
        approval_packet,
        "selected_candidate_id",
        V58_APPROVED_CANDIDATE,
        "approval_packet_candidate_mismatch",
    )
    _require_text_field(
        blockers,
        dry_run,
        "selected_candidate_id",
        V58_APPROVED_CANDIDATE,
        "dry_run_candidate_mismatch",
    )
    _require_text_field(
        blockers,
        approval_packet,
        "intended_action",
        "buy_preview",
        "approval_packet_intended_action_not_buy_preview",
    )
    _require_text_field(
        blockers,
        dry_run,
        "intended_action",
        "buy_preview",
        "dry_run_intended_action_not_buy_preview",
    )

    qty = _positive_decimal_or_none(approval_packet.get("exact_qty"))
    if qty is None:
        qty = _positive_decimal_or_none(approval_packet.get("rounded_qty"))
    dry_qty = _positive_decimal_or_none(dry_run.get("rounded_qty"))
    if qty != V58_APPROVED_QTY:
        blockers.append("approval_packet_qty_mismatch")
    if dry_qty != V58_APPROVED_QTY:
        blockers.append("dry_run_qty_mismatch")
    if qty is not None and qty > V58_APPROVED_QTY:
        blockers.append("approval_packet_qty_exceeds_approved_qty")
    if dry_qty is not None and dry_qty > V58_APPROVED_QTY:
        blockers.append("dry_run_qty_exceeds_approved_qty")

    cap = _positive_decimal_or_none(approval_packet.get("exact_cap"))
    if cap is None:
        cap = _positive_decimal_or_none(approval_packet.get("preview_cap"))
    dry_cap = _positive_decimal_or_none(dry_run.get("preview_cap"))
    if cap != V58_APPROVED_MAX_NOTIONAL:
        blockers.append("approval_packet_cap_mismatch")
    if dry_cap != V58_APPROVED_MAX_NOTIONAL:
        blockers.append("dry_run_cap_mismatch")
    preview_value = _positive_decimal_or_none(
        approval_packet.get("exact_preview_value")
    ) or _positive_decimal_or_none(approval_packet.get("derived_preview_value"))
    dry_preview_value = _positive_decimal_or_none(dry_run.get("derived_preview_value"))
    if preview_value is not None and preview_value > V58_APPROVED_MAX_NOTIONAL:
        blockers.append("approval_packet_preview_value_exceeds_cap")
    if dry_preview_value is not None and dry_preview_value > V58_APPROVED_MAX_NOTIONAL:
        blockers.append("dry_run_preview_value_exceeds_cap")

    packet_dry_run_source = Path(_clean_text(approval_packet.get("dry_run_source")))
    if packet_dry_run_source and packet_dry_run_source != dry_run_path:
        if packet_dry_run_source.as_posix() != dry_run_path.as_posix():
            blockers.append("approval_packet_dry_run_source_mismatch")

    for source, source_name in (
        (approval_packet, "approval_packet"),
        (dry_run, "dry_run"),
    ):
        if _text_list(source.get("blockers")):
            blockers.append(f"{source_name}_contains_source_blockers")
        for field in (
            "broker_action_permitted",
            "paper_submit_authorized",
            "paper_submit_performed",
            "paper_cancel_authorized",
            "paper_cancel_performed",
            "broker_mutation_performed",
            "broker_read_performed_current_run",
            "live_mutation_performed",
            "live_endpoint_touched",
            "credential_values_exposed",
            "network_access_attempted",
        ):
            if _bool(source.get(field)):
                blockers.append(f"{source_name}_{field}_true")
        if _clean_text(source.get("profit_claim")) != "none":
            blockers.append(f"{source_name}_profit_claim_not_none")

    if not approval_packet_path.is_file():
        blockers.append("approval_packet_source_not_file")
    if not dry_run_path.is_file():
        blockers.append("dry_run_source_not_file")
    return _dedupe(blockers)


def _require_text_field(
    blockers: list[str],
    row: Mapping[str, Any],
    field_name: str,
    expected: str,
    blocker: str,
) -> None:
    if _clean_text(row.get(field_name)) != expected:
        blockers.append(blocker)


def _environment_preflight(
    env: Mapping[str, str] | None = None,
    *,
    expected_paper_account_id: str = "",
) -> dict[str, bool]:
    source = _env_mapping(env)
    app_profile = source.get("APP_PROFILE", "").strip().lower()
    effective_paper_base_url = _effective_paper_base_url(source)
    credential_state = {
        f"{name}_present": bool(source.get(name, "").strip())
        for name in _CREDENTIAL_NAMES
    }
    paper_credentials_present = bool(
        _first_nonempty(source, ("ALPACA_API_KEY", "APCA_API_KEY_ID"))
    ) and bool(_first_nonempty(source, _SECRET_KEY_CANDIDATES))
    return {
        "APP_PROFILE_is_paper": app_profile == "paper",
        "APP_PROFILE_is_live": app_profile == "live",
        **credential_state,
        "paper_credentials_present": paper_credentials_present,
        "expected_paper_account_id_loaded": bool(expected_paper_account_id),
        "paper_endpoint_exact_match_indicator": (
            _normalize_endpoint(effective_paper_base_url)
            == _normalize_endpoint(DEFAULT_ALPACA_PAPER_BASE_URL)
        ),
        "live_endpoint_indicator": _live_endpoint_indicator(source),
    }


def _environment_gate_blockers(
    preflight: Mapping[str, bool],
    *,
    authorized: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not authorized:
        blockers.append("v5_8_paper_submit_authorization_switch_required")
    if preflight.get("APP_PROFILE_is_live") is True:
        blockers.append("APP_PROFILE_live_blocked")
    if preflight.get("live_endpoint_indicator") is True:
        blockers.append("live_endpoint_indicator")
    if preflight.get("APP_PROFILE_is_paper") is not True:
        blockers.append("APP_PROFILE_paper_required")
    if preflight.get("paper_endpoint_exact_match_indicator") is not True:
        blockers.append("paper_endpoint_exact_match_required")
    if preflight.get("paper_credentials_present") is not True:
        blockers.append("paper_credentials_required")
    if preflight.get("expected_paper_account_id_loaded") is not True:
        blockers.append("expected_paper_account_id_required")
    return _dedupe(blockers)


def _build_broker_client(
    env: Mapping[str, str],
    broker_client_factory: BrokerClientFactory | None,
) -> dict[str, Any]:
    try:
        config = AlpacaPaperConfig(
            app_profile=env.get("APP_PROFILE", ""),
            alpaca_api_key=_first_nonempty(env, ("ALPACA_API_KEY", "APCA_API_KEY_ID")),
            alpaca_secret_key=_first_nonempty(env, _SECRET_KEY_CANDIDATES),
            alpaca_paper_base_url=_effective_paper_base_url(env),
        )
        client = (broker_client_factory or AlpacaSdkClient)(config)
    except Exception as exc:  # noqa: BLE001 - certification fails closed.
        return {"client": None, "error": _safe_exception_message(exc)}
    return {"client": client, "error": ""}


def _read_account(client: Any) -> dict[str, Any]:
    try:
        return {"account": _account_payload(client.get_account()), "error": ""}
    except Exception as exc:  # noqa: BLE001 - certification fails closed.
        return {"account": {}, "error": _safe_exception_message(exc)}


def _read_asset(client: Any, symbol: str) -> dict[str, Any]:
    raw = _raw_trading_client(client)
    method = getattr(raw, "get_asset", None)
    if callable(method):
        try:
            return {"asset": _asset_payload(method(symbol)), "error": ""}
        except Exception as exc:  # noqa: BLE001 - certification fails closed.
            return {"asset": {}, "error": _safe_exception_message(exc)}
    for method_name in ("list_assets", "get_all_assets", "get_assets"):
        method = getattr(client, method_name, None)
        if not callable(method):
            method = getattr(raw, method_name, None)
        if callable(method):
            try:
                for asset in method():
                    payload = _asset_payload(asset)
                    if _normalize_symbol_text(payload.get("symbol")) == symbol:
                        return {"asset": payload, "error": ""}
            except Exception as exc:  # noqa: BLE001 - certification fails closed.
                return {"asset": {}, "error": _safe_exception_message(exc)}
    return {"asset": {}, "error": "paper_client_asset_read_unavailable"}


def _read_orders(client: Any, *, status_filter: str, symbol: str) -> dict[str, Any]:
    try:
        orders = client.get_orders(
            AlpacaRecentOrderQuery(
                status_filter=status_filter,
                limit=100,
                symbol_filter=symbol,
            )
        )
    except Exception as exc:  # noqa: BLE001 - certification fails closed.
        return {"orders": [], "error": _safe_exception_message(exc)}
    return {"orders": [_order_summary(order) for order in orders], "error": ""}


def _read_positions(client: Any) -> dict[str, Any]:
    try:
        positions = client.get_positions()
    except Exception as exc:  # noqa: BLE001 - certification fails closed.
        return {"positions": [], "error": _safe_exception_message(exc)}
    return {"positions": [_position_summary(position) for position in positions], "error": ""}


def _read_gate_blockers(
    *,
    account: Mapping[str, Any],
    account_error: str,
    expected_paper_account_id: str,
    asset: Mapping[str, Any],
    asset_error: str,
    open_orders: Sequence[Mapping[str, Any]],
    open_order_error: str,
    positions: Sequence[Mapping[str, Any]],
    position_error: str,
    existing_order: Mapping[str, Any],
    client_order_id: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if account_error:
        blockers.append("paper_account_read_failed")
    elif not account:
        blockers.append("paper_account_status_unobserved")
    else:
        if not _expected_account_matched(account, expected_paper_account_id):
            blockers.append("paper_account_expected_id_mismatch")
        status = _normalized_enum_text(account.get("status"))
        if not status:
            blockers.append("paper_account_status_unobserved")
        elif status not in {"active", "account_active"}:
            blockers.append("paper_account_not_active")
        if _bool(account.get("trading_blocked")) or _bool(account.get("account_blocked")):
            blockers.append("paper_account_trading_blocked")

    if asset_error:
        blockers.append("BTCUSD_asset_read_failed")
    elif not asset:
        blockers.append("BTCUSD_asset_not_observed")
    else:
        if _normalize_symbol_text(asset.get("symbol")) != V58_SYMBOL:
            blockers.append("asset_symbol_not_BTCUSD")
        if _normalized_enum_text(asset.get("asset_class") or asset.get("class")) != "crypto":
            blockers.append("asset_class_not_crypto")
        if _bool_field(asset, "tradable") is not True:
            blockers.append("BTCUSD_asset_not_tradable")
        asset_status = _normalized_enum_text(asset.get("status"))
        if asset_status and asset_status not in {"active"}:
            blockers.append("BTCUSD_asset_not_active")

    if open_order_error:
        blockers.append("BTCUSD_open_order_read_failed")
    for order in open_orders:
        if _order_symbol(order) != V58_SYMBOL:
            continue
        status = _order_status(order)
        if status in _OPEN_STATUSES or status not in _TERMINAL_STATUSES:
            if _clean_text(order.get("client_order_id")) == client_order_id:
                blockers.append("existing_v5_8_client_order_id_order_exists")
            else:
                blockers.append("existing_conflicting_BTCUSD_open_order_exists")

    if existing_order:
        status = _order_status(existing_order)
        if status not in _TERMINAL_STATUSES:
            blockers.append("existing_v5_8_client_order_id_order_exists")
        else:
            blockers.append("prior_v5_8_client_order_id_order_exists")

    if position_error:
        blockers.append("BTCUSD_position_read_failed")
    for position in positions:
        if _position_symbol(position) != V58_SYMBOL:
            continue
        qty = _decimal_or_none(position.get("qty")) or Decimal("0")
        if qty != Decimal("0"):
            blockers.append("existing_BTCUSD_position_ambiguous")
    return _dedupe(blockers)


def _build_order_design(dry_run: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    blockers: list[str] = []
    reference_price = _positive_decimal_or_none(dry_run.get("latest_price"))
    if reference_price is None:
        blockers.append("dry_run_latest_price_missing")
        reference_price = Decimal("0")
    limit_price = (reference_price * LIMIT_DISCOUNT).quantize(
        PRICE_QUANTUM,
        rounding=ROUND_DOWN,
    )
    estimated_notional = (limit_price * V58_APPROVED_QTY).quantize(
        Decimal("0.000000000001"),
        rounding=ROUND_DOWN,
    )
    if limit_price <= Decimal("0"):
        blockers.append("limit_price_not_positive")
    if V58_APPROVED_QTY > V58_APPROVED_QTY:
        blockers.append("submitted_qty_exceeds_approved_qty")
    if estimated_notional > V58_APPROVED_MAX_NOTIONAL:
        blockers.append("estimated_submit_notional_exceeds_approved_max")
    return (
        {
            "reference_price": _decimal_text(reference_price),
            "reference_price_source": "v5_6_dry_run_latest_price",
            "limit_discount": _decimal_text(LIMIT_DISCOUNT),
            "limit_price": _decimal_text(limit_price),
            "quantity": _decimal_text(V58_APPROVED_QTY),
            "estimated_submit_notional": _decimal_text(estimated_notional),
            "approved_max_notional": _decimal_text(V58_APPROVED_MAX_NOTIONAL),
            "order_type": ORDER_TYPE_LIMIT,
            "side": SIDE_BUY,
            "time_in_force": TIME_IN_FORCE_GTC,
        },
        _dedupe(blockers),
    )


def _submit_cancel_reconcile(
    *,
    client: Any,
    request: AlpacaOrderRequest,
    poll_attempts: int,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    cancel_result: dict[str, Any] = {
        "cancel_attempted": False,
        "cancel_confirmed": False,
        "cancel_status": "not_attempted",
        "cancel_ambiguous": False,
    }
    try:
        submit_response = client.submit_order(request)
        submitted_order = _order_summary(submit_response)
        submit_result = {
            "submit_attempted": True,
            "submit_call_count": 1,
            "submit_status": _order_status(submitted_order) or "accepted",
            "submit_error": "",
            "submit_error_type": "",
            "submitted_order": submitted_order,
        }
    except Exception as exc:  # noqa: BLE001 - submit may be ambiguous.
        submit_result = {
            "submit_attempted": True,
            "submit_call_count": 1,
            "submit_status": "ambiguous",
            "submit_error": _safe_exception_message(exc),
            "submit_error_type": exc.__class__.__name__,
            "submitted_order": {},
        }
        latest_after_error = _lookup_by_client_order_id(
            client,
            client_order_id=request.client_order_id,
            symbol=request.symbol,
        )
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest_after_error,
            outcome=OUTCOME_SUBMIT_AMBIGUOUS,
            blocker="submit_ambiguous_no_retry",
            next_action="operator_reconcile_ambiguous_submit_before_any_future_order",
        )

    latest = _lookup_by_client_order_id(
        client,
        client_order_id=request.client_order_id,
        symbol=request.symbol,
    ) or _mapping(submit_result.get("submitted_order"))
    status = _order_status(latest)
    if not latest:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order={},
            outcome=OUTCOME_RECONCILIATION_AMBIGUOUS,
            blocker="submitted_order_not_reconciled_after_single_submit_call",
            next_action="operator_reconcile_unresolved_v5_8_order_before_any_future_order",
        )
    if status == "rejected":
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_SUBMIT_REJECTED,
            blocker="submit_rejected_no_retry",
            next_action="review_rejected_v5_8_submit_before_any_future_order",
        )
    if status == "filled":
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_SUBMITTED_ALREADY_FILLED,
            blocker="filled_before_cancel_no_close_or_liquidate_authorized",
            next_action="operator_review_unexpected_fill_before_cleanup_authorization",
        )
    if status in _TERMINAL_STATUSES:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=_classify_final_order(latest, cancel_ambiguous=False),
            blocker="none",
            next_action="review_terminal_v5_8_order_artifacts",
        )
    if status not in _CANCELABLE_STATUSES:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_RECONCILIATION_AMBIGUOUS,
            blocker="submitted_order_not_cancelable",
            next_action="operator_reconcile_unresolved_v5_8_order_before_any_future_order",
        )

    order_id = _clean_text(latest.get("order_id") or latest.get("id"))
    if not order_id:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_RECONCILIATION_AMBIGUOUS,
            blocker="submitted_order_id_missing_for_same_order_cancel",
            next_action="operator_reconcile_unresolved_v5_8_order_before_any_future_order",
        )

    cancel_ambiguous = False
    try:
        cancel_response = _request_order_cancellation(client, order_id)
        cancel_response_payload = _generic_payload(cancel_response)
        cancel_status = _normalized_enum_text(cancel_response_payload.get("status"))
    except Exception as exc:  # noqa: BLE001 - cancel may be ambiguous.
        cancel_ambiguous = True
        cancel_response_payload = {
            "cancel_error": _safe_exception_message(exc),
            "cancel_error_type": exc.__class__.__name__,
        }
        cancel_status = "ambiguous"
    cancel_result = {
        "cancel_attempted": True,
        "cancel_confirmed": False,
        "cancel_status": cancel_status or ("ambiguous" if cancel_ambiguous else "requested"),
        "cancel_ambiguous": cancel_ambiguous,
        "cancel_response": cancel_response_payload,
        "cancel_target_order_id": order_id,
        "cancel_target_client_order_id": request.client_order_id,
    }
    final_order = _poll_lookup_by_client_order_id(
        client,
        client_order_id=request.client_order_id,
        symbol=request.symbol,
        attempts=poll_attempts,
        interval_seconds=poll_interval_seconds,
    ) or latest
    if cancel_ambiguous:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=final_order,
            outcome=OUTCOME_CANCEL_AMBIGUOUS,
            blocker="cancel_ambiguous_no_second_submit",
            next_action="operator_reconcile_cancel_ambiguous_v5_8_order",
        )
    final_outcome = _classify_final_order(final_order, cancel_ambiguous=False)
    cancel_result = {
        **cancel_result,
        "cancel_confirmed": final_outcome == OUTCOME_SUBMITTED_CANCEL_CONFIRMED,
    }
    return _lifecycle_result(
        submit_result=submit_result,
        cancel_result=cancel_result,
        final_order=final_order,
        outcome=final_outcome,
        blocker="none"
        if final_outcome != OUTCOME_RECONCILIATION_AMBIGUOUS
        else "order_not_terminal_after_cancel_reconciliation",
        next_action=(
            "review_v5_8_certification_artifacts_before_any_future_order"
            if final_outcome != OUTCOME_RECONCILIATION_AMBIGUOUS
            else "operator_reconcile_unresolved_v5_8_order_before_any_future_order"
        ),
    )


def _lifecycle_result(
    *,
    submit_result: Mapping[str, Any],
    cancel_result: Mapping[str, Any],
    final_order: Mapping[str, Any],
    outcome: str,
    blocker: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "submit_result": dict(submit_result),
        "cancel_result": dict(cancel_result),
        "final_order": dict(final_order),
        "outcome_classification": outcome,
        "blocker": blocker,
        "next_operator_action": next_action,
    }


def _finalize_result(
    result: Mapping[str, Any],
    *,
    outcome_classification: str,
    blockers: Sequence[str],
    next_operator_action: str,
    write_artifacts: bool,
) -> dict[str, Any]:
    submit_result = _mapping(result.get("submit_result"))
    cancel_result = _mapping(result.get("cancel_result"))
    final_order = _mapping(result.get("final_order"))
    order_design = _mapping(result.get("order_design"))
    submit_attempt_count = int(
        _decimal_or_none(submit_result.get("submit_call_count")) or Decimal("0")
    )
    cancel_attempt_count = 1 if cancel_result.get("cancel_attempted") is True else 0
    paper_submit_performed = submit_attempt_count > 0
    paper_cancel_performed = cancel_attempt_count > 0
    finalized = {
        **result,
        "submitted_qty": _decimal_text(V58_APPROVED_QTY)
        if paper_submit_performed
        else "",
        "estimated_submit_notional": _clean_text(
            order_design.get("estimated_submit_notional")
        ),
        "limit_price": _clean_text(order_design.get("limit_price")),
        "submit_attempt_count": submit_attempt_count,
        "cancel_attempt_count": cancel_attempt_count,
        "paper_submit_performed": paper_submit_performed,
        "paper_cancel_performed": paper_cancel_performed,
        "broker_mutation_performed": paper_submit_performed or paper_cancel_performed,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "submit_status": _clean_text(
            submit_result.get("submit_status") or result.get("submit_status")
        ),
        "cancel_status": _clean_text(
            cancel_result.get("cancel_status") or result.get("cancel_status")
        ),
        "final_order_status": _order_status(final_order),
        "reconciliation_status": _reconciliation_status(
            outcome_classification,
            final_order,
        ),
        "outcome_classification": outcome_classification,
        "blockers": [blocker for blocker in _dedupe(blockers) if blocker != "none"],
        "labels": list(_dedupe((*_text_list(result.get("labels")), *REQUIRED_LABELS))),
        "next_operator_action": next_operator_action,
        "unexpected_fill_or_position_impact": _filled_quantity(final_order)
        > Decimal("0"),
        "residual_open_order": _residual_open_order(final_order),
    }
    if write_artifacts:
        finalized["artifact_paths"] = _write_artifacts(
            Path(_clean_text(finalized.get("output_root"))),
            finalized,
        )
    return _json_safe(finalized)


def _reconciliation_status(outcome: str, final_order: Mapping[str, Any]) -> str:
    if outcome in {
        OUTCOME_SUBMITTED_CANCEL_CONFIRMED,
        OUTCOME_SUBMITTED_ALREADY_FILLED,
        OUTCOME_SUBMIT_REJECTED,
    }:
        return "reconciled"
    if outcome == OUTCOME_BLOCKED_BEFORE_SUBMIT:
        return "not_started"
    if final_order:
        return "ambiguous"
    return "unreconciled"


def _residual_open_order(order: Mapping[str, Any]) -> bool:
    status = _order_status(order)
    return bool(order) and status not in _TERMINAL_STATUSES


def _write_artifacts(root: Path, result: Mapping[str, Any]) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    certification_result_json = root / "certification_result.json"
    certification_result_md = root / "certification_result.md"
    operating_record = root / "operating_record.jsonl"
    manifest = root / "manifest.json"
    paths = {
        "certification_result_json": str(certification_result_json),
        "certification_result_md": str(certification_result_md),
        "operating_record": str(operating_record),
        "manifest": str(manifest),
    }
    result_with_paths = {**result, "artifact_paths": paths}
    _write_json(certification_result_json, result_with_paths)
    certification_result_md.write_text(
        _render_certification_markdown(result_with_paths) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    operating_record.write_text(
        json.dumps(_operating_record(result_with_paths), sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest_payload = {
        "schema_version": CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_SCHEMA_VERSION,
        "as_of": result.get("as_of", ""),
        "artifact_root": str(root),
        "generated_under_runs": _generated_under_runs(root),
        "credential_values_redacted": True,
        "required_artifacts": {
            "certification_result_json": _artifact_entry(certification_result_json),
            "certification_result_md": _artifact_entry(certification_result_md),
            "operating_record": _artifact_entry(operating_record),
        },
        "input_artifacts": {
            "approval_packet": _artifact_reference(
                _clean_text(result.get("approval_packet_source"))
            ),
            "paper_oms_dry_run": _artifact_reference(
                _clean_text(result.get("dry_run_source"))
            ),
        },
        "paper_submit_authorized": result.get("paper_submit_authorized") is True,
        "paper_submit_performed": result.get("paper_submit_performed") is True,
        "broker_mutation_performed": result.get("broker_mutation_performed") is True,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "outcome_classification": result.get("outcome_classification", ""),
        "labels": list(_text_list(result.get("labels"))),
    }
    _write_json(manifest, manifest_payload)
    return paths


def _render_certification_markdown(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Crypto Paper Submit/Cancel Certification",
            "",
            f"- Outcome: `{result.get('outcome_classification', '')}`",
            f"- Blockers: `{','.join(_text_list(result.get('blockers')))}`",
            f"- Symbol: `{result.get('symbol', '')}`",
            f"- Qty: `{result.get('submitted_qty') or result.get('approved_qty', '')}`",
            f"- Limit price: `{result.get('limit_price', '')}`",
            f"- Estimated notional: `{result.get('estimated_submit_notional', '')}`",
            f"- Client order id: `{result.get('client_order_id', '')}`",
            f"- Submit/cancel attempts: `{result.get('submit_attempt_count')}` / `{result.get('cancel_attempt_count')}`",
            f"- Submit/cancel status: `{result.get('submit_status', '')}` / `{result.get('cancel_status', '')}`",
            f"- Final order status: `{result.get('final_order_status', '')}`",
            f"- Reconciliation status: `{result.get('reconciliation_status', '')}`",
            f"- Broker read observed: `{result.get('broker_read_observed')}`",
            f"- Paper submit performed: `{result.get('paper_submit_performed')}`",
            f"- Broker mutation performed: `{result.get('broker_mutation_performed')}`",
            f"- Live endpoint touched: `{result.get('live_endpoint_touched')}`",
            f"- Credential values exposed: `{result.get('credential_values_exposed')}`",
            f"- Next operator action: `{result.get('next_operator_action', '')}`",
            "",
            "Labels: " + ", ".join(_text_list(result.get("labels"))),
        ]
    )


def _operating_record(result: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "schema_version",
        "as_of",
        "approval_packet_source",
        "dry_run_id",
        "pre_broker_order_id",
        "symbol",
        "approved_qty",
        "submitted_qty",
        "approved_max_notional",
        "estimated_submit_notional",
        "order_type",
        "side",
        "time_in_force",
        "limit_price",
        "client_order_id",
        "submit_attempt_count",
        "cancel_attempt_count",
        "paper_submit_authorized",
        "paper_submit_performed",
        "paper_cancel_performed",
        "broker_mutation_performed",
        "live_mutation_performed",
        "live_endpoint_touched",
        "credential_values_exposed",
        "broker_read_observed",
        "submit_status",
        "cancel_status",
        "final_order_status",
        "reconciliation_status",
        "outcome_classification",
        "blockers",
        "labels",
        "next_operator_action",
    )
    return {field: _json_safe(result.get(field)) for field in fields}


def _artifact_reference(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    return {
        "path": str(path),
        "sha256": _file_sha256(path) if path.is_file() else "",
    }


def _artifact_entry(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "size": path.stat().st_size,
    }


def _lookup_by_client_order_id(
    client: Any,
    *,
    client_order_id: str,
    symbol: str,
) -> dict[str, Any]:
    raw = _raw_trading_client(client)
    for method_name in ("get_order_by_client_id", "get_order_by_client_order_id"):
        method = getattr(raw, method_name, None)
        if callable(method):
            try:
                order = method(client_order_id)
            except Exception:
                order = None
            if order is not None:
                return _order_summary(order)
    try:
        orders = client.get_orders(
            AlpacaRecentOrderQuery(status_filter="all", limit=100, symbol_filter=symbol)
        )
    except Exception:
        return {}
    matches = [
        _order_summary(order)
        for order in orders
        if _clean_text(_field(order, "client_order_id")) == client_order_id
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
) -> dict[str, Any]:
    checked_attempts = max(1, int(attempts))
    checked_interval = max(0.0, float(interval_seconds))
    latest: dict[str, Any] = {}
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
    raw = _raw_trading_client(client)
    for method_name in ("cancel_order_by_id", "cancel_order"):
        method = getattr(raw, method_name, None)
        if callable(method):
            return method(order_id)
    raise RuntimeError("paper client does not expose same-order cancellation")


def _raw_trading_client(client: Any) -> Any:
    raw = getattr(client, "raw_trading_client", None)
    return raw if raw is not None else client


def _classify_final_order(order: Mapping[str, Any], *, cancel_ambiguous: bool) -> str:
    status = _order_status(order)
    if status == "rejected":
        return OUTCOME_SUBMIT_REJECTED
    if status == "filled":
        return OUTCOME_SUBMITTED_ALREADY_FILLED
    if status in _CANCELLED_STATUSES:
        if cancel_ambiguous:
            return OUTCOME_CANCEL_AMBIGUOUS
        return OUTCOME_SUBMITTED_CANCEL_CONFIRMED
    return OUTCOME_RECONCILIATION_AMBIGUOUS


def _request_fields(request: AlpacaOrderRequest) -> dict[str, str]:
    return {
        "asset_class": request.asset_class,
        "client_order_id": request.client_order_id,
        "symbol": request.symbol,
        "side": request.side,
        "order_type": request.order_type,
        "time_in_force": request.time_in_force,
        "quantity": "" if request.qty is None else str(request.qty),
        "notional": "" if request.notional is None else str(request.notional),
        "limit_price": "" if request.limit_price is None else str(request.limit_price),
    }


def _account_payload(account: object) -> dict[str, Any]:
    data = _generic_payload(account)
    return {
        "account_id": _clean_text(_first_present(data, "account_id", "id")),
        "id": _clean_text(_first_present(data, "id", "account_id")),
        "account_number": _clean_text(data.get("account_number")),
        "status": _clean_text(data.get("status")),
        "currency": _clean_text(data.get("currency")),
        "trading_blocked": _bool(data.get("trading_blocked")),
        "account_blocked": _bool(data.get("account_blocked")),
    }


def _asset_payload(asset: object) -> dict[str, Any]:
    data = _generic_payload(asset)
    return {
        "symbol": _normalize_symbol_text(data.get("symbol")),
        "asset_class": _normalized_enum_text(
            _first_present(data, "asset_class", "class")
        ),
        "status": _normalized_enum_text(data.get("status")),
        "tradable": _bool_field(data, "tradable"),
        "fractionable": _bool_field(data, "fractionable"),
        "min_order_size": _clean_text(data.get("min_order_size")),
        "min_trade_increment": _clean_text(data.get("min_trade_increment")),
        "min_order_increment": _clean_text(data.get("min_order_increment")),
        "min_notional": _clean_text(
            _first_present(data, "min_notional", "min_order_notional")
        ),
    }


def _position_summary(position: object) -> dict[str, Any]:
    data = _generic_payload(position)
    return {
        "symbol": _normalize_symbol_text(data.get("symbol")),
        "qty": _decimal_text(_decimal_or_none(_first_present(data, "qty", "quantity"))),
        "market_value": _decimal_text(_decimal_or_none(data.get("market_value"))),
        "average_entry_price": _decimal_text(
            _decimal_or_none(_first_present(data, "average_entry_price", "avg_entry_price"))
        ),
        "side": _clean_text(data.get("side")),
    }


def _residual_position(client: Any, symbol: str) -> dict[str, Any]:
    try:
        positions = tuple(_position_summary(position) for position in client.get_positions())
    except Exception as exc:  # noqa: BLE001 - receipt only.
        return {"position_read_error": _safe_exception_message(exc)}
    matches = [position for position in positions if _position_symbol(position) == symbol]
    return {
        "selected_symbol_position_observed": bool(matches),
        "selected_symbol_positions": matches,
    }


def _order_summary(order: object) -> dict[str, Any]:
    data = _generic_payload(order)
    return {
        "order_id": _clean_text(_first_present(data, "id", "order_id")),
        "id": _clean_text(_first_present(data, "id", "order_id")),
        "client_order_id": _clean_text(data.get("client_order_id")),
        "symbol": _normalize_symbol_text(data.get("symbol")),
        "side": _clean_text(data.get("side")).lower(),
        "asset_class": _normalized_enum_text(data.get("asset_class")),
        "order_type": _normalized_enum_text(_first_present(data, "type", "order_type")),
        "time_in_force": _normalized_enum_text(data.get("time_in_force")),
        "status": _normalize_status(data.get("status")),
        "qty": _decimal_text(_decimal_or_none(_first_present(data, "qty", "quantity"))),
        "notional": _decimal_text(_decimal_or_none(data.get("notional"))),
        "limit_price": _decimal_text(_decimal_or_none(data.get("limit_price"))),
        "filled_qty": _decimal_text(
            _decimal_or_none(_first_present(data, "filled_qty", "filled_quantity"))
        ),
        "filled_avg_price": _decimal_text(
            _decimal_or_none(_first_present(data, "filled_avg_price", "avg_fill_price"))
        ),
        "submitted_at": _time_text(_first_present(data, "submitted_at", "created_at")),
        "filled_at": _time_text(data.get("filled_at")),
        "canceled_at": _time_text(_first_present(data, "canceled_at", "cancelled_at")),
        "reject_reason": _clean_text(_first_present(data, "reject_reason", "reason")),
    }


def _approval_packet_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _clean_text(packet.get("schema_version")),
        "approval_packet_status": _clean_text(packet.get("approval_packet_status")),
        "approval_state": _clean_text(packet.get("approval_state")),
        "dry_run_id": _clean_text(packet.get("dry_run_id")),
        "pre_broker_order_id": _clean_text(packet.get("pre_broker_order_id")),
        "symbol": _clean_text(packet.get("symbol")),
        "exact_qty": _clean_text(packet.get("exact_qty")),
        "exact_cap": _clean_text(packet.get("exact_cap")),
        "blockers": _text_list(packet.get("blockers")),
        "labels": _text_list(packet.get("labels")),
    }


def _dry_run_summary(dry_run: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _clean_text(dry_run.get("schema_version")),
        "dry_run_status": _clean_text(dry_run.get("dry_run_status")),
        "approval_state": _clean_text(dry_run.get("approval_state")),
        "dry_run_id": _clean_text(dry_run.get("dry_run_id")),
        "pre_broker_order_id": _clean_text(dry_run.get("pre_broker_order_id")),
        "symbol": _clean_text(dry_run.get("symbol")),
        "rounded_qty": _clean_text(dry_run.get("rounded_qty")),
        "preview_cap": _clean_text(dry_run.get("preview_cap")),
        "latest_price": _clean_text(dry_run.get("latest_price")),
        "blockers": _text_list(dry_run.get("blockers")),
        "labels": _text_list(dry_run.get("labels")),
    }


def _expected_account_matched(
    account: Mapping[str, Any],
    expected_paper_account_id: str,
) -> bool:
    return bool(
        expected_paper_account_id
        and expected_paper_account_id in _account_identity_values(account)
    )


def _account_identity_values(account: Mapping[str, Any]) -> set[str]:
    return {
        text
        for text in (
            _clean_text(account.get("account_id")),
            _clean_text(account.get("id")),
            _clean_text(account.get("account_number")),
        )
        if text
    }


def _order_status(order: Mapping[str, Any]) -> str:
    return _normalize_status(order.get("status"))


def _order_symbol(order: Mapping[str, Any]) -> str:
    return _normalize_symbol_text(order.get("symbol"))


def _position_symbol(position: Mapping[str, Any]) -> str:
    return _normalize_symbol_text(position.get("symbol"))


def _filled_quantity(order: Mapping[str, Any]) -> Decimal:
    return _decimal_or_none(order.get("filled_qty")) or Decimal("0")


def _normalize_status(value: object) -> str:
    return _normalized_enum_text(value)


def _normalized_enum_text(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    normalized = text.lower().replace(" ", "_")
    if "." in normalized:
        normalized = normalized.rsplit(".", 1)[-1]
    return normalized


def _normalize_symbol_text(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return text.replace("/", "").upper()


def _generic_payload(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return _allowed_payload_fields(value)
    dumped = _model_dump_payload(value)
    if dumped is not None:
        return dumped
    return {key: _json_safe(item) for key, item in _object_data(value).items()}


def _model_dump_payload(value: object) -> dict[str, Any] | None:
    model_dump = getattr(value, "model_dump", None)
    if not callable(model_dump):
        return None
    try:
        dumped = model_dump(mode="json")
    except TypeError:
        try:
            dumped = model_dump()
        except Exception:
            return None
    except Exception:
        return None
    if not isinstance(dumped, Mapping):
        return None
    return _allowed_payload_fields(dumped)


def _allowed_payload_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    allowed: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        field = _OBJECT_PAYLOAD_FIELD_LOOKUP.get(_payload_field_lookup_key(key))
        if field is None:
            continue
        allowed[field] = _json_safe(value)
    return allowed


def _payload_field_lookup_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _object_data(value: object) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name in _OBJECT_PAYLOAD_FIELDS:
        try:
            item = getattr(value, name)
        except Exception:
            continue
        if item is None or callable(item):
            continue
        data[name] = item
    return data


def _read_json_mapping_safely(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: str | Path, field_name: str) -> Path:
    try:
        return Path(value)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be a filesystem path.") from exc


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO timestamp.") from exc
    else:
        raise ValidationError(f"{field_name} must be an ISO timestamp.")
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include timezone information.")
    return parsed.astimezone(UTC)


def _positive_decimal_or_none(value: object) -> Decimal | None:
    decimal_value = _decimal_or_none(value)
    if decimal_value is None or decimal_value <= Decimal("0"):
        return None
    return decimal_value


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value


def _decimal_text(value: Decimal | None) -> str:
    return "" if value is None else format(value.normalize(), "f")


def _clean_text(value: object) -> str:
    if value in (None, ""):
        return ""
    return str(value).strip()


def _time_text(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return _clean_text(value)


def _bool(value: object) -> bool:
    return value is True


def _bool_field(data: Mapping[str, Any], field_name: str) -> bool | None:
    value = data.get(field_name)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _text_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [text for item in value if (text := _clean_text(item))]
    text = _clean_text(value)
    return [text] if text else []


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _first_present(data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return None


def _env_mapping(env: Mapping[str, str] | None) -> dict[str, str]:
    source = os.environ if env is None else env
    return {str(key): str(value) for key, value in source.items()}


def _effective_paper_base_url(env: Mapping[str, str]) -> str:
    return env.get("ALPACA_PAPER_BASE_URL", "").strip() or DEFAULT_ALPACA_PAPER_BASE_URL


def _live_endpoint_indicator(env: Mapping[str, str]) -> bool:
    if env.get("APP_PROFILE", "").strip().lower() == "live":
        return True
    for name in ("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL"):
        value = env.get(name, "").strip().lower()
        if value and "api.alpaca.markets" in value and "paper" not in value:
            return True
    return False


def _normalize_endpoint(value: str) -> str:
    return value.strip().lower().rstrip("/")


def _first_nonempty(env: Mapping[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = env.get(name, "").strip()
        if value:
            return value
    return ""


def _safe_exception_message(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    if message is None:
        message = str(exc)
    sanitized = _URL_PATTERN.sub("<redacted_url>", str(message))
    sanitized = _BEARER_TOKEN_PATTERN.sub("Bearer <redacted>", sanitized)
    sanitized = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=<redacted>",
        sanitized,
    )
    sanitized = " ".join(sanitized.split())
    if len(sanitized) > _SAFE_MESSAGE_LIMIT:
        return f"{sanitized[:_SAFE_MESSAGE_LIMIT].rstrip()}..."
    return sanitized


def _generated_under_runs(path: Path) -> bool:
    return any(str(part).lower() == "runs" for part in path.parts)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _field(value: object, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name)
    return getattr(value, field_name, None)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crypto-paper-submit-cancel-certification",
        description="Run the explicit v5.8 BTCUSD paper submit/cancel certification.",
    )
    parser.add_argument(
        "--paper-submit-authorized",
        action="store_true",
        help="Explicit operator authorization for the one bounded submit/cancel.",
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_OUTPUT_ROOT),
        help="Ignored runtime artifact root under runs/.",
    )
    parser.add_argument(
        "--approval-packet-path",
        default=str(CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_APPROVAL_PACKET),
        help="Path to v5.7 paper_submit_approval_packet.json.",
    )
    parser.add_argument(
        "--dry-run-path",
        default=str(CRYPTO_PAPER_SUBMIT_CANCEL_CERTIFICATION_DEFAULT_DRY_RUN),
        help="Path to v5.6 paper_oms_dry_run.json.",
    )
    parser.add_argument("--timestamp", default="", help="Optional ISO timestamp.")
    parser.add_argument(
        "--expected-paper-account-id",
        default=None,
        help="Expected paper account id/number. Defaults to environment.",
    )
    parser.add_argument("--reconciliation-poll-attempts", type=int, default=3)
    parser.add_argument("--reconciliation-poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    result = run_crypto_paper_submit_cancel_certification(
        output_root=args.output_root,
        approval_packet_path=args.approval_packet_path,
        dry_run_path=args.dry_run_path,
        timestamp=args.timestamp or datetime.now(UTC),
        paper_submit_authorized=args.paper_submit_authorized,
        expected_paper_account_id=args.expected_paper_account_id,
        reconciliation_poll_attempts=args.reconciliation_poll_attempts,
        reconciliation_poll_interval_seconds=args.reconciliation_poll_interval_seconds,
    )
    if args.format == "json":
        print(json.dumps(result, sort_keys=True, indent=2))
    else:
        print(render_crypto_paper_submit_cancel_certification_text(result))
    outcome = _clean_text(result.get("outcome_classification"))
    if outcome == OUTCOME_BLOCKED_BEFORE_SUBMIT:
        return 2
    if outcome in {
        OUTCOME_SUBMIT_AMBIGUOUS,
        OUTCOME_CANCEL_AMBIGUOUS,
        OUTCOME_RECONCILIATION_AMBIGUOUS,
    }:
        return 3
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
