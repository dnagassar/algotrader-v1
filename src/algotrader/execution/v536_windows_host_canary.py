"""V5.36 bounded Windows-host read-only commissioning canary."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from threading import RLock
from typing import Protocol
import uuid

from algotrader.execution.secure_credential_provider import (
    CredentialFamily,
    CredentialProvider,
    CredentialProviderError,
    provider_from_name,
)
from algotrader.execution.v535_unattended_readonly import (
    AcceptedWindow,
    AlpacaSdkReadOnlyPaperHttpBoundary,
    ReadOnlyPaperHttpBoundary,
    RealCommandDispatcher,
    SCHEDULER_SCHEMA_VERSION,
    SchedulerJob,
    SchedulerJobStatus,
    V535CycleConfig,
    V535CycleError,
    _no_mutation_facts,
    _validate_paper_facts,
    _validated_market_dispatch,
)
from algotrader.execution.v536_canary_authorization import (
    V536AuthorizationError,
    V536CanaryAuthorization,
    load_v536_authorization,
    require_v536_arm_time,
    require_v536_execution_time,
    require_v536_install_time,
    validate_v536_runtime_binding,
)
from algotrader.execution.v536_credential_provisioning import (
    current_windows_identity,
)
from algotrader.execution.v536_windows_task import (
    V536TaskError,
    V536TaskScheduler,
    V536TaskSnapshot,
    V536TaskSpec,
    WindowsTaskSchedulerAdapter,
    build_v536_task_spec,
    render_v536_task_xml,
    validate_v536_task_snapshot,
)


V536_STATE_SCHEMA = "v5_36_canary_state_v1"
V536_ROLE_SCHEMA = "v5_36_canary_evidence_role_v1"
V536_PENDING_SCHEMA = "v5_36_canary_pending_terminal_attestation_v1"
V536_FINAL_SCHEMA = "v5_36_canary_commissioning_packet_v1"
V536_DUPLICATE_SCHEMA = "v5_36_canary_duplicate_no_op_v1"
V536_BLOCKED_SCHEMA = "v5_36_canary_blocked_v1"
V536_TASK_RECEIPT_SCHEMA = "v5_36_task_lifecycle_receipt_v1"
V536_OUTPUT_DIRECTORY = Path("runs") / "v5_36_windows_host_canary"
_ROLE_NAMES = (
    "source",
    "scheduler",
    "market_data",
    "broker",
    "readiness",
    "decision",
)
_MUTATION_FIELDS = tuple(_no_mutation_facts())
_ID_RE = re.compile(r"\A[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}\Z")
_FORBIDDEN_ENVIRONMENT_ALIASES = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
)
_FORBIDDEN_PERSISTED_TOKENS = (
    b'"api_key_id"',
    b'"api_secret_key"',
    b'"expected_account_id"',
    b"ALPACA_API_KEY",
    b"ALPACA_API_SECRET_KEY",
    b"ALPACA_SECRET_KEY",
    b"APCA_API_KEY_ID",
    b"APCA_API_SECRET_KEY",
)
_LEAK_SCAN_MAX_FILE_BYTES = 8 * 1024 * 1024
_LEAK_SCAN_MAX_TOTAL_BYTES = 64 * 1024 * 1024
_EVIDENCE_IO_LOCK = RLock()


class V536CanaryError(RuntimeError):
    """Sanitized commissioning-canary failure."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


@dataclass(frozen=True, slots=True)
class V536ClaimResult:
    admitted: bool
    owner_id: str
    invocation_id: str
    status: str


@dataclass(frozen=True, slots=True)
class V536PendingValidation:
    valid: bool
    errors: tuple[str, ...]
    packet: Mapping[str, object] | None
    roles: Mapping[str, Mapping[str, object]]


class SourceProvenanceReader(Protocol):
    def __call__(self) -> Mapping[str, object]:
        ...


class V536CanaryStateStore:
    """Durable authorization, arming, and execution single-use fencing."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def claim_install(
        self,
        authorization: V536CanaryAuthorization,
        *,
        owner_id: str,
        now: datetime,
    ) -> V536ClaimResult:
        return self._insert_initial(
            authorization,
            owner_id=owner_id,
            now=now,
            status="install_claimed",
        )

    def mark_installed(
        self,
        authorization: V536CanaryAuthorization,
        *,
        owner_id: str,
        now: datetime,
        receipt_sha256: str,
    ) -> None:
        self._transition(
            authorization,
            expected="install_claimed",
            target="installed_disabled",
            owner_column="install_owner_id",
            owner_id=owner_id,
            now=now,
            receipt_sha256=receipt_sha256,
        )

    def claim_arm(
        self,
        authorization: V536CanaryAuthorization,
        *,
        owner_id: str,
        now: datetime,
    ) -> V536ClaimResult:
        return self._claim_transition(
            authorization,
            expected="installed_disabled",
            target="arm_claimed",
            owner_column="arm_owner_id",
            owner_id=owner_id,
            now=now,
        )

    def mark_armed(
        self,
        authorization: V536CanaryAuthorization,
        *,
        owner_id: str,
        now: datetime,
        receipt_sha256: str,
    ) -> None:
        self._transition(
            authorization,
            expected="arm_claimed",
            target="armed",
            owner_column="arm_owner_id",
            owner_id=owner_id,
            now=now,
            receipt_sha256=receipt_sha256,
        )

    def claim_execution(
        self,
        authorization: V536CanaryAuthorization,
        *,
        invocation_id: str,
        now: datetime,
    ) -> V536ClaimResult:
        return self._claim_transition(
            authorization,
            expected="armed",
            target="executing",
            owner_column="execution_owner_id",
            owner_id=invocation_id,
            now=now,
            duplicate=True,
        )

    def mark_pending(
        self,
        authorization: V536CanaryAuthorization,
        *,
        invocation_id: str,
        now: datetime,
        receipt_sha256: str,
    ) -> None:
        self._transition(
            authorization,
            expected="executing",
            target="pending_terminal_attestation",
            owner_column="execution_owner_id",
            owner_id=invocation_id,
            now=now,
            receipt_sha256=receipt_sha256,
        )

    def mark_blocked(
        self,
        authorization: V536CanaryAuthorization,
        *,
        owner_id: str,
        now: datetime,
        receipt_sha256: str,
    ) -> None:
        try:
            with self._connect() as connection:
                self._initialize(connection)
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    UPDATE v536_canary_state
                    SET status = 'blocked', updated_at_utc = ?,
                        latest_receipt_sha256 = ?
                    WHERE authorization_sha256 = ?
                      AND status NOT IN ('finalized', 'blocked')
                      AND ? IN (install_owner_id, arm_owner_id, execution_owner_id)
                    """,
                    (
                        now.isoformat(),
                        receipt_sha256,
                        authorization.canonical_authorization_sha256,
                        owner_id,
                    ),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    raise V536CanaryError("canary_state_block_conflict")
                connection.commit()
        except V536CanaryError:
            raise
        except sqlite3.Error:
            raise V536CanaryError("canary_state_block_failed") from None

    def mark_disarmed(
        self,
        authorization: V536CanaryAuthorization,
        *,
        now: datetime,
    ) -> None:
        try:
            with self._connect() as connection:
                self._initialize(connection)
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    UPDATE v536_canary_state
                    SET disarmed_at_utc = ?, updated_at_utc = ?
                    WHERE authorization_sha256 = ?
                    """,
                    (
                        now.isoformat(),
                        now.isoformat(),
                        authorization.canonical_authorization_sha256,
                    ),
                )
                connection.commit()
        except sqlite3.Error:
            raise V536CanaryError("canary_disarm_state_failed") from None

    def finalize(
        self,
        authorization: V536CanaryAuthorization,
        *,
        now: datetime,
        receipt_sha256: str,
    ) -> None:
        try:
            with self._connect() as connection:
                self._initialize(connection)
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    UPDATE v536_canary_state
                    SET status = 'finalized', updated_at_utc = ?,
                        latest_receipt_sha256 = ?
                    WHERE authorization_sha256 = ?
                      AND status = 'pending_terminal_attestation'
                      AND disarmed_at_utc <> ''
                    """,
                    (
                        now.isoformat(),
                        receipt_sha256,
                        authorization.canonical_authorization_sha256,
                    ),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    raise V536CanaryError("canary_finalization_conflict")
                connection.commit()
        except V536CanaryError:
            raise
        except sqlite3.Error:
            raise V536CanaryError("canary_finalization_failed") from None

    def read(self, authorization: V536CanaryAuthorization) -> dict[str, object]:
        try:
            with self._connect() as connection:
                self._initialize(connection)
                row = connection.execute(
                    """
                    SELECT authorization_id, status, install_owner_id,
                           arm_owner_id, execution_owner_id, execution_count,
                           claimed_at_utc, updated_at_utc, disarmed_at_utc,
                           latest_receipt_sha256
                    FROM v536_canary_state WHERE authorization_sha256 = ?
                    """,
                    (authorization.canonical_authorization_sha256,),
                ).fetchone()
        except sqlite3.Error:
            raise V536CanaryError("canary_state_read_failed") from None
        if row is None:
            raise V536CanaryError("canary_state_unavailable")
        return {
            "authorization_id": row[0],
            "status": row[1],
            "install_owner_id": row[2],
            "arm_owner_id": row[3],
            "execution_owner_id": row[4],
            "execution_count": row[5],
            "claimed_at_utc": row[6],
            "updated_at_utc": row[7],
            "disarmed_at_utc": row[8],
            "latest_receipt_sha256": row[9],
        }

    def _insert_initial(
        self,
        authorization: V536CanaryAuthorization,
        *,
        owner_id: str,
        now: datetime,
        status: str,
    ) -> V536ClaimResult:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                self._initialize(connection)
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT install_owner_id, status FROM v536_canary_state
                    WHERE authorization_sha256 = ?
                    """,
                    (authorization.canonical_authorization_sha256,),
                ).fetchone()
                if row is not None:
                    connection.commit()
                    return V536ClaimResult(False, str(row[0]), owner_id, str(row[1]))
                connection.execute(
                    """
                    INSERT INTO v536_canary_state (
                        schema_version, authorization_sha256, authorization_id,
                        status, install_owner_id, arm_owner_id,
                        execution_owner_id, execution_count, claimed_at_utc,
                        updated_at_utc, disarmed_at_utc, latest_receipt_sha256
                    ) VALUES (?, ?, ?, ?, ?, '', '', 0, ?, ?, '', '')
                    """,
                    (
                        V536_STATE_SCHEMA,
                        authorization.canonical_authorization_sha256,
                        authorization.authorization_id,
                        status,
                        owner_id,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                connection.commit()
                return V536ClaimResult(True, owner_id, owner_id, status)
        except sqlite3.Error:
            raise V536CanaryError("canary_state_claim_failed") from None

    def _claim_transition(
        self,
        authorization: V536CanaryAuthorization,
        *,
        expected: str,
        target: str,
        owner_column: str,
        owner_id: str,
        now: datetime,
        duplicate: bool = False,
    ) -> V536ClaimResult:
        if owner_column not in {
            "install_owner_id",
            "arm_owner_id",
            "execution_owner_id",
        }:
            raise V536CanaryError("canary_state_owner_column_invalid")
        try:
            with self._connect() as connection:
                self._initialize(connection)
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT status, install_owner_id, arm_owner_id,
                           execution_owner_id FROM v536_canary_state
                    WHERE authorization_sha256 = ?
                    """,
                    (authorization.canonical_authorization_sha256,),
                ).fetchone()
                if row is None:
                    connection.commit()
                    return V536ClaimResult(False, "", owner_id, "unavailable")
                if str(row[0]) != expected:
                    current_owner = str(row[3] or row[2] or row[1])
                    if duplicate:
                        connection.execute(
                            """
                            INSERT INTO v536_duplicate_invocations (
                                invocation_id, authorization_sha256,
                                owner_invocation_id, observed_at_utc
                            ) VALUES (?, ?, ?, ?)
                            """,
                            (
                                owner_id,
                                authorization.canonical_authorization_sha256,
                                current_owner,
                                now.isoformat(),
                            ),
                        )
                    connection.commit()
                    return V536ClaimResult(
                        False,
                        current_owner,
                        owner_id,
                        str(row[0]),
                    )
                count_sql = ", execution_count = execution_count + 1" if duplicate else ""
                cursor = connection.execute(
                    f"""
                    UPDATE v536_canary_state
                    SET status = ?, {owner_column} = ?, updated_at_utc = ?
                        {count_sql}
                    WHERE authorization_sha256 = ? AND status = ?
                    """,
                    (
                        target,
                        owner_id,
                        now.isoformat(),
                        authorization.canonical_authorization_sha256,
                        expected,
                    ),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    raise V536CanaryError("canary_state_claim_conflict")
                connection.commit()
                return V536ClaimResult(True, owner_id, owner_id, target)
        except V536CanaryError:
            raise
        except sqlite3.Error:
            raise V536CanaryError("canary_state_claim_failed") from None

    def _transition(
        self,
        authorization: V536CanaryAuthorization,
        *,
        expected: str,
        target: str,
        owner_column: str,
        owner_id: str,
        now: datetime,
        receipt_sha256: str,
    ) -> None:
        if owner_column not in {
            "install_owner_id",
            "arm_owner_id",
            "execution_owner_id",
        }:
            raise V536CanaryError("canary_state_owner_column_invalid")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    f"""
                    UPDATE v536_canary_state
                    SET status = ?, updated_at_utc = ?, latest_receipt_sha256 = ?
                    WHERE authorization_sha256 = ? AND status = ?
                      AND {owner_column} = ?
                    """,
                    (
                        target,
                        now.isoformat(),
                        receipt_sha256,
                        authorization.canonical_authorization_sha256,
                        expected,
                        owner_id,
                    ),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    raise V536CanaryError("canary_state_transition_conflict")
                connection.commit()
        except V536CanaryError:
            raise
        except sqlite3.Error:
            raise V536CanaryError("canary_state_transition_failed") from None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS v536_canary_state (
                schema_version TEXT NOT NULL,
                authorization_sha256 TEXT PRIMARY KEY,
                authorization_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                install_owner_id TEXT NOT NULL,
                arm_owner_id TEXT NOT NULL,
                execution_owner_id TEXT NOT NULL,
                execution_count INTEGER NOT NULL,
                claimed_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL,
                disarmed_at_utc TEXT NOT NULL,
                latest_receipt_sha256 TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS v536_duplicate_invocations (
                invocation_id TEXT PRIMARY KEY,
                authorization_sha256 TEXT NOT NULL,
                owner_invocation_id TEXT NOT NULL,
                observed_at_utc TEXT NOT NULL
            )
            """
        )


def install_v536_task_disabled(
    *,
    authorization: V536CanaryAuthorization,
    scheduler: V536TaskScheduler,
    state_store: V536CanaryStateStore,
    provenance_reader: SourceProvenanceReader,
    current_identity: str,
    clock: Callable[[], datetime],
    owner_id_factory: Callable[[], str] | None = None,
) -> dict[str, object]:
    _reject_forbidden_environment()
    now = _utc_now(clock)
    require_v536_install_time(authorization, now)
    _validate_runtime(authorization, provenance_reader, current_identity)
    owner_id = _new_id(owner_id_factory)
    claim = state_store.claim_install(authorization, owner_id=owner_id, now=now)
    if not claim.admitted:
        return _duplicate_lifecycle_receipt(
            authorization,
            operation="install_disabled",
            claim=claim,
            observed_at=now,
        )
    spec = build_v536_task_spec(authorization)
    mutation_started = False
    try:
        mutation_started = True
        scheduler.install_disabled(spec)
        snapshot = scheduler.read(spec.task_identity)
        validate_v536_task_snapshot(snapshot, spec, phase="disabled")
        receipt = _task_lifecycle_receipt(
            authorization,
            operation="install_disabled",
            classification="task_installed_disabled",
            owner_id=owner_id,
            snapshot=snapshot,
            observed_at=_utc_now(clock),
        )
        _persist_lifecycle_receipt(authorization, receipt)
        state_store.mark_installed(
            authorization,
            owner_id=owner_id,
            now=_utc_now(clock),
            receipt_sha256=str(receipt["canonical_receipt_sha256"]),
        )
        return receipt
    except Exception as exc:
        if mutation_started:
            try:
                scheduler.disarm(spec.task_identity)
                state_store.mark_disarmed(authorization, now=_utc_now(clock))
            except Exception:
                exc = V536TaskError("task_disarm_failed")
        return _block_lifecycle(
            authorization=authorization,
            state_store=state_store,
            owner_id=owner_id,
            operation="install_disabled",
            exc=exc,
            clock=clock,
        )


def attest_v536_task_disabled(
    *,
    authorization: V536CanaryAuthorization,
    scheduler: V536TaskScheduler,
    provenance_reader: SourceProvenanceReader,
    current_identity: str,
    clock: Callable[[], datetime],
) -> dict[str, object]:
    _reject_forbidden_environment()
    _validate_runtime(authorization, provenance_reader, current_identity)
    spec = build_v536_task_spec(authorization)
    snapshot = scheduler.read(spec.task_identity)
    validate_v536_task_snapshot(snapshot, spec, phase="disabled")
    return _task_lifecycle_receipt(
        authorization,
        operation="attest_disabled",
        classification="task_disabled_attested",
        owner_id="read_only_attestation",
        snapshot=snapshot,
        observed_at=_utc_now(clock),
    )


def arm_v536_exact_window(
    *,
    authorization: V536CanaryAuthorization,
    scheduler: V536TaskScheduler,
    state_store: V536CanaryStateStore,
    credential_provider: CredentialProvider,
    provenance_reader: SourceProvenanceReader,
    current_identity: str,
    clock: Callable[[], datetime],
    owner_id_factory: Callable[[], str] | None = None,
) -> dict[str, object]:
    _reject_forbidden_environment()
    now = _utc_now(clock)
    require_v536_arm_time(authorization, now)
    _validate_runtime(authorization, provenance_reader, current_identity)
    owner_id = _new_id(owner_id_factory)
    claim = state_store.claim_arm(authorization, owner_id=owner_id, now=now)
    if not claim.admitted:
        return _duplicate_lifecycle_receipt(
            authorization,
            operation="arm_exact_window",
            claim=claim,
            observed_at=now,
        )
    spec = build_v536_task_spec(authorization)
    mutation_started = False
    try:
        snapshot = scheduler.read(spec.task_identity)
        validate_v536_task_snapshot(snapshot, spec, phase="disabled")
        credential_provider.validate(
            authorization.market_data_reference,
            expected_family=CredentialFamily.ALPACA_MARKET_DATA,
        )
        credential_provider.validate(
            authorization.paper_reference,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )
        mutation_started = True
        scheduler.arm(spec.task_identity)
        armed_snapshot = scheduler.read(spec.task_identity)
        validate_v536_task_snapshot(armed_snapshot, spec, phase="armed")
        receipt = _task_lifecycle_receipt(
            authorization,
            operation="arm_exact_window",
            classification="task_armed_exact_window",
            owner_id=owner_id,
            snapshot=armed_snapshot,
            observed_at=_utc_now(clock),
        )
        _persist_lifecycle_receipt(authorization, receipt)
        state_store.mark_armed(
            authorization,
            owner_id=owner_id,
            now=_utc_now(clock),
            receipt_sha256=str(receipt["canonical_receipt_sha256"]),
        )
        return receipt
    except Exception as exc:
        if mutation_started:
            try:
                scheduler.disarm(spec.task_identity)
                state_store.mark_disarmed(authorization, now=_utc_now(clock))
            except Exception:
                exc = V536TaskError("task_disarm_failed")
        return _block_lifecycle(
            authorization=authorization,
            state_store=state_store,
            owner_id=owner_id,
            operation="arm_exact_window",
            exc=exc,
            clock=clock,
        )


def execute_v536_canary(
    *,
    authorization: V536CanaryAuthorization,
    scheduler: V536TaskScheduler,
    state_store: V536CanaryStateStore,
    dispatcher: RealCommandDispatcher,
    credential_provider: CredentialProvider,
    paper_http_boundary: ReadOnlyPaperHttpBoundary,
    provenance_reader: SourceProvenanceReader,
    current_identity: str,
    clock: Callable[[], datetime],
    invocation_id_factory: Callable[[], str] | None = None,
) -> dict[str, object]:
    _reject_forbidden_environment()
    now = _utc_now(clock)
    require_v536_execution_time(authorization, now)
    provenance = _validate_runtime(
        authorization,
        provenance_reader,
        current_identity,
    )
    spec = build_v536_task_spec(authorization)
    config = _v535_config(authorization, spec)
    _validate_dispatcher(config, dispatcher, credential_provider)
    invocation_id = _new_id(invocation_id_factory)
    claim = state_store.claim_execution(
        authorization,
        invocation_id=invocation_id,
        now=now,
    )
    if not claim.admitted:
        receipt = _duplicate_execution_receipt(
            authorization,
            claim=claim,
            observed_at=now,
        )
        _persist_duplicate_receipt(authorization, receipt)
        return receipt

    disarm_error: Exception | None = None
    try:
        running_snapshot = scheduler.read(spec.task_identity)
        validate_v536_task_snapshot(running_snapshot, spec, phase="running")
        credential_provider.validate(
            authorization.market_data_reference,
            expected_family=CredentialFamily.ALPACA_MARKET_DATA,
        )
        credential_provider.validate(
            authorization.paper_reference,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )
        packet = _run_read_only_boundaries(
            authorization=authorization,
            config=config,
            spec=spec,
            invocation_id=invocation_id,
            running_snapshot=running_snapshot,
            provenance=provenance,
            dispatcher=dispatcher,
            credential_provider=credential_provider,
            paper_http_boundary=paper_http_boundary,
            clock=clock,
        )
    except Exception as exc:
        packet = _blocked_receipt(
            authorization,
            operation="execute",
            owner_id=invocation_id,
            classification=_safe_classification(exc),
            observed_at=_utc_now(clock),
        )
    finally:
        try:
            scheduler.disarm(spec.task_identity)
            state_store.mark_disarmed(authorization, now=_utc_now(clock))
        except Exception as exc:
            disarm_error = exc

    if disarm_error is not None:
        packet = _blocked_receipt(
            authorization,
            operation="execute",
            owner_id=invocation_id,
            classification="blocked_task_disarm_failed",
            observed_at=_utc_now(clock),
        )

    if packet.get("classification") == "canary_reads_complete_pending_terminal_attestation":
        _persist_pending_packet(authorization, packet)
        state_store.mark_pending(
            authorization,
            invocation_id=invocation_id,
            now=_utc_now(clock),
            receipt_sha256=str(packet["canonical_receipt_sha256"]),
        )
    else:
        _persist_blocked_receipt(authorization, packet)
        state_store.mark_blocked(
            authorization,
            owner_id=invocation_id,
            now=_utc_now(clock),
            receipt_sha256=str(packet["canonical_receipt_sha256"]),
        )
    return packet


def disarm_v536_task(
    *,
    authorization: V536CanaryAuthorization,
    scheduler: V536TaskScheduler,
    state_store: V536CanaryStateStore,
    clock: Callable[[], datetime],
) -> dict[str, object]:
    _reject_forbidden_environment()
    spec = build_v536_task_spec(authorization)
    scheduler.disarm(spec.task_identity)
    state_store.mark_disarmed(authorization, now=_utc_now(clock))
    snapshot = scheduler.read(spec.task_identity)
    validate_v536_task_snapshot(snapshot, spec, phase="disabled")
    return _task_lifecycle_receipt(
        authorization,
        operation="disarm",
        classification="task_disarmed",
        owner_id="credential_free_disarm",
        snapshot=snapshot,
        observed_at=_utc_now(clock),
    )


def post_run_attest_v536_canary(
    *,
    authorization: V536CanaryAuthorization,
    scheduler: V536TaskScheduler,
    state_store: V536CanaryStateStore,
    provenance_reader: SourceProvenanceReader,
    current_identity: str,
    clock: Callable[[], datetime],
) -> dict[str, object]:
    _reject_forbidden_environment()
    now = _utc_now(clock)
    state = state_store.read(authorization)
    if state.get("status") != "pending_terminal_attestation":
        raise V536CanaryError("canary_pending_state_missing")
    if state.get("execution_count") != 1:
        raise V536CanaryError("canary_execution_count_mismatch")
    owner_id = state.get("execution_owner_id")
    if not isinstance(owner_id, str) or not owner_id:
        raise V536CanaryError("canary_execution_owner_missing")
    try:
        provenance = _validate_runtime(
            authorization,
            provenance_reader,
            current_identity,
        )
        spec = build_v536_task_spec(authorization)
        snapshot = scheduler.read(spec.task_identity)
        validate_v536_task_snapshot(snapshot, spec, phase="post_run")
        pending_path = _pending_path(authorization)
        validation = validate_v536_pending_packet(
            pending_path,
            output_root=_output_root(authorization),
            authorization=authorization,
        )
        if not validation.valid or validation.packet is None:
            raise V536CanaryError("canary_pending_evidence_invalid")
        pending_hash = str(validation.packet["canonical_receipt_sha256"])
        if state.get("latest_receipt_sha256") != pending_hash:
            raise V536CanaryError("canary_pending_state_hash_mismatch")
    except (V536AuthorizationError, V536CanaryError, V536TaskError) as exc:
        return _block_lifecycle(
            authorization=authorization,
            state_store=state_store,
            owner_id=owner_id,
            operation="post_run_attest",
            exc=exc,
            clock=clock,
        )
    final: dict[str, object] = {
        "schema_version": V536_FINAL_SCHEMA,
        "classification": "scheduled_read_only_canary_commissioning_complete",
        **authorization.public_binding(),
        "pending_packet": {
            "path": pending_path.relative_to(_output_root(authorization)).as_posix(),
            "sha256": pending_hash,
        },
        "source_bundle_sha256": provenance["adapter_source_bundle_sha256"],
        "task_terminal_attestation": _snapshot_public(snapshot),
        "execution_count": 1,
        "task_disarmed": True,
        "second_run_possible": False,
        "credential_values_exposed": False,
        "secret_leak_scan": validation.packet["secret_leak_scan"],
        "account_flat_reconciled": True,
        "attested_at_utc": now.isoformat(),
        **_no_mutation_facts(),
    }
    final["canonical_receipt_sha256"] = _canonical_hash(final)
    path = (
        _output_root(authorization)
        / "commissioning"
        / f"commissioning_{authorization.authorization_id}.json"
    )
    _write_json_immutable(path, final)
    state_store.finalize(
        authorization,
        now=now,
        receipt_sha256=str(final["canonical_receipt_sha256"]),
    )
    return final


def validate_v536_pending_packet(
    path: Path | str,
    *,
    output_root: Path | str,
    authorization: V536CanaryAuthorization,
) -> V536PendingValidation:
    root = Path(output_root).resolve()
    errors: list[str] = []
    packet = _load_json_object(Path(path), errors, "pending_packet_unreadable")
    roles: dict[str, Mapping[str, object]] = {}
    if packet is None:
        return V536PendingValidation(False, tuple(errors), None, roles)
    expected_packet_keys = {
        "schema_version",
        "classification",
        *authorization.public_binding().keys(),
        "invocation_id",
        "production_dispatcher",
        "task_terminal_result_deferred",
        "evidence_references",
        "account_flat_reconciled",
        "credential_values_exposed",
        "secret_leak_scan",
        "completed_at_utc",
        "canonical_receipt_sha256",
        *_MUTATION_FIELDS,
    }
    if set(packet) != expected_packet_keys:
        errors.append("pending_packet_schema_malformed")
    if packet.get("schema_version") != V536_PENDING_SCHEMA:
        errors.append("pending_packet_schema_mismatch")
    if packet.get("classification") != (
        "canary_reads_complete_pending_terminal_attestation"
    ):
        errors.append("pending_packet_classification_mismatch")
    for key, value in authorization.public_binding().items():
        if packet.get(key) != value:
            errors.append(f"pending_authorization_{key}_mismatch")
    if packet.get("production_dispatcher") != "RealCommandDispatcher":
        errors.append("pending_dispatcher_mismatch")
    if packet.get("task_terminal_result_deferred") is not True:
        errors.append("pending_terminal_semantics_mismatch")
    if packet.get("account_flat_reconciled") is not True:
        errors.append("pending_account_non_flat")
    if packet.get("credential_values_exposed") is not False:
        errors.append("pending_credential_exposure")
    if packet.get("secret_leak_scan") != {
        "classification": "structural_secret_nonobservability_pass",
        "forbidden_environment_alias_count": 0,
        "forbidden_persisted_token_count": 0,
        "temporary_file_count": 0,
    }:
        errors.append("pending_secret_leak_scan_failed")
    _require_no_mutations(packet, errors, "pending")
    if packet.get("canonical_receipt_sha256") != _canonical_hash(packet):
        errors.append("pending_packet_hash_mismatch")

    references = packet.get("evidence_references")
    if not isinstance(references, Mapping) or set(references) != set(_ROLE_NAMES):
        errors.append("pending_evidence_references_malformed")
        return V536PendingValidation(False, tuple(errors), packet, roles)
    for role in _ROLE_NAMES:
        reference = references.get(role)
        if not isinstance(reference, Mapping) or set(reference) != {"path", "sha256"}:
            errors.append(f"{role}_reference_malformed")
            continue
        relative_value = reference.get("path")
        sha_value = reference.get("sha256")
        if type(relative_value) is not str or not _is_sha256(sha_value):
            errors.append(f"{role}_reference_malformed")
            continue
        role_path = (root / relative_value).resolve()
        try:
            role_path.relative_to(root)
        except ValueError:
            errors.append(f"{role}_reference_escape")
            continue
        role_receipt = _load_json_object(
            role_path,
            errors,
            f"{role}_receipt_unreadable",
        )
        if role_receipt is None:
            continue
        if role_receipt.get("canonical_receipt_sha256") != sha_value:
            errors.append(f"{role}_reference_hash_mismatch")
        if role_receipt.get("canonical_receipt_sha256") != _canonical_hash(role_receipt):
            errors.append(f"{role}_self_hash_mismatch")
        if role_receipt.get("schema_version") != V536_ROLE_SCHEMA:
            errors.append(f"{role}_schema_mismatch")
        if role_receipt.get("evidence_role") != role:
            errors.append(f"{role}_identity_mismatch")
        if role_receipt.get("authorization_sha256") != (
            authorization.canonical_authorization_sha256
        ):
            errors.append(f"{role}_authorization_mismatch")
        if role_receipt.get("invocation_id") != packet.get("invocation_id"):
            errors.append(f"{role}_invocation_mismatch")
        roles[role] = role_receipt
    if set(roles) == set(_ROLE_NAMES):
        _validate_role_cross_hashes(roles, errors)
        _validate_role_semantics(roles, authorization, errors)
    return V536PendingValidation(not errors, tuple(dict.fromkeys(errors)), packet, roles)


def _run_read_only_boundaries(
    *,
    authorization: V536CanaryAuthorization,
    config: V535CycleConfig,
    spec: V536TaskSpec,
    invocation_id: str,
    running_snapshot: V536TaskSnapshot,
    provenance: Mapping[str, object],
    dispatcher: RealCommandDispatcher,
    credential_provider: CredentialProvider,
    paper_http_boundary: ReadOnlyPaperHttpBoundary,
    clock: Callable[[], datetime],
) -> dict[str, object]:
    window = AcceptedWindow(
        authorization.target_window_start,
        authorization.target_window_start,
        authorization.target_window_end,
    )
    common = {
        "authorization_sha256": authorization.canonical_authorization_sha256,
        "authorization_id": authorization.authorization_id,
        "invocation_id": invocation_id,
        "scheduler_job_identity": authorization.task_identity,
        "accepted_window": window.identity,
        "window_start_bar_open": window.start_bar_open.isoformat(),
        "window_end_bar_open": window.end_bar_open.isoformat(),
        "provider_as_of_boundary": window.provider_as_of_boundary.isoformat(),
    }
    references: dict[str, dict[str, str]] = {}
    source = _role_receipt(
        "source",
        common,
        {
            "source_commit_sha": provenance["source_commit_sha"],
            "source_tree_sha": provenance["source_tree_sha"],
            "source_worktree_clean": True,
            "source_branch_or_detached": provenance["source_branch_or_detached"],
            "source_bundle_sha256": provenance["adapter_source_bundle_sha256"],
            "source_bundle_manifest": provenance["source_bundle_manifest"],
            "deployment_root": str(authorization.deployment_root),
            **_no_mutation_facts(),
        },
    )
    references["source"] = _persist_role(authorization, source)
    scheduler = _role_receipt(
        "scheduler",
        common,
        {
            **_snapshot_public(running_snapshot),
            "terminal_result_semantics": "deferred_until_post_run",
            "source_receipt_sha256": references["source"]["sha256"],
            **_no_mutation_facts(),
        },
    )
    references["scheduler"] = _persist_role(authorization, scheduler)

    job = SchedulerJob(
        schema_version=SCHEDULER_SCHEMA_VERSION,
        job_id="v536_" + hashlib.sha256(
            f"{authorization.task_identity}|{window.identity}".encode()
        ).hexdigest()[:32],
        lane="crypto_tournament_v2_forward_oos",
        source_commit=authorization.source_commit_sha,
        created_at=_utc_now(clock),
        requested_start_bar_open=window.start_bar_open,
        requested_end_bar_open=window.end_bar_open,
        provider_as_of_boundary=window.provider_as_of_boundary,
        symbols=("BTCUSD", "ETHUSD", "SOLUSD"),
        accepted_frontier_bar_open=window.start_bar_open - timedelta(hours=1),
        expected_frontier_bar_open=window.end_bar_open + timedelta(hours=1),
        status=SchedulerJobStatus.RUNNING,
        attempt_number=1,
        claim_identity=invocation_id,
        started_at=_utc_now(clock),
        updated_at=_utc_now(clock),
    )
    market_root = _output_root(authorization) / "market" / invocation_id
    dispatch_result = dispatcher.dispatch(
        job,
        market_root,
        _output_root(authorization) / "inputs" / "discovery_source.csv",
        _output_root(authorization) / "inputs" / "discovery_receipt.json",
        allow_network=True,
    )
    market_fields = _validated_market_dispatch(
        dispatch_result,
        config=config,
        accepted_window=window,
    )
    market_fields.update(
        {
            "market_data_endpoint": authorization.market_data_endpoint,
            "source_receipt_sha256": references["source"]["sha256"],
            "scheduler_receipt_sha256": references["scheduler"]["sha256"],
        }
    )
    market = _role_receipt("market_data", common, market_fields)
    references["market_data"] = _persist_role(authorization, market)

    lease = credential_provider.open(
        authorization.paper_reference,
        expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
    )

    def observe(api_key: str, api_secret: str, account: str | None):  # type: ignore[no-untyped-def]
        if account is None:
            raise V536CanaryError("expected_account_missing")
        return paper_http_boundary.observe(
            api_key_id=api_key,
            api_secret_key=api_secret,
            expected_account_id=account,
            paper_endpoint=authorization.paper_endpoint,
            clock=clock,
        )

    paper = lease.use(observe)
    _validate_paper_facts(paper)
    broker = _role_receipt(
        "broker",
        common,
        {
            "observation_classification": "read_only_paper_observation_complete",
            "observed_at": paper.observed_at.isoformat(),
            "paper_endpoint": authorization.paper_endpoint,
            "expected_account_match": paper.account_match,
            "account_active": paper.account_active,
            "account_flat_reconciled": paper.account_flat_reconciled,
            "position_count": paper.position_count,
            "open_order_count": paper.open_order_count,
            "target_asset_valid": paper.target_asset_valid,
            "read_counts": {
                "account": paper.account_read_count,
                "positions": paper.positions_read_count,
                "open_orders": paper.orders_read_count,
                "target_asset": paper.asset_read_count,
            },
            "broker_read_occurred": True,
            "source_receipt_sha256": references["source"]["sha256"],
            "scheduler_receipt_sha256": references["scheduler"]["sha256"],
            **_no_mutation_facts(),
        },
    )
    references["broker"] = _persist_role(authorization, broker)
    readiness = _role_receipt(
        "readiness",
        common,
        {
            "readiness_classification": "read_only_canary_ready",
            "blockers": [],
            "account_flat_reconciled": True,
            "source_receipt_sha256": references["source"]["sha256"],
            "scheduler_receipt_sha256": references["scheduler"]["sha256"],
            "market_data_receipt_sha256": references["market_data"]["sha256"],
            "broker_receipt_sha256": references["broker"]["sha256"],
            **_no_mutation_facts(),
        },
    )
    references["readiness"] = _persist_role(authorization, readiness)
    decision = _role_receipt(
        "decision",
        common,
        {
            "decision": "observe_only_no_action",
            "decision_classification": "canary_read_only_no_submit",
            "readiness_receipt_sha256": references["readiness"]["sha256"],
            "account_flat_reconciled": True,
            **_no_mutation_facts(),
        },
    )
    references["decision"] = _persist_role(authorization, decision)
    leak_scan = _structural_secret_leak_scan(_output_root(authorization))
    packet: dict[str, object] = {
        "schema_version": V536_PENDING_SCHEMA,
        "classification": "canary_reads_complete_pending_terminal_attestation",
        **authorization.public_binding(),
        "invocation_id": invocation_id,
        "production_dispatcher": "RealCommandDispatcher",
        "task_terminal_result_deferred": True,
        "evidence_references": references,
        "account_flat_reconciled": True,
        "credential_values_exposed": False,
        "secret_leak_scan": leak_scan,
        "completed_at_utc": _utc_now(clock).isoformat(),
        **_no_mutation_facts(),
    }
    packet["canonical_receipt_sha256"] = _canonical_hash(packet)
    return packet


def _v535_config(
    authorization: V536CanaryAuthorization,
    spec: V536TaskSpec,
) -> V535CycleConfig:
    root = _output_root(authorization)
    return V535CycleConfig(
        output_root=root,
        admission_db_path=root / "v535_admission.sqlite3",
        scheduler_job_identity=authorization.task_identity,
        expected_task_execute=spec.action_execute,
        expected_task_arguments=spec.action_arguments,
        credential_provider_name=authorization.credential_provider,
        market_data_credential_reference=authorization.market_data_reference,
        paper_credential_reference=authorization.paper_reference,
        app_profile="paper",
        paper_endpoint=authorization.paper_endpoint,
        market_data_endpoint=authorization.market_data_endpoint,
        scheduler_enabled=True,
        market_data_read_authorized=True,
        paper_broker_read_authorized=True,
        allow_network=True,
    )


def _validate_dispatcher(
    config: V535CycleConfig,
    dispatcher: RealCommandDispatcher,
    provider: CredentialProvider,
) -> None:
    if type(dispatcher) is not RealCommandDispatcher:
        raise V536CanaryError("real_command_dispatcher_required")
    if dispatcher.credential_provider is not provider:
        raise V536CanaryError("dispatcher_credential_provider_mismatch")
    if str(dispatcher.credential_reference) != str(
        config.market_data_credential_reference
    ):
        raise V536CanaryError("dispatcher_credential_reference_mismatch")
    if dispatcher.credential_provider_name != config.credential_provider_name:
        raise V536CanaryError("dispatcher_credential_provider_mismatch")
    if dispatcher.app_profile != "paper":
        raise V536CanaryError("dispatcher_profile_mismatch")
    if dispatcher.paper_endpoint != config.paper_endpoint:
        raise V536CanaryError("dispatcher_paper_endpoint_mismatch")
    if dispatcher.market_data_endpoint != config.market_data_endpoint:
        raise V536CanaryError("dispatcher_market_endpoint_mismatch")
    if not dispatcher.scheduler_enabled or not dispatcher.market_data_read_authorized:
        raise V536CanaryError("dispatcher_authorization_incomplete")


def _validate_runtime(
    authorization: V536CanaryAuthorization,
    provenance_reader: SourceProvenanceReader,
    current_identity: str,
) -> Mapping[str, object]:
    try:
        provenance = dict(provenance_reader())
        validate_v536_runtime_binding(
            authorization,
            provenance=provenance,
            current_identity=current_identity,
            deployment_root=authorization.deployment_root,
        )
        return provenance
    except V536AuthorizationError:
        raise
    except Exception:
        raise V536CanaryError("runtime_provenance_unavailable") from None


def _task_lifecycle_receipt(
    authorization: V536CanaryAuthorization,
    *,
    operation: str,
    classification: str,
    owner_id: str,
    snapshot: V536TaskSnapshot,
    observed_at: datetime,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": V536_TASK_RECEIPT_SCHEMA,
        "classification": classification,
        "operation": operation,
        "owner_id": owner_id,
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.canonical_authorization_sha256,
        "task_snapshot": _snapshot_public(snapshot),
        "credential_values_exposed": False,
        "task_scheduler_mutation_occurred": operation in {
            "install_disabled",
            "arm_exact_window",
            "disarm",
        },
        "network_access_occurred": False,
        "broker_access_occurred": False,
        "observed_at_utc": observed_at.isoformat(),
        **_no_mutation_facts(),
    }
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    return receipt


def _duplicate_lifecycle_receipt(
    authorization: V536CanaryAuthorization,
    *,
    operation: str,
    claim: V536ClaimResult,
    observed_at: datetime,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": V536_DUPLICATE_SCHEMA,
        "classification": "duplicate_lifecycle_no_op",
        "operation": operation,
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.canonical_authorization_sha256,
        "owner_id": claim.owner_id,
        "invocation_id": claim.invocation_id,
        "durable_status": claim.status,
        "credential_store_accessed": False,
        "task_mutation_occurred": False,
        "subprocess_created": False,
        "network_access_occurred": False,
        "broker_access_occurred": False,
        "observed_at_utc": observed_at.isoformat(),
        **_no_mutation_facts(),
    }
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    return receipt


def _duplicate_execution_receipt(
    authorization: V536CanaryAuthorization,
    *,
    claim: V536ClaimResult,
    observed_at: datetime,
) -> dict[str, object]:
    receipt = _duplicate_lifecycle_receipt(
        authorization,
        operation="execute",
        claim=claim,
        observed_at=observed_at,
    )
    receipt["classification"] = "duplicate_canary_execution_no_op"
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    return receipt


def _blocked_receipt(
    authorization: V536CanaryAuthorization,
    *,
    operation: str,
    owner_id: str,
    classification: str,
    observed_at: datetime,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": V536_BLOCKED_SCHEMA,
        "classification": classification,
        "operation": operation,
        "owner_id": owner_id,
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": authorization.canonical_authorization_sha256,
        "credential_values_exposed": False,
        "task_terminal_result_deferred": operation == "execute",
        "network_retry_authorized": False,
        "additional_window_authorized": False,
        "observed_at_utc": observed_at.isoformat(),
        **_no_mutation_facts(),
    }
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    return receipt


def _block_lifecycle(
    *,
    authorization: V536CanaryAuthorization,
    state_store: V536CanaryStateStore,
    owner_id: str,
    operation: str,
    exc: Exception,
    clock: Callable[[], datetime],
) -> dict[str, object]:
    now = _utc_now(clock)
    receipt = _blocked_receipt(
        authorization,
        operation=operation,
        owner_id=owner_id,
        classification=_safe_classification(exc),
        observed_at=now,
    )
    _persist_blocked_receipt(authorization, receipt)
    state_store.mark_blocked(
        authorization,
        owner_id=owner_id,
        now=now,
        receipt_sha256=str(receipt["canonical_receipt_sha256"]),
    )
    return receipt


def _role_receipt(
    role: str,
    common: Mapping[str, object],
    fields: Mapping[str, object],
) -> dict[str, object]:
    if role not in _ROLE_NAMES:
        raise V536CanaryError("canary_role_unknown")
    receipt = {
        "schema_version": V536_ROLE_SCHEMA,
        "evidence_role": role,
        **dict(common),
        **dict(fields),
    }
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    return receipt


def _persist_role(
    authorization: V536CanaryAuthorization,
    receipt: Mapping[str, object],
) -> dict[str, str]:
    role = str(receipt["evidence_role"])
    invocation_id = str(receipt["invocation_id"])
    digest = str(receipt["canonical_receipt_sha256"])
    relative = Path("evidence") / invocation_id / f"{role}_{digest}.json"
    path = _output_root(authorization) / relative
    _write_json_immutable(path, receipt)
    return {
        "path": relative.as_posix(),
        "sha256": digest,
    }


def _persist_lifecycle_receipt(
    authorization: V536CanaryAuthorization,
    receipt: Mapping[str, object],
) -> None:
    path = (
        _output_root(authorization)
        / "lifecycle"
        / f"{receipt['operation']}_{receipt['owner_id']}.json"
    )
    _write_json_immutable(path, receipt)


def _persist_duplicate_receipt(
    authorization: V536CanaryAuthorization,
    receipt: Mapping[str, object],
) -> None:
    path = (
        _output_root(authorization)
        / "duplicates"
        / f"duplicate_{receipt['invocation_id']}.json"
    )
    _write_json_immutable(path, receipt)


def _persist_blocked_receipt(
    authorization: V536CanaryAuthorization,
    receipt: Mapping[str, object],
) -> None:
    path = (
        _output_root(authorization)
        / "blocked"
        / f"blocked_{receipt['owner_id']}.json"
    )
    _write_json_immutable(path, receipt)


def _persist_pending_packet(
    authorization: V536CanaryAuthorization,
    packet: Mapping[str, object],
) -> None:
    _write_json_immutable(_pending_path(authorization), packet)


def _pending_path(authorization: V536CanaryAuthorization) -> Path:
    return (
        _output_root(authorization)
        / "pending"
        / f"pending_{authorization.authorization_id}.json"
    )


def _output_root(authorization: V536CanaryAuthorization) -> Path:
    return authorization.deployment_root / V536_OUTPUT_DIRECTORY


def _state_path(authorization: V536CanaryAuthorization) -> Path:
    return _output_root(authorization) / "canary_state.sqlite3"


def _snapshot_public(snapshot: V536TaskSnapshot) -> dict[str, object]:
    return {
        "task_identity": snapshot.task_identity,
        "principal_match": True,
        "logon_type": snapshot.logon_type,
        "run_level": snapshot.run_level,
        "task_enabled": snapshot.task_enabled,
        "trigger_enabled": snapshot.trigger_enabled,
        "trigger_start_utc": snapshot.trigger_start.isoformat(),
        "trigger_end_utc": snapshot.trigger_end.isoformat(),
        "task_state": snapshot.state,
        "action_execute": snapshot.action_execute,
        "action_arguments": snapshot.action_arguments,
        "working_directory": str(snapshot.working_directory.resolve()),
        "allow_start_on_demand": snapshot.allow_start_on_demand,
        "restart_on_failure": snapshot.restart_on_failure,
        "multiple_instances_policy": snapshot.multiple_instances_policy,
        "execution_time_limit": snapshot.execution_time_limit,
        "last_task_result": snapshot.last_task_result,
        "last_run_time": (
            None if snapshot.last_run_time is None else snapshot.last_run_time.isoformat()
        ),
        "next_run_time": (
            None if snapshot.next_run_time is None else snapshot.next_run_time.isoformat()
        ),
        "observed_at": snapshot.observed_at.isoformat(),
    }


def _validate_role_cross_hashes(
    roles: Mapping[str, Mapping[str, object]],
    errors: list[str],
) -> None:
    hashes = {
        role: str(receipt.get("canonical_receipt_sha256", ""))
        for role, receipt in roles.items()
    }
    expectations = {
        ("scheduler", "source_receipt_sha256"): "source",
        ("market_data", "source_receipt_sha256"): "source",
        ("market_data", "scheduler_receipt_sha256"): "scheduler",
        ("broker", "source_receipt_sha256"): "source",
        ("broker", "scheduler_receipt_sha256"): "scheduler",
        ("readiness", "source_receipt_sha256"): "source",
        ("readiness", "scheduler_receipt_sha256"): "scheduler",
        ("readiness", "market_data_receipt_sha256"): "market_data",
        ("readiness", "broker_receipt_sha256"): "broker",
        ("decision", "readiness_receipt_sha256"): "readiness",
    }
    for (role, field), target in expectations.items():
        if roles[role].get(field) != hashes[target]:
            errors.append(f"{role}_{field}_mismatch")


def _validate_role_semantics(
    roles: Mapping[str, Mapping[str, object]],
    authorization: V536CanaryAuthorization,
    errors: list[str],
) -> None:
    source = roles["source"]
    if source.get("source_commit_sha") != authorization.source_commit_sha:
        errors.append("source_commit_mismatch")
    if source.get("source_tree_sha") != authorization.source_tree_sha:
        errors.append("source_tree_mismatch")
    if source.get("source_worktree_clean") is not True:
        errors.append("source_not_clean")
    scheduler = roles["scheduler"]
    if scheduler.get("task_identity") != authorization.task_identity:
        errors.append("scheduler_identity_mismatch")
    if scheduler.get("task_state") != "Running":
        errors.append("scheduler_not_running")
    if scheduler.get("terminal_result_semantics") != "deferred_until_post_run":
        errors.append("scheduler_terminal_semantics_mismatch")
    market = roles["market_data"]
    if market.get("dispatch_type") != "real":
        errors.append("market_dispatch_not_real")
    if market.get("market_data_fetch_occurred") is not True:
        errors.append("market_read_missing")
    if market.get("market_data_endpoint") != authorization.market_data_endpoint:
        errors.append("market_endpoint_mismatch")
    broker = roles["broker"]
    if broker.get("paper_endpoint") != authorization.paper_endpoint:
        errors.append("paper_endpoint_mismatch")
    if broker.get("account_flat_reconciled") is not True:
        errors.append("broker_non_flat")
    if broker.get("position_count") != 0 or broker.get("open_order_count") != 0:
        errors.append("broker_non_flat")
    readiness = roles["readiness"]
    if readiness.get("blockers") != []:
        errors.append("readiness_blocked")
    decision = roles["decision"]
    if decision.get("decision") != "observe_only_no_action":
        errors.append("decision_mismatch")
    for role, receipt in roles.items():
        _require_no_mutations(receipt, errors, role)


def _require_no_mutations(
    payload: Mapping[str, object],
    errors: list[str],
    prefix: str,
) -> None:
    for field in _MUTATION_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_{field}_invalid")


def _load_json_object(
    path: Path,
    errors: list[str],
    classification: str,
) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        errors.append(classification)
        return None
    if not isinstance(payload, dict):
        errors.append(classification)
        return None
    return payload


def _write_json_immutable(path: Path, payload: Mapping[str, object]) -> None:
    from algotrader.execution.v535_unattended_readonly import (
        _write_json_immutable as v535_write_json_immutable,
    )

    with _EVIDENCE_IO_LOCK:
        try:
            v535_write_json_immutable(path, payload)
        except V535CycleError as exc:
            raise V536CanaryError(exc.classification) from None


def _canonical_hash(payload: Mapping[str, object]) -> str:
    body = {
        key: value
        for key, value in payload.items()
        if key != "canonical_receipt_sha256"
    }
    encoded = json.dumps(
        body,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _safe_classification(exc: Exception) -> str:
    classification = getattr(exc, "classification", "canary_unexpected_failure")
    if type(classification) is not str or re.fullmatch(
        r"[a-z][a-z0-9_]{0,95}",
        classification,
    ) is None:
        classification = "canary_unexpected_failure"
    return (
        classification
        if classification.startswith("blocked_")
        else f"blocked_{classification}"
    )


def _new_id(factory: Callable[[], str] | None) -> str:
    value = factory() if factory is not None else uuid.uuid4().hex
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise V536CanaryError("canary_invocation_identity_malformed")
    return value


def _utc_now(clock: Callable[[], datetime]) -> datetime:
    try:
        value = clock()
    except Exception:
        raise V536CanaryError("canary_clock_unavailable") from None
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise V536CanaryError("canary_clock_malformed")
    if value.utcoffset() != timedelta(0):
        raise V536CanaryError("canary_clock_malformed")
    return value.astimezone(UTC)


def _reject_forbidden_environment() -> None:
    if any(
        str(os.environ.get(name, "")).strip()
        for name in _FORBIDDEN_ENVIRONMENT_ALIASES
    ):
        raise V536CanaryError("credential_environment_alias_rejected")


def _structural_secret_leak_scan(root: Path) -> dict[str, object]:
    temporary_count = 0
    forbidden_count = 0
    total_bytes = 0
    with _EVIDENCE_IO_LOCK:
        try:
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                if path.name.endswith(".tmp") or path.name.startswith("."):
                    temporary_count += 1
                size = path.stat().st_size
                total_bytes += size
                if size > _LEAK_SCAN_MAX_FILE_BYTES or total_bytes > (
                    _LEAK_SCAN_MAX_TOTAL_BYTES
                ):
                    raise V536CanaryError("secret_leak_scan_scope_exceeded")
                if path.suffix.lower() not in {
                    ".json",
                    ".jsonl",
                    ".csv",
                    ".log",
                    ".txt",
                }:
                    continue
                content = path.read_bytes()
                forbidden_count += sum(
                    content.count(token) for token in _FORBIDDEN_PERSISTED_TOKENS
                )
        except V536CanaryError:
            raise
        except OSError:
            raise V536CanaryError("secret_leak_scan_failed") from None
    if temporary_count or forbidden_count:
        raise V536CanaryError("secret_persistence_detected")
    return {
        "classification": "structural_secret_nonobservability_pass",
        "forbidden_environment_alias_count": 0,
        "forbidden_persisted_token_count": 0,
        "temporary_file_count": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V5.36 bounded Windows-host read-only canary controller."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=(
            "preview",
            "install-disabled",
            "attest-disabled",
            "arm-exact-window",
            "execute",
            "disarm",
            "post-run-attest",
        ),
    )
    parser.add_argument("--authorization-artifact", required=True)
    parser.add_argument("--task-mutation-authorized", action="store_true")
    parser.add_argument("--credential-read-authorized", action="store_true")
    parser.add_argument("--execute-authorized", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode in {"install-disabled", "arm-exact-window", "disarm", "execute"}:
        if not args.task_mutation_authorized:
            return _print_blocked("task_mutation_not_authorized")
    if args.mode in {"arm-exact-window", "execute"}:
        if not args.credential_read_authorized:
            return _print_blocked("credential_read_not_authorized")
    if args.mode == "execute" and not args.execute_authorized:
        return _print_blocked("canary_execution_not_authorized")
    try:
        _reject_forbidden_environment()
        authorization = load_v536_authorization(
            Path(args.authorization_artifact)
        )
        spec = build_v536_task_spec(authorization)
        if args.mode == "preview":
            print(
                json.dumps(
                    {
                        "classification": "canary_task_preview",
                        "authorization_sha256": (
                            authorization.canonical_authorization_sha256
                        ),
                        "task_identity": spec.task_identity,
                        "trigger_start_utc": spec.trigger_start.isoformat(),
                        "trigger_end_utc": spec.trigger_end.isoformat(),
                        "task_enabled": False,
                        "trigger_enabled": False,
                        "task_xml_sha256": hashlib.sha256(
                            render_v536_task_xml(spec).encode("utf-8")
                        ).hexdigest(),
                        "credential_values_exposed": False,
                    },
                    sort_keys=True,
                )
            )
            return 0

        from algotrader.execution.crypto_read_only_paper_observation_adapter import (
            get_source_provenance,
        )

        clock = lambda: datetime.now(UTC)
        scheduler = WindowsTaskSchedulerAdapter(clock=clock)
        store = V536CanaryStateStore(_state_path(authorization))
        provenance_reader = lambda: get_source_provenance(
            authorization.deployment_root
        )
        identity = ""
        if args.mode != "disarm":
            identity = current_windows_identity()
        if args.mode == "disarm":
            result = disarm_v536_task(
                authorization=authorization,
                scheduler=scheduler,
                state_store=store,
                clock=clock,
            )
        elif args.mode == "install-disabled":
            result = install_v536_task_disabled(
                authorization=authorization,
                scheduler=scheduler,
                state_store=store,
                provenance_reader=provenance_reader,
                current_identity=identity,
                clock=clock,
            )
        elif args.mode == "attest-disabled":
            result = attest_v536_task_disabled(
                authorization=authorization,
                scheduler=scheduler,
                provenance_reader=provenance_reader,
                current_identity=identity,
                clock=clock,
            )
        elif args.mode == "arm-exact-window":
            provider = provider_from_name(authorization.credential_provider)
            result = arm_v536_exact_window(
                authorization=authorization,
                scheduler=scheduler,
                state_store=store,
                credential_provider=provider,
                provenance_reader=provenance_reader,
                current_identity=identity,
                clock=clock,
            )
        elif args.mode == "post-run-attest":
            result = post_run_attest_v536_canary(
                authorization=authorization,
                scheduler=scheduler,
                state_store=store,
                provenance_reader=provenance_reader,
                current_identity=identity,
                clock=clock,
            )
        else:
            provider = provider_from_name(authorization.credential_provider)
            dispatcher = RealCommandDispatcher(
                scheduler_enabled=True,
                market_data_read_authorized=True,
                credential_reference=authorization.market_data_reference,
                credential_provider=provider,
                credential_provider_name=authorization.credential_provider,
                app_profile="paper",
                paper_endpoint=authorization.paper_endpoint,
                market_data_endpoint=authorization.market_data_endpoint,
            )
            result = execute_v536_canary(
                authorization=authorization,
                scheduler=scheduler,
                state_store=store,
                dispatcher=dispatcher,
                credential_provider=provider,
                paper_http_boundary=AlpacaSdkReadOnlyPaperHttpBoundary(),
                provenance_reader=provenance_reader,
                current_identity=identity,
                clock=clock,
            )
    except (
        CredentialProviderError,
        V535CycleError,
        V536AuthorizationError,
        V536CanaryError,
        V536TaskError,
    ) as exc:
        return _print_blocked(_safe_classification(exc))
    except Exception:
        return _print_blocked("blocked_canary_unexpected_failure")
    summary = {
        "classification": result.get("classification"),
        "receipt_sha256": result.get("canonical_receipt_sha256"),
        "credential_values_exposed": False,
        "paper_mutation_performed": False,
        "live_authorized": False,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if not str(result.get("classification", "")).startswith("blocked_") else 2


def _print_blocked(classification: str) -> int:
    if not classification.startswith("blocked_"):
        classification = f"blocked_{classification}"
    print(json.dumps({"classification": classification}, sort_keys=True))
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "V536CanaryError",
    "V536CanaryStateStore",
    "V536PendingValidation",
    "arm_v536_exact_window",
    "attest_v536_task_disabled",
    "disarm_v536_task",
    "execute_v536_canary",
    "install_v536_task_disabled",
    "post_run_attest_v536_canary",
    "validate_v536_pending_packet",
]
