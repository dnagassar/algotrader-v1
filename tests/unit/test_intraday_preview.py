from __future__ import annotations

import ast
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from algotrader.research.intraday_preview import (
    INTRADAY_PREVIEW_LABELS,
    INTRADAY_PREVIEW_STRATEGY,
    IntradayPreviewConfig,
    build_intraday_preview_from_csv,
    write_intraday_preview_artifacts,
)
from algotrader.research.intraday_trend_probe import (
    IntradayBar,
    write_intraday_bars_csv,
)


def test_intraday_preview_reports_insufficient_history_before_sma32(
    tmp_path: Path,
) -> None:
    csv_path = write_intraday_bars_csv(
        _regular_session_bars(date(2026, 6, 1), close_start="450", step="0.10"),
        tmp_path / "spy_15m.csv",
    )

    preview = build_intraday_preview_from_csv(
        IntradayPreviewConfig(
            run_id="unit_insufficient",
            intraday_bars_csv=csv_path,
        )
    )

    assert preview["symbol"] == "SPY"
    assert preview["timeframe"] == "15m"
    assert preview["strategy"] == INTRADAY_PREVIEW_STRATEGY
    assert preview["calendar_validation_status"] == "passed"
    assert preview["accepted_session_date"] == "2026-06-01"
    assert preview["bars_used"] == 26
    assert preview["SMA8"] is not None
    assert preview["SMA32"] is None
    assert preview["posture"] == "insufficient_history"
    assert preview["preview_decision"] == "insufficient_history"
    assert preview["blocker_status"] == "insufficient_history"


def test_intraday_preview_reports_risk_on_preview_only(tmp_path: Path) -> None:
    csv_path = write_intraday_bars_csv(
        (
            *_regular_session_bars(date(2026, 6, 1), close_start="450", step="0.10"),
            *_regular_session_bars(date(2026, 6, 2), close_start="460", step="0.10"),
        ),
        tmp_path / "spy_15m.csv",
    )

    preview = build_intraday_preview_from_csv(
        IntradayPreviewConfig(run_id="unit_risk_on", intraday_bars_csv=csv_path)
    )

    assert preview["calendar_validation_status"] == "passed"
    assert preview["accepted_session_date"] == "2026-06-02"
    assert preview["bars_used"] == 52
    assert Decimal(str(preview["SMA8"])) > Decimal(str(preview["SMA32"]))
    assert preview["posture"] == "risk_on"
    assert preview["preview_decision"] == "risk_on_preview_only"
    assert preview["blocker_status"] == "none"
    assert preview["broker_state_mode"] == "not_observed_for_intraday"


def test_intraday_preview_reports_risk_off_preview_only(tmp_path: Path) -> None:
    csv_path = write_intraday_bars_csv(
        (
            *_regular_session_bars(date(2026, 6, 1), close_start="460", step="-0.10"),
            *_regular_session_bars(date(2026, 6, 2), close_start="450", step="-0.10"),
        ),
        tmp_path / "spy_15m.csv",
    )

    preview = build_intraday_preview_from_csv(
        IntradayPreviewConfig(run_id="unit_risk_off", intraday_bars_csv=csv_path)
    )

    assert preview["calendar_validation_status"] == "passed"
    assert Decimal(str(preview["SMA8"])) <= Decimal(str(preview["SMA32"]))
    assert preview["posture"] == "risk_off"
    assert preview["preview_decision"] == "risk_off_preview_only"
    assert preview["blocker_status"] == "none"


def test_intraday_preview_blocks_calendar_invalid_input(tmp_path: Path) -> None:
    csv_path = write_intraday_bars_csv(
        _regular_session_bars(date(2026, 6, 19), close_start="450", step="0.10"),
        tmp_path / "spy_holiday.csv",
    )

    preview = build_intraday_preview_from_csv(
        IntradayPreviewConfig(run_id="unit_calendar_block", intraday_bars_csv=csv_path)
    )

    assert preview["calendar_validation_status"] == "failed"
    assert preview["preview_decision"] == "blocked/calendar_validation_failed"
    assert preview["blocker_status"] == "calendar_validation_failed"
    assert preview["bars_used"] == 0
    assert preview["broker_access_attempted"] is False
    assert preview["paper_submit_attempted"] is False


def test_intraday_preview_blocks_stale_and_missing_data(tmp_path: Path) -> None:
    csv_path = write_intraday_bars_csv(
        (
            *_regular_session_bars(date(2026, 6, 1), close_start="450", step="0.10"),
            *_regular_session_bars(date(2026, 6, 2), close_start="460", step="0.10"),
        ),
        tmp_path / "spy_15m.csv",
    )

    stale = build_intraday_preview_from_csv(
        IntradayPreviewConfig(
            run_id="unit_stale",
            intraday_bars_csv=csv_path,
            expected_accepted_session_date="2026-06-03",
        )
    )
    missing = build_intraday_preview_from_csv(
        IntradayPreviewConfig(
            run_id="unit_missing",
            intraday_bars_csv=tmp_path / "missing.csv",
        )
    )

    assert stale["calendar_validation_status"] == "passed"
    assert stale["data_availability_status"] == "stale"
    assert stale["preview_decision"] == "blocked/intraday_data_unavailable"
    assert stale["blocker_status"] == "stale_intraday_data"
    assert missing["calendar_validation_status"] == "not_run_missing_data"
    assert missing["data_availability_status"] == "missing"
    assert missing["preview_decision"] == "blocked/intraday_data_unavailable"
    assert missing["blocker_status"] == "intraday_data_unavailable"


def test_intraday_preview_artifacts_contain_required_labels(tmp_path: Path) -> None:
    csv_path = write_intraday_bars_csv(
        (
            *_regular_session_bars(date(2026, 6, 1), close_start="450", step="0.10"),
            *_regular_session_bars(date(2026, 6, 2), close_start="460", step="0.10"),
        ),
        tmp_path / "spy_15m.csv",
    )
    preview = build_intraday_preview_from_csv(
        IntradayPreviewConfig(run_id="unit_artifacts", intraday_bars_csv=csv_path)
    )

    paths = write_intraday_preview_artifacts(preview, tmp_path / "artifacts")
    latest = json.loads(paths["latest"].read_text(encoding="utf-8"))
    record = json.loads(paths["record"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    summary = paths["summary"].read_text(encoding="utf-8")

    assert set(paths) == {"summary", "record", "manifest", "latest"}
    assert set(INTRADAY_PREVIEW_LABELS).issubset(set(latest["labels"]))
    assert set(INTRADAY_PREVIEW_LABELS).issubset(set(record["labels"]))
    assert set(INTRADAY_PREVIEW_LABELS).issubset(set(manifest["labels"]))
    for label in INTRADAY_PREVIEW_LABELS:
        assert label in summary
    assert manifest["artifact_hashes"]


def test_intraday_preview_safety_flags_remain_false(tmp_path: Path) -> None:
    csv_path = write_intraday_bars_csv(
        (
            *_regular_session_bars(date(2026, 6, 1), close_start="450", step="0.10"),
            *_regular_session_bars(date(2026, 6, 2), close_start="460", step="0.10"),
        ),
        tmp_path / "spy_15m.csv",
    )

    preview = build_intraday_preview_from_csv(
        IntradayPreviewConfig(run_id="unit_safety", intraday_bars_csv=csv_path)
    )

    assert preview["broker_access_attempted"] is False
    assert preview["broker_mutation_attempted"] is False
    assert preview["paper_submit_attempted"] is False
    assert preview["live_trading_attempted"] is False
    assert preview["paper_submit_authorized"] is False
    assert preview["paper_submit_authorization_status"] == "not_authorized"
    assert preview["profit_claim"] == "none"


def test_intraday_preview_module_and_runner_have_no_broker_or_network_imports() -> None:
    paths = (
        Path("src/algotrader/research/intraday_preview.py"),
        Path("scripts/research/run_spy_intraday_preview.py"),
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


def _regular_session_bars(
    session_date: date,
    *,
    close_start: str,
    step: str,
) -> tuple[IntradayBar, ...]:
    start = datetime.combine(
        session_date,
        time(9, 30),
        tzinfo=ZoneInfo("America/New_York"),
    )
    close = Decimal(close_start)
    delta = Decimal(step)
    bars: list[IntradayBar] = []
    for index in range(26):
        open_price = close
        close = close + delta
        high = max(open_price, close) + Decimal("1")
        low = min(open_price, close) - Decimal("1")
        bars.append(
            IntradayBar(
                symbol="SPY",
                timestamp=start + timedelta(minutes=15 * index),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000 + index,
            )
        )
    return tuple(bars)


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
