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
    "algotrader.orchestration.cancellation_planning_flow",
    "algotrader.orchestration.cancellation_planning_policy",
    "algotrader.orchestration.strategy_router",
    "algotrader.orchestration.opportunity_router",
    "algotrader.orchestration.crypto_qty_sizing_preview",
    "algotrader.orchestration.crypto_paper_oms_handoff",
    "algotrader.orchestration.crypto_paper_oms_dry_run",
    "algotrader.orchestration.crypto_paper_submit_approval_packet",
    "algotrader.orchestration.crypto_paper_certification_ingestion",
    "algotrader.orchestration.crypto_paper_fill_exit_ingestion",
    "algotrader.orchestration.crypto_paper_autonomy_cadence",
    "algotrader.orchestration.crypto_no_submit_operating_cycle",
    "algotrader.orchestration.crypto_router_input_refresh_packet",
    "algotrader.orchestration.strategy_adapter_registry",
    "algotrader.orchestration.etf_sma_execution_preview_bridge",
    "algotrader.orchestration.etf_sma_preview_jsonl_artifact",
    "algotrader.orchestration.etf_sma_paper_broker_preview",
    "algotrader.orchestration.etf_sma_paper_probe_operator_review",
    (
        "algotrader.orchestration."
        "crypto_tournament_v2_bounded_paper_probe_review"
    ),
    (
        "algotrader.orchestration."
        "crypto_tournament_v2_bounded_paper_probe_capability_producer"
    ),
    "algotrader.orchestration.crypto_tournament_v2_oos_scheduler",
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


def test_paper_cancellation_planning_adapter_has_no_mutation_or_io_imports() -> None:
    rule = DependencyRule(
        source="paper cancellation planning adapter",
        paths=(
            _module_path(
                "algotrader.execution.paper_cancellation_planning_adapter"
            ),
        ),
        forbidden_prefixes=(
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.order_journal",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        ),
    )

    assert _dependency_violations(rule) == []


def test_paper_cancellation_candidate_selector_has_no_broker_or_io_boundary() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_candidate_selector"
    )
    rule = DependencyRule(
        source="paper cancellation candidate selector",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.paper_autopilot_control",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    referenced_names = {
        name
        for node in ast.walk(tree)
        for name in _node_reference_names(node)
    }
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert _dependency_violations(rule) == []
    assert referenced_names.isdisjoint(
        {
            "DurableCancelCoordinator",
            "SqliteOrderJournal",
            "broker_client",
            "cancel_order",
            "submit_order",
        }
    )
    assert call_names.isdisjoint(
        {
            "cancel_order",
            "connect",
            "datetime.now",
            "open",
            "records",
            "submit_order",
            "write",
        }
    )


def test_paper_cancellation_handoff_preview_has_no_coordinator_or_io_boundary() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_handoff_preview"
    )
    rule = DependencyRule(
        source="paper cancellation handoff preview",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.paper_autopilot_control",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    referenced_names = {
        name
        for node in ast.walk(tree)
        for name in _node_reference_names(node)
    }
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert _dependency_violations(rule) == []
    assert referenced_names.isdisjoint(
        {
            "DurableCancelCoordinator",
            "SqliteOrderJournal",
            "broker_client",
            "cancel",
            "cancel_order",
            "callback",
        }
    )
    assert call_names.isdisjoint(
        {
            "acquire_runtime_lease",
            "cancel_order",
            "connect",
            "datetime.now",
            "open",
            "reserve_cancel_intent",
            "submit_order",
            "write",
        }
    )


def test_paper_cancellation_admission_imports_only_durable_input_contracts() -> None:
    path = _module_path("algotrader.execution.paper_cancellation_admission")
    rule = DependencyRule(
        source="paper cancellation admission",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.local_broker",
            "algotrader.execution.order_journal",
            "algotrader.execution.paper_autopilot_control",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    contract_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "algotrader.execution.durable_cancel_contracts"
        for alias in node.names
    }
    coordinator_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "algotrader.execution.durable_cancel"
        for alias in node.names
    }
    referenced_names = {
        name
        for node in ast.walk(tree)
        for name in _node_reference_names(node)
    }
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert _dependency_violations(rule) == []
    assert contract_imports == {"DurableCancelEvidence", "DurableCancelIdentity"}
    assert coordinator_imports == set()
    assert referenced_names.isdisjoint(
        {
            "DurableCancelCoordinator",
            "SqliteOrderJournal",
            "broker_client",
            "cancel",
            "cancel_order",
            "callback",
        }
    )
    assert call_names.isdisjoint(
        {
            "acquire_lease",
            "cancel_order",
            "connect",
            "datetime.now",
            "execute",
            "open",
            "reserve",
            "submit_order",
            "write",
        }
    )


