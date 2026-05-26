from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    AdvisoryOperatingBriefContentBundleExport,
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_package.py"
)
_PACKAGE_ID = "synthetic-advisory-operating-brief-package-001"
_TITLE = "Synthetic advisory operating brief package"
_SUMMARY = "Synthetic metadata bundle for a future morning brief handoff"
_AS_OF = "2026-05-24"
_EXPECTED_FIELD_NAMES = (
    "package_type",
    "status",
    "authority",
    "capital_authority",
    "package_id",
    "title",
    "summary",
    "as_of",
    "content_bundle",
    "content_bundle_export",
    "limitations",
    "non_claims",
    "sma_return_research_pipeline_observation",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.advisory_operating_brief_content_bundle",
    "algotrader.research.advisory_operating_brief_content_bundle_export",
    "algotrader.research.sma_return_research_pipeline_observation",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
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
    "langchain",
    "langgraph",
    _s("l", "lm"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    _s("path", "lib"),
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
    "from_dict",
    "getenv",
    "glob",
    "import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
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


def test_builds_package_with_fixed_advisory_metadata_and_export() -> None:
    bundle = _source_bundle()
    expected_export = export_advisory_operating_brief_content_bundle(bundle)

    package = _package(bundle)
    payload = package.to_dict()

    assert isinstance(package, AdvisoryOperatingBriefPackage)
    assert package.package_type == "advisory_operating_brief_package"
    assert package.status == "candidate_only"
    assert package.authority == "advisory_only"
    assert package.capital_authority is False
    assert package.package_id == _PACKAGE_ID
    assert package.title == _TITLE
    assert package.summary == _SUMMARY
    assert package.as_of == _AS_OF
    assert package.content_bundle is bundle
    assert package.content_bundle_export == expected_export
    assert payload["package_type"] == "advisory_operating_brief_package"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["content_bundle"] == bundle.to_dict()
    assert payload["content_bundle_export"] == {
        "payload": expected_export.payload,
        "json_text": expected_export.json_text,
        "rendered_text": expected_export.rendered_text,
    }


def test_direct_construction_validates_and_preserves_bundle_identity() -> None:
    bundle = _source_bundle()
    constructor_payload = _valid_constructor_payload(bundle)

    package = AdvisoryOperatingBriefPackage(**constructor_payload)

    assert package.content_bundle is bundle
    assert package.content_bundle_export == (
        export_advisory_operating_brief_content_bundle(bundle)
    )
    assert package.limitations == bundle.limitations
    assert package.non_claims == bundle.non_claims


def test_package_is_frozen_slotted_and_has_no_from_dict() -> None:
    package = _package()

    assert hasattr(AdvisoryOperatingBriefPackage, "__slots__")
    assert not hasattr(package, "__dict__")
    assert not hasattr(AdvisoryOperatingBriefPackage, "from_dict")
    assert "from_dict" not in _function_names()
    with pytest.raises(FrozenInstanceError):
        package.summary = "changed"


def test_exact_content_bundle_type_is_required() -> None:
    source = _source_bundle()
    subclass = _bundle_subclass(source)

    with pytest.raises(ValidationError, match="content_bundle"):
        build_advisory_operating_brief_package(
            package_id=_PACKAGE_ID,
            title=_TITLE,
            summary=_SUMMARY,
            as_of=_AS_OF,
            content_bundle=subclass,
        )

    with pytest.raises(ValidationError, match="content_bundle"):
        build_advisory_operating_brief_package(
            package_id=_PACKAGE_ID,
            title=_TITLE,
            summary=_SUMMARY,
            as_of=_AS_OF,
            content_bundle=_BundleLookalike(source),
        )


def test_content_bundle_export_type_and_values_are_validated() -> None:
    bundle = _source_bundle()
    constructor_payload = _valid_constructor_payload(bundle)
    expected_export = export_advisory_operating_brief_content_bundle(bundle)

    constructor_payload["content_bundle_export"] = _ExportLookalike(expected_export)
    with pytest.raises(ValidationError, match="content_bundle_export"):
        AdvisoryOperatingBriefPackage(**constructor_payload)

    constructor_payload = _valid_constructor_payload(bundle)
    constructor_payload["content_bundle_export"] = AdvisoryOperatingBriefContentBundleExport(
        payload={**expected_export.payload, "title": "changed copied payload"},
        json_text=expected_export.json_text,
        rendered_text=expected_export.rendered_text,
    )
    with pytest.raises(ValidationError, match="payload"):
        AdvisoryOperatingBriefPackage(**constructor_payload)

    constructor_payload = _valid_constructor_payload(bundle)
    constructor_payload["content_bundle_export"] = AdvisoryOperatingBriefContentBundleExport(
        payload=expected_export.payload,
        json_text="{}",
        rendered_text=expected_export.rendered_text,
    )
    with pytest.raises(ValidationError, match="json_text"):
        AdvisoryOperatingBriefPackage(**constructor_payload)

    constructor_payload = _valid_constructor_payload(bundle)
    constructor_payload["content_bundle_export"] = AdvisoryOperatingBriefContentBundleExport(
        payload=expected_export.payload,
        json_text=expected_export.json_text,
        rendered_text="changed copied payload",
    )
    with pytest.raises(ValidationError, match="rendered_text"):
        AdvisoryOperatingBriefPackage(**constructor_payload)


def test_export_payload_json_and_rendered_text_match_existing_export_behavior() -> None:
    bundle = _source_bundle()
    expected_export = export_advisory_operating_brief_content_bundle(bundle)
    package = _package(bundle)
    export_payload = _dict(package.to_dict()["content_bundle_export"])

    assert package.content_bundle_export.payload == expected_export.payload
    assert package.content_bundle_export.json_text == expected_export.json_text
    assert package.content_bundle_export.rendered_text == expected_export.rendered_text
    assert export_payload["payload"] == expected_export.payload
    assert export_payload["payload"] is not expected_export.payload
    assert export_payload["json_text"] == expected_export.json_text
    assert export_payload["rendered_text"] == expected_export.rendered_text


def test_repeated_construction_is_deterministic() -> None:
    bundle = _source_bundle()

    first = _package(bundle)
    second = _package(bundle)
    third = _package(_source_bundle())

    assert first == second == third
    assert first.to_dict() == second.to_dict() == third.to_dict()
    assert first.content_bundle_export.payload == second.content_bundle_export.payload
    assert first.content_bundle_export.json_text == second.content_bundle_export.json_text
    assert (
        first.content_bundle_export.rendered_text
        == second.content_bundle_export.rendered_text
    )
    assert first.to_dict()["as_of"] == _AS_OF


def test_source_bundle_and_export_are_not_mutated_by_package_serialization() -> None:
    bundle = _source_bundle()
    before_bundle_payload = bundle.to_dict()
    package = _package(bundle)
    before_export_payload = _primitive_copy(package.content_bundle_export.payload)
    payload = package.to_dict()
    exported_payload = _dict(_dict(payload["content_bundle_export"])["payload"])

    _list(_dict(payload["content_bundle"])["limitations"]).append(
        "changed primitive content copy"
    )
    _list(exported_payload["limitations"]).append("changed primitive export copy")
    _dict(payload["content_bundle"])["title"] = "changed primitive content copy"
    exported_payload["title"] = "changed primitive export copy"

    assert bundle.to_dict() == before_bundle_payload
    assert package.content_bundle is bundle
    assert package.content_bundle_export.payload == before_export_payload
    assert package.content_bundle_export.payload == (
        export_advisory_operating_brief_content_bundle(bundle).payload
    )


def test_to_dict_is_primitive_only_and_has_deterministic_top_level_order() -> None:
    payload = _package().to_dict()

    assert tuple(payload) == (
        "package_type",
        "status",
        "authority",
        "capital_authority",
        "package_id",
        "title",
        "summary",
        "as_of",
        "content_bundle",
        "content_bundle_export",
        "limitations",
        "non_claims",
    )
    _assert_primitive_only(payload)


def test_limitations_and_non_claims_carry_forward_with_first_seen_dedupe() -> None:
    bundle = _source_bundle()
    duplicated_limitations = (
        bundle.limitations[0],
        bundle.limitations[0],
        *bundle.limitations[1:],
    )
    duplicated_non_claims = (
        bundle.non_claims[0],
        bundle.non_claims[0],
        *bundle.non_claims[1:],
    )
    object.__setattr__(bundle, "limitations", duplicated_limitations)
    object.__setattr__(bundle, "non_claims", duplicated_non_claims)

    package = _package(bundle)

    assert package.limitations == _dedupe(duplicated_limitations)
    assert package.non_claims == _dedupe(duplicated_non_claims)
    assert package.to_dict()["limitations"] == list(_dedupe(duplicated_limitations))
    assert package.to_dict()["non_claims"] == list(_dedupe(duplicated_non_claims))


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("package_type", "advisory_operating_brief"),
        ("status", "draft"),
        ("authority", "research_only"),
        ("capital_authority", True),
        ("capital_authority", 0),
    ),
)
def test_fixed_metadata_is_rejected_when_malformed(
    field_name: str,
    value: object,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        AdvisoryOperatingBriefPackage(**constructor_payload)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("package_id", ""),
        ("package_id", " synthetic-package"),
        ("package_id", 123),
        ("title", ""),
        ("title", " Synthetic package"),
        ("title", object()),
        ("summary", ""),
        ("summary", " Synthetic package"),
        ("summary", object()),
        ("as_of", ""),
        ("as_of", " 2026-05-24"),
        ("as_of", object()),
    ),
)
def test_required_string_fields_reject_malformed_values(
    field_name: str,
    value: object,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        AdvisoryOperatingBriefPackage(**constructor_payload)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("package_id", _s("app", "roved-package")),
        ("title", _s("paper read", "iness handoff")),
        ("summary", _s("recomm", "endation package")),
        ("limitations", (_s("app", "roved for handoff"),)),
        ("non_claims", (_s("bro", "ker authority"),)),
    ),
)
def test_forbidden_authority_or_action_language_is_rejected(
    field_name: str,
    value: object,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        AdvisoryOperatingBriefPackage(**constructor_payload)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("limitations", ()),
        ("limitations", "not a tuple"),
        ("limitations", ("",)),
        ("limitations", (" synthetic limitation",)),
        ("non_claims", ()),
        ("non_claims", "not a tuple"),
        ("non_claims", ("",)),
        ("non_claims", ("synthetic negative claim is missing prefix",)),
    ),
)
def test_limitations_and_non_claims_reject_malformed_values(
    field_name: str,
    value: object,
) -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload[field_name] = value

    with pytest.raises(ValidationError, match=field_name):
        AdvisoryOperatingBriefPackage(**constructor_payload)


