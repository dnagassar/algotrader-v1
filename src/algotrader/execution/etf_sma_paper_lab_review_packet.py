"""Offline operator review packet for the local-bars ETF/SMA proof chain.

The M402 packet is pure local file I/O. It reads an M401 proof JSONL record,
classifies the proof for operator review, and writes one deterministic handoff
record. It does not create a broker preview, submit path, or paper/live
execution authority.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_PAPER_LAB_REVIEW_PACKET_LABELS",
    "EtfSmaPaperLabReviewPacketConfig",
    "EtfSmaPaperLabReviewPacketWriteResult",
    "build_etf_sma_paper_lab_review_packet",
    "render_etf_sma_paper_lab_review_packet_json",
    "render_etf_sma_paper_lab_review_packet_text",
    "write_etf_sma_paper_lab_review_packet_jsonl",
]


ETF_SMA_PAPER_LAB_REVIEW_PACKET_LABELS = (
    "paper_lab_only",
    "operator_review_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M402 - Offline ETF/SMA paper-lab operator review packet"
_RECORD_TYPE = "etf_sma_paper_lab_review_packet"
_COMMAND = "etf-sma-paper-lab-review-packet"
_SOURCE_RECORD_TYPE = "local_bars_etf_sma_cycle_proof"
_DEFAULT_SYMBOL = "SPY"
_PROFIT_CLAIM = "none"
_READY_REVIEW_STATE = "ready_for_operator_review"
_INSUFFICIENT_HISTORY_REVIEW_STATE = "blocked_insufficient_history"
_SAFETY_VIOLATION_REVIEW_STATE = "blocked_safety_violation"
_SYMBOL_BLOCKED_REVIEW_STATE = "blocked_symbol_not_allowed"
_UNRECOGNIZED_REVIEW_STATE = "blocked_unrecognized_proof_state"
_READY_REVIEW_REASON = (
    "m401_local_bars_proof_ready_buy_preview_operator_review_only"
)
_INSUFFICIENT_HISTORY_REVIEW_REASON = "m401_local_bars_proof_insufficient_history"
_SAFETY_VIOLATION_REVIEW_REASON = (
    "m401_proof_contains_forbidden_authority_or_mutation_evidence"
)
_SYMBOL_BLOCKED_REVIEW_REASON = "symbol_scope_outside_spy_allowlist"
_UNRECOGNIZED_REVIEW_REASON = "m401_proof_not_ready_for_operator_handoff"
_READY_NEXT_ACTION = (
    "operator_may_run_separate_read_only_paper_snapshot_reconciliation_"
    "before_any_paper_submit"
)
_INSUFFICIENT_HISTORY_NEXT_ACTION = "refresh_or_import_more_local_bars_offline"
_SAFETY_VIOLATION_NEXT_ACTION = (
    "stop_and_rebuild_m401_proof_with_false_safety_flags_before_review"
)
_SYMBOL_BLOCKED_NEXT_ACTION = "use_spy_only_current_allowlist"
_UNRECOGNIZED_NEXT_ACTION = (
    "inspect_offline_proof_and_resolve_blockers_before_paper_lab_review"
)
_BROKER_ACTION_FLAGS = {
    "submit": False,
    "cancel": False,
    "replace": False,
    "close": False,
    "liquidate": False,
    "mutation": False,
}
_SOURCE_FALSE_FIELDS = {
    "broker_action_performed",
    "broker_actions_performed",
    "broker_mutation_allowed",
    "broker_mutation_authorized",
    "credential_access_attempted",
    "live_authorized",
    "mutated",
    "network_access_attempted",
    "paper_execution_authorized",
    "paper_submit_authorized",
    "submit_authorized",
    "submitted",
}
_WRITE_RESULT_FALSE_FIELDS = (
    "paper_execution_authorized",
    "submit_authorized",
    "broker_mutation_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)


@dataclass(frozen=True, slots=True)
class EtfSmaPaperLabReviewPacketConfig:
    """Explicit local inputs for one M402 operator review packet."""

    run_id: str
    symbol: str
    proof_log: Path | str
    run_log: Path | str
    generated_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(self, "proof_log", _input_jsonl_path(self.proof_log))
        object.__setattr__(self, "run_log", _output_jsonl_path(self.run_log))
        object.__setattr__(
            self,
            "generated_at",
            _timezone_aware_timestamp(self.generated_at, "generated_at"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaPaperLabReviewPacketWriteResult:
    """Local JSONL write metadata for the single review packet record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    paper_execution_authorized: bool
    submit_authorized: bool
    broker_mutation_authorized: bool
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
            "paper_execution_authorized": self.paper_execution_authorized,
            "submit_authorized": self.submit_authorized,
            "broker_mutation_authorized": self.broker_mutation_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_actions_performed": self.broker_actions_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


