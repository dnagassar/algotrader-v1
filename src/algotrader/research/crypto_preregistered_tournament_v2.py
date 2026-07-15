"""Immutable preregistration for the BTC/ETH/SOL crypto tournament v2.

V2 is a research-only successor to the closed four-symbol tournament v1.
Its candidate set, future calendar OOS window, costs, data-quality policy,
and promotion gates are fixed before any v2 OOS bytes are fetched or scored.
Nothing in this module can access a network, broker, account, or order path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

CRYPTO_TOURNAMENT_V2_SCHEMA_VERSION = "v5_23_crypto_tournament_v2_v1"
CRYPTO_TOURNAMENT_V2_FACTORY_VERSION = "v5_23_crypto_tournament_v2_factory_v1"
CRYPTO_TOURNAMENT_V2_POLICY_VERSION = "v5_23_crypto_tournament_v2_policy_v1"
CRYPTO_TOURNAMENT_V2_GAP_POLICY_VERSION = (
    "v5_23_crypto_tournament_v2_isolated_gap_policy_v1"
)
CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT = (
    "2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b"
)

TOURNAMENT_V2_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD")
PRIMARY_TIMEFRAME = "1Hour"
ROBUSTNESS_TIMEFRAME = "4Hour"
DISCOVERY_START = "2026-01-16T00:00:00+00:00"
DISCOVERY_END_EXCLUSIVE = "2026-07-15T00:00:00+00:00"
DISCOVERY_EXPECTED_HOURLY_BARS = 4_320
EMBARGO_START = DISCOVERY_END_EXCLUSIVE
EMBARGO_END_EXCLUSIVE = "2026-07-16T00:00:00+00:00"
OOS_START = EMBARGO_END_EXCLUSIVE
OOS_END_INCLUSIVE = "2026-08-12T23:00:00+00:00"
OOS_END_EXCLUSIVE = "2026-08-13T00:00:00+00:00"
OOS_HOURLY_BARS = 672
OOS_FOLD_COUNT = 4
OOS_FOLD_HOURLY_BARS = 168
INTERIM_CHECKPOINTS = (
    "2026-07-23T00:00:00+00:00",
    "2026-07-30T00:00:00+00:00",
    "2026-08-06T00:00:00+00:00",
)

BASE_FEE_BPS = 25
BASE_SLIPPAGE_BPS = 15
STRESS_FEE_BPS = 50
STRESS_SLIPPAGE_BPS = 30
MAX_OOS_DRAWDOWN = "0.20"
MINIMUM_POSITIVE_OOS_FOLDS = 3
MAX_POSITIVE_PROFIT_CONCENTRATION = "0.50"
MINIMUM_COMPLETED_ROUND_TRIPS = 30
MINIMUM_OOS_TRANSITIONS = 20
MINIMUM_RAW_HOURLY_COVERAGE = "0.995"
MINIMUM_POSITIVE_RAW_VOLUME_FRACTION = "0.95"
MAXIMUM_CONSECUTIVE_MISSING_HOURS = 1

__all__ = [
    "CRYPTO_TOURNAMENT_V2_FACTORY_VERSION",
    "CRYPTO_TOURNAMENT_V2_GAP_POLICY_VERSION",
    "CRYPTO_TOURNAMENT_V2_POLICY_VERSION",
    "CRYPTO_TOURNAMENT_V2_SCHEMA_VERSION",
    "CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT",
    "DISCOVERY_END_EXCLUSIVE",
    "DISCOVERY_EXPECTED_HOURLY_BARS",
    "DISCOVERY_START",
    "EMBARGO_END_EXCLUSIVE",
    "EMBARGO_START",
    "INTERIM_CHECKPOINTS",
    "OOS_END_EXCLUSIVE",
    "OOS_END_INCLUSIVE",
    "OOS_FOLD_COUNT",
    "OOS_FOLD_HOURLY_BARS",
    "OOS_HOURLY_BARS",
    "OOS_START",
    "TOURNAMENT_V2_SYMBOLS",
    "build_crypto_tournament_v2_preregistration",
]


@dataclass(frozen=True, slots=True)
class _CandidateSpec:
    strategy_id: str
    strategy_family: str
    lookback_hours: int = 0
    fast_hours: int = 0
    slow_hours: int = 0

    def elapsed_parameters(self) -> dict[str, int]:
        if self.strategy_family in {"trend_momentum", "breakout"}:
            return {"lookback_hours": self.lookback_hours}
        return {"fast_hours": self.fast_hours, "slow_hours": self.slow_hours}

    def timeframe_parameters(self, hours: int) -> dict[str, int]:
        values = self.elapsed_parameters()
        if any(value % hours for value in values.values()):
            raise ValueError("candidate parameter must map exactly to timeframe")
        if self.strategy_family in {"trend_momentum", "breakout"}:
            return {"lookback_bars": self.lookback_hours // hours}
        return {
            "fast_bars": self.fast_hours // hours,
            "slow_bars": self.slow_hours // hours,
        }


def _candidate_specs() -> tuple[_CandidateSpec, ...]:
    return (
        _CandidateSpec("trend_momentum_72h", "trend_momentum", lookback_hours=72),
        _CandidateSpec("breakout_168h", "breakout", lookback_hours=168),
        _CandidateSpec(
            "moving_average_regime_24h_168h",
            "moving_average_regime",
            fast_hours=24,
            slow_hours=168,
        ),
    )


def build_crypto_tournament_v2_preregistration() -> dict[str, object]:
    """Return the immutable v2 candidate, time, quality, cost, and gate contract."""

    candidates: list[dict[str, object]] = []
    for symbol in TOURNAMENT_V2_SYMBOLS:
        for spec in _candidate_specs():
            candidate: dict[str, object] = {
                "candidate_id": f"crypto:tournament_v2:{symbol}:{spec.strategy_id}",
                "symbol": symbol,
                "strategy_id": spec.strategy_id,
                "strategy_family": spec.strategy_family,
                "elapsed_hour_parameters": spec.elapsed_parameters(),
                "primary_1h_parameters": spec.timeframe_parameters(1),
                "robustness_4h_parameters": spec.timeframe_parameters(4),
                "direction": "long_or_cash",
                "signal_execution": "one_bar_lag",
                "imputed_bar_transition_policy": "hold_prior_target_no_transition",
                "factory_version": CRYPTO_TOURNAMENT_V2_FACTORY_VERSION,
            }
            candidate["candidate_fingerprint"] = _stable_hash(candidate)
            candidates.append(candidate)

    manifest: dict[str, object] = {
        "schema_version": CRYPTO_TOURNAMENT_V2_SCHEMA_VERSION,
        "factory_version": CRYPTO_TOURNAMENT_V2_FACTORY_VERSION,
        "policy_version": CRYPTO_TOURNAMENT_V2_POLICY_VERSION,
        "gap_policy_version": CRYPTO_TOURNAMENT_V2_GAP_POLICY_VERSION,
        "record_type": "crypto_tournament_v2_preregistration",
        "predecessor_tournament": {
            "version": "v1",
            "status": "closed_terminal_input_quality_gate",
            "preregistration_fingerprint":
                "1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097",
            "candidate_reuse_allowed": False,
            "oos_reuse_allowed": False,
        },
        "symbols": list(TOURNAMENT_V2_SYMBOLS),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "primary_timeframe": PRIMARY_TIMEFRAME,
        "robustness_timeframe": ROBUSTNESS_TIMEFRAME,
        "temporal_policy": {
            "preregistration_must_be_committed_before": OOS_START,
            "discovery_start": DISCOVERY_START,
            "discovery_end_exclusive": DISCOVERY_END_EXCLUSIVE,
            "discovery_expected_hourly_bars_per_symbol": (
                DISCOVERY_EXPECTED_HOURLY_BARS
            ),
            "embargo_start": EMBARGO_START,
            "embargo_end_exclusive": EMBARGO_END_EXCLUSIVE,
            "embargo_role": "causal_signal_warmup_only",
            "embargo_data_must_be_receipt_bound": True,
            "embargo_candidate_metrics_allowed": False,
            "embargo_return_scoring_allowed": False,
            "embargo_completed_round_trip_gate_included": False,
            "embargo_expected_hourly_bars_per_symbol": 24,
            "oos_start": OOS_START,
            "oos_end_inclusive": OOS_END_INCLUSIVE,
            "oos_end_exclusive": OOS_END_EXCLUSIVE,
            "oos_hourly_bars_per_symbol": OOS_HOURLY_BARS,
            "oos_fold_count": OOS_FOLD_COUNT,
            "oos_fold_hourly_bars": OOS_FOLD_HOURLY_BARS,
            "oos_fold_4h_bars": OOS_FOLD_HOURLY_BARS // 4,
            "interim_checkpoints": list(INTERIM_CHECKPOINTS),
            "interim_candidate_metrics_allowed": False,
            "terminal_scoring_not_before": OOS_END_EXCLUSIVE,
            "optional_stopping_allowed": False,
            "window_extension_allowed": False,
        },
        "data_quality_policy": {
            "guarded_refresh_receipt_and_output_sha256_required": True,
            "expected_source": "alpaca_market_data_crypto_bars_v1beta3",
            "embargo_raw_common_grid_required": True,
            "embargo_imputation_allowed": False,
            "embargo_minimum_positive_raw_volume_fraction_per_symbol":
                MINIMUM_POSITIVE_RAW_VOLUME_FRACTION,
            "minimum_raw_hourly_coverage_per_symbol": (
                MINIMUM_RAW_HOURLY_COVERAGE
            ),
            "minimum_positive_raw_volume_fraction_per_symbol": (
                MINIMUM_POSITIVE_RAW_VOLUME_FRACTION
            ),
            "maximum_consecutive_missing_hours": (
                MAXIMUM_CONSECUTIVE_MISSING_HOURS
            ),
            "missing_first_or_last_oos_bar_allowed": False,
            "isolated_gap_fill": "prior_close_ohlc_zero_volume",
            "imputation_must_be_explicit": True,
            "transition_on_imputed_hour_allowed": False,
            "transition_on_4h_bucket_containing_imputation_allowed": False,
            "quality_failure_extends_window": False,
        },
        "cost_policy": {
            "base": {
                "fee_bps_per_transition": BASE_FEE_BPS,
                "slippage_bps_per_transition": BASE_SLIPPAGE_BPS,
                "total_bps_per_transition": BASE_FEE_BPS + BASE_SLIPPAGE_BPS,
            },
            "stress": {
                "fee_bps_per_transition": STRESS_FEE_BPS,
                "slippage_bps_per_transition": STRESS_SLIPPAGE_BPS,
                "total_bps_per_transition": STRESS_FEE_BPS + STRESS_SLIPPAGE_BPS,
            },
        },
        "benchmark_policy": {
            "required": ["cash", "same_symbol_buy_hold", "equal_weight_three_coin_buy_hold"],
            "basket_semantics": "equal_weight_at_oos_start_then_drift_no_rebalancing",
            "base_and_stress_costs_required": True,
        },
        "promotion_gates": {
            "aggregate_oos_base_return_strictly_positive": True,
            "aggregate_oos_stress_return_strictly_positive": True,
            "must_beat_all_benchmarks_under_both_costs": True,
            "max_oos_drawdown": MAX_OOS_DRAWDOWN,
            "drawdown_no_worse_than_risky_benchmarks": True,
            "minimum_positive_oos_folds": MINIMUM_POSITIVE_OOS_FOLDS,
            "max_positive_profit_concentration": MAX_POSITIVE_PROFIT_CONCENTRATION,
            "minimum_completed_round_trips_full_sample": (
                MINIMUM_COMPLETED_ROUND_TRIPS
            ),
            "minimum_oos_transitions": MINIMUM_OOS_TRANSITIONS,
            "four_hour_robustness_required": True,
            "at_most_one_terminal_winner": True,
            "passing_scope": "eligible_for_no_submit_shadow_evaluation",
            "paper_eligibility": False,
            "subsequent_single_winner_untouched_forward_shadow_required": True,
        },
        "dynamic_parameter_optimization": False,
        "post_hoc_retuning": False,
        "candidate_set_mutation_allowed": False,
        "early_promotion_allowed": False,
        "paper_or_live_execution_authorized": False,
        "profit_claim": "none",
    }
    fingerprint = _stable_hash(manifest)
    if fingerprint != CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT:
        raise RuntimeError("crypto tournament v2 preregistration drift detected")
    manifest["preregistration_fingerprint"] = fingerprint
    return manifest


def _stable_hash(value: Mapping[str, object] | object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
