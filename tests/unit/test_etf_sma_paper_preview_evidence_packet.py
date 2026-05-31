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
from algotrader.research.etf_sma_paper_preview_evidence_packet import (
    ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS,
    ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LIMITATIONS,
    ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_REQUIRED_FUTURE_PREREQUISITES,
    EtfSmaPaperPreviewEvidencePacket,
    EtfSmaPaperPreviewEvidencePacketConfig,
    build_etf_sma_paper_preview_evidence_packet,
)
from algotrader.research.etf_sma_paper_preview_operator_review import (
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


MODULE_PATH = Path(
    "src/algotrader/research/etf_sma_paper_preview_evidence_packet.py"
)
_AS_OF = "2026-01-05"
_STRATEGY_NAME = "SPY SMA paper preview evidence packet"
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
    "local_advisory_evidence_only",
    "not_live_authorized",
    "not_profit_evidence",
    "not_strategy_validation",
    "not_execution_authority",
    "not_broker_order_fill_account_portfolio_evidence",
    "paper_preview_requires_separate_milestone",
    "broker_facing_preview_requires_separate_milestone",
    "submit_requires_separate_explicit_milestone",
}
_REQUIRED_PREREQUISITES = {
    "manual_operator_review_required",
    "fresh_read_only_paper_snapshot_required",
    "separate_paper_preview_milestone_required",
    "explicit_operator_approval_required_before_any_broker_facing_preview",
}
_REQUIRED_TEMPLATE_MARKERS = (
    "<SEPARATE_PAPER_PREVIEW_MILESTONE_REQUIRED>",
    "<MANUAL_OPERATOR_REVIEW_REQUIRED>",
    "<FRESH_READ_ONLY_PAPER_SNAPSHOT_REQUIRED>",
    "<EXPLICIT_OPERATOR_APPROVAL_REQUIRED>",
    "<BROKER_FACING_PREVIEW_NOT_INCLUDED>",
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
_ALLOWED_FORBIDDEN_TERM_FIELDS = {
    "broker_facing",
    "authorize_broker_action",
    "broker_action_performed",
    "broker_preview_performed",
    "submit_allowed",
    "explicit_operator_approval_required_before_any_broker_facing_preview",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "alpaca",
    "credential",
    "execution_intent",
    "execution_plan",
    "fill",
    "live",
    "order",
    "portfolio",
    "quantity",
)
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
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
    "algotrader.research.etf_sma_paper_preview_operator_review",
}
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


def test_ready_m341_review_produces_ready_preparation_packet() -> None:
    operator_review = _ready_operator_review()

    packet = build_etf_sma_paper_preview_evidence_packet(
        operator_review,
        _config(),
    )
    payload = packet.to_dict()

    assert packet.evidence_packet_version == (
        "etf_sma_paper_preview_evidence_packet_v1"
    )
    assert packet.evidence_scope == (
        "local_research_to_paper_preview_preparation_only"
    )
    assert packet.status == "ready_for_separate_paper_preview_preparation"
    assert packet.evidence_packet_status == packet.status
    assert packet.future_paper_preview_preparation_ready is True
    assert packet.recommended_next_action == (
        "draft_separate_etf_sma_paper_preview_milestone"
    )
    assert packet.broker_facing is False
    assert packet.executable is False
    assert packet.authorize_paper_preview_now is False
    assert packet.authorize_broker_action is False
    assert packet.broker_action_performed is False
    assert packet.broker_preview_performed is False
    assert packet.submit_allowed is False
    assert packet.manual_operator_review_required is True
    assert packet.fresh_read_only_paper_snapshot_required is True
    assert packet.separate_paper_preview_milestone_required is True
    assert (
        packet.explicit_operator_approval_required_before_any_broker_facing_preview
        is True
    )
    assert packet.source_operator_review_status == (
        "authorize_separate_paper_preview_milestone"
    )
    assert packet.source_operator_review_required_next_action == (
        "prepare_separate_etf_sma_paper_preview_milestone"
    )
    assert packet.source_operator_review_ready is True
    assert packet.blocking_reasons == ()
    assert set(packet.labels) == _REQUIRED_LABELS
    assert set(packet.limitations).issuperset(_REQUIRED_LIMITATIONS)
    assert set(packet.required_future_prerequisites).issuperset(
        _REQUIRED_PREREQUISITES
    )
    assert payload["strategy_total_return"] == "3"
    assert payload["benchmark_total_return"] == "7"
    assert payload["max_drawdown"] == "0"


