from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.core.types import Bar
from algotrader.orchestration.strategy_adapter_registry import (
    StrategyAdapterRegistration,
    resolve_strategy_adapter,
    resolve_strategy_route_adapter,
)
from algotrader.orchestration.strategy_router import (
    SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_FAMILY,
    SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
    STRATEGY_ROUTER_LABEL,
    STRATEGY_ROUTER_REQUIRED_LABELS,
    route_strategy_signals,
    strategy_signal_from_spy_rsi_mean_reversion_result,
)
from algotrader.signals.spy_rsi_mean_reversion import (
    SPY_RSI_MEAN_REVERSION_LABELS,
    SPYRsiMeanReversionSignalConfig,
    evaluate_spy_rsi_mean_reversion_signal,
)


MODULE_PATH = Path("src/algotrader/signals/spy_rsi_mean_reversion.py")
AS_OF = datetime(2026, 8, 8, tzinfo=UTC)


def test_spy_rsi_shadow_candidate_emits_strategy_signal_contract() -> None:
    result = _evaluate(_descending_prices())
    signal = strategy_signal_from_spy_rsi_mean_reversion_result(result)

    assert result.posture == "oversold_buy_candidate"
    assert result.latest_rsi == Decimal("0")
    assert result.broker_action_performed is False
    assert result.submit_allowed is False
    assert result.profit_claim == "none"
    assert "accepted_adjusted_spy_daily_bars" in result.labels
    assert result.labels == SPY_RSI_MEAN_REVERSION_LABELS
    assert signal.strategy_id == SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID
    assert signal.strategy_family == SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_FAMILY
    assert signal.symbol == "SPY"
    assert signal.asset_class == "equity"
    assert signal.signal_state == "trade_candidate"
    assert signal.intended_action == "buy"
    assert signal.intended_side == "buy"
    assert signal.promotion_status == "shadow_only"
    assert signal.data_as_of == AS_OF
    assert set(STRATEGY_ROUTER_REQUIRED_LABELS) <= set(signal.labels)
    assert "shadow_only" in signal.labels
    assert STRATEGY_ROUTER_LABEL in signal.labels
    assert signal.blockers == ()


def test_spy_rsi_overbought_candidate_is_cash_only_shadow_exit() -> None:
    result = _evaluate(_ascending_prices())
    signal = strategy_signal_from_spy_rsi_mean_reversion_result(result)

    assert result.posture == "overbought_cash_candidate"
    assert result.latest_rsi == Decimal("100")
    assert signal.signal_state == "trade_candidate"
    assert signal.intended_action == "sell_close"
    assert signal.intended_side == "sell"
    assert signal.promotion_status == "shadow_only"


def test_shadow_trade_candidate_is_recorded_but_cannot_route_to_mutation() -> None:
    signal = strategy_signal_from_spy_rsi_mean_reversion_result(
        _evaluate(_descending_prices())
    )

    receipt = route_strategy_signals((signal,))
    resolution = resolve_strategy_route_adapter(receipt)

    assert receipt.route_status == "blocked"
    assert receipt.reason == "all_candidates_blocked"
    assert receipt.paper_mutation_allowed is False
    assert receipt.selected_signal is None
    assert receipt.signals == (signal,)
    assert receipt.candidate_signal_ids == ()
    assert receipt.blocked_signal_ids == (SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,)
    assert (
        "spy_rsi_14_mean_reversion_shadow:"
        "promotion_status_not_paper_mutation_candidate:shadow_only"
    ) in receipt.blockers
    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_router_all_candidates_blocked"
    assert resolution.paper_mutation_allowed is False


def test_shadow_candidate_cannot_resolve_to_paper_mutation_adapter() -> None:
    signal = strategy_signal_from_spy_rsi_mean_reversion_result(
        _evaluate(_descending_prices())
    )

    resolution = resolve_strategy_adapter(
        signal,
        registry=(
            StrategyAdapterRegistration(
                strategy_id=signal.strategy_id,
                promotion_status="paper_mutation_candidate",
                adapter_id="spy_rsi_mutation_adapter_not_allowed_fixture",
                adapter_mode="paper_mutation",
                asset_class="equity",
                supported_symbols=("SPY",),
                max_order_notional=Decimal("25.00"),
                enabled=True,
                required_labels=STRATEGY_ROUTER_REQUIRED_LABELS,
            ),
        ),
        adapter_mode="paper_mutation",
    )

    assert resolution.resolution_status == "blocked"
    assert (
        resolution.reason
        == "promotion_status_not_paper_mutation_candidate:shadow_only"
    )
    assert resolution.adapter_id == "spy_rsi_mutation_adapter_not_allowed_fixture"
    assert resolution.paper_mutation_allowed is False


def test_insufficient_history_emits_non_trade_shadow_blocker() -> None:
    result = _evaluate(_descending_prices()[:14])
    signal = strategy_signal_from_spy_rsi_mean_reversion_result(result)

    assert result.posture == "insufficient_history"
    assert result.latest_rsi is None
    assert result.blockers == ("insufficient_history",)
    assert signal.signal_state == "insufficient_evidence"
    assert signal.intended_action == "no_action"
    assert signal.intended_side == ""
    assert signal.promotion_status == "shadow_only"
    assert signal.blockers == ("insufficient_history",)


def test_spy_rsi_signal_has_no_broker_network_or_llm_imports() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    forbidden_prefixes = (
        "algotrader.execution",
        "algotrader.orchestration",
        "algotrader.research",
        "alpaca",
        "alpaca_trade_api",
        "anthropic",
        "httpx",
        "langchain",
        "langgraph",
        "openai",
        "requests",
        "socket",
        "urllib",
    )
    forbidden_calls = {
        "connect",
        "create_order",
        "request",
        "socket.socket",
        "submit_order",
        "urlopen",
    }
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
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in import_modules
        for prefix in forbidden_prefixes
    )
    assert call_names.isdisjoint(forbidden_calls)
    assert "submit_order(" not in text


def _evaluate(prices: tuple[Decimal, ...]):
    return evaluate_spy_rsi_mean_reversion_signal(
        _bars(prices),
        SPYRsiMeanReversionSignalConfig(as_of=AS_OF),
    )


def _descending_prices() -> tuple[Decimal, ...]:
    return tuple(Decimal(115 - index) for index in range(15))


def _ascending_prices() -> tuple[Decimal, ...]:
    return tuple(Decimal(100 + index) for index in range(15))


def _bars(prices: tuple[Decimal, ...]) -> tuple[Bar, ...]:
    first = AS_OF - timedelta(days=len(prices) - 1)
    return tuple(
        Bar(
            symbol="SPY",
            timestamp=first + timedelta(days=index),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=Decimal("1000"),
        )
        for index, price in enumerate(prices)
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
