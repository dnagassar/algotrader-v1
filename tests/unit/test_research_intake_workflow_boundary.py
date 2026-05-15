import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.asof import AsofObservation
from algotrader.research.external_intake import (
    EXTERNAL_RESEARCH_SOURCE_TYPES,
    ExternalResearchIntake,
)
from algotrader.research.fixture_manifest import ResearchFixtureManifest
from algotrader.research.replay import SyntheticReplayPoint
from algotrader.research.replay_result import SyntheticResearchResult
from algotrader.research.workflow import build_synthetic_research_workflow_result


RESEARCH_PATH_MODULES = (
    Path("src/algotrader/research/external_intake.py"),
    Path("src/algotrader/research/fixture_manifest.py"),
    Path("src/algotrader/research/asof.py"),
    Path("src/algotrader/research/return_construction.py"),
    Path("src/algotrader/research/replay.py"),
    Path("src/algotrader/research/replay_metrics.py"),
    Path("src/algotrader/research/replay_result.py"),
    Path("src/algotrader/research/workflow.py"),
)

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.backtest",
    "algotrader.backtesting",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.data",
    "algotrader.database",
    "algotrader.execution",
    "algotrader.ingestion",
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
    "backtesting",
    "backtrader",
    "database",
    "duckdb",
    "google.generativeai",
    "httpx",
    "keras",
    "langchain",
    "langgraph",
    "lightgbm",
    "llm",
    "numpy",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "sklearn",
    "socket",
    "sqlmodel",
    "tensorflow",
    "torch",
    "urllib",
    "vectorbt",
    "xgboost",
    "yfinance",
    "zipline",
)

_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "environ.get",
    "fit",
    "get",
    "getenv",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read",
    "read_csv",
    "request",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "write",
}

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
    "backtest",
    "backtesting",
    "benchmark_result",
    "broker",
    "broker_order_id",
    "client_order_id",
    "download",
    "evaluator",
    "execution_plan",
    "fill",
    "order_instruction",
    "portfolio",
    "position_sizing",
    "profitability",
    "real_data",
    "runtime",
    "scheduler",
    "signal_evaluator",
    "submit_order",
    "trading_ready",
    "validation_status",
}

_FORBIDDEN_SYNTHETIC_PAYLOAD_FIELDS = {
    "approval",
    "approved",
    "backtest",
    "benchmark",
    "benchmark_claim",
    "broker",
    "order",
    "order_instruction",
    "position_size",
    "position_sizing",
    "profit",
    "profitability",
    "profitable",
    "strategy_approval",
    "trade",
    "trading",
    "trading_ready",
    "validation",
    "validation_status",
}


def external_intake(**overrides: object) -> ExternalResearchIntake:
    values: dict[str, object] = {
        "source_name": "Perplexity advisory note",
        "source_type": "perplexity",
        "strategy_name": "Broad ETF moving average candidate",
        "summary": "External note captured only as advisory research metadata.",
        "universe": ("SPY", "EFA", "IEF"),
        "timeframe": "monthly",
        "assumptions": ("Requires local deterministic review before use.",),
        "limitations": ("External output is not a validation artifact.",),
        "evidence_links": ("https://example.invalid/advisory-note",),
        "created_at": date(2026, 5, 15),
    }
    values.update(overrides)
    return ExternalResearchIntake(**values)


def manifest(**overrides: object) -> ResearchFixtureManifest:
    values: dict[str, object] = {
        "fixture_id": "synthetic-boundary-fixture-001",
        "fixture_kind": "synthetic",
        "description": "Small deterministic synthetic boundary fixture.",
        "source_name": "project synthetic fixture",
        "source_type": "synthetic",
        "retrieval_date": None,
        "data_start": date(2026, 1, 1),
        "data_end": date(2026, 1, 3),
        "fields": ("observation_date", "synthetic_close"),
        "checksum": "sha256:synthetic-boundary-fixture-001",
        "normal_pytest_eligible": True,
        "redistribution_safe": True,
        "limitations": ("synthetic values only",),
        "non_claims": ("metadata only",),
    }
    values.update(overrides)
    return ResearchFixtureManifest(**values)


