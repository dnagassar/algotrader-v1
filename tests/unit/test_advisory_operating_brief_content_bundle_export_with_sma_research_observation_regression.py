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
    build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation,
    expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_PAYLOAD = (
    expected_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation_dict()
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
    "sma_research_observation_briefs",
)
_EXPECTED_BRANCH_COUNT_KEYS = (
    "candidate_research_brief_count",
    "strategy_eligibility_brief_count",
    "risk_authority_brief_count",
    "research_queue_brief_count",
    "sma_research_observation_brief_count",
)
_EXPECTED_BRANCH_HEADINGS = (
    "Candidate Research Briefs",
    "Strategy Eligibility Briefs",
    "Risk Authority Briefs",
    "Research Queue Briefs",
    "SMA Research Observation Briefs",
    "Limitations",
    "Non-Claims",
)
_EXPECTED_SMA_BRIEF_FIELDS = (
    "brief_type",
    "status",
    "authority",
    "capital_authority",
    "brief_id",
    "title",
    "summary",
    "section_count",
    "sections",
    "limitations",
    "non_claims",
)
_EXPECTED_SMA_SECTION_FIELDS = (
    "section_type",
    "status",
    "authority",
    "capital_authority",
    "section_id",
    "title",
    "summary",
    "item_count",
    "items",
    "limitations",
    "non_claims",
)
_EXPECTED_SMA_ITEM_FIELDS = (
    "item_type",
    "status",
    "authority",
    "capital_authority",
    "headline",
    "summary",
    "mechanical_state",
    "source_observation",
    "limitations",
    "non_claims",
)
_EXPECTED_SMA_SOURCE_OBSERVATION_FIELDS = (
    "observation_type",
    "status",
    "authority",
    "capital_authority",
    "symbol",
    "as_of",
    "window",
    "sample_count",
    "eligible_sample_count",
    "ignored_future_sample_count",
    "latest_close",
    "sma_value",
    "distance_from_sma",
    "distance_from_sma_pct",
    "position_vs_sma",
    "limitations",
    "non_claims",
)
_EXPECTED_SMA_NON_CLAIMS = (
    _s("not strategy app", "roval"),
    _s("not sour", "ce/data app", "roval"),
    _s("not predict", "ive validity"),
    _s("not prof", "itability"),
    _s("not a recomm", "endation"),
    _s("not sig", "nal or evalu", "ator behavior"),
    _s("not allo", "cation or or", "der authority"),
    _s("not bro", "ker authority"),
    _s("not port", "folio mut", "ation authority"),
    _s("not pa", "per read", "iness"),
    _s("not li", "ve read", "iness"),
    _s("not capital ", "authority"),
    _s("not tra", "ding authority"),
    _s("not meth", "odology app", "roval"),
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
    "algotrader.research.advisory_operating_brief_content_bundle_cli",
    "algotrader.research.advisory_operating_brief_package",
    "algotrader.research.advisory_operating_brief_package_cli",
    "algotrader.research.advisory_operating_brief_package_synthetic_builder",
    "algotrader.research.sma_research_observation_brief_export",
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
    "export_sma_research_observation_brief",
    "from_file",
    _s("from", "_dict"),
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
    "render_sma_research_observation_brief_text",
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
    _s("back", "test"),
    _s("back", "testing"),
    _s("bro", "ker"),
    _s("b", "uy"),
    _s("cre", "dential"),
    _s("dash", "board"),
    _s("data source app", "roval"),
    _s("exe", "cution read", "iness"),
    _s("fi", "le i/o"),
    _s("fi", "ll"),
    _s("fi", "lls"),
    _s("from", "_dict"),
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
    _s("source app", "roval"),
    _s("strategy exe", "cution"),
    _s("tra", "ding authority"),
    _s("tra", "ding_ready"),
    _s("tra", "ding-ready"),
    _s("tra", "ding_authority"),
    _s("ven", "dor"),
)


def test_phase_207_sma_inclusive_export_matches_expected_bundle_views() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    before_payload = bundle.to_dict()
    expected_rendered = render_advisory_operating_brief_content_bundle_text(bundle)

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
    assert exported.rendered_text == expected_rendered
    assert exported.rendered_text == (
        render_advisory_operating_brief_content_bundle_text(bundle)
    )
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD


def test_phase_207_repeated_sma_inclusive_exports_are_byte_deterministic() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    before_payload = bundle.to_dict()

    first = export_advisory_operating_brief_content_bundle(bundle)
    second = export_advisory_operating_brief_content_bundle(bundle)
    third = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
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


