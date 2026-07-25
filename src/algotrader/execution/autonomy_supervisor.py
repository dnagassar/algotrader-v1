"""Offline cross-lane autonomy supervisor over local evidence artifacts.

This module reads caller-supplied or default-located local JSONL/JSON evidence
artifacts for each known autonomy lane, normalizes each lane's declared state
field into a strict supervisory vocabulary, computes staleness against an
explicit caller ``as_of`` timestamp, and aggregates one whole-system readiness
record.

It is deterministic and offline: it loads no runtime profile, inspects no
credentials, imports no broker SDK, opens no socket, reads no wall clock, and
exposes no submit, cancel, replace, close, liquidation, or broker mutation path.
Missing, unreadable, or ambiguous artifacts fail closed and never invent a
healthy or actionable state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "ALL_LANES_ABSENT_ACTION",
    "AUTONOMY_SUPERVISOR_LABELS",
    "AUTONOMY_SUPERVISOR_LANES",
    "AutonomySupervisorConfig",
    "AutonomySupervisorWriteResult",
    "LaneSpec",
    "STATE_ABSENT",
    "STATE_ATTENTION",
    "STATE_BLOCKED",
    "STATE_NOMINAL",
    "STATE_STALE",
    "STATE_UNKNOWN",
    "STATE_WAITING",
    "SYSTEM_ATTENTION",
    "SYSTEM_BLOCKED",
    "SYSTEM_NOMINAL",
    "SYSTEM_NO_LANE_EVIDENCE",
    "SYSTEM_WAITING",
    "build_autonomy_supervisor_report",
    "build_autonomy_supervisor_report_from_records",
    "render_autonomy_supervisor_json",
    "render_autonomy_supervisor_text",
    "write_autonomy_supervisor_jsonl",
]


_MILESTONE = "V5.37 - Offline cross-lane autonomy supervisor"
_RECORD_TYPE = "autonomy_supervisor_report"
_COMMAND = "autonomy-supervisor-status"
_PROFIT_CLAIM = "none"

AUTONOMY_SUPERVISOR_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

# Normalized per-lane supervisory states, ordered here from most to least severe.
STATE_BLOCKED = "blocked"
STATE_UNKNOWN = "unknown"
STATE_ATTENTION = "attention_required"
STATE_STALE = "stale"
STATE_WAITING = "waiting"
STATE_NOMINAL = "nominal"
STATE_ABSENT = "absent"

_STATE_SEVERITY = (
    STATE_BLOCKED,
    STATE_UNKNOWN,
    STATE_ATTENTION,
    STATE_STALE,
    STATE_WAITING,
    STATE_NOMINAL,
    STATE_ABSENT,
)

# Aggregate recommended action for a lane set in which every lane is absent. No
# single lane is the remedy, so the report names no lane and recommends seeding
# the lab. The V5.38 planner classifies this token as operator-gated, so it
# never becomes an offline-runnable action.
ALL_LANES_ABSENT_ACTION = "all_lanes_absent_run_lane_commands_to_seed_evidence"

# Whole-system rollup classifications.
SYSTEM_BLOCKED = "blocked"
SYSTEM_ATTENTION = "attention_required"
SYSTEM_WAITING = "waiting"
SYSTEM_NOMINAL = "nominal"
SYSTEM_NO_LANE_EVIDENCE = "no_lane_evidence"

# Artifact reader kinds.
_KIND_JSONL_LAST = "jsonl_last"
_KIND_JSON_OBJECT = "json_object"
_ARTIFACT_KINDS = frozenset({_KIND_JSONL_LAST, _KIND_JSON_OBJECT})

# Any of these boolean safety fields, when present, must be exactly ``False``.
# A non-false value fails the lane closed rather than being ignored.
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "broker_mutation_allowed",
    "broker_mutation_attempted",
    "broker_mutation_performed",
    "broker_access_attempted",
    "network_access_attempted",
    "credential_access_attempted",
    "paper_submit_performed",
    "paper_submit_authorized",
    "submit_authorized",
    "live_trading_performed",
    "live_authorized",
    "capital_allocated",
)

_WRITE_RESULT_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _required_str_tuple(value: object, field_name: str) -> tuple[str, ...]:
    items = _str_tuple(value, field_name)
    if not items:
        raise ValidationError(f"{field_name} must be a non-empty tuple of strings.")
    return items


def _str_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        raise ValidationError(f"{field_name} must be an iterable of strings.")
    return tuple(_required_string(item, f"{field_name} item") for item in value)


def _frozen_str_map(value: object, field_name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    resolved: dict[str, str] = {}
    for key, item in value.items():
        resolved[_required_string(key, f"{field_name} key")] = _required_string(
            item, f"{field_name} value"
        )
    return resolved


@dataclass(frozen=True, slots=True)
class LaneSpec:
    """Frozen classification contract for one autonomy lane.

    ``state_map`` maps a lane's raw declared state value to a normalized
    supervisory state. Unmapped values normalize to ``unknown`` unless they
    contain a fail-closed cautionary token, in which case they normalize to
    ``blocked``. ``next_actions`` maps a normalized state to a read-only or
    operator-review next action; it never names a mutation.

    ``stale_requires_operator_action`` declares what staleness *means* for this
    lane: when true, no offline command can cure it and the remaining remedy is
    external/operator action, so the lane aggregates as ``waiting`` rather than
    ``attention_required``. The lane still reports ``stale`` and its age, so no
    signal is lost - only the system-level severity changes, because an
    autonomous loop that cannot act has genuinely finished its work.
    """

    lane_id: str
    title: str
    category: str
    artifact_relpath: str
    artifact_kind: str
    state_fields: tuple[str, ...]
    as_of_fields: tuple[str, ...]
    max_age_hours: int
    state_map: Mapping[str, str]
    next_actions: Mapping[str, str]
    blocker_fields: tuple[str, ...] = ()
    stale_requires_operator_action: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "lane_id", _required_string(self.lane_id, "lane_id"))
        object.__setattr__(self, "title", _required_string(self.title, "title"))
        object.__setattr__(self, "category", _required_string(self.category, "category"))
        object.__setattr__(
            self,
            "artifact_relpath",
            _required_string(self.artifact_relpath, "artifact_relpath"),
        )
        if self.artifact_kind not in _ARTIFACT_KINDS:
            raise ValidationError("artifact_kind must be a supported reader kind.")
        object.__setattr__(self, "state_fields", _required_str_tuple(self.state_fields, "state_fields"))
        object.__setattr__(self, "as_of_fields", _str_tuple(self.as_of_fields, "as_of_fields"))
        if type(self.max_age_hours) is not int or self.max_age_hours < 0:
            raise ValidationError("max_age_hours must be a non-negative integer.")
        object.__setattr__(self, "state_map", _frozen_str_map(self.state_map, "state_map"))
        object.__setattr__(self, "next_actions", _frozen_str_map(self.next_actions, "next_actions"))
        object.__setattr__(self, "blocker_fields", _str_tuple(self.blocker_fields, "blocker_fields"))
        if type(self.stale_requires_operator_action) is not bool:
            raise ValidationError("stale_requires_operator_action must be a bool.")
        if self.stale_requires_operator_action and self.max_age_hours <= 0:
            raise ValidationError(
                "stale_requires_operator_action is meaningless without max_age_hours."
            )

    def resolve_state(self, raw_state: str) -> str:
        """Normalize a raw lane state value into the supervisory vocabulary."""

        mapped = self.state_map.get(raw_state)
        if mapped is not None:
            return mapped
        lowered = raw_state.lower()
        if any(token in lowered for token in ("blocked", "failed", "error", "conflict")):
            return STATE_BLOCKED
        return STATE_UNKNOWN

    def next_action(self, normalized_state: str) -> str:
        return self.next_actions.get(normalized_state, "operator_review_lane_evidence")


# Frozen registry of the currently supervised autonomy lanes. Default artifact
# paths are best-effort canonical locations under the local ``runs`` root; a
# missing default simply reads ``absent``. Operators or wrappers may point a
# lane at its exact latest artifact through an explicit override.
AUTONOMY_SUPERVISOR_LANES: tuple[LaneSpec, ...] = (
    LaneSpec(
        lane_id="spy_market_data_soak",
        title="SPY unattended adjusted market-data soak",
        category="spy_equity_market_data",
        artifact_relpath="paper_lab/spy_adjusted_market_data_soak_report.json",
        artifact_kind=_KIND_JSON_OBJECT,
        state_fields=("evidence_state",),
        as_of_fields=("latest_attempted_session_date",),
        max_age_hours=96,
        state_map={
            "accepted_unattended_market_data_soak": STATE_NOMINAL,
            "collecting_unattended_market_data_soak": STATE_WAITING,
            "blocked_latest_expected_session_not_accepted": STATE_BLOCKED,
        },
        next_actions={
            STATE_NOMINAL: "unattended_market_data_soak_proven_continue_cadence",
            STATE_WAITING: "continue_scheduled_read_only_market_data_refresh_cadence",
            STATE_STALE: "operator_check_scheduled_market_data_refresh_task_health",
            STATE_BLOCKED: "operator_review_latest_failed_market_data_session_read_only",
            STATE_ATTENTION: "operator_review_market_data_soak_evidence",
            STATE_UNKNOWN: "operator_review_market_data_soak_evidence",
            STATE_ABSENT: "run_authorized_read_only_market_data_refresh_to_seed_soak",
        },
        # A stale soak means the scheduled refresh task stopped producing
        # sessions. Only the operator can restore it; no offline command can.
        stale_requires_operator_action=True,
    ),
    LaneSpec(
        lane_id="spy_offline_daily_cycle",
        title="SPY ETF/SMA offline daily cycle chain",
        category="spy_equity_paper_lab",
        artifact_relpath="paper_lab/m444_offline_daily_cycle_run.jsonl",
        artifact_kind=_KIND_JSONL_LAST,
        state_fields=(
            "daily_chain_state",
            "daily_wrapper_state",
            "validation_state",
            "state_rollup_status",
        ),
        as_of_fields=("generated_at", "as_of", "validated_at"),
        # V5.42 Stage 3: a daily cycle whose latest accepted evidence carries a
        # timestamp older than 30h is stale and should be re-run. Records without
        # a timestamp are never stale, so seeded/absent evidence is unaffected.
        max_age_hours=30,
        state_map={
            "accepted_observe_hold_noop": STATE_NOMINAL,
            "accepted_current_cycle_hold_noop": STATE_NOMINAL,
            "review_only": STATE_NOMINAL,
        },
        next_actions={
            STATE_NOMINAL: "observe_hold_noop_continue_offline_daily_cycle",
            STATE_WAITING: "await_next_offline_daily_cycle_input",
            STATE_STALE: "operator_refresh_offline_daily_cycle_inputs",
            STATE_BLOCKED: "operator_review_blocked_offline_daily_cycle_chain",
            STATE_ATTENTION: "operator_review_offline_daily_cycle_chain",
            STATE_UNKNOWN: "operator_review_offline_daily_cycle_chain",
            STATE_ABSENT: "run_offline_daily_cycle_chain_to_seed_evidence",
        },
        blocker_fields=("chain_blockers", "validation_blockers", "blockers"),
        # Stale daily-cycle evidence means the underlying daily bars are old.
        # The only command that writes this lane's artifact is the seed command,
        # which requires an operator-supplied clock and CSV; the allowlisted
        # m446 rerun is pinned to one historical dataset and writes a different
        # artifact, so it can never cure staleness here.
        stale_requires_operator_action=True,
    ),
    LaneSpec(
        lane_id="crypto_supervised_readiness_trial",
        title="Crypto V5.32 supervised readiness trial (R1)",
        category="crypto_v2_readiness",
        artifact_relpath="crypto_supervised_readiness_trial/latest/readiness_packet.json",
        artifact_kind=_KIND_JSON_OBJECT,
        state_fields=("trial_classification", "v5_32_trial_classification"),
        as_of_fields=("generated_at", "as_of"),
        max_age_hours=0,
        state_map={
            "accepted": STATE_NOMINAL,
        },
        next_actions={
            STATE_NOMINAL: "r1_deterministic_readiness_proven_continue",
            STATE_WAITING: "await_supervised_readiness_trial_inputs",
            STATE_STALE: "rerun_supervised_readiness_trial",
            STATE_BLOCKED: "operator_review_blocked_readiness_trial",
            STATE_ATTENTION: "operator_review_readiness_trial",
            STATE_UNKNOWN: "operator_review_readiness_trial",
            STATE_ABSENT: "run_supervised_readiness_trial_to_seed_r1_evidence",
        },
        blocker_fields=("blockers",),
    ),
    LaneSpec(
        lane_id="crypto_forward_shadow_cycle",
        title="Crypto V2 forward-shadow operating cycle",
        category="crypto_v2_forward_shadow",
        artifact_relpath="crypto_strategy_tournament/v2/forward_shadow/latest/cycle_status.json",
        artifact_kind=_KIND_JSON_OBJECT,
        state_fields=("classification", "cycle_classification"),
        as_of_fields=("as_of", "generated_at"),
        max_age_hours=0,
        state_map={
            "waiting_for_tournament_terminal": STATE_WAITING,
            "state_initialization_required": STATE_WAITING,
            "dormant_before_shadow_state_initialization": STATE_WAITING,
            "market_data_refresh_ready": STATE_ATTENTION,
            "ready_for_explicit_read_only_market_data_fetch": STATE_ATTENTION,
        },
        next_actions={
            STATE_NOMINAL: "continue_forward_shadow_cadence",
            STATE_WAITING: "await_tournament_terminal_or_next_shadow_window",
            STATE_STALE: "rerun_forward_shadow_status",
            STATE_BLOCKED: "operator_review_blocked_forward_shadow_cycle",
            STATE_ATTENTION: "authorized_read_only_market_data_fetch_for_shadow_window",
            STATE_UNKNOWN: "operator_review_forward_shadow_cycle",
            STATE_ABSENT: "run_forward_shadow_status_to_seed_evidence",
        },
        blocker_fields=("blockers",),
    ),
    LaneSpec(
        lane_id="crypto_bounded_paper_probe_review",
        title="Crypto V2 bounded paper-probe review",
        category="crypto_v2_probe_review",
        artifact_relpath="crypto_strategy_tournament/v2/bounded_paper_probe_review/latest/review.json",
        artifact_kind=_KIND_JSON_OBJECT,
        state_fields=("classification", "review_classification"),
        as_of_fields=("as_of", "generated_at"),
        max_age_hours=0,
        state_map={
            "waiting_for_v5_25_terminal_evidence": STATE_WAITING,
            "blocked_by_operational_evidence": STATE_BLOCKED,
            "eligible_for_operator_review_only": STATE_ATTENTION,
        },
        next_actions={
            STATE_NOMINAL: "continue_bounded_paper_probe_review_cadence",
            STATE_WAITING: "await_v5_25_terminal_evidence",
            STATE_STALE: "rerun_bounded_paper_probe_review",
            STATE_BLOCKED: "operator_review_operational_evidence_blockers_read_only",
            STATE_ATTENTION: "operator_review_only_no_paper_mutation_authorized",
            STATE_UNKNOWN: "operator_review_bounded_paper_probe_review",
            STATE_ABSENT: "run_bounded_paper_probe_review_to_seed_evidence",
        },
        blocker_fields=("blockers", "operational_evidence_blockers"),
    ),
    LaneSpec(
        lane_id="crypto_capability_production",
        title="Crypto V2 bounded-probe capability production",
        category="crypto_v2_capability",
        artifact_relpath="crypto_strategy_tournament/v2/bounded_paper_probe_capabilities/latest/production.json",
        artifact_kind=_KIND_JSON_OBJECT,
        state_fields=("classification", "production_classification"),
        as_of_fields=("as_of", "generated_at"),
        max_age_hours=0,
        state_map={
            "candidate_deferred_pending_terminal_winner": STATE_WAITING,
        },
        next_actions={
            STATE_NOMINAL: "continue_capability_production_cadence",
            STATE_WAITING: "await_v5_25_terminal_winner",
            STATE_STALE: "rerun_capability_production",
            STATE_BLOCKED: "operator_review_blocked_capability_production",
            STATE_ATTENTION: "operator_review_capability_production",
            STATE_UNKNOWN: "operator_review_capability_production",
            STATE_ABSENT: "run_capability_production_to_seed_evidence",
        },
        blocker_fields=("blockers",),
    ),
)


@dataclass(frozen=True, slots=True)
class AutonomySupervisorConfig:
    """Explicit local inputs for one offline cross-lane supervisor report."""

    run_id: str
    as_of: str
    lanes_root: Path | str = Path("runs")
    lane_artifact_overrides: Mapping[str, Path | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "as_of", _required_utc_text(self.as_of, "as_of"))
        object.__setattr__(self, "lanes_root", _required_path(self.lanes_root, "lanes_root"))
        object.__setattr__(
            self,
            "lane_artifact_overrides",
            _frozen_path_map(self.lane_artifact_overrides, "lane_artifact_overrides"),
        )


@dataclass(frozen=True, slots=True)
class AutonomySupervisorWriteResult:
    """Local JSONL write metadata for a single supervisor record."""

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
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        for field_name in _WRITE_RESULT_FALSE_FIELDS:
            object.__setattr__(
                self,
                field_name,
                _false_bool(getattr(self, field_name), field_name),
            )

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


@dataclass(frozen=True, slots=True)
class _ArtifactRead:
    path: Path
    kind: str
    found: bool
    parsed: bool
    record_count: int
    latest_record: dict[str, object] | None
    error: str


def build_autonomy_supervisor_report(
    config: AutonomySupervisorConfig,
    *,
    allow_empty_lab: bool = False,
) -> dict[str, object]:
    """Build one consolidated offline cross-lane autonomy supervisor record."""

    checked_config = _config(config)
    checked_allow_empty_lab = _bool(allow_empty_lab, "allow_empty_lab")
    lane_summaries = []
    for lane in AUTONOMY_SUPERVISOR_LANES:
        artifact = _read_lane_artifact(checked_config, lane)
        lane_summaries.append(_summarize_lane(checked_config, lane, artifact))
    return _aggregate(checked_config, lane_summaries, checked_allow_empty_lab)


def build_autonomy_supervisor_report_from_records(
    config: AutonomySupervisorConfig,
    lane_records: Mapping[str, Mapping[str, object] | None],
    *,
    allow_empty_lab: bool = False,
) -> dict[str, object]:
    """Build one report from explicit in-memory latest lane records.

    ``None`` marks a lane as absent. A mapping is treated as an already-parsed
    latest record for that lane. Unknown lane ids are rejected.
    """

    checked_config = _config(config)
    checked_allow_empty_lab = _bool(allow_empty_lab, "allow_empty_lab")
    records = _lane_records(lane_records)
    lane_summaries = []
    for lane in AUTONOMY_SUPERVISOR_LANES:
        resolved_path = _resolve_lane_path(checked_config, lane)
        if lane.lane_id in records and records[lane.lane_id] is not None:
            artifact = _ArtifactRead(
                path=resolved_path,
                kind=lane.artifact_kind,
                found=True,
                parsed=True,
                record_count=1,
                latest_record=dict(records[lane.lane_id] or {}),
                error="",
            )
        else:
            artifact = _ArtifactRead(
                path=resolved_path,
                kind=lane.artifact_kind,
                found=False,
                parsed=False,
                record_count=0,
                latest_record=None,
                error="artifact_absent",
            )
        lane_summaries.append(_summarize_lane(checked_config, lane, artifact))
    return _aggregate(checked_config, lane_summaries, checked_allow_empty_lab)


def _summarize_lane(
    config: AutonomySupervisorConfig,
    lane: LaneSpec,
    artifact: _ArtifactRead,
) -> dict[str, object]:
    record = artifact.latest_record or {}
    blockers: list[str] = []

    if not artifact.found:
        normalized_state = STATE_ABSENT
        raw_state = ""
        state_source_field = ""
    elif not artifact.parsed:
        normalized_state = STATE_BLOCKED
        raw_state = ""
        state_source_field = ""
        blockers.append(f"source_unreadable:{artifact.error}")
    else:
        raw_state, state_source_field = _extract_state(record, lane.state_fields)
        if raw_state == "":
            normalized_state = STATE_UNKNOWN
            blockers.append("source_state_field_absent")
        else:
            normalized_state = lane.resolve_state(raw_state)

    safety_flags_ok = _safety_flags_ok(record)
    operator_action_required = record.get("operator_action_required") is True

    # Fail-closed escalations that can only move a lane toward more attention.
    if artifact.parsed and not safety_flags_ok:
        normalized_state = STATE_BLOCKED
        blockers.append("source_safety_flags_not_false")
    if normalized_state == STATE_BLOCKED:
        blockers.extend(_lane_record_blockers(record, lane.blocker_fields))
    if operator_action_required and normalized_state not in (STATE_BLOCKED,):
        normalized_state = STATE_ATTENTION

    as_of_value, age_hours, stale = _staleness(config, lane, record, normalized_state)
    if stale:
        normalized_state = STATE_STALE

    next_action = lane.next_action(normalized_state)

    return {
        "lane_id": lane.lane_id,
        "title": lane.title,
        "category": lane.category,
        "artifact_path": str(artifact.path),
        "artifact_kind": lane.artifact_kind,
        "found": artifact.found,
        "parsed": artifact.parsed,
        "record_count": artifact.record_count,
        "read_error": artifact.error,
        "raw_state": raw_state,
        "state_source_field": state_source_field,
        "normalized_state": normalized_state,
        "as_of": as_of_value,
        "age_hours": age_hours,
        "max_age_hours": lane.max_age_hours,
        "stale": stale,
        "stale_requires_operator_action": lane.stale_requires_operator_action,
        "operator_action_required": operator_action_required,
        "safety_flags_ok": safety_flags_ok,
        "blockers": list(_dedupe(tuple(blockers))),
        "next_action": next_action,
    }


def _aggregate(
    config: AutonomySupervisorConfig,
    lane_summaries: list[dict[str, object]],
    allow_empty_lab: bool = False,
) -> dict[str, object]:
    counts = {state: 0 for state in _STATE_SEVERITY}
    for summary in lane_summaries:
        counts[str(summary["normalized_state"])] += 1

    # Stale lanes whose only cure is external/operator action are not a system
    # attention condition: no offline command can advance them, so the autonomous
    # loop has finished its work and is waiting on the operator.
    operator_gated_stale = sum(
        1
        for summary in lane_summaries
        if summary["normalized_state"] == STATE_STALE
        and summary["stale_requires_operator_action"] is True
    )

    system_status = _system_status(counts, operator_gated_stale)
    # An all-absent lane set is fail-closed by default: it must not read as a
    # harmless "nothing to do yet" to an unattended caller. The caller may
    # explicitly assert an intentionally empty lab to opt out, mirroring the
    # V5.42 self-refresh cycle's ``allow_empty_lab`` exception.
    evidence_required = system_status == SYSTEM_NO_LANE_EVIDENCE and not allow_empty_lab
    highest = _highest_priority_lane(lane_summaries)
    aggregate_blockers: list[str] = []
    for summary in lane_summaries:
        aggregate_blockers.extend(_string_list(summary.get("blockers")))

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": config.run_id,
        "as_of": config.as_of,
        "lanes_root": str(config.lanes_root),
        "labels": list(AUTONOMY_SUPERVISOR_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "lane_count": len(lane_summaries),
        "lane_state_counts": {state: counts[state] for state in _STATE_SEVERITY},
        "lanes": lane_summaries,
        "system_status": system_status,
        "system_blocked": system_status == SYSTEM_BLOCKED,
        "system_attention_required": system_status
        in (SYSTEM_BLOCKED, SYSTEM_ATTENTION),
        "allow_empty_lab": allow_empty_lab,
        "evidence_required": evidence_required,
        "blocked_lanes": _lanes_in_state(lane_summaries, STATE_BLOCKED),
        "unknown_lanes": _lanes_in_state(lane_summaries, STATE_UNKNOWN),
        "attention_lanes": _lanes_in_state(lane_summaries, STATE_ATTENTION),
        "stale_lanes": _lanes_in_state(lane_summaries, STATE_STALE),
        "waiting_lanes": _lanes_in_state(lane_summaries, STATE_WAITING),
        "nominal_lanes": _lanes_in_state(lane_summaries, STATE_NOMINAL),
        "absent_lanes": _lanes_in_state(lane_summaries, STATE_ABSENT),
        "aggregate_blockers": list(_dedupe(tuple(aggregate_blockers))),
        "recommended_next_action_lane": highest["lane_id"] if highest else "",
        "recommended_next_action": (
            highest["next_action"] if highest else ALL_LANES_ABSENT_ACTION
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


def _system_status(counts: Mapping[str, int], operator_gated_stale: int) -> str:
    # Stale lanes split into two kinds: those an offline command could still
    # cure (a real attention condition) and those only the operator can cure
    # (a waiting condition). ``operator_gated_stale`` counts the latter.
    actionable_stale = counts[STATE_STALE] - operator_gated_stale
    if counts[STATE_BLOCKED] > 0:
        return SYSTEM_BLOCKED
    if counts[STATE_UNKNOWN] > 0 or counts[STATE_ATTENTION] > 0 or actionable_stale > 0:
        return SYSTEM_ATTENTION
    if counts[STATE_WAITING] > 0 or operator_gated_stale > 0:
        return SYSTEM_WAITING
    if counts[STATE_NOMINAL] > 0:
        return SYSTEM_NOMINAL
    return SYSTEM_NO_LANE_EVIDENCE


def _highest_priority_lane(
    lane_summaries: list[dict[str, object]],
) -> dict[str, object] | None:
    """Return the highest-severity lane that has evidence, else ``None``.

    ``absent`` is deliberately excluded: naming one absent lane in a lane set
    where every lane is absent would answer a whole-system condition with a
    single-lane instruction. Returning ``None`` routes that case to
    ``ALL_LANES_ABSENT_ACTION`` with no recommended lane. Because the severity
    loop returns any non-absent lane first, ``None`` means exactly
    ``system_status == no_lane_evidence``, so a partially seeded lab still
    recommends its highest-severity lane and never an absent one.
    """

    for state in _STATE_SEVERITY:
        if state == STATE_ABSENT:
            continue
        for summary in lane_summaries:
            if summary["normalized_state"] == state:
                return summary
    return None


def render_autonomy_supervisor_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_autonomy_supervisor_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable cross-lane supervisor summary."""

    lines = [
        "Cross-lane autonomy supervisor",
        f"run_id: {payload.get('run_id', '')}",
        f"as_of: {payload.get('as_of', '')}",
        f"system_status: {payload.get('system_status', '')}",
        f"system_attention_required: {_bool_text(payload.get('system_attention_required'))}",
        f"allow_empty_lab: {_bool_text(payload.get('allow_empty_lab'))}",
        f"evidence_required: {_bool_text(payload.get('evidence_required'))}",
        f"recommended_next_action_lane: {payload.get('recommended_next_action_lane', '')}",
        f"recommended_next_action: {payload.get('recommended_next_action', '')}",
        "lanes:",
    ]
    for summary in _mapping_list(payload.get("lanes")):
        blockers = _joined(_string_list(summary.get("blockers")))
        lines.append(
            "  - "
            f"{summary.get('lane_id', '')}: {summary.get('normalized_state', '')}"
            f" | raw={summary.get('raw_state', '') or 'none'}"
            f" | next={summary.get('next_action', '')}"
            f" | blockers={blockers}"
        )
    lines.extend(
        (
            f"aggregate_blockers: {_joined(_string_list(payload.get('aggregate_blockers')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            f"broker_action_performed: {_bool_text(payload.get('broker_action_performed'))}",
            f"network_access_attempted: {_bool_text(payload.get('network_access_attempted'))}",
            f"credential_access_attempted: {_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )
    return "\n".join(lines)


def write_autonomy_supervisor_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> AutonomySupervisorWriteResult:
    """Write exactly one JSONL supervisor record, replacing any prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_autonomy_supervisor_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return AutonomySupervisorWriteResult(
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


def _resolve_lane_path(config: AutonomySupervisorConfig, lane: LaneSpec) -> Path:
    override = config.lane_artifact_overrides.get(lane.lane_id)
    if override is not None:
        return override
    return config.lanes_root / lane.artifact_relpath


def _read_lane_artifact(
    config: AutonomySupervisorConfig,
    lane: LaneSpec,
) -> _ArtifactRead:
    path = _resolve_lane_path(config, lane)
    if lane.artifact_kind == _KIND_JSON_OBJECT:
        return _read_json_object_artifact(path)
    return _read_jsonl_artifact(path)


def _read_json_object_artifact(path: Path) -> _ArtifactRead:
    if not path.exists():
        return _absent_read(path, _KIND_JSON_OBJECT)
    if not path.is_file():
        return _unparsed_read(path, _KIND_JSON_OBJECT, "path_not_file")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return _unparsed_read(path, _KIND_JSON_OBJECT, "empty_json")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return _unparsed_read(path, _KIND_JSON_OBJECT, "invalid_json")
    if not isinstance(payload, Mapping):
        return _unparsed_read(path, _KIND_JSON_OBJECT, "json_not_object")
    return _ArtifactRead(
        path=path,
        kind=_KIND_JSON_OBJECT,
        found=True,
        parsed=True,
        record_count=1,
        latest_record=dict(payload),
        error="",
    )


def _read_jsonl_artifact(path: Path) -> _ArtifactRead:
    if not path.exists():
        return _absent_read(path, _KIND_JSONL_LAST)
    if not path.is_file():
        return _unparsed_read(path, _KIND_JSONL_LAST, "path_not_file")

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return _unparsed_read(
                path,
                _KIND_JSONL_LAST,
                f"invalid_jsonl_line_{line_number}",
                record_count=len(records),
            )
        if not isinstance(payload, Mapping):
            return _unparsed_read(
                path,
                _KIND_JSONL_LAST,
                f"jsonl_record_{line_number}_not_object",
                record_count=len(records),
            )
        records.append(dict(payload))

    if not records:
        return _unparsed_read(path, _KIND_JSONL_LAST, "empty_jsonl")

    return _ArtifactRead(
        path=path,
        kind=_KIND_JSONL_LAST,
        found=True,
        parsed=True,
        record_count=len(records),
        latest_record=records[-1],
        error="",
    )


def _absent_read(path: Path, kind: str) -> _ArtifactRead:
    return _ArtifactRead(
        path=path,
        kind=kind,
        found=False,
        parsed=False,
        record_count=0,
        latest_record=None,
        error="path_not_found",
    )


def _unparsed_read(
    path: Path,
    kind: str,
    error: str,
    *,
    record_count: int = 0,
) -> _ArtifactRead:
    return _ArtifactRead(
        path=path,
        kind=kind,
        found=True,
        parsed=False,
        record_count=record_count,
        latest_record=None,
        error=error,
    )


def _extract_state(
    record: Mapping[str, object],
    state_fields: tuple[str, ...],
) -> tuple[str, str]:
    for field_name in state_fields:
        if field_name in record:
            value = record[field_name]
            text = _text(value).strip()
            if text:
                return text, field_name
    return "", ""


def _staleness(
    config: AutonomySupervisorConfig,
    lane: LaneSpec,
    record: Mapping[str, object],
    normalized_state: str,
) -> tuple[str, float | None, bool]:
    as_of_value = ""
    for field_name in lane.as_of_fields:
        if field_name in record:
            candidate = _text(record[field_name]).strip()
            if candidate:
                as_of_value = candidate
                break

    if as_of_value == "":
        return "", None, False

    reference = _parse_utc(config.as_of)
    observed = _parse_utc(as_of_value)
    if reference is None or observed is None:
        return as_of_value, None, False

    age_hours = round((reference - observed).total_seconds() / 3600.0, 4)
    stale = (
        lane.max_age_hours > 0
        and normalized_state in (STATE_NOMINAL, STATE_WAITING)
        and age_hours > lane.max_age_hours
    )
    return as_of_value, age_hours, stale


def _safety_flags_ok(record: Mapping[str, object]) -> bool:
    for field_name in _SAFETY_FALSE_FIELDS:
        if field_name in record and record[field_name] is not False:
            return False
    return True


def _lane_record_blockers(
    record: Mapping[str, object],
    blocker_fields: tuple[str, ...],
) -> list[str]:
    blockers: list[str] = []
    for field_name in blocker_fields:
        blockers.extend(_string_list(record.get(field_name)))
    return blockers


def _lanes_in_state(
    lane_summaries: list[dict[str, object]],
    state: str,
) -> list[str]:
    return [
        str(summary["lane_id"])
        for summary in lane_summaries
        if summary["normalized_state"] == state
    ]


def _parse_utc(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _config(value: object) -> AutonomySupervisorConfig:
    if type(value) is not AutonomySupervisorConfig:
        raise ValidationError("config must be an AutonomySupervisorConfig.")
    return value


def _lane_records(
    value: object,
) -> dict[str, Mapping[str, object] | None]:
    if not isinstance(value, Mapping):
        raise ValidationError("lane_records must be a mapping.")
    known = {lane.lane_id for lane in AUTONOMY_SUPERVISOR_LANES}
    resolved: dict[str, Mapping[str, object] | None] = {}
    for key, item in value.items():
        lane_id = _required_string(key, "lane_records key")
        if lane_id not in known:
            raise ValidationError(f"unknown lane id: {lane_id}")
        if item is None:
            resolved[lane_id] = None
        elif isinstance(item, Mapping):
            resolved[lane_id] = dict(item)
        else:
            raise ValidationError(f"lane_records[{lane_id}] must be a mapping or None.")
    return resolved


def _required_utc_text(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    if _parse_utc(text) is None:
        raise ValidationError(f"{field_name} must be an ISO-8601 UTC timestamp.")
    return text


def _required_path(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _output_path(value: object) -> Path:
    path = _required_path(value, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _frozen_path_map(
    value: object,
    field_name: str,
) -> dict[str, Path]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    known = {lane.lane_id for lane in AUTONOMY_SUPERVISOR_LANES}
    resolved: dict[str, Path] = {}
    for key, item in value.items():
        lane_id = _required_string(key, f"{field_name} key")
        if lane_id not in known:
            raise ValidationError(f"unknown lane id: {lane_id}")
        resolved[lane_id] = _required_path(item, f"{field_name}[{lane_id}]")
    return resolved


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


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


def _bool(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _joined(values: tuple[str, ...]) -> str:
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
