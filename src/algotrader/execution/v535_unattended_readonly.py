"""V5.35 secure unattended read-only production control-flow boundary.

The boundary is default-disabled, uses durable same-window admission before
external reads, exercises ``RealCommandDispatcher`` for market data, and
exposes no broker mutation operation.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from typing import Any, Protocol
import uuid

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
from algotrader.execution.secure_credential_provider import (
    WINDOWS_PROVIDER_NAME,
    CredentialFamily,
    CredentialProvider,
    CredentialProviderError,
    CredentialReference,
    provider_from_name,
)
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    SCHEDULER_SCHEMA_VERSION,
    RealCommandDispatcher,
    SchedulerJob,
    SchedulerJobStatus,
)


V535_CYCLE_SCHEMA = "v5_35_secure_unattended_cycle_v1"
V535_ROLE_SCHEMA = "v5_35_completed_cycle_evidence_role_v1"
V535_DUPLICATE_SCHEMA = "v5_35_duplicate_window_no_op_v1"
V535_ADMISSION_SCHEMA = "v5_35_transactional_admission_v1"
V535_TASK_IDENTITY = r"\crypto-tournament-v2-oos-scheduler"
V535_TASK_EXECUTE = "powershell.exe"
V535_MARKET_REFERENCE = (
    "wincred:algotrader/v5.35/alpaca-market-data/production"
)
V535_PAPER_REFERENCE = (
    "wincred:algotrader/v5.35/alpaca-paper-observation/production"
)
V535_TASK_ARGUMENTS = (
    '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File '
    '"%REPO_ROOT%\\scripts\\run_v535_unattended_readonly.ps1" '
    "-Mode run_once -SchedulerEnabled -MarketDataReadAuthorized "
    "-PaperBrokerReadAuthorized -AllowNetwork"
)
EXPECTED_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
EXPECTED_MARKET_DATA_ENDPOINT = "https://data.alpaca.markets"
_ROLE_NAMES = (
    "source",
    "scheduler",
    "market_data",
    "broker",
    "readiness",
    "decision",
)
_MUTATION_FIELDS = (
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_submit_authorized",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_authorized",
    "live_endpoint_touched",
)


class V535CycleError(RuntimeError):
    """Sanitized fail-closed cycle error."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


@dataclass(frozen=True, slots=True)
class AcceptedWindow:
    start_bar_open: datetime
    end_bar_open: datetime
    provider_as_of_boundary: datetime

    def __post_init__(self) -> None:
        for name in (
            "start_bar_open",
            "end_bar_open",
            "provider_as_of_boundary",
        ):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise V535CycleError("accepted_window_malformed")
            normalized = value.astimezone(UTC)
            if normalized.minute or normalized.second or normalized.microsecond:
                raise V535CycleError("accepted_window_malformed")
            object.__setattr__(self, name, normalized)
        if self.start_bar_open != self.end_bar_open:
            raise V535CycleError("accepted_window_not_single_hour")
        if self.provider_as_of_boundary != self.end_bar_open + timedelta(hours=1):
            raise V535CycleError("accepted_window_boundary_mismatch")

    @property
    def identity(self) -> str:
        return (
            f"{self.start_bar_open.isoformat()}_"
            f"{self.end_bar_open.isoformat()}"
        )


