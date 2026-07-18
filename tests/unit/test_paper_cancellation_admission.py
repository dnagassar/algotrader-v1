from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import inspect
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.durable_cancel import (
    DurableCancelEvidence,
    DurableCancelIdentity,
)
from algotrader.execution.order_journal import OrderJournalRecord, OrderJournalState
from algotrader.execution.paper_cancellation_admission import (
    CANCELLATION_OPERATION,
    OPERATOR_CANCELLATION_AUTHORIZATION_VERSION,
    PAPER_CANCELLATION_ADMISSION_VERSION,
    PAPER_CANCELLATION_MODE,
    OperatorCancellationAuthorization,
    PaperCancellationAdmissionBlocker,
    PaperCancellationAdmissionRequest,
    PaperCancellationAdmissionResult,
    PaperCancellationAdmissionStatus,
    build_operator_cancellation_authorization_evidence,
    evaluate_paper_cancellation_admission,
)
from algotrader.execution.paper_cancellation_handoff_preview import (
    DurableCancellationHandoffPreview,
    DurableCancellationHandoffRequest,
    preview_durable_cancellation_handoff,
)
from algotrader.orchestration.cancellation_planning_flow import (
    build_cancellation_plan,
)
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationPlanningResult,
    CancellationPlanningStatus,
)


NOW = datetime(2026, 7, 13, 15, 0, tzinfo=UTC)


def _record() -> OrderJournalRecord:
    return OrderJournalRecord(
        client_order_id="client-1",
        execution_plan_id="execution-plan-1",
        run_id="reservation-run-1",
        symbol="SPY",
        side="buy",
        quantity=None,
        notional=Decimal("25"),
        state=OrderJournalState.ACCEPTED,
        broker_order_id="broker-1",
        broker_status="accepted",
        filled_quantity=Decimal("0"),
        filled_average_price=None,
        ambiguity_reason="",
        created_at=NOW - timedelta(minutes=30),
        updated_at=NOW - timedelta(minutes=1),
    )


def _handoff(*, permitted: bool = True) -> DurableCancellationHandoffPreview:
    record = _record()
    plan = build_cancellation_plan(
        client_order_id=record.client_order_id,
        broker_order_id=record.broker_order_id,
        symbol=record.symbol,
        broker_status=record.broker_status,
        observed_at=record.updated_at,
        reason="aged local order review",
    )
    planning_result = CancellationPlanningResult(
        status=CancellationPlanningStatus.PLANNED,
        plan=plan,
        blocker=None,
    )
    return preview_durable_cancellation_handoff(
        planning_result,
        record,
        DurableCancellationHandoffRequest(
            as_of=NOW,
            maximum_record_age_seconds=300,
            handoff_permitted=permitted,
        ),
    )


def _authorization(
    handoff: DurableCancellationHandoffPreview | None = None,
    **changes: object,
) -> OperatorCancellationAuthorization:
    local_handoff = handoff or _handoff()
    assert local_handoff.identity is not None
    values: dict[str, object] = {
        "mode": PAPER_CANCELLATION_MODE,
        "operation": CANCELLATION_OPERATION,
        "source_plan_id": local_handoff.source_plan_id,
        "cancel_intent_id": local_handoff.identity.cancel_intent_id,
        "client_order_id": local_handoff.identity.client_order_id,
        "broker_order_id": local_handoff.identity.broker_order_id,
        "issued_at": NOW - timedelta(minutes=1),
        "expires_at": NOW + timedelta(minutes=1),
        "authorized": True,
    }
    values.update(changes)
    return build_operator_cancellation_authorization_evidence(  # type: ignore[arg-type]
        **values
    )


def _request(**changes: object) -> PaperCancellationAdmissionRequest:
    values: dict[str, object] = {
        "evaluated_at": NOW,
        "trading_enabled": True,
        "stop_requested": False,
        "snapshot_fresh": True,
    }
    values.update(changes)
    return PaperCancellationAdmissionRequest(**values)  # type: ignore[arg-type]


