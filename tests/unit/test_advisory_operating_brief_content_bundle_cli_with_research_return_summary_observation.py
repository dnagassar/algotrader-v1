from __future__ import annotations

import argparse
import json

from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)


_COMMAND = "advisory-operating-brief-content-bundle-preview"
_RISK_FLAG = "--include-risk-authority"
_RESEARCH_QUEUE_FLAG = "--include-research-queue"
_SMA_FLAG = "--include-sma-research-observation"
_RETURN_FLAG = "--include-research-return-observation"
_SUMMARY_FLAG = "--include-research-return-summary-observation"


def test_research_return_summary_preview_flag_is_accepted_by_parser() -> None:
    parser = _preview_parser()
    args = parser.parse_args((_SUMMARY_FLAG,))
    combined_args = parser.parse_args(
        (_RISK_FLAG, _RESEARCH_QUEUE_FLAG, _SMA_FLAG, _RETURN_FLAG, _SUMMARY_FLAG)
    )

    assert args.include_research_return_summary_observation is True
    assert args.include_research_return_observation is False
    assert args.output_format == "text"
    assert combined_args.include_research_return_summary_observation is True
    assert combined_args.include_research_return_observation is True
    assert _SUMMARY_FLAG in parser._option_string_actions


def test_include_research_return_summary_text_includes_summary_branch_only(capsys) -> None:
    expected = _expected_summary_export()

    output = _run_preview_cli((_COMMAND, _SUMMARY_FLAG), capsys)

    assert output == expected.rendered_text
    assert "Candidate Research Briefs" in output
    assert "Strategy Eligibility Briefs" in output
    assert "Research Return Summary Observation Briefs" in output
    assert "research_return_summary_observation_brief_count: 1" in output
    assert "summary_state: returns_summarized" in output
    assert "summary_state: insufficient_return_history" in output
    assert "Research Return Observation Briefs" not in output
    assert "research_return_observation_brief_count" not in output


def test_include_research_return_summary_json_round_trips(capsys) -> None:
    expected = _expected_summary_export()

    output = _run_preview_cli((_COMMAND, _SUMMARY_FLAG, "--format", "json"), capsys)
    payload = json.loads(output)

    assert output == expected.json_text
    assert payload == expected.payload
    assert payload["research_return_summary_observation_brief_count"] == 1
    assert len(payload["research_return_summary_observation_briefs"]) == 1
    assert "research_return_observation_brief_count" not in payload
    assert "research_return_observation_briefs" not in payload


def test_all_flags_include_return_and_summary_in_branch_order(capsys) -> None:
    expected = _expected_summary_export(
        include_risk_authority=True,
        include_research_queue=True,
        include_sma_research_observation=True,
        include_research_return_observation=True,
    )

    text_output = _run_preview_cli(
        (_COMMAND, _RISK_FLAG, _RESEARCH_QUEUE_FLAG, _SMA_FLAG, _RETURN_FLAG, _SUMMARY_FLAG),
        capsys,
    )
    json_output = _run_preview_cli(
        (
            _COMMAND,
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _SMA_FLAG,
            _RETURN_FLAG,
            _SUMMARY_FLAG,
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
    assert payload["research_return_observation_brief_count"] == 1
    assert payload["research_return_summary_observation_brief_count"] == 1
    assert lines.index("Research Return Observation Briefs") < lines.index(
        "Research Return Summary Observation Briefs"
    )
    assert lines.index("Research Return Summary Observation Briefs") < lines.index(
        "Limitations"
    )


def test_research_return_summary_cli_output_is_byte_deterministic(capsys) -> None:
    first = _run_preview_cli((_COMMAND, _SUMMARY_FLAG), capsys)
    second = _run_preview_cli((_COMMAND, _SUMMARY_FLAG), capsys)
    first_json = _run_preview_cli((_COMMAND, _SUMMARY_FLAG, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json", _SUMMARY_FLAG), capsys)

    assert first == second == _expected_summary_export().rendered_text
    assert first_json == second_json == _expected_summary_export().json_text
    assert first.encode("utf-8") == second.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _expected_summary_export(
    *,
    include_risk_authority: bool = False,
    include_research_queue: bool = False,
    include_sma_research_observation: bool = False,
    include_research_return_observation: bool = False,
):
    return export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation(
            include_risk_authority=include_risk_authority,
            include_research_queue=include_research_queue,
            include_sma_research_observation=include_sma_research_observation,
            include_research_return_observation=include_research_return_observation,
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
