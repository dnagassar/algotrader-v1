import ast
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.asof import (
    AsofObservation,
    iter_asof_available,
    next_available_asof_date,
)


MODULE_PATH = Path("src/algotrader/research/asof.py")

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_REFERENCE_NAMES = {
    "AlpacaPaperBroker",
    "ExecutionIntent",
    "ExecutionPlan",
    "LocalBroker",
    "PortfolioState",
    "ProposedOrder",
    "RiskEngine",
    "RiskVerdict",
    "ValidatedResearchArtifact",
    "ValidatedSignalDefinition",
    "alpaca",
    "benchmark",
    "broker",
    "cash",
    "download",
    "evaluator",
    "execution",
    "execution_plan",
    "fill",
    "portfolio",
    "ranking",
    "request",
    "runtime",
    "signal_definition",
    "strategy",
    "submit_order",
    "symbol",
    "trading_ready",
    "validated",
    "validation_status",
    "vectorbt",
    "vendor",
}

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "environ.get",
    "get",
    "getenv",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "read_csv",
    "request",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "write",
}


class CustomDate(date):
    pass


def obs(
    observation_date: date,
    available_after: date | None = None,
) -> AsofObservation:
    return AsofObservation(
        observation_date=observation_date,
        available_after=available_after or observation_date,
    )


def test_asof_observation_is_frozen_slotted_and_minimal() -> None:
    item = obs(date(2026, 1, 2), date(2026, 1, 5))
    field_names = tuple(field.name for field in fields(AsofObservation))

    assert field_names == ("observation_date", "available_after")
    assert hasattr(AsofObservation, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.available_after = date(2026, 1, 6)


def test_available_after_must_not_precede_observation_date() -> None:
    with pytest.raises(ValidationError, match="available_after"):
        AsofObservation(
            observation_date=date(2026, 1, 3),
            available_after=date(2026, 1, 2),
        )


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("observation_date", datetime(2026, 1, 2, 12, 0)),
        ("available_after", datetime(2026, 1, 3, 12, 0)),
        ("observation_date", True),
        ("available_after", False),
        ("observation_date", CustomDate(2026, 1, 2)),
        ("available_after", CustomDate(2026, 1, 3)),
        ("observation_date", "2026-01-02"),
    ),
)
def test_asof_observation_requires_plain_dates(
    field_name: str,
    value: object,
) -> None:
    values: dict[str, object] = {
        "observation_date": date(2026, 1, 2),
        "available_after": date(2026, 1, 3),
    }
    values[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        AsofObservation(**values)


def test_no_lookahead_filter_uses_available_after_not_observation_date() -> None:
    first = obs(date(2026, 1, 1), date(2026, 1, 3))
    second = obs(date(2026, 1, 2), date(2026, 1, 2))
    third = obs(date(2026, 1, 4), date(2026, 1, 5))

    result = iter_asof_available((first, second, third), date(2026, 1, 2))

    assert result == (second,)
    assert result[0] is second


def test_asof_filter_preserves_original_order_for_available_observations() -> None:
    first = obs(date(2026, 1, 1), date(2026, 1, 3))
    second = obs(date(2026, 1, 2), date(2026, 1, 2))
    third = obs(date(2026, 1, 3), date(2026, 1, 3))

    result = iter_asof_available((first, second, third), date(2026, 1, 3))

    assert result == (first, second, third)


def test_asof_filter_returns_immutable_tuple_output() -> None:
    first = obs(date(2026, 2, 1), date(2026, 2, 2))
    result = iter_asof_available([first], date(2026, 2, 2))

    assert isinstance(result, tuple)
    with pytest.raises(TypeError):
        result[0] = obs(date(2026, 2, 3))


def test_empty_asof_filter_returns_empty_tuple() -> None:
    result = iter_asof_available((), date(2026, 2, 2))

    assert result == ()
    assert isinstance(result, tuple)


def test_duplicate_observation_dates_are_rejected() -> None:
    observations = (
        obs(date(2026, 3, 1), date(2026, 3, 1)),
        obs(date(2026, 3, 1), date(2026, 3, 2)),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        iter_asof_available(observations, date(2026, 3, 2))


def test_unordered_observation_sequences_are_rejected() -> None:
    observations = (
        obs(date(2026, 3, 2), date(2026, 3, 2)),
        obs(date(2026, 3, 1), date(2026, 3, 1)),
    )

    with pytest.raises(ValidationError, match="ordered"):
        iter_asof_available(observations, date(2026, 3, 2))


@pytest.mark.parametrize(
    "observations",
    (
        (object(),),
        ("not an observation",),
        "not observations",
        None,
    ),
)
def test_malformed_observation_sequences_are_rejected(
    observations: object,
) -> None:
    with pytest.raises(ValidationError):
        iter_asof_available(observations, date(2026, 4, 1))


@pytest.mark.parametrize(
    "asof_date",
    (
        datetime(2026, 4, 1, 12, 0),
        True,
        CustomDate(2026, 4, 1),
        "2026-04-01",
    ),
)
def test_asof_date_must_be_plain_date(asof_date: object) -> None:
    with pytest.raises(ValidationError, match="asof_date"):
        iter_asof_available((obs(date(2026, 4, 1)),), asof_date)


def test_next_available_asof_date_returns_earliest_availability() -> None:
    observations = (
        obs(date(2026, 5, 1), date(2026, 5, 5)),
        obs(date(2026, 5, 2), date(2026, 5, 3)),
        obs(date(2026, 5, 4), date(2026, 5, 4)),
    )

    assert next_available_asof_date(observations) == date(2026, 5, 3)


def test_next_available_asof_date_rejects_empty_sequences() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        next_available_asof_date(())


def test_next_available_asof_date_reuses_sequence_validation() -> None:
    observations = (
        obs(date(2026, 6, 2), date(2026, 6, 2)),
        obs(date(2026, 6, 1), date(2026, 6, 1)),
    )

    with pytest.raises(ValidationError, match="ordered"):
        next_available_asof_date(observations)


def test_replay_snapshots_are_deterministic_and_synthetic_only() -> None:
    first = obs(date(2026, 7, 1), date(2026, 7, 2))
    second = obs(date(2026, 7, 2), date(2026, 7, 4))
    third = obs(date(2026, 7, 3), date(2026, 7, 3))
    observations = (first, second, third)
    replay_dates = (
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
        date(2026, 7, 4),
    )

    first_run = tuple(
        iter_asof_available(observations, replay_date)
        for replay_date in replay_dates
    )
    second_run = tuple(
        iter_asof_available(observations, replay_date)
        for replay_date in replay_dates
    )

    assert first_run == second_run
    assert first_run == (
        (),
        (first,),
        (first, third),
        (first, second, third),
    )
    assert first_run[-1][0] is first
    assert first_run[-1][1] is second
    assert first_run[-1][2] is third


def test_contract_module_imports_no_trading_path_vendor_network_or_data_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_trading_path_runtime_or_vendor_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_contract_makes_no_io_network_broker_vendor_or_ingestion_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)

    item = obs(date(2026, 8, 1), date(2026, 8, 1))

    assert item.available_after == date(2026, 8, 1)


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
