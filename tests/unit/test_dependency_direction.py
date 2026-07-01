import ast
from dataclasses import dataclass
from pathlib import Path


SRC_PACKAGE_ROOT = Path("src/algotrader")


@dataclass(frozen=True)
class ImportReference:
    path: Path
    line: int
    module: str


@dataclass(frozen=True)
class DependencyRule:
    source: str
    paths: tuple[Path, ...]
    forbidden_prefixes: tuple[str, ...]


def _module_path(module_name: str) -> Path:
    return Path("src").joinpath(*module_name.split(".")).with_suffix(".py")


def _orchestration_boundary_rule(module_name: str) -> DependencyRule:
    return DependencyRule(
        source=module_name,
        paths=(_module_path(module_name),),
        forbidden_prefixes=EXECUTION_BOUNDARY_FORBIDDEN_PREFIXES,
    )


EXECUTION_BOUNDARY_FORBIDDEN_PREFIXES = (
    "algotrader.execution",
    "algotrader.execution.broker_base",
    "algotrader.execution.fake_broker",
    "algotrader.execution.local_broker",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.execution.alpaca_mapper",
    "algotrader.execution.alpaca_translator",
    "algotrader.orchestration.trade_flow",
    "algotrader.orchestration.signal_trade_flow",
    "alpaca",
    "alpaca_trade_api",
)

EXECUTION_BYPASS_FORBIDDEN_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration.trade_flow",
    "algotrader.orchestration.signal_trade_flow",
)

RESEARCH_BOUNDARY_FORBIDDEN_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)

ADVISORY_BOUNDARY_FORBIDDEN_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
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
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "ipynb",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "numpy",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)

GOVERNANCE_BOUNDARY_FORBIDDEN_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.broker",
    "algotrader.brokers",
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
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "ipynb",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)

ORCHESTRATION_BOUNDARY_MODULES = (
    "algotrader.orchestration.screener_signal_flow",
    "algotrader.orchestration.signal_risk_flow",
    "algotrader.orchestration.risk_execution_flow",
    "algotrader.orchestration.execution_planning_flow",
    "algotrader.orchestration.execution_planning_policy",
    "algotrader.orchestration.strategy_router",
    "algotrader.orchestration.etf_sma_execution_preview_bridge",
    "algotrader.orchestration.etf_sma_preview_jsonl_artifact",
    "algotrader.orchestration.etf_sma_paper_broker_preview",
    "algotrader.orchestration.etf_sma_paper_probe_operator_review",
)

ORCHESTRATION_BOUNDARY_RULES = tuple(
    _orchestration_boundary_rule(module_name)
    for module_name in ORCHESTRATION_BOUNDARY_MODULES
)


def test_core_time_contract_does_not_import_trading_runtime_or_nondeterminism() -> None:
    path = _module_path("algotrader.core.time")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_violations = [
        f"{import_reference.path}:{import_reference.line}: "
        f"core time contract must not import {import_reference.module}"
        for import_reference in _import_references(path)
        if _matches_forbidden_prefix(
            import_reference.module,
            CORE_TIME_FORBIDDEN_IMPORT_PREFIXES,
        )
    ]
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    referenced_names = {
        name
        for node in ast.walk(tree)
        for name in _node_reference_names(node)
    }

    assert import_violations == []
    assert call_names.isdisjoint(CORE_TIME_FORBIDDEN_CALLS)
    assert referenced_names.isdisjoint(CORE_TIME_FORBIDDEN_NAMES)


def test_screener_modules_do_not_import_downstream_layers() -> None:
    rule = DependencyRule(
        source="algotrader.screener.*",
        paths=_package_files("algotrader.screener"),
        forbidden_prefixes=(
            "algotrader.signals",
            "algotrader.risk",
            "algotrader.execution",
            "algotrader.portfolio",
            "algotrader.orchestration",
        ),
    )

    assert _dependency_violations(rule) == []


