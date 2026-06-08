"""Offline M431 authorized ETF/SMA paper-lab cycle preview.

This module consumes the M430 authorized adjusted-close SMA posture snapshot and
local paper-state evidence only. It does not load profiles, inspect
credentials, import broker SDKs, open sockets, or expose broker mutation paths.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "DEFAULT_AUTHORIZED_ADJUSTED_CLOSE_SMA_POSTURE_SNAPSHOT_PATH",
    "DEFAULT_AUTHORIZED_OFFLINE_CYCLE_PREVIEW_PATH",
    "DEFAULT_OFFLINE_PAPER_STATE_PATH",
    "EtfSmaAuthorizedOfflineCyclePreviewConfig",
    "EtfSmaAuthorizedOfflineCyclePreviewWriteResult",
    "build_etf_sma_authorized_offline_cycle_preview",
    "render_etf_sma_authorized_offline_cycle_preview_json",
    "render_etf_sma_authorized_offline_cycle_preview_text",
    "write_etf_sma_authorized_offline_cycle_preview_jsonl",
]


DEFAULT_AUTHORIZED_ADJUSTED_CLOSE_SMA_POSTURE_SNAPSHOT_PATH = (
    Path("runs")
    / "paper_lab"
    / "m430_authorized_adjusted_close_sma_posture_snapshot.jsonl"
)
DEFAULT_OFFLINE_PAPER_STATE_PATH = (
    Path("runs") / "paper_lab" / "m389_offline_paper_lab_state_rollup.jsonl"
)
DEFAULT_AUTHORIZED_OFFLINE_CYCLE_PREVIEW_PATH = (
    Path("runs")
    / "paper_lab"
    / "m431_authorized_offline_paper_lab_cycle_preview.jsonl"
)


@dataclass(frozen=True, slots=True)
class EtfSmaAuthorizedOfflineCyclePreviewConfig:
    """Explicit local inputs for one M431 offline cycle preview."""

    run_id: str
    symbol: str = "SPY"
    posture_path: (
        str | Path
    ) = DEFAULT_AUTHORIZED_ADJUSTED_CLOSE_SMA_POSTURE_SNAPSHOT_PATH
    offline_paper_state_path: str | Path = DEFAULT_OFFLINE_PAPER_STATE_PATH

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "posture_path",
            _required_path(self.posture_path, "posture_path"),
        )
        object.__setattr__(
            self,
            "offline_paper_state_path",
            _required_path(
                self.offline_paper_state_path,
                "offline_paper_state_path",
            ),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaAuthorizedOfflineCyclePreviewWriteResult:
    """Local JSONL write metadata for a single M431 preview record."""

    output_path: Path
    record_count: int
    bytes_written: int
    newline_terminated: bool
    submitted: bool
    mutated: bool
    broker_action_performed: bool
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
            "submitted": self.submitted,
            "mutated": self.mutated,
            "broker_action_performed": self.broker_action_performed,
            "network_access_attempted": self.network_access_attempted,
            "credential_access_attempted": self.credential_access_attempted,
            "live_authorized": self.live_authorized,
        }


@dataclass(frozen=True, slots=True)
class _OfflinePaperState:
    open_order_count: int
    open_spy_order_count: int
    spy_position_present: bool
    spy_position_qty: str
    unexpected_position_symbols: tuple[str, ...]
    blockers: tuple[str, ...]
    source_blockers: tuple[str, ...]


_COMMAND = "etf-sma-authorized-offline-cycle-preview"
_RECORD_TYPE = "etf_sma_authorized_offline_cycle_preview"
_SCHEMA_VERSION = "1"
_MILESTONE = "M431"
_POSTURE_MILESTONE = "M430"
_SUCCESS_STATUS = "offline_cycle_preview_computed"
_BLOCKED_POSTURE_STATUS = "blocked_authorized_posture_required"
_BLOCKED_STATE_STATUS = "blocked_offline_paper_state_required"
_BLOCKED_OPEN_ORDER_STATUS = "blocked_open_order_present"
_BLOCKED_UNEXPECTED_POSITION_STATUS = "blocked_unexpected_position"
_POSTURE_SUCCESS_STATUS = "authorized_adjusted_close_sma_posture_computed"
_INPUT_REPLAY_STATUS = "authorized_adjusted_baseline_backtest_replayed"
_EXPECTED_SYMBOL = "SPY"
_PREFERRED_BASELINE = "adjusted_close_matched_window"
_PREFERRED_BASIS = "adjusted_close_price_return"
_COMPARISON_BASIS = "matched_window"
_STRATEGY_FAMILY = "etf_sma_50_200"
_POSTURE_RISK_ON = "risk_on"
_POSTURE_RISK_OFF = "risk_off"
_POSTURE_REQUIRED_STRING_FIELDS = (
    ("milestone", _POSTURE_MILESTONE),
    ("posture_snapshot_status", _POSTURE_SUCCESS_STATUS),
    ("input_replay_status", _INPUT_REPLAY_STATUS),
    ("active_preferred_baseline", _PREFERRED_BASELINE),
    ("active_preferred_basis", _PREFERRED_BASIS),
    ("comparison_basis", _COMPARISON_BASIS),
    ("strategy_family", _STRATEGY_FAMILY),
    ("data_basis", _PREFERRED_BASIS),
    ("baseline_source_milestone", "M422"),
    ("guard_source_milestone", "M423"),
    ("authorization_source_milestone", "M424"),
    ("stub_source_milestone", "M425"),
    ("summary_source_milestone", "M426"),
    ("metrics_source_milestone", "M427"),
    ("snapshot_source_milestone", "M428"),
    ("replay_source_milestone", "M429"),
    ("source_evidence_milestone", "M421"),
    ("trade_recommendation", "none"),
    ("profit_claim", "none"),
)
_POSTURE_REQUIRED_TRUE_FIELDS = (
    "downstream_comparison_authorized",
    "posture_computed",
    "sufficient_history",
)
_POSTURE_REQUIRED_FALSE_FIELDS = (
    "order_decision_computed",
    "paper_preview_computed",
    "broker_state_loaded",
    "new_market_data_loaded",
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_POSTURE_REQUIRED_PRESENT_FIELDS = (
    "as_of_date",
    "latest_available_bar_date",
    "sma50",
    "sma200",
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_STATE_OPTIONAL_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "broker_mutation_allowed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
    "preview_order_authorized",
)
_AMBIGUOUS_SOURCE_STATE_BLOCKERS = (
    "ambiguous_local_artifact_state",
    "conflicting_local_artifact_state",
    "missing_or_invalid_daily_preview",
    "missing_or_invalid_order_reconciliation",
    "order_state_unknown",
    "source_artifact_safety_flags_not_false",
)
_OPEN_ORDER_SOURCE_BLOCKERS = (
    "m376_order_nonterminal",
    "open_order_present",
)


def build_etf_sma_authorized_offline_cycle_preview(
    config: EtfSmaAuthorizedOfflineCyclePreviewConfig,
) -> dict[str, object]:
    """Build one deterministic local-only M431 cycle preview record."""

    checked_config = _config(config)
    payload = _base_payload(checked_config)

    posture_record, posture_blockers = _load_single_jsonl_record(
        checked_config.posture_path,
        "input_posture",
    )
    if posture_record is not None:
        posture_blockers = (
            *posture_blockers,
            *_validate_posture_record(posture_record, checked_config.symbol),
        )
    if posture_blockers:
        return _blocked_authorized_posture(payload, posture_record, posture_blockers)
    if posture_record is None:
        return _blocked_authorized_posture(
            payload,
            posture_record,
            ("input_posture_artifact_empty",),
        )

    _copy_posture_context(payload, posture_record)

    state_record, state_read_blockers = _load_single_jsonl_record(
        checked_config.offline_paper_state_path,
        "offline_paper_state",
    )
    if state_read_blockers or state_record is None:
        return _blocked_after_valid_posture(
            payload,
            status=_BLOCKED_STATE_STATUS,
            decision="blocked/offline_paper_state_required",
            blockers=state_read_blockers or ("offline_paper_state_artifact_empty",),
            offline_paper_state_loaded=False,
        )

    state = _offline_paper_state(state_record, checked_config.symbol)
    _copy_state_context(payload, state, checked_config.offline_paper_state_path)
    if state.blockers:
        return _blocked_after_valid_posture(
            payload,
            status=_BLOCKED_STATE_STATUS,
            decision="blocked/offline_paper_state_required",
            blockers=state.blockers,
            offline_paper_state_loaded=False,
        )

    if state.open_spy_order_count > 0:
        blockers = _dedupe(
            (
                "open_spy_order_present",
                *_matching_source_blockers(
                    state.source_blockers,
                    _OPEN_ORDER_SOURCE_BLOCKERS,
                ),
            )
        )
        return _blocked_after_valid_posture(
            payload,
            status=_BLOCKED_OPEN_ORDER_STATUS,
            decision="blocked/open_order_present",
            blockers=blockers,
            offline_paper_state_loaded=True,
        )

    if state.unexpected_position_symbols:
        return _blocked_after_valid_posture(
            payload,
            status=_BLOCKED_UNEXPECTED_POSITION_STATUS,
            decision="blocked/unexpected_position",
            blockers=("unexpected_position_symbols_present",),
            offline_paper_state_loaded=True,
        )

    payload.update(
        {
            "cycle_preview_status": _SUCCESS_STATUS,
            "cycle_decision": _cycle_decision(
                _text(posture_record["sma_posture"]),
                state.spy_position_present,
            ),
            "paper_preview_computed": True,
            "offline_paper_state_loaded": True,
            "blockers": [],
        }
    )
    payload.update(_safety_false_payload())
    return payload


def render_etf_sma_authorized_offline_cycle_preview_json(
    payload: Mapping[str, object],
) -> str:
    """Render one newline-free deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_authorized_offline_cycle_preview_text(
    payload: Mapping[str, object],
) -> str:
    """Render a compact operator-facing M431 preview summary."""

    return "\n".join(
        (
            "ETF/SMA authorized offline cycle preview",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"cycle_preview_status: {payload.get('cycle_preview_status', '')}",
            f"sma_posture: {payload.get('sma_posture', '')}",
            f"offline_paper_state_loaded: "
            f"{_bool_text(payload.get('offline_paper_state_loaded'))}",
            f"open_order_count: {payload.get('open_order_count', '')}",
            f"open_spy_order_count: {payload.get('open_spy_order_count', '')}",
            f"spy_position_present: "
            f"{_bool_text(payload.get('spy_position_present'))}",
            f"spy_position_qty: {payload.get('spy_position_qty', '')}",
            "unexpected_position_symbols: "
            f"{_joined(_string_list(payload.get('unexpected_position_symbols')))}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
            f"paper_preview_computed: "
            f"{_bool_text(payload.get('paper_preview_computed'))}",
            f"blockers: {_joined(_string_list(payload.get('blockers')))}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
            f"live_authorized: {_bool_text(payload.get('live_authorized'))}",
            f"trade_recommendation: {payload.get('trade_recommendation', '')}",
            f"profit_claim: {payload.get('profit_claim', '')}",
        )
    )


