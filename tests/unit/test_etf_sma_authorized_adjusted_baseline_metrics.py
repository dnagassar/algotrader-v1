from __future__ import annotations

import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_authorized_adjusted_baseline_metrics import (
    EtfSmaAuthorizedAdjustedBaselineMetricsConfig,
    build_etf_sma_authorized_adjusted_baseline_metrics,
    render_etf_sma_authorized_adjusted_baseline_metrics_json,
    write_etf_sma_authorized_adjusted_baseline_metrics_jsonl,
)


_COMMAND = "etf-sma-authorized-adjusted-baseline-metrics"
_INPUT_SUMMARY_STATUS = "authorized_preferred_baseline_summary_evaluated"
_INPUT_STUB_STATUS = "authorized_comparison_stub_evaluated"
_MATERIALIZED_STATUS = "authorized_adjusted_baseline_metrics_materialized"
_BLOCKED_STATUS = "blocked_authorized_summary_required"
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
_SOURCE_EVIDENCE_FALSE_FIELDS = (
    *_SAFETY_FALSE_FIELDS,
    "submit_authorized",
    "submit_path_allowed",
    "paper_submit_approved",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "credential_access",
    "broker_network_access",
    "broker_actions_performed",
    "market_data_fetch_performed",
)
_SUCCESS_ONLY_FIELDS = (
    "input_summary_status",
    "metrics_source_basis",
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
    "source_evidence_milestone",
    "matched_slice_comparisons",
    "full_window_return_deltas",
)


def test_authorized_m426_summary_materializes_m421_adjusted_metrics(
    tmp_path: Path,
) -> None:
    summary_path = _write_summary(tmp_path)
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    assert payload["run_id"] == "unit_m427"
    assert payload["symbol"] == "SPY"
    assert payload["milestone"] == "M427"
    assert payload["metrics_materialization_status"] == _MATERIALIZED_STATUS
    assert payload["input_summary_status"] == _INPUT_SUMMARY_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["metrics_materialized"] is True
    assert payload["metrics_materialization_scope"] == "existing_local_evidence_only"
    assert payload["metrics_source_basis"] == _PREFERRED_BASIS
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
    assert payload["source_evidence_milestone"] == "M421"
    assert payload["source_evidence_status"] == (
        "ready_to_promote_adjusted_matched_window_basis"
    )
    assert payload["metrics_recomputed"] is False
    assert payload["new_market_data_loaded"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    assert payload["matched_evaluated_return_count"] == 1055
    assert payload["full_adjusted_history_evaluated_return_count"] == 8195
    assert payload["full_window_return_deltas"] == (
        _source_evidence_payload()["full_window_return_deltas"]
    )
    assert payload["matched_slice_comparisons"] == (
        _source_evidence_payload()["matched_slice_comparisons"]
    )
    assert set(payload["metrics_materialized_fields"]) == {
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
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m427.jsonl"
    write_etf_sma_authorized_adjusted_baseline_metrics_jsonl(payload, run_log)
    lines = run_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == json.loads(
        render_etf_sma_authorized_adjusted_baseline_metrics_json(payload)
    )


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "authorized_summary_artifact_not_found"),
        (
            lambda path: path.write_text("", encoding="utf-8"),
            "authorized_summary_artifact_empty",
        ),
        (
            lambda path: path.write_text("{", encoding="utf-8"),
            "authorized_summary_artifact_invalid_json_line_1",
        ),
        (
            lambda path: path.write_text("[]\n", encoding="utf-8"),
            "authorized_summary_artifact_record_1_not_object",
        ),
        (
            lambda path: path.write_text(
                "\n".join(
                    [
                        json.dumps(_summary_payload(), sort_keys=True),
                        json.dumps(_summary_payload(), sort_keys=True),
                    ]
                )
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_authorized_summary_artifact_record_count",
        ),
    ],
)
def test_blocks_when_m426_summary_is_missing_empty_malformed_or_ambiguous(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    summary_path = tmp_path / "m426.jsonl"
    writer(summary_path)
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "comparison_summary_status",
            "blocked_authorized_stub_required",
            "authorized_summary_unexpected_comparison_summary_status",
        ),
        (
            "input_stub_status",
            "blocked_authorization_required",
            "authorized_summary_unexpected_input_stub_status",
        ),
        (
            "downstream_comparison_authorized",
            False,
            "authorized_summary_downstream_comparison_authorized_not_true",
        ),
        (
            "summary_performed",
            False,
            "authorized_summary_summary_performed_not_true",
        ),
    ],
)
def test_blocks_when_m426_summary_is_unauthorized(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize("field_name", _SAFETY_FALSE_FIELDS)
def test_blocks_when_m426_summary_is_safety_dirty(
    tmp_path: Path,
    field_name: str,
) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: True}),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, f"authorized_summary_safety_flag_dirty_{field_name}")


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "active_preferred_baseline",
            "raw_close_matched_window",
            "authorized_summary_unexpected_active_preferred_baseline",
        ),
        (
            "active_preferred_basis",
            "raw_close_price_return",
            "authorized_summary_unexpected_active_preferred_basis",
        ),
        (
            "comparison_basis",
            "full_history",
            "authorized_summary_unexpected_comparison_basis",
        ),
    ],
)
def test_blocks_when_baseline_basis_or_comparison_basis_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_symbol_drifts(tmp_path: Path) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update({"symbol": "QQQ"}),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, "authorized_summary_unexpected_symbol")


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        ("milestone", "M425", "authorized_summary_unexpected_milestone"),
        (
            "baseline_source_milestone",
            "M421",
            "authorized_summary_unexpected_baseline_source_milestone",
        ),
        (
            "guard_source_milestone",
            "M422",
            "authorized_summary_unexpected_guard_source_milestone",
        ),
        (
            "authorization_source_milestone",
            "M423",
            "authorized_summary_unexpected_authorization_source_milestone",
        ),
        (
            "stub_source_milestone",
            "M424",
            "authorized_summary_unexpected_stub_source_milestone",
        ),
    ],
)
def test_blocks_when_milestone_or_source_milestone_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_interval_count_drifts(tmp_path: Path) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update(
            {"matched_total_interval_count": 1054}
        ),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(
        payload,
        "authorized_summary_unexpected_matched_total_interval_count",
    )


