from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_renderer import (
    render_advisory_operating_brief_package_text,
)
from tests.fixtures.advisory_operating_brief_package import (
    build_synthetic_advisory_operating_brief_package,
    expected_synthetic_advisory_operating_brief_package_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _bullet_lines(values: object) -> tuple[str, ...]:
    assert isinstance(values, list)

    return tuple(f"- {value}" for value in values)


def _primitive_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _primitive_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_primitive_copy(item) for item in value]
    return value


MODULE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_package_renderer.py"
)
_EXPECTED_PACKAGE_DICT = expected_synthetic_advisory_operating_brief_package_dict()
_EXPECTED_CONTENT_BUNDLE_EXPORT = _dict(
    _EXPECTED_PACKAGE_DICT["content_bundle_export"]
)
_EXPECTED_NESTED_RENDERED_TEXT = str(_EXPECTED_CONTENT_BUNDLE_EXPORT["rendered_text"])
_EXPECTED_PREFIX_LINES = (
    "Advisory Operating Brief Package",
    "package_type: advisory_operating_brief_package",
    "package_id: advisory-operating-brief-package:synthetic:2026-01-20",
    "title: Synthetic advisory operating brief package",
    "summary: Advisory-only synthetic operating brief package content.",
    "as_of: 2026-01-20",
    "status: candidate_only",
    "authority: advisory_only",
    "capital_authority: False",
    "",
    "Content Bundle",
)
_EXPECTED_SUFFIX_LINES = (
    "",
    "Package Limitations",
    *_bullet_lines(_EXPECTED_PACKAGE_DICT["limitations"]),
    "",
    "Package Non-Claims",
    *_bullet_lines(_EXPECTED_PACKAGE_DICT["non_claims"]),
)
_EXPECTED_RENDERED_LINES = (
    *_EXPECTED_PREFIX_LINES,
    *_EXPECTED_NESTED_RENDERED_TEXT.splitlines(),
    *_EXPECTED_SUFFIX_LINES,
)
_EXPECTED_RENDERED_TEXT = "\n".join(_EXPECTED_RENDERED_LINES)
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_package",
}
_ALLOWED_CALL_NAMES = {
    "_append_values",
    "_LINE_BREAK.join",
    "chr",
    "lines.append",
    "lines.extend",
    "package.to_dict",
    "type",
    "ValidationError",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.backtest",
    "algotrader.backtesting",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.dashboard",
    _s("algotrader.", "data", "base"),
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
    "httpx",
    "ipynb",
    "joblib",
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
    _s("sk", "learn"),
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
    _s("cli", "ent"),
    _s("con", "nect"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "exists",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
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
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
_FORBIDDEN_SOURCE_TOKENS = (
    "approved",
    "actionable",
    _s("allo", "cation"),
    _s("bro", "ker"),
    "account",
    _s("or", "der"),
    "fill",
    _s("port", "folio"),
    "paper",
    "live",
    "ranking",
    "scoring",
    "credential",
    "dashboard",
    _s("sche", "duler"),
    _s("so", "cket"),
    "vendor",
    "notebook",
    "llm",
    "agent",
)
_AUTHORITY_LANGUAGE_TOKENS = (
    "approval",
    "approved",
    _s("recomm", "end"),
    "ranking",
    "scoring",
    "paper",
    "live",
    "readiness",
    "actionable",
    _s("allo", "cation"),
    _s("or", "der"),
    _s("bro", "ker"),
    "account",
    _s("port", "folio"),
    "capital authority",
    "trading authority",
    "trading ready",
    "trading-ready",
    "trading_ready",
)
_NEGATIVE_TEXT_PREFIXES = (
    "not ",
    "no ",
    "does not ",
    "do not ",
    "without ",
    "non-",
)


class _ExpectedPackageLookalike:
    def to_dict(self) -> dict[str, object]:
        return expected_synthetic_advisory_operating_brief_package_dict()


def test_renderer_accepts_phase_189_synthetic_package_fixture() -> None:
    package = build_synthetic_advisory_operating_brief_package()

    rendered = render_advisory_operating_brief_package_text(package)

    assert type(package) is AdvisoryOperatingBriefPackage
    assert rendered == _EXPECTED_RENDERED_TEXT
    assert tuple(rendered.splitlines()) == _EXPECTED_RENDERED_LINES


def test_repeated_rendering_is_byte_for_byte_deterministic() -> None:
    package = build_synthetic_advisory_operating_brief_package()

    first = render_advisory_operating_brief_package_text(package)
    second = render_advisory_operating_brief_package_text(package)
    third = render_advisory_operating_brief_package_text(
        build_synthetic_advisory_operating_brief_package()
    )

    assert first == second == third == _EXPECTED_RENDERED_TEXT
    assert first.encode("utf-8") == second.encode("utf-8") == third.encode("utf-8")


def test_rendering_does_not_mutate_package_bundle_or_export_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    source_bundle = package.content_bundle
    before = package.to_dict()
    before_export_payload = _primitive_copy(package.content_bundle_export.payload)

    rendered = render_advisory_operating_brief_package_text(package)

    assert rendered == _EXPECTED_RENDERED_TEXT
    assert package.to_dict() == before
    assert package.content_bundle is source_bundle
    assert package.content_bundle.to_dict() == before["content_bundle"]
    assert package.content_bundle_export.payload == before_export_payload


def test_rendered_output_embeds_stored_content_bundle_rendered_text_exactly() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    package_payload = package.to_dict()
    content_bundle_export = _dict(package_payload["content_bundle_export"])
    nested_rendered = str(content_bundle_export["rendered_text"])

    rendered = render_advisory_operating_brief_package_text(package)

    assert nested_rendered == _EXPECTED_NESTED_RENDERED_TEXT
    assert "SMA Research Observation Briefs" in nested_rendered
    assert "SMA Research Summary Observations" in nested_rendered
    assert "Research Return Observation Briefs" in nested_rendered
    assert "Research Return Summary Observation Briefs" in nested_rendered
    assert "Advisory Sections" in nested_rendered
    assert "sma_research_observation_brief_count: 1" in nested_rendered
    assert "sma_research_summary_observation_count: 1" in nested_rendered
    assert "research_return_observation_brief_count: 1" in nested_rendered
    assert "research_return_summary_observation_brief_count: 1" in nested_rendered
    assert "advisory_section_count: 11" in nested_rendered
    assert rendered == (
        "\n".join(_EXPECTED_PREFIX_LINES)
        + "\n"
        + nested_rendered
        + "\n"
        + "\n".join(_EXPECTED_SUFFIX_LINES)
    )
    assert content_bundle_export["payload"] == package_payload["content_bundle"]


def test_rendered_output_includes_all_nested_brief_branches() -> None:
    rendered = render_advisory_operating_brief_package_text(
        build_synthetic_advisory_operating_brief_package()
    )

    assert "Candidate Research Briefs" in rendered
    assert "Strategy Eligibility Briefs" in rendered
    assert "Risk Authority Briefs" in rendered
    assert "Research Queue Briefs" in rendered
    assert "SMA Research Observation Briefs" in rendered
    assert "SMA Research Summary Observations" in rendered
    assert "Research Return Observation Briefs" in rendered
    assert "Research Return Summary Observation Briefs" in rendered
    assert "Advisory Sections" in rendered
    assert "candidate_research_brief_count: 1" in rendered
    assert "strategy_eligibility_brief_count: 1" in rendered
    assert "risk_authority_brief_count: 1" in rendered
    assert "research_queue_brief_count: 1" in rendered
    assert "sma_research_observation_brief_count: 1" in rendered
    assert "sma_research_summary_observation_count: 1" in rendered
    assert "research_return_observation_brief_count: 1" in rendered
    assert "research_return_summary_observation_brief_count: 1" in rendered
    assert "advisory_section_count: 11" in rendered


@pytest.mark.parametrize(
    "value",
    (
        None,
        {},
        _ExpectedPackageLookalike(),
    ),
)
def test_renderer_rejects_non_package_inputs(value: object) -> None:
    with pytest.raises(ValidationError, match="AdvisoryOperatingBriefPackage"):
        render_advisory_operating_brief_package_text(value)


def test_renderer_rejects_subclass_instances() -> None:
    package = _package_subclass(build_synthetic_advisory_operating_brief_package())

    with pytest.raises(ValidationError, match="AdvisoryOperatingBriefPackage"):
        render_advisory_operating_brief_package_text(package)


def test_renderer_reads_package_dict_not_nested_package_objects() -> None:
    assert _package_attribute_names() == ("to_dict",)
    assert "content_bundle_export" not in _package_attribute_names()
    assert "content_bundle" not in _package_attribute_names()


def test_production_renderer_imports_no_tests_or_forbidden_paths() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_production_renderer_makes_no_forbidden_calls() -> None:
    call_names = _call_names()

    assert call_names == _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_no_from_dict_exists() -> None:
    assert not hasattr(AdvisoryOperatingBriefPackage, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()
    assert "from_dict" not in _source_text()


def test_production_renderer_literals_do_not_add_forbidden_behavior() -> None:
    lowered_source = _source_text().lower()

    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered_source) is None


def test_rendered_output_has_no_positive_actionable_authority_language() -> None:
    rendered = render_advisory_operating_brief_package_text(
        build_synthetic_advisory_operating_brief_package()
    )

    for line in rendered.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in _AUTHORITY_LANGUAGE_TOKENS):
            assert _is_negative_advisory_text(lowered), line


class PackageSubclass(AdvisoryOperatingBriefPackage):
    pass


def _package_subclass(
    source: AdvisoryOperatingBriefPackage,
) -> PackageSubclass:
    return PackageSubclass(
        package_type=source.package_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        package_id=source.package_id,
        title=source.title,
        summary=source.summary,
        as_of=source.as_of,
        content_bundle=source.content_bundle,
        content_bundle_export=source.content_bundle_export,
        limitations=source.limitations,
        non_claims=source.non_claims,
    )


def _is_negative_advisory_text(value: str) -> bool:
    text = value[2:] if value.startswith("- ") else value
    return (
        text.startswith(_NEGATIVE_TEXT_PREFIXES)
        or " not " in text
        or " before any " in text
        or " absent" in text
        or " missing" in text
        or " unresolved" in text
        or "diagnostic" in text
        or "research_data_source_readiness" in text
        or "readiness_state: candidate_only" in text
        or "synthetic_phase_271_readiness_fixture" in text
    )


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


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _package_attribute_names() -> tuple[str, ...]:
    return tuple(
        node.attr
        for node in ast.walk(_tree())
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "package"
    )
