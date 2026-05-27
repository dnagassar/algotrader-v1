from __future__ import annotations

import ast
import inspect
import json
import re
from dataclasses import is_dataclass
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import research_data_source_readiness as readiness_module
from algotrader.research import (
    research_data_source_readiness_summary as summary_module,
)
from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
    build_research_data_source_readiness,
)
from algotrader.research.research_data_source_readiness_summary import (
    ResearchDataSourceReadinessSummary,
    build_research_data_source_readiness_summary,
)


SOURCE_PATH = Path("src/algotrader/research/research_data_source_readiness.py")
SUMMARY_SOURCE_PATH = Path(
    "src/algotrader/research/research_data_source_readiness_summary.py"
)
EXPECTED_PUBLIC_SURFACE = [
    "ResearchDataSourceReadiness",
    "build_research_data_source_readiness",
]
EXPECTED_SUMMARY_PUBLIC_SURFACE = [
    "ResearchDataSourceReadinessSummary",
    "build_research_data_source_readiness_summary",
]
EXPECTED_BUILDER_PARAMS = [
    "source_id",
    "source_name",
    "asset_class_scope",
    "intended_use",
    "readiness_state",
    "required_controls",
    "satisfied_controls",
    "evidence_refs",
    "limitations",
    "non_claims",
]
EXPECTED_TO_DICT_KEYS = [
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
EXPECTED_SUMMARY_TO_DICT_KEYS = [
    "summary_type",
    "schema_version",
    "summary_scope",
    "summary_state",
    "required_control_count",
    "satisfied_control_count",
    "missing_control_count",
    "diagnostic_limitations",
]

# Phase 269 intentionally needs only deterministic stdlib/type support plus
# the local validation error. No collection/typing imports are currently needed.
EXPECTED_IMPORT_STATEMENTS = [
    ("from", "__future__", (("annotations", None),), 0),
    ("from", "dataclasses", (("dataclass", None),), 0),
    ("from", "algotrader.errors", (("ValidationError", None),), 0),
]
EXPECTED_SUMMARY_IMPORT_STATEMENTS = [
    ("from", "__future__", (("annotations", None),), 0),
    ("from", "dataclasses", (("dataclass", None),), 0),
    ("from", "algotrader.errors", (("ValidationError", None),), 0),
    (
        "from",
        "algotrader.research.research_data_source_readiness",
        (("ResearchDataSourceReadiness", None),),
        0,
    ),
]
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "algotrader.backtest",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.cli",
    "algotrader.config",
    "algotrader.data",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.notebook",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.signals",
    "algotrader.storage",
    "algotrader.strategy",
    "algotrader.vendor",
    "duckdb",
    "httpx",
    "os",
    "pandas",
    "pathlib",
    "polygon",
    "polars",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "urllib",
    "vectorbt",
    "yfinance",
)
FORBIDDEN_SOURCE_TOKENS = (
    "aiohttp",
    "alpaca",
    "api key",
    "api keys",
    "backtest",
    "benchmark",
    "broker",
    "credentials",
    "duckdb",
    "execution",
    "fill",
    "httpx",
    "llm",
    "ml",
    "network",
    "notebook",
    "order",
    "os",
    "pandas",
    "pathlib",
    "persistence",
    "polygon",
    "polars",
    "portfolio",
    "quantconnect",
    "requests",
    "runtime",
    "scheduler",
    "signal evaluator",
    "socket",
    "storage",
    "urllib",
    "vectorbt",
    "vendor",
    "yfinance",
)
FORBIDDEN_BEHAVIOR_TOKENS = (
    "Path(",
    "approved",
    "capital_authority=True",
    "datetime.now",
    "environ",
    "from_dict",
    "getenv",
    "httpx.",
    "open(",
    "random",
    "read_text",
    "requests.",
    "socket",
    "time.time",
    "trading authority",
    "trading_ready",
    "urllib.",
    "uuid",
    "write",
)
NEGATIVE_ADVISORY_ALLOWLIST = (
    "does not approve",
    "no trading authority",
    "not approved",
    "without trading authority",
)
OUTPUT_FORBIDDEN_TOKENS = (
    "api key",
    "broker",
    "credential",
    "env",
    "environ",
    "fill",
    "order",
    "portfolio",
    "runtime",
    "secret",
    "trading authority",
)
SUMMARY_OUTPUT_FORBIDDEN_KEYS = {
    "account",
    "approval_status",
    "authorization",
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
    "source_readiness",
    "timestamp",
    "token",
    "trading_authority",
    "trading_ready",
    "vendor",
    "wrapper",
}
OUTPUT_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"(^|[ \t])[/\\][A-Za-z0-9_.-]"),
    re.compile(r"[A-Za-z0-9_.-]+[/\\][A-Za-z0-9_.-]+"),
)


def test_source_imports_public_surface_and_dataclass_shape_are_pinned() -> None:
    tree = _source_tree()
    class_node = _class_node(tree, "ResearchDataSourceReadiness")

    assert _import_statements(tree) == EXPECTED_IMPORT_STATEMENTS
    assert _matching_imports(_imported_modules(tree), FORBIDDEN_IMPORT_PREFIXES) == []
    assert readiness_module.__all__ == EXPECTED_PUBLIC_SURFACE
    assert _public_defs(tree) == set(EXPECTED_PUBLIC_SURFACE)

    assert is_dataclass(ResearchDataSourceReadiness)
    assert ResearchDataSourceReadiness.__dataclass_params__.frozen is True
    assert not hasattr(_build_contract(), "__dict__")
    assert _dataclass_keyword_values(class_node) == {"frozen": True, "slots": True}


def test_builder_signature_fixed_metadata_and_missing_controls_are_pinned() -> None:
    tree = _source_tree()
    builder_node = _function_node(tree, "build_research_data_source_readiness")

    assert _assigned_literal(tree, "_CONTRACT_TYPE") == (
        "research_data_source_readiness"
    )
    assert _assigned_literal(tree, "_SCHEMA_VERSION") == "1"
    assert _assigned_literal(tree, "_READINESS_STATES") == (
        "not_reviewed",
        "blocked",
        "candidate_only",
        "metadata_ready",
    )
    assert _builder_parameter_names(builder_node) == EXPECTED_BUILDER_PARAMS
    assert _signature_parameter_kinds(
        build_research_data_source_readiness
    ) == {inspect.Parameter.KEYWORD_ONLY}
    assert "contract_type" not in inspect.signature(
        build_research_data_source_readiness
    ).parameters
    assert "schema_version" not in inspect.signature(
        build_research_data_source_readiness
    ).parameters
    assert "missing_controls" not in inspect.signature(
        build_research_data_source_readiness
    ).parameters

    builder_return = _single_return_call(builder_node, "ResearchDataSourceReadiness")
    assert _keyword_call_name(builder_return, "missing_controls") == "_missing_controls"
    assert _keyword_call_arg_names(builder_return, "missing_controls") == [
        "required",
        "satisfied",
    ]
    _assert_missing_controls_function_uses_required_minus_satisfied(tree)

    contract = _build_contract()
    assert contract.contract_type == "research_data_source_readiness"
    assert contract.schema_version == "1"
    assert contract.missing_controls == ("quality_review",)

    with pytest.raises(ValidationError, match="contract_type"):
        _direct_contract(contract_type="research_gate")

    with pytest.raises(ValidationError, match="schema_version"):
        _direct_contract(schema_version="2")


def test_source_has_no_forbidden_dependency_or_behavior_tokens() -> None:
    source = _source_text()
    tree = _source_tree()

    assert _matching_imports(_imported_modules(tree), FORBIDDEN_IMPORT_PREFIXES) == []
    assert _source_token_matches(source, FORBIDDEN_SOURCE_TOKENS) == []
    assert _source_token_matches(
        source,
        FORBIDDEN_BEHAVIOR_TOKENS,
        allow_negative_advisory=True,
    ) == []
    assert _call_names(tree).isdisjoint(
        {
            "__import__",
            "Path",
            "datetime.now",
            "eval",
            "exec",
            "getenv",
            "open",
            "os.getenv",
            "random",
            "read_text",
            "requests.get",
            "socket.socket",
            "time.time",
            "uuid4",
            "write",
        }
    )


def test_summary_source_imports_only_readiness_and_safe_stdlib() -> None:
    source = _source_text_from_path(SUMMARY_SOURCE_PATH)
    tree = _source_tree_from_path(SUMMARY_SOURCE_PATH)
    class_node = _class_node(tree, "ResearchDataSourceReadinessSummary")

    assert _import_statements(tree) == EXPECTED_SUMMARY_IMPORT_STATEMENTS
    assert _matching_imports(_imported_modules(tree), FORBIDDEN_IMPORT_PREFIXES) == []
    assert summary_module.__all__ == EXPECTED_SUMMARY_PUBLIC_SURFACE
    assert _public_defs(tree) == set(EXPECTED_SUMMARY_PUBLIC_SURFACE)
    assert is_dataclass(ResearchDataSourceReadinessSummary)
    assert ResearchDataSourceReadinessSummary.__dataclass_params__.frozen is True
    assert not hasattr(_build_summary(), "__dict__")
    assert _dataclass_keyword_values(class_node) == {"frozen": True, "slots": True}
    assert _source_token_matches(source, FORBIDDEN_SOURCE_TOKENS) == []
    assert _source_token_matches(
        source,
        FORBIDDEN_BEHAVIOR_TOKENS,
        allow_negative_advisory=True,
    ) == []
    assert _call_names(tree).isdisjoint(
        {
            "__import__",
            "Path",
            "datetime.now",
            "eval",
            "exec",
            "getenv",
            "open",
            "os.getenv",
            "random",
            "read_text",
            "requests.get",
            "socket.socket",
            "time.time",
            "uuid4",
            "write",
        }
    )


