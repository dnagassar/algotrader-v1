from __future__ import annotations

import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_authorized_adjusted_baseline_backtest_snapshot import (
    EtfSmaAuthorizedAdjustedBaselineBacktestSnapshotConfig,
    build_etf_sma_authorized_adjusted_baseline_backtest_snapshot,
    render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_json,
    write_etf_sma_authorized_adjusted_baseline_backtest_snapshot_jsonl,
)


_COMMAND = "etf-sma-authorized-adjusted-baseline-backtest-snapshot"
_INPUT_METRICS_STATUS = "authorized_adjusted_baseline_metrics_materialized"
_MATERIALIZED_STATUS = (
    "authorized_adjusted_baseline_backtest_snapshot_materialized"
)
_BLOCKED_STATUS = "blocked_authorized_metrics_required"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_NORMALIZED_METRIC_FIELDS = {
    "basis_delta_explanations",
    "basis_delta_review_required",
    "drawdown_conclusion_changes",
    "full_adjusted_history_evaluated_return_count",
    "full_window_return_deltas",
    "matched_evaluated_return_count",
    "matched_slice_comparisons",
    "return_conclusion_changes",
    "return_conclusions_unchanged",
}
_SUCCESS_ONLY_FIELDS = (
    "input_metrics_status",
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
    "source_evidence_milestone",
    "snapshot_scope",
    "normalized_metric_fields",
    "full_window_return_deltas",
    "matched_slice_comparisons",
)


def test_authorized_m427_metrics_materialize_backtest_snapshot(
    tmp_path: Path,
) -> None:
    metrics_path = _write_metrics(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    assert payload["run_id"] == "unit_m428"
    assert payload["symbol"] == "SPY"
    assert payload["milestone"] == "M428"
    assert payload["backtest_snapshot_status"] == _MATERIALIZED_STATUS
    assert payload["input_metrics_status"] == _INPUT_METRICS_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["backtest_snapshot_materialized"] is True
    assert payload["active_preferred_baseline"] == _PREFERRED_BASELINE
    assert payload["active_preferred_basis"] == _PREFERRED_BASIS
    assert payload["comparison_basis"] == "matched_window"
    assert payload["matched_total_interval_count"] == 1055
    assert payload["known_basis_delta_slices"] == ["recovery_2023"]
    assert payload["known_basis_delta_slice_count"] == 1
    assert payload["baseline_source_milestone"] == "M422"
    assert payload["guard_source_milestone"] == "M423"
    assert payload["authorization_source_milestone"] == "M424"
    assert payload["stub_source_milestone"] == "M425"
    assert payload["summary_source_milestone"] == "M426"
    assert payload["metrics_source_milestone"] == "M427"
    assert payload["source_evidence_milestone"] == "M421"
    assert payload["snapshot_scope"] == "authorized_adjusted_baseline_metrics_only"
    assert payload["metrics_recomputed"] is False
    assert payload["new_market_data_loaded"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    assert payload["matched_evaluated_return_count"] == 1055
    assert payload["full_adjusted_history_evaluated_return_count"] == 8195
    assert payload["full_window_return_deltas"] == (
        _metrics_payload()["full_window_return_deltas"]
    )
    assert payload["matched_slice_comparisons"] == (
        _metrics_payload()["matched_slice_comparisons"]
    )
    assert payload["basis_delta_explanations"] == (
        _metrics_payload()["basis_delta_explanations"]
    )
    assert set(payload["normalized_metric_fields"]) == _NORMALIZED_METRIC_FIELDS
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m428.jsonl"
    write_etf_sma_authorized_adjusted_baseline_backtest_snapshot_jsonl(
        payload,
        run_log,
    )
    lines = run_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == json.loads(
        render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_json(
            payload
        )
    )


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "input_metrics_artifact_not_found"),
        (
            lambda path: path.write_text("", encoding="utf-8"),
            "input_metrics_artifact_empty",
        ),
        (
            lambda path: path.write_text("{", encoding="utf-8"),
            "input_metrics_artifact_invalid_json_line_1",
        ),
        (
            lambda path: path.write_text("[]\n", encoding="utf-8"),
            "input_metrics_artifact_record_1_not_object",
        ),
        (
            lambda path: path.write_text(
                "\n".join(
                    [
                        json.dumps(_metrics_payload(), sort_keys=True),
                        json.dumps(_metrics_payload(), sort_keys=True),
                    ]
                )
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_input_metrics_artifact_record_count",
        ),
    ],
)
def test_blocks_when_m427_metrics_file_is_missing_empty_malformed_or_ambiguous(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    metrics_path = tmp_path / "m427.jsonl"
    writer(metrics_path)

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "metrics_materialization_status",
            "blocked_authorized_summary_required",
            "input_metrics_unexpected_metrics_materialization_status",
        ),
        (
            "input_summary_status",
            "blocked_authorized_stub_required",
            "input_metrics_unexpected_input_summary_status",
        ),
        (
            "downstream_comparison_authorized",
            False,
            "input_metrics_downstream_comparison_authorized_not_true",
        ),
        (
            "metrics_materialized",
            False,
            "input_metrics_metrics_materialized_not_true",
        ),
    ],
)
def test_blocks_when_m427_metrics_are_unauthorized(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize("field_name", _SAFETY_FALSE_FIELDS)
def test_blocks_when_m427_metrics_are_safety_dirty(
    tmp_path: Path,
    field_name: str,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: True}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, f"input_metrics_safety_flag_dirty_{field_name}")


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "active_preferred_baseline",
            "raw_close_matched_window",
            "input_metrics_unexpected_active_preferred_baseline",
        ),
        (
            "active_preferred_basis",
            "raw_close_price_return",
            "input_metrics_unexpected_active_preferred_basis",
        ),
        (
            "comparison_basis",
            "full_history",
            "input_metrics_unexpected_comparison_basis",
        ),
    ],
)
def test_blocks_when_baseline_basis_or_comparison_basis_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_symbol_drifts(tmp_path: Path) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({"symbol": "QQQ"}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, "input_metrics_unexpected_symbol")


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        ("milestone", "M426", "input_metrics_unexpected_milestone"),
        (
            "baseline_source_milestone",
            "M421",
            "input_metrics_unexpected_baseline_source_milestone",
        ),
        (
            "guard_source_milestone",
            "M422",
            "input_metrics_unexpected_guard_source_milestone",
        ),
        (
            "authorization_source_milestone",
            "M423",
            "input_metrics_unexpected_authorization_source_milestone",
        ),
        (
            "stub_source_milestone",
            "M424",
            "input_metrics_unexpected_stub_source_milestone",
        ),
        (
            "summary_source_milestone",
            "M425",
            "input_metrics_unexpected_summary_source_milestone",
        ),
        (
            "source_evidence_milestone",
            "M420",
            "input_metrics_unexpected_source_evidence_milestone",
        ),
    ],
)
def test_blocks_when_milestone_or_source_milestone_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_interval_count_drifts(tmp_path: Path) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update(
            {"matched_total_interval_count": 1054}
        ),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(
        payload,
        "input_metrics_unexpected_matched_total_interval_count",
    )


