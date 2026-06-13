from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_paper_lab import (
    EtfSmaDailyPaperLabConfig,
    run_etf_sma_daily_paper_lab,
    validate_etf_sma_daily_paper_lab_packet,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"


@pytest.fixture(autouse=True)
def enforce_preflight_offline_only() -> None:
    """Ensure that no credentials or paper profiles are present in the environment."""
    assert not os.environ.get("APP_PROFILE") == "paper"
    for var in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        assert var not in os.environ


def test_etf_sma_daily_paper_lab_success_bullish(tmp_path: Path) -> None:
    """Test successful run with 200 bullish bars."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        as_of_date="2025-07-20",
        symbol="SPY",
    )

    payload = run_etf_sma_daily_paper_lab(config)

    assert payload["schema_version"] == "1"
    assert payload["assistant_version"] == "assistant_v1"
    assert payload["assistant_packet_version"] == "assistant_v1.1"
    assert payload["packet_type"] == "daily_trading_research_command_center"
    assert payload["run_id"] == "daily_paper_lab_2025-07-20"
    assert payload["symbol"] == "SPY"
    assert payload["active_strategy_name"] == "SPY daily long-only ETF SMA 50/200 trend filter"
    assert payload["posture"] == "bullish_risk_on"
    assert payload["sma_posture_status"] == "risk_on: SMA50 is above SMA200"
    assert payload["preview_decision"] == "offline_preview_bullish_risk_on"
    assert payload["decision"] == "offline_preview_bullish_risk_on"
    assert payload["blocker_status"] == "broker_state_not_observed"
    assert payload["broker_state_mode"] == "broker_state_not_observed"
    assert payload["broker_state_observed"] is False
    assert payload["paper_submit_authorized"] is False
    assert payload["paper_submit_authorization_status"] == "not_authorized"
    assert payload["next_operator_action"] == "review_assistant_brief_no_broker_action"
    assert payload["validation_status"] == "pass"
    assert payload["missing_required_fields"] == []
    assert payload["artifact_presence_status"]["status"] == "pass"
    assert payload["history_ledger_path"].endswith("history_ledger.jsonl")
    delta = payload["history_delta"]
    assert delta["previous_packet_found"] is False
    assert delta["previous_as_of_date"] is None
    assert delta["current_as_of_date"] == "2025-07-20"
    assert delta["posture_changed"] is False
    assert delta["current_posture"] == "bullish_risk_on"
    assert delta["preview_decision_changed"] is False
    assert delta["current_preview_decision"] == "offline_preview_bullish_risk_on"
    assert delta["blocker_status_changed"] is False
    assert delta["current_blocker_status"] == "broker_state_not_observed"
    assert delta["validation_status_changed"] is False
    assert delta["current_validation_status"] == "pass"
    assert delta["broker_state_mode_changed"] is False
    assert delta["current_broker_state_mode"] == "broker_state_not_observed"
    assert delta["research_board_changed"] is False
    assert delta["research_board_delta_status"] == "no_previous_packet"
    assert delta["next_operator_action_changed"] is False
    assert (
        delta["delta_summary_text"]
        == "No prior packet was found in this output root history; this is the "
        "first observed packet in the selected history."
    )
    assert payload["artifact_presence_status"]["missing_artifacts"] == []
    assert payload["artifact_presence_status"]["empty_artifacts"] == []
    assert payload["artifact_presence_status"]["artifacts"]["operating_brief"]["exists"] is True
    assert (
        payload["artifact_presence_status"]["artifacts"]["operating_record"]["exists"]
        is True
    )
    assert payload["artifact_presence_status"]["artifacts"]["manifest"]["exists"] is True
    assert payload["executive_dashboard"]["validation_status"] == "pass"
    assert payload["executive_dashboard"]["missing_required_fields"] == []

    # Labels verification
    for label in (
        "paper_lab_only",
        "signal_evaluation_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "offline_only",
        "broker_state_not_observed",
        "paper_submit_not_authorized",
    ):
        assert label in payload["labels"]
        assert label in payload["safety_labels"]

    # Verify artifacts were created
    assert (output_root / "operating_brief.md").exists()
    assert (output_root / "operating_record.jsonl").exists()
    assert (output_root / "manifest.jsonl").exists()
    assert (output_root / "history_ledger.jsonl").exists()

    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    assert "## Executive summary" in brief
    assert "* **Recommendation**:" in brief
    assert "* **Evidence**:" in brief
    assert "* **Risks / blockers**:" in brief
    assert "## Trading desk brief" in brief
    assert "## Research lab section" in brief
    assert "## Executive dashboard" in brief
    assert "paper_submit_authorized=false" in brief
    assert "broker_state_not_observed" in brief
    assert "candidate_strategy_board_seed" in brief
    assert "placeholder_not_implemented" in brief
    assert "**Assistant packet version**: assistant_v1.1" in brief
    assert "**Validation status**: pass" in brief
    assert "**Missing required fields**: []" in brief
    assert "**Artifact presence status**: pass" in brief
    assert "**Previous packet found**: false" in brief
    assert "history_ledger.jsonl" in brief
    assert delta["delta_summary_text"] in brief

    record_lines = (output_root / "operating_record.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(record_lines) == 1
    record = json.loads(record_lines[0])
    assert record["assistant_version"] == "assistant_v1"
    assert record["assistant_packet_version"] == "assistant_v1.1"
    assert record["input_data_path"].endswith("spy_daily_bars_200_bullish.csv")
    assert record["as_of_date"] == "2025-07-20"
    assert record["active_strategy_name"] == payload["active_strategy_name"]
    assert record["preview_decision"] == "offline_preview_bullish_risk_on"
    assert record["broker_state_mode"] == "broker_state_not_observed"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_authorization_status"] == "not_authorized"
    assert record["next_operator_action"] == "review_assistant_brief_no_broker_action"
    assert "paper_lab_only" in record["safety_labels"]
    assert record["validation_status"] == "pass"
    assert record["missing_required_fields"] == []
    assert record["artifact_presence_status"]["status"] == "pass"
    assert record["history_delta"] == delta
    assert record["history_ledger_path"].endswith("history_ledger.jsonl")
    candidate = record["research_lab"]["candidate_strategy_board"][0]
    assert candidate["candidate_name"] == "candidate_strategy_board_seed"
    assert candidate["status"] == "placeholder_not_implemented"
    assert "hypothesis" in candidate
    assert "required_evidence" in candidate
    assert "next_research_action" in candidate
    assert "promotion_blockers" in candidate

    # Verify manifest content
    manifest_lines = (output_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    manifest = json.loads(manifest_lines[0])
    assert manifest["schema_version"] == "1"
    assert manifest["assistant_version"] == "assistant_v1"
    assert manifest["assistant_packet_version"] == "assistant_v1.1"
    assert manifest["manifest_type"] == "daily_trading_research_command_center_index"
    assert manifest["run_id"] == "daily_paper_lab_2025-07-20"
    assert manifest["paper_submit_authorized"] is False
    assert manifest["broker_state_mode"] == "broker_state_not_observed"
    assert manifest["next_operator_action"] == "review_assistant_brief_no_broker_action"
    assert manifest["validation_status"] == "pass"
    assert manifest["missing_required_fields"] == []
    assert manifest["artifact_presence_status"]["status"] == "pass"
    assert manifest["history_delta"] == delta
    assert manifest["previous_packet_found"] is False
    assert manifest["delta_summary_text"] == delta["delta_summary_text"]
    assert "assistant_brief" in manifest["indexed_artifacts"]
    assert "operating_record" in manifest["indexed_artifacts"]
    assert "history_ledger" in manifest["indexed_artifacts"]
    assert "manifest" not in manifest["indexed_artifacts"]

    history_lines = (output_root / "history_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(history_lines) == 1
    history_entry = json.loads(history_lines[0])
    assert history_entry["history_entry_version"] == "assistant_v1.2_history_entry"
    assert history_entry["sequence_number"] == 1
    assert history_entry["as_of_date"] == "2025-07-20"
    assert history_entry["posture"] == "bullish_risk_on"
    assert history_entry["preview_decision"] == "offline_preview_bullish_risk_on"
    assert history_entry["blocker_status"] == "broker_state_not_observed"
    assert history_entry["validation_status"] == "pass"
    assert history_entry["broker_state_mode"] == "broker_state_not_observed"
    assert len(history_entry["packet_summary_sha256"]) == 64

    validation = validate_etf_sma_daily_paper_lab_packet(output_root)
    assert validation["validation_status"] == "pass"
    assert validation["missing_required_fields"] == []
    assert validation["artifact_presence_status"]["status"] == "pass"


def test_etf_sma_daily_paper_lab_second_run_delta_compares_prior_packet(
    tmp_path: Path,
) -> None:
    """Second run against one output root reports the prior packet delta."""
    output_root = tmp_path / "paper_lab_out"

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )
    second_payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bearish.csv",
            as_of_date="2025-07-21",
            symbol="SPY",
        )
    )

    delta = second_payload["history_delta"]
    assert delta["previous_packet_found"] is True
    assert delta["previous_as_of_date"] == "2025-07-20"
    assert delta["current_as_of_date"] == "2025-07-21"
    assert delta["posture_changed"] is True
    assert delta["previous_posture"] == "bullish_risk_on"
    assert delta["current_posture"] == "defensive_risk_off"
    assert delta["preview_decision_changed"] is True
    assert delta["previous_preview_decision"] == "offline_preview_bullish_risk_on"
    assert delta["current_preview_decision"] == "offline_preview_defensive_risk_off"
    assert delta["blocker_status_changed"] is False
    assert delta["validation_status_changed"] is False
    assert delta["broker_state_mode_changed"] is False
    assert delta["research_board_changed"] is False
    assert delta["research_board_delta_status"] == "unchanged"
    assert delta["next_operator_action_changed"] is False
    assert delta["delta_summary_text"] == (
        "Prior packet found; as-of date moved from 2025-07-20 to "
        "2025-07-21; posture changed from bullish_risk_on to "
        "defensive_risk_off; preview decision changed from "
        "offline_preview_bullish_risk_on to "
        "offline_preview_defensive_risk_off."
    )

    history_lines = (output_root / "history_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(history_lines) == 2
    first_history_entry = json.loads(history_lines[0])
    second_history_entry = json.loads(history_lines[1])
    assert first_history_entry["sequence_number"] == 1
    assert second_history_entry["sequence_number"] == 2
    assert second_history_entry["posture"] == "defensive_risk_off"
    assert second_history_entry["delta_summary_text"] == delta["delta_summary_text"]

    record = json.loads(
        (output_root / "operating_record.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()[0]
    )
    manifest = json.loads(
        (output_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    assert record["history_delta"] == delta
    assert manifest["history_delta"] == delta
    assert manifest["previous_packet_found"] is True
    assert delta["delta_summary_text"] in brief


def test_etf_sma_daily_paper_lab_delta_reports_changed_operational_fields(
    tmp_path: Path,
) -> None:
    """Seeded history proves blocker, validation, broker, and action changes."""
    output_root = tmp_path / "paper_lab_out"
    output_root.mkdir(parents=True)
    seeded_history_entry = {
        "history_entry_version": "assistant_v1.2_history_entry",
        "sequence_number": 1,
        "run_id": "daily_paper_lab_2025-07-19",
        "as_of_date": "2025-07-19",
        "posture": "defensive_risk_off",
        "preview_decision": "offline_preview_defensive_risk_off",
        "blocker_status": "legacy_blocker",
        "validation_status": "fail",
        "broker_state_mode": "offline_preview_only",
        "research_board_fingerprint": "legacy_research_board",
        "next_operator_action": "legacy_operator_action",
    }
    (output_root / "history_ledger.jsonl").write_text(
        json.dumps(seeded_history_entry, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    payload = run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=FIXTURES_DIR / "spy_daily_bars_200_bullish.csv",
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    delta = payload["history_delta"]
    assert delta["previous_packet_found"] is True
    assert delta["previous_as_of_date"] == "2025-07-19"
    assert delta["current_as_of_date"] == "2025-07-20"
    assert delta["posture_changed"] is True
    assert delta["preview_decision_changed"] is True
    assert delta["blocker_status_changed"] is True
    assert delta["previous_blocker_status"] == "legacy_blocker"
    assert delta["current_blocker_status"] == "broker_state_not_observed"
    assert delta["validation_status_changed"] is True
    assert delta["previous_validation_status"] == "fail"
    assert delta["current_validation_status"] == "pass"
    assert delta["broker_state_mode_changed"] is True
    assert delta["previous_broker_state_mode"] == "offline_preview_only"
    assert delta["current_broker_state_mode"] == "broker_state_not_observed"
    assert delta["research_board_changed"] is True
    assert delta["research_board_delta_status"] == "changed"
    assert delta["next_operator_action_changed"] is True
    assert delta["previous_next_operator_action"] == "legacy_operator_action"
    assert (
        delta["current_next_operator_action"]
        == "review_assistant_brief_no_broker_action"
    )
    assert delta["delta_summary_text"] == (
        "Prior packet found; as-of date moved from 2025-07-19 to "
        "2025-07-20; posture changed from defensive_risk_off to "
        "bullish_risk_on; preview decision changed from "
        "offline_preview_defensive_risk_off to "
        "offline_preview_bullish_risk_on; blocker status changed from "
        "legacy_blocker to broker_state_not_observed; validation status "
        "changed from fail to pass; broker-state mode changed from "
        "offline_preview_only to broker_state_not_observed; research board "
        "changed; next operator action changed from legacy_operator_action "
        "to review_assistant_brief_no_broker_action."
    )

    history_lines = (output_root / "history_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(history_lines) == 2
    appended_entry = json.loads(history_lines[1])
    assert appended_entry["sequence_number"] == 2
    assert appended_entry["validation_status"] == "pass"
    assert appended_entry["blocker_status"] == "broker_state_not_observed"


def test_etf_sma_daily_paper_lab_validator_reports_missing_fields_and_artifacts(
    tmp_path: Path,
) -> None:
    """Validator failure output is deterministic for missing fields and artifacts."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    run_etf_sma_daily_paper_lab(
        EtfSmaDailyPaperLabConfig(
            output_root=output_root,
            bars_csv=bars_csv,
            as_of_date="2025-07-20",
            symbol="SPY",
        )
    )

    record_path = output_root / "operating_record.jsonl"
    record = json.loads(record_path.read_text(encoding="utf-8").splitlines()[0])
    del record["input_data_path"]
    del record["safety_labels"]
    record["paper_submit_authorized"] = True
    record["paper_submit_authorization_status"] = "authorized"
    record_path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_root / "manifest.jsonl").unlink()

    validation = validate_etf_sma_daily_paper_lab_packet(output_root)
    repeated_validation = validate_etf_sma_daily_paper_lab_packet(output_root)

    assert validation == repeated_validation
    assert validation["assistant_packet_version"] == "assistant_v1.1"
    assert validation["validation_status"] == "fail"
    assert validation["artifact_presence_status"]["status"] == "fail"
    assert validation["artifact_presence_status"]["missing_artifacts"] == ["manifest"]
    assert validation["artifact_presence_status"]["empty_artifacts"] == []
    assert validation["missing_required_fields"] == [
        "input_data_path",
        "safety_labels",
        "paper_submit_authorized_false_or_not_authorized",
    ]



