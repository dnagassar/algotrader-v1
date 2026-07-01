from __future__ import annotations

import ast
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from algotrader.orchestration.strategy_adapter_registry import (
    SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID,
    StrategyAdapterRegistration,
    resolve_strategy_adapter,
    resolve_strategy_route_adapter,
)
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_FAMILY,
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_FAMILY,
    SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
    STRATEGY_ROUTER_REQUIRED_LABELS,
    StrategySignal,
    route_strategy_signals,
)


MODULE_PATH = Path("src/algotrader/orchestration/strategy_adapter_registry.py")
REQUIRED_LABELS = STRATEGY_ROUTER_REQUIRED_LABELS


def test_known_sma_strategy_resolves_through_default_registry() -> None:
    receipt = route_strategy_signals((_signal(),))

    resolution = resolve_strategy_route_adapter(receipt)

    assert receipt.route_status == "action_routed"
    assert resolution.resolution_status == "resolved"
    assert resolution.reason == "strategy_adapter_resolved"
    assert resolution.strategy_id == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert resolution.adapter_id == SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID
    assert resolution.adapter_mode == "paper_mutation"
    assert resolution.paper_mutation_allowed is True
    assert resolution.to_dict()["adapter"]["supported_symbols"] == ["SPY"]


def test_unknown_strategy_blocks_even_when_router_would_route() -> None:
    receipt = route_strategy_signals(
        (
            _signal(
                strategy_id="unknown_spy_sma_candidate",
                strategy_family=SMA_TRAINING_WHEEL_STRATEGY_FAMILY,
                symbol="SPY",
            ),
        )
    )

    resolution = resolve_strategy_route_adapter(receipt)

    assert receipt.route_status == "action_routed"
    assert receipt.paper_mutation_allowed is True
    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_adapter_missing"
    assert resolution.paper_mutation_allowed is False


def test_missing_adapter_blocks_for_paper_mutation_candidate() -> None:
    resolution = resolve_strategy_adapter(_signal(), registry=())

    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_adapter_missing"
    assert resolution.blockers == ("strategy_adapter_missing",)
    assert resolution.paper_mutation_allowed is False


def test_disabled_adapter_blocks() -> None:
    resolution = resolve_strategy_adapter(
        _signal(),
        registry=(
            _registration(
                enabled=False,
                blocker="operator_disabled_strategy_adapter",
            ),
        ),
    )

    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "operator_disabled_strategy_adapter"
    assert resolution.adapter_id == "test_strategy_adapter"
    assert resolution.paper_mutation_allowed is False


def test_research_and_shadow_only_cannot_resolve_to_mutation_adapter() -> None:
    for promotion_status in ("research_only", "shadow_only"):
        signal = _signal(
            strategy_id=f"{promotion_status}_candidate",
            promotion_status=promotion_status,
        )
        resolution = resolve_strategy_adapter(
            signal,
            registry=(_registration(strategy_id=signal.strategy_id),),
            adapter_mode="paper_mutation",
        )

        assert resolution.resolution_status == "blocked"
        assert (
            resolution.reason
            == f"promotion_status_not_paper_mutation_candidate:{promotion_status}"
        )
        assert resolution.paper_mutation_allowed is False


def test_spy_rsi_shadow_candidate_cannot_resolve_to_mutation_adapter() -> None:
    signal = _signal(
        strategy_id=SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
        strategy_family=SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_FAMILY,
        promotion_status="shadow_only",
    )

    resolution = resolve_strategy_adapter(
        signal,
        registry=(
            _registration(
                strategy_id=signal.strategy_id,
                adapter_id="spy_rsi_paper_mutation_adapter_not_allowed_fixture",
            ),
        ),
        adapter_mode="paper_mutation",
    )

    assert resolution.resolution_status == "blocked"
    assert (
        resolution.reason
        == "promotion_status_not_paper_mutation_candidate:shadow_only"
    )
    assert resolution.adapter_id == "spy_rsi_paper_mutation_adapter_not_allowed_fixture"
    assert resolution.paper_mutation_allowed is False


def test_paper_mutation_candidate_requires_enabled_mutation_adapter() -> None:
    resolution = resolve_strategy_adapter(
        _signal(),
        registry=(
            _registration(
                promotion_status="paper_preview_candidate",
                adapter_mode="preview_only",
            ),
        ),
        adapter_mode="paper_mutation",
    )

    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_adapter_mode_mismatch"
    assert resolution.paper_mutation_allowed is False


