import ast
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.fixture_manifest import ResearchFixtureManifest


MODULE_PATH = Path("src/algotrader/research/fixture_manifest.py")

_FORBIDDEN_MANIFEST_FIELD_NAMES = {
    "account",
    "account_id",
    "alpaca",
    "alpaca_order",
    "benchmark",
    "broker",
    "broker_name",
    "broker_order_id",
    "buying_power",
    "cash",
    "cash_proxy",
    "client_order_id",
    "data_file",
    "download",
    "download_url",
    "execution",
    "execution_plan",
    "file_path",
    "fill",
    "ingestion",
    "network",
    "network_url",
    "order",
    "order_id",
    "portfolio",
    "portfolio_state",
    "profitability",
    "profitable",
    "quantity",
    "request_url",
    "risk",
    "runtime",
    "scheduler",
    "signal",
    "source_approved",
    "strategy",
    "submit_order",
    "symbol",
    "trading_ready",
    "validated",
    "validated_at",
    "validation_status",
    "vendor",
    "vendor_name",
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


def manifest(**overrides: object) -> ResearchFixtureManifest:
    values: dict[str, object] = {
        "fixture_id": "synthetic-close-fixture-001",
        "fixture_kind": "synthetic",
        "description": "Tiny deterministic synthetic close-value example.",
        "source_name": "project synthetic fixture",
        "source_type": "synthetic",
        "retrieval_date": None,
        "data_start": date(2026, 1, 1),
        "data_end": date(2026, 1, 3),
        "fields": ("observation_date", "synthetic_close"),
        "checksum": "sha256:synthetic-close-fixture-001",
        "normal_pytest_eligible": True,
        "redistribution_safe": True,
        "limitations": ("synthetic values only",),
        "non_claims": ("does not validate any trading result",),
    }
    values.update(overrides)
    return ResearchFixtureManifest(**values)


def test_valid_synthetic_manifest_creation() -> None:
    item = manifest()

    assert item.fixture_id == "synthetic-close-fixture-001"
    assert item.fixture_kind == "synthetic"
    assert item.source_type == "synthetic"
    assert item.normal_pytest_eligible is True
    assert item.redistribution_safe is True
    assert item.fields == ("observation_date", "synthetic_close")


def test_valid_local_only_manifest_creation_when_not_normal_pytest_eligible() -> None:
    item = manifest(
        fixture_id="local-snapshot-manifest-001",
        fixture_kind="local_only",
        source_name="owner local snapshot placeholder",
        source_type="local_snapshot",
        retrieval_date=date(2026, 5, 14),
        data_start=None,
        data_end=None,
        normal_pytest_eligible=False,
        redistribution_safe=False,
        limitations=("local-only metadata record, no shared data",),
        non_claims=("does not approve the local snapshot source",),
    )

    assert item.fixture_kind == "local_only"
    assert item.source_type == "local_snapshot"
    assert item.normal_pytest_eligible is False


def test_derived_manual_manifest_can_be_normal_pytest_eligible_when_safe() -> None:
    item = manifest(
        fixture_id="manual-derived-fixture-001",
        fixture_kind="derived",
        source_name="hand-authored synthetic derivation",
        source_type="manual",
        checksum="sha256:manual-derived-fixture-001",
        fields=("derived_observation",),
        normal_pytest_eligible=True,
        redistribution_safe=True,
    )

    assert item.fixture_kind == "derived"
    assert item.source_type == "manual"


def test_manifest_is_frozen_and_slotted() -> None:
    item = manifest()

    assert hasattr(ResearchFixtureManifest, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.fixture_id = "changed"


def test_tuple_inputs_are_copied_and_stored_as_immutable_tuples() -> None:
    field_values = ["observation_date"]
    limitations = ["synthetic limitation"]
    non_claims = ["synthetic non-claim"]

    item = manifest(
        fields=field_values,
        limitations=limitations,
        non_claims=non_claims,
    )
    field_values.append("late_field")
    limitations.append("late limitation")
    non_claims.append("late non-claim")

    assert item.fields == ("observation_date",)
    assert item.limitations == ("synthetic limitation",)
    assert item.non_claims == ("synthetic non-claim",)
    with pytest.raises(TypeError):
        item.fields[0] = "changed"


def test_to_dict_returns_deterministic_json_compatible_metadata_shape() -> None:
    item = manifest(retrieval_date=date(2026, 5, 14))

    payload = item.to_dict()

    assert tuple(payload) == (
        "fixture_id",
        "fixture_kind",
        "description",
        "source_name",
        "source_type",
        "retrieval_date",
        "data_start",
        "data_end",
        "fields",
        "checksum",
        "normal_pytest_eligible",
        "redistribution_safe",
        "limitations",
        "non_claims",
    )
    assert payload == {
        "fixture_id": "synthetic-close-fixture-001",
        "fixture_kind": "synthetic",
        "description": "Tiny deterministic synthetic close-value example.",
        "source_name": "project synthetic fixture",
        "source_type": "synthetic",
        "retrieval_date": "2026-05-14",
        "data_start": "2026-01-01",
        "data_end": "2026-01-03",
        "fields": ["observation_date", "synthetic_close"],
        "checksum": "sha256:synthetic-close-fixture-001",
        "normal_pytest_eligible": True,
        "redistribution_safe": True,
        "limitations": ["synthetic values only"],
        "non_claims": ["does not validate any trading result"],
    }


def test_from_dict_restores_manifest_dates_tuples_and_equality() -> None:
    item = manifest(retrieval_date=date(2026, 5, 14))
    payload = item.to_dict()

    reloaded = ResearchFixtureManifest.from_dict(payload)

    assert reloaded == item
    assert reloaded.retrieval_date == date(2026, 5, 14)
    assert reloaded.data_start == date(2026, 1, 1)
    assert reloaded.data_end == date(2026, 1, 3)
    assert reloaded.fields == ("observation_date", "synthetic_close")
    assert reloaded.limitations == ("synthetic values only",)
    assert reloaded.non_claims == ("does not validate any trading result",)


def test_from_dict_preserves_tuple_immutability_after_deserialization() -> None:
    item = ResearchFixtureManifest.from_dict(manifest().to_dict())

    assert isinstance(item.fields, tuple)
    assert isinstance(item.limitations, tuple)
    assert isinstance(item.non_claims, tuple)
    with pytest.raises(TypeError):
        item.fields[0] = "changed"


def test_to_dict_does_not_share_mutable_lists_with_original_manifest() -> None:
    item = manifest()
    payload = item.to_dict()

    payload["fields"].append("late_field")
    payload["limitations"].append("late limitation")
    payload["non_claims"].append("late non-claim")

    assert item.fields == ("observation_date", "synthetic_close")
    assert item.limitations == ("synthetic values only",)
    assert item.non_claims == ("does not validate any trading result",)


def test_from_dict_does_not_share_mutable_lists_with_reloaded_manifest() -> None:
    payload = manifest().to_dict()
    item = ResearchFixtureManifest.from_dict(payload)

    payload["fields"].append("late_field")
    payload["limitations"].append("late limitation")
    payload["non_claims"].append("late non-claim")

    assert item.fields == ("observation_date", "synthetic_close")
    assert item.limitations == ("synthetic values only",)
    assert item.non_claims == ("does not validate any trading result",)


def test_from_dict_rejects_unknown_fields() -> None:
    payload = manifest().to_dict()
    payload["download_url"] = "https://example.invalid/raw.csv"

    with pytest.raises(ValidationError, match="unknown manifest field"):
        ResearchFixtureManifest.from_dict(payload)


def test_from_dict_rejects_missing_required_fields() -> None:
    payload = manifest().to_dict()
    del payload["checksum"]

    with pytest.raises(ValidationError, match="missing manifest field"):
        ResearchFixtureManifest.from_dict(payload)


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("retrieval_date", "2026-13-14"),
        ("data_start", "20260101"),
        ("data_end", date(2026, 1, 3)),
    ),
)
def test_from_dict_rejects_malformed_date_payloads(
    field_name: str,
    value: object,
) -> None:
    payload = manifest().to_dict()
    payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        ResearchFixtureManifest.from_dict(payload)


def test_from_dict_preserves_existing_manifest_validation_rules() -> None:
    payload = manifest().to_dict()
    payload["data_end"] = "2025-12-31"

    with pytest.raises(ValidationError, match="data_end"):
        ResearchFixtureManifest.from_dict(payload)


@pytest.mark.parametrize(
    "overrides",
    (
        {
            "fixture_kind": "local_only",
            "source_type": "local_snapshot",
        },
        {
            "fixture_kind": "derived",
            "source_type": "third_party",
        },
        {
            "fixture_kind": "derived",
            "source_type": "local_snapshot",
        },
        {
            "fixture_kind": "synthetic",
            "source_type": "manual",
        },
    ),
)
def test_from_dict_rejects_unsafe_normal_pytest_eligible_payloads(
    overrides: dict[str, object],
) -> None:
    payload = manifest(normal_pytest_eligible=False).to_dict()
    payload["normal_pytest_eligible"] = True
    for field_name, value in overrides.items():
        payload[field_name] = value

    with pytest.raises(ValidationError):
        ResearchFixtureManifest.from_dict(payload)


def test_manifest_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(ResearchFixtureManifest))

    assert field_names == (
        "fixture_id",
        "fixture_kind",
        "description",
        "source_name",
        "source_type",
        "retrieval_date",
        "data_start",
        "data_end",
        "fields",
        "checksum",
        "normal_pytest_eligible",
        "redistribution_safe",
        "limitations",
        "non_claims",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_MANIFEST_FIELD_NAMES)


@pytest.mark.parametrize(
    "field_name",
    ("fixture_id", "description", "source_name", "source_type", "checksum"),
)
def test_empty_required_strings_are_rejected(field_name: str) -> None:
    with pytest.raises(ValidationError):
        manifest(**{field_name: " "})


def test_unknown_fixture_kind_is_rejected() -> None:
    with pytest.raises(ValidationError, match="fixture_kind"):
        manifest(fixture_kind="vendor_snapshot")


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("fields", ()),
        ("fields", ("observation_date", " ")),
        ("fields", "observation_date"),
        ("limitations", ("synthetic limitation", "")),
        ("limitations", "synthetic limitation"),
        ("non_claims", ("synthetic non-claim", " ")),
        ("non_claims", "synthetic non-claim"),
    ),
)
def test_malformed_tuple_fields_are_rejected(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        manifest(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    ("retrieval_date", "data_start", "data_end"),
)
def test_datetime_values_are_rejected_where_plain_dates_are_required(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: datetime(2026, 5, 14, 12, 0)})


def test_bad_data_date_ranges_are_rejected() -> None:
    with pytest.raises(ValidationError, match="data_end"):
        manifest(data_start=date(2026, 1, 3), data_end=date(2026, 1, 2))


@pytest.mark.parametrize(
    "overrides",
    (
        {
            "fixture_kind": "local_only",
            "source_type": "local_snapshot",
        },
        {
            "fixture_kind": "derived",
            "source_type": "third_party",
        },
        {
            "fixture_kind": "derived",
            "source_type": "local_snapshot",
        },
        {
            "fixture_kind": "synthetic",
            "source_type": "manual",
        },
    ),
)
def test_local_only_or_raw_external_fixtures_are_not_normal_pytest_eligible(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        manifest(
            normal_pytest_eligible=True,
            redistribution_safe=True,
            **overrides,
        )


def test_normal_pytest_eligible_requires_redistribution_safe() -> None:
    with pytest.raises(ValidationError, match="redistribution"):
        manifest(normal_pytest_eligible=True, redistribution_safe=False)


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("normal_pytest_eligible", "yes"),
        ("redistribution_safe", 1),
    ),
)
def test_boolean_flags_must_be_plain_bools(field_name: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: value})


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

    item = manifest()

    assert item.source_name == "project synthetic fixture"


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
