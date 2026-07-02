"""Durable operating history for the bounded paper-autopilot loop.

The history layer consumes the loop's latest_status.json artifact and writes
offline-only rollups. It does not import broker SDKs or perform network IO.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
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
PAPER_AUTOPILOT_DAILY_AUTONOMY_LEDGER_FILENAME = "daily_autonomy_ledger.jsonl"
PAPER_AUTOPILOT_LATEST_DAILY_AUTONOMY_FILENAME = "latest_daily_autonomy.json"
PAPER_AUTOPILOT_DAILY_AUTONOMY_SUMMARY_FILENAME = "daily_autonomy_summary.md"

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
    "latest_bar_date",
    "data_refresh_status",
    "data_freshness_status",
    "sma_posture",
    "selected_strategy_id",
    "strategy_route_action",
    "broker_state_mode",
    "broker_state_observed",
    "spy_position_observed",
    "spy_position_quantity",
    "open_spy_orders_observed",
    "unexpected_non_spy_positions_count",
    "blocker_status",
    "final_supervisor_status",
    "broker_observed_supervisor_status",
    "execution_plan_action",
    "action_decision",
    "reconciliation_status",
    "classification",
    "final_supervisor_classification",
    "vol_scaled_preview_intended_action",
    "broker_mutation_performed",
    "paper_submit_performed",
    "live_mutation_performed",
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
    autonomy_ledger_path = (
        history_root / PAPER_AUTOPILOT_DAILY_AUTONOMY_LEDGER_FILENAME
    )
    autonomy_latest_path = history_root / PAPER_AUTOPILOT_LATEST_DAILY_AUTONOMY_FILENAME
    autonomy_summary_path = history_root / PAPER_AUTOPILOT_DAILY_AUTONOMY_SUMMARY_FILENAME
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
    autonomy = classify_paper_autopilot_autonomy_record(
        normalized,
        previous_record=previous_record,
    )
    entry = {
        **normalized,
        **classification,
        **autonomy,
        "history_schema_version": PAPER_AUTOPILOT_HISTORY_SCHEMA_VERSION,
        "history_sequence": len(previous_records) + 1,
    }
    comparison = _compare_to_previous(entry, previous_record)
    entry["comparison_to_previous"] = comparison
    entry["changed_since_previous"] = comparison["changed_since_previous"]
    autonomy_entry = _build_daily_autonomy_ledger_entry(entry, comparison)

    with history_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    with autonomy_ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(autonomy_entry, sort_keys=True, separators=(",", ":")) + "\n"
        )
    autonomy_latest_path.write_text(
        json.dumps(autonomy_entry, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    autonomy_summary_path.write_text(
        render_paper_autopilot_daily_autonomy_summary(autonomy_entry),
        encoding="utf-8",
        newline="\n",
    )

    rollup = _build_rollup(
        entry=entry,
        history_count=len(previous_records) + 1,
        comparison=comparison,
        history_path=history_path,
        rollup_path=rollup_path,
        summary_path=summary_path,
        autonomy_ledger_path=autonomy_ledger_path,
        autonomy_latest_path=autonomy_latest_path,
        autonomy_summary_path=autonomy_summary_path,
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
    if blocker_status == "blocked/mutation_would_be_required_no_submit_mode":
        return _classification(
            "mutation_would_be_required_no_submit_mode",
            attention_required=True,
            hard_stop=False,
            reason_codes=["mutation_would_be_required_no_submit_mode"],
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


def classify_paper_autopilot_autonomy_record(
    record: Mapping[str, Any],
    *,
    previous_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify the deterministic daily next action without broker mutation."""

    del previous_record
    blocker_status = _text(record.get("blocker_status"))
    reason_codes: list[str] = []

    if record.get("status_artifact_available") is not True:
        return _autonomy_classification(
            "blocked_refresh_or_validate_daily_bars",
            "refresh_or_validate_daily_bars",
            attention_required=True,
            hard_stop=False,
            reason_codes=["latest_status_artifact_missing"],
        )
    if record.get("status_artifact_valid") is not True:
        return _autonomy_classification(
            "blocked_refresh_or_validate_daily_bars",
            "refresh_or_validate_daily_bars",
            attention_required=True,
            hard_stop=False,
            reason_codes=["latest_status_artifact_invalid"],
        )
    if record.get("status_artifact_stale") is True:
        return _autonomy_classification(
            "blocked_refresh_or_validate_daily_bars",
            "refresh_or_validate_daily_bars",
            attention_required=True,
            hard_stop=False,
            reason_codes=["latest_status_artifact_stale"],
        )

    safety_labels = set(_string_list(record.get("safety_labels")))
    missing_labels = sorted(_REQUIRED_SAFETY_LABELS - safety_labels)
    if record.get("live_mutation_performed") is True:
        reason_codes.append("live_mutation_performed")
    if record.get("live_trading_performed") is True:
        reason_codes.append("live_trading_performed")
    if record.get("no_submit_mode") is True and record.get("paper_submit_performed") is True:
        reason_codes.append("paper_submit_performed_in_no_submit_mode")
    if record.get("no_submit_mode") is True and record.get("broker_mutation_performed") is True:
        reason_codes.append("broker_mutation_performed_in_no_submit_mode")
    if record.get("vol_scaled_preview_mutation_allowed") is True:
        reason_codes.append("vol_scaled_preview_mutation_allowed")
    if record.get("vol_scaled_preview_submit_allowed") is True:
        reason_codes.append("vol_scaled_preview_submit_allowed")
    reason_codes.extend(f"missing_safety_label:{label}" for label in missing_labels)
    if blocker_status == "blocked/live_safety":
        reason_codes.append("blocker_live_safety")
    if reason_codes:
        return _autonomy_classification(
            "hard_stop_safety_invariant",
            "stop_and_review_safety_invariant",
            attention_required=True,
            hard_stop=True,
            reason_codes=reason_codes,
        )

    if _data_refresh_or_freshness_blocked(record):
        return _autonomy_classification(
            "blocked_refresh_or_validate_daily_bars",
            "refresh_or_validate_daily_bars",
            attention_required=True,
            hard_stop=False,
            reason_codes=["daily_bars_refresh_or_freshness_blocked"],
        )

    if record.get("expected_account_matched") is False or blocker_status in {
        "blocked/expected_account_mismatch",
        "blocked/expected_account_match_not_observed",
    }:
        return _autonomy_classification(
            "blocked_expected_account_mismatch",
            "stop_and_review_expected_paper_account_before_any_submit",
            attention_required=True,
            hard_stop=False,
            reason_codes=[blocker_status.replace("/", "_") or "expected_account_mismatch"],
        )

    if (
        record.get("open_order_present") is True
        or _int(record.get("open_spy_orders_observed")) > 0
        or blocker_status == "blocked/open_order_present"
    ):
        return _autonomy_classification(
            "blocked_open_spy_order_present",
            "reconcile_existing_spy_open_order_before_submit",
            attention_required=True,
            hard_stop=False,
            reason_codes=["open_spy_order_present"],
        )

    if (
        record.get("unexpected_non_spy_position") is True
        or _int(record.get("unexpected_non_spy_positions_count")) > 0
        or blocker_status == "blocked/unexpected_non_spy_position"
    ):
        return _autonomy_classification(
            "blocked_unexpected_non_spy_position",
            "operator_review_non_spy_position",
            attention_required=True,
            hard_stop=False,
            reason_codes=["unexpected_non_spy_position"],
        )

    if blocker_status == "blocked/expected_account_id_unavailable":
        return _autonomy_classification(
            "blocked_configure_verified_paper_profile",
            "configure_expected_paper_account_id_then_rerun",
            attention_required=True,
            hard_stop=False,
            reason_codes=["expected_account_id_unavailable"],
        )

    if record.get("broker_state_observed") is not True:
        return _autonomy_classification(
            "blocked_configure_verified_paper_profile",
            "configure_verified_paper_profile_then_rerun",
            attention_required=True,
            hard_stop=False,
            reason_codes=["broker_state_not_observed"],
        )

    if blocker_status in {
        "blocked/account_status_not_active",
        "blocked/reconciliation_required",
    }:
        return _autonomy_classification(
            "blocked_configure_verified_paper_profile",
            _first_nonempty_text(
                record.get("final_operator_action"),
                "stop_and_review_paper_account_or_reconciliation",
            ),
            attention_required=True,
            hard_stop=False,
            reason_codes=[blocker_status.replace("/", "_")],
        )

    mutation_required_no_submit = (
        record.get("mutation_would_be_required_without_no_submit") is True
        or blocker_status == "blocked/mutation_would_be_required_no_submit_mode"
    )
    if record.get("no_submit_mode") is True and mutation_required_no_submit:
        return _autonomy_classification(
            "paper_mutation_would_be_required_no_submit_mode",
            "review_visibility_only_intended_action_no_submit_mode",
            attention_required=True,
            hard_stop=False,
            reason_codes=["mutation_would_be_required_no_submit_mode"],
        )

    execution_plan_action = _text(record.get("execution_plan_action"))
    if (
        execution_plan_action in {"buy", "sell_close"}
        and record.get("paper_submit_performed") is not True
    ):
        return _autonomy_classification(
            "paper_mutation_candidate_requires_explicit_authorized_run",
            "run_explicit_authorized_bounded_paper_mutation_after_operator_approval",
            attention_required=True,
            hard_stop=False,
            reason_codes=[f"paper_{execution_plan_action}_candidate_not_submitted"],
        )

    if blocker_status not in _HEALTHY_BLOCKERS and blocker_status != "action/submitted":
        return _autonomy_classification(
            "blocked_configure_verified_paper_profile",
            _first_nonempty_text(record.get("final_operator_action"), "review_blocker"),
            attention_required=True,
            hard_stop=False,
            reason_codes=[f"blocker:{blocker_status}"],
        )

    healthy_reason = _healthy_autonomy_reason(record)
    return _autonomy_classification(
        "healthy_continue_next_daily_cycle",
        "continue_next_daily_cycle",
        attention_required=False,
        hard_stop=False,
        reason_codes=[healthy_reason],
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
        f"autonomy_status={_text(rollup.get('autonomy_status'))}",
        f"autonomy_next_action={_text(rollup.get('autonomy_next_action'))}",
        "changed_since_previous="
        f"{str(rollup.get('changed_since_previous') is True).lower()}",
        "final_supervisor_classification="
        f"{_text(rollup.get('final_supervisor_classification'))}",
        f"attention_required={str(rollup.get('attention_required') is True).lower()}",
        f"hard_stop={str(rollup.get('hard_stop') is True).lower()}",
        f"run_id={_text(rollup.get('run_id'))}",
        f"as_of_date={_text(rollup.get('as_of_date'))}",
        f"latest_bar_date={_text(rollup.get('latest_bar_date'))}",
        f"data_refresh_status={_text(rollup.get('data_refresh_status'))}",
        f"data_freshness_status={_text(rollup.get('data_freshness_status'))}",
        f"symbol={_text(rollup.get('symbol'))}",
        f"sma_posture={_text(rollup.get('sma_posture'))}",
        f"operating_mode={_text(rollup.get('operating_mode'))}",
        f"broker_state_mode={_text(rollup.get('broker_state_mode'))}",
        "broker_state_observed="
        f"{str(rollup.get('broker_state_observed') is True).lower()}",
        "broker_read_performed="
        f"{str(rollup.get('broker_read_performed') is True).lower()}",
        f"expected_account_matched={_bool_text(rollup.get('expected_account_matched'))}",
        "spy_position_observed="
        f"{str(rollup.get('spy_position_observed') is True).lower()}",
        f"spy_position_quantity={_text(rollup.get('spy_position_quantity'))}",
        f"open_spy_orders_observed={_text(rollup.get('open_spy_orders_observed'))}",
        "unexpected_non_spy_positions_count="
        f"{_text(rollup.get('unexpected_non_spy_positions_count'))}",
        "unexpected_non_spy_positions="
        + ",".join(_string_list(rollup.get("unexpected_non_spy_positions"))),
        f"selected_strategy_id={_text(rollup.get('selected_strategy_id'))}",
        f"strategy_route_action={_text(rollup.get('strategy_route_action'))}",
        "pre_broker_daily_cycle_status="
        f"{_text(rollup.get('pre_broker_daily_cycle_status'))}",
        "pre_broker_daily_cycle_classification="
        f"{_text(rollup.get('pre_broker_daily_cycle_classification'))}",
        f"blocker_status={_text(rollup.get('blocker_status'))}",
        f"final_supervisor_status={_text(rollup.get('final_supervisor_status'))}",
        "broker_observed_supervisor_status="
        f"{_text(rollup.get('broker_observed_supervisor_status'))}",
        f"execution_plan_action={_text(rollup.get('execution_plan_action'))}",
        f"action_decision={_text(rollup.get('action_decision'))}",
        "vol_scaled_preview_visible="
        f"{str(rollup.get('vol_scaled_preview_visible') is True).lower()}",
        "vol_scaled_preview_intended_action="
        f"{_text(rollup.get('vol_scaled_preview_intended_action'))}",
        "vol_scaled_preview_mutation_allowed="
        f"{str(rollup.get('vol_scaled_preview_mutation_allowed') is True).lower()}",
        "vol_scaled_preview_submit_allowed="
        f"{str(rollup.get('vol_scaled_preview_submit_allowed') is True).lower()}",
        "vol_scaled_preview_non_mutation_status="
        f"{_text(rollup.get('vol_scaled_preview_non_mutation_status'))}",
        f"reconciliation_status={_text(rollup.get('reconciliation_status'))}",
        f"next_operator_action={_text(rollup.get('next_operator_action'))}",
        f"final_operator_action={_text(rollup.get('final_operator_action'))}",
        "reason_codes=" + ",".join(_string_list(rollup.get("reason_codes"))),
        "autonomy_reason_codes="
        + ",".join(_string_list(rollup.get("autonomy_reason_codes"))),
        "latest_bar_date_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('latest_bar_date_changed') is True).lower()}",
        "broker_state_mode_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('broker_state_mode_changed') is True).lower()}",
        "spy_position_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('spy_position_changed') is True).lower()}",
        "open_orders_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('open_orders_changed') is True).lower()}",
        "selected_strategy_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('selected_strategy_changed') is True).lower()}",
        "execution_plan_action_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('execution_plan_action_changed') is True).lower()}",
        "final_supervisor_classification_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('final_supervisor_classification_changed') is True).lower()}",
        "blocker_status_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('blocker_status_changed') is True).lower()}",
        "vol_scaled_preview_action_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('vol_scaled_preview_action_changed') is True).lower()}",
        "mutation_flags_changed="
        f"{str(_mapping(rollup.get('comparison_to_previous')).get('mutation_flags_changed') is True).lower()}",
        f"operating_history={_text(artifact_paths.get('operating_history'))}",
        f"daily_autonomy_ledger={_text(artifact_paths.get('daily_autonomy_ledger'))}",
        f"latest_daily_autonomy={_text(artifact_paths.get('latest_daily_autonomy'))}",
        f"daily_autonomy_summary={_text(artifact_paths.get('daily_autonomy_summary'))}",
        f"latest_rollup={_text(artifact_paths.get('latest_rollup'))}",
        f"operating_summary={_text(artifact_paths.get('operating_summary'))}",
    ]
    return "\n".join(lines) + "\n"


