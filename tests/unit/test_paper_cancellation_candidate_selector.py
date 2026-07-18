from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import inspect
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.order_journal import OrderJournalRecord, OrderJournalState
from algotrader.execution.paper_cancellation_candidate_selector import (
    CancellationCandidateSelectionBlocker,
    CancellationCandidateSelectionRequest,
    CancellationCandidateSelectionResult,
    CancellationCandidateSelectionStatus,
    select_cancellation_candidate,
)


NOW = datetime(2026, 7, 13, 15, 0, tzinfo=UTC)


def _request(**changes: object) -> CancellationCandidateSelectionRequest:
    values: dict[str, object] = {
        "symbol": "SPY",
        "as_of": NOW,
        "minimum_open_age_seconds": 900,
        "reason": "aged local order review",
        "planning_permitted": True,
        "trading_enabled": True,
        "stop_requested": False,
    }
    values.update(changes)
    return CancellationCandidateSelectionRequest(**values)  # type: ignore[arg-type]


def _record(
    *,
    client_order_id: str = "client-1",
    broker_order_id: str = "broker-1",
    state: OrderJournalState = OrderJournalState.ACCEPTED,
    broker_status: str = "accepted",
    created_at: datetime = NOW - timedelta(minutes=30),
    updated_at: datetime = NOW - timedelta(minutes=1),
) -> OrderJournalRecord:
    return OrderJournalRecord(
        client_order_id=client_order_id,
        execution_plan_id=f"plan-{client_order_id}",
        run_id=f"run-{client_order_id}",
        symbol="SPY",
        side="buy",
        quantity=None,
        notional=Decimal("25"),
        state=state,
        broker_order_id=broker_order_id,
        broker_status=broker_status,
        filled_quantity=Decimal("0"),
        filled_average_price=None,
        ambiguity_reason="",
        created_at=created_at,
        updated_at=updated_at,
    )


def test_selects_exactly_one_aged_cancelable_local_record() -> None:
    record = _record()

    result = select_cancellation_candidate((record,), _request())

    assert result.status is CancellationCandidateSelectionStatus.SELECTED
    assert result.selected is True
    assert result.blocker is None
    assert result.considered_count == 1
    assert result.eligible_count == 1
    assert result.candidate is not None
    assert result.candidate.client_order_id == "client-1"
    assert result.candidate.broker_order_id == "broker-1"
    assert result.candidate.symbol == "SPY"
    assert result.candidate.broker_status == "accepted"
    assert result.candidate.created_at == NOW - timedelta(minutes=30)
    assert result.candidate.observed_at == NOW - timedelta(minutes=1)
    assert result.candidate.open_age_seconds == 1800
    assert result.candidate.reason == "aged local order review"
    assert result.to_dict() == {
        "status": "selected",
        "blocker": "",
        "considered_count": 1,
        "eligible_count": 1,
        "candidate": {
            "client_order_id": "client-1",
            "broker_order_id": "broker-1",
            "symbol": "SPY",
            "broker_status": "accepted",
            "created_at": "2026-07-13T14:30:00+00:00",
            "observed_at": "2026-07-13T14:59:00+00:00",
            "open_age_seconds": 1800,
            "reason": "aged local order review",
        },
    }


def test_selection_is_input_order_independent_and_consumes_iterable_once() -> None:
    eligible = replace(
        _record(),
        broker_status=OrderJournalState.ACCEPTED,  # type: ignore[arg-type]
    )
    terminal = _record(
        client_order_id="client-filled",
        broker_order_id="broker-filled",
        state=OrderJournalState.FILLED,
        broker_status="filled",
    )
    yields = 0

    def records():
        nonlocal yields
        for record in (terminal, eligible):
            yields += 1
            yield record

    generated = select_cancellation_candidate(records(), _request())
    reversed_result = select_cancellation_candidate(
        (eligible, terminal),
        _request(),
    )

    assert yields == 2
    assert generated == reversed_result
    assert generated.candidate is not None
    assert generated.candidate.broker_status == "accepted"


def test_selector_ignores_non_target_symbols() -> None:
    other = replace(
        _record(),
        client_order_id="client-other",
        broker_order_id="broker-other",
        symbol="MSFT",
    )

    result = select_cancellation_candidate((other, _record()), _request())

    assert result.selected is True
    assert result.considered_count == 1


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (
            _record(created_at=NOW - timedelta(minutes=5)),
            CancellationCandidateSelectionBlocker.NO_CANDIDATE,
        ),
        (
            _record(state=OrderJournalState.OPEN, broker_status="open"),
            CancellationCandidateSelectionBlocker.NO_CANDIDATE,
        ),
        (
            _record(state=OrderJournalState.FILLED, broker_status="filled"),
            CancellationCandidateSelectionBlocker.TERMINAL_RECORDS_ONLY,
        ),
        (
            _record(state=OrderJournalState.UNKNOWN, broker_status="accepted"),
            CancellationCandidateSelectionBlocker.UNKNOWN_RECORD_STATE,
        ),
        (
            _record(broker_status="ambiguous"),
            CancellationCandidateSelectionBlocker.UNKNOWN_RECORD_STATE,
        ),
        (
            _record(broker_status="unexpected_vendor_state"),
            CancellationCandidateSelectionBlocker.UNKNOWN_RECORD_STATE,
        ),
        (
            _record(
                created_at=NOW + timedelta(minutes=1),
                updated_at=NOW + timedelta(minutes=2),
            ),
            CancellationCandidateSelectionBlocker.FUTURE_RECORD_TIMESTAMP,
        ),
        (
            _record(
                created_at=NOW - timedelta(minutes=1),
                updated_at=NOW - timedelta(minutes=2),
            ),
            CancellationCandidateSelectionBlocker.RECORD_TIMESTAMP_INCONSISTENT,
        ),
        (
            _record(created_at=datetime(2026, 7, 13, 14, 30)),
            CancellationCandidateSelectionBlocker.RECORD_TIMESTAMP_INVALID,
        ),
    ],
)
def test_record_eligibility_failures_are_typed_and_fail_closed(
    record: OrderJournalRecord,
    expected: CancellationCandidateSelectionBlocker,
) -> None:
    result = select_cancellation_candidate((record,), _request())

    assert result.selected is False
    assert result.blocker is expected
    assert result.candidate is None


