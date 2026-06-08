from __future__ import annotations

import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_authorization_consumed_comparison import (
    EtfSmaAuthorizationConsumedComparisonConfig,
    build_etf_sma_authorization_consumed_comparison_stub,
    render_etf_sma_authorization_consumed_comparison_json,
    write_etf_sma_authorization_consumed_comparison_jsonl,
)


_COMMAND = "etf-sma-authorized-comparison-stub"
_INPUT_AUTHORIZATION_STATUS = "preferred_baseline_guard_passed"
_AUTHORIZED_STATUS = "authorized_comparison_stub_evaluated"
_BLOCKED_STATUS = "blocked_authorization_required"
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
    "input_authorization_status",
    "active_preferred_baseline",
    "active_preferred_basis",
    "comparison_basis",
    "matched_total_interval_count",
    "known_basis_delta_slices",
    "baseline_source_milestone",
    "guard_source_milestone",
    "authorization_source_milestone",
)


def test_authorized_comparison_stub_success_path_from_m424_authorization(
    tmp_path: Path,
) -> None:
    authorization_path = _write_authorization(tmp_path)

    payload = build_etf_sma_authorization_consumed_comparison_stub(
        _config(authorization_path)
    )

    assert payload["run_id"] == "unit_m425"
    assert payload["symbol"] == "SPY"
    assert payload["milestone"] == "M425"
    assert payload["comparison_stub_status"] == _AUTHORIZED_STATUS
    assert payload["input_authorization_status"] == _INPUT_AUTHORIZATION_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["evaluation_performed"] is True
    assert payload["active_preferred_baseline"] == _PREFERRED_BASELINE
    assert payload["active_preferred_basis"] == _PREFERRED_BASIS
    assert payload["comparison_basis"] == "matched_window"
    assert payload["matched_total_interval_count"] == 1055
    assert payload["known_basis_delta_slices"] == ["recovery_2023"]
    assert payload["baseline_source_milestone"] == "M422"
    assert payload["guard_source_milestone"] == "M423"
    assert payload["authorization_source_milestone"] == "M424"
    assert payload["evaluation_scope"] == "stub_only"
    assert payload["metrics_computed"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m425.jsonl"
    write_etf_sma_authorization_consumed_comparison_jsonl(payload, run_log)
    assert json.loads(run_log.read_text(encoding="utf-8")) == json.loads(
        render_etf_sma_authorization_consumed_comparison_json(payload)
    )


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "authorization_artifact_not_found"),
        (
            lambda path: path.write_text("{", encoding="utf-8"),
            "authorization_artifact_invalid_json_line_1",
        ),
        (
            lambda path: path.write_text("[]\n", encoding="utf-8"),
            "authorization_artifact_record_1_not_object",
        ),
        (
            lambda path: path.write_text("\n", encoding="utf-8"),
            "authorization_artifact_empty",
        ),
        (
            lambda path: path.write_text(
                "\n".join(
                    [
                        json.dumps(_authorization_payload(), sort_keys=True),
                        json.dumps(_authorization_payload(), sort_keys=True),
                    ]
                )
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_authorization_artifact_record_count",
        ),
    ],
)
def test_blocks_when_authorization_artifact_is_missing_invalid_or_ambiguous(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    authorization_path = tmp_path / "m424.jsonl"
    writer(authorization_path)

    payload = build_etf_sma_authorization_consumed_comparison_stub(
        _config(authorization_path)
    )

    assert payload["comparison_stub_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["evaluation_performed"] is False
    assert expected_blocker in payload["blockers"]
    assert payload["blocked_reason"] == expected_blocker
    assert payload["metrics_computed"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    for field_name in _SUCCESS_ONLY_FIELDS:
        assert field_name not in payload
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        ("downstream_comparison_authorized", False, "authorization_downstream_comparison_authorized_not_true"),
        ("active_preferred_baseline", "raw_close_matched_window", "authorization_unexpected_active_preferred_baseline"),
        ("active_preferred_basis", "raw_close_price_return", "authorization_unexpected_active_preferred_basis"),
        ("comparison_basis", "full_history", "authorization_unexpected_comparison_basis"),
        ("known_basis_delta_slices", [], "authorization_unexpected_known_basis_delta_slices"),
        ("baseline_source_milestone", "M421", "authorization_unexpected_baseline_source_milestone"),
        ("guard_source_milestone", "M422", "authorization_unexpected_guard_source_milestone"),
        ("milestone", "M423", "authorization_unexpected_milestone"),
        ("submitted", True, "authorization_safety_flag_dirty_submitted"),
        ("mutated", True, "authorization_safety_flag_dirty_mutated"),
        (
            "broker_action_performed",
            True,
            "authorization_safety_flag_dirty_broker_action_performed",
        ),
        (
            "network_access_attempted",
            True,
            "authorization_safety_flag_dirty_network_access_attempted",
        ),
        (
            "credential_access_attempted",
            True,
            "authorization_safety_flag_dirty_credential_access_attempted",
        ),
        ("live_authorized", True, "authorization_safety_flag_dirty_live_authorized"),
    ],
)
def test_blocks_when_m424_authorization_contract_is_not_authorized_or_safe(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    authorization_path = _write_authorization(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_authorization_consumed_comparison_stub(
        _config(authorization_path)
    )

    assert payload["comparison_stub_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["evaluation_performed"] is False
    assert expected_blocker in payload["blockers"]
    for success_field in _SUCCESS_ONLY_FIELDS:
        assert success_field not in payload
    for safety_field in _SAFETY_FALSE_FIELDS:
        assert payload[safety_field] is False


def test_blocks_when_authorized_interval_count_drifts(tmp_path: Path) -> None:
    authorization_path = _write_authorization(
        tmp_path,
        mutator=lambda payload: payload.update(
            {"matched_total_interval_count": 1054}
        ),
    )

    payload = build_etf_sma_authorization_consumed_comparison_stub(
        _config(authorization_path)
    )

    assert payload["comparison_stub_status"] == _BLOCKED_STATUS
    assert "authorization_unexpected_matched_total_interval_count" in (
        payload["blockers"]
    )
    assert payload["evaluation_performed"] is False


def test_cli_writes_stub_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    authorization_path = _write_authorization(tmp_path)
    run_log = tmp_path / "m425_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M425 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m425_cli",
            "--run-log",
            str(run_log),
            "--authorization-path",
            str(authorization_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["comparison_stub_status"] == _AUTHORIZED_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["evaluation_performed"] is True


def _config(
    authorization_path: Path,
) -> EtfSmaAuthorizationConsumedComparisonConfig:
    return EtfSmaAuthorizationConsumedComparisonConfig(
        run_id="unit_m425",
        symbol="SPY",
        authorization_path=authorization_path,
    )


def _write_authorization(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _authorization_payload()
    if mutator is not None:
        mutator(payload)

    authorization_path = tmp_path / "m424.jsonl"
    authorization_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return authorization_path


def _authorization_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "active_preferred_baseline": _PREFERRED_BASELINE,
        "active_preferred_basis": _PREFERRED_BASIS,
        "baseline_source_milestone": "M422",
        "blockers": [],
        "broker_mutation_status": "none",
        "command": "etf-sma-preferred-baseline-comparison-guard",
        "comparison_authorization_status": _INPUT_AUTHORIZATION_STATUS,
        "comparison_basis": "matched_window",
        "credential_access_status": "not_attempted",
        "downstream_comparison_authorized": True,
        "downstream_use": "offline_etf_sma_preferred_baseline_comparison",
        "guard_source_milestone": "M423",
        "guard_status": "preferred_adjusted_baseline_guard_ready",
        "known_basis_delta_slices": ["recovery_2023"],
        "manifest_path": "runs\\paper_lab\\m422_spy_preferred_adjusted_baseline_manifest.jsonl",
        "matched_total_interval_count": 1055,
        "milestone": "M424",
        "network_broker_access_status": "not_attempted",
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "operator_trade_recommendation": "none",
        "paper_lab_only": True,
        "profit_claim": "none",
        "record_type": "etf_sma_guarded_preferred_baseline_comparison_authorization",
        "research_only": True,
        "run_id": "unit_m424",
        "schema_version": "1",
        "signal_evaluation_only": True,
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload
