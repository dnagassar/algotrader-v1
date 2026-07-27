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
        pending_event = executor._build_base_ledger_event(
            session_id=session_id,
            as_of="2026-07-25T00:15:00Z",
            attempt_number=i,
            run_id=f"network-{session_id}-{i}",
            reservation_id=f"network-{session_id}-{i}",
            ledger_status="pending",
            exit_code=None,
            adapter_refresh_state=None,
            network_access_attempted=False,
            interlock_verdict={"paper_boundary_ok": True},
            credential_present=True,
            refusal_category=None,
        )
        completed_event = executor._build_base_ledger_event(
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
        lines.append(json.dumps(pending_event))
        lines.append(json.dumps(completed_event))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z",
        apply=True,
    )
    assert result["exit_code"] == 2
    assert result["refusal_category"] == "session_attempt_budget_exhausted"

    records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 9
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


def test_as_of_validation_strict_utc_refusals() -> None:
    for invalid in ("", "   ", "not-a-date", "2026-07-25T00:15:00", "2026-07-24T20:15:00-04:00", "2026-07-25T05:15:00+05:00"):
        with pytest.raises(ValidationError, match="as_of_invalid"):
            executor._parse_as_of(invalid)

    # Valid UTC ISO strings
    dt1 = executor._parse_as_of("2026-07-25T00:15:00Z")
    assert dt1.tzinfo == UTC
    dt2 = executor._parse_as_of("2026-07-25T00:15:00+00:00")
    assert dt2.tzinfo == UTC


def test_cli_main_handles_missing_or_invalid_args_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    # Missing --as-of
    exit1 = main([])
    assert exit1 == 2
    captured1 = capsys.readouterr()
    data1 = json.loads(captured1.out)
    assert data1["refusal_category"] == "parser_invalid_argument"

    # Invalid naive --as-of
    exit2 = main(["--as-of", "2026-07-25T00:15:00"])
    assert exit2 == 2
    captured2 = capsys.readouterr()
    data2 = json.loads(captured2.out)
    assert data2["refusal_category"] == "as_of_invalid"


def test_seam_freezes_the_read_only_tiingo_refresh_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # These invariants used to be asserted against the scheduled task's command
    # line (test_spy_eod_market_data_refresh_schedule.py). V5.51 moved the
    # unattended path to this seam, which builds the config itself, so they are
    # re-anchored here rather than dropped.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "dummy_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "dummy_secret")
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".env").write_text("TIINGO_API_KEY=test_token_value\n", encoding="utf-8")

    captured: dict[str, Any] = {}

    def _capture(config: Any, token_lookup: Any) -> dict[str, Any]:
        captured["config"] = config
        return {"refresh_state": "accepted"}

    monkeypatch.setattr(executor, "run_spy_adjusted_data_refresh", _capture)

    result = run_autonomy_read_only_network_executor(
        as_of="2026-07-25T00:15:00Z", apply=True
    )
    assert result["exit_code"] == 0

    config = captured["config"]
    assert config.provider == "tiingo"
    assert config.symbol == "SPY"
    assert config.mode == "live_market_data_fetch"
    assert config.live_fetch_authorized is True
    assert config.revision_lookback_days == 10
    assert config.start_date == "auto"
    assert config.soak_required_sessions == 5
    assert config.token_env_var == "TIINGO_API_KEY"
    assert Path(config.canonical_csv).name == (
        "m446_spy_daily_tiingo_adjusted_canonical.csv"
    )
    assert Path(config.raw_response_path).name == "tiingo_spy_adjusted_raw_latest.json"
    assert Path(config.soak_ledger).name == (
        "spy_adjusted_market_data_soak_ledger.jsonl"
    )
    assert Path(config.soak_report).name == "spy_adjusted_market_data_soak_report.json"


