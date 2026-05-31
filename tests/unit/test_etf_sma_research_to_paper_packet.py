from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.etf_sma_backtest_summary import (
    EtfSmaBacktestBar,
    EtfSmaBacktestConfig,
    EtfSmaBacktestSummary,
    build_etf_sma_backtest_summary,
)
from algotrader.research.etf_sma_paper_experiment_plan import (
    EtfSmaPaperExperimentPlan,
    EtfSmaPaperExperimentPlanConfig,
    draft_etf_sma_paper_experiment_plan,
)
from algotrader.research.etf_sma_research_candidate import (
    SmaCandidateConfig,
    SmaCandidateInputBar,
    SmaResearchToPaperCandidate,
    build_etf_sma_research_candidate,
)
from algotrader.research.etf_sma_research_to_paper_packet import (
    ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS,
    ETF_SMA_RESEARCH_TO_PAPER_PACKET_LIMITATIONS,
    EtfSmaResearchToPaperPacket,
    build_etf_sma_research_to_paper_packet,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_research_to_paper_packet.py")
_AS_OF = "2026-01-05"
_STRATEGY_NAME = "SPY SMA research-to-paper packet"
_CANDIDATE_CONFIG = SmaCandidateConfig(
    symbol="SPY",
    strategy_name=_STRATEGY_NAME,
    short_window=2,
    long_window=3,
)
_BACKTEST_CONFIG = EtfSmaBacktestConfig(
    symbol="SPY",
    strategy_name=_STRATEGY_NAME,
    short_window=2,
    long_window=3,
)
_PLAN_CONFIG = EtfSmaPaperExperimentPlanConfig(
    proposed_cap_policy="metadata_only_review_cap: USD 0"
)
_REQUIRED_LABELS = {
    "research_only",
    "paper_lab_candidate",
    "not_live_authorized",
    "profit_claim=none",
}
_REQUIRED_LIMITATIONS = {
    "not_profit_evidence",
    "offline_research_only",
    "paper_preview_requires_separate_milestone",
    "no_broker_action_authorized",
    "not_live_authorized",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "broker",
    "credential",
    "execution_intent",
    "execution_plan",
    "fill",
    "oms",
    "order",
    "portfolio",
    "position",
    "mutation",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
    "algotrader.research.etf_sma_backtest_summary",
    "algotrader.research.etf_sma_paper_experiment_plan",
    "algotrader.research.etf_sma_research_candidate",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
    "pandas",
    "polygon",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "urllib",
    "vectorbt",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "ExecutionIntent",
    "ExecutionPlan",
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "getenv",
    "liquidate",
    "open",
    "os.getenv",
    "post",
    "read",
    "request",
    "socket.socket",
    "submit_order",
    "time.time",
    "urlopen",
    "write",
}


def test_builds_ready_packet_from_valid_candidate_plan_and_backtest() -> None:
    candidate, plan, backtest = _valid_sources()

    packet = build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        backtest,
        as_of=_AS_OF,
    )
    payload = packet.to_dict()

    assert packet.status == "ready_for_paper_lab_preview_design"
    assert packet.eligibility_status == "ready_for_paper_lab_preview_design"
    assert packet.required_next_action == "draft_separate_paper_lab_preview_plan"
    assert packet.symbol == candidate.symbol == plan.symbol == backtest.symbol
    assert packet.strategy_name == _STRATEGY_NAME
    assert packet.as_of == _AS_OF
    assert packet.candidate_status == candidate.status
    assert packet.candidate_eligibility_status == candidate.eligibility_status
    assert packet.plan_review_status == plan.review_status
    assert packet.plan_action_posture == "candidate_long_bias"
    assert packet.backtest_eligibility_status == backtest.eligibility_status
    assert packet.latest_posture == "bullish_trend_candidate"
    assert packet.bar_count == 5
    assert packet.signal_count == 3
    assert packet.exposure_count == 2
    assert packet.defensive_count == 3
    assert packet.posture_change_count == 1
    assert packet.ignored_future_bar_count == 0
    assert packet.strategy_total_return == Decimal("3")
    assert packet.benchmark_total_return == Decimal("7")
    assert packet.max_drawdown == Decimal("0")
    assert packet.blocking_reasons == ()
    assert set(packet.labels) == _REQUIRED_LABELS
    assert set(packet.limitations).issuperset(_REQUIRED_LIMITATIONS)
    assert payload["strategy_total_return"] == "3"
    assert payload["benchmark_total_return"] == "7"
    assert payload["max_drawdown"] == "0"
    assert payload["candidate_labels"] == list(candidate.labels)
    assert payload["plan_labels"] == list(plan.labels)
    assert payload["backtest_labels"] == list(backtest.labels)
    assert payload["labels"] == list(ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS)
    assert payload["blocking_reasons"] == []
    assert all(item in packet.evidence_summary for item in candidate.evidence_summary)


