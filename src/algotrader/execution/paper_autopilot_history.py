"""Durable operating history for the bounded paper-autopilot loop.

The history layer consumes the loop's latest_status.json artifact and writes
offline-only rollups. It does not import broker SDKs or perform network IO.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


PAPER_AUTOPILOT_HISTORY_SCHEMA_VERSION = (
    "v208_paper_autopilot_operating_history_v1"
)
PAPER_AUTOPILOT_DEFAULT_LATEST_STATUS_PATH = (
    "runs/paper_autopilot/latest/latest_status.json"
)
PAPER_AUTOPILOT_DEFAULT_HISTORY_ROOT = "runs/paper_autopilot/history"
PAPER_AUTOPILOT_OPERATING_HISTORY_FILENAME = "operating_history.jsonl"
PAPER_AUTOPILOT_LATEST_ROLLUP_FILENAME = "latest_rollup.json"
PAPER_AUTOPILOT_OPERATING_SUMMARY_FILENAME = "operating_summary.md"

_REQUIRED_SAFETY_LABELS = frozenset({"paper_lab_only", "not_live_authorized"})
_CONFIRMED_RECONCILIATION_STATUSES = frozenset(
    {
        "confirmed",
        "confirmed_resolved",
        "reconciled",
        "reconciled_submit_observed",
        "reconciliation_confirmed",
        "reconciliation_resolved",
        "resolved",
    }
)
_HEALTHY_BLOCKERS = frozenset({"", "none"})
_COMPARISON_FIELDS = (
    "as_of_date",
    "sma_posture",
    "broker_state_mode",
    "broker_state_observed",
    "blocker_status",
    "action_decision",
    "reconciliation_status",
    "classification",
)


@dataclass(frozen=True, slots=True)
class PaperAutopilotHistoryConfig:
    """Configuration for appending one paper-autopilot operating-history entry."""

    latest_status_path: Path | str = PAPER_AUTOPILOT_DEFAULT_LATEST_STATUS_PATH
    history_root: Path | str = PAPER_AUTOPILOT_DEFAULT_HISTORY_ROOT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "latest_status_path",
            _path(self.latest_status_path, "latest_status_path"),
        )
        object.__setattr__(
            self,
            "history_root",
            _path(self.history_root, "history_root"),
        )


def update_paper_autopilot_operating_history(
    config: PaperAutopilotHistoryConfig | None = None,
) -> dict[str, Any]:
    """Append latest_status.json to durable history and write latest rollups."""

    resolved = config or PaperAutopilotHistoryConfig()
    history_root = Path(resolved.history_root)
    history_root.mkdir(parents=True, exist_ok=True)

    history_path = history_root / PAPER_AUTOPILOT_OPERATING_HISTORY_FILENAME
    rollup_path = history_root / PAPER_AUTOPILOT_LATEST_ROLLUP_FILENAME
    summary_path = history_root / PAPER_AUTOPILOT_OPERATING_SUMMARY_FILENAME
    previous_records = _read_history_records(history_path)
    previous_record = previous_records[-1] if previous_records else None

    status_load = _load_status_payload(Path(resolved.latest_status_path))
    normalized = _normalize_status_payload(
        status_load=status_load,
        previous_record=previous_record,
    )
    classification = classify_paper_autopilot_operating_record(
        normalized,
        previous_record=previous_record,
    )
    entry = {
        **normalized,
        **classification,
        "history_schema_version": PAPER_AUTOPILOT_HISTORY_SCHEMA_VERSION,
        "history_sequence": len(previous_records) + 1,
    }
    comparison = _compare_to_previous(entry, previous_record)
    entry["comparison_to_previous"] = comparison

    with history_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")

    rollup = _build_rollup(
        entry=entry,
        history_count=len(previous_records) + 1,
        comparison=comparison,
        history_path=history_path,
        rollup_path=rollup_path,
        summary_path=summary_path,
    )
    rollup_path.write_text(
        json.dumps(rollup, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary_path.write_text(
        render_paper_autopilot_operating_summary(rollup),
        encoding="utf-8",
        newline="\n",
    )
    return rollup


def classify_paper_autopilot_operating_record(
    record: Mapping[str, Any],
    *,
    previous_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify the latest normalized operating record."""

    del previous_record
    reason_codes: list[str] = []

    if record.get("status_artifact_available") is not True:
        reason_codes.append("latest_status_artifact_missing")
        return _classification(
            "stale_or_missing_status_artifact",
            attention_required=True,
            hard_stop=False,
            reason_codes=reason_codes,
        )
    if record.get("status_artifact_valid") is not True:
        reason_codes.append("latest_status_artifact_invalid")
        return _classification(
            "stale_or_missing_status_artifact",
            attention_required=True,
            hard_stop=False,
            reason_codes=reason_codes,
        )
    if record.get("status_artifact_stale") is True:
        reason_codes.append("latest_status_artifact_stale")
        return _classification(
            "stale_or_missing_status_artifact",
            attention_required=True,
            hard_stop=False,
            reason_codes=reason_codes,
        )

    blocker_status = _text(record.get("blocker_status"))
    safety_labels = set(_string_list(record.get("safety_labels")))
    missing_labels = sorted(_REQUIRED_SAFETY_LABELS - safety_labels)
    if record.get("live_mutation_performed") is True:
        reason_codes.append("live_mutation_performed")
    if record.get("live_trading_performed") is True:
        reason_codes.append("live_trading_performed")
    reason_codes.extend(f"missing_safety_label:{label}" for label in missing_labels)
    if blocker_status == "blocked/live_safety":
        reason_codes.append("blocker_live_safety")
    if reason_codes:
        return _classification(
            "live_safety_blocked",
            attention_required=True,
            hard_stop=True,
            reason_codes=reason_codes,
        )

    reconciliation_required = record.get("reconciliation_required") is True
    paper_submit_performed = record.get("paper_submit_performed") is True
    reconciliation_status = _text(record.get("reconciliation_status"))

    if blocker_status in {
        "blocked/expected_account_id_unavailable",
        "blocked/expected_account_mismatch",
        "blocked/expected_account_match_not_observed",
    }:
        return _classification(
            "expected_account_blocked",
            attention_required=True,
            hard_stop=False,
            reason_codes=[blocker_status.replace("/", "_")],
        )
    if blocker_status == "blocked/account_status_not_active":
        return _classification(
            "paper_account_status_blocked",
            attention_required=True,
            hard_stop=False,
            reason_codes=["paper_account_status_not_active"],
        )
    if blocker_status == "blocked/no_new_completed_bar_noop":
        return _classification(
            "no_new_completed_bar_noop",
            attention_required=False,
            hard_stop=False,
            reason_codes=["no_new_completed_bar_noop"],
        )
    if blocker_status in {
        "blocked/stale_data_preview_only",
        "blocked/blocked_future_dated_local_data",
        "blocked/accepted_but_stale",
        "blocked/stale_or_invalid_data",
    }:
        return _classification(
            "data_freshness_blocked",
            attention_required=True,
            hard_stop=False,
            reason_codes=[blocker_status.replace("/", "_")],
        )
    if (
        record.get("paper_profile_run") is True
        and record.get("broker_state_observed") is not True
    ):
        return _classification(
            "broker_state_not_observed",
            attention_required=True,
            hard_stop=False,
            reason_codes=["paper_profile_broker_state_not_observed"],
        )
    if blocker_status == "blocked/broker_state_not_observed":
        return _classification(
            "broker_state_not_observed",
            attention_required=True,
            hard_stop=False,
            reason_codes=["blocker_broker_state_not_observed"],
        )
    if reconciliation_required or blocker_status == "blocked/reconciliation_required":
        return _classification(
            "reconciliation_required",
            attention_required=True,
            hard_stop=False,
            reason_codes=["reconciliation_required"],
        )
    if record.get("unexpected_non_spy_position") is True:
        return _classification(
            "unexpected_position_blocked",
            attention_required=True,
            hard_stop=False,
            reason_codes=["unexpected_non_spy_position"],
        )
    if record.get("open_order_present") is True:
        return _classification(
            "open_order_conflict_blocked",
            attention_required=True,
            hard_stop=False,
            reason_codes=["open_order_present"],
        )
    if (
        paper_submit_performed
        and reconciliation_status not in _CONFIRMED_RECONCILIATION_STATUSES
    ):
        return _classification(
            "reconciliation_required",
            attention_required=True,
            hard_stop=False,
            reason_codes=["paper_submit_without_confirmed_reconciliation"],
        )
    if (
        paper_submit_performed
        and reconciliation_status in _CONFIRMED_RECONCILIATION_STATUSES
    ):
        return _classification(
            "healthy_paper_action_reconciled",
            attention_required=False,
            hard_stop=False,
            reason_codes=["paper_action_reconciled"],
        )
    if (
        _text(record.get("action_decision")) == "hold/noop"
        and blocker_status in _HEALTHY_BLOCKERS
        and record.get("broker_state_observed") is True
    ):
        return _classification(
            "healthy_hold_noop",
            attention_required=False,
            hard_stop=False,
            reason_codes=["hold_noop_broker_observed"],
        )
    if blocker_status not in _HEALTHY_BLOCKERS:
        return _classification(
            "blocked_requires_operator_attention",
            attention_required=True,
            hard_stop=False,
            reason_codes=[f"blocker:{blocker_status}"],
        )

    return _classification(
        "blocked_requires_operator_attention",
        attention_required=True,
        hard_stop=False,
        reason_codes=["unclassified_operating_state"],
    )


