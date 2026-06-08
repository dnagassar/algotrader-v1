from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_authorized_adjusted_close_posture_snapshot import (
    EtfSmaAuthorizedAdjustedClosePostureSnapshotConfig,
    build_etf_sma_authorized_adjusted_close_posture_snapshot,
    render_etf_sma_authorized_adjusted_close_posture_snapshot_json,
    write_etf_sma_authorized_adjusted_close_posture_snapshot_jsonl,
)
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS


_COMMAND = "etf-sma-authorized-adjusted-close-posture-snapshot"
_SUCCESS_STATUS = "authorized_adjusted_close_sma_posture_computed"
_INSUFFICIENT_STATUS = "insufficient_adjusted_history"
_BLOCKED_STATUS = "blocked_authorized_replay_required"
_INPUT_REPLAY_STATUS = "authorized_adjusted_baseline_backtest_replayed"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_MATCHED_INTERVAL_COUNT = 1055
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_POSTURE_FALSE_FIELDS = (
    "order_decision_computed",
    "paper_preview_computed",
    "broker_state_loaded",
    "new_market_data_loaded",
)
_SUCCESS_ONLY_FIELDS = (
    "input_replay_status",
    "active_preferred_baseline",
    "active_preferred_basis",
    "comparison_basis",
    "baseline_source_milestone",
    "guard_source_milestone",
    "authorization_source_milestone",
    "stub_source_milestone",
    "summary_source_milestone",
    "metrics_source_milestone",
    "snapshot_source_milestone",
    "replay_source_milestone",
    "source_evidence_milestone",
    "strategy_family",
    "data_basis",
    "as_of_date",
    "latest_available_bar_date",
    "adjusted_close",
    "usable_adjusted_bar_count",
    "sma_short_window",
    "sma_long_window",
    "sma50",
    "sma200",
    "sma_posture",
    "sufficient_history",
)


def test_authorized_m429_replay_computes_latest_adjusted_close_risk_on_posture(
    tmp_path: Path,
) -> None:
    bars_csv = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        [Decimal("100")] * 150 + [Decimal("200")] * 50,
    )
    replay_path = _write_replay(tmp_path, bars_csv)

    payload = build_etf_sma_authorized_adjusted_close_posture_snapshot(
        _config(replay_path)
    )

    assert payload["run_id"] == "unit_m430"
    assert payload["symbol"] == "SPY"
    assert payload["milestone"] == "M430"
    assert payload["posture_snapshot_status"] == _SUCCESS_STATUS
    assert payload["input_replay_status"] == _INPUT_REPLAY_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["posture_computed"] is True
    assert payload["active_preferred_baseline"] == _PREFERRED_BASELINE
    assert payload["active_preferred_basis"] == _PREFERRED_BASIS
    assert payload["comparison_basis"] == "matched_window"
    assert payload["baseline_source_milestone"] == "M422"
    assert payload["guard_source_milestone"] == "M423"
    assert payload["authorization_source_milestone"] == "M424"
    assert payload["stub_source_milestone"] == "M425"
    assert payload["summary_source_milestone"] == "M426"
    assert payload["metrics_source_milestone"] == "M427"
    assert payload["snapshot_source_milestone"] == "M428"
    assert payload["replay_source_milestone"] == "M429"
    assert payload["source_evidence_milestone"] == "M421"
    assert payload["strategy_family"] == "etf_sma_50_200"
    assert payload["data_basis"] == _PREFERRED_BASIS
    assert payload["as_of_date"] == _bar_date(199).isoformat()
    assert payload["latest_available_bar_date"] == _bar_date(199).isoformat()
    assert payload["adjusted_close"] == "200"
    assert payload["usable_adjusted_bar_count"] == 200
    assert payload["sma_short_window"] == 50
    assert payload["sma_long_window"] == 200
    assert payload["sma50"] == "200"
    assert payload["sma200"] == "125"
    assert payload["sma_posture"] == "risk_on"
    assert payload["sufficient_history"] is True
    assert payload["daily_bars_csv"] == str(bars_csv)
    assert payload["adjusted_close_input_helper"] == "load_local_daily_bars_csv"
    assert payload["adjusted_close_input_source"] == "m429_daily_bars_csv"
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    for field_name in _POSTURE_FALSE_FIELDS + _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m430.jsonl"
    write_etf_sma_authorized_adjusted_close_posture_snapshot_jsonl(
        payload,
        run_log,
    )
    lines = run_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == json.loads(
        render_etf_sma_authorized_adjusted_close_posture_snapshot_json(payload)
    )


