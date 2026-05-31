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
    EtfSmaPaperPreviewDesignConfig,
    build_etf_sma_paper_preview_design,
)
from algotrader.research.etf_sma_paper_preview_operator_review import (
    ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS,
    ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LIMITATIONS,
    ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_REQUIRED_CHECKS,
    EtfSmaPaperPreviewOperatorReview,
    EtfSmaPaperPreviewOperatorReviewConfig,
    build_etf_sma_paper_preview_operator_review,
)
from algotrader.research.etf_sma_paper_preview_prompt_review import (
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


MODULE_PATH = Path("src/algotrader/research/etf_sma_paper_preview_operator_review.py")
_AS_OF = "2026-01-05"
_STRATEGY_NAME = "SPY SMA paper preview operator review"
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
    "offline_operator_review_only",
    "manual_operator_review_required",
    "fresh_read_only_paper_snapshot_required_before_later_broker_facing_preview",
    "not_live_authorization",
    "not_profit_evidence",
    "not_strategy_validation",
    "not_execution_authority",
    "no_broker_preview_authorized",
    "no_broker_action_authorized",
    "paper_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
}
_REQUIRED_CHECKS = {
    "manual operator review before any future separate paper-preview milestone",
    "fresh read-only paper snapshot before any later broker-facing preview/probe milestone",
    "separate milestone required before broker-facing preview/probe work",
    "no broker action from this operator review",
    "no preview/staging from this operator review",
    "no submit authority from this operator review",
    "resolve M340 prompt-review blockers before preparing a separate milestone",
}
_REQUIRED_TEMPLATE_MARKERS = (
    "<FUTURE_SEPARATE_MILESTONE_REQUIRED>",
    "<MANUAL_OPERATOR_REVIEW_REQUIRED>",
    "<FRESH_READ_ONLY_PAPER_SNAPSHOT_REQUIRED>",
    "<BROKER_PREVIEW_COMMAND_NOT_INCLUDED>",
    "<SUBMIT_FLAG_NOT_INCLUDED>",
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
_FORBIDDEN_COMMAND_PATTERNS = (
    "submit_order",
    "create_order",
    "cancel_order",
    "replace_order",
    "close_position",
    "liquidate",
    "preview_order",
    "stage_order",
    "python -m",
)
_ALLOWED_SAFETY_FIELDS = {
    "authorize_broker_action",
    "broker_action_performed",
    "broker_preview_performed",
    "submit_allowed",
}
_FORBIDDEN_REAL_FIELD_TERMS = (
    "account",
    "alpaca",
    "credential",
    "execution_intent",
    "execution_plan",
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
    "portfolio value",
    "position quantity",
    "credential",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
    "algotrader.research.etf_sma_paper_preview_prompt_review",
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


def test_ready_m340_prompt_review_authorizes_separate_preview_milestone() -> None:
    prompt_review = _ready_prompt_review()

    review = build_etf_sma_paper_preview_operator_review(prompt_review, _config())
    payload = review.to_dict()

    assert review.status == "authorize_separate_paper_preview_milestone"
    assert review.operator_review_status == review.status
    assert review.authorize_separate_paper_preview_milestone is True
    assert review.authorize_paper_preview_now is False
    assert review.authorize_broker_action is False
    assert review.broker_action_performed is False
    assert review.broker_preview_performed is False
    assert review.submit_allowed is False
    assert review.manual_operator_review_required is True
    assert review.fresh_read_only_paper_snapshot_required is True
    assert review.required_next_action == (
        "prepare_separate_etf_sma_paper_preview_milestone"
    )
    assert review.source_prompt_review_status == "prompt_ready_for_operator_review"
    assert review.source_future_prompt_ready is True
    assert review.source_prompt_review_required_next_action == (
        "operator_review_before_separate_paper_preview_milestone"
    )
    assert review.symbol == prompt_review.symbol
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
    assert review.source_blocking_reasons == ()
    assert review.blocking_reasons == ()
    assert set(review.source_labels) == _REQUIRED_LABELS
    assert set(review.labels) == _REQUIRED_LABELS
    assert set(review.limitations).issuperset(_REQUIRED_LIMITATIONS)
    assert set(review.required_future_operator_checks).issuperset(_REQUIRED_CHECKS)
    assert payload["strategy_total_return"] == "3"
    assert payload["benchmark_total_return"] == "7"
    assert payload["max_drawdown"] == "0"
    assert payload["source_labels"] == list(prompt_review.labels)
    assert payload["source_prompt_review_source_labels"] == list(
        prompt_review.source_labels
    )
    assert payload["labels"] == list(ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS)
    assert payload["blocking_reasons"] == []


def test_blocked_m340_prompt_review_remains_blocked() -> None:
    prompt_review = _insufficient_history_prompt_review()

    review = build_etf_sma_paper_preview_operator_review(prompt_review, _config())

    assert review.status == "blocked_from_separate_paper_preview_milestone"
    assert review.operator_review_status == review.status
    assert review.authorize_separate_paper_preview_milestone is False
    assert review.required_next_action == "resolve_prompt_review_blockers"
    assert review.source_prompt_review_status == "blocked_from_prompt_review"
    assert review.source_future_prompt_ready is False
    assert "source_prompt_review_not_ready" in review.blocking_reasons
    assert "source_future_prompt_not_ready" in review.blocking_reasons
    assert "candidate_insufficient_history" in review.source_blocking_reasons
    assert "candidate_insufficient_history" in review.blocking_reasons
    assert "plan_observe_only" in review.blocking_reasons
    assert "source_insufficient_history_posture" in review.blocking_reasons


def test_live_authorized_label_or_status_blocks_operator_review() -> None:
    prompt_review = _ready_prompt_review()
    unsafe_label_review = _unsafe_prompt_review_with(
        prompt_review,
        labels=(*prompt_review.labels, "live_authorized"),
    )
    unsafe_status_review = _unsafe_prompt_review_with(
        prompt_review,
        status="live_authorized",
        prompt_review_status="live_authorized",
    )

    label_review = build_etf_sma_paper_preview_operator_review(
        unsafe_label_review,
        _config(),
    )
    status_review = build_etf_sma_paper_preview_operator_review(
        unsafe_status_review,
        _config(),
    )

    assert label_review.status == "blocked_from_separate_paper_preview_milestone"
    assert "live_authorized" in label_review.source_labels
    assert "source_contains_live_authorized" in label_review.blocking_reasons
    assert status_review.status == "blocked_from_separate_paper_preview_milestone"
    assert "source_contains_live_authorized" in status_review.blocking_reasons


def test_profit_claim_other_than_none_blocks_operator_review() -> None:
    prompt_review = _ready_prompt_review()
    unsafe_review = _unsafe_prompt_review_with(
        prompt_review,
        labels=(*prompt_review.labels, "profit_claim=positive"),
    )

    review = build_etf_sma_paper_preview_operator_review(unsafe_review, _config())

    assert review.status == "blocked_from_separate_paper_preview_milestone"
    assert "source_contains_profit_claim_other_than_none" in review.blocking_reasons
    assert "profit_claim=positive" in review.source_labels
    assert "profit_claim=none" in review.labels


def test_missing_paper_lab_candidate_blocks_operator_review() -> None:
    prompt_review = _ready_prompt_review()
    unsafe_review = _unsafe_prompt_review_with(
        prompt_review,
        labels=tuple(
            label
            for label in prompt_review.labels
            if label != "paper_lab_candidate"
        ),
    )

    review = build_etf_sma_paper_preview_operator_review(unsafe_review, _config())

    assert review.status == "blocked_from_separate_paper_preview_milestone"
    assert "paper_lab_candidate" not in review.source_labels
    assert "source_missing_paper_lab_candidate_label" in review.blocking_reasons


def test_source_labels_are_preserved_exactly() -> None:
    prompt_review = _ready_prompt_review()

    review = build_etf_sma_paper_preview_operator_review(prompt_review, _config())

    assert review.source_labels == prompt_review.labels
    assert review.source_prompt_review_source_labels == prompt_review.source_labels
    assert review.labels == ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LABELS
    assert review.to_dict()["source_labels"] == list(prompt_review.labels)


def test_review_and_config_are_immutable_slotted_and_dict_lists_are_copied() -> None:
    review = _review()
    config = _config()

    assert not hasattr(review, "__dict__")
    assert not hasattr(config, "__dict__")

    with pytest.raises(FrozenInstanceError):
        review.status = "changed"
    with pytest.raises(FrozenInstanceError):
        config.additional_limitations = ("changed",)

    payload = review.to_dict()
    payload["labels"].append("changed")
    payload["source_labels"].append("changed")
    payload["source_prompt_review_source_labels"].append("changed")
    payload["limitations"].append("changed")
    payload["source_limitations"].append("changed")
    payload["source_blocking_reasons"].append("changed")
    payload["blocking_reasons"].append("changed")
    payload["required_future_operator_checks"].append("changed")

    assert "changed" not in review.labels
    assert "changed" not in review.source_labels
    assert "changed" not in review.source_prompt_review_source_labels
    assert "changed" not in review.limitations
    assert "changed" not in review.source_limitations
    assert "changed" not in review.source_blocking_reasons
    assert "changed" not in review.blocking_reasons
    assert "changed" not in review.required_future_operator_checks
    assert "changed" not in review.to_dict()["labels"]


def test_operator_review_dict_is_primitive_only() -> None:
    _assert_primitive_only(_review().to_dict())


def test_output_has_no_capital_mutation_or_runtime_fields() -> None:
    review = _review()
    payload = review.to_dict()
    payload_text = repr(payload).lower()

    for field in fields(EtfSmaPaperPreviewOperatorReview):
        lowered = field.name.lower()
        if lowered in _ALLOWED_SAFETY_FIELDS:
            continue
        assert "broker" not in lowered
        assert "submit" not in lowered
        assert all(term not in lowered for term in _FORBIDDEN_REAL_FIELD_TERMS)

    for key in _flatten_dict_keys(payload):
        lowered = key.lower()
        if lowered in _ALLOWED_SAFETY_FIELDS:
            continue
        assert "broker" not in lowered
        assert "submit" not in lowered
        assert all(term not in lowered for term in _FORBIDDEN_REAL_FIELD_TERMS)

    for phrase in _FORBIDDEN_REAL_FIELD_PHRASES:
        assert phrase not in payload_text
    assert "execution" + "intent" not in payload_text
    assert "execution" + "plan" not in payload_text


def test_future_template_contains_no_submit_flag_or_executable_command() -> None:
    template = _review().future_operator_review_template
    lowered = template.lower()

    for marker in _REQUIRED_TEMPLATE_MARKERS:
        assert marker in template

    assert all(pattern not in lowered for pattern in _FORBIDDEN_SUBMIT_FLAG_PATTERNS)
    assert all(pattern not in lowered for pattern in _FORBIDDEN_COMMAND_PATTERNS)


def test_operator_review_module_has_no_execution_intent_or_plan_reference() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source


def test_labels_limitations_and_checks_are_tuple_normalized() -> None:
    prompt_review = _ready_prompt_review()
    unsafe_review = _unsafe_prompt_review_with(
        prompt_review,
        labels=list(prompt_review.labels),
        source_labels=list(prompt_review.source_labels),
        limitations=list(prompt_review.limitations),
        blocking_reasons=[],
    )
    config = EtfSmaPaperPreviewOperatorReviewConfig(
        required_future_operator_checks=list(
            ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_REQUIRED_CHECKS
        ),
        additional_limitations=["manual_future_milestone_review_only"],
    )

    review = build_etf_sma_paper_preview_operator_review(unsafe_review, config)

    assert type(config.required_future_operator_checks) is tuple
    assert type(config.additional_limitations) is tuple
    assert type(review.source_labels) is tuple
    assert type(review.source_prompt_review_source_labels) is tuple
    assert type(review.labels) is tuple
    assert type(review.source_blocking_reasons) is tuple
    assert type(review.blocking_reasons) is tuple
    assert type(review.source_limitations) is tuple
    assert type(review.limitations) is tuple
    assert type(review.required_future_operator_checks) is tuple
    assert "manual_future_milestone_review_only" in review.limitations
    assert set(ETF_SMA_PAPER_PREVIEW_OPERATOR_REVIEW_LIMITATIONS).issubset(
        set(review.limitations)
    )


def test_operator_review_output_is_deterministic_from_same_input() -> None:
    prompt_review = _ready_prompt_review()
    config = _config()

    first = build_etf_sma_paper_preview_operator_review(prompt_review, config)
    second = build_etf_sma_paper_preview_operator_review(prompt_review, config)

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


def _config() -> EtfSmaPaperPreviewOperatorReviewConfig:
    return EtfSmaPaperPreviewOperatorReviewConfig()


def _review() -> EtfSmaPaperPreviewOperatorReview:
    return build_etf_sma_paper_preview_operator_review(
        _ready_prompt_review(),
        _config(),
    )


def _ready_prompt_review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(_ready_design(), _prompt_config())


def _insufficient_history_prompt_review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(
        _insufficient_history_design(),
        _prompt_config(),
    )


def _ready_design() -> object:
    return build_etf_sma_paper_preview_design(_ready_packet(), _design_config())


def _insufficient_history_design() -> object:
    return build_etf_sma_paper_preview_design(
        _insufficient_history_packet(),
        _design_config(),
    )


def _design_config() -> EtfSmaPaperPreviewDesignConfig:
    return EtfSmaPaperPreviewDesignConfig()


def _prompt_config() -> EtfSmaPaperPreviewPromptReviewConfig:
    return EtfSmaPaperPreviewPromptReviewConfig()


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


def _unsafe_prompt_review_with(
    prompt_review: EtfSmaPaperPreviewPromptReview,
    **changes: object,
) -> EtfSmaPaperPreviewPromptReview:
    clone = object.__new__(EtfSmaPaperPreviewPromptReview)
    for field in fields(EtfSmaPaperPreviewPromptReview):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(prompt_review, field.name)),
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
