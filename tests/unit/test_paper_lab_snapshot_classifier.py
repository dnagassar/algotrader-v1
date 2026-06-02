from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from algotrader.execution.paper_lab_snapshot_classifier import (
    CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE,
    CLASSIFICATION_STILL_OPEN_OR_ACCEPTED_AFTER_FULL_SESSION,
    CLASSIFICATION_TERMINAL_CANCELED_OR_EXPIRED,
    CLASSIFICATION_TERMINAL_FILLED,
    PaperSnapshotClassification,
    classify_paper_snapshot_record,
)


TARGET_BROKER_ORDER_ID = "56a2f690-f4ad-4572-bcf4-1a479398fe55"
TARGET_CLIENT_ORDER_ID = "paper-order-close-m355_spy_paper_close_submit"
TARGET_SYMBOL = "SPY"


def test_filled_order_classifies_terminal_filled() -> None:
    record = _snapshot_record(
        order={
            "filled_at": "2026-06-02T20:01:00+00:00",
            "filled_quantity": "0.032905647",
            "normalized_status": "filled",
        }
    )

    result = _classify(record)

    assert result.classification == CLASSIFICATION_TERMINAL_FILLED
    assert result.reason == "filled_order_with_complete_metadata"
    assert result.target_order_found is True
    assert result.target_position_found is True
    assert result.metadata_complete is True
    assert result.mutated is False
    assert result.submitted is False
    assert result.order_status == "filled"
    assert result.filled_qty == "0.032905647"
    assert result.filled_at == "2026-06-02T20:01:00+00:00"
    assert result.position_qty == "0.032905647"
    assert result.missing_fields == ()


@pytest.mark.parametrize("status", ("canceled", "expired", "rejected"))
def test_expired_canceled_or_rejected_order_classifies_terminal_nonfilled(
    status: str,
) -> None:
    record = _snapshot_record(
        order={"filled_quantity": "0", "normalized_status": "", "status": status}
    )

    result = _classify(record)

    assert result.classification == CLASSIFICATION_TERMINAL_CANCELED_OR_EXPIRED
    assert result.order_status == status
    assert result.metadata_complete is True


@pytest.mark.parametrize("status", ("accepted", "open", "new", "pending_new"))
def test_accepted_or_open_order_classifies_still_open(status: str) -> None:
    record = _snapshot_record(
        order={"normalized_status": "", "raw_status": f"OrderStatus.{status.upper()}"}
    )

    result = _classify(record)

    assert (
        result.classification
        == CLASSIFICATION_STILL_OPEN_OR_ACCEPTED_AFTER_FULL_SESSION
    )
    assert result.order_status == status
    assert result.reason == "active_order_with_complete_metadata"


def test_missing_target_order_is_ambiguous() -> None:
    record = _snapshot_record(
        order={
            "client_order_id": "other-client-order-id",
            "order_id": "other-broker-order-id",
            "symbol": "SPY",
        }
    )

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "target_order_not_found"
    assert result.target_order_found is False
    assert result.metadata_complete is True


def test_missing_orders_observation_is_ambiguous() -> None:
    record = _snapshot_record(orders_observation_available=False, recent_orders=[])

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "required_observation_or_metadata_incomplete"
    assert "orders_observation_available" in result.missing_fields


def test_missing_positions_observation_is_ambiguous() -> None:
    record = _snapshot_record(
        positions_observation_available=False,
        positions=[],
        position_symbols=[],
    )

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "required_observation_or_metadata_incomplete"
    assert "positions_observation_available" in result.missing_fields


def test_mutated_true_is_ambiguous() -> None:
    record = _snapshot_record(mutated=True)

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "mutated_missing_or_true"
    assert result.mutated is True


def test_submitted_true_is_ambiguous() -> None:
    record = _snapshot_record(submitted=True)

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "submitted_missing_or_true"
    assert result.submitted is True


