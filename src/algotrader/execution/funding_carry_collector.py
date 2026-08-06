"""Daily collector feeding the V6.05 continuously-held funding carry shadow.

Fetches Deribit funding and perpetual marks through the existing audited
`perp_funding_refresh_adapter`, assembles the eight-hour panel exactly as V6.00
did, and writes the four canonical daily series the forward shadow reads.

It deliberately does **not** append to the shadow ledger. Collection and
observation are separate acts: a collector that also recorded observations could
quietly re-record a session after seeing how it turned out, and the ledger's
whole value is that it cannot be edited. Appending stays a distinct step.

Everything network-facing goes through the adapter, so GET-only, single
allowlisted venue, and no credentials hold in one place. Deribit's public
endpoints need no authentication and this module has no code path that can read
an environment variable, dotenv, or credential store.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.execution.perp_funding_refresh_adapter import (
    APPROVED_PERP_SYMBOLS,
    PerpFundingRefreshConfig,
    run_perp_funding_refresh,
)
from algotrader.research.funding_carry_detector import validate_signal_to_noise
from algotrader.research.funding_carry_index import (
    CASH_SYMBOL,
    build_carry_index,
    build_cash_series,
    write_canonical_daily_bars,
)

__all__ = [
    "CARRY_SYMBOL_BY_INSTRUMENT",
    "FundingCarryCollectorConfig",
    "assemble_panel",
    "run_funding_carry_collector",
]

# The forward shadow's frozen universe maps one-to-one onto Deribit instruments.
CARRY_SYMBOL_BY_INSTRUMENT: dict[str, str] = {
    "BTC-PERPETUAL": "BTCCARRY",
    "ETH-PERPETUAL": "ETHCARRY",
    "SOL_USDC-PERPETUAL": "SOLCARRY",
}

_HOUR_MS = 60 * 60 * 1000
_INTERVAL_MS = 8 * _HOUR_MS
# V6.00: Deribit chart ticks are bar OPEN times, so the close at T is the price
# at T + 1h. Established by a physical criterion before any return was computed
# and carried here unchanged.
_PERP_TICK_OFFSET_MS = _HOUR_MS


@dataclass(frozen=True, slots=True)
class FundingCarryCollectorConfig:
    """One bounded collection pass."""

    output_root: Path | str
    canonical_csv: Path | str
    mode: str = "dry_run"
    lookback_days: int = 14
    live_market_data_fetch_authorized: bool = False
    cost_bps_per_leg: float = 5.0
    # Which registered universe this pass serves. Defaults to all three legs;
    # V6.06 registered a two-leg book after SOL failed the precondition, and the
    # collection must match the registration it feeds rather than approximate it.
    instruments: tuple[str, ...] = tuple(CARRY_SYMBOL_BY_INSTRUMENT)

    def __post_init__(self) -> None:
        chosen = tuple(self.instruments)
        if not chosen:
            raise ValidationError("at least one instrument is required.")
        unknown = [item for item in chosen if item not in CARRY_SYMBOL_BY_INSTRUMENT]
        if unknown:
            raise ValidationError(f"instruments are not approved: {unknown}")
        if len(set(chosen)) != len(chosen):
            raise ValidationError("instruments contain duplicates.")
        object.__setattr__(self, "instruments", chosen)
        if self.mode not in ("dry_run", "live_market_data_fetch"):
            raise ValidationError(f"unsupported mode: {self.mode}")
        if self.mode == "live_market_data_fetch" and not self.live_market_data_fetch_authorized:
            raise ValidationError("live fetch requires explicit authorization.")
        if self.mode == "dry_run" and self.live_market_data_fetch_authorized:
            raise ValidationError("authorization flag requires live fetch mode.")
        if self.lookback_days < 1:
            raise ValidationError("lookback_days must be at least one.")
        object.__setattr__(self, "output_root", Path(self.output_root))
        object.__setattr__(self, "canonical_csv", Path(self.canonical_csv))


def assemble_panel(
    funding_rows: Sequence[Mapping[str, object]],
    perp_closes: Mapping[int, float],
) -> dict[int, dict[str, float]]:
    """Rebuild V6.00's eight-hour panel from hourly funding and perpetual marks.

    An eight-hour interval is admitted only when all eight hourly funding
    observations and the offset perpetual mark exist. A partial window is
    dropped rather than summed over what is present, because a short sum would
    understate the funding actually paid.
    """

    hourly: dict[int, tuple[float, float]] = {}
    for row in funding_rows:
        try:
            stamp = int(row["timestamp"])  # type: ignore[index]
            rate = float(row["interest_1h"])  # type: ignore[index]
            index_price = float(row["index_price"])  # type: ignore[index]
        except (KeyError, TypeError, ValueError):
            continue
        if index_price > 0.0:
            hourly[stamp] = (rate, index_price)

    panel: dict[int, dict[str, float]] = {}
    for stamp in sorted(hourly):
        if stamp % _INTERVAL_MS != 0:
            continue
        window = [hourly.get(stamp - offset * _HOUR_MS) for offset in range(8)]
        if any(item is None for item in window):
            continue
        mark = perp_closes.get(stamp - _PERP_TICK_OFFSET_MS)
        if mark is None or mark <= 0.0:
            continue
        panel[stamp] = {
            "funding": sum(float(item[0]) for item in window if item is not None),
            "index": float(hourly[stamp][1]),
            "perp": float(mark),
        }
    return panel


def run_funding_carry_collector(
    config: FundingCarryCollectorConfig,
    *,
    http_get: Callable[..., bytes] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Collect, build the indices, and write the canonical series."""

    moment = now or datetime.now(UTC)
    start_ms = int((moment - timedelta(days=config.lookback_days)).timestamp() * 1000)
    end_ms = int(moment.timestamp() * 1000)
    root = Path(config.output_root)

    receipt: dict[str, object] = {
        "record_type": "funding_carry_collection_receipt",
        "schema_version": 1,
        "mode": config.mode,
        "instruments": list(config.instruments),
        "lookback_days": config.lookback_days,
        "credential_access_attempted": False,
        "credential_values_exposed": False,
        "broker_access_attempted": False,
        "paper_submit_attempted": False,
        "live_authorized": False,
        "live_trading_performed": False,
        "shadow_ledger_appended": False,
        "collected_at": moment.isoformat(),
    }

    if config.mode == "dry_run":
        receipt.update(
            {
                "network_access_attempted": False,
                "state": "dry_run_plan_built",
                "planned_requests": len(config.instruments) * 2,
            }
        )
        return receipt

    per_symbol: dict[str, dict[int, dict[str, float]]] = {}
    blocked: dict[str, str] = {}
    signal_to_noise: dict[str, object] = {}
    for instrument in config.instruments:
        carry_symbol = CARRY_SYMBOL_BY_INSTRUMENT[instrument]
        if instrument not in APPROVED_PERP_SYMBOLS:
            raise ValidationError(f"instrument is not approved: {instrument}")
        funding_rows = _fetch_series(
            config, instrument, "funding", start_ms, end_ms, http_get=http_get
        )
        perp_rows = _fetch_series(
            config, instrument, "perp_kline", start_ms, end_ms, http_get=http_get
        )
        if funding_rows is None or perp_rows is None:
            blocked[carry_symbol] = "venue_series_unavailable"
            continue
        panel = assemble_panel(funding_rows, _closes_from_kline(perp_rows))
        if len(panel) < 2:
            blocked[carry_symbol] = "insufficient_complete_intervals"
            continue
        # The V6.05 preregistration mandates V6.00's precondition. A panel whose
        # basis noise swamps its funding is not a delta-neutral book, and V5.99
        # produced a confident -6.3% from exactly this data before the guard
        # existed. A blocked symbol is not observed, never observed as zero.
        try:
            signal_to_noise[carry_symbol] = validate_signal_to_noise(panel)
        except ValidationError as exc:
            blocked[carry_symbol] = str(exc)
            continue
        per_symbol[carry_symbol] = panel

    rows = []
    diagnostics: dict[str, object] = {}
    for carry_symbol, panel in per_symbol.items():
        try:
            built = build_carry_index(
                panel,
                symbol=carry_symbol,
                cost_bps_per_leg=config.cost_bps_per_leg,
            )
        except ValidationError as exc:
            blocked[carry_symbol] = str(exc)
            continue
        rows.extend(built)
        diagnostics[carry_symbol] = {
            "sessions": len(built),
            "intervals": sum(row.intervals for row in built),
            "first_session": built[0].session.isoformat(),
            "last_session": built[-1].session.isoformat(),
        }

    # The shadow's universe is frozen at three carry legs. A two-leg book is a
    # different hypothesis, so a missing leg blocks the whole collection rather
    # than quietly writing a smaller one.
    missing = [
        symbol
        for symbol in (CARRY_SYMBOL_BY_INSTRUMENT[i] for i in config.instruments)
        if symbol not in diagnostics
    ]
    if not rows or missing:
        receipt.update(
            {
                "network_access_attempted": True,
                "state": "blocked_incomplete_universe" if rows else "blocked_no_usable_series",
                "blocked": blocked,
                "missing_legs": missing,
                "signal_to_noise": signal_to_noise,
            }
        )
        _append_jsonl(root / "collection_receipts.jsonl", receipt)
        return receipt

    # The benchmark spans only sessions every carry symbol produced, so the
    # shadow never sees a session where one leg is silently missing.
    sessions_by_symbol = {
        symbol: {row.session for row in rows if row.symbol == symbol}
        for symbol in diagnostics
    }
    common: set[date] = set.intersection(*sessions_by_symbol.values())
    if not common:
        receipt.update(
            {
                "network_access_attempted": True,
                "state": "blocked_no_common_sessions",
                "blocked": blocked,
            }
        )
        return receipt

    complete = [row for row in rows if row.session in common]
    complete.extend(build_cash_series(sorted(common)))
    written = write_canonical_daily_bars(config.canonical_csv, complete)

    receipt.update(
        {
            "network_access_attempted": True,
            "state": "collected",
            "blocked": blocked,
            "diagnostics": diagnostics,
            "signal_to_noise": signal_to_noise,
            "common_sessions": len(common),
            "canonical": written,
            "benchmark_symbol": CASH_SYMBOL,
        }
    )
    _append_jsonl(root / "collection_receipts.jsonl", receipt)
    return receipt


