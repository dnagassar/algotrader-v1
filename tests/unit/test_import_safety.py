import ast
from pathlib import Path


FORBIDDEN_IMPORT_ROOTS = {
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
    "websockets",
}

FORBIDDEN_DYNAMIC_CALLS = {
    "__import__",
    "eval",
    "exec",
    "import_module",
    "importlib.import_module",
}


def test_production_code_does_not_import_network_broker_or_llm_modules() -> None:
    src_root = Path("src/algotrader")
    violations: list[str] = []

    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported_modules = _imported_modules(node)
            for module_name in imported_modules:
                root_module = module_name.split(".", maxsplit=1)[0]
                if root_module in FORBIDDEN_IMPORT_ROOTS:
                    violations.append(f"{path}: forbidden import {module_name}")

            dynamic_call = _forbidden_dynamic_call(node)
            if dynamic_call:
                violations.append(
                    f"{path}:{node.lineno}: forbidden dynamic call {dynamic_call}"
                )

    assert violations == []


def test_forbidden_dynamic_call_detector_flags_known_unsafe_calls() -> None:
    source = """
importlib.import_module("requests")
__import__("socket")
exec("print('unsafe')")
eval("1 + 1")
import_module("alpaca")
"""

    tree = ast.parse(source)
    detected = {
        dynamic_call
        for node in ast.walk(tree)
        if (dynamic_call := _forbidden_dynamic_call(node))
    }

    assert detected == {
        "importlib.import_module",
        "__import__",
        "exec",
        "eval",
        "import_module",
    }


def test_forbidden_dynamic_call_detector_ignores_regular_function_calls() -> None:
    tree = ast.parse(
        """
validate_alpaca_paper_ready()
config.require_paper_profile()
"""
    )

    detected = [
        dynamic_call
        for node in ast.walk(tree)
        if (dynamic_call := _forbidden_dynamic_call(node))
    ]

    assert detected == []


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)

    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)

    return ()


def _forbidden_dynamic_call(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""

    call_name = _call_name(node.func)
    if call_name in FORBIDDEN_DYNAMIC_CALLS:
        return call_name

    return ""


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
