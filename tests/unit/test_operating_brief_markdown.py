import ast
from datetime import date
from pathlib import Path

import pytest

from algotrader.advisory import (
    AdvisoryLabel,
    OperatingBrief,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    render_operating_brief_markdown,
)
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/advisory/operating_brief_markdown.py")

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
    "account_id",
    "alpaca",
    "broker_order",
    "execution_request",
    "fill_id",
    "market_data",
    "order_id",
    "portfolio_update",
    "position_id",
    "submit_order",
}

_FORBIDDEN_OUTPUT_TERMS = (
    "order_id",
    "fill_id",
    "broker_order",
    "account_id",
    "position_id",
    "portfolio_update",
    "submit_order",
    "execution_request",
)


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
        "strategy_statuses": (strategy_status(),),
        "risk_statuses": (risk_status(),),
        "limitations": ("Advisory metadata only.",),
    }
    values.update(overrides)
    return OperatingBrief(**values)


def test_renderer_accepts_only_operating_brief() -> None:
    with pytest.raises(ValidationError, match="OperatingBrief"):
        render_operating_brief_markdown({"brief_id": "not-a-brief"})


def test_renderer_returns_markdown_string_with_final_newline() -> None:
    rendered = render_operating_brief_markdown(brief())

    assert isinstance(rendered, str)
    assert rendered.endswith("\n")
    assert rendered.startswith("# Advisory Operating Brief\n")


def test_renderer_includes_advisory_disclaimer_and_as_of_date() -> None:
    rendered = render_operating_brief_markdown(brief())

    assert "As-of date: 2026-05-17" in rendered
    assert "This brief is advisory metadata only." in rendered
    assert "not a trading recommendation" in rendered
    assert "not a signal" in rendered
    assert "not an order request" in rendered
    assert "not live-trading authority" in rendered


def test_renderer_includes_candidate_dossier_fields() -> None:
    rendered = render_operating_brief_markdown(
        brief(dossiers=(dossier(advisory_label=AdvisoryLabel.WATCHLIST_ONLY),))
    )

    assert "## Candidate Dossiers" in rendered
    assert "### 1. candidate-001" in rendered
    assert "- Candidate id: candidate-001" in rendered
    assert "- Title: ETF trend research candidate" in rendered
    assert "- Advisory label: watchlist_only" in rendered
    assert "- Thesis/context: Advisory metadata for future review only." in rendered
    assert "- Limitations / non-claims:" in rendered


def test_renderer_includes_uncertainty_and_failure_mode_fields() -> None:
    rendered = render_operating_brief_markdown(brief())

    assert "- Uncertainty:" in rendered
    assert "  - Input provenance is not yet reviewed." in rendered
    assert "- Failure modes:" in rendered
    assert "  - Regime shift could invalidate assumptions." in rendered
    assert "- Next questions / research needs:" in rendered
    assert "  - What deterministic evidence package is required?" in rendered


def test_renderer_includes_strategy_eligibility_fields_and_blocking_reasons() -> None:
    rendered = render_operating_brief_markdown(
        brief(strategy_statuses=(paper_strategy_status(),))
    )

    assert "## Strategy Eligibility" in rendered
    assert "- Candidate id: candidate-001" in rendered
    assert "- Mandate id: mandate-paper-001" in rendered
    assert "- Mandate approved: true" in rendered
    assert "- Evidence approved: true" in rendered
    assert "  - evidence-package-001" in rendered
    assert "  - paper_eligible: true" in rendered
    assert "  - live_probe_eligible: false" in rendered
    assert "  - live_authorized: false" in rendered
    assert "- Blocking reasons:" in rendered
    assert "  - Live probe mandate is not approved." in rendered
    assert "- Limitations:" in rendered


def test_renderer_includes_risk_authority_fields_and_blocking_reasons() -> None:
    rendered = render_operating_brief_markdown(
        brief(risk_statuses=(paper_risk_status(),))
    )

    assert "## Risk Authority" in rendered
    assert "- Authority id: risk-paper-001" in rendered
    assert "  - paper_allowed: true" in rendered
    assert "  - live_probe_allowed: false" in rendered
    assert "  - live_authorized: false" in rendered
    assert "  - Live probe authority is not approved." in rendered
    assert "  - Authority metadata grants no trading action by itself." in rendered


