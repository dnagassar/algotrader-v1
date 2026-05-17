import ast
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

import algotrader.advisory.operating_brief_assembly as assembly
from algotrader.advisory import (
    AdvisoryLabel,
    OperatingBrief,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    assemble_operating_brief_from_parts,
    build_operating_brief_board_summary,
    render_operating_brief_board_summary_markdown,
    render_operating_brief_markdown,
)
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/advisory/operating_brief_assembly.py")

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.advisory.candidate_dossier_adapter",
    "algotrader.advisory.candidate_snapshot",
    "algotrader.advisory.governance_status_adapter",
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

_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "datetime",
    "algotrader.advisory.operating_brief",
    "algotrader.errors",
}

_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "CandidateDossierSnapshot",
    "ExecutionIntent",
    "ExecutionPlan",
    "Fill",
    "LocalBroker",
    "PortfolioState",
    "Position",
    "ProposedOrder",
    "RiskAuthoritySnapshot",
    "StrategyMandateSnapshot",
    "account",
    "account_id",
    "adapter",
    "alpaca",
    "api_key",
    "broker",
    "candidate_snapshot_to_research_candidate_dossier",
    "credential",
    "credentials",
    "discover",
    "discover_candidate",
    "discover_candidates",
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
    "recommend",
    "recommendation",
    "recommendations",
    "risk_authority_snapshot_to_risk_authority_status",
    "runtime",
    "scheduler",
    "score",
    "scoring",
    "sdk",
    "strategy_mandate_snapshot_to_strategy_eligibility_status",
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

_FORBIDDEN_SERIALIZED_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "broker",
    "broker_order",
    "broker_order_id",
    "candidate_discovery",
    "client_order_id",
    "credential",
    "credentials",
    "execution",
    "execution_request",
    "fill",
    "fill_id",
    "market_data",
    "order",
    "order_id",
    "orders",
    "portfolio",
    "portfolio_update",
    "position",
    "position_size",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "runtime",
    "scheduler",
    "score",
    "scoring",
    "submit_order",
    "target_weight",
}

_FORBIDDEN_PAYLOAD_TERMS = (
    "allocation",
    "broker",
    "candidate discovery",
    "candidate_discovery",
    "execution",
    "fill",
    "market data",
    "market_data",
    "order",
    "portfolio",
    "position",
    "rank",
    "ranking",
    "recommendation",
    "score",
    "scoring",
    "submit_order",
    "target_weight",
    "trade",
    "trading",
)


def dossier(**overrides: object) -> ResearchCandidateDossier:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "title": "ETF trend research candidate",
        "summary": "Prepared advisory metadata for future review.",
        "advisory_label": AdvisoryLabel.RESEARCH_ONLY,
        "uncertainty_factors": ("Input provenance is not yet reviewed.",),
        "failure_modes": ("Regime shift could invalidate assumptions.",),
        "next_questions": ("Which evidence package is required?",),
        "limitations": ("No capital action is authorized.",),
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
        "limitations": ("Strategy status metadata only.",),
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
        "limitations": ("Risk authority metadata only.",),
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


def assemble(**overrides: object) -> OperatingBrief:
    values: dict[str, object] = {
        "as_of_date": date(2026, 5, 17),
        "dossiers": (dossier(),),
        "strategy_statuses": (),
        "risk_statuses": (),
    }
    values.update(overrides)
    return assemble_operating_brief_from_parts(**values)


class DatedResearchCandidateDossier(ResearchCandidateDossier):
    __slots__ = ("as_of_date",)


class DatedStrategyEligibilityStatus(StrategyEligibilityStatus):
    __slots__ = ("as_of_date",)


class DatedRiskAuthorityStatus(RiskAuthorityStatus):
    __slots__ = ("as_of_date",)


def dated_dossier(as_of_date: date) -> DatedResearchCandidateDossier:
    item = DatedResearchCandidateDossier(
        candidate_id="candidate-dated",
        title="Dated advisory candidate",
        summary="Prepared advisory metadata with source date.",
        advisory_label=AdvisoryLabel.RESEARCH_ONLY,
        uncertainty_factors=("Source date is explicit.",),
        failure_modes=("Source date may be stale.",),
        next_questions=("Does the date match?",),
        limitations=("Dated source metadata only.",),
    )
    object.__setattr__(item, "as_of_date", as_of_date)
    return item


def dated_strategy_status(as_of_date: date) -> DatedStrategyEligibilityStatus:
    item = DatedStrategyEligibilityStatus(
        candidate_id="candidate-dated",
        mandate_id=None,
        mandate_approved=False,
        evidence_approved=False,
        evidence_refs=(),
        paper_eligible=False,
        live_probe_eligible=False,
        live_authorized=False,
        blocking_reasons=("No approved strategy mandate.",),
        limitations=("Dated strategy metadata only.",),
    )
    object.__setattr__(item, "as_of_date", as_of_date)
    return item


def dated_risk_status(as_of_date: date) -> DatedRiskAuthorityStatus:
    item = DatedRiskAuthorityStatus(
        candidate_id="candidate-dated",
        authority_id=None,
        paper_allowed=False,
        live_probe_allowed=False,
        live_authorized=False,
        blocking_reasons=("No risk authority is approved.",),
        limitations=("Dated risk metadata only.",),
    )
    object.__setattr__(item, "as_of_date", as_of_date)
    return item


def test_successful_assembly_preserves_order_and_uses_existing_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_candidate = dossier(candidate_id="candidate-first")
    second_candidate = dossier(
        candidate_id="candidate-second",
        advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
    )
    first_strategy = strategy_status(candidate_id="candidate-first")
    second_strategy = strategy_status(candidate_id="candidate-second")
    first_risk = risk_status(candidate_id="candidate-first")
    second_risk = risk_status(candidate_id="candidate-second")
    calls: list[dict[str, object]] = []
    real_constructor = assembly.OperatingBrief

    def spy_constructor(**kwargs: object) -> OperatingBrief:
        calls.append(kwargs)
        return real_constructor(**kwargs)

    monkeypatch.setattr(assembly, "OperatingBrief", spy_constructor)

    item = assembly.assemble_operating_brief_from_parts(
        as_of_date=date(2026, 5, 17),
        dossiers=[first_candidate, second_candidate],
        strategy_statuses=[second_strategy, first_strategy],
        risk_statuses=[second_risk, first_risk],
    )

    assert isinstance(item, real_constructor)
    assert is_dataclass(item)
    assert "__slots__" in OperatingBrief.__dict__
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.brief_id = "changed"
    assert item.brief_id == "brief-2026-05-17"
    assert item.as_of_date == date(2026, 5, 17)
    assert item.dossiers == (first_candidate, second_candidate)
    assert item.strategy_statuses == (second_strategy, first_strategy)
    assert item.risk_statuses == (second_risk, first_risk)
    assert item.limitations == ("Advisory metadata only.",)
    assert calls == [
        {
            "brief_id": "brief-2026-05-17",
            "as_of_date": date(2026, 5, 17),
            "dossiers": (first_candidate, second_candidate),
            "strategy_statuses": (second_strategy, first_strategy),
            "risk_statuses": (second_risk, first_risk),
            "limitations": ("Advisory metadata only.",),
        }
    ]


def test_assembly_does_not_mutate_inputs_and_is_deterministic() -> None:
    candidates = [dossier(candidate_id="candidate-001")]
    strategies = [strategy_status(candidate_id="candidate-001")]
    risks = [risk_status(candidate_id="candidate-001")]
    before = (
        candidates[0].to_dict(),
        strategies[0].to_dict(),
        risks[0].to_dict(),
    )

    first = assemble(
        dossiers=candidates,
        strategy_statuses=strategies,
        risk_statuses=risks,
    )
    second = assemble(
        dossiers=(dossier(candidate_id="candidate-001"),),
        strategy_statuses=(strategy_status(candidate_id="candidate-001"),),
        risk_statuses=(risk_status(candidate_id="candidate-001"),),
    )
    candidates.append(dossier(candidate_id="candidate-late"))
    strategies.append(strategy_status(candidate_id="candidate-late"))
    risks.append(risk_status(candidate_id="candidate-late"))

    assert first == second
    assert len(first.dossiers) == 1
    assert len(first.strategy_statuses) == 1
    assert len(first.risk_statuses) == 1
    assert (
        first.dossiers[0].to_dict(),
        first.strategy_statuses[0].to_dict(),
        first.risk_statuses[0].to_dict(),
    ) == before


@pytest.mark.parametrize(
    "bad_as_of_date",
    ("2026-05-17", datetime(2026, 5, 17), None),
)
def test_assembly_rejects_non_plain_date_as_of_date(bad_as_of_date: object) -> None:
    with pytest.raises(ValidationError, match="as_of_date"):
        assemble(as_of_date=bad_as_of_date)


def test_assembly_rejects_malformed_input_collections() -> None:
    with pytest.raises(ValidationError, match="ResearchCandidateDossier"):
        assemble(dossiers=(object(),))
    with pytest.raises(ValidationError, match="StrategyEligibilityStatus"):
        assemble(strategy_statuses=(object(),))
    with pytest.raises(ValidationError, match="RiskAuthorityStatus"):
        assemble(risk_statuses=(object(),))
    with pytest.raises(ValidationError, match="dossiers"):
        assemble(dossiers=())


