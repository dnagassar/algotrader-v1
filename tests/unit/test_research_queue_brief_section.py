from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_queue_brief_item import (
    ResearchQueueBriefItem,
    build_research_queue_brief_item,
)
from algotrader.research.research_queue_brief_section import (
    ResearchQueueBriefSection,
    build_research_queue_brief_section,
)
from algotrader.research.research_queue_status import build_research_queue_status


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/research_queue_brief_section.py")
_REQUIRED_NON_CLAIMS = (
    _s("not a recomm", "endation"),
    _s("not allo", "cation authority"),
    _s("not or", "der authority"),
    "not paper readiness",
    "not live readiness",
    _s("not bro", "ker authority"),
    _s("not ac", "count authority"),
    _s("not port", "folio mutation authority"),
    "not capital authority",
    "not trading authority",
)
_EXPECTED_ITEM_DICT = {
    "item_type": "research_queue_brief_item",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "queue_id": "rq-001",
    "title": "Evidence coverage review",
    "research_state": "needs_evidence",
    "priority_bucket": "high",
    "topic": "mean reversion source coverage",
    "headline": "Research queue item rq-001: needs_evidence.",
    "summary": (
        "Research queue metadata records needs_evidence work in the high "
        "priority bucket with 2 blocker(s), 2 required next step(s), "
        "2 evidence gap(s), 2 evidence reference(s), 1 related strategy id(s), "
        "2 limitation(s), and 10 non-claim(s)."
    ),
    "hypothesis": "source coverage may be incomplete for the candidate study",
    "blockers": [
        "source notes are incomplete",
        "comparison window evidence is missing",
    ],
    "required_next_steps": [
        "collect source notes for the study window",
        "document comparison window assumptions",
    ],
    "evidence_gaps": [
        "missing source coverage map",
        "missing comparison window rationale",
    ],
    "related_strategy_ids": ["strategy-candidate-001"],
    "evidence_refs": [
        "phase-182-synthetic-evidence-ref-001",
        "phase-182-synthetic-evidence-ref-002",
    ],
    "limitations": [
        "metadata-only unresolved research work",
        "synthetic advisory queue metadata only",
    ],
    "non_claims": list(_REQUIRED_NON_CLAIMS),
    "source_status": {
        "queue_type": "research_queue_status",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "queue_id": "rq-001",
        "title": "Evidence coverage review",
        "research_state": "needs_evidence",
        "priority_bucket": "high",
        "topic": "mean reversion source coverage",
        "hypothesis": "source coverage may be incomplete for the candidate study",
        "blockers": [
            "source notes are incomplete",
            "comparison window evidence is missing",
        ],
        "required_next_steps": [
            "collect source notes for the study window",
            "document comparison window assumptions",
        ],
        "evidence_gaps": [
            "missing source coverage map",
            "missing comparison window rationale",
        ],
        "related_strategy_ids": ["strategy-candidate-001"],
        "evidence_refs": [
            "phase-182-synthetic-evidence-ref-001",
            "phase-182-synthetic-evidence-ref-002",
        ],
        "limitations": [
            "metadata-only unresolved research work",
            "synthetic advisory queue metadata only",
        ],
        "non_claims": list(_REQUIRED_NON_CLAIMS),
    },
}
_EXPECTED_SECTION_DICT = {
    "section_type": "research_queue_brief_section",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Research queue metadata: needs_evidence",
    "summary": (
        "Research queue section contains 1 candidate metadata item(s) across "
        "1 related strategy id(s), state(s): needs_evidence, priority bucket(s): "
        "high, with 2 limitation(s) and 10 non-claim(s)."
    ),
    "item_count": 1,
    "items": [_EXPECTED_ITEM_DICT],
    "limitations": list(_EXPECTED_ITEM_DICT["limitations"]),
    "non_claims": list(_EXPECTED_ITEM_DICT["non_claims"]),
}
_EXPECTED_COMPACT_JSON = json.dumps(
    _EXPECTED_SECTION_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.research_queue_brief_item",
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
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    _s("quant", "connect"),
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
    "rank",
    "score",
    "sell",
    "target_weight",
    "trading_authority",
    "trading_ready",
}


def test_valid_construction_from_research_queue_item() -> None:
    item = _build_item()
    section = build_research_queue_brief_section([item])

    assert isinstance(section, ResearchQueueBriefSection)
    assert section.items == (item,)
    assert section.items[0] is item
    assert section.to_dict() == _EXPECTED_SECTION_DICT


def test_source_item_object_identity_is_preserved() -> None:
    item = _build_item()
    section = build_research_queue_brief_section((item,))

    assert section.items[0] is item
    assert section.to_dict()["items"][0] == item.to_dict()


def test_item_collections_are_converted_to_immutable_tuples() -> None:
    item = _build_item()
    payload = _valid_constructor_payload(item)
    payload["items"] = [item]
    section = ResearchQueueBriefSection(**payload)

    assert isinstance(section.items, tuple)
    assert section.items == (item,)
    assert section.items[0] is item


