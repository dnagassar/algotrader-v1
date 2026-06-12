"""Assistant v1 daily ETF/SMA paper-lab command center.

This module is completely offline, deterministic, credential-free,
network-free, and broker-free. It generates the first operator-facing daily
assistant packet for the controlled SPY SMA 50/200 paper-lab strategy.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)

__all__ = [
    "EtfSmaDailyPaperLabConfig",
    "run_etf_sma_daily_paper_lab",
    "build_etf_sma_daily_paper_lab",
]

_DEFAULT_SYMBOL = "SPY"
_DEFAULT_BARS_CSV = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
_STRATEGY_NAME = "SPY daily long-only ETF SMA 50/200 trend filter"
_SCHEMA_VERSION = "1"
_ASSISTANT_VERSION = "assistant_v1"
_PACKET_TYPE = "daily_trading_research_command_center"
_COMMAND = "etf-sma-daily-paper-lab"
_SCRIPT = "scripts/run_daily_paper_lab.ps1"
_BRIEF_FILENAME = "operating_brief.md"
_RECORD_FILENAME = "operating_record.jsonl"
_MANIFEST_FILENAME = "manifest.jsonl"
_REQUIRED_LABELS = [
    "paper_lab_only",
    "signal_evaluation_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "offline_only",
    "broker_state_not_observed",
    "paper_submit_not_authorized",
]


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPaperLabConfig:
    """Configuration for the Assistant v1 daily paper-lab loop."""

    output_root: Path | str
    bars_csv: Path | str = _DEFAULT_BARS_CSV
    as_of_date: str | None = None
    symbol: str = _DEFAULT_SYMBOL
    sma_fast_window: int = 50
    sma_slow_window: int = 200

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _required_path(self.output_root, "output_root"))
        object.__setattr__(self, "bars_csv", _required_path(self.bars_csv, "bars_csv"))
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        if self.sma_fast_window <= 0:
            raise ValidationError("sma_fast_window must be positive.")
        if self.sma_slow_window <= 0:
            raise ValidationError("sma_slow_window must be positive.")
        if self.sma_fast_window >= self.sma_slow_window:
            raise ValidationError("sma_fast_window must be less than sma_slow_window.")


def run_etf_sma_daily_paper_lab(config: EtfSmaDailyPaperLabConfig) -> dict[str, Any]:
    """Execute the daily assistant command and write the packet artifacts."""
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    payload = build_etf_sma_daily_paper_lab(config)

    record_file = output_root / _RECORD_FILENAME
    record_line = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":")) + "\n"
    record_file.write_text(record_line, encoding="utf-8", newline="\n")

    brief_file = output_root / _BRIEF_FILENAME
    brief_file.write_text(_render_brief_markdown(payload), encoding="utf-8", newline="\n")

    manifest_file = output_root / _MANIFEST_FILENAME
    manifest_data = _build_manifest(output_root, payload)
    manifest_line = json.dumps(manifest_data, sort_keys=True, separators=(",", ":")) + "\n"
    manifest_file.write_text(manifest_line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_paper_lab(config: EtfSmaDailyPaperLabConfig) -> dict[str, Any]:
    """Load inputs and build the Assistant v1 daily paper-lab payload."""
    bars_path = Path(config.bars_csv)
    bars = _load_bars(bars_path, config.symbol)

    if config.as_of_date:
        as_of_str = config.as_of_date.strip()
        try:
            as_of_dt = datetime.combine(
                datetime.fromisoformat(as_of_str).date(),
                datetime.min.time(),
                tzinfo=timezone.utc,
            )
        except ValueError as exc:
            raise ValidationError(
                f"as_of_date must be in YYYY-MM-DD format: {config.as_of_date}"
            ) from exc
        as_of_source = "explicit_config"
    else:
        if not bars:
            raise ValidationError("No usable bars found to derive default as-of date.")
        as_of_dt = max(bar.timestamp for bar in bars)
        as_of_str = as_of_dt.strftime("%Y-%m-%d")
        as_of_source = "latest_input_bar"

    latest_input_bar_date = max(bar.timestamp for bar in bars).strftime("%Y-%m-%d")
    signal = evaluate_etf_sma_signal(
        bars,
        EtfSmaSignalConfig(
            as_of=as_of_dt,
            symbol=config.symbol,
            short_window=config.sma_fast_window,
            long_window=config.sma_slow_window,
        ),
    )

    posture = signal.posture
    sma_fast_value = _decimal_text(signal.short_sma)
    sma_slow_value = _decimal_text(signal.long_sma)
    preview_decision = _preview_decision(posture)
    next_operator_action = _next_operator_action(posture, config.sma_slow_window)
    blocker_status = "broker_state_not_observed"
    broker_state_mode = "broker_state_not_observed"
    output_root = Path(config.output_root)
    artifact_paths = _artifact_paths(output_root)
    sma_status = _sma_status(
        posture=posture,
        fast_window=config.sma_fast_window,
        slow_window=config.sma_slow_window,
        usable_bar_count=signal.usable_bar_count,
    )
    data_freshness = _data_freshness(
        as_of_date=as_of_str,
        latest_input_bar_date=latest_input_bar_date,
    )
    research_lab = _research_lab(
        config=config,
        as_of_date=as_of_str,
        posture=posture,
        sma_status=sma_status,
        sma_fast_value=sma_fast_value,
        sma_slow_value=sma_slow_value,
    )

    payload: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "assistant_version": _ASSISTANT_VERSION,
        "packet_type": _PACKET_TYPE,
        "command": _COMMAND,
        "script": _SCRIPT,
        "run_id": f"daily_paper_lab_{as_of_str}",
        "input_data_path": _normalize_path(bars_path),
        "input_data_sha256": _sha256_file(bars_path),
        "as_of_date": as_of_str,
        "as_of_source": as_of_source,
        "latest_input_bar_date": latest_input_bar_date,
        "active_strategy_name": _STRATEGY_NAME,
        "strategy_name": _STRATEGY_NAME,
        "symbol": config.symbol,
        "sma_fast_window": config.sma_fast_window,
        "sma_slow_window": config.sma_slow_window,
        "sma_fast_value": sma_fast_value,
        "sma_slow_value": sma_slow_value,
        "sma_posture_status": sma_status,
        "posture": posture,
        "preview_decision": preview_decision,
        "decision": preview_decision,
        "current_recommendation": _current_recommendation(posture),
        "blocker_status": blocker_status,
        "blockers": [blocker_status],
        "broker_state_mode": broker_state_mode,
        "broker_state_observed": False,
        "broker_state_claim": (
            "No broker positions or open orders were read; this packet makes no "
            "position or order-state claim."
        ),
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "paper_submit_authorization_reason": "operator_has_not_authorized_submit",
        "next_operator_action": next_operator_action,
        "labels": list(_REQUIRED_LABELS),
        "safety_labels": list(_REQUIRED_LABELS),
        "data_freshness": data_freshness,
        "validation_status": "packet_written_offline",
        "system_health": "offline_assistant_packet_ready",
        "artifact_paths": artifact_paths,
        "artifacts": {
            "assistant_brief": artifact_paths["assistant_brief"],
            "operating_brief": artifact_paths["assistant_brief"],
            "operating_record": artifact_paths["operating_record"],
            "manifest": artifact_paths["manifest"],
        },
        "sma": {
            "symbol": signal.symbol,
            "fast_window": signal.short_window,
            "slow_window": signal.long_window,
            "fast_value": sma_fast_value,
            "slow_value": sma_slow_value,
            "latest_close": _decimal_text(signal.latest_close),
            "total_bar_count": signal.total_bar_count,
            "usable_bar_count": signal.usable_bar_count,
            "ignored_future_bar_count": signal.ignored_future_bar_count,
            "posture": posture,
            "status": sma_status,
        },
        "research_lab": research_lab,
        "executive_dashboard": {
            "data_freshness": data_freshness,
            "validation_status": "packet_written_offline",
            "artifact_paths": artifact_paths,
            "system_health": "offline_assistant_packet_ready",
            "safety_labels": list(_REQUIRED_LABELS),
            "next_operator_action": next_operator_action,
        },
    }
    payload["executive_summary"] = {
        "plain_english_status": _plain_english_status(payload),
        "current_recommendation": payload["current_recommendation"],
        "current_blocker": blocker_status,
        "daniel_action_required": _daniel_action_required(posture),
    }
    return payload


def _load_bars(path: Path, symbol: str) -> list[Bar]:
    if not path.exists():
        raise ValidationError(f"Bars CSV not found: {path}")
    bars = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            bars.append(_parse_row_to_bar(row, symbol))
    return bars


def _row_value(row: Mapping[str, object], field_name: str) -> object:
    for key, value in row.items():
        if str(key).strip().lower() == field_name:
            return value
    return None


def _parse_row_to_bar(row: Mapping[str, object], symbol: str) -> Bar:
    close_val = _row_value(row, "close")
    if close_val in (None, ""):
        raise ValidationError("close price is required in CSV.")
    raw_close = Decimal(str(close_val))

    adj_close_val = _row_value(row, "adjusted_close")
    if adj_close_val not in (None, ""):
        close = Decimal(str(adj_close_val))
        factor = close / raw_close if raw_close != Decimal("0") else Decimal("1")
    else:
        close = raw_close
        factor = Decimal("1")

    open_val = _row_value(row, "open")
    open_price = Decimal(str(open_val)) if open_val not in (None, "") else raw_close

    high_val = _row_value(row, "high")
    high = Decimal(str(high_val)) if high_val not in (None, "") else max(open_price, raw_close)

    low_val = _row_value(row, "low")
    low = Decimal(str(low_val)) if low_val not in (None, "") else min(open_price, raw_close)

    volume_val = _row_value(row, "volume")
    volume = Decimal(str(volume_val)) if volume_val not in (None, "") else Decimal("0")

    open_price = open_price * factor
    high = high * factor
    low = low * factor

    high = max(high, open_price, close)
    low = min(low, open_price, close)

    dt_val = None
    for date_field in ("date", "timestamp", "datetime"):
        val = _row_value(row, date_field)
        if val not in (None, ""):
            dt_val = str(val).strip()
            break

    if not dt_val:
        raise ValidationError("date/timestamp is required in CSV.")

    try:
        if "T" in dt_val:
            dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        else:
            dt = datetime.combine(datetime.fromisoformat(dt_val).date(), datetime.min.time())
    except ValueError as exc:
        raise ValidationError(f"Invalid date format: {dt_val}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    row_symbol = _row_value(row, "symbol")
    symbol_str = symbol if row_symbol in (None, "") else str(row_symbol).strip().upper()

    return Bar(
        symbol=symbol_str,
        timestamp=dt,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    return path


def _normalize_path(path: Path | str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _artifact_paths(output_root: Path) -> dict[str, str]:
    return {
        "assistant_brief": _normalize_path(output_root / _BRIEF_FILENAME),
        "operating_record": _normalize_path(output_root / _RECORD_FILENAME),
        "manifest": _normalize_path(output_root / _MANIFEST_FILENAME),
    }


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    return value


def _preview_decision(posture: str) -> str:
    if posture == "insufficient_history":
        return "insufficient_history"
    if posture == "bullish_risk_on":
        return "offline_preview_bullish_risk_on"
    return "offline_preview_defensive_risk_off"


def _next_operator_action(posture: str, slow_window: int) -> str:
    if posture == "insufficient_history":
        return f"provide_at_least_{slow_window}_usable_daily_bars_before_preview_use"
    return "review_assistant_brief_no_broker_action"


def _current_recommendation(posture: str) -> str:
    if posture == "insufficient_history":
        return (
            "Do not submit orders. The SMA preview is blocked until enough "
            "daily bars are available."
        )
    return (
        "Treat this as an offline research preview only. Do not submit paper or "
        "live orders from this packet."
    )


def _sma_status(
    *,
    posture: str,
    fast_window: int,
    slow_window: int,
    usable_bar_count: int,
) -> str:
    if posture == "insufficient_history":
        return (
            f"insufficient_history: {usable_bar_count} usable bars is fewer than "
            f"the {slow_window}-bar slow SMA requirement"
        )
    if posture == "bullish_risk_on":
        return f"risk_on: SMA{fast_window} is above SMA{slow_window}"
    return f"risk_off: SMA{fast_window} is at or below SMA{slow_window}"


def _data_freshness(*, as_of_date: str, latest_input_bar_date: str) -> dict[str, Any]:
    if as_of_date == latest_input_bar_date:
        status = "as_of_matches_latest_input_bar"
    elif as_of_date < latest_input_bar_date:
        status = "as_of_before_latest_input_bar"
    else:
        status = "as_of_after_latest_input_bar"
    return {
        "status": status,
        "as_of_date": as_of_date,
        "latest_input_bar_date": latest_input_bar_date,
        "freshness_basis": "input_csv_latest_bar_only",
        "wall_clock_staleness": "not_evaluated_by_offline_command",
    }


def _research_lab(
    *,
    config: EtfSmaDailyPaperLabConfig,
    as_of_date: str,
    posture: str,
    sma_status: str,
    sma_fast_value: str | None,
    sma_slow_value: str | None,
) -> dict[str, Any]:
    fast_value = sma_fast_value if sma_fast_value is not None else "not_available"
    slow_value = sma_slow_value if sma_slow_value is not None else "not_available"
    return {
        "active_strategy_evidence": [
            f"{config.symbol} daily bars loaded from {_normalize_path(config.bars_csv)}",
            (
                f"SMA {config.sma_fast_window}/{config.sma_slow_window} evaluated "
                f"as of {as_of_date}"
            ),
            f"posture={posture}",
            f"sma_status={sma_status}",
            f"sma_fast_value={fast_value}",
            f"sma_slow_value={slow_value}",
        ],
        "candidate_strategy_board": [
            {
                "strategy_name": "candidate_strategy_placeholder",
                "status": "no_candidates_loaded",
                "note": (
                    "Assistant v1 keeps SPY SMA 50/200 as the single controlled "
                    "test strategy."
                ),
            }
        ],
        "confidence_status": "confidence_not_yet_quantified",
        "missing_evidence": [
            "broker_state_not_observed",
            "multi_day_assistant_packet_history_not_yet_accumulated",
            "strategy_confidence_not_yet_quantified",
        ],
        "next_research_action": "accumulate_daily_assistant_packets_after_input_data_refresh",
    }


def _plain_english_status(payload: Mapping[str, Any]) -> str:
    fast_window = payload["sma_fast_window"]
    slow_window = payload["sma_slow_window"]
    as_of_date = payload["as_of_date"]
    posture = payload["posture"]
    if posture == "bullish_risk_on":
        return (
            f"As of {as_of_date}, SPY is risk-on under the SMA "
            f"{fast_window}/{slow_window} test."
        )
    if posture == "defensive_risk_off":
        return (
            f"As of {as_of_date}, SPY is risk-off under the SMA "
            f"{fast_window}/{slow_window} test."
        )
    return (
        f"As of {as_of_date}, the SMA {fast_window}/{slow_window} test has "
        "insufficient usable history."
    )


def _daniel_action_required(posture: str) -> str:
    if posture == "insufficient_history":
        return "Yes: provide enough daily input bars before relying on the preview."
    return (
        "No broker action is required. Daniel can review the packet and refresh "
        "input data outside this command when needed."
    )


def _render_brief_markdown(payload: dict[str, Any]) -> str:
    labels_list = "\n".join(f"* `{label}`" for label in payload["safety_labels"])
    artifact_lines = "\n".join(
        f"* **{name}**: `{path}`"
        for name, path in payload["artifact_paths"].items()
    )
    evidence_lines = "\n".join(
        f"* {item}" for item in payload["research_lab"]["active_strategy_evidence"]
    )
    missing_evidence_lines = "\n".join(
        f"* {item}" for item in payload["research_lab"]["missing_evidence"]
    )
    candidate_lines = "\n".join(
        f"* **{item['strategy_name']}**: {item['status']} - {item['note']}"
        for item in payload["research_lab"]["candidate_strategy_board"]
    )
    freshness = payload["data_freshness"]

    return f"""# Daily Trading Research Command Center

