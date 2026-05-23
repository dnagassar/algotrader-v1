from __future__ import annotations

import ast
import inspect
import json
import re
import sys

import algotrader.research.advisory_operating_brief_cli as preview_module
from algotrader.cli import build_parser, main
from algotrader.research.advisory_operating_brief_cli import (
    build_synthetic_advisory_operating_brief,
)
from algotrader.research.advisory_operating_brief_export import (
    export_advisory_operating_brief,
)
from algotrader.research.advisory_operating_brief_renderer import (
    render_advisory_operating_brief_text,
)
from tests.unit.test_advisory_operating_brief_export_regression import (
    _EXPECTED_JSON_TEXT,
    _NON_CLAIM_VALUES,
    _OPERATING_LIMITATION_VALUES,
)
from tests.unit.test_advisory_operating_brief_renderer_regression import (
    _EXPECTED_RENDERED_LINES,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _bullet(value: str) -> str:
    return f"- {value}"


_COMMAND = "advisory-operating-brief-preview"
_SYNTHETIC_FIXTURE_ID = "synthetic_return_input_snapshot_fixture_001"
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)
_SYNTHETIC_FIXTURE_CHECKSUM = f"sha256:{_SYNTHETIC_FIXTURE_DIGEST}"

_REQUIRED_MARKERS = (
    "advisory_operating_brief",
    "candidate_research_brief",
    "candidate_research_results",
    "candidate_research_result",
    "candidate_only",
)
_PROVENANCE_MARKERS = (
    _SYNTHETIC_FIXTURE_DIGEST,
    _SYNTHETIC_FIXTURE_ID,
    _SYNTHETIC_FIXTURE_CHECKSUM,
    "package_fingerprint",
    "package_snapshot_id",
    "result_snapshot_manifest_fixture_id",
    "result_snapshot_manifest_checksum",
)

_ALLOWED_IMPORTS = {
    "__future__",
    "ast",
    "inspect",
    "json",
    "re",
    "sys",
    "algotrader.cli",
    "algotrader.research.advisory_operating_brief_cli",
    "algotrader.research.advisory_operating_brief_export",
    "algotrader.research.advisory_operating_brief_renderer",
    "tests.unit.test_advisory_operating_brief_export_regression",
    "tests.unit.test_advisory_operating_brief_renderer_regression",
}


def test_default_text_cli_output_matches_phase_145_renderer_pin(capsys) -> None:
    expected_text = _expected_text_pin()

    assert (
        render_advisory_operating_brief_text(
            build_synthetic_advisory_operating_brief()
        )
        == expected_text
    )
    assert _run_preview_cli((_COMMAND,), capsys) == expected_text


def test_json_cli_output_matches_phase_147_compact_export_pin(capsys) -> None:
    expected_export = _expected_export()

    output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert output == _EXPECTED_JSON_TEXT
    assert output == expected_export.json_text
    assert json.loads(output) == expected_export.payload


def test_repeated_cli_invocations_are_byte_identical(capsys) -> None:
    first_text = _run_preview_cli((_COMMAND,), capsys)
    second_text = _run_preview_cli((_COMMAND,), capsys)
    first_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    second_json = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert first_text == second_text == _expected_text_pin()
    assert first_json == second_json == _EXPECTED_JSON_TEXT
    assert first_text.encode("utf-8") == second_text.encode("utf-8")
    assert first_json.encode("utf-8") == second_json.encode("utf-8")


def test_json_cli_output_parses_to_expected_export_payload(capsys) -> None:
    expected_payload = _expected_export().payload

    output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert json.loads(output) == expected_payload
    assert json.loads(output) == json.loads(_EXPECTED_JSON_TEXT)