def replay_point(observation_date: date, value: Decimal) -> SyntheticReplayPoint:
    return SyntheticReplayPoint(
        observation=AsofObservation(
            observation_date=observation_date,
            available_after=observation_date,
        ),
        value=value,
    )


def synthetic_result() -> SyntheticResearchResult:
    return build_synthetic_research_workflow_result(
        manifest(),
        (
            replay_point(date(2026, 1, 1), Decimal("100.00")),
            replay_point(date(2026, 1, 2), Decimal("101.00")),
            replay_point(date(2026, 1, 3), Decimal("102.00")),
        ),
        date(2026, 1, 3),
    )


def test_external_intake_and_synthetic_result_are_distinct_contracts() -> None:
    intake = external_intake()
    result = synthetic_result()

    assert intake.advisory_only is True
    assert isinstance(intake, ExternalResearchIntake)
    assert not isinstance(intake, SyntheticResearchResult)
    assert isinstance(result, SyntheticResearchResult)
    assert not isinstance(result, ExternalResearchIntake)


@pytest.mark.parametrize("source_type", EXTERNAL_RESEARCH_SOURCE_TYPES)
def test_external_intake_source_types_are_advisory_only(source_type: str) -> None:
    intake = external_intake(source_type=source_type)

    assert intake.source_type == source_type
    assert intake.advisory_only is True


@pytest.mark.parametrize(
    "summary",
    (
        "Strategy approval was granted by the external system.",
        "The copied note includes a profitability claim.",
        "Benchmark comparison says the candidate beats benchmark.",
        "Order instruction says to submit order at the close.",
        "Position sizing uses a target weight after the event.",
        "Trading ready status was asserted by the external system.",
    ),
)
def test_external_intake_rejects_trading_or_validation_claims(summary: str) -> None:
    with pytest.raises(ValidationError, match="non-advisory"):
        external_intake(summary=summary)


def test_external_intake_and_synthetic_workflow_can_coexist_as_metadata() -> None:
    intake = external_intake(source_type="quantconnect")
    result = synthetic_result()
    research_package = {
        "external_advisory": intake.to_dict(),
        "synthetic_workflow": result.to_dict(),
    }

    assert research_package["external_advisory"]["advisory_only"] is True
    assert tuple(research_package["synthetic_workflow"]) == ("snapshot", "summary")
    assert result.snapshot.manifest.normal_pytest_eligible is True
    assert result.snapshot.manifest.redistribution_safe is True
    assert not isinstance(intake, SyntheticResearchResult)
    assert not isinstance(result, ExternalResearchIntake)


def test_synthetic_workflow_output_has_no_trading_or_claim_fields() -> None:
    payload = synthetic_result().to_dict()

    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_SYNTHETIC_PAYLOAD_FIELDS)


def test_research_paths_import_no_forbidden_runtime_vendor_or_data_dependencies() -> None:
    violations: list[str] = []

    for path in RESEARCH_PATH_MODULES:
        for module in _import_references(path):
            if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES):
                violations.append(f"{path}: imports {module}")

    assert violations == []


def test_research_paths_reference_no_trading_runtime_or_backtest_names() -> None:
    violations: list[str] = []

    for path in RESEARCH_PATH_MODULES:
        forbidden_names = _referenced_names(path).intersection(
            _FORBIDDEN_REFERENCE_NAMES
        )
        violations.extend(f"{path}: references {name}" for name in forbidden_names)

    assert sorted(violations) == []


def test_research_paths_make_no_io_network_vendor_or_trading_calls() -> None:
    violations: list[str] = []

    for path in RESEARCH_PATH_MODULES:
        forbidden_calls = _call_names(path).intersection(_FORBIDDEN_CALL_NAMES)
        violations.extend(f"{path}: calls {call_name}" for call_name in forbidden_calls)

    assert sorted(violations) == []


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set()
        for key, nested_value in value.items():
            keys.add(str(key))
            keys.update(_payload_keys(nested_value))
        return keys

    if isinstance(value, list):
        keys = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _import_references(path: Path) -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _referenced_names(path: Path) -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _call_names(path: Path) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
