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
import algotrader.research.advisory_operating_brief_cli as preview_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_cli import (
    build_synthetic_advisory_operating_brief,
    render_advisory_operating_brief_preview,
)
from algotrader.research.advisory_operating_brief_export import (
    export_advisory_operating_brief,
)
from tests.fixtures.advisory_operating_brief import (
    build_synthetic_advisory_operating_brief as build_phase_143_fixture,
)


_COMMAND = "advisory-operating-brief-preview"
_SYNTHETIC_FIXTURE_ID = "synthetic_return_input_snapshot_fixture_001"
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)
_SYNTHETIC_FIXTURE_CHECKSUM = f"sha256:{_SYNTHETIC_FIXTURE_DIGEST}"


def _s(*parts: str) -> str:
    return "".join(parts)


def test_cli_preview_command_is_registered_on_existing_argparse_surface() -> None:
    preview_parser = _preview_parser()

    assert preview_parser.prog == f"algotrader {_COMMAND}"
    assert _COMMAND in _subparser_choices(build_parser())


def test_preview_builder_matches_phase_143_synthetic_fixture() -> None:
    preview_brief = build_synthetic_advisory_operating_brief()
    fixture_brief = build_phase_143_fixture()

    assert preview_brief.to_dict() == fixture_brief.to_dict()
    assert preview_brief is not fixture_brief


def test_default_command_prints_deterministic_rendered_text(capsys) -> None:
    expected = _expected_export().rendered_text

    assert main([_COMMAND]) == 0

    captured = capsys.readouterr()
    assert captured.out == expected
    assert captured.err == ""


