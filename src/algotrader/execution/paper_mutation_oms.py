"""Bounded Alpaca paper mutation boundary for the v1.89 SPY drill.

This module is the only strategy-lab execution surface that may submit the
v1.89 certification order or request its cancellation. It does not import the
Alpaca SDK directly; the SDK wrapper remains responsible for SDK construction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_UP
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from algotrader.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    AlpacaPaperConfig,
)
from algotrader.execution.alpaca_client import (
    AlpacaOrderRequest,
    AlpacaRecentOrderQuery,
    V189_SPY_CERTIFICATION_CLIENT_ORDER_ID,
)


V189_RUN_ID = "v189_paper_mutation_certification"
V189_DEFAULT_OUTPUT_ROOT = (
    "runs/paper_lab/v189_paper_mutation_certification"
)
V189_SYMBOL = "SPY"
V189_STRATEGY_ORDER = False
V189_TOTAL_SPY_EXPOSURE_CAP = Decimal("25")
V189_CERTIFICATION_MAX_MARKET_VALUE = Decimal("1")
V189_MIN_FRACTIONAL_QTY = Decimal("0.0001")
V189_NON_MARKETABLE_LIMIT_MULTIPLIER = Decimal("1.05")
EXPECTED_PAPER_ACCOUNT_ENV = "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"
ALLOWED_LABELS = (
    "paper_lab_only",
    "paper_certification_only",
    "strategy_order=false",
    "not_live_authorized",
    "live_trading=false",
    "profit_claim=none",
    "networked_paper_only",
    "paper_submit_authorized=true",
)
LIVE_ENDPOINT_FRAGMENTS = (
    "https://api.alpaca.markets",
    "http://api.alpaca.markets",
)
TERMINAL_ORDER_STATUSES = frozenset(
    {
        "canceled",
        "cancelled",
        "expired",
        "filled",
        "rejected",
        "done_for_day",
    }
)
TERMINAL_SUCCESS_OUTCOMES = frozenset(
    {
        "submitted_cancel_confirmed",
        "submitted_then_rejected",
        "submitted_partial_fill_then_cancelled",
        "submitted_filled_before_cancel",
        "cancel_ambiguous_reconciled",
    }
)
UNRESOLVED_OUTCOMES = frozenset(
    {
        "unresolved_order_outcome",
        "ambiguous_submit_unresolved",
        "cancel_ambiguous_unresolved",
    }
)
CLASSIFICATION_ALIASES = {
    "blocked_lock_contention": ("blocked_process_lock",),
}


@dataclass(frozen=True, slots=True)
class PaperCertificationRuntime:
    """Runtime dependencies for the certification lane."""

    output_root: Path | str = V189_DEFAULT_OUTPUT_ROOT
    expected_paper_account_id: str = ""
    timeout_seconds: float = 45.0
    poll_interval_seconds: float = 2.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", Path(self.output_root))
        object.__setattr__(
            self,
            "expected_paper_account_id",
            str(self.expected_paper_account_id).strip(),
        )
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        object.__setattr__(
            self,
            "poll_interval_seconds",
            float(self.poll_interval_seconds),
        )


class PaperMutationGateway:
    """Adapter around an injected paper client and optional raw SDK client."""

    def __init__(self, client: Any, raw_client: Any | None = None) -> None:
        self._client = client
        self._raw_client = raw_client or getattr(client, "raw_trading_client", client)

    def get_account(self) -> Any:
        return self._client.get_account()

    def get_positions(self) -> Sequence[Any]:
        if hasattr(self._client, "get_positions"):
            return self._client.get_positions()
        return self._client.list_positions()

    def get_orders(self, query: AlpacaRecentOrderQuery) -> Sequence[Any]:
        if hasattr(self._client, "get_orders"):
            return self._client.get_orders(query)
        return self._client.get_recent_orders(query)

    def get_asset(self, symbol: str) -> Any:
        method = getattr(self._raw_client, "get_asset", None)
        if not callable(method):
            raise RuntimeError("paper client does not expose get_asset")
        return method(symbol)

    def submit_order(self, request: AlpacaOrderRequest) -> Any:
        return self._client.submit_order(request)

    def lookup_order_by_client_order_id(self, client_order_id: str) -> Any | None:
        for method_name in (
            "get_order_by_client_id",
            "get_order_by_client_order_id",
        ):
            method = getattr(self._raw_client, method_name, None)
            if callable(method):
                try:
                    return method(client_order_id)
                except Exception:
                    raise

        query = AlpacaRecentOrderQuery(
            status_filter="all",
            symbol_filter=V189_SYMBOL,
        )
        matches = [
            order
            for order in self.get_orders(query)
            if _text_field(order, "client_order_id") == client_order_id
        ]
        return matches[0] if matches else None

    def request_order_cancellation(self, order_id: str) -> Any:
        for method_name in ("cancel_order_by_id", "cancel_order"):
            method = getattr(self._raw_client, method_name, None)
            if callable(method):
                return method(order_id)
        raise RuntimeError("paper client does not expose order cancellation")


class _CertificationBlocked(Exception):
    """Internal control flow for a safely blocked certification plan."""


class MutationProcessLock:
    """Simple process lock backed by an exclusive file create."""

    def __init__(self, lock_path: Path) -> None:
        self.path = lock_path
        self.acquired = False
        self._fd: int | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(
                str(self.path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            self.acquired = False
            return False

        os.write(self._fd, _utc_now().isoformat().encode("utf-8"))
        self.acquired = True
        return True

    def release(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        if self.acquired:
            self.path.unlink(missing_ok=True)
        self.acquired = False


def paper_config_from_env_aliases(
    env: Mapping[str, str] | None = None,
) -> AlpacaPaperConfig:
    """Build paper config while accepting the existing secret-key alias."""

    source = dict(os.environ if env is None else env)
    if not source.get("ALPACA_API_KEY") and source.get("APCA_API_KEY_ID"):
        source["ALPACA_API_KEY"] = source["APCA_API_KEY_ID"]
    if not source.get("ALPACA_SECRET_KEY") and source.get("ALPACA_API_SECRET_KEY"):
        source["ALPACA_SECRET_KEY"] = source["ALPACA_API_SECRET_KEY"]
    if not source.get("ALPACA_SECRET_KEY") and source.get("APCA_API_SECRET_KEY"):
        source["ALPACA_SECRET_KEY"] = source["APCA_API_SECRET_KEY"]
    return AlpacaPaperConfig.from_env(source)


def certification_client_order_id() -> str:
    """Return the deterministic one-shot certification client order id."""

    return V189_SPY_CERTIFICATION_CLIENT_ORDER_ID


def evaluate_strategy_plan_mutation_lane(
    execution_plan: Mapping[str, Any],
    mutation_gateway: Any | None = None,
) -> dict[str, Any]:
    """Classify a strategy plan without mutating when the action is hold/noop."""

    action = str(execution_plan.get("execution_plan_action", "")).strip().lower()
    submit_allowed = execution_plan.get("execution_plan_submit_allowed") is True
    paper_authorized = (
        execution_plan.get("execution_plan_paper_submit_authorized") is True
    )
    immutable_plan = bool(execution_plan.get("execution_plan_id"))

    if action in {"hold/noop", "noop", "hold"} or not submit_allowed:
        return {
            "outcome_classification": "not_submitted_hold_noop",
            "strategy_order": True,
            "accepted_immutable_execution_plan": immutable_plan,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "mutation_gateway_touched": False,
        }

    return {
        "outcome_classification": "blocked_unaccepted_execution_plan",
        "strategy_order": True,
        "accepted_immutable_execution_plan": immutable_plan and paper_authorized,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "mutation_gateway_touched": mutation_gateway is not None and False,
    }


def run_paper_certification_drill(
    *,
    paper_config: AlpacaPaperConfig,
    gateway: PaperMutationGateway,
    runtime: PaperCertificationRuntime,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run the bounded v1.89 certification drill and write artifacts."""

    output_root = Path(runtime.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    lifecycle_path = output_root / "order_lifecycle.jsonl"
    restart_recovery_candidate = _has_local_submit_without_final_artifact(output_root)
    if restart_recovery_candidate:
        lifecycle_path.touch()
    else:
        lifecycle_path.write_text("", encoding="utf-8", newline="\n")

    source_env = dict(os.environ if env is None else env)
    secret_values = _credential_values(source_env, paper_config)
    lock = MutationProcessLock(output_root / ".mutation.lock")
    lock_acquired = lock.acquire()
    observed: dict[str, Any] = {}
    certification_plan: dict[str, Any] = _empty_certification_plan()
    outcome = "unresolved_order_outcome"
    blocker = ""
    paper_submit_performed = False
    broker_mutation_performed = False
    final_order: dict[str, Any] = {}
    submit_ambiguous = False
    cancel_ambiguous = False
    restart_recovery_performed = False

    preflight = _initial_preflight(
        paper_config=paper_config,
        env=source_env,
        expected_paper_account_id=runtime.expected_paper_account_id,
        lock_acquired=lock_acquired,
    )
    preflight["restart_recovery_candidate"] = restart_recovery_candidate
    _append_lifecycle(
        lifecycle_path,
        "preflight_started",
        {"client_order_id": certification_client_order_id()},
    )

    try:
        prior_unresolved = _has_unresolved_prior_mutation(output_root)
        preflight["unresolved_prior_mutation_present"] = prior_unresolved

        static_blocker = _static_preflight_blocker(preflight)
        if static_blocker:
            blocker = static_blocker
            outcome = static_blocker
            _append_lifecycle(lifecycle_path, "blocked_pre_observation", preflight)
        else:
            try:
                observed = _observe_pre_mutation_state(gateway)
                preflight.update(_observed_preflight_fields(observed, runtime))
                preflight.update(_broker_local_divergence_fields(output_root, observed))
                if preflight["broker_state_observed"]:
                    _append_lifecycle(
                        lifecycle_path,
                        "broker_state_observed",
                        _observation_lifecycle_payload(observed),
                    )
            except Exception as exc:
                observed = {}
                preflight["broker_state_observed"] = False
                preflight["broker_observation_error"] = _sanitize_text(
                    str(exc),
                    secret_values,
                )
                preflight.update(
                    {
                        "broker_local_divergence_present": False,
                        "broker_local_divergence_reason": "",
                    }
                )
                _append_lifecycle(
                    lifecycle_path,
                    "broker_state_observation_failed",
                    {"message": preflight["broker_observation_error"]},
                )
            blocker = _observed_preflight_blocker(preflight)
            restart_recovery_allowed = restart_recovery_candidate and blocker in {
                "",
                "blocked_open_order_present",
                "blocked_duplicate_client_order_id",
            }
            if blocker and not restart_recovery_allowed:
                outcome = blocker
                _append_lifecycle(
                    lifecycle_path,
                    "blocked_after_observation",
                    {"blocker": blocker},
                )
                if blocker == "blocked_duplicate_client_order_id":
                    _lookup_by_client_order_id_safely(
                        gateway,
                        lifecycle_path,
                        secret_values,
                    )
            elif restart_recovery_allowed:
                restart_recovery_performed = True
                _append_lifecycle(
                    lifecycle_path,
                    "restart_recovery_started",
                    {"preflight_blocker": blocker},
                )
                lookup = _lookup_by_client_order_id_safely(
                    gateway,
                    lifecycle_path,
                    secret_values,
                )
                if lookup is None:
                    outcome = "unresolved_order_outcome"
                    _append_lifecycle(
                        lifecycle_path,
                        "restart_recovery_unresolved",
                        {"reason": "client_order_id_not_found"},
                    )
                else:
                    recovered_order = _order_payload(lookup)
                    final_order, cancel_ambiguous, cancel_requested = (
                        _cancel_and_reconcile(
                            gateway=gateway,
                            lifecycle_path=lifecycle_path,
                            initial_order=recovered_order,
                            timeout_seconds=runtime.timeout_seconds,
                            poll_interval_seconds=runtime.poll_interval_seconds,
                            secret_values=secret_values,
                        )
                    )
                    broker_mutation_performed = cancel_requested
                    outcome = _classify_final_order(
                        final_order,
                        cancel_ambiguous=cancel_ambiguous,
                    )
            else:
                certification_plan = _build_certification_plan(observed)
                _write_json(output_root / "certification_plan.json", certification_plan)
                if not certification_plan.get("certification_plan_id"):
                    blocker = "blocked_risk_cap"
                    outcome = blocker
                    _append_lifecycle(
                        lifecycle_path,
                        "blocked_certification_plan",
                        {"blocker": blocker},
                    )
                    raise _CertificationBlocked
                request = _certification_order_request(certification_plan)
                _append_lifecycle(
                    lifecycle_path,
                    "submit_attempt",
                    _request_payload(request),
                )
                paper_submit_performed = True
                broker_mutation_performed = True

                try:
                    submit_response = gateway.submit_order(request)
                    submitted_order = _order_payload(submit_response)
                    _append_lifecycle(
                        lifecycle_path,
                        "submit_response_observed",
                        submitted_order,
                    )
                except Exception as exc:
                    submit_ambiguous = True
                    submitted_order = {}
                    _append_lifecycle(
                        lifecycle_path,
                        "submit_ambiguous_lookup_started",
                        {"message": _sanitize_text(str(exc), secret_values)},
                    )

                if submit_ambiguous:
                    lookup = _lookup_by_client_order_id_safely(
                        gateway,
                        lifecycle_path,
                        secret_values,
                    )
                    if lookup is None:
                        outcome = "unresolved_order_outcome"
                    else:
                        submitted_order = _order_payload(lookup)
                        final_order, cancel_ambiguous, cancel_requested = (
                            _cancel_and_reconcile(
                                gateway=gateway,
                                lifecycle_path=lifecycle_path,
                                initial_order=submitted_order,
                                timeout_seconds=runtime.timeout_seconds,
                                poll_interval_seconds=runtime.poll_interval_seconds,
                                secret_values=secret_values,
                            )
                        )
                        broker_mutation_performed = (
                            broker_mutation_performed or cancel_requested
                        )
                        reconciled_outcome = _classify_final_order(
                            final_order,
                            cancel_ambiguous=cancel_ambiguous,
                        )
                        outcome = (
                            "ambiguous_submit_reconciled"
                            if reconciled_outcome in TERMINAL_SUCCESS_OUTCOMES
                            else "unresolved_order_outcome"
                        )
                else:
                    retrieved_order = _lookup_by_client_order_id_safely(
                        gateway,
                        lifecycle_path,
                        secret_values,
                    )
                    if retrieved_order is None:
                        retrieved_payload = submitted_order
                    else:
                        retrieved_payload = _order_payload(retrieved_order)
                    _append_lifecycle(
                        lifecycle_path,
                        "post_submit_order_retrieved",
                        retrieved_payload,
                    )
                    final_order, cancel_ambiguous, cancel_requested = (
                        _cancel_and_reconcile(
                            gateway=gateway,
                            lifecycle_path=lifecycle_path,
                            initial_order=retrieved_payload,
                            timeout_seconds=runtime.timeout_seconds,
                            poll_interval_seconds=runtime.poll_interval_seconds,
                            secret_values=secret_values,
                        )
                    )
                    broker_mutation_performed = (
                        broker_mutation_performed or cancel_requested
                    )
                    outcome = _classify_final_order(
                        final_order,
                        cancel_ambiguous=cancel_ambiguous,
                    )
    except _CertificationBlocked:
        pass
    finally:
        lock.release()

    certification_plan_path = output_root / "certification_plan.json"
    if not certification_plan_path.exists():
        _write_json(certification_plan_path, certification_plan)

    post_observation = _observe_post_mutation_state_safely(
        gateway,
        lifecycle_path,
        secret_values,
        attempted=paper_submit_performed or broker_mutation_performed,
    )
    reconciliation = _build_reconciliation(
        outcome=outcome,
        blocker=blocker,
        preflight=preflight,
        certification_plan=certification_plan,
        final_order=final_order,
        post_observation=post_observation,
        submit_ambiguous=submit_ambiguous,
        cancel_ambiguous=cancel_ambiguous,
        restart_recovery_performed=restart_recovery_performed,
        paper_submit_performed=paper_submit_performed,
        broker_mutation_performed=broker_mutation_performed,
    )
    policy = _mutation_policy_payload()
    latest_run = _latest_run_payload(
        outcome=outcome,
        blocker=blocker,
        preflight=preflight,
        certification_plan=certification_plan,
        reconciliation=reconciliation,
        restart_recovery_performed=restart_recovery_performed,
        paper_submit_performed=paper_submit_performed,
        broker_mutation_performed=broker_mutation_performed,
    )

    _write_json(output_root / "preflight.json", preflight)
    _write_json(output_root / "mutation_policy.json", policy)
    _write_json(output_root / "reconciliation.json", reconciliation)
    _write_json(output_root / "latest_run.json", latest_run)
    (output_root / "operating_brief.md").write_text(
        _render_operating_brief(latest_run),
        encoding="utf-8",
        newline="\n",
    )
    _write_manifest(output_root)
    return latest_run


def _initial_preflight(
    *,
    paper_config: AlpacaPaperConfig,
    env: Mapping[str, str],
    expected_paper_account_id: str,
    lock_acquired: bool,
) -> dict[str, Any]:
    endpoint = paper_config.alpaca_paper_base_url.strip()
    secret_loaded = bool(
        _clean_secret(paper_config.alpaca_secret_key)
        or _clean_secret(env.get("ALPACA_API_SECRET_KEY"))
    )
    api_key_loaded = bool(_clean_secret(paper_config.alpaca_api_key))
    live_endpoint_detected = any(
        fragment == endpoint.lower().rstrip("/")
        for fragment in LIVE_ENDPOINT_FRAGMENTS
    )
    return {
        "APP_PROFILE_is_paper": paper_config.is_paper_profile,
        "paper_credentials_loaded": api_key_loaded and secret_loaded,
        "credential_values_exposed": False,
        "paper_endpoint_exact_match": endpoint == DEFAULT_ALPACA_PAPER_BASE_URL,
        "live_endpoint_detected": live_endpoint_detected,
        "expected_paper_account_match": False,
        "expected_paper_account_attested": bool(expected_paper_account_id),
        "paper_mutation_policy_authorized": True,
        "mutation_process_lock_acquired": lock_acquired,
        "broker_state_observed": False,
        "broker_local_divergence_present": False,
        "broker_local_divergence_reason": "",
        "open_spy_order_present": False,
        "unexpected_non_spy_position_present": False,
        "duplicate_client_order_id_present": False,
        "unresolved_prior_mutation_present": False,
        "risk_cap_passed": False,
        "symbol": V189_SYMBOL,
        "client_order_id": certification_client_order_id(),
        "labels": list(ALLOWED_LABELS),
    }


def _static_preflight_blocker(preflight: Mapping[str, Any]) -> str:
    if preflight.get("live_endpoint_detected") is True:
        return "blocked_paper_endpoint_mismatch"
    if preflight.get("paper_endpoint_exact_match") is not True:
        return "blocked_paper_endpoint_mismatch"
    if preflight.get("APP_PROFILE_is_paper") is not True:
        return "blocked_credentials_unavailable"
    if preflight.get("paper_credentials_loaded") is not True:
        return "blocked_credentials_unavailable"
    if preflight.get("paper_mutation_policy_authorized") is not True:
        return "blocked_paper_mutation_policy"
    if preflight.get("mutation_process_lock_acquired") is not True:
        return "blocked_lock_contention"
    if preflight.get("unresolved_prior_mutation_present") is True:
        return "blocked_unresolved_prior_mutation"
    return ""


def _observed_preflight_blocker(preflight: Mapping[str, Any]) -> str:
    if preflight.get("broker_state_observed") is not True:
        return "blocked_broker_state_unobserved"
    if preflight.get("expected_paper_account_match") is not True:
        return "blocked_expected_account_mismatch"
    if preflight.get("broker_local_divergence_present") is True:
        return "blocked_broker_local_divergence"
    if preflight.get("unexpected_non_spy_position_present") is True:
        return "blocked_unexpected_position"
    if preflight.get("open_spy_order_present") is True:
        return "blocked_open_order_present"
    if preflight.get("duplicate_client_order_id_present") is True:
        return "blocked_duplicate_client_order_id"
    if preflight.get("spy_position_present") is not True:
        return "blocked_spy_position_missing"
    if preflight.get("spy_asset_certified") is not True:
        return "blocked_spy_asset_not_tradable"
    if preflight.get("reference_price_available") is not True:
        return "blocked_reference_price_unavailable"
    if preflight.get("risk_cap_passed") is not True:
        return "blocked_risk_cap"
    return ""


def _observe_pre_mutation_state(gateway: PaperMutationGateway) -> dict[str, Any]:
    observed_at = _utc_now().isoformat()
    account = gateway.get_account()
    positions = tuple(gateway.get_positions())
    open_orders = tuple(
        gateway.get_orders(
            AlpacaRecentOrderQuery(status_filter="open", symbol_filter=V189_SYMBOL)
        )
    )
    all_orders = tuple(
        gateway.get_orders(
            AlpacaRecentOrderQuery(status_filter="all", symbol_filter=V189_SYMBOL)
        )
    )
    asset = gateway.get_asset(V189_SYMBOL)
    return {
        "observed_at": observed_at,
        "account": _account_payload(account),
        "positions": [_position_payload(position) for position in positions],
        "open_orders": [_order_payload(order) for order in open_orders],
        "all_orders": [_order_payload(order) for order in all_orders],
        "asset": _asset_payload(asset),
    }


def _observed_preflight_fields(
    observed: Mapping[str, Any],
    runtime: PaperCertificationRuntime,
) -> dict[str, Any]:
    positions = _mapping_sequence(observed.get("positions"))
    open_orders = _mapping_sequence(observed.get("open_orders"))
    all_orders = _mapping_sequence(observed.get("all_orders"))
    account = _mapping(observed.get("account"))
    asset = _mapping(observed.get("asset"))
    spy_position = _spy_position(positions)
    non_spy_positions = [
        position
        for position in positions
        if str(position.get("symbol", "")).upper() != V189_SYMBOL
        and _decimal_or_zero(position.get("quantity")) != Decimal("0")
    ]
    open_spy_orders = [
        order
        for order in open_orders
        if str(order.get("symbol", "")).upper() == V189_SYMBOL
        and _normalize_status(order.get("status") or order.get("normalized_status"))
        not in TERMINAL_ORDER_STATUSES
    ]
    duplicate_orders = [
        order
        for order in all_orders
        if order.get("client_order_id") == certification_client_order_id()
    ]
    reference_price = _reference_price_from_position(spy_position)
    exposure = _decimal_or_zero(spy_position.get("market_value")) if spy_position else Decimal("0")
    asset_certified = (
        str(asset.get("symbol", "")).upper() == V189_SYMBOL
        and str(asset.get("status", "")).lower() in {"active", ""}
        and asset.get("tradable") is True
        and asset.get("fractionable") is True
    )
    return {
        "broker_state_observed": True,
        "expected_paper_account_match": (
            bool(runtime.expected_paper_account_id)
            and account.get("account_id") == runtime.expected_paper_account_id
        ),
        "open_spy_order_present": bool(open_spy_orders),
        "unexpected_non_spy_position_present": bool(non_spy_positions),
        "duplicate_client_order_id_present": bool(duplicate_orders),
        "spy_position_present": spy_position is not None
        and _decimal_or_zero(spy_position.get("quantity")) > Decimal("0"),
        "spy_asset_certified": asset_certified,
        "reference_price_available": reference_price is not None,
        "risk_cap_passed": (
            spy_position is not None
            and Decimal("0") < exposure <= V189_TOTAL_SPY_EXPOSURE_CAP
        ),
        "spy_position_market_value": _decimal_text(exposure),
        "open_spy_order_count": len(open_spy_orders),
        "unexpected_non_spy_position_count": len(non_spy_positions),
        "duplicate_client_order_count": len(duplicate_orders),
    }


def _broker_local_divergence_fields(
    output_root: Path,
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    latest = _read_json_mapping(output_root / "latest_run.json")
    if not latest:
        return {
            "broker_local_divergence_present": False,
            "broker_local_divergence_reason": "",
        }

    local_outcome = str(latest.get("outcome_classification", ""))
    if local_outcome in UNRESOLVED_OUTCOMES:
        return {
            "broker_local_divergence_present": False,
            "broker_local_divergence_reason": "",
        }

    reconciliation = _mapping(latest.get("reconciliation"))
    final_order = _mapping(reconciliation.get("final_order"))
    local_client_order_id = str(
        final_order.get("client_order_id") or latest.get("client_order_id") or ""
    )
    if local_client_order_id != certification_client_order_id():
        return {
            "broker_local_divergence_present": False,
            "broker_local_divergence_reason": "",
        }

    local_status = _normalize_status(
        final_order.get("normalized_status")
        or final_order.get("status")
        or reconciliation.get("final_order_status")
    )
    if local_outcome not in TERMINAL_SUCCESS_OUTCOMES and local_status not in TERMINAL_ORDER_STATUSES:
        return {
            "broker_local_divergence_present": False,
            "broker_local_divergence_reason": "",
        }

    broker_orders = [
        order
        for order in _mapping_sequence(observed.get("all_orders"))
        if order.get("client_order_id") == certification_client_order_id()
    ]
    if not broker_orders:
        return {
            "broker_local_divergence_present": False,
            "broker_local_divergence_reason": "",
        }

    broker_statuses = sorted(
        {
            _normalize_status(order.get("normalized_status") or order.get("status"))
            for order in broker_orders
        }
    )
    broker_statuses = [status for status in broker_statuses if status]
    if not broker_statuses:
        return {
            "broker_local_divergence_present": False,
            "broker_local_divergence_reason": "",
        }

    if local_status and all(status == local_status for status in broker_statuses):
        return {
            "broker_local_divergence_present": False,
            "broker_local_divergence_reason": "",
        }

    return {
        "broker_local_divergence_present": True,
        "broker_local_divergence_reason": "local_final_order_status_mismatch",
        "local_final_order_status": local_status,
        "broker_order_statuses": broker_statuses,
    }


def _build_certification_plan(observed: Mapping[str, Any]) -> dict[str, Any]:
    positions = _mapping_sequence(observed.get("positions"))
    spy_position = _spy_position(positions)
    reference_price = _reference_price_from_position(spy_position)
    if spy_position is None or reference_price is None:
        return _empty_certification_plan()

    existing_qty = _decimal_or_zero(spy_position.get("quantity"))
    quantity = V189_MIN_FRACTIONAL_QTY
    approximate_value = (quantity * reference_price).quantize(Decimal("0.0001"))
    if existing_qty < quantity or approximate_value > V189_CERTIFICATION_MAX_MARKET_VALUE:
        return _empty_certification_plan()

    limit_price = (reference_price * V189_NON_MARKETABLE_LIMIT_MULTIPLIER).quantize(
        Decimal("0.01"),
        rounding=ROUND_UP,
    )
    plan_source = {
        "client_order_id": certification_client_order_id(),
        "symbol": V189_SYMBOL,
        "side": "sell",
        "order_type": "limit",
        "time_in_force": "day",
        "quantity": _decimal_text(quantity),
        "limit_price": _decimal_text(limit_price),
        "reference_price": _decimal_text(reference_price),
    }
    return {
        "certification_plan_version": "v189_paper_certification_plan_v1",
        "certification_plan_id": "v189_certification_plan_"
        + hashlib.sha256(
            json.dumps(plan_source, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()[:16],
        "client_order_id": certification_client_order_id(),
        "symbol": V189_SYMBOL,
        "asset_class": "equity",
        "side": "sell",
        "order_type": "limit",
        "time_in_force": "day",
        "quantity": _decimal_text(quantity),
        "limit_price": _decimal_text(limit_price),
        "reference_price": _decimal_text(reference_price),
        "approximate_reference_market_value": _decimal_text(approximate_value),
        "strategy_order": V189_STRATEGY_ORDER,
        "labels": list(ALLOWED_LABELS),
        "expected_effect": "reduce_spy_exposure_if_filled",
    }


def _empty_certification_plan() -> dict[str, Any]:
    return {
        "certification_plan_version": "v189_paper_certification_plan_v1",
        "certification_plan_id": "",
        "client_order_id": certification_client_order_id(),
        "symbol": V189_SYMBOL,
        "strategy_order": V189_STRATEGY_ORDER,
        "labels": list(ALLOWED_LABELS),
        "status": "not_built",
    }


def _certification_order_request(plan: Mapping[str, Any]) -> AlpacaOrderRequest:
    return AlpacaOrderRequest(
        client_order_id=str(plan["client_order_id"]),
        symbol=str(plan["symbol"]),
        side="sell",
        asset_class="equity",
        qty=Decimal(str(plan["quantity"])),
        order_type="limit",
        time_in_force="day",
        limit_price=Decimal(str(plan["limit_price"])),
    )


def _cancel_and_reconcile(
    *,
    gateway: PaperMutationGateway,
    lifecycle_path: Path,
    initial_order: Mapping[str, Any],
    timeout_seconds: float,
    poll_interval_seconds: float,
    secret_values: Sequence[str],
) -> tuple[dict[str, Any], bool, bool]:
    status = _normalize_status(initial_order.get("normalized_status") or initial_order.get("status"))
    if status in {"rejected", "filled"}:
        return dict(initial_order), False, False

    order_id = str(initial_order.get("order_id", "")).strip()
    if not order_id:
        _append_lifecycle(
            lifecycle_path,
            "cancellation_blocked",
            {"reason": "missing_order_id"},
        )
        return dict(initial_order), False, False

    cancel_requested = True
    cancel_ambiguous = False
    try:
        response = gateway.request_order_cancellation(order_id)
        _append_lifecycle(
            lifecycle_path,
            "cancellation_requested",
            _json_safe({"order_id": order_id, "response": _generic_payload(response)}),
        )
    except Exception as exc:
        _append_lifecycle(
            lifecycle_path,
            "cancellation_ambiguous_lookup_started",
            {"message": _sanitize_text(str(exc), secret_values), "order_id": order_id},
        )
        cancel_ambiguous = True

    deadline = time.monotonic() + max(0.0, timeout_seconds)
    latest = dict(initial_order)
    while True:
        lookup = _lookup_by_client_order_id_safely(
            gateway,
            lifecycle_path,
            secret_values,
        )
        if lookup is not None:
            latest = _order_payload(lookup)
            _append_lifecycle(lifecycle_path, "reconciliation_poll", latest)
            status = _normalize_status(
                latest.get("normalized_status") or latest.get("status")
            )
            if status in TERMINAL_ORDER_STATUSES:
                return latest, cancel_ambiguous, cancel_requested

        if time.monotonic() >= deadline:
            return latest, cancel_ambiguous, cancel_requested
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)


def _lookup_by_client_order_id_safely(
    gateway: PaperMutationGateway,
    lifecycle_path: Path,
    secret_values: Sequence[str],
) -> Any | None:
    try:
        lookup = gateway.lookup_order_by_client_order_id(certification_client_order_id())
    except Exception as exc:
        _append_lifecycle(
            lifecycle_path,
            "client_order_id_lookup_failed",
            {"message": _sanitize_text(str(exc), secret_values)},
        )
        return None

    if lookup is None:
        _append_lifecycle(
            lifecycle_path,
            "client_order_id_lookup_empty",
            {"client_order_id": certification_client_order_id()},
        )
        return None

    _append_lifecycle(
        lifecycle_path,
        "client_order_id_lookup_found",
        _order_payload(lookup),
    )
    return lookup


def _classify_final_order(
    order: Mapping[str, Any],
    *,
    cancel_ambiguous: bool = False,
) -> str:
    if not order:
        return "unresolved_order_outcome"
    status = _normalize_status(order.get("normalized_status") or order.get("status"))
    filled_qty = _decimal_or_zero(order.get("filled_quantity") or order.get("filled_qty"))
    if status == "rejected":
        return "submitted_then_rejected"
    if status == "filled":
        return "submitted_filled_before_cancel"
    if status in {"canceled", "cancelled"} and filled_qty > Decimal("0"):
        return "submitted_partial_fill_then_cancelled"
    if status in {"canceled", "cancelled"} and cancel_ambiguous:
        return "cancel_ambiguous_reconciled"
    if status in {"canceled", "cancelled"}:
        return "submitted_cancel_confirmed"
    return "unresolved_order_outcome"


def _observe_post_mutation_state_safely(
    gateway: PaperMutationGateway,
    lifecycle_path: Path,
    secret_values: Sequence[str],
    *,
    attempted: bool,
) -> dict[str, Any]:
    if not attempted:
        return {"post_mutation_observation_performed": False}
    try:
        positions = tuple(gateway.get_positions())
        open_orders = tuple(
            gateway.get_orders(
                AlpacaRecentOrderQuery(status_filter="open", symbol_filter=V189_SYMBOL)
            )
        )
    except Exception as exc:
        message = _sanitize_text(str(exc), secret_values)
        _append_lifecycle(
            lifecycle_path,
            "post_mutation_observation_failed",
            {"message": message},
        )
        return {
            "post_mutation_observation_performed": True,
            "post_mutation_observation_available": False,
            "message": message,
        }

    payload = {
        "post_mutation_observation_performed": True,
        "post_mutation_observation_available": True,
        "positions": [_position_payload(position) for position in positions],
        "open_orders": [_order_payload(order) for order in open_orders],
    }
    _append_lifecycle(lifecycle_path, "post_mutation_observed", payload)
    return payload


def _build_reconciliation(
    *,
    outcome: str,
    blocker: str,
    preflight: Mapping[str, Any],
    certification_plan: Mapping[str, Any],
    final_order: Mapping[str, Any],
    post_observation: Mapping[str, Any],
    submit_ambiguous: bool,
    cancel_ambiguous: bool,
    restart_recovery_performed: bool,
    paper_submit_performed: bool,
    broker_mutation_performed: bool,
) -> dict[str, Any]:
    return {
        "reconciliation_version": "v189_paper_certification_reconciliation_v1",
        "outcome_classification": outcome,
        "classification_aliases": _classification_aliases(outcome),
        "blocker": blocker,
        "client_order_id": certification_client_order_id(),
        "submit_ambiguous": submit_ambiguous,
        "cancel_ambiguous": cancel_ambiguous,
        "restart_recovery_performed": restart_recovery_performed,
        "paper_submit_performed": paper_submit_performed,
        "broker_mutation_performed": broker_mutation_performed,
        "final_order": dict(final_order),
        "final_order_status": _normalize_status(
            final_order.get("normalized_status") or final_order.get("status")
        )
        if final_order
        else "",
        "preflight_passed": not blocker and paper_submit_performed,
        "preflight": dict(preflight),
        "certification_plan": dict(certification_plan),
        "post_observation": dict(post_observation),
        "labels": list(ALLOWED_LABELS),
    }


def _mutation_policy_payload() -> dict[str, Any]:
    return {
        "mutation_policy_version": "v189_bounded_spy_paper_mutation_policy_v1",
        "paper_only": True,
        "expected_endpoint": DEFAULT_ALPACA_PAPER_BASE_URL,
        "symbol_allowlist": [V189_SYMBOL],
        "asset_class_allowlist": ["equity"],
        "long_only": True,
        "strategy_order": V189_STRATEGY_ORDER,
        "total_spy_exposure_cap": _decimal_text(V189_TOTAL_SPY_EXPOSURE_CAP),
        "max_new_strategy_orders_per_completed_session_cycle": 1,
        "leverage_allowed": False,
        "shorting_allowed": False,
        "options_allowed": False,
        "crypto_allowed": False,
        "replace_allowed": False,
        "close_all_positions_allowed": False,
        "liquidate_allowed": False,
        "account_reset_allowed": False,
        "live_trading": False,
        "live_fallback_allowed": False,
        "automatic_submit_retry_allowed": False,
        "duplicate_recovery": "lookup_by_deterministic_client_order_id",
        "ambiguous_submit_recovery": "lookup_by_deterministic_client_order_id",
        "restart_recovery": "reconcile_by_deterministic_client_order_id_before_submit",
        "unresolved_prior_mutation_blocks_submit": True,
        "allowed_mutation": "one_non_marketable_fractional_spy_sell_limit_then_cancel",
        "labels": list(ALLOWED_LABELS),
    }


def _latest_run_payload(
    *,
    outcome: str,
    blocker: str,
    preflight: Mapping[str, Any],
    certification_plan: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    restart_recovery_performed: bool,
    paper_submit_performed: bool,
    broker_mutation_performed: bool,
) -> dict[str, Any]:
    return {
        "run_id": V189_RUN_ID,
        "generated_at": _utc_now().isoformat(),
        "outcome_classification": outcome,
        "classification_aliases": _classification_aliases(outcome),
        "blocker": blocker,
        "client_order_id": certification_client_order_id(),
        "restart_recovery_performed": restart_recovery_performed,
        "paper_submit_performed": paper_submit_performed,
        "broker_mutation_performed": broker_mutation_performed,
        "strategy_order": V189_STRATEGY_ORDER,
        "live_trading": False,
        "profit_claim": "none",
        "labels": [
            *ALLOWED_LABELS,
            f"paper_submit_performed={str(paper_submit_performed).lower()}",
            f"broker_mutation_performed={str(broker_mutation_performed).lower()}",
        ],
        "preflight": dict(preflight),
        "certification_plan": dict(certification_plan),
        "reconciliation": dict(reconciliation),
        "artifact_paths": {
            "preflight": "preflight.json",
            "mutation_policy": "mutation_policy.json",
            "certification_plan": "certification_plan.json",
            "order_lifecycle": "order_lifecycle.jsonl",
            "reconciliation": "reconciliation.json",
            "operating_brief": "operating_brief.md",
            "manifest": "manifest.jsonl",
            "latest_run": "latest_run.json",
        },
    }


def _render_operating_brief(latest_run: Mapping[str, Any]) -> str:
    preflight = _mapping(latest_run.get("preflight"))
    reconciliation = _mapping(latest_run.get("reconciliation"))
    return "\n".join(
        [
            "# v1.89 Paper Mutation Certification",
            "",
            f"- Outcome: `{latest_run.get('outcome_classification')}`",
            f"- Blocker: `{latest_run.get('blocker') or 'none'}`",
            f"- Client order id: `{latest_run.get('client_order_id')}`",
            f"- Paper submit performed: `{latest_run.get('paper_submit_performed')}`",
            f"- Broker mutation performed: `{latest_run.get('broker_mutation_performed')}`",
            f"- Strategy order: `{latest_run.get('strategy_order')}`",
            f"- Live trading: `{latest_run.get('live_trading')}`",
            f"- Paper endpoint exact match: `{preflight.get('paper_endpoint_exact_match')}`",
            f"- Expected paper account match: `{preflight.get('expected_paper_account_match')}`",
            f"- Final order status: `{reconciliation.get('final_order_status', '')}`",
            "",
            "Labels: "
            + ", ".join(str(label) for label in latest_run.get("labels", [])),
            "",
        ]
    )


def _write_manifest(output_root: Path) -> None:
    artifacts = {}
    for filename in (
        "preflight.json",
        "mutation_policy.json",
        "certification_plan.json",
        "order_lifecycle.jsonl",
        "reconciliation.json",
        "operating_brief.md",
        "latest_run.json",
    ):
        path = output_root / filename
        if path.exists():
            artifacts[filename] = _artifact_metadata(path)
    manifest = {
        "manifest_version": "v189_paper_certification_manifest_v1",
        "run_id": V189_RUN_ID,
        "generated_at": _utc_now().isoformat(),
        "artifacts": artifacts,
    }
    manifest_path = output_root / "manifest.jsonl"
    manifest_path.write_text(
        json.dumps(_json_safe(manifest), sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_metadata(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": path.name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _append_lifecycle(
    lifecycle_path: Path,
    event_type: str,
    payload: Mapping[str, Any],
) -> None:
    event = {
        "event_type": event_type,
        "observed_at": _utc_now().isoformat(),
        **dict(payload),
    }
    with lifecycle_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(_json_safe(event), sort_keys=True, separators=(",", ":"))
            + "\n"
        )


def _request_payload(request: AlpacaOrderRequest) -> dict[str, Any]:
    return {
        "client_order_id": request.client_order_id,
        "symbol": request.symbol,
        "side": request.side,
        "asset_class": request.asset_class,
        "qty": _decimal_text(request.qty),
        "notional": _decimal_text(request.notional),
        "order_type": request.order_type,
        "time_in_force": request.time_in_force,
        "limit_price": _decimal_text(request.limit_price),
    }


def _observation_lifecycle_payload(observed: Mapping[str, Any]) -> dict[str, Any]:
    positions = _mapping_sequence(observed.get("positions"))
    open_orders = _mapping_sequence(observed.get("open_orders"))
    all_orders = _mapping_sequence(observed.get("all_orders"))
    return {
        "observed_at": observed.get("observed_at", ""),
        "account_observed": bool(_mapping(observed.get("account"))),
        "position_count": len(positions),
        "open_spy_order_count": len(open_orders),
        "all_spy_order_count": len(all_orders),
        "asset_observed": bool(_mapping(observed.get("asset"))),
    }


def _has_unresolved_prior_mutation(output_root: Path) -> bool:
    latest_path = output_root / "latest_run.json"
    if not latest_path.is_file():
        return False
    try:
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    outcome = str(latest.get("outcome_classification", ""))
    return outcome in UNRESOLVED_OUTCOMES


def _has_local_submit_without_final_artifact(output_root: Path) -> bool:
    if (output_root / "latest_run.json").is_file():
        return False

    lifecycle_path = output_root / "order_lifecycle.jsonl"
    if not lifecycle_path.is_file():
        return False

    submit_events = {
        "submit_attempt",
        "submit_response_observed",
        "submit_ambiguous_lookup_started",
    }
    try:
        lines = lifecycle_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False

    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(event.get("event_type", "")) in submit_events:
            return True
    return False


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, Mapping) else {}


def _classification_aliases(outcome: str) -> list[str]:
    return list(CLASSIFICATION_ALIASES.get(outcome, ()))


def _account_payload(account: Any) -> dict[str, Any]:
    return {
        "account_id": _text_field(account, "account_id", "id"),
        "status": _text_field(account, "status"),
        "currency": _text_field(account, "currency"),
    }


def _position_payload(position: Any) -> dict[str, Any]:
    return {
        "symbol": _text_field(position, "symbol").upper(),
        "quantity": _decimal_text(_decimal_field(position, "qty", "quantity")),
        "market_value": _decimal_text(_decimal_field(position, "market_value")),
        "average_entry_price": _decimal_text(
            _decimal_field(
                position,
                "average_entry_price",
                "avg_entry_price",
                "average_price",
            )
        ),
        "side": _text_field(position, "side"),
    }


def _order_payload(order: Any) -> dict[str, Any]:
    status = _text_field(order, "status")
    return {
        "order_id": _text_field(order, "order_id", "id"),
        "client_order_id": _text_field(order, "client_order_id"),
        "symbol": _text_field(order, "symbol").upper(),
        "asset_class": _normalized_text_field(order, "asset_class"),
        "side": _normalized_text_field(order, "side"),
        "order_type": _normalized_text_field(order, "order_type", "type"),
        "time_in_force": _normalized_text_field(order, "time_in_force"),
        "status": _normalize_status(status),
        "normalized_status": _normalize_status(status),
        "quantity": _decimal_text(_decimal_field(order, "qty", "quantity")),
        "notional": _decimal_text(_decimal_field(order, "notional")),
        "limit_price": _decimal_text(_decimal_field(order, "limit_price")),
        "filled_quantity": _decimal_text(
            _decimal_field(order, "filled_qty", "filled_quantity")
        ),
        "filled_average_price": _decimal_text(
            _decimal_field(order, "filled_avg_price", "filled_average_price")
        ),
        "created_at": _time_text(_field(order, "created_at")),
        "submitted_at": _time_text(_field(order, "submitted_at")),
        "filled_at": _time_text(_field(order, "filled_at")),
    }


def _asset_payload(asset: Any) -> dict[str, Any]:
    return {
        "symbol": _text_field(asset, "symbol").upper(),
        "asset_class": _normalized_text_field(asset, "asset_class", "class"),
        "status": _normalized_text_field(asset, "status"),
        "tradable": _bool_field(asset, "tradable"),
        "fractionable": _bool_field(asset, "fractionable"),
    }


def _generic_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    data: dict[str, Any] = {}
    for name in ("id", "status", "client_order_id", "symbol"):
        if hasattr(value, name):
            data[name] = getattr(value, name)
    return data


def _spy_position(positions: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for position in positions:
        if str(position.get("symbol", "")).upper() == V189_SYMBOL:
            return position
    return None


def _reference_price_from_position(
    position: Mapping[str, Any] | None,
) -> Decimal | None:
    if position is None:
        return None
    quantity = _decimal_or_zero(position.get("quantity"))
    market_value = _decimal_or_zero(position.get("market_value"))
    if quantity <= 0 or market_value <= 0:
        return None
    return (market_value / quantity).quantize(Decimal("0.0001"))


def _credential_values(
    env: Mapping[str, str],
    config: AlpacaPaperConfig,
) -> tuple[str, ...]:
    candidates = (
        config.alpaca_api_key,
        config.alpaca_secret_key,
        env.get("ALPACA_API_SECRET_KEY"),
        env.get("APCA_API_KEY_ID"),
        env.get("APCA_API_SECRET_KEY"),
    )
    return tuple(
        value.strip()
        for value in candidates
        if isinstance(value, str) and value.strip()
    )


def _sanitize_text(text: str, secret_values: Sequence[str]) -> str:
    sanitized = str(text)
    for secret in sorted(set(secret_values), key=len, reverse=True):
        if secret:
            sanitized = sanitized.replace(secret, "<redacted>")
    return sanitized


def _clean_secret(value: Any) -> str:
    return str(value or "").strip()


def _text_field(value: Any, *names: str) -> str:
    raw = _first_field(value, *names)
    if raw is None:
        return ""
    enum_value = getattr(raw, "value", None)
    return str(enum_value if enum_value is not None else raw).strip()


def _normalized_text_field(value: Any, *names: str) -> str:
    return _normalize_status(_text_field(value, *names))


def _decimal_field(value: Any, *names: str) -> Decimal | None:
    raw = _first_field(value, *names)
    if raw is None or str(raw).strip() == "":
        return None
    return _decimal_or_zero(raw)


def _bool_field(value: Any, name: str) -> bool | None:
    raw = _field(value, name)
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() == "true"


def _first_field(value: Any, *names: str) -> Any:
    for name in names:
        raw = _field(value, name)
        if raw is not None:
            return raw
    return None


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    if is_dataclass(value):
        field_names = {field.name for field in fields(value)}
        if name in field_names:
            return getattr(value, name)
        return None
    return getattr(value, name, None)


def _decimal_or_zero(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _decimal_text(value: Any) -> str:
    if value is None:
        return ""
    return str(_decimal_or_zero(value))


def _time_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


__all__ = [
    "EXPECTED_PAPER_ACCOUNT_ENV",
    "PaperCertificationRuntime",
    "PaperMutationGateway",
    "V189_DEFAULT_OUTPUT_ROOT",
    "V189_RUN_ID",
    "certification_client_order_id",
    "evaluate_strategy_plan_mutation_lane",
    "paper_config_from_env_aliases",
    "run_paper_certification_drill",
]
