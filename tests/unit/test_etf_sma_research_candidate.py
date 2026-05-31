from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.etf_sma_research_candidate import (
    ETF_SMA_CANDIDATE_LABELS,
    SmaCandidateConfig,
    SmaCandidateInputBar,
    SmaResearchToPaperCandidate,
    build_etf_sma_research_candidate,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_research_candidate.py")
_CONFIG = SmaCandidateConfig(
    symbol="SPY",
    strategy_name="SPY SMA research-to-paper candidate",
    short_window=2,
    long_window=4,
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
    "client_order_id",
    "credential",
    "fill",
    "notional",
    "order",
    "portfolio",
    "quantity",
    "side",
    "time_in_force",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
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


def test_builds_bullish_trend_candidate_from_as_of_bars() -> None:
    candidate = build_etf_sma_research_candidate(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "20"),
        ),
        _CONFIG,
        "2026-01-04",
    )

    assert candidate.posture == "bullish_trend_candidate"
    assert candidate.latest_close == Decimal("20")
    assert candidate.short_sma == Decimal("20")
    assert candidate.long_sma == Decimal("15")
    assert candidate.eligible_sample_count == 4
    assert candidate.ignored_future_sample_count == 0
    assert candidate.to_dict() == {
        "candidate_type": "etf_sma_research_to_paper_candidate",
        "status": "research_candidate_only",
        "symbol": "SPY",
        "strategy_name": "SPY SMA research-to-paper candidate",
        "as_of": "2026-01-04",
        "short_window": 2,
        "long_window": 4,
        "sample_count": 4,
        "eligible_sample_count": 4,
        "ignored_future_sample_count": 0,
        "latest_close": "20",
        "short_sma": "20",
        "long_sma": "15",
        "posture": "bullish_trend_candidate",
        "evidence_summary": [
            "As of 2026-01-04, the 2-bar SMA 20 is above the 4-bar SMA 15.",
            "Future-dated bars were ignored before SMA calculation.",
        ],
        "limitations": [
            "offline deterministic candidate from caller-supplied local bars",
            "not approved for paper-lab submission",
            "no live authorization",
            "no profitability or edge claim",
            "separate paper-lab experiment plan required before any submission review",
        ],
        "labels": list(ETF_SMA_CANDIDATE_LABELS),
        "eligibility_status": "separate_plan_required_before_paper_experiment",
        "recommended_next_operator_action": "draft_separate_paper_lab_experiment_plan",
    }


def test_builds_defensive_or_cash_candidate_when_short_sma_is_not_above_long_sma() -> None:
    candidate = build_etf_sma_research_candidate(
        _bars(
            ("2026-01-01", "20"),
            ("2026-01-02", "20"),
            ("2026-01-03", "10"),
            ("2026-01-04", "10"),
        ),
        _CONFIG,
        "2026-01-04",
    )

    assert candidate.posture == "defensive_or_cash_candidate"
    assert candidate.latest_close == Decimal("10")
    assert candidate.short_sma == Decimal("10")
    assert candidate.long_sma == Decimal("15")
    assert candidate.to_dict()["evidence_summary"] == [
        "As of 2026-01-04, the 2-bar SMA 10 is at or below the 4-bar SMA 15.",
        "Future-dated bars were ignored before SMA calculation.",
    ]


def test_builds_insufficient_history_candidate_without_long_sma() -> None:
    candidate = build_etf_sma_research_candidate(
        _bars(("2026-01-01", "10"), ("2026-01-02", "11")),
        _CONFIG,
        "2026-01-02",
    )

    assert candidate.posture == "insufficient_history"
    assert candidate.latest_close == Decimal("11")
    assert candidate.short_sma == Decimal("10.5")
    assert candidate.long_sma is None
    assert candidate.to_dict()["long_sma"] is None
    assert candidate.to_dict()["evidence_summary"] == [
        "2 as-of bars available; 4 required.",
        "Future-dated bars were ignored before SMA calculation.",
    ]


def test_future_bars_do_not_influence_as_of_candidate_values() -> None:
    as_of_bars = _bars(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "20"),
    )
    with_future_bars = [
        *as_of_bars,
        SmaCandidateInputBar("2026-01-05", Decimal("1")),
        SmaCandidateInputBar("2026-01-06", Decimal("1")),
    ]

    without_future = build_etf_sma_research_candidate(
        as_of_bars,
        _CONFIG,
        "2026-01-04",
    )
    with_future = build_etf_sma_research_candidate(
        with_future_bars,
        _CONFIG,
        "2026-01-04",
    )

    assert with_future.sample_count == 6
    assert with_future.eligible_sample_count == 4
    assert with_future.ignored_future_sample_count == 2
    assert with_future.latest_close == without_future.latest_close
    assert with_future.short_sma == without_future.short_sma
    assert with_future.long_sma == without_future.long_sma
    assert with_future.posture == without_future.posture
    assert with_future.evidence_summary == without_future.evidence_summary


def test_candidate_and_inputs_are_immutable_and_dict_lists_are_copied() -> None:
    candidate = build_etf_sma_research_candidate(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "20"),
        ),
        _CONFIG,
        "2026-01-04",
    )
    bar = SmaCandidateInputBar("2026-01-01", Decimal("10"))

    with pytest.raises(FrozenInstanceError):
        candidate.posture = "changed"
    with pytest.raises(FrozenInstanceError):
        bar.close = Decimal("99")

    payload = candidate.to_dict()
    payload["labels"].append("changed")
    payload["evidence_summary"].append("changed")

    assert "changed" not in candidate.labels
    assert "changed" not in candidate.evidence_summary
    assert "changed" not in candidate.to_dict()["labels"]
    assert "changed" not in candidate.to_dict()["evidence_summary"]


def test_candidate_labels_and_eligibility_remain_conservative() -> None:
    candidate = build_etf_sma_research_candidate(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "20"),
        ),
        _CONFIG,
        "2026-01-04",
    )
    payload = candidate.to_dict()

    assert set(candidate.labels) == _REQUIRED_LABELS
    assert payload["labels"] == list(ETF_SMA_CANDIDATE_LABELS)
    assert payload["eligibility_status"] == "separate_plan_required_before_paper_experiment"
    assert payload["recommended_next_operator_action"] == (
        "draft_separate_paper_lab_experiment_plan"
    )
    assert any(
        "not approved for paper-lab submission" == item
        for item in payload["limitations"]
    )
    assert any("no live authorization" == item for item in payload["limitations"])
    assert any("no profitability or edge claim" == item for item in payload["limitations"])


def test_candidate_dict_is_primitive_only() -> None:
    candidate = build_etf_sma_research_candidate(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "20"),
        ),
        _CONFIG,
        "2026-01-04",
    )

    _assert_primitive_only(candidate.to_dict())


def test_candidate_output_has_no_execution_or_capital_mutation_fields() -> None:
    candidate = build_etf_sma_research_candidate(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "20"),
        ),
        _CONFIG,
        "2026-01-04",
    )

    for key in _flatten_dict_keys(candidate.to_dict()):
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


def test_config_requires_short_window_below_long_window() -> None:
    with pytest.raises(ValueError):
        SmaCandidateConfig(symbol="SPY", short_window=4, long_window=4)


def test_candidate_output_dataclass_validates_fixed_safety_metadata() -> None:
    with pytest.raises(ValueError):
        SmaResearchToPaperCandidate(
            candidate_type="changed",
            status="research_candidate_only",
            symbol="SPY",
            strategy_name="SPY SMA research-to-paper candidate",
            as_of="2026-01-04",
            short_window=2,
            long_window=4,
            sample_count=4,
            eligible_sample_count=4,
            ignored_future_sample_count=0,
            latest_close=Decimal("20"),
            short_sma=Decimal("20"),
            long_sma=Decimal("15"),
            posture="bullish_trend_candidate",
            evidence_summary=("example evidence",),
            limitations=("example limitation",),
            labels=ETF_SMA_CANDIDATE_LABELS,
            eligibility_status="separate_plan_required_before_paper_experiment",
            recommended_next_operator_action="draft_separate_paper_lab_experiment_plan",
        )


def _bars(*values: tuple[str, str]) -> list[SmaCandidateInputBar]:
    return [SmaCandidateInputBar(day, Decimal(close)) for day, close in values]


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
