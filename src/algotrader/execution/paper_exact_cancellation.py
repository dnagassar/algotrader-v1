"""One-shot exact-target Alpaca paper cancellation behind durable gates."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.execution.durable_cancel import (
    DurableCancelCoordinator,
    DurableCancelObservation,
)
from algotrader.execution.order_journal import SqliteOrderJournal
from algotrader.execution.paper_cancellation_admission import (
    CANCELLATION_OPERATION,
    PAPER_CANCELLATION_MODE,
    PaperCancellationAdmissionRequest,
    build_operator_cancellation_authorization_evidence,
    evaluate_paper_cancellation_admission,
)
from algotrader.execution.paper_cancellation_handoff_preview import (
    DurableCancellationHandoffRequest,
    preview_durable_cancellation_handoff,
)
from algotrader.execution.paper_cancellation_invocation import (
    PaperCancellationInvocationRequest,
    PaperCancellationInvocationStatus,
    invoke_admitted_paper_cancellation,
)
from algotrader.execution.paper_cancellation_planning_adapter import (
    adapt_paper_lifecycle_to_cancellation_plan,
)
from algotrader.execution.paper_order_lifecycle_replay import (
    PaperOrderLifecycleEvent,
)
from algotrader.orchestration.cancellation_planning_flow import (
    CANCELABLE_CANCELLATION_STATUSES,
)
from algotrader.orchestration.cancellation_planning_policy import (
    TERMINAL_CANCELLATION_STATUSES,
    CancellationPlanningRequest,
)


PAPER_EXACT_CANCELLATION_VERSION = "paper_exact_cancellation_v1"
PAPER_EXACT_CANCELLATION_AUTHORIZATION_PHRASE = (
    "AUTHORIZE ONE EXACT ALPACA PAPER CANCELLATION ATTEMPT NO RETRY"
)
PAPER_EXACT_CANCELLATION_SYMBOL = "SPY"
PAPER_EXACT_CANCELLATION_REASON = "operator_authorized_exact_paper_cancellation"
PAPER_EXACT_CANCELLATION_EXPECTED_ACCOUNT_ENV = (
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"
)
PAPER_EXACT_CANCELLATION_DEFAULT_OUTPUT_PATH = Path(
    "runs/paper_exact_cancellation/latest/cancellation_result.json"
)
PAPER_EXACT_CANCELLATION_DEFAULT_JOURNAL_PATH = Path(
    "runs/paper_autopilot/state/order_journal.sqlite3"
)
PAPER_EXACT_CANCELLATION_MAXIMUM_SNAPSHOT_AGE_SECONDS = 30
PAPER_EXACT_CANCELLATION_AUTHORIZATION_TTL_SECONDS = 120
PAPER_EXACT_CANCELLATION_LEASE_TTL_SECONDS = 120

_LIVE_ENDPOINT_FRAGMENTS = (
    "https://api.alpaca.markets",
    "http://api.alpaca.markets",
)
_BrokerFactory = Callable[[AlpacaPaperConfig], Any]


class _ExactPostCancelObservationError(RuntimeError):
    """Safe typed failure for a mismatched or unusable post-cancel read."""


def run_exact_paper_cancellation(
    *,
    target_client_order_id: str,
    target_broker_order_id: str,
    target_symbol: str,
    paper_cancel_authorized: bool = False,
    authorization_phrase: str = "",
    output_path: Path | str = PAPER_EXACT_CANCELLATION_DEFAULT_OUTPUT_PATH,
    journal_path: Path | str = PAPER_EXACT_CANCELLATION_DEFAULT_JOURNAL_PATH,
    env: Mapping[str, str] | None = None,
    occurred_at: datetime | None = None,
    broker_factory: _BrokerFactory | None = None,
) -> dict[str, object]:
    """Attempt exactly one authorized paper cancel and never retry it."""

    source_env = dict(os.environ if env is None else env)
    client_order_id = str(target_client_order_id).strip()
    broker_order_id = str(target_broker_order_id).strip()
    symbol = str(target_symbol).strip().upper()
    output = Path(output_path)
    journal_path_value = Path(journal_path)
    started_at = _utc_now(occurred_at)
    result = _base_result(
        output_path=output,
        journal_path=journal_path_value,
        occurred_at=started_at,
        client_order_id=client_order_id,
        broker_order_id=broker_order_id,
        symbol=symbol,
    )

    blockers = _configuration_blockers(
        source_env,
        client_order_id=client_order_id,
        broker_order_id=broker_order_id,
        symbol=symbol,
        paper_cancel_authorized=paper_cancel_authorized,
        authorization_phrase=authorization_phrase,
    )
    if blockers:
        return _finish(
            output,
            result,
            outcome="blocked_before_broker_access",
            blockers=blockers,
        )

    journal = SqliteOrderJournal(journal_path_value)
    try:
        local_record = journal.get(client_order_id)
        runtime_control = journal.get_runtime_control()
    except Exception as exc:
        result["error_type"] = exc.__class__.__name__
        return _finish(
            output,
            result,
            outcome="blocked_local_journal_unavailable",
            blockers=("local_journal_unavailable",),
        )

    local_blocker = _local_target_blocker(
        local_record,
        broker_order_id=broker_order_id,
        symbol=symbol,
        trading_enabled=runtime_control.trading_enabled,
        stop_requested=runtime_control.stop_requested,
    )
    if local_blocker:
        return _finish(
            output,
            result,
            outcome="blocked_local_target_not_cancel_ready",
            blockers=(local_blocker,),
        )

    try:
        paper_config = _paper_config_from_env_aliases(source_env)
        gateway = (broker_factory or _build_gateway)(paper_config)
    except Exception as exc:
        result["error_type"] = exc.__class__.__name__
        return _finish(
            output,
            result,
            outcome="blocked_broker_construction_failed",
            blockers=("broker_construction_failed",),
        )

    result["broker_access_performed"] = True
    try:
        account = gateway.get_account()
        exact_order = gateway.get_order_by_id(broker_order_id)
    except Exception as exc:
        result["pre_cancel_read_attempted"] = True
        result["error_type"] = exc.__class__.__name__
        return _finish(
            output,
            result,
            outcome="stopped_pre_cancel_observation_failed",
            blockers=("paper_broker_read_failed",),
        )

    result["pre_cancel_read_attempted"] = True
    expected_account = str(
        source_env.get(PAPER_EXACT_CANCELLATION_EXPECTED_ACCOUNT_ENV, "")
    ).strip()
    account_values = {
        _field(account, "id"),
        _field(account, "account_number"),
    } - {""}
    account_matched = expected_account in account_values
    result["pre_cancel_account"] = {
        "observed": True,
        "expected_account_configured": True,
        "expected_account_matched": account_matched,
        "paper_endpoint_validated": True,
    }
    if not account_matched:
        return _finish(
            output,
            result,
            outcome="stopped_expected_paper_account_mismatch",
            blockers=("expected_paper_account_mismatch",),
        )

    snapshot, snapshot_blocker = _validated_order_snapshot(
        exact_order,
        expected_client_order_id=client_order_id,
        expected_broker_order_id=broker_order_id,
        expected_symbol=symbol,
    )
    result["pre_cancel_observation"] = snapshot
    if snapshot_blocker:
        return _finish(
            output,
            result,
            outcome="stopped_exact_target_missing_or_mismatched",
            blockers=(snapshot_blocker,),
        )

    broker_status = str(snapshot["broker_status"])
    if broker_status in TERMINAL_CANCELLATION_STATUSES or broker_status in {
        "cancelled",
        "replaced",
    }:
        return _finish(
            output,
            result,
            outcome="stopped_target_already_terminal",
            blockers=(f"target_already_terminal:{broker_status}",),
        )
    if broker_status not in CANCELABLE_CANCELLATION_STATUSES:
        return _finish(
            output,
            result,
            outcome="stopped_target_not_cancelable",
            blockers=(f"target_not_cancelable:{broker_status}",),
        )

    snapshot_at = _utc_now(occurred_at)
    try:
        fresh_record = journal.record_broker_observation(
            client_order_id,
            snapshot_at,
            broker_order_id=broker_order_id,
            broker_status=broker_status,
            filled_quantity=str(snapshot["filled_quantity"]),
            filled_average_price=(
                str(snapshot["filled_average_price"])
                if snapshot["filled_average_price"]
                else None
            ),
        )
        planning_artifact = adapt_paper_lifecycle_to_cancellation_plan(
            (
                PaperOrderLifecycleEvent(
                    observed_at=snapshot_at.isoformat(),
                    client_order_id=client_order_id,
                    broker_order_id=broker_order_id,
                    status=broker_status,
                    filled_qty=str(snapshot["filled_quantity"]),
                    submitted=True,
                    mutated=False,
                    source="authorized_paper_pre_cancel_observation",
                ),
            ),
            request=CancellationPlanningRequest(
                target_client_order_id=client_order_id,
                target_broker_order_id=broker_order_id,
                target_symbol=symbol,
                reason=PAPER_EXACT_CANCELLATION_REASON,
                cancellation_permitted=True,
                snapshot_fresh=True,
                trading_enabled=runtime_control.trading_enabled,
                stop_requested=runtime_control.stop_requested,
            ),
            as_of=snapshot_at,
            observation_symbol=symbol,
        )
        result["planning"] = planning_artifact.to_dict()
        if not planning_artifact.planned or planning_artifact.planning_result is None:
            return _finish(
                output,
                result,
                outcome="blocked_cancellation_planning",
                blockers=("cancellation_plan_not_available",),
            )

        handoff = preview_durable_cancellation_handoff(
            planning_artifact.planning_result,
            fresh_record,
            DurableCancellationHandoffRequest(
                as_of=snapshot_at,
                maximum_record_age_seconds=(
                    PAPER_EXACT_CANCELLATION_MAXIMUM_SNAPSHOT_AGE_SECONDS
                ),
                handoff_permitted=True,
            ),
        )
        result["handoff"] = handoff.to_dict()
        if not handoff.prepared or handoff.identity is None:
            return _finish(
                output,
                result,
                outcome="blocked_durable_handoff",
                blockers=("durable_handoff_not_prepared",),
            )

        authorization = build_operator_cancellation_authorization_evidence(
            mode=PAPER_CANCELLATION_MODE,
            operation=CANCELLATION_OPERATION,
            source_plan_id=handoff.source_plan_id,
            cancel_intent_id=handoff.identity.cancel_intent_id,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            issued_at=snapshot_at,
            expires_at=snapshot_at
            + timedelta(
                seconds=PAPER_EXACT_CANCELLATION_AUTHORIZATION_TTL_SECONDS
            ),
            authorized=True,
        )
        latest_control = journal.get_runtime_control()
        admission = evaluate_paper_cancellation_admission(
            handoff,
            authorization,
            PaperCancellationAdmissionRequest(
                evaluated_at=snapshot_at,
                trading_enabled=latest_control.trading_enabled,
                stop_requested=latest_control.stop_requested,
                snapshot_fresh=True,
            ),
        )
        result["admission"] = admission.to_dict()
        if not admission.admitted:
            return _finish(
                output,
                result,
                outcome="blocked_exact_authorization_admission",
                blockers=(
                    "exact_authorization_admission_blocked"
                    if admission.blocker is None
                    else admission.blocker.value,
                ),
            )
    except Exception as exc:
        result["error_type"] = exc.__class__.__name__
        return _finish(
            output,
            result,
            outcome="blocked_local_pipeline_failure",
            blockers=("local_cancellation_pipeline_failure",),
        )

    invocation_at = _utc_now(occurred_at)
    snapshot_age_seconds = (invocation_at - snapshot_at).total_seconds()
    result["snapshot_age_seconds"] = snapshot_age_seconds
    if (
        snapshot_age_seconds < 0
        or snapshot_age_seconds
        > PAPER_EXACT_CANCELLATION_MAXIMUM_SNAPSHOT_AGE_SECONDS
    ):
        return _finish(
            output,
            result,
            outcome="blocked_snapshot_not_fresh",
            blockers=("snapshot_not_fresh",),
        )

    cancel_call_count = 0
    post_read_count = 0
    post_snapshot: dict[str, object] = {}
    post_observation_persisted = False

    def cancel_once() -> object:
        nonlocal cancel_call_count
        if cancel_call_count:
            raise RuntimeError("paper_cancel_retry_prevented")
        cancel_call_count = 1
        return gateway.execute_exact(broker_order_id)

    def observe_once(_response: object) -> DurableCancelObservation:
        nonlocal post_observation_persisted, post_read_count, post_snapshot
        if post_read_count:
            raise _ExactPostCancelObservationError(
                "post_cancel_observation_retry_prevented"
            )
        post_read_count = 1
        observed_order = gateway.get_order_by_id(broker_order_id)
        post_snapshot, blocker = _validated_order_snapshot(
            observed_order,
            expected_client_order_id=client_order_id,
            expected_broker_order_id=broker_order_id,
            expected_symbol=symbol,
        )
        if blocker:
            raise _ExactPostCancelObservationError(blocker)
        post_at = _utc_now(occurred_at)
        journal.record_broker_observation(
            client_order_id,
            post_at,
            broker_order_id=broker_order_id,
            broker_status=str(post_snapshot["broker_status"]),
            filled_quantity=str(post_snapshot["filled_quantity"]),
            filled_average_price=(
                str(post_snapshot["filled_average_price"])
                if post_snapshot["filled_average_price"]
                else None
            ),
        )
        post_observation_persisted = True
        return DurableCancelObservation(
            broker_status=_cancel_observation_status(
                str(post_snapshot["broker_status"])
            )
        )

    invocation = invoke_admitted_paper_cancellation(
        admission,
        DurableCancelCoordinator(journal),
        PaperCancellationInvocationRequest(
            expected_admission_id=admission.admission_id,
            occurred_at=invocation_at,
            lease_ttl_seconds=PAPER_EXACT_CANCELLATION_LEASE_TTL_SECONDS,
            snapshot_fresh=True,
            invocation_permitted=True,
        ),
        cancel=cancel_once,
        observe=observe_once,
        sanitize_exception=lambda exc: exc.__class__.__name__,
    )
    result.update(
        invocation=invocation.to_dict(),
        cancel_attempted=cancel_call_count == 1,
        cancel_call_count=cancel_call_count,
        broker_mutation_attempted=cancel_call_count == 1,
        paper_cancel_attempted=cancel_call_count == 1,
        post_cancel_read_attempted=post_read_count == 1,
        post_cancel_read_count=post_read_count,
        post_cancel_observation=post_snapshot,
        post_cancel_observation_persisted=(
            invocation.status is PaperCancellationInvocationStatus.OBSERVED
            and post_observation_persisted
        ),
    )

    if (
        invocation.status is PaperCancellationInvocationStatus.AMBIGUOUS
        and cancel_call_count == 1
        and post_read_count == 0
    ):
        post_snapshot, post_read_count = _fallback_post_cancel_read(
            gateway,
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
            symbol=symbol,
        )
        fallback_persistence_error_type = ""
        if post_snapshot.get("identity_matched") is True:
            try:
                post_at = _utc_now(occurred_at)
                journal.record_broker_observation(
                    client_order_id,
                    post_at,
                    broker_order_id=broker_order_id,
                    broker_status=str(post_snapshot["broker_status"]),
                    filled_quantity=str(post_snapshot["filled_quantity"]),
                    filled_average_price=(
                        str(post_snapshot["filled_average_price"])
                        if post_snapshot["filled_average_price"]
                        else None
                    ),
                )
                if admission.identity is None:
                    raise RuntimeError("admitted_cancel_identity_missing")
                journal.record_cancel_observation(
                    admission.identity.cancel_intent_id,
                    post_at,
                    broker_status=_cancel_observation_status(
                        str(post_snapshot["broker_status"])
                    ),
                )
                post_observation_persisted = True
            except Exception as exc:
                fallback_persistence_error_type = exc.__class__.__name__
        result.update(
            post_cancel_read_attempted=True,
            post_cancel_read_count=post_read_count,
            post_cancel_observation=post_snapshot,
            post_cancel_observation_persisted=post_observation_persisted,
            fallback_persistence_error_type=fallback_persistence_error_type,
        )

    if cancel_call_count == 0:
        return _finish(
            output,
            result,
            outcome="blocked_before_cancel_callback",
            blockers=(invocation.blocker or "durable_cancel_blocked",),
        )

    post_status = str(post_snapshot.get("broker_status", ""))
    if (
        post_status in {"canceled", "cancelled"}
        and result.get("post_cancel_observation_persisted") is True
    ):
        return _finish(
            output,
            result,
            outcome="cancellation_confirmed",
            blockers=(),
        )
    if invocation.status is PaperCancellationInvocationStatus.AMBIGUOUS:
        return _finish(
            output,
            result,
            outcome="stopped_cancel_attempt_ambiguous_no_retry",
            blockers=(invocation.blocker or "cancel_response_ambiguous",),
        )
    return _finish(
        output,
        result,
        outcome="cancel_attempt_observed_unconfirmed_no_retry",
        blockers=(f"post_cancel_status:{post_status or 'unavailable'}",),
    )


def _fallback_post_cancel_read(
    gateway: Any,
    *,
    broker_order_id: str,
    client_order_id: str,
    symbol: str,
) -> tuple[dict[str, object], int]:
    try:
        order = gateway.get_order_by_id(broker_order_id)
    except Exception as exc:
        return {"observed": False, "error_type": exc.__class__.__name__}, 1
    snapshot, blocker = _validated_order_snapshot(
        order,
        expected_client_order_id=client_order_id,
        expected_broker_order_id=broker_order_id,
        expected_symbol=symbol,
    )
    if blocker:
        snapshot["blocker"] = blocker
    return snapshot, 1


def _configuration_blockers(
    env: Mapping[str, str],
    *,
    client_order_id: str,
    broker_order_id: str,
    symbol: str,
    paper_cancel_authorized: bool,
    authorization_phrase: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if type(paper_cancel_authorized) is not bool or not paper_cancel_authorized:
        blockers.append("paper_cancel_not_authorized")
    if authorization_phrase != PAPER_EXACT_CANCELLATION_AUTHORIZATION_PHRASE:
        blockers.append("authorization_phrase_mismatch")
    if not client_order_id:
        blockers.append("target_client_order_id_required")
    if not broker_order_id:
        blockers.append("target_broker_order_id_required")
    if symbol != PAPER_EXACT_CANCELLATION_SYMBOL:
        blockers.append("exact_spy_symbol_required")
    if str(env.get("APP_PROFILE", "")).strip().lower() != "paper":
        blockers.append("paper_profile_required")
    if not _first_value(env, "ALPACA_API_KEY", "APCA_API_KEY_ID"):
        blockers.append("paper_api_key_required")
    if not _first_value(
        env,
        "ALPACA_SECRET_KEY",
        "ALPACA_API_SECRET_KEY",
        "APCA_API_SECRET_KEY",
    ):
        blockers.append("paper_secret_key_required")
    if not str(
        env.get(PAPER_EXACT_CANCELLATION_EXPECTED_ACCOUNT_ENV, "")
    ).strip():
        blockers.append("expected_paper_account_required")
    paper_url = str(
        env.get("ALPACA_PAPER_BASE_URL", DEFAULT_ALPACA_PAPER_BASE_URL)
    ).strip().rstrip("/").lower()
    if paper_url != DEFAULT_ALPACA_PAPER_BASE_URL:
        blockers.append("exact_paper_endpoint_required")
    for name in ("ALPACA_BASE_URL", "APCA_API_BASE_URL"):
        value = str(env.get(name, "")).strip().rstrip("/").lower()
        if value and any(fragment in value for fragment in _LIVE_ENDPOINT_FRAGMENTS):
            blockers.append(f"live_endpoint_detected:{name}")
    return tuple(blockers)


def _local_target_blocker(
    record: object,
    *,
    broker_order_id: str,
    symbol: str,
    trading_enabled: bool,
    stop_requested: bool,
) -> str:
    if record is None:
        return "local_target_missing"
    if str(getattr(record, "broker_order_id", "")).strip() != broker_order_id:
        return "local_broker_order_id_mismatch"
    if str(getattr(record, "symbol", "")).strip().upper() != symbol:
        return "local_symbol_mismatch"
    if bool(getattr(record, "terminal", False)):
        return "local_target_terminal"
    if not trading_enabled:
        return "trading_disabled"
    if stop_requested:
        return "stop_requested"
    return ""


def _validated_order_snapshot(
    order: object,
    *,
    expected_client_order_id: str,
    expected_broker_order_id: str,
    expected_symbol: str,
) -> tuple[dict[str, object], str]:
    if order is None:
        return {"observed": False}, "target_order_missing"
    broker_order_id = _field(order, "id", "order_id")
    client_order_id = _field(order, "client_order_id")
    symbol = _field(order, "symbol").upper()
    broker_status = _normalized_status(_field(order, "status"))
    filled_quantity = _non_negative_decimal_text(
        _field(order, "filled_qty", "filled_quantity") or "0"
    )
    filled_average_price = _positive_decimal_text(
        _field(order, "filled_avg_price", "filled_average_price")
    )
    snapshot: dict[str, object] = {
        "observed": True,
        "broker_order_id": broker_order_id,
        "client_order_id": client_order_id,
        "symbol": symbol,
        "broker_status": broker_status,
        "filled_quantity": filled_quantity,
        "filled_average_price": filled_average_price,
        "identity_matched": False,
    }
    if broker_order_id != expected_broker_order_id:
        return snapshot, "broker_order_id_mismatch"
    if client_order_id != expected_client_order_id:
        return snapshot, "client_order_id_mismatch"
    if symbol != expected_symbol:
        return snapshot, "symbol_mismatch"
    if not broker_status:
        return snapshot, "broker_status_missing"
    if filled_quantity == "":
        return snapshot, "filled_quantity_invalid"
    snapshot["identity_matched"] = True
    return snapshot, ""


def _base_result(
    *,
    output_path: Path,
    journal_path: Path,
    occurred_at: datetime,
    client_order_id: str,
    broker_order_id: str,
    symbol: str,
) -> dict[str, object]:
    return {
        "version": PAPER_EXACT_CANCELLATION_VERSION,
        "outcome": "not_started",
        "blocker": "",
        "blockers": [],
        "occurred_at": occurred_at.isoformat(),
        "target_client_order_id": client_order_id,
        "target_broker_order_id": broker_order_id,
        "target_symbol": symbol,
        "output_path": str(output_path),
        "journal_path": str(journal_path),
        "broker_access_performed": False,
        "pre_cancel_read_attempted": False,
        "cancel_attempted": False,
        "cancel_call_count": 0,
        "broker_mutation_attempted": False,
        "paper_cancel_attempted": False,
        "post_cancel_read_attempted": False,
        "post_cancel_read_count": 0,
        "submit_attempted": False,
        "replace_attempted": False,
        "close_attempted": False,
        "liquidate_attempted": False,
        "live_access_performed": False,
        "live_mutation_performed": False,
        "no_retry": True,
    }


def _finish(
    path: Path,
    result: dict[str, object],
    *,
    outcome: str,
    blockers: Sequence[str],
) -> dict[str, object]:
    normalized_blockers = tuple(str(value).strip() for value in blockers if value)
    result.update(
        outcome=outcome,
        blocker=normalized_blockers[0] if normalized_blockers else "",
        blockers=list(normalized_blockers),
    )
    return _write_result(path, result)


def _write_result(path: Path, result: dict[str, object]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return result


class _SdkExactCancellationGateway:
    """Narrow SDK wrapper exposing exact reads and one cancel call."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._raw_client = client.raw_trading_client

    def get_account(self) -> object:
        return self._client.get_account()

    def get_order_by_id(self, broker_order_id: str) -> object:
        return self._raw_client.get_order_by_id(broker_order_id)

    def execute_exact(self, broker_order_id: str) -> object:
        return self._raw_client.cancel_order_by_id(broker_order_id)


def _paper_config_from_env_aliases(
    env: Mapping[str, str],
) -> AlpacaPaperConfig:
    source = dict(env)
    if not source.get("ALPACA_API_KEY") and source.get("APCA_API_KEY_ID"):
        source["ALPACA_API_KEY"] = source["APCA_API_KEY_ID"]
    if not source.get("ALPACA_SECRET_KEY") and source.get("ALPACA_API_SECRET_KEY"):
        source["ALPACA_SECRET_KEY"] = source["ALPACA_API_SECRET_KEY"]
    if not source.get("ALPACA_SECRET_KEY") and source.get("APCA_API_SECRET_KEY"):
        source["ALPACA_SECRET_KEY"] = source["APCA_API_SECRET_KEY"]
    return AlpacaPaperConfig.from_env(source)


def _build_gateway(config: AlpacaPaperConfig) -> _SdkExactCancellationGateway:
    from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient

    return _SdkExactCancellationGateway(AlpacaSdkClient(config))


def _field(value: object, *names: str) -> str:
    for name in names:
        if isinstance(value, Mapping) and name in value:
            candidate = value.get(name)
        else:
            candidate = getattr(value, name, None)
        candidate = getattr(candidate, "value", candidate)
        text = "" if candidate is None else str(candidate).strip()
        if text:
            return text
    return ""


def _non_negative_decimal_text(value: str) -> str:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return ""
    if not parsed.is_finite() or parsed < 0:
        return ""
    return str(parsed)


def _positive_decimal_text(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return ""
    if not parsed.is_finite() or parsed <= 0:
        return ""
    return str(parsed)


def _normalized_status(value: object) -> str:
    text = str(value).strip().lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def _cancel_observation_status(broker_order_status: str) -> str:
    status = _normalized_status(broker_order_status)
    if status in {
        "canceled",
        "cancelled",
        "not_found",
        "pending_cancel",
        "rejected",
    }:
        return status
    return "unknown"


def _first_value(env: Mapping[str, str], *names: str) -> str:
    for name in names:
        value = str(env.get(name, "")).strip()
        if value:
            return value
    return ""


def _utc_now(value: datetime | None) -> datetime:
    resolved = datetime.now(UTC) if value is None else value
    if resolved.tzinfo is None or resolved.utcoffset() != UTC.utcoffset(resolved):
        raise ValueError("occurred_at must be a timezone-aware UTC datetime.")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m algotrader.execution.paper_exact_cancellation",
        description=(
            "Cancel one exact SPY Alpaca paper order through the durable gate."
        ),
    )
    parser.add_argument("--target-client-order-id", required=True)
    parser.add_argument("--target-broker-order-id", required=True)
    parser.add_argument("--target-symbol", required=True)
    parser.add_argument("--paper-cancel-authorized", action="store_true")
    parser.add_argument("--authorization-phrase", required=True)
    parser.add_argument(
        "--output-path",
        default=str(PAPER_EXACT_CANCELLATION_DEFAULT_OUTPUT_PATH),
    )
    parser.add_argument(
        "--journal-path",
        default=str(PAPER_EXACT_CANCELLATION_DEFAULT_JOURNAL_PATH),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_exact_paper_cancellation(
        target_client_order_id=args.target_client_order_id,
        target_broker_order_id=args.target_broker_order_id,
        target_symbol=args.target_symbol,
        paper_cancel_authorized=args.paper_cancel_authorized,
        authorization_phrase=args.authorization_phrase,
        output_path=args.output_path,
        journal_path=args.journal_path,
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    if result.get("outcome") == "cancellation_confirmed":
        return 0
    return 2 if result.get("cancel_attempted") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PAPER_EXACT_CANCELLATION_AUTHORIZATION_PHRASE",
    "PAPER_EXACT_CANCELLATION_DEFAULT_JOURNAL_PATH",
    "PAPER_EXACT_CANCELLATION_DEFAULT_OUTPUT_PATH",
    "PAPER_EXACT_CANCELLATION_VERSION",
    "build_parser",
    "main",
    "run_exact_paper_cancellation",
]
