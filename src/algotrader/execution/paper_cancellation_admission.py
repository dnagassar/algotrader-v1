"""Pure exact-authorization admission before durable cancellation execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.durable_cancel_contracts import (
    DurableCancelEvidence,
    DurableCancelIdentity,
)
from algotrader.execution.paper_cancellation_handoff_preview import (
    DurableCancellationHandoffPreview,
)


OPERATOR_CANCELLATION_AUTHORIZATION_VERSION = (
    "operator_cancellation_authorization_v1"
)
PAPER_CANCELLATION_ADMISSION_VERSION = "paper_cancellation_admission_v1"
PAPER_CANCELLATION_MODE = "paper"
CANCELLATION_OPERATION = "cancel"


class PaperCancellationAdmissionStatus(StrEnum):
    ADMITTED = "admitted"
    BLOCKED = "blocked"


class PaperCancellationAdmissionBlocker(StrEnum):
    STOP_REQUESTED = "stop_requested"
    TRADING_PAUSED = "trading_paused"
    SNAPSHOT_NOT_FRESH = "snapshot_not_fresh"
    HANDOFF_MISSING = "handoff_missing"
    HANDOFF_NOT_PREPARED = "handoff_not_prepared"
    HANDOFF_IDENTITY_MISSING = "handoff_identity_missing"
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_NOT_GRANTED = "authorization_not_granted"
    AUTHORIZATION_MODE_MISMATCH = "authorization_mode_mismatch"
    AUTHORIZATION_OPERATION_MISMATCH = "authorization_operation_mismatch"
    AUTHORIZATION_NOT_YET_VALID = "authorization_not_yet_valid"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    SOURCE_PLAN_ID_MISMATCH = "source_plan_id_mismatch"
    CANCEL_INTENT_ID_MISMATCH = "cancel_intent_id_mismatch"
    CLIENT_ORDER_ID_MISMATCH = "client_order_id_mismatch"
    BROKER_ORDER_ID_MISMATCH = "broker_order_id_mismatch"


@dataclass(frozen=True, slots=True)
class OperatorCancellationAuthorization:
    authorization_id: str
    mode: str
    operation: str
    source_plan_id: str
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    issued_at: datetime
    expires_at: datetime
    authorized: bool

    def __post_init__(self) -> None:
        mode = _required(self.mode, "mode").lower()
        operation = _required(self.operation, "operation").lower()
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "operation", operation)
        for field_name in (
            "source_plan_id",
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), field_name),
            )
        issued_at = _utc_datetime(self.issued_at, "issued_at")
        expires_at = _utc_datetime(self.expires_at, "expires_at")
        if expires_at <= issued_at:
            raise ValidationError("expires_at must be later than issued_at.")
        object.__setattr__(self, "issued_at", issued_at)
        object.__setattr__(self, "expires_at", expires_at)
        if type(self.authorized) is not bool:
            raise ValidationError("authorized must be a boolean.")
        expected = _authorization_id(
            mode=mode,
            operation=operation,
            source_plan_id=self.source_plan_id,
            cancel_intent_id=self.cancel_intent_id,
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
            issued_at=issued_at,
            expires_at=expires_at,
            authorized=self.authorized,
        )
        if str(self.authorization_id).strip() != expected:
            raise ValidationError(
                "authorization_id does not match cancellation authorization evidence."
            )
        object.__setattr__(self, "authorization_id", expected)

    def to_dict(self) -> dict[str, object]:
        return {
            "authorization_version": OPERATOR_CANCELLATION_AUTHORIZATION_VERSION,
            "authorization_id": self.authorization_id,
            "mode": self.mode,
            "operation": self.operation,
            "source_plan_id": self.source_plan_id,
            "cancel_intent_id": self.cancel_intent_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "authorized": self.authorized,
        }


def build_operator_cancellation_authorization_evidence(
    *,
    mode: str,
    operation: str,
    source_plan_id: str,
    cancel_intent_id: str,
    client_order_id: str,
    broker_order_id: str,
    issued_at: datetime,
    expires_at: datetime,
    authorized: bool,
) -> OperatorCancellationAuthorization:
    """Build immutable caller-supplied evidence; this does not execute a cancel."""

    normalized_mode = _required(mode, "mode").lower()
    normalized_operation = _required(operation, "operation").lower()
    normalized_source_plan_id = _required(source_plan_id, "source_plan_id")
    normalized_cancel_intent_id = _required(cancel_intent_id, "cancel_intent_id")
    normalized_client_order_id = _required(client_order_id, "client_order_id")
    normalized_broker_order_id = _required(broker_order_id, "broker_order_id")
    normalized_issued_at = _utc_datetime(issued_at, "issued_at")
    normalized_expires_at = _utc_datetime(expires_at, "expires_at")
    if normalized_expires_at <= normalized_issued_at:
        raise ValidationError("expires_at must be later than issued_at.")
    if type(authorized) is not bool:
        raise ValidationError("authorized must be a boolean.")
    return OperatorCancellationAuthorization(
        authorization_id=_authorization_id(
            mode=normalized_mode,
            operation=normalized_operation,
            source_plan_id=normalized_source_plan_id,
            cancel_intent_id=normalized_cancel_intent_id,
            client_order_id=normalized_client_order_id,
            broker_order_id=normalized_broker_order_id,
            issued_at=normalized_issued_at,
            expires_at=normalized_expires_at,
            authorized=authorized,
        ),
        mode=normalized_mode,
        operation=normalized_operation,
        source_plan_id=normalized_source_plan_id,
        cancel_intent_id=normalized_cancel_intent_id,
        client_order_id=normalized_client_order_id,
        broker_order_id=normalized_broker_order_id,
        issued_at=normalized_issued_at,
        expires_at=normalized_expires_at,
        authorized=authorized,
    )


@dataclass(frozen=True, slots=True)
class PaperCancellationAdmissionRequest:
    evaluated_at: datetime
    trading_enabled: bool
    stop_requested: bool
    snapshot_fresh: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evaluated_at",
            _utc_datetime(self.evaluated_at, "evaluated_at"),
        )
        for field_name in (
            "trading_enabled",
            "stop_requested",
            "snapshot_fresh",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")

    def to_dict(self) -> dict[str, object]:
        return {
            "evaluated_at": self.evaluated_at.isoformat(),
            "trading_enabled": self.trading_enabled,
            "stop_requested": self.stop_requested,
            "snapshot_fresh": self.snapshot_fresh,
        }


@dataclass(frozen=True, slots=True)
class PaperCancellationAdmissionResult:
    admission_id: str
    status: PaperCancellationAdmissionStatus
    blocker: PaperCancellationAdmissionBlocker | None
    request: PaperCancellationAdmissionRequest
    source_handoff_artifact_id: str
    source_plan_id: str
    authorization_id: str
    identity: DurableCancelIdentity | None
    evidence: DurableCancelEvidence | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, PaperCancellationAdmissionStatus):
            raise ValidationError(
                "status must be a PaperCancellationAdmissionStatus."
            )
        if not isinstance(self.request, PaperCancellationAdmissionRequest):
            raise ValidationError(
                "request must be a PaperCancellationAdmissionRequest."
            )
        for field_name in (
            "source_handoff_artifact_id",
            "source_plan_id",
            "authorization_id",
        ):
            object.__setattr__(
                self,
                field_name,
                str(getattr(self, field_name)).strip(),
            )
        if self.status is PaperCancellationAdmissionStatus.ADMITTED:
            if not isinstance(self.identity, DurableCancelIdentity):
                raise ValidationError("admitted result requires one durable identity.")
            if not isinstance(self.evidence, DurableCancelEvidence):
                raise ValidationError("admitted result requires durable evidence.")
            if self.blocker is not None:
                raise ValidationError("admitted result cannot contain a blocker.")
            if not all(
                (
                    self.source_handoff_artifact_id,
                    self.source_plan_id,
                    self.authorization_id,
                )
            ):
                raise ValidationError(
                    "admitted result requires handoff, plan, and authorization IDs."
                )
            if not self.evidence.cancel_allowed or not self.evidence.snapshot_fresh:
                raise ValidationError(
                    "admitted result requires allowed cancellation and fresh snapshot evidence."
                )
        elif (
            self.identity is not None
            or self.evidence is not None
            or not isinstance(self.blocker, PaperCancellationAdmissionBlocker)
        ):
            raise ValidationError(
                "blocked result requires one typed blocker and no durable inputs."
            )
        expected = _admission_id(
            status=self.status,
            blocker=self.blocker,
            request=self.request,
            source_handoff_artifact_id=self.source_handoff_artifact_id,
            source_plan_id=self.source_plan_id,
            authorization_id=self.authorization_id,
            identity=self.identity,
            evidence=self.evidence,
        )
        if str(self.admission_id).strip() != expected:
            raise ValidationError(
                "admission_id does not match cancellation admission evidence."
            )
        object.__setattr__(self, "admission_id", expected)

    @property
    def admitted(self) -> bool:
        return self.status is PaperCancellationAdmissionStatus.ADMITTED

    def to_dict(self) -> dict[str, object]:
        return {
            "admission_id": self.admission_id,
            **_admission_payload(
                status=self.status,
                blocker=self.blocker,
                request=self.request,
                source_handoff_artifact_id=self.source_handoff_artifact_id,
                source_plan_id=self.source_plan_id,
                authorization_id=self.authorization_id,
                identity=self.identity,
                evidence=self.evidence,
            ),
        }


def evaluate_paper_cancellation_admission(
    handoff: DurableCancellationHandoffPreview | None,
    authorization: OperatorCancellationAuthorization | None,
    request: PaperCancellationAdmissionRequest,
) -> PaperCancellationAdmissionResult:
    """Validate exact admission facts without invoking any execution boundary."""

    if not isinstance(request, PaperCancellationAdmissionRequest):
        raise ValidationError("request must be a PaperCancellationAdmissionRequest.")
    if handoff is not None and not isinstance(
        handoff,
        DurableCancellationHandoffPreview,
    ):
        raise ValidationError(
            "handoff must be a DurableCancellationHandoffPreview or None."
        )
    if authorization is not None and not isinstance(
        authorization,
        OperatorCancellationAuthorization,
    ):
        raise ValidationError(
            "authorization must be an OperatorCancellationAuthorization or None."
        )

    if request.stop_requested:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.STOP_REQUESTED,
            handoff,
            authorization,
        )
    if not request.trading_enabled:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.TRADING_PAUSED,
            handoff,
            authorization,
        )
    if not request.snapshot_fresh:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.SNAPSHOT_NOT_FRESH,
            handoff,
            authorization,
        )
    if handoff is None:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.HANDOFF_MISSING,
            handoff,
            authorization,
        )
    if not handoff.prepared:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.HANDOFF_NOT_PREPARED,
            handoff,
            authorization,
        )
    if handoff.identity is None:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.HANDOFF_IDENTITY_MISSING,
            handoff,
            authorization,
        )
    if authorization is None:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.AUTHORIZATION_MISSING,
            handoff,
            authorization,
        )
    if not authorization.authorized:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.AUTHORIZATION_NOT_GRANTED,
            handoff,
            authorization,
        )
    if authorization.mode != PAPER_CANCELLATION_MODE:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.AUTHORIZATION_MODE_MISMATCH,
            handoff,
            authorization,
        )
    if authorization.operation != CANCELLATION_OPERATION:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.AUTHORIZATION_OPERATION_MISMATCH,
            handoff,
            authorization,
        )
    if request.evaluated_at < authorization.issued_at:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.AUTHORIZATION_NOT_YET_VALID,
            handoff,
            authorization,
        )
    if request.evaluated_at >= authorization.expires_at:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.AUTHORIZATION_EXPIRED,
            handoff,
            authorization,
        )

    handoff_identity = handoff.identity
    if authorization.source_plan_id != handoff.source_plan_id:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.SOURCE_PLAN_ID_MISMATCH,
            handoff,
            authorization,
        )
    if authorization.cancel_intent_id != handoff_identity.cancel_intent_id:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.CANCEL_INTENT_ID_MISMATCH,
            handoff,
            authorization,
        )
    if authorization.client_order_id != handoff_identity.client_order_id:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.CLIENT_ORDER_ID_MISMATCH,
            handoff,
            authorization,
        )
    if authorization.broker_order_id != handoff_identity.broker_order_id:
        return _blocked(
            request,
            PaperCancellationAdmissionBlocker.BROKER_ORDER_ID_MISMATCH,
            handoff,
            authorization,
        )

    identity = DurableCancelIdentity(**handoff_identity.coordinator_inputs())
    evidence = DurableCancelEvidence(
        cancel_allowed=True,
        snapshot_fresh=True,
    )
    return _result(
        status=PaperCancellationAdmissionStatus.ADMITTED,
        blocker=None,
        request=request,
        handoff=handoff,
        authorization=authorization,
        identity=identity,
        evidence=evidence,
    )


def _blocked(
    request: PaperCancellationAdmissionRequest,
    blocker: PaperCancellationAdmissionBlocker,
    handoff: DurableCancellationHandoffPreview | None,
    authorization: OperatorCancellationAuthorization | None,
) -> PaperCancellationAdmissionResult:
    return _result(
        status=PaperCancellationAdmissionStatus.BLOCKED,
        blocker=blocker,
        request=request,
        handoff=handoff,
        authorization=authorization,
        identity=None,
        evidence=None,
    )


def _result(
    *,
    status: PaperCancellationAdmissionStatus,
    blocker: PaperCancellationAdmissionBlocker | None,
    request: PaperCancellationAdmissionRequest,
    handoff: DurableCancellationHandoffPreview | None,
    authorization: OperatorCancellationAuthorization | None,
    identity: DurableCancelIdentity | None,
    evidence: DurableCancelEvidence | None,
) -> PaperCancellationAdmissionResult:
    source_handoff_artifact_id = "" if handoff is None else handoff.artifact_id
    source_plan_id = "" if handoff is None else handoff.source_plan_id
    authorization_id = (
        "" if authorization is None else authorization.authorization_id
    )
    return PaperCancellationAdmissionResult(
        admission_id=_admission_id(
            status=status,
            blocker=blocker,
            request=request,
            source_handoff_artifact_id=source_handoff_artifact_id,
            source_plan_id=source_plan_id,
            authorization_id=authorization_id,
            identity=identity,
            evidence=evidence,
        ),
        status=status,
        blocker=blocker,
        request=request,
        source_handoff_artifact_id=source_handoff_artifact_id,
        source_plan_id=source_plan_id,
        authorization_id=authorization_id,
        identity=identity,
        evidence=evidence,
    )


def _admission_id(
    *,
    status: PaperCancellationAdmissionStatus,
    blocker: PaperCancellationAdmissionBlocker | None,
    request: PaperCancellationAdmissionRequest,
    source_handoff_artifact_id: str,
    source_plan_id: str,
    authorization_id: str,
    identity: DurableCancelIdentity | None,
    evidence: DurableCancelEvidence | None,
) -> str:
    encoded = json.dumps(
        _admission_payload(
            status=status,
            blocker=blocker,
            request=request,
            source_handoff_artifact_id=source_handoff_artifact_id,
            source_plan_id=source_plan_id,
            authorization_id=authorization_id,
            identity=identity,
            evidence=evidence,
        ),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"cancel_admission_{hashlib.sha256(encoded).hexdigest()[:24]}"


def _admission_payload(
    *,
    status: PaperCancellationAdmissionStatus,
    blocker: PaperCancellationAdmissionBlocker | None,
    request: PaperCancellationAdmissionRequest,
    source_handoff_artifact_id: str,
    source_plan_id: str,
    authorization_id: str,
    identity: DurableCancelIdentity | None,
    evidence: DurableCancelEvidence | None,
) -> dict[str, object]:
    admitted = status is PaperCancellationAdmissionStatus.ADMITTED
    return {
        "admission_version": PAPER_CANCELLATION_ADMISSION_VERSION,
        "status": status.value,
        "blocker": "" if blocker is None else blocker.value,
        "request": request.to_dict(),
        "source_handoff_artifact_id": source_handoff_artifact_id,
        "source_plan_id": source_plan_id,
        "authorization_id": authorization_id,
        "identity": {} if identity is None else _identity_payload(identity),
        "evidence": {} if evidence is None else _evidence_payload(evidence),
        "admission_ready": admitted,
        "operator_authorization_validated": admitted,
        "cancel_allowed": admitted,
        "execution_authorized": admitted,
        "execution_performed": False,
        "broker_callback_present": False,
        "coordinator_invoked": False,
        "lease_acquired": False,
        "cancel_intent_reserved": False,
        "cancel_attempted": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "journal_mutation_performed": False,
        "live_authorized": False,
        "no_submit": True,
    }


def _authorization_id(
    *,
    mode: str,
    operation: str,
    source_plan_id: str,
    cancel_intent_id: str,
    client_order_id: str,
    broker_order_id: str,
    issued_at: datetime,
    expires_at: datetime,
    authorized: bool,
) -> str:
    basis = {
        "version": OPERATOR_CANCELLATION_AUTHORIZATION_VERSION,
        "mode": mode,
        "operation": operation,
        "source_plan_id": source_plan_id,
        "cancel_intent_id": cancel_intent_id,
        "client_order_id": client_order_id,
        "broker_order_id": broker_order_id,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "authorized": authorized,
    }
    encoded = json.dumps(basis, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"cancel_authorization_{hashlib.sha256(encoded).hexdigest()[:24]}"


def _identity_payload(identity: DurableCancelIdentity) -> dict[str, str]:
    return {
        "cancel_intent_id": identity.cancel_intent_id,
        "client_order_id": identity.client_order_id,
        "broker_order_id": identity.broker_order_id,
        "reservation_run_id": identity.reservation_run_id,
        "reason": identity.reason,
    }


def _evidence_payload(evidence: DurableCancelEvidence) -> dict[str, bool]:
    return {
        "cancel_allowed": evidence.cancel_allowed,
        "snapshot_fresh": evidence.snapshot_fresh,
    }


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
    "CANCELLATION_OPERATION",
    "OPERATOR_CANCELLATION_AUTHORIZATION_VERSION",
    "PAPER_CANCELLATION_ADMISSION_VERSION",
    "PAPER_CANCELLATION_MODE",
    "OperatorCancellationAuthorization",
    "PaperCancellationAdmissionBlocker",
    "PaperCancellationAdmissionRequest",
    "PaperCancellationAdmissionResult",
    "PaperCancellationAdmissionStatus",
    "build_operator_cancellation_authorization_evidence",
    "evaluate_paper_cancellation_admission",
]
