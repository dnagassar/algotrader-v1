from __future__ import annotations

import argparse
import json

from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_summary_observation,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)


_COMMAND = "advisory-operating-brief-content-bundle-preview"
_RISK_FLAG = "--include-risk-authority"
_RESEARCH_QUEUE_FLAG = "--include-research-queue"
_SMA_FLAG = "--include-sma-research-observation"
_SMA_SUMMARY_FLAG = "--include-sma-research-summary-observation"
_RETURN_FLAG = "--include-research-return-observation"
_RETURN_SUMMARY_FLAG = "--include-research-return-summary-observation"


def test_sma_research_summary_preview_flag_is_accepted_by_parser() -> None:
    parser = _preview_parser()
    args = parser.parse_args((_SMA_SUMMARY_FLAG,))
    combined_args = parser.parse_args(
        (
            _RISK_FLAG,
            _RESEARCH_QUEUE_FLAG,
            _SMA_FLAG,
            _SMA_SUMMARY_FLAG,
            _RETURN_FLAG,
            _RETURN_SUMMARY_FLAG,
        )
    )

    assert args.include_sma_research_summary_observation is True
    assert args.include_sma_research_observation is False
    assert args.output_format == "text"
    assert combined_args.include_sma_research_summary_observation is True
    assert combined_args.include_sma_research_observation is True
    assert _SMA_SUMMARY_FLAG in parser._option_string_actions


def test_include_sma_research_summary_text_includes_summary_branch_only(
    capsys,
) -> None:
    expected = _expected_summary_export()

    output = _run_preview_cli((_COMMAND, _SMA_SUMMARY_FLAG), capsys)

    assert output == expected.rendered_text
    assert "Candidate Research Briefs" in output
    assert "Strategy Eligibility Briefs" in output
    assert "SMA Research Summary Observations" in output
    assert "sma_research_summary_observation_count: 1" in output
    assert "SMA Research Observation Briefs" not in output
    assert "sma_research_observation_brief_count" not in output
    assert "summary_state: observations_summarized" in output
    assert "total_observation_count: 2" in output
    assert "above_sma_count: 1" in output
    assert "insufficient_history_count: 1" in output
    assert "below_sma_count: 0" in output
    assert "equal_sma_count: 0" in output


def test_include_sma_research_summary_json_round_trips(capsys) -> None:
    expected = _expected_summary_export()

    output = _run_preview_cli(
        (_COMMAND, _SMA_SUMMARY_FLAG, "--format", "json"),
        capsys,
    )
    payload = json.loads(output)
    summary = _summary_observation(payload)

    assert output == expected.json_text
    assert payload == expected.payload
    assert payload["sma_research_summary_observation_count"] == 1
    assert len(payload["sma_research_summary_observations"]) == 1
    assert "sma_research_observation_brief_count" not in payload
    assert "sma_research_observation_briefs" not in payload
    assert summary["observation_type"] == "sma_research_summary_observation"
    assert summary["research_scope"] == "research_only"
    assert summary["summary_state"] == "observations_summarized"
    assert summary["total_observation_count"] == 2
    assert summary["above_sma_count"] == 1
    assert summary["insufficient_history_count"] == 1
    assert summary["below_sma_count"] == 0
    assert summary["equal_sma_count"] == 0
    assert len(_list(summary["source_observations"])) == 2


def test_include_sma_observation_and_summary_uses_same_synthetic_sources(
    capsys,
) -> None:
    expected = _expected_summary_export(include_sma_research_observation=True)

    text_output = _run_preview_cli(
        (_COMMAND, _SMA_FLAG, _SMA_SUMMARY_FLAG),
        capsys,
    )
    json_output = _run_preview_cli(
        (_COMMAND, _SMA_FLAG, _SMA_SUMMARY_FLAG, "--format", "json"),
        capsys,
    )
    payload = json.loads(json_output)
    summary_sources = _list(_summary_observation(payload)["source_observations"])
    sma_sources = [
        _dict(item)["source_observation"]
        for item in _sma_observation_items(payload)
    ]
    lines = tuple(text_output.splitlines())

    assert text_output == expected.rendered_text
    assert json_output == expected.json_text
    assert payload == expected.payload
    assert payload["sma_research_observation_brief_count"] == 1
    assert payload["sma_research_summary_observation_count"] == 1
    assert summary_sources == sma_sources
    assert lines.index("SMA Research Observation Briefs") < lines.index(
        "SMA Research Summary Observations"
    )
    assert lines.index("SMA Research Summary Observations") < lines.index(
        "Limitations"
    )


