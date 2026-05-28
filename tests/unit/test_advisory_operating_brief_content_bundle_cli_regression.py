from __future__ import annotations

import ast
import inspect
import json
import re
import sys

import pytest

import algotrader.research.advisory_operating_brief_content_bundle_cli as preview_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from tests.fixtures.advisory_operating_brief_content_bundle import (
    build_synthetic_advisory_operating_brief_content_bundle as build_phase_162_bundle,
)
from tests.fixtures.advisory_operating_brief_diagnostic_issue import (
    expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts,
)
from tests.fixtures.advisory_operating_brief_section import (
    expected_synthetic_advisory_operating_brief_section_dicts,
)
from tests.unit.test_advisory_operating_brief_content_bundle_export_regression import (
    _EXPECTED_JSON_TEXT as _EXPECTED_CONTENT_BUNDLE_JSON_TEXT,
    _EXPECTED_PAYLOAD as _EXPECTED_CONTENT_BUNDLE_PAYLOAD,
    _EXPECTED_RENDERED_TEXT as _EXPECTED_CONTENT_BUNDLE_RENDERED_TEXT,
)
from tests.unit.test_advisory_operating_brief_export_regression import (
    _EXPECTED_JSON_TEXT as _EXPECTED_LEGACY_JSON_TEXT,
)
from tests.unit.test_advisory_operating_brief_renderer_regression import (
    _EXPECTED_RENDERED_LINES as _EXPECTED_LEGACY_RENDERED_LINES,
)


def _s(*parts: str) -> str:
    return "".join(parts)


_COMMAND = "advisory-operating-brief-content-bundle-preview"
_LEGACY_COMMAND = "advisory-operating-brief-preview"
_READINESS_SUMMARY_FLAG = "--include-research-data-source-readiness-summary"
_DIAGNOSTIC_ISSUES_FLAG = "--include-diagnostic-issues"
_ADVISORY_SECTIONS_FLAG = "--include-advisory-sections"

_EXPECTED_LEGACY_RENDERED_TEXT = "\n".join(_EXPECTED_LEGACY_RENDERED_LINES)
_EXPECTED_EXPORT_PAYLOAD_KEYS = (
    "bundle_type",
    "status",
    "authority",
    "capital_authority",
    "title",
    "summary",
    "candidate_research_brief_count",
    "strategy_eligibility_brief_count",
    "candidate_research_briefs",
    "strategy_eligibility_briefs",
    "limitations",
    "non_claims",
)
_ALLOWED_SELF_IMPORTS = {
    "__future__",
    "ast",
    "inspect",
    "json",
    "pytest",
    "re",
    "sys",
    "algotrader.cli",
    "algotrader.research.advisory_operating_brief_content_bundle_cli",
    "algotrader.research.advisory_operating_brief_content_bundle_export",
    "tests.fixtures.advisory_operating_brief_content_bundle",
    "tests.fixtures.advisory_operating_brief_diagnostic_issue",
    "tests.fixtures.advisory_operating_brief_section",
    "tests.unit.test_advisory_operating_brief_content_bundle_export_regression",
    "tests.unit.test_advisory_operating_brief_export_regression",
    "tests.unit.test_advisory_operating_brief_renderer_regression",
}
_AUTHORITY_PRESENTATION_TERMS = (
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
_EXPECTED_READINESS_SUMMARY_PAYLOAD_KEYS = (
    "summary_type",
    "schema_version",
    "summary_scope",
    "summary_state",
    "required_control_count",
    "satisfied_control_count",
    "missing_control_count",
    "diagnostic_limitations",
)
_EXPECTED_DIAGNOSTIC_ISSUE_KEYS = [
    "source_branch",
    "issue_code",
    "issue_state",
    "diagnostic_message",
    "blocking_controls",
    "limitations",
]
_DIAGNOSTIC_BRANCH_FORBIDDEN_FIELD_TERMS = (
    _s("bro", "ker"),
    _s("or", "der"),
    "fill",
    _s("port", "folio"),
    "backtest",
    _s("run", "time"),
    _s("ven", "dor"),
    _s("net", "work"),
    _s("cred", "ential"),
)
_DIAGNOSTIC_BRANCH_FORBIDDEN_TEXT_TERMS = (
    _s("rank", "ing"),
    _s("scor", "ing"),
    _s("score"),
    _s("reco", "mmendation"),
    _s("app", "roval"),
    _s("app", "roved"),
)
_ADVISORY_SECTIONS_FORBIDDEN_FIELD_TERMS = (
    _s("bro", "ker"),
    _s("or", "der"),
    "fill",
    _s("port", "folio"),
    "backtest",
    _s("run", "time"),
    _s("ven", "dor"),
    _s("net", "work"),
    _s("cred", "ential"),
)
_ADVISORY_SECTIONS_FORBIDDEN_TEXT_TERMS = (
    _s("rank", "ing"),
    _s("scor", "ing"),
    _s("score"),
    _s("reco", "mmendation"),
    _s("app", "roval"),
    _s("app", "roved"),
    _s("authori", "zation"),
    _s("authori", "zed"),
)


def test_default_and_text_stdout_are_exact_phase_165_text_pins(capsys) -> None:
    expected_export = _expected_export_from_phase_162_bundle()

    default_stdout = _run_preview_cli((_COMMAND,), capsys)
    text_stdout = _run_preview_cli((_COMMAND, "--format", "text"), capsys)

    assert default_stdout == _EXPECTED_CONTENT_BUNDLE_RENDERED_TEXT
    assert text_stdout == _EXPECTED_CONTENT_BUNDLE_RENDERED_TEXT
    assert default_stdout == text_stdout
    assert text_stdout == expected_export.rendered_text
    assert text_stdout == "\n".join(_EXPECTED_CONTENT_BUNDLE_RENDERED_TEXT.splitlines())


def test_json_stdout_is_exact_phase_165_compact_export_pin(capsys) -> None:
    expected_export = _expected_export_from_phase_162_bundle()

    json_stdout = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert json_stdout == _EXPECTED_CONTENT_BUNDLE_JSON_TEXT
    assert json_stdout == expected_export.json_text
    assert json_stdout == json.dumps(
        _EXPECTED_CONTENT_BUNDLE_PAYLOAD,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json_stdout != json.dumps(_EXPECTED_CONTENT_BUNDLE_PAYLOAD, sort_keys=True)


def test_json_stdout_round_trips_exactly_to_expected_export_payload(capsys) -> None:
    json_stdout = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    payload = json.loads(json_stdout)
    expected_export = _expected_export_from_phase_162_bundle()

    assert payload == _EXPECTED_CONTENT_BUNDLE_PAYLOAD
    assert payload == expected_export.payload
    assert tuple(expected_export.payload) == _EXPECTED_EXPORT_PAYLOAD_KEYS
    assert "advisory_sections" not in payload
    assert "advisory_section_count" not in payload
    assert json.dumps(payload, sort_keys=True, separators=(",", ":")) == json_stdout


def test_repeated_text_and_json_invocations_are_byte_identical(capsys) -> None:
    first_text = _run_preview_cli((_COMMAND, "--format", "text"), capsys)
    second_text = _run_preview_cli((_COMMAND, "--format", "text"), capsys)
    first_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert first_text == second_text == _EXPECTED_CONTENT_BUNDLE_RENDERED_TEXT
    assert first_json == second_json == _EXPECTED_CONTENT_BUNDLE_JSON_TEXT
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_candidate_and_strategy_branches_keep_advisory_candidate_metadata(
    capsys,
) -> None:
    text_stdout = _run_preview_cli((_COMMAND,), capsys)
    payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))
    candidate_brief = _single_branch(payload, "candidate_research_briefs")
    candidate_section = _single_branch(candidate_brief, "sections")
    candidate_item = _single_branch(candidate_section, "items")
    strategy_brief = _single_branch(payload, "strategy_eligibility_briefs")
    strategy_section = _single_branch(strategy_brief, "sections")
    strategy_item = _single_branch(strategy_section, "items")

    assert payload["bundle_type"] == "advisory_operating_brief_content_bundle"
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["candidate_research_brief_count"] == 1
    assert payload["strategy_eligibility_brief_count"] == 1
    assert candidate_brief["status"] == "candidate_only"
    assert candidate_section["status"] == "candidate_only"
    assert candidate_item["status"] == "candidate_only"
    assert strategy_brief["status"] == "candidate_only"
    assert strategy_brief["authority"] == "advisory_only"
    assert strategy_brief["capital_authority"] is False
    assert strategy_section["status"] == "candidate_only"
    assert strategy_section["authority"] == "advisory_only"
    assert strategy_section["capital_authority"] is False
    assert strategy_item["status"] == "candidate_only"
    assert strategy_item["authority"] == "advisory_only"
    assert strategy_item["capital_authority"] is False
    assert "Candidate Research Briefs" in text_stdout
    assert "Strategy Eligibility Briefs" in text_stdout
    assert "status: candidate_only" in text_stdout
    assert "authority: advisory_only" in text_stdout
    assert "capital_authority: False" in text_stdout


