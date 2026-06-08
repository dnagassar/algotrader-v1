"""Offline daily operating brief for the SPY ETF/SMA paper lab.

This module aggregates caller-supplied local JSONL artifacts only. It does not
import broker SDKs, load credentials, open network connections, or expose any
broker mutation path.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "DAILY_OPERATING_BRIEF_LABELS",
    "DailyOperatingBriefConfig",
    "DailyOperatingBriefWriteResult",
    "build_daily_operating_brief",
    "render_daily_operating_brief_json",
    "render_daily_operating_brief_text",
    "write_daily_operating_brief_jsonl",
]


DAILY_OPERATING_BRIEF_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_RECORD_TYPE = "daily_operating_brief"
_COMMAND = "daily-operating-brief"
_SYMBOL = "SPY"
_NOT_SUPPLIED = "not_supplied"
_PROFIT_CLAIM = "none"


@dataclass(frozen=True, slots=True)
class DailyOperatingBriefConfig:
    """Explicit local inputs for one offline daily operating brief."""

    run_id: str
    symbol: str = _SYMBOL
    generated_at: datetime | str | None = None
    order_reconciliation_log: Path | str | None = None
    cycle_preview_log: Path | str | None = None
    backtest_log: Path | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "generated_at",
            _generated_at_text(self.generated_at),
        )
        for field_name in (
            "order_reconciliation_log",
            "cycle_preview_log",
            "backtest_log",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_input_path(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class DailyOperatingBriefWriteResult:
    """Local JSONL write metadata for a single-record brief artifact."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    live_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", _output_path(self.output_path))
        object.__setattr__(
            self,
            "record_count",
            _fixed_int(self.record_count, 1, "record_count"),
        )
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        object.__setattr__(
            self,
            "newline_terminated",
            _true_bool(self.newline_terminated, "newline_terminated"),
        )
        object.__setattr__(self, "submitted", _false_bool(self.submitted, "submitted"))
        object.__setattr__(self, "mutated", _false_bool(self.mutated, "mutated"))
        object.__setattr__(
            self,
            "broker_action_performed",
            _false_bool(self.broker_action_performed, "broker_action_performed"),
        )
        object.__setattr__(
            self,
            "live_authorized",
            _false_bool(self.live_authorized, "live_authorized"),
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
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _ArtifactRead:
    path: Path | None
    supplied: bool
    found: bool
    parsed: bool
    record_count: int
    latest_record: dict[str, object] | None
    error: str

    def summary(self) -> dict[str, object]:
        latest = self.latest_record or {}
        return {
            "path": str(self.path) if self.path is not None else None,
            "supplied": self.supplied,
            "found": self.found,
            "parsed": self.parsed,
            "record_count": self.record_count,
            "latest_run_id": _text(latest.get("run_id")),
            "latest_record_type": _text(latest.get("record_type")),
            "error": self.error,
        }


def build_daily_operating_brief(
    config: DailyOperatingBriefConfig,
) -> dict[str, object]:
    """Build one operator-facing offline brief from explicit local JSONL paths."""

    checked_config = _config(config)
    artifacts = {
        "order_reconciliation_log": _read_jsonl_artifact(
            checked_config.order_reconciliation_log
        ),
        "cycle_preview_log": _read_jsonl_artifact(checked_config.cycle_preview_log),
        "backtest_log": _read_jsonl_artifact(checked_config.backtest_log),
    }

    reconciliation = artifacts["order_reconciliation_log"]
    cycle_preview = artifacts["cycle_preview_log"]
    backtest = artifacts["backtest_log"]

    m376_order_summary = _m376_order_summary(reconciliation)
    cycle_preview_summary = _cycle_preview_summary(cycle_preview)
    backtest_summary = _backtest_summary(backtest)
    blockers = _brief_blockers(
        m376_order_summary,
        cycle_preview_summary,
        backtest_summary,
    )

    payload = {
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": checked_config.generated_at,
        "symbol": checked_config.symbol,
        "scope": "SPY_paper_lab_only",
        "source_artifacts": {
            name: artifact.summary() for name, artifact in artifacts.items()
        },
        "paper_state_summary": _paper_state_summary(
            checked_config,
            m376_order_summary,
            cycle_preview_summary,
            blockers,
        ),
        "m376_order_summary": m376_order_summary,
        "blockers": blockers,
        "next_allowed_action": _next_allowed_action(blockers),
        "next_forbidden_action": _next_forbidden_action(
            blockers,
            backtest_summary,
        ),
        "submit_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "market_hours_required": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_observation_performed": False,
        "broker_mutation_allowed": False,
        "profit_claim": _PROFIT_CLAIM,
        "labels": list(DAILY_OPERATING_BRIEF_LABELS),
    }
    if cycle_preview_summary is not None:
        payload["cycle_preview_summary"] = cycle_preview_summary
    if backtest_summary is not None:
        payload["backtest_summary"] = backtest_summary
    return payload


def render_daily_operating_brief_json(payload: Mapping[str, object]) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_daily_operating_brief_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable daily brief summary."""

    paper_state = _mapping(payload.get("paper_state_summary"))
    m376 = _mapping(payload.get("m376_order_summary"))
    return "\n".join(
        (
            "SPY ETF/SMA daily operating brief",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"order_state: {paper_state.get('order_state', '')}",
            f"m376_reconciliation_decision: {m376.get('reconciliation_decision', '')}",
            "next_spy_submit_blocked: "
            f"{_bool_text(paper_state.get('next_spy_submit_blocked'))}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            f"next_allowed_action: {payload.get('next_allowed_action', '')}",
            "next_forbidden_action: "
            f"{_joined(_string_list(payload.get('next_forbidden_action')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_daily_operating_brief_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> DailyOperatingBriefWriteResult:
    """Write exactly one JSONL record, replacing any prior file contents."""

    path = _output_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_daily_operating_brief_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return DailyOperatingBriefWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        live_authorized=False,
    )


def _read_jsonl_artifact(path: Path | None) -> _ArtifactRead:
    if path is None:
        return _ArtifactRead(
            path=None,
            supplied=False,
            found=False,
            parsed=False,
            record_count=0,
            latest_record=None,
            error=_NOT_SUPPLIED,
        )
    if not path.exists():
        return _ArtifactRead(
            path=path,
            supplied=True,
            found=False,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="path_not_found",
        )
    if not path.is_file():
        return _ArtifactRead(
            path=path,
            supplied=True,
            found=True,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="path_not_file",
        )

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return _ArtifactRead(
                path=path,
                supplied=True,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"invalid_jsonl_line_{line_number}",
            )
        if not isinstance(row, Mapping):
            return _ArtifactRead(
                path=path,
                supplied=True,
                found=True,
                parsed=False,
                record_count=len(records),
                latest_record=None,
                error=f"jsonl_record_{line_number}_not_object",
            )
        records.append(dict(row))

    if not records:
        return _ArtifactRead(
            path=path,
            supplied=True,
            found=True,
            parsed=False,
            record_count=0,
            latest_record=None,
            error="empty_jsonl",
        )

    return _ArtifactRead(
        path=path,
        supplied=True,
        found=True,
        parsed=True,
        record_count=len(records),
        latest_record=records[-1],
        error="",
    )


def _m376_order_summary(artifact: _ArtifactRead) -> dict[str, object]:
    if not artifact.supplied:
        return {
            "supplied": False,
            "source_found": False,
            "source_parsed": False,
            "state": "unknown",
            "reason": "order_reconciliation_log_not_supplied",
            "blockers": ["order_state_unknown"],
            "next_spy_submit_blocked": True,
        }
    if artifact.latest_record is None:
        return {
            "supplied": True,
            "source_found": artifact.found,
            "source_parsed": False,
            "state": "unknown",
            "reason": artifact.error,
            "blockers": ["order_state_unknown"],
            "next_spy_submit_blocked": True,
        }

    record = artifact.latest_record
    blockers = _string_list(record.get("blockers"))
    if _m376_nonterminal_open(record, blockers):
        blockers = _dedupe((*blockers, "m376_order_nonterminal", "open_order_present"))
    elif _open_order_present(record):
        blockers = _dedupe((*blockers, "open_order_present"))

    terminal_state = _text(record.get("terminal_state")) or "unknown"
    state = "unknown"
    if _m376_nonterminal_open(record, blockers):
        state = "nonterminal_open"
    elif terminal_state == "terminal":
        state = "terminal"

    return {
        "supplied": True,
        "source_found": artifact.found,
        "source_parsed": artifact.parsed,
        "run_id": _text(record.get("run_id")),
        "symbol": _text(record.get("symbol")),
        "client_order_id": _text(record.get("client_order_id")),
        "broker_order_id": _text(record.get("broker_order_id")),
        "expected_side": _text(record.get("expected_side")),
        "expected_qty": _text(record.get("expected_qty")),
        "observed_status": _text(record.get("observed_status")),
        "observed_side": _text(record.get("observed_side")),
        "observed_qty": _text(record.get("observed_qty")),
        "observed_filled_qty": _text(record.get("observed_filled_qty")),
        "spy_position_qty": _text(record.get("spy_position_qty")),
        "open_order_count": _optional_int(record.get("open_order_count")),
        "exact_order_found": _optional_bool(record.get("exact_order_found")),
        "exact_order_source": _text(record.get("exact_order_source")),
        "terminal_state": terminal_state,
        "terminal_reason": _text(record.get("terminal_reason")),
        "reconciliation_decision": _text(record.get("reconciliation_decision")),
        "state": state,
        "reason": _text(record.get("reason")) or _text(record.get("terminal_reason")),
        "blockers": list(blockers),
        "next_spy_submit_blocked": _bool_or(
            record.get("next_spy_submit_blocked"),
            bool(blockers),
        ),
        "submitted": _bool_or(record.get("submitted"), False),
        "mutated": _bool_or(record.get("mutated"), False),
        "broker_action_performed": _bool_or(
            record.get("broker_action_performed"),
            False,
        ),
        "live_authorized": _bool_or(record.get("live_authorized"), False),
    }


def _cycle_preview_summary(artifact: _ArtifactRead) -> dict[str, object] | None:
    if not artifact.supplied:
        return None
    if artifact.latest_record is None:
        return {
            "supplied": True,
            "source_found": artifact.found,
            "source_parsed": False,
            "reason": artifact.error,
            "blockers": ["cycle_preview_unparsed"],
        }

    record = artifact.latest_record
    blockers = _string_list(record.get("blockers"))
    if _open_order_present(record):
        blockers = _dedupe((*blockers, "open_order_present"))
    return {
        "supplied": True,
        "source_found": artifact.found,
        "source_parsed": artifact.parsed,
        "run_id": _text(record.get("run_id")),
        "symbol": _text(record.get("symbol")),
        "decision": _text(record.get("decision")),
        "decision_reason": _text(record.get("decision_reason")),
        "sma_status": _text(record.get("sma_status")),
        "sma_posture": _text(record.get("sma_posture")),
        "spy_position_quantity": _text(record.get("spy_position_quantity")),
        "open_order_count": _optional_int(record.get("open_order_count")),
        "open_order_symbols": _string_list(record.get("open_order_symbols")),
        "open_order_client_order_ids": _string_list(
            record.get("open_order_client_order_ids")
        ),
        "open_order_broker_order_ids": _string_list(
            record.get("open_order_broker_order_ids")
        ),
        "open_order_statuses": _string_list(record.get("open_order_statuses")),
        "open_order_sides": _string_list(record.get("open_order_sides")),
        "blockers": list(blockers),
        "preview_order_present": isinstance(record.get("preview_order"), Mapping),
        "submitted": _bool_or(record.get("submitted"), False),
        "mutated": _bool_or(record.get("mutated"), False),
        "broker_action_performed": _bool_or(
            record.get("broker_action_performed"),
            False,
        ),
    }


def _backtest_summary(artifact: _ArtifactRead) -> dict[str, object] | None:
    if not artifact.supplied:
        return None
    if artifact.latest_record is None:
        return {
            "supplied": True,
            "source_found": artifact.found,
            "source_parsed": False,
            "reason": artifact.error,
            "research_evidence_only": True,
            "submit_authorization": False,
            "profit_claim": _PROFIT_CLAIM,
        }

    record = artifact.latest_record
    stats = _mapping(record.get("stats"))
    return {
        "supplied": True,
        "source_found": artifact.found,
        "source_parsed": artifact.parsed,
        "run_id": _text(record.get("run_id")),
        "symbol": _text(record.get("symbol")),
        "status": _text(record.get("status")),
        "blocked": _bool_or(record.get("blocked"), False),
        "block_reason": _text(record.get("block_reason")),
        "bars_input_available": _optional_bool(record.get("bars_input_available")),
        "bar_count": _optional_int(record.get("bar_count")),
        "fast_window": _optional_int(record.get("fast_window")),
        "slow_window": _optional_int(record.get("slow_window")),
        "latest_posture": _latest_backtest_posture(record),
        "stats": {
            "start_date": stats.get("start_date"),
            "end_date": stats.get("end_date"),
            "total_return": stats.get("total_return"),
            "max_drawdown": stats.get("max_drawdown"),
            "trade_count": stats.get("trade_count"),
            "final_position_state": stats.get("final_position_state"),
            "commission_model": stats.get("commission_model"),
            "slippage_model": stats.get("slippage_model"),
        },
        "research_evidence_only": True,
        "submit_authorization": False,
        "profit_claim": _text(record.get("profit_claim")) or _PROFIT_CLAIM,
        "submitted": _bool_or(record.get("submitted"), False),
        "mutated": _bool_or(record.get("mutated"), False),
        "broker_action_performed": _bool_or(
            record.get("broker_action_performed"),
            False,
        ),
        "live_authorized": _bool_or(record.get("live_authorized"), False),
    }


def _brief_blockers(
    m376_order_summary: Mapping[str, object],
    cycle_preview_summary: Mapping[str, object] | None,
    backtest_summary: Mapping[str, object] | None,
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(_string_list(m376_order_summary.get("blockers")))
    if _text(m376_order_summary.get("state")) == "unknown":
        blockers.append("order_state_unknown")
    if cycle_preview_summary is not None:
        blockers.extend(_string_list(cycle_preview_summary.get("blockers")))
    if (
        backtest_summary is not None
        and backtest_summary.get("source_parsed") is False
    ):
        blockers.append("backtest_artifact_unparsed")
    elif backtest_summary is not None and backtest_summary.get("blocked") is True:
        blockers.append("backtest_research_input_blocked")
    return list(_dedupe(tuple(blockers)))


def _paper_state_summary(
    config: DailyOperatingBriefConfig,
    m376_order_summary: Mapping[str, object],
    cycle_preview_summary: Mapping[str, object] | None,
    blockers: list[str],
) -> dict[str, object]:
    open_order_count = m376_order_summary.get("open_order_count")
    if open_order_count is None and cycle_preview_summary is not None:
        open_order_count = cycle_preview_summary.get("open_order_count")
    spy_position_qty = _text(m376_order_summary.get("spy_position_qty"))
    if not spy_position_qty and cycle_preview_summary is not None:
        spy_position_qty = _text(cycle_preview_summary.get("spy_position_quantity"))

    return {
        "scope": "SPY_only",
        "symbol": config.symbol,
        "paper_lab_only": True,
        "live_authorized": False,
        "order_state": _text(m376_order_summary.get("state")) or "unknown",
        "m376_reconciliation_available": (
            m376_order_summary.get("source_parsed") is True
        ),
        "spy_position_qty": spy_position_qty,
        "open_order_count": open_order_count,
        "next_spy_submit_blocked": _next_spy_submit_blocked(
            m376_order_summary,
            blockers,
        ),
        "constraints": [
            "offline_brief_only",
            "read_only_local_artifacts",
            "no_broker_mutation",
            "market_hours_not_required",
            "paper_lab_only",
            "not_live_authorized",
        ],
    }


def _next_allowed_action(blockers: list[str]) -> str:
    if "order_state_unknown" in blockers:
        return "read_only_reconciliation_before_any_spy_submit"
    if (
        "m376_order_nonterminal" in blockers
        or "open_order_present" in blockers
    ):
        return "offline_work_or_read_only_reconciliation"
    return "offline_research_or_operator_review_only"


def _next_forbidden_action(
    blockers: list[str],
    backtest_summary: Mapping[str, object] | None,
) -> list[str]:
    actions = [
        "broker_mutation_from_daily_brief",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_brief",
    ]
    if (
        "m376_order_nonterminal" in blockers
        or "open_order_present" in blockers
    ):
        actions.append("spy_submit_until_m376_terminal")
    if "order_state_unknown" in blockers:
        actions.extend(
            (
                "spy_submit_until_order_state_known",
                "spy_submit_before_read_only_reconciliation",
            )
        )
    if backtest_summary is not None:
        actions.append("submit_based_on_backtest_stats")
    return list(_dedupe(tuple(actions)))


def _next_spy_submit_blocked(
    m376_order_summary: Mapping[str, object],
    blockers: list[str],
) -> bool:
    if m376_order_summary.get("next_spy_submit_blocked") is True:
        return True
    return bool(
        {
            "m376_order_nonterminal",
            "open_order_present",
            "order_state_unknown",
        }.intersection(blockers)
    )


def _m376_nonterminal_open(
    record: Mapping[str, object],
    blockers: tuple[str, ...],
) -> bool:
    return (
        record.get("terminal_state") == "nonterminal"
        or record.get("reconciliation_decision") == "m376_nonterminal_open"
        or "m376_order_nonterminal" in blockers
    )


def _open_order_present(record: Mapping[str, object]) -> bool:
    if record.get("open_order_count") not in (None, ""):
        count = _optional_int(record.get("open_order_count"))
        if count is not None and count > 0:
            return True
    broker_observation = _mapping(record.get("broker_observation"))
    count = _optional_int(broker_observation.get("open_order_count"))
    if count is not None and count > 0:
        return True
    open_order_symbols = _string_list(record.get("open_order_symbols"))
    broker_open_order_symbols = _string_list(
        broker_observation.get("open_order_symbols")
    )
    return _SYMBOL in (*open_order_symbols, *broker_open_order_symbols)


def _latest_backtest_posture(record: Mapping[str, object]) -> str:
    rows = record.get("posture_history")
    if not isinstance(rows, list) or not rows:
        return ""
    latest = rows[-1]
    if not isinstance(latest, Mapping):
        return ""
    return _text(latest.get("posture"))


def _config(value: object) -> DailyOperatingBriefConfig:
    if type(value) is not DailyOperatingBriefConfig:
        raise ValidationError("config must be a DailyOperatingBriefConfig.")
    return value


def _generated_at_text(value: object) -> str:
    if value is None:
        return datetime.now(UTC).replace(microsecond=0).isoformat()
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("generated_at must be timezone-aware.")
        return value.isoformat()
    if type(value) is str:
        text = _required_string(value, "generated_at")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("generated_at must be ISO-8601.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError("generated_at must be timezone-aware.")
        return parsed.isoformat()
    raise ValidationError("generated_at must be a datetime or ISO string.")


def _optional_input_path(value: object, field_name: str) -> Path | None:
    if value in (None, ""):
        return None
    if type(value) is str:
        return Path(value)
    if isinstance(value, Path):
        return value
    raise ValidationError(f"{field_name} must be a path string.")


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


def _spy_symbol(value: object) -> str:
    symbol = _required_string(value, "symbol").upper()
    if symbol != _SYMBOL:
        raise ValidationError("symbol must be SPY for the daily operating brief.")
    return symbol


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value == "" or value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _fixed_int(value: object, expected: int, field_name: str) -> int:
    if type(value) is not int or value != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return value


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _optional_bool(value: object) -> bool | None:
    return value if type(value) is bool else None


def _bool_or(value: object, default: bool) -> bool:
    return value if type(value) is bool else default


def _optional_int(value: object) -> int | None:
    if type(value) is int:
        return value
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


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