def test_duplicate_broker_identity_blocks_before_candidate_selection() -> None:
    duplicate = replace(_record(), client_order_id="client-2")

    result = select_cancellation_candidate((_record(), duplicate), _request())

    assert result.blocker is (
        CancellationCandidateSelectionBlocker.DUPLICATE_BROKER_IDENTITY
    )
    assert result.eligible_count == 0


@pytest.mark.parametrize("field_name", ["client_order_id", "broker_order_id"])
def test_incomplete_aged_candidate_identity_fails_closed(field_name: str) -> None:
    result = select_cancellation_candidate(
        (replace(_record(), **{field_name: ""}),),
        _request(),
    )

    assert result.blocker is CancellationCandidateSelectionBlocker.IDENTITY_INCOMPLETE
    assert result.eligible_count == 1


def test_multiple_eligible_candidates_are_never_ranked_or_selected() -> None:
    other = replace(
        _record(),
        client_order_id="client-2",
        broker_order_id="broker-2",
        created_at=NOW - timedelta(hours=3),
    )

    forward = select_cancellation_candidate((_record(), other), _request())
    reverse = select_cancellation_candidate((other, _record()), _request())

    assert forward == reverse
    assert forward.blocker is (
        CancellationCandidateSelectionBlocker.MULTIPLE_ELIGIBLE_CANDIDATES
    )
    assert forward.eligible_count == 2


def test_runtime_and_permission_blocker_precedence_is_deterministic() -> None:
    stop = select_cancellation_candidate(
        (),
        _request(
            stop_requested=True,
            trading_enabled=False,
            planning_permitted=False,
        ),
    )
    paused = select_cancellation_candidate(
        (),
        _request(trading_enabled=False, planning_permitted=False),
    )
    not_permitted = select_cancellation_candidate(
        (),
        _request(planning_permitted=False),
    )
    empty = select_cancellation_candidate((), _request())

    assert stop.blocker is CancellationCandidateSelectionBlocker.STOP_REQUESTED
    assert paused.blocker is CancellationCandidateSelectionBlocker.TRADING_PAUSED
    assert not_permitted.blocker is (
        CancellationCandidateSelectionBlocker.PLANNING_NOT_PERMITTED
    )
    assert empty.blocker is CancellationCandidateSelectionBlocker.NO_CANDIDATE


@pytest.mark.parametrize(
    "changes",
    [
        {"as_of": datetime(2026, 7, 13, 15, 0)},
        {"minimum_open_age_seconds": 0},
        {"minimum_open_age_seconds": True},
        {"reason": ""},
        {"planning_permitted": 1},
        {"trading_enabled": 1},
        {"stop_requested": 0},
    ],
)
def test_request_rejects_implicit_or_invalid_inputs(changes: dict[str, object]) -> None:
    values: dict[str, object] = {
        "symbol": "SPY",
        "as_of": NOW,
        "minimum_open_age_seconds": 900,
        "reason": "aged local order review",
        "planning_permitted": True,
        "trading_enabled": True,
        "stop_requested": False,
    }
    values.update(changes)

    with pytest.raises(ValidationError):
        CancellationCandidateSelectionRequest(**values)  # type: ignore[arg-type]


def test_selector_rejects_non_record_or_non_request_values() -> None:
    with pytest.raises(ValidationError, match="request must be"):
        select_cancellation_candidate((), object())  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="OrderJournalRecord"):
        select_cancellation_candidate((object(),), _request())  # type: ignore[arg-type]


def test_result_contract_is_frozen_and_rejects_inconsistent_construction() -> None:
    result = select_cancellation_candidate((_record(),), _request())
    with pytest.raises(FrozenInstanceError):
        result.eligible_count = 2  # type: ignore[misc]
    with pytest.raises(ValidationError, match="selected result"):
        CancellationCandidateSelectionResult(
            status=CancellationCandidateSelectionStatus.SELECTED,
            candidate=None,
            blocker=None,
            considered_count=1,
            eligible_count=1,
        )
    with pytest.raises(ValidationError, match="blocked result"):
        CancellationCandidateSelectionResult(
            status=CancellationCandidateSelectionStatus.BLOCKED,
            candidate=result.candidate,
            blocker=None,
            considered_count=1,
            eligible_count=1,
        )


def test_selector_signature_and_source_exclude_broker_or_mutation_boundaries() -> None:
    signature = inspect.signature(select_cancellation_candidate)
    assert tuple(signature.parameters) == ("records", "request")

    source_path = Path(inspect.getsourcefile(select_cancellation_candidate) or "")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }

    assert all(
        token not in module
        for module in imported
        for token in ("alpaca", "broker_base", "durable_cancel", "socket", "urllib")
    )
    assert calls.isdisjoint(
        {
            "cancel_order",
            "connect",
            "open",
            "records",
            "submit_order",
            "write",
        }
    )
