from __future__ import annotations

import json
from pathlib import Path

import pytest

from algotrader.execution.crypto_supervised_readiness_trial import (
    SCHEMA_VERSION,
    run_crypto_supervised_readiness_trial,
    validate_crypto_supervised_readiness_trial,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_crypto_supervised_readiness_trial.ps1"


def test_eight_cycle_trial_proves_complete_r1_path_and_scenarios(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "runs" / "crypto_supervised_readiness_trial" / "latest"

    packet = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )

    assert packet["schema_version"] == SCHEMA_VERSION
    assert packet["trial_classification"] == "accepted"
    assert packet["previous_readiness_rung"] == "R0_components_exist"
    assert packet["current_readiness_rung_code"] == "R1"
    assert packet["cycle_count"] == 8
    assert packet["symbols_evaluated"] == ["BTCUSD", "ETHUSD", "SOLUSD"]
    assert packet["deterministic_rerun"]["equivalent"] is True
    assert packet["deterministic_rerun"]["final_state_hash_equal"] is True
    assert packet["sequential_replay"]["all_cycles_valid"] is True
    assert len(packet["sequential_replay"]["receipts"]) == 8
    assert len(packet["scenario_receipts"]) == 8
    assert all(item["acceptance_passed"] is True for item in packet["scenario_receipts"])
    assert packet["broker_observed_result"]["classification"] == (
        "blocked_credentials_unavailable"
    )
    assert packet["safety"]["paper_submit_performed"] is False
    assert packet["safety"]["broker_mutation_performed"] is False
    assert packet["safety"]["live_authorized"] is False
    assert len(packet["receipt_chain"]["final_receipt_hash"]) == 64
    assert validate_crypto_supervised_readiness_trial(output_root)[
        "validation_status"
    ] == "passed"


def test_cycle_receipts_are_causal_chained_and_explain_router_progress(
    tmp_path: Path,
) -> None:
    packet = run_crypto_supervised_readiness_trial(
        output_root=tmp_path / "runs" / "trial",
        cycle_count=8,
        write_artifacts=False,
    )

    receipts = packet["sequential_replay"]["receipts"]
    assert receipts[0]["previous_receipt_hash"] == "0" * 64
    for index, receipt in enumerate(receipts):
        assert receipt["forming_bar_used"] is False
        assert receipt["future_data_used"] is False
        assert receipt["frontier_advanced_exactly_one_hour"] is True
        assert receipt["retry_count"] == 0
        assert receipt["silent_retry_performed"] is False
        assert receipt["submit_performed"] is False
        assert receipt["broker_mutation_performed"] is False
        assert receipt["execution_plan"]["immutable_pre_broker"] is True
        if index:
            assert receipt["previous_receipt_hash"] == receipts[index - 1][
                "receipt_hash"
            ]
    assert receipts[0]["router_decision"][
        "continues_when_one_candidate_has_no_trade"
    ] is True
    assert receipts[0]["execution_intent"]["note"] == (
        "ExecutionIntent is not a broker order."
    )


def test_rerun_at_same_root_restarts_from_canonical_state(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "runs" / "trial"
    first = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    second = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )

    assert first["receipt_chain"]["final_receipt_hash"] == second[
        "receipt_chain"
    ]["final_receipt_hash"]
    assert first["sequential_replay"]["final_state_sha256"] == second[
        "sequential_replay"
    ]["final_state_sha256"]


def test_validator_detects_artifact_tampering(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "trial"
    run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    report_path = output_root / "operating_report.md"
    report_path.write_text("tampered\n", encoding="utf-8")

    validation = validate_crypto_supervised_readiness_trial(output_root)

    assert validation["validation_status"] == "failed"
    assert "artifact_hash_mismatch:operating_report" in validation["errors"]


@pytest.mark.parametrize("cycle_count", (0, 7, 25))
def test_cycle_count_outside_bounded_range_is_rejected(
    tmp_path: Path,
    cycle_count: int,
) -> None:
    with pytest.raises(ValueError, match="cycle_count must be between 8 and 24"):
        run_crypto_supervised_readiness_trial(
            output_root=tmp_path / "runs" / "trial",
            cycle_count=cycle_count,
            write_artifacts=False,
        )


def test_read_permission_requires_explicit_broker_observation_request(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="allow_alpaca_paper_read requires broker_observed_readiness",
    ):
        run_crypto_supervised_readiness_trial(
            output_root=tmp_path / "runs" / "trial",
            cycle_count=8,
            allow_alpaca_paper_read=True,
            write_artifacts=False,
        )


def test_script_is_default_offline_no_submit_and_has_no_mutation_switch() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    for fragment in (
        '[int]$CycleCount = 24',
        "[switch]$BrokerObservedReadiness",
        "[switch]$AllowAlpacaPaperRead",
        "v5_32_preflight_credentials_present=",
        "Credential values are never printed",
        "crypto_supervised_readiness_trial",
        "--broker-observed-readiness",
        "--allow-alpaca-paper-read",
    ):
        assert fragment in script
    assert "AllowAlpacaPaperMutation" not in script
    assert "--allow-alpaca-paper-mutation" not in script
    assert "submit_order" not in script
    assert "cancel_order" not in script
    assert "--live" not in script


def test_generated_packet_records_no_more_than_three_r4_blockers(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "runs" / "trial"
    run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    packet = json.loads(
        (output_root / "readiness_packet.json").read_text(encoding="utf-8")
    )

    assert 1 <= len(packet["exact_blockers_to_R4"]) <= 3
    assert packet["selected_next_milestone"].startswith("V5.33")
