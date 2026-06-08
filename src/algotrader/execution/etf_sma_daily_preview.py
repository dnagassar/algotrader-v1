"""Offline daily preview for the SPY ETF/SMA paper lab.

This module consumes local JSONL reconciliation evidence and delegates ETF/SMA
cycle decisions to the offline cycle builder. It does not import broker SDKs,
load credentials, open sockets, or expose broker mutation behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from algotrader.core.types import Bar
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import load_local_daily_bars_csv

from .etf_sma_cycle import (
    EtfSmaCycleBrokerState,
    EtfSmaCycleConfig,
    build_etf_sma_cycle,
    build_etf_sma_cycle_from_offline_inputs,
    load_etf_sma_cycle_reconciliation_state,
)

__all__ = [
    "ETF_SMA_DAILY_PREVIEW_LABELS",
    "EtfSmaDailyPreviewConfig",
    "EtfSmaDailyPreviewWriteResult",
    "build_etf_sma_daily_preview",
    "render_etf_sma_daily_preview_json",
    "render_etf_sma_daily_preview_text",
    "write_etf_sma_daily_preview_jsonl",
]


ETF_SMA_DAILY_PREVIEW_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)

_MILESTONE = "M384 - Offline paper-lab daily preview entrypoint"
_RECORD_TYPE = "paper_lab_daily_preview"
_COMMAND = "paper-lab-daily-preview"
_DEFAULT_SYMBOL = "SPY"
_PROFIT_CLAIM = "none"
_INVALID_RECONCILIATION_BLOCKER = "missing_or_invalid_order_reconciliation"
_AMBIGUOUS_RECONCILIATION_DECISIONS = {
    "broker_unavailable",
    "m376_ambiguous",
    "m376_not_found",
}
_RECONCILIATION_FINGERPRINT_FIELDS = (
    "symbol",
    "client_order_id",
    "broker_order_id",
    "expected_side",
    "expected_qty",
    "observed_status",
    "observed_side",
    "observed_qty",
    "observed_filled_qty",
    "observed_remaining_qty",
    "terminal_state",
    "terminal_reason",
    "reconciliation_decision",
    "next_spy_submit_blocked",
    "spy_position_qty",
    "open_order_count",
    "open_order_symbols",
    "open_order_client_order_ids",
    "open_order_broker_order_ids",
    "open_order_statuses",
    "open_order_sides",
    "open_order_quantities",
    "open_order_filled_quantities",
    "non_spy_positions",
    "blockers",
)


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPreviewConfig:
    """Explicit local inputs for one offline paper-lab daily preview."""

    run_id: str
    order_reconciliation_log: Path | str
    symbol: str = _DEFAULT_SYMBOL
    generated_at: datetime | str | None = None
    daily_bars_csv: Path | str | None = None
    market_data_csv: Path | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        object.__setattr__(
            self,
            "generated_at",
            _generated_at_text(self.generated_at),
        )
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
            "daily_bars_csv",
            _optional_path(self.daily_bars_csv, "daily_bars_csv"),
        )
        object.__setattr__(
            self,
            "market_data_csv",
            _optional_path(self.market_data_csv, "market_data_csv"),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPreviewWriteResult:
    """Local JSONL write metadata for a single daily preview record."""

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
        for field_name in (
            "submitted",
            "mutated",
            "broker_action_performed",
            "network_access_attempted",
            "credential_access_attempted",
            "live_authorized",
        ):
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
class _ReconciliationArtifact:
    path: Path
    found: bool
    parsed: bool
    valid: bool
    record_count: int
    latest_record: dict[str, object] | None
    error: str
    blockers: tuple[str, ...]

    def summary(self) -> dict[str, object]:
        latest = self.latest_record or {}
        return {
            "path": str(self.path),
            "found": self.found,
            "parsed": self.parsed,
            "valid": self.valid,
            "record_count": self.record_count,
            "latest_run_id": _text(latest.get("run_id")),
            "latest_reconciliation_decision": _text(
                latest.get("reconciliation_decision")
            ),
            "error": self.error,
            "blockers": list(self.blockers),
        }


def build_etf_sma_daily_preview(
    config: EtfSmaDailyPreviewConfig,
) -> dict[str, object]:
    """Build one operator-facing offline daily preview record."""

    checked_config = _config(config)
    artifact = _read_order_reconciliation_artifact(
        checked_config.order_reconciliation_log
    )
    cycle_payload = _build_cycle_payload(checked_config, artifact)
    latest_record = artifact.latest_record or {}
    sma_payload = _mapping(cycle_payload.get("sma"))
    market_data_payload = _mapping(cycle_payload.get("market_data"))
    cycle_blockers = list(_string_list(cycle_payload.get("blockers")))
    blockers = _daily_preview_blockers(
        artifact,
        latest_record,
        cycle_blockers,
        checked_config.symbol,
    )
    forbidden_actions = _next_forbidden_action(
        blockers,
        _string_list(cycle_payload.get("next_forbidden_action")),
    )
    m376_order = _m376_order_payload(artifact, latest_record)

    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": checked_config.run_id,
        "generated_at": checked_config.generated_at,
        "as_of": checked_config.generated_at,
        "symbol": checked_config.symbol,
        "labels": list(ETF_SMA_DAILY_PREVIEW_LABELS),
        "paper_lab_only": True,
        "not_live_authorized": True,
        "profit_claim": _PROFIT_CLAIM,
        "source_order_reconciliation_log": str(
            checked_config.order_reconciliation_log
        ),
        "source_order_reconciliation": artifact.summary(),
        "source_daily_bars_csv": _path_text(checked_config.daily_bars_csv),
        "source_market_data_csv": _path_text(checked_config.market_data_csv),
        "market_data_basis": _market_data_basis(checked_config),
        "market_data": _json_safe(market_data_payload),
        "bars_source": _text(cycle_payload.get("bars_source")),
        "bars_input_available": cycle_payload.get("bars_input_available") is True,
        "total_spy_bar_count": _optional_int(
            market_data_payload.get("total_bar_count")
        ),
        "usable_spy_bar_count": _optional_int(
            market_data_payload.get("usable_bar_count")
        ),
        "ignored_future_spy_bar_count": _optional_int(
            market_data_payload.get("ignored_future_bar_count")
        ),
        "sma_status": _text(cycle_payload.get("sma_status")),
        "sma_posture": _text(cycle_payload.get("sma_posture")),
        "sma": _json_safe(sma_payload),
        "sma50": _first_text(
            sma_payload.get("fast_sma"),
            sma_payload.get("short_sma"),
        ),
        "sma200": _first_text(
            sma_payload.get("slow_sma"),
            sma_payload.get("long_sma"),
        ),
        "sma_short_window": _optional_int(
            _first_present(
                sma_payload.get("fast_window"),
                sma_payload.get("short_window"),
            )
        ),
        "sma_long_window": _optional_int(
            _first_present(
                sma_payload.get("slow_window"),
                sma_payload.get("long_window"),
            )
        ),
        "sma_required_bars": _optional_int(sma_payload.get("required_bars")),
        "latest_close": _first_text(sma_payload.get("latest_close")),
        "m376_order_summary": m376_order,
        "m376_client_order_id": m376_order["client_order_id"],
        "m376_broker_order_id": m376_order["broker_order_id"],
        "m376_terminal_state": m376_order["terminal_state"],
        "m376_terminal_reason": m376_order["terminal_reason"],
        "open_order_present": _open_order_present(
            latest_record,
            cycle_payload,
            checked_config.symbol,
        ),
        "open_order_count": _optional_int(
            _first_present(
                cycle_payload.get("open_order_count"),
                latest_record.get("open_order_count"),
                m376_order.get("open_order_count"),
            )
        ),
        "open_spy_order_present": _open_spy_order_present(
            latest_record,
            cycle_payload,
            checked_config.symbol,
        ),
        "non_spy_position_present": _non_spy_position_present(
            latest_record,
            checked_config.symbol,
            cycle_payload,
        ),
        "spy_position_qty": _first_text(
            cycle_payload.get("spy_position_quantity"),
            latest_record.get("spy_position_qty"),
            m376_order.get("spy_position_qty"),
        ),
        "daily_preview_status": _daily_preview_status(blockers),
        "blockers": blockers,
        "cycle_decision": _text(cycle_payload.get("decision")),
        "cycle_decision_reason": _text(cycle_payload.get("decision_reason")),
        "cycle_blockers": list(_dedupe(tuple(cycle_blockers))),
        "cycle_next_allowed_action": _text(
            cycle_payload.get("next_allowed_action")
        ),
        "preview_order": _json_safe(cycle_payload.get("preview_order")),
        "next_allowed_action": _next_allowed_action(blockers, cycle_payload),
        "next_forbidden_action": forbidden_actions,
        "preview_order_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def render_etf_sma_daily_preview_json(payload: Mapping[str, object]) -> str:
    """Render one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_daily_preview_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-facing daily preview summary."""

    return "\n".join(
        (
            "SPY ETF/SMA paper-lab daily preview",
            f"run_id: {payload.get('run_id', '')}",
            f"generated_at: {payload.get('generated_at', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"daily_preview_status: {payload.get('daily_preview_status', '')}",
            f"sma_status: {payload.get('sma_status', '')}",
            f"sma_posture: {payload.get('sma_posture', '')}",
            f"sma50: {payload.get('sma50', '')}",
            f"sma200: {payload.get('sma200', '')}",
            f"usable_spy_bar_count: {payload.get('usable_spy_bar_count', '')}",
            f"cycle_decision: {payload.get('cycle_decision', '')}",
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


def write_etf_sma_daily_preview_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> EtfSmaDailyPreviewWriteResult:
    """Write exactly one JSONL record, replacing any prior local artifact."""

    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_daily_preview_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
    return EtfSmaDailyPreviewWriteResult(
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


def _build_cycle_payload(
    config: EtfSmaDailyPreviewConfig,
    artifact: _ReconciliationArtifact,
) -> dict[str, object]:
    if artifact.valid:
        try:
            if config.daily_bars_csv is not None:
                return _build_cycle_payload_from_daily_bars(config)
            return build_etf_sma_cycle_from_offline_inputs(
                EtfSmaCycleConfig(
                    run_id=config.run_id,
                    symbol=config.symbol,
                    milestone=_MILESTONE,
                    as_of=config.generated_at,
                    market_data_csv=config.market_data_csv,
                    order_reconciliation_log=config.order_reconciliation_log,
                )
            )
        except ValidationError:
            pass

    invalid_state = EtfSmaCycleBrokerState(
        source=str(config.order_reconciliation_log),
        positions_observation_available=False,
        orders_observation_available=False,
        source_blockers=(_INVALID_RECONCILIATION_BLOCKER,),
    )
    return build_etf_sma_cycle(
        (),
        invalid_state,
        EtfSmaCycleConfig(
            run_id=config.run_id,
            symbol=config.symbol,
            milestone=_MILESTONE,
            as_of=config.generated_at,
            bars_source=str(config.market_data_csv or ""),
            bars_input_available=False,
        ),
    )


def _build_cycle_payload_from_daily_bars(
    config: EtfSmaDailyPreviewConfig,
) -> dict[str, object]:
    if config.daily_bars_csv is None:
        raise ValidationError("daily_bars_csv is required.")
    bars_result = load_local_daily_bars_csv(
        config.daily_bars_csv,
        symbol=config.symbol,
        as_of=config.generated_at,
    )
    bars = tuple(_adjusted_close_bar(bar) for bar in bars_result.bars)
    broker_state = load_etf_sma_cycle_reconciliation_state(
        config.order_reconciliation_log,
        symbol=config.symbol,
    )
    return build_etf_sma_cycle(
        bars,
        broker_state,
        EtfSmaCycleConfig(
            run_id=config.run_id,
            symbol=config.symbol,
            milestone=_MILESTONE,
            as_of=config.generated_at,
            bars_source=str(config.daily_bars_csv),
            bars_input_available=True,
        ),
    )


def _adjusted_close_bar(value: object) -> Bar:
    adjusted_close = value.adjusted_close
    return Bar(
        symbol=value.symbol,
        timestamp=datetime.combine(value.date, time.min, tzinfo=UTC),
        open=adjusted_close,
        high=adjusted_close,
        low=adjusted_close,
        close=adjusted_close,
        volume=Decimal(value.volume),
    )


def _read_order_reconciliation_artifact(path: Path) -> _ReconciliationArtifact:
    if not path.exists():
        return _invalid_artifact(path, "path_not_found")
    if not path.is_file():
        return _invalid_artifact(path, "path_not_file", found=True)

    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return _invalid_artifact(
                path,
                f"invalid_jsonl_line_{line_number}",
                found=True,
                parsed=False,
                record_count=len(records),
            )
        if not isinstance(payload, Mapping):
            return _invalid_artifact(
                path,
                f"jsonl_record_{line_number}_not_object",
                found=True,
                parsed=False,
                record_count=len(records),
            )
        records.append(dict(payload))

    if not records:
        return _invalid_artifact(path, "empty_jsonl", found=True)

    latest = records[-1]
    if _records_conflict(records):
        return _invalid_artifact(
            path,
            "multiple_conflicting_records",
            found=True,
            parsed=True,
            record_count=len(records),
            latest_record=latest,
            extra_blockers=("multiple_conflicting_order_reconciliation_records",),
        )
    if _ambiguous_or_invalid_reconciliation(latest):
        return _invalid_artifact(
            path,
            "ambiguous_order_reconciliation",
            found=True,
            parsed=True,
            record_count=len(records),
            latest_record=latest,
        )

    return _ReconciliationArtifact(
        path=path,
        found=True,
        parsed=True,
        valid=True,
        record_count=len(records),
        latest_record=latest,
        error="",
        blockers=(),
    )


def _invalid_artifact(
    path: Path,
    error: str,
    *,
    found: bool = False,
    parsed: bool = False,
    record_count: int = 0,
    latest_record: dict[str, object] | None = None,
    extra_blockers: tuple[str, ...] = (),
) -> _ReconciliationArtifact:
    return _ReconciliationArtifact(
        path=path,
        found=found,
        parsed=parsed,
        valid=False,
        record_count=record_count,
        latest_record=latest_record,
        error=error,
        blockers=_dedupe((_INVALID_RECONCILIATION_BLOCKER, *extra_blockers)),
    )


def _records_conflict(records: list[dict[str, object]]) -> bool:
    if len(records) <= 1:
        return False
    fingerprints = {_record_fingerprint(record) for record in records}
    return len(fingerprints) > 1


def _record_fingerprint(record: Mapping[str, object]) -> str:
    payload = {
        field_name: _json_safe(record.get(field_name))
        for field_name in _RECONCILIATION_FINGERPRINT_FIELDS
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _ambiguous_or_invalid_reconciliation(record: Mapping[str, object]) -> bool:
    decision = _text(record.get("reconciliation_decision"))
    terminal_state = _text(record.get("terminal_state"))
    blockers = _string_list(record.get("blockers"))
    if decision in _AMBIGUOUS_RECONCILIATION_DECISIONS:
        return True
    if terminal_state not in {"terminal", "nonterminal"}:
        return True
    return bool(
        {
            "multiple_conflicting_matches",
            "order_state_ambiguous",
        }.intersection(blockers)
    )


def _daily_preview_blockers(
    artifact: _ReconciliationArtifact,
    record: Mapping[str, object],
    cycle_blockers: list[str],
    symbol: str,
) -> list[str]:
    blockers = [*cycle_blockers, *artifact.blockers]
    if _non_spy_position_present(record, symbol, {}):
        blockers.append("unexpected_non_spy_position")
    return list(_dedupe(tuple(blockers)))


def _m376_order_payload(
    artifact: _ReconciliationArtifact,
    record: Mapping[str, object],
) -> dict[str, object]:
    return {
        "source_supplied": True,
        "source_found": artifact.found,
        "source_parsed": artifact.parsed,
        "source_valid": artifact.valid,
        "source_error": artifact.error,
        "run_id": _text(record.get("run_id")),
        "symbol": _text(record.get("symbol")),
        "client_order_id": _text(record.get("client_order_id")),
        "broker_order_id": _text(record.get("broker_order_id")),
        "observed_status": _text(record.get("observed_status")),
        "observed_side": _text(record.get("observed_side")),
        "observed_qty": _text(record.get("observed_qty")),
        "observed_filled_qty": _text(record.get("observed_filled_qty")),
        "spy_position_qty": _text(record.get("spy_position_qty")),
        "open_order_count": _optional_int(record.get("open_order_count")),
        "terminal_state": _text(record.get("terminal_state")),
        "terminal_reason": _text(record.get("terminal_reason")),
        "reconciliation_decision": _text(record.get("reconciliation_decision")),
        "blockers": list(_string_list(record.get("blockers"))),
        "next_spy_submit_blocked": _bool_or(
            record.get("next_spy_submit_blocked"),
            bool(artifact.blockers),
        ),
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
    }


def _daily_preview_status(blockers: list[str]) -> str:
    return "blocked" if blockers else "review_only"


def _next_allowed_action(
    blockers: list[str],
    cycle_payload: Mapping[str, object],
) -> str:
    if _INVALID_RECONCILIATION_BLOCKER in blockers:
        return "read_only_reconciliation_before_any_spy_submit"
    if "unexpected_non_spy_position" in blockers:
        return "offline_work_or_read_only_reconciliation"
    cycle_action = _text(cycle_payload.get("next_allowed_action"))
    return cycle_action or "offline_research_or_operator_review_only"


def _next_forbidden_action(
    blockers: list[str],
    cycle_forbidden_actions: tuple[str, ...],
) -> list[str]:
    actions = [
        "broker_mutation_from_daily_preview",
        "live_trading",
        "submit_cancel_replace_close_liquidate_from_daily_preview",
        *cycle_forbidden_actions,
    ]
    if _INVALID_RECONCILIATION_BLOCKER in blockers:
        actions.extend(
            (
                "spy_submit_until_order_state_known",
                "spy_submit_before_read_only_reconciliation",
            )
        )
    if (
        "m376_order_nonterminal" in blockers
        or "open_order_present" in blockers
    ):
        actions.append("spy_submit_until_m376_terminal")
    if "unexpected_non_spy_position" in blockers:
        actions.append("non_spy_action")
    return list(_dedupe(tuple(actions)))


def _open_order_present(
    record: Mapping[str, object],
    cycle_payload: Mapping[str, object],
    symbol: str,
) -> bool:
    if _open_spy_order_present(record, cycle_payload, symbol):
        return True
    count = _optional_int(record.get("open_order_count"))
    if count is not None and count > 0:
        return True
    cycle_count = _optional_int(cycle_payload.get("open_order_count"))
    return cycle_count is not None and cycle_count > 0


def _open_spy_order_present(
    record: Mapping[str, object],
    cycle_payload: Mapping[str, object],
    symbol: str,
) -> bool:
    checked_symbol = symbol_value(symbol)
    spy_count = _optional_int(record.get("spy_open_order_count"))
    if spy_count is not None and spy_count > 0:
        return True
    for value in (
        record.get("open_order_symbols"),
        cycle_payload.get("open_order_symbols"),
    ):
        symbols = _string_list(value)
        if checked_symbol in symbols:
            return True
    return False


def _non_spy_position_present(
    record: Mapping[str, object],
    symbol: str,
    cycle_payload: Mapping[str, object],
) -> bool:
    checked_symbol = symbol_value(symbol)
    if record.get("unexpected_non_spy_position_present") is True:
        return True
    non_spy_positions = record.get("non_spy_positions")
    if isinstance(non_spy_positions, Sequence) and not isinstance(
        non_spy_positions,
        (str, bytes),
    ):
        for item in non_spy_positions:
            if isinstance(item, Mapping):
                item_symbol = _text(item.get("symbol")).upper()
                quantity = _optional_decimal(item.get("quantity"))
                if (
                    item_symbol
                    and item_symbol != checked_symbol
                    and (quantity is None or quantity > Decimal("0"))
                ):
                    return True
            else:
                item_symbol = _text(item).upper()
                if item_symbol and item_symbol != checked_symbol:
                    return True
    position_symbols = _string_list(cycle_payload.get("position_symbols"))
    return any(symbol_text != checked_symbol for symbol_text in position_symbols)


def _config(value: object) -> EtfSmaDailyPreviewConfig:
    if type(value) is not EtfSmaDailyPreviewConfig:
        raise ValidationError("config must be an EtfSmaDailyPreviewConfig.")
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


def _bool_or(value: object, default: bool) -> bool:
    return value if type(value) is bool else default


def _optional_int(value: object) -> int | None:
    if type(value) is int:
        return value
    if type(value) is str and value.isdigit():
        return int(value)
    return None


def _first_present(*values: object) -> object:
    for value in values:
        if value is not None:
            return value
    return None


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal = Decimal(str(value))
    except Exception:
        return None
    if not decimal.is_finite():
        return None
    return decimal


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _first_text(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _path_text(value: object) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def _market_data_basis(config: EtfSmaDailyPreviewConfig) -> str:
    if config.daily_bars_csv is not None:
        return "adjusted_close"
    if config.market_data_csv is not None:
        return "close"
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
    if isinstance(value, Decimal):
        return str(value)
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
