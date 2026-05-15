import ast
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.price_snapshot import (
    HistoricalPriceBar,
    HistoricalPriceSnapshot,
    price_snapshot_fingerprint,
)
from algotrader.research.price_snapshot_manifest import (
    ADJUSTMENT_POLICIES,
    ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
    ADJUSTMENT_POLICY_RAW,
    ADJUSTMENT_POLICY_TOTAL_RETURN,
    ADJUSTMENT_POLICY_UNKNOWN,
    LOCAL_PRICE_SNAPSHOT_SOURCE_TYPES,
    LocalPriceSnapshotManifest,
    SOURCE_TYPE_LOCAL_EXPORT,
    SOURCE_TYPE_MANUAL_DOWNLOAD,
    SOURCE_TYPE_SYNTHETIC_TEST,
    SOURCE_TYPE_VENDOR_SNAPSHOT,
    build_local_price_snapshot_manifest,
)


MODULE_PATH = Path("src/algotrader/research/price_snapshot_manifest.py")
FILE_SHA256 = "a" * 64
SNAPSHOT_SHA256 = "b" * 64
CREATED_AT = date(2026, 5, 15)

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
    "csv",
    "database",
    "duckdb",
    "httpx",
    "json",
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
    "ValidatedSignalDefinition",
    "account",
    "account_id",
    "alpaca",
    "api",
    "backtest",
    "benchmark",
    "broker",
    "cash",
    "download",
    "evaluator",
    "execution",
    "execution_plan",
    "fill",
    "glob",
    "ingestion",
    "llm",
    "ml",
    "order",
    "portfolio",
    "ranking",
    "request",
    "rglob",
    "scheduler",
    "signal_definition",
    "strategy",
    "submit_order",
    "vectorbt",
}

_FORBIDDEN_CALL_NAMES = {
    "DictReader",
    "DictWriter",
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
    "glob",
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
    "read_csv",
    "read_text",
    "request",
    "rglob",
    "scandir",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}


def price_bar(**overrides: object) -> HistoricalPriceBar:
    values: dict[str, object] = {
        "symbol": "SPY",
        "date": date(2026, 1, 2),
        "open": Decimal("100.00"),
        "high": Decimal("102.00"),
        "low": Decimal("99.00"),
        "close": Decimal("101.00"),
        "adjusted_close": Decimal("100.50"),
        "volume": 1000,
    }
    values.update(overrides)
    return HistoricalPriceBar(**values)


def snapshot() -> HistoricalPriceSnapshot:
    return HistoricalPriceSnapshot(
        symbol="SPY",
        bars=(
            price_bar(date=date(2026, 1, 2)),
            price_bar(
                date=date(2026, 1, 5),
                open=Decimal("101.00"),
                high=Decimal("103.00"),
                low=Decimal("100.00"),
                close=Decimal("102.00"),
                adjusted_close=Decimal("101.50"),
                volume=2000,
            ),
        ),
    )


def manifest(**overrides: object) -> LocalPriceSnapshotManifest:
    values: dict[str, object] = {
        "source_name": "Example Local Export",
        "source_type": SOURCE_TYPE_MANUAL_DOWNLOAD,
        "symbol": "SPY",
        "file_name": "spy_daily.csv",
        "file_sha256": FILE_SHA256,
        "snapshot_fingerprint": SNAPSHOT_SHA256,
        "start_date": date(2026, 1, 2),
        "end_date": date(2026, 1, 5),
        "row_count": 2,
        "adjustment_policy": ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
        "created_at": CREATED_AT,
        "local_only": True,
        "normal_pytest_eligible": False,
        "limitations": ("local file is not committed",),
    }
    values.update(overrides)
    return LocalPriceSnapshotManifest(**values)


def test_allowed_constants_are_explicit_metadata_values() -> None:
    assert ADJUSTMENT_POLICIES == (
        ADJUSTMENT_POLICY_RAW,
        ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
        ADJUSTMENT_POLICY_TOTAL_RETURN,
        ADJUSTMENT_POLICY_UNKNOWN,
    )
    assert LOCAL_PRICE_SNAPSHOT_SOURCE_TYPES == (
        SOURCE_TYPE_MANUAL_DOWNLOAD,
        SOURCE_TYPE_LOCAL_EXPORT,
        SOURCE_TYPE_VENDOR_SNAPSHOT,
        SOURCE_TYPE_SYNTHETIC_TEST,
    )


def test_successful_direct_manifest_construction_normalizes_metadata() -> None:
    item = manifest(
        source_name=" Example Local Export ",
        source_type=" MANUAL_DOWNLOAD ",
        symbol=" spy ",
        adjustment_policy=" ADJUSTED_CLOSE ",
    )

    assert item.source_name == "Example Local Export"
    assert item.source_type == SOURCE_TYPE_MANUAL_DOWNLOAD
    assert item.symbol == "SPY"
    assert item.adjustment_policy == ADJUSTMENT_POLICY_ADJUSTED_CLOSE
    assert item.local_only is True
    assert item.normal_pytest_eligible is False


def test_manifest_is_frozen_and_slotted() -> None:
    item = manifest()

    assert hasattr(LocalPriceSnapshotManifest, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.row_count = 3


def test_manifest_has_exact_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(LocalPriceSnapshotManifest))

    assert field_names == (
        "source_name",
        "source_type",
        "symbol",
        "file_name",
        "file_sha256",
        "snapshot_fingerprint",
        "start_date",
        "end_date",
        "row_count",
        "adjustment_policy",
        "created_at",
        "local_only",
        "normal_pytest_eligible",
        "limitations",
    )


def test_build_from_historical_price_snapshot_derives_snapshot_metadata() -> None:
    source_snapshot = snapshot()

    item = build_local_price_snapshot_manifest(
        source_snapshot,
        source_name="Example Local Export",
        source_type=SOURCE_TYPE_LOCAL_EXPORT,
        file_name="spy_daily.csv",
        file_sha256=FILE_SHA256,
        adjustment_policy=ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
        created_at=CREATED_AT,
        limitations=("local file is not committed",),
    )

    assert item.symbol == "SPY"
    assert item.start_date == date(2026, 1, 2)
    assert item.end_date == date(2026, 1, 5)
    assert item.row_count == 2
    assert item.snapshot_fingerprint == price_snapshot_fingerprint(source_snapshot)


@pytest.mark.parametrize(
    "bad_file_name",
    (
        "snapshots/spy.csv",
        "snapshots\\spy.csv",
        "/tmp/spy.csv",
        "C:\\data\\spy.csv",
        "C:spy.csv",
        ".",
        "..",
    ),
)
def test_file_name_rejects_paths_and_absolute_paths(bad_file_name: str) -> None:
    with pytest.raises(ValidationError, match="file_name"):
        manifest(file_name=bad_file_name)


@pytest.mark.parametrize(
    "field_name,bad_value",
    (
        ("file_sha256", "a" * 63),
        ("file_sha256", "A" * 64),
        ("file_sha256", "g" * 64),
        ("snapshot_fingerprint", "b" * 63),
        ("snapshot_fingerprint", "B" * 64),
        ("snapshot_fingerprint", "z" * 64),
    ),
)
def test_sha256_fields_require_lowercase_64_character_hex(
    field_name: str,
    bad_value: str,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: bad_value})


def test_source_type_must_be_allowed() -> None:
    with pytest.raises(ValidationError, match="source_type"):
        manifest(source_type="spreadsheet")


def test_adjustment_policy_must_be_allowed() -> None:
    with pytest.raises(ValidationError, match="adjustment_policy"):
        manifest(adjustment_policy="split_adjusted")


@pytest.mark.parametrize("local_only", (False, 1, None))
def test_local_only_must_be_exactly_true(local_only: object) -> None:
    with pytest.raises(ValidationError, match="local_only"):
        manifest(local_only=local_only)


@pytest.mark.parametrize("normal_pytest_eligible", (True, 0, None))
def test_normal_pytest_eligible_must_be_exactly_false(
    normal_pytest_eligible: object,
) -> None:
    with pytest.raises(ValidationError, match="normal_pytest_eligible"):
        manifest(normal_pytest_eligible=normal_pytest_eligible)


@pytest.mark.parametrize("row_count", (True, 0, -1, Decimal("2"), 2.5, "2"))
def test_row_count_rejects_bool_zero_negative_and_non_int_values(
    row_count: object,
) -> None:
    with pytest.raises(ValidationError, match="row_count"):
        manifest(row_count=row_count)


@pytest.mark.parametrize("field_name", ("start_date", "end_date", "created_at"))
@pytest.mark.parametrize(
    "bad_date",
    (
        datetime(2026, 1, 2, 12, 0),
        True,
        "2026-01-02",
    ),
)
def test_manifest_enforces_plain_dates(field_name: str, bad_date: object) -> None:
    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: bad_date})


@pytest.mark.parametrize("field_name", ("start_date", "end_date", "created_at"))
def test_manifest_rejects_date_subclasses(field_name: str) -> None:
    class CustomDate(date):
        pass

    with pytest.raises(ValidationError, match=field_name):
        manifest(**{field_name: CustomDate(2026, 1, 2)})


def test_manifest_validates_date_range() -> None:
    with pytest.raises(ValidationError, match="start_date"):
        manifest(start_date=date(2026, 1, 6), end_date=date(2026, 1, 5))


def test_limitations_are_converted_to_an_immutable_tuple() -> None:
    item = manifest(limitations=["local file is not committed"])

    assert item.limitations == ("local file is not committed",)
    assert isinstance(item.limitations, tuple)
    with pytest.raises(TypeError):
        item.limitations[0] = "changed"


def test_limitations_input_collection_is_not_mutated_or_aliased() -> None:
    limitations = ["local file is not committed"]
    item = manifest(limitations=limitations)

    limitations.append("added later")

    assert item.limitations == ("local file is not committed",)
    assert limitations == ["local file is not committed", "added later"]


@pytest.mark.parametrize("limitations", (("valid", " "), "single string", None))
def test_limitations_reject_empty_strings_and_malformed_inputs(
    limitations: object,
) -> None:
    with pytest.raises(ValidationError, match="limitations"):
        manifest(limitations=limitations)


def test_to_dict_serializes_json_compatible_metadata_only() -> None:
    payload = manifest().to_dict()

    assert tuple(payload) == (
        "source_name",
        "source_type",
        "symbol",
        "file_name",
        "file_sha256",
        "snapshot_fingerprint",
        "start_date",
        "end_date",
        "row_count",
        "adjustment_policy",
        "created_at",
        "local_only",
        "normal_pytest_eligible",
        "limitations",
    )
    assert payload == {
        "source_name": "Example Local Export",
        "source_type": SOURCE_TYPE_MANUAL_DOWNLOAD,
        "symbol": "SPY",
        "file_name": "spy_daily.csv",
        "file_sha256": FILE_SHA256,
        "snapshot_fingerprint": SNAPSHOT_SHA256,
        "start_date": "2026-01-02",
        "end_date": "2026-01-05",
        "row_count": 2,
        "adjustment_policy": ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
        "created_at": "2026-05-15",
        "local_only": True,
        "normal_pytest_eligible": False,
        "limitations": ["local file is not committed"],
    }
    assert all(
        field_name not in payload
        for field_name in (
            "account_id",
            "broker_order_id",
            "fill_price",
            "portfolio_state",
            "strategy_approved",
        )
    )


def test_from_dict_round_trip_restores_dates_and_limitations_tuple() -> None:
    original = manifest()

    restored = LocalPriceSnapshotManifest.from_dict(original.to_dict())

    assert restored == original
    assert restored.start_date == date(2026, 1, 2)
    assert restored.created_at == CREATED_AT
    assert restored.limitations == ("local file is not committed",)
    assert isinstance(restored.limitations, tuple)


def test_from_dict_rejects_non_dict_payloads() -> None:
    with pytest.raises(ValidationError, match="dict"):
        LocalPriceSnapshotManifest.from_dict("not a dict")


def test_from_dict_rejects_unknown_fields() -> None:
    payload = manifest().to_dict()
    payload["unexpected"] = "value"

    with pytest.raises(ValidationError, match="unknown"):
        LocalPriceSnapshotManifest.from_dict(payload)


def test_from_dict_rejects_missing_fields() -> None:
    payload = manifest().to_dict()
    del payload["file_sha256"]

    with pytest.raises(ValidationError, match="missing"):
        LocalPriceSnapshotManifest.from_dict(payload)


@pytest.mark.parametrize(
    "bad_date",
    ("2026/01/02", "2026-1-02", " 2026-01-02", True),
)
def test_from_dict_rejects_malformed_dates(bad_date: object) -> None:
    payload = manifest().to_dict()
    payload["start_date"] = bad_date

    with pytest.raises(ValidationError, match="start_date"):
        LocalPriceSnapshotManifest.from_dict(payload)


def test_builder_rejects_malformed_snapshot_values() -> None:
    with pytest.raises(ValidationError, match="HistoricalPriceSnapshot"):
        build_local_price_snapshot_manifest(
            "not a snapshot",
            source_name="Example Local Export",
            source_type=SOURCE_TYPE_LOCAL_EXPORT,
            file_name="spy_daily.csv",
            file_sha256=FILE_SHA256,
            adjustment_policy=ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
            created_at=CREATED_AT,
        )


def test_builder_does_not_mutate_snapshot_or_bars() -> None:
    source_snapshot = snapshot()
    original_bars = source_snapshot.bars
    original_first_bar = source_snapshot.bars[0]

    build_local_price_snapshot_manifest(
        source_snapshot,
        source_name="Example Local Export",
        source_type=SOURCE_TYPE_LOCAL_EXPORT,
        file_name="spy_daily.csv",
        file_sha256=FILE_SHA256,
        adjustment_policy=ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
        created_at=CREATED_AT,
    )

    assert source_snapshot.bars is original_bars
    assert source_snapshot.bars[0] is original_first_bar
    assert source_snapshot == snapshot()


def test_module_imports_no_vendor_network_runtime_or_trading_path_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_references_no_strategy_signal_or_trading_path_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_module_makes_no_file_network_vendor_ingestion_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


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
