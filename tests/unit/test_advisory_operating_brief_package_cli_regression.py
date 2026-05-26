from __future__ import annotations

import argparse
import ast
import inspect
import json
import re
import sys

import algotrader.cli as cli_module
import algotrader.research.advisory_operating_brief_package_cli as preview_module
import algotrader.research.advisory_operating_brief_package_synthetic as synthetic_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_content_bundle_cli import (
    build_synthetic_advisory_operating_brief_content_bundle,
    build_synthetic_advisory_operating_brief_content_bundle_with_research_queue,
    build_synthetic_advisory_operating_brief_content_bundle_with_risk,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.advisory_operating_brief_package_export import (
    export_advisory_operating_brief_package,
)
from tests.fixtures.advisory_operating_brief_package import (
    build_synthetic_advisory_operating_brief_package as build_fixture_package,
)
from tests.fixtures.sma_return_research_pipeline_observation import (
    expected_synthetic_sma_return_research_pipeline_observation_dict,
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
    "sma_research_observation_briefs",
    "sma_research_summary_observations",
    "research_return_observation_briefs",
    "research_return_summary_observation_briefs",
)
_EXPECTED_EXPORT = export_advisory_operating_brief_package(
    build_fixture_package()
)
_EXPECTED_PAYLOAD = _EXPECTED_EXPORT.payload
_EXPECTED_SMA_RETURN_PIPELINE_PAYLOAD = (
    expected_synthetic_sma_return_research_pipeline_observation_dict()
)
_EXPECTED_TEXT = _EXPECTED_EXPORT.rendered_text
_EXPECTED_JSON = _EXPECTED_EXPORT.json_text
_ALLOWED_SELF_IMPORTS = {
    "__future__",
    "argparse",
    "ast",
    "inspect",
    "json",
    "re",
    "sys",
    "algotrader.cli",
    "algotrader.research.advisory_operating_brief_content_bundle_cli",
    "algotrader.research.advisory_operating_brief_content_bundle_export",
    "algotrader.research.advisory_operating_brief_package_cli",
    "algotrader.research.advisory_operating_brief_package_export",
    "algotrader.research.advisory_operating_brief_package_synthetic",
    "tests.fixtures.advisory_operating_brief_package",
    "tests.fixtures.sma_return_research_pipeline_observation",
}
_FORBIDDEN_SERIALIZED_FIELD_NAMES = {
    "broker",
    "account",
    "order",
    "fill",
    "position",
    "portfolio",
    "cash",
    "equity",
    "pnl",
    "benchmark",
    "backtest",
    "allocation",
    "signal",
    "execution",
    "live",
    "paper",
    "readiness",
    "approval",
}


def _s(*parts: str) -> str:
    return "".join(parts)


def test_default_and_text_stdout_are_exact_package_export_pins(capsys) -> None:
    default_stdout = _run_preview_cli((_COMMAND,), capsys)
    text_stdout = _run_preview_cli((_COMMAND, "--format", "text"), capsys)

    assert default_stdout == text_stdout
    assert default_stdout == _EXPECTED_TEXT
    assert text_stdout == _EXPECTED_EXPORT.rendered_text
    assert text_stdout == export_advisory_operating_brief_package(
        build_fixture_package()
    ).rendered_text


def test_json_stdout_is_exact_package_export_pin_and_round_trips(capsys) -> None:
    json_stdout = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    payload = json.loads(json_stdout)

    assert json_stdout == _EXPECTED_JSON
    assert json_stdout == _EXPECTED_EXPORT.json_text
    assert json_stdout == json.dumps(
        _EXPECTED_PAYLOAD,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert json_stdout != json.dumps(_EXPECTED_PAYLOAD, sort_keys=True)
    assert payload == _EXPECTED_PAYLOAD
    assert payload == build_fixture_package().to_dict()
    assert payload == (
        preview_module.build_synthetic_advisory_operating_brief_package().to_dict()
    )
    assert _dict(_dict(payload["content_bundle_export"])["payload"]) == _dict(
        payload["content_bundle"]
    )


def test_json_stdout_preserves_sma_return_pipeline_payload(capsys) -> None:
    first_json_stdout = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    second_json_stdout = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    payload = json.loads(first_json_stdout)
    package = build_fixture_package()
    pipeline = package.sma_return_research_pipeline_observation

    assert pipeline is not None
    assert first_json_stdout == second_json_stdout == _EXPECTED_JSON
    assert first_json_stdout.encode("utf-8") == second_json_stdout.encode("utf-8")
    assert payload == package.to_dict() == _EXPECTED_PAYLOAD
    assert "sma_return_research_pipeline_observation" in payload

    pipeline_payload = _dict(payload["sma_return_research_pipeline_observation"])
    policy_payload = _dict(pipeline_payload["return_construction_policy_observation"])

    assert pipeline_payload == _EXPECTED_SMA_RETURN_PIPELINE_PAYLOAD
    assert pipeline_payload == pipeline.to_dict()
    assert pipeline_payload == _dict(
        _EXPECTED_PAYLOAD["sma_return_research_pipeline_observation"]
    )
    assert policy_payload == (
        pipeline.return_construction_policy_observation.to_dict()
    )
    assert policy_payload == _dict(
        _EXPECTED_SMA_RETURN_PIPELINE_PAYLOAD[
            "return_construction_policy_observation"
        ]
    )
    assert _key_count(pipeline_payload, "return_construction_policy_observation") == 1
    assert _key_count(payload, "return_construction_policy_observation") == 1


def test_repeated_preview_invocations_are_byte_for_byte_identical(capsys) -> None:
    first_default = _run_preview_cli((_COMMAND,), capsys)
    second_default = _run_preview_cli((_COMMAND,), capsys)
    first_text = _run_preview_cli((_COMMAND, "--format", "text"), capsys)
    second_text = _run_preview_cli((_COMMAND, "--format", "text"), capsys)
    first_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert first_default == second_default == _EXPECTED_TEXT
    assert first_text == second_text == _EXPECTED_TEXT
    assert first_json == second_json == _EXPECTED_JSON
    assert first_default.encode("utf-8") == second_default.encode("utf-8")
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_package_output_contains_metadata_branches_and_cautions(capsys) -> None:
    text_stdout = _run_preview_cli((_COMMAND,), capsys)
    payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))
    content_bundle = _dict(payload["content_bundle"])
    sma_summary = _dict(_list(content_bundle["sma_research_summary_observations"])[0])

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
        "Candidate Research Briefs",
        "Strategy Eligibility Briefs",
        "Risk Authority Briefs",
        "Research Queue Briefs",
        "SMA Research Observation Briefs",
        "SMA Research Summary Observations",
        "Research Return Observation Briefs",
        "Research Return Summary Observation Briefs",
        "candidate_research_brief_count: 1",
        "strategy_eligibility_brief_count: 1",
        "risk_authority_brief_count: 1",
        "research_queue_brief_count: 1",
        "sma_research_observation_brief_count: 1",
        "sma_research_summary_observation_count: 1",
        "research_return_observation_brief_count: 1",
        "research_return_summary_observation_brief_count: 1",
        "Limitations",
        "Non-Claims",
    ):
        assert value in text_stdout

    assert payload["package_type"] == "advisory_operating_brief_package"
    assert payload["package_id"] == _PACKAGE_ID
    assert payload["title"] == _TITLE
    assert payload["summary"] == _SUMMARY
    assert payload["as_of"] == _AS_OF
    assert payload["status"] == "candidate_only"
    assert payload["authority"] == "advisory_only"
    assert payload["capital_authority"] is False
    assert payload["limitations"]
    assert payload["non_claims"]

    assert content_bundle["status"] == "candidate_only"
    assert content_bundle["authority"] == "advisory_only"
    assert content_bundle["capital_authority"] is False
    assert content_bundle["limitations"]
    assert content_bundle["non_claims"]
    assert all(key in content_bundle for key in _BRANCH_KEYS)
    assert content_bundle["candidate_research_brief_count"] == 1
    assert content_bundle["strategy_eligibility_brief_count"] == 1
    assert content_bundle["risk_authority_brief_count"] == 1
    assert content_bundle["research_queue_brief_count"] == 1
    assert content_bundle["sma_research_observation_brief_count"] == 1
    assert content_bundle["sma_research_summary_observation_count"] == 1
    assert content_bundle["research_return_observation_brief_count"] == 1
    assert content_bundle["research_return_summary_observation_brief_count"] == 1
    assert sma_summary["observation_type"] == "sma_research_summary_observation"
    assert sma_summary["status"] == "candidate_only"
    assert sma_summary["authority"] == "advisory_only"
    assert sma_summary["capital_authority"] is False
    assert sma_summary["research_scope"] == "research_only"
    assert sma_summary["summary_state"] == "observations_summarized"
    assert sma_summary["total_observation_count"] == 2
    assert sma_summary["above_sma_count"] == 1
    assert sma_summary["insufficient_history_count"] == 1
    for branch_key in _BRANCH_KEYS:
        assert len(_list(content_bundle[branch_key])) == 1