@dataclass(frozen=True, slots=True)
class TaskSchedulerSnapshot:
    task_identity: str
    enabled: bool
    state: str
    action_execute: str
    action_arguments: str
    last_task_result: int
    last_run_time: datetime
    observed_at: datetime

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool or type(self.last_task_result) is not int:
            raise V535CycleError("scheduler_snapshot_malformed")
        for name in (
            "task_identity",
            "state",
            "action_execute",
            "action_arguments",
        ):
            if type(getattr(self, name)) is not str or not getattr(self, name).strip():
                raise V535CycleError("scheduler_snapshot_malformed")
        for name in ("last_run_time", "observed_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise V535CycleError("scheduler_snapshot_malformed")
            object.__setattr__(self, name, value.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class PaperObservationFacts:
    observed_at: datetime
    account_match: bool
    account_active: bool
    account_flat_reconciled: bool
    position_count: int
    open_order_count: int
    target_asset_valid: bool
    account_read_count: int
    positions_read_count: int
    orders_read_count: int
    asset_read_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None:
            raise V535CycleError("broker_observation_malformed")
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(UTC))
        for name in (
            "account_match",
            "account_active",
            "account_flat_reconciled",
            "target_asset_valid",
        ):
            if type(getattr(self, name)) is not bool:
                raise V535CycleError("broker_observation_malformed")
        for name in (
            "position_count",
            "open_order_count",
            "account_read_count",
            "positions_read_count",
            "orders_read_count",
            "asset_read_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise V535CycleError("broker_observation_malformed")


class ReadOnlyPaperHttpBoundary(Protocol):
    """The only injected paper I/O seam; it exposes reads and no mutations."""

    def observe(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        expected_account_id: str,
        paper_endpoint: str,
        clock: Callable[[], datetime],
    ) -> PaperObservationFacts:
        ...


class AlpacaSdkReadOnlyPaperHttpBoundary:
    """Private production SDK binding restricted to four bounded reads."""

    def observe(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        expected_account_id: str,
        paper_endpoint: str,
        clock: Callable[[], datetime],
    ) -> PaperObservationFacts:
        if paper_endpoint.strip().lower().rstrip("/") != EXPECTED_PAPER_ENDPOINT:
            raise V535CycleError("paper_endpoint_mismatch")
        if not expected_account_id.strip():
            raise V535CycleError("expected_account_missing")
        try:
            from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
            from algotrader.execution.crypto_read_only_paper_observation_adapter import (
                TARGET_SYMBOL,
                _validate_account,
                _validate_asset,
                _validate_orders,
                _validate_positions,
            )

            client = AlpacaSdkClient(
                AlpacaPaperConfig(
                    app_profile="paper",
                    alpaca_api_key=api_key_id,
                    alpaca_secret_key=api_secret_key,
                    alpaca_paper_base_url=EXPECTED_PAPER_ENDPOINT,
                )
            )
        except Exception:
            raise V535CycleError("paper_client_construction_failed") from None

        try:
            account = client.get_account()
        except Exception:
            raise V535CycleError("paper_account_read_failed") from None
        account_error = _validate_account(account, expected_account_id)
        if account_error is not None:
            raise V535CycleError(f"paper_account_{account_error}")

        try:
            positions = tuple(client.get_positions())
        except Exception:
            raise V535CycleError("paper_positions_read_failed") from None
        position_error = _validate_positions(positions)
        if position_error is not None:
            raise V535CycleError(f"paper_positions_{position_error}")

        try:
            orders = tuple(
                client.get_orders(
                    AlpacaRecentOrderQuery(
                        status_filter="open",
                        limit=100,
                        direction="desc",
                    )
                )
            )
        except Exception:
            raise V535CycleError("paper_orders_read_failed") from None
        orders_error = _validate_orders(orders)
        if orders_error is not None:
            raise V535CycleError(f"paper_orders_{orders_error}")

        try:
            asset = client.get_asset(TARGET_SYMBOL)
        except Exception:
            raise V535CycleError("paper_asset_read_failed") from None
        asset_error = _validate_asset(asset)
        if asset_error is not None:
            raise V535CycleError(f"paper_asset_{asset_error}")

        observed_at = _utc_now(clock)
        return PaperObservationFacts(
            observed_at=observed_at,
            account_match=True,
            account_active=True,
            account_flat_reconciled=not positions and not orders,
            position_count=len(positions),
            open_order_count=len(orders),
            target_asset_valid=True,
            account_read_count=1,
            positions_read_count=1,
            orders_read_count=1,
            asset_read_count=1,
        )


@dataclass(frozen=True, slots=True)
class V535CycleConfig:
    output_root: Path | str
    admission_db_path: Path | str
    scheduler_job_identity: str = V535_TASK_IDENTITY
    expected_task_execute: str = V535_TASK_EXECUTE
    expected_task_arguments: str = V535_TASK_ARGUMENTS
    credential_provider_name: str = WINDOWS_PROVIDER_NAME
    market_data_credential_reference: CredentialReference | str = (
        V535_MARKET_REFERENCE
    )
    paper_credential_reference: CredentialReference | str = V535_PAPER_REFERENCE
    app_profile: str = "paper"
    paper_endpoint: str = EXPECTED_PAPER_ENDPOINT
    market_data_endpoint: str = EXPECTED_MARKET_DATA_ENDPOINT
    scheduler_enabled: bool = False
    market_data_read_authorized: bool = False
    paper_broker_read_authorized: bool = False
    allow_network: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", Path(self.output_root))
        object.__setattr__(self, "admission_db_path", Path(self.admission_db_path))
        for name in (
            "scheduler_job_identity",
            "expected_task_execute",
            "expected_task_arguments",
            "credential_provider_name",
        ):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise V535CycleError("cycle_configuration_malformed")
        for name in (
            "market_data_credential_reference",
            "paper_credential_reference",
        ):
            value = getattr(self, name)
            if not isinstance(value, CredentialReference):
                value = CredentialReference(value)
                object.__setattr__(self, name, value)
        for name in (
            "scheduler_enabled",
            "market_data_read_authorized",
            "paper_broker_read_authorized",
            "allow_network",
        ):
            if type(getattr(self, name)) is not bool:
                raise V535CycleError("cycle_configuration_malformed")


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    admitted: bool
    owner_invocation_id: str
    invocation_id: str


class V535AdmissionStore:
    """Durable exact-job/window uniqueness established before external reads."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def claim(
        self,
        *,
        scheduler_job_identity: str,
        accepted_window: str,
        invocation_id: str,
        claimed_at: datetime,
    ) -> AdmissionResult:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                self._initialize(connection)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    row = connection.execute(
                        """
                        SELECT owner_invocation_id FROM v535_admissions
                        WHERE scheduler_job_identity = ? AND accepted_window = ?
                        """,
                        (scheduler_job_identity, accepted_window),
                    ).fetchone()
                    if row is None:
                        connection.execute(
                            """
                            INSERT INTO v535_admissions (
                                schema_version, scheduler_job_identity,
                                accepted_window, owner_invocation_id, status,
                                claimed_at_utc, finalized_at_utc, cycle_sha256
                            ) VALUES (?, ?, ?, ?, 'admitted', ?, '', '')
                            """,
                            (
                                V535_ADMISSION_SCHEMA,
                                scheduler_job_identity,
                                accepted_window,
                                invocation_id,
                                claimed_at.isoformat(),
                            ),
                        )
                        connection.commit()
                        return AdmissionResult(True, invocation_id, invocation_id)
                    owner = str(row[0])
                    connection.execute(
                        """
                        INSERT INTO v535_duplicate_invocations (
                            invocation_id, scheduler_job_identity,
                            accepted_window, owner_invocation_id, observed_at_utc
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            invocation_id,
                            scheduler_job_identity,
                            accepted_window,
                            owner,
                            claimed_at.isoformat(),
                        ),
                    )
                    connection.commit()
                    return AdmissionResult(False, owner, invocation_id)
                except Exception:
                    connection.rollback()
                    raise
        except sqlite3.Error:
            raise V535CycleError("transactional_admission_failed") from None

    def finalize(
        self,
        *,
        scheduler_job_identity: str,
        accepted_window: str,
        owner_invocation_id: str,
        status: str,
        cycle_sha256: str,
        finalized_at: datetime,
    ) -> None:
        if status not in {"completed", "blocked", "failed"}:
            raise V535CycleError("admission_finalization_malformed")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    UPDATE v535_admissions
                    SET status = ?, finalized_at_utc = ?, cycle_sha256 = ?
                    WHERE scheduler_job_identity = ? AND accepted_window = ?
                      AND owner_invocation_id = ? AND status = 'admitted'
                    """,
                    (
                        status,
                        finalized_at.isoformat(),
                        cycle_sha256,
                        scheduler_job_identity,
                        accepted_window,
                        owner_invocation_id,
                    ),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    raise V535CycleError("admission_finalization_conflict")
                connection.commit()
        except sqlite3.Error:
            raise V535CycleError("admission_finalization_failed") from None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS v535_admissions (
                schema_version TEXT NOT NULL,
                scheduler_job_identity TEXT NOT NULL,
                accepted_window TEXT NOT NULL,
                owner_invocation_id TEXT NOT NULL,
                status TEXT NOT NULL,
                claimed_at_utc TEXT NOT NULL,
                finalized_at_utc TEXT NOT NULL,
                cycle_sha256 TEXT NOT NULL,
                PRIMARY KEY (scheduler_job_identity, accepted_window),
                UNIQUE (owner_invocation_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS v535_duplicate_invocations (
                invocation_id TEXT PRIMARY KEY,
                scheduler_job_identity TEXT NOT NULL,
                accepted_window TEXT NOT NULL,
                owner_invocation_id TEXT NOT NULL,
                observed_at_utc TEXT NOT NULL
            )
            """
        )


