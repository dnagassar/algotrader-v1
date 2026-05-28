from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
    build_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_diagnostic_issue import (
    build_advisory_operating_brief_diagnostic_issues,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary,
)
from tests.fixtures.advisory_operating_brief_diagnostic_issue import (
    expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts,
)


CONTENT_BUNDLE_SOURCE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_content_bundle.py"
)
RENDERER_SOURCE_PATH = Path(
    "src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py"
)
_READINESS_KEY = "research_data_source_readiness"
_READINESS_COUNT_KEY = "research_data_source_readiness_count"
_READINESS_SUMMARY_KEY = "research_data_source_readiness_summaries"
_READINESS_SUMMARY_COUNT_KEY = "research_data_source_readiness_summary_count"
_DIAGNOSTIC_ISSUES_KEY = "diagnostic_issues"
_DIAGNOSTIC_ISSUE_COUNT_KEY = "diagnostic_issue_count"
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
_EXPECTED_DIAGNOSTIC_ISSUE_PAYLOAD_KEYS = (
    "source_branch",
    "issue_code",
    "issue_state",
    "diagnostic_message",
    "blocking_controls",
    "limitations",
)
_EXPECTED_CONTENT_BUNDLE_IMPORTS = {
    "__future__": ("annotations",),
    "collections.abc": ("Iterable",),
    "dataclasses": ("dataclass",),
    "algotrader.errors": ("ValidationError",),
    "algotrader.research.advisory_operating_brief_diagnostic_issue": (
        "AdvisoryOperatingBriefDiagnosticIssue",
    ),
    "algotrader.research.candidate_research_brief": ("CandidateResearchBrief",),
    "algotrader.research.research_return_observation_brief_container": (
        "ResearchReturnObservationBrief",
    ),
    "algotrader.research.research_return_summary_observation_brief": (
        "ResearchReturnSummaryObservationBrief",
    ),
    "algotrader.research.research_queue_brief": ("ResearchQueueBrief",),
    "algotrader.research.research_data_source_readiness": (
        "ResearchDataSourceReadiness",
    ),
    "algotrader.research.research_data_source_readiness_summary": (
        "ResearchDataSourceReadinessSummary",
    ),
    "algotrader.research.risk_authority_brief": ("RiskAuthorityBrief",),
    "algotrader.research.sma_research_observation_brief_container": (
        "SmaResearchObservationBrief",
    ),
    "algotrader.research.sma_research_summary_observation": (
        "SmaResearchSummaryObservation",
    ),
    "algotrader.research.strategy_eligibility_brief": (
        "StrategyEligibilityBrief",
    ),
}
_EXPECTED_RENDERER_IMPORTS = {
    "__future__": ("annotations",),
    "algotrader.errors": ("ValidationError",),
    "algotrader.research.advisory_operating_brief_content_bundle": (
        "AdvisoryOperatingBriefContentBundle",
    ),
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.agent",
    "algotrader.agents",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.cli",
    "algotrader.config",
    "algotrader.core.config",
    "algotrader.dashboard",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
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
    "pandas",
    "pathlib",
    "polars",
    "requests",
    "sklearn",
    "socket",
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "yfinance",
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
_FORBIDDEN_SOURCE_TOKENS = (
    "alpaca",
    "backtest",
    "broker",
    "credential",
    "dashboard",
    "download",
    "duckdb",
    "external api",
    "fill",
    "httpx",
    "ingest",
    "joblib",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "openai",
    "order",
    "pandas",
    "persistence",
    "portfolio",
    "quantconnect",
    "ranking",
    "recommendation",
    "requests",
    "runtime",
    "scheduler",
    "scoring",
    "secret",
    "socket",
    "tensorflow",
    "torch",
    "trading_authority",
    "urllib",
    "vectorbt",
    "vendor",
    "yfinance",
    "capital_authority=True",
)
_FORBIDDEN_PAYLOAD_KEYS = {
    "account",
    "accounts",
    "approved",
    "authorization",
    "buy",
    "credential",
    "endpoint",
    "fill",
    "fills",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    "order",
    "orders",
    "paper_eligible",
    "password",
    "portfolio",
    "portfolios",
    "recommendation",
    "score",
    "secret",
    "sell",
    "signal",
    "source_payload",
    "timestamp",
    "token",
    "trading_authority",
    "trading_ready",
    "url",
    "vendor",
}
_FORBIDDEN_SUMMARY_PAYLOAD_KEYS = _FORBIDDEN_PAYLOAD_KEYS | {
    "approval_status",
    "authorization_status",
    "raw_payload",
    "source_authorized",
    "source_payload",
    "source_readiness",
    "wrapper",
}
_FORBIDDEN_DIAGNOSTIC_PAYLOAD_KEYS = _FORBIDDEN_SUMMARY_PAYLOAD_KEYS | {
    "authority",
    "capital_authority",
    "created_at",
    "digest",
    "generated_at",
    "priority",
    "rank",
    "raw_data",
    "raw_payload",
    "severity",
    "wrapper",
}
_FORBIDDEN_DIAGNOSTIC_TEXT_TERMS = (
    "approval",
    "approved",
    "authorization",
    "authorized",
    "ranking",
    "scoring",
    "recommendation",
    "allocation",
    "ready_to_trade",
    "trading_ready",
    "validated_for_trading",
    "usable_for_backtest",
)
_POSITIVE_READINESS_TERMS = (
    "approved",
    "approval granted",
    "ready for trading",
    "paper ready",
    "live ready",
    "trading_ready",
    "paper_eligible",
    "live_authorized",
    "buy",
    "sell",
    "hold",
)


def test_content_bundle_imports_readiness_contract_without_runtime_chains() -> None:
    import_details = _import_details_from_path(CONTENT_BUNDLE_SOURCE_PATH)
    imports = set(import_details)

    assert import_details == _EXPECTED_CONTENT_BUNDLE_IMPORTS
    assert import_details["algotrader.research.research_data_source_readiness"] == (
        "ResearchDataSourceReadiness",
    )
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert "build_research_data_source_readiness" not in _imported_names(
        import_details
    )
    assert "build_research_data_source_readiness_summary" not in _imported_names(
        import_details
    )


def test_content_bundle_readiness_branch_is_optional_metadata_only() -> None:
    signature = inspect.signature(build_advisory_operating_brief_content_bundle)
    default_payload = build_synthetic_advisory_operating_brief_content_bundle().to_dict()
    readiness_payload = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness().to_dict()
    )
    readiness = _single_branch(readiness_payload, _READINESS_KEY)

    assert signature.parameters[_READINESS_KEY].default == ()
    assert _READINESS_KEY not in default_payload
    assert _READINESS_COUNT_KEY not in default_payload
    assert readiness_payload[_READINESS_COUNT_KEY] == 1
    assert readiness["contract_type"] == _READINESS_KEY
    assert readiness["readiness_state"] == "candidate_only"
    assert readiness["source_id"] == "synthetic-broad-etf-source-candidate"
    assert readiness["intended_use"] == "pipeline_validation_only"
    assert readiness["missing_controls"] == [
        "terms_review_documented",
        "snapshot_provenance_defined",
        "redistribution_policy_reviewed",
        "adjustment_policy_defined",
        "fixture_policy_review_documented",
    ]
    assert _payload_keys(readiness_payload).isdisjoint(_FORBIDDEN_PAYLOAD_KEYS)
    assert _primitive_only(readiness_payload)


