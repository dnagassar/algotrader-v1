from __future__ import annotations

import json

from algotrader.execution.paper_lab_revalidation_brief import (
    STATE_INSUFFICIENT_OBSERVATION,
    STATE_INVALID_RUN_LOG,
    STATE_OBSERVATION_UNAVAILABLE,
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
