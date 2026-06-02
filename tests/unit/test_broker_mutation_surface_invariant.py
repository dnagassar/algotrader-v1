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
