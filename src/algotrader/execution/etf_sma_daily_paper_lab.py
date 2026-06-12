"""Working Daily ETF SMA Daily Paper-Lab execution runner for V3R.

This module is completely offline, deterministic, credential-free, network-free,
and broker-free. It generates a daily paper-lab operating packet.
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

from algotrader.errors import ValidationError
from algotrader.core.types import Bar
from algotrader.signals.etf_sma_evaluator import evaluate_etf_sma_signal, EtfSmaSignalConfig

__all__ = [
    "EtfSmaDailyPaperLabConfig",
    "run_etf_sma_daily_paper_lab",
    "build_etf_sma_daily_paper_lab",
]

_DEFAULT_SYMBOL = "SPY"
_DEFAULT_BARS_CSV = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
_STRATEGY_NAME = "SPY daily long-only ETF SMA 50/200 trend filter"
_SCHEMA_VERSION = "1"
_REQUIRED_LABELS = [
    "paper_lab_only",
    "signal_evaluation_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "offline_only",
]


@dataclass(frozen=True, slots=True)
class EtfSmaDailyPaperLabConfig:
    """Configuration for V3R Daily Paper-Lab loop execution."""

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
    """Execute the daily paper-lab command and write artifacts."""
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    payload = build_etf_sma_daily_paper_lab(config)

    # 1. Write operating_record.jsonl
    record_file = output_root / "operating_record.jsonl"
    record_line = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":")) + "\n"
    record_file.write_text(record_line, encoding="utf-8", newline="\n")

    # 2. Write operating_brief.md
    brief_file = output_root / "operating_brief.md"
    brief_content = _render_brief_markdown(payload)
    brief_file.write_text(brief_content, encoding="utf-8", newline="\n")

    # 3. Compute manifest and write manifest.jsonl
    manifest_file = output_root / "manifest.jsonl"
    manifest_data = _build_manifest(output_root, payload["run_id"], payload["as_of_date"])
    manifest_line = json.dumps(manifest_data, sort_keys=True, separators=(",", ":")) + "\n"
    manifest_file.write_text(manifest_line, encoding="utf-8", newline="\n")

    return payload


def build_etf_sma_daily_paper_lab(config: EtfSmaDailyPaperLabConfig) -> dict[str, Any]:
    """Load inputs and build daily paper-lab payload."""
    bars_path = Path(config.bars_csv)
    bars = _load_bars(bars_path, config.symbol)

    # Resolve as_of_date
    if config.as_of_date:
        as_of_str = config.as_of_date.strip()
        try:
            as_of_dt = datetime.combine(datetime.fromisoformat(as_of_str).date(), datetime.min.time(), tzinfo=timezone.utc)
        except ValueError as exc:
            raise ValidationError(f"as_of_date must be in YYYY-MM-DD format: {config.as_of_date}") from exc
    else:
        if not bars:
            raise ValidationError("No usable bars found to derive default as-of date.")
        as_of_dt = max(bar.timestamp for bar in bars)
        as_of_str = as_of_dt.strftime("%Y-%m-%d")

    # Run evaluate_etf_sma_signal
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
    sma_fast_val = _decimal_text(signal.short_sma)
    sma_slow_val = _decimal_text(signal.long_sma)

    # Determine decision, next operator action
    if posture == "insufficient_history":
        decision = "insufficient_history"
        next_operator_action = "observe_insufficient_history"
    elif posture == "bullish_risk_on":
        decision = "offline_preview_bullish_risk_on"
        next_operator_action = "observe_offline_preview_only"
    else:
        decision = "offline_preview_defensive_risk_off"
        next_operator_action = "observe_offline_preview_only"

    output_root = Path(config.output_root)
    run_id = f"daily_paper_lab_{as_of_str}"

    return {
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_data_path": _normalize_path(bars_path),
        "as_of_date": as_of_str,
        "symbol": config.symbol,
        "strategy_name": _STRATEGY_NAME,
        "sma_fast_window": config.sma_fast_window,
        "sma_slow_window": config.sma_slow_window,
        "sma_fast_value": sma_fast_val,
        "sma_slow_value": sma_slow_val,
        "posture": posture,
        "decision": decision,
        "blocker_status": "broker_state_not_observed",
        "broker_state_mode": "broker_state_not_observed",
        "broker_state_observed": False,
        "paper_submit_authorized": False,
        "paper_submit_authorization_status": "not_authorized",
        "next_operator_action": next_operator_action,
        "labels": list(_REQUIRED_LABELS),
        "artifacts": {
            "operating_brief": _normalize_path(output_root / "operating_brief.md"),
            "operating_record": _normalize_path(output_root / "operating_record.jsonl"),
            "manifest": _normalize_path(output_root / "manifest.jsonl"),
        },
    }


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
        if raw_close != Decimal("0"):
            factor = close / raw_close
        else:
            factor = Decimal("1")
    else:
        close = raw_close
        factor = Decimal("1")

    # fallback for other fields
    open_val = _row_value(row, "open")
    open_price = Decimal(str(open_val)) if open_val not in (None, "") else raw_close

    high_val = _row_value(row, "high")
    high = Decimal(str(high_val)) if high_val not in (None, "") else max(open_price, raw_close)

    low_val = _row_value(row, "low")
    low = Decimal(str(low_val)) if low_val not in (None, "") else min(open_price, raw_close)

    volume_val = _row_value(row, "volume")
    volume = Decimal(str(volume_val)) if volume_val not in (None, "") else Decimal("0")

    # Scale by adjustment factor
    open_price = open_price * factor
    high = high * factor
    low = low * factor

    # Clamp to ensure invariants are strictly satisfied
    high = max(high, open_price, close)
    low = min(low, open_price, close)


    # date
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


def _render_brief_markdown(payload: dict[str, Any]) -> str:
    labels_list = "\n".join(f"* `{label}`" for label in payload["labels"])
    fast_val = payload["sma_fast_value"] or "None"
    slow_val = payload["sma_slow_value"] or "None"

    return f"""# SPY SMA Paper-Lab Daily Operating Brief