def test_blocks_when_known_basis_delta_slices_drift(tmp_path: Path) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update({"known_basis_delta_slices": []}),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, "authorized_summary_unexpected_known_basis_delta_slices")


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "trade_recommendation",
            "buy",
            "authorized_summary_unexpected_trade_recommendation",
        ),
        ("profit_claim", "positive", "authorized_summary_unexpected_profit_claim"),
    ],
)
def test_blocks_when_trade_or_profit_claim_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    summary_path = _write_summary(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )
    evidence_path = _write_source_evidence(tmp_path)

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_required_local_evidence_is_missing(tmp_path: Path) -> None:
    summary_path = _write_summary(tmp_path)
    evidence_path = tmp_path / "m421_missing.jsonl"

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, "source_evidence_artifact_not_found")


def test_blocks_when_required_local_metric_is_missing(tmp_path: Path) -> None:
    summary_path = _write_summary(tmp_path)
    evidence_path = _write_source_evidence(
        tmp_path,
        mutator=lambda payload: payload.pop("full_window_return_deltas"),
    )

    payload = build_etf_sma_authorized_adjusted_baseline_metrics(
        _config(summary_path, evidence_path)
    )

    _assert_blocked(payload, "source_evidence_metric_missing_full_window_return_deltas")


def test_output_remains_deterministic(tmp_path: Path) -> None:
    summary_path = _write_summary(tmp_path)
    evidence_path = _write_source_evidence(tmp_path)
    config = _config(summary_path, evidence_path)

    first = build_etf_sma_authorized_adjusted_baseline_metrics(config)
    second = build_etf_sma_authorized_adjusted_baseline_metrics(config)

    assert first == second
    assert render_etf_sma_authorized_adjusted_baseline_metrics_json(
        first
    ) == render_etf_sma_authorized_adjusted_baseline_metrics_json(second)


