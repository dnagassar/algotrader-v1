import ast
import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.core.types import Bar, OrderSide, OrderType, ProposedOrder, Quote
from algotrader.orchestration.risk_execution_flow import (
    ExecutionIntent,
    build_execution_intents_from_risk_approved,
    select_risk_approved_evaluations,
)
from algotrader.orchestration.signal_risk_flow import SignalRiskEvaluation
from algotrader.risk.state import RiskVerdict


NOW = datetime(2026, 5, 6, tzinfo=timezone.utc)
MODULE_PATH = Path("src/algotrader/orchestration/risk_execution_flow.py")


def bar(symbol: str, close: str = "100") -> Bar:
    return Bar(symbol, NOW, close, close, close, close, "1000")


def quote(symbol: str, ask: str = "100.10") -> Quote:
    return Quote(symbol, NOW, bid=ask, ask=ask)


def order(symbol: str, quantity: str = "1") -> ProposedOrder:
    return ProposedOrder(symbol, OrderSide.BUY, OrderType.MARKET, quantity)


def risk_approved(
    symbol: str,
    quantity: str = "1",
    order_notional: str = "100.10",
) -> SignalRiskEvaluation:
    return SignalRiskEvaluation(
        symbol=symbol,
        previous_bar=bar(symbol),
        quote=quote(symbol),
        order=order(symbol, quantity),
        risk=RiskVerdict.allow(Decimal(order_notional)),
        status="risk_approved",
    )


def risk_rejected(symbol: str) -> SignalRiskEvaluation:
    return SignalRiskEvaluation(
        symbol=symbol,
        previous_bar=bar(symbol),
        quote=quote(symbol),
        order=order(symbol),
        risk=RiskVerdict.reject("test_rejection"),
        status="risk_rejected",
    )


def no_signal(symbol: str) -> SignalRiskEvaluation:
    return SignalRiskEvaluation(
        symbol=symbol,
        previous_bar=bar(symbol),
        quote=quote(symbol),
        order=None,
        risk=None,
        status="no_signal",
    )


def test_empty_input_returns_empty_tuple() -> None:
    assert select_risk_approved_evaluations(()) == ()


def test_build_execution_intents_empty_input_returns_empty_tuple() -> None:
    assert build_execution_intents_from_risk_approved(()) == ()


def test_all_no_signal_rows_return_empty_tuple() -> None:
    evaluations = (no_signal("MSFT"), no_signal("AAPL"))

    assert select_risk_approved_evaluations(evaluations) == ()


def test_no_signal_rows_produce_no_execution_intents() -> None:
    evaluations = (no_signal("MSFT"), no_signal("AAPL"))

    assert build_execution_intents_from_risk_approved(evaluations) == ()


def test_all_risk_rejected_rows_return_empty_tuple() -> None:
    evaluations = (risk_rejected("MSFT"), risk_rejected("AAPL"))

    assert select_risk_approved_evaluations(evaluations) == ()


def test_risk_rejected_rows_produce_no_execution_intents() -> None:
    evaluations = (risk_rejected("MSFT"), risk_rejected("AAPL"))

    assert build_execution_intents_from_risk_approved(evaluations) == ()


def test_all_risk_approved_rows_are_returned() -> None:
    evaluations = (risk_approved("MSFT"), risk_approved("AAPL"))

    assert select_risk_approved_evaluations(evaluations) == evaluations


def test_risk_approved_rows_produce_execution_intents() -> None:
    first = risk_approved("MSFT")
    second = risk_approved("AAPL")

    intents = build_execution_intents_from_risk_approved((first, second))

    assert intents == (
        ExecutionIntent(source_evaluation=first),
        ExecutionIntent(source_evaluation=second),
    )


def test_mixed_batch_preserves_order_of_approved_rows() -> None:
    approved_first = risk_approved("TSLA")
    approved_second = risk_approved("MSFT")
    evaluations = (
        no_signal("AAPL"),
        approved_first,
        risk_rejected("NVDA"),
        approved_second,
        no_signal("AMD"),
    )

    assert select_risk_approved_evaluations(evaluations) == (
        approved_first,
        approved_second,
    )


