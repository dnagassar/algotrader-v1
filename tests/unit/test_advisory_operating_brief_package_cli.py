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

import algotrader.cli as cli_module
import algotrader.research.advisory_operating_brief_cli as brief_preview_module
import algotrader.research.advisory_operating_brief_content_bundle_cli as bundle_preview_module
import algotrader.research.advisory_operating_brief_package_cli as preview_module
import algotrader.research.advisory_operating_brief_package_synthetic as synthetic_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_cli import (
    build_synthetic_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_package_export import (
    export_advisory_operating_brief_package,
)
from tests.fixtures.advisory_operating_brief_package import (
    build_synthetic_advisory_operating_brief_package as build_fixture_package,
)


_COMMAND = "advisory-operating-brief-package-preview"
_CONTENT_BUNDLE_COMMAND = "advisory-operating-brief-content-bundle-preview"
_RISK_FLAG = "--include-risk-authority"
_RESEARCH_QUEUE_FLAG = "--include-research-queue"
_PACKAGE_ID = "advisory-operating-brief-package:synthetic:2026-01-20"
_TITLE = "Synthetic advisory operating brief package"
_SUMMARY = "Advisory-only synthetic operating brief package content."
_AS_OF = "2026-01-20"
_BRANCH_KEYS = (
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "risk_authority_briefs",
    "research_queue_briefs",
)


def _s(*parts: str) -> str:
    return "".join(parts)


def test_package_preview_command_is_registered() -> None:
    preview_parser = _preview_parser()

    assert preview_parser.prog == f"algotrader {_COMMAND}"
    assert _COMMAND in _subparser_choices(build_parser())


def test_synthetic_preview_builder_uses_package_exportable_payload() -> None:
    package = build_synthetic_advisory_operating_brief_package()
    fixture_package = build_fixture_package()
    canonical_package = (
        synthetic_module.build_synthetic_advisory_operating_brief_package_preview()
    )
    export = export_advisory_operating_brief_package(package)

    assert type(package) is AdvisoryOperatingBriefPackage
    assert package == fixture_package == canonical_package
    assert export.payload == package.to_dict()
    assert export.payload == fixture_package.to_dict()
    assert _dict(export.payload["content_bundle"]) == package.content_bundle.to_dict()


def test_default_output_equals_text_output_and_export_rendered_text(capsys) -> None:
    expected = _expected_export()

    default_output = _run_preview_cli((_COMMAND,), capsys)
    text_output = _run_preview_cli((_COMMAND, "--format", "text"), capsys)

    assert default_output == text_output
    assert text_output == expected.rendered_text
    assert text_output.encode("utf-8") == expected.rendered_text.encode("utf-8")


def test_json_output_equals_compact_export_json_and_round_trips(capsys) -> None:
    expected = _expected_export()

    output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert output == expected.json_text
    assert output == json.dumps(
        expected.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert output != json.dumps(expected.payload, sort_keys=True)
    assert json.loads(output) == expected.payload
    assert output.encode("utf-8") == expected.json_text.encode("utf-8")


def test_repeated_text_and_json_invocations_are_byte_identical(capsys) -> None:
    first_text = _run_preview_cli((_COMMAND,), capsys)
    second_text = _run_preview_cli((_COMMAND,), capsys)
    first_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert first_text == second_text == _expected_export().rendered_text
    assert first_json == second_json == _expected_export().json_text
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_output_includes_package_metadata(capsys) -> None:
    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))

    for value in (
        "Advisory Operating Brief Package",
        "package_type: advisory_operating_brief_package",
        f"package_id: {_PACKAGE_ID}",
        f"title: {_TITLE}",
        f"summary: {_SUMMARY}",
        f"as_of: {_AS_OF}",
        "status: candidate_only",
        "authority: advisory_only",
        "capital_authority: False",
    ):
        assert value in text_output

    assert json_payload["package_id"] == _PACKAGE_ID
    assert json_payload["title"] == _TITLE
    assert json_payload["summary"] == _SUMMARY
    assert json_payload["as_of"] == _AS_OF
    assert json_payload["status"] == "candidate_only"
    assert json_payload["authority"] == "advisory_only"
    assert json_payload["capital_authority"] is False


def test_nested_output_includes_all_content_bundle_branches(capsys) -> None:
    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))
    content_bundle = _dict(json_payload["content_bundle"])

    for value in (
        "Candidate Research Briefs",
        "Strategy Eligibility Briefs",
        "Risk Authority Briefs",
        "Research Queue Briefs",
        "candidate_research_brief_count: 1",
        "strategy_eligibility_brief_count: 1",
        "risk_authority_brief_count: 1",
        "research_queue_brief_count: 1",
    ):
        assert value in text_output

    assert all(key in content_bundle for key in _BRANCH_KEYS)
    assert content_bundle["candidate_research_brief_count"] == 1
    assert content_bundle["strategy_eligibility_brief_count"] == 1
    assert content_bundle["risk_authority_brief_count"] == 1
    assert content_bundle["research_queue_brief_count"] == 1
    for branch_key in _BRANCH_KEYS:
        assert len(_list(content_bundle[branch_key])) == 1


def test_existing_content_bundle_preview_behavior_remains_unchanged(capsys) -> None:
    default_export = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )
    combined_export = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue(
            include_risk_authority=True,
        )
    )

    assert _run_preview_cli((_CONTENT_BUNDLE_COMMAND,), capsys) == (
        default_export.rendered_text
    )
    assert _run_preview_cli(
        (_CONTENT_BUNDLE_COMMAND, "--format", "json"),
        capsys,
    ) == default_export.json_text
    assert _run_preview_cli(
        (_CONTENT_BUNDLE_COMMAND, _RISK_FLAG, _RESEARCH_QUEUE_FLAG),
        capsys,
    ) == combined_export.rendered_text
    assert _run_preview_cli(
        (
            _CONTENT_BUNDLE_COMMAND,
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            "--format",
            "json",
        ),
        capsys,
    ) == combined_export.json_text


def test_package_preview_command_exposes_only_format_option() -> None:
    option_rows = _option_rows(_preview_parser())
    positional_rows = _positional_rows(_preview_parser())

    assert positional_rows == ()
    assert option_rows == (("output_format", ("--format",), ("text", "json")),)


def test_package_preview_command_exposes_no_external_input_options() -> None:
    option_text = _option_text(_preview_parser())

    for term in _blocked_option_terms():
        assert term not in option_text


def test_package_preview_performs_no_file_io(monkeypatch, capsys) -> None:
    def deny_file_io(*args: object, **kwargs: object) -> None:
        raise AssertionError("file I/O is not allowed for package preview")

    monkeypatch.setattr(builtins, "open", deny_file_io)
    monkeypatch.setattr(io, "open", deny_file_io)

    assert _run_preview_cli((_COMMAND,), capsys) == _expected_export().rendered_text


def test_package_preview_does_not_read_environment(monkeypatch, capsys) -> None:
    class DeniedEnvironment(dict[str, str]):
        def get(self, key: object, default: object = None) -> object:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __getitem__(self, key: str) -> str:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __contains__(self, key: object) -> bool:
            raise AssertionError(f"environment read is not allowed: {key!r}")

    monkeypatch.setattr(os, "environ", DeniedEnvironment())

    assert _run_preview_cli((_COMMAND,), capsys) == _expected_export().rendered_text


def test_package_preview_does_not_access_network(monkeypatch, capsys) -> None:
    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access is not allowed for package preview")

    monkeypatch.setattr(socket, "socket", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)

    assert _run_preview_cli((_COMMAND,), capsys) == _expected_export().rendered_text


