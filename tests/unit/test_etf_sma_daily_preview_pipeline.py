from __future__ import annotations

import ast
import json
from pathlib import Path
import pytest

from algotrader.errors import ValidationError
import algotrader.cli as cli_module
from algotrader.execution.etf_sma_daily_preview_pipeline import (
    EtfSmaDailyPreviewPipelineConfig,
    build_etf_sma_daily_preview_pipeline,
    run_etf_sma_daily_preview_pipeline,
)

MODULE_PATH = Path("src/algotrader/execution/etf_sma_daily_preview_pipeline.py")
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


def _write_valid_m447(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M447",
        "command": "etf-sma-offline-daily-cycle-rerun-m446",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "recommended_operator_action": "observe_hold_noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m448(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M448",
        "command": "etf-sma-refreshed-current-cycle-rollup-m448",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "posture": "risk_on",
        "cycle_decision": "hold/noop",
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    record.update(overrides)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return record


def _write_valid_m449(path: Path, **overrides) -> dict:
    record = {
        "milestone": "M449",
        "command": "etf-sma-daily-preview-run",
        "daily_preview_run_state": "preview_only_daily_run_ready",
        "operating_brief_state": "ready",
        "schedule_contract_state": "local_preview_contract_ready",
        "freshness_state": "accepted_current_adjusted_bars",
        "freshness_blockers": [],
        "expected_latest_bar_date": EXPECTED_DATE,
        "latest_local_bar_date": EXPECTED_DATE,
        "current_action": "observe_hold_noop",
        "recommended_operator_action": "observe_hold_noop",
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


@pytest.fixture
def patch_stages(monkeypatch):
    """Sets up stage function monkeypatches that write correct JSON by default."""
    def mock_run_m447(cfg):
        _write_valid_m447(Path(cfg.output_jsonl))

    def mock_run_m448(cfg):
        _write_valid_m448(Path(cfg.output_jsonl))

    def mock_run_m449(cfg):
        _write_valid_m449(Path(cfg.output_jsonl))

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        mock_run_m447,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        mock_run_m448,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        mock_run_m449,
    )


def test_cli_registration(tmp_path, patch_stages, monkeypatch, capsys) -> None:
    m447_path = tmp_path / "m447.jsonl"
    m448_path = tmp_path / "m448.jsonl"
    m449_path = tmp_path / "m449.jsonl"
    m450_path = tmp_path / "m450.jsonl"

    exit_code = cli_module.main(
        [
            "etf-sma-daily-preview-pipeline",
            "--m447-output-jsonl",
            str(m447_path),
            "--m448-output-jsonl",
            str(m448_path),
            "--m449-output-jsonl",
            str(m449_path),
            "--output-jsonl",
            str(m450_path),
        ]
    )

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["milestone"] == "M450"
    assert printed["pipeline_state"] == "preview_pipeline_ready"


def test_successful_accepted_pipeline(tmp_path, patch_stages) -> None:
    m447_path = tmp_path / "m447.jsonl"
    m448_path = tmp_path / "m448.jsonl"
    m449_path = tmp_path / "m449.jsonl"
    m450_path = tmp_path / "m450.jsonl"

    config = EtfSmaDailyPreviewPipelineConfig(
        m447_output_jsonl=m447_path,
        m448_output_jsonl=m448_path,
        m449_output_jsonl=m449_path,
        output_jsonl=m450_path,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)

    assert payload["milestone"] == "M450"
    assert payload["pipeline_state"] == "preview_pipeline_ready"
    assert payload["stages_run"] == ["M447", "M448", "M449"]
    assert payload["stages_validated"] == ["M447", "M448", "M449"]
    assert payload["current_action"] == "observe_hold_noop"
    assert payload["recommended_operator_action"] == "observe_hold_noop"
    assert payload["freshness_state"] == "accepted_current_adjusted_bars"
    assert payload["expected_latest_bar_date"] == EXPECTED_DATE
    assert payload["latest_local_bar_date"] == EXPECTED_DATE
    assert payload["blockers"] == []

    # Safety/Mutation flags
    for k in (
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
        assert payload[k] is False

    assert payload["profit_claim"] == "none"

    # Repeated runs determinism
    payload_repeat = run_etf_sma_daily_preview_pipeline(config)
    assert payload == payload_repeat


def test_prevention_of_stale_artifact_acceptance(tmp_path, monkeypatch) -> None:
    m447_path = tmp_path / "m447.jsonl"
    m448_path = tmp_path / "m448.jsonl"
    m449_path = tmp_path / "m449.jsonl"
    m450_path = tmp_path / "m450.jsonl"

    # Pre-write valid-looking stale output files
    _write_valid_m447(m447_path)
    _write_valid_m448(m448_path)
    _write_valid_m449(m449_path)

    # Mock M447 to succeed but M448 execution to raise exception
    def mock_run_m447(cfg):
        _write_valid_m447(Path(cfg.output_jsonl))

    def mock_run_m448_fail(cfg):
        raise RuntimeError("Rollup execution failed")

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        mock_run_m447,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        mock_run_m448_fail,
    )

    config = EtfSmaDailyPreviewPipelineConfig(
        m447_output_jsonl=m447_path,
        m448_output_jsonl=m448_path,
        m449_output_jsonl=m449_path,
        output_jsonl=m450_path,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)

    # M448 target file must have been deleted/cleaned and not accepted stale
    assert not m448_path.exists()
    assert payload["pipeline_state"] == "blocked"
    assert "m448_stage_failed" in payload["blockers"]
    assert payload["stages_run"] == ["M447", "M448"]
    assert payload["stages_validated"] == ["M447"]
    assert payload["failed_stage"] == "M448"


@pytest.mark.parametrize(
    "stage,blocker_sfx,write_fn",
    [
        ("M447", "m447_", _write_valid_m447),
        ("M448", "m448_", _write_valid_m448),
        ("M449", "m449_", _write_valid_m449),
    ],
)
def test_blocked_scenarios(tmp_path, monkeypatch, stage, blocker_sfx, write_fn) -> None:
    # Setup paths
    m447_path = tmp_path / "m447.jsonl"
    m448_path = tmp_path / "m448.jsonl"
    m449_path = tmp_path / "m449.jsonl"
    m450_path = tmp_path / "m450.jsonl"

    config = EtfSmaDailyPreviewPipelineConfig(
        m447_output_jsonl=m447_path,
        m448_output_jsonl=m448_path,
        m449_output_jsonl=m449_path,
        output_jsonl=m450_path,
    )

    # 1. Missing artifact
    def run_stage_missing(cfg):
        pass  # does not write the file

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_missing,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_missing,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_missing,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}artifact_missing" in payload["blockers"]
    assert payload["pipeline_state"] == "blocked"

    # 2. Record count not one (multiple lines)
    def run_stage_multiple(cfg):
        p = Path(cfg.output_jsonl)
        write_fn(p)
        p.write_text(p.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_multiple,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_multiple,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_multiple,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}record_count_not_one" in payload["blockers"]

    # 3. Malformed JSON
    def run_stage_malformed(cfg):
        Path(cfg.output_jsonl).write_text("{malformed\n", encoding="utf-8")

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_malformed,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_malformed,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_malformed,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}malformed_json" in payload["blockers"]

    # 4. Freshness not accepted
    def run_stage_stale(cfg):
        write_fn(Path(cfg.output_jsonl), freshness_state="stale_bars")

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_stale,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_stale,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_stale,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}freshness_not_accepted" in payload["blockers"]

    # 5. Freshness blockers present
    def run_stage_freshness_blockers(cfg):
        write_fn(Path(cfg.output_jsonl), freshness_blockers=["stale_clock"])

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_freshness_blockers,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_freshness_blockers,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_freshness_blockers,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}freshness_blockers_present" in payload["blockers"]

    # 6. Latest bar date mismatch
    def run_stage_date_mismatch(cfg):
        write_fn(Path(cfg.output_jsonl), expected_latest_bar_date="2026-06-08", latest_local_bar_date="2026-06-07")

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_date_mismatch,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_date_mismatch,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_date_mismatch,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}latest_bar_date_mismatch" in payload["blockers"]

    # 7. Action unexpected
    def run_stage_unexpected(cfg):
        if stage == "M447" or stage == "M448":
            write_fn(Path(cfg.output_jsonl), posture="defensive")
        else:
            write_fn(Path(cfg.output_jsonl), daily_preview_run_state="blocked")

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_unexpected,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_unexpected,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_unexpected,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}action_unexpected" in payload["blockers"]

    # 8. True safety flag
    def run_stage_safety_violation(cfg):
        write_fn(Path(cfg.output_jsonl), submitted=True)

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_safety_violation,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_safety_violation,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_safety_violation,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}safety_flags_not_false" in payload["blockers"]

    # 9. Non-none profit claim
    def run_stage_profit_violation(cfg):
        write_fn(Path(cfg.output_jsonl), profit_claim="some_claim")

    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_offline_daily_cycle_rerun_m446",
        (lambda cfg: _write_valid_m447(Path(cfg.output_jsonl))) if stage != "M447" else run_stage_profit_violation,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_refreshed_current_cycle_rollup_m448",
        (lambda cfg: _write_valid_m448(Path(cfg.output_jsonl))) if stage != "M448" else run_stage_profit_violation,
    )
    monkeypatch.setattr(
        "algotrader.execution.etf_sma_daily_preview_pipeline.run_etf_sma_daily_preview_run",
        (lambda cfg: _write_valid_m449(Path(cfg.output_jsonl))) if stage != "M449" else run_stage_profit_violation,
    )

    payload = run_etf_sma_daily_preview_pipeline(config)
    assert f"{blocker_sfx}profit_claim_not_none" in payload["blockers"]


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