def write_etf_sma_authorized_offline_cycle_preview_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaAuthorizedOfflineCyclePreviewWriteResult:
    """Write exactly one JSONL record, replacing any prior local artifact."""

    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_authorized_offline_cycle_preview_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaAuthorizedOfflineCyclePreviewWriteResult(
        output_path=path,
        record_count=1,
        bytes_written=len(line.encode("utf-8")),
        newline_terminated=line.endswith("\n"),
        submitted=False,
        mutated=False,
        broker_action_performed=False,
        network_access_attempted=False,
        credential_access_attempted=False,
        live_authorized=False,
    )


def _base_payload(
    config: EtfSmaAuthorizedOfflineCyclePreviewConfig,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "input_posture_path": str(config.posture_path),
        "offline_paper_state_path": str(config.offline_paper_state_path),
        "cycle_preview_status": _BLOCKED_POSTURE_STATUS,
        "input_posture_status": "",
        "downstream_comparison_authorized": False,
        "broker_state_loaded": False,
        "offline_paper_state_loaded": False,
        "open_order_count": None,
        "open_spy_order_count": None,
        "spy_position_present": False,
        "spy_position_qty": "",
        "unexpected_position_symbols": [],
        "cycle_decision": "blocked/authorized_posture_required",
        "paper_preview_computed": False,
        "order_quantity_computed": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "submitted": False,
        "mutated": False,
        "trade_recommendation": "none",
        "profit_claim": "none",
        "paper_lab_only": True,
        "not_live_authorized": True,
        "blockers": [],
    }
    payload.update(_safety_false_payload())
    return payload


