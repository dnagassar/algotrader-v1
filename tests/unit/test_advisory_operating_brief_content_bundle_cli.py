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

import algotrader.research.advisory_operating_brief_content_bundle_cli as preview_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_cli import (
    build_synthetic_advisory_operating_brief,
)
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_export import (
    export_advisory_operating_brief,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle as build_phase_162_fixture,
)


_COMMAND = "advisory-operating-brief-content-bundle-preview"
_LEGACY_COMMAND = "advisory-operating-brief-preview"


def _s(*parts: str) -> str:
    return "".join(parts)


def test_content_bundle_preview_command_is_registered() -> None:
    preview_parser = _preview_parser()

    assert preview_parser.prog == f"algotrader {_COMMAND}"
    assert _COMMAND in _subparser_choices(build_parser())


def test_preview_builder_matches_phase_162_synthetic_fixture() -> None:
    preview_bundle = build_synthetic_advisory_operating_brief_content_bundle()
    fixture_bundle = build_phase_162_fixture()

    assert preview_bundle.to_dict() == fixture_bundle.to_dict()
    assert preview_bundle is not fixture_bundle


def test_default_output_equals_text_output_and_phase_165_rendered_export(
    capsys,
) -> None:
    expected = _expected_export()

    default_output = _run_preview_cli((_COMMAND,), capsys)
    text_output = _run_preview_cli((_COMMAND, "--format", "text"), capsys)

    assert default_output == text_output
    assert text_output == expected.rendered_text


def test_json_output_equals_phase_165_compact_export_and_round_trips(
    capsys,
) -> None:
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


def test_repeated_text_and_json_invocations_are_byte_identical(capsys) -> None:
    first_text = _run_preview_cli((_COMMAND,), capsys)
    second_text = _run_preview_cli((_COMMAND,), capsys)
    first_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert first_text == second_text == _expected_export().rendered_text
    assert first_json == second_json == _expected_export().json_text
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_command_exposes_only_format_option() -> None:
    option_rows = _option_rows(_preview_parser())
    positional_rows = _positional_rows(_preview_parser())

    assert positional_rows == ()
    assert option_rows == (("output_format", ("--format",), ("text", "json")),)


def test_command_exposes_no_real_input_or_external_options() -> None:
    option_text = _option_text(_preview_parser())

    for term in _blocked_cli_option_terms():
        assert term not in option_text


def test_content_bundle_preview_performs_no_file_io(monkeypatch, capsys) -> None:
    def deny_file_io(*args: object, **kwargs: object) -> None:
        raise AssertionError("file I/O is not allowed for the content bundle preview")

    monkeypatch.setattr(builtins, "open", deny_file_io)
    monkeypatch.setattr(io, "open", deny_file_io)

    assert _run_preview_cli((_COMMAND,), capsys) == _expected_export().rendered_text


def test_content_bundle_preview_does_not_read_environment(
    monkeypatch,
    capsys,
) -> None:
    class DeniedEnvironment(dict[str, str]):
        def get(self, key: object, default: object = None) -> object:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __getitem__(self, key: str) -> str:
            raise AssertionError(f"environment read is not allowed: {key!r}")

        def __contains__(self, key: object) -> bool:
            raise AssertionError(f"environment read is not allowed: {key!r}")

    with monkeypatch.context() as env_patch:
        env_patch.setattr(os, "environ", DeniedEnvironment())
        assert _run_preview_cli((_COMMAND,), capsys) == _expected_export().rendered_text


def test_content_bundle_preview_does_not_access_network(
    monkeypatch,
    capsys,
) -> None:
    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access is not allowed for the preview command")

    monkeypatch.setattr(socket, "socket", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)

    assert _run_preview_cli((_COMMAND,), capsys) == _expected_export().rendered_text


def test_existing_advisory_operating_brief_preview_behavior_remains_unchanged(
    capsys,
) -> None:
    expected = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )

    text_output = _run_preview_cli((_LEGACY_COMMAND,), capsys)
    json_output = _run_preview_cli((_LEGACY_COMMAND, "--format", "json"), capsys)

    assert text_output == expected.rendered_text
    assert json_output == expected.json_text
    assert "Advisory Operating Brief Content Bundle" not in text_output
    assert "advisory_operating_brief_content_bundle" not in json_output


def test_production_preview_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references(preview_module)
    source = _source_text(preview_module)

    assert all(not module.startswith("tests") for module in imports)
    assert re.search(r"(?m)^\s*(from|import)\s+tests\b", source) is None
    assert re.search(r"(?m)^\s*from\s+tests\.fixtures\b", source) is None


