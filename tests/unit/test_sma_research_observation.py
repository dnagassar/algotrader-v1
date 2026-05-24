from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation import (
    SMA_RESEARCH_POSITIONS,
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)


MODULE_PATH = Path("src/algotrader/research/sma_research_observation.py")


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_SYMBOL = "SYN-SMA"
_AS_OF = "2026-01-20"
_WINDOW = 3
_LIMITATIONS = (
    "synthetic SMA mechanics only",
    "uses fixed fixture-like price points",
)
_REQUIRED_NON_CLAIMS = (
    _not("strategy app", "roval"),
    _not("sour", "ce/data app", "roval"),
    _not("predictive validity"),
    _not("profitability"),
    _not("a recomm", "endation"),
    _not("sig", "nal or evaluator behavior"),
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
_EXPECTED_ABOVE_DICT = {
    "observation_type": "sma_research_observation",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "symbol": _SYMBOL,
    "as_of": _AS_OF,
    "window": _WINDOW,
    "sample_count": 4,
    "eligible_sample_count": 3,
    "ignored_future_sample_count": 1,
    "latest_close": "11",
    "sma_value": "10",
    "distance_from_sma": "1",
    "distance_from_sma_pct": "0.1",
    "position_vs_sma": "above",
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


def test_above_sma_construction_and_exact_to_dict() -> None:
    observation = _build_above_observation()

    assert type(observation) is SmaResearchObservation
    assert observation.observation_type == "sma_research_observation"
    assert observation.status == "candidate_only"
    assert observation.authority == "advisory_only"
    assert observation.capital_authority is False
    assert observation.latest_close == Decimal("11")
    assert observation.sma_value == Decimal("10")
    assert observation.distance_from_sma == Decimal("1")
    assert observation.distance_from_sma_pct == Decimal("0.1")
    assert observation.position_vs_sma == "above"
    assert observation.to_dict() == _EXPECTED_ABOVE_DICT
    assert tuple(observation.to_dict()) == tuple(_EXPECTED_ABOVE_DICT)


def test_price_point_is_validated_and_serializes_decimal_as_string() -> None:
    price_point = SmaResearchPricePoint("2026-01-20", Decimal("10.50"))

    assert price_point.date == "2026-01-20"
    assert price_point.close == Decimal("10.50")
    assert price_point.to_dict() == {"date": "2026-01-20", "close": "10.50"}


def test_builder_sorts_dates_before_computing_latest_window() -> None:
    observation = build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-01-20", "11"),
            _point("2026-01-18", "9"),
            _point("2026-01-21", "99"),
            _point("2026-01-19", "10"),
        ),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )

    assert observation.to_dict() == _EXPECTED_ABOVE_DICT


def test_below_and_equal_sma_positions_are_deterministic() -> None:
    below = build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-01-18", "11"),
            _point("2026-01-19", "10"),
            _point("2026-01-20", "9"),
        ),
    )
    equal = build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-01-18", "10"),
            _point("2026-01-19", "10"),
            _point("2026-01-20", "10"),
        ),
    )

    assert below.position_vs_sma == "below"
    assert below.latest_close == Decimal("9")
    assert below.sma_value == Decimal("10")
    assert below.distance_from_sma == Decimal("-1")
    assert below.distance_from_sma_pct == Decimal("-0.1")
    assert below.to_dict()["position_vs_sma"] == "below"
    assert below.to_dict()["distance_from_sma_pct"] == "-0.1"

    assert equal.position_vs_sma == "equal"
    assert equal.latest_close == Decimal("10")
    assert equal.sma_value == Decimal("10")
    assert equal.distance_from_sma == Decimal("0")
    assert equal.distance_from_sma_pct == Decimal("0")
    assert equal.to_dict()["position_vs_sma"] == "equal"


