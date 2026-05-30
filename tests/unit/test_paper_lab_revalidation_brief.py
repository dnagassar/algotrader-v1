from __future__ import annotations

import json

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


SECRET_VALUE = "paper-lab-secret-value-that-must-not-leak"


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

    assert payload["state"] == STATE_RECEIPT_AND_POSITION_OBSERVED_WITH_ORDER_LIST_GAP
    assert payload["usable_for_manual_review"] is True
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
    assert summary["recent_order_observed_for_target"] is False
    assert summary["order_list_observation_gap"] is True
    assert summary["unavailable_observations"] == []
    assert payload["redaction_markers_found"] == ["credentials_redacted"]
    assert "state: receipt_and_position_observed_with_order_list_gap" in rendered
    assert "cash_delta: -9.81" in rendered
    assert "order_list_observation_gap: true" in rendered
    assert _forbidden_claims_absent(rendered)


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
    assert summary["recent_order_observed_for_target"] is True
    assert summary["order_list_observation_gap"] is False


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

    assert payload["state"] == STATE_POSITION_OBSERVED_WITHOUT_RECEIPT
    assert summary["receipt_observed"] is False
    assert summary["broker_response_received"] is True
    assert summary["broker_response_parsed"] is False
    assert summary["target_position_observed"] is True


def test_receipt_without_post_submit_observation_is_insufficient(tmp_path) -> None:
    run_log = _write_jsonl(
        tmp_path / "receipt_only.jsonl",
        _receipt_only_records(),
    )

    payload = build_paper_lab_revalidation_brief(run_log)
    summary = payload["submit_observation"]

    assert payload["state"] == STATE_INSUFFICIENT_OBSERVATION
    assert payload["usable_for_manual_review"] is False
    assert summary["receipt_observed"] is True
    assert summary["has_post_submit_observation"] is False


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
    assert payload["submit_observation"]["unavailable_observations"] == ["orders"]
    assert SECRET_VALUE not in rendered


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
    assert "token" not in rendered
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


def test_malformed_jsonl_is_invalid_run_log(tmp_path) -> None:
    run_log = tmp_path / "malformed.jsonl"
    run_log.write_text(
        '{"event_type":"paper_lab_snapshot_requested","run_id":"bad-run"}\n'
        "not-json\n",
        encoding="utf-8",
    )

    payload = build_paper_lab_revalidation_brief(run_log)

    assert payload["state"] == STATE_INVALID_RUN_LOG
    assert payload["usable_for_manual_review"] is False
    assert payload["invalid_reasons"] == ["line 2: JSONDecodeError"]


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
    assert "token" not in rendered


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
    filled: bool | None = False,
    normalized_status: str = "pending_new",
    raw_reason: str = "",
    raw_status: str = "OrderStatus.PENDING_NEW",
    recent_order_count: int = 0,
    recent_orders: list[dict[str, object]] | None = None,
    submitted: bool | None = True,
) -> tuple[dict[str, object], ...]:
    pre_run_id = "m319-pre-submit"
    probe_run_id = "m319-probe"
    post_run_id = "m319-post-submit"
    order_fields = _crypto_order_fields(
        accepted=accepted,
        broker_response_parsed=broker_response_parsed,
        broker_response_received=broker_response_received,
        filled=filled,
        normalized_status=normalized_status,
        raw_reason=raw_reason,
        raw_status=raw_status,
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
    filled: bool | None,
    normalized_status: str,
    raw_reason: str,
    raw_status: str,
    submitted: bool | None,
) -> dict[str, object]:
    return {
        "accepted": accepted,
        "asset_class": "crypto",
        "broker_normalized_status": normalized_status,
        "broker_raw_reason": raw_reason,
        "broker_raw_status": raw_status,
        "broker_response_parsed": broker_response_parsed,
        "broker_response_received": broker_response_received,
        "client_order_id": "paper-order-probe-m319",
        "command": "paper-order-probe",
        "error": "",
        "error_type": "",
        "filled": filled,
        "max_notional": "10.00",
        "min_notional": "10.00",
        "normalized_status": normalized_status,
        "notional": "10.00",
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


def _snapshot_records(
    *,
    run_id: str,
    cash: str,
    position_count: int,
    position_symbols: list[str],
    positions: list[dict[str, object]],
    recent_order_count: int,
    recent_orders: list[dict[str, object]],
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
        },
    )


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
            "recommended",
            "profitable",
            "live ready",
            "safe to submit",
            "strategy validated",
        )
    )
