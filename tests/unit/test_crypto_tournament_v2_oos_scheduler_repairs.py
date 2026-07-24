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
from algotrader.execution.secure_credential_provider import CredentialReference
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

    # 2. Credential aliases are rejected before child creation.
    with patch.dict(os.environ, {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "sensitive_key",
        "TIINGO_API_KEY": "sensitive_tiingo",
        "SYSTEMROOT": "C:\\Windows",
        "MY_UNRELATED_VAR": "should_be_scrubbed",
    }, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with pytest.raises(
                ValidationError,
                match="credential environment aliases are forbidden",
            ):
                dispatcher.dispatch(job, Path("root"), Path("source"), Path("receipt"), allow_network=True)
            assert not mock_run.called

    # 3. A clean process receives only the minimal public environment.
    provider = MagicMock()
    provider.validate.return_value = None
    secure_dispatcher = RealCommandDispatcher(
        scheduler_enabled=True,
        market_data_read_authorized=True,
        credential_reference=CredentialReference(
            "wincred:algotrader/v5.35/alpaca-market-data/offline-test"
        ),
        credential_provider=provider,
    )
    with patch.dict(os.environ, {
        "SYSTEMROOT": "C:\\Windows",
        "MY_UNRELATED_VAR": "should_be_scrubbed",
    }, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{}")
            with patch.object(Path, "is_file", return_value=True), patch(
                "algotrader.orchestration.crypto_tournament_v2_oos_scheduler._file_sha256",
                return_value="hash",
            ):
                secure_dispatcher.dispatch(
                    job,
                    Path("root"),
                    Path("source"),
                    Path("receipt"),
                    allow_network=True,
                )

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


# ==========================================
# ROUND 3 — TEST A: Delayed FAILED Classification
# ==========================================

def _make_executor_with_mock(tmp_path: Path, test_name: str) -> tuple:
    """Helper: create executor + mock dispatcher + frozen state."""
    db_file = tmp_path / f"{test_name}.sqlite3"
    output_root = tmp_path / test_name
    output_root.mkdir(parents=True, exist_ok=True)
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
    return executor, dispatcher, output_root


def test_delayed_failed_classification(tmp_path: Path) -> None:
    """A. Fail a job at time T, advance 6h, tick without reset → no_automatic_retry."""
    executor, dispatcher, output_root = _make_executor_with_mock(tmp_path, "delayed_failed")

    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": "2026-07-18T11:00:00Z",
                "requested_end": "2026-07-18T11:00:00Z",
                "as_of": "2026-07-18T12:00:00Z",
            }
        }

        dispatcher.dispatch.return_value = {
            "status": "failed",
            "classification": "subprocess_error",
            "reason": "Simulated failure at T",
        }

        t0 = datetime(2026, 7, 18, 12, 5, tzinfo=UTC)
        r0 = executor.tick(t0)
        assert r0["job_status"] == "failed"

        jobs = executor.store.list_jobs()
        assert len(jobs) == 1
        failed_job_id = jobs[0].job_id
        failed_start = jobs[0].requested_start_bar_open
        failed_end = jobs[0].requested_end_bar_open
        failed_attempt = jobs[0].attempt_number

        # Advance 6+ closed hours without reset
        t1 = datetime(2026, 7, 18, 18, 15, tzinfo=UTC)
        r1 = executor.tick(t1)
        assert r1["command_classification"] == "no_automatic_retry"
        assert r1["job_status"] == "failed"

        # DB unchanged
        jobs_after = executor.store.list_jobs()
        assert len(jobs_after) == 1
        assert jobs_after[0].job_id == failed_job_id
        assert jobs_after[0].requested_start_bar_open == failed_start
        assert jobs_after[0].requested_end_bar_open == failed_end
        assert jobs_after[0].attempt_number == failed_attempt
        assert jobs_after[0].status == SchedulerJobStatus.FAILED
        assert dispatcher.dispatch.call_count == 1


# ==========================================
# ROUND 3 — TEST B: Delayed Reset and Recovery (Parameterized)
# ==========================================

