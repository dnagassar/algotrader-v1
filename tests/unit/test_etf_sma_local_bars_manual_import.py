from __future__ import annotations

import ast
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_local_bars_manual_import import (
    ETF_SMA_LOCAL_BARS_MANUAL_IMPORT_LABELS,
    EtfSmaLocalBarsManualImportConfig,
    build_etf_sma_local_bars_manual_import,
    render_etf_sma_local_bars_manual_import_json,
    write_etf_sma_local_bars_manual_import_jsonl,
)
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    load_local_daily_bars_csv,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_local_bars_manual_import.py")
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "http",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "download",
    "getenv",
    "liquidate",
    "os.getenv",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "submit_authorized",
    "submit_path_allowed",
    "paper_submit_approved",
    "broker_mutation_authorized",
    "live_authorized",
    "broker_network_access",
    "credential_access",
    "credential_access_attempted",
    "network_access_attempted",
    "broker_action_performed",
    "broker_actions_performed",
    "market_data_fetch_performed",
)


def test_valid_local_csv_and_valid_manifest_writes_canonical_and_refreshes(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_mappable_csv(
        tmp_path / "operator_evidence" / "spy_daily_vendor.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(
        tmp_path / "operator_evidence" / "spy_daily_manifest.json",
        csv_path,
        updates={"expected_schema": "daily_ohlcv_csv"},
    )
    run_log = tmp_path / "m409.jsonl"
    canonical_output = tmp_path / "canonical" / "spy_daily.csv"
    refresh_run_log = tmp_path / "m409_refresh.jsonl"

    payload = build_etf_sma_local_bars_manual_import(
        _config(
            tmp_path,
            input_csv=csv_path,
            provenance_manifest=manifest,
            run_log=run_log,
            canonical_output=canonical_output,
            refresh_run_log=refresh_run_log,
        )
    )
    write_etf_sma_local_bars_manual_import_jsonl(payload, run_log)

    assert payload["record_type"] == "etf_sma_local_bars_manual_import"
    assert payload["manual_import_state"] == "canonical_local_operator_bars_ready"
    assert payload["refresh_state"] == "backtest_evidence_refreshed"
    assert payload["performance_evidence_state"] == "post_signal_returns_evaluated"
    assert payload["usable_bar_count"] == 201
    assert payload["evaluated_return_count"] == 1
    assert payload["canonical_csv_written"] is True
    assert payload["refresh_rerun_performed"] is True
    assert payload["profit_claim"] == "none"
    assert payload["data_validation"]["schema"] == "mappable_daily_bars_csv"
    assert canonical_output.is_file()
    assert refresh_run_log.is_file()
    assert run_log.read_text(encoding="utf-8").count("\n") == 1

    canonical = load_local_daily_bars_csv(canonical_output, symbol="SPY")
    assert canonical.observed_usable_bars == 201
    assert canonical.input_sorted_by_date is True
    assert canonical.usable_bars[0].date == date(2026, 1, 1)
    assert canonical.usable_bars[-1].date == date(2026, 7, 20)

    refresh_payload = json.loads(refresh_run_log.read_text(encoding="utf-8"))
    assert refresh_payload["refresh_state"] == "backtest_evidence_refreshed"
    assert refresh_payload["candidate_daily_bars_csv"] == str(canonical_output)


def test_200_usable_bars_blocks_without_refresh_or_canonical_output(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",),
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)
    canonical_output = tmp_path / "canonical.csv"
    refresh_run_log = tmp_path / "refresh.jsonl"

    payload = build_etf_sma_local_bars_manual_import(
        _config(
            tmp_path,
            input_csv=csv_path,
            provenance_manifest=manifest,
            canonical_output=canonical_output,
            refresh_run_log=refresh_run_log,
        )
    )

    assert payload["manual_import_state"] == (
        "blocked_manual_operator_data_missing_or_invalid"
    )
    assert payload["performance_evidence_state"] == "insufficient_post_signal_returns"
    assert payload["usable_bar_count"] == 200
    assert payload["evaluated_return_count"] == 0
    assert payload["canonical_csv_written"] is False
    assert payload["refresh_rerun_performed"] is False
    assert "insufficient_usable_bars:200<201" in payload["blockers"]
    assert not canonical_output.exists()
    assert not refresh_run_log.exists()


def test_201_usable_bars_pass_and_first_evaluated_return_is_after_signal_bar(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert payload["manual_import_state"] == "canonical_local_operator_bars_ready"
    assert payload["equity_curve"][199]["exposure"] == 0
    assert payload["equity_curve"][199]["evaluated_return"] is False
    assert payload["equity_curve"][200]["exposure"] == 1
    assert payload["equity_curve"][200]["asset_return"] == "0.1"
    assert payload["equity_curve"][200]["evaluated_return"] is True
    assert payload["events"][200]["target_as_of"] == "2026-07-19"
    assert payload["evaluated_return_count"] == 1


def test_missing_manifest_blocks_with_one_valid_jsonl_artifact(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    run_log = tmp_path / "m409.jsonl"

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=None, run_log=run_log)
    )
    write_etf_sma_local_bars_manual_import_jsonl(payload, run_log)

    assert payload["manual_import_state"] == (
        "blocked_manual_operator_data_missing_or_invalid"
    )
    assert "provenance_manifest_missing" in payload["blockers"]
    assert payload["canonical_csv_written"] is False
    assert payload["refresh_rerun_performed"] is False
    assert len(run_log.read_text(encoding="utf-8").splitlines()) == 1
    assert json.loads(run_log.read_text(encoding="utf-8")) == payload


def test_manifest_path_mismatch_blocks(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        tmp_path / "operator_evidence" / "other_spy_daily_bars.csv",
    )

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert "manifest_input_csv_path_mismatch" in payload["blockers"]
    assert payload["canonical_csv_written"] is False


def test_operator_attested_false_blocks(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        csv_path,
        updates={"operator_attested": False},
    )

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert "operator_attested_not_true" in payload["blockers"]
    assert payload["manual_import_state"] == (
        "blocked_manual_operator_data_missing_or_invalid"
    )


@pytest.mark.parametrize(
    "flag_name",
    (
        "contains_synthetic_data",
        "contains_fixture_data",
        "contains_sample_data",
        "contains_test_data",
    ),
)
def test_any_generated_sample_fixture_test_flag_true_blocks(
    tmp_path,
    flag_name: str,
) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        csv_path,
        updates={flag_name: True},
    )

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert f"{flag_name}_not_false" in payload["blockers"]
    assert payload["fixture_sample_synthetic_test_data_used_as_operator_evidence"] is False


@pytest.mark.parametrize(
    ("updates", "remove", "expected_blocker"),
    (
        ({}, ("source_description",), "missing_provenance_field:source_description"),
        ({"source_type": "unknown"}, (), "ambiguous_provenance_field:source_type"),
        ({"timeframe": "weekly"}, (), "timeframe_not_daily"),
        (
            {"source_type": "synthetic"},
            (),
            "provenance_rejected_generated_sample_fixture_test_synthetic",
        ),
    ),
)
def test_ambiguous_or_missing_provenance_fields_block(
    tmp_path,
    updates: dict[str, object],
    remove: tuple[str, ...],
    expected_blocker: str,
) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        csv_path,
        updates=updates,
        remove=remove,
    )

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert expected_blocker in payload["blockers"]
    assert payload["provenance_validation"]["valid"] is False


@pytest.mark.parametrize(
    ("case_name", "expected_blocker"),
    (
        ("duplicate_dates", "duplicate_dates"),
        ("descending_dates", "date_order_not_ascending"),
    ),
)
def test_duplicate_or_descending_dates_block_without_reordering(
    tmp_path,
    case_name: str,
    expected_blocker: str,
) -> None:  # noqa: ANN001
    csv_path = _write_malformed_csv(
        tmp_path / "operator_evidence" / f"{case_name}.csv",
        case_name,
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert expected_blocker in payload["blockers"]
    assert payload["canonical_csv_written"] is False
    assert payload["data_validation"]["input_sorted_by_date"] is False


def test_non_spy_rows_block(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_malformed_csv(
        tmp_path / "operator_evidence" / "non_spy.csv",
        "non_spy_rows",
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert "non_spy_rows_present" in payload["blockers"]
    assert payload["data_validation"]["non_spy_row_count"] == 1
    assert payload["canonical_csv_written"] is False


@pytest.mark.parametrize(
    ("case_name", "expected_blocker", "expected_flag"),
    (
        ("missing_close", "missing_or_invalid_close", "missing_or_invalid_close"),
        ("non_positive_close", "non_positive_close", "non_positive_close"),
        ("non_numeric_close", "missing_or_invalid_close", "missing_or_invalid_close"),
    ),
)
def test_missing_non_positive_or_non_numeric_close_blocks(
    tmp_path,
    case_name: str,
    expected_blocker: str,
    expected_flag: str,
) -> None:  # noqa: ANN001
    csv_path = _write_malformed_csv(
        tmp_path / "operator_evidence" / f"{case_name}.csv",
        case_name,
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    assert expected_blocker in payload["blockers"]
    assert payload["data_validation"][expected_flag] is True
    assert payload["canonical_csv_written"] is False


def test_json_rendering_and_jsonl_write_are_deterministic(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",),
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)
    config = _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    payload_a = build_etf_sma_local_bars_manual_import(config)
    payload_b = build_etf_sma_local_bars_manual_import(config)
    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"

    first = render_etf_sma_local_bars_manual_import_json(payload_a)
    second = render_etf_sma_local_bars_manual_import_json(payload_b)
    write_etf_sma_local_bars_manual_import_jsonl(payload_a, output_a)
    write_etf_sma_local_bars_manual_import_jsonl(payload_b, output_b)

    assert payload_a == payload_b
    assert first == second
    assert output_a.read_bytes() == output_b.read_bytes()
    assert len(output_a.read_text(encoding="utf-8").splitlines()) == 1


def test_all_safety_booleans_are_false_and_labels_are_conservative(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_local_bars_manual_import(
        _config(tmp_path, input_csv=csv_path, provenance_manifest=manifest)
    )

    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["profit_claim"] == "none"
    assert payload["labels"] == list(ETF_SMA_LOCAL_BARS_MANUAL_IMPORT_LABELS)
    assert payload["data_provenance"]["network_access_attempted"] is False
    assert payload["data_provenance"]["credential_access_attempted"] is False
    assert payload["operator_evidence_synthetic"] is False


def test_manual_import_research_module_imports_no_broker_sdk_or_network_dependencies() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_cli_smoke_writes_manual_import_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    csv_path = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    manifest = _write_manifest(tmp_path / "manifest.json", csv_path)
    run_log = tmp_path / "m409.jsonl"
    canonical_output = tmp_path / "canonical.csv"
    refresh_run_log = tmp_path / "refresh.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("offline manual import command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            "etf-sma-local-bars-manual-import",
            "--symbol",
            "SPY",
            "--input-csv",
            str(csv_path),
            "--provenance-manifest",
            str(manifest),
            "--source-refresh-log",
            str(_write_source_refresh_log(tmp_path / "m408.jsonl")),
            "--source-backtest-log",
            str(_write_source_backtest_log(tmp_path / "m406.jsonl")),
            "--run-id",
            "unit_m409",
            "--run-log",
            str(run_log),
            "--canonical-output",
            str(canonical_output),
            "--refresh-run-log",
            str(refresh_run_log),
            "--format",
            "json",
        ]
    ) == 0

    stdout = capsys.readouterr().out
    payload = json.loads(run_log.read_text(encoding="utf-8"))
    assert json.loads(stdout) == payload
    assert payload["record_type"] == "etf_sma_local_bars_manual_import"
    assert payload["run_id"] == "unit_m409"
    assert payload["manual_import_state"] == "canonical_local_operator_bars_ready"
    assert refresh_run_log.is_file()


def _config(
    base_path: Path,
    *,
    input_csv: Path | None = None,
    provenance_manifest: Path | None = None,
    source_refresh_log: Path | None = None,
    source_backtest_log: Path | None = None,
    run_log: Path | None = None,
    canonical_output: Path | None = None,
    refresh_run_log: Path | None = None,
) -> EtfSmaLocalBarsManualImportConfig:
    return EtfSmaLocalBarsManualImportConfig(
        run_id="unit_m409",
        symbol="SPY",
        input_csv=input_csv,
        provenance_manifest=provenance_manifest,
        source_refresh_log=source_refresh_log
        or _write_source_refresh_log(base_path / "m408.jsonl"),
        source_backtest_log=source_backtest_log
        or _write_source_backtest_log(base_path / "m406.jsonl"),
        run_log=run_log or base_path / "m409.jsonl",
        canonical_output=canonical_output or base_path / "canonical.csv",
        refresh_run_log=refresh_run_log or base_path / "refresh.jsonl",
    )


def _source_safety_fields() -> dict[str, object]:
    return {
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "paper_submit_approved": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "credential_access_attempted": False,
        "network_access_attempted": False,
    }


def _write_source_refresh_log(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "record_type": "etf_sma_local_bars_canonicalization",
        "command": "etf-sma-local-bars-canonicalize",
        "run_id": "unit_m408",
        "symbol": "SPY",
        "canonicalization_state": "blocked_no_valid_extended_local_operator_bars",
        "performance_evidence_state": "insufficient_post_signal_returns",
        "usable_bar_count": 200,
        "evaluated_return_count": 0,
        "profit_claim": "none",
        **_source_safety_fields(),
    }
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_source_backtest_log(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "record_type": "etf_sma_backtest_stats",
        "command": "etf-sma-backtest-stats",
        "run_id": "unit_m406",
        "symbol": "SPY",
        "backtest_state": "blocked_insufficient_post_signal_returns",
        "performance_evidence_state": "insufficient_post_signal_returns",
        "usable_bar_count": 200,
        "evaluated_return_count": 0,
        "starting_equity": "25.00",
        "profit_claim": "none",
        **_source_safety_fields(),
    }
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_manifest(
    path: Path,
    input_csv: Path,
    *,
    updates: dict[str, object] | None = None,
    remove: tuple[str, ...] = (),
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {
        "symbol": "SPY",
        "input_csv": str(input_csv),
        "source_description": "Operator supplied local SPY daily bars",
        "source_type": "operator_supplied_local_csv",
        "operator_attested": True,
        "attested_by": "unit_operator",
        "attested_at": "2026-06-06T12:00:00+00:00",
        "data_vendor_or_origin": "manual_operator_origin",
        "acquisition_method": "manual_download",
        "contains_synthetic_data": False,
        "contains_fixture_data": False,
        "contains_sample_data": False,
        "contains_test_data": False,
        "adjustment_policy": "adjusted_close_column_supplied",
        "timeframe": "daily",
        "expected_schema": "strict_local_daily_bars_csv",
        "notes": "pytest-only manifest fixture; not operator evidence",
    }
    if updates:
        record.update(updates)
    for field in remove:
        record.pop(field, None)
    path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    return path


def _write_csv(path: Path, values: tuple[str, ...], symbol: str = "SPY") -> Path:
    start = date(2026, 1, 1)
    rows = [
        _csv_row(symbol, start + timedelta(days=index), value)
        for index, value in enumerate(values)
    ]
    return _write_csv_rows(path, rows)


def _write_mappable_csv(path: Path, values: tuple[str, ...]) -> Path:
    start = date(2026, 1, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ("Date", "Ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume")
    lines = [",".join(columns)]
    for index, value in enumerate(values):
        row = _csv_row("SPY", start + timedelta(days=index), value)
        lines.append(
            ",".join(
                (
                    row["date"],
                    row["symbol"],
                    row["open"],
                    row["high"],
                    row["low"],
                    row["close"],
                    row["adjusted_close"],
                    row["volume"],
                )
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_malformed_csv(path: Path, case_name: str) -> Path:
    values = 150 * ("100",) + 50 * ("200",) + ("220",)
    start = date(2026, 1, 1)
    rows = [
        _csv_row("SPY", start + timedelta(days=index), value)
        for index, value in enumerate(values)
    ]
    if case_name == "duplicate_dates":
        rows[-1]["date"] = rows[-2]["date"]
        return _write_csv_rows(path, rows)
    if case_name == "descending_dates":
        rows[-1], rows[-2] = rows[-2], rows[-1]
        return _write_csv_rows(path, rows)
    if case_name == "non_spy_rows":
        rows[-1]["symbol"] = "QQQ"
        return _write_csv_rows(path, rows)
    if case_name == "missing_close":
        rows[-1]["close"] = ""
        return _write_csv_rows(path, rows)
    if case_name == "non_positive_close":
        rows[-1]["close"] = "0"
        rows[-1]["adjusted_close"] = "0"
        return _write_csv_rows(path, rows)
    if case_name == "non_numeric_close":
        rows[-1]["close"] = "bad"
        return _write_csv_rows(path, rows)
    raise AssertionError(f"Unhandled malformed CSV case: {case_name}")


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    lines.extend(
        ",".join(row[column] for column in LOCAL_DAILY_BARS_CSV_COLUMNS)
        for row in rows
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _csv_row(symbol: str, day: date, price: str) -> dict[str, str]:
    value = int(price)
    high = str(value + 1)
    low = str(value - 1 if value > 1 else value)
    return {
        "symbol": symbol,
        "date": day.isoformat(),
        "open": price,
        "high": high,
        "low": low,
        "close": price,
        "adjusted_close": price,
        "volume": "1000",
    }


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


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )
