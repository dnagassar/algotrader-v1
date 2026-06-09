from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_operator_brief import (
    EtfSmaDailyOperatorBriefConfig,
    build_etf_sma_daily_operator_brief,
    run_etf_sma_daily_operator_brief,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_operator_brief.py")
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
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def test_cli_registration(tmp_path, capsys) -> None:
    input_jsonl = tmp_path / "m450.jsonl"
    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    _write_valid_m450(input_jsonl)

    exit_code = cli_module.main(
        [
            "etf-sma-daily-operator-brief",
            "--input-jsonl",
            str(input_jsonl),
            "--output-txt",
            str(output_txt),
            "--output-jsonl",
            str(output_jsonl),
        ]
    )

    assert exit_code == 0
    printed = capsys.readouterr().out
    assert "ETF/SMA Daily Operator Brief (M451)" in printed
    assert "WARNING: This brief is preview-only" in printed


def test_cli_registration_json_format(tmp_path, capsys) -> None:
    input_jsonl = tmp_path / "m450.jsonl"
    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    _write_valid_m450(input_jsonl)

    exit_code = cli_module.main(
        [
            "etf-sma-daily-operator-brief",
            "--input-jsonl",
            str(input_jsonl),
            "--output-txt",
            str(output_txt),
            "--output-jsonl",
            str(output_jsonl),
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M451"
    assert printed["brief_state"] == "ready"


def test_successful_operator_brief_rendering(tmp_path) -> None:
    input_jsonl = tmp_path / "m450.jsonl"
    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    _write_valid_m450(input_jsonl)

    config = EtfSmaDailyOperatorBriefConfig(
        input_jsonl=input_jsonl,
        output_txt=output_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_operator_brief(config)

    assert payload["milestone"] == "M451"
    assert payload["brief_state"] == "ready"
    assert payload["blockers"] == []

    # Verify text brief content
    txt_content = output_txt.read_text(encoding="utf-8")
    assert "ETF/SMA Daily Operator Brief (M451)" in txt_content
    assert "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders." in txt_content
    assert f"Latest Local Bar Date: {EXPECTED_DATE}" in txt_content
    assert "Posture: risk_on" in txt_content
    assert "Cycle Decision: hold/noop" in txt_content
    assert "Current Action: observe_hold_noop" in txt_content
    assert "Recommended Operator Action: observe_hold_noop" in txt_content
    assert "Stages Validated: M447, M448, M449" in txt_content
    assert "Blockers: none" in txt_content
    assert "Safety Flags: submitted=false, mutated=false, broker_action_performed=false" in txt_content

    # Verify JSONL content
    jsonl_lines = output_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(jsonl_lines) == 1
    jsonl_data = json.loads(jsonl_lines[0])
    assert jsonl_data["milestone"] == "M451"
    assert jsonl_data["brief_state"] == "ready"
    assert jsonl_data["operator_warning"] == "preview_only_not_order_authorization"

    for flag in (
        "submitted",
        "mutated",
        "broker_action_performed",
        "network_access_attempted",
        "credential_access_attempted",
        "live_authorized",
        "os_scheduler_installed",
        "scheduler_mutation_performed",
        "paper_submit_allowed",
        "live_submit_allowed",
    ):
        assert jsonl_data[flag] is False

    # Determinism / byte-identical check
    payload_repeat = run_etf_sma_daily_operator_brief(config)
    assert payload == payload_repeat

    txt_content_repeat = output_txt.read_text(encoding="utf-8")
    jsonl_lines_repeat = output_jsonl.read_text(encoding="utf-8").splitlines()

    assert txt_content == txt_content_repeat
    assert jsonl_lines == jsonl_lines_repeat


def test_missing_input_file_blocks(tmp_path) -> None:
    input_jsonl = tmp_path / "missing_m450.jsonl"
    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    config = EtfSmaDailyOperatorBriefConfig(
        input_jsonl=input_jsonl,
        output_txt=output_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_operator_brief(config)
    assert payload["brief_state"] == "blocked"
    assert payload["current_action"] == "blocked/fail_closed"
    assert "input_jsonl_missing" in payload["blockers"]

    # Verify files written
    assert output_txt.exists()
    assert output_jsonl.exists()
    assert "BLOCKED / FAIL-CLOSED" in output_txt.read_text(encoding="utf-8")
    assert "input_jsonl_missing" in output_txt.read_text(encoding="utf-8")


def test_empty_input_file_blocks(tmp_path) -> None:
    input_jsonl = tmp_path / "empty_m450.jsonl"
    input_jsonl.write_text("\n   \n", encoding="utf-8")
    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    config = EtfSmaDailyOperatorBriefConfig(
        input_jsonl=input_jsonl,
        output_txt=output_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_operator_brief(config)
    assert payload["brief_state"] == "blocked"
    assert "input_jsonl_record_count_not_one" in payload["blockers"]


def test_multiple_records_block(tmp_path) -> None:
    input_jsonl = tmp_path / "multi_m450.jsonl"
    rec1 = json.dumps({"milestone": "M450"})
    rec2 = json.dumps({"milestone": "M450"})
    input_jsonl.write_text(f"{rec1}\n{rec2}\n", encoding="utf-8")
    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    config = EtfSmaDailyOperatorBriefConfig(
        input_jsonl=input_jsonl,
        output_txt=output_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_operator_brief(config)
    assert payload["brief_state"] == "blocked"
    assert "input_jsonl_record_count_not_one" in payload["blockers"]


def test_malformed_json_blocks(tmp_path) -> None:
    input_jsonl = tmp_path / "malformed_m450.jsonl"
    input_jsonl.write_text("{malformedjson\n", encoding="utf-8")
    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    config = EtfSmaDailyOperatorBriefConfig(
        input_jsonl=input_jsonl,
        output_txt=output_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_operator_brief(config)
    assert payload["brief_state"] == "blocked"
    assert "input_jsonl_malformed_json" in payload["blockers"]


def test_missing_required_fields_blocks(tmp_path) -> None:
    input_jsonl = tmp_path / "missing_fields.jsonl"
    _write_valid_m450(input_jsonl)
    
    # Read record, remove some keys, and rewrite
    data = json.loads(input_jsonl.read_text(encoding="utf-8").strip())
    del data["pipeline_state"]
    del data["stages_run"]
    input_jsonl.write_text(json.dumps(data) + "\n", encoding="utf-8")

    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    config = EtfSmaDailyOperatorBriefConfig(
        input_jsonl=input_jsonl,
        output_txt=output_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_operator_brief(config)
    assert payload["brief_state"] == "blocked"
    assert "input_jsonl_missing_required_fields" in payload["blockers"]


@pytest.mark.parametrize(
    "override_key, override_val, expected_blocker",
    [
        ("milestone", "M449", "source_milestone_not_m450"),
        ("pipeline_state", "blocked", "source_pipeline_not_ready"),
        ("stages_run", ["M447", "M448"], "source_stages_unexpected"),
        ("stages_validated", ["M447", "M448"], "source_stages_unexpected"),
        ("freshness_state", "stale_bars", "source_freshness_not_accepted"),
        ("freshness_blockers", ["some_blocker"], "source_freshness_blockers_present"),
        ("expected_latest_bar_date", "2026-06-09", "source_latest_bar_date_mismatch"),
        ("latest_local_bar_date", "2026-06-07", "source_latest_bar_date_mismatch"),
        ("current_action", "buy", "source_action_unexpected"),
        ("recommended_operator_action", "sell", "source_action_unexpected"),
        ("blockers", ["random_blocker"], "source_blockers_present"),
        ("submitted", True, "source_safety_flags_not_false"),
        ("mutated", True, "source_safety_flags_not_false"),
        ("broker_action_performed", True, "source_safety_flags_not_false"),
        ("network_access_attempted", True, "source_safety_flags_not_false"),
        ("credential_access_attempted", True, "source_safety_flags_not_false"),
        ("live_authorized", True, "source_safety_flags_not_false"),
        ("os_scheduler_installed", True, "source_scheduler_flags_not_false"),
        ("scheduler_mutation_performed", True, "source_scheduler_flags_not_false"),
        ("paper_submit_allowed", True, "source_submit_permissions_not_false"),
        ("live_submit_allowed", True, "source_submit_permissions_not_false"),
        ("profit_claim", "some_performance_metric", "source_profit_claim_not_none"),
    ],
)
def test_blocked_scenarios(tmp_path, override_key, override_val, expected_blocker) -> None:
    input_jsonl = tmp_path / "blocked_m450.jsonl"
    _write_valid_m450(input_jsonl, **{override_key: override_val})

    output_txt = tmp_path / "m451.txt"
    output_jsonl = tmp_path / "m451.jsonl"

    config = EtfSmaDailyOperatorBriefConfig(
        input_jsonl=input_jsonl,
        output_txt=output_txt,
        output_jsonl=output_jsonl,
    )

    payload = run_etf_sma_daily_operator_brief(config)
    assert payload["brief_state"] == "blocked"
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
            assert not (imp == prefix or imp.startswith(f"{prefix}.")), f"Forbidden import: {imp}"

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