@pytest.mark.parametrize("advance_hours", [0, 1, 6, 30])
def test_delayed_reset_and_recovery(tmp_path: Path, advance_hours: int) -> None:
    """B. Fail, reset, advance clock far, tick → adopts stored PENDING job verbatim."""
    test_name = f"delayed_recovery_{advance_hours}h"
    executor, dispatcher, output_root = _make_executor_with_mock(tmp_path, test_name)

    # requested_start/end come from next_refresh; provider_as_of_boundary comes from
    # ScheduleCalculator which uses current_time floor(hour). t_fail = 12:05 → as_of = 12:00.
    stored_start = datetime(2026, 7, 18, 10, 0, tzinfo=UTC)
    stored_end = datetime(2026, 7, 18, 11, 0, tzinfo=UTC)
    expected_as_of = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)  # provider_as_of_boundary set by ScheduleCalculator

    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": stored_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "requested_end": stored_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "as_of": expected_as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        }

        # STEP 1: fail the job
        dispatcher.dispatch.return_value = {
            "status": "failed",
            "classification": "subprocess_error",
            "reason": "Forced failure",
        }
        t_fail = datetime(2026, 7, 18, 12, 5, tzinfo=UTC)
        r_fail = executor.tick(t_fail)
        assert r_fail["job_status"] == "failed"

        jobs = executor.store.list_jobs()
        assert len(jobs) == 1
        original_job_id = jobs[0].job_id
        stored_provider_as_of = jobs[0].provider_as_of_boundary  # actual stored value
        assert jobs[0].status == SchedulerJobStatus.FAILED
        assert jobs[0].attempt_number == 1

        # STEP 2: authorized reset
        reset_result = executor.reset_failed(original_job_id, authorized=True)
        assert reset_result["job_status"] == "pending"
        assert dispatcher.dispatch.call_count == 1  # reset must NOT dispatch

        jobs_after_reset = executor.store.list_jobs()
        assert len(jobs_after_reset) == 1
        assert jobs_after_reset[0].status == SchedulerJobStatus.PENDING
        assert jobs_after_reset[0].attempt_number == 1

        # STEP 3: advance far (simulate delayed tick)
        t_after_reset = t_fail + timedelta(hours=advance_hours + 6)

        # Prepare valid receipts matching the STORED provider_as_of_boundary
        p_path = output_root / "operating_packet.json"
        s_path = output_root / "frozen_state.json"
        p_content = {"as_of": stored_provider_as_of.isoformat()}
        s_content = {"updated_at": stored_provider_as_of.isoformat()}
        p_path.write_text(json.dumps(p_content), encoding="utf-8")
        s_path.write_text(json.dumps(s_content), encoding="utf-8")
        p_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()
        s_hash = hashlib.sha256(s_path.read_bytes()).hexdigest()
        window_id = f"{stored_start.isoformat()}_{stored_end.isoformat()}"

        dispatcher.dispatch.return_value = {
            "status": "success",
            "classification": "subprocess_completed",
            "expected_receipts": [
                {
                    "path": str(p_path),
                    "sha256": p_hash,
                    "type": "operating_packet",
                    "window_identity": window_id,
                },
                {
                    "path": str(s_path),
                    "sha256": s_hash,
                    "type": "frozen_state",
                    "window_identity": window_id,
                },
            ],
        }

        r_recovery = executor.tick(t_after_reset)
        assert r_recovery["job_status"] == "completed", f"Expected completed, got: {r_recovery}"
        assert r_recovery["command_classification"] == "subprocess_completed"

        # Same job_id, same stored window
        jobs_final = executor.store.list_jobs()
        assert len(jobs_final) == 1
        final_job = jobs_final[0]
        assert final_job.job_id == original_job_id
        assert final_job.requested_start_bar_open == stored_start
        assert final_job.requested_end_bar_open == stored_end
        assert final_job.provider_as_of_boundary == stored_provider_as_of
        assert final_job.status == SchedulerJobStatus.COMPLETED

        # Attempt number bumped to 2 on reclaim
        assert final_job.attempt_number == 2

        # Recovery receipt reports stored window (not widened)
        assert r_recovery["requested_start_bar_open"] == stored_start.isoformat()
        assert r_recovery["requested_end_bar_open"] == stored_end.isoformat()

        # Dispatcher called exactly twice total (fail + recovery)
        assert dispatcher.dispatch.call_count == 2



# ==========================================
# ROUND 3 — TEST C: Multiple Unresolved Rows
# ==========================================

