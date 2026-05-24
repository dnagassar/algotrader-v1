from __future__ import annotations

import argparse
import ast
import inspect
import json
import re

import algotrader.cli as cli_module
import algotrader.research.advisory_operating_brief_content_bundle_cli as preview_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle_with_risk,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)


_COMMAND = "advisory-operating-brief-content-bundle-preview"
_RISK_FLAG = "--include-risk-authority"


def _s(*parts: str) -> str:
    return "".join(parts)


def test_risk_authority_preview_flag_is_accepted_by_parser() -> None:
    parser = _preview_parser()
    args = parser.parse_args((_RISK_FLAG,))
    json_args = parser.parse_args((_RISK_FLAG, "--format", "json"))

    assert args.include_risk_authority is True
    assert args.output_format == "text"
    assert json_args.include_risk_authority is True
    assert json_args.output_format == "json"
    assert _RISK_FLAG in parser._option_string_actions


def test_include_risk_authority_text_includes_risk_branch(capsys) -> None:
    expected = _expected_risk_export()

    default_risk_output = _run_preview_cli((_COMMAND, _RISK_FLAG), capsys)
    text_risk_output = _run_preview_cli(
        (_COMMAND, _RISK_FLAG, "--format", "text"),
        capsys,
    )

    assert default_risk_output == text_risk_output == expected.rendered_text
    assert "Risk Authority Briefs" in default_risk_output
    assert "risk_authority_brief_count: 1" in default_risk_output
    assert "Risk Authority Brief 1" in default_risk_output
    assert "authority_state: not_authorized" in default_risk_output


def test_include_risk_authority_json_includes_risk_branch_and_round_trips(
    capsys,
) -> None:
    expected = _expected_risk_export()

    output = _run_preview_cli((_COMMAND, _RISK_FLAG, "--format", "json"), capsys)
    payload = json.loads(output)

    assert output == expected.json_text
    assert output == json.dumps(
        expected.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert payload == expected.payload
    assert payload["risk_authority_brief_count"] == 1
    assert len(payload["risk_authority_briefs"]) == 1


def test_risk_inclusive_cli_invocations_are_byte_deterministic(capsys) -> None:
    first_text = _run_preview_cli((_COMMAND, _RISK_FLAG), capsys)
    second_text = _run_preview_cli((_COMMAND, _RISK_FLAG), capsys)
    first_json = _run_preview_cli((_COMMAND, _RISK_FLAG, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json", _RISK_FLAG), capsys)

    assert first_text == second_text == _expected_risk_export().rendered_text
    assert first_json == second_json == _expected_risk_export().json_text
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_production_cli_code_imports_no_tests_or_fixtures() -> None:
    for module in (cli_module, preview_module):
        imports = _import_references(module)

        assert all(not name.startswith("tests") for name in imports)
        assert "tests.fixtures" not in imports
        assert re.search(r"(?m)^\s*(from|import)\s+tests\b", _source_text(module)) is None
        assert (
            re.search(r"(?m)^\s*from\s+tests\.fixtures\b", _source_text(module))
            is None
        )


def test_no_file_path_vendor_broker_network_runtime_or_credential_options() -> None:
    parser = _preview_parser()
    option_text = _option_text(parser)
    option_strings = " ".join(parser._option_string_actions).lower()

    assert _RISK_FLAG in parser._option_string_actions
    for term in _blocked_option_terms():
        assert term not in option_text
        assert term not in option_strings


def test_risk_inclusive_output_adds_no_actionable_authority_states_or_fields(
    capsys,
) -> None:
    payload = json.loads(
        _run_preview_cli((_COMMAND, _RISK_FLAG, "--format", "json"), capsys)
    )
    rendered = _run_preview_cli((_COMMAND, _RISK_FLAG), capsys)

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


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _expected_risk_export():
    return export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_risk()
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
            if key in {"status", "authority", "authority_state", "eligibility_state"}:
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