def _blocked_authorized_posture(
    payload: dict[str, object],
    posture_record: Mapping[str, object] | None,
    blockers: Sequence[str],
) -> dict[str, object]:
    if posture_record is not None:
        payload["input_posture_status"] = _text(
            posture_record.get("posture_snapshot_status")
        )
    payload.update(
        {
            "cycle_preview_status": _BLOCKED_POSTURE_STATUS,
            "cycle_decision": "blocked/authorized_posture_required",
            "downstream_comparison_authorized": False,
            "paper_preview_computed": False,
            "offline_paper_state_loaded": False,
            "blockers": list(_dedupe(tuple(blockers))),
        }
    )
    payload.update(_safety_false_payload())
    return payload


def _blocked_after_valid_posture(
    payload: dict[str, object],
    *,
    status: str,
    decision: str,
    blockers: Sequence[str],
    offline_paper_state_loaded: bool,
) -> dict[str, object]:
    payload.update(
        {
            "cycle_preview_status": status,
            "cycle_decision": decision,
            "downstream_comparison_authorized": True,
            "paper_preview_computed": False,
            "offline_paper_state_loaded": offline_paper_state_loaded,
            "blockers": list(_dedupe(tuple(blockers))),
        }
    )
    payload.update(_safety_false_payload())
    return payload


