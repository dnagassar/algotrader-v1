from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.research.crypto_strategy_evidence_battery import (
    CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
    REQUIRED_NO_SUBMIT_LABELS,
    CryptoEvidenceAssumptions,
    CryptoEvidenceBar,
    run_crypto_strategy_evidence_battery,
    validate_crypto_strategy_no_submit_packet,
)


MODULE_PATH = Path("src/algotrader/research/crypto_strategy_evidence_battery.py")
AS_OF = datetime(2026, 7, 9, 0, 0, tzinfo=UTC)


def test_deterministic_fixture_ranks_promotable_candidate_first() -> None:
    packet = _packet(_mixed_fixture_bars())
    first_row = packet["evidence_table"][0]

    assert packet["schema_version"] == CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION
    assert packet["candidate_symbols"] == list(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS)
    assert [item["strategy_id"] for item in packet["strategy_candidates"]] == [
        "trend_momentum_1",
        "breakout_4",
        "moving_average_regime_3_6",
        "volatility_filter_4",
    ]
    assert packet["data_source"] == "deterministic_unit_fixture"
    assert packet["data_freshness"] == "fixture_as_of_2026-07-09"
    assert packet["no_submit_decision"] == "promote_to_no_submit_plan"
    assert packet["selected_candidate"]["candidate_id"] == first_row["candidate_id"]
    assert packet["selected_candidate"]["symbol"] == "BTCUSD"
    assert packet["selected_candidate"]["candidate_decision"] == (
        "promote_to_no_submit_plan"
    )
    assert first_row["rank"] == 1
    assert Decimal(first_row["test_excess_return_vs_buy_hold"]) > Decimal("0")
    assert packet["benchmark_comparison"]["equal_weight_crypto_basket_available"] is True
    assert {record["benchmark_id"] for record in packet["benchmark_comparison"]["benchmarks"]} >= {
        "cash_no_trade",
        "buy_and_hold",
        "equal_weight_crypto_basket",
    }
    assert packet["validation_status"] == "passed"


def test_insufficient_data_blocks_promotion() -> None:
    packet = _packet(_short_fixture_bars())

    assert packet["no_submit_decision"] == "insufficient_data"
    assert packet["selected_candidate"] is None
    assert packet["rejection_reasons"] == ["insufficient_data"]
    assert all(
        row["candidate_decision"] == "insufficient_data"
        for row in packet["evidence_table"]
    )
    assert all(
        window["status"] == "insufficient_data"
        for window in packet["walk_forward_windows"]
    )


def test_high_drawdown_blocks_promotion() -> None:
    packet = _packet(_high_drawdown_fixture_bars())

    assert packet["no_submit_decision"] == "reject_candidate"
    assert packet["selected_candidate"] is None
    assert "high_drawdown" in packet["rejection_reasons"]
    high_drawdown_rows = [
        row
        for row in packet["evidence_table"]
        if "high_drawdown" in row["rejection_reasons"]
    ]
    assert high_drawdown_rows
    assert all(
        Decimal(row["test_max_drawdown"]) > Decimal("0.25")
        for row in high_drawdown_rows
    )


def test_benchmark_underperformance_blocks_promotion() -> None:
    packet = _packet(_steady_up_fixture_bars())

    assert packet["no_submit_decision"] == "reject_candidate"
    assert packet["selected_candidate"] is None
    assert "benchmark_underperformance" in packet["rejection_reasons"]
    assert all(
        row["candidate_decision"] != "promote_to_no_submit_plan"
        for row in packet["evidence_table"]
    )


def test_no_submit_packet_cannot_contain_broker_mutation_or_submit_instructions() -> None:
    packet = _packet(_mixed_fixture_bars())

    assert validate_crypto_strategy_no_submit_packet(packet) == []
    assert set(REQUIRED_NO_SUBMIT_LABELS) <= set(packet["labels"])
    assert packet["paper_submit_occurred"] is False
    assert packet["broker_mutation_occurred"] is False
    assert packet["broker_read_occurred"] is False
    assert packet["live_endpoint_touched"] is False
    assert packet["credential_values_exposed"] is False
    assert packet["network_access_attempted"] is False

    action = packet["next_safe_operator_action"].lower()
    for forbidden in (
        "submit order",
        "place order",
        "cancel order",
        "replace order",
        "close position",
        "liquidate",
    ):
        assert forbidden not in action


