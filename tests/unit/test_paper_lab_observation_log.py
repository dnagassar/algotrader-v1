from __future__ import annotations

import json
from decimal import Decimal

import pytest

from algotrader.execution.paper_lab_observation_log import (
    EVENT_TYPES,
    PAPER_ACCOUNT_OBSERVED,
    PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
    PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
    PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
    PAPER_LAB_SNAPSHOT_REQUESTED,
    PAPER_LAB_SNAPSHOT_UNAVAILABLE,
    PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED,
    PAPER_ORDER_PREVIEWED,
    PAPER_ORDER_RECEIPT_OBSERVED,
    PAPER_ORDER_RESPONSE_PARSE_FAILED,
    PAPER_ORDER_SUBMIT_ATTEMPTED,
    PAPER_ORDER_SUBMIT_FAILED,
    PAPER_ORDER_SUBMIT_REQUESTED,
    PAPER_POSITIONS_OBSERVED,
    PaperLabObservationEvent,
    PaperLabRunLogError,
    append_jsonl_records,
    make_account_smoke_events,
    make_order_probe_initial_events,
    make_order_probe_submit_events,
    make_paper_lab_snapshot_events,
    render_jsonl_records,
    resolve_run_id,
)
from algotrader.execution.paper_order_policy import CRYPTO_SUBMIT_DISABLED_REASON


SECRET_VALUE = "paper-lab-secret-value"


def test_event_model_lists_paper_lab_observation_types() -> None:
    assert EVENT_TYPES == (
        PAPER_ACCOUNT_OBSERVED,
        PAPER_POSITIONS_OBSERVED,
        PAPER_ORDER_PREVIEWED,
        PAPER_ORDER_SUBMIT_REQUESTED,
        PAPER_ORDER_SUBMIT_ATTEMPTED,
        PAPER_ORDER_SUBMIT_FAILED,
        PAPER_ORDER_RECEIPT_OBSERVED,
        PAPER_ORDER_RESPONSE_PARSE_FAILED,
        "paper_order_post_submit_account_observed",
        PAPER_LAB_SNAPSHOT_REQUESTED,
        PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
        PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
        PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
        PAPER_LAB_SNAPSHOT_UNAVAILABLE,
    )


def test_account_smoke_events_are_json_safe_and_redacted() -> None:
    payload = {
        "account": {"cash": Decimal("100000"), "currency": "USD"},
        "command": "paper-account-smoke",
        "gates": {
            "profile_gate": {
                "detail": f"ready {SECRET_VALUE}",
                "passed": True,
            }
        },
        "ok": True,
        "position_count": 1,
        "positions": [
            {
                "average_price": Decimal("100.10"),
                "quantity": Decimal("3"),
                "symbol": "MSFT",
            }
        ],
        "submitted": False,
    }

    records = make_account_smoke_events(
        run_id="account-run",
        payload=payload,
        secret_values=(SECRET_VALUE,),
    )
    rendered = render_jsonl_records(records)

    assert [record["event_type"] for record in records] == [
        PAPER_ACCOUNT_OBSERVED,
        PAPER_POSITIONS_OBSERVED,
    ]
    assert SECRET_VALUE not in rendered
    assert "<redacted>" in rendered
    assert json.loads(rendered.splitlines()[0])["account"]["cash"] == "100000"


def test_paper_lab_snapshot_events_capture_account_positions_orders() -> None:
    payload = {
        "account": {"cash": "100000", "currency": "USD"},
        "account_observation_available": True,
        "command": "paper-lab-snapshot",
        "error": "",
        "gates": {
            "profile_gate": {"detail": "paper_profile_ready", "passed": True}
        },
        "mutated": False,
        "ok": True,
        "orders_observation_available": True,
        "position_count": 1,
        "position_symbols": ["MSFT"],
        "positions": [
            {"average_price": "100.10", "quantity": "3", "symbol": "MSFT"}
        ],
        "positions_observation_available": True,
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
        "submitted": False,
        "unavailable_observations": [],
        "unavailable_reasons": {},
    }

    records = make_paper_lab_snapshot_events(
        run_id="snapshot-run",
        payload=payload,
    )

    assert [record["event_type"] for record in records] == [
        PAPER_LAB_SNAPSHOT_REQUESTED,
        PAPER_LAB_SNAPSHOT_ACCOUNT_OBSERVED,
        PAPER_LAB_SNAPSHOT_POSITIONS_OBSERVED,
        PAPER_LAB_SNAPSHOT_ORDERS_OBSERVED,
    ]
    assert records[0]["ok"] is True
    assert records[1]["account"] == {"cash": "100000", "currency": "USD"}
    assert records[2]["position_symbols"] == ["MSFT"]
    assert records[3]["recent_orders"] == payload["recent_orders"]