def test_exact_valid_authorization_emits_typed_durable_inputs_only() -> None:
    handoff = _handoff()
    authorization = _authorization(handoff)

    result = evaluate_paper_cancellation_admission(
        handoff,
        authorization,
        _request(),
    )

    assert result.status is PaperCancellationAdmissionStatus.ADMITTED
    assert result.admitted is True
    assert result.blocker is None
    assert isinstance(result.identity, DurableCancelIdentity)
    assert isinstance(result.evidence, DurableCancelEvidence)
    assert result.identity == DurableCancelIdentity(
        **handoff.identity.coordinator_inputs()  # type: ignore[union-attr]
    )
    assert result.evidence == DurableCancelEvidence(
        cancel_allowed=True,
        snapshot_fresh=True,
    )
    assert result.source_handoff_artifact_id == handoff.artifact_id
    assert result.source_plan_id == handoff.source_plan_id
    assert result.authorization_id == authorization.authorization_id

    payload = result.to_dict()
    assert payload["admission_version"] == PAPER_CANCELLATION_ADMISSION_VERSION
    assert payload["status"] == "admitted"
    assert payload["blocker"] == ""
    assert payload["admission_ready"] is True
    assert payload["operator_authorization_validated"] is True
    assert payload["cancel_allowed"] is True
    assert payload["execution_authorized"] is True
    assert payload["identity"]["cancel_intent_id"] == (
        handoff.identity.cancel_intent_id  # type: ignore[union-attr]
    )
    assert payload["evidence"] == {
        "cancel_allowed": True,
        "snapshot_fresh": True,
    }
    _assert_no_execution(payload)


def test_admission_is_deterministic_and_evaluation_time_is_explicit() -> None:
    handoff = _handoff()
    authorization = _authorization(handoff)

    first = evaluate_paper_cancellation_admission(
        handoff,
        authorization,
        _request(),
    )
    second = evaluate_paper_cancellation_admission(
        handoff,
        authorization,
        _request(),
    )
    later = evaluate_paper_cancellation_admission(
        handoff,
        authorization,
        _request(evaluated_at=NOW + timedelta(seconds=1)),
    )

    assert first == second
    assert first.to_dict() == second.to_dict()
    assert first.admission_id != later.admission_id
    assert first.identity == later.identity
    assert first.evidence == later.evidence


def test_missing_authorization_is_the_default_denial() -> None:
    handoff = _handoff()

    result = evaluate_paper_cancellation_admission(
        handoff,
        None,
        _request(),
    )

    _assert_blocked(result, PaperCancellationAdmissionBlocker.AUTHORIZATION_MISSING)
    assert result.source_handoff_artifact_id == handoff.artifact_id
    assert result.source_plan_id == handoff.source_plan_id
    assert result.authorization_id == ""


@pytest.mark.parametrize(
    ("request_changes", "expected"),
    [
        (
            {
                "stop_requested": True,
                "trading_enabled": False,
                "snapshot_fresh": False,
            },
            PaperCancellationAdmissionBlocker.STOP_REQUESTED,
        ),
        (
            {"trading_enabled": False, "snapshot_fresh": False},
            PaperCancellationAdmissionBlocker.TRADING_PAUSED,
        ),
        (
            {"snapshot_fresh": False},
            PaperCancellationAdmissionBlocker.SNAPSHOT_NOT_FRESH,
        ),
    ],
)
def test_runtime_and_snapshot_blocker_precedence_is_fail_closed(
    request_changes: dict[str, object],
    expected: PaperCancellationAdmissionBlocker,
) -> None:
    result = evaluate_paper_cancellation_admission(
        None,
        None,
        _request(**request_changes),
    )

    _assert_blocked(result, expected)


def test_missing_or_unprepared_handoff_never_reaches_authorization() -> None:
    missing = evaluate_paper_cancellation_admission(
        None,
        None,
        _request(),
    )
    blocked_handoff = _handoff(permitted=False)
    unprepared = evaluate_paper_cancellation_admission(
        blocked_handoff,
        None,
        _request(),
    )

    _assert_blocked(missing, PaperCancellationAdmissionBlocker.HANDOFF_MISSING)
    _assert_blocked(
        unprepared,
        PaperCancellationAdmissionBlocker.HANDOFF_NOT_PREPARED,
    )


