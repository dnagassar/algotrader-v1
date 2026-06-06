from __future__ import annotations

import ast
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_local_bars_canonicalization import (
    ETF_SMA_LOCAL_BARS_CANONICALIZATION_LABELS,
    EtfSmaLocalBarsCanonicalizationConfig,
    build_etf_sma_local_bars_canonicalization,
    render_etf_sma_local_bars_canonicalization_json,
    write_etf_sma_local_bars_canonicalization_jsonl,
)
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    load_local_daily_bars_csv,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_local_bars_canonicalization.py")
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


def test_accepts_strict_201_plus_local_operator_csv_and_writes_canonical(
    tmp_path,
) -> None:  # noqa: ANN001
    source = _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    run_log = tmp_path / "m408.jsonl"
    canonical_output = tmp_path / "canonical" / "spy_daily.csv"

    payload = build_etf_sma_local_bars_canonicalization(
        _config(
            tmp_path,
            source_refresh_log=_write_source_refresh_log(tmp_path / "m407.jsonl"),
            run_log=run_log,
            canonical_output=canonical_output,
        )
    )
    write_etf_sma_local_bars_canonicalization_jsonl(payload, run_log)

    assert payload["record_type"] == "etf_sma_local_bars_canonicalization"
    assert payload["canonicalization_state"] == "canonicalized_strict_local_operator_bars"
    assert payload["performance_evidence_state"] == "local_operator_bars_ready_for_refresh"
    assert payload["accepted_source"] == str(source.relative_to(tmp_path))
    assert payload["accepted_source_is_real_local_operator_data"] is True
    assert payload["canonical_output_written"] is True
    assert payload["usable_bar_count"] == 201
    assert payload["minimum_required_usable_bars"] == 201
    assert payload["evaluated_return_count"] == 1
    assert payload["profit_claim"] == "none"
    assert canonical_output.is_file()
    assert run_log.read_text(encoding="utf-8").count("\n") == 1

    canonical = load_local_daily_bars_csv(canonical_output, symbol="SPY")
    assert canonical.observed_usable_bars == 201
    assert canonical.input_sorted_by_date is True
    assert canonical.usable_bars[0].date.isoformat() == "2026-01-01"
    assert canonical.usable_bars[-1].date.isoformat() == "2026-07-20"


def test_rejects_200_usable_bars_as_insufficient(tmp_path) -> None:  # noqa: ANN001
    _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",),
    )

    payload = build_etf_sma_local_bars_canonicalization(_config(tmp_path))
    candidate = payload["candidates"][0]

    assert payload["canonicalization_state"] == (
        "blocked_no_valid_extended_local_operator_bars"
    )
    assert payload["performance_evidence_state"] == "insufficient_post_signal_returns"
    assert payload["usable_bar_count"] == 200
    assert payload["evaluated_return_count"] == 0
    assert candidate["usable_bar_count"] == 200
    assert "insufficient_usable_bars:200<201" in candidate["rejection_reasons"]
    assert any("M402 200-bar fixture is insufficient" in note for note in payload["blocker_notes"])
    assert any("M378 sample schema date,symbol,close" in note for note in payload["blocker_notes"])


@pytest.mark.parametrize(
    "path_part",
    ("fixture", "sample", "synthetic", "test", "demo"),
)
def test_rejects_fixture_sample_synthetic_test_demo_provenance(
    tmp_path,
    path_part: str,
) -> None:  # noqa: ANN001
    _write_csv(
        tmp_path / f"operator_{path_part}" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )

    payload = build_etf_sma_local_bars_canonicalization(_config(tmp_path))
    candidate = payload["candidates"][0]

    assert candidate["accepted"] is False
    assert candidate["usable_bar_count"] == 201
    assert candidate["provenance_risk"] == "fixture_sample_synthetic_test_demo"
    assert (
        "provenance_rejected_fixture_sample_synthetic_test_demo"
        in candidate["rejection_reasons"]
    )
    assert payload["fixture_sample_synthetic_test_data_used_as_operator_evidence"] is False


def test_rejects_ambiguous_provenance_even_when_strict_and_extended(
    tmp_path,
) -> None:  # noqa: ANN001
    _write_csv(
        tmp_path / "research_snapshots" / "SPY_daily.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )

    payload = build_etf_sma_local_bars_canonicalization(_config(tmp_path))
    candidate = payload["candidates"][0]

    assert candidate["accepted"] is False
    assert candidate["usable_bar_count"] == 201
    assert candidate["provenance_risk"] == "ambiguous_provenance"
    assert (
        "provenance_rejected_ambiguous_not_operator_evidence"
        in candidate["rejection_reasons"]
    )


@pytest.mark.parametrize(
    ("case_name", "expected_reason", "expected_flag"),
    (
        ("duplicate_dates", "duplicate_dates", "duplicate_dates"),
        ("descending_dates", "date_order_not_ascending", None),
        ("non_spy_rows", "non_spy_rows_present", None),
        ("missing_close", "missing_or_invalid_close", "missing_or_invalid_close"),
        ("non_positive_close", "non_positive_close", "non_positive_close"),
        ("malformed_rows", "malformed_csv_row", "malformed_rows"),
    ),
)
def test_rejects_malformed_or_incompatible_operator_csv(
    tmp_path,
    case_name: str,
    expected_reason: str,
    expected_flag: str | None,
) -> None:  # noqa: ANN001
    _write_malformed_csv(
        tmp_path / "operator_evidence" / f"{case_name}.csv",
        case_name,
    )

    payload = build_etf_sma_local_bars_canonicalization(_config(tmp_path))
    candidate = payload["candidates"][0]

    assert candidate["accepted"] is False
    assert expected_reason in candidate["rejection_reasons"]
    if expected_flag is not None:
        assert candidate[expected_flag] is True
    assert payload["canonical_output_written"] is False


def test_json_rendering_and_jsonl_write_are_deterministic(tmp_path) -> None:  # noqa: ANN001
    _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",),
    )
    config = _config(tmp_path)
    payload_a = build_etf_sma_local_bars_canonicalization(config)
    payload_b = build_etf_sma_local_bars_canonicalization(config)
    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"

    first = render_etf_sma_local_bars_canonicalization_json(payload_a)
    second = render_etf_sma_local_bars_canonicalization_json(payload_b)
    write_etf_sma_local_bars_canonicalization_jsonl(payload_a, output_a)
    write_etf_sma_local_bars_canonicalization_jsonl(payload_b, output_b)

    assert payload_a == payload_b
    assert first == second
    assert output_a.read_bytes() == output_b.read_bytes()
    assert len(output_a.read_text(encoding="utf-8").splitlines()) == 1


def test_all_safety_booleans_are_false_and_labels_are_conservative(
    tmp_path,
) -> None:  # noqa: ANN001
    _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )

    payload = build_etf_sma_local_bars_canonicalization(_config(tmp_path))

    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["profit_claim"] == "none"
    assert payload["labels"] == list(ETF_SMA_LOCAL_BARS_CANONICALIZATION_LABELS)
    assert payload["data_provenance"]["network_access_attempted"] is False
    assert payload["data_provenance"]["credential_access_attempted"] is False
    assert payload["operator_evidence_synthetic"] is False


def test_canonicalization_research_module_imports_no_broker_sdk_or_network_dependencies() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_cli_smoke_writes_canonicalization_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    _write_csv(
        tmp_path / "operator_evidence" / "spy_daily_bars.csv",
        150 * ("100",) + 50 * ("200",) + ("220",),
    )
    run_log = tmp_path / "m408.jsonl"
    canonical_output = tmp_path / "canonical.csv"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("offline canonicalize command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            "etf-sma-local-bars-canonicalize",
            "--symbol",
            "SPY",
            "--candidate-root",
            str(tmp_path),
            "--source-refresh-log",
            str(_write_source_refresh_log(tmp_path / "m407.jsonl")),
            "--run-id",
            "unit_m408",
            "--run-log",
            str(run_log),
            "--canonical-output",
            str(canonical_output),
            "--format",
            "json",
        ]
    ) == 0

    stdout = capsys.readouterr().out
    payload = json.loads(run_log.read_text(encoding="utf-8"))
    assert json.loads(stdout) == payload
    assert payload["record_type"] == "etf_sma_local_bars_canonicalization"
    assert payload["run_id"] == "unit_m408"
    assert payload["canonicalization_state"] == "canonicalized_strict_local_operator_bars"


def _config(
    candidate_root: Path,
    *,
    source_refresh_log: Path | None = None,
    run_log: Path | None = None,
    canonical_output: Path | None = None,
) -> EtfSmaLocalBarsCanonicalizationConfig:
    return EtfSmaLocalBarsCanonicalizationConfig(
        run_id="unit_m408",
        symbol="SPY",
        candidate_root=candidate_root,
        source_refresh_log=source_refresh_log
        or _write_source_refresh_log(candidate_root / "m407.jsonl"),
        run_log=run_log or candidate_root / "m408.jsonl",
        canonical_output=canonical_output or candidate_root / "canonical.csv",
    )


def _write_source_refresh_log(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "record_type": "etf_sma_local_bars_backtest_refresh",
        "command": "etf-sma-local-bars-backtest-refresh",
        "run_id": "unit_m407",
        "symbol": "SPY",
        "candidate_daily_bars_csv": "runs/paper_lab/m402_fixture_canonical_spy_daily_bars_200.csv",
        "refresh_state": "blocked_insufficient_extended_daily_bars",
        "performance_evidence_state": "insufficient_post_signal_returns",
        "usable_bar_count": 200,
        "evaluated_return_count": 0,
        "profit_claim": "none",
    }
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_csv(path: Path, values: tuple[str, ...], symbol: str = "SPY") -> Path:
    start = date(2026, 1, 1)
    rows = [
        _csv_row(symbol, start + timedelta(days=index), value)
        for index, value in enumerate(values)
    ]
    return _write_csv_rows(path, rows)


def _write_malformed_csv(path: Path, case_name: str) -> Path:
    if case_name == "duplicate_dates":
        day = date(2026, 1, 1)
        return _write_csv_rows(
            path,
            [_csv_row("SPY", day, "100"), _csv_row("SPY", day, "101")],
        )
    if case_name == "descending_dates":
        return _write_csv_rows(
            path,
            [
                _csv_row("SPY", date(2026, 1, 2), "101"),
                _csv_row("SPY", date(2026, 1, 1), "100"),
            ],
        )
    if case_name == "non_spy_rows":
        return _write_csv_rows(
            path,
            [
                _csv_row("QQQ", date(2026, 1, 1), "100"),
                _csv_row("QQQ", date(2026, 1, 2), "101"),
            ],
        )
    if case_name == "missing_close":
        row = _csv_row("SPY", date(2026, 1, 1), "100")
        row["close"] = ""
        return _write_csv_rows(path, [row])
    if case_name == "non_positive_close":
        row = _csv_row("SPY", date(2026, 1, 1), "100")
        row["close"] = "0"
        row["adjusted_close"] = "0"
        return _write_csv_rows(path, [row])
    if case_name == "malformed_rows":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            ",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)
            + "\nSPY,2026-01-01,100,101,99,100,100,1000,extra\n",
            encoding="utf-8",
        )
        return path
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
