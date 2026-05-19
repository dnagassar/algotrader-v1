import ast
from collections.abc import Callable
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_scope import (
    APPROVAL_STATES,
    BENCHMARK_TYPES,
    CASH_PROXY_TYPES,
    REQUIRED_RESEARCH_SCOPE_NON_CLAIMS,
    SOURCE_TYPES,
    UNIVERSE_TYPES,
    ResearchBenchmarkCandidate,
    ResearchCashProxyCandidate,
    ResearchDataSourceCandidate,
    ResearchScopeSnapshot,
    ResearchUniverseCandidate,
)


MODULE_PATH = Path("src/algotrader/research/research_scope.py")

_FORBIDDEN_FIELD_NAMES = {
    "account",
    "allocation",
    "broker",
    "credential",
    "execution",
    "fill",
    "network",
    "order",
    "portfolio",
    "position",
    "runtime",
    "scheduler",
    "sdk",
    "target_weight",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.governance",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "csv",
    "database",
    "duckdb",
    "httpx",
    "ipynb",
    "json",
    "langchain",
    "langgraph",
    "llm",
    "market_data",
    "notebook",
    "numpy",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "persistence",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
    "DictReader",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "dump",
    "dumps",
    "environ.get",
    "fit",
    "getenv",
    "glob",
    "iterdir",
    "load",
    "loads",
    "makedirs",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read",
    "read_csv",
    "read_text",
    "request",
    "rglob",
    "scandir",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}


