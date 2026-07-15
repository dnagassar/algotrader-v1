from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_market_data_soak import (
    build_adjusted_market_data_soak_receipt,
    build_adjusted_market_data_soak_report,
    record_adjusted_market_data_soak,
)


def test_soak_report_qualifies_five_consecutive_sessions_across_weekend(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "soak.jsonl"
    report_path = tmp_path / "report.json"
    sessions = (
        "2026-07-09",
        "2026-07-10",
        "2026-07-13",
        "2026-07-14",
        "2026-07-15",
    )

    first = record_adjusted_market_data_soak(
        _accepted_payload(sessions[0]),
        ledger_path=ledger,
        report_path=report_path,
        observed_at=_observed(9),
    )
    assert first["evidence_state"] == "collecting_unattended_market_data_soak"
    assert first["remaining_consecutive_sessions"] == 4
    assert first["next_expected_session_date"] == "2026-07-10"

    # A retry remains a separate attempt but cannot inflate the distinct-session streak.
    record_adjusted_market_data_soak(
        _accepted_payload(sessions[0]),
        ledger_path=ledger,
        report_path=report_path,
        observed_at=_observed(9, hour=21),
    )
    for day, session in enumerate(sessions[1:], start=10):
        final = record_adjusted_market_data_soak(
            _accepted_payload(session),
            ledger_path=ledger,
            report_path=report_path,
            observed_at=_observed(day),
        )

    assert final["evidence_state"] == "accepted_unattended_market_data_soak"
    assert final["classification"] == "unattended_authoritative_market_data_proven"
    assert final["attempt_count"] == 6
    assert final["distinct_attempted_session_count"] == 5
    assert final["current_consecutive_qualifying_sessions"] == 5
    assert final["remaining_consecutive_sessions"] == 0
    assert final["strategy_evidence_produced"] is False
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 6
    assert json.loads(report_path.read_text(encoding="utf-8")) == final


def test_latest_failure_resets_streak_until_same_session_retry_succeeds() -> None:
    receipts = [
        build_adjusted_market_data_soak_receipt(
            _accepted_payload("2026-07-09"), observed_at=_observed(9)
        ),
        build_adjusted_market_data_soak_receipt(
            _accepted_payload("2026-07-10"), observed_at=_observed(10)
        ),
        build_adjusted_market_data_soak_receipt(
            _failed_payload("2026-07-13"), observed_at=_observed(13)
        ),
    ]

    blocked = build_adjusted_market_data_soak_report(receipts)
    assert blocked["evidence_state"] == "blocked_latest_expected_session_not_accepted"
    assert blocked["current_consecutive_qualifying_sessions"] == 0
    assert blocked["failed_session_dates"] == ["2026-07-13"]
    assert blocked["next_expected_session_date"] == "2026-07-13"

    receipts.append(
        build_adjusted_market_data_soak_receipt(
            _accepted_payload("2026-07-13"), observed_at=_observed(13, hour=21)
        )
    )
    recovered = build_adjusted_market_data_soak_report(receipts)
    assert recovered["evidence_state"] == "collecting_unattended_market_data_soak"
    assert recovered["current_consecutive_qualifying_sessions"] == 3
    assert recovered["failed_session_dates"] == []
    assert recovered["next_expected_session_date"] == "2026-07-14"


def test_offline_or_unsafe_refresh_cannot_qualify() -> None:
    payload = _accepted_payload("2026-07-15")
    payload["mode"] = "offline_fixture"
    payload["broker_access_attempted"] = True

    receipt = build_adjusted_market_data_soak_receipt(
        payload,
        observed_at=_observed(15),
    )

    assert receipt["qualifying"] is False
    assert "refresh_mode_not_live_market_data_fetch" in receipt[
        "qualification_blockers"
    ]
    assert "unsafe_flag_true:broker_access_attempted" in receipt[
        "qualification_blockers"
    ]


def test_invalid_existing_ledger_is_preserved(tmp_path: Path) -> None:
    ledger = tmp_path / "soak.jsonl"
    report = tmp_path / "report.json"
    ledger.write_bytes(b"not-json\n")

    with pytest.raises(ValidationError, match="invalid JSON"):
        record_adjusted_market_data_soak(
            _accepted_payload("2026-07-15"),
            ledger_path=ledger,
            report_path=report,
            observed_at=_observed(15),
        )

    assert ledger.read_bytes() == b"not-json\n"
    assert not report.exists()


def test_repository_source_paths_are_rejected() -> None:
    with pytest.raises(ValidationError, match="runtime output path"):
        record_adjusted_market_data_soak(
            _accepted_payload("2026-07-15"),
            ledger_path="src/soak.jsonl",
            report_path="runs/soak-report.json",
            observed_at=_observed(15),
        )


def _accepted_payload(session: str) -> dict[str, object]:
    return {
        "mode": "live_market_data_fetch",
        "refresh_authorized": True,
        "refresh_state": "accepted_adjusted_spy_data_refresh",
        "expected_latest_bar_date": session,
        "latest_provider_bar_date": session,
        "http_outcome_category": "success",
        "network_access_attempted": True,
        "network_destination_allowlist_enforced": True,
        "revision_check_performed": True,
        "revision_outcome": "revision_window_checked_no_change",
        "canonical_csv_sha256": f"canonical-{session}",
        "source_sha256": f"source-{session}",
        "refresh_blockers": [],
        "refresh_warnings": [],
        "market_data_token_value_printed": False,
        "market_data_token_value_written": False,
        "broker_access_attempted": False,
        "broker_mutation_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_authorized": False,
        "live_trading_performed": False,
        "canonical_changed": False,
    }


def _failed_payload(session: str) -> dict[str, object]:
    payload = _accepted_payload(session)
    payload.update(
        refresh_state="blocked_live_market_data_fetch_http_failed",
        latest_provider_bar_date="",
        http_outcome_category="timeout",
        canonical_csv_sha256="",
        source_sha256="",
        revision_check_performed=False,
        revision_outcome="not_checked",
        refresh_blockers=["market_data_http_timeout"],
    )
    return payload


def _observed(day: int, *, hour: int = 20) -> datetime:
    return datetime(2026, 7, day, hour, 10, tzinfo=UTC)
