from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.autonomy_supervisor import AutonomySupervisorConfig
from algotrader.execution.autonomy_self_refresh_cycle import (
    OUTCOME_DRY_RUN_PREVIEW,
    OUTCOME_EXECUTION_FAILED,
    OUTCOME_NOOP_NO_ACTION,
    OUTCOME_REFRESHED,
    build_self_refresh_cycle,
    render_self_refresh_cycle_json,
    render_self_refresh_cycle_text,
    write_self_refresh_cycle_jsonl,
)


MODULE_PATH = Path("src/algotrader/execution/autonomy_self_refresh_cycle.py")
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
    # Dry run does not change lane evidence, so before == after.
    assert cycle["before_system_status"] == cycle["after_system_status"]
    _assert_safety_false(cycle)


# --------------------------------------------------------------------------- #
# The loop closes: stale -> execute -> converge
# --------------------------------------------------------------------------- #
def test_stale_daily_cycle_refreshes_and_converges(tmp_path: Path) -> None:
    path = _seed_stale_daily_cycle(tmp_path)

    def _refresh_runner(argv, environ):
        # Simulate the rerun writing fresh (non-stale) daily-cycle evidence.
        path.write_text(
            json.dumps(
                {"daily_chain_state": "accepted_observe_hold_noop", "generated_at": AS_OF}
            )
            + "\n",
            encoding="utf-8",
        )
        return {"exit_code": 0, "stdout": "", "stderr": "", "timed_out": False}

    cycle = build_self_refresh_cycle(
        _config(tmp_path), apply=True, environ={}, runner=_refresh_runner
    )

    assert cycle["before_system_status"] == "attention_required"
    assert "spy_offline_daily_cycle" in cycle["before_report"]["stale_lanes"]
    assert cycle["eligible_count"] == 1
    assert cycle["execution_count"] == 1
    assert cycle["all_executions_succeeded"] is True
    assert cycle["after_system_status"] == "nominal"
    assert cycle["after_report"]["stale_lanes"] == []
    assert cycle["cycle_outcome"] == OUTCOME_REFRESHED
    assert cycle["converged"] is True
    _assert_safety_false(cycle)


def test_failed_refresh_does_not_converge(tmp_path: Path) -> None:
    _seed_stale_daily_cycle(tmp_path)

    def _failing_runner(argv, environ):
        # Command runs but fails; it writes no fresh evidence.
        return {"exit_code": 3, "stdout": "", "stderr": "boom", "timed_out": False}

    cycle = build_self_refresh_cycle(
        _config(tmp_path), apply=True, environ={}, runner=_failing_runner
    )
    assert cycle["execution_count"] == 1
    assert cycle["all_executions_succeeded"] is False
    assert cycle["cycle_outcome"] == OUTCOME_EXECUTION_FAILED
    # The lane is still stale, so the system still needs attention.
    assert cycle["after_system_status"] == "attention_required"
    assert cycle["converged"] is False


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
    # Executor refused; nothing ran, lane stays stale.
    assert cycle["execution_count"] == 0
    assert cycle["execution_ledger"]["preflight_ok"] is False
    assert cycle["converged"] is False


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
    # Stale lane not refreshed in a dry run -> not converged -> exit 1.
    assert exit_code == 1
    _assert_safety_false(payload)


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
