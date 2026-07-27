"""Tests for the autonomy read-only network executor seam."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

import pytest

from algotrader.errors import ValidationError
from algotrader.execution import autonomy_read_only_network_executor as executor
from algotrader.execution.autonomy_read_only_network_executor import (
    AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST,
    main,
    run_autonomy_read_only_network_executor,
)


def test_allowlist_contains_expected_token() -> None:
    token = "run_authorized_read_only_market_data_refresh_to_seed_soak"
    assert token in AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST
    cmd = AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST[token]
    assert "autonomy_read_only_network_executor" in cmd
    assert "--as-of" in cmd
    assert "[--apply]" in cmd
    assert "--format json" in cmd


def test_cli_parser_refuses_unknown_argument(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--as-of", "2026-07-24T20:15:00Z", "--unknown-arg"])
    assert exit_code == 2
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["refusal_category"] == "parser_invalid_argument"


def test_as_of_parsing_and_expected_session_derivation() -> None:
    # 2026-07-24 is a Friday.
    # 20:15 ET is 2026-07-25T00:15:00Z (EDT is UTC-4). After 20:10 ET -> Friday July 24, 2026.
    dt_after_cutoff = executor._parse_as_of("2026-07-25T00:15:00Z")
    session1 = executor._resolve_expected_session(dt_after_cutoff)
    assert session1.isoformat() == "2026-07-24"

    # Before cutoff (e.g. 19:00 ET -> 23:00 UTC) -> previous completed session (Thursday July 23, 2026).
    dt_before_cutoff = executor._parse_as_of("2026-07-24T23:00:00Z")
    session2 = executor._resolve_expected_session(dt_before_cutoff)
    assert session2.isoformat() == "2026-07-23"


def test_as_of_invalid_refusal() -> None:
    result = run_autonomy_read_only_network_executor(as_of="not-a-timestamp")
    assert result["exit_code"] == 2
    assert result["refusal_category"] == "as_of_invalid"


def test_short_circuit_when_session_already_qualified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)
    soak_report_path = tmp_path / "runs" / "paper_lab" / "spy_adjusted_market_data_soak_report.json"
    soak_report_path.parent.mkdir(parents=True, exist_ok=True)
    soak_report_path.write_text(
        json.dumps({"qualifying_session_dates": ["2026-07-24"]}),
        encoding="utf-8",
    )

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=False,
    )
    assert result["exit_code"] == 0
    assert result["session_already_qualified"] is True
    assert result["network_access_attempted"] is False

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    assert not ledger_path.exists()


def test_dry_run_pending_returns_exit_1_and_zero_ledger_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=False,
    )
    assert result["exit_code"] == 1
    assert result["apply"] is False
    assert result["session_already_qualified"] is False
    assert "apply_eligible" in result
    assert result["network_access_attempted"] is False

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    assert not ledger_path.exists()


def test_lock_timeout_refusal_returns_exit_2_and_zero_ledger_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    lock_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.lock"
    lock_file = executor._acquire_lock(lock_path, timeout_seconds=1.0)
    assert lock_file is not None

    try:
        def _fast_acquire(p: Path, timeout_seconds: float = 5.0) -> Any:
            return None

        monkeypatch.setattr(executor, "_acquire_lock", _fast_acquire)

        result = run_autonomy_read_only_network_executor(
            as_of="2026-07-25T00:15:00Z",
            apply=True,
        )
        assert result["exit_code"] == 2
        assert result["refusal_category"] == "ledger_lock_unavailable"

        ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
        assert not ledger_path.exists()
    finally:
        executor._release_lock(lock_file)


def test_ledger_corrupt_refusal_returns_exit_2_and_zero_ledger_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("invalid-json-content\n", encoding="utf-8")

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=True,
    )
    assert result["exit_code"] == 2
    assert result["refusal_category"] == "ledger_corrupt"
    assert ledger_path.read_text(encoding="utf-8") == "invalid-json-content\n"


def test_session_attempt_budget_exhausted_writes_one_refused_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "dummy_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "dummy_secret")
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    session_id = "2026-07-24"
    lines = []
    for i in range(1, 5):
        event = executor._build_base_ledger_event(
            session_id=session_id,
            as_of="2026-07-25T00:15:00Z",
            attempt_number=i,
            run_id=f"network-{session_id}-{i}",
            reservation_id=f"network-{session_id}-{i}",
            ledger_status="completed",
            exit_code=1,
            adapter_refresh_state="blocked_test",
            network_access_attempted=True,
            interlock_verdict={"paper_boundary_ok": True},
            credential_present=True,
            refusal_category=None,
        )
        lines.append(json.dumps(event))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=True,
    )
    assert result["exit_code"] == 2
    assert result["refusal_category"] == "session_attempt_budget_exhausted"

    records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 5
    refused_event = records[-1]
    assert refused_event["ledger_status"] == "refused"
    assert refused_event["refusal_category"] == "session_attempt_budget_exhausted"
    assert refused_event["attempt_budget_exhausted"] is True
    assert refused_event["interlock_verdict"] is None
    assert refused_event["reservation_id"] is None


def test_token_not_available_refusal_writes_one_refused_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "dummy_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "dummy_secret")
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=True,
    )
    assert result["exit_code"] == 2
    assert result["refusal_category"] == "token_not_available"

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 1
    assert records[0]["ledger_status"] == "refused"
    assert records[0]["refusal_category"] == "token_not_available"
    assert records[0]["credential_present"] is False
    assert records[0]["interlock_verdict"] is not None


def test_successful_apply_writes_reservation_and_completion_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "dummy_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "dummy_secret")
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".env").write_text("TIINGO_API_KEY=test_token_value\n", encoding="utf-8")

    def _dummy_run_spy_refresh(config: Any, token_lookup: Any) -> dict[str, Any]:
        assert token_lookup("TIINGO_API_KEY") == "test_token_value"
        return {"refresh_state": "accepted"}

    monkeypatch.setattr(executor, "run_spy_adjusted_data_refresh", _dummy_run_spy_refresh)

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=True,
    )
    assert result["exit_code"] == 0
    assert result["adapter_refresh_state"] == "accepted"
    assert result["network_access_attempted"] is True

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 2

    pending_event = records[0]
    assert pending_event["ledger_status"] == "pending"
    assert pending_event["network_access_attempted"] is False
    assert pending_event["exit_code"] is None
    assert pending_event["reservation_id"] == result["run_id"]

    completed_event = records[1]
    assert completed_event["ledger_status"] == "completed"
    assert completed_event["network_access_attempted"] is True
    assert completed_event["exit_code"] == 0
    assert completed_event["adapter_refresh_state"] == "accepted"
    assert completed_event["reservation_id"] == result["run_id"]


def test_live_capital_interlock_blocked_refusal_writes_one_refused_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_PROFILE", "live")
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=True,
    )
    assert result["exit_code"] == 2
    assert result["refusal_category"] == "live_capital_interlock_blocked"

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 1
    assert records[0]["ledger_status"] == "refused"
    assert records[0]["refusal_category"] == "live_capital_interlock_blocked"

