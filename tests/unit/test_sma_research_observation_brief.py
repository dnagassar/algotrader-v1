from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.sma_research_observation import (
    SmaResearchObservation,
    SmaResearchPricePoint,
    build_sma_research_observation,
)
from algotrader.research.sma_research_observation_brief import (
    SMA_RESEARCH_OBSERVATION_MECHANICAL_STATES,
    SmaResearchObservationBriefItem,
    build_sma_research_observation_brief_item,
)
from tests.fixtures.sma_research_observation import (
    build_synthetic_insufficient_history_sma_research_observation,
    build_synthetic_sma_research_observation,
    expected_synthetic_insufficient_history_sma_research_observation_dict,
    expected_synthetic_sma_research_observation_dict,
)


MODULE_PATH = Path("src/algotrader/research/sma_research_observation_brief.py")


def _join(*parts: str) -> str:
    return "".join(parts)


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_PRIMARY_HEADLINE = (
    "SMA observation SYNTH_ETF 2026-01-20: above_sma_observation."
)
_PRIMARY_SUMMARY = (
    "SMA observation metadata records above_sma_observation for SYNTH_ETF "
    "as of 2026-01-20 with window 3, 3 eligible sample(s), 1 later sample(s) "
    "ignored, latest close 110.00, SMA 100.00, distance 10.00, and distance "
    "pct 0.1."
)
_INSUFFICIENT_HEADLINE = (
    "SMA observation SYNTH_ETF 2026-01-20: insufficient_history."
)
_INSUFFICIENT_SUMMARY = (
    "SMA observation metadata records insufficient_history for SYNTH_ETF "
    "as of 2026-01-20 with window 3, 2 eligible sample(s), 1 later sample(s) "
    "ignored, latest close 101.00, SMA none, distance none, and distance "
    "pct none."
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "algotrader.errors",
    "algotrader.research.sma_research_observation",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    _join("algotrader.", "bro", "ker"),
    _join("algotrader.", "bro", "kers"),
    "algotrader.cli",
    "algotrader.dashboard",
    "algotrader.execution",
    _join("algotrader.", "l", "lm"),
    _join("algotrader.", "l", "lms"),
    "algotrader.ml",
    "algotrader.orchestration",
    _join("algotrader.", "persist", "ence"),
    _join("algotrader.", "port", "folio"),
    "algotrader.risk",
    _join("algotrader.", "run", "time"),
    _join("algotrader.", "sche", "duler"),
    "algotrader.screener",
    _join("algotrader.", "sig", "nals"),
    _join("al", "paca"),
    _join("al", "paca_trade_a", "pi"),
    "anthropic",
    _join("cre", "dential"),
    _join("data", "base"),
    "duckdb",
    "httpx",
    "ipynb",
    "joblib",
    "keras",
    "langchain",
    "langgraph",
    _join("l", "lm"),
    _join("mas", "sive"),
    _join("net", "work"),
    _join("num", "py"),
    "openai",
    "os",
    _join("pan", "das"),
    "pathlib",
    _join("poly", "gon"),
    _join("quant", "connect"),
    _join("re", "quests"),
    _join("so", "cket"),
    "sqlmodel",
    "subprocess",
    "tensorflow",
    "torch",
    "typer",
    "urllib",
    "vectorbt",
    "xgboost",
    _join("y", "finance"),
)
_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "Path",
    _join("cli", "ent"),
    _join("con", "nect"),
    _join("create_", "or", "der"),
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    _join("down", "load"),
    "eval",
    "exec",
    "exists",
    "from_dict",
    "from_file",
    "getenv",
    "glob",
    "import_module",
    _join("ing", "est"),
    "is_file",
    "iterdir",
    "json.dump",
    "json.load",
    "load",
    "mkdir",
    _join("op", "en"),
    "os.environ.get",
    "os.getenv",
    "post",
    _join("re", "ad"),
    "read_bytes",
    "read_csv",
    "read_text",
    _join("re", "quest"),
    _join("re", "quests.get"),
    "rglob",
    _join("sco", "re"),
    "save",
    _join("so", "cket.socket"),
    "stat",
    _join("sub", "mit_", "or", "der"),
    "time.time",
    "to_file",
    "to_sql",
    "urlopen",
    "walk",
    _join("wri", "te"),
    "write_text",
}
_FORBIDDEN_SOURCE_TOKENS = (
    _join("app", "roved"),
    _join("app", "roval"),
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("bro", "ker"),
    "account",
    _join("or", "der"),
    "fill",
    _join("allo", "cation"),
    _join("port", "folio"),
    _join("mut", "ation"),
    _join("pa", "per"),
    _join("li", "ve"),
    _join("read", "iness"),
    "paper_ready",
    "paper-ready",
    "live_ready",
    "live-ready",
    "trading_ready",
    "trading-ready",
    _join("action", "able"),
    _join("file", "_io"),
    _join("net", "work"),
    _join("so", "cket"),
    "vendor",
    _join("cre", "dential"),
    _join("run", "time"),
    _join("sche", "duler"),
    "dashboard",
    "notebook",
    _join("l", "lm"),
    "agent",
    _join("ra", "nking"),
    _join("sco", "ring"),
    _join("capital ", "authority"),
    _join("tra", "ding authority"),
)
_FORBIDDEN_PAYLOAD_KEYS = {
    "account",
    "accounts",
    "actionable",
    _join("allo", "cation"),
    _join("allo", "cations"),
    _join("allo", "cation_authority"),
    "approved",
    "buy",
    _join("bro", "ker"),
    _join("bro", "ker_authority"),
    "evaluator",
    "fill",
    "fills",
    "hold",
    "live_authorized",
    "live_probe_eligible",
    _join("or", "der"),
    _join("or", "ders"),
    _join("or", "der_authority"),
    "paper_eligible",
    _join("port", "folio"),
    _join("port", "folios"),
    "ranking",
    _join("recomm", "endation"),
    "readiness",
    "score",
    "scoring",
    "sell",
    "signal",
    _join("tra", "ding_authority"),
    "trading_ready",
}