def test_summary_builder_is_source_derived_diagnostic_and_payload_only() -> None:
    source = _build_contract(
        required_controls=["terms_review", "schema_review", "quality_review"],
        satisfied_controls=["terms_review"],
        limitations=[
            "z synthetic diagnostic limit",
            "a synthetic diagnostic limit",
        ],
    )
    summary = build_research_data_source_readiness_summary(source)
    payload = summary.to_dict()
    repeated_payload = build_research_data_source_readiness_summary(source).to_dict()

    assert summary.source_readiness is source
    assert list(payload) == EXPECTED_SUMMARY_TO_DICT_KEYS
    assert payload == {
        "summary_type": "research_data_source_readiness_summary",
        "schema_version": "1",
        "summary_scope": "advisory_metadata_only",
        "summary_state": "candidate_only",
        "required_control_count": 3,
        "satisfied_control_count": 1,
        "missing_control_count": 2,
        "diagnostic_limitations": [
            "a synthetic diagnostic limit",
            "z synthetic diagnostic limit",
        ],
    }
    assert payload == repeated_payload
    assert _primitive_only(payload)
    assert _payload_keys(payload).isdisjoint(SUMMARY_OUTPUT_FORBIDDEN_KEYS)
    assert _output_safety_violations(payload) == []

    for value in (
        source.to_dict(),
        _ReadinessLookalike(source),
    ):
        with pytest.raises(ValidationError, match="source_readiness"):
            build_research_data_source_readiness_summary(value)


def test_behavior_rejects_unknown_duplicates_missing_metadata_and_authority() -> None:
    with pytest.raises(ValidationError, match="satisfied_controls"):
        _build_contract(satisfied_controls=["terms_review", "unknown_control"])

    for field_name, value in (
        ("asset_class_scope", ["equity", "equity"]),
        ("required_controls", ["terms_review", "terms_review"]),
        ("satisfied_controls", ["terms_review", "terms_review"]),
        ("evidence_refs", ["synthetic-note", "synthetic-note"]),
    ):
        params = _builder_params()
        params[field_name] = value
        with pytest.raises(ValidationError, match="duplicates"):
            build_research_data_source_readiness(**params)

    with pytest.raises(ValidationError, match="duplicates"):
        _direct_contract(missing_controls=("quality_review", "quality_review"))

    with pytest.raises(ValidationError, match="limitations"):
        _build_contract(limitations=[])

    with pytest.raises(ValidationError, match="non_claims"):
        _build_contract(non_claims=[])

    with pytest.raises(ValidationError, match="negative"):
        _build_contract(non_claims=["metadata only"])

    for field_name, value in (
        ("source_name", "approved research candidate"),
        ("intended_use", "approved for trading"),
        ("limitations", ["grants capital authority"]),
        ("non_claims", ["trading readiness"]),
    ):
        params = _builder_params()
        params[field_name] = value
        with pytest.raises(ValidationError):
            build_research_data_source_readiness(**params)

    negative_contract = _build_contract(
        intended_use="not approved for trading",
        non_claims=[
            "not approved for trading",
            "no trading authority",
        ],
    )
    assert negative_contract.intended_use == "not approved for trading"
    assert negative_contract.non_claims == (
        "not approved for trading",
        "no trading authority",
    )


