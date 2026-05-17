import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import pytest

from algotrader.advisory import (
    AdvisoryLabel,
    OperatingBrief,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
)
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/advisory/operating_brief.py")

_FORBIDDEN_FIELD_NAMES = {
    "account",
    "account_id",
    "alpaca",
    "api_key",
    "broker",
    "broker_order_id",
    "cash",
    "client_order_id",
    "credential",
    "credentials",
    "execution",
    "execution_plan",
    "fill",
    "fill_id",
    "filled",
    "market_data",
    "order",
    "order_id",
    "orders",
    "portfolio",
    "portfolio_state",
    "position",
    "positions",
    "quantity",
    "runtime",
    "scheduler",
    "sdk",
    "signal",
    "submit_order",
    "venue",
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
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
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
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
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
    "SignalEvaluationResult",
    "account",
    "account_id",
    "alpaca",
    "api_key",
    "broker",
    "broker_order_id",
    "cash",
    "client_order_id",
    "credential",
    "execution",
    "fill",
    "market_data",
    "portfolio",
    "position",
    "quantity",
    "runtime",
    "scheduler",
    "sdk",
    "signal",
    "submit_order",
    "venue",
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
    "import_module",
    "importlib.import_module",
    "open",
    "os.getenv",
    "post",
    "read",
    "request",
    "socket.socket",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "write",
}


def dossier(**overrides: object) -> ResearchCandidateDossier:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "title": "ETF trend research candidate",
        "summary": "Advisory metadata for future review only.",
        "advisory_label": AdvisoryLabel.RESEARCH_ONLY,
        "uncertainty_factors": ("Input provenance is not yet reviewed.",),
        "failure_modes": ("Regime shift could invalidate assumptions.",),
        "next_questions": ("What deterministic evidence package is required?",),
        "limitations": ("No trading action is authorized.",),
    }
    values.update(overrides)
    return ResearchCandidateDossier(**values)


def strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "mandate_id": None,
        "mandate_approved": False,
        "evidence_approved": False,
        "evidence_refs": (),
        "paper_eligible": False,
        "live_probe_eligible": False,
        "live_authorized": False,
        "blocking_reasons": ("No approved strategy mandate.",),
        "limitations": ("Advisory status only.",),
    }
    values.update(overrides)
    return StrategyEligibilityStatus(**values)


def paper_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-paper-001",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-package-001",),
        "paper_eligible": True,
        "live_probe_eligible": False,
        "live_authorized": False,
        "blocking_reasons": ("Live probe mandate is not approved.",),
    }
    values.update(overrides)
    return strategy_status(**values)


def live_probe_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-probe-001",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-package-001",),
        "paper_eligible": True,
        "live_probe_eligible": True,
        "live_authorized": False,
        "blocking_reasons": ("Live authorization is not approved.",),
    }
    values.update(overrides)
    return strategy_status(**values)


def live_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-live-001",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-package-001",),
        "paper_eligible": True,
        "live_probe_eligible": True,
        "live_authorized": True,
        "blocking_reasons": (),
    }
    values.update(overrides)
    return strategy_status(**values)


def risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "authority_id": None,
        "paper_allowed": False,
        "live_probe_allowed": False,
        "live_authorized": False,
        "blocking_reasons": ("No risk authority is approved.",),
        "limitations": ("Authority metadata grants no trading action by itself.",),
    }
    values.update(overrides)
    return RiskAuthorityStatus(**values)


def paper_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-paper-001",
        "paper_allowed": True,
        "live_probe_allowed": False,
        "live_authorized": False,
        "blocking_reasons": ("Live probe authority is not approved.",),
    }
    values.update(overrides)
    return risk_status(**values)


def live_probe_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-probe-001",
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_authorized": False,
        "blocking_reasons": ("Live authorization is not approved.",),
    }
    values.update(overrides)
    return risk_status(**values)


def live_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-live-001",
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_authorized": True,
        "blocking_reasons": (),
    }
    values.update(overrides)
    return risk_status(**values)


def brief(**overrides: object) -> OperatingBrief:
    values: dict[str, object] = {
        "brief_id": "brief-2026-05-17",
        "as_of_date": date(2026, 5, 17),
        "dossiers": (dossier(),),
        "strategy_statuses": (),
        "risk_statuses": (),
        "limitations": ("Advisory metadata only.",),
    }
    values.update(overrides)
    return OperatingBrief(**values)


def test_advisory_labels_are_exactly_the_allowed_values() -> None:
    assert tuple(label.value for label in AdvisoryLabel) == (
        "research_only",
        "watchlist_only",
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
    )


def test_research_candidate_dossier_is_frozen_and_slotted() -> None:
    item = dossier()

    assert hasattr(ResearchCandidateDossier, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.summary = "changed"


def test_dossier_normalizes_uncertainty_failure_modes_and_questions() -> None:
    uncertainty = ["Unreviewed source package."]
    failure_modes = ["False positive from stale assumptions."]
    next_questions = ["Which evidence artifact is required?"]

    item = dossier(
        uncertainty_factors=uncertainty,
        failure_modes=failure_modes,
        next_questions=next_questions,
    )
    uncertainty.append("late uncertainty")
    failure_modes.append("late failure mode")
    next_questions.append("late question")

    assert item.uncertainty_factors == ("Unreviewed source package.",)
    assert item.failure_modes == ("False positive from stale assumptions.",)
    assert item.next_questions == ("Which evidence artifact is required?",)
    with pytest.raises(TypeError):
        item.failure_modes[0] = "changed"


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("candidate_id", " "),
        ("title", ""),
        ("summary", 42),
        ("advisory_label", "approved_trade"),
        ("advisory_label", ["research_only"]),
        ("uncertainty_factors", ()),
        ("uncertainty_factors", "uncertain"),
        ("uncertainty_factors", ("valid", 7)),
        ("failure_modes", ()),
        ("failure_modes", "single failure"),
        ("failure_modes", ("valid", "")),
        ("next_questions", ()),
        ("next_questions", ("valid", None)),
        ("limitations", ()),
        ("limitations", ("valid", " ")),
    ),
)
def test_dossier_rejects_malformed_fields(field_name: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field_name):
        dossier(**{field_name: value})


def test_dossier_has_explicit_uncertainty_and_failure_mode_fields_only() -> None:
    field_names = tuple(field.name for field in fields(ResearchCandidateDossier))

    assert field_names == (
        "candidate_id",
        "title",
        "summary",
        "advisory_label",
        "uncertainty_factors",
        "failure_modes",
        "next_questions",
        "limitations",
    )
    assert "uncertainty_factors" in field_names
    assert "failure_modes" in field_names
    assert set(field_names).isdisjoint(_FORBIDDEN_FIELD_NAMES)


def test_strategy_eligibility_status_is_frozen_and_slotted() -> None:
    status = strategy_status()

    assert hasattr(StrategyEligibilityStatus, "__slots__")
    assert not hasattr(status, "__dict__")
    with pytest.raises(FrozenInstanceError):
        status.paper_eligible = True


def test_strategy_status_requires_explicit_mandate_and_evidence_status() -> None:
    with pytest.raises(TypeError):
        StrategyEligibilityStatus(candidate_id="candidate-001")

    with pytest.raises(ValidationError, match="approved mandate and evidence"):
        strategy_status(paper_eligible=True)

    with pytest.raises(ValidationError, match="mandate_id"):
        strategy_status(
            mandate_approved=True,
            evidence_approved=True,
            evidence_refs=("evidence-package-001",),
            paper_eligible=True,
        )

    with pytest.raises(ValidationError, match="evidence_refs"):
        strategy_status(
            mandate_id="mandate-001",
            mandate_approved=True,
            evidence_approved=True,
            paper_eligible=True,
        )


