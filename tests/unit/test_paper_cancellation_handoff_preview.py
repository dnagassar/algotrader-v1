from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import inspect
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.durable_cancel import DurableCancelIdentity
from algotrader.execution.order_journal import OrderJournalRecord, OrderJournalState
from algotrader.execution.paper_cancellation_handoff_preview import (
    DURABLE_CANCELLATION_HANDOFF_PREVIEW_VERSION,
    DurableCancellationHandoffBlocker,
    DurableCancellationHandoffIdentity,
    DurableCancellationHandoffPreview,
    DurableCancellationHandoffRequest,
    DurableCancellationHandoffStatus,
    preview_durable_cancellation_handoff,
)
from algotrader.orchestration.cancellation_planning_flow import (
    build_cancellation_plan,
)
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationPlanningBlocker,
    CancellationPlanningResult,
    CancellationPlanningStatus,
)


NOW = datetime(2026, 7, 13, 15, 0, tzinfo=UTC)


def _record(**changes: object) -> OrderJournalRecord:
    values: dict[str, object] = {
        "client_order_id": "client-1",
        "execution_plan_id": "execution-plan-1",
        "run_id": "reservation-run-1",
        "symbol": "SPY",
        "side": "buy",
        "quantity": None,
        "notional": Decimal("25"),
        "state": OrderJournalState.ACCEPTED,
        "broker_order_id": "broker-1",
        "broker_status": "accepted",
        "filled_quantity": Decimal("0"),
        "filled_average_price": None,
        "ambiguity_reason": "",
        "created_at": NOW - timedelta(minutes=30),
        "updated_at": NOW - timedelta(minutes=1),
    }
    values.update(changes)
    return OrderJournalRecord(**values)  # type: ignore[arg-type]


def _planning_result(
    record: OrderJournalRecord | None = None,
    **changes: object,
) -> CancellationPlanningResult:
    local_record = record or _record()
    values: dict[str, object] = {
        "client_order_id": local_record.client_order_id,
        "broker_order_id": local_record.broker_order_id,
        "symbol": local_record.symbol,
        "broker_status": local_record.broker_status,
        "observed_at": local_record.updated_at,
        "reason": "aged local order review",
    }
    values.update(changes)
    plan = build_cancellation_plan(**values)  # type: ignore[arg-type]
    return CancellationPlanningResult(
        status=CancellationPlanningStatus.PLANNED,
        plan=plan,
        blocker=None,
    )


def _request(**changes: object) -> DurableCancellationHandoffRequest:
    values: dict[str, object] = {
        "as_of": NOW,
        "maximum_record_age_seconds": 300,
        "handoff_permitted": True,
    }
    values.update(changes)
    return DurableCancellationHandoffRequest(**values)  # type: ignore[arg-type]


