import ast
from datetime import date
from pathlib import Path

import pytest

from algotrader.advisory import (
    AdvisoryLabel,
    OperatingBriefBoardSummary,
    render_operating_brief_board_summary_markdown,
)
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/advisory/operating_brief_summary_markdown.py")

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
    "account_id",
    "allocation",
    "alpaca",
    "broker_order",
    "execution_request",
    "fill_id",
    "market_data",
    "order_id",
    "portfolio_update",
    "position_size",
    "submit_order",
    "target_weight",
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
    "target_weight",
    "position_size",
    "allocation",
)


def board_summary() -> OperatingBriefBoardSummary:
    return OperatingBriefBoardSummary(
        as_of_date=date(2026, 5, 17),
        candidate_ids_by_label=(
            (
                AdvisoryLabel.RESEARCH_ONLY,
                ("candidate-research-a", "candidate-research-b"),
            ),
            (AdvisoryLabel.WATCHLIST_ONLY, ("candidate-watchlist",)),
            (AdvisoryLabel.PAPER_ELIGIBLE, ("candidate-paper",)),
            (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, ("candidate-probe",)),
            (AdvisoryLabel.LIVE_AUTHORIZED, ("candidate-live",)),
        ),
        candidate_counts_by_label=(
            (AdvisoryLabel.RESEARCH_ONLY, 2),
            (AdvisoryLabel.WATCHLIST_ONLY, 1),
            (AdvisoryLabel.PAPER_ELIGIBLE, 1),
            (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, 1),
            (AdvisoryLabel.LIVE_AUTHORIZED, 1),
        ),
        research_queue_candidate_ids=("candidate-research-a", "candidate-research-b"),
        watchlist_candidate_ids=("candidate-watchlist",),
        paper_eligible_candidate_ids=("candidate-paper",),
        live_probe_eligible_candidate_ids=("candidate-probe",),
        live_authorized_candidate_ids=("candidate-live",),
        live_authorization_statuses=(
            (
                "candidate-research-a",
                AdvisoryLabel.RESEARCH_ONLY,
                True,
                False,
                True,
                False,
                False,
            ),
            (
                "candidate-watchlist",
                AdvisoryLabel.WATCHLIST_ONLY,
                True,
                False,
                True,
                False,
                False,
            ),
            (
                "candidate-paper",
                AdvisoryLabel.PAPER_ELIGIBLE,
                True,
                False,
                True,
                False,
                False,
            ),
            (
                "candidate-probe",
                AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
                True,
                False,
                True,
                False,
                False,
            ),
            (
                "candidate-live",
                AdvisoryLabel.LIVE_AUTHORIZED,
                True,
                True,
                True,
                True,
                True,
            ),
        ),
        strategy_blockers=(
            ("candidate-research-a", None, ("No approved strategy mandate.",)),
            (
                "candidate-paper",
                "mandate-paper-001",
                ("Live probe mandate is not approved.",),
            ),
            (
                "candidate-probe",
                "mandate-probe-001",
                ("Live strategy authorization is not approved.",),
            ),
        ),
        risk_blockers=(
            ("candidate-research-a", None, ("No risk authority is approved.",)),
            (
                "candidate-paper",
                "risk-paper-001",
                ("Live probe authority is not approved.",),
            ),
            (
                "candidate-probe",
                "risk-probe-001",
                ("Live authority is not approved.",),
            ),
        ),
        uncertainty_summaries=(
            (
                "candidate-research-a",
                ("Input provenance is not yet reviewed.",),
            ),
            (
                "candidate-paper",
                ("Paper evidence package requires deterministic review.",),
            ),
        ),
        failure_mode_summaries=(
            (
                "candidate-research-a",
                ("Regime shift could invalidate assumptions.",),
            ),
            (
                "candidate-probe",
                ("Probe controls may reveal operational gaps.",),
            ),
        ),
        brief_limitations=("Brief-level limitation is retained.",),
        candidate_limitations=(
            ("candidate-research-a", ("Candidate limitation retained.",)),
        ),
        strategy_limitations=(
            (
                "candidate-paper",
                "mandate-paper-001",
                ("Strategy limitation retained.",),
            ),
        ),
        risk_limitations=(
            ("candidate-paper", "risk-paper-001", ("Risk limitation retained.",)),
        ),
        non_claims=(
            "This summary is advisory metadata only.",
            "It reports existing labels, blockers, uncertainty, and limitations only.",
        ),
    )


def test_renderer_accepts_only_operating_brief_board_summary() -> None:
    with pytest.raises(ValidationError, match="OperatingBriefBoardSummary"):
        render_operating_brief_board_summary_markdown({"summary": "not-a-summary"})


def test_renderer_returns_markdown_string_with_final_newline() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert isinstance(rendered, str)
    assert rendered.endswith("\n")
    assert rendered.startswith("# Advisory Operating Board Summary\n")


def test_renderer_includes_advisory_disclaimer_and_as_of_date() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert "As-of date: 2026-05-17" in rendered
    assert "This board is advisory metadata only." in rendered
    assert "not a trading recommendation" in rendered
    assert "not a signal" in rendered
    assert "not an order request" in rendered
    assert "not live-trading authority" in rendered


def test_renderer_includes_counts_for_every_advisory_label() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert "## Candidate Counts" in rendered
    for label, count in (
        (AdvisoryLabel.RESEARCH_ONLY, 2),
        (AdvisoryLabel.WATCHLIST_ONLY, 1),
        (AdvisoryLabel.PAPER_ELIGIBLE, 1),
        (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, 1),
        (AdvisoryLabel.LIVE_AUTHORIZED, 1),
    ):
        assert f"- {label.value}: {count}" in rendered