def test_strategy_status_includes_blocking_reasons_and_metadata_fields_only() -> None:
    field_names = tuple(field.name for field in fields(StrategyEligibilityStatus))

    assert field_names == (
        "candidate_id",
        "mandate_id",
        "mandate_approved",
        "evidence_approved",
        "evidence_refs",
        "paper_eligible",
        "live_probe_eligible",
        "live_authorized",
        "blocking_reasons",
        "limitations",
    )
    assert "blocking_reasons" in field_names
    assert set(field_names).isdisjoint(_FORBIDDEN_FIELD_NAMES)


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("candidate_id", ""),
        ("mandate_id", ""),
        ("mandate_approved", 1),
        ("evidence_approved", "yes"),
        ("evidence_refs", "evidence-package-001"),
        ("evidence_refs", ("valid", None)),
        ("paper_eligible", None),
        ("live_probe_eligible", 1),
        ("live_authorized", "no"),
        ("blocking_reasons", "none"),
        ("limitations", ("valid", "")),
    ),
)
def test_strategy_status_rejects_malformed_fields(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        strategy_status(**{field_name: value})


def test_strategy_status_rejects_implied_higher_authority() -> None:
    with pytest.raises(ValidationError, match="paper_eligible"):
        strategy_status(
            mandate_id="mandate-001",
            mandate_approved=True,
            evidence_approved=True,
            evidence_refs=("evidence-package-001",),
            live_probe_eligible=True,
        )

    with pytest.raises(ValidationError, match="live_probe_eligible"):
        strategy_status(
            mandate_id="mandate-001",
            mandate_approved=True,
            evidence_approved=True,
            evidence_refs=("evidence-package-001",),
            paper_eligible=True,
            live_authorized=True,
        )


def test_risk_authority_status_is_frozen_and_slotted() -> None:
    status = risk_status()

    assert hasattr(RiskAuthorityStatus, "__slots__")
    assert not hasattr(status, "__dict__")
    with pytest.raises(FrozenInstanceError):
        status.paper_allowed = True


def test_risk_status_includes_explicit_authority_flags_and_blocking_reasons() -> None:
    field_names = tuple(field.name for field in fields(RiskAuthorityStatus))

    assert field_names == (
        "candidate_id",
        "authority_id",
        "paper_allowed",
        "live_probe_allowed",
        "live_authorized",
        "blocking_reasons",
        "limitations",
    )
    assert {"paper_allowed", "live_probe_allowed", "live_authorized"}.issubset(
        field_names
    )
    assert "blocking_reasons" in field_names
    assert set(field_names).isdisjoint(_FORBIDDEN_FIELD_NAMES)


def test_risk_status_requires_explicit_flags_and_authority_metadata() -> None:
    with pytest.raises(TypeError):
        RiskAuthorityStatus(candidate_id="candidate-001")

    with pytest.raises(ValidationError, match="authority_id"):
        risk_status(paper_allowed=True)

    with pytest.raises(ValidationError, match="paper_allowed"):
        risk_status(authority_id="risk-001", live_probe_allowed=True)

    with pytest.raises(ValidationError, match="live_probe_allowed"):
        risk_status(
            authority_id="risk-001",
            paper_allowed=True,
            live_authorized=True,
        )

    with pytest.raises(ValidationError, match="blocking_reasons"):
        risk_status(
            authority_id="risk-001",
            paper_allowed=True,
            blocking_reasons=(),
        )


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("candidate_id", ""),
        ("authority_id", ""),
        ("paper_allowed", 1),
        ("live_probe_allowed", "yes"),
        ("live_authorized", None),
        ("blocking_reasons", "none"),
        ("blocking_reasons", ("valid", None)),
        ("limitations", ()),
        ("limitations", "single limitation"),
        ("limitations", ("valid", "")),
    ),
)
def test_risk_status_rejects_malformed_fields(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        risk_status(**{field_name: value})


def test_risk_status_does_not_mutate_inputs_or_external_state() -> None:
    blocking_reasons = ["No live authority."]
    limitations = ["Operational eligibility only."]

    status = risk_status(
        blocking_reasons=blocking_reasons,
        limitations=limitations,
    )
    blocking_reasons.append("late reason")
    limitations.append("late limitation")

    assert status.blocking_reasons == ("No live authority.",)
    assert status.limitations == ("Operational eligibility only.",)


def test_operating_brief_is_frozen_and_slotted() -> None:
    item = brief()

    assert hasattr(OperatingBrief, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.brief_id = "changed"


def test_operating_brief_normalizes_collections_and_preserves_identity() -> None:
    candidate = dossier()
    strategy = strategy_status()
    authority = risk_status()

    item = brief(
        dossiers=[candidate],
        strategy_statuses=[strategy],
        risk_statuses=[authority],
        limitations=["Advisory bundle only."],
    )

    assert item.dossiers == (candidate,)
    assert item.strategy_statuses == (strategy,)
    assert item.risk_statuses == (authority,)
    assert item.dossiers[0] is candidate
    assert item.strategy_statuses[0] is strategy
    assert item.risk_statuses[0] is authority
    assert item.limitations == ("Advisory bundle only.",)


def test_research_and_watchlist_candidates_need_no_actionability_statuses() -> None:
    research = dossier(candidate_id="research-001")
    watchlist = dossier(
        candidate_id="watchlist-001",
        advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
    )

    item = brief(dossiers=(research, watchlist))

    assert item.dossiers == (research, watchlist)
    assert item.strategy_statuses == ()
    assert item.risk_statuses == ()


def test_operating_brief_rejects_actionable_labels_without_strategy_support() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)

    with pytest.raises(ValidationError, match="strategy eligibility support"):
        brief(dossiers=(candidate,))


def test_operating_brief_rejects_actionable_labels_without_risk_support() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)

    with pytest.raises(ValidationError, match="risk authority support"):
        brief(dossiers=(candidate,), strategy_statuses=(paper_strategy_status(),))


