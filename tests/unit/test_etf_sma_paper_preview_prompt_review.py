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
    EtfSmaPaperPreviewDesign,
    EtfSmaPaperPreviewDesignConfig,
    build_etf_sma_paper_preview_design,
)
from algotrader.research.etf_sma_paper_preview_prompt_review import (
    ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS,
    ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LIMITATIONS,
    ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_OPERATOR_CHECKLIST,
    EtfSmaPaperPreviewPromptReview,
    EtfSmaPaperPreviewPromptReviewConfig,
    build_etf_sma_paper_preview_prompt_review,
)
from algotrader.research.etf_sma_research_candidate import (
    SmaCandidateConfig,
    SmaCandidateInputBar,
    SmaResearchToPaperCandidate,
    build_etf_sma_research_candidate,
)
from algotrader.research.etf_sma_research_to_paper_packet import (
    build_etf_sma_research_to_paper_packet,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_paper_preview_prompt_review.py")
_AS_OF = "2026-01-05"
_STRATEGY_NAME = "SPY SMA paper preview prompt review"
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
    "offline_prompt_review_only",
    "not_profit_evidence",
    "no_broker_preview_authorized",
    "no_broker_action_authorized",
    "paper_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
    "not_live_authorized",
}
_REQUIRED_CHECKLIST = {
    "confirm paper profile only",
    "run fresh read-only paper snapshot before any future broker-facing preview",
    "confirm no open conflicting orders before future preview",
    "explicit operator approval required before broker-facing preview",
    "separate milestone required before broker-facing preview",
    "separate milestone required before any submit",
    "no live trading authorization",
    "stop on ambiguous broker response",
    "no retry/cancel/liquidate/fix-forward without separate explicit milestone",
}
_REQUIRED_TEMPLATE_PLACEHOLDERS = (
    "<FUTURE_SEPARATE_MILESTONE_REQUIRED>",
    "<BROKER_PREVIEW_COMMAND_NOT_INCLUDED>",
    "<SUBMIT_FLAG_NOT_INCLUDED>",
    "<PAPER_PROFILE_REQUIRED>",
    "<FRESH_READ_ONLY_SNAPSHOT_REQUIRED>",
)
_FORBIDDEN_SUBMIT_FLAG_PATTERNS = (
    "--submit",
    "submit=true",
    "submit = true",
    "submit: true",
    "submit=yes",
    "submit = yes",
    "submit: yes",
    "submit=1",
    "submit = 1",
    "submit: 1",
)
_FORBIDDEN_BROKER_COMMAND_PATTERNS = (
    "submit_order",
    "create_order",
    "cancel_order",
    "replace_order",
    "close_position",
    "liquidate",
    "preview_order",
    "stage_order",
    "alpaca",
)
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
_FORBIDDEN_REAL_FIELD_PHRASES = (
    "order id",
    "client order id",
    "broker id",
    "fill id",
    "filled quantity",
    "account id",
    "buying power",
    "portfolio value",
    "position quantity",
    "execution venue",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
    "algotrader.research.etf_sma_paper_preview_design",
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


def test_ready_m339_design_produces_prompt_ready_for_operator_review() -> None:
    design = _ready_design()

    review = build_etf_sma_paper_preview_prompt_review(design, _config())
    payload = review.to_dict()

    assert review.status == "prompt_ready_for_operator_review"
    assert review.prompt_review_status == review.status
    assert review.future_prompt_ready is True
    assert review.required_next_action == (
        "operator_review_before_separate_paper_preview_milestone"
    )
    assert review.source_design_status == (
        "ready_for_paper_lab_preview_prompt_review"
    )
    assert review.source_design_required_next_action == (
        "draft_separate_paper_lab_preview_prompt"
    )
    assert review.symbol == design.symbol
    assert review.strategy_name == _STRATEGY_NAME
    assert review.latest_posture == "bullish_trend_candidate"
    assert review.strategy_total_return == Decimal("3")
    assert review.benchmark_total_return == Decimal("7")
    assert review.max_drawdown == Decimal("0")
    assert review.bar_count == 5
    assert review.signal_count == 3
    assert review.exposure_count == 2
    assert review.defensive_count == 3
    assert review.posture_change_count == 1
    assert review.blocking_reasons == ()
    assert set(review.source_labels) == _REQUIRED_LABELS
    assert set(review.labels) == _REQUIRED_LABELS
    assert set(review.limitations).issuperset(_REQUIRED_LIMITATIONS)
    assert set(review.future_operator_checklist).issuperset(_REQUIRED_CHECKLIST)
    assert payload["strategy_total_return"] == "3"
    assert payload["benchmark_total_return"] == "7"
    assert payload["max_drawdown"] == "0"
    assert payload["source_labels"] == list(design.labels)
    assert payload["labels"] == list(ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LABELS)
    assert payload["blocking_reasons"] == []


def test_blocked_m339_design_produces_blocked_prompt_review() -> None:
    design = _insufficient_history_design()

    review = build_etf_sma_paper_preview_prompt_review(design, _config())

    assert review.status == "blocked_from_prompt_review"
    assert review.future_prompt_ready is False
    assert review.required_next_action == "resolve_paper_preview_design_blockers"
    assert review.source_design_status == (
        "blocked_from_paper_lab_preview_prompt_review"
    )
    assert review.latest_posture == "insufficient_history"
    assert "source_design_not_ready_for_prompt_review" in review.blocking_reasons
    assert "candidate_insufficient_history" in review.blocking_reasons
    assert "plan_observe_only" in review.blocking_reasons
    assert "source_insufficient_history_posture" in review.blocking_reasons


def test_future_prompt_template_contains_non_executable_placeholders() -> None:
    template = _review().future_prompt_template

    for placeholder in _REQUIRED_TEMPLATE_PLACEHOLDERS:
        assert placeholder in template

    assert "<BROKER_PREVIEW_COMMAND_NOT_INCLUDED>" in template
    assert "<SUBMIT_FLAG_NOT_INCLUDED>" in template


def test_future_prompt_template_does_not_contain_submit_flags() -> None:
    template = _review().future_prompt_template.lower()

    assert "<submit_flag_not_included>" in template
    assert all(pattern not in template for pattern in _FORBIDDEN_SUBMIT_FLAG_PATTERNS)


def test_future_prompt_template_does_not_contain_broker_execution_commands() -> None:
    template = _review().future_prompt_template.lower()

    assert "<broker_preview_command_not_included>" in template
    assert all(
        pattern not in template for pattern in _FORBIDDEN_BROKER_COMMAND_PATTERNS
    )


def test_labels_limitations_blockers_and_checklist_are_tuple_normalized() -> None:
    design = _ready_design()
    unsafe_design = _unsafe_design_with(
        design,
        labels=list(design.labels),
        limitations=list(design.limitations),
        blocking_reasons=[],
    )
    config = EtfSmaPaperPreviewPromptReviewConfig(
        future_operator_checklist=list(
            ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_OPERATOR_CHECKLIST
        ),
        additional_limitations=["manual_operator_review_only"],
    )

    review = build_etf_sma_paper_preview_prompt_review(unsafe_design, config)

    assert type(config.future_operator_checklist) is tuple
    assert type(config.additional_limitations) is tuple
    assert type(review.source_labels) is tuple
    assert type(review.labels) is tuple
    assert type(review.blocking_reasons) is tuple
    assert type(review.source_limitations) is tuple
    assert type(review.limitations) is tuple
    assert type(review.future_operator_checklist) is tuple
    assert "manual_operator_review_only" in review.limitations
    assert set(ETF_SMA_PAPER_PREVIEW_PROMPT_REVIEW_LIMITATIONS).issubset(
        set(review.limitations)
    )


def test_prompt_review_is_immutable_and_dict_lists_are_copied() -> None:
    review = _review()

    with pytest.raises(FrozenInstanceError):
        review.status = "changed"

    payload = review.to_dict()
    payload["labels"].append("changed")
    payload["source_labels"].append("changed")
    payload["limitations"].append("changed")
    payload["source_limitations"].append("changed")
    payload["blocking_reasons"].append("changed")
    payload["future_operator_checklist"].append("changed")

    assert "changed" not in review.labels
    assert "changed" not in review.source_labels
    assert "changed" not in review.limitations
    assert "changed" not in review.source_limitations
    assert "changed" not in review.blocking_reasons
    assert "changed" not in review.future_operator_checklist
    assert "changed" not in review.to_dict()["labels"]


def test_prompt_review_dict_is_primitive_only() -> None:
    _assert_primitive_only(_review().to_dict())


def test_live_authorized_source_blocks_prompt_review() -> None:
    design = _ready_design()
    unsafe_design = _unsafe_design_with(
        design,
        labels=(*design.labels, "live_authorized"),
    )

    review = build_etf_sma_paper_preview_prompt_review(unsafe_design, _config())

    assert review.status == "blocked_from_prompt_review"
    assert "live_authorized" in review.source_labels
    assert "source_contains_live_authorized" in review.blocking_reasons


def test_profit_claim_other_than_none_blocks_prompt_review() -> None:
    design = _ready_design()
    unsafe_design = _unsafe_design_with(
        design,
        labels=(*design.labels, "profit_claim=positive"),
    )

    review = build_etf_sma_paper_preview_prompt_review(unsafe_design, _config())

    assert review.status == "blocked_from_prompt_review"
    assert "source_contains_profit_claim_other_than_none" in review.blocking_reasons
    assert "profit_claim=none" in review.labels


def test_positive_backtest_return_does_not_create_profit_claim() -> None:
    review = _review()
    payload_text = repr(review.to_dict())

    assert review.strategy_total_return > Decimal("0")
    assert "profit_claim=none" in review.labels
    assert "not_profit_evidence" in review.limitations
    assert "profit_claim=positive" not in payload_text
    assert "profit_claim=profit" not in payload_text


def test_defensive_and_observe_only_postures_remain_conservative() -> None:
    defensive_review = build_etf_sma_paper_preview_prompt_review(
        _defensive_design(),
        _config(),
    )
    observe_only_review = build_etf_sma_paper_preview_prompt_review(
        _insufficient_history_design(),
        _config(),
    )

    assert defensive_review.status == "blocked_from_prompt_review"
    assert defensive_review.future_prompt_ready is False
    assert defensive_review.latest_posture == "defensive_or_cash_candidate"
    assert "plan_defensive_bias" in defensive_review.blocking_reasons
    assert "source_defensive_posture" in defensive_review.blocking_reasons
    assert observe_only_review.status == "blocked_from_prompt_review"
    assert observe_only_review.future_prompt_ready is False
    assert observe_only_review.latest_posture == "insufficient_history"
    assert "plan_observe_only" in observe_only_review.blocking_reasons


def test_prompt_review_has_no_mutation_or_execution_fields() -> None:
    review = _review()
    payload_text = repr(review.to_dict()).lower()

    for field in fields(EtfSmaPaperPreviewPromptReview):
        lowered = field.name.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    for key in _flatten_dict_keys(review.to_dict()):
        lowered = key.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    for phrase in _FORBIDDEN_REAL_FIELD_PHRASES:
        assert phrase not in payload_text


def test_prompt_review_module_has_no_execution_intent_or_plan_reference() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source


def test_prompt_review_output_is_deterministic_from_same_input() -> None:
    design = _ready_design()
    config = _config()

    first = build_etf_sma_paper_preview_prompt_review(design, config)
    second = build_etf_sma_paper_preview_prompt_review(design, config)

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


def _config() -> EtfSmaPaperPreviewPromptReviewConfig:
    return EtfSmaPaperPreviewPromptReviewConfig()


def _review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(_ready_design(), _config())


def _ready_design() -> EtfSmaPaperPreviewDesign:
    return build_etf_sma_paper_preview_design(_ready_packet(), _design_config())


def _insufficient_history_design() -> EtfSmaPaperPreviewDesign:
    return build_etf_sma_paper_preview_design(
        _insufficient_history_packet(),
        _design_config(),
    )


def _defensive_design() -> EtfSmaPaperPreviewDesign:
    return build_etf_sma_paper_preview_design(_defensive_packet(), _design_config())


def _design_config() -> EtfSmaPaperPreviewDesignConfig:
    return EtfSmaPaperPreviewDesignConfig()


def _ready_packet() -> object:
    candidate, plan, backtest = _valid_sources()
    return build_etf_sma_research_to_paper_packet(
        candidate,
        plan,
        backtest,
        as_of=_AS_OF,
    )


def _insufficient_history_packet() -> object:
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


def _defensive_packet() -> object:
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


def _unsafe_design_with(
    design: EtfSmaPaperPreviewDesign,
    **changes: object,
) -> EtfSmaPaperPreviewDesign:
    clone = object.__new__(EtfSmaPaperPreviewDesign)
    for field in fields(EtfSmaPaperPreviewDesign):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(design, field.name)),
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
