from __future__ import annotations

import ast
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation_brief_container import (
    ResearchReturnObservationBrief,
)
from algotrader.research.research_return_observation_brief_renderer import (
    render_research_return_observation_brief_text,
)
from tests.fixtures.research_return_observation_brief_container import (
    build_synthetic_research_return_observation_brief,
    expected_synthetic_research_return_observation_brief_dict,
)


MODULE_PATH = Path(
    "src/algotrader/research/research_return_observation_brief_renderer.py"
)


def _join(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_RENDERED_LINES = (
    "Research Return Observation Brief",
    "brief_type: research_return_observation_brief",
    (
        "brief_id: research-return-observation-brief:synthetic:"
        "broad-etf-return-construction"
    ),
    "title: Synthetic broad ETF return observation brief",
    (
        "summary: Brief is advisory-only synthetic close-to-close return "
        "observation content."
    ),
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "section_count: 1",
    "",
    "Brief Limitations",
    "- synthetic broad ETF close series for return mechanics only",
    "- fixed close samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "",
    "Brief Non-Claims",
    "- not source/data approval",
    "- not adjusted-close/corporate-action completeness",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
    "- not backtesting validation",
    "- not allocation or order authority",
    "- not broker authority",
    "- not portfolio mutation authority",
    "- not paper readiness",
    "- not live readiness",
    "- not capital authority",
    "- not trading authority",
    "- not methodology approval",
    "",
    "Sections",
    "",
    "Section 1",
    "section_type: research_return_observation_brief_section",
    (
        "section_id: research-return-observation-section:synthetic:"
        "broad-etf-return-construction"
    ),
    "title: Synthetic broad ETF return observation summary",
    (
        "summary: Section is advisory-only synthetic close-to-close return "
        "observation content."
    ),
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "item_count: 2",
    "Section Limitations",
    "- synthetic broad ETF close series for return mechanics only",
    "- fixed close samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "Section Non-Claims",
    "- not source/data approval",
    "- not adjusted-close/corporate-action completeness",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
    "- not backtesting validation",
    "- not allocation or order authority",
    "- not broker authority",
    "- not portfolio mutation authority",
    "- not paper readiness",
    "- not live readiness",
    "- not capital authority",
    "- not trading authority",
    "- not methodology approval",
    "Items",
    "",
    "Section 1 Item 1",
    "item_type: research_return_observation_brief_item",
    "headline: Research return observation SYNTH_ETF 2026-01-20: returns_constructed.",
    (
        "summary: Research return observation metadata records returns_constructed "
        "for SYNTH_ETF as of 2026-01-20 using close_to_close_simple_return "
        "on synthetic_close, 4 eligible sample(s), 1 later sample(s) "
        "ignored, 3 return(s), positive count 1, negative count 1, and "
        "zero count 1."
    ),
    "mechanical_state: returns_constructed",
    "positive_return_count: 1",
    "negative_return_count: 1",
    "zero_return_count: 1",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "Source Observation",
    "symbol: SYNTH_ETF",
    "as_of: 2026-01-20",
    "return_method: close_to_close_simple_return",
    "price_basis: synthetic_close",
    "sample_count: 5",
    "eligible_sample_count: 4",
    "ignored_future_sample_count: 1",
    "return_count: 3",
    "Return Points",
    "Return Point 1",
    "start_date: 2026-01-15",
    "end_date: 2026-01-16",
    "start_close: 100.00",
    "end_close: 105.00",
    "simple_return: 0.05",
    "Return Point 2",
    "start_date: 2026-01-16",
    "end_date: 2026-01-19",
    "start_close: 105.00",
    "end_close: 94.50",
    "simple_return: -0.1",
    "Return Point 3",
    "start_date: 2026-01-19",
    "end_date: 2026-01-20",
    "start_close: 94.50",
    "end_close: 94.50",
    "simple_return: 0",
    "Item Limitations",
    "- synthetic broad ETF close series for return mechanics only",
    "- fixed close samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "Item Non-Claims",
    "- not source/data approval",
    "- not adjusted-close/corporate-action completeness",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
    "- not backtesting validation",
    "- not allocation or order authority",
    "- not broker authority",
    "- not portfolio mutation authority",
    "- not paper readiness",
    "- not live readiness",
    "- not capital authority",
    "- not trading authority",
    "- not methodology approval",
    "",
    "Section 1 Item 2",
    "item_type: research_return_observation_brief_item",
    (
        "headline: Research return observation SYNTH_ETF 2026-01-20: "
        "insufficient_return_history."
    ),
    (
        "summary: Research return observation metadata records "
        "insufficient_return_history for SYNTH_ETF as of 2026-01-20 using "
        "close_to_close_simple_return on synthetic_close, 1 eligible "
        "sample(s), 1 later sample(s) ignored, 0 return(s), positive count "
        "0, negative count 0, and zero count 0."
    ),
    "mechanical_state: insufficient_return_history",
    "positive_return_count: 0",
    "negative_return_count: 0",
    "zero_return_count: 0",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "Source Observation",
    "symbol: SYNTH_ETF",
    "as_of: 2026-01-20",
    "return_method: close_to_close_simple_return",
    "price_basis: synthetic_close",
    "sample_count: 2",
    "eligible_sample_count: 1",
    "ignored_future_sample_count: 1",
    "return_count: 0",
    "Return Points",
    "- none; insufficient_return_history has no close-to-close return points.",
    "Item Limitations",
    "- synthetic broad ETF close series for return mechanics only",
    "- fixed close samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "Item Non-Claims",
    "- not source/data approval",
    "- not adjusted-close/corporate-action completeness",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
    "- not backtesting validation",
    "- not allocation or order authority",
    "- not broker authority",
    "- not portfolio mutation authority",
    "- not paper readiness",
    "- not live readiness",
    "- not capital authority",
    "- not trading authority",
    "- not methodology approval",
)
_EXPECTED_RENDERED_TEXT = "\n".join(_EXPECTED_RENDERED_LINES)
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.research_return_observation_brief_container",
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
    _join("ra", "nk"),
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
    "account",
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("bro", "ker"),
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
_FORBIDDEN_PUBLIC_CONCEPTS = {
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
    _join("ra", "nking"),
    _join("recomm", "endation"),
    _join("read", "iness"),
    _join("sco", "re"),
    _join("sco", "ring"),
    "sell",
    "signal",
    _join("tra", "ding_authority"),
    "trading_ready",
}
_FORBIDDEN_POSITIVE_TEXT = (
    _join("app", "roved"),
    _join("app", "roval"),
    _join("recomm", "endation"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("read", "iness"),
    _join("tra", "ding authority"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    _join("action", "able"),
)


def test_renderer_accepts_phase_217_synthetic_brief_fixture() -> None:
    brief = build_synthetic_research_return_observation_brief()
    rendered = render_research_return_observation_brief_text(brief)

    assert type(brief) is ResearchReturnObservationBrief
    assert isinstance(rendered, str)
    assert rendered.startswith("Research Return Observation Brief\n")


def test_rendered_output_is_pinned_exactly() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )

    assert rendered == _EXPECTED_RENDERED_TEXT
    assert tuple(rendered.splitlines()) == _EXPECTED_RENDERED_LINES


def test_repeated_rendering_is_byte_for_byte_deterministic() -> None:
    brief = build_synthetic_research_return_observation_brief()
    first = render_research_return_observation_brief_text(brief)
    second = render_research_return_observation_brief_text(brief)

    assert first == second == _EXPECTED_RENDERED_TEXT
    assert first.encode("utf-8") == second.encode("utf-8")


def test_source_brief_to_dict_is_unchanged_before_and_after_rendering() -> None:
    brief = build_synthetic_research_return_observation_brief()
    before = brief.to_dict()

    render_research_return_observation_brief_text(brief)
    render_research_return_observation_brief_text(brief)

    assert before == expected_synthetic_research_return_observation_brief_dict()
    assert brief.to_dict() == before


def test_source_section_item_observation_and_return_identities_remain_unchanged() -> None:
    brief = build_synthetic_research_return_observation_brief()
    before = _identity_snapshot(brief)

    render_research_return_observation_brief_text(brief)
    render_research_return_observation_brief_text(brief)

    assert _identity_snapshot(brief) == before


def test_rendered_text_includes_both_research_return_mechanical_states() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )

    assert "mechanical_state: returns_constructed" in rendered
    assert "mechanical_state: insufficient_return_history" in rendered


def test_rendered_text_includes_return_count_metadata() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )

    assert "positive_return_count: 1" in rendered
    assert "negative_return_count: 1" in rendered
    assert "zero_return_count: 1" in rendered
    assert "positive_return_count: 0" in rendered
    assert "negative_return_count: 0" in rendered
    assert "zero_return_count: 0" in rendered


