from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.etf_sma_paper_experiment_plan import (
    ETF_SMA_PAPER_EXPERIMENT_PLAN_LABELS,
    EtfSmaPaperExperimentPlanConfig,
    draft_etf_sma_paper_experiment_plan,
)
from algotrader.research.etf_sma_research_candidate import (
    SmaCandidateConfig,
    SmaCandidateInputBar,
    SmaResearchToPaperCandidate,
    build_etf_sma_research_candidate,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_paper_experiment_plan.py")
_CONFIG = SmaCandidateConfig(
    symbol="SPY",
    strategy_name="SPY SMA paper-lab experiment candidate",
    short_window=2,
    long_window=4,
)
_PLAN_CONFIG = EtfSmaPaperExperimentPlanConfig(
    proposed_cap_policy="metadata_only_notional_cap: USD 25; review-only cap"
)
_REQUIRED_LABELS = {
    "research_only",
    "paper_lab_candidate",
    "not_live_authorized",
    "profit_claim=none",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "broker",
    "credential",
    "execution_intent",
    "execution_plan",
    "fill",
    "order",
    "portfolio",
    "mutation",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
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
    "numpy",
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
    "urlopen",
    "write",
}


def test_bullish_candidate_produces_review_only_long_bias_plan() -> None:
    candidate = _candidate(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "20"),
    )

    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)

    assert plan.intended_paper_action_posture == "candidate_long_bias"
    assert plan.latest_close == Decimal("20")
    assert plan.short_sma == Decimal("20")
    assert plan.long_sma == Decimal("15")
    assert plan.to_dict() == {
        "plan_type": "etf_sma_paper_experiment_plan",
        "experiment_status": "paper_experiment_plan_drafted",
        "review_status": "requires_operator_review",
        "authorization_status": "not_broker_authorized",
        "symbol": "SPY",
        "strategy_name": "SPY SMA paper-lab experiment candidate",
        "as_of": "2026-01-04",
        "short_window": 2,
        "long_window": 4,
        "latest_close": "20",
        "short_sma": "20",
        "long_sma": "15",
        "candidate_posture": "bullish_trend_candidate",
        "intended_paper_action_posture": "candidate_long_bias",
        "proposed_cap_policy": "metadata_only_notional_cap: USD 25; review-only cap",
        "required_pre_submit_checks": list(
            _PLAN_CONFIG.required_pre_submit_checks
        ),
        "paper_lab_safeguards": [
            "fresh read-only snapshot required before any future submit",
            "max one broker action per approved future probe",
            "post-action read-only snapshot required",
            "ambiguous broker response means stop",
            "no retry/cancel/liquidate/close/fix-forward without separate milestone",
        ],
        "limitations": [
            "offline deterministic candidate from caller-supplied local bars",
            "not approved for paper-lab submission",
            "no live authorization",
            "no profitability or edge claim",
            "separate paper-lab experiment plan required before any submission review",
            "review-only paper-lab experiment plan; no capital authority",
            "no paper or live authorization",
            "proposed cap policy is metadata only and not executable",
            "separate preview/checklist milestone required before any paper probe",
        ],
        "labels": list(ETF_SMA_PAPER_EXPERIMENT_PLAN_LABELS),
        "source_candidate_type": "etf_sma_research_to_paper_candidate",
        "source_candidate_status": "research_candidate_only",
        "source_candidate_eligibility_status": (
            "separate_plan_required_before_paper_experiment"
        ),
        "next_operator_action": (
            "review_plan_before_separate_preview_or_paper_probe_milestone"
        ),
    }


def test_defensive_candidate_produces_review_only_defensive_plan() -> None:
    candidate = _candidate(
        ("2026-01-01", "20"),
        ("2026-01-02", "20"),
        ("2026-01-03", "10"),
        ("2026-01-04", "10"),
    )

    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)

    assert candidate.posture == "defensive_or_cash_candidate"
    assert plan.intended_paper_action_posture == "candidate_defensive_bias"
    assert plan.authorization_status == "not_broker_authorized"
    assert plan.review_status == "requires_operator_review"


