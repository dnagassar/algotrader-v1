from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
    build_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)
from algotrader.research.research_observation_manifest import (
    ResearchObservationManifest,
    build_research_observation_manifest,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
)


PACKAGE_SOURCE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_package.py"
)
SYNTHETIC_SOURCE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_package_synthetic.py"
)
_OBSERVATION_NAME = "sma_return_research_pipeline_observation"

_ALLOWED_PACKAGE_IMPORTS = {
    "__future__": ("annotations",),
    "dataclasses": ("dataclass",),
    "algotrader.errors": ("ValidationError",),
    "algotrader.research.advisory_operating_brief_content_bundle": (
        "AdvisoryOperatingBriefContentBundle",
    ),
    "algotrader.research.advisory_operating_brief_content_bundle_export": (
        "AdvisoryOperatingBriefContentBundleExport",
        "export_advisory_operating_brief_content_bundle",
    ),
    "algotrader.research.research_observation_manifest": (
        "ResearchObservationManifest",
    ),
    "algotrader.research.sma_return_research_pipeline_observation": (
        "SmaReturnResearchPipelineObservation",
    ),
}
_ALLOWED_SYNTHETIC_IMPORTS = {
    "__future__": ("annotations",),
    "decimal": ("Decimal",),
    "algotrader.research.advisory_operating_brief_content_bundle": (
        "AdvisoryOperatingBriefContentBundle",
        "build_advisory_operating_brief_content_bundle",
    ),
    "algotrader.research.advisory_operating_brief_content_bundle_cli": (
        "build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation",
    ),
    "algotrader.research.advisory_operating_brief_diagnostic_issue": (
        "build_advisory_operating_brief_diagnostic_issues",
    ),
    "algotrader.research.advisory_operating_brief_package": (
        "AdvisoryOperatingBriefPackage",
        "build_advisory_operating_brief_package",
    ),
    "algotrader.research.research_queue_brief": (
        "ResearchQueueBrief",
        "build_research_queue_brief",
    ),
    "algotrader.research.research_queue_brief_item": (
        "build_research_queue_brief_item",
    ),
    "algotrader.research.research_queue_brief_section": (
        "build_research_queue_brief_section",
    ),
    "algotrader.research.research_queue_status": (
        "build_research_queue_status",
    ),
    "algotrader.research.research_data_source_readiness": (
        "ResearchDataSourceReadiness",
        "build_research_data_source_readiness",
    ),
    "algotrader.research.research_data_source_readiness_summary": (
        "ResearchDataSourceReadinessSummary",
        "build_research_data_source_readiness_summary",
    ),
    "algotrader.research.research_return_observation": (
        "ResearchReturnPricePoint",
        "ResearchReturnSeriesObservation",
        "build_research_return_series_observation",
    ),
    "algotrader.research.research_observation_manifest": (
        "build_research_observation_manifest",
    ),
    "algotrader.research.sma_conditional_return_selection_observation": (
        "build_sma_conditional_return_selection_observation",
    ),
    "algotrader.research.sma_conditional_return_selection_summary_observation": (
        "build_sma_conditional_return_selection_summary_observation",
    ),
    "algotrader.research.sma_research_observation": (
        "SmaResearchObservation",
        "SmaResearchPricePoint",
        "build_sma_research_observation",
    ),
    "algotrader.research.sma_return_alignment_observation": (
        "build_sma_return_alignment_observation",
    ),
    "algotrader.research.sma_return_alignment_summary_observation": (
        "build_sma_return_alignment_summary_observation",
    ),
    "algotrader.research.sma_return_research_pipeline_observation": (
        "SmaReturnResearchPipelineObservation",
        "build_sma_return_research_pipeline_observation",
    ),
    "algotrader.research.sma_selected_source_return_series_observation": (
        "build_sma_selected_source_return_series_observation",
    ),
    "algotrader.research.sma_selected_source_return_summary_observation": (
        "build_sma_selected_source_return_summary_observation",
    ),
}
_FORBIDDEN_PACKAGE_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.agent",
    "algotrader.agents",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.cli",
    "algotrader.config",
    "algotrader.core.config",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.research.research_observation_manifest_export",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "algotrader.storage",
    "algotrader.vendor",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "click",
    "database",
    "duckdb",
    "google.generativeai",
    "httpx",
    "joblib",
    "langchain",
    "langgraph",
    "llm",
    "network",
    "openai",
    "os",
    "pathlib",
    "requests",
    "sklearn",
    "socket",
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
)
_FORBIDDEN_SYNTHETIC_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.agent",
    "algotrader.agents",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.config",
    "algotrader.core.config",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.research.research_observation_manifest_export",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "algotrader.storage",
    "algotrader.vendor",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "google.generativeai",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "network",
    "openai",
    "os",
    "pathlib",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
    "urllib",
)
_FORBIDDEN_SMA_EXPORT_IMPORT_PREFIXES = (
    "algotrader.research.sma_conditional_return_selection_observation_export",
    "algotrader.research.sma_conditional_return_selection_summary_observation_export",
    "algotrader.research.sma_research_observation_export",
    "algotrader.research.sma_return_alignment_observation_export",
    "algotrader.research.sma_return_alignment_summary_observation_export",
    "algotrader.research.sma_return_research_pipeline_observation_export",
    "algotrader.research.sma_selected_source_return_series_observation_export",
    "algotrader.research.sma_selected_source_return_summary_observation_export",
)
_FORBIDDEN_IMPORT_FRAGMENTS = (
    "_renderer",
    "manifest_export",
    "manifest_snapshot",
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    "add_argument",
    "add_parser",
    "client",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "eval",
    "exec",
    "exists",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    "ingest",
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
    "main",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "parse_args",
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    "request",
    "requests.get",
    "rglob",
    "save",
    "set_defaults",
    "socket.create_connection",
    "socket.socket",
    "stat",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}
_FORBIDDEN_REFERENCE_NAMES = {
    "account",
    "aiohttp",
    "alpaca",
    "broker",
    "client",
    "config",
    "credential",
    "env",
    "environ",
    "fill",
    "from_dict",
    "httpx",
    "network",
    "open",
    "order",
    "os",
    "path",
    "pathlib",
    "portfolio",
    "read_text",
    "requests",
    "runtime",
    "secret",
    "socket",
    "storage",
    "trading_authority",
    "urllib",
    "vendor",
    "write",
}
_FORBIDDEN_SIGNATURE_PARAMETER_FRAGMENTS = (
    "broker",
    "client",
    "config",
    "credential",
    "env",
    "file",
    "network",
    "path",
    "runtime",
    "storage",
    "vendor",
)
_FORBIDDEN_SOURCE_TOKENS = (
    "alpaca",
    "broker",
    "order",
    "fill",
    "portfolio",
    "account",
    "credential",
    "secret",
    "token",
    "socket",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "pathlib",
    "open(",
    "write",
    "read_text",
    "from_dict",
    "approved",
    "readiness",
    "recommendation",
    "trading_authority",
    "capital_authority=True",
)
_EXPECTED_READINESS_PAYLOAD_KEYS = (
    "contract_type",
    "schema_version",
    "source_id",
    "source_name",
    "asset_class_scope",
    "intended_use",
    "readiness_state",
    "required_controls",
    "satisfied_controls",
    "missing_controls",
    "evidence_refs",
    "limitations",
    "non_claims",
)
_EXPECTED_READINESS_SUMMARY_PAYLOAD_KEYS = (
    "summary_type",
    "schema_version",
    "summary_scope",
    "summary_state",
    "required_control_count",
    "satisfied_control_count",
    "missing_control_count",
    "diagnostic_limitations",
)
_FORBIDDEN_READINESS_PAYLOAD_KEYS = {
    "account",
    "approved",
    "authorization_status",
    "broker",
    "credential",
    "digest",
    "endpoint",
    "fill",
    "order",
    "portfolio",
    "raw_payload",
    "recommendation",
    "score",
    "source_payload",
    "timestamp",
    "token",
    "trading_authority",
    "trading_ready",
    "vendor",
    "wrapper",
}
_FORBIDDEN_READINESS_SUMMARY_PAYLOAD_KEYS = _FORBIDDEN_READINESS_PAYLOAD_KEYS | {
    "approval_status",
    "authorization_status",
    "raw_payload",
    "source_authorized",
    "source_readiness",
}
_PACKAGE_SOURCE_TOKEN_ALLOWLIST = {
    "account": ('"account",',),
    "token": ("token in lowered for token in",),
    "readiness": (
        "must not imply approval, recommendation, readiness",
        "readiness, or authority.",
    ),
    "recommendation": (
        "must not imply approval, recommendation, readiness",
        "must not imply approval, recommendation",
    ),
}
_SYNTHETIC_SOURCE_TOKEN_ALLOWLIST = {
    "readiness": (
        "algotrader.research.research_data_source_readiness",
        "ResearchDataSourceReadiness",
        "build_research_data_source_readiness",
        "algotrader.research.research_data_source_readiness_summary",
        "ResearchDataSourceReadinessSummary",
        "build_research_data_source_readiness_summary",
        "_DATA_SOURCE_REQUIRED_CONTROLS",
        "_DATA_SOURCE_SATISFIED_CONTROLS",
        "_DATA_SOURCE_EVIDENCE_REFS",
        "_build_package_research_data_source_readiness",
        "_build_package_research_data_source_readiness_summary",
        "synthetic_phase_271_readiness_fixture",
        "readiness_state=\"candidate_only\"",
        "research_data_source_readiness=(",
        "research_data_source_readiness_summaries=(",
    ),
}


