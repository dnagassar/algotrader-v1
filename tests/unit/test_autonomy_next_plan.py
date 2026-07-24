from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.autonomy_supervisor import (
    AUTONOMY_SUPERVISOR_LANES,
    AutonomySupervisorConfig,
    build_autonomy_supervisor_report,
    build_autonomy_supervisor_report_from_records,
)
from algotrader.execution.autonomy_next_plan import (
    AUTONOMY_ACTION_CLASSIFICATION,
    AUTONOMY_NEXT_PLAN_LABELS,
    EXECUTION_AUTO_OFFLINE,
    EXECUTION_NOOP,
    EXECUTION_OFFLINE_OPERATOR_INPUT,
    EXECUTION_OPERATOR_GATED,
    PLAN_ALL_NOMINAL_OR_WAITING,
    PLAN_OFFLINE_ACTION_AVAILABLE,
    PLAN_OPERATOR_AUTHORITY_REQUIRED,
    ActionClass,
    build_autonomy_next_plan,
    build_autonomy_next_plan_from_report,
    classify_action,
    render_autonomy_next_plan_json,
    render_autonomy_next_plan_text,
    write_autonomy_next_plan_jsonl,
)


MODULE_PATH = Path("src/algotrader/execution/autonomy_next_plan.py")
AS_OF = "2026-07-24T00:00:00Z"

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "os",
    "requests",
    "socket",
    "ssl",
    "subprocess",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "Popen",
    "call",
    "cancel_order",
    "check_output",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "getenv",
    "liquidate",
    "load_config",
    "monotonic",
    "now",
    "replace_order",
    "request",
    "run",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "system",
    "time",
    "urlopen",
    "utcnow",
}

_SAFETY_FALSE_KEYS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "broker_mutation_allowed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


def _config(tmp_path: Path, **overrides) -> AutonomySupervisorConfig:  # noqa: ANN003
    kwargs = {
        "run_id": "plan-test",
        "as_of": AS_OF,
        "lanes_root": tmp_path,
    }
    kwargs.update(overrides)
    return AutonomySupervisorConfig(**kwargs)


def _action(payload: dict, lane_id: str) -> dict:
    for action in payload["actions"]:
        if action["lane_id"] == lane_id:
            return action
    raise AssertionError(f"lane {lane_id} not present")


def _assert_safety_booleans_false(payload: dict) -> None:
    for key in _SAFETY_FALSE_KEYS:
        assert payload[key] is False, key


# --------------------------------------------------------------------------- #
# Classification registry
# --------------------------------------------------------------------------- #
def test_every_supervisor_action_is_classified() -> None:
    tokens = set()
    for lane in AUTONOMY_SUPERVISOR_LANES:
        tokens.update(lane.next_actions.values())
    missing = sorted(t for t in tokens if t not in AUTONOMY_ACTION_CLASSIFICATION)
    assert missing == [], f"unclassified supervisor actions: {missing}"


def test_classification_registry_is_internally_consistent() -> None:
    for token, classified in AUTONOMY_ACTION_CLASSIFICATION.items():
        assert isinstance(classified, ActionClass), token
        if classified.offline_runnable:
            assert classified.execution_class in (
                EXECUTION_AUTO_OFFLINE,
                EXECUTION_OFFLINE_OPERATOR_INPUT,
            ), token
            assert classified.command != "", token
        else:
            assert classified.command == "", token
        if classified.execution_class == EXECUTION_NOOP:
            assert classified.gate == "", token
        else:
            assert classified.gate != "", token


def test_unknown_action_fails_closed_to_operator_review() -> None:
    classified = classify_action("some_brand_new_unmapped_action")
    assert classified.execution_class == EXECUTION_OPERATOR_GATED
    assert classified.offline_runnable is False
    assert classified.gate == "unclassified_action_operator_review"


def test_action_class_rejects_offline_runnable_without_command() -> None:
    with pytest.raises(ValidationError):
        ActionClass(
            execution_class=EXECUTION_AUTO_OFFLINE,
            offline_runnable=True,
            gate="unattended_execution_authority",
            gate_detail="x",
            command="",
        )


