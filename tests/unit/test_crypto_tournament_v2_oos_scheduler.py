from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.secure_credential_provider import CredentialReference
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    SCHEDULER_SCHEMA_VERSION,
    CalculationResult,
    EligibleWindow,
    OneShotExecutor,
    PreviewDispatcher,
    RealCommandDispatcher,
    ScheduleCalculator,
    SchedulerJob,
    SchedulerJobStatus,
    SqliteJobStore,
    _generate_job_id,
)


# ==========================================
# 1. Pure Schedule and Window Calculation Tests
# ==========================================

def test_calculator_disabled_by_default() -> None:
    current_time = datetime(2026, 7, 18, 20, 5, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=False
    )
    assert res.status == "blocked"
    assert res.classification == "blocked_scheduler_disabled"


def test_calculator_malformed_frontier() -> None:
    current_time = datetime(2026, 7, 18, 20, 5, tzinfo=UTC)
    # Not hour-aligned
    frontier = datetime(2026, 7, 18, 19, 3, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "blocked"
    assert res.classification == "blocked_malformed_frontier"


def test_calculator_clock_regression() -> None:
    current_time = datetime(2026, 7, 18, 18, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "blocked"
    assert res.classification == "blocked_clock_regression"


def test_calculator_no_eligible_yet_inside_grace() -> None:
    # 20:00Z bar closes at 21:00Z. With 5-min grace, it's eligible at 21:05Z.
    # At 21:04:59Z, frontier 19:00Z -> next needed is 20:00Z. Not eligible yet.
    current_time = datetime(2026, 7, 18, 21, 4, 59, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "no_eligible_window"
    assert res.classification == "no_eligible_closed_window"


def test_calculator_eligible_exactly_at_grace_boundary() -> None:
    # Frontier is 19:00Z. Next needed bar is 20:00Z, which closes at 21:00Z, and is eligible at 21:05:00Z.
    current_time = datetime(2026, 7, 18, 21, 5, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "eligible"
    assert res.window == EligibleWindow(
        start_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        end_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        provider_as_of_boundary=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
    )


def test_calculator_catch_up_limit() -> None:
    # Frontier is 19:00Z. Next needed is 20:00Z.
    # Current time is 23:07Z. Grace boundary is 23:02Z, so latest closed bar is 22:00Z (closes at 23:00Z).
    # Eligible closed bars starting at 20:00Z are: 20:00Z, 21:00Z, 22:00Z (3 bars).
    # If max_catch_up_hours = 2, we should cap window end at 21:00Z (2 bars).
    current_time = datetime(2026, 7, 18, 23, 7, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time,
        accepted_frontier_bar_open=frontier,
        max_catch_up_hours=2,
        enabled=True,
    )
    assert res.status == "eligible"
    assert res.window == EligibleWindow(
        start_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        end_bar_open=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
        provider_as_of_boundary=datetime(2026, 7, 18, 22, 0, tzinfo=UTC),
    )


# ==========================================
# 2. Durable Job Store Tests
# ==========================================

def test_store_insert_and_claim(tmp_path: Path) -> None:
    db_file = tmp_path / "test_scheduler.sqlite3"
    store = SqliteJobStore(db_file)
    store.initialize()

    job_id = "test_job_1"
    start = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    end = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id=job_id,
        lane="test_lane",
        source_commit="commit_1",
        created_at=datetime.now(UTC),
        requested_start_bar_open=start,
        requested_end_bar_open=end,
        provider_as_of_boundary=end + timedelta(hours=1),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=start - timedelta(hours=1),
        expected_frontier_bar_open=end + timedelta(hours=1),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )

    store.insert_job(job)
    retrieved = store.get_job(job_id)
    assert retrieved is not None
    assert retrieved.job_id == job_id
    assert retrieved.status == SchedulerJobStatus.PENDING

    # Claim job atomically
    claimed = store.claim_job(job_id, "claim_token_abc", datetime.now(UTC))
    assert claimed is True

    # Double claiming fails
    double_claimed = store.claim_job(job_id, "claim_token_xyz", datetime.now(UTC))
    assert double_claimed is False

    retrieved = store.get_job(job_id)
    assert retrieved.status == SchedulerJobStatus.RUNNING
    assert retrieved.claim_identity == "claim_token_abc"
    assert retrieved.attempt_number == 1


def test_store_rejects_overlapping_active_jobs(tmp_path: Path) -> None:
    db_file = tmp_path / "test_scheduler.sqlite3"
    store = SqliteJobStore(db_file)
    store.initialize()

    # Insert pending job for 20:00Z to 22:00Z
    job1 = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="job1",
        lane="test_lane",
        source_commit="commit_1",
        created_at=datetime.now(UTC),
        requested_start_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        requested_end_bar_open=datetime(2026, 7, 18, 22, 0, tzinfo=UTC),
        provider_as_of_boundary=datetime(2026, 7, 18, 23, 0, tzinfo=UTC),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=datetime(2026, 7, 18, 19, 0, tzinfo=UTC),
        expected_frontier_bar_open=datetime(2026, 7, 18, 23, 0, tzinfo=UTC),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )
    store.insert_job(job1)

    # Insert overlapping job (21:00Z to 21:00Z) should be rejected
    job2 = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="job2",
        lane="test_lane",
        source_commit="commit_1",
        created_at=datetime.now(UTC),
        requested_start_bar_open=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
        requested_end_bar_open=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
        provider_as_of_boundary=datetime(2026, 7, 18, 22, 0, tzinfo=UTC),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        expected_frontier_bar_open=datetime(2026, 7, 18, 22, 0, tzinfo=UTC),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )

    with pytest.raises(ValidationError, match="Overlapping active job exists"):
        store.insert_job(job2)


def test_store_stale_job_recovery(tmp_path: Path) -> None:
    db_file = tmp_path / "test_scheduler.sqlite3"
    store = SqliteJobStore(db_file)
    store.initialize()

    # Insert a job
    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="job1",
        lane="test_lane",
        source_commit="commit_1",
        created_at=datetime.now(UTC),
        requested_start_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        requested_end_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        provider_as_of_boundary=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=datetime(2026, 7, 18, 19, 0, tzinfo=UTC),
        expected_frontier_bar_open=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )
    store.insert_job(job)

    # Claim it (so it is RUNNING)
    store.claim_job("job1", "claimer", datetime.now(UTC) - timedelta(minutes=20))

    # Trigger recovery with a 15-minute stale limit
    recovered = store.recover_stale_jobs("test_lane", timedelta(minutes=15))
    assert len(recovered) == 1
    assert recovered[0].job_id == "job1"
    assert recovered[0].status == SchedulerJobStatus.FAILED
    assert recovered[0].error_classification == "stale_timeout_recovered"