def test_package_imports_generic_manifest_without_snapshot_or_runtime_layers() -> None:
    import_details = _import_details_from_path(PACKAGE_SOURCE_PATH)
    imports = set(import_details)

    assert import_details == _ALLOWED_PACKAGE_IMPORTS
    assert import_details["algotrader.research.research_observation_manifest"] == (
        "ResearchObservationManifest",
    )
    assert "algotrader.research.research_observation_manifest_export" not in imports
    assert _matching_imports(imports, _FORBIDDEN_PACKAGE_IMPORT_PREFIXES) == []
    assert _matching_imports(imports, _FORBIDDEN_SMA_EXPORT_IMPORT_PREFIXES) == []
    assert _fragment_import_matches(imports, _FORBIDDEN_IMPORT_FRAGMENTS) == []
    assert all(not module_name.startswith("tests.") for module_name in imports)


def test_package_builder_stays_metadata_only_with_exact_manifest_type() -> None:
    signature = inspect.signature(build_advisory_operating_brief_package)
    manifest = _manifest()

    assert tuple(signature.parameters) == (
        "package_id",
        "title",
        "summary",
        "as_of",
        "content_bundle",
        "sma_return_research_pipeline_observation",
        "research_observation_manifest",
    )
    assert _signature_parameter_violations(signature) == []
    assert signature.parameters["research_observation_manifest"].default is None

    for value in (
        _ManifestLookalike(manifest),
        _manifest_subclass(manifest),
        {"manifest_type": "research_observation_manifest"},
    ):
        with pytest.raises(ValidationError, match="research_observation_manifest"):
            _package(research_observation_manifest=value)


def test_package_to_dict_serializes_manifest_only_when_present() -> None:
    manifest = _manifest()
    without_manifest = _package()
    with_manifest = _package(research_observation_manifest=manifest)
    with_manifest_payload = with_manifest.to_dict()

    assert without_manifest.research_observation_manifest is None
    assert "research_observation_manifest" not in without_manifest.to_dict()
    assert with_manifest.research_observation_manifest is manifest
    assert with_manifest_payload["research_observation_manifest"] == manifest.to_dict()
    assert _manifest_assignment_is_guarded_by_presence_check(PACKAGE_SOURCE_PATH)


def test_package_source_adds_no_forbidden_tokens_calls_or_surfaces() -> None:
    source = _source_text_from_path(PACKAGE_SOURCE_PATH)
    calls = _call_names_from_path(PACKAGE_SOURCE_PATH)
    references = _reference_names_from_path(PACKAGE_SOURCE_PATH)

    assert (
        _forbidden_source_token_matches(
            source,
            _FORBIDDEN_SOURCE_TOKENS,
            _PACKAGE_SOURCE_TOKEN_ALLOWLIST,
        )
        == []
    )
    assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert references.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)
    assert _function_names_from_path(PACKAGE_SOURCE_PATH).isdisjoint({"from_dict"})


