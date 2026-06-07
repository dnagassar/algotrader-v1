from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_adjusted_bars_intake import (
    ETF_SMA_ADJUSTED_BARS_INTAKE_ACCEPTED_BASIS_COLUMNS,
    ETF_SMA_ADJUSTED_BARS_INTAKE_REQUIRED_COLUMNS,
    EtfSmaAdjustedBarsIntakeConfig,
    build_etf_sma_adjusted_bars_intake,
    render_etf_sma_adjusted_bars_intake_json,
    write_etf_sma_adjusted_bars_intake_jsonl,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_adjusted_bars_intake.py")
CANONICAL_COLUMNS = (
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)
SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "broker_network_access",
    "credential_access",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "market_data_fetch_performed",
    "returns_fabricated",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "alpaca",
    "alpaca_trade_api",
    "http",
    "httpx",
    "os",
    "requests",
    "socket",
    "urllib",
    "yfinance",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "download",
    "getenv",
    "os.getenv",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_missing_input_cli_writes_deterministic_blocked_artifact(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    run_log = tmp_path / "runs" / "paper_lab" / "m419.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M419 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    exit_code = cli_module.main(
        (
            "etf-sma-adjusted-bars-intake",
            "--run-log",
            str(run_log),
            "--format",
            "json",
        )
    )

    payload = json.loads(capsys.readouterr().out)
    records = _read_jsonl(run_log)

    assert exit_code == 0
    assert records == [payload]
    assert payload["milestone"] == "M419"
    assert payload["record_type"] == "etf_sma_adjusted_bars_intake"
    assert payload["command"] == "etf-sma-adjusted-bars-intake"
    assert payload["intake_status"] == (
        "blocked_missing_operator_supplied_adjusted_bars"
    )
    assert payload["required_columns"] == list(
        ETF_SMA_ADJUSTED_BARS_INTAKE_REQUIRED_COLUMNS
    )
    assert payload["accepted_adjusted_or_total_return_fields"] == list(
        ETF_SMA_ADJUSTED_BARS_INTAKE_ACCEPTED_BASIS_COLUMNS
    )
    assert payload["canonical_csv_written"] is False
    assert not Path(payload["canonical_csv"]).exists()
    assert payload["no_fabricated_evidence"] is True
    _assert_safety_false(payload)


def test_mirrored_adjusted_close_is_rejected(tmp_path) -> None:  # noqa: ANN001
    input_csv = _write_adjusted_csv(
        tmp_path / "mirrored.csv",
        _days(5),
        adjusted_distinct=False,
    )
    canonical_csv = tmp_path / "runs" / "paper_lab" / "canonical.csv"

    payload = build_etf_sma_adjusted_bars_intake(
        _config(tmp_path, input_csv=input_csv, canonical_csv=canonical_csv)
    )

    assert payload["intake_status"] == "blocked_invalid_adjusted_bars"
    assert payload["basis_label"] == "adjusted_close_price_return"
    assert payload["rejected_basis_reason"] == (
        "adjusted_or_total_return_basis_mirrors_raw_close"
    )
    assert "basis_values_mirror_close" in payload["blockers"]
    assert payload["canonical_csv_written"] is False
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_valid_synthetic_adjusted_close_csv_is_accepted(tmp_path) -> None:  # noqa: ANN001
    input_csv = _write_adjusted_csv(
        tmp_path / "operator_adjusted.csv",
        _days(5),
        adjusted_distinct=True,
    )
    canonical_csv = tmp_path / "runs" / "paper_lab" / "canonical.csv"
    run_log = tmp_path / "runs" / "paper_lab" / "m419.jsonl"

    payload = build_etf_sma_adjusted_bars_intake(
        _config(
            tmp_path,
            input_csv=input_csv,
            canonical_csv=canonical_csv,
            run_log=run_log,
            source_name="operator fixture source",
            source_notes="unit-test adjusted close fixture",
            operator_attested=False,
        )
    )
    result = write_etf_sma_adjusted_bars_intake_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [json.loads(render_etf_sma_adjusted_bars_intake_json(payload))]
    assert payload["intake_status"] == "ready_for_m418_adjusted_basis_rerun"
    assert payload["validation_status"] == "accepted"
    assert payload["basis_column"] == "adjusted_close"
    assert payload["basis_label"] == "adjusted_close_price_return"
    assert payload["accepted_basis_reason"] == (
        "operator_supplied_basis_distinct_from_raw_close_and_canonicalized"
    )
    assert payload["source_filename"] == "operator_adjusted.csv"
    assert payload["input_sha256"] == _sha256(input_csv)
    assert payload["canonical_sha256"] == _sha256(canonical_csv)
    assert payload["fingerprint"] == payload["input_sha256"]
    assert payload["source_row_count"] == 5
    assert payload["row_count"] == 5
    assert payload["date_range_start"] == "2026-01-01"
    assert payload["date_range_end"] == "2026-01-05"
    assert payload["provenance"]["valid"] is True
    assert payload["provenance"]["operator_attested"] is False
    assert payload["preview_only_handoff"]["run_m418_automatically"] is False
    assert payload["preview_only_handoff"]["ready_for_m418"] is True
    assert _read_csv_rows(canonical_csv)[0] == list(CANONICAL_COLUMNS)
    _assert_safety_false(payload)


@pytest.mark.parametrize(
    ("case_name", "expected_blocker"),
    (
        ("date_order", "date_order_not_ascending"),
        ("duplicate_dates", "duplicate_dates"),
        ("missing_fields", "missing_required_columns:high"),
        ("nonpositive_close", "nonpositive_close"),
        ("nonpositive_adjusted_close", "nonpositive_adjusted_close"),
    ),
)
def test_invalid_csv_shapes_are_rejected(
    tmp_path,
    case_name: str,
    expected_blocker: str,
) -> None:  # noqa: ANN001
    input_csv = tmp_path / f"{case_name}.csv"
    canonical_csv = tmp_path / "runs" / "paper_lab" / f"{case_name}.canonical.csv"
    dates = _days(5)
    rows = _daily_rows(dates, adjusted_distinct=True)

    if case_name == "date_order":
        rows[2]["date"], rows[3]["date"] = rows[3]["date"], rows[2]["date"]
    elif case_name == "duplicate_dates":
        rows[3]["date"] = rows[2]["date"]
    elif case_name == "missing_fields":
        _write_rows(input_csv, rows, columns=tuple(c for c in CANONICAL_COLUMNS if c != "high"))
    elif case_name == "nonpositive_close":
        rows[2]["close"] = "0"
    elif case_name == "nonpositive_adjusted_close":
        rows[2]["adjusted_close"] = "0"

    if case_name != "missing_fields":
        _write_rows(input_csv, rows)

    payload = build_etf_sma_adjusted_bars_intake(
        _config(tmp_path, input_csv=input_csv, canonical_csv=canonical_csv)
    )

    assert payload["intake_status"] == "blocked_invalid_adjusted_bars"
    assert expected_blocker in payload["blockers"]
    assert payload["canonical_csv_written"] is False
    assert not canonical_csv.exists()
    _assert_safety_false(payload)


def test_symbol_column_may_be_absent_when_command_symbol_is_spy(tmp_path) -> None:  # noqa: ANN001
    input_csv = tmp_path / "operator_adjusted_without_symbol.csv"
    columns = tuple(column for column in CANONICAL_COLUMNS if column != "symbol")
    _write_rows(input_csv, _daily_rows(_days(3), adjusted_distinct=True), columns=columns)

    payload = build_etf_sma_adjusted_bars_intake(
        _config(tmp_path, input_csv=input_csv)
    )

    assert payload["intake_status"] == "ready_for_m418_adjusted_basis_rerun"
    assert payload["symbol"] == "SPY"
    assert payload["canonical_csv_written"] is True
    assert _read_csv_rows(Path(payload["canonical_csv"]))[1][0] == "SPY"
    _assert_safety_false(payload)


def test_m419_parser_registration() -> None:
    parser = _m419_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["input_csv"].required is False
    assert options["run_log"].required is True
    assert options["canonical_csv"].required is False
    assert options["operator_attested_provenance"].default is False


def test_intake_module_imports_no_broker_network_credentials_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    tmp_path: Path,
    *,
    input_csv: Path | None,
    canonical_csv: Path | None = None,
    run_log: Path | None = None,
    source_name: str = "",
    source_notes: str = "",
    operator_attested: bool = True,
) -> EtfSmaAdjustedBarsIntakeConfig:
    return EtfSmaAdjustedBarsIntakeConfig(
        run_log=run_log or tmp_path / "runs" / "paper_lab" / "m419.jsonl",
        input_csv=input_csv,
        canonical_csv=canonical_csv,
        operator_attested_provenance=operator_attested,
        source_name=source_name,
        source_notes=source_notes,
    )


