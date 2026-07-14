import ast
import importlib
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


CHECKED_SOURCE_FILES = (
    Path("src/algotrader/execution/alpaca_sdk_client.py"),
    Path("src/algotrader/execution/alpaca_adapter.py"),
    Path("src/algotrader/execution/alpaca_broker.py"),
    Path("src/algotrader/execution/alpaca_client.py"),
    Path("src/algotrader/execution/broker_base.py"),
)

CHECKED_RUNTIME_MODULES = (
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.broker_base",
)

CHECKED_RUNTIME_OBJECTS = (
    "algotrader.execution.alpaca_sdk_client:AlpacaSdkClient",
    "algotrader.execution.alpaca_adapter:AlpacaClientAdapter",
    "algotrader.execution.alpaca_broker:AlpacaPaperBroker",
    "algotrader.execution.alpaca_client:AlpacaClient",
    "algotrader.execution.broker_base:Broker",
)

FORBIDDEN_MUTATION_TERMS = (
    "cancel_order",
    "replace_order",
    "close_all_positions",
    "close_position",
    "liquidation",
    "liquidate",
    "cancel",
    "replace",
    "delete",
)

MUTATION_CALL_NAMES = frozenset(
    {
        "submit_order",
        "submit_order_request",
        "cancel_order",
        "cancel_order_by_id",
        "replace_order",
        "close_position",
        "close_all_positions",
        "liquidate",
    }
)

EXPECTED_DIRECT_MUTATION_CALLS = frozenset(
    {
        ("src/algotrader/cli.py", "_submit_paper_lab_spy_close_submit", "submit_order_request"),
        ("src/algotrader/cli.py", "_submit_paper_close_probe", "submit_order_request"),
        ("src/algotrader/cli.py", "_submit_paper_order_probe", "submit_order_request"),
        ("src/algotrader/execution/alpaca_adapter.py", "submit_order", "submit_order_request"),
        ("src/algotrader/execution/alpaca_broker.py", "submit_order", "submit_order"),
        ("src/algotrader/execution/alpaca_broker.py", "submit_order_request", "submit_order_request"),
        ("src/algotrader/execution/alpaca_sdk_client.py", "submit_order", "submit_order"),
        ("src/algotrader/execution/crypto_paper_fill_exit_certification.py", "_submit_and_reconcile_once", "submit_order"),
        ("src/algotrader/execution/crypto_paper_mutation_drill.py", "_submit_cancel_reconcile", "submit_order"),
        ("src/algotrader/execution/crypto_paper_submit_cancel_certification.py", "_submit_cancel_reconcile", "submit_order"),
        ("src/algotrader/execution/etf_sma_daily_oms_rehearsal.py", "submit_order", "submit_order"),
        ("src/algotrader/execution/etf_sma_m370_paper_submit.py", "_submit_once", "submit_order_request"),
        ("src/algotrader/execution/etf_sma_m435_paper_buy_submit.py", "_submit_once", "submit_order_request"),
        ("src/algotrader/execution/etf_sma_v199_authorized_bounded_spy_paper_drill.py", "_submit_cancel_reconcile", "submit_order"),
        ("src/algotrader/execution/paper_cancellation_seed.py", "send", "submit_order"),
        (
            "src/algotrader/execution/paper_exact_cancellation.py",
            "execute_exact",
            "cancel_order_by_id",
        ),
        ("src/algotrader/execution/paper_autopilot_loop.py", "_execute_plan", "submit_order"),
        ("src/algotrader/execution/paper_mutation_oms.py", "submit_order", "submit_order"),
        ("src/algotrader/execution/paper_mutation_oms.py", "run_paper_certification_drill", "submit_order"),
        ("src/algotrader/orchestration/scenarios.py", "_run_broker_flow", "submit_order"),
    }
)

AUTONOMOUS_MUTATION_CALLS = frozenset(
    {
        ("src/algotrader/execution/paper_autopilot_loop.py", "_execute_plan", "submit_order"),
    }
)