def test_cli_main_does_not_blame_the_command_line_for_internal_failures(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The seam returns every refusal it can name in its result dict, so a
    # ValidationError escaping the run function is an internal failure. It must
    # not be reported as `parser_invalid_argument` on a perfectly valid CLI.
    def _boom(**_kwargs: object) -> dict[str, object]:
        raise ValidationError("provider_row_count_exceeded")

    monkeypatch.setattr(
        executor, "run_autonomy_read_only_network_executor", _boom
    )

    exit_code = main(["--as-of", "2026-07-25T00:15:00Z"])

    assert exit_code == 2
    data = json.loads(capsys.readouterr().out)
    assert data["refusal_category"] == "unexpected_validation_error"
    assert data["action_token"] == (
        "run_authorized_read_only_market_data_refresh_to_seed_soak"
    )


def test_ledger_validation_comprehensive_corruption_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    # Case 1: Directory at ledger_path
    ledger_path.mkdir(exist_ok=True)
    res_dir = run_autonomy_read_only_network_executor(as_of="2026-07-25T00:15:00Z", apply=True)
    assert res_dir["exit_code"] == 2
    assert res_dir["refusal_category"] == "ledger_corrupt"
    ledger_path.rmdir()

    # Case 2: Extra keys in ledger record
    base_event = executor._build_base_ledger_event(
        session_id="2026-07-24",
        as_of="2026-07-25T00:15:00Z",
        attempt_number=1,
        run_id="network-2026-07-24-1",
        reservation_id="network-2026-07-24-1",
        ledger_status="pending",
        exit_code=None,
        adapter_refresh_state=None,
        network_access_attempted=False,
        interlock_verdict={"paper_boundary_ok": True},
        credential_present=True,
        refusal_category=None,
    )
    event_extra = dict(base_event)
    event_extra["unexpected_extra_field"] = "bad"
    ledger_path.write_text(json.dumps(event_extra) + "\n", encoding="utf-8")
    res_extra = run_autonomy_read_only_network_executor(as_of="2026-07-25T00:15:00Z", apply=True)
    assert res_extra["exit_code"] == 2
    assert res_extra["refusal_category"] == "ledger_corrupt"

    # Case 3: Completed without prior matching pending reservation
    completed_orphan = executor._build_base_ledger_event(
        session_id="2026-07-24",
        as_of="2026-07-25T00:15:00Z",
        attempt_number=1,
        run_id="network-2026-07-24-1",
        reservation_id="network-2026-07-24-1",
        ledger_status="completed",
        exit_code=0,
        adapter_refresh_state="accepted",
        network_access_attempted=True,
        interlock_verdict={"paper_boundary_ok": True},
        credential_present=True,
        refusal_category=None,
    )
    ledger_path.write_text(json.dumps(completed_orphan) + "\n", encoding="utf-8")
    res_orphan = run_autonomy_read_only_network_executor(as_of="2026-07-25T00:15:00Z", apply=True)
    assert res_orphan["exit_code"] == 2
    assert res_orphan["refusal_category"] == "ledger_corrupt"

    # Case 4: Valid pending reservation (crash-surviving) is budget-consuming
    ledger_path.write_text(json.dumps(base_event) + "\n", encoding="utf-8")
    count, records = executor._read_and_validate_ledger(ledger_path, "2026-07-24")
    assert count == 1
    assert len(records) == 1


def test_credential_provider_loads_dotenv_token_exactly_once_and_emits_secret_free_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "dummy_key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "dummy_secret")
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)
    secret_value = "secret_tiingo_token_99999"
    (tmp_path / ".env").write_text(f"TIINGO_API_KEY={secret_value}\n", encoding="utf-8")

    load_call_count = 0
    real_load = executor.load_tiingo_api_key_from_dotenv

    def _counted_load(path: Path, token_env_var: str = "TIINGO_API_KEY") -> str | None:
        nonlocal load_call_count
        load_call_count += 1
        return real_load(path, token_env_var=token_env_var)

    monkeypatch.setattr(executor, "load_tiingo_api_key_from_dotenv", _counted_load)

    def _dummy_run_spy_refresh(config: Any, token_lookup: Any) -> dict[str, Any]:
        val = token_lookup("TIINGO_API_KEY")
        assert val == secret_value
        return {"refresh_state": "accepted"}

    monkeypatch.setattr(executor, "run_spy_adjusted_data_refresh", _dummy_run_spy_refresh)

    exit_code = main(["--as-of", "2026-07-25T00:15:00Z", "--apply", "--format", "json"])
    assert exit_code == 0
    assert load_call_count == 1

    captured = capsys.readouterr()
    assert secret_value not in captured.out
    assert secret_value not in captured.err

    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    ledger_text = ledger_path.read_text(encoding="utf-8")
    assert secret_value not in ledger_text