def _write_adjusted_csv(
    path: Path,
    dates: list[date],
    *,
    adjusted_distinct: bool,
) -> Path:
    _write_rows(path, _daily_rows(dates, adjusted_distinct=adjusted_distinct))
    return path


def _daily_rows(
    dates: list[date],
    *,
    adjusted_distinct: bool,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, day in enumerate(dates):
        close = Decimal("100") + Decimal(index)
        adjusted_close = close + Decimal("0.25") if adjusted_distinct else close
        rows.append(
            {
                "symbol": "SPY",
                "date": day.isoformat(),
                "open": str(close - Decimal("1")),
                "high": str(close + Decimal("1")),
                "low": str(close - Decimal("2")),
                "close": str(close),
                "adjusted_close": str(adjusted_close),
                "volume": "1000",
            }
        )
    return rows


def _write_rows(
    path: Path,
    rows: list[dict[str, str]],
    *,
    columns: tuple[str, ...] = CANONICAL_COLUMNS,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(row[column] for column in columns))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _days(count: int) -> list[date]:
    start = date(2026, 1, 1)
    return [start + timedelta(days=index) for index in range(count)]


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_csv_rows(path: Path) -> list[list[str]]:
    return [
        line.split(",")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_safety_false(payload: dict[str, object]) -> None:
    for field_name in SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def _m419_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-adjusted-bars-intake" in choices:
            return choices["etf-sma-adjusted-bars-intake"]
    raise AssertionError("etf-sma-adjusted-bars-intake parser not found")


def _import_references(path: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_forbidden_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in prefixes
    )