## Metadata
* **Run ID**: {payload["run_id"]}
* **Generated At**: {payload["generated_at"]}
* **As-of Date**: {payload["as_of_date"]}
* **Symbol**: {payload["symbol"]}
* **Strategy**: {payload["strategy_name"]}
* **Input Data Path**: {payload["input_data_path"]}
* **Broker-State Mode**: {payload["broker_state_mode"]}
* **Broker-State Observed**: {payload["broker_state_observed"]}
* **Paper Submit Authorized**: {payload["paper_submit_authorized"]}
* **Paper Submit Authorization Status**: {payload["paper_submit_authorization_status"]}

## SMA Analysis
* **SMA Fast Window (50)**: {payload["sma_fast_window"]}
* **SMA Slow Window (200)**: {payload["sma_slow_window"]}
* **SMA Fast Value**: {fast_val}
* **SMA Slow Value**: {slow_val}
* **Posture**: {payload["posture"]}

## Cycle Decision
* **Decision**: {payload["decision"]}
* **Blocker Status**: {payload["blocker_status"]}
* **Next Operator Action**: {payload["next_operator_action"]}

## Safety Labels
{labels_list}
"""


def _build_manifest(output_root: Path, run_id: str, as_of_date: str) -> dict[str, Any]:
    artifacts = {}
    for filename in ("operating_brief.md", "operating_record.jsonl", "manifest.jsonl"):
        filepath = output_root / filename
        if filepath.exists():
            content = filepath.read_bytes()
            artifacts[filename.split(".")[0]] = {
                "path": _normalize_path(filepath),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }

    return {
        "schema_version": _SCHEMA_VERSION,
        "run_id": run_id,
        "as_of_date": as_of_date,
        "artifacts": artifacts,
    }