def test_package_preview_exposes_only_format_text_or_json() -> None:
    parser = _preview_parser()
    package_commands = tuple(
        command
        for command in _subparser_choices(build_parser())
        if command.startswith("advisory-operating-brief-package")
    )

    assert parser.prog == f"algotrader {_COMMAND}"
    assert _COMMAND in _subparser_choices(build_parser())
    assert package_commands == (_COMMAND,)
    assert _positional_rows(parser) == ()
    assert _option_rows(parser) == (("output_format", ("--format",), ("text", "json")),)


def test_package_preview_exposes_no_external_input_options() -> None:
    option_text = _option_text(_preview_parser())
    option_strings = " ".join(_preview_parser()._option_string_actions).lower()

    for term in _blocked_cli_option_terms():
        assert term not in option_text
        assert term not in option_strings


def test_existing_content_bundle_preview_modes_remain_unchanged(capsys) -> None:
    default_bundle = build_synthetic_advisory_operating_brief_content_bundle()
    risk_bundle = build_synthetic_advisory_operating_brief_content_bundle_with_risk()
    research_queue_bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()
    )
    combined_bundle = (
        build_synthetic_advisory_operating_brief_content_bundle_with_research_queue(
            include_risk_authority=True,
        )
    )
    cases = (
        ((), default_bundle),
        ((_RISK_FLAG,), risk_bundle),
        ((_RESEARCH_QUEUE_FLAG,), research_queue_bundle),
        ((_RISK_FLAG, _RESEARCH_QUEUE_FLAG), combined_bundle),
    )

    for flags, bundle in cases:
        expected = export_advisory_operating_brief_content_bundle(bundle)

        default_or_flag_text = _run_preview_cli(
            (_CONTENT_BUNDLE_COMMAND, *flags),
            capsys,
        )
        explicit_text = _run_preview_cli(
            (_CONTENT_BUNDLE_COMMAND, *flags, "--format", "text"),
            capsys,
        )
        json_stdout = _run_preview_cli(
            (_CONTENT_BUNDLE_COMMAND, *flags, "--format", "json"),
            capsys,
        )

        assert default_or_flag_text == explicit_text == expected.rendered_text
        assert json_stdout == expected.json_text
        assert json.loads(json_stdout) == expected.payload


