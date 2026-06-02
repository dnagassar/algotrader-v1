from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.etf_sma_next_experiment_review import (
    ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS,
    EtfSmaNextExperimentReviewConfig,
    build_etf_sma_next_experiment_review,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_next_experiment_review.py")
_SAFE_RESET = "paper_lab_flat_clean"
_SAFE_CASH = Decimal("1999.81")
_SAFE_CURRENCY = "USD"
_ACTIONABLE_SIGNAL = "bullish_risk_on"
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
    "decimal",
    "algotrader.errors",
}
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "delete_order",
    "download",
    "getenv",
    "liquidate",
    "open",
    "os.getenv",
    "post",
    "read",
    "replace_order",
    "request",
    "socket.socket",
    "submit_order",
    "time.time",
    "urlopen",
    "write",
}


def test_clean_spy_valid_cap_and_actionable_signal_is_ready_for_m368_preview() -> None:
    review = _review()
    payload = review.to_dict()

    assert review.decision == "ready_for_separate_broker_preview_milestone"
    assert review.reason.endswith("separate M368 preview-only milestone.")
    assert review.source_evidence_id == "m366_fresh_paper_lab_reset_snapshot"
    assert review.paper_reset_classification == "paper_lab_flat_clean"
    assert review.cash == Decimal("1999.81")
    assert review.currency == "USD"
    assert review.position_count == 0
    assert review.open_order_count == 0
    assert review.symbol == "SPY"
    assert review.asset_class == "equity"
    assert review.strategy_name == "long_only_broad_etf_sma_50_200_daily"
    assert review.signal_status == "bullish_risk_on"
    assert review.target_cap == Decimal("25.00")
    assert review.allowlist == ("SPY",)
    assert review.blockers == ()
    assert review.separate_broker_preview_milestone_allowed is True
    assert review.submit_authorized is False
    assert review.required_next_milestone == (
        "M368 - SPY ETF/SMA broker-facing preview-only milestone"
    )
    assert review.safety_labels == ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS
    assert payload["target_cap"] == "25.00"
    assert payload["cash"] == "1999.81"
    assert payload["allowlist"] == ["SPY"]
    assert payload["submit_authorized"] is False


def test_clean_reset_with_risk_off_signal_is_blocked_signal_not_actionable() -> None:
    review = _review(signal_status="defensive_risk_off")

    assert review.decision == "blocked_signal_not_actionable"
    assert "signal_status_risk_off" in review.blockers
    assert review.separate_broker_preview_milestone_allowed is False
    assert review.submit_authorized is False
    assert review.required_next_milestone == (
        "resolve_m367_blocker_offline_before_paper_facing_work"
    )


def test_clean_reset_with_insufficient_history_signal_is_blocked() -> None:
    review = _review(signal_status="insufficient_history")

    assert review.decision == "blocked_signal_not_actionable"
    assert "signal_status_insufficient_history" in review.blockers
    assert review.submit_authorized is False


def test_non_clean_reset_is_blocked_reset_not_clean() -> None:
    review = _review(paper_reset_classification="ambiguous_or_incomplete")

    assert review.decision == "blocked_reset_not_clean"
    assert "reset_classification_not_paper_lab_flat_clean" in review.blockers
    assert review.separate_broker_preview_milestone_allowed is False


def test_positions_or_open_orders_block_reset_cleanliness() -> None:
    with_position = _review(position_count=1)
    with_open_order = _review(open_order_count=1)

    assert with_position.decision == "blocked_reset_not_clean"
    assert "positions_present" in with_position.blockers
    assert with_open_order.decision == "blocked_reset_not_clean"
    assert "open_orders_present" in with_open_order.blockers


def test_non_spy_symbol_is_blocked_symbol_not_allowed() -> None:
    config = EtfSmaNextExperimentReviewConfig(symbol="QQQ")

    review = _review(config=config)

    assert review.decision == "blocked_symbol_not_allowed"
    assert "symbol_not_spy" in review.blockers


def test_allowlist_with_anything_besides_spy_is_blocked() -> None:
    config = EtfSmaNextExperimentReviewConfig(allowlist=("SPY", "QQQ"))

    review = _review(config=config)

    assert review.decision == "blocked_symbol_not_allowed"
    assert "allowlist_not_spy_only" in review.blockers


def test_cap_greater_than_twenty_five_is_blocked_cap_invalid() -> None:
    config = EtfSmaNextExperimentReviewConfig(target_cap=Decimal("25.01"))

    review = _review(config=config)

    assert review.decision == "blocked_cap_invalid"
    assert "cap_above_25_usd" in review.blockers


@pytest.mark.parametrize("cap", [Decimal("0"), Decimal("-0.01")])
def test_zero_or_negative_cap_is_blocked_cap_invalid(cap: Decimal) -> None:
    config = EtfSmaNextExperimentReviewConfig(target_cap=cap)

    review = _review(config=config)

    assert review.decision == "blocked_cap_invalid"
    assert "cap_non_positive" in review.blockers


def test_missing_cap_is_blocked_cap_invalid() -> None:
    config = EtfSmaNextExperimentReviewConfig(target_cap=None)

    review = _review(config=config)

    assert review.decision == "blocked_cap_invalid"
    assert "cap_missing" in review.blockers


def test_missing_signal_is_documented_as_blocked_not_actionable() -> None:
    review = _review(signal_status=None)

    assert review.decision == "blocked_signal_not_actionable"
    assert "signal_status_missing" in review.blockers
    assert review.submit_authorized is False


def test_safe_but_incomplete_non_equity_asset_class_requires_operator_review() -> None:
    config = EtfSmaNextExperimentReviewConfig(asset_class="fund")

    review = _review(config=config)

    assert review.decision == "operator_review_required"
    assert "asset_class_not_equity" in review.blockers
    assert review.required_next_milestone == (
        "operator_review_m367_inputs_before_preview_decision"
    )
    assert review.submit_authorized is False


def test_review_result_is_immutable() -> None:
    review = _review()

    with pytest.raises(FrozenInstanceError):
        review.decision = "changed"

    with pytest.raises(ValueError, match="submit_authorized"):
        replace(review, submit_authorized=True)


def test_input_collections_and_payload_lists_are_copied() -> None:
    allowlist = ["SPY"]
    labels = list(ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS)
    config = EtfSmaNextExperimentReviewConfig(
        allowlist=allowlist,
        labels=labels,
    )
    review = _review(config=config)

    allowlist.append("QQQ")
    labels.append("changed")
    payload = review.to_dict()
    payload["allowlist"].append("QQQ")
    payload["safety_labels"].append("changed")
    payload["blockers"].append("changed")
    payload["limitations"].append("changed")

    assert review.allowlist == ("SPY",)
    assert review.safety_labels == ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS
    assert review.blockers == ()
    assert "changed" not in review.limitations
    assert "QQQ" not in review.to_dict()["allowlist"]
    assert "changed" not in review.to_dict()["safety_labels"]


def test_config_and_review_dicts_are_primitive_only() -> None:
    config = EtfSmaNextExperimentReviewConfig()
    review = _review(config=config)

    _assert_primitive_only(config.to_dict())
    _assert_primitive_only(review.to_dict())


def test_submit_authorization_is_always_false_across_decisions() -> None:
    reviews = (
        _review(),
        _review(paper_reset_classification="ambiguous_or_incomplete"),
        _review(config=EtfSmaNextExperimentReviewConfig(symbol="QQQ")),
        _review(config=EtfSmaNextExperimentReviewConfig(target_cap=Decimal("25.01"))),
        _review(signal_status="stale"),
        _review(config=EtfSmaNextExperimentReviewConfig(asset_class="fund")),
    )

    assert {review.submit_authorized for review in reviews} == {False}
    assert all(
        review.to_dict()["submit_authorized"] is False
        for review in reviews
    )


def test_module_has_no_broker_sdk_network_or_credential_imports_or_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _review(
    *,
    paper_reset_classification: str = _SAFE_RESET,
    position_count: int = 0,
    open_order_count: int = 0,
    signal_status: str | None = _ACTIONABLE_SIGNAL,
    config: EtfSmaNextExperimentReviewConfig | None = None,
):
    return build_etf_sma_next_experiment_review(
        paper_reset_classification=paper_reset_classification,
        cash=_SAFE_CASH,
        currency=_SAFE_CURRENCY,
        position_count=position_count,
        open_order_count=open_order_count,
        signal_status=signal_status,
        config=config,
    )


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
