from __future__ import annotations

import json

from algotrader.execution.paper_lab_observation_log import (
    make_paper_close_preview_events,
)
from algotrader.execution.paper_lab_revalidation_brief import (
    STATE_BROKER_REJECTED,
    STATE_INSUFFICIENT_OBSERVATION,
    STATE_INVALID_RUN_LOG,
    STATE_OBSERVATION_UNAVAILABLE,
    STATE_POSITION_OBSERVED_WITHOUT_RECEIPT,
    STATE_RECEIPT_AND_POSITION_OBSERVED,
    STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP,
    STATE_SUBMIT_FAILED_BEFORE_RESPONSE,
    STATE_USABLE_FOR_MANUAL_REVIEW,
    build_paper_lab_revalidation_brief,
    render_paper_lab_revalidation_brief_text,
)
from algotrader.execution.paper_order_policy import (
    build_btcusd_paper_close_preview_contract,
)


SECRET_VALUE = "paper-lab-secret-value-that-must-not-leak"
POST_RECEIPT_RECONCILIATION_FIELDS = {
    "accepted",
    "asset_class",
    "broker_response_parsed",
    "broker_response_received",
    "cash_delta",
    "filled",
    "max_notional",
    "min_notional",
    "normalized_status",
    "notional",
    "order_list_gap",
    "order_list_gap_reason",
    "position_average_price",
    "position_observed",
    "position_quantity",
    "post_submit_cash",
    "pre_submit_cash",
    "raw_status",
    "receipt_observed",
    "receipt_state",
    "recent_order_match_basis",
    "recent_order_match_observed",
    "recent_order_query_contract_version",
    "recent_order_query_metadata_complete",
    "recent_order_query_metadata_missing_fields",
    "recent_order_query_returned_count",
    "reconciliation_confidence",
    "reconciliation_limitations",
    "recommended_next_operator_action",
    "side",
    "submitted",
    "symbol",
}


def test_text_output_is_deterministic_for_usable_snapshot_log(tmp_path) -> None:
    run_log = _write_jsonl(tmp_path / "snapshot.jsonl", _complete_snapshot_records())

    first = render_paper_lab_revalidation_brief_text(
        build_paper_lab_revalidation_brief(run_log)
    )
    second = render_paper_lab_revalidation_brief_text(
        build_paper_lab_revalidation_brief(run_log)
    )

    assert first == second
    assert "state: usable_for_manual_review" in first
    assert "paper_lab_only: true" in first
    assert "not_live_authorized: true" in first
    assert "manual_review_required: true" in first
    assert "profit_claim: none" in first
    assert "account_cash: 100000 USD" in first
    assert "position_symbols: MSFT" in first
    assert "recent_order_status: symbol=SPY side=buy" in first
    assert _forbidden_claims_absent(first)


def test_json_output_is_deterministic_for_usable_snapshot_log(tmp_path) -> None:
    run_log = _write_jsonl(tmp_path / "snapshot.jsonl", _complete_snapshot_records())

    first = _compact_json(build_paper_lab_revalidation_brief(run_log))
    second = _compact_json(build_paper_lab_revalidation_brief(run_log))
    payload = json.loads(first)

    assert first == second
    assert payload["state"] == STATE_USABLE_FOR_MANUAL_REVIEW
    assert payload["usable_for_manual_review"] is True
    assert payload["advisory_labels"]["profit_claim"] == "none"
    assert payload["event_counts"] == {
        "paper_lab_snapshot_account_observed": 1,
        "paper_lab_snapshot_orders_observed": 1,
        "paper_lab_snapshot_positions_observed": 1,
        "paper_lab_snapshot_requested": 1,
    }
    assert payload["run_ids"] == ["snapshot-run"]


def test_m318_like_receipt_cash_position_with_empty_orders_is_order_gap(
    tmp_path,
) -> None:
    run_log = _write_jsonl(tmp_path / "m318.jsonl", _m318_like_records())

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = render_paper_lab_revalidation_brief_text(payload)
    summary = payload["submit_observation"]
    reconciliation = payload["post_receipt_reconciliation"]

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP
    assert payload["usable_for_manual_review"] is True
    assert set(reconciliation) == POST_RECEIPT_RECONCILIATION_FIELDS
    assert summary["submit_attempt_count"] == 1
    assert summary["receipt_observed"] is True
    assert summary["broker_response_received"] is True
    assert summary["broker_response_parsed"] is True
    assert summary["submitted"] is True
    assert summary["accepted"] is True
    assert summary["filled"] is False
    assert summary["raw_status"] == "OrderStatus.PENDING_NEW"
    assert summary["normalized_status"] == "pending_new"
    assert summary["raw_reason"] == ""
    assert summary["asset_class"] == "crypto"
    assert summary["symbol"] == "BTCUSD"
    assert summary["side"] == "buy"
    assert summary["notional"] == "10.00"
    assert summary["max_notional"] == "10.00"
    assert summary["min_notional"] == "10.00"
    assert summary["order_type"] == "market"
    assert summary["time_in_force"] == "gtc"
    assert summary["pre_submit_cash"] == "2000"
    assert summary["post_submit_cash"] == "1990.19"
    assert summary["cash_delta"] == "-9.81"
    assert summary["pre_submit_position_count"] == 0
    assert summary["post_submit_position_count"] == 1
    assert summary["post_submit_position_symbols"] == ["BTCUSD"]
    assert summary["target_position_observed"] is True
    assert summary["target_position_quantity"] == "0.000132386"
    assert summary["target_position_average_price"] == "73886.11"
    assert summary["recent_order_count"] == 0
    assert summary["recent_order_query_attempted"] is True
    assert summary["recent_order_query_available"] is True
    assert summary["recent_order_query_limit"] is None
    assert summary["recent_order_query_status_filter"] == ""
    assert summary["recent_order_query_asset_class_filter"] == ""
    assert summary["recent_order_query_symbol_filter"] == ""
    assert summary["recent_order_query_side_filter"] == ""
    assert summary["recent_order_query_after"] is None
    assert summary["recent_order_query_until"] is None
    assert summary["recent_order_query_sort"] == ""
    assert summary["recent_order_query_direction"] == ""
    assert summary["recent_order_query_nested"] is None
    assert summary["recent_order_query_source"] == ""
    assert summary["recent_order_query_contract_version"] == ""
    assert summary["recent_order_query_metadata_complete"] is False
    assert summary["recent_order_query_metadata_missing_fields"] == [
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
    ]
    assert summary["recent_order_query_returned_count"] == 0
    assert summary["target_receipt_observed"] is True
    assert summary["target_receipt_client_order_id"] == "paper-order-probe-m319"
    assert summary["target_receipt_order_id"] == ""
    assert summary["recent_order_observed_for_target"] is False
    assert summary["target_recent_order_match_observed"] is False
    assert summary["target_recent_order_match_basis"] == "none"
    assert summary["order_list_observation_gap"] is True
    assert summary["order_list_gap_reason"] == "recent_order_query_returned_empty"
    assert summary["unavailable_observations"] == []
    assert reconciliation["receipt_observed"] is True
    assert reconciliation["receipt_state"] == (
        STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP
    )
    assert reconciliation["broker_response_received"] is True
    assert reconciliation["broker_response_parsed"] is True
    assert reconciliation["submitted"] is True
    assert reconciliation["accepted"] is True
    assert reconciliation["filled"] is False
    assert reconciliation["raw_status"] == "OrderStatus.PENDING_NEW"
    assert reconciliation["normalized_status"] == "pending_new"
    assert reconciliation["asset_class"] == "crypto"
    assert reconciliation["symbol"] == "BTCUSD"
    assert reconciliation["side"] == "buy"
    assert reconciliation["notional"] == "10.00"
    assert reconciliation["max_notional"] == "10.00"
    assert reconciliation["min_notional"] == "10.00"
    assert reconciliation["pre_submit_cash"] == "2000"
    assert reconciliation["post_submit_cash"] == "1990.19"
    assert reconciliation["cash_delta"] == "-9.81"
    assert reconciliation["position_observed"] is True
    assert reconciliation["position_quantity"] == "0.000132386"
    assert reconciliation["position_average_price"] == "73886.11"
    assert reconciliation["recent_order_query_contract_version"] == ""
    assert reconciliation["recent_order_query_metadata_complete"] is False
    assert reconciliation["recent_order_query_returned_count"] == 0
    assert reconciliation["recent_order_match_observed"] is False
    assert reconciliation["recent_order_match_basis"] == "none"
    assert reconciliation["order_list_gap"] is True
    assert reconciliation["order_list_gap_reason"] == (
        "recent_order_query_returned_empty"
    )
    assert reconciliation["reconciliation_confidence"] == (
        "medium_receipt_position_observed_order_gap"
    )
    assert reconciliation["recommended_next_operator_action"] == (
        "read_only_fresh_snapshot_before_any_close_probe"
    )
    checklist = payload["fresh_snapshot_operator_checklist"]
    assert checklist["status"] == "blocked_query_metadata_incomplete"
    assert checklist["recommended_next_operator_action"] == (
        "read_only_fresh_snapshot_before_any_close_probe"
    )
    assert checklist["evidence"]["recent_order_query_metadata_complete"] is False
    assert (
        "recent order query metadata is incomplete" in checklist["limitations"][0]
    )
    assert any(
        "recent order query metadata is incomplete" in limitation
        for limitation in reconciliation["reconciliation_limitations"]
    )
    assert payload["redaction_markers_found"] == ["credentials_redacted"]
    assert "state: receipt_and_position_observed_with_order_list_gap" in rendered
    assert "post_receipt_reconciliation:" in rendered
    assert "cash_delta: -9.81" in rendered
    assert "order_list_observation_gap: true" in rendered
    assert "order_list_gap_reason: recent_order_query_returned_empty" in rendered
    assert (
        "reconciliation_confidence: medium_receipt_position_observed_order_gap"
        in rendered
    )
    assert (
        "recommended_next_operator_action: "
        "read_only_fresh_snapshot_before_any_close_probe"
        in rendered
    )
    assert "recent_order_query_metadata_complete: false" in rendered
    assert _forbidden_claims_absent(rendered)


def test_complete_recent_order_query_metadata_is_reported(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "complete_query_metadata.jsonl",
        _m318_like_records(include_query_metadata=True),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]
    reconciliation = payload["post_receipt_reconciliation"]

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP
    assert summary["order_list_gap_reason"] == "recent_order_query_returned_empty"
    assert summary["recent_order_query_limit"] == 100
    assert summary["recent_order_query_status_filter"] == "open"
    assert summary["recent_order_query_asset_class_filter"] == ""
    assert summary["recent_order_query_symbol_filter"] == ""
    assert summary["recent_order_query_side_filter"] == ""
    assert summary["recent_order_query_after"] is None
    assert summary["recent_order_query_until"] is None
    assert summary["recent_order_query_sort"] == ""
    assert summary["recent_order_query_direction"] == "desc"
    assert summary["recent_order_query_nested"] is False
    assert summary["recent_order_query_source"] == "alpaca_sdk_client.get_orders"
    assert summary["recent_order_query_contract_version"] == (
        "paper_recent_order_query_v1"
    )
    assert summary["recent_order_query_metadata_complete"] is True
    assert summary["recent_order_query_metadata_missing_fields"] == []
    assert reconciliation["recent_order_query_contract_version"] == (
        "paper_recent_order_query_v1"
    )
    assert reconciliation["recent_order_query_metadata_complete"] is True
    assert reconciliation["reconciliation_confidence"] == (
        "medium_receipt_position_observed_order_gap"
    )
    assert not any(
        "recent order query metadata is incomplete" in limitation
        for limitation in reconciliation["reconciliation_limitations"]
    )


