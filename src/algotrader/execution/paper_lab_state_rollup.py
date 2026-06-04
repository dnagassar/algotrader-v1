"""Offline paper-lab state rollup from local JSONL artifacts.

This module reads caller-supplied local JSONL artifacts only. It does not load
profiles, inspect credentials, import broker SDKs, open sockets, or expose any
broker mutation path.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "PAPER_LAB_STATE_ROLLUP_LABELS",
    "PaperLabStateRollupConfig",
    "PaperLabStateRollupWriteResult",
    "build_paper_lab_state_rollup",
    "render_paper_lab_state_rollup_json",
    "render_paper_lab_state_rollup_text",
    "write_paper_lab_state_rollup_jsonl",
]


PAPER_LAB_STATE_ROLLUP_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M388 - Offline paper-lab state rollup from local artifacts"
_RECORD_TYPE = "paper_lab_state_rollup"
_COMMAND = "paper-lab-state-rollup"
_DEFAULT_SYMBOL = "SPY"
_PROFIT_CLAIM = "none"
_MISSING_RECONCILIATION_BLOCKER = "missing_or_invalid_order_reconciliation"
_MISSING_DAILY_PREVIEW_BLOCKER = "missing_or_invalid_daily_preview"
_CONFLICTING_LOCAL_ARTIFACT_BLOCKER = "conflicting_local_artifact_state"
_AMBIGUOUS_LOCAL_ARTIFACT_BLOCKER = "ambiguous_local_artifact_state"
_WRITE_RESULT_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SOURCE_SAFETY_FIELDS = (
    *_WRITE_RESULT_FALSE_FIELDS,
    "broker_mutation_allowed",
)


@dataclass(frozen=True, slots=True)
class PaperLabStateRollupConfig:
    """Explicit local inputs for one offline paper-lab state rollup."""

    run_id: str
    order_reconciliation_log: Path | str
    daily_preview_log: Path | str
    symbol: str = _DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "order_reconciliation_log",
            _required_path(
                self.order_reconciliation_log,
                "order_reconciliation_log",
            ),
        )
        object.__setattr__(
            self,
            "daily_preview_log",
            _required_path(self.daily_preview_log, "daily_preview_log"),
        )


@dataclass(frozen=True, slots=True)
class PaperLabStateRollupWriteResult:
    """Local JSONL write metadata for a single rollup record."""

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
    found: bool
    parsed: bool
    record_count: int
    latest_record: dict[str, object] | None
    error: str

    def summary(self) -> dict[str, object]:
        latest = self.latest_record or {}
        return {
            "path": str(self.path),
            "found": self.found,
            "parsed": self.parsed,
            "record_count": self.record_count,
            "latest_run_id": _text(latest.get("run_id")),
            "latest_record_type": _text(latest.get("record_type")),
            "error": self.error,
        }


def build_paper_lab_state_rollup(
    config: PaperLabStateRollupConfig,
) -> dict[str, object]:
    """Build one consolidated offline paper-lab state rollup record."""

    checked_config = _config(config)
    reconciliation = _read_jsonl_artifact(checked_config.order_reconciliation_log)
    daily_preview = _read_jsonl_artifact(checked_config.daily_preview_log)
    reconciliation_record = reconciliation.latest_record or {}
    daily_record = daily_preview.latest_record or {}
    daily_m376 = _mapping(daily_record.get("m376_order_summary"))

    m376_status = _first_text(
        reconciliation_record.get("observed_status"),
        daily_m376.get("observed_status"),
    )
    terminal_state = _first_text(
        reconciliation_record.get("terminal_state"),
        daily_record.get("m376_terminal_state"),
        daily_m376.get("terminal_state"),
    )
    terminal_reason = _first_text(
        reconciliation_record.get("terminal_reason"),
        daily_record.get("m376_terminal_reason"),
        daily_m376.get("terminal_reason"),
    )
    terminal_state_conflict = _terminal_state_conflict(
        reconciliation_record,
        daily_record,
        daily_m376,
    )
    m376_nonterminal = _m376_nonterminal(
        terminal_state,
        reconciliation_record,
        daily_record,
        daily_m376,
    )
    open_spy_order_present = _open_spy_order_present(
        reconciliation_record,
        daily_record,
        daily_m376,
        checked_config.symbol,
    )
    open_order_present = open_spy_order_present or _open_order_present(
        reconciliation_record,
        daily_record,
        daily_m376,
        checked_config.symbol,
    )
    open_order_count = _first_int(
        reconciliation_record.get("open_order_count"),
        daily_m376.get("open_order_count"),
        daily_record.get("open_order_count"),
    )
    spy_position_qty = _first_text(
        daily_record.get("spy_position_qty"),
        reconciliation_record.get("spy_position_qty"),
        daily_m376.get("spy_position_qty"),
    )
    blockers = _rollup_blockers(
        reconciliation,
        daily_preview,
        reconciliation_record,
        daily_record,
        daily_m376,
        terminal_state,
        terminal_state_conflict,
        m376_nonterminal,
        open_order_present,
    )
    daily_preview_status = _daily_preview_status(daily_preview, daily_record, blockers)
    cycle_decision = _cycle_decision(daily_preview, daily_record, open_order_present)
    forbidden_actions = _forbidden_actions(
        blockers,
        daily_record,
        m376_nonterminal,
        open_order_present,
    )
    next_allowed_action = _next_allowed_action(
        blockers,
        daily_record,
        m376_nonterminal,
        open_order_present,
    )

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": _first_text(daily_record.get("generated_at")),
        "as_of": _first_text(daily_record.get("as_of"), daily_record.get("generated_at")),
        "symbol": checked_config.symbol,
        "scope": "SPY_paper_lab_only",
        "labels": list(PAPER_LAB_STATE_ROLLUP_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "source_order_reconciliation_log": str(
            checked_config.order_reconciliation_log
        ),
        "source_daily_preview_log": str(checked_config.daily_preview_log),
        "source_artifacts": {
            "order_reconciliation_log": reconciliation.summary(),
            "daily_preview_log": daily_preview.summary(),
        },
        "state_rollup_status": _rollup_status(blockers),
        "m376_order_summary": _m376_order_summary(
            reconciliation,
            daily_preview,
            reconciliation_record,
            daily_record,
            daily_m376,
            m376_status,
            terminal_state,
            terminal_reason,
            m376_nonterminal,
            open_order_count,
            spy_position_qty,
        ),
        "m376_status": m376_status,
        "m376_observed_status": m376_status,
        "m376_terminal_state": terminal_state or "unknown",
        "m376_terminal_reason": terminal_reason,
        "m376_terminal": (
            terminal_state == "terminal"
            and not terminal_state_conflict
            and not m376_nonterminal
        ),
        "m376_terminal_state_conflict": terminal_state_conflict,
        "m376_nonterminal": m376_nonterminal,
        "m376_order_nonterminal": m376_nonterminal,
        "spy_position_qty": spy_position_qty,
        "open_order_count": open_order_count,
        "open_order_present": open_order_present,
        "open_spy_order_present": open_spy_order_present,
        "non_spy_position_present": _non_spy_position_present(
            reconciliation_record,
            daily_record,
            checked_config.symbol,
        ),
        "daily_preview_status": daily_preview_status,
        "cycle_decision": cycle_decision,
        "cycle_decision_reason": _first_text(
            daily_record.get("cycle_decision_reason")
        ),
        "cycle_next_allowed_action": _first_text(
            daily_record.get("cycle_next_allowed_action")
        ),
        "blockers": blockers,
        "next_allowed_action": next_allowed_action,
        "forbidden_actions": forbidden_actions,
        "next_forbidden_action": forbidden_actions,
        "preview_order_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def render_paper_lab_state_rollup_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_paper_lab_state_rollup_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable state rollup summary."""

    return "\n".join(
        (
            "SPY paper-lab state rollup",
            f"run_id: {payload.get('run_id', '')}",
            f"state_rollup_status: {payload.get('state_rollup_status', '')}",
            f"m376_status: {payload.get('m376_status', '')}",
            f"m376_terminal_state: {payload.get('m376_terminal_state', '')}",
            f"spy_position_qty: {payload.get('spy_position_qty', '')}",
            f"open_order_count: {payload.get('open_order_count', '')}",
            f"daily_preview_status: {payload.get('daily_preview_status', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            f"next_allowed_action: {payload.get('next_allowed_action', '')}",
            "forbidden_actions: "
            f"{_joined(_string_list(payload.get('forbidden_actions')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            "broker_actions_performed: "
            f"{_bool_text(payload.get('broker_actions_performed'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_paper_lab_state_rollup_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> PaperLabStateRollupWriteResult:
    """Write exactly one JSONL rollup record, replacing any prior contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_paper_lab_state_rollup_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return PaperLabStateRollupWriteResult(
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


def _read_jsonl_artifact(path: Path) -> _ArtifactRead:
    if not path.exists():
        return _ArtifactRead(
            path=path,
            found=False,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="path_not_found",
        )
    if not path.is_file():
        return _ArtifactRead(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="path_not_file",
        )

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return _ArtifactRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"invalid_jsonl_line_{line_number}",
            )
        if not isinstance(payload, Mapping):
            return _ArtifactRead(
                path=path,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"jsonl_record_{line_number}_not_object",
            )
        records.append(dict(payload))

    if not records:
        return _ArtifactRead(
            path=path,
            found=True,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="empty_jsonl",
        )

    return _ArtifactRead(
        path=path,
        found=True,
        parsed=True,
        record_count=len(records),
        latest_record=records[-1],
        error="",
    )


def _rollup_blockers(
    reconciliation: _ArtifactRead,
    daily_preview: _ArtifactRead,
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    daily_m376: Mapping[str, object],
    terminal_state: str,
    terminal_state_conflict: bool,
    m376_nonterminal: bool,
    open_order_present: bool,
) -> list[str]:
    blockers: list[str] = []
    if not reconciliation.parsed:
        blockers.append(_MISSING_RECONCILIATION_BLOCKER)
    if not daily_preview.parsed:
        blockers.append(_MISSING_DAILY_PREVIEW_BLOCKER)
    blockers.extend(_string_list(reconciliation_record.get("blockers")))
    blockers.extend(_string_list(daily_record.get("blockers")))
    blockers.extend(_string_list(daily_m376.get("blockers")))
    if terminal_state_conflict or _m376_identity_conflict(
        reconciliation_record,
        daily_record,
        daily_m376,
    ):
        blockers.append(_CONFLICTING_LOCAL_ARTIFACT_BLOCKER)
    if _ambiguous_daily_preview(daily_preview, daily_record):
        blockers.append(_AMBIGUOUS_LOCAL_ARTIFACT_BLOCKER)
    if m376_nonterminal:
        blockers.append("m376_order_nonterminal")
    if open_order_present:
        blockers.append("open_order_present")
    if reconciliation.parsed and terminal_state not in {"terminal", "nonterminal"}:
        blockers.append("order_state_unknown")
    if _source_safety_flags_violate(reconciliation_record, daily_record):
        blockers.append("source_artifact_safety_flags_not_false")
    return list(_dedupe(tuple(blockers)))


def _m376_order_summary(
    reconciliation: _ArtifactRead,
    daily_preview: _ArtifactRead,
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    daily_m376: Mapping[str, object],
    m376_status: str,
    terminal_state: str,
    terminal_reason: str,
    m376_nonterminal: bool,
    open_order_count: int | None,
    spy_position_qty: str,
) -> dict[str, object]:
    state = "unknown"
    if m376_nonterminal:
        state = "nonterminal_open"
    elif terminal_state == "terminal":
        state = "terminal"
    return {
        "source_order_reconciliation_found": reconciliation.found,
        "source_order_reconciliation_parsed": reconciliation.parsed,
        "source_daily_preview_found": daily_preview.found,
        "source_daily_preview_parsed": daily_preview.parsed,
        "run_id": _first_text(
            reconciliation_record.get("run_id"),
            daily_m376.get("run_id"),
        ),
        "symbol": _first_text(
            reconciliation_record.get("symbol"),
            daily_m376.get("symbol"),
            daily_record.get("symbol"),
        ),
        "client_order_id": _first_text(
            reconciliation_record.get("client_order_id"),
            daily_record.get("m376_client_order_id"),
            daily_m376.get("client_order_id"),
        ),
        "broker_order_id": _first_text(
            reconciliation_record.get("broker_order_id"),
            daily_record.get("m376_broker_order_id"),
            daily_m376.get("broker_order_id"),
        ),
        "observed_status": m376_status,
        "observed_side": _first_text(
            reconciliation_record.get("observed_side"),
            daily_m376.get("observed_side"),
        ),
        "observed_qty": _first_text(
            reconciliation_record.get("observed_qty"),
            daily_m376.get("observed_qty"),
        ),
        "observed_filled_qty": _first_text(
            reconciliation_record.get("observed_filled_qty"),
            daily_m376.get("observed_filled_qty"),
        ),
        "state": state,
        "terminal_state": terminal_state or "unknown",
        "terminal_reason": terminal_reason,
        "reconciliation_decision": _first_text(
            reconciliation_record.get("reconciliation_decision"),
            daily_m376.get("reconciliation_decision"),
        ),
        "spy_position_qty": spy_position_qty,
        "open_order_count": open_order_count,
        "next_spy_submit_blocked": _bool_or(
            reconciliation_record.get("next_spy_submit_blocked"),
            m376_nonterminal,
        ),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "live_authorized": False,
    }


def _daily_preview_status(
    daily_preview: _ArtifactRead,
    daily_record: Mapping[str, object],
    blockers: list[str],
) -> str:
    if not daily_preview.parsed:
        return "blocked"
    return _first_text(daily_record.get("daily_preview_status")) or (
        "blocked" if blockers else "review_only"
    )


def _cycle_decision(
    daily_preview: _ArtifactRead,
    daily_record: Mapping[str, object],
    open_order_present: bool,
) -> str:
    if daily_preview.parsed:
        decision = _first_text(daily_record.get("cycle_decision"))
        if decision:
            return decision
    if open_order_present:
        return "blocked/open_order_present"
    return f"blocked/{_MISSING_DAILY_PREVIEW_BLOCKER}"


def _next_allowed_action(
    blockers: list[str],
    daily_record: Mapping[str, object],
    m376_nonterminal: bool,
    open_order_present: bool,
) -> str:
    if _MISSING_RECONCILIATION_BLOCKER in blockers or "order_state_unknown" in blockers:
        return "read_only_reconciliation_before_any_spy_submit"
    if m376_nonterminal or open_order_present:
        return "offline_work_or_read_only_reconciliation"
    if _MISSING_DAILY_PREVIEW_BLOCKER in blockers:
        return "rebuild_daily_preview_from_current_reconciliation"
    return (
        _first_text(daily_record.get("next_allowed_action"))
        or "offline_research_or_operator_review_only"
    )


def _forbidden_actions(
    blockers: list[str],
    daily_record: Mapping[str, object],
    m376_nonterminal: bool,
    open_order_present: bool,
) -> list[str]:
    actions = [
        "broker_mutation_from_state_rollup",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_state_rollup",
        *_string_list(daily_record.get("next_forbidden_action")),
        *_string_list(daily_record.get("forbidden_actions")),
    ]
    if _MISSING_RECONCILIATION_BLOCKER in blockers or "order_state_unknown" in blockers:
        actions.extend(
            (
                "spy_submit_until_order_state_known",
                "spy_submit_before_read_only_reconciliation",
            )
        )
    if _MISSING_DAILY_PREVIEW_BLOCKER in blockers:
        actions.append("spy_submit_until_daily_preview_valid")
    if m376_nonterminal or open_order_present:
        actions.append("spy_submit_until_m376_terminal")
    return list(_dedupe(tuple(actions)))


def _m376_nonterminal(
    terminal_state: str,
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    daily_m376: Mapping[str, object],
) -> bool:
    return (
        terminal_state == "nonterminal"
        or daily_record.get("m376_terminal_state") == "nonterminal"
        or daily_m376.get("terminal_state") == "nonterminal"
        or reconciliation_record.get("reconciliation_decision") == "m376_nonterminal_open"
        or "m376_order_nonterminal"
        in _string_list(reconciliation_record.get("blockers"))
        or "m376_order_nonterminal" in _string_list(daily_record.get("blockers"))
        or "m376_order_nonterminal" in _string_list(daily_m376.get("blockers"))
    )


def _open_order_present(
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    daily_m376: Mapping[str, object],
    symbol: str,
) -> bool:
    if _bool_or(daily_record.get("open_order_present"), False):
        return True
    for value in (
        reconciliation_record.get("open_order_count"),
        daily_m376.get("open_order_count"),
        daily_record.get("open_order_count"),
    ):
        count = _optional_int(value)
        if count is not None and count > 0:
            return True
    for value in (
        reconciliation_record.get("open_order_symbols"),
        daily_record.get("open_order_symbols"),
    ):
        if symbol_value(symbol) in _string_list(value):
            return True
    return "open_order_present" in _string_list(reconciliation_record.get("blockers"))


def _open_spy_order_present(
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    daily_m376: Mapping[str, object],
    symbol: str,
) -> bool:
    checked_symbol = symbol_value(symbol)
    if _bool_or(daily_record.get("open_spy_order_present"), False):
        return True
    for value in (
        reconciliation_record.get("spy_open_order_count"),
        daily_record.get("spy_open_order_count"),
    ):
        count = _optional_int(value)
        if count is not None and count > 0:
            return True
    for value in (
        reconciliation_record.get("open_order_symbols"),
        daily_record.get("open_order_symbols"),
    ):
        if checked_symbol in _string_list(value):
            return True
    daily_symbol = _first_text(daily_m376.get("symbol"), daily_record.get("symbol"))
    return bool(_optional_int(daily_m376.get("open_order_count")) and daily_symbol == checked_symbol)


def _non_spy_position_present(
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    symbol: str,
) -> bool:
    checked_symbol = symbol_value(symbol)
    if reconciliation_record.get("unexpected_non_spy_position_present") is True:
        return True
    if daily_record.get("non_spy_position_present") is True:
        return True
    for value in (
        reconciliation_record.get("non_spy_positions"),
        daily_record.get("non_spy_positions"),
    ):
        if _non_spy_sequence_present(value, checked_symbol):
            return True
    return False


def _non_spy_sequence_present(value: object, symbol: str) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    for item in value:
        if isinstance(item, Mapping):
            item_symbol = _text(item.get("symbol")).upper()
            if item_symbol and item_symbol != symbol:
                return True
        else:
            item_symbol = _text(item).upper()
            if item_symbol and item_symbol != symbol:
                return True
    return False


def _source_safety_flags_violate(
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
) -> bool:
    for record in (reconciliation_record, daily_record):
        for field_name in _SOURCE_SAFETY_FIELDS:
            if field_name in record and record[field_name] is not False:
                return True
    return False


def _terminal_state_conflict(
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    daily_m376: Mapping[str, object],
) -> bool:
    terminal_states = {
        state
        for state in (
            _first_text(reconciliation_record.get("terminal_state")),
            _first_text(daily_record.get("m376_terminal_state")),
            _first_text(daily_m376.get("terminal_state")),
        )
        if state in {"terminal", "nonterminal"}
    }
    return len(terminal_states) > 1


def _m376_identity_conflict(
    reconciliation_record: Mapping[str, object],
    daily_record: Mapping[str, object],
    daily_m376: Mapping[str, object],
) -> bool:
    return any(
        _distinct_text_values(values)
        for values in (
            (
                reconciliation_record.get("run_id"),
                daily_m376.get("run_id"),
            ),
            (
                reconciliation_record.get("client_order_id"),
                daily_record.get("m376_client_order_id"),
                daily_m376.get("client_order_id"),
            ),
            (
                reconciliation_record.get("broker_order_id"),
                daily_record.get("m376_broker_order_id"),
                daily_m376.get("broker_order_id"),
            ),
        )
    )


def _ambiguous_daily_preview(
    daily_preview: _ArtifactRead,
    daily_record: Mapping[str, object],
) -> bool:
    if not daily_preview.parsed:
        return False
    return not any(
        field_name in daily_record
        for field_name in (
            "daily_preview_status",
            "cycle_decision",
            "m376_order_summary",
            "m376_terminal_state",
        )
    )


def _distinct_text_values(values: tuple[object, ...]) -> bool:
    observed = {_text(value) for value in values if _text(value)}
    return len(observed) > 1


def _rollup_status(blockers: list[str]) -> str:
    return "blocked" if blockers else "review_only"


def _config(value: object) -> PaperLabStateRollupConfig:
    if type(value) is not PaperLabStateRollupConfig:
        raise ValidationError("config must be a PaperLabStateRollupConfig.")
    return value


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


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _first_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _first_int(*values: object) -> int | None:
    for value in values:
        integer = _optional_int(value)
        if integer is not None:
            return integer
    return None


def _optional_int(value: object) -> int | None:
    if type(value) is int:
        return value
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _bool_or(value: object, default: bool) -> bool:
    return value if type(value) is bool else default


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


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