def test_content_bundle_readiness_summary_branch_is_optional_diagnostic_metadata() -> None:
    signature = inspect.signature(build_advisory_operating_brief_content_bundle)
    default_payload = build_synthetic_advisory_operating_brief_content_bundle().to_dict()
    summary_payload = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary().to_dict()
    )
    repeated_summary_payload = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary().to_dict()
    )
    summary = _single_branch(summary_payload, _READINESS_SUMMARY_KEY)

    assert signature.parameters[_READINESS_SUMMARY_KEY].default == ()
    assert _READINESS_SUMMARY_KEY not in default_payload
    assert _READINESS_SUMMARY_COUNT_KEY not in default_payload
    assert summary_payload[_READINESS_SUMMARY_COUNT_KEY] == 1
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
    assert _payload_keys(summary_payload).isdisjoint(
        _FORBIDDEN_SUMMARY_PAYLOAD_KEYS
    )
    assert _primitive_only(summary_payload)
    assert _compact_sorted_json(summary_payload) == _compact_sorted_json(
        repeated_summary_payload
    )


def test_content_bundle_diagnostic_issues_branch_is_optional_metadata_only() -> None:
    signature = inspect.signature(build_advisory_operating_brief_content_bundle)
    default_payload = build_synthetic_advisory_operating_brief_content_bundle().to_dict()
    diagnostic_payload = (
        _build_content_bundle_with_diagnostic_issues().to_dict()
    )
    repeated_diagnostic_payload = (
        _build_content_bundle_with_diagnostic_issues().to_dict()
    )
    issues = _branch_items(diagnostic_payload, _DIAGNOSTIC_ISSUES_KEY)

    assert signature.parameters[_DIAGNOSTIC_ISSUES_KEY].default == ()
    assert _DIAGNOSTIC_ISSUES_KEY not in default_payload
    assert _DIAGNOSTIC_ISSUE_COUNT_KEY not in default_payload
    assert _READINESS_KEY not in diagnostic_payload
    assert _READINESS_SUMMARY_KEY not in diagnostic_payload
    assert diagnostic_payload[_DIAGNOSTIC_ISSUE_COUNT_KEY] == 2
    assert issues == expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts()
    assert [tuple(issue) for issue in issues] == [
        _EXPECTED_DIAGNOSTIC_ISSUE_PAYLOAD_KEYS,
        _EXPECTED_DIAGNOSTIC_ISSUE_PAYLOAD_KEYS,
    ]
    assert [issue["source_branch"] for issue in issues] == [
        "research_data_source_readiness",
        "research_data_source_readiness_summary",
    ]
    assert [issue["issue_state"] for issue in issues] == [
        "candidate_only",
        "candidate_only",
    ]
    assert _payload_keys(issues).isdisjoint(_FORBIDDEN_DIAGNOSTIC_PAYLOAD_KEYS)
    assert _primitive_only(issues)
    assert _compact_sorted_json(diagnostic_payload) == _compact_sorted_json(
        repeated_diagnostic_payload
    )


