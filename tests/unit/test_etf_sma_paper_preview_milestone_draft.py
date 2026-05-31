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
    EtfSmaPaperPreviewEvidencePacket,
    EtfSmaPaperPreviewEvidencePacketConfig,
    build_etf_sma_paper_preview_evidence_packet,
)
from algotrader.research.etf_sma_paper_preview_milestone_draft import (
    ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS,
    ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LIMITATIONS,
    ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_REQUIRED_FUTURE_PREREQUISITES,
    EtfSmaPaperPreviewMilestoneDraft,
    EtfSmaPaperPreviewMilestoneDraftConfig,
    build_etf_sma_paper_preview_milestone_draft,
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
    "src/algotrader/research/etf_sma_paper_preview_milestone_draft.py"
)
_AS_OF = "2026-01-05"
_STRATEGY_NAME = "SPY SMA paper preview milestone draft"
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
_REQUIRED_PREREQUISITES = {
    "commit_m343_before_any_future_milestone",
    "fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe",
    "explicit_operator_approval_required_before_any_broker_facing_preview",
    "market_hours_session_check_required_for_equities_before_any_broker_facing_preview",
    "stop_if_market_session_or_broker_behavior_is_ambiguous",
}
_REQUIRED_DRAFT_PHRASES = (
    "research_only",
    "paper_lab_candidate",
    "not_live_authorized",
    "profit_claim=none",
    "not execution authority",
    "not strategy validation",
    "not live authorization",
    "no broker command included",
    "no submit flag included",
    "normal pytest must remain offline, credential-free, deterministic, and safe",
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
    "curl ",
    "powershell ",
    "pwsh ",
)
_ALLOWED_SAFETY_FIELD_TERMS = {
    "broker_action_performed",
    "broker_preview_performed",
    "broker_facing",
    "source_broker_facing",
    "submit_allowed",
    "explicit_operator_approval_required_before_any_broker_facing_preview",
    "fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe",
    "market_hours_session_check_required_for_equities_before_any_broker_facing_preview",
    "stop_if_market_session_or_broker_behavior_is_ambiguous",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "alpaca",
    "broker_order",
    "credential",
    "execution_intent",
    "execution_plan",
    "fill",
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
    "algotrader.research.etf_sma_paper_preview_evidence_packet",
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


def test_ready_m342_packet_produces_ready_operator_review_draft() -> None:
    evidence_packet = _ready_evidence_packet()

    draft = build_etf_sma_paper_preview_milestone_draft(
        evidence_packet,
        _config(),
    )
    payload = draft.to_dict()

    assert draft.milestone_draft_version == (
        "etf_sma_paper_preview_milestone_draft_v1"
    )
    assert draft.draft_scope == "local_paper_preview_milestone_draft_only"
    assert draft.status == "ready_for_operator_review_of_paper_preview_milestone"
    assert draft.milestone_draft_status == draft.status
    assert draft.operator_review_of_paper_preview_milestone_ready is True
    assert draft.recommended_next_action == (
        "operator_review_m343_then_prepare_m344_fresh_read_only_snapshot"
    )
    assert draft.paper_preview_performed is False
    assert draft.broker_action_performed is False
    assert draft.broker_preview_performed is False
    assert draft.submit_allowed is False
    assert draft.executable is False
    assert draft.broker_facing is False
    assert draft.commit_m343_before_any_future_milestone is True
    assert (
        draft.fresh_read_only_paper_snapshot_required_before_any_broker_facing_preview_probe
        is True
    )
    assert (
        draft.explicit_operator_approval_required_before_any_broker_facing_preview
        is True
    )
    assert (
        draft.market_hours_session_check_required_for_equities_before_any_broker_facing_preview
        is True
    )
    assert draft.stop_if_market_session_or_broker_behavior_is_ambiguous is True
    assert draft.source_evidence_packet_status == (
        "ready_for_separate_paper_preview_preparation"
    )
    assert draft.source_evidence_packet_recommended_next_action == (
        "draft_separate_etf_sma_paper_preview_milestone"
    )
    assert draft.source_future_paper_preview_preparation_ready is True
    assert draft.source_broker_facing is False
    assert draft.source_executable is False
    assert draft.blocking_reasons == ()
    assert set(draft.labels) == _REQUIRED_LABELS
    assert set(draft.limitations).issuperset(
        set(ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LIMITATIONS)
    )
    assert set(draft.required_future_prerequisites).issuperset(
        _REQUIRED_PREREQUISITES
    )
    assert payload["strategy_total_return"] == "3"
    assert payload["benchmark_total_return"] == "7"
    assert payload["max_drawdown"] == "0"


def test_blocked_m342_packet_remains_blocked() -> None:
    evidence_packet = _insufficient_history_evidence_packet()

    draft = build_etf_sma_paper_preview_milestone_draft(
        evidence_packet,
        _config(),
    )

    assert draft.status == "blocked_from_operator_review_of_paper_preview_milestone"
    assert draft.operator_review_of_paper_preview_milestone_ready is False
    assert draft.recommended_next_action == "resolve_evidence_packet_blockers"
    assert draft.source_evidence_packet_status == (
        "blocked_from_separate_paper_preview_preparation"
    )
    assert draft.source_future_paper_preview_preparation_ready is False
    assert "source_evidence_packet_not_ready" in draft.blocking_reasons
    assert "source_evidence_packet_status_not_ready" in draft.blocking_reasons
    assert (
        "source_future_paper_preview_preparation_not_ready"
        in draft.blocking_reasons
    )
    assert "source_insufficient_history_posture" in draft.blocking_reasons
    assert "candidate_insufficient_history" in draft.source_blocking_reasons


def test_broker_facing_or_executable_m342_packet_is_blocked() -> None:
    evidence_packet = _ready_evidence_packet()
    broker_facing_packet = _unsafe_packet_with(evidence_packet, broker_facing=True)
    executable_packet = _unsafe_packet_with(evidence_packet, executable=True)

    broker_facing_draft = build_etf_sma_paper_preview_milestone_draft(
        broker_facing_packet,
        _config(),
    )
    executable_draft = build_etf_sma_paper_preview_milestone_draft(
        executable_packet,
        _config(),
    )

    assert broker_facing_draft.status == (
        "blocked_from_operator_review_of_paper_preview_milestone"
    )
    assert "source_broker_facing_not_false" in broker_facing_draft.blocking_reasons
    assert broker_facing_draft.broker_facing is False
    assert executable_draft.status == (
        "blocked_from_operator_review_of_paper_preview_milestone"
    )
    assert "source_executable_not_false" in executable_draft.blocking_reasons
    assert executable_draft.executable is False


@pytest.mark.parametrize(
    ("flag_name", "expected_reason"),
    (
        ("authorize_paper_preview_now", "source_authorize_paper_preview_now_not_false"),
        ("authorize_broker_action", "source_authorize_broker_action_not_false"),
        ("broker_action_performed", "source_broker_action_performed_not_false"),
        ("broker_preview_performed", "source_broker_preview_performed_not_false"),
        ("submit_allowed", "source_submit_allowed_not_false"),
    ),
)
def test_any_true_broker_or_submit_action_flag_is_blocked(
    flag_name: str,
    expected_reason: str,
) -> None:
    evidence_packet = _unsafe_packet_with(_ready_evidence_packet(), **{flag_name: True})

    draft = build_etf_sma_paper_preview_milestone_draft(
        evidence_packet,
        _config(),
    )

    assert draft.status == "blocked_from_operator_review_of_paper_preview_milestone"
    assert expected_reason in draft.blocking_reasons
    assert draft.paper_preview_performed is False
    assert draft.broker_action_performed is False
    assert draft.broker_preview_performed is False
    assert draft.submit_allowed is False


def test_live_authorization_label_or_status_is_blocked() -> None:
    evidence_packet = _ready_evidence_packet()
    unsafe_label_packet = _unsafe_packet_with(
        evidence_packet,
        source_labels=(*evidence_packet.source_labels, "live_authorized"),
    )
    unsafe_status_packet = _unsafe_packet_with(
        evidence_packet,
        status="live_authorized",
        evidence_packet_status="live_authorized",
    )

    label_draft = build_etf_sma_paper_preview_milestone_draft(
        unsafe_label_packet,
        _config(),
    )
    status_draft = build_etf_sma_paper_preview_milestone_draft(
        unsafe_status_packet,
        _config(),
    )

    assert label_draft.status == (
        "blocked_from_operator_review_of_paper_preview_milestone"
    )
    assert "source_contains_live_authorized" in label_draft.blocking_reasons
    assert "live_authorized" in label_draft.source_labels
    assert status_draft.status == (
        "blocked_from_operator_review_of_paper_preview_milestone"
    )
    assert "source_contains_live_authorized" in status_draft.blocking_reasons


def test_non_none_profit_claim_is_blocked() -> None:
    evidence_packet = _ready_evidence_packet()
    unsafe_packet = _unsafe_packet_with(
        evidence_packet,
        upstream_labels=(*evidence_packet.upstream_labels, "profit_claim=positive"),
    )

    draft = build_etf_sma_paper_preview_milestone_draft(
        unsafe_packet,
        _config(),
    )

    assert draft.status == "blocked_from_operator_review_of_paper_preview_milestone"
    assert "source_contains_profit_claim_other_than_none" in draft.blocking_reasons
    assert "profit_claim=positive" in draft.upstream_labels
    assert "profit_claim=none" in draft.labels


def test_missing_paper_lab_candidate_is_blocked() -> None:
    evidence_packet = _ready_evidence_packet()
    unsafe_packet = _unsafe_packet_with(
        evidence_packet,
        source_labels=tuple(
            label
            for label in evidence_packet.source_labels
            if label != "paper_lab_candidate"
        ),
    )

    draft = build_etf_sma_paper_preview_milestone_draft(
        unsafe_packet,
        _config(),
    )

    assert draft.status == "blocked_from_operator_review_of_paper_preview_milestone"
    assert "paper_lab_candidate" not in draft.source_labels
    assert "source_missing_paper_lab_candidate_label" in draft.blocking_reasons


def test_source_and_upstream_labels_are_preserved_exactly() -> None:
    evidence_packet = _ready_evidence_packet()

    draft = build_etf_sma_paper_preview_milestone_draft(
        evidence_packet,
        _config(),
    )

    assert draft.source_evidence_packet_labels == evidence_packet.labels
    assert (
        draft.source_operator_review_labels
        == evidence_packet.source_operator_review_labels
    )
    assert draft.source_labels == evidence_packet.source_labels
    assert draft.upstream_labels == evidence_packet.upstream_labels
    assert draft.labels == ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_LABELS
    assert draft.to_dict()["source_labels"] == list(evidence_packet.source_labels)
    assert draft.to_dict()["upstream_labels"] == list(evidence_packet.upstream_labels)


def test_return_drawdown_and_count_metadata_are_preserved() -> None:
    evidence_packet = _ready_evidence_packet()

    draft = build_etf_sma_paper_preview_milestone_draft(
        evidence_packet,
        _config(),
    )

    assert draft.symbol == evidence_packet.symbol
    assert draft.strategy_name == _STRATEGY_NAME
    assert draft.as_of == evidence_packet.as_of
    assert draft.latest_posture == evidence_packet.latest_posture
    assert draft.strategy_total_return == Decimal("3")
    assert draft.strategy_total_return == evidence_packet.strategy_total_return
    assert draft.benchmark_total_return == Decimal("7")
    assert draft.benchmark_total_return == evidence_packet.benchmark_total_return
    assert draft.max_drawdown == Decimal("0")
    assert draft.max_drawdown == evidence_packet.max_drawdown
    assert draft.bar_count == 5
    assert draft.signal_count == 3
    assert draft.exposure_count == 2
    assert draft.defensive_count == 3
    assert draft.posture_change_count == 1


def test_draft_text_includes_required_prerequisites_and_safety_posture() -> None:
    draft = _draft()
    lowered = draft.draft_milestone_outline.lower()

    assert set(draft.required_future_prerequisites).issuperset(
        set(ETF_SMA_PAPER_PREVIEW_MILESTONE_DRAFT_REQUIRED_FUTURE_PREREQUISITES)
    )
    for phrase in _REQUIRED_DRAFT_PHRASES:
        assert phrase in lowered
    assert "confirm m343 is committed before any future milestone" in lowered
    assert "fresh read-only paper snapshot" in lowered
    assert "explicit operator approval before any broker-facing preview" in lowered
    assert "market-hours/session check for equities" in lowered
    assert "stop if market/session/broker behavior is ambiguous" in lowered


def test_draft_text_contains_no_submit_flag_or_executable_broker_command() -> None:
    outline = _draft().draft_milestone_outline
    lowered = outline.lower()

    assert all(pattern not in lowered for pattern in _FORBIDDEN_SUBMIT_FLAG_PATTERNS)
    assert all(pattern not in lowered for pattern in _FORBIDDEN_COMMAND_PATTERNS)


def test_draft_and_config_are_immutable_slotted_and_dict_lists_are_copied() -> None:
    draft = _draft()
    config = _config()

    assert not hasattr(draft, "__dict__")
    assert not hasattr(config, "__dict__")

    with pytest.raises(FrozenInstanceError):
        draft.status = "changed"
    with pytest.raises(FrozenInstanceError):
        config.additional_limitations = ("changed",)

    payload = draft.to_dict()
    payload["labels"].append("changed")
    payload["source_evidence_packet_labels"].append("changed")
    payload["source_operator_review_labels"].append("changed")
    payload["source_labels"].append("changed")
    payload["upstream_labels"].append("changed")
    payload["limitations"].append("changed")
    payload["source_evidence_packet_limitations"].append("changed")
    payload["source_operator_review_limitations"].append("changed")
    payload["source_limitations"].append("changed")
    payload["source_evidence_packet_blocking_reasons"].append("changed")
    payload["source_operator_review_blocking_reasons"].append("changed")
    payload["source_blocking_reasons"].append("changed")
    payload["blocking_reasons"].append("changed")
    payload["required_future_prerequisites"].append("changed")

    assert "changed" not in draft.labels
    assert "changed" not in draft.source_evidence_packet_labels
    assert "changed" not in draft.source_operator_review_labels
    assert "changed" not in draft.source_labels
    assert "changed" not in draft.upstream_labels
    assert "changed" not in draft.limitations
    assert "changed" not in draft.source_evidence_packet_limitations
    assert "changed" not in draft.source_operator_review_limitations
    assert "changed" not in draft.source_limitations
    assert "changed" not in draft.source_evidence_packet_blocking_reasons
    assert "changed" not in draft.source_operator_review_blocking_reasons
    assert "changed" not in draft.source_blocking_reasons
    assert "changed" not in draft.blocking_reasons
    assert "changed" not in draft.required_future_prerequisites
    assert "changed" not in draft.to_dict()["labels"]


def test_milestone_draft_dict_is_primitive_only() -> None:
    _assert_primitive_only(_draft().to_dict())


def test_output_contains_no_forbidden_mutation_or_runtime_fields() -> None:
    draft = _draft()
    payload = draft.to_dict()
    payload_text = repr(payload).lower()

    for field in fields(EtfSmaPaperPreviewMilestoneDraft):
        lowered = field.name.lower()
        if lowered in _ALLOWED_SAFETY_FIELD_TERMS:
            continue
        assert "broker_order" not in lowered
        assert "submit" not in lowered
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    for key in _flatten_dict_keys(payload):
        lowered = key.lower()
        if lowered in _ALLOWED_SAFETY_FIELD_TERMS:
            continue
        assert "broker_order" not in lowered
        assert "submit" not in lowered
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    assert "alpaca" not in payload_text
    assert "execution" + "intent" not in payload_text
    assert "execution" + "plan" not in payload_text


def test_milestone_draft_output_is_deterministic_from_same_input() -> None:
    evidence_packet = _ready_evidence_packet()
    config = _config()

    first = build_etf_sma_paper_preview_milestone_draft(evidence_packet, config)
    second = build_etf_sma_paper_preview_milestone_draft(evidence_packet, config)

    assert first == second
    assert first.to_dict() == second.to_dict()


def test_milestone_draft_module_has_no_execution_intent_or_plan_reference() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
        "Alpaca",
    ):
        assert forbidden not in source


