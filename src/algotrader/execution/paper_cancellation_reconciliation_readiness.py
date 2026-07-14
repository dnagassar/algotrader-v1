"""Credential-free readiness receipt for exact cancellation reconciliation.

The receipt validates one existing authorization artifact, one explicit target,
and the named local journal records. It never reads environment configuration,
loads credentials, constructs a broker reader, accesses a network, selects a
target, changes runtime control, or mutates broker or journal state.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
)
from algotrader.execution.order_journal import SqliteOrderJournal
from algotrader.execution.paper_cancellation_authorization_artifact import (
    load_paper_cancellation_observation_authorization,
)
from algotrader.execution.paper_cancellation_observation import (
    PaperCancellationObservationAuthorization,
    paper_cancellation_authorization_blocker,
)
from algotrader.execution.paper_cancellation_reconciliation_local import (
    paper_cancellation_reconciliation_local_target_blocker,
)


PAPER_CANCELLATION_RECONCILIATION_READINESS_VERSION = (
    "paper_cancellation_reconciliation_readiness_v1"
)

class PaperCancellationReconciliationReadinessStatus(StrEnum):
    BLOCKED = "blocked"
    READY = "ready"


@dataclass(frozen=True, slots=True)
class PaperCancellationReconciliationReadinessRequest:
    authorization_artifact_path: Path | str
    journal_path: Path | str
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    expected_authorization_id: str
    occurred_at: datetime
    expected_account_id: str = field(default="", repr=False)
    offline_readiness_permitted: bool = False

    def __post_init__(self) -> None:
        for field_name in ("authorization_artifact_path", "journal_path"):
            object.__setattr__(
                self,
                field_name,
                _local_path(getattr(self, field_name), field_name),
            )
        for field_name in (
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
            "expected_authorization_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "occurred_at",
            _utc_datetime(self.occurred_at, "occurred_at"),
        )
        object.__setattr__(
            self,
            "expected_account_id",
            _required(self.expected_account_id, "expected_account_id"),
        )
        if type(self.offline_readiness_permitted) is not bool:
            raise ValidationError("offline_readiness_permitted must be a boolean.")

    @property
    def identity(self) -> CancellationReconciliationIdentity:
        return CancellationReconciliationIdentity(
            cancel_intent_id=self.cancel_intent_id,
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "authorization_artifact_path_configured": True,
            "journal_path": str(self.journal_path),
            "cancel_intent_id": self.cancel_intent_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "expected_authorization_id": self.expected_authorization_id,
            "occurred_at": self.occurred_at.isoformat(),
            "expected_account_configured": True,
            "offline_readiness_permitted": self.offline_readiness_permitted,
        }


@dataclass(frozen=True, slots=True)
class PaperCancellationReconciliationReadinessResult:
    request: PaperCancellationReconciliationReadinessRequest
    status: PaperCancellationReconciliationReadinessStatus
    blocker: str
    authorization_artifact_loaded: bool
    authorization_evidence_checked: bool
    authorization_evidence_matched: bool
    journal_path_checked: bool
    local_target_checked: bool
    order_state: str = ""
    cancel_intent_state: str = ""
    error_type: str = ""

    def __post_init__(self) -> None:
        if not isinstance(
            self.request,
            PaperCancellationReconciliationReadinessRequest,
        ):
            raise ValidationError(
                "request must be a PaperCancellationReconciliationReadinessRequest."
            )
        if not isinstance(
            self.status,
            PaperCancellationReconciliationReadinessStatus,
        ):
            raise ValidationError(
                "status must be a PaperCancellationReconciliationReadinessStatus."
            )
        for field_name in (
            "authorization_artifact_loaded",
            "authorization_evidence_checked",
            "authorization_evidence_matched",
            "journal_path_checked",
            "local_target_checked",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        for field_name in (
            "blocker",
            "order_state",
            "cancel_intent_state",
            "error_type",
        ):
            object.__setattr__(
                self,
                field_name,
                str(getattr(self, field_name)).strip(),
            )
        if self.authorization_evidence_matched and not (
            self.authorization_artifact_loaded
            and self.authorization_evidence_checked
        ):
            raise ValidationError(
                "matched authorization requires a loaded and checked artifact."
            )
        if self.local_target_checked and not self.journal_path_checked:
            raise ValidationError(
                "local target check requires a checked journal path."
            )
        if self.status is PaperCancellationReconciliationReadinessStatus.READY:
            if (
                self.blocker
                or not self.authorization_evidence_matched
                or not self.journal_path_checked
                or not self.local_target_checked
                or not self.order_state
                or not self.cancel_intent_state
            ):
                raise ValidationError(
                    "ready receipt requires exact authorization and local target evidence."
                )
        elif not self.blocker:
            raise ValidationError("blocked readiness receipt requires one blocker.")

    def to_dict(self) -> dict[str, object]:
        ready = self.status is PaperCancellationReconciliationReadinessStatus.READY
        return {
            "readiness_version": (
                PAPER_CANCELLATION_RECONCILIATION_READINESS_VERSION
            ),
            "status": self.status.value,
            "blocker": self.blocker,
            "request": self.request.to_dict(),
            "authorization_artifact_loaded": self.authorization_artifact_loaded,
            "authorization_evidence_checked": self.authorization_evidence_checked,
            "authorization_evidence_matched": self.authorization_evidence_matched,
            "authorization_minted": False,
            "journal_path_checked": self.journal_path_checked,
            "local_target_checked": self.local_target_checked,
            "order_state": self.order_state,
            "cancel_intent_state": self.cancel_intent_state,
            "offline_inputs_ready": ready,
            "ready_for_exact_read_command": ready,
            "all_exact_read_preconditions_verified": False,
            "external_operator_gates_satisfied": False,
            "expected_account_verified": False,
            "paper_configuration_loaded": False,
            "environment_read": False,
            "credentials_accessed": False,
            "credential_values_serialized": False,
            "network_access_authorized": False,
            "network_accessed": False,
            "broker_client_constructed": False,
            "broker_read_authorized": False,
            "broker_read_performed": False,
            "operator_binding_authorized": False,
            "operator_binding_invoked": False,
            "local_journal_updated": False,
            "runtime_control_changed": False,
            "retry_permitted": False,
            "safe_to_recancel": False,
            "target_selection_performed": False,
            "unresolved_intents_enumerated": False,
            "polling_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "replace_attempted": False,
            "close_attempted": False,
            "liquidation_attempted": False,
            "live_authorized": False,
            "error_type": self.error_type,
        }


def build_exact_paper_cancellation_reconciliation_readiness(
    request: PaperCancellationReconciliationReadinessRequest,
) -> PaperCancellationReconciliationReadinessResult:
    """Build one offline readiness receipt without changing any state."""

    if not isinstance(request, PaperCancellationReconciliationReadinessRequest):
        raise ValidationError(
            "request must be a PaperCancellationReconciliationReadinessRequest."
        )
    if not request.offline_readiness_permitted:
        return _blocked(request, "offline_readiness_not_permitted")

    try:
        authorization = load_paper_cancellation_observation_authorization(
            request.authorization_artifact_path
        )
        if not isinstance(
            authorization,
            PaperCancellationObservationAuthorization,
        ):
            raise ValidationError(
                "authorization loader returned an invalid authorization."
            )
    except Exception as exc:
        return _blocked(
            request,
            "authorization_artifact_invalid",
            error_type=exc.__class__.__name__,
        )

    try:
        authorization_blocker = paper_cancellation_authorization_blocker(
            request.identity,
            authorization,
            expected_authorization_id=request.expected_authorization_id,
            occurred_at=request.occurred_at,
        )
    except Exception as exc:
        return _blocked(
            request,
            "authorization_evidence_invalid",
            authorization_artifact_loaded=True,
            authorization_evidence_checked=True,
            error_type=exc.__class__.__name__,
        )
    if authorization_blocker is not None:
        return _blocked(
            request,
            authorization_blocker.value,
            authorization_artifact_loaded=True,
            authorization_evidence_checked=True,
        )

    journal_path = Path(request.journal_path)
    if not journal_path.is_file():
        return _blocked(
            request,
            "local_journal_path_missing",
            authorization_artifact_loaded=True,
            authorization_evidence_checked=True,
            authorization_evidence_matched=True,
            journal_path_checked=True,
        )
    try:
        journal = SqliteOrderJournal(journal_path)
        if not isinstance(journal, SqliteOrderJournal):
            raise ValidationError(
                "journal_factory must return a SqliteOrderJournal."
            )
        order_record = journal.get(request.client_order_id)
        cancel_record = journal.get_cancel_intent(request.cancel_intent_id)
    except Exception as exc:
        return _blocked(
            request,
            "local_journal_unavailable",
            authorization_artifact_loaded=True,
            authorization_evidence_checked=True,
            authorization_evidence_matched=True,
            journal_path_checked=True,
            error_type=exc.__class__.__name__,
        )

    order_state = "" if order_record is None else order_record.state.value
    cancel_state = "" if cancel_record is None else cancel_record.state.value
    try:
        local_blocker = paper_cancellation_reconciliation_local_target_blocker(
            request.identity,
            order_record=order_record,
            cancel_record=cancel_record,
        )
    except Exception as exc:
        return _blocked(
            request,
            "local_target_invalid",
            authorization_artifact_loaded=True,
            authorization_evidence_checked=True,
            authorization_evidence_matched=True,
            journal_path_checked=True,
            local_target_checked=True,
            order_state=order_state,
            cancel_intent_state=cancel_state,
            error_type=exc.__class__.__name__,
        )
    if local_blocker:
        return _blocked(
            request,
            local_blocker,
            authorization_artifact_loaded=True,
            authorization_evidence_checked=True,
            authorization_evidence_matched=True,
            journal_path_checked=True,
            local_target_checked=True,
            order_state=order_state,
            cancel_intent_state=cancel_state,
        )

    return PaperCancellationReconciliationReadinessResult(
        request=request,
        status=PaperCancellationReconciliationReadinessStatus.READY,
        blocker="",
        authorization_artifact_loaded=True,
        authorization_evidence_checked=True,
        authorization_evidence_matched=True,
        journal_path_checked=True,
        local_target_checked=True,
        order_state=order_state,
        cancel_intent_state=cancel_state,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "python -m "
            "algotrader.execution.paper_cancellation_reconciliation_readiness"
        ),
        description=(
            "Build one credential-free readiness receipt for an exactly "
            "identified paper cancellation reconciliation."
        ),
    )
    parser.add_argument("--authorization-artifact", required=True)
    parser.add_argument("--journal-path", required=True)
    parser.add_argument("--cancel-intent-id", required=True)
    parser.add_argument("--client-order-id", required=True)
    parser.add_argument("--broker-order-id", required=True)
    parser.add_argument("--expected-authorization-id", required=True)
    parser.add_argument("--expected-paper-account-id", required=True)
    parser.add_argument("--occurred-at", required=True, type=_utc_argument)
    parser.add_argument("--allow-offline-readiness", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request = PaperCancellationReconciliationReadinessRequest(
            authorization_artifact_path=args.authorization_artifact,
            journal_path=args.journal_path,
            cancel_intent_id=args.cancel_intent_id,
            client_order_id=args.client_order_id,
            broker_order_id=args.broker_order_id,
            expected_authorization_id=args.expected_authorization_id,
            occurred_at=args.occurred_at,
            expected_account_id=args.expected_paper_account_id,
            offline_readiness_permitted=args.allow_offline_readiness,
        )
    except (TypeError, ValueError, ValidationError) as exc:
        print(json.dumps(_invalid_request_payload(exc), sort_keys=True, indent=2))
        return 2

    result = build_exact_paper_cancellation_reconciliation_readiness(request)
    print(json.dumps(result.to_dict(), sort_keys=True, indent=2))
    return (
        0
        if result.status is PaperCancellationReconciliationReadinessStatus.READY
        else 2
    )


def _blocked(
    request: PaperCancellationReconciliationReadinessRequest,
    blocker: str,
    *,
    authorization_artifact_loaded: bool = False,
    authorization_evidence_checked: bool = False,
    authorization_evidence_matched: bool = False,
    journal_path_checked: bool = False,
    local_target_checked: bool = False,
    order_state: str = "",
    cancel_intent_state: str = "",
    error_type: str = "",
) -> PaperCancellationReconciliationReadinessResult:
    return PaperCancellationReconciliationReadinessResult(
        request=request,
        status=PaperCancellationReconciliationReadinessStatus.BLOCKED,
        blocker=_required(blocker, "blocker"),
        authorization_artifact_loaded=authorization_artifact_loaded,
        authorization_evidence_checked=authorization_evidence_checked,
        authorization_evidence_matched=authorization_evidence_matched,
        journal_path_checked=journal_path_checked,
        local_target_checked=local_target_checked,
        order_state=order_state,
        cancel_intent_state=cancel_intent_state,
        error_type=error_type,
    )


def _invalid_request_payload(exc: Exception) -> dict[str, object]:
    return {
        "readiness_version": PAPER_CANCELLATION_RECONCILIATION_READINESS_VERSION,
        "status": "invalid_request",
        "blocker": "readiness_request_invalid",
        "authorization_artifact_loaded": False,
        "authorization_minted": False,
        "journal_path_checked": False,
        "local_target_checked": False,
        "offline_inputs_ready": False,
        "ready_for_exact_read_command": False,
        "all_exact_read_preconditions_verified": False,
        "external_operator_gates_satisfied": False,
        "paper_configuration_loaded": False,
        "environment_read": False,
        "credentials_accessed": False,
        "credential_values_serialized": False,
        "network_access_authorized": False,
        "network_accessed": False,
        "broker_client_constructed": False,
        "broker_read_authorized": False,
        "broker_read_performed": False,
        "operator_binding_authorized": False,
        "operator_binding_invoked": False,
        "local_journal_updated": False,
        "runtime_control_changed": False,
        "retry_permitted": False,
        "broker_mutation_authorized": False,
        "broker_mutation_performed": False,
        "live_authorized": False,
        "error_type": exc.__class__.__name__,
    }


def _utc_argument(value: str) -> datetime:
    try:
        return _utc_datetime(datetime.fromisoformat(value), "occurred_at")
    except (TypeError, ValueError, ValidationError) as exc:
        raise argparse.ArgumentTypeError(
            "occurred-at must be a timezone-aware canonical UTC timestamp."
        ) from exc


def _required(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _local_path(value: object, field_name: str) -> Path:
    text = _required(value, field_name)
    if text.startswith(("\\\\", "//")):
        raise ValidationError(f"{field_name} must be a local filesystem path.")
    return Path(text)


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except (TypeError, ValidationError) as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PAPER_CANCELLATION_RECONCILIATION_READINESS_VERSION",
    "PaperCancellationReconciliationReadinessRequest",
    "PaperCancellationReconciliationReadinessResult",
    "PaperCancellationReconciliationReadinessStatus",
    "build_exact_paper_cancellation_reconciliation_readiness",
    "build_parser",
    "main",
]