def test_renderer_readiness_wording_stays_diagnostic_and_negative() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )
    exported = export_advisory_operating_brief_content_bundle(bundle)
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    lines = tuple(rendered.splitlines())

    assert exported.rendered_text == rendered
    assert "Research Data Source Readiness Diagnostics" in lines
    assert "Research Data Source Readiness Diagnostic 1" in lines
    assert "readiness_state: candidate_only" in lines
    assert "required_controls:" in lines
    assert "satisfied_controls:" in lines
    assert "missing_controls:" in lines
    assert _positive_readiness_lines(rendered) == []
    assert "approval_status:" not in rendered
    assert "source_authorized:" not in rendered
    assert "trading_ready:" not in rendered


def test_renderer_readiness_summary_wording_stays_diagnostic_and_negative() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_summary()
    )
    exported = export_advisory_operating_brief_content_bundle(bundle)
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    lines = tuple(rendered.splitlines())

    assert exported.rendered_text == rendered
    assert "Research Data Source Readiness Summary Diagnostics" in lines
    assert "Research Data Source Readiness Summary Diagnostic 1" in lines
    assert "summary_type: research_data_source_readiness_summary" in lines
    assert "summary_scope: advisory_metadata_only" in lines
    assert "summary_state: candidate_only" in lines
    assert "required_control_count: 6" in lines
    assert "satisfied_control_count: 1" in lines
    assert "missing_control_count: 5" in lines
    assert "diagnostic_limitations:" in lines
    assert _positive_readiness_lines(rendered) == []
    assert "approval_status:" not in rendered
    assert "source_authorized:" not in rendered
    assert "source_readiness:" not in rendered
    assert "trading_ready:" not in rendered


def test_renderer_diagnostic_issue_wording_stays_diagnostic_and_negative() -> None:
    bundle = _build_content_bundle_with_diagnostic_issues()
    exported = export_advisory_operating_brief_content_bundle(bundle)
    rendered = render_advisory_operating_brief_content_bundle_text(bundle)
    lines = tuple(rendered.splitlines())
    diagnostic_text = "\n".join(
        _section_lines(rendered, "Diagnostic Issues", "Limitations")
    )

    assert exported.rendered_text == rendered
    assert "Diagnostic Issues" in lines
    assert "Diagnostic Issue 1" in lines
    assert "Diagnostic Issue 2" in lines
    assert "source_branch: research_data_source_readiness" in lines
    assert "source_branch: research_data_source_readiness_summary" in lines
    assert "issue_code: missing_diagnostic_controls" in lines
    assert "issue_state: candidate_only" in lines
    assert (
        "diagnostic_message: Readiness branch reports missing diagnostic controls."
        in lines
    )
    assert (
        "diagnostic_message: Readiness summary branch reports missing "
        "diagnostic controls."
    ) in lines
    assert "blocking_controls:" in lines
    assert "limitations:" in lines
    assert _matching_terms(
        diagnostic_text.lower(),
        _FORBIDDEN_DIAGNOSTIC_TEXT_TERMS,
    ) == []
    assert _positive_readiness_lines(rendered) == []
    assert "approval_status:" not in rendered
    assert "authorization_status:" not in rendered
    assert "trading_ready:" not in rendered


def test_renderer_imports_only_bundle_contract_and_no_runtime_chains() -> None:
    import_details = _import_details_from_path(RENDERER_SOURCE_PATH)
    imports = set(import_details)

    assert import_details == _EXPECTED_RENDERER_IMPORTS
    assert _matching_imports(imports, _FORBIDDEN_IMPORT_PREFIXES) == []
    assert _function_names_from_path(RENDERER_SOURCE_PATH).isdisjoint(
        {
            "build_research_data_source_readiness",
            "export_advisory_operating_brief_content_bundle",
            "from_dict",
        }
    )


def test_readiness_integration_paths_have_no_forbidden_tokens_or_calls() -> None:
    for path in (CONTENT_BUNDLE_SOURCE_PATH, RENDERER_SOURCE_PATH):
        source = _source_text_from_path(path)
        calls = _call_names_from_path(path)

        assert _forbidden_source_token_matches(source) == []
        assert calls.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_diagnostic_issue_branch_source_is_exact_type_and_to_dict_only() -> None:
    assert _diagnostic_tuple_requires_exact_issue_type(CONTENT_BUNDLE_SOURCE_PATH)
    assert _content_bundle_to_dict_serializes_diagnostic_issues_with_to_dict(
        CONTENT_BUNDLE_SOURCE_PATH
    )


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_content_bundle_with_diagnostic_issues() -> (
    AdvisoryOperatingBriefContentBundle
):
    source = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_and_summary()
    )
    return build_advisory_operating_brief_content_bundle(
        candidate_research_briefs=source.candidate_research_briefs,
        strategy_eligibility_briefs=source.strategy_eligibility_briefs,
        diagnostic_issues=build_advisory_operating_brief_diagnostic_issues(source),
    )


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


def _imported_names(import_details: dict[str, tuple[str, ...]]) -> set[str]:
    names: set[str] = set()
    for imported in import_details.values():
        names.update(imported)

    return names


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


