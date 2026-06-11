from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_soak_closeout_packet import (
    EtfSmaDailySoakCloseoutPacketConfig,
    run_etf_sma_daily_soak_closeout_packet,
)


@pytest.fixture(autouse=True)
def enforce_preflight_offline_only() -> None:
    """Ensure that no credentials or paper profiles are present in the environment."""
    assert os.environ.get("APP_PROFILE") != "paper"
    for var in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        assert var not in os.environ


def _safety_authorizations() -> dict[str, bool]:
    return {
        "live_authorized": False,
        "paper_submit_authorized": False,
        "paper_broker_reads_authorized": False,
        "broker_mutation_authorized": False,
        "network_authorized": False,
        "credentials_loaded": False,
    }


def _history_records(
    *,
    latest_status: str = "accepted",
    golden_status: str = "accepted",
    release_status: str = "accepted",
    latest_blockers: list[str] | None = None,
    attempted: int = 10,
    accepted: int = 10,
    blocked: int = 0,
    insufficient: int = 0,
) -> list[dict[str, Any]]:
    blockers = latest_blockers or []
    trends = {blocker: 1 for blocker in blockers}
    safety = _safety_authorizations()
    key_artifacts = ["runs/daily_soak/2025-06-01_2025-06-10/rollup.jsonl"]
    return [
        {
            "accepted_count": accepted,
            "attempted_count": attempted,
            "blocked_count": blocked,
            "blocker_trends": trends,
            "indexed_golden_acceptance_count": 1,
            "input_daily_soak_dir": "runs/daily_soak",
            "insufficient_history_count": insufficient,
            "key_artifact_paths": key_artifacts,
            "latest_as_of": "2025-06-10",
            "latest_golden_acceptance_status": golden_status,
            "latest_release_gate_status": release_status,
            "latest_run_id": "2025-06-01_2025-06-10",
            "phase": "V3J",
            "record_type": "summary",
            "safety_authorizations": safety,
            "scanned_file_count": 1,
            "status": latest_status,
            "validation_finding_count_total": 0,
        },
        {
            "key_artifact_paths": key_artifacts,
            "latest_as_of": "2025-06-10",
            "latest_golden_acceptance_status": golden_status,
            "latest_release_gate_status": release_status,
            "phase": "V3J",
            "record_type": "latest_run",
            "safety_authorizations": safety,
        },
        {
            "blocker_trends": trends,
            "phase": "V3J",
            "record_type": "blocker_trends",
            "safety_authorizations": safety,
        },
        {
            "accepted_date_count": accepted,
            "attempted_date_count": attempted,
            "blocked_date_count": blocked,
            "blockers": blockers,
            "end_date": "2025-06-10",
            "file_path": "runs/daily_soak/soak_golden_acceptance.jsonl",
            "golden_acceptance_status": golden_status,
            "insufficient_history_date_count": insufficient,
            "phase": "V3J",
            "record_type": "per_run",
            "release_gate_status": release_status,
            "run_index": 0,
            "safety_authorizations": safety,
            "start_date": "2025-06-01",
            "validation_finding_count": 0,
        },
    ]


def _operator_summary_records(
    *,
    classification: str = "proceed_offline",
    golden_status: str = "accepted",
    release_status: str = "accepted",
    blockers: list[str] | None = None,
) -> list[dict[str, Any]]:
    blocker_summary = {blocker: 1 for blocker in blockers or []}
    safety = _safety_authorizations()
    base = {
        "accepted_count": 10,
        "attempted_count": 10,
        "blocked_count": 0,
        "blocker_trend_summary": blocker_summary,
        "insufficient_history_count": 0,
        "key_artifact_paths": ["runs/daily_soak/2025-06-01_2025-06-10/rollup.jsonl"],
        "latest_as_of": "2025-06-10",
        "latest_golden_acceptance_status": golden_status,
        "latest_release_gate_status": release_status,
        "latest_run_artifact_paths": ["runs/daily_soak/2025-06-01_2025-06-10/rollup.jsonl"],
        "latest_run_id": "2025-06-01_2025-06-10",
        "next_safe_action_classification": classification,
        "next_safe_action_reason": "deterministic fixture",
        "phase": "V3K",
        "recurring_blockers": sorted(blocker_summary),
        "safety_authorizations": safety,
        "source_history_index_path": "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl",
        "status": classification,
        "validation_finding_count_total": 0,
    }
    return [
        {**base, "record_type": "summary"},
        {
            "latest_as_of": "2025-06-10",
            "latest_golden_acceptance_status": golden_status,
            "latest_release_gate_status": release_status,
            "latest_run_artifact_paths": base["latest_run_artifact_paths"],
            "latest_run_id": "2025-06-01_2025-06-10",
            "phase": "V3K",
            "record_type": "latest_status",
            "safety_authorizations": safety,
            "source_history_index_path": base["source_history_index_path"],
            "status": classification,
        },
        {
            "blocker_trend_summary": blocker_summary,
            "phase": "V3K",
            "record_type": "blocker_summary",
            "recurring_blockers": sorted(blocker_summary),
            "safety_authorizations": safety,
            "source_history_index_path": base["source_history_index_path"],
            "status": classification,
        },
        {**base, "record_type": "next_action"},
    ]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )


def _write_inputs(
    tmp_path: Path,
    *,
    history_records: list[dict[str, Any]] | None = None,
    operator_records: list[dict[str, Any]] | None = None,
    markdown: str = "# Daily Lab Acceptance Operator Summary (V3K)\n",
) -> tuple[Path, Path, Path]:
    history_path = tmp_path / "v3j_history.jsonl"
    operator_path = tmp_path / "v3k_summary.jsonl"
    operator_md_path = tmp_path / "v3k_summary.md"
    _write_jsonl(history_path, history_records or _history_records())
    _write_jsonl(operator_path, operator_records or _operator_summary_records())
    operator_md_path.write_text(markdown, encoding="utf-8", newline="\n")
    return history_path, operator_path, operator_md_path


def _run_packet(
    tmp_path: Path,
    history_path: Path,
    operator_path: Path,
    operator_md_path: Path,
    *,
    out_name: str = "closeout.jsonl",
    text_name: str = "closeout.md",
) -> tuple[list[dict[str, Any]], Path, Path]:
    out_path = tmp_path / out_name
    text_out_path = tmp_path / text_name
    records = run_etf_sma_daily_soak_closeout_packet(
        EtfSmaDailySoakCloseoutPacketConfig(
            history_index=history_path,
            operator_summary=operator_path,
            operator_summary_md=operator_md_path,
            out=out_path,
            text_out=text_out_path,
        )
    )
    return records, out_path, text_out_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_closeout_packet_happy_path_deterministic_jsonl_and_markdown(
    tmp_path: Path,
) -> None:
    history_path, operator_path, operator_md_path = _write_inputs(tmp_path)

    records, out_path, text_out_path = _run_packet(
        tmp_path,
        history_path,
        operator_path,
        operator_md_path,
        out_name="closeout_1.jsonl",
        text_name="closeout_1.md",
    )
    repeat_records, repeat_out_path, repeat_text_path = _run_packet(
        tmp_path,
        history_path,
        operator_path,
        operator_md_path,
        out_name="closeout_2.jsonl",
        text_name="closeout_2.md",
    )

    assert len(records) == 1
    assert records == repeat_records
    assert out_path.read_text(encoding="utf-8") == repeat_out_path.read_text(
        encoding="utf-8"
    )
    assert text_out_path.read_text(encoding="utf-8") == repeat_text_path.read_text(
        encoding="utf-8"
    )

    packet = records[0]
    assert packet["closeout_status"] == "ready_for_operator_review"
    assert packet["recommended_next_offline_action"] == "continue_offline_daily_soak"
    assert packet["acceptance_run_window"] == {
        "end_date": "2025-06-10",
        "latest_as_of": "2025-06-10",
        "latest_run_id": "2025-06-01_2025-06-10",
        "start_date": "2025-06-01",
    }
    assert out_path.read_text(encoding="utf-8") == (
        json.dumps(packet, sort_keys=True, separators=(",", ":")) + "\n"
    )

    markdown = text_out_path.read_text(encoding="utf-8")
    assert "# V3L Daily Soak Closeout Packet" in markdown
    assert "| kind | path | exists | size_bytes | sha256 |" in markdown
    assert "## Latest Status Summary" in markdown
    assert "## Blocker Classification Summary" in markdown
    assert "## Safety Summary" in markdown
    assert "run_daily_lab_acceptance.ps1" in markdown
    assert "does not authorize broker reads, paper submit, broker mutation, or live trading" in markdown


def test_closeout_packet_release_gate_blocked_alone_is_not_inspect_blockers(
    tmp_path: Path,
) -> None:
    history_path, operator_path, operator_md_path = _write_inputs(
        tmp_path,
        history_records=_history_records(
            latest_status="blocked",
            golden_status="blocked",
            release_status="blocked",
            latest_blockers=["release_gate_blocked"],
            attempted=10,
            accepted=0,
            blocked=10,
        ),
        operator_records=_operator_summary_records(
            classification="repair_required",
            golden_status="blocked",
            release_status="blocked",
            blockers=["release_gate_blocked"],
        ),
    )

    records, _, _ = _run_packet(tmp_path, history_path, operator_path, operator_md_path)
    packet = records[0]

    assert packet["closeout_status"] == "ready_for_operator_review"
    assert packet["blocker_classification"]["requires_inspection"] is False
    assert packet["blocker_classification"]["explicit_latest_blockers"] == []
    assert packet["blocker_classification"]["generic_latest_blockers"] == [
        "release_gate_blocked"
    ]


@pytest.mark.parametrize("blocker", ["insufficient_history", "no_history", "no_data"])
def test_closeout_packet_explicit_latest_blocker_evidence_inspects(
    tmp_path: Path,
    blocker: str,
) -> None:
    history_path, operator_path, operator_md_path = _write_inputs(
        tmp_path,
        history_records=_history_records(
            latest_status="blocked",
            golden_status="blocked",
            release_status="blocked",
            latest_blockers=["release_gate_blocked", blocker],
            attempted=10,
            accepted=0,
            insufficient=10,
        ),
        operator_records=_operator_summary_records(
            classification="inspect_blockers",
            golden_status="blocked",
            release_status="blocked",
            blockers=["release_gate_blocked", blocker],
        ),
    )

    records, _, _ = _run_packet(tmp_path, history_path, operator_path, operator_md_path)
    packet = records[0]

    assert packet["closeout_status"] == "inspect_blockers"
    assert packet["recommended_next_offline_action"] == "inspect_latest_blocker_evidence"
    assert blocker in packet["blocker_classification"]["explicit_latest_blockers"]


def test_closeout_packet_missing_inputs_are_deterministic_non_success(
    tmp_path: Path,
) -> None:
    history_path, operator_path, operator_md_path = _write_inputs(tmp_path)

    missing_history = tmp_path / "missing_history.jsonl"
    records, _, _ = _run_packet(tmp_path, missing_history, operator_path, operator_md_path)
    history_packet = records[0]
    assert history_packet["closeout_status"] == "incomplete_inputs"
    assert history_packet["recommended_next_offline_action"] == "regenerate_history_index"
    assert "missing_history_index" in history_packet["incomplete_reasons"]

    missing_operator = tmp_path / "missing_operator.jsonl"
    records, _, _ = _run_packet(tmp_path, history_path, missing_operator, operator_md_path)
    operator_packet = records[0]
    assert operator_packet["closeout_status"] == "incomplete_inputs"
    assert operator_packet["recommended_next_offline_action"] == "regenerate_operator_summary"
    assert "missing_operator_summary" in operator_packet["incomplete_reasons"]


def test_closeout_packet_artifact_references_include_size_and_sha256(
    tmp_path: Path,
) -> None:
    history_path, operator_path, operator_md_path = _write_inputs(tmp_path)
    records, _, _ = _run_packet(tmp_path, history_path, operator_path, operator_md_path)

    artifacts = {artifact["kind"]: artifact for artifact in records[0]["input_artifacts"]}
    assert artifacts["history_index"]["size_bytes"] == history_path.stat().st_size
    assert artifacts["history_index"]["sha256"] == _sha256(history_path)
    assert artifacts["operator_summary_jsonl"]["size_bytes"] == operator_path.stat().st_size
    assert artifacts["operator_summary_jsonl"]["sha256"] == _sha256(operator_path)
    assert artifacts["operator_summary_markdown"]["size_bytes"] == operator_md_path.stat().st_size
    assert artifacts["operator_summary_markdown"]["sha256"] == _sha256(operator_md_path)


def test_closeout_packet_safety_booleans_and_labels(tmp_path: Path) -> None:
    history_path, operator_path, operator_md_path = _write_inputs(tmp_path)
    records, _, _ = _run_packet(tmp_path, history_path, operator_path, operator_md_path)
    packet = records[0]

    assert packet["safety_booleans"] == {
        "broker_mutations": False,
        "broker_reads": False,
        "credentials_required": False,
        "generated_runs_artifact": True,
        "live_trading": False,
        "network_required": False,
        "paper_submit": False,
    }
    for label in (
        "paper_lab_only",
        "not_live_authorized",
        "profit_claim=none",
        "offline_only",
    ):
        assert label in packet["labels"]


def test_closeout_packet_cli_integration(tmp_path: Path) -> None:
    history_path, operator_path, operator_md_path = _write_inputs(tmp_path)
    out_path = tmp_path / "cli_closeout.jsonl"
    text_out_path = tmp_path / "cli_closeout.md"

    exit_code = cli_module.main(
        [
            "etf-sma-daily-soak-closeout-packet",
            "--history-index",
            str(history_path),
            "--operator-summary",
            str(operator_path),
            "--operator-summary-md",
            str(operator_md_path),
            "--out",
            str(out_path),
            "--text-out",
            str(text_out_path),
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    assert out_path.exists()
    assert text_out_path.exists()
