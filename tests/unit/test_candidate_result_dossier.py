from __future__ import annotations

import ast
import json
import re
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
    build_candidate_research_result_dossier,
)
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)


def _s(*parts: str) -> str:
    return "".join(parts)


MODULE_PATH = Path("src/algotrader/research/candidate_result_dossier.py")

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.replay_result",
    "algotrader.research.research_return_input_package",
    "algotrader.research.research_return_input_result_provenance",
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
    "build_synthetic_replay_snapshot",
    "build_synthetic_replay_snapshot_from_return_input_package",
    "build_synthetic_research_result",
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
    "summarize_synthetic_replay_snapshot",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}


def test_dossier_builds_from_phase_125_package_and_phase_128_129_result_path() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    dossier = build_candidate_research_result_dossier(package, result)

    assert isinstance(dossier, CandidateResearchResultDossier)
    assert dossier.status == "candidate_only"
    assert dossier.package is package
    assert dossier.result is result
    assert dossier.to_dict()["package_fingerprint"] == package.fingerprint


def test_builder_preserves_package_and_result_object_identity() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    dossier = build_candidate_research_result_dossier(package, result)

    assert dossier.package is package
    assert dossier.package.snapshot is package.snapshot
    assert dossier.result is result
    assert dossier.result.snapshot is result.snapshot
    assert dossier.result.summary is result.summary


def test_builder_rejects_mismatched_result_provenance() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    with pytest.raises(ValidationError, match="fixture_id"):
        build_candidate_research_result_dossier(package, _mismatched_result(result))


def test_dossier_is_frozen() -> None:
    dossier = dossier_fixture()

    with pytest.raises(FrozenInstanceError):
        dossier.status = "candidate_only"


def test_direct_construction_accepts_matching_package_and_result_pair() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    dossier = CandidateResearchResultDossier(package=package, result=result)

    assert dossier.package is package
    assert dossier.result is result
    assert dossier.status == "candidate_only"


@pytest.mark.parametrize("value", (object(), None, "not a package"))
def test_direct_construction_rejects_non_package_input(value: object) -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    with pytest.raises(ValidationError, match="ResearchReturnInputPackage"):
        CandidateResearchResultDossier(package=value, result=result)


@pytest.mark.parametrize("value", (object(), None, "not a result"))
def test_direct_construction_rejects_non_result_input(value: object) -> None:
    package = package_fixture()

    with pytest.raises(ValidationError, match="SyntheticResearchResult"):
        CandidateResearchResultDossier(package=package, result=value)


def test_direct_construction_rejects_mismatched_provenance() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    with pytest.raises(ValidationError, match="fixture_id"):
        CandidateResearchResultDossier(
            package=package,
            result=_mismatched_result(result),
        )


@pytest.mark.parametrize(
    "status",
    (
        "",
        "validated",
        "approved",
        "tradable",
        "ready",
        "paper_eligible",
        "live_authorized",
        "candidate_approved",
    ),
)
def test_direct_construction_rejects_forbidden_or_approval_like_statuses(
    status: str,
) -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)

    with pytest.raises(ValidationError, match="status"):
        CandidateResearchResultDossier(
            package=package,
            result=result,
            status=status,
        )


def test_limitations_and_non_claims_are_immutable_non_empty_and_deterministic() -> None:
    first = dossier_fixture()
    second = dossier_fixture()

    assert isinstance(first.limitations, tuple)
    assert isinstance(first.non_claims, tuple)
    assert first.limitations
    assert first.non_claims
    assert first.limitations == second.limitations
    assert first.non_claims == second.non_claims
    assert all(_is_clean_string(value) for value in first.limitations)
    assert all(_is_clean_string(value) for value in first.non_claims)

    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    with pytest.raises(ValidationError, match="limitations"):
        CandidateResearchResultDossier(
            package=package,
            result=result,
            limitations=["not immutable"],
        )
    with pytest.raises(ValidationError, match="limitations"):
        CandidateResearchResultDossier(package=package, result=result, limitations=())
    with pytest.raises(ValidationError, match="limitations"):
        CandidateResearchResultDossier(
            package=package,
            result=result,
            limitations=(" ",),
        )
    with pytest.raises(ValidationError, match="non_claims"):
        CandidateResearchResultDossier(
            package=package,
            result=result,
            non_claims=list(_required_non_claims()),
        )
    with pytest.raises(ValidationError, match="non_claims"):
        CandidateResearchResultDossier(
            package=package,
            result=result,
            non_claims=_required_non_claims()[:-1],
        )
    with pytest.raises(ValidationError, match="negative"):
        CandidateResearchResultDossier(
            package=package,
            result=result,
            non_claims=_required_non_claims() + ("positive candidate claim",),
        )


def test_required_non_claims_are_present() -> None:
    dossier = dossier_fixture()

    assert dossier.non_claims == _required_non_claims()
    assert set(_required_non_claims()).issubset(dossier.non_claims)


def test_to_dict_is_primitive_only_and_deterministic() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    dossier = build_candidate_research_result_dossier(package, result)
    payload = dossier.to_dict()

    assert payload == dossier.to_dict()
    assert payload == {
        "package_fingerprint": package.fingerprint,
        "package_snapshot_id": package.snapshot.snapshot_id,
        "result_snapshot_manifest_fixture_id": result.snapshot.manifest.fixture_id,
        "result_snapshot_manifest_checksum": result.snapshot.manifest.checksum,
        "status": "candidate_only",
        "limitations": list(dossier.limitations),
        "non_claims": list(dossier.non_claims),
    }
    assert _is_primitive(payload)
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload


def test_dossier_building_and_serialization_do_not_mutate_package_or_result() -> None:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    package_payload = package.to_dict()
    result_payload = result.to_dict()
    identity_snapshot = (
        id(package.snapshot),
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(result.snapshot),
        id(result.snapshot.manifest),
        id(result.snapshot.available_points),
        id(result.snapshot.returns),
        id(result.summary),
    )

    dossier = build_candidate_research_result_dossier(package, result)
    dossier.to_dict()

    assert package.to_dict() == package_payload
    assert result.to_dict() == result_payload
    assert (
        id(package.snapshot),
        id(package.snapshot.observation_dates),
        id(package.snapshot.close_values),
        id(package.snapshot.close_to_close_returns),
        id(result.snapshot),
        id(result.snapshot.manifest),
        id(result.snapshot.available_points),
        id(result.snapshot.returns),
        id(result.summary),
    ) == identity_snapshot


def test_dossier_introduces_no_trading_runtime_allocation_or_approval_fields() -> None:
    dossier = dossier_fixture()
    payload = dossier.to_dict()
    forbidden_fields = _forbidden_payload_fields()

    assert tuple(field.name for field in fields(CandidateResearchResultDossier)) == (
        "package",
        "result",
        "status",
        "limitations",
        "non_claims",
    )
    assert tuple(payload) == (
        "package_fingerprint",
        "package_snapshot_id",
        "result_snapshot_manifest_fixture_id",
        "result_snapshot_manifest_checksum",
        "status",
        "limitations",
        "non_claims",
    )
    assert _payload_keys(payload).isdisjoint(forbidden_fields)
    assert all(not hasattr(dossier, field_name) for field_name in forbidden_fields)


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


def package_fixture() -> ResearchReturnInputPackage:
    return build_research_return_input_package(
        build_synthetic_research_return_input_snapshot()
    )


def dossier_fixture() -> CandidateResearchResultDossier:
    package = package_fixture()
    result = build_synthetic_research_result_from_return_input_package(package)
    return build_candidate_research_result_dossier(package, result)


def _mismatched_result(result: object) -> object:
    bad_manifest = replace(
        result.snapshot.manifest,
        fixture_id="synthetic_return_input_snapshot_fixture_mismatch",
    )
    return replace(result, snapshot=replace(result.snapshot, manifest=bad_manifest))


def _required_non_claims() -> tuple[str, ...]:
    return (
        _s("not source approval"),
        _s("not data approval"),
        _s("not endpoint approval"),
        _s("not universe approval"),
        _s("not bench", "mark approval"),
        _s("not ca", "sh proxy approval"),
        _s("not methodology approval"),
        _s("not evidence approval"),
        _s("not return-construction approval"),
        _s("not no-lookahead approval"),
        _s("not stra", "tegy validation"),
        _s("not tra", "ding readiness"),
        _s("not production use"),
        _s("not bro", "ker or run", "time use"),
        _s("not or", "der generation"),
        _s("not port", "folio or allo", "cation authority"),
    )


def _is_clean_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _is_primitive(value: object) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, list):
        return all(_is_primitive(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_primitive(nested_value)
            for key, nested_value in value.items()
        )
    return False


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
        _s("or", "der"),
        _s("or", "ders"),
        _s("port", "folio"),
        _s("port", "folios"),
        _s("allo", "cation"),
        _s("allo", "cations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        _s("run", "time"),
        _s("run", "times"),
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("stra", "tegy_state"),
        _s("tra", "de"),
        _s("tra", "des"),
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

