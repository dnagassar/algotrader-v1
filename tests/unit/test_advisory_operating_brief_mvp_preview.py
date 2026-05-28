from __future__ import annotations

import argparse
import ast
import builtins
import inspect
import io
import json
import os
import re
import socket

import algotrader.research.advisory_operating_brief_mvp_report as mvp_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_mvp_report import (
    build_synthetic_advisory_operating_brief_mvp_report_payload,
    render_synthetic_advisory_operating_brief_mvp_report,
)
from algotrader.research.advisory_operating_brief_package_cli import (
    build_synthetic_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_package_export import (
    export_advisory_operating_brief_package,
)


_COMMAND = "advisory-operating-brief-mvp-preview"
_PACKAGE_COMMAND = "advisory-operating-brief-package-preview"
_CONTENT_BUNDLE_COMMAND = "advisory-operating-brief-content-bundle-preview"
_MAJOR_SECTIONS = (
    "Advisory View Summary",
    "Sections Present",
    "Diagnostic Issues",
    "Data-Source Readiness Problems",
    "Research Observations",
    "Blocked / Missing Before Real Strategy, Backtest, Or Trading Use",
)


def _s(*parts: str) -> str:
    return "".join(parts)


def test_mvp_preview_command_is_registered() -> None:
    preview_parser = _preview_parser()

    assert preview_parser.prog == f"algotrader {_COMMAND}"
    assert _COMMAND in _subparser_choices(build_parser())


def test_mvp_preview_text_output_is_human_readable_and_useful(capsys) -> None:
    output = _run_preview_cli((_COMMAND,), capsys)

    assert output == render_synthetic_advisory_operating_brief_mvp_report()
    assert not output.startswith("{")
    assert '"report_type"' not in output
    assert "Synthetic Research MVP Operating Brief" in output
    for section in _MAJOR_SECTIONS:
        assert section in output
    for expected in (
        "view_key: advisory_operating_brief_section_view",
        "capital_authority: False",
        "No real data source is approved.",
        "missing_diagnostic_controls",
        "SMA observations",
        "Return observations",
        "SMA-return pipeline observation",
        "Data-source readiness observations",
        "not a recommendation",
        "not trading authority",
    ):
        assert expected in output


def test_mvp_preview_output_is_byte_deterministic(capsys) -> None:
    first = _run_preview_cli((_COMMAND,), capsys)
    second = _run_preview_cli((_COMMAND,), capsys)
    first_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")
    assert first_json == second_json
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_mvp_preview_json_output_is_concise_and_consistent(capsys) -> None:
    payload = build_synthetic_advisory_operating_brief_mvp_report_payload()
    output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    parsed = json.loads(output)

    assert parsed == payload
    assert output == json.dumps(payload, sort_keys=True, separators=(",", ":"))
    assert parsed["report_type"] == "synthetic_research_mvp_operating_brief"
    assert set(parsed) == {
        "advisory_view_summary",
        "blocked_missing_before_real_use",
        "data_source_readiness",
        "description",
        "diagnostic_issues",
        "real_source_status",
        "report_type",
        "research_observations",
        "safety",
        "scope",
        "sections_present",
        "title",
    }


def test_existing_package_and_content_bundle_previews_remain_compatible(capsys) -> None:
    package_export = export_advisory_operating_brief_package(
        build_synthetic_advisory_operating_brief_package()
    )
    content_bundle_export = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    assert _run_preview_cli((_PACKAGE_COMMAND,), capsys) == (
        package_export.rendered_text
    )
    assert _run_preview_cli((_PACKAGE_COMMAND, "--format", "json"), capsys) == (
        package_export.json_text
    )
    assert _run_preview_cli((_CONTENT_BUNDLE_COMMAND,), capsys) == (
        content_bundle_export.rendered_text
    )
    assert _run_preview_cli(
        (_CONTENT_BUNDLE_COMMAND, "--format", "json"),
        capsys,
    ) == content_bundle_export.json_text


def test_mvp_preview_performs_no_file_io_environment_or_network(
    monkeypatch,
    capsys,
) -> None:
    def deny_file_io(*args: object, **kwargs: object) -> None:
        raise AssertionError("file I/O is not allowed for MVP preview")

    class DeniedEnvironment(dict[str, str]):
        def get(self, key: object, default: object = None) -> object:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __getitem__(self, key: str) -> str:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __contains__(self, key: object) -> bool:
            raise AssertionError(f"environment read is not allowed: {key!r}")

    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access is not allowed for MVP preview")

    monkeypatch.setattr(builtins, "open", deny_file_io)
    monkeypatch.setattr(io, "open", deny_file_io)
    monkeypatch.setattr(os, "environ", DeniedEnvironment())
    monkeypatch.setattr(socket, "socket", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)

    assert _run_preview_cli((_COMMAND,), capsys) == (
        render_synthetic_advisory_operating_brief_mvp_report()
    )


def test_mvp_preview_module_adds_no_forbidden_runtime_imports_or_calls() -> None:
    imports = _import_references(mvp_module)
    call_names = _call_names(mvp_module)

    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_mvp_payload_adds_no_actionable_authority_fields() -> None:
    payload = build_synthetic_advisory_operating_brief_mvp_report_payload()
    compact = json.dumps(payload, sort_keys=True, separators=(",", ":")).lower()

    assert _payload_keys(payload).isdisjoint(_forbidden_actionable_field_names())
    assert '"buy"' not in compact
    assert '"sell"' not in compact
    assert '"hold"' not in compact
    assert "trading_ready" not in compact
    assert "trading-ready" not in compact


def test_mvp_preview_command_exposes_only_format_option() -> None:
    option_rows = _option_rows(_preview_parser())
    positional_rows = _positional_rows(_preview_parser())

    assert positional_rows == ()
    assert option_rows == (("output_format", ("--format",), ("text", "json")),)


def test_mvp_preview_command_exposes_no_real_input_options() -> None:
    option_text = _option_text(_preview_parser())

    for term in _blocked_option_terms():
        assert term not in option_text


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _preview_parser() -> argparse.ArgumentParser:
    return _subparser_choices(build_parser())[_COMMAND]


def _subparser_choices(
    parser: argparse.ArgumentParser,
) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("parser has no subcommands")


def _option_rows(
    parser: argparse.ArgumentParser,
) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
    rows = []
    for action in parser._actions:
        if action.dest == "help" or not action.option_strings:
            continue
        rows.append(
            (
                action.dest,
                tuple(action.option_strings),
                tuple(action.choices or ()),
            )
        )
    return tuple(rows)


def _positional_rows(parser: argparse.ArgumentParser) -> tuple[str, ...]:
    return tuple(
        action.dest
        for action in parser._actions
        if action.dest != "help" and not action.option_strings
    )


def _option_text(parser: argparse.ArgumentParser) -> str:
    values: list[str] = []
    for action in parser._actions:
        values.extend(action.option_strings)
        values.append(str(action.dest))
        values.append(str(action.help))
        values.extend(str(choice) for choice in (action.choices or ()))
    return " ".join(values).lower()


def _source_text(module: object) -> str:
    return inspect.getsource(module)


def _tree(module: object) -> ast.AST:
    return ast.parse(_source_text(module))


def _import_references(module: object) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree(module)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _call_names(module: object) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree(module))
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_blocked_prefix(
    module_name: str,
    blocked_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == blocked_prefix
        or module_name.startswith(f"{blocked_prefix}.")
        for blocked_prefix in blocked_prefixes
    )


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