def test_packet_is_immutable_and_dict_lists_are_copied() -> None:
    packet = _packet()

    with pytest.raises(FrozenInstanceError):
        packet.status = "changed"

    payload = packet.to_dict()
    payload["labels"].append("changed")
    payload["candidate_labels"].append("changed")
    payload["limitations"].append("changed")
    payload["blocking_reasons"].append("changed")
    payload["evidence_summary"].append("changed")

    assert "changed" not in packet.labels
    assert "changed" not in packet.candidate_labels
    assert "changed" not in packet.limitations
    assert "changed" not in packet.blocking_reasons
    assert "changed" not in packet.evidence_summary
    assert "changed" not in packet.to_dict()["labels"]


def test_packet_constructor_converts_lists_to_tuples() -> None:
    packet = EtfSmaResearchToPaperPacket(
        packet_type="etf_sma_research_to_paper_evidence_packet",
        status="blocked_from_paper_lab_preview_design",
        symbol="SPY",
        strategy_name=_STRATEGY_NAME,
        as_of=_AS_OF,
        candidate_status="research_candidate_only",
        candidate_eligibility_status="separate_plan_required_before_paper_experiment",
        plan_review_status="requires_operator_review",
        plan_action_posture="observe_only",
        backtest_eligibility_status="research_measurement_only",
        latest_posture="insufficient_history",
        bar_count=2,
        signal_count=0,
        exposure_count=0,
        defensive_count=2,
        posture_change_count=0,
        ignored_future_bar_count=0,
        strategy_total_return=Decimal("0"),
        benchmark_total_return=Decimal("0.1"),
        max_drawdown=Decimal("0"),
        candidate_labels=list(ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS),
        plan_labels=list(ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS),
        backtest_labels=list(ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS),
        labels=list(ETF_SMA_RESEARCH_TO_PAPER_PACKET_LABELS),
        eligibility_status="blocked_from_paper_lab_preview_design",
        blocking_reasons=["candidate_insufficient_history"],
        required_next_action="draft_separate_paper_lab_preview_plan",
        limitations=list(ETF_SMA_RESEARCH_TO_PAPER_PACKET_LIMITATIONS),
        evidence_summary=["example evidence"],
    )

    assert type(packet.candidate_labels) is tuple
    assert type(packet.plan_labels) is tuple
    assert type(packet.backtest_labels) is tuple
    assert type(packet.labels) is tuple
    assert type(packet.limitations) is tuple
    assert type(packet.blocking_reasons) is tuple
    assert type(packet.evidence_summary) is tuple


def test_packet_dict_is_primitive_only() -> None:
    _assert_primitive_only(_packet().to_dict())


def test_packet_output_has_no_execution_or_capital_mutation_fields() -> None:
    for key in _flatten_dict_keys(_packet().to_dict()):
        lowered = key.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)


def test_live_authorized_source_label_blocks_packet() -> None:
    candidate, plan, backtest = _valid_sources()
    unsafe_candidate = _unsafe_candidate_with(
        candidate,
        labels=(*candidate.labels, "live_authorized"),
    )

    packet = build_etf_sma_research_to_paper_packet(
        unsafe_candidate,
        plan,
        backtest,
        as_of=_AS_OF,
    )

    assert packet.status == "blocked_from_paper_lab_preview_design"
    assert "source_contains_live_authorized_label" in packet.blocking_reasons
    assert "live_authorized" in packet.candidate_labels


def test_non_paper_lab_candidate_label_blocks_packet() -> None:
    candidate, plan, backtest = _valid_sources()
    unsafe_candidate = _unsafe_candidate_with(
        candidate,
        labels=(
            "research_only",
            "not_live_authorized",
            "profit_claim=none",
        ),
    )

    packet = build_etf_sma_research_to_paper_packet(
        unsafe_candidate,
        plan,
        backtest,
        as_of=_AS_OF,
    )

    assert packet.status == "blocked_from_paper_lab_preview_design"
    assert "candidate_missing_paper_lab_candidate_label" in packet.blocking_reasons


def test_insufficient_history_observe_only_sources_block_packet() -> None:
    candidate = _candidate(("2026-01-01", "10"), ("2026-01-02", "11"), as_of="2026-01-02")
    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)
    backtest = _backtest(
        ("2026-01-01", "10"),
        ("2026-01-02", "11"),
        as_of="2026-01-02",
    )

    packet = build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        backtest,
        as_of="2026-01-02",
    )

    assert packet.status == "blocked_from_paper_lab_preview_design"
    assert packet.latest_posture == "insufficient_history"
    assert packet.signal_count == 0
    assert packet.plan_action_posture == "observe_only"
    assert "candidate_insufficient_history" in packet.blocking_reasons
    assert "plan_observe_only" in packet.blocking_reasons
    assert "backtest_zero_signal_count" in packet.blocking_reasons
    assert "backtest_insufficient_history" in packet.blocking_reasons


