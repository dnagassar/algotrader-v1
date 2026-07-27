from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import algotrader.cli as cli_module
import algotrader.execution.autonomy_next_plan as plan_module
from algotrader.errors import ValidationError
from algotrader.execution.autonomy_supervisor import (
    ALL_LANES_ABSENT_ACTION,
    AUTONOMY_SUPERVISOR_LANES,
    AUTONOMY_SUPERVISOR_STATES,
    AutonomySupervisorConfig,
    build_autonomy_supervisor_report,
    build_autonomy_supervisor_report_from_records,
)
from algotrader.execution.autonomy_next_plan import (
    AUTONOMY_ACTION_CLASSIFICATION,
    AUTONOMY_NEXT_PLAN_LABELS,
    EXECUTION_AUTO_OFFLINE,
    EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
    EXECUTION_NOOP,
    EXECUTION_OFFLINE_OPERATOR_INPUT,
    EXECUTION_OPERATOR_GATED,
    PLAN_ALL_NOMINAL_OR_WAITING,
    PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE,
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
REPO_ROOT = Path(__file__).resolve().parents[2]
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
        "lanes_root": Path("runs"),
    }
    kwargs.update(overrides)
    return AutonomySupervisorConfig(**kwargs)


def _plan_from_records(
    tmp_path: Path,
    records: dict[str, object] | None = None,
) -> dict[str, object]:
    report = build_autonomy_supervisor_report_from_records(
        _config(tmp_path),
        records or {},
    )
    return build_autonomy_next_plan_from_report(report)


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
    producer_tokens = {
        token
        for lane in AUTONOMY_SUPERVISOR_LANES
        for token in lane.next_actions.values()
    } | {ALL_LANES_ABSENT_ACTION}
    assert set(AUTONOMY_ACTION_CLASSIFICATION) == producer_tokens


# --------------------------------------------------------------------------- #
# V5.38a: state vocabulary is a hard input contract
# --------------------------------------------------------------------------- #
def _report_with_lane_state(
    tmp_path: Path, lane_id: str, state: str, next_action: str
) -> dict:
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), {})
    for lane in report["lanes"]:
        if lane["lane_id"] == lane_id:
            lane["normalized_state"] = state
            lane["next_action"] = next_action
    return report


def test_out_of_vocabulary_lane_state_is_rejected(tmp_path: Path) -> None:
    # Previously this produced a self-contradictory plan: plan_class
    # offline_action_available with next_offline_action null, because the severity
    # loop could not rank "healthy" while plan_class still counted the lane.
    report = _report_with_lane_state(
        tmp_path,
        "spy_offline_daily_cycle",
        "healthy",
        "run_offline_daily_cycle_chain_to_seed_evidence",
    )

    with pytest.raises(ValidationError):
        build_autonomy_next_plan_from_report(report)


def test_every_supervisor_state_is_accepted(tmp_path: Path) -> None:
    # The guard must reject only genuinely out-of-vocabulary values.
    for state in AUTONOMY_SUPERVISOR_STATES:
        report = _report_with_lane_state(
            tmp_path,
            "spy_offline_daily_cycle",
            state,
            "run_offline_daily_cycle_chain_to_seed_evidence",
        )
        plan = build_autonomy_next_plan_from_report(report)
        assert _action(plan, "spy_offline_daily_cycle")["normalized_state"] == state


def test_planner_severity_order_is_the_supervisor_vocabulary() -> None:
    # A state the supervisor can emit but the planner cannot rank would be
    # silently skipped by selection while still counting toward plan_class.
    assert plan_module._STATE_SEVERITY is AUTONOMY_SUPERVISOR_STATES


def test_plan_class_and_next_offline_action_agree(tmp_path: Path) -> None:
    # plan_class == offline_action_available iff a next offline action exists.
    records: list[dict[str, object] | None] = [
        {},
        {"crypto_supervised_readiness_trial": {"trial_classification": "accepted"}},
        {
            "crypto_bounded_paper_probe_review": {
                "classification": "blocked_by_operational_evidence"
            }
        },
        {
            "crypto_forward_shadow_cycle": {
                "classification": "waiting_for_tournament_terminal"
            },
            "crypto_capability_production": {
                "classification": "candidate_deferred_pending_terminal_winner"
            },
        },
        {"spy_offline_daily_cycle": {"daily_chain_state": "review_only"}},
    ]
    for lane_records in records:
        plan = build_autonomy_next_plan_from_report(
            build_autonomy_supervisor_report_from_records(
                _config(tmp_path), lane_records or {}
            )
        )
        offline_available = plan["plan_class"] == PLAN_OFFLINE_ACTION_AVAILABLE
        assert offline_available is (plan["next_offline_action"] is not None), (
            plan["plan_class"],
            plan["next_offline_action_lane"],
        )
        assert offline_available is (plan["next_offline_action_lane"] != "")
        if offline_available:
            assert "No offline action is available" not in str(
                plan["operator_summary"]
            )


def test_all_lanes_absent_action_is_classified_operator_gated() -> None:
    # The supervisor emits this aggregate token whenever every lane is absent
    # (V5.37a). It must stay classified and must never become offline-runnable:
    # seeding a lane is operator-driven, so the V5.39 executor gains nothing.
    classified = AUTONOMY_ACTION_CLASSIFICATION[ALL_LANES_ABSENT_ACTION]

    assert classified.offline_runnable is False
    assert classified.execution_class == EXECUTION_OPERATOR_GATED


def test_stale_operator_action_flag_matches_action_classification() -> None:
    # The supervisor declares, per lane, whether staleness is operator-curable
    # only; the planner independently classifies that lane's stale action. If the
    # two drift, the supervisor would report "waiting" for a lane the executor
    # actually could advance (or spin on one it cannot). Keep them in lockstep.
    from algotrader.execution.autonomy_supervisor import STATE_STALE

    for lane in AUTONOMY_SUPERVISOR_LANES:
        if lane.max_age_hours <= 0:
            assert lane.stale_requires_operator_action is False, lane.lane_id
            continue
        stale_action = lane.next_actions[STATE_STALE]
        classified = AUTONOMY_ACTION_CLASSIFICATION[stale_action]
        assert classified.offline_runnable is not lane.stale_requires_operator_action, (
            f"{lane.lane_id}: stale_requires_operator_action="
            f"{lane.stale_requires_operator_action} but {stale_action} is "
            f"offline_runnable={classified.offline_runnable}"
        )


def test_classification_registry_is_internally_consistent() -> None:
    for token, classified in AUTONOMY_ACTION_CLASSIFICATION.items():
        assert isinstance(classified, ActionClass), token
        if classified.offline_runnable:
            assert classified.execution_class in (
                EXECUTION_AUTO_OFFLINE,
                EXECUTION_OFFLINE_OPERATOR_INPUT,
            ), token
            assert classified.command != "", token
        elif classified.execution_class == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY:
            assert classified.command != "", token
        else:
            assert classified.command == "", token
        if classified.execution_class in (EXECUTION_AUTO_OFFLINE, EXECUTION_NOOP):
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
            gate="",
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
def test_all_absent_preserves_aggregate_and_selects_crypto_replay(
    tmp_path: Path,
) -> None:
    payload = _plan_from_records(tmp_path)

    assert payload["record_type"] == "autonomy_next_plan"
    assert payload["labels"] == list(AUTONOMY_NEXT_PLAN_LABELS)
    assert payload["profit_claim"] == "none"
    assert payload["plan_class"] == PLAN_OFFLINE_ACTION_AVAILABLE
    assert payload["supervisor_recommended_action"] == ALL_LANES_ABSENT_ACTION
    assert payload["supervisor_recommended_action_lane"] == ""
    assert payload["next_offline_action_lane"] == "crypto_supervised_readiness_trial"
    assert payload["offline_runnable_lanes"] == [
        "spy_offline_daily_cycle",
        "crypto_supervised_readiness_trial",
    ]
    seed = _action(payload, "spy_offline_daily_cycle")
    assert seed["execution_class"] == EXECUTION_OFFLINE_OPERATOR_INPUT
    assert seed["offline_runnable"] is True
    assert "etf-sma-offline-daily-cycle-run" in seed["command"]
    assert seed["required_operator_inputs"]
    readiness = _action(payload, "crypto_supervised_readiness_trial")
    assert readiness["recommended_action"] == (
        "run_supervised_readiness_trial_to_seed_r1_evidence"
    )
    assert readiness["execution_class"] == EXECUTION_AUTO_OFFLINE
    assert readiness["gate"] == ""
    assert readiness["required_operator_inputs"] == []
    assert readiness["command"] == (
        "python -m algotrader.cli crypto-readiness-replay"
    )
    assert Path(readiness["artifact_path"]).resolve() == (
        REPO_ROOT
        / "runs"
        / "crypto_supervised_readiness_trial"
        / "latest"
        / "readiness_packet.json"
    ).resolve()
    assert payload["next_offline_action"] == readiness
    # The market-data soak seed requires an authorized read-only network fetch.
    soak = _action(payload, "spy_market_data_soak")
    assert soak["execution_class"] == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
    assert soak["gate"] == "network_market_data_fetch"
    assert "autonomy_read_only_network_executor" in soak["command"]
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


def test_readiness_stale_token_is_structurally_bound_but_not_claimed_reachable(
    tmp_path: Path,
) -> None:
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), {})
    readiness = next(
        lane
        for lane in report["lanes"]
        if lane["lane_id"] == "crypto_supervised_readiness_trial"
    )
    readiness["normalized_state"] = "stale"
    readiness["next_action"] = "rerun_supervised_readiness_trial"

    payload = build_autonomy_next_plan_from_report(report)
    action = _action(payload, "crypto_supervised_readiness_trial")
    assert action["execution_class"] == EXECUTION_AUTO_OFFLINE
    assert action["command"] == "python -m algotrader.cli crypto-readiness-replay"
    assert action["gate"] == ""
    assert payload["next_offline_action"] == action
    assert "rerun_offline_daily_cycle_chain" not in AUTONOMY_ACTION_CLASSIFICATION


def test_auto_offline_action_outranks_operator_input(tmp_path: Path) -> None:
    payload = _plan_from_records(tmp_path)
    assert payload["next_offline_action"]["lane_id"] == (
        "crypto_supervised_readiness_trial"
    )
    assert "spy_offline_daily_cycle" in payload["offline_runnable_lanes"]


def test_operator_input_is_fallback_when_no_auto_action(tmp_path: Path) -> None:
    payload = _plan_from_records(
        tmp_path,
        {"crypto_supervised_readiness_trial": {"trial_classification": "accepted"}},
    )
    assert payload["next_offline_action"]["lane_id"] == "spy_offline_daily_cycle"
    assert payload["next_offline_action"]["execution_class"] == (
        EXECUTION_OFFLINE_OPERATOR_INPUT
    )


# --------------------------------------------------------------------------- #
# Rendering, writing, determinism
# --------------------------------------------------------------------------- #
def test_render_json_is_deterministic_and_sorted(tmp_path: Path) -> None:
    payload = _plan_from_records(tmp_path)
    rendered = render_autonomy_next_plan_json(payload)
    assert "\n" not in rendered
    reparsed = json.loads(rendered)
    assert reparsed["record_type"] == "autonomy_next_plan"
    assert render_autonomy_next_plan_json(payload) == rendered
    keys = list(reparsed.keys())
    assert keys == sorted(keys)


def test_render_text_lists_actions_and_safety(tmp_path: Path) -> None:
    payload = _plan_from_records(tmp_path)
    text = render_autonomy_next_plan_text(payload)
    assert "Offline autonomy next-action plan" in text
    assert "spy_offline_daily_cycle" in text
    assert "live_authorized: false" in text


def test_report_is_deterministic_for_same_inputs(tmp_path: Path) -> None:
    first = _plan_from_records(tmp_path)
    second = _plan_from_records(tmp_path)
    assert render_autonomy_next_plan_json(first) == render_autonomy_next_plan_json(
        second
    )


def test_write_jsonl_writes_exactly_one_record(tmp_path: Path) -> None:
    payload = _plan_from_records(tmp_path)
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


def test_planner_rejects_noncanonical_lanes_root(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="canonical repository runs"):
        build_autonomy_next_plan(
            _config(tmp_path, lanes_root=tmp_path / "arbitrary-runs")
        )


def test_planner_rejects_noncanonical_readiness_override(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="readiness lane override"):
        build_autonomy_next_plan(
            _config(
                tmp_path,
                lane_artifact_overrides={
                    "crypto_supervised_readiness_trial": tmp_path / "packet.json"
                },
            )
        )


def test_planner_rejects_report_artifact_and_action_drift(tmp_path: Path) -> None:
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), {})
    readiness = next(
        lane
        for lane in report["lanes"]
        if lane["lane_id"] == "crypto_supervised_readiness_trial"
    )
    readiness["artifact_path"] = str(tmp_path / "readiness_packet.json")
    with pytest.raises(ValidationError, match="artifact_path"):
        build_autonomy_next_plan_from_report(report)

    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), {})
    readiness = next(
        lane
        for lane in report["lanes"]
        if lane["lane_id"] == "crypto_supervised_readiness_trial"
    )
    readiness["next_action"] = "rerun_supervised_readiness_trial"
    with pytest.raises(ValidationError, match="does not match"):
        build_autonomy_next_plan_from_report(report)


def test_planner_rejects_non_repository_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), {})
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError, match="cwd"):
        build_autonomy_next_plan_from_report(report)


def test_planner_rejects_source_tree_without_git_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_root = tmp_path / "fake-repo"
    fake_module = (
        fake_root
        / "src"
        / "algotrader"
        / "execution"
        / "autonomy_next_plan.py"
    )
    fake_module.parent.mkdir(parents=True)
    fake_module.write_text("# fake", encoding="utf-8")
    cli_path = fake_root / "src" / "algotrader" / "cli.py"
    cli_path.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(plan_module, "__file__", str(fake_module))
    monkeypatch.chdir(fake_root)
    with pytest.raises(ValidationError, match="Git checkout"):
        build_autonomy_next_plan_from_report(
            build_autonomy_supervisor_report_from_records(
                AutonomySupervisorConfig(
                    run_id="fake",
                    as_of=AS_OF,
                    lanes_root="runs",
                ),
                {},
            )
        )


def test_planner_rejects_symlink_artifact_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    link = tmp_path / "readiness_packet.json"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self == link or original_is_symlink(self),
    )
    report = build_autonomy_supervisor_report_from_records(_config(tmp_path), {})
    readiness = next(
        lane
        for lane in report["lanes"]
        if lane["lane_id"] == "crypto_supervised_readiness_trial"
    )
    readiness["artifact_path"] = str(link)
    with pytest.raises(ValidationError, match="symlink"):
        build_autonomy_next_plan_from_report(report)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_command_registered_and_runs_from_canonical_root() -> None:
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
                "runs",
                "--format",
                "json",
            ]
        )
    payload = json.loads(buffer.getvalue().strip())
    assert exit_code in (0, 1)
    assert payload["record_type"] == "autonomy_next_plan"
    assert Path(payload["lanes_root"]).resolve() == (REPO_ROOT / "runs").resolve()
    _assert_safety_booleans_false(payload)


def test_cli_rejects_noncanonical_readiness_override(tmp_path: Path) -> None:
    def _write(name: str, obj: dict) -> str:
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(obj), encoding="utf-8")
        return str(path)

    argv = [
        "autonomy-next-plan",
        "--run-id",
        "cli-test",
        "--as-of",
        AS_OF,
        "--lanes-root",
        "runs",
        "--lane",
        (
            "crypto_supervised_readiness_trial="
            f"{_write('trial', {'trial_classification': 'accepted'})}"
        ),
        "--format",
        "json",
    ]
    run_log = tmp_path / "plan.jsonl"
    argv.extend(["--run-log", str(run_log)])

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(argv)

    assert exit_code == 2
    assert not run_log.exists()


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


def test_v551_acceptance_criteria_1_two_way_closure() -> None:
    from algotrader.execution.autonomy_next_plan import (
        AUTONOMY_ACTION_CLASSIFICATION,
        EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
    )
    from algotrader.execution.autonomy_read_only_network_executor import (
        AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST,
    )

    classified = {
        token
        for token, ac in AUTONOMY_ACTION_CLASSIFICATION.items()
        if ac.execution_class == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
    }
    allowlisted = set(AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST.keys())
    assert classified == allowlisted


def test_v551_acceptance_criteria_2_disjointness() -> None:
    from algotrader.execution.autonomy_offline_executor import (
        AUTONOMY_EXECUTOR_ALLOWLIST,
    )
    from algotrader.execution.autonomy_read_only_network_executor import (
        AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST,
    )

    set1 = set(AUTONOMY_EXECUTOR_ALLOWLIST.keys())
    set2 = set(AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST.keys())
    assert set1.isdisjoint(set2)


def test_v551_acceptance_criteria_3_no_false_auto_offline() -> None:
    from algotrader.execution.autonomy_next_plan import (
        _OFFLINE_RUNNABLE_CLASSES,
        AUTONOMY_ACTION_CLASSIFICATION,
        EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
    )

    assert EXECUTION_AUTHORIZED_NETWORK_READ_ONLY not in _OFFLINE_RUNNABLE_CLASSES

    for token, ac in AUTONOMY_ACTION_CLASSIFICATION.items():
        if ac.execution_class == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY:
            assert ac.offline_runnable is False


def test_v551_acceptance_criteria_4_reverse_reachability() -> None:
    from algotrader.execution.autonomy_next_plan import classify_action
    from algotrader.execution.autonomy_read_only_network_executor import (
        AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST,
    )

    ac = classify_action("run_authorized_read_only_market_data_refresh_to_seed_soak")
    assert ac.execution_class == "authorized_network_read_only"
    assert "run_authorized_read_only_market_data_refresh_to_seed_soak" in AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST


def test_v551_acceptance_criteria_5_command_carve_out_is_narrow() -> None:
    from algotrader.execution.autonomy_next_plan import (
        ActionClass,
        EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
        EXECUTION_NOOP,
        EXECUTION_OPERATOR_GATED,
    )

    with pytest.raises(ValidationError, match="only offline-runnable actions may carry a command"):
        ActionClass(
            execution_class=EXECUTION_OPERATOR_GATED,
            offline_runnable=False,
            gate="operator_review",
            gate_detail="test",
            command="python -m invalid",
        )

    with pytest.raises(ValidationError, match="only offline-runnable actions may carry a command"):
        ActionClass(
            execution_class=EXECUTION_NOOP,
            offline_runnable=False,
            gate="",
            gate_detail="test",
            command="python -m invalid",
        )

    valid = ActionClass(
        execution_class=EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
        offline_runnable=False,
        gate="network_market_data_fetch",
        gate_detail="test",
        command="python -m algotrader.execution.autonomy_read_only_network_executor --as-of <ISO8601_UTC> [--apply] --format json",
        required_operator_inputs=(),
    )
    assert valid.execution_class == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
    assert valid.command != ""


# --------------------------------------------------------------------------- #
# V5.51a: the authorized-network class must not vanish from the aggregates
# --------------------------------------------------------------------------- #
def _all_other_lanes_nominal_or_waiting() -> dict[str, object]:
    # Every lane except spy_market_data_soak is nominal/waiting. The soak lane
    # is omitted entirely, so it reads `absent` and its next action is the
    # authorized read-only network refresh.
    return {
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


def test_lone_authorized_network_action_is_not_reported_as_all_nominal(
    tmp_path: Path,
) -> None:
    # Regression: EXECUTION_AUTHORIZED_NETWORK_READ_ONLY is neither
    # offline-runnable nor operator-gated, so before V5.51a a lane carrying it
    # fell out of every bucket and the plan claimed "no next action is pending"
    # while a runnable standing-authority command was sitting on that lane.
    payload = _plan_from_records(tmp_path, _all_other_lanes_nominal_or_waiting())

    soak = _action(payload, "spy_market_data_soak")
    assert soak["normalized_state"] == "absent"
    assert soak["execution_class"] == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
    assert soak["command"] != ""

    assert payload["plan_class"] == PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE
    assert payload["plan_class"] != PLAN_ALL_NOMINAL_OR_WAITING
    assert payload["authorized_network_lanes"] == ["spy_market_data_soak"]
    assert payload["next_authorized_network_action_lane"] == "spy_market_data_soak"
    assert payload["next_authorized_network_action"] == soak
    assert payload["offline_runnable_lanes"] == []
    assert payload["operator_gated_lanes"] == []
    assert "no next action is pending" not in str(payload["operator_summary"])
    assert soak["command"] in str(payload["operator_summary"])
    _assert_safety_booleans_false(payload)


def test_every_execution_class_maps_to_exactly_one_plan_bucket() -> None:
    # Round-6 finding F3: the sampled test below only exercises whatever lane
    # states its fixtures happen to produce, so a class used solely in an
    # unrepresented state could still fall out of every bucket. This is the
    # total invariant -- it reads the class vocabulary itself, so no choice of
    # fixture can hide a gap.
    from algotrader.execution.autonomy_next_plan import (
        _EXECUTION_CLASSES,
        PLAN_BUCKET_BY_EXECUTION_CLASS,
        BUCKET_OFFLINE_RUNNABLE,
        BUCKET_AUTHORIZED_NETWORK,
        BUCKET_OPERATOR_GATED,
        BUCKET_NOOP,
    )

    known_buckets = {
        BUCKET_OFFLINE_RUNNABLE,
        BUCKET_AUTHORIZED_NETWORK,
        BUCKET_OPERATOR_GATED,
        BUCKET_NOOP,
    }
    assert set(PLAN_BUCKET_BY_EXECUTION_CLASS) == set(_EXECUTION_CLASSES), (
        "every execution class must map to exactly one plan bucket"
    )
    for execution_class, bucket in PLAN_BUCKET_BY_EXECUTION_CLASS.items():
        assert bucket in known_buckets, execution_class

    # The classification table may not name a class outside that vocabulary.
    for token, classified in AUTONOMY_ACTION_CLASSIFICATION.items():
        assert classified.execution_class in PLAN_BUCKET_BY_EXECUTION_CLASS, token


def test_every_lane_lands_in_exactly_one_plan_bucket(tmp_path: Path) -> None:
    # The four bucket lists must partition the lanes: a lane in none of them is
    # invisible to every aggregate the operator reads. Sampled companion to the
    # total invariant above -- this proves the builder actually uses the
    # mapping, which the invariant alone cannot show.
    for lane_records in (
        {},
        _all_other_lanes_nominal_or_waiting(),
        {"spy_offline_daily_cycle": {"daily_chain_state": "review_only"}},
    ):
        payload = _plan_from_records(tmp_path, lane_records)
        buckets = (
            list(payload["offline_runnable_lanes"])
            + list(payload["authorized_network_lanes"])
            + list(payload["operator_gated_lanes"])
            + list(payload["noop_lanes"])
        )
        assert sorted(buckets) == sorted(
            str(action["lane_id"]) for action in payload["actions"]
        ), payload["plan_class"]
        assert len(buckets) == payload["lane_count"]


def test_authorized_network_plan_class_agrees_with_its_action(tmp_path: Path) -> None:
    for lane_records in (
        {},
        _all_other_lanes_nominal_or_waiting(),
        {
            "spy_market_data_soak": {
                "evidence_state": "accepted_unattended_market_data_soak",
                "latest_attempted_session_date": AS_OF,
            },
            **_all_other_lanes_nominal_or_waiting(),
        },
    ):
        payload = _plan_from_records(tmp_path, lane_records)
        has_network = payload["next_authorized_network_action"] is not None
        assert has_network is (payload["authorized_network_lanes"] != [])
        assert has_network is (payload["next_authorized_network_action_lane"] != "")
        if payload["plan_class"] == PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE:
            assert has_network
            assert payload["offline_runnable_lanes"] == []


def test_offline_action_outranks_authorized_network_action(tmp_path: Path) -> None:
    # An offline command needs no network at all, so it still wins the plan
    # class even when an authorized network action is also available.
    payload = _plan_from_records(tmp_path)

    assert payload["authorized_network_lanes"] == ["spy_market_data_soak"]
    assert payload["next_authorized_network_action_lane"] == "spy_market_data_soak"
    assert payload["plan_class"] == PLAN_OFFLINE_ACTION_AVAILABLE


def test_render_text_reports_the_authorized_network_lane(tmp_path: Path) -> None:
    payload = _plan_from_records(tmp_path, _all_other_lanes_nominal_or_waiting())
    text = render_autonomy_next_plan_text(payload)

    assert "plan_class: authorized_network_action_available" in text
    assert (
        "next_authorized_network_action_lane: spy_market_data_soak" in text
    )
