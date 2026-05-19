import ast
from collections.abc import Callable
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.research_methodology import (
    ACTION_TIMING_POLICIES,
    APPROVAL_STATES,
    CADENCE_POLICIES,
    COMPARISON_RULES,
    COST_ASSUMPTION_POLICIES,
    COST_POLICIES,
    LOOKAHEAD_POLICIES,
    METHODOLOGY_TYPES,
    PARAMETER_TYPES,
    REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS,
    RULE_FAMILIES,
    ResearchMethodologyCandidate,
    ResearchMethodologyScopeSnapshot,
    ResearchParameterSetCandidate,
)


MODULE_PATH = Path("src/algotrader/research/research_methodology.py")


def valid_methodology_candidate(**overrides: object) -> ResearchMethodologyCandidate:
    values: dict[str, object] = {
        "methodology_id": "methodology-synthetic-sma-candidate",
        "methodology_name": "Synthetic SMA methodology metadata candidate",
        "methodology_type": "moving_average_trend_candidate",
        "approval_state": "candidate_only",
        "rule_family": "simple_moving_average_candidate",
        "rule_description": (
            "Metadata-only candidate for comparing a value with a trailing "
            "simple moving average."
        ),
        "cadence_policy": "daily_close_candidate",
        "action_timing_policy": "next_session_candidate",
        "lookahead_policy": "candidate_as_of_protocol_required",
        "return_construction_policy": "price return convention unresolved",
        "adjustment_policy": "adjustment convention unresolved",
        "cost_policy": "real_cost_policy_required",
        "linked_scope_ids": ("research-scope-synthetic-broad-etf",),
        "evidence_refs": ("phase-74-methodology-contract",),
        "blockers": ("methodology evidence review required",),
        "limitations": ("candidate metadata only",),
        "required_follow_up": ("define deterministic as-of protocol",),
        "non_claims": REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchMethodologyCandidate(**values)  # type: ignore[arg-type]


def valid_parameter_set_candidate(**overrides: object) -> ResearchParameterSetCandidate:
    values: dict[str, object] = {
        "parameter_set_id": "parameter-set-synthetic-sma-200-candidate",
        "methodology_id": "methodology-synthetic-sma-candidate",
        "parameter_set_name": "Synthetic SMA 200-window metadata candidate",
        "parameter_type": "single_window_candidate",
        "approval_state": "candidate_only",
        "moving_average_windows": (200,),
        "cadence_policy": "daily_close_candidate",
        "action_timing_policy": "next_session_candidate",
        "comparison_rule": "value_gt_moving_average",
        "cost_assumption_policy": "real_cost_policy_required",
        "sensitivity_notes": ("sensitivity grid remains unresolved",),
        "blockers": ("parameter evidence review required",),
        "limitations": ("parameter metadata only",),
        "required_follow_up": ("define sensitivity analysis plan",),
        "non_claims": REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchParameterSetCandidate(**values)  # type: ignore[arg-type]


def valid_methodology_scope_snapshot(
    **overrides: object,
) -> ResearchMethodologyScopeSnapshot:
    methodology = valid_methodology_candidate()
    parameter_set = valid_parameter_set_candidate(
        methodology_id=methodology.methodology_id,
    )
    values: dict[str, object] = {
        "methodology_scope_id": "methodology-scope-synthetic-broad-etf",
        "as_of_date": date(2026, 1, 19),
        "approval_state": "candidate_only",
        "methodology_candidates": (methodology,),
        "parameter_set_candidates": (parameter_set,),
        "blockers": ("methodology and parameter review required",),
        "limitations": ("candidate snapshot metadata only",),
        "required_follow_up": ("connect to approved research scope later",),
        "non_claims": REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS,
    }
    values.update(overrides)
    return ResearchMethodologyScopeSnapshot(**values)  # type: ignore[arg-type]


def test_allowed_approval_states_do_not_include_approved() -> None:
    assert APPROVAL_STATES == ("candidate_only", "blocked", "deferred")
    assert "approved" not in APPROVAL_STATES


def test_enum_like_constants_match_phase_74_allowlists() -> None:
    assert METHODOLOGY_TYPES == (
        "synthetic",
        "moving_average_trend_candidate",
        "buy_and_hold_baseline_candidate",
        "other",
    )
    assert RULE_FAMILIES == (
        "synthetic",
        "simple_moving_average_candidate",
        "baseline_candidate",
        "other",
    )
    assert PARAMETER_TYPES == (
        "synthetic",
        "single_window_candidate",
        "sensitivity_grid_candidate",
        "baseline_candidate",
        "other",
    )
    assert CADENCE_POLICIES == (
        "synthetic_only",
        "daily_close_candidate",
        "monthly_close_candidate",
        "unresolved",
        "other",
    )
    assert ACTION_TIMING_POLICIES == (
        "synthetic_previous_exposure",
        "next_session_candidate",
        "next_rebalance_candidate",
        "same_close_metadata_only",
        "unresolved",
        "other",
    )
    assert LOOKAHEAD_POLICIES == (
        "synthetic_no_lookahead",
        "candidate_as_of_protocol_required",
        "unresolved",
        "other",
    )
    assert COMPARISON_RULES == (
        "value_gt_moving_average",
        "value_gte_moving_average_candidate",
        "baseline_always_exposed",
        "synthetic_only",
        "other",
    )
    assert COST_POLICIES == (
        "zero_cost_placeholder",
        "synthetic_cost_candidate",
        "real_cost_policy_required",
        "unresolved",
        "other",
    )
    assert COST_ASSUMPTION_POLICIES == COST_POLICIES


@pytest.mark.parametrize(
    "factory",
    (
        valid_methodology_candidate,
        valid_parameter_set_candidate,
        valid_methodology_scope_snapshot,
    ),
)
@pytest.mark.parametrize("approval_state", APPROVAL_STATES)
def test_methodology_contracts_construct_allowed_approval_states(
    factory: Callable[..., object],
    approval_state: str,
) -> None:
    candidate = factory(approval_state=approval_state)

    assert candidate.approval_state == approval_state  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "factory",
    (
        valid_methodology_candidate,
        valid_parameter_set_candidate,
        valid_methodology_scope_snapshot,
    ),
)
@pytest.mark.parametrize("approval_state", ("approved", " approved ", "Approved"))
def test_methodology_contracts_reject_approval_like_states(
    factory: Callable[..., object],
    approval_state: str,
) -> None:
    with pytest.raises(ValidationError, match="approval_state"):
        factory(approval_state=approval_state)


def test_methodology_candidate_accepts_valid_construction_and_normalizes_tuples() -> None:
    candidate = valid_methodology_candidate(
        methodology_id=" methodology-id ",
        linked_scope_ids=[" linked-scope "],
        evidence_refs=[" evidence-ref "],
        blockers=[" blocker "],
        limitations=[" limitation "],
        required_follow_up=[" follow-up "],
        non_claims=[
            f" {claim} " for claim in REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS
        ],
    )

    assert candidate.methodology_id == "methodology-id"
    assert candidate.methodology_type == "moving_average_trend_candidate"
    assert candidate.linked_scope_ids == ("linked-scope",)
    assert candidate.evidence_refs == ("evidence-ref",)
    assert candidate.blockers == ("blocker",)
    assert candidate.limitations == ("limitation",)
    assert candidate.required_follow_up == ("follow-up",)
    assert candidate.non_claims == REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS
    _assert_frozen_slotted(ResearchMethodologyCandidate, candidate)


@pytest.mark.parametrize(
    "field_name",
    (
        "methodology_id",
        "methodology_name",
        "methodology_type",
        "approval_state",
        "rule_family",
        "rule_description",
        "cadence_policy",
        "action_timing_policy",
        "lookahead_policy",
        "return_construction_policy",
        "adjustment_policy",
        "cost_policy",
    ),
)
@pytest.mark.parametrize("bad_value", (" ", True))
def test_methodology_candidate_rejects_invalid_strings(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError):
        valid_methodology_candidate(**{field_name: bad_value})


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("methodology_type", "trend"),
        ("rule_family", "moving_average"),
        ("cadence_policy", "weekly_close_candidate"),
        ("action_timing_policy", "immediate_candidate"),
        ("lookahead_policy", "no_lookahead"),
        ("cost_policy", "free"),
    ),
)
def test_methodology_candidate_rejects_unknown_enum_like_values(
    field_name: str,
    bad_value: str,
) -> None:
    with pytest.raises(ValidationError):
        valid_methodology_candidate(**{field_name: bad_value})


