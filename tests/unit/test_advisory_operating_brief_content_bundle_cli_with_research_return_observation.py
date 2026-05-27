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
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation,
    build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)


_COMMAND = "advisory-operating-brief-content-bundle-preview"
_RISK_FLAG = "--include-risk-authority"
_RESEARCH_QUEUE_FLAG = "--include-research-queue"
_SMA_FLAG = "--include-sma-research-observation"
_RESEARCH_RETURN_FLAG = "--include-research-return-observation"
_BRANCH_KEYS = (
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "risk_authority_briefs",
    "research_queue_briefs",
    "sma_research_observation_briefs",
    "research_return_observation_briefs",
)


def _s(*parts: str) -> str:
    return "".join(parts)


def test_research_return_observation_preview_flag_is_accepted_by_parser() -> None:
    parser = _preview_parser()
    args = parser.parse_args((_RESEARCH_RETURN_FLAG,))
    json_args = parser.parse_args((_RESEARCH_RETURN_FLAG, "--format", "json"))
    combined_args = parser.parse_args(
        (_RISK_FLAG, _RESEARCH_QUEUE_FLAG, _SMA_FLAG, _RESEARCH_RETURN_FLAG)
    )

    assert args.include_research_return_observation is True
    assert args.include_risk_authority is False
    assert args.include_research_queue is False
    assert args.include_sma_research_observation is False
    assert args.output_format == "text"
    assert json_args.include_research_return_observation is True
    assert json_args.output_format == "json"
    assert combined_args.include_risk_authority is True
    assert combined_args.include_research_queue is True
    assert combined_args.include_sma_research_observation is True
    assert combined_args.include_research_return_observation is True
    assert _RESEARCH_RETURN_FLAG in parser._option_string_actions


def test_existing_default_text_and_json_output_remain_unchanged(capsys) -> None:
    expected = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert text_output == expected.rendered_text
    assert json_output == expected.json_text
    assert "Research Return Observation Briefs" not in text_output
    assert "research_return_observation_briefs" not in json_output


def test_existing_risk_research_queue_and_sma_output_remains_unchanged(
    capsys,
) -> None:
    expected = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_observation(
            include_risk_authority=True,
            include_research_queue=True,
        )
    )

    text_output = _run_preview_cli(
        (_COMMAND, _RISK_FLAG, _RESEARCH_QUEUE_FLAG, _SMA_FLAG),
        capsys,
    )
    json_output = _run_preview_cli(
        (
            _COMMAND,
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _SMA_FLAG,
            "--format",
            "json",
        ),
        capsys,
    )

    assert text_output == expected.rendered_text
    assert json_output == expected.json_text
    assert "Research Return Observation Briefs" not in text_output
    assert "research_return_observation_briefs" not in json_output


def test_include_research_return_observation_text_includes_return_branch_only(
    capsys,
) -> None:
    expected = _expected_research_return_export()

    default_output = _run_preview_cli((_COMMAND, _RESEARCH_RETURN_FLAG), capsys)
    text_output = _run_preview_cli(
        (_COMMAND, _RESEARCH_RETURN_FLAG, "--format", "text"),
        capsys,
    )

    assert default_output == text_output == expected.rendered_text
    assert "Candidate Research Briefs" in default_output
    assert "Strategy Eligibility Briefs" in default_output
    assert "Research Return Observation Briefs" in default_output
    assert "research_return_observation_brief_count: 1" in default_output
    assert "Research Return Observation Brief 1" in default_output
    assert "mechanical_state: returns_constructed" in default_output
    assert "mechanical_state: insufficient_return_history" in default_output
    assert "Risk Authority Briefs" not in default_output
    assert "risk_authority_brief_count" not in default_output
    assert "Research Queue Briefs" not in default_output
    assert "research_queue_brief_count" not in default_output
    assert "SMA Research Observation Briefs" not in default_output
    assert "sma_research_observation_brief_count" not in default_output


def test_include_research_return_observation_json_round_trips(capsys) -> None:
    expected = _expected_research_return_export()

    output = _run_preview_cli(
        (_COMMAND, _RESEARCH_RETURN_FLAG, "--format", "json"),
        capsys,
    )
    payload = json.loads(output)

    assert output == expected.json_text
    assert output == json.dumps(
        expected.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert payload == expected.payload
    assert payload["research_return_observation_brief_count"] == 1
    assert len(payload["research_return_observation_briefs"]) == 1
    assert "risk_authority_brief_count" not in payload
    assert "risk_authority_briefs" not in payload
    assert "research_queue_brief_count" not in payload
    assert "research_queue_briefs" not in payload
    assert "sma_research_observation_brief_count" not in payload
    assert "sma_research_observation_briefs" not in payload


def test_all_flags_output_contains_all_content_bundle_branches(capsys) -> None:
    expected = _expected_research_return_export(
        include_risk_authority=True,
        include_research_queue=True,
        include_sma_research_observation=True,
    )

    text_output = _run_preview_cli(
        (_COMMAND, _RISK_FLAG, _RESEARCH_QUEUE_FLAG, _SMA_FLAG, _RESEARCH_RETURN_FLAG),
        capsys,
    )
    json_output = _run_preview_cli(
        (
            _COMMAND,
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _SMA_FLAG,
            _RESEARCH_RETURN_FLAG,
            "--format",
            "json",
        ),
        capsys,
    )
    payload = json.loads(json_output)
    lines = tuple(text_output.splitlines())

    assert text_output == expected.rendered_text
    assert json_output == expected.json_text
    assert payload == expected.payload
    assert all(key in payload for key in _BRANCH_KEYS)
    assert payload["candidate_research_brief_count"] == 1
    assert payload["strategy_eligibility_brief_count"] == 1
    assert payload["risk_authority_brief_count"] == 1
    assert payload["research_queue_brief_count"] == 1
    assert payload["sma_research_observation_brief_count"] == 1
    assert payload["research_return_observation_brief_count"] == 1
    assert "Candidate Research Briefs" in lines
    assert "Strategy Eligibility Briefs" in lines
    assert "Risk Authority Briefs" in lines
    assert "Research Queue Briefs" in lines
    assert "SMA Research Observation Briefs" in lines
    assert "Research Return Observation Briefs" in lines
    assert lines.index("SMA Research Observation Briefs") < lines.index(
        "Research Return Observation Briefs"
    )
    assert lines.index("Research Return Observation Briefs") < lines.index(
        "Limitations"
    )


def test_research_return_inclusive_cli_invocations_are_byte_deterministic(
    capsys,
) -> None:
    first_text = _run_preview_cli((_COMMAND, _RESEARCH_RETURN_FLAG), capsys)
    second_text = _run_preview_cli((_COMMAND, _RESEARCH_RETURN_FLAG), capsys)
    first_json = _run_preview_cli(
        (_COMMAND, _RESEARCH_RETURN_FLAG, "--format", "json"),
        capsys,
    )
    second_json = _run_preview_cli(
        (_COMMAND, "--format", "json", _RESEARCH_RETURN_FLAG),
        capsys,
    )
    first_all_json = _run_preview_cli(
        (
            _COMMAND,
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _SMA_FLAG,
            _RESEARCH_RETURN_FLAG,
            "--format",
            "json",
        ),
        capsys,
    )
    second_all_json = _run_preview_cli(
        (
            _COMMAND,
            "--format",
            "json",
            _RESEARCH_RETURN_FLAG,
            _SMA_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _RISK_FLAG,
        ),
        capsys,
    )

    assert first_text == second_text == _expected_research_return_export().rendered_text
    assert first_json == second_json == _expected_research_return_export().json_text
    assert first_all_json == second_all_json
    assert first_all_json == _expected_research_return_export(
        include_risk_authority=True,
        include_research_queue=True,
        include_sma_research_observation=True,
    ).json_text
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert first_all_json.encode("utf-8") == second_all_json.encode("utf-8")


def test_research_return_output_pins_observation_mechanics(capsys) -> None:
    text_output = _run_preview_cli((_COMMAND, _RESEARCH_RETURN_FLAG), capsys)
    payload = json.loads(
        _run_preview_cli(
            (_COMMAND, _RESEARCH_RETURN_FLAG, "--format", "json"),
            capsys,
        )
    )
    primary_item, insufficient_item = _return_items(payload)
    primary_observation = _dict(primary_item["source_observation"])
    insufficient_observation = _dict(insufficient_item["source_observation"])
    primary_returns = tuple(
        _dict(return_point) for return_point in _list(primary_observation["returns"])
    )

    assert primary_item["mechanical_state"] == "returns_constructed"
    assert insufficient_item["mechanical_state"] == "insufficient_return_history"
    assert primary_item["positive_return_count"] == 1
    assert primary_item["negative_return_count"] == 1
    assert primary_item["zero_return_count"] == 1
    assert insufficient_item["positive_return_count"] == 0
    assert insufficient_item["negative_return_count"] == 0
    assert insufficient_item["zero_return_count"] == 0
    assert primary_observation["return_method"] == "close_to_close_simple_return"
    assert insufficient_observation["return_method"] == "close_to_close_simple_return"
    assert primary_observation["price_basis"] == "synthetic_close"
    assert insufficient_observation["price_basis"] == "synthetic_close"
    assert primary_observation["ignored_future_sample_count"] == 1
    assert insufficient_observation["ignored_future_sample_count"] == 1
    assert primary_returns == (
        {
            "start_date": "2026-01-15",
            "end_date": "2026-01-16",
            "start_close": "100.00",
            "end_close": "105.00",
            "simple_return": "0.05",
        },
        {
            "start_date": "2026-01-16",
            "end_date": "2026-01-19",
            "start_close": "105.00",
            "end_close": "94.50",
            "simple_return": "-0.1",
        },
        {
            "start_date": "2026-01-19",
            "end_date": "2026-01-20",
            "start_close": "94.50",
            "end_close": "94.50",
            "simple_return": "0",
        },
    )
    assert _list(insufficient_observation["returns"]) == []
    assert "Return Point 1" in text_output
    assert "Return Point 2" in text_output
    assert "Return Point 3" in text_output
    assert text_output.count("ignored_future_sample_count: 1") == 2
    assert (
        "- none; insufficient_return_history has no close-to-close return points."
        in text_output
    )


def test_production_cli_modules_import_no_tests_or_fixtures() -> None:
    for module in (cli_module, preview_module):
        imports = _import_references(module)
        source = _source_text(module)

        assert all(not name.startswith("tests") for name in imports)
        assert "tests.fixtures" not in imports
        assert re.search(r"(?m)^\s*(from|import)\s+tests\b", source) is None
        assert re.search(r"(?m)^\s*from\s+tests\.fixtures\b", source) is None


def test_research_return_flag_adds_no_external_or_runtime_options() -> None:
    parser = _preview_parser()
    option_text = _option_text(parser)
    option_strings = " ".join(_non_branch_option_strings(parser)).lower()

    assert _RESEARCH_RETURN_FLAG in parser._option_string_actions
    for term in _blocked_option_terms():
        assert term not in option_text
        assert term not in option_strings


def test_research_return_output_adds_no_actionable_authority_states_or_fields(
    capsys,
) -> None:
    payload = json.loads(
        _run_preview_cli(
            (
                _COMMAND,
                _RISK_FLAG,
                _RESEARCH_QUEUE_FLAG,
                _SMA_FLAG,
                _RESEARCH_RETURN_FLAG,
                "--format",
                "json",
            ),
            capsys,
        )
    )
    rendered = _run_preview_cli(
        (_COMMAND, _RISK_FLAG, _RESEARCH_QUEUE_FLAG, _SMA_FLAG, _RESEARCH_RETURN_FLAG),
        capsys,
    )

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


def _expected_research_return_export(
    *,
    include_risk_authority: bool = False,
    include_research_queue: bool = False,
    include_sma_research_observation: bool = False,
):
    return export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_observation(
            include_risk_authority=include_risk_authority,
            include_research_queue=include_research_queue,
            include_sma_research_observation=include_sma_research_observation,
        )
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


def _non_branch_option_strings(parser: argparse.ArgumentParser) -> tuple[str, ...]:
    return tuple(
        option_string
        for option_string in parser._option_string_actions
        if not option_string.startswith("--include-")
    )


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
            if key in {
                "status",
                "authority",
                "authority_state",
                "eligibility_state",
                "research_state",
                "mechanical_state",
                "position_vs_sma",
            }:
                assert isinstance(nested_value, str)
                values.append(nested_value)
            values.extend(_state_values(nested_value))
    elif isinstance(value, list):
        for nested_value in value:
            values.extend(_state_values(nested_value))
    return tuple(values)


def _return_items(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    research_return_brief = _dict(_list(payload["research_return_observation_briefs"])[0])
    section = _dict(_list(research_return_brief["sections"])[0])
    return tuple(_dict(item) for item in _list(section["items"]))


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


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
