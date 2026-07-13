"""Operator-gated bridge from exact admission to durable cancellation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.durable_cancel import (
    DurableCancelCoordinator,
    DurableCancelObservation,
)
from algotrader.execution.paper_cancellation_admission import (
    PaperCancellationAdmissionResult,
)


PAPER_CANCELLATION_INVOCATION_VERSION = "paper_cancellation_invocation_v1"
PAPER_CANCELLATION_INVOCATION_LEASE_NAME = "paper-autopilot-cancellation"
MAXIMUM_CANCELLATION_LEASE_TTL_SECONDS = 300


class PaperCancellationInvocationStatus(StrEnum):
    BLOCKED = "blocked"
    OBSERVED = "observed"
    AMBIGUOUS = "ambiguous"


class PaperCancellationInvocationBlocker(StrEnum):
    ADMISSION_NOT_ADMITTED = "admission_not_admitted"
    ADMISSION_ID_MISMATCH = "admission_id_mismatch"
    INVOCATION_NOT_PERMITTED = "invocation_not_permitted"
    SNAPSHOT_NOT_FRESH = "snapshot_not_fresh"
    INVOCATION_BEFORE_ADMISSION = "invocation_before_admission"
    AUTHORIZATION_NOT_CURRENT = "authorization_not_current"
    DURABLE_RESERVATION_FAILED = "durable_cancel_reservation_failed"
    DURABLE_LEASE_FAILED = "durable_cancel_lease_failed"
    RUNTIME_LEASE_UNAVAILABLE = "runtime_lease_unavailable"


@dataclass(frozen=True, slots=True)
class PaperCancellationInvocationRequest:
    expected_admission_id: str
    occurred_at: datetime
    lease_ttl_seconds: int
    snapshot_fresh: bool
    invocation_permitted: bool = False
    lease_token: str | None = None

    def __post_init__(self) -> None:
        admission_id = _required(
            self.expected_admission_id,
            "expected_admission_id",
        )
        occurred_at = _utc_datetime(self.occurred_at, "occurred_at")
        if (
            type(self.lease_ttl_seconds) is not int
            or self.lease_ttl_seconds <= 0
            or self.lease_ttl_seconds > MAXIMUM_CANCELLATION_LEASE_TTL_SECONDS
        ):
            raise ValidationError(
                "lease_ttl_seconds must be an integer between 1 and "
                f"{MAXIMUM_CANCELLATION_LEASE_TTL_SECONDS}."
            )
        for field_name in ("snapshot_fresh", "invocation_permitted"):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        lease_token = None
        if self.lease_token is not None:
            lease_token = _required(self.lease_token, "lease_token")
        object.__setattr__(self, "expected_admission_id", admission_id)
        object.__setattr__(self, "occurred_at", occurred_at)
        object.__setattr__(self, "lease_token", lease_token)

    def to_dict(self) -> dict[str, object]:
        return {
            "expected_admission_id": self.expected_admission_id,
            "occurred_at": self.occurred_at.isoformat(),
            "lease_ttl_seconds": self.lease_ttl_seconds,
            "snapshot_fresh": self.snapshot_fresh,
            "invocation_permitted": self.invocation_permitted,
            "lease_token_supplied": self.lease_token is not None,
        }


@dataclass(frozen=True, slots=True)
class PaperCancellationInvocationResult:
    source_admission_id: str
    source_authorization_id: str
    cancel_intent_id: str
    status: PaperCancellationInvocationStatus
    blocker: str
    admission_validated: bool
    invocation_permitted: bool
    authorization_current: bool
    snapshot_fresh: bool
    coordinator_invoked: bool
    reservation_status: str
    reservation_acquired: bool
    lease_acquired: bool
    lease_released: bool
    broker_called: bool
    record_state: str
    error_type: str = ""
    safe_error_message: str = ""
    journal_error_type: str = ""
    lease_release_error_type: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_admission_id",
            _required(self.source_admission_id, "source_admission_id"),
        )
        for field_name in (
            "source_authorization_id",
            "cancel_intent_id",
            "blocker",
            "reservation_status",
            "record_state",
            "error_type",
            "safe_error_message",
            "journal_error_type",
            "lease_release_error_type",
        ):
            object.__setattr__(
                self,
                field_name,
                str(getattr(self, field_name)).strip(),
            )
        if not isinstance(self.status, PaperCancellationInvocationStatus):
            raise ValidationError(
                "status must be a PaperCancellationInvocationStatus."
            )
        for field_name in (
            "admission_validated",
            "invocation_permitted",
            "authorization_current",
            "snapshot_fresh",
            "coordinator_invoked",
            "reservation_acquired",
            "lease_acquired",
            "lease_released",
            "broker_called",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        if self.status is PaperCancellationInvocationStatus.BLOCKED:
            if not self.blocker:
                raise ValidationError("blocked invocation requires a blocker.")
            if self.broker_called:
                raise ValidationError("blocked invocation cannot report broker_called.")
        elif self.status is PaperCancellationInvocationStatus.OBSERVED:
            if self.blocker or not self.broker_called or not self.record_state:
                raise ValidationError(
                    "observed invocation requires a broker call and record state."
                )
        elif not self.blocker or not self.broker_called:
            raise ValidationError(
                "ambiguous invocation requires a blocker and broker call."
            )
        if self.lease_released and not self.lease_acquired:
            raise ValidationError("released lease must have been acquired.")
        if self.broker_called and not self.coordinator_invoked:
            raise ValidationError("broker call requires coordinator invocation.")

    def to_dict(self) -> dict[str, object]:
        return {
            "invocation_version": PAPER_CANCELLATION_INVOCATION_VERSION,
            "source_admission_id": self.source_admission_id,
            "source_authorization_id": self.source_authorization_id,
            "cancel_intent_id": self.cancel_intent_id,
            "status": self.status.value,
            "blocker": self.blocker,
            "admission_validated": self.admission_validated,
            "invocation_permitted": self.invocation_permitted,
            "authorization_current": self.authorization_current,
            "snapshot_fresh": self.snapshot_fresh,
            "coordinator_invoked": self.coordinator_invoked,
            "reservation_status": self.reservation_status,
            "reservation_acquired": self.reservation_acquired,
            "lease_name": PAPER_CANCELLATION_INVOCATION_LEASE_NAME,
            "lease_acquired": self.lease_acquired,
            "lease_released": self.lease_released,
            "broker_callback_invoked": self.broker_called,
            "record_state": self.record_state,
            "error_type": self.error_type,
            "safe_error_message": self.safe_error_message,
            "journal_error_type": self.journal_error_type,
            "lease_release_error_type": self.lease_release_error_type,
            "live_authorized": False,
            "no_submit": True,
        }


def invoke_admitted_paper_cancellation(
    admission: PaperCancellationAdmissionResult,
    coordinator: DurableCancelCoordinator,
    request: PaperCancellationInvocationRequest,
    *,
    cancel: Callable[[], Any],
    observe: Callable[[Any], DurableCancelObservation],
    sanitize_exception: Callable[[Exception], str] | None = None,
) -> PaperCancellationInvocationResult:
    """Invoke one durable cancel only after every explicit gate remains valid."""

    if not isinstance(admission, PaperCancellationAdmissionResult):
        raise ValidationError(
            "admission must be a PaperCancellationAdmissionResult."
        )
    if not isinstance(coordinator, DurableCancelCoordinator):
        raise ValidationError("coordinator must be a DurableCancelCoordinator.")
    if not isinstance(request, PaperCancellationInvocationRequest):
        raise ValidationError(
            "request must be a PaperCancellationInvocationRequest."
        )
    if not admission.admitted:
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.ADMISSION_NOT_ADMITTED,
        )
    if request.expected_admission_id != admission.admission_id:
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.ADMISSION_ID_MISMATCH,
        )
    if not request.invocation_permitted:
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.INVOCATION_NOT_PERMITTED,
        )
    if not request.snapshot_fresh:
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.SNAPSHOT_NOT_FRESH,
        )
    if request.occurred_at < admission.request.evaluated_at:
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.INVOCATION_BEFORE_ADMISSION,
        )
    issued_at = admission.authorization_issued_at
    expires_at = admission.authorization_expires_at
    if (
        issued_at is None
        or expires_at is None
        or request.occurred_at < issued_at
        or request.occurred_at >= expires_at
    ):
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.AUTHORIZATION_NOT_CURRENT,
        )
    if not callable(cancel) or not callable(observe):
        raise ValidationError("cancel and observe must be callable.")
    if sanitize_exception is not None and not callable(sanitize_exception):
        raise ValidationError("sanitize_exception must be callable or None.")

    identity = admission.identity
    evidence = admission.evidence
    if identity is None or evidence is None:
        raise ValidationError("admitted result is missing durable inputs.")

    try:
        reservation = coordinator.reserve(identity, request.occurred_at)
    except Exception as exc:
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.DURABLE_RESERVATION_FAILED,
            authorization_current=True,
            coordinator_invoked=True,
            error_type=exc.__class__.__name__,
        )

    try:
        lease = coordinator.acquire_lease(
            lease_name=PAPER_CANCELLATION_INVOCATION_LEASE_NAME,
            owner_run_id=identity.reservation_run_id,
            occurred_at=request.occurred_at,
            ttl_seconds=request.lease_ttl_seconds,
            lease_token=request.lease_token,
        )
    except Exception as exc:
        return _blocked(
            admission,
            request,
            PaperCancellationInvocationBlocker.DURABLE_LEASE_FAILED,
            authorization_current=True,
            coordinator_invoked=True,
            reservation_status=reservation.status,
            reservation_acquired=reservation.acquired,
            error_type=exc.__class__.__name__,
        )

    if not lease.acquired:
        return _blocked(
            admission,
            request,
            lease.blocker
            or PaperCancellationInvocationBlocker.RUNTIME_LEASE_UNAVAILABLE,
            authorization_current=True,
            coordinator_invoked=True,
            reservation_status=reservation.status,
            reservation_acquired=reservation.acquired,
        )

    lease_released = False
    lease_release_error_type = ""
    try:
        outcome = coordinator.execute(
            identity=identity,
            lease=lease,
            evidence=evidence,
            occurred_at=request.occurred_at,
            cancel=cancel,
            observe=observe,
            sanitize_exception=sanitize_exception,
        )
    finally:
        try:
            lease_released = coordinator.release_lease(lease)
        except Exception as exc:
            lease_release_error_type = exc.__class__.__name__

    if outcome.observed:
        status = PaperCancellationInvocationStatus.OBSERVED
    elif outcome.ambiguous:
        status = PaperCancellationInvocationStatus.AMBIGUOUS
    else:
        status = PaperCancellationInvocationStatus.BLOCKED
    record_state = ""
    if outcome.record is not None:
        record_state = outcome.record.state.value
    return PaperCancellationInvocationResult(
        source_admission_id=admission.admission_id,
        source_authorization_id=admission.authorization_id,
        cancel_intent_id=identity.cancel_intent_id,
        status=status,
        blocker=outcome.blocker,
        admission_validated=True,
        invocation_permitted=True,
        authorization_current=True,
        snapshot_fresh=True,
        coordinator_invoked=True,
        reservation_status=reservation.status,
        reservation_acquired=reservation.acquired,
        lease_acquired=True,
        lease_released=lease_released,
        broker_called=outcome.broker_called,
        record_state=record_state,
        error_type=outcome.error_type,
        safe_error_message=outcome.safe_error_message,
        journal_error_type=outcome.journal_error_type,
        lease_release_error_type=lease_release_error_type,
    )


def _blocked(
    admission: PaperCancellationAdmissionResult,
    request: PaperCancellationInvocationRequest,
    blocker: PaperCancellationInvocationBlocker | str,
    *,
    authorization_current: bool = False,
    coordinator_invoked: bool = False,
    reservation_status: str = "",
    reservation_acquired: bool = False,
    error_type: str = "",
) -> PaperCancellationInvocationResult:
    blocker_text = blocker.value if isinstance(
        blocker,
        PaperCancellationInvocationBlocker,
    ) else str(blocker).strip()
    identity = admission.identity
    return PaperCancellationInvocationResult(
        source_admission_id=admission.admission_id,
        source_authorization_id=admission.authorization_id,
        cancel_intent_id="" if identity is None else identity.cancel_intent_id,
        status=PaperCancellationInvocationStatus.BLOCKED,
        blocker=blocker_text,
        admission_validated=admission.admitted,
        invocation_permitted=request.invocation_permitted,
        authorization_current=authorization_current,
        snapshot_fresh=request.snapshot_fresh,
        coordinator_invoked=coordinator_invoked,
        reservation_status=reservation_status,
        reservation_acquired=reservation_acquired,
        lease_acquired=False,
        lease_released=False,
        broker_called=False,
        record_state="",
        error_type=error_type,
    )


def _required(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except (TypeError, ValidationError) as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


__all__ = [
    "MAXIMUM_CANCELLATION_LEASE_TTL_SECONDS",
    "PAPER_CANCELLATION_INVOCATION_LEASE_NAME",
    "PAPER_CANCELLATION_INVOCATION_VERSION",
    "PaperCancellationInvocationBlocker",
    "PaperCancellationInvocationRequest",
    "PaperCancellationInvocationResult",
    "PaperCancellationInvocationStatus",
    "invoke_admitted_paper_cancellation",
]
