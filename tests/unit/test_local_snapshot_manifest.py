import ast
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.local_snapshot_manifest import (
    ADJUSTMENT_POLICIES,
    LOCAL_SNAPSHOT_SOURCE_TYPES,
    REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS,
    RETURN_BASES,
    LocalSnapshotManifest,
)


MODULE_PATH = Path("src/algotrader/research/local_snapshot_manifest.py")
CHECKSUM_SHA256 = "a" * 64

_FORBIDDEN_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "benchmark_id",
    "broker",
    "broker_order_id",
    "cash_proxy_id",
    "credential",
    "evidence_approved",
    "execution",
    "execution_plan",
    "fill",
    "ingestion_status",
    "order",
    "portfolio",
    "position",
    "rank",
    "recommendation",
    "runtime",
    "score",
    "signal",
    "strategy_approved",
    "symbol",
    "ticker",
    "trading_ready",
    "validation_status",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.governance",
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
    "csv",
    "database",
    "duckdb",
    "hashlib",
    "httpx",
    "ipynb",
    "json",
    "langchain",
    "langgraph",
    "llm",
    "market_data",
    "notebook",
    "numpy",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "persistence",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
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
    "api_key",
    "approve",
    "approved",
    "backtest",
    "benchmark_approved",
    "broker",
    "cash_proxy_approved",
    "credential",
    "download",
    "evaluator",
    "evidence_approved",
    "execution",
    "fill",
    "hash_file",
    "ingest",
    "order",
    "portfolio",
    "rank",
    "recommend",
    "score",
    "signal",
    "strategy",
    "submit_order",
    "ticker",
    "trade",
    "trading_ready",
    "universe_approved",
    "validation_status",
}

_FORBIDDEN_CALL_NAMES = {
    "DictReader",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "dump",
    "dumps",
    "environ.get",
    "exists",
    "fit",
    "get",
    "getenv",
    "glob",
    "hashlib.sha256",
    "iterdir",
    "load",
    "loads",
    "makedirs",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "rglob",
    "scandir",
    "sha256",
    "socket.socket",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}


def manifest(**overrides: object) -> LocalSnapshotManifest:
    values: dict[str, object] = {
        "snapshot_id": "local-snapshot-metadata-only-001",
        "source_name": "Owner Local Snapshot Metadata Placeholder",
        "source_type": "manual_local_snapshot",
        "acquisition_date": date(2026, 2, 3),
        "observation_start_date": date(2020, 1, 2),
        "observation_end_date": date(2026, 1, 30),
        "as_of_date": date(2026, 2, 4),
        "symbols_policy": "symbol identities unresolved and not embedded",
        "schema_name": "metadata-only-price-schema-candidate",
        "fields": ("observation_date", "close_value"),
        "adjustment_policy": "unknown",
        "return_basis": "unknown",
        "checksum_sha256": CHECKSUM_SHA256,
        "storage_uri": "local-snapshot://off-repo/example",
        "redistribution_status": "not reviewed for redistribution",
        "license_note": "terms not reviewed",
        "provenance_note": "metadata-only placeholder, no rows inspected",
        "limitations": (
            "local file is not committed",
            "manifest does not validate data rows",
        ),
        "non_claims": REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS,
        "normal_pytest_eligible": False,
    }
    values.update(overrides)
    return LocalSnapshotManifest(**values)


def test_allowed_values_are_conservative_and_exclude_synthetic_fixture() -> None:
    assert LOCAL_SNAPSHOT_SOURCE_TYPES == (
        "manual_local_snapshot",
        "vendor_exported_local_snapshot",
        "broker_exported_local_snapshot",
        "public_downloaded_file",
        "api_exported_local_snapshot",
    )
    assert "synthetic_fixture" not in LOCAL_SNAPSHOT_SOURCE_TYPES
    assert ADJUSTMENT_POLICIES == (
        "unknown",
        "raw_close",
        "adjusted_close",
        "split_adjusted",
        "total_return_vendor",
        "explicit_total_return_construction",
    )
    assert RETURN_BASES == (
        "unknown",
        "price_return",
        "adjusted_price_return",
        "total_return",
    )


def test_valid_manifest_construction_normalizes_metadata() -> None:
    item = manifest(
        snapshot_id=" local-snapshot-id ",
        source_name=" Owner Local Snapshot ",
        fields=[" observation_date ", " close_value "],
        limitations=[" local only ", " metadata only "],
        non_claims=[f" {claim} " for claim in REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS],
    )

    assert item.snapshot_id == "local-snapshot-id"
    assert item.source_name == "Owner Local Snapshot"
    assert item.source_type == "manual_local_snapshot"
    assert item.fields == ("observation_date", "close_value")
    assert item.limitations == ("local only", "metadata only")
    assert item.non_claims == REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS
    assert item.normal_pytest_eligible is False


def test_manifest_is_frozen_and_slotted() -> None:
    item = manifest()

    assert is_dataclass(LocalSnapshotManifest)
    assert hasattr(LocalSnapshotManifest, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.snapshot_id = "changed"


def test_manifest_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(LocalSnapshotManifest))

    assert field_names == (
        "snapshot_id",
        "source_name",
        "source_type",
        "acquisition_date",
        "observation_start_date",
        "observation_end_date",
        "as_of_date",
        "symbols_policy",
        "schema_name",
        "fields",
        "adjustment_policy",
        "return_basis",
        "checksum_sha256",
        "storage_uri",
        "redistribution_status",
        "license_note",
        "provenance_note",
        "limitations",
        "non_claims",
        "normal_pytest_eligible",
    )
    assert set(field_names).isdisjoint(_FORBIDDEN_FIELD_NAMES)


@pytest.mark.parametrize(
    "field_name",
    (
        "snapshot_id",
        "source_name",
        "source_type",
        "symbols_policy",
        "schema_name",
        "adjustment_policy",
        "return_basis",
        "checksum_sha256",
        "storage_uri",
        "redistribution_status",
        "license_note",
        "provenance_note",
    ),
)
@pytest.mark.parametrize("bad_value", ("", "   ", True, 123, None))
def test_required_strings_reject_empty_and_non_string_values(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: bad_value})


@pytest.mark.parametrize(
    "field_name",
    (
        "acquisition_date",
        "observation_start_date",
        "observation_end_date",
        "as_of_date",
    ),
)
@pytest.mark.parametrize(
    "bad_date",
    (
        datetime(2026, 2, 4, 12, 0),
        "2026-02-04",
        True,
    ),
)
def test_manifest_enforces_plain_dates(field_name: str, bad_date: object) -> None:
    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: bad_date})


def test_manifest_rejects_date_subclasses() -> None:
    class CustomDate(date):
        pass

    with pytest.raises(ValidationError, match="as_of_date"):
        manifest(as_of_date=CustomDate(2026, 2, 4))


def test_observation_start_date_must_not_be_after_end_date() -> None:
    with pytest.raises(ValidationError, match="observation_start_date"):
        manifest(
            observation_start_date=date(2026, 2, 1),
            observation_end_date=date(2026, 1, 31),
        )


def test_tuple_fields_are_copied_to_immutable_tuples() -> None:
    field_values = ["observation_date", "close_value"]
    limitation_values = ["local file is not committed"]
    non_claim_values = list(REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS)

    item = manifest(
        fields=field_values,
        limitations=limitation_values,
        non_claims=non_claim_values,
    )
    field_values.append("late_field")
    limitation_values.append("late limitation")
    non_claim_values.append("late non-claim")

    assert item.fields == ("observation_date", "close_value")
    assert item.limitations == ("local file is not committed",)
    assert item.non_claims == REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS
    with pytest.raises(TypeError):
        item.fields[0] = "changed"


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("fields", ()),
        ("fields", "observation_date"),
        ("fields", ("observation_date", "")),
        ("fields", ("observation_date", "observation_date")),
        ("limitations", ()),
        ("limitations", "local only"),
        ("limitations", ("local only", " ")),
        ("limitations", ("local only", "local only")),
        ("non_claims", ()),
        ("non_claims", "not source approval"),
        ("non_claims", ("not source approval", " ")),
        ("non_claims", REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS + ("not source approval",)),
    ),
)
def test_tuple_fields_reject_malformed_or_duplicate_values(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: bad_value})


@pytest.mark.parametrize(
    "checksum",
    (
        "a" * 63,
        "A" * 64,
        "g" * 64,
        "sha256:" + ("a" * 64),
    ),
)
def test_checksum_requires_lowercase_64_character_hex(checksum: str) -> None:
    with pytest.raises(ValidationError, match="checksum_sha256"):
        manifest(checksum_sha256=checksum)


@pytest.mark.parametrize("source_type", LOCAL_SNAPSHOT_SOURCE_TYPES)
def test_allowed_source_types_construct(source_type: str) -> None:
    item = manifest(source_type=source_type)

    assert item.source_type == source_type


def test_unknown_source_type_is_rejected() -> None:
    with pytest.raises(ValidationError, match="source_type"):
        manifest(source_type="synthetic_fixture")


@pytest.mark.parametrize("adjustment_policy", ADJUSTMENT_POLICIES)
def test_allowed_adjustment_policies_construct(adjustment_policy: str) -> None:
    item = manifest(adjustment_policy=adjustment_policy)

    assert item.adjustment_policy == adjustment_policy


def test_unknown_adjustment_policy_is_rejected() -> None:
    with pytest.raises(ValidationError, match="adjustment_policy"):
        manifest(adjustment_policy="approved_adjusted_close")


@pytest.mark.parametrize("return_basis", RETURN_BASES)
def test_allowed_return_bases_construct(return_basis: str) -> None:
    item = manifest(return_basis=return_basis)

    assert item.return_basis == return_basis


def test_unknown_return_basis_is_rejected() -> None:
    with pytest.raises(ValidationError, match="return_basis"):
        manifest(return_basis="approved_total_return")


@pytest.mark.parametrize("normal_pytest_eligible", (True, 0, None, "false"))
def test_normal_pytest_eligible_must_be_exactly_false(
    normal_pytest_eligible: object,
) -> None:
    with pytest.raises(ValidationError, match="normal_pytest_eligible"):
        manifest(normal_pytest_eligible=normal_pytest_eligible)


def test_required_non_claims_are_enforced() -> None:
    with pytest.raises(ValidationError, match="non_claims"):
        manifest(non_claims=REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS[:-1])


def test_to_dict_serializes_deterministic_primitive_metadata_only() -> None:
    payload = manifest().to_dict()

    assert tuple(payload) == (
        "snapshot_id",
        "source_name",
        "source_type",
        "acquisition_date",
        "observation_start_date",
        "observation_end_date",
        "as_of_date",
        "symbols_policy",
        "schema_name",
        "fields",
        "adjustment_policy",
        "return_basis",
        "checksum_sha256",
        "storage_uri",
        "redistribution_status",
        "license_note",
        "provenance_note",
        "limitations",
        "non_claims",
        "normal_pytest_eligible",
    )
    assert payload["acquisition_date"] == "2026-02-03"
    assert payload["observation_start_date"] == "2020-01-02"
    assert payload["observation_end_date"] == "2026-01-30"
    assert payload["as_of_date"] == "2026-02-04"
    assert payload["fields"] == ["observation_date", "close_value"]
    assert payload["limitations"] == [
        "local file is not committed",
        "manifest does not validate data rows",
    ]
    assert payload["non_claims"] == list(REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS)
    assert payload["normal_pytest_eligible"] is False
    _assert_no_forbidden_serialized_values(payload)


def test_from_dict_round_trips_dates_tuples_and_equality() -> None:
    original = manifest()

    restored = LocalSnapshotManifest.from_dict(original.to_dict())

    assert restored == original
    assert restored.acquisition_date == date(2026, 2, 3)
    assert restored.observation_start_date == date(2020, 1, 2)
    assert restored.observation_end_date == date(2026, 1, 30)
    assert restored.as_of_date == date(2026, 2, 4)
    assert restored.fields == ("observation_date", "close_value")
    assert restored.limitations == (
        "local file is not committed",
        "manifest does not validate data rows",
    )
    assert restored.non_claims == REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS


def test_from_dict_rejects_non_dict_payloads() -> None:
    with pytest.raises(ValidationError, match="dict"):
        LocalSnapshotManifest.from_dict("not a dict")


def test_from_dict_rejects_unknown_fields() -> None:
    payload = manifest().to_dict()
    payload["download_url"] = "https://example.invalid/raw.csv"

    with pytest.raises(ValidationError, match="unknown"):
        LocalSnapshotManifest.from_dict(payload)


def test_from_dict_rejects_missing_fields() -> None:
    payload = manifest().to_dict()
    del payload["checksum_sha256"]

    with pytest.raises(ValidationError, match="missing"):
        LocalSnapshotManifest.from_dict(payload)


@pytest.mark.parametrize(
    "bad_date",
    ("2026/02/04", "2026-2-04", " 2026-02-04", True, date(2026, 2, 4)),
)
def test_from_dict_rejects_malformed_date_payloads(bad_date: object) -> None:
    payload = manifest().to_dict()
    payload["as_of_date"] = bad_date

    with pytest.raises(ValidationError, match="as_of_date"):
        LocalSnapshotManifest.from_dict(payload)


def test_from_dict_preserves_validation_rules() -> None:
    payload = manifest().to_dict()
    payload["normal_pytest_eligible"] = True

    with pytest.raises(ValidationError, match="normal_pytest_eligible"):
        LocalSnapshotManifest.from_dict(payload)


def test_json_serialization_is_deterministic_and_primitive_only() -> None:
    payload = manifest().to_dict()
    encoded = json.dumps(payload, separators=(",", ":"))
    encoded_again = json.dumps(manifest().to_dict(), separators=(",", ":"))
    round_tripped = json.dumps(json.loads(encoded), separators=(",", ":"))

    assert encoded == encoded_again
    assert round_tripped == encoded
    assert " at 0x" not in encoded
    assert "Decimal(" not in encoded
    assert "datetime." not in encoded
    assert "LocalSnapshotManifest" not in encoded
    for forbidden_text in (
        "SPY",
        "IVV",
        "VOO",
        "QQQ",
        "VTI",
        "source approved",
        "data approved",
        "strategy validated",
        "trading ready",
    ):
        assert forbidden_text not in encoded


def test_manifest_does_not_read_check_hash_or_validate_storage_uri() -> None:
    item = manifest(storage_uri="this/path/is/not/checked.csv")

    assert item.storage_uri == "this/path/is/not/checked.csv"
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_manifest_has_no_approval_strategy_signal_runtime_or_trading_fields() -> None:
    field_names = {field.name for field in fields(LocalSnapshotManifest)}

    assert field_names.isdisjoint(_FORBIDDEN_FIELD_NAMES)


def test_contract_module_imports_no_vendor_network_runtime_or_trading_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_contract_module_references_no_approval_ingestion_or_trading_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def _assert_no_forbidden_serialized_values(value: object) -> None:
    assert not is_dataclass_instance(value)
    assert not isinstance(value, (tuple, set, Decimal, date, datetime))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_no_forbidden_serialized_values(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_no_forbidden_serialized_values(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


def is_dataclass_instance(value: object) -> bool:
    return is_dataclass(value) and not isinstance(value, type)


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