def _fetch_series(
    config: FundingCarryCollectorConfig,
    instrument: str,
    series: str,
    start_ms: int,
    end_ms: int,
    *,
    http_get: Callable[..., bytes] | None,
) -> list[Mapping[str, object]] | None:
    try:
        result = run_perp_funding_refresh(
            PerpFundingRefreshConfig(
                symbol=instrument,
                series=series,
                output_root=config.output_root,
                mode="live_market_data_fetch",
                start_ms=start_ms,
                end_ms=end_ms,
                live_market_data_fetch_authorized=True,
            ),
            http_get=http_get,
        )
    except (OSError, ValidationError):
        return None
    raw = result.get("raw_response_path")
    if not raw:
        return None
    try:
        payload = json.loads(Path(str(raw)).read_bytes())
    except (OSError, json.JSONDecodeError):
        return None
    body = payload.get("result", payload)
    if series == "funding":
        return list(body) if isinstance(body, list) else None
    return body if isinstance(body, Mapping) else None


def _closes_from_kline(payload: Mapping[str, object]) -> dict[int, float]:
    ticks = payload.get("ticks")
    closes = payload.get("close")
    if not isinstance(ticks, list) or not isinstance(closes, list):
        return {}
    return {
        int(tick): float(close)
        for tick, close in zip(ticks, closes, strict=False)
        if float(close) > 0.0
    }


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--canonical-csv", required=True)
    parser.add_argument(
        "--mode", default="dry_run", choices=("dry_run", "live_market_data_fetch")
    )
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--live-market-data-fetch-authorized", action="store_true")
    parser.add_argument(
        "--instrument",
        action="append",
        dest="instruments",
        choices=sorted(CARRY_SYMBOL_BY_INSTRUMENT),
        help=(
            "Restrict collection to a registered universe. Repeat per leg. "
            "Defaults to all three, which is V6.05; V6.06 is BTC and ETH."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = run_funding_carry_collector(
            FundingCarryCollectorConfig(
                output_root=args.output_root,
                canonical_csv=args.canonical_csv,
                mode=args.mode,
                lookback_days=args.lookback_days,
                live_market_data_fetch_authorized=args.live_market_data_fetch_authorized,
                instruments=(
                    tuple(args.instruments)
                    if args.instruments
                    else tuple(CARRY_SYMBOL_BY_INSTRUMENT)
                ),
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"funding_carry_collector_status=blocked:{exc}")
        return 2
    print(f"funding_carry_collector_status={receipt['state']}")
    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    return 0 if receipt["state"] in ("collected", "dry_run_plan_built") else 3


if __name__ == "__main__":
    raise SystemExit(main())
