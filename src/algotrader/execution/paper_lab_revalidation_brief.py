"""Read-only paper-lab run-log revalidation brief."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
import json
from json import JSONDecodeError
from pathlib import Path
import re
from typing import Any

from .paper_lab_observation_log import (
    EVENT_TYPES,
    PAPER_CLOSE_PREVIEW_DESIGNED,
    PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
    PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
    PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
    PAPER_LAB_SNAPSHOT_UNAVAILABLE,
    PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED,
    PAPER_ORDER_RECEIPT_OBSERVED,
    PAPER_ORDER_RESPONSE_PARSE_FAILED,
    PAPER_ORDER_SUBMIT_ATTEMPTED,
    PAPER_ORDER_SUBMIT_FAILED,
    PAPER_ORDER_SUBMIT_REQUESTED,
)
from .paper_order_policy import (
    PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON,
    build_btcusd_paper_close_preview_contract,
)


STATE_RECEIPT_AND_POSITION_OBSERVED = "receipt_and_position_observed"
STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP = (
    "receipt_and_position_observed_with_order_list_gap"
)
STATE_RECEIPT_OBSERVED_WITHOUT_POSITION = "receipt_observed_without_position"
STATE_POSITION_OBSERVED_WITHOUT_RECEIPT = "position_observed_without_receipt"
STATE_BROKER_REJECTED = "broker_rejected"
STATE_SUBMIT_FAILED_BEFORE_RESPONSE = "submit_failed_before_response"
STATE_USABLE_FOR_MANUAL_REVIEW = "usable_for_manual_review"
STATE_INSUFFICIENT_OBSERVATION = "insufficient_observation"
STATE_OBSERVATION_UNAVAILABLE = "observation_unavailable"
STATE_INVALID_RUN_LOG = "invalid_run_log"

_OBSERVATION_EVENT_TYPES = {
    "account": PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
    "positions": PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
    "orders": PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
}
_SAFE_ORDER_STATUS_FIELDS = (
    "order_id",
    "broker_order_id",
    "client_order_id",
    "symbol",
    "side",
    "notional",
    "quantity",
    "normalized_status",
    "raw_status",
    "asset_class",
    "order_type",
    "time_in_force",
    "submitted_at",
    "filled_at",
)
_REDACTION_MARKERS = ("credentials_redacted", "<redacted>")
_SECRET_TEXT_RE = re.compile(
    r"(api[_-]?key|secret|token|password|credential|authorization|bearer|https?://)",
    re.IGNORECASE,
)
_SAFE_CODE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
_SAFE_MONEY_RE = re.compile(r"^-?[0-9][0-9,]*(\.[0-9]+)?$")
_ACCEPTED_RECEIPT_STATUSES = frozenset(
    ("accepted", "new", "pending_new", "submitted", "partially_filled", "filled")
)
_REJECTED_RECEIPT_STATUSES = frozenset(("rejected",))
_RECENT_ORDER_QUERY_METADATA_FIELDS = (
    "recent_order_query_limit",
    "recent_order_query_status_filter",
    "recent_order_query_asset_class_filter",
    "recent_order_query_symbol_filter",
    "recent_order_query_side_filter",
    "recent_order_query_after",
    "recent_order_query_until",
    "recent_order_query_sort",
    "recent_order_query_direction",
    "recent_order_query_nested",
    "recent_order_query_source",
    "recent_order_query_contract_version",
)
_RECENT_ORDER_QUERY_REQUIRED_METADATA_FIELDS = (
    "recent_order_query_limit",
    "recent_order_query_status_filter",
    "recent_order_query_direction",
    "recent_order_query_nested",
    "recent_order_query_source",
    "recent_order_query_contract_version",
)
_ORDER_LIST_GAP_REASON_RECENT_ORDER_QUERY_RETURNED_EMPTY = (
    "recent_order_query_returned_empty"
)
_ORDER_LIST_GAP_REASON_TARGET_ORDER_NOT_IN_RECENT_ORDER_RESULTS = (
    "target_order_not_in_recent_order_results"
)
_ORDER_LIST_GAP_REASON_RECEIPT_MISSING_CORRELATION_ID = (
    "receipt_missing_correlation_id"
)
_ORDER_LIST_GAP_REASON_ORDER_QUERY_UNAVAILABLE = "order_query_unavailable"
_ORDER_LIST_GAP_REASON_INSUFFICIENT_ORDER_QUERY_METADATA = (
    "insufficient_order_query_metadata"
)
_ORDER_LIST_GAP_REASON_UNKNOWN = "unknown"
_RECONCILIATION_CONFIDENCE_HIGH_RECEIPT_POSITION_CASH_OBSERVED = (
    "high_receipt_position_cash_observed"
)
_RECONCILIATION_CONFIDENCE_MEDIUM_RECEIPT_POSITION_OBSERVED_ORDER_GAP = (
    "medium_receipt_position_observed_order_gap"
)
_RECONCILIATION_CONFIDENCE_LOW_RECEIPT_ONLY = "low_receipt_only"
_RECONCILIATION_CONFIDENCE_LOW_POSITION_ONLY = "low_position_only"
_RECONCILIATION_CONFIDENCE_UNAVAILABLE = "unavailable"
_RECONCILIATION_CONFIDENCE_INVALID = "invalid"
_RECONCILIATION_ACTION_MANUAL_REVIEW_ONLY = "read_only_manual_review_before_any_probe"
_RECONCILIATION_ACTION_FRESH_SNAPSHOT_BEFORE_CLOSE = (
    "read_only_fresh_snapshot_before_any_close_probe"
)
_RECONCILIATION_ACTION_COLLECT_READ_ONLY_OBSERVATIONS = (
    "collect_read_only_observations_before_any_probe"
)
_RECONCILIATION_ACTION_REPAIR_LOCAL_RUN_LOG = (
    "repair_local_run_log_before_revalidation"
)
_PAPER_CLOSE_POST_ACTION_RECONCILIATION_SCOPE = "paper_close_post_action"
_PAPER_CLOSE_POST_ACTION_STATE_ACCEPTED_ABSENT_NO_OPEN_ORDERS = (
    "accepted_close_response_position_absent_no_open_orders"
)
_PAPER_CLOSE_POST_ACTION_STATE_REQUIRES_MANUAL_REVIEW = "requires_manual_review"
_PAPER_CLOSE_POST_ACTION_CONFIDENCE_MEDIUM_POSITION_ABSENT = (
    "medium_position_absent_order_lifecycle_incomplete"
)
_PAPER_CLOSE_POST_ACTION_CONFIDENCE_UNAVAILABLE = "unavailable"
_PAPER_CLOSE_POST_ACTION_CONFIDENCE_MANUAL_REVIEW = "low_requires_manual_review"
_PAPER_CLOSE_POST_ACTION_NEXT_READ_ONLY_REVIEW = (
    "read_only_manual_review_no_corrective_order"
)
_PAPER_CLOSE_POST_ACTION_NEXT_COLLECT_READ_ONLY = (
    "collect_read_only_observations_before_any_further_action"
)
_PAPER_CLOSE_POST_ACTION_NEXT_MANUAL_REVIEW = (
    "manual_review_required_do_not_submit_corrective_order"
)
_PAPER_CLOSE_POST_ACTION_PRE_SUBMIT_LOG = "m331_pre_submit_snapshot.jsonl"
_PAPER_CLOSE_POST_ACTION_CLOSE_PROBE_LOG = "m331_btcusd_close_probe.jsonl"
_PAPER_CLOSE_POST_ACTION_POST_CLOSE_LOG = "m331_post_close_snapshot.jsonl"
CHECKLIST_STATUS_READY_FOR_READ_ONLY_SNAPSHOT = "ready_for_read_only_snapshot"
CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED = (
    "read_only_snapshot_completed_for_manual_review"
)
CHECKLIST_STATUS_BLOCKED_MISSING_PAPER_PROFILE = "blocked_missing_paper_profile"
CHECKLIST_STATUS_BLOCKED_MISSING_CREDENTIALS = "blocked_missing_credentials"
CHECKLIST_STATUS_BLOCKED_UNAVAILABLE_OBSERVATIONS = (
    "blocked_unavailable_observations"
)
CHECKLIST_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE = (
    "blocked_query_metadata_incomplete"
)
CHECKLIST_STATUS_BLOCKED_UNEXPECTED_MUTATION = "blocked_unexpected_mutation"
CHECKLIST_STATUS_BLOCKED_UNEXPECTED_SUBMIT = "blocked_unexpected_submit"
CHECKLIST_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE = "blocked_live_profile_evidence"
CHECKLIST_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE = (
    "blocked_credential_leak_evidence"
)
CHECKLIST_STATUS_INSUFFICIENT_OBSERVATION = "insufficient_observation"
_CHECKLIST_VERSION = "fresh_snapshot_operator_checklist_v1"
_CLOSE_ACTION_ELIGIBILITY_VERSION = "close_action_eligibility_checklist_v1"
_CLOSE_ACTION_STATUS_ELIGIBLE = "eligible_for_explicit_operator_approval"
_CLOSE_ACTION_STATUS_BLOCKED_MISSING_FRESH_SNAPSHOT = (
    "blocked_missing_fresh_snapshot"
)
_CLOSE_ACTION_STATUS_BLOCKED_MISSING_CLOSE_PREVIEW = (
    "blocked_missing_close_preview"
)
_CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_MUTATION = "blocked_unexpected_mutation"
_CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_SUBMIT = "blocked_unexpected_submit"
_CLOSE_ACTION_STATUS_BLOCKED_MISSING_POSITION = "blocked_missing_position"
_CLOSE_ACTION_STATUS_BLOCKED_INVALID_QUANTITY = "blocked_invalid_quantity"
_CLOSE_ACTION_STATUS_BLOCKED_NO_SHORTING_GATE_FAILED = (
    "blocked_no_shorting_gate_failed"
)
_CLOSE_ACTION_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE = (
    "blocked_query_metadata_incomplete"
)
_CLOSE_ACTION_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE = (
    "blocked_live_profile_evidence"
)
_CLOSE_ACTION_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE = (
    "blocked_credential_leak_evidence"
)
_CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION = "insufficient_observation"
_CLOSE_ACTION_NEXT_ELIGIBLE = (
    "prepare_explicit_paper_close_probe_prompt_but_do_not_submit"
)
_CLOSE_ACTION_NEXT_BLOCKED = (
    "collect_required_read_only_or_preview_evidence_before_close_probe"
)
_FUTURE_CLOSE_PROBE_PREPARATION_VERSION = "future_close_probe_preparation_v1"
_FUTURE_CLOSE_PROBE_NEXT_ELIGIBLE = (
    "draft_explicit_paper_close_probe_command_for_operator_review_only"
)
_FUTURE_CLOSE_PROBE_NEXT_BLOCKED = (
    "complete_m326_close_action_eligibility_evidence_before_prompt_generation"
)
_FUTURE_CLOSE_PROBE_TEMPLATE_SAFETY_NOTE = (
    "review_only_template_unsafe_to_run_until_separate_manual_authorization"
)
_FUTURE_CLOSE_PROBE_COMMAND_TEMPLATE = (
    "python -m algotrader paper-close-probe --run-log "
    "runs/paper_lab/<future_close_id>.jsonl --run-id <future_close_id> "
    "--symbol BTCUSD --quantity <required_position_quantity> "
    "<EXPLICIT_SUBMIT_FLAG_NOT_INCLUDED>"
)
_EXPLICIT_CLOSE_PROBE_PROMPT_REVIEW_VERSION = (
    "explicit_close_probe_prompt_review_v1"
)
_EXPLICIT_CLOSE_PROBE_REVIEW_NEXT_ELIGIBLE = (
    "review_explicit_paper_close_probe_prompt_and_decide_whether_to_authorize_separate_m329"
)
_EXPLICIT_CLOSE_PROBE_REVIEW_NEXT_BLOCKED = (
    "complete_future_close_probe_preparation_before_prompt_review"
)
_EXPLICIT_CLOSE_PROBE_REVIEW_SCOPE = (
    "btcusd_paper_close_probe_prompt_review_only_no_broker_action"
)
_EXPLICIT_CLOSE_PROBE_COMMAND_TEMPLATE = (
    "python -m algotrader paper-close-probe --asset-class crypto "
    "--symbol BTCUSD --side sell "
    "--quantity <OBSERVED_BTCUSD_POSITION_QUANTITY> "
    "--max-quantity <OBSERVED_BTCUSD_POSITION_QUANTITY> "
    "--run-log <FRESH_RUN_LOG> --run-id <FRESH_RUN_ID> --format json "
    "<EXPLICIT_SUBMIT_FLAG_NOT_INCLUDED>"
)
_CLOSE_ACTION_REQUIRED_OPERATOR_CONFIRMATIONS = (
    "I understand this is paper-only.",
    "I understand this is not live-authorized.",
    "I understand this may close the BTCUSD paper position.",
    "I understand the action must be manually triggered.",
    "I understand normal pytest must remain credential-free.",
    "I understand this does not imply profitability.",
)
_FRESH_SNAPSHOT_COMMAND_TEMPLATE = (
    "python -m algotrader paper-lab-snapshot --run-log "
    "runs/paper_lab/<fresh_id>.jsonl --run-id <fresh_id> --format json"
)
_CHECKLIST_ACTION_MANUAL_REVIEW_FRESH_SNAPSHOT = (
    "manual_review_fresh_snapshot_before_any_close_probe_design"
)
_CHECKLIST_ACTION_STOP_AND_REPAIR = "stop_and_repair_evidence_before_any_close_probe"
_PRE_RUN_CHECKLIST_ITEMS = (
    "use a separate paper-profile shell, not the normal pytest shell",
    "verify normal pytest shell remains credential-free",
    "set APP_PROFILE=paper only in the paper snapshot shell",
    "load paper-only Alpaca credentials only in the paper snapshot shell",
    "do not print credential values",
    "use a fresh run log path",
    "use a fresh run id",
    "run read-only paper-lab-snapshot only",
    "do not run paper-order-probe",
    "do not use --submit",
    "do not run any close/sell command",
)
_POST_RUN_CHECKLIST_ITEMS = (
    "profile_gate reports paper_profile_ready",
    "ok=true",
    "mutated=false",
    "submitted=false",
    "account_observation_available=true",
    "positions_observation_available=true",
    "orders_observation_available=true",
    "account cash/currency observed",
    "BTCUSD position presence or absence clearly reported",
    "BTCUSD quantity and average price reported if present",
    "recent_order_query_contract_version present",
    "recent_order_query_metadata_complete=true for new logs",
    "recent_order_query_returned_count recorded",
    "unavailable_observations empty",
    "redaction marker credentials_redacted present",
    "no live profile, live URL, token, key, or credential detail appears",
)
_MANUAL_REVIEW_USABLE_STATES = frozenset(
    (
        STATE_RECEIPT_AND_POSITION_OBSERVED,
        STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP,
        STATE_RECEIPT_OBSERVED_WITHOUT_POSITION,
        STATE_POSITION_OBSERVED_WITHOUT_RECEIPT,
        STATE_BROKER_REJECTED,
        STATE_SUBMIT_FAILED_BEFORE_RESPONSE,
        STATE_USABLE_FOR_MANUAL_REVIEW,
    )
)


def build_paper_lab_revalidation_brief(
    run_log_path: str | Path,
    *,
    run_id: str | None = None,
) -> dict[str, object]:
    """Summarize a local paper-lab JSONL run log without side effects."""

    records, invalid_reasons = _read_jsonl_records(run_log_path)
    run_ids = _run_ids(records)
    selected_run_id = _selected_run_id(records, run_id)
    selected_records = _selected_records(records, selected_run_id)

    if invalid_reasons:
        return _brief_payload(
            STATE_INVALID_RUN_LOG,
            records=records,
            selected_records=selected_records,
            selected_run_id=selected_run_id,
            run_ids=run_ids,
            invalid_reasons=invalid_reasons,
            run_log_path=run_log_path,
        )

    submit_observation = _submit_observation(records)
    observation_records = (
        records if submit_observation["has_submit_context"] else selected_records
    )
    unavailable_events = _unavailable_or_error_events(observation_records)
    missing_observations = _missing_observations(selected_records)
    if _has_observation_unavailable(unavailable_events):
        state = STATE_OBSERVATION_UNAVAILABLE
    elif submit_observation["has_submit_context"]:
        state = _submit_observation_state(submit_observation, missing_observations)
    elif missing_observations:
        state = STATE_INSUFFICIENT_OBSERVATION
    else:
        state = STATE_USABLE_FOR_MANUAL_REVIEW

    return _brief_payload(
        state,
        records=records,
        selected_records=selected_records,
        selected_run_id=selected_run_id,
        run_ids=run_ids,
        invalid_reasons=(),
        observation_records=observation_records,
        submit_observation=submit_observation,
        run_log_path=run_log_path,
    )


def render_paper_lab_revalidation_brief_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact deterministic text brief."""

    labels = _mapping(payload.get("advisory_labels"))
    observations = _mapping(payload.get("observations"))
    account = _mapping(payload.get("account"))
    positions = _mapping(payload.get("positions"))
    recent_orders = _mapping(payload.get("recent_orders"))
    submit_observation = _mapping(payload.get("submit_observation"))
    post_receipt_reconciliation = _mapping(
        payload.get("post_receipt_reconciliation")
    )
    paper_close_post_action_reconciliation = _mapping(
        payload.get("paper_close_post_action_reconciliation")
    )
    fresh_snapshot_checklist = _mapping(
        payload.get("fresh_snapshot_operator_checklist")
    )
    close_exit_probe_design = _mapping(payload.get("close_exit_probe_design"))
    close_action_eligibility = _mapping(
        payload.get("close_action_eligibility_checklist")
    )
    future_close_probe_preparation = _mapping(
        payload.get("future_close_probe_preparation")
    )
    explicit_close_probe_prompt_review = _mapping(
        payload.get("explicit_close_probe_prompt_review")
    )

    lines = [
        "Paper lab revalidation brief",
        f"state: {_text(payload.get('state'))}",
        f"usable_for_manual_review: {_bool_text(payload.get('usable_for_manual_review'))}",
        f"paper_lab_only: {_bool_text(labels.get('paper_lab_only'))}",
        f"not_live_authorized: {_bool_text(labels.get('not_live_authorized'))}",
        f"manual_review_required: {_bool_text(labels.get('manual_review_required'))}",
        f"profit_claim: {_text(labels.get('profit_claim'))}",
        f"manual_review_note: {_text(payload.get('manual_review_note'))}",
        f"next_probe_note: {_text(payload.get('next_probe_note'))}",
        f"run_ids: {_joined(payload.get('run_ids'))}",
        f"selected_run_id: {_text(payload.get('selected_run_id')) or 'none'}",
        f"record_count: {_text(payload.get('record_count'))}",
        f"selected_record_count: {_text(payload.get('selected_record_count'))}",
    ]
    lines.extend(_event_count_lines(_mapping(payload.get("event_counts"))))
    lines.extend(
        [
            f"account_observed: {_bool_text(observations.get('account'))}",
            f"positions_observed: {_bool_text(observations.get('positions'))}",
            f"orders_observed: {_bool_text(observations.get('orders'))}",
            f"missing_observations: {_joined(payload.get('missing_observations'))}",
        ]
    )
    if account.get("observed"):
        lines.append(
            "account_cash: "
            f"{_text(account.get('cash'))} {_text(account.get('currency'))}".strip()
        )
    else:
        lines.append("account_cash: unavailable")

    lines.extend(
        [
            f"position_count: {_text(positions.get('position_count'))}",
            f"position_symbols: {_joined(positions.get('symbols'))}",
            f"recent_order_count: {_text(recent_orders.get('count'))}",
        ]
    )
    for status in _sequence(recent_orders.get("statuses")):
        if not isinstance(status, Mapping):
            continue
        lines.append(f"recent_order_status: {_status_text(status)}")

    if submit_observation.get("has_submit_context"):
        lines.extend(_submit_observation_lines(submit_observation))

    lines.extend(_post_receipt_reconciliation_lines(post_receipt_reconciliation))
    lines.extend(
        _paper_close_post_action_reconciliation_lines(
            paper_close_post_action_reconciliation
        )
    )
    lines.extend(_fresh_snapshot_operator_checklist_lines(fresh_snapshot_checklist))
    lines.extend(_close_exit_probe_design_lines(close_exit_probe_design))
    lines.extend(_close_action_eligibility_checklist_lines(close_action_eligibility))
    lines.extend(
        _future_close_probe_preparation_lines(future_close_probe_preparation)
    )
    lines.extend(
        _explicit_close_probe_prompt_review_lines(
            explicit_close_probe_prompt_review
        )
    )

    unavailable_events = _sequence(payload.get("unavailable_events"))
    if unavailable_events:
        for event in unavailable_events:
            if isinstance(event, Mapping):
                lines.append(f"unavailable_event: {_event_text(event)}")
    else:
        lines.append("unavailable_events: none")

    invalid_reasons = _sequence(payload.get("invalid_reasons"))
    if invalid_reasons:
        lines.append(f"invalid_reasons: {_joined(invalid_reasons)}")

    lines.append(
        f"redaction_markers_found: {_joined(payload.get('redaction_markers_found'))}"
    )
    return "\n".join(lines)


def _brief_payload(
    state: str,
    *,
    records: Sequence[Mapping[str, Any]],
    selected_records: Sequence[Mapping[str, Any]],
    selected_run_id: str,
    run_ids: Sequence[str],
    invalid_reasons: Sequence[str],
    observation_records: Sequence[Mapping[str, Any]] | None = None,
    submit_observation: Mapping[str, object] | None = None,
    run_log_path: str | Path | None = None,
) -> dict[str, object]:
    observation_records = selected_records if observation_records is None else observation_records
    submit_observation = (
        _submit_observation(records)
        if submit_observation is None
        else dict(submit_observation)
    )
    observations = _observations(selected_records)
    missing_observations = _missing_observations(selected_records)
    unavailable_events = _unavailable_or_error_events(observation_records)
    usable = state in _MANUAL_REVIEW_USABLE_STATES
    fresh_snapshot_checklist = _fresh_snapshot_operator_checklist(
        state,
        records=records,
        selected_records=selected_records,
        missing_observations=missing_observations,
        unavailable_events=unavailable_events,
    )
    close_exit_probe_design = _close_exit_probe_design(fresh_snapshot_checklist)
    close_action_eligibility_checklist = _close_action_eligibility_checklist(
        fresh_snapshot_checklist,
        records=records,
        selected_run_id=selected_run_id,
    )
    future_close_probe_preparation = _future_close_probe_preparation(
        fresh_snapshot_checklist,
        close_action_eligibility_checklist,
    )
    redaction_markers_found = _redaction_markers(observation_records)
    explicit_close_probe_prompt_review = _explicit_close_probe_prompt_review(
        future_close_probe_preparation,
        close_action_eligibility_checklist,
        redaction_markers_found,
    )
    return {
        "account": _latest_account(selected_records),
        "advisory_labels": {
            "manual_review_required": True,
            "not_live_authorized": True,
            "paper_lab_only": True,
            "profit_claim": "none",
        },
        "close_action_eligibility_checklist": close_action_eligibility_checklist,
        "close_exit_probe_design": close_exit_probe_design,
        "command": "paper-lab-revalidation-brief",
        "event_counts": _event_counts(selected_records),
        "explicit_close_probe_prompt_review": (
            explicit_close_probe_prompt_review
        ),
        "fresh_snapshot_operator_checklist": fresh_snapshot_checklist,
        "future_close_probe_preparation": future_close_probe_preparation,
        "invalid_reasons": list(invalid_reasons),
        "manual_review_note": (
            "manual review required before any further paper probe"
        ),
        "missing_observations": list(missing_observations),
        "next_probe_note": "next manual paper probe remains outside this command",
        "observations": observations,
        "paper_close_post_action_reconciliation": (
            _paper_close_post_action_reconciliation(
                run_log_path,
                selected_records=selected_records,
            )
        ),
        "positions": _latest_positions(selected_records),
        "post_receipt_reconciliation": _post_receipt_reconciliation(
            state,
            submit_observation,
        ),
        "recent_orders": _latest_recent_orders(selected_records),
        "record_count": len(records),
        "redaction_markers_found": redaction_markers_found,
        "run_ids": list(run_ids),
        "selected_record_count": len(selected_records),
        "selected_run_id": _safe_run_id(selected_run_id),
        "state": state,
        "submit_observation": submit_observation,
        "unavailable_events": unavailable_events,
        "usable_for_manual_review": usable,
    }


def _close_exit_probe_design(
    fresh_snapshot_checklist: Mapping[str, object],
) -> dict[str, object]:
    evidence = _mapping(fresh_snapshot_checklist.get("evidence"))
    observed_quantity = _text(evidence.get("btcusd_position_quantity"))
    contract = build_btcusd_paper_close_preview_contract(
        observed_position_quantity=observed_quantity,
        requested_close_quantity=observed_quantity,
        fresh_snapshot_status=_text(fresh_snapshot_checklist.get("status")),
        recent_order_query_metadata_complete=(
            evidence.get("recent_order_query_metadata_complete") is True
        ),
        source_mutated=_bool_or_none(evidence.get("mutated")),
        source_submitted=_bool_or_none(evidence.get("submitted")),
    )
    payload = contract.to_payload()
    payload["design_ready"] = payload["ok"]
    payload["source_evidence"] = "fresh_snapshot_operator_checklist"
    return payload


def _close_action_eligibility_checklist(
    fresh_snapshot_checklist: Mapping[str, object],
    *,
    records: Sequence[Mapping[str, Any]],
    selected_run_id: str,
) -> dict[str, object]:
    evidence = _mapping(fresh_snapshot_checklist.get("evidence"))
    close_preview = _close_preview_evidence(records)
    observed_quantity_text = _text(evidence.get("btcusd_position_quantity"))
    requested_quantity_text = _text(close_preview.get("requested_close_quantity"))
    remaining_quantity_text = _text(
        close_preview.get("remaining_quantity_after_preview")
    )
    findings = _close_action_blocking_findings(
        fresh_snapshot_checklist,
        evidence=evidence,
        close_preview=close_preview,
    )
    status = _close_action_status(findings)
    eligible = status == _CLOSE_ACTION_STATUS_ELIGIBLE
    return {
        "version": _CLOSE_ACTION_ELIGIBILITY_VERSION,
        "status": status,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
        "manual_review_required": True,
        "eligible_for_future_close_probe_consideration": eligible,
        "broker_action_performed": False,
        "close_order_submitted": False,
        "snapshot_run_id": (
            _safe_run_id(selected_run_id)
            if evidence.get("snapshot_records_observed") is True
            else ""
        ),
        "close_preview_event_observed": (
            close_preview.get("event_observed") is True
        ),
        "observed_position_quantity": observed_quantity_text,
        "requested_close_quantity": requested_quantity_text,
        "remaining_quantity_after_preview": remaining_quantity_text,
        "required_operator_confirmations": list(
            _CLOSE_ACTION_REQUIRED_OPERATOR_CONFIRMATIONS
        ),
        "blocking_reasons": [reason for _, reason in findings],
        "limitations": _close_action_limitations(status, findings),
        "recommended_next_operator_action": (
            _CLOSE_ACTION_NEXT_ELIGIBLE if eligible else _CLOSE_ACTION_NEXT_BLOCKED
        ),
    }


def _future_close_probe_preparation(
    fresh_snapshot_checklist: Mapping[str, object],
    close_action_eligibility: Mapping[str, object],
) -> dict[str, object]:
    snapshot_evidence = _mapping(fresh_snapshot_checklist.get("evidence"))
    eligibility_status = _text(close_action_eligibility.get("status"))
    ready = eligibility_status == _CLOSE_ACTION_STATUS_ELIGIBLE
    operator_confirmations = _deduped_text_items(
        _sequence(close_action_eligibility.get("required_operator_confirmations"))
    )
    if not operator_confirmations:
        operator_confirmations = list(_CLOSE_ACTION_REQUIRED_OPERATOR_CONFIRMATIONS)

    return {
        "version": _FUTURE_CLOSE_PROBE_PREPARATION_VERSION,
        "manual_review_only": True,
        "broker_action_performed": False,
        "close_order_submitted": False,
        "ready_for_future_prompt_generation": ready,
        "required_operator_confirmation": operator_confirmations,
        "required_pre_submit_snapshot": {
            "required_status": CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED,
            "observed_status": _text(fresh_snapshot_checklist.get("status")),
            "snapshot_records_observed": (
                snapshot_evidence.get("snapshot_records_observed") is True
            ),
            "snapshot_run_id": _text(
                close_action_eligibility.get("snapshot_run_id")
            ),
            "mutated": _bool_or_none(snapshot_evidence.get("mutated")),
            "submitted": _bool_or_none(snapshot_evidence.get("submitted")),
        },
        "required_position_quantity": {
            "symbol": "BTCUSD",
            "quantity": _text(
                close_action_eligibility.get("observed_position_quantity")
            ),
            "requested_close_quantity": _text(
                close_action_eligibility.get("requested_close_quantity")
            ),
            "positive_quantity_required": True,
        },
        "required_recent_order_query_metadata": {
            "metadata_complete": (
                snapshot_evidence.get("recent_order_query_metadata_complete")
                is True
            ),
            "contract_version": _text(
                snapshot_evidence.get("recent_order_query_contract_version")
            ),
            "returned_count": snapshot_evidence.get(
                "recent_order_query_returned_count"
            ),
            "missing_fields": list(
                _sequence(
                    snapshot_evidence.get(
                        "recent_order_query_metadata_missing_fields"
                    )
                )
            ),
        },
        "required_close_preview_evidence": {
            "event_observed": (
                close_action_eligibility.get("close_preview_event_observed")
                is True
            ),
            "preview_only_required": True,
            "submitted_required": False,
            "mutated_required": False,
            "requested_close_quantity": _text(
                close_action_eligibility.get("requested_close_quantity")
            ),
            "remaining_quantity_after_preview": _text(
                close_action_eligibility.get(
                    "remaining_quantity_after_preview"
                )
            ),
        },
        "required_eligibility_status": _CLOSE_ACTION_STATUS_ELIGIBLE,
        "observed_eligibility_status": eligibility_status,
        "blocking_reasons": _future_close_probe_preparation_blocking_reasons(
            eligibility_status,
            close_action_eligibility,
        ),
        "recommended_next_operator_action": (
            _FUTURE_CLOSE_PROBE_NEXT_ELIGIBLE
            if ready
            else _FUTURE_CLOSE_PROBE_NEXT_BLOCKED
        ),
        "future_command_template_review_only": (
            _FUTURE_CLOSE_PROBE_COMMAND_TEMPLATE
        ),
        "future_command_template_safety_note": (
            _FUTURE_CLOSE_PROBE_TEMPLATE_SAFETY_NOTE
        ),
    }


def _future_close_probe_preparation_blocking_reasons(
    eligibility_status: str,
    close_action_eligibility: Mapping[str, object],
) -> list[str]:
    if eligibility_status == _CLOSE_ACTION_STATUS_ELIGIBLE:
        return []

    reasons = [
        f"m326_eligibility_status_{eligibility_status or 'missing'}",
    ]
    reasons.extend(
        _deduped_text_items(
            _sequence(close_action_eligibility.get("blocking_reasons"))
        )
    )
    return _deduped_text_items(reasons)


def _explicit_close_probe_prompt_review(
    future_preparation: Mapping[str, object],
    close_action_eligibility: Mapping[str, object],
    redaction_markers_found: Sequence[str],
) -> dict[str, object]:
    pre_submit_snapshot = _mapping(
        future_preparation.get("required_pre_submit_snapshot")
    )
    position_quantity = _mapping(
        future_preparation.get("required_position_quantity")
    )
    query_metadata = _mapping(
        future_preparation.get("required_recent_order_query_metadata")
    )
    close_preview = _mapping(
        future_preparation.get("required_close_preview_evidence")
    )
    generated_from_preparation = (
        future_preparation.get("version")
        == _FUTURE_CLOSE_PROBE_PREPARATION_VERSION
    )
    observed_preparation_ready = (
        future_preparation.get("ready_for_future_prompt_generation") is True
    )
    observed_eligibility_status = _text(
        future_preparation.get("observed_eligibility_status")
    ) or _text(close_action_eligibility.get("status"))
    close_preview_evidence_exists = close_preview.get("event_observed") is True
    fresh_snapshot_complete = (
        pre_submit_snapshot.get("observed_status")
        == CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED
        and pre_submit_snapshot.get("snapshot_records_observed") is True
    )
    recent_order_query_metadata_complete = (
        query_metadata.get("metadata_complete") is True
    )
    redaction_marker_present = "credentials_redacted" in set(
        redaction_markers_found
    )
    observed_position_symbol = _text(position_quantity.get("symbol"))
    observed_position_quantity = _text(position_quantity.get("quantity"))
    prompt_ready = (
        generated_from_preparation
        and observed_preparation_ready
        and observed_eligibility_status == _CLOSE_ACTION_STATUS_ELIGIBLE
        and close_preview_evidence_exists
        and fresh_snapshot_complete
        and recent_order_query_metadata_complete
        and redaction_marker_present
    )
    blocking_reasons = _explicit_close_probe_prompt_review_blocking_reasons(
        generated_from_preparation=generated_from_preparation,
        observed_preparation_ready=observed_preparation_ready,
        observed_eligibility_status=observed_eligibility_status,
        close_preview_evidence_exists=close_preview_evidence_exists,
        fresh_snapshot_complete=fresh_snapshot_complete,
        recent_order_query_metadata_complete=(
            recent_order_query_metadata_complete
        ),
        redaction_marker_present=redaction_marker_present,
    )
    return {
        "version": _EXPLICIT_CLOSE_PROBE_PROMPT_REVIEW_VERSION,
        "manual_review_only": True,
        "broker_action_performed": False,
        "close_order_submitted": False,
        "prompt_ready_for_operator_review": prompt_ready,
        "generated_from_future_close_probe_preparation": (
            generated_from_preparation
        ),
        "observed_preparation_ready": observed_preparation_ready,
        "observed_eligibility_status": observed_eligibility_status,
        "observed_position_symbol": observed_position_symbol,
        "observed_position_quantity": observed_position_quantity,
        "observed_recent_order_query_metadata_complete": (
            recent_order_query_metadata_complete
        ),
        "required_final_pre_submit_snapshot": True,
        "required_final_operator_confirmation": True,
        "future_probe_scope": _EXPLICIT_CLOSE_PROBE_REVIEW_SCOPE,
        "blocking_reasons": blocking_reasons,
        "recommended_next_operator_action": (
            _EXPLICIT_CLOSE_PROBE_REVIEW_NEXT_ELIGIBLE
            if prompt_ready
            else _EXPLICIT_CLOSE_PROBE_REVIEW_NEXT_BLOCKED
        ),
        "review_only_prompt_text": _explicit_close_probe_review_prompt_text(
            observed_position_symbol,
            observed_position_quantity,
        ),
        "future_command_template_review_only": (
            _EXPLICIT_CLOSE_PROBE_COMMAND_TEMPLATE
        ),
    }


