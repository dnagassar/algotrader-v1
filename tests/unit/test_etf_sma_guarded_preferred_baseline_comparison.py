from __future__ import annotations

import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.research.etf_sma_guarded_preferred_baseline_comparison import (
    EtfSmaGuardedPreferredBaselineComparisonConfig,
    build_etf_sma_guarded_preferred_baseline_comparison_authorization,
    render_etf_sma_guarded_preferred_baseline_comparison_json,
    write_etf_sma_guarded_preferred_baseline_comparison_jsonl,
)


_COMMAND = "etf-sma-preferred-baseline-comparison-guard"
_GUARD_READY_STATUS = "preferred_adjusted_baseline_guard_ready"
_GUARD_BLOCKED_STATUS = "blocked_preferred_adjusted_baseline_guard"
_AUTHORIZED_STATUS = "preferred_baseline_guard_passed"
_BLOCKED_STATUS = "blocked_preferred_baseline_guard"
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


def test_guarded_preferred_baseline_comparison_success_path_from_m422_manifest(
    tmp_path: Path,
) -> None:
    manifest_path = _write_preferred_baseline_manifest(tmp_path)

    payload = build_etf_sma_guarded_preferred_baseline_comparison_authorization(
        _config(manifest_path)
    )

    assert payload["run_id"] == "unit_m424"
    assert payload["symbol"] == "SPY"
    assert payload["milestone"] == "M424"
    assert payload["guard_status"] == _GUARD_READY_STATUS
    assert payload["comparison_authorization_status"] == _AUTHORIZED_STATUS
    assert payload["downstream_comparison_authorized"] is True
    assert payload["active_preferred_baseline"] == _PREFERRED_BASELINE
    assert payload["active_preferred_basis"] == _PREFERRED_BASIS
    assert payload["comparison_basis"] == "matched_window"
    assert payload["matched_total_interval_count"] == 1055
    assert payload["known_basis_delta_slices"] == ["recovery_2023"]
    assert payload["baseline_source_milestone"] == "M422"
    assert payload["guard_source_milestone"] == "M423"
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["blockers"] == []
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m424.jsonl"
    write_etf_sma_guarded_preferred_baseline_comparison_jsonl(payload, run_log)
    assert json.loads(run_log.read_text(encoding="utf-8")) == json.loads(
        render_etf_sma_guarded_preferred_baseline_comparison_json(payload)
    )


def test_blocks_without_authorization_fields_when_m423_guard_fails(
    tmp_path: Path,
) -> None:
    manifest_path = _write_preferred_baseline_manifest(
        tmp_path,
        mutator=lambda payload: payload.update(
            {"preferred_basis": "raw_close_price_return"}
        ),
    )

    payload = build_etf_sma_guarded_preferred_baseline_comparison_authorization(
        _config(manifest_path)
    )

    assert payload["guard_status"] == _GUARD_BLOCKED_STATUS
    assert payload["comparison_authorization_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert "preferred_baseline_manifest_unexpected_preferred_basis" in (
        payload["blockers"]
    )
    assert "preferred_baseline_guard_not_ready" in payload["blockers"]
    assert "active_preferred_baseline" not in payload
    assert "active_preferred_basis" not in payload
    assert "comparison_basis" not in payload
    assert "matched_total_interval_count" not in payload
    assert "known_basis_delta_slices" not in payload
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def test_blocks_with_deterministic_m423_blocker_when_manifest_is_missing(
    tmp_path: Path,
) -> None:
    payload = build_etf_sma_guarded_preferred_baseline_comparison_authorization(
        _config(tmp_path / "missing.jsonl")
    )

    assert payload["guard_status"] == _GUARD_BLOCKED_STATUS
    assert payload["comparison_authorization_status"] == _BLOCKED_STATUS
    assert payload["downstream_comparison_authorized"] is False
    assert payload["blockers"] == [
        "preferred_baseline_manifest_not_found",
        "preferred_baseline_guard_not_ready",
        "preferred_baseline_guard_not_active",
    ]
    assert payload["blocked_reason"] == "preferred_baseline_manifest_not_found"


def test_cli_writes_authorization_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    manifest_path = _write_preferred_baseline_manifest(tmp_path)
    run_log = tmp_path / "m424_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M424 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m424_cli",
            "--run-log",
            str(run_log),
            "--manifest-path",
            str(manifest_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["comparison_authorization_status"] == _AUTHORIZED_STATUS
    assert payload["downstream_comparison_authorized"] is True


def _config(
    manifest_path: Path,
) -> EtfSmaGuardedPreferredBaselineComparisonConfig:
    return EtfSmaGuardedPreferredBaselineComparisonConfig(
        run_id="unit_m424",
        symbol="SPY",
        manifest_path=manifest_path,
    )


def _write_preferred_baseline_manifest(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _preferred_baseline_manifest_payload()
    if mutator is not None:
        mutator(payload)

    manifest_path = tmp_path / "m422.jsonl"
    manifest_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _preferred_baseline_manifest_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "baseline_source_milestone": "M421",
        "comparison_basis": "matched_window",
        "known_basis_delta_slices": ["recovery_2023"],
        "manifest_status": "preferred_baseline_active",
        "matched_total_interval_count": 1055,
        "milestone": "M422",
        "preferred_baseline": _PREFERRED_BASELINE,
        "preferred_baseline_active": True,
        "preferred_basis": _PREFERRED_BASIS,
        "profit_claim": "none",
        "record_type": "etf_sma_preferred_baseline_manifest",
        "run_id": "unit_m422_manifest",
        "schema_version": "1",
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload
