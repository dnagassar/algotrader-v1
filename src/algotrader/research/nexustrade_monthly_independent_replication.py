"""Preregistered offline independent replication of one NexusTrade strategy.

This module is deliberately separate from the authentic-source V5.58 intake.
It consumes only deterministic local adjusted-daily bars, validates the
committed V5.64 protocol and V5.63 provenance hashes, and evaluates one
standalone portfolio plus one genuine SPY-regime-filtered composite. It imports
no network, credential, broker, execution, risk, or orchestration module.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
from statistics import stdev
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import LocalDailyBar, load_local_daily_bars_csv

__all__ = [
    "NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID",
    "NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID",
    "NEXUSTRADE_MONTHLY_STOCK_SYMBOLS",
    "NexusTradeMonthlyIndependentReplicationConfig",
    "ReplicationWindow",
    "build_nexustrade_monthly_independent_preregistration",
    "main",
    "run_nexustrade_monthly_independent_replication",
]


_SCHEMA_VERSION = "1"
_PROTOCOL_ID = "v5_64_nexustrade_monthly_independent_replication_v1"
_RECORD_TYPE = "nexustrade_monthly_independent_replication"
NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID = (
    "nexustrade_monthly_independent_daily_close_365_session"
)
NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID = (
    "nexustrade_monthly_independent_spy_sma_50_200_regime_filter"
)
_SPY_BASELINE_ID = "spy_sma_50_200_baseline"
_STATIC_EQUAL_WEIGHT_ID = "static_equal_weight_11_stock_buy_hold"
_PARENT_STRATEGY_ID = _SPY_BASELINE_ID
_PAIRING_ROLE = "risk_regime_filter"
NEXUSTRADE_MONTHLY_STOCK_SYMBOLS = (
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "GS",
    "JPM",
    "BRK-B",
    "COST",
)
_SPY = "SPY"
_ALL_SYMBOLS = (*NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, _SPY)
_DEFAULT_DATA_PATH = Path(
    "runs/operator_input/multi_etf_adjusted_daily_canonical.csv"
)
_DEFAULT_DATA_MANIFEST_PATH = Path(
    "runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json"
)
_DEFAULT_PREREGISTRATION_PATH = Path(
    "docs/design/v5_64_nexustrade_monthly_independent_replication.md"
)
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/v5_64_nexustrade_monthly_independent_replication"
)
_EXPECTED_PREREGISTRATION_SHA256 = (
    "f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0"
)
_EXPECTED_DATA_SHA256 = (
    "d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575"
)
_EXPECTED_DATA_MANIFEST_SHA256 = (
    "e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1"
)
_DEFAULT_INITIAL_EQUITY = Decimal("10000")
_DEFAULT_DATA_START = date(2019, 1, 2)
_DEFAULT_DATA_END = date(2025, 3, 28)
_DEFAULT_TRAIN_START = date(2021, 12, 31)
_DEFAULT_TRAIN_END = date(2024, 3, 24)
_DEFAULT_OOS_START = date(2024, 3, 24)
_DEFAULT_OOS_END = date(2025, 3, 28)
_DEFAULT_REQUIRED_COMMON_SESSION_COUNT = 1569
_DEFAULT_REQUIRED_OOS_SESSION_COUNT = 254
_DEFAULT_MINIMUM_INDICATOR_SESSIONS = 365
_SMA_WINDOW = 30
_MINIMUM_WINDOW = 365
_RSI_WINDOW = 14
_SPY_FAST_WINDOW = 50
_SPY_SLOW_WINDOW = 200
_NEAR_MINIMUM_RATIO = Decimal("1.05")
_STOCK_RSI_THRESHOLD = Decimal("28")
_SPY_RSI_THRESHOLD = Decimal("33")
_CALENDAR_REBALANCE_DAYS = 30
_TRADING_DAYS_PER_YEAR = Decimal("252")
_ONE = Decimal("1")
_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_WEIGHT_TOLERANCE = Decimal("0.000000000000000001")
_HASH_CHUNK_SIZE = 1024 * 1024
_MAX_MANIFEST_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ReplicationWindow:
    """One immutable reporting window."""

    window_id: str
    start: date | str
    end: date | str
    role: str = "walk_forward"

    def __post_init__(self) -> None:
        if not isinstance(self.window_id, str) or not self.window_id.strip():
            raise ValidationError("window_id is required.")
        if not isinstance(self.role, str) or not self.role.strip():
            raise ValidationError("role is required.")
        object.__setattr__(self, "window_id", self.window_id.strip())
        object.__setattr__(self, "role", self.role.strip())
        for field_name in ("start", "end"):
            value = getattr(self, field_name)
            if type(value) is date:
                parsed = value
            elif isinstance(value, str):
                try:
                    parsed = date.fromisoformat(value.strip())
                except ValueError as exc:
                    raise ValidationError(
                        f"{field_name} must be YYYY-MM-DD."
                    ) from exc
            else:
                raise ValidationError(f"{field_name} must be a plain date.")
            object.__setattr__(self, field_name, parsed)
        if self.start > self.end:
            raise ValidationError("replication window start must not exceed end.")

    def to_dict(self) -> dict[str, object]:
        return {
            "window_id": self.window_id,
            "role": self.role,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


_DEFAULT_WALK_FORWARD_WINDOWS = (
    ReplicationWindow(
        "oos_walk_forward_1",
        "2024-03-25",
        "2024-07-24",
    ),
    ReplicationWindow(
        "oos_walk_forward_2",
        "2024-07-25",
        "2024-11-21",
    ),
    ReplicationWindow(
        "oos_walk_forward_3",
        "2024-11-22",
        "2025-03-28",
    ),
)


@dataclass(frozen=True, slots=True)
class _CostAssumption:
    cost_id: str
    fee_bps: Decimal
    slippage_bps: Decimal
    description: str

    @property
    def rate(self) -> Decimal:
        return (self.fee_bps + self.slippage_bps) / Decimal("10000")

    def to_dict(self) -> dict[str, object]:
        return {
            "cost_id": self.cost_id,
            "fee_bps": _decimal_text(self.fee_bps),
            "slippage_bps": _decimal_text(self.slippage_bps),
            "total_cost_bps_per_one_way_turnover": _decimal_text(
                self.fee_bps + self.slippage_bps
            ),
            "description": self.description,
        }


_COST_ASSUMPTIONS = (
    _CostAssumption(
        "zero_cost",
        Decimal("0"),
        Decimal("0"),
        "Zero-cost reference only.",
    ),
    _CostAssumption(
        "source_fee_only",
        Decimal("1"),
        Decimal("0"),
        "Source-evidenced one basis point stock fee; local zero-slippage assumption.",
    ),
    _CostAssumption(
        "low_friction",
        Decimal("1"),
        Decimal("1"),
        "One basis point fee plus one basis point local slippage.",
    ),
    _CostAssumption(
        "moderate_friction",
        Decimal("1"),
        Decimal("4"),
        "One basis point fee plus four basis points local slippage.",
    ),
)


@dataclass(frozen=True, slots=True)
class NexusTradeMonthlyIndependentReplicationConfig:
    """Exact local inputs and fixed preregistered replay boundaries."""

    output_root: Path | str = _DEFAULT_OUTPUT_ROOT
    data_path: Path | str = _DEFAULT_DATA_PATH
    data_manifest_path: Path | str = _DEFAULT_DATA_MANIFEST_PATH
    preregistration_path: Path | str = _DEFAULT_PREREGISTRATION_PATH
    expected_preregistration_sha256: str = _EXPECTED_PREREGISTRATION_SHA256
    expected_data_sha256: str = _EXPECTED_DATA_SHA256
    expected_data_manifest_sha256: str = _EXPECTED_DATA_MANIFEST_SHA256
    initial_equity: Decimal | str = _DEFAULT_INITIAL_EQUITY
    data_start: date | str = _DEFAULT_DATA_START
    data_end: date | str = _DEFAULT_DATA_END
    train_start: date | str = _DEFAULT_TRAIN_START
    train_end: date | str = _DEFAULT_TRAIN_END
    oos_start: date | str = _DEFAULT_OOS_START
    oos_end: date | str = _DEFAULT_OOS_END
    walk_forward_windows: tuple[ReplicationWindow, ...] = (
        _DEFAULT_WALK_FORWARD_WINDOWS
    )
    required_common_session_count: int = _DEFAULT_REQUIRED_COMMON_SESSION_COUNT
    required_oos_session_count: int = _DEFAULT_REQUIRED_OOS_SESSION_COUNT
    minimum_indicator_sessions: int = _DEFAULT_MINIMUM_INDICATOR_SESSIONS

    def __post_init__(self) -> None:
        for field_name in (
            "output_root",
            "data_path",
            "data_manifest_path",
            "preregistration_path",
        ):
            object.__setattr__(
                self,
                field_name,
                _path(getattr(self, field_name), field_name),
            )
        for field_name in (
            "expected_preregistration_sha256",
            "expected_data_sha256",
            "expected_data_manifest_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _sha256_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "initial_equity",
            _positive_decimal(self.initial_equity, "initial_equity"),
        )
        if self.initial_equity != _DEFAULT_INITIAL_EQUITY:
            raise ValidationError(
                "initial_equity must remain the preregistered value 10000."
            )
        for field_name in (
            "data_start",
            "data_end",
            "train_start",
            "train_end",
            "oos_start",
            "oos_end",
        ):
            object.__setattr__(
                self,
                field_name,
                _plain_date(getattr(self, field_name), field_name),
            )
        if not (
            self.data_start
            < self.train_start
            <= self.train_end
            <= self.oos_start
            <= self.oos_end
            <= self.data_end
        ):
            raise ValidationError(
                "date contract must satisfy data_start < train_start <= "
                "train_end <= oos_start <= oos_end <= data_end."
            )
        windows = tuple(self.walk_forward_windows)
        if len(windows) != 3 or any(
            not isinstance(window, ReplicationWindow) for window in windows
        ):
            raise ValidationError("walk_forward_windows must contain three windows.")
        object.__setattr__(self, "walk_forward_windows", windows)
        for field_name in (
            "required_common_session_count",
            "required_oos_session_count",
            "minimum_indicator_sessions",
        ):
            object.__setattr__(
                self,
                field_name,
                _positive_int(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True, slots=True)
class _AlignedData:
    dates: tuple[date, ...]
    prices: Mapping[str, tuple[Decimal, ...]]
    data_sha256: str
    data_manifest_sha256: str
    data_manifest: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class _DayRecord:
    date: date
    strategy_return: Decimal
    turnover: Decimal
    buy_fill_count: int
    sell_fill_count: int
    exposure: Decimal
    contributions: Mapping[str, Decimal]
    desired_target: Mapping[str, Decimal]
    posttrade_weights: Mapping[str, Decimal]


@dataclass(frozen=True, slots=True)
class _Simulation:
    strategy_id: str
    cost: _CostAssumption
    records: tuple[_DayRecord, ...]


def build_nexustrade_monthly_independent_preregistration(
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    """Build the fixed protocol payload without reading prices or outcomes."""

    checked = _config(config)
    actual_hash = _file_sha256_required(
        checked.preregistration_path,
        "preregistration_path",
    )
    if actual_hash != checked.expected_preregistration_sha256:
        raise ValidationError("preregistration SHA-256 does not match the fixed protocol.")
    return {
        "record_type": "nexustrade_monthly_independent_preregistration",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "claim": "independent_replication_not_authentic_source_replay",
        "tracked_preregistration_path": str(checked.preregistration_path),
        "tracked_preregistration_sha256": actual_hash,
        "standalone_candidate_id": NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID,
        "composite_candidate_id": NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
        "parent_strategy_id": _PARENT_STRATEGY_ID,
        "pairing_role": _PAIRING_ROLE,
        "baseline_id": _SPY_BASELINE_ID,
        "cross_asset_comparator_id": _STATIC_EQUAL_WEIGHT_ID,
        "stock_symbols": list(NEXUSTRADE_MONTHLY_STOCK_SYMBOLS),
        "regime_symbol": _SPY,
        "data_contract": {
            "data_path": str(checked.data_path),
            "data_manifest_path": str(checked.data_manifest_path),
            "expected_data_sha256": checked.expected_data_sha256,
            "expected_data_manifest_sha256": (
                checked.expected_data_manifest_sha256
            ),
            "price_field": "adjusted_close",
            "provider_source_field": "adjClose",
            "data_start": checked.data_start.isoformat(),
            "data_end": checked.data_end.isoformat(),
            "session_reference": "observed_tiingo_spy_eod_dates",
            "independent_exchange_calendar_claimed": False,
            "brk_b_mapping": "BRK-B->BRK-B",
        },
        "chronology": {
            "train_start": checked.train_start.isoformat(),
            "train_end": checked.train_end.isoformat(),
            "oos_start": checked.oos_start.isoformat(),
            "oos_end": checked.oos_end.isoformat(),
            "walk_forward_windows": [
                window.to_dict() for window in checked.walk_forward_windows
            ],
            "state_reset_at_window_boundary": False,
        },
        "indicator_assumptions": {
            "sma_window_sessions": _SMA_WINDOW,
            "minimum_window_observed_sessions": _MINIMUM_WINDOW,
            "rsi_period_close_changes": _RSI_WINDOW,
            "rsi_method": "simple_arithmetic_mean_gain_loss",
            "stock_rsi_below": _decimal_text(_STOCK_RSI_THRESHOLD),
            "spy_rsi_above": _decimal_text(_SPY_RSI_THRESHOLD),
            "near_minimum_ratio_at_most": _decimal_text(_NEAR_MINIMUM_RATIO),
            "warmup_semantics_source_authentic": False,
        },
        "fill_assumptions": {
            "signal_price": "current_session_adjusted_close",
            "fill_price": "next_observed_session_adjusted_close",
            "same_close_fill_allowed": False,
            "rebalance_state_rule": (
                "30 calendar days since last filled buy OR 30 calendar days "
                "since last filled sell"
            ),
            "missing_filled_event_satisfies_elapsed_condition": True,
            "cash_return": "0",
            "weights_drift_between_fills": True,
        },
        "cost_assumptions": [item.to_dict() for item in _COST_ASSUMPTIONS],
        "gate_policy": {
            "exact_oos_requires_full_oos_and_all_three_folds": True,
            "moderate_cost_id": "moderate_friction",
            "cross_asset_portfolio_gate_required": True,
            "composite_target_weight_difference_required": True,
            "preview_review_requires_all_applicable_gates": True,
            "paper_promotion_allowed": False,
        },
        "source_metrics_trust": "untrusted_external_evidence",
        "source_metrics_used_for_ranking": False,
        "source_metrics_used_for_promotion": False,
        "paper_promotion_allowed": False,
        "holdout_discrepancy_preserved": {
            "table_total_return_percent": "29.64",
            "chart_gain_percent": "29.41",
        },
        "safety": _safety_payload(),
    }


def run_nexustrade_monthly_independent_replication(
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    """Validate inputs, replay the frozen protocol, and write hashed artifacts."""

    checked = _config(config)
    checked.output_root.mkdir(parents=True, exist_ok=True)
    preregistration = build_nexustrade_monthly_independent_preregistration(checked)
    preregistration_path = checked.output_root / "preregistration.json"
    _write_json_atomic(preregistration_path, preregistration)

    data = _load_aligned_data(checked)
    _validate_chronology(data, checked)
    result = _build_replication_result(checked, data, preregistration)
    result_path = checked.output_root / "replication_results.json"
    _write_json_atomic(result_path, result)

    summary_path = checked.output_root / "replication_summary.md"
    _write_text_atomic(summary_path, _render_summary(result))
    manifest = _artifact_manifest(
        checked,
        data=data,
        preregistration_path=preregistration_path,
        result_path=result_path,
        summary_path=summary_path,
    )
    manifest_path = checked.output_root / "manifest.json"
    _write_json_atomic(manifest_path, manifest)

    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_path"] = str(manifest_path)
    completed["artifact_manifest_sha256"] = _file_sha256_required(
        manifest_path,
        "artifact_manifest",
    )
    return completed


def _build_replication_result(
    config: NexusTradeMonthlyIndependentReplicationConfig,
    data: _AlignedData,
    preregistration: Mapping[str, object],
) -> dict[str, object]:
    indicators = _build_indicators(data)
    simulations: dict[str, dict[str, _Simulation]] = {
        NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID: {},
        NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID: {},
        _SPY_BASELINE_ID: {},
        _STATIC_EQUAL_WEIGHT_ID: {},
    }
    for cost in _COST_ASSUMPTIONS:
        simulations[NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID][cost.cost_id] = (
            _simulate_dynamic_candidate(
                data,
                indicators,
                config,
                cost,
                composite=False,
            )
        )
        simulations[NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID][cost.cost_id] = (
            _simulate_dynamic_candidate(
                data,
                indicators,
                config,
                cost,
                composite=True,
            )
        )
        simulations[_SPY_BASELINE_ID][cost.cost_id] = _simulate_spy_baseline(
            data,
            indicators,
            config,
            cost,
        )
        simulations[_STATIC_EQUAL_WEIGHT_ID][cost.cost_id] = (
            _simulate_static_equal_weight(data, config, cost)
        )

    windows = _reporting_windows(config)
    metric_book = {
        strategy_id: {
            cost_id: {
                window.window_id: _metrics_for_window(
                    simulation,
                    window,
                    NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
                )
                for window in windows
            }
            for cost_id, simulation in cost_simulations.items()
        }
        for strategy_id, cost_simulations in simulations.items()
    }

    standalone_source = simulations[
        NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID
    ]["source_fee_only"]
    composite_source = simulations[
        NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
    ]["source_fee_only"]
    integrity = _composite_integrity(
        standalone_source,
        composite_source,
        config,
    )

    candidate_results = []
    for candidate_id in (
        NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID,
        NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
    ):
        gates = _candidate_gates(
            candidate_id,
            metric_book,
            simulations,
            config,
            composite_integrity=integrity,
        )
        candidate_results.append(
            {
                "candidate_id": candidate_id,
                "claim": "independent_replication_not_authentic_source_replay",
                "role": (
                    "standalone"
                    if candidate_id
                    == NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID
                    else _PAIRING_ROLE
                ),
                "parent_strategy_ids": (
                    []
                    if candidate_id
                    == NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID
                    else [_PARENT_STRATEGY_ID]
                ),
                "cost_results": _cost_result_records(
                    candidate_id,
                    metric_book,
                    simulations,
                    windows,
                    config,
                ),
                "gates": gates,
                "route": gates["route"],
                "paper_promotion_allowed": False,
                "source_metrics_used_for_ranking": False,
                "source_metrics_used_for_promotion": False,
            }
        )

    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "claim": "independent_replication_not_authentic_source_replay",
        "preregistration": {
            "path": str(config.preregistration_path),
            "sha256": preregistration["tracked_preregistration_sha256"],
            "committed_before_outcome_inspection": True,
        },
        "data_contract": {
            "path": str(config.data_path),
            "sha256": data.data_sha256,
            "manifest_path": str(config.data_manifest_path),
            "manifest_sha256": data.data_manifest_sha256,
            "common_session_count": len(data.dates),
            "first_session": data.dates[0].isoformat(),
            "last_session": data.dates[-1].isoformat(),
            "symbols": list(_ALL_SYMBOLS),
            "price_field": "adjusted_close",
            "brk_b_mapping": "BRK-B->BRK-B",
        },
        "chronology": {
            "train_start": config.train_start.isoformat(),
            "train_end": config.train_end.isoformat(),
            "oos_start": config.oos_start.isoformat(),
            "oos_end": config.oos_end.isoformat(),
            "walk_forward_windows": [
                window.to_dict() for window in config.walk_forward_windows
            ],
            "state_reset_at_window_boundary": False,
        },
        "cost_assumptions": [item.to_dict() for item in _COST_ASSUMPTIONS],
        "comparators": [
            _comparator_record(
                comparator_id,
                metric_book,
                simulations,
                windows,
                config,
            )
            for comparator_id in (_SPY_BASELINE_ID, _STATIC_EQUAL_WEIGHT_ID)
        ],
        "candidates": candidate_results,
        "composite_integrity": integrity,
        "source_metrics_trust": "untrusted_external_evidence",
        "source_metrics_used_for_ranking": False,
        "source_metrics_used_for_promotion": False,
        "holdout_discrepancy_preserved": {
            "table_total_return_percent": "29.64",
            "chart_gain_percent": "29.41",
        },
        "paper_promotion_allowed": False,
        "preview_review_supports_only_later_no_submit_design": True,
        "safety": _safety_payload(),
        "limitations": [
            "Independent local assumptions do not establish authentic NexusTrade "
            "data mode, slippage, warm-up, fill behavior, or lineage.",
            "Observed Tiingo SPY dates are the session reference, not an independent "
            "official exchange calendar.",
            "Adjusted close is used; adjusted OHLCV is not claimed.",
            "Cash return is zero and no tax, liquidity, lot-size, borrow, or intraday "
            "execution model is included.",
        ],
    }


def _load_aligned_data(
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> _AlignedData:
    manifest_hash = _file_sha256_required(
        config.data_manifest_path,
        "data_manifest_path",
    )
    if manifest_hash != config.expected_data_manifest_sha256:
        raise ValidationError("data manifest SHA-256 does not match preregistration.")
    manifest = _load_json_object(config.data_manifest_path, "data_manifest_path")
    if manifest.get("canonical_data_ready") is not True:
        raise ValidationError("canonical data manifest is not ready.")
    if tuple(manifest.get("symbols", [])) != _ALL_SYMBOLS:
        raise ValidationError("canonical data manifest symbols do not match protocol.")
    provider_map = manifest.get("provider_symbol_map")
    if not isinstance(provider_map, Mapping) or provider_map.get("BRK-B") != "BRK-B":
        raise ValidationError("canonical data manifest BRK-B mapping is invalid.")

    data_hash = _file_sha256_required(config.data_path, "data_path")
    if data_hash != config.expected_data_sha256:
        raise ValidationError("canonical data SHA-256 does not match preregistration.")
    if manifest.get("combined_output_sha256") != data_hash:
        raise ValidationError("canonical data hash disagrees with provenance manifest.")

    loaded = {
        symbol: load_local_daily_bars_csv(
            config.data_path,
            symbol=symbol,
            as_of=config.data_end,
        ).usable_bars
        for symbol in _ALL_SYMBOLS
    }
    reference_dates = tuple(bar.date for bar in loaded[_SPY])
    if not reference_dates:
        raise ValidationError("SPY adjusted-daily session reference is empty.")
    if len(reference_dates) != config.required_common_session_count:
        raise ValidationError("common session count does not match preregistration.")
    if (
        reference_dates[0] != config.data_start
        or reference_dates[-1] != config.data_end
    ):
        raise ValidationError("canonical data range does not match preregistration.")

    prices: dict[str, tuple[Decimal, ...]] = {}
    for symbol in _ALL_SYMBOLS:
        bars = loaded[symbol]
        dates = tuple(bar.date for bar in bars)
        if dates != reference_dates:
            raise ValidationError(f"{symbol} sessions do not match SPY reference.")
        prices[symbol] = tuple(bar.adjusted_close for bar in bars)
    if manifest.get("session_reference_count") != len(reference_dates):
        raise ValidationError("provenance session count disagrees with local bars.")
    return _AlignedData(
        dates=reference_dates,
        prices=prices,
        data_sha256=data_hash,
        data_manifest_sha256=manifest_hash,
        data_manifest=manifest,
    )


def _validate_chronology(
    data: _AlignedData,
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> None:
    dates = data.dates
    train_dates = tuple(
        item for item in dates if config.train_start <= item <= config.train_end
    )
    oos_dates = tuple(
        item for item in dates if config.oos_start <= item <= config.oos_end
    )
    if not train_dates or train_dates[0] != config.train_start:
        raise ValidationError("first observed training session is not train_start.")
    if len(oos_dates) != config.required_oos_session_count:
        raise ValidationError("OOS session count does not match preregistration.")
    fold_dates: list[date] = []
    for window in config.walk_forward_windows:
        items = tuple(item for item in oos_dates if window.start <= item <= window.end)
        if not items or items[0] != window.start or items[-1] != window.end:
            raise ValidationError(
                f"{window.window_id} observed boundaries do not match preregistration."
            )
        fold_dates.extend(items)
    if tuple(fold_dates) != oos_dates:
        raise ValidationError("walk-forward folds must exactly partition OOS sessions.")
    train_index = dates.index(train_dates[0])
    if train_index < config.minimum_indicator_sessions:
        raise ValidationError("insufficient pretraining indicator sessions.")


def _build_indicators(
    data: _AlignedData,
) -> dict[str, dict[str, tuple[Decimal | None, ...]]]:
    indicators: dict[str, dict[str, tuple[Decimal | None, ...]]] = {}
    for symbol, values in data.prices.items():
        symbol_indicators = {
            "rsi14": tuple(_simple_rsi(values, index, _RSI_WINDOW) for index in range(len(values))),
        }
        if symbol in NEXUSTRADE_MONTHLY_STOCK_SYMBOLS:
            symbol_indicators["sma30"] = tuple(
                _simple_average(values, index, _SMA_WINDOW)
                for index in range(len(values))
            )
            symbol_indicators["minimum365"] = tuple(
                _rolling_minimum(values, index, _MINIMUM_WINDOW)
                for index in range(len(values))
            )
        if symbol == _SPY:
            symbol_indicators["sma50"] = tuple(
                _simple_average(values, index, _SPY_FAST_WINDOW)
                for index in range(len(values))
            )
            symbol_indicators["sma200"] = tuple(
                _simple_average(values, index, _SPY_SLOW_WINDOW)
                for index in range(len(values))
            )
        indicators[symbol] = symbol_indicators
    return indicators


def _simulate_dynamic_candidate(
    data: _AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    config: NexusTradeMonthlyIndependentReplicationConfig,
    cost: _CostAssumption,
    *,
    composite: bool,
) -> _Simulation:
    strategy_id = (
        NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
        if composite
        else NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID
    )
    start_index = next(
        index for index, item in enumerate(data.dates) if item >= config.train_start
    )
    end_index = max(
        index for index, item in enumerate(data.dates) if item <= config.oos_end
    )
    if start_index == 0:
        raise ValidationError("training requires a prior signal session.")
    current_weights = _zero_stock_weights()
    last_filled_buy: date | None = None
    last_filled_sell: date | None = None
    source_desired = _eligible_target(data, indicators, start_index - 1)
    regime_on = _spy_regime_on(indicators, start_index - 1)
    actual_desired = (
        source_desired if (not composite or regime_on) else _zero_stock_weights()
    )
    pending_target: dict[str, Decimal] | None = dict(actual_desired)
    previous_regime_on = regime_on
    records: list[_DayRecord] = []

    for index in range(start_index, end_index + 1):
        (
            strategy_return,
            turnover,
            buy_count,
            sell_count,
            exposure,
            contributions,
            current_weights,
        ) = _portfolio_step(
            data,
            index,
            current_weights,
            pending_target,
            cost,
            NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        if buy_count:
            last_filled_buy = data.dates[index]
        if sell_count:
            last_filled_sell = data.dates[index]

        rebalance_ready = _rebalance_ready(
            data.dates[index],
            last_filled_buy,
            last_filled_sell,
        )
        if rebalance_ready:
            source_desired = _eligible_target(data, indicators, index)
        current_regime_on = _spy_regime_on(indicators, index)
        actual_desired = (
            source_desired
            if (not composite or current_regime_on)
            else _zero_stock_weights()
        )
        overlay_changed = composite and current_regime_on != previous_regime_on
        pending_target = (
            dict(actual_desired)
            if rebalance_ready or overlay_changed
            else None
        )
        previous_regime_on = current_regime_on
        records.append(
            _DayRecord(
                date=data.dates[index],
                strategy_return=strategy_return,
                turnover=turnover,
                buy_fill_count=buy_count,
                sell_fill_count=sell_count,
                exposure=exposure,
                contributions=contributions,
                desired_target=dict(actual_desired),
                posttrade_weights=dict(current_weights),
            )
        )
    return _Simulation(strategy_id=strategy_id, cost=cost, records=tuple(records))


def _simulate_spy_baseline(
    data: _AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    config: NexusTradeMonthlyIndependentReplicationConfig,
    cost: _CostAssumption,
) -> _Simulation:
    start_index = next(
        index for index, item in enumerate(data.dates) if item >= config.train_start
    )
    end_index = max(
        index for index, item in enumerate(data.dates) if item <= config.oos_end
    )
    current_weights = {_SPY: _ZERO}
    desired = {_SPY: _ONE if _spy_regime_on(indicators, start_index - 1) else _ZERO}
    pending: dict[str, Decimal] | None = dict(desired)
    records: list[_DayRecord] = []
    for index in range(start_index, end_index + 1):
        (
            strategy_return,
            turnover,
            buy_count,
            sell_count,
            exposure,
            contributions,
            current_weights,
        ) = _portfolio_step(
            data,
            index,
            current_weights,
            pending,
            cost,
            (_SPY,),
        )
        next_desired = {
            _SPY: _ONE if _spy_regime_on(indicators, index) else _ZERO
        }
        pending = (
            dict(next_desired)
            if _weights_differ(desired, next_desired, (_SPY,))
            else None
        )
        desired = next_desired
        records.append(
            _DayRecord(
                date=data.dates[index],
                strategy_return=strategy_return,
                turnover=turnover,
                buy_fill_count=buy_count,
                sell_fill_count=sell_count,
                exposure=exposure,
                contributions=contributions,
                desired_target=dict(desired),
                posttrade_weights=dict(current_weights),
            )
        )
    return _Simulation(strategy_id=_SPY_BASELINE_ID, cost=cost, records=tuple(records))


def _simulate_static_equal_weight(
    data: _AlignedData,
    config: NexusTradeMonthlyIndependentReplicationConfig,
    cost: _CostAssumption,
) -> _Simulation:
    start_index = next(
        index for index, item in enumerate(data.dates) if item >= config.train_start
    )
    end_index = max(
        index for index, item in enumerate(data.dates) if item <= config.oos_end
    )
    target_weight = _ONE / Decimal(len(NEXUSTRADE_MONTHLY_STOCK_SYMBOLS))
    desired = {
        symbol: target_weight for symbol in NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
    }
    current_weights = _zero_stock_weights()
    pending: dict[str, Decimal] | None = dict(desired)
    records: list[_DayRecord] = []
    for index in range(start_index, end_index + 1):
        (
            strategy_return,
            turnover,
            buy_count,
            sell_count,
            exposure,
            contributions,
            current_weights,
        ) = _portfolio_step(
            data,
            index,
            current_weights,
            pending,
            cost,
            NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        pending = None
        records.append(
            _DayRecord(
                date=data.dates[index],
                strategy_return=strategy_return,
                turnover=turnover,
                buy_fill_count=buy_count,
                sell_fill_count=sell_count,
                exposure=exposure,
                contributions=contributions,
                desired_target=dict(desired),
                posttrade_weights=dict(current_weights),
            )
        )
    return _Simulation(
        strategy_id=_STATIC_EQUAL_WEIGHT_ID,
        cost=cost,
        records=tuple(records),
    )


def _portfolio_step(
    data: _AlignedData,
    index: int,
    current_weights: Mapping[str, Decimal],
    pending_target: Mapping[str, Decimal] | None,
    cost: _CostAssumption,
    symbols: tuple[str, ...],
) -> tuple[
    Decimal,
    Decimal,
    int,
    int,
    Decimal,
    dict[str, Decimal],
    dict[str, Decimal],
]:
    exposure = sum((current_weights[symbol] for symbol in symbols), _ZERO)
    contributions = {symbol: _ZERO for symbol in symbols}
    gross_return = _ZERO
    if index > 0:
        for symbol in symbols:
            asset_return = (
                data.prices[symbol][index] / data.prices[symbol][index - 1]
            ) - _ONE
            contribution = current_weights[symbol] * asset_return
            contributions[symbol] = contribution
            gross_return += contribution
    growth = _ONE + gross_return
    if growth <= _ZERO:
        raise ValidationError("portfolio gross return produced nonpositive equity.")
    drifted = {
        symbol: current_weights[symbol]
        * (
            data.prices[symbol][index] / data.prices[symbol][index - 1]
            if index > 0
            else _ONE
        )
        / growth
        for symbol in symbols
    }
    turnover = _ZERO
    buy_count = 0
    sell_count = 0
    posttrade = drifted
    if pending_target is not None:
        _validate_target_weights(pending_target, symbols)
        deltas = {
            symbol: pending_target[symbol] - drifted[symbol]
            for symbol in symbols
        }
        turnover = sum((abs(delta) for delta in deltas.values()), _ZERO)
        buy_count = sum(1 for delta in deltas.values() if delta > _WEIGHT_TOLERANCE)
        sell_count = sum(1 for delta in deltas.values() if delta < -_WEIGHT_TOLERANCE)
        if turnover > _WEIGHT_TOLERANCE:
            posttrade = {symbol: pending_target[symbol] for symbol in symbols}
        else:
            turnover = _ZERO
            buy_count = 0
            sell_count = 0
    cost_fraction = turnover * cost.rate
    if cost_fraction >= _ONE:
        raise ValidationError("transaction-cost fraction must remain below one.")
    strategy_return = growth * (_ONE - cost_fraction) - _ONE
    return (
        strategy_return,
        turnover,
        buy_count,
        sell_count,
        exposure,
        contributions,
        posttrade,
    )


def _eligible_target(
    data: _AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    index: int,
) -> dict[str, Decimal]:
    eligible = []
    spy_rsi = indicators[_SPY]["rsi14"][index]
    if spy_rsi is None:
        return _zero_stock_weights()
    for symbol in NEXUSTRADE_MONTHLY_STOCK_SYMBOLS:
        price = data.prices[symbol][index]
        sma = indicators[symbol]["sma30"][index]
        minimum = indicators[symbol]["minimum365"][index]
        stock_rsi = indicators[symbol]["rsi14"][index]
        if sma is None or minimum is None or stock_rsi is None:
            continue
        true_count = sum(
            (
                price > sma,
                (price / minimum) <= _NEAR_MINIMUM_RATIO,
                stock_rsi < _STOCK_RSI_THRESHOLD and spy_rsi > _SPY_RSI_THRESHOLD,
            )
        )
        if 1 <= true_count <= 2:
            eligible.append(symbol)
    if not eligible:
        return _zero_stock_weights()
    weight = _ONE / Decimal(len(eligible))
    return {
        symbol: weight if symbol in eligible else _ZERO
        for symbol in NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
    }


def _spy_regime_on(
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    index: int,
) -> bool:
    fast = indicators[_SPY]["sma50"][index]
    slow = indicators[_SPY]["sma200"][index]
    return fast is not None and slow is not None and fast > slow


def _rebalance_ready(
    on_date: date,
    last_filled_buy: date | None,
    last_filled_sell: date | None,
) -> bool:
    buy_ready = (
        last_filled_buy is None
        or (on_date - last_filled_buy).days >= _CALENDAR_REBALANCE_DAYS
    )
    sell_ready = (
        last_filled_sell is None
        or (on_date - last_filled_sell).days >= _CALENDAR_REBALANCE_DAYS
    )
    return buy_ready or sell_ready


def _reporting_windows(
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> tuple[ReplicationWindow, ...]:
    return (
        ReplicationWindow(
            "training",
            config.train_start,
            config.train_end,
            role="training",
        ),
        ReplicationWindow(
            "oos",
            config.oos_start,
            config.oos_end,
            role="out_of_sample",
        ),
        *config.walk_forward_windows,
    )


def _metrics_for_window(
    simulation: _Simulation,
    window: ReplicationWindow,
    contribution_symbols: tuple[str, ...],
) -> dict[str, object]:
    records = tuple(
        record
        for record in simulation.records
        if window.start <= record.date <= window.end
    )
    if not records:
        raise ValidationError(f"{window.window_id} has no simulation records.")
    equity = Decimal("10000")
    peak = equity
    worst_drawdown = _ZERO
    returns = []
    contributions = {symbol: _ZERO for symbol in contribution_symbols}
    turnover = _ZERO
    buy_count = 0
    sell_count = 0
    invested_count = 0
    exposure_sum = _ZERO
    for record in records:
        returns.append(record.strategy_return)
        equity *= _ONE + record.strategy_return
        if equity <= _ZERO:
            raise ValidationError("window equity became nonpositive.")
        if equity > peak:
            peak = equity
        drawdown = (equity / peak) - _ONE
        if drawdown < worst_drawdown:
            worst_drawdown = drawdown
        turnover += record.turnover
        buy_count += record.buy_fill_count
        sell_count += record.sell_fill_count
        exposure_sum += record.exposure
        if record.exposure > _WEIGHT_TOLERANCE:
            invested_count += 1
        for symbol in contribution_symbols:
            contributions[symbol] += record.contributions.get(symbol, _ZERO)
    total_return = (equity / Decimal("10000")) - _ONE
    annualized_return = _annualized_return(
        total_return,
        records[0].date,
        records[-1].date,
    )
    volatility = _annualized_volatility(tuple(returns))
    sharpe = _sharpe_like(annualized_return, volatility)
    absolute_contribution = sum(
        (abs(value) for value in contributions.values()),
        _ZERO,
    )
    contribution_shares = {
        symbol: (
            None
            if absolute_contribution == _ZERO
            else abs(value) / absolute_contribution
        )
        for symbol, value in contributions.items()
    }
    held_symbols = sorted(
        {
            symbol
            for record in records
            for symbol in contribution_symbols
            if record.desired_target.get(symbol, _ZERO) > _WEIGHT_TOLERANCE
        }
    )
    positive_contribution_symbols = sorted(
        symbol for symbol, value in contributions.items() if value > _ZERO
    )
    max_share = max(
        (
            share
            for share in contribution_shares.values()
            if share is not None
        ),
        default=None,
    )
    return {
        **window.to_dict(),
        "first_observed_session": records[0].date.isoformat(),
        "last_observed_session": records[-1].date.isoformat(),
        "session_return_count": len(records),
        "starting_equity": "10000",
        "ending_equity": _decimal_text(equity),
        "total_return": _decimal_text(total_return),
        "annualized_return": _optional_decimal_text(annualized_return),
        "max_drawdown": _decimal_text(-worst_drawdown),
        "annualized_volatility": _optional_decimal_text(volatility),
        "sharpe_ratio": _optional_decimal_text(sharpe),
        "one_way_turnover": _decimal_text(turnover),
        "buy_fill_count": buy_count,
        "sell_fill_count": sell_count,
        "trade_count": buy_count + sell_count,
        "invested_session_percentage": _decimal_text(
            Decimal(invested_count) / Decimal(len(records)) * _HUNDRED
        ),
        "average_gross_exposure": _decimal_text(
            exposure_sum / Decimal(len(records))
        ),
        "constituent_contributions": {
            symbol: _decimal_text(value)
            for symbol, value in contributions.items()
        },
        "absolute_contribution_shares": {
            symbol: _optional_decimal_text(value)
            for symbol, value in contribution_shares.items()
        },
        "symbols_with_nonzero_target": held_symbols,
        "positive_contribution_symbols": positive_contribution_symbols,
        "max_absolute_contribution_share": _optional_decimal_text(max_share),
    }


def _candidate_gates(
    candidate_id: str,
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    simulations: Mapping[str, Mapping[str, _Simulation]],
    config: NexusTradeMonthlyIndependentReplicationConfig,
    *,
    composite_integrity: Mapping[str, object],
) -> dict[str, object]:
    oos_window_ids = (
        "oos",
        *(window.window_id for window in config.walk_forward_windows),
    )
    baseline_window_results = []
    for window_id in oos_window_ids:
        candidate_metric = metric_book[candidate_id]["source_fee_only"][window_id]
        baseline_metric = metric_book[_SPY_BASELINE_ID]["source_fee_only"][window_id]
        comparison = _metric_comparison(candidate_metric, baseline_metric)
        passed = _baseline_window_passed(comparison)
        baseline_window_results.append(
            {
                "window_id": window_id,
                "passed": passed,
                **comparison,
            }
        )
    exact_oos_passed = all(item["passed"] for item in baseline_window_results)

    source_candidate = metric_book[candidate_id]["source_fee_only"]["oos"]
    source_baseline = metric_book[_SPY_BASELINE_ID]["source_fee_only"]["oos"]
    moderate_candidate = metric_book[candidate_id]["moderate_friction"]["oos"]
    moderate_baseline = metric_book[_SPY_BASELINE_ID]["moderate_friction"]["oos"]
    source_edge = _decimal(source_candidate["total_return"]) - _decimal(
        source_baseline["total_return"]
    )
    moderate_edge = _decimal(moderate_candidate["total_return"]) - _decimal(
        moderate_baseline["total_return"]
    )
    edge_broken = source_edge > _ZERO and moderate_edge <= _ZERO
    degradation = _decimal(source_candidate["total_return"]) - _decimal(
        moderate_candidate["total_return"]
    )
    cost_passed = (
        _decimal(moderate_candidate["total_return"]) > _ZERO
        and moderate_edge > _ZERO
        and not edge_broken
        and degradation < Decimal("0.02")
    )
    cost_gate = {
        "passed": cost_passed,
        "source_fee_oos_total_return": source_candidate["total_return"],
        "moderate_oos_total_return": moderate_candidate["total_return"],
        "source_fee_spy_edge": _decimal_text(source_edge),
        "moderate_spy_edge": _decimal_text(moderate_edge),
        "edge_broken_by_moderate_cost": edge_broken,
        "return_degradation": _decimal_text(degradation),
    }

    moderate_metric = metric_book[candidate_id]["moderate_friction"]["oos"]
    cross_window_results = []
    for window_id in oos_window_ids:
        candidate_return = _decimal(
            metric_book[candidate_id]["moderate_friction"][window_id][
                "total_return"
            ]
        )
        comparator_return = _decimal(
            metric_book[_STATIC_EQUAL_WEIGHT_ID]["moderate_friction"][window_id][
                "total_return"
            ]
        )
        cross_window_results.append(
            {
                "window_id": window_id,
                "candidate_total_return": _decimal_text(candidate_return),
                "comparator_total_return": _decimal_text(comparator_return),
                "return_delta": _decimal_text(candidate_return - comparator_return),
                "passed": candidate_return > comparator_return,
            }
        )
    held_symbols = list(moderate_metric["symbols_with_nonzero_target"])
    positive_symbols = list(moderate_metric["positive_contribution_symbols"])
    max_share_text = moderate_metric["max_absolute_contribution_share"]
    max_share = None if max_share_text is None else _decimal(max_share_text)
    cross_asset_passed = (
        all(item["passed"] for item in cross_window_results)
        and len(held_symbols) >= 6
        and len(positive_symbols) >= 4
        and max_share is not None
        and max_share <= Decimal("0.50")
    )
    cross_asset_gate = {
        "passed": cross_asset_passed,
        "comparator_id": _STATIC_EQUAL_WEIGHT_ID,
        "window_results": cross_window_results,
        "symbols_with_nonzero_oos_target": held_symbols,
        "symbols_with_nonzero_oos_target_count": len(held_symbols),
        "positive_contribution_symbols": positive_symbols,
        "positive_contribution_symbol_count": len(positive_symbols),
        "max_absolute_contribution_share": max_share_text,
    }

    composite_gate: dict[str, object]
    if candidate_id == NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID:
        standalone_metric = metric_book[
            NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID
        ]["moderate_friction"]["oos"]
        value_comparison = _metric_comparison(moderate_metric, standalone_metric)
        sharpe_delta_text = value_comparison["sharpe_ratio_delta"]
        sharpe_delta = (
            None if sharpe_delta_text is None else _decimal(sharpe_delta_text)
        )
        return_delta = _decimal(value_comparison["total_return_delta"])
        drawdown_delta = _decimal(value_comparison["max_drawdown_delta"])
        at_least_one_improvement = (
            return_delta > _ZERO
            or drawdown_delta < _ZERO
            or (sharpe_delta is not None and sharpe_delta > _ZERO)
        )
        composite_value_passed = (
            composite_integrity["passed"] is True
            and return_delta >= Decimal("-0.01")
            and drawdown_delta <= Decimal("0.01")
            and (sharpe_delta is None or sharpe_delta >= Decimal("-0.05"))
            and at_least_one_improvement
        )
        composite_gate = {
            "applicable": True,
            "passed": composite_value_passed,
            "integrity": dict(composite_integrity),
            "moderate_friction_oos_comparison_to_standalone": value_comparison,
            "at_least_one_metric_improved": at_least_one_improvement,
        }
    else:
        composite_gate = {
            "applicable": False,
            "passed": True,
            "integrity": None,
        }

    all_passed = (
        exact_oos_passed
        and cost_passed
        and cross_asset_passed
        and composite_gate["passed"] is True
    )
    nonpositive_oos = _decimal(source_candidate["total_return"]) <= _ZERO
    failed_all_baseline_windows = not any(
        item["passed"] for item in baseline_window_results
    )
    route = (
        "preview_review"
        if all_passed
        else (
            "reject"
            if nonpositive_oos and failed_all_baseline_windows
            else "continue_local_research"
        )
    )
    return {
        "baseline_oos_gate": {
            "passed": exact_oos_passed,
            "baseline_id": _SPY_BASELINE_ID,
            "cost_id": "source_fee_only",
            "window_results": baseline_window_results,
        },
        "cost_gate": cost_gate,
        "portfolio_level_cross_asset_gate": cross_asset_gate,
        "composite_integrity_and_value_gate": composite_gate,
        "all_applicable_gates_passed": all_passed,
        "route": route,
        "paper_promotion_allowed": False,
    }


def _composite_integrity(
    standalone: _Simulation,
    composite: _Simulation,
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    standalone_by_date = {record.date: record for record in standalone.records}
    composite_by_date = {record.date: record for record in composite.records}
    changed_dates = []
    for on_date in sorted(set(standalone_by_date) & set(composite_by_date)):
        if not (config.oos_start <= on_date <= config.oos_end):
            continue
        if _weights_differ(
            standalone_by_date[on_date].desired_target,
            composite_by_date[on_date].desired_target,
            NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        ):
            changed_dates.append(on_date.isoformat())
    return {
        "passed": bool(changed_dates),
        "parent_strategy_id": _PARENT_STRATEGY_ID,
        "pairing_role": _PAIRING_ROLE,
        "oos_target_difference_session_count": len(changed_dates),
        "first_oos_target_difference_date": (
            None if not changed_dates else changed_dates[0]
        ),
        "last_oos_target_difference_date": (
            None if not changed_dates else changed_dates[-1]
        ),
        "oos_target_difference_dates": changed_dates,
        "parent_metadata_only": False,
    }


def _cost_result_records(
    strategy_id: str,
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    simulations: Mapping[str, Mapping[str, _Simulation]],
    windows: tuple[ReplicationWindow, ...],
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> list[dict[str, object]]:
    return [
        {
            **cost.to_dict(),
            "window_metrics": [
                dict(metric_book[strategy_id][cost.cost_id][window.window_id])
                for window in windows
            ],
            "target_vector_sha256": _target_vector_sha256(
                simulations[strategy_id][cost.cost_id],
                config.train_start,
                config.oos_end,
            ),
            "oos_target_vector_sha256": _target_vector_sha256(
                simulations[strategy_id][cost.cost_id],
                config.oos_start,
                config.oos_end,
            ),
        }
        for cost in _COST_ASSUMPTIONS
    ]


def _comparator_record(
    strategy_id: str,
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    simulations: Mapping[str, Mapping[str, _Simulation]],
    windows: tuple[ReplicationWindow, ...],
    config: NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    return {
        "comparator_id": strategy_id,
        "cost_results": _cost_result_records(
            strategy_id,
            metric_book,
            simulations,
            windows,
            config,
        ),
    }


def _metric_comparison(
    candidate: Mapping[str, object],
    baseline: Mapping[str, object],
) -> dict[str, object]:
    candidate_sharpe = _optional_decimal(candidate.get("sharpe_ratio"))
    baseline_sharpe = _optional_decimal(baseline.get("sharpe_ratio"))
    return {
        "total_return_delta": _decimal_text(
            _decimal(candidate["total_return"]) - _decimal(baseline["total_return"])
        ),
        "max_drawdown_delta": _decimal_text(
            _decimal(candidate["max_drawdown"])
            - _decimal(baseline["max_drawdown"])
        ),
        "sharpe_ratio_delta": _optional_decimal_text(
            None
            if candidate_sharpe is None or baseline_sharpe is None
            else candidate_sharpe - baseline_sharpe
        ),
    }


def _baseline_window_passed(comparison: Mapping[str, object]) -> bool:
    sharpe_delta = _optional_decimal(comparison.get("sharpe_ratio_delta"))
    return (
        _decimal(comparison["total_return_delta"]) > _ZERO
        and _decimal(comparison["max_drawdown_delta"]) <= Decimal("0.01")
        and (sharpe_delta is None or sharpe_delta >= Decimal("-0.05"))
    )


def _target_vector_sha256(
    simulation: _Simulation,
    start: date,
    end: date,
) -> str:
    rows = []
    symbols = sorted(
        {
            symbol
            for record in simulation.records
            for symbol in record.desired_target
        }
    )
    for record in simulation.records:
        if start <= record.date <= end:
            rows.append(
                record.date.isoformat()
                + "|"
                + "|".join(
                    f"{symbol}={_decimal_text(record.desired_target[symbol])}"
                    for symbol in symbols
                )
            )
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()


def _artifact_manifest(
    config: NexusTradeMonthlyIndependentReplicationConfig,
    *,
    data: _AlignedData,
    preregistration_path: Path,
    result_path: Path,
    summary_path: Path,
) -> dict[str, object]:
    return {
        "record_type": "nexustrade_monthly_independent_replication_manifest",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "claim": "independent_replication_not_authentic_source_replay",
        "artifacts": [
            _artifact_record(preregistration_path),
            _artifact_record(result_path),
            _artifact_record(summary_path),
        ],
        "inputs": [
            {
                "path": str(config.preregistration_path),
                "sha256": config.expected_preregistration_sha256,
                "role": "tracked_outcome_blind_protocol",
            },
            {
                "path": str(config.data_path),
                "sha256": data.data_sha256,
                "role": "canonical_adjusted_daily_bars",
            },
            {
                "path": str(config.data_manifest_path),
                "sha256": data.data_manifest_sha256,
                "role": "canonical_data_provenance_manifest",
            },
        ],
        "manifest_self_hash_embedded": False,
        "source_metrics_used_for_ranking": False,
        "source_metrics_used_for_promotion": False,
        "paper_promotion_allowed": False,
        "safety": _safety_payload(),
    }


def _artifact_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": _file_sha256_required(path, "artifact"),
        "size_bytes": path.stat().st_size,
    }


def _render_summary(result: Mapping[str, object]) -> str:
    lines = [
        "# V5.64 NexusTrade Monthly Independent Replication",
        "",
        "This is an independent local replication, not an authentic replay of "
        "the March 2025 NexusTrade run.",
        "",
        "| candidate | route | OOS gate | cost gate | cross-asset gate | composite gate |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for candidate in result["candidates"]:  # type: ignore[index]
        gates = candidate["gates"]
        lines.append(
            "| {candidate} | {route} | {oos} | {cost} | {cross} | {composite} |".format(
                candidate=candidate["candidate_id"],
                route=candidate["route"],
                oos=str(gates["baseline_oos_gate"]["passed"]).lower(),
                cost=str(gates["cost_gate"]["passed"]).lower(),
                cross=str(
                    gates["portfolio_level_cross_asset_gate"]["passed"]
                ).lower(),
                composite=str(
                    gates["composite_integrity_and_value_gate"]["passed"]
                ).lower(),
            )
        )
    lines.extend(
        (
            "",
            "External source metrics are untrusted and unused for ranking or promotion.",
            "",
            "Paper promotion, submission, broker access, and live activity are forbidden.",
            "",
        )
    )
    return "\n".join(lines)


def _simple_average(
    values: Sequence[Decimal],
    index: int,
    window: int,
) -> Decimal | None:
    if index + 1 < window:
        return None
    items = values[index + 1 - window : index + 1]
    return sum(items, _ZERO) / Decimal(window)


def _rolling_minimum(
    values: Sequence[Decimal],
    index: int,
    window: int,
) -> Decimal | None:
    if index + 1 < window:
        return None
    return min(values[index + 1 - window : index + 1])


def _simple_rsi(
    values: Sequence[Decimal],
    index: int,
    period: int,
) -> Decimal | None:
    if index < period:
        return None
    window = values[index - period : index + 1]
    gains = []
    losses = []
    for previous, current in zip(window, window[1:]):
        delta = current - previous
        gains.append(delta if delta > _ZERO else _ZERO)
        losses.append(-delta if delta < _ZERO else _ZERO)
    average_gain = sum(gains, _ZERO) / Decimal(period)
    average_loss = sum(losses, _ZERO) / Decimal(period)
    if average_gain == _ZERO and average_loss == _ZERO:
        return Decimal("50")
    if average_loss == _ZERO:
        return _HUNDRED
    relative_strength = average_gain / average_loss
    return _HUNDRED - (_HUNDRED / (_ONE + relative_strength))


def _annualized_return(
    total_return: Decimal,
    start_date: date,
    end_date: date,
) -> Decimal | None:
    day_count = (end_date - start_date).days
    if day_count <= 0 or _ONE + total_return <= _ZERO:
        return None
    return Decimal(
        str(math.pow(float(_ONE + total_return), 365.25 / day_count) - 1.0)
    )


def _annualized_volatility(
    returns: tuple[Decimal, ...],
) -> Decimal | None:
    if len(returns) < 2:
        return None
    return Decimal(
        str(stdev(float(item) for item in returns) * math.sqrt(float(_TRADING_DAYS_PER_YEAR)))
    )


def _sharpe_like(
    annualized_return: Decimal | None,
    volatility: Decimal | None,
) -> Decimal | None:
    if annualized_return is None or volatility is None or volatility <= _ZERO:
        return None
    return annualized_return / volatility


def _zero_stock_weights() -> dict[str, Decimal]:
    return {symbol: _ZERO for symbol in NEXUSTRADE_MONTHLY_STOCK_SYMBOLS}


def _validate_target_weights(
    weights: Mapping[str, Decimal],
    symbols: tuple[str, ...],
) -> None:
    if set(weights) != set(symbols):
        raise ValidationError("target weights must contain the exact symbol set.")
    if any(weight < _ZERO or weight > _ONE for weight in weights.values()):
        raise ValidationError("target weights must be between zero and one.")
    if sum(weights.values(), _ZERO) > _ONE + _WEIGHT_TOLERANCE:
        raise ValidationError("target weights must not exceed full investment.")


def _weights_differ(
    left: Mapping[str, Decimal],
    right: Mapping[str, Decimal],
    symbols: tuple[str, ...],
) -> bool:
    return any(
        abs(left.get(symbol, _ZERO) - right.get(symbol, _ZERO))
        > _WEIGHT_TOLERANCE
        for symbol in symbols
    )


def _safety_payload() -> dict[str, object]:
    return {
        "research_only": True,
        "offline_only": True,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_mutation_performed": False,
        "live_authorized": False,
        "live_activity_performed": False,
        "paper_promotion_allowed": False,
        "submit_authorized": False,
        "v5_57_sleeve_ownership_changed": False,
        "v5_57_reconciliation_changed": False,
        "v5_57_auditing_changed": False,
        "v5_57_caps_changed": False,
    }


def _load_json_object(path: Path, field_name: str) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError(f"{field_name} must identify an existing file.")
    if path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ValidationError(f"{field_name} exceeds the bounded size limit.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field_name} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{field_name} must contain a JSON object.")
    return payload


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    _write_text_atomic(
        path,
        json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))
        + "\n",
    )


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _file_sha256_required(path: Path, field_name: str) -> str:
    if not path.is_file():
        raise ValidationError(f"{field_name} must identify an existing file.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str) and "://" not in value:
        path = Path(_required_string(value, field_name))
    else:
        raise ValidationError(f"{field_name} must be a local path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _plain_date(value: date | str, field_name: str) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(_required_string(value, field_name))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be YYYY-MM-DD.") from exc
        return parsed
    raise ValidationError(f"{field_name} must be a plain date.")


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _sha256_text(value: object, field_name: str) -> str:
    text = _required_string(value, field_name).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValidationError(f"{field_name} must be a lowercase SHA-256 hex digest.")
    return text


def _positive_decimal(value: Decimal | str, field_name: str) -> Decimal:
    parsed = _decimal(value)
    if not parsed.is_finite() or parsed <= _ZERO:
        raise ValidationError(f"{field_name} must be positive and finite.")
    return parsed


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, (str, int)) and not isinstance(value, bool):
        try:
            parsed = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValidationError("value must be a Decimal string.") from exc
    else:
        raise ValidationError("value must be a Decimal string.")
    if not parsed.is_finite():
        raise ValidationError("Decimal value must be finite.")
    return parsed


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value)


def _positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else _decimal_text(value)


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


def _config(
    value: object,
) -> NexusTradeMonthlyIndependentReplicationConfig:
    if not isinstance(value, NexusTradeMonthlyIndependentReplicationConfig):
        raise ValidationError(
            "config must be a NexusTradeMonthlyIndependentReplicationConfig."
        )
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m "
        "algotrader.research.nexustrade_monthly_independent_replication"
    )
    parser.add_argument("--output-root", default=str(_DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--data-path", default=str(_DEFAULT_DATA_PATH))
    parser.add_argument(
        "--data-manifest-path",
        default=str(_DEFAULT_DATA_MANIFEST_PATH),
    )
    parser.add_argument(
        "--preregistration-path",
        default=str(_DEFAULT_PREREGISTRATION_PATH),
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = run_nexustrade_monthly_independent_replication(
            NexusTradeMonthlyIndependentReplicationConfig(
                output_root=args.output_root,
                data_path=args.data_path,
                data_manifest_path=args.data_manifest_path,
                preregistration_path=args.preregistration_path,
            )
        )
    except ValidationError as exc:
        print(f"nexustrade_monthly_independent_replication_error: {exc}")
        return 2
    if args.format == "json":
        print(json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":")))
    else:
        print("nexustrade_monthly_independent_replication_status=completed")
        for candidate in payload["candidates"]:
            print(f"{candidate['candidate_id']}_route={candidate['route']}")
        print("paper_promotion_allowed=false")
        print("broker_access_attempted=false")
        print("paper_mutation_performed=false")
        print("live_activity_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
