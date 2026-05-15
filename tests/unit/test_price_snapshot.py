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
    load_historical_price_snapshot_csv,
    price_snapshot_fingerprint,
)


MODULE_PATH = Path("src/algotrader/research/price_snapshot.py")
REQUIRED_COLUMNS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)

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
    "ValidatedSignalDefinition",
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
    "makedirs",
    "mkdir",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read_csv",
    "request",
    "rglob",
    "scandir",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "walk",
    "write",
}


def bar(**overrides: object) -> HistoricalPriceBar:
    values: dict[str, object] = {
        "symbol": "SPY",
        "date": date(2026, 1, 2),
        "open": Decimal("100.0100"),
        "high": Decimal("101.5000"),
        "low": Decimal("99.7500"),
        "close": Decimal("100.2500"),
        "adjusted_close": Decimal("100.1250"),
        "volume": 123456,
    }
    values.update(overrides)
    return HistoricalPriceBar(**values)


def snapshot_csv(
    tmp_path: Path,
    rows: tuple[dict[str, str], ...],
    columns: tuple[str, ...] = REQUIRED_COLUMNS,
    filename: str = "snapshot.csv",
) -> Path:
    path = tmp_path / filename
    lines = [",".join(columns)]
    lines.extend(",".join(row.get(column, "") for column in columns) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def default_rows() -> tuple[dict[str, str], ...]:
    return (
        {
            "date": "2026-01-02",
            "open": "100.0100",
            "high": "101.5000",
            "low": "99.7500",
            "close": "100.2500",
            "adjusted_close": "100.1250",
            "volume": "123456",
        },
        {
            "date": "2026-01-05",
            "open": "101.00",
            "high": "103.00",
            "low": "100.50",
            "close": "102.25",
            "adjusted_close": "102.00",
            "volume": "234567",
        },
    )


def test_successful_csv_load_normalizes_symbol_and_parses_values(tmp_path: Path) -> None:
    columns = ("symbol",) + REQUIRED_COLUMNS
    rows = tuple({"symbol": " spy ", **row} for row in default_rows())
    path = snapshot_csv(tmp_path, rows, columns=columns)

    snapshot = load_historical_price_snapshot_csv(path, " spy ")

    assert snapshot.symbol == "SPY"
    assert snapshot.bars[0].symbol == "SPY"
    assert snapshot.bars[0].date == date(2026, 1, 2)
    assert snapshot.bars[0].open == Decimal("100.0100")
    assert snapshot.bars[0].open.as_tuple().exponent == -4
    assert snapshot.bars[0].volume == 123456


def test_supplied_symbol_controls_snapshot_when_csv_has_no_symbol_column(
    tmp_path: Path,
) -> None:
    path = snapshot_csv(tmp_path, default_rows())

    snapshot = load_historical_price_snapshot_csv(path, " qqq ")

    assert snapshot.symbol == "QQQ"
    assert {price_bar.symbol for price_bar in snapshot.bars} == {"QQQ"}


def test_historical_price_bar_is_frozen_and_slotted() -> None:
    price_bar = bar()

    assert hasattr(HistoricalPriceBar, "__slots__")
    assert not hasattr(price_bar, "__dict__")
    with pytest.raises(FrozenInstanceError):
        price_bar.close = Decimal("1")


def test_historical_price_snapshot_is_frozen_and_slotted() -> None:
    item = HistoricalPriceSnapshot(symbol="spy", bars=[bar()])

    assert hasattr(HistoricalPriceSnapshot, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.symbol = "QQQ"


def test_historical_price_bar_fields_are_exact_daily_price_fields() -> None:
    field_names = tuple(field.name for field in fields(HistoricalPriceBar))

    assert field_names == (
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    )


def test_snapshot_bars_are_stored_as_an_immutable_tuple() -> None:
    item = HistoricalPriceSnapshot(symbol="SPY", bars=[bar()])

    assert isinstance(item.bars, tuple)
    with pytest.raises(TypeError):
        item.bars[0] = bar(close=Decimal("101"))


def test_snapshot_copies_input_collection_without_mutating_or_aliasing_it() -> None:
    bars = [bar()]
    item = HistoricalPriceSnapshot(symbol="SPY", bars=bars)

    bars.append(bar(date=date(2026, 1, 5)))

    assert item.bars == (bar(),)
    assert len(bars) == 2


@pytest.mark.parametrize(
    "bad_date",
    (
        datetime(2026, 1, 2, 12, 0),
        True,
        "2026-01-02",
    ),
)
def test_bar_rejects_non_plain_dates(bad_date: object) -> None:
    with pytest.raises(ValidationError, match="date"):
        bar(date=bad_date)


def test_bar_rejects_date_subclasses() -> None:
    class CustomDate(date):
        pass

    with pytest.raises(ValidationError, match="date"):
        bar(date=CustomDate(2026, 1, 2))


@pytest.mark.parametrize("bad_price", (Decimal("0"), Decimal("-1")))
def test_bar_rejects_non_positive_price_values(bad_price: Decimal) -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        bar(close=bad_price)


def test_bar_rejects_non_decimal_price_values() -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        bar(open=100)


def test_bar_rejects_bool_volume() -> None:
    with pytest.raises(ValidationError, match="volume"):
        bar(volume=True)


@pytest.mark.parametrize("bad_volume", (-1, Decimal("1"), 1.5))
def test_bar_rejects_invalid_volume_values(bad_volume: object) -> None:
    with pytest.raises(ValidationError, match="volume"):
        bar(volume=bad_volume)


def test_snapshot_rejects_symbol_mismatches() -> None:
    with pytest.raises(ValidationError, match="snapshot symbol"):
        HistoricalPriceSnapshot(symbol="SPY", bars=(bar(symbol="QQQ"),))


def test_loader_rejects_symbol_mismatch_when_symbol_column_is_present(
    tmp_path: Path,
) -> None:
    columns = ("symbol",) + REQUIRED_COLUMNS
    rows = tuple({"symbol": "QQQ", **row} for row in default_rows())
    path = snapshot_csv(tmp_path, rows, columns=columns)

    with pytest.raises(ValidationError, match="symbol"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_duplicate_dates(tmp_path: Path) -> None:
    rows = (
        default_rows()[0],
        {**default_rows()[1], "date": "2026-01-02"},
    )
    path = snapshot_csv(tmp_path, rows)

    with pytest.raises(ValidationError, match="duplicate dates"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_unordered_dates(tmp_path: Path) -> None:
    rows = (
        {**default_rows()[0], "date": "2026-01-05"},
        {**default_rows()[1], "date": "2026-01-02"},
    )
    path = snapshot_csv(tmp_path, rows)

    with pytest.raises(ValidationError, match="strictly increasing"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_missing_required_columns(tmp_path: Path) -> None:
    columns = tuple(column for column in REQUIRED_COLUMNS if column != "adjusted_close")
    rows = default_rows()
    path = snapshot_csv(tmp_path, rows, columns=columns)

    with pytest.raises(ValidationError, match="missing required columns"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_unsupported_extra_columns(tmp_path: Path) -> None:
    columns = REQUIRED_COLUMNS + ("dividend",)
    rows = tuple({**row, "dividend": "0"} for row in default_rows())
    path = snapshot_csv(tmp_path, rows, columns=columns)

    with pytest.raises(ValidationError, match="unsupported columns"):
        load_historical_price_snapshot_csv(path, "SPY")


@pytest.mark.parametrize("contents", ("", ",".join(REQUIRED_COLUMNS) + "\n"))
def test_loader_rejects_empty_files_and_files_with_no_data_rows(
    tmp_path: Path,
    contents: str,
) -> None:
    path = tmp_path / "empty.csv"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_malformed_dates(tmp_path: Path) -> None:
    rows = ({**default_rows()[0], "date": "2026/01/02"},)
    path = snapshot_csv(tmp_path, rows)

    with pytest.raises(ValidationError, match="ISO date"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_malformed_decimal_values(tmp_path: Path) -> None:
    rows = ({**default_rows()[0], "open": "not-decimal"},)
    path = snapshot_csv(tmp_path, rows)

    with pytest.raises(ValidationError, match="Decimal"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_malformed_volume_values(tmp_path: Path) -> None:
    rows = ({**default_rows()[0], "volume": "1.5"},)
    path = snapshot_csv(tmp_path, rows)

    with pytest.raises(ValidationError, match="integer"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_invalid_ohlc_relationships(tmp_path: Path) -> None:
    rows = ({**default_rows()[0], "high": "99.00"},)
    path = snapshot_csv(tmp_path, rows)

    with pytest.raises(ValidationError, match="high"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_non_positive_price_values(tmp_path: Path) -> None:
    rows = ({**default_rows()[0], "adjusted_close": "0"},)
    path = snapshot_csv(tmp_path, rows)

    with pytest.raises(ValidationError, match="greater than zero"):
        load_historical_price_snapshot_csv(path, "SPY")


def test_loader_rejects_remote_url_like_paths() -> None:
    with pytest.raises(ValidationError, match="local CSV path"):
        load_historical_price_snapshot_csv("https://example.test/snapshot.csv", "SPY")


def test_deterministic_fingerprint_is_equal_for_identical_content(
    tmp_path: Path,
) -> None:
    first_path = snapshot_csv(tmp_path, default_rows(), filename="first.csv")
    second_path = snapshot_csv(tmp_path, default_rows(), filename="second.csv")

    first = load_historical_price_snapshot_csv(first_path, "SPY")
    second = load_historical_price_snapshot_csv(second_path, " spy ")

    assert price_snapshot_fingerprint(first) == price_snapshot_fingerprint(second)


def test_deterministic_fingerprint_changes_when_bar_content_changes(
    tmp_path: Path,
) -> None:
    first_path = snapshot_csv(tmp_path, default_rows(), filename="first.csv")
    changed_rows = (
        default_rows()[0],
        {**default_rows()[1], "close": "102.50"},
    )
    second_path = snapshot_csv(tmp_path, changed_rows, filename="second.csv")

    first = load_historical_price_snapshot_csv(first_path, "SPY")
    second = load_historical_price_snapshot_csv(second_path, "SPY")

    assert price_snapshot_fingerprint(first) != price_snapshot_fingerprint(second)


def test_fingerprint_rejects_non_snapshot_values() -> None:
    with pytest.raises(ValidationError, match="HistoricalPriceSnapshot"):
        price_snapshot_fingerprint("not a snapshot")


def test_module_imports_no_vendor_network_runtime_or_trading_path_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_references_no_strategy_signal_or_trading_path_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_module_makes_no_network_vendor_write_discovery_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_loader_opens_the_supplied_csv_path_in_read_only_mode() -> None:
    open_calls = [
        node
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call) and _call_name(node.func).endswith(".open")
    ]

    assert len(open_calls) == 1
    assert _open_mode(open_calls[0]) == "r"


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


def _open_mode(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant):
        return node.args[0].value

    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value

    return None