def paper_autopilot_history_exit_status(rollup: Mapping[str, Any]) -> int:
    if rollup.get("hard_stop") is True:
        return 2
    if rollup.get("attention_required") is True:
        return 1
    return 0


def render_paper_autopilot_history_status(rollup: Mapping[str, Any]) -> str:
    """Render compact key=value status for scripts."""

    artifact_paths = _mapping(rollup.get("artifact_paths"))
    lines = [
        f"classification={_text(rollup.get('classification'))}",
        f"attention_required={str(rollup.get('attention_required') is True).lower()}",
        f"hard_stop={str(rollup.get('hard_stop') is True).lower()}",
        f"run_id={_text(rollup.get('run_id'))}",
        f"as_of_date={_text(rollup.get('as_of_date'))}",
        f"symbol={_text(rollup.get('symbol'))}",
        f"sma_posture={_text(rollup.get('sma_posture'))}",
        f"broker_state_mode={_text(rollup.get('broker_state_mode'))}",
        "broker_state_observed="
        f"{str(rollup.get('broker_state_observed') is True).lower()}",
        f"blocker_status={_text(rollup.get('blocker_status'))}",
        f"action_decision={_text(rollup.get('action_decision'))}",
        f"reconciliation_status={_text(rollup.get('reconciliation_status'))}",
        f"next_operator_action={_text(rollup.get('next_operator_action'))}",
        "reason_codes=" + ",".join(_string_list(rollup.get("reason_codes"))),
        f"operating_history={_text(artifact_paths.get('operating_history'))}",
        f"latest_rollup={_text(artifact_paths.get('latest_rollup'))}",
        f"operating_summary={_text(artifact_paths.get('operating_summary'))}",
    ]
    return "\n".join(lines) + "\n"