def test_etf_sma_daily_paper_lab_insufficient_history(tmp_path: Path) -> None:
    """Test run with only 199 bars, resulting in insufficient history."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_199.csv"

    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        as_of_date="2025-07-19",
        symbol="SPY",
    )

    payload = run_etf_sma_daily_paper_lab(config)

    assert payload["posture"] == "insufficient_history"
    assert payload["decision"] == "insufficient_history"
    assert payload["sma_slow_value"] is None
    assert payload["sma_posture_status"] == (
        "insufficient_history: 199 usable bars is fewer than "
        "the 200-bar slow SMA requirement"
    )
    assert payload["next_operator_action"] == (
        "provide_at_least_200_usable_daily_bars_before_preview_use"
    )


def test_etf_sma_daily_paper_lab_defensive_bearish(tmp_path: Path) -> None:
    """Test successful run with 200 bearish bars, resulting in risk-off posture."""
    output_root = tmp_path / "paper_lab_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bearish.csv"

    config = EtfSmaDailyPaperLabConfig(
        output_root=output_root,
        bars_csv=bars_csv,
        as_of_date="2025-07-20",
        symbol="SPY",
    )

    payload = run_etf_sma_daily_paper_lab(config)

    assert payload["posture"] == "defensive_risk_off"
    assert payload["decision"] == "offline_preview_defensive_risk_off"
    assert payload["sma_posture_status"] == "risk_off: SMA50 is at or below SMA200"
    assert payload["next_operator_action"] == "review_assistant_brief_no_broker_action"


def test_etf_sma_daily_paper_lab_cli_invocation(tmp_path: Path) -> None:
    """Test invocation of the new command via CLI."""
    output_root = tmp_path / "paper_lab_cli_out"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"

    argv = [
        "etf-sma-daily-paper-lab",
        "--output-root", str(output_root),
        "--bars-csv", str(bars_csv),
        "--as-of-date", "2025-07-20",
        "--symbol", "SPY",
        "--format", "json",
    ]

    exit_code = cli_module.main(argv)
    assert exit_code == 0

    assert (output_root / "operating_brief.md").exists()
    assert (output_root / "operating_record.jsonl").exists()
    assert (output_root / "manifest.jsonl").exists()
