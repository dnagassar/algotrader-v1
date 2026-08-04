"""Frozen V5.95 causal regime classifier.

Four exhaustive, disjoint market states on two axes — trend persistence and
volatility clustering — computed strictly from information available at the
prior close. The regime set is the largest researcher degree of freedom in the
V5.94 ensemble restructure, so it is hash-frozen here and has no revision path:
a different regime set is a different contract requiring its own
preregistration and its own untouched data.

Every statistic is trailing. A full-sample median would leak future information
into past labels, which would let a component look prescient about the very
states it was selected to exploit.

This module is local and research-only. It cannot load credentials, reach a
network or broker, mutate a paper account, or authorize live capital.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from statistics import median, stdev

from algotrader.errors import ValidationError

__all__ = [
    "MEDIAN_WINDOW",
    "RegimeOccupancy",
    "effective_action_labels",
    "regime_occupancy",
    "REFERENCE_SYMBOL",
    "REGIME_LABELS",
    "REGIME_SET_FINGERPRINT",
    "REGIME_SET_VERSION",
    "TREND_WINDOW",
    "VOLATILITY_WINDOW",
    "WARM_UP_SESSIONS",
    "build_regime_contract",
    "classify_regimes",
    "regime_episodes",
]

REGIME_SET_VERSION = "v5_95_regime_set_v1"
REFERENCE_SYMBOL = "SPY"
REGIME_LABELS = ("calm_up", "calm_down", "stressed_up", "stressed_down")
TREND_WINDOW = 200
VOLATILITY_WINDOW = 60
MEDIAN_WINDOW = 1260
WARM_UP_SESSIONS = MEDIAN_WINDOW + VOLATILITY_WINDOW
_TRADING_DAYS = 252.0
REGIME_SET_FINGERPRINT = "51607b2fc64473d37b1fce9bcb31dac70c2689789494321609fca04e2795d83f"


def build_regime_contract() -> dict[str, object]:
    """Return the frozen regime contract, refusing any drift."""

    contract: dict[str, object] = {
        "record_type": "regime_contract",
        "regime_set_version": REGIME_SET_VERSION,
        "reference_symbol": REFERENCE_SYMBOL,
        "labels": list(REGIME_LABELS),
        "regime_count": len(REGIME_LABELS),
        "trend_axis": {
            "mechanism": "directional_drift_persistence",
            "rule": "adjusted_close_t_minus_1_above_sma_200_t_minus_1",
            "window_sessions": TREND_WINDOW,
            "states": ["up", "down"],
        },
        "volatility_axis": {
            "mechanism": "volatility_clustering",
            "rule": (
                "annualized_realized_volatility_t_minus_1_above_trailing_"
                "median_of_prior_1260_daily_values"
            ),
            "volatility_window_sessions": VOLATILITY_WINDOW,
            "median_window_sessions": MEDIAN_WINDOW,
            "estimator": "sample_standard_deviation_n_minus_1",
            "full_sample_statistics_used": False,
            "states": ["calm", "stressed"],
        },
        "causality": {
            "label_for_session_t_uses_data_through": "t_minus_1_close",
            "centered_windows_used": False,
            "hand_drawn_intervals_used": False,
        },
        "warm_up_sessions": WARM_UP_SESSIONS,
        "exhaustive_and_disjoint": True,
        "revision_path_exists": False,
        "safety": {
            "network_access_performed": False,
            "credential_access_performed": False,
            "broker_access_performed": False,
            "paper_mutation_performed": False,
            "live_authorized": False,
        },
    }
    fingerprint = _stable_hash(contract)
    if fingerprint != REGIME_SET_FINGERPRINT:
        raise RuntimeError(f"regime set drift detected: {fingerprint}")
    contract["regime_set_fingerprint"] = fingerprint
    return contract


def classify_regimes(
    dates: Sequence[date],
    closes: Sequence[float],
) -> tuple[str | None, ...]:
    """Label each session, or None while the trailing windows are incomplete.

    The label for session `t` is derived entirely from closes through `t-1`.
    """

    if len(dates) != len(closes):
        raise ValidationError("dates and closes must align.")
    if len(dates) <= WARM_UP_SESSIONS:
        raise ValidationError(
            "series is shorter than the frozen regime warm-up."
        )
    if any(value <= 0.0 or not math.isfinite(value) for value in closes):
        raise ValidationError("reference closes must be positive and finite.")

    returns = [
        closes[index] / closes[index - 1] - 1.0 for index in range(1, len(closes))
    ]
    volatility: list[float | None] = [None] * len(closes)
    for index in range(VOLATILITY_WINDOW, len(closes)):
        window = returns[index - VOLATILITY_WINDOW : index]
        if len(window) != VOLATILITY_WINDOW:
            raise ValidationError("volatility window is incomplete.")
        volatility[index] = stdev(window) * math.sqrt(_TRADING_DAYS)

    labels: list[str | None] = [None] * len(dates)
    for session in range(WARM_UP_SESSIONS, len(dates)):
        prior = session - 1
        trend_window = closes[prior - TREND_WINDOW + 1 : prior + 1]
        if len(trend_window) != TREND_WINDOW:
            raise ValidationError("trend window is incomplete.")
        trend = "up" if closes[prior] > (sum(trend_window) / TREND_WINDOW) else "down"

        history = [
            volatility[index]
            for index in range(prior - MEDIAN_WINDOW + 1, prior + 1)
        ]
        if len(history) != MEDIAN_WINDOW or any(value is None for value in history):
            raise ValidationError("volatility median window is incomplete.")
        current = volatility[prior]
        if current is None or not math.isfinite(current):
            raise ValidationError("realized volatility is invalid.")
        state = "stressed" if current > median(history) else "calm"
        labels[session] = f"{state}_{trend}"

    for label in labels[WARM_UP_SESSIONS:]:
        if label not in REGIME_LABELS:
            raise ValidationError(f"unexpected regime label: {label}")
    return tuple(labels)


def effective_action_labels(
    dates: Sequence[date],
    labels: Sequence[str | None],
) -> tuple[str | None, ...]:
    """The label that actually governs holdings on each session.

    V5.96 scored monthly components against daily labels, so a component could
    be graded across an episode it never held, and out-of-regime sessions could
    carry returns from a position it was still holding. This maps each session
    to the label observed at the most recent prior month-end — the label that
    determined the target now in force — so conditioning and holding coincide.

    The transform is causal: session `t` is governed by a month-end strictly
    before `t`.
    """

    if len(dates) != len(labels):
        raise ValidationError("dates and labels must align.")
    month_end = [
        index
        for index in range(len(dates) - 1)
        if (dates[index].year, dates[index].month)
        != (dates[index + 1].year, dates[index + 1].month)
    ]
    effective: list[str | None] = [None] * len(dates)
    governing: str | None = None
    pointer = 0
    for index in range(len(dates)):
        while pointer < len(month_end) and month_end[pointer] < index:
            governing = labels[month_end[pointer]]
            pointer += 1
        effective[index] = governing
    return tuple(effective)


@dataclass(frozen=True, slots=True)
class RegimeOccupancy:
    """How much of a panel a regime actually occupies."""

    regime: str
    sessions: int
    scoreable_episodes: int
    sufficient: bool

    def as_payload(self) -> dict[str, object]:
        return {
            "regime": self.regime,
            "sessions": self.sessions,
            "scoreable_episodes": self.scoreable_episodes,
            "sufficient": self.sufficient,
        }


def regime_occupancy(
    labels: Sequence[str | None],
    *,
    minimum_episodes: int,
    minimum_episode_sessions: int,
) -> dict[str, RegimeOccupancy]:
    """Report per-regime occupancy so unusable regimes are caught in advance.

    V5.96 declared a component against `calm_down`, which occupied 17 of 3,220
    sessions and yielded zero scoreable episodes; the component was untestable
    rather than tested, and it still consumed a cohort slot and a multiplicity
    share. Occupancy depends only on dates and labels, never on returns, so
    checking it before declaring components is outcome-blind.
    """

    if minimum_episodes < 1 or minimum_episode_sessions < 1:
        raise ValidationError("occupancy minimums must be positive.")
    report: dict[str, RegimeOccupancy] = {}
    for regime in REGIME_LABELS:
        episodes = regime_episodes(
            labels, regime, minimum_sessions=minimum_episode_sessions
        )
        report[regime] = RegimeOccupancy(
            regime=regime,
            sessions=sum(1 for label in labels if label == regime),
            scoreable_episodes=len(episodes),
            sufficient=len(episodes) >= minimum_episodes,
        )
    return report


def regime_episodes(
    labels: Sequence[str | None],
    regime: str,
    *,
    minimum_sessions: int,
) -> tuple[tuple[int, int], ...]:
    """Maximal contiguous runs of `regime`, filtered by minimum length.

    Episodes shorter than the minimum are excluded outright rather than
    counted as losses: a two-day flicker is not evidence either way.
    """

    if regime not in REGIME_LABELS:
        raise ValidationError(f"unknown regime: {regime}")
    if minimum_sessions < 1:
        raise ValidationError("minimum_sessions must be positive.")
    episodes: list[tuple[int, int]] = []
    start: int | None = None
    for index, label in enumerate(labels):
        if label == regime:
            if start is None:
                start = index
        elif start is not None:
            if index - start >= minimum_sessions:
                episodes.append((start, index - 1))
            start = None
    if start is not None and len(labels) - start >= minimum_sessions:
        episodes.append((start, len(labels) - 1))
    return tuple(episodes)


def _stable_hash(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()
