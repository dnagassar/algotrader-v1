import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.errors import ValidationError
from algotrader.governance import RiskAuthoritySnapshot, StrategyMandateSnapshot


MODULE_PATH = Path("src/algotrader/governance/status_snapshot.py")

_FORBIDDEN_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker",
    "broker_order",
    "candidate_discovery",
    "credential",
    "credentials",
    "execution",
    "execution_request",
    "fill",
    "fill_id",
    "market_data",
    "network",
    "order",
    "order_id",
    "portfolio",
    "position",
    "position_id",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "runtime",
    "scheduler",
    "score",
    "scoring",
    "sdk",
    "signal_score",
    "submit_order",
    "target_weight",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "http",
    "httpx",
    "importlib",
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

_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "ExecutionIntent",
    "ExecutionPlan",
    "Fill",
    "LocalBroker",
    "PortfolioState",
    "Position",
    "ProposedOrder",
    "account",
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker",
    "broker_order",
    "candidate_discovery",
    "credential",
    "credentials",
    "execution",
    "fill",
    "fill_id",
    "market_data",
    "network",
    "order",
    "portfolio",
    "position",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "runtime",
    "scheduler",
    "score",
    "scoring",
    "sdk",
    "submit_order",
    "target_weight",
}

_FORBIDDEN_CALL_NAMES = {
    "__import__",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "eval",
    "exec",
    "getenv",
    "import_module",
    "importlib.import_module",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "random",
    "random.random",
    "read",
    "request",
    "schedule",
    "socket.socket",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_sql",
    "urlopen",
    "uuid.uuid4",
    "uuid4",
    "write",
}

_TRADING_RECOMMENDATION_LANGUAGE = {
    "buy",
    "sell",
    "hold",
    "recommendation",
    "trade",
    "trading",
}


def strategy_snapshot(**overrides: object) -> StrategyMandateSnapshot:
    values: dict[str, object] = {
        "strategy_id": "strategy-sma-200",
        "mandate_id": "mandate-sma-200",
        "as_of_date": date(2026, 5, 17),
        "mandate_approved": False,
        "evidence_approved": False,
        "paper_eligible": False,
        "live_probe_eligible": False,
        "live_authorized": False,
        "validated_research_artifact_ids": ("research-artifact-001",),
        "validated_signal_definition_ids": ("signal-definition-001",),
        "required_evidence": ("Independent evidence review is required.",),
        "promotion_requirements": ("Approve deterministic evidence package.",),
        "revocation_triggers": ("Evidence package is superseded.",),
        "blocking_reasons": ("Mandate review is incomplete.",),
        "limitations": ("Metadata source snapshot only.",),
        "uncertainty_factors": ("Evidence coverage remains incomplete.",),
        "failure_modes": ("Mandate assumptions may become stale.",),
        "non_claims": ("No capital authority is represented.",),
    }
    values.update(overrides)
    return StrategyMandateSnapshot(**values)


def paper_strategy_snapshot(**overrides: object) -> StrategyMandateSnapshot:
    values: dict[str, object] = {
        "mandate_approved": True,
        "evidence_approved": True,
        "paper_eligible": True,
        "live_probe_eligible": False,
        "live_authorized": False,
        "blocking_reasons": ("Live probe mandate review is incomplete.",),
    }
    values.update(overrides)
    return strategy_snapshot(**values)


def live_probe_strategy_snapshot(**overrides: object) -> StrategyMandateSnapshot:
    values: dict[str, object] = {
        "mandate_approved": True,
        "evidence_approved": True,
        "paper_eligible": True,
        "live_probe_eligible": True,
        "live_authorized": False,
        "blocking_reasons": ("Live mandate review is incomplete.",),
    }
    values.update(overrides)
    return strategy_snapshot(**values)