def test_above_sma_fixture_builds_expected_brief_item() -> None:
    observation = build_synthetic_sma_research_observation()
    item = build_sma_research_observation_brief_item(observation)

    assert type(item) is SmaResearchObservationBriefItem
    assert item.source_observation is observation
    assert item.to_dict() == _expected_primary_brief_dict()


def test_insufficient_history_fixture_builds_expected_brief_item() -> None:
    observation = build_synthetic_insufficient_history_sma_research_observation()
    item = build_sma_research_observation_brief_item(observation)

    assert type(item) is SmaResearchObservationBriefItem
    assert item.source_observation is observation
    assert item.to_dict() == _expected_insufficient_brief_dict()


def test_exact_source_observation_identity_is_preserved() -> None:
    observation = build_synthetic_sma_research_observation()
    item = build_sma_research_observation_brief_item(observation)

    assert item.source_observation is observation
    assert item.to_dict()["source_observation"] == observation.to_dict()


def test_exact_source_type_validation_rejects_invalid_inputs() -> None:
    class Lookalike:
        def to_dict(self) -> dict[str, object]:
            return expected_synthetic_sma_research_observation_dict()

    class ObservationSubclass(SmaResearchObservation):
        pass

    observation = build_synthetic_sma_research_observation()
    subclass = ObservationSubclass(
        observation_type=observation.observation_type,
        status=observation.status,
        authority=observation.authority,
        capital_authority=observation.capital_authority,
        symbol=observation.symbol,
        as_of=observation.as_of,
        window=observation.window,
        sample_count=observation.sample_count,
        eligible_sample_count=observation.eligible_sample_count,
        ignored_future_sample_count=observation.ignored_future_sample_count,
        latest_close=observation.latest_close,
        sma_value=observation.sma_value,
        distance_from_sma=observation.distance_from_sma,
        distance_from_sma_pct=observation.distance_from_sma_pct,
        position_vs_sma=observation.position_vs_sma,
        limitations=observation.limitations,
        non_claims=observation.non_claims,
    )

    for value in (None, object(), {}, Lookalike(), subclass):
        with pytest.raises(ValidationError, match="source_observation"):
            build_sma_research_observation_brief_item(value)


def test_direct_construction_rejects_mismatched_or_malformed_values() -> None:
    payload = _direct_payload(build_synthetic_sma_research_observation())

    for field_name, value in (
        ("item_type", "other"),
        ("status", "other"),
        ("authority", "other"),
        ("capital_authority", True),
        ("headline", _join("app", "roved metadata")),
        ("summary", _join("b", "uy metadata")),
        ("mechanical_state", "other"),
        ("limitations", (_join("bro", "ker metadata"),)),
        ("non_claims", ("positive claim",)),
    ):
        mutated = dict(payload)
        mutated[field_name] = value
        with pytest.raises(ValidationError):
            SmaResearchObservationBriefItem(**mutated)


def test_fixed_advisory_metadata_is_pinned() -> None:
    item = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    )

    assert item.item_type == "sma_research_observation_brief_item"
    assert item.status == "candidate_only"
    assert item.authority == "advisory_only"
    assert item.capital_authority is False
    assert item.to_dict()["item_type"] == "sma_research_observation_brief_item"
    assert item.to_dict()["status"] == "candidate_only"
    assert item.to_dict()["authority"] == "advisory_only"
    assert item.to_dict()["capital_authority"] is False