def test_insufficient_history_candidate_is_observe_only() -> None:
    candidate = _candidate(("2026-01-01", "10"), ("2026-01-02", "11"))

    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)

    assert candidate.posture == "insufficient_history"
    assert plan.intended_paper_action_posture == "observe_only"
    assert plan.long_sma is None
    assert plan.to_dict()["long_sma"] is None
    assert any("insufficient history candidate is observe-only" in item for item in plan.limitations)


def test_missing_paper_lab_candidate_label_is_rejected() -> None:
    candidate = _candidate(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "20"),
    )
    unsafe_candidate = _unsafe_candidate_with(
        candidate,
        labels=(
            "research_only",
            "not_live_authorized",
            "profit_claim=none",
        ),
    )

    with pytest.raises(ValueError, match="paper_lab_candidate"):
        draft_etf_sma_paper_experiment_plan(unsafe_candidate, _PLAN_CONFIG)


def test_live_authorized_label_or_status_is_rejected() -> None:
    candidate = _candidate(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "20"),
    )
    live_label_candidate = _unsafe_candidate_with(
        candidate,
        labels=(
            "research_only",
            "paper_lab_candidate",
            "live_authorized",
            "profit_claim=none",
        ),
    )
    live_status_candidate = _unsafe_candidate_with(
        candidate,
        status="live_authorized",
    )

    with pytest.raises(ValueError, match="live authorized"):
        draft_etf_sma_paper_experiment_plan(live_label_candidate, _PLAN_CONFIG)
    with pytest.raises(ValueError, match="live authorized"):
        draft_etf_sma_paper_experiment_plan(live_status_candidate, _PLAN_CONFIG)


def test_labels_are_preserved_from_candidate_to_plan() -> None:
    candidate = _candidate(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "20"),
    )

    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)

    assert set(plan.labels) == _REQUIRED_LABELS
    assert plan.labels == candidate.labels
    assert plan.to_dict()["labels"] == list(candidate.labels)


def test_plan_and_config_outputs_are_immutable_and_dict_lists_are_copied() -> None:
    candidate = _candidate(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "20"),
    )
    plan = draft_etf_sma_paper_experiment_plan(candidate, _PLAN_CONFIG)

    with pytest.raises(FrozenInstanceError):
        plan.review_status = "changed"
    with pytest.raises(FrozenInstanceError):
        _PLAN_CONFIG.proposed_cap_policy = "changed"

    payload = plan.to_dict()
    payload["labels"].append("changed")
    payload["paper_lab_safeguards"].append("changed")
    config_payload = _PLAN_CONFIG.to_dict()
    config_payload["required_pre_submit_checks"].append("changed")

    assert "changed" not in plan.labels
    assert "changed" not in plan.paper_lab_safeguards
    assert "changed" not in plan.to_dict()["labels"]
    assert "changed" not in plan.to_dict()["paper_lab_safeguards"]
    assert "changed" not in _PLAN_CONFIG.required_pre_submit_checks


def test_plan_dict_is_primitive_only() -> None:
    plan = draft_etf_sma_paper_experiment_plan(
        _candidate(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "20"),
        ),
        _PLAN_CONFIG,
    )

    _assert_primitive_only(plan.to_dict())
    _assert_primitive_only(_PLAN_CONFIG.to_dict())


def test_plan_output_has_no_execution_or_capital_mutation_fields() -> None:
    plan = draft_etf_sma_paper_experiment_plan(
        _candidate(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "20"),
        ),
        _PLAN_CONFIG,
    )

    for key in _flatten_dict_keys(plan.to_dict()):
        lowered = key.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)


def test_module_has_no_forbidden_imports_or_runtime_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _candidate(*values: tuple[str, str]) -> SmaResearchToPaperCandidate:
    return build_etf_sma_research_candidate(
        _bars(*values),
        _CONFIG,
        "2026-01-04",
    )


def _bars(*values: tuple[str, str]) -> list[SmaCandidateInputBar]:
    return [SmaCandidateInputBar(day, Decimal(close)) for day, close in values]


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
