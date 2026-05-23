from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.strategy_eligibility_brief import (
    StrategyEligibilityBrief,
    build_strategy_eligibility_brief,
)
from algotrader.research.strategy_eligibility_brief_item import (
    build_strategy_eligibility_brief_item,
)
from algotrader.research.strategy_eligibility_brief_section import (
    StrategyEligibilityBriefSection,
    build_strategy_eligibility_brief_section,
)
from algotrader.research.strategy_eligibility_status import (
    build_strategy_eligibility_status,
)
from tests.fixtures.strategy_eligibility_brief_section import (
    build_synthetic_strategy_eligibility_brief_section,
    expected_synthetic_strategy_eligibility_brief_section_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/strategy_eligibility_brief.py")
_EXPECTED_SECTION_DICT = expected_synthetic_strategy_eligibility_brief_section_dict()
_EXPECTED_BRIEF_DICT = {
    "brief_type": "strategy_eligibility_brief",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Strategy eligibility brief metadata",
    "summary": (
        "Advisory brief contains 1 strategy eligibility section(s), "
        "1 candidate item(s), 3 limitation(s), and 9 non-claim(s)."
    ),
    "section_count": 1,
    "sections": [_EXPECTED_SECTION_DICT],
    "limitations": list(_EXPECTED_SECTION_DICT["limitations"]),
    "non_claims": list(_EXPECTED_SECTION_DICT["non_claims"]),
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
_EXPECTED_SECTION_JSON = (
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
_EXPECTED_COMPACT_JSON = (
    '{"brief_type":"strategy_eligibility_brief",'
    '"status":"candidate_only","authority":"advisory_only",'
    '"capital_authority":false,'
    '"title":"Strategy eligibility brief metadata",'
    '"summary":"Advisory brief contains 1 strategy eligibility section(s), '
    '1 candidate item(s), 3 limitation(s), and 9 non-claim(s).",'
    '"section_count":1,'
    '"sections":['
    + _EXPECTED_SECTION_JSON
    + '],'
    '"limitations":["synthetic metadata only",'
    '"no profitability evidence is represented",'
    '"no approval or readiness decision is represented"],'
    '"non_claims":["not validation","not paper readiness",'
    '"not live readiness","not a trading recommendation",'
    '"not allocation authority","not order authority",'
    '"not profitability evidence","not approval","not capital authority"]}'
)
_REQUIRED_CORE_NON_CLAIMS = (
    "not validation",
    "not paper readiness",
    "not live readiness",
    _s("not a tra", "ding recommendation"),
    _s("not allo", "cation authority"),
    _s("not or", "der authority"),
)
_FORBIDDEN_TEXT_TOKENS = (
    "recommend",
    "approval",
    "approved",
    "paper",
    "live",
    "ready",
    "readiness",
    "trade",
    "trading",
    _s("allo", "cation"),
    _s("or", "der"),
    "buy",
    "sell",
    "hold",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.strategy_eligibility_brief_section",
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


def test_valid_construction_from_phase_158_synthetic_section_fixture() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    brief = build_strategy_eligibility_brief([section])

    assert isinstance(brief, StrategyEligibilityBrief)
    assert brief.sections == (section,)
    assert brief.sections[0] is section
    assert brief.to_dict() == _EXPECTED_BRIEF_DICT
    assert brief.to_dict()["sections"][0] == (
        expected_synthetic_strategy_eligibility_brief_section_dict()
    )


def test_source_section_object_identity_is_preserved() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    brief = build_strategy_eligibility_brief((section,))

    assert brief.sections[0] is section
    assert brief.to_dict()["sections"][0] == section.to_dict()


def test_section_collections_are_converted_to_immutable_tuples() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    payload = _valid_constructor_payload(section)
    payload["sections"] = [section]
    brief = StrategyEligibilityBrief(**payload)

    assert isinstance(brief.sections, tuple)
    assert brief.sections == (section,)
    assert brief.sections[0] is section


def test_section_ordering_is_preserved() -> None:
    first = build_synthetic_strategy_eligibility_brief_section()
    second = _second_section()
    brief = build_strategy_eligibility_brief([second, first])
    payload = brief.to_dict()

    assert brief.sections == (second, first)
    assert brief.sections[0] is second
    assert brief.sections[1] is first
    assert payload["sections"] == [second.to_dict(), first.to_dict()]
    assert brief.summary == (
        "Advisory brief contains 2 strategy eligibility section(s), "
        "2 candidate item(s), 4 limitation(s), and 10 non-claim(s)."
    )


def test_duplicate_section_identity_is_rejected() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()

    with pytest.raises(ValidationError, match="duplicate section identities"):
        build_strategy_eligibility_brief([section, section])

    payload = _valid_constructor_payload(section)
    payload["sections"] = (section, section)
    with pytest.raises(ValidationError, match="duplicate section identities"):
        StrategyEligibilityBrief(**payload)


def test_empty_section_collection_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        build_strategy_eligibility_brief([])

    payload = _valid_constructor_payload()
    payload["sections"] = ()
    with pytest.raises(ValidationError, match="at least one"):
        StrategyEligibilityBrief(**payload)


def test_non_section_and_malformed_section_like_objects_are_rejected() -> None:
    class SectionLike:
        section_type = "strategy_eligibility_brief_section"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False
        title = _EXPECTED_SECTION_DICT["title"]
        summary = _EXPECTED_SECTION_DICT["summary"]
        items = ()
        limitations = tuple(_EXPECTED_SECTION_DICT["limitations"])
        non_claims = tuple(_EXPECTED_SECTION_DICT["non_claims"])

        def to_dict(self) -> dict[str, object]:
            return dict(_EXPECTED_SECTION_DICT)

    with pytest.raises(ValidationError, match="StrategyEligibilityBriefSection"):
        build_strategy_eligibility_brief([object()])  # type: ignore[list-item]

    with pytest.raises(ValidationError, match="StrategyEligibilityBriefSection"):
        build_strategy_eligibility_brief([SectionLike()])  # type: ignore[list-item]

    with pytest.raises(ValidationError, match="iterable"):
        build_strategy_eligibility_brief(object())  # type: ignore[arg-type]


def test_fixed_brief_metadata_values_are_pinned() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    brief = build_strategy_eligibility_brief([section])
    payload = brief.to_dict()

    assert brief.brief_type == "strategy_eligibility_brief"
    assert brief.status == "candidate_only"
    assert brief.authority == "advisory_only"
    assert brief.capital_authority is False
    assert payload["brief_type"] == "strategy_eligibility_brief"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False

    for field_name, value in (
        ("brief_type", "strategy_eligibility_brief_section"),
        ("status", "research_only"),
        ("authority", "capital_authority"),
        ("capital_authority", True),
    ):
        constructor_payload = _valid_constructor_payload(section)
        constructor_payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            StrategyEligibilityBrief(**constructor_payload)


def test_title_and_summary_are_deterministic_and_advisory_only() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    first = build_strategy_eligibility_brief([section])
    second = build_strategy_eligibility_brief([section])

    assert first.title == second.title == _EXPECTED_BRIEF_DICT["title"]
    assert first.summary == second.summary == _EXPECTED_BRIEF_DICT["summary"]
    for text in (first.title, first.summary):
        lowered = text.lower()
        for token in _FORBIDDEN_TEXT_TOKENS:
            assert token not in lowered

    for field_name, value in (
        ("title", "Candidate metadata"),
        ("summary", "Candidate metadata"),
    ):
        constructor_payload = _valid_constructor_payload(section)
        constructor_payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            StrategyEligibilityBrief(**constructor_payload)


def test_to_dict_exact_output_and_compact_json_are_pinned() -> None:
    brief = build_strategy_eligibility_brief(
        [build_synthetic_strategy_eligibility_brief_section()]
    )
    payload = brief.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_BRIEF_DICT
    assert tuple(payload) == tuple(_EXPECTED_BRIEF_DICT)
    assert compact_json == _EXPECTED_COMPACT_JSON
    assert json.loads(compact_json) == payload
    _assert_primitive_only(payload)

    payload["sections"][0]["limitations"].append("mutated primitive copy")
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive copy")

    assert brief.to_dict() == _EXPECTED_BRIEF_DICT


def test_repeated_construction_is_deterministic() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    first = build_strategy_eligibility_brief([section])
    second = build_strategy_eligibility_brief([section])
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_json = json.dumps(first_payload, ensure_ascii=True, separators=(",", ":"))
    second_json = json.dumps(second_payload, ensure_ascii=True, separators=(",", ":"))

    assert first is not second
    assert first.sections == second.sections == (section,)
    assert first.sections[0] is second.sections[0] is section
    assert first_payload == second_payload == _EXPECTED_BRIEF_DICT
    assert first_json == second_json == _EXPECTED_COMPACT_JSON


def test_source_section_is_not_mutated() -> None:
    section = build_synthetic_strategy_eligibility_brief_section()
    before = section.to_dict()
    brief = build_strategy_eligibility_brief([section])
    payload = brief.to_dict()

    payload["sections"][0]["items"][0]["source_status"]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")

    assert section.to_dict() == before == _EXPECTED_SECTION_DICT
    assert brief.sections[0] is section
    assert brief.to_dict() == _EXPECTED_BRIEF_DICT


def test_nested_section_dictionary_matches_phase_158_expected_helper() -> None:
    brief = build_strategy_eligibility_brief(
        [build_synthetic_strategy_eligibility_brief_section()]
    )

    assert brief.to_dict()["sections"][0] == (
        expected_synthetic_strategy_eligibility_brief_section_dict()
    )


def test_non_claims_and_limitations_are_carried_forward() -> None:
    first = build_synthetic_strategy_eligibility_brief_section()
    second = _second_section()
    brief = build_strategy_eligibility_brief([first, second])

    assert brief.limitations == (
        "synthetic metadata only",
        "no profitability evidence is represented",
        "no approval or readiness decision is represented",
        "secondary metadata only",
    )
    assert brief.non_claims == (
        *_EXPECTED_SECTION_DICT["non_claims"],
        "not secondary metadata claim",
    )
    for section in (first, second):
        assert all(value in brief.limitations for value in section.limitations)
        assert all(value in brief.non_claims for value in section.non_claims)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("status", "paper_eligible"),
        ("status", "live_probe_eligible"),
        ("status", "live_authorized"),
        ("status", "trading_ready"),
        ("status", "approved"),
        ("title", "paper_eligible"),
        ("title", "live_probe_eligible"),
        ("title", "live_authorized"),
        ("title", "trading_ready"),
        ("title", "approved"),
        ("summary", "paper_eligible"),
        ("summary", "live_probe_eligible"),
        ("summary", "live_authorized"),
        ("summary", "trading_ready"),
        ("summary", "approved"),
    ),
)
def test_paper_live_approved_and_trading_ready_states_remain_impossible(
    field_name: str,
    value: str,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        StrategyEligibilityBrief(**constructor_payload)


def test_brief_is_frozen_slotted_and_has_no_from_dict() -> None:
    brief = build_strategy_eligibility_brief(
        [build_synthetic_strategy_eligibility_brief_section()]
    )

    assert hasattr(StrategyEligibilityBrief, "__slots__")
    assert not hasattr(brief, "__dict__")
    assert not hasattr(StrategyEligibilityBrief, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        brief.summary = "changed"


def test_no_actionable_trading_authority_fields_are_exposed() -> None:
    brief = build_strategy_eligibility_brief(
        [build_synthetic_strategy_eligibility_brief_section()]
    )
    field_names = {field.name for field in fields(StrategyEligibilityBrief)}
    payload_keys = _payload_keys(brief.to_dict())
    ast_fields = _brief_ast_fields()
    ast_dict_keys = _to_dict_string_keys()

    assert tuple(field.name for field in fields(StrategyEligibilityBrief)) == (
        "brief_type",
        "status",
        "authority",
        "capital_authority",
        "title",
        "summary",
        "sections",
        "limitations",
        "non_claims",
    )
    assert tuple(brief.to_dict()) == tuple(_EXPECTED_BRIEF_DICT)
    assert field_names.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_fields.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_dict_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert payload_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert all(
        not hasattr(brief, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert brief.status == "candidate_only"
    assert brief.capital_authority is False


def test_module_imports_no_forbidden_vendor_network_runtime_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_literals_do_not_add_actionable_authority_states() -> None:
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


def _valid_constructor_payload(
    section: StrategyEligibilityBriefSection | None = None,
) -> dict[str, object]:
    source_section = section or build_synthetic_strategy_eligibility_brief_section()
    return {
        "brief_type": "strategy_eligibility_brief",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _EXPECTED_BRIEF_DICT["title"],
        "summary": _EXPECTED_BRIEF_DICT["summary"],
        "sections": (source_section,),
        "limitations": source_section.limitations,
        "non_claims": source_section.non_claims,
    }


def _second_section() -> StrategyEligibilityBriefSection:
    status = build_strategy_eligibility_status(
        strategy_id="synthetic-strategy-eligibility-002",
        strategy_name="Secondary synthetic strategy metadata",
        eligibility_state="watchlist_only",
        reasons=("secondary strategy metadata is scoped to advisory display",),
        limitations=("synthetic metadata only", "secondary metadata only"),
        non_claims=(
            *_REQUIRED_CORE_NON_CLAIMS,
            "not secondary metadata claim",
        ),
        evidence_refs=("synthetic-secondary-evidence-ref-001",),
        required_next_steps=("complete secondary metadata review before any claim",),
    )
    item = build_strategy_eligibility_brief_item(status)
    return build_strategy_eligibility_brief_section((item,))


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
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


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


def _brief_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.ClassDef) and node.name == "StrategyEligibilityBrief":
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("StrategyEligibilityBrief class was not found.")


def _to_dict_string_keys() -> set[str]:
    keys: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == "to_dict":
            for nested in ast.walk(node):
                if isinstance(nested, ast.Dict):
                    for key in nested.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            keys.add(key.value)

    return keys


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
