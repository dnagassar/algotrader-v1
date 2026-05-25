from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation import (
    ResearchReturnSeriesObservation,
)
from algotrader.research.research_return_summary_observation import (
    RESEARCH_RETURN_SUMMARY_STATES,
    ResearchReturnSummaryObservation,
    build_research_return_summary_observation,
)
from tests.fixtures.research_return_observation import (
    build_synthetic_insufficient_research_return_series_observation,
    build_synthetic_research_return_series_observation,
    expected_synthetic_insufficient_research_return_series_observation_dict,
    expected_synthetic_research_return_series_observation_dict,
)


MODULE_PATH = Path("src/algotrader/research/research_return_summary_observation.py")


def _join(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_MEAN_SIMPLE_RETURN = Decimal(
    "-0.01666666666666666666666666667"
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "decimal",
    "algotrader.errors",
    "algotrader.research.research_return_observation",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _join("algotrader.", "bro", "ker"),
    _join("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.dashboard",
    "algotrader.execution",
    _join("algotrader.", "l", "lm"),
    _join("algotrader.", "l", "lms"),
    "algotrader.ml",
    "algotrader.orchestration",
    _join("algotrader.", "persist", "ence"),
    _join("algotrader.", "port", "folio"),
    "algotrader.risk",
    _join("algotrader.", "run", "time"),
    _join("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _join("algotrader.", "sig", "nals"),
    _join("al", "paca"),
    _join("al", "paca_trade_a", "pi"),
    "anthropic",
    _join("cre", "dential"),
    _join("data", "base"),
    "duckdb",
    "httpx",
    "ipynb",
    "joblib",
    "keras",
    "langchain",
    "langgraph",
    _join("l", "lm"),
    _join("mas", "sive"),
    _join("net", "work"),
    _join("num", "py"),
    "openai",
    "os",
    _join("pan", "das"),
    "pathlib",
    _join("poly", "gon"),
    _join("quant", "connect"),
    _join("re", "quests"),
    _join("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    _join("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    _join("cli", "ent"),
    _join("con", "nect"),
    _join("create_", "or", "der"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _join("down", "load"),
    "eval",
    "exec",
    "exists",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    _join("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
    "mkdir",
    _join("op", "en"),
    "os.environ.get",
    "os.getenv",
    "post",
    _join("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _join("re", "quest"),
    _join("re", "quests.get"),
    "rglob",
    _join("ra", "nk"),
    _join("sco", "re"),
    "save",
    _join("so", "cket.socket"),
    "stat",
    _join("sub", "mit_", "or", "der"),
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _join("wri", "te"),
    "write_text",
}
_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    _join("Al", "paca"),
    "api_key",
    "api_secret",
    _join("bro", "ker"),
    _join("cli", "ent"),
    _join("cre", "dential"),
    _join("dash", "board"),
    _join("data", "base"),
    _join("exec", "ution"),
    "llm",
    "ml",
    _join("or", "der"),
    _join("persist", "ence"),
    _join("port", "folio"),
    "readiness",
    _join("recomm", "endation"),
    _join("run", "time"),
    _join("sche", "duler"),
    _join("sco", "ring"),
    "secret",
    _join("sig", "nal"),
    _join("so", "cket"),
    "token",
    _join("tra", "ding_authority"),
}
_FORBIDDEN_PAYLOAD_KEYS = {
    "account",
    "accounts",
    "actionable",
    _join("allo", "cation"),
    _join("allo", "cations"),
    _join("allo", "cation_authority"),
    "approved",
    "backtest_approved",
    "buy",
    _join("bro", "ker"),
    _join("bro", "ker_authority"),
    "capital",
    "capital_authority_state",
    "evaluator",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _join("or", "der"),
    _join("or", "ders"),
    _join("or", "der_authority"),
    "paper_eligible",
    _join("port", "folio"),
    _join("port", "folios"),
    _join("ra", "nking"),
    _join("recomm", "endation"),
    "readiness",
    _join("sco", "re"),
    _join("sco", "ring"),
    "sell",
    _join("sig", "nal"),
    _join("tra", "ding_authority"),
    "trading_ready",
}


def test_primary_phase_211_fixture_builds_returns_summarized() -> None:
    observation = build_synthetic_research_return_series_observation()
    summary = build_research_return_summary_observation(observation)

    assert type(summary) is ResearchReturnSummaryObservation
    assert summary.source_observation is observation
    assert summary.summary_state == "returns_summarized"
    assert summary.to_dict() == _expected_primary_summary_dict()


def test_insufficient_phase_211_fixture_builds_insufficient_return_history() -> None:
    observation = build_synthetic_insufficient_research_return_series_observation()
    summary = build_research_return_summary_observation(observation)

    assert type(summary) is ResearchReturnSummaryObservation
    assert summary.source_observation is observation
    assert summary.summary_state == "insufficient_return_history"
    assert summary.to_dict() == _expected_insufficient_summary_dict()


def test_positive_negative_and_zero_return_counts_are_pinned() -> None:
    primary = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )
    insufficient = build_research_return_summary_observation(
        build_synthetic_insufficient_research_return_series_observation()
    )

    assert set(RESEARCH_RETURN_SUMMARY_STATES) == {
        "returns_summarized",
        "insufficient_return_history",
    }
    assert primary.source_return_count == 3
    assert primary.positive_return_count == 1
    assert primary.negative_return_count == 1
    assert primary.zero_return_count == 1
    assert insufficient.source_return_count == 0
    assert insufficient.positive_return_count == 0
    assert insufficient.negative_return_count == 0
    assert insufficient.zero_return_count == 0


def test_min_max_and_mean_simple_returns_are_pinned_for_primary_fixture() -> None:
    summary = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )

    assert summary.min_simple_return == Decimal("-0.1")
    assert summary.max_simple_return == Decimal("0.05")
    assert summary.mean_simple_return == _EXPECTED_MEAN_SIMPLE_RETURN
    assert summary.to_dict()["min_simple_return"] == "-0.1"
    assert summary.to_dict()["max_simple_return"] == "0.05"
    assert (
        summary.to_dict()["mean_simple_return"]
        == "-0.01666666666666666666666666667"
    )


def test_min_max_and_mean_are_none_for_insufficient_history() -> None:
    summary = build_research_return_summary_observation(
        build_synthetic_insufficient_research_return_series_observation()
    )

    assert summary.min_simple_return is None
    assert summary.max_simple_return is None
    assert summary.mean_simple_return is None
    assert summary.to_dict()["min_simple_return"] is None
    assert summary.to_dict()["max_simple_return"] is None
    assert summary.to_dict()["mean_simple_return"] is None


def test_exact_source_observation_identity_is_preserved() -> None:
    observation = build_synthetic_research_return_series_observation()
    summary = build_research_return_summary_observation(observation)

    assert summary.source_observation is observation
    assert summary.to_dict()["source_observation"] == observation.to_dict()


def test_exact_type_validation_rejects_invalid_inputs() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_research_return_series_observation_dict()

    class ObservationSubclass(ResearchReturnSeriesObservation):
        pass

    observation = build_synthetic_research_return_series_observation()
    subclass = ObservationSubclass(
        observation_type=observation.observation_type,
        status=observation.status,
        authority=observation.authority,
        capital_authority=observation.capital_authority,
        symbol=observation.symbol,
        as_of=observation.as_of,
        return_method=observation.return_method,
        price_basis=observation.price_basis,
        sample_count=observation.sample_count,
        eligible_sample_count=observation.eligible_sample_count,
        ignored_future_sample_count=observation.ignored_future_sample_count,
        return_count=observation.return_count,
        returns=observation.returns,
        limitations=observation.limitations,
        non_claims=observation.non_claims,
    )

    for value in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="source_observation"):
            build_research_return_summary_observation(value)


def test_fixed_advisory_metadata_is_pinned() -> None:
    summary = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )

    assert summary.observation_type == "research_return_summary_observation"
    assert summary.status == "candidate_only"
    assert summary.authority == "advisory_only"
    assert summary.capital_authority is False
    assert summary.to_dict()["observation_type"] == "research_return_summary_observation"
    assert summary.to_dict()["status"] == "candidate_only"
    assert summary.to_dict()["authority"] == "advisory_only"
    assert summary.to_dict()["capital_authority"] is False


def test_direct_construction_rejects_mismatched_or_malformed_values() -> None:
    source = build_synthetic_research_return_series_observation()
    payload = _direct_payload(source)

    for field_name, value in (
        ("observation_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("symbol", "OTHER"),
        ("source_return_count", 99),
        ("positive_return_count", 99),
        ("negative_return_count", 99),
        ("zero_return_count", 99),
        ("min_simple_return", Decimal("0")),
        ("max_simple_return", Decimal("0")),
        ("mean_simple_return", Decimal("0")),
        ("summary_state", "other"),
        ("limitations", (_join("action", "able metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchReturnSummaryObservation(**mutated)


def test_authority_and_actionability_wording_is_rejected_outside_non_claims() -> None:
    source = build_synthetic_research_return_series_observation()
    payload = _direct_payload(source)

    for value in (
        _join("author", "ity metadata"),
        _join("action", "ability metadata"),
    ):
        mutated = dict(payload)
        mutated["limitations"] = (value,)
        with pytest.raises(ValidationError, match="limitations"):
            ResearchReturnSummaryObservation(**mutated)

    source_with_extra_non_claims = _observation_with_extra_non_claims()
    summary = build_research_return_summary_observation(source_with_extra_non_claims)

    assert _join("not action", "ability") in summary.non_claims
    assert _join("not capital ", "authority") in summary.non_claims


def test_limitations_and_non_claims_carry_forward_with_first_seen_dedupe() -> None:
    observation = _observation_with_duplicate_metadata()
    summary = build_research_return_summary_observation(observation)

    assert summary.limitations == (
        "synthetic close-to-close metadata only",
        "later samples ignored by builder",
    )
    assert summary.non_claims == tuple(dict.fromkeys(observation.non_claims))
    assert summary.to_dict()["limitations"] == list(summary.limitations)
    assert summary.to_dict()["non_claims"] == list(summary.non_claims)


def test_to_dict_is_primitive_only_and_deterministic() -> None:
    first = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    ).to_dict()
    second = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    ).to_dict()

    assert first == second == _expected_primary_summary_dict()
    assert tuple(first) == tuple(_expected_primary_summary_dict())
    assert _primitive_only(first)
    assert first["source_observation"] is not second["source_observation"]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _expected_primary_summary_dict()


def test_repeated_construction_is_byte_for_byte_deterministic_under_compact_json() -> None:
    first = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )
    second = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )
    first_json = _compact_json_bytes(first)
    second_json = _compact_json_bytes(second)

    assert first == second
    assert first is not second
    assert first_json == second_json
    assert first_json == json.dumps(
        _expected_primary_summary_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert json.loads(first_json.decode("utf-8")) == _expected_primary_summary_dict()


def test_source_observation_to_dict_is_unchanged_by_summary_construction() -> None:
    observation = build_synthetic_research_return_series_observation()
    before = observation.to_dict()
    summary = build_research_return_summary_observation(observation)
    after_build = observation.to_dict()
    payload = summary.to_dict()
    after_serialize = observation.to_dict()

    assert before == expected_synthetic_research_return_series_observation_dict()
    assert after_build == before
    assert payload["source_observation"] == before
    assert after_serialize == before


def test_object_is_frozen_and_slotted() -> None:
    summary = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )

    assert hasattr(ResearchReturnSummaryObservation, "__slots__")
    assert tuple(field.name for field in fields(ResearchReturnSummaryObservation)) == (
        "observation_type",
        "status",
        "authority",
        "capital_authority",
        "symbol",
        "as_of",
        "return_method",
        "price_basis",
        "source_return_count",
        "positive_return_count",
        "negative_return_count",
        "zero_return_count",
        "min_simple_return",
        "max_simple_return",
        "mean_simple_return",
        "summary_state",
        "source_observation",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        summary.symbol = "OTHER"
    with pytest.raises((AttributeError, TypeError)):
        summary.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    summary = build_research_return_summary_observation(
        build_synthetic_research_return_series_observation()
    )

    assert not hasattr(ResearchReturnSummaryObservation, "from_dict")
    assert not hasattr(summary, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_public_payload_keys_contain_no_action_or_trading_authority_fields() -> None:
    payloads = (
        build_research_return_summary_observation(
            build_synthetic_research_return_series_observation()
        ).to_dict(),
        build_research_return_summary_observation(
            build_synthetic_insufficient_research_return_series_observation()
        ).to_dict(),
    )

    for payload in payloads:
        assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))


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


def _expected_primary_summary_dict() -> dict[str, object]:
    source_observation = expected_synthetic_research_return_series_observation_dict()
    return {
        "observation_type": "research_return_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "return_method": "close_to_close_simple_return",
        "price_basis": "synthetic_close",
        "source_return_count": 3,
        "positive_return_count": 1,
        "negative_return_count": 1,
        "zero_return_count": 1,
        "min_simple_return": "-0.1",
        "max_simple_return": "0.05",
        "mean_simple_return": "-0.01666666666666666666666666667",
        "summary_state": "returns_summarized",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def _expected_insufficient_summary_dict() -> dict[str, object]:
    source_observation = (
        expected_synthetic_insufficient_research_return_series_observation_dict()
    )
    return {
        "observation_type": "research_return_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": "SYNTH_ETF",
        "as_of": "2026-01-20",
        "return_method": "close_to_close_simple_return",
        "price_basis": "synthetic_close",
        "source_return_count": 0,
        "positive_return_count": 0,
        "negative_return_count": 0,
        "zero_return_count": 0,
        "min_simple_return": None,
        "max_simple_return": None,
        "mean_simple_return": None,
        "summary_state": "insufficient_return_history",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def _direct_payload(
    observation: ResearchReturnSeriesObservation,
) -> dict[str, object]:
    return {
        "observation_type": "research_return_summary_observation",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "symbol": observation.symbol,
        "as_of": observation.as_of,
        "return_method": observation.return_method,
        "price_basis": observation.price_basis,
        "source_return_count": observation.return_count,
        "positive_return_count": 1,
        "negative_return_count": 1,
        "zero_return_count": 1,
        "min_simple_return": Decimal("-0.1"),
        "max_simple_return": Decimal("0.05"),
        "mean_simple_return": _EXPECTED_MEAN_SIMPLE_RETURN,
        "summary_state": "returns_summarized",
        "source_observation": observation,
        "limitations": observation.limitations,
        "non_claims": observation.non_claims,
    }


def _observation_with_duplicate_metadata() -> ResearchReturnSeriesObservation:
    source = build_synthetic_research_return_series_observation()
    return ResearchReturnSeriesObservation(
        observation_type=source.observation_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        symbol=source.symbol,
        as_of=source.as_of,
        return_method=source.return_method,
        price_basis=source.price_basis,
        sample_count=source.sample_count,
        eligible_sample_count=source.eligible_sample_count,
        ignored_future_sample_count=source.ignored_future_sample_count,
        return_count=source.return_count,
        returns=source.returns,
        limitations=(
            "synthetic close-to-close metadata only",
            "synthetic close-to-close metadata only",
            "later samples ignored by builder",
        ),
        non_claims=(*source.non_claims, source.non_claims[0]),
    )


def _observation_with_extra_non_claims() -> ResearchReturnSeriesObservation:
    source = build_synthetic_research_return_series_observation()
    return ResearchReturnSeriesObservation(
        observation_type=source.observation_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        symbol=source.symbol,
        as_of=source.as_of,
        return_method=source.return_method,
        price_basis=source.price_basis,
        sample_count=source.sample_count,
        eligible_sample_count=source.eligible_sample_count,
        ignored_future_sample_count=source.ignored_future_sample_count,
        return_count=source.return_count,
        returns=source.returns,
        limitations=source.limitations,
        non_claims=(
            *source.non_claims,
            _join("not action", "ability"),
            _join("not capital ", "authority"),
        ),
    )


def _compact_json_bytes(summary: ResearchReturnSummaryObservation) -> bytes:
    return json.dumps(
        summary.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


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