def test_insufficient_history_returns_no_sma_or_distance_values() -> None:
    observation = build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-01-19", "9"),
            _point("2026-01-20", "10"),
            _point("2026-01-21", "99"),
        ),
    )

    assert observation.sample_count == 3
    assert observation.eligible_sample_count == 2
    assert observation.ignored_future_sample_count == 1
    assert observation.latest_close == Decimal("10")
    assert observation.sma_value is None
    assert observation.distance_from_sma is None
    assert observation.distance_from_sma_pct is None
    assert observation.position_vs_sma == "insufficient_history"
    assert observation.to_dict()["latest_close"] == "10"
    assert observation.to_dict()["sma_value"] is None


def test_future_samples_are_ignored_and_counted() -> None:
    observation = build_sma_research_observation(
        _SYMBOL,
        "2026-01-19",
        2,
        (
            _point("2026-01-18", "8"),
            _point("2026-01-19", "10"),
            _point("2026-01-20", "100"),
            _point("2026-01-21", "200"),
        ),
    )

    assert observation.sample_count == 4
    assert observation.eligible_sample_count == 2
    assert observation.ignored_future_sample_count == 2
    assert observation.latest_close == Decimal("10")
    assert observation.sma_value == Decimal("9")
    assert observation.distance_from_sma == Decimal("1")
    assert observation.position_vs_sma == "above"


def test_duplicate_dates_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate dates"):
        build_sma_research_observation(
            _SYMBOL,
            _AS_OF,
            _WINDOW,
            (
                _point("2026-01-18", "9"),
                _point("2026-01-18", "10"),
            ),
        )


@pytest.mark.parametrize(
    "bad_date",
    ("", "2026-1-20", "2026-02-30", "2026-01-20T00:00:00"),
)
def test_malformed_dates_are_rejected(bad_date: str) -> None:
    with pytest.raises(ValidationError, match="date"):
        SmaResearchPricePoint(bad_date, Decimal("1"))

    with pytest.raises(ValidationError, match="as_of"):
        build_sma_research_observation(_SYMBOL, bad_date, 1, ())


@pytest.mark.parametrize("bad_window", (0, -1, True, Decimal("3"), "3"))
def test_invalid_window_is_rejected(bad_window: object) -> None:
    with pytest.raises(ValidationError, match="window"):
        build_sma_research_observation(_SYMBOL, _AS_OF, bad_window, ())


@pytest.mark.parametrize("bad_symbol", ("", "  SYN", "buy threshold"))
def test_invalid_symbol_is_rejected(bad_symbol: str) -> None:
    with pytest.raises(ValidationError, match="symbol"):
        build_sma_research_observation(bad_symbol, _AS_OF, 1, ())


@pytest.mark.parametrize("bad_close", (Decimal("0"), Decimal("-1"), "1", 1))
def test_invalid_close_is_rejected(bad_close: object) -> None:
    with pytest.raises(ValidationError, match="close"):
        SmaResearchPricePoint("2026-01-20", bad_close)


def test_non_price_point_inputs_are_rejected() -> None:
    with pytest.raises(ValidationError, match="price_points"):
        build_sma_research_observation(_SYMBOL, _AS_OF, 1, (object(),))

    with pytest.raises(ValidationError, match="price_points"):
        build_sma_research_observation(_SYMBOL, _AS_OF, 1, object())


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
        build_sma_research_observation(
            _SYMBOL,
            _AS_OF,
            1,
            (_point("2026-01-20", "1"),),
            limitations=limitations,
            non_claims=non_claims,
        )


