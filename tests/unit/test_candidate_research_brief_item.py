from __future__ import annotations

import ast
import json
import re
from dataclasses import fields
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.candidate_research_brief_item import (
    CandidateResearchBriefItem,
    build_candidate_research_brief_item,
)
from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
)
from tests.fixtures.candidate_result_dossier import (
    build_synthetic_candidate_research_result_dossier,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/candidate_research_brief_item.py")

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.candidate_result_dossier",
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


def test_builds_brief_item_from_phase_133_synthetic_dossier_fixture() -> None:
    dossier = dossier_fixture()

    item = build_candidate_research_brief_item(dossier)

    assert isinstance(dossier, CandidateResearchResultDossier)
    assert isinstance(item, CandidateResearchBriefItem)
    assert item.dossier is dossier
    assert item.item_type == "candidate_research_result"
    assert item.status == "candidate_only"


def test_builder_preserves_dossier_identity_and_carries_forward_guardrails() -> None:
    dossier = dossier_fixture()

    item = build_candidate_research_brief_item(dossier)

    assert item.dossier is dossier
    assert item.limitations is dossier.limitations
    assert item.non_claims is dossier.non_claims
    assert item.limitations == dossier.limitations
    assert item.non_claims == dossier.non_claims
    assert set(dossier.non_claims).issubset(item.non_claims)
    assert all(value.startswith("not ") for value in item.non_claims)


def test_headline_and_summary_points_are_deterministic_and_non_empty() -> None:
    dossier = dossier_fixture()
    manifest = dossier.result.snapshot.manifest

    item = build_candidate_research_brief_item(dossier)

    assert item.headline == (
        "Candidate research result metadata for "
        f"{dossier.package.snapshot.snapshot_id}"
    )
    assert item.summary_points == (
        f"package snapshot id: {dossier.package.snapshot.snapshot_id}",
        f"package fingerprint: {dossier.package.fingerprint}",
        f"result manifest fixture id: {manifest.fixture_id}",
        f"result manifest checksum: {manifest.checksum}",
    )
    assert _is_clean_string(item.headline)
    assert item.summary_points
    assert all(_is_clean_string(value) for value in item.summary_points)


def test_direct_construction_accepts_valid_dossier_item_payload() -> None:
    dossier = dossier_fixture()
    payload = _valid_constructor_payload(dossier)

    item = CandidateResearchBriefItem(**payload)

    assert item.dossier is dossier
    assert item.to_dict()["item_type"] == "candidate_research_result"


@pytest.mark.parametrize("value", (object(), None, "not a dossier"))
def test_direct_construction_rejects_non_dossier_input(value: object) -> None:
    payload = _valid_constructor_payload(dossier_fixture())
    payload["dossier"] = value

    with pytest.raises(ValidationError, match="CandidateResearchResultDossier"):
        CandidateResearchBriefItem(**payload)


@pytest.mark.parametrize(
    "item_type",
    (
        "",
        "candidate_result",
        "candidate_research_result_preview",
        "validated_candidate_research_result",
    ),
)
def test_direct_construction_rejects_forbidden_item_types(item_type: str) -> None:
    payload = _valid_constructor_payload(dossier_fixture())
    payload["item_type"] = item_type

    with pytest.raises(ValidationError, match="item_type"):
        CandidateResearchBriefItem(**payload)


@pytest.mark.parametrize(
    "status",
    (
        "",
        "validated",
        "approved",
        "tradable",
        "ready",
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
    ),
)
def test_direct_construction_rejects_approval_like_statuses(status: str) -> None:
    payload = _valid_constructor_payload(dossier_fixture())
    payload["status"] = status

    with pytest.raises(ValidationError, match="status"):
        CandidateResearchBriefItem(**payload)


@pytest.mark.parametrize("headline", ("", " ", " brief", "brief ", None, 3))
def test_direct_construction_rejects_empty_or_malformed_headline(
    headline: object,
) -> None:
    payload = _valid_constructor_payload(dossier_fixture())
    payload["headline"] = headline

    with pytest.raises(ValidationError, match="headline"):
        CandidateResearchBriefItem(**payload)


@pytest.mark.parametrize(
    "summary_points",
    (
        (),
        [],
        "summary",
        ("valid", ""),
        ("valid", " "),
        ("valid", " trailing "),
        ("valid", 1),
        None,
    ),
)
def test_direct_construction_rejects_empty_or_malformed_summary_points(
    summary_points: object,
) -> None:
    payload = _valid_constructor_payload(dossier_fixture())
    payload["summary_points"] = summary_points

    with pytest.raises(ValidationError, match="summary_points"):
        CandidateResearchBriefItem(**payload)


def test_direct_construction_rejects_empty_or_malformed_limitations() -> None:
    dossier = dossier_fixture()

    for limitations in (
        (),
        list(dossier.limitations),
        "limitation",
        ("valid", ""),
        ("valid", " "),
        ("valid", 1),
        dossier.limitations[:-1],
        None,
    ):
        payload = _valid_constructor_payload(dossier)
        payload["limitations"] = limitations
        with pytest.raises(ValidationError, match="limitations"):
            CandidateResearchBriefItem(**payload)


def test_direct_construction_rejects_empty_or_malformed_non_claims() -> None:
    dossier = dossier_fixture()

    for non_claims in (
        (),
        list(dossier.non_claims),
        "non-claim",
        ("not valid", ""),
        ("not valid", " "),
        ("not valid", 1),
        dossier.non_claims[:-1],
        dossier.non_claims + ("positive candidate claim",),
        None,
    ):
        payload = _valid_constructor_payload(dossier)
        payload["non_claims"] = non_claims
        with pytest.raises(ValidationError, match="non_claims|negative"):
            CandidateResearchBriefItem(**payload)


def test_to_dict_is_primitive_only_deterministic_and_does_not_alias_lists() -> None:
    dossier = dossier_fixture()
    item = build_candidate_research_brief_item(dossier)
    manifest = dossier.result.snapshot.manifest

    payload = item.to_dict()

    assert not hasattr(CandidateResearchBriefItem, "from_dict")
    assert payload == item.to_dict()
    assert payload == {
        "item_type": "candidate_research_result",
        "status": "candidate_only",
        "headline": item.headline,
        "summary_points": list(item.summary_points),
        "package_fingerprint": dossier.package.fingerprint,
        "package_snapshot_id": dossier.package.snapshot.snapshot_id,
        "result_snapshot_manifest_fixture_id": manifest.fixture_id,
        "result_snapshot_manifest_checksum": manifest.checksum,
        "limitations": list(dossier.limitations),
        "non_claims": list(dossier.non_claims),
    }
    _assert_primitive_only(payload)
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload

    payload["summary_points"].append("mutated primitive copy")
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("mutated primitive copy")

    assert item.to_dict()["summary_points"] == list(item.summary_points)
    assert item.to_dict()["limitations"] == list(dossier.limitations)
    assert item.to_dict()["non_claims"] == list(dossier.non_claims)


def test_repeated_builder_calls_are_deterministic() -> None:
    dossier = dossier_fixture()

    first = build_candidate_research_brief_item(dossier)
    second = build_candidate_research_brief_item(dossier)
    third = build_candidate_research_brief_item(dossier_fixture())

    assert first is not second
    assert first.dossier is second.dossier is dossier
    assert first.to_dict() == second.to_dict() == third.to_dict()
    assert _sorted_compact_json(first.to_dict()) == _sorted_compact_json(
        second.to_dict()
    )


def test_builder_and_serialization_do_not_mutate_dossier_or_nested_payloads() -> None:
    dossier = dossier_fixture()
    dossier_payload = dossier.to_dict()
    package_payload = dossier.package.to_dict()
    result_payload = dossier.result.to_dict()
    identity_snapshot = (
        id(dossier.package),
        id(dossier.result),
        id(dossier.package.snapshot),
        id(dossier.result.snapshot),
        id(dossier.result.snapshot.manifest),
        id(dossier.result.summary),
        id(dossier.limitations),
        id(dossier.non_claims),
    )

    item = build_candidate_research_brief_item(dossier)
    item_payload = item.to_dict()
    item_payload["summary_points"].append("mutated primitive copy")
    item_payload["limitations"].append("mutated primitive copy")
    item_payload["non_claims"].append("mutated primitive copy")

    assert dossier.to_dict() == dossier_payload
    assert dossier.package.to_dict() == package_payload
    assert dossier.result.to_dict() == result_payload
    assert (
        id(dossier.package),
        id(dossier.result),
        id(dossier.package.snapshot),
        id(dossier.result.snapshot),
        id(dossier.result.snapshot.manifest),
        id(dossier.result.summary),
        id(dossier.limitations),
        id(dossier.non_claims),
    ) == identity_snapshot


def test_brief_item_introduces_no_disallowed_fields() -> None:
    item = build_candidate_research_brief_item(dossier_fixture())
    payload = item.to_dict()
    forbidden_fields = _forbidden_payload_fields()

    assert tuple(field.name for field in fields(CandidateResearchBriefItem)) == (
        "dossier",
        "item_type",
        "status",
        "headline",
        "summary_points",
        "limitations",
        "non_claims",
    )
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
    assert _payload_keys(payload).isdisjoint(forbidden_fields)
    assert all(not hasattr(item, field_name) for field_name in forbidden_fields)


def test_module_imports_no_forbidden_vendor_network_or_trading_modules() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []


def test_module_makes_no_io_network_persistence_runtime_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_module_text_has_no_real_world_path_secret_or_trading_literals() -> None:
    source = _source_text()
    lowered = source.lower()
    upper_source = source.upper()

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


def dossier_fixture() -> CandidateResearchResultDossier:
    return build_synthetic_candidate_research_result_dossier()


def _valid_constructor_payload(
    dossier: CandidateResearchResultDossier,
) -> dict[str, object]:
    item = build_candidate_research_brief_item(dossier)
    return {
        "dossier": dossier,
        "item_type": item.item_type,
        "status": item.status,
        "headline": item.headline,
        "summary_points": item.summary_points,
        "limitations": item.limitations,
        "non_claims": item.non_claims,
    }


def _is_clean_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


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


def _forbidden_payload_fields() -> set[str]:
    return {
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


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


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
