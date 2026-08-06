"""Quantify how much a survivor-only universe inflates its own returns.

Pure and offline: it takes per-symbol return observations and produces the
difference between the universe as constructed today and the universe as it
actually existed. The prices themselves are gathered elsewhere, because this
layer must stay free of network and credentials.

The measurement is deliberately **universe-level**. Re-scoring a closed
milestone on an expanded universe would violate the standing prohibitions on
re-running V5.91, V5.92 and V5.98, and would also confound survivorship with
whatever else changed. Comparing the return distribution of survivors against
survivors-plus-dead isolates the bias without re-testing any hypothesis.

Two properties matter more than the headline number:

- A delisted symbol contributes only the life it actually had. It is not
  extrapolated forward and it is not assumed to go to zero — an ETF that closes
  liquidates at net asset value, which is neither.
- A symbol whose price series does not overlap its own listed life is
  **discarded, not repaired**. That is the ticker-reuse case, where the series
  on offer belongs to whoever holds the symbol now.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError

__all__ = [
    "SymbolReturn",
    "SurvivorshipInflation",
    "admit_symbol_observation",
    "measure_length_weighted_inflation",
    "measure_survivorship_inflation",
    "measure_terminal_wealth_inflation",
]


@dataclass(frozen=True, slots=True)
class SymbolReturn:
    """One symbol's realised annualised return over the window it existed."""

    symbol: str
    annualized_return: float
    years: float
    delisted_on: date | None

    @property
    def survived(self) -> bool:
        return self.delisted_on is None


@dataclass(frozen=True, slots=True)
class SurvivorshipInflation:
    """The gap between the universe as constructed and as it existed."""

    survivor_count: int
    delisted_count: int
    discarded_count: int
    survivor_mean: float
    combined_mean: float

    @property
    def inflation(self) -> float:
        """Overstatement embedded in a survivor-only mean, in return points."""

        return self.survivor_mean - self.combined_mean

    def as_payload(self) -> dict[str, object]:
        return {
            "survivor_count": self.survivor_count,
            "delisted_count": self.delisted_count,
            "discarded_count": self.discarded_count,
            "survivor_mean_annualized": self.survivor_mean,
            "combined_mean_annualized": self.combined_mean,
            "inflation_annualized": self.inflation,
            "is_lower_bound": True,
        }


# A security that keeps trading well past its Form 25 did not die. Form 25 is
# a notification of removal from *a listing*, which an exchange transfer also
# triggers, so the filing alone cannot distinguish a closure from a move.
CONTINUATION_GRACE_DAYS = 90


def admit_symbol_observation(
    *,
    symbol: str,
    first_bar: date | None,
    last_bar: date | None,
    delisted_on: date | None,
    grace_days: int = CONTINUATION_GRACE_DAYS,
) -> dict[str, object]:
    """Decide whether a price series may represent this symbol's listed life.

    Three ways a claimed delisting fails to be a death, each seen in real data:

    - **Ticker reuse.** The series begins after the security stopped trading,
      so it belongs to whoever holds the symbol now. `HAO` delisted in 2019 and
      its series begins in 2024 under an unrelated issuer.
    - **Continued trading.** The series runs on past the filing. `NORW` has an
      unbroken series through 2026 despite a 2021 Form 25, because the filing
      recorded a change of listing rather than a closure. Counting it as a
      casualty would put a live fund's truncated return into the dead pool.
    - **No history at all.** The vendor never served it, so it cannot be
      measured either way.
    """

    if first_bar is None or last_bar is None:
        return {"admitted": False, "reason": "no_price_history"}
    if delisted_on is None:
        return {"admitted": True, "reason": "listed", "admit_through": None}
    if first_bar > delisted_on:
        return {"admitted": False, "reason": "ticker_reused_after_delisting"}
    if (last_bar - delisted_on).days > grace_days:
        return {
            "admitted": False,
            "reason": "continued_trading_after_delisting",
            "traded_through": last_bar.isoformat(),
        }
    return {"admitted": True, "reason": "truncated_at_delisting",
            "admit_through": delisted_on.isoformat()}


