"""M434 offline approval packet for a future tiny SPY paper buy submit.

This module is a deterministic local artifact reducer. It reads the M433
offline operator review packet only and never loads broker configuration,
credentials, SDKs, runtime broker paths, or network paths.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "DEFAULT_M433_OFFLINE_OPERATOR_REVIEW_PACKET_PATH",
    "DEFAULT_M434_OFFLINE_PAPER_BUY_SUBMIT_APPROVAL_PACKET_PATH",
    "EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig",
    "EtfSmaM434OfflinePaperBuySubmitApprovalPacketWriteResult",
    "build_etf_sma_m434_offline_paper_buy_submit_approval_packet",
    "render_etf_sma_m434_offline_paper_buy_submit_approval_packet_json",
    "render_etf_sma_m434_offline_paper_buy_submit_approval_packet_text",
    "write_etf_sma_m434_offline_paper_buy_submit_approval_packet_jsonl",
]


DEFAULT_M433_OFFLINE_OPERATOR_REVIEW_PACKET_PATH = (
    Path("runs") / "paper_lab" / "m433_offline_operator_review_packet.jsonl"
)
DEFAULT_M434_OFFLINE_PAPER_BUY_SUBMIT_APPROVAL_PACKET_PATH = (
    Path("runs")
    / "paper_lab"
    / "m434_offline_paper_buy_submit_approval_packet.jsonl"
)

_COMMAND = "etf-sma-m434-offline-buy-submit-approval-packet"
_RECORD_TYPE = "etf_sma_m434_offline_paper_buy_submit_approval_packet"
_SCHEMA_VERSION = "1"
_MILESTONE = "M434"
_APPROVAL_SCOPE = "offline_paper_buy_submit_approval_packet"
_SYMBOL = "SPY"
_SIDE = "buy"
_ASSET_CLASS = "equity"
_INTENDED_ORDER_TYPE = "market"
_INTENDED_TIME_IN_FORCE = "day"
_SOURCE_READY_DECISION = (
    "ready_for_separate_operator_authorized_paper_buy_submit_milestone"
)
_READY_APPROVAL_DECISION = "ready_for_explicit_operator_authorization"
_BLOCKED_APPROVAL_DECISION = "blocked_m433_not_ready"
_READY_NEXT_MILESTONE = "M435_operator_authorized_tiny_spy_paper_buy_submit"
_BLOCKED_NEXT_MILESTONE = "rerun_m433_offline_operator_review_packet_before_submit"
_PROFIT_CLAIM = "none"
_TRADE_RECOMMENDATION = "none"
_SAFETY_FALSE_FIELDS = (
    "submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_read_only",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_SOURCE_FALSE_FIELDS = (
    "submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_read_only",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_REQUIRED_FRESH_PRE_SUBMIT_CHECKS = (
    "APP_PROFILE must be paper inside the scoped submit shell.",
    "Alpaca/APCA credentials may be loaded only inside the scoped paper shell "
    "and never printed.",
    "Fresh broker-observed read-only pre-submit reconciliation must run "
    "immediately before submit.",
    "Post-submit read-only reconciliation must be required in the later "
    "submit milestone.",
    "Normal pytest after any paper shell must run only after APP_PROFILE and "
    "Alpaca/APCA credential booleans are false.",
)
_REQUIRED_SUBMIT_GATES = (
    "Live profile, live URL, or live broker support must fail closed.",
    "Symbol allowlist must be SPY only.",
    "Order must be paper-only.",
    "submit_order must be the only allowed mutation surface.",
    "cancel/replace/close/liquidate/delete/retry must remain forbidden.",
    "Submit must be single-attempt, no retry.",
    "Operator must explicitly authorize the separate submit milestone.",
)
_REQUIRED_DUPLICATE_ID_GUARD = (
    "Duplicate client_order_id must be checked before submit.",
)
_REQUIRED_OPEN_ORDER_GUARD = ("No open SPY order may exist.",)
_REQUIRED_POSITION_GUARD = (
    "No unexpected non-SPY position may exist.",
    "SPY position must be absent/zero before a buy submit.",
)
_REQUIRED_REDACTION_CHECK = (
    "Credentials may never be printed.",
    "Redaction check must run before operator-facing submit artifacts.",
)


@dataclass(frozen=True, slots=True)
class EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig:
    """Explicit local inputs for one M434 offline approval packet."""

    run_id: str
    m433_review_path: str | Path = DEFAULT_M433_OFFLINE_OPERATOR_REVIEW_PACKET_PATH

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "m433_review_path",
            _jsonl_path(self.m433_review_path, "m433_review_path"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaM434OfflinePaperBuySubmitApprovalPacketWriteResult:
    """Local JSONL write metadata for the single M434 record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    paper_only: bool
    operator_approval_required: bool
    required_single_attempt_submit: bool
    submit_authorized: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
    broker_read_only: bool
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
        object.__setattr__(self, "paper_only", _true_bool(self.paper_only, "paper_only"))
        object.__setattr__(
            self,
            "operator_approval_required",
            _true_bool(self.operator_approval_required, "operator_approval_required"),
        )
        object.__setattr__(
            self,
            "required_single_attempt_submit",
            _true_bool(
                self.required_single_attempt_submit,
                "required_single_attempt_submit",
            ),
        )
        for field_name in _SAFETY_FALSE_FIELDS:
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
            "paper_only": self.paper_only,
            "operator_approval_required": self.operator_approval_required,
            "required_single_attempt_submit": self.required_single_attempt_submit,
            "submit_authorized": self.submit_authorized,
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "broker_read_only": self.broker_read_only,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


