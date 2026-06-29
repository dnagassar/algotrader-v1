"""Offline adjusted ETF bars refresh intake.

Consumes a refreshed operator-supplied Tiingo adjusted ETF daily-bars CSV,
validates and canonicalizes it, and emits one M446 JSONL refresh manifest plus
a refreshed canonical adjusted ETF CSV if valid and current.

This module is completely offline, local, deterministic, credential-free,
network-free, broker-free, and mutation-free.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "APPROVED_ADJUSTED_ETF_SYMBOLS",
    "EtfSmaAdjustedSpyBarsRefreshIntakeConfig",
    "build_etf_sma_adjusted_spy_bars_refresh_intake",
    "render_etf_sma_adjusted_spy_bars_refresh_intake_json",
    "render_etf_sma_adjusted_spy_bars_refresh_intake_text",
    "run_etf_sma_adjusted_spy_bars_refresh_intake",
    "write_etf_sma_adjusted_spy_bars_refresh_intake_jsonl",
]

_MILESTONE = "M446"
_RECORD_TYPE = "etf_sma_adjusted_spy_bars_refresh_manifest"
_COMMAND = "etf-sma-adjusted-spy-bars-refresh-intake"
APPROVED_ADJUSTED_ETF_SYMBOLS = ("SPY", "QQQ", "IWM", "TLT", "GLD")
_DEFAULT_SYMBOL = "SPY"

_REQUIRED_COLUMNS = ("date", "open", "high", "low", "close", "volume")
_BASIS_COLUMN = "adjusted_close"
_CANONICAL_COLUMNS = ("symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume")

_OUTPUT_FALSE_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "live_authorized",
    "network_access_attempted",
    "credential_access_attempted",
)


@dataclass(frozen=True, slots=True)
class EtfSmaAdjustedSpyBarsRefreshIntakeConfig:
    """Inputs for M446 adjusted ETF bars refresh intake command."""

    expected_latest_bar_date: date | str
    input_csv: Path | str
    canonical_csv: Path | str
    run_log: Path | str
    symbol: str = _DEFAULT_SYMBOL
    run_id: str = "m446_adjusted_spy_bars_refresh_intake"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "expected_latest_bar_date",
            _required_date_text(self.expected_latest_bar_date, "expected_latest_bar_date"),
        )
        object.__setattr__(self, "input_csv", _required_path(self.input_csv, "input_csv"))
        object.__setattr__(self, "symbol", _approved_symbol(self.symbol))
        object.__setattr__(
            self,
            "canonical_csv",
            _required_path(self.canonical_csv, "canonical_csv"),
        )
        object.__setattr__(self, "run_log", _required_path(self.run_log, "run_log"))
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))


@dataclass(frozen=True, slots=True)
class _ParsedRow:
    symbol: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int


def run_etf_sma_adjusted_spy_bars_refresh_intake(
    config: EtfSmaAdjustedSpyBarsRefreshIntakeConfig,
) -> dict[str, object]:
    """Execute the refresh intake command and write the JSONL manifest."""
    checked_config = _config(config)
    payload = build_etf_sma_adjusted_spy_bars_refresh_intake(checked_config)
    write_etf_sma_adjusted_spy_bars_refresh_intake_jsonl(payload, checked_config.run_log)
    return payload


def build_etf_sma_adjusted_spy_bars_refresh_intake(
    config: EtfSmaAdjustedSpyBarsRefreshIntakeConfig,
) -> dict[str, object]:
    """Validate, canonicalize, and construct the M446 refresh manifest payload."""
    checked_config = _config(config)

    input_path = checked_config.input_csv
    if not input_path.exists() or not input_path.is_file():
        return _build_manifest(
            checked_config,
            refresh_state="blocked_missing_operator_input_csv",
            refresh_blockers=["missing_operator_input_csv"],
        )

    # Read and parse input file
    try:
        data = input_path.read_bytes()
        input_sha256 = hashlib.sha256(data).hexdigest()
        text = data.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return _build_manifest(
            checked_config,
            refresh_state="blocked_invalid_adjusted_bars",
            refresh_blockers=["malformed_csv"],
        )

    # Parse CSV structure
    try:
        reader = csv.DictReader(text.splitlines())
        fieldnames = reader.fieldnames
        if not fieldnames:
            return _build_manifest(
                checked_config,
                refresh_state="blocked_invalid_adjusted_bars",
                refresh_blockers=["malformed_csv"],
                operator_input_sha256=input_sha256,
            )

        # Check required columns
        missing_cols = [col for col in _REQUIRED_COLUMNS if col not in fieldnames]
        if missing_cols:
            return _build_manifest(
                checked_config,
                refresh_state="blocked_invalid_adjusted_bars",
                refresh_blockers=[f"missing_required_columns:{','.join(missing_cols)}"],
                operator_input_sha256=input_sha256,
            )

        # Require adjusted_close specifically (M446 correction 1)
        if _BASIS_COLUMN not in fieldnames:
            return _build_manifest(
                checked_config,
                refresh_state="blocked_invalid_adjusted_bars",
                refresh_blockers=["missing_adjusted_close"],
                operator_input_sha256=input_sha256,
            )

        # Check duplicate headers
        if len(set(fieldnames)) != len(fieldnames):
            return _build_manifest(
                checked_config,
                refresh_state="blocked_invalid_adjusted_bars",
                refresh_blockers=["duplicate_columns"],
                operator_input_sha256=input_sha256,
            )

        parsed_rows: list[_ParsedRow] = []
        blockers: list[str] = []
        seen_dates: set[date] = set()
        duplicate_dates = False

        for row_idx, row in enumerate(reader, start=2):
            if None in row or any(val is None for val in row.values()):
                blockers.append("malformed_csv_row")
                continue

            try:
                # 8. Require requested approved ETF daily bars if the source has a symbol column
                if "symbol" in row:
                    sym = str(row["symbol"]).strip()
                    if sym.upper() != checked_config.symbol:
                        blockers.append(
                            f"symbol_scope_must_be_{checked_config.symbol.lower()}"
                        )
                        continue
                    parsed_symbol = checked_config.symbol
                else:
                    parsed_symbol = checked_config.symbol

                # Parse date
                date_str = str(row.get("date")).strip()
                if len(date_str) != 10 or date_str[4] != "-" or date_str[7] != "-":
                    raise ValueError("Invalid ISO date format")
                parsed_date = date.fromisoformat(date_str)

                # Parse OHLCV values
                parsed_open = _parse_positive_decimal(row.get("open"), "open")
                parsed_high = _parse_positive_decimal(row.get("high"), "high")
                parsed_low = _parse_positive_decimal(row.get("low"), "low")
                parsed_close = _parse_positive_decimal(row.get("close"), "close")
                parsed_adj = _parse_positive_decimal(row.get(_BASIS_COLUMN), _BASIS_COLUMN)
                parsed_vol = _parse_non_negative_int(row.get("volume"), "volume")

                # Track duplicates
                if parsed_date in seen_dates:
                    duplicate_dates = True

                seen_dates.add(parsed_date)
                parsed_rows.append(
                    _ParsedRow(
                        symbol=parsed_symbol,
                        date=parsed_date,
                        open=parsed_open,
                        high=parsed_high,
                        low=parsed_low,
                        close=parsed_close,
                        adjusted_close=parsed_adj,
                        volume=parsed_vol,
                    )
                )

            except (ValueError, TypeError, ValidationError, InvalidOperation) as exc:
                blockers.append(_row_blocker_message(str(exc)))

        # Fail closed validation checks
        if blockers:
            return _build_manifest(
                checked_config,
                refresh_state="blocked_invalid_adjusted_bars",
                refresh_blockers=_dedupe(blockers),
                operator_input_sha256=input_sha256,
            )

        if duplicate_dates:
            return _build_manifest(
                checked_config,
                refresh_state="blocked_invalid_adjusted_bars",
                refresh_blockers=["duplicate_dates"],
                operator_input_sha256=input_sha256,
            )

        if not parsed_rows:
            return _build_manifest(
                checked_config,
                refresh_state="blocked_invalid_adjusted_bars",
                refresh_blockers=["zero_valid_rows"],
                operator_input_sha256=input_sha256,
            )

    except Exception:
        return _build_manifest(
            checked_config,
            refresh_state="blocked_invalid_adjusted_bars",
            refresh_blockers=["malformed_csv"],
            operator_input_sha256=input_sha256,
        )

    # Compute latest local bar date
    sorted_rows = sorted(parsed_rows, key=lambda r: r.date)
    latest_local_bar_date = sorted_rows[-1].date
    expected_date = date.fromisoformat(checked_config.expected_latest_bar_date)

    refresh_warnings: list[str] = []
    refresh_blockers = []

    if latest_local_bar_date < expected_date:
        refresh_state = "blocked_stale_adjusted_bars"
        refresh_blockers.append("latest_local_bar_date_before_expected")
    elif latest_local_bar_date > expected_date:
        refresh_state = "accepted_adjusted_bars_ahead_of_expected"
        refresh_warnings.append("latest_local_bar_date_after_expected")
    else:
        refresh_state = "accepted_current_adjusted_bars"

    # If any blocker exists (like stale date), fail closed and do not write CSV
    if refresh_blockers:
        return _build_manifest(
            checked_config,
            refresh_state=refresh_state,
            refresh_blockers=refresh_blockers,
            refresh_warnings=refresh_warnings,
            latest_local_bar_date=latest_local_bar_date.isoformat(),
            operator_input_sha256=input_sha256,
        )

    # 9. Require deterministic ascending date order in the canonical output
    # Write canonical CSV output
    canonical_path = Path(checked_config.canonical_csv)
    if canonical_path.parent != Path("."):
        canonical_path.parent.mkdir(parents=True, exist_ok=True)

    with canonical_path.open("w", encoding="utf-8", newline="") as out_stream:
        writer = csv.writer(out_stream, lineterminator="\n")
        writer.writerow(_CANONICAL_COLUMNS)
        for row in sorted_rows:
            writer.writerow(
                (
                    row.symbol,
                    row.date.isoformat(),
                    _decimal_text(row.open),
                    _decimal_text(row.high),
                    _decimal_text(row.low),
                    _decimal_text(row.close),
                    _decimal_text(row.adjusted_close),
                    str(row.volume),
                )
            )

    refreshed_canonical_sha256 = _sha256_file(canonical_path)

    return _build_manifest(
        checked_config,
        refresh_state=refresh_state,
        refresh_blockers=refresh_blockers,
        refresh_warnings=refresh_warnings,
        latest_local_bar_date=latest_local_bar_date.isoformat(),
        operator_input_sha256=input_sha256,
        refreshed_canonical_csv_sha256=refreshed_canonical_sha256,
        accepted_row_count=len(sorted_rows),
        date_range_start=sorted_rows[0].date.isoformat(),
        date_range_end=sorted_rows[-1].date.isoformat(),
    )


def write_etf_sma_adjusted_spy_bars_refresh_intake_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one JSONL manifest record to the specified path."""
    path = Path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    line = render_etf_sma_adjusted_spy_bars_refresh_intake_json(payload) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(line)


def render_etf_sma_adjusted_spy_bars_refresh_intake_json(payload: Mapping[str, object]) -> str:
    """Render the payload as compact sorted JSON."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_adjusted_spy_bars_refresh_intake_text(payload: Mapping[str, object]) -> str:
    """Render the payload as human-readable text."""
    blockers = ", ".join(payload.get("refresh_blockers", [])) or "none"
    warnings = ", ".join(payload.get("refresh_warnings", [])) or "none"
    return "\n".join(
        (
            f"M446 ETF/SMA {payload.get('symbol')} Bars Refresh Intake",
            f"refresh_state: {payload.get('refresh_state')}",
            f"expected_latest_bar_date: {payload.get('expected_latest_bar_date')}",
            f"latest_local_bar_date: {payload.get('latest_local_bar_date') or 'none'}",
            f"operator_input_path: {payload.get('operator_input_path')}",
            f"refreshed_canonical_csv_path: {payload.get('refreshed_canonical_csv_path')}",
            f"accepted_row_count: {payload.get('accepted_row_count')}",
            f"refresh_blockers: {blockers}",
            f"refresh_warnings: {warnings}",
        )
    )


def _build_manifest(
    config: EtfSmaAdjustedSpyBarsRefreshIntakeConfig,
    *,
    refresh_state: str,
    refresh_blockers: list[str],
    refresh_warnings: list[str] | None = None,
    latest_local_bar_date: str = "",
    operator_input_sha256: str = "",
    refreshed_canonical_csv_sha256: str = "",
    accepted_row_count: int = 0,
    date_range_start: str = "",
    date_range_end: str = "",
) -> dict[str, object]:
    """Helper to build the 24-field manifest dict."""
    return {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "refresh_state": refresh_state,
        "expected_latest_bar_date": config.expected_latest_bar_date,
        "latest_local_bar_date": latest_local_bar_date,
        "operator_input_path": str(config.input_csv),
        "operator_input_sha256": operator_input_sha256,
        "refreshed_canonical_csv_path": str(config.canonical_csv),
        "refreshed_canonical_csv_sha256": refreshed_canonical_csv_sha256,
        "accepted_row_count": accepted_row_count,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "basis": _BASIS_COLUMN,
        "refresh_blockers": list(refresh_blockers),
        "refresh_warnings": list(refresh_warnings or []),
        "paper_action_authorized": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "profit_claim": "none",
    }


def _config(value: object) -> EtfSmaAdjustedSpyBarsRefreshIntakeConfig:
    if not isinstance(value, EtfSmaAdjustedSpyBarsRefreshIntakeConfig):
        raise ValidationError("config must be an EtfSmaAdjustedSpyBarsRefreshIntakeConfig.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _approved_symbol(value: object) -> str:
    text = _required_string(value, "symbol").upper()
    if text not in APPROVED_ADJUSTED_ETF_SYMBOLS:
        raise ValidationError(
            "symbol must be one of "
            + ",".join(APPROVED_ADJUSTED_ETF_SYMBOLS)
            + "."
        )
    return text


def _required_path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{field_name} is required.")
        path = Path(text)
    if not str(path):
        raise ValidationError(f"{field_name} is required.")
    return path


def _required_date_text(value: date | str, field_name: str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    text = _required_string(value, field_name)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.") from exc
    if parsed.isoformat() != text:
        raise ValidationError(f"{field_name} must be a YYYY-MM-DD date.")
    return text


def _parse_positive_decimal(value: Any, col_name: str) -> Decimal:
    if value is None:
        raise ValidationError(f"missing {col_name}")
    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValidationError(f"invalid decimal in {col_name}") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValidationError(f"nonpositive_{col_name}")
    return parsed


def _parse_non_negative_int(value: Any, col_name: str) -> int:
    if value is None:
        raise ValidationError(f"missing {col_name}")
    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise ValidationError(f"invalid integer in {col_name}") from exc
    if parsed < 0:
        raise ValidationError(f"negative_{col_name}")
    return parsed


def _row_blocker_message(msg: str) -> str:
    if "nonpositive_open" in msg or "nonpositive_high" in msg or "nonpositive_low" in msg or "nonpositive_close" in msg or "negative_volume" in msg or "invalid decimal" in msg or "invalid integer" in msg:
        return "invalid_ohlcv_values"
    if "nonpositive_adjusted_close" in msg:
        return "nonpositive_adjusted_close"
    if "ISO date" in msg:
        return "invalid_date"
    return msg


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value
