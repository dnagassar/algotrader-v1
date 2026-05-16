"""Explicitly gated Alpaca Market Data daily snapshot fetcher."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = Path(".data") / "research_snapshots"
_HASH_CHUNK_SIZE = 1024 * 1024
_MARKET_DATA_BASE_URL = "https://data.alpaca.markets"
_STOCK_BARS_PATH_TEMPLATE = "/v2/stocks/{symbol}/bars"
_DEFAULT_LIMIT = 10000
_TIMEFRAME = "1Day"
_ADJUSTMENT = "all"
_DEFAULT_FEED = "iex"
_ALLOWED_FEEDS = (_DEFAULT_FEED, "sip", "delayed_sip")
_ADJUSTMENT_POLICY_UNKNOWN = "unknown"
_RETURN_BASIS_PRICE_RETURN = "price_return"
_ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK = "close_price_fallback"
_ADJUSTED_CLOSE_SOURCE_UNCONFIRMED_VENDOR_FIELD = "unconfirmed_vendor_field"
_CSV_COLUMNS = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)
_KEY_ID_ENV = "ALPACA_API_KEY_ID"
_SECRET_KEY_ENV = "ALPACA_API_SECRET_KEY"
_ADJUSTMENT_LIMITATION = (
    "Adjustment policy limitation: the request asks Alpaca Market Data for "
    "adjustment=all daily bars. The stock bars payload may not include a "
    "separate adjusted_close field; when it does not, this script writes "
    "adjusted_close equal to close. This snapshot must not be treated as "
    "total-return accurate data."
)


class SnapshotFetchError(ValueError):
    """Raised for safe, credential-redacted fetcher failures."""


class AlpacaCredentials:
    """Environment-sourced API credentials with redacted representation."""

    __slots__ = ("api_key_id", "api_secret_key")

    def __init__(self, api_key_id: str, api_secret_key: str) -> None:
        self.api_key_id = api_key_id
        self.api_secret_key = api_secret_key

    def __repr__(self) -> str:
        return (
            "AlpacaCredentials("
            "api_key_id=<redacted>, api_secret_key=<redacted>"
            ")"
        )

    __str__ = __repr__


@dataclass(frozen=True, slots=True)
class SnapshotCsvRow:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: int
    adjusted_close_source: str = _ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK

    def as_csv_dict(self) -> dict[str, str]:
        return {
            "date": self.date.isoformat(),
            "open": _decimal_csv_text(self.open),
            "high": _decimal_csv_text(self.high),
            "low": _decimal_csv_text(self.low),
            "close": _decimal_csv_text(self.close),
            "adjusted_close": _decimal_csv_text(self.adjusted_close),
            "volume": str(self.volume),
        }


@dataclass(frozen=True, slots=True)
class SnapshotFetchResult:
    symbol: str
    start_date: date
    end_date: date
    feed: str
    output_path: Path
    row_count: int
    file_sha256: str
    adjustment_policy: str = _ADJUSTMENT_POLICY_UNKNOWN
    return_basis: str = _RETURN_BASIS_PRICE_RETURN
    adjusted_close_available: bool = False
    adjusted_close_source: str = _ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK
    adjustment_policy_limitation: str = _ADJUSTMENT_LIMITATION


UrlOpen = Callable[[urllib.request.Request, int], Any]


def build_request_url(
    symbol: str,
    start_date: str | date,
    end_date: str | date,
    *,
    page_token: str | None = None,
    base_url: str = _MARKET_DATA_BASE_URL,
    limit: int = _DEFAULT_LIMIT,
    feed: str = _DEFAULT_FEED,
) -> str:
    """Build the Alpaca Market Data historical stock bars request URL."""
    checked_symbol = _symbol_value(symbol)
    checked_start = _date_value(start_date, "start")
    checked_end = _date_value(end_date, "end")
    _validate_date_range(checked_start, checked_end)
    checked_limit = _positive_int(limit, "limit")
    checked_feed = _feed_value(feed)

    query_items: list[tuple[str, str]] = [
        ("timeframe", _TIMEFRAME),
        ("start", checked_start.isoformat()),
        ("end", checked_end.isoformat()),
        ("adjustment", _ADJUSTMENT),
        ("feed", checked_feed),
        ("limit", str(checked_limit)),
    ]
    if page_token is not None:
        checked_page_token = _page_token_value(page_token)
        query_items.append(("page_token", checked_page_token))

    quoted_symbol = urllib.parse.quote(checked_symbol, safe=".-_")
    path = _STOCK_BARS_PATH_TEMPLATE.format(symbol=quoted_symbol)
    return f"{base_url.rstrip('/')}{path}?{urllib.parse.urlencode(query_items)}"


def read_credentials_from_env(
    env: Mapping[str, str] | None = None,
) -> AlpacaCredentials:
    """Read Alpaca API credentials from environment variables only."""
    source = os.environ if env is None else env
    key_id = source.get(_KEY_ID_ENV, "").strip()
    secret_key = source.get(_SECRET_KEY_ENV, "").strip()
    missing = tuple(
        name
        for name, value in (
            (_KEY_ID_ENV, key_id),
            (_SECRET_KEY_ENV, secret_key),
        )
        if not value
    )
    if missing:
        raise SnapshotFetchError(
            "Missing Alpaca Market Data credentials: "
            f"{', '.join(missing)} must be set in the environment."
        )

    return AlpacaCredentials(api_key_id=key_id, api_secret_key=secret_key)


def validate_output_path(
    output_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    allow_outside_data_dir: bool = False,
    overwrite: bool = False,
) -> Path:
    """Validate that the output CSV path is under the ignored snapshot dir."""
    if isinstance(output_path, str) and not output_path.strip():
        raise SnapshotFetchError("output path is required.")
    if not isinstance(output_path, (str, Path)):
        raise SnapshotFetchError("output path must be a local CSV path.")

    checked_path = Path(output_path).expanduser().resolve()
    if checked_path.suffix.lower() != ".csv":
        raise SnapshotFetchError("output path must reference a CSV file.")
    if checked_path.exists() and checked_path.is_dir():
        raise SnapshotFetchError("output path must reference a CSV file, not a directory.")
    if checked_path.exists() and not overwrite:
        raise SnapshotFetchError("output path already exists; pass --overwrite to replace it.")

    checked_repo_root = _repo_root_value(repo_root)
    allowed_dir = (checked_repo_root / _DATA_DIR).resolve()
    if not allow_outside_data_dir and not _is_relative_to(checked_path, allowed_dir):
        raise SnapshotFetchError(
            "output path must be under .data/research_snapshots/ unless "
            "--allow-outside-data-dir is provided."
        )

    return checked_path


def normalize_api_bar_response(payload: object) -> tuple[SnapshotCsvRow, ...]:
    """Normalize and validate a single Alpaca stock bars response payload."""
    bars = _bars_from_payload(payload)
    rows = tuple(_row_from_bar(bar, index) for index, bar in enumerate(bars, start=1))
    if not rows:
        raise SnapshotFetchError("Alpaca Market Data response must include at least one bar.")

    _validate_row_dates(rows)
    return rows


def write_csv_rows(path: str | Path, rows: Sequence[SnapshotCsvRow]) -> None:
    """Write normalized rows using the exact HistoricalPriceSnapshot columns."""
    checked_rows = tuple(rows)
    if not checked_rows:
        raise SnapshotFetchError("CSV output requires at least one row.")

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in checked_rows:
            writer.writerow(row.as_csv_dict())


def compute_output_sha256(path: str | Path) -> str:
    """Return the sha256 hex digest for the written CSV file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while True:
            chunk = source.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def fetch_alpaca_daily_bars(
    symbol: str,
    start_date: str | date,
    end_date: str | date,
    credentials: AlpacaCredentials,
    *,
    opener: UrlOpen | None = None,
    timeout: int = 30,
    feed: str = _DEFAULT_FEED,
) -> tuple[SnapshotCsvRow, ...]:
    """Fetch daily bars from the Alpaca Market Data historical stock bars endpoint."""
    if not isinstance(credentials, AlpacaCredentials):
        raise SnapshotFetchError("Alpaca credentials are required.")

    checked_symbol = _symbol_value(symbol)
    checked_start = _date_value(start_date, "start")
    checked_end = _date_value(end_date, "end")
    _validate_date_range(checked_start, checked_end)
    checked_feed = _feed_value(feed)

    bar_items: list[object] = []
    page_token: str | None = None
    seen_page_tokens: set[str] = set()
    while True:
        url = build_request_url(
            checked_symbol,
            checked_start,
            checked_end,
            page_token=page_token,
            feed=checked_feed,
        )
        payload = _request_json(url, credentials, opener=opener, timeout=timeout)
        page_bars = _bars_from_payload(payload)
        bar_items.extend(page_bars)
        next_page_token = _next_page_token(payload)
        if next_page_token is None:
            break
        if next_page_token in seen_page_tokens:
            raise SnapshotFetchError("Alpaca Market Data pagination repeated a page token.")
        seen_page_tokens.add(next_page_token)
        page_token = next_page_token

    return normalize_api_bar_response({"bars": bar_items})