def test_methodology_candidate_rejects_approved_approval_state() -> None:
    with pytest.raises(ValidationError):
        valid_methodology_candidate(approval_state="approved")


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("linked_scope_ids", "scope-id"),
        ("evidence_refs", (object(),)),
        ("blockers", ("",)),
        ("limitations", (" ",)),
        ("required_follow_up", (True,)),
    ),
)
def test_methodology_candidate_rejects_malformed_tuple_entries(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError):
        valid_methodology_candidate(**{field_name: bad_value})


def test_methodology_candidate_enforces_required_non_claims() -> None:
    with pytest.raises(ValidationError):
        valid_methodology_candidate(
            non_claims=REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS[:-1],
        )


def test_methodology_candidate_to_dict_uses_primitive_serialization() -> None:
    candidate = valid_methodology_candidate()
    payload = candidate.to_dict()

    assert payload == candidate.to_dict()
    assert payload["linked_scope_ids"] == ["research-scope-synthetic-broad-etf"]
    assert payload["non_claims"] == list(REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS)
    _assert_no_forbidden_serialized_values(payload)
    compact = json.dumps(payload, separators=(",", ":"))
    assert "object at 0x" not in compact


def test_parameter_set_candidate_accepts_valid_construction_and_normalizes_tuples() -> None:
    candidate = valid_parameter_set_candidate(
        parameter_set_id=" parameter-set-id ",
        moving_average_windows=[200],
        sensitivity_notes=[" sensitivity note "],
        blockers=[" blocker "],
        limitations=[" limitation "],
        required_follow_up=[" follow-up "],
        non_claims=[
            f" {claim} " for claim in REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS
        ],
    )

    assert candidate.parameter_set_id == "parameter-set-id"
    assert candidate.parameter_type == "single_window_candidate"
    assert candidate.moving_average_windows == (200,)
    assert candidate.sensitivity_notes == ("sensitivity note",)
    assert candidate.blockers == ("blocker",)
    assert candidate.limitations == ("limitation",)
    assert candidate.required_follow_up == ("follow-up",)
    assert candidate.non_claims == REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS
    _assert_frozen_slotted(ResearchParameterSetCandidate, candidate)