def test_repeated_default_invocation_is_byte_identical(capsys) -> None:
    assert main([_COMMAND]) == 0
    first = capsys.readouterr().out

    assert main([_COMMAND]) == 0
    second = capsys.readouterr().out

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_json_format_prints_phase_147_compact_json(capsys) -> None:
    expected = _expected_export()

    assert main([_COMMAND, "--format", "json"]) == 0

    captured = capsys.readouterr()
    assert captured.out == expected.json_text
    assert captured.err == ""
    assert json.loads(captured.out) == expected.payload
    assert captured.out == json.dumps(
        expected.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert captured.out != json.dumps(expected.payload, sort_keys=True)


def test_preview_command_has_no_file_or_path_arguments() -> None:
    preview_parser = _preview_parser()
    option_actions = [
        action
        for action in preview_parser._actions
        if action.option_strings and action.dest != "help"
    ]
    positional_actions = [
        action
        for action in preview_parser._actions
        if not action.option_strings and action.dest != "help"
    ]

    assert positional_actions == []
    assert [(action.dest, tuple(action.option_strings)) for action in option_actions] == [
        ("output_format", ("--format",))
    ]
    assert option_actions[0].choices == ("text", "json")
    assert {
        forbidden
        for action in preview_parser._actions
        for forbidden in ("path", "file")
        if forbidden in action.dest.lower()
    } == set()


def test_preview_command_performs_no_file_io(monkeypatch, capsys) -> None:
    def deny_file_io(*args: object, **kwargs: object) -> None:
        raise AssertionError("file I/O is not allowed for the preview command")

    monkeypatch.setattr(builtins, "open", deny_file_io)
    monkeypatch.setattr(io, "open", deny_file_io)

    assert main([_COMMAND]) == 0
    assert capsys.readouterr().out == _expected_export().rendered_text


def test_preview_command_does_not_read_environment(monkeypatch, capsys) -> None:
    class DeniedEnvironment(dict[str, str]):
        def get(self, key: object, default: object = None) -> object:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __getitem__(self, key: str) -> str:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __contains__(self, key: object) -> bool:
            raise AssertionError(f"environment read is not allowed: {key!r}")

    monkeypatch.setattr(os, "environ", DeniedEnvironment())

    assert main([_COMMAND]) == 0
    assert capsys.readouterr().out == _expected_export().rendered_text


def test_preview_command_does_not_access_network(monkeypatch, capsys) -> None:
    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access is not allowed for the preview command")

    monkeypatch.setattr(socket, "socket", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)

    assert main([_COMMAND]) == 0
    assert capsys.readouterr().out == _expected_export().rendered_text


def test_preview_command_imports_no_runtime_vendor_or_ai_modules(
    monkeypatch,
    capsys,
) -> None:
    real_import = builtins.__import__
    blocked_imports: list[str] = []

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if level == 0 and _matches_blocked_prefix(name, _blocked_import_prefixes()):
            blocked_imports.append(name)
            raise AssertionError(f"blocked import during preview command: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    assert main([_COMMAND]) == 0
    assert capsys.readouterr().out == _expected_export().rendered_text
    assert blocked_imports == []


def test_preview_output_includes_fixed_type_status_and_provenance(capsys) -> None:
    assert main([_COMMAND]) == 0

    output = capsys.readouterr().out
    for value in (
        "advisory_operating_brief",
        "candidate_research_brief",
        "candidate_research_results",
        "candidate_research_result",
        "candidate_only",
        _SYNTHETIC_FIXTURE_DIGEST,
        _SYNTHETIC_FIXTURE_ID,
        _SYNTHETIC_FIXTURE_CHECKSUM,
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
    ):
        assert value in output


def test_preview_output_includes_limitations_and_non_claims(capsys) -> None:
    assert main([_COMMAND]) == 0

    output = capsys.readouterr().out
    for value in (
        "Limitations",
        "Non-Claims",
        "metadata-only container for existing candidate research briefs",
        "does not create research, compute metrics, or mutate brief payloads",
        "not source approval",
        "not data approval",
        "not trading readiness",
    ):
        assert value in output


def test_preview_output_introduces_no_extra_decision_language(capsys) -> None:
    expected = _expected_export()

    assert main([_COMMAND]) == 0

    output = capsys.readouterr().out
    assert output == expected.rendered_text
    fixed_output = _remove_payload_strings(output, expected.payload).lower()
    for term in _blocked_output_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", fixed_output) is None


def test_preview_export_path_does_not_mutate_source_objects() -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    before_payload = operating_brief.to_dict()

    rendered = render_advisory_operating_brief_preview()
    exported = export_advisory_operating_brief(operating_brief)

    assert rendered == _expected_export().rendered_text
    assert operating_brief.to_dict() == before_payload
    assert exported.payload == before_payload
    assert export_advisory_operating_brief(operating_brief).payload == before_payload


def test_preview_module_has_no_forbidden_imports_calls_or_literals() -> None:
    imports = _import_references(preview_module)
    call_names = _call_names(preview_module)
    source = _source_text(preview_module)
    lowered = source.lower()
    upper_source = source.upper()

    assert all(not module.startswith("tests.") for module in imports)
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())
    for code_points in _real_symbol_codes():
        symbol = "".join(chr(code_point) for code_point in code_points)
        assert re.search(rf"(?<![A-Z0-9]){symbol}(?![A-Z0-9])", upper_source) is None
    for term in _provider_or_sdk_terms():
        assert term not in lowered
    for term in _sensitive_terms():
        assert term not in lowered
    for term in _location_markers():
        assert term not in lowered
    for term in _blocked_source_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", lowered) is None


def test_cli_module_keeps_runtime_imports_lazy_for_preview() -> None:
    top_level_imports = _top_level_import_references(cli_module)

    assert [
        module_name
        for module_name in top_level_imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []


def _expected_export():
    return export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )


def _preview_parser() -> argparse.ArgumentParser:
    return _subparser_choices(build_parser())[_COMMAND]


def _subparser_choices(
    parser: argparse.ArgumentParser,
) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices
    raise AssertionError("parser has no subcommands")


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


def _top_level_import_references(module: object) -> set[str]:
    imports: set[str] = set()

    for node in _tree(module).body:
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


def _payload_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, dict):
        strings: list[str] = []
        for nested_value in value.values():
            strings.extend(_payload_strings(nested_value))
        return tuple(strings)

    if isinstance(value, list):
        strings = []
        for nested_value in value:
            strings.extend(_payload_strings(nested_value))
        return tuple(strings)

    if isinstance(value, str):
        return (value,)

    return ()