def test_mechanical_state_mapping_is_deterministic() -> None:
    cases = (
        (_position_observation("9", "10", "11"), "above_sma_observation"),
        (_position_observation("11", "10", "9"), "below_sma_observation"),
        (_position_observation("10", "10", "10"), "equal_sma_observation"),
        (
            build_synthetic_insufficient_history_sma_research_observation(),
            "insufficient_history",
        ),
    )

    assert set(SMA_RESEARCH_OBSERVATION_MECHANICAL_STATES) == {
        "above_sma_observation",
        "below_sma_observation",
        "equal_sma_observation",
        "insufficient_history",
    }
    for observation, expected_state in cases:
        item = build_sma_research_observation_brief_item(observation)
        assert item.mechanical_state == expected_state
        assert item.to_dict()["mechanical_state"] == expected_state


def test_headline_and_summary_are_deterministic_and_non_actionable() -> None:
    first = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    )
    second = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    )

    assert first.headline == second.headline == _PRIMARY_HEADLINE
    assert first.summary == second.summary == _PRIMARY_SUMMARY
    for text in (first.headline, first.summary):
        lowered = text.lower()
        assert "not " not in lowered
        assert not any(token in lowered for token in _positive_action_tokens())


def test_limitations_and_non_claims_carry_forward_with_first_seen_dedupe() -> None:
    observation = _observation_with_duplicate_metadata()
    item = build_sma_research_observation_brief_item(observation)

    assert item.limitations == (
        "synthetic broad ETF close series for fixture mechanics only",
        "fixed date samples with later samples ignored by the builder",
    )
    assert item.non_claims == tuple(dict.fromkeys(observation.non_claims))
    assert item.to_dict()["limitations"] == list(item.limitations)
    assert item.to_dict()["non_claims"] == list(item.non_claims)


def test_to_dict_is_primitive_only_and_deterministic() -> None:
    first = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    ).to_dict()
    second = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    ).to_dict()

    assert first == second == _expected_primary_brief_dict()
    assert tuple(first) == tuple(_expected_primary_brief_dict())
    assert _primitive_only(first)
    assert first["source_observation"] is not second["source_observation"]
    assert first["limitations"] is not second["limitations"]
    assert first["non_claims"] is not second["non_claims"]

    first["limitations"].append("mutated primitive copy")
    first["non_claims"].append("not mutated primitive copy")

    assert second == _expected_primary_brief_dict()


def test_repeated_construction_is_byte_for_byte_deterministic_under_compact_json() -> None:
    first = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    )
    second = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    )
    first_json = _compact_json_bytes(first)
    second_json = _compact_json_bytes(second)

    assert first == second
    assert first is not second
    assert first_json == second_json
    assert first_json == json.dumps(
        _expected_primary_brief_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert json.loads(first_json.decode("utf-8")) == _expected_primary_brief_dict()


def test_source_observation_to_dict_is_unchanged_by_brief_construction() -> None:
    observation = build_synthetic_sma_research_observation()
    before = observation.to_dict()
    item = build_sma_research_observation_brief_item(observation)
    after_build = observation.to_dict()
    payload = item.to_dict()
    after_serialize = observation.to_dict()

    assert before == expected_synthetic_sma_research_observation_dict()
    assert after_build == before
    assert payload["source_observation"] == before
    assert after_serialize == before


def test_object_is_frozen_and_slotted() -> None:
    item = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    )

    assert hasattr(SmaResearchObservationBriefItem, "__slots__")
    assert tuple(field.name for field in fields(SmaResearchObservationBriefItem)) == (
        "item_type",
        "status",
        "authority",
        "capital_authority",
        "headline",
        "summary",
        "mechanical_state",
        "source_observation",
        "limitations",
        "non_claims",
    )
    with pytest.raises(FrozenInstanceError):
        item.headline = "other"
    with pytest.raises((AttributeError, TypeError)):
        item.extra_field = "not allowed"


def test_no_from_dict_exists() -> None:
    item = build_sma_research_observation_brief_item(
        build_synthetic_sma_research_observation()
    )

    assert not hasattr(SmaResearchObservationBriefItem, "from_dict")
    assert not hasattr(item, "from_dict")
    assert "from_dict" not in _function_names()
    assert "from_dict" not in _call_names()


def test_public_payload_keys_contain_no_action_or_trading_authority_fields() -> None:
    payloads = (
        build_sma_research_observation_brief_item(
            build_synthetic_sma_research_observation()
        ).to_dict(),
        build_sma_research_observation_brief_item(
            build_synthetic_insufficient_history_sma_research_observation()
        ).to_dict(),
    )

    for payload in payloads:
        assert _FORBIDDEN_PAYLOAD_KEYS.isdisjoint(_payload_keys(payload))