def test_paper_lab_snapshot_unavailable_event_is_redacted() -> None:
    payload = {
        "account_observation_available": False,
        "command": "paper-lab-snapshot",
        "error": "paper_lab_snapshot_unavailable",
        "gates": {
            "profile_gate": {"detail": "paper_profile_ready", "passed": True}
        },
        "mutated": False,
        "ok": False,
        "orders_observation_available": False,
        "position_count": 0,
        "position_symbols": [],
        "positions_observation_available": False,
        "recent_order_count": 0,
        "submitted": False,
        "unavailable_observations": ["orders"],
        "unavailable_reasons": {
            "orders": {
                "error_type": "AlpacaAdapterError",
                "message": f"failed with {SECRET_VALUE}",
            }
        },
    }

    records = make_paper_lab_snapshot_events(
        run_id="snapshot-unavailable-run",
        payload=payload,
        secret_values=(SECRET_VALUE,),
    )
    rendered = render_jsonl_records(records)

    assert [record["event_type"] for record in records] == [
        PAPER_LAB_SNAPSHOT_REQUESTED,
        PAPER_LAB_SNAPSHOT_UNAVAILABLE,
    ]
    assert records[-1]["unavailable_observations"] == ["orders"]
    assert SECRET_VALUE not in rendered
    assert "<redacted>" in rendered


def test_order_probe_events_capture_preview_request_attempt_and_receipt() -> None:
    preview_payload = _order_payload(
        submit_requested=True,
        submit_attempted=False,
        broker_response_received=False,
        broker_response_parsed=False,
        submitted=False,
    )
    submit_payload = {
        **preview_payload,
        "accepted": True,
        "broker_response_parsed": True,
        "broker_response_received": True,
        "broker_result": {
            "accepted": True,
            "normalized_status": "accepted",
            "raw_reason": "broker accepted",
            "raw_status": "orderstatus.accepted",
            "reason": "",
        },
        "filled": False,
        "market_session_note": (
            "Market DAY equity orders submitted after hours may be accepted "
            "or queued by the broker and may not fill until the next regular "
            "session."
        ),
        "post_submit_account": {"cash": "99995", "currency": "USD"},
        "post_submit_position_count": 1,
        "post_submit_positions": [
            {"average_price": "100.10", "quantity": "3", "symbol": "MSFT"}
        ],
        "preview_only": False,
        "submitted": True,
        "submit_attempted": True,
    }

    records = (
        *make_order_probe_initial_events(
            run_id="probe-run",
            payload=preview_payload,
        ),
        *make_order_probe_submit_events(
            run_id="probe-run",
            payload=submit_payload,
        ),
    )

    assert [record["event_type"] for record in records] == [
        PAPER_ORDER_PREVIEWED,
        PAPER_ORDER_SUBMIT_REQUESTED,
        PAPER_ORDER_SUBMIT_ATTEMPTED,
        PAPER_ORDER_RECEIPT_OBSERVED,
        PAPER_ORDER_POST_SUBMIT_ACCOUNT_OBSERVED,
    ]
    receipt = records[-2]
    post_submit = records[-1]
    assert receipt["asset_class"] == "equity"
    assert receipt["symbol"] == "SPY"
    assert receipt["side"] == "buy"
    assert receipt["sizing_mode"] == "notional"
    assert receipt["notional"] == "5"
    assert receipt["submitted"] is True
    assert receipt["accepted"] is True
    assert receipt["filled"] is False
    assert receipt["broker_normalized_status"] == "accepted"
    assert receipt["broker_raw_status"] == "orderstatus.accepted"
    assert receipt["broker_raw_reason"] == "broker accepted"
    assert receipt["market_session_note"].startswith("Market DAY equity orders")
    assert post_submit["account"] == {"cash": "99995", "currency": "USD"}
    assert post_submit["position_count"] == 1


def test_disabled_asset_submit_request_records_asset_class_and_reason() -> None:
    payload = {
        **_order_payload(
            submit_requested=True,
            submit_attempted=False,
            broker_response_received=False,
            broker_response_parsed=False,
            submitted=False,
        ),
        "asset_class": "crypto",
        "preview_only": True,
        "submission_disabled_reason": CRYPTO_SUBMIT_DISABLED_REASON,
        "proposed_order_request": {
            "client_order_id": "paper-order-probe-notional-1",
            "notional": "5",
            "order_type": "market",
            "qty": "",
            "side": "buy",
            "symbol": "BTCUSD",
            "time_in_force": "gtc",
        },
    }

    records = make_order_probe_initial_events(
        run_id="crypto-disabled-run",
        payload=payload,
    )

    assert [record["event_type"] for record in records] == [
        PAPER_ORDER_PREVIEWED,
        PAPER_ORDER_SUBMIT_REQUESTED,
    ]
    assert {record["asset_class"] for record in records} == {"crypto"}
    assert {
        record["submission_disabled_reason"] for record in records
    } == {CRYPTO_SUBMIT_DISABLED_REASON}