def _remove_payload_strings(text: str, payload: object) -> str:
    cleaned = text
    for value in _payload_strings(payload):
        cleaned = cleaned.replace(value, "")
    return cleaned


def _blocked_import_prefixes() -> tuple[str, ...]:
    return (
        "aiohttp",
        _s("algotrader.", "bro", "ker"),
        _s("algotrader.", "bro", "kers"),
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
        _s("num", "py"),
        _s("op", "en", "ai"),
        "os",
        _s("pan", "das"),
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
        _s("import_module"),
        _s("ing", "est"),
        "is_file",
        "iterdir",
        "load",
        "mkdir",
        _s("op", "en"),
        "os.environ.get",
        "os.getenv",
        "post",
        "read",
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
        "to_file",
        "to_sql",
        "urlopen",
        "walk",
        "write",
        "write_text",
    }


def _real_symbol_codes() -> tuple[tuple[int, ...], ...]:
    return (
        (83, 80, 89),
        (73, 86, 86),
        (86, 79, 79),
        (81, 81, 81),
        (86, 84, 73),
        (73, 87, 77),
        (68, 73, 65),
        (65, 71, 71),
        (66, 78, 68),
        (84, 76, 84),
        (71, 76, 68),
        (69, 70, 65),
        (69, 69, 77),
    )


def _provider_or_sdk_terms() -> set[str]:
    return {
        _s("al", "paca"),
        _s("alpha van", "tage"),
        _s("bloom", "berg"),
        _s("fact", "set"),
        _s("finn", "hub"),
        _s("interactive bro", "kers"),
        _s("poly", "gon"),
        _s("quant", "connect"),
        _s("quan", "dl"),
        _s("refini", "tiv"),
        _s("ti", "ingo"),
        _s("ya", "hoo"),
        _s("y", "finance"),
    }


def _sensitive_terms() -> set[str]:
    return {
        _s("a", "pi_key"),
        _s("a", "pikey"),
        _s("bear", "er"),
        _s("client_", "sec", "ret"),
        _s("cred", "ential"),
        _s("oa", "uth"),
        _s("pass", "word"),
        _s("private", "_key"),
        _s("sec", "ret"),
        _s("to", "ken"),
    }


def _location_markers() -> set[str]:
    return {
        _s(":", chr(47), chr(47)),
        _s("ht", "tp", ":"),
        _s("ht", "tps", ":"),
        _s("w", "ww."),
        _s(".", "com"),
        _s(".da", "ta", chr(47)),
        _s(".", "csv"),
        _s(".", "jsonl"),
        _s(".", "parquet"),
        _s(".", "zip"),
        chr(47),
        chr(92),
    }


def _blocked_source_terms() -> set[str]:
    return {
        _s("app", "roval"),
        _s("app", "roved"),
        _s("bench", "mark"),
        _s("bro", "ker"),
        _s("ca", "sh"),
        _s("or", "der"),
        _s("port", "folio"),
        _s("allo", "cation"),
        _s("po", "sition"),
        _s("prior", "itize"),
        _s("ra", "nk"),
        _s("reco", "mmend"),
        _s("run", "time"),
        _s("sco", "re"),
        _s("sig", "nal"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "de"),
    }


def _blocked_output_terms() -> set[str]:
    return {
        _s("act", "ion"),
        _s("act", "ions"),
        _s("app", "roval"),
        _s("app", "roved"),
        _s("bench", "mark"),
        _s("bench", "marks"),
        _s("bro", "ker"),
        _s("bro", "kers"),
        _s("ca", "sh"),
        _s("co", "st"),
        _s("co", "sts"),
        _s("fi", "ll"),
        _s("fi", "lls"),
        _s("or", "der"),
        _s("or", "ders"),
        _s("port", "folio"),
        _s("port", "folios"),
        _s("allo", "cation"),
        _s("allo", "cations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        _s("prior", "itize"),
        _s("prior", "itized"),
        _s("ra", "nk"),
        _s("ra", "nking"),
        _s("reco", "mmend"),
        _s("reco", "mmendation"),
        _s("reco", "mmendations"),
        _s("run", "time"),
        _s("sco", "re"),
        _s("sco", "ring"),
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "de"),
        _s("tra", "des"),
    }