def test_production_module_imports_no_tests_or_fixtures() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert all(not module_name.startswith("tests") for module_name in imports)
    assert "tests.fixtures" not in imports


def test_production_module_has_no_forbidden_imports_calls_or_literals() -> None:
    imports = _import_references()
    call_names = _call_names()
    lowered = _source_text().lower()

    assert [
        module_name
        for module_name in imports
        if _matches_forbidden_prefix(module_name, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert [
        token for token in _FORBIDDEN_SOURCE_TOKENS if token in lowered
    ] == []


def _expected_primary_brief_dict() -> dict[str, object]:
    source_observation = expected_synthetic_sma_research_observation_dict()
    return {
        "item_type": "sma_research_observation_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "headline": _PRIMARY_HEADLINE,
        "summary": _PRIMARY_SUMMARY,
        "mechanical_state": "above_sma_observation",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def _expected_insufficient_brief_dict() -> dict[str, object]:
    source_observation = (
        expected_synthetic_insufficient_history_sma_research_observation_dict()
    )
    return {
        "item_type": "sma_research_observation_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "headline": _INSUFFICIENT_HEADLINE,
        "summary": _INSUFFICIENT_SUMMARY,
        "mechanical_state": "insufficient_history",
        "source_observation": source_observation,
        "limitations": list(source_observation["limitations"]),
        "non_claims": list(source_observation["non_claims"]),
    }


def _direct_payload(observation: SmaResearchObservation) -> dict[str, object]:
    return {
        "item_type": "sma_research_observation_brief_item",
        "status": "candidate_only",
        "authority": "advisory_only",
        "capital_authority": False,
        "headline": _PRIMARY_HEADLINE,
        "summary": _PRIMARY_SUMMARY,
        "mechanical_state": "above_sma_observation",
        "source_observation": observation,
        "limitations": observation.limitations,
        "non_claims": observation.non_claims,
    }


def _position_observation(
    first_close: str,
    second_close: str,
    third_close: str,
) -> SmaResearchObservation:
    return build_sma_research_observation(
        "SYNTH_ETF",
        "2026-01-20",
        3,
        (
            SmaResearchPricePoint("2026-01-18", Decimal(first_close)),
            SmaResearchPricePoint("2026-01-19", Decimal(second_close)),
            SmaResearchPricePoint("2026-01-20", Decimal(third_close)),
        ),
        limitations=("synthetic mechanics mapping only",),
    )


def _observation_with_duplicate_metadata() -> SmaResearchObservation:
    source = build_synthetic_sma_research_observation()
    return SmaResearchObservation(
        observation_type=source.observation_type,
        status=source.status,
        authority=source.authority,
        capital_authority=source.capital_authority,
        symbol=source.symbol,
        as_of=source.as_of,
        window=source.window,
        sample_count=source.sample_count,
        eligible_sample_count=source.eligible_sample_count,
        ignored_future_sample_count=source.ignored_future_sample_count,
        latest_close=source.latest_close,
        sma_value=source.sma_value,
        distance_from_sma=source.distance_from_sma,
        distance_from_sma_pct=source.distance_from_sma_pct,
        position_vs_sma=source.position_vs_sma,
        limitations=(
            "synthetic broad ETF close series for fixture mechanics only",
            "synthetic broad ETF close series for fixture mechanics only",
            "fixed date samples with later samples ignored by the builder",
        ),
        non_claims=(*source.non_claims, source.non_claims[0]),
    )


def _positive_action_tokens() -> tuple[str, ...]:
    return (
        _join("app", "roved"),
        _join("recomm", "end"),
        _join("sig", "nal"),
        _join("evalu", "ator"),
        _join("or", "der"),
        _join("allo", "cation"),
        _join("bro", "ker"),
        _join("port", "folio"),
        "paper_ready",
        "live_ready",
        "trading_ready",
        _join("action", "able"),
        "buy",
        "sell",
        "hold",
        "rank",
        "score",
    )


def _compact_json_bytes(item: SmaResearchObservationBriefItem) -> bytes:
    return json.dumps(
        item.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _primitive_only(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if isinstance(value, list):
        return all(_primitive_only(item) for item in value)
    if isinstance(value, dict):
        return all(type(key) is str and _primitive_only(item) for key, item in value.items())

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


def _source_text() -> str:
    return MODULE_PATH.read_text(encoding="utf-8")


def _tree() -> ast.AST:
    return ast.parse(_source_text(), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


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


def _function_names() -> set[str]:
    return {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == forbidden_prefix
        or module_name.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
