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
    build_synthetic_advisory_operating_brief_content_bundle_with_risk,
    expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_PAYLOAD = (
    expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict()
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
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    _s("algotrader.", "dash", "board"),
    "algotrader.execution",
    _s("algotrader.", "l", "lm"),
    _s("algotrader.", "l", "lms"),
    "algotrader.ml",
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
    _s("act", "ionable"),
    _s("ag", "ent"),
    _s("allo", "cation"),
    _s("app", "roved"),
    _s("bro", "ker"),
    _s("b", "uy"),
    _s("cre", "dential"),
    _s("dash", "board"),
    _s("fi", "ll"),
    _s("fi", "lls"),
    _s("ho", "ld"),
    _s("li", "ve"),
    _s("live_", "authorized"),
    _s("live_", "probe_eligible"),
    _s("l", "lm"),
    _s("n", "et", "work"),
    _s("note", "book"),
    _s("or", "der"),
    _s("or", "ders"),
    _s("pa", "per"),
    _s("paper_", "eligible"),
    _s("port", "folio"),
    _s("port", "folio mutation"),
    _s("run", "time"),
    _s("sche", "duler"),
    _s("se", "ll"),
    _s("so", "cket"),
    _s("tra", "ding_ready"),
    _s("tra", "ding-ready"),
    _s("tra", "ding_authority"),
    _s("ven", "dor"),
)


def test_phase_180_risk_inclusive_export_matches_expected_bundle_views() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
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


def test_phase_180_repeated_risk_inclusive_exports_are_byte_deterministic() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    before_payload = bundle.to_dict()

    first = export_advisory_operating_brief_content_bundle(bundle)
    second = export_advisory_operating_brief_content_bundle(bundle)

    assert first == second
    assert first.payload == second.payload == _EXPECTED_PAYLOAD
    assert first.payload is not second.payload
    assert first.json_text == second.json_text == _EXPECTED_JSON_TEXT
    assert first.json_text.encode("utf-8") == second.json_text.encode("utf-8")
    assert first.rendered_text == second.rendered_text
    assert first.rendered_text.encode("utf-8") == second.rendered_text.encode("utf-8")
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_phase_180_risk_branch_presence_sequence_and_metadata_are_pinned() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    exported = export_advisory_operating_brief_content_bundle(bundle)
    payload = exported.payload
    expected_risk_brief = _EXPECTED_PAYLOAD["risk_authority_briefs"][0]
    risk_brief = payload["risk_authority_briefs"][0]
    expected_risk_item = expected_risk_brief["sections"][0]["items"][0]
    risk_item = risk_brief["sections"][0]["items"][0]
    lines = tuple(exported.rendered_text.splitlines())

    assert tuple(payload) == tuple(_EXPECTED_PAYLOAD)
    assert all(key in payload for key in _EXPECTED_BRANCH_KEYS)
    assert payload["candidate_research_brief_count"] == 1
    assert payload["strategy_eligibility_brief_count"] == 1
    assert payload["risk_authority_brief_count"] == 1
    assert len(payload["candidate_research_briefs"]) == 1
    assert len(payload["strategy_eligibility_briefs"]) == 1
    assert len(payload["risk_authority_briefs"]) == 1
    assert risk_brief == expected_risk_brief
    assert risk_item["authority_state"] == expected_risk_item["authority_state"]
    assert risk_item["source_status"] == expected_risk_item["source_status"]
    assert _index(payload, "candidate_research_briefs") < _index(
        payload,
        "strategy_eligibility_briefs",
    )
    assert _index(payload, "strategy_eligibility_briefs") < _index(
        payload,
        "risk_authority_briefs",
    )
    assert _line_index(lines, "Candidate Research Briefs") < _line_index(
        lines,
        "Strategy Eligibility Briefs",
    )
    assert _line_index(lines, "Strategy Eligibility Briefs") < _line_index(
        lines,
        "Risk Authority Briefs",
    )
    assert _line_index(lines, "Risk Authority Briefs") < _line_index(
        lines,
        "Limitations",
    )
    assert _line_index(lines, "Limitations") < _line_index(lines, "Non-Claims")


def test_phase_180_limitations_and_non_claims_are_preserved() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    exported = export_advisory_operating_brief_content_bundle(bundle)
    payload = exported.payload
    lines = tuple(exported.rendered_text.splitlines())

    assert payload["limitations"] == _EXPECTED_PAYLOAD["limitations"]
    assert payload["non_claims"] == _EXPECTED_PAYLOAD["non_claims"]
    assert payload["limitations"]
    assert payload["non_claims"]
    assert "Limitations" in lines
    assert "Non-Claims" in lines
    for value in _EXPECTED_PAYLOAD["limitations"]:
        assert f"- {value}" in lines
    for value in _EXPECTED_PAYLOAD["non_claims"]:
        assert f"- {value}" in lines


def test_phase_180_export_payload_changes_do_not_change_source_bundle() -> None:
    bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    before_payload = bundle.to_dict()
    before_rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    exported = export_advisory_operating_brief_content_bundle(bundle)

    exported.payload["title"] = "changed copied payload"
    exported.payload["limitations"].append("changed copied payload")
    exported.payload["risk_authority_briefs"][0]["title"] = "changed copied payload"

    assert exported.payload != _EXPECTED_PAYLOAD
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD
    assert render_advisory_operating_brief_content_bundle_text(bundle) == before_rendered
    assert export_advisory_operating_brief_content_bundle(bundle).payload == (
        _EXPECTED_PAYLOAD
    )


def test_phase_180_guardrails_new_test_avoids_forbidden_behavior() -> None:
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


def _index(payload: dict[str, object], key: str) -> int:
    return tuple(payload).index(key)


def _line_index(lines: tuple[str, ...], value: str) -> int:
    return lines.index(value)


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
