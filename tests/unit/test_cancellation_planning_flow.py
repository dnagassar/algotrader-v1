import ast
import inspect
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.orchestration.cancellation_planning_flow import (
    CANCELABLE_CANCELLATION_STATUSES,
    CancellationPlan,
    build_cancellation_plan,
)


NOW = datetime(2026, 7, 12, 14, 30, tzinfo=timezone.utc)
MODULE_PATH = Path(
    "src/algotrader/orchestration/cancellation_planning_flow.py"
)


def plan(**overrides: object) -> CancellationPlan:
    values: dict[str, object] = {
        "client_order_id": "client-123",
        "broker_order_id": "broker-456",
        "symbol": "BTC/USD",
        "broker_status": "new",
        "observed_at": NOW,
        "reason": "operator-approved stale thesis exit",
    }
    values.update(overrides)
    return build_cancellation_plan(**values)  # type: ignore[arg-type]


def test_builder_returns_normalized_same_order_plan() -> None:
    result = plan(symbol=" btc/usd ", broker_status="OrderStatus.PARTIALLY FILLED")

    assert result.client_order_id == "client-123"
    assert result.broker_order_id == "broker-456"
    assert result.symbol == "BTC/USD"
    assert result.broker_status == "partially_filled"
    assert result.observed_at is NOW
    assert result.reason == "operator-approved stale thesis exit"
    assert result.plan_id.startswith("cancel_plan_")


def test_same_inputs_produce_identical_plan_and_identity() -> None:
    first = plan()
    second = plan()

    assert first == second
    assert first.plan_id == second.plan_id
    assert first.to_dict() == second.to_dict()


@pytest.mark.parametrize(
    ("field_name", "changed_value"),
    [
        ("client_order_id", "client-other"),
        ("broker_order_id", "broker-other"),
        ("symbol", "ETH/USD"),
        ("broker_status", "partially_filled"),
        ("observed_at", NOW + timedelta(seconds=1)),
        ("reason", "different explicit reason"),
    ],
)
def test_each_identity_field_changes_plan_id(
    field_name: str,
    changed_value: object,
) -> None:
    assert plan(**{field_name: changed_value}).plan_id != plan().plan_id


def test_plan_is_frozen_and_has_only_pre_broker_fields() -> None:
    result = plan()

    assert tuple(field.name for field in fields(CancellationPlan)) == (
        "plan_id",
        "client_order_id",
        "broker_order_id",
        "symbol",
        "broker_status",
        "observed_at",
        "reason",
    )
    with pytest.raises(FrozenInstanceError):
        result.reason = "mutated"
    for forbidden in (
        "account_id",
        "broker",
        "callback",
        "cancel_order",
        "execute",
        "journal",
        "request",
        "response",
        "sdk_order",
    ):
        assert not hasattr(result, forbidden)


def test_to_dict_is_primitive_only_and_stable() -> None:
    result = plan()

    assert result.to_dict() == {
        "plan_id": result.plan_id,
        "client_order_id": "client-123",
        "broker_order_id": "broker-456",
        "symbol": "BTC/USD",
        "broker_status": "new",
        "observed_at": "2026-07-12T14:30:00+00:00",
        "reason": "operator-approved stale thesis exit",
    }
    assert all(isinstance(value, str) for value in result.to_dict().values())


@pytest.mark.parametrize(
    "overrides",
    [
        {"client_order_id": "  "},
        {"broker_order_id": ""},
        {"symbol": ""},
        {"reason": "\t"},
        {"broker_status": "filled"},
        {"broker_status": "pending_cancel"},
        {"observed_at": datetime(2026, 7, 12, 14, 30)},
        {
            "observed_at": datetime(
                2026,
                7,
                12,
                10,
                30,
                tzinfo=timezone(timedelta(hours=-4)),
            )
        },
    ],
)
def test_builder_rejects_invalid_plan_inputs(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        plan(**overrides)


def test_direct_construction_rejects_forged_plan_id() -> None:
    original = plan()

    with pytest.raises(ValidationError, match="plan_id"):
        replace(original, plan_id="cancel_plan_forged")


def test_all_declared_cancelable_statuses_build() -> None:
    assert {
        plan(broker_status=status).broker_status
        for status in CANCELABLE_CANCELLATION_STATUSES
    } == set(CANCELABLE_CANCELLATION_STATUSES)


def test_builder_signature_has_only_explicit_local_values() -> None:
    assert tuple(inspect.signature(build_cancellation_plan).parameters) == (
        "client_order_id",
        "broker_order_id",
        "symbol",
        "broker_status",
        "observed_at",
        "reason",
    )


def test_module_has_no_execution_network_or_callback_boundary() -> None:
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
        name.startswith(("algotrader.execution", "alpaca", "requests", "httpx"))
        for name in imports
    )
    assert referenced.isdisjoint(
        {
            "Broker",
            "cancel_order",
            "callback",
            "DurableCancelCoordinator",
            "requests",
            "socket",
            "urlopen",
        }
    )