def test_item_ordering_is_preserved() -> None:
    first = _build_item()
    second = _second_item()
    section = build_research_queue_brief_section([second, first])
    payload = section.to_dict()

    assert section.items == (second, first)
    assert section.items[0] is second
    assert section.items[1] is first
    assert payload["items"] == [second.to_dict(), first.to_dict()]
    assert section.title == "Research queue metadata: 2 items"
    assert section.summary == (
        "Research queue section contains 2 candidate metadata item(s) across "
        "2 related strategy id(s), state(s): blocked, needs_evidence, "
        "priority bucket(s): low, high, with 3 limitation(s) and "
        "11 non-claim(s)."
    )


def test_duplicate_item_identity_is_rejected() -> None:
    item = _build_item()

    with pytest.raises(ValidationError, match="duplicate item identities"):
        build_research_queue_brief_section([item, item])

    payload = _valid_constructor_payload(item)
    payload["items"] = (item, item)
    with pytest.raises(ValidationError, match="duplicate item identities"):
        ResearchQueueBriefSection(**payload)


def test_empty_item_collection_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        build_research_queue_brief_section([])

    payload = _valid_constructor_payload()
    payload["items"] = ()
    with pytest.raises(ValidationError, match="at least one"):
        ResearchQueueBriefSection(**payload)


def test_non_item_malformed_item_like_and_subclass_instances_are_rejected() -> None:
    class ItemLike:
        section_type = "research_queue_brief_item"
        status = "candidate_only"
        authority = "advisory_only"
        capital_authority = False
        limitations = tuple(_EXPECTED_ITEM_DICT["limitations"])
        non_claims = tuple(_EXPECTED_ITEM_DICT["non_claims"])

        def to_dict(self) -> dict[str, object]:
            return dict(_EXPECTED_ITEM_DICT)

    class DerivedResearchQueueBriefItem(ResearchQueueBriefItem):
        pass

    source = _build_item()
    subclass_item = DerivedResearchQueueBriefItem(
        item_type=source.item_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        queue_id=source.queue_id,
        title=source.title,
        research_state=source.research_state,
        priority_bucket=source.priority_bucket,
        topic=source.topic,
        headline=source.headline,
        summary=source.summary,
        hypothesis=source.hypothesis,
        blockers=source.blockers,
        required_next_steps=source.required_next_steps,
        evidence_gaps=source.evidence_gaps,
        related_strategy_ids=source.related_strategy_ids,
        evidence_refs=source.evidence_refs,
        limitations=source.limitations,
        non_claims=source.non_claims,
        source_status=source.source_status,
    )

    with pytest.raises(ValidationError, match="ResearchQueueBriefItem"):
        build_research_queue_brief_section([object()])  # type: ignore[list-item]

    with pytest.raises(ValidationError, match="ResearchQueueBriefItem"):
        build_research_queue_brief_section([ItemLike()])  # type: ignore[list-item]

    with pytest.raises(ValidationError, match="ResearchQueueBriefItem"):
        build_research_queue_brief_section([subclass_item])

    with pytest.raises(ValidationError, match="iterable"):
        build_research_queue_brief_section(object())  # type: ignore[arg-type]


def test_fixed_section_metadata_values_are_pinned() -> None:
    item = _build_item()
    section = build_research_queue_brief_section([item])
    payload = section.to_dict()

    assert section.section_type == "research_queue_brief_section"
    assert section.status == "candidate_only"
    assert section.authority == "advisory_only"
    assert section.capital_authority is False
    assert payload["section_type"] == "research_queue_brief_section"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False

    for field_name, value in (
        ("section_type", "research_queue_brief"),
        ("status", "approved"),
        ("authority", "capital_authority"),
        ("capital_authority", True),
    ):
        constructor_payload = _valid_constructor_payload(item)
        constructor_payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            ResearchQueueBriefSection(**constructor_payload)


def test_to_dict_exact_output_and_compact_json_are_pinned() -> None:
    section = build_research_queue_brief_section([_build_item()])
    payload = section.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_SECTION_DICT
    assert tuple(payload) == tuple(_EXPECTED_SECTION_DICT)
    assert compact_json == _EXPECTED_COMPACT_JSON
    assert json.loads(compact_json) == payload
    _assert_primitive_only(payload)

    payload["items"][0]["limitations"].append("mutated primitive copy")
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive copy")

    assert section.to_dict() == _EXPECTED_SECTION_DICT


def test_repeated_construction_is_deterministic() -> None:
    item = _build_item()
    first = build_research_queue_brief_section([item])
    second = build_research_queue_brief_section([item])

    assert first is not second
    assert first.items == second.items == (item,)
    assert first.items[0] is second.items[0] is item
    assert first.to_dict() == second.to_dict() == _EXPECTED_SECTION_DICT


def test_source_item_is_not_mutated() -> None:
    item = _build_item()
    before = item.to_dict()
    section = build_research_queue_brief_section([item])
    payload = section.to_dict()

    payload["items"][0]["source_status"]["non_claims"].append(
        "not mutated primitive copy"
    )
    payload["limitations"].append("mutated primitive copy")

    assert item.to_dict() == before == _EXPECTED_ITEM_DICT
    assert section.items[0] is item
    assert section.to_dict() == _EXPECTED_SECTION_DICT


