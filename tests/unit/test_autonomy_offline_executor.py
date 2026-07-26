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
    ALL_LANES_ABSENT_ACTION,
    AUTONOMY_SUPERVISOR_LANES,
    AutonomySupervisorConfig,
    build_autonomy_supervisor_report_from_records,
)
from algotrader.execution.autonomy_next_plan import (
    AUTONOMY_ACTION_CLASSIFICATION,
    EXECUTION_AUTO_OFFLINE,
    build_autonomy_next_plan_from_report,
)
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
REPO_ROOT = Path(__file__).resolve().parents[2]
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
    kwargs = {"run_id": "exec-test", "as_of": AS_OF, "lanes_root": Path("runs")}
    kwargs.update(overrides)
    return AutonomySupervisorConfig(**kwargs)


def _absent_replay_plan(config: AutonomySupervisorConfig) -> dict:
    report = build_autonomy_supervisor_report_from_records(config, {})
    return build_autonomy_next_plan_from_report(report)


def _nominal_plan(config: AutonomySupervisorConfig) -> dict:
    report = build_autonomy_supervisor_report_from_records(
        config,
        {
            "spy_market_data_soak": {
                "evidence_state": "accepted_unattended_market_data_soak",
                "latest_attempted_session_date": AS_OF,
            },
            "spy_offline_daily_cycle": {
                "daily_chain_state": "accepted_observe_hold_noop"
            },
            "crypto_supervised_readiness_trial": {
                "trial_classification": "accepted"
            },
            "crypto_forward_shadow_cycle": {
                "classification": "waiting_for_tournament_terminal"
            },
            "crypto_bounded_paper_probe_review": {
                "classification": "waiting_for_v5_25_terminal_evidence"
            },
            "crypto_capability_production": {
                "classification": "candidate_deferred_pending_terminal_winner"
            },
        },
    )
    return build_autonomy_next_plan_from_report(report)


def _install_canonical_plan(
    monkeypatch: pytest.MonkeyPatch,
    plan: dict,
) -> None:
    monkeypatch.setattr(
        executor_module,
        "build_autonomy_next_plan",
        lambda config: plan,
    )


def _assert_safety_booleans_false(payload: dict) -> None:
    for key in _SAFETY_FALSE_KEYS:
        assert payload[key] is False, key


# --------------------------------------------------------------------------- #
# Allowlist and preflight
# --------------------------------------------------------------------------- #
def test_allowlist_is_exact_reachable_auto_offline_closure() -> None:
    producer_tokens = {
        token
        for lane in AUTONOMY_SUPERVISOR_LANES
        for token in lane.next_actions.values()
    } | {ALL_LANES_ABSENT_ACTION}
    auto_tokens = {
        token
        for token, classified in AUTONOMY_ACTION_CLASSIFICATION.items()
        if classified.execution_class == EXECUTION_AUTO_OFFLINE
    }
    assert set(AUTONOMY_EXECUTOR_ALLOWLIST) == auto_tokens
    assert set(AUTONOMY_EXECUTOR_ALLOWLIST) <= producer_tokens
    assert set(AUTONOMY_EXECUTOR_ALLOWLIST) == {
        "run_supervised_readiness_trial_to_seed_r1_evidence",
        "rerun_supervised_readiness_trial",
    }
    assert set(AUTONOMY_EXECUTOR_ALLOWLIST.values()) == {
        ("crypto-readiness-replay",)
    }
    assert "rerun_offline_daily_cycle_chain" not in AUTONOMY_EXECUTOR_ALLOWLIST


