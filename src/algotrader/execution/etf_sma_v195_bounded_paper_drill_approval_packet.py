"""v1.95 bounded paper-drill approval packet, offline-only.

This module prepares a review artifact for a future separately authorized
bounded paper drill. It reuses the v1.93 order-intent review packet and never
loads broker configuration, constructs SDK clients, reads broker state, or sends
broker requests.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.execution.etf_sma_daily_oms_rehearsal import (
    OFFLINE_FIXTURE_BROKER_STATE_MODE,
    OFFLINE_OMS_REHEARSAL_MODE,
    OfflineOmsFixture,
    load_daily_execution_plan_packet,
)
from algotrader.execution.etf_sma_daily_order_intent_adapter import (
    OFFLINE_APPROVAL_SOURCE,
    OfflineOrderIntentApprovalFixture,
    sample_v192_daily_execution_plan_packet,
)
from algotrader.execution.etf_sma_daily_order_intent_review_packet import (
    REVIEW_BLOCKED_APPROVAL_REQUIRED,
    REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED,
    REVIEW_BLOCKED_INTENT_INCOMPLETE,
    REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH,
    REVIEW_BLOCKED_OPEN_ORDER_PRESENT,
    REVIEW_BLOCKED_UNEXPECTED_POSITION,
    REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION,
    REVIEW_READY_FAKE_ONLY,
    run_v193_order_intent_review_packet,
)

V195_RUN_ID = "v195_bounded_paper_drill_approval_packet"
V195_DEFAULT_OUTPUT_ROOT = (
    "runs/paper_lab/v195_bounded_paper_drill_approval_packet_smoke"
)
V195_PACKET_VERSION = "v195_bounded_paper_drill_approval_packet_v1"
V195_MANIFEST_VERSION = "v195_bounded_paper_drill_approval_packet_manifest_v1"
V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE = (
    "AUTHORIZE_V1_95_BOUNDED_SPY_PAPER_DRILL"
)

APPROVAL_PACKET_READY_NO_MUTATION = "approval_packet_ready_no_mutation"
APPROVAL_PACKET_BLOCKED_REVIEW_NOT_READY = (
    "approval_packet_blocked_review_not_ready"
)
APPROVAL_PACKET_BLOCKED_ORDER_INTENT_INCOMPLETE = (
    "approval_packet_blocked_order_intent_incomplete"
)
APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED = (
    "approval_packet_blocked_broker_state_required"
)
APPROVAL_PACKET_BLOCKED_UNRESOLVED_PRIOR_MUTATION = (
    "approval_packet_blocked_unresolved_prior_mutation"
)
APPROVAL_PACKET_BLOCKED_OPEN_ORDER_PRESENT = (
    "approval_packet_blocked_open_order_present"
)
APPROVAL_PACKET_BLOCKED_UNEXPECTED_POSITION = (
    "approval_packet_blocked_unexpected_position"
)
APPROVAL_PACKET_BLOCKED_MISSING_CAP = "approval_packet_blocked_missing_cap"
APPROVAL_PACKET_BLOCKED_MISMATCH = "approval_packet_blocked_mismatch"
APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED = (
    "approval_packet_blocked_authorization_not_requested"
)

V195_SAFETY_LABELS = (
    "paper_lab_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
    "paper_submit_authorized=false",
    "approval_packet_only",
    "no_broker_read_performed",
    "no_broker_mutation_performed",
)

_ORDER_INTENT_REQUIRED_FIELDS = (
    "symbol",
    "side",
    "quantity",
    "notional",
    "quantity_or_notional_source",
    "order_type",
    "time_in_force",
    "deterministic_client_order_id",
    "client_order_id",
)
_FALSE_SAFETY_FIELDS = (
    "broker_request_sent",
    "paper_submit_authorized",
    "paper_submit_performed",
    "real_broker_read_performed",
    "real_broker_mutation_performed",
    "broker_mutation_performed",
    "live_trading_authorized",
    "live_trading_performed",
    "real_broker_client_selected",
    "real_broker_client_instantiated",
)


@dataclass(frozen=True, slots=True)
class BoundedPaperDrillCap:
    """Explicit cap fixture for bounded approval-packet validation."""

    maximum_notional: str = ""
    maximum_quantity: str = ""
    cap_source: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "maximum_notional",
            _decimal_text(self.maximum_notional),
        )
        object.__setattr__(
            self,
            "maximum_quantity",
            _decimal_text(self.maximum_quantity),
        )
        object.__setattr__(self, "cap_source", str(self.cap_source).strip())

    def to_dict(self) -> dict[str, str]:
        return {
            "maximum_notional": self.maximum_notional,
            "maximum_quantity": self.maximum_quantity,
            "cap_source": self.cap_source,
        }


def run_v195_bounded_paper_drill_approval_packet(
    daily_packet_or_execution_plan: Mapping[str, Any],
    *,
    approval_fixture: OfflineOrderIntentApprovalFixture | None = None,
    oms_fixture: OfflineOmsFixture | None = None,
    output_root: Path | str = V195_DEFAULT_OUTPUT_ROOT,
    input_path: Path | str | None = None,
    run_id: str = V195_RUN_ID,
    cap: BoundedPaperDrillCap | None = None,
) -> dict[str, Any]:
    """Build the v1.95 approval packet from a local daily packet."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    review_packet = run_v193_order_intent_review_packet(
        daily_packet_or_execution_plan,
        approval_fixture=approval_fixture,
        oms_fixture=oms_fixture,
        output_root=root / "v193_order_intent_review_packet",
        input_path=input_path,
        run_id=f"{run_id}_v193_review",
    )
    return build_v195_bounded_paper_drill_approval_packet(
        review_packet,
        output_root=root,
        input_path=input_path,
        run_id=run_id,
        cap=cap,
    )


