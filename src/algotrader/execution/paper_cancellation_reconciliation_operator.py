"""Default-disabled operator binding for exact cancellation reconciliation.

The caller supplies an existing immutable authorization and explicit target.
This module derives paper/credential/endpoint evidence from injected config,
checks the exact local journal target, builds one private reader, and invokes
the one-shot reconciliation workflow. It never reads environment variables,
mints authorization, selects a target, polls, retries, or mutates a broker.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
)
from algotrader.execution.order_journal import (
    SqliteOrderJournal,
)
from algotrader.execution.paper_cancellation_observation import (
    PaperCancellationObservationAuthorization,
    PaperCancellationObservationRequest,
    paper_cancellation_observation_blocker,
)
from algotrader.execution.paper_cancellation_observation_sdk import (
    ObservationClock,
    PaperCancellationObservationClientFactory,
    build_paper_cancellation_sdk_reader,
)
from algotrader.execution.paper_cancellation_reconciliation_workflow import (
    PaperCancellationReconciliationWorkflowResult,
    PaperCancellationReconciliationWorkflowStatus,
    reconcile_exact_paper_cancellation,
)
from algotrader.execution.paper_cancellation_reconciliation_local import (
    paper_cancellation_reconciliation_local_target_blocker,
)


PAPER_CANCELLATION_RECONCILIATION_OPERATOR_VERSION = (
    "paper_cancellation_reconciliation_operator_v1"
)

_LIVE_ENDPOINTS = frozenset(
    {
        "http://api.alpaca.markets",
        "https://api.alpaca.markets",
    }
)
JournalFactory = Callable[[Path], SqliteOrderJournal]


class PaperCancellationReconciliationOperatorStatus(StrEnum):
    BLOCKED_BEFORE_READER = "blocked_before_reader"
    WORKFLOW_BLOCKED = "workflow_blocked"
    CONVERGED = "converged"


@dataclass(frozen=True, slots=True)
class PaperCancellationReconciliationOperatorRequest:
    journal_path: Path | str
    cancel_intent_id: str
    client_order_id: str
    broker_order_id: str
    expected_authorization_id: str
    occurred_at: datetime
    expected_account_id: str = field(default="", repr=False)
    operator_binding_permitted: bool = False
    network_access_permitted: bool = False

    def __post_init__(self) -> None:
        raw_journal_path = str(self.journal_path).strip()
        if not raw_journal_path:
            raise ValidationError("journal_path is required.")
        object.__setattr__(self, "journal_path", Path(raw_journal_path))
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
            str(self.expected_account_id).strip(),
        )
        for field_name in (
            "operator_binding_permitted",
            "network_access_permitted",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")

    @property
    def identity(self) -> CancellationReconciliationIdentity:
        return CancellationReconciliationIdentity(
            cancel_intent_id=self.cancel_intent_id,
            client_order_id=self.client_order_id,
            broker_order_id=self.broker_order_id,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "journal_path": str(self.journal_path),
            "cancel_intent_id": self.cancel_intent_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "expected_authorization_id": self.expected_authorization_id,
            "occurred_at": self.occurred_at.isoformat(),
            "expected_account_configured": bool(self.expected_account_id),
            "operator_binding_permitted": self.operator_binding_permitted,
            "network_access_permitted": self.network_access_permitted,
        }


@dataclass(frozen=True, slots=True)
class PaperCancellationReconciliationOperatorResult:
    request: PaperCancellationReconciliationOperatorRequest
    observation_request: PaperCancellationObservationRequest
    status: PaperCancellationReconciliationOperatorStatus
    blocker: str
    local_target_checked: bool
    reader_constructed: bool
    workflow_result: PaperCancellationReconciliationWorkflowResult | None = None
    error_type: str = ""

    def __post_init__(self) -> None:
        if not isinstance(
            self.request,
            PaperCancellationReconciliationOperatorRequest,
        ):
            raise ValidationError(
                "request must be a PaperCancellationReconciliationOperatorRequest."
            )
        if not isinstance(
            self.observation_request,
            PaperCancellationObservationRequest,
        ):
            raise ValidationError(
                "observation_request must be a PaperCancellationObservationRequest."
            )
        if not isinstance(
            self.status,
            PaperCancellationReconciliationOperatorStatus,
        ):
            raise ValidationError(
                "status must be a PaperCancellationReconciliationOperatorStatus."
            )
        for field_name in ("local_target_checked", "reader_constructed"):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        object.__setattr__(self, "blocker", str(self.blocker).strip())
        object.__setattr__(self, "error_type", str(self.error_type).strip())
        if self.workflow_result is not None and not isinstance(
            self.workflow_result,
            PaperCancellationReconciliationWorkflowResult,
        ):
            raise ValidationError(
                "workflow_result must be a "
                "PaperCancellationReconciliationWorkflowResult or None."
            )

        if (
            self.status
            is PaperCancellationReconciliationOperatorStatus.BLOCKED_BEFORE_READER
        ):
            if not self.blocker or self.reader_constructed or self.workflow_result:
                raise ValidationError(
                    "pre-reader block requires one blocker and no reader/workflow."
                )
        elif (
            self.status
            is PaperCancellationReconciliationOperatorStatus.WORKFLOW_BLOCKED
        ):
            if (
                not self.blocker
                or not self.reader_constructed
                or self.workflow_result is None
                or self.workflow_result.status
                is PaperCancellationReconciliationWorkflowStatus.CONVERGED
            ):
                raise ValidationError(
                    "workflow block requires a constructed reader and blocked result."
                )
        elif (
            self.blocker
            or not self.local_target_checked
            or not self.reader_constructed
            or self.workflow_result is None
            or self.workflow_result.status
            is not PaperCancellationReconciliationWorkflowStatus.CONVERGED
        ):
            raise ValidationError(
                "converged operator result requires exact local and workflow success."
            )

    def to_dict(self) -> dict[str, object]:
        workflow_payload = (
            {} if self.workflow_result is None else self.workflow_result.to_dict()
        )
        exact_order_reader_invoked = bool(
            self.workflow_result is not None
            and self.workflow_result.observation_result.read_callback_invoked
        )
        return {
            "operator_version": (
                PAPER_CANCELLATION_RECONCILIATION_OPERATOR_VERSION
            ),
            "status": self.status.value,
            "blocker": self.blocker,
            "request": self.request.to_dict(),
            "observation_gate": self.observation_request.to_dict(),
            "authorization_minted": False,
            "preexisting_authorization_evaluated": True,
            "local_target_checked": self.local_target_checked,
            "read_client_constructed": self.reader_constructed,
            "workflow_invoked": self.workflow_result is not None,
            "exact_order_reader_invoked": exact_order_reader_invoked,
            "workflow_result": workflow_payload,
            "local_journal_updated": bool(
                self.workflow_result is not None
                and self.workflow_result.local_journal_updated
            ),
            "error_type": self.error_type,
            "retry_permitted": False,
            "safe_to_recancel": False,
            "target_selection_performed": False,
            "unresolved_intents_enumerated": False,
            "polling_performed": False,
            "environment_read": False,
            "credential_values_serialized": False,
            "runtime_control_changed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "replace_attempted": False,
            "close_attempted": False,
            "liquidation_attempted": False,
            "live_authorized": False,
        }


def run_exact_paper_cancellation_reconciliation_operator(
    config: AlpacaPaperConfig,
    authorization: PaperCancellationObservationAuthorization | None,
    request: PaperCancellationReconciliationOperatorRequest,
    *,
    client_factory: PaperCancellationObservationClientFactory | None = None,
    reader_clock: ObservationClock | None = None,
    journal_factory: JournalFactory = SqliteOrderJournal,
) -> PaperCancellationReconciliationOperatorResult:
    """Run one pre-authorized exact reconciliation or fail closed."""

    if not isinstance(config, AlpacaPaperConfig):
        raise ValidationError("config must be an AlpacaPaperConfig.")
    if authorization is not None and not isinstance(
        authorization,
        PaperCancellationObservationAuthorization,
    ):
        raise ValidationError(
            "authorization must be a PaperCancellationObservationAuthorization or None."
        )
    if not isinstance(
        request,
        PaperCancellationReconciliationOperatorRequest,
    ):
        raise ValidationError(
            "request must be a PaperCancellationReconciliationOperatorRequest."
        )
    if client_factory is not None and not callable(client_factory):
        raise ValidationError("client_factory must be callable or None.")
    if reader_clock is not None and not callable(reader_clock):
        raise ValidationError("reader_clock must be callable or None.")
    if not callable(journal_factory):
        raise ValidationError("journal_factory must be callable.")

    identity = request.identity
    observation_request = _observation_request(config, request)
    blocker = paper_cancellation_observation_blocker(
        identity,
        authorization,
        observation_request,
    )
    if blocker is not None:
        return _blocked(
            request,
            observation_request,
            blocker.value,
        )

    journal_path = Path(request.journal_path)
    if not journal_path.is_file():
        return _blocked(
            request,
            observation_request,
            "local_journal_path_missing",
        )
    try:
        journal = journal_factory(journal_path)
        if not isinstance(journal, SqliteOrderJournal):
            raise ValidationError(
                "journal_factory must return a SqliteOrderJournal."
            )
        order_record = journal.get(identity.client_order_id)
        cancel_record = journal.get_cancel_intent(identity.cancel_intent_id)
    except Exception as exc:
        return _blocked(
            request,
            observation_request,
            "local_journal_unavailable",
            local_target_checked=True,
            error_type=exc.__class__.__name__,
        )

    local_blocker = paper_cancellation_reconciliation_local_target_blocker(
        identity,
        order_record=order_record,
        cancel_record=cancel_record,
    )
    if local_blocker:
        return _blocked(
            request,
            observation_request,
            local_blocker,
            local_target_checked=True,
        )

    try:
        reader = build_paper_cancellation_sdk_reader(
            config,
            identity,
            client_factory=client_factory,
            clock=reader_clock,
        )
    except Exception as exc:
        return _blocked(
            request,
            observation_request,
            "exact_reader_construction_failed",
            local_target_checked=True,
            error_type=exc.__class__.__name__,
        )

    workflow_result = reconcile_exact_paper_cancellation(
        journal,
        identity,
        authorization,
        observation_request,
        read_exact_order=reader,
    )
    status = (
        PaperCancellationReconciliationOperatorStatus.CONVERGED
        if workflow_result.status
        is PaperCancellationReconciliationWorkflowStatus.CONVERGED
        else PaperCancellationReconciliationOperatorStatus.WORKFLOW_BLOCKED
    )
    return PaperCancellationReconciliationOperatorResult(
        request=request,
        observation_request=observation_request,
        status=status,
        blocker=workflow_result.blocker,
        local_target_checked=True,
        reader_constructed=True,
        workflow_result=workflow_result,
    )


def _observation_request(
    config: AlpacaPaperConfig,
    request: PaperCancellationReconciliationOperatorRequest,
) -> PaperCancellationObservationRequest:
    endpoint = config.alpaca_paper_base_url.strip().lower().rstrip("/")
    return PaperCancellationObservationRequest(
        expected_authorization_id=request.expected_authorization_id,
        occurred_at=request.occurred_at,
        expected_account_id=request.expected_account_id,
        observation_permitted=request.operator_binding_permitted,
        network_access_permitted=request.network_access_permitted,
        paper_profile_ready=config.is_paper_profile,
        api_key_present=_present(config.alpaca_api_key),
        secret_key_present=_present(config.alpaca_secret_key),
        paper_endpoint_validated=(
            config.alpaca_paper_base_url == DEFAULT_ALPACA_PAPER_BASE_URL
        ),
        live_endpoint_detected=endpoint in _LIVE_ENDPOINTS,
    )


def _blocked(
    request: PaperCancellationReconciliationOperatorRequest,
    observation_request: PaperCancellationObservationRequest,
    blocker: str,
    *,
    local_target_checked: bool = False,
    error_type: str = "",
) -> PaperCancellationReconciliationOperatorResult:
    return PaperCancellationReconciliationOperatorResult(
        request=request,
        observation_request=observation_request,
        status=(
            PaperCancellationReconciliationOperatorStatus.BLOCKED_BEFORE_READER
        ),
        blocker=_required(blocker, "blocker"),
        local_target_checked=local_target_checked,
        reader_constructed=False,
        error_type=error_type,
    )


def _present(value: object) -> bool:
    return bool(str(value or "").strip())


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
    "PAPER_CANCELLATION_RECONCILIATION_OPERATOR_VERSION",
    "PaperCancellationReconciliationOperatorRequest",
    "PaperCancellationReconciliationOperatorResult",
    "PaperCancellationReconciliationOperatorStatus",
    "run_exact_paper_cancellation_reconciliation_operator",
]