SHARED_CLAIM_OPERATOR_MUTATION_CALLS = frozenset(
    {
        (
            "src/algotrader/cli.py",
            "_submit_paper_lab_spy_close_submit",
            "submit_order_request",
        ),
        (
            "src/algotrader/execution/etf_sma_m370_paper_submit.py",
            "_submit_once",
            "submit_order_request",
        ),
        (
            "src/algotrader/execution/etf_sma_m435_paper_buy_submit.py",
            "_submit_once",
            "submit_order_request",
        ),
    }
)

BROKER_BOUNDARY_MUTATION_CALLS = frozenset(
    {
        ("src/algotrader/execution/alpaca_adapter.py", "submit_order", "submit_order_request"),
        ("src/algotrader/execution/alpaca_broker.py", "submit_order", "submit_order"),
        ("src/algotrader/execution/alpaca_broker.py", "submit_order_request", "submit_order_request"),
        ("src/algotrader/execution/alpaca_sdk_client.py", "submit_order", "submit_order"),
        ("src/algotrader/execution/paper_mutation_oms.py", "submit_order", "submit_order"),
    }
)

OFFLINE_SIMULATION_MUTATION_CALLS = frozenset(
    {
        ("src/algotrader/execution/etf_sma_daily_oms_rehearsal.py", "submit_order", "submit_order"),
        ("src/algotrader/orchestration/scenarios.py", "_run_broker_flow", "submit_order"),
    }
)

OPERATOR_GATED_MUTATION_CALLS = EXPECTED_DIRECT_MUTATION_CALLS - (
    AUTONOMOUS_MUTATION_CALLS
    | SHARED_CLAIM_OPERATOR_MUTATION_CALLS
    | BROKER_BOUNDARY_MUTATION_CALLS
    | OFFLINE_SIMULATION_MUTATION_CALLS
)

EXPECTED_DYNAMIC_CANCEL_DISPATCHERS = frozenset(
    {
        ("src/algotrader/execution/crypto_paper_mutation_drill.py", "_request_order_cancellation"),
        ("src/algotrader/execution/crypto_paper_submit_cancel_certification.py", "_request_order_cancellation"),
        ("src/algotrader/execution/etf_sma_v199_authorized_bounded_spy_paper_drill.py", "_request_order_cancellation"),
        ("src/algotrader/execution/paper_mutation_oms.py", "request_order_cancellation"),
    }
)


@dataclass(frozen=True)
class NameObservation:
    source: str
    line: int | None
    kind: str
    name: str

    def violation(self, term: str) -> str:
        line = "" if self.line is None else f":{self.line}"
        return (
            f"{self.source}{line}: {self.kind} {self.name!r} contains "
            f"forbidden broker mutation term {term!r}"
        )


def test_checked_source_files_define_no_forbidden_mutation_names() -> None:
    violations: list[str] = []

    for path in CHECKED_SOURCE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for observation in _ast_name_observations(path, tree):
            if term := _forbidden_mutation_term(observation.name):
                violations.append(observation.violation(term))

    assert violations == []


def test_runtime_public_broker_surface_exposes_no_forbidden_mutation_names() -> None:
    violations: list[str] = []

    for module_name in CHECKED_RUNTIME_MODULES:
        module = importlib.import_module(module_name)
        for observation in _public_runtime_observations(module_name, module):
            if term := _forbidden_mutation_term(observation.name):
                violations.append(observation.violation(term))

    for object_path in CHECKED_RUNTIME_OBJECTS:
        obj = _load_runtime_object(object_path)
        for observation in _public_runtime_observations(object_path, obj):
            if term := _forbidden_mutation_term(observation.name):
                violations.append(observation.violation(term))

    assert violations == []


def test_alpaca_paper_broker_mutation_surface_is_submit_only() -> None:
    from algotrader.execution.alpaca_broker import AlpacaPaperBroker

    public_callable_names = {
        name
        for name, value in vars(AlpacaPaperBroker).items()
        if _is_public(name) and callable(value)
    }

    assert "submit_order" in public_callable_names
    assert all(
        _forbidden_mutation_term(name) == "" for name in public_callable_names
    )


