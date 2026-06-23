from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.intraday_trend_probe import (
    INTRADAY_PROBE_LABELS,
    LOCAL_INTRADAY_BARS_CSV_COLUMNS,
    IntradayBar,
    IntradayTrendCandidate,
    IntradayTrendProbeConfig,
    build_intraday_trend_probe_from_csv,
    evaluate_intraday_trend_candidate,
    load_local_intraday_bars_csv,
    write_intraday_probe_artifacts,
    write_sample_spy_intraday_fixture,
)


def test_load_local_intraday_bars_normalizes_and_sorts_requested_spy_rows(
    tmp_path: Path,
) -> None:
    csv_path = _write_intraday_csv(
        tmp_path / "spy_15m.csv",
        [
            _row("QQQ", "2026-06-01T13:30:00+00:00", "100"),
            _row("spy", "2026-06-01T13:45:00-00:00", "451"),
            _row("SPY", "2026-06-01T13:30:00+00:00", "450"),
        ],
    )

    result = load_local_intraday_bars_csv(
        csv_path,
        symbol="SPY",
        source_timeframe_minutes=15,
    )

    assert result.total_row_count == 3
    assert result.matching_symbol_row_count == 2
    assert result.ignored_wrong_symbol_row_count == 1
    assert result.input_sorted_by_timestamp is False
    assert [bar.symbol for bar in result.bars] == ["SPY", "SPY"]
    assert [bar.timestamp_text for bar in result.bars] == [
        "2026-06-01T13:30:00+00:00",
        "2026-06-01T13:45:00+00:00",
    ]


def test_load_local_intraday_bars_rejects_duplicate_spy_timestamps(
    tmp_path: Path,
) -> None:
    csv_path = _write_intraday_csv(
        tmp_path / "duplicate_spy_15m.csv",
        [
            _row("SPY", "2026-06-01T13:30:00+00:00", "450"),
            _row("SPY", "2026-06-01T13:30:00+00:00", "451"),
        ],
    )

    with pytest.raises(ValidationError, match="duplicates timestamp"):
        load_local_intraday_bars_csv(csv_path, symbol="SPY")