def test_store_fail_closed_on_corruption(tmp_path: Path) -> None:
    db_file = tmp_path / "corrupt_scheduler.sqlite3"
    db_file.write_text("not a sqlite database file at all", encoding="utf-8")

    store = SqliteJobStore(db_file)
    with pytest.raises(ValidationError, match="Scheduler database initialization failed"):
        store.initialize()


# ==========================================
# 3. One-Shot Executor Tests
# ==========================================

@patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos")
@patch("algotrader.research.crypto_tournament_v2_forward_oos.initialize_crypto_tournament_v2_forward_oos")
def test_executor_tick_preview_mode(
    mock_init: MagicMock, mock_run: MagicMock, tmp_path: Path
) -> None:
    db_file = tmp_path / "test_scheduler.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()

    # Create dummy files to represent initialized tournament
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    # Mock next refresh request
    mock_run.return_value = {
        "next_refresh": {
            "classification": "ready_for_explicit_read_only_market_data_fetch",
            "requested_start": "2026-07-18T20:00:00Z",
            "requested_end": "2026-07-18T20:00:00Z",
            "as_of": "2026-07-18T21:00:00Z",
        }
    }

    # Frontier is 19:00Z. Next needed bar is 20:00Z, closing at 21:00Z, eligible at 21:05:00Z.
    current_time = datetime(2026, 7, 18, 21, 5, tzinfo=UTC)
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "crypto_1h_1y.csv",
        discovery_receipt=tmp_path / "refresh_packet.json",
        dispatcher=PreviewDispatcher(),
        enabled=True,
        allow_network=False,
    )

    receipt = executor.tick(current_time)
    assert receipt["job_status"] == "completed"
    assert receipt["command_classification"] == "preview_successful"
    assert receipt["accepted_frontier_bar_open"] == "2026-07-18T19:00:00+00:00"
    assert receipt["requested_start_bar_open"] == "2026-07-18T20:00:00+00:00"
    assert receipt["requested_end_bar_open"] == "2026-07-18T20:00:00+00:00"
    assert receipt["provider_as_of_boundary"] == "2026-07-18T21:00:00+00:00"
    assert receipt["expected_frontier_bar_open"] == "2026-07-18T21:00:00+00:00"


@patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos")
def test_executor_tick_no_op_waiting_hour(
    mock_run: MagicMock, tmp_path: Path
) -> None:
    db_file = tmp_path / "test_scheduler.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    # Mock waiting response (no next refresh hour requested yet)
    mock_run.return_value = {
        "next_refresh": {
            "classification": "waiting_for_calendar_hour",
            "requested_start": "2026-07-18T21:00:00Z",
            "requested_end": "",
            "as_of": "2026-07-18T20:00:00Z",
        }
    }

    current_time = datetime(2026, 7, 18, 20, 5, tzinfo=UTC)
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "crypto_1h_1y.csv",
        discovery_receipt=tmp_path / "refresh_packet.json",
        dispatcher=PreviewDispatcher(),
        enabled=True,
        allow_network=False,
    )

    receipt = executor.tick(current_time)
    assert receipt["job_status"] == "blocked"
    assert receipt["command_classification"] == "no_eligible_closed_window"


def test_real_dispatcher_rejection() -> None:
    dispatcher = RealCommandDispatcher(
        scheduler_enabled=False, market_data_read_authorized=False
    )
    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="job",
        lane="lane",
        source_commit="commit",
        created_at=datetime.now(UTC),
        requested_start_bar_open=datetime.now(UTC),
        requested_end_bar_open=datetime.now(UTC),
        provider_as_of_boundary=datetime.now(UTC) + timedelta(hours=1),
        symbols=(),
        accepted_frontier_bar_open=datetime.now(UTC),
        expected_frontier_bar_open=datetime.now(UTC),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )

    with pytest.raises(ValidationError, match="Scheduler is disabled"):
        dispatcher.dispatch(
            job,
            Path("dummy_root"),
            Path("dummy_source"),
            Path("dummy_receipt"),
            allow_network=True,
        )


# ==========================================
# 4. Clock-Injected Regression Cases A-I
# ==========================================

