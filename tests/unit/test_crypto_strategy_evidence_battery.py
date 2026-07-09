from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.crypto_strategy_evidence_battery import (
    CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
    REQUIRED_NO_SUBMIT_LABELS,
    CryptoEvidenceAssumptions,
    CryptoEvidenceBar,
    build_crypto_strategy_real_data_evidence_packet,
    classify_crypto_strategy_no_submit_packet,
    load_crypto_evidence_bars_from_csv,
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


def test_valid_multi_symbol_local_csv_passes_sufficiency(tmp_path: Path) -> None:
    csv_path = tmp_path / "crypto_history.csv"
    bars = _multi_symbol_bars(row_count=80)
    _write_crypto_csv(csv_path, bars)

    loaded_bars = load_crypto_evidence_bars_from_csv(csv_path)
    packet = build_crypto_strategy_real_data_evidence_packet(
        csv_path,
        as_of=AS_OF,
        data_source="local_historical_crypto_csv",
        data_freshness="unit_test_local_snapshot",
    )

    assert len(loaded_bars) == 320
    assert packet["data_path"] == str(csv_path)
    assert packet["input_paths"] == [str(csv_path)]
    assert packet["normalized_output_path"] == ""
    assert packet["classification"] == "sufficient_real_crypto_history"
    assert packet["symbols_required"] == list(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS)
    assert packet["symbols_found"] == list(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS)
    assert packet["symbols_missing"] == []
    assert packet["rows_per_symbol"] == {
        symbol: 80 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert packet["rows_per_symbol_before_normalization"] == {
        symbol: 80 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert packet["rows_per_symbol_after_normalization"] == {
        symbol: 80 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert packet["duplicate_rows_removed_per_symbol"] == {
        symbol: 0 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert packet["required_minimum_rows"] == 80
    assert packet["required_minimum_span"] == {"hours": 72, "iso8601": "PT72H"}
    assert packet["schema_validation_status"] == "passed"
    assert packet["duplicate_timestamp_status"] == "passed"
    assert packet["duplicate_timestamp_status_after_normalization"] == "passed"
    assert packet["missing_close_status"] == "passed"
    assert packet["monotonic_timestamp_status"] == "passed"
    assert packet["volume_status"] == "available"
    assert packet["data_inventory"]["blocking_reasons"] == []
    assert packet["date_range_per_symbol"]["BTCUSD"]["start"] == (
        bars[0].timestamp.isoformat()
    )
    assert packet["missing_columns"] == []
    assert packet["strategies_evaluated"] == [
        "trend_momentum_1",
        "breakout_4",
        "moving_average_regime_3_6",
        "volatility_filter_4",
    ]
    assert packet["no_submit_classification"] in {
        "promote_to_no_submit_plan",
        "reject_candidate",
        "keep_researching",
    }
    assert packet["paper_planning_eligibility"] in {"eligible", "not_eligible"}
    assert packet["validation_status"] == "passed"


def test_single_symbol_btc_only_data_blocks_multi_symbol_sufficiency(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "btc_only.csv"
    _write_crypto_csv(csv_path, _bars("BTCUSD", _linear_prices("100", "1", 80)))

    packet = build_crypto_strategy_real_data_evidence_packet(csv_path, as_of=AS_OF)

    assert packet["classification"] == "insufficient_real_crypto_history"
    assert packet["no_submit_classification"] == "insufficient_real_crypto_history"
    assert packet["symbols_found"] == ["BTCUSD"]
    assert packet["symbols_missing"] == ["ETHUSD", "SOLUSD", "ADAUSD"]
    assert packet["rows_per_symbol"] == {"BTCUSD": 80}
    assert "missing_required_symbols" in packet["data_inventory"]["blocking_reasons"]
    assert packet["strategies_evaluated"] == []
    assert packet["selected_candidate"] is None
    assert packet["paper_planning_eligibility"] == "not_eligible"


def test_missing_required_columns_block_real_data_probe(tmp_path: Path) -> None:
    csv_path = tmp_path / "missing_close.csv"
    csv_path.write_text(
        "timestamp,symbol,asset_class,open,high,low\n"
        f"{AS_OF.isoformat()},BTCUSD,crypto,100,101,99\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="missing required columns: close"):
        load_crypto_evidence_bars_from_csv(csv_path)

    packet = build_crypto_strategy_real_data_evidence_packet(
        csv_path,
        as_of=AS_OF,
    )

    assert packet["classification"] == "insufficient_real_crypto_history"
    assert packet["no_submit_classification"] == "insufficient_real_crypto_history"
    assert packet["schema_validation_status"] == "failed"
    assert packet["missing_close_status"] == "failed"
    assert packet["missing_columns"] == ["close"]
    assert packet["selected_candidate"] is None
    assert "missing_required_columns" in packet["data_inventory"]["blocking_reasons"]


def test_insufficient_real_data_rows_block_probe_promotion(tmp_path: Path) -> None:
    csv_path = tmp_path / "short_history.csv"
    _write_crypto_csv(csv_path, _multi_symbol_bars(row_count=79))

    packet = build_crypto_strategy_real_data_evidence_packet(
        csv_path,
        as_of=AS_OF,
    )

    assert packet["battery_no_submit_decision"] == "insufficient_data"
    assert packet["classification"] == "insufficient_real_crypto_history"
    assert packet["no_submit_classification"] == "insufficient_real_crypto_history"
    assert packet["rows_per_symbol"] == {
        symbol: 79 for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    }
    assert "insufficient_rows" in packet["data_inventory"]["blocking_reasons"]
    assert packet["selected_candidate"] is None


def test_duplicate_symbol_timestamp_rows_normalize_deterministically(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "duplicate_history.csv"
    normalized_path = tmp_path / "normalized_history.csv"
    clean_bars = _multi_symbol_bars(row_count=80)
    duplicate_btc_bar = CryptoEvidenceBar(
        symbol="BTCUSD",
        timestamp=clean_bars[0].timestamp,
        close=Decimal("101"),
    )
    _write_crypto_csv(csv_path, (*clean_bars, duplicate_btc_bar))

    packet = build_crypto_strategy_real_data_evidence_packet(
        csv_path,
        as_of=AS_OF,
        normalized_output_path=normalized_path,
    )

    assert packet["classification"] == "sufficient_real_crypto_history"
    assert packet["duplicate_timestamp_status"] == "passed"
    assert packet["duplicate_timestamp_status_after_normalization"] == "passed"
    assert packet["rows_per_symbol_before_normalization"]["BTCUSD"] == 81
    assert packet["rows_per_symbol_after_normalization"]["BTCUSD"] == 80
    assert packet["duplicate_rows_removed_per_symbol"]["BTCUSD"] == 1
    assert packet["data_inventory"]["blocking_reasons"] == []
    assert packet["normalized_output_path"] == str(normalized_path)
    assert normalized_path.is_file()

    normalized_bars = load_crypto_evidence_bars_from_csv(normalized_path)
    assert len(normalized_bars) == 320
    assert normalized_bars[0].symbol == "ADAUSD"
    first_btc = next(bar for bar in normalized_bars if bar.symbol == "BTCUSD")
    assert first_btc.close == Decimal("101")


def test_insufficient_ada_rows_and_span_block_sufficiency(tmp_path: Path) -> None:
    csv_path = tmp_path / "ada_short_history.csv"
    bars = (
        *_bars("BTCUSD", _linear_prices("100", "1", 80)),
        *_bars("ETHUSD", _linear_prices("200", "1", 80)),
        *_bars("SOLUSD", _linear_prices("300", "1", 80)),
        *_bars("ADAUSD", _linear_prices("1", "0.01", 10)),
    )
    _write_crypto_csv(csv_path, bars)

    packet = build_crypto_strategy_real_data_evidence_packet(csv_path, as_of=AS_OF)

    assert packet["classification"] == "insufficient_real_crypto_history"
    assert packet["symbols_missing"] == []
    assert packet["rows_per_symbol_after_normalization"]["ADAUSD"] == 10
    assert packet["date_range_per_symbol"]["ADAUSD"]["span_hours"] == "9"
    assert "insufficient_rows" in packet["data_inventory"]["blocking_reasons"]
    assert "insufficient_date_span" in packet["data_inventory"]["blocking_reasons"]
    assert packet["paper_planning_eligibility"] == "not_eligible"


def test_missing_close_values_block_sufficiency(tmp_path: Path) -> None:
    csv_path = tmp_path / "missing_close_value.csv"
    csv_path.write_text(
        "timestamp,symbol,asset_class,open,high,low,close,volume\n"
        f"{AS_OF.isoformat()},BTCUSD,crypto,100,101,99,,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="missing close price"):
        load_crypto_evidence_bars_from_csv(csv_path)

    packet = build_crypto_strategy_real_data_evidence_packet(csv_path, as_of=AS_OF)

    assert packet["classification"] == "insufficient_real_crypto_history"
    assert packet["missing_close_status"] == "failed"
    assert "missing_close_values" in packet["data_inventory"]["blocking_reasons"]
    assert packet["selected_candidate"] is None


def test_non_monotonic_timestamps_are_sorted_by_normalization(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "non_monotonic_history.csv"
    normalized_path = tmp_path / "normalized_non_monotonic.csv"
    reversed_bars = tuple(reversed(_multi_symbol_bars(row_count=80)))
    _write_crypto_csv(csv_path, reversed_bars)

    packet = build_crypto_strategy_real_data_evidence_packet(
        csv_path,
        as_of=AS_OF,
        normalized_output_path=normalized_path,
    )

    assert packet["classification"] == "sufficient_real_crypto_history"
    assert packet["monotonic_timestamp_status"] == "passed"
    assert packet["data_inventory"]["records"][0][
        "monotonic_timestamp_status_before_normalization"
    ] == "failed"
    assert packet["data_inventory"]["blocking_reasons"] == []

    normalized_bars = load_crypto_evidence_bars_from_csv(normalized_path)
    timestamps_by_symbol: dict[str, list[datetime]] = {}
    for bar in normalized_bars:
        timestamps_by_symbol.setdefault(bar.symbol, []).append(bar.timestamp)
    assert all(
        timestamps == sorted(timestamps)
        for timestamps in timestamps_by_symbol.values()
    )


def test_fixture_only_result_cannot_be_mislabeled_as_real_data_promotion(
    tmp_path: Path,
) -> None:
    fixture_packet = _packet(_mixed_fixture_bars())
    assert fixture_packet["no_submit_decision"] == "promote_to_no_submit_plan"
    assert (
        classify_crypto_strategy_no_submit_packet(fixture_packet)
        == "insufficient_real_crypto_history"
    )

    csv_path = tmp_path / "fixture_history.csv"
    _write_crypto_csv(
        csv_path,
        _multi_symbol_bars(row_count=80),
        source="deterministic_unit_fixture",
    )
    real_probe_packet = build_crypto_strategy_real_data_evidence_packet(
        csv_path,
        as_of=AS_OF,
        data_source="deterministic_unit_fixture",
    )

    assert real_probe_packet["classification"] == (
        "insufficient_real_crypto_history"
    )
    assert real_probe_packet["no_submit_classification"] == (
        "insufficient_real_crypto_history"
    )
    assert real_probe_packet["selected_candidate"] is None
    assert real_probe_packet["paper_planning_eligibility"] == "not_eligible"
    assert "fixture" in real_probe_packet["reason_for_classification"]


def test_no_submit_packet_cannot_contain_broker_mutation_or_submit_instructions(
    tmp_path: Path,
) -> None:
    packet = _packet(_mixed_fixture_bars())
    blocker_csv = tmp_path / "btc_only.csv"
    _write_crypto_csv(blocker_csv, _bars("BTCUSD", _linear_prices("100", "1", 80)))
    blocker_packet = build_crypto_strategy_real_data_evidence_packet(
        blocker_csv,
        as_of=AS_OF,
    )

    assert validate_crypto_strategy_no_submit_packet(packet) == []
    assert validate_crypto_strategy_no_submit_packet(blocker_packet) == []
    assert set(REQUIRED_NO_SUBMIT_LABELS) <= set(packet["labels"])
    assert packet["paper_submit_occurred"] is False
    assert packet["broker_mutation_occurred"] is False
    assert packet["broker_read_occurred"] is False
    assert packet["live_endpoint_touched"] is False
    assert packet["credential_values_exposed"] is False
    assert packet["network_access_attempted"] is False

    actions = (
        str(packet["next_safe_operator_action"]).lower(),
        str(blocker_packet["next_safe_operator_action"]).lower(),
    )
    for forbidden in (
        "submit order",
        "place order",
        "cancel order",
        "replace order",
        "close position",
        "liquidate",
    ):
        assert all(forbidden not in action for action in actions)


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


def _multi_symbol_bars(*, row_count: int) -> tuple[CryptoEvidenceBar, ...]:
    bars: list[CryptoEvidenceBar] = []
    for index, symbol in enumerate(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS):
        start = str(Decimal("100") + Decimal(index * 25))
        bars.extend(_bars(symbol, _linear_prices(start, "1", row_count)))
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


def _write_crypto_csv(
    path: Path,
    bars: tuple[CryptoEvidenceBar, ...],
    *,
    source: str = "unit_test_local_history",
) -> None:
    lines = ["timestamp,symbol,asset_class,open,high,low,close,volume,basis,source"]
    for bar in bars:
        close = str(bar.close)
        lines.append(
            ",".join(
                (
                    bar.timestamp.isoformat(),
                    bar.symbol,
                    "crypto",
                    close,
                    close,
                    close,
                    close,
                    "1",
                    "unit_test_ohlcv",
                    source,
                )
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
