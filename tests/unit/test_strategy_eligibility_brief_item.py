from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.strategy_eligibility_brief_item import (
    StrategyEligibilityBriefItem,
    build_strategy_eligibility_brief_item,
)
from algotrader.research.strategy_eligibility_status import StrategyEligibilityStatus
from tests.fixtures.strategy_eligibility_status import (
    build_synthetic_strategy_eligibility_status,
    expected_synthetic_strategy_eligibility_status_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/strategy_eligibility_brief_item.py")
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
_EXPECTED_SOURCE_STATUS_DICT = {
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
_EXPECTED_DICT = {
    "item_type": "strategy_eligibility_brief_item",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "strategy_id": "synthetic-strategy-eligibility-001",
    "strategy_name": "Synthetic strategy eligibility research fixture",
    "eligibility_state": "research_only",
    "headline": "Advisory eligibility metadata: research_only.",
    "summary": (
        "Candidate metadata records research_only with 2 reason(s), "
        "3 limitation(s), 9 non-claim(s), 2 evidence reference(s), "
        "2 blocker(s), and 2 required next step(s)."
    ),
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
    "source_status": _EXPECTED_SOURCE_STATUS_DICT,
}
_EXPECTED_SOURCE_STATUS_JSON = (
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
_EXPECTED_COMPACT_JSON = (
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
    + _EXPECTED_SOURCE_STATUS_JSON
    + "}"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.strategy_eligibility_status",
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
    "trading_ready",
}
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
    "trading_ready",
}
_FORBIDDEN_LITERAL_SUBSTRINGS = (
    _s("bro", "ker"),
    _s("port", "folio"),
)


def test_valid_construction_from_phase_154_synthetic_fixture() -> None:
    status = build_synthetic_strategy_eligibility_status()
    item = build_strategy_eligibility_brief_item(status)

    assert isinstance(item, StrategyEligibilityBriefItem)
    assert item.source_status is status
    assert item.strategy_id == status.strategy_id
    assert item.strategy_name == status.strategy_name
    assert item.eligibility_state == status.eligibility_state
    assert item.to_dict() == _EXPECTED_DICT
    assert item.to_dict()["source_status"] == expected_synthetic_strategy_eligibility_status_dict()


def test_source_status_object_identity_is_preserved() -> None:
    status = build_synthetic_strategy_eligibility_status()
    item = build_strategy_eligibility_brief_item(status)

    assert item.source_status is status
    assert item.to_dict()["source_status"] == status.to_dict()


def test_fixed_item_metadata_values_are_pinned() -> None:
    item = build_strategy_eligibility_brief_item(
        build_synthetic_strategy_eligibility_status()
    )
    payload = item.to_dict()

    assert item.item_type == "strategy_eligibility_brief_item"
    assert item.status == "candidate_only"
    assert item.authority == "advisory_only"
    assert item.capital_authority is False
    assert payload["item_type"] == "strategy_eligibility_brief_item"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False

    for field_name, value in (
        ("item_type", "strategy_eligibility_brief"),
        ("status", "research_only"),
        ("authority", "capital_authority"),
        ("capital_authority", True),
    ):
        constructor_payload = _valid_constructor_payload()
        constructor_payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            StrategyEligibilityBriefItem(**constructor_payload)


def test_headline_and_summary_are_deterministic_and_advisory_only() -> None:
    first = build_strategy_eligibility_brief_item(
        build_synthetic_strategy_eligibility_status()
    )
    second = build_strategy_eligibility_brief_item(
        build_synthetic_strategy_eligibility_status()
    )

    assert first.headline == second.headline == _EXPECTED_DICT["headline"]
    assert first.summary == second.summary == _EXPECTED_DICT["summary"]
    for text in (first.headline, first.summary):
        lowered = text.lower()
        for token in _FORBIDDEN_TEXT_TOKENS:
            assert token not in lowered


def test_to_dict_exact_output_and_compact_json_are_pinned() -> None:
    item = build_strategy_eligibility_brief_item(
        build_synthetic_strategy_eligibility_status()
    )
    payload = item.to_dict()
    compact_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    assert payload == _EXPECTED_DICT
    assert tuple(payload) == tuple(_EXPECTED_DICT)
    assert compact_json == _EXPECTED_COMPACT_JSON
    assert json.loads(compact_json) == payload
    _assert_primitive_only(payload)

    payload["reasons"].append("mutated primitive copy")
    payload["source_status"]["reasons"].append("mutated nested primitive copy")

    assert item.to_dict() == _EXPECTED_DICT


def test_tuple_and_list_metadata_are_serialized_as_lists() -> None:
    constructor_payload = _valid_constructor_payload()
    for field_name in _TUPLE_FIELDS:
        constructor_payload[field_name] = list(constructor_payload[field_name])

    item = StrategyEligibilityBriefItem(**constructor_payload)
    payload = item.to_dict()

    for field_name in _TUPLE_FIELDS:
        assert isinstance(getattr(item, field_name), tuple)
        assert isinstance(payload[field_name], list)
        assert payload[field_name] == list(getattr(item, field_name))
        assert isinstance(payload["source_status"][field_name], list)


def test_repeated_construction_is_deterministic() -> None:
    status = build_synthetic_strategy_eligibility_status()
    first = build_strategy_eligibility_brief_item(status)
    second = build_strategy_eligibility_brief_item(status)
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_json = json.dumps(first_payload, ensure_ascii=True, separators=(",", ":"))
    second_json = json.dumps(second_payload, ensure_ascii=True, separators=(",", ":"))

    assert first is not second
    assert first.source_status is second.source_status is status
    assert first_payload == second_payload == _EXPECTED_DICT
    assert first_json == second_json == _EXPECTED_COMPACT_JSON


def test_source_status_is_not_mutated() -> None:
    status = build_synthetic_strategy_eligibility_status()
    before = status.to_dict()
    item = build_strategy_eligibility_brief_item(status)
    payload = item.to_dict()

    payload["limitations"].append("mutated primitive copy")
    payload["source_status"]["limitations"].append("mutated nested primitive copy")

    assert status.to_dict() == before == _EXPECTED_SOURCE_STATUS_DICT
    assert item.source_status is status
    assert item.to_dict() == _EXPECTED_DICT


def test_brief_item_is_frozen_slotted_and_has_no_from_dict() -> None:
    item = build_strategy_eligibility_brief_item(
        build_synthetic_strategy_eligibility_status()
    )

    assert hasattr(StrategyEligibilityBriefItem, "__slots__")
    assert not hasattr(item, "__dict__")
    assert not hasattr(StrategyEligibilityBriefItem, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        item.summary = "changed"


def test_invalid_non_strategy_eligibility_status_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="StrategyEligibilityStatus"):
        build_strategy_eligibility_brief_item(object())  # type: ignore[arg-type]

    constructor_payload = _valid_constructor_payload()
    constructor_payload["source_status"] = object()
    with pytest.raises(ValidationError, match="StrategyEligibilityStatus"):
        StrategyEligibilityBriefItem(**constructor_payload)


def test_malformed_status_like_objects_are_rejected() -> None:
    class StatusLike:
        strategy_id = _EXPECTED_DICT["strategy_id"]
        strategy_name = _EXPECTED_DICT["strategy_name"]
        eligibility_state = _EXPECTED_DICT["eligibility_state"]
        reasons = tuple(_EXPECTED_DICT["reasons"])
        evidence_refs = tuple(_EXPECTED_DICT["evidence_refs"])
        blockers = tuple(_EXPECTED_DICT["blockers"])
        required_next_steps = tuple(_EXPECTED_DICT["required_next_steps"])
        limitations = tuple(_EXPECTED_DICT["limitations"])
        non_claims = tuple(_EXPECTED_DICT["non_claims"])

        def to_dict(self) -> dict[str, object]:
            return dict(_EXPECTED_SOURCE_STATUS_DICT)

    with pytest.raises(ValidationError, match="StrategyEligibilityStatus"):
        build_strategy_eligibility_brief_item(StatusLike())  # type: ignore[arg-type]

    constructor_payload = _valid_constructor_payload()
    constructor_payload["source_status"] = StatusLike()
    with pytest.raises(ValidationError, match="StrategyEligibilityStatus"):
        StrategyEligibilityBriefItem(**constructor_payload)


@pytest.mark.parametrize(
    "field_name",
    (
        "strategy_id",
        "strategy_name",
        "eligibility_state",
        "headline",
        "summary",
        "reasons",
        "evidence_refs",
        "blockers",
        "required_next_steps",
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
        StrategyEligibilityBriefItem(**constructor_payload)


def test_non_claims_and_limitations_are_carried_forward() -> None:
    status = build_synthetic_strategy_eligibility_status()
    item = build_strategy_eligibility_brief_item(status)

    assert item.limitations == status.limitations
    assert item.non_claims == status.non_claims
    assert item.to_dict()["limitations"] == _EXPECTED_DICT["limitations"]
    assert item.to_dict()["non_claims"] == _EXPECTED_DICT["non_claims"]
    assert set(_REQUIRED_NON_CLAIMS).issubset(item.non_claims)
    assert set(_ADDITIONAL_NON_CLAIMS).issubset(item.non_claims)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("status", "paper_eligible"),
        ("status", "live_probe_eligible"),
        ("status", "live_authorized"),
        ("status", "trading_ready"),
        ("status", "approved"),
        ("eligibility_state", "paper_eligible"),
        ("eligibility_state", "live_probe_eligible"),
        ("eligibility_state", "live_authorized"),
        ("eligibility_state", "trading_ready"),
        ("eligibility_state", "approved"),
    ),
)
def test_paper_live_approved_and_trading_ready_states_remain_impossible(
    field_name: str,
    value: str,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        StrategyEligibilityBriefItem(**constructor_payload)


def test_no_actionable_trading_authority_fields_are_exposed() -> None:
    item = build_strategy_eligibility_brief_item(
        build_synthetic_strategy_eligibility_status()
    )
    field_names = {field.name for field in fields(StrategyEligibilityBriefItem)}
    payload_keys = _payload_keys(item.to_dict())
    ast_fields = _brief_item_ast_fields()
    ast_dict_keys = _to_dict_string_keys()

    assert tuple(field.name for field in fields(StrategyEligibilityBriefItem)) == (
        "item_type",
        "status",
        "authority",
        "capital_authority",
        "strategy_id",
        "strategy_name",
        "eligibility_state",
        "headline",
        "summary",
        "reasons",
        "evidence_refs",
        "blockers",
        "required_next_steps",
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
    assert all(
        not hasattr(item, field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
    )
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
    ):
        assert token not in lowered_source


def _valid_constructor_payload() -> dict[str, object]:
    source_status = build_synthetic_strategy_eligibility_status()
    return {
        "item_type": "strategy_eligibility_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "strategy_id": source_status.strategy_id,
        "strategy_name": source_status.strategy_name,
        "eligibility_state": source_status.eligibility_state,
        "headline": _EXPECTED_DICT["headline"],
        "summary": _EXPECTED_DICT["summary"],
        "reasons": source_status.reasons,
        "evidence_refs": source_status.evidence_refs,
        "blockers": source_status.blockers,
        "required_next_steps": source_status.required_next_steps,
        "limitations": source_status.limitations,
        "non_claims": source_status.non_claims,
        "source_status": source_status,
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
        if isinstance(node, ast.ClassDef) and node.name == "StrategyEligibilityBriefItem":
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("StrategyEligibilityBriefItem class was not found.")


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
