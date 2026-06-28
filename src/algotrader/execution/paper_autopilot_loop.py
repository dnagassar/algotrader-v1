"""Bounded SPY SMA paper-autopilot operating loop.

This is an execution-layer boundary. It may observe a verified paper broker and
submit at most one bounded SPY paper action from an immutable plan. The signal
evaluator stays broker-free and network-free.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaOrderRequest, AlpacaRecentOrderQuery
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.etf_sma_daily_paper_lab import (
    EtfSmaDailyPaperLabConfig,
    run_etf_sma_daily_paper_lab,
)
from algotrader.execution.paper_autopilot_history import (
    PaperAutopilotHistoryConfig,
    update_paper_autopilot_operating_history,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)


PAPER_AUTOPILOT_POLICY = "paper_autopilot_unlocked"
PAPER_AUTOPILOT_SCHEMA_VERSION = "v207_paper_autopilot_loop_v1"
PAPER_AUTOPILOT_DEFAULT_OUTPUT_ROOT = "runs/paper_autopilot/latest"
PAPER_AUTOPILOT_DEFAULT_BARS_CSV = (
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
PAPER_AUTOPILOT_MAX_NOTIONAL = Decimal("25.00")
PAPER_AUTOPILOT_SPY_BUY_CLIENT_ORDER_ID_PREFIX = "pa-v207-spy-buy-"
PAPER_AUTOPILOT_SPY_CLOSE_CLIENT_ORDER_ID_PREFIX = "pa-v207-spy-close-"

BrokerClientFactory = Callable[[AlpacaPaperConfig], Any]
DailyLabRunner = Callable[[EtfSmaDailyPaperLabConfig], Mapping[str, Any]]

_SYMBOL = "SPY"
_ASSET_CLASS = "equity"
_ORDER_TYPE = "market"
_TIME_IN_FORCE = "day"
_SAFETY_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
    PAPER_AUTOPILOT_POLICY,
)
_CREDENTIAL_ENV_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
_ENDPOINT_ENV_NAMES = (
    "ALPACA_PAPER_BASE_URL",
    "ALPACA_BASE_URL",
    "ALPACA_LIVE_BASE_URL",
    "APCA_API_BASE_URL",
)
_LIVE_ENDPOINT_FRAGMENTS = (
    "https://api.alpaca.markets",
    "http://api.alpaca.markets",
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|authorization|secret(?:[_-]?key)?|token)\b"
    r"\s*[:=]\s*[^,\s;)]*"
)
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
_SAFE_MESSAGE_LIMIT = 240


@dataclass(frozen=True, slots=True)
class PaperAutopilotLoopConfig:
    """Configuration for one SPY daily SMA paper-autopilot cycle."""

    output_root: Path | str = PAPER_AUTOPILOT_DEFAULT_OUTPUT_ROOT
    bars_csv: Path | str = PAPER_AUTOPILOT_DEFAULT_BARS_CSV
    as_of_date: str | None = None
    run_date: str | None = None
    symbol: str = _SYMBOL
    sma_fast_window: int = 50
    sma_slow_window: int = 200
    max_notional: Decimal | str = PAPER_AUTOPILOT_MAX_NOTIONAL
    policy: str = PAPER_AUTOPILOT_POLICY

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _path(self.output_root, "output_root"))
        object.__setattr__(self, "bars_csv", _path(self.bars_csv, "bars_csv"))
        symbol = str(self.symbol).strip().upper()
        if symbol != _SYMBOL:
            raise ValidationError("paper autopilot is restricted to SPY.")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(
            self,
            "sma_fast_window",
            _positive_int(self.sma_fast_window, "sma_fast_window"),
        )
        object.__setattr__(
            self,
            "sma_slow_window",
            _positive_int(self.sma_slow_window, "sma_slow_window"),
        )
        if self.sma_fast_window >= self.sma_slow_window:
            raise ValidationError("sma_fast_window must be less than sma_slow_window.")
        object.__setattr__(
            self,
            "max_notional",
            _positive_decimal(self.max_notional, "max_notional"),
        )
        if self.policy != PAPER_AUTOPILOT_POLICY:
            raise ValidationError("paper autopilot policy is not authorized.")
        if self.as_of_date is not None:
            _parse_date_text(self.as_of_date, "as_of_date")
        if self.run_date is not None:
            _parse_date_text(self.run_date, "run_date")


@dataclass(frozen=True, slots=True)
class PaperAutopilotExecutionIntent:
    """Immutable pre-plan intent derived from signal and broker observation."""

    symbol: str
    action: str
    reason: str
    side: str = ""
    notional: Decimal | None = None
    quantity: Decimal | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "reason": self.reason,
            "side": self.side,
            "notional": _decimal_text(self.notional),
            "quantity": _decimal_text(self.quantity),
        }


@dataclass(frozen=True, slots=True)
class PaperAutopilotExecutionPlan:
    """Immutable pre-broker paper-autopilot execution plan."""

    execution_plan_id: str
    symbol: str
    action: str
    side: str
    notional_cap: Decimal
    notional: Decimal | None
    quantity: Decimal | None
    client_order_id: str
    as_of_date: str
    data_path: str
    data_sha256: str
    broker_state_mode: str
    paper_submit_authorized: bool
    submit_allowed: bool
    blockers: tuple[str, ...]
    safety_labels: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "execution_plan_id": self.execution_plan_id,
            "immutable": True,
            "symbol": self.symbol,
            "action": self.action,
            "side": self.side,
            "notional_cap": str(self.notional_cap),
            "notional": _decimal_text(self.notional),
            "quantity": _decimal_text(self.quantity),
            "client_order_id": self.client_order_id,
            "as_of_date": self.as_of_date,
            "data_path": self.data_path,
            "data_sha256": self.data_sha256,
            "broker_state_mode": self.broker_state_mode,
            "paper_submit_authorized": self.paper_submit_authorized,
            "submit_allowed": self.submit_allowed,
            "blockers": list(self.blockers),
            "safety_labels": list(self.safety_labels),
        }


def run_paper_autopilot_loop(
    config: PaperAutopilotLoopConfig | None = None,
    *,
    env: Mapping[str, str] | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    daily_lab_runner: DailyLabRunner | None = None,
    timestamp: str | None = None,
    update_history: bool = True,
) -> dict[str, Any]:
    """Run one bounded paper-autopilot cycle and write operating artifacts."""

    resolved = config or PaperAutopilotLoopConfig()
    output_root = Path(resolved.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    generated_at = timestamp or _utc_now_text()
    run_id = f"paper_autopilot_{generated_at.replace(':', '').replace('-', '')}"
    process_env = _normalized_env(env)
    secret_values = _secret_values(process_env)

    bars_path = Path(resolved.bars_csv)
    bars = _load_bars(bars_path, resolved.symbol)
    data_sha256 = _file_sha256(bars_path)
    as_of_dt = _as_of_datetime(resolved, bars)
    as_of_date = as_of_dt.date().isoformat()
    signal = evaluate_etf_sma_signal(
        bars,
        EtfSmaSignalConfig(
            as_of=as_of_dt,
            symbol=resolved.symbol,
            short_window=resolved.sma_fast_window,
            long_window=resolved.sma_slow_window,
        ),
    )
    posture = _autopilot_posture(signal.posture)
    preflight = _preflight(process_env)
    daily_cycle = _run_daily_cycle(
        resolved,
        output_root=output_root,
        daily_lab_runner=daily_lab_runner,
    )
    broker_state = _observe_broker_state(
        preflight=preflight,
        env=process_env,
        secret_values=secret_values,
        broker_client_factory=broker_client_factory,
    )
    safety_labels = _safety_labels(broker_state["broker_state_observed"] is True)
    intent = _build_intent(
        posture=posture,
        broker_state=broker_state,
        max_notional=resolved.max_notional,
    )
    client_order_id = paper_autopilot_client_order_id(
        action=intent.action,
        symbol=resolved.symbol,
        as_of_date=as_of_date,
        data_sha256=data_sha256,
    )
    plan = _build_plan(
        config=resolved,
        intent=intent,
        as_of_date=as_of_date,
        data_sha256=data_sha256,
        broker_state=broker_state,
        preflight=preflight,
        client_order_id=client_order_id,
        safety_labels=safety_labels,
    )
    broker = broker_state.pop("_broker", None)
    action_result = _execute_plan(plan, broker=broker, secret_values=secret_values)
    reconciliation = _reconcile_after_action(
        plan=plan,
        action_result=action_result,
        broker=broker,
        secret_values=secret_values,
    )
    blocker_status = _final_blocker_status(plan, action_result, reconciliation)
    record = _build_record(
        config=resolved,
        run_id=run_id,
        generated_at=generated_at,
        data_sha256=data_sha256,
        as_of_date=as_of_date,
        signal=signal.to_dict(),
        posture=posture,
        preflight=preflight,
        broker_state=broker_state,
        intent=intent,
        plan=plan,
        action_result=action_result,
        reconciliation=reconciliation,
        daily_cycle=daily_cycle,
        blocker_status=blocker_status,
        safety_labels=safety_labels,
        output_root=output_root,
    )
    _write_operating_artifacts(output_root, record)
    if update_history:
        update_paper_autopilot_operating_history(
            PaperAutopilotHistoryConfig(
                latest_status_path=output_root / "latest_status.json",
                history_root=output_root.parent / "history",
            )
        )
    return record


def paper_autopilot_loop_exit_status(record: Mapping[str, Any]) -> int:
    if record.get("blocker_status") in {
        "blocked/live_safety",
        "blocked/reconciliation_required",
    }:
        return 2
    return 0


def paper_autopilot_client_order_id(
    *,
    action: str,
    symbol: str,
    as_of_date: str,
    data_sha256: str,
) -> str:
    date_part = as_of_date.replace("-", "")
    digest = data_sha256[:12]
    action = str(action).strip().lower()
    if action == "buy":
        prefix = PAPER_AUTOPILOT_SPY_BUY_CLIENT_ORDER_ID_PREFIX
    elif action == "sell_close":
        prefix = PAPER_AUTOPILOT_SPY_CLOSE_CLIENT_ORDER_ID_PREFIX
    else:
        prefix = f"pa-v207-{symbol.lower()}-noop-"
    return f"{prefix}{date_part}-{digest}"


def _run_daily_cycle(
    config: PaperAutopilotLoopConfig,
    *,
    output_root: Path,
    daily_lab_runner: DailyLabRunner | None,
) -> dict[str, Any]:
    runner = daily_lab_runner or run_etf_sma_daily_paper_lab
    daily_output_root = output_root / "daily_cycle"
    payload = runner(
        EtfSmaDailyPaperLabConfig(
            output_root=daily_output_root,
            bars_csv=config.bars_csv,
            as_of_date=config.as_of_date,
            symbol=config.symbol,
            sma_fast_window=config.sma_fast_window,
            sma_slow_window=config.sma_slow_window,
            broker_state_mode="broker_state_not_observed",
            run_date=config.run_date,
            operational_only=True,
        )
    )
    data_freshness_plan = _mapping(payload.get("data_freshness_plan"))
    data_refresh_bridge = _mapping(payload.get("data_refresh_bridge"))
    data_refresh_dry_run = _mapping(payload.get("data_refresh_dry_run"))
    return {
        "daily_cycle_ran": True,
        "daily_cycle_output_root": str(daily_output_root),
        "daily_cycle_preview_decision": _text(payload.get("preview_decision")),
        "daily_cycle_blocker_status": _text(payload.get("blocker_status")),
        "daily_cycle_next_operator_action": _text(payload.get("next_operator_action")),
        "daily_cycle_latest_bar_date": _first_nonempty_text(
            payload.get("latest_bar_date"),
            data_freshness_plan.get("latest_bar_date"),
            data_refresh_bridge.get("current_data_as_of"),
            data_refresh_bridge.get("current_accepted_data_as_of"),
        ),
        "daily_cycle_data_freshness_status": _first_nonempty_text(
            payload.get("data_freshness_status"),
            data_freshness_plan.get("data_freshness_status"),
            data_refresh_bridge.get("current_data_freshness_status"),
        ),
        "daily_cycle_data_refresh_status": _first_nonempty_text(
            payload.get("data_refresh_status"),
            data_refresh_bridge.get("data_refresh_status"),
            data_refresh_dry_run.get("refresh_state"),
            data_refresh_bridge.get("accepted_refresh_manifest_status"),
            data_refresh_bridge.get("current_data_freshness_status"),
        ),
        "daily_cycle_expected_latest_bar_date": _first_nonempty_text(
            payload.get("expected_latest_bar_date"),
            data_freshness_plan.get("expected_latest_bar_date"),
            data_refresh_bridge.get("expected_latest_bar_date"),
            data_refresh_bridge.get("accepted_refresh_expected_latest_bar_date"),
        ),
        "daily_cycle_data_freshness_plan_path": _text(
            payload.get("data_freshness_plan_path")
        ),
        "daily_cycle_data_refresh_bridge_path": _text(
            payload.get("data_refresh_bridge_path")
        ),
        "daily_cycle_data_refresh_dry_run_path": _text(
            payload.get("data_refresh_dry_run_path")
        ),
    }


def _preflight(env: Mapping[str, str]) -> dict[str, Any]:
    app_profile = env.get("APP_PROFILE", "")
    base_url = env.get("ALPACA_PAPER_BASE_URL", DEFAULT_ALPACA_PAPER_BASE_URL)
    credential_presence = {
        f"{name}_loaded": name in env and bool(str(env.get(name, "")).strip())
        for name in _CREDENTIAL_ENV_NAMES
    }
    endpoint_presence = {
        f"{name}_loaded": name in env and bool(str(env.get(name, "")).strip())
        for name in _ENDPOINT_ENV_NAMES
    }
    live_indicators = _live_indicators(env)
    credentials_ready = bool(
        env.get("ALPACA_API_KEY", "").strip()
        and env.get("ALPACA_SECRET_KEY", "").strip()
    )
    paper_url_confirmed = "paper" in base_url.strip().lower()
    paper_profile_ready = (
        app_profile == "paper"
        and credentials_ready
        and paper_url_confirmed
        and not live_indicators
    )
    return {
        "APP_PROFILE": app_profile,
        "APP_PROFILE_is_paper": app_profile == "paper",
        "APP_PROFILE_is_live": app_profile == "live",
        **credential_presence,
        **endpoint_presence,
        "credential_values_printed": False,
        "paper_credentials_ready": credentials_ready,
        "paper_url_confirmed": paper_url_confirmed,
        "paper_profile_ready": paper_profile_ready,
        "live_endpoint_or_profile_detected": bool(live_indicators),
        "live_safety_indicators": live_indicators,
        "live_safety_status": "blocked/live_safety"
        if live_indicators
        else "passed",
    }


def _observe_broker_state(
    *,
    preflight: Mapping[str, Any],
    env: Mapping[str, str],
    secret_values: Sequence[str],
    broker_client_factory: BrokerClientFactory | None,
) -> dict[str, Any]:
    if preflight.get("live_endpoint_or_profile_detected") is True:
        return _unobserved_broker_state("live_safety")
    if preflight.get("paper_profile_ready") is not True:
        return _unobserved_broker_state("broker_state_not_observed")

    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key=env.get("ALPACA_API_KEY"),
        alpaca_secret_key=env.get("ALPACA_SECRET_KEY"),
        alpaca_paper_base_url=env.get(
            "ALPACA_PAPER_BASE_URL",
            DEFAULT_ALPACA_PAPER_BASE_URL,
        ),
    )
    try:
        broker = (broker_client_factory or AlpacaSdkClient)(config)
    except Exception as exc:
        return {
            **_unobserved_broker_state("broker_unavailable"),
            "broker_error": _safe_exception_message(exc, secret_values),
        }

    state: dict[str, Any] = {
        "broker_state_mode": "alpaca_paper_observed",
        "broker_state_observed": True,
        "broker_state_not_observed": False,
        "broker_error": "",
        "account_observation_available": False,
        "positions_observation_available": False,
        "orders_observation_available": False,
        "account": {},
        "positions": [],
        "open_orders": [],
        "recent_orders": [],
        "spy_position_quantity": "",
        "spy_position_present": False,
        "unexpected_non_spy_positions": [],
        "open_spy_order_present": False,
        "_broker": broker,
    }
    try:
        state["account"] = _account_payload(_call_broker(broker, "get_account"))
        state["account_observation_available"] = True
        positions = tuple(_call_broker(broker, "get_positions") or ())
        position_payloads = [_position_payload(position) for position in positions]
        state["positions"] = position_payloads
        state["positions_observation_available"] = True
        state.update(_position_summary(position_payloads))
        open_orders = _broker_orders(
            broker,
            AlpacaRecentOrderQuery(status_filter="open", symbol_filter=_SYMBOL),
        )
        recent_orders = _broker_orders(
            broker,
            AlpacaRecentOrderQuery(status_filter="all", symbol_filter=_SYMBOL),
        )
        state["open_orders"] = [_order_payload(order) for order in open_orders]
        state["recent_orders"] = [_order_payload(order) for order in recent_orders]
        state["orders_observation_available"] = True
        state["open_spy_order_present"] = any(
            order.get("symbol") == _SYMBOL for order in state["open_orders"]
        )
    except Exception as exc:
        return {
            **_unobserved_broker_state("broker_unavailable"),
            "broker_error": _safe_exception_message(exc, secret_values),
        }
    return state


def _build_intent(
    *,
    posture: str,
    broker_state: Mapping[str, Any],
    max_notional: Decimal,
) -> PaperAutopilotExecutionIntent:
    if broker_state.get("broker_state_observed") is not True:
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="blocked",
            reason=_text(broker_state.get("blocker")) or "broker_state_not_observed",
        )
    if posture == "insufficient_history":
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="blocked",
            reason="insufficient_history",
        )
    if broker_state.get("unexpected_non_spy_positions"):
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="blocked",
            reason="unexpected_non_spy_position",
        )
    if broker_state.get("open_spy_order_present") is True:
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="blocked",
            reason="open_order_present",
        )

    spy_quantity = _optional_decimal(broker_state.get("spy_position_quantity"))
    has_position = spy_quantity is not None and spy_quantity > Decimal("0")
    if posture == "risk_on" and not has_position:
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="buy",
            side="buy",
            notional=max_notional,
            reason="risk_on_no_position_no_open_order",
        )
    if posture == "risk_on" and has_position:
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="hold",
            reason="risk_on_spy_position_present",
        )
    if posture == "risk_off" and has_position:
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="sell_close",
            side="sell",
            quantity=spy_quantity,
            reason="risk_off_spy_position_present_no_open_order",
        )
    return PaperAutopilotExecutionIntent(
        symbol=_SYMBOL,
        action="hold",
        reason="risk_off_no_position",
    )


def _build_plan(
    *,
    config: PaperAutopilotLoopConfig,
    intent: PaperAutopilotExecutionIntent,
    as_of_date: str,
    data_sha256: str,
    broker_state: Mapping[str, Any],
    preflight: Mapping[str, Any],
    client_order_id: str,
    safety_labels: Sequence[str],
) -> PaperAutopilotExecutionPlan:
    blockers = list(_plan_blockers(intent, broker_state, preflight, client_order_id))
    submit_allowed = intent.action in {"buy", "sell_close"} and not blockers
    paper_authorized = (
        submit_allowed
        and config.policy == PAPER_AUTOPILOT_POLICY
        and preflight.get("paper_profile_ready") is True
        and preflight.get("live_endpoint_or_profile_detected") is not True
    )
    if submit_allowed and not paper_authorized:
        blockers.append("paper_submit_not_authorized")
        submit_allowed = False
    seed = {
        "symbol": config.symbol,
        "action": intent.action,
        "side": intent.side,
        "notional_cap": str(config.max_notional),
        "notional": _decimal_text(intent.notional),
        "quantity": _decimal_text(intent.quantity),
        "client_order_id": client_order_id,
        "as_of_date": as_of_date,
        "data_sha256": data_sha256,
        "broker_state_mode": _text(broker_state.get("broker_state_mode")),
        "paper_submit_authorized": paper_authorized,
        "blockers": blockers,
        "safety_labels": list(safety_labels),
    }
    plan_id = "plan-" + hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return PaperAutopilotExecutionPlan(
        execution_plan_id=plan_id,
        symbol=config.symbol,
        action=intent.action,
        side=intent.side,
        notional_cap=config.max_notional,
        notional=intent.notional,
        quantity=intent.quantity,
        client_order_id=client_order_id,
        as_of_date=as_of_date,
        data_path=str(config.bars_csv),
        data_sha256=data_sha256,
        broker_state_mode=_text(broker_state.get("broker_state_mode")),
        paper_submit_authorized=paper_authorized,
        submit_allowed=submit_allowed and paper_authorized,
        blockers=tuple(_dedupe(blockers)),
        safety_labels=tuple(safety_labels),
    )


def _plan_blockers(
    intent: PaperAutopilotExecutionIntent,
    broker_state: Mapping[str, Any],
    preflight: Mapping[str, Any],
    client_order_id: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if preflight.get("live_endpoint_or_profile_detected") is True:
        blockers.append("live_safety")
    if broker_state.get("broker_state_observed") is not True:
        blockers.append("broker_state_not_observed")
    if intent.action == "blocked":
        blockers.append(intent.reason)
    if broker_state.get("unexpected_non_spy_positions"):
        blockers.append("unexpected_non_spy_position")
    if broker_state.get("open_spy_order_present") is True:
        blockers.append("open_order_present")
    if intent.action in {"buy", "sell_close"}:
        orders = [
            *_mapping_items(broker_state.get("open_orders")),
            *_mapping_items(broker_state.get("recent_orders")),
        ]
        if any(order.get("client_order_id") == client_order_id for order in orders):
            blockers.append("duplicate_client_order_id")
    return _dedupe(blockers)


def _execute_plan(
    plan: PaperAutopilotExecutionPlan,
    *,
    broker: Any,
    secret_values: Sequence[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "action_decision": plan.action,
        "submit_attempted": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "request": {},
        "broker_response": {},
        "broker_error": "",
        "mutation_status": "not_attempted",
    }
    if not plan.submit_allowed:
        result["mutation_status"] = "blocked_before_submit" if plan.blockers else "noop"
        return result
    request = AlpacaOrderRequest(
        client_order_id=plan.client_order_id,
        symbol=plan.symbol,
        side=plan.side,
        asset_class=_ASSET_CLASS,
        qty=plan.quantity,
        notional=plan.notional,
        order_type=_ORDER_TYPE,
        time_in_force=_TIME_IN_FORCE,
    )
    result.update(
        {
            "submit_attempted": True,
            "paper_submit_performed": True,
            "broker_mutation_performed": True,
            "request": _request_payload(request),
        }
    )
    try:
        response = broker.submit_order(request)
    except Exception as exc:
        result.update(
            {
                "broker_error": _safe_exception_message(exc, secret_values),
                "mutation_status": "ambiguous_submit_reconciliation_required",
            }
        )
        return result
    result.update(
        {
            "broker_response": _order_payload(response),
            "mutation_status": "submit_response_observed",
        }
    )
    return result


def _reconcile_after_action(
    *,
    plan: PaperAutopilotExecutionPlan,
    action_result: Mapping[str, Any],
    broker: Any,
    secret_values: Sequence[str],
) -> dict[str, Any]:
    if action_result.get("broker_mutation_performed") is not True:
        return {
            "reconciliation_status": "not_required_no_broker_mutation",
            "reconciliation_required": False,
            "post_submit_observation": {},
        }
    if action_result.get("broker_error"):
        return {
            "reconciliation_status": "reconciliation_required",
            "reconciliation_required": True,
            "post_submit_observation": {},
        }
    try:
        orders = _broker_orders(
            broker,
            AlpacaRecentOrderQuery(status_filter="all", symbol_filter=plan.symbol),
        )
    except Exception as exc:
        return {
            "reconciliation_status": "reconciliation_required",
            "reconciliation_required": True,
            "post_submit_error": _safe_exception_message(exc, secret_values),
            "post_submit_observation": {},
        }
    order_payloads = [_order_payload(order) for order in orders]
    matching = [
        order for order in order_payloads if order.get("client_order_id") == plan.client_order_id
    ]
    return {
        "reconciliation_status": "reconciled_submit_observed"
        if matching
        else "reconciliation_required",
        "reconciliation_required": not bool(matching),
        "post_submit_observation": {
            "recent_order_count": len(order_payloads),
            "matching_client_order_id_found": bool(matching),
            "matching_orders": matching,
        },
    }


def _build_record(
    *,
    config: PaperAutopilotLoopConfig,
    run_id: str,
    generated_at: str,
    data_sha256: str,
    as_of_date: str,
    signal: Mapping[str, Any],
    posture: str,
    preflight: Mapping[str, Any],
    broker_state: Mapping[str, Any],
    intent: PaperAutopilotExecutionIntent,
    plan: PaperAutopilotExecutionPlan,
    action_result: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    daily_cycle: Mapping[str, Any],
    blocker_status: str,
    safety_labels: Sequence[str],
    output_root: Path,
) -> dict[str, Any]:
    artifact_paths = {
        "operating_brief": str(output_root / "operating_brief.md"),
        "operating_record": str(output_root / "operating_record.jsonl"),
        "manifest": str(output_root / "manifest.json"),
        "latest_status": str(output_root / "latest_status.json"),
        "operating_history": str(
            output_root.parent / "history" / "operating_history.jsonl"
        ),
        "latest_rollup": str(output_root.parent / "history" / "latest_rollup.json"),
        "operating_summary": str(
            output_root.parent / "history" / "operating_summary.md"
        ),
        "daily_cycle_output_root": str(output_root / "daily_cycle"),
    }
    return {
        "schema_version": PAPER_AUTOPILOT_SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
        "policy": config.policy,
        "command": "paper-autopilot-loop",
        "symbol": config.symbol,
        "as_of_date": as_of_date,
        "input_data_path": str(config.bars_csv),
        "input_data_sha256": data_sha256,
        "sma_posture": posture,
        "signal": dict(signal),
        "broker_state_mode": broker_state.get("broker_state_mode"),
        "broker_state_observed": broker_state.get("broker_state_observed") is True,
        "broker_state": dict(broker_state),
        "preflight": dict(preflight),
        "execution_intent": intent.to_dict(),
        "execution_plan": plan.to_dict(),
        "execution_plan_summary": {
            "execution_plan_id": plan.execution_plan_id,
            "action": plan.action,
            "side": plan.side,
            "client_order_id": plan.client_order_id,
            "paper_submit_authorized": plan.paper_submit_authorized,
            "submit_allowed": plan.submit_allowed,
        },
        "preview_action_decision": _preview_action_decision(plan),
        "blocker_status": blocker_status,
        "blockers": list(plan.blockers),
        "action_result": dict(action_result),
        "reconciliation": dict(reconciliation),
        "reconciliation_status": reconciliation.get("reconciliation_status"),
        "next_operator_action": _next_operator_action(blocker_status, plan),
        "paper_submit_authorized": plan.paper_submit_authorized,
        "paper_submit_performed": action_result.get("paper_submit_performed") is True,
        "broker_mutation_performed": action_result.get("broker_mutation_performed") is True,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "credential_values_exposed": False,
        "daily_cycle": dict(daily_cycle),
        "safety_labels": list(safety_labels),
        "artifact_paths": artifact_paths,
    }


def _write_operating_artifacts(output_root: Path, record: Mapping[str, Any]) -> None:
    brief_path = output_root / "operating_brief.md"
    record_path = output_root / "operating_record.jsonl"
    latest_path = output_root / "latest_status.json"
    manifest_path = output_root / "manifest.json"
    brief_path.write_text(_render_operating_brief(record), encoding="utf-8", newline="\n")
    with record_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n")
    latest_path.write_text(
        json.dumps(_json_safe(record), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "manifest_version": "v207_paper_autopilot_manifest_v1",
        "run_id": record.get("run_id"),
        "generated_at": record.get("generated_at"),
        "blocker_status": record.get("blocker_status"),
        "paper_submit_performed": record.get("paper_submit_performed"),
        "broker_mutation_performed": record.get("broker_mutation_performed"),
        "live_mutation_performed": False,
        "artifacts": {
            "operating_brief": _artifact_metadata(brief_path),
            "operating_record": _artifact_metadata(record_path),
            "latest_status": _artifact_metadata(latest_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _render_operating_brief(record: Mapping[str, Any]) -> str:
    plan = _mapping(record.get("execution_plan_summary"))
    return "\n".join(
        [
            "# Paper Autopilot Operating Brief",
            "",
            f"- Run id: `{record.get('run_id', '')}`",
            f"- As-of date: `{record.get('as_of_date', '')}`",
            f"- Symbol: `{record.get('symbol', '')}`",
            f"- SMA posture: `{record.get('sma_posture', '')}`",
            f"- Broker-state mode: `{record.get('broker_state_mode', '')}`",
            f"- Execution plan: `{plan.get('execution_plan_id', '')}`",
            f"- Action decision: `{record.get('preview_action_decision', '')}`",
            f"- Blocker status: `{record.get('blocker_status', '')}`",
            f"- Reconciliation status: `{record.get('reconciliation_status', '')}`",
            f"- Paper submit authorized: `{record.get('paper_submit_authorized')}`",
            f"- Paper submit performed: `{record.get('paper_submit_performed')}`",
            f"- Broker mutation performed: `{record.get('broker_mutation_performed')}`",
            f"- Live mutation performed: `{record.get('live_mutation_performed')}`",
            f"- Next operator action: `{record.get('next_operator_action', '')}`",
            "",
            "Safety labels: "
            + ", ".join(str(label) for label in record.get("safety_labels", [])),
            "",
        ]
    )


def _final_blocker_status(
    plan: PaperAutopilotExecutionPlan,
    action_result: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
) -> str:
    if reconciliation.get("reconciliation_required") is True:
        return "blocked/reconciliation_required"
    if plan.blockers:
        first = plan.blockers[0]
        if first == "live_safety":
            return "blocked/live_safety"
        if first == "broker_state_not_observed":
            return "blocked/broker_state_not_observed"
        return f"blocked/{first}"
    if action_result.get("paper_submit_performed") is True:
        return "action/submitted"
    return "none"


def _preview_action_decision(plan: PaperAutopilotExecutionPlan) -> str:
    if plan.submit_allowed:
        return f"paper_{plan.action}_allowed"
    if plan.action == "hold":
        return "hold/noop"
    return "blocked"


def _next_operator_action(blocker_status: str, plan: PaperAutopilotExecutionPlan) -> str:
    actions = {
        "none": "continue_next_daily_cycle",
        "action/submitted": "review_latest_status_and_next_reconciliation_cycle",
        "blocked/live_safety": "stop_and_review_live_safety_before_any_paper_action",
        "blocked/broker_state_not_observed": "configure_verified_paper_profile_then_rerun",
        "blocked/open_order_present": "reconcile_existing_spy_open_order_before_submit",
        "blocked/unexpected_non_spy_position": "operator_review_non_spy_position",
        "blocked/duplicate_client_order_id": "review_duplicate_client_order_id_before_rerun",
        "blocked/insufficient_history": "wait_for_200_usable_asof_bars",
        "blocked/reconciliation_required": "stop_for_manual_reconciliation_review",
    }
    return actions.get(blocker_status, f"review_blocker_before_{plan.action}")


def _load_bars(path: Path, symbol: str) -> list[Bar]:
    if not path.is_file():
        raise ValidationError(f"Bars CSV not found: {path}")
    bars: list[Bar] = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            bars.append(_parse_bar_row(row, symbol))
    if not bars:
        raise ValidationError("Bars CSV contains no usable rows.")
    return bars


def _parse_bar_row(row: Mapping[str, object], symbol: str) -> Bar:
    close_raw = _required_row_value(row, "close")
    raw_close = _positive_decimal(close_raw, "close")
    adjusted_close = _row_value(row, "adjusted_close")
    close = (
        _positive_decimal(adjusted_close, "adjusted_close")
        if adjusted_close not in (None, "")
        else raw_close
    )
    factor = close / raw_close if raw_close != Decimal("0") else Decimal("1")
    open_price = _optional_decimal(_row_value(row, "open")) or raw_close
    high = _optional_decimal(_row_value(row, "high")) or max(open_price, raw_close)
    low = _optional_decimal(_row_value(row, "low")) or min(open_price, raw_close)
    volume = _optional_decimal(_row_value(row, "volume")) or Decimal("0")
    open_price *= factor
    high *= factor
    low *= factor
    row_symbol = _row_value(row, "symbol")
    return Bar(
        symbol=symbol if row_symbol in (None, "") else str(row_symbol).strip().upper(),
        timestamp=_row_datetime(row),
        open=open_price,
        high=max(high, open_price, close),
        low=min(low, open_price, close),
        close=close,
        volume=volume,
    )


def _row_datetime(row: Mapping[str, object]) -> datetime:
    for field_name in ("date", "timestamp", "datetime"):
        value = _row_value(row, field_name)
        if value not in (None, ""):
            text = str(value).strip()
            break
    else:
        raise ValidationError("date/timestamp is required in CSV.")
    try:
        if "T" in text:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            parsed = datetime.combine(
                datetime.fromisoformat(text).date(),
                datetime.min.time(),
                tzinfo=UTC,
            )
    except ValueError as exc:
        raise ValidationError(f"Invalid date format: {text}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_of_datetime(config: PaperAutopilotLoopConfig, bars: Sequence[Bar]) -> datetime:
    if config.as_of_date:
        return datetime.combine(
            _parse_date_text(config.as_of_date, "as_of_date"),
            datetime.min.time(),
            tzinfo=UTC,
        )
    return max(bar.timestamp for bar in bars)


def _autopilot_posture(signal_posture: str) -> str:
    if signal_posture == "bullish_risk_on":
        return "risk_on"
    if signal_posture == "defensive_risk_off":
        return "risk_off"
    return "insufficient_history"


def _unobserved_broker_state(blocker: str) -> dict[str, Any]:
    return {
        "broker_state_mode": "broker_state_not_observed",
        "broker_state_observed": False,
        "broker_state_not_observed": True,
        "blocker": blocker,
        "broker_error": "",
        "account_observation_available": False,
        "positions_observation_available": False,
        "orders_observation_available": False,
        "account": {},
        "positions": [],
        "open_orders": [],
        "recent_orders": [],
        "spy_position_quantity": "",
        "spy_position_present": False,
        "unexpected_non_spy_positions": [],
        "open_spy_order_present": False,
        "_broker": None,
    }


def _position_summary(positions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    spy_quantity = Decimal("0")
    unexpected: list[str] = []
    for position in positions:
        symbol = _text(position.get("symbol")).upper()
        quantity = _optional_decimal(position.get("quantity")) or Decimal("0")
        if symbol == _SYMBOL:
            spy_quantity += quantity
        elif quantity != Decimal("0") and symbol not in unexpected:
            unexpected.append(symbol)
    return {
        "spy_position_quantity": _decimal_text(spy_quantity) or "",
        "spy_position_present": spy_quantity > Decimal("0"),
        "unexpected_non_spy_positions": unexpected,
    }


def _call_broker(broker: Any, method_name: str, *args: object) -> Any:
    method = getattr(broker, method_name, None)
    if method is None or not callable(method):
        raise ValidationError(f"broker method {method_name} is unavailable.")
    return method(*args)


def _broker_orders(broker: Any, query: AlpacaRecentOrderQuery) -> tuple[Any, ...]:
    if hasattr(broker, "get_orders"):
        return tuple(broker.get_orders(query) or ())
    if hasattr(broker, "get_recent_orders"):
        return tuple(broker.get_recent_orders(query) or ())
    raise ValidationError("broker order observation method is unavailable.")


def _account_payload(account: Any) -> dict[str, object]:
    data = _object_data(account)
    return {
        "status": _text(_first_present(data, "status")),
        "tradable": _bool_or_none(_first_present(data, "tradable", "account_tradable")),
        "trading_blocked": _bool_or_none(_first_present(data, "trading_blocked")),
        "currency": _text(_first_present(data, "currency")),
        "cash": _decimal_text(_optional_decimal(_first_present(data, "cash"))),
        "buying_power": _decimal_text(
            _optional_decimal(_first_present(data, "buying_power"))
        ),
    }


def _position_payload(position: Any) -> dict[str, object]:
    data = _object_data(position)
    return {
        "symbol": _text(_first_present(data, "symbol")).upper(),
        "quantity": _decimal_text(_optional_decimal(_first_present(data, "quantity", "qty")))
        or "0",
        "market_value": _decimal_text(_optional_decimal(_first_present(data, "market_value")))
        or "",
        "side": _text(_first_present(data, "side")).lower(),
    }


def _order_payload(order: Any) -> dict[str, object]:
    data = _object_data(order)
    return {
        "order_id": _text(_first_present(data, "order_id", "id")),
        "client_order_id": _text(_first_present(data, "client_order_id")),
        "symbol": _text(_first_present(data, "symbol")).upper(),
        "side": _text(_first_present(data, "side")).lower(),
        "asset_class": _text(_first_present(data, "asset_class")).lower(),
        "order_type": _normalized_status(_first_present(data, "order_type", "type")),
        "time_in_force": _normalized_status(_first_present(data, "time_in_force")),
        "status": _normalized_status(
            _first_present(data, "normalized_status", "status", "raw_status")
        ),
        "notional": _decimal_text(_optional_decimal(_first_present(data, "notional"))) or "",
        "quantity": _decimal_text(_optional_decimal(_first_present(data, "quantity", "qty")))
        or "",
        "filled_quantity": _decimal_text(
            _optional_decimal(_first_present(data, "filled_quantity", "filled_qty"))
        )
        or "",
    }


def _request_payload(request: AlpacaOrderRequest) -> dict[str, object]:
    return {
        "client_order_id": request.client_order_id,
        "symbol": request.symbol,
        "side": request.side,
        "asset_class": request.asset_class,
        "order_type": request.order_type,
        "time_in_force": request.time_in_force,
        "notional": _decimal_text(request.notional) or "",
        "quantity": _decimal_text(request.qty) or "",
    }


def _object_data(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    names = (
        "account_tradable",
        "asset_class",
        "buying_power",
        "cash",
        "client_order_id",
        "currency",
        "filled_qty",
        "filled_quantity",
        "id",
        "market_value",
        "normalized_status",
        "notional",
        "order_id",
        "order_type",
        "qty",
        "quantity",
        "raw_status",
        "side",
        "status",
        "symbol",
        "time_in_force",
        "tradable",
        "trading_blocked",
        "type",
    )
    return {name: getattr(value, name) for name in names if hasattr(value, name)}


def _normalized_env(env: Mapping[str, str] | None) -> dict[str, str]:
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


def _live_indicators(env: Mapping[str, str]) -> list[str]:
    indicators: list[str] = []
    if env.get("APP_PROFILE") == "live":
        indicators.append("APP_PROFILE=live")
    for name in _ENDPOINT_ENV_NAMES:
        value = env.get(name, "")
        lowered = value.strip().lower()
        if any(fragment in lowered for fragment in _LIVE_ENDPOINT_FRAGMENTS):
            indicators.append(name)
    return indicators


def _secret_values(env: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(
        value
        for name in _CREDENTIAL_ENV_NAMES
        if (value := str(env.get(name, "")).strip())
    )


def _safe_exception_message(exc: Exception, secret_values: Sequence[str]) -> str:
    message = str(exc)
    for secret in sorted(set(secret_values), key=len, reverse=True):
        if secret:
            message = message.replace(secret, "<redacted>")
    message = _URL_PATTERN.sub("<redacted_url>", message)
    message = _BEARER_TOKEN_PATTERN.sub("Bearer <redacted>", message)
    message = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=<redacted>",
        message,
    )
    message = " ".join(message.split())
    return message[:_SAFE_MESSAGE_LIMIT].rstrip()


def _safety_labels(broker_observed: bool) -> tuple[str, ...]:
    return (
        *_SAFETY_LABELS,
        "broker_state_observed" if broker_observed else "broker_state_not_observed",
    )


def _artifact_metadata(path: Path) -> dict[str, object]:
    content = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row_value(row: Mapping[str, object], field_name: str) -> object:
    for key, value in row.items():
        if str(key).strip().lower() == field_name:
            return value
    return None


def _required_row_value(row: Mapping[str, object], field_name: str) -> object:
    value = _row_value(row, field_name)
    if value in (None, ""):
        raise ValidationError(f"{field_name} is required in CSV.")
    return value


def _path(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a Path or string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _parse_date_text(value: object, field_name: str) -> date:
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be YYYY-MM-DD.") from exc


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    parsed = _optional_decimal(value)
    if parsed is None or parsed <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return parsed


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _decimal_text(value: object) -> str | None:
    parsed = _optional_decimal(value)
    return None if parsed is None else str(parsed)


def _first_present(data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return ""


def _bool_or_none(value: object) -> bool | None:
    if value is True or value is False:
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    return None


def _normalized_status(value: object) -> str:
    text = str(value or "").strip().lower()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_items(value: object) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
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
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value).strip()


def _first_nonempty_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _utc_now_text() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


__all__ = [
    "PAPER_AUTOPILOT_DEFAULT_BARS_CSV",
    "PAPER_AUTOPILOT_DEFAULT_OUTPUT_ROOT",
    "PAPER_AUTOPILOT_MAX_NOTIONAL",
    "PAPER_AUTOPILOT_POLICY",
    "PAPER_AUTOPILOT_SPY_BUY_CLIENT_ORDER_ID_PREFIX",
    "PAPER_AUTOPILOT_SPY_CLOSE_CLIENT_ORDER_ID_PREFIX",
    "PaperAutopilotExecutionIntent",
    "PaperAutopilotExecutionPlan",
    "PaperAutopilotLoopConfig",
    "paper_autopilot_client_order_id",
    "paper_autopilot_loop_exit_status",
    "run_paper_autopilot_loop",
]