def test_order_probe_parse_failure_event_captures_attempted_submit() -> None:
    payload = {
        **_order_payload(
            submit_requested=True,
            submit_attempted=True,
            broker_response_received=True,
            broker_response_parsed=False,
            submitted=True,
        ),
        "broker_error": True,
        "error": "broker_response_parse_failed",
        "error_type": "AlpacaTranslationError",
        "message": f"bad receipt {SECRET_VALUE}",
    }

    records = make_order_probe_submit_events(
        run_id="parse-run",
        payload=payload,
        secret_values=(SECRET_VALUE,),
    )

    assert [record["event_type"] for record in records] == [
        PAPER_ORDER_SUBMIT_ATTEMPTED,
        PAPER_ORDER_RESPONSE_PARSE_FAILED,
    ]
    parse_failure = records[-1]
    assert parse_failure["submit_attempted"] is True
    assert parse_failure["broker_response_received"] is True
    assert parse_failure["broker_response_parsed"] is False
    assert SECRET_VALUE not in render_jsonl_records(records)


def test_order_probe_adapter_failure_event_has_unknown_submitted_state() -> None:
    payload = {
        **_order_payload(
            submit_requested=True,
            submit_attempted=True,
            broker_response_received=False,
            broker_response_parsed=False,
            submitted=None,
        ),
        "accepted": None,
        "broker_error": True,
        "error": "paper_order_probe_submit_failed",
        "error_type": "AlpacaAdapterError",
        "filled": None,
        "message": f"local submit failed {SECRET_VALUE}",
    }

    records = make_order_probe_submit_events(
        run_id="adapter-failure-run",
        payload=payload,
        secret_values=(SECRET_VALUE,),
    )

    assert [record["event_type"] for record in records] == [
        PAPER_ORDER_SUBMIT_ATTEMPTED,
        PAPER_ORDER_SUBMIT_FAILED,
    ]
    failure = records[-1]
    assert failure["submit_attempted"] is True
    assert failure["broker_response_received"] is False
    assert failure["broker_response_parsed"] is False
    assert failure["submitted"] is None
    assert failure["accepted"] is None
    assert failure["filled"] is None
    assert SECRET_VALUE not in render_jsonl_records(records)


def test_jsonl_append_creates_parent_and_appends(tmp_path) -> None:
    path = tmp_path / "runs" / "paper_lab" / "probe.jsonl"
    record = PaperLabObservationEvent(
        run_id="append-run",
        command="paper-order-probe",
        event_type=PAPER_ORDER_PREVIEWED,
        fields={"notional": Decimal("5"), "submitted": False},
    ).to_record()

    append_jsonl_records(path, (record,))
    append_jsonl_records(path, (record,))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == record
    assert lines[0] == lines[1]


def test_repeated_deterministic_records_are_byte_identical() -> None:
    record = PaperLabObservationEvent(
        run_id="deterministic-run",
        command="paper-order-probe",
        event_type=PAPER_ORDER_PREVIEWED,
        fields={
            "gate_summary": {"profile_gate": {"detail": "ready", "passed": True}},
            "notional": Decimal("5.00"),
            "submitted": False,
        },
    ).to_record()

    assert render_jsonl_records((record,)) == render_jsonl_records((record,))


def test_invalid_run_log_path_raises_clean_error(tmp_path) -> None:
    directory_path = tmp_path / "not-a-file"
    directory_path.mkdir()
    record = PaperLabObservationEvent(
        run_id="bad-path-run",
        command="paper-order-probe",
        event_type=PAPER_ORDER_PREVIEWED,
    ).to_record()

    with pytest.raises(PaperLabRunLogError) as exc_info:
        append_jsonl_records(directory_path, (record,))

    assert str(exc_info.value).startswith("paper_lab_run_log_write_failed:")
    assert str(directory_path) not in str(exc_info.value)


def test_run_id_sanitization_keeps_deterministic_user_value() -> None:
    assert resolve_run_id(" paper lab/test ") == "paper_lab_test"


def _order_payload(
    *,
    submit_requested: bool,
    submit_attempted: bool,
    broker_response_received: bool,
    broker_response_parsed: bool,
    submitted: bool | None,
) -> dict[str, object]:
    return {
        "accepted": None,
        "asset_class": "equity",
        "broker_response_parsed": broker_response_parsed,
        "broker_response_received": broker_response_received,
        "command": "paper-order-probe",
        "error": "",
        "filled": None,
        "gates": {
            "profile_gate": {"detail": "paper_profile_ready", "passed": True},
            "halt_gate": {"detail": "halt_not_set", "passed": True},
        },
        "max_notional": "10",
        "preview_only": not submit_requested,
        "proposed_order_request": {
            "client_order_id": "paper-order-probe-notional-1",
            "notional": "5",
            "qty": "",
            "side": "buy",
            "symbol": "SPY",
        },
        "requested_notional": "5",
        "requested_qty": "",
        "sizing_mode": "notional",
        "submitted": submitted,
        "submit_attempted": submit_attempted,
        "submit_requested": submit_requested,
    }