def test_cli_writes_metrics_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    summary_path = _write_summary(tmp_path)
    evidence_path = _write_source_evidence(tmp_path)
    run_log = tmp_path / "m427_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M427 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m427_cli",
            "--run-log",
            str(run_log),
            "--summary-path",
            str(summary_path),
            "--source-evidence-path",
            str(evidence_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["metrics_materialization_status"] == _MATERIALIZED_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["metrics_materialized"] is True


def _assert_blocked(payload: dict[str, object], expected_blocker: str) -> None:
    assert payload["milestone"] == "M427"
    assert payload["metrics_materialization_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["metrics_materialized"] is False
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
    summary_path: Path,
    evidence_path: Path,
) -> EtfSmaAuthorizedAdjustedBaselineMetricsConfig:
    return EtfSmaAuthorizedAdjustedBaselineMetricsConfig(
        run_id="unit_m427",
        symbol="SPY",
        summary_path=summary_path,
        source_evidence_path=evidence_path,
    )


def _write_summary(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _summary_payload()
    if mutator is not None:
        mutator(payload)

    summary_path = tmp_path / "m426.jsonl"
    summary_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary_path


def _write_source_evidence(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _source_evidence_payload()
    if mutator is not None:
        mutator(payload)

    evidence_path = tmp_path / "m421.jsonl"
    evidence_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence_path


def _summary_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "active_preferred_baseline": _PREFERRED_BASELINE,
        "active_preferred_basis": _PREFERRED_BASIS,
        "authorization_source_milestone": "M424",
        "baseline_source_milestone": "M422",
        "blockers": [],
        "broker_mutation_status": "none",
        "command": "etf-sma-authorized-comparison-summary",
        "comparison_basis": "matched_window",
        "comparison_summary_status": _INPUT_SUMMARY_STATUS,
        "credential_access_status": "not_attempted",
        "downstream_comparison_authorized": True,
        "guard_source_milestone": "M423",
        "input_stub_status": _INPUT_STUB_STATUS,
        "known_basis_delta_slice_count": 1,
        "known_basis_delta_slices": ["recovery_2023"],
        "matched_total_interval_count": 1055,
        "metrics_recomputed": False,
        "milestone": "M426",
        "network_broker_access_status": "not_attempted",
        "new_performance_metrics_computed": False,
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "operator_trade_recommendation": "none",
        "paper_lab_only": True,
        "profit_claim": "none",
        "record_type": "etf_sma_authorized_preferred_baseline_comparison_summary",
        "research_only": True,
        "run_id": "unit_m426",
        "schema_version": "1",
        "signal_evaluation_only": True,
        "stub_path": (
            "runs\\paper_lab\\"
            "m425_authorization_consumed_etf_sma_comparison_stub.jsonl"
        ),
        "stub_source_milestone": "M425",
        "summary_performed": True,
        "summary_scope": "authorized_stub_only",
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload


def _source_evidence_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "adjusted_basis": _PREFERRED_BASIS,
        "baseline_recommendation": _PREFERRED_BASELINE,
        "basis_delta_explanations": [
            {
                "changed_field": "drawdown_conclusion",
                "slice_name": "recovery_2023",
            }
        ],
        "basis_delta_review_required": True,
        "blockers": [],
        "broker_mutation_status": "none",
        "command": "etf-sma-adjusted-basis-promotion-packet",
        "comparison_basis": "matched_window",
        "credential_access_status": "not_attempted",
        "drawdown_conclusion_changes": ["recovery_2023"],
        "full_adjusted_history_evaluated_return_count": 8195,
        "full_window_return_deltas": {
            "benchmark_total_return": {
                "adjusted": "0.757757631674850346984645900",
                "delta": "0.098066819550365097541589131",
                "raw": "0.659690812124485249443056769",
            },
            "strategy_total_return": {
                "adjusted": "0.62307367524076557019890148",
                "delta": "0.07889589203503783429444773",
                "raw": "0.54417778320572773590445375",
            },
        },
        "m417a_slice_counts_unchanged": True,
        "matched_evaluated_return_count": 1055,
        "matched_slice_comparisons": _matched_slice_comparisons(),
        "matched_total_interval_count": 1055,
        "milestone": "M421",
        "network_broker_access_status": "not_attempted",
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "operator_trade_recommendation": "none",
        "paper_lab_only": True,
        "preferred_offline_baseline_ready": True,
        "profit_claim": "none",
        "promotion_status": "ready_to_promote_adjusted_matched_window_basis",
        "raw_basis": "raw_close_price_return",
        "record_type": "etf_sma_adjusted_basis_promotion_packet",
        "research_only": True,
        "return_conclusion_changes": [],
        "return_conclusions_unchanged": True,
        "run_id": "unit_m421",
        "same_slice_counts": True,
        "same_slice_dates": True,
        "schema_version": "1",
        "signal_evaluation_only": True,
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SOURCE_EVIDENCE_FALSE_FIELDS:
        payload[field_name] = False
    return payload


def _matched_slice_comparisons() -> list[dict[str, object]]:
    return [
        _slice_comparison("full_evaluated_window", 1055),
        _slice_comparison("stress_2022", 197),
        _slice_comparison("recovery_2023", 250, drawdown_changed=True),
        _slice_comparison("bull_2024", 252),
        _slice_comparison("whipsaw_2025", 250),
        _slice_comparison("ytd_2026", 106),
    ]


def _slice_comparison(
    slice_name: str,
    count: int,
    *,
    drawdown_changed: bool = False,
) -> dict[str, object]:
    raw_drawdown = "strategy_drawdown_below_benchmark"
    adjusted_drawdown = (
        "strategy_drawdown_above_benchmark"
        if drawdown_changed
        else raw_drawdown
    )
    return {
        "adjusted_benchmark_max_drawdown": "0.22",
        "adjusted_benchmark_total_return": "0.75",
        "adjusted_drawdown_conclusion": adjusted_drawdown,
        "adjusted_evaluated_return_count": count,
        "adjusted_return_conclusion": "strategy_return_below_benchmark",
        "adjusted_strategy_max_drawdown": "0.18",
        "adjusted_strategy_total_return": "0.62",
        "benchmark_max_drawdown_delta": "-0.01",
        "benchmark_total_return_delta": "0.09",
        "drawdown_conclusion_unchanged": not drawdown_changed,
        "raw_benchmark_max_drawdown": "0.23",
        "raw_benchmark_total_return": "0.66",
        "raw_drawdown_conclusion": raw_drawdown,
        "raw_evaluated_return_count": count,
        "raw_return_conclusion": "strategy_return_below_benchmark",
        "raw_strategy_max_drawdown": "0.19",
        "raw_strategy_total_return": "0.54",
        "return_conclusion_unchanged": True,
        "same_evaluated_return_count": True,
        "same_slice_dates": True,
        "slice_name": slice_name,
        "status": "compared",
        "strategy_max_drawdown_delta": "-0.01",
        "strategy_total_return_delta": "0.08",
    }