def test_no_network_or_sdk_imports_are_introduced() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _config() -> EtfSmaPaperPreviewMilestoneDraftConfig:
    return EtfSmaPaperPreviewMilestoneDraftConfig()


def _draft() -> EtfSmaPaperPreviewMilestoneDraft:
    return build_etf_sma_paper_preview_milestone_draft(
        _ready_evidence_packet(),
        _config(),
    )


def _ready_evidence_packet() -> EtfSmaPaperPreviewEvidencePacket:
    return build_etf_sma_paper_preview_evidence_packet(
        _ready_operator_review(),
        _evidence_config(),
    )


def _insufficient_history_evidence_packet() -> EtfSmaPaperPreviewEvidencePacket:
    return build_etf_sma_paper_preview_evidence_packet(
        _insufficient_history_operator_review(),
        _evidence_config(),
    )


def _evidence_config() -> EtfSmaPaperPreviewEvidencePacketConfig:
    return EtfSmaPaperPreviewEvidencePacketConfig()


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


def _operator_review_config() -> EtfSmaPaperPreviewOperatorReviewConfig:
    return EtfSmaPaperPreviewOperatorReviewConfig()


def _ready_prompt_review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(_ready_design(), _prompt_config())


def _insufficient_history_prompt_review() -> EtfSmaPaperPreviewPromptReview:
    return build_etf_sma_paper_preview_prompt_review(
        _insufficient_history_design(),
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
    evidence_packet: EtfSmaPaperPreviewEvidencePacket,
    **changes: object,
) -> EtfSmaPaperPreviewEvidencePacket:
    clone = object.__new__(EtfSmaPaperPreviewEvidencePacket)
    for field in fields(EtfSmaPaperPreviewEvidencePacket):
        object.__setattr__(
            clone,
            field.name,
            changes.get(field.name, getattr(evidence_packet, field.name)),
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