def _function_names_from_path(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree_from_path(path))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _function_def_from_path(path: Path, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(_tree_from_path(path)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node

    return None


def _diagnostic_tuple_requires_exact_issue_type(path: Path) -> bool:
    function_def = _function_def_from_path(path, "_diagnostic_issues_tuple")
    if function_def is None:
        return False

    has_local_import = any(
        isinstance(node, ast.ImportFrom)
        and node.module
        == "algotrader.research.advisory_operating_brief_diagnostic_issue"
        and any(
            alias.name == "AdvisoryOperatingBriefDiagnosticIssue"
            for alias in node.names
        )
        for node in ast.walk(function_def)
    )
    has_exact_type_check = any(
        _is_type_is_not_diagnostic_issue_compare(node)
        for node in ast.walk(function_def)
    )

    return has_local_import and has_exact_type_check


def _is_type_is_not_diagnostic_issue_compare(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Call)
        and _call_name(node.left.func) == "type"
        and len(node.left.args) == 1
        and isinstance(node.left.args[0], ast.Name)
        and node.left.args[0].id == "issue"
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.IsNot)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Name)
        and node.comparators[0].id == "AdvisoryOperatingBriefDiagnosticIssue"
    )


def _content_bundle_to_dict_serializes_diagnostic_issues_with_to_dict(
    path: Path,
) -> bool:
    to_dict = _function_def_from_path(path, "to_dict")
    if to_dict is None:
        return False

    for node in ast.walk(to_dict):
        if not isinstance(node, ast.If):
            continue
        if not _is_self_attribute(node.test, "diagnostic_issues"):
            continue
        if any(
            _is_payload_key_assignment(child, "diagnostic_issues")
            and _contains_issue_to_dict_call(child)
            for child in ast.walk(node)
        ):
            return True

    return False


def _is_self_attribute(node: ast.AST, attribute_name: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == attribute_name
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _is_payload_key_assignment(node: ast.AST, key: str) -> bool:
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Subscript)
        and isinstance(node.targets[0].value, ast.Name)
        and node.targets[0].value.id == "payload"
        and isinstance(node.targets[0].slice, ast.Constant)
        and node.targets[0].slice.value == key
    )


def _contains_issue_to_dict_call(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and child.func.attr == "to_dict"
        and isinstance(child.func.value, ast.Name)
        and child.func.value.id == "issue"
        for child in ast.walk(node)
    )


def _forbidden_source_token_matches(source: str) -> list[str]:
    return [
        token
        for token in _FORBIDDEN_SOURCE_TOKENS
        if _source_contains_token(source, token)
    ]


def _source_contains_token(source: str, token: str) -> bool:
    lowered_token = token.lower()

    for line in source.splitlines():
        if _line_contains_token(line.lower(), lowered_token):
            return True

    return False


def _line_contains_token(lowered_line: str, token: str) -> bool:
    if re.match(r"^[a-z0-9_]+$", token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return token in lowered_line


def _single_branch(payload: dict[str, object], key: str) -> dict[str, object]:
    branch = payload[key]
    assert isinstance(branch, list)
    assert len(branch) == 1
    item = branch[0]
    assert isinstance(item, dict)

    return item


def _branch_items(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    branch = payload[key]
    assert isinstance(branch, list)
    for item in branch:
        assert isinstance(item, dict)

    return branch


def _section_lines(text: str, start: str, end: str) -> tuple[str, ...]:
    lines = tuple(text.splitlines())
    start_index = lines.index(start)
    end_index = lines.index(end, start_index)

    return lines[start_index:end_index]


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
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


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (bool, int, float, str):
        return True
    if type(value) is list:
        return all(_primitive_only(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _primitive_only(item)
            for key, item in value.items()
        )

    return False


def _positive_readiness_lines(text: str) -> list[str]:
    matches: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if not any(term in lowered for term in _POSITIVE_READINESS_TERMS):
            continue
        if line.startswith("- no ") or line.startswith("- not "):
            continue
        matches.append(line)

    return matches


def _compact_sorted_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _matching_terms(text: str, forbidden_terms: tuple[str, ...]) -> list[str]:
    return [term for term in forbidden_terms if term in text]