def test_module_has_no_broker_network_runtime_or_llm_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_prefixes = (
        "algotrader.execution",
        "algotrader.orchestration",
        "algotrader.portfolio",
        "algotrader.risk",
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "numpy",
        "openai",
        "pandas",
        "requests",
        "socket",
        "urllib",
        "yfinance",
    )
    imports = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ]
    imports.extend(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imports
        for prefix in forbidden_prefixes
    )


def _packet(bars: tuple[CryptoEvidenceBar, ...]) -> dict[str, object]:
    return run_crypto_strategy_evidence_battery(
        bars,
        as_of=AS_OF,
        data_source="deterministic_unit_fixture",
        data_freshness="fixture_as_of_2026-07-09",
        assumptions=CryptoEvidenceAssumptions(),
    )


def _mixed_fixture_bars() -> tuple[CryptoEvidenceBar, ...]:
    return (
        *_bars(
            "BTCUSD",
            (
                "100",
                "101",
                "102",
                "103",
                "104",
                "105",
                "106",
                "107",
                "108",
                "109",
                "110",
                "111",
                "112",
                "111",
                "80",
                "82",
                "84",
                "92",
                "104",
                "118",
            ),
        ),
        *_bars("ETHUSD", _linear_prices("50", "2", 20)),
        *_bars(
            "SOLUSD",
            (
                "40",
                "41",
                "42",
                "41",
                "40",
                "39",
                "41",
                "43",
                "44",
                "43",
                "42",
                "41",
                "40",
                "39",
                "38",
                "39",
                "40",
                "41",
                "42",
                "43",
            ),
        ),
        *_bars(
            "ADAUSD",
            (
                "1",
                "1.02",
                "1.01",
                "1.03",
                "1.04",
                "1.02",
                "1.05",
                "1.06",
                "1.04",
                "1.05",
                "1.03",
                "1.02",
                "1.01",
                "1",
                "0.99",
                "1",
                "1.01",
                "1.02",
                "1.03",
                "1.04",
            ),
        ),
    )


def _short_fixture_bars() -> tuple[CryptoEvidenceBar, ...]:
    bars: list[CryptoEvidenceBar] = []
    for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS:
        bars.extend(_bars(symbol, _linear_prices("100", "1", 8)))
    return tuple(bars)


def _high_drawdown_fixture_bars() -> tuple[CryptoEvidenceBar, ...]:
    prices = (
        "100",
        "101",
        "102",
        "103",
        "104",
        "105",
        "106",
        "107",
        "108",
        "109",
        "110",
        "111",
        "112",
        "114",
        "50",
        "49",
        "48",
        "52",
        "55",
        "58",
    )
    bars: list[CryptoEvidenceBar] = []
    for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS:
        bars.extend(_bars(symbol, prices))
    return tuple(bars)


def _steady_up_fixture_bars() -> tuple[CryptoEvidenceBar, ...]:
    bars: list[CryptoEvidenceBar] = []
    for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS:
        bars.extend(_bars(symbol, _linear_prices("100", "2", 20)))
    return tuple(bars)


def _bars(symbol: str, prices: tuple[str, ...]) -> tuple[CryptoEvidenceBar, ...]:
    first = AS_OF - timedelta(hours=len(prices) - 1)
    return tuple(
        CryptoEvidenceBar(
            symbol=symbol,
            timestamp=first + timedelta(hours=index),
            close=Decimal(price),
        )
        for index, price in enumerate(prices)
    )


def _linear_prices(start: str, step: str, count: int) -> tuple[str, ...]:
    start_value = Decimal(start)
    step_value = Decimal(step)
    return tuple(str(start_value + (step_value * Decimal(index))) for index in range(count))