def _copy_posture_context(
    payload: dict[str, object],
    posture_record: Mapping[str, object],
) -> None:
    copied_fields = (
        ("input_posture_status", "posture_snapshot_status"),
        ("posture_source_milestone", "milestone"),
        ("replay_source_milestone", "replay_source_milestone"),
        ("snapshot_source_milestone", "snapshot_source_milestone"),
        ("metrics_source_milestone", "metrics_source_milestone"),
        ("summary_source_milestone", "summary_source_milestone"),
        ("stub_source_milestone", "stub_source_milestone"),
        ("authorization_source_milestone", "authorization_source_milestone"),
        ("guard_source_milestone", "guard_source_milestone"),
        ("baseline_source_milestone", "baseline_source_milestone"),
        ("source_evidence_milestone", "source_evidence_milestone"),
        ("strategy_family", "strategy_family"),
        ("data_basis", "data_basis"),
        ("as_of_date", "as_of_date"),
        ("latest_available_bar_date", "latest_available_bar_date"),
        ("sma50", "sma50"),
        ("sma200", "sma200"),
        ("sma_posture", "sma_posture"),
        ("sufficient_history", "sufficient_history"),
    )
    for output_field, source_field in copied_fields:
        payload[output_field] = posture_record[source_field]
    payload["downstream_comparison_authorized"] = True


def _copy_state_context(
    payload: dict[str, object],
    state: _OfflinePaperState,
    source_path: Path,
) -> None:
    payload.update(
        {
            "offline_paper_state_loaded": not state.blockers,
            "offline_paper_state_source": str(source_path),
            "open_order_count": state.open_order_count,
            "open_spy_order_count": state.open_spy_order_count,
            "spy_position_present": state.spy_position_present,
            "spy_position_qty": state.spy_position_qty,
            "unexpected_position_symbols": list(state.unexpected_position_symbols),
        }
    )


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
            return None, (
                f"{artifact_name}_artifact_invalid_json_line_{line_number}",
            )
        if not isinstance(decoded, Mapping):
            return None, (
                f"{artifact_name}_artifact_record_{line_number}_not_object",
            )
        records.append(dict(decoded))

    if not records:
        return None, (f"{artifact_name}_artifact_empty",)
    if len(records) != 1:
        return None, (f"ambiguous_{artifact_name}_artifact_record_count",)
    return records[0], ()


def _validate_posture_record(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    symbol_blocker = _validate_expected_string_field(
        record,
        "symbol",
        symbol,
        "input_posture",
    )
    if symbol_blocker is not None:
        blockers.append(symbol_blocker)

    for field_name, expected in _POSTURE_REQUIRED_STRING_FIELDS:
        blocker = _validate_expected_string_field(
            record,
            field_name,
            expected,
            "input_posture",
        )
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _POSTURE_REQUIRED_TRUE_FIELDS:
        blocker = _validate_required_true_field(record, field_name, "input_posture")
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _POSTURE_REQUIRED_FALSE_FIELDS:
        blocker = _validate_required_false_field(record, field_name, "input_posture")
        if blocker is not None:
            blockers.append(blocker)

    for field_name in _POSTURE_REQUIRED_PRESENT_FIELDS:
        if field_name not in record or record[field_name] in ("", None):
            blockers.append(f"input_posture_missing_{field_name}")

    sma_posture = record.get("sma_posture")
    if sma_posture not in (_POSTURE_RISK_ON, _POSTURE_RISK_OFF):
        blockers.append("input_posture_unexpected_sma_posture")

    return tuple(blockers)


def _offline_paper_state(
    record: Mapping[str, object],
    symbol: str,
) -> _OfflinePaperState:
    checked_symbol = symbol_value(symbol)
    blockers: list[str] = []
    source_blockers = _string_list(record.get("blockers"))
    for blocker in source_blockers:
        if blocker in _AMBIGUOUS_SOURCE_STATE_BLOCKERS:
            blockers.append(f"offline_paper_state_{blocker}")

    if record.get("symbol") not in (None, "", checked_symbol):
        blockers.append("offline_paper_state_unexpected_symbol")

    for field_name in _STATE_OPTIONAL_FALSE_FIELDS:
        if field_name in record and record[field_name] is not False:
            blockers.append(f"offline_paper_state_{field_name}_not_false")

    if "profit_claim" in record and record["profit_claim"] != "none":
        blockers.append("offline_paper_state_unexpected_profit_claim")

    open_order_count = _open_order_count(record, blockers)
    open_spy_order_count = _open_spy_order_count(
        record,
        checked_symbol,
        open_order_count,
        blockers,
    )
    spy_position_qty = _spy_position_qty(record, checked_symbol, blockers)
    spy_position_present = _spy_position_present(record, spy_position_qty, blockers)
    unexpected_symbols = _unexpected_position_symbols(record, checked_symbol)

    return _OfflinePaperState(
        open_order_count=open_order_count or 0,
        open_spy_order_count=open_spy_order_count or 0,
        spy_position_present=spy_position_present,
        spy_position_qty=spy_position_qty,
        unexpected_position_symbols=unexpected_symbols,
        blockers=_dedupe(tuple(blockers)),
        source_blockers=source_blockers,
    )


def _open_order_count(
    record: Mapping[str, object],
    blockers: list[str],
) -> int | None:
    count = _optional_non_negative_int(record.get("open_order_count"))
    present = record.get("open_order_present")
    if count is not None:
        if present is False and count > 0:
            blockers.append("offline_paper_state_conflicting_open_order_evidence")
        if present is True and count == 0:
            blockers.append("offline_paper_state_conflicting_open_order_evidence")
        return count

    if present is False:
        return 0
    if present is True:
        symbols = _string_list(record.get("open_order_symbols"))
        if symbols:
            return len(symbols)
        blockers.append("offline_paper_state_missing_open_order_count")
        return None

    blockers.append("offline_paper_state_missing_open_order_evidence")
    return None


def _open_spy_order_count(
    record: Mapping[str, object],
    symbol: str,
    open_order_count: int | None,
    blockers: list[str],
) -> int | None:
    count = _first_optional_non_negative_int(
        record.get("open_spy_order_count"),
        record.get("spy_open_order_count"),
    )
    present = record.get("open_spy_order_present")
    if count is not None:
        if present is False and count > 0:
            blockers.append("offline_paper_state_conflicting_spy_order_evidence")
        if present is True and count == 0:
            blockers.append("offline_paper_state_conflicting_spy_order_evidence")
        return count

    if present is True:
        return 1
    if present is False:
        return 0

    symbols = tuple(item.upper() for item in _string_list(record.get("open_order_symbols")))
    if symbols:
        return sum(1 for item in symbols if item == symbol)
    if open_order_count == 0:
        return 0
    if open_order_count is not None and open_order_count > 0:
        blockers.append("offline_paper_state_missing_open_spy_order_evidence")
        return None

    blockers.append("offline_paper_state_missing_open_spy_order_evidence")
    return None


def _spy_position_qty(
    record: Mapping[str, object],
    symbol: str,
    blockers: list[str],
) -> str:
    if "spy_position_qty" in record:
        value = record.get("spy_position_qty")
        if value in (None, ""):
            return ""
        text = _text(value)
        if _decimal_or_none(text) is None:
            blockers.append("offline_paper_state_malformed_spy_position_qty")
        return text

    positions = _positions(record.get("positions"))
    for position in positions:
        if _text(position.get("symbol")).upper() == symbol:
            qty = _text(position.get("qty") or position.get("quantity"))
            if qty and _decimal_or_none(qty) is None:
                blockers.append("offline_paper_state_malformed_spy_position_qty")
            return qty

    if "spy_position_present" in record and record["spy_position_present"] is False:
        return ""
    if "spy_position_present" in record and record["spy_position_present"] is True:
        return ""

    blockers.append("offline_paper_state_missing_position_evidence")
    return ""


def _spy_position_present(
    record: Mapping[str, object],
    spy_position_qty: str,
    blockers: list[str],
) -> bool:
    qty_present = _quantity_present(spy_position_qty)
    present = record.get("spy_position_present")
    if present is True:
        if spy_position_qty and not qty_present:
            blockers.append("offline_paper_state_conflicting_spy_position_evidence")
        return True
    if present is False:
        if qty_present:
            blockers.append("offline_paper_state_conflicting_spy_position_evidence")
        return False
    return qty_present


def _unexpected_position_symbols(
    record: Mapping[str, object],
    symbol: str,
) -> tuple[str, ...]:
    symbols: list[str] = []
    for value in _string_list(record.get("unexpected_position_symbols")):
        _append_unexpected_symbol(symbols, value, symbol)
    for item in _position_items(record.get("non_spy_positions")):
        _append_unexpected_symbol(symbols, _position_symbol(item), symbol)
    for item in _position_items(record.get("positions")):
        item_symbol = _position_symbol(item)
        if item_symbol != symbol and _position_quantity_present(item):
            _append_unexpected_symbol(symbols, item_symbol, symbol)
    if (
        record.get("non_spy_position_present") is True
        or record.get("unexpected_non_spy_position_present") is True
    ) and not symbols:
        symbols.append("UNKNOWN")
    return _dedupe(tuple(symbols))


def _cycle_decision(sma_posture: str, spy_position_present: bool) -> str:
    if sma_posture == _POSTURE_RISK_ON:
        return "hold/noop" if spy_position_present else "buy_preview"
    if sma_posture == _POSTURE_RISK_OFF:
        return "sell_preview" if spy_position_present else "hold/noop"
    return "blocked/authorized_posture_required"


def _validate_expected_string_field(
    record: Mapping[str, object],
    field_name: str,
    expected: str,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if type(value) is not str:
        return f"{prefix}_malformed_{field_name}"
    if value != expected:
        return f"{prefix}_unexpected_{field_name}"
    return None


def _validate_required_true_field(
    record: Mapping[str, object],
    field_name: str,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if value is not True and value is not False:
        return f"{prefix}_malformed_{field_name}"
    if value is not True:
        return f"{prefix}_{field_name}_not_true"
    return None


def _validate_required_false_field(
    record: Mapping[str, object],
    field_name: str,
    prefix: str,
) -> str | None:
    if field_name not in record:
        return f"{prefix}_missing_{field_name}"
    value = record[field_name]
    if value is not True and value is not False:
        return f"{prefix}_malformed_{field_name}"
    if value is not False:
        return f"{prefix}_{field_name}_not_false"
    return None


def _config(value: object) -> EtfSmaAuthorizedOfflineCyclePreviewConfig:
    if type(value) is not EtfSmaAuthorizedOfflineCyclePreviewConfig:
        raise ValidationError(
            "config must be an EtfSmaAuthorizedOfflineCyclePreviewConfig."
        )
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
    if "://" in str(path):
        raise ValidationError(f"{field_name} must be a local path.")
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


def _true_bool(value: object, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be true.")
    return True


def _false_bool(value: object, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be false.")
    return False


def _first_optional_non_negative_int(*values: object) -> int | None:
    for value in values:
        integer = _optional_non_negative_int(value)
        if integer is not None:
            return integer
    return None


def _optional_non_negative_int(value: object) -> int | None:
    if type(value) is int and value >= 0:
        return value
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _quantity_present(value: str) -> bool:
    decimal = _decimal_or_none(value)
    return decimal is not None and decimal != Decimal("0")


def _decimal_or_none(value: str) -> Decimal | None:
    if value == "":
        return Decimal("0")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _positions(value: object) -> tuple[Mapping[str, object], ...]:
    return tuple(
        item
        for item in _position_items(value)
        if isinstance(item, Mapping)
    )


def _position_items(value: object) -> tuple[object, ...]:
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return tuple(value)
    return ()


def _position_symbol(value: object) -> str:
    if isinstance(value, Mapping):
        return _text(value.get("symbol")).upper()
    return _text(value).upper()


def _position_quantity_present(value: object) -> bool:
    if not isinstance(value, Mapping):
        return True
    qty = _text(value.get("qty") or value.get("quantity"))
    return _quantity_present(qty)


def _append_unexpected_symbol(
    symbols: list[str],
    value: str,
    expected_symbol: str,
) -> None:
    candidate = value.upper()
    if candidate and candidate != expected_symbol:
        symbols.append(candidate)


def _matching_source_blockers(
    source_blockers: tuple[str, ...],
    expected: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(blocker for blocker in source_blockers if blocker in expected)


def _safety_false_payload() -> dict[str, bool]:
    return {field_name: False for field_name in _SAFETY_FALSE_FIELDS}


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
    if isinstance(value, Path):
        return str(value)
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _joined(values: tuple[str, ...]) -> str:
    return ",".join(values) if values else "none"