def test_status_and_filled_quantity_conflict_is_ambiguous() -> None:
    record = _snapshot_record(
        order={
            "filled_at": "",
            "filled_quantity": "0.032905647",
            "normalized_status": "accepted",
        }
    )

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "filled_quantity_status_conflict"
    assert result.order_status == "accepted"
    assert result.missing_fields == ("filled_qty",)


def test_missing_mutated_or_submitted_flags_are_ambiguous() -> None:
    record = _snapshot_record()
    del record["mutated"]
    del record["submitted"]

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "mutated_missing_or_true"
    assert result.mutated is None


def test_broker_error_is_ambiguous() -> None:
    record = _snapshot_record(error="paper_lab_snapshot_unavailable")

    result = _classify(record)

    assert result.classification == CLASSIFICATION_AMBIGUOUS_OR_INCOMPLETE
    assert result.reason == "broker_response_error"


def test_result_object_is_immutable() -> None:
    result = _classify(_snapshot_record())

    with pytest.raises(FrozenInstanceError):
        result.classification = "changed"  # type: ignore[misc]


def test_classifier_does_not_mutate_input_dict() -> None:
    record = _snapshot_record()
    before = deepcopy(record)

    _classify(record)

    assert record == before


def test_classifier_has_no_network_sdk_or_credential_imports() -> None:
    path = Path("src/algotrader/execution/paper_lab_snapshot_classifier.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden_roots = {
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    forbidden_modules = {
        "algotrader.config",
        "algotrader.execution.alpaca_adapter",
        "algotrader.execution.alpaca_broker",
        "algotrader.execution.alpaca_client",
        "algotrader.execution.alpaca_sdk_client",
    }
    imported_modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert {
        module.split(".", maxsplit=1)[0] for module in imported_modules
    }.isdisjoint(forbidden_roots)
    assert set(imported_modules).isdisjoint(forbidden_modules)


def _classify(record: dict[str, object]) -> PaperSnapshotClassification:
    return classify_paper_snapshot_record(
        record,
        broker_order_id=TARGET_BROKER_ORDER_ID,
        client_order_id=TARGET_CLIENT_ORDER_ID,
        symbol=TARGET_SYMBOL,
    )


def _snapshot_record(
    *,
    order: dict[str, object] | None = None,
    recent_orders: list[dict[str, object]] | None = None,
    positions: list[dict[str, object]] | None = None,
    position_symbols: list[str] | None = None,
    account_observation_available: bool = True,
    orders_observation_available: bool = True,
    positions_observation_available: bool = True,
    recent_order_query_available: bool = True,
    recent_order_query_metadata_complete: bool = True,
    mutated: bool = False,
    submitted: bool = False,
    error: str = "",
) -> dict[str, object]:
    base_order = {
        "client_order_id": TARGET_CLIENT_ORDER_ID,
        "filled_at": "",
        "filled_quantity": "0",
        "normalized_status": "accepted",
        "order_id": TARGET_BROKER_ORDER_ID,
        "quantity": "0.032905647",
        "raw_status": "OrderStatus.ACCEPTED",
        "symbol": TARGET_SYMBOL,
    }
    if order:
        base_order.update(order)

    resolved_orders = [base_order] if recent_orders is None else recent_orders
    resolved_positions = (
        [{"average_price": "759.748", "quantity": "0.032905647", "symbol": "SPY"}]
        if positions is None
        else positions
    )
    resolved_position_symbols = (
        ["SPY"] if position_symbols is None else position_symbols
    )

    return {
        "account_observation_available": account_observation_available,
        "error": error,
        "mutated": mutated,
        "orders_observation_available": orders_observation_available,
        "position_symbols": resolved_position_symbols,
        "positions": resolved_positions,
        "positions_observation_available": positions_observation_available,
        "recent_order_query_available": recent_order_query_available,
        "recent_order_query_metadata_complete": recent_order_query_metadata_complete,
        "recent_order_query_metadata_missing_fields": [],
        "recent_orders": resolved_orders,
        "submitted": submitted,
        "unavailable_observations": [],
        "unavailable_reasons": {},
    }
