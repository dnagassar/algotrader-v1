"""Build the V6.05 synthetic carry indices from a funding panel.

The V6.05 forward shadow holds a long weight in a synthetic index whose daily
change *is* the delta-neutral carry. This module builds that index. It is pure:
bytes and numbers in, canonical daily bars out, no network and no credentials.

The construction is frozen by the V6.05 preregistration
(`rule_fingerprint` `85f03ee2...`) and must not be changed while the window is
open. Per 8-hour interval, on the panel shape V6.00 already produces:

    carry_return(t) = funding(t) + basis(t) - cost(t)
    index(t)        = index(t-1) * (1 + carry_return(t))

`basis(t)` is V6.00's own per-interval basis term — the delta-neutral price
result of being short the perpetual and long the index,
`(index_t/index_{t-1} - 1) - (perp_t/perp_{t-1} - 1)`. The preregistration's
`basis(t) - basis(t-1)` names that increment; this module uses V6.00's
expression verbatim so the two milestones cannot drift apart in sign or scale.

`funding(t)` is the eight-hour sum already assembled by the panel loader, and it
is added rather than subtracted because the book is short the perpetual and a
positive rate is paid by longs to shorts.

Cost is charged only when the book is re-struck, which the preregistration fixes
at monthly renewals, at two legs per renewal. Holding costs nothing, which is
the entire point of the hypothesis.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import math
from pathlib import Path

from algotrader.errors import ValidationError

__all__ = [
    "CARRY_INDEX_BASE",
    "CASH_SYMBOL",
    "CarryIndexRow",
    "build_carry_index",
    "build_cash_series",
    "write_canonical_daily_bars",
]

CARRY_INDEX_BASE = 1000.0
CASH_SYMBOL = "USDCASH"
_INTERVAL_MS = 8 * 60 * 60 * 1000
_CANONICAL_COLUMNS = (
    "symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume",
)


@dataclass(frozen=True, slots=True)
class CarryIndexRow:
    """One session of the synthetic carry index."""

    symbol: str
    session: date
    index_value: float
    intervals: int
    funding: float
    basis: float
    cost: float
    renewed: bool


def build_carry_index(
    panel: Mapping[int, Mapping[str, float]],
    *,
    symbol: str,
    cost_bps_per_leg: float = 5.0,
    legs_per_renewal: int = 2,
    base: float = CARRY_INDEX_BASE,
) -> tuple[CarryIndexRow, ...]:
    """Compound one symbol's 8-hour carry into a daily index.

    A session's value is the compounded result of the intervals that closed
    within it. Sessions with no complete interval are absent rather than carried
    flat: a gap in the venue's data is missing evidence, and writing a zero
    return would silently assert the carry was zero that day.
    """

    if cost_bps_per_leg < 0:
        raise ValidationError("cost_bps_per_leg must not be negative.")
    if legs_per_renewal < 0:
        raise ValidationError("legs_per_renewal must not be negative.")
    if base <= 0:
        raise ValidationError("base must be positive.")

    stamps = sorted(int(stamp) for stamp in panel)
    if len(stamps) < 2:
        raise ValidationError("panel is too short to build a carry index.")

    renewal_cost = (cost_bps_per_leg / 10_000.0) * legs_per_renewal
    by_session: dict[date, list[dict[str, float]]] = {}
    for position in range(1, len(stamps)):
        previous, current = panel[stamps[position - 1]], panel[stamps[position]]
        if stamps[position] - stamps[position - 1] != _INTERVAL_MS:
            # A skipped interval means the book's history is not continuous;
            # compounding across the hole would invent carry that was never
            # observed.
            continue
        basis = (
            (float(current["index"]) / float(previous["index"]) - 1.0)
            - (float(current["perp"]) / float(previous["perp"]) - 1.0)
        )
        session = datetime.fromtimestamp(stamps[position] / 1000.0, UTC).date()
        by_session.setdefault(session, []).append(
            {"funding": float(current["funding"]), "basis": basis}
        )

    rows: list[CarryIndexRow] = []
    index_value = float(base)
    previous_month: tuple[int, int] | None = None
    for session in sorted(by_session):
        month = (session.year, session.month)
        renewed = previous_month is not None and month != previous_month
        previous_month = month
        cost = renewal_cost if renewed else 0.0

        funding_total = math.fsum(item["funding"] for item in by_session[session])
        basis_total = math.fsum(item["basis"] for item in by_session[session])
        for item in by_session[session]:
            index_value *= 1.0 + item["funding"] + item["basis"]
        index_value *= 1.0 - cost
        if not math.isfinite(index_value) or index_value <= 0.0:
            raise ValidationError(
                f"carry index for {symbol} became non-positive on "
                f"{session.isoformat()}; the panel is not a delta-neutral book."
            )
        rows.append(
            CarryIndexRow(
                symbol=symbol,
                session=session,
                index_value=index_value,
                intervals=len(by_session[session]),
                funding=funding_total,
                basis=basis_total,
                cost=cost,
                renewed=renewed,
            )
        )
    return tuple(rows)


def build_cash_series(sessions: Sequence[date], *, base: float = CARRY_INDEX_BASE):
    """The flat benchmark: holding cash rather than running the book."""

    ordered = sorted(set(sessions))
    if not ordered:
        raise ValidationError("cash series requires at least one session.")
    return tuple(
        CarryIndexRow(
            symbol=CASH_SYMBOL,
            session=session,
            index_value=float(base),
            intervals=0,
            funding=0.0,
            basis=0.0,
            cost=0.0,
            renewed=False,
        )
        for session in ordered
    )


def write_canonical_daily_bars(
    path: Path | str,
    rows: Sequence[CarryIndexRow],
) -> dict[str, object]:
    """Write the strict daily-bars CSV the forward shadow reads.

    Open, high, low and close are all the index level: a synthetic index has no
    intraday range, and inventing one would be fabrication rather than
    formatting.
    """

    if not rows:
        raise ValidationError("no rows to write.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda item: (item.symbol, item.session))
    seen: set[tuple[str, date]] = set()
    for row in ordered:
        key = (row.symbol, row.session)
        if key in seen:
            raise ValidationError(
                f"duplicate session {row.session.isoformat()} for {row.symbol}."
            )
        seen.add(key)

    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(_CANONICAL_COLUMNS)
        for row in ordered:
            level = _decimal_text(row.index_value)
            writer.writerow(
                [row.symbol, row.session.isoformat(), level, level, level, level,
                 level, "0"]
            )
    return {
        "record_type": "carry_index_canonical_write",
        "path": str(target),
        "symbols": sorted({row.symbol for row in ordered}),
        "row_count": len(ordered),
        "first_session": ordered[0].session.isoformat(),
        "last_session": ordered[-1].session.isoformat(),
    }


def _decimal_text(value: float) -> str:
    quantised = Decimal(repr(float(value))).quantize(Decimal("0.000000000001"))
    if quantised <= 0:
        raise ValidationError("index level must be positive.")
    return format(quantised, "f")
