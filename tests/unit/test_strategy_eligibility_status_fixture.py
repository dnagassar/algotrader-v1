from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from algotrader.research.strategy_eligibility_status import (
    StrategyEligibilityStatus,
)
from tests.fixtures import strategy_eligibility_status as fixture_module
from tests.fixtures.strategy_eligibility_status import (
    build_synthetic_strategy_eligibility_status,
    expected_synthetic_strategy_eligibility_status_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


FIXTURE_PATH = Path("tests/fixtures/strategy_eligibility_status.py")
_TUPLE_FIELDS = (
    "reasons",
    "evidence_refs",
    "blockers",
    "required_next_steps",
    "limitations",
    "non_claims",
)
_REQUIRED_NON_CLAIMS = (
    "not validation",
    "not paper readiness",
    "not live readiness",
    _s("not a tra", "ding recommendation"),
    _s("not allo", "cation authority"),
    _s("not or", "der authority"),
)
_ADDITIONAL_NON_CLAIMS = (
    "not profitability evidence",
    "not approval",
    "not capital authority",
)
_EXPECTED_DICT = {
    "eligibility_type": "strategy_eligibility_status",
    "authority": "advisory_only",
    "capital_authority": False,
    "strategy_id": "synthetic-strategy-eligibility-001",
    "strategy_name": "Synthetic strategy eligibility research fixture",
    "eligibility_state": "research_only",
    "reasons": [
        "synthetic strategy metadata is scoped to research review",
        "eligibility status is provided for advisory composition tests",
    ],
    "evidence_refs": [
        "synthetic-evidence-ref-001",
        "synthetic-advisory-metadata-ref-001",
    ],
    "blockers": [
        "validation review has not been completed",
        "readiness review has not been completed",
    ],
    "required_next_steps": [
        "complete independent methodology review before any readiness claim",
        "collect validation evidence before any approval claim",
    ],
    "limitations": [
        "synthetic metadata only",
        "no profitability evidence is represented",
        "no approval or readiness decision is represented",
    ],
    "non_claims": [*_REQUIRED_NON_CLAIMS, *_ADDITIONAL_NON_CLAIMS],
}
_EXPECTED_COMPACT_JSON = (
    '{"eligibility_type":"strategy_eligibility_status",'
    '"authority":"advisory_only","capital_authority":false,'
    '"strategy_id":"synthetic-strategy-eligibility-001",'
    '"strategy_name":"Synthetic strategy eligibility research fixture",'
    '"eligibility_state":"research_only",'
    '"reasons":["synthetic strategy metadata is scoped to research review",'
    '"eligibility status is provided for advisory composition tests"],'
    '"evidence_refs":["synthetic-evidence-ref-001",'
    '"synthetic-advisory-metadata-ref-001"],'
    '"blockers":["validation review has not been completed",'
    '"readiness review has not been completed"],'
    '"required_next_steps":["complete independent methodology review before any '
    'readiness claim","collect validation evidence before any approval claim"],'
    '"limitations":["synthetic metadata only",'
    '"no profitability evidence is represented",'
    '"no approval or readiness decision is represented"],'
    '"non_claims":["not validation","not paper readiness",'
    '"not live readiness","not a trading recommendation",'
    '"not allocation authority","not order authority",'
    '"not profitability evidence","not approval","not capital authority"]}'
)
_EXPECTED_COMPACT_JSON_BYTES = _EXPECTED_COMPACT_JSON.encode("ascii")

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.strategy_eligibility_status",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.execution",
    _s("algotrader.", "l", "lm"),
    _s("algotrader.", "l", "lms"),
    "algotrader.ml",
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.risk",
    _s("algotrader.", "run", "time"),
    "algotrader.scheduler",
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    _s("data", "base"),
    "duckdb",
    "httpx",
    "ipynb",
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("net", "work"),
    _s("pan", "das"),
    _s("poly", "gon"),
    _s("re", "quests"),
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "urllib",
    "vectorbt",
    _s("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    _s("cli", "ent"),
    _s("con", "nect"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "exists",
    "from_file",
    "getenv",
    "glob",
    _s("import_module"),
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "load",
    "loads",
    "mkdir",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "post",
    "print",
    _s("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "rglob",
    "save",
    _s("so", "cket.socket"),
    "stat",
    _s("sub", "mit_", "or", "der"),
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
_FORBIDDEN_AUTHORITY_FIELDS = {
    "account",
    "accounts",
    "approved",
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _s("or", "der"),
    _s("or", "ders"),
    "paper_eligible",
    _s("port", "folio"),
    _s("port", "folios"),
    _s("allo", "cation"),
    _s("allo", "cations"),
    _s("allo", "cation_authority"),
    _s("or", "der_authority"),
    "trading_authority",
    "trading_ready",
}
_FORBIDDEN_EXACT_LITERALS = {
    "approved",
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    "paper_eligible",
    "trading_authority",
    "trading_ready",
}
_FORBIDDEN_LITERAL_SUBSTRINGS = (
    _s("bro", "ker"),
    _s("port", "folio"),
)


def test_fixture_builds_strategy_eligibility_status() -> None:
    status = build_synthetic_strategy_eligibility_status()

    assert isinstance(status, StrategyEligibilityStatus)
    assert status.eligibility_state == "research_only"


def test_fixture_uses_phase_153_public_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    real_builder = fixture_module.build_strategy_eligibility_status

    def recording_builder(**kwargs: object) -> StrategyEligibilityStatus:
        calls.append(kwargs)
        return real_builder(**kwargs)

    monkeypatch.setattr(
        fixture_module,
        "build_strategy_eligibility_status",
        recording_builder,
    )

    status = fixture_module.build_synthetic_strategy_eligibility_status()

    assert isinstance(status, StrategyEligibilityStatus)
    assert calls == [
        {
            "strategy_id": _EXPECTED_DICT["strategy_id"],
            "strategy_name": _EXPECTED_DICT["strategy_name"],
            "eligibility_state": "research_only",
            "reasons": tuple(_EXPECTED_DICT["reasons"]),
            "evidence_refs": tuple(_EXPECTED_DICT["evidence_refs"]),
            "blockers": tuple(_EXPECTED_DICT["blockers"]),
            "required_next_steps": tuple(_EXPECTED_DICT["required_next_steps"]),
            "limitations": tuple(_EXPECTED_DICT["limitations"]),
            "non_claims": tuple(_EXPECTED_DICT["non_claims"]),
        }
    ]


def test_fixture_output_matches_expected_dictionary_exactly() -> None:
    status = build_synthetic_strategy_eligibility_status()
    expected = expected_synthetic_strategy_eligibility_status_dict()

    assert expected == _EXPECTED_DICT
    assert status.to_dict() == expected
    assert tuple(expected) == tuple(_EXPECTED_DICT)
    assert expected is not status.to_dict()
    _assert_primitive_only(expected)


def test_repeated_fixture_construction_is_dict_and_byte_deterministic() -> None:
    first = build_synthetic_strategy_eligibility_status()
    second = build_synthetic_strategy_eligibility_status()
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_expected = expected_synthetic_strategy_eligibility_status_dict()
    second_expected = expected_synthetic_strategy_eligibility_status_dict()
    first_json_bytes = _compact_json_bytes(first_payload)
    second_json_bytes = _compact_json_bytes(second_payload)

    assert first is not second
    assert first_payload == second_payload == first_expected == second_expected
    assert first_json_bytes == second_json_bytes == _EXPECTED_COMPACT_JSON_BYTES
    assert json.loads(first_json_bytes.decode("ascii")) == first_payload


def test_fixture_state_and_fixed_advisory_metadata_are_pinned() -> None:
    status = build_synthetic_strategy_eligibility_status()
    payload = status.to_dict()

    assert status.eligibility_type == "strategy_eligibility_status"
    assert status.authority == "advisory_only"
    assert status.capital_authority is False
    assert status.eligibility_state == "research_only"
    assert payload["eligibility_type"] == "strategy_eligibility_status"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["strategy_id"] == "synthetic-strategy-eligibility-001"
    assert payload["strategy_name"] == (
        "Synthetic strategy eligibility research fixture"
    )


def test_tuple_storage_and_list_serialization_are_pinned() -> None:
    status = build_synthetic_strategy_eligibility_status()
    payload = status.to_dict()

    for field_name in _TUPLE_FIELDS:
        value = getattr(status, field_name)
        serialized = payload[field_name]
        assert isinstance(value, tuple)
        assert isinstance(serialized, list)
        assert serialized == list(value)

    payload["reasons"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive source")

    assert status.to_dict() == _EXPECTED_DICT


def test_non_claims_and_limitations_are_present_and_negative() -> None:
    status = build_synthetic_strategy_eligibility_status()

    assert status.limitations
    assert status.non_claims
    assert set(_REQUIRED_NON_CLAIMS).issubset(status.non_claims)
    assert set(_ADDITIONAL_NON_CLAIMS).issubset(status.non_claims)
    assert all(value.startswith("not ") for value in status.non_claims)
    assert "no profitability evidence is represented" in status.limitations
    assert "no approval or readiness decision is represented" in status.limitations


def test_expected_helper_returns_fresh_primitive_lists() -> None:
    first = expected_synthetic_strategy_eligibility_status_dict()
    second = expected_synthetic_strategy_eligibility_status_dict()

    assert first is not second
    for field_name in _TUPLE_FIELDS:
        assert first[field_name] is not second[field_name]

    first["reasons"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _EXPECTED_DICT
    assert expected_synthetic_strategy_eligibility_status_dict() == _EXPECTED_DICT


def test_fixture_building_does_not_mutate_source_collections() -> None:
    source_names = (
        "_REASONS",
        "_EVIDENCE_REFS",
        "_BLOCKERS",
        "_REQUIRED_NEXT_STEPS",
        "_LIMITATIONS",
        "_NON_CLAIMS",
    )
    before = {name: tuple(getattr(fixture_module, name)) for name in source_names}

    status = build_synthetic_strategy_eligibility_status()
    expected = expected_synthetic_strategy_eligibility_status_dict()
    expected["limitations"].append("mutated primitive copy")
    expected["non_claims"].append("not mutated primitive copy")

    after = {name: tuple(getattr(fixture_module, name)) for name in source_names}
    assert after == before
    assert status.to_dict() == _EXPECTED_DICT


def test_fixture_exposes_no_forbidden_authority_payload_or_object_fields() -> None:
    status = build_synthetic_strategy_eligibility_status()
    payload = status.to_dict()

    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _ast_dict_string_keys().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _call_keyword_names().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert all(
        not hasattr(status, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert status.capital_authority is False


def test_fixture_module_imports_no_forbidden_trading_or_runtime_paths() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_fixture_module_makes_no_io_network_or_authority_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_literals_do_not_add_forbidden_authority_states() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
    for substring in _FORBIDDEN_LITERAL_SUBSTRINGS:
        assert substring not in lowered_source
    for token in (
        _s("allo", "cation"),
        _s("or", "der"),
        _s("tra", "ding"),
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
        "trading_authority",
        "trading_ready",
    ):
        assert token not in lowered_source


def _compact_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode(
        "ascii"
    )


def _assert_primitive_only(value: object) -> None:
    assert not isinstance(value, (tuple, set))
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


def _source_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(FIXTURE_PATH))


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


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
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


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _ast_dict_string_keys() -> set[str]:
    keys: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.add(key.value)

    return keys


def _call_keyword_names() -> set[str]:
    return {
        keyword.arg
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg is not None
    }


def _string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
