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
from algotrader.research.etf_sma_paper_preview_design import (
    ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS,
    ETF_SMA_PAPER_PREVIEW_DESIGN_LIMITATIONS,
    ETF_SMA_PAPER_PREVIEW_DESIGN_REQUIRED_OPERATOR_CHECKS,
    EtfSmaPaperPreviewDesign,
    EtfSmaPaperPreviewDesignConfig,
    build_etf_sma_paper_preview_design,
)
from algotrader.research.etf_sma_research_candidate import (
    SmaCandidateConfig,
    SmaCandidateInputBar,
    SmaResearchToPaperCandidate,
    build_etf_sma_research_candidate,
)
from algotrader.research.etf_sma_research_to_paper_packet import (
    EtfSmaResearchToPaperPacket,
    build_etf_sma_research_to_paper_packet,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_paper_preview_design.py")
_AS_OF = "2026-01-05"
_STRATEGY_NAME = "SPY SMA paper preview design"
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
    "offline_design_only",
    "not_profit_evidence",
    "no_broker_preview_authorized",
    "no_broker_action_authorized",
    "paper_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
    "not_live_authorized",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "broker",
    "buying_power",
    "cash",
    "execution_intent",
    "execution_plan",
    "execution_venue",
    "fill",
    "order",
    "portfolio",
    "position",
    "quantity",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
    "algotrader.research.etf_sma_research_to_paper_packet",
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


def test_valid_ready_m338_packet_produces_ready_preview_design() -> None:
    packet = _ready_packet()

    design = build_etf_sma_paper_preview_design(packet, _config())
    payload = design.to_dict()

    assert design.status == "ready_for_paper_lab_preview_prompt_review"
    assert design.preview_design_status == design.status
    assert design.required_next_action == "draft_separate_paper_lab_preview_prompt"
    assert design.source_packet_status == "ready_for_paper_lab_preview_design"
    assert design.source_packet_eligibility_status == (
        "ready_for_paper_lab_preview_design"
    )
    assert design.source_packet_required_next_action == (
        "draft_separate_paper_lab_preview_plan"
    )
    assert design.symbol == packet.symbol
    assert design.strategy_name == _STRATEGY_NAME
    assert design.latest_posture == "bullish_trend_candidate"
    assert design.bar_count == 5
    assert design.signal_count == 3
    assert design.exposure_count == 2
    assert design.defensive_count == 3
    assert design.posture_change_count == 1
    assert design.strategy_total_return == Decimal("3")
    assert design.benchmark_total_return == Decimal("7")
    assert design.max_drawdown == Decimal("0")
    assert design.blocking_reasons == ()
    assert set(design.source_labels) == _REQUIRED_LABELS
    assert set(design.labels) == _REQUIRED_LABELS
    assert set(design.limitations).issuperset(_REQUIRED_LIMITATIONS)
    assert set(design.required_future_operator_checks).issuperset(
        set(ETF_SMA_PAPER_PREVIEW_DESIGN_REQUIRED_OPERATOR_CHECKS)
    )
    assert payload["strategy_total_return"] == "3"
    assert payload["benchmark_total_return"] == "7"
    assert payload["max_drawdown"] == "0"
    assert payload["source_labels"] == list(packet.labels)
    assert payload["labels"] == list(ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS)
    assert payload["blocking_reasons"] == []


def test_blocked_m338_packet_produces_blocked_preview_design() -> None:
    packet = _insufficient_history_packet()

    design = build_etf_sma_paper_preview_design(packet, _config())

    assert design.status == "blocked_from_paper_lab_preview_prompt_review"
    assert design.required_next_action == "resolve_research_to_paper_packet_blockers"
    assert design.source_packet_status == "blocked_from_paper_lab_preview_design"
    assert design.latest_posture == "insufficient_history"
    assert "source_packet_not_ready_for_paper_lab_preview_design" in (
        design.blocking_reasons
    )
    assert "candidate_insufficient_history" in design.blocking_reasons
    assert "plan_observe_only" in design.blocking_reasons
    assert "source_insufficient_history_posture" in design.blocking_reasons


def test_source_labels_are_preserved_and_tuple_normalized() -> None:
    packet = _ready_packet()
    unsafe_packet = _unsafe_packet_with(packet, labels=list(packet.labels))

    design = build_etf_sma_paper_preview_design(unsafe_packet, _config())

    assert type(design.source_labels) is tuple
    assert design.source_labels == packet.labels
    assert type(design.labels) is tuple
    assert design.labels == ETF_SMA_PAPER_PREVIEW_DESIGN_LABELS


def test_limitations_and_operator_checks_are_tuple_normalized() -> None:
    packet = _ready_packet()
    unsafe_packet = _unsafe_packet_with(packet, limitations=list(packet.limitations))
    config = EtfSmaPaperPreviewDesignConfig(
        required_future_operator_checks=list(
            ETF_SMA_PAPER_PREVIEW_DESIGN_REQUIRED_OPERATOR_CHECKS
        ),
        additional_limitations=["manual_prompt_review_only"],
    )

    design = build_etf_sma_paper_preview_design(unsafe_packet, config)

    assert type(config.required_future_operator_checks) is tuple
    assert type(config.additional_limitations) is tuple
    assert type(design.required_future_operator_checks) is tuple
    assert type(design.source_limitations) is tuple
    assert type(design.limitations) is tuple
    assert "manual_prompt_review_only" in design.limitations
    assert set(ETF_SMA_PAPER_PREVIEW_DESIGN_LIMITATIONS).issubset(
        set(design.limitations)
    )


def test_preview_design_is_immutable_and_dict_lists_are_copied() -> None:
    design = _design()

    with pytest.raises(FrozenInstanceError):
        design.status = "changed"

    payload = design.to_dict()
    payload["labels"].append("changed")
    payload["source_labels"].append("changed")
    payload["limitations"].append("changed")
    payload["source_limitations"].append("changed")
    payload["blocking_reasons"].append("changed")
    payload["required_future_operator_checks"].append("changed")

    assert "changed" not in design.labels
    assert "changed" not in design.source_labels
    assert "changed" not in design.limitations
    assert "changed" not in design.source_limitations
    assert "changed" not in design.blocking_reasons
    assert "changed" not in design.required_future_operator_checks
    assert "changed" not in design.to_dict()["labels"]


def test_preview_design_dict_is_primitive_only() -> None:
    _assert_primitive_only(_design().to_dict())


def test_live_authorized_source_blocks_preview_design() -> None:
    packet = _ready_packet()
    unsafe_packet = _unsafe_packet_with(
        packet,
        labels=(*packet.labels, "live_authorized"),
    )

    design = build_etf_sma_paper_preview_design(unsafe_packet, _config())

    assert design.status == "blocked_from_paper_lab_preview_prompt_review"
    assert "live_authorized" in design.source_labels
    assert "source_contains_live_authorized" in design.blocking_reasons


def test_profit_claim_other_than_none_blocks_preview_design() -> None:
    packet = _ready_packet()
    unsafe_packet = _unsafe_packet_with(
        packet,
        labels=(*packet.labels, "profit_claim=positive"),
    )

    design = build_etf_sma_paper_preview_design(unsafe_packet, _config())

    assert design.status == "blocked_from_paper_lab_preview_prompt_review"
    assert "source_contains_profit_claim_other_than_none" in (
        design.blocking_reasons
    )
    assert "profit_claim=none" in design.labels


def test_positive_backtest_return_does_not_create_profit_claim() -> None:
    design = _design()
    payload_text = repr(design.to_dict())

    assert design.strategy_total_return > Decimal("0")
    assert "profit_claim=none" in design.labels
    assert "not_profit_evidence" in design.limitations
    assert "profit_claim=positive" not in payload_text
    assert "profit_claim=profit" not in payload_text


def test_defensive_and_observe_only_postures_remain_conservative() -> None:
    defensive_design = build_etf_sma_paper_preview_design(
        _defensive_packet(),
        _config(),
    )
    observe_only_design = build_etf_sma_paper_preview_design(
        _insufficient_history_packet(),
        _config(),
    )

    assert defensive_design.status == "blocked_from_paper_lab_preview_prompt_review"
    assert defensive_design.latest_posture == "defensive_or_cash_candidate"
    assert "plan_defensive_bias" in defensive_design.blocking_reasons
    assert "source_defensive_posture" in defensive_design.blocking_reasons
    assert observe_only_design.status == "blocked_from_paper_lab_preview_prompt_review"
    assert observe_only_design.latest_posture == "insufficient_history"
    assert "plan_observe_only" in observe_only_design.blocking_reasons


def test_preview_design_has_no_mutation_or_execution_fields() -> None:
    design = _design()

    for field in fields(EtfSmaPaperPreviewDesign):
        lowered = field.name.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    for key in _flatten_dict_keys(design.to_dict()):
        lowered = key.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)