def test_operating_brief_rejects_actionable_labels_without_matching_support() -> None:
    paper_candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)
    probe_candidate = dossier(advisory_label=AdvisoryLabel.LIVE_PROBE_ELIGIBLE)

    with pytest.raises(ValidationError, match="paper_eligible"):
        brief(
            dossiers=(paper_candidate,),
            strategy_statuses=(
                strategy_status(
                    mandate_id="mandate-review-001",
                    mandate_approved=True,
                    evidence_approved=True,
                    evidence_refs=("evidence-package-001",),
                ),
            ),
            risk_statuses=(paper_risk_status(),),
        )

    with pytest.raises(ValidationError, match="live_probe_eligible"):
        brief(
            dossiers=(probe_candidate,),
            strategy_statuses=(paper_strategy_status(),),
            risk_statuses=(paper_risk_status(),),
        )


def test_paper_eligible_does_not_imply_live_readiness() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)
    strategy = paper_strategy_status()
    authority = paper_risk_status()

    item = brief(
        dossiers=(candidate,),
        strategy_statuses=(strategy,),
        risk_statuses=(authority,),
    )

    assert item.dossiers[0].advisory_label is AdvisoryLabel.PAPER_ELIGIBLE
    assert item.strategy_statuses[0].paper_eligible is True
    assert item.strategy_statuses[0].live_probe_eligible is False
    assert item.risk_statuses[0].paper_allowed is True
    assert item.risk_statuses[0].live_probe_allowed is False


def test_live_probe_eligible_remains_operational_metadata_only() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.LIVE_PROBE_ELIGIBLE)

    item = brief(
        dossiers=(candidate,),
        strategy_statuses=(live_probe_strategy_status(),),
        risk_statuses=(live_probe_risk_status(),),
    )

    assert item.dossiers[0].advisory_label is AdvisoryLabel.LIVE_PROBE_ELIGIBLE
    for field_name in ("profitability", "profitable", "strategy_validated"):
        assert not hasattr(item.dossiers[0], field_name)
        assert not hasattr(item.strategy_statuses[0], field_name)
        assert not hasattr(item.risk_statuses[0], field_name)


def test_live_authorized_requires_strategy_and_risk_authority() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.LIVE_AUTHORIZED)

    with pytest.raises(ValidationError, match="live_authorized"):
        brief(
            dossiers=(candidate,),
            strategy_statuses=(live_strategy_status(),),
            risk_statuses=(live_probe_risk_status(),),
        )

    with pytest.raises(ValidationError, match="live_authorized"):
        brief(
            dossiers=(candidate,),
            strategy_statuses=(live_probe_strategy_status(),),
            risk_statuses=(live_risk_status(),),
        )

    item = brief(
        dossiers=(candidate,),
        strategy_statuses=(live_strategy_status(),),
        risk_statuses=(live_risk_status(),),
    )

    assert item.dossiers[0].advisory_label is AdvisoryLabel.LIVE_AUTHORIZED
    assert item.strategy_statuses[0].live_authorized is True
    assert item.risk_statuses[0].live_authorized is True


