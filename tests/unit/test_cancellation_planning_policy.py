import ast
import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationOrderObservation,
    CancellationPlanningBlocker,
    CancellationPlanningRequest,
    CancellationPlanningResult,
    CancellationPlanningStatus,
    plan_cancellation,
)


NOW = datetime(2026, 7, 12, 14, 30, tzinfo=timezone.utc)
MODULE_PATH = Path(
    "src/algotrader/orchestration/cancellation_planning_policy.py"
)


def request(**overrides: object) -> CancellationPlanningRequest:
    values: dict[str, object] = {
        "target_client_order_id": "client-123",
        "target_broker_order_id": "broker-456",
        "target_symbol": "BTC/USD",
        "reason": "operator-approved stale thesis exit",
        "cancellation_permitted": True,
        "snapshot_fresh": True,
        "trading_enabled": True,
        "stop_requested": False,
    }
    values.update(overrides)
    return CancellationPlanningRequest(**values)  # type: ignore[arg-type]


def observation(**overrides: object) -> CancellationOrderObservation:
    values: dict[str, object] = {
        "client_order_id": "client-123",
        "broker_order_id": "broker-456",
        "symbol": "BTC/USD",
        "broker_status": "new",
        "observed_at": NOW,
    }
    values.update(overrides)
    return CancellationOrderObservation(**values)  # type: ignore[arg-type]


def assert_blocked(
    result: CancellationPlanningResult,
    blocker: CancellationPlanningBlocker,
) -> None:
    assert result.status is CancellationPlanningStatus.BLOCKED
    assert result.blocker is blocker
    assert result.plan is None
    assert not result.planned


def test_eligible_same_order_observation_returns_one_pre_broker_plan() -> None:
    result = plan_cancellation(request(), observation())

    assert result.status is CancellationPlanningStatus.PLANNED
    assert result.blocker is None
    assert result.planned
    assert result.plan is not None
    assert result.plan.client_order_id == "client-123"
    assert result.plan.broker_order_id == "broker-456"
    assert result.plan.symbol == "BTC/USD"
    assert result.plan.broker_status == "new"
    assert result.plan.observed_at is NOW


def test_same_inputs_produce_identical_result() -> None:
    first = plan_cancellation(request(), observation())
    second = plan_cancellation(request(), observation())

    assert first == second
    assert first.to_dict() == second.to_dict()


def test_request_and_observation_normalize_identity_and_status() -> None:
    result = plan_cancellation(
        request(target_symbol=" btc/usd "),
        observation(
            symbol="btc/usd",
            broker_status="OrderStatus.PARTIALLY-FILLED",
        ),
    )

    assert result.plan is not None
    assert result.plan.symbol == "BTC/USD"
    assert result.plan.broker_status == "partially_filled"


@pytest.mark.parametrize(
    ("request_changes", "observed", "expected"),
    [
        ({"stop_requested": True}, observation(), CancellationPlanningBlocker.STOP_REQUESTED),
        ({"trading_enabled": False}, observation(), CancellationPlanningBlocker.TRADING_PAUSED),
        (
            {"cancellation_permitted": False},
            observation(),
            CancellationPlanningBlocker.CANCELLATION_NOT_PERMITTED,
        ),
        ({}, None, CancellationPlanningBlocker.OBSERVATION_MISSING),
        ({"snapshot_fresh": False}, observation(), CancellationPlanningBlocker.SNAPSHOT_NOT_FRESH),
        (
            {"target_client_order_id": ""},
            observation(),
            CancellationPlanningBlocker.TARGET_CLIENT_ORDER_ID_MISSING,
        ),
        (
            {"target_broker_order_id": ""},
            observation(),
            CancellationPlanningBlocker.TARGET_BROKER_ORDER_ID_MISSING,
        ),
        ({"target_symbol": ""}, observation(), CancellationPlanningBlocker.TARGET_SYMBOL_MISSING),
        ({"reason": ""}, observation(), CancellationPlanningBlocker.REASON_MISSING),
        (
            {},
            observation(client_order_id=""),
            CancellationPlanningBlocker.OBSERVED_CLIENT_ORDER_ID_MISSING,
        ),
        (
            {},
            observation(broker_order_id=""),
            CancellationPlanningBlocker.OBSERVED_BROKER_ORDER_ID_MISSING,
        ),
        ({}, observation(symbol=""), CancellationPlanningBlocker.OBSERVED_SYMBOL_MISSING),
        (
            {},
            observation(client_order_id="other"),
            CancellationPlanningBlocker.CLIENT_ORDER_ID_MISMATCH,
        ),
        (
            {},
            observation(broker_order_id="other"),
            CancellationPlanningBlocker.BROKER_ORDER_ID_MISMATCH,
        ),
        ({}, observation(symbol="ETH/USD"), CancellationPlanningBlocker.SYMBOL_MISMATCH),
        ({}, observation(broker_status="unknown"), CancellationPlanningBlocker.ORDER_STATUS_UNKNOWN),
        ({}, observation(broker_status="filled"), CancellationPlanningBlocker.ORDER_TERMINAL),
        (
            {},
            observation(broker_status="pending_cancel"),
            CancellationPlanningBlocker.ORDER_NOT_CANCELABLE,
        ),
    ],
)
def test_policy_returns_typed_fail_closed_blocker(
    request_changes: dict[str, object],
    observed: CancellationOrderObservation | None,
    expected: CancellationPlanningBlocker,
) -> None:
    assert_blocked(plan_cancellation(request(**request_changes), observed), expected)