@pytest.mark.parametrize(
    "field_name",
    (
        "parameter_set_id",
        "methodology_id",
        "parameter_set_name",
        "parameter_type",
        "approval_state",
        "cadence_policy",
        "action_timing_policy",
        "comparison_rule",
        "cost_assumption_policy",
    ),
)
@pytest.mark.parametrize("bad_value", (" ", True))
def test_parameter_set_candidate_rejects_invalid_strings(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(**{field_name: bad_value})


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("parameter_type", "window"),
        ("cadence_policy", "weekly_close_candidate"),
        ("action_timing_policy", "immediate_candidate"),
        ("comparison_rule", "crosses_above"),
        ("cost_assumption_policy", "free"),
    ),
)
def test_parameter_set_candidate_rejects_unknown_enum_like_values(
    field_name: str,
    bad_value: str,
) -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(**{field_name: bad_value})


def test_parameter_set_candidate_rejects_approved_approval_state() -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(approval_state="approved")


def test_parameter_set_candidate_rejects_empty_moving_average_windows() -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(moving_average_windows=())


@pytest.mark.parametrize("bad_window", (True, "200", 0, -1, 1.5))
def test_parameter_set_candidate_rejects_malformed_moving_average_windows(
    bad_window: object,
) -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(moving_average_windows=(bad_window,))


def test_parameter_set_candidate_rejects_duplicate_moving_average_windows() -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(moving_average_windows=(200, 50, 200))


