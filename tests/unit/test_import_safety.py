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

    assert violations == []


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)

    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)

    return ()