def test_blocked_m341_review_remains_blocked() -> None:
    operator_review = _insufficient_history_operator_review()

    packet = build_etf_sma_paper_preview_evidence_packet(
        operator_review,
        _config(),
    )

    assert packet.status == "blocked_from_separate_paper_preview_preparation"
    assert packet.future_paper_preview_preparation_ready is False
    assert packet.recommended_next_action == "resolve_operator_review_blockers"
    assert packet.source_operator_review_status == (
        "blocked_from_separate_paper_preview_milestone"
    )
    assert packet.source_operator_review_ready is False
    assert "source_operator_review_not_ready" in packet.blocking_reasons
    assert "source_operator_review_readiness_false" in packet.blocking_reasons
    assert "source_insufficient_history_posture" in packet.blocking_reasons


def test_live_authorized_label_or_status_blocks_packet() -> None:
    operator_review = _ready_operator_review()
    unsafe_label_review = _unsafe_operator_review_with(
        operator_review,
        source_labels=(*operator_review.source_labels, "live_authorized"),
    )
    unsafe_status_review = _unsafe_operator_review_with(
        operator_review,
        status="live_authorized",
        operator_review_status="live_authorized",
    )

    label_packet = build_etf_sma_paper_preview_evidence_packet(
        unsafe_label_review,
        _config(),
    )
    status_packet = build_etf_sma_paper_preview_evidence_packet(
        unsafe_status_review,
        _config(),
    )

    assert label_packet.status == "blocked_from_separate_paper_preview_preparation"
    assert "live_authorized" in label_packet.source_labels
    assert "source_contains_live_authorized" in label_packet.blocking_reasons
    assert status_packet.status == "blocked_from_separate_paper_preview_preparation"
    assert "source_contains_live_authorized" in status_packet.blocking_reasons


def test_non_none_profit_claim_blocks_packet() -> None:
    operator_review = _ready_operator_review()
    unsafe_review = _unsafe_operator_review_with(
        operator_review,
        upstream_labels=(),
        source_prompt_review_source_labels=(
            *operator_review.source_prompt_review_source_labels,
            "profit_claim=positive",
        ),
    )

    packet = build_etf_sma_paper_preview_evidence_packet(unsafe_review, _config())

    assert packet.status == "blocked_from_separate_paper_preview_preparation"
    assert "source_contains_profit_claim_other_than_none" in packet.blocking_reasons
    assert "profit_claim=positive" in packet.upstream_labels
    assert "profit_claim=none" in packet.labels


def test_missing_paper_lab_candidate_blocks_packet() -> None:
    operator_review = _ready_operator_review()
    unsafe_review = _unsafe_operator_review_with(
        operator_review,
        source_labels=tuple(
            label
            for label in operator_review.source_labels
            if label != "paper_lab_candidate"
        ),
    )

    packet = build_etf_sma_paper_preview_evidence_packet(unsafe_review, _config())

    assert packet.status == "blocked_from_separate_paper_preview_preparation"
    assert "paper_lab_candidate" not in packet.source_labels
    assert "source_missing_paper_lab_candidate_label" in packet.blocking_reasons


def test_source_blockers_are_preserved_and_block_readiness() -> None:
    operator_review = _insufficient_history_operator_review()

    packet = build_etf_sma_paper_preview_evidence_packet(
        operator_review,
        _config(),
    )

    assert packet.source_operator_review_blocking_reasons == (
        operator_review.blocking_reasons
    )
    assert packet.source_blocking_reasons == operator_review.source_blocking_reasons
    assert "candidate_insufficient_history" in packet.source_blocking_reasons
    assert "candidate_insufficient_history" in packet.blocking_reasons
    assert packet.future_paper_preview_preparation_ready is False


def test_insufficient_history_blocks_readiness() -> None:
    packet = build_etf_sma_paper_preview_evidence_packet(
        _insufficient_history_operator_review(),
        _config(),
    )

    assert packet.latest_posture == "insufficient_history"
    assert "source_insufficient_history_posture" in packet.blocking_reasons
    assert packet.status == "blocked_from_separate_paper_preview_preparation"


def test_defensive_posture_blocks_readiness() -> None:
    packet = build_etf_sma_paper_preview_evidence_packet(
        _defensive_operator_review(),
        _config(),
    )

    assert packet.latest_posture == "defensive_or_cash_candidate"
    assert "source_defensive_posture" in packet.blocking_reasons
    assert packet.status == "blocked_from_separate_paper_preview_preparation"