def run_v195_bounded_paper_drill_approval_packet_from_path(
    input_path: Path | str,
    *,
    approval_fixture: OfflineOrderIntentApprovalFixture | None = None,
    oms_fixture: OfflineOmsFixture | None = None,
    output_root: Path | str = V195_DEFAULT_OUTPUT_ROOT,
    run_id: str = V195_RUN_ID,
    cap: BoundedPaperDrillCap | None = None,
) -> dict[str, Any]:
    """Build the v1.95 approval packet from a local JSON packet path."""

    packet = load_daily_execution_plan_packet(input_path)
    return run_v195_bounded_paper_drill_approval_packet(
        packet,
        approval_fixture=approval_fixture,
        oms_fixture=oms_fixture,
        output_root=output_root,
        input_path=input_path,
        run_id=run_id,
        cap=cap,
    )


def build_v195_bounded_paper_drill_approval_packet(
    v193_review_packet: Mapping[str, Any],
    *,
    output_root: Path | str = V195_DEFAULT_OUTPUT_ROOT,
    input_path: Path | str | None = None,
    run_id: str = V195_RUN_ID,
    cap: BoundedPaperDrillCap | None = None,
) -> dict[str, Any]:
    """Reduce a v1.93/v1.94 fake-only review packet into an approval packet."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    review = dict(v193_review_packet)
    order_intent = _mapping(review.get("order_intent"))
    fake_oms_rehearsal = _mapping(review.get("fake_oms_rehearsal"))
    projected_fields = _projected_request_fields(review)
    resolved_cap = _resolve_cap(review, cap)
    validation = _validation_summary(
        review=review,
        order_intent=order_intent,
        cap=resolved_cap,
    )
    classification = _approval_packet_classification(review, validation)
    packet = _build_packet(
        root=root,
        input_path=input_path,
        run_id=run_id,
        review=review,
        order_intent=order_intent,
        fake_oms_rehearsal=fake_oms_rehearsal,
        projected_fields=projected_fields,
        cap=resolved_cap,
        validation=validation,
        classification=classification,
    )
    _write_artifacts(root, packet)
    return packet


def sample_v195_daily_execution_plan_packet(action: str = "buy_preview") -> dict[str, Any]:
    """Return a local SPY daily ExecutionPlan packet for v1.95 smoke/tests."""

    packet = sample_v192_daily_execution_plan_packet()
    normalized_action = str(action).strip() or "buy_preview"
    packet["broker_state_mode"] = OFFLINE_FIXTURE_BROKER_STATE_MODE
    packet["broker_state_source"] = OFFLINE_APPROVAL_SOURCE
    packet["preview_decision"] = normalized_action
    plan = packet["execution_plan"]
    plan["execution_plan_id"] = (
        f"daily_execution_plan_v195_{normalized_action.replace('/', '_')}"
    )
    plan["execution_plan_status"] = "preview_only"
    plan["execution_plan_action"] = normalized_action
    plan["execution_plan_source_preview_decision"] = normalized_action
    plan["execution_plan_requires_approval"] = True
    plan["execution_plan_blocker"] = "none"
    plan["execution_plan_reason"] = (
        f"{normalized_action}_requires_explicit_authorization"
    )
    return packet


def _build_packet(
    *,
    root: Path,
    input_path: Path | str | None,
    run_id: str,
    review: Mapping[str, Any],
    order_intent: Mapping[str, Any],
    fake_oms_rehearsal: Mapping[str, Any],
    projected_fields: Mapping[str, Any],
    cap: BoundedPaperDrillCap,
    validation: Mapping[str, Any],
    classification: str,
) -> dict[str, Any]:
    quantity = str(review.get("quantity", "") or order_intent.get("quantity", ""))
    notional = str(review.get("notional", "") or order_intent.get("notional", ""))
    sizing_kind = "notional" if notional else "quantity" if quantity else ""
    cap_kind = "notional" if cap.maximum_notional else "quantity" if cap.maximum_quantity else ""
    client_order_id = str(
        review.get("deterministic_client_order_id")
        or review.get("client_order_id")
        or order_intent.get("deterministic_client_order_id")
        or order_intent.get("client_order_id")
        or ""
    )
    proposed_action = _future_paper_action_candidate(
        review=review,
        projected_fields=projected_fields,
        cap=cap,
    )
    stop_conditions = _stop_condition_checklist(classification, validation)
    packet = {
        "packet_version": V195_PACKET_VERSION,
        "run_id": run_id,
        "created_at": _utc_now_text(),
        "generated_at": "",
        "input_daily_packet_or_execution_plan_path": (
            str(input_path) if input_path is not None else ""
        ),
        "as_of_date": str(review.get("as_of_date", "")),
        "symbol": str(review.get("symbol", "")),
        "source_execution_plan_id": str(review.get("source_execution_plan_id", "")),
        "source_execution_plan_digest": str(
            review.get("source_execution_plan_digest", "")
        ),
        "daily_posture_status": str(review.get("daily_posture_status", "")),
        "daily_execution_plan_status": str(
            review.get("daily_execution_plan_status", "")
        ),
        "preview_decision": str(review.get("preview_decision", "")),
        "upstream_blocker": _upstream_blocker_text(review),
        "broker_state_mode": str(review.get("broker_state_mode", "")),
        "order_side": str(review.get("order_side", "") or order_intent.get("side", "")),
        "quantity": quantity,
        "notional": notional,
        "notional_or_quantity": notional or quantity,
        "notional_or_quantity_kind": sizing_kind,
        "notional_quantity_source": str(
            review.get("notional_quantity_source")
            or review.get("quantity_or_notional_source")
            or order_intent.get("quantity_or_notional_source", "")
        ),
        "quantity_or_notional_source": str(
            review.get("quantity_or_notional_source")
            or order_intent.get("quantity_or_notional_source", "")
        ),
        "order_type": str(
            review.get("order_type", "") or order_intent.get("order_type", "")
        ),
        "time_in_force": str(
            review.get("time_in_force", "") or order_intent.get("time_in_force", "")
        ),
        "limit_price": str(
            review.get("limit_price", "") or order_intent.get("limit_price", "")
        ),
        "deterministic_client_order_id": client_order_id,
        "client_order_id": client_order_id,
        "maximum_notional_cap": cap.maximum_notional,
        "maximum_quantity_cap": cap.maximum_quantity,
        "maximum_notional_or_quantity_cap": cap.maximum_notional
        or cap.maximum_quantity,
        "maximum_notional_or_quantity_cap_kind": cap_kind,
        "maximum_notional_or_quantity_cap_source": cap.cap_source,
        "fake_oms_classification": str(review.get("fake_oms_classification", "")),
        "fake_submit_call_count": int(review.get("fake_submit_call_count") or 0),
        "fake_cancel_call_count": int(review.get("fake_cancel_call_count") or 0),
        "fake_submit_call_count_label": "simulated_fake_oms_only",
        "fake_cancel_call_count_label": "simulated_fake_oms_only",
        "operator_review_classification": str(
            review.get("final_review_classification")
            or review.get("outcome_classification")
            or ""
        ),
        "approval_packet_classification": classification,
        "outcome_classification": classification,
        "approval_packet_is_authorization": False,
        "approval_packet_statement": (
            "This offline approval packet is not authorization to read a broker, "
            "submit, cancel, replace, close, liquidate, or trade live."
        ),
        "not_authorization_statement": (
            "Not authorization: a future bounded paper drill requires the exact "
            "authorization phrase and fresh broker-state observation."
        ),
        "proposed_future_paper_action_fields": proposed_action,
        "future_paper_action_candidate": proposed_action,
        "future_paper_action_candidate_status": "projected_only_not_authorized",
        "projected_broker_request_fields": dict(projected_fields),
        "projected_broker_request_status": "projected_only_not_sent",
        "projected_broker_request_label": "projected_only",
        "projected_fields_are_projected_only": True,
        "broker_request_sent": False,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "real_broker_read_performed": False,
        "real_broker_mutation_performed": False,
        "broker_mutation_performed": False,
        "live_trading_authorized": False,
        "live_trading_performed": False,
        "real_broker_client_selected": False,
        "real_broker_client_instantiated": False,
        "future_broker_read_required": True,
        "future_paper_submit_requires_explicit_authorization": True,
        "future_authorization_phrase_required": True,
        "future_authorization_phrase_requested_now": False,
        "required_future_authorization_phrase": (
            V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE
        ),
        "expected_account_profile_endpoint_checks": (
            _expected_account_profile_endpoint_checks()
        ),
        "broker_state_prerequisites": _broker_state_prerequisites(),
        "duplicate_client_order_id_prevention_requirements": (
            _duplicate_client_order_id_requirements(client_order_id)
        ),
        "open_order_blocker_requirements": _open_order_blocker_requirements(),
        "unexpected_position_blocker_requirements": (
            _unexpected_position_blocker_requirements()
        ),
        "cancel_reconciliation_expectations": _cancel_reconciliation_expectations(),
        "stop_condition_checklist": stop_conditions,
        "stop_conditions_triggered_now": [
            name for name, item in stop_conditions.items() if item["triggered_now"]
        ],
        "hard_gate_checklist": _hard_gate_checklist(),
        "hard_gates_closed": True,
        "approval_packet_validation": dict(validation),
        "next_operator_action": _next_operator_action(classification),
        "safety_labels": list(V195_SAFETY_LABELS),
        "execution_mode": OFFLINE_OMS_REHEARSAL_MODE,
        "source_v193_order_intent_review_packet": dict(review),
        "order_intent": dict(order_intent),
        "fake_oms_rehearsal": dict(fake_oms_rehearsal),
        "artifact_paths": {
            "approval_packet": str(root / "approval_packet.json"),
            "operating_packet": str(root / "operating_packet.json"),
            "projected_paper_request": str(root / "projected_paper_request.json"),
            "operating_record": str(root / "operating_record.jsonl"),
            "operating_brief": str(root / "operating_brief.md"),
            "manifest": str(root / "manifest.jsonl"),
            "source_operator_review_packet": _source_review_artifact_path(review),
        },
    }
    packet["generated_at"] = packet["created_at"]
    return packet


def _approval_packet_classification(
    review: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> str:
    review_classification = str(
        review.get("final_review_classification")
        or review.get("outcome_classification")
        or ""
    )
    if review_classification == REVIEW_BLOCKED_APPROVAL_REQUIRED:
        return APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED
    if review_classification == REVIEW_BLOCKED_INTENT_INCOMPLETE:
        return APPROVAL_PACKET_BLOCKED_ORDER_INTENT_INCOMPLETE
    if review_classification == REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED:
        return APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED
    if review_classification == REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION:
        return APPROVAL_PACKET_BLOCKED_UNRESOLVED_PRIOR_MUTATION
    if review_classification == REVIEW_BLOCKED_OPEN_ORDER_PRESENT:
        return APPROVAL_PACKET_BLOCKED_OPEN_ORDER_PRESENT
    if review_classification == REVIEW_BLOCKED_UNEXPECTED_POSITION:
        return APPROVAL_PACKET_BLOCKED_UNEXPECTED_POSITION
    if review_classification == REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH:
        return APPROVAL_PACKET_BLOCKED_MISMATCH
    if review_classification != REVIEW_READY_FAKE_ONLY:
        return APPROVAL_PACKET_BLOCKED_REVIEW_NOT_READY
    if not validation["offline_approval_fixture_marked"]:
        return APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED
    if validation["upstream_blocker_present"]:
        return APPROVAL_PACKET_BLOCKED_REVIEW_NOT_READY
    if not validation["broker_state_fixture_mode"]:
        return APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED
    if not validation["order_intent_complete"]:
        return APPROVAL_PACKET_BLOCKED_ORDER_INTENT_INCOMPLETE
    if not validation["intent_rehearsal_match"]:
        return APPROVAL_PACKET_BLOCKED_MISMATCH
    if not validation["cap_present"]:
        return APPROVAL_PACKET_BLOCKED_MISSING_CAP
    if not validation["request_within_cap"]:
        return APPROVAL_PACKET_BLOCKED_MISMATCH
    return APPROVAL_PACKET_READY_NO_MUTATION


def _validation_summary(
    *,
    review: Mapping[str, Any],
    order_intent: Mapping[str, Any],
    cap: BoundedPaperDrillCap,
) -> dict[str, Any]:
    quantity = str(review.get("quantity", "") or order_intent.get("quantity", ""))
    notional = str(review.get("notional", "") or order_intent.get("notional", ""))
    intent_issues = list(review.get("intent_validation_issues") or ())
    missing_fields = _order_intent_missing_fields(order_intent)
    if missing_fields:
        intent_issues.extend(f"missing_{field}" for field in missing_fields)
    if not quantity and not notional:
        intent_issues.append("missing_quantity_or_notional")
    if quantity and notional:
        intent_issues.append("quantity_and_notional_both_present")
    if str(order_intent.get("client_order_id", "")) != str(
        order_intent.get("deterministic_client_order_id", "")
    ):
        intent_issues.append("client_order_id_not_deterministic_client_order_id")
    cap_present = bool(cap.maximum_notional or cap.maximum_quantity)
    request_within_cap = _request_within_cap(
        quantity=quantity,
        notional=notional,
        cap=cap,
    )
    return {
        "review_ready_fake_only": (
            str(review.get("final_review_classification", ""))
            == REVIEW_READY_FAKE_ONLY
        ),
        "approval_granted": bool(review.get("approval_granted")),
        "approval_fixture_only": bool(review.get("approval_fixture_only")),
        "approval_source": str(review.get("approval_source", "")),
        "offline_approval_fixture_marked": (
            bool(review.get("approval_granted"))
            and bool(review.get("approval_fixture_only"))
            and str(review.get("approval_source", "")) == OFFLINE_APPROVAL_SOURCE
        ),
        "upstream_blocker_present": _upstream_blocker_text(review) not in {"", "none"},
        "broker_state_fixture_mode": (
            str(review.get("broker_state_mode", ""))
            == OFFLINE_FIXTURE_BROKER_STATE_MODE
        ),
        "order_intent_complete": bool(order_intent) and not intent_issues,
        "order_intent_issues": sorted(set(str(item) for item in intent_issues if item)),
        "intent_rehearsal_match": bool(
            review.get("intent_rehearsal_consistency_passed")
        ),
        "cap_present": cap_present,
        "request_within_cap": request_within_cap,
    }


def _order_intent_missing_fields(order_intent: Mapping[str, Any]) -> tuple[str, ...]:
    if not order_intent:
        return _ORDER_INTENT_REQUIRED_FIELDS
    return tuple(field for field in _ORDER_INTENT_REQUIRED_FIELDS if field not in order_intent)


def _resolve_cap(
    review: Mapping[str, Any],
    cap: BoundedPaperDrillCap | None,
) -> BoundedPaperDrillCap:
    if cap is not None:
        return cap
    notional = str(review.get("notional", "")).strip()
    quantity = str(review.get("quantity", "")).strip()
    source = str(
        review.get("notional_quantity_source")
        or review.get("quantity_or_notional_source")
        or "reviewed_order_intent"
    )
    if notional:
        return BoundedPaperDrillCap(maximum_notional=notional, cap_source=source)
    if quantity:
        return BoundedPaperDrillCap(maximum_quantity=quantity, cap_source=source)
    return BoundedPaperDrillCap()


def _request_within_cap(
    *,
    quantity: str,
    notional: str,
    cap: BoundedPaperDrillCap,
) -> bool:
    if notional:
        return bool(
            cap.maximum_notional
            and _decimal_value(notional) is not None
            and _decimal_value(cap.maximum_notional) is not None
            and _decimal_value(notional) <= _decimal_value(cap.maximum_notional)
        )
    if quantity:
        return bool(
            cap.maximum_quantity
            and _decimal_value(quantity) is not None
            and _decimal_value(cap.maximum_quantity) is not None
            and _decimal_value(quantity) <= _decimal_value(cap.maximum_quantity)
        )
    return False


def _projected_request_fields(review: Mapping[str, Any]) -> dict[str, Any]:
    fields = review.get("projected_broker_request_fields")
    if isinstance(fields, Mapping):
        return dict(fields)
    order_intent = _mapping(review.get("order_intent"))
    if not order_intent:
        return {}
    projected: dict[str, Any] = {
        "asset_class": str(order_intent.get("asset_class", "equity")),
        "client_order_id": str(order_intent.get("client_order_id", "")),
        "symbol": str(order_intent.get("symbol", "")),
        "side": str(order_intent.get("side", "")),
        "order_type": str(order_intent.get("order_type", "")),
        "time_in_force": str(order_intent.get("time_in_force", "")),
    }
    quantity = str(order_intent.get("quantity", "")).strip()
    notional = str(order_intent.get("notional", "")).strip()
    limit_price = str(order_intent.get("limit_price", "")).strip()
    if quantity:
        projected["qty"] = quantity
    if notional:
        projected["notional"] = notional
    if limit_price:
        projected["limit_price"] = limit_price
    return projected


def _future_paper_action_candidate(
    *,
    review: Mapping[str, Any],
    projected_fields: Mapping[str, Any],
    cap: BoundedPaperDrillCap,
) -> dict[str, Any]:
    return {
        "candidate_status": "projected_only_not_authorized",
        "action_scope": "future_bounded_spy_paper_drill",
        "symbol": str(review.get("symbol", "")),
        "side": str(review.get("order_side", "")),
        "asset_class": str(projected_fields.get("asset_class", "equity")),
        "order_type": str(review.get("order_type", "")),
        "time_in_force": str(review.get("time_in_force", "")),
        "qty": str(projected_fields.get("qty", "")),
        "notional": str(projected_fields.get("notional", "")),
        "limit_price": str(projected_fields.get("limit_price", "")),
        "client_order_id": str(projected_fields.get("client_order_id", "")),
        "maximum_notional_cap": cap.maximum_notional,
        "maximum_quantity_cap": cap.maximum_quantity,
        "cap_source": cap.cap_source,
        "projected_only": True,
        "broker_request_sent": False,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
    }


def _hard_gate_checklist() -> dict[str, dict[str, Any]]:
    gates = {
        "future_explicit_authorization_phrase": {
            "closed": True,
            "required": True,
            "requested_now": False,
            "required_phrase": V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE,
        },
        "fresh_real_paper_broker_read": {
            "closed": True,
            "required": True,
            "performed_now": False,
        },
        "paper_submit_authorized": {"closed": True, "value": False},
        "paper_submit_performed": {"closed": True, "value": False},
        "broker_request_sent": {"closed": True, "value": False},
        "real_broker_mutation_performed": {"closed": True, "value": False},
        "live_trading_authorized": {"closed": True, "value": False},
        "live_trading_performed": {"closed": True, "value": False},
    }
    return gates


def _expected_account_profile_endpoint_checks() -> list[str]:
    return [
        "APP_PROFILE must be paper only inside a future scoped paper shell.",
        "Alpaca/APCA credentials may be loaded only inside that future shell and never printed.",
        "The broker endpoint must be the paper endpoint, not a live endpoint.",
        "Expected paper account identity must be freshly observed and matched if configured.",
        "Account trading_blocked/account_blocked status must be freshly observed.",
        "Buying power or cash sufficiency must be freshly observed for the bounded request.",
    ]


def _broker_state_prerequisites() -> dict[str, Any]:
    return {
        "future_broker_read_required": True,
        "required_observation_timing": "fresh_immediately_before_future_drill",
        "required_mode": "future_explicit_alpaca_paper_read_only_observation",
        "account_observation_required": True,
        "positions_observation_required": True,
        "open_orders_observation_required": True,
        "recent_client_order_id_observation_required": True,
        "broker_read_performed_in_this_packet": False,
    }


def _duplicate_client_order_id_requirements(client_order_id: str) -> list[str]:
    return [
        f"Freshly query paper orders for client_order_id={client_order_id}.",
        "Block the future drill if the deterministic client_order_id already exists.",
        "Do not alter the deterministic client_order_id after GPT/operator review.",
    ]


def _open_order_blocker_requirements() -> list[str]:
    return [
        "Freshly observe open paper orders before any future paper submit.",
        "Block if any SPY open order exists.",
        "Block if open-order state is unavailable or ambiguous.",
    ]


def _unexpected_position_blocker_requirements() -> list[str]:
    return [
        "Freshly observe all paper positions before any future paper submit.",
        "Block if any non-SPY position exists.",
        "Block if position state is unavailable or ambiguous.",
    ]


def _cancel_reconciliation_expectations() -> list[str]:
    return [
        "This packet authorizes no cancel action.",
        "A future submit drill must define post-submit read-only reconciliation.",
        "Any future cancel requires separate explicit operator authorization.",
        "Ambiguous submit, cancel, order, or reconciliation state blocks the drill.",
    ]


def _stop_condition_checklist(
    classification: str,
    validation: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    triggered = {
        "review_packet_not_ready": classification
        == APPROVAL_PACKET_BLOCKED_REVIEW_NOT_READY,
        "authorization_not_requested": classification
        == APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED,
        "order_intent_incomplete": classification
        == APPROVAL_PACKET_BLOCKED_ORDER_INTENT_INCOMPLETE,
        "broker_state_required": classification
        == APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED,
        "unresolved_prior_mutation": classification
        == APPROVAL_PACKET_BLOCKED_UNRESOLVED_PRIOR_MUTATION,
        "existing_spy_open_order": classification
        == APPROVAL_PACKET_BLOCKED_OPEN_ORDER_PRESENT,
        "unexpected_non_spy_position": classification
        == APPROVAL_PACKET_BLOCKED_UNEXPECTED_POSITION,
        "missing_cap": classification == APPROVAL_PACKET_BLOCKED_MISSING_CAP,
        "intent_rehearsal_mismatch": classification
        == APPROVAL_PACKET_BLOCKED_MISMATCH,
        "future_authorization_phrase_missing_or_mismatch": True,
        "future_fresh_broker_state_not_observed": True,
        "paper_submit_authorized_now": False,
        "real_broker_read_performed_now": False,
        "real_broker_mutation_performed_now": False,
        "live_trading_authorized_now": False,
    }
    return {
        name: {
            "would_block_future_drill": True,
            "triggered_now": bool(value),
            "detail": _stop_condition_detail(name, validation),
        }
        for name, value in triggered.items()
    }


def _stop_condition_detail(name: str, validation: Mapping[str, Any]) -> str:
    details = {
        "review_packet_not_ready": "The fake-only review packet must be review_ready_fake_only.",
        "authorization_not_requested": "Offline approval fixture or future exact phrase is missing.",
        "order_intent_incomplete": ",".join(validation.get("order_intent_issues", [])),
        "broker_state_required": "Fresh real paper broker state is required before a future drill.",
        "unresolved_prior_mutation": "Prior fake/paper mutation outcome must be resolved first.",
        "existing_spy_open_order": "No SPY open order may exist before a future drill.",
        "unexpected_non_spy_position": "No non-SPY position may exist before a future drill.",
        "missing_cap": "A maximum notional or quantity cap is required.",
        "intent_rehearsal_mismatch": "Order intent and fake OMS rehearsal must match.",
        "future_authorization_phrase_missing_or_mismatch": (
            "Future operator phrase has not been requested in this milestone."
        ),
        "future_fresh_broker_state_not_observed": (
            "No real broker read is performed in this milestone."
        ),
        "paper_submit_authorized_now": "Paper submit must remain false now.",
        "real_broker_read_performed_now": "Real broker read must remain false now.",
        "real_broker_mutation_performed_now": "Real broker mutation must remain false now.",
        "live_trading_authorized_now": "Live trading must remain false now.",
    }
    return details.get(name, "")


def _next_operator_action(classification: str) -> str:
    if classification == APPROVAL_PACKET_READY_NO_MUTATION:
        return "gpt_operator_review_packet_before_future_separately_authorized_paper_drill"
    if classification == APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED:
        return "repair_fake_review_approval_fixture_before_future_packet_review"
    if classification == APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED:
        return "provide_explicit_offline_fixture_or_stop_before_future_packet_review"
    if classification in {
        APPROVAL_PACKET_BLOCKED_OPEN_ORDER_PRESENT,
        APPROVAL_PACKET_BLOCKED_UNEXPECTED_POSITION,
        APPROVAL_PACKET_BLOCKED_UNRESOLVED_PRIOR_MUTATION,
    }:
        return "resolve_source_review_state_before_future_paper_drill_review"
    if classification == APPROVAL_PACKET_BLOCKED_MISSING_CAP:
        return "define_bounded_notional_or_quantity_cap_before_review"
    return "repair_order_intent_review_packet_before_future_paper_drill_review"


def _source_review_artifact_path(review: Mapping[str, Any]) -> str:
    artifact_paths = review.get("artifact_paths")
    if isinstance(artifact_paths, Mapping):
        return str(artifact_paths.get("operator_review_packet", ""))
    return ""


def _upstream_blocker_text(review: Mapping[str, Any]) -> str:
    return str(review.get("upstream_blocker", "") or "none").strip() or "none"


def _write_artifacts(root: Path, packet: Mapping[str, Any]) -> None:
    _write_json(root / "approval_packet.json", packet)
    _write_json(root / "operating_packet.json", packet)
    _write_json(
        root / "projected_paper_request.json",
        {
            "projected_broker_request_status": packet[
                "projected_broker_request_status"
            ],
            "projected_broker_request_label": packet["projected_broker_request_label"],
            "broker_request_sent": False,
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "projected_broker_request_fields": packet[
                "projected_broker_request_fields"
            ],
            "proposed_future_paper_action_fields": packet[
                "proposed_future_paper_action_fields"
            ],
        },
    )
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
    artifact_paths = (
        root / "approval_packet.json",
        root / "operating_packet.json",
        root / "projected_paper_request.json",
        root / "operating_record.jsonl",
        root / "operating_brief.md",
    )
    manifest = {
        "manifest_version": V195_MANIFEST_VERSION,
        "run_id": packet["run_id"],
        "generated_at": packet["generated_at"],
        "execution_mode": OFFLINE_OMS_REHEARSAL_MODE,
        "artifacts": {
            path.name: {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
            for path in artifact_paths
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
            "# v1.95 Bounded Paper Drill Approval Packet",
            "",
            f"- Approval packet classification: `{packet.get('approval_packet_classification')}`",
            f"- Operator review classification: `{packet.get('operator_review_classification')}`",
            f"- Approval packet is authorization: `{packet.get('approval_packet_is_authorization')}`",
            f"- As-of date: `{packet.get('as_of_date')}`",
            f"- Symbol: `{packet.get('symbol')}`",
            f"- Source ExecutionPlan: `{packet.get('source_execution_plan_id')}`",
            f"- ExecutionPlan digest: `{packet.get('source_execution_plan_digest')}`",
            f"- Preview decision: `{packet.get('preview_decision')}`",
            f"- Broker-state mode: `{packet.get('broker_state_mode')}`",
            f"- Order side: `{packet.get('order_side')}`",
            f"- Quantity: `{packet.get('quantity')}`",
            f"- Notional: `{packet.get('notional')}`",
            f"- Cap: `{packet.get('maximum_notional_or_quantity_cap')}`",
            f"- Client order id: `{packet.get('client_order_id')}`",
            f"- Fake OMS classification: `{packet.get('fake_oms_classification')}`",
            f"- Projected request status: `{packet.get('projected_broker_request_status')}`",
            f"- Broker request sent: `{packet.get('broker_request_sent')}`",
            f"- Paper submit authorized: `{packet.get('paper_submit_authorized')}`",
            f"- Paper submit performed: `{packet.get('paper_submit_performed')}`",
            f"- Real broker read performed: `{packet.get('real_broker_read_performed')}`",
            f"- Real broker mutation performed: `{packet.get('real_broker_mutation_performed')}`",
            f"- Future broker read required: `{packet.get('future_broker_read_required')}`",
            f"- Required future authorization phrase: `{packet.get('required_future_authorization_phrase')}`",
            f"- Next operator action: `{packet.get('next_operator_action')}`",
            "",
            "Labels: "
            + ", ".join(str(label) for label in packet.get("safety_labels", [])),
            "",
            str(packet.get("approval_packet_statement", "")),
            "",
        ]
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _decimal_value(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_text(value: Any) -> str:
    parsed = _decimal_value(value)
    return "" if parsed is None else str(parsed)


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
    "APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED",
    "APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED",
    "APPROVAL_PACKET_BLOCKED_MISMATCH",
    "APPROVAL_PACKET_BLOCKED_MISSING_CAP",
    "APPROVAL_PACKET_BLOCKED_OPEN_ORDER_PRESENT",
    "APPROVAL_PACKET_BLOCKED_ORDER_INTENT_INCOMPLETE",
    "APPROVAL_PACKET_BLOCKED_REVIEW_NOT_READY",
    "APPROVAL_PACKET_BLOCKED_UNEXPECTED_POSITION",
    "APPROVAL_PACKET_BLOCKED_UNRESOLVED_PRIOR_MUTATION",
    "APPROVAL_PACKET_READY_NO_MUTATION",
    "BoundedPaperDrillCap",
    "V195_DEFAULT_OUTPUT_ROOT",
    "V195_PACKET_VERSION",
    "V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE",
    "V195_RUN_ID",
    "V195_SAFETY_LABELS",
    "build_v195_bounded_paper_drill_approval_packet",
    "run_v195_bounded_paper_drill_approval_packet",
    "run_v195_bounded_paper_drill_approval_packet_from_path",
    "sample_v195_daily_execution_plan_packet",
]