def test_registration_mode_promotion_mismatch_blocks() -> None:
    resolution = resolve_strategy_adapter(
        _signal(),
        registry=(
            _registration(
                promotion_status="paper_preview_candidate",
                adapter_mode="paper_mutation",
            ),
        ),
        adapter_mode="paper_mutation",
    )

    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_adapter_registration_promotion_mismatch"
    assert resolution.paper_mutation_allowed is False


def test_preview_only_adapter_resolves_preview_candidate_without_mutation() -> None:
    signal = _signal(
        strategy_id="preview_only_dummy_strategy",
        promotion_status="paper_preview_candidate",
    )
    resolution = resolve_strategy_adapter(
        signal,
        registry=(
            _registration(
                strategy_id=signal.strategy_id,
                promotion_status="paper_preview_candidate",
                adapter_mode="preview_only",
            ),
        ),
        adapter_mode="preview_only",
    )

    assert resolution.resolution_status == "resolved"
    assert resolution.adapter_mode == "preview_only"
    assert resolution.paper_mutation_allowed is False


def test_unsupported_symbol_blocks() -> None:
    resolution = resolve_strategy_adapter(_signal(symbol="QQQ"))

    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_adapter_unsupported_symbol"
    assert resolution.paper_mutation_allowed is False


def test_unsupported_asset_class_blocks() -> None:
    resolution = resolve_strategy_adapter(_signal(asset_class="crypto"))

    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_adapter_unsupported_asset_class"
    assert resolution.paper_mutation_allowed is False


def test_requested_notional_over_adapter_cap_blocks() -> None:
    resolution = resolve_strategy_adapter(
        _signal(),
        requested_order_notional=Decimal("25.01"),
    )

    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_adapter_max_order_notional_exceeded"
    assert resolution.paper_mutation_allowed is False


def test_conflicting_routed_candidates_still_block_before_registry() -> None:
    receipt = route_strategy_signals(
        (
            _signal(),
            _signal(
                strategy_id="conflicting_dummy_candidate",
                intended_action="sell_close",
                intended_side="sell",
            ),
        )
    )

    resolution = resolve_strategy_route_adapter(receipt)

    assert receipt.route_status == "blocked"
    assert receipt.reason == "conflict_requires_review"
    assert resolution.resolution_status == "blocked"
    assert resolution.reason == "strategy_router_conflict_requires_review"
    assert resolution.paper_mutation_allowed is False


def test_strategy_adapter_registry_has_no_broker_network_or_llm_imports() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    forbidden_prefixes = (
        "algotrader.execution",
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
    assert "submit_order" not in text


def _signal(
    *,
    strategy_id: str = SMA_TRAINING_WHEEL_STRATEGY_ID,
    strategy_family: str = SMA_TRAINING_WHEEL_STRATEGY_FAMILY,
    symbol: str = "SPY",
    asset_class: str = "equity",
    signal_state: str = "trade_candidate",
    intended_action: str = "buy",
    intended_side: str = "buy",
    promotion_status: str = "paper_mutation_candidate",
    labels: tuple[str, ...] = REQUIRED_LABELS,
) -> StrategySignal:
    return StrategySignal(
        strategy_id=strategy_id,
        strategy_family=strategy_family,
        symbol=symbol,
        asset_class=asset_class,
        signal_state=signal_state,
        intended_action=intended_action,
        intended_side=intended_side,
        expected_holding_period="test_only",
        max_loss_model="test_only",
        risk_budget="test_only",
        data_as_of=datetime(2026, 8, 8, tzinfo=UTC),
        promotion_status=promotion_status,
        labels=labels,
    )


def _registration(
    *,
    strategy_id: str = SMA_TRAINING_WHEEL_STRATEGY_ID,
    promotion_status: str = "paper_mutation_candidate",
    adapter_id: str = "test_strategy_adapter",
    adapter_mode: str = "paper_mutation",
    asset_class: str = "equity",
    supported_symbols: tuple[str, ...] = ("SPY",),
    max_order_notional: Decimal | str | None = Decimal("25.00"),
    enabled: bool = True,
    blocker: str = "",
) -> StrategyAdapterRegistration:
    return StrategyAdapterRegistration(
        strategy_id=strategy_id,
        promotion_status=promotion_status,
        adapter_id=adapter_id,
        adapter_mode=adapter_mode,
        asset_class=asset_class,
        supported_symbols=supported_symbols,
        max_order_notional=max_order_notional,
        enabled=enabled,
        required_labels=REQUIRED_LABELS,
        blocker=blocker,
    )
