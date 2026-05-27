from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import algotrader.research.advisory_operating_brief_package_synthetic as synthetic_module
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_export import (
    export_advisory_operating_brief_package,
)
from tests.fixtures import advisory_operating_brief_package as fixture_module
from tests.fixtures.advisory_operating_brief_package import (
    build_synthetic_advisory_operating_brief_package,
    expected_synthetic_advisory_operating_brief_package_dict,
)
from tests.fixtures.sma_return_research_pipeline_observation import (
    expected_synthetic_sma_return_research_pipeline_observation_dict,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _primitive_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _primitive_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_primitive_copy(item) for item in value]
    return value


def _compact_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode(
        "ascii"
    )


FIXTURE_PATH = Path("tests/fixtures/advisory_operating_brief_package.py")
_PACKAGE_ID = "advisory-operating-brief-package:synthetic:2026-01-20"
_TITLE = "Synthetic advisory operating brief package"
_SUMMARY = "Advisory-only synthetic operating brief package content."
_AS_OF = "2026-01-20"
_EXPECTED_DICT = build_synthetic_advisory_operating_brief_package().to_dict()
_EXPECTED_CONTENT_BUNDLE_DICT = _primitive_copy(_EXPECTED_DICT["content_bundle"])
_EXPECTED_CONTENT_BUNDLE_EXPORT_DICT = _primitive_copy(
    _EXPECTED_DICT["content_bundle_export"]
)
_EXPECTED_SMA_RETURN_PIPELINE_DICT = (
    expected_synthetic_sma_return_research_pipeline_observation_dict()
)
_EXPECTED_COMPACT_JSON_BYTES = _compact_json_bytes(_EXPECTED_DICT)
_EXPECTED_FIELD_ORDER = tuple(_EXPECTED_DICT)
_TUPLE_FIELDS = ("limitations", "non_claims")
_BRANCH_KEYS = (
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "risk_authority_briefs",
    "research_queue_briefs",
    "sma_research_observation_briefs",
    "sma_research_summary_observations",
    "research_return_observation_briefs",
    "research_return_summary_observation_briefs",
    "research_data_source_readiness",
)
_FORBIDDEN_SERIALIZED_FIELD_NAMES = {
    "broker",
    "account",
    "order",
    "fill",
    "position",
    "portfolio",
    "cash",
    "equity",
    "pnl",
    "benchmark",
    "backtest",
    "allocation",
    "signal",
    "execution",
    "live",
    "paper",
    "approval",
}
_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.advisory_operating_brief_package",
    "algotrader.research.advisory_operating_brief_package_synthetic",
}
_ALLOWED_CALL_NAMES = {
    "build_synthetic_advisory_operating_brief_package",
    "build_synthetic_advisory_operating_brief_package_preview",
    "package.to_dict",
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
_FORBIDDEN_EXACT_LITERALS = {
    "approved",
    "paper",
    "live",
    "trading_ready",
    "trading-ready",
    "actionable",
    _s("allo", "cation"),
    _s("bro", "ker"),
    "account",
    _s("or", "der"),
    "fill",
    _s("port", "folio"),
    "ranking",
    "scoring",
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


def test_fixture_builder_returns_exact_package() -> None:
    package = build_synthetic_advisory_operating_brief_package()

    assert type(package) is AdvisoryOperatingBriefPackage
    assert tuple(package.to_dict()) == _EXPECTED_FIELD_ORDER
    assert package.to_dict() == _EXPECTED_DICT


def test_expected_dict_helper_matches_to_dict_exactly() -> None:
    package = build_synthetic_advisory_operating_brief_package()

    assert expected_synthetic_advisory_operating_brief_package_dict() == (
        package.to_dict()
    )
    assert expected_synthetic_advisory_operating_brief_package_dict() == (
        _EXPECTED_DICT
    )


def test_expected_dict_helper_returns_fresh_mutable_primitive_copies() -> None:
    first = expected_synthetic_advisory_operating_brief_package_dict()
    second = expected_synthetic_advisory_operating_brief_package_dict()
    first_export = _dict(first["content_bundle_export"])
    second_export = _dict(second["content_bundle_export"])

    assert first is not second
    assert first["content_bundle"] is not second["content_bundle"]
    assert first["content_bundle"] is not first_export["payload"]
    assert first["sma_return_research_pipeline_observation"] is not (
        second["sma_return_research_pipeline_observation"]
    )
    assert first_export is not second_export
    assert first_export["payload"] is not second_export["payload"]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]
    for branch_key in _BRANCH_KEYS:
        assert _dict(first["content_bundle"])[branch_key] is not (
            _dict(second["content_bundle"])[branch_key]
        )
        assert _list(_dict(first["content_bundle"])[branch_key])[0] is not (
            _list(_dict(second["content_bundle"])[branch_key])[0]
        )
    for field_name in _TUPLE_FIELDS:
        assert first[field_name] is not _dict(first["content_bundle"])[field_name]
        assert first[field_name] is not _dict(first_export["payload"])[field_name]

    _list(first["limitations"]).append("mutated primitive copy")
    _dict(first["content_bundle"])["title"] = "mutated primitive copy"
    _list(_dict(first_export["payload"])["non_claims"]).append(
        "not mutated primitive copy"
    )

    assert second == _EXPECTED_DICT
    assert expected_synthetic_advisory_operating_brief_package_dict() == _EXPECTED_DICT


def test_repeated_construction_and_compact_json_bytes_are_deterministic() -> None:
    first = build_synthetic_advisory_operating_brief_package()
    second = build_synthetic_advisory_operating_brief_package()
    third_payload = expected_synthetic_advisory_operating_brief_package_dict()

    assert first == second
    assert first is not second
    assert first.to_dict() == second.to_dict() == third_payload == _EXPECTED_DICT
    assert _compact_json_bytes(first.to_dict()) == _EXPECTED_COMPACT_JSON_BYTES
    assert _compact_json_bytes(second.to_dict()) == _EXPECTED_COMPACT_JSON_BYTES
    assert _compact_json_bytes(third_payload) == _EXPECTED_COMPACT_JSON_BYTES
    assert json.loads(_EXPECTED_COMPACT_JSON_BYTES.decode("ascii")) == _EXPECTED_DICT


def test_nested_content_bundle_promotes_sma_summary_branch() -> None:
    payload = build_synthetic_advisory_operating_brief_package().to_dict()
    content_bundle = _dict(payload["content_bundle"])
    summary = _dict(_list(content_bundle["sma_research_summary_observations"])[0])
    sma_brief = _dict(_list(content_bundle["sma_research_observation_briefs"])[0])
    sma_section = _dict(_list(sma_brief["sections"])[0])
    sma_sources = [
        _dict(item)["source_observation"]
        for item in _list(sma_section["items"])
    ]

    assert content_bundle == _EXPECTED_CONTENT_BUNDLE_DICT
    assert content_bundle["candidate_research_brief_count"] == 1
    assert content_bundle["strategy_eligibility_brief_count"] == 1
    assert content_bundle["risk_authority_brief_count"] == 1
    assert content_bundle["research_queue_brief_count"] == 1
    assert content_bundle["sma_research_observation_brief_count"] == 1
    assert content_bundle["sma_research_summary_observation_count"] == 1
    assert content_bundle["research_return_observation_brief_count"] == 1
    assert content_bundle["research_return_summary_observation_brief_count"] == 1
    assert tuple(branch_key for branch_key in _BRANCH_KEYS if branch_key in content_bundle) == (
        _BRANCH_KEYS
    )
    assert summary["observation_type"] == "sma_research_summary_observation"
    assert summary["status"] == "candidate_only"
    assert summary["authority"] == "advisory_only"
    assert summary["capital_authority"] is False
    assert summary["research_scope"] == "research_only"
    assert summary["summary_state"] == "observations_summarized"
    assert summary["total_observation_count"] == 2
    assert summary["above_sma_count"] == 1
    assert summary["below_sma_count"] == 0
    assert summary["equal_sma_count"] == 0
    assert summary["insufficient_history_count"] == 1
    assert _list(summary["source_observations"]) == sma_sources


def test_package_fixture_pins_phase_249_sma_return_pipeline_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    payload = package.to_dict()
    content_bundle = _dict(payload["content_bundle"])
    pipeline_payload = _dict(payload["sma_return_research_pipeline_observation"])
    pipeline = package.sma_return_research_pipeline_observation

    assert pipeline is not None
    assert pipeline_payload == pipeline.to_dict()
    assert pipeline_payload == _EXPECTED_SMA_RETURN_PIPELINE_DICT
    assert (
        pipeline_payload["return_construction_policy_observation"]
        == pipeline.return_construction_policy_observation.to_dict()
    )
    assert pipeline_payload["return_construction_policy_observation"] == (
        _EXPECTED_SMA_RETURN_PIPELINE_DICT["return_construction_policy_observation"]
    )
    assert _key_count(payload, "return_construction_policy_observation") == 1
    assert _key_count(pipeline_payload, "return_construction_policy_observation") == 1
    assert "sma_return_research_pipeline_observation" not in content_bundle
    assert tuple(branch_key for branch_key in _BRANCH_KEYS if branch_key in content_bundle) == (
        _BRANCH_KEYS
    )


def test_package_fixture_adds_no_forbidden_serialized_fields() -> None:
    payload = expected_synthetic_advisory_operating_brief_package_dict()

    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_SERIALIZED_FIELD_NAMES)