def test_limitations_non_claims_and_non_authority_language_are_present(
    capsys,
) -> None:
    text_stdout = _run_preview_cli((_COMMAND,), capsys)
    payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))
    source_cautions = _source_caution_values(payload)

    assert payload["limitations"]
    assert payload["non_claims"]
    assert "Limitations" in text_stdout.splitlines()
    assert "Non-Claims" in text_stdout.splitlines()
    assert _payload_keys(payload).isdisjoint(_forbidden_actionable_field_names())
    assert _rendered_field_names(text_stdout).isdisjoint(
        _forbidden_actionable_field_names()
    )
    for path, value in _authority_presentation_payload_strings(payload):
        assert _is_caution_path(path)
        assert value in source_cautions
    for line in _authority_presentation_lines(text_stdout):
        assert line.startswith("- ")
        assert line[2:] in source_cautions


def test_command_exposes_no_file_path_source_vendor_broker_runtime_options() -> None:
    parser = _preview_parser()

    assert _positional_rows(parser) == ()
    assert _option_rows(parser) == (("output_format", ("--format",), ("text", "json")),)

    option_text = _option_text(parser)
    for term in _blocked_cli_option_terms():
        assert term not in option_text


def test_readiness_preview_flag_is_hidden_boolean_and_non_input_bearing(
    capsys,
) -> None:
    parser = _preview_parser()
    help_text = f"{build_parser().format_help()}\n{parser.format_help()}"

    assert "--include-research-data-source-readiness" not in help_text
    assert "--include-research-data-source-readiness" not in _option_text(parser)
    assert _positional_rows(parser) == ()
    assert _option_rows(parser) == (("output_format", ("--format",), ("text", "json")),)

    json_stdout = _run_preview_cli(
        (
            _COMMAND,
            "--include-research-data-source-readiness",
            "--format",
            "json",
        ),
        capsys,
    )
    payload = json.loads(json_stdout)
    readiness = _single_branch(payload, "research_data_source_readiness")

    assert payload["research_data_source_readiness_count"] == 1
    assert readiness["contract_type"] == "research_data_source_readiness"
    assert readiness["readiness_state"] == "candidate_only"
    assert readiness["source_id"] == "synthetic-broad-etf-source-candidate"
    assert readiness["missing_controls"] == [
        "terms_review_documented",
        "snapshot_provenance_defined",
        "redistribution_policy_reviewed",
        "adjustment_policy_defined",
        "fixture_policy_review_documented",
    ]

    for argv in (
        (_COMMAND, "--include-research-data-source-readiness=true"),
        (_COMMAND, "--include-research-data-source-readiness", "true"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert captured.out == ""
        assert (
            "ignored explicit argument" in captured.err
            or "unrecognized arguments:" in captured.err
        )
        assert "true" in captured.err


def test_readiness_summary_preview_flag_is_hidden_boolean_and_non_input_bearing(
    capsys,
) -> None:
    parser = _preview_parser()
    help_text = f"{build_parser().format_help()}\n{parser.format_help()}"

    assert _READINESS_SUMMARY_FLAG not in help_text
    assert _READINESS_SUMMARY_FLAG not in _option_text(parser)
    assert _positional_rows(parser) == ()
    assert _option_rows(parser) == (("output_format", ("--format",), ("text", "json")),)

    json_stdout = _run_preview_cli(
        (
            _COMMAND,
            _READINESS_SUMMARY_FLAG,
            "--format",
            "json",
        ),
        capsys,
    )
    text_stdout = _run_preview_cli(
        (
            _COMMAND,
            _READINESS_SUMMARY_FLAG,
            "--format",
            "text",
        ),
        capsys,
    )
    payload = json.loads(json_stdout)
    summary = _single_branch(payload, "research_data_source_readiness_summaries")

    assert "research_data_source_readiness" not in payload
    assert payload["research_data_source_readiness_summary_count"] == 1
    assert tuple(summary) == tuple(sorted(_EXPECTED_READINESS_SUMMARY_PAYLOAD_KEYS))
    assert summary["summary_type"] == "research_data_source_readiness_summary"
    assert summary["summary_scope"] == "advisory_metadata_only"
    assert summary["summary_state"] == "candidate_only"
    assert summary["required_control_count"] == 6
    assert summary["satisfied_control_count"] == 1
    assert summary["missing_control_count"] == 5
    assert summary["diagnostic_limitations"] == [
        "Fixture carries no observations, values, or external source content.",
        "Fixture is synthetic metadata only and not connected to real data.",
    ]
    assert _payload_keys(payload).isdisjoint(_forbidden_summary_field_names())
    assert "Research Data Source Readiness Summary Diagnostics" in text_stdout
    assert "Research Data Source Readiness Summary Diagnostic 1" in text_stdout
    assert "source_readiness:" not in text_stdout
    assert "approval_status:" not in text_stdout
    assert "trading_ready:" not in text_stdout

    for argv in (
        (_COMMAND, f"{_READINESS_SUMMARY_FLAG}=true"),
        (_COMMAND, _READINESS_SUMMARY_FLAG, "true"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert captured.out == ""
        assert (
            "ignored explicit argument" in captured.err
            or "unrecognized arguments:" in captured.err
        )
        assert "true" in captured.err


def test_diagnostic_issues_preview_flag_is_hidden_boolean_and_non_input_bearing(
    capsys,
) -> None:
    parser = _preview_parser()
    help_text = f"{build_parser().format_help()}\n{parser.format_help()}"

    assert _DIAGNOSTIC_ISSUES_FLAG not in help_text
    assert _DIAGNOSTIC_ISSUES_FLAG not in _option_text(parser)
    assert _positional_rows(parser) == ()
    assert _option_rows(parser) == (("output_format", ("--format",), ("text", "json")),)

    json_stdout = _run_preview_cli(
        (
            _COMMAND,
            _DIAGNOSTIC_ISSUES_FLAG,
            "--format",
            "json",
        ),
        capsys,
    )
    payload = json.loads(json_stdout)

    assert "research_data_source_readiness" not in payload
    assert "research_data_source_readiness_summaries" not in payload
    assert payload["diagnostic_issue_count"] == 2
    assert payload["diagnostic_issues"] == (
        expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts()
    )

    for argv in (
        (_COMMAND, f"{_DIAGNOSTIC_ISSUES_FLAG}=true"),
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "true"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert captured.out == ""
        assert (
            "ignored explicit argument" in captured.err
            or "unrecognized arguments:" in captured.err
        )
        assert "true" in captured.err


def test_diagnostic_issues_preview_text_and_json_include_issue_records(
    capsys,
) -> None:
    text_stdout = _run_preview_cli(
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "--format", "text"),
        capsys,
    )
    json_stdout = _run_preview_cli(
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "--format", "json"),
        capsys,
    )
    payload = json.loads(json_stdout)
    issues = payload["diagnostic_issues"]

    assert isinstance(issues, list)
    assert issues == expected_synthetic_advisory_operating_brief_diagnostic_issue_dicts()
    assert [list(issue) for issue in issues] == [
        sorted(_EXPECTED_DIAGNOSTIC_ISSUE_KEYS),
        sorted(_EXPECTED_DIAGNOSTIC_ISSUE_KEYS),
    ]
    assert [issue["source_branch"] for issue in issues] == [
        "research_data_source_readiness",
        "research_data_source_readiness_summary",
    ]
    assert [issue["issue_code"] for issue in issues] == [
        "missing_diagnostic_controls",
        "missing_diagnostic_controls",
    ]
    assert [issue["issue_state"] for issue in issues] == [
        "candidate_only",
        "candidate_only",
    ]
    assert [issue["diagnostic_message"] for issue in issues] == [
        "Readiness branch reports missing diagnostic controls.",
        "Readiness summary branch reports missing diagnostic controls.",
    ]
    assert issues[0]["blocking_controls"] == [
        "terms_review_documented",
        "snapshot_provenance_defined",
        "redistribution_policy_reviewed",
        "adjustment_policy_defined",
        "fixture_policy_review_documented",
    ]
    assert issues[1]["blocking_controls"] == issues[0]["blocking_controls"]
    assert issues[0]["limitations"] == [
        "Fixture is synthetic metadata only and not connected to real data.",
        "Fixture carries no observations, values, or external source content.",
    ]
    assert issues[1]["limitations"] == [
        "Fixture carries no observations, values, or external source content.",
        "Fixture is synthetic metadata only and not connected to real data.",
    ]

    for expected_line in (
        "Diagnostic Issues",
        "Diagnostic Issue 1",
        "source_branch: research_data_source_readiness",
        "issue_code: missing_diagnostic_controls",
        "issue_state: candidate_only",
        "diagnostic_message: Readiness branch reports missing diagnostic controls.",
        "blocking_controls:",
        "limitations:",
        "Diagnostic Issue 2",
        "source_branch: research_data_source_readiness_summary",
        (
            "diagnostic_message: Readiness summary branch reports missing "
            "diagnostic controls."
        ),
    ):
        assert expected_line in text_stdout


def test_diagnostic_issues_preview_repeated_text_and_json_are_byte_identical(
    capsys,
) -> None:
    first_text = _run_preview_cli(
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "--format", "text"),
        capsys,
    )
    second_text = _run_preview_cli(
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "--format", "text"),
        capsys,
    )
    first_json = _run_preview_cli(
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "--format", "json"),
        capsys,
    )
    second_json = _run_preview_cli(
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "--format", "json"),
        capsys,
    )

    assert first_text == second_text
    assert first_json == second_json
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert json.dumps(
        json.loads(first_json),
        sort_keys=True,
        separators=(",", ":"),
    ) == first_json