def test_blocks_when_known_basis_delta_slices_drift(tmp_path: Path) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({"known_basis_delta_slices": []}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, "input_metrics_unexpected_known_basis_delta_slices")


def test_blocks_when_known_basis_delta_slice_count_drifts(
    tmp_path: Path,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update(
            {"known_basis_delta_slice_count": 2}
        ),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(
        payload,
        "input_metrics_unexpected_known_basis_delta_slice_count",
    )


@pytest.mark.parametrize(
    ("field_name", "expected_blocker"),
    [
        ("metrics_recomputed", "input_metrics_metrics_recomputed_not_false"),
        (
            "new_market_data_loaded",
            "input_metrics_new_market_data_loaded_not_false",
        ),
    ],
)
def test_blocks_when_metrics_were_recomputed_or_market_data_loaded(
    tmp_path: Path,
    field_name: str,
    expected_blocker: str,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: True}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "trade_recommendation",
            "buy",
            "input_metrics_unexpected_trade_recommendation",
        ),
        ("profit_claim", "positive", "input_metrics_unexpected_profit_claim"),
    ],
)
def test_blocks_when_trade_or_profit_claim_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    _assert_blocked(payload, expected_blocker)


def test_optional_metric_absence_is_omitted_without_recomputing(
    tmp_path: Path,
) -> None:
    metrics_path = _write_metrics(
        tmp_path,
        mutator=lambda payload: payload.pop("basis_delta_explanations"),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(
        _config(metrics_path)
    )

    assert payload["backtest_snapshot_status"] == _MATERIALIZED_STATUS
    assert payload["backtest_snapshot_materialized"] is True
    assert "basis_delta_explanations" not in payload
    assert "basis_delta_explanations" not in payload["normalized_metric_fields"]
    assert payload["metrics_recomputed"] is False
    assert payload["new_market_data_loaded"] is False


def test_output_remains_deterministic(tmp_path: Path) -> None:
    metrics_path = _write_metrics(tmp_path)
    config = _config(metrics_path)

    first = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(config)
    second = build_etf_sma_authorized_adjusted_baseline_backtest_snapshot(config)

    assert first == second
    assert render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_json(
        first
    ) == render_etf_sma_authorized_adjusted_baseline_backtest_snapshot_json(
        second
    )


def test_cli_writes_snapshot_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    metrics_path = _write_metrics(tmp_path)
    run_log = tmp_path / "m428_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M428 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m428_cli",
            "--run-log",
            str(run_log),
            "--metrics-path",
            str(metrics_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["backtest_snapshot_status"] == _MATERIALIZED_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["backtest_snapshot_materialized"] is True


def _assert_blocked(payload: dict[str, object], expected_blocker: str) -> None:
    assert payload["milestone"] == "M428"
    assert payload["backtest_snapshot_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["backtest_snapshot_materialized"] is False
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
    metrics_path: Path,
) -> EtfSmaAuthorizedAdjustedBaselineBacktestSnapshotConfig:
    return EtfSmaAuthorizedAdjustedBaselineBacktestSnapshotConfig(
        run_id="unit_m428",
        symbol="SPY",
        metrics_path=metrics_path,
    )


def _write_metrics(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _metrics_payload()
    if mutator is not None:
        mutator(payload)

    metrics_path = tmp_path / "m427.jsonl"
    metrics_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metrics_path


def _metrics_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "active_preferred_baseline": _PREFERRED_BASELINE,
        "active_preferred_basis": _PREFERRED_BASIS,
        "authorization_source_milestone": "M424",
        "baseline_source_milestone": "M422",
        "basis_delta_explanations": [
            {
                "changed_field": "drawdown_conclusion",
                "slice_name": "recovery_2023",
            }
        ],
        "basis_delta_review_required": True,
        "blockers": [],
        "broker_mutation_status": "none",
        "command": "etf-sma-authorized-adjusted-baseline-metrics",
        "comparison_basis": "matched_window",
        "credential_access_status": "not_attempted",
        "downstream_comparison_authorized": True,
        "drawdown_conclusion_changes": ["recovery_2023"],
        "full_adjusted_history_evaluated_return_count": 8195,
        "full_window_return_deltas": {
            "benchmark_total_return": {
                "adjusted": "0.75",
                "delta": "0.09",
                "raw": "0.66",
            },
            "strategy_total_return": {
                "adjusted": "0.62",
                "delta": "0.08",
                "raw": "0.54",
            },
        },
        "guard_source_milestone": "M423",
        "input_summary_status": (
            "authorized_preferred_baseline_summary_evaluated"
        ),
        "known_basis_delta_slice_count": 1,
        "known_basis_delta_slices": ["recovery_2023"],
        "matched_evaluated_return_count": 1055,
        "matched_slice_comparisons": [
            {
                "adjusted_drawdown_conclusion": (
                    "strategy_drawdown_above_benchmark"
                ),
                "adjusted_evaluated_return_count": 250,
                "adjusted_return_conclusion": (
                    "strategy_return_below_benchmark"
                ),
                "drawdown_conclusion_unchanged": False,
                "raw_drawdown_conclusion": "strategy_drawdown_below_benchmark",
                "raw_evaluated_return_count": 250,
                "raw_return_conclusion": "strategy_return_below_benchmark",
                "return_conclusion_unchanged": True,
                "same_evaluated_return_count": True,
                "same_slice_dates": True,
                "slice_name": "recovery_2023",
                "status": "compared",
            }
        ],
        "matched_total_interval_count": 1055,
        "metrics_materialization_status": _INPUT_METRICS_STATUS,
        "metrics_materialized": True,
        "metrics_recomputed": False,
        "metrics_source_basis": _PREFERRED_BASIS,
        "milestone": "M427",
        "network_broker_access_status": "not_attempted",
        "new_market_data_loaded": False,
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "operator_trade_recommendation": "none",
        "paper_lab_only": True,
        "profit_claim": "none",
        "record_type": (
            "etf_sma_authorized_adjusted_baseline_metrics_materialization"
        ),
        "research_only": True,
        "return_conclusion_changes": [],
        "return_conclusions_unchanged": True,
        "run_id": "unit_m427",
        "schema_version": "1",
        "signal_evaluation_only": True,
        "source_evidence_milestone": "M421",
        "stub_source_milestone": "M425",
        "summary_source_milestone": "M426",
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload
