from __future__ import annotations

import argparse
import json

from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict,
)
from tests.fixtures.research_data_source_readiness import (
    expected_synthetic_research_data_source_readiness,
    expected_synthetic_research_data_source_readiness_dict,
)


_COMMAND = "advisory-operating-brief-content-bundle-preview"
_RISK_FLAG = "--include-risk-authority"
_RESEARCH_QUEUE_FLAG = "--include-research-queue"
_SMA_FLAG = "--include-sma-research-observation"
_SMA_SUMMARY_FLAG = "--include-sma-research-summary-observation"
_RETURN_FLAG = "--include-research-return-observation"
_RETURN_SUMMARY_FLAG = "--include-research-return-summary-observation"
_READINESS_FLAG = "--include-research-data-source-readiness"
_FORBIDDEN_BRANCH_FIELD_TERMS = (
    "broker",
    "order",
    "fill",
    "portfolio",
    "backtest",
    "runtime",
    "vendor",
    "network",
    "credential",
)


def _s(*parts: str) -> str:
    return "".join(parts)


def test_readiness_preview_flag_is_accepted_by_parser() -> None:
    parser = _preview_parser()
    default_args = parser.parse_args(())
    args = parser.parse_args((_READINESS_FLAG,))
    json_args = parser.parse_args((_READINESS_FLAG, "--format", "json"))
    action = parser._option_string_actions[_READINESS_FLAG]

    assert default_args.include_research_data_source_readiness is False
    assert args.include_research_data_source_readiness is True
    assert args.output_format == "text"
    assert json_args.include_research_data_source_readiness is True
    assert json_args.output_format == "json"
    assert action.nargs == 0
    assert action.const is True
    assert action.default is False
    assert action.choices is None
    assert action.metavar is None


def test_readiness_preview_builder_matches_existing_fixture_branch() -> None:
    bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness()
    )
    expected = (
        expected_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness_dict()
    )
    readiness = expected_synthetic_research_data_source_readiness()

    assert bundle.to_dict() == expected
    assert bundle.research_data_source_readiness == (readiness,)
    assert bundle.research_data_source_readiness[0].missing_controls == (
        readiness.missing_controls
    )


def test_existing_default_text_and_json_output_remain_unchanged(capsys) -> None:
    expected = export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle()
    )

    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert text_output == expected.rendered_text
    assert json_output == expected.json_text
    assert "Research Data Source Readiness Diagnostics" not in text_output
    assert "research_data_source_readiness" not in json_output


def test_include_readiness_text_includes_diagnostic_and_missing_controls(
    capsys,
) -> None:
    expected = _expected_readiness_export()
    readiness = expected_synthetic_research_data_source_readiness()

    output = _run_preview_cli((_COMMAND, _READINESS_FLAG), capsys)

    assert output == expected.rendered_text
    assert "Research Data Source Readiness Diagnostics" in output
    assert "research_data_source_readiness_count: 1" in output
    assert "readiness_state: candidate_only" in output
    assert "missing_controls:" in output
    for missing_control in readiness.missing_controls:
        assert f"- {missing_control}" in output
    assert "metadata_ready" not in output
    assert "- no source approval" in output