def test_readiness_state_missing_control_and_primitive_output_regressions() -> None:
    encoded_payloads: list[bytes] = []

    with pytest.raises(ValidationError, match="metadata_ready"):
        _build_contract(
            readiness_state="metadata_ready",
            required_controls=["terms_review", "schema_review"],
            satisfied_controls=["terms_review"],
        )

    for state in ("not_reviewed", "blocked", "candidate_only"):
        contract = _build_contract(
            readiness_state=state,
            required_controls=["terms_review", "schema_review"],
            satisfied_controls=["terms_review"],
        )
        assert contract.missing_controls == ("schema_review",)

    contract = _build_contract(
        readiness_state="metadata_ready",
        required_controls=["terms_review", "schema_review"],
        satisfied_controls=["terms_review", "schema_review"],
    )
    payload = contract.to_dict()
    first_json = _compact_sorted_json(payload).encode("utf-8")
    second_json = _compact_sorted_json(contract.to_dict()).encode("utf-8")
    encoded_payloads.extend([first_json, second_json])

    assert list(payload) == EXPECTED_TO_DICT_KEYS
    assert _primitive_only(payload)
    assert json.loads(first_json.decode("utf-8")) == payload
    assert encoded_payloads[0] == encoded_payloads[1]
    assert payload["missing_controls"] == []
    assert payload["asset_class_scope"] == ["equity", "rate_proxy"]
    assert _output_safety_violations(payload) == []


def _builder_params() -> dict[str, object]:
    return {
        "source_id": "synthetic-source-candidate",
        "source_name": "Synthetic Source Candidate",
        "asset_class_scope": ["equity", "rate_proxy"],
        "intended_use": "metadata-only review candidate",
        "readiness_state": "candidate_only",
        "required_controls": [
            "terms_review",
            "schema_review",
            "quality_review",
        ],
        "satisfied_controls": ["terms_review", "schema_review"],
        "evidence_refs": ["synthetic-readiness-note"],
        "limitations": ["synthetic metadata only"],
        "non_claims": [
            "not source adoption",
            "no market payload",
            "does not grant production use",
            "without live use",
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
        "missing_controls": ("quality_review",),
    }
    params.update(overrides)

    return ResearchDataSourceReadiness(**params)


def _build_summary(**overrides: object) -> ResearchDataSourceReadinessSummary:
    source = _build_contract(**overrides)

    return build_research_data_source_readiness_summary(source)


class _ReadinessLookalike:
    def __init__(self, source: ResearchDataSourceReadiness) -> None:
        self.contract_type = source.contract_type
        self.schema_version = source.schema_version
        self.source_id = source.source_id
        self.source_name = source.source_name
        self.asset_class_scope = source.asset_class_scope
        self.intended_use = source.intended_use
        self.readiness_state = source.readiness_state
        self.required_controls = source.required_controls
        self.satisfied_controls = source.satisfied_controls
        self.missing_controls = source.missing_controls
        self.evidence_refs = source.evidence_refs
        self.limitations = source.limitations
        self.non_claims = source.non_claims


def _source_text() -> str:
    return SOURCE_PATH.read_text(encoding="utf-8")


def _source_tree() -> ast.Module:
    return ast.parse(_source_text(), filename=str(SOURCE_PATH))


def _source_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _source_tree_from_path(path: Path) -> ast.Module:
    return ast.parse(_source_text_from_path(path), filename=str(path))


def _import_statements(tree: ast.AST) -> list[tuple[str, str, tuple[tuple[str, str | None], ...], int]]:
    statements: list[tuple[str, str, tuple[tuple[str, str | None], ...], int]] = []

    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Import):
            for alias in node.names:
                statements.append(("import", alias.name, ((alias.name, alias.asname),), 0))
        elif isinstance(node, ast.ImportFrom):
            statements.append(
                (
                    "from",
                    node.module or "",
                    tuple((alias.name, alias.asname) for alias in node.names),
                    node.level,
                )
            )

    return statements


def _imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    return modules


def _matching_imports(
    imports: set[str],
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    return [
        module_name
        for module_name in sorted(imports)
        if any(
            module_name == prefix or module_name.startswith(f"{prefix}.")
            for prefix in forbidden_prefixes
        )
    ]


def _public_defs(tree: ast.AST) -> set[str]:
    if not isinstance(tree, ast.Module):
        return set()

    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def _class_node(tree: ast.AST, name: str) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node

    raise AssertionError(f"Missing class {name}.")


def _function_node(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node

    raise AssertionError(f"Missing function {name}.")


def _dataclass_keyword_values(class_node: ast.ClassDef) -> dict[str, object]:
    for decorator in class_node.decorator_list:
        if isinstance(decorator, ast.Call) and _call_name(decorator.func) == "dataclass":
            return {
                keyword.arg or "": ast.literal_eval(keyword.value)
                for keyword in decorator.keywords
            }

    raise AssertionError("ResearchDataSourceReadiness is missing @dataclass(...).")


def _assigned_literal(tree: ast.AST, name: str) -> object:
    if not isinstance(tree, ast.Module):
        raise AssertionError("Expected module AST.")

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)

    raise AssertionError(f"Missing assignment for {name}.")


def _builder_parameter_names(builder_node: ast.FunctionDef) -> list[str]:
    args = builder_node.args

    assert args.posonlyargs == []
    assert args.args == []
    assert args.vararg is None
    assert args.kwarg is None
    assert args.defaults == []
    assert args.kw_defaults == [None] * len(args.kwonlyargs)

    return [arg.arg for arg in args.kwonlyargs]


def _signature_parameter_kinds(function: object) -> set[inspect._ParameterKind]:
    return {parameter.kind for parameter in inspect.signature(function).parameters.values()}


def _single_return_call(function_node: ast.FunctionDef, call_name: str) -> ast.Call:
    returns = [
        node.value
        for node in ast.walk(function_node)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call)
    ]

    assert len(returns) == 1
    assert _call_name(returns[0].func) == call_name

    return returns[0]