def test_ledger_validation_rejects_duplicate_pending_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    pending_event = executor._build_base_ledger_event(
        session_id="2026-07-24",
        as_of="2026-07-25T00:15:00Z",
        attempt_number=1,
        run_id="network-2026-07-24-1",
        reservation_id="network-2026-07-24-1",
        ledger_status="pending",
        exit_code=None,
        adapter_refresh_state=None,
        network_access_attempted=False,
        interlock_verdict={"paper_boundary_ok": True},
        credential_present=True,
        refusal_category=None,
    )
    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(pending_event) + "\n" + json.dumps(pending_event) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="ledger_corrupt"):
        executor._read_and_validate_ledger(ledger_path, "2026-07-24")

    res = run_autonomy_read_only_network_executor(as_of="2026-07-25T00:15:00Z", apply=True)
    assert res["exit_code"] == 2
    assert res["refusal_category"] == "ledger_corrupt"


def test_ledger_validation_rejects_completed_mismatched_with_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    pending_event = executor._build_base_ledger_event(
        session_id="2026-07-24",
        as_of="2026-07-25T00:15:00Z",
        attempt_number=1,
        run_id="network-2026-07-24-1",
        reservation_id="network-2026-07-24-1",
        ledger_status="pending",
        exit_code=None,
        adapter_refresh_state=None,
        network_access_attempted=False,
        interlock_verdict={"paper_boundary_ok": True},
        credential_present=True,
        refusal_category=None,
    )
    completed_mismatched = executor._build_base_ledger_event(
        session_id="2026-07-24",
        as_of="2026-07-25T00:15:00Z",
        attempt_number=2,  # Mismatched attempt_number!
        run_id="network-2026-07-24-1",
        reservation_id="network-2026-07-24-1",
        ledger_status="completed",
        exit_code=0,
        adapter_refresh_state="accepted",
        network_access_attempted=True,
        interlock_verdict={"paper_boundary_ok": True},
        credential_present=True,
        refusal_category=None,
    )
    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(pending_event) + "\n" + json.dumps(completed_mismatched) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="ledger_corrupt"):
        executor._read_and_validate_ledger(ledger_path, "2026-07-24")


def test_ledger_validation_rejects_blank_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    pending_event = executor._build_base_ledger_event(
        session_id="2026-07-24",
        as_of="2026-07-25T00:15:00Z",
        attempt_number=1,
        run_id="network-2026-07-24-1",
        reservation_id="network-2026-07-24-1",
        ledger_status="pending",
        exit_code=None,
        adapter_refresh_state=None,
        network_access_attempted=False,
        interlock_verdict={"paper_boundary_ok": True},
        credential_present=True,
        refusal_category=None,
    )
    ledger_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(pending_event) + "\n\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="ledger_corrupt"):
        executor._read_and_validate_ledger(ledger_path, "2026-07-24")


def test_acquire_lock_handles_parent_mkdir_or_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "src" / "algotrader").mkdir(parents=True, exist_ok=True)

    def _failing_mkdir(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("Access denied")

    monkeypatch.setattr(Path, "mkdir", _failing_mkdir)

    lock_path = tmp_path / "runs" / "autonomy_network_executor" / "ledger.lock"
    lock_obj = executor._acquire_lock(lock_path)
    assert lock_obj is None

    res = run_autonomy_read_only_network_executor(as_of="2026-07-25T00:15:00Z", apply=True)
    assert res["exit_code"] == 2
    assert res["refusal_category"] == "ledger_lock_unavailable"
