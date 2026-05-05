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


ORCHESTRATION_BOUNDARY_RULES = (
    DependencyRule(
        source="algotrader.orchestration.screener_signal_flow",
        paths=(Path("src/algotrader/orchestration/screener_signal_flow.py"),),
        forbidden_prefixes=(
            "algotrader.execution",
            "algotrader.orchestration.trade_flow",
            "algotrader.orchestration.signal_trade_flow",
            "alpaca",
            "alpaca_trade_api",
        ),
    ),
    DependencyRule(
        source="algotrader.orchestration.signal_risk_flow",
        paths=(Path("src/algotrader/orchestration/signal_risk_flow.py"),),
        forbidden_prefixes=(
            "algotrader.execution",
            "algotrader.orchestration.trade_flow",
            "algotrader.orchestration.signal_trade_flow",
            "alpaca",
            "alpaca_trade_api",
        ),
    ),
)


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


def test_signal_modules_do_not_import_downstream_or_screener_layers() -> None:
    rule = DependencyRule(
        source="algotrader.signals.*",
        paths=_package_files("algotrader.signals"),
        forbidden_prefixes=(
            "algotrader.screener",
            "algotrader.risk",
            "algotrader.execution",
            "algotrader.portfolio",
            "algotrader.orchestration",
        ),
    )

    assert _dependency_violations(rule) == []


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