def test_phase_207_sma_branches_and_nested_metadata_are_pinned() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    payload = exported.payload
    expected_sma_brief = _dict(
        _list(_EXPECTED_PAYLOAD["sma_research_observation_briefs"])[0]
    )
    sma_brief = _dict(_list(payload["sma_research_observation_briefs"])[0])
    expected_section = _dict(_list(expected_sma_brief["sections"])[0])
    section = _dict(_list(sma_brief["sections"])[0])
    expected_items = tuple(_dict(item) for item in _list(expected_section["items"]))
    items = tuple(_dict(item) for item in _list(section["items"]))
    source_observations = tuple(
        _dict(item["source_observation"]) for item in items
    )

    assert tuple(payload) == tuple(_EXPECTED_PAYLOAD)
    assert all(key in payload for key in _EXPECTED_BRANCH_KEYS)
    assert all(key in payload for key in _EXPECTED_BRANCH_COUNT_KEYS)
    assert payload["candidate_research_brief_count"] == 1
    assert payload["strategy_eligibility_brief_count"] == 1
    assert payload["risk_authority_brief_count"] == 1
    assert payload["research_queue_brief_count"] == 1
    assert payload["sma_research_observation_brief_count"] == 1
    assert len(_list(payload["candidate_research_briefs"])) == 1
    assert len(_list(payload["strategy_eligibility_briefs"])) == 1
    assert len(_list(payload["risk_authority_briefs"])) == 1
    assert len(_list(payload["research_queue_briefs"])) == 1
    assert len(_list(payload["sma_research_observation_briefs"])) == 1
    assert sma_brief == expected_sma_brief
    assert section == expected_section
    assert items == expected_items
    assert tuple(sma_brief) == _EXPECTED_SMA_BRIEF_FIELDS
    assert tuple(section) == _EXPECTED_SMA_SECTION_FIELDS
    assert tuple(items[0]) == _EXPECTED_SMA_ITEM_FIELDS
    assert tuple(items[1]) == _EXPECTED_SMA_ITEM_FIELDS
    assert tuple(source_observations[0]) == _EXPECTED_SMA_SOURCE_OBSERVATION_FIELDS
    assert tuple(source_observations[1]) == _EXPECTED_SMA_SOURCE_OBSERVATION_FIELDS
    assert sma_brief["brief_type"] == "sma_research_observation_brief"
    assert section["section_type"] == "sma_research_observation_brief_section"
    assert section["item_count"] == 2
    assert all(
        item["item_type"] == "sma_research_observation_brief_item"
        for item in items
    )
    assert all(
        observation["observation_type"] == "sma_research_observation"
        for observation in source_observations
    )
    assert {observation["symbol"] for observation in source_observations} == {
        "SYNTH_ETF",
    }
    assert {observation["as_of"] for observation in source_observations} == {
        "2026-01-20",
    }
    assert {observation["window"] for observation in source_observations} == {3}


def test_phase_207_nested_sma_mechanics_are_pinned() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    primary_item, insufficient_item = _sma_items(exported.payload)
    primary_observation = _dict(primary_item["source_observation"])
    insufficient_observation = _dict(insufficient_item["source_observation"])

    assert (
        primary_item["mechanical_state"],
        insufficient_item["mechanical_state"],
    ) == ("above_sma_observation", "insufficient_history")
    assert primary_observation["position_vs_sma"] == "above"
    assert insufficient_observation["position_vs_sma"] == "insufficient_history"
    assert primary_observation["ignored_future_sample_count"] == 1
    assert insufficient_observation["ignored_future_sample_count"] == 1
    assert primary_observation["eligible_sample_count"] == 3
    assert insufficient_observation["eligible_sample_count"] == 2
    assert primary_observation["latest_close"] == "110.00"
    assert insufficient_observation["latest_close"] == "101.00"
    assert primary_observation["sma_value"] == "100.00"
    assert primary_observation["distance_from_sma"] == "10.00"
    assert primary_observation["distance_from_sma_pct"] == "0.1"
    assert insufficient_observation["sma_value"] is None
    assert insufficient_observation["distance_from_sma"] is None
    assert insufficient_observation["distance_from_sma_pct"] is None
    assert "mechanical_state: above_sma_observation" in exported.rendered_text
    assert "mechanical_state: insufficient_history" in exported.rendered_text
    assert exported.rendered_text.count("ignored_future_sample_count: 1") == 2
    assert "sma_value: null" in exported.rendered_text
    assert "distance_from_sma: null" in exported.rendered_text
    assert "distance_from_sma_pct: null" in exported.rendered_text