def test_assembly_rejects_duplicate_candidate_ids() -> None:
    candidate = dossier(candidate_id="candidate-duplicate")

    with pytest.raises(ValidationError, match="dossiers.*duplicate"):
        assemble(dossiers=(candidate, candidate))
    with pytest.raises(ValidationError, match="strategy_statuses.*duplicate"):
        assemble(
            dossiers=(dossier(candidate_id="candidate-duplicate"),),
            strategy_statuses=(
                strategy_status(candidate_id="candidate-duplicate"),
                strategy_status(candidate_id="candidate-duplicate"),
            ),
        )
    with pytest.raises(ValidationError, match="risk_statuses.*duplicate"):
        assemble(
            dossiers=(dossier(candidate_id="candidate-duplicate"),),
            risk_statuses=(
                risk_status(candidate_id="candidate-duplicate"),
                risk_status(candidate_id="candidate-duplicate"),
            ),
        )


def test_assembly_rejects_orphan_status_candidate_ids() -> None:
    with pytest.raises(ValidationError, match="strategy status candidate"):
        assemble(strategy_statuses=(strategy_status(candidate_id="orphan"),))
    with pytest.raises(ValidationError, match="risk status candidate"):
        assemble(risk_statuses=(risk_status(candidate_id="orphan"),))


@pytest.mark.parametrize(
    "label,strategy_builder,risk_builder",
    (
        (
            AdvisoryLabel.PAPER_ELIGIBLE,
            paper_strategy_status,
            paper_risk_status,
        ),
        (
            AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
            live_probe_strategy_status,
            live_probe_risk_status,
        ),
        (
            AdvisoryLabel.LIVE_AUTHORIZED,
            live_strategy_status,
            live_risk_status,
        ),
    ),
)
def test_assembly_accepts_elevated_labels_with_matching_status_support(
    label: AdvisoryLabel,
    strategy_builder,
    risk_builder,
) -> None:
    candidate = dossier(advisory_label=label)

    item = assemble(
        dossiers=(candidate,),
        strategy_statuses=(strategy_builder(),),
        risk_statuses=(risk_builder(),),
    )

    assert item.dossiers[0] is candidate
    assert item.dossiers[0].advisory_label is label


def test_assembly_requires_elevated_labels_to_have_matching_status_objects() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)

    with pytest.raises(ValidationError, match="matching strategy status"):
        assemble(dossiers=(candidate,))
    with pytest.raises(ValidationError, match="matching risk status"):
        assemble(dossiers=(candidate,), strategy_statuses=(paper_strategy_status(),))


def test_assembly_relies_on_operating_brief_for_final_actionable_validation() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.LIVE_AUTHORIZED)

    with pytest.raises(ValidationError, match="live_authorized"):
        assemble(
            dossiers=(candidate,),
            strategy_statuses=(live_strategy_status(),),
            risk_statuses=(live_probe_risk_status(),),
        )


def test_assembly_allows_non_actionable_labels_without_statuses() -> None:
    research = dossier(candidate_id="candidate-research")
    watchlist = dossier(
        candidate_id="candidate-watchlist",
        advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
    )

    item = assemble(dossiers=(research, watchlist))

    assert item.dossiers == (research, watchlist)
    assert item.strategy_statuses == ()
    assert item.risk_statuses == ()


def test_assembly_preserves_non_actionable_labels_when_statuses_are_permissive() -> None:
    research = dossier(candidate_id="candidate-research")
    watchlist = dossier(
        candidate_id="candidate-watchlist",
        advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
    )

    item = assemble(
        dossiers=(research, watchlist),
        strategy_statuses=(
            live_strategy_status(candidate_id="candidate-research"),
            live_strategy_status(candidate_id="candidate-watchlist"),
        ),
        risk_statuses=(
            live_risk_status(candidate_id="candidate-research"),
            live_risk_status(candidate_id="candidate-watchlist"),
        ),
    )
    summary = build_operating_brief_board_summary(item)

    assert item.dossiers[0].advisory_label is AdvisoryLabel.RESEARCH_ONLY
    assert item.dossiers[1].advisory_label is AdvisoryLabel.WATCHLIST_ONLY
    assert summary.research_queue_candidate_ids == ("candidate-research",)
    assert summary.watchlist_candidate_ids == ("candidate-watchlist",)
    assert summary.live_authorized_candidate_ids == ()
    assert summary.candidate_ids_by_label == (
        (AdvisoryLabel.RESEARCH_ONLY, ("candidate-research",)),
        (AdvisoryLabel.WATCHLIST_ONLY, ("candidate-watchlist",)),
        (AdvisoryLabel.PAPER_ELIGIBLE, ()),
        (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, ()),
        (AdvisoryLabel.LIVE_AUTHORIZED, ()),
    )


def test_assembly_rejects_mismatched_source_as_of_date_when_exposed() -> None:
    assembly_date = date(2026, 5, 17)
    other_date = date(2026, 5, 18)

    with pytest.raises(ValidationError, match="dossiers as_of_date"):
        assemble(as_of_date=assembly_date, dossiers=(dated_dossier(other_date),))
    with pytest.raises(ValidationError, match="strategy_statuses as_of_date"):
        assemble(
            as_of_date=assembly_date,
            dossiers=(dated_dossier(assembly_date),),
            strategy_statuses=(dated_strategy_status(other_date),),
        )
    with pytest.raises(ValidationError, match="risk_statuses as_of_date"):
        assemble(
            as_of_date=assembly_date,
            dossiers=(dated_dossier(assembly_date),),
            risk_statuses=(dated_risk_status(other_date),),
        )

    item = assemble(
        as_of_date=assembly_date,
        dossiers=(dated_dossier(assembly_date),),
        strategy_statuses=(dated_strategy_status(assembly_date),),
        risk_statuses=(dated_risk_status(assembly_date),),
    )
    assert item.as_of_date == assembly_date


def test_current_advisory_part_contracts_do_not_add_as_of_date_fields() -> None:
    assert not hasattr(dossier(), "as_of_date")
    assert not hasattr(strategy_status(), "as_of_date")
    assert not hasattr(risk_status(), "as_of_date")


def test_assembled_brief_serialization_rendering_and_summary_are_stable() -> None:
    item = assemble(
        dossiers=(
            dossier(
                candidate_id="candidate-watchlist",
                advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
            ),
            dossier(
                candidate_id="candidate-paper",
                advisory_label=AdvisoryLabel.PAPER_ELIGIBLE,
            ),
        ),
        strategy_statuses=(
            live_strategy_status(candidate_id="candidate-watchlist"),
            paper_strategy_status(candidate_id="candidate-paper"),
        ),
        risk_statuses=(
            live_risk_status(candidate_id="candidate-watchlist"),
            paper_risk_status(candidate_id="candidate-paper"),
        ),
    )

    first_payload = item.to_dict()
    second_payload = item.to_dict()
    first_rendered = render_operating_brief_markdown(item)
    second_rendered = render_operating_brief_markdown(item)
    summary = build_operating_brief_board_summary(item)
    first_summary_payload = summary.to_dict()
    second_summary_payload = summary.to_dict()
    first_summary_rendered = render_operating_brief_board_summary_markdown(summary)
    second_summary_rendered = render_operating_brief_board_summary_markdown(summary)

    assert first_payload == second_payload
    assert first_payload["as_of_date"] == "2026-05-17"
    assert first_payload["dossiers"][0]["candidate_id"] == "candidate-watchlist"
    assert first_payload["dossiers"][1]["candidate_id"] == "candidate-paper"
    assert first_payload["strategy_statuses"][0]["candidate_id"] == (
        "candidate-watchlist"
    )
    assert first_payload["risk_statuses"][0]["candidate_id"] == "candidate-watchlist"
    assert first_rendered == second_rendered
    assert first_summary_payload == second_summary_payload
    assert first_summary_rendered == second_summary_rendered
    assert summary.watchlist_candidate_ids == ("candidate-watchlist",)
    assert summary.paper_eligible_candidate_ids == ("candidate-paper",)
    assert summary.live_authorized_candidate_ids == ()
    _assert_primitive_json_compatible(first_payload)
    _assert_primitive_json_compatible(first_summary_payload)


def test_assembled_output_contains_no_forbidden_behavior_fields_or_language() -> None:
    payload = assemble().to_dict()
    keys = _all_serialized_keys(payload)
    serialized_text = str(payload).lower()

    assert keys.isdisjoint(_FORBIDDEN_SERIALIZED_FIELD_NAMES)
    for forbidden_term in _FORBIDDEN_PAYLOAD_TERMS:
        assert forbidden_term not in serialized_text
    for behavior_name in (
        "create_order",
        "discover_candidate",
        "generate_candidate",
        "rank_candidate",
        "score_strategy",
        "submit_order",
        "update_portfolio",
    ):
        assert not hasattr(assemble(), behavior_name)


def test_no_alternate_public_assembly_entry_points_are_added() -> None:
    assert assembly.__all__ == ["assemble_operating_brief_from_parts"]


def test_assembly_module_imports_only_allowed_advisory_parts() -> None:
    imports = _import_references()
    violations = [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert imports <= _ALLOWED_IMPORTS
    assert violations == []


def test_assembly_module_references_no_snapshots_adapters_or_runtime_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_assembly_module_makes_no_io_network_clock_or_runtime_calls() -> None:
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
