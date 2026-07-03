"""Fetch read-only Alpaca crypto bars and run deterministic BTCUSD intake.

This script is a broker/provider boundary for operator-run market-data refreshes.
It never submits, cancels, replaces, closes, or liquidates orders.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from algotrader.errors import ValidationError
from algotrader.execution.crypto_bars_intake import (
    CRYPTO_BARS_INTAKE_DEFAULT_CANONICAL_CSV,
    CRYPTO_BARS_INTAKE_DEFAULT_RAW_RESPONSE_PATH,
    CRYPTO_BARS_INTAKE_DEFAULT_RUN_LOG,
    CRYPTO_BARS_INTAKE_DEFAULT_SYMBOL,
    CryptoBarsIntakeConfig,
    render_crypto_bars_intake_json,
    render_crypto_bars_intake_text,
    run_crypto_bars_intake,
)

_DEFAULT_DATA_BASE_URL = "https://data.alpaca.markets"
_DEFAULT_LOC = "us"
_DEFAULT_TIMEFRAME = "1Hour"
_DEFAULT_LIMIT = 10000
_DEFAULT_HOURS = 80
_KEY_ID_CANDIDATES = ("ALPACA_API_KEY", "APCA_API_KEY_ID", "ALPACA_API_KEY_ID")
_SECRET_KEY_CANDIDATES = (
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_SECRET_KEY",
)
_PUBLIC_ENV_NAMES = (
    "APP_PROFILE",
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
)

class UrlOpen(Protocol):
    def __call__(self, request: urllib.request.Request, *, timeout: int) -> Any:
        ...



class CryptoBarsFetchError(ValueError):
    """Raised for credential-redacted crypto bars fetch failures."""


class AlpacaCredentials:
    """Environment-sourced Alpaca credentials with redacted representation."""

    __slots__ = ("api_key_id", "api_secret_key")

    def __init__(self, api_key_id: str, api_secret_key: str) -> None:
        self.api_key_id = api_key_id
        self.api_secret_key = api_secret_key

    def __repr__(self) -> str:
        return "AlpacaCredentials(api_key_id=<redacted>, api_secret_key=<redacted>)"


def read_credentials_from_env(env: Mapping[str, str] | None = None) -> AlpacaCredentials:
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
        raise CryptoBarsFetchError(
            "missing required Alpaca credential environment variable(s): "
            + ",".join(missing)
        )
    return AlpacaCredentials(key_id, secret_key)


def crypto_market_data_preflight(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    """Return boolean-only environment state for the read-only fetch boundary."""

    source = os.environ if env is None else env
    app_profile = source.get("APP_PROFILE", "").strip().lower()
    credential_state = {
        f"{name}_present": bool(source.get(name, "").strip())
        for name in (*_KEY_ID_CANDIDATES, *_SECRET_KEY_CANDIDATES)
    }
    return {
        "APP_PROFILE_is_paper": app_profile == "paper",
        "APP_PROFILE_is_live": app_profile == "live",
        **credential_state,
        "paper_credentials_present": bool(_first_nonempty(source, _KEY_ID_CANDIDATES))
        and bool(_first_nonempty(source, _SECRET_KEY_CANDIDATES)),
        "live_endpoint_indicator": _live_endpoint_indicator(source),
    }


def build_crypto_bars_url(
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
    """Build the Alpaca v1beta3 crypto historical bars URL."""

    checked_loc = _loc_value(loc)
    checked_timeframe = _timeframe_value(timeframe)
    checked_limit = _limit_value(limit)
    query_items = [
        ("symbols", _api_symbol_value(api_symbol)),
        ("timeframe", checked_timeframe),
        ("start", _utc_datetime(start, "start").isoformat().replace("+00:00", "Z")),
        ("end", _utc_datetime(end, "end").isoformat().replace("+00:00", "Z")),
        ("limit", str(checked_limit)),
        ("sort", "asc"),
    ]
    if page_token:
        query_items.append(("page_token", _page_token_value(page_token)))
    path = f"/v1beta3/crypto/{checked_loc}/bars"
    return f"{base_url.rstrip('/')}{path}?{urllib.parse.urlencode(query_items)}"


def fetch_alpaca_crypto_bars(
    *,
    api_symbol: str,
    start: datetime,
    end: datetime,
    credentials: AlpacaCredentials,
    allow_network: bool = False,
    market_data_fetch_authorized: bool = False,
    opener: UrlOpen | None = None,
    timeout: int = 30,
    timeframe: str = _DEFAULT_TIMEFRAME,
    loc: str = _DEFAULT_LOC,
    limit: int = _DEFAULT_LIMIT,
    base_url: str = _DEFAULT_DATA_BASE_URL,
) -> dict[str, object]:
    """Fetch Alpaca crypto bars using only the read-only market-data endpoint."""

    if not allow_network or not market_data_fetch_authorized:
        raise CryptoBarsFetchError(
            "read-only market-data fetch requires --allow-network and "
            "--market-data-fetch-authorized."
        )
    checked_symbol = _api_symbol_value(api_symbol)
    checked_start = _utc_datetime(start, "start")
    checked_end = _utc_datetime(end, "end")
    if checked_start >= checked_end:
        raise CryptoBarsFetchError("start must be before end.")

    bar_items: list[object] = []
    page_token = ""
    seen_page_tokens: set[str] = set()
    urlopen = urllib.request.urlopen if opener is None else opener
    while True:
        url = build_crypto_bars_url(
            api_symbol=checked_symbol,
            start=checked_start,
            end=checked_end,
            timeframe=timeframe,
            loc=loc,
            limit=limit,
            page_token=page_token,
            base_url=base_url,
        )
        request = urllib.request.Request(
            url,
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
        except (OSError, urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
            raise CryptoBarsFetchError(_sanitized_exception_message(exc, credentials)) from exc

        try:
            payload = json.loads(response_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CryptoBarsFetchError("Alpaca crypto bars response was not valid JSON.") from exc

        bar_items.extend(_bar_items_from_payload(payload, checked_symbol))
        next_page_token = _next_page_token(payload)
        if not next_page_token:
            break
        if next_page_token in seen_page_tokens:
            raise CryptoBarsFetchError("Alpaca crypto bars pagination repeated a token.")
        seen_page_tokens.add(next_page_token)
        page_token = next_page_token

    return {
        "bars": {checked_symbol: bar_items},
        "source": "alpaca_market_data_crypto_bars_v1beta3",
        "loc": loc,
        "timeframe": timeframe,
        "sort": "asc",
    }


def fetch_and_intake_crypto_bars(
    *,
    raw_response_path: Path | str = CRYPTO_BARS_INTAKE_DEFAULT_RAW_RESPONSE_PATH,
    canonical_csv: Path | str = CRYPTO_BARS_INTAKE_DEFAULT_CANONICAL_CSV,
    run_log: Path | str = CRYPTO_BARS_INTAKE_DEFAULT_RUN_LOG,
    symbol: str = CRYPTO_BARS_INTAKE_DEFAULT_SYMBOL,
    api_symbol: str = "BTC/USD",
    hours: int = _DEFAULT_HOURS,
    start: datetime | str | None = None,
    end: datetime | str | None = None,
    observed_at: datetime | str | None = None,
    allow_network: bool = False,
    market_data_fetch_authorized: bool = False,
    env: Mapping[str, str] | None = None,
    opener: UrlOpen | None = None,
    timeframe: str = _DEFAULT_TIMEFRAME,
    loc: str = _DEFAULT_LOC,
) -> dict[str, object]:
    """Fetch raw market data, write it under runs/, and run canonical intake."""

    source_env = os.environ if env is None else env
    preflight = crypto_market_data_preflight(source_env)
    if preflight["APP_PROFILE_is_live"] or preflight["live_endpoint_indicator"]:
        raise CryptoBarsFetchError("live endpoint/profile indicator blocks crypto bars fetch.")
    if not preflight["APP_PROFILE_is_paper"]:
        raise CryptoBarsFetchError("APP_PROFILE=paper is required for this paper-read shell.")
    credentials = read_credentials_from_env(source_env)
    checked_observed_at = (
        datetime.now(UTC)
        if observed_at is None
        else _utc_datetime(observed_at, "observed_at")
    )
    checked_end = checked_observed_at if end is None else _utc_datetime(end, "end")
    checked_start = (
        checked_end - timedelta(hours=_hours_value(hours))
        if start is None
        else _utc_datetime(start, "start")
    )
    raw_payload = fetch_alpaca_crypto_bars(
        api_symbol=api_symbol,
        start=checked_start,
        end=checked_end,
        credentials=credentials,
        allow_network=allow_network,
        market_data_fetch_authorized=market_data_fetch_authorized,
        opener=opener,
        timeframe=timeframe,
        loc=loc,
    )
    raw_path = Path(raw_response_path)
    if raw_path.parent != Path("."):
        raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(raw_payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    payload = run_crypto_bars_intake(
        CryptoBarsIntakeConfig(
            input_path=raw_path,
            canonical_csv=canonical_csv,
            run_log=run_log,
            observed_at=checked_observed_at,
            symbol=symbol,
            market_data_read_performed=True,
            network_access_attempted=True,
        )
    )
    payload["operator_preflight"] = preflight
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch read-only Alpaca BTCUSD crypto bars and run local intake.",
    )
    parser.add_argument("--symbol", default=CRYPTO_BARS_INTAKE_DEFAULT_SYMBOL)
    parser.add_argument("--api-symbol", default="BTC/USD")
    parser.add_argument("--loc", default=_DEFAULT_LOC)
    parser.add_argument("--timeframe", default=_DEFAULT_TIMEFRAME)
    parser.add_argument("--hours", type=int, default=_DEFAULT_HOURS)
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    parser.add_argument("--observed-at", default="")
    parser.add_argument(
        "--raw-response-path",
        default=str(CRYPTO_BARS_INTAKE_DEFAULT_RAW_RESPONSE_PATH),
    )
    parser.add_argument(
        "--canonical-csv",
        default=str(CRYPTO_BARS_INTAKE_DEFAULT_CANONICAL_CSV),
    )
    parser.add_argument("--run-log", default=str(CRYPTO_BARS_INTAKE_DEFAULT_RUN_LOG))
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--market-data-fetch-authorized", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = fetch_and_intake_crypto_bars(
            raw_response_path=args.raw_response_path,
            canonical_csv=args.canonical_csv,
            run_log=args.run_log,
            symbol=args.symbol,
            api_symbol=args.api_symbol,
            hours=args.hours,
            start=args.start or None,
            end=args.end or None,
            observed_at=args.observed_at or None,
            allow_network=args.allow_network,
            market_data_fetch_authorized=args.market_data_fetch_authorized,
            timeframe=args.timeframe,
            loc=args.loc,
        )
    except (CryptoBarsFetchError, ValidationError) as exc:
        print(str(exc))
        return 2
    if args.format == "json":
        print(render_crypto_bars_intake_json(payload))
    else:
        print(render_crypto_bars_intake_text(payload))
    return 0


def _bar_items_from_payload(payload: object, api_symbol: str) -> tuple[object, ...]:
    if not isinstance(payload, Mapping):
        raise CryptoBarsFetchError("Alpaca crypto bars response must be a JSON object.")
    bars = payload.get("bars")
    if isinstance(bars, list):
        return tuple(bars)
    if isinstance(bars, Mapping):
        normalized_api_symbol = api_symbol.replace("/", "").upper()
        for key, value in bars.items():
            if str(key).replace("/", "").upper() == normalized_api_symbol:
                if not isinstance(value, list):
                    raise CryptoBarsFetchError("Alpaca crypto symbol bars must be a list.")
                return tuple(value)
    raise CryptoBarsFetchError("Alpaca crypto bars response did not include BTCUSD bars.")


def _next_page_token(payload: object) -> str:
    if not isinstance(payload, Mapping):
        return ""
    value = payload.get("next_page_token")
    return "" if value in (None, "") else str(value).strip()


def _sanitized_exception_message(exc: Exception, credentials: AlpacaCredentials) -> str:
    message = str(exc)
    for secret in (credentials.api_key_id, credentials.api_secret_key):
        if secret:
            message = message.replace(secret, "<redacted>")
    return f"Alpaca crypto bars fetch failed: {message}"


def _first_nonempty(source: Mapping[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = source.get(name, "").strip()
        if value:
            return value
    return ""


def _live_endpoint_indicator(source: Mapping[str, str]) -> bool:
    for name in _PUBLIC_ENV_NAMES:
        value = source.get(name, "").strip().lower()
        if name == "APP_PROFILE" and value == "live":
            return True
        if value and "api.alpaca.markets" in value and "paper" not in value:
            return True
    return False


def _utc_datetime(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise CryptoBarsFetchError(f"{field_name} must be an ISO timestamp.") from exc
    else:
        raise CryptoBarsFetchError(f"{field_name} must be an ISO timestamp.")
    if parsed.tzinfo is None:
        raise CryptoBarsFetchError(f"{field_name} must include timezone information.")
    return parsed.astimezone(UTC)


def _api_symbol_value(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise CryptoBarsFetchError("api_symbol must be a non-empty string.")
    text = value.strip().upper()
    if text not in {"BTC/USD", "BTCUSD"}:
        raise CryptoBarsFetchError("api_symbol must be BTC/USD or BTCUSD.")
    return text


def _loc_value(value: object) -> str:
    if type(value) is not str or value.strip() not in {"us", "us-1", "us-2", "eu-1", "bs-1"}:
        raise CryptoBarsFetchError("loc must be an allowed Alpaca crypto location.")
    return value.strip()


def _timeframe_value(value: object) -> str:
    if type(value) is not str or value.strip() not in {"1Min", "5Min", "15Min", "1Hour", "1Day"}:
        raise CryptoBarsFetchError("timeframe is not allowed for this refresh.")
    return value.strip()


def _limit_value(value: object) -> int:
    if type(value) is not int or value < 1 or value > _DEFAULT_LIMIT:
        raise CryptoBarsFetchError("limit must be between 1 and 10000.")
    return value


def _hours_value(value: object) -> int:
    if type(value) is not int or value < 50 or value > 720:
        raise CryptoBarsFetchError("hours must be an integer between 50 and 720.")
    return value


def _page_token_value(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise CryptoBarsFetchError("page_token must be a non-empty string.")
    return value.strip()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
