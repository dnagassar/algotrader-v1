"""Guarded multi-symbol crypto OHLC history refresh adapter.

This module is a market-data boundary for the v5.19 crypto evidence battery.
Default modes are offline and deterministic. The market-data path is read-only
and requires explicit operator authorization before it can use the network.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import http.client
import json
import os
from pathlib import Path
from typing import Any, Protocol

from algotrader.errors import ValidationError
from algotrader.research.crypto_strategy_evidence_battery import (
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
    build_crypto_strategy_real_data_evidence_packet,
)

CRYPTO_HISTORY_REFRESH_ADAPTER_SCHEMA_VERSION = (
    "v5_19_4_crypto_history_refresh_adapter_v1"
)
CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH = Path(
    "runs/operator_input/crypto_paper_bars.csv"
)
CRYPTO_HISTORY_REFRESH_DEFAULT_PACKET_PATH = Path(
    "runs/crypto_history_refresh/latest/refresh_packet.json"
)
CRYPTO_HISTORY_REFRESH_DEFAULT_RAW_RESPONSE_PATH = Path(
    "runs/crypto_history_refresh/latest/raw_crypto_bars.json"
)
CRYPTO_HISTORY_REFRESH_MODES = ("dry_run", "offline_fixture", "market_data_fetch")
CRYPTO_HISTORY_REFRESH_CLASSIFICATIONS = (
    "dry_run_ready",
    "offline_fixture_ready",
    "market_data_refresh_ready",
    "market_data_refresh_not_configured",
    "rejected_live_endpoint_risk",
    "insufficient_real_crypto_history",
    "sufficient_real_crypto_history",
)

_DEFAULT_DATA_BASE_URL = "https://data.alpaca.markets"
_DEFAULT_LOC = "us"
_DEFAULT_TIMEFRAME = "1Hour"
_DEFAULT_LIMIT = 10000
_DEFAULT_HOURS = 240
_FIXTURE_ROWS_PER_SYMBOL = 80
_CSV_COLUMNS = (
    "timestamp",
    "symbol",
    "asset_class",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "basis",
    "source",
)
_KEY_ID_CANDIDATES = ("ALPACA_API_KEY", "ALPACA_API_KEY_ID", "APCA_API_KEY_ID")
_SECRET_KEY_CANDIDATES = (
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_SECRET_KEY",
)
_REQUIRED_BOOLEAN_PREFLIGHT_FIELDS = (
    "APP_PROFILE_is_paper",
    "ALPACA_API_KEY_loaded",
    "ALPACA_API_SECRET_KEY_loaded",
    "ALPACA_SECRET_KEY_loaded",
    "APCA_API_KEY_ID_loaded",
    "APCA_API_SECRET_KEY_loaded",
    "APCA_API_BASE_URL_is_live",
    "APCA_API_BASE_URL_is_paper",
)
_PUBLIC_ENDPOINT_NAMES = (
    "APP_PROFILE",
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
)
_SAFETY_FALSE_FIELDS = (
    "paper_submit_occurred",
    "broker_mutation_occurred",
    "broker_read_occurred",
    "live_endpoint_touched",
    "credential_values_exposed",
)
_FORBIDDEN_COMMAND_WORDS = (
    "submit",
    "cancel",
    "replace",
    "close",
    "liquidate",
)


class UrlOpen(Protocol):
    def __call__(self, request: _ReadOnlyHttpRequest, *, timeout: int) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class _ReadOnlyHttpRequest:
    full_url: str
    headers: Mapping[str, str]
    method: str = "GET"
    data: None = None

    def get_method(self) -> str:
        return self.method


class _HttpClientResponse:
    def __init__(
        self,
        connection: http.client.HTTPSConnection,
        response: http.client.HTTPResponse,
    ) -> None:
        self._connection = connection
        self._response = response

    def __enter__(self) -> _HttpClientResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self._response.close()
        self._connection.close()

    def read(self) -> bytes:
        return self._response.read()


class CryptoHistoryRefreshError(ValueError):
    """Raised for credential-redacted refresh failures."""


@dataclass(frozen=True, slots=True)
class AlpacaMarketDataCredentials:
    """Environment-sourced Alpaca market-data credentials."""

    api_key_id: str
    api_secret_key: str

    def __repr__(self) -> str:
        return (
            "AlpacaMarketDataCredentials("
            "api_key_id=<redacted>, api_secret_key=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class CryptoHistoryRefreshConfig:
    """Configuration for the guarded multi-symbol refresh adapter."""

    mode: str = "dry_run"
    symbols: tuple[str, ...] = DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
    output_path: Path | str = CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH
    packet_path: Path | str | None = CRYPTO_HISTORY_REFRESH_DEFAULT_PACKET_PATH
    raw_response_path: Path | str | None = (
        CRYPTO_HISTORY_REFRESH_DEFAULT_RAW_RESPONSE_PATH
    )
    fixture_input_path: Path | str | None = None
    as_of: datetime | str | None = None
    start: datetime | str | None = None
    end: datetime | str | None = None
    hours: int = _DEFAULT_HOURS
    timeframe: str = _DEFAULT_TIMEFRAME
    loc: str = _DEFAULT_LOC
    market_data_fetch_authorized: bool = False
    allow_network: bool = False
    write_packet: bool = True

    def __post_init__(self) -> None:
        mode = _required_text(self.mode, "mode")
        if mode not in CRYPTO_HISTORY_REFRESH_MODES:
            allowed = ",".join(CRYPTO_HISTORY_REFRESH_MODES)
            raise ValidationError(f"mode must be one of: {allowed}.")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "symbols", _symbol_tuple(self.symbols))
        object.__setattr__(
            self,
            "output_path",
            _path(self.output_path, "output_path"),
        )
        object.__setattr__(
            self,
            "packet_path",
            None
            if self.packet_path is None
            else _path(self.packet_path, "packet_path"),
        )
        object.__setattr__(
            self,
            "raw_response_path",
            None
            if self.raw_response_path is None
            else _path(self.raw_response_path, "raw_response_path"),
        )
        object.__setattr__(
            self,
            "fixture_input_path",
            None
            if self.fixture_input_path is None
            else _path(self.fixture_input_path, "fixture_input_path"),
        )
        object.__setattr__(self, "hours", _hours_value(self.hours))
        object.__setattr__(self, "timeframe", _timeframe_value(self.timeframe))
        object.__setattr__(self, "loc", _loc_value(self.loc))
        for field_name in (
            "market_data_fetch_authorized",
            "allow_network",
            "write_packet",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")


def run_crypto_history_refresh(
    config: CryptoHistoryRefreshConfig,
    *,
    env: Mapping[str, str] | None = None,
    opener: UrlOpen | None = None,
) -> dict[str, object]:
    """Build a guarded refresh packet and, when allowed, local CSV artifacts."""

    checked_config = _config(config)
    source_env = os.environ if env is None else env
    preflight = crypto_history_refresh_preflight(source_env)
    as_of = _as_of_datetime(checked_config.as_of)

    if preflight["live_endpoint_indicator"]:
        return _finish_packet(
            _base_packet(checked_config, preflight, as_of=as_of),
            classification="rejected_live_endpoint_risk",
            authorization_status="blocked_live_endpoint_risk",
            endpoint_safety_status="rejected_live_endpoint_risk",
            next_safe_operator_action=(
                "Clear APP_PROFILE=live or live Alpaca endpoint settings before "
                "any market-data refresh; no network call was attempted."
            ),
        )

    if checked_config.mode == "dry_run":
        return _finish_packet(
            _base_packet(checked_config, preflight, as_of=as_of),
            classification="dry_run_ready",
            authorization_status="not_required_for_dry_run",
            endpoint_safety_status="passed_non_live_endpoint_check",
            next_safe_operator_action=(
                "Review the generated read-only market-data command. Run it only "
                "with explicit operator authorization and paper-profile credentials."
            ),
        )

    if checked_config.mode == "offline_fixture":
        return _run_offline_fixture_mode(checked_config, preflight, as_of=as_of)

    return _run_market_data_fetch_mode(
        checked_config,
        preflight,
        as_of=as_of,
        env=source_env,
        opener=opener,
    )


def crypto_history_refresh_preflight(
    env: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    """Return boolean-only environment state for safe operator preflight."""

    source = os.environ if env is None else env
    app_profile = source.get("APP_PROFILE", "").strip().lower()
    apca_api_base_url = source.get("APCA_API_BASE_URL", "").strip().lower()
    result = {
        "APP_PROFILE_is_paper": app_profile == "paper",
        "APP_PROFILE_is_live": app_profile == "live",
        "ALPACA_API_KEY_loaded": _env_loaded(source, "ALPACA_API_KEY"),
        "ALPACA_API_KEY_ID_loaded": _env_loaded(source, "ALPACA_API_KEY_ID"),
        "ALPACA_API_SECRET_KEY_loaded": _env_loaded(source, "ALPACA_API_SECRET_KEY"),
        "ALPACA_SECRET_KEY_loaded": _env_loaded(source, "ALPACA_SECRET_KEY"),
        "APCA_API_KEY_ID_loaded": _env_loaded(source, "APCA_API_KEY_ID"),
        "APCA_API_SECRET_KEY_loaded": _env_loaded(source, "APCA_API_SECRET_KEY"),
        "APCA_API_BASE_URL_is_live": bool(
            apca_api_base_url
            and "api.alpaca.markets" in apca_api_base_url
            and "paper" not in apca_api_base_url
        ),
        "APCA_API_BASE_URL_is_paper": bool(
            apca_api_base_url
            and "paper-api.alpaca.markets" in apca_api_base_url
        ),
    }
    result["paper_credentials_present"] = _first_nonempty(source, _KEY_ID_CANDIDATES) != (
        ""
    ) and _first_nonempty(source, _SECRET_KEY_CANDIDATES) != ""
    result["live_endpoint_indicator"] = _live_endpoint_indicator(source)
    return result


def build_crypto_history_refresh_url(
    *,
    api_symbol: str,
    start: datetime,
    end: datetime,
    timeframe: str = _DEFAULT_TIMEFRAME,
    loc: str = _DEFAULT_LOC,
    limit: int = _DEFAULT_LIMIT,
    page_token: str = "",
    base_url: str = _DEFAULT_DATA_BASE_URL,
) -> str:
    """Build the Alpaca v1beta3 read-only crypto bars URL."""

    checked_symbol = _api_symbol(api_symbol)
    checked_start = _aware_utc_datetime(start, "start")
    checked_end = _aware_utc_datetime(end, "end")
    query_items = [
        ("symbols", checked_symbol),
        ("timeframe", _timeframe_value(timeframe)),
        ("start", checked_start.isoformat().replace("+00:00", "Z")),
        ("end", checked_end.isoformat().replace("+00:00", "Z")),
        ("limit", str(_limit_value(limit))),
        ("sort", "asc"),
    ]
    if page_token:
        query_items.append(("page_token", _required_text(page_token, "page_token")))
    path = f"/v1beta3/crypto/{_loc_value(loc)}/bars"
    return f"{base_url.rstrip('/')}{path}?{_urlencode(query_items)}"


def fetch_crypto_history_from_alpaca_market_data(
    *,
    symbols: Sequence[str],
    start: datetime,
    end: datetime,
    credentials: AlpacaMarketDataCredentials,
    allow_network: bool,
    market_data_fetch_authorized: bool,
    opener: UrlOpen | None = None,
    timeout: int = 30,
    timeframe: str = _DEFAULT_TIMEFRAME,
    loc: str = _DEFAULT_LOC,
) -> dict[str, object]:
    """Fetch read-only market-data bars for the requested crypto symbols."""

    if not allow_network or not market_data_fetch_authorized:
        raise CryptoHistoryRefreshError(
            "market-data refresh requires --allow-network and "
            "--market-data-fetch-authorized."
        )

    checked_symbols = _symbol_tuple(symbols)
    checked_start = _aware_utc_datetime(start, "start")
    checked_end = _aware_utc_datetime(end, "end")
    if checked_start >= checked_end:
        raise CryptoHistoryRefreshError("start must be before end.")

    urlopen = _open_read_only_https_request if opener is None else opener
    bars_by_api_symbol: dict[str, list[object]] = {}
    for symbol in checked_symbols:
        api_symbol = _api_symbol(symbol)
        bars_by_api_symbol[api_symbol] = []
        page_token = ""
        seen_page_tokens: set[str] = set()
        while True:
            url = build_crypto_history_refresh_url(
                api_symbol=api_symbol,
                start=checked_start,
                end=checked_end,
                timeframe=timeframe,
                loc=loc,
                page_token=page_token,
            )
            request = _ReadOnlyHttpRequest(
                full_url=url,
                headers={
                    "APCA-API-KEY-ID": credentials.api_key_id,
                    "APCA-API-SECRET-KEY": credentials.api_secret_key,
                    "Accept": "application/json",
                },
                method="GET",
            )
            try:
                with urlopen(request, timeout=timeout) as response:
                    response_bytes = response.read()
            except (
                OSError,
                RuntimeError,
                http.client.HTTPException,
            ) as exc:
                raise CryptoHistoryRefreshError(
                    _sanitized_exception_message(exc, credentials)
                ) from exc

            try:
                payload = json.loads(response_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CryptoHistoryRefreshError(
                    "Alpaca crypto bars response was not valid JSON."
                ) from exc

            bars_by_api_symbol[api_symbol].extend(
                _bar_items_from_payload(payload, api_symbol)
            )
            next_page_token = _next_page_token(payload)
            if not next_page_token:
                break
            if next_page_token in seen_page_tokens:
                raise CryptoHistoryRefreshError(
                    "Alpaca crypto bars pagination repeated a token."
                )
            seen_page_tokens.add(next_page_token)
            page_token = next_page_token

    return {
        "bars": bars_by_api_symbol,
        "source": "alpaca_market_data_crypto_bars_v1beta3",
        "loc": loc,
        "timeframe": timeframe,
        "sort": "asc",
    }


def _open_read_only_https_request(
    request: _ReadOnlyHttpRequest,
    *,
    timeout: int,
) -> _HttpClientResponse:
    expected_prefix = f"{_DEFAULT_DATA_BASE_URL}/"
    if not request.full_url.startswith(expected_prefix):
        raise CryptoHistoryRefreshError("market-data URL scope violation.")
    request_target = request.full_url[len(_DEFAULT_DATA_BASE_URL) :]
    connection = http.client.HTTPSConnection("data.alpaca.markets", timeout=timeout)
    try:
        connection.request(
            request.get_method(),
            request_target,
            body=request.data,
            headers=dict(request.headers),
        )
        response = connection.getresponse()
        status = int(response.status)
        if status < 200 or status >= 300:
            response.read()
            raise OSError(
                f"Alpaca market-data HTTP status failure: {status}."
            )
        return _HttpClientResponse(connection, response)
    except (
        OSError,
        RuntimeError,
        http.client.HTTPException,
    ):
        connection.close()
        raise


def _urlencode(items: Sequence[tuple[str, str]]) -> str:
    return "&".join(
        f"{_quote_plus(key)}={_quote_plus(value)}"
        for key, value in items
    )


def _quote_plus(value: str) -> str:
    encoded: list[str] = []
    for byte in value.encode("utf-8"):
        if (
            65 <= byte <= 90
            or 97 <= byte <= 122
            or 48 <= byte <= 57
            or byte in b"-._~"
        ):
            encoded.append(chr(byte))
        elif byte == 32:
            encoded.append("+")
        else:
            encoded.append(f"%{byte:02X}")
    return "".join(encoded)


def read_market_data_credentials_from_env(
    env: Mapping[str, str] | None = None,
) -> AlpacaMarketDataCredentials:
    """Read credentials from environment variables without exposing values."""

    source = os.environ if env is None else env
    key_id = _first_nonempty(source, _KEY_ID_CANDIDATES)
    secret_key = _first_nonempty(source, _SECRET_KEY_CANDIDATES)
    missing: list[str] = []
    if not key_id:
        missing.append("alpaca_api_key")
    if not secret_key:
        missing.append("alpaca_api_secret")
    if missing:
        raise CryptoHistoryRefreshError(
            "missing required Alpaca credential environment variable(s): "
            + ",".join(missing)
        )
    return AlpacaMarketDataCredentials(key_id, secret_key)


def render_crypto_history_refresh_json(packet: Mapping[str, object]) -> str:
    """Render a refresh packet as deterministic compact JSON."""

    return json.dumps(_json_safe(dict(packet)), sort_keys=True, separators=(",", ":"))


def render_crypto_history_refresh_text(packet: Mapping[str, object]) -> str:
    """Render a compact operator-facing refresh summary."""

    return "\n".join(
        (
            "crypto_history_refresh_command=refresh_multi_symbol_crypto_history",
            f"classification={packet.get('classification', '')}",
            f"mode={packet.get('mode', '')}",
            f"requested_symbols={','.join(_string_sequence(packet.get('requested_symbols')))}",
            f"fetched_symbols={','.join(_string_sequence(packet.get('fetched_symbols')))}",
            f"output_path={packet.get('output_path', '')}",
            f"data_source={packet.get('data_source', '')}",
            f"authorization_status={packet.get('authorization_status', '')}",
            f"endpoint_safety_status={packet.get('endpoint_safety_status', '')}",
            f"schema_validation_status={packet.get('schema_validation_status', '')}",
            f"coverage_gate_classification={packet.get('coverage_gate_classification', '')}",
            f"paper_planning_eligibility={packet.get('paper_planning_eligibility', '')}",
            f"market_data_fetch_occurred={_bool_text(packet.get('market_data_fetch_occurred'))}",
            f"broker_mutation_occurred={_bool_text(packet.get('broker_mutation_occurred'))}",
            f"paper_submit_occurred={_bool_text(packet.get('paper_submit_occurred'))}",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a guarded multi-symbol crypto OHLC history refresh packet.",
    )
    parser.add_argument("--mode", choices=CRYPTO_HISTORY_REFRESH_MODES, default="dry_run")
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS),
    )
    parser.add_argument(
        "--output-path",
        default=str(CRYPTO_HISTORY_REFRESH_DEFAULT_OUTPUT_PATH),
    )
    parser.add_argument(
        "--packet-path",
        default=str(CRYPTO_HISTORY_REFRESH_DEFAULT_PACKET_PATH),
    )
    parser.add_argument(
        "--raw-response-path",
        default=str(CRYPTO_HISTORY_REFRESH_DEFAULT_RAW_RESPONSE_PATH),
    )
    parser.add_argument("--fixture-input-path", default="")
    parser.add_argument("--as-of", default="")
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    parser.add_argument("--hours", type=int, default=_DEFAULT_HOURS)
    parser.add_argument("--timeframe", default=_DEFAULT_TIMEFRAME)
    parser.add_argument("--loc", default=_DEFAULT_LOC)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--market-data-fetch-authorized", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        packet = run_crypto_history_refresh(
            CryptoHistoryRefreshConfig(
                mode=args.mode,
                symbols=_split_symbols(args.symbols),
                output_path=args.output_path,
                packet_path=args.packet_path,
                raw_response_path=args.raw_response_path,
                fixture_input_path=args.fixture_input_path or None,
                as_of=args.as_of or None,
                start=args.start or None,
                end=args.end or None,
                hours=args.hours,
                timeframe=args.timeframe,
                loc=args.loc,
                allow_network=args.allow_network,
                market_data_fetch_authorized=args.market_data_fetch_authorized,
            )
        )
    except (CryptoHistoryRefreshError, ValidationError) as exc:
        print(str(exc))
        return 2

    if args.format == "json":
        print(json.dumps(packet, indent=2, sort_keys=True))
    else:
        print(render_crypto_history_refresh_text(packet))

    return 2 if packet.get("classification") == "rejected_live_endpoint_risk" else 0


def _run_offline_fixture_mode(
    config: CryptoHistoryRefreshConfig,
    preflight: Mapping[str, bool],
    *,
    as_of: datetime,
) -> dict[str, object]:
    packet = _base_packet(config, preflight, as_of=as_of)
    if config.fixture_input_path is None:
        _write_history_csv(
            config.output_path,
            _offline_fixture_rows(config.symbols, as_of=as_of),
            source="offline_fixture",
        )
        input_path = config.output_path
    else:
        _copy_file(config.fixture_input_path, config.output_path)
        input_path = config.output_path

    coverage = build_crypto_strategy_real_data_evidence_packet(
        input_path,
        as_of=as_of,
        data_source="offline_fixture",
        data_freshness="offline_fixture_snapshot",
    )
    packet = _overlay_coverage(packet, coverage)
    blocking_reasons = _string_sequence(
        _mapping(coverage.get("data_inventory")).get("blocking_reasons")
    )
    only_fixture_blocked = set(blocking_reasons).issubset({"fixture_only_history"})
    classification = (
        "offline_fixture_ready"
        if only_fixture_blocked
        else "insufficient_real_crypto_history"
    )
    return _finish_packet(
        packet,
        classification=classification,
        authorization_status="not_required_for_offline_fixture",
        endpoint_safety_status="passed_non_live_endpoint_check",
        data_source="offline_fixture",
        next_safe_operator_action=(
            "Use this fixture output only for parser and coverage-gate rehearsal; "
            "refresh real local crypto history before any paper-planning milestone."
        ),
    )


def _run_market_data_fetch_mode(
    config: CryptoHistoryRefreshConfig,
    preflight: Mapping[str, bool],
    *,
    as_of: datetime,
    env: Mapping[str, str],
    opener: UrlOpen | None,
) -> dict[str, object]:
    packet = _base_packet(config, preflight, as_of=as_of)
    readiness_errors = _market_data_readiness_errors(config, preflight)
    if readiness_errors:
        return _finish_packet(
            packet,
            classification="market_data_refresh_not_configured",
            authorization_status="blocked_" + ",".join(readiness_errors),
            endpoint_safety_status="passed_non_live_endpoint_check",
            data_source="alpaca_market_data_crypto_bars_v1beta3",
            next_safe_operator_action=(
                "Set APP_PROFILE=paper, load paper market-data credentials, use "
                "a non-live endpoint, and rerun with explicit market-data "
                "authorization."
            ),
        )

    end = _as_of_datetime(config.end) if config.end is not None else as_of
    start = (
        _as_of_datetime(config.start)
        if config.start is not None
        else end - timedelta(hours=config.hours)
    )
    credentials = read_market_data_credentials_from_env(env)
    raw_payload = fetch_crypto_history_from_alpaca_market_data(
        symbols=config.symbols,
        start=start,
        end=end,
        credentials=credentials,
        allow_network=config.allow_network,
        market_data_fetch_authorized=config.market_data_fetch_authorized,
        opener=opener,
        timeframe=config.timeframe,
        loc=config.loc,
    )
    if config.raw_response_path is not None:
        _write_json(config.raw_response_path, raw_payload)

    rows = _history_rows_from_raw_payload(raw_payload)
    _write_history_csv(
        config.output_path,
        rows,
        source="alpaca_market_data_crypto_bars_v1beta3",
    )
    coverage = build_crypto_strategy_real_data_evidence_packet(
        config.output_path,
        as_of=as_of,
        data_source="alpaca_market_data_crypto_bars_v1beta3",
        data_freshness="operator_refreshed_market_data_snapshot",
        normalized_output_path=config.output_path,
    )
    packet = _overlay_coverage(packet, coverage)
    packet["market_data_fetch_occurred"] = True
    packet["network_access_attempted"] = True
    coverage_classification = str(
        packet.get("coverage_gate_classification", "insufficient_real_crypto_history")
    )
    return _finish_packet(
        packet,
        classification=coverage_classification,
        authorization_status="authorized",
        endpoint_safety_status="passed_non_live_endpoint_check",
        data_source="alpaca_market_data_crypto_bars_v1beta3",
        next_safe_operator_action=_coverage_next_action(coverage_classification),
    )


def _base_packet(
    config: CryptoHistoryRefreshConfig,
    preflight: Mapping[str, bool],
    *,
    as_of: datetime,
) -> dict[str, object]:
    packet: dict[str, object] = {
        "schema_version": CRYPTO_HISTORY_REFRESH_ADAPTER_SCHEMA_VERSION,
        "record_type": "crypto_history_refresh_adapter_packet",
        "classification": "",
        "classification_vocabulary": list(CRYPTO_HISTORY_REFRESH_CLASSIFICATIONS),
        "mode": config.mode,
        "requested_symbols": list(config.symbols),
        "fetched_symbols": [],
        "output_path": str(config.output_path),
        "packet_path": "" if config.packet_path is None else str(config.packet_path),
        "raw_response_path": ""
        if config.raw_response_path is None
        else str(config.raw_response_path),
        "write_packet": config.write_packet,
        "data_source": "none",
        "as_of": as_of.isoformat(),
        "authorization_status": "",
        "endpoint_safety_status": "",
        "operator_preflight": {
            field: bool(preflight.get(field, False))
            for field in sorted(preflight)
        },
        "live_endpoint_indicator": bool(preflight.get("live_endpoint_indicator")),
        "required_boolean_preflight_fields": list(_REQUIRED_BOOLEAN_PREFLIGHT_FIELDS),
        "generated_command_text": _generated_market_data_command(config),
        "generated_command_safety_status": "passed",
        "rows_per_symbol": {},
        "rows_per_symbol_before_normalization": {},
        "rows_per_symbol_after_normalization": {},
        "date_range_per_symbol": {},
        "missing_symbols": list(config.symbols),
        "schema_validation_status": "not_checked",
        "duplicate_timestamp_status": "not_checked",
        "duplicate_timestamp_status_after_normalization": "not_checked",
        "duplicate_rows_removed_per_symbol": {},
        "coverage_gate_classification": "insufficient_real_crypto_history",
        "coverage_gate_blocking_reasons": [],
        "coverage_gate_reason": "",
        "paper_planning_eligibility": "not_eligible",
        "paper_planning_promotion_allowed": False,
        "market_data_fetch_occurred": False,
        "network_access_attempted": False,
        "broker_mutation_authorized": False,
        "paper_submit_authorized": False,
        "live_authorized": False,
        "next_safe_operator_action": "",
        "labels": [
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "profit_claim": "none",
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        packet[field_name] = False
    return packet


def _finish_packet(
    packet: dict[str, object],
    *,
    classification: str,
    authorization_status: str,
    endpoint_safety_status: str,
    next_safe_operator_action: str,
    data_source: str | None = None,
) -> dict[str, object]:
    if classification not in CRYPTO_HISTORY_REFRESH_CLASSIFICATIONS:
        raise ValidationError("unknown refresh classification.")
    packet["classification"] = classification
    packet["authorization_status"] = authorization_status
    packet["endpoint_safety_status"] = endpoint_safety_status
    if data_source is not None:
        packet["data_source"] = data_source
    packet["next_safe_operator_action"] = next_safe_operator_action
    if _command_contains_forbidden_word(str(packet.get("generated_command_text", ""))):
        packet["generated_command_safety_status"] = "failed"
    if packet.get("write_packet") is False:
        return packet
    packet_path = str(packet.get("packet_path", "")).strip()
    if packet_path:
        _write_json(Path(packet_path), packet)
    return packet


def _overlay_coverage(
    packet: dict[str, object],
    coverage: Mapping[str, object],
) -> dict[str, object]:
    data_inventory = _mapping(coverage.get("data_inventory"))
    symbols_found = _string_sequence(coverage.get("symbols_found"))
    packet["fetched_symbols"] = list(symbols_found)
    packet["rows_per_symbol"] = dict(_mapping(coverage.get("rows_per_symbol")))
    packet["rows_per_symbol_before_normalization"] = dict(
        _mapping(coverage.get("rows_per_symbol_before_normalization"))
    )
    packet["rows_per_symbol_after_normalization"] = dict(
        _mapping(coverage.get("rows_per_symbol_after_normalization"))
    )
    packet["date_range_per_symbol"] = dict(
        _mapping(coverage.get("date_range_per_symbol"))
    )
    packet["missing_symbols"] = list(_string_sequence(coverage.get("symbols_missing")))
    packet["schema_validation_status"] = str(
        coverage.get("schema_validation_status", "not_checked")
    )
    packet["duplicate_timestamp_status"] = str(
        coverage.get("duplicate_timestamp_status", "not_checked")
    )
    packet["duplicate_timestamp_status_after_normalization"] = str(
        coverage.get("duplicate_timestamp_status_after_normalization", "not_checked")
    )
    packet["duplicate_rows_removed_per_symbol"] = dict(
        _mapping(coverage.get("duplicate_rows_removed_per_symbol"))
    )
    packet["coverage_gate_classification"] = str(
        coverage.get("classification", "insufficient_real_crypto_history")
    )
    packet["coverage_gate_blocking_reasons"] = list(
        _string_sequence(data_inventory.get("blocking_reasons"))
    )
    packet["coverage_gate_reason"] = str(coverage.get("reason_for_classification", ""))
    packet["paper_planning_eligibility"] = str(
        coverage.get("paper_planning_eligibility", "not_eligible")
    )
    packet["paper_planning_promotion_allowed"] = (
        packet["paper_planning_eligibility"] == "eligible"
    )
    return packet


def _market_data_readiness_errors(
    config: CryptoHistoryRefreshConfig,
    preflight: Mapping[str, bool],
) -> list[str]:
    errors: list[str] = []
    if not preflight.get("APP_PROFILE_is_paper", False):
        errors.append("paper_profile_required")
    if not preflight.get("paper_credentials_present", False):
        errors.append("paper_credentials_required")
    if preflight.get("APCA_API_BASE_URL_is_live", False):
        errors.append("apca_live_base_url_rejected")
    if not preflight.get("APCA_API_BASE_URL_is_paper", False):
        errors.append("apca_paper_base_url_required")
    if not config.market_data_fetch_authorized:
        errors.append("authorization_flag_required")
    if not config.allow_network:
        errors.append("allow_network_required")
    return errors


def _offline_fixture_rows(
    symbols: Sequence[str],
    *,
    as_of: datetime,
) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    first = as_of - timedelta(hours=_FIXTURE_ROWS_PER_SYMBOL - 1)
    for symbol_index, symbol in enumerate(_symbol_tuple(symbols)):
        if symbol == "ADAUSD":
            start_price = Decimal("1") + Decimal(symbol_index) / Decimal("10")
            step = Decimal("0.01")
        else:
            start_price = Decimal("100") + Decimal(symbol_index * 100)
            step = Decimal("1")
        for row_index in range(_FIXTURE_ROWS_PER_SYMBOL):
            close = start_price + (step * Decimal(row_index))
            timestamp = first + timedelta(hours=row_index)
            rows.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "symbol": symbol,
                    "open": _decimal_text(close),
                    "high": _decimal_text(close + step),
                    "low": _decimal_text(max(close - step, Decimal("0.00000001"))),
                    "close": _decimal_text(close),
                    "volume": "1",
                }
            )
    return tuple(rows)


def _history_rows_from_raw_payload(
    payload: Mapping[str, object],
) -> tuple[dict[str, str], ...]:
    bars = payload.get("bars")
    if not isinstance(bars, Mapping):
        raise CryptoHistoryRefreshError("raw market-data payload must include bars.")
    rows: list[dict[str, str]] = []
    for api_symbol, values in bars.items():
        symbol = _symbol(str(api_symbol))
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise CryptoHistoryRefreshError("market-data bars must be lists.")
        for item in values:
            if not isinstance(item, Mapping):
                raise CryptoHistoryRefreshError("market-data bar must be an object.")
            rows.append(
                {
                    "timestamp": _first_text(item, "timestamp", "t"),
                    "symbol": symbol,
                    "open": _first_text(item, "open", "o"),
                    "high": _first_text(item, "high", "h"),
                    "low": _first_text(item, "low", "l"),
                    "close": _first_text(item, "close", "c"),
                    "volume": _first_text(item, "volume", "v") or "0",
                }
            )
    return tuple(rows)


def _write_history_csv(
    output_path: Path,
    rows: Sequence[Mapping[str, str]],
    *,
    source: str,
) -> None:
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "timestamp": row["timestamp"],
                    "symbol": _symbol(row["symbol"]),
                    "asset_class": "crypto",
                    "open": _decimal_text(_decimal(row["open"], "open")),
                    "high": _decimal_text(_decimal(row["high"], "high")),
                    "low": _decimal_text(_decimal(row["low"], "low")),
                    "close": _decimal_text(_decimal(row["close"], "close")),
                    "volume": _decimal_text(_decimal(row.get("volume", "0"), "volume")),
                    "basis": "alpaca_crypto_bars_v1beta3_ohlcv",
                    "source": source,
                }
            )


def _generated_market_data_command(config: CryptoHistoryRefreshConfig) -> str:
    parts = [
        r".\scripts\refresh_multi_symbol_crypto_history.ps1",
        "-Mode",
        "market_data_fetch",
        "-Symbols",
        ",".join(config.symbols),
        "-OutputPath",
        str(config.output_path),
        "-MarketDataFetchAuthorized",
    ]
    if config.as_of is not None:
        parts.extend(("-AsOfTimestamp", _datetime_arg(config.as_of)))
    if config.start is not None:
        parts.extend(("-Start", _datetime_arg(config.start)))
    if config.end is not None:
        parts.extend(("-End", _datetime_arg(config.end)))
    if config.hours != _DEFAULT_HOURS:
        parts.extend(("-Hours", str(config.hours)))
    return " ".join(_powershell_quote(part) for part in parts)


def _command_contains_forbidden_word(command_text: str) -> bool:
    lowered = command_text.lower()
    return any(word in lowered for word in _FORBIDDEN_COMMAND_WORDS)


def _coverage_next_action(classification: str) -> str:
    if classification == "sufficient_real_crypto_history":
        return (
            "Review the v5.19 evidence packet offline. This refresh does not "
            "authorize paper planning or broker mutation."
        )
    return (
        "Refresh or add missing local OHLC history for BTCUSD, ETHUSD, SOLUSD, "
        "and ADAUSD, then rerun the evidence battery."
    )


def _bar_items_from_payload(payload: object, api_symbol: str) -> tuple[object, ...]:
    if not isinstance(payload, Mapping):
        raise CryptoHistoryRefreshError("Alpaca crypto bars response must be an object.")
    bars = payload.get("bars")
    if isinstance(bars, list):
        return tuple(bars)
    if isinstance(bars, Mapping):
        wanted = _symbol(api_symbol)
        for key, value in bars.items():
            if _symbol(str(key)) == wanted:
                if not isinstance(value, list):
                    raise CryptoHistoryRefreshError("crypto symbol bars must be a list.")
                return tuple(value)
    raise CryptoHistoryRefreshError(f"Alpaca response missing bars for {_symbol(api_symbol)}.")


def _next_page_token(payload: object) -> str:
    if not isinstance(payload, Mapping):
        return ""
    value = payload.get("next_page_token")
    return "" if value in (None, "") else str(value).strip()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_crypto_history_refresh_json(payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _copy_file(source: Path, destination: Path) -> None:
    if destination.parent != Path("."):
        destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def _sanitized_exception_message(
    exc: Exception,
    credentials: AlpacaMarketDataCredentials,
) -> str:
    message = str(exc)
    for secret in (credentials.api_key_id, credentials.api_secret_key):
        if secret:
            message = message.replace(secret, "<redacted>")
    return f"Alpaca market-data crypto history fetch failed: {message}"


def _first_nonempty(source: Mapping[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = source.get(name, "").strip()
        if value:
            return value
    return ""


def _env_loaded(source: Mapping[str, str], name: str) -> bool:
    return bool(source.get(name, "").strip())


def _live_endpoint_indicator(source: Mapping[str, str]) -> bool:
    for name in _PUBLIC_ENDPOINT_NAMES:
        value = source.get(name, "").strip().lower()
        if name == "APP_PROFILE" and value == "live":
            return True
        if value and "api.alpaca.markets" in value and "paper" not in value:
            return True
    return False


def _config(value: object) -> CryptoHistoryRefreshConfig:
    if not isinstance(value, CryptoHistoryRefreshConfig):
        raise ValidationError("config must be a CryptoHistoryRefreshConfig.")
    return value


def _path(value: object, field_name: str) -> Path:
    if isinstance(value, Path):
        return value
    if type(value) is str and value.strip():
        return Path(value.strip())
    raise ValidationError(f"{field_name} must be a filesystem path.")


def _split_symbols(value: str) -> tuple[str, ...]:
    return _symbol_tuple(part for part in value.split(",") if part.strip())


def _symbol_tuple(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError("symbols must be a sequence of symbol strings.")
    symbols = tuple(_symbol(value) for value in values)
    if not symbols:
        raise ValidationError("symbols must not be empty.")
    if len(set(symbols)) != len(symbols):
        raise ValidationError("symbols must not contain duplicates.")
    return symbols


def _symbol(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("symbol must be a string.")
    normalized = "".join(ch for ch in value.upper().strip() if ch.isalnum())
    if not normalized:
        raise ValidationError("symbol must be non-empty.")
    return normalized


def _api_symbol(value: str) -> str:
    symbol = _symbol(value)
    if not symbol.endswith("USD") or len(symbol) <= 3:
        raise ValidationError("crypto symbol must be a USD pair.")
    return f"{symbol[:-3]}/USD"


def _loc_value(value: object) -> str:
    if type(value) is not str or value.strip() not in {"us", "us-1", "us-2", "eu-1", "bs-1"}:
        raise ValidationError("loc must be an allowed Alpaca crypto location.")
    return value.strip()


def _timeframe_value(value: object) -> str:
    allowed = {"1Min", "5Min", "15Min", "1Hour", "1Day"}
    if type(value) is not str or value.strip() not in allowed:
        raise ValidationError("timeframe is not allowed for this refresh.")
    return value.strip()


def _limit_value(value: object) -> int:
    if type(value) is not int or value < 1 or value > _DEFAULT_LIMIT:
        raise ValidationError("limit must be between 1 and 10000.")
    return value


def _hours_value(value: object) -> int:
    if type(value) is not int or value < 80 or value > 24 * 365:
        raise ValidationError("hours must be an integer between 80 and 8760.")
    return value


def _as_of_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(UTC).replace(microsecond=0)
    return _datetime_value(value, "as_of")


def _datetime_arg(value: datetime | str) -> str:
    return _datetime_value(value, "timestamp").isoformat()


def _datetime_value(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO timestamp.") from exc
    else:
        raise ValidationError(f"{field_name} must be an ISO timestamp.")
    return _aware_utc_datetime(parsed, field_name)


def _aware_utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or type(value) is not datetime:
        raise ValidationError(f"{field_name} must be a datetime.")
    if value.tzinfo is None:
        raise ValidationError(f"{field_name} must include timezone information.")
    return value.astimezone(UTC)


def _required_text(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    wanted = {field.lower() for field in field_names}
    for key, value in row.items():
        if str(key).strip().lower() in wanted:
            return "" if value is None else str(value).strip()
    return ""


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be decimal text.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    if parsed < Decimal("0"):
        raise ValidationError(f"{field_name} must be non-negative.")
    return parsed


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _powershell_quote(value: str) -> str:
    if not value:
        return "''"
    if all(ch.isalnum() or ch in r".\:,_/-" for ch in value):
        return value
    return "'" + value.replace("'", "''") + "'"


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