def test_durable_cancel_input_contracts_have_no_journal_or_coordinator_boundary() -> None:
    path = _module_path("algotrader.execution.durable_cancel_contracts")
    rule = DependencyRule(
        source="durable cancellation input contracts",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.order_journal",
            "algotrader.execution.paper_autopilot_control",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    referenced_names = {
        name
        for node in ast.walk(tree)
        for name in _node_reference_names(node)
    }
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert _dependency_violations(rule) == []
    assert referenced_names.isdisjoint(
        {
            "CancelIntent",
            "DurableCancelCoordinator",
            "SqliteOrderJournal",
            "cancel_order",
            "callback",
        }
    )
    assert call_names.isdisjoint(
        {
            "connect",
            "datetime.now",
            "execute",
            "open",
            "reserve",
            "write",
        }
    )


def test_cancellation_reconciliation_is_one_shot_and_broker_free() -> None:
    path = _module_path("algotrader.execution.cancellation_reconciliation")
    rule = DependencyRule(
        source="read-only cancellation reconciliation",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.paper_autopilot_control",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_exact_cancellation",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    workflow = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "reconcile_unresolved_cancellation"
    )
    argument_names = tuple(argument.arg for argument in workflow.args.args)
    call_names = [
        _call_name(node.func)
        for node in ast.walk(workflow)
        if isinstance(node, ast.Call)
    ]

    assert _dependency_violations(rule) == []
    assert argument_names == ("journal", "identity", "observation")
    forbidden_call_names = {
            "acquire_runtime_lease",
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "get_account",
            "get_order_by_id",
            "get_recent_orders",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
        }
    assert all(
        call_name.rsplit(".", maxsplit=1)[-1] not in forbidden_call_names
        for call_name in call_names
    )
    assert call_names.count(
        "journal.reconcile_unresolved_cancel_observation"
    ) == 1
    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(workflow))


def test_paper_cancellation_observation_is_one_exact_read_only_boundary() -> None:
    path = _module_path("algotrader.execution.paper_cancellation_observation")
    rule = DependencyRule(
        source="exact paper cancellation observation boundary",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.order_journal",
            "algotrader.execution.paper_autopilot_control",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_exact_cancellation",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    workflow = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "observe_exact_paper_cancellation"
    )
    call_names = [
        _call_name(node.func)
        for node in ast.walk(workflow)
        if isinstance(node, ast.Call)
    ]
    forbidden_call_names = {
        "acquire_runtime_lease",
        "cancel_order",
        "cancel_order_by_id",
        "close_all_positions",
        "close_position",
        "get_account",
        "get_order_by_id",
        "get_recent_orders",
        "reconcile_unresolved_cancellation",
        "replace_order",
        "request_order_cancellation",
        "submit_order",
        "submit_order_request",
        "unresolved_cancel_intents",
    }

    assert _dependency_violations(rule) == []
    assert call_names.count("read_exact_order") == 1
    assert all(
        call_name.rsplit(".", maxsplit=1)[-1] not in forbidden_call_names
        for call_name in call_names
    )
    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(workflow))


def test_crypto_read_only_paper_observation_adapter_does_not_import_downstream_layers() -> None:
    path = _module_path("algotrader.execution.crypto_read_only_paper_observation_adapter")
    rule = DependencyRule(
        source="crypto read-only paper observation adapter",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.advisory",
            "algotrader.governance",
            "algotrader.orchestration",
            "algotrader.portfolio",
            "algotrader.risk",
            "algotrader.screener",
            "algotrader.signals",
            "alpaca.trading",
            "alpaca_trade_api",
        ),
    )
    assert _dependency_violations(rule) == []


def test_paper_cancellation_sdk_binding_is_one_shot_and_read_only() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_observation_sdk"
    )
    rule = DependencyRule(
        source="exact paper cancellation SDK read binding",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.order_journal",
            "algotrader.execution.paper_autopilot_control",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_exact_cancellation",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    reader = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "__call__"
    )
    call_names = [
        _call_name(node.func)
        for node in ast.walk(reader)
        if isinstance(node, ast.Call)
    ]
    leaf_call_names = [name.rsplit(".", maxsplit=1)[-1] for name in call_names]

    assert _dependency_violations(rule) == []
    assert leaf_call_names.count("get_account") == 1
    assert leaf_call_names.count("get_order_by_id") == 1
    assert set(leaf_call_names).isdisjoint(
        {
            "acquire_runtime_lease",
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "get_orders",
            "get_recent_orders",
            "reconcile_unresolved_cancellation",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
        }
    )
    assert not any(
        isinstance(node, (ast.For, ast.While)) for node in ast.walk(reader)
    )


def test_paper_cancellation_reconciliation_workflow_is_the_single_composition() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_reconciliation_workflow"
    )
    rule = DependencyRule(
        source="exact paper cancellation reconciliation composition",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.config",
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.paper_autopilot_control",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_cancellation_observation_sdk",
            "algotrader.execution.paper_exact_cancellation",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    workflow = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "reconcile_exact_paper_cancellation"
    )
    call_names = [
        _call_name(node.func)
        for node in ast.walk(workflow)
        if isinstance(node, ast.Call)
    ]
    leaf_call_names = [name.rsplit(".", maxsplit=1)[-1] for name in call_names]

    assert _dependency_violations(rule) == []
    assert leaf_call_names.count("observe_exact_paper_cancellation") == 1
    assert leaf_call_names.count("reconcile_unresolved_cancellation") == 1
    assert set(leaf_call_names).isdisjoint(
        {
            "acquire_runtime_lease",
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "get_account",
            "get_order_by_id",
            "get_orders",
            "get_recent_orders",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
        }
    )
    assert not any(
        isinstance(node, (ast.For, ast.While)) for node in ast.walk(workflow)
    )


def test_paper_cancellation_reconciliation_operator_is_exact_and_pre_authorized() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_reconciliation_operator"
    )
    rule = DependencyRule(
        source="exact paper cancellation reconciliation operator binding",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.paper_autopilot_control",
            "algotrader.execution.paper_cancellation_admission",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_exact_cancellation",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    runner = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name
        == "run_exact_paper_cancellation_reconciliation_operator"
    )
    call_names = [
        _call_name(node.func)
        for node in ast.walk(runner)
        if isinstance(node, ast.Call)
    ]
    leaf_call_names = [name.rsplit(".", maxsplit=1)[-1] for name in call_names]

    assert _dependency_violations(rule) == []
    assert leaf_call_names.count("paper_cancellation_observation_blocker") == 1
    assert leaf_call_names.count("build_paper_cancellation_sdk_reader") == 1
    assert leaf_call_names.count("reconcile_exact_paper_cancellation") == 1
    assert leaf_call_names.count(
        "paper_cancellation_reconciliation_local_target_blocker"
    ) == 1
    assert leaf_call_names.count("get") == 1
    assert leaf_call_names.count("get_cancel_intent") == 1
    assert set(leaf_call_names).isdisjoint(
        {
            "build_paper_cancellation_observation_authorization",
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "get_account",
            "get_order_by_id",
            "get_orders",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
        }
    )
    assert not any(
        isinstance(node, (ast.For, ast.While)) for node in ast.walk(runner)
    )


def test_general_cli_cannot_reach_cancellation_reconciliation_operator() -> None:
    cli_path = _module_path("algotrader.cli")
    tree = ast.parse(
        cli_path.read_text(encoding="utf-8"),
        filename=str(cli_path),
    )
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert (
        "algotrader.execution.paper_cancellation_reconciliation_operator"
        not in imported_modules
    )


def test_cancellation_authorization_artifact_loader_is_read_only_and_cannot_mint() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_authorization_artifact"
    )
    rule = DependencyRule(
        source="exact cancellation authorization artifact loader",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.config",
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.order_journal",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_cancellation_reconciliation_operator",
            "algotrader.execution.paper_exact_cancellation",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = {
        _call_name(node.func).rsplit(".", maxsplit=1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert _dependency_violations(rule) == []
    assert "build_paper_cancellation_observation_authorization" not in calls
    assert calls.isdisjoint(
        {
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "get_account",
            "get_order_by_id",
            "get_orders",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
            "write_bytes",
            "write_text",
        }
    )


def test_standalone_cancellation_reconciliation_command_is_one_shot_and_confined() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_reconciliation_command"
    )
    rule = DependencyRule(
        source="standalone exact cancellation reconciliation command",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.paper_autopilot_control",
            "algotrader.execution.paper_cancellation_admission",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_exact_cancellation",
            "algotrader.execution.paper_mutation_oms",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    runner = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name
        == "run_exact_paper_cancellation_reconciliation_command"
    )
    leaf_call_names = [
        _call_name(node.func).rsplit(".", maxsplit=1)[-1]
        for node in ast.walk(runner)
        if isinstance(node, ast.Call)
    ]

    assert _dependency_violations(rule) == []
    assert leaf_call_names.count(
        "run_exact_paper_cancellation_reconciliation_operator"
    ) == 1
    assert leaf_call_names.count("from_env") == 1
    assert "build_paper_cancellation_observation_authorization" not in leaf_call_names
    assert set(leaf_call_names).isdisjoint(
        {
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "get_account",
            "get_order_by_id",
            "get_orders",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
        }
    )
    assert not any(
        isinstance(node, (ast.For, ast.While)) for node in ast.walk(runner)
    )


def test_cancellation_reconciliation_local_check_is_pure_and_shared() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_reconciliation_local"
    )
    rule = DependencyRule(
        source="pure exact cancellation local target check",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.config",
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_cancellation_reconciliation_operator",
            "algotrader.execution.paper_exact_cancellation",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = {
        _call_name(node.func).rsplit(".", maxsplit=1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert _dependency_violations(rule) == []
    assert calls.isdisjoint(
        {
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "connect",
            "get_account",
            "get_order_by_id",
            "get_orders",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
        }
    )


def test_cancellation_reconciliation_readiness_is_offline_exact_and_one_shot() -> None:
    path = _module_path(
        "algotrader.execution.paper_cancellation_reconciliation_readiness"
    )
    rule = DependencyRule(
        source="credential-free exact cancellation readiness receipt",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.config",
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.durable_cancel",
            "algotrader.execution.local_broker",
            "algotrader.execution.paper_autopilot_control",
            "algotrader.execution.paper_cancellation_admission",
            "algotrader.execution.paper_cancellation_invocation",
            "algotrader.execution.paper_cancellation_observation_sdk",
            "algotrader.execution.paper_cancellation_reconciliation_command",
            "algotrader.execution.paper_cancellation_reconciliation_operator",
            "algotrader.execution.paper_exact_cancellation",
            "algotrader.execution.paper_mutation_oms",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "os",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    runner = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name
        == "build_exact_paper_cancellation_reconciliation_readiness"
    )
    leaf_call_names = [
        _call_name(node.func).rsplit(".", maxsplit=1)[-1]
        for node in ast.walk(runner)
        if isinstance(node, ast.Call)
    ]

    assert _dependency_violations(rule) == []
    assert leaf_call_names.count(
        "load_paper_cancellation_observation_authorization"
    ) == 1
    assert leaf_call_names.count("paper_cancellation_authorization_blocker") == 1
    assert leaf_call_names.count("SqliteOrderJournal") == 1
    assert leaf_call_names.count("get") == 1
    assert leaf_call_names.count("get_cancel_intent") == 1
    assert leaf_call_names.count(
        "paper_cancellation_reconciliation_local_target_blocker"
    ) == 1
    assert "from_env" not in leaf_call_names
    assert "build_paper_cancellation_observation_authorization" not in leaf_call_names
    assert set(leaf_call_names).isdisjoint(
        {
            "acquire_runtime_lease",
            "cancel_order",
            "cancel_order_by_id",
            "close_all_positions",
            "close_position",
            "get_account",
            "get_order_by_id",
            "get_orders",
            "reconcile_unresolved_cancellation",
            "replace_order",
            "request_order_cancellation",
            "submit_order",
            "submit_order_request",
            "unresolved_cancel_intents",
        }
    )
    assert not any(
        isinstance(node, (ast.For, ast.While)) for node in ast.walk(runner)
    )


def test_general_cli_cannot_reach_cancellation_reconciliation_command() -> None:
    cli_path = _module_path("algotrader.cli")
    tree = ast.parse(
        cli_path.read_text(encoding="utf-8"),
        filename=str(cli_path),
    )
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert (
        "algotrader.execution.paper_cancellation_reconciliation_command"
        not in imported_modules
    )
    assert (
        "algotrader.execution.paper_cancellation_authorization_artifact"
        not in imported_modules
    )
    assert (
        "algotrader.execution.paper_cancellation_reconciliation_readiness"
        not in imported_modules
    )


def test_paper_cancellation_invocation_is_the_single_gated_bridge() -> None:
    path = _module_path("algotrader.execution.paper_cancellation_invocation")
    rule = DependencyRule(
        source="paper cancellation invocation",
        paths=(path,),
        forbidden_prefixes=(
            "algotrader.cli",
            "algotrader.execution.alpaca",
            "algotrader.execution.broker_base",
            "algotrader.execution.local_broker",
            "algotrader.execution.order_journal",
            "algotrader.execution.paper_autopilot_control",
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        ),
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    durable_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "algotrader.execution.durable_cancel"
        for alias in node.names
    }
    admission_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "algotrader.execution.paper_cancellation_admission"
        for alias in node.names
    }
    direct_callback_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"cancel", "observe"}
    ]
    coordinator_calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "coordinator"
    ]

    assert _dependency_violations(rule) == []
    assert durable_imports == {
        "DurableCancelCoordinator",
        "DurableCancelObservation",
    }
    assert admission_imports == {"PaperCancellationAdmissionResult"}
    assert direct_callback_calls == []
    assert coordinator_calls.count("reserve") == 1
    assert coordinator_calls.count("acquire_lease") == 1
    assert coordinator_calls.count("execute") == 1
    assert coordinator_calls.count("release_lease") == 1