def test_fresh_snapshot_operator_checklist_completes_for_fresh_read_only_snapshot(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "fresh_snapshot.jsonl",
        _fresh_snapshot_records(),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    checklist = payload["fresh_snapshot_operator_checklist"]
    close_design = payload["close_exit_probe_design"]
    close_action = payload["close_action_eligibility_checklist"]
    evidence = checklist["evidence"]
    rendered = render_paper_lab_revalidation_brief_text(payload)

    assert checklist["status"] == "read_only_snapshot_completed_for_manual_review"
    assert checklist["pre_run_status"] == "ready_for_read_only_snapshot"
    assert checklist["paper_lab_only"] is True
    assert checklist["not_live_authorized"] is True
    assert checklist["profit_claim"] == "none"
    assert checklist["fresh_snapshot_command_template"] == (
        "python -m algotrader paper-lab-snapshot --run-log "
        "runs/paper_lab/<fresh_id>.jsonl --run-id <fresh_id> --format json"
    )
    assert evidence["profile_gate_status"] == "paper_profile_ready"
    assert evidence["ok"] is True
    assert evidence["mutated"] is False
    assert evidence["submitted"] is False
    assert evidence["account_observation_available"] is True
    assert evidence["positions_observation_available"] is True
    assert evidence["orders_observation_available"] is True
    assert evidence["account_cash_observed"] is True
    assert evidence["account_currency_observed"] is True
    assert evidence["btcusd_position_status"] == "present"
    assert evidence["btcusd_position_quantity"] == "0.000132386"
    assert evidence["btcusd_position_average_price"] == "73886.11"
    assert evidence["recent_order_query_contract_version"] == (
        "paper_recent_order_query_v1"
    )
    assert evidence["recent_order_query_metadata_complete"] is True
    assert evidence["recent_order_query_returned_count"] == 0
    assert evidence["unavailable_observations"] == []
    assert evidence["credentials_redacted_present"] is True
    assert evidence["live_profile_evidence"] is False
    assert evidence["credential_leak_evidence"] is False
    assert close_design["design_ready"] is True
    assert close_design["preview_only"] is True
    assert close_design["submitted"] is False
    assert close_design["mutated"] is False
    assert close_design["paper_lab_only"] is True
    assert close_design["not_live_authorized"] is True
    assert close_design["profit_claim"] == "none"
    assert close_design["manual_review_required"] is True
    assert close_design["asset_class"] == "crypto"
    assert close_design["symbol"] == "BTCUSD"
    assert close_design["side"] == "sell"
    assert close_design["order_type"] == "market"
    assert close_design["time_in_force"] == "gtc"
    assert close_design["observed_position_quantity"] == "0.000132386"
    assert close_design["requested_close_quantity"] == "0.000132386"
    assert close_design["remaining_quantity_after_preview"] == "0"
    assert close_design["close_quantity_within_observed_position"] is True
    assert close_design["no_shorting_gate"] == "passed"
    assert close_design["fresh_snapshot_required"] is True
    assert close_design["fresh_snapshot_status"] == (
        "read_only_snapshot_completed_for_manual_review"
    )
    assert close_design["recent_order_query_metadata_complete"] is True
    assert close_action["status"] == "blocked_missing_close_preview"
    assert close_action["eligible_for_future_close_probe_consideration"] is False
    assert close_action["broker_action_performed"] is False
    assert close_action["close_order_submitted"] is False
    assert close_action["snapshot_run_id"] == "fresh-snapshot-run"
    assert close_action["close_preview_event_observed"] is False
    assert close_action["observed_position_quantity"] == "0.000132386"
    assert close_action["requested_close_quantity"] == ""
    assert close_action["remaining_quantity_after_preview"] == ""
    assert close_action["blocking_reasons"] == ["close_preview_evidence_missing"]
    assert close_action["recommended_next_operator_action"] == (
        "collect_required_read_only_or_preview_evidence_before_close_probe"
    )
    assert "close_exit_probe_design:" in rendered
    assert "close_action_eligibility_checklist:" in rendered
    assert "design_ready: true" in rendered
    assert "submission_disabled_reason: close_preview_submission_disabled" in rendered


def test_close_action_eligibility_checklist_allows_later_operator_approval(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "close_eligible.jsonl",
        (
            *_fresh_snapshot_records(run_id="m324-fresh-read-only"),
            *_close_preview_records(run_id="m325-close-preview"),
        ),
    )

    payload = build_paper_lab_revalidation_brief(
        run_log,
        run_id="m324-fresh-read-only",
    )
    checklist = payload["close_action_eligibility_checklist"]
    rendered = render_paper_lab_revalidation_brief_text(payload)

    assert checklist["version"] == "close_action_eligibility_checklist_v1"
    assert checklist["status"] == "eligible_for_explicit_operator_approval"
    assert checklist["paper_lab_only"] is True
    assert checklist["not_live_authorized"] is True
    assert checklist["profit_claim"] == "none"
    assert checklist["manual_review_required"] is True
    assert checklist["eligible_for_future_close_probe_consideration"] is True
    assert checklist["broker_action_performed"] is False
    assert checklist["close_order_submitted"] is False
    assert checklist["snapshot_run_id"] == "m324-fresh-read-only"
    assert checklist["close_preview_event_observed"] is True
    assert checklist["observed_position_quantity"] == "0.000132386"
    assert checklist["requested_close_quantity"] == "0.000132386"
    assert checklist["remaining_quantity_after_preview"] == "0"
    assert checklist["required_operator_confirmations"] == [
        "I understand this is paper-only.",
        "I understand this is not live-authorized.",
        "I understand this may close the BTCUSD paper position.",
        "I understand the action must be manually triggered.",
        "I understand normal pytest must remain credential-free.",
        "I understand this does not imply profitability.",
    ]
    assert checklist["blocking_reasons"] == []
    assert checklist["recommended_next_operator_action"] == (
        "prepare_explicit_paper_close_probe_prompt_but_do_not_submit"
    )
    assert (
        "status: eligible_for_explicit_operator_approval"
        in rendered
    )
    assert (
        "recommended_next_operator_action: "
        "prepare_explicit_paper_close_probe_prompt_but_do_not_submit"
        in rendered
    )


def test_close_action_eligibility_checklist_blocks_no_shorting_failure(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "close_no_shorting_blocked.jsonl",
        (
            *_fresh_snapshot_records(run_id="m324-fresh-read-only"),
            *_close_preview_records(
                run_id="m325-close-preview",
                requested_close_quantity="0.000132387",
            ),
        ),
    )

    payload = build_paper_lab_revalidation_brief(
        run_log,
        run_id="m324-fresh-read-only",
    )
    checklist = payload["close_action_eligibility_checklist"]

    assert checklist["status"] == "blocked_no_shorting_gate_failed"
    assert checklist["eligible_for_future_close_probe_consideration"] is False
    assert checklist["requested_close_quantity"] == "0.000132387"
    assert "requested_close_quantity_exceeds_observed_position" in checklist[
        "blocking_reasons"
    ]
    assert "no_shorting_gate_not_passed" in checklist["blocking_reasons"]


def test_fresh_snapshot_operator_checklist_blocks_unavailable_observations(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "fresh_unavailable.jsonl",
        _fresh_snapshot_records(unavailable_observations=["orders"]),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    checklist = payload["fresh_snapshot_operator_checklist"]

    assert checklist["status"] == "blocked_unavailable_observations"
    assert checklist["evidence"]["orders_observation_available"] is False
    assert checklist["evidence"]["unavailable_observations"] == ["orders"]


def test_fresh_snapshot_operator_checklist_blocks_unexpected_mutation_or_submit(
    tmp_path,
) -> None:
    mutated_log = _write_jsonl(
        tmp_path / "fresh_mutated.jsonl",
        _fresh_snapshot_records(mutated=True),
    )
    submitted_log = _write_jsonl(
        tmp_path / "fresh_submitted.jsonl",
        _fresh_snapshot_records(submitted=True),
    )

    mutated_payload = build_paper_lab_revalidation_brief(mutated_log)
    submitted_payload = build_paper_lab_revalidation_brief(submitted_log)

    assert (
        mutated_payload["fresh_snapshot_operator_checklist"]["status"]
        == "blocked_unexpected_mutation"
    )
    assert (
        submitted_payload["fresh_snapshot_operator_checklist"]["status"]
        == "blocked_unexpected_submit"
    )
    assert mutated_payload["close_exit_probe_design"]["design_ready"] is False
    assert submitted_payload["close_exit_probe_design"]["design_ready"] is False


def test_fresh_snapshot_operator_checklist_blocks_live_profile_evidence(
    tmp_path,
) -> None:
    records = list(_fresh_snapshot_records())
    records[0] = {
        **records[0],
        "profile": "live-profile-that-must-not-appear",
        "url": "https://live.example.test",
    }
    run_log = _write_jsonl(tmp_path / "fresh_live.jsonl", records)

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = _compact_json(payload) + render_paper_lab_revalidation_brief_text(
        payload
    )

    assert (
        payload["fresh_snapshot_operator_checklist"]["status"]
        == "blocked_live_profile_evidence"
    )
    assert "live-profile-that-must-not-appear" not in rendered
    assert "https://live.example.test" not in rendered


def test_fresh_snapshot_operator_checklist_blocks_credential_like_evidence(
    tmp_path,
) -> None:
    records = list(_fresh_snapshot_records())
    records[0] = {**records[0], "api_key": SECRET_VALUE}
    run_log = _write_jsonl(tmp_path / "fresh_secret.jsonl", records)

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = _compact_json(payload) + render_paper_lab_revalidation_brief_text(
        payload
    )
    checklist = payload["fresh_snapshot_operator_checklist"]

    assert checklist["status"] == "blocked_credential_leak_evidence"
    assert checklist["paper_lab_only"] is True
    assert checklist["not_live_authorized"] is True
    assert checklist["profit_claim"] == "none"
    assert "paper-lab-snapshot --run-log runs/paper_lab/<fresh_id>.jsonl" in rendered
    assert SECRET_VALUE not in rendered
    assert "api_key" not in rendered
    assert "ALPACA_API_KEY" not in rendered


def test_successful_receipt_with_target_recent_order_has_no_order_gap(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "target_order.jsonl",
        _m318_like_records(
            recent_order_count=1,
            recent_orders=[
                {
                    "asset_class": "crypto",
                    "client_order_id": "paper-order-probe-m319",
                    "normalized_status": "pending_new",
                    "order_type": "market",
                    "raw_status": "OrderStatus.PENDING_NEW",
                    "side": "buy",
                    "symbol": "BTCUSD",
                    "time_in_force": "gtc",
                }
            ],
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]
    reconciliation = payload["post_receipt_reconciliation"]

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED
    assert summary["recent_order_observed_for_target"] is True
    assert summary["target_recent_order_match_observed"] is True
    assert summary["target_recent_order_match_basis"] == "client_order_id"
    assert summary["order_list_observation_gap"] is False
    assert summary["order_list_gap_reason"] == ""
    assert reconciliation["recent_order_match_observed"] is True
    assert reconciliation["recent_order_match_basis"] == "client_order_id"
    assert reconciliation["order_list_gap"] is False
    assert reconciliation["reconciliation_confidence"] == (
        "high_receipt_position_cash_observed"
    )


def test_successful_receipt_with_target_recent_order_by_broker_id_has_no_gap(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "target_order_id.jsonl",
        _m318_like_records(
            receipt_order_id="broker-order-m319",
            recent_order_count=1,
            recent_orders=[
                {
                    "asset_class": "crypto",
                    "order_id": "broker-order-m319",
                    "normalized_status": "pending_new",
                    "order_type": "market",
                    "raw_status": "OrderStatus.PENDING_NEW",
                    "side": "buy",
                    "symbol": "BTCUSD",
                    "time_in_force": "gtc",
                }
            ],
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED
    assert summary["target_receipt_order_id"] == "broker-order-m319"
    assert summary["recent_order_observed_for_target"] is True
    assert summary["target_recent_order_match_observed"] is True
    assert summary["target_recent_order_match_basis"] == "broker_order_id"
    assert summary["order_list_observation_gap"] is False


def test_successful_receipt_can_match_recent_order_by_symbol_side_notional(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "target_symbol_side_notional.jsonl",
        _m318_like_records(
            client_order_id="",
            recent_order_count=1,
            recent_orders=[
                {
                    "asset_class": "crypto",
                    "notional": "10.00",
                    "normalized_status": "pending_new",
                    "order_type": "market",
                    "raw_status": "OrderStatus.PENDING_NEW",
                    "side": "buy",
                    "symbol": "BTCUSD",
                    "time_in_force": "gtc",
                }
            ],
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED
    assert summary["target_receipt_client_order_id"] == ""
    assert summary["recent_order_observed_for_target"] is True
    assert summary["target_recent_order_match_basis"] == "symbol_side_notional"
    assert summary["order_list_observation_gap"] is False


def test_successful_receipt_with_unrelated_recent_orders_reports_gap_reason(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "unrelated_order.jsonl",
        _m318_like_records(
            recent_order_count=1,
            recent_orders=[
                {
                    "asset_class": "crypto",
                    "client_order_id": "other-client-order",
                    "notional": "10.00",
                    "normalized_status": "pending_new",
                    "order_id": "other-broker-order",
                    "order_type": "market",
                    "raw_status": "OrderStatus.PENDING_NEW",
                    "side": "buy",
                    "symbol": "ETHUSD",
                    "time_in_force": "gtc",
                }
            ],
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP
    assert summary["recent_order_observed_for_target"] is False
    assert summary["target_recent_order_match_basis"] == "none"
    assert summary["order_list_observation_gap"] is True
    assert (
        summary["order_list_gap_reason"]
        == "target_order_not_in_recent_order_results"
    )


def test_receipt_missing_correlation_id_reports_diagnostic_gap_reason(
    tmp_path,
) -> None:
    run_log = _write_jsonl(
        tmp_path / "missing_correlation.jsonl",
        _m318_like_records(
            client_order_id="",
            notional="",
            recent_order_count=1,
            recent_orders=[
                {
                    "asset_class": "crypto",
                    "normalized_status": "pending_new",
                    "order_type": "market",
                    "raw_status": "OrderStatus.PENDING_NEW",
                    "side": "buy",
                    "symbol": "BTCUSD",
                    "time_in_force": "gtc",
                }
            ],
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP
    assert summary["target_receipt_client_order_id"] == ""
    assert summary["target_receipt_order_id"] == ""
    assert summary["order_list_observation_gap"] is True
    assert summary["order_list_gap_reason"] == "receipt_missing_correlation_id"


def test_broker_rejected_receipt_classifies_as_broker_rejected(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "rejected.jsonl",
        _m318_like_records(
            accepted=False,
            broker_response_received=True,
            broker_response_parsed=True,
            filled=False,
            normalized_status="rejected",
            raw_reason="order_rejected",
            raw_status="OrderStatus.REJECTED",
            submitted=False,
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_BROKER_REJECTED
    assert payload["usable_for_manual_review"] is True
    assert summary["broker_rejected"] is True
    assert summary["accepted"] is False
    assert summary["raw_reason"] == "order_rejected"


def test_submit_failed_before_response_classifies_boundary_failure(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "submit_failed.jsonl",
        _submit_failed_before_response_records(),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_SUBMIT_FAILED_BEFORE_RESPONSE
    assert payload["usable_for_manual_review"] is True
    assert summary["submit_attempt_count"] == 1
    assert summary["receipt_observed"] is False
    assert summary["broker_response_received"] is False
    assert summary["submit_failed_before_response"] is True


def test_position_observed_without_receipt_is_distinct(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "position_without_receipt.jsonl",
        _position_without_receipt_records(),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]
    reconciliation = payload["post_receipt_reconciliation"]

    assert payload["state"] == STATE_POSITION_OBSERVED_WITHOUT_RECEIPT
    assert summary["receipt_observed"] is False
    assert summary["broker_response_received"] is True
    assert summary["broker_response_parsed"] is False
    assert summary["target_position_observed"] is True
    assert reconciliation["reconciliation_confidence"] == "low_position_only"


def test_receipt_without_post_submit_observation_is_insufficient(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "receipt_only.jsonl",
        _receipt_only_records(),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]
    reconciliation = payload["post_receipt_reconciliation"]

    assert payload["state"] == STATE_INSUFFICIENT_OBSERVATION
    assert payload["usable_for_manual_review"] is False
    assert summary["receipt_observed"] is True
    assert summary["has_post_submit_observation"] is False
    assert reconciliation["reconciliation_confidence"] == "low_receipt_only"


def test_submit_context_unavailable_observation_blocks_summary(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "submit_unavailable.jsonl",
        (
            *_m318_like_records(),
            {
                "command": "paper-lab-snapshot",
                "error": "paper_lab_snapshot_unavailable",
                "event_type": "paper_lab_snapshot_unavailable",
                "redaction": "credentials_redacted",
                "run_id": "m319-post-submit",
                "unavailable_observations": ["orders"],
                "unavailable_reasons": {
                    "orders": {
                        "error_type": "AlpacaAdapterError",
                        "message": f"orders unavailable {SECRET_VALUE}",
                    }
                },
            },
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = _compact_json(payload) + render_paper_lab_revalidation_brief_text(
        payload
    )

    assert payload["state"] == STATE_OBSERVATION_UNAVAILABLE
    assert payload["usable_for_manual_review"] is False
    assert payload["post_receipt_reconciliation"]["reconciliation_confidence"] == (
        "unavailable"
    )
    assert payload["submit_observation"]["unavailable_observations"] == ["orders"]
    assert SECRET_VALUE not in rendered


def test_order_query_unavailable_reports_gap_reason_without_submit_failure(
    tmp_path,
) -> None:
    records = tuple(
        record
        for record in _m318_like_records()
        if record.get("event_type") != "paper_lab_snapshot_orders_observed"
    )
    run_log = _write_jsonl(
        tmp_path / "orders_unavailable.jsonl",
        (
            *records,
            {
                "command": "paper-lab-snapshot",
                "error": "paper_lab_snapshot_unavailable",
                "event_type": "paper_lab_snapshot_unavailable",
                "redaction": "credentials_redacted",
                "run_id": "m319-post-submit",
                "unavailable_observations": ["orders"],
                "unavailable_reasons": {
                    "orders": {
                        "error_type": "AlpacaAdapterError",
                        "message": f"orders unavailable {SECRET_VALUE}",
                    }
                },
            },
        ),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_OBSERVATION_UNAVAILABLE
    assert summary["submit_failed_before_response"] is False
    assert summary["receipt_observed"] is True
    assert summary["target_position_observed"] is True
    assert summary["recent_order_query_attempted"] is True
    assert summary["recent_order_query_available"] is False
    assert summary["recent_order_query_returned_count"] is None
    assert summary["order_list_observation_gap"] is True
    assert summary["order_list_gap_reason"] == "order_query_unavailable"
    assert payload["post_receipt_reconciliation"]["reconciliation_confidence"] == (
        "unavailable"
    )


def test_submit_observation_output_excludes_live_and_secret_details(tmp_path) -> None:
    records = list(_m318_like_records())
    records[6] = {
        **records[6],
        "api_key": "paper-lab-secret",
        "profile": "live-profile-that-must-not-appear",
        "secret_key": "paper-lab-secret",
        "token": "paper-lab-secret",
        "url": "https://live.example.test",
    }
    run_log = _write_jsonl(tmp_path / "secret_submit.jsonl", records)

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = _compact_json(payload) + render_paper_lab_revalidation_brief_text(
        payload
    )

    assert payload["redaction_markers_found"] == ["credentials_redacted"]
    assert "paper-lab-secret" not in rendered
    assert "api_key" not in rendered
    assert "secret_key" not in rendered
    assert '"token"' not in rendered
    assert "live-profile-that-must-not-appear" not in rendered
    assert "https://live.example.test" not in rendered


def test_empty_log_is_insufficient_observation(tmp_path) -> None:
    run_log = tmp_path / "empty.jsonl"
    run_log.write_text("", encoding="utf-8")

    payload = build_paper_lab_revalidation_brief(run_log)

    assert payload["state"] == STATE_INSUFFICIENT_OBSERVATION
    assert payload["usable_for_manual_review"] is False
    assert payload["missing_observations"] == ["account", "positions", "orders"]
    assert payload["record_count"] == 0
    assert payload["post_receipt_reconciliation"]["reconciliation_confidence"] == (
        "unavailable"
    )


def test_malformed_jsonl_is_invalid_run_log(tmp_path) -> None:
    run_log = tmp_path / "malformed.jsonl"
    run_log.write_text(
        '{"event_type":"paper_lab_snapshot_requested","run_id":"bad-run"}\n'
        "not-json\n",
        encoding="utf-8",
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = render_paper_lab_revalidation_brief_text(payload)

    assert payload["state"] == STATE_INVALID_RUN_LOG
    assert payload["usable_for_manual_review"] is False
    assert payload["invalid_reasons"] == ["line 2: JSONDecodeError"]
    assert payload["post_receipt_reconciliation"]["reconciliation_confidence"] == (
        "invalid"
    )
    assert "Traceback" not in rendered


def test_missing_account_observation_is_reported(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "missing_account.jsonl",
        _records_without("paper_lab_snapshot_account_observed"),
    )

    payload = build_paper_lab_revalidation_brief(run_log)

    assert payload["state"] == STATE_INSUFFICIENT_OBSERVATION
    assert payload["missing_observations"] == ["account"]
    assert payload["observations"]["account"] is False


def test_missing_positions_observation_is_reported(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "missing_positions.jsonl",
        _records_without("paper_lab_snapshot_positions_observed"),
    )

    payload = build_paper_lab_revalidation_brief(run_log)

    assert payload["state"] == STATE_INSUFFICIENT_OBSERVATION
    assert payload["missing_observations"] == ["positions"]
    assert payload["observations"]["positions"] is False


def test_missing_orders_observation_is_reported(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "missing_orders.jsonl",
        _records_without("paper_lab_snapshot_orders_observed"),
    )

    payload = build_paper_lab_revalidation_brief(run_log)

    assert payload["state"] == STATE_INSUFFICIENT_OBSERVATION
    assert payload["missing_observations"] == ["orders"]
    assert payload["observations"]["orders"] is False


def test_unavailable_event_blocks_manual_review_without_leaking_message(
    tmp_path,
) -> None:
    records = (
        *_records_without("paper_lab_snapshot_orders_observed"),
        {
            "command": "paper-lab-snapshot",
            "error": "paper_lab_snapshot_unavailable",
            "event_type": "paper_lab_snapshot_unavailable",
            "redaction": "credentials_redacted",
            "run_id": "snapshot-run",
            "unavailable_observations": ["orders"],
            "unavailable_reasons": {
                "orders": {
                    "error_type": "AlpacaAdapterError",
                    "message": f"local failure <redacted> {SECRET_VALUE}",
                }
            },
        },
    )
    run_log = _write_jsonl(tmp_path / "unavailable.jsonl", records)

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = _compact_json(payload) + render_paper_lab_revalidation_brief_text(
        payload
    )

    assert payload["state"] == STATE_OBSERVATION_UNAVAILABLE
    assert payload["usable_for_manual_review"] is False
    assert payload["unavailable_events"][-1]["unavailable_reasons"] == {
        "orders": {
            "error_type": "AlpacaAdapterError",
            "message": "<redacted>",
        }
    }
    assert "<redacted>" in rendered
    assert SECRET_VALUE not in rendered


def test_secret_like_keys_are_not_emitted(tmp_path) -> None:
    records = list(_complete_snapshot_records())
    records[1] = {
        **records[1],
        "api_key": SECRET_VALUE,
        "secret_key": SECRET_VALUE,
        "nested": {"token": SECRET_VALUE},
    }
    run_log = _write_jsonl(tmp_path / "secret_keys.jsonl", records)

    payload = build_paper_lab_revalidation_brief(run_log)
    rendered = _compact_json(payload) + render_paper_lab_revalidation_brief_text(
        payload
    )

    assert SECRET_VALUE not in rendered
    assert "api_key" not in rendered
    assert "secret_key" not in rendered
    assert '"token"' not in rendered


def test_latest_run_is_selected_and_all_run_ids_are_reported(tmp_path) -> None:
    earlier = tuple(
        {**record, "run_id": "earlier-run"} for record in _complete_snapshot_records()
    )
    latest = _complete_snapshot_records(run_id="latest-run")
    run_log = _write_jsonl(tmp_path / "multi_run.jsonl", (*earlier, *latest))

    payload = build_paper_lab_revalidation_brief(run_log)

    assert payload["run_ids"] == ["earlier-run", "latest-run"]
    assert payload["selected_run_id"] == "latest-run"
    assert payload["selected_record_count"] == 4
    assert payload["state"] == STATE_USABLE_FOR_MANUAL_REVIEW


def _m318_like_records(
    *,
    accepted: bool | None = True,
    broker_response_parsed: bool = True,
    broker_response_received: bool = True,
    client_order_id: str = "paper-order-probe-m319",
    filled: bool | None = False,
    include_query_metadata: bool = False,
    normalized_status: str = "pending_new",
    notional: str = "10.00",
    raw_reason: str = "",
    raw_status: str = "OrderStatus.PENDING_NEW",
    recent_order_count: int = 0,
    recent_orders: list[dict[str, object]] | None = None,
    receipt_order_id: str = "",
    submitted: bool | None = True,
) -> tuple[dict[str, object], ...]:
    pre_run_id = "m319-pre-submit"
    probe_run_id = "m319-probe"
    post_run_id = "m319-post-submit"
    order_fields = _crypto_order_fields(
        accepted=accepted,
        broker_response_parsed=broker_response_parsed,
        broker_response_received=broker_response_received,
        client_order_id=client_order_id,
        filled=filled,
        normalized_status=normalized_status,
        notional=notional,
        raw_reason=raw_reason,
        raw_status=raw_status,
        receipt_order_id=receipt_order_id,
        submitted=submitted,
    )
    return (
        *_snapshot_records(
            run_id=pre_run_id,
            cash="2000",
            position_count=0,
            position_symbols=[],
            positions=[],
            recent_order_count=0,
            recent_orders=[],
        ),
        {
            **order_fields,
            "event_type": "paper_order_previewed",
            "run_id": probe_run_id,
            "submit_attempted": False,
        },
        {
            **order_fields,
            "event_type": "paper_order_submit_requested",
            "run_id": probe_run_id,
            "submit_attempted": False,
        },
        {
            **order_fields,
            "event_type": "paper_order_submit_attempted",
            "run_id": probe_run_id,
            "submit_attempted": True,
        },
        {
            **order_fields,
            "event_type": "paper_order_receipt_observed",
            "run_id": probe_run_id,
            "submit_attempted": True,
        },
        {
            **order_fields,
            "account": {"cash": "1990.19", "currency": "USD"},
            "event_type": "paper_order_post_submit_account_observed",
            "position_count": 1,
            "positions": [
                {
                    "average_price": "73886.11",
                    "quantity": "0.000132386",
                    "symbol": "BTCUSD",
                }
            ],
            "run_id": probe_run_id,
            "submit_attempted": True,
        },
        *_snapshot_records(
            run_id=post_run_id,
            cash="1990.19",
            position_count=1,
            position_symbols=["BTCUSD"],
            positions=[
                {
                    "average_price": "73886.11",
                    "quantity": "0.000132386",
                    "symbol": "BTCUSD",
                }
            ],
            recent_order_count=recent_order_count,
            recent_orders=recent_orders or [],
            include_query_metadata=include_query_metadata,
        ),
    )


def _submit_failed_before_response_records() -> tuple[dict[str, object], ...]:
    order_fields = _crypto_order_fields(
        accepted=None,
        broker_response_parsed=False,
        broker_response_received=False,
        filled=None,
        normalized_status="",
        raw_reason="",
        raw_status="",
        submitted=None,
    )
    return (
        {
            **order_fields,
            "event_type": "paper_order_submit_attempted",
            "run_id": "failed-probe",
            "submit_attempted": True,
        },
        {
            **order_fields,
            "error": "paper_order_probe_submit_failed",
            "error_type": "AlpacaAdapterError",
            "event_type": "paper_order_submit_failed",
            "run_id": "failed-probe",
            "submit_attempted": True,
            "submit_error_stage": "submit_call_failed_before_response",
        },
    )


def _position_without_receipt_records() -> tuple[dict[str, object], ...]:
    order_fields = _crypto_order_fields(
        accepted=None,
        broker_response_parsed=False,
        broker_response_received=True,
        filled=None,
        normalized_status="",
        raw_reason="",
        raw_status="",
        submitted=True,
    )
    return (
        {
            **order_fields,
            "event_type": "paper_order_submit_attempted",
            "run_id": "position-without-receipt-probe",
            "submit_attempted": True,
        },
        *_snapshot_records(
            run_id="position-without-receipt-post",
            cash="1990.19",
            position_count=1,
            position_symbols=["BTCUSD"],
            positions=[
                {
                    "average_price": "73886.11",
                    "quantity": "0.000132386",
                    "symbol": "BTCUSD",
                }
            ],
            recent_order_count=0,
            recent_orders=[],
        ),
    )


def _receipt_only_records() -> tuple[dict[str, object], ...]:
    order_fields = _crypto_order_fields(
        accepted=True,
        broker_response_parsed=True,
        broker_response_received=True,
        filled=False,
        normalized_status="pending_new",
        raw_reason="",
        raw_status="OrderStatus.PENDING_NEW",
        submitted=True,
    )
    return (
        {
            **order_fields,
            "event_type": "paper_order_submit_attempted",
            "run_id": "receipt-only-probe",
            "submit_attempted": True,
        },
        {
            **order_fields,
            "event_type": "paper_order_receipt_observed",
            "run_id": "receipt-only-probe",
            "submit_attempted": True,
        },
    )


def _crypto_order_fields(
    *,
    accepted: bool | None,
    broker_response_parsed: bool,
    broker_response_received: bool,
    client_order_id: str = "paper-order-probe-m319",
    filled: bool | None,
    normalized_status: str,
    notional: str = "10.00",
    raw_reason: str,
    raw_status: str,
    receipt_order_id: str = "",
    submitted: bool | None,
) -> dict[str, object]:
    fields: dict[str, object] = {
        "accepted": accepted,
        "asset_class": "crypto",
        "broker_normalized_status": normalized_status,
        "broker_raw_reason": raw_reason,
        "broker_raw_status": raw_status,
        "broker_response_parsed": broker_response_parsed,
        "broker_response_received": broker_response_received,
        "client_order_id": client_order_id,
        "command": "paper-order-probe",
        "error": "",
        "error_type": "",
        "filled": filled,
        "max_notional": "10.00",
        "min_notional": "10.00",
        "normalized_status": normalized_status,
        "notional": notional,
        "order_type": "market",
        "preview_only": False,
        "qty": "",
        "raw_reason": raw_reason,
        "raw_status": raw_status,
        "redaction": "credentials_redacted",
        "side": "buy",
        "sizing_mode": "notional",
        "submitted": submitted,
        "submit_requested": True,
        "symbol": "BTCUSD",
        "time_in_force": "gtc",
    }
    if receipt_order_id:
        fields["order_id"] = receipt_order_id

    return fields


def _snapshot_records(
    *,
    run_id: str,
    cash: str,
    position_count: int,
    position_symbols: list[str],
    positions: list[dict[str, object]],
    recent_order_count: int,
    recent_orders: list[dict[str, object]],
    include_query_metadata: bool = False,
) -> tuple[dict[str, object], ...]:
    base = {
        "command": "paper-lab-snapshot",
        "redaction": "credentials_redacted",
        "run_id": run_id,
    }
    return (
        {
            **base,
            "event_type": "paper_lab_snapshot_requested",
            "ok": True,
        },
        {
            **base,
            "account": {"cash": cash, "currency": "USD"},
            "event_type": "paper_lab_snapshot_account_observed",
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_positions_observed",
            "position_count": position_count,
            "position_symbols": position_symbols,
            "positions": positions,
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_orders_observed",
            "recent_order_count": recent_order_count,
            "recent_orders": recent_orders,
            **(
                _complete_recent_order_query_metadata(recent_order_count)
                if include_query_metadata
                else {}
            ),
        },
    )


def _complete_recent_order_query_metadata(
    returned_count: int,
) -> dict[str, object]:
    return {
        "recent_order_query_after": None,
        "recent_order_query_asset_class_filter": "",
        "recent_order_query_attempted": True,
        "recent_order_query_available": True,
        "recent_order_query_contract_version": "paper_recent_order_query_v1",
        "recent_order_query_direction": "desc",
        "recent_order_query_limit": 100,
        "recent_order_query_metadata_complete": True,
        "recent_order_query_metadata_missing_fields": [],
        "recent_order_query_nested": False,
        "recent_order_query_returned_count": returned_count,
        "recent_order_query_side_filter": "",
        "recent_order_query_sort": "",
        "recent_order_query_source": "alpaca_sdk_client.get_orders",
        "recent_order_query_status_filter": "open",
        "recent_order_query_symbol_filter": "",
        "recent_order_query_until": None,
    }


def _close_preview_records(
    *,
    run_id: str,
    requested_close_quantity: str = "0.000132386",
) -> tuple[dict[str, object], ...]:
    payload = build_btcusd_paper_close_preview_contract(
        observed_position_quantity="0.000132386",
        requested_close_quantity=requested_close_quantity,
        fresh_snapshot_status="read_only_snapshot_completed_for_manual_review",
        recent_order_query_metadata_complete=True,
        source_mutated=False,
        source_submitted=False,
    ).to_payload()
    return make_paper_close_preview_events(run_id=run_id, payload=payload)


def _fresh_snapshot_records(
    *,
    run_id: str = "fresh-snapshot-run",
    mutated: bool = False,
    submitted: bool = False,
    unavailable_observations: list[str] | None = None,
) -> tuple[dict[str, object], ...]:
    unavailable_observations = unavailable_observations or []
    orders_available = "orders" not in unavailable_observations
    base = {
        "account_observation_available": True,
        "command": "paper-lab-snapshot",
        "gate_summary": {
            "profile_gate": {"detail": "paper_profile_ready", "passed": True}
        },
        "mutated": mutated,
        "ok": not unavailable_observations,
        "orders_observation_available": orders_available,
        "positions_observation_available": True,
        "redaction": "credentials_redacted",
        "run_id": run_id,
        "submitted": submitted,
        "unavailable_observations": unavailable_observations,
        "unavailable_reasons": (
            {
                name: {"error_type": "AlpacaAdapterError", "message": "<redacted>"}
                for name in unavailable_observations
            }
            if unavailable_observations
            else {}
        ),
        **_complete_recent_order_query_metadata(0),
    }
    records = [
        {
            **base,
            "event_type": "paper_lab_snapshot_requested",
        },
        {
            **base,
            "account": {"cash": "1990.19", "currency": "USD"},
            "event_type": "paper_lab_snapshot_account_observed",
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_positions_observed",
            "position_count": 1,
            "position_symbols": ["BTCUSD"],
            "positions": [
                {
                    "average_price": "73886.11",
                    "quantity": "0.000132386",
                    "symbol": "BTCUSD",
                }
            ],
        },
    ]
    if orders_available:
        records.append(
            {
                **base,
                "event_type": "paper_lab_snapshot_orders_observed",
                "recent_order_count": 0,
                "recent_orders": [],
            }
        )
    if unavailable_observations:
        records.append(
            {
                **base,
                "error": "paper_lab_snapshot_unavailable",
                "event_type": "paper_lab_snapshot_unavailable",
            }
        )

    return tuple(records)


def _complete_snapshot_records(
    *,
    run_id: str = "snapshot-run",
) -> tuple[dict[str, object], ...]:
    base = {
        "command": "paper-lab-snapshot",
        "redaction": "credentials_redacted",
        "run_id": run_id,
    }
    return (
        {
            **base,
            "event_type": "paper_lab_snapshot_requested",
            "ok": True,
        },
        {
            **base,
            "account": {"cash": "100000", "currency": "USD"},
            "event_type": "paper_lab_snapshot_account_observed",
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_positions_observed",
            "position_count": 1,
            "position_symbols": ["MSFT"],
            "positions": [
                {"average_price": "100.10", "quantity": "3", "symbol": "MSFT"}
            ],
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_orders_observed",
            "recent_order_count": 1,
            "recent_orders": [
                {
                    "asset_class": "equity",
                    "filled_at": "",
                    "normalized_status": "accepted",
                    "notional": "5.00",
                    "order_type": "market",
                    "quantity": "",
                    "raw_status": "OrderStatus.ACCEPTED",
                    "side": "buy",
                    "submitted_at": "2026-05-29T14:30:00+00:00",
                    "symbol": "SPY",
                    "time_in_force": "day",
                }
            ],
        },
    )


def _records_without(event_type: str) -> tuple[dict[str, object], ...]:
    return tuple(
        record
        for record in _complete_snapshot_records()
        if record["event_type"] != event_type
    )


def _write_jsonl(path, records) -> object:  # noqa: ANN001
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    return path


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _forbidden_claims_absent(rendered: str) -> bool:
    lowered = rendered.lower()
    return all(
        phrase not in lowered
        for phrase in (
            "ready to trade",
            "approved",
            "profitable",
            "live ready",
            "recommended buy",
            "recommended sell",
            "recommended trade",
            "safe to submit",
            "strategy validated",
        )
    )
