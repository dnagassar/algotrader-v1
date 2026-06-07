from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.research.etf_sma_backtest_stats import (
    EtfSmaAdjustedBasisValidationConfig,
    build_etf_sma_adjusted_basis_validation,
)
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS


_WINDOW_START = date(2022, 3, 21)
_WINDOW_END = date(2022, 3, 24)
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


def test_m420_matched_window_uses_source_dates_counts_and_excludes_warmup(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        _matched_contract_dates(extra_after=2),
        adjusted_distinct=True,
    )
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", csv_path)

    payload = build_etf_sma_adjusted_basis_validation(
        EtfSmaAdjustedBasisValidationConfig(
            run_id="unit_m420",
            source_m417_artifact=source_m417,
            daily_bars_csv=csv_path,
            match_source_slice_contract=True,
        )
    )

    assert payload["milestone"] == "M420"
    assert payload["record_type"] == "etf_sma_adjusted_matched_window_validation"
    assert (
        payload["basis_validation_status"]
        == "completed_adjusted_matched_window_validation"
    )
    assert payload["source_m417_data_basis"] == "raw_close_price_return"
    assert payload["data_basis"] == "adjusted_close_price_return"
    assert payload["match_source_slice_contract"] is True
    assert payload["matched_total_interval_count"] == 3
    assert payload["evaluated_return_count"] == 3
    assert payload["full_history_evaluated_return_count"] > 3
    assert payload["evaluated_start_date"] == _WINDOW_START.isoformat()
    assert payload["evaluated_end_date"] == _WINDOW_END.isoformat()
    assert payload["same_slice_counts"] is True
    assert payload["same_slice_dates"] is True
    assert payload["m417a_slice_counts_unchanged"] is True
    assert payload["adjusted_close_available"] is True
    assert payload["total_return_available"] is False
    assert payload["profit_claim"] == "none"
    assert payload["trade_recommendation"] == "none"
    _assert_safety_false(payload)

    slices = {item["slice_name"]: item for item in payload["regime_slices"]}
    assert set(slices) == {
        "full_evaluated_window",
        "first_interval",
        "remaining_intervals",
    }
    assert slices["full_evaluated_window"]["slice_start_date"] == "2022-03-21"
    assert slices["full_evaluated_window"]["slice_end_date"] == "2022-03-24"
    assert slices["full_evaluated_window"]["evaluated_return_count"] == 3
    assert "2022-03-21" not in (
        slices["full_evaluated_window"]["transition_event_dates"]
    )
    assert slices["first_interval"]["slice_start_date"] == "2022-03-21"
    assert slices["first_interval"]["slice_end_date"] == "2022-03-22"
    assert slices["first_interval"]["evaluated_return_count"] == 1
    assert slices["remaining_intervals"]["slice_start_date"] == "2022-03-22"
    assert slices["remaining_intervals"]["slice_end_date"] == "2022-03-24"
    assert slices["remaining_intervals"]["evaluated_return_count"] == 2

    comparisons = {
        item["slice_name"]: item for item in payload["matched_slice_comparisons"]
    }
    for name in slices:
        assert comparisons[name]["same_evaluated_return_count"] is True
        assert comparisons[name]["same_slice_dates"] is True


def test_m420_missing_source_artifact_blocks_deterministically(tmp_path) -> None:  # noqa: ANN001
    payload = build_etf_sma_adjusted_basis_validation(
        EtfSmaAdjustedBasisValidationConfig(
            run_id="unit_m420_missing_source",
            source_m417_artifact=tmp_path / "missing.jsonl",
            match_source_slice_contract=True,
        )
    )

    assert payload["milestone"] == "M420"
    assert payload["basis_validation_status"] == (
        "blocked_missing_source_m417_artifact"
    )
    assert payload["blocked_reason"] == "source_m417_artifact_not_found"
    assert payload["same_slice_counts"] is False
    assert payload["same_slice_dates"] is False
    _assert_safety_false(payload)


