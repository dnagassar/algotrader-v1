from __future__ import annotations

import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_authorized_comparison_summary import (
    EtfSmaAuthorizedComparisonSummaryConfig,
    build_etf_sma_authorized_comparison_summary,
    render_etf_sma_authorized_comparison_summary_json,
    write_etf_sma_authorized_comparison_summary_jsonl,
)


_COMMAND = "etf-sma-authorized-comparison-summary"
_INPUT_STUB_STATUS = "authorized_comparison_stub_evaluated"
_AUTHORIZED_STATUS = "authorized_preferred_baseline_summary_evaluated"
_BLOCKED_STATUS = "blocked_authorized_stub_required"
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
_SUCCESS_ONLY_FIELDS = (
    "input_stub_status",
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
)


def test_authorized_m425_stub_produces_one_authorized_m426_summary_record(
    tmp_path: Path,
) -> None:
    stub_path = _write_stub(tmp_path)

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    assert payload["run_id"] == "unit_m426"
    assert payload["symbol"] == "SPY"
    assert payload["milestone"] == "M426"
    assert payload["comparison_summary_status"] == _AUTHORIZED_STATUS
    assert payload["input_stub_status"] == _INPUT_STUB_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["summary_performed"] is True
    assert payload["summary_scope"] == "authorized_stub_only"
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
    assert payload["metrics_recomputed"] is False
    assert payload["new_performance_metrics_computed"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m426.jsonl"
    write_etf_sma_authorized_comparison_summary_jsonl(payload, run_log)
    lines = run_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == json.loads(
        render_etf_sma_authorized_comparison_summary_json(payload)
    )


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "comparison_stub_artifact_not_found"),
        (
            lambda path: path.write_text("", encoding="utf-8"),
            "comparison_stub_artifact_empty",
        ),
        (
            lambda path: path.write_text("{", encoding="utf-8"),
            "comparison_stub_artifact_invalid_json_line_1",
        ),
        (
            lambda path: path.write_text("[]\n", encoding="utf-8"),
            "comparison_stub_artifact_record_1_not_object",
        ),
        (
            lambda path: path.write_text(
                "\n".join(
                    [
                        json.dumps(_stub_payload(), sort_keys=True),
                        json.dumps(_stub_payload(), sort_keys=True),
                    ]
                )
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_comparison_stub_artifact_record_count",
        ),
    ],
)
def test_blocks_when_stub_artifact_is_missing_empty_malformed_or_ambiguous(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    stub_path = tmp_path / "m425.jsonl"
    writer(stub_path)

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "comparison_stub_status",
            "blocked_authorization_required",
            "comparison_stub_unexpected_comparison_stub_status",
        ),
        (
            "downstream_comparison_authorized",
            False,
            "comparison_stub_downstream_comparison_authorized_not_true",
        ),
        (
            "evaluation_performed",
            False,
            "comparison_stub_evaluation_performed_not_true",
        ),
    ],
)
def test_blocks_when_m425_stub_is_unauthorized(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    stub_path = _write_stub(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(payload, expected_blocker)


@pytest.mark.parametrize("field_name", _SAFETY_FALSE_FIELDS)
def test_blocks_when_m425_stub_is_safety_dirty(
    tmp_path: Path,
    field_name: str,
) -> None:
    stub_path = _write_stub(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: True}),
    )

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(
        payload,
        f"comparison_stub_safety_flag_dirty_{field_name}",
    )


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "active_preferred_baseline",
            "raw_close_matched_window",
            "comparison_stub_unexpected_active_preferred_baseline",
        ),
        (
            "active_preferred_basis",
            "raw_close_price_return",
            "comparison_stub_unexpected_active_preferred_basis",
        ),
        (
            "comparison_basis",
            "full_history",
            "comparison_stub_unexpected_comparison_basis",
        ),
    ],
)
def test_blocks_when_baseline_basis_or_comparison_basis_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    stub_path = _write_stub(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_symbol_drifts(tmp_path: Path) -> None:
    stub_path = _write_stub(
        tmp_path,
        mutator=lambda payload: payload.update({"symbol": "QQQ"}),
    )

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(payload, "comparison_stub_unexpected_symbol")


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        ("milestone", "M424", "comparison_stub_unexpected_milestone"),
        (
            "baseline_source_milestone",
            "M421",
            "comparison_stub_unexpected_baseline_source_milestone",
        ),
        (
            "guard_source_milestone",
            "M422",
            "comparison_stub_unexpected_guard_source_milestone",
        ),
        (
            "authorization_source_milestone",
            "M423",
            "comparison_stub_unexpected_authorization_source_milestone",
        ),
    ],
)
def test_blocks_when_milestone_or_source_milestone_drifts(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    stub_path = _write_stub(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(payload, expected_blocker)


def test_blocks_when_interval_count_drifts(tmp_path: Path) -> None:
    stub_path = _write_stub(
        tmp_path,
        mutator=lambda payload: payload.update(
            {"matched_total_interval_count": 1054}
        ),
    )

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(
        payload,
        "comparison_stub_unexpected_matched_total_interval_count",
    )


def test_blocks_when_known_basis_delta_slices_drift(tmp_path: Path) -> None:
    stub_path = _write_stub(
        tmp_path,
        mutator=lambda payload: payload.update({"known_basis_delta_slices": []}),
    )

    payload = build_etf_sma_authorized_comparison_summary(_config(stub_path))

    _assert_blocked(payload, "comparison_stub_unexpected_known_basis_delta_slices")


def test_output_remains_deterministic(tmp_path: Path) -> None:
    stub_path = _write_stub(tmp_path)
    config = _config(stub_path)

    first = build_etf_sma_authorized_comparison_summary(config)
    second = build_etf_sma_authorized_comparison_summary(config)

    assert first == second
    assert render_etf_sma_authorized_comparison_summary_json(
        first
    ) == render_etf_sma_authorized_comparison_summary_json(second)


def test_cli_writes_summary_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    stub_path = _write_stub(tmp_path)
    run_log = tmp_path / "m426_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M426 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m426_cli",
            "--run-log",
            str(run_log),
            "--stub-path",
            str(stub_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["comparison_summary_status"] == _AUTHORIZED_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["summary_performed"] is True


def _assert_blocked(payload: dict[str, object], expected_blocker: str) -> None:
    assert payload["milestone"] == "M426"
    assert payload["comparison_summary_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["summary_performed"] is False
    assert expected_blocker in payload["blockers"]
    assert payload["blocked_reason"] == expected_blocker
    assert payload["metrics_recomputed"] is False
    assert payload["new_performance_metrics_computed"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    for field_name in _SUCCESS_ONLY_FIELDS:
        assert field_name not in payload
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def _config(stub_path: Path) -> EtfSmaAuthorizedComparisonSummaryConfig:
    return EtfSmaAuthorizedComparisonSummaryConfig(
        run_id="unit_m426",
        symbol="SPY",
        stub_path=stub_path,
    )


def _write_stub(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _stub_payload()
    if mutator is not None:
        mutator(payload)

    stub_path = tmp_path / "m425.jsonl"
    stub_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return stub_path


def _stub_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "active_preferred_baseline": _PREFERRED_BASELINE,
        "active_preferred_basis": _PREFERRED_BASIS,
        "authorization_path": (
            "runs\\paper_lab\\"
            "m424_guarded_preferred_baseline_comparison_authorization.jsonl"
        ),
        "authorization_source_milestone": "M424",
        "baseline_source_milestone": "M422",
        "blockers": [],
        "broker_mutation_status": "none",
        "command": "etf-sma-authorized-comparison-stub",
        "comparison_basis": "matched_window",
        "comparison_stub_status": _INPUT_STUB_STATUS,
        "credential_access_status": "not_attempted",
        "downstream_comparison_authorized": True,
        "evaluation_performed": True,
        "evaluation_scope": "stub_only",
        "guard_source_milestone": "M423",
        "input_authorization_status": "preferred_baseline_guard_passed",
        "known_basis_delta_slices": ["recovery_2023"],
        "matched_total_interval_count": 1055,
        "metrics_computed": False,
        "milestone": "M425",
        "network_broker_access_status": "not_attempted",
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "operator_trade_recommendation": "none",
        "paper_lab_only": True,
        "profit_claim": "none",
        "record_type": "etf_sma_authorization_consumed_comparison_stub",
        "research_only": True,
        "run_id": "unit_m425",
        "schema_version": "1",
        "signal_evaluation_only": True,
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload
