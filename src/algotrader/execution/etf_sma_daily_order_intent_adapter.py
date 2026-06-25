"""v1.92 daily ExecutionPlan to offline Paper OMS order-intent adapter.

This module is fixture-only. It creates reviewable order-intent packets from
approved daily ExecutionPlans and can route the packet into the existing v1.91
fake OMS rehearsal. It does not select, construct, or import real SDK clients.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_UP
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.execution.etf_sma_daily_oms_rehearsal import (
    ACTIONABLE_PLAN_ACTIONS,
    HOLD_PLAN_ACTIONS,
    OFFLINE_FIXTURE_BROKER_STATE_MODE,
    OFFLINE_OMS_REHEARSAL_MODE,
    OfflineOmsFixture,
    deterministic_client_order_id,
    deterministic_execution_plan_digest,
    load_daily_execution_plan_packet,
    run_v191_offline_oms_rehearsal,
    sample_daily_execution_plan_packet,
)
from algotrader.execution.paper_mutation_oms import (
    V189_MIN_FRACTIONAL_QTY,
    V189_NON_MARKETABLE_LIMIT_MULTIPLIER,
)
from algotrader.execution.paper_order_policy import (
    ASSET_CLASS_EQUITY,
    paper_order_policy_for_asset_class,
)

V192_RUN_ID = "v192_order_intent_adapter"
V192_DEFAULT_OUTPUT_ROOT = "runs/paper_lab/v192_order_intent_adapter_smoke"
V192_PACKET_VERSION = "v192_order_intent_adapter_packet_v1"
V192_MANIFEST_VERSION = "v192_order_intent_adapter_manifest_v1"
V192_ORDER_INTENT_VERSION = "v192_paper_oms_order_intent_v1"
V192_CLIENT_ORDER_ID_PREFIX = "v192-spy"
V192_SAFETY_LABELS = (
    "paper_lab_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
    "paper_submit_authorized=false",
)
OFFLINE_APPROVAL_SOURCE = "offline_fixture_only"
NO_APPROVAL_SOURCE = "none"
OFFLINE_APPROVAL_MODE = "offline_fixture"
NO_APPROVAL_MODE = "not_granted"

_REQUIRED_EXECUTION_PLAN_FIELDS = (
    "execution_plan_version",
    "execution_plan_id",
    "execution_plan_status",
    "execution_plan_action",
    "execution_plan_symbol",
    "execution_plan_reason",
    "execution_plan_blocker",
    "execution_plan_source_preview_decision",
    "execution_plan_requires_approval",
    "execution_plan_broker_order_required",
    "execution_plan_submit_allowed",
    "execution_plan_paper_submit_authorized",
    "execution_plan_live_authorized",
    "execution_plan_broker_mutation_performed",
    "execution_plan_created_order_payload",
    "execution_plan_labels",
)


@dataclass(frozen=True, slots=True)
class OfflineOrderIntentApprovalFixture:
    """Explicit fixture-only approval marker for offline order-intent rehearsals."""

    approval_granted: bool = False
    approval_mode: str = OFFLINE_APPROVAL_MODE
    approval_source: str = OFFLINE_APPROVAL_SOURCE
    broker_state_mode: str = OFFLINE_FIXTURE_BROKER_STATE_MODE

    def __post_init__(self) -> None:
        object.__setattr__(self, "approval_granted", bool(self.approval_granted))
        object.__setattr__(
            self,
            "approval_mode",
            str(self.approval_mode).strip() or OFFLINE_APPROVAL_MODE,
        )
        object.__setattr__(
            self,
            "approval_source",
            str(self.approval_source).strip() or OFFLINE_APPROVAL_SOURCE,
        )
        object.__setattr__(
            self,
            "broker_state_mode",
            str(self.broker_state_mode).strip() or "broker_state_not_observed",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_granted": self.approval_granted,
            "approval_mode": self.approval_mode,
            "approval_source": self.approval_source,
            "broker_state_mode": self.broker_state_mode,
            "real_operator_authorization": False,
            "paper_submit_authorized": False,
        }


def run_v192_order_intent_adapter(
    daily_packet_or_execution_plan: Mapping[str, Any],
    *,
    approval_fixture: OfflineOrderIntentApprovalFixture | None = None,
    oms_fixture: OfflineOmsFixture | None = None,
    output_root: Path | str = V192_DEFAULT_OUTPUT_ROOT,
    input_path: Path | str | None = None,
    run_id: str = V192_RUN_ID,
) -> dict[str, Any]:
    """Build an offline order-intent packet and optionally run fake OMS rehearsal."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    plan = _extract_execution_plan(daily_packet_or_execution_plan)
    packet_source = _packet_source(daily_packet_or_execution_plan)
    _validate_execution_plan_shape(plan)
    plan_digest = deterministic_execution_plan_digest(plan)
    client_order_id = deterministic_v192_client_order_id(plan)
    approval = _approval_payload(approval_fixture)
    execution_mode = OFFLINE_OMS_REHEARSAL_MODE
    broker_state_mode = _broker_state_mode(packet_source, approval_fixture)
    fixture = oms_fixture or OfflineOmsFixture()

    classification = ""
    blocker = ""
    order_intent: dict[str, Any] = {}
    oms_packet: dict[str, Any] = {}

    static_blocker = _static_plan_blocker(plan, packet_source)
    if static_blocker:
        classification = static_blocker
        blocker = static_blocker
    elif _is_hold_noop_plan(plan):
        classification = "not_submitted_hold_noop"
    elif not _is_actionable_plan(plan):
        classification = "blocked_unaccepted_execution_plan"
        blocker = classification
    elif approval["approval_granted"] is not True:
        classification = "approval_required"
        blocker = "approval_required"
    elif not _is_offline_fixture_approval(approval):
        classification = "blocked_non_offline_approval"
        blocker = classification
    elif broker_state_mode != OFFLINE_FIXTURE_BROKER_STATE_MODE:
        classification = "blocked_broker_state_not_observed"
        blocker = classification
    elif fixture_blocker := _offline_fixture_blocker(fixture):
        classification = fixture_blocker
        blocker = fixture_blocker
    else:
        order_intent = _build_order_intent(
            run_id=run_id,
            packet_source=packet_source,
            plan=plan,
            plan_digest=plan_digest,
            client_order_id=client_order_id,
            approval=approval,
            execution_mode=execution_mode,
            broker_state_mode=broker_state_mode,
            fixture=fixture,
        )
        oms_packet = run_v191_offline_oms_rehearsal(
            daily_packet_or_execution_plan,
            output_root=root / "v191_fake_oms_rehearsal",
            input_path=input_path,
            fixture=fixture,
            run_id=f"{run_id}_fake_oms",
            client_order_id_override=client_order_id,
            order_intent_override=order_intent,
        )
        classification = str(oms_packet.get("oms_classification", ""))
        blocker = str(oms_packet.get("blocker") or "")

    packet = _build_packet(
        run_id=run_id,
        root=root,
        input_path=input_path,
        packet_source=packet_source,
        plan=plan,
        plan_digest=plan_digest,
        client_order_id=client_order_id,
        approval=approval,
        execution_mode=execution_mode,
        broker_state_mode=broker_state_mode,
        order_intent=order_intent,
        oms_packet=oms_packet,
        classification=classification,
        blocker=blocker,
        fixture=fixture,
    )
    _write_artifacts(root, packet)
    return packet


def run_v192_order_intent_adapter_from_path(
    input_path: Path | str,
    *,
    approval_fixture: OfflineOrderIntentApprovalFixture | None = None,
    oms_fixture: OfflineOmsFixture | None = None,
    output_root: Path | str = V192_DEFAULT_OUTPUT_ROOT,
    run_id: str = V192_RUN_ID,
) -> dict[str, Any]:
    packet = load_daily_execution_plan_packet(input_path)
    return run_v192_order_intent_adapter(
        packet,
        approval_fixture=approval_fixture,
        oms_fixture=oms_fixture,
        output_root=output_root,
        input_path=input_path,
        run_id=run_id,
    )


def deterministic_v192_client_order_id(
    daily_packet_or_execution_plan: Mapping[str, Any],
) -> str:
    """Return the stable v1.92 order-intent identity derived from the plan."""

    plan_digest = deterministic_execution_plan_digest(daily_packet_or_execution_plan)
    return f"{V192_CLIENT_ORDER_ID_PREFIX}-{plan_digest[:24]}"


def sample_v192_daily_execution_plan_packet() -> dict[str, Any]:
    packet = sample_daily_execution_plan_packet()
    packet["broker_state_mode"] = OFFLINE_FIXTURE_BROKER_STATE_MODE
    packet["broker_state_source"] = OFFLINE_APPROVAL_SOURCE
    return packet


def _build_packet(
    *,
    run_id: str,
    root: Path,
    input_path: Path | str | None,
    packet_source: Mapping[str, Any],
    plan: Mapping[str, Any],
    plan_digest: str,
    client_order_id: str,
    approval: Mapping[str, Any],
    execution_mode: str,
    broker_state_mode: str,
    order_intent: Mapping[str, Any],
    oms_packet: Mapping[str, Any],
    classification: str,
    blocker: str,
    fixture: OfflineOmsFixture,
) -> dict[str, Any]:
    fake_submit_count = int(oms_packet.get("fake_submit_call_count") or 0)
    fake_cancel_count = int(oms_packet.get("fake_cancel_call_count") or 0)
    order_side = str(order_intent.get("side", ""))
    quantity = str(order_intent.get("quantity", ""))
    notional = str(order_intent.get("notional", ""))
    quantity_or_notional_source = str(
        order_intent.get("quantity_or_notional_source", "")
    )
    order_type = str(order_intent.get("order_type", ""))
    time_in_force = str(order_intent.get("time_in_force", ""))
    source_plan_id = str(plan.get("execution_plan_id", ""))
    return {
        "packet_version": V192_PACKET_VERSION,
        "run_id": run_id,
        "generated_at": _utc_now_text(),
        "input_daily_packet_or_execution_plan_path": (
            str(input_path) if input_path is not None else ""
        ),
        "as_of_date": _source_value(packet_source, "as_of_date"),
        "symbol": str(plan.get("execution_plan_symbol", "")),
        "source_execution_plan_id": source_plan_id,
        "execution_plan_id": source_plan_id,
        "source_execution_plan_digest": plan_digest,
        "execution_plan_digest": plan_digest,
        "v191_plan_derived_client_order_id": deterministic_client_order_id(plan),
        "preview_decision": _preview_decision(plan, packet_source),
        "approval_mode": approval["approval_mode"],
        "approval_granted": approval["approval_granted"],
        "approval_source": approval["approval_source"],
        "approval_fixture_only": approval["approval_source"] == OFFLINE_APPROVAL_SOURCE,
        "real_operator_authorization": False,
        "order_intent_created": bool(order_intent),
        "order_side": order_side,
        "quantity": quantity,
        "notional": notional,
        "quantity_or_notional_source": quantity_or_notional_source,
        "order_type": order_type,
        "time_in_force": time_in_force,
        "deterministic_client_order_id": client_order_id,
        "client_order_id": client_order_id,
        "oms_classification": classification,
        "outcome_classification": classification,
        "blocker": blocker,
        "next_operator_action": _next_operator_action(
            classification=classification,
            blocker=blocker,
            order_intent_created=bool(order_intent),
        ),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "real_broker_read_performed": False,
        "real_broker_mutation_performed": False,
        "broker_mutation_performed": False,
        "execution_mode": execution_mode,
        "broker_state_mode": broker_state_mode,
        "broker_state_source": (
            OFFLINE_APPROVAL_SOURCE
            if broker_state_mode == OFFLINE_FIXTURE_BROKER_STATE_MODE
            else "not_observed"
        ),
        "fake_submit_call_count": fake_submit_count,
        "fake_cancel_call_count": fake_cancel_count,
        "simulated_submit_performed": bool(oms_packet.get("simulated_submit_performed")),
        "simulated_broker_mutation_performed": bool(
            oms_packet.get("simulated_broker_mutation_performed")
        ),
        "safety_labels": list(V192_SAFETY_LABELS),
        "execution_plan": dict(plan),
        "approval_fixture": dict(approval),
        "order_intent": dict(order_intent),
        "paper_oms_request_shape": dict(order_intent),
        "broker_state_fixture": fixture.to_dict(),
        "oms_rehearsal": _oms_rehearsal_summary(oms_packet),
        "artifact_paths": {
            "operating_packet": str(root / "operating_packet.json"),
            "order_intent_packet": str(root / "order_intent_packet.json"),
            "operating_record": str(root / "operating_record.jsonl"),
            "operating_brief": str(root / "operating_brief.md"),
            "manifest": str(root / "manifest.jsonl"),
        },
    }


def _build_order_intent(
    *,
    run_id: str,
    packet_source: Mapping[str, Any],
    plan: Mapping[str, Any],
    plan_digest: str,
    client_order_id: str,
    approval: Mapping[str, Any],
    execution_mode: str,
    broker_state_mode: str,
    fixture: OfflineOmsFixture,
) -> dict[str, Any]:
    side = _side_from_action(str(plan.get("execution_plan_action", "")))
    if side == "buy":
        sizing = _buy_sizing()
    else:
        sizing = _sell_sizing(fixture)

    return {
        "order_intent_version": V192_ORDER_INTENT_VERSION,
        "run_id": run_id,
        "as_of_date": _source_value(packet_source, "as_of_date"),
        "symbol": "SPY",
        "asset_class": ASSET_CLASS_EQUITY,
        "source_execution_plan_id": str(plan.get("execution_plan_id", "")),
        "source_execution_plan_digest": plan_digest,
        "preview_decision": _preview_decision(plan, packet_source),
        "approval_mode": approval["approval_mode"],
        "approval_granted": approval["approval_granted"],
        "approval_source": approval["approval_source"],
        "real_operator_authorization": False,
        "side": side,
        "quantity": sizing["quantity"],
        "notional": sizing["notional"],
        "quantity_or_notional_source": sizing["quantity_or_notional_source"],
        "order_type": sizing["order_type"],
        "time_in_force": sizing["time_in_force"],
        "limit_price": sizing["limit_price"],
        "deterministic_client_order_id": client_order_id,
        "client_order_id": client_order_id,
        "oms_classification": "order_intent_created_fake_oms_rehearsal_pending",
        "blocker": "",
        "next_operator_action": "review_offline_order_intent_and_fake_oms_rehearsal",
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "real_broker_read_performed": False,
        "real_broker_mutation_performed": False,
        "execution_mode": execution_mode,
        "broker_state_mode": broker_state_mode,
        "safety_labels": list(V192_SAFETY_LABELS),
    }


def _buy_sizing() -> dict[str, str]:
    policy = paper_order_policy_for_asset_class(ASSET_CLASS_EQUITY)
    if policy.max_notional_cap is None:
        return _blocked_sizing()
    return {
        "quantity": "",
        "notional": _decimal_text(policy.max_notional_cap),
        "quantity_or_notional_source": (
            "paper_order_policy.equity.max_notional_cap"
        ),
        "order_type": "market",
        "time_in_force": policy.time_in_force,
        "limit_price": "",
    }


def _sell_sizing(fixture: OfflineOmsFixture) -> dict[str, str]:
    reference_price = _fixture_reference_price(fixture)
    if reference_price is None:
        return _blocked_sizing()
    limit_price = (reference_price * V189_NON_MARKETABLE_LIMIT_MULTIPLIER).quantize(
        Decimal("0.01"),
        rounding=ROUND_UP,
    )
    return {
        "quantity": _decimal_text(V189_MIN_FRACTIONAL_QTY),
        "notional": "",
        "quantity_or_notional_source": (
            "paper_mutation_oms.V189_MIN_FRACTIONAL_QTY"
        ),
        "order_type": "limit",
        "time_in_force": "day",
        "limit_price": _decimal_text(limit_price),
    }


def _blocked_sizing() -> dict[str, str]:
    return {
        "quantity": "",
        "notional": "",
        "quantity_or_notional_source": "blocked_order_intent_incomplete",
        "order_type": "",
        "time_in_force": "",
        "limit_price": "",
    }


def _extract_execution_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value.get("execution_plan"), Mapping):
        return dict(value["execution_plan"])
    if all(field in value for field in _REQUIRED_EXECUTION_PLAN_FIELDS):
        return dict(value)
    latest = value.get("latest_run")
    if isinstance(latest, Mapping) and isinstance(latest.get("execution_plan"), Mapping):
        return dict(latest["execution_plan"])
    raise ValueError("daily packet does not contain a serialized ExecutionPlan")


def _validate_execution_plan_shape(plan: Mapping[str, Any]) -> None:
    missing = [field for field in _REQUIRED_EXECUTION_PLAN_FIELDS if field not in plan]
    if missing:
        raise ValueError(f"ExecutionPlan is missing required fields: {', '.join(missing)}")