def test_status_and_cli_cannot_reach_cancellation_invocation_bridge() -> None:
    for module_name in (
        "algotrader.cli",
        "algotrader.execution.paper_autopilot_control",
    ):
        path = _module_path(module_name)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        assert (
            "algotrader.execution.paper_cancellation_invocation"
            not in imported_modules
        )


def test_paper_cancellation_seed_is_submit_only_and_cli_independent() -> None:
    path = _module_path("algotrader.execution.paper_cancellation_seed")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]

    assert "algotrader.cli" not in imports
    assert "algotrader.execution.durable_cancel" not in imports
    assert "algotrader.execution.paper_cancellation_invocation" not in imports
    assert "algotrader.execution.paper_mutation_oms" not in imports
    assert calls.count("submit_order") == 1
    assert all(
        call not in {
            "cancel_order",
            "cancel_order_by_id",
            "replace_order",
            "close_position",
            "close_all_positions",
        }
        for call in calls
    )


def test_exact_paper_cancellation_is_the_narrow_broker_binding() -> None:
    path = _module_path("algotrader.execution.paper_exact_cancellation")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]

    assert "algotrader.cli" not in imports
    assert "algotrader.execution.paper_mutation_oms" not in imports
    assert "algotrader.execution.paper_cancellation_seed" not in imports
    assert {
        "algotrader.execution.paper_cancellation_admission",
        "algotrader.execution.paper_cancellation_handoff_preview",
        "algotrader.execution.paper_cancellation_invocation",
        "algotrader.execution.paper_cancellation_planning_adapter",
    }.issubset(imports)
    assert calls.count("cancel_order_by_id") == 1
    assert all(
        call not in {
            "submit_order",
            "submit_order_request",
            "replace_order",
            "close_position",
            "close_all_positions",
            "liquidate",
        }
        for call in calls
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
    parts = list(relative_path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


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


def _package_files(package_name: str) -> tuple[Path, ...]:
    pkg_dir = Path("src").joinpath(*package_name.split("."))
    return tuple(sorted(pkg_dir.glob("*.py")))


CRYPTO_READINESS_REPLAY_MODULE_PATHS = (
    _module_path("algotrader.execution.crypto_readiness_replay"),
    _module_path("algotrader.execution.crypto_supervised_readiness_trial_core"),
    _module_path("algotrader.execution.tomorrow_crypto_trader_demo"),
    _module_path("algotrader.execution.crypto_market_data_symbol_normalization"),
    _module_path("algotrader.execution.simulator"),
    _module_path("algotrader.orchestration.execution_planning_flow"),
    _module_path("algotrader.orchestration.execution_planning_policy"),
    _module_path("algotrader.orchestration.risk_execution_flow"),
    _module_path("algotrader.orchestration.screener_signal_flow"),
    _module_path("algotrader.orchestration.signal_risk_flow"),
    _module_path("algotrader.portfolio.state"),
    _module_path("algotrader.risk.config"),
    _module_path("algotrader.risk.context"),
    _module_path("algotrader.risk.engine"),
    _module_path("algotrader.risk.state"),
    _module_path("algotrader.signals.crypto_trend"),
    _module_path("algotrader.signals.simple_rule"),
    _module_path("algotrader.core.types"),
    _module_path("algotrader.core.validation"),
    _module_path("algotrader.core.time"),
    _module_path("algotrader.errors"),
    *_package_files("algotrader.screener"),
)

CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS = (
    "algotrader.config",
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_mapper",
    "algotrader.execution.alpaca_translator",
    "algotrader.execution.live_capital_interlock",
    "algotrader.execution.crypto_read_only_paper_observation_adapter",
    "algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter",
    "algotrader.execution.tomorrow_crypto_trader_demo_cli",
    "alpaca",
    "alpaca_trade_api",
    "requests",
    "httpx",
    "socket",
    "urllib",
    "importlib",
    "runpy",
    "pkgutil",
)


def test_crypto_readiness_replay_import_closure_is_broker_credential_and_profile_free() -> None:
    rule = DependencyRule(
        source="crypto readiness replay import closure",
        paths=CRYPTO_READINESS_REPLAY_MODULE_PATHS,
        forbidden_prefixes=CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS,
    )
    assert _dependency_violations(rule) == []


def _ast_docstring_constant_nodes(tree: ast.AST) -> set[int]:
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring_nodes.add(id(node.body[0].value))
    return docstring_nodes


def _fold_static_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _fold_static_string(node.left)
        right = _fold_static_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for val in node.values:
            folded = _fold_static_string(val)
            if folded is None:
                return None
            parts.append(folded)
        return "".join(parts)
    if isinstance(node, ast.FormattedValue):
        return _fold_static_string(node.value)
    return None


def _import_aliases_for_module(tree: ast.AST, target_module: str) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == target_module:
                    aliases.add(alias.asname or alias.name)
    return aliases


def _check_tree_bans(tree: ast.AST, filename: str) -> list[str]:
    violations: list[str] = []
    banned_call_names = {"import_module", "__import__"}
    forbidden_literal_roots = tuple(
        item.lower()
        for item in CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS
    )
    docstring_nodes = _ast_docstring_constant_nodes(tree)
    os_aliases = _import_aliases_for_module(tree, "os")

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            names_set = {alias.name for alias in node.names}
            if names_set.intersection({"environ", "getenv"}):
                violations.append(f"{filename}:{node.lineno}: ambient environment access is banned")
        if isinstance(node, ast.Name):
            if node.id in {"importlib", "runpy", "pkgutil", "__import__"}:
                violations.append(f"{filename}:{node.lineno}: dynamic import machinery is banned")
        if isinstance(node, ast.Call):
            func = node.func
            called_name = (
                func.attr if isinstance(func, ast.Attribute)
                else func.id if isinstance(func, ast.Name)
                else None
            )
            if called_name in banned_call_names:
                violations.append(f"{filename}:{node.lineno}: dynamic module loading via {called_name!r} is banned")
            if called_name == "getattr" and len(node.args) >= 2:
                attribute_name = _fold_static_string(node.args[1])
                if attribute_name in banned_call_names:
                    violations.append(f"{filename}:{node.lineno}: constructed lookup of {attribute_name!r} is banned")
                if (
                    isinstance(node.args[0], ast.Name)
                    and node.args[0].id in os_aliases
                ):
                    if attribute_name in {"environ", "getenv"}:
                        violations.append(f"{filename}:{node.lineno}: constructed ambient environment access is banned")
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in os_aliases
        ):
            if node.attr in {"environ", "getenv"}:
                violations.append(f"{filename}:{node.lineno}: ambient environment access is banned")
        folded = _fold_static_string(node)
        if folded is not None and id(node) not in docstring_nodes:
            normalized = folded.strip().lower()
            if any(
                normalized == root or normalized.startswith(root + ".")
                for root in forbidden_literal_roots
            ):
                violations.append(f"{filename}:{node.lineno}: forbidden module literal {folded!r}")
    return violations


def test_crypto_readiness_replay_import_closure_bans_dynamic_loading_and_forbidden_literals() -> None:
    for path in CRYPTO_READINESS_REPLAY_MODULE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations = _check_tree_bans(tree, str(path))
        assert not violations, "\n".join(violations)

    # Negative test cases proving detection works on evasions
    negative_cases = [
        "import importlib; importlib.import_module('algotrader.config')",
        "__import__('algotrader.config')",
        "getattr(importlib, 'im' + 'port_module')('alpaca.data.historical')",
        "x = 'socket.socket'",
        "import os; env = os.environ",
        "import os; val = os.getenv('APP_PROFILE')",
        "from os import environ",
        "import os; val = getattr(os, 'en' + 'viron')",
    ]
    for case in negative_cases:
        tree = ast.parse(case, filename="<synthetic>")
        violations = _check_tree_bans(tree, "<synthetic>")
        assert len(violations) > 0, f"Expected violations for negative synthetic case: {case!r}"

    # Positive test cases proving valid non-evasion passes
    positive_cases = [
        "'''Docs referencing importlib and os.environ are allowed.'''\nx = 'allow_alpaca_paper_read'",
    ]
    for case in positive_cases:
        tree = ast.parse(case, filename="<synthetic>")
        violations = _check_tree_bans(tree, "<synthetic>")
        assert violations == [], f"Unexpected violations for positive synthetic case: {violations}"


def test_crypto_readiness_replay_import_closure_has_no_untracked_first_party_imports() -> None:
    tracked_paths = set(CRYPTO_READINESS_REPLAY_MODULE_PATHS)
    tracked_modules = {_module_name(path) for path in tracked_paths}
    discovered_modules: set[str] = set(tracked_modules)
    frontier = list(tracked_paths)
    while frontier:
        path = frontier.pop()
        for import_reference in _import_references(path):
            module = import_reference.module
            if not module.startswith("algotrader.") or module in discovered_modules:
                continue
            discovered_modules.add(module)
            candidate_module_path = _module_path(module)
            candidate_package_dir = Path("src").joinpath(*module.split("."))
            if candidate_module_path.is_file():
                frontier.append(candidate_module_path)
            elif candidate_package_dir.is_dir():
                frontier.extend(_package_files(module))
            else:
                raise AssertionError(
                    f"import reference {module!r} (from {path}:"
                    f"{import_reference.line}) resolves to neither a "
                    "module file nor a package directory."
                )
    assert discovered_modules == tracked_modules, (
        "crypto_readiness_replay's real import closure has grown beyond "
        "CRYPTO_READINESS_REPLAY_MODULE_PATHS; add the new module(s) and "
        "re-verify them before allowlisting."
    )


def test_crypto_readiness_replay_fresh_process_sys_modules_smoke() -> None:
    import subprocess
    import sys
    code = (
        "import sys; sys.path.insert(0, 'src'); "
        "import algotrader.execution.crypto_readiness_replay; "
        "forbidden = {'algotrader.execution.alpaca_sdk_client', "
        "'algotrader.execution.alpaca_client', 'algotrader.config', "
        "'algotrader.execution.live_capital_interlock', "
        "'algotrader.execution.crypto_read_only_paper_observation_adapter', "
        "'algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter', "
        "'algotrader.execution.tomorrow_crypto_trader_demo_cli'}; "
        "loaded = set(sys.modules.keys()).intersection(forbidden); "
        "assert not loaded, f'Forbidden modules loaded: {loaded}'"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, f"Fresh process sys.modules smoke test failed: {result.stderr}"


def test_crypto_readiness_replay_raising_protected_environment(tmp_path: Path) -> None:
    import json
    import os
    from algotrader.execution.crypto_readiness_replay import run_crypto_readiness_replay
    from algotrader.execution.crypto_supervised_readiness_trial_core import (
        _json_safe,
    )

    protected_keys = {
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    }

    class RaisingEnvMap(dict):
        def __getitem__(self, key: object) -> str:
            if str(key) in protected_keys:
                raise RuntimeError(f"Protected environment key accessed: {key}")
            return super().__getitem__(key)

        def get(self, key: object, default: object = None) -> object:
            if str(key) in protected_keys:
                raise RuntimeError(f"Protected environment key accessed: {key}")
            return super().get(key, default)

        def __contains__(self, key: object) -> bool:
            if str(key) in protected_keys:
                raise RuntimeError(f"Protected environment key accessed: {key}")
            return super().__contains__(key)

        def __iter__(self):
            for key in super().__iter__():
                decoded = (
                    key.decode(errors="replace")
                    if isinstance(key, bytes)
                    else str(key)
                )
                if decoded in protected_keys:
                    raise RuntimeError(
                        f"Protected environment key iterated: {decoded}"
                    )
                yield key

    original_env = os.environ._data
    try:
        os.environ._data = RaisingEnvMap(original_env)
        output_root = tmp_path / "replay_output"
        packet = run_crypto_readiness_replay(
            output_root=output_root,
            cycle_count=8,
            write_artifacts=True,
        )
        assert packet["trial_classification"] == "accepted"
        assert packet["safety"]["app_profile_paper"] is False
        assert packet["safety"]["app_profile_live"] is False
        assert packet["safety"]["credentials_present"] is False
        assert packet["safety"]["network_used"] is False
        assert packet["safety"]["broker_read_occurred"] is False
        assert packet["safety"]["credentials_present"] is False
        rendered = json.dumps(_json_safe(packet), sort_keys=True)
        assert '"trial_classification": "accepted"' in rendered
    finally:
        os.environ._data = original_env


# --------------------------------------------------------------------------- #
# V5.48: exact central CLI launcher eager/path-specific purity proof.
# --------------------------------------------------------------------------- #
CENTRAL_REPLAY_LAUNCHER_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "httpx",
    "langchain",
    "langgraph",
    "openai",
    "requests",
    "socket",
    "urllib",
    "algotrader.config",
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.execution.alpaca_mapper",
    "algotrader.execution.alpaca_translator",
    "algotrader.execution.crypto_read_only_paper_observation_adapter",
    "algotrader.execution.live_capital_interlock",
    "algotrader.execution.read_only_paper_broker_snapshot_operator_review",
    "algotrader.execution.read_only_paper_broker_snapshot_reconciliation",
    "algotrader.execution.secure_credential_provider",
    "algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter",
    "algotrader.execution.tomorrow_crypto_trader_demo_cli",
    "algotrader.execution.v536_credential_provisioning",
    "algotrader.orchestration.etf_sma_paper_broker_preview",
)

_CENTRAL_REPLAY_MUTATION_CALLS = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "create_order",
    "liquidate",
    "replace_order",
    "submit_order",
    "submit_order_request",
}


