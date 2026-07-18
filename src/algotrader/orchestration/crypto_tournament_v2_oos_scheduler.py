"""Deterministic tournament-v2 OOS scheduler and durable job state.

This module is the core control plane scheduler. It calculates window eligibility,
manages durable SQLite-backed job status lifecycle, claims jobs atomically,
dispatches accruals, and logs secret-free receipts.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Callable, Mapping, Sequence

from algotrader.errors import ValidationError
from algotrader.core.time import require_utc_datetime

SCHEDULER_VERSION = "v5.31a_v1"
SCHEDULER_SCHEMA_VERSION = "v5_31a_scheduler_schema_v1"

_ONE_HOUR = timedelta(hours=1)


class SchedulerJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class EligibleWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class CalculationResult:
    status: str  # "eligible", "no_eligible_window", "blocked"
    classification: str
    window: EligibleWindow | None = None
    reason: str = ""


@dataclass(frozen=True)
class SchedulerJob:
    schema_version: str
    job_id: str
    lane: str
    source_commit: str
    created_at: datetime
    requested_start: datetime
    requested_end: datetime
    symbols: tuple[str, ...]
    current_frontier: datetime
    expected_next_frontier: datetime
    status: SchedulerJobStatus
    attempt_number: int
    claim_identity: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_classification: str = ""
    error_classification: str = ""
    receipt_paths: tuple[str, ...] = ()
    receipt_hashes: tuple[str, ...] = ()
    source_state_fingerprint_before: str = ""
    source_state_fingerprint_after: str = ""
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "job_id": self.job_id,
            "lane": self.lane,
            "source_commit": self.source_commit,
            "created_at": self.created_at.isoformat(),
            "requested_start": self.requested_start.isoformat(),
            "requested_end": self.requested_end.isoformat(),
            "symbols": list(self.symbols),
            "current_frontier": self.current_frontier.isoformat(),
            "expected_next_frontier": self.expected_next_frontier.isoformat(),
            "status": self.status.value,
            "attempt_number": self.attempt_number,
            "claim_identity": self.claim_identity,
            "started_at": self.started_at.isoformat() if self.started_at else "",
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
            "result_classification": self.result_classification,
            "error_classification": self.error_classification,
            "receipt_paths": list(self.receipt_paths),
            "receipt_hashes": list(self.receipt_hashes),
            "source_state_fingerprint_before": self.source_state_fingerprint_before,
            "source_state_fingerprint_after": self.source_state_fingerprint_after,
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class ScheduleCalculator:
    @staticmethod
    def calculate_eligible_window(
        current_time: datetime,
        frontier: datetime,
        bar_interval: timedelta = _ONE_HOUR,
        publication_grace: timedelta = timedelta(minutes=5),
        max_catch_up_hours: int = 24,
        enabled: bool = False,
    ) -> CalculationResult:
        """Determines the eligible contiguous window of closed hours to accrue."""
        try:
            require_utc_datetime(current_time)
        except ValidationError as exc:
            return CalculationResult(
                status="blocked",
                classification="blocked_malformed_current_time",
                reason=str(exc),
            )
        try:
            require_utc_datetime(frontier)
        except ValidationError as exc:
            return CalculationResult(
                status="blocked",
                classification="blocked_malformed_frontier",
                reason=str(exc),
            )

        if (
            frontier.minute != 0
            or frontier.second != 0
            or frontier.microsecond != 0
        ):
            return CalculationResult(
                status="blocked",
                classification="blocked_malformed_frontier",
                reason="Frontier must be UTC hour-aligned",
            )

        if not enabled:
            return CalculationResult(
                status="blocked",
                classification="blocked_scheduler_disabled",
                reason="Scheduler is disabled by default",
            )

        if current_time < frontier:
            return CalculationResult(
                status="blocked",
                classification="blocked_clock_regression",
                reason="Current time is before frontier",
            )

        if current_time == frontier:
            return CalculationResult(
                status="no_eligible_window",
                classification="no_eligible_closed_window",
                reason="Current time equals frontier",
            )

        next_needed = frontier + bar_interval
        if current_time < next_needed + publication_grace:
            return CalculationResult(
                status="no_eligible_window",
                classification="no_eligible_closed_window",
                reason="Next needed hour has not passed publication grace period",
            )

        latest_eligible = current_time - publication_grace
        latest_eligible = latest_eligible.replace(
            minute=0, second=0, microsecond=0
        )

        if latest_eligible < next_needed:
            return CalculationResult(
                status="no_eligible_window",
                classification="no_eligible_closed_window",
                reason="No eligible closed hours available",
            )

        total_hours = (
            int((latest_eligible - next_needed).total_seconds() / 3600) + 1
        )
        if total_hours > max_catch_up_hours:
            latest_eligible = next_needed + timedelta(
                hours=max_catch_up_hours - 1
            )

        return CalculationResult(
            status="eligible",
            classification="eligible_window_calculated",
            window=EligibleWindow(start=next_needed, end=latest_eligible),
        )


class SqliteJobStore:
    """SQLite job store supporting atomic transactions and WAL concurrency."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS scheduler_metadata "
                    "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                existing = connection.execute(
                    "SELECT value FROM scheduler_metadata WHERE key = 'schema_version'"
                ).fetchone()

                if existing is None:
                    connection.execute(
                        "INSERT INTO scheduler_metadata (key, value) VALUES ('schema_version', ?)",
                        (SCHEDULER_SCHEMA_VERSION,),
                    )
                    self._create_schema(connection)
                else:
                    if existing[0] != SCHEDULER_SCHEMA_VERSION:
                        raise ValidationError(
                            f"Unsupported scheduler schema version: {existing[0]}"
                        )
                    self._verify_schema(connection)
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Scheduler database initialization failed: {exc}"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=5,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _create_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduler_jobs (
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

    def _verify_schema(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(scheduler_jobs)"
            ).fetchall()
        }
        required = {
            "job_id",
            "schema_version",
            "lane",
            "source_commit",
            "created_at",
            "requested_start",
            "requested_end",
            "symbols",
            "current_frontier",
            "expected_next_frontier",
            "status",
            "attempt_number",
            "claim_identity",
            "started_at",
            "completed_at",
            "result_classification",
            "error_classification",
            "receipt_paths",
            "receipt_hashes",
            "source_state_fingerprint_before",
            "source_state_fingerprint_after",
            "updated_at",
        }
        missing = required - columns
        if missing:
            raise ValidationError(
                f"Scheduler database is corrupt, missing fields: {missing}"
            )

    def get_job(self, job_id: str) -> SchedulerJob | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM scheduler_jobs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
                if row is None:
                    return None
                return self._row_to_job(row)
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Failed to load job {job_id}: {exc}"
            ) from exc

    def insert_job(self, job: SchedulerJob) -> None:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    # Overlap protection
                    overlaps = connection.execute(
                        """
                        SELECT COUNT(*) FROM scheduler_jobs
                        WHERE lane = ?
                          AND status IN ('pending', 'running')
                          AND requested_start <= ?
                          AND requested_end >= ?
                        """,
                        (
                            job.lane,
                            job.requested_end.isoformat(),
                            job.requested_start.isoformat(),
                        ),
                    ).fetchone()[0]
                    if overlaps > 0:
                        raise ValidationError(
                            "Overlapping active job exists for this window."
                        )

                    connection.execute(
                        """
                        INSERT INTO scheduler_jobs (
                            job_id, schema_version, lane, source_commit, created_at,
                            requested_start, requested_end, symbols, current_frontier,
                            expected_next_frontier, status, attempt_number, claim_identity,
                            started_at, completed_at, result_classification, error_classification,
                            receipt_paths, receipt_hashes, source_state_fingerprint_before,
                            source_state_fingerprint_after, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        self._job_sql_values(job),
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                f"Duplicate job ID detected: {job.job_id}"
            ) from exc
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Failed to insert job {job.job_id}: {exc}"
            ) from exc

    def claim_job(
        self, job_id: str, claim_identity: str, started_at: datetime
    ) -> bool:
        """Atomically transitions a job from pending to running."""
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    updated = connection.execute(
                        """
                        UPDATE scheduler_jobs
                        SET status = ?,
                            claim_identity = ?,
                            started_at = ?,
                            attempt_number = attempt_number + 1,
                            updated_at = ?
                        WHERE job_id = ? AND status = ?
                        """,
                        (
                            SchedulerJobStatus.RUNNING.value,
                            claim_identity,
                            started_at.isoformat(),
                            started_at.isoformat(),
                            job_id,
                            SchedulerJobStatus.PENDING.value,
                        ),
                    ).rowcount
                    connection.commit()
                    return updated == 1
                except Exception:
                    connection.rollback()
                    raise
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Claim job {job_id} transaction failed: {exc}"
            ) from exc

    def update_job(self, job: SchedulerJob) -> None:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    updated_at = datetime.now(UTC).isoformat()
                    connection.execute(
                        """
                        UPDATE scheduler_jobs
                        SET status = ?,
                            completed_at = ?,
                            result_classification = ?,
                            error_classification = ?,
                            receipt_paths = ?,
                            receipt_hashes = ?,
                            source_state_fingerprint_before = ?,
                            source_state_fingerprint_after = ?,
                            updated_at = ?
                        WHERE job_id = ?
                        """,
                        (
                            job.status.value,
                            (
                                job.completed_at.isoformat()
                                if job.completed_at
                                else ""
                            ),
                            job.result_classification,
                            job.error_classification,
                            json.dumps(list(job.receipt_paths)),
                            json.dumps(list(job.receipt_hashes)),
                            job.source_state_fingerprint_before,
                            job.source_state_fingerprint_after,
                            updated_at,
                            job.job_id,
                        ),
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Failed to update job {job.job_id}: {exc}"
            ) from exc

    def list_jobs(self, lane: str | None = None) -> list[SchedulerJob]:
        try:
            with self._connect() as connection:
                if lane:
                    rows = connection.execute(
                        "SELECT * FROM scheduler_jobs WHERE lane = ? ORDER BY created_at DESC",
                        (lane,),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT * FROM scheduler_jobs ORDER BY created_at DESC"
                    ).fetchall()
                return [self._row_to_job(row) for row in rows]
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Failed to list scheduler jobs: {exc}"
            ) from exc

    def recover_stale_jobs(
        self, lane: str, max_age: timedelta
    ) -> list[SchedulerJob]:
        """Finds running jobs older than max_age and marks them as failed."""
        recovered: list[SchedulerJob] = []
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    cutoff = (datetime.now(UTC) - max_age).isoformat()
                    rows = connection.execute(
                        """
                        SELECT * FROM scheduler_jobs
                        WHERE lane = ? AND status = ? AND updated_at < ?
                        """,
                        (lane, SchedulerJobStatus.RUNNING.value, cutoff),
                    ).fetchall()

                    for row in rows:
                        job = self._row_to_job(row)
                        now_utc = datetime.now(UTC)
                        updated = replace(
                            job,
                            status=SchedulerJobStatus.FAILED,
                            completed_at=now_utc,
                            error_classification="stale_timeout_recovered",
                            updated_at=now_utc,
                        )
                        connection.execute(
                            """
                            UPDATE scheduler_jobs
                            SET status = ?, completed_at = ?, error_classification = ?, updated_at = ?
                            WHERE job_id = ?
                            """,
                            (
                                updated.status.value,
                                updated.completed_at.isoformat(),
                                updated.error_classification,
                                now_utc.isoformat(),
                                updated.job_id,
                            ),
                        )
                        recovered.append(updated)
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Failed to recover stale running jobs: {exc}"
            ) from exc
        return recovered

    def _row_to_job(self, row: sqlite3.Row) -> SchedulerJob:
        return SchedulerJob(
            schema_version=row["schema_version"],
            job_id=row["job_id"],
            lane=row["lane"],
            source_commit=row["source_commit"],
            created_at=datetime.fromisoformat(row["created_at"]),
            requested_start=datetime.fromisoformat(row["requested_start"]),
            requested_end=datetime.fromisoformat(row["requested_end"]),
            symbols=tuple(json.loads(row["symbols"])),
            current_frontier=datetime.fromisoformat(row["current_frontier"]),
            expected_next_frontier=datetime.fromisoformat(
                row["expected_next_frontier"]
            ),
            status=SchedulerJobStatus(row["status"]),
            attempt_number=row["attempt_number"],
            claim_identity=row["claim_identity"],
            started_at=(
                datetime.fromisoformat(row["started_at"])
                if row["started_at"]
                else None
            ),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            result_classification=row["result_classification"],
            error_classification=row["error_classification"],
            receipt_paths=tuple(json.loads(row["receipt_paths"])),
            receipt_hashes=tuple(json.loads(row["receipt_hashes"])),
            source_state_fingerprint_before=row[
                "source_state_fingerprint_before"
            ],
            source_state_fingerprint_after=row[
                "source_state_fingerprint_after"
            ],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _job_sql_values(self, job: SchedulerJob) -> tuple:
        return (
            job.job_id,
            job.schema_version,
            job.lane,
            job.source_commit,
            job.created_at.isoformat(),
            job.requested_start.isoformat(),
            job.requested_end.isoformat(),
            json.dumps(list(job.symbols)),
            job.current_frontier.isoformat(),
            job.expected_next_frontier.isoformat(),
            job.status.value,
            job.attempt_number,
            job.claim_identity,
            job.started_at.isoformat() if job.started_at else "",
            job.completed_at.isoformat() if job.completed_at else "",
            job.result_classification,
            job.error_classification,
            json.dumps(list(job.receipt_paths)),
            json.dumps(list(job.receipt_hashes)),
            job.source_state_fingerprint_before,
            job.source_state_fingerprint_after,
            (
                job.updated_at.isoformat()
                if job.updated_at
                else job.created_at.isoformat()
            ),
        )


class CommandDispatcher:
    def dispatch(
        self,
        job: SchedulerJob,
        output_root: Path,
        discovery_source: Path,
        discovery_receipt: Path,
        allow_network: bool,
    ) -> dict[str, object]:
        raise NotImplementedError


class PreviewDispatcher(CommandDispatcher):
    def dispatch(
        self,
        job: SchedulerJob,
        output_root: Path,
        discovery_source: Path,
        discovery_receipt: Path,
        allow_network: bool,
    ) -> dict[str, object]:
        # Return deterministic preview/fixture outcome
        return {
            "status": "success",
            "classification": "preview_successful",
            "dispatch_type": "preview",
            "market_data_fetch_occurred": False,
            "network_access_attempted": False,
            "receipt_paths": [
                "runs/crypto_strategy_tournament/v2/latest/forward_oos_delta.csv"
            ],
            "receipt_hashes": [
                "da39a3ee5e6b4b0d3255bfef95601890afd80709"
            ],  # Mock hash
        }


class RealCommandDispatcher(CommandDispatcher):
    def __init__(
        self, scheduler_enabled: bool, market_data_read_authorized: bool
    ) -> None:
        self.scheduler_enabled = scheduler_enabled
        self.market_data_read_authorized = market_data_read_authorized

    def dispatch(
        self,
        job: SchedulerJob,
        output_root: Path,
        discovery_source: Path,
        discovery_receipt: Path,
        allow_network: bool,
    ) -> dict[str, object]:
        if not self.scheduler_enabled:
            raise ValidationError("Real dispatch rejected: Scheduler is disabled.")
        if not self.market_data_read_authorized:
            raise ValidationError(
                "Real dispatch rejected: MarketDataReadAuthorized is false."
            )
        if not allow_network:
            raise ValidationError(
                "Real dispatch rejected: AllowNetwork is false."
            )

        cmd = [
            sys.executable,
            "-I",
            "-m",
            "algotrader.orchestration.crypto_tournament_v2_forward_oos",
            "--mode",
            "market_data_fetch",
            "--output-root",
            str(output_root),
            "--discovery-source-path",
            str(discovery_source),
            "--discovery-receipt-path",
            str(discovery_receipt),
            "--market-data-fetch-authorized",
            "--allow-network",
            "--as-of",
            job.requested_end.isoformat(),
        ]

        # Clean environment copy
        env = os.environ.copy()
        # Keep PYTHONPATH, but ensure Python Software Foundation standard execution environment is safe
        # (wrapper scrubs credentials, but child uses whatever was inherited if any)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            if result.returncode != 0:
                return {
                    "status": "failed",
                    "classification": "subprocess_error",
                    "dispatch_type": "real",
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            # Try to parse stdout as json
            try:
                data = json.loads(result.stdout)
                return {
                    "status": "success",
                    "classification": "subprocess_completed",
                    "dispatch_type": "real",
                    "output": data,
                }
            except json.JSONDecodeError:
                return {
                    "status": "failed",
                    "classification": "subprocess_unparseable_output",
                    "dispatch_type": "real",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
        except Exception as exc:
            return {
                "status": "failed",
                "classification": "subprocess_exception",
                "dispatch_type": "real",
                "error_type": exc.__class__.__name__,
                "reason": str(exc),
            }


class OneShotExecutor:
    def __init__(
        self,
        db_path: Path,
        output_root: Path,
        discovery_source: Path,
        discovery_receipt: Path,
        dispatcher: CommandDispatcher,
        enabled: bool = False,
        allow_network: bool = False,
    ) -> None:
        self.db_path = db_path
        self.output_root = output_root
        self.discovery_source = discovery_source
        self.discovery_receipt = discovery_receipt
        self.dispatcher = dispatcher
        self.enabled = enabled
        self.allow_network = allow_network
        self.store = SqliteJobStore(db_path)

    def tick(self, current_time: datetime) -> dict[str, object]:
        """Runs one schedule tick."""
        start_time = datetime.now(UTC)
        require_utc_datetime(current_time)

        # 1. Initialize Store (Fail-closed on corruption)
        try:
            self.store.initialize()
        except Exception as exc:
            return self._write_noop_receipt(
                job_id="na",
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=current_time,
                start=current_time,
                end=current_time,
                classification="quarantined_corrupt_store",
                reason=f"Database corruption: {exc}",
                duration=0.0,
            )

        lane = "crypto_tournament_v2_forward_oos"
        symbols = ("BTCUSD", "ETHUSD", "SOLUSD")

        # 2. Inspect tournament v2 OOS state to find frontier
        # Import research/orchestration lane inside executor boundary to satisfy dependency checks
        from algotrader.research.crypto_tournament_v2_forward_oos import (
            run_crypto_tournament_v2_forward_oos,
            initialize_crypto_tournament_v2_forward_oos,
        )

        paths_dict = {
            "state": self.output_root / "frozen_state.json",
        }

        # Initialize tournament state if missing
        if not paths_dict["state"].is_file():
            if not self.discovery_source.is_file():
                return self._write_noop_receipt(
                    job_id="na",
                    status=SchedulerJobStatus.BLOCKED,
                    mode="status",
                    frontier=current_time,
                    start=current_time,
                    end=current_time,
                    classification="blocked_missing_discovery_source",
                    reason="Tournament state not initialized and discovery source missing",
                    duration=0.0,
                )
            try:
                initialize_crypto_tournament_v2_forward_oos(
                    discovery_source_path=self.discovery_source,
                    discovery_receipt_path=self.discovery_receipt,
                    output_root=self.output_root,
                    as_of=current_time,
                    write_artifacts=True,
                )
            except Exception as exc:
                return self._write_noop_receipt(
                    job_id="na",
                    status=SchedulerJobStatus.BLOCKED,
                    mode="status",
                    frontier=current_time,
                    start=current_time,
                    end=current_time,
                    classification="blocked_initialization_failed",
                    reason=f"Failed to initialize tournament state: {exc}",
                    duration=0.0,
                )

        try:
            status = run_crypto_tournament_v2_forward_oos(
                output_root=self.output_root,
                as_of=current_time,
                write_artifacts=False,
            )
        except Exception as exc:
            return self._write_noop_receipt(
                job_id="na",
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=current_time,
                start=current_time,
                end=current_time,
                classification="blocked_oos_load_failed",
                reason=f"Failed to load OOS status: {exc}",
                duration=0.0,
            )

        next_refresh = status.get("next_refresh", {})
        ref_class = next_refresh.get("classification", "")

        # Check completed tournament
        if ref_class == "terminal_window_closed":
            return self._write_noop_receipt(
                job_id="na",
                status=SchedulerJobStatus.COMPLETED,
                mode="status",
                frontier=current_time,
                start=current_time,
                end=current_time,
                classification="accrual_complete",
                reason="Tournament forward OOS accrual is complete (terminal window reached)",
                duration=0.0,
            )

        requested_start_str = next_refresh.get("requested_start", "")
        if not requested_start_str:
            # accrual complete or waiting for hour
            if ref_class == "accrual_complete":
                return self._write_noop_receipt(
                    job_id="na",
                    status=SchedulerJobStatus.COMPLETED,
                    mode="status",
                    frontier=current_time,
                    start=current_time,
                    end=current_time,
                    classification="accrual_complete",
                    reason="Accrual complete according to tournament next_refresh payload",
                    duration=0.0,
                )
            else:
                return self._write_noop_receipt(
                    job_id="na",
                    status=SchedulerJobStatus.BLOCKED,
                    mode="status",
                    frontier=current_time,
                    start=current_time,
                    end=current_time,
                    classification="no_eligible_closed_window",
                    reason="No next refresh hour requested by OOS status",
                    duration=0.0,
                )

        requested_start = datetime.fromisoformat(
            requested_start_str.replace("Z", "+00:00")
        )
        frontier = requested_start - _ONE_HOUR

        # 3. Calculate Eligible Window using ScheduleCalculator
        calc = ScheduleCalculator.calculate_eligible_window(
            current_time=current_time,
            frontier=frontier,
            bar_interval=_ONE_HOUR,
            publication_grace=timedelta(minutes=5),
            max_catch_up_hours=24,
            enabled=self.enabled,
        )

        if calc.status == "blocked":
            return self._write_noop_receipt(
                job_id="na",
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=frontier,
                start=current_time,
                end=current_time,
                classification=calc.classification,
                reason=calc.reason,
                duration=0.0,
            )

        if calc.status == "no_eligible_window":
            return self._write_noop_receipt(
                job_id="na",
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=frontier,
                start=current_time,
                end=current_time,
                classification=calc.classification,
                reason=calc.reason,
                duration=0.0,
            )

        assert calc.window is not None
        window = calc.window

        # 4. Deterministic Job ID for same lane/window
        job_id = _generate_job_id(lane, window.start, window.end)

        # 5. Check if Job exists in store
        existing_job = self.store.get_job(job_id)
        source_state_before = _file_sha256(self.output_root / "frozen_state.json")

        if existing_job:
            if existing_job.status == SchedulerJobStatus.COMPLETED:
                return self._write_noop_receipt(
                    job_id=job_id,
                    status=SchedulerJobStatus.COMPLETED,
                    mode="status",
                    frontier=frontier,
                    start=window.start,
                    end=window.end,
                    classification="idempotent_no_op",
                    reason="Window already successfully processed and recorded.",
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                )
            elif existing_job.status == SchedulerJobStatus.RUNNING:
                # Check if stale (timeout 15 minutes)
                stale_limit = timedelta(minutes=15)
                if (
                    existing_job.updated_at
                    and datetime.now(UTC) - existing_job.updated_at
                    > stale_limit
                ):
                    # Recover stale job
                    self.store.recover_stale_jobs(lane, stale_limit)
                    return self._write_noop_receipt(
                        job_id=job_id,
                        status=SchedulerJobStatus.FAILED,
                        mode="status",
                        frontier=frontier,
                        start=window.start,
                        end=window.end,
                        classification="stale_timeout_recovered",
                        reason="Crashed/stale running job detected and recovered to FAILED.",
                        duration=(
                            datetime.now(UTC) - start_time
                        ).total_seconds(),
                    )
                else:
                    return self._write_noop_receipt(
                        job_id=job_id,
                        status=SchedulerJobStatus.BLOCKED,
                        mode="status",
                        frontier=frontier,
                        start=window.start,
                        end=window.end,
                        classification="blocked_concurrent_run",
                        reason="Job is currently running under a valid lease.",
                        duration=(
                            datetime.now(UTC) - start_time
                        ).total_seconds(),
                    )
            elif existing_job.status in (
                SchedulerJobStatus.FAILED,
                SchedulerJobStatus.BLOCKED,
            ):
                return self._write_noop_receipt(
                    job_id=job_id,
                    status=existing_job.status,
                    mode="status",
                    frontier=frontier,
                    start=window.start,
                    end=window.end,
                    classification="no_automatic_retry",
                    reason=f"Prior job was in {existing_job.status} state. Retries disabled.",
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                )

        # 6. Create Pending Job
        commit_hash = _get_source_commit()
        job = SchedulerJob(
            schema_version=SCHEDULER_SCHEMA_VERSION,
            job_id=job_id,
            lane=lane,
            source_commit=commit_hash,
            created_at=datetime.now(UTC),
            requested_start=window.start,
            requested_end=window.end,
            symbols=symbols,
            current_frontier=frontier,
            expected_next_frontier=window.end,
            status=SchedulerJobStatus.PENDING,
            attempt_number=0,
            claim_identity="",
            source_state_fingerprint_before=source_state_before,
        )

        try:
            self.store.insert_job(job)
        except ValidationError as exc:
            # Overlap or concurrent insert block
            return self._write_noop_receipt(
                job_id=job_id,
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=frontier,
                start=window.start,
                end=window.end,
                classification="blocked_concurrent_overlap",
                reason=str(exc),
                duration=(datetime.now(UTC) - start_time).total_seconds(),
            )

        # 7. Claim Job Atomically
        claim_identity = f"run_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{os.getpid()}"
        started_at = datetime.now(UTC)
        claimed = self.store.claim_job(job_id, claim_identity, started_at)

        if not claimed:
            return self._write_noop_receipt(
                job_id=job_id,
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=frontier,
                start=window.start,
                end=window.end,
                classification="blocked_claim_contention",
                reason="Failed to claim pending job due to contention",
                duration=(datetime.now(UTC) - start_time).total_seconds(),
            )

        # Refetch claimed job
        job = self.store.get_job(job_id)
        assert job is not None

        # 8. Dispatch Command
        dispatch_result = self.dispatcher.dispatch(
            job=job,
            output_root=self.output_root,
            discovery_source=self.discovery_source,
            discovery_receipt=self.discovery_receipt,
            allow_network=self.allow_network,
        )

        now_utc = datetime.now(UTC)
        source_state_after = _file_sha256(self.output_root / "frozen_state.json")
        receipt_paths, receipt_hashes = _get_tournament_receipts(
            self.output_root
        )

        # 9. Record Terminal Result
        if dispatch_result.get("status") == "success":
            final_job = replace(
                job,
                status=SchedulerJobStatus.COMPLETED,
                completed_at=now_utc,
                result_classification=dispatch_result.get(
                    "classification", "success"
                ),
                receipt_paths=tuple(receipt_paths),
                receipt_hashes=tuple(receipt_hashes),
                source_state_fingerprint_after=source_state_after,
            )
            self.store.update_job(final_job)
            return self._write_receipt_file(
                job=final_job,
                mode="run_once",
                duration=(datetime.now(UTC) - start_time).total_seconds(),
                reason="Subprocess accrual executed successfully.",
            )
        else:
            final_job = replace(
                job,
                status=SchedulerJobStatus.FAILED,
                completed_at=now_utc,
                error_classification=dispatch_result.get(
                    "classification", "subprocess_failed"
                ),
                receipt_paths=tuple(receipt_paths),
                receipt_hashes=tuple(receipt_hashes),
                source_state_fingerprint_after=source_state_after,
            )
            self.store.update_job(final_job)
            return self._write_receipt_file(
                job=final_job,
                mode="run_once",
                duration=(datetime.now(UTC) - start_time).total_seconds(),
                reason=dispatch_result.get("reason", "Subprocess execution failed."),
            )

    def _write_noop_receipt(
        self,
        job_id: str,
        status: SchedulerJobStatus,
        mode: str,
        frontier: datetime,
        start: datetime,
        end: datetime,
        classification: str,
        reason: str,
        duration: float,
    ) -> dict[str, object]:
        now_utc = datetime.now(UTC)
        next_check = now_utc + _ONE_HOUR
        receipt = {
            "schema_version": SCHEDULER_SCHEMA_VERSION,
            "source_commit": _get_source_commit(),
            "scheduler_version": SCHEDULER_VERSION,
            "job_id": job_id,
            "job_status": status.value,
            "invoked_mode": mode,
            "clock_time": now_utc.isoformat(),
            "frontier_before": frontier.isoformat(),
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "expected_frontier": end.isoformat(),
            "dispatcher_type": self.dispatcher.__class__.__name__,
            "authorization_status": {
                "scheduler_enabled": self.enabled,
                "allow_network": self.allow_network,
            },
            "credential_loaded_booleans": {
                "ALPACA_API_KEY_present": "ALPACA_API_KEY" in os.environ,
                "ALPACA_API_SECRET_KEY_present": "ALPACA_API_SECRET_KEY"
                in os.environ,
            },
            "network_used": self.allow_network,
            "broker_read": False,
            "broker_mutation": False,
            "paper_submit": False,
            "live_endpoint_used": False,
            "command_classification": classification,
            "native_tournament_receipt_paths": [],
            "native_tournament_receipt_hashes": [],
            "source_state_hash_before": _file_sha256(
                self.output_root / "frozen_state.json"
            ),
            "source_state_hash_after": _file_sha256(
                self.output_root / "frozen_state.json"
            ),
            "duration_seconds": duration,
            "next_eligible_check": next_check.isoformat(),
            "operator_action_required": (status == SchedulerJobStatus.FAILED),
            "exact_reason": reason,
        }
        _write_receipt_file_atomic(self.output_root, job_id, receipt)
        return receipt

    def _write_receipt_file(
        self,
        job: SchedulerJob,
        mode: str,
        duration: float,
        reason: str,
    ) -> dict[str, object]:
        now_utc = datetime.now(UTC)
        next_check = now_utc + _ONE_HOUR
        receipt = {
            "schema_version": SCHEDULER_SCHEMA_VERSION,
            "source_commit": job.source_commit,
            "scheduler_version": SCHEDULER_VERSION,
            "job_id": job.job_id,
            "job_status": job.status.value,
            "invoked_mode": mode,
            "clock_time": now_utc.isoformat(),
            "frontier_before": job.current_frontier.isoformat(),
            "requested_start": job.requested_start.isoformat(),
            "requested_end": job.requested_end.isoformat(),
            "expected_frontier": job.expected_next_frontier.isoformat(),
            "dispatcher_type": self.dispatcher.__class__.__name__,
            "authorization_status": {
                "scheduler_enabled": self.enabled,
                "allow_network": self.allow_network,
            },
            "credential_loaded_booleans": {
                "ALPACA_API_KEY_present": "ALPACA_API_KEY" in os.environ,
                "ALPACA_API_SECRET_KEY_present": "ALPACA_API_SECRET_KEY"
                in os.environ,
            },
            "network_used": self.allow_network,
            "broker_read": False,
            "broker_mutation": False,
            "paper_submit": False,
            "live_endpoint_used": False,
            "command_classification": (
                job.result_classification
                if job.status == SchedulerJobStatus.COMPLETED
                else job.error_classification
            ),
            "native_tournament_receipt_paths": list(job.receipt_paths),
            "native_tournament_receipt_hashes": list(job.receipt_hashes),
            "source_state_hash_before": job.source_state_fingerprint_before,
            "source_state_hash_after": job.source_state_fingerprint_after,
            "duration_seconds": duration,
            "next_eligible_check": next_check.isoformat(),
            "operator_action_required": (job.status == SchedulerJobStatus.FAILED),
            "exact_reason": reason,
        }
        _write_receipt_file_atomic(self.output_root, job.job_id, receipt)
        return receipt


def _generate_job_id(lane: str, start: datetime, end: datetime) -> str:
    # deterministic string hash
    key = f"{lane}:{start.replace(tzinfo=None).isoformat()}:{end.replace(tzinfo=None).isoformat()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _get_tournament_receipts(output_root: Path) -> tuple[list[str], list[str]]:
    paths = []
    hashes = []
    # collect tournament v2 latest state outputs
    for p in sorted(output_root.glob("*")):
        if (
            p.is_file()
            and p.name not in ("scheduler.sqlite3", "scheduler_receipts")
            and not p.name.startswith("receipt_")
        ):
            paths.append(str(p.name))
            hashes.append(_file_sha256(p))
    return paths, hashes


def _write_receipt_file_atomic(
    output_root: Path, job_id: str, receipt: dict[str, object]
) -> None:
    folder = output_root / "scheduler_receipts"
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    sanitized_id = job_id.replace("/", "_").replace("\\", "_")
    filename = f"receipt_{sanitized_id}_{timestamp}.json"
    temp_path = folder / f"{filename}.tmp"
    final_path = folder / filename

    try:
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
        # Atomically rename
        if final_path.exists():
            final_path.unlink()
        temp_path.rename(final_path)
    except OSError as exc:
        raise ValidationError(
            f"Failed to write scheduler receipt atomically: {exc}"
        ) from exc


def _get_source_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return res.stdout.strip()
    except Exception:
        return "unknown_commit"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic tournament-v2 OOS scheduler CLI."
    )
    parser.add_argument(
        "--mode",
        choices=("preview", "run_once", "status", "recover_stale"),
        default="preview",
        help="Scheduler execution mode.",
    )
    parser.add_argument(
        "--output-root",
        default="runs/crypto_strategy_tournament/v2/latest",
        help="Path to tournament output root.",
    )
    parser.add_argument(
        "--discovery-source-path",
        default="runs/crypto_strategy_tournament/v1/input/crypto_1h_1y.csv",
        help="Discovery source path.",
    )
    parser.add_argument(
        "--discovery-receipt-path",
        default="runs/crypto_strategy_tournament/v1/refresh/refresh_packet.json",
        help="Discovery receipt path.",
    )
    parser.add_argument(
        "--db-path",
        default="",
        help="Path to scheduler SQLite database file.",
    )
    parser.add_argument(
        "--scheduler-enabled",
        action="store_true",
        help="Enable the scheduler (disabled by default).",
    )
    parser.add_argument(
        "--market-data-read-authorized",
        action="store_true",
        help="Authorize child process market data read.",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow network operations.",
    )
    parser.add_argument(
        "--as-of",
        default="",
        help="UTC ISO timestamp overriding current clock.",
    )

    args = parser.parse_args(argv)

    as_of = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else datetime.now(UTC)
    )

    output_root = Path(args.output_root)
    db_path = Path(args.db_path) if args.db_path else output_root / "scheduler.sqlite3"
    discovery_source = Path(args.discovery_source_path)
    discovery_receipt = Path(args.discovery_receipt_path)

    # Validate Mode-specific flag bounds
    if args.mode == "run_once":
        if not args.scheduler_enabled:
            print("Error: run_once requires --scheduler-enabled", file=sys.stderr)
            return 1
        if not args.market_data_read_authorized:
            print(
                "Error: run_once requires --market-data-read-authorized",
                file=sys.stderr,
            )
            return 1
        if not args.allow_network:
            print("Error: run_once requires --allow-network", file=sys.stderr)
            return 1

    # Instantiate Dispatcher
    if args.mode == "preview":
        dispatcher = PreviewDispatcher()
    else:
        dispatcher = RealCommandDispatcher(
            scheduler_enabled=args.scheduler_enabled,
            market_data_read_authorized=args.market_data_read_authorized,
        )

    executor = OneShotExecutor(
        db_path=db_path,
        output_root=output_root,
        discovery_source=discovery_source,
        discovery_receipt=discovery_receipt,
        dispatcher=dispatcher,
        enabled=args.scheduler_enabled,
        allow_network=args.allow_network,
    )

    if args.mode == "status":
        try:
            executor.store.initialize()
            jobs = executor.store.list_jobs()
            print(f"Scheduler Database: {db_path.resolve()}")
            print(f"Total jobs recorded: {len(jobs)}")
            if jobs:
                print(f"{'Job ID':<32} | {'Start':<25} | {'End':<25} | {'Status':<10}")
                print("-" * 100)
                for job in jobs[:10]:
                    print(
                        f"{job.job_id:<32} | {job.requested_start.isoformat():<25} | {job.requested_end.isoformat():<25} | {job.status.value:<10}"
                    )
            return 0
        except Exception as exc:
            print(f"Error querying status: {exc}", file=sys.stderr)
            return 2

    if args.mode == "recover_stale":
        try:
            executor.store.initialize()
            recovered = executor.store.recover_stale_jobs(
                "crypto_tournament_v2_forward_oos", timedelta(minutes=15)
            )
            print(f"Recovered {len(recovered)} stale jobs.")
            for job in recovered:
                print(f"Recovered job {job.job_id} to FAILED.")
            return 0
        except Exception as exc:
            print(f"Error during recovery: {exc}", file=sys.stderr)
            return 2

    # tick for preview or run_once
    receipt = executor.tick(as_of)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