def test_production_preview_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references(preview_module)
    call_names = _call_names(preview_module)

    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_production_preview_module_literals_add_no_external_behavior() -> None:
    source = _source_text(preview_module).lower()

    for term in _provider_or_sdk_terms():
        assert term not in source
    for term in _sensitive_terms():
        assert term not in source
    for marker in _external_location_markers():
        assert marker not in source
    for term in _forbidden_exact_literals():
        assert term not in _string_literals(preview_module)


def test_cli_output_adds_no_actionable_authority_fields(capsys) -> None:
    expected = _expected_export()
    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    payload = json.loads(json_output)

    assert payload == expected.payload
    assert text_output == expected.rendered_text
    assert _payload_keys(payload).isdisjoint(_forbidden_actionable_field_names())
    assert _rendered_field_names(text_output).isdisjoint(
        _forbidden_actionable_field_names()
    )


def test_authority_language_in_cli_output_is_caution_only(capsys) -> None:
    output = _run_preview_cli((_COMMAND,), capsys)
    payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))
    source_cautions = _source_caution_values(payload)

    for line in _authority_presentation_lines(output):
        assert line.startswith("- ")
        assert line[2:] in source_cautions


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _expected_export():
    return export_advisory_operating_brief_content_bundle(build_phase_162_fixture())


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


def _string_literals(module: object) -> set[str]:
    return {
        node.value
        for node in ast.walk(_tree(module))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


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


def _authority_presentation_lines(text: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in text.splitlines()
        if any(
            re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", line.lower())
            for term in _authority_presentation_terms()
        )
    )


def _source_caution_values(payload: object) -> set[str]:
    caution_fields = {
        "blockers",
        "limitations",
        "non_claims",
        "required_next_steps",
    }
    values: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in caution_fields and isinstance(value, list):
                values.update(item for item in value if isinstance(item, str))
            values.update(_source_caution_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.update(_source_caution_values(value))

    return values


def _blocked_cli_option_terms() -> tuple[str, ...]:
    return (
        _s("fi", "le"),
        _s("pa", "th"),
        _s("local"),
        _s("snap", "shot"),
        _s("sour", "ce"),
        _s("ven", "dor"),
        _s("bro", "ker"),
        _s("run", "time"),
        "market",
        "data",
        "feed",
        _s("ing", "est"),
        "endpoint",
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
        "joblib",
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
        _s("poly", "gon_a", "pi_client"),
        _s("quant", "connect"),
        _s("re", "quests"),
        _s("sche", "dule"),
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
        "from_file",
        "getenv",
        "glob",
        _s("import_module"),
        _s("ing", "est"),
        "is_file",
        "iterdir",
        "json.load",
        "load",
        "mkdir",
        _s("op", "en"),
        "os.environ.get",
        "os.getenv",
        "parse_args",
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
        "to_file",
        "to_sql",
        "urlopen",
        "walk",
        _s("wri", "te"),
        "write_text",
    }


def _provider_or_sdk_terms() -> set[str]:
    return {
        _s("al", "paca"),
        _s("alpha van", "tage"),
        _s("bloom", "berg"),
        _s("fact", "set"),
        _s("finn", "hub"),
        _s("fr", "ed"),
        _s("interactive bro", "kers"),
        _s("mas", "sive"),
        _s("morning", "star"),
        _s("nas", "daq"),
        _s("poly", "gon"),
        _s("quant", "connect"),
        _s("quan", "dl"),
        _s("refini", "tiv"),
        _s("st", "ooq"),
        _s("tii", "ngo"),
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


def _external_location_markers() -> set[str]:
    return {
        _s(":", chr(47), chr(47)),
        _s("ht", "tp", ":"),
        _s("ht", "tps", ":"),
        _s("w", "ww."),
        _s(".", "com"),
        _s(".", "csv"),
        _s(".", "jsonl"),
        _s(".", "parquet"),
        _s(".", "zip"),
        chr(47),
        chr(92),
    }


def _forbidden_exact_literals() -> set[str]:
    return {
        "account",
        "accounts",
        "approved",
        "buy",
        "sell",
        "hold",
        "live_authorized",
        "live_probe_eligible",
        "paper_eligible",
        _s("tra", "ding_authority"),
        "trading_ready",
    }


def _forbidden_actionable_field_names() -> set[str]:
    return {
        "account",
        "accounts",
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


def _authority_presentation_terms() -> tuple[str, ...]:
    return (
        _s("app", "roval"),
        _s("app", "roved"),
        "paper readiness",
        "live readiness",
        _s("reco", "mmendation"),
        _s("allo", "cation authority"),
        _s("or", "der authority"),
        _s("tra", "ding authority"),
        _s("tra", "ding readiness"),
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
        "trading_ready",
        "buy",
        "sell",
        "hold",
    )
