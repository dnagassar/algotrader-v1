"""Offline-proven crash-safe coordinator for broker cancellation boundaries."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.durable_cancel_contracts import (
    DurableCancelEvidence,
    DurableCancelIdentity,
)
from algotrader.execution.order_journal import (
    CancelIntent,
    CancelJournalRecord,
    CancelReservationResult,
    SqliteOrderJournal,
)

__all__ = [
    "DurableCancelCoordinator",
    "DurableCancelEvidence",
    "DurableCancelIdentity",
    "DurableCancelLease",
    "DurableCancelObservation",
    "DurableCancelOutcome",
]


@dataclass(frozen=True, slots=True)
class DurableCancelLease:
    lease_name: str
    owner_run_id: str
    lease_token: str
    fencing_generation: int
    acquired: bool = True
    blocker: str = ""

    def __post_init__(self) -> None:
        for field_name in ("lease_name", "owner_run_id"):
            value = str(getattr(self, field_name)).strip()
            if not value:
                raise ValidationError(f"{field_name} is required.")
            object.__setattr__(self, field_name, value)
        token = str(self.lease_token).strip()
        if self.acquired and not token:
            raise ValidationError("lease_token is required for an acquired lease.")
        object.__setattr__(self, "lease_token", token)
        if type(self.fencing_generation) is not int or self.fencing_generation < 0:
            raise ValidationError("fencing_generation must be a non-negative integer.")
        if self.acquired and self.fencing_generation <= 0:
            raise ValidationError(
                "an acquired lease requires positive fencing_generation."
            )
        if type(self.acquired) is not bool:
            raise ValidationError("acquired must be a boolean.")
        object.__setattr__(self, "blocker", str(self.blocker).strip())


@dataclass(frozen=True, slots=True)
class DurableCancelObservation:
    broker_status: str

    def __post_init__(self) -> None:
        status = str(self.broker_status).strip().lower()
        if not status:
            raise ValidationError("broker_status is required.")
        object.__setattr__(self, "broker_status", status)


@dataclass(frozen=True, slots=True)
class DurableCancelOutcome:
    status: str
    broker_called: bool
    record: CancelJournalRecord | None
    response: Any = None
    blocker: str = ""
    error_type: str = ""
    safe_error_message: str = ""
    journal_error_type: str = ""
    exception: Exception | None = field(default=None, repr=False, compare=False)

    @property
    def observed(self) -> bool:
        return self.status == "observed"

    @property
    def ambiguous(self) -> bool:
        return self.status == "ambiguous"


class DurableCancelCoordinator:
    """Own the final durable transition around one injected cancel callback."""

    def __init__(self, journal: SqliteOrderJournal) -> None:
        if not isinstance(journal, SqliteOrderJournal):
            raise ValidationError("journal must be a SqliteOrderJournal.")
        self.journal = journal

    def reserve(
        self,
        identity: DurableCancelIdentity,
        occurred_at: datetime,
    ) -> CancelReservationResult:
        if not isinstance(identity, DurableCancelIdentity):
            raise ValidationError("identity must be DurableCancelIdentity.")
        return self.journal.reserve_cancel_intent(
            CancelIntent(
                cancel_intent_id=identity.cancel_intent_id,
                client_order_id=identity.client_order_id,
                broker_order_id=identity.broker_order_id,
                run_id=identity.reservation_run_id,
                reason=identity.reason,
            ),
            occurred_at,
        )

    def acquire_lease(
        self,
        *,
        lease_name: str,
        owner_run_id: str,
        occurred_at: datetime,
        ttl_seconds: int,
        lease_token: str | None = None,
    ) -> DurableCancelLease:
        result = self.journal.acquire_runtime_lease(
            lease_name=lease_name,
            owner_run_id=owner_run_id,
            occurred_at=occurred_at,
            ttl_seconds=ttl_seconds,
            lease_token=lease_token,
        )
        return DurableCancelLease(
            lease_name=result.lease_name,
            owner_run_id=(owner_run_id if result.acquired else result.owner_run_id),
            lease_token=result.lease_token,
            fencing_generation=result.fencing_generation,
            acquired=result.acquired,
            blocker=result.blocker,
        )

    def release_lease(self, lease: DurableCancelLease) -> bool:
        if not isinstance(lease, DurableCancelLease):
            raise ValidationError("lease must be DurableCancelLease.")
        if not lease.acquired:
            return False
        return self.journal.release_runtime_lease(
            lease_name=lease.lease_name,
            owner_run_id=lease.owner_run_id,
            lease_token=lease.lease_token,
        )

    def execute(
        self,
        *,
        identity: DurableCancelIdentity,
        lease: DurableCancelLease,
        evidence: DurableCancelEvidence,
        occurred_at: datetime,
        cancel: Callable[[], Any],
        observe: Callable[[Any], DurableCancelObservation],
        sanitize_exception: Callable[[Exception], str] | None = None,
    ) -> DurableCancelOutcome:
        if not isinstance(identity, DurableCancelIdentity):
            raise ValidationError("identity must be DurableCancelIdentity.")
        if not isinstance(lease, DurableCancelLease):
            raise ValidationError("lease must be DurableCancelLease.")
        if not isinstance(evidence, DurableCancelEvidence):
            raise ValidationError("evidence must be DurableCancelEvidence.")
        if not callable(cancel) or not callable(observe):
            raise ValidationError("cancel and observe must be callable.")
        if not lease.acquired:
            return DurableCancelOutcome(
                status="blocked",
                broker_called=False,
                record=None,
                blocker=lease.blocker or "runtime_lease_unavailable",
            )

        try:
            claimed = self.journal.claim_pre_mutation_cancel(
                cancel_intent_id=identity.cancel_intent_id,
                client_order_id=identity.client_order_id,
                broker_order_id=identity.broker_order_id,
                reservation_run_id=identity.reservation_run_id,
                lease_name=lease.lease_name,
                lease_owner_run_id=lease.owner_run_id,
                lease_token=lease.lease_token,
                fencing_generation=lease.fencing_generation,
                cancel_allowed=evidence.cancel_allowed,
                snapshot_fresh=evidence.snapshot_fresh,
                occurred_at=occurred_at,
            )
        except ValidationError as exc:
            return DurableCancelOutcome(
                status="blocked",
                broker_called=False,
                record=None,
                blocker=str(exc),
            )
        except Exception as exc:
            return DurableCancelOutcome(
                status="blocked",
                broker_called=False,
                record=None,
                blocker="durable_cancel_journal_unavailable",
                error_type=exc.__class__.__name__,
            )

        try:
            response = cancel()
        except Exception as exc:
            record, journal_error = self._mark_ambiguous(
                identity=identity,
                occurred_at=occurred_at,
                reason=exc.__class__.__name__,
            )
            return DurableCancelOutcome(
                status="ambiguous",
                broker_called=True,
                record=record or claimed,
                blocker="cancel_response_ambiguous",
                error_type=exc.__class__.__name__,
                safe_error_message=_safe_exception_message(exc, sanitize_exception),
                journal_error_type=journal_error,
                exception=exc,
            )

        try:
            observation = observe(response)
            if not isinstance(observation, DurableCancelObservation):
                raise ValidationError(
                    "observe must return DurableCancelObservation."
                )
            record = self.journal.record_cancel_observation(
                identity.cancel_intent_id,
                occurred_at,
                broker_status=observation.broker_status,
            )
        except Exception as exc:
            record, journal_error = self._mark_ambiguous(
                identity=identity,
                occurred_at=occurred_at,
                reason="cancel_observation_persistence_failed",
            )
            return DurableCancelOutcome(
                status="ambiguous",
                broker_called=True,
                record=record or claimed,
                response=response,
                blocker="cancel_observation_persistence_failed",
                error_type=exc.__class__.__name__,
                safe_error_message=_safe_exception_message(exc, sanitize_exception),
                journal_error_type=journal_error,
                exception=exc,
            )

        return DurableCancelOutcome(
            status="observed",
            broker_called=True,
            record=record,
            response=response,
        )

    def _mark_ambiguous(
        self,
        *,
        identity: DurableCancelIdentity,
        occurred_at: datetime,
        reason: str,
    ) -> tuple[CancelJournalRecord | None, str]:
        try:
            return (
                self.journal.mark_cancel_ambiguous(
                    identity.cancel_intent_id,
                    occurred_at,
                    reason=reason,
                ),
                "",
            )
        except Exception as exc:
            try:
                record = self.journal.get_cancel_intent(identity.cancel_intent_id)
            except Exception:
                record = None
            return record, exc.__class__.__name__


def _safe_exception_message(
    exc: Exception,
    sanitizer: Callable[[Exception], str] | None,
) -> str:
    if sanitizer is None:
        return exc.__class__.__name__
    try:
        return str(sanitizer(exc))
    except Exception:
        return exc.__class__.__name__
