"""Offline autonomy next-action planner over the cross-lane supervisor report.

The V5.37 cross-lane supervisor (:mod:`algotrader.execution.autonomy_supervisor`)
answers *what state is each autonomy lane in* and emits one abstract
``recommended_next_action`` token per lane. It deliberately never maps those
tokens to a runnable command and never distinguishes an action that can be run
inside the offline envelope from one that is blocked on the operator.

This module closes that observe/act gap without crossing it. It consumes a
supervisor report and, for each lane, classifies the lane's declared
``recommended_next_action`` token against a frozen classification registry into
a concrete plan: the exact offline command to run (when one exists), the
operator-supplied inputs it still requires, its preconditions, and — when no
offline path exists — the specific operator gate that blocks autonomous
progress. It then aggregates one whole-system plan naming the single
highest-leverage offline-runnable action and the full set of operator-gated
actions.

It is a read-only reporting/planning surface with the exact same safety profile
as the supervisor. It loads no runtime profile, inspects no credential, imports
no broker SDK, opens no socket, reads no wall clock, spawns no subprocess, and
performs and exposes no submit/cancel/replace/close/liquidation/paper-mutation/
capital/live path. It *plans* commands; it never executes them. Autonomous
(unattended) execution of even an offline command is a distinct authority
expansion reserved for the operator and is out of scope here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.autonomy_supervisor import (
    ALL_LANES_ABSENT_ACTION,
    AUTONOMY_SUPERVISOR_LANES,
    AutonomySupervisorConfig,
    STATE_ABSENT,
    STATE_ATTENTION,
    STATE_BLOCKED,
    STATE_NOMINAL,
    STATE_STALE,
    STATE_UNKNOWN,
    STATE_WAITING,
    build_autonomy_supervisor_report,
)

__all__ = [
    "AUTONOMY_NEXT_PLAN_LABELS",
    "AUTONOMY_ACTION_CLASSIFICATION",
    "ActionClass",
    "AutonomyNextPlanWriteResult",
    "EXECUTION_AUTO_OFFLINE",
    "EXECUTION_NOOP",
    "EXECUTION_OFFLINE_OPERATOR_INPUT",
    "EXECUTION_OPERATOR_GATED",
    "PLAN_ALL_NOMINAL_OR_WAITING",
    "PLAN_OFFLINE_ACTION_AVAILABLE",
    "PLAN_OPERATOR_AUTHORITY_REQUIRED",
    "build_autonomy_next_plan",
    "build_autonomy_next_plan_from_report",
    "classify_action",
    "render_autonomy_next_plan_json",
    "render_autonomy_next_plan_text",
    "write_autonomy_next_plan_jsonl",
]


_MILESTONE = "V5.38 - Offline autonomy next-action planner"
_RECORD_TYPE = "autonomy_next_plan"
_COMMAND = "autonomy-next-plan"
_PROFIT_CLAIM = "none"

AUTONOMY_NEXT_PLAN_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

# Execution classes, ordered here from most to least autonomous progress.
EXECUTION_AUTO_OFFLINE = "auto_offline"
EXECUTION_OFFLINE_OPERATOR_INPUT = "offline_operator_input"
EXECUTION_OPERATOR_GATED = "operator_gated"
EXECUTION_NOOP = "noop"

_EXECUTION_CLASSES = frozenset(
    {
        EXECUTION_AUTO_OFFLINE,
        EXECUTION_OFFLINE_OPERATOR_INPUT,
        EXECUTION_OPERATOR_GATED,
        EXECUTION_NOOP,
    }
)

_OFFLINE_RUNNABLE_CLASSES = frozenset(
    {EXECUTION_AUTO_OFFLINE, EXECUTION_OFFLINE_OPERATOR_INPUT}
)

# Whole-system plan classifications.
PLAN_OFFLINE_ACTION_AVAILABLE = "offline_action_available"
PLAN_OPERATOR_AUTHORITY_REQUIRED = "operator_authority_required"
PLAN_ALL_NOMINAL_OR_WAITING = "all_nominal_or_waiting"

# Supervisor normalized-state severity, most to least severe. Reused to pick the
# highest-leverage offline-runnable lane and break ties toward attention.
_STATE_SEVERITY = (
    STATE_BLOCKED,
    STATE_UNKNOWN,
    STATE_ATTENTION,
    STATE_STALE,
    STATE_WAITING,
    STATE_NOMINAL,
    STATE_ABSENT,
)

# Gate vocabulary. A non-empty gate names the single blocker that stops the
# system from advancing this lane autonomously right now.
_GATE_UNATTENDED_EXECUTION = "unattended_execution_authority"
_GATE_OPERATOR_INPUTS = "operator_supplied_inputs"
_GATE_NETWORK_MARKET_DATA = "network_market_data_fetch"
_GATE_BROKER_OBSERVATION = "broker_observation"
_GATE_OPERATOR_REVIEW = "operator_review"
_GATE_TASK_SCHEDULER = "task_scheduler_health"
_GATE_NO_OFFLINE_COMMAND = "no_offline_command_available"
_GATE_UNCLASSIFIED = "unclassified_action_operator_review"


@dataclass(frozen=True, slots=True)
class ActionClass:
    """Frozen classification of one supervisor ``recommended_next_action`` token.

    ``command`` is the exact offline command a caller (or the operator) may run
    to advance the lane; it is empty when no offline command exists.
    ``required_operator_inputs`` lists the operator-supplied arguments the
    command still needs. ``gate`` names the single blocker to autonomous
    progress and is empty only for :data:`EXECUTION_NOOP`.
    """

    execution_class: str
    offline_runnable: bool
    gate: str
    gate_detail: str
    command: str = ""
    required_operator_inputs: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.execution_class not in _EXECUTION_CLASSES:
            raise ValidationError("execution_class must be a supported class.")
        if type(self.offline_runnable) is not bool:
            raise ValidationError("offline_runnable must be a bool.")
        expected_runnable = self.execution_class in _OFFLINE_RUNNABLE_CLASSES
        if self.offline_runnable is not expected_runnable:
            raise ValidationError(
                "offline_runnable must match the execution_class contract."
            )
        if self.execution_class == EXECUTION_NOOP:
            if self.gate != "":
                raise ValidationError("noop actions must not declare a gate.")
        elif self.gate == "":
            raise ValidationError("non-noop actions must declare a gate.")
        if self.offline_runnable and self.command == "":
            raise ValidationError("offline-runnable actions must carry a command.")
        if not self.offline_runnable and self.command != "":
            raise ValidationError(
                "only offline-runnable actions may carry a command."
            )
        object.__setattr__(
            self, "required_operator_inputs", tuple(self.required_operator_inputs)
        )
        object.__setattr__(self, "preconditions", tuple(self.preconditions))

    def to_dict(self) -> dict[str, object]:
        return {
            "execution_class": self.execution_class,
            "offline_runnable": self.offline_runnable,
            "gate": self.gate,
            "gate_detail": self.gate_detail,
            "command": self.command,
            "required_operator_inputs": list(self.required_operator_inputs),
            "preconditions": list(self.preconditions),
        }


def _noop(gate_detail: str) -> ActionClass:
    return ActionClass(
        execution_class=EXECUTION_NOOP,
        offline_runnable=False,
        gate="",
        gate_detail=gate_detail,
    )


def _operator_gated(gate: str, gate_detail: str) -> ActionClass:
    return ActionClass(
        execution_class=EXECUTION_OPERATOR_GATED,
        offline_runnable=False,
        gate=gate,
        gate_detail=gate_detail,
    )


# Exact offline commands for the only lane that today exposes an offline daily
# cycle chain. Both underlying modules were verified to import no network,
# broker, credential, or profile surface; the planner records the command as
# data and never runs it.
_OFFLINE_DAILY_CYCLE_SEED_COMMAND = (
    "python -m algotrader.cli etf-sma-offline-daily-cycle-run"
    " --validated-at <OPERATOR_ISO8601_UTC_DAILY_CHAIN_CLOCK>"
    " --daily-bars-csv <OPERATOR_LOCAL_ADJUSTED_SPY_DAILY_BARS_CSV>"
    " --readiness-output-jsonl runs/paper_lab/m441_unified_cycle_readiness_packet.jsonl"
    " --validation-output-jsonl runs/paper_lab/m442_offline_daily_cycle_validation.jsonl"
    " --summary-output-jsonl runs/paper_lab/m443_offline_daily_cycle_summary.jsonl"
    " --manifest-output-jsonl runs/paper_lab/m444_offline_daily_cycle_run.jsonl"
)
_OFFLINE_DAILY_CYCLE_RERUN_COMMAND = (
    "python -m algotrader.cli etf-sma-offline-daily-cycle-rerun-m446"
)


# Frozen classification of every ``recommended_next_action`` token the frozen
# supervisor lane registry can emit. A token absent from this map fails closed
# to an operator-review gate; ``test_every_supervisor_action_is_classified``
# proves full coverage so a new lane action cannot silently degrade the plan.
AUTONOMY_ACTION_CLASSIFICATION: dict[str, ActionClass] = {
    # --- Healthy: nominal or healthily-waiting lanes; nothing to run. ---
    "unattended_market_data_soak_proven_continue_cadence": _noop(
        "market-data soak proven; continue the existing read-only cadence."
    ),
    "continue_scheduled_read_only_market_data_refresh_cadence": _noop(
        "lane waiting healthily on the scheduled read-only refresh cadence."
    ),
    "observe_hold_noop_continue_offline_daily_cycle": _noop(
        "offline daily cycle accepted at observe/hold/noop; continue."
    ),
    "await_next_offline_daily_cycle_input": _noop(
        "offline daily cycle waiting on its next input; nothing to run."
    ),
    "r1_deterministic_readiness_proven_continue": _noop(
        "R1 deterministic readiness proven; continue."
    ),
    "await_supervised_readiness_trial_inputs": _noop(
        "supervised readiness trial waiting on inputs; nothing to run."
    ),
    "continue_forward_shadow_cadence": _noop(
        "forward-shadow cycle nominal; continue the cadence."
    ),
    "await_tournament_terminal_or_next_shadow_window": _noop(
        "forward-shadow waiting on tournament terminal or next window."
    ),
    "continue_bounded_paper_probe_review_cadence": _noop(
        "bounded paper-probe review nominal; continue the cadence."
    ),
    "await_v5_25_terminal_evidence": _noop(
        "bounded paper-probe review waiting on V5.25 terminal evidence."
    ),
    "continue_capability_production_cadence": _noop(
        "capability production nominal; continue the cadence."
    ),
    "await_v5_25_terminal_winner": _noop(
        "capability production waiting on the V5.25 terminal winner."
    ),
    # --- Offline-runnable: the SPY offline daily cycle chain. ---
    "run_offline_daily_cycle_chain_to_seed_evidence": ActionClass(
        execution_class=EXECUTION_OFFLINE_OPERATOR_INPUT,
        offline_runnable=True,
        gate=_GATE_OPERATOR_INPUTS,
        gate_detail=(
            "offline command exists but needs an operator-supplied daily chain "
            "clock and a local adjusted SPY daily-bars CSV."
        ),
        command=_OFFLINE_DAILY_CYCLE_SEED_COMMAND,
        required_operator_inputs=(
            "--validated-at: timezone-aware ISO-8601 daily chain clock",
            "--daily-bars-csv: local adjusted SPY daily-bars CSV path",
        ),
    ),
    "rerun_offline_daily_cycle_chain": ActionClass(
        execution_class=EXECUTION_AUTO_OFFLINE,
        offline_runnable=True,
        gate=_GATE_UNATTENDED_EXECUTION,
        gate_detail=(
            "fully-defaulted offline command that reproduces the pinned M446/M447 "
            "milestone result; only unattended execution authority remains."
        ),
        command=_OFFLINE_DAILY_CYCLE_RERUN_COMMAND,
        preconditions=(
            "the exact pinned M446 canonical CSV (sha256 408fd46...db69, latest "
            "bar date 2026-06-08) present at "
            "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv",
        ),
        # This command is a milestone reproduction, not a refresh: the module
        # hard-pins the expected latest bar date to 2026-06-08 and writes the
        # M447 manifest, never the m444 artifact the daily-cycle lane reads. It
        # therefore cannot cure daily-cycle staleness; that routes to
        # ``operator_refresh_offline_daily_cycle_inputs`` instead.
    ),
    "operator_refresh_offline_daily_cycle_inputs": ActionClass(
        execution_class=EXECUTION_OPERATOR_GATED,
        offline_runnable=False,
        gate=_GATE_OPERATOR_INPUTS,
        gate_detail=(
            "stale daily-cycle evidence means the underlying daily bars are old; "
            "curing it needs an operator-supplied refreshed adjusted SPY "
            "daily-bars CSV and daily chain clock, then a reseed of the chain "
            "via etf-sma-offline-daily-cycle-run. No allowlisted offline command "
            "writes this lane's artifact."
        ),
        required_operator_inputs=(
            "--validated-at: timezone-aware ISO-8601 daily chain clock",
            "--daily-bars-csv: refreshed local adjusted SPY daily-bars CSV path",
        ),
    ),
    # --- Operator-gated: market-data fetch (network). ---
    "run_authorized_read_only_market_data_refresh_to_seed_soak": _operator_gated(
        _GATE_NETWORK_MARKET_DATA,
        "seeding the soak needs an authorized read-only market-data fetch "
        "(network); outside the offline envelope.",
    ),
    "authorized_read_only_market_data_fetch_for_shadow_window": _operator_gated(
        _GATE_NETWORK_MARKET_DATA,
        "advancing the shadow window needs an authorized read-only market-data "
        "fetch (network); outside the offline envelope.",
    ),
    # --- Operator-gated: scheduled-task health. ---
    "operator_check_scheduled_market_data_refresh_task_health": _operator_gated(
        _GATE_TASK_SCHEDULER,
        "stale soak implies the operator must check the scheduled refresh "
        "task's health.",
    ),
    # --- Operator-gated: read-only operator review. ---
    "operator_review_latest_failed_market_data_session_read_only": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must read-only review the latest failed market-data session.",
    ),
    "operator_review_market_data_soak_evidence": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the market-data soak evidence.",
    ),
    "operator_review_blocked_offline_daily_cycle_chain": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the blocked offline daily cycle chain.",
    ),
    "operator_review_offline_daily_cycle_chain": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the offline daily cycle chain.",
    ),
    "operator_review_blocked_readiness_trial": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the blocked supervised readiness trial.",
    ),
    "operator_review_readiness_trial": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the supervised readiness trial.",
    ),
    "operator_review_blocked_forward_shadow_cycle": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the blocked forward-shadow cycle.",
    ),
    "operator_review_forward_shadow_cycle": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the forward-shadow cycle.",
    ),
    "operator_review_operational_evidence_blockers_read_only": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must read-only review the operational-evidence blockers.",
    ),
    "operator_review_only_no_paper_mutation_authorized": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator-review only; no paper mutation is authorized.",
    ),
    "operator_review_bounded_paper_probe_review": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the bounded paper-probe review.",
    ),
    "operator_review_blocked_capability_production": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the blocked capability production.",
    ),
    "operator_review_capability_production": _operator_gated(
        _GATE_OPERATOR_REVIEW,
        "operator must review the capability production.",
    ),
    # --- Operator-gated: no offline command exists to seed/rerun the lane. ---
    "rerun_supervised_readiness_trial": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command reruns the supervised readiness trial; operator "
        "must drive it.",
    ),
    "run_supervised_readiness_trial_to_seed_r1_evidence": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command seeds the supervised readiness trial; operator "
        "must drive it.",
    ),
    "rerun_forward_shadow_status": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command reruns the forward-shadow status; operator must "
        "drive it.",
    ),
    "run_forward_shadow_status_to_seed_evidence": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command seeds the forward-shadow status; operator must "
        "drive it.",
    ),
    "rerun_bounded_paper_probe_review": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command reruns the bounded paper-probe review; operator "
        "must drive it.",
    ),
    "run_bounded_paper_probe_review_to_seed_evidence": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command seeds the bounded paper-probe review; operator "
        "must drive it.",
    ),
    "rerun_capability_production": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command reruns capability production; operator must drive "
        "it.",
    ),
    "run_capability_production_to_seed_evidence": _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "no offline command seeds capability production; operator must drive "
        "it.",
    ),
    # --- Aggregate action the supervisor emits when every lane is absent. ---
    ALL_LANES_ABSENT_ACTION: _operator_gated(
        _GATE_NO_OFFLINE_COMMAND,
        "all lanes absent; per-lane seeding is operator-driven.",
    ),
}


def classify_action(recommended_action: str) -> ActionClass:
    """Classify one supervisor action token, failing closed to operator review."""

    token = _required_string(recommended_action, "recommended_action")
    classified = AUTONOMY_ACTION_CLASSIFICATION.get(token)
    if classified is not None:
        return classified
    return ActionClass(
        execution_class=EXECUTION_OPERATOR_GATED,
        offline_runnable=False,
        gate=_GATE_UNCLASSIFIED,
        gate_detail=(
            "unclassified recommended action; operator must review the lane "
            "evidence before any autonomous progress."
        ),
    )


@dataclass(frozen=True, slots=True)
class AutonomyNextPlanWriteResult:
    """Local JSONL write metadata for a single next-plan record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_actions_performed: bool
    network_access_attempted: bool
    credential_access_attempted: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if self.newline_terminated is not True:
            raise ValidationError("newline_terminated must be true.")
        for field_name in (
            "submitted",
            "mutated",
            "broker_action_performed",
            "broker_actions_performed",
            "network_access_attempted",
            "credential_access_attempted",
            "live_authorized",
        ):
            if getattr(self, field_name) is not False:
                raise ValidationError(f"{field_name} must be false.")

    def to_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "record_count": self.record_count,
            "bytes_written": self.bytes_written,
            "newline_terminated": self.newline_terminated,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


def build_autonomy_next_plan(config: AutonomySupervisorConfig) -> dict[str, object]:
    """Build one offline autonomy next-action plan from local lane evidence."""

    if type(config) is not AutonomySupervisorConfig:
        raise ValidationError("config must be an AutonomySupervisorConfig.")
    supervisor_report = build_autonomy_supervisor_report(config)
    return build_autonomy_next_plan_from_report(supervisor_report)


def build_autonomy_next_plan_from_report(
    supervisor_report: Mapping[str, object],
) -> dict[str, object]:
    """Build one plan from an already-built cross-lane supervisor report."""

    report = _supervisor_report(supervisor_report)
    lane_summaries = _report_lanes(report)

    actions: list[dict[str, object]] = []
    for summary in lane_summaries:
        actions.append(_plan_lane(summary))

    offline_lanes = [
        str(action["lane_id"])
        for action in actions
        if action["offline_runnable"] is True
    ]
    gated_lanes = [
        str(action["lane_id"])
        for action in actions
        if action["execution_class"] == EXECUTION_OPERATOR_GATED
    ]
    noop_lanes = [
        str(action["lane_id"])
        for action in actions
        if action["execution_class"] == EXECUTION_NOOP
    ]

    next_offline = _highest_priority_action(
        actions, lambda action: action["offline_runnable"] is True
    )
    plan_class = _plan_class(offline_lanes, gated_lanes)

    operator_gated_actions = [
        {
            "lane_id": action["lane_id"],
            "recommended_action": action["recommended_action"],
            "gate": action["gate"],
            "gate_detail": action["gate_detail"],
        }
        for action in actions
        if action["execution_class"] == EXECUTION_OPERATOR_GATED
    ]

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": report["run_id"],
        "as_of": report["as_of"],
        "lanes_root": report["lanes_root"],
        "labels": list(AUTONOMY_NEXT_PLAN_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "supervisor_system_status": report["system_status"],
        "supervisor_recommended_action": report["recommended_next_action"],
        "supervisor_recommended_action_lane": report[
            "recommended_next_action_lane"
        ],
        "lane_count": len(actions),
        "actions": actions,
        "plan_class": plan_class,
        "next_offline_action_lane": (
            str(next_offline["lane_id"]) if next_offline else ""
        ),
        "next_offline_action": next_offline,
        "offline_runnable_lanes": offline_lanes,
        "operator_gated_lanes": gated_lanes,
        "noop_lanes": noop_lanes,
        "operator_gated_actions": operator_gated_actions,
        "operator_summary": _operator_summary(
            plan_class, next_offline, gated_lanes
        ),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _plan_lane(summary: Mapping[str, object]) -> dict[str, object]:
    lane_id = _required_string(summary.get("lane_id"), "lane_id")
    normalized_state = _required_string(
        summary.get("normalized_state"), "normalized_state"
    )
    recommended_action = _required_string(
        summary.get("next_action"), "next_action"
    )
    classified = classify_action(recommended_action)
    return {
        "lane_id": lane_id,
        "title": _text(summary.get("title")),
        "category": _text(summary.get("category")),
        "normalized_state": normalized_state,
        "recommended_action": recommended_action,
        "execution_class": classified.execution_class,
        "offline_runnable": classified.offline_runnable,
        "command": classified.command,
        "required_operator_inputs": list(classified.required_operator_inputs),
        "preconditions": list(classified.preconditions),
        "gate": classified.gate,
        "gate_detail": classified.gate_detail,
        "blockers": _string_list(summary.get("blockers")),
    }


def _highest_priority_action(
    actions: list[dict[str, object]],
    predicate,
) -> dict[str, object] | None:
    for state in _STATE_SEVERITY:
        for action in actions:
            if action["normalized_state"] == state and predicate(action):
                return action
    return None


def _plan_class(offline_lanes: list[str], gated_lanes: list[str]) -> str:
    if offline_lanes:
        return PLAN_OFFLINE_ACTION_AVAILABLE
    if gated_lanes:
        return PLAN_OPERATOR_AUTHORITY_REQUIRED
    return PLAN_ALL_NOMINAL_OR_WAITING


def _operator_summary(
    plan_class: str,
    next_offline: dict[str, object] | None,
    gated_lanes: list[str],
) -> str:
    if plan_class == PLAN_ALL_NOMINAL_OR_WAITING:
        return (
            "All lanes are nominal or healthily waiting; no next action is "
            "pending."
        )
    if plan_class == PLAN_OFFLINE_ACTION_AVAILABLE and next_offline is not None:
        gated = len(gated_lanes)
        return (
            f"Next offline action on lane {next_offline['lane_id']}: run "
            f"`{next_offline['command']}` "
            f"(gate: {next_offline['gate']}). "
            f"{gated} further lane(s) are gated on the operator."
        )
    return (
        f"No offline action is available; {len(gated_lanes)} lane(s) are gated "
        "on the operator (review, network market-data fetch, scheduled-task "
        "health, or a missing offline command)."
    )


def render_autonomy_next_plan_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_autonomy_next_plan_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable next-action plan summary."""

    lines = [
        "Offline autonomy next-action plan",
        f"run_id: {payload.get('run_id', '')}",
        f"as_of: {payload.get('as_of', '')}",
        f"supervisor_system_status: {payload.get('supervisor_system_status', '')}",
        f"plan_class: {payload.get('plan_class', '')}",
        f"next_offline_action_lane: {payload.get('next_offline_action_lane', '')}",
        "actions:",
    ]
    for action in _mapping_list(payload.get("actions")):
        inputs = _joined(_string_list(action.get("required_operator_inputs")))
        lines.append(
            "  - "
            f"{action.get('lane_id', '')}: {action.get('normalized_state', '')}"
            f" | class={action.get('execution_class', '')}"
            f" | offline_runnable={_bool_text(action.get('offline_runnable'))}"
            f" | gate={action.get('gate', '') or 'none'}"
            f" | inputs={inputs}"
        )
        command = _text(action.get("command"))
        if command:
            lines.append(f"      command: {command}")
    lines.extend(
        (
            f"operator_summary: {payload.get('operator_summary', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"broker_action_performed: {_bool_text(payload.get('broker_action_performed'))}",
            f"network_access_attempted: {_bool_text(payload.get('network_access_attempted'))}",
            f"credential_access_attempted: {_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )
    return "\n".join(lines)


def write_autonomy_next_plan_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> AutonomyNextPlanWriteResult:
    """Write exactly one JSONL plan record, replacing any prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_autonomy_next_plan_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return AutonomyNextPlanWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _supervisor_report(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError("supervisor_report must be a mapping.")
    if value.get("record_type") != "autonomy_supervisor_report":
        raise ValidationError(
            "supervisor_report must be an autonomy_supervisor_report record."
        )
    for key in (
        "run_id",
        "as_of",
        "lanes_root",
        "system_status",
        "recommended_next_action",
        "recommended_next_action_lane",
    ):
        if key not in value:
            raise ValidationError(f"supervisor_report is missing '{key}'.")
    return value


def _report_lanes(report: Mapping[str, object]) -> list[Mapping[str, object]]:
    lanes = report.get("lanes")
    if not isinstance(lanes, list):
        raise ValidationError("supervisor_report['lanes'] must be a list.")
    known = {lane.lane_id for lane in AUTONOMY_SUPERVISOR_LANES}
    resolved: list[Mapping[str, object]] = []
    for lane in lanes:
        if not isinstance(lane, Mapping):
            raise ValidationError(
                "supervisor_report['lanes'] items must be mappings."
            )
        lane_id = _text(lane.get("lane_id"))
        if lane_id not in known:
            raise ValidationError(f"unknown lane id in report: {lane_id}")
        resolved.append(lane)
    return resolved


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


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
