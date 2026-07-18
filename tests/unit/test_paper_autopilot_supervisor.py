from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.exchange_session import NyseExchangeSessionCalendar
from algotrader.execution.order_journal import SqliteOrderJournal
from algotrader.execution.paper_autopilot_supervisor import (
    PaperAutopilotSupervisor,
    PaperAutopilotSupervisorConfig,
)


AFTER_REGULAR_CLOSE = datetime(2026, 7, 10, 21, 15, tzinfo=UTC)


def _config(tmp_path: Path, *, attempts: int = 2) -> PaperAutopilotSupervisorConfig:
    return PaperAutopilotSupervisorConfig(
        journal_path=tmp_path / "state" / "orders.sqlite3",
        output_root=tmp_path / "out",
        bars_csv=tmp_path / "bars.csv",
        max_cycle_attempts=attempts,
    )


def _success(calls: list[str]):
    def runner(*args, **kwargs):
        calls.append(kwargs["timestamp"])
        return {"operator_summary": {"operator_exit_code": 0}}

    return runner


def _run_once(
    config: PaperAutopilotSupervisorConfig,
    now: datetime,
    runner,
    *,
    owner: str,
) -> PaperAutopilotSupervisor:
    supervisor = PaperAutopilotSupervisor(
        config,
        clock=lambda: now,
        sleeper=lambda seconds: None,
        operator_runner=runner,
        owner_run_id=owner,
    )
    supervisor.run(max_loops=1)
    return supervisor


def test_calendar_rejects_weekend_holiday_and_incomplete_session() -> None:
    calendar = NyseExchangeSessionCalendar()

    assert calendar.latest_completed_session(
        datetime(2026, 7, 11, 21, 15, tzinfo=UTC)
    ) is None
    assert calendar.latest_completed_session(
        datetime(2026, 11, 26, 21, 15, tzinfo=UTC)
    ) is None
    assert calendar.latest_completed_session(
        datetime(2026, 7, 10, 19, 59, tzinfo=UTC)
    ) is None


def test_calendar_uses_early_close_boundary_and_deterministic_identity() -> None:
    calendar = NyseExchangeSessionCalendar()

    before = calendar.latest_completed_session(
        datetime(2026, 12, 24, 17, 59, tzinfo=UTC)
    )
    after = calendar.latest_completed_session(
        datetime(2026, 12, 24, 18, 0, tzinfo=UTC)
    )

    assert before is None
    assert after is not None
    assert after.identity == "NYSE:2026-12-24"
    assert after.early_close is True


def test_exactly_one_success_in_process_and_after_restart(tmp_path: Path) -> None:
    calls: list[str] = []
    config = _config(tmp_path)
    supervisor = _run_once(config, AFTER_REGULAR_CLOSE, _success(calls), owner="one")
    supervisor.run(max_loops=1)
    _run_once(config, AFTER_REGULAR_CLOSE, _success(calls), owner="restart")

    cycle = SqliteOrderJournal(config.journal_path).get_supervisor_cycle("NYSE:2026-07-10")
    assert calls == [AFTER_REGULAR_CLOSE.isoformat()]
    assert cycle is not None and cycle.succeeded is True
    assert cycle.attempt_count == 1


def test_duplicate_start_is_fenced_before_cycle(tmp_path: Path) -> None:
    config = _config(tmp_path)
    journal = SqliteOrderJournal(config.journal_path)
    journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="existing",
        occurred_at=AFTER_REGULAR_CLOSE,
        ttl_seconds=60,
    )
    calls: list[str] = []
    supervisor = PaperAutopilotSupervisor(
        config,
        clock=lambda: AFTER_REGULAR_CLOSE,
        sleeper=lambda seconds: None,
        operator_runner=_success(calls),
        owner_run_id="duplicate",
    )

    with pytest.raises(ValidationError, match="runtime_instance_already_active"):
        supervisor.run(max_loops=1)

    assert calls == []


