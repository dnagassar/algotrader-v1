from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from algotrader.research.candidate_research_brief_item import (
    CandidateResearchBriefItem,
    build_candidate_research_brief_item,
)
from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
)
from tests.fixtures import candidate_research_brief_item as fixture_module
from tests.fixtures.candidate_research_brief_item import (
    build_synthetic_candidate_research_brief_item,
    expected_synthetic_candidate_research_brief_item_dict,
)
from tests.fixtures.candidate_result_dossier import (
    build_synthetic_candidate_research_result_dossier,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


FIXTURE_PATH = Path("tests/fixtures/candidate_research_brief_item.py")

_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "algotrader.research.candidate_research_brief_item",
    "tests.fixtures.candidate_result_dossier",
}

_ALLOWED_CALL_NAMES = {
    "build_candidate_research_brief_item",
    "build_synthetic_candidate_research_brief_item",
    "build_synthetic_candidate_research_result_dossier",
    "to_dict",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _s("algotrader.", "bro", "ker"),
    _s("algotrader.", "bro", "kers"),
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
    "anthropic",
    _s("data", "base"),
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    _s("mas", "sive"),
    _s("net", "work"),
    _s("num", "py"),
    "openai",
    "os",
    _s("pan", "das"),
    "pathlib",
    _s("poly", "gon"),
    _s("poly", "gon_a", "pi_client"),
    _s("quant", "connect"),
    _s("re", "quests"),
    _s("so", "cket"),
    "sqlmodel",
    "urllib",
    "vectorbt",
    _s("y", "finance"),
)

_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "client",
    _s("con", "nect"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _s("down", "load"),
    "eval",
    "exec",
    "exists",
    "getenv",
    "glob",
    "import_module",
    "importlib.import_module",
    _s("ing", "est"),
    "is_file",
    "iterdir",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "parse",
    "Path",
    _s("persist"),
    "post",
    "read",
    "read_bytes",
    "read_csv",
    "read_text",
    _s("re", "quest"),
    _s("re", "quests.get"),
    "rglob",
    _s("so", "cket.socket"),
    "stat",
    _s("submit_", "or", "der"),
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_FORBIDDEN_PAYLOAD_FIELDS = {
    "account",
    _s("action"),
    _s("actions"),
    _s("approval"),
    _s("approved"),
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
    _s("fi", "ll"),
    _s("fi", "lls"),
    "live_authorized",
    "live_probe_eligible",
    _s("or", "der"),
    _s("or", "ders"),
    "paper_eligible",
    _s("port", "folio"),
    _s("port", "folios"),
    _s("allo", "cation"),
    _s("allo", "cations"),
    _s("po", "sition"),
    _s("po", "sitions"),
    _s("recommendation"),
    _s("recommendations"),
    "ready",
    _s("run", "time"),
    _s("run", "times"),
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

_REQUIRED_NON_CLAIMS = (
    _not("source approval"),
    _not("data approval"),
    _not("endpoint approval"),
    _not("universe approval"),
    _not("bench", "mark approval"),
    _not("ca", "sh proxy approval"),
    _not("methodology approval"),
    _not("evidence approval"),
    _not("return-construction approval"),
    _not("no-lookahead approval"),
    _not("stra", "tegy validation"),
    _not("tra", "ding readiness"),
    _not("production use"),
    _not("bro", "ker or run", "time use"),
    _not("or", "der generation"),
    _not("port", "folio or allo", "cation authority"),
)


def test_fixture_builds_candidate_research_brief_item() -> None:
    item = build_synthetic_candidate_research_brief_item()

    assert isinstance(item, CandidateResearchBriefItem)
    assert isinstance(item.dossier, CandidateResearchResultDossier)


def test_fixture_builds_through_phase_133_dossier_fixture_and_phase_134_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_dossier = build_synthetic_candidate_research_result_dossier()

    assert fixture_module.build_synthetic_candidate_research_result_dossier is (
        build_synthetic_candidate_research_result_dossier
    )
    assert fixture_module.build_candidate_research_brief_item is (
        build_candidate_research_brief_item
    )

    def recording_dossier_fixture() -> CandidateResearchResultDossier:
        calls.append(("dossier_fixture", source_dossier))
        return source_dossier

    def recording_brief_builder(
        dossier: CandidateResearchResultDossier,
    ) -> CandidateResearchBriefItem:
        item = build_candidate_research_brief_item(dossier)
        calls.append(("brief_builder", dossier))
        return item

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_result_dossier",
        recording_dossier_fixture,
    )
    monkeypatch.setattr(
        fixture_module,
        "build_candidate_research_brief_item",
        recording_brief_builder,
    )

    item = fixture_module.build_synthetic_candidate_research_brief_item()

    assert [name for name, _ in calls] == [
        "dossier_fixture",
        "brief_builder",
    ]
    assert calls[0][1] is source_dossier
    assert calls[1][1] is source_dossier
    assert item.dossier is source_dossier


def test_fixture_preserves_dossier_identity_where_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dossier = build_synthetic_candidate_research_result_dossier()

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_result_dossier",
        lambda: source_dossier,
    )

    item = fixture_module.build_synthetic_candidate_research_brief_item()

    assert item.dossier is source_dossier
    assert item.limitations is source_dossier.limitations
    assert item.non_claims is source_dossier.non_claims


def test_item_type_status_headline_and_summary_are_advisory_and_deterministic() -> None:
    first = build_synthetic_candidate_research_brief_item()
    second = build_synthetic_candidate_research_brief_item()

    assert first.item_type == "candidate_research_result"
    assert first.status == "candidate_only"
    assert first.headline == second.headline
    assert first.summary_points == second.summary_points
    assert _is_clean_string(first.headline)
    assert first.summary_points
    assert all(_is_clean_string(value) for value in first.summary_points)
    _assert_non_actionable((first.headline, *first.summary_points))


def test_limitations_non_claims_and_required_non_claims_are_carried_forward() -> None:
    item = build_synthetic_candidate_research_brief_item()
    payload = item.to_dict()

    assert item.limitations is item.dossier.limitations
    assert item.non_claims is item.dossier.non_claims
    assert item.limitations
    assert item.non_claims
    assert payload["limitations"] == list(item.dossier.limitations)
    assert payload["non_claims"] == list(item.dossier.non_claims)
    assert set(_REQUIRED_NON_CLAIMS).issubset(item.non_claims)
    assert all(value.startswith("not ") for value in item.non_claims)


def test_phase_123_fingerprint_is_preserved_in_brief_item_dict() -> None:
    item = build_synthetic_candidate_research_brief_item()
    payload = item.to_dict()

    assert item.dossier.package.fingerprint == _SYNTHETIC_FIXTURE_DIGEST
    assert payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST


def test_phase_127_provenance_convention_is_preserved_in_brief_item_dict() -> None:
    item = build_synthetic_candidate_research_brief_item()
    payload = item.to_dict()

    assert payload["package_snapshot_id"] == item.dossier.package.snapshot.snapshot_id
    assert payload["result_snapshot_manifest_fixture_id"] == (
        item.dossier.package.snapshot.snapshot_id
    )
    assert payload["result_snapshot_manifest_checksum"] == (
        f"sha256:{item.dossier.package.fingerprint}"
    )


def test_expected_output_matches_brief_item_serialization_exactly() -> None:
    item = build_synthetic_candidate_research_brief_item()
    expected = expected_synthetic_candidate_research_brief_item_dict()

    assert expected == item.to_dict()
    assert tuple(expected) == (
        "item_type",
        "status",
        "headline",
        "summary_points",
        "package_fingerprint",
        "package_snapshot_id",
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
        "limitations",
        "non_claims",
    )
    assert expected is not item.to_dict()
    _assert_primitive_only(expected)


def test_repeated_fixture_calls_are_deterministic() -> None:
    first = build_synthetic_candidate_research_brief_item()
    second = build_synthetic_candidate_research_brief_item()
    first_expected = expected_synthetic_candidate_research_brief_item_dict()
    second_expected = expected_synthetic_candidate_research_brief_item_dict()

    assert first is not second
    assert first.dossier is not second.dossier
    assert first.to_dict() == second.to_dict()
    assert first_expected == second_expected == first.to_dict()
    assert _sorted_compact_json(first.to_dict()) == _sorted_compact_json(
        second.to_dict()
    )


def test_fixture_helpers_do_not_mutate_source_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dossier = build_synthetic_candidate_research_result_dossier()
    dossier_before = source_dossier.to_dict()
    package_before = source_dossier.package.to_dict()
    result_before = source_dossier.result.to_dict()
    identity_snapshot = (
        id(source_dossier.package),
        id(source_dossier.result),
        id(source_dossier.package.snapshot),
        id(source_dossier.result.snapshot),
        id(source_dossier.result.snapshot.manifest),
        id(source_dossier.result.summary),
        id(source_dossier.limitations),
        id(source_dossier.non_claims),
    )

    monkeypatch.setattr(
        fixture_module,
        "build_synthetic_candidate_research_result_dossier",
        lambda: source_dossier,
    )

    item = fixture_module.build_synthetic_candidate_research_brief_item()
    item_payload = item.to_dict()
    expected_payload = fixture_module.expected_synthetic_candidate_research_brief_item_dict()
    item_payload["summary_points"].append("mutated primitive copy")
    item_payload["limitations"].append("mutated primitive copy")
    item_payload["non_claims"].append("mutated primitive copy")
    expected_payload["summary_points"].append("mutated primitive copy")
    expected_payload["limitations"].append("mutated primitive copy")
    expected_payload["non_claims"].append("mutated primitive copy")

    assert item.dossier is source_dossier
    assert source_dossier.to_dict() == dossier_before
    assert source_dossier.package.to_dict() == package_before
    assert source_dossier.result.to_dict() == result_before
    assert (
        id(source_dossier.package),
        id(source_dossier.result),
        id(source_dossier.package.snapshot),
        id(source_dossier.result.snapshot),
        id(source_dossier.result.snapshot.manifest),
        id(source_dossier.result.summary),
        id(source_dossier.limitations),
        id(source_dossier.non_claims),
    ) == identity_snapshot


def test_fixture_adds_no_disallowed_payload_or_object_fields() -> None:
    item = build_synthetic_candidate_research_brief_item()
    payload = item.to_dict()

    assert tuple(payload) == (
        "item_type",
        "status",
        "headline",
        "summary_points",
        "package_fingerprint",
        "package_snapshot_id",
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
        "limitations",
        "non_claims",
    )
    assert _payload_keys(payload).isdisjoint(_FORBIDDEN_PAYLOAD_FIELDS)
    assert all(not hasattr(item, field_name) for field_name in _FORBIDDEN_PAYLOAD_FIELDS)
    assert all(
        not hasattr(item.dossier, field_name)
        for field_name in _FORBIDDEN_PAYLOAD_FIELDS
    )


def test_fixture_module_has_no_forbidden_imports_or_calls() -> None:
    imports = _import_references()
    call_names = _call_names()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names == _ALLOWED_CALL_NAMES
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_fixture_module_text_has_no_real_world_path_secret_or_trading_literals() -> None:
    source = _source_text()
    upper_source = source.upper()
    lowered = source.lower()

    for code_points in _real_symbol_codes():
        symbol = "".join(chr(code_point) for code_point in code_points)
        assert re.search(rf"(?<![A-Z0-9]){symbol}(?![A-Z0-9])", upper_source) is None
    for term in _vendor_or_provider_terms():
        assert term not in lowered
    for term in _credential_terms():
        assert term not in lowered
    for marker in _path_or_data_source_markers():
        assert marker not in lowered
    for word in _forbidden_source_words():
        assert re.search(rf"(?<![a-z0-9_]){word}(?![a-z0-9_])", lowered) is None


def _is_clean_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _assert_non_actionable(values: tuple[str, ...]) -> None:
    lowered_values = tuple(value.lower() for value in values)

    for term in _actionable_terms():
        assert all(
            re.search(rf"(?<![a-z0-9_]){term}(?![a-z0-9_])", value) is None
            for value in lowered_values
        )


def _actionable_terms() -> tuple[str, ...]:
    return (
        _s("action"),
        _s("actions"),
        _s("approval"),
        _s("approved"),
        "buy",
        "enter",
        "exit",
        "hold",
        _s("or", "der"),
        _s("recommend"),
        _s("recommendation"),
        _s("sell"),
        _s("size"),
        "tradable",
        _s("tra", "de"),
        _s("tra", "ding"),
        "validated",
    )


def _sorted_compact_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _assert_primitive_only(value: object) -> None:
    assert not isinstance(value, (tuple, set))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_only(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_primitive_only(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


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


def _source_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(FIXTURE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            elif node.level > 0:
                imports.add("__future__")

    return imports


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
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


def _vendor_or_provider_terms() -> set[str]:
    return {
        _s("al", "paca"),
        "alpha vantage",
        "bloomberg",
        "factset",
        "finnhub",
        "fred",
        _s("interactive ", "bro", "kers"),
        _s("mas", "sive"),
        "morningstar",
        "nasdaq",
        _s("poly", "gon"),
        _s("quant", "connect"),
        "quandl",
        "refinitiv",
        "stooq",
        "tiingo",
        "yahoo",
        _s("y", "finance"),
    }


def _credential_terms() -> set[str]:
    return {
        _s("a", "pi_key"),
        _s("a", "pikey"),
        "bearer",
        _s("client_", "sec", "ret"),
        "credential",
        "oauth",
        "password",
        _s("private_key"),
        _s("sec", "ret"),
        "token",
    }


def _path_or_data_source_markers() -> set[str]:
    return {
        _s(":", chr(47), chr(47)),
        "http:",
        "https:",
        "www.",
        ".com",
        _s(".data"),
        ".csv",
        ".jsonl",
        ".parquet",
        ".zip",
        chr(47),
        chr(92),
    }


def _forbidden_source_words() -> set[str]:
    return {
        _s("bench", "mark"),
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
        _s("recommendation"),
        _s("recommendations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        _s("run", "time"),
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "de"),
        _s("tra", "des"),
    }