def test_multiple_unresolved_rows_fails_closed(tmp_path: Path) -> None:
    """C. Store with 2 unresolved jobs → blocked_ambiguous_unresolved_jobs."""
    executor, dispatcher, output_root = _make_executor_with_mock(tmp_path, "ambiguous")

    t_base = datetime(2026, 7, 18, 10, 0, tzinfo=UTC)
    lane = "crypto_tournament_v2_forward_oos"

    job_a = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="aaaa1111aaaa1111aaaa1111aaaa1111",
        lane=lane,
        source_commit="abc",
        created_at=t_base,
        requested_start_bar_open=t_base,
        requested_end_bar_open=t_base,
        provider_as_of_boundary=t_base,
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=t_base,
        expected_frontier_bar_open=t_base + timedelta(hours=1),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )
    job_b = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="bbbb2222bbbb2222bbbb2222bbbb2222",
        lane=lane,
        source_commit="abc",
        created_at=t_base + timedelta(hours=1),
        requested_start_bar_open=t_base + timedelta(hours=1),
        requested_end_bar_open=t_base + timedelta(hours=1),
        provider_as_of_boundary=t_base + timedelta(hours=1),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=t_base + timedelta(hours=1),
        expected_frontier_bar_open=t_base + timedelta(hours=2),
        status=SchedulerJobStatus.FAILED,
        attempt_number=1,
        claim_identity="",
    )
    executor.store.insert_job(job_a)
    executor.store.insert_job(job_b)

    current_time = datetime(2026, 7, 18, 18, 0, tzinfo=UTC)
    receipt = executor.tick(current_time)
    assert receipt["command_classification"] == "blocked_ambiguous_unresolved_jobs"
    assert receipt["job_status"] == "blocked"
    assert dispatcher.dispatch.call_count == 0

    jobs = executor.store.list_jobs()
    assert len(jobs) == 2


# ==========================================
# ROUND 3 — TEST D: Unknown Receipt Type
# ==========================================

def test_unrecognized_receipt_type_fails_closed(tmp_path: Path) -> None:
    """D. unknown receipt type must fail closed, never reach COMPLETED."""
    executor, dispatcher, output_root = _make_executor_with_mock(tmp_path, "unknown_type")

    stored_start = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    stored_end = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    stored_as_of = datetime(2026, 7, 18, 21, 0, tzinfo=UTC)

    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": stored_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "requested_end": stored_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "as_of": stored_as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        }

        p_path = output_root / "operating_packet.json"
        p_path.write_text("{}", encoding="utf-8")
        p_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()
        window_id = f"{stored_start.isoformat()}_{stored_end.isoformat()}"

        dispatcher.dispatch.return_value = {
            "status": "success",
            "classification": "subprocess_completed",
            "expected_receipts": [
                {
                    "path": str(p_path),
                    "sha256": p_hash,
                    "type": "wrong_type",  # unrecognized
                    "window_identity": window_id,
                }
            ],
        }

        current_time = datetime(2026, 7, 18, 21, 5, tzinfo=UTC)
        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "failed"
        assert receipt["command_classification"] == "unknown_receipt_type"

        jobs = executor.store.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].status == SchedulerJobStatus.FAILED

        # Subsequent tick → no_automatic_retry (frontier not advanced)
        receipt2 = executor.tick(current_time + timedelta(hours=6))
        assert receipt2["command_classification"] == "no_automatic_retry"


# ==========================================
# ROUND 3 — TEST E: Recognized But Wrong Type
# ==========================================