## Executive summary
* **Plain-English status**: {payload["executive_summary"]["plain_english_status"]}
* **Current recommendation**: {payload["current_recommendation"]}
* **Current blocker**: {payload["blocker_status"]}. {payload["broker_state_claim"]}
* **Does Daniel need to do anything?** {payload["executive_summary"]["daniel_action_required"]}

## Trading desk brief
* **Active strategy**: {payload["active_strategy_name"]}
* **Market/posture state**: {payload["sma_posture_status"]}
* **Preview decision**: {payload["preview_decision"]}
* **Blocker status**: {payload["blocker_status"]}
* **Paper submit authorization status**: {payload["paper_submit_authorization_status"]} (`paper_submit_authorized=false`)
* **Broker-state mode**: {payload["broker_state_mode"]}
* **As-of date**: {payload["as_of_date"]}
* **Input data path**: `{payload["input_data_path"]}`

## Research lab section
* **Active strategy evidence**:
{evidence_lines}
* **Candidate strategy board**:
{candidate_lines}
* **Confidence status**: {payload["research_lab"]["confidence_status"]}
* **Missing evidence**:
{missing_evidence_lines}
* **Next research action**: {payload["research_lab"]["next_research_action"]}

## Executive dashboard
* **Data freshness**: {freshness["status"]} (latest input bar: {freshness["latest_input_bar_date"]}; basis: {freshness["freshness_basis"]}; wall-clock staleness: {freshness["wall_clock_staleness"]})
* **Validation status**: {payload["validation_status"]}
* **Artifact paths**:
{artifact_lines}
* **System health**: {payload["system_health"]}
* **Safety labels**:
{labels_list}
* **Next operator action**: {payload["next_operator_action"]}
"""


def _build_manifest(output_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    indexed_artifacts = {
        "assistant_brief": _artifact_metadata(output_root / _BRIEF_FILENAME),
        "operating_record": _artifact_metadata(output_root / _RECORD_FILENAME),
    }
    return {
        "schema_version": _SCHEMA_VERSION,
        "assistant_version": _ASSISTANT_VERSION,
        "manifest_type": "daily_trading_research_command_center_index",
        "command": _COMMAND,
        "script": _SCRIPT,
        "run_id": payload["run_id"],
        "as_of_date": payload["as_of_date"],
        "active_strategy_name": payload["active_strategy_name"],
        "input_data_path": payload["input_data_path"],
        "input_data_sha256": payload["input_data_sha256"],
        "sma_posture_status": payload["sma_posture_status"],
        "preview_decision": payload["preview_decision"],
        "blocker_status": payload["blocker_status"],
        "broker_state_mode": payload["broker_state_mode"],
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "safety_labels": list(_REQUIRED_LABELS),
        "artifact_paths": dict(payload["artifact_paths"]),
        "indexed_artifacts": indexed_artifacts,
    }


def _artifact_metadata(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "path": _normalize_path(path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