def build_etf_sma_paper_lab_review_packet(
    config: EtfSmaPaperLabReviewPacketConfig,
) -> dict[str, object]:
    """Build one deterministic M402 review packet from the latest M401 proof."""

    checked_config = _config(config)
    proof, proof_record_count, proof_record_line = _load_latest_proof_record(
        checked_config.proof_log
    )
    source_proof_run_id = _required_payload_string(proof, "run_id")
    source_proof_symbol = _required_payload_string(proof, "symbol")
    input_sha256 = _required_payload_string(proof, "input_sha256")
    canonical_sha256 = _required_payload_string(proof, "canonical_sha256")
    required_usable_bars = _required_payload_int(proof, "required_usable_bars")
    usable_bar_count = _required_payload_int(proof, "usable_bar_count")
    missing_usable_bars = _required_payload_int(proof, "missing_usable_bars")
    readiness_state = _required_payload_string(proof, "readiness_state")
    readiness_reason = _required_payload_string(proof, "readiness_reason")
    cycle_decision = _required_payload_string(proof, "cycle_decision")
    cycle_decision_reason = _required_payload_string(
        proof,
        "cycle_decision_reason",
    )
    cycle_next_allowed_action = _required_payload_string(
        proof,
        "cycle_next_allowed_action",
    )

    proof_blockers = _string_list(proof.get("blockers"))
    safety_blockers = _source_safety_blockers(proof)
    symbol_blockers = _symbol_blockers(
        requested_symbol=checked_config.symbol,
        source_symbol=source_proof_symbol,
    )
    review_state, review_reason, recommended_next_action, blockers = (
        _classify_review(
            readiness_state=readiness_state,
            missing_usable_bars=missing_usable_bars,
            cycle_decision=cycle_decision,
            proof_blockers=proof_blockers,
            safety_blockers=safety_blockers,
            symbol_blockers=symbol_blockers,
        )
    )

    broker_action_flags = dict(_BROKER_ACTION_FLAGS)
    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "symbol": checked_config.symbol,
        "generated_at": checked_config.generated_at,
        "source_proof_run_id": source_proof_run_id,
        "source_proof_log": str(checked_config.proof_log),
        "source_proof_record_count": proof_record_count,
        "source_proof_record_line": proof_record_line,
        "source_proof_symbol": source_proof_symbol,
        "input_sha256": input_sha256,
        "canonical_sha256": canonical_sha256,
        "required_usable_bars": required_usable_bars,
        "usable_bar_count": usable_bar_count,
        "missing_usable_bars": missing_usable_bars,
        "readiness_state": readiness_state,
        "readiness_reason": readiness_reason,
        "cycle_decision": cycle_decision,
        "cycle_decision_reason": cycle_decision_reason,
        "cycle_next_allowed_action": cycle_next_allowed_action,
        "review_state": review_state,
        "review_reason": review_reason,
        "operator_handoff": _operator_handoff(
            review_state=review_state,
            review_reason=review_reason,
            recommended_next_action=recommended_next_action,
        ),
        "evidence_summary": _evidence_summary(
            proof=proof,
            source_proof_run_id=source_proof_run_id,
            source_proof_log=checked_config.proof_log,
            readiness_state=readiness_state,
            readiness_reason=readiness_reason,
            required_usable_bars=required_usable_bars,
            usable_bar_count=usable_bar_count,
            missing_usable_bars=missing_usable_bars,
            cycle_decision=cycle_decision,
            cycle_decision_reason=cycle_decision_reason,
            cycle_next_allowed_action=cycle_next_allowed_action,
            input_sha256=input_sha256,
            canonical_sha256=canonical_sha256,
        ),
        "blockers": list(blockers),
        "paper_lab_only": True,
        "operator_review_only": True,
        "labels": list(ETF_SMA_PAPER_LAB_REVIEW_PACKET_LABELS),
        "profit_claim": _PROFIT_CLAIM,
        "not_live_authorized": True,
        "paper_execution_authorized": False,
        "paper_submit_authorized": False,
        "submit_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_action_flags": broker_action_flags,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "forbidden_actions": _forbidden_actions(),
        "next_forbidden_action": _forbidden_actions(),
    }


