from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_acceptance_gate import (
    EtfSmaDailyAcceptanceGateConfig,
    build_etf_sma_daily_acceptance_gate,
    run_etf_sma_daily_acceptance_gate,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_acceptance_gate.py")
EXPECTED_DATE = "2026-06-08"

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "urllib",
)

FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "delete",
    "getenv",
    "liquidate",
    "load_config",
    "replace_order",
    "request",
    "retry",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}

_WARNING_TEXT = "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders."


def _write_valid_m450(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M450",
        "pipeline_state": "preview_pipeline_ready",
        "stages_run": ["M447", "M448", "M449"],
        "stages_validated": ["M447", "M448", "M449"],
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m451_summary(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M451",
        "phase": "offline_daily_operator_brief_renderer",
        "command": "etf-sma-daily-operator-brief",
        "brief_state": "ready",
        "source_milestone": "M450",
        "source_pipeline_state": "preview_pipeline_ready",
        "source_stages_run": ["M447", "M448", "M449"],
        "source_stages_validated": ["M447", "M448", "M449"],
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "operator_warning": "preview_only_not_order_authorization",
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "os_scheduler_installed": False,
        "scheduler_mutation_performed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
        "blockers": [],
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m451_text(path: Path, warning: str = _WARNING_TEXT) -> None:
    content = f"Some header info\n{warning}\nSome footer info\n"
    path.write_text(content, encoding="utf-8")


def test_cli_registration(tmp_path, capsys) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl)
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    exit_code = cli_module.main(
        [
            "etf-sma-daily-acceptance-gate",
            "--pipeline-jsonl",
            str(pipeline_jsonl),
            "--brief-summary-jsonl",
            str(brief_summary_jsonl),
            "--brief-txt",
            str(brief_txt),
            "--output-jsonl",
            str(output_jsonl),
        ]
    )

    assert exit_code == 0
    printed = capsys.readouterr().out
    assert "ETF/SMA Daily Acceptance Gate (M452) - ACCEPTED FOR OBSERVATION" in printed
    assert "Acceptance Gate State: accepted_for_preview_only_observation" in printed


def test_cli_registration_json_format(tmp_path, capsys) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl)
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    exit_code = cli_module.main(
        [
            "etf-sma-daily-acceptance-gate",
            "--pipeline-jsonl",
            str(pipeline_jsonl),
            "--brief-summary-jsonl",
            str(brief_summary_jsonl),
            "--brief-txt",
            str(brief_txt),
            "--output-jsonl",
            str(output_jsonl),
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M452"
    assert printed["acceptance_gate_state"] == "accepted_for_preview_only_observation"


def test_successful_acceptance_gate(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl)
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)

    assert payload["milestone"] == "M452"
    assert payload["acceptance_gate_state"] == "accepted_for_preview_only_observation"
    assert payload["accepted_for_operator_observation"] is True
    assert payload["blockers"] == []

    # Verify JSONL content
    jsonl_lines = output_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(jsonl_lines) == 1
    jsonl_data = json.loads(jsonl_lines[0])
    assert jsonl_data["milestone"] == "M452"
    assert jsonl_data["acceptance_gate_state"] == "accepted_for_preview_only_observation"
    assert jsonl_data["accepted_for_operator_observation"] is True
    assert jsonl_data["order_authorization"] is False
    assert jsonl_data["paper_submit_allowed"] is False
    assert jsonl_data["live_submit_allowed"] is False
    assert jsonl_data["scheduler_install_allowed"] is False
    assert jsonl_data["text_warning_present"] is True

    for flag in (
        "submitted",
        "mutated",
        "broker_action_performed",
        "network_access_attempted",
        "credential_access_attempted",
        "live_authorized",
        "os_scheduler_installed",
        "scheduler_mutation_performed",
    ):
        assert jsonl_data[flag] is False

    # Determinism check
    payload_repeat = run_etf_sma_daily_acceptance_gate(config)
    assert payload == payload_repeat


def test_missing_m450_artifact_blocks(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "missing_m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert payload["accepted_for_operator_observation"] is False
    assert "pipeline_jsonl_missing" in payload["blockers"]


def test_missing_m451_summary_artifact_blocks(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "missing_m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert "brief_summary_jsonl_missing" in payload["blockers"]


def test_missing_m451_text_artifact_blocks(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "missing_m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl)
    _write_valid_m451_summary(brief_summary_jsonl)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert "brief_txt_missing" in payload["blockers"]


def test_multiple_record_inputs_block(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    rec1 = json.dumps({"milestone": "M450"})
    pipeline_jsonl.write_text(f"{rec1}\n{rec1}\n", encoding="utf-8")
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert "pipeline_jsonl_record_count_not_one" in payload["blockers"]


def test_m450_pipeline_state_not_ready_blocks(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl, pipeline_state="blocked")
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert "pipeline_state_not_ready" in payload["blockers"]


def test_m451_brief_state_not_ready_blocks(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl)
    _write_valid_m451_summary(brief_summary_jsonl, brief_state="blocked")
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert "brief_state_not_ready" in payload["blockers"]


def test_mismatched_stages_block(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl, stages_run=["M447"])
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert (
        "pipeline_stages_unexpected" in payload["blockers"]
        or "mismatched_stages_run" in payload["blockers"]
    )


def test_mismatched_latest_bar_dates_block(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl, latest_local_bar_date="2026-06-07")
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert (
        "pipeline_latest_bar_date_unexpected" in payload["blockers"]
        or "mismatched_latest_local_bar_date" in payload["blockers"]
    )


def test_missing_text_warning_blocks(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl)
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt, warning="Warning line missing entirely")

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert "brief_txt_warning_missing" in payload["blockers"]


def test_non_empty_blockers_block(tmp_path) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl, blockers=["random_pipeline_blocker"])
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert "pipeline_has_blockers" in payload["blockers"]


@pytest.mark.parametrize(
    "override_key, override_val, expected_blocker",
    [
        ("submitted", True, "pipeline_safety_flags_not_false"),
        ("mutated", True, "pipeline_safety_flags_not_false"),
        ("broker_action_performed", True, "pipeline_safety_flags_not_false"),
        ("network_access_attempted", True, "pipeline_safety_flags_not_false"),
        ("credential_access_attempted", True, "pipeline_safety_flags_not_false"),
        ("live_authorized", True, "pipeline_safety_flags_not_false"),
        ("os_scheduler_installed", True, "pipeline_scheduler_flags_not_false"),
        ("scheduler_mutation_performed", True, "pipeline_scheduler_flags_not_false"),
        ("paper_submit_allowed", True, "pipeline_safety_flags_not_false"),
        ("live_submit_allowed", True, "pipeline_safety_flags_not_false"),
    ],
)
def test_safety_and_scheduler_flags_block(
    tmp_path, override_key, override_val, expected_blocker
) -> None:
    pipeline_jsonl = tmp_path / "m450.jsonl"
    brief_summary_jsonl = tmp_path / "m451_summary.jsonl"
    brief_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m452.jsonl"

    _write_valid_m450(pipeline_jsonl, **{override_key: override_val})
    _write_valid_m451_summary(brief_summary_jsonl)
    _write_valid_m451_text(brief_txt)

    config = EtfSmaDailyAcceptanceGateConfig(
        pipeline_jsonl=pipeline_jsonl,
        brief_summary_jsonl=brief_summary_jsonl,
        brief_txt=brief_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_acceptance_gate(config)
    assert payload["acceptance_gate_state"] == "blocked_or_invalid"
    assert expected_blocker in payload["blockers"]


def test_imports_and_calls_invariant() -> None:
    with open(MODULE_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(MODULE_PATH))

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    # Check forbidden imports
    for prefix in FORBIDDEN_IMPORT_PREFIXES:
        for imp in imports:
            assert not (
                imp == prefix or imp.startswith(f"{prefix}.")
            ), f"Forbidden import: {imp}"

    # Check call names
    call_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                call_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    call_names.add(f"{func.value.id}.{func.attr}")
                else:
                    call_names.add(func.attr)

    violations = call_names.intersection(FORBIDDEN_CALL_NAMES)
    assert not violations, f"Forbidden calls found: {violations}"