def build_etf_sma_m434_offline_paper_buy_submit_approval_packet(
    config: EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig,
) -> dict[str, object]:
    """Build one deterministic local-only M434 approval packet."""

    checked_config = _config(config)
    payload = _base_payload(checked_config)
    m433_record, read_blockers = _load_single_jsonl_record(
        checked_config.m433_review_path,
        "source_m433",
    )

    source_readiness = ""
    source_next = ""
    source_blockers: tuple[str, ...] = ()
    if m433_record is not None:
        source_readiness = _first_text(m433_record.get("readiness_decision"))
        source_next = _first_text(m433_record.get("next_required_milestone"))
        source_blockers = _string_list(m433_record.get("blockers"))

    payload.update(
        {
            "source_m433_readiness_decision": source_readiness,
            "source_next_required_milestone": source_next,
        }
    )

    blockers = list(read_blockers)
    if m433_record is not None:
        blockers.extend(_source_m433_shape_blockers(m433_record))
        if source_readiness != _SOURCE_READY_DECISION:
            blockers.append(
                "source_m433_readiness_decision_not_ready:"
                f"{source_readiness or 'missing'}"
            )
        if source_blockers:
            blockers.append("source_m433_blockers_present")
            blockers.extend(f"source_m433_blocker:{item}" for item in source_blockers)

    if blockers:
        return _complete_payload(
            payload,
            approval_decision=_BLOCKED_APPROVAL_DECISION,
            next_required_milestone=_BLOCKED_NEXT_MILESTONE,
            blockers=blockers,
        )

    return _complete_payload(
        payload,
        approval_decision=_READY_APPROVAL_DECISION,
        next_required_milestone=_READY_NEXT_MILESTONE,
        blockers=[],
    )