def run_v535_unattended_cycle(
    *,
    config: V535CycleConfig,
    accepted_window: AcceptedWindow,
    dispatcher: RealCommandDispatcher,
    credential_provider: CredentialProvider,
    task_scheduler_reader: Callable[[], TaskSchedulerSnapshot],
    paper_http_boundary: ReadOnlyPaperHttpBoundary,
    source_provenance_reader: Callable[[], Mapping[str, object]],
    clock: Callable[[], datetime],
    invocation_id_factory: Callable[[], str] | None = None,
) -> dict[str, object]:
    """Run one exact scheduled cycle or persist one immutable duplicate no-op."""

    _validate_public_configuration(config, dispatcher, credential_provider)
    _validate_credential_records(config, credential_provider)

    now = _utc_now(clock)
    invocation_id = _new_invocation_id(invocation_id_factory)
    store = V535AdmissionStore(config.admission_db_path)
    admission = store.claim(
        scheduler_job_identity=config.scheduler_job_identity,
        accepted_window=accepted_window.identity,
        invocation_id=invocation_id,
        claimed_at=now,
    )
    if not admission.admitted:
        return _write_duplicate_noop(
            config=config,
            accepted_window=accepted_window,
            admission=admission,
            observed_at=now,
        )

    try:
        task_snapshot = task_scheduler_reader()
        _validate_task_snapshot(config, accepted_window, task_snapshot)
        provenance = dict(source_provenance_reader())
        _validate_source_provenance(provenance)

        common = {
            "cycle_id": invocation_id,
            "scheduler_job_identity": config.scheduler_job_identity,
            "accepted_window": accepted_window.identity,
            "window_start_bar_open": accepted_window.start_bar_open.isoformat(),
            "window_end_bar_open": accepted_window.end_bar_open.isoformat(),
            "provider_as_of_boundary": (
                accepted_window.provider_as_of_boundary.isoformat()
            ),
        }
        references: dict[str, dict[str, str]] = {}
        source_receipt = _role_receipt(
            "source",
            common,
            {
                "source_commit_sha": provenance["source_commit_sha"],
                "source_tree_sha": provenance["source_tree_sha"],
                "source_worktree_clean": True,
                "source_branch_or_detached": provenance[
                    "source_branch_or_detached"
                ],
                "source_bundle_sha256": provenance[
                    "adapter_source_bundle_sha256"
                ],
                "source_bundle_manifest": provenance["source_bundle_manifest"],
            },
        )
        references["source"] = _persist_role(config, source_receipt)

        scheduler_receipt = _role_receipt(
            "scheduler",
            common,
            {
                "task_identity": task_snapshot.task_identity,
                "task_enabled": task_snapshot.enabled,
                "task_state": task_snapshot.state,
                "task_action_execute": task_snapshot.action_execute,
                "task_action_arguments": task_snapshot.action_arguments,
                "last_task_result": task_snapshot.last_task_result,
                "last_run_time": task_snapshot.last_run_time.isoformat(),
                "observed_at": task_snapshot.observed_at.isoformat(),
                "source_receipt_sha256": references["source"]["sha256"],
            },
        )
        references["scheduler"] = _persist_role(config, scheduler_receipt)

        market_root = config.output_root / "market" / invocation_id
        scheduler_job = SchedulerJob(
            schema_version=SCHEDULER_SCHEMA_VERSION,
            job_id=_scheduler_dispatch_job_id(
                config.scheduler_job_identity,
                accepted_window.identity,
            ),
            lane="crypto_tournament_v2_forward_oos",
            source_commit=str(provenance["source_commit_sha"]),
            created_at=now,
            requested_start_bar_open=accepted_window.start_bar_open,
            requested_end_bar_open=accepted_window.end_bar_open,
            provider_as_of_boundary=accepted_window.provider_as_of_boundary,
            symbols=("BTCUSD", "ETHUSD", "SOLUSD"),
            accepted_frontier_bar_open=(
                accepted_window.start_bar_open - timedelta(hours=1)
            ),
            expected_frontier_bar_open=(
                accepted_window.end_bar_open + timedelta(hours=1)
            ),
            status=SchedulerJobStatus.RUNNING,
            attempt_number=1,
            claim_identity=invocation_id,
            started_at=now,
            updated_at=now,
        )
        dispatch_result = dispatcher.dispatch(
            scheduler_job,
            market_root,
            config.output_root / "inputs" / "discovery_source.csv",
            config.output_root / "inputs" / "discovery_receipt.json",
            allow_network=config.allow_network,
        )
        market_fields = _validated_market_dispatch(
            dispatch_result,
            config=config,
            accepted_window=accepted_window,
        )
        market_fields.update(
            {
                "source_receipt_sha256": references["source"]["sha256"],
                "scheduler_receipt_sha256": references["scheduler"]["sha256"],
            }
        )
        market_receipt = _role_receipt("market_data", common, market_fields)
        references["market_data"] = _persist_role(config, market_receipt)

        paper_reference = config.paper_credential_reference
        assert isinstance(paper_reference, CredentialReference)
        lease = credential_provider.open(
            paper_reference,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )

        def observe_paper(
            api_key: str,
            api_secret: str,
            expected_account: str | None,
        ) -> PaperObservationFacts:
            if expected_account is None:
                raise V535CycleError("expected_account_missing")
            return paper_http_boundary.observe(
                api_key_id=api_key,
                api_secret_key=api_secret,
                expected_account_id=expected_account,
                paper_endpoint=config.paper_endpoint,
                clock=clock,
            )

        paper_facts = lease.use(observe_paper)
        _validate_paper_facts(paper_facts)
        broker_receipt = _role_receipt(
            "broker",
            common,
            {
                "observation_classification": "read_only_paper_observation_complete",
                "observed_at": paper_facts.observed_at.isoformat(),
                "paper_endpoint": config.paper_endpoint,
                "expected_account_match": paper_facts.account_match,
                "account_active": paper_facts.account_active,
                "account_flat_reconciled": paper_facts.account_flat_reconciled,
                "position_count": paper_facts.position_count,
                "open_order_count": paper_facts.open_order_count,
                "target_asset_valid": paper_facts.target_asset_valid,
                "read_counts": {
                    "account": paper_facts.account_read_count,
                    "positions": paper_facts.positions_read_count,
                    "open_orders": paper_facts.orders_read_count,
                    "target_asset": paper_facts.asset_read_count,
                },
                "broker_read_occurred": True,
                **_no_mutation_facts(),
                "source_receipt_sha256": references["source"]["sha256"],
                "scheduler_receipt_sha256": references["scheduler"]["sha256"],
            },
        )
        references["broker"] = _persist_role(config, broker_receipt)

        readiness_receipt = _role_receipt(
            "readiness",
            common,
            {
                "readiness_classification": "read_only_cycle_ready",
                "blockers": [],
                "account_flat_reconciled": True,
                "source_receipt_sha256": references["source"]["sha256"],
                "scheduler_receipt_sha256": references["scheduler"]["sha256"],
                "market_data_receipt_sha256": references["market_data"]["sha256"],
                "broker_receipt_sha256": references["broker"]["sha256"],
                **_no_mutation_facts(),
            },
        )
        references["readiness"] = _persist_role(config, readiness_receipt)

        decision_receipt = _role_receipt(
            "decision",
            common,
            {
                "decision": "observe_only_no_action",
                "decision_classification": "completed_read_only_no_submit",
                "readiness_receipt_sha256": references["readiness"]["sha256"],
                "account_flat_reconciled": True,
                **_no_mutation_facts(),
            },
        )
        references["decision"] = _persist_role(config, decision_receipt)

        completed_at = _utc_now(clock)
        composite = {
            "schema_version": V535_CYCLE_SCHEMA,
            "classification": "completed_read_only_cycle",
            "invocation_source": "scheduled",
            **common,
            "completed_at_utc": completed_at.isoformat(),
            "evidence_references": references,
            "account_flat_reconciled": True,
            "production_dispatcher": "RealCommandDispatcher",
            **_no_mutation_facts(),
        }
        composite["canonical_receipt_sha256"] = _canonical_hash(composite)
        cycle_path = config.output_root / "cycles" / f"cycle_{invocation_id}.json"
        _write_json_immutable(cycle_path, composite)
        store.finalize(
            scheduler_job_identity=config.scheduler_job_identity,
            accepted_window=accepted_window.identity,
            owner_invocation_id=invocation_id,
            status="completed",
            cycle_sha256=str(composite["canonical_receipt_sha256"]),
            finalized_at=completed_at,
        )
        return composite
    except Exception as exc:
        classification = _safe_cycle_failure(exc)
        blocked_at = _utc_now(clock)
        blocked = {
            "schema_version": V535_CYCLE_SCHEMA,
            "classification": classification,
            "invocation_source": "scheduled",
            "cycle_id": invocation_id,
            "scheduler_job_identity": config.scheduler_job_identity,
            "accepted_window": accepted_window.identity,
            "window_start_bar_open": accepted_window.start_bar_open.isoformat(),
            "window_end_bar_open": accepted_window.end_bar_open.isoformat(),
            "provider_as_of_boundary": (
                accepted_window.provider_as_of_boundary.isoformat()
            ),
            "completed_at_utc": blocked_at.isoformat(),
            "production_dispatcher": "RealCommandDispatcher",
            "account_flat_reconciled": False,
            **_no_mutation_facts(),
        }
        blocked["canonical_receipt_sha256"] = _canonical_hash(blocked)
        blocked_path = (
            config.output_root / "cycles" / f"cycle_{invocation_id}.json"
        )
        _write_json_immutable(blocked_path, blocked)
        store.finalize(
            scheduler_job_identity=config.scheduler_job_identity,
            accepted_window=accepted_window.identity,
            owner_invocation_id=invocation_id,
            status="blocked",
            cycle_sha256=str(blocked["canonical_receipt_sha256"]),
            finalized_at=blocked_at,
        )
        return blocked