def test_production_cli_modules_import_no_tests_or_fixtures() -> None:
    for module in (
        cli_module,
        brief_preview_module,
        bundle_preview_module,
        preview_module,
        synthetic_module,
    ):
        imports = _import_references(module)
        source = _source_text(module)

        assert all(not name.startswith("tests") for name in imports)
        assert "tests.fixtures" not in imports
        assert re.search(r"(?m)^\s*(from|import)\s+tests\b", source) is None
        assert re.search(r"(?m)^\s*from\s+tests\.fixtures\b", source) is None


def test_production_package_preview_has_no_forbidden_imports_or_calls() -> None:
    imports = set()
    call_names = set()
    for module in (preview_module, synthetic_module):
        imports.update(_import_references(module))
        call_names.update(_call_names(module))

    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_output_adds_no_actionable_authority_states_or_fields(capsys) -> None:
    rendered = _run_preview_cli((_COMMAND,), capsys)
    payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))
    compact = json.dumps(payload, sort_keys=True, separators=(",", ":")).lower()

    assert _payload_keys(payload).isdisjoint(_forbidden_actionable_field_names())
    assert _rendered_field_names(rendered).isdisjoint(
        _forbidden_actionable_field_names()
    )
    for state_value in _state_values(payload):
        lowered = state_value.lower()
        assert "paper" not in lowered
        assert "live" not in lowered
        assert "approved" not in lowered
        assert "trading_ready" not in lowered
        assert "trading-ready" not in lowered
        assert "actionable" not in lowered

    assert '"approved"' not in compact
    assert '"paper"' not in compact
    assert '"live"' not in compact
    assert "trading-ready" not in compact
    assert "trading_ready" not in compact
    assert "actionable" not in compact


def build_synthetic_equivalent_package() -> AdvisoryOperatingBriefPackage:
    return build_fixture_package()


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _expected_export():
    return export_advisory_operating_brief_package(build_synthetic_equivalent_package())


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


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


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


def _rendered_field_names(text: str) -> set[str]:
    field_names: set[str] = set()
    for line in text.splitlines():
        if line.startswith("- ") or ":" not in line:
            continue
        field_names.add(line.split(":", maxsplit=1)[0])
    return field_names


def _state_values(value: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key in {
                "status",
                "authority",
                "authority_state",
                "eligibility_state",
                "research_state",
            }:
                assert isinstance(nested_value, str)
                values.append(nested_value)
            values.extend(_state_values(nested_value))
    elif isinstance(value, list):
        for nested_value in value:
            values.extend(_state_values(nested_value))
    return tuple(values)


def _blocked_option_terms() -> tuple[str, ...]:
    return (
        _s("fi", "le"),
        _s("pa", "th"),
        _s("sour", "ce"),
        _s("ven", "dor"),
        _s("bro", "ker"),
        _s("net", "work"),
        _s("run", "time"),
        _s("cre", "dential"),
        "endpoint",
        "feed",
        "live",
        "paper",
    )


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
        _s("algotrader.", "sig", "nals"),
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
        _s("mas", "sive"),
        _s("net", "work"),
        _s("num", "py"),
        _s("op", "en", "ai"),
        "os",
        _s("pan", "das"),
        "pathlib",
        _s("poly", "gon"),
        _s("quant", "connect"),
        _s("re", "quests"),
        _s("so", "cket"),
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
        "from_dict",
        "from_file",
        "getenv",
        "glob",
        "import_module",
        _s("ing", "est"),
        "is_file",
        "iterdir",
        "json.dump",
        "json.load",
        "load",
        "loads",
        "mkdir",
        _s("op", "en"),
        "os.environ.get",
        "os.getenv",
        "post",
        _s("re", "ad"),
        "read_bytes",
        "read_csv",
        "read_text",
        _s("re", "quest"),
        _s("re", "quests.get"),
        "rglob",
        "save",
        _s("so", "cket.socket"),
        "stat",
        _s("sub", "mit_", "or", "der"),
        "time.time",
        "to_file",
        "to_sql",
        "urlopen",
        "walk",
        _s("wri", "te"),
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