def test_recognized_but_wrong_type_fails_closed(tmp_path: Path) -> None:
    """E. Manifest says 'operating_packet' but content is frozen_state → receipt_type_mismatch."""
    executor, dispatcher, output_root = _make_executor_with_mock(tmp_path, "wrong_type")

    stored_start = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    stored_end = datetime(2026, 7, 18, 20, 0, tzinfo=UTC)
    stored_as_of = datetime(2026, 7, 18, 21, 0, tzinfo=UTC)

    with patch("algotrader.research.crypto_tournament_v2_forward_oos.run_crypto_tournament_v2_forward_oos") as mock_run:
        mock_run.return_value = {
            "next_refresh": {
                "classification": "ready_for_explicit_read_only_market_data_fetch",
                "requested_start": stored_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "requested_end": stored_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "as_of": stored_as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        }

        # File has frozen_state content but manifest says operating_packet
        p_path = output_root / "packet.json"
        p_content = {"updated_at": stored_as_of.isoformat()}  # frozen_state content
        p_path.write_text(json.dumps(p_content), encoding="utf-8")
        p_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()
        window_id = f"{stored_start.isoformat()}_{stored_end.isoformat()}"

        dispatcher.dispatch.return_value = {
            "status": "success",
            "classification": "subprocess_completed",
            "expected_receipts": [
                {
                    "path": str(p_path),
                    "sha256": p_hash,
                    "type": "operating_packet",  # manifest says this, file is frozen_state
                    "window_identity": window_id,
                }
            ],
        }

        current_time = datetime(2026, 7, 18, 21, 5, tzinfo=UTC)
        receipt = executor.tick(current_time)
        assert receipt["job_status"] == "failed"
        assert receipt["command_classification"] == "receipt_type_mismatch"
        jobs_failed = executor.store.list_jobs()
        assert len(jobs_failed) == 1
        assert jobs_failed[0].status == SchedulerJobStatus.FAILED


# ==========================================
# ROUND 3 — TEST F: Endpoint Adversarial Table
# ==========================================

@pytest.mark.parametrize("url,expected_hostname,should_reject", [
    ("https://api.alpaca.markets/v2", "api.alpaca.markets", True),
    ("https://api.alpaca.markets/v2?note=paper", "api.alpaca.markets", True),
    ("https://api.alpaca.markets/paper", "api.alpaca.markets", True),
    ("https://api.alpaca.markets#paper", "api.alpaca.markets", True),
    ("https://API.ALPACA.MARKETS/v2", "api.alpaca.markets", True),
    ("https://api.alpaca.markets:443/v2", "api.alpaca.markets", True),
    ("https://api.alpaca.markets./v2", "api.alpaca.markets", True),
    ("https://user@api.alpaca.markets/v2", "api.alpaca.markets", True),
    ("https://user:pass@api.alpaca.markets/v2", "api.alpaca.markets", True),
    ("https://paper-api.alpaca.markets@api.alpaca.markets/v2", "api.alpaca.markets", True),
    ("https://paper-api.alpaca.markets", "paper-api.alpaca.markets", False),
    ("https://paper-api.alpaca.markets:443", "paper-api.alpaca.markets", False),
    ("https://paper-api.alpaca.markets.example.invalid", "paper-api.alpaca.markets.example.invalid", False),
    ("http://other.markets", "other.markets", False),
])
def test_endpoint_parser_table(url: str, expected_hostname: str, should_reject: bool) -> None:
    from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import _extract_hostname
    hostname = _extract_hostname(url)
    assert hostname == expected_hostname, (
        f"URL {url!r}: expected hostname {expected_hostname!r}, got {hostname!r}"
    )

    dispatcher = RealCommandDispatcher(scheduler_enabled=True, market_data_read_authorized=True)
    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="dummy_job_id_1234567890123456",
        lane="dummy",
        source_commit="dummy",
        created_at=datetime.now(UTC),
        requested_start_bar_open=datetime(2026, 7, 18, 10, 0, tzinfo=UTC),
        requested_end_bar_open=datetime(2026, 7, 18, 10, 0, tzinfo=UTC),
        provider_as_of_boundary=datetime(2026, 7, 18, 10, 0, tzinfo=UTC),
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=datetime(2026, 7, 18, 10, 0, tzinfo=UTC),
        expected_frontier_bar_open=datetime(2026, 7, 18, 11, 0, tzinfo=UTC),
        status=SchedulerJobStatus.PENDING,
        attempt_number=1,
        claim_identity="dummy",
    )

    with patch.dict(os.environ, {"ALPACA_API_ENDPOINT": url}), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="{}")

        if should_reject:
            with pytest.raises(ValidationError) as exc_info:
                dispatcher.dispatch(
                    job=job,
                    output_root=Path("/tmp"),
                    discovery_source=Path("/tmp"),
                    discovery_receipt=Path("/tmp"),
                    allow_network=True,
                )
            assert "Live Alpaca endpoint found" in str(exc_info.value)
        else:
            try:
                dispatcher.dispatch(
                    job=job,
                    output_root=Path("/tmp"),
                    discovery_source=Path("/tmp"),
                    discovery_receipt=Path("/tmp"),
                    allow_network=True,
                )
            except ValidationError as exc:
                assert "Live Alpaca endpoint found" not in str(exc), (
                    f"URL {url!r} (hostname={hostname!r}) was wrongly rejected: {exc}"
                )