def render_paper_autopilot_operating_summary(rollup: Mapping[str, Any]) -> str:
    artifact_paths = _mapping(rollup.get("artifact_paths"))
    reason_codes = ", ".join(_string_list(rollup.get("reason_codes"))) or "none"
    autonomy_reason_codes = (
        ", ".join(_string_list(rollup.get("autonomy_reason_codes"))) or "none"
    )
    return "\n".join(
        [
            "# Paper Autopilot Operating Summary",
            "",
            f"- Classification: `{_text(rollup.get('classification'))}`",
            f"- Autonomy status: `{_text(rollup.get('autonomy_status'))}`",
            f"- Autonomy next action: `{_text(rollup.get('autonomy_next_action'))}`",
            f"- Changed since previous: `{str(rollup.get('changed_since_previous') is True).lower()}`",
            f"- Final supervisor classification: `{_text(rollup.get('final_supervisor_classification'))}`",
            f"- Attention required: `{str(rollup.get('attention_required') is True).lower()}`",
            f"- Hard stop: `{str(rollup.get('hard_stop') is True).lower()}`",
            f"- Run id: `{_text(rollup.get('run_id'))}`",
            f"- As-of date: `{_text(rollup.get('as_of_date'))}`",
            f"- Latest bar date: `{_text(rollup.get('latest_bar_date'))}`",
            f"- Data refresh status: `{_text(rollup.get('data_refresh_status'))}`",
            f"- Data freshness status: `{_text(rollup.get('data_freshness_status'))}`",
            f"- Symbol: `{_text(rollup.get('symbol'))}`",
            f"- SMA posture: `{_text(rollup.get('sma_posture'))}`",
            f"- Selected strategy: `{_text(rollup.get('selected_strategy_id'))}`",
            f"- Operating mode: `{_text(rollup.get('operating_mode'))}`",
            f"- Broker-state mode: `{_text(rollup.get('broker_state_mode'))}`",
            f"- Broker state observed: `{str(rollup.get('broker_state_observed') is True).lower()}`",
            f"- Broker read performed: `{str(rollup.get('broker_read_performed') is True).lower()}`",
            f"- Expected account matched: `{_bool_text(rollup.get('expected_account_matched'))}`",
            f"- SPY position observed: `{str(rollup.get('spy_position_observed') is True).lower()}`",
            f"- SPY position quantity: `{_text(rollup.get('spy_position_quantity'))}`",
            f"- Open SPY orders observed: `{_text(rollup.get('open_spy_orders_observed'))}`",
            f"- Unexpected non-SPY positions: `{', '.join(_string_list(rollup.get('unexpected_non_spy_positions'))) or 'none'}`",
            f"- Pre-broker daily-cycle status: `{_text(rollup.get('pre_broker_daily_cycle_status'))}`",
            f"- Pre-broker daily-cycle classification: `{_text(rollup.get('pre_broker_daily_cycle_classification'))}`",
            f"- Blocker status: `{_text(rollup.get('blocker_status'))}`",
            f"- Final supervisor status: `{_text(rollup.get('final_supervisor_status'))}`",
            f"- Broker-observed supervisor status: `{_text(rollup.get('broker_observed_supervisor_status'))}`",
            f"- Execution plan action: `{_text(rollup.get('execution_plan_action'))}`",
            f"- Action decision: `{_text(rollup.get('action_decision'))}`",
            f"- Vol-scaled preview visible: `{str(rollup.get('vol_scaled_preview_visible') is True).lower()}`",
            f"- Vol-scaled preview intended action: `{_text(rollup.get('vol_scaled_preview_intended_action'))}`",
            f"- Vol-scaled preview mutation allowed: `{str(rollup.get('vol_scaled_preview_mutation_allowed') is True).lower()}`",
            f"- Vol-scaled preview submit allowed: `{str(rollup.get('vol_scaled_preview_submit_allowed') is True).lower()}`",
            f"- Vol-scaled preview non-mutation status: `{_text(rollup.get('vol_scaled_preview_non_mutation_status'))}`",
            f"- Reconciliation status: `{_text(rollup.get('reconciliation_status'))}`",
            f"- Next operator action: `{_text(rollup.get('next_operator_action'))}`",
            f"- Final operator action: `{_text(rollup.get('final_operator_action'))}`",
            f"- Reason codes: `{reason_codes}`",
            f"- Autonomy reason codes: `{autonomy_reason_codes}`",
            "",
            "Artifacts:",
            f"- Operating history: `{_text(artifact_paths.get('operating_history'))}`",
            f"- Daily autonomy ledger: `{_text(artifact_paths.get('daily_autonomy_ledger'))}`",
            f"- Latest daily autonomy: `{_text(artifact_paths.get('latest_daily_autonomy'))}`",
            f"- Daily autonomy summary: `{_text(artifact_paths.get('daily_autonomy_summary'))}`",
            f"- Latest rollup: `{_text(artifact_paths.get('latest_rollup'))}`",
            f"- Operating summary: `{_text(artifact_paths.get('operating_summary'))}`",
            "",
        ]
    )


