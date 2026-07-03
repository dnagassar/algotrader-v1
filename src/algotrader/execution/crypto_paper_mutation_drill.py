"""v4.12C explicit bounded BTCUSD Alpaca paper mutation drill.

This module is deliberately separate from the normal crypto visibility
supervisor. The supervisor remains preview/no-submit; this runner requires an
explicit authorization flag and uses one deterministic client order id.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
import csv
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import (
    AlpacaOrderRequest,
    AlpacaRecentOrderQuery,
    V412C_CRYPTO_PAPER_MUTATION_DRILL_CLIENT_ORDER_ID_PREFIX,
)
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.crypto_paper_supervisor import (
    CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV,
    CryptoPaperSupervisorConfig,
    run_crypto_paper_supervisor,
)
from algotrader.signals.crypto_trend import (
    CRYPTO_TREND_STRATEGY_ID,
    normalize_crypto_symbol,
)

CRYPTO_PAPER_MUTATION_DRILL_SCHEMA_VERSION = "v4_12c_crypto_paper_mutation_drill_v1"
CRYPTO_PAPER_MUTATION_DRILL_COMMAND = "run_crypto_paper_mutation_drill"
CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_paper_mutation_drill/latest"
)
CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_SYMBOL = "BTCUSD"
CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_MAX_NOTIONAL = Decimal("11.00")
CRYPTO_PAPER_MUTATION_DRILL_LIMIT_DISCOUNT = Decimal("0.995")
CRYPTO_PAPER_MUTATION_DRILL_PRICE_QUANTUM = Decimal("0.01")
CRYPTO_PAPER_MUTATION_DRILL_TIME_IN_FORCE = "gtc"
CRYPTO_PAPER_MUTATION_DRILL_ORDER_TYPE = "limit"
CRYPTO_PAPER_MUTATION_DRILL_SIDE = "buy"

OUTCOME_BLOCKED_PRE_SUBMIT = "crypto_paper_drill_blocked_pre_submit_gate"
OUTCOME_IDEMPOTENT_EXISTING_ORDER = (
    "crypto_paper_drill_idempotent_existing_order_reconciled"
)
OUTCOME_SUBMITTED_REJECTED = "crypto_paper_drill_submitted_then_rejected"
OUTCOME_SUBMITTED_FILLED = "crypto_paper_drill_submitted_filled_no_flatten"
OUTCOME_SUBMITTED_CANCELLED = "crypto_paper_drill_submitted_cancel_confirmed"
OUTCOME_SUBMITTED_PARTIAL_CANCELLED = (
    "crypto_paper_drill_submitted_partial_fill_then_cancelled"
)
OUTCOME_CANCEL_AMBIGUOUS_RECONCILED = (
    "crypto_paper_drill_cancel_ambiguous_reconciled"
)
OUTCOME_UNRESOLVED = "crypto_paper_drill_unresolved_order_outcome"
OUTCOME_AMBIGUOUS_SUBMIT = "crypto_paper_drill_ambiguous_submit_outcome"

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
_PUBLIC_ENV_NAMES = (
    "APP_PROFILE",
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
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
    "new",
    "partially_filled",
    "pending_new",
}
_OPEN_STATUSES = _CANCELABLE_STATUSES | {"pending_cancel", "accepted_for_bidding"}
_KNOWN_CRYPTO_SYMBOLS = {"BTCUSD", "ETHUSD", "BTC/USD", "ETH/USD"}
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|secret(?:[_-]?key)?|token)\b"
    r"\s*[:=]\s*[^,\s;)]+"
)
_URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
_SAFE_MESSAGE_LIMIT = 240
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

BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]

__all__ = [
    "CRYPTO_PAPER_MUTATION_DRILL_COMMAND",
    "CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_MAX_NOTIONAL",
    "CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_SYMBOL",
    "CRYPTO_PAPER_MUTATION_DRILL_SCHEMA_VERSION",
    "crypto_paper_mutation_environment_preflight",
    "deterministic_crypto_paper_drill_client_order_id",
    "render_crypto_paper_mutation_drill_text",
    "run_crypto_paper_mutation_drill",
]


def run_crypto_paper_mutation_drill(
    *,
    output_root: str | Path = CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_OUTPUT_ROOT,
    bars_csv: str | Path = CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV,
    timestamp: datetime | str | None = None,
    env: Mapping[str, str] | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    crypto_paper_mutation_authorized: bool = False,
    expected_paper_account_id: str | None = None,
    target_symbol: str = CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_SYMBOL,
    selected_symbol_override_reason: str = "",
    max_drill_notional: Decimal | str = CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_MAX_NOTIONAL,
    reconciliation_poll_attempts: int = 3,
    reconciliation_poll_interval_seconds: float = 1.0,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    """Run the bounded v4.12C paper drill, failing closed before submit."""

    generated_at = _utc_datetime(timestamp or datetime.now(UTC), "timestamp")
    root = _path(output_root, "output_root")
    bars_path = _path(bars_csv, "bars_csv")
    source_env = _env_mapping(env)
    expected_account = (
        _clean_text(expected_paper_account_id)
        if expected_paper_account_id is not None
        else _first_nonempty(source_env, _EXPECTED_ACCOUNT_ENV_NAMES)
    )
    preflight = crypto_paper_mutation_environment_preflight(
        source_env,
        expected_paper_account_id=expected_account,
    )
    symbol = normalize_crypto_symbol(target_symbol)
    max_notional = _positive_decimal(max_drill_notional, "max_drill_notional")
    client_order_id = deterministic_crypto_paper_drill_client_order_id(symbol)
    base = _base_packet(
        output_root=root,
        bars_csv=bars_path,
        generated_at=generated_at,
        preflight=preflight,
        explicit_authorization=crypto_paper_mutation_authorized,
        expected_paper_account_id_loaded=bool(expected_account),
        target_symbol=symbol,
        selected_symbol_override_reason=selected_symbol_override_reason,
        max_notional=max_notional,
        client_order_id=client_order_id,
    )

    early_blockers = _environment_gate_blockers(
        preflight,
        authorized=crypto_paper_mutation_authorized,
    )
    if early_blockers:
        return _finalize_packet(
            base,
            outcome_classification=OUTCOME_BLOCKED_PRE_SUBMIT,
            blocker=",".join(early_blockers),
            next_operator_action="repair_paper_shell_preflight_before_crypto_drill",
            write_artifacts=write_artifacts,
        )

    if not bars_path.is_file():
        return _finalize_packet(
            {**base, "bars_gate": {"bars_csv_exists": False}},
            outcome_classification=OUTCOME_BLOCKED_PRE_SUBMIT,
            blocker="crypto_bars_csv_missing",
            next_operator_action="refresh_crypto_bars_before_crypto_drill",
            write_artifacts=write_artifacts,
        )

    client_result = _build_broker_client(source_env, broker_client_factory)
    client = client_result["client"]
    if client is None:
        return _finalize_packet(
            {
                **base,
                "broker_client_error": client_result["error"],
            },
            outcome_classification=OUTCOME_BLOCKED_PRE_SUBMIT,
            blocker="paper_broker_client_unavailable",
            next_operator_action="repair_paper_broker_client_before_crypto_drill",
            write_artifacts=write_artifacts,
        )

    account_result = _read_account(client)
    account_payload = account_result["account"]
    account_blockers = _account_gate_blockers(
        account_payload,
        expected_paper_account_id=expected_account,
        account_error=account_result["error"],
    )

    supervisor_result = _run_supervisor(
        client=client,
        bars_csv=bars_path,
        generated_at=generated_at,
        env=source_env,
    )
    supervisor_record = supervisor_result["record"]
    asset_observation = _selected_asset_observation(
        client,
        _clean_text(supervisor_record.get("selected_symbol")) or symbol,
    )
    observed_record = _record_with_observed_asset_metadata(
        supervisor_record,
        asset_observation,
    )
    supervisor_blockers = _supervisor_gate_blockers(
        observed_record,
        target_symbol=symbol,
        selected_symbol_override_reason=selected_symbol_override_reason,
    )

    latest_bar_result = _latest_usable_bar(
        bars_path,
        symbol=symbol,
        as_of=generated_at,
    )
    order_design, design_blockers = _build_order_design(
        supervisor_record=observed_record,
        latest_bar=latest_bar_result["bar"],
        symbol=symbol,
        max_notional=max_notional,
        client_order_id=client_order_id,
    )

    scan_result = _scan_open_orders(
        client,
        symbol=symbol,
        crypto_symbols=_crypto_symbols(supervisor_record),
    )
    position_result = _scan_positions(
        client,
        symbol=symbol,
        crypto_symbols=_crypto_symbols(supervisor_record),
    )
    existing_order = _lookup_by_client_order_id(
        client,
        client_order_id=client_order_id,
        symbol=symbol,
    )

    pre_submit_blockers = _dedupe(
        (
            *account_blockers,
            *supervisor_blockers,
            *_asset_observation_blockers(asset_observation),
            *latest_bar_result["blockers"],
            *design_blockers,
            *scan_result["blockers"],
            *position_result["blockers"],
        )
    )
    observed = {
        **base,
        "account_observation": account_payload,
        "expected_account_matched": _expected_account_matched(
            account_payload,
            expected_account,
        ),
        "supervisor_observation": observed_record,
        "selected_asset_observation": asset_observation,
        "latest_bar_observation": latest_bar_result["receipt"],
        "order_design": order_design,
        "open_order_scan": scan_result["receipt"],
        "position_scan": position_result["receipt"],
        "existing_client_order_id_order": existing_order,
        "pre_submit_gate_blockers": pre_submit_blockers,
    }

    if existing_order:
        final_order = _order_summary(existing_order)
        return _finalize_packet(
            {
                **observed,
                "final_order": final_order,
                "final_broker_order_status": final_order.get("status", ""),
                "fill_status": _fill_status(final_order),
            },
            outcome_classification=OUTCOME_IDEMPOTENT_EXISTING_ORDER,
            blocker="existing_client_order_id_reconciled_no_submit",
            next_operator_action="review_existing_drill_order_before_any_future_drill",
            paper_submit_performed=False,
            broker_mutation_performed=False,
            write_artifacts=write_artifacts,
        )

    if pre_submit_blockers:
        return _finalize_packet(
            observed,
            outcome_classification=OUTCOME_BLOCKED_PRE_SUBMIT,
            blocker=",".join(pre_submit_blockers),
            next_operator_action="repair_pre_submit_gate_before_crypto_drill",
            write_artifacts=write_artifacts,
        )

    request = AlpacaOrderRequest(
        client_order_id=client_order_id,
        symbol=symbol,
        side=CRYPTO_PAPER_MUTATION_DRILL_SIDE,
        asset_class="crypto",
        qty=_decimal_or_none(order_design.get("quantity")),
        order_type=CRYPTO_PAPER_MUTATION_DRILL_ORDER_TYPE,
        time_in_force=CRYPTO_PAPER_MUTATION_DRILL_TIME_IN_FORCE,
        limit_price=_decimal_or_none(order_design.get("limit_price")),
    )
    lifecycle = _submit_cancel_reconcile(
        client=client,
        request=request,
        poll_attempts=reconciliation_poll_attempts,
        poll_interval_seconds=reconciliation_poll_interval_seconds,
    )
    final_order = _mapping(lifecycle.get("final_order"))
    residual_position = {}
    if _filled_quantity(final_order) > Decimal("0") or _order_status(final_order) == "filled":
        residual_position = _residual_position(client, symbol)

    return _finalize_packet(
        {
            **observed,
            "actual_submitted_request_fields": _request_fields(request),
            "submit_result": _mapping(lifecycle.get("submit_result")),
            "cancel_result": _mapping(lifecycle.get("cancel_result")),
            "reconciliation": {
                "final_order": final_order,
                "final_order_status": _order_status(final_order),
                "filled_qty": _decimal_text(_filled_quantity(final_order)),
                "filled_avg_price": _decimal_text(
                    _decimal_or_none(final_order.get("filled_avg_price"))
                ),
                "notional_estimate": _notional_estimate(final_order),
                "residual_position": residual_position,
                "blocker": _clean_text(lifecycle.get("blocker")),
            },
            "final_order": final_order,
            "final_broker_order_status": _order_status(final_order),
            "fill_status": _fill_status(final_order),
        },
        outcome_classification=_clean_text(lifecycle.get("outcome_classification")),
        blocker=_clean_text(lifecycle.get("blocker")),
        next_operator_action=_clean_text(lifecycle.get("next_operator_action")),
        paper_submit_performed=_bool(
            _mapping(lifecycle.get("submit_result")).get("submit_attempted")
        ),
        broker_mutation_performed=(
            _bool(_mapping(lifecycle.get("submit_result")).get("submit_attempted"))
            or _bool(_mapping(lifecycle.get("cancel_result")).get("cancel_attempted"))
        ),
        paper_cancel_performed=_bool(
            _mapping(lifecycle.get("cancel_result")).get("cancel_attempted")
        ),
        write_artifacts=write_artifacts,
    )


def crypto_paper_mutation_environment_preflight(
    env: Mapping[str, str] | None = None,
    *,
    expected_paper_account_id: str = "",
) -> dict[str, bool]:
    """Return boolean-only credential, endpoint, and expected-account state."""

    source = _env_mapping(env)
    app_profile = source.get("APP_PROFILE", "").strip().lower()
    effective_paper_base_url = _effective_paper_base_url(source)
    paper_endpoint_exact_match = (
        _normalize_endpoint(effective_paper_base_url)
        == _normalize_endpoint(DEFAULT_ALPACA_PAPER_BASE_URL)
    )
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
        "paper_endpoint_exact_match_indicator": paper_endpoint_exact_match,
        "live_endpoint_indicator": _live_endpoint_indicator(source),
    }


def deterministic_crypto_paper_drill_client_order_id(symbol: str) -> str:
    checked_symbol = normalize_crypto_symbol(symbol).lower()
    return f"{V412C_CRYPTO_PAPER_MUTATION_DRILL_CLIENT_ORDER_ID_PREFIX}{checked_symbol}"


def render_crypto_paper_mutation_drill_text(packet: Mapping[str, Any]) -> str:
    """Render a compact sanitized receipt for the operator shell."""

    preflight = packet.get("operator_preflight", {})
    if not isinstance(preflight, Mapping):
        preflight = {}
    lines = [
        f"crypto_paper_mutation_drill_command={CRYPTO_PAPER_MUTATION_DRILL_COMMAND}",
        "crypto_paper_mutation_drill_scope=alpaca_paper_only_btcusd_bounded_limit_buy",
        f"crypto_paper_mutation_authorized={_bool_text(packet.get('explicit_authorization_flag_observed'))}",
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
            f"outcome_classification={_clean_text(packet.get('outcome_classification'))}",
            f"blocker={_clean_text(packet.get('blocker'))}",
            f"account_status={_clean_text(packet.get('account_status'))}",
            f"account_blocked={_bool_text(packet.get('account_blocked'))}",
            f"trading_blocked={_bool_text(packet.get('trading_blocked'))}",
            f"expected_account_matched={_bool_text(packet.get('expected_account_matched'))}",
            f"selected_symbol={_clean_text(packet.get('selected_symbol'))}",
            f"side={_clean_text(packet.get('side'))}",
            f"order_type={_clean_text(packet.get('order_type'))}",
            f"limit_price={_clean_text(packet.get('limit_price'))}",
            f"quantity={_clean_text(packet.get('quantity'))}",
            f"target_notional={_clean_text(packet.get('target_notional'))}",
            f"estimated_notional={_clean_text(packet.get('estimated_notional'))}",
            f"max_drill_notional={_clean_text(packet.get('max_drill_notional'))}",
            f"min_notional={_clean_text(packet.get('min_notional'))}",
            f"client_order_id={_clean_text(packet.get('client_order_id'))}",
            f"submit_attempted={_bool_text(packet.get('submit_attempted'))}",
            f"submit_status={_clean_text(packet.get('submit_status'))}",
            f"cancel_attempted={_bool_text(packet.get('cancel_attempted'))}",
            f"cancel_confirmed={_bool_text(packet.get('cancel_confirmed'))}",
            f"final_broker_order_status={_clean_text(packet.get('final_broker_order_status'))}",
            f"fill_status={_clean_text(packet.get('fill_status'))}",
            f"broker_read_performed={_bool_text(packet.get('broker_read_performed'))}",
            f"paper_submit_authorized={_bool_text(packet.get('paper_submit_authorized'))}",
            f"paper_submit_performed={_bool_text(packet.get('paper_submit_performed'))}",
            f"broker_mutation_performed={_bool_text(packet.get('broker_mutation_performed'))}",
            f"paper_cancel_performed={_bool_text(packet.get('paper_cancel_performed'))}",
            f"live_mutation_performed={_bool_text(packet.get('live_mutation_performed'))}",
            f"next_operator_action={_clean_text(packet.get('next_operator_action'))}",
        ]
    )
    artifacts = packet.get("artifact_paths")
    if isinstance(artifacts, Mapping):
        for key in ("latest_status", "drill_receipt", "operating_brief", "manifest"):
            lines.append(f"artifact_{key}={_clean_text(artifacts.get(key))}")
    return "\n".join(lines)


def _base_packet(
    *,
    output_root: Path,
    bars_csv: Path,
    generated_at: datetime,
    preflight: Mapping[str, bool],
    explicit_authorization: bool,
    expected_paper_account_id_loaded: bool,
    target_symbol: str,
    selected_symbol_override_reason: str,
    max_notional: Decimal,
    client_order_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": CRYPTO_PAPER_MUTATION_DRILL_SCHEMA_VERSION,
        "operator_command": CRYPTO_PAPER_MUTATION_DRILL_COMMAND,
        "run_timestamp": generated_at.isoformat(),
        "output_root": str(output_root),
        "bars_csv": str(bars_csv),
        "explicit_authorization_flag_required": True,
        "explicit_authorization_flag_observed": explicit_authorization,
        "paper_submit_authorized": explicit_authorization,
        "paper_cancel_authorized": explicit_authorization,
        "expected_paper_account_id_loaded": expected_paper_account_id_loaded,
        "operator_preflight": dict(preflight),
        "target_symbol": target_symbol,
        "selected_symbol": target_symbol,
        "selected_symbol_override_reason": _clean_text(selected_symbol_override_reason),
        "symbol": target_symbol,
        "asset_class": "crypto",
        "side": CRYPTO_PAPER_MUTATION_DRILL_SIDE,
        "order_type": CRYPTO_PAPER_MUTATION_DRILL_ORDER_TYPE,
        "time_in_force": CRYPTO_PAPER_MUTATION_DRILL_TIME_IN_FORCE,
        "max_drill_notional": str(max_notional),
        "configured_drill_cap": str(max_notional),
        "client_order_id": client_order_id,
        "deterministic_client_order_id": client_order_id,
        "strategy_id": CRYPTO_TREND_STRATEGY_ID,
        "strategy_adapter_mode": "preview_only",
        "normal_crypto_visibility_path_remains_no_submit": True,
        "no_submit_mode_can_mutate": False,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
        "safety_labels": [
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
            "v4.12c_explicit_crypto_paper_mutation_drill",
        ],
        "live_endpoint_used": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "broker_mutation_performed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "cancel_confirmed": False,
        "submit_call_count_max": 1,
        "retry_submit_after_rejection_allowed": False,
        "flatten_or_close_order_allowed": False,
    }


def _environment_gate_blockers(
    preflight: Mapping[str, bool],
    *,
    authorized: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not authorized:
        blockers.append("crypto_paper_mutation_authorization_required")
    if preflight.get("APP_PROFILE_is_live") is True or preflight.get("live_endpoint_indicator") is True:
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
    except Exception as exc:  # noqa: BLE001 - drill receipt fails closed.
        return {"client": None, "error": _safe_exception_message(exc)}
    return {"client": client, "error": ""}


def _read_account(client: Any) -> dict[str, Any]:
    try:
        return {"account": _account_payload(client.get_account()), "error": ""}
    except Exception as exc:  # noqa: BLE001 - drill receipt fails closed.
        return {"account": {}, "error": _safe_exception_message(exc)}


def _account_gate_blockers(
    account: Mapping[str, Any],
    *,
    expected_paper_account_id: str,
    account_error: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if account_error:
        blockers.append("paper_account_read_failed")
        return tuple(blockers)
    if not account:
        blockers.append("paper_account_status_unobserved")
        return tuple(blockers)
    values = _account_identity_values(account)
    if expected_paper_account_id and expected_paper_account_id not in values:
        blockers.append("paper_account_expected_id_mismatch")
    status = _clean_text(account.get("status"))
    normalized_status = _normalized_enum_text(status)
    if not normalized_status:
        blockers.append("paper_account_status_unobserved")
    elif normalized_status not in {"active", "account_active"}:
        blockers.append("paper_account_not_active")
    if _bool(account.get("trading_blocked")) or _bool(account.get("account_blocked")):
        blockers.append("paper_account_trading_blocked")
    return tuple(blockers)


def _run_supervisor(
    *,
    client: Any,
    bars_csv: Path,
    generated_at: datetime,
    env: Mapping[str, str],
) -> dict[str, Any]:
    try:
        record = run_crypto_paper_supervisor(
            CryptoPaperSupervisorConfig(
                output_root=CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_OUTPUT_ROOT,
                bars_csv=bars_csv,
            ),
            env=_public_broker_env(env),
            broker=client,
            timestamp=generated_at,
            write_artifacts=False,
        )
        return {"record": record, "error": ""}
    except Exception as exc:  # noqa: BLE001 - drill receipt fails closed.
        return {"record": {}, "error": _safe_exception_message(exc)}


def _supervisor_gate_blockers(
    record: Mapping[str, Any],
    *,
    target_symbol: str,
    selected_symbol_override_reason: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not record:
        return ("crypto_supervisor_observation_failed",)
    selected_symbol = _clean_text(record.get("selected_symbol"))
    if record.get("broker_read_performed") is not True:
        blockers.append("broker_read_not_performed")
    if record.get("broker_state_mode") != "alpaca_paper_observed":
        blockers.append("alpaca_paper_observed_state_required")
    if record.get("crypto_trading_supported") is not True:
        blockers.append("crypto_trading_not_supported")
    if selected_symbol != target_symbol:
        blockers.append("selected_symbol_mismatch")
    if selected_symbol != CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_SYMBOL and not _clean_text(
        selected_symbol_override_reason
    ):
        blockers.append("non_btcusd_symbol_requires_recorded_reason")
    if record.get("selected_symbol_tradable") is not True:
        blockers.append("selected_symbol_not_tradable")
    if record.get("selected_symbol_fractionable") is not True:
        blockers.append("selected_symbol_fractionable_required")
    if not _clean_text(record.get("min_notional")):
        blockers.append("min_notional_missing")
    if record.get("data_freshness_status") != "current_for_24_7_crypto_lab":
        blockers.append("crypto_bars_not_current")
    strategy_signal = record.get("strategy_signal")
    if isinstance(strategy_signal, Mapping):
        if _decimal_or_none(strategy_signal.get("usable_bar_count")) is not None:
            if int(Decimal(str(strategy_signal.get("usable_bar_count")))) < 50:
                blockers.append("insufficient_crypto_strategy_history")
        if strategy_signal.get("posture") == "insufficient_history":
            blockers.append("insufficient_crypto_strategy_history")
    if record.get("strategy_adapter_mode") != "preview_only":
        blockers.append("crypto_strategy_adapter_preview_only_required")
    if record.get("no_submit_mode") is not True:
        blockers.append("normal_crypto_visibility_no_submit_mode_required")
    if record.get("paper_submit_performed") is not False:
        blockers.append("normal_crypto_visibility_paper_submit_must_be_false")
    if record.get("broker_mutation_performed") is not False:
        blockers.append("normal_crypto_visibility_broker_mutation_must_be_false")
    if record.get("live_mutation_performed") is not False:
        blockers.append("normal_crypto_visibility_live_mutation_must_be_false")
    return _dedupe(blockers)


def _selected_asset_observation(client: Any, symbol: str) -> dict[str, Any]:
    try:
        assets = tuple(_generic_payload(asset) for asset in client.list_assets())
    except Exception as exc:  # noqa: BLE001 - receipt fails closed.
        return {
            "asset_read_error": _safe_exception_message(exc),
            "selected_asset_observed": False,
            "selected_symbol": symbol,
        }
    selected = next(
        (
            asset
            for asset in assets
            if _normalize_symbol_text(asset.get("symbol")) == symbol
            and _normalized_enum_text(asset.get("asset_class") or asset.get("class"))
            == "crypto"
        ),
        None,
    )
    if selected is None:
        return {
            "asset_read_error": "",
            "selected_asset_observed": False,
            "selected_symbol": symbol,
            "observed_crypto_asset_count": len(
                [
                    asset
                    for asset in assets
                    if _normalized_enum_text(
                        asset.get("asset_class") or asset.get("class")
                    )
                    == "crypto"
                ]
            ),
        }
    return {
        "asset_read_error": "",
        "selected_asset_observed": True,
        "selected_symbol": symbol,
        "selected_symbol_tradable": _bool_field(selected, "tradable"),
        "selected_symbol_fractionable": _bool_field(selected, "fractionable"),
        "min_notional": _clean_text(
            _first_present(selected, "min_notional", "min_order_notional")
        ),
        "min_order_size": _clean_text(selected.get("min_order_size")),
        "min_trade_increment": _clean_text(selected.get("min_trade_increment")),
        "min_order_increment": _clean_text(selected.get("min_order_increment")),
    }


def _record_with_observed_asset_metadata(
    record: Mapping[str, Any],
    asset_observation: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(record)
    for field in (
        "selected_symbol_tradable",
        "selected_symbol_fractionable",
        "min_notional",
        "min_order_size",
        "min_trade_increment",
        "min_order_increment",
    ):
        if field in asset_observation:
            merged[field] = asset_observation[field]
    return merged


def _asset_observation_blockers(asset_observation: Mapping[str, Any]) -> tuple[str, ...]:
    blockers: list[str] = []
    if asset_observation.get("asset_read_error"):
        blockers.append("selected_asset_observation_failed")
    if asset_observation.get("selected_asset_observed") is not True:
        blockers.append("selected_crypto_asset_not_observed")
    if not _clean_text(asset_observation.get("min_notional")):
        blockers.append("min_notional_missing")
    return tuple(blockers)


def _latest_usable_bar(path: Path, *, symbol: str, as_of: datetime) -> dict[str, Any]:
    blockers: list[str] = []
    latest: Bar | None = None
    if not path.is_file():
        blockers.append("crypto_bars_csv_missing")
    else:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                for row in csv.DictReader(stream):
                    bar = _bar_from_row(row)
                    if bar.symbol == symbol and bar.timestamp <= as_of:
                        if latest is None or bar.timestamp > latest.timestamp:
                            latest = bar
        except Exception as exc:  # noqa: BLE001 - receipt fails closed.
            blockers.append(f"crypto_bars_csv_invalid:{exc.__class__.__name__}")
    if latest is None:
        blockers.append("latest_crypto_bar_missing")
    receipt = {
        "latest_bar_at": "" if latest is None else latest.timestamp.isoformat(),
        "latest_bar_close": "" if latest is None else str(latest.close),
        "bar_symbol": "" if latest is None else latest.symbol,
        "bars_csv_sha256": _file_sha256(path) if path.is_file() else "",
    }
    return {"bar": latest, "blockers": tuple(blockers), "receipt": receipt}


def _build_order_design(
    *,
    supervisor_record: Mapping[str, Any],
    latest_bar: Bar | None,
    symbol: str,
    max_notional: Decimal,
    client_order_id: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    blockers: list[str] = []
    min_notional = _decimal_or_none(supervisor_record.get("min_notional"))
    min_order_size = _decimal_or_none(supervisor_record.get("min_order_size"))
    min_trade_increment = _decimal_or_none(supervisor_record.get("min_trade_increment"))
    if min_notional is None:
        blockers.append("min_notional_missing")
    elif min_notional > max_notional:
        blockers.append("min_notional_exceeds_drill_cap")
    if latest_bar is None:
        blockers.append("latest_crypto_bar_missing")
    if min_trade_increment is None:
        min_trade_increment = Decimal("0.000000001")

    if blockers:
        return {
            "symbol": symbol,
            "client_order_id": client_order_id,
            "side": CRYPTO_PAPER_MUTATION_DRILL_SIDE,
            "order_type": CRYPTO_PAPER_MUTATION_DRILL_ORDER_TYPE,
            "time_in_force": CRYPTO_PAPER_MUTATION_DRILL_TIME_IN_FORCE,
            "max_drill_notional": str(max_notional),
            "min_notional": "" if min_notional is None else str(min_notional),
            "min_order_size": "" if min_order_size is None else str(min_order_size),
            "min_trade_increment": str(min_trade_increment),
        }, tuple(blockers)

    assert min_notional is not None
    assert latest_bar is not None
    target_notional = min_notional
    limit_price = (latest_bar.close * CRYPTO_PAPER_MUTATION_DRILL_LIMIT_DISCOUNT).quantize(
        CRYPTO_PAPER_MUTATION_DRILL_PRICE_QUANTUM
    )
    if limit_price <= Decimal("0"):
        blockers.append("limit_price_not_positive")
        limit_price = latest_bar.close
    required_quantity = target_notional / limit_price
    if min_order_size is not None:
        required_quantity = max(required_quantity, min_order_size)
    quantity = _round_up_to_increment(required_quantity, min_trade_increment)
    estimated_notional = (quantity * limit_price).quantize(Decimal("0.00000001"))
    if estimated_notional < min_notional:
        quantity = _round_up_to_increment(
            min_notional / limit_price,
            min_trade_increment,
        )
        estimated_notional = (quantity * limit_price).quantize(Decimal("0.00000001"))
    if estimated_notional > max_notional:
        blockers.append("rounded_order_notional_exceeds_drill_cap")
    if min_order_size is not None and quantity < min_order_size:
        blockers.append("quantity_below_min_order_size_after_rounding")
    if quantity <= Decimal("0"):
        blockers.append("quantity_not_positive")

    design = {
        "symbol": symbol,
        "side": CRYPTO_PAPER_MUTATION_DRILL_SIDE,
        "asset_class": "crypto",
        "order_type": CRYPTO_PAPER_MUTATION_DRILL_ORDER_TYPE,
        "time_in_force": CRYPTO_PAPER_MUTATION_DRILL_TIME_IN_FORCE,
        "client_order_id": client_order_id,
        "deterministic_client_order_id": client_order_id,
        "latest_bar_close": str(latest_bar.close),
        "limit_price": str(limit_price),
        "limit_price_derivation": (
            "latest_usable_crypto_bar_close * 0.995, rounded to 0.01 USD"
        ),
        "target_notional": str(target_notional),
        "estimated_notional": str(estimated_notional),
        "quantity": str(quantity),
        "quantity_derivation": (
            "ceil(max(min_notional / limit_price, min_order_size) "
            "/ min_trade_increment) * min_trade_increment"
        ),
        "min_notional": str(min_notional),
        "min_order_size": "" if min_order_size is None else str(min_order_size),
        "min_trade_increment": str(min_trade_increment),
        "max_drill_notional": str(max_notional),
        "rounding_decisions": [
            "target_notional=min_notional",
            f"limit_discount={CRYPTO_PAPER_MUTATION_DRILL_LIMIT_DISCOUNT}",
            f"price_quantum={CRYPTO_PAPER_MUTATION_DRILL_PRICE_QUANTUM}",
            f"quantity_rounded_up_to_increment={min_trade_increment}",
        ],
    }
    return design, tuple(blockers)


def _scan_open_orders(
    client: Any,
    *,
    symbol: str,
    crypto_symbols: set[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        orders = tuple(
            _order_summary(order)
            for order in client.get_orders(
                AlpacaRecentOrderQuery(status_filter="open", limit=100)
            )
        )
    except Exception as exc:  # noqa: BLE001 - receipt fails closed.
        return {
            "blockers": ("open_order_scan_failed",),
            "receipt": {"open_order_scan_error": _safe_exception_message(exc)},
        }
    selected = [
        order
        for order in orders
        if _order_symbol(order) == symbol and _order_status(order) not in _TERMINAL_STATUSES
    ]
    conflicting_crypto = [
        order
        for order in orders
        if _is_crypto_order(order, crypto_symbols)
        and _order_status(order) not in _TERMINAL_STATUSES
    ]
    if selected:
        blockers.append("open_selected_symbol_order_exists")
    if conflicting_crypto:
        blockers.append("open_conflicting_crypto_order_exists")
    return {
        "blockers": tuple(blockers),
        "receipt": {
            "open_order_count": len(orders),
            "open_selected_symbol_order_observed": bool(selected),
            "open_conflicting_crypto_order_observed": bool(conflicting_crypto),
            "open_selected_symbol_orders": selected,
            "open_conflicting_crypto_orders": conflicting_crypto,
        },
    }


def _scan_positions(
    client: Any,
    *,
    symbol: str,
    crypto_symbols: set[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        positions = tuple(_position_summary(position) for position in client.get_positions())
    except Exception as exc:  # noqa: BLE001 - receipt fails closed.
        return {
            "blockers": ("position_scan_failed",),
            "receipt": {"position_scan_error": _safe_exception_message(exc)},
        }
    selected = [
        position
        for position in positions
        if _position_symbol(position) == symbol
        and (_decimal_or_none(position.get("qty")) or Decimal("0")) != Decimal("0")
    ]
    crypto = [
        position
        for position in positions
        if _position_symbol(position) in crypto_symbols
        and (_decimal_or_none(position.get("qty")) or Decimal("0")) != Decimal("0")
    ]
    if selected:
        blockers.append("existing_selected_symbol_position_ambiguous")
    if crypto:
        blockers.append("existing_crypto_position_ambiguous")
    return {
        "blockers": tuple(blockers),
        "receipt": {
            "position_count": len(positions),
            "selected_symbol_position_observed": bool(selected),
            "crypto_position_observed": bool(crypto),
            "selected_symbol_positions": selected,
            "crypto_positions": crypto,
        },
    }


def _submit_cancel_reconcile(
    *,
    client: Any,
    request: AlpacaOrderRequest,
    poll_attempts: int,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    submit_ambiguous = False
    cancel_result: dict[str, Any] = {
        "cancel_attempted": False,
        "cancel_confirmed": False,
        "cancel_ambiguous": False,
    }
    try:
        submit_response = client.submit_order(request)
        submitted_order = _order_summary(submit_response)
        submit_result = {
            "submit_attempted": True,
            "submit_call_count": 1,
            "submit_accepted": _submit_accepted(submitted_order),
            "submit_status": _order_status(submitted_order),
            "submit_error": "",
            "submit_error_type": "",
            "submitted_order": submitted_order,
        }
    except Exception as exc:  # noqa: BLE001 - submit may be ambiguous.
        submit_ambiguous = True
        submit_result = {
            "submit_attempted": True,
            "submit_call_count": 1,
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
    ) or _mapping(submit_result.get("submitted_order"))

    if not latest:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order={},
            outcome=OUTCOME_AMBIGUOUS_SUBMIT if submit_ambiguous else OUTCOME_UNRESOLVED,
            blocker="submitted_order_not_reconciled_after_single_submit_call",
            next_action="operator_reconcile_ambiguous_crypto_order_before_any_future_drill",
        )

    status = _order_status(latest)
    if status == "rejected":
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_SUBMITTED_REJECTED,
            blocker="submit_rejected_no_retry",
            next_action="review_rejected_crypto_drill_before_any_future_drill",
        )
    if status == "filled":
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_SUBMITTED_FILLED,
            blocker="filled_before_cancel_no_flatten_authorized",
            next_action="operator_review_residual_crypto_position_before_cleanup",
        )
    if status in _TERMINAL_STATUSES:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=_classify_final_order(latest, cancel_ambiguous=False),
            blocker="none",
            next_action="review_terminal_crypto_drill_order",
        )
    if status not in _CANCELABLE_STATUSES:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_UNRESOLVED,
            blocker="submitted_order_not_cancelable",
            next_action="operator_reconcile_unresolved_crypto_order_before_any_future_drill",
        )

    order_id = _clean_text(latest.get("order_id") or latest.get("id"))
    if not order_id:
        return _lifecycle_result(
            submit_result=submit_result,
            cancel_result=cancel_result,
            final_order=latest,
            outcome=OUTCOME_UNRESOLVED,
            blocker="submitted_order_id_missing_for_same_order_cancel",
            next_action="operator_reconcile_unresolved_crypto_order_before_any_future_drill",
        )

    cancel_ambiguous = False
    try:
        cancel_response = _request_order_cancellation(client, order_id)
        cancel_response_payload = _generic_payload(cancel_response)
    except Exception as exc:  # noqa: BLE001 - cancel may be ambiguous.
        cancel_ambiguous = True
        cancel_response_payload = {
            "cancel_error": _safe_exception_message(exc),
            "cancel_error_type": exc.__class__.__name__,
        }
    cancel_result = {
        "cancel_attempted": True,
        "cancel_confirmed": False,
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
    final_outcome = _classify_final_order(final_order, cancel_ambiguous=cancel_ambiguous)
    return _lifecycle_result(
        submit_result=submit_result,
        cancel_result={
            **cancel_result,
            "cancel_confirmed": final_outcome
            in {
                OUTCOME_SUBMITTED_CANCELLED,
                OUTCOME_SUBMITTED_PARTIAL_CANCELLED,
                OUTCOME_CANCEL_AMBIGUOUS_RECONCILED,
            },
        },
        final_order=final_order,
        outcome=final_outcome,
        blocker="none"
        if final_outcome != OUTCOME_UNRESOLVED
        else (
            "cancel_ambiguous_unresolved"
            if cancel_ambiguous
            else "order_not_terminal_after_cancel_reconciliation"
        ),
        next_action=(
            "review_terminal_crypto_drill_artifacts_before_any_future_drill"
            if final_outcome != OUTCOME_UNRESOLVED
            else "operator_reconcile_unresolved_crypto_order_before_any_future_drill"
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


def _finalize_packet(
    packet: Mapping[str, Any],
    *,
    outcome_classification: str,
    blocker: str,
    next_operator_action: str,
    paper_submit_performed: bool = False,
    broker_mutation_performed: bool = False,
    paper_cancel_performed: bool = False,
    write_artifacts: bool,
) -> dict[str, Any]:
    submit_result = _mapping(packet.get("submit_result"))
    cancel_result = _mapping(packet.get("cancel_result"))
    order_design = _mapping(packet.get("order_design"))
    supervisor = _mapping(packet.get("supervisor_observation"))
    account = _mapping(packet.get("account_observation"))
    final_order = _mapping(packet.get("final_order"))
    finalized = {
        **packet,
        "outcome_classification": outcome_classification,
        "blocker": blocker or "none",
        "next_operator_action": next_operator_action,
        "paper_submit_performed": paper_submit_performed,
        "paper_cancel_performed": paper_cancel_performed,
        "broker_mutation_performed": broker_mutation_performed,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "broker_read_performed": supervisor.get("broker_read_performed") is True,
        "broker_state_mode": _clean_text(supervisor.get("broker_state_mode")),
        "crypto_trading_supported": supervisor.get("crypto_trading_supported") is True,
        "account_status": _clean_text(account.get("status")),
        "account_blocked": _bool(account.get("account_blocked")),
        "trading_blocked": _bool(account.get("trading_blocked")),
        "expected_account_matched": packet.get("expected_account_matched") is True,
        "selected_symbol": _clean_text(
            supervisor.get("selected_symbol") or packet.get("selected_symbol")
        ),
        "selected_symbol_tradable": supervisor.get("selected_symbol_tradable"),
        "selected_symbol_fractionable": supervisor.get("selected_symbol_fractionable"),
        "data_freshness_status": _clean_text(supervisor.get("data_freshness_status")),
        "action_decision": _clean_text(supervisor.get("action_decision")),
        "no_submit_mode": supervisor.get("no_submit_mode") is True,
        "normal_visibility_paper_submit_performed": (
            supervisor.get("paper_submit_performed") is True
        ),
        "normal_visibility_broker_mutation_performed": (
            supervisor.get("broker_mutation_performed") is True
        ),
        "normal_visibility_live_mutation_performed": (
            supervisor.get("live_mutation_performed") is True
        ),
        "min_notional": _clean_text(
            order_design.get("min_notional") or supervisor.get("min_notional")
        ),
        "min_order_size": _clean_text(
            order_design.get("min_order_size") or supervisor.get("min_order_size")
        ),
        "min_trade_increment": _clean_text(
            order_design.get("min_trade_increment")
            or supervisor.get("min_trade_increment")
        ),
        "limit_price": _clean_text(order_design.get("limit_price")),
        "quantity": _clean_text(order_design.get("quantity")),
        "target_notional": _clean_text(order_design.get("target_notional")),
        "estimated_notional": _clean_text(order_design.get("estimated_notional")),
        "submit_attempted": _bool(submit_result.get("submit_attempted")),
        "submit_status": _clean_text(submit_result.get("submit_status")),
        "submit_call_count": int(
            _decimal_or_none(submit_result.get("submit_call_count")) or Decimal("0")
        ),
        "cancel_attempted": _bool(cancel_result.get("cancel_attempted")),
        "cancel_confirmed": _bool(cancel_result.get("cancel_confirmed")),
        "cancel_ambiguous": _bool(cancel_result.get("cancel_ambiguous")),
        "final_broker_order_status": _clean_text(
            packet.get("final_broker_order_status") or _order_status(final_order)
        ),
        "fill_status": _clean_text(packet.get("fill_status") or _fill_status(final_order)),
    }
    if write_artifacts:
        finalized["artifact_paths"] = _write_artifacts(
            Path(finalized["output_root"]),
            finalized,
        )
    return _json_safe(finalized)


def _write_artifacts(root: Path, packet: Mapping[str, Any]) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    latest_status = root / "latest_status.json"
    drill_receipt = root / "drill_receipt.jsonl"
    operating_brief = root / "operating_brief.md"
    manifest = root / "manifest.json"
    paths = {
        "latest_status": str(latest_status),
        "drill_receipt": str(drill_receipt),
        "operating_brief": str(operating_brief),
        "manifest": str(manifest),
    }
    packet_with_paths = {**packet, "artifact_paths": paths}
    latest_status.write_text(
        json.dumps(_json_safe(packet_with_paths), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    drill_receipt.write_text(
        json.dumps(_drill_receipt(packet_with_paths), sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    operating_brief.write_text(
        _render_operating_brief(packet_with_paths) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest_payload = {
        "schema_version": CRYPTO_PAPER_MUTATION_DRILL_SCHEMA_VERSION,
        "artifact_root": str(root),
        "runtime_artifacts_under_runs": str(root).replace("\\", "/").startswith("runs/"),
        "credential_values_redacted": True,
        "artifacts": {
            "latest_status": _artifact_entry(latest_status),
            "drill_receipt": _artifact_entry(drill_receipt),
            "operating_brief": _artifact_entry(operating_brief),
        },
    }
    manifest.write_text(
        json.dumps(manifest_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return paths


def _drill_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "schema_version",
        "operator_command",
        "run_timestamp",
        "outcome_classification",
        "blocker",
        "account_status",
        "account_blocked",
        "trading_blocked",
        "expected_account_matched",
        "selected_symbol",
        "side",
        "order_type",
        "time_in_force",
        "limit_price",
        "quantity",
        "target_notional",
        "estimated_notional",
        "max_drill_notional",
        "min_notional",
        "client_order_id",
        "broker_read_performed",
        "broker_state_mode",
        "data_freshness_status",
        "submit_attempted",
        "submit_status",
        "cancel_attempted",
        "cancel_confirmed",
        "final_broker_order_status",
        "fill_status",
        "paper_submit_authorized",
        "paper_submit_performed",
        "paper_cancel_performed",
        "broker_mutation_performed",
        "live_mutation_performed",
        "next_operator_action",
        "safety_labels",
    )
    return {field: _json_safe(packet.get(field)) for field in fields}


def _render_operating_brief(packet: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Crypto Paper Mutation Drill Brief",
            "",
            f"- Outcome: `{packet.get('outcome_classification', '')}`",
            f"- Blocker: `{packet.get('blocker', '')}`",
            f"- Symbol: `{packet.get('selected_symbol', '')}`",
            f"- Side/type: `{packet.get('side', '')}` / `{packet.get('order_type', '')}`",
            f"- Limit price: `{packet.get('limit_price', '')}`",
            f"- Quantity: `{packet.get('quantity', '')}`",
            f"- Target/estimated notional: `{packet.get('target_notional', '')}` / `{packet.get('estimated_notional', '')}`",
            f"- Cap/min notional: `{packet.get('max_drill_notional', '')}` / `{packet.get('min_notional', '')}`",
            f"- Client order id: `{packet.get('client_order_id', '')}`",
            f"- Broker read performed: `{packet.get('broker_read_performed')}`",
            f"- Submit/cancel attempted: `{packet.get('submit_attempted')}` / `{packet.get('cancel_attempted')}`",
            f"- Final order status: `{packet.get('final_broker_order_status', '')}`",
            f"- Paper submit performed: `{packet.get('paper_submit_performed')}`",
            f"- Broker mutation performed: `{packet.get('broker_mutation_performed')}`",
            f"- Live mutation performed: `{packet.get('live_mutation_performed')}`",
            f"- Next operator action: `{packet.get('next_operator_action', '')}`",
        ]
    )


def _lookup_by_client_order_id(
    client: Any,
    *,
    client_order_id: str,
    symbol: str,
) -> dict[str, Any]:
    raw_client = _raw_trading_client(client)
    for method_name in ("get_order_by_client_id", "get_order_by_client_order_id"):
        method = getattr(raw_client, method_name, None)
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
    raw_client = _raw_trading_client(client)
    for method_name in ("cancel_order_by_id", "cancel_order"):
        method = getattr(raw_client, method_name, None)
        if callable(method):
            return method(order_id)
    raise RuntimeError("paper client does not expose same-order cancellation")


def _raw_trading_client(client: Any) -> Any:
    raw = getattr(client, "raw_trading_client", None)
    return raw if raw is not None else client


def _classify_final_order(order: Mapping[str, Any], *, cancel_ambiguous: bool) -> str:
    status = _order_status(order)
    filled_qty = _filled_quantity(order)
    if status == "rejected":
        return OUTCOME_SUBMITTED_REJECTED
    if status == "filled":
        return OUTCOME_SUBMITTED_FILLED
    if status in _CANCELLED_STATUSES and filled_qty > Decimal("0"):
        return OUTCOME_SUBMITTED_PARTIAL_CANCELLED
    if status in _CANCELLED_STATUSES and cancel_ambiguous:
        return OUTCOME_CANCEL_AMBIGUOUS_RECONCILED
    if status in _CANCELLED_STATUSES:
        return OUTCOME_SUBMITTED_CANCELLED
    return OUTCOME_UNRESOLVED


def _submit_accepted(order: Mapping[str, Any]) -> bool:
    status = _order_status(order)
    return bool(order) and status not in {"", "rejected"}


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
        "account_id_present": bool(_clean_text(_first_present(data, "account_id", "id"))),
        "account_number_present": bool(_clean_text(data.get("account_number"))),
        "status": _clean_text(data.get("status")),
        "currency": _clean_text(data.get("currency")),
        "trading_blocked": _bool(data.get("trading_blocked")),
        "account_blocked": _bool(data.get("account_blocked")),
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


def _position_summary(position: object) -> dict[str, Any]:
    data = _generic_payload(position)
    return {
        "symbol": _normalize_symbol_text(_first_present(data, "symbol")),
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
        "asset_class": _clean_text(data.get("asset_class")).lower(),
        "order_type": _clean_text(_first_present(data, "type", "order_type")).lower(),
        "time_in_force": _clean_text(data.get("time_in_force")).lower(),
        "status": _normalize_status(data.get("status")),
        "qty": _decimal_text(_decimal_or_none(_first_present(data, "qty", "quantity"))),
        "notional": _decimal_text(_decimal_or_none(data.get("notional"))),
        "limit_price": _decimal_text(_decimal_or_none(data.get("limit_price"))),
        "filled_qty": _decimal_text(
            _decimal_or_none(_first_present(data, "filled_qty", "filled_quantity"))
        ),
        "filled_avg_price": _decimal_text(
            _decimal_or_none(
                _first_present(data, "filled_avg_price", "avg_fill_price")
            )
        ),
        "submitted_at": _time_text(_first_present(data, "submitted_at", "created_at")),
        "filled_at": _time_text(data.get("filled_at")),
        "canceled_at": _time_text(_first_present(data, "canceled_at", "cancelled_at")),
        "reject_reason": _clean_text(_first_present(data, "reject_reason", "reason")),
    }


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
    return {
        field: _json_safe(data[field])
        for field in _OBJECT_PAYLOAD_FIELDS
        if field in data and data[field] is not None
    }


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


def _bar_from_row(row: Mapping[str, object]) -> Bar:
    symbol = normalize_crypto_symbol(_required_text(row.get("symbol"), "symbol"))
    close = _positive_decimal(_required_text(row.get("close"), "close"), "close")
    open_price = _decimal_or_none(row.get("open")) or close
    high = _decimal_or_none(row.get("high")) or max(open_price, close)
    low = _decimal_or_none(row.get("low")) or min(open_price, close)
    volume = _decimal_or_none(row.get("volume")) or Decimal("0")
    return Bar(
        symbol=symbol,
        timestamp=_utc_datetime(_required_text(row.get("timestamp"), "timestamp"), "timestamp"),
        open=open_price,
        high=max(high, open_price, close),
        low=min(low, open_price, close),
        close=close,
        volume=volume,
    )


def _round_up_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    if increment <= Decimal("0"):
        raise ValidationError("min_trade_increment must be positive.")
    units = (value / increment).to_integral_value(rounding=ROUND_CEILING)
    return units * increment


def _notional_estimate(order: Mapping[str, Any]) -> str:
    qty = _decimal_or_none(order.get("filled_qty")) or _decimal_or_none(order.get("qty"))
    avg = _decimal_or_none(order.get("filled_avg_price")) or _decimal_or_none(
        order.get("limit_price")
    )
    if qty is None or avg is None:
        return ""
    return str((qty * avg).quantize(Decimal("0.00000001")))


def _filled_quantity(order: Mapping[str, Any]) -> Decimal:
    return _decimal_or_none(order.get("filled_qty")) or Decimal("0")


def _fill_status(order: Mapping[str, Any]) -> str:
    status = _order_status(order)
    filled_qty = _filled_quantity(order)
    if status == "filled":
        return "filled"
    if filled_qty > Decimal("0"):
        return "partial_fill"
    return "unfilled"


def _order_status(order: Mapping[str, Any]) -> str:
    return _normalize_status(order.get("status"))


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


def _order_symbol(order: Mapping[str, Any]) -> str:
    return _normalize_symbol_text(order.get("symbol"))


def _position_symbol(position: Mapping[str, Any]) -> str:
    return _normalize_symbol_text(position.get("symbol"))


def _is_crypto_order(order: Mapping[str, Any], crypto_symbols: set[str]) -> bool:
    return (
        _normalized_enum_text(order.get("asset_class")) == "crypto"
        or _order_symbol(order) in crypto_symbols
    )


def _crypto_symbols(record: Mapping[str, Any]) -> set[str]:
    values = set(_KNOWN_CRYPTO_SYMBOLS)
    eligible = record.get("eligible_crypto_symbols")
    if isinstance(eligible, (list, tuple)):
        values.update(_normalize_symbol_text(value) for value in eligible)
    selected = _clean_text(record.get("selected_symbol"))
    if selected:
        values.add(_normalize_symbol_text(selected))
    return {value for value in values if value}


def _normalize_symbol_text(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    try:
        return normalize_crypto_symbol(text)
    except ValidationError:
        return text.upper()


def _field(value: object, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _first_present(data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return None


def _public_broker_env(env: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name in _PUBLIC_ENV_NAMES
        if (value := env.get(name, "").strip())
    }


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


def _artifact_entry(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_or_none(value)
    if decimal_value is None:
        raise ValidationError(f"{field_name} must be a decimal.")
    if decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
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
    return "" if value is None else str(value)


def _required_text(value: object, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


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


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crypto-paper-mutation-drill",
        description="Run the explicit v4.12C bounded BTCUSD Alpaca paper drill.",
    )
    parser.add_argument(
        "--crypto-paper-mutation-authorized",
        action="store_true",
        help="Explicit operator authorization for the one bounded paper drill.",
    )
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_OUTPUT_ROOT),
        help="Ignored runtime artifact root under runs/.",
    )
    parser.add_argument(
        "--bars-csv",
        default=str(CRYPTO_PAPER_SUPERVISOR_DEFAULT_BARS_CSV),
        help="Canonical BTCUSD crypto bars CSV.",
    )
    parser.add_argument("--timestamp", default="", help="Optional ISO timestamp.")
    parser.add_argument(
        "--expected-paper-account-id",
        default=None,
        help="Expected paper account id/number. Defaults to environment.",
    )
    parser.add_argument(
        "--target-symbol",
        default=CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_SYMBOL,
        help="Target crypto symbol; BTCUSD is the authorized default.",
    )
    parser.add_argument(
        "--selected-symbol-override-reason",
        default="",
        help="Required if a broker-observed non-BTCUSD symbol is selected.",
    )
    parser.add_argument(
        "--max-drill-notional",
        default=str(CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_MAX_NOTIONAL),
        help="Hard USD notional cap for limit_price * quantity.",
    )
    parser.add_argument("--reconciliation-poll-attempts", type=int, default=3)
    parser.add_argument("--reconciliation-poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    packet = run_crypto_paper_mutation_drill(
        output_root=args.output_root,
        bars_csv=args.bars_csv,
        timestamp=args.timestamp or datetime.now(UTC),
        crypto_paper_mutation_authorized=args.crypto_paper_mutation_authorized,
        expected_paper_account_id=args.expected_paper_account_id,
        target_symbol=args.target_symbol,
        selected_symbol_override_reason=args.selected_symbol_override_reason,
        max_drill_notional=args.max_drill_notional,
        reconciliation_poll_attempts=args.reconciliation_poll_attempts,
        reconciliation_poll_interval_seconds=args.reconciliation_poll_interval_seconds,
    )
    if args.format == "json":
        print(json.dumps(packet, sort_keys=True, indent=2))
    else:
        print(render_crypto_paper_mutation_drill_text(packet))
    outcome = _clean_text(packet.get("outcome_classification"))
    if outcome == OUTCOME_BLOCKED_PRE_SUBMIT:
        return 2
    if outcome in {OUTCOME_AMBIGUOUS_SUBMIT, OUTCOME_UNRESOLVED}:
        return 3
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