# ==========================================
# ROUND 3 — TEST G: Claim Identity Uniqueness
# ==========================================

def test_claim_identity_uniqueness(tmp_path: Path) -> None:
    """G. Same timestamp+PID → different identities; stale identity cannot complete/fail new."""
    import uuid
    from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
        _generate_job_id,
    )
    from dataclasses import replace as dc_replace

    db_file = tmp_path / "claim_identity.sqlite3"
    store = SqliteJobStore(db_file)
    store.initialize()

    lane = "test_lane"
    t = datetime(2026, 7, 18, 10, 0, tzinfo=UTC)
    job_id = _generate_job_id(lane, t, t)

    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id=job_id,
        lane=lane,
        source_commit="abc",
        created_at=t,
        requested_start_bar_open=t,
        requested_end_bar_open=t,
        provider_as_of_boundary=t,
        symbols=("BTCUSD",),
        accepted_frontier_bar_open=t,
        expected_frontier_bar_open=t + timedelta(hours=1),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )
    store.insert_job(job)

    # Same fixed timestamp and PID but different nonces
    fixed_ts = "20260718100000"
    fixed_pid = "12345"
    nonce_a = uuid.uuid4().hex[:8]
    nonce_b = uuid.uuid4().hex[:8]
    # UUID4 nonces are astronomically unlikely to collide but resample if they do
    while nonce_a == nonce_b:
        nonce_b = uuid.uuid4().hex[:8]

    identity_a = f"run_{fixed_ts}_{fixed_pid}_{nonce_a}"
    identity_b = f"run_{fixed_ts}_{fixed_pid}_{nonce_b}"
    assert identity_a != identity_b, "Identities with same ts/pid but different nonces must differ"

    # Claim with identity_a
    claimed = store.claim_job(job_id, identity_a, datetime.now(UTC))
    assert claimed

    j = store.get_job(job_id)
    assert j is not None
    assert j.claim_identity == identity_a

    # Stale identity_b cannot complete attempt owned by identity_a
    stale_complete = dc_replace(j, claim_identity=identity_b, status=SchedulerJobStatus.COMPLETED)
    with pytest.raises(ValidationError):
        store.update_job(stale_complete)

    # Stale identity_b cannot fail attempt owned by identity_a
    stale_fail = dc_replace(j, claim_identity=identity_b, status=SchedulerJobStatus.FAILED)
    with pytest.raises(ValidationError):
        store.update_job(stale_fail)

    # Correct identity_a can complete
    good_final = dc_replace(j, status=SchedulerJobStatus.COMPLETED)
    store.update_job(good_final)
    completed = store.get_job(job_id)
    assert completed is not None
    assert completed.status == SchedulerJobStatus.COMPLETED


# ==========================================
# ROUND 3 — TEST H: Type-Hint Resolution
# ==========================================

def test_type_hint_resolution() -> None:
    """H. EligibleWindow annotation resolves; ScheduleWindow is not defined in the module."""
    import typing
    import algotrader.orchestration.crypto_tournament_v2_oos_scheduler as sched_mod

    assert hasattr(sched_mod, "EligibleWindow"), "EligibleWindow must be defined in the scheduler module"
    ew = sched_mod.EligibleWindow

    hints = typing.get_type_hints(sched_mod.OneShotExecutor._fail_job_and_write_receipt)
    window_hint = hints.get("window")
    assert window_hint is ew, (
        f"_fail_job_and_write_receipt.window annotated as {window_hint!r}, "
        f"expected EligibleWindow ({ew!r})"
    )

    assert not hasattr(sched_mod, "ScheduleWindow"), (
        "ScheduleWindow must not exist as a module-level name; only EligibleWindow is canonical"
    )


# ==========================================
# ROUND 4 — TEST I: Disabled Adoption Gate
# ==========================================

def _persist_pending_job(store: SqliteJobStore) -> SchedulerJob:
    """Helper: insert one hour-aligned PENDING job as a crash leftover."""
    start = datetime(2026, 7, 18, 3, 0, tzinfo=UTC)
    end = datetime(2026, 7, 18, 5, 0, tzinfo=UTC)
    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id=hashlib.sha256(b"round4_disabled_gate").hexdigest()[:32],
        lane="crypto_tournament_v2_forward_oos",
        source_commit="deadbeef",
        created_at=datetime(2026, 7, 18, 6, 0, tzinfo=UTC),
        requested_start_bar_open=start,
        requested_end_bar_open=end,
        provider_as_of_boundary=end + timedelta(hours=1),
        symbols=("BTCUSD", "ETHUSD", "SOLUSD"),
        accepted_frontier_bar_open=start - timedelta(hours=1),
        expected_frontier_bar_open=end + timedelta(hours=1),
        status=SchedulerJobStatus.PENDING,
        attempt_number=0,
        claim_identity="",
    )
    store.insert_job(job)
    return job


def test_disabled_tick_never_claims_persisted_pending_job(tmp_path: Path) -> None:
    """I1. enabled=False + persisted PENDING job → blocked, no claim, no dispatch."""
    db_file = tmp_path / "disabled_gate.sqlite3"
    output_root = tmp_path / "disabled_gate"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    dispatcher = MagicMock()
    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=dispatcher,
        enabled=False,
        allow_network=False,
    )
    executor.store.initialize()
    pending = _persist_pending_job(executor.store)

    receipt = executor.tick(datetime(2026, 7, 19, 12, 0, tzinfo=UTC))

    assert receipt["command_classification"] == "blocked_scheduler_disabled"
    assert receipt["job_status"] == "blocked"
    assert receipt["job_id"] == pending.job_id
    dispatcher.dispatch.assert_not_called()

    stored = executor.store.get_job(pending.job_id)
    assert stored is not None
    assert stored.status == SchedulerJobStatus.PENDING
    assert stored.attempt_number == 0
    assert stored.claim_identity == ""


def test_disabled_tick_preserves_real_state_from_preview_overwrite(
    tmp_path: Path,
) -> None:
    """I2. enabled=False + PENDING job + PreviewDispatcher → real artifacts untouched."""
    db_file = tmp_path / "disabled_preview.sqlite3"
    output_root = tmp_path / "disabled_preview"
    output_root.mkdir(parents=True, exist_ok=True)
    real_state = json.dumps(
        {"record_type": "crypto_tournament_v2_frozen_state", "marker": "REAL_STATE"}
    )
    (output_root / "frozen_state.json").write_text(real_state, encoding="utf-8")

    executor = OneShotExecutor(
        db_path=db_file,
        output_root=output_root,
        discovery_source=tmp_path / "source.csv",
        discovery_receipt=tmp_path / "receipt.json",
        dispatcher=PreviewDispatcher(),
        enabled=False,
        allow_network=False,
    )
    executor.store.initialize()
    pending = _persist_pending_job(executor.store)

    receipt = executor.tick(datetime(2026, 7, 19, 12, 0, tzinfo=UTC))

    assert receipt["command_classification"] == "blocked_scheduler_disabled"
    state_after = (output_root / "frozen_state.json").read_text(encoding="utf-8")
    assert state_after == real_state
    assert not (output_root / "operating_packet.json").exists()

    stored = executor.store.get_job(pending.job_id)
    assert stored is not None
    assert stored.status == SchedulerJobStatus.PENDING
    assert stored.attempt_number == 0


def test_enabled_tick_still_adopts_persisted_pending_job(tmp_path: Path) -> None:
    """I3. enabled=True keeps round-3 adoption: stored PENDING job is claimed."""
    db_file = tmp_path / "enabled_adoption.sqlite3"
    output_root = tmp_path / "enabled_adoption"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "frozen_state.json").write_text("{}", encoding="utf-8")

    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = {
        "status": "failed",
        "classification": "subprocess_error",
        "reason": "Simulated failure",
    }
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
    pending = _persist_pending_job(executor.store)

    executor.tick(datetime(2026, 7, 19, 12, 0, tzinfo=UTC))

    dispatcher.dispatch.assert_called_once()
    stored = executor.store.get_job(pending.job_id)
    assert stored is not None
    assert stored.attempt_number == 1
    dispatched_job = dispatcher.dispatch.call_args.kwargs["job"]
    assert dispatched_job.requested_start_bar_open == pending.requested_start_bar_open
    assert dispatched_job.requested_end_bar_open == pending.requested_end_bar_open