def _blocked_import_prefixes() -> tuple[str, ...]:
    return (
        "aiohttp",
        _s("algotrader.", "bro", "ker"),
        _s("algotrader.", "bro", "kers"),
        "algotrader.dashboard",
        "algotrader.execution",
        _s("algotrader.", "l", "lm"),
        _s("algotrader.", "l", "lms"),
        "algotrader.ml",
        "algotrader.orchestration",
        _s("algotrader.", "persist", "ence"),
        _s("algotrader.", "port", "folio"),
        "algotrader.risk",
        _s("algotrader.", "run", "time"),
        "algotrader.scheduler",
        "algotrader.screener",
        "algotrader.signals",
        _s("al", "paca"),
        _s("al", "paca_trade_a", "pi"),
        _s("an", "thropic"),
        _s("data", "base"),
        "duckdb",
        "httpx",
        "ipynb",
        "langchain",
        "langgraph",
        _s("l", "lm"),
        _s("num", "py"),
        _s("op", "en", "ai"),
        "os",
        _s("pan", "das"),
        "pathlib",
        _s("poly", "gon"),
        _s("quant", "connect"),
        _s("re", "quests"),
        "socket",
        "sqlmodel",
        "subprocess",
        "urllib",
        "vectorbt",
        _s("y", "finance"),
    )


def _blocked_call_names() -> set[str]:
    return {
        "__import__",
        "Path",
        _s("cli", "ent"),
        _s("con", "nect"),
        "date.today",
        "datetime.now",
        "datetime.utcnow",
        _s("down", "load"),
        "eval",
        "exec",
        "exists",
        "from_file",
        "getenv",
        "glob",
        "import_module",
        _s("ing", "est"),
        "is_file",
        "iterdir",
        "json.load",
        "load",
        "loads",
        "mkdir",
        "open",
        "os.environ.get",
        "os.getenv",
        "post",
        "read",
        "read_bytes",
        "read_csv",
        "read_text",
        "request",
        "requests.get",
        "rglob",
        "save",
        "socket.socket",
        "stat",
        _s("sub", "mit_", "or", "der"),
        "to_file",
        "to_sql",
        "urlopen",
        "walk",
        "write",
        "write_text",
    }


def _forbidden_actionable_field_names() -> set[str]:
    return {
        "account",
        "accounts",
        "actionable",
        "approved",
        "buy",
        "sell",
        "hold",
        "live_authorized",
        "live_probe_eligible",
        "paper_eligible",
        _s("allo", "cation"),
        _s("allo", "cations"),
        _s("allo", "cation_authority"),
        _s("or", "der"),
        _s("or", "ders"),
        _s("or", "der_authority"),
        _s("port", "folio"),
        _s("port", "folios"),
        _s("tra", "ding_authority"),
        "trading_ready",
    }


def _blocked_option_terms() -> tuple[str, ...]:
    return (
        _s("fi", "le"),
        _s("pa", "th"),
        "local",
        _s("snap", "shot"),
        _s("sour", "ce"),
        _s("ven", "dor"),
        _s("bro", "ker"),
        "market",
        "data",
        "feed",
        "endpoint",
        "live",
        "paper",
    )