def test_renderer_includes_grouped_candidate_ids_by_exact_labels() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert "### Research Only (research_only)" in rendered
    assert "### Watchlist Only (watchlist_only)" in rendered
    assert "### Paper Eligible (paper_eligible)" in rendered
    assert "### Live Probe Eligible (live_probe_eligible)" in rendered
    assert "### Live Authorized (live_authorized)" in rendered
    assert "- candidate-research-a" in rendered
    assert "- candidate-research-b" in rendered
    assert "- candidate-watchlist" in rendered
    assert "- candidate-paper" in rendered
    assert "- candidate-probe" in rendered
    assert "- candidate-live" in rendered


def test_renderer_includes_board_ids_for_paper_probe_and_live_metadata() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert "## Paper-Eligible Board IDs" in rendered
    assert "- candidate-paper" in rendered
    assert "## Live-Probe-Eligible Board IDs" in rendered
    assert "- candidate-probe" in rendered
    assert "## Live-Authorized Metadata" in rendered
    assert "metadata only and do not create trading authority" in rendered
    assert "- candidate-live" in rendered
    assert "candidate-live: advisory_label=live_authorized" in rendered
    assert "strategy_live_authorized=true" in rendered
    assert "risk_live_authorized=true" in rendered
    assert "label_live_authorized=true" in rendered


def test_renderer_includes_strategy_and_risk_blockers() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert "## Strategy Blockers" in rendered
    assert (
        "- candidate-research-a: mandate_id=not set; "
        "No approved strategy mandate."
    ) in rendered
    assert (
        "- candidate-paper: mandate_id=mandate-paper-001; "
        "Live probe mandate is not approved."
    ) in rendered
    assert "## Risk Blockers" in rendered
    assert (
        "- candidate-research-a: authority_id=not set; "
        "No risk authority is approved."
    ) in rendered
    assert (
        "- candidate-paper: authority_id=risk-paper-001; "
        "Live probe authority is not approved."
    ) in rendered


def test_renderer_includes_uncertainty_failure_modes_limitations_and_non_claims() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert "## Uncertainty" in rendered
    assert (
        "- candidate-research-a: Input provenance is not yet reviewed."
    ) in rendered
    assert "## Failure Modes" in rendered
    assert (
        "- candidate-research-a: Regime shift could invalidate assumptions."
    ) in rendered
    assert "## Limitations" in rendered
    assert "- Brief-level limitation is retained." in rendered
    assert "- candidate-research-a: Candidate limitation retained." in rendered
    assert (
        "- candidate-paper: mandate_id=mandate-paper-001; "
        "Strategy limitation retained."
    ) in rendered
    assert (
        "- candidate-paper: authority_id=risk-paper-001; Risk limitation retained."
    ) in rendered
    assert "## Non-Claims" in rendered
    assert "- The board does not validate profitability." in rendered
    assert "- The board does not rank or score candidates." in rendered
    assert "- The board does not create trading recommendations." in rendered
    assert "- `paper_eligible` does not imply live readiness." in rendered
    assert "- `live_probe_eligible` is operational eligibility only." in rendered
    assert (
        "- `live_authorized` remains constructor-gated by strategy eligibility "
        "and risk authority."
    ) in rendered
    assert (
        "- The board does not create broker, portfolio, order, fill, execution, "
        "or runtime behavior."
    ) in rendered
    assert "### Source Summary Non-Claims" in rendered
    assert "- This summary is advisory metadata only." in rendered


def test_renderer_preserves_summary_ordering() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert rendered.index("- candidate-research-a") < rendered.index(
        "- candidate-research-b"
    )
    assert rendered.index("### Research Only (research_only)") < rendered.index(
        "### Watchlist Only (watchlist_only)"
    )
    assert rendered.index("No approved strategy mandate.") < rendered.index(
        "Live probe mandate is not approved."
    )
    assert rendered.index("Input provenance is not yet reviewed.") < rendered.index(
        "Paper evidence package requires deterministic review."
    )
    assert rendered.index("Regime shift could invalidate assumptions.") < rendered.index(
        "Probe controls may reveal operational gaps."
    )


def test_renderer_is_deterministic_across_repeated_calls() -> None:
    summary = board_summary()

    assert render_operating_brief_board_summary_markdown(
        summary
    ) == render_operating_brief_board_summary_markdown(summary)


def test_renderer_does_not_mutate_source_summary() -> None:
    summary = board_summary()
    before = summary.to_dict()

    render_operating_brief_board_summary_markdown(summary)

    assert summary.to_dict() == before
    assert summary.research_queue_candidate_ids == (
        "candidate-research-a",
        "candidate-research-b",
    )


def test_renderer_output_contains_no_python_reprs_or_memory_addresses() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    assert " at 0x" not in rendered
    assert "OperatingBriefBoardSummary(" not in rendered
    assert "AdvisoryLabel." not in rendered
    assert "{" not in rendered
    assert "}" not in rendered


def test_renderer_output_contains_no_forbidden_behavior_field_terms() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary())

    for term in _FORBIDDEN_OUTPUT_TERMS:
        assert term not in rendered


def test_renderer_does_not_add_positive_selection_or_discovery_language() -> None:
    rendered = render_operating_brief_board_summary_markdown(board_summary()).lower()

    for phrase in (
        "ranked candidate",
        "ranking:",
        "score:",
        "scored candidate",
        "recommendation:",
        "recommended candidate",
        "candidate discovery",
        "discovered candidate",
        "top candidate",
        "best candidate",
    ):
        assert phrase not in rendered
    assert "does not rank or score candidates" in rendered
    assert "does not create trading recommendations" in rendered


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
