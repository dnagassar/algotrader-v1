"""Gated executor for the offline-runnable subset of the autonomy plan.

The V5.38 planner (:mod:`algotrader.execution.autonomy_next_plan`) resolves each
lane's recommended action into a concrete plan and marks which actions are
offline-runnable. This module is the one authorized step that can *act* on that
plan — and only on the strictly-offline, fully-defaulted subset of it, behind a
hard gate.

Its authority is deliberately narrow:

- It executes only commands on the frozen :data:`AUTONOMY_EXECUTOR_ALLOWLIST`.
  Every allowlisted command is a fully-defaulted CLI subcommand whose producing
  module was verified to import no network, broker, credential, or profile
  surface. An action not on the allowlist is never executed.
- It is **dry-run by default**. Without ``apply=True`` it resolves what *would*
  run and executes nothing (it spawns no subprocess at all).
- Before any execution it runs a credential/profile/network preflight over the
  environment and refuses to execute if a paper/live profile or any Alpaca
  credential or network-test variable is loaded. It reports only the offending
  variable *names*, never their values.
- It executes each allowlisted command with a sanitized child environment that
  has every credential/profile variable removed, so a child can neither
  authenticate nor reach a broker even if it tried.
- It performs and exposes no submit/cancel/replace/close/liquidation/paper-
  mutation/capital/live action of its own. It writes one deterministic local
  action ledger.

Autonomous execution of even these offline commands is a standing authority the
operator authorized explicitly; this module is the sole seam that exercises it,
and it fails closed everywhere else.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.autonomy_next_plan import (
    EXECUTION_AUTO_OFFLINE,
    build_autonomy_next_plan,
    build_autonomy_next_plan_from_report,
)
from algotrader.execution.autonomy_supervisor import AutonomySupervisorConfig

__all__ = [
    "AUTONOMY_EXECUTOR_ALLOWLIST",
    "AUTONOMY_EXECUTOR_LABELS",
    "CREDENTIAL_PREFLIGHT_ENV_KEYS",
    "SKIP_NOT_ALLOWLISTED",
    "SKIP_NOT_OFFLINE_RUNNABLE",
    "SKIP_REQUIRES_OPERATOR_INPUT",
    "build_offline_execution_ledger",
    "execution_preflight",
    "render_offline_execution_ledger_json",
    "render_offline_execution_ledger_text",
    "write_offline_execution_ledger_jsonl",
]


_MILESTONE = "V5.39 - Gated offline autonomy executor"
_RECORD_TYPE = "autonomy_offline_execution_ledger"
_COMMAND = "autonomy-apply-plan"
_PROFIT_CLAIM = "none"
_STDIO_TAIL_LIMIT = 2000
_DEFAULT_TIMEOUT_SECONDS = 600

AUTONOMY_EXECUTOR_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

# Environment variables whose presence forces the executor to refuse to run.
# Reported by name only; values are never read into the ledger.
CREDENTIAL_PREFLIGHT_ENV_KEYS = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
)
_PROFILE_ENV_KEY = "APP_PROFILE"
_STRIPPED_CHILD_ENV_KEYS = (*CREDENTIAL_PREFLIGHT_ENV_KEYS, _PROFILE_ENV_KEY)

# Frozen allowlist mapping a V5.38 ``recommended_next_action`` token to the exact
# CLI argv the executor is permitted to run. Every command here is a
# fully-defaulted offline subcommand whose producing module imports no network,
# broker, credential, or profile surface (verified: etf_sma_offline_daily_cycle_
# rerun_m446). The seed command etf-sma-offline-daily-cycle-run is intentionally
# absent because it requires operator-supplied inputs.
AUTONOMY_EXECUTOR_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "rerun_offline_daily_cycle_chain": (
        "etf-sma-offline-daily-cycle-rerun-m446",
    ),
}

# Reasons an offline-planned action is skipped rather than executed.
SKIP_NOT_OFFLINE_RUNNABLE = "not_offline_runnable"
SKIP_REQUIRES_OPERATOR_INPUT = "requires_operator_input"
SKIP_NOT_ALLOWLISTED = "not_allowlisted"


def execution_preflight(
    environ: Mapping[str, str] | None = None,
) -> tuple[bool, list[str]]:
    """Return ``(ok, reasons)`` for whether execution is permitted.

    ``ok`` is ``False`` if a paper/live profile or any credential/network-test
    variable is loaded. Reasons name the offending variable only; no value is
    read into the result.
    """

    source = os.environ if environ is None else environ
    reasons: list[str] = []
    profile = source.get(_PROFILE_ENV_KEY, "")
    if isinstance(profile, str) and profile.strip() in ("paper", "live"):
        reasons.append(f"profile_loaded:{_PROFILE_ENV_KEY}")
    for key in CREDENTIAL_PREFLIGHT_ENV_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip() != "":
            reasons.append(f"credential_or_network_var_loaded:{key}")
    return (not reasons, reasons)


@dataclass(frozen=True, slots=True)
class _EligibleAction:
    lane_id: str
    recommended_action: str
    argv: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SkippedAction:
    lane_id: str
    recommended_action: str
    execution_class: str
    reason: str


def build_offline_execution_ledger(
    config: AutonomySupervisorConfig,
    *,
    apply: bool = False,
    plan_report: Mapping[str, object] | None = None,
    environ: Mapping[str, str] | None = None,
    runner=None,
) -> dict[str, object]:
    """Build one deterministic offline execution ledger.

    With ``apply=False`` (the default) the ledger records what *would* run and
    executes nothing. With ``apply=True`` it runs the eligible allowlisted
    commands after a passing preflight, capturing each result. ``runner`` is an
    injectable subprocess runner used by tests; production uses the real one.
    """

    if type(config) is not AutonomySupervisorConfig:
        raise ValidationError("config must be an AutonomySupervisorConfig.")
    if type(apply) is not bool:
        raise ValidationError("apply must be a bool.")

    if plan_report is None:
        plan = build_autonomy_next_plan(config)
    else:
        source = _plan_source(plan_report)
        if source.get("record_type") == "autonomy_next_plan":
            plan = source
        else:
            plan = build_autonomy_next_plan_from_report(source)

    eligible, skipped = _partition_actions(plan)
    preflight_ok, preflight_reasons = execution_preflight(environ)

    executed: list[dict[str, object]] = []
    execution_refused_reason = ""
    if apply:
        if not preflight_ok:
            execution_refused_reason = "preflight_failed"
        elif eligible:
            active_runner = runner if runner is not None else _run_subprocess
            for action in eligible:
                executed.append(_execute(action, active_runner, environ))

    execution_count = len(executed)
    all_succeeded = all(
        record["exit_code"] == 0 for record in executed
    )

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": plan["run_id"],
        "as_of": plan["as_of"],
        "lanes_root": plan["lanes_root"],
        "labels": list(AUTONOMY_EXECUTOR_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "apply": apply,
        "dry_run": not apply,
        "preflight_ok": preflight_ok,
        "preflight_reasons": preflight_reasons,
        "plan_class": plan["plan_class"],
        "supervisor_system_status": plan["supervisor_system_status"],
        "eligible_actions": [
            {
                "lane_id": action.lane_id,
                "recommended_action": action.recommended_action,
                "argv": list(action.argv),
            }
            for action in eligible
        ],
        "eligible_count": len(eligible),
        "skipped_actions": [
            {
                "lane_id": action.lane_id,
                "recommended_action": action.recommended_action,
                "execution_class": action.execution_class,
                "reason": action.reason,
            }
            for action in skipped
        ],
        "executed_actions": executed,
        "execution_count": execution_count,
        "execution_refused_reason": execution_refused_reason,
        "all_executions_succeeded": all_succeeded,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _partition_actions(
    plan: Mapping[str, object],
) -> tuple[list[_EligibleAction], list[_SkippedAction]]:
    eligible: list[_EligibleAction] = []
    skipped: list[_SkippedAction] = []
    for action in _plan_actions(plan):
        lane_id = _text(action.get("lane_id"))
        recommended = _text(action.get("recommended_action"))
        execution_class = _text(action.get("execution_class"))
        offline_runnable = action.get("offline_runnable") is True

        if not offline_runnable:
            skipped.append(
                _SkippedAction(
                    lane_id, recommended, execution_class, SKIP_NOT_OFFLINE_RUNNABLE
                )
            )
            continue
        if recommended not in AUTONOMY_EXECUTOR_ALLOWLIST:
            # Offline-runnable but needs operator input (e.g. the seed), so it is
            # not on the unattended allowlist.
            reason = (
                SKIP_REQUIRES_OPERATOR_INPUT
                if execution_class != EXECUTION_AUTO_OFFLINE
                else SKIP_NOT_ALLOWLISTED
            )
            skipped.append(
                _SkippedAction(lane_id, recommended, execution_class, reason)
            )
            continue
        eligible.append(
            _EligibleAction(
                lane_id=lane_id,
                recommended_action=recommended,
                argv=AUTONOMY_EXECUTOR_ALLOWLIST[recommended],
            )
        )
    return eligible, skipped


def _execute(action: _EligibleAction, runner, environ) -> dict[str, object]:
    # Defence in depth: never hand a non-allowlisted argv to the runner.
    if action.recommended_action not in AUTONOMY_EXECUTOR_ALLOWLIST:
        raise ValidationError("refusing to execute a non-allowlisted action.")
    if AUTONOMY_EXECUTOR_ALLOWLIST[action.recommended_action] != action.argv:
        raise ValidationError("resolved argv does not match the allowlist.")

    result = runner(action.argv, environ)
    return {
        "lane_id": action.lane_id,
        "recommended_action": action.recommended_action,
        "argv": list(action.argv),
        "exit_code": int(result["exit_code"]),
        "succeeded": int(result["exit_code"]) == 0,
        "stdout_tail": _tail(_text(result.get("stdout"))),
        "stderr_tail": _tail(_text(result.get("stderr"))),
        "timed_out": result.get("timed_out") is True,
    }


def _run_subprocess(
    argv: tuple[str, ...],
    environ: Mapping[str, str] | None,
) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[3]
    src_path = str(repo_root / "src")
    base_env = dict(os.environ if environ is None else environ)
    child_env = {
        key: value
        for key, value in base_env.items()
        if key not in _STRIPPED_CHILD_ENV_KEYS
    }
    child_env["PYTHONPATH"] = src_path
    command = [sys.executable, "-m", "algotrader.cli", *argv]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed allowlisted argv only
            command,
            cwd=str(repo_root),
            env=child_env,
            capture_output=True,
            text=True,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "timed_out": False,
    }


def render_offline_execution_ledger_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_offline_execution_ledger_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable execution ledger summary."""

    lines = [
        "Gated offline autonomy execution ledger",
        f"run_id: {payload.get('run_id', '')}",
        f"as_of: {payload.get('as_of', '')}",
        f"apply: {_bool_text(payload.get('apply'))}",
        f"dry_run: {_bool_text(payload.get('dry_run'))}",
        f"preflight_ok: {_bool_text(payload.get('preflight_ok'))}",
        f"plan_class: {payload.get('plan_class', '')}",
        f"eligible_count: {payload.get('eligible_count', 0)}",
        f"execution_count: {payload.get('execution_count', 0)}",
        f"execution_refused_reason: {payload.get('execution_refused_reason', '') or 'none'}",
        f"all_executions_succeeded: {_bool_text(payload.get('all_executions_succeeded'))}",
        "eligible_actions:",
    ]
    for action in _mapping_list(payload.get("eligible_actions")):
        argv = " ".join(_string_list(action.get("argv")))
        lines.append(
            f"  - {action.get('lane_id', '')}: {action.get('recommended_action', '')}"
            f" | argv={argv}"
        )
    lines.append("executed_actions:")
    for action in _mapping_list(payload.get("executed_actions")):
        lines.append(
            f"  - {action.get('lane_id', '')}: exit={action.get('exit_code', '')}"
            f" | succeeded={_bool_text(action.get('succeeded'))}"
            f" | timed_out={_bool_text(action.get('timed_out'))}"
        )
    lines.append("skipped_actions:")
    for action in _mapping_list(payload.get("skipped_actions")):
        lines.append(
            f"  - {action.get('lane_id', '')}: {action.get('recommended_action', '')}"
            f" | reason={action.get('reason', '')}"
        )
    lines.extend(
        (
            f"preflight_reasons: {_joined(_string_list(payload.get('preflight_reasons')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"broker_action_performed: {_bool_text(payload.get('broker_action_performed'))}",
            f"network_access_attempted: {_bool_text(payload.get('network_access_attempted'))}",
            f"credential_access_attempted: {_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )
    return "\n".join(lines)


def write_offline_execution_ledger_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> dict[str, object]:
    """Write exactly one JSONL ledger record, replacing any prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_offline_execution_ledger_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return {
        "output_path": str(path),
        "record_count": 1,
        "bytes_written": len(line.encode("utf-8")),
        "newline_terminated": line.endswith("\n"),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _plan_source(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError("plan_report must be a mapping.")
    if value.get("record_type") == "autonomy_supervisor_report":
        return value
    if value.get("record_type") == "autonomy_next_plan":
        return value
    raise ValidationError(
        "plan_report must be an autonomy_next_plan or autonomy_supervisor_report "
        "record."
    )


def _plan_actions(plan: Mapping[str, object]) -> list[Mapping[str, object]]:
    actions = plan.get("actions")
    if not isinstance(actions, list):
        raise ValidationError("plan is missing an 'actions' list.")
    resolved: list[Mapping[str, object]] = []
    for action in actions:
        if not isinstance(action, Mapping):
            raise ValidationError("each plan action must be a mapping.")
        resolved.append(action)
    return resolved


def _output_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("output_path must be a path string.")
    if str(path).strip() == "":
        raise ValidationError("output_path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _tail(text: str) -> str:
    if len(text) <= _STDIO_TAIL_LIMIT:
        return text
    return text[-_STDIO_TAIL_LIMIT:]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    return [str(item) for item in value if str(item)]


def _mapping_list(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: list[str]) -> str:
    return ",".join(values) if values else "none"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