@pytest.mark.parametrize(
    "field_name",
    (
        "title",
        "summary",
        "limitations",
        "non_claims",
    ),
)
def test_direct_constructor_rejects_metadata_that_does_not_match_items(
    field_name: str,
) -> None:
    constructor_payload = _valid_constructor_payload()
    original = constructor_payload[field_name]
    constructor_payload[field_name] = (
        ("different",) if isinstance(original, tuple) else "different"
    )

    with pytest.raises(ValidationError, match=field_name):
        ResearchQueueBriefSection(**constructor_payload)


def test_non_claims_and_limitations_are_carried_forward_with_dedupe() -> None:
    first = _build_item()
    second = _second_item()
    section = build_research_queue_brief_section([first, second])

    assert section.limitations == (
        "metadata-only unresolved research work",
        "synthetic advisory queue metadata only",
        "secondary unresolved research metadata",
    )
    assert section.non_claims == (
        *_REQUIRED_NON_CLAIMS,
        "not secondary queue claim",
    )


def test_brief_section_is_frozen_slotted_and_has_no_from_dict() -> None:
    section = build_research_queue_brief_section([_build_item()])

    assert hasattr(ResearchQueueBriefSection, "__slots__")
    assert not hasattr(section, "__dict__")
    assert not hasattr(ResearchQueueBriefSection, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        section.summary = "changed"


def test_no_actionable_trading_authority_fields_are_exposed() -> None:
    section = build_research_queue_brief_section([_build_item()])
    field_names = {field.name for field in fields(ResearchQueueBriefSection)}
    payload_keys = _payload_keys(section.to_dict())
    ast_fields = _brief_section_ast_fields()
    ast_dict_keys = _to_dict_string_keys()

    assert tuple(field.name for field in fields(ResearchQueueBriefSection)) == (
        "section_type",
        "status",
        "authority",
        "capital_authority",
        "title",
        "summary",
        "items",
        "limitations",
        "non_claims",
    )
    assert tuple(section.to_dict()) == tuple(_EXPECTED_SECTION_DICT)
    assert field_names.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_fields.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_dict_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert (payload_keys - set(_EXPECTED_ITEM_DICT)).isdisjoint(
        _FORBIDDEN_AUTHORITY_FIELDS
    )
    assert section.status == "candidate_only"
    assert section.capital_authority is False


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


def _build_item() -> ResearchQueueBriefItem:
    status = build_research_queue_status(
        queue_id="rq-001",
        title="Evidence coverage review",
        research_state="needs_evidence",
        priority_bucket="high",
        topic="mean reversion source coverage",
        hypothesis="source coverage may be incomplete for the candidate study",
        blockers=(
            "source notes are incomplete",
            "comparison window evidence is missing",
        ),
        required_next_steps=(
            "collect source notes for the study window",
            "document comparison window assumptions",
        ),
        evidence_gaps=(
            "missing source coverage map",
            "missing comparison window rationale",
        ),
        related_strategy_ids=("strategy-candidate-001",),
        evidence_refs=(
            "phase-182-synthetic-evidence-ref-001",
            "phase-182-synthetic-evidence-ref-002",
        ),
        limitations=(
            "metadata-only unresolved research work",
            "synthetic advisory queue metadata only",
        ),
        non_claims=_REQUIRED_NON_CLAIMS,
    )
    return build_research_queue_brief_item(status)


def _second_item() -> ResearchQueueBriefItem:
    status = build_research_queue_status(
        queue_id="rq-002",
        title="Secondary source review",
        research_state="blocked",
        priority_bucket="low",
        topic="secondary evidence review",
        hypothesis="secondary evidence may need a separate source pass",
        blockers=("secondary source notes are missing",),
        required_next_steps=("collect secondary source notes",),
        evidence_gaps=("missing secondary evidence summary",),
        related_strategy_ids=("strategy-candidate-002",),
        evidence_refs=("phase-182-secondary-evidence-ref-001",),
        limitations=(
            "metadata-only unresolved research work",
            "secondary unresolved research metadata",
        ),
        non_claims=(*_REQUIRED_NON_CLAIMS, "not secondary queue claim"),
    )
    return build_research_queue_brief_item(status)


def _valid_constructor_payload(
    item: ResearchQueueBriefItem | None = None,
) -> dict[str, object]:
    source_item = item or _build_item()
    return {
        "section_type": "research_queue_brief_section",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "title": _EXPECTED_SECTION_DICT["title"],
        "summary": _EXPECTED_SECTION_DICT["summary"],
        "items": (source_item,),
        "limitations": source_item.limitations,
        "non_claims": source_item.non_claims,
    }


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


def _brief_section_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.ClassDef) and node.name == "ResearchQueueBriefSection":
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("ResearchQueueBriefSection class was not found.")


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
