from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.execution.paper_order_lifecycle_replay import (
    ORDER_LIFECYCLE_ACCEPTED_OPEN_UNFILLED,
    ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT,
    ORDER_LIFECYCLE_CANCELED_TERMINAL,
    ORDER_LIFECYCLE_FILLED_TERMINAL,
    ORDER_LIFECYCLE_INCONSISTENT,
    ORDER_LIFECYCLE_NOT_SEEN,
    ORDER_LIFECYCLE_PARTIALLY_FILLED_OPEN,
    ORDER_LIFECYCLE_REJECTED_TERMINAL,
    ORDER_LIFECYCLE_SUBMITTED_SEEN,
    PaperOrderLifecycleEvent,
    PaperOrderLifecycleReplayResult,
    replay_paper_order_lifecycle,
)


MODULE_PATH = Path("src/algotrader/execution/paper_order_lifecycle_replay.py")
CLIENT_ORDER_ID = "paper-order-close-m355_spy_paper_close_submit"
BROKER_ORDER_ID = "56a2f690-f4ad-4572-bcf4-1a479398fe55"


def test_empty_replay_returns_not_seen_with_no_observation_blocker() -> None:
    result = replay_paper_order_lifecycle(())

    assert result == PaperOrderLifecycleReplayResult(
        client_order_id="",
        final_state=ORDER_LIFECYCLE_NOT_SEEN,
        terminal=False,
        blockers=("no_observations",),
        observations=(),
        submitted=False,
        mutated=False,
        order_seen=False,
    )


def test_submitted_then_accepted_open_unfilled_resolves_open() -> None:
    submitted = _event("2026-06-02T10:01:00-04:00", status="submitted")
    accepted = _event(
        "2026-06-02T10:02:00-04:00",
        status="OrderStatus.ACCEPTED",
        filled_qty="0",
        submitted=False,
        mutated=False,
        source="read_only_snapshot",
    )

    result = replay_paper_order_lifecycle((submitted, accepted))

    assert result.final_state == ORDER_LIFECYCLE_ACCEPTED_OPEN_UNFILLED
    assert result.terminal is False
    assert result.blockers == ()
    assert result.observations == (submitted, accepted)
    assert result.submitted is True
    assert result.mutated is True
    assert result.order_seen is True


