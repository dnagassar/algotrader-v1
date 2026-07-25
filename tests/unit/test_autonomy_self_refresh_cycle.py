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
    AUTONOMY_SUPERVISOR_SYSTEM_STATUSES,
    AutonomySupervisorConfig,
)
from algotrader.execution.autonomy_self_refresh_cycle import (
    OUTCOME_DRY_RUN_PREVIEW,
    OUTCOME_EVIDENCE_REQUIRED,
    OUTCOME_EXECUTION_FAILED,
    OUTCOME_NOOP_NO_ACTION,
    OUTCOME_REFRESHED,
    OUTCOME_STILL_PENDING,
    _SYSTEM_SEVERITY,
    _classify_outcome,
    build_self_refresh_cycle,
    render_self_refresh_cycle_json,
    render_self_refresh_cycle_text,
    write_self_refresh_cycle_jsonl,
)


MODULE_PATH = Path("src/algotrader/execution/autonomy_self_refresh_cycle.py")
SCRIPT_PATH = Path("scripts/run_autonomy_self_refresh_cycle.ps1")
AS_OF = "2026-07-24T00:00:00Z"
STALE_AT = "2026-07-20T00:00:00Z"

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
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
    "cancel_order",
    "create_order",
    "getenv",
    "now",
    "run",
    "submit_order",
    "system",
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
    kwargs = {"run_id": "cycle-test", "as_of": AS_OF, "lanes_root": tmp_path}
    kwargs.update(overrides)
    return AutonomySupervisorConfig(**kwargs)


def _daily_cycle_path(tmp_path: Path) -> Path:
    path = tmp_path / "paper_lab" / "m444_offline_daily_cycle_run.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _seed_stale_daily_cycle(tmp_path: Path) -> Path:
    path = _daily_cycle_path(tmp_path)
    path.write_text(
        json.dumps(
            {"daily_chain_state": "accepted_observe_hold_noop", "generated_at": STALE_AT}
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _assert_safety_false(payload: dict) -> None:
    for key in _SAFETY_FALSE_KEYS:
        assert payload[key] is False, key


# --------------------------------------------------------------------------- #
# Dry run is inert
# --------------------------------------------------------------------------- #
def test_dry_run_preview_executes_nothing(tmp_path: Path) -> None:
    _seed_stale_daily_cycle(tmp_path)

    def _forbidden(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("dry run must not execute")

    cycle = build_self_refresh_cycle(
        _config(tmp_path), apply=False, environ={}, runner=_forbidden
    )
    assert cycle["cycle_outcome"] == OUTCOME_DRY_RUN_PREVIEW
    assert cycle["dry_run"] is True
    assert cycle["execution_count"] == 0
    # V5.44: zero executions is not a vacuous success claim.
    assert cycle["all_executions_succeeded"] is None
    # Dry run does not change lane evidence, so before == after.
    assert cycle["before_system_status"] == cycle["after_system_status"]
    _assert_safety_false(cycle)


# --------------------------------------------------------------------------- #
# The loop closes: stale evidence the loop cannot cure converges to "waiting"
# --------------------------------------------------------------------------- #
def test_stale_daily_cycle_converges_to_operator_wait(tmp_path: Path) -> None:
    # No allowlisted offline command writes this lane's artifact: the pinned
    # m446 milestone rerun writes the M447 manifest, not m444. So staleness here
    # is operator-curable only, and the loop converges by correctly reporting it
    # has nothing to run rather than spinning on an action that cannot help.
    _seed_stale_daily_cycle(tmp_path)

    def _forbidden(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("no allowlisted action can cure daily-cycle staleness")

    cycle = build_self_refresh_cycle(
        _config(tmp_path), apply=True, environ={}, runner=_forbidden
    )

    # The staleness signal itself is preserved, not suppressed.
    assert "spy_offline_daily_cycle" in cycle["before_report"]["stale_lanes"]
    assert "spy_offline_daily_cycle" in cycle["after_report"]["stale_lanes"]
    assert cycle["plan_summary"]["next_offline_action_lane"] == ""
    assert "spy_offline_daily_cycle" in cycle["plan_summary"]["operator_gated_lanes"]
    # Nothing was eligible, nothing ran, and the system waits on the operator.
    assert cycle["eligible_count"] == 0
    assert cycle["execution_count"] == 0
    assert cycle["all_executions_succeeded"] is None
    assert cycle["before_system_status"] == "waiting"
    assert cycle["after_system_status"] == "waiting"
    assert cycle["cycle_outcome"] == OUTCOME_NOOP_NO_ACTION
    assert cycle["converged"] is True
    _assert_safety_false(cycle)


def test_stale_apply_cycle_is_inert(tmp_path: Path) -> None:
    # This concrete stale-lane scenario must not reach the obsolete M446 rerun.
    # The executor registry test separately proves no current lane action can
    # reach the allowlist.
    _seed_stale_daily_cycle(tmp_path)

    def _forbidden(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("executor must be inert under the current registry")

    cycle = build_self_refresh_cycle(
        _config(tmp_path), apply=True, environ={}, runner=_forbidden
    )
    assert cycle["eligible_count"] == 0
    assert cycle["execution_count"] == 0
    assert cycle["all_executions_succeeded"] is None


def test_no_lane_evidence_fails_closed_by_default(tmp_path: Path) -> None:
    cycle = build_self_refresh_cycle(_config(tmp_path), apply=False, environ={})

    assert cycle["before_system_status"] == "no_lane_evidence"
    assert cycle["after_system_status"] == "no_lane_evidence"
    assert cycle["cycle_outcome"] == OUTCOME_EVIDENCE_REQUIRED
    assert cycle["allow_empty_lab"] is False
    assert cycle["evidence_required"] is True
    assert cycle["converged"] is False
    _assert_safety_false(cycle)


def test_explicit_empty_lab_can_converge(tmp_path: Path) -> None:
    cycle = build_self_refresh_cycle(
        _config(tmp_path),
        apply=False,
        allow_empty_lab=True,
        environ={},
    )

    assert cycle["after_system_status"] == "no_lane_evidence"
    assert cycle["cycle_outcome"] == OUTCOME_DRY_RUN_PREVIEW
    assert cycle["allow_empty_lab"] is True
    assert cycle["evidence_required"] is False
    assert cycle["converged"] is True
    _assert_safety_false(cycle)


@pytest.mark.parametrize(
    ("apply_flag", "count", "ok", "before", "after", "expected"),
    (
        (False, 0, True, "attention_required", "attention_required", OUTCOME_DRY_RUN_PREVIEW),
        (True, 0, True, "waiting", "waiting", OUTCOME_NOOP_NO_ACTION),
        (True, 1, False, "attention_required", "attention_required", OUTCOME_EXECUTION_FAILED),
        (True, 1, True, "attention_required", "nominal", OUTCOME_REFRESHED),
        (True, 1, True, "attention_required", "attention_required", OUTCOME_STILL_PENDING),
    ),
)
def test_outcome_classification(
    apply_flag: bool, count: int, ok: bool, before: str, after: str, expected: str
) -> None:
    # The execute/refresh code paths stay correct and covered even though the
    # current lane registry cannot reach them.
    assert (
        _classify_outcome(
            apply=apply_flag,
            execution_count=count,
            all_succeeded=ok,
            before_status=before,
            after_status=after,
        )
        == expected
    )


# --------------------------------------------------------------------------- #
# V5.42a: severity ranking is derived, fail-closed, and correctly ordered
# --------------------------------------------------------------------------- #
def test_severity_map_matches_the_exported_vocabulary() -> None:
    assert set(_SYSTEM_SEVERITY) == set(AUTONOMY_SUPERVISOR_SYSTEM_STATUSES)
    ranks = [_SYSTEM_SEVERITY[status] for status in AUTONOMY_SUPERVISOR_SYSTEM_STATUSES]
    # Strictly decreasing: the exported tuple is most-to-least severe.
    assert ranks == sorted(ranks, reverse=True)
    assert len(set(ranks)) == len(ranks)


def test_no_lane_evidence_outranks_every_other_status() -> None:
    for status in AUTONOMY_SUPERVISOR_SYSTEM_STATUSES:
        if status == "no_lane_evidence":
            continue
        assert _SYSTEM_SEVERITY["no_lane_evidence"] > _SYSTEM_SEVERITY[status]


@pytest.mark.parametrize("before", ("blocked", "attention_required", "waiting", "nominal"))
def test_losing_all_evidence_is_never_a_refresh(before: str) -> None:
    # An empty lab is declared, so the fail-closed branch does not short-circuit
    # and the improvement test is what decides the outcome.
    assert (
        _classify_outcome(
            apply=True,
            execution_count=1,
            all_succeeded=True,
            before_status=before,
            after_status="no_lane_evidence",
            allow_empty_lab=True,
        )
        == OUTCOME_STILL_PENDING
    )


def test_seeding_an_empty_lab_is_a_refresh() -> None:
    assert (
        _classify_outcome(
            apply=True,
            execution_count=1,
            all_succeeded=True,
            before_status="no_lane_evidence",
            after_status="nominal",
        )
        == OUTCOME_REFRESHED
    )


# --------------------------------------------------------------------------- #
# V5.44: zero executions is tri-state (True/False/None), never vacuously true
# --------------------------------------------------------------------------- #
def test_classify_outcome_fails_closed_on_none_with_nonzero_count() -> None:
    # execution_count > 0 with all_succeeded=None violates the producer
    # contract; classification must fail closed to execution_failed rather
    # than treat the absent claim as success.
    assert (
        _classify_outcome(
            apply=True,
            execution_count=1,
            all_succeeded=None,
            before_status="attention_required",
            after_status="attention_required",
        )
        == OUTCOME_EXECUTION_FAILED
    )


@pytest.mark.parametrize("bad_status", ("", "degraded", "NOMINAL", "unknown"))
def test_unrankable_system_status_fails_closed(bad_status: str) -> None:
    # Defaulting here would let an unranked status decide whether the cycle
    # claims it refreshed the system.
    with pytest.raises(ValidationError):
        _classify_outcome(
            apply=True,
            execution_count=1,
            all_succeeded=True,
            before_status="attention_required",
            after_status=bad_status,
        )


def test_noop_when_nothing_eligible(tmp_path: Path) -> None:
    # Fresh daily-cycle evidence: nominal, nothing to refresh.
    _daily_cycle_path(tmp_path).write_text(
        json.dumps(
            {"daily_chain_state": "accepted_observe_hold_noop", "generated_at": AS_OF}
        )
        + "\n",
        encoding="utf-8",
    )

    def _forbidden(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("nothing should execute")

    cycle = build_self_refresh_cycle(
        _config(tmp_path), apply=True, environ={}, runner=_forbidden
    )
    assert cycle["eligible_count"] == 0
    assert cycle["execution_count"] == 0
    assert cycle["all_executions_succeeded"] is None
    assert cycle["cycle_outcome"] == OUTCOME_NOOP_NO_ACTION
    assert cycle["converged"] is True


def test_apply_refuses_execution_under_live_signal(tmp_path: Path) -> None:
    _seed_stale_daily_cycle(tmp_path)

    def _forbidden(argv, environ):  # pragma: no cover - must not run
        raise AssertionError("must not execute when preflight fails")

    cycle = build_self_refresh_cycle(
        _config(tmp_path),
        apply=True,
        environ={"APP_PROFILE": "live"},
        runner=_forbidden,
    )
    # Executor refused at preflight; nothing ran and the lane stays stale.
    assert cycle["execution_count"] == 0
    assert cycle["all_executions_succeeded"] is None
    assert cycle["execution_ledger"]["preflight_ok"] is False
    assert "spy_offline_daily_cycle" in cycle["after_report"]["stale_lanes"]


# --------------------------------------------------------------------------- #
# Rendering / writing / validation
# --------------------------------------------------------------------------- #
def test_render_json_deterministic_and_sorted(tmp_path: Path) -> None:
    cycle = build_self_refresh_cycle(_config(tmp_path), apply=False, environ={})
    rendered = render_self_refresh_cycle_json(cycle)
    assert "\n" not in rendered
    reparsed = json.loads(rendered)
    assert list(reparsed.keys()) == sorted(reparsed.keys())
    assert reparsed["record_type"] == "autonomy_self_refresh_cycle"


def test_render_text_reports_outcome_and_safety(tmp_path: Path) -> None:
    cycle = build_self_refresh_cycle(_config(tmp_path), apply=False, environ={})
    text = render_self_refresh_cycle_text(cycle)
    assert "Offline autonomy self-refresh cycle" in text
    assert "cycle_outcome:" in text
    assert "live_authorized: false" in text
    # V5.44: zero executions renders distinctly from true/false.
    assert "all_executions_succeeded: not_applicable" in text


def test_render_json_nulls_all_executions_succeeded_at_zero_count(
    tmp_path: Path,
) -> None:
    cycle = build_self_refresh_cycle(_config(tmp_path), apply=False, environ={})
    reparsed = json.loads(render_self_refresh_cycle_json(cycle))
    assert reparsed["execution_count"] == 0
    assert reparsed["all_executions_succeeded"] is None


def test_write_jsonl_one_record(tmp_path: Path) -> None:
    cycle = build_self_refresh_cycle(_config(tmp_path), apply=False, environ={})
    out = tmp_path / "nested" / "cycle.jsonl"
    result = write_self_refresh_cycle_jsonl(cycle, out)
    assert result["record_count"] == 1
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n") and len(text.splitlines()) == 1


def test_rejects_wrong_config(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_self_refresh_cycle({"run_id": "x"})  # type: ignore[arg-type]


def test_rejects_non_bool_apply(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_self_refresh_cycle(_config(tmp_path), apply="yes")  # type: ignore[arg-type]


def test_rejects_non_bool_allow_empty_lab(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        build_self_refresh_cycle(
            _config(tmp_path),
            allow_empty_lab="yes",  # type: ignore[arg-type]
        )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_dry_run(tmp_path: Path) -> None:
    _seed_stale_daily_cycle(tmp_path)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-self-refresh-cycle",
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
    assert payload["record_type"] == "autonomy_self_refresh_cycle"
    assert payload["dry_run"] is True
    assert payload["execution_count"] == 0
    assert payload["all_executions_succeeded"] is None
    # The stale lane is operator-curable only, so the loop has converged on a
    # correct waiting state: exit 0, with the staleness still reported.
    assert payload["converged"] is True
    assert "spy_offline_daily_cycle" in payload["after_report"]["stale_lanes"]
    assert exit_code == 0
    _assert_safety_false(payload)


def test_cli_no_lane_evidence_exits_one_by_default(tmp_path: Path) -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-self-refresh-cycle",
                "--run-id",
                "cli-empty",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--format",
                "json",
            ]
        )

    payload = json.loads(buffer.getvalue().strip())
    assert payload["cycle_outcome"] == OUTCOME_EVIDENCE_REQUIRED
    assert payload["evidence_required"] is True
    assert payload["converged"] is False
    assert exit_code == 1


def test_cli_allows_explicit_empty_lab(tmp_path: Path) -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli_module.main(
            [
                "autonomy-self-refresh-cycle",
                "--run-id",
                "cli-empty",
                "--as-of",
                AS_OF,
                "--lanes-root",
                str(tmp_path),
                "--allow-empty-lab",
                "--format",
                "json",
            ]
        )

    payload = json.loads(buffer.getvalue().strip())
    assert payload["allow_empty_lab"] is True
    assert payload["evidence_required"] is False
    assert payload["converged"] is True
    assert exit_code == 0


def test_powershell_wrapper_forwards_allow_empty_lab() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[switch]$AllowEmptyLab" in script
    assert '$Arguments += "--allow-empty-lab"' in script


def test_cli_bad_lane_override_returns_validation_exit(tmp_path: Path) -> None:
    exit_code = cli_module.main(
        [
            "autonomy-self-refresh-cycle",
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
# Safety source-scan
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