def test_output_authority_terms_are_limited_to_caution_lists(capsys) -> None:
    rendered = _run_preview_cli((_COMMAND,), capsys)
    payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))
    source_cautions = _source_caution_values(payload)

    assert _payload_keys(payload).isdisjoint(_forbidden_actionable_field_names())
    assert _rendered_field_names(rendered).isdisjoint(
        _forbidden_actionable_field_names()
    )

    for path, value in _authority_presentation_payload_strings(payload):
        assert _is_caution_path(path), (path, value)
        assert value in source_cautions

    for line in _authority_presentation_lines(rendered):
        assert line.startswith("- ")
        assert line[2:] in source_cautions

    compact = json.dumps(payload, sort_keys=True, separators=(",", ":")).lower()
    for state_value in _state_values(payload):
        lowered = state_value.lower()
        assert "paper" not in lowered
        assert "live" not in lowered
        assert _s("app", "roved") not in lowered
        assert _s("tra", "ding_ready") not in lowered
        assert _s("tra", "ding-ready") not in lowered
        assert "actionable" not in lowered

    assert _s('"', "app", "roved", '"') not in compact
    assert '"paper"' not in compact
    assert '"live"' not in compact
    assert _s("tra", "ding-ready") not in compact
    assert _s("tra", "ding_ready") not in compact
    assert "actionable" not in compact


def test_json_payload_adds_no_forbidden_serialized_fields(capsys) -> None:
    payload = json.loads(_run_preview_cli((_COMMAND, "--format", "json"), capsys))

    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_SERIALIZED_FIELD_NAMES)
    assert _payload_keys(_EXPECTED_PAYLOAD).isdisjoint(
        _FORBIDDEN_SERIALIZED_FIELD_NAMES
    )


