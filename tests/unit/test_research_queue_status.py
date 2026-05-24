from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_queue_status import (
    RESEARCH_QUEUE_PRIORITY_BUCKETS,
    RESEARCH_QUEUE_STATES,
    ResearchQueueStatus,
    build_research_queue_status,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/research_queue_status.py")
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
_EXPECTED_DICT = {
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
_EXPECTED_JSON = (
    '{"queue_type":"research_queue_status","status":"candidate_only",'
    '"authority":"advisory_only","capital_authority":false,'
    '"queue_id":"rq-001","title":"Evidence coverage review",'
    '"research_state":"needs_evidence","priority_bucket":"high",'
    '"topic":"mean reversion source coverage",'
    '"hypothesis":"source coverage may be incomplete for the candidate study",'
    '"blockers":["source notes are incomplete",'
    '"comparison window evidence is missing"],'
    '"required_next_steps":["collect source notes for the study window",'
    '"document comparison window assumptions"],'
    '"evidence_gaps":["missing source coverage map",'
    '"missing comparison window rationale"],'
    '"related_strategy_ids":["strategy-candidate-001"],'
    '"evidence_refs":["phase-182-synthetic-evidence-ref-001",'
    '"phase-182-synthetic-evidence-ref-002"],'
    '"limitations":["metadata-only unresolved research work",'
    '"synthetic advisory queue metadata only"],'
    '"non_claims":["not a recommendation","not allocation authority",'
    '"not order authority","not paper readiness","not live readiness",'
    '"not broker authority","not account authority",'
    '"not portfolio mutation authority","not capital authority",'
    '"not trading authority"]}'
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
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
    _s("or", "ders"),
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


@pytest.mark.parametrize("research_state", RESEARCH_QUEUE_STATES)
def test_valid_construction_for_allowed_research_states(
    research_state: str,
) -> None:
    status = _build_status(research_state=research_state)

    assert isinstance(status, ResearchQueueStatus)
    assert status.research_state == research_state
    assert status.to_dict()["research_state"] == research_state


@pytest.mark.parametrize("priority_bucket", RESEARCH_QUEUE_PRIORITY_BUCKETS)
def test_valid_construction_for_allowed_priority_buckets(
    priority_bucket: str,
) -> None:
    status = _build_status(priority_bucket=priority_bucket)

    assert status.priority_bucket == priority_bucket
    assert status.to_dict()["priority_bucket"] == priority_bucket


def test_fixed_metadata_values_are_pinned() -> None:
    status = _build_status()

    assert status.queue_type == "research_queue_status"
    assert status.status == "candidate_only"
    assert status.authority == "advisory_only"
    assert status.capital_authority is False
    assert status.to_dict() == _EXPECTED_DICT

    for field_name, value in (
        ("queue_type", "research_queue"),
        ("status", "approved"),
        ("authority", "capital_authority"),
        ("capital_authority", True),
        ("capital_authority", 0),
    ):
        payload = _valid_constructor_payload()
        payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            ResearchQueueStatus(**payload)


def test_status_is_frozen_slotted_and_has_no_from_dict() -> None:
    status = _build_status()

    assert hasattr(ResearchQueueStatus, "__slots__")
    assert not hasattr(status, "__dict__")
    assert not hasattr(ResearchQueueStatus, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        status.title = "changed"


def test_tuple_conversion_copies_inputs_and_does_not_mutate_sources() -> None:
    blockers = [
        "source notes are incomplete",
        "comparison window evidence is missing",
    ]
    required_next_steps = [
        "collect source notes for the study window",
        "document comparison window assumptions",
    ]
    evidence_gaps = [
        "missing source coverage map",
        "missing comparison window rationale",
    ]
    related_strategy_ids = ["strategy-candidate-001"]
    evidence_refs = [
        "phase-182-synthetic-evidence-ref-001",
        "phase-182-synthetic-evidence-ref-002",
    ]
    limitations = [
        "metadata-only unresolved research work",
        "synthetic advisory queue metadata only",
    ]
    non_claims = list(_REQUIRED_NON_CLAIMS)
    source_snapshot = (
        list(blockers),
        list(required_next_steps),
        list(evidence_gaps),
        list(related_strategy_ids),
        list(evidence_refs),
        list(limitations),
        list(non_claims),
    )

    status = build_research_queue_status(
        queue_id="rq-001",
        title="Evidence coverage review",
        research_state="needs_evidence",
        priority_bucket="high",
        topic="mean reversion source coverage",
        hypothesis="source coverage may be incomplete for the candidate study",
        blockers=blockers,
        required_next_steps=required_next_steps,
        evidence_gaps=evidence_gaps,
        related_strategy_ids=related_strategy_ids,
        evidence_refs=evidence_refs,
        limitations=limitations,
        non_claims=non_claims,
    )

    assert status.blockers == tuple(blockers)
    assert status.required_next_steps == tuple(required_next_steps)
    assert status.evidence_gaps == tuple(evidence_gaps)
    assert status.related_strategy_ids == tuple(related_strategy_ids)
    assert status.evidence_refs == tuple(evidence_refs)
    assert status.limitations == tuple(limitations)
    assert status.non_claims == tuple(non_claims)
    assert (
        blockers,
        required_next_steps,
        evidence_gaps,
        related_strategy_ids,
        evidence_refs,
        limitations,
        non_claims,
    ) == source_snapshot

    blockers.append("source mutated after construction")
    required_next_steps.append("source mutated after construction")
    evidence_gaps.append("source mutated after construction")
    related_strategy_ids.append("source mutated after construction")
    evidence_refs.append("source mutated after construction")
    limitations.append("source mutated after construction")
    non_claims.append("not source mutation")

    assert status.to_dict() == _EXPECTED_DICT


def test_to_dict_is_exact_deterministic_primitive_and_list_based() -> None:
    first = _build_status()
    second = _build_status()
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_json = json.dumps(first_payload, separators=(",", ":"))
    second_json = json.dumps(second_payload, separators=(",", ":"))

    assert first_payload == second_payload == _EXPECTED_DICT
    assert first_json == second_json == _EXPECTED_JSON
    assert tuple(first_payload) == tuple(_EXPECTED_DICT)
    assert isinstance(first.blockers, tuple)
    assert isinstance(first_payload["blockers"], list)
    assert isinstance(first_payload["non_claims"], list)
    _assert_primitive_only(first_payload)
    assert json.loads(json.dumps(first_payload, sort_keys=True)) == first_payload

    first_payload["blockers"].append("mutated primitive copy")
    first_payload["non_claims"].append("not mutated primitive source")

    assert first.to_dict() == _EXPECTED_DICT


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("queue_id", ""),
        ("queue_id", " rq-001"),
        ("queue_id", True),
        ("title", " "),
        ("title", "Evidence coverage review "),
        ("research_state", ""),
        ("research_state", "unknown"),
        ("research_state", True),
        ("priority_bucket", ""),
        ("priority_bucket", "urgent"),
        ("priority_bucket", 1),
        ("topic", ""),
        ("hypothesis", " "),
        ("blockers", ()),
        ("blockers", "blocked"),
        ("blockers", ("valid", "")),
        ("blockers", ("valid", " trailing")),
        ("blockers", ("valid", True)),
        ("required_next_steps", ()),
        ("required_next_steps", {"next step"}),
        ("required_next_steps", ("valid", 1)),
        ("evidence_gaps", ()),
        ("evidence_gaps", ["valid", object()]),
        ("related_strategy_ids", "strategy-candidate-001"),
        ("related_strategy_ids", ("valid", "")),
        ("evidence_refs", "evidence-ref"),
        ("evidence_refs", {"evidence-ref"}),
        ("evidence_refs", ("valid", False)),
        ("limitations", ()),
        ("limitations", ("valid", "")),
        ("non_claims", ()),
        ("non_claims", ("not a recommendation",)),
        ("non_claims", _REQUIRED_NON_CLAIMS + ("positive claim",)),
    ),
)
def test_empty_malformed_strings_and_collections_are_rejected(
    field_name: str,
    value: object,
) -> None:
    payload = _valid_constructor_payload()
    payload[field_name] = value

    with pytest.raises(ValidationError):
        ResearchQueueStatus(**payload)


@pytest.mark.parametrize(
    "field_name",
    (
        "queue_id",
        "title",
        "topic",
        "hypothesis",
        "blockers",
        "required_next_steps",
        "evidence_gaps",
        "related_strategy_ids",
        "evidence_refs",
        "limitations",
    ),
)
def test_forbidden_language_is_rejected_in_advisory_metadata(
    field_name: str,
) -> None:
    payload = _valid_constructor_payload()
    forbidden_text = _s("requires bro", "ker review")
    payload[field_name] = (
        (forbidden_text,) if isinstance(payload[field_name], tuple) else forbidden_text
    )

    with pytest.raises(ValidationError, match=field_name):
        ResearchQueueStatus(**payload)


@pytest.mark.parametrize(
    "state",
    (
        "candidate_only",
        "unknown",
        "paper_eligible",
        "paper_ready",
        "live_probe_eligible",
        "live_authorized",
        "authorized",
        "trading_ready",
        "trading-ready",
        "approved",
    ),
)
def test_unknown_and_authority_like_research_states_are_rejected(
    state: str,
) -> None:
    with pytest.raises(ValidationError, match="research_state"):
        _build_status(research_state=state)


@pytest.mark.parametrize(
    "priority_bucket",
    (
        "candidate_only",
        "unknown",
        "approved",
        "authorized",
        "trading_ready",
        "paper_ready",
        "live_ready",
    ),
)
def test_unknown_and_authority_like_priority_buckets_are_rejected(
    priority_bucket: str,
) -> None:
    with pytest.raises(ValidationError, match="priority_bucket"):
        _build_status(priority_bucket=priority_bucket)


def test_required_non_claims_are_explicit_and_negative() -> None:
    status = _build_status()

    assert set(_REQUIRED_NON_CLAIMS).issubset(status.non_claims)
    assert all(value.startswith("not ") for value in status.non_claims)
    for claim in _REQUIRED_NON_CLAIMS:
        assert claim in status.non_claims


def test_ast_guardrails_expose_no_actionable_authority_fields() -> None:
    status = _build_status()
    field_names = {field.name for field in fields(ResearchQueueStatus)}
    payload_keys = set(status.to_dict())
    ast_fields = _status_ast_fields()
    ast_dict_keys = _to_dict_string_keys()

    assert tuple(field.name for field in fields(ResearchQueueStatus)) == (
        "queue_type",
        "status",
        "authority",
        "capital_authority",
        "queue_id",
        "title",
        "research_state",
        "priority_bucket",
        "topic",
        "hypothesis",
        "blockers",
        "required_next_steps",
        "evidence_gaps",
        "related_strategy_ids",
        "evidence_refs",
        "limitations",
        "non_claims",
    )
    assert tuple(status.to_dict()) == tuple(_EXPECTED_DICT)
    assert field_names.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert payload_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_fields.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_dict_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert status.capital_authority is False


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _build_status(**overrides: object) -> ResearchQueueStatus:
    values = {
        "queue_id": "rq-001",
        "title": "Evidence coverage review",
        "research_state": "needs_evidence",
        "priority_bucket": "high",
        "topic": "mean reversion source coverage",
        "hypothesis": "source coverage may be incomplete for the candidate study",
        "blockers": (
            "source notes are incomplete",
            "comparison window evidence is missing",
        ),
        "required_next_steps": (
            "collect source notes for the study window",
            "document comparison window assumptions",
        ),
        "evidence_gaps": (
            "missing source coverage map",
            "missing comparison window rationale",
        ),
        "related_strategy_ids": ("strategy-candidate-001",),
        "evidence_refs": (
            "phase-182-synthetic-evidence-ref-001",
            "phase-182-synthetic-evidence-ref-002",
        ),
        "limitations": (
            "metadata-only unresolved research work",
            "synthetic advisory queue metadata only",
        ),
        "non_claims": _REQUIRED_NON_CLAIMS,
    }
    values.update(overrides)
    return build_research_queue_status(**values)


def _valid_constructor_payload() -> dict[str, object]:
    status = _build_status()
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


def _status_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.ClassDef) and node.name == "ResearchQueueStatus":
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("ResearchQueueStatus class was not found.")


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
