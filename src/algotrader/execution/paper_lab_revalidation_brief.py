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
    fresh_snapshot_checklist = _mapping(
        payload.get("fresh_snapshot_operator_checklist")
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
    lines.extend(_fresh_snapshot_operator_checklist_lines(fresh_snapshot_checklist))

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
    return {
        "account": _latest_account(selected_records),
        "advisory_labels": {
            "manual_review_required": True,
            "not_live_authorized": True,
            "paper_lab_only": True,
            "profit_claim": "none",
        },
        "command": "paper-lab-revalidation-brief",
        "event_counts": _event_counts(selected_records),
        "fresh_snapshot_operator_checklist": _fresh_snapshot_operator_checklist(
            state,
            records=records,
            selected_records=selected_records,
            missing_observations=missing_observations,
            unavailable_events=unavailable_events,
        ),
        "invalid_reasons": list(invalid_reasons),
        "manual_review_note": (
            "manual review required before any further paper probe"
        ),
        "missing_observations": list(missing_observations),
        "next_probe_note": "next manual paper probe remains outside this command",
        "observations": observations,
        "positions": _latest_positions(selected_records),
        "post_receipt_reconciliation": _post_receipt_reconciliation(
            state,
            submit_observation,
        ),
        "recent_orders": _latest_recent_orders(selected_records),
        "record_count": len(records),
        "redaction_markers_found": _redaction_markers(observation_records),
        "run_ids": list(run_ids),
        "selected_record_count": len(selected_records),
        "selected_run_id": _safe_run_id(selected_run_id),
        "state": state,
        "submit_observation": submit_observation,
        "unavailable_events": unavailable_events,
        "usable_for_manual_review": usable,
    }


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
