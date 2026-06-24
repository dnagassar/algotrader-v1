from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from algotrader.errors import ValidationError
from algotrader.research.intraday_trend_probe import (
    INTRADAY_PROBE_LABELS,
    INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
    LOCAL_INTRADAY_BARS_CSV_COLUMNS,
    IntradayBar,
    IntradayTrendCandidate,
    IntradayTrendProbeConfig,
    build_intraday_trend_probe_from_csv,
    evaluate_intraday_trend_candidate,
    load_local_intraday_bars_csv,
    validate_regular_session_intraday_bars,
    write_calendar_validation_report,
    write_intraday_bars_csv,
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


def test_calendar_validation_flags_known_market_holiday_session() -> None:
    result = validate_regular_session_intraday_bars(
        _regular_session_bars(date(2026, 5, 25)),
        source_timeframe_minutes=15,
    )

    assert result.accepted_bars == ()
    assert result.rejected_bar_count == 26
    assert result.rejected_sessions[0]["date"] == "2026-05-25"
    assert _reason_codes(result.rejected_sessions[0]) == ["market_holiday"]


def test_calendar_validation_excludes_holiday_and_keeps_regular_session() -> None:
    result = validate_regular_session_intraday_bars(
        (
            *_regular_session_bars(date(2026, 5, 22), close_start="450"),
            *_regular_session_bars(date(2026, 5, 25), close_start="500"),
        ),
        source_timeframe_minutes=15,
    )

    assert len(result.accepted_bars) == 26
    assert result.accepted_sessions[0]["date"] == "2026-05-22"
    assert result.rejected_sessions[0]["date"] == "2026-05-25"
    assert result.to_report()["source_calendar_label"] == (
        INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL
    )


def test_calendar_validation_uses_new_york_regular_session_boundaries() -> None:
    result = validate_regular_session_intraday_bars(
        _regular_session_bars(date(2026, 6, 1)),
        source_timeframe_minutes=15,
    )

    assert result.accepted_sessions[0]["start_timestamp"] == (
        "2026-06-01T13:30:00+00:00"
    )
    assert result.accepted_sessions[0]["end_timestamp"] == (
        "2026-06-01T19:45:00+00:00"
    )
    assert result.accepted_sessions[0]["observed_start_time"] == "09:30"
    assert result.accepted_sessions[0]["observed_end_time"] == "15:45"


def test_calendar_validation_rejects_off_boundary_15m_bar() -> None:
    bars = list(_regular_session_bars(date(2026, 6, 1)))
    bad_bar = bars[3]
    bars[3] = IntradayBar(
        symbol=bad_bar.symbol,
        timestamp=bad_bar.timestamp + timedelta(minutes=1),
        open=bad_bar.open,
        high=bad_bar.high,
        low=bad_bar.low,
        close=bad_bar.close,
        volume=bad_bar.volume,
    )

    result = validate_regular_session_intraday_bars(
        tuple(bars),
        source_timeframe_minutes=15,
    )

    assert result.accepted_bars == ()
    assert "invalid_bar_boundary" in _reason_codes(result.rejected_sessions[0])


def test_calendar_validation_rejects_duplicate_timestamps() -> None:
    first_bar = _regular_session_bars(date(2026, 6, 1))[0]

    with pytest.raises(ValidationError, match="duplicate timestamp"):
        validate_regular_session_intraday_bars(
            (first_bar, first_bar),
            source_timeframe_minutes=15,
        )


def test_calendar_validation_detects_missing_regular_session_timestamp() -> None:
    bars = tuple(
        bar
        for index, bar in enumerate(_regular_session_bars(date(2026, 6, 1)))
        if index != 5
    )

    result = validate_regular_session_intraday_bars(
        bars,
        source_timeframe_minutes=15,
    )

    assert result.accepted_bars == ()
    assert "missing_timestamps" in _reason_codes(result.rejected_sessions[0])
    missing_reason = _reason_by_code(result.rejected_sessions[0], "missing_timestamps")
    assert missing_reason["missing_timestamps"] == ["10:45"]


def test_calendar_valid_probe_metrics_use_only_accepted_sessions(
    tmp_path: Path,
) -> None:
    mixed_csv = write_intraday_bars_csv(
        (
            *_regular_session_bars(date(2026, 6, 18), close_start="450"),
            *_regular_session_bars(date(2026, 6, 19), close_start="900"),
        ),
        tmp_path / "mixed.csv",
    )
    csv_result = load_local_intraday_bars_csv(mixed_csv, symbol="SPY")
    validation = validate_regular_session_intraday_bars(csv_result.bars)
    accepted_csv = write_intraday_bars_csv(
        validation.accepted_bars,
        tmp_path / "accepted.csv",
    )

    build = build_intraday_trend_probe_from_csv(
        IntradayTrendProbeConfig(
            run_id="calendar_valid_metrics",
            intraday_bars_csv=accepted_csv,
            candidates=(IntradayTrendCandidate("test_15m_sma_1_2", 15, 1, 2),),
            source_calendar_label=INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
            calendar_validation=validation.to_report(),
        )
    )

    result = build.payload["candidate_results"][0]
    assert build.payload["source"]["bar_count"] == 26
    assert result["bar_count"] == 26
    assert result["end_timestamp"] == "2026-06-18T19:45:00+00:00"


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


def test_calendar_valid_artifacts_include_rejected_session_reasons(
    tmp_path: Path,
) -> None:
    mixed_csv = write_intraday_bars_csv(
        (
            *_regular_session_bars(date(2026, 6, 18), close_start="450"),
            *_regular_session_bars(date(2026, 6, 19), close_start="500"),
        ),
        tmp_path / "mixed.csv",
    )
    csv_result = load_local_intraday_bars_csv(mixed_csv, symbol="SPY")
    validation = validate_regular_session_intraday_bars(csv_result.bars)
    report_path = write_calendar_validation_report(
        validation,
        tmp_path / "calendar_validation_report.json",
    )
    accepted_csv = write_intraday_bars_csv(
        validation.accepted_bars,
        tmp_path / "accepted.csv",
    )
    build = build_intraday_trend_probe_from_csv(
        IntradayTrendProbeConfig(
            run_id="calendar_valid_artifacts",
            intraday_bars_csv=accepted_csv,
            source_calendar_label=INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
            calendar_validation=validation.to_report(),
        )
    )

    paths = write_intraday_probe_artifacts(
        build,
        tmp_path / "artifacts",
        normalized_filename="normalized_spy_intraday_15m_calendar_valid.csv",
        extra_artifact_paths=(report_path,),
    )
    results = json.loads(paths["results"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL in results["labels"]
    assert INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL in manifest["labels"]
    assert results["calendar_validation"]["rejected_sessions"][0]["date"] == (
        "2026-06-19"
    )
    assert _reason_codes(results["calendar_validation"]["rejected_sessions"][0]) == [
        "market_holiday"
    ]
    assert report["rejected_sessions"][0]["date"] == "2026-06-19"
    assert any(
        item["path"].endswith("calendar_validation_report.json")
        for item in manifest["artifact_hashes"]
    )
    assert paths["normalized_input"].name == (
        "normalized_spy_intraday_15m_calendar_valid.csv"
    )


def test_intraday_probe_module_has_no_broker_or_network_imports() -> None:
    paths = (
        Path("src/algotrader/research/intraday_trend_probe.py"),
        Path("scripts/research/run_spy_intraday_probe.py"),
    )
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
        for path in paths
        for node in ast.walk(
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        )
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


def _regular_session_bars(
    session_date: date,
    *,
    close_start: str = "450",
) -> tuple[IntradayBar, ...]:
    start = datetime.combine(
        session_date,
        time(9, 30),
        tzinfo=ZoneInfo("America/New_York"),
    )
    close = Decimal(close_start)
    bars: list[IntradayBar] = []
    for index in range(26):
        open_price = close
        close = close + Decimal("0.1")
        bars.append(
            IntradayBar(
                symbol="SPY",
                timestamp=start + timedelta(minutes=15 * index),
                open=open_price,
                high=close + Decimal("1"),
                low=open_price - Decimal("1"),
                close=close,
                volume=1000 + index,
            )
        )
    return tuple(bars)


def _reason_codes(session: object) -> list[str]:
    return [
        str(reason.get("code", ""))
        for reason in session.get("reasons", [])
        if isinstance(reason, dict)
    ]


def _reason_by_code(session: object, code: str) -> dict[str, object]:
    for reason in session.get("reasons", []):
        if isinstance(reason, dict) and reason.get("code") == code:
            return reason
    raise AssertionError(f"missing reason {code}")


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
