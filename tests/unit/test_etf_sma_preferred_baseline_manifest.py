from __future__ import annotations

import json
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.research.etf_sma_preferred_baseline_manifest import (
    EtfSmaPreferredBaselineManifestConfig,
    build_etf_sma_preferred_baseline_manifest,
    load_and_validate_preferred_adjusted_baseline_manifest,
    render_etf_sma_preferred_baseline_manifest_json,
    write_etf_sma_preferred_baseline_manifest_jsonl,
)


_COMMAND = "etf-sma-preferred-baseline-manifest"
_ACTIVE_STATUS = "preferred_baseline_active"
_BLOCKED_STATUS = "blocked_preferred_baseline_manifest"
_GUARD_READY_STATUS = "preferred_adjusted_baseline_guard_ready"
_GUARD_BLOCKED_STATUS = "blocked_preferred_adjusted_baseline_guard"
_SOURCE_PROMOTION_STATUS = "ready_to_promote_adjusted_matched_window_basis"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_LEGACY_RAW_BASIS = "raw_close_price_return"
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SOURCE_FALSE_FIELDS = _SAFETY_FALSE_FIELDS + (
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


def test_preferred_baseline_manifest_success_path_from_m421_packet(
    tmp_path: Path,
) -> None:
    source_path = _write_source_packet(tmp_path)

    payload = build_etf_sma_preferred_baseline_manifest(_config(source_path))

    assert payload["manifest_status"] == _ACTIVE_STATUS
    assert payload["symbol"] == "SPY"
    assert payload["preferred_baseline"] == _PREFERRED_BASELINE
    assert payload["preferred_basis"] == _PREFERRED_BASIS
    assert payload["comparison_basis"] == "matched_window"
    assert payload["baseline_source_milestone"] == "M421"
    assert payload["source_promotion_packet"] == str(source_path)
    assert payload["source_promotion_status"] == _SOURCE_PROMOTION_STATUS
    assert payload["legacy_raw_basis"] == _LEGACY_RAW_BASIS
    assert payload["legacy_raw_baseline_status"] == (
        "superseded_for_offline_comparison"
    )
    assert payload["same_slice_counts"] is True
    assert payload["same_slice_dates"] is True
    assert payload["m417a_slice_counts_unchanged"] is True
    assert payload["matched_total_interval_count"] == 1055
    assert payload["return_conclusions_unchanged"] is True
    assert payload["known_basis_delta_count"] == 1
    assert payload["known_basis_delta_slices"] == ["recovery_2023"]
    assert payload["basis_delta_review_required"] is True
    assert payload["downstream_use"] == "offline_etf_sma_comparison_baseline"
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    run_log = tmp_path / "m422.jsonl"
    write_etf_sma_preferred_baseline_manifest_jsonl(payload, run_log)
    assert json.loads(run_log.read_text(encoding="utf-8")) == json.loads(
        render_etf_sma_preferred_baseline_manifest_json(payload)
    )


@pytest.mark.parametrize(
    ("writer", "expected_blocker"),
    [
        (lambda path: None, "source_promotion_packet_not_found"),
        (
            lambda path: path.write_text("{", encoding="utf-8"),
            "source_promotion_packet_invalid_json",
        ),
        (
            lambda path: path.write_text("[]\n", encoding="utf-8"),
            "source_promotion_packet_record_not_object",
        ),
        (
            lambda path: path.write_text(
                "\n".join(
                    [
                        json.dumps(_source_payload(), sort_keys=True),
                        json.dumps(_source_payload(), sort_keys=True),
                    ]
                )
                + "\n",
                encoding="utf-8",
            ),
            "ambiguous_source_promotion_packet_record_count",
        ),
    ],
)
def test_blocks_when_m421_packet_is_missing_invalid_or_ambiguous(
    tmp_path: Path,
    writer,
    expected_blocker: str,
) -> None:
    source_path = tmp_path / "m421.jsonl"
    writer(source_path)

    payload = build_etf_sma_preferred_baseline_manifest(_config(source_path))

    assert payload["manifest_status"] == _BLOCKED_STATUS
    assert payload["preferred_baseline_active"] is False
    assert expected_blocker in payload["blockers"]
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        ("promotion_status", "blocked", "source_promotion_status_not_ready"),
        (
            "baseline_recommendation",
            "raw_close_matched_window",
            "source_baseline_recommendation_not_adjusted_matched_window",
        ),
        ("same_slice_counts", False, "source_same_slice_counts_not_true"),
        ("same_slice_dates", False, "source_same_slice_dates_not_true"),
        (
            "m417a_slice_counts_unchanged",
            False,
            "source_m417a_slice_counts_not_unchanged",
        ),
        (
            "drawdown_conclusion_changes",
            [],
            "source_drawdown_conclusion_changes_mismatch",
        ),
        (
            "return_conclusions_unchanged",
            False,
            "source_return_conclusions_not_unchanged",
        ),
        ("submitted", True, "source_safety_flag_dirty_submitted"),
        (
            "network_access_attempted",
            True,
            "source_safety_flag_dirty_network_access_attempted",
        ),
        (
            "credential_access_attempted",
            True,
            "source_safety_flag_dirty_credential_access_attempted",
        ),
        ("live_authorized", True, "source_safety_flag_dirty_live_authorized"),
        ("trade_recommendation", "buy", "source_trade_recommendation_not_none"),
        ("profit_claim", "positive", "source_profit_claim_not_none"),
    ],
)
def test_blocks_when_m421_packet_contract_is_not_ready_or_safe(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    source_path = _write_source_packet(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    payload = build_etf_sma_preferred_baseline_manifest(_config(source_path))

    assert payload["manifest_status"] == _BLOCKED_STATUS
    assert payload["preferred_baseline_active"] is False
    assert expected_blocker in payload["blockers"]
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"


def test_blocks_if_raw_and_adjusted_basis_labels_are_reversed(
    tmp_path: Path,
) -> None:
    source_path = _write_source_packet(
        tmp_path,
        mutator=lambda payload: payload.update(
            {
                "raw_basis": _PREFERRED_BASIS,
                "adjusted_basis": _LEGACY_RAW_BASIS,
            }
        ),
    )

    payload = build_etf_sma_preferred_baseline_manifest(_config(source_path))

    assert payload["manifest_status"] == _BLOCKED_STATUS
    assert "source_raw_basis_not_raw_close" in payload["blockers"]
    assert "source_adjusted_basis_not_adjusted_close" in payload["blockers"]


def test_cli_writes_manifest_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    source_path = _write_source_packet(tmp_path)
    run_log = tmp_path / "m422_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M422 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m422_cli",
            "--run-log",
            str(run_log),
            "--source-promotion-packet",
            str(source_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["manifest_status"] == _ACTIVE_STATUS


def test_preferred_adjusted_baseline_guard_success_path_from_m422_record(
    tmp_path: Path,
) -> None:
    manifest_path = _write_preferred_baseline_manifest(tmp_path)

    result = load_and_validate_preferred_adjusted_baseline_manifest(manifest_path)

    assert result.guard_status == _GUARD_READY_STATUS
    assert result.preferred_baseline_active is True
    assert result.preferred_baseline == _PREFERRED_BASELINE
    assert result.preferred_basis == _PREFERRED_BASIS
    assert result.comparison_basis == "matched_window"
    assert result.matched_total_interval_count == 1055
    assert result.known_basis_delta_slices == ("recovery_2023",)
    assert result.blockers == ()
    assert result.submitted is False
    assert result.mutated is False
    assert result.broker_action_performed is False
    assert result.network_access_attempted is False
    assert result.credential_access_attempted is False
    assert result.live_authorized is False
    assert result.to_dict()["guard_status"] == _GUARD_READY_STATUS


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    [
        (
            "preferred_baseline",
            "raw_close_matched_window",
            "preferred_baseline_manifest_unexpected_preferred_baseline",
        ),
        (
            "preferred_basis",
            "raw_close_price_return",
            "preferred_baseline_manifest_unexpected_preferred_basis",
        ),
        (
            "comparison_basis",
            "full_history",
            "preferred_baseline_manifest_unexpected_comparison_basis",
        ),
        (
            "matched_total_interval_count",
            1054,
            "preferred_baseline_manifest_unexpected_matched_total_interval_count",
        ),
    ],
)
def test_preferred_adjusted_baseline_guard_fails_closed_on_core_drift(
    tmp_path: Path,
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    manifest_path = _write_preferred_baseline_manifest(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: value}),
    )

    result = load_and_validate_preferred_adjusted_baseline_manifest(manifest_path)

    assert result.guard_status == _GUARD_BLOCKED_STATUS
    assert result.preferred_baseline_active is False
    assert expected_blocker in result.blockers
    assert result.submitted is False
    assert result.mutated is False
    assert result.broker_action_performed is False
    assert result.network_access_attempted is False
    assert result.credential_access_attempted is False
    assert result.live_authorized is False


@pytest.mark.parametrize(
    ("mutator", "expected_blocker"),
    [
        (
            lambda payload: payload.pop("known_basis_delta_slices"),
            "preferred_baseline_manifest_missing_known_basis_delta_slices",
        ),
        (
            lambda payload: payload.update({"known_basis_delta_slices": []}),
            "preferred_baseline_manifest_unexpected_known_basis_delta_slices",
        ),
    ],
)
def test_preferred_adjusted_baseline_guard_fails_closed_on_delta_slice_drift(
    tmp_path: Path,
    mutator,
    expected_blocker: str,
) -> None:
    manifest_path = _write_preferred_baseline_manifest(
        tmp_path,
        mutator=mutator,
    )

    result = load_and_validate_preferred_adjusted_baseline_manifest(manifest_path)

    assert result.guard_status == _GUARD_BLOCKED_STATUS
    assert result.preferred_baseline_active is False
    assert expected_blocker in result.blockers


@pytest.mark.parametrize("field_name", _SAFETY_FALSE_FIELDS)
def test_preferred_adjusted_baseline_guard_fails_closed_when_safety_flag_is_true(
    tmp_path: Path,
    field_name: str,
) -> None:
    manifest_path = _write_preferred_baseline_manifest(
        tmp_path,
        mutator=lambda payload: payload.update({field_name: True}),
    )

    result = load_and_validate_preferred_adjusted_baseline_manifest(manifest_path)

    assert result.guard_status == _GUARD_BLOCKED_STATUS
    assert result.preferred_baseline_active is False
    assert (
        f"preferred_baseline_manifest_safety_flag_dirty_{field_name}"
        in result.blockers
    )
    assert result.submitted is False
    assert result.mutated is False
    assert result.broker_action_performed is False
    assert result.network_access_attempted is False
    assert result.credential_access_attempted is False
    assert result.live_authorized is False


def test_preferred_adjusted_baseline_guard_fails_closed_when_manifest_missing(
    tmp_path: Path,
) -> None:
    result = load_and_validate_preferred_adjusted_baseline_manifest(
        tmp_path / "missing.jsonl"
    )

    assert result.guard_status == _GUARD_BLOCKED_STATUS
    assert result.preferred_baseline_active is False
    assert result.blockers == ("preferred_baseline_manifest_not_found",)
    assert result.preferred_baseline == ""


def _config(source_path: Path) -> EtfSmaPreferredBaselineManifestConfig:
    return EtfSmaPreferredBaselineManifestConfig(
        run_id="unit_m422",
        symbol="SPY",
        source_promotion_packet=source_path,
    )


def _write_source_packet(
    tmp_path: Path,
    *,
    mutator=None,  # noqa: ANN001
) -> Path:
    payload = _source_payload()
    if mutator is not None:
        mutator(payload)

    source_path = tmp_path / "m421.jsonl"
    source_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return source_path


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
        "basis_delta_review_required": True,
        "blockers": [],
        "broker_mutation_status": "none",
        "command": _COMMAND,
        "comparison_basis": "matched_window",
        "credential_access_status": "not_attempted",
        "downstream_use": "offline_etf_sma_comparison_baseline",
        "known_basis_delta_count": 1,
        "known_basis_delta_slices": ["recovery_2023"],
        "legacy_raw_baseline_status": "superseded_for_offline_comparison",
        "legacy_raw_basis": _LEGACY_RAW_BASIS,
        "m417a_slice_counts_unchanged": True,
        "manifest_status": _ACTIVE_STATUS,
        "matched_total_interval_count": 1055,
        "milestone": "M422",
        "network_broker_access_status": "not_attempted",
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "operator_trade_recommendation": "none",
        "paper_lab_only": True,
        "preferred_baseline": _PREFERRED_BASELINE,
        "preferred_baseline_active": True,
        "preferred_basis": _PREFERRED_BASIS,
        "profit_claim": "none",
        "record_type": "etf_sma_preferred_baseline_manifest",
        "research_only": True,
        "return_conclusion_changes": [],
        "return_conclusions_unchanged": True,
        "run_id": "unit_m422_manifest",
        "same_slice_counts": True,
        "same_slice_dates": True,
        "schema_version": "1",
        "signal_evaluation_only": True,
        "source_promotion_packet": "runs\\paper_lab\\m421_spy_adjusted_basis.jsonl",
        "source_promotion_packet_valid": True,
        "source_promotion_status": _SOURCE_PROMOTION_STATUS,
        "symbol": "SPY",
        "trade_recommendation": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    return payload


def _source_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": "etf_sma_adjusted_basis_promotion_packet",
        "schema_version": "1",
        "command": "etf-sma-adjusted-basis-promotion-packet",
        "milestone": "M421",
        "run_id": "unit_m421",
        "symbol": "SPY",
        "promotion_status": _SOURCE_PROMOTION_STATUS,
        "comparison_basis": "matched_window",
        "raw_basis": _LEGACY_RAW_BASIS,
        "adjusted_basis": _PREFERRED_BASIS,
        "same_slice_counts": True,
        "same_slice_dates": True,
        "m417a_slice_counts_unchanged": True,
        "matched_total_interval_count": 1055,
        "return_conclusions_unchanged": True,
        "return_conclusion_changes": [],
        "drawdown_conclusion_changes": ["recovery_2023"],
        "basis_delta_review_required": True,
        "baseline_recommendation": _PREFERRED_BASELINE,
        "preferred_offline_baseline_ready": True,
        "trade_recommendation": "none",
        "operator_trade_recommendation": "none",
        "profit_claim": "none",
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "paper_lab_only": True,
        "research_only": True,
        "signal_evaluation_only": True,
        "broker_mutation_status": "none",
        "network_broker_access_status": "not_attempted",
        "credential_access_status": "not_attempted",
    }
    for field_name in _SOURCE_FALSE_FIELDS:
        payload[field_name] = False
    return payload