def test_operating_brief_rejects_malformed_fields_and_unknown_statuses() -> None:
    candidate = dossier()

    with pytest.raises(ValidationError, match="brief_id"):
        brief(brief_id="")
    with pytest.raises(ValidationError, match="as_of_date"):
        brief(as_of_date=datetime(2026, 5, 17))
    with pytest.raises(ValidationError, match="advisory_only"):
        brief(advisory_only=False)
    with pytest.raises(ValidationError, match="duplicate"):
        brief(dossiers=(candidate, candidate))
    with pytest.raises(ValidationError, match="not in dossiers"):
        brief(strategy_statuses=(strategy_status(candidate_id="other-candidate"),))
    with pytest.raises(ValidationError, match="not in dossiers"):
        brief(risk_statuses=(risk_status(candidate_id="other-candidate"),))


def test_operating_brief_exposes_no_trading_behavior() -> None:
    item = brief()

    for field_name in _FORBIDDEN_FIELD_NAMES:
        assert not hasattr(item, field_name)
    for behavior_name in (
        "approve_trade",
        "create_signal",
        "generate_signal",
        "place_order",
        "submit_order",
        "update_portfolio",
    ):
        assert not hasattr(item, behavior_name)


def test_dossier_to_dict_returns_deterministic_primitive_metadata() -> None:
    item = dossier(advisory_label=AdvisoryLabel.WATCHLIST_ONLY)

    payload = item.to_dict()

    assert payload == {
        "candidate_id": "candidate-001",
        "title": "ETF trend research candidate",
        "summary": "Advisory metadata for future review only.",
        "advisory_label": "watchlist_only",
        "uncertainty_factors": ["Input provenance is not yet reviewed."],
        "failure_modes": ["Regime shift could invalidate assumptions."],
        "next_questions": ["What deterministic evidence package is required?"],
        "limitations": ["No trading action is authorized."],
    }
    assert isinstance(payload, dict)
    assert isinstance(payload["advisory_label"], str)
    assert isinstance(payload["uncertainty_factors"], list)
    assert isinstance(payload["failure_modes"], list)
    assert "uncertainty_factors" in payload
    assert "failure_modes" in payload
    assert set(payload).isdisjoint(_FORBIDDEN_FIELD_NAMES)
    _assert_primitive_json_compatible(payload)
    assert item.to_dict() == payload


def test_dossier_to_dict_does_not_mutate_source_object() -> None:
    item = dossier()

    payload = item.to_dict()
    payload["uncertainty_factors"].append("late uncertainty")
    payload["failure_modes"].append("late failure mode")
    payload["next_questions"].append("late question")

    assert item.uncertainty_factors == ("Input provenance is not yet reviewed.",)
    assert item.failure_modes == ("Regime shift could invalidate assumptions.",)
    assert item.next_questions == ("What deterministic evidence package is required?",)
    assert item.to_dict()["uncertainty_factors"] == [
        "Input provenance is not yet reviewed."
    ]


def test_strategy_status_to_dict_returns_deterministic_primitive_metadata() -> None:
    status = paper_strategy_status(limitations=("Paper metadata only.",))

    payload = status.to_dict()

    assert payload == {
        "candidate_id": "candidate-001",
        "mandate_id": "mandate-paper-001",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ["evidence-package-001"],
        "paper_eligible": True,
        "live_probe_eligible": False,
        "live_authorized": False,
        "blocking_reasons": ["Live probe mandate is not approved."],
        "limitations": ["Paper metadata only."],
    }
    assert isinstance(payload, dict)
    assert isinstance(payload["evidence_refs"], list)
    assert "blocking_reasons" in payload
    assert "limitations" in payload
    assert set(payload).isdisjoint(_FORBIDDEN_FIELD_NAMES)
    _assert_primitive_json_compatible(payload)
    assert status.to_dict() == payload
    assert strategy_status().to_dict()["mandate_id"] is None


def test_strategy_status_to_dict_does_not_mutate_source_object() -> None:
    status = paper_strategy_status()

    payload = status.to_dict()
    payload["evidence_refs"].append("late-evidence")
    payload["blocking_reasons"].append("late reason")

    assert status.evidence_refs == ("evidence-package-001",)
    assert status.blocking_reasons == ("Live probe mandate is not approved.",)
    assert status.to_dict()["evidence_refs"] == ["evidence-package-001"]


def test_risk_status_to_dict_returns_deterministic_primitive_metadata() -> None:
    status = paper_risk_status(limitations=("Paper risk authority metadata only.",))

    payload = status.to_dict()

    assert payload == {
        "candidate_id": "candidate-001",
        "authority_id": "risk-paper-001",
        "paper_allowed": True,
        "live_probe_allowed": False,
        "live_authorized": False,
        "blocking_reasons": ["Live probe authority is not approved."],
        "limitations": ["Paper risk authority metadata only."],
    }
    assert isinstance(payload, dict)
    assert isinstance(payload["blocking_reasons"], list)
    assert "paper_allowed" in payload
    assert "live_probe_allowed" in payload
    assert "live_authorized" in payload
    assert set(payload).isdisjoint(_FORBIDDEN_FIELD_NAMES)
    _assert_primitive_json_compatible(payload)
    assert status.to_dict() == payload
    assert risk_status().to_dict()["authority_id"] is None


def test_risk_status_to_dict_does_not_mutate_source_object() -> None:
    status = paper_risk_status()

    payload = status.to_dict()
    payload["blocking_reasons"].append("late reason")
    payload["limitations"].append("late limitation")

    assert status.blocking_reasons == ("Live probe authority is not approved.",)
    assert status.limitations == (
        "Authority metadata grants no trading action by itself.",
    )
    assert status.to_dict()["blocking_reasons"] == [
        "Live probe authority is not approved."
    ]


def test_operating_brief_to_dict_serializes_nested_objects_and_ordering() -> None:
    paper_candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)
    watchlist_candidate = dossier(
        candidate_id="candidate-002",
        advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
    )
    paper_strategy = paper_strategy_status()
    watchlist_strategy = strategy_status(candidate_id="candidate-002")
    paper_authority = paper_risk_status()
    watchlist_authority = risk_status(candidate_id="candidate-002")
    item = brief(
        dossiers=(paper_candidate, watchlist_candidate),
        strategy_statuses=(paper_strategy, watchlist_strategy),
        risk_statuses=(paper_authority, watchlist_authority),
    )

    payload = item.to_dict()

    assert payload == {
        "brief_id": "brief-2026-05-17",
        "as_of_date": "2026-05-17",
        "dossiers": [paper_candidate.to_dict(), watchlist_candidate.to_dict()],
        "strategy_statuses": [
            paper_strategy.to_dict(),
            watchlist_strategy.to_dict(),
        ],
        "risk_statuses": [
            paper_authority.to_dict(),
            watchlist_authority.to_dict(),
        ],
        "limitations": ["Advisory metadata only."],
        "advisory_only": True,
    }
    assert isinstance(payload, dict)
    assert payload["dossiers"][0]["candidate_id"] == "candidate-001"
    assert payload["dossiers"][1]["candidate_id"] == "candidate-002"
    assert payload["dossiers"][0]["advisory_label"] == "paper_eligible"
    assert isinstance(payload["dossiers"][0]["advisory_label"], str)
    assert payload["strategy_statuses"][0]["candidate_id"] == "candidate-001"
    assert payload["strategy_statuses"][1]["candidate_id"] == "candidate-002"
    assert payload["risk_statuses"][0]["candidate_id"] == "candidate-001"
    assert payload["risk_statuses"][1]["candidate_id"] == "candidate-002"
    _assert_primitive_json_compatible(payload)
    assert item.to_dict() == payload


def test_operating_brief_to_dict_is_deterministic_across_repeated_calls() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)
    item = brief(
        dossiers=(candidate,),
        strategy_statuses=(paper_strategy_status(),),
        risk_statuses=(paper_risk_status(),),
    )

    first_payload = item.to_dict()
    second_payload = item.to_dict()

    assert first_payload == second_payload


def test_operating_brief_to_dict_does_not_mutate_nested_objects() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)
    strategy = paper_strategy_status()
    authority = paper_risk_status()
    item = brief(
        dossiers=(candidate,),
        strategy_statuses=(strategy,),
        risk_statuses=(authority,),
    )

    payload = item.to_dict()
    payload["dossiers"][0]["failure_modes"].append("late failure mode")
    payload["strategy_statuses"][0]["evidence_refs"].append("late evidence")
    payload["risk_statuses"][0]["blocking_reasons"].append("late reason")
    payload["limitations"].append("late limitation")

    assert candidate.failure_modes == ("Regime shift could invalidate assumptions.",)
    assert strategy.evidence_refs == ("evidence-package-001",)
    assert authority.blocking_reasons == ("Live probe authority is not approved.",)
    assert item.limitations == ("Advisory metadata only.",)
    assert item.to_dict()["dossiers"][0]["failure_modes"] == [
        "Regime shift could invalidate assumptions."
    ]


def test_serialized_paper_and_live_probe_labels_do_not_imply_more_authority() -> None:
    paper_candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)
    paper_payload = brief(
        dossiers=(paper_candidate,),
        strategy_statuses=(paper_strategy_status(),),
        risk_statuses=(paper_risk_status(),),
    ).to_dict()

    assert paper_payload["dossiers"][0]["advisory_label"] == "paper_eligible"
    assert paper_payload["strategy_statuses"][0]["paper_eligible"] is True
    assert paper_payload["strategy_statuses"][0]["live_probe_eligible"] is False
    assert paper_payload["risk_statuses"][0]["live_probe_allowed"] is False

    probe_candidate = dossier(advisory_label=AdvisoryLabel.LIVE_PROBE_ELIGIBLE)
    probe_payload = brief(
        dossiers=(probe_candidate,),
        strategy_statuses=(live_probe_strategy_status(),),
        risk_statuses=(live_probe_risk_status(),),
    ).to_dict()

    assert probe_payload["dossiers"][0]["advisory_label"] == "live_probe_eligible"
    assert probe_payload["strategy_statuses"][0]["live_authorized"] is False
    assert probe_payload["risk_statuses"][0]["live_authorized"] is False
    _assert_no_forbidden_serialized_keys(paper_payload)
    _assert_no_forbidden_serialized_keys(probe_payload)
    for forbidden_key in ("profitability", "profitable", "strategy_validated"):
        assert forbidden_key not in _all_serialized_keys(probe_payload)


def test_serialized_live_authorized_remains_constructor_gated() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.LIVE_AUTHORIZED)

    with pytest.raises(ValidationError, match="live_authorized"):
        brief(
            dossiers=(candidate,),
            strategy_statuses=(live_strategy_status(),),
            risk_statuses=(live_probe_risk_status(),),
        )

    payload = brief(
        dossiers=(candidate,),
        strategy_statuses=(live_strategy_status(),),
        risk_statuses=(live_risk_status(),),
    ).to_dict()

    assert payload["dossiers"][0]["advisory_label"] == "live_authorized"
    assert payload["strategy_statuses"][0]["live_authorized"] is True
    assert payload["risk_statuses"][0]["live_authorized"] is True
    _assert_primitive_json_compatible(payload)


def test_serialized_operating_brief_contains_no_trading_runtime_or_action_keys() -> None:
    payload = brief().to_dict()

    _assert_no_forbidden_serialized_keys(payload)
    for forbidden_key in (
        "candidate_discovery",
        "evaluation",
        "evaluations",
        "fill",
        "fills",
        "order",
        "orders",
        "position",
        "positions",
        "portfolio_mutation",
        "rank",
        "ranking",
        "recommendation",
        "score",
        "scoring",
        "signal",
        "signals",
        "runtime_action",
    ):
        assert forbidden_key not in _all_serialized_keys(payload)
    assert " at 0x" not in str(payload)


def test_advisory_module_imports_no_forbidden_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_advisory_module_references_no_trading_runtime_or_external_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_advisory_module_makes_no_io_network_broker_llm_or_scheduler_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _assert_primitive_json_compatible(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, Enum)

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


def _assert_no_forbidden_serialized_keys(payload: object) -> None:
    assert _all_serialized_keys(payload).isdisjoint(_FORBIDDEN_FIELD_NAMES)


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