def live_strategy_snapshot(**overrides: object) -> StrategyMandateSnapshot:
    values: dict[str, object] = {
        "mandate_approved": True,
        "evidence_approved": True,
        "paper_eligible": True,
        "live_probe_eligible": True,
        "live_authorized": True,
        "blocking_reasons": (),
    }
    values.update(overrides)
    return strategy_snapshot(**values)


def risk_snapshot(**overrides: object) -> RiskAuthoritySnapshot:
    values: dict[str, object] = {
        "authority_id": "risk-authority-sma-200",
        "strategy_id": "strategy-sma-200",
        "as_of_date": date(2026, 5, 17),
        "paper_allowed": False,
        "live_probe_allowed": False,
        "live_allowed": False,
        "kill_switch_active": False,
        "risk_policy_ids": ("risk-policy-001",),
        "active_constraints": ("Manual review required before promotion.",),
        "promotion_requirements": ("Approve deterministic risk constraints.",),
        "revocation_triggers": ("Risk policy is superseded.",),
        "blocking_reasons": ("Risk authority review is incomplete.",),
        "limitations": ("Risk authority source snapshot only.",),
        "uncertainty_factors": ("Operational assumptions remain unresolved.",),
        "failure_modes": ("Control review may become stale.",),
        "non_claims": ("No capital authority is represented.",),
    }
    values.update(overrides)
    return RiskAuthoritySnapshot(**values)


def paper_risk_snapshot(**overrides: object) -> RiskAuthoritySnapshot:
    values: dict[str, object] = {
        "paper_allowed": True,
        "live_probe_allowed": False,
        "live_allowed": False,
        "blocking_reasons": ("Live probe risk review is incomplete.",),
    }
    values.update(overrides)
    return risk_snapshot(**values)


def live_probe_risk_snapshot(**overrides: object) -> RiskAuthoritySnapshot:
    values: dict[str, object] = {
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_allowed": False,
        "blocking_reasons": ("Live risk review is incomplete.",),
    }
    values.update(overrides)
    return risk_snapshot(**values)


def live_risk_snapshot(**overrides: object) -> RiskAuthoritySnapshot:
    values: dict[str, object] = {
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_allowed": True,
        "kill_switch_active": False,
        "blocking_reasons": (),
    }
    values.update(overrides)
    return risk_snapshot(**values)


def test_strategy_mandate_snapshot_accepts_valid_metadata_only_inputs() -> None:
    snapshot = strategy_snapshot()

    assert snapshot.strategy_id == "strategy-sma-200"
    assert snapshot.mandate_id == "mandate-sma-200"
    assert snapshot.as_of_date == date(2026, 5, 17)
    assert snapshot.validated_research_artifact_ids == ("research-artifact-001",)
    assert set(field.name for field in fields(snapshot)).isdisjoint(
        _FORBIDDEN_FIELD_NAMES
    )


def test_strategy_mandate_snapshot_is_frozen_and_slotted() -> None:
    snapshot = strategy_snapshot()

    assert hasattr(StrategyMandateSnapshot, "__slots__")
    assert not hasattr(snapshot, "__dict__")
    with pytest.raises(FrozenInstanceError):
        snapshot.strategy_id = "changed"


