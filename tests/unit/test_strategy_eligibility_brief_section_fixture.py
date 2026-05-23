from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from algotrader.research.strategy_eligibility_brief_item import (
    StrategyEligibilityBriefItem,
)
from algotrader.research.strategy_eligibility_brief_section import (
    StrategyEligibilityBriefSection,
    build_strategy_eligibility_brief_section,
)
from tests.fixtures import strategy_eligibility_brief_section as fixture_module
from tests.fixtures.strategy_eligibility_brief_item import (
    build_synthetic_strategy_eligibility_brief_item,
    expected_synthetic_strategy_eligibility_brief_item_dict,
)
from tests.fixtures.strategy_eligibility_brief_section import (
    build_synthetic_strategy_eligibility_brief_section,
    expected_synthetic_strategy_eligibility_brief_section_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


FIXTURE_PATH = Path("tests/fixtures/strategy_eligibility_brief_section.py")
_EXPECTED_ITEM_DICT = expected_synthetic_strategy_eligibility_brief_item_dict()
_EXPECTED_DICT = {
    "section_type": "strategy_eligibility_brief_section",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Strategy eligibility metadata: research_only",
    "summary": (
        "Advisory section contains 1 candidate eligibility item(s) across "
        "1 strategy id(s), state(s): research_only, with 3 limitation(s) "
        "and 9 non-claim(s)."
    ),
    "item_count": 1,
    "items": [_EXPECTED_ITEM_DICT],
    "limitations": list(_EXPECTED_ITEM_DICT["limitations"]),
    "non_claims": list(_EXPECTED_ITEM_DICT["non_claims"]),
}
_EXPECTED_ITEM_SOURCE_STATUS_JSON = (
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
_EXPECTED_ITEM_JSON = (
    '{"item_type":"strategy_eligibility_brief_item",'
    '"status":"candidate_only","authority":"advisory_only",'
    '"capital_authority":false,'
    '"strategy_id":"synthetic-strategy-eligibility-001",'
    '"strategy_name":"Synthetic strategy eligibility research fixture",'
    '"eligibility_state":"research_only",'
    '"headline":"Advisory eligibility metadata: research_only.",'
    '"summary":"Candidate metadata records research_only with 2 reason(s), '
    '3 limitation(s), 9 non-claim(s), 2 evidence reference(s), 2 blocker(s), '
    'and 2 required next step(s).",'
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
    '"not profitability evidence","not approval","not capital authority"],'
    '"source_status":'
    + _EXPECTED_ITEM_SOURCE_STATUS_JSON
    + "}"
)
_EXPECTED_COMPACT_JSON = (
    '{"section_type":"strategy_eligibility_brief_section",'
    '"status":"candidate_only","authority":"advisory_only",'
    '"capital_authority":false,'
    '"title":"Strategy eligibility metadata: research_only",'
    '"summary":"Advisory section contains 1 candidate eligibility item(s) '
    'across 1 strategy id(s), state(s): research_only, with 3 limitation(s) '
    'and 9 non-claim(s).",'
    '"item_count":1,'
    '"items":['
    + _EXPECTED_ITEM_JSON
    + '],'
    '"limitations":["synthetic metadata only",'
    '"no profitability evidence is represented",'
    '"no approval or readiness decision is represented"],'
    '"non_claims":["not validation","not paper readiness",'
    '"not live readiness","not a trading recommendation",'
    '"not allocation authority","not order authority",'
    '"not profitability evidence","not approval","not capital authority"]}'
)
_EXPECTED_COMPACT_JSON_BYTES = _EXPECTED_COMPACT_JSON.encode("ascii")
_REQUIRED_CORE_NON_CLAIMS = (
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
_TUPLE_FIELDS = ("limitations", "non_claims")
_FORBIDDEN_TEXT_TOKENS = (
    "profitability",
    "approval",
    "approved",
    "recommend",
    "paper",
    "live",
    "ready",
    "readiness",
    "capital",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.strategy_eligibility_brief_section",
    "tests.fixtures.strategy_eligibility_brief_item",
}
_ALLOWED_CALL_NAMES = {
    "build_strategy_eligibility_brief_section",
    "build_synthetic_strategy_eligibility_brief_item",
    "expected_synthetic_strategy_eligibility_brief_item_dict",
    "list",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
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
    _s("poly", "gon"),
    _s("quant", "connect"),
    _s("re", "quests"),
    "sklearn",
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
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
    _s("bro", "ker"),
    _s("bro", "kers"),
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
    _s("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_EXACT_LITERALS = {
    "account",
    "accounts",
    "approved",
    "buy",
    "sell",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    "paper_eligible",
    _s("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_LITERAL_SUBSTRINGS = (
    _s("bro", "ker"),
    _s("port", "folio"),
)


def test_fixture_builds_strategy_eligibility_brief_section() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()

    assert isinstance(section, StrategyEligibilityBriefSection)
    assert section.items
    assert isinstance(section.items[0], StrategyEligibilityBriefItem)


def test_fixture_uses_phase_156_item_fixture_and_phase_157_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_item = build_synthetic_strategy_eligibility_brief_item()

    assert fixture_module.build_synthetic_strategy_eligibility_brief_item is (
        build_synthetic_strategy_eligibility_brief_item
    )
    assert fixture_module.build_strategy_eligibility_brief_section is (
        build_strategy_eligibility_brief_section
    )

    def recording_item_fixture() -> StrategyEligibilityBriefItem:
        calls.append(("item_fixture", source_item))
        return source_item

    def recording_section_builder(
        items: tuple[StrategyEligibilityBriefItem, ...],
    ) -> StrategyEligibilityBriefSection:
        checked_items = tuple(items)
        calls.append(("section_builder", checked_items))
        return build_strategy_eligibility_brief_section(checked_items)

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_strategy_eligibility_brief_item",
        recording_item_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_strategy_eligibility_brief_section",
        recording_section_builder,
    )

    section = fixture_module.build_synthetic_strategy_eligibility_brief_section()

    assert [name for name, _ in calls] == ["item_fixture", "section_builder"]
    assert calls[0][1] is source_item
    assert calls[1][1] == (source_item,)
    assert section.items == (source_item,)
    assert section.items[0] is source_item


def test_expected_helper_uses_phase_156_expected_item_dictionary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    source_expected = expected_synthetic_strategy_eligibility_brief_item_dict()

    def recording_expected_item() -> dict[str, object]:
        calls.append("expected_item")
        return source_expected

    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_strategy_eligibility_brief_item_dict",
        recording_expected_item,
    )

    expected = (
        fixture_module.expected_synthetic_strategy_eligibility_brief_section_dict()
    )

    assert calls == ["expected_item"]
    assert expected["items"][0] is source_expected
    assert expected["items"][0] == _EXPECTED_ITEM_DICT
    assert expected["limitations"] == source_expected["limitations"]
    assert expected["limitations"] is not source_expected["limitations"]
    assert expected["non_claims"] == source_expected["non_claims"]
    assert expected["non_claims"] is not source_expected["non_claims"]


def test_fixture_contains_phase_156_item_payload_exactly() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    item = section.items[0]
    payload = section.to_dict()

    assert item.to_dict() == expected_synthetic_strategy_eligibility_brief_item_dict()
    assert payload["items"][0] == expected_synthetic_strategy_eligibility_brief_item_dict()
    assert payload["items"][0] == _EXPECTED_ITEM_DICT


def test_fixture_output_matches_expected_dictionary_exactly() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    payload = section.to_dict()
    expected = expected_synthetic_strategy_eligibility_brief_section_dict()

    assert expected == _EXPECTED_DICT
    assert payload == expected
    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert payload["items"][0] == _EXPECTED_ITEM_DICT
    _assert_primitive_only(payload)
    _assert_primitive_only(expected)


def test_repeated_fixture_construction_is_dict_and_byte_deterministic() -> None:
    first = build_synthetic_strategy_eligibility_brief_section()
    second = build_synthetic_strategy_eligibility_brief_section()
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_expected = expected_synthetic_strategy_eligibility_brief_section_dict()
    second_expected = expected_synthetic_strategy_eligibility_brief_section_dict()
    first_json_bytes = _compact_json_bytes(first_payload)
    second_json_bytes = _compact_json_bytes(second_payload)

    assert first is not second
    assert first.items[0] is not second.items[0]
    assert first_payload == second_payload == first_expected == second_expected
    assert first_payload == _EXPECTED_DICT
    assert first_json_bytes == second_json_bytes == _EXPECTED_COMPACT_JSON_BYTES
    assert json.loads(first_json_bytes.decode("ascii")) == first_payload


def test_fixed_advisory_metadata_is_pinned() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    payload = section.to_dict()

    assert section.section_type == "strategy_eligibility_brief_section"
    assert section.status == "candidate_only"
    assert section.authority == "advisory_only"
    assert section.capital_authority is False
    assert payload["section_type"] == "strategy_eligibility_brief_section"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False


def test_title_and_summary_are_pinned_and_non_actionable() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()

    assert section.title == _EXPECTED_DICT["title"]
    assert section.summary == _EXPECTED_DICT["summary"]
    assert section.to_dict()["title"] == _EXPECTED_DICT["title"]
    assert section.to_dict()["summary"] == _EXPECTED_DICT["summary"]

    for text in (section.title, section.summary):
        lowered = text.lower()
        for token in _FORBIDDEN_TEXT_TOKENS:
            assert token not in lowered


def test_tuple_storage_and_list_serialization_are_pinned() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    item = section.items[0]
    payload = section.to_dict()

    assert isinstance(section.items, tuple)
    assert section.items == (item,)
    assert isinstance(payload["items"], list)
    assert payload["items"] == [item.to_dict()]

    for field_name in _TUPLE_FIELDS:
        section_value = getattr(section, field_name)
        item_value = getattr(item, field_name)
        serialized = payload[field_name]
        nested_serialized = payload["items"][0][field_name]

        assert isinstance(section_value, tuple)
        assert isinstance(item_value, tuple)
        assert isinstance(serialized, list)
        assert isinstance(nested_serialized, list)
        assert section_value == item_value
        assert serialized == nested_serialized == list(item_value)
        assert serialized is not nested_serialized

    payload["items"].append(item.to_dict())
    payload["limitations"].append("mutated primitive copy")
    payload["items"][0]["limitations"].append("mutated nested primitive copy")

    assert section.to_dict() == _EXPECTED_DICT


def test_limitations_and_non_claims_are_present_and_carried_forward() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    item = section.items[0]
    payload = section.to_dict()

    assert section.limitations == item.limitations
    assert section.non_claims == item.non_claims
    assert payload["limitations"] == payload["items"][0]["limitations"]
    assert payload["non_claims"] == payload["items"][0]["non_claims"]
    assert set(_REQUIRED_CORE_NON_CLAIMS).issubset(section.non_claims)
    assert set(_ADDITIONAL_NON_CLAIMS).issubset(section.non_claims)
    assert all(value.startswith("not ") for value in section.non_claims)
    assert "no profitability evidence is represented" in section.limitations
    assert "no approval or readiness decision is represented" in section.limitations


def test_fixture_helpers_do_not_mutate_source_or_share_mutable_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_item = build_synthetic_strategy_eligibility_brief_item()
    source_before = source_item.to_dict()

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_strategy_eligibility_brief_item",
        lambda: source_item,
    )

    section = fixture_module.build_synthetic_strategy_eligibility_brief_section()
    payload = section.to_dict()
    first_expected = expected_synthetic_strategy_eligibility_brief_section_dict()
    second_expected = expected_synthetic_strategy_eligibility_brief_section_dict()

    assert first_expected["items"] is not second_expected["items"]
    assert first_expected["items"][0] is not second_expected["items"][0]
    for field_name in _TUPLE_FIELDS:
        assert first_expected[field_name] is not second_expected[field_name]
        assert (
            first_expected["items"][0][field_name]
            is not second_expected["items"][0][field_name]
        )
        assert first_expected[field_name] is not first_expected["items"][0][field_name]

    payload["items"][0]["source_status"]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")
    first_expected["items"][0]["limitations"].append("mutated expected copy")
    first_expected["limitations"].append("mutated expected copy")
    first_expected["non_claims"].append("not mutated expected copy")

    assert section.items[0] is source_item
    assert source_item.to_dict() == source_before == _EXPECTED_ITEM_DICT
    assert section.to_dict() == _EXPECTED_DICT
    assert second_expected == _EXPECTED_DICT
    assert expected_synthetic_strategy_eligibility_brief_section_dict() == (
        _EXPECTED_DICT
    )


def test_fixture_exposes_no_forbidden_authority_payload_or_object_fields() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    item = section.items[0]
    payload = section.to_dict()

    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _ast_dict_string_keys().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _call_keyword_names().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert all(
        not hasattr(section, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert all(not hasattr(item, field_name) for field_name in _FORBIDDEN_AUTHORITY_FIELDS)
    assert section.status == "candidate_only"
    assert section.capital_authority is False
    assert item.status == "candidate_only"
    assert item.capital_authority is False


def test_fixture_module_imports_no_forbidden_trading_or_runtime_paths() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_fixture_module_makes_no_io_network_or_authority_calls() -> None:
    call_names = _call_names()

    assert call_names == _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_literals_do_not_add_forbidden_authority_states() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
    for substring in _FORBIDDEN_LITERAL_SUBSTRINGS:
        assert substring not in lowered_source
    for token in (
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
        "trading_ready",
        "approved",
        "buy",
        "sell",
        "hold",
        _s("allo", "cation"),
        _s("or", "der"),
        _s("tra", "ding_authority"),
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