@pytest.mark.parametrize("status", ["", "unknown", "ambiguous"])
def test_unknown_statuses_fail_closed(status: str) -> None:
    assert_blocked(
        plan_cancellation(request(), observation(broker_status=status)),
        CancellationPlanningBlocker.ORDER_STATUS_UNKNOWN,
    )


@pytest.mark.parametrize(
    "status",
    ["canceled", "cancelled", "done_for_day", "expired", "filled", "rejected"],
)
def test_terminal_statuses_fail_closed(status: str) -> None:
    assert_blocked(
        plan_cancellation(request(), observation(broker_status=status)),
        CancellationPlanningBlocker.ORDER_TERMINAL,
    )


def test_stop_has_precedence_over_every_other_failure() -> None:
    result = plan_cancellation(
        request(
            stop_requested=True,
            trading_enabled=False,
            cancellation_permitted=False,
            snapshot_fresh=False,
        ),
        None,
    )

    assert_blocked(result, CancellationPlanningBlocker.STOP_REQUESTED)


def test_values_are_frozen() -> None:
    planning_request = request()
    observed = observation()
    result = plan_cancellation(planning_request, observed)

    with pytest.raises(FrozenInstanceError):
        planning_request.reason = "changed"
    with pytest.raises(FrozenInstanceError):
        observed.broker_status = "filled"
    with pytest.raises(FrozenInstanceError):
        result.plan = None


def test_result_to_dict_is_explicit_for_planned_and_blocked() -> None:
    planned = plan_cancellation(request(), observation())
    blocked = plan_cancellation(request(snapshot_fresh=False), observation())

    assert planned.to_dict()["status"] == "planned"
    assert planned.to_dict()["blocker"] == ""
    assert isinstance(planned.to_dict()["plan"], dict)
    assert blocked.to_dict() == {
        "status": "blocked",
        "blocker": "snapshot_not_fresh",
        "plan": {},
    }


@pytest.mark.parametrize(
    "field_name",
    [
        "cancellation_permitted",
        "snapshot_fresh",
        "trading_enabled",
        "stop_requested",
    ],
)
@pytest.mark.parametrize("invalid", [0, 1, None, "true"])
def test_request_requires_exact_booleans(field_name: str, invalid: object) -> None:
    with pytest.raises(ValidationError, match=field_name):
        request(**{field_name: invalid})


def test_policy_rejects_wrong_input_types() -> None:
    with pytest.raises(ValidationError, match="request"):
        plan_cancellation(object(), observation())  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="observation"):
        plan_cancellation(request(), object())  # type: ignore[arg-type]


def test_result_rejects_inconsistent_states() -> None:
    planned = plan_cancellation(request(), observation())
    assert planned.plan is not None

    with pytest.raises(ValidationError):
        replace(planned, blocker=CancellationPlanningBlocker.ORDER_TERMINAL)
    with pytest.raises(ValidationError):
        CancellationPlanningResult(
            status=CancellationPlanningStatus.BLOCKED,
            plan=planned.plan,
            blocker=CancellationPlanningBlocker.ORDER_TERMINAL,
        )


def test_observation_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        observation(observed_at=datetime(2026, 7, 12, 14, 30))
    with pytest.raises(ValidationError, match="UTC"):
        observation(
            observed_at=datetime(
                2026,
                7,
                12,
                10,
                30,
                tzinfo=timezone(timedelta(hours=-4)),
            )
        )


def test_policy_signature_exposes_no_callback_or_runtime_object() -> None:
    assert tuple(inspect.signature(plan_cancellation).parameters) == (
        "request",
        "observation",
    )


def test_policy_module_has_no_mutation_runtime_or_nondeterminism() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    referenced = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    } | {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }

    assert not any(
        name.startswith(
            (
                "algotrader.execution",
                "alpaca",
                "requests",
                "httpx",
                "pathlib",
                "socket",
            )
        )
        for name in imports
    )
    assert referenced.isdisjoint(
        {
            "Broker",
            "cancel_order",
            "callback",
            "datetime.now",
            "DurableCancelCoordinator",
            "open",
            "sleep",
            "time",
            "urlopen",
        }
    )