def test_strategy_mandate_snapshot_normalizes_sequences_to_immutable_tuples() -> None:
    research_ids = ["research-artifact-001"]
    signal_ids = ["signal-definition-001"]
    required_evidence = ["Independent review required."]

    snapshot = strategy_snapshot(
        validated_research_artifact_ids=research_ids,
        validated_signal_definition_ids=signal_ids,
        required_evidence=required_evidence,
    )
    research_ids.append("late-research-artifact")
    signal_ids.append("late-signal-definition")
    required_evidence.append("late-evidence")

    assert snapshot.validated_research_artifact_ids == ("research-artifact-001",)
    assert snapshot.validated_signal_definition_ids == ("signal-definition-001",)
    assert snapshot.required_evidence == ("Independent review required.",)
    with pytest.raises(TypeError):
        snapshot.required_evidence[0] = "changed"


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("strategy_id", ""),
        ("strategy_id", " "),
        ("strategy_id", True),
        ("mandate_id", ""),
        ("mandate_id", " "),
        ("mandate_id", False),
    ),
)
def test_strategy_mandate_snapshot_rejects_empty_or_non_string_ids(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        strategy_snapshot(**{field_name: value})


def test_strategy_mandate_snapshot_rejects_datetime_as_as_of_date() -> None:
    with pytest.raises(ValidationError, match="as_of_date"):
        strategy_snapshot(as_of_date=datetime(2026, 5, 17))


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("validated_research_artifact_ids", "research-artifact-001"),
        ("validated_research_artifact_ids", ("valid", None)),
        ("validated_signal_definition_ids", ("valid", True)),
        ("required_evidence", ("valid", "")),
        ("promotion_requirements", ("valid", " ")),
        ("revocation_triggers", ("valid", 1)),
        ("blocking_reasons", "none"),
        ("limitations", ("valid", None)),
        ("uncertainty_factors", ("valid", False)),
        ("failure_modes", ("valid", "")),
        ("non_claims", ("valid", " ")),
    ),
)
def test_strategy_mandate_snapshot_rejects_malformed_tuple_entries(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        strategy_snapshot(**{field_name: value})


def test_strategy_mandate_snapshot_rejects_live_probe_without_paper() -> None:
    with pytest.raises(ValidationError, match="paper_eligible"):
        strategy_snapshot(live_probe_eligible=True, paper_eligible=False)


def test_strategy_mandate_snapshot_rejects_live_authorized_without_mandate() -> None:
    with pytest.raises(ValidationError, match="mandate_approved"):
        live_strategy_snapshot(mandate_approved=False)


def test_strategy_mandate_snapshot_rejects_live_authorized_without_evidence() -> None:
    with pytest.raises(ValidationError, match="evidence_approved"):
        live_strategy_snapshot(evidence_approved=False)


def test_strategy_mandate_snapshot_rejects_live_authorized_without_paper() -> None:
    with pytest.raises(ValidationError, match="paper_eligible"):
        strategy_snapshot(
            mandate_approved=True,
            evidence_approved=True,
            paper_eligible=False,
            live_probe_eligible=False,
            live_authorized=True,
            blocking_reasons=(),
        )


def test_strategy_mandate_snapshot_rejects_live_authorized_without_probe() -> None:
    with pytest.raises(ValidationError, match="live_probe_eligible"):
        strategy_snapshot(
            mandate_approved=True,
            evidence_approved=True,
            paper_eligible=True,
            live_probe_eligible=False,
            live_authorized=True,
            blocking_reasons=(),
        )


def test_strategy_mandate_snapshot_rejects_live_authorized_with_blockers() -> None:
    with pytest.raises(ValidationError, match="blocking_reasons"):
        live_strategy_snapshot(blocking_reasons=("Open blocker.",))


def test_strategy_mandate_paper_eligibility_does_not_imply_live_readiness() -> None:
    snapshot = paper_strategy_snapshot()

    assert snapshot.paper_eligible is True
    assert snapshot.live_probe_eligible is False
    assert snapshot.live_authorized is False


def test_strategy_mandate_live_probe_does_not_imply_profitability() -> None:
    snapshot = live_probe_strategy_snapshot()
    field_names = tuple(field.name for field in fields(snapshot))

    assert snapshot.live_probe_eligible is True
    assert snapshot.live_authorized is False
    assert "profitability" not in field_names
    assert "profitable" not in field_names


def test_strategy_mandate_preserves_required_governance_metadata() -> None:
    snapshot = strategy_snapshot(
        promotion_requirements=("Paper review board approval.",),
        revocation_triggers=("Evidence artifact withdrawn.",),
        limitations=("Governance metadata only.",),
        uncertainty_factors=("Data provenance unresolved.",),
        failure_modes=("Evidence decay.",),
        non_claims=("No capital authority is represented.",),
    )

    assert snapshot.promotion_requirements == ("Paper review board approval.",)
    assert snapshot.revocation_triggers == ("Evidence artifact withdrawn.",)
    assert snapshot.limitations == ("Governance metadata only.",)
    assert snapshot.uncertainty_factors == ("Data provenance unresolved.",)
    assert snapshot.failure_modes == ("Evidence decay.",)
    assert snapshot.non_claims == ("No capital authority is represented.",)


def test_risk_authority_snapshot_accepts_valid_metadata_only_inputs() -> None:
    snapshot = risk_snapshot()

    assert snapshot.authority_id == "risk-authority-sma-200"
    assert snapshot.strategy_id == "strategy-sma-200"
    assert snapshot.as_of_date == date(2026, 5, 17)
    assert snapshot.risk_policy_ids == ("risk-policy-001",)
    assert set(field.name for field in fields(snapshot)).isdisjoint(
        _FORBIDDEN_FIELD_NAMES
    )


def test_risk_authority_snapshot_is_frozen_and_slotted() -> None:
    snapshot = risk_snapshot()

    assert hasattr(RiskAuthoritySnapshot, "__slots__")
    assert not hasattr(snapshot, "__dict__")
    with pytest.raises(FrozenInstanceError):
        snapshot.authority_id = "changed"


def test_risk_authority_snapshot_normalizes_sequences_to_immutable_tuples() -> None:
    risk_policy_ids = ["risk-policy-001"]
    active_constraints = ["Manual review required."]
    revocation_triggers = ["Risk policy superseded."]

    snapshot = risk_snapshot(
        risk_policy_ids=risk_policy_ids,
        active_constraints=active_constraints,
        revocation_triggers=revocation_triggers,
    )
    risk_policy_ids.append("late-policy")
    active_constraints.append("late-constraint")
    revocation_triggers.append("late-trigger")

    assert snapshot.risk_policy_ids == ("risk-policy-001",)
    assert snapshot.active_constraints == ("Manual review required.",)
    assert snapshot.revocation_triggers == ("Risk policy superseded.",)
    with pytest.raises(TypeError):
        snapshot.active_constraints[0] = "changed"


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("authority_id", ""),
        ("authority_id", " "),
        ("authority_id", True),
        ("strategy_id", ""),
        ("strategy_id", " "),
        ("strategy_id", False),
    ),
)
def test_risk_authority_snapshot_rejects_empty_or_non_string_ids(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        risk_snapshot(**{field_name: value})


def test_risk_authority_snapshot_rejects_datetime_as_as_of_date() -> None:
    with pytest.raises(ValidationError, match="as_of_date"):
        risk_snapshot(as_of_date=datetime(2026, 5, 17))


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("risk_policy_ids", "risk-policy-001"),
        ("risk_policy_ids", ("valid", None)),
        ("active_constraints", ("valid", True)),
        ("promotion_requirements", ("valid", "")),
        ("revocation_triggers", ("valid", " ")),
        ("blocking_reasons", ("valid", 1)),
        ("limitations", "one limitation"),
        ("uncertainty_factors", ("valid", False)),
        ("failure_modes", ("valid", "")),
        ("non_claims", ("valid", " ")),
    ),
)
def test_risk_authority_snapshot_rejects_malformed_tuple_entries(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        risk_snapshot(**{field_name: value})


def test_risk_authority_snapshot_rejects_live_probe_without_paper() -> None:
    with pytest.raises(ValidationError, match="paper_allowed"):
        risk_snapshot(live_probe_allowed=True, paper_allowed=False)


def test_risk_authority_snapshot_rejects_live_allowed_without_paper() -> None:
    with pytest.raises(ValidationError, match="paper_allowed"):
        risk_snapshot(
            paper_allowed=False,
            live_probe_allowed=False,
            live_allowed=True,
            blocking_reasons=(),
        )


def test_risk_authority_snapshot_rejects_live_allowed_without_probe() -> None:
    with pytest.raises(ValidationError, match="live_probe_allowed"):
        risk_snapshot(
            paper_allowed=True,
            live_probe_allowed=False,
            live_allowed=True,
            blocking_reasons=(),
        )


def test_risk_authority_snapshot_rejects_live_allowed_with_kill_switch() -> None:
    with pytest.raises(ValidationError, match="kill_switch_active"):
        live_risk_snapshot(kill_switch_active=True)


def test_risk_authority_snapshot_rejects_live_allowed_with_blockers() -> None:
    with pytest.raises(ValidationError, match="blocking_reasons"):
        live_risk_snapshot(blocking_reasons=("Open risk blocker.",))


def test_risk_authority_paper_allowed_does_not_imply_live_readiness() -> None:
    snapshot = paper_risk_snapshot()

    assert snapshot.paper_allowed is True
    assert snapshot.live_probe_allowed is False
    assert snapshot.live_allowed is False


def test_risk_authority_live_probe_is_operational_metadata_only() -> None:
    snapshot = live_probe_risk_snapshot()
    field_names = tuple(field.name for field in fields(snapshot))

    assert snapshot.live_probe_allowed is True
    assert snapshot.live_allowed is False
    assert "profitability" not in field_names
    assert "profitable" not in field_names


def test_risk_authority_preserves_required_governance_metadata() -> None:
    snapshot = risk_snapshot(
        active_constraints=("Max exposure constraint under review.",),
        promotion_requirements=("Approve risk policy bundle.",),
        revocation_triggers=("Kill switch activated.",),
        limitations=("Risk metadata only.",),
        uncertainty_factors=("Constraint coverage unresolved.",),
        failure_modes=("Risk control drift.",),
        non_claims=("No capital authority is represented.",),
    )

    assert snapshot.active_constraints == ("Max exposure constraint under review.",)
    assert snapshot.promotion_requirements == ("Approve risk policy bundle.",)
    assert snapshot.revocation_triggers == ("Kill switch activated.",)
    assert snapshot.limitations == ("Risk metadata only.",)
    assert snapshot.uncertainty_factors == ("Constraint coverage unresolved.",)
    assert snapshot.failure_modes == ("Risk control drift.",)
    assert snapshot.non_claims == ("No capital authority is represented.",)


def test_strategy_mandate_snapshot_to_dict_is_deterministic_primitive_data() -> None:
    snapshot = live_strategy_snapshot()

    first_payload = snapshot.to_dict()
    second_payload = snapshot.to_dict()

    assert first_payload == second_payload
    assert first_payload == {
        "strategy_id": "strategy-sma-200",
        "mandate_id": "mandate-sma-200",
        "as_of_date": "2026-05-17",
        "mandate_approved": True,
        "evidence_approved": True,
        "paper_eligible": True,
        "live_probe_eligible": True,
        "live_authorized": True,
        "validated_research_artifact_ids": ["research-artifact-001"],
        "validated_signal_definition_ids": ["signal-definition-001"],
        "required_evidence": ["Independent evidence review is required."],
        "promotion_requirements": ["Approve deterministic evidence package."],
        "revocation_triggers": ["Evidence package is superseded."],
        "blocking_reasons": [],
        "limitations": ["Metadata source snapshot only."],
        "uncertainty_factors": ["Evidence coverage remains incomplete."],
        "failure_modes": ["Mandate assumptions may become stale."],
        "non_claims": ["No capital authority is represented."],
    }
    assert isinstance(first_payload["as_of_date"], str)
    assert isinstance(first_payload["required_evidence"], list)
    _assert_primitive_json_compatible(first_payload)
    assert "StrategyMandateSnapshot(" not in str(first_payload)
    assert " at 0x" not in str(first_payload)


def test_risk_authority_snapshot_to_dict_is_deterministic_primitive_data() -> None:
    snapshot = live_risk_snapshot()

    first_payload = snapshot.to_dict()
    second_payload = snapshot.to_dict()

    assert first_payload == second_payload
    assert first_payload == {
        "authority_id": "risk-authority-sma-200",
        "strategy_id": "strategy-sma-200",
        "as_of_date": "2026-05-17",
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_allowed": True,
        "kill_switch_active": False,
        "risk_policy_ids": ["risk-policy-001"],
        "active_constraints": ["Manual review required before promotion."],
        "promotion_requirements": ["Approve deterministic risk constraints."],
        "revocation_triggers": ["Risk policy is superseded."],
        "blocking_reasons": [],
        "limitations": ["Risk authority source snapshot only."],
        "uncertainty_factors": ["Operational assumptions remain unresolved."],
        "failure_modes": ["Control review may become stale."],
        "non_claims": ["No capital authority is represented."],
    }
    assert isinstance(first_payload["as_of_date"], str)
    assert isinstance(first_payload["active_constraints"], list)
    _assert_primitive_json_compatible(first_payload)
    assert "RiskAuthoritySnapshot(" not in str(first_payload)
    assert " at 0x" not in str(first_payload)


def test_to_dict_lists_do_not_mutate_source_snapshots() -> None:
    strategy = strategy_snapshot()
    risk = risk_snapshot()

    strategy_payload = strategy.to_dict()
    risk_payload = risk.to_dict()
    strategy_payload["required_evidence"].append("late evidence")
    risk_payload["active_constraints"].append("late constraint")

    assert strategy.required_evidence == ("Independent evidence review is required.",)
    assert risk.active_constraints == ("Manual review required before promotion.",)
    assert strategy.to_dict()["required_evidence"] == [
        "Independent evidence review is required."
    ]
    assert risk.to_dict()["active_constraints"] == [
        "Manual review required before promotion."
    ]


def test_snapshot_contracts_expose_no_forbidden_fields() -> None:
    for contract in (StrategyMandateSnapshot, RiskAuthoritySnapshot):
        field_names = {field.name for field in fields(contract)}

        assert field_names.isdisjoint(_FORBIDDEN_FIELD_NAMES)
        for forbidden_fragment in (
            "broker",
            "order",
            "fill",
            "account",
            "position",
            "portfolio",
            "allocation",
            "target_weight",
            "execution",
            "runtime",
            "scheduler",
            "score",
            "rank",
            "recommendation",
            "candidate_discovery",
        ):
            assert all(forbidden_fragment not in name for name in field_names)


def test_snapshot_contracts_expose_no_trading_or_discovery_behavior() -> None:
    strategy = strategy_snapshot()
    risk = risk_snapshot()

    for snapshot in (strategy, risk):
        for behavior_name in (
            "approve_trade",
            "discover_candidate",
            "generate_signal",
            "rank_candidate",
            "recommend",
            "score_strategy",
            "submit_order",
            "update_portfolio",
        ):
            assert not hasattr(snapshot, behavior_name)


def test_non_claims_do_not_contain_trading_recommendation_language() -> None:
    strategy = strategy_snapshot()
    risk = risk_snapshot()

    for snapshot in (strategy, risk):
        for non_claim in snapshot.non_claims:
            normalized = non_claim.lower()
            for term in _TRADING_RECOMMENDATION_LANGUAGE:
                assert term not in normalized


def test_governance_status_snapshot_module_imports_no_forbidden_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_governance_status_snapshot_module_references_no_forbidden_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_governance_status_snapshot_module_makes_no_forbidden_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _assert_primitive_json_compatible(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, Enum)
    assert not isinstance(value, tuple)
    assert not isinstance(value, set)
    assert not isinstance(value, Decimal)
    assert not isinstance(value, date)
    assert not callable(value)
    assert not isinstance(value, ModuleType)

    if value is None or type(value) in (str, bool, int, float):
        return

    if type(value) is list:
        for item in value:
            _assert_primitive_json_compatible(item)
        return

    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_json_compatible(item)
        return

    raise AssertionError(f"non-primitive serialized value: {type(value)!r}")


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


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


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
