from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation_brief import (
    ResearchReturnObservationBriefItem,
)
from algotrader.research.research_return_observation_brief_section import (
    ResearchReturnObservationBriefSection,
    build_research_return_observation_brief_section,
)
from tests.fixtures.research_return_observation_brief import (
    build_synthetic_insufficient_research_return_observation_brief_item,
    build_synthetic_research_return_observation_brief_item,
    expected_synthetic_insufficient_research_return_observation_brief_item_dict,
    expected_synthetic_research_return_observation_brief_item_dict,
)


MODULE_PATH = Path(
    "src/algotrader/research/research_return_observation_brief_section.py"
)


def _join(*parts: str) -> str:
    return "".join(parts)


_SECTION_ID = "research-return-observation-brief-section:synthetic:2026-01-20"
_TITLE = "Synthetic return observation metadata group"
_SUMMARY = (
    "Return observation metadata group contains 2 candidate item(s): "
    "returns_constructed and insufficient_return_history."
)
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.research_return_observation_brief",
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
    _join("action", "ability"),
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


def test_builds_section_from_phase_213_fixtures() -> None:
    primary = build_synthetic_research_return_observation_brief_item()
    insufficient = build_synthetic_insufficient_research_return_observation_brief_item()
    section = _build_section(primary, insufficient)

    assert type(section) is ResearchReturnObservationBriefSection
    assert section.items == (primary, insufficient)
    assert section.to_dict() == _expected_section_dict()


def test_preserves_exact_item_identity_and_order() -> None:
    primary = build_synthetic_research_return_observation_brief_item()
    insufficient = build_synthetic_insufficient_research_return_observation_brief_item()
    section = _build_section(primary, insufficient)

    assert section.items[0] is primary
    assert section.items[1] is insufficient
    assert [item["mechanical_state"] for item in section.to_dict()["items"]] == [
        "returns_constructed",
        "insufficient_return_history",
    ]


def test_rejects_empty_item_list() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        build_research_return_observation_brief_section(
            _SECTION_ID,
            _TITLE,
            _SUMMARY,
            (),
        )


def test_rejects_duplicate_item_identities() -> None:
    item = build_synthetic_research_return_observation_brief_item()

    with pytest.raises(ValidationError, match="duplicate item identities"):
        build_research_return_observation_brief_section(
            _SECTION_ID,
            _TITLE,
            _SUMMARY,
            (item, item),
        )


def test_rejects_non_items_lookalikes_and_subclasses() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_research_return_observation_brief_item_dict()

    class ItemSubclass(ResearchReturnObservationBriefItem):
        pass

    source = build_synthetic_research_return_observation_brief_item()
    subclass = ItemSubclass(
        item_type=source.item_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        headline=source.headline,
        summary=source.summary,
        mechanical_state=source.mechanical_state,
        positive_return_count=source.positive_return_count,
        negative_return_count=source.negative_return_count,
        zero_return_count=source.zero_return_count,
        source_observation=source.source_observation,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )

    for bad_item in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="items\\[0\\]"):
            build_research_return_observation_brief_section(
                _SECTION_ID,
                _TITLE,
                _SUMMARY,
                (bad_item,),
            )


def test_requires_non_empty_section_id_title_and_summary() -> None:
    item = build_synthetic_research_return_observation_brief_item()

    for section_id, title, summary in (
        ("", _TITLE, _SUMMARY),
        ("  bad", _TITLE, _SUMMARY),
        (_SECTION_ID, "", _SUMMARY),
        (_SECTION_ID, _join("author", "ity title"), _SUMMARY),
        (_SECTION_ID, _TITLE, ""),
        (_SECTION_ID, _TITLE, _join("action", "ability summary")),
    ):
        with pytest.raises(ValidationError):
            build_research_return_observation_brief_section(
                section_id,
                title,
                summary,
                (item,),
            )


def test_fixed_advisory_metadata_is_pinned() -> None:
    section = _build_default_section()
    payload = section.to_dict()

    assert section.section_type == "research_return_observation_brief_section"
    assert section.status == "candidate_only"
    assert section.authority == "advisory_only"
    assert section.capital_authority is False
    assert payload["section_type"] == "research_return_observation_brief_section"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["section_id"] == _SECTION_ID
    assert payload["title"] == _TITLE
    assert payload["summary"] == _SUMMARY
    assert payload["item_count"] == 2


def test_limitations_and_non_claims_carry_forward_with_first_seen_dedupe() -> None:
    primary = build_synthetic_research_return_observation_brief_item()
    insufficient = build_synthetic_insufficient_research_return_observation_brief_item()
    section = _build_section(primary, insufficient)

    assert section.limitations == primary.limitations
    assert section.non_claims == primary.non_claims
    assert section.to_dict()["limitations"] == list(primary.limitations)
    assert section.to_dict()["non_claims"] == list(primary.non_claims)
    assert "not trading authority" in section.non_claims


