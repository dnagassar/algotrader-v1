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
import re
import sqlite3
import subprocess
import sys
from typing import Callable, Mapping, Sequence

from algotrader.errors import ValidationError
from algotrader.core.time import require_utc_datetime

WINDOWS_PROVIDER_NAME = "windows-credential-manager"
_V535_MARKET_CREDENTIAL_REFERENCE_RE = re.compile(
    r"\Awincred:algotrader/v5[.]35/alpaca-market-data/"
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z"
)

SCHEDULER_VERSION = "v5.31a_v2"
SCHEDULER_SCHEMA_VERSION = "v5_31a_scheduler_schema_v2"

_ONE_HOUR = timedelta(hours=1)


class SchedulerJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class EligibleWindow:
    start_bar_open: datetime
    end_bar_open: datetime
    provider_as_of_boundary: datetime


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
    requested_start_bar_open: datetime
    requested_end_bar_open: datetime
    provider_as_of_boundary: datetime
    symbols: tuple[str, ...]
    accepted_frontier_bar_open: datetime
    expected_frontier_bar_open: datetime
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
            "requested_start_bar_open": self.requested_start_bar_open.isoformat(),
            "requested_end_bar_open": self.requested_end_bar_open.isoformat(),
            "provider_as_of_boundary": self.provider_as_of_boundary.isoformat(),
            "symbols": list(self.symbols),
            "accepted_frontier_bar_open": self.accepted_frontier_bar_open.isoformat(),
            "expected_frontier_bar_open": self.expected_frontier_bar_open.isoformat(),
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
        accepted_frontier_bar_open: datetime,
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
            require_utc_datetime(accepted_frontier_bar_open)
        except ValidationError as exc:
            return CalculationResult(
                status="blocked",
                classification="blocked_malformed_frontier",
                reason=str(exc),
            )

        if (
            accepted_frontier_bar_open.minute != 0
            or accepted_frontier_bar_open.second != 0
            or accepted_frontier_bar_open.microsecond != 0
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

        if current_time < accepted_frontier_bar_open:
            return CalculationResult(
                status="blocked",
                classification="blocked_clock_regression",
                reason="Current time is before frontier",
            )

        if current_time == accepted_frontier_bar_open:
            return CalculationResult(
                status="no_eligible_window",
                classification="no_eligible_closed_window",
                reason="Current time equals frontier",
            )

        effective_boundary = (current_time - publication_grace).replace(
            minute=0, second=0, microsecond=0
        )
        latest_closed_bar_open = effective_boundary - bar_interval
        candidate_start_bar_open = accepted_frontier_bar_open + bar_interval

        if candidate_start_bar_open > latest_closed_bar_open:
            return CalculationResult(
                status="no_eligible_window",
                classification="no_eligible_closed_window",
                reason="No new eligible closed hours available",
            )

        requested_start_bar_open = candidate_start_bar_open
        requested_end_bar_open = min(
            latest_closed_bar_open,
            requested_start_bar_open + (max_catch_up_hours - 1) * bar_interval
        )
        provider_as_of_boundary = requested_end_bar_open + bar_interval

        return CalculationResult(
            status="eligible",
            classification="eligible_window_calculated",
            window=EligibleWindow(
                start_bar_open=requested_start_bar_open,
                end_bar_open=requested_end_bar_open,
                provider_as_of_boundary=provider_as_of_boundary,
            ),
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
                    current_ver = existing[0]
                    if current_ver == SCHEDULER_SCHEMA_VERSION:
                        self._verify_schema(connection)
                    elif current_ver == "v5_31a_scheduler_schema_v1":
                        self._migrate_v1_to_v2(connection)
                    else:
                        raise ValidationError(
                            f"Unsupported scheduler schema version: {current_ver}"
                        )
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Scheduler database initialization failed: {exc}"
            ) from exc

    def _migrate_v1_to_v2(self, connection: sqlite3.Connection) -> None:
        # Perform migration inside a transaction
        connection.execute("BEGIN IMMEDIATE")
        try:
            # Check the actual columns present in the existing scheduler_jobs table
            cursor = connection.execute("PRAGMA table_info(scheduler_jobs)")
            columns = [row["name"] for row in cursor.fetchall()]
            if not columns:
                raise ValidationError("scheduler_jobs table not found for migration")

            has_start = "requested_start" in columns or "requested_start_hour" in columns
            has_end = "requested_end" in columns or "requested_end_hour" in columns
            if not (has_start and has_end):
                raise ValidationError("Database schema does not match expected v1 schema columns")

            # Rename table
            connection.execute("ALTER TABLE scheduler_jobs RENAME TO _old_scheduler_jobs")

            # Create new schema
            self._create_schema(connection)

            # Read all rows from old table
            old_rows = connection.execute("SELECT * FROM _old_scheduler_jobs").fetchall()

            for row in old_rows:
                # Map old columns to new columns
                job_id = row["job_id"]
                lane = row["lane"]
                source_commit = row["source_commit"]
                created_at = row["created_at"]

                req_start_val = row["requested_start_hour"] if "requested_start_hour" in columns else row["requested_start"]
                req_end_val = row["requested_end_hour"] if "requested_end_hour" in columns else row["requested_end"]

                # Reconstruct provider_as_of_boundary = requested_end_bar_open + 1 hour
                dt_str = req_end_val.replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                provider_as_of = (dt + timedelta(hours=1)).isoformat()

                symbols = row["symbols"]

                frontier_val = row["accepted_frontier"] if "accepted_frontier" in columns else row["current_frontier"]
                exp_frontier_val = row["expected_frontier"] if "expected_frontier" in columns else row["expected_next_frontier"]

                status = row["status"]
                attempt_number = row["attempt_number"]
                claim_identity = row["claim_identity"]
                started_at = row["started_at"]
                completed_at = row["completed_at"]
                result_classification = row["result_classification"]
                error_classification = row["error_classification"]
                receipt_paths = row["receipt_paths"]
                receipt_hashes = row["receipt_hashes"]
                source_state_fingerprint_before = row["source_state_fingerprint_before"]
                source_state_fingerprint_after = row["source_state_fingerprint_after"]
                updated_at = row["updated_at"]

                connection.execute(
                    """
                    INSERT INTO scheduler_jobs (
                        job_id, schema_version, lane, source_commit, created_at,
                        requested_start_bar_open, requested_end_bar_open,
                        provider_as_of_boundary, symbols, accepted_frontier_bar_open,
                        expected_frontier_bar_open, status, attempt_number, claim_identity,
                        started_at, completed_at, result_classification, error_classification,
                        receipt_paths, receipt_hashes, source_state_fingerprint_before,
                        source_state_fingerprint_after, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        SCHEDULER_SCHEMA_VERSION,
                        lane,
                        source_commit,
                        created_at,
                        req_start_val,
                        req_end_val,
                        provider_as_of,
                        symbols,
                        frontier_val,
                        exp_frontier_val,
                        status,
                        attempt_number,
                        claim_identity,
                        started_at,
                        completed_at,
                        result_classification,
                        error_classification,
                        receipt_paths,
                        receipt_hashes,
                        source_state_fingerprint_before,
                        source_state_fingerprint_after,
                        updated_at,
                    )
                )

            # Drop old table
            connection.execute("DROP TABLE _old_scheduler_jobs")

            # Update metadata schema version
            connection.execute(
                "UPDATE scheduler_metadata SET value = ? WHERE key = 'schema_version'",
                (SCHEDULER_SCHEMA_VERSION,),
            )
            connection.commit()
        except Exception as exc:
            connection.execute("ROLLBACK")
            raise ValidationError(f"Migration failed: {exc}") from exc

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
                requested_start_bar_open TEXT NOT NULL,
                requested_end_bar_open TEXT NOT NULL,
                provider_as_of_boundary TEXT NOT NULL,
                symbols TEXT NOT NULL,
                accepted_frontier_bar_open TEXT NOT NULL,
                expected_frontier_bar_open TEXT NOT NULL,
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
            "requested_start_bar_open",
            "requested_end_bar_open",
            "provider_as_of_boundary",
            "symbols",
            "accepted_frontier_bar_open",
            "expected_frontier_bar_open",
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
                          AND requested_start_bar_open <= ?
                          AND requested_end_bar_open >= ?
                        """,
                        (
                            job.lane,
                            job.requested_end_bar_open.isoformat(),
                            job.requested_start_bar_open.isoformat(),
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
                            requested_start_bar_open, requested_end_bar_open,
                            provider_as_of_boundary, symbols, accepted_frontier_bar_open,
                            expected_frontier_bar_open, status, attempt_number, claim_identity,
                            started_at, completed_at, result_classification, error_classification,
                            receipt_paths, receipt_hashes, source_state_fingerprint_before,
                            source_state_fingerprint_after, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    cursor = connection.execute(
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
                        WHERE job_id = ? AND claim_identity = ? AND status = 'running'
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
                            job.claim_identity,
                        ),
                    )
                    rowcount = cursor.rowcount
                    connection.commit()
                    if rowcount == 0:
                        raise ValidationError(
                            f"Fencing conflict: Job {job.job_id} could not be updated to {job.status.value}. "
                            f"Either status was not running or claim_identity '{job.claim_identity}' did not match."
                        )
                except Exception:
                    connection.rollback()
                    raise
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Failed to update job {job.job_id}: {exc}"
            ) from exc

    def reset_failed_job(self, job_id: str) -> SchedulerJob:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    row = connection.execute(
                        "SELECT * FROM scheduler_jobs WHERE job_id = ?",
                        (job_id,),
                    ).fetchone()
                    if row is None:
                        raise ValidationError(f"Job {job_id} not found in database.")
                    job = self._row_to_job(row)
                    if job.status != SchedulerJobStatus.FAILED:
                        raise ValidationError(
                            f"Job {job_id} is in status '{job.status.value}', only '{SchedulerJobStatus.FAILED.value}' jobs can be reset."
                        )

                    now_utc = datetime.now(UTC)
                    connection.execute(
                        """
                        UPDATE scheduler_jobs
                        SET status = ?,
                            claim_identity = '',
                            started_at = '',
                            completed_at = '',
                            result_classification = '',
                            error_classification = '',
                            receipt_paths = '[]',
                            receipt_hashes = '[]',
                            source_state_fingerprint_after = '',
                            updated_at = ?
                        WHERE job_id = ?
                        """,
                        (
                            SchedulerJobStatus.PENDING.value,
                            now_utc.isoformat(),
                            job_id,
                        ),
                    )
                    connection.commit()

                    # Refetch job to return updated state
                    updated_row = connection.execute(
                        "SELECT * FROM scheduler_jobs WHERE job_id = ?",
                        (job_id,),
                    ).fetchone()
                    return self._row_to_job(updated_row)
                except Exception:
                    connection.rollback()
                    raise
        except sqlite3.Error as exc:
            raise ValidationError(
                f"Failed to reset job {job_id}: {exc}"
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
            requested_start_bar_open=datetime.fromisoformat(row["requested_start_bar_open"]),
            requested_end_bar_open=datetime.fromisoformat(row["requested_end_bar_open"]),
            provider_as_of_boundary=datetime.fromisoformat(row["provider_as_of_boundary"]),
            symbols=tuple(json.loads(row["symbols"])),
            accepted_frontier_bar_open=datetime.fromisoformat(row["accepted_frontier_bar_open"]),
            expected_frontier_bar_open=datetime.fromisoformat(
                row["expected_frontier_bar_open"]
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
            updated_at=(
                datetime.fromisoformat(row["updated_at"])
                if row["updated_at"]
                else None
            ),
        )

    def _job_sql_values(self, job: SchedulerJob) -> tuple:
        return (
            job.job_id,
            job.schema_version,
            job.lane,
            job.source_commit,
            job.created_at.isoformat(),
            job.requested_start_bar_open.isoformat(),
            job.requested_end_bar_open.isoformat(),
            job.provider_as_of_boundary.isoformat(),
            json.dumps(list(job.symbols)),
            job.accepted_frontier_bar_open.isoformat(),
            job.expected_frontier_bar_open.isoformat(),
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
            job.updated_at.isoformat() if job.updated_at else "",
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
        packet_path = output_root / "operating_packet.json"
        state_path = output_root / "frozen_state.json"
        packet_path.parent.mkdir(parents=True, exist_ok=True)

        # Write mock files so they exist if they are verified
        mock_packet = {
            "schema_version": "v5_23_crypto_tournament_v2_forward_oos_v1",
            "as_of": job.provider_as_of_boundary.isoformat(),
        }
        mock_state = {
            "schema_version": "v5_23_crypto_tournament_v2_frozen_state_v1",
            "updated_at": job.provider_as_of_boundary.isoformat(),
        }
        with packet_path.open("w", encoding="utf-8") as f:
            json.dump(mock_packet, f)
        with state_path.open("w", encoding="utf-8") as f:
            json.dump(mock_state, f)

        packet_hash = hashlib.sha256(packet_path.read_bytes()).hexdigest()
        state_hash = hashlib.sha256(state_path.read_bytes()).hexdigest()

        return {
            "status": "success",
            "classification": "preview_successful",
            "dispatch_type": "preview",
            "market_data_fetch_occurred": False,
            "network_access_attempted": False,
            "expected_receipts": [
                {
                    "path": str(packet_path.resolve()),
                    "sha256": packet_hash,
                    "type": "operating_packet",
                    "window_identity": f"{job.requested_start_bar_open.isoformat()}_{job.requested_end_bar_open.isoformat()}",
                },
                {
                    "path": str(state_path.resolve()),
                    "sha256": state_hash,
                    "type": "frozen_state",
                    "window_identity": f"{job.requested_start_bar_open.isoformat()}_{job.requested_end_bar_open.isoformat()}",
                }
            ]
        }


class RealCommandDispatcher(CommandDispatcher):
    def __init__(
        self,
        scheduler_enabled: bool,
        market_data_read_authorized: bool,
        *,
        credential_reference: object | None = None,
        credential_provider: object | None = None,
        credential_provider_name: str = WINDOWS_PROVIDER_NAME,
        app_profile: str = "paper",
        paper_endpoint: str = "https://paper-api.alpaca.markets",
        market_data_endpoint: str = "https://data.alpaca.markets",
        process_runner: Callable[..., object] | None = None,
    ) -> None:
        self.scheduler_enabled = scheduler_enabled
        self.market_data_read_authorized = market_data_read_authorized
        if credential_reference is not None and not _V535_MARKET_CREDENTIAL_REFERENCE_RE.fullmatch(
            str(credential_reference)
        ):
            raise ValidationError(
                "Real dispatch rejected: malformed market-data credential reference."
            )
        self.credential_reference = credential_reference
        self.credential_provider = credential_provider
        self.credential_provider_name = credential_provider_name
        self.app_profile = app_profile
        self.paper_endpoint = paper_endpoint
        self.market_data_endpoint = market_data_endpoint
        self.process_runner = process_runner

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

        if self.app_profile.strip().lower() != "paper":
            raise ValidationError("Real dispatch rejected: exact paper profile required.")
        if self.paper_endpoint.strip().lower().rstrip("/") != "https://paper-api.alpaca.markets":
            raise ValidationError("Real dispatch rejected: exact paper endpoint required.")
        if self.market_data_endpoint.strip().lower().rstrip("/") != "https://data.alpaca.markets":
            raise ValidationError("Real dispatch rejected: exact market-data endpoint required.")

        if str(os.environ.get("APP_PROFILE", "")).strip().lower() == "live":
            raise ValidationError(
                "Real dispatch rejected: APP_PROFILE cannot be 'live'."
            )

        credential_aliases = {
            "ALPACA_API_KEY",
            "ALPACA_API_KEY_ID",
            "ALPACA_API_SECRET_KEY",
            "ALPACA_SECRET_KEY",
            "APCA_API_KEY_ID",
            "APCA_API_SECRET_KEY",
        }
        if any(str(os.environ.get(name, "")).strip() for name in credential_aliases):
            raise ValidationError(
                "Real dispatch rejected: credential environment aliases are forbidden."
            )

        for k, v in os.environ.items():
            if "alpaca.markets" in v.lower():
                hostname = _extract_hostname(v)
                if hostname == "api.alpaca.markets":
                    raise ValidationError(f"Real dispatch rejected: Live Alpaca endpoint found in environment variable {k}.")

        if self.credential_reference is None:
            raise ValidationError(
                "Real dispatch rejected: secure credential reference required."
            )
        try:
            provider = self.credential_provider
            if provider is None or not callable(getattr(provider, "validate", None)):
                raise ValidationError(
                    "Real dispatch rejected: secure credential provider required."
                )
            provider.validate(  # type: ignore[attr-defined]
                self.credential_reference,
                expected_family="alpaca-market-data",
            )
        except ValidationError:
            raise
        except Exception as exc:
            classification = getattr(exc, "classification", "credential_provider_failed")
            if type(classification) is not str or not re.fullmatch(
                r"[a-z][a-z0-9_]{0,63}", classification
            ):
                classification = "credential_provider_failed"
            raise ValidationError(
                f"Real dispatch rejected: {classification}."
            ) from None

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
            job.provider_as_of_boundary.isoformat(),
            "--credential-provider",
            self.credential_provider_name,
            "--credential-reference",
            str(self.credential_reference),
            "--app-profile",
            self.app_profile,
            "--paper-endpoint",
            self.paper_endpoint,
            "--market-data-endpoint",
            self.market_data_endpoint,
        ]

        # Minimal allowlisted child environment
        env = {}
        allowlist = {
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATH",
            "PATHEXT",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
        }

        excluded_prefixes = ("ALPACA_", "APCA_", "TIINGO_")
        excluded_exact = {
            "APP_PROFILE",
            "PYTHONSTARTUP",
            "PYTHONHOME",
            "PYTHONINSPECT",
            "PYTHONUSERBASE",
            "PYTHONBREAKPOINT",
            "PYTHONPYCACHEPREFIX",
        }

        for k, v in os.environ.items():
            k_upper = k.upper()
            if k_upper in allowlist:
                if not k_upper.startswith(excluded_prefixes) and k_upper not in excluded_exact:
                    env[k] = v

        try:
            run_process = self.process_runner or subprocess.run
            result = run_process(
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
                    "output_discarded": True,
                }
            # Try to parse stdout as json
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                data = {}

            packet_path = output_root / "operating_packet.json"
            state_path = output_root / "frozen_state.json"

            if not packet_path.is_file():
                return {
                    "status": "failed",
                    "classification": "missing_operating_packet",
                    "dispatch_type": "real",
                }
            if not state_path.is_file():
                return {
                    "status": "failed",
                    "classification": "missing_frozen_state",
                    "dispatch_type": "real",
                }

            packet_hash = _file_sha256(packet_path)
            state_hash = _file_sha256(state_path)

            return {
                "status": "success",
                "classification": "subprocess_completed",
                "dispatch_type": "real",
                "output": data,
                "expected_receipts": [
                    {
                        "path": str(packet_path.resolve()),
                        "sha256": packet_hash,
                        "type": "operating_packet",
                        "window_identity": f"{job.requested_start_bar_open.isoformat()}_{job.requested_end_bar_open.isoformat()}",
                    },
                    {
                        "path": str(state_path.resolve()),
                        "sha256": state_hash,
                        "type": "frozen_state",
                        "window_identity": f"{job.requested_start_bar_open.isoformat()}_{job.requested_end_bar_open.isoformat()}",
                    }
                ]
            }
        except Exception as exc:
            return {
                "status": "failed",
                "classification": "subprocess_exception",
                "dispatch_type": "real",
                "error_type": exc.__class__.__name__,
                "output_discarded": True,
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
                start=None,
                end=None,
                provider_as_of=None,
                expected_frontier=None,
                classification="quarantined_corrupt_store",
                reason=f"Database corruption: {exc}",
                duration=0.0,
            )

        lane = "crypto_tournament_v2_forward_oos"
        symbols = ("BTCUSD", "ETHUSD", "SOLUSD")

        # Query the store for unresolved jobs belonging to this scheduler lane
        all_jobs = self.store.list_jobs(lane)
        unresolved_jobs = [
            j for j in all_jobs
            if j.status in (
                SchedulerJobStatus.PENDING,
                SchedulerJobStatus.RUNNING,
                SchedulerJobStatus.FAILED,
                SchedulerJobStatus.BLOCKED,
            )
        ]

        if len(unresolved_jobs) > 1:
            return self._write_noop_receipt(
                job_id="na",
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=current_time,
                start=None,
                end=None,
                provider_as_of=None,
                expected_frontier=None,
                classification="blocked_ambiguous_unresolved_jobs",
                reason=f"Ambiguous state: {len(unresolved_jobs)} unresolved jobs exist.",
                duration=(datetime.now(UTC) - start_time).total_seconds(),
            )

        elif len(unresolved_jobs) == 1:
            active_job = unresolved_jobs[0]
            if active_job.status == SchedulerJobStatus.PENDING:
                # A disabled scheduler must never claim, dispatch, or mutate;
                # the fresh-window path enforces this inside ScheduleCalculator,
                # and adoption must hold the same gate.
                if not self.enabled:
                    return self._write_noop_receipt(
                        job_id=active_job.job_id,
                        status=SchedulerJobStatus.BLOCKED,
                        mode="status",
                        frontier=active_job.accepted_frontier_bar_open,
                        start=active_job.requested_start_bar_open,
                        end=active_job.requested_end_bar_open,
                        provider_as_of=active_job.provider_as_of_boundary,
                        expected_frontier=active_job.accepted_frontier_bar_open,
                        classification="blocked_scheduler_disabled",
                        reason="Scheduler is disabled; persisted pending job was not claimed.",
                        duration=(datetime.now(UTC) - start_time).total_seconds(),
                    )

                # Adopt the persisted recovery job verbatim
                job = active_job
                job_id = job.job_id
                window = EligibleWindow(
                    start_bar_open=job.requested_start_bar_open,
                    end_bar_open=job.requested_end_bar_open,
                    provider_as_of_boundary=job.provider_as_of_boundary,
                )
                accepted_frontier_bar_open = job.accepted_frontier_bar_open

                # Validate stored fields using existing alignment and UTC rules
                try:
                    _validate_stored_job_fields(job)
                except ValidationError as exc:
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="malformed_persisted_job",
                        reason=f"Stored job validation failed: {exc}",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )
            elif active_job.status in (SchedulerJobStatus.FAILED, SchedulerJobStatus.BLOCKED):
                return self._write_noop_receipt(
                    job_id=active_job.job_id,
                    status=active_job.status,
                    mode="status",
                    frontier=active_job.accepted_frontier_bar_open,
                    start=active_job.requested_start_bar_open,
                    end=active_job.requested_end_bar_open,
                    provider_as_of=active_job.provider_as_of_boundary,
                    expected_frontier=active_job.accepted_frontier_bar_open,
                    classification="no_automatic_retry",
                    reason=f"Prior job was in {active_job.status.value} state. Retries disabled.",
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                )
            elif active_job.status == SchedulerJobStatus.RUNNING:
                stale_limit = timedelta(minutes=15)
                if (
                    active_job.updated_at
                    and datetime.now(UTC) - active_job.updated_at > stale_limit
                ):
                    # Recover stale job
                    self.store.recover_stale_jobs(lane, stale_limit)
                    return self._write_noop_receipt(
                        job_id=active_job.job_id,
                        status=SchedulerJobStatus.FAILED,
                        mode="status",
                        frontier=active_job.accepted_frontier_bar_open,
                        start=active_job.requested_start_bar_open,
                        end=active_job.requested_end_bar_open,
                        provider_as_of=active_job.provider_as_of_boundary,
                        expected_frontier=active_job.accepted_frontier_bar_open,
                        classification="stale_timeout_recovered",
                        reason="Crashed/stale running job detected and recovered to FAILED.",
                        duration=(datetime.now(UTC) - start_time).total_seconds(),
                    )
                else:
                    return self._write_noop_receipt(
                        job_id=active_job.job_id,
                        status=SchedulerJobStatus.BLOCKED,
                        mode="status",
                        frontier=active_job.accepted_frontier_bar_open,
                        start=active_job.requested_start_bar_open,
                        end=active_job.requested_end_bar_open,
                        provider_as_of=active_job.provider_as_of_boundary,
                        expected_frontier=active_job.accepted_frontier_bar_open,
                        classification="blocked_concurrent_run",
                        reason="Job is currently running under a valid lease.",
                        duration=(datetime.now(UTC) - start_time).total_seconds(),
                    )

        else:
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
                        start=None,
                        end=None,
                        provider_as_of=None,
                        expected_frontier=None,
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
                        start=None,
                        end=None,
                        provider_as_of=None,
                        expected_frontier=None,
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
                    start=None,
                    end=None,
                    provider_as_of=None,
                    expected_frontier=None,
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
                    start=None,
                    end=None,
                    provider_as_of=None,
                    expected_frontier=None,
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
                        start=None,
                        end=None,
                        provider_as_of=None,
                        expected_frontier=None,
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
                        start=None,
                        end=None,
                        provider_as_of=None,
                        expected_frontier=None,
                        classification="no_eligible_closed_window",
                        reason="No next refresh hour requested by OOS status",
                        duration=0.0,
                    )

            requested_start = datetime.fromisoformat(
                requested_start_str.replace("Z", "+00:00")
            )
            accepted_frontier_bar_open = requested_start - _ONE_HOUR

            # 3. Calculate Eligible Window using ScheduleCalculator
            calc = ScheduleCalculator.calculate_eligible_window(
                current_time=current_time,
                accepted_frontier_bar_open=accepted_frontier_bar_open,
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
                    frontier=accepted_frontier_bar_open,
                    start=None,
                    end=None,
                    provider_as_of=None,
                    expected_frontier=None,
                    classification=calc.classification,
                    reason=calc.reason,
                    duration=0.0,
                )

            if calc.status == "no_eligible_window":
                return self._write_noop_receipt(
                    job_id="na",
                    status=SchedulerJobStatus.BLOCKED,
                    mode="status",
                    frontier=accepted_frontier_bar_open,
                    start=None,
                    end=None,
                    provider_as_of=None,
                    expected_frontier=None,
                    classification=calc.classification,
                    reason=calc.reason,
                    duration=0.0,
                )

            assert calc.window is not None
            window = calc.window

            # 4. Deterministic Job ID for same lane/window
            job_id = _generate_job_id(lane, window.start_bar_open, window.end_bar_open)

            # 5. Check if Job exists in store
            existing_job = self.store.get_job(job_id)
            source_state_before = _file_sha256(self.output_root / "frozen_state.json")

            job = None
            if existing_job:
                if existing_job.status == SchedulerJobStatus.COMPLETED:
                    return self._write_noop_receipt(
                        job_id=job_id,
                        status=SchedulerJobStatus.COMPLETED,
                        mode="status",
                        frontier=accepted_frontier_bar_open,
                        start=window.start_bar_open,
                        end=window.end_bar_open,
                        provider_as_of=window.provider_as_of_boundary,
                        expected_frontier=window.end_bar_open + _ONE_HOUR,
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
                            frontier=accepted_frontier_bar_open,
                            start=window.start_bar_open,
                            end=window.end_bar_open,
                            provider_as_of=window.provider_as_of_boundary,
                            expected_frontier=accepted_frontier_bar_open,
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
                            frontier=accepted_frontier_bar_open,
                            start=window.start_bar_open,
                            end=window.end_bar_open,
                            provider_as_of=window.provider_as_of_boundary,
                            expected_frontier=accepted_frontier_bar_open,
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
                        frontier=accepted_frontier_bar_open,
                        start=window.start_bar_open,
                        end=window.end_bar_open,
                        provider_as_of=window.provider_as_of_boundary,
                        expected_frontier=accepted_frontier_bar_open,
                        classification="no_automatic_retry",
                        reason=f"Prior job was in {existing_job.status} state. Retries disabled.",
                        duration=(datetime.now(UTC) - start_time).total_seconds(),
                    )
                elif existing_job.status == SchedulerJobStatus.PENDING:
                    job = existing_job

            if job is None:
                # 6. Create Pending Job
                commit_hash = _get_source_commit()
                job = SchedulerJob(
                    schema_version=SCHEDULER_SCHEMA_VERSION,
                    job_id=job_id,
                    lane=lane,
                    source_commit=commit_hash,
                    created_at=datetime.now(UTC),
                    requested_start_bar_open=window.start_bar_open,
                    requested_end_bar_open=window.end_bar_open,
                    provider_as_of_boundary=window.provider_as_of_boundary,
                    symbols=symbols,
                    accepted_frontier_bar_open=accepted_frontier_bar_open,
                    expected_frontier_bar_open=window.end_bar_open + _ONE_HOUR,
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
                        frontier=accepted_frontier_bar_open,
                        start=window.start_bar_open,
                        end=window.end_bar_open,
                        provider_as_of=window.provider_as_of_boundary,
                        expected_frontier=accepted_frontier_bar_open,
                        classification="blocked_concurrent_overlap",
                        reason=str(exc),
                        duration=(datetime.now(UTC) - start_time).total_seconds(),
                    )

        # 7. Claim Job Atomically
        import uuid
        claim_identity = f"run_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(UTC)
        claimed = self.store.claim_job(job_id, claim_identity, started_at)

        if not claimed:
            return self._write_noop_receipt(
                job_id=job_id,
                status=SchedulerJobStatus.BLOCKED,
                mode="status",
                frontier=accepted_frontier_bar_open,
                start=window.start_bar_open,
                end=window.end_bar_open,
                provider_as_of=window.provider_as_of_boundary,
                expected_frontier=accepted_frontier_bar_open,
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

        # 9. Verify Expected Receipts
        if dispatch_result.get("status") == "success":
            expected_receipts = dispatch_result.get("expected_receipts")
            if not expected_receipts:
                # If no expected receipts are provided in success, fail closed
                return self._fail_job_and_write_receipt(
                    job=job,
                    classification="missing_receipt_manifest",
                    reason="Dispatcher did not return an explicit expected receipt manifest.",
                    start_time=start_time,
                    accepted_frontier_bar_open=accepted_frontier_bar_open,
                    window=window,
                )

            validated_paths = []
            validated_hashes = []

            for item in expected_receipts:
                r_path_str = item.get("path")
                r_hash = item.get("sha256")
                r_type = item.get("type")
                r_window_id = item.get("window_identity")

                if not r_path_str or not r_hash or not r_type or not r_window_id:
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="malformed_receipt_manifest",
                        reason="Expected receipt manifest entry is missing required fields.",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )

                r_path = Path(r_path_str)
                if not r_path.is_file():
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="missing_receipt_file",
                        reason=f"Expected receipt file does not exist: {r_path}",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )

                actual_hash = _file_sha256(r_path)
                if actual_hash != r_hash:
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="receipt_hash_mismatch",
                        reason=f"Receipt hash mismatch for {r_path.name}. Expected {r_hash}, got {actual_hash}",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )

                try:
                    content = json.loads(r_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="unparseable_receipt_file",
                        reason=f"Failed to parse receipt file as JSON: {exc}",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )

                # Validate expected receipt type is allowlisted
                if r_type not in ("operating_packet", "frozen_state"):
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="unknown_receipt_type",
                        reason=f"Unrecognized receipt type '{r_type}' is not permitted.",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )

                # Infer actual type of the receipt file from content
                if "as_of" in content:
                    actual_type = "operating_packet"
                elif "updated_at" in content:
                    actual_type = "frozen_state"
                else:
                    actual_type = "unknown"

                if actual_type != r_type:
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="receipt_type_mismatch",
                        reason=f"Receipt type mismatch for {r_path.name}. Expected '{r_type}', got '{actual_type}'",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )

                if r_type == "operating_packet":
                    as_of_str = content.get("as_of")
                    if not as_of_str:
                        return self._fail_job_and_write_receipt(
                            job=job,
                            classification="receipt_binding_mismatch",
                            reason="operating_packet lacks 'as_of' binding field.",
                            start_time=start_time,
                            accepted_frontier_bar_open=accepted_frontier_bar_open,
                            window=window,
                        )
                    try:
                        as_of_dt = datetime.fromisoformat(as_of_str.replace("Z", "+00:00"))
                        job_as_of_dt = job.provider_as_of_boundary
                        if abs((as_of_dt - job_as_of_dt).total_seconds()) > 1.0:
                            return self._fail_job_and_write_receipt(
                                job=job,
                                classification="receipt_binding_mismatch",
                                reason=f"operating_packet 'as_of' ({as_of_str}) does not match job provider_as_of_boundary ({job.provider_as_of_boundary.isoformat()}).",
                                start_time=start_time,
                                accepted_frontier_bar_open=accepted_frontier_bar_open,
                                window=window,
                            )
                    except Exception as exc:
                        return self._fail_job_and_write_receipt(
                            job=job,
                            classification="receipt_binding_mismatch",
                            reason=f"Failed to parse 'as_of' in operating_packet: {exc}",
                            start_time=start_time,
                            accepted_frontier_bar_open=accepted_frontier_bar_open,
                            window=window,
                        )

                elif r_type == "frozen_state":
                    updated_at_str = content.get("updated_at")
                    if not updated_at_str:
                        return self._fail_job_and_write_receipt(
                            job=job,
                            classification="receipt_binding_mismatch",
                            reason="frozen_state lacks 'updated_at' binding field.",
                            start_time=start_time,
                            accepted_frontier_bar_open=accepted_frontier_bar_open,
                            window=window,
                        )
                    try:
                        updated_at_dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                        job_as_of_dt = job.provider_as_of_boundary
                        if abs((updated_at_dt - job_as_of_dt).total_seconds()) > 1.0:
                            return self._fail_job_and_write_receipt(
                                job=job,
                                classification="receipt_binding_mismatch",
                                reason=f"frozen_state 'updated_at' ({updated_at_str}) does not match job provider_as_of_boundary ({job.provider_as_of_boundary.isoformat()}).",
                                start_time=start_time,
                                accepted_frontier_bar_open=accepted_frontier_bar_open,
                                window=window,
                            )
                    except Exception as exc:
                        return self._fail_job_and_write_receipt(
                            job=job,
                            classification="receipt_binding_mismatch",
                            reason=f"Failed to parse 'updated_at' in frozen_state: {exc}",
                            start_time=start_time,
                            accepted_frontier_bar_open=accepted_frontier_bar_open,
                            window=window,
                        )

                expected_window_id = f"{job.requested_start_bar_open.isoformat()}_{job.requested_end_bar_open.isoformat()}"
                if r_window_id != expected_window_id:
                    return self._fail_job_and_write_receipt(
                        job=job,
                        classification="receipt_window_mismatch",
                        reason=f"Receipt window identity mismatch. Expected {expected_window_id}, got {r_window_id}",
                        start_time=start_time,
                        accepted_frontier_bar_open=accepted_frontier_bar_open,
                        window=window,
                    )

                validated_paths.append(str(r_path.name))
                validated_hashes.append(r_hash)

            try:
                final_job = replace(
                    job,
                    status=SchedulerJobStatus.COMPLETED,
                    completed_at=now_utc,
                    result_classification=dispatch_result.get(
                        "classification", "success"
                    ),
                    receipt_paths=tuple(validated_paths),
                    receipt_hashes=tuple(validated_hashes),
                    source_state_fingerprint_after=source_state_after,
                )
                self.store.update_job(final_job)
                return self._write_receipt_file(
                    job=final_job,
                    mode="run_once",
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                    reason="Subprocess accrual executed successfully.",
                )
            except ValidationError as exc:
                return self._write_noop_receipt(
                    job_id=job_id,
                    status=SchedulerJobStatus.FAILED,
                    mode="run_once",
                    frontier=accepted_frontier_bar_open,
                    start=window.start_bar_open,
                    end=window.end_bar_open,
                    provider_as_of=window.provider_as_of_boundary,
                    expected_frontier=accepted_frontier_bar_open,
                    classification="fencing_conflict",
                    reason=str(exc),
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                )
        else:
            try:
                final_job = replace(
                    job,
                    status=SchedulerJobStatus.FAILED,
                    completed_at=now_utc,
                    error_classification=dispatch_result.get(
                        "classification", "subprocess_failed"
                    ),
                    receipt_paths=(),
                    receipt_hashes=(),
                    source_state_fingerprint_after=source_state_after,
                )
                self.store.update_job(final_job)
                return self._write_receipt_file(
                    job=final_job,
                    mode="run_once",
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                    reason=dispatch_result.get("reason", "Subprocess execution failed."),
                )
            except ValidationError as exc:
                return self._write_noop_receipt(
                    job_id=job_id,
                    status=SchedulerJobStatus.FAILED,
                    mode="run_once",
                    frontier=accepted_frontier_bar_open,
                    start=window.start_bar_open,
                    end=window.end_bar_open,
                    provider_as_of=window.provider_as_of_boundary,
                    expected_frontier=accepted_frontier_bar_open,
                    classification="fencing_conflict",
                    reason=str(exc),
                    duration=(datetime.now(UTC) - start_time).total_seconds(),
                )

    def reset_failed(self, job_id: str, authorized: bool) -> dict[str, object]:
        if not authorized:
            raise ValidationError("Reset failed rejected: Reset was not authorized.")
        if not job_id:
            raise ValidationError("Reset failed requires a valid job_id.")

        self.store.initialize()
        job = self.store.get_job(job_id)
        if not job:
            raise ValidationError(f"Job {job_id} not found.")

        if job.status != SchedulerJobStatus.FAILED:
            raise ValidationError(f"Job {job_id} is not in FAILED state (current: {job.status.value}).")

        updated_job = self.store.reset_failed_job(job_id)

        # Write audit receipt
        receipt = self._write_receipt_file(
            job=updated_job,
            mode="reset_failed",
            duration=0.0,
            reason="Operator explicitly reset failed job.",
        )
        return receipt

    def _write_noop_receipt(
        self,
        job_id: str,
        status: SchedulerJobStatus,
        mode: str,
        frontier: datetime,
        start: datetime | None,
        end: datetime | None,
        provider_as_of: datetime | None,
        expected_frontier: datetime | None,
        classification: str,
        reason: str,
        duration: float,
        publication_grace_seconds: float = 300.0,
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
            "clock_time_utc": now_utc.isoformat(),
            "publication_grace_seconds": publication_grace_seconds,
            "accepted_frontier_bar_open": frontier.isoformat(),
            "requested_start_bar_open": start.isoformat() if start else None,
            "requested_end_bar_open": end.isoformat() if end else None,
            "provider_as_of_boundary": provider_as_of.isoformat() if provider_as_of else None,
            "expected_frontier_bar_open": expected_frontier.isoformat() if expected_frontier else None,
            "next_eligible_scheduler_time": next_check.isoformat(),
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
        publication_grace_seconds: float = 300.0,
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
            "clock_time_utc": now_utc.isoformat(),
            "publication_grace_seconds": publication_grace_seconds,
            "accepted_frontier_bar_open": job.accepted_frontier_bar_open.isoformat(),
            "requested_start_bar_open": job.requested_start_bar_open.isoformat(),
            "requested_end_bar_open": job.requested_end_bar_open.isoformat(),
            "provider_as_of_boundary": job.provider_as_of_boundary.isoformat(),
            "expected_frontier_bar_open": job.expected_frontier_bar_open.isoformat(),
            "next_eligible_scheduler_time": next_check.isoformat(),
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
            "operator_action_required": (job.status == SchedulerJobStatus.FAILED),
            "exact_reason": reason,
        }
        _write_receipt_file_atomic(self.output_root, job.job_id, receipt)
        return receipt

    def _fail_job_and_write_receipt(
        self,
        job: SchedulerJob,
        classification: str,
        reason: str,
        start_time: datetime,
        accepted_frontier_bar_open: datetime,
        window: EligibleWindow,
    ) -> dict[str, object]:
        now_utc = datetime.now(UTC)
        source_state_after = _file_sha256(self.output_root / "frozen_state.json")
        try:
            final_job = replace(
                job,
                status=SchedulerJobStatus.FAILED,
                completed_at=now_utc,
                error_classification=classification,
                receipt_paths=(),
                receipt_hashes=(),
                source_state_fingerprint_after=source_state_after,
            )
            self.store.update_job(final_job)
            return self._write_receipt_file(
                job=final_job,
                mode="run_once",
                duration=(datetime.now(UTC) - start_time).total_seconds(),
                reason=reason,
            )
        except ValidationError as exc:
            return self._write_noop_receipt(
                job_id=job.job_id,
                status=SchedulerJobStatus.FAILED,
                mode="run_once",
                frontier=accepted_frontier_bar_open,
                start=window.start_bar_open,
                end=window.end_bar_open,
                provider_as_of=window.provider_as_of_boundary,
                expected_frontier=accepted_frontier_bar_open,
                classification="fencing_conflict",
                reason=str(exc),
                duration=(datetime.now(UTC) - start_time).total_seconds(),
            )
def _extract_hostname(url: str) -> str:
    temp = url.strip().lower()
    if "://" in temp:
        temp = temp.split("://", 1)[1]
    cut_idx = len(temp)
    for char in ("/", "?", "#"):
        idx = temp.find(char)
        if idx != -1 and idx < cut_idx:
            cut_idx = idx
    temp = temp[:cut_idx]
    if "@" in temp:
        temp = temp.rsplit("@", 1)[1]
    if ":" in temp:
        temp = temp.split(":", 1)[0]
    if temp.endswith("."):
        temp = temp[:-1]
    return temp


def _validate_stored_job_fields(job: SchedulerJob) -> None:
    require_utc_datetime(job.requested_start_bar_open)
    require_utc_datetime(job.requested_end_bar_open)
    require_utc_datetime(job.provider_as_of_boundary)
    require_utc_datetime(job.accepted_frontier_bar_open)
    require_utc_datetime(job.expected_frontier_bar_open)

    for dt in (
        job.requested_start_bar_open,
        job.requested_end_bar_open,
        job.provider_as_of_boundary,
        job.accepted_frontier_bar_open,
        job.expected_frontier_bar_open,
    ):
        if dt.minute != 0 or dt.second != 0 or dt.microsecond != 0:
            raise ValidationError(
                f"Stored job datetime is not aligned to the hour: {dt.isoformat()}"
            )

    if job.requested_start_bar_open > job.requested_end_bar_open:
        raise ValidationError(
            f"Stored job requested_start_bar_open ({job.requested_start_bar_open.isoformat()}) "
            f"cannot be after requested_end_bar_open ({job.requested_end_bar_open.isoformat()})"
        )


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
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, final_path)
        try:
            parent_fd = os.open(str(folder), os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except (AttributeError, OSError):
            pass
    except OSError as exc:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise ValidationError(
            f"Failed to write scheduler receipt atomically: {exc}"
        ) from exc


_CACHED_SOURCE_COMMIT: str | None = None


def _get_source_commit() -> str:
    global _CACHED_SOURCE_COMMIT
    if _CACHED_SOURCE_COMMIT is None:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            _CACHED_SOURCE_COMMIT = res.stdout.strip()
        except Exception:
            _CACHED_SOURCE_COMMIT = "unknown_commit"
    return _CACHED_SOURCE_COMMIT


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic tournament-v2 OOS scheduler CLI."
    )
    parser.add_argument(
        "--mode",
        choices=("preview", "run_once", "status", "recover_stale", "reset_failed"),
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
    parser.add_argument(
        "--job-id",
        default="",
        help="Job ID to reset (used in reset_failed mode).",
    )
    parser.add_argument(
        "--reset-authorized",
        action="store_true",
        help="Authorize resetting a failed job (used in reset_failed mode).",
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
    elif args.mode == "reset_failed":
        if not args.job_id:
            print("Error: reset_failed requires --job-id", file=sys.stderr)
            return 1
        if not args.reset_authorized:
            print("Error: reset_failed requires --reset-authorized", file=sys.stderr)
            return 1

    # Instantiate Dispatcher
    if args.mode == "run_once":
        dispatcher = RealCommandDispatcher(
            scheduler_enabled=args.scheduler_enabled,
            market_data_read_authorized=args.market_data_read_authorized,
        )
    else:
        dispatcher = PreviewDispatcher()

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
                print(f"{'Job ID':<32} | {'Start Bar Open':<25} | {'End Bar Open':<25} | {'Status':<10}")
                print("-" * 100)
                for job in jobs[:10]:
                    print(
                        f"{job.job_id:<32} | {job.requested_start_bar_open.isoformat():<25} | {job.requested_end_bar_open.isoformat():<25} | {job.status.value:<10}"
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

    if args.mode == "reset_failed":
        try:
            receipt = executor.reset_failed(args.job_id, args.reset_authorized)
            print(json.dumps(receipt, indent=2, sort_keys=True))
            return 0
        except Exception as exc:
            print(f"Error resetting job: {exc}", file=sys.stderr)
            return 2

    # tick for preview or run_once
    receipt = executor.tick(as_of)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