def test_every_production_mutation_call_is_explicitly_classified() -> None:
    observed = [
        call
        for path in sorted(Path("src/algotrader").rglob("*.py"))
        for call in _direct_mutation_calls(path)
    ]
    classified = (
        AUTONOMOUS_MUTATION_CALLS
        | SHARED_CLAIM_OPERATOR_MUTATION_CALLS
        | BROKER_BOUNDARY_MUTATION_CALLS
        | OFFLINE_SIMULATION_MUTATION_CALLS
        | OPERATOR_GATED_MUTATION_CALLS
    )

    assert frozenset(observed) == EXPECTED_DIRECT_MUTATION_CALLS
    assert len(observed) == len(EXPECTED_DIRECT_MUTATION_CALLS)
    assert classified == EXPECTED_DIRECT_MUTATION_CALLS
    assert AUTONOMOUS_MUTATION_CALLS == {
        ("src/algotrader/execution/paper_autopilot_loop.py", "_execute_plan", "submit_order")
    }


def test_dynamic_cancel_dispatchers_remain_operator_gated_and_allowlisted() -> None:
    observed = frozenset(
        dispatcher
        for path in sorted(Path("src/algotrader").rglob("*.py"))
        for dispatcher in _dynamic_cancel_dispatchers(path)
    )

    assert observed == EXPECTED_DYNAMIC_CANCEL_DISPATCHERS


def test_cancellation_reconciliation_exposes_no_broker_action_surface() -> None:
    path = Path("src/algotrader/execution/cancellation_reconciliation.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    attribute_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert all(
        not module.startswith(("alpaca", "requests", "httpx", "urllib"))
        for module in imported_modules
    )
    assert attribute_calls.isdisjoint(
        MUTATION_CALL_NAMES
        | {
            "get_account",
            "get_order_by_id",
            "get_recent_orders",
            "request_order_cancellation",
        }
    )


def test_paper_cancellation_observation_exposes_no_broker_mutation_surface() -> None:
    path = Path("src/algotrader/execution/paper_cancellation_observation.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    calls = {
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }

    assert all(
        not module.startswith(("alpaca", "requests", "httpx", "urllib"))
        for module in imported_modules
    )
    assert calls.isdisjoint(
        MUTATION_CALL_NAMES
        | {
            "get_account",
            "get_order_by_id",
            "get_recent_orders",
            "request_order_cancellation",
        }
    )


def test_paper_cancellation_sdk_binding_exposes_only_exact_reads() -> None:
    from algotrader.execution.paper_cancellation_observation_sdk import (
        PaperCancellationSdkExactOrderReader,
    )

    path = Path(
        "src/algotrader/execution/paper_cancellation_observation_sdk.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    calls = [
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    ]
    public_callable_names = {
        name
        for name, value in vars(PaperCancellationSdkExactOrderReader).items()
        if _is_public(name) and callable(value)
    }

    assert calls.count("get_account") == 1
    assert calls.count("get_order_by_id") == 1
    assert set(calls).isdisjoint(MUTATION_CALL_NAMES | {"get_orders"})
    assert public_callable_names == set()
    assert "raw_trading_client" not in source


def test_paper_cancellation_reconciliation_workflow_has_no_broker_action() -> None:
    path = Path(
        "src/algotrader/execution/"
        "paper_cancellation_reconciliation_workflow.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    calls = [
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    ]
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert calls.count("observe_exact_paper_cancellation") == 1
    assert calls.count("reconcile_unresolved_cancellation") == 1
    assert set(calls).isdisjoint(
        MUTATION_CALL_NAMES
        | {
            "get_account",
            "get_order_by_id",
            "get_orders",
            "request_order_cancellation",
            "unresolved_cancel_intents",
        }
    )
    assert all(
        not module.startswith(("alpaca", "requests", "httpx", "urllib"))
        for module in imported_modules
    )
    assert "raw_trading_client" not in source


