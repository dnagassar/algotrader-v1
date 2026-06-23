"""Explicitly gated adjusted SPY market-data refresh adapter.

This module plans and, when explicitly authorized, executes a Tiingo adjusted
SPY daily-bar refresh before handing the normalized CSV to the existing M446
intake/canonicalization path.

Default and test modes are network-free, credential-free, broker-free, and
deterministic.  The live provider path is implemented but requires both the
``live_market_data_fetch`` mode and an explicit authorization flag.
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "SPYAdjustedDataRefreshConfig",
    "build_tiingo_adjusted_spy_request",
    "render_spy_adjusted_data_refresh_json",
    "render_spy_adjusted_data_refresh_text",
    "run_spy_adjusted_data_refresh",
    "write_spy_adjusted_data_refresh_jsonl",
]

_RECORD_TYPE = "automatic_adjusted_spy_data_refresh"
_MILESTONE = "v1.77"
_PROVIDER = "tiingo"
_SYMBOL = "SPY"
_DRY_RUN = "dry_run"
_OFFLINE_FIXTURE = "offline_fixture"
_LIVE_MARKET_DATA_FETCH = "live_market_data_fetch"
_MODES = (_OFFLINE_FIXTURE, _DRY_RUN, _LIVE_MARKET_DATA_FETCH)
_TOKEN_ENV_VAR = "TIINGO_API_KEY"
_TIINGO_URL = "https://api.tiingo.com/tiingo/daily/SPY/prices"
_DEFAULT_START_DATE = "1993-01-29"
_CANONICAL_COLUMNS = (
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)
_REQUIRED_PROVIDER_FIELDS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adjusted_close",
)
_PROVIDER_FIELD_ALIASES = {
    "date": ("date",),
    "open": ("open",),
    "high": ("high",),
    "low": ("low",),
    "close": ("close",),
    "volume": ("volume",),
    "adjusted_close": ("adjClose", "adjusted_close"),
    "symbol": ("symbol", "ticker"),
}
_KNOWN_TIINGO_FIELDS = frozenset(
    {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjClose",
        "adjusted_close",
        "adjOpen",
        "adjHigh",
        "adjLow",
        "adjVolume",
        "divCash",
        "splitFactor",
        "symbol",
        "ticker",
    }
)
_VALIDATION_CONTRACT = (
    "known_tiingo_provider_columns_only",
    "symbol_scope_spy_only",
    "deterministic_date_parse",
    "ascending_canonical_date_sort",
    "duplicate_dates_rejected",
    "missing_adjusted_close_rejected",
    "nonpositive_adjusted_close_rejected",
    "missing_required_ohlcv_rejected",
    "latest_date_must_be_newer_than_existing_canonical",
    "expected_latest_bar_date_must_match_when_supplied",
    "token_value_never_printed_or_written",
    "broker_access_forbidden",
)
_FALSE_SAFETY_FIELDS = (
    "paper_action_authorized",
    "submit_authorized",
    "paper_submit_authorized",
    "paper_submit_performed",
    "broker_read_performed",
    "broker_mutation_performed",
    "broker_action_performed",
    "live_authorized",
    "live_trading_performed",
    "credential_access_attempted",
)


@dataclass(frozen=True, slots=True)
class SPYAdjustedDataRefreshConfig:
    """Inputs for the automatic adjusted SPY refresh adapter."""

    provider: str
    expected_latest_bar_date: date | str
    output_csv: Path | str
    canonical_csv: Path | str
    run_log: Path | str
    mode: str = _DRY_RUN
    fixture_input_path: Path | str | None = None
    live_fetch_authorized: bool = False
    raw_response_path: Path | str | None = None
    start_date: date | str = _DEFAULT_START_DATE
    token_env_var: str = _TOKEN_ENV_VAR
    run_id: str = "v177_automatic_adjusted_spy_data_refresh"

    def __post_init__(self) -> None:
        provider = _required_string(self.provider, "provider").lower()
        if provider != _PROVIDER:
            raise ValidationError("provider must be tiingo.")
        object.__setattr__(self, "provider", provider)

        mode = _required_string(self.mode, "mode")
        if mode not in _MODES:
            raise ValidationError(
                "mode must be offline_fixture, dry_run, or live_market_data_fetch."
            )
        object.__setattr__(self, "mode", mode)
        object.__setattr__(
            self,
            "expected_latest_bar_date",
            _required_date_text(
                self.expected_latest_bar_date,
                "expected_latest_bar_date",
            ),
        )
        object.__setattr__(
            self,
            "start_date",
            _required_date_text(self.start_date, "start_date"),
        )
        object.__setattr__(self, "output_csv", _required_path(self.output_csv, "output_csv"))
        object.__setattr__(
            self,
            "canonical_csv",
            _required_path(self.canonical_csv, "canonical_csv"),
        )
        object.__setattr__(self, "run_log", _required_path(self.run_log, "run_log"))
        if self.fixture_input_path is not None:
            object.__setattr__(
                self,
                "fixture_input_path",
                _required_path(self.fixture_input_path, "fixture_input_path"),
            )
        raw_response_path = self.raw_response_path
        if raw_response_path is None:
            run_log = _required_path(self.run_log, "run_log")
            raw_response_path = run_log.with_name(
                f"{run_log.stem}_raw_tiingo_response.json"
            )
        object.__setattr__(
            self,
            "raw_response_path",
            _required_path(raw_response_path, "raw_response_path"),
        )
        object.__setattr__(
            self,
            "token_env_var",
            _required_string(self.token_env_var, "token_env_var"),
        )
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))


@dataclass(frozen=True, slots=True)
class _NormalizedRow:
    symbol: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int


def run_spy_adjusted_data_refresh(
    config: SPYAdjustedDataRefreshConfig,
    *,
    token_lookup: Callable[[str], str | None] | None = None,
    http_get: Callable[[str, Mapping[str, str]], bytes] | None = None,
) -> dict[str, object]:
    """Run the selected refresh mode and write one deterministic JSONL manifest."""
    payload = _build_refresh_payload(
        _config(config),
        token_lookup=token_lookup or os.environ.get,
        http_get=http_get,
    )
    write_spy_adjusted_data_refresh_jsonl(payload, config.run_log)
    return payload


def build_tiingo_adjusted_spy_request(
    config: SPYAdjustedDataRefreshConfig,
) -> dict[str, object]:
    """Return a sanitized Tiingo daily-prices request plan."""
    checked_config = _config(config)
    query = (
        f"startDate={checked_config.start_date}"
        f"&endDate={checked_config.expected_latest_bar_date}"
        "&format=json"
    )
    return {
        "method": "GET",
        "url": f"{_TIINGO_URL}?{query}",
        "headers": {"Authorization": "Token <redacted>"},
        "token_env_var": checked_config.token_env_var,
        "symbol": _SYMBOL,
        "provider_adjusted_close_field": "adjClose",
    }


def write_spy_adjusted_data_refresh_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one refresh manifest record."""
    path = Path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_spy_adjusted_data_refresh_json(payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def render_spy_adjusted_data_refresh_json(payload: Mapping[str, object]) -> str:
    """Render a compact sorted JSON object."""
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_spy_adjusted_data_refresh_text(payload: Mapping[str, object]) -> str:
    """Render a concise operator-facing text summary."""
    blockers = ", ".join(_string_sequence(payload.get("refresh_blockers"))) or "none"
    warnings = ", ".join(_string_sequence(payload.get("refresh_warnings"))) or "none"
    request = _mapping(payload.get("provider_request"))
    return "\n".join(
        (
            "Automatic Adjusted SPY Data Refresh",
            f"refresh_state: {payload.get('refresh_state')}",
            f"mode: {payload.get('mode')}",
            f"provider: {payload.get('provider')}",
            f"symbol: {payload.get('symbol')}",
            f"request_url: {request.get('url', '')}",
            f"expected_latest_bar_date: {payload.get('expected_latest_bar_date')}",
            "current_canonical_latest_bar_date: "
            f"{payload.get('current_canonical_latest_bar_date') or 'none'}",
            f"latest_provider_bar_date: {payload.get('latest_provider_bar_date') or 'none'}",
            f"output_csv_path: {payload.get('output_csv_path')}",
            f"canonical_csv_path: {payload.get('canonical_csv_path')}",
            f"accepted_row_count: {payload.get('accepted_row_count')}",
            f"network_access_attempted: {_bool_text(payload.get('network_access_attempted'))}",
            "market_data_token_access_attempted: "
            f"{_bool_text(payload.get('market_data_token_access_attempted'))}",
            f"refresh_blockers: {blockers}",
            f"refresh_warnings: {warnings}",
        )
    )


def _build_refresh_payload(
    config: SPYAdjustedDataRefreshConfig,
    *,
    token_lookup: Callable[[str], str | None],
    http_get: Callable[[str, Mapping[str, str]], bytes] | None,
) -> dict[str, object]:
    request = build_tiingo_adjusted_spy_request(config)
    current_latest_error = ""
    try:
        current_latest = _current_canonical_latest(config.canonical_csv)
    except ValidationError as exc:
        current_latest = ""
        current_latest_error = str(exc)

    if config.mode == _DRY_RUN:
        return _manifest(
            config,
            refresh_state="dry_run_refresh_plan_built",
            refresh_blockers=[],
            provider_request=request,
            current_canonical_latest_bar_date=current_latest,
            dry_run_only=True,
        )

    if current_latest_error:
        return _manifest(
            config,
            refresh_state="blocked_current_canonical_invalid",
            refresh_blockers=[f"current_canonical_invalid:{current_latest_error}"],
            provider_request=request,
            current_canonical_latest_bar_date=current_latest,
        )

    if config.mode == _OFFLINE_FIXTURE:
        if config.fixture_input_path is None:
            return _manifest(
                config,
                refresh_state="blocked_offline_fixture_required",
                refresh_blockers=["offline_fixture_input_required"],
                provider_request=request,
                current_canonical_latest_bar_date=current_latest,
            )
        return _run_normalized_refresh(
            config,
            records=_read_fixture_records(config.fixture_input_path),
            provider_request=request,
            current_canonical_latest_bar_date=current_latest,
            source_sha256=_sha256_file(config.fixture_input_path),
            source_path=config.fixture_input_path,
        )

    if config.mode == _LIVE_MARKET_DATA_FETCH:
        if not config.live_fetch_authorized:
            return _manifest(
                config,
                refresh_state="blocked_live_market_data_fetch_not_authorized",
                refresh_blockers=["live_market_data_fetch_not_authorized"],
                provider_request=request,
                current_canonical_latest_bar_date=current_latest,
            )
        if not _runtime_output_path(config.raw_response_path):
            return _manifest(
                config,
                refresh_state="blocked_raw_provider_response_path_not_runtime_output",
                refresh_blockers=["raw_provider_response_path_not_runtime_output"],
                provider_request=request,
                current_canonical_latest_bar_date=current_latest,
                market_data_token_access_attempted=False,
            )
        token = token_lookup(config.token_env_var)
        if not token:
            return _manifest(
                config,
                refresh_state="blocked_market_data_refresh_token_required",
                refresh_blockers=["market_data_refresh_token_required"],
                provider_request=request,
                current_canonical_latest_bar_date=current_latest,
                market_data_token_access_attempted=True,
                market_data_token_loaded=False,
            )
        if http_get is None:
            return _manifest(
                config,
                refresh_state="blocked_live_market_data_fetch_transport_required",
                refresh_blockers=["live_market_data_fetch_transport_required"],
                provider_request=request,
                current_canonical_latest_bar_date=current_latest,
                market_data_token_access_attempted=True,
                market_data_token_loaded=True,
            )
        raw_bytes = http_get(
            str(request["url"]),
            {"Authorization": f"Token {token}"},
        )
        raw_path = Path(config.raw_response_path)
        if raw_path.parent != Path("."):
            raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw_bytes)
        records = _read_provider_json_bytes(raw_bytes)
        return _run_normalized_refresh(
            config,
            records=records,
            provider_request=request,
            current_canonical_latest_bar_date=current_latest,
            source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
            source_path=raw_path,
            network_access_attempted=True,
            market_data_token_access_attempted=True,
            market_data_token_loaded=True,
        )

    raise AssertionError(f"unhandled mode: {config.mode}")


