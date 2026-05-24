from __future__ import annotations

import ast
import inspect
import json
import re
import sys

from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_PAYLOAD = (
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()
)
_EXPECTED_JSON_TEXT = json.dumps(
    _EXPECTED_PAYLOAD,
    sort_keys=True,
    separators=(",", ":"),
)
_EXPECTED_BRANCH_KEYS = (
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "risk_authority_briefs",
    "research_queue_briefs",
)
_EXPECTED_BRANCH_COUNT_KEYS = (
    "candidate_research_brief_count",
    "strategy_eligibility_brief_count",
    "risk_authority_brief_count",
    "research_queue_brief_count",
)
_EXPECTED_BRANCH_HEADINGS = (
    "Candidate Research Briefs",
    "Strategy Eligibility Briefs",
    "Risk Authority Briefs",
    "Research Queue Briefs",
    "Limitations",
    "Non-Claims",
)
_EXPECTED_RESEARCH_QUEUE_ITEM_FIELDS = (
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
    "source_status",
)
_EXPECTED_RESEARCH_QUEUE_STATUS_FIELDS = (
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
_EXPECTED_RESEARCH_QUEUE_NON_CLAIMS = (
    _s("not a recomm", "endation"),
    _s("not allo", "cation authority"),
    _s("not or", "der authority"),
    _s("not pa", "per read", "iness"),
    _s("not li", "ve read", "iness"),
    _s("not bro", "ker authority"),
    _s("not acc", "ount authority"),
    _s("not port", "folio mutation authority"),
    _s("not cap", "ital authority"),
    _s("not tra", "ding authority"),
    _s("not strategy app", "roval"),
    _s("not data source app", "roval"),
    _s("not methodology app", "roval"),
    _s("not profit", "ability evidence"),
    _s("not research conclusion"),
    _s("not back", "test read", "iness"),
    _s("not exe", "cution read", "iness"),
    _s("not allo", "cation guidance"),
    _s("not or", "der placement"),
    _s("not ran", "king or sco", "ring output"),
)
_ALLOWED_IMPORTS = {
    "__future__",
    "ast",
    "inspect",
    "json",
    "re",
    "sys",
    "algotrader.research.advisory_operating_brief_content_bundle_export",
    "algotrader.research.advisory_operating_brief_content_bundle_renderer",
    "tests.fixtures.advisory_operating_brief_content_bundle",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "argparse",
    _s("algotrader.", "back", "test"),
    _s("algotrader.", "back", "testing"),
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    _s("algotrader.", "dash", "board"),
    _s("algotrader.", "exe", "cution"),
    _s("algotrader.", "l", "lm"),
    _s("algotrader.", "l", "lms"),
    _s("algotrader.", "m", "l"),
    "algotrader.orchestration",
    _s("algotrader.", "persist", "ence"),
    _s("algotrader.", "port", "folio"),
    "algotrader.risk",
    _s("algotrader.", "run", "time"),
    _s("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _s("algotrader.", "sig", "nals"),
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    "anthropic",
    "click",
    _s("data", "base"),
    "duckdb",
    _s("ht", "tp"),
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
    _s("path", "lib"),
    _s("poly", "gon"),
    _s("poly", "gon_a", "pi_client"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("sche", "dule"),
    "sklearn",
    _s("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    _s("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    "build_parser",
    _s("cli", "ent"),
    _s("con", "nect"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "exists",
    "export_advisory_operating_brief",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "json.load",
    "main",
    "mkdir",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "parse_args",
    "post",
    "print",
    _s("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    "render_advisory_operating_brief_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "rglob",
    "save",
    _s("so", "cket", ".", "so", "cket"),
    "stat",
    _s("sub", "mit_", "or", "der"),
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
_FORBIDDEN_SOURCE_TERMS = (
    _s("acc", "ount"),
    _s("acc", "ounts"),
    _s("ag", "ent"),
    _s("allo", "cation"),
    _s("app", "roval"),
    _s("app", "roved"),
    _s("back", "testing"),
    _s("bro", "ker"),
    _s("b", "uy"),
    _s("cre", "dential"),
    _s("dash", "board"),
    _s("data source app", "roval"),
    _s("exe", "cution read", "iness"),
    _s("fi", "ll"),
    _s("fi", "lls"),
    _s("ho", "ld"),
    _s("li", "ve"),
    _s("live_", "authorized"),
    _s("live_", "probe_eligible"),
    _s("l", "lm"),
    _s("m", "l"),
    _s("methodology app", "roval"),
    _s("n", "et", "work"),
    _s("note", "book"),
    _s("or", "der"),
    _s("or", "ders"),
    _s("pa", "per"),
    _s("paper_", "eligible"),
    _s("port", "folio"),
    _s("port", "folio mutation"),
    _s("ran", "king"),
    _s("read", "iness"),
    _s("recomm", "endation"),
    _s("risk app", "roval"),
    _s("run", "time"),
    _s("sche", "duler"),
    _s("sco", "ring"),
    _s("se", "ll"),
    _s("sig", "nal"),
    _s("so", "cket"),
    _s("strategy exe", "cution"),
    _s("tra", "ding authority"),
    _s("tra", "ding_ready"),
    _s("tra", "ding-ready"),
    _s("tra", "ding_authority"),
    _s("ven", "dor"),
)


def test_phase_186_research_queue_export_matches_expected_bundle_views() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    before_payload = bundle.to_dict()

    exported = export_advisory_operating_brief_content_bundle(bundle)

    assert exported.payload == _EXPECTED_PAYLOAD
    assert exported.payload == before_payload
    assert exported.json_text == _EXPECTED_JSON_TEXT
    assert exported.json_text == json.dumps(
        _EXPECTED_PAYLOAD,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json.loads(exported.json_text) == _EXPECTED_PAYLOAD
    assert exported.rendered_text == (
        render_advisory_operating_brief_content_bundle_text(bundle)
    )
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_phase_186_repeated_research_queue_exports_are_byte_deterministic() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    before_payload = bundle.to_dict()

    first = export_advisory_operating_brief_content_bundle(bundle)
    second = export_advisory_operating_brief_content_bundle(bundle)
    third = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    )

    assert first == second == third
    assert first.payload == second.payload == third.payload == _EXPECTED_PAYLOAD
    assert first.payload is not second.payload
    assert first.payload is not third.payload
    assert first.json_text == second.json_text == third.json_text == _EXPECTED_JSON_TEXT
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert second.json_text.encode("utf-8") == third.json_text.encode("utf-8")
    assert first.rendered_text == second.rendered_text == third.rendered_text
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")
    assert second.rendered_text.encode("utf-8") == third.rendered_text.encode("utf-8")
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_phase_186_research_queue_branches_and_nested_metadata_are_pinned() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    exported = export_advisory_operating_brief_content_bundle(bundle)
    payload = exported.payload
    expected_research_brief = _dict(_list(_EXPECTED_PAYLOAD["research_queue_briefs"])[0])
    research_brief = _dict(_list(payload["research_queue_briefs"])[0])
    expected_section = _dict(_list(expected_research_brief["sections"])[0])
    section = _dict(_list(research_brief["sections"])[0])
    expected_item = _dict(_list(expected_section["items"])[0])
    item = _dict(_list(section["items"])[0])
    expected_status = _dict(expected_item["source_status"])
    source_status = _dict(item["source_status"])

    assert tuple(payload) == tuple(_EXPECTED_PAYLOAD)
    assert all(key in payload for key in _EXPECTED_BRANCH_KEYS)
    assert all(key in payload for key in _EXPECTED_BRANCH_COUNT_KEYS)
    assert payload["candidate_research_brief_count"] == 1
    assert payload["strategy_eligibility_brief_count"] == 1
    assert payload["risk_authority_brief_count"] == 1
    assert payload["research_queue_brief_count"] == 1
    assert len(_list(payload["candidate_research_briefs"])) == 1
    assert len(_list(payload["strategy_eligibility_briefs"])) == 1
    assert len(_list(payload["risk_authority_briefs"])) == 1
    assert len(_list(payload["research_queue_briefs"])) == 1
    assert research_brief == expected_research_brief
    assert section == expected_section
    assert item == expected_item
    assert source_status == expected_status
    assert research_brief["brief_type"] == "research_queue_brief"
    assert section["section_type"] == "research_queue_brief_section"
    assert item["item_type"] == "research_queue_brief_item"
    assert source_status["queue_type"] == "research_queue_status"
    assert item["research_state"] == "needs_evidence"
    assert item["priority_bucket"] == "medium"
    assert item["topic"] == "broad_etf_sma_trend_following"
    assert tuple(key for key in _EXPECTED_RESEARCH_QUEUE_ITEM_FIELDS if key in item) == (
        _EXPECTED_RESEARCH_QUEUE_ITEM_FIELDS
    )
    assert tuple(
        key for key in _EXPECTED_RESEARCH_QUEUE_STATUS_FIELDS if key in source_status
    ) == _EXPECTED_RESEARCH_QUEUE_STATUS_FIELDS
    for field_name in _EXPECTED_RESEARCH_QUEUE_ITEM_FIELDS:
        if field_name == "source_status":
            continue
        assert item[field_name] == expected_item[field_name]
    for field_name in _EXPECTED_RESEARCH_QUEUE_STATUS_FIELDS:
        assert source_status[field_name] == expected_status[field_name]


def test_phase_186_branch_sequence_is_deterministic() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    )
    payload = exported.payload
    lines = tuple(exported.rendered_text.splitlines())

    assert tuple(payload) == tuple(_EXPECTED_PAYLOAD)
    assert _index(payload, "candidate_research_briefs") < _index(
        payload,
        "strategy_eligibility_briefs",
    )
    assert _index(payload, "strategy_eligibility_briefs") < _index(
        payload,
        "risk_authority_briefs",
    )
    assert _index(payload, "risk_authority_briefs") < _index(
        payload,
        "research_queue_briefs",
    )
    assert _index(payload, "research_queue_briefs") < _index(payload, "limitations")
    _assert_sequence(lines, _EXPECTED_BRANCH_HEADINGS)


def test_phase_186_cautions_are_preserved() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    exported = export_advisory_operating_brief_content_bundle(bundle)
    payload = exported.payload
    lines = tuple(exported.rendered_text.splitlines())
    research_brief = _dict(_list(payload["research_queue_briefs"])[0])

    assert payload["limitations"] == _EXPECTED_PAYLOAD["limitations"]
    assert payload["non_claims"] == _EXPECTED_PAYLOAD["non_claims"]
    assert payload["limitations"]
    assert payload["non_claims"]
    assert set(_EXPECTED_RESEARCH_QUEUE_NON_CLAIMS).issubset(
        set(_list(research_brief["non_claims"]))
    )
    assert all(
        value.startswith("not ") for value in _list(research_brief["non_claims"])
    )
    assert "Limitations" in lines
    assert "Non-Claims" in lines
    for branch_key in _EXPECTED_BRANCH_KEYS:
        for branch_payload in _list(payload[branch_key]):
            branch = _dict(branch_payload)
            for value in _list(branch["limitations"]):
                assert f"- {value}" in lines
            for value in _list(branch["non_claims"]):
                assert f"- {value}" in lines
    for value in _list(payload["limitations"]):
        assert f"- {value}" in lines
    for value in _list(payload["non_claims"]):
        assert f"- {value}" in lines


def test_phase_186_export_payload_changes_do_not_change_source_bundle() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    before_payload = bundle.to_dict()
    before_rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    exported = export_advisory_operating_brief_content_bundle(bundle)

    _change_export_payload(exported.payload)

    assert exported.payload != _EXPECTED_PAYLOAD
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD
    assert render_advisory_operating_brief_content_bundle_text(bundle) == before_rendered
    assert export_advisory_operating_brief_content_bundle(bundle).payload == (
        _EXPECTED_PAYLOAD
    )


def test_phase_186_guardrails_keep_test_isolated() -> None:
    imports = _import_references()
    call_names = _call_names()
    lowered_source = _source_text().lower()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    for term in _FORBIDDEN_SOURCE_TERMS:
        assert (
            re.search(
                rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])",
                lowered_source,
            )
            is None
        )


def _change_export_payload(payload: dict[str, object]) -> None:
    research_brief = _dict(_list(payload["research_queue_briefs"])[0])
    section = _dict(_list(research_brief["sections"])[0])
    item = _dict(_list(section["items"])[0])
    source_status = _dict(item["source_status"])

    payload["title"] = "changed copied payload"
    _list(payload["limitations"]).append("changed copied payload")
    research_brief["title"] = "changed copied payload"
    section["title"] = "changed copied payload"
    item["title"] = "changed copied payload"
    _list(source_status["blockers"]).append("changed copied payload")


def _index(payload: dict[str, object], key: str) -> int:
    return tuple(payload).index(key)


def _assert_sequence(lines: tuple[str, ...], expected_values: tuple[str, ...]) -> None:
    positions = tuple(lines.index(value) for value in expected_values)

    assert positions == tuple(sorted(positions))


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


def _source_text() -> str:
    return inspect.getsource(sys.modules[__name__])


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