def test_all_flags_include_sma_summary_in_branch_order(capsys) -> None:
    expected = _expected_summary_export(
        include_risk_authority=True,
        include_research_queue=True,
        include_sma_research_observation=True,
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
    assert payload["sma_research_summary_observation_count"] == 1
    assert lines.index("SMA Research Observation Briefs") < lines.index(
        "SMA Research Summary Observations"
    )
    assert lines.index("SMA Research Summary Observations") < lines.index(
        "Research Return Observation Briefs"
    )
    assert _index(expected.payload, "sma_research_summary_observations") < _index(
        expected.payload,
        "research_return_observation_briefs",
    )


def test_sma_summary_cli_output_is_byte_deterministic(capsys) -> None:
    first = _run_preview_cli((_COMMAND, _SMA_SUMMARY_FLAG), capsys)
    second = _run_preview_cli((_COMMAND, _SMA_SUMMARY_FLAG), capsys)
    first_json = _run_preview_cli(
        (_COMMAND, _SMA_SUMMARY_FLAG, "--format", "json"),
        capsys,
    )
    second_json = _run_preview_cli(
        (_COMMAND, "--format", "json", _SMA_SUMMARY_FLAG),
        capsys,
    )

    assert first == second == _expected_summary_export().rendered_text
    assert first_json == second_json == _expected_summary_export().json_text
    assert first.encode("utf-8") == second.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_sma_summary_output_adds_no_actionable_authority_states(capsys) -> None:
    payload = json.loads(
        _run_preview_cli(
            (_COMMAND, _SMA_SUMMARY_FLAG, "--format", "json"),
            capsys,
        )
    )
    rendered = _run_preview_cli((_COMMAND, _SMA_SUMMARY_FLAG), capsys)

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


def _expected_summary_export(
    *,
    include_risk_authority: bool = False,
    include_research_queue: bool = False,
    include_sma_research_observation: bool = False,
    include_research_return_observation: bool = False,
    include_research_return_summary_observation: bool = False,
):
    return export_advisory_operating_brief_content_bundle(
        build_synthetic_advisory_operating_brief_content_bundle_with_sma_research_summary_observation(
            include_risk_authority=include_risk_authority,
            include_research_queue=include_research_queue,
            include_sma_research_observation=include_sma_research_observation,
        )
        if not (
            include_research_return_observation
            or include_research_return_summary_observation
        )
        else build_synthetic_advisory_operating_brief_content_bundle_with_research_return_summary_observation(
            include_risk_authority=include_risk_authority,
            include_research_queue=include_research_queue,
            include_sma_research_observation=include_sma_research_observation,
            include_sma_research_summary_observation=True,
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


def _summary_observation(payload: dict[str, object]) -> dict[str, object]:
    return _dict(_list(payload["sma_research_summary_observations"])[0])


def _sma_observation_items(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    sma_brief = _dict(_list(payload["sma_research_observation_briefs"])[0])
    section = _dict(_list(sma_brief["sections"])[0])
    return tuple(_dict(item) for item in _list(section["items"]))


def _dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _list(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def _index(payload: dict[str, object], key: str) -> int:
    return tuple(payload).index(key)


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set()
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
                "summary_state",
                "position_vs_sma",
            }:
                assert isinstance(nested_value, str)
                values.append(nested_value)
            values.extend(_state_values(nested_value))
    elif isinstance(value, list):
        for nested_value in value:
            values.extend(_state_values(nested_value))
    return tuple(values)


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
        "allocation",
        "allocations",
        "allocation_authority",
        "order",
        "orders",
        "order_authority",
        "portfolio",
        "portfolios",
        "trading_authority",
        "trading_ready",
    }
