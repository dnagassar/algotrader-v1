import ast
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.advisory import (
    AdvisoryLabel,
    CandidateDossierSnapshot,
    OperatingBrief,
    OperatingBriefBoardSummary,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    assemble_operating_brief_from_parts,
    build_operating_brief_board_summary,
    candidate_snapshot_to_research_candidate_dossier,
    render_operating_brief_board_summary_markdown,
    render_operating_brief_markdown,
    risk_authority_snapshot_to_risk_authority_status,
    strategy_mandate_snapshot_to_strategy_eligibility_status,
)
from algotrader.errors import ValidationError
from algotrader.governance import RiskAuthoritySnapshot, StrategyMandateSnapshot
from tests.fixtures.advisory_pipeline import (
    build_synthetic_advisory_board_summary_from_pipeline,
    build_synthetic_advisory_dossiers_from_snapshots,
    build_synthetic_advisory_operating_brief_from_pipeline,
    build_synthetic_candidate_snapshots,
    build_synthetic_risk_authority_snapshots,
    build_synthetic_risk_statuses_from_snapshots,
    build_synthetic_strategy_mandate_snapshots,
    build_synthetic_strategy_statuses_from_snapshots,
    expected_synthetic_pipeline_board_summary_markdown,
    expected_synthetic_pipeline_operating_brief_markdown,
)


MODULE_PATH = Path("tests/fixtures/advisory_pipeline.py")
FIXED_AS_OF_DATE = date(2026, 1, 16)

EXPECTED_CANDIDATE_IDS = (
    "synthetic_pipeline_research_only",
    "synthetic_pipeline_watchlist_only",
    "synthetic_pipeline_paper_eligible",
    "synthetic_pipeline_live_probe_eligible",
    "synthetic_pipeline_live_authorized",
)
EXPECTED_STATUS_CANDIDATE_IDS = (
    "synthetic_pipeline_watchlist_only",
    "synthetic_pipeline_paper_eligible",
    "synthetic_pipeline_live_probe_eligible",
    "synthetic_pipeline_live_authorized",
)
EXPECTED_IDS_BY_LABEL = {
    AdvisoryLabel.RESEARCH_ONLY: ("synthetic_pipeline_research_only",),
    AdvisoryLabel.WATCHLIST_ONLY: ("synthetic_pipeline_watchlist_only",),
    AdvisoryLabel.PAPER_ELIGIBLE: ("synthetic_pipeline_paper_eligible",),
    AdvisoryLabel.LIVE_PROBE_ELIGIBLE: (
        "synthetic_pipeline_live_probe_eligible",
    ),
    AdvisoryLabel.LIVE_AUTHORIZED: ("synthetic_pipeline_live_authorized",),
}

