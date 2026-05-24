from __future__ import annotations

import ast
import json
from pathlib import Path

from algotrader.research.sma_research_observation import SmaResearchObservation
from algotrader.research.sma_research_observation_brief import (
    SmaResearchObservationBriefItem,
    build_sma_research_observation_brief_item,
)
from tests.fixtures.sma_research_observation import (
    expected_synthetic_insufficient_history_sma_research_observation_dict,
    expected_synthetic_sma_research_observation_dict,
)
from tests.fixtures.sma_research_observation_brief import (
    build_synthetic_insufficient_history_sma_research_observation_brief_item,
    build_synthetic_sma_research_observation_brief_item,
    expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict,
    expected_synthetic_sma_research_observation_brief_item_dict,
)


MODULE_PATH = Path("tests/fixtures/sma_research_observation_brief.py")


def _join(*parts: str) -> str:
    return "".join(parts)


_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.sma_research_observation_brief",
    "tests.fixtures.sma_research_observation",
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
_FORBIDDEN_SOURCE_TOKENS = (
    _join("app", "roved"),
    _join("app", "roval"),
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("bro", "ker"),
    "account",
    _join("or", "der"),
    "fill",
    _join("allo", "cation"),
    _join("port", "folio"),
    _join("mut", "ation"),
    _join("pa", "per"),
    _join("li", "ve"),
    _join("read", "iness"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    _join("action", "able"),
    _join("file", "_io"),
    _join("net", "work"),
    _join("so", "cket"),
    "vendor",
    _join("cre", "dential"),
    _join("run", "time"),
    _join("sche", "duler"),
    "dashboard",
    "notebook",
    _join("l", "lm"),
    "agent",
    _join("ra", "nking"),
    _join("sco", "ring"),
    _join("capital ", "authority"),
    _join("tra", "ding authority"),
)
_FORBIDDEN_PAYLOAD_KEYS = {
    "account",
    "accounts",
    "actionable",
    _join("allo", "cation"),
    _join("allo", "cations"),
    _join("allo", "cation_authority"),
    "approved",
    "buy",
    _join("bro", "ker"),
    _join("bro", "ker_authority"),
    "evaluator",
    "fill",
    "fills",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _join("or", "der"),
    _join("or", "ders"),
    _join("or", "der_authority"),
    "paper_eligible",
    _join("port", "folio"),
    _join("port", "folios"),
    "ranking",
    _join("recomm", "endation"),
    "readiness",
    "score",
    "scoring",
    "sell",
    "signal",
    _join("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_POSITIVE_STATE_TEXT = (
    _join("app", "roved"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    _join("action", "able"),
)


def test_fixture_builders_return_exact_phase_197_production_type() -> None:
    primary = build_synthetic_sma_research_observation_brief_item()
    insufficient = (
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )

    assert type(primary) is SmaResearchObservationBriefItem
    assert type(insufficient) is SmaResearchObservationBriefItem
    assert type(primary.source_observation) is SmaResearchObservation
    assert type(insufficient.source_observation) is SmaResearchObservation


def test_expected_dict_helpers_match_to_dict_exactly() -> None:
    primary = build_synthetic_sma_research_observation_brief_item()
    insufficient = (
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )

    assert primary.to_dict() == (
        expected_synthetic_sma_research_observation_brief_item_dict()
    )
    assert insufficient.to_dict() == (
        expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict()
    )


def test_expected_dict_helpers_return_fresh_mutable_primitive_copies() -> None:
    first_primary = expected_synthetic_sma_research_observation_brief_item_dict()
    second_primary = expected_synthetic_sma_research_observation_brief_item_dict()
    first_insufficient = (
        expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict()
    )
    second_insufficient = (
        expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict()
    )

    assert _primitive_only(first_primary)
    assert _primitive_only(first_insufficient)
    assert first_primary is not second_primary
    assert first_primary["source_observation"] is not second_primary[
        "source_observation"
    ]
    assert first_primary["limitations"] is not second_primary["limitations"]
    assert first_primary["non_claims"] is not second_primary["non_claims"]
    assert first_insufficient is not second_insufficient
    assert first_insufficient["source_observation"] is not second_insufficient[
        "source_observation"
    ]
    assert first_insufficient["limitations"] is not second_insufficient["limitations"]
    assert first_insufficient["non_claims"] is not second_insufficient["non_claims"]

    first_primary["limitations"].append("mutated primitive copy")
    first_primary["non_claims"].append("not mutated primitive copy")
    first_primary["source_observation"]["limitations"].append("mutated nested copy")
    first_insufficient["limitations"].append("mutated primitive copy")
    first_insufficient["non_claims"].append("not mutated primitive copy")
    first_insufficient["source_observation"]["limitations"].append(
        "mutated nested copy"
    )

    assert second_primary == (
        build_synthetic_sma_research_observation_brief_item().to_dict()
    )
    assert second_insufficient == (
        build_synthetic_insufficient_history_sma_research_observation_brief_item().to_dict()
    )


def test_repeated_construction_is_deterministic() -> None:
    first_primary = build_synthetic_sma_research_observation_brief_item()
    second_primary = build_synthetic_sma_research_observation_brief_item()
    first_insufficient = (
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )
    second_insufficient = (
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )

    assert first_primary == second_primary
    assert first_primary is not second_primary
    assert first_primary.source_observation == second_primary.source_observation
    assert first_primary.source_observation is not second_primary.source_observation
    assert first_insufficient == second_insufficient
    assert first_insufficient is not second_insufficient
    assert first_insufficient.source_observation == second_insufficient.source_observation
    assert first_insufficient.source_observation is not second_insufficient.source_observation


def test_compact_json_bytes_are_deterministic() -> None:
    primary_json = _compact_json_bytes(
        build_synthetic_sma_research_observation_brief_item()
    )
    repeated_primary_json = _compact_json_bytes(
        build_synthetic_sma_research_observation_brief_item()
    )
    insufficient_json = _compact_json_bytes(
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )
    repeated_insufficient_json = _compact_json_bytes(
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )

    assert primary_json == repeated_primary_json
    assert insufficient_json == repeated_insufficient_json
    assert primary_json == json.dumps(
        expected_synthetic_sma_research_observation_brief_item_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert insufficient_json == json.dumps(
        expected_synthetic_insufficient_history_sma_research_observation_brief_item_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def test_primary_fixture_maps_to_above_sma_observation() -> None:
    item = build_synthetic_sma_research_observation_brief_item()
    payload = item.to_dict()

    assert item.item_type == "sma_research_observation_brief_item"
    assert item.status == "candidate_only"
    assert item.authority == "advisory_only"
    assert item.capital_authority is False
    assert item.mechanical_state == "above_sma_observation"
    assert payload["mechanical_state"] == "above_sma_observation"
    assert payload["source_observation"] == (
        expected_synthetic_sma_research_observation_dict()
    )


def test_insufficient_history_fixture_maps_to_insufficient_history() -> None:
    item = build_synthetic_insufficient_history_sma_research_observation_brief_item()
    payload = item.to_dict()

    assert item.item_type == "sma_research_observation_brief_item"
    assert item.status == "candidate_only"
    assert item.authority == "advisory_only"
    assert item.capital_authority is False
    assert item.mechanical_state == "insufficient_history"
    assert payload["mechanical_state"] == "insufficient_history"
    assert payload["source_observation"] == (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )


def test_nested_source_observations_match_phase_196_expected_payloads() -> None:
    primary = build_synthetic_sma_research_observation_brief_item()
    insufficient = (
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )

    assert primary.source_observation.to_dict() == (
        expected_synthetic_sma_research_observation_dict()
    )
    assert primary.to_dict()["source_observation"] == (
        expected_synthetic_sma_research_observation_dict()
    )
    assert insufficient.source_observation.to_dict() == (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )
    assert insufficient.to_dict()["source_observation"] == (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )


def test_source_observation_identity_is_preserved() -> None:
    primary = build_synthetic_sma_research_observation_brief_item()
    insufficient = (
        build_synthetic_insufficient_history_sma_research_observation_brief_item()
    )
    rebuilt_primary = build_sma_research_observation_brief_item(
        primary.source_observation
    )
    rebuilt_insufficient = build_sma_research_observation_brief_item(
        insufficient.source_observation
    )

    assert rebuilt_primary.source_observation is primary.source_observation
    assert rebuilt_primary.to_dict() == primary.to_dict()
    assert rebuilt_insufficient.source_observation is insufficient.source_observation
    assert rebuilt_insufficient.to_dict() == insufficient.to_dict()


def test_limitations_and_non_claims_carry_forward() -> None:
    for item in (
        build_synthetic_sma_research_observation_brief_item(),
        build_synthetic_insufficient_history_sma_research_observation_brief_item(),
    ):
        source_payload = item.source_observation.to_dict()
        assert item.limitations == tuple(item.source_observation.limitations)
        assert item.non_claims == tuple(item.source_observation.non_claims)
        assert item.to_dict()["limitations"] == list(source_payload["limitations"])
        assert item.to_dict()["non_claims"] == list(source_payload["non_claims"])


def test_no_from_dict_exists() -> None:
    item = build_synthetic_sma_research_observation_brief_item()

    assert not hasattr(SmaResearchObservationBriefItem, "from_dict")
    assert not hasattr(item, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_no_positive_action_or_authority_states_appear() -> None:
    payloads = (
        build_synthetic_sma_research_observation_brief_item().to_dict(),
        build_synthetic_insufficient_history_sma_research_observation_brief_item().to_dict(),
    )

    for payload in payloads:
        assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
        for text in _string_values(payload):
            lowered = text.lower()
            if lowered.startswith("not "):
                continue
            assert not any(
                token in lowered for token in _FORBIDDEN_POSITIVE_STATE_TEXT
            )


def test_fixture_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_module_has_no_forbidden_source_literals() -> None:
    lowered = _source_text().lower()

    assert [
        token for token in _FORBIDDEN_SOURCE_TOKENS if token in lowered
    ] == []


def _compact_json_bytes(item: SmaResearchObservationBriefItem) -> bytes:
    return json.dumps(
        item.to_dict(),
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


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        strings: list[str] = []
        for nested_value in value.values():
            strings.extend(_string_values(nested_value))
        return tuple(strings)
    if isinstance(value, list):
        strings = []
        for nested_value in value:
            strings.extend(_string_values(nested_value))
        return tuple(strings)

    return ()


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
