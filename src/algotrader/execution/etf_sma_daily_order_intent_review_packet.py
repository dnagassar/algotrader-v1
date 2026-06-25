"""v1.93 operator review packet for order intent vs fake OMS rehearsal.

This module is offline-only. It composes the serialized daily ExecutionPlan,
the v1.92 order-intent adapter, and the v1.91 fake OMS rehearsal summary into
one pre-submit review artifact. It does not create real broker clients or send
broker requests.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
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
    run_v192_order_intent_adapter,
)

V193_RUN_ID = "v193_order_intent_review_packet"
V193_DEFAULT_OUTPUT_ROOT = "runs/paper_lab/v193_order_intent_review_packet_smoke"
V193_PACKET_VERSION = "v193_order_intent_review_packet_v1"
V193_MANIFEST_VERSION = "v193_order_intent_review_packet_manifest_v1"
V193_SAFETY_LABELS = (
    "paper_lab_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
    "paper_submit_authorized=false",
)

REVIEW_READY_FAKE_ONLY = "review_ready_fake_only"
REVIEW_BLOCKED_APPROVAL_REQUIRED = "review_blocked_approval_required"
REVIEW_BLOCKED_UPSTREAM_BLOCKER = "review_blocked_upstream_blocker"
REVIEW_BLOCKED_INSUFFICIENT_HISTORY = "review_blocked_insufficient_history"
REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED = "review_blocked_broker_state_unobserved"
REVIEW_BLOCKED_INTENT_INCOMPLETE = "review_blocked_intent_incomplete"
REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH = (
    "review_blocked_intent_rehearsal_mismatch"
)
REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION = (
    "review_blocked_unresolved_prior_mutation"
)
REVIEW_BLOCKED_OPEN_ORDER_PRESENT = "review_blocked_open_order_present"
REVIEW_BLOCKED_UNEXPECTED_POSITION = "review_blocked_unexpected_position"

_READY_FAKE_OMS_CLASSIFICATIONS = frozenset(
    {
        "submitted_cancel_confirmed",
        "submitted_then_rejected",
        "submitted_partial_fill_then_cancelled",
        "submitted_filled_before_cancel",
        "ambiguous_submit_reconciled",
        "cancel_ambiguous_reconciled",
    }
)
_UNRESOLVED_PRIOR_CLASSIFICATIONS = frozenset(
    {
        "blocked_unresolved_prior_mutation",
        "unresolved_order_outcome",
        "ambiguous_submit_unresolved",
        "cancel_ambiguous_unresolved",
    }
)
_REQUIRED_ORDER_INTENT_FIELDS = (
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


def run_v193_order_intent_review_packet(
    daily_packet_or_execution_plan: Mapping[str, Any],
    *,
    approval_fixture: OfflineOrderIntentApprovalFixture | None = None,
    oms_fixture: OfflineOmsFixture | None = None,
    output_root: Path | str = V193_DEFAULT_OUTPUT_ROOT,
    input_path: Path | str | None = None,
    run_id: str = V193_RUN_ID,
) -> dict[str, Any]:
    """Run the offline order-intent review packet composition."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    adapter_packet = run_v192_order_intent_adapter(
        daily_packet_or_execution_plan,
        approval_fixture=approval_fixture,
        oms_fixture=oms_fixture,
        output_root=root / "v192_order_intent_adapter",
        input_path=input_path,
        run_id=f"{run_id}_v192_order_intent",
    )
    packet = build_v193_order_intent_review_packet(
        adapter_packet,
        daily_packet_or_execution_plan=daily_packet_or_execution_plan,
        output_root=root,
        input_path=input_path,
        run_id=run_id,
    )
    _write_artifacts(root, packet)
    return packet


def run_v193_order_intent_review_packet_from_path(
    input_path: Path | str,
    *,
    approval_fixture: OfflineOrderIntentApprovalFixture | None = None,
    oms_fixture: OfflineOmsFixture | None = None,
    output_root: Path | str = V193_DEFAULT_OUTPUT_ROOT,
    run_id: str = V193_RUN_ID,
) -> dict[str, Any]:
    packet = load_daily_execution_plan_packet(input_path)
    return run_v193_order_intent_review_packet(
        packet,
        approval_fixture=approval_fixture,
        oms_fixture=oms_fixture,
        output_root=output_root,
        input_path=input_path,
        run_id=run_id,
    )


def build_v193_order_intent_review_packet(
    v192_order_intent_packet: Mapping[str, Any],
    *,
    daily_packet_or_execution_plan: Mapping[str, Any] | None = None,
    output_root: Path | str = V193_DEFAULT_OUTPUT_ROOT,
    input_path: Path | str | None = None,
    run_id: str = V193_RUN_ID,
) -> dict[str, Any]:
    """Build a deterministic review packet from an existing v1.92 packet."""

    root = Path(output_root)
    plan = _mapping(v192_order_intent_packet.get("execution_plan"))
    order_intent = _mapping(v192_order_intent_packet.get("order_intent"))
    oms_rehearsal = _mapping(v192_order_intent_packet.get("oms_rehearsal"))
    source = daily_packet_or_execution_plan or {}
    approval_granted = bool(v192_order_intent_packet.get("approval_granted"))
    approval_source = str(v192_order_intent_packet.get("approval_source", ""))
    approval_mode = str(v192_order_intent_packet.get("approval_mode", ""))
    broker_state_mode = str(v192_order_intent_packet.get("broker_state_mode", ""))
    source_classification = str(
        v192_order_intent_packet.get("oms_classification")
        or v192_order_intent_packet.get("outcome_classification")
        or ""
    )
    source_blocker = str(v192_order_intent_packet.get("blocker") or "")
    intent_issues = _order_intent_issues(order_intent)
    consistency_checks = _intent_rehearsal_consistency_checks(
        order_intent,
        oms_rehearsal,
    )
    final_classification = _review_classification(
        plan=plan,
        source_classification=source_classification,
        source_blocker=source_blocker,
        broker_state_mode=broker_state_mode,
        approval_granted=approval_granted,
        approval_source=approval_source,
        order_intent=order_intent,
        intent_issues=intent_issues,
        consistency_checks=consistency_checks,
    )
    projected_request = _projected_broker_request_fields(order_intent)
    hard_gates = _hard_gate_checklist()
    plan_digest = str(
        v192_order_intent_packet.get("source_execution_plan_digest")
        or v192_order_intent_packet.get("execution_plan_digest")
        or order_intent.get("source_execution_plan_digest", "")
    )
    client_order_id = str(
        order_intent.get("deterministic_client_order_id")
        or v192_order_intent_packet.get("deterministic_client_order_id")
        or v192_order_intent_packet.get("client_order_id", "")
    )
    quantity = str(order_intent.get("quantity", ""))
    notional = str(order_intent.get("notional", ""))
    sizing_kind = "notional" if notional else "quantity" if quantity else ""
    return {
        "packet_version": V193_PACKET_VERSION,
        "run_id": run_id,
        "generated_at": _utc_now_text(),
        "input_daily_packet_or_execution_plan_path": (
            str(input_path) if input_path is not None else ""
        ),
        "as_of_date": str(v192_order_intent_packet.get("as_of_date", ""))
        or _source_value(source, "as_of_date"),
        "symbol": str(v192_order_intent_packet.get("symbol", ""))
        or str(plan.get("execution_plan_symbol", "")),
        "source_execution_plan_id": str(
            v192_order_intent_packet.get("source_execution_plan_id")
            or v192_order_intent_packet.get("execution_plan_id")
            or plan.get("execution_plan_id", "")
        ),
        "source_execution_plan_digest": plan_digest,
        "daily_posture_status": _daily_posture_status(source, plan),
        "daily_execution_plan_status": str(plan.get("execution_plan_status", "")),
        "preview_decision": str(v192_order_intent_packet.get("preview_decision", "")),
        "upstream_blocker": _upstream_blocker(plan, source_blocker),
        "broker_state_mode": broker_state_mode,
        "approval_mode": approval_mode,
        "approval_source": approval_source,
        "approval_granted": approval_granted,
        "approval_fixture_only": approval_source == OFFLINE_APPROVAL_SOURCE,
        "approval_statement": _approval_statement(approval_granted, approval_source),
        "real_operator_authorization": False,
        "order_intent_created": bool(order_intent),
        "order_side": str(order_intent.get("side", "")),
        "quantity": quantity,
        "notional": notional,
        "notional_or_quantity": notional or quantity,
        "notional_or_quantity_kind": sizing_kind,
        "notional_quantity_source": str(
            order_intent.get("quantity_or_notional_source", "")
        ),
        "quantity_or_notional_source": str(
            order_intent.get("quantity_or_notional_source", "")
        ),
        "order_type": str(order_intent.get("order_type", "")),
        "time_in_force": str(order_intent.get("time_in_force", "")),
        "limit_price": str(order_intent.get("limit_price", "")),
        "deterministic_client_order_id": client_order_id,
        "client_order_id": client_order_id,
        "projected_broker_request_fields": projected_request,
        "projected_broker_request_status": "projected_only_not_sent",
        "broker_request_sent": False,
        "broker_request_sent_statement": (
            "No broker request was sent; fields are projected for review only."
        ),
        "no_broker_request_sent_statement": (
            "No broker request was sent during this offline review packet run."
        ),
        "fake_oms_classification": source_classification,
        "fake_submit_call_count": int(
            v192_order_intent_packet.get("fake_submit_call_count") or 0
        ),
        "fake_cancel_call_count": int(
            v192_order_intent_packet.get("fake_cancel_call_count") or 0
        ),
        "fake_submit_call_count_label": "simulated_fake_oms_only",
        "fake_cancel_call_count_label": "simulated_fake_oms_only",
        "intent_validation_issues": intent_issues,
        "intent_rehearsal_consistency_checks": consistency_checks,
        "intent_rehearsal_consistency_passed": _checks_passed(consistency_checks),
        "hard_gate_checklist": hard_gates,
        "hard_gates_closed": all(item["closed"] for item in hard_gates.values()),
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "real_broker_read_performed": False,
        "real_broker_mutation_performed": False,
        "broker_mutation_performed": False,
        "live_trading_authorized": False,
        "live_trading_performed": False,
        "real_broker_client_selected": False,
        "real_broker_client_instantiated": False,
        "final_review_classification": final_classification,
        "outcome_classification": final_classification,
        "next_operator_action": _next_operator_action(final_classification),
        "safety_labels": list(V193_SAFETY_LABELS),
        "execution_mode": OFFLINE_OMS_REHEARSAL_MODE,
        "source_v192_order_intent_packet": dict(v192_order_intent_packet),
        "order_intent": dict(order_intent),
        "fake_oms_rehearsal": dict(oms_rehearsal),
        "artifact_paths": {
            "operator_review_packet": str(root / "operator_review_packet.json"),
            "operating_packet": str(root / "operating_packet.json"),
            "projected_broker_request": str(root / "projected_broker_request.json"),
            "operating_record": str(root / "operating_record.jsonl"),
            "operating_brief": str(root / "operating_brief.md"),
            "manifest": str(root / "manifest.jsonl"),
        },
    }


def _review_classification(
    *,
    plan: Mapping[str, Any],
    source_classification: str,
    source_blocker: str,
    broker_state_mode: str,
    approval_granted: bool,
    approval_source: str,
    order_intent: Mapping[str, Any],
    intent_issues: list[str],
    consistency_checks: Mapping[str, Mapping[str, Any]],
) -> str:
    normalized_blocker = _normalized(_upstream_blocker(plan, source_blocker))
    normalized_source = _normalized(source_classification)
    if normalized_source == "insufficient_history" or normalized_blocker == (
        "insufficient_history"
    ):
        return REVIEW_BLOCKED_INSUFFICIENT_HISTORY
    if normalized_source in _UNRESOLVED_PRIOR_CLASSIFICATIONS:
        return REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION
    if normalized_source == "blocked_open_order_present":
        return REVIEW_BLOCKED_OPEN_ORDER_PRESENT
    if normalized_source == "blocked_unexpected_position":
        return REVIEW_BLOCKED_UNEXPECTED_POSITION
    if broker_state_mode != OFFLINE_FIXTURE_BROKER_STATE_MODE or normalized_source in {
        "blocked_broker_state_not_observed",
        "blocked_broker_state_unobserved",
    }:
        return REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED
    if (
        normalized_source == "approval_required"
        or normalized_blocker == "approval_required"
        or approval_granted is not True
        or approval_source != OFFLINE_APPROVAL_SOURCE
    ):
        return REVIEW_BLOCKED_APPROVAL_REQUIRED
    if _has_upstream_blocker(plan, normalized_blocker, normalized_source):
        return REVIEW_BLOCKED_UPSTREAM_BLOCKER
    if not order_intent or intent_issues:
        return REVIEW_BLOCKED_INTENT_INCOMPLETE
    if not _checks_passed(consistency_checks):
        return REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH
    if normalized_source in _READY_FAKE_OMS_CLASSIFICATIONS:
        return REVIEW_READY_FAKE_ONLY
    if normalized_source.startswith("blocked_") or source_blocker:
        return REVIEW_BLOCKED_UPSTREAM_BLOCKER
    return REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH


def _order_intent_issues(order_intent: Mapping[str, Any]) -> list[str]:
    if not order_intent:
        return ["order_intent_missing"]
    issues = [
        f"missing_{field}"
        for field in _REQUIRED_ORDER_INTENT_FIELDS
        if field not in order_intent
    ]
    side = str(order_intent.get("side", "")).strip().lower()
    quantity = str(order_intent.get("quantity", "")).strip()
    notional = str(order_intent.get("notional", "")).strip()
    if side not in {"buy", "sell"}:
        issues.append("invalid_or_missing_side")
    if not quantity and not notional:
        issues.append("missing_quantity_or_notional")
    if quantity and notional:
        issues.append("quantity_and_notional_both_present")
    if not str(order_intent.get("order_type", "")).strip():
        issues.append("missing_order_type")
    if not str(order_intent.get("time_in_force", "")).strip():
        issues.append("missing_time_in_force")
    if str(order_intent.get("client_order_id", "")) != str(
        order_intent.get("deterministic_client_order_id", "")
    ):
        issues.append("client_order_id_not_deterministic_client_order_id")
    return sorted(set(issues))


def _intent_rehearsal_consistency_checks(
    order_intent: Mapping[str, Any],
    oms_rehearsal: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if not order_intent or not oms_rehearsal:
        return {}
    checks = {
        "symbol_matches": _check(
            str(order_intent.get("symbol", "")).upper(),
            str(oms_rehearsal.get("symbol", "")).upper(),
        ),
        "side_matches": _check(
            str(order_intent.get("side", "")).lower(),
            str(oms_rehearsal.get("side", "")).lower(),
        ),
        "deterministic_client_order_id_matches": _check(
            str(order_intent.get("deterministic_client_order_id", "")),
            str(
                oms_rehearsal.get("deterministic_client_order_id")
                or oms_rehearsal.get("client_order_id", "")
            ),
        ),
        "paper_submit_authorized_false_in_both": _check(False, False),
        "paper_submit_performed_false_in_both": _check(False, False),
        "real_broker_read_performed_false_in_both": _check(False, False),
        "real_broker_mutation_performed_false_in_both": _check(False, False),
    }
    checks["paper_submit_authorized_false_in_both"]["intent_value"] = bool(
        order_intent.get("paper_submit_authorized")
    )
    checks["paper_submit_authorized_false_in_both"]["rehearsal_value"] = bool(
        oms_rehearsal.get("paper_submit_authorized")
    )
    checks["paper_submit_authorized_false_in_both"]["passed"] = (
        checks["paper_submit_authorized_false_in_both"]["intent_value"] is False
        and checks["paper_submit_authorized_false_in_both"]["rehearsal_value"] is False
    )
    checks["paper_submit_performed_false_in_both"]["intent_value"] = bool(
        order_intent.get("paper_submit_performed")
    )
    checks["paper_submit_performed_false_in_both"]["rehearsal_value"] = bool(
        oms_rehearsal.get("paper_submit_performed")
    )
    checks["paper_submit_performed_false_in_both"]["passed"] = (
        checks["paper_submit_performed_false_in_both"]["intent_value"] is False
        and checks["paper_submit_performed_false_in_both"]["rehearsal_value"] is False
    )
    checks["real_broker_read_performed_false_in_both"]["intent_value"] = bool(
        order_intent.get("real_broker_read_performed")
    )
    checks["real_broker_read_performed_false_in_both"]["rehearsal_value"] = bool(
        oms_rehearsal.get("real_broker_read_performed")
    )
    checks["real_broker_read_performed_false_in_both"]["passed"] = (
        checks["real_broker_read_performed_false_in_both"]["intent_value"] is False
        and checks["real_broker_read_performed_false_in_both"]["rehearsal_value"]
        is False
    )
    checks["real_broker_mutation_performed_false_in_both"]["intent_value"] = bool(
        order_intent.get("real_broker_mutation_performed")
    )
    checks["real_broker_mutation_performed_false_in_both"]["rehearsal_value"] = bool(
        oms_rehearsal.get("real_broker_mutation_performed")
    )
    checks["real_broker_mutation_performed_false_in_both"]["passed"] = (
        checks["real_broker_mutation_performed_false_in_both"]["intent_value"]
        is False
        and checks["real_broker_mutation_performed_false_in_both"]["rehearsal_value"]
        is False
    )
    return checks


def _check(intent_value: Any, rehearsal_value: Any) -> dict[str, Any]:
    return {
        "passed": intent_value == rehearsal_value,
        "intent_value": intent_value,
        "rehearsal_value": rehearsal_value,
    }


def _projected_broker_request_fields(order_intent: Mapping[str, Any]) -> dict[str, Any]:
    if not order_intent:
        return {}
    fields: dict[str, Any] = {
        "client_order_id": str(order_intent.get("client_order_id", "")),
        "symbol": str(order_intent.get("symbol", "")),
        "side": str(order_intent.get("side", "")),
        "asset_class": str(order_intent.get("asset_class", "equity")),
        "order_type": str(order_intent.get("order_type", "")),
        "time_in_force": str(order_intent.get("time_in_force", "")),
    }
    quantity = str(order_intent.get("quantity", "")).strip()
    notional = str(order_intent.get("notional", "")).strip()
    limit_price = str(order_intent.get("limit_price", "")).strip()
    if quantity:
        fields["qty"] = quantity
    if notional:
        fields["notional"] = notional
    if limit_price:
        fields["limit_price"] = limit_price
    return fields


def _hard_gate_checklist() -> dict[str, dict[str, Any]]:
    gates = {
        "real_operator_authorization": False,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_request_sent": False,
        "real_broker_read_performed": False,
        "real_broker_mutation_performed": False,
        "live_trading_authorized": False,
        "live_trading_performed": False,
        "real_broker_client_selected": False,
        "real_broker_client_instantiated": False,
    }
    return {
        name: {"closed": value is False, "value": value}
        for name, value in gates.items()
    }


def _checks_passed(checks: Mapping[str, Mapping[str, Any]]) -> bool:
    return bool(checks) and all(bool(check.get("passed")) for check in checks.values())


def _has_upstream_blocker(
    plan: Mapping[str, Any],
    normalized_blocker: str,
    normalized_source: str,
) -> bool:
    status = _normalized(plan.get("execution_plan_status"))
    action = _normalized(plan.get("execution_plan_action"))
    if normalized_blocker not in {"", "none"}:
        return True
    return normalized_source.startswith("blocked_") or status == "blocked" or action == "none"


def _upstream_blocker(plan: Mapping[str, Any], source_blocker: str) -> str:
    plan_blocker = str(plan.get("execution_plan_blocker", "") or "none")
    if plan_blocker.strip().lower() != "none":
        return plan_blocker
    return source_blocker


def _daily_posture_status(
    source: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> str:
    return (
        _source_value(source, "sma_posture_status")
        or _source_value(source, "posture")
        or str(plan.get("execution_plan_status", ""))
    )


def _approval_statement(approval_granted: bool, approval_source: str) -> str:
    if approval_granted and approval_source == OFFLINE_APPROVAL_SOURCE:
        return "Offline approval fixture only; not real operator authorization."
    if not approval_granted:
        return "Approval is absent; no operator authorization is present."
    return "Approval source is not an accepted offline fixture."


def _next_operator_action(final_classification: str) -> str:
    if final_classification == REVIEW_READY_FAKE_ONLY:
        return "gpt_and_operator_review_before_separately_authorized_paper_drill"
    if final_classification == REVIEW_BLOCKED_APPROVAL_REQUIRED:
        return "collect_real_operator_authorization_before_any_future_paper_submit"
    if final_classification == REVIEW_BLOCKED_INSUFFICIENT_HISTORY:
        return "collect_at_least_200_usable_as_of_bars_before_replanning"
    if final_classification == REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED:
        return "provide_explicit_offline_broker_state_fixture_or_stop"
    if final_classification in {
        REVIEW_BLOCKED_OPEN_ORDER_PRESENT,
        REVIEW_BLOCKED_UNEXPECTED_POSITION,
        REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION,
    }:
        return "resolve_fixture_state_before_any_authorization_review"
    return "repair_review_packet_inputs_before_any_authorization_review"


def _write_artifacts(root: Path, packet: Mapping[str, Any]) -> None:
    _write_json(root / "operator_review_packet.json", packet)
    _write_json(root / "operating_packet.json", packet)
    _write_json(
        root / "projected_broker_request.json",
        {
            "projected_broker_request_status": packet[
                "projected_broker_request_status"
            ],
            "broker_request_sent": False,
            "broker_request_sent_statement": packet[
                "broker_request_sent_statement"
            ],
            "projected_broker_request_fields": packet[
                "projected_broker_request_fields"
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
        root / "operator_review_packet.json",
        root / "operating_packet.json",
        root / "projected_broker_request.json",
        root / "operating_record.jsonl",
        root / "operating_brief.md",
    )
    manifest = {
        "manifest_version": V193_MANIFEST_VERSION,
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
            "# v1.93 Order Intent Review Packet",
            "",
            f"- Final review classification: `{packet.get('final_review_classification')}`",
            f"- As-of date: `{packet.get('as_of_date')}`",
            f"- Symbol: `{packet.get('symbol')}`",
            f"- Source ExecutionPlan: `{packet.get('source_execution_plan_id')}`",
            f"- ExecutionPlan digest: `{packet.get('source_execution_plan_digest')}`",
            f"- Daily posture/status: `{packet.get('daily_posture_status')}`",
            f"- Preview decision: `{packet.get('preview_decision')}`",
            f"- Approval mode: `{packet.get('approval_mode')}`",
            f"- Approval source: `{packet.get('approval_source')}`",
            f"- Approval granted: `{packet.get('approval_granted')}`",
            f"- Real operator authorization: `{packet.get('real_operator_authorization')}`",
            f"- Order side: `{packet.get('order_side')}`",
            f"- Quantity: `{packet.get('quantity')}`",
            f"- Notional: `{packet.get('notional')}`",
            f"- Client order id: `{packet.get('client_order_id')}`",
            f"- Projected broker request status: `{packet.get('projected_broker_request_status')}`",
            f"- Broker request sent: `{packet.get('broker_request_sent')}`",
            f"- Fake OMS classification: `{packet.get('fake_oms_classification')}`",
            f"- Fake submit calls: `{packet.get('fake_submit_call_count')}`",
            f"- Fake cancel calls: `{packet.get('fake_cancel_call_count')}`",
            f"- Paper submit authorized: `{packet.get('paper_submit_authorized')}`",
            f"- Paper submit performed: `{packet.get('paper_submit_performed')}`",
            f"- Real broker read performed: `{packet.get('real_broker_read_performed')}`",
            f"- Real broker mutation performed: `{packet.get('real_broker_mutation_performed')}`",
            f"- Live trading authorized: `{packet.get('live_trading_authorized')}`",
            f"- Live trading performed: `{packet.get('live_trading_performed')}`",
            f"- Next operator action: `{packet.get('next_operator_action')}`",
            "",
            "Labels: "
            + ", ".join(str(label) for label in packet.get("safety_labels", [])),
            "",
        ]
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
    "REVIEW_BLOCKED_APPROVAL_REQUIRED",
    "REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED",
    "REVIEW_BLOCKED_INSUFFICIENT_HISTORY",
    "REVIEW_BLOCKED_INTENT_INCOMPLETE",
    "REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH",
    "REVIEW_BLOCKED_OPEN_ORDER_PRESENT",
    "REVIEW_BLOCKED_UNEXPECTED_POSITION",
    "REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION",
    "REVIEW_BLOCKED_UPSTREAM_BLOCKER",
    "REVIEW_READY_FAKE_ONLY",
    "V193_DEFAULT_OUTPUT_ROOT",
    "V193_PACKET_VERSION",
    "V193_RUN_ID",
    "V193_SAFETY_LABELS",
    "build_v193_order_intent_review_packet",
    "run_v193_order_intent_review_packet",
    "run_v193_order_intent_review_packet_from_path",
]