def test_diagnostic_issues_preview_branch_adds_no_operating_fields_or_terms(
    capsys,
) -> None:
    json_stdout = _run_preview_cli(
        (_COMMAND, _DIAGNOSTIC_ISSUES_FLAG, "--format", "json"),
        capsys,
    )
    payload = json.loads(json_stdout)
    issues = payload["diagnostic_issues"]
    issue_text = json.dumps(issues, sort_keys=True, separators=(",", ":")).lower()

    assert _matching_field_terms(
        _payload_keys(issues),
        _DIAGNOSTIC_BRANCH_FORBIDDEN_FIELD_TERMS,
    ) == []
    assert _matching_terms(
        issue_text,
        _DIAGNOSTIC_BRANCH_FORBIDDEN_TEXT_TERMS,
    ) == []


def test_advisory_sections_preview_flag_is_hidden_boolean_and_non_input_bearing(
    capsys,
) -> None:
    parser = _preview_parser()
    help_text = f"{build_parser().format_help()}\n{parser.format_help()}"

    assert _ADVISORY_SECTIONS_FLAG not in help_text
    assert _ADVISORY_SECTIONS_FLAG not in _option_text(parser)
    assert _positional_rows(parser) == ()
    assert _option_rows(parser) == (("output_format", ("--format",), ("text", "json")),)

    json_stdout = _run_preview_cli(
        (
            _COMMAND,
            _ADVISORY_SECTIONS_FLAG,
            "--format",
            "json",
        ),
        capsys,
    )
    payload = json.loads(json_stdout)

    assert "research_data_source_readiness" not in payload
    assert "research_data_source_readiness_summaries" not in payload
    assert "diagnostic_issues" not in payload
    assert payload["advisory_section_count"] == len(
        expected_synthetic_advisory_operating_brief_section_dicts()
    )
    assert payload["advisory_sections"] == (
        expected_synthetic_advisory_operating_brief_section_dicts()
    )

    for argv in (
        (_COMMAND, f"{_ADVISORY_SECTIONS_FLAG}=true"),
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "true"),
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert captured.out == ""
        assert (
            "ignored explicit argument" in captured.err
            or "unrecognized arguments:" in captured.err
        )
        assert "true" in captured.err