def test_paper_cancellation_reconciliation_operator_cannot_mint_or_mutate() -> None:
    path = Path(
        "src/algotrader/execution/"
        "paper_cancellation_reconciliation_operator.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    calls = [
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    ]
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert calls.count("paper_cancellation_observation_blocker") == 1
    assert calls.count("build_paper_cancellation_sdk_reader") == 1
    assert calls.count("reconcile_exact_paper_cancellation") == 1
    assert "build_paper_cancellation_observation_authorization" not in calls
    assert set(calls).isdisjoint(
        MUTATION_CALL_NAMES
        | {
            "get_account",
            "get_order_by_id",
            "get_orders",
            "request_order_cancellation",
            "unresolved_cancel_intents",
        }
    )
    assert all(
        not module.startswith(("alpaca", "requests", "httpx", "urllib"))
        for module in imported_modules
    )
    assert "raw_trading_client" not in source


def test_cancellation_reconciliation_loader_command_and_script_are_read_only() -> None:
    paths = (
        Path(
            "src/algotrader/execution/"
            "paper_cancellation_authorization_artifact.py"
        ),
        Path(
            "src/algotrader/execution/"
            "paper_cancellation_reconciliation_command.py"
        ),
        Path("scripts/run_exact_paper_cancellation_reconciliation.py"),
    )
    calls: list[str] = []
    imported_modules: set[str] = set()
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        calls.extend(
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Attribute, ast.Name))
        )
        imported_modules.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )

    assert calls.count(
        "run_exact_paper_cancellation_reconciliation_operator"
    ) == 1
    assert "build_paper_cancellation_observation_authorization" not in calls
    assert set(calls).isdisjoint(
        MUTATION_CALL_NAMES
        | {
            "get_account",
            "get_order_by_id",
            "get_orders",
            "request_order_cancellation",
            "unresolved_cancel_intents",
        }
    )
    assert all(
        not module.startswith(("alpaca", "requests", "httpx", "urllib"))
        for module in imported_modules
    )


def test_shared_coordinator_owns_atomic_claim_before_submit_callback() -> None:
    path = Path("src/algotrader/execution/durable_submit.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    execute = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    claim_lines = [
        node.lineno
        for node in ast.walk(execute)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "claim_pre_mutation_submit"
    ]
    submit_callback_lines = [
        node.lineno
        for node in ast.walk(execute)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "submit"
    ]

    assert len(claim_lines) == 1
    assert len(submit_callback_lines) == 1
    assert claim_lines[0] < submit_callback_lines[0]


def test_durable_cancel_owns_atomic_claim_before_cancel_callback() -> None:
    path = Path("src/algotrader/execution/durable_cancel.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    execute = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    claim_lines = [
        node.lineno
        for node in ast.walk(execute)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "claim_pre_mutation_cancel"
    ]
    cancel_callback_lines = [
        node.lineno
        for node in ast.walk(execute)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "cancel"
    ]

    assert len(claim_lines) == 1
    assert len(cancel_callback_lines) == 1
    assert claim_lines[0] < cancel_callback_lines[0]


