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
    AutonomySupervisorConfig,
    SYSTEM_ATTENTION,
    SYSTEM_BLOCKED,
    SYSTEM_NOMINAL,
    SYSTEM_NO_LANE_EVIDENCE,
    SYSTEM_WAITING,
    build_autonomy_supervisor_report,
)

__all__ = [
    "AUTONOMY_SELF_REFRESH_LABELS",
    "OUTCOME_DRY_RUN_PREVIEW",
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
OUTCOME_NOOP_NO_ACTION = "noop_no_action"
OUTCOME_REFRESHED = "refreshed"
OUTCOME_STILL_PENDING = "still_pending"
OUTCOME_EXECUTION_FAILED = "execution_failed"

# System-status severity, most to least severe. Used only to decide whether the
# act phase reduced overall severity (a genuine refresh).
_SYSTEM_SEVERITY = {
    SYSTEM_BLOCKED: 4,
    SYSTEM_ATTENTION: 3,
    SYSTEM_WAITING: 2,
    SYSTEM_NOMINAL: 1,
    SYSTEM_NO_LANE_EVIDENCE: 0,
}

# A system in one of these states needs no further attention this cycle.
_CONVERGED_STATES = frozenset({SYSTEM_NOMINAL, SYSTEM_WAITING, SYSTEM_NO_LANE_EVIDENCE})


def build_self_refresh_cycle(
    config: AutonomySupervisorConfig,
    *,
    apply: bool = False,
    environ: Mapping[str, str] | None = None,
    runner=None,
) -> dict[str, object]:
    """Run one deterministic observe -> decide -> act -> re-observe cycle."""

    if type(config) is not AutonomySupervisorConfig:
        raise ValidationError("config must be an AutonomySupervisorConfig.")
    if type(apply) is not bool:
        raise ValidationError("apply must be a bool.")

    before = build_autonomy_supervisor_report(config)
    plan = build_autonomy_next_plan_from_report(before)
    ledger = build_offline_execution_ledger(
        config,
        apply=apply,
        plan_report=plan,
        environ=environ,
        runner=runner,
    )
    after = build_autonomy_supervisor_report(config)

    before_status = str(before["system_status"])
    after_status = str(after["system_status"])
    execution_count = int(ledger["execution_count"])
    all_succeeded = bool(ledger["all_executions_succeeded"])

    outcome = _classify_outcome(
        apply=apply,
        execution_count=execution_count,
        all_succeeded=all_succeeded,
        before_status=before_status,
        after_status=after_status,
    )
    converged = after_status in _CONVERGED_STATES

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
    all_succeeded: bool,
    before_status: str,
    after_status: str,
) -> str:
    if not apply:
        return OUTCOME_DRY_RUN_PREVIEW
    if execution_count == 0:
        return OUTCOME_NOOP_NO_ACTION
    if not all_succeeded:
        return OUTCOME_EXECUTION_FAILED
    before_rank = _SYSTEM_SEVERITY.get(before_status, 0)
    after_rank = _SYSTEM_SEVERITY.get(after_status, 0)
    if after_rank < before_rank:
        return OUTCOME_REFRESHED
    return OUTCOME_STILL_PENDING


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
        f"before_system_status: {payload.get('before_system_status', '')}",
        f"eligible_count: {payload.get('eligible_count', 0)}",
        f"execution_count: {payload.get('execution_count', 0)}",
        f"all_executions_succeeded: {_bool_text(payload.get('all_executions_succeeded'))}",
        f"after_system_status: {payload.get('after_system_status', '')}",
        f"cycle_outcome: {payload.get('cycle_outcome', '')}",
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
