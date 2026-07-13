from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.paper_cancellation_planning_adapter import (
    PAPER_CANCELLATION_PLANNING_ARTIFACT_VERSION,
    PaperCancellationPlanningAdapterBlocker,
    PaperCancellationPlanningArtifact,
    adapt_paper_lifecycle_to_cancellation_plan,
)
from algotrader.execution.paper_order_lifecycle_replay import (
    ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT,
    ORDER_LIFECYCLE_INCONSISTENT,
    ORDER_LIFECYCLE_NOT_SEEN,
    PaperOrderLifecycleEvent,
)
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationPlanningBlocker,
    CancellationPlanningRequest,
)


AS_OF = datetime(2026, 7, 13, 19, 0, tzinfo=timezone.utc)
CLIENT_ORDER_ID = "paper-client-123"
BROKER_ORDER_ID = "paper-broker-456"
MODULE_PATH = Path(
    "src/algotrader/execution/paper_cancellation_planning_adapter.py"
)


def planning_request(**overrides: object) -> CancellationPlanningRequest:
    values: dict[str, object] = {
        "target_client_order_id": CLIENT_ORDER_ID,
        "target_broker_order_id": BROKER_ORDER_ID,
        "target_symbol": "BTC/USD",
        "reason": "explicit local lifecycle exit",
        "cancellation_permitted": True,
        "snapshot_fresh": True,
        "trading_enabled": True,
        "stop_requested": False,
    }
    values.update(overrides)
    return CancellationPlanningRequest(**values)  # type: ignore[arg-type]


def event(
    observed_at: str = "2026-07-13T14:30:00-04:00",
    *,
    client_order_id: str = CLIENT_ORDER_ID,
    broker_order_id: str = BROKER_ORDER_ID,
    status: str = "accepted",
    filled_qty: Decimal | str | int | None = "0",
    submitted: bool | None = None,
    mutated: bool | None = None,
    source: str = "local_lifecycle_fixture",
) -> PaperOrderLifecycleEvent:
    return PaperOrderLifecycleEvent(
        observed_at=observed_at,
        client_order_id=client_order_id,
        broker_order_id=broker_order_id,
        status=status,
        filled_qty=filled_qty,
        submitted=submitted,
        mutated=mutated,
        source=source,
    )


def adapt(
    events: object = None,
    *,
    request: CancellationPlanningRequest | None = None,
    as_of: datetime = AS_OF,
) -> PaperCancellationPlanningArtifact:
    lifecycle = (event(),) if events is None else events
    return adapt_paper_lifecycle_to_cancellation_plan(
        lifecycle,  # type: ignore[arg-type]
        request=planning_request() if request is None else request,
        as_of=as_of,
    )


def test_accepted_lifecycle_emits_one_deterministic_no_submit_plan() -> None:
    artifact = adapt()

    assert artifact.planned
    assert artifact.adapter_blocker is None
    assert artifact.latest_observation is not None
    assert artifact.latest_observation.client_order_id == CLIENT_ORDER_ID
    assert artifact.latest_observation.broker_order_id == BROKER_ORDER_ID
    assert artifact.latest_observation.symbol == "BTC/USD"
    assert artifact.latest_observation.broker_status == "accepted"
    assert artifact.latest_observation.observed_at == datetime(
        2026,
        7,
        13,
        18,
        30,
        tzinfo=timezone.utc,
    )
    assert artifact.planning_result is not None
    assert artifact.planning_result.plan is not None
    assert artifact.planning_result.plan.client_order_id == CLIENT_ORDER_ID
    assert artifact.planning_result.plan.broker_order_id == BROKER_ORDER_ID


def test_partial_fill_alias_is_canonicalized_and_planned() -> None:
    artifact = adapt(
        (
            event(
                status="OrderStatus.PARTIAL-FILL",
                filled_qty="0.01",
            ),
        )
    )

    assert artifact.planned
    assert artifact.latest_observation is not None
    assert artifact.latest_observation.broker_status == "partially_filled"
    assert artifact.planning_result is not None
    assert artifact.planning_result.plan is not None
    assert artifact.planning_result.plan.broker_status == "partially_filled"


def test_identical_inputs_produce_identical_artifact() -> None:
    events = (
        event("2026-07-13T14:29:00-04:00", status="submitted"),
        event(),
    )

    first = adapt(events)
    second = adapt(events)

    assert first == second
    assert first.artifact_id == second.artifact_id
    assert first.to_dict() == second.to_dict()


def test_generator_is_consumed_once_without_mutating_source_events() -> None:
    first_event = event()
    source = [first_event]

    artifact = adapt(item for item in source)

    assert source == [first_event]
    assert artifact.lifecycle_replay.observations == (first_event,)


