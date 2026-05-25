from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation import (
    ResearchReturnPoint,
    ResearchReturnPricePoint,
    ResearchReturnSeriesObservation,
    build_research_return_series_observation,
)


MODULE_PATH = Path("src/algotrader/research/research_return_observation.py")


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYMBOL = "SYN-RET"
_AS_OF = "2026-01-23"
_LIMITATIONS = (
    "synthetic close-to-close mechanics only",
    "uses fixed fixture-like closes",
)
_REQUIRED_NON_CLAIMS = (
    _not("sour", "ce/data app", "roval"),
    _not("adjusted-close/corporate-action completeness"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
    _not("backtesting validation"),
    _not("allo", "cation or or", "der authority"),
    _not("bro", "ker authority"),
    _not("port", "folio mutation authority"),
    _not("paper read", "iness"),
    _not("live read", "iness"),
    _not("capital authority"),
    _not("tra", "ding authority"),
)
_EXTRA_NON_CLAIMS = ("not operational advice",)
_EXPECTED_NON_CLAIMS = (*_REQUIRED_NON_CLAIMS, *_EXTRA_NON_CLAIMS)
_EXPECTED_RETURN_DICT = {
    "observation_type": "research_return_series_observation",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "symbol": _SYMBOL,
    "as_of": _AS_OF,
    "return_method": "close_to_close_simple_return",
    "price_basis": "synthetic_close",
    "sample_count": 5,
    "eligible_sample_count": 4,
    "ignored_future_sample_count": 1,
    "return_count": 3,
    "returns": [
        {
            "start_date": "2026-01-20",
            "end_date": "2026-01-21",
            "start_close": "100",
            "end_close": "110",
            "simple_return": "0.1",
        },
        {
            "start_date": "2026-01-21",
            "end_date": "2026-01-22",
            "start_close": "110",
            "end_close": "99",
            "simple_return": "-0.1",
        },
        {
            "start_date": "2026-01-22",
            "end_date": "2026-01-23",
            "start_close": "99",
            "end_close": "99",
            "simple_return": "0",
        },
    ],
    "limitations": list(_LIMITATIONS),
    "non_claims": list(_EXPECTED_NON_CLAIMS),
}
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.dashboard",
    "algotrader.execution",
    _s("algotrader.", "l", "lm"),
    _s("algotrader.", "l", "lms"),
    "algotrader.ml",
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.risk",
    _s("algotrader.", "run", "time"),
    _s("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    _s("cre", "dential"),
    _s("data", "base"),
    "duckdb",
    "httpx",
    "ipynb",
    "joblib",
    "keras",
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("mas", "sive"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    "pathlib",
    _s("poly", "gon"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    _s("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    _s("cli", "ent"),
    _s("con", "nect"),
    _s("create_", "or", "der"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "exists",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
    "mkdir",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "post",
    _s("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "rglob",
    _s("ra", "nk"),
    _s("sco", "re"),
    "save",
    _s("so", "cket.socket"),
    "stat",
    _s("sub", "mit_", "or", "der"),
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    _s("Al", "paca"),
    "api_key",
    "api_secret",
    _s("bro", "ker"),
    _s("cli", "ent"),
    _s("cre", "dential"),
    _s("dash", "board"),
    _s("data", "base"),
    _s("exec", "ution"),
    "llm",
    "ml",
    _s("or", "der"),
    _s("persist", "ence"),
    _s("port", "folio"),
    "readiness",
    _s("recomm", "endation"),
    _s("run", "time"),
    _s("sche", "duler"),
    _s("sco", "ring"),
    "secret",
    _s("sig", "nal"),
    _s("so", "cket"),
    "token",
    _s("tra", "ding_authority"),
}


def test_construction_and_exact_to_dict_for_positive_negative_and_zero_returns() -> None:
    observation = _build_observation()

    assert type(observation) is ResearchReturnSeriesObservation
    assert observation.observation_type == "research_return_series_observation"
    assert observation.status == "candidate_only"
    assert observation.authority == "advisory_only"
    assert observation.capital_authority is False
    assert observation.return_method == "close_to_close_simple_return"
    assert observation.price_basis == "synthetic_close"
    assert tuple(point.simple_return for point in observation.returns) == (
        Decimal("0.1"),
        Decimal("-0.1"),
        Decimal("0"),
    )
    assert observation.to_dict() == _EXPECTED_RETURN_DICT
    assert tuple(observation.to_dict()) == tuple(_EXPECTED_RETURN_DICT)


def test_price_and_return_points_serialize_decimals_as_strings() -> None:
    price_point = ResearchReturnPricePoint("2026-01-20", Decimal("10.50"))
    return_point = ResearchReturnPoint(
        "2026-01-20",
        "2026-01-21",
        Decimal("10.50"),
        Decimal("10.50"),
        Decimal("0"),
    )

    assert price_point.to_dict() == {"date": "2026-01-20", "close": "10.50"}
    assert return_point.to_dict() == {
        "start_date": "2026-01-20",
        "end_date": "2026-01-21",
        "start_close": "10.50",
        "end_close": "10.50",
        "simple_return": "0",
    }


def test_builder_sorts_dates_before_constructing_returns() -> None:
    observation = build_research_return_series_observation(
        _SYMBOL,
        _AS_OF,
        (
            _point("2026-01-22", "99"),
            _point("2026-01-24", "1000"),
            _point("2026-01-20", "100"),
            _point("2026-01-23", "99"),
            _point("2026-01-21", "110"),
        ),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )

    assert observation.to_dict() == _EXPECTED_RETURN_DICT


def test_future_samples_are_ignored_and_counted() -> None:
    observation = build_research_return_series_observation(
        _SYMBOL,
        "2026-01-21",
        _price_points(),
    )

    assert observation.sample_count == 5
    assert observation.eligible_sample_count == 2
    assert observation.ignored_future_sample_count == 3
    assert observation.return_count == 1
    assert observation.returns == (
        ResearchReturnPoint(
            "2026-01-20",
            "2026-01-21",
            Decimal("100"),
            Decimal("110"),
            Decimal("0.1"),
        ),
    )
    assert "2026-01-22" not in _compact_json(observation.to_dict())


def test_fewer_than_two_eligible_samples_produces_zero_returns() -> None:
    observation = build_research_return_series_observation(
        _SYMBOL,
        "2026-01-20",
        (
            _point("2026-01-20", "100"),
            _point("2026-01-21", "110"),
        ),
    )

    assert observation.sample_count == 2
    assert observation.eligible_sample_count == 1
    assert observation.ignored_future_sample_count == 1
    assert observation.return_count == 0
    assert observation.returns == ()
    assert observation.to_dict()["returns"] == []


def test_duplicate_dates_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate dates"):
        build_research_return_series_observation(
            _SYMBOL,
            _AS_OF,
            (
                _point("2026-01-20", "100"),
                _point("2026-01-20", "101"),
            ),
        )


@pytest.mark.parametrize(
    "bad_date",
    ("", "2026-1-20", "2026-02-30", "2026-01-20T00:00:00", True, None),
)
def test_malformed_dates_are_rejected(bad_date: object) -> None:
    with pytest.raises(ValidationError, match="date"):
        ResearchReturnPricePoint(bad_date, Decimal("1"))

    with pytest.raises(ValidationError, match="as_of"):
        build_research_return_series_observation(_SYMBOL, bad_date, ())


@pytest.mark.parametrize("bad_symbol", ("", "  SYN", "buy setup", True, None))
def test_invalid_symbol_is_rejected(bad_symbol: object) -> None:
    with pytest.raises(ValidationError, match="symbol"):
        build_research_return_series_observation(bad_symbol, _AS_OF, ())


@pytest.mark.parametrize(
    "bad_close",
    (Decimal("0"), Decimal("-1"), Decimal("NaN"), "1", 1, True, None),
)
def test_invalid_close_is_rejected(bad_close: object) -> None:
    with pytest.raises(ValidationError, match="close"):
        ResearchReturnPricePoint("2026-01-20", bad_close)


def test_malformed_price_point_inputs_are_rejected() -> None:
    with pytest.raises(ValidationError, match="price_points"):
        build_research_return_series_observation(_SYMBOL, _AS_OF, object())

    with pytest.raises(ValidationError, match="price_points"):
        build_research_return_series_observation(_SYMBOL, _AS_OF, (object(),))


def test_malformed_return_point_inputs_are_rejected() -> None:
    with pytest.raises(ValidationError, match="end_date"):
        ResearchReturnPoint(
            "2026-01-21",
            "2026-01-20",
            Decimal("100"),
            Decimal("110"),
            Decimal("0.1"),
        )

    with pytest.raises(ValidationError, match="simple_return"):
        ResearchReturnPoint(
            "2026-01-20",
            "2026-01-21",
            Decimal("100"),
            Decimal("110"),
            Decimal("0.2"),
        )


@pytest.mark.parametrize(
    "limitations, non_claims, expected",
    (
        (("synthetic only", ""), (), "limitations"),
        ("synthetic only", (), "limitations"),
        ((_s("contains recomm", "endation language"),), (), "limitations"),
        ((), ("positive claim",), "negative"),
        ((), "not operational advice", "non_claims"),
    ),
)
def test_malformed_limitations_and_non_claims_are_rejected(
    limitations: object,
    non_claims: object,
    expected: str,
) -> None:
    with pytest.raises(ValidationError, match=expected):
        build_research_return_series_observation(
            _SYMBOL,
            _AS_OF,
            (_point("2026-01-20", "1"),),
            limitations=limitations,
            non_claims=non_claims,
        )


def test_direct_construction_rejects_inconsistent_or_mutated_metadata() -> None:
    payload = _direct_payload()

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("return_method", "compound_return"),
        ("price_basis", "adjusted_close"),
        ("sample_count", 99),
        ("eligible_sample_count", 99),
        ("return_count", 99),
        ("returns", (object(),)),
        ("non_claims", ("not operational advice",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchReturnSeriesObservation(**mutated)


def test_observation_return_point_and_price_point_are_frozen_slotted() -> None:
    observation = _build_observation()
    price_point = _point("2026-01-20", "100")
    return_point = observation.returns[0]

    assert hasattr(ResearchReturnSeriesObservation, "__slots__")
    assert hasattr(ResearchReturnPricePoint, "__slots__")
    assert hasattr(ResearchReturnPoint, "__slots__")
    assert tuple(field.name for field in fields(ResearchReturnSeriesObservation)) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "symbol",
        "as_of",
        "return_method",
        "price_basis",
        "sample_count",
        "eligible_sample_count",
        "ignored_future_sample_count",
        "return_count",
        "returns",
        "limitations",
        "non_claims",
    )
    assert tuple(field.name for field in fields(ResearchReturnPoint)) == (
        "start_date",
        "end_date",
        "start_close",
        "end_close",
        "simple_return",
    )

    with pytest.raises(FrozenInstanceError):
        observation.symbol = "OTHER"
    with pytest.raises(FrozenInstanceError):
        price_point.close = Decimal("101")
    with pytest.raises(FrozenInstanceError):
        return_point.simple_return = Decimal("0")
    with pytest.raises((AttributeError, TypeError)):
        observation.extra_field = "not allowed"


def test_repeated_construction_is_byte_for_byte_deterministic_under_compact_json() -> None:
    first = _build_observation()
    second = _build_observation()
    first_json = _compact_json(first.to_dict())
    second_json = _compact_json(second.to_dict())

    assert first == second
    assert first is not second
    assert first.to_dict() == second.to_dict() == _EXPECTED_RETURN_DICT
    assert first_json == second_json
    assert json.loads(first_json) == _EXPECTED_RETURN_DICT


def test_serialization_is_primitive_only_and_returns_fresh_lists() -> None:
    first = _build_observation().to_dict()
    second = _build_observation().to_dict()

    assert _primitive_only(first)
    assert isinstance(first["returns"], list)
    assert isinstance(first["returns"][0]["simple_return"], str)
    assert isinstance(first["limitations"], list)
    assert isinstance(first["non_claims"], list)
    assert first["returns"] is not second["returns"]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["returns"][0]["simple_return"] = "mutated"
    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _EXPECTED_RETURN_DICT
    assert _build_observation().to_dict() == _EXPECTED_RETURN_DICT


def test_no_from_dict_exists() -> None:
    observation = _build_observation()
    price_point = _point("2026-01-20", "100")
    return_point = observation.returns[0]

    assert not hasattr(ResearchReturnSeriesObservation, "from_dict")
    assert not hasattr(ResearchReturnPricePoint, "from_dict")
    assert not hasattr(ResearchReturnPoint, "from_dict")
    assert not hasattr(observation, "from_dict")
    assert not hasattr(price_point, "from_dict")
    assert not hasattr(return_point, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_public_payload_keys_do_not_emit_actionable_or_trading_authority_fields() -> None:
    payload = _build_observation().to_dict()

    assert set(payload).isdisjoint(_forbidden_payload_keys())
    assert _forbidden_payload_keys().isdisjoint(_payload_keys(payload))
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))


def test_production_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_module_has_no_forbidden_imports_calls_or_references() -> None:
    imports = _import_references()
    call_names = _call_names()
    reference_names = _referenced_names()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert reference_names.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def _build_observation() -> ResearchReturnSeriesObservation:
    return build_research_return_series_observation(
        _SYMBOL,
        _AS_OF,
        _price_points(),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def _price_points() -> tuple[ResearchReturnPricePoint, ...]:
    return (
        _point("2026-01-22", "99"),
        _point("2026-01-24", "1000"),
        _point("2026-01-20", "100"),
        _point("2026-01-23", "99"),
        _point("2026-01-21", "110"),
    )


def _point(value_date: str, close: str) -> ResearchReturnPricePoint:
    return ResearchReturnPricePoint(value_date, Decimal(close))


def _direct_payload() -> dict[str, object]:
    return {
        "observation_type": "research_return_series_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": _SYMBOL,
        "as_of": _AS_OF,
        "return_method": "close_to_close_simple_return",
        "price_basis": "synthetic_close",
        "sample_count": 5,
        "eligible_sample_count": 4,
        "ignored_future_sample_count": 1,
        "return_count": 3,
        "returns": _build_observation().returns,
        "limitations": _LIMITATIONS,
        "non_claims": _EXPECTED_NON_CLAIMS,
    }


def _compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(type(key) is str and _primitive_only(item) for key, item in value.items())

    return False


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
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


def _forbidden_payload_keys() -> set[str]:
    return {
        "account",
        "accounts",
        "actionable",
        _s("allo", "cation"),
        _s("allo", "cations"),
        _s("allo", "cation_authority"),
        "approved",
        "backtest_approved",
        "buy",
        "broker",
        "broker_authority",
        "capital",
        "capital_authority_state",
        "evaluator",
        "hold",
        "live_authorized",
        "live_probe_eligible",
        _s("or", "der"),
        _s("or", "ders"),
        _s("or", "der_authority"),
        "paper_eligible",
        _s("port", "folio"),
        _s("port", "folios"),
        _s("ra", "nking"),
        _s("recomm", "endation"),
        "readiness",
        _s("sco", "re"),
        _s("sco", "ring"),
        "sell",
        _s("sig", "nal"),
        _s("tra", "ding_authority"),
        "trading_ready",
    }


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


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


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
