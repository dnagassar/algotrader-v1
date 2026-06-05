"""Unified offline ETF/SMA cycle preview from local paper-lab artifacts.

This module composes the existing daily preview and paper-lab state rollup
builders in memory. It reads only explicit local JSONL artifacts supplied by
the caller and never imports broker SDKs, reads credentials, opens sockets, or
exposes broker mutation behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

from .etf_sma_cycle import (
    EtfSmaCycleConfig,
    build_etf_sma_cycle_from_offline_inputs,
)
from .etf_sma_daily_preview import (
    EtfSmaDailyPreviewConfig,
    build_etf_sma_daily_preview,
)
from .paper_lab_state_rollup import (
    PaperLabStateRollupConfig,
    build_paper_lab_state_rollup_from_daily_preview_record,
)

__all__ = [
    "ETF_SMA_CYCLE_UNIFIED_PREVIEW_LABELS",
    "EtfSmaCycleUnifiedPreviewConfig",
    "EtfSmaCycleUnifiedPreviewWriteResult",
    "build_etf_sma_cycle_unified_preview",
    "render_etf_sma_cycle_unified_preview_json",
    "render_etf_sma_cycle_unified_preview_text",
    "write_etf_sma_cycle_unified_preview_jsonl",
]


ETF_SMA_CYCLE_UNIFIED_PREVIEW_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M394 - Unified offline ETF/SMA cycle preview command"
_RECORD_TYPE = "etf_sma_cycle_unified_preview"
_COMMAND = "etf-sma-cycle"
_DEFAULT_SYMBOL = "SPY"
_PROFIT_CLAIM = "none"
_DERIVED_DAILY_PREVIEW_SUFFIX = "derived_daily_preview.jsonl"
_DEFAULT_SMA_SHORT_WINDOW = 50
_DEFAULT_SMA_LONG_WINDOW = 200
_WRITE_RESULT_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaCycleUnifiedPreviewConfig:
    """Explicit local inputs for one unified offline cycle preview."""

    run_id: str
    order_reconciliation_log: Path | str
    generated_at: datetime | str
    symbol: str = _DEFAULT_SYMBOL
    market_data_csv: Path | str | None = None

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
            "generated_at",
            _generated_at_text(self.generated_at),
        )
        object.__setattr__(
            self,
            "market_data_csv",
            _optional_path(self.market_data_csv, "market_data_csv"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaCycleUnifiedPreviewWriteResult:
    """Local JSONL write metadata for a single unified preview record."""

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


def build_etf_sma_cycle_unified_preview(
    config: EtfSmaCycleUnifiedPreviewConfig,
) -> dict[str, object]:
    """Build one deterministic unified offline ETF/SMA cycle preview record."""

    checked_config = _config(config)
    daily_preview = build_etf_sma_daily_preview(
        EtfSmaDailyPreviewConfig(
            run_id=checked_config.run_id,
            symbol=checked_config.symbol,
            generated_at=checked_config.generated_at,
            order_reconciliation_log=checked_config.order_reconciliation_log,
            market_data_csv=checked_config.market_data_csv,
        )
    )
    source_reconciliation = _mapping(
        daily_preview.get("source_order_reconciliation")
    )
    state_rollup = build_paper_lab_state_rollup_from_daily_preview_record(
        PaperLabStateRollupConfig(
            run_id=checked_config.run_id,
            symbol=checked_config.symbol,
            order_reconciliation_log=checked_config.order_reconciliation_log,
            daily_preview_log=_derived_daily_preview_log(checked_config.run_id),
        ),
        daily_preview_found=True,
        daily_preview_parsed=True,
        daily_preview_record_count=1,
        daily_preview_latest_record=daily_preview,
        daily_preview_error="",
    )
    forbidden_actions = _forbidden_actions(state_rollup)
    data_readiness = _cycle_data_readiness(checked_config)

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": checked_config.generated_at,
        "as_of": checked_config.generated_at,
        "symbol": checked_config.symbol,
        "strategy": {
            "name": "etf_sma_cycle",
            "version": "v1",
        },
        "strategy_name": "etf_sma_cycle",
        "strategy_version": "v1",
        "labels": list(ETF_SMA_CYCLE_UNIFIED_PREVIEW_LABELS),
        "paper_lab_only": True,
        "signal_evaluation_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "source_order_reconciliation_log": str(
            checked_config.order_reconciliation_log
        ),
        "source_order_reconciliation": _json_safe(source_reconciliation),
        "source_artifacts": {
            "order_reconciliation_log": _json_safe(source_reconciliation),
        },
        "daily_preview_status": _text(daily_preview.get("daily_preview_status")),
        "daily_preview_summary": _daily_preview_summary(daily_preview),
        "data_readiness": data_readiness,
        "state_rollup_status": _text(state_rollup.get("state_rollup_status")),
        "state_rollup_summary": _state_rollup_summary(state_rollup),
        "cycle_decision": _text(state_rollup.get("cycle_decision")),
        "cycle_decision_reason": _text(state_rollup.get("cycle_decision_reason")),
        "cycle_next_allowed_action": _text(
            state_rollup.get("cycle_next_allowed_action")
        ),
        "next_allowed_action": _text(state_rollup.get("next_allowed_action")),
        "blockers": list(_string_list(state_rollup.get("blockers"))),
        "m376_terminal": state_rollup.get("m376_terminal") is True,
        "m376_status": _text(state_rollup.get("m376_status")),
        "m376_observed_status": _text(state_rollup.get("m376_observed_status")),
        "m376_terminal_state": _text(state_rollup.get("m376_terminal_state")),
        "m376_terminal_reason": _text(state_rollup.get("m376_terminal_reason")),
        "m376_terminal_state_conflict": (
            state_rollup.get("m376_terminal_state_conflict") is True
        ),
        "m376_nonterminal": state_rollup.get("m376_nonterminal") is True,
        "m376_order_nonterminal": (
            state_rollup.get("m376_order_nonterminal") is True
        ),
        "m376_order_summary": _json_safe(state_rollup.get("m376_order_summary")),
        "open_order_count": state_rollup.get("open_order_count"),
        "open_order_present": state_rollup.get("open_order_present") is True,
        "open_spy_order_present": state_rollup.get("open_spy_order_present") is True,
        "spy_position_qty": _text(state_rollup.get("spy_position_qty")),
        "non_spy_position_present": (
            state_rollup.get("non_spy_position_present") is True
        ),
        "preview_order_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "forbidden_actions": forbidden_actions,
        "next_forbidden_action": forbidden_actions,
    }


def render_etf_sma_cycle_unified_preview_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_cycle_unified_preview_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing unified preview summary."""

    return "\n".join(
        (
            "ETF/SMA unified offline cycle preview",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"daily_preview_status: {payload.get('daily_preview_status', '')}",
            f"state_rollup_status: {payload.get('state_rollup_status', '')}",
            f"m376_status: {payload.get('m376_status', '')}",
            f"m376_terminal_state: {payload.get('m376_terminal_state', '')}",
            f"open_order_count: {payload.get('open_order_count', '')}",
            f"open_order_present: {_bool_text(payload.get('open_order_present'))}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            f"next_allowed_action: {payload.get('next_allowed_action', '')}",
            "forbidden_actions: "
            f"{_joined(_string_list(payload.get('forbidden_actions')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_actions_performed: "
            f"{_bool_text(payload.get('broker_actions_performed'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_etf_sma_cycle_unified_preview_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaCycleUnifiedPreviewWriteResult:
    """Write exactly one JSONL record, replacing any prior local artifact."""

    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_cycle_unified_preview_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaCycleUnifiedPreviewWriteResult(
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


def _daily_preview_summary(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": _text(payload.get("record_type")),
        "command": _text(payload.get("command")),
        "daily_preview_status": _text(payload.get("daily_preview_status")),
        "cycle_decision": _text(payload.get("cycle_decision")),
        "cycle_decision_reason": _text(payload.get("cycle_decision_reason")),
        "cycle_next_allowed_action": _text(
            payload.get("cycle_next_allowed_action")
        ),
        "next_allowed_action": _text(payload.get("next_allowed_action")),
        "blockers": list(_string_list(payload.get("blockers"))),
        "m376_terminal_state": _text(payload.get("m376_terminal_state")),
        "m376_terminal_reason": _text(payload.get("m376_terminal_reason")),
        "open_order_present": payload.get("open_order_present") is True,
        "open_spy_order_present": payload.get("open_spy_order_present") is True,
        "spy_position_qty": _text(payload.get("spy_position_qty")),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _state_rollup_summary(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": _text(payload.get("record_type")),
        "command": _text(payload.get("command")),
        "state_rollup_status": _text(payload.get("state_rollup_status")),
        "daily_preview_status": _text(payload.get("daily_preview_status")),
        "cycle_decision": _text(payload.get("cycle_decision")),
        "cycle_decision_reason": _text(payload.get("cycle_decision_reason")),
        "m376_terminal": payload.get("m376_terminal") is True,
        "m376_status": _text(payload.get("m376_status")),
        "m376_terminal_state": _text(payload.get("m376_terminal_state")),
        "m376_terminal_reason": _text(payload.get("m376_terminal_reason")),
        "open_order_count": payload.get("open_order_count"),
        "open_order_present": payload.get("open_order_present") is True,
        "open_spy_order_present": payload.get("open_spy_order_present") is True,
        "spy_position_qty": _text(payload.get("spy_position_qty")),
        "blockers": list(_string_list(payload.get("blockers"))),
        "next_allowed_action": _text(payload.get("next_allowed_action")),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _forbidden_actions(state_rollup: Mapping[str, object]) -> list[str]:
    actions = [
        "broker_mutation_from_etf_sma_cycle_unified_preview",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_etf_sma_cycle",
        "delete_from_etf_sma_cycle",
        "retry_from_etf_sma_cycle",
        *_string_list(state_rollup.get("forbidden_actions")),
        *_string_list(state_rollup.get("next_forbidden_action")),
    ]
    return list(_dedupe(tuple(actions)))


def _cycle_data_readiness(
    config: EtfSmaCycleUnifiedPreviewConfig,
) -> dict[str, object]:
    cycle_record, evidence_error = _cycle_evidence_record(config)
    sma_config = _mapping(cycle_record.get("sma_config"))
    sma = _mapping(cycle_record.get("sma"))
    market_data = _mapping(cycle_record.get("market_data"))

    short_window = _first_int(
        sma_config.get("fast_window"),
        sma.get("fast_window"),
        sma.get("short_window"),
        default=_DEFAULT_SMA_SHORT_WINDOW,
    )
    long_window = _first_int(
        sma_config.get("slow_window"),
        sma.get("slow_window"),
        sma.get("long_window"),
        default=_DEFAULT_SMA_LONG_WINDOW,
    )
    required_usable_bars = _first_int(
        sma_config.get("required_bars"),
        sma.get("required_bars"),
        long_window,
        default=_DEFAULT_SMA_LONG_WINDOW,
    )
    observed_usable_bars = _observed_usable_bars_from_cycle(
        cycle_record,
        market_data,
        sma,
    )
    missing_usable_bars = _missing_usable_bars(
        required_usable_bars,
        observed_usable_bars,
    )
    missing_evidence = _data_readiness_missing_evidence(
        evidence_error,
        cycle_record,
        observed_usable_bars,
    )

    return {
        "required_usable_bars": required_usable_bars,
        "observed_usable_bars": observed_usable_bars,
        "missing_usable_bars": missing_usable_bars,
        "sma_short_window": short_window,
        "sma_long_window": long_window,
        "readiness_state": _readiness_state(
            required_usable_bars,
            observed_usable_bars,
        ),
        "readiness_reason": _readiness_reason(
            evidence_error,
            required_usable_bars,
            observed_usable_bars,
        ),
        "missing_evidence": missing_evidence,
        "source": "offline_etf_sma_cycle_evidence",
        "source_record_type": _text(cycle_record.get("record_type")),
        "source_market_data": {
            "source": _text(market_data.get("source")),
            "input_available": market_data.get("input_available") is True,
            "total_bar_count": _optional_int(market_data.get("total_bar_count")),
            "usable_bar_count": _optional_int(market_data.get("usable_bar_count")),
            "ignored_future_bar_count": _optional_int(
                market_data.get("ignored_future_bar_count")
            ),
        },
    }


def _cycle_evidence_record(
    config: EtfSmaCycleUnifiedPreviewConfig,
) -> tuple[Mapping[str, object], str]:
    try:
        record = build_etf_sma_cycle_from_offline_inputs(
            EtfSmaCycleConfig(
                run_id=config.run_id,
                symbol=config.symbol,
                milestone=_MILESTONE,
                as_of=config.generated_at,
                market_data_csv=config.market_data_csv,
                order_reconciliation_log=config.order_reconciliation_log,
            )
        )
    except ValidationError as exc:
        return {}, str(exc)
    return _mapping(record), ""


def _observed_usable_bars_from_cycle(
    cycle_record: Mapping[str, object],
    market_data: Mapping[str, object],
    sma: Mapping[str, object],
) -> int | None:
    if not _market_data_input_available(cycle_record, market_data):
        return None
    for value in (market_data.get("usable_bar_count"), sma.get("usable_bar_count")):
        integer = _optional_int(value)
        if integer is not None:
            return integer
    return None


def _market_data_input_available(
    cycle_record: Mapping[str, object],
    market_data: Mapping[str, object],
) -> bool:
    return (
        market_data.get("input_available") is True
        or cycle_record.get("bars_input_available") is True
    )


def _missing_usable_bars(
    required_usable_bars: int,
    observed_usable_bars: int | None,
) -> int | None:
    if observed_usable_bars is None:
        return None
    return max(required_usable_bars - observed_usable_bars, 0)


def _data_readiness_missing_evidence(
    evidence_error: str,
    cycle_record: Mapping[str, object],
    observed_usable_bars: int | None,
) -> list[str]:
    missing: list[str] = []
    market_data = _mapping(cycle_record.get("market_data"))
    if evidence_error:
        missing.append("offline_etf_sma_cycle_evidence")
    if not _market_data_input_available(cycle_record, market_data):
        missing.append("local_market_data_bars")
    if observed_usable_bars is None:
        missing.append("observed_usable_bars")
    return list(_dedupe(tuple(missing)))


def _readiness_state(
    required_usable_bars: int,
    observed_usable_bars: int | None,
) -> str:
    if observed_usable_bars is None:
        return "unknown_from_cycle_artifact"
    if observed_usable_bars < required_usable_bars:
        return "insufficient_history"
    return "ready_from_cycle_artifact"


def _readiness_reason(
    evidence_error: str,
    required_usable_bars: int,
    observed_usable_bars: int | None,
) -> str:
    if evidence_error:
        return "offline_etf_sma_cycle_evidence_unavailable"
    if observed_usable_bars is None:
        return "observed_usable_bars_missing"
    if observed_usable_bars < required_usable_bars:
        return "sma_insufficient_history"
    return "sma_usable_bars_ready"


def _config(value: object) -> EtfSmaCycleUnifiedPreviewConfig:
    if type(value) is not EtfSmaCycleUnifiedPreviewConfig:
        raise ValidationError("config must be an EtfSmaCycleUnifiedPreviewConfig.")
    return value


def _generated_at_text(value: object) -> str:
    if value is None:
        raise ValidationError("generated_at is required.")
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


def _derived_daily_preview_log(run_id: str) -> Path:
    return Path(f"{run_id}_{_DERIVED_DAILY_PREVIEW_SUFFIX}")


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


def _optional_path(value: object, field_name: str) -> Path | None:
    if value in (None, ""):
        return None
    return _required_path(value, field_name)


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


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _optional_int(value: object) -> int | None:
    if type(value) is int:
        return value if value >= 0 else None
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _first_int(*values: object, default: int | None = None) -> int:
    for value in values:
        integer = _optional_int(value)
        if integer is not None:
            return integer
    if default is None:
        raise ValidationError("integer evidence is required.")
    return default


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


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
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
