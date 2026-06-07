from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.research.etf_sma_backtest_stats import (
    EtfSmaAdjustedBasisValidationConfig,
    build_etf_sma_adjusted_basis_validation,
    render_etf_sma_adjusted_basis_validation_json,
    write_etf_sma_adjusted_basis_validation_jsonl,
)
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS


MODULE_PATH = Path("src/algotrader/research/etf_sma_backtest_stats.py")
_SOURCE_M417_ARTIFACT = "runs\\paper_lab\\m417_spy_etf_sma_regime_slice_evidence.jsonl"
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "submit_authorized",
    "submit_path_allowed",
    "paper_submit_approved",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "credential_access",
    "credential_access_attempted",
    "broker_network_access",
    "network_access_attempted",
    "broker_action_performed",
    "broker_actions_performed",
    "market_data_fetch_performed",
)
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
    "openai",
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
    "os.getenv",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}
_M417A_SLICE_COUNTS = {
    "stress_2022": ("2022-03-21", "2022-12-30", 197),
    "recovery_2023": ("2022-12-30", "2023-12-29", 250),
    "bull_2024": ("2023-12-29", "2024-12-31", 252),
    "whipsaw_2025": ("2024-12-31", "2025-12-31", 250),
    "ytd_2026": ("2025-12-31", "2026-06-05", 106),
}


def test_m418_unavailable_basis_writes_clean_blocked_artifact(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "raw_mirrored_adjusted.csv",
        [date(2026, 1, 1) + timedelta(days=index) for index in range(205)],
        adjusted_distinct=False,
    )
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", csv_path)

    payload = build_etf_sma_adjusted_basis_validation(
        EtfSmaAdjustedBasisValidationConfig(
            run_id="unit_m418",
            source_m417_artifact=source_m417,
        )
    )

    assert payload["milestone"] == "M418"
    assert payload["source_m417_artifact"] == str(source_m417)
    assert payload["data_basis"] == "unavailable_adjusted_or_total_return_basis"
    assert (
        payload["basis_validation_status"]
        == "blocked_adjusted_or_total_return_basis_unavailable"
    )
    assert payload["adjusted_close_available"] is False
    assert payload["total_return_available"] is False
    assert payload["blocked_reason"] == (
        "offline_adjusted_close_or_total_return_compatible_data_unavailable"
    )
    assert payload["profit_claim"] == "none"
    assert payload["trade_recommendation"] == "none"
    assert payload["returns_fabricated"] is False
    assert "regime_slices" not in payload
    assert (
        "adjusted_close_values_distinct_from_raw_close_for_spy_dividend_window"
        in payload["missing_inputs"]
    )
    assert (
        payload["adjusted_basis_vs_m417a_raw_close_comparison"][
            "raw_close_conclusions_revalidated"
        ]
        is False
    )
    _assert_safety_false(payload)

    run_log = tmp_path / "m418.jsonl"
    write_etf_sma_adjusted_basis_validation_jsonl(payload, run_log)
    lines = run_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == json.loads(
        render_etf_sma_adjusted_basis_validation_json(payload)
    )


def test_m418_available_adjusted_close_path_preserves_m417a_slice_counts(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        _m417a_contract_dates(),
        adjusted_distinct=True,
    )
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", csv_path)

    payload = build_etf_sma_adjusted_basis_validation(
        EtfSmaAdjustedBasisValidationConfig(
            run_id="unit_m418_available",
            source_m417_artifact=source_m417,
            cost_bps="1",
        )
    )

    assert payload["basis_validation_status"] == (
        "completed_adjusted_close_basis_validation"
    )
    assert payload["data_basis"] == "adjusted_close_price_return"
    assert payload["price_field"] == "adjusted_close"
    assert payload["adjusted_close_available"] is True
    assert payload["total_return_available"] is False
    assert payload["evaluated_return_count"] == 1055
    assert payload["m417a_slice_counts_unchanged"] is True
    assert payload["profit_claim"] == "none"
    assert payload["trade_recommendation"] == "none"
    _assert_safety_false(payload)

    slices = {item["slice_name"]: item for item in payload["regime_slices"]}
    assert slices["full_evaluated_window"]["evaluated_return_count"] == 1055
    for name, (start_date, end_date, count) in _M417A_SLICE_COUNTS.items():
        item = slices[name]
        assert item["slice_start_date"] == start_date
        assert item["slice_end_date"] == end_date
        assert item["evaluated_return_count"] == count
        assert item["data_basis"] == "adjusted_close_price_return"
        assert item["profit_claim"] == "none"


