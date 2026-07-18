"""Pure exact-local-target checks for cancellation reconciliation.

This module validates already-loaded journal records only. It performs no I/O,
does not own a journal, and exposes no broker, credential, network, runtime
control, target-selection, or mutation capability.
"""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
)
from algotrader.execution.order_journal import (
    CancelJournalRecord,
    CancelJournalState,
    OrderJournalRecord,
)


_RECONCILIATION_READY_CANCEL_STATES = frozenset(
    {
        CancelJournalState.CANCEL_ATTEMPTED,
        CancelJournalState.UNKNOWN,
        CancelJournalState.CANCEL_ACCEPTED,
    }
)


def paper_cancellation_reconciliation_local_target_blocker(
    identity: CancellationReconciliationIdentity,
    *,
    order_record: OrderJournalRecord | None,
    cancel_record: CancelJournalRecord | None,
) -> str:
    """Return the exact local target blocker or an empty ready value."""

    if not isinstance(identity, CancellationReconciliationIdentity):
        raise ValidationError(
            "identity must be a CancellationReconciliationIdentity."
        )
    if order_record is not None and not isinstance(
        order_record,
        OrderJournalRecord,
    ):
        raise ValidationError("order_record must be an OrderJournalRecord or None.")
    if cancel_record is not None and not isinstance(
        cancel_record,
        CancelJournalRecord,
    ):
        raise ValidationError(
            "cancel_record must be a CancelJournalRecord or None."
        )

    if order_record is None:
        return "order_journal_record_missing"
    if cancel_record is None:
        return "cancel_intent_missing"
    if order_record.broker_order_id != identity.broker_order_id:
        return "order_broker_identity_mismatch"
    if cancel_record.client_order_id != identity.client_order_id:
        return "cancel_client_order_identity_mismatch"
    if cancel_record.broker_order_id != identity.broker_order_id:
        return "cancel_broker_order_identity_mismatch"
    if cancel_record.terminal:
        return "cancel_intent_already_terminal"
    if cancel_record.state not in _RECONCILIATION_READY_CANCEL_STATES:
        return "cancel_intent_not_reconciliation_ready"
    return ""


__all__ = ["paper_cancellation_reconciliation_local_target_blocker"]