def _explicit_close_probe_prompt_review_blocking_reasons(
    *,
    generated_from_preparation: bool,
    observed_preparation_ready: bool,
    observed_eligibility_status: str,
    close_preview_evidence_exists: bool,
    fresh_snapshot_complete: bool,
    recent_order_query_metadata_complete: bool,
    redaction_marker_present: bool,
) -> list[str]:
    reasons: list[str] = []
    if not generated_from_preparation:
        reasons.append("future_close_probe_preparation_missing")
    if not observed_preparation_ready:
        reasons.append("future_close_probe_preparation_not_ready")
    if observed_eligibility_status != _CLOSE_ACTION_STATUS_ELIGIBLE:
        reasons.append(
            f"m326_eligibility_status_{observed_eligibility_status or 'missing'}"
        )
    if not close_preview_evidence_exists:
        reasons.append("close_preview_evidence_missing")
    if not fresh_snapshot_complete:
        reasons.append("fresh_snapshot_checklist_incomplete")
    if not recent_order_query_metadata_complete:
        reasons.append("recent_order_query_metadata_incomplete")
    if not redaction_marker_present:
        reasons.append("redaction_marker_missing")
    return _deduped_text_items(reasons)


def _explicit_close_probe_review_prompt_text(
    observed_position_symbol: str,
    observed_position_quantity: str,
) -> str:
    symbol = observed_position_symbol or "BTCUSD"
    quantity = observed_position_quantity or "<OBSERVED_BTCUSD_POSITION_QUANTITY>"
    return (
        "OPERATOR REVIEW ONLY: draft a possible separate M329 approval packet "
        f"for a future {symbol} paper close probe. This review does not "
        "execute, authorize, simulate, or submit any broker-side action. "
        f"Observed {symbol} position quantity: {quantity}. A future action, if "
        "separately authorized, must first require a final fresh read-only "
        "paper snapshot and explicit final operator confirmation."
    )


def _close_preview_evidence(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, object]:
    record = _latest_record(records, PAPER_CLOSE_PREVIEW_DESIGNED)
    if record is None:
        return {"event_observed": False}

    return {
        "event_observed": True,
        "run_id": _safe_run_id(record.get("run_id")),
        "asset_class": _text(record.get("asset_class")).lower(),
        "symbol": _text(record.get("symbol")).upper(),
        "side": _text(record.get("side")).lower(),
        "ok": _record_bool(record, "ok"),
        "preview_only": _record_bool(record, "preview_only"),
        "submitted": _record_bool(record, "submitted"),
        "mutated": _record_bool(record, "mutated"),
        "paper_lab_only": _record_bool(record, "paper_lab_only"),
        "not_live_authorized": _record_bool(record, "not_live_authorized"),
        "manual_review_required": _record_bool(record, "manual_review_required"),
        "profit_claim": _text(record.get("profit_claim")),
        "observed_position_quantity": _text(
            record.get("observed_position_quantity")
        ),
        "requested_close_quantity": _text(record.get("requested_close_quantity")),
        "remaining_quantity_after_preview": _text(
            record.get("remaining_quantity_after_preview")
        ),
        "no_shorting_gate": _text(record.get("no_shorting_gate")),
        "submission_disabled_reason": _text(
            record.get("submission_disabled_reason")
        ),
    }


def _close_action_blocking_findings(
    fresh_snapshot_checklist: Mapping[str, object],
    *,
    evidence: Mapping[str, object],
    close_preview: Mapping[str, object],
) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    snapshot_status = _text(fresh_snapshot_checklist.get("status"))
    observed_quantity = _positive_decimal_or_none(
        evidence.get("btcusd_position_quantity")
    )
    requested_quantity = _positive_decimal_or_none(
        close_preview.get("requested_close_quantity")
    )

    if evidence.get("credential_leak_evidence") is True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE,
            "credential_leak_evidence_found",
        )
    if evidence.get("live_profile_evidence") is True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE,
            "live_profile_evidence_found",
        )

    if evidence.get("snapshot_records_observed") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_MISSING_FRESH_SNAPSHOT,
            "fresh_snapshot_evidence_missing",
        )
    elif snapshot_status != CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED:
        _add_close_action_finding(
            findings,
            _close_action_status_for_snapshot_status(snapshot_status),
            f"fresh_snapshot_checklist_status_{snapshot_status or 'missing'}",
        )

    if evidence.get("ok") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "fresh_snapshot_ok_not_true",
        )
    if evidence.get("mutated") is True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_MUTATION,
            "fresh_snapshot_mutated_true",
        )
    elif evidence.get("mutated") is not False:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "fresh_snapshot_mutated_not_observed_false",
        )
    if evidence.get("submitted") is True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_SUBMIT,
            "fresh_snapshot_submitted_true",
        )
    elif evidence.get("submitted") is not False:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "fresh_snapshot_submitted_not_observed_false",
        )

    for field_name, reason in (
        ("account_observation_available", "account_observation_missing"),
        ("positions_observation_available", "positions_observation_missing"),
        ("orders_observation_available", "orders_observation_missing"),
    ):
        if evidence.get(field_name) is not True:
            _add_close_action_finding(
                findings,
                _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
                reason,
            )

    if evidence.get("btcusd_position_status") != "present":
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_MISSING_POSITION,
            "btcusd_position_not_present",
        )
    if observed_quantity is None:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_INVALID_QUANTITY,
            "observed_btcusd_quantity_not_positive",
        )
    if evidence.get("recent_order_query_metadata_complete") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE,
            "recent_order_query_metadata_incomplete",
        )
    if evidence.get("recent_order_query_returned_count") is None:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE,
            "recent_open_order_count_not_observed",
        )
    if evidence.get("credentials_redacted_present") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "credentials_redacted_marker_missing",
        )

    if close_preview.get("event_observed") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_MISSING_CLOSE_PREVIEW,
            "close_preview_evidence_missing",
        )
        return findings

    if close_preview.get("preview_only") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_preview_only_not_true",
        )
    if close_preview.get("submitted") is True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_SUBMIT,
            "close_preview_submitted_true",
        )
    elif close_preview.get("submitted") is not False:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_submitted_not_observed_false",
        )
    if close_preview.get("mutated") is True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_MUTATION,
            "close_preview_mutated_true",
        )
    elif close_preview.get("mutated") is not False:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_mutated_not_observed_false",
        )
    if close_preview.get("asset_class") != "crypto":
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_asset_class_not_crypto",
        )
    if close_preview.get("symbol") != "BTCUSD":
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_symbol_not_BTCUSD",
        )
    if close_preview.get("side") != "sell":
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_side_not_sell",
        )
    if requested_quantity is None:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_INVALID_QUANTITY,
            "requested_close_quantity_not_positive",
        )
    elif observed_quantity is not None and requested_quantity > observed_quantity:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_NO_SHORTING_GATE_FAILED,
            "requested_close_quantity_exceeds_observed_position",
        )
    if close_preview.get("no_shorting_gate") != "passed":
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_BLOCKED_NO_SHORTING_GATE_FAILED,
            "no_shorting_gate_not_passed",
        )
    if (
        close_preview.get("submission_disabled_reason")
        != PAPER_CLOSE_PREVIEW_SUBMISSION_DISABLED_REASON
    ):
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "submission_disabled_reason_missing",
        )
    if close_preview.get("manual_review_required") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "manual_review_required_not_true",
        )
    if close_preview.get("paper_lab_only") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_paper_lab_only_not_true",
        )
    if close_preview.get("not_live_authorized") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_not_live_authorized_not_true",
        )
    if close_preview.get("profit_claim") != "none":
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_profit_claim_not_none",
        )
    if close_preview.get("ok") is not True:
        _add_close_action_finding(
            findings,
            _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
            "close_preview_ok_not_true",
        )

    return findings


def _close_action_status(
    findings: Sequence[tuple[str, str]],
) -> str:
    if not findings:
        return _CLOSE_ACTION_STATUS_ELIGIBLE

    priority = (
        _CLOSE_ACTION_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE,
        _CLOSE_ACTION_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE,
        _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_MUTATION,
        _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_SUBMIT,
        _CLOSE_ACTION_STATUS_BLOCKED_MISSING_FRESH_SNAPSHOT,
        _CLOSE_ACTION_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE,
        _CLOSE_ACTION_STATUS_BLOCKED_MISSING_POSITION,
        _CLOSE_ACTION_STATUS_BLOCKED_INVALID_QUANTITY,
        _CLOSE_ACTION_STATUS_BLOCKED_NO_SHORTING_GATE_FAILED,
        _CLOSE_ACTION_STATUS_BLOCKED_MISSING_CLOSE_PREVIEW,
        _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION,
    )
    statuses = {status for status, _ in findings}
    for status in priority:
        if status in statuses:
            return status

    return _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION


def _close_action_status_for_snapshot_status(snapshot_status: str) -> str:
    if snapshot_status == CHECKLIST_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE:
        return _CLOSE_ACTION_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE
    if snapshot_status == CHECKLIST_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE:
        return _CLOSE_ACTION_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE
    if snapshot_status == CHECKLIST_STATUS_BLOCKED_UNEXPECTED_MUTATION:
        return _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_MUTATION
    if snapshot_status == CHECKLIST_STATUS_BLOCKED_UNEXPECTED_SUBMIT:
        return _CLOSE_ACTION_STATUS_BLOCKED_UNEXPECTED_SUBMIT
    if snapshot_status == CHECKLIST_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE:
        return _CLOSE_ACTION_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE
    if snapshot_status == CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED:
        return _CLOSE_ACTION_STATUS_ELIGIBLE
    if not snapshot_status:
        return _CLOSE_ACTION_STATUS_BLOCKED_MISSING_FRESH_SNAPSHOT

    return _CLOSE_ACTION_STATUS_INSUFFICIENT_OBSERVATION


def _add_close_action_finding(
    findings: list[tuple[str, str]],
    status: str,
    reason: str,
) -> None:
    if reason not in {existing_reason for _, existing_reason in findings}:
        findings.append((status, reason))


def _deduped_text_items(values: Sequence[Any]) -> list[str]:
    items: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in items:
            items.append(text)
    return items


def _positive_decimal_or_none(value: Any) -> Decimal | None:
    text = _text(value)
    if not text:
        return None
    try:
        decimal_value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None

    if decimal_value <= 0:
        return None

    return decimal_value


def _close_action_limitations(
    status: str,
    findings: Sequence[tuple[str, str]],
) -> list[str]:
    if status == _CLOSE_ACTION_STATUS_ELIGIBLE:
        return [
            "eligibility only supports preparing a later explicit operator prompt",
            "no broker action is authorized or performed by this checklist",
        ]

    reasons = ", ".join(reason for _, reason in findings)
    return [
        "close action eligibility is blocked until required read-only and "
        "preview evidence is complete",
        f"blocking reasons: {reasons}" if reasons else "blocking reasons: none",
    ]