def test_stale_token_cannot_renew_or_release_replacement(tmp_path: Path) -> None:
    journal = SqliteOrderJournal(tmp_path / "orders.sqlite3")
    first = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="first",
        occurred_at=AFTER_REGULAR_CLOSE,
        ttl_seconds=10,
    )
    replacement = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="replacement",
        occurred_at=AFTER_REGULAR_CLOSE + timedelta(seconds=11),
        ttl_seconds=60,
    )

    stale_renew = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="first",
        occurred_at=AFTER_REGULAR_CLOSE + timedelta(seconds=12),
        ttl_seconds=60,
        lease_token=first.lease_token,
    )
    stale_release = journal.release_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="first",
        lease_token=first.lease_token,
    )

    assert replacement.fencing_generation == first.fencing_generation + 1
    assert stale_renew.acquired is False
    assert stale_release is False


def test_pause_keeps_supervisor_alive_but_skips_cycle(tmp_path: Path) -> None:
    config = _config(tmp_path)
    journal = SqliteOrderJournal(config.journal_path)
    journal.set_runtime_control(
        trading_enabled=False,
        reason="operator_pause",
        occurred_at=AFTER_REGULAR_CLOSE,
    )
    calls: list[str] = []

    _run_once(config, AFTER_REGULAR_CLOSE, _success(calls), owner="paused")

    assert calls == []
    assert journal.get_runtime_control().trading_enabled is False
    assert journal.get_supervisor_cycle("NYSE:2026-07-10") is None


def test_stop_request_releases_by_owner_without_changing_pause_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    journal = SqliteOrderJournal(config.journal_path)
    journal.set_runtime_control(
        trading_enabled=True,
        reason="running",
        occurred_at=AFTER_REGULAR_CLOSE,
        stop_requested=True,
    )
    calls: list[str] = []

    _run_once(config, AFTER_REGULAR_CLOSE, _success(calls), owner="stopping")

    control = journal.get_runtime_control()
    lease = journal.get_lease_details("paper-autopilot")
    assert calls == []
    assert control.stop_requested is True
    assert control.trading_enabled is True
    assert lease is not None and lease.expires_at <= AFTER_REGULAR_CLOSE


def test_heartbeat_failure_stops_before_cycle(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls: list[str] = []
    supervisor = PaperAutopilotSupervisor(
        config,
        clock=lambda: AFTER_REGULAR_CLOSE,
        sleeper=lambda seconds: None,
        operator_runner=_success(calls),
        owner_run_id="heartbeat",
    )
    supervisor.journal.update_heartbeat = lambda **kwargs: False  # type: ignore[method-assign]

    supervisor.run(max_loops=1)

    assert calls == []
    assert supervisor.journal.get_runtime_control().last_blocked_reason == "heartbeat_lease_lost"


def test_retryable_failure_is_bounded_then_successful(tmp_path: Path) -> None:
    config = _config(tmp_path, attempts=2)
    outcomes = [
        {"operator_summary": {"operator_exit_code": 1}, "loop_error": "local_io_failure"},
        {"operator_summary": {"operator_exit_code": 0}},
    ]
    calls: list[str] = []

    def runner(*args, **kwargs):
        calls.append(kwargs["timestamp"])
        return outcomes.pop(0)

    _run_once(config, AFTER_REGULAR_CLOSE, runner, owner="retry-one")
    _run_once(config, AFTER_REGULAR_CLOSE, runner, owner="retry-two")

    cycle = SqliteOrderJournal(config.journal_path).get_supervisor_cycle("NYSE:2026-07-10")
    assert len(calls) == 2
    assert cycle is not None and cycle.succeeded is True
    assert cycle.attempt_count == 2


def test_safety_and_ambiguous_failure_never_retries(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls: list[str] = []

    def ambiguous(*args, **kwargs):
        calls.append("ambiguous")
        return {
            "operator_summary": {"operator_exit_code": 1},
            "action_result": {"submit_response_ambiguous": True},
        }

    _run_once(config, AFTER_REGULAR_CLOSE, ambiguous, owner="ambiguous-one")
    _run_once(config, AFTER_REGULAR_CLOSE, _success(calls), owner="ambiguous-two")

    cycle = SqliteOrderJournal(config.journal_path).get_supervisor_cycle("NYSE:2026-07-10")
    assert calls == ["ambiguous"]
    assert cycle is not None and cycle.outcome == "safety_failure"