def test_mixed_batch_intents_preserve_approved_row_order() -> None:
    approved_first = risk_approved("TSLA")
    approved_second = risk_approved("MSFT")
    evaluations = (
        no_signal("AAPL"),
        approved_first,
        risk_rejected("NVDA"),
        approved_second,
        no_signal("AMD"),
    )

    intents = build_execution_intents_from_risk_approved(evaluations)

    assert tuple(intent.source_evaluation for intent in intents) == (
        approved_first,
        approved_second,
    )


def test_returned_rows_are_same_objects_from_input() -> None:
    approved_first = risk_approved("MSFT")
    approved_second = risk_approved("AAPL")

    selected = select_risk_approved_evaluations((approved_first, approved_second))

    assert selected[0] is approved_first
    assert selected[1] is approved_second


def test_execution_intents_preserve_source_evaluation_identity() -> None:
    approved_first = risk_approved("MSFT")
    approved_second = risk_approved("AAPL")

    intents = build_execution_intents_from_risk_approved(
        (approved_first, approved_second)
    )

    assert intents[0].source_evaluation is approved_first
    assert intents[1].source_evaluation is approved_second


def test_output_is_a_tuple() -> None:
    selected = select_risk_approved_evaluations([risk_approved("MSFT")])

    assert isinstance(selected, tuple)


def test_execution_intent_output_is_a_tuple() -> None:
    intents = build_execution_intents_from_risk_approved([risk_approved("MSFT")])

    assert isinstance(intents, tuple)


def test_execution_intent_is_frozen() -> None:
    intent = ExecutionIntent(source_evaluation=risk_approved("MSFT"))

    with pytest.raises(FrozenInstanceError):
        intent.source_evaluation = risk_approved("AAPL")


def test_inputs_are_not_mutated() -> None:
    approved = risk_approved("MSFT")
    rejected = risk_rejected("AAPL")
    evaluations = [approved, rejected]
    snapshot = tuple(evaluations)

    selected = select_risk_approved_evaluations(evaluations)

    assert evaluations == list(snapshot)
    assert evaluations[0] is approved
    assert evaluations[1] is rejected
    assert selected == (approved,)


def test_build_execution_intents_does_not_mutate_inputs() -> None:
    approved = risk_approved("MSFT")
    rejected = risk_rejected("AAPL")
    evaluations = [approved, rejected]
    snapshot = tuple(evaluations)

    intents = build_execution_intents_from_risk_approved(evaluations)

    assert evaluations == list(snapshot)
    assert evaluations[0] is approved
    assert evaluations[1] is rejected
    assert tuple(intent.source_evaluation for intent in intents) == (approved,)


def test_no_portfolio_state_is_required_or_referenced() -> None:
    parameters = tuple(inspect.signature(select_risk_approved_evaluations).parameters)

    assert parameters == ("evaluations",)
    assert "PortfolioState" not in _referenced_names()


def test_execution_intent_builder_requires_no_portfolio_state() -> None:
    parameters = tuple(
        inspect.signature(build_execution_intents_from_risk_approved).parameters
    )

    assert parameters == ("evaluations",)
    assert "PortfolioState" not in _referenced_names()


def test_no_risk_engine_is_required_or_referenced() -> None:
    parameters = tuple(inspect.signature(select_risk_approved_evaluations).parameters)

    assert parameters == ("evaluations",)
    assert "RiskEngine" not in _referenced_names()


def test_execution_intent_builder_requires_no_risk_engine() -> None:
    parameters = tuple(
        inspect.signature(build_execution_intents_from_risk_approved).parameters
    )

    assert parameters == ("evaluations",)
    assert "RiskEngine" not in _referenced_names()


def test_no_broker_or_execution_object_is_required_or_referenced() -> None:
    parameters = tuple(inspect.signature(select_risk_approved_evaluations).parameters)

    assert parameters == ("evaluations",)
    assert _referenced_names().isdisjoint(
        {
            "Broker",
            "BrokerOrderResult",
            "LocalBroker",
            "AlpacaPaperBroker",
            "Execution",
        }
    )


def test_execution_intent_builder_requires_no_broker_or_execution_object() -> None:
    parameters = tuple(
        inspect.signature(build_execution_intents_from_risk_approved).parameters
    )

    assert parameters == ("evaluations",)
    assert _referenced_names().isdisjoint(
        {
            "Broker",
            "BrokerOrderResult",
            "LocalBroker",
            "AlpacaPaperBroker",
            "Execution",
        }
    )


def test_selector_does_not_compute_or_enforce_batch_level_cumulative_cash() -> None:
    batch_cash = Decimal("100")
    evaluations = (
        risk_approved("MSFT", quantity="1", order_notional="80"),
        risk_approved("AAPL", quantity="1", order_notional="80"),
    )

    approved_notional = sum(
        evaluation.risk.order_notional
        for evaluation in evaluations
        if evaluation.risk is not None
    )

    assert approved_notional > batch_cash
    assert select_risk_approved_evaluations(evaluations) == evaluations


def test_execution_intent_builder_does_not_enforce_batch_level_cash() -> None:
    batch_cash = Decimal("100")
    first = risk_approved("MSFT", quantity="1", order_notional="80")
    second = risk_approved("AAPL", quantity="1", order_notional="80")
    evaluations = (first, second)

    approved_notional = sum(
        evaluation.risk.order_notional
        for evaluation in evaluations
        if evaluation.risk is not None
    )

    intents = build_execution_intents_from_risk_approved(evaluations)

    assert approved_notional > batch_cash
    assert tuple(intent.source_evaluation for intent in intents) == evaluations


def test_selector_does_not_resolve_same_symbol_conflicts() -> None:
    approved_first = risk_approved("MSFT", quantity="1")
    approved_second = risk_approved("MSFT", quantity="2")

    selected = select_risk_approved_evaluations((approved_first, approved_second))

    assert selected == (approved_first, approved_second)
    assert selected[0] is approved_first
    assert selected[1] is approved_second


def test_execution_intent_builder_does_not_resolve_same_symbol_conflicts() -> None:
    approved_first = risk_approved("MSFT", quantity="1")
    approved_second = risk_approved("MSFT", quantity="2")

    intents = build_execution_intents_from_risk_approved(
        (approved_first, approved_second)
    )

    assert tuple(intent.source_evaluation for intent in intents) == (
        approved_first,
        approved_second,
    )
    assert intents[0].source_evaluation is approved_first
    assert intents[1].source_evaluation is approved_second


def test_execution_intent_has_only_source_evaluation_field() -> None:
    field_names = {field.name for field in fields(ExecutionIntent)}

    assert field_names == {"source_evaluation"}
    assert field_names.isdisjoint(
        {
            "account_id",
            "broker",
            "broker_order_id",
            "client_order_id",
            "fill",
            "filled_at",
            "idempotency_key",
            "persisted_at",
            "submitted_at",
            "venue",
        }
    )


def test_selector_uses_no_trading_path_or_order_submission_logic() -> None:
    imported_modules = _imported_modules()
    referenced_names = _referenced_names()
    called_names = _called_names()

    assert imported_modules == {
        "__future__",
        "collections.abc",
        "dataclasses",
        "algotrader.orchestration.signal_risk_flow",
    }
    assert not any(
        _matches_prefix(module, _FORBIDDEN_MODULE_PREFIXES)
        for module in imported_modules
    )
    assert referenced_names.isdisjoint(_FORBIDDEN_TRADING_PATH_NAMES)
    assert called_names.isdisjoint(_FORBIDDEN_TRADING_PATH_NAMES)


_FORBIDDEN_MODULE_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration.trade_flow",
    "algotrader.orchestration.signal_trade_flow",
    "alpaca",
    "alpaca_trade_api",
    "algotrader.scheduler",
    "algotrader.persistence",
    "algotrader.ml",
    "openai",
    "anthropic",
    "langchain",
    "langgraph",
)

_FORBIDDEN_TRADING_PATH_NAMES = {
    "AlpacaPaperBroker",
    "Broker",
    "BrokerOrderResult",
    "Execution",
    "LocalBroker",
    "PortfolioState",
    "RiskEngine",
    "client_order_id",
    "create_client_order_id",
    "execute",
    "execution",
    "idempotency_key",
    "ml",
    "persist",
    "persistence",
    "scheduler",
    "submit_order",
    "trade_flow",
}


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _imported_modules() -> set[str]:
    modules: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    return modules


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _called_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call):
            names.add(_call_name(node.func))

    return names


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _matches_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in prefixes
    )