def test_parameter_set_candidate_preserves_window_ordering() -> None:
    candidate = valid_parameter_set_candidate(moving_average_windows=[200, 50, 100])

    assert candidate.moving_average_windows == (200, 50, 100)
    assert candidate.to_dict()["moving_average_windows"] == [200, 50, 100]


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("sensitivity_notes", "note"),
        ("blockers", (object(),)),
        ("limitations", ("",)),
        ("required_follow_up", (True,)),
    ),
)
def test_parameter_set_candidate_rejects_malformed_tuple_entries(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(**{field_name: bad_value})


def test_parameter_set_candidate_enforces_required_non_claims() -> None:
    with pytest.raises(ValidationError):
        valid_parameter_set_candidate(
            non_claims=REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS[:-1],
        )


def test_parameter_set_candidate_to_dict_uses_primitive_serialization() -> None:
    candidate = valid_parameter_set_candidate()
    payload = candidate.to_dict()

    assert payload == candidate.to_dict()
    assert payload["moving_average_windows"] == [200]
    assert payload["non_claims"] == list(REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS)
    _assert_no_forbidden_serialized_values(payload)
    compact = json.dumps(payload, separators=(",", ":"))
    assert "object at 0x" not in compact


def test_methodology_scope_snapshot_accepts_valid_construction() -> None:
    snapshot = valid_methodology_scope_snapshot(
        methodology_scope_id=" methodology-scope-id ",
        methodology_candidates=[valid_methodology_candidate()],
        parameter_set_candidates=[valid_parameter_set_candidate()],
        blockers=[" blocker "],
        limitations=[" limitation "],
        required_follow_up=[" follow-up "],
        non_claims=[
            f" {claim} " for claim in REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS
        ],
    )

    assert snapshot.methodology_scope_id == "methodology-scope-id"
    assert snapshot.as_of_date == date(2026, 1, 19)
    assert len(snapshot.methodology_candidates) == 1
    assert len(snapshot.parameter_set_candidates) == 1
    assert snapshot.blockers == ("blocker",)
    assert snapshot.limitations == ("limitation",)
    assert snapshot.required_follow_up == ("follow-up",)
    assert snapshot.non_claims == REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS
    _assert_frozen_slotted(ResearchMethodologyScopeSnapshot, snapshot)


@pytest.mark.parametrize("bad_date", (datetime(2026, 1, 19, 12, 0), "2026-01-19"))
def test_methodology_scope_snapshot_requires_plain_date_only(bad_date: object) -> None:
    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(as_of_date=bad_date)


@pytest.mark.parametrize("field_name", ("methodology_candidates", "parameter_set_candidates"))
def test_methodology_scope_snapshot_rejects_empty_candidate_groups(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(**{field_name: ()})


def test_methodology_scope_snapshot_rejects_duplicate_methodology_ids() -> None:
    methodology = valid_methodology_candidate(methodology_id="duplicate-methodology")
    duplicate = valid_methodology_candidate(
        methodology_id="duplicate-methodology",
        methodology_name="Second metadata candidate",
    )
    parameter_set = valid_parameter_set_candidate(
        methodology_id=methodology.methodology_id,
    )

    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(
            methodology_candidates=(methodology, duplicate),
            parameter_set_candidates=(parameter_set,),
        )


def test_methodology_scope_snapshot_rejects_duplicate_parameter_set_ids() -> None:
    methodology = valid_methodology_candidate()
    parameter_set = valid_parameter_set_candidate(
        parameter_set_id="duplicate-parameter-set",
        methodology_id=methodology.methodology_id,
    )
    duplicate = valid_parameter_set_candidate(
        parameter_set_id="duplicate-parameter-set",
        methodology_id=methodology.methodology_id,
        parameter_set_name="Second parameter metadata candidate",
    )

    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(
            methodology_candidates=(methodology,),
            parameter_set_candidates=(parameter_set, duplicate),
        )


def test_methodology_scope_snapshot_rejects_parameter_set_without_matching_methodology() -> None:
    methodology = valid_methodology_candidate(methodology_id="methodology-a")
    parameter_set = valid_parameter_set_candidate(methodology_id="methodology-b")

    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(
            methodology_candidates=(methodology,),
            parameter_set_candidates=(parameter_set,),
        )


def test_methodology_scope_snapshot_validates_methodologies_before_links() -> None:
    parameter_set = valid_parameter_set_candidate(methodology_id="missing-methodology")

    with pytest.raises(ValidationError, match="methodology_candidates"):
        valid_methodology_scope_snapshot(
            methodology_candidates=(),
            parameter_set_candidates=(parameter_set,),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("methodology_candidates", (object(),)),
        ("parameter_set_candidates", (object(),)),
        ("blockers", ("",)),
        ("limitations", (object(),)),
        ("required_follow_up", "follow-up"),
    ),
)
def test_methodology_scope_snapshot_rejects_malformed_candidate_or_tuple_entries(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(**{field_name: bad_value})


def test_methodology_scope_snapshot_rejects_approved_approval_state() -> None:
    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(approval_state="approved")


def test_methodology_scope_snapshot_enforces_required_non_claims() -> None:
    with pytest.raises(ValidationError):
        valid_methodology_scope_snapshot(
            non_claims=REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS[:-1],
        )


def test_methodology_scope_snapshot_preserves_candidate_ordering() -> None:
    first_methodology = valid_methodology_candidate(methodology_id="methodology-first")
    second_methodology = valid_methodology_candidate(
        methodology_id="methodology-second",
        methodology_name="Second methodology metadata candidate",
    )
    first_parameter_set = valid_parameter_set_candidate(
        parameter_set_id="parameter-set-first",
        methodology_id=first_methodology.methodology_id,
    )
    second_parameter_set = valid_parameter_set_candidate(
        parameter_set_id="parameter-set-second",
        methodology_id=second_methodology.methodology_id,
        parameter_set_name="Second parameter metadata candidate",
    )
    snapshot = valid_methodology_scope_snapshot(
        methodology_candidates=(second_methodology, first_methodology),
        parameter_set_candidates=(second_parameter_set, first_parameter_set),
    )

    assert [item.methodology_id for item in snapshot.methodology_candidates] == [
        "methodology-second",
        "methodology-first",
    ]
    assert [item.parameter_set_id for item in snapshot.parameter_set_candidates] == [
        "parameter-set-second",
        "parameter-set-first",
    ]
    assert [
        item["methodology_id"] for item in snapshot.to_dict()["methodology_candidates"]
    ] == ["methodology-second", "methodology-first"]
    assert [
        item["parameter_set_id"]
        for item in snapshot.to_dict()["parameter_set_candidates"]
    ] == ["parameter-set-second", "parameter-set-first"]


def test_methodology_scope_snapshot_to_dict_is_deterministic_and_json_primitive() -> None:
    snapshot = valid_methodology_scope_snapshot()
    payload = snapshot.to_dict()

    assert payload == snapshot.to_dict()
    assert payload["as_of_date"] == "2026-01-19"
    assert payload["methodology_candidates"] == [
        snapshot.methodology_candidates[0].to_dict()
    ]
    assert payload["parameter_set_candidates"] == [
        snapshot.parameter_set_candidates[0].to_dict()
    ]
    _assert_no_forbidden_serialized_values(payload)

    compact = json.dumps(payload, separators=(",", ":"))
    assert json.dumps(json.loads(compact), separators=(",", ":")) == compact
    assert "object at 0x" not in compact


def test_contract_field_names_avoid_trading_and_runtime_surfaces() -> None:
    forbidden_field_names = {
        "order",
        "fill",
        "broker",
        "account",
        "position",
        "portfolio",
        "allocation",
        "target_weight",
        "execution",
        "runtime",
        "scheduler",
        "credential",
        "sdk",
        "network",
    }

    for contract in (
        ResearchMethodologyCandidate,
        ResearchParameterSetCandidate,
        ResearchMethodologyScopeSnapshot,
    ):
        field_names = {field.name for field in fields(contract)}
        assert field_names.isdisjoint(forbidden_field_names)


def test_non_claims_are_explicitly_non_approving_and_non_trading() -> None:
    payload = valid_methodology_scope_snapshot().to_dict()
    compact = json.dumps(payload, separators=(",", ":"))

    for claim in REQUIRED_RESEARCH_METHODOLOGY_NON_CLAIMS:
        assert claim in compact
    assert "methodology approval" in compact
    assert "parameter approval" in compact
    assert "evidence approval" in compact
    assert "strategy validation" in compact
    assert "signal approval" in compact
    assert "evaluator approval" in compact
    assert "trading authority" in compact
    assert "real data ingestion" in compact
    assert "source/universe/benchmark/cash proxy approval" in compact


def test_snapshot_requires_no_real_etf_ticker_data() -> None:
    compact = json.dumps(
        valid_methodology_scope_snapshot().to_dict(),
        separators=(",", ":"),
    )

    for ticker in ("SPY", "IVV", "VOO", "QQQ", "VTI"):
        assert ticker not in compact


def test_research_methodology_module_has_no_runtime_or_candidate_discovery_behavior() -> None:
    tree = _tree()
    forbidden_public_names = {
        "approve",
        "backtest",
        "broker",
        "discover",
        "evaluate",
        "fill",
        "ingest",
        "order",
        "portfolio",
        "rank",
        "recommend",
        "score",
        "signal",
        "strategy",
        "trade",
    }

    public_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        and not node.name.startswith("_")
    }

    assert public_names == {
        "ResearchMethodologyCandidate",
        "ResearchMethodologyScopeSnapshot",
        "ResearchParameterSetCandidate",
        "to_dict",
    }
    assert public_names.isdisjoint(forbidden_public_names)


def test_research_methodology_ast_guardrails_exclude_disallowed_dependencies() -> None:
    forbidden_import_prefixes = (
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
        "algotrader.runtime",
        "algotrader.scheduler",
        "alpaca",
        "alpaca_trade_api",
        "anthropic",
        "database",
        "duckdb",
        "httpx",
        "ipynb",
        "langchain",
        "langgraph",
        "llm",
        "notebook",
        "numpy",
        "openai",
        "os",
        "pandas",
        "pathlib",
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
    violations = [
        f"{reference.path}:{reference.line}: {reference.module}"
        for reference in _import_references(MODULE_PATH)
        if _matches_forbidden_prefix(reference.module, forbidden_import_prefixes)
    ]

    assert violations == []


def test_research_methodology_ast_guardrails_exclude_io_network_and_clock_calls() -> None:
    call_names = {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }
    forbidden_calls = {
        "connect",
        "create_connection",
        "date.today",
        "datetime.now",
        "datetime.utcnow",
        "environ.get",
        "get",
        "getenv",
        "open",
        "os.environ.get",
        "os.getenv",
        "Path",
        "Path.read_text",
        "post",
        "random",
        "random.random",
        "read",
        "request",
        "socket",
        "socket.socket",
        "time.monotonic",
        "time.time",
        "write",
    }

    assert call_names.isdisjoint(forbidden_calls)


def _assert_frozen_slotted(contract: type[object], instance: object) -> None:
    assert is_dataclass(contract)
    assert not hasattr(instance, "__dict__")
    with pytest.raises(FrozenInstanceError):
        instance.approval_state = "blocked"  # type: ignore[attr-defined]


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


class ImportReference:
    def __init__(self, path: Path, line: int, module: str) -> None:
        self.path = path
        self.line = line
        self.module = module


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references(path: Path) -> tuple[ImportReference, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[ImportReference] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                ImportReference(path=path, line=node.lineno, module=alias.name)
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imports.extend(
                ImportReference(path=path, line=node.lineno, module=module)
                for module in _import_from_modules(path, node)
            )

    return tuple(imports)


def _import_from_modules(path: Path, node: ast.ImportFrom) -> tuple[str, ...]:
    if node.level == 0:
        return (node.module,) if node.module else ()

    base_module = _relative_import_base(path, node.level)
    if node.module:
        return (f"{base_module}.{node.module}",)

    return tuple(f"{base_module}.{alias.name}" for alias in node.names)


def _relative_import_base(path: Path, level: int) -> str:
    module_name = _module_name(path)
    if path.name == "__init__.py":
        package_name = module_name
    else:
        package_name = module_name.rsplit(".", maxsplit=1)[0]

    package_parts = package_name.split(".")
    base_parts = package_parts[: len(package_parts) - level + 1]
    return ".".join(base_parts)


def _module_name(path: Path) -> str:
    relative_path = path.relative_to(Path("src"))
    return ".".join(relative_path.with_suffix("").parts)


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
