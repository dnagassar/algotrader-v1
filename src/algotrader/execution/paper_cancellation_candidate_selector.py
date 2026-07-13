"""Deterministic broker-free cancellation candidate selection."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.execution.order_journal import OrderJournalRecord, OrderJournalState
from algotrader.orchestration.cancellation_planning_flow import (
    CANCELABLE_CANCELLATION_STATUSES,
)


_KNOWN_NONCANCELABLE_STATUSES = frozenset(
    {
        "calculated",
        "canceled",
        "cancelled",
        "done_for_day",
        "expired",
        "filled",
        "held",
        "open",
        "pending_cancel",
        "pending_replace",
        "rejected",
        "replaced",
        "stopped",
        "suspended",
    }
)


class CancellationCandidateSelectionStatus(StrEnum):
    SELECTED = "selected"
    BLOCKED = "blocked"


class CancellationCandidateSelectionBlocker(StrEnum):
    STOP_REQUESTED = "stop_requested"
    TRADING_PAUSED = "trading_paused"
    PLANNING_NOT_PERMITTED = "planning_not_permitted"
    NO_CANDIDATE = "no_candidate"
    MULTIPLE_ELIGIBLE_CANDIDATES = "multiple_eligible_candidates"
    DUPLICATE_BROKER_IDENTITY = "duplicate_broker_identity"
    RECORD_TIMESTAMP_INVALID = "record_timestamp_invalid"
    FUTURE_RECORD_TIMESTAMP = "future_record_timestamp"
    RECORD_TIMESTAMP_INCONSISTENT = "record_timestamp_inconsistent"
    IDENTITY_INCOMPLETE = "identity_incomplete"
    TERMINAL_RECORDS_ONLY = "terminal_records_only"
    UNKNOWN_RECORD_STATE = "unknown_record_state"


@dataclass(frozen=True, slots=True)
class CancellationCandidateSelectionRequest:
    symbol: str
    as_of: datetime
    minimum_open_age_seconds: int
    reason: str
    planning_permitted: bool
    trading_enabled: bool
    stop_requested: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        try:
            as_of = require_utc_datetime(self.as_of)
        except ValidationError as exc:
            raise ValidationError(
                "as_of must be a timezone-aware UTC datetime."
            ) from exc
        object.__setattr__(self, "as_of", as_of)
        if (
            type(self.minimum_open_age_seconds) is not int
            or self.minimum_open_age_seconds <= 0
        ):
            raise ValidationError(
                "minimum_open_age_seconds must be a positive integer."
            )
        reason = str(self.reason).strip()
        if not reason:
            raise ValidationError("reason is required.")
        object.__setattr__(self, "reason", reason)
        for field_name in (
            "planning_permitted",
            "trading_enabled",
            "stop_requested",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")


@dataclass(frozen=True, slots=True)
class CancellationCandidate:
    client_order_id: str
    broker_order_id: str
    symbol: str
    broker_status: str
    created_at: datetime
    observed_at: datetime
    open_age_seconds: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
            "broker_status": self.broker_status,
            "created_at": self.created_at.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "open_age_seconds": self.open_age_seconds,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class CancellationCandidateSelectionResult:
    status: CancellationCandidateSelectionStatus
    candidate: CancellationCandidate | None
    blocker: CancellationCandidateSelectionBlocker | None
    considered_count: int
    eligible_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.status, CancellationCandidateSelectionStatus):
            raise ValidationError(
                "status must be a CancellationCandidateSelectionStatus."
            )
        if self.status is CancellationCandidateSelectionStatus.SELECTED:
            if not isinstance(self.candidate, CancellationCandidate):
                raise ValidationError("selected result requires one candidate.")
            if self.blocker is not None or self.eligible_count != 1:
                raise ValidationError(
                    "selected result requires no blocker and one eligible candidate."
                )
        elif self.candidate is not None or not isinstance(
            self.blocker,
            CancellationCandidateSelectionBlocker,
        ):
            raise ValidationError(
                "blocked result requires one typed blocker and no candidate."
            )
        for field_name in ("considered_count", "eligible_count"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValidationError(f"{field_name} must be a non-negative integer.")

    @property
    def selected(self) -> bool:
        return self.status is CancellationCandidateSelectionStatus.SELECTED

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "blocker": "" if self.blocker is None else self.blocker.value,
            "considered_count": self.considered_count,
            "eligible_count": self.eligible_count,
            "candidate": (
                {} if self.candidate is None else self.candidate.to_dict()
            ),
        }


def select_cancellation_candidate(
    records: Iterable[OrderJournalRecord],
    request: CancellationCandidateSelectionRequest,
) -> CancellationCandidateSelectionResult:
    """Select exactly one eligible local record or return one typed blocker."""

    if not isinstance(request, CancellationCandidateSelectionRequest):
        raise ValidationError(
            "request must be a CancellationCandidateSelectionRequest."
        )
    values = tuple(records)
    if any(not isinstance(record, OrderJournalRecord) for record in values):
        raise ValidationError("records must contain only OrderJournalRecord values.")
    matching = tuple(
        sorted(
            (record for record in values if record.symbol == request.symbol),
            key=_record_identity,
        )
    )
    considered_count = len(matching)

    if request.stop_requested:
        return _blocked(
            CancellationCandidateSelectionBlocker.STOP_REQUESTED,
            considered_count,
        )
    if not request.trading_enabled:
        return _blocked(
            CancellationCandidateSelectionBlocker.TRADING_PAUSED,
            considered_count,
        )
    if not request.planning_permitted:
        return _blocked(
            CancellationCandidateSelectionBlocker.PLANNING_NOT_PERMITTED,
            considered_count,
        )
    if not matching:
        return _blocked(
            CancellationCandidateSelectionBlocker.NO_CANDIDATE,
            considered_count,
        )
    if any(not _valid_record_timestamp(record) for record in matching):
        return _blocked(
            CancellationCandidateSelectionBlocker.RECORD_TIMESTAMP_INVALID,
            considered_count,
        )
    if any(record.created_at > record.updated_at for record in matching):
        return _blocked(
            CancellationCandidateSelectionBlocker.RECORD_TIMESTAMP_INCONSISTENT,
            considered_count,
        )
    if any(
        record.created_at > request.as_of or record.updated_at > request.as_of
        for record in matching
    ):
        return _blocked(
            CancellationCandidateSelectionBlocker.FUTURE_RECORD_TIMESTAMP,
            considered_count,
        )
    broker_ids = [record.broker_order_id.strip() for record in matching]
    broker_id_counts = Counter(value for value in broker_ids if value)
    if any(count > 1 for count in broker_id_counts.values()):
        return _blocked(
            CancellationCandidateSelectionBlocker.DUPLICATE_BROKER_IDENTITY,
            considered_count,
        )
    if any(_unknown_record(record) for record in matching):
        return _blocked(
            CancellationCandidateSelectionBlocker.UNKNOWN_RECORD_STATE,
            considered_count,
        )

    aged_cancelable = tuple(
        record
        for record in matching
        if not record.terminal
        and _normalized_status(record.broker_status)
        in CANCELABLE_CANCELLATION_STATUSES
        and _open_age_seconds(record, request.as_of)
        >= request.minimum_open_age_seconds
    )
    if any(
        not record.client_order_id.strip() or not record.broker_order_id.strip()
        for record in aged_cancelable
    ):
        return _blocked(
            CancellationCandidateSelectionBlocker.IDENTITY_INCOMPLETE,
            considered_count,
            eligible_count=len(aged_cancelable),
        )
    eligible = tuple(
        record
        for record in aged_cancelable
        if record.client_order_id.strip() and record.broker_order_id.strip()
    )
    if len(eligible) > 1:
        return _blocked(
            CancellationCandidateSelectionBlocker.MULTIPLE_ELIGIBLE_CANDIDATES,
            considered_count,
            eligible_count=len(eligible),
        )
    if not eligible:
        blocker = (
            CancellationCandidateSelectionBlocker.TERMINAL_RECORDS_ONLY
            if all(record.terminal for record in matching)
            else CancellationCandidateSelectionBlocker.NO_CANDIDATE
        )
        return _blocked(blocker, considered_count)

    selected = eligible[0]
    return CancellationCandidateSelectionResult(
        status=CancellationCandidateSelectionStatus.SELECTED,
        candidate=CancellationCandidate(
            client_order_id=selected.client_order_id,
            broker_order_id=selected.broker_order_id,
            symbol=selected.symbol,
            broker_status=_normalized_status(selected.broker_status),
            created_at=selected.created_at,
            observed_at=selected.updated_at,
            open_age_seconds=_open_age_seconds(selected, request.as_of),
            reason=request.reason,
        ),
        blocker=None,
        considered_count=considered_count,
        eligible_count=1,
    )


def _blocked(
    blocker: CancellationCandidateSelectionBlocker,
    considered_count: int,
    eligible_count: int = 0,
) -> CancellationCandidateSelectionResult:
    return CancellationCandidateSelectionResult(
        status=CancellationCandidateSelectionStatus.BLOCKED,
        candidate=None,
        blocker=blocker,
        considered_count=considered_count,
        eligible_count=eligible_count,
    )


def _unknown_record(record: OrderJournalRecord) -> bool:
    status = _normalized_status(record.broker_status)
    return not record.terminal and (
        not isinstance(record.state, OrderJournalState)
        or record.state is OrderJournalState.UNKNOWN
        or status not in (
            CANCELABLE_CANCELLATION_STATUSES | _KNOWN_NONCANCELABLE_STATUSES
        )
    )


def _valid_record_timestamp(record: OrderJournalRecord) -> bool:
    try:
        require_utc_datetime(record.created_at)
        require_utc_datetime(record.updated_at)
    except ValidationError:
        return False
    return True


def _open_age_seconds(record: OrderJournalRecord, as_of: datetime) -> int:
    return int((as_of - record.created_at).total_seconds())


def _record_identity(record: OrderJournalRecord) -> tuple[str, str, str, str]:
    return (
        record.client_order_id,
        record.broker_order_id,
        record.created_at.isoformat(),
        record.updated_at.isoformat(),
    )


def _normalized_status(value: object) -> str:
    text = str(value).strip().lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")


__all__ = [
    "CancellationCandidate",
    "CancellationCandidateSelectionBlocker",
    "CancellationCandidateSelectionRequest",
    "CancellationCandidateSelectionResult",
    "CancellationCandidateSelectionStatus",
    "select_cancellation_candidate",
]
