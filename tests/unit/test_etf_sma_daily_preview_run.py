from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_preview_run import (
    EtfSmaDailyPreviewRunConfig,
    build_etf_sma_daily_preview_run,
    run_etf_sma_daily_preview_run,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_preview_run.py")
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


def _write_m448_rollup(
    path: Path,
    expected_date: str = EXPECTED_DATE,
    latest_date: str = EXPECTED_DATE,
    freshness_state: str = "accepted_current_adjusted_bars",
    freshness_blockers: list = None,
    current_action: str = "observe_hold_noop",
    cycle_decision: str = "hold/noop",
    posture: str = "risk_on",
    submitted: bool = False,
    mutated: bool = False,
    broker_action_performed: bool = False,
    network_access_attempted: bool = False,
    credential_access_attempted: bool = False,
    live_authorized: bool = False,
    profit_claim: str = "none",
) -> None:
    if freshness_blockers is None:
        freshness_blockers = []
    record = {
        "broker_action_performed": broker_action_performed,
        "command": "etf-sma-refreshed-current-cycle-rollup-m448",
        "credential_access_attempted": credential_access_attempted,
        "current_action": current_action,
        "cycle_decision": cycle_decision,
        "expected_latest_bar_date": expected_date,
        "freshness_blockers": freshness_blockers,
        "freshness_state": freshness_state,
        "latest_local_bar_date": latest_date,
        "live_authorized": live_authorized,
        "milestone": "M448",
        "mutated": mutated,
        "network_access_attempted": network_access_attempted,
        "paper_action_authorized": False,
        "paper_submit_authorized": False,
        "posture": posture,
        "profit_claim": profit_claim,
        "recommended_operator_action": "observe_hold_noop",
        "record_type": "m448_refreshed_current_cycle_rollup",
        "run_id": "m448_refreshed_current_cycle_rollup",
        "source_m447_manifest_path": "runs\\paper_lab\\m447_offline_daily_cycle_m446_rerun_manifest.jsonl",
        "source_m447_manifest_sha256": "948f69bc6ece90710b07859e1f4dfdbaeaa41b71206099cc1f6cd4af90117d09",
        "submit_authorized": False,
        "submitted": submitted,
    }
    content = json.dumps(record) + "\n"
    path.write_bytes(content.encode("utf-8"))


def test_successful_preview_run_execution(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path)

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    # Required field validations for accepted case
    assert payload["milestone"] == "M449"
    assert payload["phase"] == "offline_preview_only_daily_operating_brief_automation_packet"
    assert payload["command"] == "etf-sma-daily-preview-run"
    assert payload["source_rollup_path"] == str(source_path)
    assert payload["source_rollup_record_count"] == 1
    assert payload["source_rollup_loaded"] is True
    assert payload["source_current_action"] == "observe_hold_noop"
    assert payload["source_cycle_decision"] == "hold/noop"
    assert payload["source_posture"] == "risk_on"
    assert payload["freshness_state"] == "accepted_current_adjusted_bars"
    assert payload["freshness_blockers"] == []
    assert payload["expected_latest_bar_date"] == EXPECTED_DATE
    assert payload["latest_local_bar_date"] == EXPECTED_DATE
    assert payload["daily_preview_run_state"] == "preview_only_daily_run_ready"
    assert payload["operating_brief_state"] == "ready"
    assert payload["schedule_contract_state"] == "local_preview_contract_ready"
    assert payload["os_scheduler_installed"] is False
    assert payload["scheduler_mutation_performed"] is False
    assert payload["paper_submit_allowed"] is False
    assert payload["live_submit_allowed"] is False
    assert payload["current_action"] == "observe_hold_noop"
    assert payload["recommended_operator_action"] == "observe_hold_noop"
    assert payload["next_safe_command"] == "python -m algotrader.cli etf-sma-daily-preview-run"
    assert payload["source_refresh_prerequisite"] == "refresh_adjusted_bars_and_rerun_current_cycle_rollup_before_relying_on_a_new_trading_day"
    assert payload["blockers"] == []
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["profit_claim"] == "none"

    # Verify JSONL content contains exactly one record
    lines = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0] == payload


