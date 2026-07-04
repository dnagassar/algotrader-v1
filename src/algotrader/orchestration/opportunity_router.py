"""Offline multi-asset opportunity router foundation."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from algotrader.core.time import require_utc_datetime
from algotrader.core.types import Bar
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_FAMILY,
    SMA_TRAINING_WHEEL_STRATEGY_ID,
)
from algotrader.signals.crypto_trend import (
    CRYPTO_TREND_STRATEGY_FAMILY,
    CRYPTO_TREND_STRATEGY_ID,
    CryptoTrendSignalConfig,
    evaluate_crypto_trend_signal,
    normalize_crypto_symbol,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)

OPPORTUNITY_ROUTER_SCHEMA_VERSION = "v5_0_opportunity_router_v1"
OPPORTUNITY_ROUTER_DEFAULT_OUTPUT_ROOT = Path("runs/opportunity_router/latest")
OPPORTUNITY_ROUTER_DEFAULT_SPY_BARS_CSV = Path(
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
OPPORTUNITY_ROUTER_FALLBACK_SPY_BARS_CSV = Path("data/local/m400_spy_daily_bars_200.csv")
OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_BARS_CSV = Path("runs/operator_input/crypto_paper_bars.csv")
OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_VISIBILITY_STATUS = Path(
    "runs/crypto_paper_visibility/latest/latest_status.json"
)

OPPORTUNITY_ROUTER_REQUIRED_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_submit_mode",
)
OPPORTUNITY_ROUTER_SAFETY_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_submit_mode",
    "offline_only",
)

CRYPTO_VOL_ADJUSTED_MOMENTUM_STRATEGY_ID = "crypto_vol_adjusted_momentum_24h_preview"
CRYPTO_VOL_ADJUSTED_MOMENTUM_STRATEGY_FAMILY = "crypto_volatility_adjusted_momentum_preview"
CRYPTO_BREAKOUT_REVERSION_STRATEGY_ID = "crypto_breakout_reversion_20h_flag_preview"
CRYPTO_BREAKOUT_REVERSION_STRATEGY_FAMILY = "crypto_breakout_reversion_flag_preview"

CryptoCandidateStrategy = Literal[
    "trend_momentum",
    "volatility_adjusted_momentum",
    "breakout_reversion_flag",
]

__all__ = [
    "CRYPTO_BREAKOUT_REVERSION_STRATEGY_FAMILY",
    "CRYPTO_BREAKOUT_REVERSION_STRATEGY_ID",
    "CRYPTO_VOL_ADJUSTED_MOMENTUM_STRATEGY_FAMILY",
    "CRYPTO_VOL_ADJUSTED_MOMENTUM_STRATEGY_ID",
    "OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_BARS_CSV",
    "OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_VISIBILITY_STATUS",
    "OPPORTUNITY_ROUTER_DEFAULT_OUTPUT_ROOT",
    "OPPORTUNITY_ROUTER_DEFAULT_SPY_BARS_CSV",
    "OPPORTUNITY_ROUTER_REQUIRED_LABELS",
    "OPPORTUNITY_ROUTER_SCHEMA_VERSION",
    "BarHistoryQuality",
    "CryptoUniverseSource",
    "OpportunityCandidate",
    "OpportunityRouterDecision",
    "build_crypto_opportunity_candidates",
    "build_crypto_opportunity_candidates_for_symbol",
    "build_opportunity_router_packet",
    "build_spy_sma_opportunity_candidate",
    "classify_bar_history",
    "main",
    "normalize_crypto_asset_metadata",
    "render_operating_brief",
    "route_opportunities",
    "run_opportunity_router",
    "write_opportunity_router_artifacts",
]


@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    """Normalized pre-broker opportunity record consumed by the router."""

    candidate_id: str
    as_of: datetime
    asset_class: str
    symbol: str
    venue: str
    source: str
    strategy_id: str
    strategy_family: str
    signal_direction: str
    signal_status: str
    evidence_tier: str
    data_quality_status: str
    history_status: str
    freshness_status: str
    broker_state_mode: str
    orderability_status: str
    blocker_status: str
    blockers: tuple[str, ...]
    risk_notes: tuple[str, ...]
    score_components: Mapping[str, Decimal]
    router_score: Decimal
    labels: tuple[str, ...]
    profit_claim: str = "none"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _required_string(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(self, "as_of", _utc_datetime(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "asset_class",
            _choice(self.asset_class, _ASSET_CLASSES, "asset_class"),
        )
        object.__setattr__(self, "symbol", _normalized_symbol(self.symbol, self.asset_class))
        object.__setattr__(self, "venue", _required_string(self.venue, "venue"))
        object.__setattr__(self, "source", _required_string(self.source, "source"))
        object.__setattr__(
            self,
            "strategy_id",
            _required_string(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "strategy_family",
            _required_string(self.strategy_family, "strategy_family"),
        )
        object.__setattr__(
            self,
            "signal_direction",
            _choice(self.signal_direction, _SIGNAL_DIRECTIONS, "signal_direction"),
        )
        object.__setattr__(
            self,
            "signal_status",
            _choice(self.signal_status, _SIGNAL_STATUSES, "signal_status"),
        )
        object.__setattr__(
            self,
            "evidence_tier",
            _choice(self.evidence_tier, _EVIDENCE_TIERS, "evidence_tier"),
        )
        object.__setattr__(
            self,
            "data_quality_status",
            _choice(
                self.data_quality_status,
                _DATA_QUALITY_STATUSES,
                "data_quality_status",
            ),
        )
        object.__setattr__(
            self,
            "history_status",
            _choice(self.history_status, _HISTORY_STATUSES, "history_status"),
        )
        object.__setattr__(
            self,
            "freshness_status",
            _choice(self.freshness_status, _FRESHNESS_STATUSES, "freshness_status"),
        )
        object.__setattr__(
            self,
            "broker_state_mode",
            _choice(
                self.broker_state_mode,
                _BROKER_STATE_MODES,
                "broker_state_mode",
            ),
        )
        object.__setattr__(
            self,
            "orderability_status",
            _choice(
                self.orderability_status,
                _ORDERABILITY_STATUSES,
                "orderability_status",
            ),
        )
        object.__setattr__(
            self,
            "blocker_status",
            _choice(self.blocker_status, _BLOCKER_STATUSES, "blocker_status"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "risk_notes",
            _string_tuple(self.risk_notes, "risk_notes"),
        )
        components = _score_component_mapping(self.score_components)
        object.__setattr__(self, "score_components", MappingProxyType(components))
        object.__setattr__(
            self,
            "router_score",
            _decimal_value(self.router_score, "router_score"),
        )
        if sum(components.values(), Decimal("0")) != self.router_score:
            raise ValidationError("router_score must equal score_components total.")
        object.__setattr__(self, "labels", _dedupe(self.labels))
        object.__setattr__(
            self,
            "profit_claim",
            _fixed_string(self.profit_claim, "none", "profit_claim"),
        )
        _validate_candidate_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-safe candidate representation."""

        return {
            "candidate_id": self.candidate_id,
            "as_of": self.as_of.isoformat(),
            "asset_class": self.asset_class,
            "symbol": self.symbol,
            "venue": self.venue,
            "source": self.source,
            "strategy_id": self.strategy_id,
            "strategy_family": self.strategy_family,
            "signal_direction": self.signal_direction,
            "signal_status": self.signal_status,
            "evidence_tier": self.evidence_tier,
            "data_quality_status": self.data_quality_status,
            "history_status": self.history_status,
            "freshness_status": self.freshness_status,
            "broker_state_mode": self.broker_state_mode,
            "orderability_status": self.orderability_status,
            "blocker_status": self.blocker_status,
            "blockers": list(self.blockers),
            "risk_notes": list(self.risk_notes),
            "score_components": {
                key: _decimal_text(value)
                for key, value in self.score_components.items()
            },
            "router_score": _decimal_text(self.router_score),
            "labels": list(self.labels),
            "profit_claim": self.profit_claim,
        }


@dataclass(frozen=True, slots=True)
class BarHistoryQuality:
    """Per-symbol history and freshness classification."""

    symbol: str
    asset_class: str
    data_path: str
    source_mode: str
    bar_count: int
    usable_bar_count: int
    required_bar_count: int
    latest_timestamp: datetime | None
    data_quality_status: str
    history_status: str
    freshness_status: str
    duplicate_timestamps: tuple[str, ...]
    gap_count: int
    max_gap_seconds: int
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "data_path": self.data_path,
            "source_mode": self.source_mode,
            "bar_count": self.bar_count,
            "usable_bar_count": self.usable_bar_count,
            "required_bar_count": self.required_bar_count,
            "latest_timestamp": (
                "" if self.latest_timestamp is None else self.latest_timestamp.isoformat()
            ),
            "data_quality_status": self.data_quality_status,
            "history_status": self.history_status,
            "freshness_status": self.freshness_status,
            "duplicate_timestamps": list(self.duplicate_timestamps),
            "gap_count": self.gap_count,
            "max_gap_seconds": self.max_gap_seconds,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class CryptoUniverseSource:
    """Read-only local crypto universe and metadata source."""

    symbols: tuple[str, ...]
    source_mode: str
    source_path: str
    broker_state_mode: str
    capability_source: str
    metadata_by_symbol: Mapping[str, Mapping[str, object]]
    blockers: tuple[str, ...]

    def to_manifest(self, *, bars_symbols: Sequence[str]) -> dict[str, object]:
        bar_symbol_set = set(bars_symbols)
        metadata_symbols = tuple(sorted(self.metadata_by_symbol))
        return {
            "asset_class": "crypto",
            "source_mode": self.source_mode,
            "source_path": self.source_path,
            "broker_state_mode": self.broker_state_mode,
            "capability_source": self.capability_source,
            "symbol_count": len(self.symbols),
            "symbols": list(self.symbols),
            "history_symbol_count": len(bar_symbol_set),
            "history_symbols": sorted(bar_symbol_set),
            "metadata_symbol_count": len(metadata_symbols),
            "metadata_symbols": list(metadata_symbols),
            "metadata_gap_symbols": [
                symbol for symbol in self.symbols if symbol not in self.metadata_by_symbol
            ],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class OpportunityRouterDecision:
    """Deterministic router decision over normalized opportunities."""

    as_of: datetime
    decision: str
    selected_candidate: OpportunityCandidate | None
    eligible_candidates: tuple[OpportunityCandidate, ...]
    candidates: tuple[OpportunityCandidate, ...]
    categories: Mapping[str, tuple[str, ...]]
    top_blockers: tuple[tuple[str, int], ...]
    labels: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        selected = self.selected_candidate
        count_by_asset = _candidate_counts(self.candidates, "asset_class")
        count_by_strategy = _candidate_counts(self.candidates, "strategy_id")
        return {
            "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
            "as_of": self.as_of.isoformat(),
            "decision": self.decision,
            "selected_candidate_id": None if selected is None else selected.candidate_id,
            "selected_candidate": None if selected is None else selected.to_dict(),
            "selected_symbol": "" if selected is None else selected.symbol,
            "selected_asset_class": "" if selected is None else selected.asset_class,
            "selected_strategy_id": "" if selected is None else selected.strategy_id,
            "selected_evidence_tier": "" if selected is None else selected.evidence_tier,
            "selected_router_score": (
                "" if selected is None else _decimal_text(selected.router_score)
            ),
            "selected_score_components": (
                {}
                if selected is None
                else {
                    key: _decimal_text(value)
                    for key, value in selected.score_components.items()
                }
            ),
            "selection_reason": (
                "no_trade_all_candidates_blocked"
                if selected is None
                else "highest_ranked_eligible_candidate"
            ),
            "eligible_candidate_count": len(self.eligible_candidates),
            "blocked_candidate_count": len(self.categories.get("blocked", ())),
            "candidate_count": len(self.candidates),
            "candidate_count_by_asset_class": count_by_asset,
            "candidate_count_by_strategy": count_by_strategy,
            "categories": {
                key: list(value) for key, value in sorted(self.categories.items())
            },
            "top_blockers": [
                {"blocker": blocker, "count": count}
                for blocker, count in self.top_blockers
            ],
            "broker_state_modes": sorted(
                {candidate.broker_state_mode for candidate in self.candidates}
            ),
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "live_mutation_performed": False,
            "network_access_attempted": False,
            "profit_claim": "none",
            "labels": list(self.labels),
            "next_operator_action": _next_operator_action(
                selected_candidate=selected,
                top_blockers=self.top_blockers,
            ),
        }


def build_spy_sma_opportunity_candidate(
    result: EtfSmaSignalResult,
    *,
    source: str = "local_spy_daily_bars",
    venue: str = "NYSE_ARCA",
    broker_state_mode: str = "offline_preview_only",
    orderability_status: str = "orderable",
    as_of: datetime | None = None,
    freshness_max_age: timedelta = timedelta(days=7),
) -> OpportunityCandidate:
    """Adapt the existing SPY SMA 50/200 signal lane into an opportunity."""

    if not isinstance(result, EtfSmaSignalResult):
        raise ValidationError("result must be an EtfSmaSignalResult.")
    candidate_as_of = _utc_datetime(as_of or result.as_of, "as_of")
    latest_bar_at = result.as_of if result.usable_bar_count else None
    freshness_status = _freshness_status(
        latest_timestamp=latest_bar_at,
        as_of=candidate_as_of,
        max_age=freshness_max_age,
    )
    if result.posture == "bullish_risk_on":
        signal_direction = "long"
        signal_status = "trade_candidate"
    elif result.posture == "defensive_risk_off":
        signal_direction = "exit"
        signal_status = "trade_candidate"
    else:
        signal_direction = "none"
        signal_status = "insufficient_history"

    history_status = (
        "sufficient_history"
        if result.usable_bar_count >= result.long_window
        else "insufficient_history"
    )
    data_quality_status = "valid" if result.usable_bar_count else "missing_data"
    risk_notes = (
        "SPY SMA 50/200 remains heartbeat_canary_lane",
        "tiny_notional_preview_only",
        "router_score_is_not_expected_profit",
    )
    labels = (
        "paper_lab_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "offline_only",
    )
    return _candidate(
        candidate_id="equity:SPY:spy_sma_50_200_training_wheel",
        as_of=candidate_as_of,
        asset_class="equity",
        symbol=result.symbol,
        venue=venue,
        source=source,
        strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
        strategy_family=SMA_TRAINING_WHEEL_STRATEGY_FAMILY,
        signal_direction=signal_direction,
        signal_status=signal_status,
        evidence_tier="backtest_supported",
        data_quality_status=data_quality_status,
        history_status=history_status,
        freshness_status=freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status=orderability_status,
        labels=labels,
        risk_notes=risk_notes,
    )


def build_crypto_opportunity_candidates_for_symbol(
    *,
    symbol: str,
    bars: Iterable[Bar],
    as_of: datetime,
    asset_metadata: Mapping[str, object] | None = None,
    broker_state_mode: str = "broker_state_not_observed",
    venue: str = "alpaca_crypto",
    source: str = "local_crypto_bars",
    data_path: str = "in_memory",
    max_bar_age: timedelta = timedelta(hours=2),
) -> tuple[OpportunityCandidate, ...]:
    """Build first-pass crypto opportunities for one symbol."""

    normalized_symbol = normalize_crypto_symbol(symbol)
    as_of_value = _utc_datetime(as_of, "as_of")
    bar_tuple = tuple(bars)
    metadata = (
        normalize_crypto_asset_metadata(asset_metadata)
        if asset_metadata is not None
        else None
    )
    if metadata is not None and metadata["symbol"] != normalized_symbol:
        raise ValidationError("asset_metadata symbol must match symbol.")
    orderability_status = _orderability_status(metadata)

    return (
        _crypto_trend_candidate(
            symbol=normalized_symbol,
            bars=bar_tuple,
            as_of=as_of_value,
            broker_state_mode=broker_state_mode,
            orderability_status=orderability_status,
            venue=venue,
            source=source,
            data_path=data_path,
            max_bar_age=max_bar_age,
        ),
        _crypto_vol_adjusted_momentum_candidate(
            symbol=normalized_symbol,
            bars=bar_tuple,
            as_of=as_of_value,
            broker_state_mode=broker_state_mode,
            orderability_status=orderability_status,
            venue=venue,
            source=source,
            data_path=data_path,
            max_bar_age=max_bar_age,
        ),
        _crypto_breakout_reversion_candidate(
            symbol=normalized_symbol,
            bars=bar_tuple,
            as_of=as_of_value,
            broker_state_mode=broker_state_mode,
            orderability_status=orderability_status,
            venue=venue,
            source=source,
            data_path=data_path,
            max_bar_age=max_bar_age,
        ),
    )


def build_crypto_opportunity_candidates(
    *,
    bars_csv: Path | str = OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_BARS_CSV,
    crypto_visibility_status: Path | str = OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_VISIBILITY_STATUS,
    as_of: datetime,
) -> tuple[
    tuple[OpportunityCandidate, ...],
    dict[str, object],
    dict[str, object],
]:
    """Load local crypto universe/history artifacts and build candidates."""

    as_of_value = _utc_datetime(as_of, "as_of")
    bars_path = Path(bars_csv)
    status_path = Path(crypto_visibility_status)
    bars_by_symbol = _read_crypto_bars_by_symbol(bars_path)
    universe = _load_crypto_universe_source(status_path, bars_by_symbol)
    candidates: list[OpportunityCandidate] = []
    data_quality_records: list[dict[str, object]] = []
    for symbol in universe.symbols:
        symbol_bars = bars_by_symbol.get(symbol, ())
        metadata = universe.metadata_by_symbol.get(symbol)
        candidates.extend(
            build_crypto_opportunity_candidates_for_symbol(
                symbol=symbol,
                bars=symbol_bars,
                as_of=as_of_value,
                asset_metadata=metadata,
                broker_state_mode=universe.broker_state_mode,
                source=universe.source_mode,
                data_path=str(bars_path),
            )
        )
        data_quality_records.append(
            classify_bar_history(
                symbol=symbol,
                asset_class="crypto",
                bars=symbol_bars,
                as_of=as_of_value,
                required_bar_count=50,
                max_bar_age=timedelta(hours=2),
                data_path=str(bars_path),
                source_mode=universe.source_mode,
            ).to_dict()
        )

    universe_manifest = universe.to_manifest(bars_symbols=tuple(bars_by_symbol))
    data_quality_report = {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "asset_class": "crypto",
        "as_of": as_of_value.isoformat(),
        "data_path": str(bars_path),
        "symbol_count": len(universe.symbols),
        "records": data_quality_records,
    }
    return tuple(candidates), universe_manifest, data_quality_report


def classify_bar_history(
    *,
    symbol: str,
    asset_class: str,
    bars: Iterable[Bar],
    as_of: datetime,
    required_bar_count: int,
    max_bar_age: timedelta,
    data_path: str,
    source_mode: str,
) -> BarHistoryQuality:
    """Classify per-symbol bar history without assuming orderability."""

    normalized_symbol = _normalized_symbol(symbol, asset_class)
    as_of_value = _utc_datetime(as_of, "as_of")
    required = _positive_int(required_bar_count, "required_bar_count")
    max_age = _nonnegative_timedelta(max_bar_age, "max_bar_age")
    bar_values = tuple(bars)
    duplicates = _duplicate_timestamps(bar_values)
    ordered = tuple(sorted(bar_values, key=lambda bar: _utc_datetime(bar.timestamp, "timestamp")))
    usable = tuple(
        bar
        for bar in ordered
        if _utc_datetime(bar.timestamp, "timestamp") <= as_of_value
    )
    latest = (
        max((_utc_datetime(bar.timestamp, "timestamp") for bar in usable), default=None)
    )
    gaps = _history_gaps(ordered)
    blockers: list[str] = []
    if not ordered:
        data_quality_status = "missing_data"
        history_status = "missing_history"
        freshness_status = "missing_data"
        blockers.append("missing_history")
    elif duplicates:
        data_quality_status = "duplicate_timestamps"
        history_status = "invalid_history"
        freshness_status = "missing_data" if latest is None else "fresh"
        blockers.append("duplicate_timestamps")
    else:
        data_quality_status = "valid"
        history_status = (
            "sufficient_history" if len(usable) >= required else "insufficient_history"
        )
        if history_status != "sufficient_history":
            blockers.append("insufficient_history")
        freshness_status = _freshness_status(
            latest_timestamp=latest,
            as_of=as_of_value,
            max_age=max_age,
        )
        if freshness_status != "fresh":
            blockers.append(freshness_status)

    return BarHistoryQuality(
        symbol=normalized_symbol,
        asset_class=asset_class,
        data_path=_required_string(data_path, "data_path"),
        source_mode=_required_string(source_mode, "source_mode"),
        bar_count=len(ordered),
        usable_bar_count=len(usable),
        required_bar_count=required,
        latest_timestamp=latest,
        data_quality_status=data_quality_status,
        history_status=history_status,
        freshness_status=freshness_status,
        duplicate_timestamps=tuple(timestamp.isoformat() for timestamp in duplicates),
        gap_count=gaps["gap_count"],
        max_gap_seconds=gaps["max_gap_seconds"],
        blockers=_dedupe(blockers),
    )


def normalize_crypto_asset_metadata(value: Mapping[str, object] | object) -> dict[str, object]:
    """Normalize allowlisted crypto orderability metadata variants."""

    raw = _asset_metadata_payload(value)
    symbol_text = _first_text(raw, "symbol", "name")
    symbol = normalize_crypto_symbol(symbol_text)
    asset_class = _normalized_enum_text(_first_text(raw, "asset_class", "class"))
    if asset_class and asset_class != "crypto":
        raise ValidationError("asset metadata must be crypto.")
    tradable = _bool_field(raw, "tradable")
    status = _normalized_enum_text(_first_text(raw, "status"))
    min_notional = _first_text(raw, "min_notional", "min_order_notional")
    min_order_size = _first_text(raw, "min_order_size")
    min_trade_increment = _first_text(raw, "min_trade_increment")
    price_increment = _first_text(raw, "price_increment")
    qty_increment = _first_text(raw, "qty_increment", "min_order_increment")
    return {
        "symbol": symbol,
        "asset_class": "crypto",
        "tradable": tradable,
        "status": status,
        "marginable": _bool_field(raw, "marginable"),
        "fractionable": _bool_field(raw, "fractionable"),
        "min_notional": min_notional,
        "min_order_size": min_order_size,
        "min_trade_increment": min_trade_increment,
        "price_increment": price_increment,
        "qty_increment": qty_increment,
        "metadata_fields_present": sorted(
            key
            for key, item in {
                "tradable": tradable,
                "status": status,
                "min_notional": min_notional,
                "min_order_size": min_order_size,
                "min_trade_increment": min_trade_increment,
                "price_increment": price_increment,
                "qty_increment": qty_increment,
            }.items()
            if item not in (None, "")
        ),
    }


def route_opportunities(
    candidates: Iterable[OpportunityCandidate],
    *,
    as_of: datetime,
) -> OpportunityRouterDecision:
    """Rank opportunities and select exactly one eligible candidate or no-trade."""

    as_of_value = _utc_datetime(as_of, "as_of")
    candidate_values = _candidate_tuple(candidates)
    eligible = tuple(candidate for candidate in candidate_values if _is_selectable(candidate))
    ranked = tuple(sorted(eligible, key=_candidate_rank_key))
    selected = ranked[0] if ranked else None
    categories = _candidate_categories(candidate_values, selected)
    top_blockers = tuple(
        sorted(
            Counter(
                blocker
                for candidate in candidate_values
                for blocker in candidate.blockers
            ).items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    )
    labels = _dedupe(
        (
            *OPPORTUNITY_ROUTER_REQUIRED_LABELS,
            "offline_only",
            "router_score_is_not_expected_profit",
        )
    )
    return OpportunityRouterDecision(
        as_of=as_of_value,
        decision="selected" if selected is not None else "no_trade",
        selected_candidate=selected,
        eligible_candidates=ranked,
        candidates=candidate_values,
        categories=MappingProxyType(categories),
        top_blockers=top_blockers,
        labels=labels,
    )


def build_opportunity_router_packet(
    *,
    candidates: Iterable[OpportunityCandidate],
    as_of: datetime,
    universe_manifest: Mapping[str, object] | None = None,
    strategy_manifest: Mapping[str, object] | None = None,
    data_quality_report: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the complete primitive-only router packet."""

    as_of_value = _utc_datetime(as_of, "as_of")
    candidate_values = _candidate_tuple(candidates)
    decision = route_opportunities(candidate_values, as_of=as_of_value)
    return {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "as_of": as_of_value.isoformat(),
        "candidates": [candidate.to_dict() for candidate in candidate_values],
        "router_decision": decision.to_dict(),
        "universe_manifest": dict(universe_manifest or _default_universe_manifest(candidate_values)),
        "strategy_manifest": dict(strategy_manifest or _default_strategy_manifest(candidate_values)),
        "data_quality_report": dict(data_quality_report or _default_data_quality_report(candidate_values, as_of_value)),
        "safety": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_performed": False,
            "live_mutation_performed": False,
            "network_access_attempted": False,
            "broker_read_performed_current_run": False,
            "profit_claim": "none",
            "labels": list(OPPORTUNITY_ROUTER_SAFETY_LABELS),
        },
    }


def run_opportunity_router(
    *,
    output_root: Path | str = OPPORTUNITY_ROUTER_DEFAULT_OUTPUT_ROOT,
    spy_bars_csv: Path | str | None = None,
    crypto_bars_csv: Path | str = OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_BARS_CSV,
    crypto_visibility_status: Path | str = OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_VISIBILITY_STATUS,
    as_of: datetime | str | None = None,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Run the deterministic local opportunity router and optionally write artifacts."""

    as_of_value = _utc_datetime(as_of or datetime.now(UTC), "as_of")
    spy_path = _resolve_spy_bars_path(spy_bars_csv)
    spy_candidates, spy_quality = _build_spy_candidates_from_csv(spy_path, as_of_value)
    (
        crypto_candidates,
        crypto_universe_manifest,
        crypto_data_quality_report,
    ) = build_crypto_opportunity_candidates(
        bars_csv=crypto_bars_csv,
        crypto_visibility_status=crypto_visibility_status,
        as_of=as_of_value,
    )
    candidates = (*spy_candidates, *crypto_candidates)
    universe_manifest = _combined_universe_manifest(
        candidates=candidates,
        spy_path=spy_path,
        crypto_manifest=crypto_universe_manifest,
    )
    data_quality_report = _combined_data_quality_report(
        as_of=as_of_value,
        spy_quality=spy_quality,
        crypto_report=crypto_data_quality_report,
    )
    strategy_manifest = _default_strategy_manifest(candidates)
    packet = build_opportunity_router_packet(
        candidates=candidates,
        as_of=as_of_value,
        universe_manifest=universe_manifest,
        strategy_manifest=strategy_manifest,
        data_quality_report=data_quality_report,
    )
    if write_artifacts:
        packet["artifact_paths"] = write_opportunity_router_artifacts(output_root, packet)
    return packet


def write_opportunity_router_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the local opportunity router."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    candidates_payload = {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "as_of": packet.get("as_of", ""),
        "candidates": packet.get("candidates", []),
    }
    paths = {
        "opportunity_candidates_json": root / "opportunity_candidates.json",
        "opportunity_candidates_csv": root / "opportunity_candidates.csv",
        "router_decision": root / "router_decision.json",
        "operating_brief": root / "operating_brief.md",
        "operating_record": root / "operating_record.jsonl",
        "universe_manifest": root / "universe_manifest.json",
        "strategy_manifest": root / "strategy_manifest.json",
        "data_quality_report": root / "data_quality_report.json",
    }
    _write_json(paths["opportunity_candidates_json"], candidates_payload)
    _write_candidates_csv(
        paths["opportunity_candidates_csv"],
        _mapping_sequence(packet.get("candidates")),
    )
    _write_json(paths["router_decision"], _mapping(packet.get("router_decision")))
    paths["operating_brief"].write_text(
        render_operating_brief(packet) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths["operating_record"].write_text(
        json.dumps(
            {
                "record_type": "opportunity_router_decision",
                "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
                "as_of": packet.get("as_of", ""),
                "router_decision": packet.get("router_decision", {}),
                "safety": packet.get("safety", {}),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_json(paths["universe_manifest"], _mapping(packet.get("universe_manifest")))
    _write_json(paths["strategy_manifest"], _mapping(packet.get("strategy_manifest")))
    _write_json(paths["data_quality_report"], _mapping(packet.get("data_quality_report")))
    manifest_path = root / "manifest.json"
    manifest = {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "as_of": packet.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: {
                "path": str(path),
                "sha256": _file_sha256(path),
            }
            for key, path in sorted(paths.items())
        },
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "network_access_attempted": False,
        "generated_under_runs": "runs" in root.parts,
    }
    _write_json(manifest_path, manifest)
    paths["manifest"] = manifest_path
    return {key: str(path) for key, path in sorted(paths.items())}


def render_operating_brief(packet: Mapping[str, object]) -> str:
    """Render the operator-facing opportunity router brief."""

    decision = _mapping(packet.get("router_decision"))
    selected = decision.get("selected_candidate")
    selected_mapping = selected if isinstance(selected, Mapping) else {}
    count_by_asset = _mapping(decision.get("candidate_count_by_asset_class"))
    count_by_strategy = _mapping(decision.get("candidate_count_by_strategy"))
    top_blockers = _mapping_sequence(decision.get("top_blockers"))
    score_components = _mapping(decision.get("selected_score_components"))
    safety = _mapping(packet.get("safety"))
    return "\n".join(
        [
            "# Opportunity Router Operating Brief",
            "",
            f"- As-of timestamp: `{packet.get('as_of', '')}`",
            "- Supported asset universes: "
            f"`{', '.join(_supported_universes(_mapping(packet.get('universe_manifest'))))}`",
            "- Supported strategy sources: "
            f"`{', '.join(str(key) for key in sorted(count_by_strategy))}`",
            f"- Candidate count by asset class: `{json.dumps(count_by_asset, sort_keys=True)}`",
            f"- Candidate count by strategy: `{json.dumps(count_by_strategy, sort_keys=True)}`",
            f"- Eligible candidate count: `{decision.get('eligible_candidate_count', 0)}`",
            f"- Blocked candidate count: `{decision.get('blocked_candidate_count', 0)}`",
            f"- Selected opportunity or no-trade: `{decision.get('decision', '')}`",
            f"- Selected symbol: `{selected_mapping.get('symbol', '')}`",
            f"- Selected asset class: `{selected_mapping.get('asset_class', '')}`",
            f"- Selected strategy: `{selected_mapping.get('strategy_id', '')}`",
            f"- Selected evidence tier: `{selected_mapping.get('evidence_tier', '')}`",
            "- Router score components: "
            f"`{json.dumps(score_components, sort_keys=True)}`",
            f"- Top blockers: `{_brief_blockers(top_blockers)}`",
            f"- Broker-state mode: `{_brief_broker_state(decision)}`",
            "- paper_submit_authorized=false",
            f"- paper_submit_performed={_bool_text(safety.get('paper_submit_performed'))}",
            f"- broker_mutation_performed={_bool_text(safety.get('broker_mutation_performed'))}",
            f"- live_mutation_performed={_bool_text(safety.get('live_mutation_performed'))}",
            f"- Next operator action: `{decision.get('next_operator_action', '')}`",
            f"- Safety labels: `{', '.join(_string_sequence(safety.get('labels')))}`",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="opportunity-router",
        description="Run the offline multi-asset no-submit opportunity router.",
    )
    parser.add_argument(
        "--output-root",
        default=str(OPPORTUNITY_ROUTER_DEFAULT_OUTPUT_ROOT),
        help="Output directory for ignored router artifacts.",
    )
    parser.add_argument(
        "--spy-bars-csv",
        default="",
        help="Local SPY daily bars CSV. Defaults to operator input then fixture fallback.",
    )
    parser.add_argument(
        "--crypto-bars-csv",
        default=str(OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_BARS_CSV),
        help="Local crypto bars CSV.",
    )
    parser.add_argument(
        "--crypto-visibility-status",
        default=str(OPPORTUNITY_ROUTER_DEFAULT_CRYPTO_VISIBILITY_STATUS),
        help="Local crypto visibility latest_status.json.",
    )
    parser.add_argument(
        "--as-of",
        default="",
        help="Optional UTC ISO as-of timestamp for deterministic runs.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Console output format.",
    )
    args = parser.parse_args(argv)

    packet = run_opportunity_router(
        output_root=args.output_root,
        spy_bars_csv=args.spy_bars_csv or None,
        crypto_bars_csv=args.crypto_bars_csv,
        crypto_visibility_status=args.crypto_visibility_status,
        as_of=args.as_of or None,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True, indent=2))
    else:
        decision = _mapping(packet.get("router_decision"))
        print(f"opportunity_router_decision={decision.get('decision', '')}")
        print(f"selected_candidate_id={decision.get('selected_candidate_id')}")
        print(f"selected_symbol={decision.get('selected_symbol', '')}")
        print(f"selected_strategy_id={decision.get('selected_strategy_id', '')}")
        print(f"eligible_candidate_count={decision.get('eligible_candidate_count', 0)}")
        print(f"blocked_candidate_count={decision.get('blocked_candidate_count', 0)}")
        print("paper_submit_authorized=false")
        print("paper_submit_performed=false")
        print("broker_mutation_performed=false")
        print("live_mutation_performed=false")
        artifact_paths = _mapping(packet.get("artifact_paths"))
        for key in sorted(artifact_paths):
            print(f"artifact_{key}={artifact_paths[key]}")
    return 0


def _build_spy_candidates_from_csv(
    path: Path,
    as_of: datetime,
) -> tuple[tuple[OpportunityCandidate, ...], dict[str, object]]:
    if not path.is_file():
        candidate = _candidate(
            candidate_id="equity:SPY:spy_sma_50_200_training_wheel",
            as_of=as_of,
            asset_class="equity",
            symbol="SPY",
            venue="NYSE_ARCA",
            source=str(path),
            strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
            strategy_family=SMA_TRAINING_WHEEL_STRATEGY_FAMILY,
            signal_direction="none",
            signal_status="blocked",
            evidence_tier="backtest_supported",
            data_quality_status="missing_data",
            history_status="missing_history",
            freshness_status="missing_data",
            broker_state_mode="offline_preview_only",
            orderability_status="orderable",
            labels=_spy_labels(),
            risk_notes=("SPY bars CSV missing", "router_score_is_not_expected_profit"),
        )
        quality = {
            "asset_class": "equity",
            "symbol": "SPY",
            "data_path": str(path),
            "data_quality_status": "missing_data",
            "history_status": "missing_history",
            "freshness_status": "missing_data",
            "blockers": ["missing_history"],
        }
        return (candidate,), quality
    try:
        bars = _read_spy_bars(path)
        result = evaluate_etf_sma_signal(bars, EtfSmaSignalConfig(as_of=as_of, symbol="SPY"))
        candidate = build_spy_sma_opportunity_candidate(
            result,
            source=str(path),
            broker_state_mode="offline_preview_only",
            orderability_status="orderable",
            as_of=as_of,
        )
        quality = {
            "asset_class": "equity",
            "symbol": "SPY",
            "data_path": str(path),
            "data_quality_status": candidate.data_quality_status,
            "history_status": candidate.history_status,
            "freshness_status": candidate.freshness_status,
            "bar_count": len(bars),
            "usable_bar_count": result.usable_bar_count,
            "latest_timestamp": result.as_of.isoformat(),
            "blockers": list(candidate.blockers),
        }
        return (candidate,), quality
    except ValidationError as exc:
        candidate = _candidate(
            candidate_id="equity:SPY:spy_sma_50_200_training_wheel",
            as_of=as_of,
            asset_class="equity",
            symbol="SPY",
            venue="NYSE_ARCA",
            source=str(path),
            strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
            strategy_family=SMA_TRAINING_WHEEL_STRATEGY_FAMILY,
            signal_direction="none",
            signal_status="blocked",
            evidence_tier="backtest_supported",
            data_quality_status="invalid_data",
            history_status="invalid_history",
            freshness_status="missing_data",
            broker_state_mode="offline_preview_only",
            orderability_status="orderable",
            labels=_spy_labels(),
            risk_notes=(f"SPY bars invalid: {exc}", "router_score_is_not_expected_profit"),
        )
        quality = {
            "asset_class": "equity",
            "symbol": "SPY",
            "data_path": str(path),
            "data_quality_status": "invalid_data",
            "history_status": "invalid_history",
            "freshness_status": "missing_data",
            "blockers": list(candidate.blockers),
        }
        return (candidate,), quality


def _crypto_trend_candidate(
    *,
    symbol: str,
    bars: tuple[Bar, ...],
    as_of: datetime,
    broker_state_mode: str,
    orderability_status: str,
    venue: str,
    source: str,
    data_path: str,
    max_bar_age: timedelta,
) -> OpportunityCandidate:
    quality = classify_bar_history(
        symbol=symbol,
        asset_class="crypto",
        bars=bars,
        as_of=as_of,
        required_bar_count=50,
        max_bar_age=max_bar_age,
        data_path=data_path,
        source_mode=source,
    )
    signal_status = _signal_status_from_quality(quality)
    signal_direction = "none"
    risk_notes = [
        "crypto SMA 20/50 preview signal_only",
        "router_score_is_not_expected_profit",
    ]
    if quality.history_status == "sufficient_history" and quality.data_quality_status == "valid":
        try:
            result = evaluate_crypto_trend_signal(
                bars,
                CryptoTrendSignalConfig(as_of=as_of, symbol=symbol),
            )
        except ValidationError as exc:
            signal_status = "blocked"
            risk_notes.append(f"crypto trend evaluation invalid: {exc}")
        else:
            if result.posture == "risk_on":
                signal_status = "trade_candidate"
                signal_direction = "long"
            elif result.posture == "risk_off":
                signal_status = "no_trade"
            else:
                signal_status = "insufficient_history"
            if result.short_sma is not None and result.long_sma is not None:
                risk_notes.append(
                    f"sma20={_decimal_text(result.short_sma)} sma50={_decimal_text(result.long_sma)}"
                )
    return _candidate(
        candidate_id=f"crypto:{symbol}:{CRYPTO_TREND_STRATEGY_ID}",
        as_of=as_of,
        asset_class="crypto",
        symbol=symbol,
        venue=venue,
        source=source,
        strategy_id=CRYPTO_TREND_STRATEGY_ID,
        strategy_family=CRYPTO_TREND_STRATEGY_FAMILY,
        signal_direction=signal_direction,
        signal_status=signal_status,
        evidence_tier="signal_only",
        data_quality_status=quality.data_quality_status,
        history_status=quality.history_status,
        freshness_status=quality.freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status=orderability_status,
        labels=_crypto_labels(),
        risk_notes=tuple(risk_notes),
    )


def _crypto_vol_adjusted_momentum_candidate(
    *,
    symbol: str,
    bars: tuple[Bar, ...],
    as_of: datetime,
    broker_state_mode: str,
    orderability_status: str,
    venue: str,
    source: str,
    data_path: str,
    max_bar_age: timedelta,
) -> OpportunityCandidate:
    quality = classify_bar_history(
        symbol=symbol,
        asset_class="crypto",
        bars=bars,
        as_of=as_of,
        required_bar_count=30,
        max_bar_age=max_bar_age,
        data_path=data_path,
        source_mode=source,
    )
    signal_status = _signal_status_from_quality(quality)
    signal_direction = "none"
    risk_notes = [
        "volatility-adjusted momentum is signal_only",
        "router_score_is_not_expected_profit",
    ]
    strength = Decimal("0")
    usable = _usable_ordered_bars(bars, as_of)
    if quality.history_status == "sufficient_history" and quality.data_quality_status == "valid":
        lookback = 24
        recent = usable[-1].close
        prior = usable[-lookback - 1].close
        raw_return = (recent - prior) / prior
        vol_proxy = _mean_abs_return(usable[-lookback - 1 :])
        adjusted = raw_return / vol_proxy if vol_proxy > Decimal("0") else Decimal("0")
        strength = min(max(adjusted, Decimal("0")), Decimal("5"))
        risk_notes.append(
            "return_24h="
            f"{_decimal_text(raw_return)} vol_proxy={_decimal_text(vol_proxy)}"
        )
        if raw_return > Decimal("0"):
            signal_status = "trade_candidate"
            signal_direction = "long"
        else:
            signal_status = "no_trade"
    return _candidate(
        candidate_id=f"crypto:{symbol}:{CRYPTO_VOL_ADJUSTED_MOMENTUM_STRATEGY_ID}",
        as_of=as_of,
        asset_class="crypto",
        symbol=symbol,
        venue=venue,
        source=source,
        strategy_id=CRYPTO_VOL_ADJUSTED_MOMENTUM_STRATEGY_ID,
        strategy_family=CRYPTO_VOL_ADJUSTED_MOMENTUM_STRATEGY_FAMILY,
        signal_direction=signal_direction,
        signal_status=signal_status,
        evidence_tier="signal_only",
        data_quality_status=quality.data_quality_status,
        history_status=quality.history_status,
        freshness_status=quality.freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status=orderability_status,
        labels=_crypto_labels(),
        risk_notes=tuple(risk_notes),
        signal_strength_score=strength,
    )


def _crypto_breakout_reversion_candidate(
    *,
    symbol: str,
    bars: tuple[Bar, ...],
    as_of: datetime,
    broker_state_mode: str,
    orderability_status: str,
    venue: str,
    source: str,
    data_path: str,
    max_bar_age: timedelta,
) -> OpportunityCandidate:
    quality = classify_bar_history(
        symbol=symbol,
        asset_class="crypto",
        bars=bars,
        as_of=as_of,
        required_bar_count=21,
        max_bar_age=max_bar_age,
        data_path=data_path,
        source_mode=source,
    )
    signal_status = _signal_status_from_quality(quality)
    signal_direction = "none"
    risk_notes = [
        "breakout/reversion flag is signal_only",
        "router_score_is_not_expected_profit",
    ]
    strength = Decimal("0")
    usable = _usable_ordered_bars(bars, as_of)
    if quality.history_status == "sufficient_history" and quality.data_quality_status == "valid":
        window = usable[-21:-1]
        latest = usable[-1]
        prior_high = max(bar.high for bar in window)
        prior_low = min(bar.low for bar in window)
        if latest.close > prior_high:
            signal_status = "trade_candidate"
            signal_direction = "long"
            strength = Decimal("3")
            risk_notes.append("breakout_above_prior_20_bar_high")
        elif latest.close < prior_low:
            signal_status = "trade_candidate"
            signal_direction = "long"
            strength = Decimal("2")
            risk_notes.append("reversion_watch_below_prior_20_bar_low")
        else:
            signal_status = "no_trade"
            risk_notes.append("inside_prior_20_bar_range")
    return _candidate(
        candidate_id=f"crypto:{symbol}:{CRYPTO_BREAKOUT_REVERSION_STRATEGY_ID}",
        as_of=as_of,
        asset_class="crypto",
        symbol=symbol,
        venue=venue,
        source=source,
        strategy_id=CRYPTO_BREAKOUT_REVERSION_STRATEGY_ID,
        strategy_family=CRYPTO_BREAKOUT_REVERSION_STRATEGY_FAMILY,
        signal_direction=signal_direction,
        signal_status=signal_status,
        evidence_tier="signal_only",
        data_quality_status=quality.data_quality_status,
        history_status=quality.history_status,
        freshness_status=quality.freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status=orderability_status,
        labels=_crypto_labels(),
        risk_notes=tuple(risk_notes),
        signal_strength_score=strength,
    )


def _candidate(
    *,
    candidate_id: str,
    as_of: datetime,
    asset_class: str,
    symbol: str,
    venue: str,
    source: str,
    strategy_id: str,
    strategy_family: str,
    signal_direction: str,
    signal_status: str,
    evidence_tier: str,
    data_quality_status: str,
    history_status: str,
    freshness_status: str,
    broker_state_mode: str,
    orderability_status: str,
    labels: tuple[str, ...],
    risk_notes: tuple[str, ...],
    extra_blockers: tuple[str, ...] = (),
    signal_strength_score: Decimal = Decimal("0"),
) -> OpportunityCandidate:
    blockers = _candidate_blockers(
        signal_status=signal_status,
        data_quality_status=data_quality_status,
        history_status=history_status,
        freshness_status=freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status=orderability_status,
        labels=labels,
        extra_blockers=extra_blockers,
    )
    blocker_status = "blocked" if blockers else "eligible"
    score_components = _score_components(
        signal_status=signal_status,
        evidence_tier=evidence_tier,
        data_quality_status=data_quality_status,
        history_status=history_status,
        freshness_status=freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status=orderability_status,
        labels=labels,
        signal_strength_score=signal_strength_score,
    )
    return OpportunityCandidate(
        candidate_id=candidate_id,
        as_of=as_of,
        asset_class=asset_class,
        symbol=symbol,
        venue=venue,
        source=source,
        strategy_id=strategy_id,
        strategy_family=strategy_family,
        signal_direction=signal_direction,
        signal_status=signal_status,
        evidence_tier=evidence_tier,
        data_quality_status=data_quality_status,
        history_status=history_status,
        freshness_status=freshness_status,
        broker_state_mode=broker_state_mode,
        orderability_status=orderability_status,
        blocker_status=blocker_status,
        blockers=blockers,
        risk_notes=risk_notes,
        score_components=score_components,
        router_score=sum(score_components.values(), Decimal("0")),
        labels=labels,
        profit_claim="none",
    )


def _candidate_blockers(
    *,
    signal_status: str,
    data_quality_status: str,
    history_status: str,
    freshness_status: str,
    broker_state_mode: str,
    orderability_status: str,
    labels: tuple[str, ...],
    extra_blockers: tuple[str, ...],
) -> tuple[str, ...]:
    blockers: list[str] = list(extra_blockers)
    if signal_status != "trade_candidate":
        blockers.append(f"signal_status_{signal_status}")
    if data_quality_status != "valid":
        blockers.append(data_quality_status)
    if history_status != "sufficient_history":
        blockers.append(history_status)
    if freshness_status != "fresh":
        blockers.append(freshness_status)
    if broker_state_mode not in _SELECTABLE_BROKER_STATE_MODES:
        blockers.append(broker_state_mode)
    if orderability_status != "orderable":
        blockers.append(orderability_status)
    for label in OPPORTUNITY_ROUTER_REQUIRED_LABELS:
        if label not in labels:
            blockers.append(f"missing_required_label:{label}")
    if not ({"signal_evaluation_only", "research_only"} & set(labels)):
        blockers.append("missing_signal_or_research_label")
    return _dedupe(blockers)


def _score_components(
    *,
    signal_status: str,
    evidence_tier: str,
    data_quality_status: str,
    history_status: str,
    freshness_status: str,
    broker_state_mode: str,
    orderability_status: str,
    labels: tuple[str, ...],
    signal_strength_score: Decimal,
) -> dict[str, Decimal]:
    signal = Decimal("40") if signal_status == "trade_candidate" else Decimal("0")
    evidence = {
        "backtest_supported": Decimal("25"),
        "signal_only": Decimal("10"),
        "research_only": Decimal("5"),
        "future_placeholder": Decimal("0"),
    }[evidence_tier]
    data_quality = (
        Decimal("15")
        if data_quality_status == "valid"
        and history_status == "sufficient_history"
        and freshness_status == "fresh"
        else Decimal("0")
    )
    broker_state = (
        Decimal("10") if broker_state_mode in _SELECTABLE_BROKER_STATE_MODES else Decimal("0")
    )
    orderability = Decimal("5") if orderability_status == "orderable" else Decimal("0")
    safety = (
        Decimal("5")
        if set(OPPORTUNITY_ROUTER_REQUIRED_LABELS).issubset(set(labels))
        and "profit_claim=none" in labels
        else Decimal("0")
    )
    signal_strength = min(max(signal_strength_score, Decimal("0")), Decimal("5"))
    return {
        "signal": signal,
        "evidence": evidence,
        "data_quality": data_quality,
        "broker_state": broker_state,
        "orderability": orderability,
        "safety": safety,
        "signal_strength": signal_strength,
    }


def _is_selectable(candidate: OpportunityCandidate) -> bool:
    return (
        candidate.blocker_status == "eligible"
        and not candidate.blockers
        and candidate.signal_status == "trade_candidate"
        and candidate.data_quality_status == "valid"
        and candidate.history_status == "sufficient_history"
        and candidate.freshness_status == "fresh"
        and candidate.broker_state_mode in _SELECTABLE_BROKER_STATE_MODES
        and candidate.orderability_status == "orderable"
        and candidate.profit_claim == "none"
        and set(OPPORTUNITY_ROUTER_REQUIRED_LABELS).issubset(set(candidate.labels))
    )


def _candidate_rank_key(candidate: OpportunityCandidate) -> tuple[Decimal, int, str, str, str]:
    return (
        -candidate.router_score,
        _EVIDENCE_RANK[candidate.evidence_tier],
        candidate.asset_class,
        candidate.symbol,
        candidate.candidate_id,
    )


def _candidate_categories(
    candidates: tuple[OpportunityCandidate, ...],
    selected: OpportunityCandidate | None,
) -> dict[str, tuple[str, ...]]:
    selected_id = "" if selected is None else selected.candidate_id
    selectable = tuple(candidate for candidate in candidates if _is_selectable(candidate))
    return {
        "selected": (selected_id,) if selected_id else (),
        "eligible": tuple(candidate.candidate_id for candidate in selectable),
        "blocked": tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.blocker_status == "blocked"
        ),
        "stale_data": tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.freshness_status in {"stale_data", "missing_data"}
        ),
        "insufficient_history": tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.history_status in {"insufficient_history", "missing_history"}
        ),
        "metadata_blocked": tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.orderability_status != "orderable"
        ),
        "broker_state_not_observed": tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.broker_state_mode in {
                "broker_state_not_observed",
                "offline_preview_only",
                "unknown",
            }
        ),
        "signal_only": tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.evidence_tier == "signal_only"
        ),
        "backtest_supported": tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.evidence_tier == "backtest_supported"
        ),
    }


