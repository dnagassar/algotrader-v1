"""Shared crash-safe final-claim coordinator for broker submit boundaries."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.order_journal import (
    OrderJournalRecord,
    OrderReservation,
    ReservationResult,
    SqliteOrderJournal,
)

__all__ = [
    "DurableBrokerObservation",
    "DurableSubmitCoordinator",
    "DurableSubmitEvidence",
    "DurableSubmitIdentity",
    "DurableSubmitLease",
    "DurableSubmitOutcome",
]


@dataclass(frozen=True, slots=True)
class DurableSubmitIdentity:
    client_order_id: str
    execution_plan_id: str
    reservation_run_id: str
    symbol: str
    side: str
    quantity: Decimal | str | None
    notional: Decimal | str | None

    def reservation(self) -> OrderReservation:
        return OrderReservation(
            client_order_id=self.client_order_id,
            execution_plan_id=self.execution_plan_id,
            run_id=self.reservation_run_id,
            symbol=self.symbol,
            side=self.side,
            quantity=self.quantity,
            notional=self.notional,
        )


@dataclass(frozen=True, slots=True)
class DurableSubmitLease:
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
            raise ValidationError("an acquired lease requires positive fencing_generation.")
        if type(self.acquired) is not bool:
            raise ValidationError("acquired must be a boolean.")
        object.__setattr__(self, "blocker", str(self.blocker).strip())


@dataclass(frozen=True, slots=True)
class DurableSubmitEvidence:
    canonical_risk_allowed: bool
    snapshot_fresh: bool

    def __post_init__(self) -> None:
        if type(self.canonical_risk_allowed) is not bool:
            raise ValidationError("canonical_risk_allowed must be a boolean.")
        if type(self.snapshot_fresh) is not bool:
            raise ValidationError("snapshot_fresh must be a boolean.")


@dataclass(frozen=True, slots=True)
class DurableBrokerObservation:
    broker_order_id: str
    broker_status: str
    filled_quantity: Decimal | str | None = None
    filled_average_price: Decimal | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "broker_order_id", str(self.broker_order_id).strip())
        status = str(self.broker_status).strip().lower()
        if not status:
            raise ValidationError("broker_status is required.")
        object.__setattr__(self, "broker_status", status)


@dataclass(frozen=True, slots=True)
class DurableSubmitOutcome:
    status: str
    broker_called: bool
    record: OrderJournalRecord | None
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


class DurableSubmitCoordinator:
    """Own the final durable transition around one injected submit callback."""

    def __init__(self, journal: SqliteOrderJournal) -> None:
        if not isinstance(journal, SqliteOrderJournal):
            raise ValidationError("journal must be a SqliteOrderJournal.")
        self.journal = journal

    def reserve(
        self,
        identity: DurableSubmitIdentity,
        occurred_at: datetime,
    ) -> ReservationResult:
        if not isinstance(identity, DurableSubmitIdentity):
            raise ValidationError("identity must be DurableSubmitIdentity.")
        return self.journal.reserve(identity.reservation(), occurred_at)

    def acquire_lease(
        self,
        *,
        lease_name: str,
        owner_run_id: str,
        occurred_at: datetime,
        ttl_seconds: int,
        lease_token: str | None = None,
    ) -> DurableSubmitLease:
        result = self.journal.acquire_runtime_lease(
            lease_name=lease_name,
            owner_run_id=owner_run_id,
            occurred_at=occurred_at,
            ttl_seconds=ttl_seconds,
            lease_token=lease_token,
        )
        return DurableSubmitLease(
            lease_name=result.lease_name,
            owner_run_id=(owner_run_id if result.acquired else result.owner_run_id),
            lease_token=result.lease_token,
            fencing_generation=result.fencing_generation,
            acquired=result.acquired,
            blocker=result.blocker,
        )

    def release_lease(self, lease: DurableSubmitLease) -> bool:
        if not isinstance(lease, DurableSubmitLease):
            raise ValidationError("lease must be DurableSubmitLease.")
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
        identity: DurableSubmitIdentity,
        lease: DurableSubmitLease,
        evidence: DurableSubmitEvidence,
        occurred_at: datetime,
        submit: Callable[[], Any],
        observe: Callable[[Any], DurableBrokerObservation],
        sanitize_exception: Callable[[Exception], str] | None = None,
    ) -> DurableSubmitOutcome:
        if not isinstance(identity, DurableSubmitIdentity):
            raise ValidationError("identity must be DurableSubmitIdentity.")
        if not isinstance(lease, DurableSubmitLease):
            raise ValidationError("lease must be DurableSubmitLease.")
        if not isinstance(evidence, DurableSubmitEvidence):
            raise ValidationError("evidence must be DurableSubmitEvidence.")
        if not callable(submit) or not callable(observe):
            raise ValidationError("submit and observe must be callable.")
        if not lease.acquired:
            return DurableSubmitOutcome(
                status="blocked",
                broker_called=False,
                record=None,
                blocker=lease.blocker or "runtime_lease_unavailable",
            )

        try:
            claimed = self.journal.claim_pre_mutation_submit(
                client_order_id=identity.client_order_id,
                execution_plan_id=identity.execution_plan_id,
                reservation_run_id=identity.reservation_run_id,
                lease_name=lease.lease_name,
                lease_owner_run_id=lease.owner_run_id,
                lease_token=lease.lease_token,
                fencing_generation=lease.fencing_generation,
                canonical_risk_allowed=evidence.canonical_risk_allowed,
                snapshot_fresh=evidence.snapshot_fresh,
                occurred_at=occurred_at,
            )
        except ValidationError as exc:
            return DurableSubmitOutcome(
                status="blocked",
                broker_called=False,
                record=None,
                blocker=str(exc),
            )
        except Exception as exc:
            return DurableSubmitOutcome(
                status="blocked",
                broker_called=False,
                record=None,
                blocker="durable_submit_journal_unavailable",
                error_type=exc.__class__.__name__,
            )

        try:
            response = submit()
        except Exception as exc:
            record, journal_error = self._mark_ambiguous(
                identity=identity,
                occurred_at=occurred_at,
                reason=exc.__class__.__name__,
            )
            return DurableSubmitOutcome(
                status="ambiguous",
                broker_called=True,
                record=record or claimed,
                blocker="submit_response_ambiguous",
                error_type=exc.__class__.__name__,
                safe_error_message=_safe_exception_message(exc, sanitize_exception),
                journal_error_type=journal_error,
                exception=exc,
            )

        try:
            observation = observe(response)
            if not isinstance(observation, DurableBrokerObservation):
                raise ValidationError(
                    "observe must return DurableBrokerObservation."
                )
            record = self.journal.record_broker_observation(
                identity.client_order_id,
                occurred_at,
                broker_order_id=observation.broker_order_id,
                broker_status=observation.broker_status,
                filled_quantity=observation.filled_quantity,
                filled_average_price=observation.filled_average_price,
            )
        except Exception as exc:
            record, journal_error = self._mark_ambiguous(
                identity=identity,
                occurred_at=occurred_at,
                reason="broker_observation_persistence_failed",
            )
            return DurableSubmitOutcome(
                status="ambiguous",
                broker_called=True,
                record=record or claimed,
                response=response,
                blocker="broker_observation_persistence_failed",
                error_type=exc.__class__.__name__,
                safe_error_message=_safe_exception_message(exc, sanitize_exception),
                journal_error_type=journal_error,
                exception=exc,
            )

        return DurableSubmitOutcome(
            status="observed",
            broker_called=True,
            record=record,
            response=response,
        )

    def _mark_ambiguous(
        self,
        *,
        identity: DurableSubmitIdentity,
        occurred_at: datetime,
        reason: str,
    ) -> tuple[OrderJournalRecord | None, str]:
        try:
            return (
                self.journal.mark_submit_ambiguous(
                    identity.client_order_id,
                    occurred_at,
                    reason=reason,
                ),
                "",
            )
        except Exception as exc:
            try:
                record = self.journal.get(identity.client_order_id)
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
