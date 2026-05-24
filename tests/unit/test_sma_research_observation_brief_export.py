from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import inspect
import json

import pytest

from algotrader.errors import ValidationError
from algotrader.research import (
    sma_research_observation_brief_export as export_module,
)
from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
)
from algotrader.research.sma_research_observation_brief_export import (
    SmaResearchObservationBriefExport,
    export_sma_research_observation_brief,
)
from algotrader.research.sma_research_observation_brief_renderer import (
    render_sma_research_observation_brief_text,
)
from tests.fixtures.sma_research_observation_brief_container import (
    build_synthetic_sma_research_observation_brief,
    expected_synthetic_sma_research_observation_brief_dict,
)


def _join(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_PAYLOAD = expected_synthetic_sma_research_observation_brief_dict()
_EXPECTED_JSON_TEXT = json.dumps(
    _EXPECTED_PAYLOAD,
    sort_keys=True,
    separators=(",", ":"),
)
_EXPECTED_RENDERED_TEXT = render_sma_research_observation_brief_text(
    build_synthetic_sma_research_observation_brief()
)
_EXPECTED_FIELD_NAMES = ("payload", "json_text", "rendered_text")
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "json",
    "algotrader.errors",
    "algotrader.research.sma_research_observation_brief_container",
    "algotrader.research.sma_research_observation_brief_renderer",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "argparse",
    _join("algotrader.", "back", "test"),
    _join("algotrader.", "back", "testing"),
    _join("algotrader.", "bro", "ker"),
    _join("algotrader.", "bro", "kers"),
    "algotrader.cli",
    _join("algotrader.", "dash", "board"),
    _join("algotrader.", "data", "base"),
    "algotrader.execution",
    _join("algotrader.", "l", "lm"),
    _join("algotrader.", "l", "lms"),
    _join("algotrader.", "m", "l"),
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
    "click",
    _join("cre", "dential"),
    _join("data", "base"),
    "duckdb",
    _join("ht", "tp"),
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
    _join("path", "lib"),
    _join("poly", "gon"),
    _join("quant", "connect"),
    _join("re", "quests"),
    _join("sche", "dule"),
    _join("sk", "learn"),
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
    "build_parser",
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
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    _join("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "main",
    "mkdir",
    _join("op", "en"),
    "os.environ.get",
    "os.getenv",
    "parse_args",
    "post",
    "print",
    _join("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _join("re", "quest"),
    _join("re", "quests.get"),
    "rglob",
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
_FORBIDDEN_SOURCE_TERMS = (
    _join("acc", "ount"),
    _join("acc", "ounts"),
    _join("ag", "ent"),
    _join("allo", "cation"),
    _join("app", "roval"),
    _join("app", "roved"),
    _join("back", "testing"),
    _join("bro", "ker"),
    _join("cre", "dential"),
    _join("dash", "board"),
    _join("data source app", "roval"),
    _join("exe", "cution read", "iness"),
    _join("fi", "ll"),
    _join("fi", "lls"),
    _join("li", "ve"),
    _join("live_", "authorized"),
    _join("live_", "probe_eligible"),
    _join("l", "lm"),
    _join("m", "l"),
    _join("methodology app", "roval"),
    _join("n", "et", "work"),
    _join("note", "book"),
    _join("or", "der"),
    _join("or", "ders"),
    _join("pa", "per"),
    _join("paper_", "eligible"),
    _join("port", "folio"),
    _join("port", "folio mutation"),
    _join("ran", "king"),
    _join("read", "iness"),
    _join("recomm", "endation"),
    _join("risk app", "roval"),
    _join("run", "time"),
    _join("sche", "duler"),
    _join("sco", "ring"),
    _join("sig", "nal"),
    _join("so", "cket"),
    _join("strategy exe", "cution"),
    _join("tra", "ding authority"),
    _join("tra", "ding_ready"),
    _join("tra", "ding-ready"),
    _join("tra", "ding_authority"),
    _join("ven", "dor"),
)
_FORBIDDEN_PUBLIC_CONCEPTS = {
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
_AUTHORITY_LANGUAGE_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    "evaluator",
    "ranking",
    "scoring",
    "paper",
    "live",
    "readiness",
    "actionable",
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    "account",
    _join("port", "folio"),
    "capital authority",
    "trading authority",
    "trading ready",
    "trading-ready",
    "trading_ready",
)
_NEGATIVE_TEXT_PREFIXES = (
    "not ",
    "no ",
    "does not ",
    "do not ",
    "without ",
    "non-",
)


def test_export_builder_accepts_phase_202_fixture_and_matches_views() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    before_payload = brief.to_dict()
    before_identities = _identity_snapshot(brief)

    exported = export_sma_research_observation_brief(brief)

    assert type(brief) is SmaResearchObservationBrief
    assert type(exported) is SmaResearchObservationBriefExport
    assert exported.payload == brief.to_dict() == before_payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.json_text == json.dumps(
        exported.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json.loads(exported.json_text) == exported.payload
    assert exported.rendered_text == _EXPECTED_RENDERED_TEXT
    assert exported.rendered_text == render_sma_research_observation_brief_text(brief)
    assert brief.to_dict() == before_payload
    assert _identity_snapshot(brief) == before_identities


def test_json_text_is_compact_deterministic_and_round_trips_to_payload() -> None:
    exported = export_sma_research_observation_brief(
        build_synthetic_sma_research_observation_brief()
    )

    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.json_text != json.dumps(exported.payload, sort_keys=True)
    assert exported.json_text.startswith('{"authority":"advisory_only"')
    assert json.loads(exported.json_text) == exported.payload


def test_rendered_text_matches_phase_203_renderer_output() -> None:
    brief = build_synthetic_sma_research_observation_brief()

    exported = export_sma_research_observation_brief(brief)
    rendered = render_sma_research_observation_brief_text(brief)

    assert exported.rendered_text == rendered == _EXPECTED_RENDERED_TEXT
    assert exported.rendered_text.startswith("SMA Research Observation Brief")
    assert tuple(exported.rendered_text.splitlines()) == tuple(rendered.splitlines())


def test_repeated_exports_are_byte_for_byte_deterministic() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    before_payload = brief.to_dict()

    first = export_sma_research_observation_brief(brief)
    second = export_sma_research_observation_brief(brief)
    third = export_sma_research_observation_brief(
        build_synthetic_sma_research_observation_brief()
    )

    assert first == second == third
    assert first.payload == second.payload == third.payload == _EXPECTED_PAYLOAD
    assert first.json_text == second.json_text == third.json_text == _EXPECTED_JSON_TEXT
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert second.json_text.encode("utf-8") == third.json_text.encode("utf-8")
    assert first.rendered_text == second.rendered_text == third.rendered_text
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")
    assert second.rendered_text.encode("utf-8") == third.rendered_text.encode("utf-8")
    assert brief.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_source_brief_to_dict_is_unchanged_before_and_after_export() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    before = brief.to_dict()

    export_sma_research_observation_brief(brief)
    export_sma_research_observation_brief(brief)

    assert brief.to_dict() == before == _EXPECTED_PAYLOAD


def test_section_item_and_source_observation_identities_remain_stable() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    before = _identity_snapshot(brief)

    export_sma_research_observation_brief(brief)
    export_sma_research_observation_brief(brief)

    assert _identity_snapshot(brief) == before


def test_export_payload_access_returns_fresh_primitive_copies() -> None:
    exported = export_sma_research_observation_brief(
        build_synthetic_sma_research_observation_brief()
    )

    first_payload = exported.payload
    second_payload = exported.payload
    _change_payload_copy(first_payload)

    assert first_payload != _EXPECTED_PAYLOAD
    assert second_payload == _EXPECTED_PAYLOAD
    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.payload is not exported.payload
    assert exported.payload is not first_payload
    assert exported.payload is not second_payload
    assert json.loads(exported.json_text) == exported.payload
    assert exported.rendered_text == _EXPECTED_RENDERED_TEXT


def test_direct_construction_validates_copies_and_is_frozen_slotted() -> None:
    payload = _primitive_copy(_EXPECTED_PAYLOAD)
    exported = SmaResearchObservationBriefExport(
        payload=payload,
        json_text=_EXPECTED_JSON_TEXT,
        rendered_text=_EXPECTED_RENDERED_TEXT,
    )

    payload["title"] = "changed primitive constructor input"

    assert tuple(field.name for field in fields(SmaResearchObservationBriefExport)) == (
        _EXPECTED_FIELD_NAMES
    )
    assert hasattr(SmaResearchObservationBriefExport, "__slots__")
    assert not hasattr(exported, "__dict__")
    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.rendered_text == _EXPECTED_RENDERED_TEXT
    with pytest.raises(FrozenInstanceError):
        exported.json_text = "{}"
    with pytest.raises(FrozenInstanceError):
        exported.payload = {}


@pytest.mark.parametrize(
    ("payload", "json_text", "rendered_text", "match"),
    (
        ([], "[]", _EXPECTED_RENDERED_TEXT, "payload"),
        ({}, "{}", _EXPECTED_RENDERED_TEXT, "payload"),
        ({1: "value"}, '{"1":"value"}', _EXPECTED_RENDERED_TEXT, "payload"),
        ({"nested": {"bad": object()}}, "{}", _EXPECTED_RENDERED_TEXT, "primitive"),
        (
            {"nested": ("not", "primitive")},
            '{"nested":["not","primitive"]}',
            _EXPECTED_RENDERED_TEXT,
            "primitive",
        ),
        (_EXPECTED_PAYLOAD, "", _EXPECTED_RENDERED_TEXT, "json_text"),
        (_EXPECTED_PAYLOAD, " {}", _EXPECTED_RENDERED_TEXT, "json_text"),
        (_EXPECTED_PAYLOAD, "not-json", _EXPECTED_RENDERED_TEXT, "json_text"),
        (
            _EXPECTED_PAYLOAD,
            json.dumps(_EXPECTED_PAYLOAD, sort_keys=True),
            _EXPECTED_RENDERED_TEXT,
            "json_text",
        ),
        (_EXPECTED_PAYLOAD, _EXPECTED_JSON_TEXT, "", "rendered_text"),
        (_EXPECTED_PAYLOAD, _EXPECTED_JSON_TEXT, " rendered", "rendered_text"),
        (_EXPECTED_PAYLOAD, _EXPECTED_JSON_TEXT, object(), "rendered_text"),
    ),
    ids=(
        "payload-list",
        "payload-empty",
        "payload-key",
        "payload-object",
        "payload-tuple",
        "json-empty",
        "json-leading-space",
        "json-invalid",
        "json-not-compact",
        "rendered-empty",
        "rendered-leading-space",
        "rendered-object",
    ),
)
def test_direct_construction_rejects_malformed_values(
    payload: object,
    json_text: object,
    rendered_text: object,
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        SmaResearchObservationBriefExport(
            payload=payload,
            json_text=json_text,
            rendered_text=rendered_text,
        )


def test_exact_brief_type_validation_rejects_non_briefs_and_lookalikes() -> None:
    for value in (
        None,
        object(),
        {},
        expected_synthetic_sma_research_observation_brief_dict(),
        _BriefLookalike(),
    ):
        with pytest.raises(ValidationError, match="SmaResearchObservationBrief"):
            export_sma_research_observation_brief(value)


def test_exact_brief_type_validation_rejects_subclasses() -> None:
    brief = _brief_subclass(build_synthetic_sma_research_observation_brief())

    with pytest.raises(ValidationError, match="SmaResearchObservationBrief"):
        export_sma_research_observation_brief(brief)


def test_no_from_dict_exists() -> None:
    exported = export_sma_research_observation_brief(
        build_synthetic_sma_research_observation_brief()
    )

    assert not hasattr(SmaResearchObservationBriefExport, "from_dict")
    assert not hasattr(exported, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()
    assert "from_dict" not in _source_text()


def test_no_forbidden_public_export_concepts_appear() -> None:
    exported = export_sma_research_observation_brief(
        build_synthetic_sma_research_observation_brief()
    )

    assert _export_ast_fields() == {"payload", "json_text", "rendered_text"}
    assert _export_return_keyword_names() == {"payload", "json_text", "rendered_text"}
    assert _export_ast_fields().isdisjoint(_FORBIDDEN_PUBLIC_CONCEPTS)
    assert _export_return_keyword_names().isdisjoint(_FORBIDDEN_PUBLIC_CONCEPTS)
    assert _payload_keys(exported.payload).isdisjoint(_FORBIDDEN_PUBLIC_CONCEPTS)
    assert _rendered_field_names(exported.rendered_text).isdisjoint(
        _FORBIDDEN_PUBLIC_CONCEPTS
    )


def test_no_positive_authority_actionability_or_recommendation_language_appears() -> None:
    exported = export_sma_research_observation_brief(
        build_synthetic_sma_research_observation_brief()
    )
    values = (
        *_string_values(exported.payload),
        *exported.rendered_text.splitlines(),
    )

    for value in values:
        lowered = value.lower()
        if any(token in lowered for token in _AUTHORITY_LANGUAGE_TOKENS):
            assert _is_negative_advisory_text(lowered), value


def test_production_export_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_export_has_no_forbidden_imports_calls_or_terms() -> None:
    imports = _import_references()
    call_names = _call_names()
    lowered_source = _source_text().lower()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert [
        term for term in _FORBIDDEN_SOURCE_TERMS if term in lowered_source
    ] == []


class BriefSubclass(SmaResearchObservationBrief):
    pass


class _BriefLookalike:
    def to_dict(self) -> dict[str, object]:
        return _primitive_copy(_EXPECTED_PAYLOAD)


def _brief_subclass(
    source: SmaResearchObservationBrief,
) -> BriefSubclass:
    return BriefSubclass(
        brief_type=source.brief_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        brief_id=source.brief_id,
        title=source.title,
        summary=source.summary,
        sections=source.sections,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )


def _identity_snapshot(brief: SmaResearchObservationBrief) -> tuple[int, ...]:
    section = brief.sections[0]
    first_item = section.items[0]
    second_item = section.items[1]
    first_observation = first_item.source_observation
    second_observation = second_item.source_observation

    return (
        id(brief),
        id(brief.sections),
        id(section),
        id(section.items),
        id(first_item),
        id(second_item),
        id(first_item.limitations),
        id(first_item.non_claims),
        id(second_item.limitations),
        id(second_item.non_claims),
        id(first_observation),
        id(first_observation.limitations),
        id(first_observation.non_claims),
        id(second_observation),
        id(second_observation.limitations),
        id(second_observation.non_claims),
        id(section.limitations),
        id(section.non_claims),
        id(brief.limitations),
        id(brief.non_claims),
    )


def _change_payload_copy(payload: dict[str, object]) -> None:
    section = _dict(_list(payload["sections"])[0])
    item = _dict(_list(section["items"])[0])
    observation = _dict(item["source_observation"])

    payload["title"] = "changed primitive export payload copy"
    _list(payload["limitations"]).append("changed primitive export payload copy")
    section["title"] = "changed primitive section payload copy"
    item["headline"] = "changed primitive item payload copy"
    observation["symbol"] = "CHANGED_SYNTH"


def _primitive_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _primitive_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_primitive_copy(item) for item in value]
    return value


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


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


def _rendered_field_names(text: str) -> set[str]:
    field_names: set[str] = set()
    for line in text.splitlines():
        if line.startswith("- ") or ":" not in line:
            continue
        field_names.add(line.split(":", maxsplit=1)[0])

    return field_names


def _string_values(value: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, str):
        values.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            values.extend(_string_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_string_values(item))

    return tuple(values)


def _is_negative_advisory_text(value: str) -> bool:
    text = value[2:] if value.startswith("- ") else value
    return (
        text.startswith(_NEGATIVE_TEXT_PREFIXES)
        or " not " in text
        or " without " in text
        or " no " in text
    )


def _source_text() -> str:
    return inspect.getsource(export_module)


def _tree() -> ast.AST:
    return ast.parse(_source_text())


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

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


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _export_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "SmaResearchObservationBriefExport"
        ):
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("SmaResearchObservationBriefExport was not found.")


def _export_return_keyword_names() -> set[str]:
    keyword_names: set[str] = set()

    for node in ast.walk(_tree()):
        if (
            isinstance(node, ast.Call)
            and _call_name(node.func) == "SmaResearchObservationBriefExport"
        ):
            keyword_names.update(
                keyword.arg for keyword in node.keywords if keyword.arg is not None
            )

    return keyword_names
