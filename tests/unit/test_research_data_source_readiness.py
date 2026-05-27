from __future__ import annotations

import ast
import json
import re
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import research_data_source_readiness as readiness_module
from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
    build_research_data_source_readiness,
)


def _s(*parts: str) -> str:
    return "".join(parts)


SOURCE_PATH = Path("src/algotrader/research/research_data_source_readiness.py")
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
ALLOWED_IMPORTS = {
    "__future__": ("annotations",),
    "dataclasses": ("dataclass",),
    "algotrader.errors": ("ValidationError",),
}
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("al", "paca"),
    _s("al", "paca_trade_a", "pi"),
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.config",
    "algotrader.data",
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
    "print",
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
    _s("back", "test"),
    _s("bro", "ker"),
    _s("down", "load"),
    "duckdb",
    "env",
    _s("fi", "le"),
    _s("fi", "ll"),
    "httpx",
    _s("ing", "est"),
    "llm",
    "ml",
    _s("net", "work"),
    "notebook",
    "os",
    "pandas",
    _s("path", "lib"),
    "polars",
    _s("port", "folio"),
    "QuantConnect",
    "quantconnect",
    _s("re", "quests"),
    _s("run", "time"),
    _s("sche", "duler"),
    _s("so", "cket"),
    "urllib",
    "vectorbt",
    "vendor",
    "yfinance",
)


def test_builder_creates_frozen_slotted_metadata_only_object() -> None:
    contract = _build_contract()

    assert isinstance(contract, ResearchDataSourceReadiness)
    assert is_dataclass(contract)
    assert not hasattr(contract, "__dict__")

    with pytest.raises(FrozenInstanceError):
        contract.source_id = "changed"  # type: ignore[misc]


def test_fixed_metadata_is_pinned_and_builder_excludes_fixed_inputs() -> None:
    contract = _build_contract()

    assert readiness_module.__all__ == [
        "ResearchDataSourceReadiness",
        "build_research_data_source_readiness",
    ]
    assert contract.contract_type == "research_data_source_readiness"
    assert contract.schema_version == "1"

    with pytest.raises(ValidationError, match="contract_type"):
        _direct_contract(contract_type="other")

    with pytest.raises(ValidationError, match="schema_version"):
        _direct_contract(schema_version="2")


def test_list_inputs_are_converted_to_tuples() -> None:
    contract = _build_contract(
        asset_class_scope=["equity", "rate_proxy"],
        required_controls=["terms_review", "schema_review"],
        satisfied_controls=["terms_review"],
        evidence_refs=["synthetic-control-note"],
        limitations=["synthetic metadata only"],
        non_claims=["not source approval"],
    )

    assert contract.asset_class_scope == ("equity", "rate_proxy")
    assert contract.required_controls == ("terms_review", "schema_review")
    assert contract.satisfied_controls == ("terms_review",)
    assert contract.missing_controls == ("schema_review",)
    assert contract.evidence_refs == ("synthetic-control-note",)
    assert contract.limitations == ("synthetic metadata only",)
    assert contract.non_claims == ("not source approval",)


def test_builder_computes_missing_controls_in_required_control_order() -> None:
    contract = _build_contract(
        required_controls=[
            "terms_review",
            "schema_review",
            "quality_review",
            "coverage_review",
        ],
        satisfied_controls=["quality_review", "terms_review"],
    )

    assert contract.missing_controls == ("schema_review", "coverage_review")


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("asset_class_scope", ["equity", "equity"]),
        ("required_controls", ["terms_review", "terms_review"]),
        ("satisfied_controls", ["terms_review", "terms_review"]),
        ("evidence_refs", ["synthetic-note", "synthetic-note"]),
    ),
)
def test_duplicate_controls_scopes_and_evidence_refs_are_rejected(
    field_name: str,
    value: list[str],
) -> None:
    params = _builder_params()
    params[field_name] = value

    with pytest.raises(ValidationError, match="duplicates"):
        build_research_data_source_readiness(**params)


def test_duplicate_missing_controls_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicates"):
        _direct_contract(
            required_controls=("terms_review", "schema_review"),
            satisfied_controls=(),
            missing_controls=("schema_review", "schema_review"),
        )


def test_unknown_satisfied_controls_are_rejected() -> None:
    with pytest.raises(ValidationError, match="satisfied_controls"):
        _build_contract(satisfied_controls=["terms_review", "unknown_control"])


def test_direct_contract_requires_matching_missing_controls() -> None:
    with pytest.raises(ValidationError, match="missing_controls"):
        _direct_contract(
            required_controls=("terms_review", "schema_review"),
            satisfied_controls=("terms_review",),
            missing_controls=("terms_review",),
        )


def test_metadata_ready_requires_no_missing_controls() -> None:
    with pytest.raises(ValidationError, match="metadata_ready"):
        _build_contract(readiness_state="metadata_ready")

    contract = _build_contract(
        readiness_state="metadata_ready",
        satisfied_controls=["terms_review", "schema_review", "quality_review"],
    )

    assert contract.missing_controls == ()


@pytest.mark.parametrize("state", ("candidate_only", "blocked", "not_reviewed"))
def test_non_metadata_ready_states_can_carry_missing_controls(state: str) -> None:
    contract = _build_contract(readiness_state=state)

    assert contract.readiness_state == state
    assert contract.missing_controls == ("schema_review", "quality_review")


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("source_id", ""),
        ("source_name", " "),
        ("intended_use", "\t"),
        ("readiness_state", ""),
        ("asset_class_scope", ["equity", ""]),
        ("required_controls", ["terms_review", " "]),
        ("satisfied_controls", [""]),
        ("evidence_refs", ["synthetic-note", " "]),
        ("limitations", []),
        ("limitations", [""]),
        ("non_claims", []),
        ("non_claims", [""]),
    ),
)
def test_empty_and_blank_strings_are_rejected(field_name: str, value: object) -> None:
    params = _builder_params()
    params[field_name] = value

    with pytest.raises(ValidationError):
        build_research_data_source_readiness(**params)


def test_non_claims_must_be_negative_advisory_statements() -> None:
    with pytest.raises(ValidationError, match="negative"):
        _build_contract(non_claims=["metadata only"])

    contract = _build_contract(
        non_claims=[
            "not source approval",
            "no market payload",
            "does not grant capital authority",
            "without trading authority",
            "non-production readiness",
        ]
    )

    assert contract.non_claims == (
        "not source approval",
        "no market payload",
        "does not grant capital authority",
        "without trading authority",
        "non-production readiness",
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("source_name", "Production readiness source"),
        ("intended_use", "approved for trading"),
        ("limitations", ["grants capital authority"]),
        ("non_claims", ["trading readiness"]),
    ),
)
def test_approval_readiness_trading_and_capital_language_is_rejected(
    field_name: str,
    value: object,
) -> None:
    params = _builder_params()
    params[field_name] = value

    with pytest.raises(ValidationError):
        build_research_data_source_readiness(**params)


def test_guarded_language_is_allowed_when_clearly_negative() -> None:
    contract = _build_contract(
        source_name="No Trading Authority Source Note",
        intended_use="not production readiness",
        limitations=[
            "not approved for source use",
            "without trading authority",
        ],
        non_claims=[
            "not trading readiness",
            "no capital authority",
            "does not approve real use",
            "without trading authority",
            "non-production readiness",
        ],
    )

    assert contract.source_name == "No Trading Authority Source Note"
    assert contract.intended_use == "not production readiness"


def test_to_dict_is_primitive_json_round_trippable() -> None:
    contract = _build_contract()
    payload = contract.to_dict()
    encoded = _compact_sorted_json(payload)

    assert list(payload) == EXPECTED_KEYS
    assert _primitive_only(payload)
    assert json.loads(encoded) == payload
    assert payload["asset_class_scope"] == list(contract.asset_class_scope)
    assert payload["missing_controls"] == list(contract.missing_controls)


def test_to_dict_and_compact_sorted_json_are_byte_deterministic() -> None:
    contract = _build_contract()
    first_payload = contract.to_dict()
    second_payload = contract.to_dict()
    first_json = _compact_sorted_json(first_payload).encode("utf-8")
    second_json = _compact_sorted_json(second_payload).encode("utf-8")

    assert first_payload == second_payload
    assert first_json == second_json


def test_source_module_imports_only_deterministic_safe_dependencies() -> None:
    import_details = _import_details_from_path(SOURCE_PATH)

    assert import_details == ALLOWED_IMPORTS
    assert _matching_imports(
        set(import_details),
        FORBIDDEN_IMPORT_PREFIXES,
    ) == []


def test_source_has_no_forbidden_runtime_data_or_trading_surfaces() -> None:
    source = _source_text_from_path(SOURCE_PATH)
    calls = _call_names_from_path(SOURCE_PATH)

    assert calls.isdisjoint(FORBIDDEN_CALL_NAMES)
    assert _forbidden_source_token_matches(source, FORBIDDEN_SOURCE_TOKENS) == []


def _builder_params() -> dict[str, object]:
    return {
        "source_id": "synthetic-source-candidate",
        "source_name": "Synthetic Source Candidate",
        "asset_class_scope": ["equity"],
        "intended_use": "metadata-only review candidate",
        "readiness_state": "candidate_only",
        "required_controls": [
            "terms_review",
            "schema_review",
            "quality_review",
        ],
        "satisfied_controls": ["terms_review"],
        "evidence_refs": ["synthetic-readiness-note"],
        "limitations": ["synthetic metadata only"],
        "non_claims": [
            "not source approval",
            "no market payload",
            "does not grant capital authority",
            "without trading authority",
        ],
    }


def _build_contract(**overrides: object) -> ResearchDataSourceReadiness:
    params = _builder_params()
    params.update(overrides)

    return build_research_data_source_readiness(**params)


def _direct_contract(**overrides: object) -> ResearchDataSourceReadiness:
    params = {
        "contract_type": "research_data_source_readiness",
        "schema_version": "1",
        **_builder_params(),
        "missing_controls": ("schema_review", "quality_review"),
    }
    params.update(overrides)

    return ResearchDataSourceReadiness(**params)


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