def test_fixed_preview_type_and_status_values_are_present(capsys) -> None:
    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    payload = json.loads(json_output)
    candidate_payload = _single_candidate_brief_payload(payload)
    section_payload = _single_section_payload(payload)
    item_payload = _single_item_payload(payload)

    assert payload["operating_brief_type"] == "advisory_operating_brief"
    assert candidate_payload["brief_type"] == "candidate_research_brief"
    assert section_payload["section_type"] == "candidate_research_results"
    assert item_payload["item_type"] == "candidate_research_result"
    for value in _REQUIRED_MARKERS:
        assert value in text_output
        assert value in json_output


def test_fingerprint_and_provenance_convention_are_present(capsys) -> None:
    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    item_payload = _single_item_payload(json.loads(json_output))

    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST
    assert item_payload["package_snapshot_id"] == _SYNTHETIC_FIXTURE_ID
    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        _SYNTHETIC_FIXTURE_ID
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        _SYNTHETIC_FIXTURE_CHECKSUM
    )
    for value in _PROVENANCE_MARKERS:
        assert value in text_output
        assert value in json_output


def test_limitations_and_non_claims_are_present_in_cli_views(capsys) -> None:
    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)

    assert "Limitations" in text_output
    assert "Non-Claims" in text_output
    for value in (*_OPERATING_LIMITATION_VALUES, *_NON_CLAIM_VALUES):
        assert value in json_output
        assert _bullet(value) in text_output


def test_preview_command_exposes_only_format_option() -> None:
    option_rows = _option_rows(_preview_parser())
    positional_rows = _positional_rows(_preview_parser())

    assert positional_rows == ()
    assert option_rows == (("output_format", ("--format",), ("text", "json")),)


def test_preview_command_exposes_no_real_input_or_external_options() -> None:
    option_text = _option_text(_preview_parser())

    for term in _blocked_cli_option_terms():
        assert term not in option_text


def test_cli_preview_does_not_mutate_brief_object(monkeypatch, capsys) -> None:
    operating_brief = build_synthetic_advisory_operating_brief()
    before_payload = operating_brief.to_dict()

    def build_existing_brief():
        return operating_brief

    monkeypatch.setattr(
        preview_module,
        "build_synthetic_advisory_operating_brief",
        build_existing_brief,
    )

    assert _run_preview_cli((_COMMAND, "--format", "json"), capsys) == (
        _EXPECTED_JSON_TEXT
    )
    assert operating_brief.to_dict() == before_payload
    assert export_advisory_operating_brief(operating_brief).payload == before_payload


def test_cli_views_keep_blocked_decision_terms_outside_payload(capsys) -> None:
    expected_export = _expected_export()
    text_output = _run_preview_cli((_COMMAND,), capsys)
    json_output = _run_preview_cli((_COMMAND, "--format", "json"), capsys)
    fixed_text = _remove_payload_strings(text_output, expected_export.payload).lower()
    fixed_json = _remove_payload_strings(json_output, expected_export.payload).lower()

    assert _payload_keys(expected_export.payload).isdisjoint(_blocked_field_names())
    for fixed_view in (fixed_text, fixed_json):
        for term in _blocked_output_terms():
            assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", fixed_view) is None


def test_new_test_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_blocked_prefix(module_name, _blocked_import_prefixes())
    ] == []
    assert call_names.isdisjoint(_blocked_call_names())


def test_new_test_module_text_has_no_disallowed_literals() -> None:
    source = _source_text()
    upper_source = source.upper()
    lowered = source.lower()

    for code_points in _real_symbol_codes():
        symbol = "".join(chr(code_point) for code_point in code_points)
        assert re.search(rf"(?<![A-Z0-9]){symbol}(?![A-Z0-9])", upper_source) is None
    for term in _provider_or_sdk_terms():
        assert term not in lowered
    for term in _sensitive_terms():
        assert term not in lowered
    for marker in _location_markers():
        assert marker not in lowered
    for term in _index_like_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", lowered) is None
    for term in _blocked_output_terms():
        assert re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", lowered) is None