def _run_normalized_refresh(
    config: SPYAdjustedDataRefreshConfig,
    *,
    records: Sequence[Mapping[str, object]],
    provider_request: Mapping[str, object],
    current_canonical_latest_bar_date: str,
    source_sha256: str,
    source_path: Path,
    network_access_attempted: bool = False,
    market_data_token_access_attempted: bool = False,
    market_data_token_loaded: bool = False,
) -> dict[str, object]:
    normalized = _normalize_provider_records(records)
    if not normalized or isinstance(normalized[0], str):
        return _manifest(
            config,
            refresh_state="blocked_invalid_provider_adjusted_bars",
            refresh_blockers=[str(item) for item in normalized],
            provider_request=provider_request,
            current_canonical_latest_bar_date=current_canonical_latest_bar_date,
            source_sha256=source_sha256,
            source_path=source_path,
            network_access_attempted=network_access_attempted,
            market_data_token_access_attempted=market_data_token_access_attempted,
            market_data_token_loaded=market_data_token_loaded,
        )
    rows = normalized

    latest_provider_date = rows[-1].date
    expected_latest_date = date.fromisoformat(config.expected_latest_bar_date)
    if latest_provider_date != expected_latest_date:
        return _manifest(
            config,
            refresh_state="blocked_expected_latest_bar_date_mismatch",
            refresh_blockers=["expected_latest_bar_date_mismatch"],
            provider_request=provider_request,
            current_canonical_latest_bar_date=current_canonical_latest_bar_date,
            latest_provider_bar_date=latest_provider_date.isoformat(),
            date_range_start=rows[0].date.isoformat(),
            date_range_end=latest_provider_date.isoformat(),
            accepted_row_count=len(rows),
            source_sha256=source_sha256,
            source_path=source_path,
            network_access_attempted=network_access_attempted,
            market_data_token_access_attempted=market_data_token_access_attempted,
            market_data_token_loaded=market_data_token_loaded,
        )

    if current_canonical_latest_bar_date:
        current_date = date.fromisoformat(current_canonical_latest_bar_date)
        if latest_provider_date <= current_date:
            return _manifest(
                config,
                refresh_state="blocked_latest_bar_date_not_newer_than_canonical",
                refresh_blockers=["latest_bar_date_not_newer_than_canonical"],
                provider_request=provider_request,
                current_canonical_latest_bar_date=current_canonical_latest_bar_date,
                latest_provider_bar_date=latest_provider_date.isoformat(),
                date_range_start=rows[0].date.isoformat(),
                date_range_end=latest_provider_date.isoformat(),
                accepted_row_count=len(rows),
                source_sha256=source_sha256,
                source_path=source_path,
                network_access_attempted=network_access_attempted,
                market_data_token_access_attempted=market_data_token_access_attempted,
                market_data_token_loaded=market_data_token_loaded,
            )

    output_csv_bytes = _canonical_csv_bytes(rows)
    output_path = Path(config.output_csv)
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_csv_bytes)
    output_sha256 = hashlib.sha256(output_csv_bytes).hexdigest()

    from .etf_sma_adjusted_spy_bars_refresh_intake import (
        EtfSmaAdjustedSpyBarsRefreshIntakeConfig,
        build_etf_sma_adjusted_spy_bars_refresh_intake,
    )

    intake_payload = build_etf_sma_adjusted_spy_bars_refresh_intake(
        EtfSmaAdjustedSpyBarsRefreshIntakeConfig(
            expected_latest_bar_date=config.expected_latest_bar_date,
            input_csv=output_path,
            canonical_csv=config.canonical_csv,
            run_log=config.run_log,
            run_id=f"{config.run_id}_m446_intake",
        )
    )
    intake_state = str(intake_payload.get("refresh_state", ""))
    if intake_state.startswith("blocked"):
        return _manifest(
            config,
            refresh_state="blocked_existing_intake_rejected_adjusted_bars",
            refresh_blockers=["existing_intake_rejected_adjusted_bars"],
            provider_request=provider_request,
            current_canonical_latest_bar_date=current_canonical_latest_bar_date,
            latest_provider_bar_date=latest_provider_date.isoformat(),
            date_range_start=rows[0].date.isoformat(),
            date_range_end=latest_provider_date.isoformat(),
            accepted_row_count=len(rows),
            source_sha256=source_sha256,
            source_path=source_path,
            normalized_output_sha256=output_sha256,
            intake_manifest=intake_payload,
            network_access_attempted=network_access_attempted,
            market_data_token_access_attempted=market_data_token_access_attempted,
            market_data_token_loaded=market_data_token_loaded,
        )

    return _manifest(
        config,
        refresh_state="accepted_adjusted_spy_data_refresh",
        refresh_blockers=[],
        refresh_warnings=_string_sequence(intake_payload.get("refresh_warnings")),
        provider_request=provider_request,
        current_canonical_latest_bar_date=current_canonical_latest_bar_date,
        latest_provider_bar_date=latest_provider_date.isoformat(),
        date_range_start=rows[0].date.isoformat(),
        date_range_end=latest_provider_date.isoformat(),
        accepted_row_count=len(rows),
        source_sha256=source_sha256,
        source_path=source_path,
        normalized_output_sha256=output_sha256,
        canonical_csv_sha256=str(intake_payload.get("refreshed_canonical_csv_sha256", "")),
        intake_manifest=intake_payload,
        network_access_attempted=network_access_attempted,
        market_data_token_access_attempted=market_data_token_access_attempted,
        market_data_token_loaded=market_data_token_loaded,
    )