def test_latest_valid_event_drives_observation_and_plan_identity() -> None:
    artifact = adapt(
        (
            event("2026-07-13T14:20:00-04:00", status="accepted"),
            event("2026-07-13T14:40:00-04:00", status="new"),
        )
    )

    assert artifact.latest_observation is not None
    assert artifact.latest_observation.broker_status == "new"
    assert artifact.latest_observation.observed_at == datetime(
        2026,
        7,
        13,
        18,
        40,
        tzinfo=timezone.utc,
    )
    assert artifact.planning_result is not None
    assert artifact.planning_result.plan is not None
    assert artifact.planning_result.plan.broker_status == "new"


@pytest.mark.parametrize(
    ("request_changes", "expected"),
    [
        ({"stop_requested": True}, CancellationPlanningBlocker.STOP_REQUESTED),
        ({"trading_enabled": False}, CancellationPlanningBlocker.TRADING_PAUSED),
        (
            {"cancellation_permitted": False},
            CancellationPlanningBlocker.CANCELLATION_NOT_PERMITTED,
        ),
    ],
)
def test_runtime_controls_keep_policy_precedence_even_for_ambiguous_lifecycle(
    request_changes: dict[str, object],
    expected: CancellationPlanningBlocker,
) -> None:
    ambiguous = (
        event(
            status="submit_exception",
            filled_qty=None,
            submitted=True,
            mutated=True,
        ),
    )

    artifact = adapt(ambiguous, request=planning_request(**request_changes))

    assert not artifact.planned
    assert artifact.adapter_blocker is None
    assert artifact.lifecycle_replay.final_state == (
        ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT
    )
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is expected


def test_empty_lifecycle_returns_policy_observation_missing() -> None:
    artifact = adapt(())

    assert not artifact.planned
    assert artifact.adapter_blocker is None
    assert artifact.lifecycle_replay.final_state == ORDER_LIFECYCLE_NOT_SEEN
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is (
        CancellationPlanningBlocker.OBSERVATION_MISSING
    )


def test_not_seen_lifecycle_returns_policy_observation_missing() -> None:
    artifact = adapt((event(status="not_seen", filled_qty=None),))

    assert artifact.adapter_blocker is None
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is (
        CancellationPlanningBlocker.OBSERVATION_MISSING
    )


def test_stale_snapshot_is_blocked_by_existing_policy() -> None:
    artifact = adapt(request=planning_request(snapshot_fresh=False))

    assert artifact.adapter_blocker is None
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is (
        CancellationPlanningBlocker.SNAPSHOT_NOT_FRESH
    )


@pytest.mark.parametrize(
    ("request_changes", "expected"),
    [
        (
            {"target_client_order_id": "other-client"},
            CancellationPlanningBlocker.CLIENT_ORDER_ID_MISMATCH,
        ),
        (
            {"target_broker_order_id": "other-broker"},
            CancellationPlanningBlocker.BROKER_ORDER_ID_MISMATCH,
        ),
    ],
)
def test_target_identity_mismatch_is_blocked_by_existing_policy(
    request_changes: dict[str, object],
    expected: CancellationPlanningBlocker,
) -> None:
    artifact = adapt(request=planning_request(**request_changes))

    assert artifact.adapter_blocker is None
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is expected


def test_missing_observed_broker_identity_fails_closed_in_policy() -> None:
    artifact = adapt((event(broker_order_id=""),))

    assert artifact.latest_observation is not None
    assert artifact.latest_observation.broker_order_id == ""
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is (
        CancellationPlanningBlocker.OBSERVED_BROKER_ORDER_ID_MISSING
    )


@pytest.mark.parametrize(
    ("status", "filled_qty"),
    [
        ("filled", "0.1"),
        ("rejected", "0"),
        ("canceled", "0"),
        ("expired", "0"),
    ],
)
def test_terminal_lifecycle_is_blocked_by_policy(
    status: str,
    filled_qty: str,
) -> None:
    artifact = adapt((event(status=status, filled_qty=filled_qty),))

    assert artifact.adapter_blocker is None
    assert artifact.lifecycle_replay.terminal
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is (
        CancellationPlanningBlocker.ORDER_TERMINAL
    )


@pytest.mark.parametrize("status", ["held", "open", "pending_replace", "submitted"])
def test_non_cancelable_lifecycle_status_fails_closed(status: str) -> None:
    artifact = adapt((event(status=status),))

    assert artifact.adapter_blocker is None
    assert artifact.planning_result is not None
    assert artifact.planning_result.blocker is (
        CancellationPlanningBlocker.ORDER_NOT_CANCELABLE
    )


@pytest.mark.parametrize(
    "conflicting_event",
    [
        event(
            "2026-07-13T14:40:00-04:00",
            client_order_id="other-client",
        ),
        event(
            "2026-07-13T14:40:00-04:00",
            broker_order_id="other-broker",
        ),
    ],
)
def test_conflicting_lifecycle_identity_blocks_before_policy(
    conflicting_event: PaperOrderLifecycleEvent,
) -> None:
    artifact = adapt((event(), conflicting_event))

    assert artifact.lifecycle_replay.final_state == ORDER_LIFECYCLE_INCONSISTENT
    assert artifact.adapter_blocker is (
        PaperCancellationPlanningAdapterBlocker.LIFECYCLE_INCONSISTENT
    )
    assert artifact.latest_observation is None
    assert artifact.planning_result is None