def test_defensive_plan_state_blocks_packet_conservatively() -> None:
    candidate = _candidate(
        ("2026-01-01", "80"),
        ("2026-01-02", "40"),
        ("2026-01-03", "20"),
        ("2026-01-04", "10"),
        ("2026-01-05", "5"),
    )
    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)
    backtest = _backtest(
        ("2026-01-01", "80"),
        ("2026-01-02", "40"),
        ("2026-01-03", "20"),
        ("2026-01-04", "10"),
        ("2026-01-05", "5"),
    )

    packet = build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        backtest,
        as_of=_AS_OF,
    )

    assert packet.status == "blocked_from_paper_lab_preview_design"
    assert packet.plan_action_posture == "candidate_defensive_bias"
    assert "plan_defensive_bias" in packet.blocking_reasons


def test_positive_backtest_return_does_not_create_profit_claim() -> None:
    packet = _packet()
    payload_text = repr(packet.to_dict())

    assert packet.strategy_total_return > Decimal("0")
    assert "profit_claim=none" in packet.labels
    assert "not_profit_evidence" in packet.limitations
    assert "profit_claim=positive" not in payload_text
    assert "profit_claim=profit" not in payload_text
    assert any("do not change profit_claim=none" in item for item in packet.evidence_summary)


def test_packet_does_not_authorize_broker_action() -> None:
    packet = _packet()
    action = packet.required_next_action

    assert action == "draft_separate_paper_lab_preview_plan"
    assert packet.status == "ready_for_paper_lab_preview_design"
    assert "no_broker_action_authorized" in packet.limitations
    for unsafe_term in ("submit", "buy", "sell", "trade", "execute"):
        assert unsafe_term not in action


def test_packet_preserves_future_bar_ignore_count_from_backtest_summary() -> None:
    candidate, plan, _backtest_without_future = _valid_sources()
    with_future_backtest = build_etf_sma_backtest_summary(
        [
            *_backtest_bars(
                ("2026-01-01", "10"),
                ("2026-01-02", "10"),
                ("2026-01-03", "20"),
                ("2026-01-04", "40"),
                ("2026-01-05", "80"),
            ),
            EtfSmaBacktestBar("2026-01-06", Decimal("1")),
            EtfSmaBacktestBar("2026-01-07", Decimal("1")),
        ],
        _BACKTEST_CONFIG,
        _AS_OF,
    )

    packet = build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        with_future_backtest,
        as_of=_AS_OF,
    )

    assert packet.ignored_future_bar_count == 2
    assert packet.strategy_total_return == Decimal("3")
    assert packet.benchmark_total_return == Decimal("7")


def test_mismatched_source_as_of_is_rejected() -> None:
    candidate, plan, backtest = _valid_sources()

    with pytest.raises(ValueError, match="as_of"):
        build_etf_sma_research_to_paper_packet(
            candidate,
            plan,
            backtest,
            as_of="2026-01-04",
        )


def test_module_has_no_forbidden_imports_or_runtime_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _packet() -> EtfSmaResearchToPaperPacket:
    candidate, plan, backtest = _valid_sources()
    return build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        backtest,
        as_of=_AS_OF,
    )


def _valid_sources() -> tuple[
    SmaResearchToPaperCandidate,
    EtfSmaPaperExperimentPlan,
    EtfSmaBacktestSummary,
]:
    candidate = _candidate(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "40"),
        ("2026-01-05", "80"),
    )
    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)
    backtest = _backtest(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "40"),
        ("2026-01-05", "80"),
    )
    return candidate, plan, backtest


def _candidate(
    *values: tuple[str, str],
    as_of: str = _AS_OF,
) -> SmaResearchToPaperCandidate:
    return build_etf_sma_research_candidate(
        _candidate_bars(*values),
        _CANDIDATE_CONFIG,
        as_of,
    )


def _backtest(
    *values: tuple[str, str],
    as_of: str = _AS_OF,
) -> EtfSmaBacktestSummary:
    return build_etf_sma_backtest_summary(
        _backtest_bars(*values),
        _BACKTEST_CONFIG,
        as_of,
    )


def _candidate_bars(*values: tuple[str, str]) -> list[SmaCandidateInputBar]:
    return [SmaCandidateInputBar(day, Decimal(close)) for day, close in values]


def _backtest_bars(*values: tuple[str, str]) -> list[EtfSmaBacktestBar]:
    return [EtfSmaBacktestBar(day, Decimal(close)) for day, close in values]


def _unsafe_candidate_with(
    candidate: SmaResearchToPaperCandidate,
    **changes: object,
) -> SmaResearchToPaperCandidate:
    clone = object.__new__(SmaResearchToPaperCandidate)
    for field in fields(SmaResearchToPaperCandidate):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(candidate, field.name)),
        )

    return clone


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal, date))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_only(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_primitive_only(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


def _flatten_dict_keys(value: object) -> tuple[str, ...]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_flatten_dict_keys(item))
        return tuple(keys)

    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_flatten_dict_keys(item))
        return tuple(keys)

    return ()


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
