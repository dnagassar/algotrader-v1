from __future__ import annotations

import ast
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation_brief_container import (
    SmaResearchObservationBrief,
)
from algotrader.research.sma_research_observation_brief_renderer import (
    render_sma_research_observation_brief_text,
)
from tests.fixtures.sma_research_observation_brief_container import (
    build_synthetic_sma_research_observation_brief,
    expected_synthetic_sma_research_observation_brief_dict,
)


MODULE_PATH = Path("src/algotrader/research/sma_research_observation_brief_renderer.py")


def _join(*parts: str) -> str:
    return "".join(parts)


_EXPECTED_RENDERED_LINES = (
    "SMA Research Observation Brief",
    "brief_type: sma_research_observation_brief",
    "brief_id: sma-research-observation-brief:synthetic:broad-etf-sma",
    "title: Synthetic broad ETF SMA research observation brief",
    (
        "summary: Brief is advisory-only synthetic SMA observation content for broad "
        "ETF SMA mechanics."
    ),
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "section_count: 1",
    "",
    "Brief Limitations",
    "- synthetic broad ETF close series for fixture mechanics only",
    "- fixed date samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "",
    "Brief Non-Claims",
    "- not strategy approval",
    "- not source/data approval",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
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
    "section_type: sma_research_observation_brief_section",
    "section_id: sma-research-observation-section:synthetic:broad-etf-sma",
    "title: Synthetic broad ETF SMA observation summary",
    (
        "summary: Section is advisory-only synthetic SMA observation content for "
        "broad ETF SMA mechanics."
    ),
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "item_count: 2",
    "Section Limitations",
    "- synthetic broad ETF close series for fixture mechanics only",
    "- fixed date samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "Section Non-Claims",
    "- not strategy approval",
    "- not source/data approval",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
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
    "item_type: sma_research_observation_brief_item",
    "headline: SMA observation SYNTH_ETF 2026-01-20: above_sma_observation.",
    (
        "summary: SMA observation metadata records above_sma_observation for "
        "SYNTH_ETF as of 2026-01-20 with window 3, 3 eligible sample(s), "
        "1 later sample(s) ignored, latest close 110.00, SMA 100.00, "
        "distance 10.00, and distance pct 0.1."
    ),
    "mechanical_state: above_sma_observation",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "Source Observation",
    "symbol: SYNTH_ETF",
    "as_of: 2026-01-20",
    "window: 3",
    "sample_count: 4",
    "eligible_sample_count: 3",
    "ignored_future_sample_count: 1",
    "latest_close: 110.00",
    "sma_value: 100.00",
    "distance_from_sma: 10.00",
    "distance_from_sma_pct: 0.1",
    "position_vs_sma: above",
    "Item Limitations",
    "- synthetic broad ETF close series for fixture mechanics only",
    "- fixed date samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "Item Non-Claims",
    "- not strategy approval",
    "- not source/data approval",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
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
    "item_type: sma_research_observation_brief_item",
    "headline: SMA observation SYNTH_ETF 2026-01-20: insufficient_history.",
    (
        "summary: SMA observation metadata records insufficient_history for "
        "SYNTH_ETF as of 2026-01-20 with window 3, 2 eligible sample(s), "
        "1 later sample(s) ignored, latest close 101.00, SMA none, distance "
        "none, and distance pct none."
    ),
    "mechanical_state: insufficient_history",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "Source Observation",
    "symbol: SYNTH_ETF",
    "as_of: 2026-01-20",
    "window: 3",
    "sample_count: 3",
    "eligible_sample_count: 2",
    "ignored_future_sample_count: 1",
    "latest_close: 101.00",
    "sma_value: null",
    "distance_from_sma: null",
    "distance_from_sma_pct: null",
    "position_vs_sma: insufficient_history",
    "Item Limitations",
    "- synthetic broad ETF close series for fixture mechanics only",
    "- fixed date samples with later samples ignored by the builder",
    "- candidate-only advisory research metadata with no system connection",
    "Item Non-Claims",
    "- not strategy approval",
    "- not source/data approval",
    "- not predictive validity",
    "- not profitability",
    "- not a recommendation",
    "- not signal or evaluator behavior",
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
    "algotrader.research.sma_research_observation_brief_container",
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
    "pathlib",
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
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("bro", "ker"),
    "account",
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
    "ranking",
    _join("recomm", "endation"),
    "readiness",
    "score",
    "scoring",
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


def test_renderer_accepts_phase_202_synthetic_brief_fixture() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    rendered = render_sma_research_observation_brief_text(brief)

    assert type(brief) is SmaResearchObservationBrief
    assert isinstance(rendered, str)
    assert rendered.startswith("SMA Research Observation Brief\n")


def test_rendered_output_is_pinned_exactly() -> None:
    rendered = render_sma_research_observation_brief_text(
        build_synthetic_sma_research_observation_brief()
    )

    assert rendered == _EXPECTED_RENDERED_TEXT
    assert tuple(rendered.splitlines()) == _EXPECTED_RENDERED_LINES


def test_repeated_rendering_is_byte_for_byte_deterministic() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    first = render_sma_research_observation_brief_text(brief)
    second = render_sma_research_observation_brief_text(brief)

    assert first == second == _EXPECTED_RENDERED_TEXT
    assert first.encode("utf-8") == second.encode("utf-8")


def test_source_brief_to_dict_is_unchanged_before_and_after_rendering() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    before = brief.to_dict()

    render_sma_research_observation_brief_text(brief)
    render_sma_research_observation_brief_text(brief)

    assert before == expected_synthetic_sma_research_observation_brief_dict()
    assert brief.to_dict() == before


def test_source_section_item_and_observation_identities_remain_unchanged() -> None:
    brief = build_synthetic_sma_research_observation_brief()
    before = _identity_snapshot(brief)

    render_sma_research_observation_brief_text(brief)
    render_sma_research_observation_brief_text(brief)

    assert _identity_snapshot(brief) == before


def test_rendered_text_includes_both_mechanical_states() -> None:
    rendered = render_sma_research_observation_brief_text(
        build_synthetic_sma_research_observation_brief()
    )

    assert "mechanical_state: above_sma_observation" in rendered
    assert "mechanical_state: insufficient_history" in rendered
    assert "position_vs_sma: above" in rendered
    assert "position_vs_sma: insufficient_history" in rendered


def test_rendered_text_includes_future_sample_count_and_null_distance_fields() -> None:
    rendered = render_sma_research_observation_brief_text(
        build_synthetic_sma_research_observation_brief()
    )

    assert rendered.count("ignored_future_sample_count: 1") == 2
    assert "sma_value: null" in rendered
    assert "distance_from_sma: null" in rendered
    assert "distance_from_sma_pct: null" in rendered


def test_renderer_rejects_non_briefs_lookalikes_and_subclasses() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_sma_research_observation_brief_dict()

    class BriefSubclass(SmaResearchObservationBrief):
        pass

    source = build_synthetic_sma_research_observation_brief()
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
        expected_synthetic_sma_research_observation_brief_dict(),
        Lookalike(),
        subclass,
    ):
        with pytest.raises(ValidationError, match="SmaResearchObservationBrief"):
            render_sma_research_observation_brief_text(value)


def test_production_renderer_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_no_from_dict_exists() -> None:
    assert not hasattr(render_sma_research_observation_brief_text, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()
    assert "from_dict" not in _source_text()


def test_no_forbidden_public_renderer_concepts_appear() -> None:
    rendered = render_sma_research_observation_brief_text(
        build_synthetic_sma_research_observation_brief()
    )

    assert _FORBIDDEN_PUBLIC_CONCEPTS.isdisjoint(_renderer_concepts(rendered))


def test_no_positive_authority_or_actionability_language_appears() -> None:
    rendered = render_sma_research_observation_brief_text(
        build_synthetic_sma_research_observation_brief()
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


def _identity_snapshot(brief: SmaResearchObservationBrief) -> tuple[int, ...]:
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
        id(first_observation.limitations),
        id(first_observation.non_claims),
        id(second_observation),
        id(second_observation.limitations),
        id(second_observation.non_claims),
        id(section.limitations),
        id(section.non_claims),
        id(brief.limitations),
        id(brief.non_claims),
    )


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
