from __future__ import annotations

import ast
import hashlib
import json
import socket
import subprocess
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from algotrader.errors import ValidationError
from algotrader.research.intraday_evidence import (
    INTRADAY_EVIDENCE_LABELS,
    INTRADAY_EVIDENCE_STRATEGY,
    IntradayEvidenceConfig,
    build_intraday_evidence_from_csv,
    write_intraday_evidence_artifacts,
)
from algotrader.research.intraday_trend_probe import (
    INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
    LOCAL_INTRADAY_BARS_CSV_COLUMNS,
    IntradayBar,
    load_local_intraday_bars_csv,
    validate_regular_session_intraday_bars,
    write_intraday_bars_csv,
)


def test_intraday_evidence_builds_multi_session_packet(tmp_path: Path) -> None:
    csv_path = _calendar_valid_csv(tmp_path, _session_dates(3))

    evidence = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="unit_multi", intraday_bars_csv=csv_path)
    )

    integrity = evidence["data_integrity"]
    behavior = evidence["signal_behavior"]
    diagnostics = evidence["directional_diagnostics"]
    assert evidence["strategy"] == INTRADAY_EVIDENCE_STRATEGY
    assert evidence["evaluation_status"] == "complete_signal_evidence"
    assert evidence["execution_semantics_status"] == "not_defined"
    assert integrity["session_count"] == 3
    assert integrity["total_bars"] == 78
    assert integrity["usable_bars_after_sma_warmup"] == 47
    assert integrity["duplicate_count"] == 0
    assert integrity["invalid_session_count"] == 0
    assert behavior["risk_on_bar_count"] + behavior["risk_off_bar_count"] == 47
    assert diagnostics["next_bar"]["global_by_posture"]["risk_on"]["sample_count"] > 0
    assert diagnostics["next_four_bar"]["exclusions"]["future_bar_exclusion_count"] > 0


def test_intraday_evidence_artifacts_are_stable_on_repeated_runs(
    tmp_path: Path,
) -> None:
    csv_path = _calendar_valid_csv(tmp_path, _session_dates(4))
    evidence = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="unit_stable", intraday_bars_csv=csv_path)
    )
    output_root = tmp_path / "artifacts"

    paths = write_intraday_evidence_artifacts(evidence, output_root)
    first_contents = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    second_paths = write_intraday_evidence_artifacts(evidence, output_root)
    second_contents = {
        name: path.read_text(encoding="utf-8") for name, path in second_paths.items()
    }

    assert first_contents == second_contents
    assert set(paths) == {"summary", "evidence", "manifest"}


def test_intraday_evidence_fails_without_calendar_validation_evidence(
    tmp_path: Path,
) -> None:
    csv_path = write_intraday_bars_csv(
        _regular_session_bars(date(2026, 6, 1)),
        tmp_path / "spy_15m.csv",
    )

    with pytest.raises(ValidationError, match="calendar-validation evidence"):
        build_intraday_evidence_from_csv(
            IntradayEvidenceConfig(run_id="unit_missing", intraday_bars_csv=csv_path)
        )


def test_intraday_evidence_rejects_duplicate_and_unsorted_timestamps(
    tmp_path: Path,
) -> None:
    duplicate_path = _write_intraday_csv(
        tmp_path / "duplicate.csv",
        [
            _row("2026-06-01T13:30:00+00:00", "450"),
            _row("2026-06-01T13:30:00+00:00", "451"),
        ],
    )
    unsorted_path = _write_intraday_csv(
        tmp_path / "unsorted.csv",
        [
            _row("2026-06-01T13:45:00+00:00", "451"),
            _row("2026-06-01T13:30:00+00:00", "450"),
        ],
    )

    with pytest.raises(ValidationError, match="duplicates timestamp"):
        build_intraday_evidence_from_csv(
            IntradayEvidenceConfig(run_id="unit_duplicate", intraday_bars_csv=duplicate_path)
        )
    with pytest.raises(ValidationError, match="sorted by timestamp"):
        build_intraday_evidence_from_csv(
            IntradayEvidenceConfig(run_id="unit_unsorted", intraday_bars_csv=unsorted_path)
        )


def test_intraday_evidence_tracks_sma_warmup_and_insufficient_history(
    tmp_path: Path,
) -> None:
    csv_path = _calendar_valid_csv(tmp_path, (date(2026, 6, 1),))

    evidence = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="unit_warmup", intraday_bars_csv=csv_path)
    )

    assert evidence["evaluation_status"] == "insufficient_history"
    assert evidence["data_integrity"]["usable_bars_after_sma_warmup"] == 0
    assert evidence["signal_behavior"]["risk_on_bar_count"] == 0
    assert evidence["signal_behavior"]["risk_off_bar_count"] == 0
    assert {
        row["posture"] for row in evidence["signal_history"]
    } == {"insufficient_history"}


def test_intraday_evidence_signals_have_no_lookahead(tmp_path: Path) -> None:
    dates = _session_dates(4)
    baseline_csv = _calendar_valid_csv(tmp_path / "baseline", dates)
    changed_csv = _calendar_valid_csv(
        tmp_path / "changed",
        dates,
        close_overrides={85: Decimal("999")},
    )

    baseline = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="baseline", intraday_bars_csv=baseline_csv)
    )
    changed = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="changed", intraday_bars_csv=changed_csv)
    )

    assert baseline["signal_history"][:85] == changed["signal_history"][:85]


def test_intraday_evidence_counts_session_and_dataset_forward_exclusions(
    tmp_path: Path,
) -> None:
    csv_path = _calendar_valid_csv(tmp_path, _session_dates(3))

    evidence = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="unit_boundaries", intraday_bars_csv=csv_path)
    )

    next_bar_exclusions = evidence["directional_diagnostics"]["next_bar"]["exclusions"]
    next_four_exclusions = evidence["directional_diagnostics"]["next_four_bar"][
        "exclusions"
    ]
    assert next_bar_exclusions["by_reason"]["session_boundary"] == 1
    assert next_bar_exclusions["by_reason"]["dataset_boundary"] == 1
    assert next_bar_exclusions["future_bar_exclusion_count"] == 2
    assert next_four_exclusions["by_reason"]["session_boundary"] == 4
    assert next_four_exclusions["by_reason"]["dataset_boundary"] == 4


def test_intraday_evidence_partitions_chronological_halves_by_session(
    tmp_path: Path,
) -> None:
    csv_path = _calendar_valid_csv(tmp_path, _session_dates(5))

    evidence = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="unit_halves", intraday_bars_csv=csv_path)
    )
    halves = evidence["directional_diagnostics"][
        "chronological_first_half_vs_second_half"
    ]

    assert halves["first_half"]["session_count"] == 2
    assert halves["first_half"]["sessions"] == ["2026-06-01", "2026-06-02"]
    assert halves["second_half"]["session_count"] == 3
    assert halves["second_half"]["sessions"] == [
        "2026-06-03",
        "2026-06-04",
        "2026-06-05",
    ]


def test_intraday_evidence_required_labels_and_safety_flags(
    tmp_path: Path,
) -> None:
    csv_path = _calendar_valid_csv(tmp_path, _session_dates(3))

    evidence = build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="unit_safety", intraday_bars_csv=csv_path)
    )

    assert set(INTRADAY_EVIDENCE_LABELS).issubset(set(evidence["labels"]))
    assert evidence["paper_submit_authorized"] is False
    assert evidence["broker_access"] is False
    assert evidence["broker_mutation"] is False
    assert evidence["live_trading"] is False
    assert evidence["network_access"] is False
    assert evidence["market_data_fetch"] is False
    assert evidence["tiingo_fetch"] is False
    assert evidence["profit_claim"] == "none"


def test_intraday_evidence_build_does_not_touch_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = _calendar_valid_csv(tmp_path, _session_dates(3))
    calls: list[object] = []

    def blocked_socket(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        raise AssertionError("network socket access is forbidden")

    monkeypatch.setattr(socket, "socket", blocked_socket)
    build_intraday_evidence_from_csv(
        IntradayEvidenceConfig(run_id="unit_no_network", intraday_bars_csv=csv_path)
    )

    assert calls == []


def test_intraday_evidence_module_and_runner_have_no_network_broker_or_execution_imports() -> None:
    paths = (
        Path("src/algotrader/research/intraday_evidence.py"),
        Path("scripts/research/run_spy_intraday_evidence.py"),
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


def test_intraday_evidence_runs_artifacts_are_gitignored() -> None:
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            "-q",
            "runs/intraday_evidence/v1_84/intraday_evidence.json",
        ],
        check=False,
        cwd=Path.cwd(),
    )

    assert result.returncode == 0


def _calendar_valid_csv(
    root: Path,
    session_dates: tuple[date, ...],
    *,
    close_overrides: dict[int, Decimal] | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    bars: list[IntradayBar] = []
    close = Decimal("450")
    overrides = close_overrides or {}
    global_index = 0
    for session_date in session_dates:
        for bar in _regular_session_bars(session_date, close_start=close):
            close = Decimal(str(bar.close))
            if global_index in overrides:
                close = overrides[global_index]
                bar = IntradayBar(
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    open=close,
                    high=close + Decimal("1"),
                    low=close - Decimal("1"),
                    close=close,
                    volume=bar.volume,
                )
            bars.append(bar)
            global_index += 1
    csv_path = write_intraday_bars_csv(bars, root / "spy_15m.csv")
    _write_validation_artifacts(csv_path)
    return csv_path


def _write_validation_artifacts(csv_path: Path) -> None:
    csv_result = load_local_intraday_bars_csv(csv_path, symbol="SPY")
    validation = validate_regular_session_intraday_bars(csv_result.bars)
    report_path = csv_path.parent / "calendar_validation_report.json"
    report_path.write_text(
        json.dumps(validation.to_report(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "record_type": "spy_intraday_trend_probe_manifest",
        "schema_version": "1",
        "run_id": "unit_source_validation",
        "symbol": "SPY",
        "data_source_kind": "local_intraday_csv",
        "source_path": str(csv_path),
        "source_timeframe": "15m",
        "bar_count": csv_result.observed_bar_count,
        "labels": [
            "research_only",
            "signal_evaluation_only",
            "not_live_authorized",
            "no_broker_access",
            "no_paper_submit",
            "profit_claim=none",
            INTRADAY_SOURCE_CALENDAR_VALIDATED_LABEL,
        ],
        "market_data_fetch_performed": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_authorized": False,
        "artifact_hashes": [
            {"path": str(csv_path), "sha256": _sha256(csv_path)},
            {"path": str(report_path), "sha256": _sha256(report_path)},
        ],
    }
    (csv_path.parent / "intraday_probe_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _regular_session_bars(
    session_date: date,
    *,
    close_start: Decimal = Decimal("450"),
) -> tuple[IntradayBar, ...]:
    start = datetime.combine(
        session_date,
        time(9, 30),
        tzinfo=ZoneInfo("America/New_York"),
    )
    close = close_start
    bars: list[IntradayBar] = []
    for index in range(26):
        step = Decimal("0.15") if index % 7 not in (5, 6) else Decimal("-0.08")
        open_price = close
        close = close + step
        bars.append(
            IntradayBar(
                symbol="SPY",
                timestamp=start + timedelta(minutes=15 * index),
                open=open_price,
                high=max(open_price, close) + Decimal("1"),
                low=min(open_price, close) - Decimal("1"),
                close=close,
                volume=1000 + index,
            )
        )
    return tuple(bars)


def _session_dates(count: int) -> tuple[date, ...]:
    all_dates = (
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 3),
        date(2026, 6, 4),
        date(2026, 6, 5),
    )
    return all_dates[:count]


def _write_intraday_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    lines = [",".join(LOCAL_INTRADAY_BARS_CSV_COLUMNS)]
    lines.extend(
        ",".join(row[column] for column in LOCAL_INTRADAY_BARS_CSV_COLUMNS)
        for row in rows
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _row(timestamp: str, close: str) -> dict[str, str]:
    parsed_close = Decimal(close)
    return {
        "symbol": "SPY",
        "timestamp": timestamp,
        "open": close,
        "high": str(parsed_close + Decimal("1")),
        "low": str(parsed_close - Decimal("1")),
        "close": close,
        "volume": "1000",
    }


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
