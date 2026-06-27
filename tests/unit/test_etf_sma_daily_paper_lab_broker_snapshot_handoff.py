from __future__ import annotations

import json
from pathlib import Path

import algotrader.execution.etf_sma_daily_paper_lab as paper_lab_module
from algotrader.execution.etf_sma_daily_paper_lab import (
    EtfSmaDailyPaperLabConfig,
    run_etf_sma_daily_paper_lab,
)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"
CLIENT_ORDER_ID = "v202-local-post-drill-order"


def test_valid_local_read_only_paper_snapshot_renders_handoff(
    tmp_path: Path,
) -> None:
    snapshot_log = tmp_path / "valid_snapshot.jsonl"
    _write_snapshot(snapshot_log, spy_position_qty="0.5")
    output_root = tmp_path / "valid_handoff"

    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_log))

    mission = _read_json(output_root / "mission_control.json")
    latest = _read_json(output_root / "latest_run.json")
    manifest = _read_jsonl(output_root / "manifest.jsonl")
    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")

    handoff = mission["broker_snapshot_handoff"]
    assert handoff["handoff_status"] == "broker_snapshot_observed"
    assert handoff["display_only"] is True
    assert handoff["local_artifact_only"] is True
    assert handoff["broker_state_observed"] is True
    assert handoff["current_broker_truth_claimed"] is True
    assert handoff["broker_observation_timestamp"] == "2025-07-20T12:00:00+00:00"
    assert handoff["packet_freshness_status"] == "fresh"
    assert handoff["snapshot_validation_status"] == "passed"
    assert handoff["source_packet_path"] == snapshot_log.as_posix()
    assert handoff["source_packet_metadata"]["command"] == (
        "paper-lab-read-only-broker-snapshot-reconciliation"
    )
    assert handoff["source_packet_metadata"]["record_type"] == (
        "read_only_paper_broker_snapshot_reconciliation"
    )
    assert handoff["spy_position_summary"]["present"] is True
    assert handoff["spy_position_summary"]["quantity"] == "0.5"
    assert handoff["spy_open_order_summary"]["open_spy_order_count"] == 0
    assert handoff["unexpected_non_spy_position_blocker_present"] is False
    _assert_handoff_denies_paper_authority(handoff)

    assert latest["broker_snapshot_handoff_status"] == "broker_snapshot_observed"
    assert latest["broker_snapshot_current_broker_truth_claimed"] is True
    assert manifest["broker_snapshot_handoff"]["handoff_status"] == (
        "broker_snapshot_observed"
    )
    assert "## Read-Only Broker Snapshot Handoff" in brief
    assert "Current broker truth claimed: `true`" in brief
    assert "paper_submit_authorized=false" in brief
    assert "paper_cancel_authorized=false" in brief


def test_missing_snapshot_fails_closed_as_not_available(tmp_path: Path) -> None:
    missing_snapshot = tmp_path / "missing_snapshot.jsonl"
    output_root = tmp_path / "missing_handoff"

    run_etf_sma_daily_paper_lab(_config(output_root, missing_snapshot))

    handoff = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_handoff"
    ]
    assert handoff["handoff_status"] == "broker_snapshot_not_available"
    assert handoff["source_packet_found"] is False
    assert handoff["source_packet_parsed"] is False
    assert handoff["current_broker_truth_claimed"] is False
    assert handoff["spy_position_summary"]["present"] is None
    assert handoff["spy_open_order_summary"]["open_spy_order_count"] is None
    _assert_handoff_denies_paper_authority(handoff)


def test_malformed_snapshot_fails_closed(tmp_path: Path) -> None:
    snapshot_log = tmp_path / "malformed_snapshot.jsonl"
    snapshot_log.write_text("{not-json}\n", encoding="utf-8")
    output_root = tmp_path / "malformed_handoff"

    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_log))

    handoff = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_handoff"
    ]
    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert handoff["source_packet_parsed"] is False
    assert handoff["snapshot_validation_status"] == "failed"
    assert handoff["blocker"] == "broker_snapshot_json_decode_error"
    assert handoff["current_broker_truth_claimed"] is False
    _assert_handoff_denies_paper_authority(handoff)


def test_stale_snapshot_is_visible_but_not_current_broker_truth(
    tmp_path: Path,
) -> None:
    snapshot_log = tmp_path / "stale_snapshot.jsonl"
    _write_snapshot(snapshot_log, generated_at="2025-07-18T12:00:00+00:00")
    output_root = tmp_path / "stale_handoff"

    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_log))

    mission = _read_json(output_root / "mission_control.json")
    latest = _read_json(output_root / "latest_run.json")
    handoff = mission["broker_snapshot_handoff"]
    assert handoff["handoff_status"] == "broker_snapshot_stale"
    assert handoff["packet_stale"] is True
    assert handoff["packet_freshness_status"] == "stale_snapshot"
    assert handoff["current_broker_truth_claimed"] is False
    assert handoff["spy_position_summary"]["present"] is None
    assert latest["observed_spy_position_qty"] is None
    assert latest["broker_snapshot_current_broker_truth_claimed"] is False
    _assert_handoff_denies_paper_authority(handoff)


def test_live_tainted_snapshot_is_rejected_fail_closed(tmp_path: Path) -> None:
    snapshot_log = tmp_path / "live_tainted_snapshot.jsonl"
    _write_snapshot(snapshot_log, live_url_detected=True)
    output_root = tmp_path / "live_tainted_handoff"

    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_log))

    handoff = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_handoff"
    ]
    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert handoff["broker_state_status"] == "live_url_detected"
    assert "broker_snapshot_live_labeled" in handoff["snapshot_validation_errors"]
    assert handoff["current_broker_truth_claimed"] is False
    _assert_handoff_denies_paper_authority(handoff)


def test_mutation_tainted_snapshot_is_rejected_fail_closed(tmp_path: Path) -> None:
    snapshot_log = tmp_path / "mutation_tainted_snapshot.jsonl"
    _write_snapshot(
        snapshot_log,
        overrides={
            "broker_mutation_allowed": True,
            "broker_action_flags": {
                "submit": False,
                "cancel": True,
                "replace": False,
                "close": False,
                "liquidate": False,
                "mutation": True,
            },
        },
    )
    output_root = tmp_path / "mutation_tainted_handoff"

    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_log))

    handoff = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_handoff"
    ]
    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert handoff["broker_state_status"] == (
        "non_paper_or_mutation_capable_snapshot"
    )
    assert "broker_snapshot_broker_mutation_allowed_not_false" in handoff[
        "snapshot_validation_errors"
    ]
    assert "broker_snapshot_action_cancel_not_false" in handoff[
        "snapshot_validation_errors"
    ]
    assert handoff["current_broker_truth_claimed"] is False
    _assert_handoff_denies_paper_authority(handoff)


def test_credential_tainted_snapshot_is_rejected_without_serializing_value(
    tmp_path: Path,
) -> None:
    snapshot_log = tmp_path / "credential_tainted_snapshot.jsonl"
    _write_snapshot(snapshot_log, overrides={"api_key": "do-not-serialize"})
    output_root = tmp_path / "credential_tainted_handoff"

    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_log))

    mission_text = (output_root / "mission_control.json").read_text(encoding="utf-8")
    handoff = json.loads(mission_text)["broker_snapshot_handoff"]
    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert handoff["broker_state_status"] == "credential_tainted_snapshot"
    assert handoff["credential_tainted"] is True
    assert handoff["source_packet_sha256"] == ""
    assert handoff["source_packet_metadata"]["sha256"] == ""
    assert "do-not-serialize" not in mission_text
    for artifact_path in output_root.rglob("*"):
        if artifact_path.is_file():
            assert "do-not-serialize" not in artifact_path.read_text(encoding="utf-8")
    _assert_handoff_denies_paper_authority(handoff)


def test_credential_tainted_snapshot_reader_does_not_hash_packet(
    tmp_path: Path,
    monkeypatch,
) -> None:
    snapshot_log = tmp_path / "credential_tainted_snapshot.jsonl"
    _write_snapshot(snapshot_log, overrides={"api_key": "do-not-hash"})

    def fail_sha256(_content):
        raise AssertionError("credential-tainted broker snapshot was hashed")

    monkeypatch.setattr(paper_lab_module.hashlib, "sha256", fail_sha256)

    record, status, record_count, digest = (
        paper_lab_module._read_single_broker_snapshot_artifact(snapshot_log)
    )

    assert record is not None
    assert status == "parsed"
    assert record_count == 1
    assert digest is None


def test_snapshot_and_post_drill_guard_never_grant_paper_authority(
    tmp_path: Path,
) -> None:
    snapshot_log = tmp_path / "authority_tainted_snapshot.jsonl"
    _write_snapshot(
        snapshot_log,
        overrides={
            "paper_submit_authorized": True,
            "paper_cancel_authorized": True,
        },
    )
    guard_path = tmp_path / "post_drill_guard_packet.json"
    _write_guard_packet(guard_path)
    output_root = tmp_path / "authority_tainted_handoff"

    run_etf_sma_daily_paper_lab(
        _config(
            output_root,
            snapshot_log,
            post_drill_guard_packet_path=guard_path,
        )
    )

    mission = _read_json(output_root / "mission_control.json")
    latest = _read_json(output_root / "latest_run.json")
    handoff = mission["broker_snapshot_handoff"]
    guard = mission["post_drill_guard"]

    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert "broker_snapshot_paper_submit_authorized_not_false" in handoff[
        "snapshot_validation_errors"
    ]
    assert "broker_snapshot_paper_cancel_authorized_not_false" in handoff[
        "snapshot_validation_errors"
    ]
    _assert_handoff_denies_paper_authority(handoff)
    assert guard["status"] == "post_drill_guard_authority_closed"
    assert guard["paper_submit_authorized"] is False
    assert guard["paper_cancel_authorized"] is False
    assert latest["paper_submit_authorized"] is False
    assert latest["post_drill_guard_paper_submit_authorized"] is False
    assert latest["post_drill_guard_paper_cancel_authorized"] is False