def _keyword_call_name(call_node: ast.Call, keyword_name: str) -> str:
    value = _keyword_value(call_node, keyword_name)

    assert isinstance(value, ast.Call)

    return _call_name(value.func)


def _keyword_call_arg_names(call_node: ast.Call, keyword_name: str) -> list[str]:
    value = _keyword_value(call_node, keyword_name)

    assert isinstance(value, ast.Call)

    return [_name(arg) for arg in value.args]


def _keyword_value(call_node: ast.Call, keyword_name: str) -> ast.AST:
    for keyword in call_node.keywords:
        if keyword.arg == keyword_name:
            return keyword.value

    raise AssertionError(f"Missing keyword {keyword_name}.")


def _assert_missing_controls_function_uses_required_minus_satisfied(
    tree: ast.AST,
) -> None:
    function_node = _function_node(tree, "_missing_controls")
    return_node = next(
        node for node in function_node.body if isinstance(node, ast.Return)
    )

    assert isinstance(return_node.value, ast.Call)
    assert _call_name(return_node.value.func) == "tuple"
    assert len(return_node.value.args) == 1
    generator = return_node.value.args[0]
    assert isinstance(generator, ast.GeneratorExp)
    assert _name(generator.elt) == "control"
    assert len(generator.generators) == 1

    comprehension = generator.generators[0]
    assert _name(comprehension.target) == "control"
    assert _name(comprehension.iter) == "required_controls"
    assert len(comprehension.ifs) == 1

    condition = comprehension.ifs[0]
    assert isinstance(condition, ast.Compare)
    assert _name(condition.left) == "control"
    assert len(condition.ops) == 1
    assert isinstance(condition.ops[0], ast.NotIn)
    assert [_name(comparator) for comparator in condition.comparators] == [
        "satisfied_controls"
    ]


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


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    raise AssertionError(f"Expected name node, got {type(node).__name__}.")


def _source_token_matches(
    source: str,
    tokens: tuple[str, ...],
    *,
    allow_negative_advisory: bool = False,
) -> list[str]:
    matches: list[str] = []

    for line in source.splitlines():
        lowered_line = line.lower()
        for token in tokens:
            lowered_token = token.lower()
            if _line_contains_token(lowered_line, lowered_token) and not (
                allow_negative_advisory
                and _line_has_negative_advisory_allowance(lowered_line)
            ):
                matches.append(token)

    return sorted(set(matches))


def _line_contains_token(lowered_line: str, lowered_token: str) -> bool:
    if re.fullmatch(r"[a-z0-9_]+", lowered_token):
        return re.search(
            rf"(?<![a-z0-9_]){re.escape(lowered_token)}(?![a-z0-9_])",
            lowered_line,
        ) is not None

    return lowered_token in lowered_line


def _line_has_negative_advisory_allowance(lowered_line: str) -> bool:
    return any(allowed in lowered_line for allowed in NEGATIVE_ADVISORY_ALLOWLIST)


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


def _output_safety_violations(payload: dict[str, object]) -> list[str]:
    violations: list[str] = []

    for value in _flatten_strings(payload):
        lowered = value.lower()
        for token in OUTPUT_FORBIDDEN_TOKENS:
            if _line_contains_token(lowered, token):
                violations.append(token)
        for pattern in OUTPUT_PATH_PATTERNS:
            if pattern.search(value):
                violations.append(f"path:{value}")

    return sorted(set(violations))


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


def _flatten_strings(value: object) -> list[str]:
    if type(value) is str:
        return [value]
    if type(value) is list:
        return [
            item
            for value_item in value
            for item in _flatten_strings(value_item)
        ]
    if type(value) is dict:
        return [
            item
            for value_item in value.values()
            for item in _flatten_strings(value_item)
        ]

    return []