def test_durable_cancel_consumers_are_an_exact_operator_gated_allowlist() -> None:
    consumers: set[str] = set()
    for path in Path("src/algotrader").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, ast.ImportFrom)
            and node.module == "algotrader.execution.durable_cancel"
            for node in ast.walk(tree)
        ):
            consumers.add(path.as_posix())

    certification_path = (
        "src/algotrader/execution/crypto_paper_submit_cancel_certification.py"
    )
    crypto_drill_path = (
        "src/algotrader/execution/crypto_paper_mutation_drill.py"
    )
    oms_path = "src/algotrader/execution/paper_mutation_oms.py"
    invocation_path = (
        "src/algotrader/execution/paper_cancellation_invocation.py"
    )
    exact_binding_path = (
        "src/algotrader/execution/paper_exact_cancellation.py"
    )
    v199_path = (
        "src/algotrader/execution/"
        "etf_sma_v199_authorized_bounded_spy_paper_drill.py"
    )
    assert consumers == {
        certification_path,
        crypto_drill_path,
        exact_binding_path,
        invocation_path,
        oms_path,
        v199_path,
    }

    path = Path(invocation_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    invocation = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "invoke_admitted_paper_cancellation"
    )
    coordinator_calls = [
        node
        for node in ast.walk(invocation)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "coordinator"
    ]
    assert [call.func.attr for call in coordinator_calls].count("reserve") == 1
    assert [call.func.attr for call in coordinator_calls].count("acquire_lease") == 1
    assert [call.func.attr for call in coordinator_calls].count("execute") == 1
    assert [call.func.attr for call in coordinator_calls].count("release_lease") == 1
    execute_call = next(
        call for call in coordinator_calls if call.func.attr == "execute"
    )
    cancel_keyword = next(
        keyword for keyword in execute_call.keywords if keyword.arg == "cancel"
    )
    observe_keyword = next(
        keyword for keyword in execute_call.keywords if keyword.arg == "observe"
    )
    assert isinstance(cancel_keyword.value, ast.Name)
    assert cancel_keyword.value.id == "cancel"
    assert isinstance(observe_keyword.value, ast.Name)
    assert observe_keyword.value.id == "observe"

    path = Path(certification_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lifecycle = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_submit_cancel_reconcile"
    )
    coordinator_calls = [
        node
        for node in ast.walk(lifecycle)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "cancel_coordinator"
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    cancel_keyword = next(
        keyword
        for keyword in coordinator_calls[0].keywords
        if keyword.arg == "cancel"
    )
    assert isinstance(cancel_keyword.value, ast.Lambda)
    injected_calls = [
        node
        for node in ast.walk(cancel_keyword.value)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_request_order_cancellation"
    ]
    assert len(injected_calls) == 1

    path = Path(v199_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lifecycle = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_submit_cancel_reconcile"
    )
    coordinator_calls = [
        node
        for node in ast.walk(lifecycle)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "cancel_coordinator"
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    cancel_keyword = next(
        keyword
        for keyword in coordinator_calls[0].keywords
        if keyword.arg == "cancel"
    )
    assert isinstance(cancel_keyword.value, ast.Lambda)
    injected_calls = [
        node
        for node in ast.walk(cancel_keyword.value)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_request_order_cancellation"
    ]
    assert len(injected_calls) == 1

    path = Path(crypto_drill_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lifecycle = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_submit_cancel_reconcile"
    )
    coordinator_calls = [
        node
        for node in ast.walk(lifecycle)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "cancel_coordinator"
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    cancel_keyword = next(
        keyword
        for keyword in coordinator_calls[0].keywords
        if keyword.arg == "cancel"
    )
    assert isinstance(cancel_keyword.value, ast.Lambda)
    injected_calls = [
        node
        for node in ast.walk(cancel_keyword.value)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_request_order_cancellation"
    ]
    assert len(injected_calls) == 1

    path = Path(oms_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lifecycle = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_cancel_and_reconcile"
    )
    coordinator_calls = [
        node
        for node in ast.walk(lifecycle)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "cancel_coordinator"
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    cancel_keyword = next(
        keyword
        for keyword in coordinator_calls[0].keywords
        if keyword.arg == "cancel"
    )
    assert isinstance(cancel_keyword.value, ast.Lambda)
    injected_calls = [
        node
        for node in ast.walk(cancel_keyword.value)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "gateway"
        and node.func.attr == "request_order_cancellation"
    ]
    assert len(injected_calls) == 1


def test_autonomous_submit_routes_broker_call_through_shared_coordinator() -> None:
    path = Path("src/algotrader/execution/paper_autopilot_loop.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    execute_plan = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_execute_plan"
    )
    coordinator_calls = [
        node
        for node in ast.walk(execute_plan)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    broker_calls_inside = [
        node
        for node in ast.walk(coordinator_calls[0])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "submit_order"
    ]

    assert len(broker_calls_inside) == 1


def test_m435_operator_submit_requires_shared_durable_claim_first() -> None:
    path = Path("src/algotrader/execution/etf_sma_m435_paper_buy_submit.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    submit_once = functions["_submit_once"]
    coordinator_calls = [
        node
        for node in ast.walk(submit_once)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    broker_calls_inside = [
        node
        for node in ast.walk(coordinator_calls[0])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "submit_order_request"
    ]

    assert len(broker_calls_inside) == 1


def test_m370_operator_submit_requires_shared_durable_claim_first() -> None:
    path = Path("src/algotrader/execution/etf_sma_m370_paper_submit.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    submit_once = functions["_submit_once"]
    coordinator_calls = [
        node
        for node in ast.walk(submit_once)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    broker_calls_inside = [
        node
        for node in ast.walk(coordinator_calls[0])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "submit_order_request"
    ]

    assert len(broker_calls_inside) == 1


def test_m376_operator_close_requires_shared_durable_claim_first() -> None:
    path = Path("src/algotrader/cli.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    submit_close = functions["_submit_paper_lab_spy_close_submit"]
    coordinator_calls = [
        node
        for node in ast.walk(submit_close)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
    ]
    assert len(coordinator_calls) == 1
    broker_calls_inside = [
        node
        for node in ast.walk(coordinator_calls[0])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "submit_order_request"
    ]

    assert len(broker_calls_inside) == 1


def _ast_name_observations(path: Path, tree: ast.AST) -> list[NameObservation]:
    observations: list[NameObservation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            observations.append(
                NameObservation(str(path), node.lineno, "class", node.name)
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            observations.append(
                NameObservation(str(path), node.lineno, _function_kind(node), node.name)
            )
        elif isinstance(node, ast.Assign):
            observations.extend(
                NameObservation(str(path), _target_line(target, node), "assignment", name)
                for target in node.targets
                for name in _target_names(target)
            )
        elif isinstance(node, ast.AnnAssign):
            observations.extend(
                NameObservation(
                    str(path),
                    _target_line(node.target, node),
                    "annotated assignment",
                    name,
                )
                for name in _target_names(node.target)
            )
        elif isinstance(node, ast.AugAssign):
            observations.extend(
                NameObservation(
                    str(path),
                    _target_line(node.target, node),
                    "augmented assignment",
                    name,
                )
                for name in _target_names(node.target)
            )

    return observations


def _direct_mutation_calls(path: Path) -> list[tuple[str, str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    visitor = _MutationCallVisitor(path)
    visitor.visit(tree)
    return visitor.calls


def _dynamic_cancel_dispatchers(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    dispatchers: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        constants = {
            child.value
            for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        }
        if not {"cancel_order", "cancel_order_by_id"}.issubset(constants):
            continue
        has_dynamic_getattr = any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "getattr"
            and len(child.args) >= 2
            and isinstance(child.args[1], ast.Name)
            for child in ast.walk(node)
        )
        if has_dynamic_getattr:
            dispatchers.add((path.as_posix(), node.name))
    return dispatchers


class _MutationCallVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.function_stack: list[str] = []
        self.calls: list[tuple[str, str, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr in MUTATION_CALL_NAMES:
            function_name = self.function_stack[-1] if self.function_stack else "<module>"
            self.calls.append((self.path.as_posix(), function_name, node.func.attr))
        self.generic_visit(node)


def _function_kind(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if any(_decorator_name(decorator) == "property" for decorator in node.decorator_list):
        return "property"
    return "async function" if isinstance(node, ast.AsyncFunctionDef) else "function"


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _decorator_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _call_target_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (node.attr,)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(name for element in node.elts for name in _target_names(element))
    return ()


def _target_line(target: ast.AST, parent: ast.AST) -> int:
    return getattr(target, "lineno", getattr(parent, "lineno", 0))


def _public_runtime_observations(source: str, obj: Any) -> list[NameObservation]:
    return [
        NameObservation(source, None, _runtime_kind(value), name)
        for name, value in vars(obj).items()
        if _is_public(name)
    ]


def _runtime_kind(value: Any) -> str:
    if isinstance(value, property):
        return "runtime property"
    if isinstance(value, type):
        return "runtime class"
    if isinstance(value, ModuleType):
        return "runtime module"
    if callable(value):
        return "runtime callable"
    return "runtime attribute"


def _load_runtime_object(object_path: str) -> Any:
    module_name, object_name = object_path.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    return getattr(module, object_name)


def _forbidden_mutation_term(name: str) -> str:
    normalized = name.lower()
    for term in FORBIDDEN_MUTATION_TERMS:
        if term in normalized:
            return term
    return ""


def _is_public(name: str) -> bool:
    return not name.startswith("_")