def test_direct_construction_rejects_inconsistent_or_mutated_fixed_metadata() -> None:
    payload = _direct_payload()

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("sample_count", 99),
        ("position_vs_sma", "insufficient_history"),
        ("distance_from_sma", Decimal("2")),
        ("non_claims", ("not operational advice",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaResearchObservation(**mutated)


def test_observation_and_price_point_are_frozen_slotted() -> None:
    observation = _build_above_observation()
    price_point = _point("2026-01-20", "10")

    assert hasattr(SmaResearchObservation, "__slots__")
    assert hasattr(SmaResearchPricePoint, "__slots__")
    assert tuple(field.name for field in fields(SmaResearchObservation)) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "symbol",
        "as_of",
        "window",
        "sample_count",
        "eligible_sample_count",
        "ignored_future_sample_count",
        "latest_close",
        "sma_value",
        "distance_from_sma",
        "distance_from_sma_pct",
        "position_vs_sma",
        "limitations",
        "non_claims",
    )

    with pytest.raises(FrozenInstanceError):
        observation.symbol = "OTHER"
    with pytest.raises(FrozenInstanceError):
        price_point.close = Decimal("11")
    with pytest.raises((AttributeError, TypeError)):
        observation.extra_field = "not allowed"


def test_repeated_construction_and_compact_json_are_deterministic() -> None:
    first = _build_above_observation()
    second = _build_above_observation()
    first_json = _compact_json(first.to_dict())
    second_json = _compact_json(second.to_dict())

    assert first == second
    assert first is not second
    assert first.to_dict() == second.to_dict() == _EXPECTED_ABOVE_DICT
    assert first_json == second_json
    assert json.loads(first_json) == _EXPECTED_ABOVE_DICT


def test_serialization_is_primitive_only_and_returns_fresh_lists() -> None:
    first = _build_above_observation().to_dict()
    second = _build_above_observation().to_dict()

    assert _primitive_only(first)
    assert isinstance(first["latest_close"], str)
    assert isinstance(first["sma_value"], str)
    assert isinstance(first["distance_from_sma"], str)
    assert isinstance(first["distance_from_sma_pct"], str)
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _EXPECTED_ABOVE_DICT
    assert _build_above_observation().to_dict() == _EXPECTED_ABOVE_DICT


def test_no_from_dict_exists() -> None:
    observation = _build_above_observation()
    price_point = _point("2026-01-20", "10")

    assert not hasattr(SmaResearchObservation, "from_dict")
    assert not hasattr(SmaResearchPricePoint, "from_dict")
    assert not hasattr(observation, "from_dict")
    assert not hasattr(price_point, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_public_payload_keys_do_not_emit_actionable_or_authority_fields() -> None:
    payload = _build_above_observation().to_dict()

    assert set(payload).isdisjoint(_forbidden_payload_keys())
    assert set(SMA_RESEARCH_POSITIONS) == {
        "above",
        "below",
        "equal",
        "insufficient_history",
    }
    assert _forbidden_payload_keys().isdisjoint(_payload_keys(payload))
    assert set(_REQUIRED_NON_CLAIMS).issubset(set(payload["non_claims"]))


def test_production_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def _build_above_observation() -> SmaResearchObservation:
    return build_sma_research_observation(
        _SYMBOL,
        _AS_OF,
        _WINDOW,
        (
            _point("2026-01-20", "11"),
            _point("2026-01-18", "9"),
            _point("2026-01-21", "99"),
            _point("2026-01-19", "10"),
        ),
        limitations=_LIMITATIONS,
        non_claims=_EXTRA_NON_CLAIMS,
    )


def _point(value_date: str, close: str) -> SmaResearchPricePoint:
    return SmaResearchPricePoint(value_date, Decimal(close))


def _direct_payload() -> dict[str, object]:
    return {
        "observation_type": "sma_research_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": _SYMBOL,
        "as_of": _AS_OF,
        "window": _WINDOW,
        "sample_count": 4,
        "eligible_sample_count": 3,
        "ignored_future_sample_count": 1,
        "latest_close": Decimal("11"),
        "sma_value": Decimal("10"),
        "distance_from_sma": Decimal("1"),
        "distance_from_sma_pct": Decimal("0.1"),
        "position_vs_sma": "above",
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
        "ranking",
        "recommendation",
        "readiness",
        "score",
        "scoring",
        "sell",
        "signal",
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


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