def test_production_cli_modules_import_no_tests_or_fixtures() -> None:
    for module in (cli_module, preview_module, synthetic_module):
        imports = _import_references(module)
        source = _source_text(module)

        assert all(not name.startswith("tests") for name in imports)
        assert "tests.fixtures" not in imports
        assert re.search(r"(?m)^\s*(from|import)\s+tests\b", source) is None
        assert re.search(r"(?m)^\s*from\s+tests\.fixtures\b", source) is None


def test_production_package_preview_has_no_forbidden_imports_calls_or_terms() -> None:
    imports = set()
    call_names = set()
    lowered_source = ""
    for module in (preview_module, synthetic_module):
        imports.update(_import_references(module))
        call_names.update(_call_names(module))
        lowered_source += _source_text(module).lower()

    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_production_call_names())
    for term in _blocked_production_source_terms():
        assert (
            re.search(
                rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])",
                lowered_source,
            )
            is None
        )


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


def _key_count(value: object, key: str) -> int:
    if isinstance(value, dict):
        return sum(
            (1 if item_key == key else 0) + _key_count(item_value, key)
            for item_key, item_value in value.items()
        )
    if isinstance(value, list):
        return sum(_key_count(item, key) for item in value)
    return 0


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


def _authority_presentation_lines(text: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in text.splitlines()
        if any(
            re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", line.lower())
            for term in _authority_presentation_terms()
        )
    )


def _authority_presentation_payload_strings(
    value: object,
    path: str = "",
) -> tuple[tuple[str, str], ...]:
    matches: list[tuple[str, str]] = []
    if _is_embedded_export_text_path(path):
        return ()
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}" if path else key
            matches.extend(
                _authority_presentation_payload_strings(nested_value, nested_path)
            )
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
        for term in _authority_presentation_terms()
    )


def _is_embedded_export_text_path(path: str) -> bool:
    return path in {
        "content_bundle_export.json_text",
        "content_bundle_export.rendered_text",
    }


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


def _blocked_cli_option_terms() -> tuple[str, ...]:
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
        _s("algotrader.", "back", "test"),
        _s("algotrader.", "back", "testing"),
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
        "click",
        _s("cre", "dential"),
        _s("data", "base"),
        "duckdb",
        "httpx",
        "ipynb",
        "joblib",
        "keras",
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
        "tensorflow",
        "torch",
        "typer",
        "urllib",
        "vectorbt",
        "xgboost",
        _s("y", "finance"),
    )


def _blocked_self_import_prefixes() -> tuple[str, ...]:
    return _blocked_import_prefixes()


def _blocked_production_call_names() -> set[str]:
    return {
        "__import__",
        "Path",
        _s("cli", "ent"),
        _s("con", "nect"),
        _s("create_", "or", "der"),
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
        "json.dump",
        "json.load",
        "load",
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


def _blocked_self_call_names() -> set[str]:
    return _blocked_production_call_names() - {"main"}


def _blocked_production_source_terms() -> tuple[str, ...]:
    return (
        _s("acc", "ount"),
        _s("acc", "ounts"),
        _s("ag", "ent"),
        _s("allo", "cation"),
        _s("app", "roval"),
        _s("app", "roved"),
        _s("back", "testing"),
        _s("bro", "ker"),
        _s("cre", "dential"),
        _s("dash", "board"),
        _s("data source app", "roval"),
        _s("fi", "ll"),
        _s("fi", "lls"),
        _s("li", "ve"),
        _s("l", "lm"),
        _s("m", "l"),
        _s("methodology app", "roval"),
        _s("n", "et", "work"),
        _s("note", "book"),
        _s("or", "der"),
        _s("or", "ders"),
        _s("pa", "per"),
        _s("port", "folio"),
        _s("ran", "king"),
        _s("read", "iness"),
        _s("recomm", "endation"),
        _s("risk app", "roval"),
        _s("run", "time"),
        _s("sche", "duler"),
        _s("sco", "ring"),
        _s("so", "cket"),
        _s("tra", "ding authority"),
        _s("tra", "ding_ready"),
        _s("tra", "ding-ready"),
        _s("tra", "ding_authority"),
        _s("ven", "dor"),
    )


def _authority_presentation_terms() -> tuple[str, ...]:
    return (
        _s("app", "roval"),
        _s("app", "roved"),
        _s("reco", "mmendation"),
        _s("ran", "king"),
        _s("sco", "ring"),
        "paper readiness",
        "live readiness",
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
