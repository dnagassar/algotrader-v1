from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import algotrader.cli as cli_module
import algotrader.execution.autonomy_offline_executor as executor_module
from algotrader.errors import ValidationError
from algotrader.execution.autonomy_supervisor import (
    AUTONOMY_SUPERVISOR_LANES,
    AutonomySupervisorConfig,
    build_autonomy_supervisor_report_from_records,
)
from algotrader.execution.autonomy_next_plan import build_autonomy_next_plan_from_report
from algotrader.execution.autonomy_offline_executor import (
    AUTONOMY_EXECUTOR_ALLOWLIST,
    AUTONOMY_EXECUTOR_LABELS,
    CREDENTIAL_PREFLIGHT_ENV_KEYS,
    SKIP_NOT_OFFLINE_RUNNABLE,
    SKIP_REQUIRES_OPERATOR_INPUT,
    build_offline_execution_ledger,
    execution_preflight,
    render_offline_execution_ledger_json,
    render_offline_execution_ledger_text,
    write_offline_execution_ledger_jsonl,
)


MODULE_PATH = Path("src/algotrader/execution/autonomy_offline_executor.py")
AS_OF = "2026-07-24T00:00:00Z"

# This module must execute subprocesses, so os/sys/subprocess are allowed; every
# network/broker/credential-SDK surface is still forbidden.
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "ssl",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "liquidate",
    "load_config",
    "replace_order",
    "submit_order",
    "submit_order_request",
    "urlopen",
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
    kwargs = {"run_id": "exec-test", "as_of": AS_OF, "lanes_root": tmp_path}
    kwargs.update(overrides)
    return AutonomySupervisorConfig(**kwargs)


def _stale_rerun_plan(config: AutonomySupervisorConfig) -> dict:
    """A plan whose daily-cycle lane recommends the allowlisted rerun."""
    report = build_autonomy_supervisor_report_from_records(config, {})
    for lane in report["lanes"]:
        if lane["lane_id"] == "spy_offline_daily_cycle":
            lane["normalized_state"] = "stale"
            lane["next_action"] = "rerun_offline_daily_cycle_chain"
    return build_autonomy_next_plan_from_report(report)


def _assert_safety_booleans_false(payload: dict) -> None:
    for key in _SAFETY_FALSE_KEYS:
        assert payload[key] is False, key


# --------------------------------------------------------------------------- #
# Allowlist and preflight
# --------------------------------------------------------------------------- #
def test_allowlist_is_the_verified_offline_command_only() -> None:
    assert set(AUTONOMY_EXECUTOR_ALLOWLIST) == {"rerun_offline_daily_cycle_chain"}
    assert AUTONOMY_EXECUTOR_ALLOWLIST["rerun_offline_daily_cycle_chain"] == (
        "etf-sma-offline-daily-cycle-rerun-m446",
    )
    # The seed command that requires operator input must never be allowlisted.
    for argv in AUTONOMY_EXECUTOR_ALLOWLIST.values():
        assert "etf-sma-offline-daily-cycle-run" not in argv


def test_allowlisted_actions_are_unreachable_from_current_lane_registry() -> None:
    emitted_actions = {
        action
        for lane in AUTONOMY_SUPERVISOR_LANES
        for action in lane.next_actions.values()
    }
    reachable_allowlisted = sorted(
        emitted_actions.intersection(AUTONOMY_EXECUTOR_ALLOWLIST)
    )
    assert reachable_allowlisted == []


def test_preflight_passes_on_clean_env() -> None:
    ok, reasons = execution_preflight({})
    assert ok is True
    assert reasons == []


def test_preflight_refuses_on_loaded_profile_or_credential() -> None:
    ok, reasons = execution_preflight(
        {"APP_PROFILE": "paper", "ALPACA_API_KEY": "secretvalue"}
    )
    assert ok is False
    assert any("APP_PROFILE" in r for r in reasons)
    assert any("ALPACA_API_KEY" in r for r in reasons)
    # The credential value is never echoed into the reasons.
    assert all("secretvalue" not in r for r in reasons)


def test_preflight_ignores_live_only_when_blank() -> None:
    ok, _ = execution_preflight({"APP_PROFILE": "", "ALPACA_API_KEY": "  "})
    assert ok is True


# --------------------------------------------------------------------------- #
# Dry-run is inert
# --------------------------------------------------------------------------- #
def test_dry_run_executes_nothing_even_when_eligible(tmp_path: Path) -> None:
    plan = _stale_rerun_plan(_config(tmp_path))

    def _forbidden_runner(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("dry run must not execute anything")

    ledger = build_offline_execution_ledger(
        _config(tmp_path),
        apply=False,
        plan_report=plan,
        environ={},
        runner=_forbidden_runner,
    )
    assert ledger["dry_run"] is True
    assert ledger["apply"] is False
    assert ledger["eligible_count"] == 1
    assert ledger["execution_count"] == 0
    assert ledger["executed_actions"] == []
    assert ledger["labels"] == list(AUTONOMY_EXECUTOR_LABELS)
    _assert_safety_booleans_false(ledger)


def test_clean_checkout_seed_is_skipped_not_eligible(tmp_path: Path) -> None:
    ledger = build_offline_execution_ledger(_config(tmp_path), apply=False, environ={})
    assert ledger["eligible_count"] == 0
    daily = [
        s
        for s in ledger["skipped_actions"]
        if s["lane_id"] == "spy_offline_daily_cycle"
    ]
    assert daily and daily[0]["reason"] == SKIP_REQUIRES_OPERATOR_INPUT
    gated = [
        s
        for s in ledger["skipped_actions"]
        if s["lane_id"] == "spy_market_data_soak"
    ]
    assert gated and gated[0]["reason"] == SKIP_NOT_OFFLINE_RUNNABLE


# --------------------------------------------------------------------------- #
# Apply runs only the allowlisted argv
# --------------------------------------------------------------------------- #
def test_apply_executes_only_allowlisted_argv(tmp_path: Path) -> None:
    plan = _stale_rerun_plan(_config(tmp_path))
    calls = []

    def _runner(argv, environ):
        calls.append(argv)
        return {"exit_code": 0, "stdout": "ok", "stderr": "", "timed_out": False}

    ledger = build_offline_execution_ledger(
        _config(tmp_path),
        apply=True,
        plan_report=plan,
        environ={},
        runner=_runner,
    )
    assert calls == [("etf-sma-offline-daily-cycle-rerun-m446",)]
    assert ledger["execution_count"] == 1
    assert ledger["all_executions_succeeded"] is True
    executed = ledger["executed_actions"][0]
    assert executed["exit_code"] == 0
    assert executed["succeeded"] is True
    assert executed["lane_id"] == "spy_offline_daily_cycle"
    _assert_safety_booleans_false(ledger)


def test_apply_records_failed_execution(tmp_path: Path) -> None:
    plan = _stale_rerun_plan(_config(tmp_path))

    def _runner(argv, environ):
        return {"exit_code": 3, "stdout": "", "stderr": "boom", "timed_out": False}

    ledger = build_offline_execution_ledger(
        _config(tmp_path),
        apply=True,
        plan_report=plan,
        environ={},
        runner=_runner,
    )
    assert ledger["execution_count"] == 1
    assert ledger["all_executions_succeeded"] is False
    assert ledger["executed_actions"][0]["succeeded"] is False


def test_apply_refuses_when_preflight_fails(tmp_path: Path) -> None:
    plan = _stale_rerun_plan(_config(tmp_path))

    def _forbidden_runner(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("must not execute when preflight fails")

    ledger = build_offline_execution_ledger(
        _config(tmp_path),
        apply=True,
        plan_report=plan,
        environ={"APP_PROFILE": "live"},
        runner=_forbidden_runner,
    )
    assert ledger["preflight_ok"] is False
    assert ledger["execution_count"] == 0
    assert ledger["execution_refused_reason"] == "preflight_failed"


# --------------------------------------------------------------------------- #
# Real runner sanitizes the child environment
# --------------------------------------------------------------------------- #
def test_real_runner_strips_credentials_and_sets_pythonpath(
    tmp_path: Path, monkeypatch
) -> None:
    captured = {}

    class _Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs.get("env")
        captured["cwd"] = kwargs.get("cwd")
        return _Completed()

    monkeypatch.setattr(executor_module.subprocess, "run", _fake_run)
    dirty_env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "secret",
        "APCA_API_SECRET_KEY": "secret2",
        "PATH": "/usr/bin",
    }
    result = executor_module._run_subprocess(
        ("etf-sma-offline-daily-cycle-rerun-m446",), dirty_env
    )
    assert result["exit_code"] == 0
    child_env = captured["env"]
    # Every credential/profile key is stripped from the child environment.
    for key in (*CREDENTIAL_PREFLIGHT_ENV_KEYS, "APP_PROFILE"):
        assert key not in child_env
    assert child_env["PATH"] == "/usr/bin"
    assert child_env["PYTHONPATH"].endswith("src")
    # The command targets the algotrader CLI with exactly the allowlisted argv.
    assert child_env is not dirty_env
    assert captured["command"][1:] == [
        "-m",
        "algotrader.cli",
        "etf-sma-offline-daily-cycle-rerun-m446",
    ]


def test_execute_refuses_argv_not_matching_allowlist(tmp_path: Path) -> None:
    tampered = executor_module._EligibleAction(
        lane_id="spy_offline_daily_cycle",
        recommended_action="rerun_offline_daily_cycle_chain",
        argv=("etf-sma-offline-daily-cycle-run", "--danger"),
    )
    with pytest.raises(ValidationError):
        executor_module._execute(tampered, lambda argv, env: {"exit_code": 0}, {})


# --------------------------------------------------------------------------- #
# Rendering / writing / validation
# --------------------------------------------------------------------------- #
def test_render_json_is_deterministic_and_sorted(tmp_path: Path) -> None:
    ledger = build_offline_execution_ledger(_config(tmp_path), apply=False, environ={})
    rendered = render_offline_execution_ledger_json(ledger)
    assert "\n" not in rendered
    reparsed = json.loads(rendered)
    assert list(reparsed.keys()) == sorted(reparsed.keys())
    assert reparsed["record_type"] == "autonomy_offline_execution_ledger"


def test_render_text_reports_apply_and_safety(tmp_path: Path) -> None:
    ledger = build_offline_execution_ledger(_config(tmp_path), apply=False, environ={})
    text = render_offline_execution_ledger_text(ledger)
    assert "Gated offline autonomy execution ledger" in text
    assert "live_authorized: false" in text


def test_write_jsonl_writes_exactly_one_record(tmp_path: Path) -> None:
    ledger = build_offline_execution_ledger(_config(tmp_path), apply=False, environ={})
    out = tmp_path / "nested" / "ledger.jsonl"
    result = write_offline_execution_ledger_jsonl(ledger, out)
    assert result["record_count"] == 1
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n") and len(text.splitlines()) == 1


def test_rejects_wrong_config_type() -> None:
    with pytest.raises(ValidationError):
        build_offline_execution_ledger({"run_id": "x"})  # type: ignore[arg-type]


def test_rejects_non_apply_bool(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_offline_execution_ledger(_config(tmp_path), apply="yes")  # type: ignore[arg-type]


def test_rejects_bad_plan_report(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_offline_execution_ledger(
            _config(tmp_path),
            apply=False,
            plan_report={"record_type": "something_else", "actions": []},
        )


def test_rejects_supervisor_report_with_unrankable_lane_state(tmp_path: Path) -> None:
    # V5.38a: the executor's external-plan seam re-plans a supervisor report, so
    # it must inherit the planner's state-vocabulary guard rather than build a
    # ledger from a plan that claims an offline action and names none.
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), {})
    for lane in report["lanes"]:
        if lane["lane_id"] == "spy_offline_daily_cycle":
            lane["normalized_state"] = "healthy"
            lane["next_action"] = "run_offline_daily_cycle_chain_to_seed_evidence"

    with pytest.raises(ValidationError):
        build_offline_execution_ledger(
            _config(tmp_path), apply=False, plan_report=report
        )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_dry_run_default_executes_nothing(tmp_path: Path) -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-apply-plan",
                "--run-id",
                "cli",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
    payload = json.loads(buffer.getvalue().strip())
    assert payload["dry_run"] is True
    assert payload["execution_count"] == 0
    # Clean checkout: nothing eligible -> exit 0.
    assert exit_code == 0
    _assert_safety_booleans_false(payload)


def test_cli_apply_on_clean_checkout_is_safe(tmp_path: Path) -> None:
    run_log = tmp_path / "ledger.jsonl"
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-apply-plan",
                "--run-id",
                "cli",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--apply",
                "--run-log",
                str(run_log),
                "--format",
                "json",
            ]
        )
    assert exit_code == 0
    record = json.loads(run_log.read_text(encoding="utf-8").strip())
    assert record["apply"] is True
    assert record["execution_count"] == 0


def test_cli_bad_lane_override_returns_validation_exit(tmp_path: Path) -> None:
    exit_code = cli_module.main(
        [
            "autonomy-apply-plan",
            "--run-id",
            "cli",
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
# Safety: no forbidden imports/calls
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