def test_source_and_upstream_labels_are_preserved_exactly() -> None:
    operator_review = _ready_operator_review()

    packet = build_etf_sma_paper_preview_evidence_packet(
        operator_review,
        _config(),
    )

    assert packet.source_operator_review_labels == operator_review.labels
    assert packet.source_labels == operator_review.source_labels
    assert packet.upstream_labels == operator_review.source_prompt_review_source_labels
    assert packet.labels == ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LABELS
    assert packet.to_dict()["source_labels"] == list(operator_review.source_labels)
    assert packet.to_dict()["upstream_labels"] == list(
        operator_review.source_prompt_review_source_labels
    )


def test_return_drawdown_and_count_metadata_are_preserved() -> None:
    operator_review = _ready_operator_review()

    packet = build_etf_sma_paper_preview_evidence_packet(
        operator_review,
        _config(),
    )

    assert packet.symbol == operator_review.symbol
    assert packet.strategy_name == _STRATEGY_NAME
    assert packet.as_of == operator_review.as_of
    assert packet.latest_posture == operator_review.latest_posture
    assert packet.strategy_total_return == Decimal("3")
    assert packet.strategy_total_return == operator_review.strategy_total_return
    assert packet.benchmark_total_return == Decimal("7")
    assert packet.benchmark_total_return == operator_review.benchmark_total_return
    assert packet.max_drawdown == Decimal("0")
    assert packet.max_drawdown == operator_review.max_drawdown
    assert packet.bar_count == 5
    assert packet.signal_count == 3
    assert packet.exposure_count == 2
    assert packet.defensive_count == 3
    assert packet.posture_change_count == 1


def test_packet_and_config_are_immutable_slotted_and_dict_lists_are_copied() -> None:
    packet = _packet()
    config = _config()

    assert not hasattr(packet, "__dict__")
    assert not hasattr(config, "__dict__")

    with pytest.raises(FrozenInstanceError):
        packet.status = "changed"
    with pytest.raises(FrozenInstanceError):
        config.additional_limitations = ("changed",)

    payload = packet.to_dict()
    payload["labels"].append("changed")
    payload["source_labels"].append("changed")
    payload["upstream_labels"].append("changed")
    payload["limitations"].append("changed")
    payload["source_limitations"].append("changed")
    payload["source_operator_review_limitations"].append("changed")
    payload["source_blocking_reasons"].append("changed")
    payload["source_operator_review_blocking_reasons"].append("changed")
    payload["blocking_reasons"].append("changed")
    payload["required_future_prerequisites"].append("changed")

    assert "changed" not in packet.labels
    assert "changed" not in packet.source_labels
    assert "changed" not in packet.upstream_labels
    assert "changed" not in packet.limitations
    assert "changed" not in packet.source_limitations
    assert "changed" not in packet.source_operator_review_limitations
    assert "changed" not in packet.source_blocking_reasons
    assert "changed" not in packet.source_operator_review_blocking_reasons
    assert "changed" not in packet.blocking_reasons
    assert "changed" not in packet.required_future_prerequisites
    assert "changed" not in packet.to_dict()["labels"]


def test_evidence_packet_dict_is_primitive_only() -> None:
    _assert_primitive_only(_packet().to_dict())


def test_output_has_no_forbidden_runtime_or_mutation_fields() -> None:
    packet = _packet()
    payload = packet.to_dict()
    payload_text = repr(payload).lower()

    for field in fields(EtfSmaPaperPreviewEvidencePacket):
        lowered = field.name.lower()
        if lowered in _ALLOWED_FORBIDDEN_TERM_FIELDS:
            continue
        assert "broker" not in lowered
        assert "submit" not in lowered
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    for key in _flatten_dict_keys(payload):
        lowered = key.lower()
        if lowered in _ALLOWED_FORBIDDEN_TERM_FIELDS:
            continue
        assert "broker" not in lowered
        assert "submit" not in lowered
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    assert "alpaca" not in payload_text
    assert "credential" not in payload_text
    assert "execution" + "intent" not in payload_text
    assert "execution" + "plan" not in payload_text


def test_future_template_contains_no_submit_flag_or_executable_command() -> None:
    template = _packet().future_preparation_template
    lowered = template.lower()

    for marker in _REQUIRED_TEMPLATE_MARKERS:
        assert marker in template

    assert all(pattern not in lowered for pattern in _FORBIDDEN_SUBMIT_FLAG_PATTERNS)
    assert all(pattern not in lowered for pattern in _FORBIDDEN_COMMAND_PATTERNS)