def render_paper_autopilot_daily_autonomy_summary(
    entry: Mapping[str, Any],
) -> str:
    reason_codes = ", ".join(_string_list(entry.get("reason_codes"))) or "none"
    return "\n".join(
        [
            "# Daily Autonomy Summary",
            "",
            f"- Autonomy status: `{_text(entry.get('autonomy_status'))}`",
            f"- Autonomy next action: `{_text(entry.get('autonomy_next_action'))}`",
            f"- Changed since previous: `{str(entry.get('changed_since_previous') is True).lower()}`",
            f"- Hard stop: `{str(entry.get('hard_stop') is True).lower()}`",
            f"- Attention required: `{str(entry.get('attention_required') is True).lower()}`",
            f"- Reason codes: `{reason_codes}`",
            f"- Run id: `{_text(entry.get('run_id'))}`",
            f"- As-of date: `{_text(entry.get('as_of_date'))}`",
            f"- Latest bar date: `{_text(entry.get('latest_bar_date'))}`",
            f"- Broker-state mode: `{_text(entry.get('broker_state_mode'))}`",
            f"- Execution plan action: `{_text(entry.get('execution_plan_action'))}`",
            f"- Action decision: `{_text(entry.get('action_decision'))}`",
            f"- Final supervisor classification: `{_text(entry.get('final_supervisor_classification'))}`",
            f"- Final operator action: `{_text(entry.get('final_operator_action'))}`",
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
    daily_cycle = _mapping(payload.get("daily_cycle"))
    route_receipt = _mapping(payload.get("strategy_route_receipt"))
    execution_plan_summary = _mapping(payload.get("execution_plan_summary"))
    execution_plan = _mapping(payload.get("execution_plan"))
    action_result = _mapping(payload.get("action_result"))
    reconciliation = _mapping(payload.get("reconciliation"))
    vol_scaled_preview = _mapping(payload.get("vol_scaled_preview"))
    vol_scaled_trend_signal = _mapping(payload.get("vol_scaled_trend_signal"))
    generated_at = _text(payload.get("generated_at"))
    paper_profile_run = _bool(preflight.get("APP_PROFILE_is_paper")) or (
        _text(preflight.get("APP_PROFILE")) == "paper"
    )
    no_submit_mode = (
        _bool(payload.get("no_submit_mode"))
        or _bool(execution_plan_summary.get("no_submit_mode"))
        or _bool(execution_plan.get("no_submit_mode"))
    )
    blocker_status = _text(payload.get("blocker_status"))
    final_supervisor_status = _first_nonempty_text(
        payload.get("final_supervisor_status"),
        blocker_status,
    )
    pre_broker_daily_cycle_status = _first_nonempty_text(
        payload.get("pre_broker_daily_cycle_status"),
        _pre_broker_daily_cycle_status(daily_cycle),
    )
    expected_account_matched = payload.get("expected_account_matched")
    if expected_account_matched in (None, ""):
        expected_account_matched = broker_state.get("expected_account_matched")
    unexpected_non_spy_positions = _string_list(
        _first_present(
            broker_state,
            "unexpected_non_spy_positions",
            "unexpected_non_spy_position_symbols",
        )
    ) or _string_list(payload.get("unexpected_non_spy_positions"))
    open_spy_orders_observed = _first_nonempty_text(
        payload.get("open_spy_orders_observed"),
        broker_state.get("open_spy_orders_observed"),
    )
    if (
        _int(open_spy_orders_observed) == 0
        and _bool(broker_state.get("open_spy_order_present"))
    ):
        open_spy_orders_observed = "1"
    broker_state_observed = (
        _bool(payload.get("broker_state_observed"))
        if payload.get("broker_state_observed") not in (None, "")
        else _bool(broker_state.get("broker_state_observed"))
    )
    record = {
        "run_id": _text(payload.get("run_id")),
        "generated_at": generated_at,
        "as_of_date": _text(payload.get("as_of_date")),
        "latest_bar_date": _first_nonempty_text(
            payload.get("latest_bar_date"),
            payload.get("data_latest_bar"),
            daily_cycle.get("daily_cycle_latest_bar_date"),
            payload.get("as_of_date"),
        ),
        "data_refresh_status": _first_nonempty_text(
            payload.get("data_refresh_status"),
            daily_cycle.get("daily_cycle_data_refresh_status"),
        ),
        "data_freshness_status": _first_nonempty_text(
            payload.get("data_freshness_status"),
            daily_cycle.get("daily_cycle_data_freshness_status"),
        ),
        "symbol": _text(payload.get("symbol")),
        "sma_posture": _text(payload.get("sma_posture")),
        "operating_mode": _first_nonempty_text(
            payload.get("operating_mode"),
            _operating_mode(no_submit_mode),
        ),
        "broker_state_mode": _first_nonempty_text(
            payload.get("broker_state_mode"),
            broker_state.get("broker_state_mode"),
        ),
        "broker_state_observed": broker_state_observed,
        "expected_account_matched": _bool_or_none(expected_account_matched),
        "selected_strategy_id": _text(payload.get("selected_strategy_id")),
        "strategy_route_action": _first_nonempty_text(
            payload.get("strategy_route_action"),
            route_receipt.get("route_action"),
        ),
        "pre_broker_daily_cycle_status": pre_broker_daily_cycle_status,
        "pre_broker_daily_cycle_classification": _first_nonempty_text(
            payload.get("pre_broker_daily_cycle_classification"),
            _pre_broker_daily_cycle_classification(pre_broker_daily_cycle_status),
        ),
        "blocker_status": blocker_status,
        "final_supervisor_status": final_supervisor_status,
        "broker_observed_supervisor_status": _first_nonempty_text(
            payload.get("broker_observed_supervisor_status"),
            _broker_observed_supervisor_status(
                broker_state_observed=broker_state_observed,
                final_supervisor_status=final_supervisor_status,
            ),
        ),
        "final_supervisor_classification": _first_nonempty_text(
            payload.get("final_supervisor_classification"),
            payload.get("final_classification"),
            payload.get("classification"),
        ),
        "execution_plan_id": _first_nonempty_text(
            execution_plan_summary.get("execution_plan_id"),
            execution_plan.get("execution_plan_id"),
        ),
        "client_order_id": _first_nonempty_text(
            execution_plan_summary.get("client_order_id"),
            execution_plan.get("client_order_id"),
        ),
        "no_submit_mode": no_submit_mode,
        "broker_read_performed": _bool(payload.get("broker_read_performed")),
        "spy_position_observed": _bool(payload.get("spy_position_observed"))
        or _bool(broker_state.get("spy_position_present")),
        "spy_position_quantity": _first_nonempty_text(
            payload.get("spy_position_quantity"),
            broker_state.get("spy_position_quantity"),
        ),
        "open_spy_orders_observed": _int(open_spy_orders_observed),
        "unexpected_non_spy_positions": unexpected_non_spy_positions,
        "unexpected_non_spy_positions_count": _int(
            payload.get("unexpected_non_spy_positions_observed")
        )
        or len(unexpected_non_spy_positions),
        "execution_plan_action": _first_nonempty_text(
            payload.get("execution_plan_action"),
            execution_plan_summary.get("action"),
            execution_plan.get("action"),
        ),
        "intended_mutation_action": _first_nonempty_text(
            payload.get("intended_mutation_action"),
            execution_plan_summary.get("intended_mutation_action"),
            execution_plan.get("intended_mutation_action"),
        ),
        "mutation_would_be_required_without_no_submit": _bool(
            payload.get("mutation_would_be_required_without_no_submit")
        )
        or _bool(
            execution_plan_summary.get(
                "mutation_would_be_required_without_no_submit"
            )
        )
        or _bool(
            execution_plan.get("mutation_would_be_required_without_no_submit")
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
        "vol_scaled_preview_visible": _bool(
            payload.get("vol_scaled_preview_visible")
        )
        or _bool(vol_scaled_preview.get("visible")),
        "vol_scaled_preview_intended_action": _first_nonempty_text(
            payload.get("vol_scaled_preview_intended_action"),
            vol_scaled_preview.get("intended_action"),
            vol_scaled_trend_signal.get("intended_action"),
        ),
        "vol_scaled_preview_mutation_allowed": _bool(
            payload.get("vol_scaled_preview_mutation_allowed")
        )
        or _bool(vol_scaled_preview.get("mutation_allowed")),
        "vol_scaled_preview_submit_allowed": _bool(
            payload.get("vol_scaled_preview_submit_allowed")
        )
        or _bool(vol_scaled_preview.get("submit_allowed")),
        "vol_scaled_preview_non_mutation_status": _first_nonempty_text(
            payload.get("vol_scaled_preview_non_mutation_status"),
            vol_scaled_preview.get("non_mutation_status"),
        ),
        "reconciliation_status": _first_nonempty_text(
            payload.get("reconciliation_status"),
            reconciliation.get("reconciliation_status"),
        ),
        "reconciliation_required": _bool(reconciliation.get("reconciliation_required"))
        or blocker_status == "blocked/reconciliation_required",
        "next_operator_action": _text(payload.get("next_operator_action")),
        "final_operator_action": _first_nonempty_text(
            payload.get("final_operator_action"),
            payload.get("next_operator_action"),
        ),
        "safety_labels": _string_list(payload.get("safety_labels")),
        "input_data_path": _text(payload.get("input_data_path")),
        "input_data_sha256": _text(payload.get("input_data_sha256")),
        "paper_profile_run": paper_profile_run,
        "unexpected_non_spy_position": bool(
            unexpected_non_spy_positions
        )
        or _text(payload.get("blocker_status"))
        == "blocked/unexpected_non_spy_position",
        "open_order_present": _bool(broker_state.get("open_spy_order_present"))
        or blocker_status == "blocked/open_order_present",
        "status_artifact_available": status_load.get("status_artifact_available")
        is True,
        "status_artifact_valid": status_load.get("status_artifact_valid") is True,
        "status_artifact_error": _text(status_load.get("status_artifact_error")),
        "source_status_path": _text(status_load.get("source_status_path")),
        "source_status_sha256": _text(status_load.get("source_status_sha256")),
    }
    record["status_artifact_stale"] = _status_artifact_stale(record, previous_record)
    return record


def _operating_mode(no_submit: bool) -> str:
    return "visibility/no_submit" if no_submit else "bounded_paper_mutation"


def _pre_broker_daily_cycle_status(daily_cycle: Mapping[str, Any]) -> str:
    blocker_status = _text(daily_cycle.get("daily_cycle_blocker_status"))
    if blocker_status and blocker_status != "none":
        return blocker_status
    for field_name in (
        "daily_cycle_data_refresh_status",
        "daily_cycle_data_freshness_status",
        "daily_cycle_preview_decision",
    ):
        status = _text(daily_cycle.get(field_name))
        if status:
            return status
    return "none" if daily_cycle.get("daily_cycle_ran") is True else ""


def _pre_broker_daily_cycle_classification(status: str) -> str:
    normalized = _normalized_status(status)
    if normalized in {
        "",
        "none",
        "no_refresh_required",
        "accepted_data_current",
        "fake_daily_cycle_ran",
    }:
        return "pre_broker_daily_cycle_ready"
    if "broker_state_not_observed" in normalized:
        return "pre_broker_broker_state_not_observed_context"
    if normalized == "no_new_completed_bar_noop":
        return "pre_broker_no_new_completed_bar_noop"
    if (
        "stale" in normalized
        or "invalid" in normalized
        or normalized.startswith("blocked_future")
    ):
        return "pre_broker_data_freshness_blocked"
    if normalized.startswith("blocked"):
        return "pre_broker_daily_cycle_blocked"
    return "pre_broker_daily_cycle_context"


def _broker_observed_supervisor_status(
    *,
    broker_state_observed: bool,
    final_supervisor_status: str,
) -> str:
    if broker_state_observed:
        return final_supervisor_status
    return "broker_state_not_observed"


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


def _autonomy_classification(
    autonomy_status: str,
    autonomy_next_action: str,
    *,
    attention_required: bool,
    hard_stop: bool,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    return {
        "autonomy_status": autonomy_status,
        "autonomy_next_action": autonomy_next_action,
        "autonomy_attention_required": attention_required,
        "autonomy_hard_stop": hard_stop,
        "autonomy_reason_codes": list(reason_codes),
    }


def _data_refresh_or_freshness_blocked(record: Mapping[str, Any]) -> bool:
    statuses = {
        _normalized_status(record.get("data_refresh_status")),
        _normalized_status(record.get("data_freshness_status")),
        _normalized_status(record.get("pre_broker_daily_cycle_status")),
        _normalized_status(record.get("pre_broker_daily_cycle_classification")),
        _normalized_status(record.get("blocker_status")),
    }
    explicit_blockers = {
        "blocked_stale_data_preview_only",
        "blocked_blocked_future_dated_local_data",
        "blocked_accepted_but_stale",
        "blocked_stale_or_invalid_data",
        "blocked/stale_data_preview_only",
        "blocked/blocked_future_dated_local_data",
        "blocked/accepted_but_stale",
        "blocked/stale_or_invalid_data",
        "stale_data_preview_only",
        "blocked_future_dated_local_data",
        "accepted_but_stale",
        "stale_or_invalid_data",
        "pre_broker_data_freshness_blocked",
    }
    if statuses & explicit_blockers:
        return True
    return any(
        status
        and status not in {"none", "accepted_data_current", "no_refresh_required"}
        and ("stale" in status or "invalid" in status)
        for status in statuses
    )


def _healthy_autonomy_reason(record: Mapping[str, Any]) -> str:
    posture = _normalized_status(record.get("sma_posture"))
    action_decision = _normalized_status(record.get("action_decision"))
    has_spy_position = record.get("spy_position_observed") is True or _decimal_gt_zero(
        record.get("spy_position_quantity")
    )
    if posture == "risk_on" and has_spy_position and action_decision in {
        "hold/noop",
        "hold_noop",
    }:
        return "risk_on_spy_position_already_held"
    if posture == "risk_off" and not has_spy_position and action_decision in {
        "hold/noop",
        "hold_noop",
    }:
        return "risk_off_no_spy_position_noop"
    if record.get("paper_submit_performed") is True:
        return "paper_action_completed_or_reconciled"
    return "no_action_required_no_mutation"


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
            "changed_since_previous": False,
            "latest_bar_date_changed": False,
            "classification_changed": False,
            "blocker_status_changed": False,
            "broker_state_mode_changed": False,
            "spy_position_changed": False,
            "open_orders_changed": False,
            "selected_strategy_changed": False,
            "execution_plan_action_changed": False,
            "final_supervisor_classification_changed": False,
            "vol_scaled_preview_action_changed": False,
            "mutation_flags_changed": False,
            "reconciliation_status_changed": False,
        }
    changed_fields = [
        field
        for field in _COMPARISON_FIELDS
        if entry.get(field) != previous_record.get(field)
    ]
    mutation_flag_fields = {
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_mutation_performed",
    }
    return {
        "previous_run_id": _text(previous_record.get("run_id")),
        "previous_generated_at": _text(previous_record.get("generated_at")),
        "changed_fields": changed_fields,
        "changed_since_previous": bool(changed_fields),
        "latest_bar_date_changed": "latest_bar_date" in changed_fields,
        "classification_changed": "classification" in changed_fields,
        "blocker_status_changed": "blocker_status" in changed_fields,
        "broker_state_mode_changed": "broker_state_mode" in changed_fields,
        "spy_position_changed": (
            "spy_position_observed" in changed_fields
            or "spy_position_quantity" in changed_fields
        ),
        "open_orders_changed": "open_spy_orders_observed" in changed_fields,
        "selected_strategy_changed": "selected_strategy_id" in changed_fields,
        "execution_plan_action_changed": "execution_plan_action" in changed_fields,
        "final_supervisor_classification_changed": (
            "final_supervisor_classification" in changed_fields
        ),
        "vol_scaled_preview_action_changed": (
            "vol_scaled_preview_intended_action" in changed_fields
        ),
        "mutation_flags_changed": bool(mutation_flag_fields & set(changed_fields)),
        "reconciliation_status_changed": "reconciliation_status" in changed_fields,
    }


def _build_daily_autonomy_ledger_entry(
    entry: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    hard_stop = entry.get("hard_stop") is True or entry.get("autonomy_hard_stop") is True
    attention_required = (
        entry.get("attention_required") is True
        or entry.get("autonomy_attention_required") is True
    )
    reason_codes = _dedupe(
        (
            *_string_list(entry.get("reason_codes")),
            *_string_list(entry.get("autonomy_reason_codes")),
        )
    )
    autonomy_status = _text(entry.get("autonomy_status"))
    autonomy_next_action = _text(entry.get("autonomy_next_action"))
    return {
        "daily_autonomy_ledger_schema_version": (
            "v4_6_daily_autonomy_ledger_entry_v1"
        ),
        "generated_at": entry.get("generated_at"),
        "run_id": entry.get("run_id"),
        "as_of_date": entry.get("as_of_date"),
        "latest_bar_date": entry.get("latest_bar_date"),
        "input_data_sha256": entry.get("input_data_sha256"),
        "operating_mode": entry.get("operating_mode"),
        "no_submit_mode": entry.get("no_submit_mode"),
        "data_refresh_status": entry.get("data_refresh_status"),
        "data_freshness_status": entry.get("data_freshness_status"),
        "broker_read_performed": entry.get("broker_read_performed"),
        "broker_state_observed": entry.get("broker_state_observed"),
        "broker_state_mode": entry.get("broker_state_mode"),
        "expected_account_matched": entry.get("expected_account_matched"),
        "spy_position_observed": entry.get("spy_position_observed"),
        "spy_position_quantity": entry.get("spy_position_quantity"),
        "open_spy_orders_observed": entry.get("open_spy_orders_observed"),
        "unexpected_non_spy_positions_count": entry.get(
            "unexpected_non_spy_positions_count"
        ),
        "unexpected_non_spy_positions": list(
            _string_list(entry.get("unexpected_non_spy_positions"))
        ),
        "selected_strategy_id": entry.get("selected_strategy_id"),
        "strategy_route_action": entry.get("strategy_route_action"),
        "execution_plan_action": entry.get("execution_plan_action"),
        "action_decision": entry.get("action_decision"),
        "final_supervisor_classification": entry.get(
            "final_supervisor_classification"
        ),
        "final_operator_action": entry.get("final_operator_action"),
        "vol_scaled_preview_visible": entry.get("vol_scaled_preview_visible"),
        "vol_scaled_preview_intended_action": entry.get(
            "vol_scaled_preview_intended_action"
        ),
        "vol_scaled_preview_mutation_allowed": entry.get(
            "vol_scaled_preview_mutation_allowed"
        ),
        "vol_scaled_preview_submit_allowed": entry.get(
            "vol_scaled_preview_submit_allowed"
        ),
        "broker_mutation_performed": entry.get("broker_mutation_performed"),
        "paper_submit_performed": entry.get("paper_submit_performed"),
        "live_mutation_performed": entry.get("live_mutation_performed"),
        "reconciliation_status": entry.get("reconciliation_status"),
        "safety_labels": list(_string_list(entry.get("safety_labels"))),
        "autonomy_status": autonomy_status,
        "autonomy_next_action": autonomy_next_action,
        "changed_since_previous": comparison.get("changed_since_previous") is True,
        "hard_stop": hard_stop,
        "attention_required": attention_required,
        "reason_codes": list(reason_codes),
        "latest_bar_date_changed": (
            comparison.get("latest_bar_date_changed") is True
        ),
        "broker_state_mode_changed": (
            comparison.get("broker_state_mode_changed") is True
        ),
        "spy_position_changed": comparison.get("spy_position_changed") is True,
        "open_orders_changed": comparison.get("open_orders_changed") is True,
        "selected_strategy_changed": (
            comparison.get("selected_strategy_changed") is True
        ),
        "execution_plan_action_changed": (
            comparison.get("execution_plan_action_changed") is True
        ),
        "final_supervisor_classification_changed": (
            comparison.get("final_supervisor_classification_changed") is True
        ),
        "blocker_status_changed": (
            comparison.get("blocker_status_changed") is True
        ),
        "vol_scaled_preview_action_changed": (
            comparison.get("vol_scaled_preview_action_changed") is True
        ),
        "mutation_flags_changed": comparison.get("mutation_flags_changed") is True,
        "comparison_to_previous": dict(comparison),
        "operator_summary": {
            "autonomy_status": autonomy_status,
            "autonomy_next_action": autonomy_next_action,
            "changed_since_previous": comparison.get("changed_since_previous")
            is True,
            "hard_stop": hard_stop,
            "attention_required": attention_required,
            "reason_codes": list(reason_codes),
        },
    }


def _build_rollup(
    *,
    entry: Mapping[str, Any],
    history_count: int,
    comparison: Mapping[str, Any],
    history_path: Path,
    rollup_path: Path,
    summary_path: Path,
    autonomy_ledger_path: Path,
    autonomy_latest_path: Path,
    autonomy_summary_path: Path,
) -> dict[str, Any]:
    hard_stop = entry.get("hard_stop") is True or entry.get("autonomy_hard_stop") is True
    attention_required = (
        entry.get("attention_required") is True
        or entry.get("autonomy_attention_required") is True
    )
    reason_codes = _dedupe(
        (
            *_string_list(entry.get("reason_codes")),
            *_string_list(entry.get("autonomy_reason_codes")),
        )
    )
    if hard_stop:
        severity = "hard_stop"
    elif attention_required:
        severity = "attention_required"
    else:
        severity = "healthy"
    return {
        "schema_version": PAPER_AUTOPILOT_HISTORY_SCHEMA_VERSION,
        "history_count": history_count,
        "classification": entry.get("classification"),
        "autonomy_status": entry.get("autonomy_status"),
        "autonomy_next_action": entry.get("autonomy_next_action"),
        "autonomy_attention_required": entry.get("autonomy_attention_required"),
        "autonomy_hard_stop": entry.get("autonomy_hard_stop"),
        "autonomy_reason_codes": list(
            _string_list(entry.get("autonomy_reason_codes"))
        ),
        "changed_since_previous": comparison.get("changed_since_previous") is True,
        "attention_required": attention_required,
        "hard_stop": hard_stop,
        "severity": severity,
        "reason_codes": list(reason_codes),
        "run_id": entry.get("run_id"),
        "generated_at": entry.get("generated_at"),
        "as_of_date": entry.get("as_of_date"),
        "latest_bar_date": entry.get("latest_bar_date"),
        "data_refresh_status": entry.get("data_refresh_status"),
        "data_freshness_status": entry.get("data_freshness_status"),
        "symbol": entry.get("symbol"),
        "sma_posture": entry.get("sma_posture"),
        "operating_mode": entry.get("operating_mode"),
        "broker_state_mode": entry.get("broker_state_mode"),
        "broker_state_observed": entry.get("broker_state_observed"),
        "broker_read_performed": entry.get("broker_read_performed"),
        "expected_account_matched": entry.get("expected_account_matched"),
        "spy_position_observed": entry.get("spy_position_observed"),
        "spy_position_quantity": entry.get("spy_position_quantity"),
        "open_spy_orders_observed": entry.get("open_spy_orders_observed"),
        "unexpected_non_spy_positions_count": entry.get(
            "unexpected_non_spy_positions_count"
        ),
        "unexpected_non_spy_positions": list(
            _string_list(entry.get("unexpected_non_spy_positions"))
        ),
        "selected_strategy_id": entry.get("selected_strategy_id"),
        "strategy_route_action": entry.get("strategy_route_action"),
        "pre_broker_daily_cycle_status": entry.get("pre_broker_daily_cycle_status"),
        "pre_broker_daily_cycle_classification": entry.get(
            "pre_broker_daily_cycle_classification"
        ),
        "blocker_status": entry.get("blocker_status"),
        "final_supervisor_status": entry.get("final_supervisor_status"),
        "broker_observed_supervisor_status": entry.get(
            "broker_observed_supervisor_status"
        ),
        "final_supervisor_classification": entry.get(
            "final_supervisor_classification"
        ),
        "execution_plan_id": entry.get("execution_plan_id"),
        "client_order_id": entry.get("client_order_id"),
        "no_submit_mode": entry.get("no_submit_mode"),
        "execution_plan_action": entry.get("execution_plan_action"),
        "intended_mutation_action": entry.get("intended_mutation_action"),
        "mutation_would_be_required_without_no_submit": entry.get(
            "mutation_would_be_required_without_no_submit"
        ),
        "action_decision": entry.get("action_decision"),
        "paper_submit_authorized": entry.get("paper_submit_authorized"),
        "paper_submit_performed": entry.get("paper_submit_performed"),
        "broker_mutation_performed": entry.get("broker_mutation_performed"),
        "live_mutation_performed": entry.get("live_mutation_performed"),
        "live_trading_performed": entry.get("live_trading_performed"),
        "vol_scaled_preview_visible": entry.get("vol_scaled_preview_visible"),
        "vol_scaled_preview_intended_action": entry.get(
            "vol_scaled_preview_intended_action"
        ),
        "vol_scaled_preview_mutation_allowed": entry.get(
            "vol_scaled_preview_mutation_allowed"
        ),
        "vol_scaled_preview_submit_allowed": entry.get(
            "vol_scaled_preview_submit_allowed"
        ),
        "vol_scaled_preview_non_mutation_status": entry.get(
            "vol_scaled_preview_non_mutation_status"
        ),
        "reconciliation_status": entry.get("reconciliation_status"),
        "next_operator_action": entry.get("next_operator_action"),
        "final_operator_action": entry.get("final_operator_action"),
        "safety_labels": list(_string_list(entry.get("safety_labels"))),
        "input_data_path": entry.get("input_data_path"),
        "input_data_sha256": entry.get("input_data_sha256"),
        "comparison_to_previous": dict(comparison),
        "artifact_paths": {
            "operating_history": str(history_path),
            "daily_autonomy_ledger": str(autonomy_ledger_path),
            "latest_daily_autonomy": str(autonomy_latest_path),
            "daily_autonomy_summary": str(autonomy_summary_path),
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


def _bool_or_none(value: object) -> bool | None:
    if value is True:
        return True
    if value is False or value is None:
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return None


def _bool_text(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def _int(value: object) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _decimal_gt_zero(value: object) -> bool:
    if value in (None, ""):
        return False
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return parsed.is_finite() and parsed > Decimal("0")


def _string_list(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return tuple(deduped)


def _first_present(data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return ""


def _first_nonempty_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _normalized_status(value: object) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "PAPER_AUTOPILOT_DAILY_AUTONOMY_LEDGER_FILENAME",
    "PAPER_AUTOPILOT_DAILY_AUTONOMY_SUMMARY_FILENAME",
    "PAPER_AUTOPILOT_DEFAULT_HISTORY_ROOT",
    "PAPER_AUTOPILOT_DEFAULT_LATEST_STATUS_PATH",
    "PAPER_AUTOPILOT_HISTORY_SCHEMA_VERSION",
    "PAPER_AUTOPILOT_LATEST_DAILY_AUTONOMY_FILENAME",
    "PaperAutopilotHistoryConfig",
    "classify_paper_autopilot_autonomy_record",
    "classify_paper_autopilot_operating_record",
    "paper_autopilot_history_exit_status",
    "render_paper_autopilot_daily_autonomy_summary",
    "render_paper_autopilot_history_status",
    "render_paper_autopilot_operating_summary",
    "update_paper_autopilot_operating_history",
]
