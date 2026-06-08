from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_authorized_adjusted_baseline_backtest_replay import (
    EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig,
    build_etf_sma_authorized_adjusted_baseline_backtest_replay,
    render_etf_sma_authorized_adjusted_baseline_backtest_replay_json,
    write_etf_sma_authorized_adjusted_baseline_backtest_replay_jsonl,
)
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS


_COMMAND = "etf-sma-authorized-adjusted-baseline-backtest-replay"
_INPUT_SNAPSHOT_STATUS = (
    "authorized_adjusted_baseline_backtest_snapshot_materialized"
)
_MATERIALIZED_STATUS = "authorized_adjusted_baseline_backtest_replayed"
_BLOCKED_STATUS = "blocked_authorized_snapshot_required"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_WINDOW_START = date(2022, 3, 21)
_MATCHED_INTERVAL_COUNT = 1055
_SLICE_COUNTS = (
    ("stress_2022", 197),
    ("recovery_2023", 250),
    ("bull_2024", 252),
    ("whipsaw_2025", 250),
    ("ytd_2026", 106),
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SUCCESS_ONLY_FIELDS = (
    "input_snapshot_status",
    "active_preferred_baseline",
    "active_preferred_basis",
    "comparison_basis",
    "matched_total_interval_count",
    "known_basis_delta_slices",
    "known_basis_delta_slice_count",
    "baseline_source_milestone",
    "guard_source_milestone",
    "authorization_source_milestone",
    "stub_source_milestone",
    "summary_source_milestone",
    "metrics_source_milestone",
    "snapshot_source_milestone",
    "source_evidence_milestone",
    "replay_scope",
    "strategy_family",
    "data_basis",
    "evaluated_return_count",
    "start_date",
    "end_date",
    "strategy_total_return",
    "max_drawdown",
    "trade_count",
)


def test_authorized_m428_snapshot_replays_adjusted_matched_window_backtest(
    tmp_path: Path,
) -> None:
    snapshot_path = _write_snapshot(tmp_path)
    source_m417, daily_bars_csv = _write_local_replay_inputs(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_replay(
        _config(snapshot_path, source_m417, daily_bars_csv)
    )

    assert payload["run_id"] == "unit_m429"
    assert payload["symbol"] == "SPY"
    assert payload["milestone"] == "M429"
    assert payload["backtest_replay_status"] == _MATERIALIZED_STATUS
    assert payload["input_snapshot_status"] == _INPUT_SNAPSHOT_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["backtest_replayed"] is True
    assert payload["active_preferred_baseline"] == _PREFERRED_BASELINE
    assert payload["active_preferred_basis"] == _PREFERRED_BASIS
    assert payload["comparison_basis"] == "matched_window"
    assert payload["matched_total_interval_count"] == _MATCHED_INTERVAL_COUNT
    assert payload["known_basis_delta_slices"] == ["recovery_2023"]
    assert payload["known_basis_delta_slice_count"] == 1
    assert payload["baseline_source_milestone"] == "M422"
    assert payload["guard_source_milestone"] == "M423"
    assert payload["authorization_source_milestone"] == "M424"
    assert payload["stub_source_milestone"] == "M425"
    assert payload["summary_source_milestone"] == "M426"
    assert payload["metrics_source_milestone"] == "M427"
    assert payload["snapshot_source_milestone"] == "M428"
    assert payload["source_evidence_milestone"] == "M421"
    assert payload["local_replay_source_milestone"] == "M420"
    assert payload["replay_scope"] == "authorized_adjusted_close_matched_window"
    assert payload["strategy_family"] == "etf_sma_50_200"
    assert payload["data_basis"] == _PREFERRED_BASIS
    assert payload["benchmark_basis"] == (
        "adjusted_close_price_return_buy_and_hold"
    )
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    assert payload["evaluated_return_count"] == _MATCHED_INTERVAL_COUNT
    assert payload["start_date"] == _WINDOW_START.isoformat()
    assert payload["end_date"] == _boundary_date(_MATCHED_INTERVAL_COUNT).isoformat()
    assert "strategy_total_return" in payload
    assert "max_drawdown" in payload
    assert isinstance(payload["trade_count"], int)
    assert payload["trades_count"] == payload["trade_count"]
    assert payload["regime_slice_count"] == 6
    assert payload["matched_slice_comparisons_count"] == 6
    assert payload["matched_slice_diagnostics_count"] == 6
    assert payload["metrics_recomputed"] is False
    assert payload["new_market_data_loaded"] is False
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m429.jsonl"
    write_etf_sma_authorized_adjusted_baseline_backtest_replay_jsonl(
        payload,
        run_log,
    )
    lines = run_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == json.loads(
        render_etf_sma_authorized_adjusted_baseline_backtest_replay_json(
            payload
        )
    )


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "input_snapshot_artifact_not_found"),
        (
            lambda path: path.write_text("", encoding="utf-8"),
            "input_snapshot_artifact_empty",
        ),
        (
            lambda path: path.write_text("{", encoding="utf-8"),
            "input_snapshot_artifact_invalid_json_line_1",
        ),
        (
            lambda path: path.write_text("[]\n", encoding="utf-8"),
            "input_snapshot_artifact_record_1_not_object",
        ),
        (
            lambda path: path.write_text(
                "\n".join(
                    [
                        json.dumps(_snapshot_payload(), sort_keys=True),
                        json.dumps(_snapshot_payload(), sort_keys=True),
                    ]
                )
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_input_snapshot_artifact_record_count",
        ),
    ],
)
def test_blocks_when_m428_snapshot_file_is_missing_empty_malformed_or_ambiguous(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    snapshot_path = tmp_path / "m428.jsonl"
    writer(snapshot_path)

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_replay(
        _config(snapshot_path, tmp_path / "m417.jsonl", tmp_path / "bars.csv")
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "backtest_snapshot_status",
            "blocked_authorized_metrics_required",
            "input_snapshot_unexpected_backtest_snapshot_status",
        ),
        (
            "input_metrics_status",
            "blocked_authorized_summary_required",
            "input_snapshot_unexpected_input_metrics_status",
        ),
        (
            "downstream_comparison_authorized",
            False,
            "input_snapshot_downstream_comparison_authorized_not_true",
        ),
        (
            "backtest_snapshot_materialized",
            False,
            "input_snapshot_backtest_snapshot_materialized_not_true",
        ),
        (
            "active_preferred_baseline",
            "raw_close_matched_window",
            "input_snapshot_unexpected_active_preferred_baseline",
        ),
        (
            "active_preferred_basis",
            "raw_close_price_return",
            "input_snapshot_unexpected_active_preferred_basis",
        ),
        (
            "comparison_basis",
            "full_history",
            "input_snapshot_unexpected_comparison_basis",
        ),
        ("symbol", "QQQ", "input_snapshot_unexpected_symbol"),
        ("milestone", "M427", "input_snapshot_unexpected_milestone"),
        (
            "baseline_source_milestone",
            "M421",
            "input_snapshot_unexpected_baseline_source_milestone",
        ),
        (
            "guard_source_milestone",
            "M422",
            "input_snapshot_unexpected_guard_source_milestone",
        ),
        (
            "authorization_source_milestone",
            "M423",
            "input_snapshot_unexpected_authorization_source_milestone",
        ),
        (
            "stub_source_milestone",
            "M424",
            "input_snapshot_unexpected_stub_source_milestone",
        ),
        (
            "summary_source_milestone",
            "M425",
            "input_snapshot_unexpected_summary_source_milestone",
        ),
        (
            "metrics_source_milestone",
            "M426",
            "input_snapshot_unexpected_metrics_source_milestone",
        ),
        (
            "source_evidence_milestone",
            "M420",
            "input_snapshot_unexpected_source_evidence_milestone",
        ),
        (
            "matched_total_interval_count",
            1054,
            "input_snapshot_unexpected_matched_total_interval_count",
        ),
        (
            "known_basis_delta_slices",
            [],
            "input_snapshot_unexpected_known_basis_delta_slices",
        ),
        (
            "known_basis_delta_slice_count",
            2,
            "input_snapshot_unexpected_known_basis_delta_slice_count",
        ),
        (
            "metrics_recomputed",
            True,
            "input_snapshot_metrics_recomputed_not_false",
        ),
        (
            "new_market_data_loaded",
            True,
            "input_snapshot_new_market_data_loaded_not_false",
        ),
        (
            "trade_recommendation",
            "buy",
            "input_snapshot_unexpected_trade_recommendation",
        ),
        ("profit_claim", "positive", "input_snapshot_unexpected_profit_claim"),
    ],
)
def test_blocks_when_m428_snapshot_authorization_or_contract_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    snapshot_path = _write_snapshot(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_replay(
        _config(snapshot_path, tmp_path / "m417.jsonl", tmp_path / "bars.csv")
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize("field_name", _SAFETY_FALSE_FIELDS)
def test_blocks_when_m428_snapshot_is_safety_dirty(
    tmp_path: Path,
    field_name: str,
) -> None:
    snapshot_path = _write_snapshot(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: True}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_replay(
        _config(snapshot_path, tmp_path / "m417.jsonl", tmp_path / "bars.csv")
    )

    _assert_blocked(payload, f"input_snapshot_safety_flag_dirty_{field_name}")


@pytest.mark.parametrize(
    ("mutator", "expected_blocker"),
    [
        (
            lambda paths: paths["source_m417"].unlink(),
            "source_m417_artifact_not_found",
        ),
        (
            lambda paths: paths["source_m417"].write_text(
                json.dumps(_source_m417_payload(paths["daily_bars_csv"]))
                + "\n"
                + json.dumps(_source_m417_payload(paths["daily_bars_csv"]))
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_source_m417_artifact_record_count",
        ),
        (
            lambda paths: paths["daily_bars_csv"].unlink(),
            "daily_bars_csv_not_found",
        ),
    ],
)
def test_blocks_when_local_replay_inputs_are_missing_or_ambiguous(
    tmp_path: Path,
    mutator,
    expected_blocker: str,
) -> None:
    snapshot_path = _write_snapshot(tmp_path)
    source_m417, daily_bars_csv = _write_local_replay_inputs(tmp_path)
    mutator({"source_m417": source_m417, "daily_bars_csv": daily_bars_csv})

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_replay(
        _config(snapshot_path, source_m417, daily_bars_csv)
    )

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_local_replay_helper_cannot_validate_adjusted_basis(
    tmp_path: Path,
) -> None:
    snapshot_path = _write_snapshot(tmp_path)
    source_m417, daily_bars_csv = _write_local_replay_inputs(
        tmp_path,
        adjusted_distinct=False,
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_replay(
        _config(snapshot_path, source_m417, daily_bars_csv)
    )

    _assert_blocked(
        payload,
        "local_replay_unexpected_basis_validation_status",
    )


def test_output_remains_deterministic(tmp_path: Path) -> None:
    snapshot_path = _write_snapshot(tmp_path)
    source_m417, daily_bars_csv = _write_local_replay_inputs(tmp_path)
    config = _config(snapshot_path, source_m417, daily_bars_csv)

    first = build_etf_sma_authorized_adjusted_baseline_backtest_replay(config)
    second = build_etf_sma_authorized_adjusted_baseline_backtest_replay(config)

    assert first == second
    assert render_etf_sma_authorized_adjusted_baseline_backtest_replay_json(
        first
    ) == render_etf_sma_authorized_adjusted_baseline_backtest_replay_json(second)


def test_cli_writes_replay_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    snapshot_path = _write_snapshot(tmp_path)
    source_m417, daily_bars_csv = _write_local_replay_inputs(tmp_path)
    run_log = tmp_path / "m429_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M429 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m429_cli",
            "--run-log",
            str(run_log),
            "--snapshot-path",
            str(snapshot_path),
            "--source-m417-artifact",
            str(source_m417),
            "--daily-bars-csv",
            str(daily_bars_csv),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["backtest_replay_status"] == _MATERIALIZED_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["backtest_replayed"] is True


def _assert_blocked(payload: dict[str, object], expected_blocker: str) -> None:
    assert payload["milestone"] == "M429"
    assert payload["backtest_replay_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["backtest_replayed"] is False
    assert expected_blocker in payload["blockers"]
    assert payload["blocked_reason"] == expected_blocker
    assert payload["metrics_recomputed"] is False
    assert payload["new_market_data_loaded"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    for field_name in _SUCCESS_ONLY_FIELDS:
        assert field_name not in payload
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def _config(
    snapshot_path: Path,
    source_m417: Path,
    daily_bars_csv: Path,
) -> EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig:
    return EtfSmaAuthorizedAdjustedBaselineBacktestReplayConfig(
        run_id="unit_m429",
        symbol="SPY",
        snapshot_path=snapshot_path,
        source_m417_artifact=source_m417,
        daily_bars_csv=daily_bars_csv,
    )


def _write_snapshot(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _snapshot_payload()
    if mutator is not None:
        mutator(payload)

    snapshot_path = tmp_path / "m428.jsonl"
    snapshot_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return snapshot_path


def _snapshot_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "active_preferred_baseline": _PREFERRED_BASELINE,
        "active_preferred_basis": _PREFERRED_BASIS,
        "authorization_source_milestone": "M424",
        "backtest_snapshot_materialized": True,
        "backtest_snapshot_status": _INPUT_SNAPSHOT_STATUS,
        "baseline_source_milestone": "M422",
        "blockers": [],
        "command": "etf-sma-authorized-adjusted-baseline-backtest-snapshot",
        "comparison_basis": "matched_window",
        "downstream_comparison_authorized": True,
        "guard_source_milestone": "M423",
        "input_metrics_status": (
            "authorized_adjusted_baseline_metrics_materialized"
        ),
        "known_basis_delta_slice_count": 1,
        "known_basis_delta_slices": ["recovery_2023"],
        "matched_total_interval_count": _MATCHED_INTERVAL_COUNT,
        "metrics_recomputed": False,
        "metrics_source_milestone": "M427",
        "milestone": "M428",
        "new_market_data_loaded": False,
        "profit_claim": "none",
        "record_type": "etf_sma_authorized_adjusted_baseline_backtest_snapshot",
        "run_id": "unit_m428",
        "schema_version": "1",
        "snapshot_scope": "authorized_adjusted_baseline_metrics_only",
        "source_evidence_milestone": "M421",
        "stub_source_milestone": "M425",
        "summary_source_milestone": "M426",
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload


def _write_local_replay_inputs(
    tmp_path: Path,
    *,
    adjusted_distinct: bool = True,
) -> tuple[Path, Path]:
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        _daily_bar_dates(),
        adjusted_distinct=adjusted_distinct,
    )
    source_m417 = tmp_path / "m417.jsonl"
    source_m417.write_text(
        json.dumps(_source_m417_payload(daily_bars_csv), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return source_m417, daily_bars_csv


def _write_daily_bars_csv(
    path: Path,
    dates: list[date],
    *,
    adjusted_distinct: bool,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    for index, day in enumerate(dates):
        close = Decimal("100") + Decimal(index)
        adjusted_close = (
            Decimal("200") + Decimal(index) if adjusted_distinct else close
        )
        rows.append(
            ",".join(
                (
                    "SPY",
                    day.isoformat(),
                    str(close),
                    str(close + Decimal("1")),
                    str(close - Decimal("1")),
                    str(close),
                    str(adjusted_close),
                    "1000",
                )
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _source_m417_payload(daily_bars_csv: Path) -> dict[str, object]:
    payload = {
        "record_type": "etf_sma_regime_slice_evidence",
        "schema_version": "1",
        "milestone": "M417",
        "run_id": "unit_m417",
        "symbol": "SPY",
        "data_basis": "raw_close_price_return",
        "source_daily_bars_csv": str(daily_bars_csv),
        "evaluated_return_count": _MATCHED_INTERVAL_COUNT,
        "benchmark_equity_curve": [
            _source_return(index) for index in range(1, _MATCHED_INTERVAL_COUNT + 1)
        ],
        "regime_slices": _source_regime_slices(),
    }
    return payload


def _source_return(index: int) -> dict[str, object]:
    return {
        "date": _boundary_date(index).isoformat(),
        "start_date": _boundary_date(index - 1).isoformat(),
        "close": "100",
        "asset_return": "0.01",
        "equity": "25.00",
        "drawdown": "0",
    }


def _source_regime_slices() -> list[dict[str, object]]:
    slices = [
        _raw_slice(
            "full_evaluated_window",
            _boundary_date(0),
            _boundary_date(_MATCHED_INTERVAL_COUNT),
            _MATCHED_INTERVAL_COUNT,
        )
    ]
    offset = 0
    for name, count in _SLICE_COUNTS:
        slices.append(_raw_slice(name, _boundary_date(offset), _boundary_date(offset + count), count))
        offset += count
    assert offset == _MATCHED_INTERVAL_COUNT
    return slices


def _raw_slice(
    name: str,
    start_date: date,
    end_date: date,
    count: int,
) -> dict[str, object]:
    strategy_return = Decimal("0.10")
    benchmark_return = Decimal("0.20")
    strategy_drawdown = Decimal("0.05")
    benchmark_drawdown = Decimal("0.07")
    return {
        "slice_name": name,
        "slice_start_date": start_date.isoformat(),
        "slice_end_date": end_date.isoformat(),
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
        "trade_recommendation": "none",
    }


def _daily_bar_dates() -> list[date]:
    warmup_start = _WINDOW_START - timedelta(days=200)
    dates = [warmup_start + timedelta(days=index) for index in range(201)]
    dates.extend(
        _WINDOW_START + timedelta(days=index)
        for index in range(1, _MATCHED_INTERVAL_COUNT + 1)
    )
    assert len(set(dates)) == len(dates)
    return dates


def _boundary_date(offset: int) -> date:
    return _WINDOW_START + timedelta(days=offset)