def test_advisory_sections_preview_text_and_json_include_section_records(
    capsys,
) -> None:
    text_stdout = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "text"),
        capsys,
    )
    json_stdout = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "json"),
        capsys,
    )
    payload = json.loads(json_stdout)
    sections = payload["advisory_sections"]
    expected_sections = expected_synthetic_advisory_operating_brief_section_dicts()

    assert isinstance(sections, list)
    assert sections == expected_sections
    assert [section["section_key"] for section in sections] == [
        section["section_key"] for section in expected_sections
    ]
    assert [list(section) for section in sections] == [
        sorted(
            [
                "section_key",
                "section_title",
                "section_state",
                "source_branches",
                "item_count",
                "diagnostic_messages",
                "limitations",
            ]
        )
    ] * len(expected_sections)
    assert sections[-1]["diagnostic_messages"] == [
        "Readiness branch reports missing diagnostic controls.",
        "Readiness summary branch reports missing diagnostic controls.",
    ]
    assert json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ) == json_stdout

    for expected_line in (
        "advisory_section_count: 5",
        "Advisory Sections",
        "Advisory Section 1",
        "section_key: candidate_research_briefs",
        "section_title: Candidate research brief metadata",
        "section_state: candidate_only",
        "source_branches:",
        "- candidate_research_briefs",
        "item_count: 1",
        "diagnostic_messages:",
        "limitations:",
        "Advisory Section 5",
        "section_key: diagnostic_issues",
        "section_title: Diagnostic issue metadata",
        "- Readiness branch reports missing diagnostic controls.",
        "- Readiness summary branch reports missing diagnostic controls.",
        "- diagnostic messages are copied from existing issue records",
    ):
        assert expected_line in text_stdout


def test_advisory_sections_preview_repeated_text_and_json_are_byte_identical(
    capsys,
) -> None:
    first_text = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "text"),
        capsys,
    )
    second_text = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "text"),
        capsys,
    )
    first_json = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "json"),
        capsys,
    )
    second_json = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "json"),
        capsys,
    )

    assert first_text == second_text
    assert first_json == second_json
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")
    assert json.dumps(
        json.loads(first_json),
        sort_keys=True,
        separators=(",", ":"),
    ) == first_json


def test_advisory_sections_preview_branch_adds_no_operating_fields_or_terms(
    capsys,
) -> None:
    text_stdout = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "text"),
        capsys,
    )
    json_stdout = _run_preview_cli(
        (_COMMAND, _ADVISORY_SECTIONS_FLAG, "--format", "json"),
        capsys,
    )
    payload = json.loads(json_stdout)
    sections = payload["advisory_sections"]
    section_text = json.dumps(
        sections,
        sort_keys=True,
        separators=(",", ":"),
    ).lower()
    rendered_section_text = "\n".join(_advisory_sections_text_block(text_stdout)).lower()

    assert _matching_field_terms(
        _payload_keys(sections),
        _ADVISORY_SECTIONS_FORBIDDEN_FIELD_TERMS,
    ) == []
    assert _matching_terms(
        section_text,
        _ADVISORY_SECTIONS_FORBIDDEN_TEXT_TERMS,
    ) == []
    assert _matching_terms(
        rendered_section_text,
        _ADVISORY_SECTIONS_FORBIDDEN_TEXT_TERMS,
    ) == []
    assert _matching_terms(
        rendered_section_text,
        _ADVISORY_SECTIONS_FORBIDDEN_FIELD_TERMS,
    ) == []


def test_preview_module_is_synthetic_only_and_has_no_external_chains() -> None:
    imports = _import_references(preview_module)
    call_names = _call_names(preview_module)
    source = _source_text(preview_module).lower()

    assert all(not module.startswith("tests") for module in imports)
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_production_call_names())
    for term in _provider_or_sdk_terms():
        assert term not in source
    for term in _sensitive_terms():
        assert term not in source
    for term in _forbidden_exact_literals():
        assert term not in _string_literals(preview_module)


def test_existing_advisory_operating_brief_preview_behavior_is_unchanged(
    capsys,
) -> None:
    text_stdout = _run_preview_cli((_LEGACY_COMMAND,), capsys)
    json_stdout = _run_preview_cli((_LEGACY_COMMAND, "--format", "json"), capsys)

    assert text_stdout == _EXPECTED_LEGACY_RENDERED_TEXT
    assert json_stdout == _EXPECTED_LEGACY_JSON_TEXT
    assert "Advisory Operating Brief Content Bundle" not in text_stdout
    assert "advisory_operating_brief_content_bundle" not in json_stdout


def test_regression_guard_imports_and_calls_no_forbidden_paths() -> None:
    imports = _import_references(sys.modules[__name__])
    call_names = _call_names(sys.modules[__name__])

    assert imports == _ALLOWED_SELF_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_self_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_self_call_names())


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _expected_export_from_phase_162_bundle():
    return export_advisory_operating_brief_content_bundle(build_phase_162_bundle())


def _preview_parser():
    return _subparser_choices(build_parser())[_COMMAND]


def _subparser_choices(parser) -> dict[str, object]:
    for parser_entry in parser._actions:
        choices = getattr(parser_entry, "choices", None)
        if isinstance(choices, dict) and _COMMAND in choices:
            return choices
    raise AssertionError("parser has no content bundle preview command choices")


def _option_rows(parser) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
    rows = []
    for parser_entry in parser._actions:
        if parser_entry.dest == "help" or not parser_entry.option_strings:
            continue
        rows.append(
            (
                parser_entry.dest,
                tuple(parser_entry.option_strings),
                tuple(parser_entry.choices or ()),
            )
        )
    return tuple(rows)


def _positional_rows(parser) -> tuple[str, ...]:
    return tuple(
        parser_entry.dest
        for parser_entry in parser._actions
        if parser_entry.dest != "help" and not parser_entry.option_strings
    )


def _option_text(parser) -> str:
    values: list[str] = []
    for parser_entry in parser._actions:
        values.extend(parser_entry.option_strings)
        values.append(str(parser_entry.dest))
        values.append(str(parser_entry.help))
        values.extend(str(choice) for choice in (parser_entry.choices or ()))
    return " ".join(values).lower()


def _single_branch(payload: dict[str, object], key: str) -> dict[str, object]:
    branch = payload[key]
    assert isinstance(branch, list)
    assert len(branch) == 1
    item = branch[0]
    assert isinstance(item, dict)
    return item


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


def _matching_field_terms(
    field_names: set[str],
    forbidden_terms: tuple[str, ...],
) -> list[str]:
    matches: list[str] = []
    for field_name in sorted(field_names):
        for term in forbidden_terms:
            if term in field_name.lower():
                matches.append(field_name)
                break

    return matches


def _matching_terms(text: str, forbidden_terms: tuple[str, ...]) -> list[str]:
    return [term for term in forbidden_terms if term in text]


def _rendered_field_names(text: str) -> set[str]:
    field_names: set[str] = set()
    for line in text.splitlines():
        if line.startswith("- ") or ":" not in line:
            continue
        field_names.add(line.split(":", maxsplit=1)[0])

    return field_names


def _advisory_sections_text_block(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    start = lines.index("Advisory Sections")
    end = lines.index("Limitations", start)

    return tuple(lines[start:end])


def _authority_presentation_lines(text: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in text.splitlines()
        if any(
            re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", line.lower())
            for term in _AUTHORITY_PRESENTATION_TERMS
        )
    )


def _authority_presentation_payload_strings(
    value: object,
    path: str = "",
) -> tuple[tuple[str, str], ...]:
    matches: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}" if path else key
            matches.extend(_authority_presentation_payload_strings(nested_value, nested_path))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            matches.extend(
                _authority_presentation_payload_strings(
                    nested_value,
                    f"{path}[{index}]",
                )
            )
    elif isinstance(value, str) and _contains_authority_presentation_term(value):
        matches.append((path, value))

    return tuple(matches)


def _contains_authority_presentation_term(value: str) -> bool:
    lowered = value.lower()
    return any(
        re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", lowered)
        for term in _AUTHORITY_PRESENTATION_TERMS
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


def _is_caution_path(path: str) -> bool:
    return any(
        caution_field in path
        for caution_field in (
            "blockers[",
            "limitations[",
            "non_claims[",
            "required_next_steps[",
        )
    )


def _blocked_cli_option_terms() -> tuple[str, ...]:
    return (
        _s("fi", "le"),
        _s("pa", "th"),
        "local",
        _s("snap", "shot"),
        _s("sour", "ce"),
        _s("ven", "dor"),
        _s("bro", "ker"),
        _s("net", "work"),
        _s("cred", "ential"),
        _s("run", "time"),
        _s("market"),
        _s("da", "ta"),
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
        "algotrader.llm",
        "algotrader.llms",
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


def _blocked_self_import_prefixes() -> tuple[str, ...]:
    return _blocked_import_prefixes() + (
        "click",
        "typer",
        "tensorflow",
        "torch",
        "xgboost",
    )


def _blocked_production_call_names() -> set[str]:
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


def _blocked_self_call_names() -> set[str]:
    return _blocked_production_call_names() - {
        "main",
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


def _forbidden_summary_field_names() -> set[str]:
    return _forbidden_actionable_field_names() | {
        "approval_status",
        "authorization_status",
        "raw_payload",
        "source_authorized",
        "source_payload",
        "source_readiness",
        "wrapper",
    }
