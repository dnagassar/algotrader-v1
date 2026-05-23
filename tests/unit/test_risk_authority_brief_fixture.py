from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from algotrader.research.risk_authority_brief import (
    RiskAuthorityBrief,
    build_risk_authority_brief,
)
from algotrader.research.risk_authority_brief_section import (
    RiskAuthorityBriefSection,
)
from tests.fixtures import risk_authority_brief as fixture_module
from tests.fixtures.risk_authority_brief import (
    build_synthetic_risk_authority_brief,
    expected_synthetic_risk_authority_brief_dict,
)
from tests.fixtures.risk_authority_brief_section import (
    build_synthetic_risk_authority_brief_section,
    expected_synthetic_risk_authority_brief_section_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


FIXTURE_PATH = Path("tests/fixtures/risk_authority_brief.py")
_EXPECTED_SECTION_DICT = expected_synthetic_risk_authority_brief_section_dict()
_EXPECTED_DICT = {
    "brief_type": "risk_authority_brief",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Advisory risk metadata brief: 1 section",
    "summary": (
        "Advisory brief contains 1 candidate risk metadata section(s) with "
        "1 item(s), 3 limitation(s), and 13 non-claim(s)."
    ),
    "section_count": 1,
    "sections": [_EXPECTED_SECTION_DICT],
    "limitations": list(_EXPECTED_SECTION_DICT["limitations"]),
    "non_claims": list(_EXPECTED_SECTION_DICT["non_claims"]),
}
_EXPECTED_SECTION_JSON = json.dumps(
    _EXPECTED_SECTION_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_EXPECTED_COMPACT_JSON = (
    '{"brief_type":"risk_authority_brief",'
    '"status":"candidate_only","authority":"advisory_only",'
    '"capital_authority":false,'
    '"title":"Advisory risk metadata brief: 1 section",'
    '"summary":"Advisory brief contains 1 candidate risk metadata section(s) '
    'with 1 item(s), 3 limitation(s), and 13 non-claim(s).",'
    '"section_count":1,'
    '"sections":['
    + _EXPECTED_SECTION_JSON
    + '],'
    '"limitations":["synthetic metadata only",'
    '"no approval, readiness, recommendation, allocation, order placement, '
    'broker access, portfolio mutation, capital authority, or trading authority '
    'is represented",'
    '"fixture output is not connected to runtime or account state"],'
    '"non_claims":["not risk approval","not allocation authority",'
    '"not order authority","not paper readiness","not live readiness",'
    '"not broker authority","not portfolio mutation authority",'
    '"not capital authority","not trading authority",'
    '"not a trading recommendation","not order placement",'
    '"not broker access","not portfolio mutation"]}'
)
_EXPECTED_COMPACT_JSON_BYTES = _EXPECTED_COMPACT_JSON.encode("ascii")
_TUPLE_FIELDS = ("limitations", "non_claims")
_REQUIRED_NON_CLAIMS = (
    "not risk approval",
    _s("not allo", "cation authority"),
    _s("not or", "der authority"),
    "not paper readiness",
    "not live readiness",
    _s("not bro", "ker authority"),
    _s("not port", "folio mutation authority"),
    "not capital authority",
    "not trading authority",
)
_ADDITIONAL_NON_CLAIMS = (
    _s("not a tra", "ding recommendation"),
    _s("not or", "der placement"),
    _s("not bro", "ker access"),
    _s("not port", "folio mutation"),
)
_FORBIDDEN_TEXT_TOKENS = (
    "approval",
    "approved",
    "recommend",
    "paper",
    "live",
    "ready",
    "readiness",
    _s("allo", "cation"),
    _s("or", "der"),
    _s("bro", "ker"),
    _s("port", "folio"),
    "buy",
    "sell",
    "hold",
    "trade",
    "trading",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.risk_authority_brief",
    "tests.fixtures.risk_authority_brief_section",
}
_ALLOWED_CALL_NAMES = {
    "build_risk_authority_brief",
    "build_synthetic_risk_authority_brief_section",
    "expected_synthetic_risk_authority_brief_section_dict",
    "list",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.backtest",
    "algotrader.backtesting",
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
    _s("poly", "gon"),
    _s("quant", "connect"),
    _s("re", "quests"),
    "sklearn",
    _s("sk", "learn"),
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
    _s("allo", "cation"),
    _s("allo", "cations"),
    _s("allo", "cation_authority"),
    _s("bro", "ker"),
    _s("bro", "ker_authority"),
    "buy",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _s("or", "der"),
    _s("or", "der_authority"),
    _s("or", "der_ready"),
    _s("or", "ders"),
    "paper_eligible",
    _s("port", "folio"),
    _s("port", "folio_mutation"),
    "position_size",
    "sell",
    "target_weight",
    "trading_authority",
    "trading_ready",
}
_FORBIDDEN_EXACT_LITERALS = {
    "account",
    "accounts",
    "approved",
    _s("allo", "cation"),
    _s("allo", "cation_authority"),
    _s("bro", "ker"),
    _s("bro", "ker_authority"),
    "buy",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _s("or", "der"),
    _s("or", "der_authority"),
    "paper_eligible",
    _s("port", "folio"),
    _s("port", "folio_mutation"),
    "position_size",
    "sell",
    "target_weight",
    "trading_authority",
    "trading_ready",
}


def test_fixture_builds_risk_authority_brief() -> None:
    brief = build_synthetic_risk_authority_brief()

    assert isinstance(brief, RiskAuthorityBrief)
    assert brief.sections
    assert isinstance(brief.sections[0], RiskAuthorityBriefSection)


def test_fixture_uses_phase_174_section_fixture_and_phase_175_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_section = build_synthetic_risk_authority_brief_section()

    assert fixture_module.build_synthetic_risk_authority_brief_section is (
        build_synthetic_risk_authority_brief_section
    )
    assert fixture_module.build_risk_authority_brief is build_risk_authority_brief

    def recording_section_fixture() -> RiskAuthorityBriefSection:
        calls.append(("section_fixture", source_section))
        return source_section

    def recording_brief_builder(
        sections: tuple[RiskAuthorityBriefSection, ...],
    ) -> RiskAuthorityBrief:
        checked_sections = tuple(sections)
        calls.append(("brief_builder", checked_sections))
        return build_risk_authority_brief(checked_sections)

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_risk_authority_brief_section",
        recording_section_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_risk_authority_brief",
        recording_brief_builder,
    )

    brief = fixture_module.build_synthetic_risk_authority_brief()

    assert [name for name, _ in calls] == ["section_fixture", "brief_builder"]
    assert calls[0][1] is source_section
    assert calls[1][1] == (source_section,)
    assert brief.sections == (source_section,)
    assert brief.sections[0] is source_section


def test_expected_helper_uses_phase_174_expected_section_dictionary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    source_expected = expected_synthetic_risk_authority_brief_section_dict()

    def recording_expected_section() -> dict[str, object]:
        calls.append("expected_section")
        return source_expected

    monkeypatch.setattr(
        fixture_module,
        "expected_synthetic_risk_authority_brief_section_dict",
        recording_expected_section,
    )

    expected = fixture_module.expected_synthetic_risk_authority_brief_dict()

    assert calls == ["expected_section"]
    assert expected["sections"][0] is source_expected
    assert expected["sections"][0] == _EXPECTED_SECTION_DICT
    assert expected["limitations"] == source_expected["limitations"]
    assert expected["limitations"] is not source_expected["limitations"]
    assert expected["non_claims"] == source_expected["non_claims"]
    assert expected["non_claims"] is not source_expected["non_claims"]


def test_fixture_contains_phase_174_section_payload_exactly() -> None:
    brief = build_synthetic_risk_authority_brief()
    section = brief.sections[0]
    payload = brief.to_dict()

    assert section.to_dict() == expected_synthetic_risk_authority_brief_section_dict()
    assert payload["sections"][0] == expected_synthetic_risk_authority_brief_section_dict()
    assert payload["sections"][0] == _EXPECTED_SECTION_DICT


def test_fixture_output_matches_expected_dictionary_exactly() -> None:
    brief = build_synthetic_risk_authority_brief()
    payload = brief.to_dict()
    expected = expected_synthetic_risk_authority_brief_dict()

    assert expected == _EXPECTED_DICT
    assert payload == expected
    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert payload["sections"][0] == _EXPECTED_SECTION_DICT
    _assert_primitive_only(payload)
    _assert_primitive_only(expected)


def test_fixed_advisory_metadata_is_pinned() -> None:
    brief = build_synthetic_risk_authority_brief()
    payload = brief.to_dict()

    assert brief.brief_type == "risk_authority_brief"
    assert brief.status == "candidate_only"
    assert brief.authority == "advisory_only"
    assert brief.capital_authority is False
    assert payload["brief_type"] == "risk_authority_brief"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False


def test_title_and_summary_are_pinned_and_non_actionable() -> None:
    brief = build_synthetic_risk_authority_brief()

    assert brief.title == _EXPECTED_DICT["title"]
    assert brief.summary == _EXPECTED_DICT["summary"]
    assert brief.to_dict()["title"] == _EXPECTED_DICT["title"]
    assert brief.to_dict()["summary"] == _EXPECTED_DICT["summary"]

    for text in (brief.title, brief.summary):
        lowered = text.lower()
        for token in _FORBIDDEN_TEXT_TOKENS:
            assert token not in lowered


def test_repeated_fixture_construction_is_dict_and_byte_deterministic() -> None:
    first = build_synthetic_risk_authority_brief()
    second = build_synthetic_risk_authority_brief()
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_expected = expected_synthetic_risk_authority_brief_dict()
    second_expected = expected_synthetic_risk_authority_brief_dict()
    first_json_bytes = _compact_json_bytes(first_payload)
    second_json_bytes = _compact_json_bytes(second_payload)

    assert first is not second
    assert first.sections[0] is not second.sections[0]
    assert first_payload == second_payload == first_expected == second_expected
    assert first_payload == _EXPECTED_DICT
    assert first_json_bytes == second_json_bytes == _EXPECTED_COMPACT_JSON_BYTES
    assert json.loads(first_json_bytes.decode("ascii")) == first_payload


def test_tuple_storage_and_list_serialization_are_pinned() -> None:
    brief = build_synthetic_risk_authority_brief()
    section = brief.sections[0]
    payload = brief.to_dict()

    assert isinstance(brief.sections, tuple)
    assert brief.sections == (section,)
    assert isinstance(payload["sections"], list)
    assert payload["sections"] == [section.to_dict()]

    for field_name in _TUPLE_FIELDS:
        brief_value = getattr(brief, field_name)
        section_value = getattr(section, field_name)
        serialized = payload[field_name]
        nested_serialized = payload["sections"][0][field_name]

        assert isinstance(brief_value, tuple)
        assert isinstance(section_value, tuple)
        assert isinstance(serialized, list)
        assert isinstance(nested_serialized, list)
        assert brief_value == section_value
        assert serialized == nested_serialized == list(section_value)
        assert serialized is not nested_serialized

    payload["sections"].append(section.to_dict())
    payload["limitations"].append("mutated primitive copy")
    payload["sections"][0]["limitations"].append("mutated nested primitive copy")

    assert brief.to_dict() == _EXPECTED_DICT


def test_non_claims_and_limitations_are_present_and_carried_forward() -> None:
    brief = build_synthetic_risk_authority_brief()
    section = brief.sections[0]
    payload = brief.to_dict()

    assert brief.limitations == section.limitations
    assert brief.non_claims == section.non_claims
    assert payload["limitations"] == payload["sections"][0]["limitations"]
    assert payload["non_claims"] == payload["sections"][0]["non_claims"]
    assert set(_REQUIRED_NON_CLAIMS).issubset(brief.non_claims)
    assert set(_ADDITIONAL_NON_CLAIMS).issubset(brief.non_claims)
    assert all(value.startswith("not ") for value in brief.non_claims)
    assert "synthetic metadata only" in brief.limitations
    assert (
        "no approval, readiness, recommendation, allocation, order placement, "
        "broker access, portfolio mutation, capital authority, or trading "
        "authority is represented"
    ) in brief.limitations


def test_expected_helper_returns_fresh_primitive_lists() -> None:
    first = expected_synthetic_risk_authority_brief_dict()
    second = expected_synthetic_risk_authority_brief_dict()

    assert first is not second
    assert first["sections"] is not second["sections"]
    assert first["sections"][0] is not second["sections"][0]
    for field_name in _TUPLE_FIELDS:
        assert first[field_name] is not second[field_name]
        assert (
            first["sections"][0][field_name]
            is not second["sections"][0][field_name]
        )
        assert first[field_name] is not first["sections"][0][field_name]

    first["limitations"].append("mutated primitive copy")
    first["sections"][0]["limitations"].append("mutated nested primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _EXPECTED_DICT
    assert expected_synthetic_risk_authority_brief_dict() == _EXPECTED_DICT


def test_fixture_helpers_do_not_mutate_source_or_share_mutable_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_section = build_synthetic_risk_authority_brief_section()
    source_before = source_section.to_dict()

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_risk_authority_brief_section",
        lambda: source_section,
    )

    brief = fixture_module.build_synthetic_risk_authority_brief()
    payload = brief.to_dict()
    first_expected = expected_synthetic_risk_authority_brief_dict()
    second_expected = expected_synthetic_risk_authority_brief_dict()

    assert first_expected["sections"] is not second_expected["sections"]
    assert first_expected["sections"][0] is not second_expected["sections"][0]
    for field_name in _TUPLE_FIELDS:
        assert first_expected[field_name] is not second_expected[field_name]
        assert (
            first_expected["sections"][0][field_name]
            is not second_expected["sections"][0][field_name]
        )
        assert first_expected[field_name] is not first_expected["sections"][0][field_name]

    payload["sections"][0]["items"][0]["source_status"]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")
    first_expected["sections"][0]["limitations"].append("mutated expected copy")
    first_expected["limitations"].append("mutated expected copy")
    first_expected["non_claims"].append("not mutated expected copy")

    assert brief.sections[0] is source_section
    assert source_section.to_dict() == source_before == _EXPECTED_SECTION_DICT
    assert brief.to_dict() == _EXPECTED_DICT
    assert second_expected == _EXPECTED_DICT
    assert expected_synthetic_risk_authority_brief_dict() == _EXPECTED_DICT


def test_fixture_exposes_no_forbidden_authority_payload_or_object_fields() -> None:
    brief = build_synthetic_risk_authority_brief()
    section = brief.sections[0]
    payload = brief.to_dict()

    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _ast_dict_string_keys().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _call_keyword_names().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert all(
        not hasattr(brief, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert all(
        not hasattr(section, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert brief.status == "candidate_only"
    assert brief.capital_authority is False
    assert section.status == "candidate_only"
    assert section.capital_authority is False


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


def test_fixture_literals_do_not_add_forbidden_actionable_fields() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
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
        _s("bro", "ker"),
        _s("port", "folio"),
        "trading_authority",
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