def test_ambiguous_submit_blocks_before_policy() -> None:
    artifact = adapt(
        (
            event(
                status="ambiguous_submit_exception",
                filled_qty=None,
                submitted=True,
                mutated=True,
            ),
        )
    )

    assert artifact.adapter_blocker is (
        PaperCancellationPlanningAdapterBlocker.LIFECYCLE_AMBIGUOUS
    )
    assert artifact.planning_result is None


@pytest.mark.parametrize("observed_at", ["", "not-a-time", "2026-07-13T18:30:00"])
def test_invalid_event_timestamp_blocks_adapter(observed_at: str) -> None:
    artifact = adapt((event(observed_at),))

    assert artifact.adapter_blocker is (
        PaperCancellationPlanningAdapterBlocker.EVENT_TIMESTAMP_INVALID
    )
    assert artifact.planning_result is None


def test_event_after_explicit_as_of_blocks_adapter() -> None:
    artifact = adapt((event("2026-07-13T15:30:00-04:00"),))

    assert artifact.adapter_blocker is (
        PaperCancellationPlanningAdapterBlocker.EVENT_TIMESTAMP_AFTER_AS_OF
    )


def test_event_time_regression_blocks_adapter() -> None:
    artifact = adapt(
        (
            event("2026-07-13T14:40:00-04:00"),
            event("2026-07-13T14:30:00-04:00"),
        )
    )

    assert artifact.adapter_blocker is (
        PaperCancellationPlanningAdapterBlocker.EVENT_TIMESTAMP_REGRESSION
    )


def test_artifact_is_frozen_and_has_only_evidence_fields() -> None:
    artifact = adapt()

    assert tuple(field.name for field in fields(PaperCancellationPlanningArtifact)) == (
        "artifact_id",
        "as_of",
        "request",
        "lifecycle_replay",
        "latest_observation",
        "planning_result",
        "adapter_blocker",
    )
    with pytest.raises(FrozenInstanceError):
        artifact.artifact_id = "changed"
    for forbidden in (
        "broker",
        "callback",
        "coordinator",
        "journal",
        "order_request",
        "response",
    ):
        assert not hasattr(artifact, forbidden)


def test_forged_artifact_id_is_rejected() -> None:
    artifact = adapt()

    with pytest.raises(ValidationError, match="artifact_id"):
        replace(artifact, artifact_id="paper_cancel_plan_artifact_forged")


def test_to_dict_is_primitive_and_explicitly_no_submit() -> None:
    payload = adapt().to_dict()

    assert payload["artifact_version"] == (
        PAPER_CANCELLATION_PLANNING_ARTIFACT_VERSION
    )
    assert payload["status"] == "planned"
    assert payload["no_submit"] is True
    assert payload["cancel_attempted"] is False
    assert payload["broker_access_performed"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["adapter_blocker"] == ""
    _assert_primitive(payload)


def test_artifact_identity_changes_when_explicit_as_of_changes() -> None:
    later_as_of = AS_OF + timedelta(minutes=1)

    assert adapt().artifact_id != adapt(as_of=later_as_of).artifact_id


def test_adapter_rejects_invalid_runtime_types() -> None:
    with pytest.raises(ValidationError, match="request"):
        adapt_paper_lifecycle_to_cancellation_plan(
            (event(),),
            request=object(),  # type: ignore[arg-type]
            as_of=AS_OF,
        )
    with pytest.raises(ValidationError, match="as_of"):
        adapt(as_of=datetime(2026, 7, 13, 19, 0))
    with pytest.raises(ValidationError, match="PaperOrderLifecycleEvent"):
        adapt((object(),))


def test_adapter_signature_has_no_callback_io_or_broker_parameter() -> None:
    assert tuple(
        inspect.signature(
            adapt_paper_lifecycle_to_cancellation_plan
        ).parameters
    ) == ("events", "request", "as_of")


def test_module_has_no_io_network_broker_or_mutation_boundary() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))
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
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert not any(
        name.startswith(
            (
                "algotrader.execution.durable_cancel",
                "algotrader.execution.order_journal",
                "algotrader.execution.alpaca",
                "alpaca",
                "httpx",
                "pathlib",
                "requests",
                "socket",
                "subprocess",
                "urllib",
            )
        )
        for name in imports
    )
    assert call_names.isdisjoint(
        {
            "cancel_order",
            "open",
            "Path",
            "replace_order",
            "submit_order",
            "urlopen",
        }
    )
    assert "DurableCancelCoordinator" not in source


def _assert_primitive(value: object) -> None:
    if isinstance(value, dict):
        assert all(isinstance(key, str) for key in value)
        for nested in value.values():
            _assert_primitive(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _assert_primitive(nested)
        return
    assert value is None or isinstance(value, (str, bool, int, float))


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