def test_synthetic_imports_manifest_builder_without_runtime_trading_surfaces() -> None:
    import_details = _import_details_from_path(SYNTHETIC_SOURCE_PATH)
    imports = set(import_details)

    assert import_details == _ALLOWED_SYNTHETIC_IMPORTS
    assert import_details["algotrader.research.research_observation_manifest"] == (
        "build_research_observation_manifest",
    )
    assert "algotrader.research.research_observation_manifest_export" not in imports
    assert _matching_imports(imports, _FORBIDDEN_SYNTHETIC_IMPORT_PREFIXES) == []


def test_synthetic_source_builds_manifest_from_sma_pipeline_payload() -> None:
    source = _source_text_from_path(SYNTHETIC_SOURCE_PATH)
    calls = _call_names_from_path(SYNTHETIC_SOURCE_PATH)
    references = _reference_names_from_path(SYNTHETIC_SOURCE_PATH)

    assert _OBSERVATION_NAME in source
    assert _manifest_builder_uses_sma_pipeline_payload(SYNTHETIC_SOURCE_PATH)
    assert (
        _forbidden_source_token_matches(
            source,
            _FORBIDDEN_SOURCE_TOKENS,
            _SYNTHETIC_SOURCE_TOKEN_ALLOWLIST,
        )
        == []
    )
    assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert references.isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_synthetic_manifest_matches_included_observation_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    manifest = package.research_observation_manifest
    observation = package.sma_return_research_pipeline_observation

    assert manifest is not None
    assert observation is not None

    observation_payload = observation.to_dict()
    entry = manifest.entries[0]

    assert entry.observation_name == _OBSERVATION_NAME
    assert entry.observation_type == observation_payload["observation_type"]
    assert entry.payload_key_count == len(observation_payload)
    assert entry.payload_digest_sha256 == _payload_digest(observation_payload)


def test_synthetic_package_includes_readiness_as_synthetic_diagnostic_metadata() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    payload = package.to_dict()
    content_bundle = _dict(payload["content_bundle"])
    readiness = _dict(_single(_list(content_bundle["research_data_source_readiness"])))
    manifest_payload = _dict(payload["research_observation_manifest"])

    assert _package_content_bundle_includes_readiness_builder(SYNTHETIC_SOURCE_PATH)
    assert content_bundle["research_data_source_readiness_count"] == 1
    assert tuple(readiness) == _EXPECTED_READINESS_PAYLOAD_KEYS
    assert readiness["contract_type"] == "research_data_source_readiness"
    assert readiness["source_id"] == "synthetic-broad-etf-source-candidate"
    assert readiness["source_name"] == "Synthetic broad ETF source candidate"
    assert readiness["intended_use"] == "pipeline_validation_only"
    assert readiness["readiness_state"] == "candidate_only"
    assert readiness["satisfied_controls"] == ["no_lookahead_protocol_defined"]
    assert readiness["missing_controls"] == [
        "terms_review_documented",
        "snapshot_provenance_defined",
        "redistribution_policy_reviewed",
        "adjustment_policy_defined",
        "fixture_policy_review_documented",
    ]
    assert set(readiness).isdisjoint(_FORBIDDEN_READINESS_PAYLOAD_KEYS)
    assert all(
        str(ref).startswith(("synthetic_", "internal_"))
        for ref in readiness["evidence_refs"]
    )
    assert all(str(value).startswith("no ") for value in readiness["non_claims"])
    assert "research_data_source_readiness" not in _compact_sorted_json(manifest_payload)


def test_synthetic_package_includes_readiness_summary_as_diagnostic_metadata() -> None:
    package = build_synthetic_advisory_operating_brief_package_preview()
    payload = package.to_dict()
    content_bundle = _dict(payload["content_bundle"])
    summary = _dict(
        _single(_list(content_bundle["research_data_source_readiness_summaries"]))
    )
    manifest_payload = _dict(payload["research_observation_manifest"])

    assert _package_content_bundle_includes_readiness_summary_builder(
        SYNTHETIC_SOURCE_PATH
    )
    assert content_bundle["research_data_source_readiness_summary_count"] == 1
    assert tuple(summary) == _EXPECTED_READINESS_SUMMARY_PAYLOAD_KEYS
    assert summary["summary_type"] == "research_data_source_readiness_summary"
    assert summary["schema_version"] == "1"
    assert summary["summary_scope"] == "advisory_metadata_only"
    assert summary["summary_state"] == "candidate_only"
    assert summary["required_control_count"] == 6
    assert summary["satisfied_control_count"] == 1
    assert summary["missing_control_count"] == 5
    assert summary["diagnostic_limitations"] == [
        "Fixture carries no observations, values, or external source content.",
        "Fixture is synthetic metadata only and not connected to real data.",
    ]
    assert set(summary).isdisjoint(_FORBIDDEN_READINESS_SUMMARY_PAYLOAD_KEYS)
    assert "source_readiness" not in summary
    assert "research_data_source_readiness_summary" not in _compact_sorted_json(
        manifest_payload
    )