def test_include_readiness_json_includes_diagnostic_and_round_trips(capsys) -> None:
    expected = _expected_readiness_export()
    readiness = expected_synthetic_research_data_source_readiness()
    readiness_payload = expected_synthetic_research_data_source_readiness_dict()

    output = _run_preview_cli((_COMMAND, _READINESS_FLAG, "--format", "json"), capsys)
    payload = json.loads(output)
    branch = payload["research_data_source_readiness"][0]

    assert output == expected.json_text
    assert output == json.dumps(
        expected.payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert payload == expected.payload
    assert branch == readiness_payload
    assert branch["missing_controls"] == list(readiness.missing_controls)
    assert branch["missing_controls"]
    assert "\n" not in output
    assert '": ' not in output


def test_readiness_cli_outputs_are_byte_deterministic(capsys) -> None:
    first_text = _run_preview_cli((_COMMAND, _READINESS_FLAG), capsys)
    second_text = _run_preview_cli((_COMMAND, _READINESS_FLAG), capsys)
    first_json = _run_preview_cli(
        (_COMMAND, _READINESS_FLAG, "--format", "json"),
        capsys,
    )
    second_json = _run_preview_cli(
        (_COMMAND, "--format", "json", _READINESS_FLAG),
        capsys,
    )

    assert first_text == second_text == _expected_readiness_export().rendered_text
    assert first_json == second_json == _expected_readiness_export().json_text
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_all_flags_keep_readiness_after_existing_branches(capsys) -> None:
    expected = _expected_readiness_export(
        include_risk_authority=True,
        include_research_queue=True,
        include_sma_research_observation=True,
        include_sma_research_summary_observation=True,
        include_research_return_observation=True,
        include_research_return_summary_observation=True,
    )

    text_output = _run_preview_cli(
        (
            _COMMAND,
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _SMA_FLAG,
            _SMA_SUMMARY_FLAG,
            _RETURN_FLAG,
            _RETURN_SUMMARY_FLAG,
            _READINESS_FLAG,
        ),
        capsys,
    )
    json_output = _run_preview_cli(
        (
            _COMMAND,
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _SMA_FLAG,
            _SMA_SUMMARY_FLAG,
            _RETURN_FLAG,
            _RETURN_SUMMARY_FLAG,
            _READINESS_FLAG,
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
    assert lines.index("Research Return Summary Observation Briefs") < lines.index(
        "Research Data Source Readiness Diagnostics"
    )
    assert lines.index("Research Data Source Readiness Diagnostics") < lines.index(
        "Limitations"
    )


def test_cli_exposes_no_real_input_or_external_visible_options() -> None:
    parser = _preview_parser()

    assert _positional_rows(parser) == ()
    assert _option_rows(parser) == (("output_format", ("--format",), ("text", "json")),)

    option_text = _option_text(parser)
    for term in _blocked_visible_option_terms():
        assert term not in option_text


def test_readiness_branch_adds_no_runtime_trading_or_vendor_fields(capsys) -> None:
    payload = json.loads(
        _run_preview_cli(
            (_COMMAND, _READINESS_FLAG, "--format", "json"),
            capsys,
        )
    )
    readiness_payloads = payload["research_data_source_readiness"]
    field_names = _serialized_keys(readiness_payloads)

    assert _matching_field_terms(
        field_names,
        _FORBIDDEN_BRANCH_FIELD_TERMS,
    ) == []


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _expected_readiness_export(
    *,
    include_risk_authority: bool = False,
    include_research_queue: bool = False,
    include_sma_research_observation: bool = False,
    include_sma_research_summary_observation: bool = False,
    include_research_return_observation: bool = False,
    include_research_return_summary_observation: bool = False,
):
    return export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_data_source_readiness(
            include_risk_authority=include_risk_authority,
            include_research_queue=include_research_queue,
            include_sma_research_observation=include_sma_research_observation,
            include_sma_research_summary_observation=(
                include_sma_research_summary_observation
            ),
            include_research_return_observation=include_research_return_observation,
            include_research_return_summary_observation=(
                include_research_return_summary_observation
            ),
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


def _blocked_visible_option_terms() -> tuple[str, ...]:
    return (
        _s("fi", "le"),
        _s("pa", "th"),
        _s("sour", "ce"),
        _s("ven", "dor"),
        _s("bro", "ker"),
        _s("net", "work"),
        _s("cre", "dential"),
        "endpoint",
        "feed",
        "live",
        "paper",
    )


def _serialized_keys(value: object) -> set[str]:
    if type(value) is dict:
        return {
            key
            for dict_key, item in value.items()
            for key in {dict_key, *_serialized_keys(item)}
        }
    if type(value) is list:
        return {
            key
            for item in value
            for key in _serialized_keys(item)
        }

    return set()


def _matching_field_terms(
    field_names: set[str],
    forbidden_terms: tuple[str, ...],
) -> list[str]:
    return sorted(
        {
            term
            for field_name in field_names
            for term in forbidden_terms
            if term in field_name.lower()
        }
    )
