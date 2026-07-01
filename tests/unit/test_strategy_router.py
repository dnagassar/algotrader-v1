from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.core.types import Bar
from algotrader.orchestration.strategy_router import (
    STRATEGY_ROUTER_LABEL,
    StrategySignal,
    route_strategy_signals,
    strategy_signal_from_etf_sma_result,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)


MODULE_PATH = Path("src/algotrader/orchestration/strategy_router.py")
REQUIRED_LABELS = ("paper_lab_only", "not_live_authorized", "profit_claim=none")


def test_no_trade_strategy_does_not_suppress_promoted_candidate() -> None:
    receipt = route_strategy_signals(
        (
            _dummy_signal(
                strategy_id="dummy_no_trade_fixture",
                signal_state="no_trade",
                intended_action="no_action",
                intended_side="",
                promotion_status="research_only",
            ),
            _dummy_signal(strategy_id="promoted_candidate"),
        )
    )

    assert receipt.route_status == "action_routed"
    assert receipt.paper_mutation_allowed is True
    assert receipt.selected_signal is not None
    assert receipt.selected_signal.strategy_id == "promoted_candidate"
    assert receipt.candidate_signal_ids == ("promoted_candidate",)


def test_research_only_candidate_cannot_route_for_paper_mutation() -> None:
    receipt = route_strategy_signals(
        (
            _dummy_signal(
                strategy_id="research_only_trade_candidate",
                promotion_status="research_only",
            ),
        )
    )

    assert receipt.route_status == "blocked"
    assert receipt.paper_mutation_allowed is False
    assert receipt.selected_signal is None
    assert receipt.candidate_signal_ids == ()
    assert (
        "research_only_trade_candidate:"
        "promotion_status_not_paper_mutation_candidate:research_only"
    ) in receipt.blockers


def test_shadow_only_candidate_cannot_route_for_paper_mutation() -> None:
    receipt = route_strategy_signals(
        (
            _dummy_signal(
                strategy_id="shadow_only_trade_candidate",
                promotion_status="shadow_only",
            ),
        )
    )

    assert receipt.route_status == "blocked"
    assert receipt.paper_mutation_allowed is False
    assert (
        "shadow_only_trade_candidate:"
        "promotion_status_not_paper_mutation_candidate:shadow_only"
    ) in receipt.blockers


def test_paper_mutation_candidate_routes_after_independent_safety_gates() -> None:
    receipt = route_strategy_signals((_dummy_signal(strategy_id="promoted"),))

    assert receipt.route_status == "action_routed"
    assert receipt.route_action == "buy"
    assert receipt.paper_mutation_allowed is True
    assert receipt.blockers == ()
    assert set(REQUIRED_LABELS) <= set(receipt.labels)
    assert STRATEGY_ROUTER_LABEL in receipt.labels


def test_conflicting_promoted_candidates_block_for_review() -> None:
    receipt = route_strategy_signals(
        (
            _dummy_signal(strategy_id="promoted_buy"),
            _dummy_signal(
                strategy_id="promoted_sell",
                intended_action="sell_close",
                intended_side="sell",
            ),
        )
    )

    assert receipt.route_status == "blocked"
    assert receipt.paper_mutation_allowed is False
    assert receipt.reason == "conflict_requires_review"
    assert "conflict_requires_review" in receipt.blockers
    assert receipt.candidate_signal_ids == ("promoted_buy", "promoted_sell")


def test_all_blocked_candidates_produce_blocked_receipt() -> None:
    receipt = route_strategy_signals(
        (
            _dummy_signal(
                strategy_id="blocked_one",
                signal_state="blocked",
                intended_action="no_action",
                intended_side="",
                blockers=("manual_review_required",),
            ),
            _dummy_signal(
                strategy_id="blocked_two",
                signal_state="insufficient_evidence",
                intended_action="no_action",
                intended_side="",
                blockers=("insufficient_history",),
            ),
        )
    )

    assert receipt.route_status == "blocked"
    assert receipt.route_action == "no_action_required"
    assert receipt.paper_mutation_allowed is False
    assert receipt.blocked_signal_ids == ("blocked_one", "blocked_two")
    assert receipt.candidate_signal_ids == ()


def test_sma_signal_output_is_represented_in_router_contract() -> None:
    as_of = datetime(2026, 8, 8, tzinfo=UTC)
    result = evaluate_etf_sma_signal(
        _bars(as_of, posture="risk_on"),
        EtfSmaSignalConfig(as_of=as_of, symbol="SPY"),
    )

    signal = strategy_signal_from_etf_sma_result(result)
    receipt = route_strategy_signals((signal,))

    assert signal.strategy_id == "spy_sma_50_200_training_wheel"
    assert signal.strategy_family == "long_only_broad_etf_sma_trend_filter"
    assert signal.symbol == "SPY"
    assert signal.asset_class == "equity"
    assert signal.signal_state == "trade_candidate"
    assert signal.intended_action == "buy"
    assert signal.promotion_status == "paper_mutation_candidate"
    assert set(REQUIRED_LABELS) <= set(signal.labels)
    assert receipt.paper_mutation_allowed is True
    assert receipt.selected_signal is signal


def test_router_receipt_preserves_labels_and_blockers() -> None:
    receipt = route_strategy_signals(
        (
            _dummy_signal(
                strategy_id="blocked_fixture",
                labels=(*REQUIRED_LABELS, "custom_label"),
                blockers=("operator_review_required",),
            ),
        )
    )
    payload = receipt.to_dict()

    assert "custom_label" in receipt.labels
    assert "blocked_fixture:operator_review_required" in receipt.blockers
    assert payload["signals"][0]["labels"] == [
        *REQUIRED_LABELS,
        "custom_label",
    ]
    assert payload["signals"][0]["blockers"] == ["operator_review_required"]


def test_strategy_router_hot_path_has_no_broker_or_network_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_prefixes = (
        "algotrader.execution",
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )
    import_modules = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]
    import_modules.extend(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in import_modules
        for prefix in forbidden_prefixes
    )
    assert "submit_order" not in MODULE_PATH.read_text(encoding="utf-8")


def _dummy_signal(
    *,
    strategy_id: str,
    signal_state: str = "trade_candidate",
    intended_action: str = "buy",
    intended_side: str = "buy",
    promotion_status: str = "paper_mutation_candidate",
    labels: tuple[str, ...] = REQUIRED_LABELS,
    blockers: tuple[str, ...] = (),
) -> StrategySignal:
    return StrategySignal(
        strategy_id=strategy_id,
        strategy_family="test_dummy_strategy_fixture",
        symbol="SPY",
        asset_class="equity",
        signal_state=signal_state,
        intended_action=intended_action,
        intended_side=intended_side,
        expected_holding_period="test_only",
        max_loss_model="test_only",
        risk_budget="test_only",
        data_as_of=datetime(2026, 8, 8, tzinfo=UTC),
        promotion_status=promotion_status,
        labels=labels,
        blockers=blockers,
    )


def _bars(as_of: datetime, *, posture: str) -> tuple[Bar, ...]:
    first = as_of - timedelta(days=219)
    bars: list[Bar] = []
    for index in range(220):
        close = Decimal("100") + Decimal(index)
        if posture == "risk_off":
            close = Decimal("500") - Decimal(index)
        timestamp = first + timedelta(days=index)
        bars.append(
            Bar(
                symbol="SPY",
                timestamp=timestamp,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=Decimal("1000"),
            )
        )
    return tuple(bars)