def test_m418_cli_writes_artifact_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "raw_mirrored_adjusted.csv",
        [date(2026, 1, 1) + timedelta(days=index) for index in range(205)],
        adjusted_distinct=False,
    )
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", csv_path)
    run_log = tmp_path / "m418.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M418 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            "etf-sma-adjusted-basis-validation",
            "--source-m417-artifact",
            str(source_m417),
            "--run-log",
            str(run_log),
            "--run-id",
            "unit_m418_cli",
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["basis_validation_status"] == (
        "blocked_adjusted_or_total_return_basis_unavailable"
    )
    assert payload["profit_claim"] == "none"


def test_m418_research_module_imports_no_broker_network_or_credential_dependencies() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _assert_safety_false(payload: dict[str, object]) -> None:
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def _write_daily_bars_csv(
    path: Path,
    dates: list[date],
    *,
    adjusted_distinct: bool,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    for index, day in enumerate(dates):
        close = Decimal("100")
        adjusted_close = (
            Decimal("200") + Decimal(index)
            if adjusted_distinct
            else close
        )
        rows.append(
            ",".join(
                (
                    "SPY",
                    day.isoformat(),
                    "100",
                    "101",
                    "99",
                    str(close),
                    str(adjusted_close),
                    "1000",
                )
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _write_source_m417_artifact(path: Path, daily_bars_csv: Path) -> Path:
    payload = {
        "record_type": "etf_sma_regime_slice_evidence",
        "schema_version": "1",
        "milestone": "M417",
        "run_id": "unit_m417",
        "data_basis": "raw_close_price_return",
        "source_daily_bars_csv": str(daily_bars_csv),
        "evaluated_return_count": 1055,
        "regime_slices": [
            _raw_slice("full_evaluated_window", "2022-03-21", "2026-06-05", 1055),
            _raw_slice("stress_2022", "2022-03-21", "2022-12-30", 197),
            _raw_slice("recovery_2023", "2022-12-30", "2023-12-29", 250),
            _raw_slice("bull_2024", "2023-12-29", "2024-12-31", 252),
            _raw_slice("whipsaw_2025", "2024-12-31", "2025-12-31", 250),
            _raw_slice("ytd_2026", "2025-12-31", "2026-06-05", 106),
        ],
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _raw_slice(
    name: str,
    start_date: str,
    end_date: str,
    count: int,
) -> dict[str, object]:
    strategy_return = Decimal("0.10")
    benchmark_return = Decimal("0.20")
    strategy_drawdown = Decimal("0.05")
    benchmark_drawdown = Decimal("0.07")
    return {
        "slice_name": name,
        "slice_start_date": start_date,
        "slice_end_date": end_date,
        "evaluated_return_count": count,
        "data_basis": "raw_close_price_return",
        "strategy_starting_equity": "25.00",
        "strategy_ending_equity": str(Decimal("25.00") * (1 + strategy_return)),
        "strategy_total_return": str(strategy_return),
        "benchmark_starting_equity": "25.00",
        "benchmark_ending_equity": str(Decimal("25.00") * (1 + benchmark_return)),
        "benchmark_total_return": str(benchmark_return),
        "excess_return": str(strategy_return - benchmark_return),
        "strategy_max_drawdown": str(strategy_drawdown),
        "benchmark_max_drawdown": str(benchmark_drawdown),
        "drawdown_delta": str(strategy_drawdown - benchmark_drawdown),
        "strategy_exposure_fraction": "1",
        "trade_count": 0,
        "entry_count": 0,
        "exit_count": 0,
        "transition_event_dates": [],
        "profit_claim": "none",
    }


def _m417a_contract_dates() -> list[date]:
    pre_start = date(2022, 3, 21) - timedelta(days=199)
    dates = [pre_start + timedelta(days=index) for index in range(200)]
    dates.extend(_sample_dates(date(2022, 3, 22), date(2022, 12, 30), 197))
    dates.extend(_sample_dates(date(2023, 1, 1), date(2023, 12, 29), 250))
    dates.extend(_sample_dates(date(2024, 1, 1), date(2024, 12, 31), 252))
    dates.extend(_sample_dates(date(2025, 1, 1), date(2025, 12, 31), 250))
    dates.extend(_sample_dates(date(2026, 1, 1), date(2026, 6, 5), 106))
    assert len(dates) == 1255
    assert len(set(dates)) == len(dates)
    return dates


def _sample_dates(start: date, end: date, count: int) -> list[date]:
    if count <= 0:
        return []
    if count == 1:
        return [start]
    day_span = (end - start).days
    return [
        start + timedelta(days=(index * day_span) // (count - 1))
        for index in range(count)
    ]


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
