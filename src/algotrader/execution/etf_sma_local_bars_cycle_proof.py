"""Offline proof chain for local daily bars through the ETF/SMA cycle.

The proof command is intentionally local file I/O only. It canonicalizes an
operator-supplied CSV, validates the canonical CSV, consumes it through the
unified ETF/SMA cycle path, and writes deterministic JSONL evidence without
broker, credential, or network behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars_checkpoint import (
    LocalDailyBarsCheckpointConfig,
    build_local_daily_bars_checkpoint,
    write_local_daily_bars_checkpoint_jsonl,
)
from algotrader.research.local_daily_bars_intake import (
    LocalDailyBarsIntakeConfig,
    build_local_daily_bars_intake_manifest,
    write_local_daily_bars_intake_manifest_jsonl,
)

from .etf_sma_cycle_unified_preview import (
    EtfSmaCycleUnifiedPreviewConfig,
    build_etf_sma_cycle_unified_preview,
    write_etf_sma_cycle_unified_preview_jsonl,
)

__all__ = [
    "ETF_SMA_LOCAL_BARS_CYCLE_PROOF_LABELS",
    "EtfSmaLocalBarsCycleProofConfig",
    "EtfSmaLocalBarsCycleProofWriteResult",
    "build_etf_sma_local_bars_cycle_proof",
    "render_etf_sma_local_bars_cycle_proof_json",
    "render_etf_sma_local_bars_cycle_proof_text",
    "write_etf_sma_local_bars_cycle_proof_jsonl",
]


ETF_SMA_LOCAL_BARS_CYCLE_PROOF_LABELS = (
    "paper_lab_only",
    "data_readiness_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M401 - Offline local-bars ETF/SMA cycle end-to-end proof"
_RECORD_TYPE = "local_bars_etf_sma_cycle_proof"
_COMMAND = "local-bars-etf-sma-cycle-proof"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_REQUIRED_USABLE_BARS = 200
_PROFIT_CLAIM = "none"
_WRITE_RESULT_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_BROKER_ACTION_FLAGS = {
    "submit": False,
    "cancel": False,
    "replace": False,
    "close": False,
    "liquidate": False,
    "mutation": False,
}


@dataclass(frozen=True, slots=True)
class EtfSmaLocalBarsCycleProofConfig:
    """Explicit local inputs for one end-to-end local bars proof."""

    run_id: str
    input_csv: Path | str
    canonical_csv: Path | str
    as_of: date | datetime | str
    run_log: Path | str
    symbol: str = _DEFAULT_SYMBOL

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "input_csv",
            _input_csv_path(self.input_csv),
        )
        object.__setattr__(
            self,
            "canonical_csv",
            _output_csv_path(self.canonical_csv),
        )
        object.__setattr__(self, "run_log", _output_jsonl_path(self.run_log))
        if self.as_of is None:
            raise ValidationError("as_of is required.")


@dataclass(frozen=True, slots=True)
class EtfSmaLocalBarsCycleProofWriteResult:
    """Local JSONL write metadata for the single proof record."""

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
        object.__setattr__(self, "output_path", _output_jsonl_path(self.output_path))
        if self.record_count != 1:
            raise ValidationError("record_count must be exactly 1.")
        if self.bytes_written <= 0:
            raise ValidationError("bytes_written must be positive.")
        if self.newline_terminated is not True:
            raise ValidationError("newline_terminated must be true.")
        for field_name in _WRITE_RESULT_FALSE_FIELDS:
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


@dataclass(frozen=True, slots=True)
class _ProofArtifacts:
    intake_manifest_log: Path
    checkpoint_log: Path
    order_reconciliation_log: Path
    cycle_log: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "intake_manifest_log": str(self.intake_manifest_log),
            "checkpoint_log": str(self.checkpoint_log),
            "order_reconciliation_log": str(self.order_reconciliation_log),
            "cycle_log": str(self.cycle_log),
        }


def build_etf_sma_local_bars_cycle_proof(
    config: EtfSmaLocalBarsCycleProofConfig,
) -> dict[str, object]:
    """Build and write all local artifacts except the final proof JSONL line."""

    checked_config = _config(config)
    as_of_date, generated_at = _as_of_parts(checked_config.as_of)
    artifacts = _proof_artifacts(checked_config.run_log)
    source_run_ids = _source_run_ids(checked_config.run_id)

    intake_payload = build_local_daily_bars_intake_manifest(
        LocalDailyBarsIntakeConfig(
            run_id=source_run_ids["intake_run_id"],
            symbol=checked_config.symbol,
            input_csv=checked_config.input_csv,
            output_csv=checked_config.canonical_csv,
            as_of=as_of_date,
            required_usable_bars=_DEFAULT_REQUIRED_USABLE_BARS,
        )
    )
    intake_write = write_local_daily_bars_intake_manifest_jsonl(
        intake_payload,
        artifacts.intake_manifest_log,
    )

    checkpoint_payload = build_local_daily_bars_checkpoint(
        LocalDailyBarsCheckpointConfig(
            run_id=source_run_ids["checkpoint_run_id"],
            symbol=checked_config.symbol,
            daily_bars_csv=checked_config.canonical_csv,
            as_of=as_of_date,
            required_usable_bars=_DEFAULT_REQUIRED_USABLE_BARS,
        )
    )
    checkpoint_write = write_local_daily_bars_checkpoint_jsonl(
        checkpoint_payload,
        artifacts.checkpoint_log,
    )

    reconciliation_record = _offline_reconciliation_record(
        run_id=source_run_ids["order_reconciliation_run_id"],
        symbol=checked_config.symbol,
    )
    reconciliation_write = _write_jsonl_record(
        reconciliation_record,
        artifacts.order_reconciliation_log,
    )

    cycle_payload = build_etf_sma_cycle_unified_preview(
        EtfSmaCycleUnifiedPreviewConfig(
            run_id=source_run_ids["cycle_run_id"],
            symbol=checked_config.symbol,
            generated_at=generated_at,
            order_reconciliation_log=artifacts.order_reconciliation_log,
            daily_bars_csv=checked_config.canonical_csv,
        )
    )
    cycle_write = write_etf_sma_cycle_unified_preview_jsonl(
        cycle_payload,
        artifacts.cycle_log,
    )

    readiness = _mapping(cycle_payload.get("data_readiness"))
    source_market_data = _mapping(readiness.get("source_market_data"))
    usable_bar_count = _first_int(
        readiness.get("observed_usable_bars"),
        checkpoint_payload.get("usable_bar_count"),
    )
    required_usable_bars = _first_int(
        readiness.get("required_usable_bars"),
        checkpoint_payload.get("required_usable_bars"),
        _DEFAULT_REQUIRED_USABLE_BARS,
    )
    missing_usable_bars = _first_int(
        readiness.get("missing_usable_bars"),
        checkpoint_payload.get("missing_usable_bars"),
    )
    blockers = _proof_blockers(
        intake_payload,
        checkpoint_payload,
        cycle_payload,
        readiness,
    )
    broker_action_flags = dict(_BROKER_ACTION_FLAGS)

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "symbol": checked_config.symbol,
        "as_of": as_of_date,
        "generated_at": generated_at,
        "scope": f"{checked_config.symbol}_paper_lab_only",
        "labels": list(ETF_SMA_LOCAL_BARS_CYCLE_PROOF_LABELS),
        "paper_lab_only": True,
        "data_readiness_only": True,
        "signal_evaluation_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "input_csv": str(checked_config.input_csv),
        "canonical_csv": str(checked_config.canonical_csv),
        "input_sha256": _text(intake_payload.get("input_sha256")),
        "canonical_sha256": _text(intake_payload.get("output_sha256")),
        "intake_status": "canonicalized",
        "checkpoint_status": _text(checkpoint_payload.get("readiness_state")),
        "cycle_status": _text(readiness.get("readiness_state")),
        "required_usable_bars": required_usable_bars,
        "usable_bar_count": usable_bar_count,
        "missing_usable_bars": missing_usable_bars,
        "readiness_state": _text(readiness.get("readiness_state")),
        "readiness_reason": _text(readiness.get("readiness_reason")),
        "cycle_decision": _text(cycle_payload.get("cycle_decision")),
        "cycle_decision_reason": _text(
            cycle_payload.get("cycle_decision_reason")
        ),
        "cycle_next_allowed_action": _text(
            cycle_payload.get("cycle_next_allowed_action")
        ),
        "next_allowed_action": _text(cycle_payload.get("next_allowed_action")),
        "future_bar_count_excluded": _first_int(
            intake_payload.get("future_bar_count_excluded"),
            0,
        ),
        "intake_future_bar_count_excluded": _first_int(
            intake_payload.get("future_bar_count_excluded"),
            0,
        ),
        "checkpoint_future_bar_count_excluded": _first_int(
            checkpoint_payload.get("future_bar_count_excluded"),
            0,
        ),
        "cycle_future_bar_count_excluded": _first_int(
            source_market_data.get("ignored_future_bar_count"),
            0,
        ),
        "artifact_paths": artifacts.to_dict(),
        "source_run_ids": source_run_ids,
        "intake_summary": _intake_summary(intake_payload),
        "checkpoint_summary": _checkpoint_summary(checkpoint_payload),
        "cycle_summary": _cycle_summary(cycle_payload),
        "artifact_write_results": {
            "intake_manifest": intake_write.to_dict(),
            "checkpoint": checkpoint_write.to_dict(),
            "order_reconciliation": reconciliation_write,
            "cycle": cycle_write.to_dict(),
        },
        "blockers": blockers,
        "safety_summary": {
            "paper_lab_only": True,
            "broker_mutation_allowed": False,
            "not_live_authorized": True,
            "live_authorized": False,
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "broker_actions_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "broker_action_flags": broker_action_flags,
        },
        "broker_action_flags": broker_action_flags,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "forbidden_actions": _forbidden_actions(),
        "next_forbidden_action": _forbidden_actions(),
    }


def render_etf_sma_local_bars_cycle_proof_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_local_bars_cycle_proof_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing proof summary."""

    return "\n".join(
        (
            "Local bars ETF/SMA cycle proof",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"as_of: {payload.get('as_of', '')}",
            f"input_csv: {payload.get('input_csv', '')}",
            f"canonical_csv: {payload.get('canonical_csv', '')}",
            f"usable_bar_count: {_none_text(payload.get('usable_bar_count'))}",
            f"required_usable_bars: {payload.get('required_usable_bars', '')}",
            f"missing_usable_bars: {_none_text(payload.get('missing_usable_bars'))}",
            f"readiness_state: {payload.get('readiness_state', '')}",
            f"readiness_reason: {payload.get('readiness_reason', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"cycle_decision_reason: {payload.get('cycle_decision_reason', '')}",
            f"cycle_next_allowed_action: {payload.get('cycle_next_allowed_action', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
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


def write_etf_sma_local_bars_cycle_proof_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaLocalBarsCycleProofWriteResult:
    """Write exactly one proof JSONL record, replacing prior contents."""

    path = _output_jsonl_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_local_bars_cycle_proof_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaLocalBarsCycleProofWriteResult(
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


def _proof_artifacts(run_log: Path) -> _ProofArtifacts:
    stem = run_log.stem or "local_bars_etf_sma_cycle_proof"
    parent = run_log.parent
    return _ProofArtifacts(
        intake_manifest_log=parent / f"{stem}_intake_manifest.jsonl",
        checkpoint_log=parent / f"{stem}_local_daily_bars_checkpoint.jsonl",
        order_reconciliation_log=parent / f"{stem}_order_reconciliation.jsonl",
        cycle_log=parent / f"{stem}_etf_sma_cycle.jsonl",
    )


def _source_run_ids(run_id: str) -> dict[str, str]:
    return {
        "intake_run_id": f"{run_id}_intake",
        "checkpoint_run_id": f"{run_id}_checkpoint",
        "order_reconciliation_run_id": f"{run_id}_offline_reconciliation",
        "cycle_run_id": f"{run_id}_cycle",
    }


def _offline_reconciliation_record(*, run_id: str, symbol: str) -> dict[str, object]:
    checked_symbol = symbol_value(symbol)
    return {
        "run_id": run_id,
        "record_type": "offline_order_reconciliation_fixture",
        "symbol": checked_symbol,
        "client_order_id": "offline-proof-no-broker-order",
        "broker_order_id": "offline-proof-no-broker-order",
        "expected_side": "sell",
        "expected_qty": "0",
        "observed_status": "filled",
        "observed_symbol": checked_symbol,
        "observed_side": "sell",
        "observed_qty": "0",
        "observed_filled_qty": "0",
        "observed_remaining_qty": "0",
        "exact_order_found": True,
        "exact_order_source": "offline_fixture",
        "terminal_state": "terminal",
        "terminal_reason": "offline_fixture_no_open_orders",
        "reconciliation_decision": "offline_terminal_no_open_orders",
        "next_spy_submit_blocked": False,
        "reason": "offline_fixture_no_open_orders",
        "spy_position_qty": "",
        "open_order_count": 0,
        "spy_open_order_count": 0,
        "open_order_symbols": [],
        "open_order_client_order_ids": [],
        "open_order_broker_order_ids": [],
        "open_order_statuses": [],
        "open_order_sides": [],
        "open_order_quantities": [],
        "open_order_filled_quantities": [],
        "non_spy_positions": [],
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "account_observation_available": True,
        "positions_observation_available": True,
        "orders_observation_available": True,
    }


def _write_jsonl_record(
    payload: Mapping[str, object],
    output_path: Path,
) -> dict[str, object]:
    path = _output_jsonl_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))
    text = line + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return {
        "output_path": str(path),
        "record_count": 1,
        "bytes_written": len(text.encode("utf-8")),
        "newline_terminated": True,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _intake_summary(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": _text(payload.get("record_type")),
        "command": _text(payload.get("command")),
        "run_id": _text(payload.get("run_id")),
        "input_csv": _text(payload.get("input_csv")),
        "output_csv": _text(payload.get("output_csv")),
        "input_sha256": _text(payload.get("input_sha256")),
        "output_sha256": _text(payload.get("output_sha256")),
        "accepted_row_count": _first_int(payload.get("accepted_row_count")),
        "usable_bar_count": _first_int(payload.get("usable_bar_count")),
        "missing_usable_bars": _first_int(payload.get("missing_usable_bars")),
        "readiness_state": _text(payload.get("readiness_state")),
        "readiness_reason": _text(payload.get("readiness_reason")),
        "future_bar_count_excluded": _first_int(
            payload.get("future_bar_count_excluded"),
        ),
        "submitted": False,
        "mutated": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _checkpoint_summary(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": _text(payload.get("record_type")),
        "command": _text(payload.get("command")),
        "run_id": _text(payload.get("run_id")),
        "daily_bars_csv": _text(payload.get("daily_bars_csv")),
        "usable_bar_count": _first_int(payload.get("usable_bar_count")),
        "required_usable_bars": _first_int(payload.get("required_usable_bars")),
        "missing_usable_bars": _first_int(payload.get("missing_usable_bars")),
        "readiness_state": _text(payload.get("readiness_state")),
        "readiness_reason": _text(payload.get("readiness_reason")),
        "future_bar_count_excluded": _first_int(
            payload.get("future_bar_count_excluded"),
        ),
        "submitted": False,
        "mutated": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _cycle_summary(payload: Mapping[str, object]) -> dict[str, object]:
    readiness = _mapping(payload.get("data_readiness"))
    return {
        "record_type": _text(payload.get("record_type")),
        "command": _text(payload.get("command")),
        "run_id": _text(payload.get("run_id")),
        "daily_preview_status": _text(payload.get("daily_preview_status")),
        "state_rollup_status": _text(payload.get("state_rollup_status")),
        "cycle_decision": _text(payload.get("cycle_decision")),
        "cycle_decision_reason": _text(payload.get("cycle_decision_reason")),
        "cycle_next_allowed_action": _text(
            payload.get("cycle_next_allowed_action")
        ),
        "required_usable_bars": _first_int(readiness.get("required_usable_bars")),
        "observed_usable_bars": _first_int(readiness.get("observed_usable_bars")),
        "missing_usable_bars": _first_int(readiness.get("missing_usable_bars")),
        "readiness_state": _text(readiness.get("readiness_state")),
        "readiness_reason": _text(readiness.get("readiness_reason")),
        "source_record_type": _text(readiness.get("source_record_type")),
        "blockers": list(_string_list(payload.get("blockers"))),
        "submitted": False,
        "mutated": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _proof_blockers(
    intake_payload: Mapping[str, object],
    checkpoint_payload: Mapping[str, object],
    cycle_payload: Mapping[str, object],
    readiness: Mapping[str, object],
) -> list[str]:
    blockers = [
        *_string_list(intake_payload.get("blockers")),
        *_string_list(checkpoint_payload.get("blockers")),
        *_string_list(cycle_payload.get("blockers")),
        *_string_list(readiness.get("missing_evidence")),
    ]
    return list(_dedupe(tuple(blockers)))


def _forbidden_actions() -> list[str]:
    return [
        "broker_mutation_from_local_bars_etf_sma_cycle_proof",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_local_bars_cycle_proof",
    ]


def _config(value: object) -> EtfSmaLocalBarsCycleProofConfig:
    if type(value) is not EtfSmaLocalBarsCycleProofConfig:
        raise ValidationError("config must be an EtfSmaLocalBarsCycleProofConfig.")
    return value


def _as_of_parts(value: date | datetime | str) -> tuple[str, str]:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("as_of timestamp must be timezone-aware.")
        return value.date().isoformat(), value.isoformat()
    if type(value) is date:
        return value.isoformat(), _utc_midnight(value)
    if type(value) is str:
        text = _required_string(value, "as_of")
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            try:
                parsed_date = date.fromisoformat(text)
            except ValueError as exc:
                raise ValidationError("as_of must be an ISO date or timestamp.") from exc
            if parsed_date.isoformat() != text:
                raise ValidationError("as_of must be an ISO date or timestamp.")
            return text, _utc_midnight(parsed_date)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("as_of must be an ISO date or timestamp.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError("as_of timestamp must be timezone-aware.")
        return parsed.date().isoformat(), parsed.isoformat()
    raise ValidationError("as_of must be an ISO date or timezone-aware timestamp.")


def _utc_midnight(value: date) -> str:
    return datetime.combine(value, time.min, tzinfo=UTC).isoformat()


def _input_csv_path(value: object) -> Path:
    path = _local_csv_path(value, "input_csv")
    if not path.is_file():
        raise ValidationError("input_csv must reference an existing local CSV file.")
    return path


def _output_csv_path(value: object) -> Path:
    path = _local_csv_path(value, "canonical_csv")
    if path.exists() and path.is_dir():
        raise ValidationError("canonical_csv must not be a directory.")
    return path


def _local_csv_path(value: object, field_name: str) -> Path:
    path = _required_path(value, field_name)
    if type(value) is str and "://" in value:
        raise ValidationError(f"{field_name} must be a local CSV path.")
    if path.suffix.lower() != ".csv":
        raise ValidationError(f"{field_name} must reference a CSV file.")
    return path


def _output_jsonl_path(value: object) -> Path:
    path = _required_path(value, "run_log")
    if path.exists() and path.is_dir():
        raise ValidationError("run_log must not be a directory.")
    return path


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


def _first_int(*values: object) -> int | None:
    for value in values:
        if type(value) is int:
            return value if value >= 0 else None
        if type(value) is str and value.isdigit():
            return int(value)
    return None


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
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _none_text(value: object) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