def _fresh_snapshot_operator_checklist(
    state: str,
    *,
    records: Sequence[Mapping[str, Any]],
    selected_records: Sequence[Mapping[str, Any]],
    missing_observations: Sequence[str],
    unavailable_events: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    snapshot_records = _snapshot_records_for_checklist(selected_records)
    evidence = _fresh_snapshot_checklist_evidence(records, snapshot_records)
    status = _fresh_snapshot_checklist_status(
        state,
        evidence=evidence,
        missing_observations=missing_observations,
        unavailable_events=unavailable_events,
    )
    return {
        "version": _CHECKLIST_VERSION,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
        "pre_run_status": CHECKLIST_STATUS_READY_FOR_READ_ONLY_SNAPSHOT,
        "status": status,
        "recommended_next_operator_action": (
            _fresh_snapshot_checklist_action(status)
        ),
        "fresh_snapshot_command_template": _FRESH_SNAPSHOT_COMMAND_TEMPLATE,
        "pre_run_checklist": list(_PRE_RUN_CHECKLIST_ITEMS),
        "post_run_checklist": list(_POST_RUN_CHECKLIST_ITEMS),
        "evidence": evidence,
        "limitations": _fresh_snapshot_checklist_limitations(
            status,
            evidence=evidence,
            missing_observations=missing_observations,
        ),
    }


def _snapshot_records_for_checklist(
    records: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    return tuple(record for record in records if _is_snapshot_record(record))


def _is_snapshot_record(record: Mapping[str, Any]) -> bool:
    command = _text(record.get("command"))
    event_type = _safe_event_type(record.get("event_type"))
    return command == "paper-lab-snapshot" or event_type.startswith(
        "paper_lab_snapshot_"
    )


def _fresh_snapshot_checklist_evidence(
    records: Sequence[Mapping[str, Any]],
    snapshot_records: Sequence[Mapping[str, Any]],
) -> dict[str, object]:
    account = _latest_account(snapshot_records)
    latest_orders = _latest_record(snapshot_records, PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED)
    profile_gate = _profile_gate_evidence(snapshot_records)
    btcusd_position = _btcusd_position_evidence(snapshot_records)
    redaction_markers = _redaction_markers(records)
    query_missing_fields = _recent_order_query_metadata_missing_fields(latest_orders)
    query_metadata = _recent_order_query_metadata(latest_orders)
    return {
        "snapshot_records_observed": bool(snapshot_records),
        "profile_gate_reported": profile_gate["reported"],
        "profile_gate_status": profile_gate["status"],
        "ok": _snapshot_bool_observation(snapshot_records, "ok"),
        "mutated": _snapshot_bool_observation(snapshot_records, "mutated"),
        "submitted": _snapshot_bool_observation(snapshot_records, "submitted"),
        "account_observation_available": _observation_available(
            snapshot_records,
            PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
            "account_observation_available",
        ),
        "positions_observation_available": _observation_available(
            snapshot_records,
            PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
            "positions_observation_available",
        ),
        "orders_observation_available": _observation_available(
            snapshot_records,
            PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
            "orders_observation_available",
        ),
        "account_cash_observed": bool(account.get("cash")),
        "account_currency_observed": bool(account.get("currency")),
        "btcusd_position_status": btcusd_position["status"],
        "btcusd_position_quantity": btcusd_position["quantity"],
        "btcusd_position_average_price": btcusd_position["average_price"],
        "recent_order_query_contract_version": query_metadata[
            "recent_order_query_contract_version"
        ],
        "recent_order_query_metadata_complete": (
            latest_orders is not None
            and not query_missing_fields
            and _record_bool(
                latest_orders, "recent_order_query_metadata_complete"
            )
            is not False
        ),
        "recent_order_query_metadata_missing_fields": list(query_missing_fields),
        "recent_order_query_returned_count": _recent_order_query_returned_count(
            latest_orders
        ),
        "unavailable_observations": list(
            _unavailable_observations(snapshot_records)
        ),
        "credentials_redacted_present": "credentials_redacted" in redaction_markers,
        "live_profile_evidence": _live_profile_evidence_found(records),
        "credential_leak_evidence": _credential_leak_evidence_found(records),
    }


def _fresh_snapshot_checklist_status(
    state: str,
    *,
    evidence: Mapping[str, object],
    missing_observations: Sequence[str],
    unavailable_events: Sequence[Mapping[str, object]],
) -> str:
    if evidence.get("credential_leak_evidence") is True:
        return CHECKLIST_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE
    if evidence.get("live_profile_evidence") is True:
        return CHECKLIST_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE

    profile_gate_status = _text(evidence.get("profile_gate_status"))
    if profile_gate_status == "missing_credentials":
        return CHECKLIST_STATUS_BLOCKED_MISSING_CREDENTIALS
    if profile_gate_status in {"missing_paper_profile", "failed"}:
        return CHECKLIST_STATUS_BLOCKED_MISSING_PAPER_PROFILE

    if evidence.get("mutated") is True:
        return CHECKLIST_STATUS_BLOCKED_UNEXPECTED_MUTATION
    if evidence.get("submitted") is True:
        return CHECKLIST_STATUS_BLOCKED_UNEXPECTED_SUBMIT
    if (
        state == STATE_OBSERVATION_UNAVAILABLE
        or bool(unavailable_events)
        or bool(_sequence(evidence.get("unavailable_observations")))
    ):
        return CHECKLIST_STATUS_BLOCKED_UNAVAILABLE_OBSERVATIONS
    if not evidence.get("snapshot_records_observed") or missing_observations:
        return CHECKLIST_STATUS_INSUFFICIENT_OBSERVATION
    if (
        evidence.get("account_observation_available") is not True
        or evidence.get("positions_observation_available") is not True
        or evidence.get("orders_observation_available") is not True
    ):
        return CHECKLIST_STATUS_BLOCKED_UNAVAILABLE_OBSERVATIONS
    if (
        evidence.get("account_cash_observed") is not True
        or evidence.get("account_currency_observed") is not True
    ):
        return CHECKLIST_STATUS_INSUFFICIENT_OBSERVATION
    if evidence.get("ok") is False:
        return CHECKLIST_STATUS_BLOCKED_UNAVAILABLE_OBSERVATIONS
    if evidence.get("recent_order_query_metadata_complete") is not True:
        return CHECKLIST_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE
    if evidence.get("recent_order_query_returned_count") is None:
        return CHECKLIST_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE
    if evidence.get("profile_gate_reported") is not True:
        return CHECKLIST_STATUS_INSUFFICIENT_OBSERVATION
    if evidence.get("credentials_redacted_present") is not True:
        return CHECKLIST_STATUS_INSUFFICIENT_OBSERVATION
    if (
        evidence.get("btcusd_position_status") == "present"
        and (
            not _text(evidence.get("btcusd_position_quantity"))
            or not _text(evidence.get("btcusd_position_average_price"))
        )
    ):
        return CHECKLIST_STATUS_INSUFFICIENT_OBSERVATION

    return CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED


def _fresh_snapshot_checklist_action(status: str) -> str:
    if status == CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED:
        return _CHECKLIST_ACTION_MANUAL_REVIEW_FRESH_SNAPSHOT
    if status in {
        CHECKLIST_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE,
        CHECKLIST_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE,
        CHECKLIST_STATUS_BLOCKED_UNEXPECTED_MUTATION,
        CHECKLIST_STATUS_BLOCKED_UNEXPECTED_SUBMIT,
    }:
        return _CHECKLIST_ACTION_STOP_AND_REPAIR

    return _RECONCILIATION_ACTION_FRESH_SNAPSHOT_BEFORE_CLOSE


def _fresh_snapshot_checklist_limitations(
    status: str,
    *,
    evidence: Mapping[str, object],
    missing_observations: Sequence[str],
) -> list[str]:
    limitations: list[str] = []
    if status == CHECKLIST_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE:
        limitations.append(
            "recent order query metadata is incomplete; keep old evidence "
            "conservative before any close-probe design"
        )
    if status == CHECKLIST_STATUS_BLOCKED_UNAVAILABLE_OBSERVATIONS:
        limitations.append(
            "one or more account, positions, or orders observations are unavailable"
        )
    if status == CHECKLIST_STATUS_BLOCKED_UNEXPECTED_MUTATION:
        limitations.append(
            "snapshot evidence reports mutation; stop before any close-probe design"
        )
    if status == CHECKLIST_STATUS_BLOCKED_UNEXPECTED_SUBMIT:
        limitations.append(
            "snapshot evidence reports submit; stop before any close-probe design"
        )
    if status == CHECKLIST_STATUS_BLOCKED_LIVE_PROFILE_EVIDENCE:
        limitations.append(
            "live profile or live URL evidence appears in the local log"
        )
    if status == CHECKLIST_STATUS_BLOCKED_CREDENTIAL_LEAK_EVIDENCE:
        limitations.append(
            "credential-like evidence appears in the local log"
        )
    if status == CHECKLIST_STATUS_BLOCKED_MISSING_PAPER_PROFILE:
        limitations.append("profile gate did not prove paper_profile_ready")
    if status == CHECKLIST_STATUS_BLOCKED_MISSING_CREDENTIALS:
        limitations.append("profile gate reports missing paper-only credentials")
    if missing_observations:
        limitations.append(
            f"missing snapshot observations: {','.join(missing_observations)}"
        )
    if (
        evidence.get("profile_gate_reported") is not True
        and status != CHECKLIST_STATUS_BLOCKED_QUERY_METADATA_INCOMPLETE
    ):
        limitations.append("profile gate evidence is missing from the snapshot log")
    if evidence.get("credentials_redacted_present") is not True:
        limitations.append("credentials_redacted marker is missing")
    if status == CHECKLIST_STATUS_READ_ONLY_SNAPSHOT_COMPLETED:
        limitations.append(
            "fresh read-only snapshot is ready for manual review only"
        )

    return limitations


def _profile_gate_evidence(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, object]:
    for record in reversed(records):
        gates = _mapping(record.get("gate_summary")) or _mapping(record.get("gates"))
        profile_gate = _mapping(gates.get("profile_gate"))
        if not profile_gate:
            continue
        passed = _record_bool(profile_gate, "passed")
        detail = _text(profile_gate.get("detail"))
        if passed is True:
            return {"reported": True, "status": "paper_profile_ready"}
        if "ALPACA_API_KEY" in detail or "ALPACA_SECRET_KEY" in detail:
            return {"reported": True, "status": "missing_credentials"}
        if "APP_PROFILE=paper" in detail or "paper profile" in detail.lower():
            return {"reported": True, "status": "missing_paper_profile"}
        return {"reported": True, "status": "failed"}

    return {"reported": False, "status": "missing"}


def _btcusd_position_evidence(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    latest_positions = _latest_record(records, PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED)
    if latest_positions is None:
        return {"status": "unavailable", "quantity": "", "average_price": ""}

    for position in _safe_positions(latest_positions.get("positions")):
        if position.get("symbol") == "BTCUSD":
            return {
                "status": "present",
                "quantity": position.get("quantity", ""),
                "average_price": position.get("average_price", ""),
            }
    if "BTCUSD" in _safe_symbols(latest_positions.get("position_symbols")):
        return {"status": "present", "quantity": "", "average_price": ""}

    return {"status": "absent", "quantity": "", "average_price": ""}


def _snapshot_bool_observation(
    records: Sequence[Mapping[str, Any]],
    key: str,
) -> bool | None:
    observed: bool | None = None
    for record in records:
        value = _record_bool(record, key)
        if value is None:
            continue
        observed = value
        if key in {"mutated", "submitted"} and value is True:
            return True

    return observed


def _observation_available(
    records: Sequence[Mapping[str, Any]],
    event_type: str,
    availability_key: str,
) -> bool:
    observed_event = any(
        _safe_event_type(record.get("event_type")) == event_type for record in records
    )
    observed_flag = _snapshot_bool_observation(records, availability_key)
    if observed_flag is not None:
        return observed_flag

    return observed_event


def _recent_order_query_returned_count(
    record: Mapping[str, Any] | None,
) -> int | None:
    if record is None:
        return None
    returned_count = _safe_optional_count(
        record.get("recent_order_query_returned_count")
    )
    if returned_count is not None:
        return returned_count

    return _safe_optional_count(record.get("recent_order_count"))


def _live_profile_evidence_found(value: Any, *, parent_key: str = "") -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _live_profile_evidence_found(item, parent_key=str(key)):
                return True
        return False
    if isinstance(value, list):
        return any(_live_profile_evidence_found(item) for item in value)
    if not isinstance(value, str):
        return False

    text = value.lower()
    key_text = parent_key.lower()
    if "profile" in key_text and "live" in text:
        return True
    if "url" in key_text or "endpoint" in key_text:
        if "live" in text:
            return True
        if ("http://" in text or "https://" in text) and "paper" not in text:
            return True
    return "app_profile=live" in text or "profile=live" in text


def _credential_leak_evidence_found(value: Any, *, parent_key: str = "") -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if _credential_key_name(key_text) and _credential_value_is_leaked(item):
                return True
            if _credential_leak_evidence_found(item, parent_key=key_text):
                return True
        return False
    if isinstance(value, list):
        return any(_credential_leak_evidence_found(item) for item in value)
    if not isinstance(value, str):
        return False

    return _credential_string_evidence(value)


def _credential_key_name(key: str) -> bool:
    return any(
        token in key
        for token in (
            "api_key",
            "apikey",
            "secret_key",
            "secretkey",
            "password",
            "token",
            "authorization",
            "bearer",
        )
    )


def _credential_value_is_leaked(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip().lower()
        return bool(text) and text not in {"<redacted>", "credentials_redacted"}
    return True


def _credential_string_evidence(value: str) -> bool:
    text = value.strip().lower()
    if not text or text in {"<redacted>", "credentials_redacted"}:
        return False
    if "credentials_redacted" in text:
        return False
    if "paper-lab-secret" in text:
        return True
    if "bearer " in text or "authorization:" in text:
        return True
    return bool(
        re.search(
            r"(api[_-]?key|secret[_-]?key|token|password|credential)\s*[:=]\s*\S+",
            text,
        )
    )


def _read_jsonl_records(
    run_log_path: str | Path,
) -> tuple[list[Mapping[str, Any]], tuple[str, ...]]:
    path = Path(run_log_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], (f"read_failed:{exc.__class__.__name__}",)

    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except JSONDecodeError:
            return records, (f"line {line_number}: JSONDecodeError",)
        if not isinstance(record, Mapping):
            return records, (f"line {line_number}: record_must_be_object",)
        records.append(record)

    return records, ()


def _selected_run_id(
    records: Sequence[Mapping[str, Any]],
    requested_run_id: str | None,
) -> str:
    if requested_run_id is not None:
        return str(requested_run_id)

    for record in reversed(records):
        run_id = record.get("run_id")
        if run_id:
            return str(run_id)

    return ""


def _selected_records(
    records: Sequence[Mapping[str, Any]],
    selected_run_id: str,
) -> tuple[Mapping[str, Any], ...]:
    if not selected_run_id:
        return ()

    return tuple(
        record for record in records if str(record.get("run_id", "")) == selected_run_id
    )


def _run_ids(records: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    run_ids: list[str] = []
    seen: set[str] = set()
    for record in records:
        run_id = record.get("run_id")
        if not run_id:
            continue
        raw_run_id = str(run_id)
        if raw_run_id in seen:
            continue
        seen.add(raw_run_id)
        run_ids.append(_safe_run_id(raw_run_id))

    return tuple(run_ids)


def _observations(records: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    event_types = {_safe_event_type(record.get("event_type")) for record in records}
    return {
        name: event_type in event_types
        for name, event_type in _OBSERVATION_EVENT_TYPES.items()
    }


def _missing_observations(
    records: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    observations = _observations(records)
    return tuple(
        name for name in ("account", "positions", "orders") if not observations[name]
    )


def _latest_account(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED)
    account = _mapping(record.get("account") if record else None)
    if not account:
        return {"cash": "", "currency": "", "observed": False}

    return {
        "cash": _safe_money(account.get("cash")),
        "currency": _safe_code(account.get("currency")),
        "observed": True,
    }


def _latest_positions(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED)
    if record is None:
        return {"observed": False, "position_count": 0, "symbols": []}

    symbols = _safe_symbols(record.get("position_symbols"))
    if not symbols:
        symbols = _symbols_from_positions(record.get("positions"))
    return {
        "observed": True,
        "position_count": _safe_count(record.get("position_count"), len(symbols)),
        "symbols": list(symbols),
    }


def _latest_recent_orders(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED)
    if record is None:
        return {"count": 0, "observed": False, "statuses": []}

    orders = _sequence(record.get("recent_orders"))
    statuses = [
        _safe_order_status(order) for order in orders if isinstance(order, Mapping)
    ]
    return {
        "count": _safe_count(record.get("recent_order_count"), len(statuses)),
        "observed": True,
        "statuses": statuses,
    }


def _submit_observation(records: Sequence[Mapping[str, Any]]) -> dict[str, object]:
    submit_attempt_indices = _event_indices(records, PAPER_ORDER_SUBMIT_ATTEMPTED)
    submit_index = submit_attempt_indices[-1] if submit_attempt_indices else None
    receipt_record = _latest_record(records, PAPER_ORDER_RECEIPT_OBSERVED)
    failed_record = _latest_record(records, PAPER_ORDER_SUBMIT_FAILED)
    parse_failed_record = _latest_record(records, PAPER_ORDER_RESPONSE_PARSE_FAILED)
    attempted_record = _latest_record(records, PAPER_ORDER_SUBMIT_ATTEMPTED)
    requested_record = _latest_record(records, PAPER_ORDER_SUBMIT_REQUESTED)
    source_record = (
        receipt_record
        or failed_record
        or parse_failed_record
        or attempted_record
        or requested_record
    )
    has_submit_context = source_record is not None

    target_symbol = _target_symbol(records, source_record)
    pre_account = _latest_event_before(
        records, PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED, submit_index
    )
    post_account = _latest_event_after(
        records, PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED, submit_index
    ) or _latest_record(records, PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED)
    pre_positions = _latest_event_before(
        records, PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED, submit_index
    )
    post_positions = _latest_event_after(
        records, PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED, submit_index
    ) or _latest_record(records, PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED)
    post_orders = _latest_event_after(
        records, PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED, submit_index
    )

    pre_cash = _account_cash(pre_account)
    post_cash = _account_cash(post_account)
    post_position_items = _safe_positions(
        post_positions.get("positions") if post_positions else None
    )
    post_position_symbols = _post_submit_position_symbols(post_positions)
    target_position = _target_position(post_position_items, target_symbol)
    recent_order_statuses = (
        [
            _safe_order_status(order)
            for order in _sequence(post_orders.get("recent_orders"))
            if isinstance(order, Mapping)
        ]
        if post_orders
        else []
    )
    recent_order_count = (
        _safe_count(post_orders.get("recent_order_count"), len(recent_order_statuses))
        if post_orders
        else None
    )
    unavailable_observations = _unavailable_observations(records)
    order_query_unavailable = "orders" in unavailable_observations and post_orders is None
    accepted = _record_bool(source_record, "accepted")
    normalized_status = _record_status(
        source_record, "normalized_status", "broker_normalized_status"
    )
    receipt_observed = receipt_record is not None
    receipt_client_order_id = _record_correlation_id(
        source_record, "client_order_id"
    )
    receipt_order_id = _record_receipt_order_id(source_record)
    target_recent_order_match_basis = (
        _target_recent_order_match_basis(
            recent_order_statuses,
            target_symbol=target_symbol,
            target_side=_record_code(source_record, "side"),
            target_notional=_record_money(source_record, "notional"),
            receipt_client_order_id=receipt_client_order_id,
            receipt_order_id=receipt_order_id,
        )
        if post_orders
        else "none"
    )
    target_recent_order_observed = (
        target_recent_order_match_basis != "none" if post_orders else None
    )
    receipt_successful = _receipt_successful(
        receipt_observed=receipt_observed,
        accepted=accepted,
        normalized_status=normalized_status,
    )
    order_list_observation_gap = bool(
        receipt_successful
        and (
            (post_orders is not None and not target_recent_order_observed)
            or order_query_unavailable
        )
    )
    order_list_gap_reason = _order_list_gap_reason(
        order_list_observation_gap=order_list_observation_gap,
        order_query_unavailable=order_query_unavailable,
        recent_order_count=recent_order_count,
        recent_order_statuses=recent_order_statuses,
        receipt_client_order_id=receipt_client_order_id,
        receipt_order_id=receipt_order_id,
        target_notional=_record_money(source_record, "notional"),
        target_recent_order_match_basis=target_recent_order_match_basis,
        target_side=_record_code(source_record, "side"),
        target_symbol=target_symbol,
    )
    recent_order_query_metadata = _recent_order_query_metadata(post_orders)
    recent_order_query_missing_fields = (
        _recent_order_query_metadata_missing_fields(post_orders)
    )

    return {
        "accepted": accepted,
        "asset_class": _record_code(source_record, "asset_class"),
        "broker_rejected": _broker_rejected(
            receipt_observed=receipt_observed,
            accepted=accepted,
            normalized_status=normalized_status,
        ),
        "broker_response_parsed": _record_bool(
            source_record, "broker_response_parsed"
        ),
        "broker_response_received": _record_bool(
            source_record, "broker_response_received"
        ),
        "cash_delta": _decimal_delta(pre_cash, post_cash),
        "filled": _record_bool(source_record, "filled"),
        "has_post_submit_observation": bool(post_account or post_positions),
        "has_submit_context": has_submit_context,
        "max_notional": _record_money(source_record, "max_notional"),
        "min_notional": _record_money(source_record, "min_notional"),
        "normalized_status": normalized_status,
        "notional": _record_money(source_record, "notional"),
        "order_list_observation_gap": order_list_observation_gap,
        "order_list_gap_reason": order_list_gap_reason,
        "order_type": _record_code(source_record, "order_type"),
        "post_submit_cash": post_cash,
        "post_submit_position_count": _position_count(post_positions),
        "post_submit_position_symbols": post_position_symbols,
        "pre_submit_cash": pre_cash,
        "pre_submit_position_count": _position_count(pre_positions),
        "raw_reason": _record_status(source_record, "raw_reason", "broker_raw_reason"),
        "raw_status": _record_status(source_record, "raw_status", "broker_raw_status"),
        "receipt_observed": receipt_observed,
        "receipt_successful": receipt_successful,
        "recent_order_count": recent_order_count,
        "recent_order_query_after": recent_order_query_metadata[
            "recent_order_query_after"
        ],
        "recent_order_query_asset_class_filter": recent_order_query_metadata[
            "recent_order_query_asset_class_filter"
        ],
        "recent_order_query_attempted": _recent_order_query_attempted(
            post_orders, order_query_unavailable
        ),
        "recent_order_query_available": _recent_order_query_available(
            post_orders, order_query_unavailable
        ),
        "recent_order_query_contract_version": recent_order_query_metadata[
            "recent_order_query_contract_version"
        ],
        "recent_order_query_direction": recent_order_query_metadata[
            "recent_order_query_direction"
        ],
        "recent_order_query_limit": recent_order_query_metadata[
            "recent_order_query_limit"
        ],
        "recent_order_query_metadata_complete": not recent_order_query_missing_fields,
        "recent_order_query_metadata_missing_fields": list(
            recent_order_query_missing_fields
        ),
        "recent_order_query_nested": recent_order_query_metadata[
            "recent_order_query_nested"
        ],
        "recent_order_query_returned_count": (
            recent_order_count if post_orders else None
        ),
        "recent_order_query_side_filter": recent_order_query_metadata[
            "recent_order_query_side_filter"
        ],
        "recent_order_query_sort": recent_order_query_metadata[
            "recent_order_query_sort"
        ],
        "recent_order_query_source": recent_order_query_metadata[
            "recent_order_query_source"
        ],
        "recent_order_query_status_filter": recent_order_query_metadata[
            "recent_order_query_status_filter"
        ],
        "recent_order_query_symbol_filter": recent_order_query_metadata[
            "recent_order_query_symbol_filter"
        ],
        "recent_order_query_until": recent_order_query_metadata[
            "recent_order_query_until"
        ],
        "recent_order_observed_for_target": target_recent_order_observed,
        "side": _record_code(source_record, "side"),
        "submit_attempt_count": len(submit_attempt_indices),
        "submit_failed_before_response": _submit_failed_before_response(
            submit_attempt_count=len(submit_attempt_indices),
            receipt_observed=receipt_observed,
            source_record=source_record,
        ),
        "submitted": _record_bool(source_record, "submitted"),
        "symbol": target_symbol,
        "target_position_average_price": (
            target_position.get("average_price") if target_position else ""
        ),
        "target_position_observed": target_position is not None,
        "target_position_quantity": (
            target_position.get("quantity") if target_position else ""
        ),
        "target_receipt_client_order_id": receipt_client_order_id,
        "target_receipt_observed": receipt_observed,
        "target_receipt_order_id": receipt_order_id,
        "target_recent_order_match_basis": target_recent_order_match_basis,
        "target_recent_order_match_observed": (
            target_recent_order_match_basis != "none"
        ),
        "time_in_force": _record_code(source_record, "time_in_force"),
        "unavailable_observations": list(unavailable_observations),
    }


def _submit_observation_state(
    submit_observation: Mapping[str, object],
    missing_observations: Sequence[str],
) -> str:
    if bool(submit_observation.get("broker_rejected")):
        return STATE_BROKER_REJECTED
    if bool(submit_observation.get("submit_failed_before_response")):
        return STATE_SUBMIT_FAILED_BEFORE_RESPONSE
    if bool(submit_observation.get("receipt_observed")):
        if not bool(submit_observation.get("has_post_submit_observation")):
            return STATE_INSUFFICIENT_OBSERVATION
        if bool(submit_observation.get("target_position_observed")):
            if bool(submit_observation.get("order_list_observation_gap")):
                return STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP
            return STATE_RECEIPT_AND_POSITION_OBSERVED
        return STATE_RECEIPT_OBSERVED_WITHOUT_POSITION
    if bool(submit_observation.get("target_position_observed")):
        return STATE_POSITION_OBSERVED_WITHOUT_RECEIPT
    if missing_observations:
        return STATE_INSUFFICIENT_OBSERVATION

    return STATE_INSUFFICIENT_OBSERVATION


def _post_receipt_reconciliation(
    state: str,
    submit_observation: Mapping[str, object],
) -> dict[str, object]:
    confidence = _reconciliation_confidence(state, submit_observation)
    return {
        "receipt_observed": submit_observation.get("receipt_observed"),
        "receipt_state": state,
        "broker_response_received": submit_observation.get(
            "broker_response_received"
        ),
        "broker_response_parsed": submit_observation.get("broker_response_parsed"),
        "submitted": submit_observation.get("submitted"),
        "accepted": submit_observation.get("accepted"),
        "filled": submit_observation.get("filled"),
        "raw_status": submit_observation.get("raw_status"),
        "normalized_status": submit_observation.get("normalized_status"),
        "asset_class": submit_observation.get("asset_class"),
        "symbol": submit_observation.get("symbol"),
        "side": submit_observation.get("side"),
        "notional": submit_observation.get("notional"),
        "max_notional": submit_observation.get("max_notional"),
        "min_notional": submit_observation.get("min_notional"),
        "pre_submit_cash": submit_observation.get("pre_submit_cash"),
        "post_submit_cash": submit_observation.get("post_submit_cash"),
        "cash_delta": submit_observation.get("cash_delta"),
        "position_observed": submit_observation.get("target_position_observed"),
        "position_quantity": submit_observation.get("target_position_quantity"),
        "position_average_price": submit_observation.get(
            "target_position_average_price"
        ),
        "recent_order_query_contract_version": submit_observation.get(
            "recent_order_query_contract_version"
        ),
        "recent_order_query_metadata_complete": submit_observation.get(
            "recent_order_query_metadata_complete"
        ),
        "recent_order_query_metadata_missing_fields": list(
            _sequence(
                submit_observation.get("recent_order_query_metadata_missing_fields")
            )
        ),
        "recent_order_query_returned_count": submit_observation.get(
            "recent_order_query_returned_count"
        ),
        "recent_order_match_observed": submit_observation.get(
            "target_recent_order_match_observed"
        ),
        "recent_order_match_basis": submit_observation.get(
            "target_recent_order_match_basis"
        ),
        "order_list_gap": submit_observation.get("order_list_observation_gap"),
        "order_list_gap_reason": submit_observation.get("order_list_gap_reason"),
        "reconciliation_confidence": confidence,
        "reconciliation_limitations": _reconciliation_limitations(
            confidence,
            submit_observation,
        ),
        "recommended_next_operator_action": _reconciliation_operator_action(
            confidence,
            submit_observation,
        ),
    }


def _paper_close_post_action_reconciliation(
    run_log_path: str | Path | None,
    *,
    selected_records: Sequence[Mapping[str, Any]],
) -> dict[str, object]:
    evidence_records, missing_sources, invalid_sources = (
        _paper_close_post_action_evidence_records(run_log_path)
    )
    pre_submit_records = evidence_records["pre_submit"]
    close_probe_records = evidence_records["close_probe"]
    post_close_records = evidence_records["post_close"]
    followup_records = tuple(selected_records)
    close_source = _paper_close_submit_source(close_probe_records)
    submit_attempt_count = len(
        _event_indices(close_probe_records, PAPER_ORDER_SUBMIT_ATTEMPTED)
    )
    symbol = _record_symbol(close_source, "symbol") or "BTCUSD"
    asset_class = _record_code(close_source, "asset_class") or "crypto"
    side = _record_code(close_source, "side") or "sell"
    intended_close_quantity = (
        _record_money(close_source, "qty")
        or _record_money(close_source, "quantity")
        or _record_money(close_source, "max_quantity")
    )
    pre_submit_position = _snapshot_position_state(pre_submit_records, symbol)
    post_close_position = _snapshot_position_state(post_close_records, symbol)
    followup_position = _snapshot_position_state(followup_records, symbol)
    followup_orders = _snapshot_recent_order_state(followup_records)

    pre_submit_position_quantity = _value_or_empty(
        pre_submit_position["remaining_quantity"]
    ) or _record_money(close_source, "target_position_quantity")
    broker_order_id_available = bool(_record_receipt_order_id(close_source))
    broker_result_classification = _broker_result_classification(close_source)
    filled_from_submit_response = _record_bool(close_source, "filled")
    recent_open_order_count = followup_orders["recent_open_order_count"]
    recent_order_query_metadata_complete = (
        followup_orders["recent_order_query_metadata_complete"] is True
    )
    redaction_marker_present = _required_redaction_markers_present(
        (
            pre_submit_records,
            close_probe_records,
            post_close_records,
            followup_records,
        )
    )
    unavailable_observations = _unavailable_observations(
        (
            *pre_submit_records,
            *post_close_records,
            *followup_records,
        )
    )
    required_observations_available = (
        _required_snapshot_observations_available(pre_submit_records)
        and _required_snapshot_observations_available(post_close_records)
        and _required_snapshot_observations_available(followup_records)
    )
    evidence_available = bool(close_source) and not (
        missing_sources
        or invalid_sources
        or unavailable_observations
        or not required_observations_available
        or not recent_order_query_metadata_complete
        or not redaction_marker_present
    )

    submitted = _record_bool(close_source, "submitted")
    accepted_response = (
        submitted is True
        and _record_bool(close_source, "broker_response_received") is True
        and _record_bool(close_source, "broker_response_parsed") is True
        and broker_result_classification == "accepted"
    )
    post_close_position_present = post_close_position["position_present"]
    followup_position_present = followup_position["position_present"]

    if not evidence_available:
        reconciliation_state = STATE_OBSERVATION_UNAVAILABLE
        reconciliation_confidence = _PAPER_CLOSE_POST_ACTION_CONFIDENCE_UNAVAILABLE
        recommended_next_operator_action = _PAPER_CLOSE_POST_ACTION_NEXT_COLLECT_READ_ONLY
    elif (
        post_close_position_present is True
        or followup_position_present is True
        or _positive_count(recent_open_order_count)
    ):
        reconciliation_state = _PAPER_CLOSE_POST_ACTION_STATE_REQUIRES_MANUAL_REVIEW
        reconciliation_confidence = _PAPER_CLOSE_POST_ACTION_CONFIDENCE_MANUAL_REVIEW
        recommended_next_operator_action = _PAPER_CLOSE_POST_ACTION_NEXT_MANUAL_REVIEW
    elif (
        accepted_response
        and post_close_position_present is False
        and followup_position_present is False
        and recent_open_order_count == 0
    ):
        reconciliation_state = (
            _PAPER_CLOSE_POST_ACTION_STATE_ACCEPTED_ABSENT_NO_OPEN_ORDERS
        )
        reconciliation_confidence = (
            _PAPER_CLOSE_POST_ACTION_CONFIDENCE_MEDIUM_POSITION_ABSENT
        )
        recommended_next_operator_action = (
            _PAPER_CLOSE_POST_ACTION_NEXT_READ_ONLY_REVIEW
        )
    else:
        reconciliation_state = STATE_OBSERVATION_UNAVAILABLE
        reconciliation_confidence = _PAPER_CLOSE_POST_ACTION_CONFIDENCE_UNAVAILABLE
        recommended_next_operator_action = _PAPER_CLOSE_POST_ACTION_NEXT_COLLECT_READ_ONLY

    return {
        "reconciliation_scope": _PAPER_CLOSE_POST_ACTION_RECONCILIATION_SCOPE,
        "symbol": symbol,
        "asset_class": asset_class,
        "side": side,
        "intended_close_quantity": intended_close_quantity,
        "pre_submit_position_quantity": pre_submit_position_quantity,
        "submitted": submitted,
        "submit_attempt_count": submit_attempt_count,
        "broker_response_received": _record_bool(
            close_source, "broker_response_received"
        ),
        "broker_response_parsed": _record_bool(
            close_source, "broker_response_parsed"
        ),
        "broker_result_classification": broker_result_classification,
        "normalized_status": _record_status(
            close_source, "normalized_status", "broker_normalized_status"
        ),
        "raw_status": _record_status(
            close_source, "raw_status", "broker_raw_status"
        ),
        "filled_from_submit_response": filled_from_submit_response,
        "client_order_id": _record_correlation_id(close_source, "client_order_id"),
        "broker_order_id_available": broker_order_id_available,
        "post_close_position_present": post_close_position_present,
        "post_close_remaining_quantity": post_close_position["remaining_quantity"],
        "followup_position_present": followup_position_present,
        "followup_remaining_quantity": followup_position["remaining_quantity"],
        "recent_open_order_count": recent_open_order_count,
        "recent_order_query_metadata_complete": recent_order_query_metadata_complete,
        "redaction_marker_present": redaction_marker_present,
        "reconciliation_state": reconciliation_state,
        "reconciliation_confidence": reconciliation_confidence,
        "limitations": _paper_close_post_action_limitations(
            missing_sources=missing_sources,
            invalid_sources=invalid_sources,
            unavailable_observations=unavailable_observations,
            required_observations_available=required_observations_available,
            recent_order_query_metadata_complete=(
                recent_order_query_metadata_complete
            ),
            redaction_marker_present=redaction_marker_present,
            filled_from_submit_response=filled_from_submit_response,
            broker_order_id_available=broker_order_id_available,
            post_close_position_present=post_close_position_present,
            followup_position_present=followup_position_present,
            recent_open_order_count=recent_open_order_count,
        ),
        "recommended_next_operator_action": recommended_next_operator_action,
    }


def _paper_close_post_action_evidence_records(
    run_log_path: str | Path | None,
) -> tuple[dict[str, tuple[Mapping[str, Any], ...]], list[str], list[str]]:
    sources = {
        "pre_submit": _PAPER_CLOSE_POST_ACTION_PRE_SUBMIT_LOG,
        "close_probe": _PAPER_CLOSE_POST_ACTION_CLOSE_PROBE_LOG,
        "post_close": _PAPER_CLOSE_POST_ACTION_POST_CLOSE_LOG,
    }
    records_by_source: dict[str, tuple[Mapping[str, Any], ...]] = {}
    missing_sources: list[str] = []
    invalid_sources: list[str] = []
    if run_log_path is None:
        return (
            {name: () for name in sources},
            list(sources),
            [],
        )

    evidence_dir = Path(run_log_path).parent
    for source_name, file_name in sources.items():
        path = evidence_dir / file_name
        if not path.exists():
            records_by_source[source_name] = ()
            missing_sources.append(source_name)
            continue
        records, invalid_reasons = _read_jsonl_records(path)
        records_by_source[source_name] = tuple(records)
        if invalid_reasons:
            invalid_sources.append(source_name)

    return records_by_source, missing_sources, invalid_sources


def _paper_close_submit_source(
    records: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    return _latest_record(records, PAPER_ORDER_RECEIPT_OBSERVED) or _latest_record(
        records, PAPER_ORDER_SUBMIT_ATTEMPTED
    )


def _snapshot_position_state(
    records: Sequence[Mapping[str, Any]],
    symbol: str,
) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED)
    if record is None:
        return {
            "positions_observed": False,
            "position_present": None,
            "remaining_quantity": "",
        }

    positions = _safe_positions(record.get("positions"))
    target_position = _target_position(positions, symbol)
    if target_position is not None:
        return {
            "positions_observed": True,
            "position_present": True,
            "remaining_quantity": target_position.get("quantity", ""),
        }

    if symbol in _post_submit_position_symbols(record):
        return {
            "positions_observed": True,
            "position_present": True,
            "remaining_quantity": "",
        }

    return {
        "positions_observed": True,
        "position_present": False,
        "remaining_quantity": "0",
    }


def _snapshot_recent_order_state(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, object]:
    record = _latest_record(records, PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED)
    if record is None:
        return {
            "orders_observed": False,
            "recent_open_order_count": None,
            "recent_order_query_metadata_complete": False,
        }

    recent_orders = [
        order for order in _sequence(record.get("recent_orders")) if isinstance(order, Mapping)
    ]
    missing_metadata = _recent_order_query_metadata_missing_fields(record)
    return {
        "orders_observed": True,
        "recent_open_order_count": _safe_count(
            record.get("recent_order_count"), len(recent_orders)
        ),
        "recent_order_query_metadata_complete": not missing_metadata,
    }


def _broker_result_classification(record: Mapping[str, Any] | None) -> str:
    explicit = _record_code(record, "broker_result_classification")
    if explicit:
        return explicit
    accepted = _record_bool(record, "accepted")
    if accepted is True:
        return "accepted"
    if accepted is False:
        return "rejected"
    normalized_status = _record_status(
        record, "normalized_status", "broker_normalized_status"
    ).lower()
    if normalized_status in _ACCEPTED_RECEIPT_STATUSES:
        return "accepted"
    if normalized_status in _REJECTED_RECEIPT_STATUSES:
        return "rejected"

    return ""


def _required_snapshot_observations_available(
    records: Sequence[Mapping[str, Any]],
) -> bool:
    observations = _observations(records)
    return observations["account"] and observations["positions"] and observations["orders"]


def _required_redaction_markers_present(
    record_groups: Sequence[Sequence[Mapping[str, Any]]],
) -> bool:
    return all(_redaction_markers(records) for records in record_groups)


def _positive_count(value: object) -> bool:
    return isinstance(value, int) and value > 0


def _value_or_empty(value: object) -> str:
    text = _text(value)
    return "" if text == "None" else text


def _paper_close_post_action_limitations(
    *,
    missing_sources: Sequence[str],
    invalid_sources: Sequence[str],
    unavailable_observations: Sequence[str],
    required_observations_available: bool,
    recent_order_query_metadata_complete: bool,
    redaction_marker_present: bool,
    filled_from_submit_response: bool | None,
    broker_order_id_available: bool,
    post_close_position_present: object,
    followup_position_present: object,
    recent_open_order_count: object,
) -> list[str]:
    limitations: list[str] = []
    if missing_sources:
        limitations.append(
            "required local evidence files are missing: "
            + ",".join(sorted(missing_sources))
        )
    if invalid_sources:
        limitations.append(
            "required local evidence files could not be parsed: "
            + ",".join(sorted(invalid_sources))
        )
    if unavailable_observations:
        limitations.append(
            "broker observations unavailable: "
            + ",".join(sorted(unavailable_observations))
        )
    if not required_observations_available:
        limitations.append(
            "required account, position, or order observations are incomplete"
        )
    if filled_from_submit_response is not True:
        limitations.append("submit response did not report filled=true")
    if not broker_order_id_available:
        limitations.append(
            "broker order id was not exposed by the normalized mapper"
        )
    if not recent_order_query_metadata_complete:
        limitations.append(
            "recent order query metadata is incomplete; local evidence does not "
            "prove external broker order state"
        )
    if not redaction_marker_present:
        limitations.append(
            "redaction marker missing from required local evidence"
        )
    if post_close_position_present is True:
        limitations.append("M331 post-close snapshot still showed BTCUSD")
    if followup_position_present is True:
        limitations.append("M332 follow-up snapshot showed BTCUSD")
    if _positive_count(recent_open_order_count):
        limitations.append("recent open orders were observed")
    if (
        filled_from_submit_response is not True
        or not broker_order_id_available
        or not recent_order_query_metadata_complete
    ):
        limitations.append(
            "position-based reconciliation only; do not claim final settlement"
        )

    return limitations


def _reconciliation_confidence(
    state: str,
    submit_observation: Mapping[str, object],
) -> str:
    if state == STATE_INVALID_RUN_LOG:
        return _RECONCILIATION_CONFIDENCE_INVALID
    if state == STATE_OBSERVATION_UNAVAILABLE:
        return _RECONCILIATION_CONFIDENCE_UNAVAILABLE
    if not bool(submit_observation.get("has_submit_context")):
        return _RECONCILIATION_CONFIDENCE_UNAVAILABLE

    receipt_observed = bool(submit_observation.get("receipt_observed"))
    position_observed = bool(submit_observation.get("target_position_observed"))
    cash_observed = _cash_movement_observed(submit_observation)
    order_list_gap = bool(submit_observation.get("order_list_observation_gap"))
    recent_order_match_observed = bool(
        submit_observation.get("target_recent_order_match_observed")
    )

    if receipt_observed and position_observed:
        if order_list_gap:
            return (
                _RECONCILIATION_CONFIDENCE_MEDIUM_RECEIPT_POSITION_OBSERVED_ORDER_GAP
            )
        if cash_observed and recent_order_match_observed:
            return _RECONCILIATION_CONFIDENCE_HIGH_RECEIPT_POSITION_CASH_OBSERVED
        return _RECONCILIATION_CONFIDENCE_UNAVAILABLE
    if receipt_observed:
        return _RECONCILIATION_CONFIDENCE_LOW_RECEIPT_ONLY
    if position_observed:
        return _RECONCILIATION_CONFIDENCE_LOW_POSITION_ONLY

    return _RECONCILIATION_CONFIDENCE_UNAVAILABLE


def _cash_movement_observed(submit_observation: Mapping[str, object]) -> bool:
    pre_cash = _text(submit_observation.get("pre_submit_cash"))
    post_cash = _text(submit_observation.get("post_submit_cash"))
    cash_delta = _text(submit_observation.get("cash_delta"))
    return bool(pre_cash and post_cash and cash_delta and cash_delta != "<redacted>")


def _reconciliation_limitations(
    confidence: str,
    submit_observation: Mapping[str, object],
) -> list[str]:
    limitations: list[str] = []
    order_gap_reason = _text(submit_observation.get("order_list_gap_reason"))
    metadata_complete = submit_observation.get("recent_order_query_metadata_complete")

    if confidence == _RECONCILIATION_CONFIDENCE_INVALID:
        limitations.append(
            "run log could not be parsed; reconciliation uses invalid state only"
        )
        return limitations
    if confidence == _RECONCILIATION_CONFIDENCE_UNAVAILABLE:
        limitations.append(
            "required receipt, position, cash, or order observations are unavailable"
        )
    elif confidence == (
        _RECONCILIATION_CONFIDENCE_MEDIUM_RECEIPT_POSITION_OBSERVED_ORDER_GAP
    ):
        if _cash_movement_observed(submit_observation):
            limitations.append(
                "broker receipt, cash movement, and target position were observed, "
                "but the recent-order list did not include the order"
            )
        else:
            limitations.append(
                "broker receipt and target position were observed, but cash movement "
                "or recent-order match evidence is incomplete"
            )
    elif confidence == _RECONCILIATION_CONFIDENCE_LOW_RECEIPT_ONLY:
        limitations.append(
            "broker receipt was observed without a post-submit target position"
        )
    elif confidence == _RECONCILIATION_CONFIDENCE_LOW_POSITION_ONLY:
        limitations.append(
            "target position was observed without a broker receipt in the run log"
        )

    if metadata_complete is not True:
        limitations.append(
            "recent order query metadata is incomplete; local evidence does not "
            "prove external broker order state"
        )
    if order_gap_reason:
        limitations.append(f"order-list gap reason: {order_gap_reason}")

    return limitations


def _reconciliation_operator_action(
    confidence: str,
    submit_observation: Mapping[str, object],
) -> str:
    if confidence == _RECONCILIATION_CONFIDENCE_INVALID:
        return _RECONCILIATION_ACTION_REPAIR_LOCAL_RUN_LOG
    if confidence == _RECONCILIATION_CONFIDENCE_UNAVAILABLE:
        return _RECONCILIATION_ACTION_COLLECT_READ_ONLY_OBSERVATIONS
    if bool(submit_observation.get("order_list_observation_gap")):
        return _RECONCILIATION_ACTION_FRESH_SNAPSHOT_BEFORE_CLOSE
    if confidence in {
        _RECONCILIATION_CONFIDENCE_LOW_RECEIPT_ONLY,
        _RECONCILIATION_CONFIDENCE_LOW_POSITION_ONLY,
    }:
        return _RECONCILIATION_ACTION_COLLECT_READ_ONLY_OBSERVATIONS

    return _RECONCILIATION_ACTION_MANUAL_REVIEW_ONLY


def _latest_record(
    records: Sequence[Mapping[str, Any]],
    event_type: str,
) -> Mapping[str, Any] | None:
    for record in reversed(records):
        if _safe_event_type(record.get("event_type")) == event_type:
            return record

    return None


def _event_indices(
    records: Sequence[Mapping[str, Any]],
    event_type: str,
) -> tuple[int, ...]:
    return tuple(
        index
        for index, record in enumerate(records)
        if _safe_event_type(record.get("event_type")) == event_type
    )


def _latest_event_before(
    records: Sequence[Mapping[str, Any]],
    event_type: str,
    index: int | None,
) -> Mapping[str, Any] | None:
    if index is None:
        return None
    for record in reversed(records[:index]):
        if _safe_event_type(record.get("event_type")) == event_type:
            return record

    return None


def _latest_event_after(
    records: Sequence[Mapping[str, Any]],
    event_type: str,
    index: int | None,
) -> Mapping[str, Any] | None:
    candidates = records if index is None else records[index + 1 :]
    for record in reversed(candidates):
        if _safe_event_type(record.get("event_type")) == event_type:
            return record

    return None


def _target_symbol(
    records: Sequence[Mapping[str, Any]],
    source_record: Mapping[str, Any] | None,
) -> str:
    symbol = _record_symbol(source_record, "symbol")
    if symbol:
        return symbol
    for record in reversed(records):
        symbol = _record_symbol(record, "symbol")
        if symbol:
            return symbol
    for record in reversed(records):
        symbols = _post_submit_position_symbols(record)
        if len(symbols) == 1:
            return symbols[0]

    return ""


def _account_cash(record: Mapping[str, Any] | None) -> str:
    account = _mapping(record.get("account") if record else None)
    return _safe_money(account.get("cash"))


def _position_count(record: Mapping[str, Any] | None) -> int | None:
    if record is None:
        return None
    symbols = _post_submit_position_symbols(record)
    return _safe_count(record.get("position_count"), len(symbols))


def _post_submit_position_symbols(record: Mapping[str, Any] | None) -> list[str]:
    if record is None:
        return []
    symbols = _safe_symbols(record.get("position_symbols"))
    if not symbols:
        symbols = _symbols_from_positions(record.get("positions"))
    return sorted(dict.fromkeys(symbols))


def _safe_positions(value: Any) -> list[dict[str, str]]:
    positions: list[dict[str, str]] = []
    for position in _sequence(value):
        if not isinstance(position, Mapping):
            continue
        symbol = _safe_symbol(position.get("symbol"))
        if not symbol:
            continue
        positions.append(
            {
                "average_price": _safe_money(position.get("average_price")),
                "quantity": _safe_money(position.get("quantity")),
                "symbol": symbol,
            }
        )

    return positions


def _target_position(
    positions: Sequence[Mapping[str, str]],
    target_symbol: str,
) -> Mapping[str, str] | None:
    if not target_symbol:
        return None
    for position in positions:
        if position.get("symbol") == target_symbol:
            return position

    return None


def _target_recent_order_match_basis(
    statuses: Sequence[Mapping[str, str]],
    *,
    target_symbol: str,
    target_side: str,
    target_notional: str,
    receipt_client_order_id: str,
    receipt_order_id: str,
) -> str:
    if receipt_client_order_id and any(
        status.get("client_order_id") == receipt_client_order_id
        for status in statuses
    ):
        return "client_order_id"
    if receipt_order_id and any(
        _status_order_id(status) == receipt_order_id for status in statuses
    ):
        return "broker_order_id"
    if target_symbol and target_side and target_notional and any(
        status.get("symbol") == target_symbol
        and status.get("side") == target_side
        and status.get("notional") == target_notional
        for status in statuses
    ):
        return "symbol_side_notional"

    return "none"


def _status_order_id(status: Mapping[str, str]) -> str:
    return status.get("order_id") or status.get("broker_order_id") or ""


def _order_list_gap_reason(
    *,
    order_list_observation_gap: bool,
    order_query_unavailable: bool,
    recent_order_count: int | None,
    recent_order_statuses: Sequence[Mapping[str, str]],
    receipt_client_order_id: str,
    receipt_order_id: str,
    target_notional: str,
    target_recent_order_match_basis: str,
    target_side: str,
    target_symbol: str,
) -> str:
    if not order_list_observation_gap:
        return ""
    if order_query_unavailable:
        return _ORDER_LIST_GAP_REASON_ORDER_QUERY_UNAVAILABLE
    if target_recent_order_match_basis != "none":
        return ""
    if recent_order_count == 0:
        return _ORDER_LIST_GAP_REASON_RECENT_ORDER_QUERY_RETURNED_EMPTY
    if not receipt_client_order_id and not receipt_order_id:
        return _ORDER_LIST_GAP_REASON_RECEIPT_MISSING_CORRELATION_ID
    if not _has_recent_order_match_metadata(
        recent_order_statuses,
        target_notional=target_notional,
        target_side=target_side,
        target_symbol=target_symbol,
    ):
        return _ORDER_LIST_GAP_REASON_INSUFFICIENT_ORDER_QUERY_METADATA

    return _ORDER_LIST_GAP_REASON_TARGET_ORDER_NOT_IN_RECENT_ORDER_RESULTS


def _has_recent_order_match_metadata(
    statuses: Sequence[Mapping[str, str]],
    *,
    target_notional: str,
    target_side: str,
    target_symbol: str,
) -> bool:
    for status in statuses:
        if status.get("client_order_id") or _status_order_id(status):
            return True
        if (
            target_symbol
            and target_side
            and target_notional
            and status.get("symbol")
            and status.get("side")
            and status.get("notional")
        ):
            return True

    return False


def _recent_order_query_attempted(
    post_orders: Mapping[str, Any] | None,
    order_query_unavailable: bool,
) -> bool | None:
    if post_orders is None:
        return True if order_query_unavailable else None
    attempted = _record_bool(post_orders, "recent_order_query_attempted")
    return True if attempted is None else attempted


def _recent_order_query_available(
    post_orders: Mapping[str, Any] | None,
    order_query_unavailable: bool,
) -> bool | None:
    if post_orders is None:
        return False if order_query_unavailable else None
    available = _record_bool(post_orders, "recent_order_query_available")
    return True if available is None else available


def _recent_order_query_metadata(
    post_orders: Mapping[str, Any] | None,
) -> dict[str, object]:
    return {
        field: _recent_order_query_metadata_value(post_orders, field)
        for field in _RECENT_ORDER_QUERY_METADATA_FIELDS
    }


def _recent_order_query_metadata_value(
    post_orders: Mapping[str, Any] | None,
    field: str,
) -> object:
    if post_orders is None:
        return None if field in _RECENT_ORDER_QUERY_NULLABLE_FIELDS else ""
    if field == "recent_order_query_asset_class_filter":
        value = post_orders.get(field)
        if value in (None, ""):
            value = post_orders.get("recent_order_query_asset_filter")
        return _safe_status_value(value)
    if field == "recent_order_query_limit":
        return _safe_optional_count(post_orders.get(field))
    if field == "recent_order_query_nested":
        return _record_bool(post_orders, field)
    if field in _RECENT_ORDER_QUERY_NULLABLE_FIELDS:
        value = post_orders.get(field)
        return None if value in (None, "") else _safe_status_value(value)

    return _safe_status_value(post_orders.get(field))


_RECENT_ORDER_QUERY_NULLABLE_FIELDS = frozenset(
    ("recent_order_query_after", "recent_order_query_until")
)


def _recent_order_query_metadata_missing_fields(
    post_orders: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    if post_orders is None:
        return _RECENT_ORDER_QUERY_METADATA_FIELDS

    missing_fields: list[str] = []
    for field in _RECENT_ORDER_QUERY_METADATA_FIELDS:
        if field not in post_orders:
            missing_fields.append(field)
            continue
        if field in _RECENT_ORDER_QUERY_REQUIRED_METADATA_FIELDS and _is_missing_query_metadata(
            post_orders.get(field)
        ):
            missing_fields.append(field)

    return tuple(missing_fields)


def _is_missing_query_metadata(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip()
        return not text or text == "unspecified"
    return False


def _record_correlation_id(record: Mapping[str, Any] | None, key: str) -> str:
    return _safe_status_value(record.get(key) if record else None)


def _record_receipt_order_id(record: Mapping[str, Any] | None) -> str:
    if record is None:
        return ""
    for key in ("order_id", "broker_order_id"):
        value = _safe_status_value(record.get(key))
        if value:
            return value
    broker_result = _mapping(record.get("broker_result"))
    for key in ("order_id", "broker_order_id", "id"):
        value = _safe_status_value(broker_result.get(key))
        if value:
            return value

    return ""


def _receipt_successful(
    *,
    receipt_observed: bool,
    accepted: bool | None,
    normalized_status: str,
) -> bool:
    if not receipt_observed:
        return False
    if accepted is True:
        return True
    return normalized_status.lower() in _ACCEPTED_RECEIPT_STATUSES


def _broker_rejected(
    *,
    receipt_observed: bool,
    accepted: bool | None,
    normalized_status: str,
) -> bool:
    if not receipt_observed:
        return False
    if accepted is False:
        return True
    return normalized_status.lower() in _REJECTED_RECEIPT_STATUSES


def _submit_failed_before_response(
    *,
    submit_attempt_count: int,
    receipt_observed: bool,
    source_record: Mapping[str, Any] | None,
) -> bool:
    if submit_attempt_count <= 0 or receipt_observed:
        return False
    if _record_bool(source_record, "broker_response_received") is True:
        return False
    stage = _record_code(source_record, "submit_error_stage")
    if stage == "submit_call_failed_before_response":
        return True
    return _safe_event_type(source_record.get("event_type") if source_record else "") in {
        PAPER_ORDER_SUBMIT_ATTEMPTED,
        PAPER_ORDER_SUBMIT_FAILED,
    }


def _decimal_delta(before: str, after: str) -> str:
    before_decimal = _decimal_from_money(before)
    after_decimal = _decimal_from_money(after)
    if before_decimal is None or after_decimal is None:
        return ""
    return str(after_decimal - before_decimal)


def _decimal_from_money(value: str) -> Decimal | None:
    if not value or value == "<redacted>":
        return None
    try:
        return Decimal(value.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _unavailable_observations(
    records: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    names: set[str] = set()
    for record in records:
        names.update(_safe_observation_names(record.get("unavailable_observations")))
    return tuple(sorted(names))


def _record_bool(record: Mapping[str, Any] | None, key: str) -> bool | None:
    if record is None or key not in record:
        return None
    value = record.get(key)
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    text = _text(value).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False

    return None


def _record_code(record: Mapping[str, Any] | None, key: str) -> str:
    return _safe_code(record.get(key) if record else None)


def _record_symbol(record: Mapping[str, Any] | None, key: str) -> str:
    return _safe_symbol(record.get(key) if record else None)


def _record_money(record: Mapping[str, Any] | None, key: str) -> str:
    return _safe_money(record.get(key) if record else None)


def _record_status(
    record: Mapping[str, Any] | None,
    key: str,
    fallback_key: str,
) -> str:
    if record is None:
        return ""
    value = record.get(key)
    if value in (None, ""):
        value = record.get(fallback_key)
    return _safe_status_value(value)


def _event_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counter = Counter(_safe_event_type(record.get("event_type")) for record in records)
    ordered: dict[str, int] = {}
    for event_type in EVENT_TYPES:
        if counter[event_type]:
            ordered[event_type] = counter[event_type]
    for event_type in sorted(set(counter) - set(EVENT_TYPES)):
        if counter[event_type]:
            ordered[event_type] = counter[event_type]

    return ordered


def _unavailable_or_error_events(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for record in records:
        event_type = _safe_event_type(record.get("event_type"))
        error = _safe_code(record.get("error"))
        if not (
            event_type == PAPER_LAB_SNAPSHOT_UNAVAILABLE
            or event_type.endswith(("_failed", "_unavailable", "_parse_failed"))
            or bool(error)
        ):
            continue
        event: dict[str, object] = {"event_type": event_type}
        if error:
            event["error"] = error
        unavailable_observations = _safe_observation_names(
            record.get("unavailable_observations")
        )
        if unavailable_observations:
            event["unavailable_observations"] = list(unavailable_observations)
        reasons = _safe_unavailable_reasons(record.get("unavailable_reasons"))
        if reasons:
            event["unavailable_reasons"] = reasons
        error_type = _safe_code(record.get("error_type"))
        if error_type:
            event["error_type"] = error_type
        events.append(event)

    return events


def _has_observation_unavailable(
    unavailable_events: Sequence[Mapping[str, object]],
) -> bool:
    for event in unavailable_events:
        event_type = _text(event.get("event_type"))
        if event_type == PAPER_LAB_SNAPSHOT_UNAVAILABLE:
            return True
        if event_type.endswith("_unavailable"):
            return True
        observations = set(_safe_observation_names(event.get("unavailable_observations")))
        if observations.intersection({"account", "positions", "orders"}):
            return True

    return False


def _safe_unavailable_reasons(value: Any) -> dict[str, dict[str, str]]:
    reasons = _mapping(value)
    safe_reasons: dict[str, dict[str, str]] = {}
    for name, reason in reasons.items():
        reason_payload = _mapping(reason)
        safe_name = _safe_observation_name(name)
        if not safe_name:
            continue
        detail: dict[str, str] = {}
        error_type = _safe_code(reason_payload.get("error_type"))
        if error_type:
            detail["error_type"] = error_type
        markers = _markers_in_value(reason_payload.get("message"))
        if markers:
            detail["message"] = ",".join(markers)
        if detail:
            safe_reasons[safe_name] = detail

    return safe_reasons


def _safe_order_status(order: Mapping[str, Any]) -> dict[str, str]:
    return {
        field: _safe_status_value(order.get(field))
        for field in _SAFE_ORDER_STATUS_FIELDS
        if field in order
    }


def _safe_symbols(value: Any) -> tuple[str, ...]:
    return tuple(
        symbol
        for symbol in (_safe_symbol(item) for item in _sequence(value))
        if symbol
    )


def _symbols_from_positions(value: Any) -> tuple[str, ...]:
    symbols: list[str] = []
    for position in _sequence(value):
        if not isinstance(position, Mapping):
            continue
        symbol = _safe_symbol(position.get("symbol"))
        if symbol:
            symbols.append(symbol)

    return tuple(symbols)


def _safe_observation_names(value: Any) -> tuple[str, ...]:
    return tuple(
        name
        for name in (_safe_observation_name(item) for item in _sequence(value))
        if name
    )


def _safe_observation_name(value: Any) -> str:
    text = _text(value)
    if text in {"account", "positions", "orders", "broker"}:
        return text

    return ""


def _safe_count(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int) and value >= 0:
        return value
    text = _text(value)
    if text.isdigit():
        return int(text)

    return fallback


def _safe_optional_count(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    text = _text(value)
    if text.isdigit():
        return int(text)

    return None


def _safe_run_id(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if _is_secret_like(text):
        return "<redacted>"

    return text[:96]


def _safe_symbol(value: Any) -> str:
    text = _text(value).upper()
    if not _SAFE_CODE_RE.fullmatch(text) or _is_secret_like(text):
        return ""

    return text


def _safe_event_type(value: Any) -> str:
    text = _text(value)
    if not text:
        return "missing_event_type"
    if not _SAFE_CODE_RE.fullmatch(text) or _is_secret_like(text):
        return "redacted_event_type"

    return text


def _safe_status_value(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if _is_secret_like(text):
        return "<redacted>"

    return text[:160]


def _safe_code(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if not _SAFE_CODE_RE.fullmatch(text) or _is_secret_like(text):
        return "<redacted>"

    return text


def _safe_money(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if _SAFE_MONEY_RE.fullmatch(text):
        return text

    return "<redacted>"


def _redaction_markers(records: Sequence[Mapping[str, Any]]) -> list[str]:
    markers: set[str] = set()
    for record in records:
        markers.update(_markers_in_value(record))

    return sorted(markers)


def _markers_in_value(value: Any) -> tuple[str, ...]:
    markers: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            markers.update(_markers_in_value(item))
    elif isinstance(value, list):
        for item in value:
            markers.update(_markers_in_value(item))
    elif isinstance(value, str):
        for marker in _REDACTION_MARKERS:
            if marker in value:
                markers.add(marker)

    return tuple(sorted(markers))


def _event_count_lines(event_counts: Mapping[str, object]) -> list[str]:
    if not event_counts:
        return ["event_counts: none"]

    return [
        f"event_count: {event_type}={event_counts[event_type]}"
        for event_type in event_counts
    ]


def _post_receipt_reconciliation_lines(
    reconciliation: Mapping[str, Any],
) -> list[str]:
    return [
        "post_receipt_reconciliation:",
        (
            "  receipt_observed: "
            f"{_tri_bool_text(reconciliation.get('receipt_observed'))}"
        ),
        f"  receipt_state: {_value_text(reconciliation.get('receipt_state'))}",
        (
            "  broker_response_received: "
            f"{_tri_bool_text(reconciliation.get('broker_response_received'))}"
        ),
        (
            "  broker_response_parsed: "
            f"{_tri_bool_text(reconciliation.get('broker_response_parsed'))}"
        ),
        f"  submitted: {_tri_bool_text(reconciliation.get('submitted'))}",
        f"  accepted: {_tri_bool_text(reconciliation.get('accepted'))}",
        f"  filled: {_tri_bool_text(reconciliation.get('filled'))}",
        f"  raw_status: {_value_text(reconciliation.get('raw_status'))}",
        (
            "  normalized_status: "
            f"{_value_text(reconciliation.get('normalized_status'))}"
        ),
        f"  asset_class: {_value_text(reconciliation.get('asset_class'))}",
        f"  symbol: {_value_text(reconciliation.get('symbol'))}",
        f"  side: {_value_text(reconciliation.get('side'))}",
        f"  notional: {_value_text(reconciliation.get('notional'))}",
        f"  max_notional: {_value_text(reconciliation.get('max_notional'))}",
        f"  min_notional: {_value_text(reconciliation.get('min_notional'))}",
        f"  pre_submit_cash: {_value_text(reconciliation.get('pre_submit_cash'))}",
        f"  post_submit_cash: {_value_text(reconciliation.get('post_submit_cash'))}",
        f"  cash_delta: {_value_text(reconciliation.get('cash_delta'))}",
        (
            "  position_observed: "
            f"{_tri_bool_text(reconciliation.get('position_observed'))}"
        ),
        (
            "  position_quantity: "
            f"{_value_text(reconciliation.get('position_quantity'))}"
        ),
        (
            "  position_average_price: "
            f"{_value_text(reconciliation.get('position_average_price'))}"
        ),
        (
            "  recent_order_query_contract_version: "
            f"{_value_text(reconciliation.get('recent_order_query_contract_version'))}"
        ),
        (
            "  recent_order_query_metadata_complete: "
            f"{_tri_bool_text(reconciliation.get('recent_order_query_metadata_complete'))}"
        ),
        (
            "  recent_order_query_metadata_missing_fields: "
            f"{_joined(reconciliation.get('recent_order_query_metadata_missing_fields'))}"
        ),
        (
            "  recent_order_query_returned_count: "
            f"{_value_text(reconciliation.get('recent_order_query_returned_count'))}"
        ),
        (
            "  recent_order_match_observed: "
            f"{_tri_bool_text(reconciliation.get('recent_order_match_observed'))}"
        ),
        (
            "  recent_order_match_basis: "
            f"{_value_text(reconciliation.get('recent_order_match_basis'))}"
        ),
        (
            "  order_list_gap: "
            f"{_tri_bool_text(reconciliation.get('order_list_gap'))}"
        ),
        (
            "  order_list_gap_reason: "
            f"{_value_text(reconciliation.get('order_list_gap_reason'))}"
        ),
        (
            "  reconciliation_confidence: "
            f"{_value_text(reconciliation.get('reconciliation_confidence'))}"
        ),
        (
            "  reconciliation_limitations: "
            f"{_joined(reconciliation.get('reconciliation_limitations'))}"
        ),
        (
            "  recommended_next_operator_action: "
            f"{_value_text(reconciliation.get('recommended_next_operator_action'))}"
        ),
    ]


def _paper_close_post_action_reconciliation_lines(
    reconciliation: Mapping[str, Any],
) -> list[str]:
    return [
        "paper_close_post_action_reconciliation:",
        (
            "  reconciliation_scope: "
            f"{_value_text(reconciliation.get('reconciliation_scope'))}"
        ),
        f"  symbol: {_value_text(reconciliation.get('symbol'))}",
        f"  asset_class: {_value_text(reconciliation.get('asset_class'))}",
        f"  side: {_value_text(reconciliation.get('side'))}",
        (
            "  intended_close_quantity: "
            f"{_value_text(reconciliation.get('intended_close_quantity'))}"
        ),
        (
            "  pre_submit_position_quantity: "
            f"{_value_text(reconciliation.get('pre_submit_position_quantity'))}"
        ),
        f"  submitted: {_tri_bool_text(reconciliation.get('submitted'))}",
        (
            "  submit_attempt_count: "
            f"{_value_text(reconciliation.get('submit_attempt_count'))}"
        ),
        (
            "  broker_response_received: "
            f"{_tri_bool_text(reconciliation.get('broker_response_received'))}"
        ),
        (
            "  broker_response_parsed: "
            f"{_tri_bool_text(reconciliation.get('broker_response_parsed'))}"
        ),
        (
            "  broker_result_classification: "
            f"{_value_text(reconciliation.get('broker_result_classification'))}"
        ),
        (
            "  normalized_status: "
            f"{_value_text(reconciliation.get('normalized_status'))}"
        ),
        f"  raw_status: {_value_text(reconciliation.get('raw_status'))}",
        (
            "  filled_from_submit_response: "
            f"{_tri_bool_text(reconciliation.get('filled_from_submit_response'))}"
        ),
        f"  client_order_id: {_value_text(reconciliation.get('client_order_id'))}",
        (
            "  broker_order_id_available: "
            f"{_bool_text(reconciliation.get('broker_order_id_available'))}"
        ),
        (
            "  post_close_position_present: "
            f"{_tri_bool_text(reconciliation.get('post_close_position_present'))}"
        ),
        (
            "  post_close_remaining_quantity: "
            f"{_value_text(reconciliation.get('post_close_remaining_quantity'))}"
        ),
        (
            "  followup_position_present: "
            f"{_tri_bool_text(reconciliation.get('followup_position_present'))}"
        ),
        (
            "  followup_remaining_quantity: "
            f"{_value_text(reconciliation.get('followup_remaining_quantity'))}"
        ),
        (
            "  recent_open_order_count: "
            f"{_value_text(reconciliation.get('recent_open_order_count'))}"
        ),
        (
            "  recent_order_query_metadata_complete: "
            f"{_bool_text(reconciliation.get('recent_order_query_metadata_complete'))}"
        ),
        (
            "  redaction_marker_present: "
            f"{_bool_text(reconciliation.get('redaction_marker_present'))}"
        ),
        (
            "  reconciliation_state: "
            f"{_value_text(reconciliation.get('reconciliation_state'))}"
        ),
        (
            "  reconciliation_confidence: "
            f"{_value_text(reconciliation.get('reconciliation_confidence'))}"
        ),
        f"  limitations: {_joined(reconciliation.get('limitations'))}",
        (
            "  recommended_next_operator_action: "
            f"{_value_text(reconciliation.get('recommended_next_operator_action'))}"
        ),
    ]


def _fresh_snapshot_operator_checklist_lines(
    checklist: Mapping[str, Any],
) -> list[str]:
    evidence = _mapping(checklist.get("evidence"))
    lines = [
        "fresh_snapshot_operator_checklist:",
        f"  version: {_value_text(checklist.get('version'))}",
        f"  status: {_value_text(checklist.get('status'))}",
        f"  pre_run_status: {_value_text(checklist.get('pre_run_status'))}",
        (
            "  recommended_next_operator_action: "
            f"{_value_text(checklist.get('recommended_next_operator_action'))}"
        ),
        f"  paper_lab_only: {_bool_text(checklist.get('paper_lab_only'))}",
        f"  not_live_authorized: {_bool_text(checklist.get('not_live_authorized'))}",
        f"  profit_claim: {_value_text(checklist.get('profit_claim'))}",
        (
            "  fresh_snapshot_command_template: "
            f"{_value_text(checklist.get('fresh_snapshot_command_template'))}"
        ),
    ]
    for item in _sequence(checklist.get("pre_run_checklist")):
        lines.append(f"  pre_run_check: {_value_text(item)}")
    for item in _sequence(checklist.get("post_run_checklist")):
        lines.append(f"  post_run_check: {_value_text(item)}")
    lines.extend(
        [
            "  evidence:",
            (
                "    snapshot_records_observed: "
                f"{_bool_text(evidence.get('snapshot_records_observed'))}"
            ),
            (
                "    profile_gate_reported: "
                f"{_bool_text(evidence.get('profile_gate_reported'))}"
            ),
            (
                "    profile_gate_status: "
                f"{_value_text(evidence.get('profile_gate_status'))}"
            ),
            f"    ok: {_tri_bool_text(evidence.get('ok'))}",
            f"    mutated: {_tri_bool_text(evidence.get('mutated'))}",
            f"    submitted: {_tri_bool_text(evidence.get('submitted'))}",
            (
                "    account_observation_available: "
                f"{_bool_text(evidence.get('account_observation_available'))}"
            ),
            (
                "    positions_observation_available: "
                f"{_bool_text(evidence.get('positions_observation_available'))}"
            ),
            (
                "    orders_observation_available: "
                f"{_bool_text(evidence.get('orders_observation_available'))}"
            ),
            (
                "    account_cash_observed: "
                f"{_bool_text(evidence.get('account_cash_observed'))}"
            ),
            (
                "    account_currency_observed: "
                f"{_bool_text(evidence.get('account_currency_observed'))}"
            ),
            (
                "    btcusd_position_status: "
                f"{_value_text(evidence.get('btcusd_position_status'))}"
            ),
            (
                "    btcusd_position_quantity: "
                f"{_value_text(evidence.get('btcusd_position_quantity'))}"
            ),
            (
                "    btcusd_position_average_price: "
                f"{_value_text(evidence.get('btcusd_position_average_price'))}"
            ),
            (
                "    recent_order_query_contract_version: "
                f"{_value_text(evidence.get('recent_order_query_contract_version'))}"
            ),
            (
                "    recent_order_query_metadata_complete: "
                f"{_bool_text(evidence.get('recent_order_query_metadata_complete'))}"
            ),
            (
                "    recent_order_query_metadata_missing_fields: "
                f"{_joined(evidence.get('recent_order_query_metadata_missing_fields'))}"
            ),
            (
                "    recent_order_query_returned_count: "
                f"{_value_text(evidence.get('recent_order_query_returned_count'))}"
            ),
            (
                "    unavailable_observations: "
                f"{_joined(evidence.get('unavailable_observations'))}"
            ),
            (
                "    credentials_redacted_present: "
                f"{_bool_text(evidence.get('credentials_redacted_present'))}"
            ),
            (
                "    live_profile_evidence: "
                f"{_bool_text(evidence.get('live_profile_evidence'))}"
            ),
            (
                "    credential_leak_evidence: "
                f"{_bool_text(evidence.get('credential_leak_evidence'))}"
            ),
            (
                "  limitations: "
                f"{_joined(checklist.get('limitations'))}"
            ),
        ]
    )
    return lines


def _close_exit_probe_design_lines(
    design: Mapping[str, Any],
) -> list[str]:
    return [
        "close_exit_probe_design:",
        f"  design_ready: {_bool_text(design.get('design_ready'))}",
        f"  close_preview_status: {_value_text(design.get('close_preview_status'))}",
        f"  preview_only: {_bool_text(design.get('preview_only'))}",
        f"  submitted: {_tri_bool_text(design.get('submitted'))}",
        f"  mutated: {_tri_bool_text(design.get('mutated'))}",
        f"  paper_lab_only: {_bool_text(design.get('paper_lab_only'))}",
        f"  not_live_authorized: {_bool_text(design.get('not_live_authorized'))}",
        f"  profit_claim: {_value_text(design.get('profit_claim'))}",
        (
            "  manual_review_required: "
            f"{_bool_text(design.get('manual_review_required'))}"
        ),
        f"  asset_class: {_value_text(design.get('asset_class'))}",
        f"  symbol: {_value_text(design.get('symbol'))}",
        f"  side: {_value_text(design.get('side'))}",
        f"  order_type: {_value_text(design.get('order_type'))}",
        f"  time_in_force: {_value_text(design.get('time_in_force'))}",
        (
            "  observed_position_quantity: "
            f"{_value_text(design.get('observed_position_quantity'))}"
        ),
        (
            "  requested_close_quantity: "
            f"{_value_text(design.get('requested_close_quantity'))}"
        ),
        (
            "  remaining_quantity_after_preview: "
            f"{_value_text(design.get('remaining_quantity_after_preview'))}"
        ),
        (
            "  close_quantity_within_observed_position: "
            f"{_bool_text(design.get('close_quantity_within_observed_position'))}"
        ),
        f"  no_shorting_gate: {_value_text(design.get('no_shorting_gate'))}",
        (
            "  fresh_snapshot_required: "
            f"{_bool_text(design.get('fresh_snapshot_required'))}"
        ),
        (
            "  fresh_snapshot_status: "
            f"{_value_text(design.get('fresh_snapshot_status'))}"
        ),
        (
            "  recent_order_query_metadata_complete: "
            f"{_bool_text(design.get('recent_order_query_metadata_complete'))}"
        ),
        (
            "  submission_disabled_reason: "
            f"{_value_text(design.get('submission_disabled_reason'))}"
        ),
        (
            "  recommended_next_operator_action: "
            f"{_value_text(design.get('recommended_next_operator_action'))}"
        ),
    ]


def _close_action_eligibility_checklist_lines(
    checklist: Mapping[str, Any],
) -> list[str]:
    lines = [
        "close_action_eligibility_checklist:",
        f"  version: {_value_text(checklist.get('version'))}",
        f"  status: {_value_text(checklist.get('status'))}",
        f"  paper_lab_only: {_bool_text(checklist.get('paper_lab_only'))}",
        f"  not_live_authorized: {_bool_text(checklist.get('not_live_authorized'))}",
        f"  profit_claim: {_value_text(checklist.get('profit_claim'))}",
        (
            "  manual_review_required: "
            f"{_bool_text(checklist.get('manual_review_required'))}"
        ),
        (
            "  eligible_for_future_close_probe_consideration: "
            f"{_bool_text(checklist.get('eligible_for_future_close_probe_consideration'))}"
        ),
        (
            "  broker_action_performed: "
            f"{_bool_text(checklist.get('broker_action_performed'))}"
        ),
        (
            "  close_order_submitted: "
            f"{_bool_text(checklist.get('close_order_submitted'))}"
        ),
        f"  snapshot_run_id: {_value_text(checklist.get('snapshot_run_id'))}",
        (
            "  close_preview_event_observed: "
            f"{_bool_text(checklist.get('close_preview_event_observed'))}"
        ),
        (
            "  observed_position_quantity: "
            f"{_value_text(checklist.get('observed_position_quantity'))}"
        ),
        (
            "  requested_close_quantity: "
            f"{_value_text(checklist.get('requested_close_quantity'))}"
        ),
        (
            "  remaining_quantity_after_preview: "
            f"{_value_text(checklist.get('remaining_quantity_after_preview'))}"
        ),
    ]
    for item in _sequence(checklist.get("required_operator_confirmations")):
        lines.append(f"  required_operator_confirmation: {_value_text(item)}")
    lines.extend(
        [
            (
                "  blocking_reasons: "
                f"{_joined(checklist.get('blocking_reasons'))}"
            ),
            f"  limitations: {_joined(checklist.get('limitations'))}",
            (
                "  recommended_next_operator_action: "
                f"{_value_text(checklist.get('recommended_next_operator_action'))}"
            ),
        ]
    )
    return lines


def _future_close_probe_preparation_lines(
    preparation: Mapping[str, Any],
) -> list[str]:
    pre_submit_snapshot = _mapping(
        preparation.get("required_pre_submit_snapshot")
    )
    position_quantity = _mapping(preparation.get("required_position_quantity"))
    query_metadata = _mapping(
        preparation.get("required_recent_order_query_metadata")
    )
    close_preview = _mapping(preparation.get("required_close_preview_evidence"))
    lines = [
        "future_close_probe_preparation:",
        f"  version: {_value_text(preparation.get('version'))}",
        (
            "  manual_review_only: "
            f"{_bool_text(preparation.get('manual_review_only'))}"
        ),
        (
            "  broker_action_performed: "
            f"{_bool_text(preparation.get('broker_action_performed'))}"
        ),
        (
            "  close_order_submitted: "
            f"{_bool_text(preparation.get('close_order_submitted'))}"
        ),
        (
            "  ready_for_future_prompt_generation: "
            f"{_bool_text(preparation.get('ready_for_future_prompt_generation'))}"
        ),
    ]
    for item in _sequence(preparation.get("required_operator_confirmation")):
        lines.append(f"  required_operator_confirmation: {_value_text(item)}")
    lines.extend(
        [
            "  required_pre_submit_snapshot:",
            (
                "    required_status: "
                f"{_value_text(pre_submit_snapshot.get('required_status'))}"
            ),
            (
                "    observed_status: "
                f"{_value_text(pre_submit_snapshot.get('observed_status'))}"
            ),
            (
                "    snapshot_records_observed: "
                f"{_bool_text(pre_submit_snapshot.get('snapshot_records_observed'))}"
            ),
            (
                "    snapshot_run_id: "
                f"{_value_text(pre_submit_snapshot.get('snapshot_run_id'))}"
            ),
            f"    mutated: {_tri_bool_text(pre_submit_snapshot.get('mutated'))}",
            f"    submitted: {_tri_bool_text(pre_submit_snapshot.get('submitted'))}",
            "  required_position_quantity:",
            f"    symbol: {_value_text(position_quantity.get('symbol'))}",
            f"    quantity: {_value_text(position_quantity.get('quantity'))}",
            (
                "    requested_close_quantity: "
                f"{_value_text(position_quantity.get('requested_close_quantity'))}"
            ),
            (
                "    positive_quantity_required: "
                f"{_bool_text(position_quantity.get('positive_quantity_required'))}"
            ),
            "  required_recent_order_query_metadata:",
            (
                "    metadata_complete: "
                f"{_bool_text(query_metadata.get('metadata_complete'))}"
            ),
            (
                "    contract_version: "
                f"{_value_text(query_metadata.get('contract_version'))}"
            ),
            (
                "    returned_count: "
                f"{_value_text(query_metadata.get('returned_count'))}"
            ),
            (
                "    missing_fields: "
                f"{_joined(query_metadata.get('missing_fields'))}"
            ),
            "  required_close_preview_evidence:",
            (
                "    event_observed: "
                f"{_bool_text(close_preview.get('event_observed'))}"
            ),
            (
                "    preview_only_required: "
                f"{_bool_text(close_preview.get('preview_only_required'))}"
            ),
            (
                "    submitted_required: "
                f"{_bool_text(close_preview.get('submitted_required'))}"
            ),
            (
                "    mutated_required: "
                f"{_bool_text(close_preview.get('mutated_required'))}"
            ),
            (
                "    requested_close_quantity: "
                f"{_value_text(close_preview.get('requested_close_quantity'))}"
            ),
            (
                "    remaining_quantity_after_preview: "
                f"{_value_text(close_preview.get('remaining_quantity_after_preview'))}"
            ),
            (
                "  required_eligibility_status: "
                f"{_value_text(preparation.get('required_eligibility_status'))}"
            ),
            (
                "  observed_eligibility_status: "
                f"{_value_text(preparation.get('observed_eligibility_status'))}"
            ),
            (
                "  blocking_reasons: "
                f"{_joined(preparation.get('blocking_reasons'))}"
            ),
            (
                "  recommended_next_operator_action: "
                f"{_value_text(preparation.get('recommended_next_operator_action'))}"
            ),
            (
                "  future_command_template_review_only: "
                f"{_value_text(preparation.get('future_command_template_review_only'))}"
            ),
            (
                "  future_command_template_safety_note: "
                f"{_value_text(preparation.get('future_command_template_safety_note'))}"
            ),
        ]
    )
    return lines


def _explicit_close_probe_prompt_review_lines(
    review: Mapping[str, Any],
) -> list[str]:
    return [
        "explicit_close_probe_prompt_review:",
        "  review_only_label: operator_review_only",
        f"  version: {_value_text(review.get('version'))}",
        (
            "  manual_review_only: "
            f"{_bool_text(review.get('manual_review_only'))}"
        ),
        (
            "  broker_action_performed: "
            f"{_bool_text(review.get('broker_action_performed'))}"
        ),
        (
            "  close_order_submitted: "
            f"{_bool_text(review.get('close_order_submitted'))}"
        ),
        (
            "  prompt_ready_for_operator_review: "
            f"{_bool_text(review.get('prompt_ready_for_operator_review'))}"
        ),
        (
            "  generated_from_future_close_probe_preparation: "
            f"{_bool_text(review.get('generated_from_future_close_probe_preparation'))}"
        ),
        (
            "  observed_preparation_ready: "
            f"{_bool_text(review.get('observed_preparation_ready'))}"
        ),
        (
            "  observed_eligibility_status: "
            f"{_value_text(review.get('observed_eligibility_status'))}"
        ),
        (
            "  observed_position_symbol: "
            f"{_value_text(review.get('observed_position_symbol'))}"
        ),
        (
            "  observed_position_quantity: "
            f"{_value_text(review.get('observed_position_quantity'))}"
        ),
        (
            "  observed_recent_order_query_metadata_complete: "
            f"{_bool_text(review.get('observed_recent_order_query_metadata_complete'))}"
        ),
        (
            "  required_final_pre_submit_snapshot: "
            f"{_bool_text(review.get('required_final_pre_submit_snapshot'))}"
        ),
        (
            "  required_final_operator_confirmation: "
            f"{_bool_text(review.get('required_final_operator_confirmation'))}"
        ),
        f"  future_probe_scope: {_value_text(review.get('future_probe_scope'))}",
        f"  blocking_reasons: {_joined(review.get('blocking_reasons'))}",
        (
            "  recommended_next_operator_action: "
            f"{_value_text(review.get('recommended_next_operator_action'))}"
        ),
        (
            "  review_only_prompt_text: "
            f"{_value_text(review.get('review_only_prompt_text'))}"
        ),
        (
            "  future_command_template_review_only: "
            f"{_value_text(review.get('future_command_template_review_only'))}"
        ),
    ]


def _submit_observation_lines(
    submit_observation: Mapping[str, Any],
) -> list[str]:
    return [
        f"submit_attempt_count: {_value_text(submit_observation.get('submit_attempt_count'))}",
        f"receipt_observed: {_tri_bool_text(submit_observation.get('receipt_observed'))}",
        (
            "broker_response_received: "
            f"{_tri_bool_text(submit_observation.get('broker_response_received'))}"
        ),
        (
            "broker_response_parsed: "
            f"{_tri_bool_text(submit_observation.get('broker_response_parsed'))}"
        ),
        f"submitted: {_tri_bool_text(submit_observation.get('submitted'))}",
        f"accepted: {_tri_bool_text(submit_observation.get('accepted'))}",
        f"filled: {_tri_bool_text(submit_observation.get('filled'))}",
        f"raw_status: {_value_text(submit_observation.get('raw_status'))}",
        (
            "normalized_status: "
            f"{_value_text(submit_observation.get('normalized_status'))}"
        ),
        f"raw_reason: {_value_text(submit_observation.get('raw_reason'))}",
        f"asset_class: {_value_text(submit_observation.get('asset_class'))}",
        f"symbol: {_value_text(submit_observation.get('symbol'))}",
        f"side: {_value_text(submit_observation.get('side'))}",
        f"notional: {_value_text(submit_observation.get('notional'))}",
        f"max_notional: {_value_text(submit_observation.get('max_notional'))}",
        f"min_notional: {_value_text(submit_observation.get('min_notional'))}",
        f"order_type: {_value_text(submit_observation.get('order_type'))}",
        f"time_in_force: {_value_text(submit_observation.get('time_in_force'))}",
        f"pre_submit_cash: {_value_text(submit_observation.get('pre_submit_cash'))}",
        f"post_submit_cash: {_value_text(submit_observation.get('post_submit_cash'))}",
        f"cash_delta: {_value_text(submit_observation.get('cash_delta'))}",
        (
            "pre_submit_position_count: "
            f"{_value_text(submit_observation.get('pre_submit_position_count'))}"
        ),
        (
            "post_submit_position_count: "
            f"{_value_text(submit_observation.get('post_submit_position_count'))}"
        ),
        (
            "post_submit_position_symbols: "
            f"{_joined(submit_observation.get('post_submit_position_symbols'))}"
        ),
        (
            "target_position_observed: "
            f"{_tri_bool_text(submit_observation.get('target_position_observed'))}"
        ),
        (
            "target_position_quantity: "
            f"{_value_text(submit_observation.get('target_position_quantity'))}"
        ),
        (
            "target_position_average_price: "
            f"{_value_text(submit_observation.get('target_position_average_price'))}"
        ),
        (
            "recent_order_count: "
            f"{_value_text(submit_observation.get('recent_order_count'))}"
        ),
        (
            "recent_order_query_attempted: "
            f"{_tri_bool_text(submit_observation.get('recent_order_query_attempted'))}"
        ),
        (
            "recent_order_query_available: "
            f"{_tri_bool_text(submit_observation.get('recent_order_query_available'))}"
        ),
        (
            "recent_order_query_limit: "
            f"{_value_text(submit_observation.get('recent_order_query_limit'))}"
        ),
        (
            "recent_order_query_status_filter: "
            f"{_value_text(submit_observation.get('recent_order_query_status_filter'))}"
        ),
        (
            "recent_order_query_asset_class_filter: "
            f"{_value_text(submit_observation.get('recent_order_query_asset_class_filter'))}"
        ),
        (
            "recent_order_query_symbol_filter: "
            f"{_value_text(submit_observation.get('recent_order_query_symbol_filter'))}"
        ),
        (
            "recent_order_query_side_filter: "
            f"{_value_text(submit_observation.get('recent_order_query_side_filter'))}"
        ),
        (
            "recent_order_query_after: "
            f"{_value_text(submit_observation.get('recent_order_query_after'))}"
        ),
        (
            "recent_order_query_until: "
            f"{_value_text(submit_observation.get('recent_order_query_until'))}"
        ),
        (
            "recent_order_query_sort: "
            f"{_value_text(submit_observation.get('recent_order_query_sort'))}"
        ),
        (
            "recent_order_query_direction: "
            f"{_value_text(submit_observation.get('recent_order_query_direction'))}"
        ),
        (
            "recent_order_query_nested: "
            f"{_tri_bool_text(submit_observation.get('recent_order_query_nested'))}"
        ),
        (
            "recent_order_query_source: "
            f"{_value_text(submit_observation.get('recent_order_query_source'))}"
        ),
        (
            "recent_order_query_contract_version: "
            f"{_value_text(submit_observation.get('recent_order_query_contract_version'))}"
        ),
        (
            "recent_order_query_returned_count: "
            f"{_value_text(submit_observation.get('recent_order_query_returned_count'))}"
        ),
        (
            "recent_order_query_metadata_complete: "
            f"{_tri_bool_text(submit_observation.get('recent_order_query_metadata_complete'))}"
        ),
        (
            "recent_order_query_metadata_missing_fields: "
            f"{_joined(submit_observation.get('recent_order_query_metadata_missing_fields'))}"
        ),
        (
            "target_receipt_observed: "
            f"{_tri_bool_text(submit_observation.get('target_receipt_observed'))}"
        ),
        (
            "target_receipt_client_order_id: "
            f"{_value_text(submit_observation.get('target_receipt_client_order_id'))}"
        ),
        (
            "target_receipt_order_id: "
            f"{_value_text(submit_observation.get('target_receipt_order_id'))}"
        ),
        (
            "recent_order_observed_for_target: "
            f"{_tri_bool_text(submit_observation.get('recent_order_observed_for_target'))}"
        ),
        (
            "target_recent_order_match_observed: "
            f"{_tri_bool_text(submit_observation.get('target_recent_order_match_observed'))}"
        ),
        (
            "target_recent_order_match_basis: "
            f"{_value_text(submit_observation.get('target_recent_order_match_basis'))}"
        ),
        (
            "order_list_observation_gap: "
            f"{_tri_bool_text(submit_observation.get('order_list_observation_gap'))}"
        ),
        (
            "order_list_gap_reason: "
            f"{_value_text(submit_observation.get('order_list_gap_reason'))}"
        ),
        (
            "unavailable_observations: "
            f"{_joined(submit_observation.get('unavailable_observations'))}"
        ),
    ]


def _status_text(status: Mapping[str, Any]) -> str:
    return " ".join(
        f"{field}={_text(status.get(field))}"
        for field in _SAFE_ORDER_STATUS_FIELDS
        if field in status
    )


def _event_text(event: Mapping[str, Any]) -> str:
    parts = [f"event_type={_text(event.get('event_type'))}"]
    if event.get("error"):
        parts.append(f"error={_text(event.get('error'))}")
    if event.get("error_type"):
        parts.append(f"error_type={_text(event.get('error_type'))}")
    observations = _joined(event.get("unavailable_observations"))
    if observations != "none":
        parts.append(f"unavailable_observations={observations}")
    reasons = _mapping(event.get("unavailable_reasons"))
    if reasons:
        parts.append(f"unavailable_reasons={_reason_text(reasons)}")

    return " ".join(parts)


def _reason_text(reasons: Mapping[str, object]) -> str:
    parts: list[str] = []
    for name in sorted(reasons):
        detail = _mapping(reasons[name])
        reason_parts = [f"{key}:{detail[key]}" for key in sorted(detail)]
        parts.append(f"{name}({','.join(reason_parts)})")

    return ";".join(parts)


def _joined(value: Any) -> str:
    items = [_text(item) for item in _sequence(value) if _text(item)]
    return ",".join(items) if items else "none"


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value

    return {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if value is None or isinstance(value, (str, bytes)):
        return ()
    if isinstance(value, Sequence):
        return tuple(value)

    return ()


def _is_secret_like(value: str) -> bool:
    return bool(_SECRET_TEXT_RE.search(value))


def _bool_or_none(value: Any) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _tri_bool_text(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def _value_text(value: Any) -> str:
    text = _text(value)
    return text if text else "unavailable"


def _text(value: Any) -> str:
    if value is None:
        return ""

    return str(value)


__all__ = [
    "STATE_BROKER_REJECTED",
    "STATE_INSUFFICIENT_OBSERVATION",
    "STATE_INVALID_RUN_LOG",
    "STATE_OBSERVATION_UNAVAILABLE",
    "STATE_POSITION_OBSERVED_WITHOUT_RECEIPT",
    "STATE_RECEIPT_AND_POSITION_OBSERVED",
    "STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP",
    "STATE_RECEIPT_OBSERVED_WITHOUT_POSITION",
    "STATE_SUBMIT_FAILED_BEFORE_RESPONSE",
    "STATE_USABLE_FOR_MANUAL_REVIEW",
    "build_paper_lab_revalidation_brief",
    "render_paper_lab_revalidation_brief_text",
]