def test_command_determinism(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path1 = tmp_path / "m449_preview1.jsonl"
    output_path2 = tmp_path / "m449_preview2.jsonl"

    _write_m448_rollup(source_path)

    config1 = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path1,
    )
    config2 = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path2,
    )

    payload1 = run_etf_sma_daily_preview_run(config1)
    payload2 = run_etf_sma_daily_preview_run(config2)

    assert payload1 == payload2
    assert output_path1.read_text(encoding="utf-8") == output_path2.read_text(encoding="utf-8")


def test_blocked_missing_source(tmp_path) -> None:
    output_path = tmp_path / "m449_preview.jsonl"

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=tmp_path / "nonexistent.jsonl",
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert payload["operating_brief_state"] == "blocked"
    assert payload["schedule_contract_state"] == "blocked"
    assert payload["source_rollup_loaded"] is False
    assert "source_rollup_record_count" not in payload
    assert payload["blockers"] == ["missing_source_rollup"]

    # Verify all safety/mutation/scheduler/submit flags are false
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["os_scheduler_installed"] is False
    assert payload["scheduler_mutation_performed"] is False
    assert payload["paper_submit_allowed"] is False
    assert payload["live_submit_allowed"] is False
    assert payload["profit_claim"] == "none"


def test_blocked_empty_source(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    source_path.write_bytes(b"\n\n")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert payload["source_rollup_loaded"] is True
    assert payload["source_rollup_record_count"] == 0
    assert "source_rollup_record_count_not_one" in payload["blockers"]


def test_blocked_multiple_records(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    rec1 = {"milestone": "M448"}
    rec2 = {"milestone": "M448"}
    content = json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n"
    source_path.write_bytes(content.encode("utf-8"))

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert payload["source_rollup_loaded"] is True
    assert payload["source_rollup_record_count"] == 2
    assert "source_rollup_record_count_not_one" in payload["blockers"]


def test_blocked_malformed_json(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    source_path.write_bytes(b"{invalid_json\n")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_rollup_malformed_json" in payload["blockers"]


def test_blocked_missing_required_fields(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    record = {"milestone": "M448"}
    source_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_rollup_missing_required_fields" in payload["blockers"]


def test_blocked_freshness_state_mismatch(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path, freshness_state="stale_bars")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_freshness_state_not_accepted" in payload["blockers"]


def test_blocked_freshness_blockers_present(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path, freshness_blockers=["some_blocker"])

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_freshness_blockers_present" in payload["blockers"]


def test_blocked_latest_bar_date_mismatch(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path, expected_date="2026-06-08", latest_date="2026-06-07")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_latest_bar_date_mismatch" in payload["blockers"]


def test_blocked_current_action_unexpected(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path, current_action="buy")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_current_action_unexpected" in payload["blockers"]


def test_blocked_cycle_decision_unexpected(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path, cycle_decision="buy")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_cycle_decision_unexpected" in payload["blockers"]


def test_blocked_posture_unexpected(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path, posture="defensive")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_posture_unexpected" in payload["blockers"]


@pytest.mark.parametrize("flag_name", ["submitted", "mutated", "broker_action_performed", "network_access_attempted", "credential_access_attempted", "live_authorized"])
def test_blocked_safety_flags_not_false(tmp_path, flag_name) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    kwargs = {flag_name: True}
    _write_m448_rollup(source_path, **kwargs)

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_safety_flags_not_false" in payload["blockers"]


def test_blocked_profit_claim_not_none(tmp_path) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path, profit_claim="some_claim")

    config = EtfSmaDailyPreviewRunConfig(
        source_rollup_jsonl=source_path,
        output_jsonl=output_path,
    )

    payload = run_etf_sma_daily_preview_run(config)

    assert payload["daily_preview_run_state"] == "blocked_fail_closed"
    assert "source_profit_claim_not_none" in payload["blockers"]


def test_cli_dispatch_works(tmp_path, capsys) -> None:
    source_path = tmp_path / "m448_rollup.jsonl"
    output_path = tmp_path / "m449_preview.jsonl"

    _write_m448_rollup(source_path)

    exit_code = cli_module.main(
        [
            "etf-sma-daily-preview-run",
            "--source-rollup-jsonl",
            str(source_path),
            "--output-jsonl",
            str(output_path),
        ]
    )

    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert printed["milestone"] == "M449"
    assert printed["daily_preview_run_state"] == "preview_only_daily_run_ready"


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
