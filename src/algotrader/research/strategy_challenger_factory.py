"""Deterministic offline strategy challenger factory for SPY candidates."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
from statistics import stdev

from algotrader.errors import ValidationError
from algotrader.research.daily_backtest import (
    DailyBacktestAssumptions,
    DailyBacktestPoint,
    DailyBacktestResult,
    DailyExposure,
    run_daily_backtest,
)
from algotrader.research.local_daily_bars import (
    LocalDailyBar,
    LocalDailyBarsCsvResult,
    load_local_daily_bars_csv,
)
from algotrader.research.price_snapshot import (
    HistoricalPriceBar,
    HistoricalPriceSnapshot,
)

__all__ = [
    "DEFAULT_STRATEGY_CHALLENGER_SYMBOLS",
    "STRATEGY_CHALLENGER_FACTORY_LABELS",
    "STRATEGY_CHALLENGER_PROMOTION_CLASSIFICATIONS",
    "StrategyChallengerCandidate",
    "StrategyChallengerFactoryConfig",
    "build_default_strategy_challenger_candidates",
    "build_strategy_review_packet",
    "build_strategy_challenger_payload",
    "build_strategy_challenger_validation_windows",
    "classify_strategy_challenger_promotion",
    "main",
    "render_strategy_review_packet_markdown",
    "render_strategy_challenger_summary_markdown",
    "run_strategy_challenger_factory",
    "write_strategy_challenger_artifacts",
]


STRATEGY_CHALLENGER_FACTORY_LABELS = (
    "research_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_paper_promotion",
)
STRATEGY_CHALLENGER_PROMOTION_CLASSIFICATIONS = (
    "reject",
    "keep_researching",
    "preview_only",
    "paper_candidate",
)

_RECORD_TYPE = "strategy_challenger_factory"
_SCHEMA_VERSION = "1"
_FACTORY_ID = "v2.16_strategy_challenger_factory"
_PREVIOUS_FACTORY_ID = "v2.13_strategy_challenger_factory"
_DEFAULT_SYMBOL = "SPY"
DEFAULT_STRATEGY_CHALLENGER_SYMBOLS = ("SPY", "QQQ", "IWM", "TLT", "GLD")
_BASKET_SYMBOL = "ETF_BASKET"
_DEFAULT_TIMEFRAME = "1d"
_DEFAULT_DATA_PATH = Path("runs/operator_input/multi_etf_adjusted_daily_canonical.csv")
_DEFAULT_OUTPUT_ROOT = Path("runs/strategy_challengers/latest")
_DEFAULT_INITIAL_EQUITY = Decimal("10000")
_DEFAULT_FEE_BPS = Decimal("0")
_DEFAULT_SLIPPAGE_BPS = Decimal("0")
_ONE = Decimal("1")
_ZERO = Decimal("0")
_TRADING_DAYS_PER_YEAR = Decimal("252")
_HASH_CHUNK_SIZE = 1024 * 1024

_BASELINE_CANDIDATE_ID = "spy_sma_50_200_baseline"
_CASH_RISK_OFF_COMPARATOR_ID = "spy_sma_50_200_cash_risk_off_comparator"
_BUY_AND_HOLD_COMPARATOR_ID = "spy_buy_and_hold_comparator"
_COMPARATOR_CANDIDATE_IDS = (
    _CASH_RISK_OFF_COMPARATOR_ID,
    _BUY_AND_HOLD_COMPARATOR_ID,
)
_RELATIVE_MOMENTUM_FAMILY = "etf_relative_momentum_basket"
_RELATIVE_MOMENTUM_CASH_FILTER_STATE = "cash_filter_positive_momentum"
_REBALANCE_RULE_MONTHLY = "monthly"
_REBALANCE_RULE_DAILY = "daily"
_NO_PAPER_PROMOTION_REASON = "v2_16_no_paper_promotion"
_DATA_QUALITY_VALID = "valid_local_daily_bars"
_DATA_QUALITY_MALFORMED = "malformed_or_unreadable_local_daily_bars"
_DATA_QUALITY_MISSING = "missing_local_daily_bars"
_DATA_QUALITY_MIXED = "mixed_local_daily_bars"
_DATA_AVAILABILITY_AVAILABLE = "available"
_DATA_AVAILABILITY_MISSING = "missing_data"
_DATA_REFRESH_NOT_REQUIRED = "not_required"
_DATA_REFRESH_REQUIRED = "data_refresh_required"
_VALIDATION_WINDOW_METHOD = (
    "full_sample_plus_chronological_half_split_plus_three_walk_forward_folds"
)
_FULL_SAMPLE_WINDOW_ID = "full_sample"
_EARLY_TRAIN_WINDOW_ID = "early_train"
_LATER_TEST_WINDOW_ID = "later_test"
_ZERO_COST_ID = "zero_cost"
_LOW_COST_ID = "low_cost_1bp"
_MODERATE_COST_ID = "moderate_cost_5bps"
_PROMOTION_PRIORITY = {
    "reject": 0,
    "keep_researching": 1,
    "preview_only": 2,
    "paper_candidate": 3,
}

_DEFAULT_LIMITATIONS = (
    "offline deterministic research only",
    "uses local adjusted-close daily bars only",
    "cash/risk-off return is modeled as zero return before costs",
    "no tax, borrow, liquidity, slippage realism, dividend timing, or intraday execution model",
    "no broker access, broker mutation, paper submit, live submit, or capital authority",
    "not a trading recommendation",
)


@dataclass(frozen=True, slots=True)
class StrategyChallengerCostAssumption:
    """Deterministic transaction-cost assumption for sensitivity checks."""

    cost_id: str
    fee_bps: Decimal
    slippage_bps: Decimal
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "cost_id", _required_string(self.cost_id, "cost_id"))
        object.__setattr__(
            self,
            "fee_bps",
            _non_negative_decimal(self.fee_bps, "fee_bps"),
        )
        object.__setattr__(
            self,
            "slippage_bps",
            _non_negative_decimal(self.slippage_bps, "slippage_bps"),
        )
        object.__setattr__(
            self,
            "description",
            _required_string(self.description, "description"),
        )

    @property
    def total_cost_bps_per_transition(self) -> Decimal:
        return self.fee_bps + self.slippage_bps

    def to_dict(self) -> dict[str, object]:
        return {
            "cost_id": self.cost_id,
            "fee_bps": _decimal_text(self.fee_bps),
            "slippage_bps": _decimal_text(self.slippage_bps),
            "total_cost_bps_per_transition": _decimal_text(
                self.total_cost_bps_per_transition
            ),
            "cost_model": "abs(exposure_delta) * total_cost_bps_per_transition / 10000",
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class StrategyChallengerValidationWindow:
    """Chronological validation span over the local adjusted daily history."""

    window_id: str
    window_role: str
    start_index: int
    end_index_exclusive: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "window_id",
            _required_string(self.window_id, "window_id"),
        )
        object.__setattr__(
            self,
            "window_role",
            _required_string(self.window_role, "window_role"),
        )
        object.__setattr__(
            self,
            "start_index",
            _non_negative_int(self.start_index, "start_index"),
        )
        object.__setattr__(
            self,
            "end_index_exclusive",
            _positive_int(self.end_index_exclusive, "end_index_exclusive"),
        )
        if self.start_index >= self.end_index_exclusive:
            raise ValidationError("validation window start must be before end.")

    @property
    def bar_count(self) -> int:
        return self.end_index_exclusive - self.start_index

    def to_dict(self, bars: tuple[LocalDailyBar, ...]) -> dict[str, object]:
        if self.end_index_exclusive > len(bars):
            raise ValidationError("validation window exceeds usable bars.")
        return {
            "window_id": self.window_id,
            "window_role": self.window_role,
            "start_index": self.start_index,
            "end_index_exclusive": self.end_index_exclusive,
            "bar_count": self.bar_count,
            "as_of_start": bars[self.start_index].date.isoformat(),
            "as_of_end": bars[self.end_index_exclusive - 1].date.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class StrategyChallengerCandidate:
    """Static definition for one deterministic strategy challenger."""

    candidate_id: str
    strategy_family: str
    symbol: str
    timeframe: str
    fast_window: int
    slow_window: int
    role: str = "challenger"
    risk_off_state: str = "cash"
    basket_symbols: tuple[str, ...] = ()
    top_n: int = 1
    rebalance_rule: str = _REBALANCE_RULE_DAILY

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _required_string(self.candidate_id, "candidate_id"),
        )
        object.__setattr__(
            self,
            "strategy_family",
            _required_string(self.strategy_family, "strategy_family"),
        )
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "timeframe",
            _required_string(self.timeframe, "timeframe"),
        )
        object.__setattr__(
            self,
            "fast_window",
            _positive_int(self.fast_window, "fast_window"),
        )
        object.__setattr__(
            self,
            "slow_window",
            _positive_int(self.slow_window, "slow_window"),
        )
        object.__setattr__(self, "role", _required_string(self.role, "role"))
        object.__setattr__(
            self,
            "risk_off_state",
            _required_string(self.risk_off_state, "risk_off_state"),
        )
        object.__setattr__(
            self,
            "basket_symbols",
            _basket_symbol_tuple(self.basket_symbols),
        )
        object.__setattr__(self, "top_n", _positive_int(self.top_n, "top_n"))
        object.__setattr__(
            self,
            "rebalance_rule",
            _rebalance_rule(self.rebalance_rule),
        )
        if self.fast_window >= self.slow_window:
            raise ValidationError("fast_window must be less than slow_window.")
        if self.basket_symbols and self.top_n > len(self.basket_symbols):
            raise ValidationError("top_n must not exceed basket_symbols count.")
        if self.strategy_family == _RELATIVE_MOMENTUM_FAMILY and len(self.basket_symbols) < 2:
            raise ValidationError("relative momentum candidates require multiple ETF symbols.")

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_family": self.strategy_family,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "fast_window": self.fast_window,
            "slow_window": self.slow_window,
            "role": self.role,
            "risk_off_state": self.risk_off_state,
            "basket_symbols": list(self.basket_symbols),
            "top_n": self.top_n,
            "rebalance_rule": self.rebalance_rule,
        }


@dataclass(frozen=True, slots=True)
class StrategyChallengerFactoryConfig:
    """Inputs for one offline strategy challenger factory run."""

    output_root: Path | str
    data_path: Path | str = _DEFAULT_DATA_PATH
    symbol: str = _DEFAULT_SYMBOL
    symbols: Iterable[str] | str | None = None
    as_of: date | str | None = None
    initial_equity: Decimal | str = _DEFAULT_INITIAL_EQUITY
    fee_bps: Decimal | str = _DEFAULT_FEE_BPS
    slippage_bps: Decimal | str = _DEFAULT_SLIPPAGE_BPS
    candidates: tuple[StrategyChallengerCandidate, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _path(self.output_root, "output_root"))
        object.__setattr__(self, "data_path", _path(self.data_path, "data_path"))
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "symbols",
            _symbol_tuple(self.symbols, fallback_symbol=self.symbol),
        )
        object.__setattr__(self, "as_of", _optional_date(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "initial_equity",
            _positive_decimal(self.initial_equity, "initial_equity"),
        )
        object.__setattr__(
            self,
            "fee_bps",
            _non_negative_decimal(self.fee_bps, "fee_bps"),
        )
        object.__setattr__(
            self,
            "slippage_bps",
            _non_negative_decimal(self.slippage_bps, "slippage_bps"),
        )
        if self.candidates is None:
            candidates = build_default_strategy_challenger_candidates(symbol=self.symbol)
        else:
            candidates = _candidate_tuple(self.candidates)
        object.__setattr__(self, "candidates", candidates)
        if not any(candidate.candidate_id == _BASELINE_CANDIDATE_ID for candidate in candidates):
            raise ValidationError("candidates must include the SPY SMA 50/200 baseline.")
        if self.symbol not in self.symbols:
            raise ValidationError("symbols must include the operating baseline symbol.")


@dataclass(frozen=True, slots=True)
class _BasketBacktest:
    """Synthetic basket equity curve plus allocation metadata."""

    points: tuple[DailyBacktestPoint, ...]
    exposures: tuple[DailyExposure, ...]
    allocation_turnovers: tuple[Decimal, ...]
    scheduled_rebalance_dates: tuple[date, ...]
    rebalance_dates: tuple[date, ...]
    rebalance_allocations: tuple[dict[str, object], ...]

    @property
    def turnover(self) -> Decimal:
        return sum(self.allocation_turnovers, _ZERO)

    @property
    def transition_count(self) -> int:
        return sum(1 for turnover in self.allocation_turnovers if turnover != _ZERO)


def build_default_strategy_challenger_candidates(
    *,
    symbol: str = _DEFAULT_SYMBOL,
) -> tuple[StrategyChallengerCandidate, ...]:
    """Return the controlled v2.16 deterministic candidate set."""

    checked_symbol = _symbol(symbol)
    return (
        StrategyChallengerCandidate(
            candidate_id=_BASELINE_CANDIDATE_ID,
            strategy_family="sma_crossover_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=50,
            slow_window=200,
            role="current_baseline",
        ),
        StrategyChallengerCandidate(
            candidate_id=_BUY_AND_HOLD_COMPARATOR_ID,
            strategy_family="buy_and_hold_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=1,
            slow_window=200,
            role="benchmark_comparator",
            risk_off_state="none",
        ),
        StrategyChallengerCandidate(
            candidate_id="spy_sma_20_100_long_only",
            strategy_family="sma_crossover_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=20,
            slow_window=100,
        ),
        StrategyChallengerCandidate(
            candidate_id="spy_sma_10_50_long_only",
            strategy_family="sma_crossover_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=10,
            slow_window=50,
        ),
        StrategyChallengerCandidate(
            candidate_id="spy_sma_50_150_long_only",
            strategy_family="sma_crossover_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=50,
            slow_window=150,
        ),
        StrategyChallengerCandidate(
            candidate_id="spy_sma_100_200_long_only",
            strategy_family="sma_crossover_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=100,
            slow_window=200,
        ),
        StrategyChallengerCandidate(
            candidate_id="spy_tsmom_252_long_only",
            strategy_family="time_series_momentum_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=1,
            slow_window=252,
        ),
        StrategyChallengerCandidate(
            candidate_id="spy_drawdown_20pct_risk_off",
            strategy_family="drawdown_filter_long_only",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=63,
            slow_window=252,
            risk_off_state="cash_below_20pct_drawdown",
        ),
        StrategyChallengerCandidate(
            candidate_id=_CASH_RISK_OFF_COMPARATOR_ID,
            strategy_family="sma_crossover_long_only_cash_risk_off",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=50,
            slow_window=200,
            role="baseline_comparator",
            risk_off_state="cash_zero_return",
        ),
        StrategyChallengerCandidate(
            candidate_id="relative_momentum_top1_126d_monthly",
            strategy_family=_RELATIVE_MOMENTUM_FAMILY,
            symbol=_BASKET_SYMBOL,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=1,
            slow_window=126,
            basket_symbols=DEFAULT_STRATEGY_CHALLENGER_SYMBOLS,
            top_n=1,
            rebalance_rule=_REBALANCE_RULE_MONTHLY,
            risk_off_state="fully_invested_top_ranked_etf",
        ),
        StrategyChallengerCandidate(
            candidate_id="relative_momentum_top1_252d_monthly",
            strategy_family=_RELATIVE_MOMENTUM_FAMILY,
            symbol=_BASKET_SYMBOL,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=1,
            slow_window=252,
            basket_symbols=DEFAULT_STRATEGY_CHALLENGER_SYMBOLS,
            top_n=1,
            rebalance_rule=_REBALANCE_RULE_MONTHLY,
            risk_off_state="fully_invested_top_ranked_etf",
        ),
        StrategyChallengerCandidate(
            candidate_id="dual_momentum_top1_252d_monthly_with_cash_filter",
            strategy_family=_RELATIVE_MOMENTUM_FAMILY,
            symbol=_BASKET_SYMBOL,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=1,
            slow_window=252,
            basket_symbols=DEFAULT_STRATEGY_CHALLENGER_SYMBOLS,
            top_n=1,
            rebalance_rule=_REBALANCE_RULE_MONTHLY,
            risk_off_state=_RELATIVE_MOMENTUM_CASH_FILTER_STATE,
        ),
        StrategyChallengerCandidate(
            candidate_id="relative_momentum_equal_weight_top2_126d_monthly",
            strategy_family=_RELATIVE_MOMENTUM_FAMILY,
            symbol=_BASKET_SYMBOL,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=2,
            slow_window=126,
            basket_symbols=DEFAULT_STRATEGY_CHALLENGER_SYMBOLS,
            top_n=2,
            rebalance_rule=_REBALANCE_RULE_MONTHLY,
            risk_off_state="fully_invested_top_ranked_etfs",
        ),
    )


def build_strategy_challenger_validation_windows(
    bars: Sequence[LocalDailyBar],
) -> tuple[dict[str, object], ...]:
    """Return deterministic chronological validation-window metadata."""

    bar_items = tuple(bars)
    if not bar_items:
        return ()
    return tuple(
        window.to_dict(bar_items)
        for window in _build_validation_window_specs(len(bar_items))
    )


def run_strategy_challenger_factory(
    config: StrategyChallengerFactoryConfig,
) -> dict[str, object]:
    """Build the payload and write all required strategy challenger artifacts."""

    checked_config = _config(config)
    payload = build_strategy_challenger_payload(checked_config)
    manifest = write_strategy_challenger_artifacts(payload, checked_config.output_root)
    result = dict(payload)
    result["manifest"] = manifest
    return result


def build_strategy_challenger_payload(
    config: StrategyChallengerFactoryConfig,
) -> dict[str, object]:
    """Evaluate challenger candidates against the operating SPY baseline."""

    checked_config = _config(config)
    data_sha256 = _file_sha256_or_none(checked_config.data_path)
    cost_assumptions = _cost_assumption_records()
    symbol_records: list[dict[str, object]] = []
    validation_windows_by_symbol: dict[str, list[dict[str, object]]] = {}
    all_results: list[dict[str, object]] = []

    for symbol in checked_config.symbols:
        results, symbol_record = _evaluate_symbol_candidate_set(
            checked_config,
            symbol=symbol,
            data_sha256=data_sha256,
        )
        all_results.extend(results)
        symbol_records.append(symbol_record)
        validation_windows_by_symbol[symbol] = list(
            symbol_record.get("validation_windows", [])
        )

    basket_candidates = _basket_candidates(checked_config.candidates)
    if basket_candidates and len(checked_config.symbols) > 1:
        basket_results, basket_validation_windows = _evaluate_basket_candidate_set(
            checked_config,
            candidates=basket_candidates,
            data_sha256=data_sha256,
        )
        all_results.extend(basket_results)
        validation_windows_by_symbol[_BASKET_SYMBOL] = list(basket_validation_windows)

    cross_asset_validation = _build_cross_asset_validation(
        all_results,
        symbol_records,
        checked_config,
    )
    if len(checked_config.symbols) > 1:
        all_results = list(
            _apply_cross_asset_promotion_gates(
                all_results,
                checked_config,
            )
        )
        cross_asset_validation = _build_cross_asset_validation(
            all_results,
            symbol_records,
            checked_config,
        )

    recommendations = _build_promotion_recommendations(
        all_results,
        cross_asset_validation=cross_asset_validation,
    )
    as_of_start, as_of_end = _payload_as_of_range(all_results)
    validation_windows = tuple(
        validation_windows_by_symbol.get(checked_config.symbol, [])
    )
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "previous_factory_id": _PREVIOUS_FACTORY_ID,
        "run_id": _run_id(checked_config.symbols, as_of_end, data_sha256),
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "symbol": checked_config.symbol,
        "operating_baseline_symbol": checked_config.symbol,
        "symbols": list(checked_config.symbols),
        "symbol_count": len(checked_config.symbols),
        "symbols_evaluated": list(cross_asset_validation["symbols_evaluated"]),
        "symbols_missing_data": list(cross_asset_validation["symbols_missing_data"]),
        "symbol_data_statuses": list(symbol_records),
        "timeframe": _DEFAULT_TIMEFRAME,
        "data_path": str(checked_config.data_path),
        "data_sha256": data_sha256,
        "data_quality_status": _aggregate_data_quality_status(symbol_records),
        "data_error": _aggregate_data_error(symbol_records),
        "as_of_start": as_of_start,
        "as_of_end": as_of_end,
        "candidate_count": len(all_results),
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "validation_window_method": _VALIDATION_WINDOW_METHOD,
        "validation_windows": list(validation_windows),
        "validation_windows_by_symbol": validation_windows_by_symbol,
        "cost_assumptions": list(cost_assumptions),
        "results": [dict(result) for result in all_results],
        "cross_asset_validation": cross_asset_validation,
        "promotion_recommendations": recommendations,
        "safety": _safety_payload(),
    }


def classify_strategy_challenger_promotion(
    candidate_result: Mapping[str, object],
    baseline_result: Mapping[str, object] | None,
) -> tuple[str, tuple[str, ...]]:
    """Classify one candidate promotion recommendation conservatively."""

    result = dict(candidate_result)
    reasons: list[str] = []

    if result.get("data_quality_status") != _DATA_QUALITY_VALID:
        if result.get("data_availability_status") == _DATA_AVAILABILITY_MISSING:
            return "reject", (_DATA_AVAILABILITY_MISSING, _DATA_REFRESH_REQUIRED)
        return "reject", ("malformed_or_missing_data",)
    if str(result.get("metrics_status", "")) == "rejected_insufficient_history":
        return "reject", ("insufficient_history_for_candidate_slow_window",)
    if str(result.get("metrics_status", "")) != "valid":
        return "reject", ("invalid_or_impossible_metrics",)

    usable_bars = _int_from_result(result, "usable_bars")
    required_history_bars = _int_from_result(result, "required_history_bars")
    evaluated_return_count = _int_from_result(result, "evaluated_return_count")
    if usable_bars < required_history_bars:
        return "reject", ("insufficient_history_for_candidate_slow_window",)
    if evaluated_return_count < 30:
        return "reject", ("insufficient_evaluated_return_count",)
    if not _metrics_are_possible(result):
        return "reject", ("impossible_metrics",)

    baseline = dict(baseline_result) if baseline_result is not None else None
    if baseline is None or baseline.get("metrics_status") != "valid":
        return "keep_researching", ("baseline_comparison_unavailable",)

    return_delta = _decimal_from_result(result, "baseline_total_return_delta")
    drawdown_delta = _decimal_from_result(result, "baseline_max_drawdown_delta")
    sharpe_delta = _optional_decimal_from_result(result, "baseline_sharpe_ratio_delta")
    out_of_sample_validation = _mapping_or_empty(result.get("out_of_sample_validation"))
    cost_sensitivity = _mapping_or_empty(result.get("cost_sensitivity_summary"))
    out_of_sample_passed = out_of_sample_validation.get("validation_passed") is True
    out_of_sample_failed = out_of_sample_validation.get("validation_failed") is True
    edge_broken_by_cost = cost_sensitivity.get("edge_broken_by_moderate_cost") is True
    highly_cost_sensitive = (
        cost_sensitivity.get("returns_highly_cost_sensitive") is True
    )

    if result.get("candidate_id") == _BASELINE_CANDIDATE_ID:
        return "keep_researching", ("current_baseline_reference",)

    if result.get("candidate_id") == _BUY_AND_HOLD_COMPARATOR_ID:
        return "keep_researching", ("benchmark_buy_and_hold_comparator",)

    if result.get("candidate_id") == _CASH_RISK_OFF_COMPARATOR_ID:
        return "keep_researching", ("baseline_cash_risk_off_comparator",)

    if usable_bars < max(252, required_history_bars * 2):
        return "keep_researching", ("sample_evidence_too_short_for_promotion",)

    if return_delta <= Decimal("-0.05") and drawdown_delta <= Decimal("-0.02"):
        return "reject", ("drawdown_improvement_with_severe_return_degradation",)

    if return_delta <= Decimal("-0.02") and drawdown_delta >= Decimal("0.02"):
        return "reject", ("materially_worse_return_and_drawdown_than_baseline",)

    sharpe_improved = sharpe_delta is not None and sharpe_delta >= Decimal("0.10")
    drawdown_not_regressed = drawdown_delta <= Decimal("0.01")
    drawdown_improved = drawdown_delta < Decimal("0")
    return_improved = return_delta > Decimal("0")
    return_clear = return_delta >= Decimal("0.03")
    positive_absolute_return = _decimal_from_result(result, "total_return") > _ZERO

    if return_improved and out_of_sample_failed:
        if _int_from_result(
            out_of_sample_validation,
            "passed_window_count",
        ) > 0:
            return "preview_only", ("mixed_out_of_sample_evidence",)
        return "keep_researching", ("full_sample_edge_failed_out_of_sample",)

    if return_improved and edge_broken_by_cost:
        return "keep_researching", ("cost_sensitivity_breaks_edge",)

    if return_improved and highly_cost_sensitive:
        return "keep_researching", ("returns_highly_cost_sensitive",)

    if (
        return_clear
        and positive_absolute_return
        and drawdown_not_regressed
        and sharpe_improved
        and out_of_sample_passed
        and not edge_broken_by_cost
        and not highly_cost_sensitive
        and usable_bars >= 500
    ):
        return "preview_only", (
            "clear_return_improvement_without_drawdown_regression",
            "positive_absolute_return",
            "risk_adjusted_score_improved",
            "out_of_sample_validation_passed",
            "cost_sensitivity_survived",
            "sample_history_acceptable",
            _NO_PAPER_PROMOTION_REASON,
        )

    if return_improved and drawdown_delta <= Decimal("0.03") and not out_of_sample_failed:
        reasons.append("return_improved_without_obvious_drawdown_regression")
    if drawdown_improved and return_delta >= Decimal("-0.01") and not out_of_sample_failed:
        reasons.append("drawdown_improved_without_material_return_regression")
    if out_of_sample_passed and not return_improved:
        reasons.append("out_of_sample_evidence_interesting_but_full_sample_edge_absent")
    if reasons:
        return "preview_only", tuple(reasons)

    return "keep_researching", ("mixed_or_small_baseline_comparison",)


def write_strategy_challenger_artifacts(
    payload: Mapping[str, object],
    output_root: Path | str,
) -> dict[str, object]:
    """Write required JSON, JSONL, markdown, recommendations, and manifest files."""

    root = _path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)

    payload_dict = dict(payload)
    recommendations = dict(payload_dict["promotion_recommendations"])  # type: ignore[index]
    review_packet = build_strategy_review_packet(payload_dict)

    artifact_writers = (
        (
            "challenger_results.json",
            lambda path: _write_text(path, _json_dumps(payload_dict) + "\n"),
        ),
        (
            "challenger_results.jsonl",
            lambda path: _write_text(
                path,
                "".join(
                    _json_dumps(result) + "\n"
                    for result in _result_list(payload_dict)
                ),
            ),
        ),
        (
            "challenger_summary.md",
            lambda path: _write_text(
                path,
                render_strategy_challenger_summary_markdown(payload_dict),
            ),
        ),
        (
            "promotion_recommendations.json",
            lambda path: _write_text(path, _json_dumps(recommendations) + "\n"),
        ),
        (
            "strategy_review_packet.json",
            lambda path: _write_text(path, _json_dumps(review_packet) + "\n"),
        ),
        (
            "strategy_review_packet.md",
            lambda path: _write_text(
                path,
                render_strategy_review_packet_markdown(review_packet),
            ),
        ),
        (
            "validation_windows.json",
            lambda path: _write_text(
                path,
                _json_dumps(_validation_windows_artifact(payload_dict)) + "\n",
            ),
        ),
        (
            "cost_sensitivity.json",
            lambda path: _write_text(
                path,
                _json_dumps(_cost_sensitivity_artifact(payload_dict)) + "\n",
            ),
        ),
        (
            "cross_asset_validation.json",
            lambda path: _write_text(
                path,
                _json_dumps(_cross_asset_validation_artifact(payload_dict)) + "\n",
            ),
        ),
        (
            "cross_asset_summary.md",
            lambda path: _write_text(
                path,
                render_cross_asset_summary_markdown(payload_dict),
            ),
        ),
    )

    artifact_paths: list[Path] = []
    for filename, writer in artifact_writers:
        artifact_path = root / filename
        writer(artifact_path)
        artifact_paths.append(artifact_path)

    manifest = _manifest_payload(payload_dict, root, artifact_paths)
    _write_text(root / "manifest.json", _json_dumps(manifest) + "\n")
    return manifest


def render_strategy_challenger_summary_markdown(
    payload: Mapping[str, object],
) -> str:
    """Render a compact deterministic markdown summary for operator review."""

    payload_dict = dict(payload)
    recommendations = dict(payload_dict["promotion_recommendations"])  # type: ignore[index]
    lines = [
        "# Strategy Challenger Factory",
        "",
        "Labels: " + ", ".join(str(item) for item in payload_dict["labels"]),  # type: ignore[index]
        "",
        "## Data",
        f"- operating_baseline_symbol: {payload_dict.get('operating_baseline_symbol')}",
        "- symbols: "
        + ", ".join(str(item) for item in payload_dict.get("symbols", [])),
        f"- timeframe: {payload_dict.get('timeframe')}",
        f"- data_path: {payload_dict.get('data_path')}",
        f"- data_sha256: {payload_dict.get('data_sha256')}",
        f"- as_of_start: {payload_dict.get('as_of_start')}",
        f"- as_of_end: {payload_dict.get('as_of_end')}",
        f"- data_quality_status: {payload_dict.get('data_quality_status')}",
        "",
        "## Validation Windows",
        f"- method: {payload_dict.get('validation_window_method')}",
    ]
    for window in payload_dict.get("validation_windows", []):
        if isinstance(window, Mapping):
            lines.append(
                "- {window_id}: {as_of_start} to {as_of_end} "
                "({bar_count} bars, {window_role})".format(
                    window_id=window.get("window_id"),
                    as_of_start=window.get("as_of_start"),
                    as_of_end=window.get("as_of_end"),
                    bar_count=window.get("bar_count"),
                    window_role=window.get("window_role"),
                )
            )
    lines.extend(
        [
            "",
            "## Cost Assumptions",
        ]
    )
    for assumption in payload_dict.get("cost_assumptions", []):
        if isinstance(assumption, Mapping):
            lines.append(
                "- {cost_id}: {total_cost_bps_per_transition} bps per transition".format(
                    cost_id=assumption.get("cost_id"),
                    total_cost_bps_per_transition=assumption.get(
                        "total_cost_bps_per_transition"
                    ),
                )
            )
    lines.extend(
        [
            "",
            "## Cross-Asset Validation",
        ]
    )
    cross_asset = _mapping_or_empty(payload_dict.get("cross_asset_validation"))
    lines.extend(
        [
            "- symbols_evaluated: "
            + ", ".join(str(item) for item in cross_asset.get("symbols_evaluated", [])),
            "- symbols_missing_data: "
            + ", ".join(str(item) for item in cross_asset.get("symbols_missing_data", [])),
            "- robustness_flags: "
            + ", ".join(str(item) for item in cross_asset.get("robustness_flags", [])),
            "",
            "## Candidate Results",
            "| symbol | candidate_id | total_return | max_drawdown | sharpe_ratio | transitions | exposure_pct | OOS status | cost status | classification |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for result in _result_list(payload_dict):
        lines.append(
            "| {symbol} | {candidate_id} | {total_return} | {max_drawdown} | "
            "{sharpe_ratio} | {transition_count} | {exposure_percentage} | "
            "{oos_status} | {cost_status} | {promotion_classification} |".format(
                symbol=result.get("symbol"),
                candidate_id=result.get("candidate_id"),
                total_return=_markdown_value(result.get("total_return")),
                max_drawdown=_markdown_value(result.get("max_drawdown")),
                sharpe_ratio=_markdown_value(result.get("sharpe_ratio")),
                transition_count=_markdown_value(result.get("transition_count")),
                exposure_percentage=_markdown_value(result.get("exposure_percentage")),
                oos_status=_markdown_value(result.get("oos_status")),
                cost_status=_markdown_value(result.get("cost_sensitivity_status")),
                promotion_classification=result.get("promotion_classification"),
            )
        )

    lines.extend(
        [
            "",
            "## Promotion Recommendations",
            f"- best_candidate_id: {recommendations.get('best_candidate_id')}",
            f"- best_candidate_classification: {recommendations.get('best_candidate_classification')}",
            f"- classification_recommendation: {recommendations.get('classification_recommendation')}",
            "",
            "## Safety",
            "- broker_access_attempted: false",
            "- broker_mutation_performed: false",
            "- live_mutation_performed: false",
            "- network_access_attempted: false",
            "- credential_access_attempted: false",
            "",
            "## Limitations",
        ]
    )
    for limitation in _DEFAULT_LIMITATIONS:
        lines.append(f"- {limitation}")
    lines.append("")
    return "\n".join(lines)


def render_cross_asset_summary_markdown(
    payload: Mapping[str, object],
) -> str:
    """Render the deterministic ETF basket validation summary."""

    payload_dict = dict(payload)
    cross_asset = _mapping_or_empty(payload_dict.get("cross_asset_validation"))
    lines = [
        "# Cross-Asset Strategy Validation",
        "",
        "Labels: " + ", ".join(str(item) for item in payload_dict["labels"]),  # type: ignore[index]
        "",
        "## Basket",
        f"- operating_baseline_symbol: {payload_dict.get('operating_baseline_symbol')}",
        "- symbols_requested: "
        + ", ".join(str(item) for item in cross_asset.get("symbols_requested", [])),
        "- symbols_evaluated: "
        + ", ".join(str(item) for item in cross_asset.get("symbols_evaluated", [])),
        "- symbols_missing_data: "
        + ", ".join(str(item) for item in cross_asset.get("symbols_missing_data", [])),
        "- robustness_flags: "
        + ", ".join(str(item) for item in cross_asset.get("robustness_flags", [])),
        "",
        "## OOS By Symbol",
        "| symbol | passing_oos_candidates | failing_oos_candidates |",
        "| --- | --- | --- |",
    ]
    passing = _mapping_or_empty(cross_asset.get("candidates_passing_oos_by_symbol"))
    failing = _mapping_or_empty(cross_asset.get("candidates_failing_oos_by_symbol"))
    for symbol in payload_dict.get("symbols", []):
        lines.append(
            "| {symbol} | {passing} | {failing} |".format(
                symbol=symbol,
                passing=", ".join(str(item) for item in passing.get(str(symbol), [])),
                failing=", ".join(str(item) for item in failing.get(str(symbol), [])),
            )
        )

    lines.extend(
        [
            "",
            "## Aggregate Candidate Scores",
            "| candidate_id | symbol_count | average_rank | average_score |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for score in cross_asset.get("candidate_aggregate_scores", []):
        if not isinstance(score, Mapping):
            continue
        lines.append(
            "| {candidate_id} | {symbol_count} | {average_rank} | {average_score} |".format(
                candidate_id=score.get("candidate_id"),
                symbol_count=score.get("symbol_count"),
                average_rank=score.get("average_rank"),
                average_score=score.get("average_score"),
            )
        )

    lines.extend(
        [
            "",
            "## Promotion Gate",
            "| candidate_id | allowed | blockers |",
            "| --- | ---: | --- |",
        ]
    )
    for rollup in cross_asset.get("candidate_rollups", []):
        if not isinstance(rollup, Mapping):
            continue
        lines.append(
            "| {candidate_id} | {allowed} | {blockers} |".format(
                candidate_id=rollup.get("candidate_id"),
                allowed=rollup.get("paper_candidate_allowed"),
                blockers=", ".join(
                    str(item) for item in rollup.get("paper_candidate_blockers", [])
                ),
            )
        )

    lines.extend(
        [
            "",
            "## Safety",
            "- broker_access_attempted: false",
            "- broker_mutation_performed: false",
            "- paper_submit_performed: false",
            "- live_mutation_performed: false",
            "- network_access_attempted: false",
            "- profit_claim: none",
            "",
        ]
    )
    return "\n".join(lines)


def build_strategy_review_packet(payload: Mapping[str, object]) -> dict[str, object]:
    """Build compact operator-facing evidence and rationale for each candidate."""

    payload_dict = dict(payload)
    results = _result_list(payload_dict)
    benchmark_available = any(
        result.get("candidate_id") == _BUY_AND_HOLD_COMPARATOR_ID
        for result in results
    )
    return {
        "record_type": "strategy_challenger_review_packet",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": payload_dict.get("factory_id"),
        "previous_factory_id": payload_dict.get("previous_factory_id"),
        "run_id": payload_dict.get("run_id"),
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "symbol": payload_dict.get("symbol"),
        "operating_baseline_symbol": payload_dict.get("operating_baseline_symbol"),
        "symbols": list(payload_dict.get("symbols", [])),
        "timeframe": payload_dict.get("timeframe"),
        "data_path": payload_dict.get("data_path"),
        "data_sha256": payload_dict.get("data_sha256"),
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "benchmark_candidate_id": (
            _BUY_AND_HOLD_COMPARATOR_ID if benchmark_available else None
        ),
        "validation_window_method": payload_dict.get("validation_window_method"),
        "cost_assumptions": list(payload_dict.get("cost_assumptions", [])),
        "promotion_recommendations": payload_dict.get(
            "promotion_recommendations",
            {},
        ),
        "cross_asset_validation": payload_dict.get("cross_asset_validation", {}),
        "candidates": [
            _strategy_review_candidate(result, benchmark_available=benchmark_available)
            for result in results
        ],
        "safety": _safety_payload(),
        "limitations": list(_DEFAULT_LIMITATIONS),
    }


def render_strategy_review_packet_markdown(packet: Mapping[str, object]) -> str:
    """Render the strategy review packet as compact markdown."""

    packet_dict = dict(packet)
    recommendations = _mapping_or_empty(packet_dict.get("promotion_recommendations"))
    lines = [
        "# Strategy Review Packet",
        "",
        "Labels: " + ", ".join(str(item) for item in packet_dict["labels"]),  # type: ignore[index]
        "",
        "## Evidence Summary",
        f"- baseline_candidate_id: {packet_dict.get('baseline_candidate_id')}",
        f"- benchmark_candidate_id: {packet_dict.get('benchmark_candidate_id')}",
        "- symbols: "
        + ", ".join(str(item) for item in packet_dict.get("symbols", [])),
        f"- classification_recommendation: {recommendations.get('classification_recommendation')}",
        "- broker_access_attempted: false",
        "- broker_mutation_performed: false",
        "- paper_submit_performed: false",
        "- live_mutation_performed: false",
        "",
        "## Candidate Decisions",
        "| symbol | candidate_id | role | total_return | OOS | moderate_cost | classification | rationale |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    candidates = packet_dict.get("candidates", [])
    if isinstance(candidates, Iterable) and not isinstance(
        candidates,
        (str, bytes, Mapping),
    ):
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            metrics = _mapping_or_empty(candidate.get("metrics_summary"))
            oos = _mapping_or_empty(candidate.get("oos_result"))
            cost = _mapping_or_empty(candidate.get("cost_sensitivity_result"))
            lines.append(
                "| {symbol} | {candidate_id} | {role} | {total_return} | "
                "passed={oos_passed}, failed={oos_failed} | "
                "edge_broken={edge_broken}, sensitive={sensitive} | "
                "{classification} | {rationale} |".format(
                    symbol=candidate.get("symbol"),
                    candidate_id=candidate.get("candidate_id"),
                    role=candidate.get("role"),
                    total_return=_markdown_value(metrics.get("total_return")),
                    oos_passed=_markdown_value(oos.get("validation_passed")),
                    oos_failed=_markdown_value(oos.get("validation_failed")),
                    edge_broken=_markdown_value(
                        cost.get("edge_broken_by_moderate_cost")
                    ),
                    sensitive=_markdown_value(
                        cost.get("returns_highly_cost_sensitive")
                    ),
                    classification=candidate.get("promotion_classification"),
                    rationale=candidate.get("promotion_rationale"),
                )
            )

    lines.extend(["", "## Operator Takeaways"])
    if isinstance(candidates, Iterable) and not isinstance(
        candidates,
        (str, bytes, Mapping),
    ):
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            lines.append(
                "- {candidate_id}: {takeaway}".format(
                    candidate_id=candidate.get("candidate_id"),
                    takeaway=candidate.get("operator_takeaway"),
                )
            )
    lines.append("")
    return "\n".join(lines)


def _strategy_review_candidate(
    result: Mapping[str, object],
    *,
    benchmark_available: bool,
) -> dict[str, object]:
    classification = str(result.get("promotion_classification", "reject"))
    reasons = [
        str(reason)
        for reason in result.get("promotion_reasons", [])
        if isinstance(reason, str)
    ]
    benchmark_comparison = (
        result.get("benchmark_buy_and_hold_comparison", {})
        if benchmark_available
        else {}
    )
    return {
        "symbol": result.get("symbol"),
        "candidate_id": result.get("candidate_id"),
        "role": result.get("role"),
        "strategy_family": result.get("strategy_family"),
        "strategy_hypothesis": _strategy_hypothesis(result),
        "metrics_summary": _metrics_summary(result),
        "oos_result": _review_out_of_sample_result(result),
        "cost_sensitivity_result": _review_cost_sensitivity_result(result),
        "baseline_comparison": result.get("benchmark_baseline_comparison", {}),
        "benchmark_comparison": benchmark_comparison,
        "promotion_classification": classification,
        "promotion_reasons": reasons,
        "promotion_rationale": _promotion_rationale(classification, reasons),
        "operator_takeaway": _operator_takeaway(classification, reasons),
        "cross_asset_promotion_gate": result.get("cross_asset_promotion_gate", {}),
        "limitations": list(result.get("limitations", _DEFAULT_LIMITATIONS)),
        "safety_labels": list(result.get("labels", STRATEGY_CHALLENGER_FACTORY_LABELS)),
    }


def _metrics_summary(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "metrics_status": result.get("metrics_status"),
        "total_return": result.get("total_return"),
        "annualized_return": result.get("annualized_return"),
        "max_drawdown": result.get("max_drawdown"),
        "sharpe_ratio": result.get("sharpe_ratio"),
        "transition_count": result.get("transition_count"),
        "exposure_percentage": result.get("exposure_percentage"),
        "evaluated_return_count": result.get("evaluated_return_count"),
        "data_availability_status": result.get("data_availability_status"),
        "data_refresh_status": result.get("data_refresh_status"),
        "oos_status": result.get("oos_status"),
        "cost_sensitivity_status": result.get("cost_sensitivity_status"),
    }


def _review_out_of_sample_result(result: Mapping[str, object]) -> dict[str, object]:
    summary = _mapping_or_empty(result.get("out_of_sample_validation"))
    return {
        "primary_window_id": summary.get("primary_window_id"),
        "window_count": summary.get("window_count"),
        "passed_window_count": summary.get("passed_window_count"),
        "failed_window_count": summary.get("failed_window_count"),
        "primary_window_passed": summary.get("primary_window_passed"),
        "primary_window_failed": summary.get("primary_window_failed"),
        "validation_passed": summary.get("validation_passed"),
        "validation_failed": summary.get("validation_failed"),
        "oos_status": result.get("oos_status"),
        "window_results": summary.get("window_results", []),
    }


def _review_cost_sensitivity_result(result: Mapping[str, object]) -> dict[str, object]:
    summary = _mapping_or_empty(result.get("cost_sensitivity_summary"))
    return {
        "zero_cost_total_return": summary.get("zero_cost_total_return"),
        "moderate_cost_total_return": summary.get("moderate_cost_total_return"),
        "zero_cost_baseline_total_return_delta": summary.get(
            "zero_cost_baseline_total_return_delta"
        ),
        "moderate_cost_baseline_total_return_delta": summary.get(
            "moderate_cost_baseline_total_return_delta"
        ),
        "moderate_cost_return_degradation": summary.get(
            "moderate_cost_return_degradation"
        ),
        "moderate_cost_edge_degradation": summary.get(
            "moderate_cost_edge_degradation"
        ),
        "edge_broken_by_moderate_cost": summary.get(
            "edge_broken_by_moderate_cost"
        ),
        "returns_highly_cost_sensitive": summary.get("returns_highly_cost_sensitive"),
        "cost_sensitivity_status": result.get("cost_sensitivity_status"),
    }


def _strategy_hypothesis(result: Mapping[str, object]) -> str:
    candidate_id = str(result.get("candidate_id", ""))
    family = str(result.get("strategy_family", ""))
    symbol = str(result.get("symbol", _DEFAULT_SYMBOL))
    fast_window = result.get("fast_window")
    slow_window = result.get("slow_window")
    if candidate_id == _BASELINE_CANDIDATE_ID:
        return (
            f"Operating baseline shape: long {symbol} when SMA 50 is above "
            "SMA 200, otherwise cash."
        )
    if candidate_id == _BUY_AND_HOLD_COMPARATOR_ID:
        return (
            f"Benchmark comparator: hold {symbol} continuously across the "
            "evaluated adjusted-close history."
        )
    if candidate_id == _CASH_RISK_OFF_COMPARATOR_ID:
        return "Comparator: current SMA 50/200 trend rule with explicit zero-return cash risk-off semantics."
    if family == "sma_crossover_long_only":
        return (
            f"Trend filter: long {symbol} when SMA {fast_window} is above "
            f"SMA {slow_window}, otherwise cash."
        )
    if family == "time_series_momentum_long_only":
        return (
            f"Time-series momentum: long {symbol} when adjusted close is above "
            f"its {slow_window}-bar lookback price, otherwise cash."
        )
    if family == "drawdown_filter_long_only":
        return (
            f"Drawdown risk-off filter: long {symbol} after {slow_window} bars "
            "unless price is at least 20 percent below the rolling high."
        )
    if family == _RELATIVE_MOMENTUM_FAMILY:
        basket_symbols = ", ".join(
            str(item) for item in result.get("basket_symbols", [])
        )
        top_n = result.get("top_n", 1)
        rebalance_rule = result.get("rebalance_rule", _REBALANCE_RULE_MONTHLY)
        cash_filter = (
            " with a positive absolute momentum cash filter"
            if result.get("risk_off_state") == _RELATIVE_MOMENTUM_CASH_FILTER_STATE
            else ""
        )
        return (
            f"ETF relative momentum basket: hold top {top_n} of "
            f"{basket_symbols} by {slow_window}-bar adjusted-close momentum, "
            f"rebalanced {rebalance_rule}{cash_filter}."
        )
    return (
        f"Deterministic {symbol} strategy candidate evaluated against the "
        "operating baseline shape."
    )


def _promotion_rationale(classification: str, reasons: Sequence[str]) -> str:
    reason_text = _reason_text(reasons)
    if classification == "reject":
        return f"Rejected because {reason_text}."
    if classification == "keep_researching":
        return f"Keep researching because {reason_text}."
    if classification == "preview_only":
        return f"Preview only because {reason_text}."
    if classification == "paper_candidate":
        return f"Paper candidate because {reason_text}; operator approval is still required."
    return f"{classification}: {reason_text}."


def _operator_takeaway(classification: str, reasons: Sequence[str]) -> str:
    reason_text = _reason_text(reasons)
    if classification == "reject":
        return f"Do not promote; evidence failed the gate on {reason_text}."
    if classification == "keep_researching":
        return f"Research-only follow-up; current evidence is limited by {reason_text}."
    if classification == "preview_only":
        return f"Preview only; review manually before any future promotion discussion because {reason_text}."
    if classification == "paper_candidate":
        return f"Candidate survived deterministic gates, but paper use still requires explicit operator approval because {reason_text}."
    return f"Treat as research-only until reviewed; rationale: {reason_text}."


def _reason_text(reasons: Sequence[str]) -> str:
    if not reasons:
        return "no explicit reason was emitted"
    return "; ".join(reason.replace("_", " ") for reason in reasons)


def _evaluate_symbol_candidate_set(
    config: StrategyChallengerFactoryConfig,
    *,
    symbol: str,
    data_sha256: str | None,
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    checked_symbol = _symbol(symbol)
    candidates = _candidates_for_symbol(config.candidates, checked_symbol)
    data_error: str | None = None
    data_quality_status = _DATA_QUALITY_VALID
    csv_result: LocalDailyBarsCsvResult | None = None
    validation_windows: tuple[dict[str, object], ...] = ()

    try:
        csv_result = load_local_daily_bars_csv(
            config.data_path,
            symbol=checked_symbol,
            as_of=config.as_of,
        )
    except ValidationError as exc:
        data_error = str(exc)
        data_quality_status = (
            _DATA_QUALITY_MISSING
            if not config.data_path.exists()
            else _DATA_QUALITY_MALFORMED
        )

    if csv_result is not None and csv_result.matching_symbol_row_count == 0:
        data_error = (
            f"missing_data for {checked_symbol}; "
            f"{_DATA_REFRESH_REQUIRED}"
        )
        data_quality_status = _DATA_QUALITY_MISSING
        csv_result = None

    if csv_result is None:
        results = tuple(
            _rejected_data_result(
                candidate,
                config=config,
                data_sha256=data_sha256,
                data_quality_status=data_quality_status,
                data_error=data_error or data_quality_status,
            )
            for candidate in candidates
        )
        symbol_record = _symbol_data_status_record(
            symbol=checked_symbol,
            data_quality_status=data_quality_status,
            data_error=data_error or data_quality_status,
            csv_result=None,
            validation_windows=(),
        )
        return results, symbol_record

    validation_windows = build_strategy_challenger_validation_windows(
        csv_result.usable_bars
    )
    symbol_config = _config_for_symbol(config, checked_symbol, candidates)
    results = _evaluate_candidates(
        csv_result,
        config=symbol_config,
        data_sha256=data_sha256,
        validation_windows=validation_windows,
    )
    symbol_record = _symbol_data_status_record(
        symbol=checked_symbol,
        data_quality_status=data_quality_status,
        data_error=None,
        csv_result=csv_result,
        validation_windows=validation_windows,
    )
    return results, symbol_record


def _symbol_data_status_record(
    *,
    symbol: str,
    data_quality_status: str,
    data_error: str | None,
    csv_result: LocalDailyBarsCsvResult | None,
    validation_windows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    missing = data_quality_status == _DATA_QUALITY_MISSING
    available = data_quality_status == _DATA_QUALITY_VALID
    return {
        "symbol": symbol,
        "data_quality_status": data_quality_status,
        "data_availability_status": (
            _DATA_AVAILABILITY_MISSING
            if missing
            else _DATA_AVAILABILITY_AVAILABLE
            if available
            else "unavailable"
        ),
        "data_refresh_status": (
            _DATA_REFRESH_REQUIRED if missing else _DATA_REFRESH_NOT_REQUIRED
        ),
        "data_error": data_error,
        "matching_symbol_row_count": (
            0 if csv_result is None else csv_result.matching_symbol_row_count
        ),
        "usable_bars": 0 if csv_result is None else len(csv_result.usable_bars),
        "ignored_wrong_symbol_row_count": (
            0 if csv_result is None else csv_result.ignored_wrong_symbol_row_count
        ),
        "ignored_future_bar_count": (
            0 if csv_result is None else csv_result.ignored_future_bar_count
        ),
        "validation_windows": list(validation_windows),
    }


def _config_for_symbol(
    config: StrategyChallengerFactoryConfig,
    symbol: str,
    candidates: tuple[StrategyChallengerCandidate, ...],
) -> StrategyChallengerFactoryConfig:
    return StrategyChallengerFactoryConfig(
        output_root=config.output_root,
        data_path=config.data_path,
        symbol=symbol,
        symbols=(symbol,),
        as_of=config.as_of,
        initial_equity=config.initial_equity,
        fee_bps=config.fee_bps,
        slippage_bps=config.slippage_bps,
        candidates=candidates,
    )


def _candidates_for_symbol(
    candidates: Iterable[StrategyChallengerCandidate],
    symbol: str,
) -> tuple[StrategyChallengerCandidate, ...]:
    checked_symbol = _symbol(symbol)
    return tuple(
        candidate
        if candidate.symbol == checked_symbol
        else StrategyChallengerCandidate(
            candidate_id=candidate.candidate_id,
            strategy_family=candidate.strategy_family,
            symbol=checked_symbol,
            timeframe=candidate.timeframe,
            fast_window=candidate.fast_window,
            slow_window=candidate.slow_window,
            role=candidate.role,
            risk_off_state=candidate.risk_off_state,
            basket_symbols=candidate.basket_symbols,
            top_n=candidate.top_n,
            rebalance_rule=candidate.rebalance_rule,
        )
        for candidate in candidates
        if not _is_basket_candidate(candidate)
    )


def _evaluate_candidates(
    csv_result: LocalDailyBarsCsvResult,
    *,
    config: StrategyChallengerFactoryConfig,
    data_sha256: str | None,
    validation_windows: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    usable_bars = csv_result.usable_bars
    if not usable_bars:
        return tuple(
            _insufficient_history_result(
                candidate,
                csv_result=csv_result,
                data_sha256=data_sha256,
                validation_windows=validation_windows,
            )
            for candidate in config.candidates
        )

    snapshot = _snapshot_from_local_bars(config.symbol, usable_bars)
    assumptions = DailyBacktestAssumptions(
        initial_equity=config.initial_equity,
        fee_bps=config.fee_bps,
        slippage_bps=config.slippage_bps,
    )
    raw_results: list[dict[str, object]] = []
    for candidate in config.candidates:
        raw_results.append(
            _evaluate_candidate(
                candidate,
                csv_result=csv_result,
                snapshot=snapshot,
                assumptions=assumptions,
                data_sha256=data_sha256,
                validation_windows=validation_windows,
            )
        )

    baseline = next(
        (
            result
            for result in raw_results
            if result["candidate_id"] == _BASELINE_CANDIDATE_ID
        ),
        None,
    )
    buy_and_hold = next(
        (
            result
            for result in raw_results
            if result["candidate_id"] == _BUY_AND_HOLD_COMPARATOR_ID
        ),
        None,
    )
    return _enrich_candidate_results(
        raw_results,
        baseline=baseline,
        buy_and_hold=buy_and_hold,
    )


def _enrich_candidate_results(
    raw_results: Iterable[Mapping[str, object]],
    *,
    baseline: Mapping[str, object] | None,
    buy_and_hold: Mapping[str, object] | None,
) -> tuple[dict[str, object], ...]:
    results: list[dict[str, object]] = []
    for result in raw_results:
        enriched = dict(result)
        enriched["benchmark_baseline_comparison"] = _baseline_comparison(
            enriched,
            baseline,
        )
        comparison = dict(enriched["benchmark_baseline_comparison"])  # type: ignore[arg-type]
        enriched["baseline_total_return_delta"] = comparison.get("total_return_delta")
        enriched["baseline_max_drawdown_delta"] = comparison.get("max_drawdown_delta")
        enriched["baseline_annualized_return_delta"] = comparison.get(
            "annualized_return_delta"
        )
        enriched["baseline_volatility_delta"] = comparison.get("volatility_delta")
        enriched["baseline_sharpe_ratio_delta"] = comparison.get("sharpe_ratio_delta")
        enriched["benchmark_buy_and_hold_comparison"] = _baseline_comparison(
            enriched,
            buy_and_hold,
            baseline_candidate_id=_BUY_AND_HOLD_COMPARATOR_ID,
        )
        benchmark_comparison = dict(enriched["benchmark_buy_and_hold_comparison"])  # type: ignore[arg-type]
        enriched["buy_and_hold_total_return_delta"] = benchmark_comparison.get(
            "total_return_delta"
        )
        enriched["buy_and_hold_max_drawdown_delta"] = benchmark_comparison.get(
            "max_drawdown_delta"
        )
        enriched["buy_and_hold_sharpe_ratio_delta"] = benchmark_comparison.get(
            "sharpe_ratio_delta"
        )
        _add_validation_window_baseline_comparisons(enriched, baseline)
        _add_cost_baseline_comparisons(enriched, baseline)
        enriched["out_of_sample_validation"] = _out_of_sample_validation_summary(
            enriched
        )
        enriched["cost_sensitivity_summary"] = _cost_sensitivity_summary(enriched)
        enriched["oos_status"] = _oos_status(enriched)
        enriched["cost_sensitivity_status"] = _cost_sensitivity_status(enriched)
        classification, reasons = classify_strategy_challenger_promotion(
            enriched,
            baseline,
        )
        enriched["promotion_classification"] = classification
        enriched["promotion_reasons"] = list(reasons)
        results.append(enriched)

    return tuple(results)


def _evaluate_basket_candidate_set(
    config: StrategyChallengerFactoryConfig,
    *,
    candidates: tuple[StrategyChallengerCandidate, ...],
    data_sha256: str | None,
) -> tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...]]:
    basket_symbols = _basket_required_symbols(candidates)
    csv_results, data_quality_status, data_error = _load_basket_csv_results(
        config,
        basket_symbols,
    )
    if data_quality_status != _DATA_QUALITY_VALID:
        return (
            tuple(
                _rejected_basket_data_result(
                    candidate,
                    config=config,
                    data_sha256=data_sha256,
                    data_quality_status=data_quality_status,
                    data_error=data_error or data_quality_status,
                )
                for candidate in candidates
            ),
            (),
        )

    bars_by_symbol = _common_calendar_bars(csv_results, basket_symbols)
    if not bars_by_symbol:
        return (
            tuple(
                _rejected_basket_data_result(
                    candidate,
                    config=config,
                    data_sha256=data_sha256,
                    data_quality_status=_DATA_QUALITY_MISSING,
                    data_error="no common ETF basket calendar after as-of filtering",
                )
                for candidate in candidates
            ),
            (),
        )

    representative_symbol = (
        config.symbol if config.symbol in bars_by_symbol else basket_symbols[0]
    )
    validation_windows = build_strategy_challenger_validation_windows(
        bars_by_symbol[representative_symbol]
    )
    baseline, buy_and_hold = _aligned_basket_baselines(
        config,
        data_sha256=data_sha256,
        bars_by_symbol=bars_by_symbol,
        source_results=csv_results,
        validation_windows=validation_windows,
    )
    raw_results = tuple(
        _evaluate_basket_candidate(
            candidate,
            config=config,
            bars_by_symbol=bars_by_symbol,
            source_results=csv_results,
            data_sha256=data_sha256,
            validation_windows=validation_windows,
        )
        for candidate in candidates
    )
    return (
        _enrich_candidate_results(
            raw_results,
            baseline=baseline,
            buy_and_hold=buy_and_hold,
        ),
        validation_windows,
    )


def _evaluate_basket_candidate(
    candidate: StrategyChallengerCandidate,
    *,
    config: StrategyChallengerFactoryConfig,
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
    source_results: Mapping[str, LocalDailyBarsCsvResult],
    data_sha256: str | None,
    validation_windows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    base = _basket_candidate_base_result(
        candidate,
        config=config,
        bars_by_symbol=bars_by_symbol,
        source_results=source_results,
        data_sha256=data_sha256,
        validation_windows=validation_windows,
    )
    common_bar_count = _basket_common_bar_count(bars_by_symbol)
    if common_bar_count < candidate.slow_window:
        base.update(
            {
                "metrics_status": "rejected_insufficient_history",
                "promotion_classification": "reject",
                "promotion_reasons": ["insufficient_history_for_candidate_slow_window"],
                "blockers": ["insufficient_history"],
                "scheduled_rebalance_dates": [],
                "rebalance_dates": [],
                "rebalance_count": 0,
                "rebalance_allocations": [],
                "limitations": list(
                    _limitations_with(
                        f"requires at least {candidate.slow_window} common ETF basket bars",
                    )
                ),
            }
        )
        return _with_empty_metrics(base)

    assumptions = DailyBacktestAssumptions(
        initial_equity=config.initial_equity,
        fee_bps=config.fee_bps,
        slippage_bps=config.slippage_bps,
    )
    backtest = _run_relative_momentum_basket_backtest(
        candidate,
        bars_by_symbol=bars_by_symbol,
        assumptions=assumptions,
    )
    metrics = _metrics_from_basket_backtest(backtest, initial_equity=config.initial_equity)
    window_metrics = _basket_validation_window_metrics(
        backtest,
        validation_windows,
        initial_equity=config.initial_equity,
    )
    full_sample_metrics = _window_metrics_by_id(
        window_metrics,
        _FULL_SAMPLE_WINDOW_ID,
    )
    out_of_sample_metrics = _out_of_sample_metrics(window_metrics)
    cost_adjusted_metrics = _basket_cost_adjusted_metrics(
        candidate,
        bars_by_symbol=bars_by_symbol,
        validation_windows=validation_windows,
        initial_equity=config.initial_equity,
    )
    base.update(metrics)
    base.update(
        {
            "metrics_status": "valid",
            "blockers": [],
            "limitations": list(
                _limitations_with(
                    "relative momentum allocates across the approved ETF basket on a common adjusted-close calendar",
                    "rebalance decisions are deterministic and monthly",
                    "paper promotion is explicitly forbidden in v2.16",
                )
            ),
            "scheduled_rebalance_dates": [
                item.isoformat() for item in backtest.scheduled_rebalance_dates
            ],
            "rebalance_dates": [item.isoformat() for item in backtest.rebalance_dates],
            "rebalance_count": len(backtest.rebalance_dates),
            "rebalance_allocations": list(backtest.rebalance_allocations),
            "full_sample_metrics": full_sample_metrics,
            "validation_window_metrics": list(window_metrics),
            "out_of_sample_metrics": out_of_sample_metrics,
            "cost_adjusted_metrics": list(cost_adjusted_metrics),
            "cost_sensitivity_summary": _empty_cost_sensitivity_summary(),
            "out_of_sample_validation": _empty_out_of_sample_validation_summary(),
            "promotion_classification": "keep_researching",
            "promotion_reasons": [],
        }
    )
    return base


def _evaluate_candidate(
    candidate: StrategyChallengerCandidate,
    *,
    csv_result: LocalDailyBarsCsvResult,
    snapshot: HistoricalPriceSnapshot,
    assumptions: DailyBacktestAssumptions,
    data_sha256: str | None,
    validation_windows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    usable_bars = csv_result.usable_bars
    base = _candidate_base_result(
        candidate,
        csv_result=csv_result,
        data_sha256=data_sha256,
        validation_windows=validation_windows,
    )
    if len(usable_bars) < candidate.slow_window:
        return _insufficient_history_result(
            candidate,
            csv_result=csv_result,
            data_sha256=data_sha256,
            validation_windows=validation_windows,
        )

    exposures = _candidate_exposures(usable_bars, candidate)
    result = run_daily_backtest(snapshot, exposures, assumptions)
    metrics = _metrics_from_backtest(result, exposures)
    window_metrics = _validation_window_metrics(
        result.points,
        exposures,
        validation_windows,
        initial_equity=assumptions.initial_equity,
    )
    full_sample_metrics = _window_metrics_by_id(
        window_metrics,
        _FULL_SAMPLE_WINDOW_ID,
    )
    out_of_sample_metrics = _out_of_sample_metrics(window_metrics)
    cost_adjusted_metrics = _cost_adjusted_metrics(
        snapshot,
        exposures,
        validation_windows,
        initial_equity=assumptions.initial_equity,
    )
    base.update(metrics)
    base.update(
        {
            "metrics_status": "valid",
            "blockers": [],
            "limitations": list(_DEFAULT_LIMITATIONS),
            "full_sample_metrics": full_sample_metrics,
            "validation_window_metrics": list(window_metrics),
            "out_of_sample_metrics": out_of_sample_metrics,
            "cost_adjusted_metrics": list(cost_adjusted_metrics),
            "cost_sensitivity_summary": _empty_cost_sensitivity_summary(),
            "out_of_sample_validation": _empty_out_of_sample_validation_summary(),
            "promotion_classification": "keep_researching",
            "promotion_reasons": [],
        }
    )
    return base


def _basket_candidate_base_result(
    candidate: StrategyChallengerCandidate,
    *,
    config: StrategyChallengerFactoryConfig,
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
    source_results: Mapping[str, LocalDailyBarsCsvResult],
    data_sha256: str | None,
    validation_windows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    common_bar_count = _basket_common_bar_count(bars_by_symbol)
    dates = _basket_common_dates(bars_by_symbol)
    return {
        "record_type": "strategy_challenger_result",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "previous_factory_id": _PREVIOUS_FACTORY_ID,
        "candidate_id": candidate.candidate_id,
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "strategy_family": candidate.strategy_family,
        "strategy_hypothesis": _strategy_hypothesis(candidate.to_dict()),
        "symbol": candidate.symbol,
        "timeframe": candidate.timeframe,
        "role": candidate.role,
        "fast_window": candidate.fast_window,
        "slow_window": candidate.slow_window,
        "risk_off_state": candidate.risk_off_state,
        **_basket_result_metadata(candidate),
        "data_path": str(config.data_path),
        "data_sha256": data_sha256,
        "data_quality_status": _DATA_QUALITY_VALID,
        "data_availability_status": _DATA_AVAILABILITY_AVAILABLE,
        "data_refresh_status": _DATA_REFRESH_NOT_REQUIRED,
        "as_of_start": dates[0].isoformat() if dates else None,
        "as_of_end": dates[-1].isoformat() if dates else None,
        "total_bars": common_bar_count,
        "usable_bars": common_bar_count,
        "source_total_rows": sum(
            result.total_row_count for result in source_results.values()
        ),
        "ignored_wrong_symbol_row_count": sum(
            result.ignored_wrong_symbol_row_count for result in source_results.values()
        ),
        "ignored_future_bar_count": sum(
            result.ignored_future_bar_count for result in source_results.values()
        ),
        "required_history_bars": candidate.slow_window,
        "validation_window_method": _VALIDATION_WINDOW_METHOD,
        "validation_windows_evaluated": [
            str(window["window_id"]) for window in validation_windows
        ],
        "cost_assumptions_evaluated": [
            str(assumption["cost_id"]) for assumption in _cost_assumption_records()
        ],
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "safety": _safety_payload(),
    }


def _rejected_basket_data_result(
    candidate: StrategyChallengerCandidate,
    *,
    config: StrategyChallengerFactoryConfig,
    data_sha256: str | None,
    data_quality_status: str,
    data_error: str,
) -> dict[str, object]:
    result = _rejected_data_result(
        candidate,
        config=config,
        data_sha256=data_sha256,
        data_quality_status=data_quality_status,
        data_error=data_error,
    )
    result.update(
        {
            **_basket_result_metadata(candidate),
            "scheduled_rebalance_dates": [],
            "rebalance_dates": [],
            "rebalance_count": 0,
            "rebalance_allocations": [],
        }
    )
    return result


def _load_basket_csv_results(
    config: StrategyChallengerFactoryConfig,
    basket_symbols: tuple[str, ...],
) -> tuple[dict[str, LocalDailyBarsCsvResult], str, str | None]:
    results: dict[str, LocalDailyBarsCsvResult] = {}
    missing_symbols: list[str] = []
    for symbol in basket_symbols:
        try:
            result = load_local_daily_bars_csv(
                config.data_path,
                symbol=symbol,
                as_of=config.as_of,
            )
        except ValidationError as exc:
            status = (
                _DATA_QUALITY_MISSING
                if not config.data_path.exists()
                else _DATA_QUALITY_MALFORMED
            )
            return {}, status, str(exc)
        if not result.usable_bars:
            missing_symbols.append(symbol)
        results[symbol] = result

    if missing_symbols:
        return (
            results,
            _DATA_QUALITY_MISSING,
            "missing usable local daily bars for ETF basket symbols: "
            + ", ".join(missing_symbols),
        )
    return results, _DATA_QUALITY_VALID, None


def _common_calendar_bars(
    csv_results: Mapping[str, LocalDailyBarsCsvResult],
    basket_symbols: tuple[str, ...],
) -> dict[str, tuple[LocalDailyBar, ...]]:
    if not basket_symbols:
        return {}
    date_sets = [
        {bar.date for bar in csv_results[symbol].usable_bars}
        for symbol in basket_symbols
        if symbol in csv_results
    ]
    if len(date_sets) != len(basket_symbols):
        return {}
    common_dates = sorted(set.intersection(*date_sets))
    if not common_dates:
        return {}
    aligned: dict[str, tuple[LocalDailyBar, ...]] = {}
    for symbol in basket_symbols:
        bars_by_date = {bar.date: bar for bar in csv_results[symbol].usable_bars}
        aligned[symbol] = tuple(bars_by_date[on_date] for on_date in common_dates)
    return aligned


def _aligned_basket_baselines(
    config: StrategyChallengerFactoryConfig,
    *,
    data_sha256: str | None,
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
    source_results: Mapping[str, LocalDailyBarsCsvResult],
    validation_windows: tuple[dict[str, object], ...],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    operating_bars = bars_by_symbol.get(config.symbol)
    source_result = source_results.get(config.symbol)
    if operating_bars is None or source_result is None:
        return None, None
    baseline_candidates = tuple(
        candidate
        for candidate in _candidates_for_symbol(config.candidates, config.symbol)
        if candidate.candidate_id in {_BASELINE_CANDIDATE_ID, _BUY_AND_HOLD_COMPARATOR_ID}
    )
    if not baseline_candidates:
        return None, None
    aligned_csv_result = _csv_result_with_usable_bars(source_result, operating_bars)
    baseline_config = _config_for_symbol(config, config.symbol, baseline_candidates)
    results = _evaluate_candidates(
        aligned_csv_result,
        config=baseline_config,
        data_sha256=data_sha256,
        validation_windows=validation_windows,
    )
    baseline = next(
        (
            result
            for result in results
            if result.get("candidate_id") == _BASELINE_CANDIDATE_ID
        ),
        None,
    )
    buy_and_hold = next(
        (
            result
            for result in results
            if result.get("candidate_id") == _BUY_AND_HOLD_COMPARATOR_ID
        ),
        None,
    )
    return baseline, buy_and_hold


def _csv_result_with_usable_bars(
    source: LocalDailyBarsCsvResult,
    bars: tuple[LocalDailyBar, ...],
) -> LocalDailyBarsCsvResult:
    return LocalDailyBarsCsvResult(
        path=source.path,
        symbol=source.symbol,
        as_of_date=source.as_of_date,
        bars=bars,
        usable_bars=bars,
        total_row_count=len(bars),
        matching_symbol_row_count=len(bars),
        ignored_wrong_symbol_row_count=0,
        ignored_future_bar_count=0,
        input_sorted_by_date=True,
    )


def _run_relative_momentum_basket_backtest(
    candidate: StrategyChallengerCandidate,
    *,
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
    assumptions: DailyBacktestAssumptions,
) -> _BasketBacktest:
    if candidate.strategy_family != _RELATIVE_MOMENTUM_FAMILY:
        raise ValidationError(f"unsupported basket strategy_family: {candidate.strategy_family}")
    basket_symbols = candidate.basket_symbols
    dates = _basket_common_dates(bars_by_symbol)
    prices_by_symbol = {
        symbol: tuple(bar.adjusted_close for bar in bars_by_symbol[symbol])
        for symbol in basket_symbols
    }
    cost_rate = (assumptions.fee_bps + assumptions.slippage_bps) / Decimal("10000")
    current_weights = {symbol: _ZERO for symbol in basket_symbols}
    equity = assumptions.initial_equity
    synthetic_price = Decimal("100")
    points: list[DailyBacktestPoint] = []
    exposures: list[DailyExposure] = []
    allocation_turnovers: list[Decimal] = []
    scheduled_rebalance_dates: list[date] = []
    rebalance_dates: list[date] = []
    rebalance_allocations: list[dict[str, object]] = []

    for index, on_date in enumerate(dates):
        target_weights = current_weights
        if _is_rebalance_index(dates, index, candidate.rebalance_rule):
            if index >= candidate.slow_window:
                scheduled_rebalance_dates.append(on_date)
            target_weights = _relative_momentum_target_weights(
                candidate,
                prices_by_symbol=prices_by_symbol,
                index=index,
            )

        asset_return = _ZERO
        if index > 0:
            for symbol in basket_symbols:
                previous_price = prices_by_symbol[symbol][index - 1]
                current_price = prices_by_symbol[symbol][index]
                asset_return += current_weights[symbol] * (
                    (current_price / previous_price) - _ONE
                )

        turnover = sum(
            abs(target_weights[symbol] - current_weights[symbol])
            for symbol in basket_symbols
        )
        transaction_cost = turnover * cost_rate
        strategy_return_after_costs = asset_return - transaction_cost
        equity = equity * (_ONE + strategy_return_after_costs)
        synthetic_price = synthetic_price * (_ONE + asset_return)
        if synthetic_price <= _ZERO or equity <= _ZERO:
            raise ValidationError("basket backtest equity path became non-positive.")

        exposure = sum(target_weights.values(), _ZERO)
        points.append(
            DailyBacktestPoint(
                date=on_date,
                adjusted_close=synthetic_price,
                exposure=exposure,
                asset_return=asset_return,
                strategy_return_before_costs=asset_return,
                transaction_cost=transaction_cost,
                strategy_return_after_costs=strategy_return_after_costs,
                equity=equity,
            )
        )
        exposures.append(DailyExposure(date=on_date, exposure=exposure))
        allocation_turnovers.append(turnover)
        if turnover != _ZERO:
            rebalance_dates.append(on_date)
            rebalance_allocations.append(
                _rebalance_allocation_record(on_date, target_weights)
            )
        current_weights = target_weights

    return _BasketBacktest(
        points=tuple(points),
        exposures=tuple(exposures),
        allocation_turnovers=tuple(allocation_turnovers),
        scheduled_rebalance_dates=tuple(scheduled_rebalance_dates),
        rebalance_dates=tuple(rebalance_dates),
        rebalance_allocations=tuple(rebalance_allocations),
    )


def _relative_momentum_target_weights(
    candidate: StrategyChallengerCandidate,
    *,
    prices_by_symbol: Mapping[str, tuple[Decimal, ...]],
    index: int,
) -> dict[str, Decimal]:
    basket_symbols = candidate.basket_symbols
    zero_weights = {symbol: _ZERO for symbol in basket_symbols}
    if index < candidate.slow_window:
        return zero_weights

    ranked = sorted(
        (
            (
                symbol,
                (prices_by_symbol[symbol][index] / prices_by_symbol[symbol][index - candidate.slow_window])
                - _ONE,
            )
            for symbol in basket_symbols
        ),
        key=lambda item: (-item[1], item[0]),
    )
    if (
        candidate.risk_off_state == _RELATIVE_MOMENTUM_CASH_FILTER_STATE
        and ranked
        and ranked[0][1] <= _ZERO
    ):
        return zero_weights
    selected = tuple(symbol for symbol, _momentum in ranked[: candidate.top_n])
    if not selected:
        return zero_weights
    weight = _ONE / Decimal(len(selected))
    return {
        symbol: weight if symbol in selected else _ZERO
        for symbol in basket_symbols
    }


def _metrics_from_basket_backtest(
    backtest: _BasketBacktest,
    *,
    initial_equity: Decimal,
) -> dict[str, object]:
    metrics = _metrics_from_backtest_points(
        backtest.points,
        backtest.exposures,
        initial_equity=initial_equity,
        previous_exposure=_ZERO,
        include_first_return=False,
    )
    _override_basket_turnover_metrics(
        metrics,
        backtest.allocation_turnovers,
    )
    return metrics


def _basket_validation_window_metrics(
    backtest: _BasketBacktest,
    validation_windows: tuple[dict[str, object], ...],
    *,
    initial_equity: Decimal,
) -> tuple[dict[str, object], ...]:
    metrics = [
        dict(metric)
        for metric in _validation_window_metrics(
            backtest.points,
            backtest.exposures,
            validation_windows,
            initial_equity=initial_equity,
        )
    ]
    for metric in metrics:
        start_index = _int_from_mapping(metric, "start_index")
        end_index = _int_from_mapping(metric, "end_index_exclusive")
        _override_basket_turnover_metrics(
            metric,
            backtest.allocation_turnovers[start_index:end_index],
        )
    return tuple(metrics)


def _basket_cost_adjusted_metrics(
    candidate: StrategyChallengerCandidate,
    *,
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
    validation_windows: tuple[dict[str, object], ...],
    initial_equity: Decimal,
) -> tuple[dict[str, object], ...]:
    metrics: list[dict[str, object]] = []
    for assumption in _default_cost_assumptions():
        backtest = _run_relative_momentum_basket_backtest(
            candidate,
            bars_by_symbol=bars_by_symbol,
            assumptions=DailyBacktestAssumptions(
                initial_equity=initial_equity,
                fee_bps=assumption.fee_bps,
                slippage_bps=assumption.slippage_bps,
            ),
        )
        window_metrics = _basket_validation_window_metrics(
            backtest,
            validation_windows,
            initial_equity=initial_equity,
        )
        metrics.append(
            {
                **assumption.to_dict(),
                "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
                "full_sample_metrics": _window_metrics_by_id(
                    window_metrics,
                    _FULL_SAMPLE_WINDOW_ID,
                ),
                "out_of_sample_metrics": _out_of_sample_metrics(window_metrics),
                "window_metrics": list(window_metrics),
            }
        )
    return tuple(metrics)


def _candidate_base_result(
    candidate: StrategyChallengerCandidate,
    *,
    csv_result: LocalDailyBarsCsvResult,
    data_sha256: str | None,
    validation_windows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    usable = csv_result.usable_bars
    return {
        "record_type": "strategy_challenger_result",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "previous_factory_id": _PREVIOUS_FACTORY_ID,
        "candidate_id": candidate.candidate_id,
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "strategy_family": candidate.strategy_family,
        "strategy_hypothesis": _strategy_hypothesis(candidate.to_dict()),
        "symbol": candidate.symbol,
        "timeframe": candidate.timeframe,
        "role": candidate.role,
        "fast_window": candidate.fast_window,
        "slow_window": candidate.slow_window,
        "risk_off_state": candidate.risk_off_state,
        "data_path": str(csv_result.path),
        "data_sha256": data_sha256,
        "data_quality_status": _DATA_QUALITY_VALID,
        "data_availability_status": _DATA_AVAILABILITY_AVAILABLE,
        "data_refresh_status": _DATA_REFRESH_NOT_REQUIRED,
        "as_of_start": usable[0].date.isoformat() if usable else None,
        "as_of_end": usable[-1].date.isoformat() if usable else None,
        "total_bars": csv_result.matching_symbol_row_count,
        "usable_bars": len(usable),
        "source_total_rows": csv_result.total_row_count,
        "ignored_wrong_symbol_row_count": csv_result.ignored_wrong_symbol_row_count,
        "ignored_future_bar_count": csv_result.ignored_future_bar_count,
        "required_history_bars": candidate.slow_window,
        "validation_window_method": _VALIDATION_WINDOW_METHOD,
        "validation_windows_evaluated": [
            str(window["window_id"]) for window in validation_windows
        ],
        "cost_assumptions_evaluated": [
            str(assumption["cost_id"]) for assumption in _cost_assumption_records()
        ],
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "safety": _safety_payload(),
    }


def _insufficient_history_result(
    candidate: StrategyChallengerCandidate,
    *,
    csv_result: LocalDailyBarsCsvResult,
    data_sha256: str | None,
    validation_windows: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    base = _candidate_base_result(
        candidate,
        csv_result=csv_result,
        data_sha256=data_sha256,
        validation_windows=validation_windows,
    )
    base.update(
        {
            "metrics_status": "rejected_insufficient_history",
            "promotion_classification": "reject",
            "promotion_reasons": ["insufficient_history_for_candidate_slow_window"],
            "blockers": ["insufficient_history"],
            "limitations": list(
                _limitations_with(
                    f"requires at least {candidate.slow_window} usable bars",
                )
            ),
        }
    )
    return _with_empty_metrics(base)


def _rejected_data_result(
    candidate: StrategyChallengerCandidate,
    *,
    config: StrategyChallengerFactoryConfig,
    data_sha256: str | None,
    data_quality_status: str,
    data_error: str,
) -> dict[str, object]:
    missing = data_quality_status == _DATA_QUALITY_MISSING
    base = {
        "record_type": "strategy_challenger_result",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "previous_factory_id": _PREVIOUS_FACTORY_ID,
        "candidate_id": candidate.candidate_id,
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "strategy_family": candidate.strategy_family,
        "strategy_hypothesis": _strategy_hypothesis(candidate.to_dict()),
        "symbol": candidate.symbol,
        "timeframe": candidate.timeframe,
        "role": candidate.role,
        "fast_window": candidate.fast_window,
        "slow_window": candidate.slow_window,
        "risk_off_state": candidate.risk_off_state,
        "data_path": str(config.data_path),
        "data_sha256": data_sha256,
        "data_quality_status": data_quality_status,
        "data_availability_status": (
            _DATA_AVAILABILITY_MISSING if missing else "unavailable"
        ),
        "data_refresh_status": (
            _DATA_REFRESH_REQUIRED if missing else _DATA_REFRESH_NOT_REQUIRED
        ),
        "data_error": data_error,
        "as_of_start": None,
        "as_of_end": None,
        "total_bars": 0,
        "usable_bars": 0,
        "source_total_rows": 0,
        "ignored_wrong_symbol_row_count": 0,
        "ignored_future_bar_count": 0,
        "required_history_bars": candidate.slow_window,
        "metrics_status": "rejected_missing_data" if missing else "rejected_data_invalid",
        "promotion_classification": "reject",
        "promotion_reasons": (
            [_DATA_AVAILABILITY_MISSING, _DATA_REFRESH_REQUIRED]
            if missing
            else ["malformed_or_missing_data"]
        ),
        "blockers": [data_quality_status],
        "benchmark_baseline_comparison": _empty_baseline_comparison(),
        "validation_window_method": _VALIDATION_WINDOW_METHOD,
        "validation_windows_evaluated": [],
        "cost_assumptions_evaluated": [],
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "limitations": list(_limitations_with(data_error)),
        "safety": _safety_payload(),
    }
    return _with_empty_metrics(base)


def _with_empty_metrics(base: dict[str, object]) -> dict[str, object]:
    metrics = {
        "starting_equity": None,
        "ending_equity": None,
        "total_return": None,
        "annualized_return": None,
        "cagr": None,
        "max_drawdown": None,
        "annualized_volatility": None,
        "volatility": None,
        "sharpe_ratio": None,
        "risk_adjusted_score": None,
        "trade_count": 0,
        "transition_count": 0,
        "exposure_percentage": "0",
        "evaluated_return_count": 0,
        "benchmark_baseline_comparison": _empty_baseline_comparison(),
        "benchmark_buy_and_hold_comparison": _empty_baseline_comparison(
            baseline_candidate_id=_BUY_AND_HOLD_COMPARATOR_ID
        ),
        "baseline_total_return_delta": None,
        "baseline_max_drawdown_delta": None,
        "baseline_annualized_return_delta": None,
        "baseline_volatility_delta": None,
        "baseline_sharpe_ratio_delta": None,
        "buy_and_hold_total_return_delta": None,
        "buy_and_hold_max_drawdown_delta": None,
        "buy_and_hold_sharpe_ratio_delta": None,
        "full_sample_metrics": None,
        "validation_window_metrics": [],
        "out_of_sample_metrics": {
            "primary_window_id": _LATER_TEST_WINDOW_ID,
            "windows": [],
        },
        "out_of_sample_validation": _empty_out_of_sample_validation_summary(),
        "oos_status": "not_evaluable",
        "cost_adjusted_metrics": [],
        "cost_sensitivity_summary": _empty_cost_sensitivity_summary(),
        "cost_sensitivity_status": "not_evaluable",
    }
    result = dict(base)
    result.update(metrics)
    return result


def _metrics_from_backtest(
    result: DailyBacktestResult,
    exposures: tuple[DailyExposure, ...],
) -> dict[str, object]:
    daily_returns = tuple(point.strategy_return_after_costs for point in result.points[1:])
    annualized_return = _annualized_return(
        result.total_return,
        result.points[0].date,
        result.points[-1].date,
    )
    volatility = _annualized_volatility(daily_returns)
    sharpe = _sharpe_like_score(annualized_return, volatility)
    transition_count = _transition_count(exposures)
    exposure_percentage = result.exposure_ratio * Decimal("100")
    return {
        "starting_equity": _decimal_text(result.starting_equity),
        "ending_equity": _decimal_text(result.ending_equity),
        "total_return": _decimal_text(result.total_return),
        "annualized_return": _optional_decimal_text(annualized_return),
        "cagr": _optional_decimal_text(annualized_return),
        "max_drawdown": _decimal_text(result.max_drawdown),
        "annualized_volatility": _optional_decimal_text(volatility),
        "volatility": _optional_decimal_text(volatility),
        "sharpe_ratio": _optional_decimal_text(sharpe),
        "risk_adjusted_score": _optional_decimal_text(sharpe),
        "trade_count": transition_count,
        "transition_count": transition_count,
        "turnover": _decimal_text(result.turnover),
        "exposure_percentage": _decimal_text(exposure_percentage),
        "evaluated_return_count": len(daily_returns),
    }


def _default_cost_assumptions() -> tuple[StrategyChallengerCostAssumption, ...]:
    return (
        StrategyChallengerCostAssumption(
            cost_id=_ZERO_COST_ID,
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
            description="Zero transaction-cost reference case.",
        ),
        StrategyChallengerCostAssumption(
            cost_id=_LOW_COST_ID,
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("1"),
            description="Low friction case: 1 basis point per full exposure transition.",
        ),
        StrategyChallengerCostAssumption(
            cost_id=_MODERATE_COST_ID,
            fee_bps=Decimal("1"),
            slippage_bps=Decimal("4"),
            description="Moderate friction case: 5 basis points per full exposure transition.",
        ),
    )


def _cost_assumption_records() -> tuple[dict[str, object], ...]:
    return tuple(assumption.to_dict() for assumption in _default_cost_assumptions())


def _build_validation_window_specs(
    bar_count: int,
) -> tuple[StrategyChallengerValidationWindow, ...]:
    checked_count = _positive_int(bar_count, "bar_count")
    windows: list[StrategyChallengerValidationWindow] = [
        StrategyChallengerValidationWindow(
            window_id=_FULL_SAMPLE_WINDOW_ID,
            window_role="full_sample",
            start_index=0,
            end_index_exclusive=checked_count,
        )
    ]

    half_split = checked_count // 2
    if 0 < half_split < checked_count:
        windows.extend(
            (
                StrategyChallengerValidationWindow(
                    window_id=_EARLY_TRAIN_WINDOW_ID,
                    window_role="train",
                    start_index=0,
                    end_index_exclusive=half_split,
                ),
                StrategyChallengerValidationWindow(
                    window_id=_LATER_TEST_WINDOW_ID,
                    window_role="out_of_sample",
                    start_index=half_split,
                    end_index_exclusive=checked_count,
                ),
            )
        )

    previous_end: int | None = None
    for fold_index in range(3):
        start_index = (checked_count * fold_index) // 3
        end_index = (checked_count * (fold_index + 1)) // 3
        if end_index <= start_index:
            continue
        if previous_end is not None and start_index < previous_end:
            raise ValidationError("walk-forward windows must be chronological.")
        windows.append(
            StrategyChallengerValidationWindow(
                window_id=f"walk_forward_{fold_index + 1}",
                window_role="walk_forward",
                start_index=start_index,
                end_index_exclusive=end_index,
            )
        )
        previous_end = end_index

    return tuple(windows)


def _validation_window_metrics(
    points: tuple[DailyBacktestPoint, ...],
    exposures: tuple[DailyExposure, ...],
    validation_windows: tuple[dict[str, object], ...],
    *,
    initial_equity: Decimal,
) -> tuple[dict[str, object], ...]:
    if len(points) != len(exposures):
        raise ValidationError("backtest points and exposures must align.")

    metrics: list[dict[str, object]] = []
    for window in validation_windows:
        start_index = _int_from_mapping(window, "start_index")
        end_index = _int_from_mapping(window, "end_index_exclusive")
        if start_index < 0 or end_index > len(points) or start_index >= end_index:
            raise ValidationError("validation window indices are out of bounds.")
        previous_exposure = (
            _ZERO if start_index == 0 else exposures[start_index - 1].exposure
        )
        window_metrics = _metrics_from_backtest_points(
            points[start_index:end_index],
            exposures[start_index:end_index],
            initial_equity=initial_equity,
            previous_exposure=previous_exposure,
            include_first_return=start_index > 0,
        )
        window_metrics.update(
            {
                "window_id": str(window["window_id"]),
                "window_role": str(window["window_role"]),
                "start_index": start_index,
                "end_index_exclusive": end_index,
                "bar_count": _int_from_mapping(window, "bar_count"),
                "as_of_start": str(window["as_of_start"]),
                "as_of_end": str(window["as_of_end"]),
            }
        )
        metrics.append(window_metrics)

    return tuple(metrics)


def _metrics_from_backtest_points(
    points: tuple[DailyBacktestPoint, ...],
    exposures: tuple[DailyExposure, ...],
    *,
    initial_equity: Decimal,
    previous_exposure: Decimal,
    include_first_return: bool,
) -> dict[str, object]:
    if not points:
        raise ValidationError("window points must not be empty.")
    if len(points) != len(exposures):
        raise ValidationError("window points and exposures must align.")

    equity = initial_equity
    peak = equity
    worst_drawdown = _ZERO
    daily_returns: list[Decimal] = []
    turnover = _ZERO
    transition_count = 0
    exposure_sum = _ZERO
    prior_exposure = previous_exposure

    for index, point in enumerate(points):
        if include_first_return or index > 0:
            daily_returns.append(point.strategy_return_after_costs)
        equity = equity * (_ONE + point.strategy_return_after_costs)
        if equity > peak:
            peak = equity
        drawdown = (equity / peak) - _ONE
        if drawdown < worst_drawdown:
            worst_drawdown = drawdown

        exposure = exposures[index].exposure
        exposure_delta = abs(exposure - prior_exposure)
        turnover += exposure_delta
        if exposure_delta != _ZERO:
            transition_count += 1
        exposure_sum += exposure
        prior_exposure = exposure

    total_return = (equity / initial_equity) - _ONE
    annualized_return = _annualized_return(
        total_return,
        points[0].date,
        points[-1].date,
    )
    volatility = _annualized_volatility(tuple(daily_returns))
    sharpe = _sharpe_like_score(annualized_return, volatility)
    exposure_percentage = (exposure_sum / Decimal(len(exposures))) * Decimal("100")

    return {
        "metrics_status": "valid",
        "starting_equity": _decimal_text(initial_equity),
        "ending_equity": _decimal_text(equity),
        "total_return": _decimal_text(total_return),
        "annualized_return": _optional_decimal_text(annualized_return),
        "cagr": _optional_decimal_text(annualized_return),
        "max_drawdown": _decimal_text(-worst_drawdown),
        "annualized_volatility": _optional_decimal_text(volatility),
        "volatility": _optional_decimal_text(volatility),
        "sharpe_ratio": _optional_decimal_text(sharpe),
        "risk_adjusted_score": _optional_decimal_text(sharpe),
        "trade_count": transition_count,
        "transition_count": transition_count,
        "turnover": _decimal_text(turnover),
        "exposure_percentage": _decimal_text(exposure_percentage),
        "evaluated_return_count": len(daily_returns),
    }


def _cost_adjusted_metrics(
    snapshot: HistoricalPriceSnapshot,
    exposures: tuple[DailyExposure, ...],
    validation_windows: tuple[dict[str, object], ...],
    *,
    initial_equity: Decimal,
) -> tuple[dict[str, object], ...]:
    metrics: list[dict[str, object]] = []
    for assumption in _default_cost_assumptions():
        backtest = run_daily_backtest(
            snapshot,
            exposures,
            DailyBacktestAssumptions(
                initial_equity=initial_equity,
                fee_bps=assumption.fee_bps,
                slippage_bps=assumption.slippage_bps,
            ),
        )
        window_metrics = _validation_window_metrics(
            backtest.points,
            exposures,
            validation_windows,
            initial_equity=initial_equity,
        )
        metrics.append(
            {
                **assumption.to_dict(),
                "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
                "full_sample_metrics": _window_metrics_by_id(
                    window_metrics,
                    _FULL_SAMPLE_WINDOW_ID,
                ),
                "out_of_sample_metrics": _out_of_sample_metrics(window_metrics),
                "window_metrics": list(window_metrics),
            }
        )
    return tuple(metrics)


def _window_metrics_by_id(
    metrics: Iterable[Mapping[str, object]],
    window_id: str,
) -> dict[str, object] | None:
    for item in metrics:
        metric = dict(item)
        if metric.get("window_id") == window_id:
            return metric
    return None


def _out_of_sample_metrics(
    window_metrics: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    windows = [
        dict(metric)
        for metric in window_metrics
        if _is_out_of_sample_window(metric)
    ]
    return {
        "primary_window_id": _LATER_TEST_WINDOW_ID,
        "windows": windows,
    }


def _candidate_exposures(
    bars: tuple[LocalDailyBar, ...],
    candidate: StrategyChallengerCandidate,
) -> tuple[DailyExposure, ...]:
    if candidate.strategy_family == "buy_and_hold_long_only":
        return _buy_and_hold_exposures(bars)
    if candidate.strategy_family == "time_series_momentum_long_only":
        return _time_series_momentum_exposures(bars, candidate)
    if candidate.strategy_family == "drawdown_filter_long_only":
        return _drawdown_filter_exposures(bars, candidate)
    if candidate.strategy_family not in {
        "sma_crossover_long_only",
        "sma_crossover_long_only_cash_risk_off",
    }:
        raise ValidationError(f"unsupported strategy_family: {candidate.strategy_family}")
    return _sma_crossover_exposures(bars, candidate)


def _sma_crossover_exposures(
    bars: tuple[LocalDailyBar, ...],
    candidate: StrategyChallengerCandidate,
) -> tuple[DailyExposure, ...]:
    prices = tuple(bar.adjusted_close for bar in bars)
    fast_sum = _ZERO
    slow_sum = _ZERO
    exposures: list[DailyExposure] = []

    for index, bar in enumerate(bars):
        fast_sum += prices[index]
        slow_sum += prices[index]
        if index >= candidate.fast_window:
            fast_sum -= prices[index - candidate.fast_window]
        if index >= candidate.slow_window:
            slow_sum -= prices[index - candidate.slow_window]

        exposure = _ZERO
        if index >= candidate.slow_window - 1:
            fast_sma = fast_sum / Decimal(candidate.fast_window)
            slow_sma = slow_sum / Decimal(candidate.slow_window)
            if fast_sma > slow_sma:
                exposure = _ONE

        exposures.append(DailyExposure(date=bar.date, exposure=exposure))

    return tuple(exposures)


def _buy_and_hold_exposures(
    bars: tuple[LocalDailyBar, ...],
) -> tuple[DailyExposure, ...]:
    return tuple(DailyExposure(date=bar.date, exposure=_ONE) for bar in bars)


def _time_series_momentum_exposures(
    bars: tuple[LocalDailyBar, ...],
    candidate: StrategyChallengerCandidate,
) -> tuple[DailyExposure, ...]:
    prices = tuple(bar.adjusted_close for bar in bars)
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        exposure = _ZERO
        if index >= candidate.slow_window:
            lookback_price = prices[index - candidate.slow_window]
            if prices[index] > lookback_price:
                exposure = _ONE
        exposures.append(DailyExposure(date=bar.date, exposure=exposure))
    return tuple(exposures)


def _drawdown_filter_exposures(
    bars: tuple[LocalDailyBar, ...],
    candidate: StrategyChallengerCandidate,
) -> tuple[DailyExposure, ...]:
    prices = tuple(bar.adjusted_close for bar in bars)
    threshold = Decimal("0.80")
    exposures: list[DailyExposure] = []
    for index, bar in enumerate(bars):
        exposure = _ZERO
        if index >= candidate.slow_window - 1:
            window_start = index - candidate.slow_window + 1
            rolling_high = max(prices[window_start : index + 1])
            if prices[index] >= rolling_high * threshold:
                exposure = _ONE
        exposures.append(DailyExposure(date=bar.date, exposure=exposure))
    return tuple(exposures)


def _basket_candidates(
    candidates: Iterable[StrategyChallengerCandidate],
) -> tuple[StrategyChallengerCandidate, ...]:
    return tuple(candidate for candidate in candidates if _is_basket_candidate(candidate))


def _is_basket_candidate(candidate: StrategyChallengerCandidate) -> bool:
    return candidate.strategy_family == _RELATIVE_MOMENTUM_FAMILY


def _basket_required_symbols(
    candidates: Iterable[StrategyChallengerCandidate],
) -> tuple[str, ...]:
    symbols: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        for symbol in candidate.basket_symbols:
            if symbol in seen:
                continue
            symbols.append(symbol)
            seen.add(symbol)
    return tuple(symbols)


def _basket_common_dates(
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
) -> tuple[date, ...]:
    if not bars_by_symbol:
        return ()
    first_bars = next(iter(bars_by_symbol.values()))
    return tuple(bar.date for bar in first_bars)


def _basket_common_bar_count(
    bars_by_symbol: Mapping[str, tuple[LocalDailyBar, ...]],
) -> int:
    dates = _basket_common_dates(bars_by_symbol)
    return len(dates)


def _is_rebalance_index(
    dates: tuple[date, ...],
    index: int,
    rebalance_rule: str,
) -> bool:
    if rebalance_rule == _REBALANCE_RULE_DAILY:
        return True
    if rebalance_rule != _REBALANCE_RULE_MONTHLY:
        raise ValidationError(f"unsupported rebalance_rule: {rebalance_rule}")
    if index == 0:
        return True
    previous = dates[index - 1]
    current = dates[index]
    return previous.year != current.year or previous.month != current.month


def _rebalance_allocation_record(
    on_date: date,
    weights: Mapping[str, Decimal],
) -> dict[str, object]:
    selected_symbols = [
        symbol for symbol, weight in weights.items() if weight > _ZERO
    ]
    return {
        "date": on_date.isoformat(),
        "selected_symbols": selected_symbols,
        "weights": {
            symbol: _decimal_text(weight)
            for symbol, weight in weights.items()
            if weight > _ZERO
        },
    }


def _override_basket_turnover_metrics(
    metrics: dict[str, object],
    allocation_turnovers: Sequence[Decimal],
) -> None:
    turnover = sum(allocation_turnovers, _ZERO)
    transition_count = sum(1 for item in allocation_turnovers if item != _ZERO)
    metrics["trade_count"] = transition_count
    metrics["transition_count"] = transition_count
    metrics["turnover"] = _decimal_text(turnover)


def _basket_result_metadata(
    candidate: StrategyChallengerCandidate,
) -> dict[str, object]:
    return {
        "basket_symbols": list(candidate.basket_symbols),
        "basket_symbol_count": len(candidate.basket_symbols),
        "allocation_scope": "approved_etf_basket",
        "top_n": candidate.top_n,
        "rebalance_rule": candidate.rebalance_rule,
        "paper_promotion_allowed": False,
        "paper_promotion_blocker": _NO_PAPER_PROMOTION_REASON,
    }


def _snapshot_from_local_bars(
    symbol: str,
    bars: tuple[LocalDailyBar, ...],
) -> HistoricalPriceSnapshot:
    if not bars:
        raise ValidationError("strategy challenger factory requires usable bars.")
    return HistoricalPriceSnapshot(
        symbol=symbol,
        bars=tuple(
            HistoricalPriceBar(
                symbol=bar.symbol,
                date=bar.date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                adjusted_close=bar.adjusted_close,
                volume=bar.volume,
            )
            for bar in bars
        ),
    )


def _baseline_comparison(
    result: Mapping[str, object],
    baseline: Mapping[str, object] | None,
    *,
    baseline_candidate_id: str = _BASELINE_CANDIDATE_ID,
) -> dict[str, object]:
    if baseline is None or baseline.get("metrics_status") != "valid":
        return _empty_baseline_comparison(baseline_candidate_id=baseline_candidate_id)
    if result.get("metrics_status") != "valid":
        return _empty_baseline_comparison(
            baseline_available=True,
            baseline_candidate_id=baseline_candidate_id,
        )

    total_return_delta = _decimal_from_result(result, "total_return") - _decimal_from_result(
        baseline,
        "total_return",
    )
    drawdown_delta = _decimal_from_result(result, "max_drawdown") - _decimal_from_result(
        baseline,
        "max_drawdown",
    )
    annualized_return_delta = _optional_delta(
        result,
        baseline,
        "annualized_return",
    )
    volatility_delta = _optional_delta(result, baseline, "annualized_volatility")
    sharpe_delta = _optional_delta(result, baseline, "sharpe_ratio")
    exposure_delta = _decimal_from_result(
        result,
        "exposure_percentage",
    ) - _decimal_from_result(baseline, "exposure_percentage")
    return {
        "baseline_candidate_id": baseline_candidate_id,
        "baseline_available": True,
        "total_return_delta": _decimal_text(total_return_delta),
        "max_drawdown_delta": _decimal_text(drawdown_delta),
        "annualized_return_delta": _optional_decimal_text(annualized_return_delta),
        "volatility_delta": _optional_decimal_text(volatility_delta),
        "sharpe_ratio_delta": _optional_decimal_text(sharpe_delta),
        "exposure_percentage_delta": _decimal_text(exposure_delta),
        "return_improved": total_return_delta > _ZERO,
        "drawdown_improved": drawdown_delta < _ZERO,
        "same_as_baseline": result.get("candidate_id") == baseline_candidate_id,
    }


def _empty_baseline_comparison(
    *,
    baseline_available: bool = False,
    baseline_candidate_id: str = _BASELINE_CANDIDATE_ID,
) -> dict[str, object]:
    return {
        "baseline_candidate_id": baseline_candidate_id,
        "baseline_available": baseline_available,
        "total_return_delta": None,
        "max_drawdown_delta": None,
        "annualized_return_delta": None,
        "volatility_delta": None,
        "sharpe_ratio_delta": None,
        "exposure_percentage_delta": None,
        "return_improved": False,
        "drawdown_improved": False,
        "same_as_baseline": False,
    }


def _add_validation_window_baseline_comparisons(
    result: dict[str, object],
    baseline: Mapping[str, object] | None,
) -> None:
    window_metrics = [
        dict(metric)
        for metric in result.get("validation_window_metrics", [])
        if isinstance(metric, Mapping)
    ]
    baseline_windows = _window_metric_map(
        [] if baseline is None else baseline.get("validation_window_metrics", [])
    )

    enriched_metrics: list[dict[str, object]] = []
    for metric in window_metrics:
        baseline_metric = baseline_windows.get(str(metric.get("window_id")))
        metric["baseline_comparison"] = _baseline_comparison(
            metric,
            baseline_metric,
        )
        enriched_metrics.append(metric)

    result["validation_window_metrics"] = enriched_metrics
    result["full_sample_metrics"] = _window_metrics_by_id(
        enriched_metrics,
        _FULL_SAMPLE_WINDOW_ID,
    )
    result["out_of_sample_metrics"] = _out_of_sample_metrics(enriched_metrics)


def _add_cost_baseline_comparisons(
    result: dict[str, object],
    baseline: Mapping[str, object] | None,
) -> None:
    cost_metrics = [
        dict(metric)
        for metric in result.get("cost_adjusted_metrics", [])
        if isinstance(metric, Mapping)
    ]
    baseline_costs = _cost_metric_map(
        [] if baseline is None else baseline.get("cost_adjusted_metrics", [])
    )

    enriched_costs: list[dict[str, object]] = []
    for cost_metric in cost_metrics:
        baseline_cost = baseline_costs.get(str(cost_metric.get("cost_id")))
        baseline_windows = _window_metric_map(
            [] if baseline_cost is None else baseline_cost.get("window_metrics", [])
        )

        window_metrics: list[dict[str, object]] = []
        for window_metric in cost_metric.get("window_metrics", []):
            if not isinstance(window_metric, Mapping):
                continue
            window = dict(window_metric)
            baseline_window = baseline_windows.get(str(window.get("window_id")))
            window["baseline_comparison"] = _baseline_comparison(
                window,
                baseline_window,
            )
            window_metrics.append(window)

        cost_metric["window_metrics"] = window_metrics
        cost_metric["full_sample_metrics"] = _window_metrics_by_id(
            window_metrics,
            _FULL_SAMPLE_WINDOW_ID,
        )
        cost_metric["out_of_sample_metrics"] = _out_of_sample_metrics(window_metrics)
        cost_metric["full_sample_baseline_comparison"] = _baseline_comparison(
            cost_metric.get("full_sample_metrics", {}),
            None if baseline_cost is None else baseline_cost.get("full_sample_metrics"),
        )
        cost_metric["out_of_sample_baseline_comparison"] = _baseline_comparison(
            _primary_out_of_sample_metric(cost_metric),
            None if baseline_cost is None else _primary_out_of_sample_metric(baseline_cost),
        )
        enriched_costs.append(cost_metric)

    result["cost_adjusted_metrics"] = enriched_costs


def _out_of_sample_validation_summary(
    result: Mapping[str, object],
) -> dict[str, object]:
    out_of_sample = result.get("out_of_sample_metrics", {})
    windows = []
    if isinstance(out_of_sample, Mapping):
        windows = [
            dict(window)
            for window in out_of_sample.get("windows", [])
            if isinstance(window, Mapping)
        ]

    window_results: list[dict[str, object]] = []
    passed_count = 0
    failed_count = 0
    primary_passed = False
    primary_failed = False

    for window in windows:
        comparison = dict(window.get("baseline_comparison", {}))
        total_return_delta = _optional_decimal_from_result(
            comparison,
            "total_return_delta",
        )
        drawdown_delta = _optional_decimal_from_result(
            comparison,
            "max_drawdown_delta",
        )
        sharpe_delta = _optional_decimal_from_result(
            comparison,
            "sharpe_ratio_delta",
        )
        passed = (
            total_return_delta is not None
            and drawdown_delta is not None
            and total_return_delta > _ZERO
            and drawdown_delta <= Decimal("0.01")
            and (sharpe_delta is None or sharpe_delta >= Decimal("-0.05"))
        )
        failed = (
            total_return_delta is None
            or drawdown_delta is None
            or total_return_delta <= _ZERO
            or drawdown_delta > Decimal("0.03")
        )
        if passed:
            passed_count += 1
        if failed:
            failed_count += 1
        if window.get("window_id") == _LATER_TEST_WINDOW_ID:
            primary_passed = passed
            primary_failed = failed
        window_results.append(
            {
                "window_id": window.get("window_id"),
                "window_role": window.get("window_role"),
                "passed": passed,
                "failed": failed,
                "total_return_delta": comparison.get("total_return_delta"),
                "max_drawdown_delta": comparison.get("max_drawdown_delta"),
                "sharpe_ratio_delta": comparison.get("sharpe_ratio_delta"),
            }
        )

    validation_passed = bool(windows) and primary_passed and failed_count == 0
    validation_failed = bool(windows) and (primary_failed or failed_count > 0)
    return {
        "primary_window_id": _LATER_TEST_WINDOW_ID,
        "window_count": len(windows),
        "passed_window_count": passed_count,
        "failed_window_count": failed_count,
        "primary_window_passed": primary_passed,
        "primary_window_failed": primary_failed,
        "validation_passed": validation_passed,
        "validation_failed": validation_failed,
        "window_results": window_results,
    }


def _empty_out_of_sample_validation_summary() -> dict[str, object]:
    return {
        "primary_window_id": _LATER_TEST_WINDOW_ID,
        "window_count": 0,
        "passed_window_count": 0,
        "failed_window_count": 0,
        "primary_window_passed": False,
        "primary_window_failed": False,
        "validation_passed": False,
        "validation_failed": False,
        "window_results": [],
    }


def _cost_sensitivity_summary(result: Mapping[str, object]) -> dict[str, object]:
    costs = _cost_metric_map(result.get("cost_adjusted_metrics", []))
    zero = costs.get(_ZERO_COST_ID)
    moderate = costs.get(_MODERATE_COST_ID)
    if zero is None or moderate is None:
        return _empty_cost_sensitivity_summary()

    zero_full = _mapping_or_empty(zero.get("full_sample_metrics"))
    moderate_full = _mapping_or_empty(moderate.get("full_sample_metrics"))
    zero_comparison = _mapping_or_empty(zero.get("full_sample_baseline_comparison"))
    moderate_comparison = _mapping_or_empty(
        moderate.get("full_sample_baseline_comparison")
    )

    zero_return = _optional_decimal_from_result(zero_full, "total_return")
    moderate_return = _optional_decimal_from_result(moderate_full, "total_return")
    zero_edge = _optional_decimal_from_result(
        zero_comparison,
        "total_return_delta",
    )
    moderate_edge = _optional_decimal_from_result(
        moderate_comparison,
        "total_return_delta",
    )

    return_degradation = (
        None
        if zero_return is None or moderate_return is None
        else zero_return - moderate_return
    )
    edge_degradation = (
        None if zero_edge is None or moderate_edge is None else zero_edge - moderate_edge
    )
    edge_broken = (
        zero_edge is not None
        and moderate_edge is not None
        and zero_edge > _ZERO
        and moderate_edge <= _ZERO
    )
    highly_sensitive = bool(
        edge_broken
        or (
            return_degradation is not None
            and edge_degradation is not None
            and return_degradation >= Decimal("0.02")
            and edge_degradation >= Decimal("0.01")
        )
    )

    return {
        "zero_cost_id": _ZERO_COST_ID,
        "moderate_cost_id": _MODERATE_COST_ID,
        "zero_cost_total_return": _optional_decimal_text(zero_return),
        "moderate_cost_total_return": _optional_decimal_text(moderate_return),
        "zero_cost_baseline_total_return_delta": _optional_decimal_text(zero_edge),
        "moderate_cost_baseline_total_return_delta": _optional_decimal_text(
            moderate_edge
        ),
        "moderate_cost_return_degradation": _optional_decimal_text(
            return_degradation
        ),
        "moderate_cost_edge_degradation": _optional_decimal_text(edge_degradation),
        "edge_broken_by_moderate_cost": edge_broken,
        "returns_highly_cost_sensitive": highly_sensitive,
    }


def _empty_cost_sensitivity_summary() -> dict[str, object]:
    return {
        "zero_cost_id": _ZERO_COST_ID,
        "moderate_cost_id": _MODERATE_COST_ID,
        "zero_cost_total_return": None,
        "moderate_cost_total_return": None,
        "zero_cost_baseline_total_return_delta": None,
        "moderate_cost_baseline_total_return_delta": None,
        "moderate_cost_return_degradation": None,
        "moderate_cost_edge_degradation": None,
        "edge_broken_by_moderate_cost": False,
        "returns_highly_cost_sensitive": False,
    }


def _oos_status(result: Mapping[str, object]) -> str:
    if result.get("metrics_status") != "valid":
        return "not_evaluable"
    summary = _mapping_or_empty(result.get("out_of_sample_validation"))
    if summary.get("validation_passed") is True:
        return "passed"
    if summary.get("validation_failed") is True:
        return "failed"
    if summary.get("window_count") == 0:
        return "not_evaluable"
    return "mixed"


def _cost_sensitivity_status(result: Mapping[str, object]) -> str:
    if result.get("metrics_status") != "valid":
        return "not_evaluable"
    summary = _mapping_or_empty(result.get("cost_sensitivity_summary"))
    if summary.get("edge_broken_by_moderate_cost") is True:
        return "edge_broken"
    if summary.get("returns_highly_cost_sensitive") is True:
        return "highly_sensitive"
    return "survived"


def _window_metric_map(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return {}
    mapping: dict[str, dict[str, object]] = {}
    for item in value:
        if isinstance(item, Mapping):
            metric = dict(item)
            window_id = metric.get("window_id")
            if window_id is not None:
                mapping[str(window_id)] = metric
    return mapping


def _cost_metric_map(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return {}
    mapping: dict[str, dict[str, object]] = {}
    for item in value:
        if isinstance(item, Mapping):
            metric = dict(item)
            cost_id = metric.get("cost_id")
            if cost_id is not None:
                mapping[str(cost_id)] = metric
    return mapping


def _primary_out_of_sample_metric(value: Mapping[str, object] | object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    out_of_sample = value.get("out_of_sample_metrics")
    if not isinstance(out_of_sample, Mapping):
        return {}
    for window in out_of_sample.get("windows", []):
        if isinstance(window, Mapping) and window.get("window_id") == _LATER_TEST_WINDOW_ID:
            return dict(window)
    return {}


def _is_out_of_sample_window(metric: Mapping[str, object]) -> bool:
    return str(metric.get("window_role")) in {"out_of_sample", "walk_forward"}


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _build_cross_asset_validation(
    results: Iterable[Mapping[str, object]],
    symbol_records: Sequence[Mapping[str, object]],
    config: StrategyChallengerFactoryConfig,
) -> dict[str, object]:
    result_items = tuple(dict(result) for result in results)
    symbols_evaluated = [
        str(record["symbol"])
        for record in symbol_records
        if record.get("data_quality_status") == _DATA_QUALITY_VALID
    ]
    symbols_missing_data = [
        str(record["symbol"])
        for record in symbol_records
        if record.get("data_availability_status") == _DATA_AVAILABILITY_MISSING
    ]
    passing_by_symbol: dict[str, list[str]] = {
        symbol: [] for symbol in config.symbols
    }
    failing_by_symbol: dict[str, list[str]] = {
        symbol: [] for symbol in config.symbols
    }

    for result in result_items:
        symbol = str(result.get("symbol"))
        candidate_id = str(result.get("candidate_id"))
        if result.get("oos_status") == "passed":
            passing_by_symbol.setdefault(symbol, []).append(candidate_id)
        elif result.get("oos_status") == "failed":
            failing_by_symbol.setdefault(symbol, []).append(candidate_id)

    candidate_rollups = _cross_asset_candidate_rollups(result_items, config)
    robustness_flags = _cross_asset_robustness_flags(
        symbols_evaluated=symbols_evaluated,
        symbols_missing_data=symbols_missing_data,
        candidate_rollups=candidate_rollups,
        config=config,
    )
    return {
        "record_type": "strategy_challenger_cross_asset_validation",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "operating_baseline_symbol": config.symbol,
        "symbols_requested": list(config.symbols),
        "symbols_evaluated": symbols_evaluated,
        "symbols_missing_data": symbols_missing_data,
        "symbol_data_statuses": [dict(record) for record in symbol_records],
        "candidates_passing_oos_by_symbol": passing_by_symbol,
        "candidates_failing_oos_by_symbol": failing_by_symbol,
        "candidate_aggregate_scores": _candidate_aggregate_scores(result_items),
        "candidate_rollups": candidate_rollups,
        "robustness_flags": robustness_flags,
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "safety": _safety_payload(),
    }


def _apply_cross_asset_promotion_gates(
    results: Iterable[Mapping[str, object]],
    config: StrategyChallengerFactoryConfig,
) -> tuple[dict[str, object], ...]:
    result_items = tuple(dict(result) for result in results)
    gated: list[dict[str, object]] = []
    for result in result_items:
        candidate_id = str(result.get("candidate_id"))
        blockers = _cross_asset_paper_candidate_blockers(
            candidate_id,
            result_items,
            config,
        )
        gate = {
            "paper_candidate_allowed": not blockers,
            "blockers": blockers,
            "operating_baseline_symbol": config.symbol,
            "symbols_requested": list(config.symbols),
        }
        enriched = dict(result)
        enriched["cross_asset_promotion_gate"] = gate
        if (
            enriched.get("promotion_classification") == "paper_candidate"
            and blockers
        ):
            enriched["promotion_classification"] = "preview_only"
            reasons = [
                str(reason)
                for reason in enriched.get("promotion_reasons", [])
                if isinstance(reason, str)
            ]
            enriched["promotion_reasons"] = list(
                dict.fromkeys(
                    [
                        *reasons,
                        "cross_asset_promotion_gate_blocked",
                        *blockers,
                    ]
                )
            )
        gated.append(enriched)
    return tuple(gated)


def _cross_asset_paper_candidate_blockers(
    candidate_id: str,
    results: Sequence[Mapping[str, object]],
    config: StrategyChallengerFactoryConfig,
) -> list[str]:
    if candidate_id in {_BASELINE_CANDIDATE_ID, *_COMPARATOR_CANDIDATE_IDS}:
        return ["not_a_promotable_challenger"]

    blockers: list[str] = [_NO_PAPER_PROMOTION_REASON]
    result_by_symbol = {
        str(result.get("symbol")): dict(result)
        for result in results
        if result.get("candidate_id") == candidate_id
    }
    operating = result_by_symbol.get(config.symbol)
    if operating is None:
        blockers.append("operating_symbol_result_missing")
    elif operating.get("data_availability_status") == _DATA_AVAILABILITY_MISSING:
        blockers.extend(["operating_symbol_data_missing", _DATA_REFRESH_REQUIRED])
    elif operating.get("metrics_status") != "valid":
        blockers.append("operating_symbol_metrics_not_valid")
    else:
        if operating.get("oos_status") != "passed":
            blockers.append("operating_symbol_oos_not_passed")
        if operating.get("cost_sensitivity_status") != "survived":
            blockers.append("operating_symbol_cost_sensitivity_not_survived")

    non_operating_results = [
        result
        for symbol, result in result_by_symbol.items()
        if symbol != config.symbol and result.get("metrics_status") == "valid"
    ]
    confirming_non_operating = [
        result
        for result in non_operating_results
        if result.get("oos_status") == "passed"
        and result.get("cost_sensitivity_status") == "survived"
    ]
    if not non_operating_results:
        blockers.append("cross_asset_data_refresh_required")
    elif not confirming_non_operating:
        blockers.append("cross_asset_oos_or_cost_not_confirmed")
    if (
        operating is not None
        and operating.get("oos_status") == "passed"
        and not confirming_non_operating
    ):
        blockers.append("only_operating_symbol_evidence_passed")

    return list(dict.fromkeys(blockers))


def _cross_asset_candidate_rollups(
    results: Sequence[Mapping[str, object]],
    config: StrategyChallengerFactoryConfig,
) -> list[dict[str, object]]:
    candidate_ids = sorted(
        {
            str(result.get("candidate_id"))
            for result in results
            if result.get("candidate_id") is not None
        }
    )
    rollups: list[dict[str, object]] = []
    for candidate_id in candidate_ids:
        candidate_results = [
            dict(result)
            for result in results
            if result.get("candidate_id") == candidate_id
        ]
        symbols_with_valid_metrics = [
            str(result.get("symbol"))
            for result in candidate_results
            if result.get("metrics_status") == "valid"
        ]
        symbols_missing_data = [
            str(result.get("symbol"))
            for result in candidate_results
            if result.get("data_availability_status") == _DATA_AVAILABILITY_MISSING
        ]
        oos_passed_symbols = [
            str(result.get("symbol"))
            for result in candidate_results
            if result.get("oos_status") == "passed"
        ]
        oos_failed_symbols = [
            str(result.get("symbol"))
            for result in candidate_results
            if result.get("oos_status") == "failed"
        ]
        cost_survived_symbols = [
            str(result.get("symbol"))
            for result in candidate_results
            if result.get("cost_sensitivity_status") == "survived"
        ]
        cost_broken_symbols = [
            str(result.get("symbol"))
            for result in candidate_results
            if result.get("cost_sensitivity_status")
            in {"edge_broken", "highly_sensitive"}
        ]
        operating = next(
            (
                result
                for result in candidate_results
                if result.get("symbol") == config.symbol
            ),
            None,
        )
        blockers = _cross_asset_paper_candidate_blockers(
            candidate_id,
            results,
            config,
        )
        rollups.append(
            {
                "candidate_id": candidate_id,
                "symbols_with_valid_metrics": symbols_with_valid_metrics,
                "symbols_missing_data": symbols_missing_data,
                "oos_passed_symbols": oos_passed_symbols,
                "oos_failed_symbols": oos_failed_symbols,
                "cost_survived_symbols": cost_survived_symbols,
                "cost_broken_symbols": cost_broken_symbols,
                "operating_symbol_oos_status": None
                if operating is None
                else operating.get("oos_status"),
                "operating_symbol_cost_sensitivity_status": None
                if operating is None
                else operating.get("cost_sensitivity_status"),
                "paper_candidate_allowed": not blockers,
                "paper_candidate_blockers": blockers,
            }
        )
    return rollups


def _candidate_aggregate_scores(
    results: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    ranks_by_candidate: dict[str, list[int]] = {}
    scores_by_candidate: dict[str, list[Decimal]] = {}
    symbols = sorted(
        {
            str(result.get("symbol"))
            for result in results
            if result.get("metrics_status") == "valid"
        }
    )
    for symbol in symbols:
        symbol_results = [
            dict(result)
            for result in results
            if result.get("symbol") == symbol
            and result.get("metrics_status") == "valid"
            and result.get("candidate_id") not in {_BASELINE_CANDIDATE_ID}
        ]
        ranked = sorted(symbol_results, key=_recommendation_sort_key, reverse=True)
        for rank, result in enumerate(ranked, start=1):
            candidate_id = str(result.get("candidate_id"))
            ranks_by_candidate.setdefault(candidate_id, []).append(rank)
            scores_by_candidate.setdefault(candidate_id, []).append(
                _aggregate_score(result)
            )

    aggregate_records = []
    for candidate_id, ranks in ranks_by_candidate.items():
        scores = scores_by_candidate.get(candidate_id, [])
        average_rank = Decimal(sum(ranks)) / Decimal(len(ranks))
        average_score = (
            None
            if not scores
            else sum(scores, Decimal("0")) / Decimal(len(scores))
        )
        aggregate_records.append(
            {
                "candidate_id": candidate_id,
                "symbol_count": len(ranks),
                "average_rank": _decimal_text(average_rank),
                "average_score": _optional_decimal_text(average_score),
            }
        )
    return sorted(
        aggregate_records,
        key=lambda item: (
            Decimal(str(item["average_rank"])),
            -Decimal(str(item["average_score"] or "0")),
            str(item["candidate_id"]),
        ),
    )


def _aggregate_score(result: Mapping[str, object]) -> Decimal:
    return_delta = _optional_decimal_from_result(
        result,
        "baseline_total_return_delta",
    ) or _ZERO
    drawdown_delta = _optional_decimal_from_result(
        result,
        "baseline_max_drawdown_delta",
    ) or _ZERO
    sharpe_delta = _optional_decimal_from_result(
        result,
        "baseline_sharpe_ratio_delta",
    ) or _ZERO
    drawdown_penalty = drawdown_delta if drawdown_delta > _ZERO else _ZERO
    return return_delta + sharpe_delta - drawdown_penalty


def _cross_asset_robustness_flags(
    *,
    symbols_evaluated: Sequence[str],
    symbols_missing_data: Sequence[str],
    candidate_rollups: Sequence[Mapping[str, object]],
    config: StrategyChallengerFactoryConfig,
) -> list[str]:
    flags: list[str] = []
    if config.symbol in symbols_evaluated:
        flags.append("operating_symbol_data_available")
    else:
        flags.append("operating_symbol_data_missing")
    non_operating_evaluated = [
        symbol for symbol in symbols_evaluated if symbol != config.symbol
    ]
    if non_operating_evaluated:
        flags.append("non_operating_symbols_evaluated")
    else:
        flags.append("non_operating_symbol_data_missing")
    if symbols_missing_data:
        flags.append("cross_asset_data_incomplete")
        flags.append(_DATA_REFRESH_REQUIRED)
    if not any(
        rollup.get("paper_candidate_allowed") is True
        for rollup in candidate_rollups
    ):
        flags.append("paper_candidate_blocked_until_cross_asset_confirmation")
    return list(dict.fromkeys(flags))


def _aggregate_data_quality_status(
    symbol_records: Sequence[Mapping[str, object]],
) -> str:
    statuses = {str(record.get("data_quality_status")) for record in symbol_records}
    if statuses == {_DATA_QUALITY_VALID}:
        return _DATA_QUALITY_VALID
    if statuses == {_DATA_QUALITY_MISSING}:
        return _DATA_QUALITY_MISSING
    if statuses == {_DATA_QUALITY_MALFORMED}:
        return _DATA_QUALITY_MALFORMED
    return _DATA_QUALITY_MIXED


def _aggregate_data_error(
    symbol_records: Sequence[Mapping[str, object]],
) -> str | None:
    errors = [
        f"{record.get('symbol')}: {record.get('data_error')}"
        for record in symbol_records
        if record.get("data_error")
    ]
    if not errors:
        return None
    return "; ".join(str(error) for error in errors)


def _build_promotion_recommendations(
    results: Iterable[Mapping[str, object]],
    *,
    cross_asset_validation: Mapping[str, object] | None = None,
) -> dict[str, object]:
    result_items = tuple(dict(result) for result in results)
    counts = {name: 0 for name in STRATEGY_CHALLENGER_PROMOTION_CLASSIFICATIONS}
    for result in result_items:
        classification = str(result.get("promotion_classification", "reject"))
        if classification in counts:
            counts[classification] += 1

    candidates = tuple(
        result
        for result in result_items
        if result.get("candidate_id") != _BASELINE_CANDIDATE_ID
        and result.get("candidate_id") not in _COMPARATOR_CANDIDATE_IDS
        and result.get("metrics_status") == "valid"
    )
    best = max(candidates, key=_recommendation_sort_key, default=None)
    if best is None:
        classification_recommendation = "no_valid_challenger_ready"
    else:
        best_classification = str(best.get("promotion_classification"))
        if best_classification == "paper_candidate":
            classification_recommendation = "review_paper_candidate_conservatively"
        elif best_classification == "preview_only":
            classification_recommendation = "preview_only_research_followup"
        elif best_classification == "keep_researching":
            classification_recommendation = "keep_researching"
        else:
            classification_recommendation = "no_promotion"

    return {
        "record_type": "strategy_challenger_promotion_recommendations",
        "schema_version": _SCHEMA_VERSION,
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "classification_counts": counts,
        "cross_asset_validation": dict(cross_asset_validation or {}),
        "best_candidate_id": None if best is None else best.get("candidate_id"),
        "best_symbol": None if best is None else best.get("symbol"),
        "best_candidate_classification": None
        if best is None
        else best.get("promotion_classification"),
        "classification_recommendation": classification_recommendation,
        "paper_candidate_count": counts["paper_candidate"],
        "preview_only_count": counts["preview_only"],
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "profit_claim": "none",
        "recommendations": [
            {
                "symbol": result.get("symbol"),
                "candidate_id": result.get("candidate_id"),
                "promotion_classification": result.get("promotion_classification"),
                "promotion_reasons": result.get("promotion_reasons", []),
                "baseline_total_return_delta": result.get("baseline_total_return_delta"),
                "baseline_max_drawdown_delta": result.get("baseline_max_drawdown_delta"),
                "baseline_sharpe_ratio_delta": result.get("baseline_sharpe_ratio_delta"),
                "out_of_sample_validation": result.get(
                    "out_of_sample_validation",
                    {},
                ),
                "cost_sensitivity_summary": result.get(
                    "cost_sensitivity_summary",
                    {},
                ),
                "cross_asset_promotion_gate": result.get(
                    "cross_asset_promotion_gate",
                    {},
                ),
            }
            for result in result_items
        ],
    }


def _recommendation_sort_key(result: Mapping[str, object]) -> tuple[int, Decimal, Decimal, Decimal]:
    classification = str(result.get("promotion_classification", "reject"))
    return_delta = _optional_decimal_from_result(
        result,
        "baseline_total_return_delta",
    ) or Decimal("-999")
    drawdown_delta = _optional_decimal_from_result(
        result,
        "baseline_max_drawdown_delta",
    ) or Decimal("999")
    sharpe_delta = _optional_decimal_from_result(
        result,
        "baseline_sharpe_ratio_delta",
    ) or Decimal("-999")
    return (
        _PROMOTION_PRIORITY.get(classification, 0),
        return_delta,
        -drawdown_delta,
        sharpe_delta,
    )


def _manifest_payload(
    payload: Mapping[str, object],
    output_root: Path,
    artifact_paths: tuple[Path, ...] | list[Path],
) -> dict[str, object]:
    artifacts = tuple(_artifact_record(output_root, path) for path in artifact_paths)
    return {
        "record_type": "strategy_challenger_factory_manifest",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "run_id": payload.get("run_id"),
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "output_root": str(output_root),
        "data_path": payload.get("data_path"),
        "data_sha256": payload.get("data_sha256"),
        "operating_baseline_symbol": payload.get("operating_baseline_symbol"),
        "symbols": list(payload.get("symbols", [])),
        "symbols_evaluated": list(payload.get("symbols_evaluated", [])),
        "symbols_missing_data": list(payload.get("symbols_missing_data", [])),
        "artifact_count": len(artifacts),
        "artifacts": list(artifacts),
        "safety": _safety_payload(),
        "profit_claim": "none",
    }


def _validation_windows_artifact(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "record_type": "strategy_challenger_validation_windows",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": payload.get("factory_id"),
        "previous_factory_id": payload.get("previous_factory_id"),
        "run_id": payload.get("run_id"),
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "symbol": payload.get("symbol"),
        "operating_baseline_symbol": payload.get("operating_baseline_symbol"),
        "symbols": list(payload.get("symbols", [])),
        "timeframe": payload.get("timeframe"),
        "data_path": payload.get("data_path"),
        "data_sha256": payload.get("data_sha256"),
        "validation_window_method": payload.get("validation_window_method"),
        "validation_windows": list(payload.get("validation_windows", [])),
        "validation_windows_by_symbol": dict(
            _mapping_or_empty(payload.get("validation_windows_by_symbol"))
        ),
        "safety": _safety_payload(),
    }


def _cost_sensitivity_artifact(payload: Mapping[str, object]) -> dict[str, object]:
    results = [
        {
            "candidate_id": result.get("candidate_id"),
            "symbol": result.get("symbol"),
            "baseline_candidate_id": result.get("baseline_candidate_id"),
            "cost_assumptions_evaluated": result.get("cost_assumptions_evaluated", []),
            "cost_sensitivity_summary": result.get("cost_sensitivity_summary", {}),
            "cost_sensitivity_status": result.get("cost_sensitivity_status"),
            "cost_adjusted_metrics": result.get("cost_adjusted_metrics", []),
            "promotion_classification": result.get("promotion_classification"),
            "promotion_reasons": result.get("promotion_reasons", []),
        }
        for result in _result_list(payload)
    ]
    return {
        "record_type": "strategy_challenger_cost_sensitivity",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": payload.get("factory_id"),
        "previous_factory_id": payload.get("previous_factory_id"),
        "run_id": payload.get("run_id"),
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "symbol": payload.get("symbol"),
        "operating_baseline_symbol": payload.get("operating_baseline_symbol"),
        "symbols": list(payload.get("symbols", [])),
        "timeframe": payload.get("timeframe"),
        "data_path": payload.get("data_path"),
        "data_sha256": payload.get("data_sha256"),
        "cost_assumptions": list(payload.get("cost_assumptions", [])),
        "results": results,
        "safety": _safety_payload(),
    }


def _cross_asset_validation_artifact(payload: Mapping[str, object]) -> dict[str, object]:
    cross_asset = dict(_mapping_or_empty(payload.get("cross_asset_validation")))
    return {
        "record_type": "strategy_challenger_cross_asset_validation_artifact",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": payload.get("factory_id"),
        "previous_factory_id": payload.get("previous_factory_id"),
        "run_id": payload.get("run_id"),
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "operating_baseline_symbol": payload.get("operating_baseline_symbol"),
        "symbols": list(payload.get("symbols", [])),
        "cross_asset_validation": cross_asset,
        "safety": _safety_payload(),
    }


def _artifact_record(output_root: Path, path: Path) -> dict[str, object]:
    return {
        "name": path.name,
        "path": str(path),
        "path_relative_to_output_root": path.relative_to(output_root).as_posix(),
        "sha256": _file_sha256(path),
        "byte_size": path.stat().st_size,
    }


def _safety_payload() -> dict[str, object]:
    return {
        "research_only": True,
        "offline_only": True,
        "not_live_authorized": True,
        "no_paper_promotion": True,
        "profit_claim": "none",
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
    }


def _metrics_are_possible(result: Mapping[str, object]) -> bool:
    try:
        total_return = _decimal_from_result(result, "total_return")
        max_drawdown = _decimal_from_result(result, "max_drawdown")
        exposure_percentage = _decimal_from_result(result, "exposure_percentage")
    except ValidationError:
        return False
    if total_return <= Decimal("-1"):
        return False
    if max_drawdown < _ZERO or max_drawdown > _ONE:
        return False
    if exposure_percentage < _ZERO or exposure_percentage > Decimal("100"):
        return False
    for field_name in (
        "annualized_return",
        "annualized_volatility",
        "sharpe_ratio",
    ):
        value = _optional_decimal_from_result(result, field_name)
        if value is not None and not value.is_finite():
            return False
    return True


def _annualized_return(
    total_return: Decimal,
    start_date: date,
    end_date: date,
) -> Decimal | None:
    day_count = (end_date - start_date).days
    if day_count <= 0:
        return None
    base = float(_ONE + total_return)
    if base <= 0:
        return None
    annualized = math.pow(base, 365.25 / float(day_count)) - 1.0
    return _decimal_from_float(annualized)


def _annualized_volatility(daily_returns: tuple[Decimal, ...]) -> Decimal | None:
    if len(daily_returns) < 2:
        return None
    values = [float(item) for item in daily_returns]
    annualized = stdev(values) * math.sqrt(float(_TRADING_DAYS_PER_YEAR))
    return _decimal_from_float(annualized)


def _sharpe_like_score(
    annualized_return: Decimal | None,
    annualized_volatility: Decimal | None,
) -> Decimal | None:
    if annualized_return is None or annualized_volatility is None:
        return None
    if annualized_volatility <= _ZERO:
        return None
    return annualized_return / annualized_volatility


def _transition_count(exposures: tuple[DailyExposure, ...]) -> int:
    transitions = 0
    previous = _ZERO
    for exposure in exposures:
        if exposure.exposure != previous:
            transitions += 1
        previous = exposure.exposure
    return transitions


def _file_sha256_or_none(path: Path) -> str | None:
    if not path.is_file():
        return None
    return _file_sha256(path)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _json_dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    return value


def _result_list(payload: Mapping[str, object]) -> list[dict[str, object]]:
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        raise ValidationError("payload results must be a list.")
    return [dict(item) for item in raw_results if isinstance(item, Mapping)]


def _payload_as_of_range(
    results: Iterable[Mapping[str, object]],
) -> tuple[str | None, str | None]:
    starts = tuple(
        str(result["as_of_start"])
        for result in results
        if result.get("as_of_start") is not None
    )
    ends = tuple(
        str(result["as_of_end"])
        for result in results
        if result.get("as_of_end") is not None
    )
    return (min(starts) if starts else None, max(ends) if ends else None)


def _run_id(
    symbols: Sequence[str] | str,
    as_of_end: str | None,
    data_sha256: str | None,
) -> str:
    date_part = "unknown_as_of" if as_of_end is None else as_of_end.replace("-", "")
    hash_part = "missingdata" if data_sha256 is None else data_sha256[:12]
    if isinstance(symbols, str):
        symbol_part = _symbol(symbols).lower()
    else:
        symbol_part = "_".join(_symbol(symbol).lower() for symbol in symbols)
    return f"strategy_challenger_factory_{symbol_part}_{date_part}_{hash_part}"


def _limitations_with(*extra: str) -> tuple[str, ...]:
    cleaned_extra = tuple(_required_string(item, "limitation") for item in extra)
    return (*_DEFAULT_LIMITATIONS, *cleaned_extra)


def _optional_delta(
    result: Mapping[str, object],
    baseline: Mapping[str, object],
    field_name: str,
) -> Decimal | None:
    result_value = _optional_decimal_from_result(result, field_name)
    baseline_value = _optional_decimal_from_result(baseline, field_name)
    if result_value is None or baseline_value is None:
        return None
    return result_value - baseline_value


def _decimal_from_float(value: float) -> Decimal:
    if not math.isfinite(value):
        raise ValidationError("metric must be finite.")
    return Decimal(f"{value:.12f}")


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _decimal_from_result(result: Mapping[str, object], field_name: str) -> Decimal:
    value = result.get(field_name)
    if value is None:
        raise ValidationError(f"{field_name} is required.")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be decimal-compatible.") from exc
    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return decimal_value


def _optional_decimal_from_result(
    result: Mapping[str, object],
    field_name: str,
) -> Decimal | None:
    value = result.get(field_name)
    if value is None:
        return None
    return _decimal_from_result(result, field_name)


def _int_from_result(result: Mapping[str, object], field_name: str) -> int:
    value = result.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    return value


def _int_from_mapping(value: Mapping[str, object], field_name: str) -> int:
    item = value.get(field_name)
    if not isinstance(item, int) or isinstance(item, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    return item


def _candidate_tuple(
    candidates: Iterable[StrategyChallengerCandidate],
) -> tuple[StrategyChallengerCandidate, ...]:
    try:
        items = tuple(candidates)
    except TypeError as exc:
        raise ValidationError("candidates must be iterable.") from exc
    if not items:
        raise ValidationError("candidates must contain at least one candidate.")
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, StrategyChallengerCandidate):
            raise ValidationError("candidates must contain StrategyChallengerCandidate values.")
        if item.candidate_id in seen_ids:
            raise ValidationError("candidate_id values must be unique.")
        seen_ids.add(item.candidate_id)
    return items


def _config(value: StrategyChallengerFactoryConfig) -> StrategyChallengerFactoryConfig:
    if not isinstance(value, StrategyChallengerFactoryConfig):
        raise ValidationError("config must be a StrategyChallengerFactoryConfig.")
    return value


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        if not value.strip():
            raise ValidationError(f"{field_name} is required.")
        if "://" in value:
            raise ValidationError(f"{field_name} must be a local path.")
        path = Path(value)
    else:
        raise ValidationError(f"{field_name} must be a path.")
    return path


def _symbol(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("symbol must be a non-empty uppercase symbol.")
    normalized = value.strip().upper()
    if not normalized:
        raise ValidationError("symbol must be a non-empty uppercase symbol.")
    return normalized


def _symbol_tuple(
    value: Iterable[str] | str | None,
    *,
    fallback_symbol: str,
) -> tuple[str, ...]:
    fallback = _symbol(fallback_symbol)
    if value is None:
        return (fallback,)
    if isinstance(value, str):
        raw_items = tuple(item for item in value.split(","))
    else:
        try:
            raw_items = tuple(value)
        except TypeError as exc:
            raise ValidationError("symbols must be a comma string or iterable.") from exc
    symbols: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        checked = _symbol(raw_item)
        if checked in seen:
            continue
        symbols.append(checked)
        seen.add(checked)
    if not symbols:
        raise ValidationError("symbols must contain at least one symbol.")
    if fallback not in seen:
        symbols.insert(0, fallback)
    elif symbols[0] != fallback:
        symbols = [fallback, *(symbol for symbol in symbols if symbol != fallback)]
    return tuple(symbols)


def _basket_symbol_tuple(value: Iterable[str] | str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_items = tuple(item for item in value.split(","))
    else:
        try:
            raw_items = tuple(value)
        except TypeError as exc:
            raise ValidationError("basket_symbols must be a comma string or iterable.") from exc
    symbols: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        checked = _symbol(raw_item)
        if checked in seen:
            continue
        symbols.append(checked)
        seen.add(checked)
    return tuple(symbols)


def _rebalance_rule(value: str) -> str:
    checked = _required_string(value, "rebalance_rule").lower()
    if checked not in {_REBALANCE_RULE_DAILY, _REBALANCE_RULE_MONTHLY}:
        raise ValidationError("rebalance_rule must be daily or monthly.")
    return checked


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return normalized


def _positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a positive integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _optional_date(value: date | str | None, field_name: str) -> date | None:
    if value is None:
        return None
    if type(value) is date:
        return value
    if isinstance(value, str):
        text = _required_string(value, field_name)
        if len(text) != 10 or text[4] != "-" or text[7] != "-":
            raise ValidationError(f"{field_name} must be an ISO date.")
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO date.") from exc
    if isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a plain date.")
    raise ValidationError(f"{field_name} must be an ISO date.")


def _positive_decimal(value: Decimal | str, field_name: str) -> Decimal:
    checked = _decimal_value(value, field_name)
    if checked <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return checked


def _non_negative_decimal(value: Decimal | str, field_name: str) -> Decimal:
    checked = _decimal_value(value, field_name)
    if checked < _ZERO:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return checked


def _decimal_value(value: Decimal | str, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        checked = value
    elif isinstance(value, str):
        try:
            checked = Decimal(value.strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{field_name} must be decimal-compatible.") from exc
    else:
        raise ValidationError(f"{field_name} must be a Decimal or string.")
    if not checked.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return checked


def _markdown_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="strategy-challenger-factory")
    parser.add_argument(
        "--output-root",
        default=str(_DEFAULT_OUTPUT_ROOT),
        help="Directory for challenger factory artifacts.",
    )
    parser.add_argument(
        "--data-path",
        default=str(_DEFAULT_DATA_PATH),
        help="Local strict daily bars CSV to evaluate.",
    )
    parser.add_argument("--symbol", default=_DEFAULT_SYMBOL)
    parser.add_argument(
        "--symbols",
        default=None,
        help="Comma-separated symbols to evaluate. Defaults to --symbol only.",
    )
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument("--initial-equity", default=str(_DEFAULT_INITIAL_EQUITY))
    parser.add_argument("--fee-bps", default=str(_DEFAULT_FEE_BPS))
    parser.add_argument("--slippage-bps", default=str(_DEFAULT_SLIPPAGE_BPS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = StrategyChallengerFactoryConfig(
        output_root=args.output_root,
        data_path=args.data_path,
        symbol=args.symbol,
        symbols=args.symbols,
        as_of=args.as_of_date,
        initial_equity=args.initial_equity,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
    )
    payload = run_strategy_challenger_factory(config)
    recommendations = dict(payload["promotion_recommendations"])  # type: ignore[index]
    print(f"strategy_challenger_factory_status=completed")
    print(f"output_root={config.output_root}")
    print(f"best_candidate_id={recommendations.get('best_candidate_id')}")
    print(
        "best_candidate_classification="
        f"{recommendations.get('best_candidate_classification')}"
    )
    print(
        "classification_recommendation="
        f"{recommendations.get('classification_recommendation')}"
    )
    cross_asset = dict(payload.get("cross_asset_validation", {}))
    print("symbols_evaluated=" + ",".join(str(item) for item in cross_asset.get("symbols_evaluated", [])))
    print("symbols_missing_data=" + ",".join(str(item) for item in cross_asset.get("symbols_missing_data", [])))
    print("broker_mutation_performed=false")
    print("live_mutation_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