def test_direct_construction_rejects_metadata_mismatches() -> None:
    payload = _direct_payload()

    for field_name, value in (
        ("section_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        (
            "limitations",
            ("synthetic broad ETF close series for return mechanics only",),
        ),
        ("non_claims", ("not unrelated",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchReturnObservationBriefSection(**mutated)


def test_rejects_authority_and_actionability_wording_outside_non_claims() -> None:
    payload = _direct_payload()

    for field_name, value in (
        ("section_id", _join("author", "ity-section")),
        ("title", _join("action", "able title")),
        ("summary", _join("app", "roval summary")),
        ("limitations", (_join("capital ", "authority"),)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchReturnObservationBriefSection(**mutated)

    assert "not capital authority" in payload["non_claims"]
    assert "not trading authority" in payload["non_claims"]


def test_to_dict_is_primitive_only_and_deterministic() -> None:
    first = _build_default_section().to_dict()
    second = _build_default_section().to_dict()

    assert first == second == _expected_section_dict()
    assert tuple(first) == tuple(_expected_section_dict())
    assert _primitive_only(first)
    assert first["items"] is not second["items"]
    assert first["items"][0] is not second["items"][0]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["items"][0]["limitations"].append("mutated primitive copy")
    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _expected_section_dict()


def test_repeated_construction_is_byte_for_byte_deterministic_under_compact_json() -> None:
    first = _build_default_section()
    second = _build_default_section()
    first_json = _compact_json_bytes(first)
    second_json = _compact_json_bytes(second)

    assert first == second
    assert first is not second
    assert first_json == second_json
    assert first_json == json.dumps(
        _expected_section_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert json.loads(first_json.decode("utf-8")) == _expected_section_dict()


def test_source_item_to_dict_outputs_are_unchanged() -> None:
    primary = build_synthetic_research_return_observation_brief_item()
    insufficient = build_synthetic_insufficient_research_return_observation_brief_item()
    before = (primary.to_dict(), insufficient.to_dict())
    section = _build_section(primary, insufficient)
    after_build = (primary.to_dict(), insufficient.to_dict())
    payload = section.to_dict()
    after_serialize = (primary.to_dict(), insufficient.to_dict())

    assert before == (
        expected_synthetic_research_return_observation_brief_item_dict(),
        expected_synthetic_insufficient_research_return_observation_brief_item_dict(),
    )
    assert after_build == before
    assert payload["items"] == list(before)
    assert after_serialize == before


def test_object_is_frozen_and_slotted() -> None:
    section = _build_default_section()

    assert hasattr(ResearchReturnObservationBriefSection, "__slots__")
    assert tuple(
        field.name for field in fields(ResearchReturnObservationBriefSection)
    ) == (
        "section_type",
        "status",
        "authority",
        "capital_authority",
        "section_id",
        "title",
        "summary",
        "items",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        section.title = "other"
    with pytest.raises((AttributeError, TypeError)):
        section.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    section = _build_default_section()

    assert not hasattr(ResearchReturnObservationBriefSection, "from_dict")
    assert not hasattr(section, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_public_payload_keys_contain_no_action_or_trading_authority_fields() -> None:
    payload = _build_default_section().to_dict()

    assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))


def test_production_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_module_has_no_forbidden_imports_calls_or_literals() -> None:
    imports = _import_references()
    call_names = _call_names()
    lowered = _source_text().lower()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert [
        token for token in _FORBIDDEN_SOURCE_TOKENS if token in lowered
    ] == []


def _build_default_section() -> ResearchReturnObservationBriefSection:
    return _build_section(
        build_synthetic_research_return_observation_brief_item(),
        build_synthetic_insufficient_research_return_observation_brief_item(),
    )


def _build_section(
    first: ResearchReturnObservationBriefItem,
    second: ResearchReturnObservationBriefItem,
) -> ResearchReturnObservationBriefSection:
    return build_research_return_observation_brief_section(
        _SECTION_ID,
        _TITLE,
        _SUMMARY,
        (first, second),
    )


def _expected_section_dict() -> dict[str, object]:
    first = expected_synthetic_research_return_observation_brief_item_dict()
    second = expected_synthetic_insufficient_research_return_observation_brief_item_dict()
    return {
        "section_type": "research_return_observation_brief_section",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "section_id": _SECTION_ID,
        "title": _TITLE,
        "summary": _SUMMARY,
        "item_count": 2,
        "items": [first, second],
        "limitations": list(first["limitations"]),
        "non_claims": list(first["non_claims"]),
    }


def _direct_payload() -> dict[str, object]:
    section = _build_default_section()
    return {
        "section_type": section.section_type,
        "status": section.status,
        "authority": section.authority,
        "capital_authority": section.capital_authority,
        "section_id": section.section_id,
        "title": section.title,
        "summary": section.summary,
        "items": section.items,
        "limitations": section.limitations,
        "non_claims": section.non_claims,
    }


def _compact_json_bytes(section: ResearchReturnObservationBriefSection) -> bytes:
    return json.dumps(
        section.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

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