def test_carried_metadata_must_match_content_bundle() -> None:
    constructor_payload = _valid_constructor_payload()
    constructor_payload["limitations"] = (
        *constructor_payload["limitations"],
        "synthetic unmatched limitation",
    )
    with pytest.raises(ValidationError, match="limitations"):
        AdvisoryOperatingBriefPackage(**constructor_payload)

    constructor_payload = _valid_constructor_payload()
    constructor_payload["non_claims"] = (
        *constructor_payload["non_claims"],
        "not unmatched package claim",
    )
    with pytest.raises(ValidationError, match="non_claims"):
        AdvisoryOperatingBriefPackage(**constructor_payload)


def test_no_actionable_authority_fields_are_added() -> None:
    package = _package()
    field_names = {field.name for field in fields(AdvisoryOperatingBriefPackage)}
    payload_keys = set(package.to_dict())
    forbidden_fields = {
        "approved",
        "live_authorized",
        "paper_eligible",
        _s("allo", "cation"),
        _s("allo", "cation_authority"),
        _s("bro", "ker"),
        _s("or", "der"),
        _s("or", "der_authority"),
        _s("port", "folio"),
        _s("tra", "ding_authority"),
        "trading_ready",
    }

    assert tuple(field.name for field in fields(AdvisoryOperatingBriefPackage)) == (
        _EXPECTED_FIELD_NAMES
    )
    assert field_names.isdisjoint(forbidden_fields)
    assert payload_keys.isdisjoint(forbidden_fields)
    assert all(not hasattr(package, field_name) for field_name in forbidden_fields)