def valid_source_candidate(**overrides: object) -> ResearchDataSourceCandidate:
    values = {
        "source_id": "synthetic-source-candidate",
        "source_name": "Synthetic Source Candidate",
        "source_type": "synthetic",
        "approval_state": "candidate_only",
        "data_kind": "synthetic adjusted close metadata candidate",
        "terms_status": "not reviewed",
        "storage_policy": "metadata only",
        "adjustment_policy": "candidate only adjustment metadata",
        "revision_policy": "candidate only revision metadata",
        "blockers": ("source terms not reviewed",),
        "limitations": ("metadata only",),
        "required_follow_up": ("review source terms before use",),
        "non_claims": REQUIRED_RESEARCH_SCOPE_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchDataSourceCandidate(**values)


def valid_universe_candidate(**overrides: object) -> ResearchUniverseCandidate:
    values = {
        "universe_id": "synthetic-universe-candidate",
        "universe_name": "Synthetic Universe Candidate",
        "universe_type": "broad_etf_candidate",
        "approval_state": "candidate_only",
        "asset_ids": ("SYNTH_ETF_A", "SYNTH_ETF_B"),
        "inclusion_rules": ("metadata candidate only",),
        "exclusion_rules": ("exclude unreviewed live listings",),
        "survivorship_policy": "not reviewed",
        "inception_policy": "not reviewed",
        "delisting_policy": "not reviewed",
        "blockers": ("universe membership not approved",),
        "limitations": ("synthetic asset ids only",),
        "required_follow_up": ("define survivorship policy before use",),
        "non_claims": REQUIRED_RESEARCH_SCOPE_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchUniverseCandidate(**values)


def valid_benchmark_candidate(**overrides: object) -> ResearchBenchmarkCandidate:
    values = {
        "benchmark_id": "synthetic-benchmark-candidate",
        "benchmark_name": "Synthetic Benchmark Candidate",
        "benchmark_type": "buy_and_hold_candidate",
        "approval_state": "candidate_only",
        "return_basis": "candidate price return basis",
        "comparison_role": "candidate comparison metadata only",
        "blockers": ("benchmark not approved",),
        "limitations": ("metadata only",),
        "required_follow_up": ("define benchmark basis before use",),
        "non_claims": REQUIRED_RESEARCH_SCOPE_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchBenchmarkCandidate(**values)


def valid_cash_proxy_candidate(**overrides: object) -> ResearchCashProxyCandidate:
    values = {
        "cash_proxy_id": "synthetic-cash-proxy-candidate",
        "cash_proxy_name": "Synthetic Cash Proxy Candidate",
        "cash_proxy_type": "zero_return_placeholder",
        "approval_state": "candidate_only",
        "return_basis": "placeholder return basis",
        "availability_policy": "candidate availability metadata only",
        "blockers": ("cash proxy not approved",),
        "limitations": ("zero-return placeholder only",),
        "required_follow_up": ("review cash proxy before use",),
        "non_claims": REQUIRED_RESEARCH_SCOPE_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchCashProxyCandidate(**values)


def valid_scope_snapshot(**overrides: object) -> ResearchScopeSnapshot:
    values = {
        "scope_id": "synthetic-scope-candidate-snapshot",
        "as_of_date": date(2026, 1, 31),
        "approval_state": "candidate_only",
        "source_candidates": (valid_source_candidate(),),
        "universe_candidates": (valid_universe_candidate(),),
        "benchmark_candidates": (valid_benchmark_candidate(),),
        "cash_proxy_candidates": (valid_cash_proxy_candidate(),),
        "blockers": ("candidate metadata only",),
        "limitations": ("no approved research scope",),
        "required_follow_up": ("review every candidate before use",),
        "non_claims": REQUIRED_RESEARCH_SCOPE_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchScopeSnapshot(**values)


def test_allowed_values_exclude_approved() -> None:
    assert APPROVAL_STATES == ("candidate_only", "blocked", "deferred")
    assert "approved" not in APPROVAL_STATES
    assert SOURCE_TYPES == (
        "synthetic",
        "local_snapshot_candidate",
        "vendor_candidate",
        "public_candidate",
        "manual_candidate",
        "other",
    )
    assert UNIVERSE_TYPES == (
        "synthetic",
        "broad_etf_candidate",
        "single_symbol_candidate",
        "other",
    )
    assert BENCHMARK_TYPES == (
        "synthetic",
        "buy_and_hold_candidate",
        "index_candidate",
        "cash_candidate",
        "other",
    )
    assert CASH_PROXY_TYPES == (
        "synthetic",
        "treasury_bill_candidate",
        "money_market_candidate",
        "zero_return_placeholder",
        "other",
    )


@pytest.mark.parametrize(
    "contract",
    (
        ResearchDataSourceCandidate,
        ResearchUniverseCandidate,
        ResearchBenchmarkCandidate,
        ResearchCashProxyCandidate,
        ResearchScopeSnapshot,
    ),
)
def test_contracts_are_frozen_and_slotted(contract: type[object]) -> None:
    values = {
        ResearchDataSourceCandidate: valid_source_candidate,
        ResearchUniverseCandidate: valid_universe_candidate,
        ResearchBenchmarkCandidate: valid_benchmark_candidate,
        ResearchCashProxyCandidate: valid_cash_proxy_candidate,
        ResearchScopeSnapshot: valid_scope_snapshot,
    }
    instance = values[contract]()

    assert is_dataclass(contract)
    assert not hasattr(instance, "__dict__")
    with pytest.raises(FrozenInstanceError):
        instance.approval_state = "blocked"


@pytest.mark.parametrize(
    "factory",
    (
        valid_source_candidate,
        valid_universe_candidate,
        valid_benchmark_candidate,
        valid_cash_proxy_candidate,
        valid_scope_snapshot,
    ),
)
@pytest.mark.parametrize("approval_state", APPROVAL_STATES)
def test_scope_contracts_construct_allowed_approval_states(
    factory: Callable[..., object],
    approval_state: str,
) -> None:
    candidate = factory(approval_state=approval_state)

    assert candidate.approval_state == approval_state  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "factory",
    (
        valid_source_candidate,
        valid_universe_candidate,
        valid_benchmark_candidate,
        valid_cash_proxy_candidate,
        valid_scope_snapshot,
    ),
)
@pytest.mark.parametrize("approval_state", ("approved", " approved ", "Approved"))
def test_scope_contracts_reject_approval_like_states(
    factory: Callable[..., object],
    approval_state: str,
) -> None:
    with pytest.raises(ValidationError, match="approval_state"):
        factory(approval_state=approval_state)


def test_data_source_candidate_accepts_valid_construction_and_normalizes_tuples() -> None:
    candidate = valid_source_candidate(
        source_id=" source-id ",
        blockers=[" source blocked "],
        limitations=[" metadata only "],
        required_follow_up=[" review terms "],
        non_claims=[f" {claim} " for claim in REQUIRED_RESEARCH_SCOPE_NON_CLAIMS],
    )

    assert candidate.source_id == "source-id"
    assert candidate.source_type == "synthetic"
    assert candidate.blockers == ("source blocked",)
    assert candidate.limitations == ("metadata only",)
    assert candidate.required_follow_up == ("review terms",)
    assert candidate.non_claims == REQUIRED_RESEARCH_SCOPE_NON_CLAIMS


@pytest.mark.parametrize("bad_value", ("", "   ", True, 123, None))
def test_data_source_candidate_rejects_invalid_required_strings(
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match="source_name"):
        valid_source_candidate(source_name=bad_value)


def test_data_source_candidate_rejects_unknown_source_type() -> None:
    with pytest.raises(ValidationError, match="source_type"):
        valid_source_candidate(source_type="live_vendor")


def test_data_source_candidate_rejects_approved_state() -> None:
    with pytest.raises(ValidationError, match="approval_state"):
        valid_source_candidate(approval_state="approved")


@pytest.mark.parametrize(
    "bad_value",
    ("text", ("",), ("   ",), (1,), (True,)),
)
def test_data_source_candidate_rejects_malformed_tuple_entries(
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match="blockers"):
        valid_source_candidate(blockers=bad_value)


def test_data_source_candidate_to_dict_returns_primitives() -> None:
    payload = valid_source_candidate().to_dict()

    assert payload["source_id"] == "synthetic-source-candidate"
    assert payload["non_claims"] == list(REQUIRED_RESEARCH_SCOPE_NON_CLAIMS)
    _assert_json_primitive(payload)
    json.dumps(payload, separators=(",", ":"))


def test_universe_candidate_accepts_valid_construction_and_preserves_policies() -> None:
    candidate = valid_universe_candidate(
        asset_ids=[" SYNTH_A ", " SYNTH_B "],
        survivorship_policy=" candidate survivorship ",
        inception_policy=" candidate inception ",
        delisting_policy=" candidate delisting ",
    )

    assert candidate.asset_ids == ("SYNTH_A", "SYNTH_B")
    assert candidate.survivorship_policy == "candidate survivorship"
    assert candidate.inception_policy == "candidate inception"
    assert candidate.delisting_policy == "candidate delisting"


def test_universe_candidate_rejects_duplicate_asset_ids() -> None:
    with pytest.raises(ValidationError, match="asset_ids"):
        valid_universe_candidate(asset_ids=("SYNTH_A", "SYNTH_A"))


def test_universe_candidate_rejects_empty_asset_ids() -> None:
    with pytest.raises(ValidationError, match="asset_ids"):
        valid_universe_candidate(asset_ids=())


def test_universe_candidate_rejects_unknown_universe_type() -> None:
    with pytest.raises(ValidationError, match="universe_type"):
        valid_universe_candidate(universe_type="approved_etf_universe")


def test_universe_candidate_rejects_approved_state() -> None:
    with pytest.raises(ValidationError, match="approval_state"):
        valid_universe_candidate(approval_state="approved")


def test_universe_candidate_to_dict_returns_primitives() -> None:
    payload = valid_universe_candidate().to_dict()

    assert payload["asset_ids"] == ["SYNTH_ETF_A", "SYNTH_ETF_B"]
    assert payload["survivorship_policy"] == "not reviewed"
    _assert_json_primitive(payload)
    json.dumps(payload, separators=(",", ":"))


def test_benchmark_candidate_accepts_valid_construction_and_preserves_fields() -> None:
    candidate = valid_benchmark_candidate(
        return_basis=" price return candidate ",
        comparison_role=" comparison candidate ",
    )

    assert candidate.return_basis == "price return candidate"
    assert candidate.comparison_role == "comparison candidate"


def test_benchmark_candidate_rejects_unknown_benchmark_type() -> None:
    with pytest.raises(ValidationError, match="benchmark_type"):
        valid_benchmark_candidate(benchmark_type="approved_benchmark")


def test_benchmark_candidate_rejects_approved_state() -> None:
    with pytest.raises(ValidationError, match="approval_state"):
        valid_benchmark_candidate(approval_state="approved")


def test_benchmark_candidate_to_dict_returns_primitives() -> None:
    payload = valid_benchmark_candidate().to_dict()

    assert payload["return_basis"] == "candidate price return basis"
    assert payload["comparison_role"] == "candidate comparison metadata only"
    _assert_json_primitive(payload)
    json.dumps(payload, separators=(",", ":"))


def test_cash_proxy_candidate_accepts_valid_construction_and_preserves_policy() -> None:
    candidate = valid_cash_proxy_candidate(
        availability_policy=" candidate availability "
    )

    assert candidate.cash_proxy_type == "zero_return_placeholder"
    assert candidate.availability_policy == "candidate availability"


def test_cash_proxy_candidate_rejects_unknown_cash_proxy_type() -> None:
    with pytest.raises(ValidationError, match="cash_proxy_type"):
        valid_cash_proxy_candidate(cash_proxy_type="approved_cash_proxy")


def test_cash_proxy_candidate_rejects_approved_state() -> None:
    with pytest.raises(ValidationError, match="approval_state"):
        valid_cash_proxy_candidate(approval_state="approved")


def test_cash_proxy_candidate_to_dict_returns_primitives() -> None:
    payload = valid_cash_proxy_candidate().to_dict()

    assert payload["availability_policy"] == "candidate availability metadata only"
    assert payload["return_basis"] == "placeholder return basis"
    _assert_json_primitive(payload)
    json.dumps(payload, separators=(",", ":"))


def test_scope_snapshot_accepts_valid_construction_and_normalizes_tuples() -> None:
    snapshot = valid_scope_snapshot(
        source_candidates=[valid_source_candidate(source_id="source-a")],
        universe_candidates=[valid_universe_candidate(universe_id="universe-a")],
        benchmark_candidates=[valid_benchmark_candidate(benchmark_id="benchmark-a")],
        cash_proxy_candidates=[valid_cash_proxy_candidate(cash_proxy_id="cash-a")],
        blockers=[" blocker "],
        limitations=[" limitation "],
        required_follow_up=[" follow up "],
    )

    assert snapshot.as_of_date == date(2026, 1, 31)
    assert tuple(candidate.source_id for candidate in snapshot.source_candidates) == (
        "source-a",
    )
    assert snapshot.blockers == ("blocker",)
    assert snapshot.limitations == ("limitation",)
    assert snapshot.required_follow_up == ("follow up",)


def test_scope_snapshot_rejects_datetime_as_of_date() -> None:
    with pytest.raises(ValidationError, match="plain date"):
        valid_scope_snapshot(as_of_date=datetime(2026, 1, 31))


@pytest.mark.parametrize(
    "field_name",
    (
        "source_candidates",
        "universe_candidates",
        "benchmark_candidates",
        "cash_proxy_candidates",
    ),
)
def test_scope_snapshot_rejects_empty_candidate_groups(field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        valid_scope_snapshot(**{field_name: ()})


@pytest.mark.parametrize(
    ("field_name", "candidate"),
    (
        ("source_candidates", object()),
        ("universe_candidates", object()),
        ("benchmark_candidates", object()),
        ("cash_proxy_candidates", object()),
    ),
)
def test_scope_snapshot_rejects_wrong_candidate_types(
    field_name: str,
    candidate: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        valid_scope_snapshot(**{field_name: (candidate,)})


def test_scope_snapshot_rejects_malformed_candidate_entries() -> None:
    malformed_source = object.__new__(ResearchDataSourceCandidate)

    with pytest.raises(ValidationError, match="malformed"):
        valid_scope_snapshot(source_candidates=(malformed_source,))


@pytest.mark.parametrize(
    ("field_name", "first", "second"),
    (
        (
            "source_candidates",
            valid_source_candidate(source_id="duplicate"),
            valid_source_candidate(source_id="duplicate"),
        ),
        (
            "universe_candidates",
            valid_universe_candidate(universe_id="duplicate"),
            valid_universe_candidate(universe_id="duplicate"),
        ),
        (
            "benchmark_candidates",
            valid_benchmark_candidate(benchmark_id="duplicate"),
            valid_benchmark_candidate(benchmark_id="duplicate"),
        ),
        (
            "cash_proxy_candidates",
            valid_cash_proxy_candidate(cash_proxy_id="duplicate"),
            valid_cash_proxy_candidate(cash_proxy_id="duplicate"),
        ),
    ),
)
def test_scope_snapshot_rejects_duplicate_candidate_ids(
    field_name: str,
    first: object,
    second: object,
) -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        valid_scope_snapshot(**{field_name: (first, second)})


def test_scope_snapshot_rejects_approved_state() -> None:
    with pytest.raises(ValidationError, match="approval_state"):
        valid_scope_snapshot(approval_state="approved")


def test_scope_snapshot_preserves_candidate_ordering() -> None:
    first = valid_source_candidate(source_id="source-a")
    second = valid_source_candidate(source_id="source-b")

    snapshot = valid_scope_snapshot(source_candidates=(first, second))

    assert tuple(candidate.source_id for candidate in snapshot.source_candidates) == (
        "source-a",
        "source-b",
    )
    assert [item["source_id"] for item in snapshot.to_dict()["source_candidates"]] == [
        "source-a",
        "source-b",
    ]


def test_scope_snapshot_to_dict_is_deterministic_and_json_round_trips() -> None:
    snapshot = valid_scope_snapshot()
    first_payload = snapshot.to_dict()
    second_payload = snapshot.to_dict()

    assert first_payload == second_payload
    encoded = json.dumps(first_payload, separators=(",", ":"))
    encoded_again = json.dumps(second_payload, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(encoded), separators=(",", ":"))

    assert encoded == encoded_again
    assert round_tripped == encoded
    assert '"as_of_date":"2026-01-31"' in encoded
    assert " at 0x" not in encoded
    assert "Decimal(" not in encoded
    assert "datetime." not in encoded
    assert "Research" not in encoded
    _assert_no_forbidden_serialized_values(first_payload)


@pytest.mark.parametrize(
    ("factory", "field_name"),
    (
        (valid_source_candidate, "source_id"),
        (valid_universe_candidate, "universe_id"),
        (valid_benchmark_candidate, "benchmark_id"),
        (valid_cash_proxy_candidate, "cash_proxy_id"),
        (valid_scope_snapshot, "scope_id"),
    ),
)
def test_contracts_reject_empty_required_ids(factory: object, field_name: str) -> None:
    with pytest.raises(ValidationError, match=field_name):
        factory(**{field_name: "   "})


@pytest.mark.parametrize(
    "factory",
    (
        valid_source_candidate,
        valid_universe_candidate,
        valid_benchmark_candidate,
        valid_cash_proxy_candidate,
        valid_scope_snapshot,
    ),
)
def test_contracts_require_clear_non_approval_non_claims(factory: object) -> None:
    with pytest.raises(ValidationError, match="non_claims"):
        factory(non_claims=("not strategy validation",))


def test_contract_field_names_do_not_add_forbidden_trading_runtime_surfaces() -> None:
    contract_fields = set()
    for contract in (
        ResearchDataSourceCandidate,
        ResearchUniverseCandidate,
        ResearchBenchmarkCandidate,
        ResearchCashProxyCandidate,
        ResearchScopeSnapshot,
    ):
        contract_fields.update(field.name for field in fields(contract))

    assert contract_fields.isdisjoint(_FORBIDDEN_FIELD_NAMES)


def test_no_real_ticker_data_is_required() -> None:
    snapshot = valid_scope_snapshot()

    assert "SPY" not in json.dumps(snapshot.to_dict(), separators=(",", ":"))


def test_module_imports_no_vendor_network_runtime_or_trading_path_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_only_imports_plain_date_from_datetime() -> None:
    imported_datetime_names = {
        alias.name
        for node in ast.walk(_tree())
        if isinstance(node, ast.ImportFrom) and node.module == "datetime"
        for alias in node.names
    }

    assert imported_datetime_names == {"date"}


def test_module_makes_no_file_network_clock_vendor_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _assert_json_primitive(value: object) -> None:
    if isinstance(value, dict):
        assert all(type(key) is str for key in value)
        for item in value.values():
            _assert_json_primitive(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_json_primitive(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


def _assert_no_forbidden_serialized_values(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal, date, datetime))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_no_forbidden_serialized_values(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_no_forbidden_serialized_values(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
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