def _run_preview_cli(argv: tuple[str, ...], capsys) -> str:
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _expected_text_pin() -> str:
    return chr(10).join(_EXPECTED_RENDERED_LINES)


def _expected_export():
    return export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )


def _preview_parser():
    return _subparser_choices(build_parser())[_COMMAND]


def _subparser_choices(parser) -> dict[str, object]:
    for parser_entry in parser._actions:
        choices = getattr(parser_entry, "choices", None)
        if isinstance(choices, dict) and _COMMAND in choices:
            return choices
    raise AssertionError("parser has no preview command choices")


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
        _s("market"),
        _s("da", "ta"),
        _s("feed"),
        _s("ing", "est"),
        _s("endpoint"),
        _s("live"),
        _s("paper"),
    )


def _single_candidate_brief_payload(payload: dict[str, object]) -> dict[str, object]:
    candidate_briefs = payload["candidate_research_briefs"]
    assert isinstance(candidate_briefs, list)
    assert len(candidate_briefs) == 1
    candidate_brief = candidate_briefs[0]
    assert isinstance(candidate_brief, dict)
    return candidate_brief


def _single_section_payload(payload: dict[str, object]) -> dict[str, object]:
    candidate_brief = _single_candidate_brief_payload(payload)
    sections = candidate_brief["sections"]
    assert isinstance(sections, list)
    assert len(sections) == 1
    section = sections[0]
    assert isinstance(section, dict)
    return section


def _single_item_payload(payload: dict[str, object]) -> dict[str, object]:
    section = _single_section_payload(payload)
    items = section["items"]
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, dict)
    return item


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


def _source_text() -> str:
    return inspect.getsource(sys.modules[__name__])


def _tree() -> ast.AST:
    return ast.parse(_source_text())


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_blocked_prefix(
    module_name: str,
    blocked_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == blocked_prefix
        or module_name.startswith(f"{blocked_prefix}.")
        for blocked_prefix in blocked_prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


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
        _s("ht", "tp"),
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
        _s("poly", "gon"),
        _s("poly", "gon_a", "pi_client"),
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
        "print",
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


def _blocked_field_names() -> set[str]:
    return {
        _s("acc", "ount"),
        _s("act", "ion"),
        _s("act", "ions"),
        _s("app", "roval"),
        _s("app", "roved"),
        _s("bench", "mark"),
        _s("bench", "marks"),
        _s("bro", "ker"),
        _s("bro", "kers"),
        _s("ca", "sh"),
        _s("ca", "sh_return"),
        _s("ca", "sh_returns"),
        _s("co", "st"),
        _s("co", "sts"),
        "evaluator",
        "evaluators",
        "live_authorized",
        "live_probe_eligible",
        _s("or", "der"),
        _s("or", "ders"),
        _s("port", "folio"),
        _s("port", "folios"),
        _s("allo", "cation"),
        _s("allo", "cations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        _s("prior", "ity"),
        _s("prior", "itized"),
        _s("ra", "nk"),
        _s("ra", "nking"),
        _s("reco", "mmendation"),
        _s("reco", "mmendations"),
        "ready",
        _s("run", "time"),
        _s("run", "times"),
        _s("sco", "re"),
        _s("sco", "ring"),
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("stra", "tegy_state"),
        "tradable",
        _s("tra", "de"),
        _s("tra", "des"),
        _s("tra", "ding_readiness"),
        "validated",
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
        (88, 76, 75),
        (88, 76, 70),
        (88, 76, 69),
        (88, 76, 86),
        (88, 76, 85),
        (88, 76, 73),
        (88, 76, 89),
        (88, 76, 80),
        (88, 76, 82, 69),
    )


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


def _index_like_terms() -> set[str]:
    return {
        _s("s", "&p"),
        _s("russ", "ell"),
        _s("wil", "shire"),
        _s("ms", "ci"),
        _s("cr", "sp"),
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