def test_labels_limitations_prerequisites_and_blockers_are_tuple_normalized() -> None:
    operator_review = _ready_operator_review()
    unsafe_review = _unsafe_operator_review_with(
        operator_review,
        labels=list(operator_review.labels),
        source_labels=list(operator_review.source_labels),
        source_prompt_review_source_labels=list(
            operator_review.source_prompt_review_source_labels
        ),
        source_limitations=list(operator_review.source_limitations),
        limitations=list(operator_review.limitations),
        source_blocking_reasons=[],
        blocking_reasons=[],
    )
    config = EtfSmaPaperPreviewEvidencePacketConfig(
        required_future_prerequisites=list(
            ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_REQUIRED_FUTURE_PREREQUISITES
        ),
        additional_limitations=["manual_future_preparation_review_only"],
    )

    packet = build_etf_sma_paper_preview_evidence_packet(unsafe_review, config)

    assert type(config.required_future_prerequisites) is tuple
    assert type(config.additional_limitations) is tuple
    assert type(packet.source_operator_review_labels) is tuple
    assert type(packet.source_labels) is tuple
    assert type(packet.upstream_labels) is tuple
    assert type(packet.labels) is tuple
    assert type(packet.source_operator_review_blocking_reasons) is tuple
    assert type(packet.source_blocking_reasons) is tuple
    assert type(packet.blocking_reasons) is tuple
    assert type(packet.source_operator_review_limitations) is tuple
    assert type(packet.source_limitations) is tuple
    assert type(packet.limitations) is tuple
    assert type(packet.required_future_prerequisites) is tuple
    assert "manual_future_preparation_review_only" in packet.limitations
    assert set(ETF_SMA_PAPER_PREVIEW_EVIDENCE_PACKET_LIMITATIONS).issubset(
        set(packet.limitations)
    )


def test_evidence_packet_output_is_deterministic_from_same_input() -> None:
    operator_review = _ready_operator_review()
    config = _config()

    first = build_etf_sma_paper_preview_evidence_packet(operator_review, config)
    second = build_etf_sma_paper_preview_evidence_packet(operator_review, config)

    assert first == second
    assert first.to_dict() == second.to_dict()


def test_evidence_packet_module_has_no_execution_intent_or_plan_reference() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
        "Alpaca",
    ):
        assert forbidden not in source


def test_dependency_direction_remains_clean() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _config() -> EtfSmaPaperPreviewEvidencePacketConfig:
    return EtfSmaPaperPreviewEvidencePacketConfig()


def _packet() -> EtfSmaPaperPreviewEvidencePacket:
    return build_etf_sma_paper_preview_evidence_packet(
        _ready_operator_review(),
        _config(),
    )


def _ready_operator_review() -> EtfSmaPaperPreviewOperatorReview:
    return build_etf_sma_paper_preview_operator_review(
        _ready_prompt_review(),
        _operator_review_config(),
    )


def _insufficient_history_operator_review() -> EtfSmaPaperPreviewOperatorReview:
    return build_etf_sma_paper_preview_operator_review(
        _insufficient_history_prompt_review(),
        _operator_review_config(),
    )


def _defensive_operator_review() -> EtfSmaPaperPreviewOperatorReview:
    return build_etf_sma_paper_preview_operator_review(
        _defensive_prompt_review(),
        _operator_review_config(),
    )


def _operator_review_config() -> EtfSmaPaperPreviewOperatorReviewConfig:
    return EtfSmaPaperPreviewOperatorReviewConfig()


def _ready_prompt_review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(_ready_design(), _prompt_config())


def _insufficient_history_prompt_review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(
        _insufficient_history_design(),
        _prompt_config(),
    )


def _defensive_prompt_review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(
        _defensive_design(),
        _prompt_config(),
    )


def _prompt_config() -> EtfSmaPaperPreviewPromptReviewConfig:
    return EtfSmaPaperPreviewPromptReviewConfig()


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


def _unsafe_operator_review_with(
    operator_review: EtfSmaPaperPreviewOperatorReview,
    **changes: object,
) -> EtfSmaPaperPreviewOperatorReview:
    clone = object.__new__(EtfSmaPaperPreviewOperatorReview)
    for field in fields(EtfSmaPaperPreviewOperatorReview):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(operator_review, field.name)),
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