def test_nested_content_bundle_export_matches_payload_json_and_renderer() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    payload = package.to_dict()
    content_bundle = _dict(payload["content_bundle"])
    content_bundle_export = _dict(payload["content_bundle_export"])

    assert content_bundle_export["payload"] == content_bundle
    assert content_bundle_export["payload"] is not content_bundle
    assert json.loads(str(content_bundle_export["json_text"])) == content_bundle
    assert content_bundle_export["json_text"] == json.dumps(
        content_bundle,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert content_bundle_export == _EXPECTED_CONTENT_BUNDLE_EXPORT_DICT
    assert content_bundle_export["rendered_text"] == (
        package.content_bundle_export.rendered_text
    )


def test_fixture_export_payload_byte_matches_expected_package() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    exported = export_advisory_operating_brief_package(package)

    assert exported.payload == _EXPECTED_DICT
    assert _compact_json_bytes(exported.payload) == _EXPECTED_COMPACT_JSON_BYTES
    assert exported.payload == expected_synthetic_advisory_operating_brief_package_dict()


def test_package_builds_expected_content_bundle_from_research_return_summary_source(
    monkeypatch,
) -> None:
    source = build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation(
        include_risk_authority=True,
        include_research_queue=True,
        include_sma_research_observation=True,
        include_sma_research_summary_observation=True,
        include_research_return_observation=True,
    )

    def return_source(
        *,
        include_risk_authority: bool = False,
        include_research_queue: bool = False,
        include_sma_research_observation: bool = False,
        include_sma_research_summary_observation: bool = False,
        include_research_return_observation: bool = False,
    ):
        assert include_risk_authority is True
        assert include_research_queue is True
        assert include_sma_research_observation is True
        assert include_sma_research_summary_observation is True
        assert include_research_return_observation is True
        return source

    monkeypatch.setattr(
        synthetic_module,
        "build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation",
        return_source,
    )

    package = fixture_module.build_synthetic_advisory_operating_brief_package()

    assert package.content_bundle is not source
    assert package.content_bundle.candidate_research_briefs == (
        source.candidate_research_briefs
    )
    assert package.content_bundle.strategy_eligibility_briefs == (
        source.strategy_eligibility_briefs
    )
    assert package.content_bundle.risk_authority_briefs == source.risk_authority_briefs
    assert package.content_bundle.sma_research_observation_briefs == (
        source.sma_research_observation_briefs
    )
    assert package.content_bundle.sma_research_summary_observations == (
        source.sma_research_summary_observations
    )
    assert package.content_bundle.research_return_observation_briefs == (
        source.research_return_observation_briefs
    )
    assert package.content_bundle.research_return_summary_observation_briefs == (
        source.research_return_summary_observation_briefs
    )
    assert package.content_bundle.research_queue_briefs[0] is not (
        source.research_queue_briefs[0]
    )
    assert package.content_bundle.to_dict() == _EXPECTED_CONTENT_BUNDLE_DICT


def test_fixed_package_metadata_is_pinned() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    payload = package.to_dict()

    assert package.package_type == "advisory_operating_brief_package"
    assert package.status == "candidate_only"
    assert package.authority == "advisory_only"
    assert package.capital_authority is False
    assert package.package_id == _PACKAGE_ID
    assert package.title == _TITLE
    assert package.summary == _SUMMARY
    assert package.as_of == _AS_OF
    assert payload["package_id"] == _PACKAGE_ID
    assert payload["title"] == _TITLE
    assert payload["summary"] == _SUMMARY
    assert payload["as_of"] == _AS_OF


def test_limitations_and_non_claims_are_carried_forward() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    payload = package.to_dict()
    expected_limitations = tuple(_EXPECTED_CONTENT_BUNDLE_DICT["limitations"])
    expected_non_claims = tuple(_EXPECTED_CONTENT_BUNDLE_DICT["non_claims"])

    assert package.limitations == expected_limitations
    assert package.non_claims == expected_non_claims
    assert payload["limitations"] == list(expected_limitations)
    assert payload["non_claims"] == list(expected_non_claims)
    assert payload["limitations"] == _EXPECTED_CONTENT_BUNDLE_DICT["limitations"]
    assert payload["non_claims"] == _EXPECTED_CONTENT_BUNDLE_DICT["non_claims"]


def test_no_from_dict_exists() -> None:
    package = build_synthetic_advisory_operating_brief_package()

    assert not hasattr(AdvisoryOperatingBriefPackage, "from_dict")
    assert not hasattr(package, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_advisory_candidate_capital_false_metadata_is_preserved_recursively() -> None:
    payload = build_synthetic_advisory_operating_brief_package().to_dict()

    for item in _dict_nodes(payload):
        if "status" in item:
            assert item["status"] == "candidate_only"
        if "authority" in item:
            assert item["authority"] == "advisory_only"
        if "capital_authority" in item:
            assert item["capital_authority"] is False


def test_no_positive_actionable_authority_states_appear() -> None:
    payload = expected_synthetic_advisory_operating_brief_package_dict()

    for value in _string_values(payload):
        lowered = value.lower()
        if any(token in lowered for token in _AUTHORITY_LANGUAGE_TOKENS):
            assert _is_negative_advisory_text(lowered), value
    compact = json.dumps(payload, sort_keys=True, separators=(",", ":")).lower()
    assert '"approved"' not in compact
    assert '"paper"' not in compact
    assert '"live"' not in compact
    assert "trading-ready" not in compact
    assert "trading_ready" not in compact
    assert "actionable" not in compact


def test_fixture_module_imports_no_forbidden_paths() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert all(not module_name.startswith("src.") for module_name in imports)


def test_fixture_module_makes_no_forbidden_calls() -> None:
    call_names = _call_names()

    assert call_names == _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_module_literals_do_not_add_forbidden_behavior() -> None:
    literals = _string_literals()
    lowered_source = _source_text().lower()

    assert literals.isdisjoint(_FORBIDDEN_EXACT_LITERALS)
    for token in _FORBIDDEN_SOURCE_TOKENS:
        assert re.search(rf"(?<![a-z0-9_]){token}(?![a-z0-9_])", lowered_source) is None
    assert "from_dict" not in lowered_source


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


def _dict_nodes(value: object) -> tuple[dict[str, object], ...]:
    nodes: list[dict[str, object]] = []
    if isinstance(value, dict):
        nodes.append(value)
        for item in value.values():
            nodes.extend(_dict_nodes(item))
    elif isinstance(value, list):
        for item in value:
            nodes.extend(_dict_nodes(item))

    return tuple(nodes)


def _key_count(value: object, key: str) -> int:
    if isinstance(value, dict):
        return sum(
            (1 if item_key == key else 0) + _key_count(item_value, key)
            for item_key, item_value in value.items()
        )
    if isinstance(value, list):
        return sum(_key_count(item, key) for item in value)

    return 0


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_payload_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_payload_keys(item))
        return keys

    return set()


def _string_values(value: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, str):
        values.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            values.extend(_string_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_string_values(item))

    return tuple(values)


def _is_negative_advisory_text(value: str) -> bool:
    return (
        value.startswith(_NEGATIVE_TEXT_PREFIXES)
        or " not " in value
        or " before any " in value
        or " absent" in value
        or " missing" in value
        or " unresolved" in value
        or "diagnostic" in value
        or "research_data_source_readiness" in value
        or "readiness_state: candidate_only" in value
        or "synthetic_phase_271_readiness_fixture" in value
    )


def _source_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(FIXTURE_PATH))


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


def _string_literals() -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree())
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
