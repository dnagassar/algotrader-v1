from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.risk_authority_status import (
    RISK_AUTHORITY_STATES,
    RiskAuthorityStatus,
    build_risk_authority_status,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/risk_authority_status.py")
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
_EXPECTED_DICT = {
    "authority_type": "risk_authority_status",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "authority_state": "research_only",
    "reasons": ["risk-capital authority has not been granted"],
    "blockers": ["risk approval workflow is not present"],
    "required_next_steps": [
        "document advisory review prerequisites before any authority change"
    ],
    "limitations": ["metadata-only advisory risk authority status"],
    "non_claims": [*_REQUIRED_NON_CLAIMS],
    "evidence_refs": ["advisory-operating-brief-foundation"],
    "related_strategy_ids": ["strategy-candidate-001"],
}
_EXPECTED_JSON = (
    '{"authority_type":"risk_authority_status","status":"candidate_only",'
    '"authority":"advisory_only","capital_authority":false,'
    '"authority_state":"research_only",'
    '"reasons":["risk-capital authority has not been granted"],'
    '"blockers":["risk approval workflow is not present"],'
    '"required_next_steps":['
    '"document advisory review prerequisites before any authority change"],'
    '"limitations":["metadata-only advisory risk authority status"],'
    '"non_claims":["not risk approval","not allocation authority",'
    '"not order authority","not paper readiness","not live readiness",'
    '"not broker authority","not portfolio mutation authority",'
    '"not capital authority","not trading authority"],'
    '"evidence_refs":["advisory-operating-brief-foundation"],'
    '"related_strategy_ids":["strategy-candidate-001"]}'
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
    _s("mas", "sive"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    _s("poly", "gon"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("sk", "learn"),
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
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
    _s("allo", "cation"),
    _s("allo", "cations"),
    "allocation_ready",
    _s("bro", "ker"),
    "broker_ready",
    "buy",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _s("or", "der"),
    "order_ready",
    _s("or", "ders"),
    "paper_eligible",
    _s("port", "folio"),
    _s("port", "folio_mutation"),
    "portfolio_ready",
    "position_size",
    "sell",
    "target_weight",
    "trading_ready",
}


@pytest.mark.parametrize("state", RISK_AUTHORITY_STATES)
def test_valid_construction_for_allowed_advisory_states(state: str) -> None:
    status = _build_status(authority_state=state)

    assert isinstance(status, RiskAuthorityStatus)
    assert status.authority_state == state
    assert status.to_dict()["authority_state"] == state


def test_fixed_metadata_values_are_pinned() -> None:
    status = _build_status()

    assert status.authority_type == "risk_authority_status"
    assert status.status == "candidate_only"
    assert status.authority == "advisory_only"
    assert status.capital_authority is False
    assert status.to_dict() == _EXPECTED_DICT

    for field_name, value in (
        ("authority_type", "risk_authority"),
        ("status", "approved"),
        ("authority", "capital_authority"),
        ("capital_authority", True),
        ("capital_authority", 0),
    ):
        payload = _valid_constructor_payload()
        payload[field_name] = value
        with pytest.raises(ValidationError, match=field_name):
            RiskAuthorityStatus(**payload)


def test_status_is_frozen_and_slotted() -> None:
    status = _build_status()

    assert hasattr(RiskAuthorityStatus, "__slots__")
    assert not hasattr(status, "__dict__")
    with pytest.raises(FrozenInstanceError):
        status.authority_state = "blocked"


def test_tuple_conversion_copies_inputs_and_does_not_mutate_sources() -> None:
    reasons = ["risk-capital authority has not been granted"]
    blockers = ["risk approval workflow is not present"]
    required_next_steps = [
        "document advisory review prerequisites before any authority change"
    ]
    limitations = ["metadata-only advisory risk authority status"]
    non_claims = [*_REQUIRED_NON_CLAIMS]
    evidence_refs = ["advisory-operating-brief-foundation"]
    related_strategy_ids = ["strategy-candidate-001"]
    source_snapshot = (
        list(reasons),
        list(blockers),
        list(required_next_steps),
        list(limitations),
        list(non_claims),
        list(evidence_refs),
        list(related_strategy_ids),
    )

    status = build_risk_authority_status(
        authority_state="research_only",
        reasons=reasons,
        blockers=blockers,
        required_next_steps=required_next_steps,
        limitations=limitations,
        non_claims=non_claims,
        evidence_refs=evidence_refs,
        related_strategy_ids=related_strategy_ids,
    )

    assert status.reasons == tuple(reasons)
    assert status.blockers == tuple(blockers)
    assert status.required_next_steps == tuple(required_next_steps)
    assert status.limitations == tuple(limitations)
    assert status.non_claims == tuple(non_claims)
    assert status.evidence_refs == tuple(evidence_refs)
    assert status.related_strategy_ids == tuple(related_strategy_ids)
    assert (
        reasons,
        blockers,
        required_next_steps,
        limitations,
        non_claims,
        evidence_refs,
        related_strategy_ids,
    ) == source_snapshot

    reasons.append("source mutated after construction")
    blockers.append("source mutated after construction")
    required_next_steps.append("source mutated after construction")
    limitations.append("source mutated after construction")
    non_claims.append("not source mutation")
    evidence_refs.append("source mutated after construction")
    related_strategy_ids.append("source mutated after construction")

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
    assert isinstance(first.reasons, tuple)
    assert isinstance(first_payload["reasons"], list)
    assert isinstance(first_payload["non_claims"], list)
    _assert_primitive_only(first_payload)
    assert json.loads(json.dumps(first_payload, sort_keys=True)) == first_payload

    first_payload["reasons"].append("mutated primitive copy")
    first_payload["non_claims"].append("not mutated primitive source")
    first_payload["evidence_refs"].append("mutated primitive copy")

    assert first.to_dict() == _EXPECTED_DICT


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("authority_state", ""),
        ("authority_state", " "),
        ("authority_state", " research_only"),
        ("authority_state", "research_only "),
        ("authority_state", True),
        ("reasons", ()),
        ("reasons", "reason"),
        ("reasons", ("valid", "")),
        ("reasons", ("valid", " ")),
        ("reasons", ("valid", " trailing")),
        ("reasons", ("valid", "trailing ")),
        ("reasons", ("valid", True)),
        ("blockers", ()),
        ("blockers", "blocked"),
        ("blockers", ("valid", False)),
        ("required_next_steps", ()),
        ("required_next_steps", {"next step"}),
        ("required_next_steps", ("valid", 1)),
        ("limitations", ()),
        ("limitations", ["valid", object()]),
        ("non_claims", ()),
        ("non_claims", ("not risk approval",)),
        ("non_claims", _REQUIRED_NON_CLAIMS + ("positive claim",)),
        ("evidence_refs", "evidence-ref"),
        ("evidence_refs", {"evidence-ref"}),
        ("evidence_refs", ("valid", False)),
        ("related_strategy_ids", "strategy-candidate-001"),
        ("related_strategy_ids", ("valid", "")),
    ),
)
def test_empty_malformed_strings_and_collections_are_rejected(
    field_name: str,
    value: object,
) -> None:
    payload = _valid_constructor_payload()
    payload[field_name] = value

    with pytest.raises(ValidationError):
        RiskAuthorityStatus(**payload)


@pytest.mark.parametrize(
    "state",
    (
        "candidate_only",
        "unknown",
        "paper_eligible",
        "paper_ready",
        "live_probe_eligible",
        "live_authorized",
        "live_ready",
        "authorized",
        "trading_ready",
        "trade_ready",
        "approved",
        "allocation_ready",
        "allocation_authorized",
        "order_ready",
        "order_capable",
        "broker_ready",
        "portfolio_ready",
        "buy",
        "sell",
        "hold",
        "target_weight",
        "position_size",
        _s("allo", "cation"),
        _s("or", "der"),
        _s("bro", "ker"),
        "account",
        _s("port", "folio"),
        _s("port", "folio_authority"),
        _s("port", "folio_mutation"),
    ),
)
def test_unknown_and_authority_like_states_are_rejected(state: str) -> None:
    with pytest.raises(ValidationError, match="authority_state"):
        _build_status(authority_state=state)


def test_required_non_claims_are_explicit_and_negative() -> None:
    status = _build_status()

    assert set(_REQUIRED_NON_CLAIMS).issubset(status.non_claims)
    assert all(value.startswith("not ") for value in status.non_claims)
    assert "not risk approval" in status.non_claims
    assert _s("not allo", "cation authority") in status.non_claims
    assert _s("not or", "der authority") in status.non_claims
    assert "not paper readiness" in status.non_claims
    assert "not live readiness" in status.non_claims
    assert _s("not bro", "ker authority") in status.non_claims
    assert _s("not port", "folio mutation authority") in status.non_claims
    assert "not capital authority" in status.non_claims
    assert "not trading authority" in status.non_claims


def test_ast_and_literal_guardrails_expose_no_actionable_authority_fields() -> None:
    status = _build_status()
    field_names = {field.name for field in fields(RiskAuthorityStatus)}
    payload_keys = set(status.to_dict())
    ast_fields = _risk_status_ast_fields()
    ast_dict_keys = _to_dict_string_keys()
    exact_source_literals = _source_string_literals()

    assert tuple(field.name for field in fields(RiskAuthorityStatus)) == (
        "authority_type",
        "status",
        "authority",
        "capital_authority",
        "authority_state",
        "reasons",
        "blockers",
        "required_next_steps",
        "limitations",
        "non_claims",
        "evidence_refs",
        "related_strategy_ids",
    )
    assert tuple(status.to_dict()) == tuple(_EXPECTED_DICT)
    assert field_names.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert payload_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_fields.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert ast_dict_keys.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert exact_source_literals.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
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


def _build_status(**overrides: object) -> RiskAuthorityStatus:
    values = {
        "authority_state": "research_only",
        "reasons": ("risk-capital authority has not been granted",),
        "blockers": ("risk approval workflow is not present",),
        "required_next_steps": (
            "document advisory review prerequisites before any authority change",
        ),
        "limitations": ("metadata-only advisory risk authority status",),
        "non_claims": _REQUIRED_NON_CLAIMS,
        "evidence_refs": ("advisory-operating-brief-foundation",),
        "related_strategy_ids": ("strategy-candidate-001",),
    }
    values.update(overrides)
    return build_risk_authority_status(**values)


def _valid_constructor_payload() -> dict[str, object]:
    status = _build_status()
    return {
        "authority_type": status.authority_type,
        "status": status.status,
        "authority": status.authority,
        "capital_authority": status.capital_authority,
        "authority_state": status.authority_state,
        "reasons": status.reasons,
        "blockers": status.blockers,
        "required_next_steps": status.required_next_steps,
        "limitations": status.limitations,
        "non_claims": status.non_claims,
        "evidence_refs": status.evidence_refs,
        "related_strategy_ids": status.related_strategy_ids,
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


def _risk_status_ast_fields() -> set[str]:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.ClassDef) and node.name == "RiskAuthorityStatus":
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
            }

    raise AssertionError("RiskAuthorityStatus class was not found.")


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


def _source_string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and type(node.value) is str
    }