def test_m420_missing_daily_bars_csv_blocks_deterministically(tmp_path) -> None:  # noqa: ANN001
    missing_csv = tmp_path / "missing.csv"
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", missing_csv)

    payload = build_etf_sma_adjusted_basis_validation(
        EtfSmaAdjustedBasisValidationConfig(
            run_id="unit_m420_missing_csv",
            source_m417_artifact=source_m417,
            match_source_slice_contract=True,
        )
    )

    assert payload["basis_validation_status"] == "blocked_missing_daily_bars_csv"
    assert payload["blocked_reason"] == "daily_bars_csv_not_found"
    assert payload["source_daily_bars_csv"] == str(missing_csv)
    _assert_safety_false(payload)


def test_m420_insufficient_adjusted_coverage_blocks_deterministically(
    tmp_path,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "short_adjusted.csv",
        _matched_contract_dates(interval_count=2),
        adjusted_distinct=True,
    )
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", csv_path)

    payload = build_etf_sma_adjusted_basis_validation(
        EtfSmaAdjustedBasisValidationConfig(
            run_id="unit_m420_short_coverage",
            source_m417_artifact=source_m417,
            daily_bars_csv=csv_path,
            match_source_slice_contract=True,
        )
    )

    assert payload["basis_validation_status"] == (
        "blocked_adjusted_bars_do_not_cover_m417a_window"
    )
    assert payload["same_slice_counts"] is False
    assert payload["same_slice_dates"] is False
    _assert_safety_false(payload)


def test_m420_rejects_adjusted_close_that_mirrors_raw_close(tmp_path) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "mirrored_adjusted.csv",
        _matched_contract_dates(),
        adjusted_distinct=False,
    )
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", csv_path)

    payload = build_etf_sma_adjusted_basis_validation(
        EtfSmaAdjustedBasisValidationConfig(
            run_id="unit_m420_invalid_basis",
            source_m417_artifact=source_m417,
            daily_bars_csv=csv_path,
            match_source_slice_contract=True,
        )
    )

    assert payload["basis_validation_status"] == "blocked_invalid_adjusted_close_basis"
    assert payload["blocked_reason"] == (
        "adjusted_close_column_mirrors_raw_close_for_all_usable_rows"
    )
    assert payload["adjusted_close_available"] is False
    _assert_safety_false(payload)


def test_m420_cli_writes_artifact_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    csv_path = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        _matched_contract_dates(),
        adjusted_distinct=True,
    )
    source_m417 = _write_source_m417_artifact(tmp_path / "m417.jsonl", csv_path)
    run_log = tmp_path / "m420.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M420 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            "etf-sma-adjusted-basis-validation",
            "--source-m417-artifact",
            str(source_m417),
            "--daily-bars-csv",
            str(csv_path),
            "--run-log",
            str(run_log),
            "--run-id",
            "unit_m420_cli",
            "--match-source-slice-contract",
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["basis_validation_status"] == (
        "completed_adjusted_matched_window_validation"
    )
    assert payload["same_slice_counts"] is True
    assert payload["same_slice_dates"] is True


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
        "evaluated_return_count": 3,
        "benchmark_equity_curve": [
            _source_return("2022-03-22", "2022-03-21"),
            _source_return("2022-03-23", "2022-03-22"),
            _source_return("2022-03-24", "2022-03-23"),
        ],
        "regime_slices": [
            _raw_slice("full_evaluated_window", "2022-03-21", "2022-03-24", 3),
            _raw_slice("first_interval", "2022-03-21", "2022-03-22", 1),
            _raw_slice("remaining_intervals", "2022-03-22", "2022-03-24", 2),
        ],
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _source_return(end_date: str, start_date: str) -> dict[str, object]:
    return {
        "date": end_date,
        "start_date": start_date,
        "close": "100",
        "asset_return": "0.01",
        "equity": "25.00",
        "drawdown": "0",
    }


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


def _matched_contract_dates(
    *,
    interval_count: int = 3,
    extra_after: int = 0,
) -> list[date]:
    warmup_start = _WINDOW_START - timedelta(days=200)
    dates = [warmup_start + timedelta(days=index) for index in range(201)]
    dates.extend(
        _WINDOW_START + timedelta(days=index)
        for index in range(1, interval_count + 1)
    )
    dates.extend(
        _WINDOW_END + timedelta(days=index)
        for index in range(1, extra_after + 1)
    )
    assert len(set(dates)) == len(dates)
    return dates
