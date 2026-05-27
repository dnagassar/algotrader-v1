import ast
import inspect
import json

from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
)
from tests.fixtures import research_data_source_readiness as fixture_module
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_dict,
    expected_synthetic_research_data_source_readiness_export_snapshot_dict,
    expected_synthetic_research_data_source_readiness_export_snapshot_json,
    expected_synthetic_research_data_source_readiness_json,
)


EXPECTED_KEYS = [
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
]

EXPECTED_REQUIRED_CONTROLS = [
    "terms_review_documented",
    "snapshot_provenance_defined",
    "redistribution_policy_reviewed",
    "adjustment_policy_defined",
    "fixture_policy_review_documented",
    "no_lookahead_protocol_defined",
]

EXPECTED_SATISFIED_CONTROLS = ["no_lookahead_protocol_defined"]

EXPECTED_MISSING_CONTROLS = [
    "terms_review_documented",
    "snapshot_provenance_defined",
    "redistribution_policy_reviewed",
    "adjustment_policy_defined",
    "fixture_policy_review_documented",
]

EXPECTED_NON_CLAIMS = [
    "no source approval",
    "no data ingestion approval",
    "no trading authority",
    "no capital authority",
    "no data-source authorization",
]

ALLOWED_IMPORTS = {
    "json": (),
    "algotrader.research.research_data_source_readiness": (
        "ResearchDataSourceReadiness",
        "build_research_data_source_readiness",
    ),
}

FORBIDDEN_SOURCE_TERMS = (
    "pathlib",
    "os",
    "socket",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "pandas",
    "polars",
    "duckdb",
    "yfinance",
    "alpaca",
    "polygon",
    "vectorbt",
    "QuantConnect",
    "notebook",
    "broker",
    "runtime",
    "scheduler",
    "portfolio",
    "order",
    "fill",
    "execution",
    "persistence",
    "storage",
    "credential",
    "secret",
    "token",
    "API key",
    "network",
    "backtest",
    "benchmark",
    "ML",
    "LLM",
    "agent",
    "open(",
    "read_text",
    "write",
    "Path(",
    "getenv",
    "environ",
    "datetime.now",
    "time.time",
    "random",
    "uuid",
    "from_dict",
)

ADVISORY_SOURCE_TERMS = (
    "approval",
    "authorization",
    "authority",
    "capital",
    "trading",
)

NEGATIVE_NON_CLAIM_ALLOWLIST = (
    '"no source approval",',
    '"no data ingestion approval",',
    '"no trading authority",',
    '"no capital authority",',
    '"no data-source authorization",',
)

FORBIDDEN_FIELD_TERMS = (
    "file",
    "path",
    "env",
    "network",
    "vendor",
    "broker",
    "runtime",
    "persistence",
    "backtest",
    "trading",
)


def test_object_fixture_returns_exact_research_data_source_readiness() -> None:
    readiness = expected_synthetic_research_data_source_readiness()

    assert type(readiness) is ResearchDataSourceReadiness
    assert readiness.source_id == "synthetic-broad-etf-source-candidate"
    assert readiness.source_name == "Synthetic broad ETF source candidate"
    assert readiness.asset_class_scope == ("equity_etf",)
    assert readiness.intended_use == "pipeline_validation_only"
    assert readiness.readiness_state == "candidate_only"
    assert readiness.required_controls == tuple(EXPECTED_REQUIRED_CONTROLS)
    assert readiness.satisfied_controls == tuple(EXPECTED_SATISFIED_CONTROLS)
    assert readiness.missing_controls == tuple(EXPECTED_MISSING_CONTROLS)
    assert readiness.evidence_refs == (
        "synthetic_phase_271_readiness_fixture",
        "internal_control_gap_note",
    )
    assert readiness.limitations == (
        "Fixture is synthetic metadata only and not connected to real data.",
        "Fixture carries no observations, values, or external source content.",
    )
    assert readiness.non_claims == tuple(EXPECTED_NON_CLAIMS)


def test_dict_fixture_returns_object_to_dict_unchanged() -> None:
    readiness = expected_synthetic_research_data_source_readiness()
    payload = expected_synthetic_research_data_source_readiness_dict()

    assert payload == readiness.to_dict()
    assert list(payload) == EXPECTED_KEYS


def test_json_fixture_returns_compact_sorted_key_json() -> None:
    payload = expected_synthetic_research_data_source_readiness_dict()
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert expected_synthetic_research_data_source_readiness_json() == expected_json


def test_export_snapshot_fixture_returns_existing_dict_and_json_payloads() -> None:
    payload = expected_synthetic_research_data_source_readiness_dict()
    expected_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    assert (
        expected_synthetic_research_data_source_readiness_export_snapshot_dict()
        == payload
    )
    assert (
        expected_synthetic_research_data_source_readiness_export_snapshot_json()
        == expected_json
    )


def test_repeated_fixture_calls_are_deterministic() -> None:
    first_object = expected_synthetic_research_data_source_readiness()
    second_object = expected_synthetic_research_data_source_readiness()
    first_payload = expected_synthetic_research_data_source_readiness_dict()
    second_payload = expected_synthetic_research_data_source_readiness_dict()
    first_json = expected_synthetic_research_data_source_readiness_json()
    second_json = expected_synthetic_research_data_source_readiness_json()
    first_export_payload = (
        expected_synthetic_research_data_source_readiness_export_snapshot_dict()
    )
    second_export_payload = (
        expected_synthetic_research_data_source_readiness_export_snapshot_dict()
    )
    first_export_json = (
        expected_synthetic_research_data_source_readiness_export_snapshot_json()
    )
    second_export_json = (
        expected_synthetic_research_data_source_readiness_export_snapshot_json()
    )

    assert first_object == second_object
    assert first_object is not second_object
    assert first_payload == second_payload
    assert first_payload is not second_payload
    assert first_json == second_json
    assert first_export_payload == second_export_payload
    assert first_export_payload is not second_export_payload
    assert first_export_json == second_export_json


def test_fixture_payload_is_primitive_json_round_trippable() -> None:
    payload = expected_synthetic_research_data_source_readiness_dict()
    compact_json = expected_synthetic_research_data_source_readiness_json()

    assert _primitive_only(payload)
    assert json.loads(compact_json) == payload
    assert json.dumps(
        json.loads(compact_json),
        sort_keys=True,
        separators=(",", ":"),
    ) == compact_json


def test_missing_controls_are_computed_in_required_control_order() -> None:
    payload = expected_synthetic_research_data_source_readiness_dict()

    assert payload["required_controls"] == EXPECTED_REQUIRED_CONTROLS
    assert payload["satisfied_controls"] == EXPECTED_SATISFIED_CONTROLS
    assert payload["missing_controls"] == EXPECTED_MISSING_CONTROLS


def test_fixture_is_not_metadata_ready() -> None:
    readiness = expected_synthetic_research_data_source_readiness()

    assert readiness.readiness_state == "candidate_only"
    assert readiness.readiness_state != "metadata_ready"
    assert readiness.missing_controls


def test_fixture_carries_only_negative_authority_and_approval_claims() -> None:
    readiness = expected_synthetic_research_data_source_readiness()

    assert list(readiness.non_claims) == EXPECTED_NON_CLAIMS
    assert "no source approval" in readiness.non_claims
    assert "no data ingestion approval" in readiness.non_claims
    assert "no trading authority" in readiness.non_claims
    assert "no capital authority" in readiness.non_claims
    assert "no data-source authorization" in readiness.non_claims


def test_fixture_source_has_no_forbidden_runtime_or_data_fields() -> None:
    payload = expected_synthetic_research_data_source_readiness_dict()
    field_names = _serialized_keys(payload)

    assert _matching_field_terms(field_names, FORBIDDEN_FIELD_TERMS) == []


def test_fixture_module_imports_only_allowed_dependencies() -> None:
    tree = _fixture_tree()
    import_details = _import_details(tree)

    assert import_details == ALLOWED_IMPORTS
    assert _matching_imports(
        set(import_details),
        FORBIDDEN_SOURCE_TERMS,
    ) == []


def test_fixture_module_source_has_no_forbidden_surfaces() -> None:
    source = _fixture_source()
    tree = _fixture_tree()

    assert "ResearchDataSourceReadiness(" not in source
    assert _call_names(tree).isdisjoint(
        {
            "__import__",
            "open",
            "Path",
            "read_text",
            "write",
            "getenv",
            "datetime.now",
            "time.time",
            "random",
            "uuid",
            "from_dict",
        }
    )
    assert _source_token_matches(source, FORBIDDEN_SOURCE_TERMS) == []
    assert _source_token_matches(
        source,
        ADVISORY_SOURCE_TERMS,
        allowed_lines=NEGATIVE_NON_CLAIM_ALLOWLIST,
    ) == []


def _fixture_source() -> str:
    return inspect.getsource(fixture_module)


def _fixture_tree() -> ast.AST:
    return ast.parse(_fixture_source(), filename=fixture_module.__name__)


def _import_details(tree: ast.AST) -> dict[str, tuple[str, ...]]:
    imports: dict[str, tuple[str, ...]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.name] = ()
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports[node.module] = tuple(alias.name for alias in node.names)

    return imports


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


def _call_names(tree: ast.AST) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _source_token_matches(
    source: str,
    tokens: tuple[str, ...],
    *,
    allowed_lines: tuple[str, ...] = (),
) -> list[str]:
    matches: list[str] = []

    for line in source.splitlines():
        stripped_line = line.strip()
        if stripped_line in allowed_lines:
            continue
        lowered_line = line.lower()
        for token in tokens:
            lowered_token = token.lower()
            if _line_contains_token(lowered_line, lowered_token):
                matches.append(token)

    return sorted(set(matches))


def _line_contains_token(lowered_line: str, lowered_token: str) -> bool:
    if lowered_token.isalnum():
        start = 0
        while True:
            index = lowered_line.find(lowered_token, start)
            if index == -1:
                return False
            before = lowered_line[index - 1] if index > 0 else ""
            after_index = index + len(lowered_token)
            after = lowered_line[after_index] if after_index < len(lowered_line) else ""
            if not _is_identifier_char(before) and not _is_identifier_char(after):
                return True
            start = index + 1

    return lowered_token in lowered_line


def _is_identifier_char(value: str) -> bool:
    return value.isalnum() or value == "_"


def _serialized_keys(value: object) -> set[str]:
    if type(value) is dict:
        return {
            key
            for dict_key, item in value.items()
            for key in {dict_key, *_serialized_keys(item)}
        }
    if type(value) is list:
        return {
            key
            for item in value
            for key in _serialized_keys(item)
        }

    return set()


def _matching_field_terms(
    field_names: set[str],
    forbidden_terms: tuple[str, ...],
) -> list[str]:
    return sorted(
        {
            term
            for field_name in field_names
            for term in forbidden_terms
            if term in field_name.lower()
        }
    )


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