def test_phase_207_sma_branch_sequence_is_deterministic() -> None:
    exported = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
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
    assert _index(payload, "research_queue_briefs") < _index(
        payload,
        "sma_research_observation_briefs",
    )
    assert _index(payload, "sma_research_observation_briefs") < _index(
        payload,
        "limitations",
    )
    assert _index(payload, "limitations") < _index(payload, "non_claims")
    _assert_sequence(lines, _EXPECTED_BRANCH_HEADINGS)


def test_phase_207_limitations_and_non_claims_are_preserved() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    exported = export_advisory_operating_brief_content_bundle(bundle)
    payload = exported.payload
    lines = tuple(exported.rendered_text.splitlines())
    sma_brief = _dict(_list(payload["sma_research_observation_briefs"])[0])
    items = _sma_items(payload)

    assert payload["limitations"] == _EXPECTED_PAYLOAD["limitations"]
    assert payload["non_claims"] == _EXPECTED_PAYLOAD["non_claims"]
    assert payload["limitations"]
    assert payload["non_claims"]
    assert set(_EXPECTED_SMA_NON_CLAIMS).issubset(
        set(_list(sma_brief["non_claims"]))
    )
    assert all(value.startswith("not ") for value in _list(sma_brief["non_claims"]))
    for item in items:
        assert set(_EXPECTED_SMA_NON_CLAIMS).issubset(
            set(_list(item["non_claims"]))
        )
        assert all(value.startswith("not ") for value in _list(item["non_claims"]))
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


def test_phase_207_export_payload_changes_do_not_change_source_bundle() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation()
    )
    before_payload = bundle.to_dict()
    before_rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    identity_snapshot = _source_identity_snapshot(bundle)
    exported = export_advisory_operating_brief_content_bundle(bundle)

    _change_export_payload(exported.payload)

    assert exported.payload != _EXPECTED_PAYLOAD
    assert bundle.to_dict() == before_payload == _EXPECTED_PAYLOAD
    assert render_advisory_operating_brief_content_bundle_text(bundle) == before_rendered
    assert _source_identity_snapshot(bundle) == identity_snapshot
    assert export_advisory_operating_brief_content_bundle(bundle).payload == (
        _EXPECTED_PAYLOAD
    )


def test_phase_207_guardrails_keep_regression_isolated() -> None:
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


def _sma_items(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    sma_brief = _dict(_list(payload["sma_research_observation_briefs"])[0])
    section = _dict(_list(sma_brief["sections"])[0])

    return tuple(_dict(item) for item in _list(section["items"]))


def _change_export_payload(payload: dict[str, object]) -> None:
    sma_brief = _dict(_list(payload["sma_research_observation_briefs"])[0])
    section = _dict(_list(sma_brief["sections"])[0])
    primary_item, insufficient_item = _sma_items(payload)
    primary_observation = _dict(primary_item["source_observation"])
    insufficient_observation = _dict(insufficient_item["source_observation"])

    payload["title"] = "changed copied payload"
    _list(payload["limitations"]).append("changed copied payload")
    sma_brief["title"] = "changed copied payload"
    section["title"] = "changed copied payload"
    primary_item["headline"] = "changed copied payload"
    primary_observation["symbol"] = "CHANGED"
    _list(insufficient_observation["limitations"]).append("changed copied payload")


def _source_identity_snapshot(bundle: object) -> tuple[int, ...]:
    research_queue_brief = bundle.research_queue_briefs[0]
    sma_brief = bundle.sma_research_observation_briefs[0]
    sma_section = sma_brief.sections[0]
    first_item = sma_section.items[0]
    second_item = sma_section.items[1]

    return (
        id(bundle),
        id(bundle.candidate_research_briefs[0]),
        id(bundle.strategy_eligibility_briefs[0]),
        id(bundle.risk_authority_briefs[0]),
        id(research_queue_brief),
        id(research_queue_brief.sections),
        id(research_queue_brief.sections[0]),
        id(research_queue_brief.sections[0].items[0]),
        id(research_queue_brief.sections[0].items[0].source_status),
        id(sma_brief),
        id(sma_brief.sections),
        id(sma_section),
        id(sma_section.items),
        id(first_item),
        id(second_item),
        id(first_item.source_observation),
        id(second_item.source_observation),
    )


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