def _load_crypto_universe_source(
    status_path: Path,
    bars_by_symbol: Mapping[str, tuple[Bar, ...]],
) -> CryptoUniverseSource:
    if status_path.is_file():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            status = {}
        if isinstance(status, Mapping):
            capability = status.get("crypto_capability")
            capability_mapping = capability if isinstance(capability, Mapping) else {}
            symbols = _crypto_symbols_from_status(status, capability_mapping, bars_by_symbol)
            metadata = _metadata_from_status(status, capability_mapping)
            broker_state_mode = _broker_state_mode(status.get("broker_state_mode"))
            capability_source = _text(status.get("capability_source")) or "local_artifact"
            blockers = tuple(_string_sequence(status.get("blockers")))
            return CryptoUniverseSource(
                symbols=symbols,
                source_mode="local_crypto_visibility_artifact",
                source_path=str(status_path),
                broker_state_mode=broker_state_mode,
                capability_source=capability_source,
                metadata_by_symbol=MappingProxyType(metadata),
                blockers=blockers,
            )
    symbols = tuple(sorted(bars_by_symbol))
    if not symbols:
        symbols = ("BTCUSD",)
    return CryptoUniverseSource(
        symbols=symbols,
        source_mode="local_crypto_bars_only_no_visibility_artifact",
        source_path=str(status_path),
        broker_state_mode="broker_state_not_observed",
        capability_source="not_observed",
        metadata_by_symbol=MappingProxyType({}),
        blockers=("crypto_visibility_artifact_missing",),
    )