def render_etf_sma_m434_offline_paper_buy_submit_approval_packet_json(
    payload: Mapping[str, object],
) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_m434_offline_paper_buy_submit_approval_packet_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing M434 packet summary."""

    return "\n".join(
        (
            "M434 offline paper buy submit approval packet",
            f"run_id: {payload.get('run_id', '')}",
            f"source_m433_artifact: {payload.get('source_m433_artifact', '')}",
            "source_m433_readiness_decision: "
            f"{payload.get('source_m433_readiness_decision', '')}",
            "source_next_required_milestone: "
            f"{payload.get('source_next_required_milestone', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"side: {payload.get('side', '')}",
            f"approval_decision: {payload.get('approval_decision', '')}",
            f"next_required_milestone: {payload.get('next_required_milestone', '')}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            "operator_approval_required: "
            f"{_bool_text(payload.get('operator_approval_required'))}",
            f"submit_authorized: {_bool_text(payload.get('submit_authorized'))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            f"broker_read_only: {_bool_text(payload.get('broker_read_only'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"trade_recommendation: {payload.get('trade_recommendation', '')}",
            f"profit_claim: {payload.get('profit_claim', '')}",
        )
    )


def write_etf_sma_m434_offline_paper_buy_submit_approval_packet_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaM434OfflinePaperBuySubmitApprovalPacketWriteResult:
    """Write exactly one JSONL record, replacing any prior local artifact."""

    checked_payload = dict(payload)
    _validate_m434_safety_fields(checked_payload)
    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = (
        render_etf_sma_m434_offline_paper_buy_submit_approval_packet_json(
            checked_payload
        )
        + "\n"
    )
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaM434OfflinePaperBuySubmitApprovalPacketWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        paper_only=True,
        operator_approval_required=True,
        required_single_attempt_submit=True,
        submit_authorized=False,
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        broker_read_only=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _base_payload(
    config: EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": config.run_id,
        "milestone": _MILESTONE,
        "approval_scope": _APPROVAL_SCOPE,
        "source_m433_artifact": str(config.m433_review_path),
        "source_m433_readiness_decision": "",
        "source_next_required_milestone": "",
        "symbol": _SYMBOL,
        "side": _SIDE,
        "asset_class": _ASSET_CLASS,
        "intended_order_type": _INTENDED_ORDER_TYPE,
        "intended_time_in_force": _INTENDED_TIME_IN_FORCE,
        "paper_only": True,
        "operator_approval_required": True,
        "trade_recommendation": _TRADE_RECOMMENDATION,
        "profit_claim": _PROFIT_CLAIM,
        "approval_decision": _BLOCKED_APPROVAL_DECISION,
        "next_required_milestone": _BLOCKED_NEXT_MILESTONE,
        "required_fresh_pre_submit_checks": list(_REQUIRED_FRESH_PRE_SUBMIT_CHECKS),
        "required_submit_gates": list(_REQUIRED_SUBMIT_GATES),
        "required_duplicate_id_guard": list(_REQUIRED_DUPLICATE_ID_GUARD),
        "required_open_order_guard": list(_REQUIRED_OPEN_ORDER_GUARD),
        "required_position_guard": list(_REQUIRED_POSITION_GUARD),
        "required_redaction_check": list(_REQUIRED_REDACTION_CHECK),
        "required_single_attempt_submit": True,
        "blockers": [],
        "paper_lab_only": True,
        "not_live_authorized": True,
        "labels": [
            "paper_lab_only",
            "offline_paper_buy_submit_approval_packet",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "notes": [
            "M434 is offline-only and does not authorize or perform submit.",
            "A later submit milestone requires fresh broker-observed "
            "read-only pre-submit reconciliation inside an explicitly scoped "
            "operator-authorized paper shell.",
        ],
        "provenance_summary": "Consumes the M433 offline operator review packet.",
    }
    payload.update(_safety_false_payload())
    return payload


def _complete_payload(
    payload: dict[str, object],
    *,
    approval_decision: str,
    next_required_milestone: str,
    blockers: Sequence[str],
) -> dict[str, object]:
    payload.update(
        {
            "approval_decision": approval_decision,
            "next_required_milestone": next_required_milestone,
            "blockers": list(_dedupe(tuple(blockers))),
        }
    )
    payload.update(_safety_false_payload())
    _validate_m434_safety_fields(payload)
    return payload


def _source_m433_shape_blockers(record: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    if record.get("milestone") != "M433":
        blockers.append("source_m433_milestone_not_m433")
    if record.get("symbol") != _SYMBOL:
        blockers.append("source_m433_symbol_not_spy")
    if record.get("operator_approval_required") is not True:
        blockers.append("source_m433_operator_approval_required_not_true")
    if record.get("trade_recommendation") != _TRADE_RECOMMENDATION:
        blockers.append("source_m433_trade_recommendation_not_none")
    if record.get("profit_claim") != _PROFIT_CLAIM:
        blockers.append("source_m433_profit_claim_not_none")
    for field_name in _SOURCE_FALSE_FIELDS:
        if record.get(field_name) is not False:
            blockers.append(f"source_m433_{field_name}_not_false")
    return _dedupe(tuple(blockers))


def _load_single_jsonl_record(
    path: Path,
    artifact_name: str,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    if not path.exists():
        return None, (f"{artifact_name}_artifact_not_found",)
    if not path.is_file():
        return None, (f"{artifact_name}_artifact_path_not_file",)

    records: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, (f"{artifact_name}_artifact_unreadable",)

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            return None, (f"{artifact_name}_artifact_invalid_json_line_{line_number}",)
        if not isinstance(decoded, Mapping):
            return None, (f"{artifact_name}_artifact_record_{line_number}_not_object",)
        records.append(dict(decoded))

    if not records:
        return None, (f"{artifact_name}_artifact_empty",)
    if len(records) != 1:
        return None, (f"ambiguous_{artifact_name}_artifact_record_count",)
    return records[0], ()


def _config(
    value: object,
) -> EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig:
    if type(value) is not EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig:
        raise ValidationError(
            "config must be an "
            "EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig."
        )
    return value


def _jsonl_path(value: object, field_name: str) -> Path:
    path = _required_path(value, field_name)
    if type(value) is str and "://" in value:
        raise ValidationError(f"{field_name} must be a local JSONL path.")
    if path.suffix.lower() != ".jsonl":
        raise ValidationError(f"{field_name} must reference a JSONL file.")
    return path


def _output_path(value: object) -> Path:
    path = _jsonl_path(value, "output_path")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
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


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _safety_false_payload() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


def _validate_m434_safety_fields(payload: Mapping[str, object]) -> None:
    if payload.get("milestone") != _MILESTONE:
        raise ValidationError("milestone must be M434.")
    if payload.get("approval_scope") != _APPROVAL_SCOPE:
        raise ValidationError("approval_scope is unexpected.")
    if payload.get("symbol") != _SYMBOL:
        raise ValidationError("symbol must be SPY.")
    if payload.get("side") != _SIDE:
        raise ValidationError("side must be buy.")
    if payload.get("asset_class") != _ASSET_CLASS:
        raise ValidationError("asset_class must be equity.")
    if payload.get("intended_order_type") != _INTENDED_ORDER_TYPE:
        raise ValidationError("intended_order_type must be market.")
    if payload.get("intended_time_in_force") != _INTENDED_TIME_IN_FORCE:
        raise ValidationError("intended_time_in_force must be day.")
    if payload.get("paper_only") is not True:
        raise ValidationError("paper_only must be true.")
    if payload.get("operator_approval_required") is not True:
        raise ValidationError("operator_approval_required must be true.")
    if payload.get("required_single_attempt_submit") is not True:
        raise ValidationError("required_single_attempt_submit must be true.")
    for field_name in _SAFETY_FALSE_FIELDS:
        if payload.get(field_name) is not False:
            raise ValidationError(f"{field_name} must be false.")
    if payload.get("trade_recommendation") != _TRADE_RECOMMENDATION:
        raise ValidationError("trade_recommendation must be none.")
    if payload.get("profit_claim") != _PROFIT_CLAIM:
        raise ValidationError("profit_claim must be none.")


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _first_text(*values: object) -> str:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return ""


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_json_safe(item) for item in value]
    if type(value) is list:
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