def fetch_alpaca_daily_snapshot(
    *,
    symbol: str = "SPY",
    start_date: str | date,
    end_date: str | date,
    output_path: str | Path,
    allow_network: bool = False,
    allow_outside_data_dir: bool = False,
    overwrite: bool = False,
    feed: str = _DEFAULT_FEED,
    env: Mapping[str, str] | None = None,
    repo_root: str | Path | None = None,
    opener: UrlOpen | None = None,
) -> SnapshotFetchResult:
    """Fetch a gated local daily snapshot and write an ignored CSV."""
    if not allow_network:
        raise SnapshotFetchError(
            "Network access is disabled by default; pass --allow-network to fetch "
            "from Alpaca Market Data."
        )

    checked_symbol = _symbol_value(symbol)
    checked_start = _date_value(start_date, "start")
    checked_end = _date_value(end_date, "end")
    _validate_date_range(checked_start, checked_end)
    checked_feed = _feed_value(feed)
    credentials = read_credentials_from_env(env)
    checked_output_path = validate_output_path(
        output_path,
        repo_root=repo_root,
        allow_outside_data_dir=allow_outside_data_dir,
        overwrite=overwrite,
    )
    rows = fetch_alpaca_daily_bars(
        checked_symbol,
        checked_start,
        checked_end,
        credentials,
        opener=opener,
        feed=checked_feed,
    )

    write_csv_rows(checked_output_path, rows)
    adjusted_close_source = _snapshot_adjusted_close_source(rows)
    return SnapshotFetchResult(
        symbol=checked_symbol,
        start_date=checked_start,
        end_date=checked_end,
        feed=checked_feed,
        output_path=checked_output_path,
        row_count=len(rows),
        file_sha256=compute_output_sha256(checked_output_path),
        adjusted_close_source=adjusted_close_source,
    )