def measure_survivorship_inflation(
    observations: Sequence[SymbolReturn],
    *,
    discarded: int = 0,
    minimum_years: float = 0.0,
) -> SurvivorshipInflation:
    """Compare a survivor-only mean against the mean including the dead.

    `minimum_years` drops observations too short to carry a meaningful
    annualised figure, applied identically to both groups so it cannot tilt the
    comparison.
    """

    if minimum_years < 0:
        raise ValidationError("minimum_years must not be negative.")
    kept = [item for item in observations if item.years >= minimum_years]
    survivors = [item for item in kept if item.survived]
    delisted = [item for item in kept if not item.survived]
    if not survivors:
        raise ValidationError("no surviving symbols to compare against.")
    survivor_mean = sum(item.annualized_return for item in survivors) / len(survivors)
    combined = survivors + delisted
    combined_mean = sum(item.annualized_return for item in combined) / len(combined)
    return SurvivorshipInflation(
        survivor_count=len(survivors),
        delisted_count=len(delisted),
        discarded_count=discarded,
        survivor_mean=survivor_mean,
        combined_mean=combined_mean,
    )


def measure_length_weighted_inflation(
    observations: Sequence[SymbolReturn],
    *,
    discarded: int = 0,
) -> SurvivorshipInflation:
    """Weight each symbol by how long it actually existed.

    The equal-weighted mean gives a fund that lived five months the same say as
    one that lived seven years, and annualising a five-month return is noisy.
    Because short-lived funds are systematically the failures, that noise is not
    symmetric — it lands mostly in the dead pool.
    """

    survivors = [item for item in observations if item.survived]
    delisted = [item for item in observations if not item.survived]
    if not survivors:
        raise ValidationError("no surviving symbols to compare against.")

    def weighted(group: Sequence[SymbolReturn]) -> float:
        total = sum(item.years for item in group)
        if total <= 0:
            raise ValidationError("total lifetime must be positive.")
        return sum(item.annualized_return * item.years for item in group) / total

    return SurvivorshipInflation(
        survivor_count=len(survivors),
        delisted_count=len(delisted),
        discarded_count=discarded,
        survivor_mean=weighted(survivors),
        combined_mean=weighted(survivors + delisted),
    )


def measure_terminal_wealth_inflation(
    observations: Sequence[SymbolReturn],
    *,
    window_years: float,
    discarded: int = 0,
) -> SurvivorshipInflation:
    """Compare what an equal-weighted holding would actually have been worth.

    This is the portfolio question rather than the average-of-averages question:
    buy every fund at the window's start, hold, and let the dead ones liquidate
    at net asset value into cash for the remainder. Lifespans become comparable
    because every symbol is carried to the same end date.
    """

    if window_years <= 0:
        raise ValidationError("window_years must be positive.")
    survivors = [item for item in observations if item.survived]
    delisted = [item for item in observations if not item.survived]
    if not survivors:
        raise ValidationError("no surviving symbols to compare against.")

    def terminal(group: Sequence[SymbolReturn]) -> float:
        # Growth over the life it had; cash, meaning no further change, after.
        multiples = [
            (1.0 + item.annualized_return) ** item.years for item in group
        ]
        mean_multiple = sum(multiples) / len(multiples)
        if mean_multiple <= 0:
            raise ValidationError("terminal wealth must be positive.")
        return mean_multiple ** (1.0 / window_years) - 1.0

    return SurvivorshipInflation(
        survivor_count=len(survivors),
        delisted_count=len(delisted),
        discarded_count=discarded,
        survivor_mean=terminal(survivors),
        combined_mean=terminal(survivors + delisted),
    )


def annualized_return(first_close: float, last_close: float, years: float) -> float:
    """Compound annual rate implied by two prices and an elapsed time."""

    if first_close <= 0 or last_close <= 0:
        raise ValidationError("closes must be positive.")
    if years <= 0:
        raise ValidationError("years must be positive.")
    return (last_close / first_close) ** (1.0 / years) - 1.0


def summarize_by_group(
    observations: Sequence[SymbolReturn],
    groups: Mapping[str, Sequence[str]],
) -> dict[str, dict[str, object]]:
    """Inflation within each named subset, so one category cannot hide another."""

    by_symbol = {item.symbol: item for item in observations}
    summary: dict[str, dict[str, object]] = {}
    for name, symbols in groups.items():
        members = [by_symbol[s] for s in symbols if s in by_symbol]
        if not any(item.survived for item in members):
            summary[name] = {"error": "no surviving symbols in group"}
            continue
        summary[name] = measure_survivorship_inflation(members).as_payload()
    return summary