def test_research_contracts_do_not_import_trading_path_or_runtime_layers() -> None:
    rule = DependencyRule(
        source="algotrader.research.*",
        paths=_package_files("algotrader.research"),
        forbidden_prefixes=RESEARCH_BOUNDARY_FORBIDDEN_PREFIXES,
    )

    assert _dependency_violations(rule) == []


def test_research_planning_validation_helper_has_no_runtime_io_or_network_calls() -> None:
    path = _module_path("algotrader.research._planning_validation")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_violations = [
        f"{import_reference.path}:{import_reference.line}: "
        f"planning validation helper must not import {import_reference.module}"
        for import_reference in _import_references(path)
        if _matches_forbidden_prefix(
            import_reference.module,
            RESEARCH_BOUNDARY_FORBIDDEN_PREFIXES,
        )
    ]
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert import_violations == []
    assert call_names.isdisjoint(RESEARCH_PLANNING_VALIDATION_FORBIDDEN_CALLS)


def test_advisory_contracts_do_not_import_trading_runtime_or_ai_layers() -> None:
    rule = DependencyRule(
        source="algotrader.advisory.*",
        paths=_package_files("algotrader.advisory"),
        forbidden_prefixes=ADVISORY_BOUNDARY_FORBIDDEN_PREFIXES,
    )

    assert _dependency_violations(rule) == []


def test_governance_contracts_do_not_import_advisory_or_runtime_layers() -> None:
    rule = DependencyRule(
        source="algotrader.governance.*",
        paths=_package_files("algotrader.governance"),
        forbidden_prefixes=GOVERNANCE_BOUNDARY_FORBIDDEN_PREFIXES,
    )

    assert _dependency_violations(rule) == []


def test_signal_modules_do_not_import_downstream_or_screener_layers() -> None:
    rule = DependencyRule(
        source="algotrader.signals.*",
        paths=_package_files("algotrader.signals"),
        forbidden_prefixes=(
            "algotrader.research",
            "algotrader.screener",
            "algotrader.risk",
            "algotrader.execution",
            "algotrader.portfolio",
            "algotrader.orchestration",
            "algotrader.scheduler",
            "algotrader.runtime",
            "algotrader.persistence",
            "algotrader.database",
            "algotrader.ml",
            "algotrader.llm",
            "algotrader.llms",
            "alpaca",
            "alpaca_trade_api",
            "anthropic",
            "database",
            "duckdb",
            "httpx",
            "langchain",
            "langgraph",
            "llm",
            "openai",
            "requests",
            "socket",
            "sqlmodel",
            "urllib",
        ),
    )

    assert _dependency_violations(rule) == []


def test_signal_evaluation_input_contract_has_no_downstream_or_nondeterministic_calls() -> None:
    path = _module_path("algotrader.signals.signal_evaluation_input")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_violations = [
        f"{import_reference.path}:{import_reference.line}: "
        f"signal evaluation input contract must not import {import_reference.module}"
        for import_reference in _import_references(path)
        if _matches_forbidden_prefix(
            import_reference.module,
            SIGNAL_EVALUATION_INPUT_FORBIDDEN_IMPORT_PREFIXES,
        )
    ]
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    referenced_names = {
        name
        for node in ast.walk(tree)
        for name in _node_reference_names(node)
    }

    assert import_violations == []
    assert call_names.isdisjoint(SIGNAL_EVALUATION_INPUT_FORBIDDEN_CALLS)
    assert referenced_names.isdisjoint(SIGNAL_EVALUATION_INPUT_FORBIDDEN_NAMES)


def test_risk_modules_do_not_import_signal_screener_or_execution_layers() -> None:
    rule = DependencyRule(
        source="algotrader.risk.*",
        paths=_package_files("algotrader.risk"),
        forbidden_prefixes=(
            "algotrader.screener",
            "algotrader.signals",
            "algotrader.orchestration",
            "algotrader.execution",
        ),
    )

    assert _dependency_violations(rule) == []


