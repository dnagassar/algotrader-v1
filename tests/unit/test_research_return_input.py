import ast
import json
import re
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import research_return_input as module
from algotrader.research.research_return_input import ResearchReturnInputSnapshot


MODULE_PATH = Path("src/algotrader/research/research_return_input.py")

_EXPECTED_FIELDS = (
    "snapshot_id",
    "symbol",
    "observation_dates",
    "close_values",
    "close_to_close_returns",
    "return_basis",
    "adjustment_policy",
    "synthetic_only",
    "candidate_only",
    "non_claims",
)

_REQUIRED_NON_CLAIMS = (
    "not source approval",
    "not data approval",
    "not endpoint approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not evidence approval",
    "not return-construction approval",
    "not no-lookahead approval",
    "not strategy validation",
    "not trading readiness",
)

_REAL_TICKERS = (
    "SPY",
    "IVV",
    "VOO",
    "QQQ",
    "VTI",
    "IWM",
    "DIA",
    "AGG",
    "BND",
    "TLT",
    "GLD",
    "EFA",
    "EEM",
)

_VENDOR_OR_PROVIDER_TERMS = (
    "alpaca",
    "alpha vantage",
    "bloomberg",
    "factset",
    "fred",
    "massive",
    "nasdaq",
    "polygon",
    "quantconnect",
    "quandl",
    "refinitiv",
    "stooq",
    "yahoo",
    "yfinance",
)

_CREDENTIAL_TERMS = (
    "api_key",
    "apikey",
    "bearer",
    "client_secret",
    "credential",
    "oauth",
    "password",
    "private_key",
    "secret",
    "token",
)

_PATH_OR_URL_MARKERS = (
    "://",
    "http:",
    "https:",
    "www.",
    ".com",
    ".data",
    ".csv",
    ".jsonl",
    ".parquet",
    ".zip",
    "/",
    "\\",
)

_FORBIDDEN_APPROVAL_FIELD_TERMS = (
    "approval",
    "approved",
    "data_source",
    "endpoint",
    "source",
    "vendor",
)

_FORBIDDEN_TRADING_FIELD_TERMS = (
    "broker",
    "evaluator",
    "execution",
    "order",
    "portfolio",
    "position",
    "risk",
    "signal",
    "strategy",
    "trade",
    "trading",
)

_FORBIDDEN_MARKET_BAR_FIELD_TERMS = (
    "bar",
    "bars",
    "bar_count",
    "open",
    "high",
    "low",
    "ohlc",
    "volume",
)

_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
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
    "massive",
    "network",
    "numpy",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "polygon",
    "polygon_api_client",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
    "client",
    "connect",
    "download",
    "exists",
    "glob",
    "hash",
    "ingest",
    "is_file",
    "iterdir",
    "mkdir",
    "open",
    "parse",
    "Path",
    "persist",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "rglob",
    "socket.socket",
    "stat",
    "submit_order",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_FORBIDDEN_REFERENCE_NAMES = {
    "Alpaca",
    "api_client",
    "broker",
    "client",
    "evaluator",
    "execution",
    "httpx",
    "ingest",
    "loader",
    "market_bar",
    "network",
    "numpy",
    "open",
    "pandas",
    "parser",
    "Path",
    "pathlib",
    "portfolio",
    "QuantConnect",
    "requests",
    "runtime",
    "signal",
    "socket",
    "strategy",
    "trade",
    "vectorbt",
    "yfinance",
}


def valid_snapshot(**overrides: object) -> ResearchReturnInputSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "synthetic-return-input-001",
        "symbol": "SYNRET001",
        "observation_dates": (
            date(2026, 1, 2),
            date(2026, 1, 5),
            date(2026, 1, 6),
        ),
        "close_values": (Decimal("100.00"), Decimal("102.50"), Decimal("101.25")),
        "close_to_close_returns": (Decimal("0.025"), Decimal("-0.012195121951219512")),
        "return_basis": "close_to_close_simple_return",
        "adjustment_policy": "pre_adjusted_synthetic_values",
        "synthetic_only": True,
        "candidate_only": True,
        "non_claims": _REQUIRED_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchReturnInputSnapshot(**values)