def test_authorized_m429_replay_computes_latest_risk_off_posture(
    tmp_path: Path,
) -> None:
    bars_csv = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        [Decimal("200")] * 150 + [Decimal("100")] * 50,
    )
    replay_path = _write_replay(tmp_path, bars_csv)

    payload = build_etf_sma_authorized_adjusted_close_posture_snapshot(
        _config(replay_path)
    )

    assert payload["posture_snapshot_status"] == _SUCCESS_STATUS
    assert payload["sma50"] == "100"
    assert payload["sma200"] == "175"
    assert payload["sma_posture"] == "risk_off"
    assert payload["sufficient_history"] is True
    assert payload["order_decision_computed"] is False
    assert payload["paper_preview_computed"] is False


def test_authorized_m429_replay_with_less_than_200_bars_is_insufficient_history(
    tmp_path: Path,
) -> None:
    bars_csv = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        [Decimal("100")] * 149 + [Decimal("200")] * 50,
    )
    replay_path = _write_replay(tmp_path, bars_csv)

    payload = build_etf_sma_authorized_adjusted_close_posture_snapshot(
        _config(replay_path)
    )

    assert payload["posture_snapshot_status"] == _INSUFFICIENT_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["posture_computed"] is True
    assert payload["sufficient_history"] is False
    assert payload["usable_adjusted_bar_count"] == 199
    assert payload["sma50"] == "200"
    assert payload["sma200"] is None
    assert payload["sma_posture"] == "insufficient_history"
    assert payload["order_decision_computed"] is False
    assert payload["paper_preview_computed"] is False
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "input_replay_artifact_not_found"),
        (
            lambda path: path.write_text("", encoding="utf-8"),
            "input_replay_artifact_empty",
        ),
        (
            lambda path: path.write_text("{", encoding="utf-8"),
            "input_replay_artifact_invalid_json_line_1",
        ),
        (
            lambda path: path.write_text("[]\n", encoding="utf-8"),
            "input_replay_artifact_record_1_not_object",
        ),
        (
            lambda path: path.write_text(
                json.dumps(_m429_payload(Path("bars.csv")), sort_keys=True)
                + "\n"
                + json.dumps(_m429_payload(Path("bars.csv")), sort_keys=True)
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_input_replay_artifact_record_count",
        ),
    ],
)
def test_blocks_when_m429_replay_file_is_missing_empty_malformed_or_ambiguous(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    replay_path = tmp_path / "m429.jsonl"
    writer(replay_path)

    payload = build_etf_sma_authorized_adjusted_close_posture_snapshot(
        _config(replay_path)
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "backtest_replay_status",
            "blocked_authorized_snapshot_required",
            "input_replay_unexpected_backtest_replay_status",
        ),
        (
            "input_snapshot_status",
            "blocked_authorized_metrics_required",
            "input_replay_unexpected_input_snapshot_status",
        ),
        (
            "downstream_comparison_authorized",
            False,
            "input_replay_downstream_comparison_authorized_not_true",
        ),
        (
            "backtest_replayed",
            False,
            "input_replay_backtest_replayed_not_true",
        ),
        (
            "active_preferred_baseline",
            "raw_close_matched_window",
            "input_replay_unexpected_active_preferred_baseline",
        ),
        (
            "active_preferred_basis",
            "raw_close_price_return",
            "input_replay_unexpected_active_preferred_basis",
        ),
        (
            "comparison_basis",
            "full_history",
            "input_replay_unexpected_comparison_basis",
        ),
        ("symbol", "QQQ", "input_replay_unexpected_symbol"),
        ("milestone", "M428", "input_replay_unexpected_milestone"),
        (
            "baseline_source_milestone",
            "M421",
            "input_replay_unexpected_baseline_source_milestone",
        ),
        (
            "guard_source_milestone",
            "M422",
            "input_replay_unexpected_guard_source_milestone",
        ),
        (
            "authorization_source_milestone",
            "M423",
            "input_replay_unexpected_authorization_source_milestone",
        ),
        (
            "stub_source_milestone",
            "M424",
            "input_replay_unexpected_stub_source_milestone",
        ),
        (
            "summary_source_milestone",
            "M425",
            "input_replay_unexpected_summary_source_milestone",
        ),
        (
            "metrics_source_milestone",
            "M426",
            "input_replay_unexpected_metrics_source_milestone",
        ),
        (
            "snapshot_source_milestone",
            "M427",
            "input_replay_unexpected_snapshot_source_milestone",
        ),
        (
            "source_evidence_milestone",
            "M420",
            "input_replay_unexpected_source_evidence_milestone",
        ),
        (
            "replay_scope",
            "raw_close_matched_window",
            "input_replay_unexpected_replay_scope",
        ),
        (
            "strategy_family",
            "other_strategy",
            "input_replay_unexpected_strategy_family",
        ),
        (
            "data_basis",
            "raw_close_price_return",
            "input_replay_unexpected_data_basis",
        ),
        (
            "matched_total_interval_count",
            1054,
            "input_replay_unexpected_matched_total_interval_count",
        ),
        (
            "known_basis_delta_slices",
            [],
            "input_replay_unexpected_known_basis_delta_slices",
        ),
        (
            "known_basis_delta_slice_count",
            2,
            "input_replay_unexpected_known_basis_delta_slice_count",
        ),
        (
            "trade_recommendation",
            "buy",
            "input_replay_unexpected_trade_recommendation",
        ),
        ("profit_claim", "positive", "input_replay_unexpected_profit_claim"),
        (
            "new_market_data_loaded",
            True,
            "input_replay_new_market_data_loaded_not_false",
        ),
    ],
)
def test_blocks_when_m429_replay_authorization_or_contract_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    replay_path = _write_replay(
        tmp_path,
        tmp_path / "adjusted.csv",
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_adjusted_close_posture_snapshot(
        _config(replay_path)
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize("field_name", _SAFETY_FALSE_FIELDS)
def test_blocks_when_m429_replay_is_safety_dirty(
    tmp_path: Path,
    field_name: str,
) -> None:
    replay_path = _write_replay(
        tmp_path,
        tmp_path / "adjusted.csv",
        mutator=lambda payload: payload.update({field_name: True}),
    )

    payload = build_etf_sma_authorized_adjusted_close_posture_snapshot(
        _config(replay_path)
    )

    _assert_blocked(payload, f"input_replay_{field_name}_not_false")


@pytest.mark.parametrize(
    ("mutator", "expected_blocker"),
    [
        (
            lambda paths: paths["bars_csv"].unlink(),
            "local_adjusted_close_input_not_found",
        ),
        (
            lambda paths: paths["replay_payload"].pop("daily_bars_csv"),
            "input_replay_missing_daily_bars_csv",
        ),
        (
            lambda paths: paths["replay_payload"].update({"daily_bars_csv": 123}),
            "input_replay_missing_daily_bars_csv",
        ),
        (
            lambda paths: _write_daily_bars_csv(
                paths["bars_csv"],
                [Decimal("100")] * 200,
                raw_equals_adjusted=True,
            ),
            "local_adjusted_close_input_not_adjusted",
        ),
        (
            lambda paths: _write_daily_bars_csv(
                paths["bars_csv"],
                [Decimal("100")] * 200,
                include_wrong_symbol=True,
            ),
            "ambiguous_local_adjusted_close_input_symbol_rows",
        ),
        (
            lambda paths: _write_daily_bars_csv(
                paths["bars_csv"],
                [Decimal("100")] * 200,
                reverse_dates=True,
            ),
            "ambiguous_local_adjusted_close_input_unsorted_dates",
        ),
    ],
)
def test_blocks_when_local_adjusted_close_input_is_missing_or_ambiguous(
    tmp_path: Path,
    mutator,
    expected_blocker: str,
) -> None:
    bars_csv = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        [Decimal("100")] * 150 + [Decimal("200")] * 50,
    )
    replay_payload = _m429_payload(bars_csv)
    mutator({"bars_csv": bars_csv, "replay_payload": replay_payload})
    replay_path = _write_replay_payload(tmp_path / "m429.jsonl", replay_payload)

    payload = build_etf_sma_authorized_adjusted_close_posture_snapshot(
        _config(replay_path)
    )

    _assert_blocked(payload, expected_blocker)


def test_output_remains_deterministic(tmp_path: Path) -> None:
    bars_csv = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        [Decimal("100")] * 150 + [Decimal("200")] * 50,
    )
    replay_path = _write_replay(tmp_path, bars_csv)
    config = _config(replay_path)

    first = build_etf_sma_authorized_adjusted_close_posture_snapshot(config)
    second = build_etf_sma_authorized_adjusted_close_posture_snapshot(config)

    assert first == second
    assert render_etf_sma_authorized_adjusted_close_posture_snapshot_json(
        first
    ) == render_etf_sma_authorized_adjusted_close_posture_snapshot_json(second)


