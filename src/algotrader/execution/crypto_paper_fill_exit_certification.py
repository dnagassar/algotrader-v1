"""v5.10 operator-authorized BTCUSD paper fill/exit certification.

This module performs at most one bounded BTCUSD Alpaca paper entry attempt and,
only when that entry creates an observed BTCUSD paper fill/position, at most one
bounded exit attempt for the resulting certification position.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.execution.alpaca_client import (
    AlpacaOrderRequest,
    AlpacaRecentOrderQuery,
)
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient


SCHEMA_VERSION = "v5_10_crypto_paper_fill_exit_certification_v1"
COMMAND_NAME = "run_crypto_paper_fill_exit_certification"
DEFAULT_OUTPUT_ROOT = Path("runs/crypto_paper_fill_exit_certification/latest")
DEFAULT_APPROVAL_PACKET_PATH = Path(
    "runs/crypto_paper_certification_ingestion/latest/"
    "paper_fill_experiment_approval_packet.json"
)
DEFAULT_PRIOR_CERTIFICATION_PATH = Path(
    "runs/crypto_paper_submit_cancel_certification/latest/certification_result.json"
)

V510_PRIOR_CERTIFICATION_ID = "v58_btcusd_submit_cancel_043554307307d348"
V510_PRIOR_CLIENT_ORDER_ID = "v58-btcusd-paper-cert-bfa9caadd6b57b19"
V510_SYMBOL = "BTCUSD"
V510_APPROVED_MAX_NOTIONAL = Decimal("25")
V510_REQUESTED_SCOPE = "bounded_btcusd_paper_fill_and_exit_certification"
V510_AUTHORIZATION_TEXT = (
    "Authorized for future v5.10 review: using prior_certification_id "
    "v58_btcusd_submit_cancel_043554307307d348 and prior client_order_id "
    "v58-btcusd-paper-cert-bfa9caadd6b57b19, authorize exactly one bounded "
    "BTCUSD Alpaca paper entry attempt and one bounded exit/flatten attempt "
    "for the resulting BTCUSD paper position, with max notional 25. This does "
    "not authorize live trading, additional orders, replacement, "
    "liquidation/close-all, capital changes, credential exposure, or paid "
    "services."
)

OUTCOME_FILLED_EXIT_CONFIRMED = "filled_exit_confirmed"
OUTCOME_PARTIAL_FILL_EXIT_CONFIRMED = "partial_fill_exit_confirmed"
OUTCOME_ENTRY_REJECTED_NO_POSITION = "entry_rejected_no_position"
OUTCOME_ENTRY_NO_FILL_NO_EXIT = "entry_no_fill_no_exit"
OUTCOME_ENTRY_AMBIGUOUS = "entry_ambiguous"
OUTCOME_EXIT_REJECTED_RESIDUAL_POSITION = "exit_rejected_residual_position"
OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION = "exit_ambiguous_residual_position"
OUTCOME_BLOCKED_BEFORE_ENTRY = "blocked_before_entry"
OUTCOME_BLOCKED_BEFORE_EXIT = "blocked_before_exit"
OUTCOME_CERTIFICATION_AMBIGUOUS = "certification_ambiguous"

REQUIRED_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
    "bounded_btcusd_paper_fill_exit_certification",
    "one_entry_attempt_only",
    "one_exit_attempt_only",
    "btcusd_only",
    "not_live",
    "operator_authorized_v5_10",
)

BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]

_CREDENTIAL_VARIABLE_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
_EXPECTED_ACCOUNT_VARIABLE_NAMES = (
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
)
_NETWORK_TEST_FLAG_NAMES = (
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
)
_TERMINAL_STATUSES = {"canceled", "cancelled", "expired", "filled", "rejected"}
_NO_FILL_TERMINAL_STATUSES = {"canceled", "cancelled", "expired", "rejected"}
_OPEN_OR_AMBIGUOUS_STATUSES = {
    "",
    "accepted",
    "accepted_for_bidding",
    "calculated",
    "held",
    "new",
    "partially_filled",
    "pending_cancel",
    "pending_new",
    "pending_replace",
    "stopped",
    "suspended",
}
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
    "tradable",
    "fractionable",
    "min_order_size",
    "min_trade_increment",
    "min_order_increment",
    "min_notional",
    "side",
    "type",
    "order_type",
    "time_in_force",
    "qty",
    "notional",
    "limit_price",
    "filled_qty",
    "filled_avg_price",
    "filled_at",
    "submitted_at",
    "created_at",
    "canceled_at",
    "cancelled_at",
    "client_order_id",
    "order_id",
    "reject_reason",
    "average_entry_price",
    "market_value",
    "bid_price",
    "ask_price",
    "price",
    "timestamp",
)
_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|secret(?:[_-]?key)?|token)\b"
    r"\s*[:=]\s*[^,\s;)]+"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
_SAFE_MESSAGE_LIMIT = 240


def run_crypto_paper_fill_exit_certification(
    *,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    approval_packet_path: str | Path = DEFAULT_APPROVAL_PACKET_PATH,
    prior_certification_path: str | Path = DEFAULT_PRIOR_CERTIFICATION_PATH,
    timestamp: datetime | str | None = None,
    env: Mapping[str, str] | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    paper_fill_exit_authorized: bool = False,
    expected_paper_account_id: str = "",
    reconciliation_poll_attempts: int = 3,
    reconciliation_poll_interval_seconds: float = 1.0,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    """Run the bounded v5.10 certification, failing closed before mutation."""

    output_root_path = _path(output_root, "output_root")
    approval_path = _path(approval_packet_path, "approval_packet_path")
    prior_path = _path(prior_certification_path, "prior_certification_path")
    as_of = _utc_datetime(timestamp or datetime.now(UTC), "timestamp")
    source_env = _normalized_paper_env(_env_mapping(env))
    expected_account_id = (
        _clean_text(expected_paper_account_id)
        or _first_nonempty(source_env, _EXPECTED_ACCOUNT_VARIABLE_NAMES)
    )
    entry_client_order_id, exit_client_order_id = deterministic_v510_client_order_ids(
        prior_certification_id=V510_PRIOR_CERTIFICATION_ID,
        prior_client_order_id=V510_PRIOR_CLIENT_ORDER_ID,
    )
    approval_packet = _read_json_mapping_safely(approval_path)
    prior_certification = _read_json_mapping_safely(prior_path)

    base = _base_result(
        as_of=as_of,
        output_root=output_root_path,
        approval_packet_path=approval_path,
        prior_certification_path=prior_path,
        approval_packet=approval_packet,
        prior_certification=prior_certification,
        entry_client_order_id=entry_client_order_id,
        exit_client_order_id=exit_client_order_id,
        authorized=paper_fill_exit_authorized,
    )

    authorization_blockers = _authorization_blockers(
        approval_packet=approval_packet,
        prior_certification=prior_certification,
        approval_packet_path=approval_path,
        prior_certification_path=prior_path,
    )
    preflight = _environment_preflight(
        source_env,
        expected_paper_account_id=expected_account_id,
    )
    environment_blockers = _environment_gate_blockers(
        preflight,
        authorized=paper_fill_exit_authorized,
    )
    early_blockers = _dedupe((*authorization_blockers, *environment_blockers))
    if early_blockers:
        return _finalize_result(
            {
                **base,
                "operator_preflight": preflight,
                "outcome_classification": OUTCOME_BLOCKED_BEFORE_ENTRY,
            },
            blockers=early_blockers,
            next_operator_action="repair_v5_10_pre_entry_gate_before_paper_submit",
            write_artifacts=write_artifacts,
        )

    client_result = _build_broker_client(source_env, broker_client_factory)
    client = client_result["client"]
    if client is None:
        return _finalize_result(
            {
                **base,
                "operator_preflight": preflight,
                "broker_client_error": client_result["error"],
                "outcome_classification": OUTCOME_BLOCKED_BEFORE_ENTRY,
            },
            blockers=("paper_broker_client_unavailable",),
            next_operator_action="repair_paper_broker_client_before_v5_10_entry",
            write_artifacts=write_artifacts,
        )

    account_result = _read_account(client)
    account = account_result["account"]
    asset_result = _read_asset(client, V510_SYMBOL)
    asset = asset_result["asset"]
    open_order_result = _read_orders(client, status_filter="open", symbol=V510_SYMBOL)
    open_orders = open_order_result["orders"]
    position_result = _read_positions(client)
    positions = position_result["positions"]
    price_basis = _read_price_basis(client, V510_SYMBOL)
    existing_entry_order = _lookup_by_client_order_id(
        client,
        client_order_id=entry_client_order_id,
        symbol=V510_SYMBOL,
    )
    existing_exit_order = _lookup_by_client_order_id(
        client,
        client_order_id=exit_client_order_id,
        symbol=V510_SYMBOL,
    )
    read_blockers = _read_gate_blockers(
        account=account,
        account_error=account_result["error"],
        expected_paper_account_id=expected_account_id,
        asset=asset,
        asset_error=asset_result["error"],
        open_orders=open_orders,
        open_order_error=open_order_result["error"],
        positions=positions,
        position_error=position_result["error"],
        existing_entry_order=existing_entry_order,
        existing_exit_order=existing_exit_order,
    )
    entry_design, design_blockers = _build_entry_design(price_basis)
    pre_entry_blockers = _dedupe((*read_blockers, *design_blockers))
    observed_base = {
        **base,
        "operator_preflight": preflight,
        "account_observation": account,
        "asset_observation": asset,
        "open_order_scan": open_orders,
        "position_scan": positions,
        "entry_price_basis": price_basis,
        "existing_entry_client_order_id_order": existing_entry_order,
        "existing_exit_client_order_id_order": existing_exit_order,
        "entry_order_design": entry_design,
        "broker_read_observed": True,
        "pre_entry_gate_blockers": pre_entry_blockers,
    }
    if pre_entry_blockers:
        return _finalize_result(
            {**observed_base, "outcome_classification": OUTCOME_BLOCKED_BEFORE_ENTRY},
            blockers=pre_entry_blockers,
            next_operator_action="repair_v5_10_broker_read_gate_before_entry",
            write_artifacts=write_artifacts,
        )

    entry_request = AlpacaOrderRequest(
        client_order_id=entry_client_order_id,
        symbol=V510_SYMBOL,
        side="buy",
        asset_class="crypto",
        notional=V510_APPROVED_MAX_NOTIONAL,
        order_type="market",
        time_in_force="ioc",
    )
    entry_lifecycle = _submit_and_reconcile_once(
        client,
        request=entry_request,
        role="entry",
        reconciliation_poll_attempts=reconciliation_poll_attempts,
        reconciliation_poll_interval_seconds=reconciliation_poll_interval_seconds,
    )
    entry_result = _mapping(entry_lifecycle.get("submit_result"))
    entry_final_order = _mapping(entry_lifecycle.get("final_order"))
    position_after_entry_result = _residual_position(client, V510_SYMBOL)
    position_after_entry = _mapping(position_after_entry_result.get("position"))
    entry_filled_qty = _filled_quantity(entry_final_order)
    entry_final_status = _order_status(entry_final_order)
    entry_submit_status = _clean_text(entry_result.get("submit_status"))
    after_entry_base = {
        **observed_base,
        "submitted_entry_request": _request_fields(entry_request),
        "entry_submit_result": entry_result,
        "entry_final_order": entry_final_order,
        "entry_submit_status": entry_submit_status,
        "entry_final_status": entry_final_status,
        "entry_filled_qty": _decimal_text(entry_filled_qty),
        "entry_filled_avg_price": _decimal_text(
            _decimal_or_none(entry_final_order.get("filled_avg_price"))
        ),
        "position_after_entry": position_after_entry,
        "position_after_entry_result": position_after_entry_result,
    }

    entry_outcome = _classify_entry_before_exit(
        final_order=entry_final_order,
        submit_result=entry_result,
        position_after_entry=position_after_entry,
        position_after_entry_error=_clean_text(
            position_after_entry_result.get("position_read_error")
        ),
    )
    if entry_outcome["stop_before_exit"]:
        return _finalize_result(
            {
                **after_entry_base,
                "outcome_classification": entry_outcome["outcome"],
            },
            blockers=entry_outcome["blockers"],
            next_operator_action=entry_outcome["next_operator_action"],
            write_artifacts=write_artifacts,
        )

    exit_design, exit_blockers = _build_exit_design(
        entry_filled_qty=entry_filled_qty,
        position_after_entry=position_after_entry,
    )
    if exit_blockers:
        return _finalize_result(
            {
                **after_entry_base,
                "exit_order_design": exit_design,
                "outcome_classification": OUTCOME_BLOCKED_BEFORE_EXIT,
            },
            blockers=exit_blockers,
            next_operator_action="operator_reconcile_v5_10_position_before_any_exit",
            write_artifacts=write_artifacts,
        )

    exit_qty = _positive_decimal_or_none(exit_design.get("exit_qty")) or Decimal("0")
    exit_side = _clean_text(exit_design.get("exit_side"))
    exit_request = AlpacaOrderRequest(
        client_order_id=exit_client_order_id,
        symbol=V510_SYMBOL,
        side=exit_side,
        asset_class="crypto",
        qty=exit_qty,
        order_type="market",
        time_in_force="ioc",
    )
    exit_lifecycle = _submit_and_reconcile_once(
        client,
        request=exit_request,
        role="exit",
        reconciliation_poll_attempts=reconciliation_poll_attempts,
        reconciliation_poll_interval_seconds=reconciliation_poll_interval_seconds,
    )
    exit_result = _mapping(exit_lifecycle.get("submit_result"))
    exit_final_order = _mapping(exit_lifecycle.get("final_order"))
    final_position_result = _residual_position(client, V510_SYMBOL)
    final_position = _mapping(final_position_result.get("position"))
    exit_outcome = _classify_exit_result(
        entry_final_order=entry_final_order,
        exit_final_order=exit_final_order,
        exit_submit_result=exit_result,
        final_position=final_position,
        final_position_error=_clean_text(final_position_result.get("position_read_error")),
    )

    return _finalize_result(
        {
            **after_entry_base,
            "exit_order_design": exit_design,
            "submitted_exit_request": _request_fields(exit_request),
            "exit_submit_result": exit_result,
            "exit_final_order": exit_final_order,
            "exit_submit_status": _clean_text(exit_result.get("submit_status")),
            "exit_final_status": _order_status(exit_final_order),
            "exit_filled_qty": _decimal_text(_filled_quantity(exit_final_order)),
            "exit_filled_avg_price": _decimal_text(
                _decimal_or_none(exit_final_order.get("filled_avg_price"))
            ),
            "final_position": final_position,
            "final_position_result": final_position_result,
            "outcome_classification": exit_outcome["outcome"],
        },
        blockers=exit_outcome["blockers"],
        next_operator_action=exit_outcome["next_operator_action"],
        write_artifacts=write_artifacts,
    )


def deterministic_v510_client_order_ids(
    *,
    prior_certification_id: str,
    prior_client_order_id: str,
) -> tuple[str, str]:
    """Return deterministic one-shot v5.10 entry and exit client order ids."""

    payload = json.dumps(
        {
            "prior_certification_id": _clean_text(prior_certification_id),
            "prior_client_order_id": _clean_text(prior_client_order_id),
            "symbol": V510_SYMBOL,
            "scope": V510_REQUESTED_SCOPE,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return (
        f"v510-btcusd-entry-{digest[:16]}",
        f"v510-btcusd-exit-{digest[16:32]}",
    )


def render_crypto_paper_fill_exit_certification_text(
    result: Mapping[str, Any],
) -> str:
    """Render a compact credential-free operator receipt."""

    lines = [
        f"crypto_paper_fill_exit_certification_command={COMMAND_NAME}",
        "crypto_paper_fill_exit_certification_scope=alpaca_paper_only_btcusd_one_entry_one_exit",
        f"paper_fill_exit_authorized={_bool_text(result.get('paper_fill_exit_authorized'))}",
        f"outcome_classification={_clean_text(result.get('outcome_classification'))}",
        f"blockers={','.join(_text_list(result.get('blockers')))}",
    ]
    preflight = _mapping(result.get("operator_preflight"))
    for key in (
        "APP_PROFILE_is_paper",
        "APP_PROFILE_is_live",
        "paper_credentials_present",
        "expected_paper_account_id_loaded",
        "paper_endpoint_exact_match_indicator",
        "live_endpoint_indicator",
        "network_test_flag_enabled",
    ):
        if key in preflight:
            lines.append(f"preflight_{key}={_bool_text(preflight.get(key))}")
    lines.extend(
        [
            f"symbol={_clean_text(result.get('symbol'))}",
            f"approved_max_notional={_clean_text(result.get('approved_max_notional'))}",
            f"entry_client_order_id={_clean_text(result.get('entry_client_order_id'))}",
            f"exit_client_order_id={_clean_text(result.get('exit_client_order_id'))}",
            f"entry_attempt_count={_clean_text(result.get('entry_attempt_count'))}",
            f"exit_attempt_count={_clean_text(result.get('exit_attempt_count'))}",
            f"entry_submit_status={_clean_text(result.get('entry_submit_status'))}",
            f"entry_final_status={_clean_text(result.get('entry_final_status'))}",
            f"entry_filled_qty={_clean_text(result.get('entry_filled_qty'))}",
            f"entry_filled_avg_price={_clean_text(result.get('entry_filled_avg_price'))}",
            f"exit_submit_status={_clean_text(result.get('exit_submit_status'))}",
            f"exit_final_status={_clean_text(result.get('exit_final_status'))}",
            f"exit_filled_qty={_clean_text(result.get('exit_filled_qty'))}",
            f"exit_filled_avg_price={_clean_text(result.get('exit_filled_avg_price'))}",
            f"residual_position_status={_clean_text(result.get('residual_position_status'))}",
            f"broker_read_observed={_bool_text(result.get('broker_read_observed'))}",
            f"broker_mutation_performed={_bool_text(result.get('broker_mutation_performed'))}",
            f"paper_submit_performed={_bool_text(result.get('paper_submit_performed'))}",
            f"live_mutation_performed={_bool_text(result.get('live_mutation_performed'))}",
            f"live_endpoint_touched={_bool_text(result.get('live_endpoint_touched'))}",
            f"credential_values_exposed={_bool_text(result.get('credential_values_exposed'))}",
            f"next_operator_action={_clean_text(result.get('next_operator_action'))}",
            "Credential values are never printed",
        ]
    )
    artifacts = _mapping(result.get("artifact_paths"))
    for key in (
        "fill_exit_certification_result_json",
        "fill_exit_certification_result_md",
        "operating_record",
        "manifest",
    ):
        if key in artifacts:
            lines.append(f"artifact_{key}={artifacts[key]}")
    return "\n".join(lines)


def _base_result(
    *,
    as_of: datetime,
    output_root: Path,
    approval_packet_path: Path,
    prior_certification_path: Path,
    approval_packet: Mapping[str, Any],
    prior_certification: Mapping[str, Any],
    entry_client_order_id: str,
    exit_client_order_id: str,
    authorized: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "operator_command": COMMAND_NAME,
        "as_of": as_of.isoformat(),
        "output_root": str(output_root),
        "approved_authorization_text": V510_AUTHORIZATION_TEXT,
        "approval_packet_source": str(approval_packet_path),
        "prior_certification_source": str(prior_certification_path),
        "approval_packet_summary": _approval_packet_summary(approval_packet),
        "prior_certification_summary": _prior_certification_summary(prior_certification),
        "prior_certification_id": V510_PRIOR_CERTIFICATION_ID,
        "prior_client_order_id": V510_PRIOR_CLIENT_ORDER_ID,
        "symbol": V510_SYMBOL,
        "approved_max_notional": _decimal_text(V510_APPROVED_MAX_NOTIONAL),
        "entry_client_order_id": entry_client_order_id,
        "exit_client_order_id": "",
        "reserved_exit_client_order_id": exit_client_order_id,
        "entry_attempt_count": 0,
        "exit_attempt_count": 0,
        "paper_fill_exit_authorized": bool(authorized),
        "broker_read_observed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "entry_order_type": "market",
        "entry_side": "buy",
        "entry_qty": "",
        "entry_notional": _decimal_text(V510_APPROVED_MAX_NOTIONAL),
        "entry_price_basis": "market_ioc_notional_cap",
        "entry_limit_price": "",
        "estimated_entry_notional": _decimal_text(V510_APPROVED_MAX_NOTIONAL),
        "entry_submit_status": "not_attempted",
        "entry_final_status": "not_attempted",
        "entry_filled_qty": "0",
        "entry_filled_avg_price": "",
        "position_after_entry": {},
        "exit_side": "",
        "exit_qty": "",
        "estimated_exit_notional": "",
        "exit_submit_status": "not_attempted",
        "exit_final_status": "not_attempted",
        "exit_filled_qty": "",
        "exit_filled_avg_price": "",
        "final_position": {},
        "residual_position_status": "not_observed",
        "outcome_classification": OUTCOME_BLOCKED_BEFORE_ENTRY,
        "blockers": [],
        "labels": list(REQUIRED_LABELS),
        "next_operator_action": "",
        "close_or_liquidate_allowed": False,
        "replace_allowed": False,
        "retry_entry_allowed": False,
        "retry_exit_allowed": False,
        "entry_call_count_max": 1,
        "exit_call_count_max": 1,
    }


def _authorization_blockers(
    *,
    approval_packet: Mapping[str, Any],
    prior_certification: Mapping[str, Any],
    approval_packet_path: Path,
    prior_certification_path: Path,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not approval_packet_path.is_file():
        blockers.append("approval_packet_missing")
    if not prior_certification_path.is_file():
        blockers.append("prior_certification_result_missing")
    if not approval_packet:
        blockers.append("approval_packet_unreadable")
    if not prior_certification:
        blockers.append("prior_certification_result_unreadable")
    if blockers:
        return _dedupe(blockers)

    if _clean_text(approval_packet.get("required_operator_phrase")) != V510_AUTHORIZATION_TEXT:
        blockers.append("approval_packet_authorization_text_mismatch")
    if _clean_text(approval_packet.get("prior_certification_id")) != V510_PRIOR_CERTIFICATION_ID:
        blockers.append("approval_packet_prior_certification_id_mismatch")
    if _clean_text(approval_packet.get("prior_client_order_id")) != V510_PRIOR_CLIENT_ORDER_ID:
        blockers.append("approval_packet_prior_client_order_id_mismatch")
    if _clean_text(approval_packet.get("requested_future_authorization_scope")) != V510_REQUESTED_SCOPE:
        blockers.append("approval_packet_requested_scope_mismatch")
    if _normalize_symbol_text(approval_packet.get("proposed_symbol")) != V510_SYMBOL:
        blockers.append("approval_packet_symbol_not_BTCUSD")
    packet_cap = _decimal_or_none(
        _first_present(
            approval_packet,
            "proposed_max_notional",
            "proposed_max_notional_cap",
            "approved_max_notional",
        )
    )
    if packet_cap is None:
        blockers.append("approval_packet_max_notional_missing")
    elif packet_cap != V510_APPROVED_MAX_NOTIONAL:
        blockers.append("approval_packet_max_notional_mismatch")
    if packet_cap is not None and packet_cap > V510_APPROVED_MAX_NOTIONAL:
        blockers.append("approval_packet_max_notional_exceeds_approved_max")

    prior_referenced = _mapping(approval_packet.get("prior_certification_result_referenced"))
    if _clean_text(prior_referenced.get("client_order_id")) != V510_PRIOR_CLIENT_ORDER_ID:
        blockers.append("approval_packet_referenced_prior_client_order_id_mismatch")
    if _clean_text(prior_referenced.get("filled_qty")) not in {"0", "0.0", "0.00"}:
        blockers.append("approval_packet_prior_fill_not_zero")

    if _clean_text(prior_certification.get("client_order_id")) != V510_PRIOR_CLIENT_ORDER_ID:
        blockers.append("prior_certification_client_order_id_mismatch")
    if _normalize_symbol_text(prior_certification.get("symbol")) != V510_SYMBOL:
        blockers.append("prior_certification_symbol_not_BTCUSD")
    if _clean_text(prior_certification.get("approved_max_notional")) != _decimal_text(
        V510_APPROVED_MAX_NOTIONAL
    ):
        blockers.append("prior_certification_max_notional_mismatch")
    prior_filled_qty = _decimal_or_none(
        _first_present(prior_certification, "entry_filled_qty", "filled_qty")
    ) or _decimal_or_none(
        _mapping(prior_certification.get("final_order")).get("filled_qty")
    ) or Decimal("0")
    if prior_filled_qty != Decimal("0"):
        blockers.append("prior_certification_fill_not_zero")
    if _bool(prior_certification.get("live_endpoint_touched")):
        blockers.append("prior_certification_live_endpoint_touched")
    if _bool(prior_certification.get("credential_values_exposed")):
        blockers.append("prior_certification_credential_values_exposed")

    return _dedupe(blockers)


def _environment_preflight(
    env: Mapping[str, str],
    *,
    expected_paper_account_id: str,
) -> dict[str, Any]:
    credential_state = {
        f"{name}_present": bool(_clean_text(env.get(name)))
        for name in _CREDENTIAL_VARIABLE_NAMES
    }
    paper_credentials_present = bool(
        _clean_text(env.get("ALPACA_API_KEY"))
        and _clean_text(env.get("ALPACA_SECRET_KEY"))
    )
    return {
        **credential_state,
        "APP_PROFILE_is_paper": env.get("APP_PROFILE", "").strip().lower() == "paper",
        "APP_PROFILE_is_live": env.get("APP_PROFILE", "").strip().lower() == "live",
        "paper_credentials_present": paper_credentials_present,
        "expected_paper_account_id_loaded": bool(_clean_text(expected_paper_account_id)),
        "paper_endpoint_exact_match_indicator": _normalize_endpoint(
            _effective_paper_base_url(env)
        )
        == _normalize_endpoint(DEFAULT_ALPACA_PAPER_BASE_URL),
        "live_endpoint_indicator": _live_endpoint_indicator(env),
        "network_test_flag_enabled": _network_test_flag_enabled(env),
    }


def _environment_gate_blockers(
    preflight: Mapping[str, Any],
    *,
    authorized: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not authorized:
        blockers.append("v5_10_paper_fill_exit_authorization_switch_required")
    if preflight.get("APP_PROFILE_is_live") is True:
        blockers.append("APP_PROFILE_live_not_authorized")
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
    if preflight.get("network_test_flag_enabled") is True:
        blockers.append("network_test_flag_enabled")
    return _dedupe(blockers)


def _build_broker_client(
    env: Mapping[str, str],
    broker_client_factory: BrokerClientFactory | None,
) -> dict[str, Any]:
    try:
        config = AlpacaPaperConfig(
            app_profile=env.get("APP_PROFILE", ""),
            alpaca_api_key=env.get("ALPACA_API_KEY"),
            alpaca_secret_key=env.get("ALPACA_SECRET_KEY"),
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
    for target in (client, _raw_trading_client(client)):
        method = getattr(target, "get_asset", None)
        if callable(method):
            try:
                return {"asset": _asset_payload(method(symbol)), "error": ""}
            except Exception:
                pass
    try:
        assets = client.list_assets()
    except Exception as exc:  # noqa: BLE001 - certification fails closed.
        return {"asset": {}, "error": _safe_exception_message(exc)}
    for asset in assets:
        payload = _asset_payload(asset)
        if _normalize_symbol_text(payload.get("symbol")) == symbol:
            return {"asset": payload, "error": ""}
    return {"asset": {}, "error": "BTCUSD_asset_not_found"}


def _read_orders(client: Any, *, status_filter: str, symbol: str) -> dict[str, Any]:
    try:
        orders = client.get_orders(
            AlpacaRecentOrderQuery(
                status_filter=status_filter,
                symbol_filter=symbol,
                asset_class_filter="crypto",
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


def _read_price_basis(client: Any, symbol: str) -> dict[str, Any]:
    method_names = (
        "get_latest_crypto_quote",
        "get_crypto_latest_quote",
        "get_latest_quote",
        "get_quote",
        "get_crypto_quote",
        "get_latest_crypto_trade",
        "get_latest_trade",
    )
    for target in (client, _raw_trading_client(client)):
        for method_name in method_names:
            method = getattr(target, method_name, None)
            if not callable(method):
                continue
            try:
                payload = _generic_payload(method(symbol))
            except Exception as exc:  # noqa: BLE001 - quote is informational here.
                return {
                    "price_basis": "market_ioc_notional_cap",
                    "quote_observed": False,
                    "quote_read_error": _safe_exception_message(exc),
                    "estimated_entry_notional": _decimal_text(V510_APPROVED_MAX_NOTIONAL),
                }
            price = _first_decimal(
                payload,
                "ask_price",
                "bid_price",
                "price",
                "ap",
                "bp",
                "p",
            )
            return {
                "price_basis": "market_ioc_notional_cap",
                "quote_observed": price is not None,
                "quote_summary": _quote_payload(payload),
                "reference_price": _decimal_text(price),
                "estimated_entry_notional": _decimal_text(V510_APPROVED_MAX_NOTIONAL),
            }
    return {
        "price_basis": "market_ioc_notional_cap_no_quote_required",
        "quote_observed": False,
        "quote_read_error": "paper_trading_client_quote_read_unavailable",
        "estimated_entry_notional": _decimal_text(V510_APPROVED_MAX_NOTIONAL),
    }


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
    existing_entry_order: Mapping[str, Any],
    existing_exit_order: Mapping[str, Any],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if account_error:
        blockers.append("paper_account_read_failed")
    elif not _expected_account_matched(account, expected_paper_account_id):
        blockers.append("paper_account_id_mismatch")
    elif _normalize_status(account.get("status")) not in {"active"}:
        blockers.append("paper_account_not_active")
    if _bool(account.get("trading_blocked")) or _bool(account.get("account_blocked")):
        blockers.append("paper_account_blocked")

    if asset_error:
        blockers.append("BTCUSD_asset_read_failed")
    elif not asset:
        blockers.append("BTCUSD_asset_missing")
    else:
        if _normalize_symbol_text(asset.get("symbol")) != V510_SYMBOL:
            blockers.append("BTCUSD_asset_symbol_mismatch")
        if _normalize_status(asset.get("status")) not in {"active"}:
            blockers.append("BTCUSD_asset_not_active")
        if asset.get("tradable") is not True:
            blockers.append("BTCUSD_asset_not_tradable")

    if open_order_error:
        blockers.append("BTCUSD_open_order_read_failed")
    for order in open_orders:
        if _order_symbol(order) != V510_SYMBOL:
            continue
        client_order_id = _clean_text(order.get("client_order_id"))
        if client_order_id == _clean_text(existing_entry_order.get("client_order_id")):
            blockers.append("existing_v5_10_entry_client_order_id_order_exists")
        elif client_order_id == _clean_text(existing_exit_order.get("client_order_id")):
            blockers.append("existing_v5_10_exit_client_order_id_order_exists")
        else:
            blockers.append("existing_conflicting_BTCUSD_open_order_exists")
    if existing_entry_order:
        blockers.append("prior_v5_10_entry_client_order_id_order_exists")
    if existing_exit_order:
        blockers.append("prior_v5_10_exit_client_order_id_order_exists")

    if position_error:
        blockers.append("BTCUSD_position_read_failed")
    for position in positions:
        if _position_symbol(position) != V510_SYMBOL:
            continue
        qty = _position_quantity(position)
        if qty != Decimal("0"):
            blockers.append("existing_BTCUSD_position_ambiguous")
    return _dedupe(blockers)


def _build_entry_design(price_basis: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    blockers: list[str] = []
    estimated_notional = V510_APPROVED_MAX_NOTIONAL
    if estimated_notional > V510_APPROVED_MAX_NOTIONAL:
        blockers.append("estimated_entry_notional_exceeds_approved_max")
    entry_order_can_rest = False
    if entry_order_can_rest:
        blockers.append("entry_order_could_rest_without_cancel_authority")
    return (
        {
            "symbol": V510_SYMBOL,
            "side": "buy",
            "asset_class": "crypto",
            "order_type": "market",
            "time_in_force": "ioc",
            "notional": _decimal_text(V510_APPROVED_MAX_NOTIONAL),
            "quantity": "",
            "estimated_entry_notional": _decimal_text(estimated_notional),
            "entry_order_can_rest": entry_order_can_rest,
            "non_resting_reason": "market_ioc",
            "price_basis": _clean_text(price_basis.get("price_basis")),
            "quote_observed": price_basis.get("quote_observed") is True,
            "reference_price": _clean_text(price_basis.get("reference_price")),
        },
        _dedupe(blockers),
    )


def _submit_and_reconcile_once(
    client: Any,
    *,
    request: AlpacaOrderRequest,
    role: str,
    reconciliation_poll_attempts: int,
    reconciliation_poll_interval_seconds: float,
) -> dict[str, Any]:
    try:
        response = client.submit_order(request)
        submitted_order = _order_summary(response)
        submit_result = {
            "role": role,
            "submit_attempted": True,
            "submit_call_count": 1,
            "submit_status": _order_status(submitted_order) or "accepted",
            "submit_error": "",
            "submit_error_type": "",
            "submitted_order": submitted_order,
        }
    except Exception as exc:  # noqa: BLE001 - submit may be ambiguous.
        submit_result = {
            "role": role,
            "submit_attempted": True,
            "submit_call_count": 1,
            "submit_status": "ambiguous",
            "submit_error": _safe_exception_message(exc),
            "submit_error_type": exc.__class__.__name__,
            "submitted_order": {},
        }
        final_order = _lookup_by_client_order_id(
            client,
            client_order_id=request.client_order_id,
            symbol=request.symbol,
        )
        return {
            "submit_result": submit_result,
            "final_order": final_order,
            "reconciliation_status": "submit_ambiguous_no_retry",
        }

    final_order = _poll_lookup_by_client_order_id(
        client,
        client_order_id=request.client_order_id,
        symbol=request.symbol,
        attempts=reconciliation_poll_attempts,
        interval_seconds=reconciliation_poll_interval_seconds,
    ) or _mapping(submit_result.get("submitted_order"))
    return {
        "submit_result": submit_result,
        "final_order": final_order,
        "reconciliation_status": "reconciled" if final_order else "unreconciled",
    }


def _classify_entry_before_exit(
    *,
    final_order: Mapping[str, Any],
    submit_result: Mapping[str, Any],
    position_after_entry: Mapping[str, Any],
    position_after_entry_error: str,
) -> dict[str, Any]:
    status = _order_status(final_order)
    filled_qty = _filled_quantity(final_order)
    if _clean_text(submit_result.get("submit_status")) == "ambiguous":
        return {
            "stop_before_exit": True,
            "outcome": OUTCOME_ENTRY_AMBIGUOUS,
            "blockers": ("entry_submit_ambiguous_no_retry",),
            "next_operator_action": "operator_reconcile_ambiguous_entry_before_any_future_order",
        }
    if not final_order:
        return {
            "stop_before_exit": True,
            "outcome": OUTCOME_ENTRY_AMBIGUOUS,
            "blockers": ("entry_order_not_reconciled_after_single_submit_call",),
            "next_operator_action": "operator_reconcile_unobserved_entry_before_any_future_order",
        }
    if status == "rejected":
        return {
            "stop_before_exit": True,
            "outcome": OUTCOME_ENTRY_REJECTED_NO_POSITION,
            "blockers": ("entry_rejected_no_retry",),
            "next_operator_action": "review_rejected_v5_10_entry_artifacts",
        }
    if filled_qty <= Decimal("0"):
        if status in _NO_FILL_TERMINAL_STATUSES:
            return {
                "stop_before_exit": True,
                "outcome": OUTCOME_ENTRY_NO_FILL_NO_EXIT,
                "blockers": (),
                "next_operator_action": "review_v5_10_no_fill_entry_artifacts",
            }
        return {
            "stop_before_exit": True,
            "outcome": OUTCOME_ENTRY_AMBIGUOUS,
            "blockers": ("entry_no_fill_order_not_terminal",),
            "next_operator_action": "operator_reconcile_open_or_ambiguous_entry_order",
        }
    if status in _OPEN_OR_AMBIGUOUS_STATUSES and status not in _TERMINAL_STATUSES:
        return {
            "stop_before_exit": True,
            "outcome": OUTCOME_ENTRY_AMBIGUOUS,
            "blockers": ("entry_filled_but_order_status_not_terminal",),
            "next_operator_action": "operator_reconcile_entry_residual_open_order",
        }
    if position_after_entry_error:
        return {
            "stop_before_exit": True,
            "outcome": OUTCOME_BLOCKED_BEFORE_EXIT,
            "blockers": ("BTCUSD_position_after_entry_read_failed",),
            "next_operator_action": "operator_reconcile_position_before_exit_attempt",
        }
    position_qty = _position_quantity(position_after_entry)
    if position_qty <= Decimal("0"):
        return {
            "stop_before_exit": True,
            "outcome": OUTCOME_BLOCKED_BEFORE_EXIT,
            "blockers": ("BTCUSD_position_after_entry_not_observed",),
            "next_operator_action": "operator_reconcile_entry_fill_without_position",
        }
    return {
        "stop_before_exit": False,
        "outcome": "",
        "blockers": (),
        "next_operator_action": "",
    }


def _build_exit_design(
    *,
    entry_filled_qty: Decimal,
    position_after_entry: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    blockers: list[str] = []
    position_qty = _position_quantity(position_after_entry)
    position_side = _normalize_status(position_after_entry.get("side"))
    if entry_filled_qty <= Decimal("0"):
        blockers.append("entry_filled_qty_required_before_exit")
    if position_qty <= Decimal("0"):
        blockers.append("positive_BTCUSD_position_required_before_exit")
    if position_side and position_side not in {"long"}:
        blockers.append("unexpected_BTCUSD_position_side_before_exit")
    exit_qty = min(entry_filled_qty, position_qty)
    if exit_qty <= Decimal("0"):
        blockers.append("exit_qty_not_positive")
    if exit_qty > entry_filled_qty:
        blockers.append("exit_qty_exceeds_entry_filled_qty")
    if exit_qty > position_qty:
        blockers.append("exit_qty_exceeds_resulting_position_qty")
    avg_price = _decimal_or_none(position_after_entry.get("average_entry_price"))
    estimated_exit_notional = exit_qty * avg_price if avg_price is not None else None
    return (
        {
            "symbol": V510_SYMBOL,
            "exit_side": "sell",
            "exit_qty": _decimal_text(exit_qty),
            "order_type": "market",
            "time_in_force": "ioc",
            "position_qty_basis": _decimal_text(position_qty),
            "entry_filled_qty_basis": _decimal_text(entry_filled_qty),
            "estimated_exit_notional": _decimal_text(estimated_exit_notional),
            "exit_order_can_rest": False,
            "non_resting_reason": "market_ioc",
        },
        _dedupe(blockers),
    )


def _classify_exit_result(
    *,
    entry_final_order: Mapping[str, Any],
    exit_final_order: Mapping[str, Any],
    exit_submit_result: Mapping[str, Any],
    final_position: Mapping[str, Any],
    final_position_error: str,
) -> dict[str, Any]:
    if _clean_text(exit_submit_result.get("submit_status")) == "ambiguous":
        return {
            "outcome": OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
            "blockers": ("exit_submit_ambiguous_no_retry",),
            "next_operator_action": "operator_reconcile_ambiguous_exit_and_residual_position",
        }
    if not exit_final_order:
        return {
            "outcome": OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
            "blockers": ("exit_order_not_reconciled_after_single_submit_call",),
            "next_operator_action": "operator_reconcile_unobserved_exit_and_residual_position",
        }
    exit_status = _order_status(exit_final_order)
    if exit_status == "rejected":
        return {
            "outcome": OUTCOME_EXIT_REJECTED_RESIDUAL_POSITION,
            "blockers": ("exit_rejected_no_retry",),
            "next_operator_action": "operator_reconcile_rejected_exit_residual_position",
        }
    if exit_status not in _TERMINAL_STATUSES:
        return {
            "outcome": OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
            "blockers": ("exit_order_status_not_terminal",),
            "next_operator_action": "operator_reconcile_open_or_ambiguous_exit_order",
        }
    if _filled_quantity(exit_final_order) <= Decimal("0"):
        return {
            "outcome": OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
            "blockers": ("exit_no_fill_observed",),
            "next_operator_action": "operator_reconcile_exit_no_fill_residual_position",
        }
    if final_position_error:
        return {
            "outcome": OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
            "blockers": ("final_BTCUSD_position_read_failed",),
            "next_operator_action": "operator_reconcile_final_position_after_exit",
        }
    if _position_quantity(final_position) != Decimal("0"):
        return {
            "outcome": OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
            "blockers": ("residual_BTCUSD_position_after_exit",),
            "next_operator_action": "operator_reconcile_residual_BTCUSD_position_no_retry",
        }
    entry_status = _order_status(entry_final_order)
    outcome = (
        OUTCOME_FILLED_EXIT_CONFIRMED
        if entry_status == "filled"
        else OUTCOME_PARTIAL_FILL_EXIT_CONFIRMED
    )
    return {
        "outcome": outcome,
        "blockers": (),
        "next_operator_action": "review_v5_10_fill_exit_certification_artifacts",
    }


def _finalize_result(
    result: Mapping[str, Any],
    *,
    blockers: Sequence[str],
    next_operator_action: str,
    write_artifacts: bool,
) -> dict[str, Any]:
    entry_result = _mapping(result.get("entry_submit_result"))
    exit_result = _mapping(result.get("exit_submit_result"))
    entry_attempt_count = int(
        _decimal_or_none(entry_result.get("submit_call_count")) or Decimal("0")
    )
    exit_attempt_count = int(
        _decimal_or_none(exit_result.get("submit_call_count")) or Decimal("0")
    )
    exit_design = _mapping(result.get("exit_order_design"))
    final_position = _mapping(result.get("final_position"))
    position_after_entry = _mapping(result.get("position_after_entry"))
    residual_position_status = _residual_position_status(final_position)
    if not final_position and position_after_entry and exit_attempt_count == 0:
        residual_position_status = "entry_position_observed_exit_not_attempted"
    finalized = {
        **dict(result),
        "exit_client_order_id": result.get("reserved_exit_client_order_id", "")
        if exit_attempt_count > 0
        else "",
        "entry_attempt_count": entry_attempt_count,
        "exit_attempt_count": exit_attempt_count,
        "broker_mutation_performed": entry_attempt_count > 0 or exit_attempt_count > 0,
        "paper_submit_performed": entry_attempt_count > 0 or exit_attempt_count > 0,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "exit_side": _clean_text(exit_design.get("exit_side"))
        if exit_attempt_count > 0
        else _clean_text(result.get("exit_side")),
        "exit_qty": _clean_text(exit_design.get("exit_qty"))
        if exit_attempt_count > 0
        else _clean_text(result.get("exit_qty")),
        "estimated_exit_notional": _clean_text(
            exit_design.get("estimated_exit_notional")
        ),
        "residual_position_status": residual_position_status,
        "blockers": list(_dedupe(blockers)),
        "labels": list(REQUIRED_LABELS),
        "next_operator_action": next_operator_action,
    }
    if write_artifacts:
        finalized["artifact_paths"] = _write_artifacts(
            _path(finalized["output_root"], "output_root"),
            finalized,
        )
    return _json_safe(finalized)


def _write_artifacts(root: Path, result: Mapping[str, Any]) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    result_json = root / "fill_exit_certification_result.json"
    result_md = root / "fill_exit_certification_result.md"
    operating_record = root / "operating_record.jsonl"
    manifest = root / "manifest.json"
    paths = {
        "fill_exit_certification_result_json": str(result_json),
        "fill_exit_certification_result_md": str(result_md),
        "operating_record": str(operating_record),
        "manifest": str(manifest),
    }
    result_with_paths = {**dict(result), "artifact_paths": paths}
    _write_json(result_json, result_with_paths)
    result_md.write_text(
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
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_fill_exit_certification_manifest",
        "as_of": result.get("as_of", ""),
        "artifact_root": str(root),
        "generated_under_runs": _generated_under_runs(root),
        "credential_values_redacted": True,
        "required_artifacts": {
            "fill_exit_certification_result_json": _artifact_entry(result_json),
            "fill_exit_certification_result_md": _artifact_entry(result_md),
            "operating_record": _artifact_entry(operating_record),
            "manifest": {"path": str(manifest)},
        },
        "input_artifacts": {
            "approval_packet": _artifact_reference(
                _clean_text(result.get("approval_packet_source"))
            ),
            "prior_certification_result": _artifact_reference(
                _clean_text(result.get("prior_certification_source"))
            ),
        },
        "broker_read_observed": result.get("broker_read_observed") is True,
        "broker_mutation_performed": result.get("broker_mutation_performed") is True,
        "paper_submit_performed": result.get("paper_submit_performed") is True,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "outcome_classification": result.get("outcome_classification", ""),
        "labels": list(REQUIRED_LABELS),
    }
    _write_json(manifest, manifest_payload)
    return paths


def _render_certification_markdown(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# BTCUSD Paper Fill/Exit Certification",
            "",
            f"- Outcome: `{result.get('outcome_classification', '')}`",
            f"- Symbol: `{result.get('symbol', '')}`",
            f"- Approved max notional: `{result.get('approved_max_notional', '')}`",
            f"- Entry client order id: `{result.get('entry_client_order_id', '')}`",
            f"- Exit client order id: `{result.get('exit_client_order_id', '')}`",
            f"- Entry attempts: `{result.get('entry_attempt_count')}`",
            f"- Exit attempts: `{result.get('exit_attempt_count')}`",
            f"- Entry status: `{result.get('entry_submit_status', '')}` / `{result.get('entry_final_status', '')}`",
            f"- Entry fill: `{result.get('entry_filled_qty', '')}` @ `{result.get('entry_filled_avg_price', '')}`",
            f"- Exit status: `{result.get('exit_submit_status', '')}` / `{result.get('exit_final_status', '')}`",
            f"- Exit fill: `{result.get('exit_filled_qty', '')}` @ `{result.get('exit_filled_avg_price', '')}`",
            f"- Residual position status: `{result.get('residual_position_status', '')}`",
            f"- Broker read observed: `{result.get('broker_read_observed')}`",
            f"- Broker mutation performed: `{result.get('broker_mutation_performed')}`",
            f"- Paper submit performed: `{result.get('paper_submit_performed')}`",
            f"- Live endpoint touched: `{result.get('live_endpoint_touched')}`",
            f"- Credential values exposed: `{result.get('credential_values_exposed')}`",
            f"- Blockers: `{', '.join(_text_list(result.get('blockers')))}`",
            f"- Next operator action: `{result.get('next_operator_action', '')}`",
            "",
            "Labels: " + ", ".join(_text_list(result.get("labels"))),
        ]
    )


def _operating_record(result: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "schema_version",
        "operator_command",
        "as_of",
        "prior_certification_id",
        "prior_client_order_id",
        "symbol",
        "approved_max_notional",
        "entry_client_order_id",
        "exit_client_order_id",
        "entry_attempt_count",
        "exit_attempt_count",
        "broker_read_observed",
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_mutation_performed",
        "live_endpoint_touched",
        "credential_values_exposed",
        "entry_submit_status",
        "entry_final_status",
        "entry_filled_qty",
        "entry_filled_avg_price",
        "exit_submit_status",
        "exit_final_status",
        "exit_filled_qty",
        "exit_filled_avg_price",
        "residual_position_status",
        "outcome_classification",
        "blockers",
        "next_operator_action",
    )
    return {field: _json_safe(result.get(field)) for field in fields}


def _lookup_by_client_order_id(
    client: Any,
    *,
    client_order_id: str,
    symbol: str,
) -> dict[str, Any]:
    for target in (client, _raw_trading_client(client)):
        for method_name in ("get_order_by_client_id", "get_order_by_client_order_id"):
            method = getattr(target, method_name, None)
            if not callable(method):
                continue
            try:
                order = method(client_order_id)
            except Exception:
                continue
            if order is not None:
                return _order_summary(order)
    try:
        orders = client.get_orders(
            AlpacaRecentOrderQuery(status_filter="all", symbol_filter=symbol)
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
    for index in range(checked_attempts):
        latest = _lookup_by_client_order_id(
            client,
            client_order_id=client_order_id,
            symbol=symbol,
        )
        if latest and (
            _order_status(latest) in _TERMINAL_STATUSES
            or index == checked_attempts - 1
        ):
            return latest
        if interval_seconds > 0 and index < checked_attempts - 1:
            time.sleep(interval_seconds)
    return {}


def _residual_position(client: Any, symbol: str) -> dict[str, Any]:
    try:
        positions = tuple(_position_summary(position) for position in client.get_positions())
    except Exception as exc:  # noqa: BLE001 - receipt only.
        return {"position_read_error": _safe_exception_message(exc), "position": {}}
    matches = [position for position in positions if _position_symbol(position) == symbol]
    if not matches:
        return {"position_read_error": "", "position": {}}
    if len(matches) != 1:
        return {
            "position_read_error": "multiple_BTCUSD_positions_observed",
            "position": {},
            "selected_symbol_positions": matches,
        }
    return {"position_read_error": "", "position": matches[0]}


def _request_fields(request: AlpacaOrderRequest) -> dict[str, str]:
    return {
        "client_order_id": request.client_order_id,
        "symbol": request.symbol,
        "side": request.side,
        "asset_class": request.asset_class,
        "order_type": request.order_type,
        "time_in_force": request.time_in_force,
        "quantity": _decimal_text(request.qty),
        "notional": _decimal_text(request.notional),
        "limit_price": _decimal_text(request.limit_price),
    }


def _account_payload(account: object) -> dict[str, Any]:
    data = _generic_payload(account)
    return {
        "id": _clean_text(_first_present(data, "id", "account_id")),
        "account_id": _clean_text(_first_present(data, "account_id", "id")),
        "account_number": _clean_text(data.get("account_number")),
        "status": _normalize_status(data.get("status")),
        "currency": _clean_text(data.get("currency")),
        "trading_blocked": data.get("trading_blocked") is True,
        "account_blocked": data.get("account_blocked") is True,
    }


def _asset_payload(asset: object) -> dict[str, Any]:
    data = _generic_payload(asset)
    return {
        "symbol": _normalize_symbol_text(data.get("symbol")),
        "asset_class": _normalized_enum_text(data.get("asset_class")),
        "tradable": data.get("tradable") is True,
        "fractionable": data.get("fractionable") is True,
        "status": _normalize_status(data.get("status")),
        "min_order_size": _clean_text(data.get("min_order_size")),
        "min_trade_increment": _clean_text(data.get("min_trade_increment")),
        "min_order_increment": _clean_text(data.get("min_order_increment")),
        "min_notional": _clean_text(data.get("min_notional")),
    }


def _position_summary(position: object) -> dict[str, Any]:
    data = _generic_payload(position)
    return {
        "symbol": _normalize_symbol_text(data.get("symbol")),
        "qty": _clean_text(data.get("qty")),
        "side": _normalize_status(data.get("side")),
        "market_value": _clean_text(data.get("market_value")),
        "average_entry_price": _clean_text(data.get("average_entry_price")),
    }


def _order_summary(order: object) -> dict[str, Any]:
    data = _generic_payload(order)
    order_id = _clean_text(_first_present(data, "order_id", "id"))
    return {
        "id": order_id,
        "order_id": order_id,
        "client_order_id": _clean_text(data.get("client_order_id")),
        "symbol": _normalize_symbol_text(data.get("symbol")),
        "asset_class": _normalized_enum_text(data.get("asset_class")),
        "side": _normalized_enum_text(data.get("side")),
        "order_type": _normalized_enum_text(_first_present(data, "order_type", "type")),
        "time_in_force": _normalized_enum_text(data.get("time_in_force")),
        "qty": _clean_text(data.get("qty")),
        "notional": _clean_text(data.get("notional")),
        "limit_price": _clean_text(data.get("limit_price")),
        "filled_qty": _clean_text(data.get("filled_qty")),
        "filled_avg_price": _clean_text(data.get("filled_avg_price")),
        "status": _normalize_status(data.get("status")),
        "reject_reason": _clean_text(data.get("reject_reason")),
        "submitted_at": _time_text(_first_present(data, "submitted_at", "created_at")),
        "filled_at": _time_text(data.get("filled_at")),
        "canceled_at": _time_text(_first_present(data, "canceled_at", "cancelled_at")),
    }


def _quote_payload(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bid_price": _clean_text(_first_present(data, "bid_price", "bp")),
        "ask_price": _clean_text(_first_present(data, "ask_price", "ap")),
        "price": _clean_text(_first_present(data, "price", "p")),
        "timestamp": _time_text(_first_present(data, "timestamp", "t")),
    }


def _approval_packet_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _clean_text(packet.get("schema_version")),
        "approval_packet_status": _clean_text(packet.get("approval_packet_status")),
        "approval_state": _clean_text(packet.get("approval_state")),
        "requested_future_authorization_scope": _clean_text(
            packet.get("requested_future_authorization_scope")
        ),
        "prior_certification_id": _clean_text(packet.get("prior_certification_id")),
        "prior_client_order_id": _clean_text(packet.get("prior_client_order_id")),
        "proposed_symbol": _normalize_symbol_text(packet.get("proposed_symbol")),
        "proposed_max_notional": _clean_text(packet.get("proposed_max_notional")),
        "blockers": _text_list(packet.get("blockers")),
        "labels": _text_list(packet.get("labels")),
    }


def _prior_certification_summary(prior: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _clean_text(prior.get("schema_version")),
        "client_order_id": _clean_text(prior.get("client_order_id")),
        "symbol": _normalize_symbol_text(prior.get("symbol")),
        "approved_max_notional": _clean_text(prior.get("approved_max_notional")),
        "outcome_classification": _clean_text(prior.get("outcome_classification")),
        "final_order_status": _clean_text(prior.get("final_order_status")),
        "filled_qty": _clean_text(
            _first_present(
                prior,
                "entry_filled_qty",
                "filled_qty",
                "unexpected_fill_or_position_impact",
            )
        ),
        "live_endpoint_touched": prior.get("live_endpoint_touched") is True,
        "credential_values_exposed": prior.get("credential_values_exposed") is True,
    }


def _expected_account_matched(
    account: Mapping[str, Any],
    expected_paper_account_id: str,
) -> bool:
    expected = _clean_text(expected_paper_account_id)
    return bool(expected and expected in _account_identity_values(account))


def _account_identity_values(account: Mapping[str, Any]) -> set[str]:
    return {
        text
        for text in (
            _clean_text(account.get("id")),
            _clean_text(account.get("account_id")),
            _clean_text(account.get("account_number")),
        )
        if text
    }


def _residual_position_status(position: Mapping[str, Any]) -> str:
    if not position:
        return "flat_or_no_BTCUSD_position_observed"
    qty = _position_quantity(position)
    if qty == Decimal("0"):
        return "flat_or_no_BTCUSD_position_observed"
    return "residual_BTCUSD_position_observed"


def _order_status(order: Mapping[str, Any]) -> str:
    return _normalize_status(order.get("status"))


def _order_symbol(order: Mapping[str, Any]) -> str:
    return _normalize_symbol_text(order.get("symbol"))


def _position_symbol(position: Mapping[str, Any]) -> str:
    return _normalize_symbol_text(position.get("symbol"))


def _position_quantity(position: Mapping[str, Any]) -> Decimal:
    qty = _decimal_or_none(position.get("qty")) or Decimal("0")
    side = _normalize_status(position.get("side"))
    if side == "short" and qty > Decimal("0"):
        return -qty
    return qty


def _filled_quantity(order: Mapping[str, Any]) -> Decimal:
    return _decimal_or_none(order.get("filled_qty")) or Decimal("0")


def _normalize_status(value: object) -> str:
    return _normalized_enum_text(value)


def _normalized_enum_text(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    normalized = text.lower()
    if "." in normalized:
        normalized = normalized.rsplit(".", maxsplit=1)[-1]
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
        return {str(key): _json_safe(item) for key, item in value.items()}
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
    allowed = set(_OBJECT_PAYLOAD_FIELDS) | {
        _payload_field_lookup_key(field) for field in _OBJECT_PAYLOAD_FIELDS
    }
    result: dict[str, Any] = {}
    for key, value in data.items():
        key_text = str(key)
        if key_text in allowed or _payload_field_lookup_key(key_text) in allowed:
            result[key_text] = _json_safe(value)
    return result


def _payload_field_lookup_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _object_data(value: object) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name in _OBJECT_PAYLOAD_FIELDS:
        if not hasattr(value, name):
            continue
        try:
            data[name] = getattr(value, name)
        except Exception:
            continue
    return data


def _raw_trading_client(client: Any) -> Any:
    raw = getattr(client, "raw_trading_client", None)
    return raw if raw is not None else client


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


def _artifact_reference(path_text: str) -> dict[str, Any]:
    path = Path(path_text) if path_text else Path()
    return {
        "path": path_text,
        "exists": bool(path_text and path.is_file()),
    }


def _artifact_entry(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _file_sha256(path) if path.is_file() else "",
    }


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
        raise ValueError(f"{field_name} must be a path-like value") from exc


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _first_decimal(data: Mapping[str, Any], *names: str) -> Decimal | None:
    for name in names:
        decimal_value = _decimal_or_none(data.get(name))
        if decimal_value is not None:
            return decimal_value
    return None


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


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _text_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [_clean_text(item) for item in value if _clean_text(item)]
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


def _normalized_paper_env(env: Mapping[str, str]) -> dict[str, str]:
    normalized = dict(env)
    if not normalized.get("ALPACA_API_KEY") and normalized.get("APCA_API_KEY_ID"):
        normalized["ALPACA_API_KEY"] = normalized["APCA_API_KEY_ID"]
    if not normalized.get("ALPACA_SECRET_KEY"):
        normalized["ALPACA_SECRET_KEY"] = (
            normalized.get("ALPACA_API_SECRET_KEY")
            or normalized.get("APCA_API_SECRET_KEY")
            or ""
        )
    return normalized


def _effective_paper_base_url(env: Mapping[str, str]) -> str:
    return env.get("ALPACA_PAPER_BASE_URL", "").strip() or DEFAULT_ALPACA_PAPER_BASE_URL


def _live_endpoint_indicator(env: Mapping[str, str]) -> bool:
    if env.get("APP_PROFILE", "").strip().lower() == "live":
        return True
    for name in ("ALPACA_BASE_URL", "ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL"):
        value = env.get(name, "")
        lowered = value.strip().lower()
        if "api.alpaca.markets" in lowered and "paper" not in lowered:
            return True
    return False


def _network_test_flag_enabled(env: Mapping[str, str]) -> bool:
    if env.get("PYTEST_ADDOPTS", "").find("--allow-network") >= 0:
        return True
    return any(env.get(name, "").strip() in {"1", "true", "True"} for name in _NETWORK_TEST_FLAG_NAMES)


def _normalize_endpoint(value: str) -> str:
    return value.strip().lower().rstrip("/")


def _first_nonempty(env: Mapping[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = _clean_text(env.get(name))
        if value:
            return value
    return ""


def _safe_exception_message(exc: Exception) -> str:
    message = str(exc)
    if message is None:
        return exc.__class__.__name__
    sanitized = _URL_PATTERN.sub("<redacted_url>", message)
    sanitized = _BEARER_PATTERN.sub("Bearer <redacted>", sanitized)
    sanitized = _SENSITIVE_VALUE_PATTERN.sub(
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
        text = _clean_text(value)
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
        prog="crypto-paper-fill-exit-certification",
        description="Run the explicit v5.10 BTCUSD paper fill/exit certification.",
    )
    parser.add_argument(
        "--paper-fill-exit-authorized",
        action="store_true",
        help="Explicit operator authorization for one bounded entry and one bounded exit.",
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument(
        "--approval-packet-path",
        default=str(DEFAULT_APPROVAL_PACKET_PATH),
        help="Path to v5.9 paper_fill_experiment_approval_packet.json.",
    )
    parser.add_argument(
        "--prior-certification-path",
        default=str(DEFAULT_PRIOR_CERTIFICATION_PATH),
        help="Path to v5.8 certification_result.json.",
    )
    parser.add_argument("--expected-paper-account-id", default="")
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--reconciliation-poll-attempts", type=int, default=3)
    parser.add_argument("--reconciliation-poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    result = run_crypto_paper_fill_exit_certification(
        output_root=args.output_root,
        approval_packet_path=args.approval_packet_path,
        prior_certification_path=args.prior_certification_path,
        timestamp=args.timestamp or None,
        paper_fill_exit_authorized=args.paper_fill_exit_authorized,
        expected_paper_account_id=args.expected_paper_account_id,
        reconciliation_poll_attempts=args.reconciliation_poll_attempts,
        reconciliation_poll_interval_seconds=args.reconciliation_poll_interval_seconds,
    )
    if args.format == "json":
        print(json.dumps(result, sort_keys=True))
    else:
        print(render_crypto_paper_fill_exit_certification_text(result))

    outcome = _clean_text(result.get("outcome_classification"))
    if outcome in {OUTCOME_BLOCKED_BEFORE_ENTRY, OUTCOME_BLOCKED_BEFORE_EXIT}:
        return 2
    if outcome in {
        OUTCOME_ENTRY_AMBIGUOUS,
        OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
        OUTCOME_EXIT_REJECTED_RESIDUAL_POSITION,
        OUTCOME_CERTIFICATION_AMBIGUOUS,
    }:
        return 3
    return 0


__all__ = [
    "OUTCOME_BLOCKED_BEFORE_ENTRY",
    "OUTCOME_BLOCKED_BEFORE_EXIT",
    "OUTCOME_CERTIFICATION_AMBIGUOUS",
    "OUTCOME_ENTRY_AMBIGUOUS",
    "OUTCOME_ENTRY_NO_FILL_NO_EXIT",
    "OUTCOME_ENTRY_REJECTED_NO_POSITION",
    "OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION",
    "OUTCOME_EXIT_REJECTED_RESIDUAL_POSITION",
    "OUTCOME_FILLED_EXIT_CONFIRMED",
    "OUTCOME_PARTIAL_FILL_EXIT_CONFIRMED",
    "REQUIRED_LABELS",
    "SCHEMA_VERSION",
    "V510_APPROVED_MAX_NOTIONAL",
    "V510_AUTHORIZATION_TEXT",
    "V510_PRIOR_CERTIFICATION_ID",
    "V510_PRIOR_CLIENT_ORDER_ID",
    "V510_SYMBOL",
    "deterministic_v510_client_order_ids",
    "render_crypto_paper_fill_exit_certification_text",
    "run_crypto_paper_fill_exit_certification",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