def test_allowlisted_actions_are_reachable_from_current_lane_registry() -> None:
    emitted_actions = {
        action
        for lane in AUTONOMY_SUPERVISOR_LANES
        for action in lane.next_actions.values()
    }
    reachable_allowlisted = sorted(
        emitted_actions.intersection(AUTONOMY_EXECUTOR_ALLOWLIST)
    )
    assert reachable_allowlisted == sorted(AUTONOMY_EXECUTOR_ALLOWLIST)


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
def test_dry_run_executes_nothing_even_when_eligible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _absent_replay_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)

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
    assert ledger["eligible_actions"] == [
        {
            "lane_id": "crypto_supervised_readiness_trial",
            "recommended_action": (
                "run_supervised_readiness_trial_to_seed_r1_evidence"
            ),
            "argv": ["crypto-readiness-replay"],
        }
    ]
    assert ledger["execution_count"] == 0
    assert ledger["executed_actions"] == []
    assert ledger["labels"] == list(AUTONOMY_EXECUTOR_LABELS)
    # V5.44: zero executions is not a vacuous success claim.
    assert ledger["all_executions_succeeded"] is None
    _assert_safety_booleans_false(ledger)


def test_absent_readiness_is_eligible_and_spy_seed_is_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _absent_replay_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)
    ledger = build_offline_execution_ledger(_config(tmp_path), apply=False, environ={})
    assert ledger["eligible_count"] == 1
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
# V5.44: zero executions is tri-state (True/False/None), never vacuously true
# --------------------------------------------------------------------------- #
def test_apply_with_no_auto_action_reports_not_applicable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Genuine no-op: apply=True, preflight passes, nothing eligible.
    plan = _nominal_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)

    def _forbidden_runner(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("nothing eligible must not execute")

    ledger = build_offline_execution_ledger(
        _config(tmp_path), apply=True, environ={}, runner=_forbidden_runner
    )
    assert ledger["eligible_count"] == 0
    assert ledger["execution_count"] == 0
    assert ledger["execution_refused_reason"] == ""
    assert ledger["preflight_ok"] is True
    assert ledger["all_executions_succeeded"] is None


def test_preflight_refusal_reports_not_applicable_not_true(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _absent_replay_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)

    def _forbidden_runner(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("must not execute when preflight fails")

    ledger = build_offline_execution_ledger(
        _config(tmp_path),
        apply=True,
        plan_report=plan,
        environ={"APP_PROFILE": "live"},
        runner=_forbidden_runner,
    )
    assert ledger["execution_count"] == 0
    assert ledger["execution_refused_reason"] == "preflight_failed"
    # A safety refusal must never read as a vacuous success.
    assert ledger["all_executions_succeeded"] is None


def test_execution_count_zero_iff_all_succeeded_is_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _absent_replay_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)

    def _runner(argv, environ):
        return {"exit_code": 0, "stdout": "", "stderr": "", "timed_out": False}

    for apply_flag, environ in (
        (False, {}),
        (True, {"APP_PROFILE": "live"}),
    ):
        ledger = build_offline_execution_ledger(
            _config(tmp_path),
            apply=apply_flag,
            plan_report=plan,
            environ=environ,
            runner=_runner if apply_flag else None,
        )
        assert ledger["execution_count"] == 0
        assert ledger["all_executions_succeeded"] is None

    ledger = build_offline_execution_ledger(
        _config(tmp_path), apply=True, plan_report=plan, environ={}, runner=_runner
    )
    assert ledger["execution_count"] > 0
    assert ledger["all_executions_succeeded"] is not None
    assert isinstance(ledger["all_executions_succeeded"], bool)


# --------------------------------------------------------------------------- #
# Apply runs only the allowlisted argv
# --------------------------------------------------------------------------- #
def test_apply_executes_only_allowlisted_argv_with_sanitized_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _absent_replay_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)
    calls = []

    def _runner(argv, environ):
        calls.append((argv, environ))
        return {"exit_code": 0, "stdout": "ok", "stderr": "", "timed_out": False}

    ledger = build_offline_execution_ledger(
        _config(tmp_path),
        apply=True,
        plan_report=plan,
        environ={"PATH": "safe", "APP_PROFILE": ""},
        runner=_runner,
    )
    assert len(calls) == 1
    assert calls[0][0] == ("crypto-readiness-replay",)
    assert calls[0][1]["PATH"] == "safe"
    assert calls[0][1]["PYTHONPATH"] == str(REPO_ROOT / "src")
    for key in (*CREDENTIAL_PREFLIGHT_ENV_KEYS, "APP_PROFILE"):
        assert key not in calls[0][1]
    assert ledger["execution_count"] == 1
    assert ledger["all_executions_succeeded"] is True
    executed = ledger["executed_actions"][0]
    assert executed["exit_code"] == 0
    assert executed["succeeded"] is True
    assert executed["lane_id"] == "crypto_supervised_readiness_trial"
    _assert_safety_booleans_false(ledger)