def render_paper_autopilot_operating_summary(rollup: Mapping[str, Any]) -> str:
    artifact_paths = _mapping(rollup.get("artifact_paths"))
    reason_codes = ", ".join(_string_list(rollup.get("reason_codes"))) or "none"
    return "\n".join(
        [
            "# Paper Autopilot Operating Summary",
            "",
            f"- Classification: `{_text(rollup.get('classification'))}`",
            f"- Attention required: `{str(rollup.get('attention_required') is True).lower()}`",
            f"- Hard stop: `{str(rollup.get('hard_stop') is True).lower()}`",
            f"- Run id: `{_text(rollup.get('run_id'))}`",
            f"- As-of date: `{_text(rollup.get('as_of_date'))}`",
            f"- Symbol: `{_text(rollup.get('symbol'))}`",
            f"- SMA posture: `{_text(rollup.get('sma_posture'))}`",
            f"- Broker-state mode: `{_text(rollup.get('broker_state_mode'))}`",
            f"- Broker state observed: `{str(rollup.get('broker_state_observed') is True).lower()}`",
            f"- Blocker status: `{_text(rollup.get('blocker_status'))}`",
            f"- Action decision: `{_text(rollup.get('action_decision'))}`",
            f"- Reconciliation status: `{_text(rollup.get('reconciliation_status'))}`",
            f"- Next operator action: `{_text(rollup.get('next_operator_action'))}`",
            f"- Reason codes: `{reason_codes}`",
            "",
            "Artifacts:",
            f"- Operating history: `{_text(artifact_paths.get('operating_history'))}`",
            f"- Latest rollup: `{_text(artifact_paths.get('latest_rollup'))}`",
            f"- Operating summary: `{_text(artifact_paths.get('operating_summary'))}`",
            "",
        ]
    )


def _load_status_payload(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "payload": {},
            "source_status_path": str(path),
            "source_status_sha256": "",
            "status_artifact_available": False,
            "status_artifact_valid": False,
            "status_artifact_error": "latest_status_artifact_missing",
        }
    content = path.read_bytes()
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
        valid = False
        error = "latest_status_artifact_invalid"
    else:
        valid = isinstance(payload, Mapping)
        error = "" if valid else "latest_status_artifact_not_object"
    return {
        "payload": dict(payload) if isinstance(payload, Mapping) else {},
        "source_status_path": str(path),
        "source_status_sha256": hashlib.sha256(content).hexdigest(),
        "status_artifact_available": True,
        "status_artifact_valid": valid,
        "status_artifact_error": error,
    }


def _normalize_status_payload(
    *,
    status_load: Mapping[str, Any],
    previous_record: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _mapping(status_load.get("payload"))
    broker_state = _mapping(payload.get("broker_state"))
    preflight = _mapping(payload.get("preflight"))
    execution_plan_summary = _mapping(payload.get("execution_plan_summary"))
    execution_plan = _mapping(payload.get("execution_plan"))
    action_result = _mapping(payload.get("action_result"))
    reconciliation = _mapping(payload.get("reconciliation"))
    generated_at = _text(payload.get("generated_at"))
    paper_profile_run = _bool(preflight.get("APP_PROFILE_is_paper")) or (
        _text(preflight.get("APP_PROFILE")) == "paper"
    )
    record = {
        "run_id": _text(payload.get("run_id")),
        "generated_at": generated_at,
        "as_of_date": _text(payload.get("as_of_date")),
        "symbol": _text(payload.get("symbol")),
        "sma_posture": _text(payload.get("sma_posture")),
        "broker_state_mode": _text(payload.get("broker_state_mode")),
        "broker_state_observed": _bool(payload.get("broker_state_observed")),
        "blocker_status": _text(payload.get("blocker_status")),
        "execution_plan_id": _first_nonempty_text(
            execution_plan_summary.get("execution_plan_id"),
            execution_plan.get("execution_plan_id"),
        ),
        "client_order_id": _first_nonempty_text(
            execution_plan_summary.get("client_order_id"),
            execution_plan.get("client_order_id"),
        ),
        "action_decision": _first_nonempty_text(
            payload.get("preview_action_decision"),
            action_result.get("action_decision"),
            execution_plan_summary.get("action"),
            execution_plan.get("action"),
        ),
        "paper_submit_authorized": _bool(payload.get("paper_submit_authorized")),
        "paper_submit_performed": _bool(payload.get("paper_submit_performed")),
        "broker_mutation_performed": _bool(payload.get("broker_mutation_performed")),
        "live_mutation_performed": _bool(payload.get("live_mutation_performed")),
        "live_trading_performed": _bool(payload.get("live_trading_performed")),
        "reconciliation_status": _first_nonempty_text(
            payload.get("reconciliation_status"),
            reconciliation.get("reconciliation_status"),
        ),
        "reconciliation_required": _bool(reconciliation.get("reconciliation_required"))
        or _text(payload.get("blocker_status")) == "blocked/reconciliation_required",
        "next_operator_action": _text(payload.get("next_operator_action")),
        "safety_labels": _string_list(payload.get("safety_labels")),
        "input_data_path": _text(payload.get("input_data_path")),
        "input_data_sha256": _text(payload.get("input_data_sha256")),
        "paper_profile_run": paper_profile_run,
        "unexpected_non_spy_position": bool(
            _string_list(broker_state.get("unexpected_non_spy_positions"))
        )
        or _text(payload.get("blocker_status"))
        == "blocked/unexpected_non_spy_position",
        "open_order_present": _bool(broker_state.get("open_spy_order_present"))
        or _text(payload.get("blocker_status")) == "blocked/open_order_present",
        "status_artifact_available": status_load.get("status_artifact_available")
        is True,
        "status_artifact_valid": status_load.get("status_artifact_valid") is True,
        "status_artifact_error": _text(status_load.get("status_artifact_error")),
        "source_status_path": _text(status_load.get("source_status_path")),
        "source_status_sha256": _text(status_load.get("source_status_sha256")),
    }
    record["status_artifact_stale"] = _status_artifact_stale(record, previous_record)
    return record


def _classification(
    classification: str,
    *,
    attention_required: bool,
    hard_stop: bool,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    if hard_stop:
        severity = "hard_stop"
    elif attention_required:
        severity = "attention_required"
    else:
        severity = "healthy"
    return {
        "classification": classification,
        "attention_required": attention_required,
        "hard_stop": hard_stop,
        "severity": severity,
        "reason_codes": list(reason_codes),
    }


def _status_artifact_stale(
    record: Mapping[str, Any],
    previous_record: Mapping[str, Any] | None,
) -> bool:
    if record.get("status_artifact_available") is not True:
        return False
    current_generated_at = _parse_datetime(_text(record.get("generated_at")))
    if current_generated_at is None:
        return True
    if previous_record is None:
        return False
    previous_generated_at = _parse_datetime(_text(previous_record.get("generated_at")))
    return previous_generated_at is not None and current_generated_at < previous_generated_at


def _compare_to_previous(
    entry: Mapping[str, Any],
    previous_record: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if previous_record is None:
        return {
            "previous_run_id": "",
            "previous_generated_at": "",
            "changed_fields": [],
            "classification_changed": False,
            "blocker_status_changed": False,
            "broker_state_mode_changed": False,
            "reconciliation_status_changed": False,
        }
    changed_fields = [
        field
        for field in _COMPARISON_FIELDS
        if entry.get(field) != previous_record.get(field)
    ]
    return {
        "previous_run_id": _text(previous_record.get("run_id")),
        "previous_generated_at": _text(previous_record.get("generated_at")),
        "changed_fields": changed_fields,
        "classification_changed": "classification" in changed_fields,
        "blocker_status_changed": "blocker_status" in changed_fields,
        "broker_state_mode_changed": "broker_state_mode" in changed_fields,
        "reconciliation_status_changed": "reconciliation_status" in changed_fields,
    }


def _build_rollup(
    *,
    entry: Mapping[str, Any],
    history_count: int,
    comparison: Mapping[str, Any],
    history_path: Path,
    rollup_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": PAPER_AUTOPILOT_HISTORY_SCHEMA_VERSION,
        "history_count": history_count,
        "classification": entry.get("classification"),
        "attention_required": entry.get("attention_required"),
        "hard_stop": entry.get("hard_stop"),
        "severity": entry.get("severity"),
        "reason_codes": list(_string_list(entry.get("reason_codes"))),
        "run_id": entry.get("run_id"),
        "generated_at": entry.get("generated_at"),
        "as_of_date": entry.get("as_of_date"),
        "symbol": entry.get("symbol"),
        "sma_posture": entry.get("sma_posture"),
        "broker_state_mode": entry.get("broker_state_mode"),
        "broker_state_observed": entry.get("broker_state_observed"),
        "blocker_status": entry.get("blocker_status"),
        "execution_plan_id": entry.get("execution_plan_id"),
        "client_order_id": entry.get("client_order_id"),
        "action_decision": entry.get("action_decision"),
        "paper_submit_authorized": entry.get("paper_submit_authorized"),
        "paper_submit_performed": entry.get("paper_submit_performed"),
        "broker_mutation_performed": entry.get("broker_mutation_performed"),
        "live_mutation_performed": entry.get("live_mutation_performed"),
        "live_trading_performed": entry.get("live_trading_performed"),
        "reconciliation_status": entry.get("reconciliation_status"),
        "next_operator_action": entry.get("next_operator_action"),
        "safety_labels": list(_string_list(entry.get("safety_labels"))),
        "input_data_path": entry.get("input_data_path"),
        "input_data_sha256": entry.get("input_data_sha256"),
        "comparison_to_previous": dict(comparison),
        "artifact_paths": {
            "operating_history": str(history_path),
            "latest_rollup": str(rollup_path),
            "operating_summary": str(summary_path),
        },
    }


def _read_history_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            records.append(dict(payload))
    return records


def _path(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a Path or string.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _bool(value: object) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False


def _string_list(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _first_nonempty_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "PAPER_AUTOPILOT_DEFAULT_HISTORY_ROOT",
    "PAPER_AUTOPILOT_DEFAULT_LATEST_STATUS_PATH",
    "PAPER_AUTOPILOT_HISTORY_SCHEMA_VERSION",
    "PaperAutopilotHistoryConfig",
    "classify_paper_autopilot_operating_record",
    "paper_autopilot_history_exit_status",
    "render_paper_autopilot_history_status",
    "render_paper_autopilot_operating_summary",
    "update_paper_autopilot_operating_history",
]