def render_fetch_report(result: SnapshotFetchResult) -> str:
    """Render a metadata-only success report."""
    return "\n".join(
        (
            "Alpaca daily snapshot fetched.",
            f"Symbol: {result.symbol}",
            f"Requested date range: {result.start_date.isoformat()} to {result.end_date.isoformat()}",
            f"Feed: {result.feed}",
            f"Rows written: {result.row_count}",
            f"Output CSV: {result.output_path}",
            f"File SHA-256: {result.file_sha256}",
            f"Adjustment policy: {result.adjustment_policy}",
            f"Return basis: {result.return_basis}",
            f"Adjusted close available: {str(result.adjusted_close_available).lower()}",
            f"Adjusted close source: {result.adjusted_close_source}",
            result.adjustment_policy_limitation,
            "",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a gated local daily OHLCV snapshot from Alpaca Market Data "
            "into .data/research_snapshots/."
        ),
    )
    parser.add_argument(
        "--symbol",
        default="SPY",
        help="Stock symbol to fetch. Default: SPY.",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Explicit start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="Explicit end date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Explicit output CSV path. Default safety requires .data/research_snapshots/.",
    )
    parser.add_argument(
        "--feed",
        choices=_ALLOWED_FEEDS,
        default=_DEFAULT_FEED,
        help="Alpaca Market Data feed to request. Default: iex.",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Required to make the Alpaca Market Data request.",
    )
    parser.add_argument(
        "--allow-outside-data-dir",
        action="store_true",
        help="Allow output outside .data/research_snapshots/.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output CSV.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        result = fetch_alpaca_daily_snapshot(
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            output_path=args.output,
            allow_network=args.allow_network,
            allow_outside_data_dir=args.allow_outside_data_dir,
            overwrite=args.overwrite,
            feed=args.feed,
        )
    except SnapshotFetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(render_fetch_report(result))
    return 0