def test_synthetic_preview_manifest_output_is_byte_deterministic() -> None:
    first_package = build_synthetic_advisory_operating_brief_package_preview()
    second_package = build_synthetic_advisory_operating_brief_package_preview()
    first_payload = first_package.to_dict()
    second_payload = second_package.to_dict()
    first_json = _compact_sorted_json(first_payload)
    second_json = _compact_sorted_json(second_payload)
    manifest_payload = _dict(first_payload["research_observation_manifest"])
    entries = _list(manifest_payload["entries"])

    assert first_payload == second_payload
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert manifest_payload["entry_count"] == 1
    assert len(entries) == 1
    assert entries[0]["observation_name"] == _OBSERVATION_NAME


class ManifestSubclass(ResearchObservationManifest):
    pass


class _ManifestLookalike:
    def __init__(self, source: ResearchObservationManifest) -> None:
        self.manifest_type = source.manifest_type
        self.schema_version = source.schema_version
        self.advisory_scope = source.advisory_scope
        self.entry_count = source.entry_count
        self.entries = source.entries

    def to_dict(self) -> dict[str, object]:
        return {}


def _manifest() -> ResearchObservationManifest:
    return build_research_observation_manifest(
        (
            (
                "synthetic_research_observation",
                {
                    "observation_type": "synthetic_research_observation",
                    "value": 1,
                },
            ),
        )
    )


def _manifest_subclass(source: ResearchObservationManifest) -> ManifestSubclass:
    return ManifestSubclass(
        manifest_type=source.manifest_type,
        schema_version=source.schema_version,
        advisory_scope=source.advisory_scope,
        entry_count=source.entry_count,
        entries=source.entries,
    )


def _package(
    *,
    research_observation_manifest: object = None,
) -> AdvisoryOperatingBriefPackage:
    return build_advisory_operating_brief_package(
        package_id="synthetic-advisory-operating-brief-package-001",
        title="Synthetic advisory operating brief package",
        summary="Synthetic metadata bundle for a future morning brief handoff",
        as_of="2026-05-24",
        content_bundle=build_synthetic_advisory_operating_brief_content_bundle_with_research_queue(),
        research_observation_manifest=research_observation_manifest,
    )


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree_from_path(path: Path) -> ast.AST:
    return ast.parse(_source_text_from_path(path), filename=str(path))


def _import_details_from_path(path: Path) -> dict[str, tuple[str, ...]]:
    imports: dict[str, tuple[str, ...]] = {}

    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.name] = ()
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports[node.module] = tuple(alias.name for alias in node.names)

    return imports


def _call_names_from_path(path: Path) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree_from_path(path))
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _reference_names_from_path(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _function_names_from_path(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree_from_path(path))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _matching_imports(
    imports: set[str],
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    return [
        module_name
        for module_name in sorted(imports)
        if _matches_forbidden_prefix(module_name, forbidden_prefixes)
    ]


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _fragment_import_matches(
    imports: set[str],
    forbidden_fragments: tuple[str, ...],
) -> list[str]:
    return [
        module_name
        for module_name in sorted(imports)
        if any(fragment in module_name for fragment in forbidden_fragments)
    ]


def _signature_parameter_violations(
    signature: inspect.Signature,
) -> list[str]:
    return [
        name
        for name in signature.parameters
        if any(
            fragment in name.lower()
            for fragment in _FORBIDDEN_SIGNATURE_PARAMETER_FRAGMENTS
        )
    ]


def _forbidden_source_token_matches(
    source: str,
    tokens: tuple[str, ...],
    allowlist: dict[str, tuple[str, ...]],
) -> list[str]:
    matches: list[str] = []

    for token in tokens:
        if _source_token_has_unallowed_match(source, token, allowlist.get(token, ())):
            matches.append(token)

    return matches


def _source_token_has_unallowed_match(
    source: str,
    token: str,
    allowed_fragments: tuple[str, ...],
) -> bool:
    lowered_fragments = tuple(fragment.lower() for fragment in allowed_fragments)

    for line in source.splitlines():
        lowered_line = line.lower()
        if not _line_contains_token(lowered_line, token.lower()):
            continue
        if any(fragment in lowered_line for fragment in lowered_fragments):
            continue
        return True

    return False


def _line_contains_token(lowered_line: str, token: str) -> bool:
    if re.match(r"^[a-z0-9_]+$", token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return token in lowered_line


def _manifest_assignment_is_guarded_by_presence_check(path: Path) -> bool:
    to_dict = _function_def_from_path(path, "to_dict")
    if to_dict is None:
        return False

    for node in ast.walk(to_dict):
        if not isinstance(node, ast.If):
            continue
        if not _is_self_manifest_not_none_check(node.test):
            continue
        if any(_is_manifest_payload_assignment(child) for child in ast.walk(node)):
            return True

    return False


def _is_self_manifest_not_none_check(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Compare)
        and _is_self_manifest_attribute(node.left)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.IsNot)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value is None
    )


def _is_manifest_payload_assignment(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and _is_payload_manifest_subscript(node.targets[0])
        and _is_self_manifest_to_dict_call(node.value)
    )


def _is_payload_manifest_subscript(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "payload"
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == "research_observation_manifest"
    )


def _is_self_manifest_to_dict_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "to_dict"
        and _is_self_manifest_attribute(node.func.value)
    )


def _is_self_manifest_attribute(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "research_observation_manifest"
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _manifest_builder_uses_sma_pipeline_payload(path: Path) -> bool:
    tree = _tree_from_path(path)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node.func) != "build_research_observation_manifest":
            continue
        if len(node.args) != 1:
            return False
        return (
            _contains_string_constant(node.args[0], _OBSERVATION_NAME)
            and _contains_sma_pipeline_to_dict_call(node.args[0])
        )

    return False


def _package_content_bundle_includes_readiness_builder(path: Path) -> bool:
    function_def = _function_def_from_path(
        path,
        "_build_synthetic_package_content_bundle",
    )
    if function_def is None:
        return False

    for node in ast.walk(function_def):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node.func) != "build_advisory_operating_brief_content_bundle":
            continue
        for keyword in node.keywords:
            if keyword.arg != "research_data_source_readiness":
                continue
            return _contains_call(
                function_def,
                "_build_package_research_data_source_readiness",
            ) and _contains_name(keyword.value, "data_source_readiness")

    return False


def _package_content_bundle_includes_readiness_summary_builder(path: Path) -> bool:
    function_def = _function_def_from_path(
        path,
        "_build_synthetic_package_content_bundle",
    )
    if function_def is None:
        return False

    for node in ast.walk(function_def):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node.func) != "build_advisory_operating_brief_content_bundle":
            continue
        for keyword in node.keywords:
            if keyword.arg != "research_data_source_readiness_summaries":
                continue
            return _contains_call(
                function_def,
                "_build_package_research_data_source_readiness_summary",
            ) and (
                _contains_name(keyword.value, "data_source_readiness")
                or _contains_name(keyword.value, "data_source_readiness_summary")
            )

    return False


def _contains_name(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id == name
        for child in ast.walk(node)
    )


def _contains_call(node: ast.AST, call_name: str) -> bool:
    return any(
        isinstance(child, ast.Call) and _call_name(child.func) == call_name
        for child in ast.walk(node)
    )


def _contains_string_constant(node: ast.AST, value: str) -> bool:
    return any(
        isinstance(child, ast.Constant) and child.value == value
        for child in ast.walk(node)
    )


def _contains_sma_pipeline_to_dict_call(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not isinstance(child.func, ast.Attribute):
            continue
        if child.func.attr != "to_dict":
            continue
        if not isinstance(child.func.value, ast.Name):
            continue
        if child.func.value.id == "sma_return_research_pipeline_observation":
            return True

    return False


def _function_def_from_path(path: Path, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node

    return None


def _payload_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        _compact_sorted_json(payload).encode("utf-8")
    ).hexdigest()


def _compact_sorted_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)

    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)

    return value


def _single(value: list[object]) -> object:
    assert len(value) == 1

    return value[0]
