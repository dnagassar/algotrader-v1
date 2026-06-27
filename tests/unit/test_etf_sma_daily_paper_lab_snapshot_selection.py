from __future__ import annotations

import json
from pathlib import Path

import algotrader.execution.etf_sma_daily_paper_lab as paper_lab_module
from algotrader.execution.etf_sma_daily_paper_lab import (
    EtfSmaDailyPaperLabConfig,
    run_etf_sma_daily_paper_lab,
)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"


def test_selects_latest_valid_non_stale_local_snapshot(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    older = snapshot_root / "older_snapshot.jsonl"
    latest = snapshot_root / "latest_snapshot.jsonl"
    _write_snapshot(older, generated_at="2025-07-19T12:00:00+00:00")
    _write_snapshot(latest, generated_at="2025-07-20T12:00:00+00:00")

    output_root = tmp_path / "selected_latest"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

    mission = _read_json(output_root / "mission_control.json")
    latest_run = _read_json(output_root / "latest_run.json")
    selection = mission["broker_snapshot_selection"]
    handoff = mission["broker_snapshot_handoff"]

    assert selection["selection_status"] == "selected_latest_valid_snapshot"
    assert selection["selected_path"] == latest.as_posix()
    assert selection["selected_observed_at"] == "2025-07-20T12:00:00+00:00"
    assert selection["selected_freshness_status"] == "fresh"
    assert selection["selected_validation_status"] == "passed"
    assert selection["candidate_count"] == 2
    assert handoff["handoff_status"] == "broker_snapshot_observed"
    assert handoff["source_packet_path"] == latest.as_posix()
    assert handoff["current_broker_truth_claimed"] is True
    assert latest_run["broker_snapshot_selection_status"] == (
        "selected_latest_valid_snapshot"
    )
    assert latest_run["broker_snapshot_selected_path"] == latest.as_posix()


def test_snapshot_selection_tie_breaks_deterministically_by_path(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    first = snapshot_root / "a_snapshot.jsonl"
    second = snapshot_root / "b_snapshot.jsonl"
    _write_snapshot(second, generated_at="2025-07-20T12:00:00+00:00")
    _write_snapshot(first, generated_at="2025-07-20T12:00:00+00:00")

    output_root = tmp_path / "deterministic"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

    selection = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_selection"
    ]

    assert selection["selected_path"] == first.as_posix()
    assert [
        candidate["candidate_path"] for candidate in selection["candidates"]
    ] == [first.as_posix(), second.as_posix()]
    assert [candidate["candidate_order"] for candidate in selection["candidates"]] == [
        1,
        2,
    ]


def test_missing_snapshot_roots_fail_closed(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing_snapshots"
    output_root = tmp_path / "missing"

    run_etf_sma_daily_paper_lab(_config(output_root, missing_root))

    mission = _read_json(output_root / "mission_control.json")
    selection = mission["broker_snapshot_selection"]
    handoff = mission["broker_snapshot_handoff"]

    assert selection["selection_status"] == "broker_snapshot_not_available"
    assert selection["candidate_count"] == 1
    assert selection["selected_path"] == ""
    assert selection["candidates"][0]["candidate_status"] == "not_available"
    assert selection["candidates"][0]["rejection_reason"] == "broker_snapshot_missing"
    assert handoff["handoff_status"] == "broker_snapshot_not_available"
    assert handoff["source_packet_found"] is False
    assert handoff["current_broker_truth_claimed"] is False
    _assert_handoff_denies_paper_authority(handoff)


def test_only_stale_candidates_are_visible_but_not_current_truth(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    stale_old = snapshot_root / "stale_old.jsonl"
    stale_latest = snapshot_root / "stale_latest.jsonl"
    _write_snapshot(stale_old, generated_at="2025-07-17T12:00:00+00:00")
    _write_snapshot(stale_latest, generated_at="2025-07-18T12:00:00+00:00")

    output_root = tmp_path / "stale"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

    mission = _read_json(output_root / "mission_control.json")
    latest_run = _read_json(output_root / "latest_run.json")
    selection = mission["broker_snapshot_selection"]
    handoff = mission["broker_snapshot_handoff"]

    assert selection["selection_status"] == "only_stale_candidates"
    assert selection["selected_path"] == ""
    assert selection["displayed_candidate_path"] == stale_latest.as_posix()
    assert selection["latest_stale_candidate_path"] == stale_latest.as_posix()
    assert handoff["handoff_status"] == "broker_snapshot_stale"
    assert handoff["packet_freshness_status"] == "stale_snapshot"
    assert handoff["current_broker_truth_claimed"] is False
    assert latest_run["broker_snapshot_current_broker_truth_claimed"] is False
    assert latest_run["observed_spy_position_qty"] is None
    _assert_handoff_denies_paper_authority(handoff)


def test_malformed_discovered_candidate_is_rejected_fail_closed(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    malformed = snapshot_root / "malformed.jsonl"
    malformed.write_text("{not-json}\n", encoding="utf-8")

    output_root = tmp_path / "malformed"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

    handoff = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_handoff"
    ]
    selection = handoff["selection_policy"]

    assert selection["selection_status"] == "no_valid_broker_snapshot_candidate"
    assert selection["candidates"][0]["rejection_reason"] == (
        "broker_snapshot_json_decode_error"
    )
    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert handoff["snapshot_validation_status"] == "failed"
    assert handoff["current_broker_truth_claimed"] is False
    _assert_handoff_denies_paper_authority(handoff)


def test_live_tainted_discovered_candidate_is_rejected_fail_closed(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    _write_snapshot(snapshot_root / "live.jsonl", live_url_detected=True)

    output_root = tmp_path / "live"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

    handoff = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_handoff"
    ]

    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert handoff["broker_state_status"] == "live_url_detected"
    assert "broker_snapshot_live_labeled" in handoff["snapshot_validation_errors"]
    assert handoff["current_broker_truth_claimed"] is False
    _assert_handoff_denies_paper_authority(handoff)


def test_mutation_tainted_discovered_candidate_is_rejected_fail_closed(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    _write_snapshot(
        snapshot_root / "mutation.jsonl",
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

    output_root = tmp_path / "mutation"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

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


def test_credential_tainted_candidate_is_rejected_without_serializing_or_hashing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    credential_text = "do-not-serialize-or-hash"
    _write_snapshot(
        snapshot_root / "credential.jsonl",
        overrides={"api_key": credential_text},
    )

    def fail_sha256(_content):
        raise AssertionError("credential-tainted broker snapshot was hashed")

    monkeypatch.setattr(paper_lab_module.hashlib, "sha256", fail_sha256)
    selection = paper_lab_module._select_broker_state_snapshot(
        broker_snapshot_log=None,
        broker_snapshot_roots=(snapshot_root,),
        broker_state_mode="alpaca_paper_read_only",
        symbol="SPY",
        run_date="2025-07-20",
        latest_completed_session_date="2025-07-19",
    )
    assert selection["candidates"][0]["credential_tainted"] is True
    assert selection["candidates"][0]["source_packet_sha256"] == ""
    assert selection["candidates"][0]["sha256_omitted_reason"] == (
        "credential_tainted_snapshot"
    )

    monkeypatch.undo()
    output_root = tmp_path / "credential"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

    for artifact_path in output_root.rglob("*"):
        if artifact_path.is_file():
            assert credential_text not in artifact_path.read_text(encoding="utf-8")

    handoff = _read_json(output_root / "mission_control.json")[
        "broker_snapshot_handoff"
    ]
    assert handoff["handoff_status"] == "broker_snapshot_rejected"
    assert handoff["broker_state_status"] == "credential_tainted_snapshot"
    assert handoff["source_packet_sha256"] == ""
    assert handoff["selection_policy"]["candidates"][0]["source_packet_sha256"] == ""
    _assert_handoff_denies_paper_authority(handoff)


def test_discovered_snapshot_selection_keeps_paper_authority_false(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    _write_snapshot(snapshot_root / "valid.jsonl")

    output_root = tmp_path / "authority"
    run_etf_sma_daily_paper_lab(_config(output_root, snapshot_root))

    mission = _read_json(output_root / "mission_control.json")
    latest = _read_json(output_root / "latest_run.json")
    handoff = mission["broker_snapshot_handoff"]
    selection = mission["broker_snapshot_selection"]

    assert selection["paper_submit_authorized"] is False
    assert selection["paper_cancel_authorized"] is False
    assert selection["live_authorized"] is False
    assert latest["paper_submit_authorized"] is False
    assert latest["broker_snapshot_handoff_paper_submit_authorized"] is False
    assert latest["broker_snapshot_handoff_paper_cancel_authorized"] is False
    _assert_handoff_denies_paper_authority(handoff)


def _config(
    output_root: Path,
    broker_snapshot_root: Path,
) -> EtfSmaDailyPaperLabConfig:
    return EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
        as_of_date="2025-07-19",
        run_date="2025-07-20",
        symbol="SPY",
        broker_state_mode="alpaca_paper_read_only",
        broker_snapshot_roots=(broker_snapshot_root,),
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
        "run_id": "v203_read_only_paper_broker_snapshot_reconciliation",
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
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return record


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
