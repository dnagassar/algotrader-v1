from __future__ import annotations

import ast
import json
import re
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import research_data_source_readiness_summary as summary_module
from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
    build_research_data_source_readiness,
)
from algotrader.research.research_data_source_readiness_summary import (
    ResearchDataSourceReadinessSummary,
    build_research_data_source_readiness_summary,
)
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_summary,
    expected_synthetic_research_data_source_readiness_summary_dict,
    expected_synthetic_research_data_source_readiness_summary_json,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path(
    "src/algotrader/research/research_data_source_readiness_summary.py"
)
EXPECTED_KEYS = [
    "summary_type",
    "schema_version",
    "summary_scope",
    "summary_state",
    "required_control_count",
    "satisfied_control_count",
    "missing_control_count",
    "diagnostic_limitations",
]
ALLOWED_IMPORTS = {
    "__future__": ("annotations",),
    "dataclasses": ("dataclass",),
    "algotrader.errors": ("ValidationError",),
    "algotrader.research.research_data_source_readiness": (
        "ResearchDataSourceReadiness",
    ),
}
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.config",
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
    "algotrader.storage",
    "algotrader.vendor",
    _s("data", "base"),
    "duckdb",
    "httpx",
    "numpy",
    "openai",
    "os",
    "pandas",
    _s("path", "lib"),
    "polars",
    "QuantConnect",
    "quantconnect",
    _s("re", "quests"),
    _s("so", "cket"),
    "urllib",
    "vectorbt",
    "yfinance",
)
FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    _s("cli", "ent"),
    _s("con", "nect"),
    _s("create_", "or", "der"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    _s("ing", "est"),
    "json.dump",
    "json.load",
    "load",
    "main",
    "mkdir",
    _s("op", "en"),
    "os.environ.get",
    "os.getenv",
    "parse_args",
    "post",
    _s("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "rglob",
    "save",
    _s("so", "cket.create_", "con", "nection"),
    _s("so", "cket.", "so", "cket"),
    "stat",
    _s("sub", "mit_", "or", "der"),
    "time.monotonic",
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _s("wri", "te"),
    "write_text",
}
FORBIDDEN_SOURCE_TOKENS = (
    _s("al", "paca"),
    _s("app", "roved"),
    _s("author", "ized"),
    _s("back", "test"),
    _s("bro", "ker"),
    _s("cre", "dential"),
    _s("down", "load"),
    "duckdb",
    _s("fi", "ll"),
    "httpx",
    _s("ing", "est"),
    "llm",
    "ml",
    _s("net", "work"),
    "notebook",
    _s("or", "der"),
    "pandas",
    _s("persist", "ence"),
    "polars",
    _s("port", "folio"),
    "production_ready",
    "QuantConnect",
    "quantconnect",
    "ready_to_trade",
    _s("re", "quests"),
    _s("run", "time"),
    _s("sche", "duler"),
    _s("so", "cket"),
    "urllib",
    "usable_for_backtest",
    "validated_for_trading",
    "vectorbt",
    _s("ven", "dor"),
    "yfinance",
)
FORBIDDEN_PAYLOAD_KEYS = {
    _s("allo", "cation"),
    _s("bro", "ker"),
    _s("cap", "ital"),
    _s("or", "der"),
    _s("port", "folio"),
    _s("ra", "nk"),
    _s("raw", "_payload"),
    _s("recomm", "endation"),
    _s("sco", "re"),
    "source_readiness",
    _s("stra", "tegy"),
    _s("tra", "ding"),
    "wrapper",
}


def test_builder_accepts_exact_readiness_and_preserves_identity() -> None:
    source = expected_synthetic_research_data_source_readiness()
    summary = build_research_data_source_readiness_summary(source)

    assert type(summary) is ResearchDataSourceReadinessSummary
    assert summary.source_readiness is source
    assert summary.to_dict() == (
        expected_synthetic_research_data_source_readiness_summary_dict(
            build_research_data_source_readiness_summary
        )
    )


def test_fixture_builds_summary_through_production_builder() -> None:
    source = expected_synthetic_research_data_source_readiness()
    calls: list[ResearchDataSourceReadiness] = []

    def tracked_builder(
        source_readiness: ResearchDataSourceReadiness,
    ) -> ResearchDataSourceReadinessSummary:
        calls.append(source_readiness)
        return build_research_data_source_readiness_summary(source_readiness)

    summary = expected_synthetic_research_data_source_readiness_summary(
        tracked_builder,
        source,
    )

    assert type(summary) is ResearchDataSourceReadinessSummary
    assert calls == [source]
    assert summary.source_readiness is source
    assert summary.to_dict() == (
        expected_synthetic_research_data_source_readiness_summary_dict(
            build_research_data_source_readiness_summary,
            source,
        )
    )


def test_subclasses_lookalikes_and_non_readiness_are_rejected() -> None:
    class Lookalike:
        readiness_state = "candidate_only"
        required_controls = ("terms_review",)
        satisfied_controls = ()
        missing_controls = ("terms_review",)
        limitations = ("metadata only",)

    class ReadinessSubclass(ResearchDataSourceReadiness):
        pass

    source = expected_synthetic_research_data_source_readiness()
    subclass = ReadinessSubclass(**source.to_dict())

    for value in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="source_readiness"):
            build_research_data_source_readiness_summary(value)

    payload = _direct_payload(source)
    payload["source_readiness"] = subclass
    with pytest.raises(ValidationError, match="source_readiness"):
        ResearchDataSourceReadinessSummary(**payload)


