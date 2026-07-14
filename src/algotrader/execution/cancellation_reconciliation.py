"""Broker-free convergence for one unresolved durable cancellation.

The caller supplies one already-observed broker order snapshot. This module
does not discover a target, contact a broker, read credentials, or expose a
broker mutation callback.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import decimal_value
from algotrader.errors import ValidationError
from algotrader.execution.order_journal import (
    CancelJournalRecord,
    OrderJournalRecord,
    SqliteOrderJournal,
)


CANCELLATION_RECONCILIATION_VERSION = "cancellation_reconciliation_v1"


class CancellationReconciliationStatus(StrEnum):
    CONVERGED = "converged"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CancellationReconciliationIdentity:
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class CancellationReconciliationObservation:
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    broker_status: str
    observed_at: datetime
    filled_quantity: Decimal | str | None = None
    filled_average_price: Decimal | str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "broker_status",
            _normalized_status(self.broker_status),
        )
        object.__setattr__(
            self,
            "observed_at",
            _utc_datetime(self.observed_at, "observed_at"),
        )
        object.__setattr__(
            self,
            "filled_quantity",
            _optional_non_negative_decimal(
                self.filled_quantity,
                "filled_quantity",
            ),
        )
        object.__setattr__(
            self,
            "filled_average_price",
            _optional_positive_decimal(
                self.filled_average_price,
                "filled_average_price",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "cancel_intent_id": self.cancel_intent_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "broker_status": self.broker_status,
            "observed_at": self.observed_at.isoformat(),
            "filled_quantity": _decimal_text(self.filled_quantity),
            "filled_average_price": _decimal_text(self.filled_average_price),
        }


@dataclass(frozen=True, slots=True)
class CancellationReconciliationResult:
    identity: CancellationReconciliationIdentity
    observation: CancellationReconciliationObservation
    status: CancellationReconciliationStatus
    blocker: str
    local_journal_updated: bool
    order_record: OrderJournalRecord | None = None
    cancel_record: CancelJournalRecord | None = None
    error_type: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.identity, CancellationReconciliationIdentity):
            raise ValidationError(
                "identity must be a CancellationReconciliationIdentity."
            )
        if not isinstance(
            self.observation,
            CancellationReconciliationObservation,
        ):
            raise ValidationError(
                "observation must be a CancellationReconciliationObservation."
            )
        if not isinstance(self.status, CancellationReconciliationStatus):
            raise ValidationError(
                "status must be a CancellationReconciliationStatus."
            )
        if type(self.local_journal_updated) is not bool:
            raise ValidationError("local_journal_updated must be a boolean.")
        object.__setattr__(self, "blocker", str(self.blocker).strip())
        object.__setattr__(self, "error_type", str(self.error_type).strip())
        if self.status is CancellationReconciliationStatus.CONVERGED:
            if (
                self.blocker
                or not self.local_journal_updated
                or self.order_record is None
                or self.cancel_record is None
            ):
                raise ValidationError(
                    "converged reconciliation requires both journal records."
                )
        elif (
            not self.blocker
            or self.local_journal_updated
            or self.order_record is not None
            or self.cancel_record is not None
        ):
            raise ValidationError(
                "blocked reconciliation cannot report journal convergence."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "reconciliation_version": CANCELLATION_RECONCILIATION_VERSION,
            "status": self.status.value,
            "blocker": self.blocker,
            "identity": {
                "cancel_intent_id": self.identity.cancel_intent_id,
                "client_order_id": self.identity.client_order_id,
                "broker_order_id": self.identity.broker_order_id,
            },
            "observation": self.observation.to_dict(),
            "injected_observation_count": 1,
            "injected_observation_consumed": True,
            "local_journal_updated": self.local_journal_updated,
            "order_state": (
                "" if self.order_record is None else self.order_record.state.value
            ),
            "cancel_intent_state": (
                "" if self.cancel_record is None else self.cancel_record.state.value
            ),
            "order_terminal": (
                False if self.order_record is None else self.order_record.terminal
            ),
            "cancel_intent_terminal": (
                False if self.cancel_record is None else self.cancel_record.terminal
            ),
            "error_type": self.error_type,
            "retry_permitted": False,
            "safe_to_recancel": False,
            "broker_read_performed": False,
            "broker_mutation_performed": False,
            "network_accessed": False,
            "credentials_accessed": False,
            "runtime_control_changed": False,
            "target_selection_performed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "replace_attempted": False,
            "close_attempted": False,
            "liquidation_attempted": False,
            "live_authorized": False,
        }


def reconcile_unresolved_cancellation(
    journal: SqliteOrderJournal,
    identity: CancellationReconciliationIdentity,
    observation: CancellationReconciliationObservation,
) -> CancellationReconciliationResult:
    """Consume one injected observation and converge exact local state once."""

    if not isinstance(journal, SqliteOrderJournal):
        raise ValidationError("journal must be a SqliteOrderJournal.")
    if not isinstance(identity, CancellationReconciliationIdentity):
        raise ValidationError(
            "identity must be a CancellationReconciliationIdentity."
        )
    if not isinstance(observation, CancellationReconciliationObservation):
        raise ValidationError(
            "observation must be a CancellationReconciliationObservation."
        )

    mismatch = _identity_mismatch(identity, observation)
    if mismatch:
        return _blocked(identity, observation, mismatch)

    try:
        order_record, cancel_record = (
            journal.reconcile_unresolved_cancel_observation(
                cancel_intent_id=identity.cancel_intent_id,
                client_order_id=identity.client_order_id,
                broker_order_id=identity.broker_order_id,
                occurred_at=observation.observed_at,
                broker_status=observation.broker_status,
                filled_quantity=observation.filled_quantity,
                filled_average_price=observation.filled_average_price,
            )
        )
    except ValidationError as exc:
        return _blocked(identity, observation, str(exc))
    except Exception as exc:
        return _blocked(
            identity,
            observation,
            "local_journal_unavailable",
            error_type=exc.__class__.__name__,
        )

    return CancellationReconciliationResult(
        identity=identity,
        observation=observation,
        status=CancellationReconciliationStatus.CONVERGED,
        blocker="",
        local_journal_updated=True,
        order_record=order_record,
        cancel_record=cancel_record,
    )


def _blocked(
    identity: CancellationReconciliationIdentity,
    observation: CancellationReconciliationObservation,
    blocker: str,
    *,
    error_type: str = "",
) -> CancellationReconciliationResult:
    return CancellationReconciliationResult(
        identity=identity,
        observation=observation,
        status=CancellationReconciliationStatus.BLOCKED,
        blocker=_required(blocker, "blocker"),
        local_journal_updated=False,
        error_type=error_type,
    )


def _identity_mismatch(
    identity: CancellationReconciliationIdentity,
    observation: CancellationReconciliationObservation,
) -> str:
    if observation.cancel_intent_id != identity.cancel_intent_id:
        return "cancel_intent_identity_mismatch"
    if observation.client_order_id != identity.client_order_id:
        return "client_order_identity_mismatch"
    if observation.broker_order_id != identity.broker_order_id:
        return "broker_order_identity_mismatch"
    return ""


def _required(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _normalized_status(value: object) -> str:
    text = _required(value, "broker_status").lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except (TypeError, ValidationError) as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _optional_non_negative_decimal(
    value: Decimal | str | None,
    field_name: str,
) -> Decimal | None:
    if value is None or value == "":
        return None
    parsed = decimal_value(value, field_name)
    if parsed < 0:
        raise ValidationError(f"{field_name} must be non-negative.")
    return parsed


def _optional_positive_decimal(
    value: Decimal | str | None,
    field_name: str,
) -> Decimal | None:
    if value is None or value == "":
        return None
    parsed = decimal_value(value, field_name)
    if parsed <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return parsed


def _decimal_text(value: Decimal | None) -> str:
    return "" if value is None else str(value)


__all__ = [
    "CANCELLATION_RECONCILIATION_VERSION",
    "CancellationReconciliationIdentity",
    "CancellationReconciliationObservation",
    "CancellationReconciliationResult",
    "CancellationReconciliationStatus",
    "reconcile_unresolved_cancellation",
]
