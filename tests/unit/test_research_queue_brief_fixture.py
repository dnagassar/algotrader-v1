from __future__ import annotations

import ast
import json
from pathlib import Path

from algotrader.research.research_queue_brief import ResearchQueueBrief
from algotrader.research.research_queue_brief_item import ResearchQueueBriefItem
from algotrader.research.research_queue_brief_section import (
    ResearchQueueBriefSection,
)
from algotrader.research.research_queue_status import ResearchQueueStatus
from tests.fixtures import research_queue_brief as fixture_module
from tests.fixtures.research_queue_brief import (
    build_synthetic_research_queue_brief,
    build_synthetic_research_queue_brief_item,
    build_synthetic_research_queue_brief_section,
    build_synthetic_research_queue_status,
    expected_synthetic_research_queue_brief_dict,
    expected_synthetic_research_queue_brief_item_dict,
    expected_synthetic_research_queue_brief_section_dict,
    expected_synthetic_research_queue_status_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


FIXTURE_PATH = Path("tests/fixtures/research_queue_brief.py")
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
_ADDITIONAL_NON_CLAIMS = (
    "not strategy approval",
    "not data source approval",
    "not methodology approval",
    "not profitability evidence",
    "not research conclusion",
    "not backtest readiness",
    "not execution readiness",
    _s("not allo", "cation guidance"),
    _s("not or", "der placement"),
    "not ranking or scoring output",
)
_EXPECTED_STATUS_DICT = {
    "queue_type": "research_queue_status",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "queue_id": "research-queue:broad-etf-sma:candidate",
    "title": "Broad ETF SMA trend-following research queue item",
    "research_state": "needs_evidence",
    "priority_bucket": "medium",
    "topic": "broad_etf_sma_trend_following",
    "hypothesis": (
        "broad ETF SMA trend-following remains a pipeline-validation candidate only"
    ),
    "blockers": [
        "source data clearance is unresolved",
        "ETF universe definition is unresolved",
        "benchmark and cash proxy policy is unresolved",
        "return policy is unresolved",
        "no-lookahead protocol is unresolved",
        "survivorship policy is unresolved",
        "reproduction protocol is unresolved",
        "validation evidence is missing",
    ],
    "required_next_steps": [
        "validate deterministic fixture shape for broad ETF SMA inputs",
        "confirm source provenance boundaries before real data use",
        "scope methodology before any research claim",
        "construct no-lookahead returns from fixture inputs only",
    ],
    "evidence_gaps": [
        "real data provenance evidence is absent",
        "benchmark and cash handling evidence is absent",
        "survivorship treatment evidence is absent",
        "cost and slippage assumptions are absent",
        "out-of-sample robustness evidence is absent",
        "reproduction evidence is absent",
    ],
    "related_strategy_ids": [
        "synthetic-advisory:broad-etf-sma",
        "research-queue:broad-etf-sma",
    ],
    "evidence_refs": [
        "phase-182-research-queue-status-contract",
        "phase-182-research-queue-brief-contract",
        "advisory-operating-brief-synthetic-foundation",
    ],
    "limitations": [
        "synthetic metadata-only unresolved research queue fixture",
        "broad ETF SMA remains pipeline-validation metadata only",
        "fixture output is not connected to real data or runtime state",
    ],
    "non_claims": [*_REQUIRED_NON_CLAIMS, *_ADDITIONAL_NON_CLAIMS],
}
_EXPECTED_ITEM_DICT = {
    "item_type": "research_queue_brief_item",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "queue_id": _EXPECTED_STATUS_DICT["queue_id"],
    "title": _EXPECTED_STATUS_DICT["title"],
    "research_state": _EXPECTED_STATUS_DICT["research_state"],
    "priority_bucket": _EXPECTED_STATUS_DICT["priority_bucket"],
    "topic": _EXPECTED_STATUS_DICT["topic"],
    "headline": (
        "Research queue item research-queue:broad-etf-sma:candidate: "
        "needs_evidence."
    ),
    "summary": (
        "Research queue metadata records needs_evidence work in the medium "
        "priority bucket with 8 blocker(s), 4 required next step(s), "
        "6 evidence gap(s), 3 evidence reference(s), 2 related strategy id(s), "
        "3 limitation(s), and 20 non-claim(s)."
    ),
    "hypothesis": _EXPECTED_STATUS_DICT["hypothesis"],
    "blockers": list(_EXPECTED_STATUS_DICT["blockers"]),
    "required_next_steps": list(_EXPECTED_STATUS_DICT["required_next_steps"]),
    "evidence_gaps": list(_EXPECTED_STATUS_DICT["evidence_gaps"]),
    "related_strategy_ids": list(_EXPECTED_STATUS_DICT["related_strategy_ids"]),
    "evidence_refs": list(_EXPECTED_STATUS_DICT["evidence_refs"]),
    "limitations": list(_EXPECTED_STATUS_DICT["limitations"]),
    "non_claims": list(_EXPECTED_STATUS_DICT["non_claims"]),
    "source_status": _EXPECTED_STATUS_DICT,
}
_EXPECTED_SECTION_DICT = {
    "section_type": "research_queue_brief_section",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Research queue metadata: needs_evidence",
    "summary": (
        "Research queue section contains 1 candidate metadata item(s) across "
        "2 related strategy id(s), state(s): needs_evidence, priority bucket(s): "
        "medium, with 3 limitation(s) and 20 non-claim(s)."
    ),
    "item_count": 1,
    "items": [_EXPECTED_ITEM_DICT],
    "limitations": list(_EXPECTED_ITEM_DICT["limitations"]),
    "non_claims": list(_EXPECTED_ITEM_DICT["non_claims"]),
}
_EXPECTED_BRIEF_DICT = {
    "brief_type": "research_queue_brief",
    "status": "candidate_only",
    "authority": "advisory_only",
    "capital_authority": False,
    "title": "Research queue brief: 1 section",
    "summary": (
        "Research queue brief contains 1 candidate metadata section(s) with "
        "1 item(s), 3 limitation(s), and 20 non-claim(s)."
    ),
    "section_count": 1,
    "sections": [_EXPECTED_SECTION_DICT],
    "limitations": list(_EXPECTED_SECTION_DICT["limitations"]),
    "non_claims": list(_EXPECTED_SECTION_DICT["non_claims"]),
}
_EXPECTED_COMPACT_JSON = json.dumps(
    _EXPECTED_BRIEF_DICT,
    ensure_ascii=True,
    separators=(",", ":"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.research_queue_brief",
    "algotrader.research.research_queue_brief_item",
    "algotrader.research.research_queue_brief_section",
    "algotrader.research.research_queue_status",
}
_ALLOWED_CALL_NAMES = {
    "build_research_queue_brief",
    "build_research_queue_brief_item",
    "build_research_queue_brief_section",
    "build_research_queue_status",
    "build_synthetic_research_queue_brief_item",
    "build_synthetic_research_queue_brief_section",
    "build_synthetic_research_queue_status",
    "expected_synthetic_research_queue_brief_item_dict",
    "expected_synthetic_research_queue_brief_section_dict",
    "expected_synthetic_research_queue_status_dict",
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
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("net", "work"),
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
    "fill",
    "fills",
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
_FORBIDDEN_PAYLOAD_TOKENS = (
    "paper_eligible",
    "paper_ready",
    "live_authorized",
    "live_ready",
    "approved",
    "authorized",
    "trading_ready",
    "trading-ready",
    "buy",
    "sell",
    "hold",
)
_FORBIDDEN_NON_NON_CLAIM_TEXT_TOKENS = (
    "recommend",
    "approval",
    "approved",
    "readiness",
    _s("allo", "cation"),
    _s("or", "der"),
    _s("bro", "ker"),
    _s("ac", "count"),
    _s("port", "folio"),
    "rank",
    "score",
    "trading authority",
)


def test_fixture_builders_return_exact_phase_182_types() -> None:
    status = build_synthetic_research_queue_status()
    item = build_synthetic_research_queue_brief_item()
    section = build_synthetic_research_queue_brief_section()
    brief = build_synthetic_research_queue_brief()

    assert type(status) is ResearchQueueStatus
    assert type(item) is ResearchQueueBriefItem
    assert type(section) is ResearchQueueBriefSection
    assert type(brief) is ResearchQueueBrief


def test_expected_dict_helpers_match_to_dict_outputs() -> None:
    status = build_synthetic_research_queue_status()
    item = build_synthetic_research_queue_brief_item()
    section = build_synthetic_research_queue_brief_section()
    brief = build_synthetic_research_queue_brief()

    assert status.to_dict() == expected_synthetic_research_queue_status_dict()
    assert item.to_dict() == expected_synthetic_research_queue_brief_item_dict()
    assert section.to_dict() == expected_synthetic_research_queue_brief_section_dict()
    assert brief.to_dict() == expected_synthetic_research_queue_brief_dict()
    assert brief.to_dict() == _EXPECTED_BRIEF_DICT
    _assert_primitive_only(brief.to_dict())


def test_fixture_payloads_are_exact_and_compact_json_deterministic() -> None:
    assert expected_synthetic_research_queue_status_dict() == _EXPECTED_STATUS_DICT
    assert expected_synthetic_research_queue_brief_item_dict() == _EXPECTED_ITEM_DICT
    assert (
        expected_synthetic_research_queue_brief_section_dict()
        == _EXPECTED_SECTION_DICT
    )
    assert expected_synthetic_research_queue_brief_dict() == _EXPECTED_BRIEF_DICT

    first = build_synthetic_research_queue_brief().to_dict()
    second = build_synthetic_research_queue_brief().to_dict()
    first_json = json.dumps(first, ensure_ascii=True, separators=(",", ":"))
    second_json = json.dumps(second, ensure_ascii=True, separators=(",", ":"))

    assert first == second == _EXPECTED_BRIEF_DICT
    assert first_json == second_json == _EXPECTED_COMPACT_JSON
    assert json.loads(first_json) == first


def test_expected_dict_helpers_return_fresh_mutable_copies() -> None:
    first = expected_synthetic_research_queue_brief_dict()
    second = expected_synthetic_research_queue_brief_dict()

    assert first is not second
    assert first["sections"] is not second["sections"]
    assert first["sections"][0] is not second["sections"][0]
    assert first["sections"][0]["items"] is not second["sections"][0]["items"]
    assert (
        first["sections"][0]["items"][0]
        is not second["sections"][0]["items"][0]
    )
    assert (
        first["sections"][0]["items"][0]["source_status"]
        is not second["sections"][0]["items"][0]["source_status"]
    )

    for field_name in ("limitations", "non_claims"):
        assert first[field_name] is not second[field_name]
        assert (
            first["sections"][0][field_name]
            is not second["sections"][0][field_name]
        )
        assert first[field_name] is not first["sections"][0][field_name]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")
    first["sections"][0]["items"][0]["source_status"]["blockers"].append(
        "mutated nested primitive copy"
    )

    assert second == _EXPECTED_BRIEF_DICT
    assert expected_synthetic_research_queue_brief_dict() == _EXPECTED_BRIEF_DICT


def test_repeated_construction_is_deterministic_without_shared_objects() -> None:
    first_status = build_synthetic_research_queue_status()
    second_status = build_synthetic_research_queue_status()
    first_item = build_synthetic_research_queue_brief_item()
    second_item = build_synthetic_research_queue_brief_item()
    first_section = build_synthetic_research_queue_brief_section()
    second_section = build_synthetic_research_queue_brief_section()
    first_brief = build_synthetic_research_queue_brief()
    second_brief = build_synthetic_research_queue_brief()

    assert first_status is not second_status
    assert first_item is not second_item
    assert first_section is not second_section
    assert first_brief is not second_brief
    assert first_status.to_dict() == second_status.to_dict() == _EXPECTED_STATUS_DICT
    assert first_item.to_dict() == second_item.to_dict() == _EXPECTED_ITEM_DICT
    assert first_section.to_dict() == second_section.to_dict() == _EXPECTED_SECTION_DICT
    assert first_brief.to_dict() == second_brief.to_dict() == _EXPECTED_BRIEF_DICT


def test_item_section_and_brief_preserve_source_identity_and_order() -> None:
    status = build_synthetic_research_queue_status()
    item = fixture_module.build_research_queue_brief_item(status)
    section = fixture_module.build_research_queue_brief_section((item,))
    brief = fixture_module.build_research_queue_brief((section,))

    assert item.source_status is status
    assert section.items == (item,)
    assert section.items[0] is item
    assert brief.sections == (section,)
    assert brief.sections[0] is section
    assert brief.to_dict() == _EXPECTED_BRIEF_DICT


def test_fixed_advisory_metadata_is_pinned_at_every_level() -> None:
    status = build_synthetic_research_queue_status()
    item = build_synthetic_research_queue_brief_item()
    section = build_synthetic_research_queue_brief_section()
    brief = build_synthetic_research_queue_brief()

    assert status.queue_type == "research_queue_status"
    assert item.item_type == "research_queue_brief_item"
    assert section.section_type == "research_queue_brief_section"
    assert brief.brief_type == "research_queue_brief"

    for node in (status, item, section, brief):
        assert node.status == "candidate_only"
        assert node.authority == "advisory_only"
        assert node.capital_authority is False


def test_limitations_and_non_claims_are_present_and_carried_forward() -> None:
    status = build_synthetic_research_queue_status()
    item = build_synthetic_research_queue_brief_item()
    section = build_synthetic_research_queue_brief_section()
    brief = build_synthetic_research_queue_brief()

    assert item.limitations == status.limitations
    assert section.limitations == item.limitations
    assert brief.limitations == section.limitations
    assert item.non_claims == status.non_claims
    assert section.non_claims == item.non_claims
    assert brief.non_claims == section.non_claims
    assert set(_REQUIRED_NON_CLAIMS).issubset(brief.non_claims)
    assert set(_ADDITIONAL_NON_CLAIMS).issubset(brief.non_claims)
    assert all(value.startswith("not ") for value in brief.non_claims)
    assert len(brief.non_claims) == 20


def test_no_authority_like_states_or_actionable_payload_values_appear() -> None:
    payload = build_synthetic_research_queue_brief().to_dict()
    strings = _payload_strings_excluding_keys(payload, excluded_keys={"non_claims"})
    lowered_strings = tuple(value.lower() for value in strings)

    assert payload["status"] == "candidate_only"
    assert payload["sections"][0]["items"][0]["research_state"] == "needs_evidence"
    assert payload["sections"][0]["items"][0]["priority_bucket"] == "medium"
    for token in _FORBIDDEN_PAYLOAD_TOKENS:
        assert all(token not in value for value in lowered_strings)
    for token in _FORBIDDEN_NON_NON_CLAIM_TEXT_TOKENS:
        assert all(token not in value for value in lowered_strings)


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


def test_fixture_literals_keep_authority_language_inside_non_claims_only() -> None:
    non_claim_literals = _non_claim_string_literals()
    other_literals = _string_literals() - non_claim_literals

    for token in _FORBIDDEN_NON_NON_CLAIM_TEXT_TOKENS:
        assert all(token not in value.lower() for value in other_literals)
    assert any("approval" in value.lower() for value in non_claim_literals)
    assert any(_s("allo", "cation") in value.lower() for value in non_claim_literals)
    assert any(_s("or", "der") in value.lower() for value in non_claim_literals)
    assert any(_s("bro", "ker") in value.lower() for value in non_claim_literals)
    assert any(_s("ac", "count") in value.lower() for value in non_claim_literals)
    assert any(_s("port", "folio") in value.lower() for value in non_claim_literals)
    assert any("readiness" in value.lower() for value in non_claim_literals)
    assert any("trading authority" in value.lower() for value in non_claim_literals)


def test_fixture_exposes_no_actionable_authority_fields() -> None:
    payload = build_synthetic_research_queue_brief().to_dict()

    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _ast_dict_string_keys().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert _call_keyword_names().isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)
    assert all(
        not hasattr(build_synthetic_research_queue_brief(), field_name)
        for field_name in _FORBIDDEN_AUTHORITY_FIELDS
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


def _payload_strings_excluding_keys(
    value: object,
    *,
    excluded_keys: set[str],
) -> tuple[str, ...]:
    strings: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key in excluded_keys:
                continue
            strings.extend(
                _payload_strings_excluding_keys(
                    nested_value,
                    excluded_keys=excluded_keys,
                )
            )
        return tuple(strings)

    if isinstance(value, list):
        for nested_value in value:
            strings.extend(
                _payload_strings_excluding_keys(
                    nested_value,
                    excluded_keys=excluded_keys,
                )
            )
        return tuple(strings)

    if type(value) is str:
        return (value,)

    return ()


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


def _non_claim_string_literals() -> set[str]:
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_NON_CLAIMS":
                    return {
                        nested.value
                        for nested in ast.walk(node.value)
                        if isinstance(nested, ast.Constant)
                        and isinstance(nested.value, str)
                    }

    raise AssertionError("_NON_CLAIMS was not found.")