def test_renderer_preserves_dossier_strategy_and_risk_ordering() -> None:
    first_candidate = dossier(candidate_id="candidate-001")
    second_candidate = dossier(
        candidate_id="candidate-002",
        title="Second research candidate",
        advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
    )
    first_strategy = strategy_status(candidate_id="candidate-001")
    second_strategy = strategy_status(
        candidate_id="candidate-002",
        blocking_reasons=("Second strategy block.",),
    )
    first_risk = risk_status(candidate_id="candidate-001")
    second_risk = risk_status(
        candidate_id="candidate-002",
        blocking_reasons=("Second risk block.",),
    )

    rendered = render_operating_brief_markdown(
        brief(
            dossiers=(first_candidate, second_candidate),
            strategy_statuses=(first_strategy, second_strategy),
            risk_statuses=(first_risk, second_risk),
        )
    )

    assert rendered.index("### 1. candidate-001") < rendered.index(
        "### 2. candidate-002"
    )
    assert rendered.index("No approved strategy mandate.") < rendered.index(
        "Second strategy block."
    )
    assert rendered.index("No risk authority is approved.") < rendered.index(
        "Second risk block."
    )


def test_renderer_is_deterministic_across_repeated_calls() -> None:
    item = brief()

    first_rendered = render_operating_brief_markdown(item)
    second_rendered = render_operating_brief_markdown(item)

    assert first_rendered == second_rendered
    assert first_rendered.encode("utf-8") == second_rendered.encode("utf-8")


def test_renderer_does_not_mutate_source_or_nested_objects() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.PAPER_ELIGIBLE)
    strategy = paper_strategy_status()
    authority = paper_risk_status()
    item = brief(
        dossiers=(candidate,),
        strategy_statuses=(strategy,),
        risk_statuses=(authority,),
    )
    before = item.to_dict()

    render_operating_brief_markdown(item)

    assert item.to_dict() == before
    assert candidate.failure_modes == ("Regime shift could invalidate assumptions.",)
    assert strategy.evidence_refs == ("evidence-package-001",)
    assert authority.blocking_reasons == ("Live probe authority is not approved.",)


def test_renderer_output_contains_no_python_reprs_or_memory_addresses() -> None:
    rendered = render_operating_brief_markdown(brief())

    assert " at 0x" not in rendered
    assert "ResearchCandidateDossier(" not in rendered
    assert "StrategyEligibilityStatus(" not in rendered
    assert "RiskAuthorityStatus(" not in rendered
    assert "OperatingBrief(" not in rendered
    assert "AdvisoryLabel." not in rendered


def test_renderer_output_contains_no_forbidden_behavior_field_terms() -> None:
    rendered = render_operating_brief_markdown(brief())

    for term in _FORBIDDEN_OUTPUT_TERMS:
        assert term not in rendered


def test_renderer_includes_non_claims_section() -> None:
    rendered = render_operating_brief_markdown(brief())

    assert "## Non-Claims" in rendered
    assert "- The brief does not validate profitability." in rendered
    assert "- `paper_eligible` does not imply live readiness." in rendered
    assert "- `live_probe_eligible` is operational eligibility only." in rendered
    assert (
        "- `live_authorized` must remain constructor-gated by strategy "
        "eligibility and risk authority."
        in rendered
    )
    assert (
        "- The brief does not create broker, portfolio, order, fill, "
        "execution, or runtime behavior."
        in rendered
    )


def test_renderer_does_not_bypass_live_authorized_constructor_gates() -> None:
    candidate = dossier(advisory_label=AdvisoryLabel.LIVE_AUTHORIZED)

    with pytest.raises(ValidationError, match="live_authorized"):
        brief(
            dossiers=(candidate,),
            strategy_statuses=(live_strategy_status(),),
            risk_statuses=(live_probe_risk_status(),),
        )

    rendered = render_operating_brief_markdown(
        brief(
            dossiers=(candidate,),
            strategy_statuses=(live_strategy_status(),),
            risk_statuses=(live_risk_status(),),
        )
    )

    assert "- Advisory label: live_authorized" in rendered
    assert "  - live_authorized: true" in rendered


def test_markdown_module_imports_no_forbidden_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_markdown_module_references_no_forbidden_trading_runtime_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_markdown_module_makes_no_io_network_broker_llm_or_scheduler_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


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