@pytest.mark.parametrize(
    ("authorization_changes", "request_changes", "expected"),
    [
        (
            {"authorized": False},
            {},
            PaperCancellationAdmissionBlocker.AUTHORIZATION_NOT_GRANTED,
        ),
        (
            {"mode": "live"},
            {},
            PaperCancellationAdmissionBlocker.AUTHORIZATION_MODE_MISMATCH,
        ),
        (
            {"operation": "replace"},
            {},
            PaperCancellationAdmissionBlocker.AUTHORIZATION_OPERATION_MISMATCH,
        ),
        (
            {
                "issued_at": NOW + timedelta(minutes=1),
                "expires_at": NOW + timedelta(minutes=2),
            },
            {},
            PaperCancellationAdmissionBlocker.AUTHORIZATION_NOT_YET_VALID,
        ),
        (
            {
                "issued_at": NOW - timedelta(minutes=2),
                "expires_at": NOW,
            },
            {},
            PaperCancellationAdmissionBlocker.AUTHORIZATION_EXPIRED,
        ),
    ],
)
def test_authorization_scope_and_validity_window_are_exact(
    authorization_changes: dict[str, object],
    request_changes: dict[str, object],
    expected: PaperCancellationAdmissionBlocker,
) -> None:
    handoff = _handoff()
    result = evaluate_paper_cancellation_admission(
        handoff,
        _authorization(handoff, **authorization_changes),
        _request(**request_changes),
    )

    _assert_blocked(result, expected)


@pytest.mark.parametrize(
    ("authorization_changes", "expected"),
    [
        (
            {"source_plan_id": "other-plan"},
            PaperCancellationAdmissionBlocker.SOURCE_PLAN_ID_MISMATCH,
        ),
        (
            {"cancel_intent_id": "other-intent"},
            PaperCancellationAdmissionBlocker.CANCEL_INTENT_ID_MISMATCH,
        ),
        (
            {"client_order_id": "other-client"},
            PaperCancellationAdmissionBlocker.CLIENT_ORDER_ID_MISMATCH,
        ),
        (
            {"broker_order_id": "other-broker"},
            PaperCancellationAdmissionBlocker.BROKER_ORDER_ID_MISMATCH,
        ),
    ],
)
def test_authorization_must_bind_to_every_handoff_identity_field(
    authorization_changes: dict[str, object],
    expected: PaperCancellationAdmissionBlocker,
) -> None:
    handoff = _handoff()
    result = evaluate_paper_cancellation_admission(
        handoff,
        _authorization(handoff, **authorization_changes),
        _request(),
    )

    _assert_blocked(result, expected)