def test_screener_signal_flow_does_not_import_execution_or_broker_layers() -> None:
    violations: list[str] = []
    for rule in ORCHESTRATION_BOUNDARY_RULES:
        violations.extend(_dependency_violations(rule))

    assert violations == []


def test_pre_execution_orchestration_chain_does_not_bypass_execution_boundary() -> None:
    rule = DependencyRule(
        source="pre-execution orchestration chain",
        paths=tuple(_module_path(module_name) for module_name in ORCHESTRATION_BOUNDARY_MODULES),
        forbidden_prefixes=EXECUTION_BYPASS_FORBIDDEN_PREFIXES,
    )

    assert _dependency_violations(rule) == []


def test_execution_planning_modules_do_not_call_runtime_or_broker_boundaries() -> None:
    modules = (
        "algotrader.orchestration.execution_planning_flow",
        "algotrader.orchestration.execution_planning_policy",
    )

    for module_name in modules:
        _assert_execution_planning_module_has_no_runtime_or_broker_boundaries(
            module_name
        )


def test_paper_lab_revalidation_brief_has_no_network_or_broker_sdk_paths() -> None:
    path = _module_path("algotrader.execution.paper_lab_revalidation_brief")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden_import_prefixes = (
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )
    import_violations = [
        f"{import_reference.path}:{import_reference.line}: "
        f"revalidation brief must not import {import_reference.module}"
        for import_reference in _import_references(path)
        if _matches_forbidden_prefix(
            import_reference.module,
            forbidden_import_prefixes,
        )
    ]
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    forbidden_calls = {
        "cancel_order",
        "close_position",
        "connect",
        "create_order",
        "liquidate",
        "request",
        "socket.socket",
        "submit_order",
        "urlopen",
    }

    assert import_violations == []
    assert call_names.isdisjoint(forbidden_calls)


def _assert_execution_planning_module_has_no_runtime_or_broker_boundaries(
    module_name: str,
) -> None:
    path = _module_path(module_name)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_violations = [
        f"{import_reference.path}:{import_reference.line}: "
        f"execution planning must not import {import_reference.module}"
        for import_reference in _import_references(path)
        if _matches_forbidden_prefix(
            import_reference.module,
            EXECUTION_PLANNING_FORBIDDEN_IMPORT_PREFIXES,
        )
    ]
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    referenced_names = {
        name
        for node in ast.walk(tree)
        for name in _node_reference_names(node)
    }

    assert import_violations == []
    assert call_names.isdisjoint(EXECUTION_PLANNING_FORBIDDEN_CALLS)
    assert referenced_names.isdisjoint(EXECUTION_PLANNING_FORBIDDEN_NAMES)


def _package_files(package: str) -> tuple[Path, ...]:
    package_path = Path("src").joinpath(*package.split("."))
    return tuple(sorted(package_path.rglob("*.py")))


def _dependency_violations(rule: DependencyRule) -> list[str]:
    violations: list[str] = []

    for path in rule.paths:
        for import_reference in _import_references(path):
            if _matches_forbidden_prefix(
                import_reference.module,
                rule.forbidden_prefixes,
            ):
                violations.append(
                    f"{import_reference.path}:{import_reference.line}: "
                    f"{rule.source} must not import {import_reference.module}"
                )

    return violations


def _import_references(path: Path) -> tuple[ImportReference, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[ImportReference] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                ImportReference(path=path, line=node.lineno, module=alias.name)
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imports.extend(
                ImportReference(path=path, line=node.lineno, module=module)
                for module in _import_from_modules(path, node)
            )

    return tuple(imports)


def _import_from_modules(path: Path, node: ast.ImportFrom) -> tuple[str, ...]:
    if node.level == 0:
        return (node.module,) if node.module else ()

    base_module = _relative_import_base(path, node.level)
    if node.module:
        return (f"{base_module}.{node.module}",)

    return tuple(f"{base_module}.{alias.name}" for alias in node.names)


def _relative_import_base(path: Path, level: int) -> str:
    module_name = _module_name(path)
    if path.name == "__init__.py":
        package_name = module_name
    else:
        package_name = module_name.rsplit(".", maxsplit=1)[0]

    package_parts = package_name.split(".")
    base_parts = package_parts[: len(package_parts) - level + 1]
    return ".".join(base_parts)


def _module_name(path: Path) -> str:
    relative_path = path.relative_to(SRC_PACKAGE_ROOT.parent)
    return ".".join(relative_path.with_suffix("").parts)


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


EXECUTION_PLANNING_FORBIDDEN_CALLS = {
    "client_order_id",
    "idempotency",
    "persist",
    "submit_order",
}

EXECUTION_PLANNING_FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.scheduler",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
)