def _manifest(
    config: SPYAdjustedDataRefreshConfig,
    *,
    refresh_state: str,
    refresh_blockers: Sequence[str],
    provider_request: Mapping[str, object],
    refresh_warnings: Sequence[str] = (),
    current_canonical_latest_bar_date: str = "",
    latest_provider_bar_date: str = "",
    date_range_start: str = "",
    date_range_end: str = "",
    accepted_row_count: int = 0,
    source_sha256: str = "",
    source_path: Path | str | None = None,
    normalized_output_sha256: str = "",
    canonical_csv_sha256: str = "",
    intake_manifest: Mapping[str, object] | None = None,
    dry_run_only: bool = False,
    network_access_attempted: bool = False,
    market_data_token_access_attempted: bool = False,
    market_data_token_loaded: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "milestone": _MILESTONE,
        "record_type": _RECORD_TYPE,
        "run_id": config.run_id,
        "provider": config.provider,
        "symbol": _SYMBOL,
        "mode": config.mode,
        "refresh_state": refresh_state,
        "refresh_blockers": list(refresh_blockers),
        "refresh_warnings": list(refresh_warnings),
        "expected_latest_bar_date": config.expected_latest_bar_date,
        "start_date": config.start_date,
        "current_canonical_latest_bar_date": current_canonical_latest_bar_date,
        "latest_provider_bar_date": latest_provider_bar_date,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "accepted_row_count": accepted_row_count,
        "source_path": str(source_path or ""),
        "source_sha256": source_sha256,
        "output_csv_path": str(config.output_csv),
        "normalized_output_sha256": normalized_output_sha256,
        "canonical_csv_path": str(config.canonical_csv),
        "canonical_csv_sha256": canonical_csv_sha256,
        "run_log_path": str(config.run_log),
        "raw_provider_response_path": str(config.raw_response_path),
        "provider_request": dict(provider_request),
        "provider_column_mapping": {
            "symbol": "constant SPY unless provider symbol/ticker is present",
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "adjusted_close": "adjClose",
            "volume": "volume",
        },
        "validation_contract": list(_VALIDATION_CONTRACT),
        "dry_run_only": dry_run_only,
        "ingest_performed": refresh_state == "accepted_adjusted_spy_data_refresh",
        "network_access_attempted": network_access_attempted,
        "market_data_token_env_var": config.token_env_var,
        "market_data_token_access_attempted": market_data_token_access_attempted,
        "market_data_token_loaded": market_data_token_loaded,
        "market_data_token_value_printed": False,
        "market_data_token_value_written": False,
        "profit_claim": "none",
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }
    for field in _FALSE_SAFETY_FIELDS:
        payload[field] = False
    if intake_manifest is not None:
        payload["existing_intake_manifest"] = dict(intake_manifest)
    return payload