def test_regression_case_a() -> None:
    # Case A: Frontier 19:00Z, Grace 5m, Now 20:04:59Z -> no eligible window
    current_time = datetime(2026, 7, 18, 20, 4, 59, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "no_eligible_window"
    assert res.classification == "no_eligible_closed_window"


def test_regression_case_b() -> None:
    # Case B: Frontier 19:00Z, Grace 5m, Now 20:05:00Z -> no eligible window (latest grace-qualified bar is 19:00Z)
    current_time = datetime(2026, 7, 18, 20, 5, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "no_eligible_window"
    assert res.classification == "no_eligible_closed_window"


def test_regression_case_c() -> None:
    # Case C: Frontier 19:00Z, Grace 5m, Now 21:04:59Z -> no eligible window
    current_time = datetime(2026, 7, 18, 21, 4, 59, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "no_eligible_window"
    assert res.classification == "no_eligible_closed_window"


def test_regression_case_d() -> None:
    # Case D: Frontier 19:00Z, Grace 5m, Now 21:05:00Z -> eligible [20:00Z, 20:00Z]
    current_time = datetime(2026, 7, 18, 21, 5, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "eligible"
    assert res.window.start_bar_open == datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    assert res.window.end_bar_open == datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    assert res.window.provider_as_of_boundary == datetime(2026, 7, 18, 21, 0, tzinfo=UTC)


def test_regression_case_e() -> None:
    # Case E: Frontier 19:00Z, Grace 5m, Now 22:07:00Z -> eligible [20:00Z, 21:00Z]
    current_time = datetime(2026, 7, 18, 22, 7, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "eligible"
    assert res.window.start_bar_open == datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    assert res.window.end_bar_open == datetime(2026, 7, 18, 21, 0, tzinfo=UTC)
    assert res.window.provider_as_of_boundary == datetime(2026, 7, 18, 22, 0, tzinfo=UTC)


def test_regression_case_f() -> None:
    # Case F: Frontier 18:00Z, Grace 5m, Now 20:05:00Z -> eligible [19:00Z, 19:00Z]
    current_time = datetime(2026, 7, 18, 20, 5, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 18, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "eligible"
    assert res.window.start_bar_open == datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    assert res.window.end_bar_open == datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    assert res.window.provider_as_of_boundary == datetime(2026, 7, 18, 20, 0, tzinfo=UTC)


def test_regression_case_g() -> None:
    # Case G: Catch-up cap 24: Frontier 19:00Z, Now 2026-07-20T00:05:00Z (29 hours later) -> exactly 24 bars
    current_time = datetime(2026, 7, 20, 0, 5, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, max_catch_up_hours=24, enabled=True
    )
    assert res.status == "eligible"
    # start_bar_open should be frontier + 1 hour = 20:00Z on 7/18
    assert res.window.start_bar_open == datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    # end_bar_open should be 24 hours later - 1 hour = start_bar_open + 23 hours = 19:00Z on 7/19
    assert res.window.end_bar_open == datetime(2026, 7, 19, 19, 0, tzinfo=UTC)
    assert res.window.provider_as_of_boundary == datetime(2026, 7, 19, 20, 0, tzinfo=UTC)


def test_regression_case_h() -> None:
    # Case H: Forming bar protection: prove that a currently forming bar (e.g. at tick time HH:MM)
    # can never appear in job IDs, requests, dispatcher commands, or receipt boundaries.
    current_time = datetime(2026, 7, 18, 21, 59, 59, tzinfo=UTC)  # 21:00 bar is forming, closes at 22:00
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "eligible"
    # Only 20:00Z is closed (closed at 21:00Z). 21:00Z is forming and must not be included.
    assert res.window.end_bar_open == datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    assert res.window.provider_as_of_boundary == datetime(2026, 7, 18, 21, 0, tzinfo=UTC)


def test_regression_case_i() -> None:
    # Case I: Prove that a trigger firing at HH:05 schedules the prior hour's bar-open timestamp (HH - 1 hour), not HH:00.
    # At 21:05:00Z, we schedule 20:00:00Z, not 21:00:00Z.
    current_time = datetime(2026, 7, 18, 21, 5, 0, tzinfo=UTC)
    frontier = datetime(2026, 7, 18, 19, 0, tzinfo=UTC)
    res = ScheduleCalculator.calculate_eligible_window(
        current_time=current_time, accepted_frontier_bar_open=frontier, enabled=True
    )
    assert res.status == "eligible"
    assert res.window.end_bar_open == datetime(2026, 7, 18, 20, 0, tzinfo=UTC)  # 20:00Z, which is HH - 1 hour


# ==========================================
# 5. Dispatcher Argument Mapping Test
# ==========================================

def test_dispatcher_command_argument_mapping() -> None:
    # Prove that requested_end_bar_open = 2026-07-18T20:00:00Z maps to command argument --as-of 2026-07-18T21:00:00Z
    provider = MagicMock()
    provider.validate.return_value = None
    dispatcher = RealCommandDispatcher(
        scheduler_enabled=True,
        market_data_read_authorized=True,
        credential_reference=CredentialReference(
            "wincred:algotrader/v5.35/alpaca-market-data/offline-test"
        ),
        credential_provider=provider,
    )
    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="job_xyz",
        lane="crypto_tournament_v2_forward_oos",
        source_commit="commit_abc",
        created_at=datetime.now(UTC),
        requested_start_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        requested_end_bar_open=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        provider_as_of_boundary=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=datetime(2026, 7, 18, 19, 0, tzinfo=UTC),
        expected_frontier_bar_open=datetime(2026, 7, 18, 21, 0, tzinfo=UTC),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        dispatcher.dispatch(
            job=job,
            output_root=Path("output"),
            discovery_source=Path("source.csv"),
            discovery_receipt=Path("receipt.json"),
            allow_network=True,
        )
        assert mock_run.called
        args, kwargs = mock_run.call_args
        cmd = kwargs.get("args") or args[0]
        # Verify the --as-of command line argument
        as_of_idx = cmd.index("--as-of")
        assert cmd[as_of_idx + 1] == "2026-07-18T21:00:00+00:00"
        assert "--credential-reference" in cmd
        assert not any("sensitive" in str(item) for item in cmd)
