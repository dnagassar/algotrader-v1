"""Pure default-denied handoff preview for durable cancellation inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.order_journal import OrderJournalRecord, OrderJournalState
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationPlanningResult,
)


DURABLE_CANCELLATION_HANDOFF_PREVIEW_VERSION = (
    "durable_cancellation_handoff_preview_v1"
)


class DurableCancellationHandoffStatus(StrEnum):
    PREPARED = "prepared"
    BLOCKED = "blocked"


class DurableCancellationHandoffBlocker(StrEnum):
    HANDOFF_NOT_PERMITTED = "handoff_not_permitted"
    PLANNING_RESULT_MISSING = "planning_result_missing"
    PLAN_NOT_AVAILABLE = "plan_not_available"
    RECORD_MISSING = "record_missing"
    RECORD_TIMESTAMP_INVALID = "record_timestamp_invalid"
    RECORD_TIMESTAMP_INCONSISTENT = "record_timestamp_inconsistent"
    FUTURE_RECORD_TIMESTAMP = "future_record_timestamp"
    RECORD_TERMINAL = "record_terminal"
    RECORD_STATE_NOT_CANCEL_READY = "record_state_not_cancel_ready"
    RECORD_STALE = "record_stale"
    RECORD_IDENTITY_INCOMPLETE = "record_identity_incomplete"
    CLIENT_ORDER_ID_MISMATCH = "client_order_id_mismatch"
    BROKER_ORDER_ID_MISMATCH = "broker_order_id_mismatch"
    SYMBOL_MISMATCH = "symbol_mismatch"
    BROKER_STATUS_MISMATCH = "broker_status_mismatch"
    OBSERVATION_TIMESTAMP_MISMATCH = "observation_timestamp_mismatch"


@dataclass(frozen=True, slots=True)
class DurableCancellationHandoffRequest:
    as_of: datetime
    maximum_record_age_seconds: int
    handoff_permitted: bool

    def __post_init__(self) -> None:
        try:
            as_of = require_utc_datetime(self.as_of)
        except ValidationError as exc:
            raise ValidationError(
                "as_of must be a timezone-aware UTC datetime."
            ) from exc
        object.__setattr__(self, "as_of", as_of)
        if (
            type(self.maximum_record_age_seconds) is not int
            or self.maximum_record_age_seconds <= 0
        ):
            raise ValidationError(
                "maximum_record_age_seconds must be a positive integer."
            )
        if type(self.handoff_permitted) is not bool:
            raise ValidationError("handoff_permitted must be a boolean.")

    def to_dict(self) -> dict[str, object]:
        return {
            "as_of": self.as_of.isoformat(),
            "maximum_record_age_seconds": self.maximum_record_age_seconds,
            "handoff_permitted": self.handoff_permitted,
        }


@dataclass(frozen=True, slots=True)
class DurableCancellationHandoffIdentity:
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    reservation_run_id: str
    reason: str
    source_plan_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "client_order_id",
            "broker_order_id",
            "reservation_run_id",
            "reason",
            "source_plan_id",
        ):
            value = str(getattr(self, field_name)).strip()
            if not value:
                raise ValidationError(f"{field_name} is required.")
            object.__setattr__(self, field_name, value)
        expected = _cancel_intent_id(
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
            reservation_run_id=self.reservation_run_id,
            reason=self.reason,
            source_plan_id=self.source_plan_id,
        )
        if str(self.cancel_intent_id).strip() != expected:
            raise ValidationError(
                "cancel_intent_id does not match the durable handoff identity."
            )
        object.__setattr__(self, "cancel_intent_id", expected)

    def coordinator_inputs(self) -> dict[str, str]:
        """Return exact DurableCancelIdentity-compatible primitive inputs."""

        return {
            "cancel_intent_id": self.cancel_intent_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "reservation_run_id": self.reservation_run_id,
            "reason": self.reason,
        }

    def to_dict(self) -> dict[str, str]:
        return {
            **self.coordinator_inputs(),
            "source_plan_id": self.source_plan_id,
        }


@dataclass(frozen=True, slots=True)
class DurableCancellationHandoffPreview:
    artifact_id: str
    status: DurableCancellationHandoffStatus
    blocker: DurableCancellationHandoffBlocker | None
    request: DurableCancellationHandoffRequest
    source_plan_id: str
    identity: DurableCancellationHandoffIdentity | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, DurableCancellationHandoffStatus):
            raise ValidationError(
                "status must be a DurableCancellationHandoffStatus."
            )
        if not isinstance(self.request, DurableCancellationHandoffRequest):
            raise ValidationError(
                "request must be a DurableCancellationHandoffRequest."
            )
        source_plan_id = str(self.source_plan_id).strip()
        object.__setattr__(self, "source_plan_id", source_plan_id)
        if self.status is DurableCancellationHandoffStatus.PREPARED:
            if not isinstance(self.identity, DurableCancellationHandoffIdentity):
                raise ValidationError("prepared preview requires one identity.")
            if self.blocker is not None:
                raise ValidationError("prepared preview cannot contain a blocker.")
            if not self.request.handoff_permitted:
                raise ValidationError("prepared preview requires handoff permission.")
            if not source_plan_id or self.identity.source_plan_id != source_plan_id:
                raise ValidationError(
                    "prepared preview requires one matching source plan ID."
                )
        elif self.identity is not None or not isinstance(
            self.blocker,
            DurableCancellationHandoffBlocker,
        ):
            raise ValidationError(
                "blocked preview requires one typed blocker and no identity."
            )
        expected = _artifact_id(
            status=self.status,
            blocker=self.blocker,
            request=self.request,
            source_plan_id=source_plan_id,
            identity=self.identity,
        )
        if str(self.artifact_id).strip() != expected:
            raise ValidationError(
                "artifact_id does not match durable handoff evidence."
            )
        object.__setattr__(self, "artifact_id", expected)

    @property
    def prepared(self) -> bool:
        return self.status is DurableCancellationHandoffStatus.PREPARED

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            **_artifact_payload(
                status=self.status,
                blocker=self.blocker,
                request=self.request,
                source_plan_id=self.source_plan_id,
                identity=self.identity,
            ),
        }


def preview_durable_cancellation_handoff(
    planning_result: CancellationPlanningResult | None,
    record: OrderJournalRecord | None,
    request: DurableCancellationHandoffRequest,
) -> DurableCancellationHandoffPreview:
    """Prepare deterministic identity inputs without crossing a mutation boundary."""

    if not isinstance(request, DurableCancellationHandoffRequest):
        raise ValidationError(
            "request must be a DurableCancellationHandoffRequest."
        )
    if planning_result is not None and not isinstance(
        planning_result,
        CancellationPlanningResult,
    ):
        raise ValidationError(
            "planning_result must be a CancellationPlanningResult or None."
        )
    if record is not None and not isinstance(record, OrderJournalRecord):
        raise ValidationError("record must be an OrderJournalRecord or None.")
    if not request.handoff_permitted:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.HANDOFF_NOT_PERMITTED,
            planning_result,
        )
    if planning_result is None:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.PLANNING_RESULT_MISSING,
        )
    if not planning_result.planned or planning_result.plan is None:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.PLAN_NOT_AVAILABLE,
            planning_result,
        )
    plan = planning_result.plan
    if record is None:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.RECORD_MISSING,
            planning_result,
        )
    if not _valid_record_timestamps(record):
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.RECORD_TIMESTAMP_INVALID,
            planning_result,
        )
    if record.created_at > record.updated_at:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.RECORD_TIMESTAMP_INCONSISTENT,
            planning_result,
        )
    if record.created_at > request.as_of or record.updated_at > request.as_of:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.FUTURE_RECORD_TIMESTAMP,
            planning_result,
        )
    if record.terminal:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.RECORD_TERMINAL,
            planning_result,
        )
    if (
        not isinstance(record.state, OrderJournalState)
        or record.state
        not in {OrderJournalState.ACCEPTED, OrderJournalState.PARTIALLY_FILLED}
    ):
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.RECORD_STATE_NOT_CANCEL_READY,
            planning_result,
        )
    if (
        request.as_of - record.updated_at
    ).total_seconds() > request.maximum_record_age_seconds:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.RECORD_STALE,
            planning_result,
        )
    if any(
        not str(value).strip()
        for value in (
            record.client_order_id,
            record.broker_order_id,
            record.run_id,
        )
    ):
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.RECORD_IDENTITY_INCOMPLETE,
            planning_result,
        )
    if plan.client_order_id != record.client_order_id:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.CLIENT_ORDER_ID_MISMATCH,
            planning_result,
        )
    if plan.broker_order_id != record.broker_order_id:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.BROKER_ORDER_ID_MISMATCH,
            planning_result,
        )
    if plan.symbol != record.symbol:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.SYMBOL_MISMATCH,
            planning_result,
        )
    if plan.broker_status != _normalized_status(record.broker_status):
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.BROKER_STATUS_MISMATCH,
            planning_result,
        )
    if plan.observed_at != record.updated_at:
        return _blocked(
            request,
            DurableCancellationHandoffBlocker.OBSERVATION_TIMESTAMP_MISMATCH,
            planning_result,
        )

    identity = DurableCancellationHandoffIdentity(
        cancel_intent_id=_cancel_intent_id(
            client_order_id=plan.client_order_id,
            broker_order_id=plan.broker_order_id,
            reservation_run_id=record.run_id,
            reason=plan.reason,
            source_plan_id=plan.plan_id,
        ),
        client_order_id=plan.client_order_id,
        broker_order_id=plan.broker_order_id,
        reservation_run_id=record.run_id,
        reason=plan.reason,
        source_plan_id=plan.plan_id,
    )
    return _preview(
        status=DurableCancellationHandoffStatus.PREPARED,
        blocker=None,
        request=request,
        source_plan_id=plan.plan_id,
        identity=identity,
    )


def _blocked(
    request: DurableCancellationHandoffRequest,
    blocker: DurableCancellationHandoffBlocker,
    planning_result: CancellationPlanningResult | None = None,
) -> DurableCancellationHandoffPreview:
    source_plan_id = ""
    if (
        isinstance(planning_result, CancellationPlanningResult)
        and planning_result.plan is not None
    ):
        source_plan_id = planning_result.plan.plan_id
    return _preview(
        status=DurableCancellationHandoffStatus.BLOCKED,
        blocker=blocker,
        request=request,
        source_plan_id=source_plan_id,
        identity=None,
    )


def _preview(
    *,
    status: DurableCancellationHandoffStatus,
    blocker: DurableCancellationHandoffBlocker | None,
    request: DurableCancellationHandoffRequest,
    source_plan_id: str,
    identity: DurableCancellationHandoffIdentity | None,
) -> DurableCancellationHandoffPreview:
    return DurableCancellationHandoffPreview(
        artifact_id=_artifact_id(
            status=status,
            blocker=blocker,
            request=request,
            source_plan_id=source_plan_id,
            identity=identity,
        ),
        status=status,
        blocker=blocker,
        request=request,
        source_plan_id=source_plan_id,
        identity=identity,
    )


def _artifact_id(
    *,
    status: DurableCancellationHandoffStatus,
    blocker: DurableCancellationHandoffBlocker | None,
    request: DurableCancellationHandoffRequest,
    source_plan_id: str,
    identity: DurableCancellationHandoffIdentity | None,
) -> str:
    encoded = json.dumps(
        _artifact_payload(
            status=status,
            blocker=blocker,
            request=request,
            source_plan_id=source_plan_id,
            identity=identity,
        ),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"cancel_handoff_{hashlib.sha256(encoded).hexdigest()[:24]}"


def _artifact_payload(
    *,
    status: DurableCancellationHandoffStatus,
    blocker: DurableCancellationHandoffBlocker | None,
    request: DurableCancellationHandoffRequest,
    source_plan_id: str,
    identity: DurableCancellationHandoffIdentity | None,
) -> dict[str, object]:
    return {
        "artifact_version": DURABLE_CANCELLATION_HANDOFF_PREVIEW_VERSION,
        "status": status.value,
        "blocker": "" if blocker is None else blocker.value,
        "request": request.to_dict(),
        "source_plan_id": source_plan_id,
        "identity": {} if identity is None else identity.to_dict(),
        "coordinator_identity_inputs": (
            {} if identity is None else identity.coordinator_inputs()
        ),
        "no_submit": True,
        "handoff_prepared": (
            status is DurableCancellationHandoffStatus.PREPARED
        ),
        "cancel_allowed": False,
        "execution_authorized": False,
        "broker_callback_present": False,
        "coordinator_invoked": False,
        "cancel_attempted": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "journal_mutation_performed": False,
    }


def _cancel_intent_id(
    *,
    client_order_id: str,
    broker_order_id: str,
    reservation_run_id: str,
    reason: str,
    source_plan_id: str,
) -> str:
    basis = {
        "version": DURABLE_CANCELLATION_HANDOFF_PREVIEW_VERSION,
        "client_order_id": client_order_id,
        "broker_order_id": broker_order_id,
        "reservation_run_id": reservation_run_id,
        "reason": reason,
        "source_plan_id": source_plan_id,
    }
    encoded = json.dumps(basis, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"cancel_intent_{hashlib.sha256(encoded).hexdigest()[:24]}"


def _valid_record_timestamps(record: OrderJournalRecord) -> bool:
    try:
        require_utc_datetime(record.created_at)
        require_utc_datetime(record.updated_at)
    except ValidationError:
        return False
    return True


def _normalized_status(value: object) -> str:
    text = str(value).strip().lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")


__all__ = [
    "DURABLE_CANCELLATION_HANDOFF_PREVIEW_VERSION",
    "DurableCancellationHandoffBlocker",
    "DurableCancellationHandoffIdentity",
    "DurableCancellationHandoffPreview",
    "DurableCancellationHandoffRequest",
    "DurableCancellationHandoffStatus",
    "preview_durable_cancellation_handoff",
]