def _request_json(
    url: str,
    credentials: AlpacaCredentials,
    *,
    opener: UrlOpen | None,
    timeout: int,
) -> object:
    headers = {
        "APCA-API-KEY-ID": credentials.api_key_id,
        "APCA-API-SECRET-KEY": credentials.api_secret_key,
        "Accept": "application/json",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    open_url = urllib.request.urlopen if opener is None else opener
    try:
        with open_url(request, timeout=timeout) as response:
            raw_payload = response.read()
    except urllib.error.HTTPError as exc:
        raise SnapshotFetchError(_http_error_message(exc.code)) from None
    except urllib.error.URLError:
        raise SnapshotFetchError(
            "Alpaca Market Data request failed before a response was received."
        ) from None
    except Exception:
        raise SnapshotFetchError(
            "Alpaca Market Data request failed before a usable response was received."
        ) from None

    try:
        return json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SnapshotFetchError("Alpaca Market Data response was not valid JSON.") from None


def _bars_from_payload(payload: object) -> list[object]:
    if not isinstance(payload, dict):
        raise SnapshotFetchError("Alpaca Market Data response must be a JSON object.")
    bars = payload.get("bars")
    if not isinstance(bars, list):
        raise SnapshotFetchError("Alpaca Market Data response must include a bars list.")

    return bars


def _next_page_token(payload: object) -> str | None:
    if not isinstance(payload, dict):
        raise SnapshotFetchError("Alpaca Market Data response must be a JSON object.")

    value = payload.get("next_page_token")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SnapshotFetchError("Alpaca Market Data next_page_token must be a string.")

    return value


def _row_from_bar(bar: object, index: int) -> SnapshotCsvRow:
    if not isinstance(bar, dict):
        raise SnapshotFetchError(f"bar {index} must be a JSON object.")

    open_price = _price_value(_required_bar_value(bar, ("o", "open"), index, "open"), f"bar {index} open")
    high_price = _price_value(_required_bar_value(bar, ("h", "high"), index, "high"), f"bar {index} high")
    low_price = _price_value(_required_bar_value(bar, ("l", "low"), index, "low"), f"bar {index} low")
    close_price = _price_value(_required_bar_value(bar, ("c", "close"), index, "close"), f"bar {index} close")
    adjusted_close, adjusted_close_source = _optional_adjusted_close_value(
        bar,
        close_price,
        index,
    )
    volume = _volume_value(_required_bar_value(bar, ("v", "volume"), index, "volume"), f"bar {index} volume")
    row = SnapshotCsvRow(
        date=_bar_date_value(_required_bar_value(bar, ("t", "date"), index, "date"), f"bar {index} date"),
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        adjusted_close=adjusted_close,
        volume=volume,
        adjusted_close_source=adjusted_close_source,
    )
    _validate_ohlc_relationships(row, index)
    return row


def _required_bar_value(
    bar: Mapping[object, object],
    names: tuple[str, ...],
    index: int,
    label: str,
) -> object:
    for name in names:
        if name in bar:
            return bar[name]

    accepted_names = " or ".join(names)
    raise SnapshotFetchError(f"bar {index} is missing required {label} field ({accepted_names}).")


def _optional_adjusted_close_value(
    bar: Mapping[object, object],
    close_price: Decimal,
    index: int,
) -> tuple[Decimal, str]:
    for name in ("adjusted_close", "adjustedClose", "adj_close", "ac"):
        if name in bar:
            return (
                _price_value(bar[name], f"bar {index} adjusted_close"),
                _ADJUSTED_CLOSE_SOURCE_UNCONFIRMED_VENDOR_FIELD,
            )

    return close_price, _ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK


def _snapshot_adjusted_close_source(rows: Sequence[SnapshotCsvRow]) -> str:
    if any(
        row.adjusted_close_source == _ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK
        for row in rows
    ):
        return _ADJUSTED_CLOSE_SOURCE_CLOSE_PRICE_FALLBACK

    return _ADJUSTED_CLOSE_SOURCE_UNCONFIRMED_VENDOR_FIELD


def _validate_row_dates(rows: tuple[SnapshotCsvRow, ...]) -> None:
    seen_dates: set[date] = set()
    previous_date: date | None = None
    for row in rows:
        if row.date in seen_dates:
            raise SnapshotFetchError("Alpaca Market Data response contains duplicate dates.")
        if previous_date is not None and row.date <= previous_date:
            raise SnapshotFetchError(
                "Alpaca Market Data response dates must be strictly increasing."
            )

        seen_dates.add(row.date)
        previous_date = row.date


def _validate_ohlc_relationships(row: SnapshotCsvRow, index: int) -> None:
    if row.high < row.open or row.high < row.close or row.high < row.low:
        raise SnapshotFetchError(
            f"bar {index} high must be greater than or equal to open, close, and low."
        )
    if row.low > row.open or row.low > row.close or row.low > row.high:
        raise SnapshotFetchError(
            f"bar {index} low must be less than or equal to open, close, and high."
        )


def _symbol_value(value: str) -> str:
    if not isinstance(value, str):
        raise SnapshotFetchError("symbol must be a non-empty string.")

    normalized = value.strip().upper()
    if not normalized:
        raise SnapshotFetchError("symbol must be a non-empty string.")
    allowed_characters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
    if any(character not in allowed_characters for character in normalized):
        raise SnapshotFetchError("symbol contains unsupported characters.")

    return normalized


def _date_value(value: str | date, field_name: str) -> date:
    if type(value) is date:
        return value
    if not isinstance(value, str):
        raise SnapshotFetchError(f"{field_name} date must use YYYY-MM-DD format.")

    text = value.strip()
    if text != value or len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise SnapshotFetchError(f"{field_name} date must use YYYY-MM-DD format.")

    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise SnapshotFetchError(f"{field_name} date must use YYYY-MM-DD format.") from exc
    if parsed.isoformat() != text:
        raise SnapshotFetchError(f"{field_name} date must use YYYY-MM-DD format.")

    return parsed


def _bar_date_value(value: object, field_name: str) -> date:
    if not isinstance(value, str):
        raise SnapshotFetchError(f"{field_name} must be an Alpaca timestamp string.")

    text = value.strip()
    if len(text) < 10:
        raise SnapshotFetchError(f"{field_name} must include an ISO date.")

    return _date_value(text[:10], field_name)


def _validate_date_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise SnapshotFetchError("start date must be on or before end date.")


def _price_value(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise SnapshotFetchError(f"{field_name} must be greater than zero.")
    if not isinstance(value, (int, float, str, Decimal)):
        raise SnapshotFetchError(f"{field_name} must be a decimal-compatible value.")

    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise SnapshotFetchError(f"{field_name} must be a decimal-compatible value.") from exc

    if not parsed.is_finite() or parsed <= 0:
        raise SnapshotFetchError(f"{field_name} must be greater than zero.")

    return parsed


def _volume_value(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise SnapshotFetchError(f"{field_name} must be an integer.")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise SnapshotFetchError(f"{field_name} must be an integer.")
        try:
            parsed = int(text)
        except ValueError as exc:
            raise SnapshotFetchError(f"{field_name} must be an integer.") from exc
    else:
        raise SnapshotFetchError(f"{field_name} must be an integer.")

    if parsed < 0:
        raise SnapshotFetchError(f"{field_name} must be zero or greater.")

    return parsed


def _positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SnapshotFetchError(f"{field_name} must be a positive integer.")

    return value


def _feed_value(value: str) -> str:
    if not isinstance(value, str):
        raise SnapshotFetchError(_invalid_feed_message())

    normalized = value.strip().lower()
    if normalized not in _ALLOWED_FEEDS:
        raise SnapshotFetchError(_invalid_feed_message())

    return normalized


def _page_token_value(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SnapshotFetchError("page_token must be a non-empty string.")

    return value


def _repo_root_value(repo_root: str | Path | None) -> Path:
    if repo_root is None:
        return _REPO_ROOT
    if isinstance(repo_root, str) and not repo_root.strip():
        raise SnapshotFetchError("repo_root is required.")
    if not isinstance(repo_root, (str, Path)):
        raise SnapshotFetchError("repo_root must be a local path.")

    return Path(repo_root).expanduser().resolve()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False

    return True


def _decimal_csv_text(value: Decimal) -> str:
    return format(value, "f")


def _http_error_message(status_code: int) -> str:
    message = f"Alpaca Market Data request failed with HTTP status {status_code}."
    if status_code == 403:
        return (
            f"{message} Credentials may be invalid or stale, the key may not "
            "have market-data permissions, or the selected feed may not be "
            "available for the account. Try --feed iex for basic access."
        )

    return message


def _invalid_feed_message() -> str:
    allowed = ", ".join(_ALLOWED_FEEDS)
    return f"feed must be one of: {allowed}."


if __name__ == "__main__":
    raise SystemExit(main())