def test_accepted_open_unfilled_then_filled_resolves_terminal() -> None:
    result = replay_paper_order_lifecycle(
        (
            _event("2026-06-02T10:02:00-04:00", status="accepted", filled_qty="0"),
            _event("2026-06-02T16:00:00-04:00", status="filled", filled_qty="0.1"),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_FILLED_TERMINAL
    assert result.terminal is True
    assert result.blockers == ()
    assert result.client_order_id == CLIENT_ORDER_ID
    assert result.order_seen is True


def test_partial_fill_followed_by_larger_partial_fill_is_monotonic() -> None:
    result = replay_paper_order_lifecycle(
        (
            _event("2026-06-02T10:02:00-04:00", status="partially_filled", filled_qty="0.01"),
            _event("2026-06-02T10:03:00-04:00", status="partially_filled", filled_qty="0.02"),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_PARTIALLY_FILLED_OPEN
    assert result.terminal is False
    assert result.blockers == ()


def test_filled_quantity_decrease_is_inconsistent() -> None:
    result = replay_paper_order_lifecycle(
        (
            _event("2026-06-02T10:02:00-04:00", status="partially_filled", filled_qty="0.02"),
            _event("2026-06-02T10:03:00-04:00", status="partially_filled", filled_qty="0.01"),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_INCONSISTENT
    assert "event_2_filled_qty_decreased" in result.blockers


def test_filled_terminal_followed_by_accepted_open_is_status_regression() -> None:
    result = replay_paper_order_lifecycle(
        (
            _event("2026-06-02T10:02:00-04:00", status="filled", filled_qty="0.1"),
            _event("2026-06-02T10:03:00-04:00", status="accepted", filled_qty="0"),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_INCONSISTENT
    assert "event_2_terminal_status_regression" in result.blockers


def test_rejected_terminal_blocks_future_repeat_submission() -> None:
    result = replay_paper_order_lifecycle(
        (_event("2026-06-02T10:02:00-04:00", status="rejected", filled_qty="0"),)
    )

    assert result.final_state == ORDER_LIFECYCLE_REJECTED_TERMINAL
    assert result.terminal is True
    assert result.blockers == ("rejected_terminal_blocks_repeat_submission",)


def test_rejected_terminal_followed_by_open_order_is_inconsistent() -> None:
    result = replay_paper_order_lifecycle(
        (
            _event("2026-06-02T10:02:00-04:00", status="rejected", filled_qty="0"),
            _event("2026-06-02T10:03:00-04:00", status="open", filled_qty="0"),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_INCONSISTENT
    assert "event_2_terminal_status_regression" in result.blockers


def test_canceled_terminal_is_terminal() -> None:
    result = replay_paper_order_lifecycle(
        (_event("2026-06-02T10:02:00-04:00", status="canceled", filled_qty="0"),)
    )

    assert result.final_state == ORDER_LIFECYCLE_CANCELED_TERMINAL
    assert result.terminal is True
    assert result.blockers == ("canceled_terminal_blocks_repeat_submission",)


def test_ambiguous_submit_exception_blocks_repeat_submission_until_resolved() -> None:
    result = replay_paper_order_lifecycle(
        (
            _event(
                "2026-06-02T10:01:00-04:00",
                status="submit_exception",
                submitted=True,
                mutated=True,
                source="local_submit_exception",
            ),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT
    assert result.terminal is True
    assert result.submitted is True
    assert result.mutated is True
    assert result.blockers == (
        "ambiguous_submit_exception",
        "repeat_submission_blocked_until_read_only_order_evidence",
    )


def test_ambiguous_submit_exception_can_be_resolved_by_read_only_order_evidence() -> None:
    result = replay_paper_order_lifecycle(
        (
            _event(
                "2026-06-02T10:01:00-04:00",
                status="submit_exception",
                submitted=True,
                mutated=True,
            ),
            _event(
                "2026-06-02T10:02:00-04:00",
                status="accepted",
                filled_qty="0",
                submitted=False,
                mutated=False,
                source="read_only_snapshot",
            ),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_ACCEPTED_OPEN_UNFILLED
    assert result.terminal is False
    assert result.blockers == ()
    assert result.submitted is True
    assert result.mutated is True


def test_m355_style_accepted_unfilled_then_filled_replay_resolves_terminal() -> None:
    events = (
        _event("2026-06-02T09:35:00-04:00", status="submitted", filled_qty="0"),
        _event("2026-06-02T09:36:00-04:00", status="accepted", filled_qty="0"),
        _event("2026-06-02T12:00:00-04:00", status="open", filled_qty="0"),
        _event("2026-06-02T15:55:00-04:00", status="filled", filled_qty="0.032905647"),
    )

    result = replay_paper_order_lifecycle(events)

    assert result.final_state == ORDER_LIFECYCLE_FILLED_TERMINAL
    assert result.terminal is True
    assert result.blockers == ()
    assert result.submitted is True
    assert result.mutated is True
    assert result.observations == events


def test_missing_client_order_id_blocks_replay() -> None:
    result = replay_paper_order_lifecycle(
        (
            PaperOrderLifecycleEvent(
                observed_at="2026-06-02T10:02:00-04:00",
                client_order_id="",
                broker_order_id=BROKER_ORDER_ID,
                status="accepted",
            ),
        )
    )

    assert result.final_state == ORDER_LIFECYCLE_INCONSISTENT
    assert result.client_order_id == ""
    assert result.order_seen is False
    assert "event_1_client_order_id_missing" in result.blockers


def test_unknown_status_is_inconsistent() -> None:
    result = replay_paper_order_lifecycle(
        (_event("2026-06-02T10:02:00-04:00", status="broker_magic_state"),)
    )

    assert result.final_state == ORDER_LIFECYCLE_INCONSISTENT
    assert "event_1_status_unknown_broker_magic_state" in result.blockers


def test_event_and_result_objects_are_frozen_slotted_dataclasses() -> None:
    event = _event("2026-06-02T10:02:00-04:00", status="accepted")
    result = replay_paper_order_lifecycle((event,))

    assert is_dataclass(PaperOrderLifecycleEvent)
    assert is_dataclass(PaperOrderLifecycleReplayResult)
    assert hasattr(PaperOrderLifecycleEvent, "__slots__")
    assert hasattr(PaperOrderLifecycleReplayResult, "__slots__")
    assert tuple(field.name for field in fields(PaperOrderLifecycleEvent)) == (
        "observed_at",
        "client_order_id",
        "broker_order_id",
        "status",
        "filled_qty",
        "submitted",
        "mutated",
        "source",
    )
    with pytest.raises(FrozenInstanceError):
        event.status = "filled"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.final_state = ORDER_LIFECYCLE_SUBMITTED_SEEN  # type: ignore[misc]


def test_module_introduces_no_forbidden_broker_or_network_calls() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    forbidden_call_names = {
        "cancel_order",
        "close_all_positions",
        "close_position",
        "delete_order",
        "liquidate",
        "replace_order",
        "submit_order",
    }
    forbidden_fragments = {
        "AlpacaSdkClient",
        "alpaca_trade_api",
        "cancel_order",
        "close_all_positions",
        "close_position",
        "delete_order",
        "liquidate(",
        "replace_order",
        "requests",
        "socket",
        "submit_order",
        "subprocess",
        "urllib",
    }
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert call_names.isdisjoint(forbidden_call_names)
    assert all(fragment not in source for fragment in forbidden_fragments)


def _event(
    observed_at: str,
    *,
    status: str,
    filled_qty: Decimal | str | int | None = None,
    submitted: bool | None = None,
    mutated: bool | None = None,
    source: str = "unit_fixture",
) -> PaperOrderLifecycleEvent:
    return PaperOrderLifecycleEvent(
        observed_at=observed_at,
        client_order_id=CLIENT_ORDER_ID,
        broker_order_id=BROKER_ORDER_ID,
        status=status,
        filled_qty=filled_qty,
        submitted=True if submitted is None and status == "submitted" else submitted,
        mutated=True if mutated is None and status == "submitted" else mutated,
        source=source,
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