def _metadata_from_status(
    status: Mapping[str, object],
    capability: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    metadata: dict[str, Mapping[str, object]] = {}
    asset_records = status.get("asset_metadata")
    if isinstance(asset_records, Mapping):
        for raw_symbol, raw_metadata in asset_records.items():
            if isinstance(raw_metadata, Mapping):
                payload = {"symbol": raw_symbol, **dict(raw_metadata)}
                normalized = normalize_crypto_asset_metadata(payload)
                metadata[str(normalized["symbol"])] = normalized
    asset_list = status.get("crypto_assets")
    if isinstance(asset_list, Sequence) and not isinstance(asset_list, (str, bytes)):
        for item in asset_list:
            if isinstance(item, Mapping):
                normalized = normalize_crypto_asset_metadata(item)
                metadata[str(normalized["symbol"])] = normalized

    selected_symbol = _first_text(capability, "selected_symbol") or _first_text(
        status,
        "selected_symbol",
    )
    if selected_symbol:
        selected_payload = {
            "symbol": selected_symbol,
            "asset_class": "crypto",
            "tradable": _first_nonempty(
                _first_text(capability, "selected_symbol_tradable"),
                _first_text(status, "selected_symbol_tradable"),
            ),
            "status": "active",
            "marginable": _first_nonempty(
                _first_text(capability, "selected_symbol_marginable"),
                _first_text(status, "selected_symbol_marginable"),
            ),
            "fractionable": _first_nonempty(
                _first_text(capability, "selected_symbol_fractionable"),
                _first_text(status, "selected_symbol_fractionable"),
            ),
            "min_order_size": _first_nonempty(
                _first_text(capability, "min_order_size"),
                _first_text(status, "min_order_size"),
            ),
            "min_trade_increment": _first_nonempty(
                _first_text(capability, "min_trade_increment"),
                _first_text(status, "min_trade_increment"),
            ),
            "qty_increment": _first_nonempty(
                _first_text(capability, "min_order_increment"),
                _first_text(status, "min_order_increment"),
            ),
            "min_notional": _first_nonempty(
                _first_text(capability, "min_notional"),
                _first_text(status, "min_notional"),
            ),
        }
        normalized = normalize_crypto_asset_metadata(selected_payload)
        metadata[str(normalized["symbol"])] = normalized
    return metadata


def _crypto_symbols_from_status(
    status: Mapping[str, object],
    capability: Mapping[str, object],
    bars_by_symbol: Mapping[str, tuple[Bar, ...]],
) -> tuple[str, ...]:
    for value in (
        capability.get("eligible_crypto_symbols"),
        status.get("eligible_crypto_symbols"),
    ):
        symbols = _crypto_symbol_sequence(value)
        if symbols:
            return symbols
    if bars_by_symbol:
        return tuple(sorted(bars_by_symbol))
    selected = _first_text(capability, "selected_symbol") or _first_text(status, "selected_symbol")
    return (normalize_crypto_symbol(selected),) if selected else ("BTCUSD",)


def _read_spy_bars(path: Path) -> tuple[Bar, ...]:
    rows = _read_csv_rows(path)
    bars: list[Bar] = []
    for row in rows:
        symbol = _row_text(row, "symbol") or "SPY"
        if symbol_value(symbol) != "SPY":
            continue
        timestamp = _row_datetime(row)
        close = _positive_decimal(
            _first_nonempty(_row_text(row, "adjusted_close"), _row_text(row, "close")),
            "adjusted_close",
        )
        bars.append(
            Bar(
                symbol="SPY",
                timestamp=timestamp,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=_nonnegative_decimal(_row_text(row, "volume") or "0", "volume"),
            )
        )
    if not bars:
        raise ValidationError("SPY bars CSV did not include SPY rows.")
    return tuple(bars)


def _read_crypto_bars_by_symbol(path: Path) -> dict[str, tuple[Bar, ...]]:
    if not path.is_file():
        return {}
    rows = _read_csv_rows(path)
    by_symbol: dict[str, list[Bar]] = {}
    for row in rows:
        symbol_text = _row_text(row, "symbol") or _row_text(row, "S")
        if not symbol_text:
            continue
        symbol = normalize_crypto_symbol(symbol_text)
        asset_class = _row_text(row, "asset_class")
        if asset_class and asset_class.strip().lower() != "crypto":
            continue
        open_price = _positive_decimal(_first_row_text(row, "open", "o"), "open")
        high = _positive_decimal(_first_row_text(row, "high", "h"), "high")
        low = _positive_decimal(_first_row_text(row, "low", "l"), "low")
        close = _positive_decimal(_first_row_text(row, "close", "c"), "close")
        volume_text = _first_row_text(row, "volume", "v")
        volume = _nonnegative_decimal(volume_text or "0", "volume")
        by_symbol.setdefault(symbol, []).append(
            Bar(
                symbol=symbol,
                timestamp=_row_datetime(row),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return {symbol: tuple(values) for symbol, values in sorted(by_symbol.items())}


def _read_csv_rows(path: Path) -> tuple[Mapping[str, str], ...]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ValidationError(f"unable to read CSV: {path}") from exc
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValidationError("CSV header is required.")
    rows: list[Mapping[str, str]] = []
    for row in reader:
        if None in row:
            raise ValidationError("malformed CSV row.")
        rows.append(row)
    return tuple(rows)


def _row_datetime(row: Mapping[str, object]) -> datetime:
    text = _first_row_text(row, "timestamp", "datetime", "date", "t")
    if not text:
        raise ValidationError("timestamp/date is required.")
    try:
        if "T" in text:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            parsed = datetime.combine(datetime.fromisoformat(text).date(), time.min, UTC)
    except ValueError as exc:
        raise ValidationError("timestamp/date must be ISO formatted.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_spy_bars_path(value: Path | str | None) -> Path:
    if value is not None:
        return Path(value)
    if OPPORTUNITY_ROUTER_DEFAULT_SPY_BARS_CSV.is_file():
        return OPPORTUNITY_ROUTER_DEFAULT_SPY_BARS_CSV
    return OPPORTUNITY_ROUTER_FALLBACK_SPY_BARS_CSV


def _freshness_status(
    *,
    latest_timestamp: datetime | None,
    as_of: datetime,
    max_age: timedelta,
) -> str:
    if latest_timestamp is None:
        return "missing_data"
    if latest_timestamp > as_of:
        return "missing_data"
    age = as_of - latest_timestamp
    return "fresh" if age <= max_age else "stale_data"


def _signal_status_from_quality(quality: BarHistoryQuality) -> str:
    if quality.data_quality_status == "duplicate_timestamps":
        return "blocked"
    if quality.history_status in {"missing_history", "insufficient_history"}:
        return "insufficient_history"
    if quality.freshness_status != "fresh":
        return "stale_data"
    return "blocked" if quality.data_quality_status != "valid" else "no_trade"


def _usable_ordered_bars(bars: Iterable[Bar], as_of: datetime) -> tuple[Bar, ...]:
    as_of_value = _utc_datetime(as_of, "as_of")
    return tuple(
        sorted(
            (
                bar
                for bar in bars
                if _utc_datetime(bar.timestamp, "timestamp") <= as_of_value
            ),
            key=lambda bar: _utc_datetime(bar.timestamp, "timestamp"),
        )
    )


def _mean_abs_return(bars: Sequence[Bar]) -> Decimal:
    returns: list[Decimal] = []
    for previous, current in zip(bars, bars[1:]):
        returns.append(abs((current.close - previous.close) / previous.close))
    if not returns:
        return Decimal("0")
    return sum(returns, Decimal("0")) / Decimal(len(returns))


def _duplicate_timestamps(bars: Iterable[Bar]) -> tuple[datetime, ...]:
    seen: set[datetime] = set()
    duplicates: list[datetime] = []
    for bar in bars:
        timestamp = _utc_datetime(bar.timestamp, "timestamp")
        if timestamp in seen and timestamp not in duplicates:
            duplicates.append(timestamp)
        seen.add(timestamp)
    return tuple(sorted(duplicates))


def _history_gaps(bars: Sequence[Bar]) -> dict[str, int]:
    ordered = tuple(sorted(bars, key=lambda bar: _utc_datetime(bar.timestamp, "timestamp")))
    if len(ordered) < 2:
        return {"gap_count": 0, "max_gap_seconds": 0}
    deltas = [
        int(
            (
                _utc_datetime(current.timestamp, "timestamp")
                - _utc_datetime(previous.timestamp, "timestamp")
            ).total_seconds()
        )
        for previous, current in zip(ordered, ordered[1:])
    ]
    positive_deltas = [delta for delta in deltas if delta > 0]
    if not positive_deltas:
        return {"gap_count": 0, "max_gap_seconds": 0}
    expected = min(positive_deltas)
    gaps = [delta for delta in positive_deltas if delta > expected * 2]
    return {
        "gap_count": len(gaps),
        "max_gap_seconds": max(gaps) if gaps else max(positive_deltas),
    }


def _orderability_status(metadata: Mapping[str, object] | None) -> str:
    if metadata is None:
        return "metadata_missing"
    if metadata.get("tradable") is not True:
        return "not_orderable"
    status = _text(metadata.get("status")).lower()
    if status and status not in {"active", "tradable"}:
        return "not_orderable"
    has_notional = bool(_text(metadata.get("min_notional")))
    has_size_increment = any(
        _text(metadata.get(field))
        for field in ("min_order_size", "min_trade_increment", "qty_increment")
    )
    if not has_notional or not has_size_increment:
        return "metadata_missing"
    return "orderable"


def _asset_metadata_payload(value: Mapping[str, object] | object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return _allowed_asset_metadata_fields(value)
    model_dump = getattr(value, "model_dump", None)
    data: Mapping[str, object] = {}
    if callable(model_dump):
        try:
            dumped = model_dump(mode="json")
        except TypeError:
            dumped = model_dump()
        if isinstance(dumped, Mapping):
            data = dumped
    result = _allowed_asset_metadata_fields(data)
    for field_name in _ASSET_METADATA_FIELDS:
        if field_name in result:
            continue
        try:
            item = getattr(value, field_name)
        except Exception:
            continue
        if item is not None and not callable(item):
            result[field_name] = item
    return result


def _allowed_asset_metadata_fields(data: Mapping[str, object]) -> dict[str, object]:
    allowed: dict[str, object] = {}
    for key, value in data.items():
        field = _ASSET_METADATA_LOOKUP.get(_field_lookup_key(key))
        if field is not None and value is not None:
            allowed[field] = value
    return allowed


def _field_lookup_key(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _broker_state_mode(value: object) -> str:
    text = _text(value)
    if not text:
        return "broker_state_not_observed"
    if text in _BROKER_STATE_MODES:
        return text
    if "observed" in text and "paper" in text:
        return "alpaca_paper_observed"
    if "not_observed" in text:
        return "broker_state_not_observed"
    if "live" in text:
        return "blocked_live_endpoint_indicator"
    return "unknown"


def _combined_universe_manifest(
    *,
    candidates: Sequence[OpportunityCandidate],
    spy_path: Path,
    crypto_manifest: Mapping[str, object],
) -> dict[str, object]:
    symbols_by_asset: dict[str, set[str]] = {}
    for candidate in candidates:
        symbols_by_asset.setdefault(candidate.asset_class, set()).add(candidate.symbol)
    return {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "asset_universes": {
            "equity": {
                "source_mode": "local_spy_sma_daily_lane",
                "source_path": str(spy_path),
                "symbols": sorted(symbols_by_asset.get("equity", ())),
            },
            "crypto": dict(crypto_manifest),
            "options": {
                "source_mode": "future_placeholder_disabled",
                "symbols": [],
                "enabled": False,
                "blockers": ["options_not_authorized"],
            },
        },
    }


def _combined_data_quality_report(
    *,
    as_of: datetime,
    spy_quality: Mapping[str, object],
    crypto_report: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "as_of": as_of.isoformat(),
        "records": [dict(spy_quality), *list(_mapping_sequence(crypto_report.get("records")))],
    }


def _default_universe_manifest(
    candidates: Sequence[OpportunityCandidate],
) -> dict[str, object]:
    by_asset: dict[str, set[str]] = {}
    for candidate in candidates:
        by_asset.setdefault(candidate.asset_class, set()).add(candidate.symbol)
    return {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "asset_universes": {
            asset_class: {"symbols": sorted(symbols)}
            for asset_class, symbols in sorted(by_asset.items())
        },
    }


def _default_strategy_manifest(
    candidates: Sequence[OpportunityCandidate],
) -> dict[str, object]:
    strategies: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        strategies.setdefault(
            candidate.strategy_id,
            {
                "strategy_id": candidate.strategy_id,
                "strategy_family": candidate.strategy_family,
                "asset_classes": [],
                "evidence_tiers": [],
                "paper_submit_authorized": False,
                "profit_claim": "none",
            },
        )
        strategy = strategies[candidate.strategy_id]
        asset_classes = set(_string_sequence(strategy.get("asset_classes")))
        asset_classes.add(candidate.asset_class)
        strategy["asset_classes"] = sorted(asset_classes)
        tiers = set(_string_sequence(strategy.get("evidence_tiers")))
        tiers.add(candidate.evidence_tier)
        strategy["evidence_tiers"] = sorted(tiers)
    return {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "strategies": [strategies[key] for key in sorted(strategies)],
    }


def _default_data_quality_report(
    candidates: Sequence[OpportunityCandidate],
    as_of: datetime,
) -> dict[str, object]:
    return {
        "schema_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "as_of": as_of.isoformat(),
        "records": [
            {
                "symbol": candidate.symbol,
                "asset_class": candidate.asset_class,
                "strategy_id": candidate.strategy_id,
                "data_quality_status": candidate.data_quality_status,
                "history_status": candidate.history_status,
                "freshness_status": candidate.freshness_status,
                "blockers": list(candidate.blockers),
            }
            for candidate in candidates
        ],
    }


def _candidate_counts(
    candidates: Sequence[OpportunityCandidate],
    field_name: str,
) -> dict[str, int]:
    return dict(
        sorted(
            Counter(str(getattr(candidate, field_name)) for candidate in candidates).items()
        )
    )


def _next_operator_action(
    *,
    selected_candidate: OpportunityCandidate | None,
    top_blockers: tuple[tuple[str, int], ...],
) -> str:
    if selected_candidate is not None:
        return "operator_review_selected_preview_no_submit"
    blocker_names = {blocker for blocker, _count in top_blockers}
    if blocker_names & {"stale_data", "missing_data"}:
        return "refresh_local_market_data_then_rerun_router"
    if blocker_names & {"metadata_missing", "not_orderable"}:
        return "refresh_read_only_orderability_metadata_then_rerun_router"
    if blocker_names & {"broker_state_not_observed", "offline_preview_only", "unknown"}:
        return "run_explicit_read_only_visibility_cycle_then_rerun_router"
    if blocker_names & {"insufficient_history", "missing_history"}:
        return "collect_more_local_history_then_rerun_router"
    return "review_blockers_before_any_paper_action"


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_candidates_csv(
    path: Path,
    candidates: Sequence[Mapping[str, object]],
) -> None:
    fieldnames = (
        "candidate_id",
        "as_of",
        "asset_class",
        "symbol",
        "venue",
        "source",
        "strategy_id",
        "strategy_family",
        "signal_direction",
        "signal_status",
        "evidence_tier",
        "data_quality_status",
        "history_status",
        "freshness_status",
        "broker_state_mode",
        "orderability_status",
        "blocker_status",
        "blockers",
        "risk_notes",
        "score_components",
        "router_score",
        "labels",
        "profit_claim",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            row = dict(candidate)
            row["blockers"] = ";".join(_string_sequence(candidate.get("blockers")))
            row["risk_notes"] = ";".join(_string_sequence(candidate.get("risk_notes")))
            row["labels"] = ";".join(_string_sequence(candidate.get("labels")))
            row["score_components"] = json.dumps(
                _mapping(candidate.get("score_components")),
                sort_keys=True,
            )
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_candidate_consistency(candidate: OpportunityCandidate) -> None:
    if candidate.blocker_status == "eligible" and candidate.blockers:
        raise ValidationError("eligible candidates must not carry blockers.")
    if candidate.blocker_status == "blocked" and not candidate.blockers:
        raise ValidationError("blocked candidates must explain blockers.")
    if candidate.asset_class == "option":
        raise ValidationError("options candidates are not enabled.")
    if "profit_claim=none" not in candidate.labels:
        raise ValidationError("profit_claim=none label is required.")
    if candidate.profit_claim != "none":
        raise ValidationError("profit_claim must be none.")


def _candidate_tuple(values: Iterable[OpportunityCandidate]) -> tuple[OpportunityCandidate, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError("candidates must be an iterable.")
    try:
        candidates = tuple(values)
    except TypeError as exc:
        raise ValidationError("candidates must be an iterable.") from exc
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, OpportunityCandidate):
            raise ValidationError(f"candidates[{index}] must be an OpportunityCandidate.")
        if candidate.candidate_id in seen:
            raise ValidationError("candidate_id values must be unique.")
        seen.add(candidate.candidate_id)
    return candidates


def _score_component_mapping(value: Mapping[str, object]) -> dict[str, Decimal]:
    if not isinstance(value, Mapping):
        raise ValidationError("score_components must be a mapping.")
    result: dict[str, Decimal] = {}
    for key, item in value.items():
        result[_required_string(key, "score_components key")] = _decimal_value(
            item,
            "score_component",
        )
    return dict(sorted(result.items()))


def _crypto_symbol_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(dict.fromkeys(normalize_crypto_symbol(item) for item in value))


def _spy_labels() -> tuple[str, ...]:
    return (
        "paper_lab_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "offline_only",
    )


def _crypto_labels() -> tuple[str, ...]:
    return (
        "paper_lab_only",
        "research_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "offline_only",
        "crypto_preview_only",
    )


def _normalized_symbol(value: object, asset_class: object) -> str:
    if asset_class == "crypto":
        return normalize_crypto_symbol(value)
    return symbol_value(value)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _row_text(row: Mapping[str, object], field_name: str) -> str:
    wanted = field_name.strip().lower()
    for key, value in row.items():
        if str(key).strip().lower() == wanted:
            return "" if value is None else str(value).strip()
    return ""


def _first_row_text(row: Mapping[str, object], *field_names: str) -> str:
    for field_name in field_names:
        text = _row_text(row, field_name)
        if text:
            return text
    return ""


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    wanted = {field_name.strip().lower() for field_name in field_names}
    for key, value in row.items():
        if str(key).strip().lower() in wanted:
            return _text(value)
    return ""


def _first_nonempty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    enum_value = getattr(value, "value", None)
    if type(enum_value) is str:
        return enum_value.strip()
    return str(value).strip()


def _normalized_enum_text(value: object) -> str:
    text = _text(value).lower().replace(" ", "_")
    return text.rsplit(".", 1)[-1] if "." in text else text


def _bool_field(row: Mapping[str, object], field_name: str) -> bool | None:
    value = row.get(field_name)
    if type(value) is bool:
        return value
    text = _first_text(row, field_name).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _supported_universes(universe_manifest: Mapping[str, object]) -> tuple[str, ...]:
    universes = universe_manifest.get("asset_universes")
    if isinstance(universes, Mapping):
        return tuple(str(key) for key in sorted(universes))
    return ()


def _brief_blockers(values: Sequence[Mapping[str, object]]) -> str:
    if not values:
        return "none"
    return ", ".join(
        f"{item.get('blocker', '')}:{item.get('count', '')}" for item in values[:5]
    )


def _brief_broker_state(decision: Mapping[str, object]) -> str:
    modes = _string_sequence(decision.get("broker_state_modes"))
    return ",".join(modes) if modes else ""


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    parsed = _decimal_value(value, field_name)
    if parsed <= Decimal("0"):
        raise ValidationError(f"{field_name} must be positive.")
    return parsed


def _nonnegative_decimal(value: object, field_name: str) -> Decimal:
    parsed = _decimal_value(value, field_name)
    if parsed < Decimal("0"):
        raise ValidationError(f"{field_name} must be non-negative.")
    return parsed


def _decimal_value(value: object, field_name: str) -> Decimal:
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a finite Decimal.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be a finite Decimal.")
    return parsed


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _nonnegative_timedelta(value: object, field_name: str) -> timedelta:
    if not isinstance(value, timedelta) or value.total_seconds() < 0:
        raise ValidationError(f"{field_name} must be a non-negative timedelta.")
    return value


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be a UTC ISO timestamp.") from exc
    else:
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")
    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include timezone information.")
    try:
        return require_utc_datetime(parsed.astimezone(UTC))
    except ValidationError as exc:
        raise ValidationError(f"{field_name} must be a UTC datetime.") from exc


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _fixed_string(value: object, expected: str, field_name: str) -> str:
    text = _required_string(value, field_name)
    if text != expected:
        raise ValidationError(f"{field_name} must be exactly {expected}.")
    return text


def _choice(value: object, allowed: tuple[str, ...], field_name: str) -> str:
    if type(value) is not str or value not in allowed:
        raise ValidationError(f"{field_name} must be one of: {', '.join(allowed)}.")
    return value


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    return tuple(_required_string(value, f"{field_name}[]") for value in values)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _required_string(value, "value")
        if text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


_ASSET_CLASSES = ("equity", "crypto", "option")
_SIGNAL_DIRECTIONS = ("long", "exit", "flat", "none")
_SIGNAL_STATUSES = (
    "trade_candidate",
    "no_trade",
    "blocked",
    "insufficient_history",
    "stale_data",
)
_EVIDENCE_TIERS = (
    "backtest_supported",
    "signal_only",
    "research_only",
    "future_placeholder",
)
_EVIDENCE_RANK = {
    "backtest_supported": 0,
    "signal_only": 1,
    "research_only": 2,
    "future_placeholder": 3,
}
_DATA_QUALITY_STATUSES = (
    "valid",
    "missing_data",
    "stale_data",
    "duplicate_timestamps",
    "invalid_data",
    "metadata_only_no_history",
)
_HISTORY_STATUSES = (
    "sufficient_history",
    "insufficient_history",
    "missing_history",
    "invalid_history",
)
_FRESHNESS_STATUSES = ("fresh", "stale_data", "missing_data", "not_applicable")
_BROKER_STATE_MODES = (
    "alpaca_paper_observed",
    "paper_observed",
    "simulated_offline",
    "broker_state_not_observed",
    "offline_preview_only",
    "blocked_live_endpoint_indicator",
    "unknown",
)
_SELECTABLE_BROKER_STATE_MODES = (
    "alpaca_paper_observed",
    "paper_observed",
    "simulated_offline",
)
_ORDERABILITY_STATUSES = (
    "orderable",
    "metadata_missing",
    "not_orderable",
    "future_disabled",
    "unknown",
)
_BLOCKER_STATUSES = ("eligible", "blocked")
_ASSET_METADATA_FIELDS = (
    "symbol",
    "name",
    "asset_class",
    "class",
    "tradable",
    "status",
    "marginable",
    "fractionable",
    "min_notional",
    "min_order_notional",
    "min_order_size",
    "min_trade_increment",
    "min_order_increment",
    "price_increment",
    "qty_increment",
)
_ASSET_METADATA_LOOKUP = {
    _field_lookup_key(field): field for field in _ASSET_METADATA_FIELDS
}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