def test_preview_design_module_has_no_execution_intent_or_plan_reference() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "ExecutionIntent" not in source
    assert "ExecutionPlan" not in source
    assert "execution_intent" not in source
    assert "execution_plan" not in source


def test_preview_design_output_is_deterministic_from_same_input() -> None:
    packet = _ready_packet()
    config = _config()

    first = build_etf_sma_paper_preview_design(packet, config)
    second = build_etf_sma_paper_preview_design(packet, config)

    assert first == second
    assert first.to_dict() == second.to_dict()


def test_dependency_direction_remains_clean() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _config() -> EtfSmaPaperPreviewDesignConfig:
    return EtfSmaPaperPreviewDesignConfig()


def _design() -> EtfSmaPaperPreviewDesign:
    return build_etf_sma_paper_preview_design(_ready_packet(), _config())


def _ready_packet() -> EtfSmaResearchToPaperPacket:
    candidate, plan, backtest = _valid_sources()
    return build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        backtest,
        as_of=_AS_OF,
    )


def _insufficient_history_packet() -> EtfSmaResearchToPaperPacket:
    as_of = "2026-01-02"
    candidate = _candidate(
        ("2026-01-01", "10"),
        ("2026-01-02", "11"),
        as_of=as_of,
    )
    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)
    backtest = _backtest(
        ("2026-01-01", "10"),
        ("2026-01-02", "11"),
        as_of=as_of,
    )

    return build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        backtest,
        as_of=as_of,
    )


def _defensive_packet() -> EtfSmaResearchToPaperPacket:
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


def _unsafe_packet_with(
    packet: EtfSmaResearchToPaperPacket,
    **changes: object,
) -> EtfSmaResearchToPaperPacket:
    clone = object.__new__(EtfSmaResearchToPaperPacket)
    for field in fields(EtfSmaResearchToPaperPacket):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(packet, field.name)),
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
