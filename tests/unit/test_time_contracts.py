import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from algotrader.core.time import (
    Clock,
    FixedClock,
    assert_not_after_as_of,
    require_utc_datetime,
)
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/core/time.py")

UTC_NOW = datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc)
UTC_EARLIER = datetime(2026, 5, 9, 14, 29, tzinfo=timezone.utc)
EASTERN_NOW = datetime(2026, 5, 9, 10, 30, tzinfo=timezone(timedelta(hours=-4)))

_FORBIDDEN_TIME_CONTRACT_FIELD_NAMES = {
    "account",
    "account_id",
    "alpaca",
    "broker",
    "broker_order_id",
    "buying_power",
    "buying_power_reserved",
    "cash",
    "cash_reserved",
    "client_order_id",
    "execution",
    "execution_intent",
    "execution_plan",
    "fill",
    "idempotency_key",
    "native_order",
    "order",
    "order_id",
    "portfolio",
    "position",
    "priority",
    "quantity",
    "rank",
    "ranking",
    "reservation",
    "risk",
    "risk_approval",
    "risk_approved",
    "score",
    "side",
    "submit_order",
    "symbol",
    "venue",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.scheduler",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "algotrader.ml",
    "algotrader.llm",
    "algotrader.llms",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
)

_FORBIDDEN_REFERENCE_NAMES = {
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "ExecutionIntent",
    "ExecutionPlan",
    "LocalBroker",
    "PlanningPolicyResult",
    "PortfolioState",
    "ProposedOrder",
    "RiskEngine",
    "RiskVerdict",
    "ScreenerSignalEvaluation",
    "SignalRiskEvaluation",
    "ValidatedSignalDefinition",
    "client_order_id",
    "execution_intent",
    "execution_plan",
    "fill",
    "idempotency",
    "order",
    "portfolio",
    "ranking",
    "risk_approved",
    "submit_order",
}

_FORBIDDEN_CALL_NAMES = {
    "datetime.now",
    "datetime.utcnow",
    "environ.get",
    "getenv",
    "open",
    "os.getenv",
    "random",
    "random.random",
    "read",
    "request",
    "time.monotonic",
    "time.time",
    "uuid.uuid4",
    "uuid4",
    "write",
}

_FORBIDDEN_REFERENCE_ONLY_NAMES = {
    "environ",
    "monotonic",
    "random",
    "time",
    "uuid",
    "uuid4",
}


def test_require_utc_datetime_accepts_utc_aware_datetime_and_preserves_identity() -> None:
    assert require_utc_datetime(UTC_NOW) is UTC_NOW


def test_require_utc_datetime_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        require_utc_datetime(datetime(2026, 5, 9, 14, 30))


@pytest.mark.parametrize("value", (None, "2026-05-09T14:30:00Z", object(), 123))
def test_require_utc_datetime_rejects_non_datetime_values(value: object) -> None:
    with pytest.raises(ValidationError, match="datetime"):
        require_utc_datetime(value)


def test_require_utc_datetime_rejects_non_utc_aware_datetime() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        require_utc_datetime(EASTERN_NOW)


def test_clock_protocol_can_be_satisfied_by_fixed_clock() -> None:
    def read_clock(clock: Clock) -> datetime:
        return clock.now()

    assert read_clock(FixedClock(UTC_NOW)) is UTC_NOW


def test_fixed_clock_is_frozen_and_slotted() -> None:
    clock = FixedClock(UTC_NOW)

    assert hasattr(FixedClock, "__slots__")
    assert not hasattr(clock, "__dict__")
    with pytest.raises(FrozenInstanceError):
        clock.timestamp = UTC_EARLIER


def test_fixed_clock_has_exact_timestamp_field_only() -> None:
    field_names = tuple(field.name for field in fields(FixedClock))

    assert field_names == ("timestamp",)
    assert set(field_names).isdisjoint(_FORBIDDEN_TIME_CONTRACT_FIELD_NAMES)


def test_fixed_clock_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        FixedClock(datetime(2026, 5, 9, 14, 30))


def test_fixed_clock_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        FixedClock(EASTERN_NOW)


def test_fixed_clock_now_returns_exact_stored_datetime() -> None:
    clock = FixedClock(UTC_NOW)

    assert clock.now() is UTC_NOW


def test_repeated_fixed_clock_now_calls_return_same_value() -> None:
    clock = FixedClock(UTC_NOW)

    assert clock.now() is UTC_NOW
    assert clock.now() is UTC_NOW
    assert clock.now() == UTC_NOW


def test_assert_not_after_as_of_allows_observed_before_or_equal_to_as_of() -> None:
    assert assert_not_after_as_of(UTC_EARLIER, UTC_NOW) is None
    assert assert_not_after_as_of(UTC_NOW, UTC_NOW) is None


def test_assert_not_after_as_of_rejects_observed_after_as_of() -> None:
    observed_at = datetime(2026, 5, 9, 14, 31, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="after as_of"):
        assert_not_after_as_of(observed_at, UTC_NOW)


def test_assert_not_after_as_of_rejects_naive_inputs() -> None:
    with pytest.raises(ValidationError, match="observed_at"):
        assert_not_after_as_of(datetime(2026, 5, 9, 14, 30), UTC_NOW)
    with pytest.raises(ValidationError, match="as_of"):
        assert_not_after_as_of(UTC_NOW, datetime(2026, 5, 9, 14, 30))


def test_time_contract_module_exposes_no_trading_path_fields_or_behavior() -> None:
    clock = FixedClock(UTC_NOW)

    for field_name in _FORBIDDEN_TIME_CONTRACT_FIELD_NAMES:
        assert not hasattr(clock, field_name)

    assert not hasattr(clock, "evaluate")
    assert not hasattr(clock, "compute_signal")
    assert not hasattr(clock, "submit_order")
    assert not hasattr(clock, "approve_trade")
    assert not hasattr(clock, "mutate_execution_plan")


def test_time_contract_module_imports_no_trading_path_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_time_contract_module_references_no_trading_path_runtime_or_random_types() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_ONLY_NAMES)


def test_fixed_clock_now_does_not_call_real_system_time_or_hidden_io() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)

    clock = FixedClock(UTC_NOW)

    assert clock.now() is UTC_NOW


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
