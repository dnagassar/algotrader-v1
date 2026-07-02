"""Bounded SPY SMA paper-autopilot operating loop.

This is an execution-layer boundary. It may observe a verified paper broker and
submit at most one bounded SPY paper action from an immutable plan. The signal
evaluator stays broker-free and network-free.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Iterable, Mapping, Sequence
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
from algotrader.orchestration.strategy_router import (
    STRATEGY_ROUTER_LABEL,
    StrategyRouteReceipt,
    StrategySignal,
    route_strategy_signals,
    strategy_signal_from_etf_sma_result,
    strategy_signal_from_spy_rsi_mean_reversion_result,
    strategy_signal_from_spy_vol_scaled_trend_result,
)
from algotrader.orchestration.strategy_adapter_registry import (
    DEFAULT_STRATEGY_ADAPTER_REGISTRY,
    StrategyAdapterRegistryInput,
    StrategyAdapterResolution,
    resolve_strategy_adapter,
    resolve_strategy_route_adapter,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)
from algotrader.signals.spy_rsi_mean_reversion import (
    SPYRsiMeanReversionSignalConfig,
    evaluate_spy_rsi_mean_reversion_signal,
)
from algotrader.signals.spy_vol_scaled_trend import (
    SPYVolScaledTrendSignalConfig,
    evaluate_spy_vol_scaled_trend_signal,
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
PAPER_MUTATION_SUPERVISOR_SCHEMA_VERSION = (
    "v3_0_paper_only_mutation_supervisor_receipt_v1"
)
PAPER_MUTATION_SUPERVISOR_COMMAND = "scripts/run_spy_paper_mutation_supervisor.ps1"

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
_EXPECTED_ACCOUNT_ENV = "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"
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
    no_submit: bool = False

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
        if type(self.no_submit) is not bool:
            raise ValidationError("no_submit must be a boolean.")
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
    no_submit_mode: bool
    mutation_would_be_required_without_no_submit: bool
    intended_mutation_action: str
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
            "no_submit_mode": self.no_submit_mode,
            "mutation_would_be_required_without_no_submit": (
                self.mutation_would_be_required_without_no_submit
            ),
            "intended_mutation_action": self.intended_mutation_action,
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
    candidate_strategy_signals: Iterable[StrategySignal] | None = None,
    strategy_adapter_registry: StrategyAdapterRegistryInput | None = None,
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
    primary_strategy_signal = strategy_signal_from_etf_sma_result(signal)
    shadow_strategy_signal = strategy_signal_from_spy_rsi_mean_reversion_result(
        evaluate_spy_rsi_mean_reversion_signal(
            bars,
            SPYRsiMeanReversionSignalConfig(
                as_of=as_of_dt,
                symbol=resolved.symbol,
            ),
        )
    )
    vol_scaled_trend_signal = evaluate_spy_vol_scaled_trend_signal(
        bars,
        SPYVolScaledTrendSignalConfig(
            as_of=as_of_dt,
            symbol=resolved.symbol,
        ),
    )
    vol_scaled_trend_strategy_signal = (
        strategy_signal_from_spy_vol_scaled_trend_result(vol_scaled_trend_signal)
    )
    adapter_registry = _stable_strategy_adapter_registry(strategy_adapter_registry)
    route_receipt = route_strategy_signals(
        _strategy_signals(
            primary_strategy_signal,
            (shadow_strategy_signal,),
            (
                vol_scaled_trend_strategy_signal,
                *_extra_strategy_signals(
                    candidate_strategy_signals,
                    field_name="candidate_strategy_signals",
                ),
            ),
        )
    )
    adapter_resolution = resolve_strategy_route_adapter(
        route_receipt,
        registry=adapter_registry,
        adapter_mode="paper_mutation",
        requested_order_notional=resolved.max_notional,
    )
    preview_adapter_resolutions = _preview_strategy_adapter_resolutions(
        route_receipt,
        registry=adapter_registry,
    )
    route_blocker = _paper_autopilot_route_blocker(
        route_receipt,
        adapter_resolution,
    )
    preflight = _preflight(process_env)
    daily_cycle = _run_daily_cycle(
        resolved,
        output_root=output_root,
        daily_lab_runner=daily_lab_runner,
    )
    if route_blocker:
        broker_state = _unobserved_broker_state(route_blocker)
    else:
        broker_state = _observe_broker_state(
            preflight=preflight,
            env=process_env,
            secret_values=secret_values,
            broker_client_factory=broker_client_factory,
        )
    safety_labels = _dedupe(
        (*_safety_labels(broker_state["broker_state_observed"] is True), STRATEGY_ROUTER_LABEL)
    )
    intent = _build_intent(
        posture=posture,
        route_receipt=route_receipt,
        adapter_resolution=adapter_resolution,
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
        daily_cycle=daily_cycle,
        client_order_id=client_order_id,
        safety_labels=safety_labels,
        broker_observation_required=route_blocker == "",
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
        vol_scaled_trend_signal=vol_scaled_trend_signal.to_dict(),
        route_receipt=route_receipt,
        adapter_resolution=adapter_resolution,
        preview_adapter_resolutions=preview_adapter_resolutions,
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
    expected_account_id_loaded = bool(env.get(_EXPECTED_ACCOUNT_ENV, "").strip())
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
        and expected_account_id_loaded
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
        "expected_account_id_loaded": expected_account_id_loaded,
        "expected_account_configured": expected_account_id_loaded,
        "paper_profile_ready": paper_profile_ready,
        "live_endpoint_or_profile_detected": bool(live_indicators),
        "live_safety_indicators": live_indicators,
        "live_safety_status": "blocked/live_safety"
        if live_indicators
        else "passed",
        "paper_submit_gate_enabled": True,
        "paper_submit_authorization_scope": "bounded_supervisor_run_only",
        "live_authorized": False,
        "live_endpoint_supported": False,
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
        return _unobserved_broker_state(_preflight_broker_blocker(preflight))

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
        "expected_account_check": _expected_account_check(
            env.get(_EXPECTED_ACCOUNT_ENV)
        ),
        "expected_account_id_loaded": True,
        "expected_account_configured": True,
        "expected_account_matched": None,
        "expected_account_match_mode": "none",
        "expected_account_blocker": "expected_account_match_not_observed",
        "_broker": broker,
    }
    try:
        raw_account = _call_broker(broker, "get_account")
        state["account"] = _account_payload(raw_account)
        state["account_observation_available"] = True
        expected_check = _expected_account_check(
            env.get(_EXPECTED_ACCOUNT_ENV),
            account=raw_account,
        )
        expected_blocker = _expected_account_blocker(expected_check)
        state.update(
            {
                "expected_account_check": expected_check,
                "expected_account_id_loaded": (
                    expected_check.get("expected_account_configured") is True
                ),
                "expected_account_configured": (
                    expected_check.get("expected_account_configured") is True
                ),
                "expected_account_matched": expected_check.get(
                    "expected_account_matched"
                ),
                "expected_account_match_mode": _text(
                    expected_check.get("expected_account_match_mode")
                ),
                "expected_account_blocker": expected_blocker,
            }
        )
        if expected_blocker != "none":
            return _blocked_after_account_state(
                blocker=expected_blocker,
                account=state["account"],
                expected_check=expected_check,
            )
        if not _account_status_active(state["account"]):
            return _blocked_after_account_state(
                blocker="account_status_not_active",
                account=state["account"],
                expected_check=expected_check,
            )
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


def _strategy_signals(
    primary_strategy_signal: StrategySignal,
    shadow_strategy_signals: Iterable[StrategySignal] | None,
    candidate_strategy_signals: Iterable[StrategySignal] | None,
) -> tuple[StrategySignal, ...]:
    if not isinstance(primary_strategy_signal, StrategySignal):
        raise ValidationError("primary_strategy_signal must be a StrategySignal.")
    return (
        primary_strategy_signal,
        *_extra_strategy_signals(
            shadow_strategy_signals,
            field_name="shadow_strategy_signals",
        ),
        *_extra_strategy_signals(
            candidate_strategy_signals,
            field_name="candidate_strategy_signals",
        ),
    )


def _extra_strategy_signals(
    values: Iterable[StrategySignal] | None,
    *,
    field_name: str,
) -> tuple[StrategySignal, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise ValidationError(
            f"{field_name} must be an iterable of StrategySignal values."
        )
    extra_signals = tuple(values)
    for index, signal in enumerate(extra_signals):
        if not isinstance(signal, StrategySignal):
            raise ValidationError(f"{field_name}[{index}] must be a StrategySignal.")
    return extra_signals


def _stable_strategy_adapter_registry(
    registry: StrategyAdapterRegistryInput | None,
) -> StrategyAdapterRegistryInput:
    if registry is None:
        return DEFAULT_STRATEGY_ADAPTER_REGISTRY
    if isinstance(registry, Mapping):
        return registry
    if isinstance(registry, (str, bytes)) or not isinstance(registry, Iterable):
        return registry
    return tuple(registry)


def _paper_autopilot_route_blocker(
    route_receipt: StrategyRouteReceipt,
    adapter_resolution: StrategyAdapterResolution,
) -> str:
    if not isinstance(route_receipt, StrategyRouteReceipt):
        raise ValidationError("route_receipt must be a StrategyRouteReceipt.")
    if not isinstance(adapter_resolution, StrategyAdapterResolution):
        raise ValidationError(
            "adapter_resolution must be a StrategyAdapterResolution."
        )
    if adapter_resolution.resolution_status != "resolved":
        return adapter_resolution.reason
    if adapter_resolution.paper_mutation_allowed is not True:
        return "strategy_adapter_not_paper_mutation"
    return ""


def _preview_strategy_adapter_resolutions(
    route_receipt: StrategyRouteReceipt,
    *,
    registry: StrategyAdapterRegistryInput,
) -> tuple[dict[str, object], ...]:
    if not isinstance(route_receipt, StrategyRouteReceipt):
        raise ValidationError("route_receipt must be a StrategyRouteReceipt.")
    resolutions = tuple(
        resolve_strategy_adapter(
            signal,
            registry=registry,
            adapter_mode="preview_only",
        ).to_dict()
        for signal in route_receipt.signals
        if signal.promotion_status == "paper_preview_candidate"
    )
    return tuple(
        {
            **resolution,
            "mutation_allowed": resolution.get("paper_mutation_allowed") is True,
        }
        for resolution in resolutions
    )


def _build_intent(
    *,
    posture: str,
    route_receipt: StrategyRouteReceipt,
    adapter_resolution: StrategyAdapterResolution,
    broker_state: Mapping[str, Any],
    max_notional: Decimal,
) -> PaperAutopilotExecutionIntent:
    route_blocker = _paper_autopilot_route_blocker(
        route_receipt,
        adapter_resolution,
    )
    if route_blocker:
        return PaperAutopilotExecutionIntent(
            symbol=_SYMBOL,
            action="blocked",
            reason=route_blocker,
        )
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
    daily_cycle: Mapping[str, Any],
    client_order_id: str,
    safety_labels: Sequence[str],
    broker_observation_required: bool = True,
) -> PaperAutopilotExecutionPlan:
    blockers = list(
        _plan_blockers(
            intent,
            broker_state,
            preflight,
            daily_cycle,
            client_order_id,
            broker_observation_required=broker_observation_required,
        )
    )
    mutation_action = intent.action if intent.action in {"buy", "sell_close"} else ""
    mutation_would_be_required_without_no_submit = bool(
        config.no_submit and mutation_action and not blockers
    )
    submit_allowed = bool(mutation_action and not blockers)
    if mutation_would_be_required_without_no_submit:
        blockers.append("mutation_would_be_required_no_submit_mode")
        submit_allowed = False
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
        "no_submit_mode": config.no_submit,
        "mutation_would_be_required_without_no_submit": (
            mutation_would_be_required_without_no_submit
        ),
        "intended_mutation_action": mutation_action,
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
        no_submit_mode=config.no_submit,
        mutation_would_be_required_without_no_submit=(
            mutation_would_be_required_without_no_submit
        ),
        intended_mutation_action=mutation_action,
        blockers=tuple(_dedupe(blockers)),
        safety_labels=tuple(safety_labels),
    )


def _plan_blockers(
    intent: PaperAutopilotExecutionIntent,
    broker_state: Mapping[str, Any],
    preflight: Mapping[str, Any],
    daily_cycle: Mapping[str, Any],
    client_order_id: str,
    *,
    broker_observation_required: bool = True,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if preflight.get("live_endpoint_or_profile_detected") is True:
        blockers.append("live_safety")
    blockers.extend(_daily_cycle_blockers(daily_cycle))
    broker_blocker = _text(broker_state.get("blocker"))
    if broker_blocker and broker_blocker != "broker_state_not_observed":
        blockers.append(broker_blocker)
    if (
        broker_observation_required
        and broker_state.get("broker_state_observed") is not True
    ):
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


def _daily_cycle_blockers(daily_cycle: Mapping[str, Any]) -> tuple[str, ...]:
    statuses = [
        _normalized_status(daily_cycle.get("daily_cycle_data_refresh_status")),
        _normalized_status(daily_cycle.get("daily_cycle_data_freshness_status")),
        _normalized_status(daily_cycle.get("daily_cycle_blocker_status")),
    ]
    if "no_new_completed_bar_noop" in statuses:
        return ("no_new_completed_bar_noop",)
    for status in statuses:
        if status in {
            "stale_data_preview_only",
            "blocked_future_dated_local_data",
            "accepted_but_stale",
        }:
            return (status,)
        if (
            status
            and status != "none"
            and (
                "stale" in status
                or "invalid" in status
                or status.startswith("blocked_future")
            )
        ):
            return ("stale_or_invalid_data",)
    return ()


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
        "submit_response_ambiguous": False,
    }
    if plan.no_submit_mode and plan.mutation_would_be_required_without_no_submit:
        result["mutation_status"] = "blocked_no_submit_mode"
        return result
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
                "submit_response_ambiguous": True,
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
    submit_response_ambiguous = action_result.get("submit_response_ambiguous") is True
    return {
        "reconciliation_status": _post_submit_reconciliation_status(
            matching=bool(matching),
            submit_response_ambiguous=submit_response_ambiguous,
        ),
        "reconciliation_required": submit_response_ambiguous or not bool(matching),
        "submit_response_ambiguous": submit_response_ambiguous,
        "post_submit_observation": {
            "recent_order_count": len(order_payloads),
            "matching_client_order_id_found": bool(matching),
            "matching_orders": matching,
        },
    }


def _post_submit_reconciliation_status(
    *,
    matching: bool,
    submit_response_ambiguous: bool,
) -> str:
    if submit_response_ambiguous and matching:
        return "ambiguous_submit_response_order_observed"
    if submit_response_ambiguous:
        return "ambiguous_submit_response_reconciliation_required"
    if matching:
        return "reconciled_submit_observed"
    return "reconciliation_required"


def _build_record(
    *,
    config: PaperAutopilotLoopConfig,
    run_id: str,
    generated_at: str,
    data_sha256: str,
    as_of_date: str,
    signal: Mapping[str, Any],
    vol_scaled_trend_signal: Mapping[str, Any],
    route_receipt: StrategyRouteReceipt,
    adapter_resolution: StrategyAdapterResolution,
    preview_adapter_resolutions: Sequence[Mapping[str, object]],
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
        "supervisor_brief": str(output_root / "supervisor_brief.md"),
        "supervisor_receipt": str(output_root / "supervisor_receipt.jsonl"),
        "broker_snapshot": str(output_root / "broker_snapshot.json"),
        "operating_history": str(
            output_root.parent / "history" / "operating_history.jsonl"
        ),
        "daily_autonomy_ledger": str(
            output_root.parent / "history" / "daily_autonomy_ledger.jsonl"
        ),
        "latest_daily_autonomy": str(
            output_root.parent / "history" / "latest_daily_autonomy.json"
        ),
        "daily_autonomy_summary": str(
            output_root.parent / "history" / "daily_autonomy_summary.md"
        ),
        "latest_rollup": str(output_root.parent / "history" / "latest_rollup.json"),
        "operating_summary": str(
            output_root.parent / "history" / "operating_summary.md"
        ),
        "daily_cycle_output_root": str(output_root / "daily_cycle"),
    }
    if action_result.get("submit_attempted") is True:
        artifact_paths["mutation_receipt"] = str(output_root / "mutation_receipt.json")
    final_classification = _final_classification(
        blocker_status=blocker_status,
        plan=plan,
        action_result=action_result,
        reconciliation=reconciliation,
    )
    broker_response = _mapping(action_result.get("broker_response"))
    request = _mapping(action_result.get("request"))
    route_payload = route_receipt.to_dict()
    adapter_payload = adapter_resolution.to_dict()
    strategy_signal_states = _strategy_signal_states(route_receipt)
    strategy_preview_states = _strategy_preview_states(route_receipt)
    vol_scaled_preview = _vol_scaled_preview_receipt(
        signal_payload=vol_scaled_trend_signal,
        preview_states=strategy_preview_states,
        preview_adapter_resolutions=preview_adapter_resolutions,
    )
    strategy_action_disagreements = _strategy_action_disagreements(
        route_receipt,
        plan,
    )
    open_spy_orders = [
        order
        for order in _mapping_items(broker_state.get("open_orders"))
        if _text(order.get("symbol")).upper() == _SYMBOL
    ]
    broker_read_performed = _broker_read_performed(broker_state)
    operating_mode = _operating_mode(plan.no_submit_mode)
    pre_broker_daily_cycle_status = _pre_broker_daily_cycle_status(daily_cycle)
    pre_broker_daily_cycle_classification = (
        _pre_broker_daily_cycle_classification(daily_cycle)
    )
    final_supervisor_status = blocker_status
    broker_observed_supervisor_status = _broker_observed_supervisor_status(
        broker_state=broker_state,
        final_supervisor_status=final_supervisor_status,
    )
    final_operator_action = _next_operator_action(blocker_status, plan)
    return {
        "schema_version": PAPER_AUTOPILOT_SCHEMA_VERSION,
        "supervisor_schema_version": PAPER_MUTATION_SUPERVISOR_SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
        "run_timestamp": generated_at,
        "policy": config.policy,
        "command": "paper-autopilot-loop",
        "supervisor_command": PAPER_MUTATION_SUPERVISOR_COMMAND,
        "no_submit_mode": plan.no_submit_mode,
        "operating_mode": operating_mode,
        "symbol": config.symbol,
        "as_of_date": as_of_date,
        "data_latest_bar": _first_nonempty_text(
            daily_cycle.get("daily_cycle_latest_bar_date"),
            as_of_date,
        ),
        "latest_bar_date": _first_nonempty_text(
            daily_cycle.get("daily_cycle_latest_bar_date"),
            as_of_date,
        ),
        "data_freshness_status": _text(
            daily_cycle.get("daily_cycle_data_freshness_status")
        ),
        "data_refresh_status": _text(
            daily_cycle.get("daily_cycle_data_refresh_status")
        ),
        "input_data_path": str(config.bars_csv),
        "input_data_sha256": data_sha256,
        "pre_broker_daily_cycle_status": pre_broker_daily_cycle_status,
        "pre_broker_daily_cycle_classification": (
            pre_broker_daily_cycle_classification
        ),
        "sma_posture": posture,
        "signal": dict(signal),
        "vol_scaled_trend_signal": dict(vol_scaled_trend_signal),
        "vol_scaled_preview": vol_scaled_preview,
        "vol_scaled_preview_visible": vol_scaled_preview["visible"],
        "vol_scaled_preview_intended_action": _text(
            vol_scaled_preview["intended_action"]
        ),
        "vol_scaled_preview_mutation_allowed": vol_scaled_preview[
            "mutation_allowed"
        ],
        "vol_scaled_preview_submit_allowed": vol_scaled_preview["submit_allowed"],
        "vol_scaled_preview_non_mutation_status": vol_scaled_preview[
            "non_mutation_status"
        ],
        "strategy_route_receipt": route_payload,
        "strategy_route_status": route_receipt.route_status,
        "strategy_route_reason": route_receipt.reason,
        "strategy_route_action": route_receipt.route_action,
        "strategy_route_paper_mutation_allowed": (
            route_receipt.paper_mutation_allowed
        ),
        "selected_strategy_id": route_payload.get("selected_signal_id"),
        "strategy_signal_states": strategy_signal_states,
        "strategy_preview_states": strategy_preview_states,
        "strategy_preview_adapter_resolutions": [
            dict(resolution) for resolution in preview_adapter_resolutions
        ],
        "strategy_action_disagreements": strategy_action_disagreements,
        "strategy_adapter_resolution": adapter_payload,
        "strategy_adapter_resolution_status": adapter_resolution.resolution_status,
        "strategy_adapter_reason": adapter_resolution.reason,
        "strategy_adapter_id": adapter_resolution.adapter_id,
        "strategy_adapter_mode": adapter_resolution.adapter_mode,
        "strategy_adapter_paper_mutation_allowed": (
            adapter_resolution.paper_mutation_allowed
        ),
        "broker_state_mode": broker_state.get("broker_state_mode"),
        "broker_state_observed": broker_state.get("broker_state_observed") is True,
        "broker_read_performed": broker_read_performed,
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
            "no_submit_mode": plan.no_submit_mode,
            "mutation_would_be_required_without_no_submit": (
                plan.mutation_would_be_required_without_no_submit
            ),
            "intended_mutation_action": plan.intended_mutation_action,
        },
        "execution_plan_action": plan.action,
        "intended_mutation_action": plan.intended_mutation_action,
        "mutation_would_be_required_without_no_submit": (
            plan.mutation_would_be_required_without_no_submit
        ),
        "execution_plan_status": _execution_plan_status(plan),
        "preview_action_decision": _preview_action_decision(plan),
        "blocker_status": blocker_status,
        "blockers": list(plan.blockers),
        "submit_blocker": plan.blockers[0] if plan.blockers else "",
        "action_result": dict(action_result),
        "reconciliation": dict(reconciliation),
        "reconciliation_status": reconciliation.get("reconciliation_status"),
        "next_operator_action": final_operator_action,
        "final_operator_action": final_operator_action,
        "final_supervisor_status": final_supervisor_status,
        "broker_observed_supervisor_status": broker_observed_supervisor_status,
        "final_classification": final_classification,
        "final_supervisor_classification": final_classification,
        "classification": final_classification,
        "spy_position_observed": broker_state.get("spy_position_present") is True,
        "spy_position_quantity": _text(broker_state.get("spy_position_quantity")),
        "open_spy_orders_observed": len(open_spy_orders),
        "unexpected_non_spy_positions": list(
            _string_list(broker_state.get("unexpected_non_spy_positions"))
        ),
        "unexpected_non_spy_positions_observed": len(
            _string_list(broker_state.get("unexpected_non_spy_positions"))
        ),
        "expected_account_id_loaded": preflight.get("expected_account_id_loaded") is True,
        "expected_account_matched": broker_state.get("expected_account_matched"),
        "expected_account_match_mode": _text(
            broker_state.get("expected_account_match_mode")
        ),
        "paper_submit_authorized": plan.paper_submit_authorized,
        "paper_submit_performed": action_result.get("paper_submit_performed") is True,
        "broker_mutation_performed": action_result.get("broker_mutation_performed") is True,
        "mutation_performed": action_result.get("broker_mutation_performed") is True,
        "submit_response_ambiguous": (
            action_result.get("submit_response_ambiguous") is True
        ),
        "order_id": _text(broker_response.get("order_id")),
        "client_order_id": _text(broker_response.get("client_order_id")),
        "requested_notional": _text(request.get("notional")),
        "requested_quantity": _text(request.get("quantity")),
        "order_status": _text(broker_response.get("status")),
        "submitted_at": _text(broker_response.get("submitted_at")),
        "fill_status": _text(broker_response.get("fill_status")),
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "live_authorized": False,
        "live_endpoint_supported": False,
        "paper_submit_authorization_scope": "bounded_supervisor_run_only",
        "credential_values_exposed": False,
        "daily_cycle": dict(daily_cycle),
        "safety_labels": list(safety_labels),
        "artifact_paths": artifact_paths,
    }


def _broker_read_performed(broker_state: Mapping[str, Any]) -> bool:
    return any(
        broker_state.get(field) is True
        for field in (
            "broker_state_observed",
            "account_observation_available",
            "positions_observation_available",
            "orders_observation_available",
        )
    )


def _operating_mode(no_submit: bool) -> str:
    return "visibility/no_submit" if no_submit else "bounded_paper_mutation"


def _pre_broker_daily_cycle_status(daily_cycle: Mapping[str, Any]) -> str:
    blocker_status = _text(daily_cycle.get("daily_cycle_blocker_status"))
    if blocker_status and blocker_status != "none":
        return blocker_status
    for field_name in (
        "daily_cycle_data_refresh_status",
        "daily_cycle_data_freshness_status",
        "daily_cycle_preview_decision",
    ):
        status = _text(daily_cycle.get(field_name))
        if status:
            return status
    return "none" if daily_cycle.get("daily_cycle_ran") is True else "not_run"


def _pre_broker_daily_cycle_classification(daily_cycle: Mapping[str, Any]) -> str:
    status = _normalized_status(_pre_broker_daily_cycle_status(daily_cycle))
    if status in {
        "",
        "none",
        "no_refresh_required",
        "accepted_data_current",
        "fake_daily_cycle_ran",
    }:
        return "pre_broker_daily_cycle_ready"
    if "broker_state_not_observed" in status:
        return "pre_broker_broker_state_not_observed_context"
    if status == "no_new_completed_bar_noop":
        return "pre_broker_no_new_completed_bar_noop"
    if (
        "stale" in status
        or "invalid" in status
        or status.startswith("blocked_future")
    ):
        return "pre_broker_data_freshness_blocked"
    if status.startswith("blocked"):
        return "pre_broker_daily_cycle_blocked"
    return "pre_broker_daily_cycle_context"


def _broker_observed_supervisor_status(
    *,
    broker_state: Mapping[str, Any],
    final_supervisor_status: str,
) -> str:
    if broker_state.get("broker_state_observed") is True:
        return final_supervisor_status
    return "broker_state_not_observed"


def _write_operating_artifacts(output_root: Path, record: Mapping[str, Any]) -> None:
    brief_path = output_root / "operating_brief.md"
    record_path = output_root / "operating_record.jsonl"
    latest_path = output_root / "latest_status.json"
    manifest_path = output_root / "manifest.json"
    supervisor_brief_path = output_root / "supervisor_brief.md"
    supervisor_receipt_path = output_root / "supervisor_receipt.jsonl"
    broker_snapshot_path = output_root / "broker_snapshot.json"
    mutation_receipt_path = output_root / "mutation_receipt.json"
    brief_path.write_text(_render_operating_brief(record), encoding="utf-8", newline="\n")
    supervisor_brief_path.write_text(
        _render_supervisor_brief(record),
        encoding="utf-8",
        newline="\n",
    )
    with record_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(_json_safe(record), sort_keys=True, separators=(",", ":")) + "\n")
    with supervisor_receipt_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                _supervisor_receipt(record),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
    latest_path.write_text(
        json.dumps(_json_safe(record), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    broker_snapshot_path.write_text(
        json.dumps(
            _json_safe(_mapping(record.get("broker_state"))),
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if record.get("paper_submit_performed") is True:
        mutation_receipt_path.write_text(
            json.dumps(
                _json_safe(
                    {
                        "run_id": record.get("run_id"),
                        "generated_at": record.get("generated_at"),
                        "execution_plan_id": _mapping(
                            record.get("execution_plan_summary")
                        ).get("execution_plan_id"),
                        "action_result": _mapping(record.get("action_result")),
                        "reconciliation": _mapping(record.get("reconciliation")),
                        "live_mutation_performed": False,
                    }
                ),
                sort_keys=True,
                indent=2,
            )
            + "\n",
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
            "supervisor_brief": _artifact_metadata(supervisor_brief_path),
            "supervisor_receipt": _artifact_metadata(supervisor_receipt_path),
            "broker_snapshot": _artifact_metadata(broker_snapshot_path),
        },
    }
    if mutation_receipt_path.is_file():
        manifest["artifacts"]["mutation_receipt"] = _artifact_metadata(
            mutation_receipt_path
        )
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
            f"- Strategy route: `{record.get('strategy_route_status', '')}`",
            f"- Selected strategy: `{record.get('selected_strategy_id', '')}`",
            f"- Preview candidates: `{len(record.get('strategy_preview_states', []))}`",
            f"- Preview disagreements: `{len(record.get('strategy_action_disagreements', []))}`",
            f"- Strategy adapter: `{record.get('strategy_adapter_id', '')}`",
            f"- Adapter resolution: `{record.get('strategy_adapter_resolution_status', '')}`",
            f"- Broker-state mode: `{record.get('broker_state_mode', '')}`",
            f"- No-submit mode: `{record.get('no_submit_mode')}`",
            f"- Operating mode: `{record.get('operating_mode', '')}`",
            f"- Pre-broker daily-cycle status: `{record.get('pre_broker_daily_cycle_status', '')}`",
            f"- Pre-broker daily-cycle classification: `{record.get('pre_broker_daily_cycle_classification', '')}`",
            f"- Broker read performed: `{record.get('broker_read_performed')}`",
            f"- Execution plan: `{plan.get('execution_plan_id', '')}`",
            f"- Action decision: `{record.get('preview_action_decision', '')}`",
            f"- Blocker status: `{record.get('blocker_status', '')}`",
            f"- Final supervisor status: `{record.get('final_supervisor_status', '')}`",
            f"- Broker-observed supervisor status: `{record.get('broker_observed_supervisor_status', '')}`",
            f"- Reconciliation status: `{record.get('reconciliation_status', '')}`",
            f"- Paper submit authorized: `{record.get('paper_submit_authorized')}`",
            f"- Paper submit performed: `{record.get('paper_submit_performed')}`",
            f"- Broker mutation performed: `{record.get('broker_mutation_performed')}`",
            f"- Live mutation performed: `{record.get('live_mutation_performed')}`",
            f"- Final supervisor classification: `{record.get('final_supervisor_classification', '')}`",
            f"- Final operator action: `{record.get('final_operator_action', '')}`",
            "",
            "Safety labels: "
            + ", ".join(str(label) for label in record.get("safety_labels", [])),
            "",
        ]
    )


def _render_supervisor_brief(record: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# SPY Paper Mutation Supervisor Brief",
            "",
            f"- Run timestamp: `{record.get('run_timestamp', '')}`",
            f"- Latest bar: `{record.get('data_latest_bar', '')}`",
            f"- Data freshness: `{record.get('data_freshness_status', '')}`",
            f"- SMA posture: `{record.get('sma_posture', '')}`",
            f"- Strategy route: `{record.get('strategy_route_status', '')}`",
            f"- Selected strategy: `{record.get('selected_strategy_id', '')}`",
            f"- Preview candidates: `{len(record.get('strategy_preview_states', []))}`",
            f"- Preview disagreements: `{len(record.get('strategy_action_disagreements', []))}`",
            f"- Strategy adapter: `{record.get('strategy_adapter_id', '')}`",
            f"- Adapter resolution: `{record.get('strategy_adapter_resolution_status', '')}`",
            f"- Broker-state mode: `{record.get('broker_state_mode', '')}`",
            f"- No-submit mode: `{record.get('no_submit_mode')}`",
            f"- Operating mode: `{record.get('operating_mode', '')}`",
            f"- Pre-broker daily-cycle status: `{record.get('pre_broker_daily_cycle_status', '')}`",
            f"- Pre-broker daily-cycle classification: `{record.get('pre_broker_daily_cycle_classification', '')}`",
            f"- Broker read performed: `{record.get('broker_read_performed')}`",
            f"- Execution plan action: `{record.get('execution_plan_action', '')}`",
            f"- Intended mutation action: `{record.get('intended_mutation_action', '')}`",
            f"- Paper submit authorized: `{record.get('paper_submit_authorized')}`",
            f"- Mutation performed: `{record.get('mutation_performed')}`",
            f"- Submit blocker: `{record.get('submit_blocker', '')}`",
            f"- Final supervisor status: `{record.get('final_supervisor_status', '')}`",
            f"- Broker-observed supervisor status: `{record.get('broker_observed_supervisor_status', '')}`",
            f"- Final supervisor classification: `{record.get('final_supervisor_classification', '')}`",
            f"- Final operator action: `{record.get('final_operator_action', '')}`",
            "",
        ]
    )


def _supervisor_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "run_timestamp",
        "latest_bar_date",
        "data_latest_bar",
        "data_refresh_status",
        "data_freshness_status",
        "sma_posture",
        "strategy_route_status",
        "strategy_route_reason",
        "strategy_route_action",
        "strategy_route_paper_mutation_allowed",
        "selected_strategy_id",
        "vol_scaled_trend_signal",
        "vol_scaled_preview",
        "vol_scaled_preview_visible",
        "vol_scaled_preview_intended_action",
        "vol_scaled_preview_mutation_allowed",
        "vol_scaled_preview_submit_allowed",
        "vol_scaled_preview_non_mutation_status",
        "strategy_signal_states",
        "strategy_preview_states",
        "strategy_preview_adapter_resolutions",
        "strategy_action_disagreements",
        "strategy_adapter_resolution_status",
        "strategy_adapter_reason",
        "strategy_adapter_id",
        "strategy_adapter_mode",
        "strategy_adapter_paper_mutation_allowed",
        "broker_state_mode",
        "broker_state_observed",
        "broker_read_performed",
        "spy_position_observed",
        "spy_position_quantity",
        "open_spy_orders_observed",
        "unexpected_non_spy_positions",
        "unexpected_non_spy_positions_observed",
        "expected_account_matched",
        "no_submit_mode",
        "operating_mode",
        "pre_broker_daily_cycle_status",
        "pre_broker_daily_cycle_classification",
        "execution_plan_action",
        "intended_mutation_action",
        "mutation_would_be_required_without_no_submit",
        "execution_plan_status",
        "preview_action_decision",
        "paper_submit_authorized",
        "mutation_performed",
        "submit_blocker",
        "order_id",
        "client_order_id",
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_mutation_performed",
        "live_authorized",
        "final_supervisor_status",
        "broker_observed_supervisor_status",
        "final_classification",
        "final_supervisor_classification",
        "next_operator_action",
        "final_operator_action",
        "safety_labels",
    )
    return {
        "supervisor_schema_version": PAPER_MUTATION_SUPERVISOR_SCHEMA_VERSION,
        **{field: _json_safe(record.get(field)) for field in fields},
    }


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


def _final_classification(
    *,
    blocker_status: str,
    plan: PaperAutopilotExecutionPlan,
    action_result: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
) -> str:
    if action_result.get("submit_response_ambiguous") is True:
        return "ambiguous_submit_response_reconciliation_required"
    if blocker_status == "action/submitted":
        if reconciliation.get("reconciliation_required") is True:
            return "paper_submit_reconciliation_required"
        return "paper_submit_reconciled"
    if blocker_status == "none" and plan.action == "hold":
        return "no_action_required_no_mutation"
    if blocker_status == "blocked/no_new_completed_bar_noop":
        return "no_new_completed_bar_noop"
    if blocker_status == "blocked/mutation_would_be_required_no_submit_mode":
        return "mutation_would_be_required_no_submit_mode"
    if blocker_status != "none":
        return blocker_status.replace("/", "_")
    return "no_action_required_no_mutation"


def _execution_plan_status(plan: PaperAutopilotExecutionPlan) -> str:
    if plan.blockers:
        return "blocked"
    if plan.action == "hold":
        return "no_action_required"
    if plan.submit_allowed:
        return "action_required"
    return "blocked"


def _preview_action_decision(plan: PaperAutopilotExecutionPlan) -> str:
    if plan.submit_allowed:
        return f"paper_{plan.action}_allowed"
    if plan.mutation_would_be_required_without_no_submit:
        return f"paper_{plan.action}_blocked_no_submit_mode"
    if plan.action == "hold":
        return "hold/noop"
    return "blocked"


def _strategy_signal_states(
    route_receipt: StrategyRouteReceipt,
) -> list[dict[str, object]]:
    return [signal.to_dict() for signal in route_receipt.signals]


def _strategy_preview_states(
    route_receipt: StrategyRouteReceipt,
) -> list[dict[str, object]]:
    return [
        signal.to_dict()
        for signal in route_receipt.signals
        if signal.promotion_status == "paper_preview_candidate"
    ]


def _vol_scaled_preview_receipt(
    *,
    signal_payload: Mapping[str, Any],
    preview_states: Sequence[Mapping[str, object]],
    preview_adapter_resolutions: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    strategy_id = _text(signal_payload.get("strategy_id"))
    preview_state = _first_mapping_by_strategy_id(preview_states, strategy_id)
    adapter_resolution = _first_mapping_by_strategy_id(
        preview_adapter_resolutions,
        strategy_id,
    )
    visible = bool(strategy_id and preview_state)
    submit_allowed = signal_payload.get("submit_allowed") is True
    mutation_allowed = (
        signal_payload.get("paper_mutation_allowed") is True
        or adapter_resolution.get("paper_mutation_allowed") is True
        or adapter_resolution.get("mutation_allowed") is True
    )
    if visible and not submit_allowed and not mutation_allowed:
        non_mutation_status = "preview_only_non_mutating"
    else:
        non_mutation_status = "not_verified_non_mutating"
    return {
        "strategy_id": strategy_id,
        "visible": visible,
        "promotion_status": _first_nonempty_text(
            preview_state.get("promotion_status"),
            signal_payload.get("promotion_status"),
        ),
        "adapter_mode": _text(adapter_resolution.get("adapter_mode")),
        "intended_action": _first_nonempty_text(
            preview_state.get("intended_action"),
            signal_payload.get("intended_action"),
        ),
        "submit_allowed": submit_allowed,
        "paper_mutation_allowed": mutation_allowed,
        "mutation_allowed": mutation_allowed,
        "non_mutation_status": non_mutation_status,
    }


def _first_mapping_by_strategy_id(
    values: Sequence[Mapping[str, object]],
    strategy_id: str,
) -> Mapping[str, object]:
    if not strategy_id:
        return {}
    for value in values:
        if _text(value.get("strategy_id")) == strategy_id:
            return value
    return {}


def _strategy_action_disagreements(
    route_receipt: StrategyRouteReceipt,
    plan: PaperAutopilotExecutionPlan,
) -> list[dict[str, object]]:
    selected_signal = route_receipt.selected_signal
    selected_action = "" if selected_signal is None else selected_signal.intended_action
    disagreements: list[dict[str, object]] = []
    for signal in route_receipt.signals:
        if signal.promotion_status != "paper_preview_candidate":
            continue
        if signal.intended_action in {"hold", "no_action"}:
            continue
        if signal.intended_action == plan.action:
            continue
        disagreements.append(
            {
                "strategy_id": signal.strategy_id,
                "promotion_status": signal.promotion_status,
                "preview_intended_action": signal.intended_action,
                "paper_execution_plan_action": plan.action,
                "selected_strategy_id": (
                    "" if selected_signal is None else selected_signal.strategy_id
                ),
                "selected_strategy_intended_action": selected_action,
                "paper_mutation_allowed": False,
                "reason": "preview_candidate_disagrees_with_paper_execution_plan",
            }
        )
    return disagreements


def _next_operator_action(blocker_status: str, plan: PaperAutopilotExecutionPlan) -> str:
    actions = {
        "none": "continue_next_daily_cycle",
        "action/submitted": "review_latest_status_and_next_reconciliation_cycle",
        "blocked/live_safety": "stop_and_review_live_safety_before_any_paper_action",
        "blocked/broker_state_not_observed": "configure_verified_paper_profile_then_rerun",
        "blocked/expected_account_id_unavailable": "configure_expected_paper_account_id_then_rerun",
        "blocked/expected_account_mismatch": "stop_and_review_expected_paper_account_before_any_submit",
        "blocked/expected_account_match_not_observed": "stop_and_review_expected_paper_account_before_any_submit",
        "blocked/account_status_not_active": "stop_and_review_paper_account_status_before_any_submit",
        "blocked/no_new_completed_bar_noop": "wait_for_next_completed_daily_bar",
        "blocked/mutation_would_be_required_no_submit_mode": (
            "review_visibility_only_intended_action_no_submit_mode"
        ),
        "blocked/stale_data_preview_only": "refresh_or_validate_daily_bars_before_submit",
        "blocked/blocked_future_dated_local_data": "fix_daily_bar_date_before_submit",
        "blocked/accepted_but_stale": "refresh_or_validate_daily_bars_before_submit",
        "blocked/stale_or_invalid_data": "refresh_or_validate_daily_bars_before_submit",
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


def _preflight_broker_blocker(preflight: Mapping[str, Any]) -> str:
    if preflight.get("live_endpoint_or_profile_detected") is True:
        return "live_safety"
    if (
        preflight.get("APP_PROFILE_is_paper") is True
        and preflight.get("paper_credentials_ready") is True
        and preflight.get("paper_url_confirmed") is True
        and preflight.get("expected_account_id_loaded") is not True
    ):
        return "expected_account_id_unavailable"
    return "broker_state_not_observed"


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
        "expected_account_check": _expected_account_check(None),
        "expected_account_id_loaded": False,
        "expected_account_configured": False,
        "expected_account_matched": None,
        "expected_account_match_mode": "none",
        "expected_account_blocker": "expected_account_id_unavailable",
        "_broker": None,
    }


def _blocked_after_account_state(
    *,
    blocker: str,
    account: Mapping[str, Any],
    expected_check: Mapping[str, Any],
) -> dict[str, Any]:
    state = _unobserved_broker_state(blocker)
    state.update(
        {
            "broker_state_mode": "alpaca_paper_account_validation_blocked",
            "account_observation_available": True,
            "account": dict(account),
            "expected_account_check": dict(expected_check),
            "expected_account_id_loaded": (
                expected_check.get("expected_account_configured") is True
            ),
            "expected_account_configured": (
                expected_check.get("expected_account_configured") is True
            ),
            "expected_account_matched": expected_check.get(
                "expected_account_matched"
            ),
            "expected_account_match_mode": _text(
                expected_check.get("expected_account_match_mode")
            ),
            "expected_account_blocker": blocker,
            "_broker": None,
        }
    )
    return state


def _expected_account_check(
    expected_account_id: str | None,
    *,
    account: Any | None = None,
) -> dict[str, object]:
    expected = _text(expected_account_id)
    account_identity = _account_identity(account)
    observed_id = account_identity["account_id"]
    observed_number = account_identity["account_number"]
    configured = bool(expected)
    account_id_matched = (
        (observed_id == expected) if configured and observed_id else None
    )
    account_number_matched = (
        (observed_number == expected) if configured and observed_number else None
    )
    if account_id_matched is True:
        matched = True
        match_mode = "account_id"
    elif account_number_matched is True:
        matched = True
        match_mode = "account_number"
    elif account_id_matched is False or account_number_matched is False:
        matched = False
        match_mode = "none"
    else:
        matched = None
        match_mode = "none"
    return {
        "observed_account_id_present": bool(observed_id),
        "observed_account_number_present": bool(observed_number),
        "expected_account_configured": configured,
        "expected_account_id_matched": account_id_matched,
        "expected_account_number_matched": account_number_matched,
        "expected_account_matched": matched,
        "expected_account_match_mode": match_mode,
    }


def _expected_account_blocker(expected_check: Mapping[str, Any]) -> str:
    if expected_check.get("expected_account_configured") is not True:
        return "expected_account_id_unavailable"
    matched = expected_check.get("expected_account_matched")
    if matched is True:
        return "none"
    if matched is False:
        return "expected_account_mismatch"
    return "expected_account_match_not_observed"


def _account_identity(account: Any | None) -> dict[str, str]:
    data = _object_data(account) if account is not None else {}
    return {
        "account_id": _text(_first_present(data, "account_id", "id")),
        "account_number": _text(_first_present(data, "account_number")),
    }


def _account_status_active(account: Mapping[str, Any]) -> bool:
    status = _normalized_status(account.get("status"))
    return status in {"active", "account_status_active"}


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
        "submitted_at": _text(_first_present(data, "submitted_at", "created_at")),
        "filled_at": _text(_first_present(data, "filled_at")),
        "fill_status": _fill_status(data),
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


def _fill_status(data: Mapping[str, Any]) -> str:
    status = _normalized_status(_first_present(data, "status", "raw_status"))
    filled_qty = _optional_decimal(_first_present(data, "filled_quantity", "filled_qty"))
    if filled_qty is not None and filled_qty > Decimal("0"):
        return "filled_or_partially_filled"
    return status or "unknown"


def _object_data(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    names = (
        "account_tradable",
        "account_id",
        "account_number",
        "asset_class",
        "buying_power",
        "cash",
        "client_order_id",
        "created_at",
        "currency",
        "filled_at",
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
        "submitted_at",
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
        for name in (*_CREDENTIAL_ENV_NAMES, _EXPECTED_ACCOUNT_ENV)
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


def _string_list(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


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
    "PAPER_MUTATION_SUPERVISOR_COMMAND",
    "PAPER_MUTATION_SUPERVISOR_SCHEMA_VERSION",
    "PaperAutopilotExecutionIntent",
    "PaperAutopilotExecutionPlan",
    "PaperAutopilotLoopConfig",
    "paper_autopilot_client_order_id",
    "paper_autopilot_loop_exit_status",
    "run_paper_autopilot_loop",
]
