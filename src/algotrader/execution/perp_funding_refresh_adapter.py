"""Read-only public perpetual funding and kline refresh adapter.

Adds a third external destination to a repository deliberately limited to two.
The addition is deliberate and is recorded in the V5.99 preregistration; this
module keeps the same safety architecture as the existing adapters:

- GET only, and the method is asserted rather than assumed;
- one destination host, checked against a frozen allowlist;
- **no credentials of any kind** — every endpoint used here is public, and the
  module has no code path that reads an environment variable, a dotenv, or a
  credential store;
- `dry_run` mode builds and records the exact request without opening a socket,
  so the whole pipeline is testable offline;
- every response is written to a receipt with its SHA-256 before use.

It cannot place an order, read an account, or touch a broker.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import http.client
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError

__all__ = [
    "APPROVED_PERP_SYMBOLS",
    "DESTINATION_HOST",
    "FUNDING_PATH",
    "PerpFundingRefreshConfig",
    "build_perp_request",
    "run_perp_funding_refresh",
]

# Binance returns HTTP 451 (geo-blocked) from this jurisdiction, so the venue
# was changed to Deribit before any data was scored. See the V5.99 amendment.
DESTINATION_HOST = "www.deribit.com"
SPOT_DESTINATION_HOST = DESTINATION_HOST
_DESTINATION_ALLOWLIST = (DESTINATION_HOST,)
FUNDING_PATH = "/api/v2/public/get_funding_rate_history"
PERP_KLINE_PATH = "/api/v2/public/get_tradingview_chart_data"
SPOT_KLINE_PATH = PERP_KLINE_PATH
APPROVED_PERP_SYMBOLS = ("BTC-PERPETUAL", "ETH-PERPETUAL", "SOL_USDC-PERPETUAL")
_APPROVED_SERIES = ("funding", "perp_kline", "spot_kline")
_METHOD = "GET"
_MAX_LIMIT = 1000
_KLINE_INTERVAL = "60"


@dataclass(frozen=True, slots=True)
class PerpFundingRefreshConfig:
    """Inputs for one bounded, read-only public series request."""

    symbol: str
    series: str
    output_root: Path | str
    mode: str = "dry_run"
    start_ms: int | None = None
    end_ms: int | None = None
    limit: int = _MAX_LIMIT
    live_market_data_fetch_authorized: bool = False

    def __post_init__(self) -> None:
        symbol = str(self.symbol).strip().upper()
        if symbol not in APPROVED_PERP_SYMBOLS:
            raise ValidationError(f"symbol is not approved: {symbol}")
        object.__setattr__(self, "symbol", symbol)
        if self.series not in _APPROVED_SERIES:
            raise ValidationError(f"series is not approved: {self.series}")
        if self.mode not in ("dry_run", "live_market_data_fetch"):
            raise ValidationError(f"unsupported mode: {self.mode}")
        if self.mode == "live_market_data_fetch" and not (
            self.live_market_data_fetch_authorized
        ):
            raise ValidationError(
                "live public market-data fetch requires explicit authorization."
            )
        if self.mode == "dry_run" and self.live_market_data_fetch_authorized:
            raise ValidationError(
                "authorization flag requires live fetch mode."
            )
        if not (1 <= int(self.limit) <= _MAX_LIMIT):
            raise ValidationError("limit must lie in [1, 1000].")
        object.__setattr__(self, "output_root", Path(self.output_root))


def build_perp_request(config: PerpFundingRefreshConfig) -> dict[str, object]:
    """Build the exact request without performing any network access."""

    if config.series == "funding":
        host, path = DESTINATION_HOST, FUNDING_PATH
    elif config.series == "perp_kline":
        host, path = DESTINATION_HOST, PERP_KLINE_PATH
    else:
        host, path = SPOT_DESTINATION_HOST, SPOT_KLINE_PATH
    if host not in _DESTINATION_ALLOWLIST:
        raise ValidationError("destination host is not allowlisted.")

    query: list[tuple[str, str]] = [("instrument_name", config.symbol)]
    if config.start_ms is not None:
        query.append(("start_timestamp", str(int(config.start_ms))))
    if config.end_ms is not None:
        query.append(("end_timestamp", str(int(config.end_ms))))
    if config.series != "funding":
        query.append(("resolution", _KLINE_INTERVAL))
    encoded = "&".join(f"{key}={value}" for key, value in query)
    return {
        "method": _METHOD,
        "scheme": "https",
        "destination_host": host,
        "destination_path": path,
        "destination_allowlist": list(_DESTINATION_ALLOWLIST),
        "destination_allowlist_match": True,
        "url": f"https://{host}{path}?{encoded}",
        "symbol": config.symbol,
        "series": config.series,
        "interval": None if config.series == "funding" else _KLINE_INTERVAL,
        "credentials_used": False,
        "authenticated": False,
        "headers": {},
    }


def run_perp_funding_refresh(
    config: PerpFundingRefreshConfig,
    *,
    http_get: object | None = None,
) -> dict[str, object]:
    """Fetch one bounded public series, or plan it without touching the network."""

    request = build_perp_request(config)
    root = Path(config.output_root)
    stem = f"{config.symbol.lower()}_{config.series}"
    receipt: dict[str, object] = {
        "record_type": "perp_public_series_refresh_receipt",
        "schema_version": 1,
        "symbol": config.symbol,
        "series": config.series,
        "mode": config.mode,
        "provider_request": request,
        "network_method_allowlist": [_METHOD],
        "network_destination_allowlist_enforced": True,
        "credential_access_attempted": False,
        "credential_values_exposed": False,
        "authenticated_request": False,
        "broker_access_attempted": False,
        "broker_mutation_attempted": False,
        "paper_submit_attempted": False,
        "live_authorized": False,
        "live_trading_performed": False,
        "recorded_at": datetime.now(UTC).isoformat(),
    }

    if config.mode == "dry_run":
        receipt.update(
            {
                "network_access_attempted": False,
                "refresh_state": "dry_run_request_plan_built",
                "row_count": 0,
                "raw_response_path": "",
                "raw_response_sha256": "",
                "http_outcome_category": "not_attempted",
            }
        )
        _write_jsonl(root / f"{stem}_receipt.jsonl", receipt)
        return receipt

    payload = (http_get or _https_get)(
        request["destination_host"], f"{request['destination_path']}?"
        + request["url"].split("?", 1)[1]
    )
    decoded = json.loads(payload)
    # Deribit wraps every public response in a JSON-RPC envelope; the chart
    # endpoint returns an object of parallel arrays rather than a row list.
    result = decoded.get("result", decoded) if isinstance(decoded, dict) else decoded
    if isinstance(result, list):
        rows = result
    elif isinstance(result, Mapping):
        rows = result.get("close", [])
    else:
        raise ValidationError("unrecognised public series response shape.")
    raw_path = root / f"{stem}_raw.json"
    _write_bytes(raw_path, payload if isinstance(payload, bytes) else payload.encode())
    receipt.update(
        {
            "network_access_attempted": True,
            "refresh_state": "accepted_public_series_refresh",
            "row_count": len(rows),
            "raw_response_path": str(raw_path),
            "raw_response_sha256": _sha256(raw_path),
            "http_outcome_category": "success",
        }
    )
    _write_jsonl(root / f"{stem}_receipt.jsonl", receipt)
    return receipt


def _https_get(host: str, path: str, timeout: float = 30.0) -> bytes:
    if host not in _DESTINATION_ALLOWLIST:
        raise ValidationError("destination host is not allowlisted.")
    connection = http.client.HTTPSConnection(host, timeout=timeout)
    try:
        connection.request(_METHOD, path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise ValidationError(
                f"public series request failed with status {response.status}."
            )
        return body
    finally:
        connection.close()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _write_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--series", required=True, choices=_APPROVED_SERIES)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--mode", default="dry_run", choices=("dry_run", "live_market_data_fetch")
    )
    parser.add_argument("--start-ms", type=int, default=None)
    parser.add_argument("--end-ms", type=int, default=None)
    parser.add_argument("--limit", type=int, default=_MAX_LIMIT)
    parser.add_argument(
        "--live-market-data-fetch-authorized", action="store_true"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = run_perp_funding_refresh(
            PerpFundingRefreshConfig(
                symbol=args.symbol,
                series=args.series,
                output_root=args.output_root,
                mode=args.mode,
                start_ms=args.start_ms,
                end_ms=args.end_ms,
                limit=args.limit,
                live_market_data_fetch_authorized=(
                    args.live_market_data_fetch_authorized
                ),
            )
        )
    except (OSError, ValidationError, ValueError, json.JSONDecodeError) as exc:
        print(f"perp_funding_refresh_status=blocked:{exc}")
        return 2
    print(f"perp_funding_refresh_status={receipt['refresh_state']}")
    print(f"rows={receipt['row_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
