import ast
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.external_intake import (
    EXTERNAL_RESEARCH_SOURCE_TYPES,
    ExternalResearchIntake,
)


MODULE_PATH = Path("src/algotrader/research/external_intake.py")

_FORBIDDEN_INTAKE_FIELD_NAMES = {
    "account",
    "account_id",
    "alpaca",
    "alpaca_order",
    "benchmark",
    "broker",
    "broker_name",
    "broker_order_id",
    "buying_power",
    "capital_allocation",
    "cash",
    "cash_reserved",
    "client_order_id",
    "execution",
    "execution_plan",
    "fill",
    "fill_price",
    "fill_quantity",
    "filled",
    "metrics",
    "order",
    "order_id",
    "orders",
    "portfolio",
    "portfolio_state",
    "position",
    "position_size",
    "profitability",
    "profitable",
    "quantity",
    "request_url",
    "result_metrics",
    "risk",
    "runtime",
    "scheduler",
    "signal",
    "source_approved",
    "strategy_approved",
    "submit_order",
    "symbol",
    "trading_ready",
    "validated",
    "validation_status",
}

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
    "account_id",
    "alpaca",
    "benchmark",
    "broker",
    "capital_allocation",
    "cash",
    "download",
    "evaluator",
    "execution",
    "execution_plan",
    "fill",
    "metrics",
    "portfolio",
    "position_size",
    "profitability",
    "ranking",
    "request",
    "runtime",
    "signal_definition",
    "submit_order",
    "symbol",
    "trading_ready",
    "validated",
    "validation_status",
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


def intake(**overrides: object) -> ExternalResearchIntake:
    values: dict[str, object] = {
        "source_name": "Perplexity research note",
        "source_type": "perplexity",
        "strategy_name": "Broad ETF moving average candidate",
        "summary": "Exploratory external note captured for local review only.",
        "universe": ("SPY", "EFA", "IEF"),
        "timeframe": "monthly",
        "assumptions": ("External context is advisory metadata only.",),
        "limitations": ("Requires separate local evidence review.",),
        "evidence_links": ("https://example.invalid/research-note",),
        "created_at": date(2026, 5, 15),
    }
    values.update(overrides)
    return ExternalResearchIntake(**values)


def test_valid_external_research_intake_construction() -> None:
    item = intake()

    assert item.source_name == "Perplexity research note"
    assert item.source_type == "perplexity"
    assert item.strategy_name == "Broad ETF moving average candidate"
    assert item.universe == ("SPY", "EFA", "IEF")
    assert item.created_at == date(2026, 5, 15)
    assert item.advisory_only is True


@pytest.mark.parametrize("source_type", EXTERNAL_RESEARCH_SOURCE_TYPES)
def test_allowed_source_types_are_accepted(source_type: str) -> None:
    item = intake(source_type=source_type)

    assert item.source_type == source_type


def test_unknown_source_type_is_rejected() -> None:
    with pytest.raises(ValidationError, match="source_type"):
        intake(source_type="hosted_backtest_platform")


@pytest.mark.parametrize("value", (False, 1, "true", None))
def test_advisory_only_must_be_exactly_true(value: object) -> None:
    with pytest.raises(ValidationError, match="advisory_only"):
        intake(advisory_only=value)


def test_intake_is_frozen_and_slotted() -> None:
    item = intake()

    assert hasattr(ExternalResearchIntake, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.summary = "changed"


def test_tuple_inputs_are_copied_and_stored_as_immutable_tuples() -> None:
    universe = ["SPY"]
    assumptions = ["external context only"]
    limitations = ["requires local review"]
    evidence_links = ["https://example.invalid/note"]

    item = intake(
        universe=universe,
        assumptions=assumptions,
        limitations=limitations,
        evidence_links=evidence_links,
    )
    universe.append("QQQ")
    assumptions.append("late assumption")
    limitations.append("late limitation")
    evidence_links.append("https://example.invalid/late")

    assert item.universe == ("SPY",)
    assert item.assumptions == ("external context only",)
    assert item.limitations == ("requires local review",)
    assert item.evidence_links == ("https://example.invalid/note",)
    with pytest.raises(TypeError):
        item.universe[0] = "QQQ"


@pytest.mark.parametrize(
    "field_name",
    ("source_name", "source_type", "strategy_name", "summary", "timeframe"),
)
def test_empty_required_strings_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        intake(**{field_name: " "})


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("universe", ("SPY", "")),
        ("universe", "SPY"),
        ("universe", ("SPY", 42)),
        ("assumptions", ("external context only", " ")),
        ("assumptions", "external context only"),
        ("limitations", ("requires local review", "")),
        ("limitations", "requires local review"),
        ("evidence_links", ("https://example.invalid/note", None)),
        ("evidence_links", "https://example.invalid/note"),
    ),
)
def test_malformed_tuple_fields_are_rejected(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        intake(**{field_name: value})


class CustomDate(date):
    pass


@pytest.mark.parametrize(
    "value",
    (
        datetime(2026, 5, 15, 9, 30),
        True,
        "2026-05-15",
        CustomDate(2026, 5, 15),
    ),
)
def test_created_at_must_be_plain_date(value: object) -> None:
    with pytest.raises(ValidationError, match="created_at"):
        intake(created_at=value)


def test_to_dict_returns_deterministic_json_compatible_metadata_shape() -> None:
    payload = intake().to_dict()

    assert tuple(payload) == (
        "source_name",
        "source_type",
        "strategy_name",
        "summary",
        "universe",
        "timeframe",
        "assumptions",
        "limitations",
        "evidence_links",
        "created_at",
        "advisory_only",
    )
    assert payload == {
        "source_name": "Perplexity research note",
        "source_type": "perplexity",
        "strategy_name": "Broad ETF moving average candidate",
        "summary": "Exploratory external note captured for local review only.",
        "universe": ["SPY", "EFA", "IEF"],
        "timeframe": "monthly",
        "assumptions": ["External context is advisory metadata only."],
        "limitations": ["Requires separate local evidence review."],
        "evidence_links": ["https://example.invalid/research-note"],
        "created_at": "2026-05-15",
        "advisory_only": True,
    }


def test_from_dict_round_trips_dates_tuples_and_equality() -> None:
    item = intake(source_type="notebook", created_at=date(2026, 5, 14))

    reloaded = ExternalResearchIntake.from_dict(item.to_dict())

    assert reloaded == item
    assert reloaded.created_at == date(2026, 5, 14)
    assert reloaded.universe == ("SPY", "EFA", "IEF")
    assert reloaded.assumptions == ("External context is advisory metadata only.",)
    assert reloaded.limitations == ("Requires separate local evidence review.",)
    assert reloaded.evidence_links == ("https://example.invalid/research-note",)


def test_from_dict_rejects_non_dict_payloads() -> None:
    with pytest.raises(ValidationError, match="payload"):
        ExternalResearchIntake.from_dict(["not", "a", "dict"])


def test_from_dict_rejects_unknown_fields() -> None:
    payload = intake().to_dict()
    payload["broker_order_id"] = "abc-123"

    with pytest.raises(ValidationError, match="unknown external research intake field"):
        ExternalResearchIntake.from_dict(payload)


@pytest.mark.parametrize("field_name", ("summary", "advisory_only"))
def test_from_dict_rejects_missing_required_fields(field_name: str) -> None:
    payload = intake().to_dict()
    del payload[field_name]

    with pytest.raises(ValidationError, match="missing external research intake field"):
        ExternalResearchIntake.from_dict(payload)


@pytest.mark.parametrize(
    "value",
    ("2026-13-15", "20260515", "2026-05-15T00:00:00", date(2026, 5, 15)),
)
def test_from_dict_rejects_malformed_dates(value: object) -> None:
    payload = intake().to_dict()
    payload["created_at"] = value

    with pytest.raises(ValidationError, match="created_at"):
        ExternalResearchIntake.from_dict(payload)


def test_to_dict_does_not_share_mutable_lists_with_intake() -> None:
    item = intake()
    payload = item.to_dict()

    payload["universe"].append("QQQ")
    payload["assumptions"].append("late assumption")
    payload["limitations"].append("late limitation")
    payload["evidence_links"].append("https://example.invalid/late")

    assert item.universe == ("SPY", "EFA", "IEF")
    assert item.assumptions == ("External context is advisory metadata only.",)
    assert item.limitations == ("Requires separate local evidence review.",)
    assert item.evidence_links == ("https://example.invalid/research-note",)


def test_from_dict_does_not_share_mutable_lists_with_reloaded_intake() -> None:
    payload = intake().to_dict()
    item = ExternalResearchIntake.from_dict(payload)

    payload["universe"].append("QQQ")
    payload["assumptions"].append("late assumption")
    payload["limitations"].append("late limitation")
    payload["evidence_links"].append("https://example.invalid/late")

    assert item.universe == ("SPY", "EFA", "IEF")
    assert item.assumptions == ("External context is advisory metadata only.",)
    assert item.limitations == ("Requires separate local evidence review.",)
    assert item.evidence_links == ("https://example.invalid/research-note",)


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("summary", "Sharpe ratio was reported as 1.2."),
        ("summary", "Approved for live trading by the external tool."),
        ("summary", "Submit order after the crossing event."),
        ("summary", "Position sizing uses target weight values."),
        ("summary", "API key appears in copied hosted output."),
        ("evidence_links", ("https://example.invalid/report?token=secret",)),
    ),
)
def test_forbidden_content_guardrails_reject_non_advisory_metadata(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match="non-advisory"):
        intake(**{field_name: value})


def test_intake_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(ExternalResearchIntake))

    assert field_names == (
        "source_name",
        "source_type",
        "strategy_name",
        "summary",
        "universe",
        "timeframe",
        "assumptions",
        "limitations",
        "evidence_links",
        "created_at",
        "advisory_only",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_INTAKE_FIELD_NAMES)


def test_intake_exposes_no_trading_path_or_result_attributes() -> None:
    item = intake()

    for field_name in _FORBIDDEN_INTAKE_FIELD_NAMES:
        assert not hasattr(item, field_name)


def test_contract_module_imports_no_trading_path_vendor_network_or_data_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_trading_path_runtime_or_result_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_contract_makes_no_io_network_broker_vendor_or_ingestion_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)

    item = intake()

    assert item.source_type == "perplexity"


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