def _normalize_provider_records(
    records: Sequence[Mapping[str, object]],
) -> list[_NormalizedRow] | list[str]:
    blockers: list[str] = []
    rows: list[_NormalizedRow] = []
    seen_dates: set[date] = set()
    duplicate_dates = False
    if not records:
        return ["zero_provider_rows"]

    for record in records:
        unknown = sorted(str(key) for key in record if str(key) not in _KNOWN_TIINGO_FIELDS)
        if unknown:
            blockers.append(f"unknown_provider_columns:{','.join(unknown)}")
            continue
        missing = [
            field
            for field in _REQUIRED_PROVIDER_FIELDS
            if _record_value(record, field) in (None, "")
        ]
        if "adjusted_close" in missing:
            blockers.append("missing_adjusted_close")
            continue
        if missing:
            blockers.append("missing_required_ohlcv")
            continue
        try:
            parsed_symbol = _parse_symbol(record)
            parsed_date = _parse_provider_date(_record_value(record, "date"))
            parsed_open = _parse_positive_decimal(_record_value(record, "open"), "open")
            parsed_high = _parse_positive_decimal(_record_value(record, "high"), "high")
            parsed_low = _parse_positive_decimal(_record_value(record, "low"), "low")
            parsed_close = _parse_positive_decimal(_record_value(record, "close"), "close")
            parsed_adjusted_close = _parse_positive_decimal(
                _record_value(record, "adjusted_close"),
                "adjusted_close",
            )
            parsed_volume = _parse_non_negative_int(_record_value(record, "volume"))
        except ValidationError as exc:
            blockers.append(str(exc))
            continue

        if parsed_date in seen_dates:
            duplicate_dates = True
        seen_dates.add(parsed_date)
        rows.append(
            _NormalizedRow(
                symbol=parsed_symbol,
                date=parsed_date,
                open=parsed_open,
                high=parsed_high,
                low=parsed_low,
                close=parsed_close,
                adjusted_close=parsed_adjusted_close,
                volume=parsed_volume,
            )
        )

    if blockers:
        return _dedupe(blockers)
    if duplicate_dates:
        return ["duplicate_dates"]
    if not rows:
        return ["zero_valid_provider_rows"]
    return sorted(rows, key=lambda row: row.date)


def _read_fixture_records(path: Path | str) -> list[Mapping[str, object]]:
    fixture_path = Path(path)
    if not fixture_path.exists() or not fixture_path.is_file():
        raise ValidationError("fixture_input_path must exist.")
    suffix = fixture_path.suffix.lower()
    data = fixture_path.read_bytes()
    if suffix == ".json":
        return _read_provider_json_bytes(data)
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        raise ValidationError("fixture CSV is missing headers.")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        return [{"__duplicate_columns__": True}]
    return [dict(row) for row in reader]


def _read_provider_json_bytes(data: bytes) -> list[Mapping[str, object]]:
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("provider JSON response is malformed.") from exc
    if not isinstance(parsed, list):
        raise ValidationError("provider JSON response must be a list.")
    records: list[Mapping[str, object]] = []
    for item in parsed:
        if not isinstance(item, Mapping):
            raise ValidationError("provider JSON rows must be objects.")
        records.append(dict(item))
    return records


def _record_value(record: Mapping[str, object], canonical_field: str) -> object:
    for alias in _PROVIDER_FIELD_ALIASES[canonical_field]:
        if alias in record:
            value = record[alias]
            if isinstance(value, str):
                return value.strip()
            return value
    return None


def _parse_symbol(record: Mapping[str, object]) -> str:
    symbol_value = None
    for alias in _PROVIDER_FIELD_ALIASES["symbol"]:
        if alias in record:
            symbol_value = record[alias]
            break
    if symbol_value in (None, ""):
        return _SYMBOL
    if str(symbol_value).strip().upper() != _SYMBOL:
        raise ValidationError("symbol_scope_must_be_spy")
    return _SYMBOL


def _parse_provider_date(value: object) -> date:
    if value is None:
        raise ValidationError("missing_date")
    text = str(value).strip()
    if len(text) < 10 or text[4] != "-" or text[7] != "-":
        raise ValidationError("invalid_date")
    if len(text) > 10 and text[10] != "T":
        raise ValidationError("invalid_date")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValidationError("invalid_date") from exc


def _parse_positive_decimal(value: object, field_name: str) -> Decimal:
    if value in (None, ""):
        if field_name == "adjusted_close":
            raise ValidationError("missing_adjusted_close")
        raise ValidationError("missing_required_ohlcv")
    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation as exc:
        if field_name == "adjusted_close":
            raise ValidationError("invalid_adjusted_close") from exc
        raise ValidationError("invalid_ohlcv_values") from exc
    if not parsed.is_finite() or parsed <= 0:
        if field_name == "adjusted_close":
            raise ValidationError("nonpositive_adjusted_close")
        raise ValidationError("invalid_ohlcv_values")
    return parsed


def _parse_non_negative_int(value: object) -> int:
    if value in (None, ""):
        raise ValidationError("missing_required_ohlcv")
    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise ValidationError("invalid_ohlcv_values") from exc
    if parsed < 0:
        raise ValidationError("invalid_ohlcv_values")
    return parsed


def _canonical_csv_bytes(rows: Sequence[_NormalizedRow]) -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(_CANONICAL_COLUMNS)
    for row in rows:
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
    return stream.getvalue().encode("utf-8")


def _current_canonical_latest(path: Path | str) -> str:
    canonical_path = Path(path)
    if not canonical_path.exists():
        return ""
    text = canonical_path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None or "date" not in reader.fieldnames:
        raise ValidationError("current_canonical_date_column_missing")
    latest: date | None = None
    for row in reader:
        row_date = _parse_provider_date(row.get("date"))
        if latest is None or row_date > latest:
            latest = row_date
    return latest.isoformat() if latest is not None else ""


def _runtime_output_path(path: Path | str) -> bool:
    candidate = Path(path)
    parts = tuple(part.lower() for part in candidate.parts)
    if any(part in {"src", "tests", "scripts"} for part in parts):
        return False
    if candidate.is_absolute():
        return True
    return bool(parts) and parts[0] in {".data", "runs"}


def _config(value: object) -> SPYAdjustedDataRefreshConfig:
    if not isinstance(value, SPYAdjustedDataRefreshConfig):
        raise ValidationError("config must be an SPYAdjustedDataRefreshConfig.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
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


def _sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
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


def _string_sequence(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [str(item) for item in value if str(item)]


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m algotrader.execution.etf_sma_adjusted_spy_data_refresh"
    )
    parser.add_argument("--provider", choices=(_PROVIDER,), required=True)
    parser.add_argument("--expected-latest-bar-date", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--canonical-csv", required=True)
    parser.add_argument("--run-log", required=True)
    parser.add_argument("--mode", choices=_MODES, default=_DRY_RUN)
    parser.add_argument("--fixture-input-path", default=None)
    parser.add_argument("--raw-response-path", default=None)
    parser.add_argument(
        "--live-market-data-fetch-authorized",
        action="store_true",
        dest="live_fetch_authorized",
    )
    parser.add_argument("--start-date", default=_DEFAULT_START_DATE)
    parser.add_argument("--token-env-var", default=_TOKEN_ENV_VAR)
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
    )
    return parser


def _payload_exit_code(payload: Mapping[str, object]) -> int:
    state = str(payload.get("refresh_state", ""))
    if state.startswith("accepted") or state == "dry_run_refresh_plan_built":
        return 0
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = run_spy_adjusted_data_refresh(
            SPYAdjustedDataRefreshConfig(
                provider=args.provider,
                expected_latest_bar_date=args.expected_latest_bar_date,
                output_csv=args.output_csv,
                canonical_csv=args.canonical_csv,
                run_log=args.run_log,
                mode=args.mode,
                fixture_input_path=args.fixture_input_path,
                live_fetch_authorized=args.live_fetch_authorized,
                raw_response_path=args.raw_response_path,
                start_date=args.start_date,
                token_env_var=args.token_env_var,
            )
        )
    except ValidationError as exc:
        print(f"market_data_refresh_validation_error: {exc}", file=sys.stderr)
        return 2
    if args.output_format == "json":
        print(render_spy_adjusted_data_refresh_json(payload))
    else:
        print(render_spy_adjusted_data_refresh_text(payload))
    return _payload_exit_code(payload)


if __name__ == "__main__":
    raise SystemExit(main())
