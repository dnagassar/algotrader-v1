from __future__ import annotations

import json
import os
import sqlite3
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from algotrader.errors import ValidationError
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    SCHEDULER_SCHEMA_VERSION,
    SchedulerJob,
    SchedulerJobStatus,
    SqliteJobStore,
    OneShotExecutor,
    PreviewDispatcher,
    RealCommandDispatcher,
    _file_sha256,
)


# ==========================================
# 1. SQLite V1-to-V2 Migration Tests
# ==========================================

def test_migration_v1_to_v2_preserves_rows(tmp_path: Path) -> None:
    db_file = tmp_path / "test_migration.sqlite3"
    
    # 1. Create a raw v1 database manually
    connection = sqlite3.connect(db_file)
    connection.execute(
        """
        CREATE TABLE scheduler_jobs (
            job_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            lane TEXT NOT NULL,
            source_commit TEXT NOT NULL,
            created_at TEXT NOT NULL,
            requested_start TEXT NOT NULL,
            requested_end TEXT NOT NULL,
            symbols TEXT NOT NULL,
            current_frontier TEXT NOT NULL,
            expected_next_frontier TEXT NOT NULL,
            status TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            claim_identity TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            result_classification TEXT NOT NULL,
            error_classification TEXT NOT NULL,
            receipt_paths TEXT NOT NULL,
            receipt_hashes TEXT NOT NULL,
            source_state_fingerprint_before TEXT NOT NULL,
            source_state_fingerprint_after TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE TABLE scheduler_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO scheduler_metadata (key, value) VALUES ('schema_version', 'v5_31a_scheduler_schema_v1')"
    )

    # Insert one pending, one running, one completed job in v1 format
    t_now = datetime.now(UTC).isoformat()
    t_start = "2026-07-18T20:00:00+00:00"
    t_end = "2026-07-18T22:00:00+00:00"
    t_front = "2026-07-18T19:00:00+00:00"

    connection.execute(
        """
        INSERT INTO scheduler_jobs VALUES (
            'job_pending', 'v5_31a_scheduler_schema_v1', 'lane_1', 'commit_1', ?,
            ?, ?, '["BTCUSD"]', ?, ?, 'pending', 0, '', '', '', '', '', '[]', '[]', 'state_b', 'state_a', ?
        )
        """, (t_now, t_start, t_end, t_front, t_end, t_now)
    )
    connection.execute(
        """
        INSERT INTO scheduler_jobs VALUES (
            'job_running', 'v5_31a_scheduler_schema_v1', 'lane_1', 'commit_1', ?,
            ?, ?, '["BTCUSD"]', ?, ?, 'running', 1, 'claim_abc', ?, '', '', '', '[]', '[]', 'state_b', '', ?
        )
        """, (t_now, t_start, t_end, t_front, t_end, t_now, t_now)
    )
    connection.execute(
        """
        INSERT INTO scheduler_jobs VALUES (
            'job_completed', 'v5_31a_scheduler_schema_v1', 'lane_1', 'commit_1', ?,
            ?, ?, '["BTCUSD"]', ?, ?, 'completed', 1, 'claim_xyz', ?, ?, 'preview_successful', '', '[]', '[]', 'state_b', 'state_a', ?
        )
        """, (t_now, t_start, t_end, t_front, t_end, t_now, t_now, t_now)
    )
    connection.commit()
    connection.close()

    # 2. Initialize the store using SqliteJobStore, triggering migration
    store = SqliteJobStore(db_file)
    store.initialize()

    # 3. Verify all jobs survive and column mapping is correct
    p_job = store.get_job("job_pending")
    assert p_job is not None
    assert p_job.status == SchedulerJobStatus.PENDING
    assert p_job.requested_start_bar_open.isoformat() == t_start
    assert p_job.requested_end_bar_open.isoformat() == t_end
    # Reconstructed provider_as_of_boundary = requested_end_bar_open + 1 hour
    assert p_job.provider_as_of_boundary.isoformat() == "2026-07-18T23:00:00+00:00"
    assert p_job.accepted_frontier_bar_open.isoformat() == t_front
    assert p_job.expected_frontier_bar_open.isoformat() == t_end

    r_job = store.get_job("job_running")
    assert r_job is not None
    assert r_job.status == SchedulerJobStatus.RUNNING
    assert r_job.claim_identity == "claim_abc"

    c_job = store.get_job("job_completed")
    assert c_job is not None
    assert c_job.status == SchedulerJobStatus.COMPLETED
    assert c_job.result_classification == "preview_successful"

    # Verify idempotency
    store.initialize()
    assert store.get_job("job_pending").status == SchedulerJobStatus.PENDING


def test_migration_fail_closed_on_unknown_schema(tmp_path: Path) -> None:
    db_file = tmp_path / "test_unknown.sqlite3"
    
    connection = sqlite3.connect(db_file)
    connection.execute(
        "CREATE TABLE scheduler_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO scheduler_metadata (key, value) VALUES ('schema_version', 'v5_31a_future_schema_v99')"
    )
    connection.commit()
    connection.close()

    store = SqliteJobStore(db_file)
    with pytest.raises(ValidationError, match="Unsupported scheduler schema version"):
        store.initialize()


def test_migration_failure_leaves_v1_intact(tmp_path: Path) -> None:
    db_file = tmp_path / "test_failure.sqlite3"
    
    connection = sqlite3.connect(db_file)
    connection.execute(
        "CREATE TABLE scheduler_jobs (job_id TEXT PRIMARY KEY, status TEXT)"
    )
    connection.execute(
        "CREATE TABLE scheduler_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO scheduler_metadata (key, value) VALUES ('schema_version', 'v5_31a_scheduler_schema_v1')"
    )
    connection.commit()
    connection.close()

    # The table scheduler_jobs lacks most required columns, causing migration to fail.
    store = SqliteJobStore(db_file)
    with pytest.raises(ValidationError, match="Database schema does not match expected v1 schema columns"):
        store.initialize()

    # Verify that the schema metadata version remains v1 after failed transaction
    connection = sqlite3.connect(db_file)
    ver = connection.execute(
        "SELECT value FROM scheduler_metadata WHERE key = 'schema_version'"
    ).fetchone()[0]
    connection.close()
    assert ver == "v5_31a_scheduler_schema_v1"


# ==========================================
# 2. Terminal-Update Fencing Tests
# ==========================================

def test_terminal_update_fencing(tmp_path: Path) -> None:
    db_file = tmp_path / "test_fencing.sqlite3"
    store = SqliteJobStore(db_file)
    store.initialize()

    job_id = "fencing_job"
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

    # Claim the job (attempt_number becomes 1, status RUNNING, claim_identity = "claimer_1")
    claimed = store.claim_job(job_id, "claimer_1", datetime.now(UTC))
    assert claimed is True

    # Try to write terminal update with wrong claim token
    wrong_job = SchedulerJob(
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
        status=SchedulerJobStatus.COMPLETED,
        attempt_number=1,
        claim_identity="wrong_claimer",
    )
    with pytest.raises(ValidationError, match="Fencing conflict"):
        store.update_job(wrong_job)

    # Try to write terminal update with correct claim token but wrong status
    wrong_job_2 = SchedulerJob(
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
        status=SchedulerJobStatus.COMPLETED,
        attempt_number=1,
        claim_identity="claimer_1",
    )
    # This should succeed since current status in DB is RUNNING, and claim is claimer_1
    store.update_job(wrong_job_2)

    # Verify job is now COMPLETED
    updated_job = store.get_job(job_id)
    assert updated_job.status == SchedulerJobStatus.COMPLETED

    # Try to rewrite job status now that it is completed (should fail fencing because DB status is not 'running')
    with pytest.raises(ValidationError, match="Fencing conflict"):
        store.update_job(wrong_job_2)


# ==========================================
# 3. Failed-Window Recovery Tests
# ==========================================

def test_failed_window_recovery(tmp_path: Path) -> None:
    db_file = tmp_path / "test_recovery.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=PreviewDispatcher(),
        enabled=True,
        allow_network=False,
    )
    executor.store.initialize()

    # Create a failed job in the database
    start = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    end = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="failed_job_1",
        lane="crypto_tournament_v2_forward_oos",
        source_commit="commit_1",
        created_at=datetime.now(UTC),
        requested_start_bar_open=start,
        requested_end_bar_open=end,
        provider_as_of_boundary=end + timedelta(hours=1),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=start - timedelta(hours=1),
        expected_frontier_bar_open=end + timedelta(hours=1),
        status=SchedulerJobStatus.FAILED,
        attempt_number=1,
        claim_identity="claimer",
    )
    executor.store.insert_job(job)

    # Resetting without authorization raises
    with pytest.raises(ValidationError, match="Reset failed rejected"):
        executor.reset_failed("failed_job_1", authorized=False)

    # Resetting completed job raises
    job_comp = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="completed_job",
        lane="crypto_tournament_v2_forward_oos",
        source_commit="commit_1",
        created_at=datetime.now(UTC),
        requested_start_bar_open=start,
        requested_end_bar_open=end,
        provider_as_of_boundary=end + timedelta(hours=1),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=start - timedelta(hours=1),
        expected_frontier_bar_open=end + timedelta(hours=1),
        status=SchedulerJobStatus.COMPLETED,
        attempt_number=1,
        claim_identity="claimer",
    )
    executor.store.insert_job(job_comp)
    with pytest.raises(ValidationError, match="is not in FAILED state"):
        executor.reset_failed("completed_job", authorized=True)

    # Perform successful reset
    receipt = executor.reset_failed("failed_job_1", authorized=True)
    assert receipt["job_status"] == "pending"
    assert receipt["invoked_mode"] == "reset_failed"

    # Verify DB state of updated job
    updated_job = executor.store.get_job("failed_job_1")
    assert updated_job.status == SchedulerJobStatus.PENDING
    assert updated_job.attempt_number == 1
    assert updated_job.claim_identity == ""
    assert updated_job.started_at is None
    assert updated_job.completed_at is None


# ==========================================
# 4. Native Receipt Binding Tests
# ==========================================

def test_native_receipt_binding(tmp_path: Path) -> None:
    db_file = tmp_path / "test_binding.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    # Mock dispatcher that returns expected receipts manifest
    dispatcher = MagicMock()
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=dispatcher,
        enabled=True,
        allow_network=False,
    )
    executor.store.initialize()

    def clear_db() -> None:
        with executor.store._connect() as conn:
            conn.execute("DELETE FROM scheduler_jobs")
            conn.commit()

    # Prepopulate the OOS status mocked return in run_crypto_tournament_v2_forward_oos
    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": "2026-07-18T20:00:00Z",
                "requested_end": "2026-07-18T20:00:00Z",
                "as_of": "2026-07-18T21:00:00Z",
            }
        }

        # 1. Valid Receipt Manifest
        p_path = output_root / "operating_packet.json"
        s_path = output_root / "frozen_state.json"
        
        p_content = {"as_of": "2026-07-18T21:00:00Z"}
        s_content = {"updated_at": "2026-07-18T21:00:00Z"}
        p_path.write_text(json.dumps(p_content), encoding="utf-8")
        s_path.write_text(json.dumps(s_content), encoding="utf-8")

        p_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()
        s_hash = hashlib.sha256(s_path.read_bytes()).hexdigest()

        dispatcher.dispatch.return_value = {
            "status": "success",
            "classification": "subprocess_completed",
            "expected_receipts": [
                {
                    "path": str(p_path),
                    "sha256": p_hash,
                    "type": "operating_packet",
                    "window_identity": "2026-07-18T20:00:00+00:00_2026-07-18T20:00:00+00:00",
                },
                {
                    "path": str(s_path),
                    "sha256": s_hash,
                    "type": "frozen_state",
                    "window_identity": "2026-07-18T20:00:00+00:00_2026-07-18T20:00:00+00:00",
                }
            ]
        }

        # Tick should succeed and job should be completed
        current_time = datetime(2026, 7, 18, 21, 5, tzinfo=UTC)
        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "completed"

        # 2. Missing Receipt File
        clear_db()
        # Mutate manifest path to point to a nonexistent file
        nonexistent_path = output_root / "nonexistent.json"
        dispatcher.dispatch.return_value["expected_receipts"][1]["path"] = str(nonexistent_path)

        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "failed"
        assert receipt["command_classification"] == "missing_receipt_file"

        # 3. Wrong Hash
        clear_db()
        # Restore valid path
        dispatcher.dispatch.return_value["expected_receipts"][1]["path"] = str(s_path)
        # Mismatch hash in dispatcher return
        dispatcher.dispatch.return_value["expected_receipts"][1]["sha256"] = "wrong_hash"
        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "failed"
        assert receipt["command_classification"] == "receipt_hash_mismatch"

        # 4. Stale Receipt / Timestamp mismatch
        clear_db()
        dispatcher.dispatch.return_value["expected_receipts"][1]["sha256"] = s_hash
        # Write stale timestamp to operating_packet
        p_path.write_text(json.dumps({"as_of": "2026-07-18T19:00:00Z"}), encoding="utf-8")
        p_hash_new = hashlib.sha256(p_path.read_bytes()).hexdigest()
        dispatcher.dispatch.return_value["expected_receipts"][0]["sha256"] = p_hash_new

        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "failed"
        assert receipt["command_classification"] == "receipt_binding_mismatch"


# ==========================================
# 5. Atomic Scheduler Receipts Tests
# ==========================================

def test_atomic_scheduler_receipts(tmp_path: Path) -> None:
    db_file = tmp_path / "test_atomic.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()
    
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=PreviewDispatcher(),
        enabled=True,
        allow_network=False,
    )
    executor.store.initialize()

    # Trigger no-op receipt to verify nulls instead of empty strings
    receipt = executor._write_noop_receipt(
        job_id="test_no_op",
        status=SchedulerJobStatus.BLOCKED,
        mode="preview",
        frontier=datetime(2026, 7, 18, 20, 0, tzinfo=UTC),
        start=None,
        end=None,
        provider_as_of=None,
        expected_frontier=None,
        classification="blocked_test",
        reason="Testing",
        duration=0.0,
    )

    assert receipt["requested_start_bar_open"] is None
    assert receipt["requested_end_bar_open"] is None
    assert receipt["provider_as_of_boundary"] is None
    assert receipt["expected_frontier_bar_open"] is None

    # Verify receipt file exists and is well-formed
    receipt_dir = output_root / "scheduler_receipts"
    files = list(receipt_dir.glob("*.json"))
    assert len(files) == 1
    content = json.loads(files[0].read_text(encoding="utf-8"))
    assert content["job_id"] == "test_no_op"
    assert content["requested_start_bar_open"] is None


# ==========================================
# 6. Child-Process Environment Isolation Tests
# ==========================================

def test_environment_isolation_and_live_rejection() -> None:
    # 1. Test live endpoint rejection
    dispatcher = RealCommandDispatcher(
        scheduler_enabled=True, market_data_read_authorized=True
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

    # Inhibit live endpoint
    with patch.dict(os.environ, {"ALPACA_BASE_URL": "https://api.alpaca.markets"}):
        with pytest.raises(ValidationError, match="Live Alpaca endpoint found"):
            dispatcher.dispatch(job, Path("root"), Path("source"), Path("receipt"), allow_network=True)

    # Inhibit live APP_PROFILE
    with patch.dict(os.environ, {"APP_PROFILE": "live"}):
        with pytest.raises(ValidationError, match="APP_PROFILE cannot be 'live'"):
            dispatcher.dispatch(job, Path("root"), Path("source"), Path("receipt"), allow_network=True)

    # 2. Test minimal allowlisted env filtering
    with patch.dict(os.environ, {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "sensitive_key",
        "TIINGO_API_KEY": "sensitive_tiingo",
        "SYSTEMROOT": "C:\\Windows",
        "MY_UNRELATED_VAR": "should_be_scrubbed",
    }, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Create files so dispatch doesn't fail on missing manifest checks
            # (though mock_run is mocked, so let's mock the file exists check or create files)
            with patch.object(Path, "is_file", return_value=True), patch("algotrader.orchestration.crypto_tournament_v2_oos_scheduler._file_sha256", return_value="hash"):
                dispatcher.dispatch(job, Path("root"), Path("source"), Path("receipt"), allow_network=True)
            
            assert mock_run.called
            run_kwargs = mock_run.call_args[1]
            child_env = run_kwargs["env"]

            # SystemRoot must be preserved
            assert "SYSTEMROOT" in child_env or "SystemRoot" in child_env
            # Sensitive keys must be scrubbed
            assert "ALPACA_API_KEY" not in child_env
            assert "TIINGO_API_KEY" not in child_env
            assert "APP_PROFILE" not in child_env
            # Unrelated keys must be scrubbed
            assert "MY_UNRELATED_VAR" not in child_env


# ==========================================
# 7. Additional Bounded Repair Tests
# ==========================================

def test_failed_to_reset_to_completed_e2e(tmp_path: Path) -> None:
    db_file = tmp_path / "test_e2e.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    dispatcher = MagicMock()
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=dispatcher,
        enabled=True,
        allow_network=False,
    )
    executor.store.initialize()

    # Mock next_refresh return
    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": "2026-07-18T20:00:00Z",
                "requested_end": "2026-07-18T20:00:00Z",
                "as_of": "2026-07-18T21:00:00Z",
            }
        }

        # First run: dispatcher fails, resulting in a FAILED job.
        dispatcher.dispatch.return_value = {
            "status": "failed",
            "classification": "subprocess_error",
            "reason": "Simulated failure",
        }

        current_time = datetime(2026, 7, 18, 21, 5, tzinfo=UTC)
        receipt1 = executor.tick(current_time)
        assert receipt1["job_status"] == "failed"

        # Verify the job exists in the DB with attempt_number = 1
        jobs = executor.store.list_jobs()
        assert len(jobs) == 1
        job_id = jobs[0].job_id
        assert jobs[0].status == SchedulerJobStatus.FAILED
        assert jobs[0].attempt_number == 1

        # Reset failed job (operator-authorized)
        reset_receipt = executor.reset_failed(job_id, authorized=True)
        assert reset_receipt["job_status"] == "pending"
        # Verify attempt_number did not double increment during reset (stays at 1)
        job_after_reset = executor.store.get_job(job_id)
        assert job_after_reset.status == SchedulerJobStatus.PENDING
        assert job_after_reset.attempt_number == 1

        # Second run: dispatcher succeeds, we write valid expected receipts
        p_path = output_root / "operating_packet.json"
        s_path = output_root / "frozen_state.json"
        p_content = {"as_of": "2026-07-18T21:00:00Z"}
        s_content = {"updated_at": "2026-07-18T21:00:00Z"}
        p_path.write_text(json.dumps(p_content), encoding="utf-8")
        s_path.write_text(json.dumps(s_content), encoding="utf-8")
        p_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()
        s_hash = hashlib.sha256(s_path.read_bytes()).hexdigest()

        dispatcher.dispatch.return_value = {
            "status": "success",
            "classification": "subprocess_completed",
            "expected_receipts": [
                {
                    "path": str(p_path),
                    "sha256": p_hash,
                    "type": "operating_packet",
                    "window_identity": "2026-07-18T20:00:00+00:00_2026-07-18T20:00:00+00:00",
                },
                {
                    "path": str(s_path),
                    "sha256": s_hash,
                    "type": "frozen_state",
                    "window_identity": "2026-07-18T20:00:00+00:00_2026-07-18T20:00:00+00:00",
                }
            ]
        }

        # Tick again: must NOT trip overlap guard (not blocked_concurrent_overlap) and succeed
        receipt2 = executor.tick(current_time)
        assert receipt2["job_status"] == "completed"
        assert receipt2["command_classification"] == "subprocess_completed"

        # Verify the completed job in DB has attempt_number = 2 (incremented during the second claim)
        final_job = executor.store.get_job(job_id)
        assert final_job.status == SchedulerJobStatus.COMPLETED
        assert final_job.attempt_number == 2


def test_window_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    db_file = tmp_path / "test_window_mismatch.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    dispatcher = MagicMock()
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=dispatcher,
        enabled=True,
        allow_network=False,
    )
    executor.store.initialize()

    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": "2026-07-18T20:00:00Z",
                "requested_end": "2026-07-18T20:00:00Z",
                "as_of": "2026-07-18T21:00:00Z",
            }
        }

        p_path = output_root / "operating_packet.json"
        p_content = {"as_of": "2026-07-18T21:00:00Z"}
        p_path.write_text(json.dumps(p_content), encoding="utf-8")
        p_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()

        dispatcher.dispatch.return_value = {
            "status": "success",
            "classification": "subprocess_completed",
            "expected_receipts": [
                {
                    "path": str(p_path),
                    "sha256": p_hash,
                    "type": "operating_packet",
                    "window_identity": "wrong_window_identity_here",
                }
            ]
        }

        current_time = datetime(2026, 7, 18, 21, 5, tzinfo=UTC)
        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "failed"
        assert receipt["command_classification"] == "receipt_window_mismatch"

        # Verify job in DB is FAILED and not completed
        jobs = executor.store.list_jobs()
        assert jobs[0].status == SchedulerJobStatus.FAILED


def test_absent_expected_receipts_manifest_fails_closed(tmp_path: Path) -> None:
    db_file = tmp_path / "test_absent_manifest.sqlite3"
    output_root = tmp_path / "oos_latest"
    output_root.mkdir()
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    dispatcher = MagicMock()
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=dispatcher,
        enabled=True,
        allow_network=False,
    )
    executor.store.initialize()

    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": "2026-07-18T20:00:00Z",
                "requested_end": "2026-07-18T20:00:00Z",
                "as_of": "2026-07-18T21:00:00Z",
            }
        }

        dispatcher.dispatch.return_value = {
            "status": "success",
            "classification": "subprocess_completed",
            "expected_receipts": None,  # absent/None manifest
        }

        current_time = datetime(2026, 7, 18, 21, 5, tzinfo=UTC)
        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "failed"
        assert receipt["command_classification"] == "missing_receipt_manifest"

        # Verify job in DB is FAILED and not completed
        jobs = executor.store.list_jobs()
        assert jobs[0].status == SchedulerJobStatus.FAILED
