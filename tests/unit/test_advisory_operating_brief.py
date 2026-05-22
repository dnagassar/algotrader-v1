from __future__ import annotations

import ast
import json
import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import algotrader.research as research_package
from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief import (
    AdvisoryOperatingBrief,
    build_advisory_operating_brief,
)
from algotrader.research.candidate_research_brief import CandidateResearchBrief
from algotrader.research.research_return_input_provenance import (
    build_research_return_input_provenance,
)
from tests.fixtures.candidate_research_brief import (
    build_synthetic_candidate_research_brief,
)


def _s(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


MODULE_PATH = Path("src/algotrader/research/advisory_operating_brief.py")
_SYNTHETIC_FIXTURE_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)

_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.candidate_research_brief",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
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


def test_builds_operating_brief_from_phase_139_synthetic_candidate_brief() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()

    operating_brief = build_advisory_operating_brief((candidate_brief,))

    assert isinstance(operating_brief, AdvisoryOperatingBrief)
    assert operating_brief.candidate_research_briefs == (candidate_brief,)
    assert operating_brief.candidate_research_briefs[0] is candidate_brief
    assert isinstance(
        operating_brief.candidate_research_briefs[0],
        CandidateResearchBrief,
    )


def test_operating_brief_is_frozen_and_slotted() -> None:
    operating_brief = build_advisory_operating_brief(
        (build_synthetic_candidate_research_brief(),)
    )

    assert hasattr(AdvisoryOperatingBrief, "__slots__")
    assert not hasattr(operating_brief, "__dict__")
    with pytest.raises(FrozenInstanceError):
        operating_brief.title = "changed"


def test_builder_preserves_candidate_brief_identity_and_input_sequence() -> None:
    first = _brief_variant("Candidate research brief metadata one")
    second = _brief_variant("Candidate research brief metadata two")

    operating_brief = build_advisory_operating_brief((first, second))

    assert operating_brief.candidate_research_briefs[0] is first
    assert operating_brief.candidate_research_briefs[1] is second
    assert tuple(
        brief.title for brief in operating_brief.candidate_research_briefs
    ) == (
        first.title,
        second.title,
    )
    assert [
        brief_payload["title"]
        for brief_payload in operating_brief.to_dict()["candidate_research_briefs"]
    ] == [first.title, second.title]


def test_type_status_title_limitations_and_non_claims_are_deterministic() -> None:
    first = build_advisory_operating_brief(
        (build_synthetic_candidate_research_brief(),)
    )
    second = build_advisory_operating_brief(
        (build_synthetic_candidate_research_brief(),)
    )

    assert (
        first.operating_brief_type
        == second.operating_brief_type
        == "advisory_operating_brief"
    )
    assert first.status == second.status == "candidate_only"
    assert first.title == second.title == "Candidate research operating brief metadata"
    assert _is_clean_string(first.title)
    _assert_non_actionable((first.title,))
    assert first.limitations == second.limitations
    assert first.non_claims == second.non_claims
    assert first.limitations[:3] == (
        "metadata-only container for existing candidate research briefs",
        "does not create research, compute metrics, or mutate brief payloads",
        "advisory grouping for future operating brief surfaces only",
    )
    assert first.limitations
    assert first.non_claims


def test_limitations_non_claims_and_required_non_claims_are_carried_forward() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    operating_brief = build_advisory_operating_brief((candidate_brief,))
    payload = operating_brief.to_dict()

    assert all(
        value in operating_brief.limitations for value in candidate_brief.limitations
    )
    assert all(value in operating_brief.non_claims for value in candidate_brief.non_claims)
    assert payload["limitations"] == list(operating_brief.limitations)
    assert payload["non_claims"] == list(operating_brief.non_claims)
    assert set(_REQUIRED_NON_CLAIMS).issubset(operating_brief.non_claims)
    assert all(value.startswith("not ") for value in operating_brief.non_claims)


def test_direct_construction_accepts_valid_operating_brief_payload() -> None:
    payload = _valid_constructor_payload()

    operating_brief = AdvisoryOperatingBrief(**payload)

    assert operating_brief.operating_brief_type == "advisory_operating_brief"
    assert operating_brief.status == "candidate_only"
    assert operating_brief.candidate_research_briefs == payload[
        "candidate_research_briefs"
    ]


def test_builder_and_direct_construction_reject_empty_briefs() -> None:
    with pytest.raises(ValidationError, match="candidate_research_briefs"):
        build_advisory_operating_brief(())

    payload = _valid_constructor_payload()
    payload["candidate_research_briefs"] = ()
    with pytest.raises(ValidationError, match="candidate_research_briefs"):
        AdvisoryOperatingBrief(**payload)


@pytest.mark.parametrize("value", (object(), None, "not a candidate brief"))
def test_builder_and_direct_construction_reject_non_brief_inputs(
    value: object,
) -> None:
    with pytest.raises(ValidationError, match="CandidateResearchBrief"):
        build_advisory_operating_brief((value,))

    payload = _valid_constructor_payload()
    payload["candidate_research_briefs"] = (value,)
    with pytest.raises(ValidationError, match="CandidateResearchBrief"):
        AdvisoryOperatingBrief(**payload)


def test_builder_rejects_non_iterable_input() -> None:
    with pytest.raises(ValidationError, match="iterable"):
        build_advisory_operating_brief(None)


def test_direct_construction_rejects_mutable_brief_collections() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    payload = _valid_constructor_payload((candidate_brief,))
    payload["candidate_research_briefs"] = [candidate_brief]

    with pytest.raises(ValidationError, match="candidate_research_briefs"):
        AdvisoryOperatingBrief(**payload)


@pytest.mark.parametrize(
    "operating_brief_type",
    (
        "",
        "candidate_research_brief",
        "operating_brief",
        "validated_advisory_operating_brief",
    ),
)
def test_direct_construction_rejects_forbidden_operating_brief_types(
    operating_brief_type: str,
) -> None:
    payload = _valid_constructor_payload()
    payload["operating_brief_type"] = operating_brief_type

    with pytest.raises(ValidationError, match="operating_brief_type"):
        AdvisoryOperatingBrief(**payload)


def test_direct_construction_rejects_nested_forbidden_brief_type() -> None:
    payload = _valid_constructor_payload()
    payload["candidate_research_briefs"] = (
        _unsafe_candidate_brief(brief_type="validated_candidate_research_brief"),
    )

    with pytest.raises(ValidationError, match="brief_type"):
        AdvisoryOperatingBrief(**payload)


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
    payload = _valid_constructor_payload()
    payload["status"] = status

    with pytest.raises(ValidationError, match="status"):
        AdvisoryOperatingBrief(**payload)


def test_direct_construction_rejects_nested_approval_like_brief_status() -> None:
    payload = _valid_constructor_payload()
    payload["candidate_research_briefs"] = (
        _unsafe_candidate_brief(status="approved"),
    )

    with pytest.raises(ValidationError, match="status"):
        AdvisoryOperatingBrief(**payload)


def test_builder_and_direct_construction_reject_duplicate_brief_identities() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()

    with pytest.raises(ValidationError, match="duplicate"):
        build_advisory_operating_brief((candidate_brief, candidate_brief))

    payload = _valid_constructor_payload((candidate_brief,))
    payload["candidate_research_briefs"] = (candidate_brief, candidate_brief)
    with pytest.raises(ValidationError, match="duplicate"):
        AdvisoryOperatingBrief(**payload)


@pytest.mark.parametrize("title", ("", " ", " title", "title ", None, 3))
def test_direct_construction_rejects_empty_or_malformed_title(title: object) -> None:
    payload = _valid_constructor_payload()
    payload["title"] = title

    with pytest.raises(ValidationError, match="title"):
        AdvisoryOperatingBrief(**payload)


def test_direct_construction_rejects_empty_or_malformed_limitations() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()

    for limitations in (
        (),
        list(candidate_brief.limitations),
        "limitation",
        ("valid", ""),
        ("valid", " "),
        ("valid", " trailing "),
        ("valid", 1),
        ("metadata-only container for existing candidate research briefs",),
        None,
    ):
        payload = _valid_constructor_payload((candidate_brief,))
        payload["limitations"] = limitations
        with pytest.raises(ValidationError, match="limitations"):
            AdvisoryOperatingBrief(**payload)