def test_production_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not name.startswith("tests") for name in imports)
    assert "tests.fixtures" not in imports


def test_module_imports_no_forbidden_dependencies() -> None:
    imports = _import_references()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_clock_network_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


class ContentBundleSubclass(AdvisoryOperatingBriefContentBundle):
    pass


class _BundleLookalike:
    def __init__(self, source: AdvisoryOperatingBriefContentBundle) -> None:
        self.bundle_type = source.bundle_type
        self.status = source.status
        self.authority = source.authority
        self.capital_authority = source.capital_authority
        self.title = source.title
        self.summary = source.summary
        self.limitations = source.limitations
        self.non_claims = source.non_claims

    def to_dict(self) -> dict[str, object]:
        return {}


class _ExportLookalike:
    def __init__(self, source: AdvisoryOperatingBriefContentBundleExport) -> None:
        self.payload = source.payload
        self.json_text = source.json_text
        self.rendered_text = source.rendered_text


def _source_bundle() -> AdvisoryOperatingBriefContentBundle:
    return build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()


def _package(
    bundle: AdvisoryOperatingBriefContentBundle | None = None,
) -> AdvisoryOperatingBriefPackage:
    return build_advisory_operating_brief_package(
        package_id=_PACKAGE_ID,
        title=_TITLE,
        summary=_SUMMARY,
        as_of=_AS_OF,
        content_bundle=bundle or _source_bundle(),
    )


def _valid_constructor_payload(
    bundle: AdvisoryOperatingBriefContentBundle | None = None,
) -> dict[str, object]:
    source = bundle or _source_bundle()
    package = _package(source)
    return {
        "package_type": package.package_type,
        "status": package.status,
        "authority": package.authority,
        "capital_authority": package.capital_authority,
        "package_id": package.package_id,
        "title": package.title,
        "summary": package.summary,
        "as_of": package.as_of,
        "content_bundle": package.content_bundle,
        "content_bundle_export": package.content_bundle_export,
        "limitations": package.limitations,
        "non_claims": package.non_claims,
    }


def _bundle_subclass(
    source: AdvisoryOperatingBriefContentBundle,
) -> ContentBundleSubclass:
    return ContentBundleSubclass(
        bundle_type=source.bundle_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        title=source.title,
        summary=source.summary,
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        limitations=source.limitations,
        non_claims=source.non_claims,
        risk_authority_briefs=source.risk_authority_briefs,
        research_queue_briefs=source.research_queue_briefs,
    )


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value in deduped:
            continue
        deduped.append(value)

    return tuple(deduped)


def _primitive_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _primitive_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_primitive_copy(item) for item in value]
    return value


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