def test_cli_writes_posture_snapshot_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    bars_csv = _write_daily_bars_csv(
        tmp_path / "adjusted.csv",
        [Decimal("100")] * 150 + [Decimal("200")] * 50,
    )
    replay_path = _write_replay(tmp_path, bars_csv)
    run_log = tmp_path / "m430_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M430 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m430_cli",
            "--run-log",
            str(run_log),
            "--replay-path",
            str(replay_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["posture_snapshot_status"] == _SUCCESS_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["posture_computed"] is True


def _assert_blocked(payload: dict[str, object], expected_blocker: str) -> None:
    assert payload["milestone"] == "M430"
    assert payload["posture_snapshot_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["posture_computed"] is False
    assert expected_blocker in payload["blockers"]
    assert payload["blocked_reason"] == expected_blocker
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    for field_name in _SUCCESS_ONLY_FIELDS:
        assert field_name not in payload
    for field_name in _POSTURE_FALSE_FIELDS + _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def _config(
    replay_path: Path,
) -> EtfSmaAuthorizedAdjustedClosePostureSnapshotConfig:
    return EtfSmaAuthorizedAdjustedClosePostureSnapshotConfig(
        run_id="unit_m430",
        symbol="SPY",
        replay_path=replay_path,
    )


def _write_replay(
    tmp_path: Path,
    daily_bars_csv: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _m429_payload(daily_bars_csv)
    if mutator is not None:
        mutator(payload)
    return _write_replay_payload(tmp_path / "m429.jsonl", payload)


def _write_replay_payload(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _m429_payload(daily_bars_csv: Path) -> dict[str, object]:
    payload: dict[str, object] = {
        "active_preferred_baseline": _PREFERRED_BASELINE,
        "active_preferred_basis": _PREFERRED_BASIS,
        "authorization_source_milestone": "M424",
        "backtest_replay_status": _INPUT_REPLAY_STATUS,
        "backtest_replayed": True,
        "baseline_source_milestone": "M422",
        "blockers": [],
        "command": "etf-sma-authorized-adjusted-baseline-backtest-replay",
        "comparison_basis": "matched_window",
        "daily_bars_csv": str(daily_bars_csv),
        "data_basis": _PREFERRED_BASIS,
        "downstream_comparison_authorized": True,
        "guard_source_milestone": "M423",
        "input_snapshot_status": (
            "authorized_adjusted_baseline_backtest_snapshot_materialized"
        ),
        "known_basis_delta_slice_count": 1,
        "known_basis_delta_slices": ["recovery_2023"],
        "matched_total_interval_count": _MATCHED_INTERVAL_COUNT,
        "metrics_source_milestone": "M427",
        "milestone": "M429",
        "new_market_data_loaded": False,
        "profit_claim": "none",
        "record_type": "etf_sma_authorized_adjusted_baseline_backtest_replay",
        "replay_scope": "authorized_adjusted_close_matched_window",
        "run_id": "unit_m429",
        "schema_version": "1",
        "snapshot_source_milestone": "M428",
        "source_evidence_milestone": "M421",
        "strategy_family": "etf_sma_50_200",
        "stub_source_milestone": "M425",
        "summary_source_milestone": "M426",
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload


def _write_daily_bars_csv(
    path: Path,
    adjusted_values: list[Decimal],
    *,
    raw_equals_adjusted: bool = False,
    include_wrong_symbol: bool = False,
    reverse_dates: bool = False,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    dates = [_bar_date(index) for index in range(len(adjusted_values))]
    if reverse_dates:
        dates = list(reversed(dates))
    for day, adjusted_close in zip(dates, adjusted_values):
        raw_close = (
            adjusted_close
            if raw_equals_adjusted
            else adjusted_close - Decimal("1")
        )
        rows.append(_csv_row("SPY", day, raw_close, adjusted_close))
    if include_wrong_symbol:
        rows.append(_csv_row("QQQ", _bar_date(len(adjusted_values)), Decimal("10"), Decimal("11")))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _csv_row(
    symbol: str,
    day: date,
    close: Decimal,
    adjusted_close: Decimal,
) -> str:
    return ",".join(
        (
            symbol,
            day.isoformat(),
            str(close),
            str(close + Decimal("1")),
            str(close - Decimal("1")),
            str(close),
            str(adjusted_close),
            "1000",
        )
    )


def _bar_date(index: int) -> date:
    return date(2025, 1, 1) + timedelta(days=index)