def test_load_local_intraday_bars_rejects_missing_ohlcv_column(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "missing_volume.csv"
    csv_path.write_text(
        "symbol,timestamp,open,high,low,close\n"
        "SPY,2026-06-01T13:30:00+00:00,450,451,449,450\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="volume"):
        load_local_intraday_bars_csv(csv_path, symbol="SPY")


def test_load_local_intraday_bars_rejects_missing_ohlcv_value(
    tmp_path: Path,
) -> None:
    csv_path = _write_intraday_csv(
        tmp_path / "missing_close.csv",
        [
            {
                **_row("SPY", "2026-06-01T13:30:00+00:00", "450"),
                "close": "",
            }
        ],
    )

    with pytest.raises(ValidationError, match="close must be a non-empty string"):
        load_local_intraday_bars_csv(csv_path, symbol="SPY")


def test_intraday_sma_signal_generation_uses_fast_above_slow_rule() -> None:
    candidate = IntradayTrendCandidate("test_15m_sma_1_2", 15, 1, 2)

    result = evaluate_intraday_trend_candidate(
        _bars_from_closes("10", "20", "15", "30"),
        candidate,
        slippage_bps="10",
    )

    assert [row["posture"] for row in result["signal_history"]] == [
        "insufficient_history",
        "risk_on",
        "risk_off",
        "risk_on",
    ]
    assert [row["target_exposure"] for row in result["signal_history"]] == [
        0,
        1,
        0,
        1,
    ]


def test_intraday_turnover_flip_and_slippage_metrics_are_deterministic() -> None:
    candidate = IntradayTrendCandidate("test_15m_sma_1_2", 15, 1, 2)

    result = evaluate_intraday_trend_candidate(
        _bars_from_closes("10", "20", "15", "30"),
        candidate,
        slippage_bps="10",
    )
    metrics = result["metrics"]

    assert metrics["signal_flips"] == 2
    assert metrics["exposure_change_count"] == 2
    assert metrics["rough_turnover"] == "2"
    assert metrics["average_holding_period_bars"] == "1"
    assert metrics["average_holding_period_hours"] == "0.25"
    assert metrics["gross_return"] == "-0.25"
    assert metrics["slippage_adjusted_return"] == "-0.25149925"
    assert metrics["slippage_cost_return_drag"] == "0.00149925"
    assert metrics["buy_and_hold_return"] == "2"
    assert metrics["max_drawdown"] == "0.25149925"
    assert Decimal(str(metrics["exposure_fraction"])) == Decimal(1) / Decimal(3)


def test_intraday_probe_artifacts_include_required_labels_and_safety_fields(
    tmp_path: Path,
) -> None:
    source_csv = write_sample_spy_intraday_fixture(tmp_path / "spy_fixture.csv")
    build = build_intraday_trend_probe_from_csv(
        IntradayTrendProbeConfig(
            run_id="unit_intraday_probe",
            intraday_bars_csv=source_csv,
            data_source_kind="deterministic_fixture",
        )
    )

    paths = write_intraday_probe_artifacts(build, tmp_path / "artifacts")
    results = json.loads(paths["results"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

    assert set(INTRADAY_PROBE_LABELS).issubset(set(results["labels"]))
    assert set(INTRADAY_PROBE_LABELS).issubset(set(manifest["labels"]))
    assert results["decision_quality"] == "fixture_behavior_only"
    assert results["recommendation"] == "keep_researching"
    assert results["market_data_fetch_performed"] is False
    assert results["network_access_attempted"] is False
    assert results["broker_access_performed"] is False
    assert results["broker_mutation_performed"] is False
    assert results["paper_submit_authorized"] is False
    assert results["source"]["bar_count"] == 130
    assert results["candidate_results"][0]["bar_count"] == 130
    assert results["candidate_results"][1]["bar_count"] == 65
    assert paths["normalized_input"].is_file()
    assert manifest["data_source_kind"] == "deterministic_fixture"
    assert manifest["market_data_fetch_performed"] is False
    assert manifest["broker_access_performed"] is False


def test_intraday_probe_module_has_no_broker_or_network_imports() -> None:
    path = Path("src/algotrader/research/intraday_trend_probe.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden_prefixes = (
        "aiohttp",
        "alpaca",
        "alpaca_trade_api",
        "algotrader.execution",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )

    violations = [
        f"{path}:{node.lineno}: forbidden import {module_name}"
        for node in ast.walk(tree)
        for module_name in _imported_modules(node)
        if any(
            module_name == prefix or module_name.startswith(f"{prefix}.")
            for prefix in forbidden_prefixes
        )
    ]

    assert violations == []


def _write_intraday_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(LOCAL_INTRADAY_BARS_CSV_COLUMNS)]
    lines.extend(",".join(row[column] for column in LOCAL_INTRADAY_BARS_CSV_COLUMNS) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _row(symbol: str, timestamp: str, close: str) -> dict[str, str]:
    parsed_close = Decimal(close)
    return {
        "symbol": symbol,
        "timestamp": timestamp,
        "open": str(parsed_close),
        "high": str(parsed_close + Decimal("1")),
        "low": str(parsed_close - Decimal("1")),
        "close": close,
        "volume": "1000",
    }


def _bars_from_closes(*closes: str) -> tuple[IntradayBar, ...]:
    start = datetime(2026, 6, 1, 13, 30, tzinfo=UTC)
    return tuple(
        IntradayBar(
            symbol="SPY",
            timestamp=start + timedelta(minutes=15 * index),
            open=close,
            high=str(Decimal(close) + Decimal("1")),
            low=str(Decimal(close) - Decimal("1")),
            close=close,
            volume=1000,
        )
        for index, close in enumerate(closes)
    )


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