def _config(
    output_root: Path,
    broker_snapshot_log: Path,
    *,
    post_drill_guard_packet_path: Path | None = None,
) -> EtfSmaDailyPaperLabConfig:
    return EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
        as_of_date="2025-07-19",
        run_date="2025-07-20",
        symbol="SPY",
        broker_state_mode="alpaca_paper_read_only",
        broker_snapshot_log=broker_snapshot_log,
        post_drill_guard_packet_path=post_drill_guard_packet_path,
        operational_only=True,
    )


def _write_snapshot(
    path: Path,
    *,
    generated_at: str = "2025-07-20T12:00:00+00:00",
    spy_position_qty: str = "0.033695775",
    live_url_detected: bool = False,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    spy_position_present = spy_position_qty not in {"", "0", "0.0", "0.000000000"}
    positions: list[dict[str, object]] = []
    if spy_position_present:
        positions.append({"symbol": "SPY", "qty": spy_position_qty})
    record: dict[str, object] = {
        "command": "paper-lab-read-only-broker-snapshot-reconciliation",
        "record_type": "read_only_paper_broker_snapshot_reconciliation",
        "run_id": "v202_read_only_paper_broker_snapshot_reconciliation",
        "symbol": "SPY",
        "generated_at": generated_at,
        "source_review_symbol": "SPY",
        "source_review_state": "ready_for_operator_review",
        "broker_observation_state": "observed",
        "reconciliation_state": "ready_for_operator_review",
        "blockers": [],
        "paper_lab_only": True,
        "not_live_authorized": True,
        "read_only_broker_observation": True,
        "paper_profile_gate_passed": True,
        "live_url_detected": live_url_detected,
        "account_observed": False,
        "positions_observed": True,
        "orders_observed": True,
        "open_orders_observed": True,
        "recent_orders_observed": False,
        "positions": positions,
        "open_orders": [],
        "recent_orders": [],
        "position_count": len(positions),
        "position_symbols": [str(position["symbol"]) for position in positions],
        "spy_position_present": spy_position_present,
        "spy_position_qty": spy_position_qty if spy_position_present else "0",
        "unexpected_non_spy_positions": [],
        "open_order_count": 0,
        "open_order_symbols": [],
        "open_spy_order_count": 0,
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "cancel_authorized": False,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "paper_execution_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_allowed": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "live_authorized": False,
        "profit_claim": "none",
        "labels": [
            "paper_lab_only",
            "read_only_broker_observation",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "broker_action_flags": {
            "submit": False,
            "cancel": False,
            "replace": False,
            "close": False,
            "liquidate": False,
            "mutation": False,
        },
    }
    if overrides:
        record.update(overrides)
    _write_jsonl(path, record)
    return record


def _write_guard_packet(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "packet_version": "v200_post_drill_operating_guard_packet_v1",
                "post_drill_guard_classification": "post_drill_guard_ready",
                "blocker": "none",
                "source_paper_drill_packet_found": True,
                "source_paper_drill_packet_parsed": True,
                "last_paper_drill_outcome": "paper_drill_submitted_cancel_confirmed",
                "latest_bounded_paper_drill": {
                    "outcome_classification": (
                        "paper_drill_submitted_cancel_confirmed"
                    ),
                    "final_broker_order_status": "canceled",
                    "client_order_id": CLIENT_ORDER_ID,
                    "broker_read_performed": True,
                    "broker_mutation_performed": True,
                    "paper_submit_performed": True,
                    "paper_cancel_performed": True,
                    "live_read_performed": False,
                    "live_mutation_performed": False,
                    "live_trading_performed": False,
                },
                "client_order_id": CLIENT_ORDER_ID,
                "final_broker_order_status_from_source_packet": "canceled",
                "last_authorization_consumed": True,
                "paper_submit_authorized": False,
                "paper_cancel_authorized": False,
                "next_paper_action_requires_new_authorization": True,
                "next_operator_action": (
                    "new_explicit_operator_authorization_required_before_any_future_paper_action"
                ),
                "source_broker_read_performed": True,
                "source_broker_mutation_performed": True,
                "source_paper_submit_performed": True,
                "source_paper_cancel_performed": True,
                "source_live_read_performed": False,
                "source_live_mutation_performed": False,
                "source_live_trading_performed": False,
                "broker_read_performed": False,
                "broker_mutation_performed": False,
                "paper_submit_performed": False,
                "paper_cancel_performed": False,
                "live_read_performed": False,
                "live_mutation_performed": False,
                "live_trading_performed": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _assert_handoff_denies_paper_authority(handoff: dict[str, object]) -> None:
    assert handoff["paper_submit_authorized"] is False
    assert handoff["paper_cancel_authorized"] is False
    assert handoff["paper_authority_granted"] is False
    assert handoff["live_authorized"] is False
    assert handoff["broker_read_performed"] is False
    assert handoff["broker_mutation_performed"] is False
    assert handoff["network_access_performed"] is False


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, record: dict[str, object]) -> None:
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