FORBIDDEN_SERIALIZED_FIELD_NAMES = {
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
    "execution_request",
    "fill",
    "fill_id",
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

FORBIDDEN_PAYLOAD_TERMS = (
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker_order",
    "candidate discovery",
    "candidate_discovery",
    "credential",
    "execution_request",
    "fill_id",
    "http://",
    "https://",
    "market data",
    "market-data",
    "order_id",
    "password",
    "position_size",
    "price",
    "quantconnect",
    "ranking",
    "recommendation",
    "score",
    "scoring",
    "secret",
    "submit_order",
    "symbol",
    "target_weight",
    "ticker",
    "token",
    "vendor",
    "volume",
)

FORBIDDEN_IMPORT_PREFIXES = (
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
    "algotrader.research",
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

ALLOWED_IMPORTS = {
    "__future__",
    "datetime",
    "algotrader.advisory",
    "algotrader.governance",
}

FORBIDDEN_REFERENCE_NAMES = {
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
    "client_order_id",
    "credential",
    "credentials",
    "discover",
    "discover_candidate",
    "discover_candidates",
    "execution",
    "execution_request",
    "fill",
    "fill_id",
    "market_data",
    "network",
    "open",
    "order",
    "order_id",
    "os",
    "Path",
    "portfolio",
    "portfolio_update",
    "position",
    "position_size",
    "random",
    "rank",
    "ranking",
    "recommend",
    "recommendation",
    "recommendations",
    "runtime",
    "scheduler",
    "score",
    "scoring",
    "socket",
    "submit_order",
    "target_weight",
}

FORBIDDEN_CALL_NAMES = {
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
    "Path",
    "post",
    "random",
    "random.random",
    "read",
    "render_operating_brief_board_summary_markdown",
    "render_operating_brief_markdown",
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


def test_snapshot_fixture_builders_return_expected_snapshot_types_and_dates() -> None:
    first_candidates = build_synthetic_candidate_snapshots()
    second_candidates = build_synthetic_candidate_snapshots()
    first_strategies = build_synthetic_strategy_mandate_snapshots()
    second_strategies = build_synthetic_strategy_mandate_snapshots()
    first_risks = build_synthetic_risk_authority_snapshots()
    second_risks = build_synthetic_risk_authority_snapshots()

    assert all(isinstance(item, CandidateDossierSnapshot) for item in first_candidates)
    assert all(isinstance(item, StrategyMandateSnapshot) for item in first_strategies)
    assert all(isinstance(item, RiskAuthoritySnapshot) for item in first_risks)
    assert tuple(item.candidate_id for item in first_candidates) == EXPECTED_CANDIDATE_IDS
    assert tuple(item.proposed_label for item in first_candidates) == tuple(AdvisoryLabel)
    assert tuple(item.as_of_date for item in first_candidates) == (FIXED_AS_OF_DATE,) * 5
    assert tuple(item.as_of_date for item in first_strategies) == (FIXED_AS_OF_DATE,) * 4
    assert tuple(item.as_of_date for item in first_risks) == (FIXED_AS_OF_DATE,) * 4
    assert first_candidates == second_candidates
    assert first_strategies == second_strategies
    assert first_risks == second_risks
    assert first_candidates is not second_candidates
    assert first_strategies is not second_strategies
    assert first_risks is not second_risks
    assert first_candidates[0] is not second_candidates[0]
    assert first_strategies[0] is not second_strategies[0]
    assert first_risks[0] is not second_risks[0]


def test_snapshot_fixture_includes_required_synthetic_metadata_without_over_support() -> None:
    candidates = build_synthetic_candidate_snapshots()
    strategies = build_synthetic_strategy_mandate_snapshots()
    risks = build_synthetic_risk_authority_snapshots()

    assert len(strategies) == 4
    assert len(risks) == 4
    assert "synthetic_pipeline_research_only" not in EXPECTED_STATUS_CANDIDATE_IDS
    assert candidates[0].strategy_id == ""
    assert candidates[0].mandate_id == ""
    assert candidates[0].proposed_label is AdvisoryLabel.RESEARCH_ONLY
    assert candidates[1].proposed_label is AdvisoryLabel.WATCHLIST_ONLY
    assert strategies[0].live_authorized is True
    assert risks[0].live_allowed is True

    for candidate in candidates:
        assert candidate.source_type == "synthetic"
        assert candidate.label_source == "synthetic_fixture"
        assert candidate.uncertainty_factors
        assert candidate.failure_modes
        assert candidate.next_questions
        assert candidate.limitations
        assert candidate.non_claims
    for snapshot in strategies:
        assert snapshot.promotion_requirements
        assert snapshot.revocation_triggers
        assert snapshot.limitations
        assert snapshot.uncertainty_factors
        assert snapshot.failure_modes
        assert snapshot.non_claims
    for snapshot in risks:
        assert snapshot.promotion_requirements
        assert snapshot.revocation_triggers
        assert snapshot.limitations
        assert snapshot.uncertainty_factors
        assert snapshot.failure_modes
        assert snapshot.non_claims
    assert any(snapshot.blocking_reasons for snapshot in strategies)
    assert any(snapshot.blocking_reasons for snapshot in risks)


def test_adapters_convert_snapshots_to_prepared_parts_without_mutation() -> None:
    candidate_sources = build_synthetic_candidate_snapshots()
    strategy_sources = build_synthetic_strategy_mandate_snapshots()
    risk_sources = build_synthetic_risk_authority_snapshots()
    before = (
        tuple(source.to_dict() for source in candidate_sources),
        tuple(source.to_dict() for source in strategy_sources),
        tuple(source.to_dict() for source in risk_sources),
    )

    dossiers = tuple(
        candidate_snapshot_to_research_candidate_dossier(source)
        for source in candidate_sources
    )
    strategy_statuses = tuple(
        strategy_mandate_snapshot_to_strategy_eligibility_status(
            source,
            candidate_id=candidate_id,
        )
        for source, candidate_id in zip(
            strategy_sources,
            EXPECTED_STATUS_CANDIDATE_IDS,
            strict=True,
        )
    )
    risk_statuses = tuple(
        risk_authority_snapshot_to_risk_authority_status(
            source,
            candidate_id=candidate_id,
        )
        for source, candidate_id in zip(
            risk_sources,
            EXPECTED_STATUS_CANDIDATE_IDS,
            strict=True,
        )
    )

    assert all(isinstance(item, ResearchCandidateDossier) for item in dossiers)
    assert all(isinstance(item, StrategyEligibilityStatus) for item in strategy_statuses)
    assert all(isinstance(item, RiskAuthorityStatus) for item in risk_statuses)
    assert dossiers == build_synthetic_advisory_dossiers_from_snapshots()
    assert strategy_statuses == build_synthetic_strategy_statuses_from_snapshots()
    assert risk_statuses == build_synthetic_risk_statuses_from_snapshots()
    assert tuple(item.candidate_id for item in dossiers) == EXPECTED_CANDIDATE_IDS
    assert tuple(item.candidate_id for item in strategy_statuses) == (
        EXPECTED_STATUS_CANDIDATE_IDS
    )
    assert tuple(item.candidate_id for item in risk_statuses) == (
        EXPECTED_STATUS_CANDIDATE_IDS
    )
    assert tuple(item.advisory_label for item in dossiers) == tuple(
        source.proposed_label for source in candidate_sources
    )
    assert (
        tuple(source.to_dict() for source in candidate_sources),
        tuple(source.to_dict() for source in strategy_sources),
        tuple(source.to_dict() for source in risk_sources),
    ) == before


def test_strategy_and_risk_adapter_candidate_ids_are_explicit_literals() -> None:
    calls = [
        node
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and _call_name(node.func)
        in {
            "strategy_mandate_snapshot_to_strategy_eligibility_status",
            "risk_authority_snapshot_to_risk_authority_status",
        }
    ]
    explicit_candidate_ids = tuple(
        keyword.value.value
        for call in calls
        for keyword in call.keywords
        if keyword.arg == "candidate_id"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    )

    assert explicit_candidate_ids == EXPECTED_STATUS_CANDIDATE_IDS * 2
    assert "candidate_id" not in StrategyMandateSnapshot.__dataclass_fields__
    assert "candidate_id" not in RiskAuthoritySnapshot.__dataclass_fields__


def test_pipeline_assembles_prepared_parts_with_order_and_label_authority() -> None:
    dossiers = build_synthetic_advisory_dossiers_from_snapshots()
    strategy_statuses = build_synthetic_strategy_statuses_from_snapshots()
    risk_statuses = build_synthetic_risk_statuses_from_snapshots()

    manual = assemble_operating_brief_from_parts(
        as_of_date=FIXED_AS_OF_DATE,
        dossiers=dossiers,
        strategy_statuses=strategy_statuses,
        risk_statuses=risk_statuses,
    )
    pipeline = build_synthetic_advisory_operating_brief_from_pipeline()
    summary = build_operating_brief_board_summary(manual)
    strategy_by_id = {status.candidate_id: status for status in manual.strategy_statuses}
    risk_by_id = {status.candidate_id: status for status in manual.risk_statuses}

    assert isinstance(manual, OperatingBrief)
    assert is_dataclass(manual)
    assert "__slots__" in OperatingBrief.__dict__
    assert not hasattr(manual, "__dict__")
    with pytest.raises(FrozenInstanceError):
        manual.brief_id = "changed"
    assert manual == pipeline
    assert build_synthetic_advisory_operating_brief_from_pipeline() == pipeline
    assert manual.dossiers == dossiers
    assert manual.strategy_statuses == strategy_statuses
    assert manual.risk_statuses == risk_statuses
    assert manual.dossiers[0] is dossiers[0]
    assert manual.strategy_statuses[0] is strategy_statuses[0]
    assert manual.risk_statuses[0] is risk_statuses[0]
    assert tuple(item.candidate_id for item in manual.dossiers) == EXPECTED_CANDIDATE_IDS
    assert tuple(item.candidate_id for item in manual.strategy_statuses) == (
        EXPECTED_STATUS_CANDIDATE_IDS
    )
    assert tuple(item.candidate_id for item in manual.risk_statuses) == (
        EXPECTED_STATUS_CANDIDATE_IDS
    )
    assert strategy_by_id["synthetic_pipeline_watchlist_only"].live_authorized is True
    assert risk_by_id["synthetic_pipeline_watchlist_only"].live_authorized is True
    assert summary.watchlist_candidate_ids == ("synthetic_pipeline_watchlist_only",)
    assert summary.live_authorized_candidate_ids == (
        "synthetic_pipeline_live_authorized",
    )


def test_pipeline_elevated_labels_require_matching_prepared_statuses() -> None:
    dossiers = build_synthetic_advisory_dossiers_from_snapshots()
    strategy_statuses = build_synthetic_strategy_statuses_from_snapshots()
    risk_statuses = build_synthetic_risk_statuses_from_snapshots()

    with pytest.raises(ValidationError, match="matching strategy status"):
        assemble_operating_brief_from_parts(
            as_of_date=FIXED_AS_OF_DATE,
            dossiers=dossiers,
            strategy_statuses=(strategy_statuses[0], *strategy_statuses[2:]),
            risk_statuses=risk_statuses,
        )
    with pytest.raises(ValidationError, match="matching risk status"):
        assemble_operating_brief_from_parts(
            as_of_date=FIXED_AS_OF_DATE,
            dossiers=dossiers,
            strategy_statuses=strategy_statuses,
            risk_statuses=(risk_statuses[0], *risk_statuses[2:]),
        )


def test_board_summary_and_markdown_rendering_match_literal_expected_strings() -> None:
    brief = build_synthetic_advisory_operating_brief_from_pipeline()
    summary = build_synthetic_advisory_board_summary_from_pipeline()
    manual_summary = build_operating_brief_board_summary(brief)
    expected_brief_markdown = expected_synthetic_pipeline_operating_brief_markdown()
    expected_summary_markdown = expected_synthetic_pipeline_board_summary_markdown()
    first_brief_render = render_operating_brief_markdown(brief)
    second_brief_render = render_operating_brief_markdown(brief)
    first_summary_render = render_operating_brief_board_summary_markdown(summary)
    second_summary_render = render_operating_brief_board_summary_markdown(summary)

    assert isinstance(summary, OperatingBriefBoardSummary)
    assert is_dataclass(summary)
    assert "__slots__" in OperatingBriefBoardSummary.__dict__
    assert not hasattr(summary, "__dict__")
    with pytest.raises(FrozenInstanceError):
        summary.research_queue_candidate_ids = ()
    assert summary == manual_summary
    assert build_synthetic_advisory_board_summary_from_pipeline() == summary
    assert dict(summary.candidate_ids_by_label) == EXPECTED_IDS_BY_LABEL
    assert summary.candidate_counts_by_label == tuple(
        (label, 1) for label in AdvisoryLabel
    )
    assert expected_brief_markdown.endswith("\n")
    assert expected_summary_markdown.endswith("\n")
    assert first_brief_render == expected_brief_markdown
    assert second_brief_render == expected_brief_markdown
    assert first_summary_render == expected_summary_markdown
    assert second_summary_render == expected_summary_markdown
    assert (
        "synthetic_pipeline_research_only"
        in expected_synthetic_pipeline_operating_brief_markdown()
    )


def test_pipeline_serialization_is_deterministic_and_primitive() -> None:
    brief = build_synthetic_advisory_operating_brief_from_pipeline()
    summary = build_synthetic_advisory_board_summary_from_pipeline()
    first_brief_payload = brief.to_dict()
    second_brief_payload = brief.to_dict()
    first_summary_payload = summary.to_dict()
    second_summary_payload = summary.to_dict()

    assert first_brief_payload == second_brief_payload
    assert first_summary_payload == second_summary_payload
    assert first_brief_payload["as_of_date"] == "2026-01-16"
    assert first_summary_payload["as_of_date"] == "2026-01-16"
    _assert_primitive_json_compatible(first_brief_payload)
    _assert_primitive_json_compatible(first_summary_payload)
    for payload in (first_brief_payload, first_summary_payload):
        serialized_repr = repr(payload)
        assert " at 0x" not in serialized_repr
        assert "AdvisoryLabel." not in serialized_repr
        assert "OperatingBrief(" not in serialized_repr
        assert "OperatingBriefBoardSummary(" not in serialized_repr


def test_pipeline_fixture_content_contains_no_disallowed_runtime_or_selection_data() -> None:
    payloads = _fixture_payloads()

    for payload in payloads:
        assert _all_serialized_keys(payload).isdisjoint(FORBIDDEN_SERIALIZED_FIELD_NAMES)
        content = repr(payload).lower()
        for forbidden_term in FORBIDDEN_PAYLOAD_TERMS:
            assert forbidden_term not in content
        assert "$" not in content
        assert "://" not in content
    assert "buy" not in _payload_words(payloads)
    assert "sell" not in _payload_words(payloads)
    assert "hold" not in _payload_words(payloads)
    assert "trade" not in _payload_words(payloads)
    assert "trading" not in _payload_words(payloads)


def test_pipeline_fixture_module_has_no_forbidden_imports_calls_or_references() -> None:
    imports = _import_references()
    call_names = _call_names()
    reference_names = _referenced_names()
    source_text = MODULE_PATH.read_text(encoding="utf-8").lower()
    import_violations = [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert imports <= ALLOWED_IMPORTS
    assert import_violations == []
    assert call_names.isdisjoint(FORBIDDEN_CALL_NAMES)
    assert reference_names.isdisjoint(FORBIDDEN_REFERENCE_NAMES)
    assert "render_operating_brief_markdown" not in imports
    assert "render_operating_brief_board_summary_markdown" not in imports
    for forbidden_text in (
        "alpaca",
        "api_key",
        "candidate_discovery",
        "execution_request",
        "http://",
        "https://",
        "os.getenv",
        "pathlib",
        "position_size",
        "submit_order",
        "target_weight",
        "vectorbt",
    ):
        assert forbidden_text not in source_text


def _fixture_payloads() -> tuple[dict[str, object], ...]:
    candidates = build_synthetic_candidate_snapshots()
    strategies = build_synthetic_strategy_mandate_snapshots()
    risks = build_synthetic_risk_authority_snapshots()
    dossiers = build_synthetic_advisory_dossiers_from_snapshots()
    strategy_statuses = build_synthetic_strategy_statuses_from_snapshots()
    risk_statuses = build_synthetic_risk_statuses_from_snapshots()
    brief = build_synthetic_advisory_operating_brief_from_pipeline()
    summary = build_synthetic_advisory_board_summary_from_pipeline()

    return (
        *(candidate.to_dict() for candidate in candidates),
        *(strategy.to_dict() for strategy in strategies),
        *(risk.to_dict() for risk in risks),
        *(dossier.to_dict() for dossier in dossiers),
        *(status.to_dict() for status in strategy_statuses),
        *(status.to_dict() for status in risk_statuses),
        brief.to_dict(),
        summary.to_dict(),
    )


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


def _payload_words(payloads: tuple[dict[str, object], ...]) -> set[str]:
    text = repr(payloads).lower()
    return {
        part.strip(".,;:!?()[]{}'\"`")
        for part in text.replace("_", " ").split()
    }


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