def _packet_source(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return value if not all(field in value for field in _REQUIRED_EXECUTION_PLAN_FIELDS) else {}


def _approval_payload(
    approval_fixture: OfflineOrderIntentApprovalFixture | None,
) -> dict[str, Any]:
    if approval_fixture is None:
        return {
            "approval_granted": False,
            "approval_mode": NO_APPROVAL_MODE,
            "approval_source": NO_APPROVAL_SOURCE,
            "broker_state_mode": "broker_state_not_observed",
            "real_operator_authorization": False,
            "paper_submit_authorized": False,
        }
    return approval_fixture.to_dict()


def _broker_state_mode(
    packet_source: Mapping[str, Any],
    approval_fixture: OfflineOrderIntentApprovalFixture | None,
) -> str:
    if approval_fixture is not None:
        return approval_fixture.broker_state_mode
    return (
        _source_value(packet_source, "broker_state_mode")
        or _source_value(packet_source, "broker_state_status")
        or "broker_state_not_observed"
    )


def _static_plan_blocker(
    plan: Mapping[str, Any],
    packet_source: Mapping[str, Any],
) -> str:
    if str(plan.get("execution_plan_symbol", "")).upper() != "SPY":
        return "blocked_symbol_not_allowlisted"
    unsafe_flags = (
        "execution_plan_broker_order_required",
        "execution_plan_submit_allowed",
        "execution_plan_paper_submit_authorized",
        "execution_plan_live_authorized",
        "execution_plan_broker_mutation_performed",
        "execution_plan_created_order_payload",
    )
    if any(plan.get(field) is not False for field in unsafe_flags):
        return "blocked_execution_plan_safety_flags_not_false"
    if _is_insufficient_history(plan, packet_source):
        return "insufficient_history"
    blocker = _normalized_plan_blocker(plan)
    if blocker != "none":
        return _blocker_classification(blocker)
    status = str(plan.get("execution_plan_status", "")).strip().lower()
    action = str(plan.get("execution_plan_action", "")).strip().lower()
    if status == "blocked" or action == "none":
        source_preview = _preview_decision(plan, packet_source)
        if source_preview.startswith("blocked/"):
            return _blocker_classification(source_preview.split("/", maxsplit=1)[1])
        return "blocked_upstream_execution_plan"
    return ""


def _is_insufficient_history(
    plan: Mapping[str, Any],
    packet_source: Mapping[str, Any],
) -> bool:
    fields = (
        plan.get("execution_plan_status"),
        plan.get("execution_plan_action"),
        plan.get("execution_plan_reason"),
        plan.get("execution_plan_blocker"),
        plan.get("execution_plan_source_preview_decision"),
        _source_value(packet_source, "preview_decision"),
        _source_value(packet_source, "main_blocker"),
    )
    return any(str(value or "").strip().lower() == "insufficient_history" for value in fields)


def _is_hold_noop_plan(plan: Mapping[str, Any]) -> bool:
    action = str(plan.get("execution_plan_action", "")).strip().lower()
    return action in HOLD_PLAN_ACTIONS


def _is_actionable_plan(plan: Mapping[str, Any]) -> bool:
    action = str(plan.get("execution_plan_action", "")).strip().lower()
    return (
        action in ACTIONABLE_PLAN_ACTIONS
        and plan.get("execution_plan_requires_approval") is True
    )


def _is_offline_fixture_approval(approval: Mapping[str, Any]) -> bool:
    return (
        approval.get("approval_mode") == OFFLINE_APPROVAL_MODE
        and approval.get("approval_source") == OFFLINE_APPROVAL_SOURCE
    )


def _offline_fixture_blocker(fixture: OfflineOmsFixture) -> str:
    unexpected_symbols = tuple(
        symbol
        for symbol in (_position_symbol(position) for position in fixture.positions)
        if symbol and symbol != "SPY"
    )
    if unexpected_symbols:
        return "blocked_unexpected_position"
    if tuple(fixture.open_orders):
        return "blocked_open_order_present"
    return ""


def _normalized_plan_blocker(plan: Mapping[str, Any]) -> str:
    blocker = str(plan.get("execution_plan_blocker", "") or "none").strip().lower()
    return blocker if blocker else "none"


def _blocker_classification(blocker: str) -> str:
    normalized = blocker.strip().lower().replace(" ", "_")
    if normalized in {"none", ""}:
        return ""
    if normalized == "insufficient_history":
        return "insufficient_history"
    if normalized in {"open_order_present", "open_spy_order_present"}:
        return "blocked_open_order_present"
    if normalized in {
        "unexpected_non_spy_position",
        "unexpected_position",
        "unexpected_position_present",
    }:
        return "blocked_unexpected_position"
    if normalized in {"broker_state_not_observed", "stale_broker_state"}:
        return "blocked_broker_state_not_observed"
    if normalized.startswith("blocked_"):
        return normalized
    return f"blocked_{normalized}"


def _side_from_action(action: str) -> str:
    normalized = action.strip().lower()
    if normalized == "buy_preview":
        return "buy"
    if normalized == "sell_preview":
        return "sell"
    return ""


def _preview_decision(
    plan: Mapping[str, Any],
    packet_source: Mapping[str, Any],
) -> str:
    return str(
        plan.get("execution_plan_source_preview_decision")
        or _source_value(packet_source, "preview_decision")
    )


def _fixture_reference_price(fixture: OfflineOmsFixture) -> Decimal | None:
    for position in fixture.positions:
        if _position_symbol(position) != "SPY":
            continue
        quantity = _decimal_or_zero(_mapping_get(position, "qty", "quantity"))
        market_value = _decimal_or_zero(_mapping_get(position, "market_value"))
        if quantity > 0 and market_value > 0:
            return (market_value / quantity).quantize(Decimal("0.0001"))
    return None


def _position_symbol(position: Mapping[str, Any]) -> str:
    return str(position.get("symbol", "")).strip().upper()


def _mapping_get(value: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in value:
            return value[name]
    return None


def _next_operator_action(
    *,
    classification: str,
    blocker: str,
    order_intent_created: bool,
) -> str:
    if classification == "approval_required":
        return "collect_explicit_operator_authorization_before_any_paper_submit"
    if classification == "not_submitted_hold_noop":
        return "record_noop_no_broker_action"
    if classification == "insufficient_history":
        return "collect_at_least_200_usable_as_of_bars_before_replanning"
    if blocker or classification.startswith("blocked_"):
        return "review_blocker_before_any_operator_authorization"
    if order_intent_created:
        return "review_offline_order_intent_and_fake_oms_rehearsal"
    return "review_offline_order_intent_adapter_packet"


def _oms_rehearsal_summary(oms_packet: Mapping[str, Any]) -> dict[str, Any]:
    if not oms_packet:
        return {}
    oms_latest = oms_packet.get("oms_latest", {})
    if not isinstance(oms_latest, Mapping):
        oms_latest = {}
    certification_plan = oms_latest.get("certification_plan", {})
    if not isinstance(certification_plan, Mapping):
        certification_plan = {}
    reconciliation = oms_latest.get("reconciliation", {})
    if not isinstance(reconciliation, Mapping):
        reconciliation = {}
    final_order = reconciliation.get("final_order", {})
    if not isinstance(final_order, Mapping):
        final_order = {}
    rehearsal_request = oms_packet.get("rehearsal_order_request", {})
    if not isinstance(rehearsal_request, Mapping):
        rehearsal_request = {}
    submitted_request = oms_packet.get("fake_submitted_request_fields", {})
    if not isinstance(submitted_request, Mapping):
        submitted_request = {}
    return {
        "packet_version": str(oms_packet.get("packet_version", "")),
        "run_id": str(oms_packet.get("run_id", "")),
        "oms_classification": str(oms_packet.get("oms_classification", "")),
        "symbol": str(oms_packet.get("symbol", "")),
        "side": _first_present_value(
            submitted_request,
            rehearsal_request,
            certification_plan,
            field="side",
        ),
        "order_type": _first_present_value(
            submitted_request,
            rehearsal_request,
            certification_plan,
            field="order_type",
        ),
        "time_in_force": _first_present_value(
            submitted_request,
            rehearsal_request,
            certification_plan,
            field="time_in_force",
        ),
        "quantity": _first_present_value(
            submitted_request,
            rehearsal_request,
            certification_plan,
            field="quantity",
        ),
        "notional": _first_present_value(
            submitted_request,
            rehearsal_request,
            certification_plan,
            field="notional",
        ),
        "limit_price": _first_present_value(
            submitted_request,
            rehearsal_request,
            certification_plan,
            field="limit_price",
        ),
        "final_order": dict(final_order),
        "rehearsal_order_request": dict(rehearsal_request),
        "fake_submitted_request_fields": dict(submitted_request),
        "deterministic_client_order_id": str(
            oms_packet.get("deterministic_client_order_id", "")
        ),
        "client_order_id": str(oms_packet.get("client_order_id", "")),
        "execution_mode": str(oms_packet.get("execution_mode", "")),
        "broker_state_mode": str(oms_packet.get("broker_state_mode", "")),
        "fake_submit_call_count": int(oms_packet.get("fake_submit_call_count") or 0),
        "fake_cancel_call_count": int(oms_packet.get("fake_cancel_call_count") or 0),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "real_broker_read_performed": False,
        "real_broker_mutation_performed": False,
        "artifact_paths": dict(oms_packet.get("artifact_paths", {})),
    }


def _first_present_value(
    *containers: Mapping[str, Any],
    field: str,
) -> str:
    for container in containers:
        if field in container and container[field] is not None:
            return str(container[field])
    return ""


def _write_artifacts(root: Path, packet: Mapping[str, Any]) -> None:
    _write_json(root / "operating_packet.json", packet)
    _write_json(root / "order_intent_packet.json", packet)
    (root / "operating_record.jsonl").write_text(
        json.dumps(_json_safe(packet), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "operating_brief.md").write_text(
        _render_operating_brief(packet),
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "manifest_version": V192_MANIFEST_VERSION,
        "run_id": packet["run_id"],
        "generated_at": packet["generated_at"],
        "execution_mode": packet["execution_mode"],
        "artifacts": {
            path.name: {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
            for path in (
                root / "operating_packet.json",
                root / "order_intent_packet.json",
                root / "operating_record.jsonl",
                root / "operating_brief.md",
            )
        },
    }
    (root / "manifest.jsonl").write_text(
        json.dumps(_json_safe(manifest), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _render_operating_brief(packet: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# v1.92 Order Intent Adapter",
            "",
            f"- Outcome: `{packet.get('oms_classification')}`",
            f"- Blocker: `{packet.get('blocker') or 'none'}`",
            f"- As-of date: `{packet.get('as_of_date')}`",
            f"- Symbol: `{packet.get('symbol')}`",
            f"- Preview decision: `{packet.get('preview_decision')}`",
            f"- Approval mode: `{packet.get('approval_mode')}`",
            f"- Approval granted: `{packet.get('approval_granted')}`",
            f"- Approval source: `{packet.get('approval_source')}`",
            f"- Order side: `{packet.get('order_side')}`",
            f"- Client order id: `{packet.get('client_order_id')}`",
            f"- Execution mode: `{packet.get('execution_mode')}`",
            f"- Broker-state mode: `{packet.get('broker_state_mode')}`",
            f"- Fake submit calls: `{packet.get('fake_submit_call_count')}`",
            f"- Fake cancel calls: `{packet.get('fake_cancel_call_count')}`",
            f"- Paper submit authorized: `{packet.get('paper_submit_authorized')}`",
            f"- Paper submit performed: `{packet.get('paper_submit_performed')}`",
            f"- Real broker read performed: `{packet.get('real_broker_read_performed')}`",
            f"- Real broker mutation performed: `{packet.get('real_broker_mutation_performed')}`",
            f"- Next operator action: `{packet.get('next_operator_action')}`",
            "",
            "Labels: "
            + ", ".join(str(label) for label in packet.get("safety_labels", [])),
            "",
        ]
    )


def _source_value(packet_source: Mapping[str, Any], key: str) -> str:
    value = packet_source.get(key)
    if value not in (None, ""):
        return str(value)
    for container_key in (
        "latest_run",
        "daily_decision_summary",
        "broker_state_lane",
        "broker_state",
        "executive_dashboard",
    ):
        container = packet_source.get(container_key)
        if isinstance(container, Mapping) and container.get(key) not in (None, ""):
            return str(container.get(key))
    return ""


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _decimal_or_zero(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _decimal_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(_decimal_or_zero(value))


def _utc_now_text() -> str:
    return datetime.now(tz=UTC).isoformat()


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
    "NO_APPROVAL_MODE",
    "NO_APPROVAL_SOURCE",
    "OFFLINE_APPROVAL_MODE",
    "OFFLINE_APPROVAL_SOURCE",
    "OfflineOrderIntentApprovalFixture",
    "V192_DEFAULT_OUTPUT_ROOT",
    "V192_ORDER_INTENT_VERSION",
    "V192_PACKET_VERSION",
    "V192_RUN_ID",
    "V192_SAFETY_LABELS",
    "deterministic_v192_client_order_id",
    "run_v192_order_intent_adapter",
    "run_v192_order_intent_adapter_from_path",
    "sample_v192_daily_execution_plan_packet",
]