EXECUTION_PLANNING_FORBIDDEN_NAMES = {
    "alpaca",
    "alpaca_trade_api",
    "broker",
    "client_order_id",
    "database",
    "duckdb",
    "execution",
    "idempotency",
    "langgraph",
    "llm",
    "ml",
    "persistence",
    "runtime",
    "scheduler",
    "sqlmodel",
    "submit_order",
}

CORE_TIME_FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
)

CORE_TIME_FORBIDDEN_CALLS = {
    "datetime.now",
    "datetime.utcnow",
    "environ.get",
    "getenv",
    "open",
    "os.environ.get",
    "os.getenv",
    "random",
    "random.random",
    "read",
    "request",
    "time.monotonic",
    "time.time",
    "uuid.uuid4",
    "uuid4",
    "write",
}

CORE_TIME_FORBIDDEN_NAMES = {
    "alpaca",
    "broker",
    "client_order_id",
    "database",
    "duckdb",
    "environ",
    "execution",
    "execution_intent",
    "execution_plan",
    "fill",
    "idempotency",
    "langgraph",
    "llm",
    "ml",
    "monotonic",
    "order",
    "os",
    "persistence",
    "portfolio",
    "random",
    "risk",
    "runtime",
    "scheduler",
    "sqlmodel",
    "submit_order",
    "time",
    "uuid",
    "uuid4",
}

SIGNAL_EVALUATION_INPUT_FORBIDDEN_IMPORT_PREFIXES = (
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.runtime",
    "algotrader.persistence",
    "algotrader.database",
    "algotrader.ml",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.signals.signal_evaluation_result",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
)

SIGNAL_EVALUATION_INPUT_FORBIDDEN_CALLS = {
    "connect",
    "create_order",
    "datetime.now",
    "datetime.utcnow",
    "environ.get",
    "get",
    "getenv",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "random",
    "random.random",
    "read",
    "request",
    "schedule",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_sql",
    "uuid.uuid4",
    "uuid4",
    "write",
}

RESEARCH_PLANNING_VALIDATION_FORBIDDEN_CALLS = {
    "__import__",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "eval",
    "exec",
    "get",
    "getenv",
    "import_module",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "random",
    "random.random",
    "read",
    "read_csv",
    "request",
    "rglob",
    "socket.socket",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_sql",
    "urlopen",
    "write",
    "write_text",
}

SIGNAL_EVALUATION_INPUT_FORBIDDEN_NAMES = {
    "account_id",
    "alpaca",
    "approved",
    "broker",
    "broker_order_id",
    "buying_power",
    "cash",
    "client_order_id",
    "confidence",
    "database",
    "duckdb",
    "execution",
    "execution_intent",
    "execution_plan",
    "fill",
    "fill_id",
    "langgraph",
    "limit_price",
    "llm",
    "ml",
    "notional",
    "order",
    "order_type",
    "persistence",
    "portfolio",
    "position_id",
    "priority",
    "quantity",
    "rank",
    "rejected",
    "risk",
    "risk_approved",
    "runtime",
    "scheduler",
    "score",
    "side",
    "SignalEvaluationResult",
    "signal_evaluation_result",
    "signal_direction",
    "sqlmodel",
    "stop_price",
    "strategy",
    "submit_order",
    "symbol",
    "time_in_force",
}


def _node_reference_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)

    if isinstance(node, ast.Attribute):
        return (node.attr,)

    return ()


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
