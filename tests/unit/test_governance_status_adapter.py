import ast
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

import algotrader.advisory.governance_status_adapter as adapter
from algotrader.advisory import (
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    risk_authority_snapshot_to_risk_authority_status,
    strategy_mandate_snapshot_to_strategy_eligibility_status,
)
from algotrader.errors import ValidationError
from algotrader.governance import RiskAuthoritySnapshot, StrategyMandateSnapshot


MODULE_PATH = Path("src/algotrader/advisory/governance_status_adapter.py")

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
    "submit_order",
    "target_weight",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
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
    "AdvisoryLabel",
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "ExecutionIntent",
    "ExecutionPlan",
    "Fill",
    "LocalBroker",
    "OperatingBrief",
    "PortfolioState",
    "Position",
    "ProposedOrder",
    "ResearchCandidateDossier",
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
        "validated_research_artifact_ids": (
            "research-artifact-001",
            "research-artifact-002",
        ),
        "validated_signal_definition_ids": (
            "signal-definition-001",
            "signal-definition-002",
        ),
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
        "risk_policy_ids": ("risk-policy-001", "risk-policy-002"),
        "active_constraints": (
            "Manual review required before promotion.",
            "Probe size must remain capped.",
        ),
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


def adapt_strategy(
    snapshot: StrategyMandateSnapshot,
    *,
    candidate_id: object = "candidate-sma-200",
) -> StrategyEligibilityStatus:
    return strategy_mandate_snapshot_to_strategy_eligibility_status(
        snapshot,
        candidate_id=candidate_id,
    )


def adapt_risk(
    snapshot: RiskAuthoritySnapshot,
    *,
    candidate_id: object = "candidate-sma-200",
) -> RiskAuthorityStatus:
    return risk_authority_snapshot_to_risk_authority_status(
        snapshot,
        candidate_id=candidate_id,
    )


def test_strategy_adapter_converts_snapshot_to_strategy_status() -> None:
    snapshot = paper_strategy_snapshot()

    status = adapt_strategy(snapshot)

    assert isinstance(status, StrategyEligibilityStatus)
    assert status.candidate_id == "candidate-sma-200"
    assert status.mandate_id == "mandate-sma-200"
    assert status.mandate_approved is True
    assert status.evidence_approved is True
    assert status.evidence_refs == (
        "research-artifact-001",
        "research-artifact-002",
        "signal-definition-001",
        "signal-definition-002",
    )
    assert status.paper_eligible is True
    assert status.live_probe_eligible is False
    assert status.live_authorized is False
    assert status.blocking_reasons == (
        "Live probe mandate review is incomplete.",
    )
    assert status.limitations == ("Metadata source snapshot only.",)
    assert not hasattr(status, "__dict__")


def test_strategy_adapter_preserves_supported_tuple_ordering_only() -> None:
    snapshot = strategy_snapshot(
        validated_research_artifact_ids=("research-a", "research-b"),
        validated_signal_definition_ids=("signal-a", "signal-b"),
        blocking_reasons=("first blocker", "second blocker"),
        limitations=("first limitation", "second limitation"),
    )

    status = adapt_strategy(snapshot)

    assert status.evidence_refs == (
        "research-a",
        "research-b",
        "signal-a",
        "signal-b",
    )
    assert status.blocking_reasons == ("first blocker", "second blocker")
    assert status.limitations == ("first limitation", "second limitation")
    for unsupported_field in (
        "strategy_id",
        "as_of_date",
        "required_evidence",
        "promotion_requirements",
        "revocation_triggers",
        "uncertainty_factors",
        "failure_modes",
        "non_claims",
    ):
        assert not hasattr(status, unsupported_field)


def test_strategy_adapter_uses_existing_strategy_status_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    real_constructor = adapter.StrategyEligibilityStatus

    def spy_constructor(**kwargs: object) -> StrategyEligibilityStatus:
        calls.append(kwargs)
        return real_constructor(**kwargs)

    monkeypatch.setattr(adapter, "StrategyEligibilityStatus", spy_constructor)
    snapshot = paper_strategy_snapshot()

    status = adapter.strategy_mandate_snapshot_to_strategy_eligibility_status(
        snapshot,
        candidate_id="candidate-sma-200",
    )

    assert isinstance(status, real_constructor)
    assert calls == [
        {
            "candidate_id": "candidate-sma-200",
            "mandate_id": "mandate-sma-200",
            "mandate_approved": True,
            "evidence_approved": True,
            "evidence_refs": (
                "research-artifact-001",
                "research-artifact-002",
                "signal-definition-001",
                "signal-definition-002",
            ),
            "paper_eligible": True,
            "live_probe_eligible": False,
            "live_authorized": False,
            "blocking_reasons": (
                "Live probe mandate review is incomplete.",
            ),
            "limitations": ("Metadata source snapshot only.",),
        }
    ]


def test_strategy_adapter_does_not_mutate_source_and_is_deterministic() -> None:
    snapshot = paper_strategy_snapshot()
    before = snapshot.to_dict()

    first_status = adapt_strategy(snapshot)
    second_status = adapt_strategy(snapshot)

    assert first_status == second_status
    assert snapshot.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        first_status.paper_eligible = False


def test_strategy_adapter_live_snapshot_maps_to_live_authorized_status() -> None:
    status = adapt_strategy(live_strategy_snapshot())

    assert status.paper_eligible is True
    assert status.live_probe_eligible is True
    assert status.live_authorized is True
    assert status.blocking_reasons == ()


def test_strategy_adapter_paper_snapshot_stays_paper_only() -> None:
    status = adapt_strategy(paper_strategy_snapshot())

    assert status.paper_eligible is True
    assert status.live_probe_eligible is False
    assert status.live_authorized is False


def test_strategy_adapter_blocked_snapshot_does_not_upgrade_authority() -> None:
    snapshot = strategy_snapshot()

    status = adapt_strategy(snapshot)

    assert status.mandate_approved is False
    assert status.evidence_approved is False
    assert status.paper_eligible is False
    assert status.live_probe_eligible is False
    assert status.live_authorized is False
    assert status.blocking_reasons == ("Mandate review is incomplete.",)


def test_strategy_adapter_does_not_invent_evidence_or_authority() -> None:
    snapshot = paper_strategy_snapshot(
        validated_research_artifact_ids=(),
        validated_signal_definition_ids=(),
    )

    with pytest.raises(ValidationError, match="evidence_refs"):
        adapt_strategy(snapshot)


def test_risk_adapter_converts_snapshot_to_risk_status() -> None:
    snapshot = paper_risk_snapshot()

    status = adapt_risk(snapshot)

    assert isinstance(status, RiskAuthorityStatus)
    assert status.candidate_id == "candidate-sma-200"
    assert status.authority_id == "risk-authority-sma-200"
    assert status.paper_allowed is True
    assert status.live_probe_allowed is False
    assert status.live_authorized is False
    assert status.blocking_reasons == ("Live probe risk review is incomplete.",)
    assert status.limitations == ("Risk authority source snapshot only.",)
    assert not hasattr(status, "__dict__")


def test_risk_adapter_preserves_supported_tuple_ordering_only() -> None:
    snapshot = risk_snapshot(
        blocking_reasons=("first blocker", "second blocker"),
        limitations=("first limitation", "second limitation"),
    )

    status = adapt_risk(snapshot)

    assert status.blocking_reasons == ("first blocker", "second blocker")
    assert status.limitations == ("first limitation", "second limitation")
    for unsupported_field in (
        "strategy_id",
        "as_of_date",
        "kill_switch_active",
        "risk_policy_ids",
        "active_constraints",
        "promotion_requirements",
        "revocation_triggers",
        "uncertainty_factors",
        "failure_modes",
        "non_claims",
    ):
        assert not hasattr(status, unsupported_field)


def test_risk_adapter_uses_existing_risk_status_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    real_constructor = adapter.RiskAuthorityStatus

    def spy_constructor(**kwargs: object) -> RiskAuthorityStatus:
        calls.append(kwargs)
        return real_constructor(**kwargs)

    monkeypatch.setattr(adapter, "RiskAuthorityStatus", spy_constructor)
    snapshot = paper_risk_snapshot()

    status = adapter.risk_authority_snapshot_to_risk_authority_status(
        snapshot,
        candidate_id="candidate-sma-200",
    )

    assert isinstance(status, real_constructor)
    assert calls == [
        {
            "candidate_id": "candidate-sma-200",
            "authority_id": "risk-authority-sma-200",
            "paper_allowed": True,
            "live_probe_allowed": False,
            "live_authorized": False,
            "blocking_reasons": ("Live probe risk review is incomplete.",),
            "limitations": ("Risk authority source snapshot only.",),
        }
    ]


def test_risk_adapter_does_not_mutate_source_and_is_deterministic() -> None:
    snapshot = paper_risk_snapshot()
    before = snapshot.to_dict()

    first_status = adapt_risk(snapshot)
    second_status = adapt_risk(snapshot)

    assert first_status == second_status
    assert snapshot.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        first_status.paper_allowed = False


def test_risk_adapter_live_snapshot_maps_to_live_authorized_status() -> None:
    status = adapt_risk(live_risk_snapshot())

    assert status.paper_allowed is True
    assert status.live_probe_allowed is True
    assert status.live_authorized is True
    assert status.blocking_reasons == ()


def test_risk_adapter_paper_snapshot_stays_paper_only() -> None:
    status = adapt_risk(paper_risk_snapshot())

    assert status.paper_allowed is True
    assert status.live_probe_allowed is False
    assert status.live_authorized is False


