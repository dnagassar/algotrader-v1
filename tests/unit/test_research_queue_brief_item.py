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
from algotrader.research.research_queue_status import (
    ResearchQueueStatus,
    build_research_queue_status,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/research_queue_brief_item.py")
_TUPLE_FIELDS = (
    "blockers",
    "required_next_steps",
    "evidence_gaps",
    "related_strategy_ids",
    "evidence_refs",
    "limitations",
    "non_claims",
)
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
_EXPECTED_SOURCE_STATUS_DICT = {
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
}
_EXPECTED_DICT = {
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
    "source_status": _EXPECTED_SOURCE_STATUS_DICT,
}
_EXPECTED_COMPACT_JSON = json.dumps(
    _EXPECTED_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.research_queue_status",
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


def test_valid_construction_from_research_queue_status() -> None:
    status = _build_status()
    item = build_research_queue_brief_item(status)

    assert isinstance(item, ResearchQueueBriefItem)
    assert item.source_status is status
    assert item.queue_id == status.queue_id
    assert item.to_dict() == _EXPECTED_DICT
    assert item.to_dict()["source_status"] == status.to_dict()


def test_source_status_object_identity_is_preserved() -> None:
    status = _build_status()
    item = build_research_queue_brief_item(status)

    assert item.source_status is status
    assert item.to_dict()["source_status"] == _EXPECTED_SOURCE_STATUS_DICT


def test_fixed_item_metadata_values_are_pinned() -> None:
    item = build_research_queue_brief_item(_build_status())
    payload = item.to_dict()

    assert item.item_type == "research_queue_brief_item"
    assert item.status == "candidate_only"
    assert item.authority == "advisory_only"
    assert item.capital_authority is False
    assert payload["item_type"] == "research_queue_brief_item"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False

    for field_name, value in (
        ("item_type", "research_queue_brief"),
        ("status", "approved"),
        ("authority", "capital_authority"),
        ("capital_authority", True),
    ):
        constructor_payload = _valid_constructor_payload()
        constructor_payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            ResearchQueueBriefItem(**constructor_payload)


def test_headline_and_summary_are_deterministic_from_source_metadata() -> None:
    first = build_research_queue_brief_item(_build_status())
    second = build_research_queue_brief_item(_build_status())

    assert first.headline == second.headline == _EXPECTED_DICT["headline"]
    assert first.summary == second.summary == _EXPECTED_DICT["summary"]


def test_to_dict_exact_output_and_compact_json_are_pinned() -> None:
    item = build_research_queue_brief_item(_build_status())
    payload = item.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_DICT
    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert compact_json == _EXPECTED_COMPACT_JSON
    assert json.loads(compact_json) == payload
    _assert_primitive_only(payload)

    payload["blockers"].append("mutated primitive copy")
    payload["source_status"]["blockers"].append("mutated nested primitive copy")

    assert item.to_dict() == _EXPECTED_DICT


def test_tuple_and_list_metadata_are_serialized_as_lists() -> None:
    constructor_payload = _valid_constructor_payload()
    for field_name in _TUPLE_FIELDS:
        constructor_payload[field_name] = list(constructor_payload[field_name])

    item = ResearchQueueBriefItem(**constructor_payload)
    payload = item.to_dict()

    for field_name in _TUPLE_FIELDS:
        assert isinstance(getattr(item, field_name), tuple)
        assert isinstance(payload[field_name], list)
        assert payload[field_name] == list(getattr(item, field_name))
        assert isinstance(payload["source_status"][field_name], list)


def test_repeated_construction_is_deterministic() -> None:
    status = _build_status()
    first = build_research_queue_brief_item(status)
    second = build_research_queue_brief_item(status)

    assert first is not second
    assert first.source_status is second.source_status is status
    assert first.to_dict() == second.to_dict() == _EXPECTED_DICT


def test_source_status_is_not_mutated() -> None:
    status = _build_status()
    before = status.to_dict()
    item = build_research_queue_brief_item(status)
    payload = item.to_dict()

    payload["limitations"].append("mutated primitive copy")
    payload["source_status"]["limitations"].append("mutated nested primitive copy")

    assert status.to_dict() == before == _EXPECTED_SOURCE_STATUS_DICT
    assert item.source_status is status
    assert item.to_dict() == _EXPECTED_DICT


def test_brief_item_is_frozen_slotted_and_has_no_from_dict() -> None:
    item = build_research_queue_brief_item(_build_status())

    assert hasattr(ResearchQueueBriefItem, "__slots__")
    assert not hasattr(item, "__dict__")
    assert not hasattr(ResearchQueueBriefItem, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        item.summary = "changed"


def test_invalid_non_research_queue_status_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ResearchQueueStatus"):
        build_research_queue_brief_item(object())  # type: ignore[arg-type]

    constructor_payload = _valid_constructor_payload()
    constructor_payload["source_status"] = object()
    with pytest.raises(ValidationError, match="ResearchQueueStatus"):
        ResearchQueueBriefItem(**constructor_payload)


def test_malformed_status_like_objects_and_subclasses_are_rejected() -> None:
    class StatusLike:
        queue_id = _EXPECTED_DICT["queue_id"]
        title = _EXPECTED_DICT["title"]
        research_state = _EXPECTED_DICT["research_state"]
        priority_bucket = _EXPECTED_DICT["priority_bucket"]
        topic = _EXPECTED_DICT["topic"]
        hypothesis = _EXPECTED_DICT["hypothesis"]
        blockers = tuple(_EXPECTED_DICT["blockers"])
        required_next_steps = tuple(_EXPECTED_DICT["required_next_steps"])
        evidence_gaps = tuple(_EXPECTED_DICT["evidence_gaps"])
        related_strategy_ids = tuple(_EXPECTED_DICT["related_strategy_ids"])
        evidence_refs = tuple(_EXPECTED_DICT["evidence_refs"])
        limitations = tuple(_EXPECTED_DICT["limitations"])
        non_claims = tuple(_EXPECTED_DICT["non_claims"])

        def to_dict(self) -> dict[str, object]:
            return dict(_EXPECTED_SOURCE_STATUS_DICT)

    class DerivedResearchQueueStatus(ResearchQueueStatus):
        pass

    source = _build_status()
    subclass_status = DerivedResearchQueueStatus(**_status_constructor_payload(source))

    with pytest.raises(ValidationError, match="ResearchQueueStatus"):
        build_research_queue_brief_item(StatusLike())  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="ResearchQueueStatus"):
        build_research_queue_brief_item(subclass_status)


@pytest.mark.parametrize(
    "field_name",
    (
        "queue_id",
        "title",
        "research_state",
        "priority_bucket",
        "topic",
        "headline",
        "summary",
        "hypothesis",
        "blockers",
        "required_next_steps",
        "evidence_gaps",
        "related_strategy_ids",
        "evidence_refs",
        "limitations",
        "non_claims",
    ),
)
def test_direct_constructor_rejects_metadata_that_does_not_match_source(
    field_name: str,
) -> None:
    constructor_payload = _valid_constructor_payload()
    original = constructor_payload[field_name]
    constructor_payload[field_name] = (
        ("different",) if isinstance(original, tuple) else "different"
    )

    with pytest.raises(ValidationError, match=field_name):
        ResearchQueueBriefItem(**constructor_payload)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("status", "paper_eligible"),
        ("status", "live_authorized"),
        ("status", "trading_ready"),
        ("status", "approved"),
        ("title", "paper_eligible"),
        ("summary", "trading_ready"),
    ),
)
def test_paper_live_approved_and_trading_ready_states_remain_impossible(
    field_name: str,
    value: str,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        ResearchQueueBriefItem(**constructor_payload)


def test_non_claims_and_limitations_are_carried_forward() -> None:
    status = _build_status()
    item = build_research_queue_brief_item(status)

    assert item.limitations == status.limitations
    assert item.non_claims == status.non_claims
    assert set(_REQUIRED_NON_CLAIMS).issubset(item.non_claims)


def test_no_actionable_trading_authority_fields_are_exposed() -> None:
    item = build_research_queue_brief_item(_build_status())
    field_names = {field.name for field in fields(ResearchQueueBriefItem)}
    payload_keys = _payload_keys(item.to_dict())
    ast_fields = _brief_item_ast_fields()
    ast_dict_keys = _to_dict_string_keys()

    assert tuple(field.name for field in fields(ResearchQueueBriefItem)) == (
        "item_type",
        "status",
        "authority",
        "capital_authority",
        "queue_id",
        "title",
        "research_state",
        "priority_bucket",
        "topic",
        "headline",
        "summary",
        "hypothesis",
        "blockers",
        "required_next_steps",
        "evidence_gaps",
        "related_strategy_ids",
        "evidence_refs",
        "limitations",
        "non_claims",
        "source_status",
    )
    assert tuple(item.to_dict()) == tuple(_EXPECTED_DICT)
    assert field_names.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_fields.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_dict_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert (
        payload_keys - set(_EXPECTED_SOURCE_STATUS_DICT)
    ).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert item.status == "candidate_only"
    assert item.capital_authority is False


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


def _build_status() -> ResearchQueueStatus:
    return build_research_queue_status(
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


def _valid_constructor_payload() -> dict[str, object]:
    source_status = _build_status()
    return {
        "item_type": "research_queue_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "queue_id": source_status.queue_id,
        "title": source_status.title,
        "research_state": source_status.research_state,
        "priority_bucket": source_status.priority_bucket,
        "topic": source_status.topic,
        "headline": _EXPECTED_DICT["headline"],
        "summary": _EXPECTED_DICT["summary"],
        "hypothesis": source_status.hypothesis,
        "blockers": source_status.blockers,
        "required_next_steps": source_status.required_next_steps,
        "evidence_gaps": source_status.evidence_gaps,
        "related_strategy_ids": source_status.related_strategy_ids,
        "evidence_refs": source_status.evidence_refs,
        "limitations": source_status.limitations,
        "non_claims": source_status.non_claims,
        "source_status": source_status,
    }


def _status_constructor_payload(status: ResearchQueueStatus) -> dict[str, object]:
    return {
        "queue_type": status.queue_type,
        "status": status.status,
        "authority": status.authority,
        "capital_authority": status.capital_authority,
        "queue_id": status.queue_id,
        "title": status.title,
        "research_state": status.research_state,
        "priority_bucket": status.priority_bucket,
        "topic": status.topic,
        "hypothesis": status.hypothesis,
        "blockers": status.blockers,
        "required_next_steps": status.required_next_steps,
        "evidence_gaps": status.evidence_gaps,
        "related_strategy_ids": status.related_strategy_ids,
        "evidence_refs": status.evidence_refs,
        "limitations": status.limitations,
        "non_claims": status.non_claims,
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


def _brief_item_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.ClassDef) and node.name == "ResearchQueueBriefItem":
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("ResearchQueueBriefItem class was not found.")


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
