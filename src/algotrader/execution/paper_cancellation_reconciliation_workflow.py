"""One-shot composition for exact paper cancellation reconciliation.

This module connects the authorization/observation boundary to the atomic
local reconciler. It accepts one caller-supplied exact reader and never owns a
broker client, credentials, target selection, polling, retry, or broker mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
    CancellationReconciliationResult,
    CancellationReconciliationStatus,
    reconcile_unresolved_cancellation,
)
from algotrader.execution.order_journal import SqliteOrderJournal
from algotrader.execution.paper_cancellation_observation import (
    ExactOrderReader,
    PaperCancellationObservationAuthorization,
    PaperCancellationObservationRequest,
    PaperCancellationObservationResult,
    observe_exact_paper_cancellation,
)


PAPER_CANCELLATION_RECONCILIATION_WORKFLOW_VERSION = (
    "paper_cancellation_reconciliation_workflow_v1"
)


class PaperCancellationReconciliationWorkflowStatus(StrEnum):
    CONVERGED = "converged"
    OBSERVATION_BLOCKED = "observation_blocked"
    RECONCILIATION_BLOCKED = "reconciliation_blocked"


@dataclass(frozen=True, slots=True)
class PaperCancellationReconciliationWorkflowResult:
    identity: CancellationReconciliationIdentity
    observation_result: PaperCancellationObservationResult
    reconciliation_result: CancellationReconciliationResult | None
    status: PaperCancellationReconciliationWorkflowStatus

    def __post_init__(self) -> None:
        if not isinstance(self.identity, CancellationReconciliationIdentity):
            raise ValidationError(
                "identity must be a CancellationReconciliationIdentity."
            )
        if not isinstance(
            self.observation_result,
            PaperCancellationObservationResult,
        ):
            raise ValidationError(
                "observation_result must be a PaperCancellationObservationResult."
            )
        if self.reconciliation_result is not None and not isinstance(
            self.reconciliation_result,
            CancellationReconciliationResult,
        ):
            raise ValidationError(
                "reconciliation_result must be a CancellationReconciliationResult "
                "or None."
            )
        if not isinstance(
            self.status,
            PaperCancellationReconciliationWorkflowStatus,
        ):
            raise ValidationError(
                "status must be a PaperCancellationReconciliationWorkflowStatus."
            )
        if self.observation_result.identity != self.identity:
            raise ValidationError("observation result identity is inconsistent.")
        if (
            self.reconciliation_result is not None
            and self.reconciliation_result.identity != self.identity
        ):
            raise ValidationError("reconciliation result identity is inconsistent.")

        if self.status is PaperCancellationReconciliationWorkflowStatus.CONVERGED:
            if (
                not self.observation_result.observed
                or self.reconciliation_result is None
                or self.reconciliation_result.status
                is not CancellationReconciliationStatus.CONVERGED
                or not self.reconciliation_result.local_journal_updated
            ):
                raise ValidationError(
                    "converged workflow requires one validated observation and "
                    "local reconciliation."
                )
        elif (
            self.status
            is PaperCancellationReconciliationWorkflowStatus.OBSERVATION_BLOCKED
        ):
            if (
                self.observation_result.observed
                or self.reconciliation_result is not None
            ):
                raise ValidationError(
                    "observation-blocked workflow cannot invoke reconciliation."
                )
        elif (
            not self.observation_result.observed
            or self.reconciliation_result is None
            or self.reconciliation_result.status
            is not CancellationReconciliationStatus.BLOCKED
            or self.reconciliation_result.local_journal_updated
        ):
            raise ValidationError(
                "reconciliation-blocked workflow requires a validated observation "
                "and no local journal update."
            )

    @property
    def blocker(self) -> str:
        if self.reconciliation_result is not None:
            return self.reconciliation_result.blocker
        blocker = self.observation_result.blocker
        return "" if blocker is None else blocker.value

    @property
    def local_journal_updated(self) -> bool:
        return bool(
            self.reconciliation_result is not None
            and self.reconciliation_result.local_journal_updated
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "workflow_version": (
                PAPER_CANCELLATION_RECONCILIATION_WORKFLOW_VERSION
            ),
            "status": self.status.value,
            "blocker": self.blocker,
            "identity": {
                "cancel_intent_id": self.identity.cancel_intent_id,
                "client_order_id": self.identity.client_order_id,
                "broker_order_id": self.identity.broker_order_id,
            },
            "authorization_id": self.observation_result.authorization_id,
            "exact_order_reader_invoked": (
                self.observation_result.read_callback_invoked
            ),
            "exact_order_read_count": self.observation_result.read_count,
            "observation_validated": self.observation_result.observed,
            "observation_result": self.observation_result.to_dict(),
            "reconciliation_invoked": self.reconciliation_result is not None,
            "injected_observation_consumed": (
                self.reconciliation_result is not None
            ),
            "local_journal_updated": self.local_journal_updated,
            "reconciliation_result": (
                {}
                if self.reconciliation_result is None
                else self.reconciliation_result.to_dict()
            ),
            "retry_permitted": False,
            "safe_to_recancel": False,
            "target_selection_performed": False,
            "polling_performed": False,
            "runtime_control_changed": False,
            "credential_values_accessed_by_workflow": False,
            "network_client_constructed_by_workflow": False,
            "broker_sdk_imported_by_workflow": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "replace_attempted": False,
            "close_attempted": False,
            "liquidation_attempted": False,
            "live_authorized": False,
        }


def reconcile_exact_paper_cancellation(
    journal: SqliteOrderJournal,
    identity: CancellationReconciliationIdentity,
    authorization: PaperCancellationObservationAuthorization | None,
    request: PaperCancellationObservationRequest,
    *,
    read_exact_order: ExactOrderReader,
) -> PaperCancellationReconciliationWorkflowResult:
    """Read and reconcile one exact cancellation target at most once."""

    if not isinstance(journal, SqliteOrderJournal):
        raise ValidationError("journal must be a SqliteOrderJournal.")
    if not isinstance(identity, CancellationReconciliationIdentity):
        raise ValidationError(
            "identity must be a CancellationReconciliationIdentity."
        )
    if authorization is not None and not isinstance(
        authorization,
        PaperCancellationObservationAuthorization,
    ):
        raise ValidationError(
            "authorization must be a PaperCancellationObservationAuthorization or None."
        )
    if not isinstance(request, PaperCancellationObservationRequest):
        raise ValidationError(
            "request must be a PaperCancellationObservationRequest."
        )
    if not callable(read_exact_order):
        raise ValidationError("read_exact_order must be callable.")

    observation_result = observe_exact_paper_cancellation(
        identity,
        authorization,
        request,
        read_exact_order=read_exact_order,
    )
    if not observation_result.observed:
        return PaperCancellationReconciliationWorkflowResult(
            identity=identity,
            observation_result=observation_result,
            reconciliation_result=None,
            status=(
                PaperCancellationReconciliationWorkflowStatus.OBSERVATION_BLOCKED
            ),
        )

    observation = observation_result.observation
    if observation is None:
        raise ValidationError(
            "observed result must contain a reconciliation observation."
        )
    reconciliation_result = reconcile_unresolved_cancellation(
        journal,
        identity,
        observation,
    )
    status = (
        PaperCancellationReconciliationWorkflowStatus.CONVERGED
        if reconciliation_result.status
        is CancellationReconciliationStatus.CONVERGED
        else PaperCancellationReconciliationWorkflowStatus.RECONCILIATION_BLOCKED
    )
    return PaperCancellationReconciliationWorkflowResult(
        identity=identity,
        observation_result=observation_result,
        reconciliation_result=reconciliation_result,
        status=status,
    )


__all__ = [
    "PAPER_CANCELLATION_RECONCILIATION_WORKFLOW_VERSION",
    "PaperCancellationReconciliationWorkflowResult",
    "PaperCancellationReconciliationWorkflowStatus",
    "reconcile_exact_paper_cancellation",
]