def test_apply_records_failed_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _absent_replay_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)

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


def test_apply_refuses_when_preflight_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _absent_replay_plan(_config(tmp_path))
    _install_canonical_plan(monkeypatch, plan)

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
def test_real_runner_uses_prepared_sanitized_environment_and_canonical_cwd(
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
    child_input = executor_module._sanitized_child_environment(dirty_env, REPO_ROOT)
    result = executor_module._run_subprocess(("crypto-readiness-replay",), child_input)
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
        "crypto-readiness-replay",
    ]
    assert Path(captured["cwd"]).resolve() == REPO_ROOT.resolve()


def test_execute_refuses_argv_not_matching_allowlist(tmp_path: Path) -> None:
    tampered = executor_module._EligibleAction(
        lane_id="crypto_supervised_readiness_trial",
        recommended_action="run_supervised_readiness_trial_to_seed_r1_evidence",
        argv=("crypto-readiness-replay", "--output-root", "elsewhere"),
    )
    with pytest.raises(ValidationError):
        executor_module._execute(tampered, lambda argv, env: {"exit_code": 0}, {})


# --------------------------------------------------------------------------- #
# Canonical target and supplied-plan/report fail-closed validation
# --------------------------------------------------------------------------- #
def test_executor_rejects_fabricated_plan_fields_before_runner_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    canonical = _absent_replay_plan(config)
    _install_canonical_plan(monkeypatch, canonical)
    calls: list[tuple[str, ...]] = []

    def _runner(argv, environ):
        calls.append(argv)
        return {"exit_code": 0, "stdout": "", "stderr": "", "timed_out": False}

    variants: list[dict] = []
    for field, value in (
        ("run_id", "fabricated"),
        ("lanes_root", str(tmp_path / "other-runs")),
    ):
        variant = json.loads(json.dumps(canonical))
        variant[field] = value
        variants.append(variant)

    for action_field, value in (
        ("artifact_path", str(tmp_path / "packet.json")),
        ("command", "python -m algotrader.cli something-else"),
        ("recommended_action", "rerun_supervised_readiness_trial"),
    ):
        variant = json.loads(json.dumps(canonical))
        action = next(
            item
            for item in variant["actions"]
            if item["lane_id"] == "crypto_supervised_readiness_trial"
        )
        action[action_field] = value
        variants.append(variant)

    for variant in variants:
        with pytest.raises(ValidationError):
            build_offline_execution_ledger(
                config,
                apply=True,
                plan_report=variant,
                environ={},
                runner=_runner,
            )
    assert calls == []


def test_executor_rejects_mismatched_supervisor_report_before_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    canonical = _absent_replay_plan(config)
    _install_canonical_plan(monkeypatch, canonical)
    report = build_autonomy_supervisor_report_from_records(config, {})
    report["run_id"] = "fabricated"
    calls = []

    with pytest.raises(ValidationError, match="match"):
        build_offline_execution_ledger(
            config,
            apply=True,
            plan_report=report,
            environ={},
            runner=lambda argv, environ: calls.append(argv),
        )
    assert calls == []


@pytest.mark.parametrize(
    "config_overrides",
    [
        {"lanes_root": Path("other-runs")},
        {
            "lane_artifact_overrides": {
                "crypto_supervised_readiness_trial": Path("other-packet.json")
            }
        },
    ],
)
def test_executor_rejects_noncanonical_config_before_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_overrides: dict,
) -> None:
    canonical_config = _config(tmp_path)
    canonical = _absent_replay_plan(canonical_config)
    _install_canonical_plan(monkeypatch, canonical)
    calls = []

    with pytest.raises(ValidationError):
        build_offline_execution_ledger(
            _config(tmp_path, **config_overrides),
            apply=True,
            environ={},
            runner=lambda argv, environ: calls.append(argv),
        )
    assert calls == []


def test_executor_rejects_non_repository_cwd_before_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    canonical = _absent_replay_plan(config)
    _install_canonical_plan(monkeypatch, canonical)
    monkeypatch.chdir(tmp_path)
    calls = []

    with pytest.raises(ValidationError, match="cwd"):
        build_offline_execution_ledger(
            config,
            apply=True,
            environ={},
            runner=lambda argv, environ: calls.append(argv),
        )
    assert calls == []


def test_executor_rejects_source_tree_without_git_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    canonical = _absent_replay_plan(config)
    _install_canonical_plan(monkeypatch, canonical)
    fake_root = tmp_path / "fake-repo"
    fake_module = (
        fake_root
        / "src"
        / "algotrader"
        / "execution"
        / "autonomy_offline_executor.py"
    )
    fake_module.parent.mkdir(parents=True)
    fake_module.write_text("# fake", encoding="utf-8")
    cli_path = fake_root / "src" / "algotrader" / "cli.py"
    cli_path.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(executor_module, "__file__", str(fake_module))
    monkeypatch.chdir(fake_root)
    calls = []

    with pytest.raises(ValidationError, match="Git checkout"):
        build_offline_execution_ledger(
            config,
            apply=True,
            environ={},
            runner=lambda argv, environ: calls.append(argv),
        )
    assert calls == []


def test_executor_rejects_symlink_artifact_before_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    canonical = _absent_replay_plan(config)
    _install_canonical_plan(monkeypatch, canonical)
    link = tmp_path / "readiness_packet.json"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self == link or original_is_symlink(self),
    )
    fabricated = json.loads(json.dumps(canonical))
    readiness = next(
        action
        for action in fabricated["actions"]
        if action["lane_id"] == "crypto_supervised_readiness_trial"
    )
    readiness["artifact_path"] = str(link)
    calls = []

    with pytest.raises(ValidationError, match="symlink"):
        build_offline_execution_ledger(
            config,
            apply=True,
            plan_report=fabricated,
            environ={},
            runner=lambda argv, environ: calls.append(argv),
        )
    assert calls == []


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
    # V5.44: zero executions renders distinctly from true/false.
    assert "all_executions_succeeded: not_applicable" in text


def test_render_json_nulls_all_executions_succeeded_at_zero_count(
    tmp_path: Path,
) -> None:
    ledger = build_offline_execution_ledger(_config(tmp_path), apply=False, environ={})
    reparsed = json.loads(render_offline_execution_ledger_json(ledger))
    assert reparsed["execution_count"] == 0
    assert reparsed["all_executions_succeeded"] is None


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
def test_cli_dry_run_default_executes_nothing_from_canonical_root() -> None:
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
                "runs",
                "--format",
                "json",
            ]
        )
    payload = json.loads(buffer.getvalue().strip())
    assert payload["dry_run"] is True
    assert payload["execution_count"] == 0
    assert payload["all_executions_succeeded"] is None
    assert exit_code in (0, 1)
    _assert_safety_booleans_false(payload)


def test_cli_apply_refuses_noncanonical_lanes_root_without_ledger(
    tmp_path: Path,
) -> None:
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
    assert exit_code == 2
    assert not run_log.exists()


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