def test_valid_construction_normalizes_required_strings() -> None:
    snapshot = valid_snapshot(
        snapshot_id=" synthetic-return-input-001 ",
        return_basis=" close_to_close_simple_return ",
    )

    assert snapshot.snapshot_id == "synthetic-return-input-001"
    assert snapshot.symbol == "SYNRET001"
    assert snapshot.observation_dates == (
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
    )
    assert snapshot.close_values == (
        Decimal("100.00"),
        Decimal("102.50"),
        Decimal("101.25"),
    )
    assert snapshot.close_to_close_returns == (
        Decimal("0.025"),
        Decimal("-0.012195121951219512"),
    )
    assert snapshot.return_basis == "close_to_close_simple_return"
    assert snapshot.adjustment_policy == "pre_adjusted_synthetic_values"
    assert snapshot.synthetic_only is True
    assert snapshot.candidate_only is True
    assert snapshot.non_claims == _REQUIRED_NON_CLAIMS


def test_snapshot_is_frozen_slotted_dataclass() -> None:
    snapshot = valid_snapshot()

    assert is_dataclass(snapshot)
    assert hasattr(ResearchReturnInputSnapshot, "__slots__")
    assert tuple(field.name for field in fields(ResearchReturnInputSnapshot)) == (
        _EXPECTED_FIELDS
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.symbol = "CHANGED"
    with pytest.raises(TypeError):
        snapshot.close_values[0] = Decimal("0")


def test_tuple_like_inputs_are_normalized_to_immutable_tuples() -> None:
    observation_dates = [date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6)]
    close_values = [Decimal("100.00"), Decimal("102.50"), Decimal("101.25")]
    returns = [Decimal("0.025"), Decimal("-0.012195121951219512")]
    non_claims = list(_REQUIRED_NON_CLAIMS)

    snapshot = valid_snapshot(
        observation_dates=observation_dates,
        close_values=close_values,
        close_to_close_returns=returns,
        non_claims=non_claims,
    )
    observation_dates.append(date(2026, 1, 7))
    close_values.append(Decimal("103.00"))
    returns.append(Decimal("0.017283950617283951"))
    non_claims.append("not investment advice")

    assert snapshot.observation_dates == (
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
    )
    assert snapshot.close_values == (
        Decimal("100.00"),
        Decimal("102.50"),
        Decimal("101.25"),
    )
    assert snapshot.close_to_close_returns == (
        Decimal("0.025"),
        Decimal("-0.012195121951219512"),
    )
    assert snapshot.non_claims == _REQUIRED_NON_CLAIMS
    assert isinstance(snapshot.observation_dates, tuple)
    assert isinstance(snapshot.close_values, tuple)
    assert isinstance(snapshot.close_to_close_returns, tuple)
    assert isinstance(snapshot.non_claims, tuple)