def query_windows_task_snapshot(
    *,
    task_identity: str = V535_TASK_IDENTITY,
    runner: Callable[..., object] | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> TaskSchedulerSnapshot:
    """Perform one bounded read-only Task Scheduler query."""

    task_name = task_identity.lstrip("\\")
    escaped = task_name.replace("'", "''")
    command = (
        f"$t=Get-ScheduledTask -TaskName '{escaped}' -ErrorAction Stop;"
        f"$i=Get-ScheduledTaskInfo -TaskName '{escaped}' -ErrorAction Stop;"
        "@{state=[string]$t.State;enabled=([string]$t.State -ne 'Disabled');"
        "action_execute=[string]$t.Actions[0].Execute;"
        "action_arguments=[string]$t.Actions[0].Arguments;"
        "last_task_result=[int]$i.LastTaskResult;"
        "last_run_time=([datetime]$i.LastRunTime).ToUniversalTime().ToString('o')}"
        "|ConvertTo-Json -Compress"
    )
    run = runner or subprocess.run
    try:
        completed = run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception:
        raise V535CycleError("scheduler_query_failed") from None
    if int(getattr(completed, "returncode", 1)) != 0:
        raise V535CycleError("scheduler_query_failed")
    try:
        payload = json.loads(str(getattr(completed, "stdout", "")))
        return TaskSchedulerSnapshot(
            task_identity=task_identity,
            enabled=payload["enabled"] is True,
            state=str(payload["state"]),
            action_execute=str(payload["action_execute"]),
            action_arguments=str(payload["action_arguments"]),
            last_task_result=int(payload["last_task_result"]),
            last_run_time=_parse_datetime(payload["last_run_time"]),
            observed_at=_utc_now(clock),
        )
    except Exception:
        raise V535CycleError("scheduler_query_malformed") from None


def _validate_public_configuration(
    config: V535CycleConfig,
    dispatcher: RealCommandDispatcher,
    provider: CredentialProvider,
) -> None:
    if not isinstance(config, V535CycleConfig):
        raise V535CycleError("cycle_configuration_malformed")
    if type(dispatcher) is not RealCommandDispatcher:
        raise V535CycleError("real_command_dispatcher_required")
    forbidden_environment_names = (
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
    if any(
        str(os.environ.get(name, "")).strip()
        for name in forbidden_environment_names
    ):
        raise V535CycleError("credential_environment_alias_rejected")
    if config.app_profile.strip().lower() != "paper":
        raise V535CycleError("paper_profile_required")
    if config.paper_endpoint.strip().lower().rstrip("/") != EXPECTED_PAPER_ENDPOINT:
        raise V535CycleError("paper_endpoint_mismatch")
    if (
        config.market_data_endpoint.strip().lower().rstrip("/")
        != EXPECTED_MARKET_DATA_ENDPOINT
    ):
        raise V535CycleError("market_data_endpoint_mismatch")
    if not all(
        (
            config.scheduler_enabled,
            config.market_data_read_authorized,
            config.paper_broker_read_authorized,
            config.allow_network,
        )
    ):
        raise V535CycleError("read_only_authorization_incomplete")
    if config.credential_provider_name != WINDOWS_PROVIDER_NAME:
        raise V535CycleError("credential_provider_unsupported")
    if getattr(provider, "provider_name", None) != config.credential_provider_name:
        raise V535CycleError("credential_provider_mismatch")
    market_reference = config.market_data_credential_reference
    paper_reference = config.paper_credential_reference
    assert isinstance(market_reference, CredentialReference)
    assert isinstance(paper_reference, CredentialReference)
    if market_reference.family is not CredentialFamily.ALPACA_MARKET_DATA:
        raise V535CycleError("credential_family_mismatch")
    if paper_reference.family is not CredentialFamily.ALPACA_PAPER_OBSERVATION:
        raise V535CycleError("credential_family_mismatch")
    if dispatcher.credential_provider is not provider:
        raise V535CycleError("dispatcher_credential_provider_mismatch")
    if dispatcher.credential_reference is None or (
        str(dispatcher.credential_reference) != str(market_reference)
    ):
        raise V535CycleError("dispatcher_credential_reference_mismatch")
    if dispatcher.credential_provider_name != config.credential_provider_name:
        raise V535CycleError("dispatcher_credential_provider_mismatch")
    if dispatcher.app_profile != config.app_profile:
        raise V535CycleError("dispatcher_profile_mismatch")
    if dispatcher.paper_endpoint != config.paper_endpoint:
        raise V535CycleError("dispatcher_paper_endpoint_mismatch")
    if dispatcher.market_data_endpoint != config.market_data_endpoint:
        raise V535CycleError("dispatcher_market_data_endpoint_mismatch")


def _validate_credential_records(
    config: V535CycleConfig,
    provider: CredentialProvider,
) -> None:
    try:
        market_reference = config.market_data_credential_reference
        paper_reference = config.paper_credential_reference
        assert isinstance(market_reference, CredentialReference)
        assert isinstance(paper_reference, CredentialReference)
        provider.validate(
            market_reference,
            expected_family=CredentialFamily.ALPACA_MARKET_DATA,
        )
        provider.validate(
            paper_reference,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )
    except CredentialProviderError as exc:
        raise V535CycleError(exc.classification) from None


def _validate_task_snapshot(
    config: V535CycleConfig,
    window: AcceptedWindow,
    snapshot: TaskSchedulerSnapshot,
) -> None:
    if not isinstance(snapshot, TaskSchedulerSnapshot):
        raise V535CycleError("scheduler_snapshot_malformed")
    if snapshot.task_identity != config.scheduler_job_identity:
        raise V535CycleError("scheduler_identity_mismatch")
    if not snapshot.enabled or snapshot.state not in {"Ready", "Running"}:
        raise V535CycleError("scheduler_task_disabled_or_failed")
    if snapshot.action_execute.lower() != config.expected_task_execute.lower():
        raise V535CycleError("scheduler_action_mismatch")
    if snapshot.action_arguments != config.expected_task_arguments:
        raise V535CycleError("scheduler_action_mismatch")
    if snapshot.last_task_result != 0:
        raise V535CycleError("scheduler_task_result_failed")
    if snapshot.last_run_time < window.provider_as_of_boundary:
        raise V535CycleError("scheduler_run_time_mismatch")
    if snapshot.last_run_time > snapshot.observed_at:
        raise V535CycleError("scheduler_snapshot_clock_mismatch")


def _validate_source_provenance(provenance: Mapping[str, object]) -> None:
    required = {
        "source_commit_sha",
        "source_tree_sha",
        "source_worktree_clean",
        "source_branch_or_detached",
        "adapter_source_bundle_sha256",
        "source_bundle_manifest",
    }
    if set(provenance) != required:
        raise V535CycleError("source_provenance_malformed")
    for name, expected_length in (
        ("source_commit_sha", 40),
        ("source_tree_sha", 40),
        ("adapter_source_bundle_sha256", 64),
    ):
        value = provenance.get(name)
        if type(value) is not str or len(value) != expected_length:
            raise V535CycleError("source_provenance_malformed")
        try:
            int(value, 16)
        except ValueError:
            raise V535CycleError("source_provenance_malformed") from None
    if provenance.get("source_worktree_clean") is not True:
        raise V535CycleError("source_worktree_dirty")
    if type(provenance.get("source_branch_or_detached")) is not str:
        raise V535CycleError("source_provenance_malformed")
    manifest = provenance.get("source_bundle_manifest")
    if not isinstance(manifest, Mapping) or not manifest:
        raise V535CycleError("source_provenance_malformed")


def _validated_market_dispatch(
    result: Mapping[str, object],
    *,
    config: V535CycleConfig,
    accepted_window: AcceptedWindow,
) -> dict[str, object]:
    if not isinstance(result, Mapping):
        raise V535CycleError("market_dispatch_malformed")
    if result.get("status") != "success" or result.get("dispatch_type") != "real":
        raise V535CycleError("market_dispatch_failed")
    output = result.get("output")
    if not isinstance(output, Mapping):
        raise V535CycleError("market_dispatch_output_malformed")
    if output.get("market_data_fetch_occurred") is not True:
        raise V535CycleError("market_data_fetch_not_proven")
    if output.get("network_access_attempted") is not True:
        raise V535CycleError("market_data_network_not_proven")
    for name in _MUTATION_FIELDS:
        if output.get(name, False) is not False:
            raise V535CycleError("market_dispatch_mutation_bearing")
    manifest = result.get("expected_receipts")
    if not isinstance(manifest, Sequence) or isinstance(manifest, (str, bytes)):
        raise V535CycleError("market_receipt_manifest_malformed")
    expected_window = accepted_window.identity
    normalized_manifest: list[dict[str, str]] = []
    root = config.output_root.resolve()
    for item in manifest:
        if not isinstance(item, Mapping):
            raise V535CycleError("market_receipt_manifest_malformed")
        path_value = item.get("path")
        sha_value = item.get("sha256")
        type_value = item.get("type")
        if (
            type(path_value) is not str
            or type(sha_value) is not str
            or type(type_value) is not str
            or item.get("window_identity") != expected_window
        ):
            raise V535CycleError("market_receipt_manifest_malformed")
        path = Path(path_value).resolve()
        try:
            relative = path.relative_to(root)
        except ValueError:
            raise V535CycleError("market_receipt_path_escape") from None
        if not path.is_file() or _file_sha256(path) != sha_value:
            raise V535CycleError("market_receipt_hash_mismatch")
        normalized_manifest.append(
            {
                "path": relative.as_posix(),
                "sha256": sha_value,
                "type": type_value,
                "window_identity": expected_window,
            }
        )
    if {item["type"] for item in normalized_manifest} != {
        "operating_packet",
        "frozen_state",
    }:
        raise V535CycleError("market_receipt_manifest_ambiguous")
    return {
        "dispatch_type": "real",
        "dispatch_status": "success",
        "dispatch_classification": str(result.get("classification", "")),
        "market_data_fetch_occurred": True,
        "network_access_attempted": True,
        "artifact_manifest": normalized_manifest,
        **_no_mutation_facts(),
    }


def _validate_paper_facts(facts: PaperObservationFacts) -> None:
    if not isinstance(facts, PaperObservationFacts):
        raise V535CycleError("broker_observation_malformed")
    if not facts.account_match or not facts.account_active:
        raise V535CycleError("broker_account_mismatch_or_inactive")
    if not facts.target_asset_valid:
        raise V535CycleError("broker_target_asset_invalid")
    if not facts.account_flat_reconciled:
        raise V535CycleError("broker_account_non_flat")
    if facts.position_count != 0 or facts.open_order_count != 0:
        raise V535CycleError("broker_account_non_flat")
    if (
        facts.account_read_count,
        facts.positions_read_count,
        facts.orders_read_count,
        facts.asset_read_count,
    ) != (1, 1, 1, 1):
        raise V535CycleError("broker_read_count_mismatch")


def _role_receipt(
    role: str,
    common: Mapping[str, object],
    fields: Mapping[str, object],
) -> dict[str, object]:
    if role not in _ROLE_NAMES:
        raise V535CycleError("evidence_role_unknown")
    receipt = {
        "schema_version": V535_ROLE_SCHEMA,
        "evidence_role": role,
        **dict(common),
        **dict(fields),
    }
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    return receipt


def _persist_role(
    config: V535CycleConfig,
    receipt: Mapping[str, object],
) -> dict[str, str]:
    cycle_id = str(receipt["cycle_id"])
    role = str(receipt["evidence_role"])
    digest = str(receipt["canonical_receipt_sha256"])
    relative = Path("evidence") / cycle_id / f"{role}_{digest}.json"
    _write_json_immutable(config.output_root / relative, receipt)
    return {"path": relative.as_posix(), "sha256": digest}


def _write_duplicate_noop(
    *,
    config: V535CycleConfig,
    accepted_window: AcceptedWindow,
    admission: AdmissionResult,
    observed_at: datetime,
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema_version": V535_DUPLICATE_SCHEMA,
        "classification": "duplicate_window_no_op",
        "invocation_id": admission.invocation_id,
        "original_owner_invocation_id": admission.owner_invocation_id,
        "scheduler_job_identity": config.scheduler_job_identity,
        "accepted_window": accepted_window.identity,
        "observed_at_utc": observed_at.isoformat(),
        "subprocess_created": False,
        "client_constructed": False,
        "network_access_attempted": False,
        "broker_read_occurred": False,
        **_no_mutation_facts(),
    }
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    path = (
        config.output_root
        / "duplicates"
        / f"duplicate_{admission.invocation_id}.json"
    )
    _write_json_immutable(path, receipt)
    return receipt


def _no_mutation_facts() -> dict[str, bool]:
    return {name: False for name in _MUTATION_FIELDS}


def _safe_cycle_failure(exc: Exception) -> str:
    if isinstance(exc, V535CycleError):
        classification = exc.classification
    elif isinstance(exc, CredentialProviderError):
        classification = exc.classification
    else:
        classification = "unexpected_cycle_failure"
    if not classification.startswith("blocked_"):
        classification = f"blocked_{classification}"
    return classification


def _scheduler_dispatch_job_id(task_identity: str, window: str) -> str:
    return "v535_" + hashlib.sha256(f"{task_identity}|{window}".encode()).hexdigest()[:32]


def _new_invocation_id(factory: Callable[[], str] | None) -> str:
    value = factory() if factory is not None else uuid.uuid4().hex
    if type(value) is not str or not value or len(value) > 128:
        raise V535CycleError("invocation_identity_malformed")
    if not all(character.isalnum() or character in "_-" for character in value):
        raise V535CycleError("invocation_identity_malformed")
    return value


def _canonical_hash(payload: Mapping[str, object]) -> str:
    body = {
        key: value
        for key, value in payload.items()
        if key != "canonical_receipt_sha256"
    }
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_immutable(path: Path, payload: Mapping[str, object]) -> None:
    if path.exists():
        raise V535CycleError("immutable_evidence_exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = -1
    temporary_name = ""
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = -1
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            raise V535CycleError("immutable_evidence_exists")
        os.replace(temporary_name, path)
        temporary_name = ""
    except V535CycleError:
        raise
    except Exception:
        raise V535CycleError("immutable_evidence_persistence_failed") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise V535CycleError("datetime_malformed") from None
    else:
        raise V535CycleError("datetime_malformed")
    if parsed.tzinfo is None:
        raise V535CycleError("datetime_malformed")
    return parsed.astimezone(UTC)


def _utc_now(clock: Callable[[], datetime]) -> datetime:
    try:
        return _parse_datetime(clock())
    except Exception:
        raise V535CycleError("clock_malformed") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V5.35 secure unattended read-only scheduled cycle."
    )
    parser.add_argument("--output-root", default="runs/v5_35_unattended_readonly")
    parser.add_argument("--admission-db-path", default="")
    parser.add_argument("--as-of", default="")
    parser.add_argument("--scheduler-job-identity", default=V535_TASK_IDENTITY)
    parser.add_argument("--expected-task-execute", default=V535_TASK_EXECUTE)
    parser.add_argument("--expected-task-arguments", default=V535_TASK_ARGUMENTS)
    parser.add_argument("--credential-provider", default=WINDOWS_PROVIDER_NAME)
    parser.add_argument("--market-data-credential-reference", default=V535_MARKET_REFERENCE)
    parser.add_argument("--paper-credential-reference", default=V535_PAPER_REFERENCE)
    parser.add_argument("--app-profile", default="paper")
    parser.add_argument("--paper-endpoint", default=EXPECTED_PAPER_ENDPOINT)
    parser.add_argument("--market-data-endpoint", default=EXPECTED_MARKET_DATA_ENDPOINT)
    parser.add_argument("--scheduler-enabled", action="store_true")
    parser.add_argument("--market-data-read-authorized", action="store_true")
    parser.add_argument("--paper-broker-read-authorized", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    clock = lambda: datetime.now(UTC)
    try:
        as_of = _parse_datetime(args.as_of) if args.as_of else _utc_now(clock)
        target_bar = (as_of - timedelta(minutes=5)).replace(
            minute=0,
            second=0,
            microsecond=0,
        ) - timedelta(hours=1)
        window = AcceptedWindow(
            target_bar,
            target_bar,
            target_bar + timedelta(hours=1),
        )
        output_root = Path(args.output_root)
        db_path = (
            Path(args.admission_db_path)
            if args.admission_db_path
            else output_root / "admission.sqlite3"
        )
        provider = provider_from_name(args.credential_provider)
        market_reference = CredentialReference(
            args.market_data_credential_reference
        )
        config = V535CycleConfig(
            output_root=output_root,
            admission_db_path=db_path,
            scheduler_job_identity=args.scheduler_job_identity,
            expected_task_execute=args.expected_task_execute,
            expected_task_arguments=args.expected_task_arguments,
            credential_provider_name=args.credential_provider,
            market_data_credential_reference=market_reference,
            paper_credential_reference=args.paper_credential_reference,
            app_profile=args.app_profile,
            paper_endpoint=args.paper_endpoint,
            market_data_endpoint=args.market_data_endpoint,
            scheduler_enabled=args.scheduler_enabled,
            market_data_read_authorized=args.market_data_read_authorized,
            paper_broker_read_authorized=args.paper_broker_read_authorized,
            allow_network=args.allow_network,
        )
        dispatcher = RealCommandDispatcher(
            scheduler_enabled=config.scheduler_enabled,
            market_data_read_authorized=config.market_data_read_authorized,
            credential_reference=market_reference,
            credential_provider=provider,
            credential_provider_name=config.credential_provider_name,
            app_profile=config.app_profile,
            paper_endpoint=config.paper_endpoint,
            market_data_endpoint=config.market_data_endpoint,
        )
        from algotrader.execution.crypto_read_only_paper_observation_adapter import (
            get_source_provenance,
        )

        receipt = run_v535_unattended_cycle(
            config=config,
            accepted_window=window,
            dispatcher=dispatcher,
            credential_provider=provider,
            task_scheduler_reader=lambda: query_windows_task_snapshot(
                task_identity=config.scheduler_job_identity,
                clock=clock,
            ),
            paper_http_boundary=AlpacaSdkReadOnlyPaperHttpBoundary(),
            source_provenance_reader=lambda: get_source_provenance(Path.cwd()),
            clock=clock,
        )
    except (V535CycleError, CredentialProviderError) as exc:
        classification = (
            exc.classification
            if isinstance(exc, (V535CycleError, CredentialProviderError))
            else "blocked_unexpected_cycle_failure"
        )
        print(json.dumps({"classification": classification}, sort_keys=True))
        return 2
    except Exception:
        print(
            json.dumps(
                {"classification": "blocked_unexpected_cycle_failure"},
                sort_keys=True,
            )
        )
        return 2

    safe_summary = {
        "classification": receipt.get("classification"),
        "cycle_sha256": receipt.get("canonical_receipt_sha256"),
        "credential_values_exposed": False,
        "paper_mutation_performed": False,
        "live_authorized": False,
    }
    print(json.dumps(safe_summary, sort_keys=True))
    return 0 if receipt.get("classification") in {
        "completed_read_only_cycle",
        "duplicate_window_no_op",
    } else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
