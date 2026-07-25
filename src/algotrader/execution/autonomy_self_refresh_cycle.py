"""Offline autonomy self-refresh cycle: one observe -> decide -> act -> re-observe.

This is the Stage 3 closed loop. It composes the three autonomy layers into one
deterministic cycle:

1. Observe  - build the V5.37 cross-lane supervisor report (``before``).
2. Decide   - build the V5.38 next-action plan from that report.
3. Act      - run the V5.39 gated offline executor over the plan. Dry-run by
              default (executes nothing); with ``apply=True`` it runs the
              eligible allowlisted offline commands.
4. Re-observe - rebuild the supervisor report (``after``) and classify whether
              the system converged to a healthy steady state.

It performs no work of its own beyond orchestration: every side effect is the
executor's, and the executor only runs frozen-allowlist offline commands behind a
credential/profile preflight. This module spawns no subprocess, imports no broker
SDK, opens no socket, reads no wall clock (time comes from the caller ``as_of``),
and performs no submit/mutation/live action. Every record fixes the safety
booleans to false.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.autonomy_next_plan import (
    build_autonomy_next_plan_from_report,
)
from algotrader.execution.autonomy_offline_executor import (
    build_offline_execution_ledger,
)
from algotrader.execution.autonomy_supervisor import (
    AUTONOMY_SUPERVISOR_SYSTEM_STATUSES,
    AutonomySupervisorConfig,
    SYSTEM_NOMINAL,
    SYSTEM_NO_LANE_EVIDENCE,
    SYSTEM_WAITING,
    build_autonomy_supervisor_report,
)

__all__ = [
    "AUTONOMY_SELF_REFRESH_LABELS",
    "OUTCOME_DRY_RUN_PREVIEW",
    "OUTCOME_EVIDENCE_REQUIRED",
    "OUTCOME_EXECUTION_FAILED",
    "OUTCOME_NOOP_NO_ACTION",
    "OUTCOME_REFRESHED",
    "OUTCOME_STILL_PENDING",
    "build_self_refresh_cycle",
    "render_self_refresh_cycle_json",
    "render_self_refresh_cycle_text",
    "write_self_refresh_cycle_jsonl",
]


_MILESTONE = "V5.42 - Offline autonomy self-refresh cycle"
_RECORD_TYPE = "autonomy_self_refresh_cycle"
_COMMAND = "autonomy-self-refresh-cycle"
_PROFIT_CLAIM = "none"

AUTONOMY_SELF_REFRESH_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

OUTCOME_DRY_RUN_PREVIEW = "dry_run_preview"
OUTCOME_EVIDENCE_REQUIRED = "evidence_required"
OUTCOME_NOOP_NO_ACTION = "noop_no_action"
OUTCOME_REFRESHED = "refreshed"
OUTCOME_STILL_PENDING = "still_pending"
OUTCOME_EXECUTION_FAILED = "execution_failed"

# System-status severity, derived from the supervisor's own exported ordering
# rather than restated here: a status the supervisor can emit but this map does
# not rank would otherwise take a default rank and invent an answer. Used only to
# decide whether the act phase reduced overall severity (a genuine refresh).
#
# Higher is more severe. ``no_lane_evidence`` ranks highest, so a cycle whose
# lane evidence disappeared can never report ``refreshed``, and seeding an empty
# lab reports ``refreshed`` rather than ``still_pending``.
_SYSTEM_SEVERITY = {
    status: len(AUTONOMY_SUPERVISOR_SYSTEM_STATUSES) - index
    for index, status in enumerate(AUTONOMY_SUPERVISOR_SYSTEM_STATUSES)
}

# A system in one of these states needs no further attention this cycle. Stated
# against the exported vocabulary above; an unlisted status is not converged,
# which is the fail-closed direction.
_CONVERGED_STATES = frozenset({SYSTEM_NOMINAL, SYSTEM_WAITING})


def build_self_refresh_cycle(
    config: AutonomySupervisorConfig,
    *,
    apply: bool = False,
    allow_empty_lab: bool = False,
    environ: Mapping[str, str] | None = None,
    runner=None,
) -> dict[str, object]:
    """Run one deterministic observe -> decide -> act -> re-observe cycle."""

    if type(config) is not AutonomySupervisorConfig:
        raise ValidationError("config must be an AutonomySupervisorConfig.")
    if type(apply) is not bool:
        raise ValidationError("apply must be a bool.")
    if type(allow_empty_lab) is not bool:
        raise ValidationError("allow_empty_lab must be a bool.")

    # ``allow_empty_lab`` is forwarded so the two observations agree with the
    # cycle's own declaration instead of computing their rollup booleans as if
    # the caller had never made it. Output-neutral today - ``_report_summary``
    # projects neither ``evidence_required`` nor ``system_attention_required``,
    # and neither the plan nor the ledger reads them - but it keeps the
    # inconsistency from surfacing if that projection ever grows.
    before = build_autonomy_supervisor_report(config, allow_empty_lab=allow_empty_lab)
    plan = build_autonomy_next_plan_from_report(before)
    ledger = build_offline_execution_ledger(
        config,
        apply=apply,
        plan_report=plan,
        environ=environ,
        runner=runner,
    )
    after = build_autonomy_supervisor_report(config, allow_empty_lab=allow_empty_lab)

    before_status = str(before["system_status"])
    after_status = str(after["system_status"])
    execution_count = int(ledger["execution_count"])
    # V5.44: the ledger's all_executions_succeeded is tri-state (bool | None);
    # forward it verbatim rather than coercing None to False, which would
    # turn "not applicable, nothing ran" into a false failure claim.
    all_succeeded = ledger["all_executions_succeeded"]

    outcome = _classify_outcome(
        apply=apply,
        execution_count=execution_count,
        all_succeeded=all_succeeded,
        before_status=before_status,
        after_status=after_status,
        allow_empty_lab=allow_empty_lab,
    )
    evidence_required = (
        after_status == SYSTEM_NO_LANE_EVIDENCE and not allow_empty_lab
    )
    converged = after_status in _CONVERGED_STATES or (
        after_status == SYSTEM_NO_LANE_EVIDENCE and allow_empty_lab
    )

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": before["run_id"],
        "as_of": before["as_of"],
        "lanes_root": before["lanes_root"],
        "labels": list(AUTONOMY_SELF_REFRESH_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "apply": apply,
        "dry_run": not apply,
        "allow_empty_lab": allow_empty_lab,
        "evidence_required": evidence_required,
        "before_system_status": before_status,
        "before_plan_class": str(plan["plan_class"]),
        "eligible_count": int(ledger["eligible_count"]),
        "execution_count": execution_count,
        "all_executions_succeeded": all_succeeded,
        "after_system_status": after_status,
        "cycle_outcome": outcome,
        "converged": converged,
        "before_report": _report_summary(before),
        "plan_summary": {
            "plan_class": str(plan["plan_class"]),
            "next_offline_action_lane": str(plan["next_offline_action_lane"]),
            "operator_gated_lanes": _string_list(plan.get("operator_gated_lanes")),
        },
        "execution_ledger": ledger,
        "after_report": _report_summary(after),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _classify_outcome(
    *,
    apply: bool,
    execution_count: int,
    all_succeeded: bool | None,
    before_status: str,
    after_status: str,
    allow_empty_lab: bool = False,
) -> str:
    if after_status == SYSTEM_NO_LANE_EVIDENCE and not allow_empty_lab:
        return OUTCOME_EVIDENCE_REQUIRED
    if not apply:
        return OUTCOME_DRY_RUN_PREVIEW
    if execution_count == 0:
        return OUTCOME_NOOP_NO_ACTION
    # execution_count > 0 guarantees a real bool by producer contract (V5.44);
    # `is not True` fails closed to execution_failed rather than treating an
    # unexpected None as success if that contract is ever violated.
    if all_succeeded is not True:
        return OUTCOME_EXECUTION_FAILED
    if _system_rank(after_status) < _system_rank(before_status):
        return OUTCOME_REFRESHED
    return OUTCOME_STILL_PENDING


def _system_rank(status: str) -> int:
    """Return the severity rank of one system status, or fail closed.

    Refusing an unrankable status is the same choice the planner's
    ``_required_state`` makes: defaulting would let an unranked status silently
    decide whether the cycle claims it refreshed the system.
    """

    rank = _SYSTEM_SEVERITY.get(status)
    if rank is None:
        raise ValidationError(
            f"system_status must be a supervisor system status: {status}"
        )
    return rank


def _report_summary(report: Mapping[str, object]) -> dict[str, object]:
    return {
        "system_status": str(report.get("system_status", "")),
        "recommended_next_action": str(report.get("recommended_next_action", "")),
        "recommended_next_action_lane": str(
            report.get("recommended_next_action_lane", "")
        ),
        "blocked_lanes": _string_list(report.get("blocked_lanes")),
        "attention_lanes": _string_list(report.get("attention_lanes")),
        "stale_lanes": _string_list(report.get("stale_lanes")),
        "waiting_lanes": _string_list(report.get("waiting_lanes")),
        "nominal_lanes": _string_list(report.get("nominal_lanes")),
        "absent_lanes": _string_list(report.get("absent_lanes")),
    }


def render_self_refresh_cycle_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_self_refresh_cycle_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable self-refresh cycle summary."""

    lines = [
        "Offline autonomy self-refresh cycle",
        f"run_id: {payload.get('run_id', '')}",
        f"as_of: {payload.get('as_of', '')}",
        f"apply: {_bool_text(payload.get('apply'))}",
        f"allow_empty_lab: {_bool_text(payload.get('allow_empty_lab'))}",
        f"before_system_status: {payload.get('before_system_status', '')}",
        f"eligible_count: {payload.get('eligible_count', 0)}",
        f"execution_count: {payload.get('execution_count', 0)}",
        f"all_executions_succeeded: {_tri_bool_text(payload.get('all_executions_succeeded'))}",
        f"after_system_status: {payload.get('after_system_status', '')}",
        f"cycle_outcome: {payload.get('cycle_outcome', '')}",
        f"evidence_required: {_bool_text(payload.get('evidence_required'))}",
        f"converged: {_bool_text(payload.get('converged'))}",
    ]
    after = payload.get("after_report")
    if isinstance(after, Mapping):
        lines.append(
            "after_stale_lanes: "
            f"{_joined(_string_list(after.get('stale_lanes')))}"
        )
        lines.append(
            "after_attention_lanes: "
            f"{_joined(_string_list(after.get('attention_lanes')))}"
        )
    lines.extend(
        (
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"broker_action_performed: {_bool_text(payload.get('broker_action_performed'))}",
            f"network_access_attempted: {_bool_text(payload.get('network_access_attempted'))}",
            f"credential_access_attempted: {_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )
    return "\n".join(lines)


def write_self_refresh_cycle_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> dict[str, object]:
    """Write exactly one JSONL cycle record, replacing any prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_self_refresh_cycle_json(payload) + "\n"
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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    return [str(item) for item in value if str(item)]


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
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