def _top_level_import_references(path: Path) -> tuple[ImportReference, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[ImportReference] = []
    for node in tree.body:
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


def _first_party_module_path(module: str) -> Path | None:
    module_path = _module_path(module)
    if module_path.is_file():
        return module_path
    package_init = Path("src").joinpath(*module.split("."), "__init__.py")
    if package_init.is_file():
        return package_init
    return None


def _implicit_package_initializers(module: str) -> tuple[Path, ...]:
    parts = module.split(".")
    initializers: list[Path] = []
    for index in range(1, len(parts)):
        init_path = Path("src").joinpath(*parts[:index], "__init__.py")
        if init_path.is_file():
            initializers.append(init_path)
    return tuple(initializers)


def _central_replay_eager_closure() -> tuple[Path, ...]:
    seeds = {
        Path("src/algotrader/__init__.py"),
        Path("src/algotrader/execution/__init__.py"),
        _module_path("algotrader.cli"),
    }
    discovered = set(seeds)
    frontier = list(seeds)
    while frontier:
        path = frontier.pop()
        for reference in _top_level_import_references(path):
            if not reference.module.startswith("algotrader"):
                continue
            candidates = list(_implicit_package_initializers(reference.module))
            module_path = _first_party_module_path(reference.module)
            if module_path is not None:
                candidates.append(module_path)
            for candidate in candidates:
                if candidate not in discovered:
                    discovered.add(candidate)
                    frontier.append(candidate)
    return tuple(sorted(discovered))


def _top_level_executed_nodes(tree: ast.Module) -> tuple[ast.AST, ...]:
    resolved: list[ast.AST] = []

    def _visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return
        if isinstance(node, ast.ClassDef):
            for decorator in node.decorator_list:
                resolved.extend(ast.walk(decorator))
            return
        resolved.append(node)
        for child in ast.iter_child_nodes(node):
            _visit(child)

    for statement in tree.body:
        _visit(statement)
    return tuple(resolved)


def _launcher_scanner_violations(
    tree: ast.Module,
    filename: str,
    *,
    imports: tuple[ImportReference, ...] = (),
    mutation_scope: tuple[ast.AST, ...] | None = None,
) -> list[str]:
    violations = _check_tree_bans(tree, filename)
    for reference in imports:
        if _matches_forbidden_prefix(
            reference.module,
            CENTRAL_REPLAY_LAUNCHER_FORBIDDEN_IMPORT_PREFIXES,
        ):
            violations.append(
                f"{reference.path}:{reference.line}: forbidden launcher import "
                f"{reference.module}"
            )
    nodes = tuple(ast.walk(tree)) if mutation_scope is None else mutation_scope
    for node in nodes:
        if isinstance(node, ast.Call):
            called = _call_name(node.func)
            if called.rsplit(".", maxsplit=1)[-1] in _CENTRAL_REPLAY_MUTATION_CALLS:
                violations.append(
                    f"{filename}:{node.lineno}: mutation call {called} is banned"
                )
    return violations


def test_central_replay_launcher_static_eager_closure_is_pure() -> None:
    cli_path = _module_path("algotrader.cli")
    cli_imports = _top_level_import_references(cli_path)
    assert {reference.module for reference in cli_imports} == {
        "__future__",
        "argparse",
        "collections.abc",
        "decimal",
        "json",
        "pathlib",
        "sys",
        "types",
        "algotrader.execution.paper_order_policy",
    }

    policy_path = _module_path("algotrader.execution.paper_order_policy")
    assert {
        reference.module
        for reference in _top_level_import_references(policy_path)
    } == {"__future__", "dataclasses", "decimal"}

    closure = _central_replay_eager_closure()
    assert Path("src/algotrader/__init__.py") in closure
    assert Path("src/algotrader/execution/__init__.py") in closure
    assert policy_path in closure

    violations: list[str] = []
    for path in closure:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = _top_level_import_references(path)
        scanned_tree = tree
        if path == cli_path:
            scanned_tree = ast.Module(
                body=[
                    node
                    for node in tree.body
                    if not isinstance(
                        node,
                        (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
                    )
                ],
                type_ignores=[],
            )
        violations.extend(
            _launcher_scanner_violations(
                scanned_tree,
                str(path),
                imports=imports,
                mutation_scope=_top_level_executed_nodes(scanned_tree),
            )
        )
    assert violations == []


def test_central_replay_cli_selected_path_imports_are_exact() -> None:
    cli_path = _module_path("algotrader.cli")
    tree = ast.parse(cli_path.read_text(encoding="utf-8"), filename=str(cli_path))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    handler = functions["_run_crypto_readiness_replay"]
    handler_imports: list[str] = []
    for node in ast.walk(handler):
        if isinstance(node, ast.Import):
            handler_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            handler_imports.extend(_import_from_modules(cli_path, node))
    assert set(handler_imports) == {
        "json",
        "algotrader.execution.crypto_readiness_replay",
        "algotrader.execution.crypto_supervised_readiness_trial_core",
    }

    main = functions["main"]
    replay_branch = next(
        node
        for node in ast.walk(main)
        if isinstance(node, ast.If)
        and any(
            isinstance(value, ast.Constant)
            and value.value == "crypto-readiness-replay"
            for value in ast.walk(node.test)
        )
    )
    replay_return = next(
        node for node in replay_branch.body if isinstance(node, ast.Return)
    )
    assert _call_name(replay_return.value.func) == "_run_crypto_readiness_replay"
    imports_before_dispatch = [
        node
        for node in ast.walk(main)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and node.lineno <= replay_branch.lineno
    ]
    assert imports_before_dispatch == []

    parser_function = functions["build_parser"]
    replay_literals = {
        node.value
        for node in ast.walk(parser_function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert {
        "crypto-readiness-replay",
        "--output-root",
        "--decision-start",
        "--cycle-count",
        "--format",
    } <= replay_literals


def test_central_replay_launcher_scanner_detects_synthetic_evasions() -> None:
    cases = (
        "import alpaca",
        "import openai",
        "import importlib; importlib.import_module('algotrader.config')",
        "import os; value = os.environ.get('APP_PROFILE')",
        "submit_order()",
        "client.cancel_order('id')",
    )
    for source in cases:
        tree = ast.parse(source, filename="<synthetic-launcher>")
        imports: list[ImportReference] = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(
                    ImportReference(
                        path=Path("<synthetic-launcher>"),
                        line=node.lineno,
                        module=alias.name,
                    )
                    for alias in node.names
                )
        assert _launcher_scanner_violations(
            tree,
            "<synthetic-launcher>",
            imports=tuple(imports),
        ), source


def test_v551_read_only_network_executor_seven_file_closure_import_purity() -> None:
    closure_paths = (
        Path("src/algotrader/execution/autonomy_read_only_network_executor.py"),
        Path("src/algotrader/execution/etf_sma_adjusted_spy_data_refresh.py"),
        Path("src/algotrader/execution/etf_sma_market_data_soak.py"),
        Path("src/algotrader/execution/exchange_session.py"),
        Path("src/algotrader/errors.py"),
        Path("src/algotrader/execution/live_capital_interlock.py"),
        Path("src/algotrader/config.py"),
    )
    for p in closure_paths:
        assert p.exists(), f"Closure file missing: {p}"

    seam_file = closure_paths[0]
    seam_tree = ast.parse(seam_file.read_text(encoding="utf-8"), filename=str(seam_file))

    # Assertion 1: Direct-import scope of seam file.
    #
    # This set MIRRORS the V5.51 contract, "Direct-import scope" (round-6
    # amendment). It may not be widened to match an implementation. Widening it
    # is exactly what produced independent-review finding F1: the seam imported
    # a third module, the allowlist was extended to admit it, and a contract
    # violation became a passing suite. If the seam needs a further import,
    # amend the contract first -- under independent review -- and mirror the
    # amendment here. Never the reverse.
    contract_allowed_execution_imports = frozenset(
        {
            "algotrader.execution.etf_sma_adjusted_spy_data_refresh",
            "algotrader.execution.live_capital_interlock",
            "algotrader.execution.exchange_session",
        }
    )
    assert len(contract_allowed_execution_imports) == 3, (
        "the contract names exactly three permitted internal execution imports; "
        "a change here must correspond to a reviewed contract amendment"
    )
    # algotrader.errors falls outside the rule's scope (it is not an
    # algotrader.execution/algotrader.config/broker-prefixed module), so it is
    # permitted without being contract-named.
    allowed_internal_modules = contract_allowed_execution_imports | {"algotrader.errors"}
    for node in ast.walk(seam_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("algotrader") or alias.name.startswith("alpaca"):
                    assert alias.name in allowed_internal_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("algotrader") or mod.startswith("alpaca"):
                assert mod in allowed_internal_modules, f"Forbidden import from: {mod}"

    # Assertion 2: No direct config or secret identifiers in seam file AST
    forbidden_seam_names = {"AlpacaPaperConfig", "require_paper_profile", "alpaca_api_key", "alpaca_secret_key"}
    for node in ast.walk(seam_tree):
        if isinstance(node, ast.Name):
            assert node.id not in forbidden_seam_names, f"Forbidden name in seam: {node.id}"
        elif isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_seam_names, f"Forbidden attribute in seam: {node.attr}"

    # Assertion 3: Adapter & soak report have no config or broker import
    adapter_paths = (closure_paths[1], closure_paths[2])
    forbidden_adapter_prefixes = ("algotrader.config", "alpaca", "alpaca_trade_api", "algotrader.execution.broker_base")
    for p in adapter_paths:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_adapter_prefixes), f"Forbidden adapter import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith(forbidden_adapter_prefixes), f"Forbidden adapter import: {mod}"

    # Assertion 4: live_capital_interlock.py is sole importer of AlpacaPaperConfig/require_paper_profile from algotrader.config
    interlock_file = closure_paths[5]
    for p in closure_paths:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        imports_found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "algotrader.config":
                for alias in node.names:
                    if alias.name in {"AlpacaPaperConfig", "require_paper_profile"}:
                        imports_found.add(alias.name)
        if p == interlock_file:
            assert imports_found == {"AlpacaPaperConfig", "require_paper_profile"}
        else:
            assert not imports_found, f"Found config imports in non-interlock file {p}: {imports_found}"

    # Assertion 5: SDK client/order/mutation exclusion across all seven files
    forbidden_sdk_prefixes = ("alpaca", "alpaca_trade_api", "require_live_capital_interlock")
    forbidden_callables = {"submit_order", "cancel_order", "replace_order", "close_position", "liquidate_position"}
    for p in closure_paths:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_sdk_prefixes), f"Forbidden SDK import in {p}: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith(forbidden_sdk_prefixes), f"Forbidden SDK import in {p}: {mod}"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in forbidden_callables, f"Forbidden call in {p}: {node.func.id}"
                elif isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in forbidden_callables, f"Forbidden call in {p}: {node.func.attr}"
