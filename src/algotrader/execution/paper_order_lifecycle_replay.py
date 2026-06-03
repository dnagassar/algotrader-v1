"""Pure offline replay of paper order lifecycle observations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


ORDER_LIFECYCLE_NOT_SEEN = "not_seen"
ORDER_LIFECYCLE_SUBMITTED_SEEN = "submitted_seen"
ORDER_LIFECYCLE_ACCEPTED_OPEN_UNFILLED = "accepted_open_unfilled"
ORDER_LIFECYCLE_PARTIALLY_FILLED_OPEN = "partially_filled_open"
ORDER_LIFECYCLE_FILLED_TERMINAL = "filled_terminal"
ORDER_LIFECYCLE_REJECTED_TERMINAL = "rejected_terminal"
ORDER_LIFECYCLE_CANCELED_TERMINAL = "canceled_terminal"
ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT = "ambiguous_after_submit"
ORDER_LIFECYCLE_INCONSISTENT = "inconsistent_lifecycle"

_AMBIGUOUS_SUBMIT_STATUSES = frozenset(
    (
        "ambiguous_submit_exception",
        "broker_submit_exception",
        "submit_exception",
        "submit_failed_ambiguous",
        "submission_exception",
    )
)
_NOT_SEEN_STATUSES = frozenset(("absent", "missing", "not_found", "not_seen"))
_SUBMITTED_STATUSES = frozenset(("pending_submit", "submit_observed", "submitted"))
_ACTIVE_UNFILLED_STATUSES = frozenset(
    (
        "accepted",
        "held",
        "new",
        "open",
        "pending_new",
        "pending_replace",
    )
)
_PARTIAL_STATUSES = frozenset(("partial_fill", "partially_filled"))
_FILLED_STATUSES = frozenset(("filled",))
_REJECTED_STATUSES = frozenset(("rejected",))
_CANCELED_STATUSES = frozenset(
    (
        "canceled",
        "cancelled",
        "done_for_day",
        "expired",
    )
)
_KNOWN_STATUSES = (
    _AMBIGUOUS_SUBMIT_STATUSES
    | _NOT_SEEN_STATUSES
    | _SUBMITTED_STATUSES
    | _ACTIVE_UNFILLED_STATUSES
    | _PARTIAL_STATUSES
    | _FILLED_STATUSES
    | _REJECTED_STATUSES
    | _CANCELED_STATUSES
)
_TERMINAL_STATES = frozenset(
    (
        ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT,
        ORDER_LIFECYCLE_FILLED_TERMINAL,
        ORDER_LIFECYCLE_REJECTED_TERMINAL,
        ORDER_LIFECYCLE_CANCELED_TERMINAL,
    )
)
_ORDERED_STAGES = {
    ORDER_LIFECYCLE_NOT_SEEN: -1,
    ORDER_LIFECYCLE_SUBMITTED_SEEN: 0,
    ORDER_LIFECYCLE_ACCEPTED_OPEN_UNFILLED: 1,
    ORDER_LIFECYCLE_PARTIALLY_FILLED_OPEN: 2,
    ORDER_LIFECYCLE_FILLED_TERMINAL: 3,
    ORDER_LIFECYCLE_REJECTED_TERMINAL: 3,
    ORDER_LIFECYCLE_CANCELED_TERMINAL: 3,
}


@dataclass(frozen=True, slots=True)
class PaperOrderLifecycleEvent:
    observed_at: str
    client_order_id: str
    broker_order_id: str = ""
    status: str = ""
    filled_qty: Decimal | str | int | None = None
    submitted: bool | None = None
    mutated: bool | None = None
    source: str = ""


@dataclass(frozen=True, slots=True)
class PaperOrderLifecycleReplayResult:
    client_order_id: str
    final_state: str
    terminal: bool
    blockers: tuple[str, ...]
    observations: tuple[PaperOrderLifecycleEvent, ...]
    submitted: bool
    mutated: bool
    order_seen: bool


@dataclass(frozen=True, slots=True)
class _ClassifiedObservation:
    state: str
    status: str
    filled_qty: Decimal | None


def replay_paper_order_lifecycle(
    events: Iterable[PaperOrderLifecycleEvent],
) -> PaperOrderLifecycleReplayResult:
    """Replay local paper-order observations in their source order."""

    observations = tuple(events)
    if not observations:
        return PaperOrderLifecycleReplayResult(
            client_order_id="",
            final_state=ORDER_LIFECYCLE_NOT_SEEN,
            terminal=False,
            blockers=("no_observations",),
            observations=(),
            submitted=False,
            mutated=False,
            order_seen=False,
        )

    client_order_id = ""
    broker_order_id = ""
    final_state = ORDER_LIFECYCLE_NOT_SEEN
    terminal_state = ""
    terminal_filled_qty: Decimal | None = None
    last_filled_qty: Decimal | None = None
    submitted = False
    mutated = False
    order_seen = False
    blockers: list[str] = []

    for event_index, event in enumerate(observations, start=1):
        status = _normalize_status(event.status)
        submitted = submitted or event.submitted is True or status in (
            _AMBIGUOUS_SUBMIT_STATUSES | _SUBMITTED_STATUSES
        )
        mutated = mutated or event.mutated is True or status in (
            _AMBIGUOUS_SUBMIT_STATUSES
        )

        event_client_order_id = _text(event.client_order_id)
        if not event_client_order_id:
            blockers.append(f"event_{event_index}_client_order_id_missing")
            continue
        if client_order_id and event_client_order_id != client_order_id:
            blockers.append(f"event_{event_index}_client_order_id_conflict")
            continue
        client_order_id = client_order_id or event_client_order_id

        event_broker_order_id = _text(event.broker_order_id)
        if (
            broker_order_id
            and event_broker_order_id
            and event_broker_order_id != broker_order_id
        ):
            blockers.append(f"event_{event_index}_broker_order_id_conflict")
            continue
        broker_order_id = broker_order_id or event_broker_order_id

        if (
            final_state in _TERMINAL_STATES
            and final_state != ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT
            and not _status_confirms_terminal_state(final_state, status)
        ):
            blockers.append(f"event_{event_index}_terminal_status_regression")
            continue

        classified, event_blockers = _classify_observation(
            event_index=event_index,
            status=status,
            raw_filled_qty=event.filled_qty,
            previous_filled_qty=last_filled_qty,
        )
        if event_blockers:
            blockers.extend(event_blockers)
            continue
        if classified is None:
            continue

        if classified.filled_qty is not None:
            last_filled_qty = classified.filled_qty

        if classified.state == ORDER_LIFECYCLE_NOT_SEEN:
            if final_state == ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT:
                continue
            if final_state != ORDER_LIFECYCLE_NOT_SEEN or submitted:
                blockers.append(f"event_{event_index}_order_missing_after_evidence")
            continue

        if classified.state == ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT:
            if order_seen:
                blockers.append(
                    f"event_{event_index}_ambiguous_submit_after_order_evidence"
                )
                continue
            final_state = ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT
            terminal_state = ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT
            terminal_filled_qty = None
            continue

        order_seen = True

        if final_state == ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT:
            final_state = classified.state
            terminal_state = (
                classified.state if classified.state in _TERMINAL_STATES else ""
            )
            terminal_filled_qty = (
                classified.filled_qty if classified.state in _TERMINAL_STATES else None
            )
            continue

        if final_state in _TERMINAL_STATES:
            if _terminal_observation_confirms(
                terminal_state=terminal_state,
                terminal_filled_qty=terminal_filled_qty,
                observation=classified,
            ):
                continue
            blockers.append(f"event_{event_index}_terminal_status_regression")
            continue

        if _stage_regressed(final_state, classified.state):
            blockers.append(f"event_{event_index}_status_regression")
            continue

        final_state = classified.state
        if classified.state in _TERMINAL_STATES:
            terminal_state = classified.state
            terminal_filled_qty = classified.filled_qty

    if blockers:
        return PaperOrderLifecycleReplayResult(
            client_order_id=client_order_id,
            final_state=ORDER_LIFECYCLE_INCONSISTENT,
            terminal=False,
            blockers=tuple(dict.fromkeys(blockers)),
            observations=observations,
            submitted=submitted,
            mutated=mutated,
            order_seen=order_seen,
        )

    return PaperOrderLifecycleReplayResult(
        client_order_id=client_order_id,
        final_state=final_state,
        terminal=final_state in _TERMINAL_STATES,
        blockers=_final_state_blockers(final_state),
        observations=observations,
        submitted=submitted,
        mutated=mutated,
        order_seen=order_seen,
    )


def _classify_observation(
    *,
    event_index: int,
    status: str,
    raw_filled_qty: Decimal | str | int | None,
    previous_filled_qty: Decimal | None,
) -> tuple[_ClassifiedObservation | None, tuple[str, ...]]:
    blockers: list[str] = []
    if not status:
        return None, (f"event_{event_index}_status_missing",)
    if status not in _KNOWN_STATUSES:
        return None, (f"event_{event_index}_status_unknown_{status}",)

    filled_qty, filled_qty_blocker = _filled_quantity(raw_filled_qty)
    if filled_qty_blocker:
        return None, (f"event_{event_index}_{filled_qty_blocker}",)
    if (
        previous_filled_qty is not None
        and filled_qty is not None
        and filled_qty < previous_filled_qty
    ):
        return None, (f"event_{event_index}_filled_qty_decreased",)

    if status in _NOT_SEEN_STATUSES:
        if _is_positive(filled_qty):
            blockers.append(f"event_{event_index}_not_seen_status_has_filled_qty")
        state = ORDER_LIFECYCLE_NOT_SEEN
    elif status in _AMBIGUOUS_SUBMIT_STATUSES:
        if _is_positive(filled_qty):
            blockers.append(
                f"event_{event_index}_ambiguous_submit_status_has_filled_qty"
            )
        state = ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT
    elif status in _SUBMITTED_STATUSES:
        if _is_positive(filled_qty):
            blockers.append(f"event_{event_index}_submitted_status_has_filled_qty")
        state = ORDER_LIFECYCLE_SUBMITTED_SEEN
    elif status in _ACTIVE_UNFILLED_STATUSES:
        if _is_positive(filled_qty):
            blockers.append(f"event_{event_index}_active_status_has_filled_qty")
        state = ORDER_LIFECYCLE_ACCEPTED_OPEN_UNFILLED
    elif status in _PARTIAL_STATUSES:
        if not _is_positive(filled_qty):
            blockers.append(
                f"event_{event_index}_partial_status_missing_positive_filled_qty"
            )
        state = ORDER_LIFECYCLE_PARTIALLY_FILLED_OPEN
    elif status in _FILLED_STATUSES:
        if not _is_positive(filled_qty):
            blockers.append(
                f"event_{event_index}_filled_status_missing_positive_filled_qty"
            )
        state = ORDER_LIFECYCLE_FILLED_TERMINAL
    elif status in _REJECTED_STATUSES:
        if _is_positive(filled_qty) or _is_positive(previous_filled_qty):
            blockers.append(f"event_{event_index}_rejected_status_after_fill_evidence")
        state = ORDER_LIFECYCLE_REJECTED_TERMINAL
    else:
        state = ORDER_LIFECYCLE_CANCELED_TERMINAL

    if blockers:
        return None, tuple(blockers)
    return _ClassifiedObservation(state, status, filled_qty), ()


def _terminal_observation_confirms(
    *,
    terminal_state: str,
    terminal_filled_qty: Decimal | None,
    observation: _ClassifiedObservation,
) -> bool:
    if observation.state != terminal_state:
        return False
    if terminal_state == ORDER_LIFECYCLE_REJECTED_TERMINAL:
        return not _is_positive(observation.filled_qty)
    if terminal_filled_qty is None:
        return observation.filled_qty is None
    return observation.filled_qty == terminal_filled_qty


def _status_confirms_terminal_state(terminal_state: str, status: str) -> bool:
    if terminal_state == ORDER_LIFECYCLE_FILLED_TERMINAL:
        return status in _FILLED_STATUSES
    if terminal_state == ORDER_LIFECYCLE_REJECTED_TERMINAL:
        return status in _REJECTED_STATUSES
    if terminal_state == ORDER_LIFECYCLE_CANCELED_TERMINAL:
        return status in _CANCELED_STATUSES
    return False


def _stage_regressed(previous_state: str, next_state: str) -> bool:
    previous_stage = _ORDERED_STAGES.get(previous_state, -1)
    next_stage = _ORDERED_STAGES.get(next_state, previous_stage)
    return next_stage < previous_stage


def _final_state_blockers(final_state: str) -> tuple[str, ...]:
    if final_state == ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT:
        return (
            "ambiguous_submit_exception",
            "repeat_submission_blocked_until_read_only_order_evidence",
        )
    if final_state == ORDER_LIFECYCLE_REJECTED_TERMINAL:
        return ("rejected_terminal_blocks_repeat_submission",)
    if final_state == ORDER_LIFECYCLE_CANCELED_TERMINAL:
        return ("canceled_terminal_blocks_repeat_submission",)
    return ()


def _filled_quantity(value: Any) -> tuple[Decimal | None, str]:
    text = _text(value).replace(",", "")
    if not text:
        return None, ""
    try:
        filled_qty = Decimal(text)
    except InvalidOperation:
        return None, "filled_qty_invalid"
    if filled_qty < 0:
        return None, "filled_qty_negative"
    return filled_qty, ""


def _normalize_status(value: Any) -> str:
    text = _text(value).lower()
    if not text:
        return ""
    text = text.replace("-", "_").replace(" ", "_")
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text


def _is_positive(value: Decimal | None) -> bool:
    return value is not None and value > 0


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value).strip()


__all__ = [
    "ORDER_LIFECYCLE_ACCEPTED_OPEN_UNFILLED",
    "ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT",
    "ORDER_LIFECYCLE_CANCELED_TERMINAL",
    "ORDER_LIFECYCLE_FILLED_TERMINAL",
    "ORDER_LIFECYCLE_INCONSISTENT",
    "ORDER_LIFECYCLE_NOT_SEEN",
    "ORDER_LIFECYCLE_PARTIALLY_FILLED_OPEN",
    "ORDER_LIFECYCLE_REJECTED_TERMINAL",
    "ORDER_LIFECYCLE_SUBMITTED_SEEN",
    "PaperOrderLifecycleEvent",
    "PaperOrderLifecycleReplayResult",
    "replay_paper_order_lifecycle",
]