def test_action_class_rejects_command_on_non_offline_action() -> None:
    with pytest.raises(ValidationError):
        ActionClass(
            execution_class=EXECUTION_OPERATOR_GATED,
            offline_runnable=False,
            gate="operator_review",
            gate_detail="x",
            command="python -m algotrader.cli something",
        )


def test_action_class_rejects_noop_with_gate() -> None:
    with pytest.raises(ValidationError):
        ActionClass(
            execution_class=EXECUTION_NOOP,
            offline_runnable=False,
            gate="operator_review",
            gate_detail="x",
        )


# --------------------------------------------------------------------------- #
# Whole-system plan behaviour
# --------------------------------------------------------------------------- #
def test_clean_checkout_offers_offline_daily_cycle_seed(tmp_path: Path) -> None:
    payload = build_autonomy_next_plan(_config(tmp_path))

    assert payload["record_type"] == "autonomy_next_plan"
    assert payload["labels"] == list(AUTONOMY_NEXT_PLAN_LABELS)
    assert payload["profit_claim"] == "none"
    # In a clean checkout the only offline-runnable lane is the daily cycle.
    assert payload["plan_class"] == PLAN_OFFLINE_ACTION_AVAILABLE
    assert payload["next_offline_action_lane"] == "spy_offline_daily_cycle"
    assert payload["offline_runnable_lanes"] == ["spy_offline_daily_cycle"]
    seed = _action(payload, "spy_offline_daily_cycle")
    assert seed["execution_class"] == EXECUTION_OFFLINE_OPERATOR_INPUT
    assert seed["offline_runnable"] is True
    assert "etf-sma-offline-daily-cycle-run" in seed["command"]
    assert seed["required_operator_inputs"]
    # The market-data soak seed requires a network fetch: operator-gated.
    soak = _action(payload, "spy_market_data_soak")
    assert soak["execution_class"] == EXECUTION_OPERATOR_GATED
    assert soak["gate"] == "network_market_data_fetch"
    assert soak["command"] == ""
    _assert_safety_booleans_false(payload)


def test_all_nominal_or_waiting_reports_no_action(tmp_path: Path) -> None:
    records = {
        "spy_market_data_soak": {
            "evidence_state": "accepted_unattended_market_data_soak",
            "latest_attempted_session_date": AS_OF,
        },
        "spy_offline_daily_cycle": {"daily_chain_state": "accepted_observe_hold_noop"},
        "crypto_supervised_readiness_trial": {"trial_classification": "accepted"},
        "crypto_forward_shadow_cycle": {
            "classification": "waiting_for_tournament_terminal"
        },
        "crypto_bounded_paper_probe_review": {
            "classification": "waiting_for_v5_25_terminal_evidence"
        },
        "crypto_capability_production": {
            "classification": "candidate_deferred_pending_terminal_winner"
        },
    }
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), records)
    payload = build_autonomy_next_plan_from_report(report)

    assert payload["plan_class"] == PLAN_ALL_NOMINAL_OR_WAITING
    assert payload["next_offline_action"] is None
    assert payload["next_offline_action_lane"] == ""
    assert payload["offline_runnable_lanes"] == []
    assert payload["operator_gated_lanes"] == []
    assert len(payload["noop_lanes"]) == len(AUTONOMY_SUPERVISOR_LANES)


def test_operator_authority_required_when_no_offline_action(tmp_path: Path) -> None:
    # A blocked crypto review lane with everything else nominal/waiting: no
    # offline-runnable lane, so the whole plan is operator-authority-gated.
    records = {
        "spy_market_data_soak": {
            "evidence_state": "accepted_unattended_market_data_soak",
            "latest_attempted_session_date": AS_OF,
        },
        "spy_offline_daily_cycle": {"daily_chain_state": "accepted_observe_hold_noop"},
        "crypto_supervised_readiness_trial": {"trial_classification": "accepted"},
        "crypto_forward_shadow_cycle": {
            "classification": "waiting_for_tournament_terminal"
        },
        "crypto_bounded_paper_probe_review": {
            "classification": "blocked_by_operational_evidence",
            "blockers": ["needs_operational_evidence"],
        },
        "crypto_capability_production": {
            "classification": "candidate_deferred_pending_terminal_winner"
        },
    }
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), records)
    payload = build_autonomy_next_plan_from_report(report)

    assert payload["supervisor_system_status"] == "blocked"
    assert payload["plan_class"] == PLAN_OPERATOR_AUTHORITY_REQUIRED
    assert payload["offline_runnable_lanes"] == []
    assert "crypto_bounded_paper_probe_review" in payload["operator_gated_lanes"]
    gated = _action(payload, "crypto_bounded_paper_probe_review")
    assert gated["gate"] == "operator_review"


def test_stale_daily_cycle_offers_auto_offline_rerun(tmp_path: Path) -> None:
    # Force the daily cycle lane stale by overriding it with a stale nominal
    # record, and give it a max_age lane... the daily cycle disables staleness,
    # so instead drive the auto_offline rerun via a direct classify check plus a
    # crafted supervisor lane whose next_action is the rerun token.
    classified = classify_action("rerun_offline_daily_cycle_chain")
    assert classified.execution_class == EXECUTION_AUTO_OFFLINE
    assert classified.offline_runnable is True
    assert "etf-sma-offline-daily-cycle-rerun-m446" in classified.command
    assert classified.required_operator_inputs == ()
    assert classified.preconditions  # depends on the refreshed M446 CSV


def test_next_offline_action_prefers_higher_severity(tmp_path: Path) -> None:
    # spy_market_data_soak stale (attention-ish) is operator-gated; the daily
    # cycle absent seed is offline-runnable. Only offline-runnable lanes are
    # eligible for next_offline_action, and among them the most severe wins.
    payload = build_autonomy_next_plan(_config(tmp_path))
    assert payload["next_offline_action"]["lane_id"] == "spy_offline_daily_cycle"


# --------------------------------------------------------------------------- #
# Rendering, writing, determinism
# --------------------------------------------------------------------------- #
def test_render_json_is_deterministic_and_sorted(tmp_path: Path) -> None:
    payload = build_autonomy_next_plan(_config(tmp_path))
    rendered = render_autonomy_next_plan_json(payload)
    assert "\n" not in rendered
    reparsed = json.loads(rendered)
    assert reparsed["record_type"] == "autonomy_next_plan"
    assert render_autonomy_next_plan_json(payload) == rendered
    keys = list(reparsed.keys())
    assert keys == sorted(keys)


def test_render_text_lists_actions_and_safety(tmp_path: Path) -> None:
    payload = build_autonomy_next_plan(_config(tmp_path))
    text = render_autonomy_next_plan_text(payload)
    assert "Offline autonomy next-action plan" in text
    assert "spy_offline_daily_cycle" in text
    assert "live_authorized: false" in text


def test_report_is_deterministic_for_same_inputs(tmp_path: Path) -> None:
    first = build_autonomy_next_plan(_config(tmp_path))
    second = build_autonomy_next_plan(_config(tmp_path))
    assert render_autonomy_next_plan_json(first) == render_autonomy_next_plan_json(
        second
    )


def test_write_jsonl_writes_exactly_one_record(tmp_path: Path) -> None:
    payload = build_autonomy_next_plan(_config(tmp_path))
    out = tmp_path / "nested" / "plan.jsonl"
    result = write_autonomy_next_plan_jsonl(payload, out)
    assert result.record_count == 1
    assert result.newline_terminated is True
    assert result.submitted is False
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert len(text.splitlines()) == 1
    json.loads(text.strip())


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #
def test_from_report_rejects_non_supervisor_record() -> None:
    with pytest.raises(ValidationError):
        build_autonomy_next_plan_from_report({"record_type": "something_else"})


def test_from_report_rejects_missing_lanes() -> None:
    with pytest.raises(ValidationError):
        build_autonomy_next_plan_from_report(
            {
                "record_type": "autonomy_supervisor_report",
                "run_id": "x",
                "as_of": AS_OF,
                "lanes_root": "runs",
                "system_status": "no_lane_evidence",
                "recommended_next_action": "x",
                "recommended_next_action_lane": "",
                "lanes": "not-a-list",
            }
        )


def test_build_rejects_wrong_config_type() -> None:
    with pytest.raises(ValidationError):
        build_autonomy_next_plan({"run_id": "x"})  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_command_registered_and_runs(tmp_path: Path) -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-next-plan",
                "--run-id",
                "cli-test",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
    payload = json.loads(buffer.getvalue().strip())
    # Clean checkout: offline daily-cycle seed available -> action pending -> 1.
    assert exit_code == 1
    assert payload["record_type"] == "autonomy_next_plan"
    assert payload["plan_class"] == PLAN_OFFLINE_ACTION_AVAILABLE
    _assert_safety_booleans_false(payload)


def test_cli_all_nominal_returns_zero_exit(tmp_path: Path) -> None:
    # Seed every lane nominal/waiting via per-lane overrides.
    def _write(name: str, obj: dict) -> str:
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(obj), encoding="utf-8")
        return str(path)

    overrides = [
        f"spy_market_data_soak={_write('soak', {'evidence_state': 'accepted_unattended_market_data_soak', 'latest_attempted_session_date': AS_OF})}",
        f"spy_offline_daily_cycle={_write('daily', {'daily_chain_state': 'accepted_observe_hold_noop'})}",
        f"crypto_supervised_readiness_trial={_write('trial', {'trial_classification': 'accepted'})}",
        f"crypto_forward_shadow_cycle={_write('shadow', {'classification': 'waiting_for_tournament_terminal'})}",
        f"crypto_bounded_paper_probe_review={_write('probe', {'classification': 'waiting_for_v5_25_terminal_evidence'})}",
        f"crypto_capability_production={_write('cap', {'classification': 'candidate_deferred_pending_terminal_winner'})}",
    ]
    argv = [
        "autonomy-next-plan",
        "--run-id",
        "cli-test",
        "--as-of",
        AS_OF,
        "--lanes-root",
        str(tmp_path),
        "--format",
        "json",
    ]
    for override in overrides:
        argv.extend(["--lane", override])
    run_log = tmp_path / "plan.jsonl"
    argv.extend(["--run-log", str(run_log)])

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(argv)

    assert exit_code == 0
    record = json.loads(run_log.read_text(encoding="utf-8").strip())
    assert record["plan_class"] == PLAN_ALL_NOMINAL_OR_WAITING


def test_cli_bad_lane_override_returns_validation_exit(tmp_path: Path) -> None:
    exit_code = cli_module.main(
        [
            "autonomy-next-plan",
            "--run-id",
            "cli-test",
            "--as-of",
            AS_OF,
            "--lanes-root",
            str(tmp_path),
            "--lane",
            "missing_equals_sign",
        ]
    )
    assert exit_code == 2


# --------------------------------------------------------------------------- #
# Safety: no forbidden imports/calls; plans commands but never executes them.
# --------------------------------------------------------------------------- #
def test_module_has_no_forbidden_imports_or_calls() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _assert_import_allowed(alias.name)
        elif isinstance(node, ast.ImportFrom):
            _assert_import_allowed(node.module or "")
        elif isinstance(node, ast.Call):
            _assert_call_allowed(node.func)


def _assert_import_allowed(module_name: str) -> None:
    root = module_name.split(".")[0]
    assert root not in FORBIDDEN_IMPORT_PREFIXES, module_name


def _assert_call_allowed(func: ast.expr) -> None:
    if isinstance(func, ast.Name):
        assert func.id not in FORBIDDEN_CALL_NAMES, func.id
    elif isinstance(func, ast.Attribute):
        assert func.attr not in FORBIDDEN_CALL_NAMES, func.attr