def render_etf_sma_paper_lab_review_packet_json(
    payload: Mapping[str, object],
) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_paper_lab_review_packet_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing review packet summary."""

    return "\n".join(
        (
            "ETF/SMA paper-lab review packet",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"source_proof_run_id: {payload.get('source_proof_run_id', '')}",
            f"source_proof_log: {payload.get('source_proof_log', '')}",
            f"usable_bar_count: {_none_text(payload.get('usable_bar_count'))}",
            f"required_usable_bars: {payload.get('required_usable_bars', '')}",
            f"missing_usable_bars: {_none_text(payload.get('missing_usable_bars'))}",
            f"readiness_state: {payload.get('readiness_state', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"review_state: {payload.get('review_state', '')}",
            f"review_reason: {payload.get('review_reason', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            "paper_execution_authorized: "
            f"{_bool_text(payload.get('paper_execution_authorized'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            "broker_mutation_authorized: "
            f"{_bool_text(payload.get('broker_mutation_authorized'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
        )
    )


def write_etf_sma_paper_lab_review_packet_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaPaperLabReviewPacketWriteResult:
    """Write exactly one review packet JSONL record, replacing prior contents."""

    path = _output_jsonl_path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_paper_lab_review_packet_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaPaperLabReviewPacketWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        paper_execution_authorized=False,
        submit_authorized=False,
        broker_mutation_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_actions_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _load_latest_proof_record(path: Path) -> tuple[Mapping[str, object], int, int]:
    if not path.exists() or not path.is_file():
        raise ValidationError("proof_log must reference an existing JSONL file.")

    records: list[tuple[int, Mapping[str, object]]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"proof_log contains invalid JSON at line {line_number}."
            ) from exc
        if not isinstance(parsed, Mapping):
            raise ValidationError(
                f"proof_log line {line_number} must contain a JSON object."
            )
        records.append((line_number, parsed))

    if not records:
        raise ValidationError("proof_log must contain at least one JSON object.")

    selected_line, selected_record = records[-1]
    return selected_record, len(records), selected_line


def _classify_review(
    *,
    readiness_state: str,
    missing_usable_bars: int,
    cycle_decision: str,
    proof_blockers: tuple[str, ...],
    safety_blockers: tuple[str, ...],
    symbol_blockers: tuple[str, ...],
) -> tuple[str, str, str, tuple[str, ...]]:
    if safety_blockers:
        blockers = _dedupe((*safety_blockers, *symbol_blockers, *proof_blockers))
        return (
            _SAFETY_VIOLATION_REVIEW_STATE,
            _SAFETY_VIOLATION_REVIEW_REASON,
            _SAFETY_VIOLATION_NEXT_ACTION,
            blockers,
        )
    if symbol_blockers:
        blockers = _dedupe((*symbol_blockers, *proof_blockers))
        return (
            _SYMBOL_BLOCKED_REVIEW_STATE,
            _SYMBOL_BLOCKED_REVIEW_REASON,
            _SYMBOL_BLOCKED_NEXT_ACTION,
            blockers,
        )
    if readiness_state == "insufficient_history" or missing_usable_bars > 0:
        blockers = _dedupe((*proof_blockers, "missing_usable_bars"))
        return (
            _INSUFFICIENT_HISTORY_REVIEW_STATE,
            _INSUFFICIENT_HISTORY_REVIEW_REASON,
            _INSUFFICIENT_HISTORY_NEXT_ACTION,
            blockers,
        )
    if (
        readiness_state == "ready"
        and missing_usable_bars == 0
        and cycle_decision == "buy_preview"
        and not proof_blockers
    ):
        return (
            _READY_REVIEW_STATE,
            _READY_REVIEW_REASON,
            _READY_NEXT_ACTION,
            (),
        )

    blockers = _dedupe((*proof_blockers, "unrecognized_m401_proof_state"))
    return (
        _UNRECOGNIZED_REVIEW_STATE,
        _UNRECOGNIZED_REVIEW_REASON,
        _UNRECOGNIZED_NEXT_ACTION,
        blockers,
    )


def _operator_handoff(
    *,
    review_state: str,
    review_reason: str,
    recommended_next_action: str,
) -> dict[str, object]:
    return {
        "handoff_state": review_state,
        "review_reason": review_reason,
        "recommended_next_action": recommended_next_action,
        "offline_evidence_only": True,
        "broker_or_paper_execution_separated": True,
        "separate_read_only_paper_snapshot_reconciliation_required": (
            review_state == _READY_REVIEW_STATE
        ),
        "separate_submit_milestone_required": True,
        "paper_execution_authorized": False,
        "submit_authorized": False,
        "broker_mutation_authorized": False,
        "submitted": False,
        "mutated": False,
        "live_authorized": False,
    }


def _evidence_summary(
    *,
    proof: Mapping[str, object],
    source_proof_run_id: str,
    source_proof_log: Path,
    readiness_state: str,
    readiness_reason: str,
    required_usable_bars: int,
    usable_bar_count: int,
    missing_usable_bars: int,
    cycle_decision: str,
    cycle_decision_reason: str,
    cycle_next_allowed_action: str,
    input_sha256: str,
    canonical_sha256: str,
) -> dict[str, object]:
    return {
        "offline_evidence_source": "m401_local_bars_etf_sma_cycle_proof",
        "source_record_type": _text(proof.get("record_type")),
        "source_command": _text(proof.get("command")),
        "source_proof_run_id": source_proof_run_id,
        "source_proof_log": str(source_proof_log),
        "input_sha256": input_sha256,
        "canonical_sha256": canonical_sha256,
        "required_usable_bars": required_usable_bars,
        "usable_bar_count": usable_bar_count,
        "missing_usable_bars": missing_usable_bars,
        "readiness_state": readiness_state,
        "readiness_reason": readiness_reason,
        "cycle_decision": cycle_decision,
        "cycle_decision_reason": cycle_decision_reason,
        "cycle_next_allowed_action": cycle_next_allowed_action,
        "proof_submitted": _payload_bool_or_none(proof.get("submitted")),
        "proof_mutated": _payload_bool_or_none(proof.get("mutated")),
        "proof_network_access_attempted": _payload_bool_or_none(
            proof.get("network_access_attempted")
        ),
        "proof_credential_access_attempted": _payload_bool_or_none(
            proof.get("credential_access_attempted")
        ),
        "proof_live_authorized": _payload_bool_or_none(
            proof.get("live_authorized")
        ),
        "broker_or_paper_execution_evidence": "none_from_m402_review_packet",
    }


def _source_safety_blockers(proof: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []

    if proof.get("record_type") != _SOURCE_RECORD_TYPE:
        blockers.append("source_record_type_unexpected")
    if proof.get("command") != "local-bars-etf-sma-cycle-proof":
        blockers.append("source_command_unexpected")
    if proof.get("profit_claim") != _PROFIT_CLAIM:
        blockers.append("source_profit_claim_not_none")
    if proof.get("not_live_authorized") is not True:
        blockers.append("source_not_live_authorized_missing_or_false")

    labels = _string_list(proof.get("labels"))
    if "profit_claim=none" not in labels:
        blockers.append("source_missing_profit_claim_none_label")
    if "not_live_authorized" not in labels:
        blockers.append("source_missing_not_live_authorized_label")

    for key, value in _walk_mapping_items(proof):
        if key in _SOURCE_FALSE_FIELDS and value is True:
            blockers.append(f"source_{key}_true")
        if key == "broker_action_flags" and isinstance(value, Mapping):
            for action, flag in value.items():
                if flag is True:
                    blockers.append(f"source_broker_action_flag_{action}_true")
        if key == "profit_claim" and value not in (None, _PROFIT_CLAIM):
            blockers.append("source_profit_claim_not_none")
        if type(value) is str and value.startswith("profit_claim="):
            if value != "profit_claim=none":
                blockers.append("source_profit_claim_not_none")
        if (
            type(value) is str
            and value != "not_live_authorized"
            and value != "not_live_authorization"
            and value == "live_authorized"
        ):
            blockers.append("source_contains_live_authorized_text")

    return _dedupe(tuple(blockers))


def _symbol_blockers(
    *,
    requested_symbol: str,
    source_symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if requested_symbol != _DEFAULT_SYMBOL:
        blockers.append("symbol_not_spy")
    if source_symbol != _DEFAULT_SYMBOL:
        blockers.append("source_symbol_not_spy")
    if source_symbol != requested_symbol:
        blockers.append("source_symbol_mismatch")
    return tuple(blockers)


def _forbidden_actions() -> list[str]:
    return [
        "broker_mutation_from_etf_sma_paper_lab_review_packet",
        "paper_submit_from_etf_sma_paper_lab_review_packet",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_review_packet",
    ]


def _config(value: object) -> EtfSmaPaperLabReviewPacketConfig:
    if type(value) is not EtfSmaPaperLabReviewPacketConfig:
        raise ValidationError("config must be an EtfSmaPaperLabReviewPacketConfig.")
    return value


def _input_jsonl_path(value: object) -> Path:
    path = _local_jsonl_path(value, "proof_log")
    if not path.exists() or not path.is_file():
        raise ValidationError("proof_log must reference an existing JSONL file.")
    return path


def _output_jsonl_path(value: object) -> Path:
    path = _local_jsonl_path(value, "run_log")
    if path.exists() and path.is_dir():
        raise ValidationError("run_log must not be a directory.")
    return path


def _local_jsonl_path(value: object, field_name: str) -> Path:
    path = _required_path(value, field_name)
    if type(value) is str and "://" in value:
        raise ValidationError(f"{field_name} must be a local JSONL path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must reference a JSONL file.")
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


def _timezone_aware_timestamp(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return text


def _required_payload_string(
    payload: Mapping[str, object],
    field_name: str,
) -> str:
    value = payload.get(field_name)
    if type(value) is not str or value == "":
        raise ValidationError(f"proof_log latest record missing {field_name}.")
    return value


def _required_payload_int(payload: Mapping[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    if type(value) is not int or value < 0:
        raise ValidationError(f"proof_log latest record missing {field_name}.")
    return value


def _walk_mapping_items(value: object) -> tuple[tuple[str, object], ...]:
    items: list[tuple[str, object]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is str:
                items.append((key, item))
            items.extend(_walk_mapping_items(item))
    elif type(value) in (list, tuple):
        for item in value:
            items.extend(_walk_mapping_items(item))
    return tuple(items)


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _payload_bool_or_none(value: object) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_json_safe(item) for item in value]
    if type(value) is list:
        return [_json_safe(item) for item in value]
    return value


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _none_text(value: object) -> str:
    if value is None:
        return "unknown"
    return str(value)


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