def test_summary_is_frozen_slotted_and_has_pinned_field_order() -> None:
    summary = build_research_data_source_readiness_summary(
        expected_synthetic_research_data_source_readiness()
    )

    assert is_dataclass(ResearchDataSourceReadinessSummary)
    assert ResearchDataSourceReadinessSummary.__dataclass_params__.frozen is True
    assert hasattr(ResearchDataSourceReadinessSummary, "__slots__")
    assert not hasattr(summary, "__dict__")
    assert tuple(field.name for field in fields(ResearchDataSourceReadinessSummary)) == (
        "summary_type",
        "schema_version",
        "summary_scope",
        "summary_state",
        "required_control_count",
        "satisfied_control_count",
        "missing_control_count",
        "diagnostic_limitations",
        "source_readiness",
    )

    with pytest.raises(FrozenInstanceError):
        summary.summary_state = "blocked"
    with pytest.raises((AttributeError, TypeError)):
        summary.extra_field = "not allowed"


def test_control_counts_and_summary_state_mirror_source_readiness() -> None:
    source = expected_synthetic_research_data_source_readiness()
    summary = build_research_data_source_readiness_summary(source)

    assert summary.summary_state == source.readiness_state == "candidate_only"
    assert summary.required_control_count == 6
    assert summary.satisfied_control_count == 1
    assert summary.missing_control_count == 5
    assert summary.missing_control_count == len(source.missing_controls)

    complete_source = _build_readiness(
        readiness_state="metadata_ready",
        required_controls=["terms_review", "schema_review"],
        satisfied_controls=["terms_review", "schema_review"],
    )
    complete_summary = build_research_data_source_readiness_summary(complete_source)

    assert complete_summary.summary_state == "metadata_ready"
    assert complete_summary.required_control_count == 2
    assert complete_summary.satisfied_control_count == 2
    assert complete_summary.missing_control_count == 0


@pytest.mark.parametrize("state", ("not_reviewed", "blocked", "candidate_only"))
def test_summary_state_mirrors_non_complete_source_states(state: str) -> None:
    source = _build_readiness(readiness_state=state)
    summary = build_research_data_source_readiness_summary(source)

    assert summary.summary_state == state
    assert summary.to_dict()["summary_state"] == state
    assert "ready_to_trade" not in summary.to_dict()


def test_diagnostic_limitations_are_sorted_deduped_source_metadata() -> None:
    source = _build_readiness(
        limitations=[
            "zeta diagnostic metadata only",
            "alpha diagnostic metadata only",
            "zeta diagnostic metadata only",
        ]
    )
    summary = build_research_data_source_readiness_summary(source)

    assert summary.diagnostic_limitations == (
        "alpha diagnostic metadata only",
        "zeta diagnostic metadata only",
    )
    assert summary.to_dict()["diagnostic_limitations"] == [
        "alpha diagnostic metadata only",
        "zeta diagnostic metadata only",
    ]


def test_direct_construction_rejects_mismatched_source_derived_values() -> None:
    source = expected_synthetic_research_data_source_readiness()
    payload = _direct_payload(source)

    for field_name, value in (
        ("summary_type", "other"),
        ("schema_version", "2"),
        ("summary_scope", "other"),
        ("summary_state", "blocked"),
        ("required_control_count", 99),
        ("satisfied_control_count", 99),
        ("missing_control_count", 99),
        ("diagnostic_limitations", ("other diagnostic metadata only",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchDataSourceReadinessSummary(**mutated)

    for field_name, value in (
        ("required_control_count", True),
        ("satisfied_control_count", -1),
        ("missing_control_count", "5"),
        ("diagnostic_limitations", ()),
        ("diagnostic_limitations", ("",)),
        ("summary_state", " "),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            ResearchDataSourceReadinessSummary(**mutated)


def test_to_dict_is_primitive_deterministic_and_has_no_source_wrapper() -> None:
    summary = build_research_data_source_readiness_summary(
        expected_synthetic_research_data_source_readiness()
    )
    first = summary.to_dict()
    second = summary.to_dict()

    assert list(first) == EXPECTED_KEYS
    assert first == second
    assert first == expected_synthetic_research_data_source_readiness_summary_dict(
        build_research_data_source_readiness_summary
    )
    assert _primitive_only(first)
    assert "source_readiness" not in first
    assert "source_readiness" not in _payload_keys(first)
    assert first["diagnostic_limitations"] is not second["diagnostic_limitations"]

    first["diagnostic_limitations"].append("mutated copy")
    assert second == expected_synthetic_research_data_source_readiness_summary_dict(
        build_research_data_source_readiness_summary
    )


def test_compact_sorted_json_is_byte_deterministic() -> None:
    summary = build_research_data_source_readiness_summary(
        expected_synthetic_research_data_source_readiness()
    )
    first_json = _compact_sorted_json(summary.to_dict()).encode("utf-8")
    second_json = _compact_sorted_json(summary.to_dict()).encode("utf-8")

    assert first_json == second_json
    assert first_json == (
        expected_synthetic_research_data_source_readiness_summary_json(
            build_research_data_source_readiness_summary
        ).encode("utf-8")
    )
    assert json.loads(first_json.decode("utf-8")) == (
        expected_synthetic_research_data_source_readiness_summary_dict(
            build_research_data_source_readiness_summary
        )
    )


def test_repeated_builds_are_equal_with_distinct_source_identities() -> None:
    first_source = expected_synthetic_research_data_source_readiness()
    second_source = expected_synthetic_research_data_source_readiness()
    first = build_research_data_source_readiness_summary(first_source)
    second = build_research_data_source_readiness_summary(second_source)

    assert first_source == second_source
    assert first_source is not second_source
    assert first == second
    assert first is not second
    assert first.source_readiness is first_source
    assert second.source_readiness is second_source
    assert first.to_dict() == second.to_dict()


def test_source_readiness_payload_is_unchanged_by_summary_build() -> None:
    source = expected_synthetic_research_data_source_readiness()
    before = source.to_dict()
    summary = build_research_data_source_readiness_summary(source)
    after_build = source.to_dict()
    after_dict = summary.to_dict()
    after_summary_serialization = source.to_dict()

    assert after_build == before
    assert after_summary_serialization == before
    assert after_dict == expected_synthetic_research_data_source_readiness_summary_dict(
        build_research_data_source_readiness_summary
    )
    assert "source_readiness" not in after_dict


def test_public_surface_imports_and_source_are_metadata_only() -> None:
    import_details = _import_details_from_path(MODULE_PATH)
    source = _source_text_from_path(MODULE_PATH)
    calls = _call_names_from_path(MODULE_PATH)

    assert summary_module.__all__ == [
        "ResearchDataSourceReadinessSummary",
        "build_research_data_source_readiness_summary",
    ]
    assert import_details == ALLOWED_IMPORTS
    assert _matching_imports(set(import_details), FORBIDDEN_IMPORT_PREFIXES) == []
    assert calls.isdisjoint(FORBIDDEN_CALL_NAMES)
    assert _forbidden_source_token_matches(source, FORBIDDEN_SOURCE_TOKENS) == []


def test_payload_keys_have_no_forbidden_operating_fields() -> None:
    payload = build_research_data_source_readiness_summary(
        expected_synthetic_research_data_source_readiness()
    ).to_dict()

    assert FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))
    assert "from_dict" not in _function_names_from_path(MODULE_PATH)


def _readiness_params() -> dict[str, object]:
    return {
        "source_id": "synthetic-readiness-candidate",
        "source_name": "Synthetic readiness candidate",
        "asset_class_scope": ["equity"],
        "intended_use": "metadata-only review candidate",
        "readiness_state": "candidate_only",
        "required_controls": [
            "terms_review",
            "schema_review",
            "coverage_review",
        ],
        "satisfied_controls": ["terms_review"],
        "evidence_refs": ["synthetic-readiness-note"],
        "limitations": ["diagnostic metadata only"],
        "non_claims": [
            "not operational use",
            "no market payload",
            "does not grant capital authority",
            "without live use",
        ],
    }


def _build_readiness(**overrides: object) -> ResearchDataSourceReadiness:
    params = _readiness_params()
    params.update(overrides)

    return build_research_data_source_readiness(**params)


def _direct_payload(source: ResearchDataSourceReadiness) -> dict[str, object]:
    return {
        "summary_type": "research_data_source_readiness_summary",
        "schema_version": "1",
        "summary_scope": "advisory_metadata_only",
        "summary_state": source.readiness_state,
        "required_control_count": len(source.required_controls),
        "satisfied_control_count": len(source.satisfied_controls),
        "missing_control_count": len(source.missing_controls),
        "diagnostic_limitations": tuple(sorted(set(source.limitations))),
        "source_readiness": source,
    }


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


def _forbidden_source_token_matches(
    source: str,
    tokens: tuple[str, ...],
) -> list[str]:
    return [
        token
        for token in tokens
        if _source_contains_token(source, token)
    ]


def _source_contains_token(source: str, token: str) -> bool:
    lowered_token = token.lower()

    for line in source.splitlines():
        lowered_line = line.lower()
        if _line_contains_token(lowered_line, lowered_token):
            return True

    return False


def _line_contains_token(lowered_line: str, token: str) -> bool:
    if re.match(r"^[a-z0-9_]+$", token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return token in lowered_line


def _compact_sorted_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


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


def _payload_keys(value: object) -> set[str]:
    if type(value) is dict:
        keys: set[str] = set()
        for key, nested_value in value.items():
            keys.add(key)
            keys.update(_payload_keys(nested_value))
        return keys

    if type(value) is list:
        keys: set[str] = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()