def test_direct_construction_rejects_empty_or_malformed_non_claims() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()

    for non_claims in (
        (),
        list(candidate_brief.non_claims),
        "non-claim",
        ("not valid", ""),
        ("not valid", " "),
        ("not valid", " trailing "),
        ("not valid", 1),
        candidate_brief.non_claims[:-1],
        candidate_brief.non_claims + ("positive candidate claim",),
        None,
    ):
        payload = _valid_constructor_payload((candidate_brief,))
        payload["non_claims"] = non_claims
        with pytest.raises(ValidationError, match="non_claims|negative"):
            AdvisoryOperatingBrief(**payload)


def test_to_dict_is_primitive_only_deterministic_and_does_not_alias_lists() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    operating_brief = build_advisory_operating_brief((candidate_brief,))

    payload = operating_brief.to_dict()

    assert not hasattr(AdvisoryOperatingBrief, "from_dict")
    assert payload == operating_brief.to_dict()
    assert payload == {
        "operating_brief_type": "advisory_operating_brief",
        "status": "candidate_only",
        "title": operating_brief.title,
        "candidate_research_brief_count": 1,
        "candidate_research_briefs": [candidate_brief.to_dict()],
        "limitations": list(operating_brief.limitations),
        "non_claims": list(operating_brief.non_claims),
    }
    _assert_primitive_only(payload)
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload

    payload["candidate_research_briefs"].append(candidate_brief.to_dict())
    payload["limitations"].append("mutated primitive copy")
    payload["non_claims"].append("not mutated primitive source")

    assert operating_brief.to_dict()["candidate_research_briefs"] == [
        candidate_brief.to_dict()
    ]
    assert operating_brief.to_dict()["limitations"] == list(
        operating_brief.limitations
    )
    assert operating_brief.to_dict()["non_claims"] == list(
        operating_brief.non_claims
    )


def test_repeated_builder_calls_are_deterministic() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()

    first = build_advisory_operating_brief((candidate_brief,))
    second = build_advisory_operating_brief((candidate_brief,))
    third = build_advisory_operating_brief(
        (build_synthetic_candidate_research_brief(),)
    )

    assert first is not second
    assert first.candidate_research_briefs[0] is second.candidate_research_briefs[
        0
    ] is candidate_brief
    assert first.to_dict() == second.to_dict() == third.to_dict()
    assert _sorted_compact_json(first.to_dict()) == _sorted_compact_json(
        second.to_dict()
    )


def test_builder_and_serialization_do_not_mutate_candidate_briefs() -> None:
    candidate_brief = build_synthetic_candidate_research_brief()
    brief_payload = candidate_brief.to_dict()
    section_payload = candidate_brief.sections[0].to_dict()
    item_payload = candidate_brief.sections[0].items[0].to_dict()
    identity_snapshot = (
        id(candidate_brief),
        id(candidate_brief.sections),
        id(candidate_brief.sections[0]),
        id(candidate_brief.sections[0].items),
        id(candidate_brief.sections[0].items[0]),
        id(candidate_brief.sections[0].items[0].dossier),
        id(candidate_brief.limitations),
        id(candidate_brief.non_claims),
    )

    operating_brief = build_advisory_operating_brief((candidate_brief,))
    operating_payload = operating_brief.to_dict()
    operating_payload["candidate_research_briefs"].append(candidate_brief.to_dict())
    operating_payload["limitations"].append("mutated primitive copy")
    operating_payload["non_claims"].append("not mutated primitive source")

    assert candidate_brief.to_dict() == brief_payload
    assert candidate_brief.sections[0].to_dict() == section_payload
    assert candidate_brief.sections[0].items[0].to_dict() == item_payload
    assert (
        id(candidate_brief),
        id(candidate_brief.sections),
        id(candidate_brief.sections[0]),
        id(candidate_brief.sections[0].items),
        id(candidate_brief.sections[0].items[0]),
        id(candidate_brief.sections[0].items[0].dossier),
        id(candidate_brief.limitations),
        id(candidate_brief.non_claims),
    ) == identity_snapshot


def test_nested_phase_123_digest_and_phase_127_141_provenance_remain_visible() -> None:
    operating_brief = build_advisory_operating_brief(
        (build_synthetic_candidate_research_brief(),)
    )
    item = operating_brief.candidate_research_briefs[0].sections[0].items[0]
    provenance = build_research_return_input_provenance(item.dossier.package)
    item_payload = _single_item_payload(operating_brief.to_dict())

    assert item_payload["package_fingerprint"] == _SYNTHETIC_FIXTURE_DIGEST
    assert item_payload["package_snapshot_id"] == provenance.snapshot_id
    assert item_payload["result_snapshot_manifest_fixture_id"] == (
        provenance.manifest_fixture_id
    )
    assert item_payload["result_snapshot_manifest_checksum"] == (
        provenance.manifest_checksum
    )
    assert provenance.manifest_fixture_id == item.dossier.package.snapshot.snapshot_id
    assert provenance.manifest_checksum == f"sha256:{item.dossier.package.fingerprint}"


def test_operating_brief_introduces_no_disallowed_fields_or_reexport() -> None:
    operating_brief = build_advisory_operating_brief(
        (build_synthetic_candidate_research_brief(),)
    )
    payload = operating_brief.to_dict()
    forbidden_fields = _forbidden_payload_fields()

    assert tuple(field.name for field in fields(AdvisoryOperatingBrief)) == (
        "operating_brief_type",
        "status",
        "title",
        "candidate_research_briefs",
        "limitations",
        "non_claims",
    )
    assert tuple(payload) == (
        "operating_brief_type",
        "status",
        "title",
        "candidate_research_brief_count",
        "candidate_research_briefs",
        "limitations",
        "non_claims",
    )
    assert _payload_keys(payload).isdisjoint(forbidden_fields)
    assert all(not hasattr(operating_brief, field_name) for field_name in forbidden_fields)
    assert not hasattr(research_package, "AdvisoryOperatingBrief")
    assert not hasattr(research_package, "build_advisory_operating_brief")


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


def _brief_variant(title: str) -> CandidateResearchBrief:
    candidate_brief = build_synthetic_candidate_research_brief()
    return CandidateResearchBrief(
        brief_type=candidate_brief.brief_type,
        status=candidate_brief.status,
        title=title,
        sections=candidate_brief.sections,
        limitations=candidate_brief.limitations,
        non_claims=candidate_brief.non_claims,
    )


def _unsafe_candidate_brief(**overrides: object) -> CandidateResearchBrief:
    candidate_brief = build_synthetic_candidate_research_brief()
    values = {
        "brief_type": candidate_brief.brief_type,
        "status": candidate_brief.status,
        "title": candidate_brief.title,
        "sections": candidate_brief.sections,
        "limitations": candidate_brief.limitations,
        "non_claims": candidate_brief.non_claims,
    }
    values.update(overrides)
    unsafe = object.__new__(CandidateResearchBrief)
    for field_name, value in values.items():
        object.__setattr__(unsafe, field_name, value)
    return unsafe


def _valid_constructor_payload(
    candidate_research_briefs: tuple[CandidateResearchBrief, ...] | None = None,
) -> dict[str, object]:
    checked_briefs = candidate_research_briefs or (
        build_synthetic_candidate_research_brief(),
    )
    operating_brief = build_advisory_operating_brief(checked_briefs)
    return {
        "operating_brief_type": operating_brief.operating_brief_type,
        "status": operating_brief.status,
        "title": operating_brief.title,
        "candidate_research_briefs": operating_brief.candidate_research_briefs,
        "limitations": operating_brief.limitations,
        "non_claims": operating_brief.non_claims,
    }


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
        "priority",
        "prioritized",
        "rank",
        "ranking",
        _s("recommendation"),
        _s("recommendations"),
        "ready",
        _s("run", "time"),
        _s("run", "times"),
        "score",
        "scoring",
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
        _s("recommend"),
        _s("recommendation"),
        _s("recommendations"),
        _s("po", "sition"),
        _s("po", "sitions"),
        "prioritize",
        "prioritized",
        "rank",
        "ranking",
        _s("run", "time"),
        "score",
        "scoring",
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("tra", "ding"),
        _s("tra", "de"),
        _s("tra", "des"),
    }
