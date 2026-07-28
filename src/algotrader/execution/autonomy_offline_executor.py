"""Gated executor for the offline-runnable subset of the autonomy plan.

The V5.38 planner (:mod:`algotrader.execution.autonomy_next_plan`) resolves each
lane's recommended action into a concrete plan and marks which actions are
offline-runnable. This module is the one authorized step that can *act* on that
plan — and only on the strictly-offline, fully-defaulted subset of it, behind a
hard gate.

Its authority is deliberately narrow:

- It executes the two supervisor-produced readiness tokens on the frozen
  :data:`AUTONOMY_EXECUTOR_ALLOWLIST`. Both resolve to the same fully-defaulted
  import-pure replay command.
- It may execute the SPY daily-cycle seed/refresh tokens only when both declared
  operator inputs are supplied together. The input file is resolved as an
  existing local file, the timestamp is normalized, argv is constructed without
  a shell, and all M441-M444 outputs are pinned to the canonical supervised
  ``runs/`` paths.
- An action not on either exact registry is never executed.
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
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.autonomy_next_plan import (
    CANONICAL_LANES_ROOT_RELPATH,
    CANONICAL_READINESS_PACKET_RELPATH,
    CANONICAL_REPLAY_ARGV,
    CANONICAL_SPY_DAILY_CYCLE_MANIFEST_RELPATH,
    CANONICAL_SPY_DAILY_CYCLE_OUTPUTS,
    EXECUTION_AUTO_OFFLINE,
    EXECUTION_OFFLINE_OPERATOR_INPUT,
    SPY_DAILY_CYCLE_ABSENT_ACTION,
    SPY_DAILY_CYCLE_LANE_ID,
    SPY_DAILY_CYCLE_SEED_COMMAND,
    SPY_DAILY_CYCLE_STALE_ACTION,
    build_autonomy_next_plan,
    build_autonomy_next_plan_from_report,
)
from algotrader.execution.autonomy_supervisor import (
    AUTONOMY_SUPERVISOR_LANES,
    AutonomySupervisorConfig,
)

__all__ = [
    "AUTONOMY_EXECUTOR_ALLOWLIST",
    "AUTONOMY_EXECUTOR_LABELS",
    "AUTONOMY_EXECUTOR_OPERATOR_INPUT_ACTIONS",
    "CREDENTIAL_PREFLIGHT_ENV_KEYS",
    "OfflineOperatorInputs",
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

# Frozen allowlist mapping the two readiness producer tokens to the one exact
# import-pure replay argv.
AUTONOMY_EXECUTOR_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "run_supervised_readiness_trial_to_seed_r1_evidence": CANONICAL_REPLAY_ARGV,
    "rerun_supervised_readiness_trial": CANONICAL_REPLAY_ARGV,
}
AUTONOMY_EXECUTOR_OPERATOR_INPUT_ACTIONS = frozenset(
    {SPY_DAILY_CYCLE_ABSENT_ACTION, SPY_DAILY_CYCLE_STALE_ACTION}
)
_READINESS_LANE_ID = "crypto_supervised_readiness_trial"
_READINESS_REPLAY_COMMAND = "python -m algotrader.cli crypto-readiness-replay"

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


@dataclass(frozen=True, slots=True)
class OfflineOperatorInputs:
    """Operator-bound local inputs for the SPY offline daily-cycle action."""

    validated_at: str
    daily_bars_csv: Path | str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "validated_at",
            _normalized_timestamp(self.validated_at, "validated_at"),
        )
        object.__setattr__(
            self,
            "daily_bars_csv",
            _required_path(self.daily_bars_csv, "daily_bars_csv"),
        )


def build_offline_execution_ledger(
    config: AutonomySupervisorConfig,
    *,
    apply: bool = False,
    plan_report: Mapping[str, object] | None = None,
    operator_inputs: OfflineOperatorInputs | None = None,
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
    if operator_inputs is not None and type(operator_inputs) is not OfflineOperatorInputs:
        raise ValidationError("operator_inputs must be OfflineOperatorInputs or None.")

    canonical_plan = build_autonomy_next_plan(config)
    if plan_report is None:
        plan = canonical_plan
    else:
        source = _plan_source(plan_report)
        if source.get("record_type") == "autonomy_next_plan":
            supplied_plan = source
        else:
            supplied_plan = build_autonomy_next_plan_from_report(source)
        _validate_executor_target(config, supplied_plan)
        _require_plan_match(supplied_plan, canonical_plan)
        plan = canonical_plan

    repo_root = _validate_executor_target(config, plan)
    resolved_inputs = _resolve_operator_inputs(operator_inputs, repo_root)
    eligible, skipped = _partition_actions(plan, resolved_inputs)
    preflight_ok, preflight_reasons = execution_preflight(environ)

    executed: list[dict[str, object]] = []
    execution_refused_reason = ""
    if apply:
        if not preflight_ok:
            execution_refused_reason = "preflight_failed"
        elif eligible:
            active_runner = runner if runner is not None else _run_subprocess
            child_environ = _sanitized_child_environment(environ, repo_root)
            for action in eligible:
                executed.append(
                    _execute(
                        action,
                        active_runner,
                        child_environ,
                        operator_inputs=resolved_inputs,
                    )
                )

    execution_count = len(executed)
    # V5.44: zero executions is not a success claim about anything that
    # happened (dry run, genuine no-op, and preflight refusal all reach
    # here), so it is represented as `None` rather than the vacuous
    # `all([]) is True`. A real bool is reported only once something ran.
    all_succeeded: bool | None
    if executed:
        all_succeeded = all(record["exit_code"] == 0 for record in executed)
    else:
        all_succeeded = None

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
        "operator_inputs_provided": resolved_inputs is not None,
        "operator_input_bound_actions": [
            action.recommended_action
            for action in eligible
            if action.recommended_action in AUTONOMY_EXECUTOR_OPERATOR_INPUT_ACTIONS
        ],
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


def _executing_repository_root() -> Path:
    """Independently verify the repository root used for execution."""

    root = Path(__file__).resolve().parents[3]
    if not _valid_git_marker(root):
        raise ValidationError("executor source root must be a Git checkout/worktree.")
    if not (root / "src" / "algotrader" / "cli.py").is_file():
        raise ValidationError("executor source root is missing src/algotrader/cli.py.")
    try:
        cwd = Path.cwd().resolve(strict=True)
    except OSError as exc:
        raise ValidationError("executor cwd must resolve to the repository root.") from exc
    if cwd != root:
        raise ValidationError("executor cwd must equal the executing repository root.")
    return root


def _valid_git_marker(root: Path) -> bool:
    marker = root / ".git"
    if marker.is_dir():
        return (marker / "HEAD").is_file()
    if not marker.is_file():
        return False
    try:
        text = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if not text.startswith("gitdir:"):
        return False
    git_dir = Path(text.partition(":")[2].strip())
    if not git_dir.is_absolute():
        git_dir = marker.parent / git_dir
    try:
        resolved = git_dir.resolve(strict=True)
    except OSError:
        return False
    return resolved.is_dir() and (resolved / "HEAD").is_file()


def _resolved_target(value: object, *, root: Path, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    candidate = path if path.is_absolute() else root / path
    _reject_symlink_components(candidate, field_name)
    try:
        return candidate.resolve(strict=False)
    except OSError as exc:
        raise ValidationError(f"{field_name} must resolve canonically.") from exc


def _canonical_target(root: Path, relpath: Path) -> Path:
    candidate = root / relpath
    _reject_symlink_components(candidate, "canonical executor target")
    try:
        return candidate.resolve(strict=False)
    except OSError as exc:
        raise ValidationError("canonical executor target must resolve.") from exc


def _reject_symlink_components(path: Path, field_name: str) -> None:
    current = Path(path.anchor) if path.anchor else Path()
    for part in path.parts[1:] if path.anchor else path.parts:
        current /= part
        if current.is_symlink():
            raise ValidationError(f"{field_name} must not traverse a symlink.")


def _validate_executor_target(
    config: AutonomySupervisorConfig,
    plan: Mapping[str, object],
) -> Path:
    """Recheck config, plan, action, command, cwd, and target before partition."""

    root = _executing_repository_root()
    expected_lanes_root = _canonical_target(root, CANONICAL_LANES_ROOT_RELPATH)
    expected_packet = _canonical_target(root, CANONICAL_READINESS_PACKET_RELPATH)
    expected_daily_manifest = _canonical_target(
        root, CANONICAL_SPY_DAILY_CYCLE_MANIFEST_RELPATH
    )

    for value, field_name in (
        (config.lanes_root, "config lanes_root"),
        (plan.get("lanes_root"), "plan lanes_root"),
    ):
        if _resolved_target(value, root=root, field_name=field_name) != expected_lanes_root:
            raise ValidationError(f"{field_name} must be the canonical runs path.")

    if plan.get("run_id") != config.run_id or plan.get("as_of") != config.as_of:
        raise ValidationError("plan run_id/as_of must match the executor config.")

    override = config.lane_artifact_overrides.get(_READINESS_LANE_ID)
    if override is not None and (
        _resolved_target(
            override,
            root=root,
            field_name="crypto readiness lane override",
        )
        != expected_packet
    ):
        raise ValidationError(
            "crypto readiness lane override must equal the canonical packet."
        )

    readiness_actions = [
        action
        for action in _plan_actions(plan)
        if action.get("lane_id") == _READINESS_LANE_ID
    ]
    if len(readiness_actions) != 1:
        raise ValidationError("plan must contain exactly one crypto readiness action.")
    readiness = readiness_actions[0]
    if (
        _resolved_target(
            readiness.get("artifact_path"),
            root=root,
            field_name="crypto readiness artifact_path",
        )
        != expected_packet
    ):
        raise ValidationError(
            "crypto readiness artifact_path must equal the canonical packet."
        )

    state = _text(readiness.get("normalized_state"))
    readiness_spec = next(
        lane for lane in AUTONOMY_SUPERVISOR_LANES if lane.lane_id == _READINESS_LANE_ID
    )
    if state not in readiness_spec.next_actions:
        raise ValidationError("crypto readiness normalized_state is not supported.")
    expected_action = readiness_spec.next_actions[state]
    if readiness.get("recommended_action") != expected_action:
        raise ValidationError(
            "crypto readiness action does not match its normalized state."
        )

    if expected_action in AUTONOMY_EXECUTOR_ALLOWLIST:
        if (
            readiness.get("execution_class") != EXECUTION_AUTO_OFFLINE
            or readiness.get("offline_runnable") is not True
            or readiness.get("gate") != ""
            or readiness.get("command") != _READINESS_REPLAY_COMMAND
            or AUTONOMY_EXECUTOR_ALLOWLIST[expected_action] != CANONICAL_REPLAY_ARGV
        ):
            raise ValidationError("crypto readiness execution binding is not canonical.")
        if plan.get("next_offline_action_lane") != _READINESS_LANE_ID:
            raise ValidationError(
                "canonical crypto readiness action must be selected next."
            )
        selected = plan.get("next_offline_action")
        if not isinstance(selected, Mapping) or dict(selected) != dict(readiness):
            raise ValidationError(
                "selected next action must equal the crypto readiness action."
            )

    daily_override = config.lane_artifact_overrides.get(SPY_DAILY_CYCLE_LANE_ID)
    if daily_override is not None and (
        _resolved_target(
            daily_override,
            root=root,
            field_name="SPY daily-cycle lane override",
        )
        != expected_daily_manifest
    ):
        raise ValidationError(
            "SPY daily-cycle lane override must equal the canonical manifest."
        )
    daily_actions = [
        action
        for action in _plan_actions(plan)
        if action.get("lane_id") == SPY_DAILY_CYCLE_LANE_ID
    ]
    if len(daily_actions) != 1:
        raise ValidationError("plan must contain exactly one SPY daily-cycle action.")
    daily = daily_actions[0]
    if (
        _resolved_target(
            daily.get("artifact_path"),
            root=root,
            field_name="SPY daily-cycle artifact_path",
        )
        != expected_daily_manifest
    ):
        raise ValidationError(
            "SPY daily-cycle artifact_path must equal the canonical manifest."
        )
    daily_state = _text(daily.get("normalized_state"))
    daily_spec = next(
        lane
        for lane in AUTONOMY_SUPERVISOR_LANES
        if lane.lane_id == SPY_DAILY_CYCLE_LANE_ID
    )
    if daily_state not in daily_spec.next_actions:
        raise ValidationError("SPY daily-cycle normalized_state is not supported.")
    expected_daily_action = daily_spec.next_actions[daily_state]
    if daily.get("recommended_action") != expected_daily_action:
        raise ValidationError(
            "SPY daily-cycle action does not match its normalized state."
        )
    if expected_daily_action in AUTONOMY_EXECUTOR_OPERATOR_INPUT_ACTIONS and (
        daily.get("execution_class") != EXECUTION_OFFLINE_OPERATOR_INPUT
        or daily.get("offline_runnable") is not True
        or daily.get("gate") != "operator_supplied_inputs"
        or daily.get("command") != SPY_DAILY_CYCLE_SEED_COMMAND
        or not daily.get("required_operator_inputs")
    ):
        raise ValidationError("SPY daily-cycle execution binding is not canonical.")
    return root


def _require_plan_match(
    supplied_plan: Mapping[str, object],
    canonical_plan: Mapping[str, object],
) -> None:
    if _json_safe(dict(supplied_plan)) != _json_safe(dict(canonical_plan)):
        raise ValidationError(
            "supplied plan/report does not match the freshly derived canonical plan."
        )


def _sanitized_child_environment(
    environ: Mapping[str, str] | None,
    repo_root: Path,
) -> dict[str, str]:
    source = os.environ if environ is None else environ
    stripped = {key.upper() for key in _STRIPPED_CHILD_ENV_KEYS}
    child_env = {
        str(key): str(value)
        for key, value in source.items()
        if str(key).upper() not in stripped
    }
    child_env["PYTHONPATH"] = str(repo_root / "src")
    return child_env


def _partition_actions(
    plan: Mapping[str, object],
    operator_inputs: OfflineOperatorInputs | None = None,
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
        if execution_class == EXECUTION_OFFLINE_OPERATOR_INPUT:
            if (
                recommended in AUTONOMY_EXECUTOR_OPERATOR_INPUT_ACTIONS
                and operator_inputs is not None
            ):
                eligible.append(
                    _EligibleAction(
                        lane_id=lane_id,
                        recommended_action=recommended,
                        argv=_spy_daily_cycle_argv(operator_inputs),
                    )
                )
            else:
                reason = (
                    SKIP_REQUIRES_OPERATOR_INPUT
                    if operator_inputs is None
                    else SKIP_NOT_ALLOWLISTED
                )
                skipped.append(
                    _SkippedAction(lane_id, recommended, execution_class, reason)
                )
            continue
        if (
            recommended not in AUTONOMY_EXECUTOR_ALLOWLIST
            or execution_class != EXECUTION_AUTO_OFFLINE
        ):
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


def _execute(
    action: _EligibleAction,
    runner,
    environ,
    *,
    operator_inputs: OfflineOperatorInputs | None = None,
) -> dict[str, object]:
    # Defence in depth: independently rederive either the static allowlist argv
    # or the exact operator-bound SPY argv immediately before runner handoff.
    if action.recommended_action in AUTONOMY_EXECUTOR_ALLOWLIST:
        expected_argv = AUTONOMY_EXECUTOR_ALLOWLIST[action.recommended_action]
    elif action.recommended_action in AUTONOMY_EXECUTOR_OPERATOR_INPUT_ACTIONS:
        if operator_inputs is None:
            raise ValidationError(
                "refusing to execute an operator-input action without inputs."
            )
        expected_argv = _spy_daily_cycle_argv(operator_inputs)
    else:
        raise ValidationError("refusing to execute a non-allowlisted action.")
    if expected_argv != action.argv:
        raise ValidationError("resolved argv does not match the action binding.")

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


def _resolve_operator_inputs(
    value: OfflineOperatorInputs | None,
    repo_root: Path,
) -> OfflineOperatorInputs | None:
    if value is None:
        return None
    resolved_csv = _resolved_input_file(
        value.daily_bars_csv,
        root=repo_root,
        field_name="daily_bars_csv",
    )
    canonical_outputs = {
        _canonical_target(repo_root, relpath)
        for _, relpath in CANONICAL_SPY_DAILY_CYCLE_OUTPUTS
    }
    if resolved_csv in canonical_outputs:
        raise ValidationError("daily_bars_csv must not equal a canonical output path.")
    return OfflineOperatorInputs(
        validated_at=value.validated_at,
        daily_bars_csv=resolved_csv,
    )


def _resolved_input_file(
    value: Path | str,
    *,
    root: Path,
    field_name: str,
) -> Path:
    path = _required_path(value, field_name)
    candidate = path if path.is_absolute() else root / path
    _reject_symlink_components(candidate, field_name)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"{field_name} must be an existing local file.") from exc
    if not resolved.is_file():
        raise ValidationError(f"{field_name} must be an existing local file.")
    return resolved


def _required_path(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif type(value) is str:
        path = Path(value.strip())
    else:
        raise ValidationError(f"{field_name} must be a path string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _normalized_timestamp(value: object, field_name: str) -> str:
    if type(value) is not str or value.strip() == "":
        raise ValidationError(f"{field_name} is required.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware ISO-8601 value."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(
            f"{field_name} must be a timezone-aware ISO-8601 value."
        )
    return parsed.astimezone(timezone.utc).isoformat()


def _spy_daily_cycle_argv(
    operator_inputs: OfflineOperatorInputs,
) -> tuple[str, ...]:
    argv = [
        "etf-sma-offline-daily-cycle-run",
        "--validated-at",
        operator_inputs.validated_at,
        "--daily-bars-csv",
        str(operator_inputs.daily_bars_csv),
    ]
    for flag, relpath in CANONICAL_SPY_DAILY_CYCLE_OUTPUTS:
        argv.extend((flag, relpath.as_posix()))
    return tuple(argv)


def _run_subprocess(
    argv: tuple[str, ...],
    environ: Mapping[str, str] | None,
) -> dict[str, object]:
    repo_root = _executing_repository_root()
    child_env = dict(environ or {})
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
        f"all_executions_succeeded: {_tri_bool_text(payload.get('all_executions_succeeded'))}",
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


def _tri_bool_text(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "not_applicable"


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