@pytest.mark.parametrize(
    "field_name",
    ("snapshot_id", "symbol", "return_basis", "adjustment_policy"),
)
def test_required_strings_must_be_non_empty_after_stripping(field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        valid_snapshot(**{field_name: "   "})


def test_observation_dates_must_be_plain_dates_not_datetimes() -> None:
    with pytest.raises(ValidationError, match="observation_dates"):
        valid_snapshot(
            observation_dates=(
                date(2026, 1, 2),
                datetime(2026, 1, 5, 16, 0),
                date(2026, 1, 6),
            )
        )


def test_observation_dates_must_be_strictly_increasing() -> None:
    with pytest.raises(ValidationError, match="strictly increasing"):
        valid_snapshot(
            observation_dates=(
                date(2026, 1, 2),
                date(2026, 1, 6),
                date(2026, 1, 5),
            )
        )


def test_duplicate_observation_dates_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        valid_snapshot(
            observation_dates=(
                date(2026, 1, 2),
                date(2026, 1, 5),
                date(2026, 1, 5),
            )
        )


@pytest.mark.parametrize(
    "field_name,values",
    (
        (
            "close_values",
            (Decimal("100.00"), 102.50, Decimal("101.25")),
        ),
        (
            "close_to_close_returns",
            (Decimal("0.025"), -0.012195121951219512),
        ),
    ),
)
def test_decimal_fields_must_contain_decimals(
    field_name: str,
    values: tuple[object, ...],
) -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        valid_snapshot(**{field_name: values})


def test_close_values_must_contain_at_least_two_values() -> None:
    with pytest.raises(ValidationError, match="close_values"):
        valid_snapshot(
            observation_dates=(date(2026, 1, 2),),
            close_values=(Decimal("100.00"),),
            close_to_close_returns=(),
        )


def test_return_count_must_match_close_values_minus_one() -> None:
    with pytest.raises(ValidationError, match="close_values count minus one"):
        valid_snapshot(close_to_close_returns=(Decimal("0.025"),))


def test_return_count_must_match_observation_dates_minus_one() -> None:
    with pytest.raises(ValidationError, match="observation_dates count minus one"):
        valid_snapshot(
            observation_dates=(
                date(2026, 1, 2),
                date(2026, 1, 5),
                date(2026, 1, 6),
                date(2026, 1, 7),
            )
        )


@pytest.mark.parametrize("value", (False, 1, "true", None))
def test_synthetic_only_must_be_exactly_true(value: object) -> None:
    with pytest.raises(ValidationError, match="synthetic_only"):
        valid_snapshot(synthetic_only=value)


@pytest.mark.parametrize("value", (False, 1, "true", None))
def test_candidate_only_must_be_exactly_true(value: object) -> None:
    with pytest.raises(ValidationError, match="candidate_only"):
        valid_snapshot(candidate_only=value)


def test_required_non_claims_are_enforced() -> None:
    with pytest.raises(ValidationError, match="not source approval"):
        valid_snapshot(non_claims=_REQUIRED_NON_CLAIMS[1:])


def test_non_claims_must_remain_negative_statements() -> None:
    with pytest.raises(ValidationError, match="negative statements"):
        valid_snapshot(non_claims=(*_REQUIRED_NON_CLAIMS, "source approved"))


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("snapshot_id", True),
        ("symbol", True),
        ("observation_dates", (date(2026, 1, 2), True, date(2026, 1, 6))),
        ("close_values", (Decimal("100.00"), True, Decimal("101.25"))),
        ("close_to_close_returns", (Decimal("0.025"), True)),
        ("return_basis", True),
        ("adjustment_policy", True),
        ("non_claims", (*_REQUIRED_NON_CLAIMS[:-1], True)),
    ),
)
def test_bools_are_rejected_for_string_date_decimal_and_tuple_values(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        valid_snapshot(**{field_name: value})


def test_to_dict_from_dict_round_trips_through_primitive_payload() -> None:
    snapshot = valid_snapshot()
    payload = snapshot.to_dict()
    reloaded = ResearchReturnInputSnapshot.from_dict(payload)

    assert reloaded == snapshot
    assert reloaded is not snapshot
    assert payload == {
        "snapshot_id": "synthetic-return-input-001",
        "symbol": "SYNRET001",
        "observation_dates": ["2026-01-02", "2026-01-05", "2026-01-06"],
        "close_values": ["100.00", "102.50", "101.25"],
        "close_to_close_returns": ["0.025", "-0.012195121951219512"],
        "return_basis": "close_to_close_simple_return",
        "adjustment_policy": "pre_adjusted_synthetic_values",
        "synthetic_only": True,
        "candidate_only": True,
        "non_claims": list(_REQUIRED_NON_CLAIMS),
    }
    _assert_primitive_only(payload)


def test_to_dict_lists_do_not_mutate_snapshot_tuples() -> None:
    snapshot = valid_snapshot()
    payload = snapshot.to_dict()

    payload["observation_dates"].append("2026-01-07")
    payload["close_values"][0] = "0"
    payload["close_to_close_returns"].append("0")
    payload["non_claims"].append("not changed")

    assert snapshot.to_dict() == valid_snapshot().to_dict()


def test_from_dict_rebuilds_tuple_immutability_without_sharing_payload_lists() -> None:
    payload = valid_snapshot().to_dict()
    snapshot = ResearchReturnInputSnapshot.from_dict(payload)
    payload["non_claims"].append("not changed")

    assert snapshot.non_claims == _REQUIRED_NON_CLAIMS
    with pytest.raises(TypeError):
        snapshot.non_claims[0] = "not changed"


def test_deterministic_json_serialization_is_byte_stable() -> None:
    first = _compact_json(valid_snapshot().to_dict())
    second = _compact_json(valid_snapshot().to_dict())
    round_tripped = _compact_json(
        ResearchReturnInputSnapshot.from_dict(valid_snapshot().to_dict()).to_dict()
    )

    assert first == second
    assert first == round_tripped
    assert first.startswith('{"snapshot_id":')
    assert first.index('"symbol":') < first.index('"observation_dates":')
    assert first.index('"close_values":') < first.index('"close_to_close_returns":')


def test_from_dict_rejects_unknown_fields() -> None:
    payload = valid_snapshot().to_dict()
    payload["source_approval"] = "not allowed"

    with pytest.raises(ValidationError, match="unknown research return input field"):
        ResearchReturnInputSnapshot.from_dict(payload)


def test_from_dict_rejects_missing_fields() -> None:
    payload = valid_snapshot().to_dict()
    del payload["return_basis"]

    with pytest.raises(ValidationError, match="missing research return input field"):
        ResearchReturnInputSnapshot.from_dict(payload)


@pytest.mark.parametrize("bad_date", ("20260102", "2026-13-02", True, None))
def test_from_dict_rejects_malformed_dates(bad_date: object) -> None:
    payload = valid_snapshot().to_dict()
    payload["observation_dates"][0] = bad_date

    with pytest.raises(ValidationError):
        ResearchReturnInputSnapshot.from_dict(payload)


@pytest.mark.parametrize("bad_decimal", ("not-decimal", "", True, None))
def test_from_dict_rejects_malformed_decimals(bad_decimal: object) -> None:
    payload = valid_snapshot().to_dict()
    payload["close_values"][0] = bad_decimal

    with pytest.raises(ValidationError):
        ResearchReturnInputSnapshot.from_dict(payload)


def test_from_dict_rejects_invalid_lengths_after_deserializing() -> None:
    payload = valid_snapshot().to_dict()
    payload["close_to_close_returns"].pop()

    with pytest.raises(ValidationError, match="count must equal"):
        ResearchReturnInputSnapshot.from_dict(payload)


def test_snapshot_has_no_source_data_vendor_or_endpoint_approval_fields() -> None:
    field_names = _snapshot_field_names()

    assert all(
        all(term not in field_name for term in _FORBIDDEN_APPROVAL_FIELD_TERMS)
        for field_name in field_names
    )


def test_snapshot_has_no_signal_evaluator_portfolio_or_trading_fields() -> None:
    field_names = _snapshot_field_names()

    assert all(
        all(term not in field_name for term in _FORBIDDEN_TRADING_FIELD_TERMS)
        for field_name in field_names
    )


def test_snapshot_does_not_create_market_bar_production_contract_fields() -> None:
    field_names = _snapshot_field_names()

    assert not hasattr(module, "ResearchMarketBar")
    assert not hasattr(module, "ResearchMarketBarSequence")
    assert not hasattr(module, "ResearchMarketBarReturnInput")
    assert all(
        all(term not in field_name for term in _FORBIDDEN_MARKET_BAR_FIELD_TERMS)
        for field_name in field_names
    )


def test_snapshot_payload_has_no_real_ticker_vendor_path_or_credential_content() -> None:
    serialized = _compact_json(valid_snapshot().to_dict())
    upper_serialized = serialized.upper()
    lowered = serialized.lower()

    assert "SYNRET001" in upper_serialized
    for ticker in _REAL_TICKERS:
        assert re.search(rf"(?<![A-Z0-9]){ticker}(?![A-Z0-9])", upper_serialized) is None
    for term in _VENDOR_OR_PROVIDER_TERMS:
        assert term not in lowered
    for term in _CREDENTIAL_TERMS:
        assert term not in lowered
    for marker in _PATH_OR_URL_MARKERS:
        assert marker not in lowered


def test_module_imports_no_vendor_data_network_or_trading_path_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_vendor_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_references_no_vendor_io_runtime_or_trading_path_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def _snapshot_field_names() -> tuple[str, ...]:
    return tuple(field.name for field in fields(ResearchReturnInputSnapshot))


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal, date, datetime))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_only(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_primitive_only(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            elif node.level > 0:
                imports.add("__future__")

    return imports


def _matches_forbidden_prefix(module_name: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