def test_rendered_text_includes_return_method_price_basis_and_future_count() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )

    assert rendered.count("return_method: close_to_close_simple_return") == 2
    assert rendered.count("price_basis: synthetic_close") == 2
    assert rendered.count("ignored_future_sample_count: 1") == 2


def test_rendered_text_includes_primary_return_points_in_order() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )
    lines = tuple(rendered.splitlines())

    first = lines.index("Return Point 1")
    second = lines.index("Return Point 2")
    third = lines.index("Return Point 3")

    assert first < second < third
    assert lines.index("start_date: 2026-01-15") < lines.index("simple_return: 0.05")
    assert lines.index("start_date: 2026-01-16") < lines.index("simple_return: -0.1")
    assert lines.index("start_date: 2026-01-19") < lines.index("simple_return: 0")


def test_rendered_text_includes_empty_return_wording() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )

    assert (
        "- none; insufficient_return_history has no close-to-close return points."
        in rendered
    )


def test_renderer_rejects_non_briefs_lookalikes_and_subclasses() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_research_return_observation_brief_dict()

    class BriefSubclass(ResearchReturnObservationBrief):
        pass

    source = build_synthetic_research_return_observation_brief()
    subclass = BriefSubclass(
        brief_type=source.brief_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        brief_id=source.brief_id,
        title=source.title,
        summary=source.summary,
        sections=source.sections,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )

    for value in (
        None,
        object(),
        {},
        expected_synthetic_research_return_observation_brief_dict(),
        Lookalike(),
        subclass,
    ):
        with pytest.raises(ValidationError, match="ResearchReturnObservationBrief"):
            render_research_return_observation_brief_text(value)


def test_production_renderer_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_no_from_dict_exists() -> None:
    assert not hasattr(render_research_return_observation_brief_text, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()
    assert "from_dict" not in _source_text()


def test_no_forbidden_public_renderer_concepts_appear() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )

    assert _FORBIDDEN_PUBLIC_CONCEPTS.isdisjoint(_renderer_concepts(rendered))


def test_no_positive_authority_or_actionability_language_appears() -> None:
    rendered = render_research_return_observation_brief_text(
        build_synthetic_research_return_observation_brief()
    )

    for line in rendered.splitlines():
        lowered = line.lower()
        if lowered.startswith("- not "):
            continue
        assert not any(token in lowered for token in _FORBIDDEN_POSITIVE_TEXT)


def test_renderer_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_renderer_module_has_no_forbidden_source_literals() -> None:
    lowered = _source_text().lower()

    assert [
        token for token in _FORBIDDEN_SOURCE_TOKENS if token in lowered
    ] == []


def _identity_snapshot(brief: ResearchReturnObservationBrief) -> tuple[int, ...]:
    section = brief.sections[0]
    first_item = section.items[0]
    second_item = section.items[1]
    first_observation = first_item.source_observation
    second_observation = second_item.source_observation

    return (
        id(brief),
        id(brief.sections),
        id(section),
        id(section.items),
        id(first_item),
        id(second_item),
        id(first_item.limitations),
        id(first_item.non_claims),
        id(second_item.limitations),
        id(second_item.non_claims),
        id(first_observation),
        id(first_observation.returns),
        *(id(return_point) for return_point in first_observation.returns),
        id(first_observation.limitations),
        id(first_observation.non_claims),
        id(second_observation),
        id(second_observation.returns),
        *(id(return_point) for return_point in second_observation.returns),
        id(second_observation.limitations),
        id(second_observation.non_claims),
        id(section.limitations),
        id(section.non_claims),
        id(brief.limitations),
        id(brief.non_claims),
    )


def _index(text: str, value: str) -> int:
    return text.index(value)


def _renderer_concepts(rendered: str) -> set[str]:
    concepts: set[str] = set()
    for line in rendered.splitlines():
        if line.startswith("- ") or ": " not in line:
            continue
        concepts.add(line.split(": ", maxsplit=1)[0])

    return concepts


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