def test_prepares_exact_durable_identity_inputs_with_default_denial() -> None:
    record = _record()

    preview = preview_durable_cancellation_handoff(
        _planning_result(record),
        record,
        _request(),
    )

    assert preview.status is DurableCancellationHandoffStatus.PREPARED
    assert preview.prepared is True
    assert preview.blocker is None
    assert preview.identity is not None
    assert preview.identity.cancel_intent_id.startswith("cancel_intent_")
    assert preview.identity.client_order_id == "client-1"
    assert preview.identity.broker_order_id == "broker-1"
    assert preview.identity.reservation_run_id == "reservation-run-1"
    assert preview.identity.reason == "aged local order review"
    assert preview.identity.source_plan_id == preview.source_plan_id
    durable_identity = DurableCancelIdentity(
        **preview.identity.coordinator_inputs()
    )
    assert durable_identity.cancel_intent_id == preview.identity.cancel_intent_id

    payload = preview.to_dict()
    assert payload["artifact_version"] == (
        DURABLE_CANCELLATION_HANDOFF_PREVIEW_VERSION
    )
    assert payload["status"] == "prepared"
    assert payload["blocker"] == ""
    assert payload["handoff_prepared"] is True
    assert payload["identity"] == preview.identity.to_dict()
    assert payload["coordinator_identity_inputs"] == (
        preview.identity.coordinator_inputs()
    )
    assert payload["no_submit"] is True
    assert payload["cancel_allowed"] is False
    assert payload["execution_authorized"] is False
    assert payload["broker_callback_present"] is False
    assert payload["coordinator_invoked"] is False
    assert payload["cancel_attempted"] is False
    assert payload["broker_access_performed"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["journal_mutation_performed"] is False


def test_identity_and_artifact_are_deterministic_across_reruns() -> None:
    record = _record()
    result = _planning_result(record)

    first = preview_durable_cancellation_handoff(result, record, _request())
    second = preview_durable_cancellation_handoff(result, record, _request())
    later = preview_durable_cancellation_handoff(
        result,
        record,
        _request(as_of=NOW + timedelta(seconds=1)),
    )
    different_run = preview_durable_cancellation_handoff(
        result,
        replace(record, run_id="reservation-run-2"),
        _request(),
    )

    assert first == second
    assert first.to_dict() == second.to_dict()
    assert first.artifact_id != later.artifact_id
    assert first.identity is not None
    assert later.identity is not None
    assert first.identity.cancel_intent_id == later.identity.cancel_intent_id
    assert different_run.identity is not None
    assert different_run.identity.cancel_intent_id != first.identity.cancel_intent_id


def test_missing_permission_blocks_before_plan_or_record_evaluation() -> None:
    preview = preview_durable_cancellation_handoff(
        None,
        None,
        _request(handoff_permitted=False),
    )

    _assert_blocked(
        preview,
        DurableCancellationHandoffBlocker.HANDOFF_NOT_PERMITTED,
    )


def test_missing_or_blocked_planning_result_never_emits_identity() -> None:
    missing = preview_durable_cancellation_handoff(None, _record(), _request())
    blocked_result = CancellationPlanningResult(
        status=CancellationPlanningStatus.BLOCKED,
        plan=None,
        blocker=CancellationPlanningBlocker.CANCELLATION_NOT_PERMITTED,
    )
    blocked = preview_durable_cancellation_handoff(
        blocked_result,
        _record(),
        _request(),
    )

    _assert_blocked(
        missing,
        DurableCancellationHandoffBlocker.PLANNING_RESULT_MISSING,
    )
    _assert_blocked(
        blocked,
        DurableCancellationHandoffBlocker.PLAN_NOT_AVAILABLE,
    )


def test_missing_record_blocks_a_valid_plan() -> None:
    preview = preview_durable_cancellation_handoff(
        _planning_result(),
        None,
        _request(),
    )

    _assert_blocked(preview, DurableCancellationHandoffBlocker.RECORD_MISSING)
    assert preview.source_plan_id.startswith("cancel_plan_")


@pytest.mark.parametrize(
    ("record_changes", "request_changes", "expected"),
    [
        (
            {"created_at": datetime(2026, 7, 13, 14, 30)},
            {},
            DurableCancellationHandoffBlocker.RECORD_TIMESTAMP_INVALID,
        ),
        (
            {
                "created_at": NOW - timedelta(seconds=30),
                "updated_at": NOW - timedelta(minutes=1),
            },
            {},
            DurableCancellationHandoffBlocker.RECORD_TIMESTAMP_INCONSISTENT,
        ),
        (
            {
                "created_at": NOW + timedelta(minutes=1),
                "updated_at": NOW + timedelta(minutes=2),
            },
            {},
            DurableCancellationHandoffBlocker.FUTURE_RECORD_TIMESTAMP,
        ),
        (
            {"state": OrderJournalState.FILLED},
            {},
            DurableCancellationHandoffBlocker.RECORD_TERMINAL,
        ),
        (
            {"state": OrderJournalState.UNKNOWN},
            {},
            DurableCancellationHandoffBlocker.RECORD_STATE_NOT_CANCEL_READY,
        ),
        (
            {"state": OrderJournalState.SUBMIT_ATTEMPTED},
            {},
            DurableCancellationHandoffBlocker.RECORD_STATE_NOT_CANCEL_READY,
        ),
        (
            {},
            {"as_of": NOW + timedelta(minutes=10)},
            DurableCancellationHandoffBlocker.RECORD_STALE,
        ),
        (
            {"client_order_id": ""},
            {},
            DurableCancellationHandoffBlocker.RECORD_IDENTITY_INCOMPLETE,
        ),
        (
            {"broker_order_id": ""},
            {},
            DurableCancellationHandoffBlocker.RECORD_IDENTITY_INCOMPLETE,
        ),
        (
            {"run_id": ""},
            {},
            DurableCancellationHandoffBlocker.RECORD_IDENTITY_INCOMPLETE,
        ),
    ],
)
def test_record_safety_failures_are_typed_and_default_denied(
    record_changes: dict[str, object],
    request_changes: dict[str, object],
    expected: DurableCancellationHandoffBlocker,
) -> None:
    baseline = _record()
    changed = replace(baseline, **record_changes)

    preview = preview_durable_cancellation_handoff(
        _planning_result(baseline),
        changed,
        _request(**request_changes),
    )

    _assert_blocked(preview, expected)


@pytest.mark.parametrize(
    ("plan_changes", "expected"),
    [
        (
            {"client_order_id": "other-client"},
            DurableCancellationHandoffBlocker.CLIENT_ORDER_ID_MISMATCH,
        ),
        (
            {"broker_order_id": "other-broker"},
            DurableCancellationHandoffBlocker.BROKER_ORDER_ID_MISMATCH,
        ),
        (
            {"symbol": "MSFT"},
            DurableCancellationHandoffBlocker.SYMBOL_MISMATCH,
        ),
        (
            {"broker_status": "new"},
            DurableCancellationHandoffBlocker.BROKER_STATUS_MISMATCH,
        ),
        (
            {"observed_at": NOW - timedelta(minutes=2)},
            DurableCancellationHandoffBlocker.OBSERVATION_TIMESTAMP_MISMATCH,
        ),
    ],
)
def test_plan_must_bind_exactly_to_the_local_record(
    plan_changes: dict[str, object],
    expected: DurableCancellationHandoffBlocker,
) -> None:
    record = _record()

    preview = preview_durable_cancellation_handoff(
        _planning_result(record, **plan_changes),
        record,
        _request(),
    )

    _assert_blocked(preview, expected)


@pytest.mark.parametrize(
    "changes",
    [
        {"as_of": datetime(2026, 7, 13, 15, 0)},
        {"maximum_record_age_seconds": 0},
        {"maximum_record_age_seconds": True},
        {"handoff_permitted": 1},
    ],
)
def test_request_requires_explicit_utc_boolean_and_positive_age(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _request(**changes)


def test_function_rejects_wrong_typed_inputs() -> None:
    with pytest.raises(ValidationError, match="request must be"):
        preview_durable_cancellation_handoff(
            None,
            None,
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError, match="planning_result must be"):
        preview_durable_cancellation_handoff(
            object(),  # type: ignore[arg-type]
            None,
            _request(),
        )
    with pytest.raises(ValidationError, match="record must be"):
        preview_durable_cancellation_handoff(
            _planning_result(),
            object(),  # type: ignore[arg-type]
            _request(),
        )
    with pytest.raises(ValidationError, match="planning_result must be"):
        preview_durable_cancellation_handoff(
            object(),  # type: ignore[arg-type]
            None,
            _request(handoff_permitted=False),
        )


def test_contracts_are_frozen_and_reject_forged_identity_or_preview() -> None:
    record = _record()
    preview = preview_durable_cancellation_handoff(
        _planning_result(record),
        record,
        _request(),
    )
    assert preview.identity is not None
    with pytest.raises(FrozenInstanceError):
        preview.identity.reason = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError, match="cancel_intent_id"):
        replace(preview.identity, cancel_intent_id="forged")
    with pytest.raises(ValidationError, match="artifact_id"):
        replace(preview, artifact_id="forged")
    with pytest.raises(ValidationError, match="blocked preview"):
        DurableCancellationHandoffPreview(
            artifact_id="forged",
            status=DurableCancellationHandoffStatus.BLOCKED,
            blocker=None,
            request=_request(),
            source_plan_id="",
            identity=preview.identity,
        )


def test_module_has_no_durable_coordinator_broker_callback_or_io_boundary() -> None:
    signature = inspect.signature(preview_durable_cancellation_handoff)
    assert tuple(signature.parameters) == (
        "planning_result",
        "record",
        "request",
    )

    source_path = Path(
        inspect.getsourcefile(preview_durable_cancellation_handoff) or ""
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
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
    referenced_names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
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
        for token in (
            "alpaca",
            "broker_base",
            "durable_cancel",
            "httpx",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        )
    )
    assert referenced_names.isdisjoint(
        {
            "DurableCancelCoordinator",
            "SqliteOrderJournal",
            "broker_client",
            "cancel",
            "cancel_order",
            "callback",
        }
    )
    assert calls.isdisjoint(
        {
            "cancel_order",
            "connect",
            "datetime.now",
            "open",
            "reserve_cancel_intent",
            "submit_order",
            "write",
        }
    )


def _assert_blocked(
    preview: DurableCancellationHandoffPreview,
    blocker: DurableCancellationHandoffBlocker,
) -> None:
    assert preview.status is DurableCancellationHandoffStatus.BLOCKED
    assert preview.prepared is False
    assert preview.blocker is blocker
    assert preview.identity is None
    payload = preview.to_dict()
    assert payload["identity"] == {}
    assert payload["coordinator_identity_inputs"] == {}
    assert payload["cancel_allowed"] is False
    assert payload["execution_authorized"] is False
    assert payload["broker_callback_present"] is False
    assert payload["coordinator_invoked"] is False
    assert payload["cancel_attempted"] is False
    assert payload["broker_access_performed"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["journal_mutation_performed"] is False