def test_authorization_builder_is_deterministic_and_primitive_only() -> None:
    handoff = _handoff()
    first = _authorization(handoff)
    second = _authorization(handoff)

    assert first == second
    assert first.authorization_id.startswith("cancel_authorization_")
    assert first.to_dict() == second.to_dict()
    assert first.to_dict()["authorization_version"] == (
        OPERATOR_CANCELLATION_AUTHORIZATION_VERSION
    )
    assert first.to_dict()["mode"] == "paper"
    assert first.to_dict()["operation"] == "cancel"
    assert first.to_dict()["authorized"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": ""},
        {"operation": ""},
        {"source_plan_id": ""},
        {"cancel_intent_id": ""},
        {"client_order_id": ""},
        {"broker_order_id": ""},
        {"issued_at": datetime(2026, 7, 13, 14, 59)},
        {"expires_at": datetime(2026, 7, 13, 15, 1)},
        {"expires_at": NOW - timedelta(minutes=1)},
        {"authorized": 1},
    ],
)
def test_authorization_builder_rejects_implicit_or_invalid_evidence(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _authorization(**changes)


def test_authorization_rejects_forged_deterministic_id() -> None:
    authorization = _authorization()

    with pytest.raises(ValidationError, match="authorization_id"):
        replace(authorization, authorization_id="forged")


@pytest.mark.parametrize(
    "changes",
    [
        {"evaluated_at": datetime(2026, 7, 13, 15, 0)},
        {"trading_enabled": 1},
        {"stop_requested": 0},
        {"snapshot_fresh": 1},
    ],
)
def test_admission_request_requires_explicit_utc_and_exact_booleans(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _request(**changes)


def test_evaluator_rejects_wrong_typed_inputs_before_policy_precedence() -> None:
    with pytest.raises(ValidationError, match="request must be"):
        evaluate_paper_cancellation_admission(
            None,
            None,
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError, match="handoff must be"):
        evaluate_paper_cancellation_admission(
            object(),  # type: ignore[arg-type]
            None,
            _request(stop_requested=True),
        )
    with pytest.raises(ValidationError, match="authorization must be"):
        evaluate_paper_cancellation_admission(
            _handoff(),
            object(),  # type: ignore[arg-type]
            _request(stop_requested=True),
        )


def test_results_are_frozen_and_reject_forged_or_inconsistent_state() -> None:
    handoff = _handoff()
    admitted = evaluate_paper_cancellation_admission(
        handoff,
        _authorization(handoff),
        _request(),
    )
    with pytest.raises(FrozenInstanceError):
        admitted.authorization_id = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError, match="admission_id"):
        replace(admitted, admission_id="forged")
    with pytest.raises(ValidationError, match="blocked result"):
        PaperCancellationAdmissionResult(
            admission_id="forged",
            status=PaperCancellationAdmissionStatus.BLOCKED,
            blocker=None,
            request=_request(),
            source_handoff_artifact_id="",
            source_plan_id="",
            authorization_id="",
            identity=admitted.identity,
            evidence=admitted.evidence,
        )
    with pytest.raises(ValidationError, match="fresh snapshot"):
        replace(
            admitted,
            evidence=DurableCancelEvidence(
                cancel_allowed=True,
                snapshot_fresh=False,
            ),
        )


def test_module_imports_only_durable_identity_and_evidence_not_coordinator() -> None:
    signature = inspect.signature(evaluate_paper_cancellation_admission)
    assert tuple(signature.parameters) == (
        "handoff",
        "authorization",
        "request",
    )

    source_path = Path(
        inspect.getsourcefile(evaluate_paper_cancellation_admission) or ""
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    contract_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "algotrader.execution.durable_cancel_contracts"
        for alias in node.names
    }
    coordinator_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "algotrader.execution.durable_cancel"
        for alias in node.names
    }
    imported_modules = {
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

    assert contract_imports == {"DurableCancelEvidence", "DurableCancelIdentity"}
    assert coordinator_imports == set()
    assert all(
        token not in module
        for module in imported_modules
        for token in (
            "alpaca",
            "broker_base",
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
            "acquire_lease",
            "cancel_order",
            "connect",
            "datetime.now",
            "execute",
            "open",
            "reserve",
            "submit_order",
            "write",
        }
    )


def _assert_blocked(
    result: PaperCancellationAdmissionResult,
    blocker: PaperCancellationAdmissionBlocker,
) -> None:
    assert result.status is PaperCancellationAdmissionStatus.BLOCKED
    assert result.admitted is False
    assert result.blocker is blocker
    assert result.identity is None
    assert result.evidence is None
    payload = result.to_dict()
    assert payload["identity"] == {}
    assert payload["evidence"] == {}
    assert payload["admission_ready"] is False
    assert payload["operator_authorization_validated"] is False
    assert payload["cancel_allowed"] is False
    assert payload["execution_authorized"] is False
    _assert_no_execution(payload)


def _assert_no_execution(payload: dict[str, object]) -> None:
    assert payload["execution_performed"] is False
    assert payload["broker_callback_present"] is False
    assert payload["coordinator_invoked"] is False
    assert payload["lease_acquired"] is False
    assert payload["cancel_intent_reserved"] is False
    assert payload["cancel_attempted"] is False
    assert payload["broker_access_performed"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["journal_mutation_performed"] is False
    assert payload["live_authorized"] is False
    assert payload["no_submit"] is True
