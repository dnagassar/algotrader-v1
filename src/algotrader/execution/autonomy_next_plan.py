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
capital/live path. It *plans* commands; it never executes them. The readiness
replay action has standing offline authority, but remains controlled by exact
allowlisting, canonical-target validation, executor preflight, and the
executor's explicit ``--apply`` switch.
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
    AUTONOMY_SUPERVISOR_STATES,
    AutonomySupervisorConfig,
    build_autonomy_supervisor_report,
)

__all__ = [
    "AUTONOMY_NEXT_PLAN_LABELS",
    "AUTONOMY_ACTION_CLASSIFICATION",
    "ActionClass",
    "AutonomyNextPlanWriteResult",
    "CANONICAL_LANES_ROOT_RELPATH",
    "CANONICAL_READINESS_PACKET_RELPATH",
    "CANONICAL_REPLAY_ARGV",
    "EXECUTION_AUTO_OFFLINE",
    "EXECUTION_AUTHORIZED_NETWORK_READ_ONLY",
    "EXECUTION_NOOP",
    "EXECUTION_OFFLINE_OPERATOR_INPUT",
    "EXECUTION_OPERATOR_GATED",
    "PLAN_ALL_NOMINAL_OR_WAITING",
    "PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE",
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

CANONICAL_LANES_ROOT_RELPATH = Path("runs")
CANONICAL_READINESS_PACKET_RELPATH = Path(
    "runs/crypto_supervised_readiness_trial/latest/readiness_packet.json"
)
CANONICAL_REPLAY_ARGV = ("crypto-readiness-replay",)
_READINESS_LANE_ID = "crypto_supervised_readiness_trial"
_READINESS_ABSENT_ACTION = "run_supervised_readiness_trial_to_seed_r1_evidence"
_READINESS_STALE_ACTION = "rerun_supervised_readiness_trial"
_READINESS_REPLAY_COMMAND = "python -m algotrader.cli crypto-readiness-replay"

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
EXECUTION_AUTHORIZED_NETWORK_READ_ONLY = "authorized_network_read_only"

_EXECUTION_CLASSES = frozenset(
    {
        EXECUTION_AUTO_OFFLINE,
        EXECUTION_OFFLINE_OPERATOR_INPUT,
        EXECUTION_OPERATOR_GATED,
        EXECUTION_NOOP,
        EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
    }
)

_OFFLINE_RUNNABLE_CLASSES = frozenset(
    {EXECUTION_AUTO_OFFLINE, EXECUTION_OFFLINE_OPERATOR_INPUT}
)

# Plan rollup buckets. Every execution class maps to exactly one of these, and
# the mapping is checked against the class vocabulary at import time.
#
# Round-6 correction (finding F3). The V5.51a repair guarded the fourth
# recurrence of this defect class with a test that sampled three report
# fixtures, so a future class used only in a lane state no fixture exercises
# could still fall out of every bucket. Deriving the buckets from one total
# mapping — rather than from four independent comprehensions — makes that
# structurally impossible: a class added without a bucket fails at import,
# regardless of which lane states any test happens to construct.
BUCKET_OFFLINE_RUNNABLE = "offline_runnable_lanes"
BUCKET_AUTHORIZED_NETWORK = "authorized_network_lanes"
BUCKET_OPERATOR_GATED = "operator_gated_lanes"
BUCKET_NOOP = "noop_lanes"

PLAN_BUCKET_BY_EXECUTION_CLASS: dict[str, str] = {
    EXECUTION_AUTO_OFFLINE: BUCKET_OFFLINE_RUNNABLE,
    EXECUTION_OFFLINE_OPERATOR_INPUT: BUCKET_OFFLINE_RUNNABLE,
    EXECUTION_AUTHORIZED_NETWORK_READ_ONLY: BUCKET_AUTHORIZED_NETWORK,
    EXECUTION_OPERATOR_GATED: BUCKET_OPERATOR_GATED,
    EXECUTION_NOOP: BUCKET_NOOP,
}

if set(PLAN_BUCKET_BY_EXECUTION_CLASS) != set(_EXECUTION_CLASSES):
    raise ValidationError(
        "every execution class must map to exactly one plan bucket."
    )


def _bucket_lanes(actions: list[dict[str, object]]) -> dict[str, list[str]]:
    """Partition lanes across the plan buckets, total by construction."""

    buckets: dict[str, list[str]] = {
        BUCKET_OFFLINE_RUNNABLE: [],
        BUCKET_AUTHORIZED_NETWORK: [],
        BUCKET_OPERATOR_GATED: [],
        BUCKET_NOOP: [],
    }
    for action in actions:
        execution_class = str(action["execution_class"])
        # ActionClass already rejects any class outside the vocabulary, and the
        # import-time check above proves the vocabulary is fully mapped, so this
        # lookup cannot miss.
        buckets[PLAN_BUCKET_BY_EXECUTION_CLASS[execution_class]].append(
            str(action["lane_id"])
        )
    return buckets

# Whole-system plan classifications, ordered here from most to least autonomous
# progress. ``PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE`` exists because
# :data:`EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` is neither offline-runnable nor
# an operator blocker: without its own plan class such a lane would fall through
# every bucket and the plan would report ``all_nominal_or_waiting`` while a
# runnable, standing-authority action was pending.
PLAN_OFFLINE_ACTION_AVAILABLE = "offline_action_available"
PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE = "authorized_network_action_available"
PLAN_OPERATOR_AUTHORITY_REQUIRED = "operator_authority_required"
PLAN_ALL_NOMINAL_OR_WAITING = "all_nominal_or_waiting"

# Supervisor normalized-state severity, most to least severe. Used to pick the
# highest-leverage offline-runnable lane and break ties toward attention. This is
# the supervisor's own exported vocabulary rather than a local copy: a state the
# supervisor can emit but this tuple does not rank would be silently skipped by
# ``_highest_priority_action`` while still counting toward ``plan_class``.
_STATE_SEVERITY = AUTONOMY_SUPERVISOR_STATES

# Gate vocabulary. A non-empty gate names the single blocker that stops the
# system from advancing this lane autonomously right now. Auto-offline and noop
# actions have no gate.
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

    ``command`` is the exact command a caller (or the operator) may run to
    advance the lane; it is empty when no command exists (only offline-runnable
    actions and :data:`EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` may carry a
    non-empty command).
    ``required_operator_inputs`` lists the operator-supplied arguments the
    command still needs. ``gate`` names the single blocker to progress and is
    empty for :data:`EXECUTION_AUTO_OFFLINE` and :data:`EXECUTION_NOOP`.
    """

    execution_class: str
    offline_runnable: bool
    gate: str
    gate_detail: str
    command: str = ""
    required_operator_inputs: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "required_operator_inputs", tuple(self.required_operator_inputs)
        )
        object.__setattr__(self, "preconditions", tuple(self.preconditions))
        if self.execution_class not in _EXECUTION_CLASSES:
            raise ValidationError("execution_class must be a supported class.")
        if type(self.offline_runnable) is not bool:
            raise ValidationError("offline_runnable must be a bool.")
        expected_runnable = self.execution_class in _OFFLINE_RUNNABLE_CLASSES
        if self.offline_runnable is not expected_runnable:
            raise ValidationError(
                "offline_runnable must match the execution_class contract."
            )
        if self.execution_class in (EXECUTION_AUTO_OFFLINE, EXECUTION_NOOP):
            if self.gate != "":
                raise ValidationError(
                    "auto-offline and noop actions must not declare a gate."
                )
        elif self.gate == "":
            raise ValidationError(
                "operator-input and operator-gated actions must declare a gate."
            )
        if self.offline_runnable and self.command == "":
            raise ValidationError("offline-runnable actions must carry a command.")
        if (
            not self.offline_runnable
            and self.command != ""
            and self.execution_class != EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
        ):
            raise ValidationError(
                "only offline-runnable actions may carry a command."
            )
        if self.execution_class == EXECUTION_AUTO_OFFLINE:
            if self.required_operator_inputs:
                raise ValidationError(
                    "auto-offline actions must not require operator inputs."
                )
        if self.execution_class == EXECUTION_OFFLINE_OPERATOR_INPUT:
            if self.gate != _GATE_OPERATOR_INPUTS:
                raise ValidationError(
                    "offline operator-input actions must use the "
                    "operator_supplied_inputs gate."
                )
            if not self.required_operator_inputs:
                raise ValidationError(
                    "offline operator-input actions must require operator inputs."
                )

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


# Exact offline seed command for the SPY daily-cycle lane. It remains an
# operator-input action and is not executor-allowlisted.
_OFFLINE_DAILY_CYCLE_SEED_COMMAND = (
    "python -m algotrader.cli etf-sma-offline-daily-cycle-run"
    " --validated-at <OPERATOR_ISO8601_UTC_DAILY_CHAIN_CLOCK>"
    " --daily-bars-csv <OPERATOR_LOCAL_ADJUSTED_SPY_DAILY_BARS_CSV>"
    " --readiness-output-jsonl runs/paper_lab/m441_unified_cycle_readiness_packet.jsonl"
    " --validation-output-jsonl runs/paper_lab/m442_offline_daily_cycle_validation.jsonl"
    " --summary-output-jsonl runs/paper_lab/m443_offline_daily_cycle_summary.jsonl"
    " --manifest-output-jsonl runs/paper_lab/m444_offline_daily_cycle_run.jsonl"
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
    # --- Offline-runnable: operator-input SPY seed and auto crypto replay. ---
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
    _READINESS_ABSENT_ACTION: ActionClass(
        execution_class=EXECUTION_AUTO_OFFLINE,
        offline_runnable=True,
        gate="",
        gate_detail=(
            "standing offline authority applies; execution remains controlled by "
            "the exact allowlist, canonical-target validation, preflight, and the "
            "explicit executor --apply switch."
        ),
        command=_READINESS_REPLAY_COMMAND,
        required_operator_inputs=(),
        preconditions=(
            "executor credential/profile/network preflight passes",
            "crypto-readiness-replay import-purity and parser guards pass",
        ),
    ),
    _READINESS_STALE_ACTION: ActionClass(
        execution_class=EXECUTION_AUTO_OFFLINE,
        offline_runnable=True,
        gate="",
        gate_detail=(
            "standing offline authority applies; execution remains controlled by "
            "the exact allowlist, canonical-target validation, preflight, and the "
            "explicit executor --apply switch."
        ),
        command=_READINESS_REPLAY_COMMAND,
        required_operator_inputs=(),
        preconditions=(
            "executor credential/profile/network preflight passes",
            "crypto-readiness-replay import-purity and parser guards pass",
        ),
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
    # --- Authorized network read-only: market-data refresh. ---
    "run_authorized_read_only_market_data_refresh_to_seed_soak": ActionClass(
        execution_class=EXECUTION_AUTHORIZED_NETWORK_READ_ONLY,
        offline_runnable=False,
        gate=_GATE_NETWORK_MARKET_DATA,
        gate_detail=(
            "Standing authority granted for read-only market-data refresh; "
            "runnable via autonomy_read_only_network_executor."
        ),
        command=(
            "python -m algotrader.execution.autonomy_read_only_network_executor"
            " --as-of <ISO8601_UTC> [--apply] --format json"
        ),
        required_operator_inputs=(),
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
    _validate_canonical_config(config)
    supervisor_report = build_autonomy_supervisor_report(config)
    return build_autonomy_next_plan_from_report(supervisor_report)


def build_autonomy_next_plan_from_report(
    supervisor_report: Mapping[str, object],
) -> dict[str, object]:
    """Build one plan from an already-built cross-lane supervisor report."""

    report = _supervisor_report(supervisor_report)
    lane_summaries = _report_lanes(report)
    _validate_canonical_report(report, lane_summaries)

    actions: list[dict[str, object]] = []
    for summary in lane_summaries:
        actions.append(_plan_lane(summary))

    buckets = _bucket_lanes(actions)
    offline_lanes = buckets[BUCKET_OFFLINE_RUNNABLE]
    authorized_network_lanes = buckets[BUCKET_AUTHORIZED_NETWORK]
    gated_lanes = buckets[BUCKET_OPERATOR_GATED]
    noop_lanes = buckets[BUCKET_NOOP]

    next_offline = _highest_priority_action(
        actions,
        lambda action: action["execution_class"] == EXECUTION_AUTO_OFFLINE,
    )
    if next_offline is None:
        next_offline = _highest_priority_action(
            actions, lambda action: action["offline_runnable"] is True
        )
    next_authorized_network = _highest_priority_action(
        actions,
        lambda action: (
            action["execution_class"] == EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
        ),
    )
    plan_class = _plan_class(offline_lanes, authorized_network_lanes, gated_lanes)

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
        "next_authorized_network_action_lane": (
            str(next_authorized_network["lane_id"])
            if next_authorized_network
            else ""
        ),
        "next_authorized_network_action": next_authorized_network,
        "offline_runnable_lanes": offline_lanes,
        "authorized_network_lanes": authorized_network_lanes,
        "operator_gated_lanes": gated_lanes,
        "noop_lanes": noop_lanes,
        "operator_gated_actions": operator_gated_actions,
        "operator_summary": _operator_summary(
            plan_class, next_offline, next_authorized_network, gated_lanes
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
    normalized_state = _required_state(summary.get("normalized_state"))
    recommended_action = _required_string(
        summary.get("next_action"), "next_action"
    )
    classified = classify_action(recommended_action)
    return {
        "lane_id": lane_id,
        "title": _text(summary.get("title")),
        "category": _text(summary.get("category")),
        "normalized_state": normalized_state,
        "artifact_path": _required_string(
            summary.get("artifact_path"), "artifact_path"
        ),
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


def _executing_repository_root() -> Path:
    """Return the verified source checkout root for this executing module."""

    root = Path(__file__).resolve().parents[3]
    if not _valid_git_marker(root):
        raise ValidationError("executing source root must be a Git checkout/worktree.")
    if not (root / "src" / "algotrader" / "cli.py").is_file():
        raise ValidationError("executing source root is missing src/algotrader/cli.py.")
    try:
        cwd = Path.cwd().resolve(strict=True)
    except OSError as exc:
        raise ValidationError("process cwd must resolve to the repository root.") from exc
    if cwd != root:
        raise ValidationError("process cwd must equal the executing repository root.")
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
    _reject_symlink_components(candidate, "canonical readiness target")
    try:
        return candidate.resolve(strict=False)
    except OSError as exc:
        raise ValidationError("canonical readiness target must resolve.") from exc


def _reject_symlink_components(path: Path, field_name: str) -> None:
    current = Path(path.anchor) if path.anchor else Path()
    for part in path.parts[1:] if path.anchor else path.parts:
        current /= part
        if current.is_symlink():
            raise ValidationError(f"{field_name} must not traverse a symlink.")


def _readiness_lane_summary(
    lane_summaries: Iterable[Mapping[str, object]],
) -> Mapping[str, object]:
    matches = [
        summary
        for summary in lane_summaries
        if summary.get("lane_id") == _READINESS_LANE_ID
    ]
    if len(matches) != 1:
        raise ValidationError(
            "supervisor report must contain exactly one crypto readiness lane."
        )
    return matches[0]


def _validate_canonical_config(config: AutonomySupervisorConfig) -> None:
    """Fail closed unless config observes the fixed repository readiness target."""

    root = _executing_repository_root()
    expected_lanes_root = _canonical_target(root, CANONICAL_LANES_ROOT_RELPATH)
    if (
        _resolved_target(config.lanes_root, root=root, field_name="lanes_root")
        != expected_lanes_root
    ):
        raise ValidationError("lanes_root must be the canonical repository runs path.")
    override = config.lane_artifact_overrides.get(_READINESS_LANE_ID)
    if override is not None:
        expected_packet = _canonical_target(
            root, CANONICAL_READINESS_PACKET_RELPATH
        )
        if (
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


def _validate_canonical_report(
    report: Mapping[str, object],
    lane_summaries: Iterable[Mapping[str, object]],
) -> None:
    """Validate the report's observed readiness packet before classification."""

    root = _executing_repository_root()
    expected_lanes_root = _canonical_target(root, CANONICAL_LANES_ROOT_RELPATH)
    if (
        _resolved_target(report.get("lanes_root"), root=root, field_name="lanes_root")
        != expected_lanes_root
    ):
        raise ValidationError("report lanes_root is not the canonical runs path.")

    readiness = _readiness_lane_summary(lane_summaries)
    expected_packet = _canonical_target(root, CANONICAL_READINESS_PACKET_RELPATH)
    if (
        _resolved_target(
            readiness.get("artifact_path"),
            root=root,
            field_name="crypto readiness artifact_path",
        )
        != expected_packet
    ):
        raise ValidationError(
            "crypto readiness artifact_path is not the canonical packet."
        )

    state = _required_state(readiness.get("normalized_state"))
    readiness_spec = next(
        lane for lane in AUTONOMY_SUPERVISOR_LANES if lane.lane_id == _READINESS_LANE_ID
    )
    expected_action = readiness_spec.next_actions[state]
    action = _required_string(readiness.get("next_action"), "next_action")
    if action != expected_action:
        raise ValidationError(
            "crypto readiness action does not match its normalized state."
        )

    classified = classify_action(action)
    if action in (_READINESS_ABSENT_ACTION, _READINESS_STALE_ACTION):
        if (
            classified.execution_class != EXECUTION_AUTO_OFFLINE
            or classified.offline_runnable is not True
            or classified.gate != ""
            or classified.command != _READINESS_REPLAY_COMMAND
        ):
            raise ValidationError(
                "crypto readiness replay classification is not canonical."
            )


def _required_state(value: object) -> str:
    """Return a lane state the severity loop can rank, else fail closed.

    A state outside the supervisor's frozen vocabulary would match nothing in
    ``_highest_priority_action`` and be silently skipped, while still counting
    toward ``offline_runnable_lanes`` and ``plan_class`` — yielding a plan that
    claims an offline action exists and simultaneously names none. Reject it here
    instead, mirroring the unknown-lane-id rejection in ``_report_lanes``.
    """

    state = _required_string(value, "normalized_state")
    if state not in AUTONOMY_SUPERVISOR_STATES:
        raise ValidationError(
            f"normalized_state must be a supervisor state: {state}"
        )
    return state


def _highest_priority_action(
    actions: list[dict[str, object]],
    predicate,
) -> dict[str, object] | None:
    for state in _STATE_SEVERITY:
        for action in actions:
            if action["normalized_state"] == state and predicate(action):
                return action
    return None


def _plan_class(
    offline_lanes: list[str],
    authorized_network_lanes: list[str],
    gated_lanes: list[str],
) -> str:
    """Rank the plan by the most autonomous progress actually available.

    ``authorized_network_lanes`` is ranked below offline (an offline command
    needs no network at all) but above operator-gated, and — critically —
    above ``PLAN_ALL_NOMINAL_OR_WAITING``: a lane carrying a standing-authority
    read-only network command is a pending next action, not a nominal lane.
    """

    if offline_lanes:
        return PLAN_OFFLINE_ACTION_AVAILABLE
    if authorized_network_lanes:
        return PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE
    if gated_lanes:
        return PLAN_OPERATOR_AUTHORITY_REQUIRED
    return PLAN_ALL_NOMINAL_OR_WAITING


def _operator_summary(
    plan_class: str,
    next_offline: dict[str, object] | None,
    next_authorized_network: dict[str, object] | None,
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
    if (
        plan_class == PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE
        and next_authorized_network is not None
    ):
        gated = len(gated_lanes)
        return (
            "No offline action is available; next authorized read-only "
            f"network action on lane {next_authorized_network['lane_id']}: run "
            f"`{next_authorized_network['command']}` "
            f"(gate: {next_authorized_network['gate']}, standing authority). "
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
        "next_authorized_network_action_lane: "
        f"{payload.get('next_authorized_network_action_lane', '')}",
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