def test_risk_adapter_kill_switch_snapshot_remains_blocked() -> None:
    snapshot = risk_snapshot(
        paper_allowed=True,
        live_probe_allowed=True,
        live_allowed=False,
        kill_switch_active=True,
        blocking_reasons=("Kill switch is active.",),
    )

    status = adapt_risk(snapshot)

    assert snapshot.kill_switch_active is True
    assert status.paper_allowed is True
    assert status.live_probe_allowed is True
    assert status.live_authorized is False
    assert status.blocking_reasons == ("Kill switch is active.",)


def test_risk_adapter_does_not_upgrade_authority() -> None:
    snapshot = risk_snapshot()

    status = adapt_risk(snapshot)

    assert status.paper_allowed is False
    assert status.live_probe_allowed is False
    assert status.live_authorized is False
    assert status.blocking_reasons == ("Risk authority review is incomplete.",)


def test_strategy_adapter_rejects_non_strategy_snapshot_inputs() -> None:
    with pytest.raises(ValidationError, match="StrategyMandateSnapshot"):
        strategy_mandate_snapshot_to_strategy_eligibility_status(
            risk_snapshot(),
            candidate_id="candidate-sma-200",
        )


def test_risk_adapter_rejects_non_risk_snapshot_inputs() -> None:
    with pytest.raises(ValidationError, match="RiskAuthoritySnapshot"):
        risk_authority_snapshot_to_risk_authority_status(
            strategy_snapshot(),
            candidate_id="candidate-sma-200",
        )


@pytest.mark.parametrize("candidate_id", ("", " ", True, False, 7, None))
def test_strategy_adapter_rejects_malformed_candidate_id(candidate_id: object) -> None:
    with pytest.raises(ValidationError, match="candidate_id"):
        adapt_strategy(strategy_snapshot(), candidate_id=candidate_id)


@pytest.mark.parametrize("candidate_id", ("", " ", True, False, 7, None))
def test_risk_adapter_rejects_malformed_candidate_id(candidate_id: object) -> None:
    with pytest.raises(ValidationError, match="candidate_id"):
        adapt_risk(risk_snapshot(), candidate_id=candidate_id)


def test_adapted_strategy_status_serialization_remains_primitive() -> None:
    status = adapt_strategy(paper_strategy_snapshot())

    first_payload = status.to_dict()
    second_payload = status.to_dict()

    assert first_payload == second_payload
    assert first_payload == {
        "candidate_id": "candidate-sma-200",
        "mandate_id": "mandate-sma-200",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": [
            "research-artifact-001",
            "research-artifact-002",
            "signal-definition-001",
            "signal-definition-002",
        ],
        "paper_eligible": True,
        "live_probe_eligible": False,
        "live_authorized": False,
        "blocking_reasons": ["Live probe mandate review is incomplete."],
        "limitations": ["Metadata source snapshot only."],
    }
    _assert_primitive_json_compatible(first_payload)
    assert " at 0x" not in str(first_payload)
    assert "StrategyEligibilityStatus(" not in str(first_payload)


def test_adapted_risk_status_serialization_remains_primitive() -> None:
    status = adapt_risk(paper_risk_snapshot())

    first_payload = status.to_dict()
    second_payload = status.to_dict()

    assert first_payload == second_payload
    assert first_payload == {
        "candidate_id": "candidate-sma-200",
        "authority_id": "risk-authority-sma-200",
        "paper_allowed": True,
        "live_probe_allowed": False,
        "live_authorized": False,
        "blocking_reasons": ["Live probe risk review is incomplete."],
        "limitations": ["Risk authority source snapshot only."],
    }
    _assert_primitive_json_compatible(first_payload)
    assert " at 0x" not in str(first_payload)
    assert "RiskAuthorityStatus(" not in str(first_payload)


def test_adapter_outputs_contain_no_forbidden_fields_or_selection_terms() -> None:
    payloads = (
        adapt_strategy(paper_strategy_snapshot()).to_dict(),
        adapt_risk(paper_risk_snapshot()).to_dict(),
    )

    for payload in payloads:
        keys = _all_serialized_keys(payload)
        assert keys.isdisjoint(_FORBIDDEN_FIELD_NAMES)
        for forbidden_key in (
            "candidate_discovery",
            "rank",
            "ranking",
            "recommendation",
            "score",
            "scoring",
        ):
            assert forbidden_key not in keys


def test_adapter_outputs_contain_no_trading_recommendation_language() -> None:
    payloads = (
        adapt_strategy(paper_strategy_snapshot()).to_dict(),
        adapt_risk(paper_risk_snapshot()).to_dict(),
    )

    for payload in payloads:
        serialized_text = str(payload).lower()
        for term in _TRADING_RECOMMENDATION_LANGUAGE:
            assert term not in serialized_text


def test_adapter_module_imports_no_forbidden_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_adapter_module_references_no_forbidden_trading_or_brief_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_adapter_module_makes_no_io_network_broker_llm_or_scheduler_calls() -> None:
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


def _all_serialized_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_serialized_keys(item))
        return keys

    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_serialized_keys(item))
        return keys

    return set()


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
