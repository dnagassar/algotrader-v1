"""Preregistered offline high-volatility defense for the V5.64 stock strategy."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research import nexustrade_monthly_independent_replication as _base
from algotrader.research.volatility_regime_evidence import (
    classify_realized_volatility_series,
    compute_realized_volatility_series,
)

__all__ = [
    "NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID",
    "NexusTradeMonthlyHighVolatilityDefenseConfig",
    "build_nexustrade_monthly_high_volatility_defense_preregistration",
    "run_nexustrade_monthly_high_volatility_defense",
]

_PROTOCOL_ID = (
    "v5_65_nexustrade_monthly_independent_high_volatility_defense_v1"
)
_RECORD_TYPE = "nexustrade_monthly_high_volatility_defense_result"
_SCHEMA_VERSION = 1
NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID = (
    "nexustrade_monthly_independent_spy_sma_50_200_high_volatility_defense"
)
_FROZEN_PARENT_ID = _base.NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
_FROZEN_SOURCE_RULE_ID = _base.NEXUSTRADE_MONTHLY_INDEPENDENT_STANDALONE_ID
_SPY_BASELINE_ID = "spy_sma_50_200_baseline"
_STATIC_EQUAL_WEIGHT_ID = "static_equal_weight_11_stock_buy_hold"
_PAIRING_ROLE = "volatility_regime_filter"
_SPY = "SPY"
_ZERO = Decimal("0")
_ONE = Decimal("1")
_STARTING_EQUITY = Decimal("10000")
_VOLATILITY_LOOKBACK = 20
_QUANTILE_MIN_HISTORY = 252
_LOW_QUANTILE = Decimal("0.33")
_HIGH_QUANTILE = Decimal("0.67")
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/v5_65_nexustrade_monthly_high_volatility_defense"
)
_DEFAULT_DATA_PATH = Path(
    "runs/operator_input/multi_etf_adjusted_daily_canonical.csv"
)
_DEFAULT_DATA_MANIFEST_PATH = Path(
    "runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json"
)
_DEFAULT_PREREGISTRATION_PATH = Path(
    "docs/design/v5_65_nexustrade_monthly_high_volatility_defense.md"
)
_DEFAULT_PARENT_PREREGISTRATION_PATH = Path(
    "docs/design/v5_64_nexustrade_monthly_independent_replication.md"
)
_DEFAULT_PARENT_ENGINE_PATH = Path(
    "src/algotrader/research/nexustrade_monthly_independent_replication.py"
)
_EXPECTED_PREREGISTRATION_SHA256 = (
    "1b614cb9d9e310704a0f8adcda224a4c540054a70af2731bcd3ec9c9b44db0c5"
)
_EXPECTED_PARENT_PREREGISTRATION_SHA256 = (
    "f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0"
)
_EXPECTED_PARENT_ENGINE_SHA256 = (
    "66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5"
)
_EXPECTED_DATA_SHA256 = (
    "d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575"
)
_EXPECTED_DATA_MANIFEST_SHA256 = (
    "e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1"
)
_DEFAULT_WALK_FORWARD_WINDOWS = (
    _base.ReplicationWindow(
        "oos_walk_forward_1",
        date(2024, 3, 25),
        date(2024, 7, 24),
    ),
    _base.ReplicationWindow(
        "oos_walk_forward_2",
        date(2024, 7, 25),
        date(2024, 11, 21),
    ),
    _base.ReplicationWindow(
        "oos_walk_forward_3",
        date(2024, 11, 22),
        date(2025, 3, 28),
    ),
)


@dataclass(frozen=True, slots=True)
class NexusTradeMonthlyHighVolatilityDefenseConfig:
    """Fixed inputs for the V5.65 offline high-volatility defense."""

    output_root: Path | str = _DEFAULT_OUTPUT_ROOT
    data_path: Path | str = _DEFAULT_DATA_PATH
    data_manifest_path: Path | str = _DEFAULT_DATA_MANIFEST_PATH
    preregistration_path: Path | str = _DEFAULT_PREREGISTRATION_PATH
    parent_preregistration_path: Path | str = _DEFAULT_PARENT_PREREGISTRATION_PATH
    parent_engine_path: Path | str = _DEFAULT_PARENT_ENGINE_PATH
    expected_preregistration_sha256: str = _EXPECTED_PREREGISTRATION_SHA256
    expected_parent_preregistration_sha256: str = (
        _EXPECTED_PARENT_PREREGISTRATION_SHA256
    )
    expected_parent_engine_sha256: str = _EXPECTED_PARENT_ENGINE_SHA256
    expected_data_sha256: str = _EXPECTED_DATA_SHA256
    expected_data_manifest_sha256: str = _EXPECTED_DATA_MANIFEST_SHA256
    initial_equity: Decimal | str = _STARTING_EQUITY
    data_start: date = date(2019, 1, 2)
    data_end: date = date(2025, 3, 28)
    train_start: date = date(2021, 12, 31)
    train_end: date = date(2024, 3, 24)
    oos_start: date = date(2024, 3, 24)
    oos_end: date = date(2025, 3, 28)
    walk_forward_windows: tuple[_base.ReplicationWindow, ...] = field(
        default_factory=lambda: _DEFAULT_WALK_FORWARD_WINDOWS
    )
    required_common_session_count: int = 1569
    required_oos_session_count: int = 254
    minimum_indicator_sessions: int = 365
    volatility_lookback: int = _VOLATILITY_LOOKBACK
    quantile_min_history: int = _QUANTILE_MIN_HISTORY
    low_quantile: Decimal | str = _LOW_QUANTILE
    high_quantile: Decimal | str = _HIGH_QUANTILE

    def __post_init__(self) -> None:
        for field_name in (
            "output_root",
            "data_path",
            "data_manifest_path",
            "preregistration_path",
            "parent_preregistration_path",
            "parent_engine_path",
        ):
            object.__setattr__(
                self,
                field_name,
                _path(getattr(self, field_name), field_name),
            )
        for field_name in (
            "expected_preregistration_sha256",
            "expected_parent_preregistration_sha256",
            "expected_parent_engine_sha256",
            "expected_data_sha256",
            "expected_data_manifest_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _base._sha256_text(getattr(self, field_name), field_name),
            )
        initial_equity = _base._positive_decimal(
            self.initial_equity,
            "initial_equity",
        )
        if initial_equity != _STARTING_EQUITY:
            raise ValidationError(
                "initial_equity must equal the preregistered value 10000."
            )
        object.__setattr__(self, "initial_equity", initial_equity)
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
                _base._plain_date(getattr(self, field_name), field_name),
            )
        windows = tuple(self.walk_forward_windows)
        if not windows or any(
            type(window) is not _base.ReplicationWindow for window in windows
        ):
            raise ValidationError(
                "walk_forward_windows must contain ReplicationWindow values."
            )
        object.__setattr__(self, "walk_forward_windows", windows)
        for field_name in (
            "required_common_session_count",
            "required_oos_session_count",
            "minimum_indicator_sessions",
        ):
            object.__setattr__(
                self,
                field_name,
                _base._positive_int(getattr(self, field_name), field_name),
            )
        if self.volatility_lookback != _VOLATILITY_LOOKBACK:
            raise ValidationError(
                "volatility_lookback must equal the preregistered value 20."
            )
        if self.quantile_min_history != _QUANTILE_MIN_HISTORY:
            raise ValidationError(
                "quantile_min_history must equal the preregistered value 252."
            )
        low = _decimal(self.low_quantile, "low_quantile")
        high = _decimal(self.high_quantile, "high_quantile")
        if low != _LOW_QUANTILE or high != _HIGH_QUANTILE:
            raise ValidationError(
                "volatility quantiles must equal preregistered values 0.33/0.67."
            )
        object.__setattr__(self, "low_quantile", low)
        object.__setattr__(self, "high_quantile", high)
        self.base_config()

    def base_config(self) -> _base.NexusTradeMonthlyIndependentReplicationConfig:
        """Return the frozen V5.64 mechanics configuration."""

        return _base.NexusTradeMonthlyIndependentReplicationConfig(
            output_root=self.output_root,
            data_path=self.data_path,
            data_manifest_path=self.data_manifest_path,
            preregistration_path=self.parent_preregistration_path,
            expected_preregistration_sha256=(
                self.expected_parent_preregistration_sha256
            ),
            expected_data_sha256=self.expected_data_sha256,
            expected_data_manifest_sha256=self.expected_data_manifest_sha256,
            initial_equity=self.initial_equity,
            data_start=self.data_start,
            data_end=self.data_end,
            train_start=self.train_start,
            train_end=self.train_end,
            oos_start=self.oos_start,
            oos_end=self.oos_end,
            walk_forward_windows=self.walk_forward_windows,
            required_common_session_count=self.required_common_session_count,
            required_oos_session_count=self.required_oos_session_count,
            minimum_indicator_sessions=self.minimum_indicator_sessions,
        )


def build_nexustrade_monthly_high_volatility_defense_preregistration(
    config: NexusTradeMonthlyHighVolatilityDefenseConfig,
) -> dict[str, object]:
    """Build the fixed protocol payload without reading bars or outcomes."""

    checked = _config(config)
    dependency_hashes = _validate_protocol_dependencies(checked)
    return {
        "record_type": "nexustrade_monthly_high_volatility_defense_preregistration",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "claim": "independent_followup_not_authentic_source_replay",
        "tracked_preregistration_path": str(checked.preregistration_path),
        "tracked_preregistration_sha256": dependency_hashes[
            "tracked_preregistration_sha256"
        ],
        "frozen_parent": {
            "candidate_id": _FROZEN_PARENT_ID,
            "source_rule_candidate_id": _FROZEN_SOURCE_RULE_ID,
            "protocol_path": str(checked.parent_preregistration_path),
            "protocol_sha256": dependency_hashes["parent_protocol_sha256"],
            "engine_path": str(checked.parent_engine_path),
            "engine_sha256": dependency_hashes["parent_engine_sha256"],
            "altered": False,
        },
        "candidate_id": NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID,
        "pairing_role": _PAIRING_ROLE,
        "parent_strategy_id": _SPY_BASELINE_ID,
        "baseline_id": _SPY_BASELINE_ID,
        "cross_asset_comparator_id": _STATIC_EQUAL_WEIGHT_ID,
        "parameter_search_performed": False,
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
        "volatility_regime": {
            "symbol": _SPY,
            "return_input": "daily_adjusted_close_simple_returns",
            "rolling_lookback_sessions": checked.volatility_lookback,
            "realized_volatility": "sample_standard_deviation_times_sqrt_252",
            "threshold_history": "expanding_prior_only",
            "threshold_method": "nearest_rank",
            "quantile_min_history": checked.quantile_min_history,
            "low_quantile": _text(checked.low_quantile),
            "high_quantile": _text(checked.high_quantile),
            "forced_cash_regime": "high_vol",
            "insufficient_history_forces_cash": False,
            "parameter_search_performed": False,
        },
        "candidate_rule": {
            "source_rule": "frozen_v5_64_equal_weight_eligible_set",
            "risk_on_condition": (
                "SPY SMA50 > SMA200 and SPY volatility regime != high_vol"
            ),
            "risk_off_target": "cash",
            "fill_price": "next_observed_session_adjusted_close",
            "same_close_fill_allowed": False,
            "overlay_fills_update_candidate_filled_event_state": True,
        },
        "cost_assumptions": [
            item.to_dict() for item in _base._COST_ASSUMPTIONS
        ],
        "gate_policy": {
            "exact_oos_requires_full_oos_and_all_three_folds": True,
            "cross_asset_fold_two_requirement_softened": False,
            "full_oos_drawdown_improvement_required": "0.01",
            "full_oos_return_retention_floor": "-0.02",
            "fold_drawdown_worsening_allowed": False,
            "preview_review_requires_all_applicable_gates": True,
            "paper_promotion_allowed": False,
        },
        "source_metrics_trust": "untrusted_external_evidence",
        "source_metrics_used_for_ranking": False,
        "source_metrics_used_for_promotion": False,
        "holdout_discrepancy_preserved": {
            "table_total_return_percent": "29.64",
            "chart_gain_percent": "29.41",
        },
        "paper_promotion_allowed": False,
        "safety": _safety_payload(),
    }


def run_nexustrade_monthly_high_volatility_defense(
    config: NexusTradeMonthlyHighVolatilityDefenseConfig,
) -> dict[str, object]:
    """Validate, replay, and write deterministic V5.65 artifacts."""

    checked = _config(config)
    checked.output_root.mkdir(parents=True, exist_ok=True)
    preregistration = (
        build_nexustrade_monthly_high_volatility_defense_preregistration(
            checked
        )
    )
    preregistration_path = checked.output_root / "preregistration.json"
    _base._write_json_atomic(preregistration_path, preregistration)

    base_config = checked.base_config()
    data = _base._load_aligned_data(base_config)
    _base._validate_chronology(data, base_config)
    result = _build_result(checked, base_config, data, preregistration)
    result_path = checked.output_root / "defense_results.json"
    _base._write_json_atomic(result_path, result)
    summary_path = checked.output_root / "defense_summary.md"
    _base._write_text_atomic(summary_path, _render_summary(result))
    manifest = _artifact_manifest(
        checked,
        data=data,
        preregistration_path=preregistration_path,
        result_path=result_path,
        summary_path=summary_path,
    )
    manifest_path = checked.output_root / "manifest.json"
    _base._write_json_atomic(manifest_path, manifest)

    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_path"] = str(manifest_path)
    completed["artifact_manifest_sha256"] = _file_sha256(manifest_path)
    return completed


def _build_result(
    config: NexusTradeMonthlyHighVolatilityDefenseConfig,
    base_config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    data: _base._AlignedData,
    preregistration: Mapping[str, object],
) -> dict[str, object]:
    indicators = _base._build_indicators(data)
    volatility_regimes = _build_volatility_regimes(data, config)
    simulations: dict[str, dict[str, _base._Simulation]] = {
        NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID: {},
        _FROZEN_PARENT_ID: {},
        _SPY_BASELINE_ID: {},
        _STATIC_EQUAL_WEIGHT_ID: {},
    }
    for cost in _base._COST_ASSUMPTIONS:
        simulations[
            NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID
        ][cost.cost_id] = _simulate_defense(
            data,
            indicators,
            volatility_regimes,
            base_config,
            cost,
        )
        simulations[_FROZEN_PARENT_ID][cost.cost_id] = (
            _base._simulate_dynamic_candidate(
                data,
                indicators,
                base_config,
                cost,
                composite=True,
            )
        )
        simulations[_SPY_BASELINE_ID][cost.cost_id] = _base._simulate_spy_baseline(
            data,
            indicators,
            base_config,
            cost,
        )
        simulations[_STATIC_EQUAL_WEIGHT_ID][cost.cost_id] = (
            _base._simulate_static_equal_weight(data, base_config, cost)
        )

    windows = _base._reporting_windows(base_config)
    metric_book = {
        strategy_id: {
            cost_id: {
                window.window_id: _base._metrics_for_window(
                    simulation,
                    window,
                    _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
                )
                for window in windows
            }
            for cost_id, simulation in cost_simulations.items()
        }
        for strategy_id, cost_simulations in simulations.items()
    }
    diagnostics = _overlay_diagnostics(
        simulations,
        dict(zip(data.dates, volatility_regimes)),
        windows,
    )
    integrity = _overlay_integrity(
        simulations[NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID][
            "source_fee_only"
        ],
        simulations[_FROZEN_PARENT_ID]["source_fee_only"],
        base_config,
    )
    gates = _candidate_gates(
        metric_book,
        diagnostics,
        integrity,
        base_config,
    )
    cost_results = _base._cost_result_records(
        NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID,
        metric_book,
        simulations,
        windows,
        base_config,
    )
    for cost_result in cost_results:
        cost_result["volatility_overlay_diagnostics"] = diagnostics[
            str(cost_result["cost_id"])
        ]

    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "claim": "independent_followup_not_authentic_source_replay",
        "preregistration": {
            "path": str(config.preregistration_path),
            "sha256": preregistration["tracked_preregistration_sha256"],
            "committed_before_outcome_inspection": True,
        },
        "frozen_parent": dict(preregistration["frozen_parent"]),
        "parameter_search_performed": False,
        "data_contract": {
            "path": str(config.data_path),
            "sha256": data.data_sha256,
            "manifest_path": str(config.data_manifest_path),
            "manifest_sha256": data.data_manifest_sha256,
            "common_session_count": len(data.dates),
            "first_session": data.dates[0].isoformat(),
            "last_session": data.dates[-1].isoformat(),
            "symbols": [*_base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS, _SPY],
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
        "volatility_regime": dict(preregistration["volatility_regime"]),
        "cost_assumptions": [
            item.to_dict() for item in _base._COST_ASSUMPTIONS
        ],
        "candidate": {
            "candidate_id": NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID,
            "claim": "independent_followup_not_authentic_source_replay",
            "role": _PAIRING_ROLE,
            "parent_candidate_ids": [_FROZEN_PARENT_ID],
            "parent_strategy_ids": [_SPY_BASELINE_ID],
            "cost_results": cost_results,
            "gates": gates,
            "route": gates["route"],
            "paper_promotion_allowed": False,
            "source_metrics_used_for_ranking": False,
            "source_metrics_used_for_promotion": False,
        },
        "frozen_parent_cost_results": _base._cost_result_records(
            _FROZEN_PARENT_ID,
            metric_book,
            simulations,
            windows,
            base_config,
        ),
        "comparators": [
            _base._comparator_record(
                comparator_id,
                metric_book,
                simulations,
                windows,
                base_config,
            )
            for comparator_id in (_SPY_BASELINE_ID, _STATIC_EQUAL_WEIGHT_ID)
        ],
        "overlay_integrity": integrity,
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
            "V5.64 is frozen; V5.65 is a separately named local risk-overlay "
            "hypothesis.",
            "Independent assumptions do not establish authentic NexusTrade data "
            "mode, slippage, warm-up, fill behavior, or lineage.",
            "Observed Tiingo SPY dates are the session reference, not an "
            "independent official exchange calendar.",
            "Cash return is zero and no tax, liquidity, lot-size, borrow, or "
            "intraday execution model is included.",
        ],
    }


def _build_volatility_regimes(
    data: _base._AlignedData,
    config: NexusTradeMonthlyHighVolatilityDefenseConfig,
) -> tuple[str, ...]:
    prices = data.prices[_SPY]
    returns = [
        float(current / previous - _ONE)
        for previous, current in zip(prices, prices[1:])
    ]
    realized_returns = compute_realized_volatility_series(
        returns,
        lookback=config.volatility_lookback,
    )
    aligned_realized = (None, *realized_returns)
    classifications = classify_realized_volatility_series(
        aligned_realized,
        quantile_min_history=config.quantile_min_history,
        low_quantile=float(config.low_quantile),
        high_quantile=float(config.high_quantile),
    )
    regimes = tuple(item.regime for item in classifications)
    if len(regimes) != len(data.dates):
        raise ValidationError("volatility regimes do not align to canonical dates.")
    return regimes


def _simulate_defense(
    data: _base._AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    volatility_regimes: Sequence[str],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    cost: _base._CostAssumption,
) -> _base._Simulation:
    start_index = next(
        index for index, item in enumerate(data.dates) if item >= config.train_start
    )
    end_index = max(
        index for index, item in enumerate(data.dates) if item <= config.oos_end
    )
    if start_index == 0:
        raise ValidationError("training requires a prior signal session.")
    current_weights = _base._zero_stock_weights()
    last_filled_buy: date | None = None
    last_filled_sell: date | None = None
    source_desired = _base._eligible_target(data, indicators, start_index - 1)
    risk_on = _defense_risk_on(
        indicators,
        volatility_regimes,
        start_index - 1,
    )
    actual_desired = source_desired if risk_on else _base._zero_stock_weights()
    pending_target: dict[str, Decimal] | None = dict(actual_desired)
    previous_risk_on = risk_on
    records: list[_base._DayRecord] = []

    for index in range(start_index, end_index + 1):
        (
            strategy_return,
            turnover,
            buy_count,
            sell_count,
            exposure,
            contributions,
            current_weights,
        ) = _base._portfolio_step(
            data,
            index,
            current_weights,
            pending_target,
            cost,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        if buy_count:
            last_filled_buy = data.dates[index]
        if sell_count:
            last_filled_sell = data.dates[index]

        rebalance_ready = _base._rebalance_ready(
            data.dates[index],
            last_filled_buy,
            last_filled_sell,
        )
        if rebalance_ready:
            source_desired = _base._eligible_target(data, indicators, index)
        current_risk_on = _defense_risk_on(
            indicators,
            volatility_regimes,
            index,
        )
        actual_desired = (
            source_desired if current_risk_on else _base._zero_stock_weights()
        )
        overlay_changed = current_risk_on != previous_risk_on
        pending_target = (
            dict(actual_desired)
            if rebalance_ready or overlay_changed
            else None
        )
        previous_risk_on = current_risk_on
        records.append(
            _base._DayRecord(
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
    return _base._Simulation(
        strategy_id=NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID,
        cost=cost,
        records=tuple(records),
    )


def _defense_risk_on(
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    volatility_regimes: Sequence[str],
    index: int,
) -> bool:
    return (
        _base._spy_regime_on(indicators, index)
        and volatility_regimes[index] != "high_vol"
    )


def _overlay_diagnostics(
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    regime_by_date: Mapping[date, str],
    windows: Sequence[_base.ReplicationWindow],
) -> dict[str, list[dict[str, object]]]:
    diagnostics: dict[str, list[dict[str, object]]] = {}
    for cost in _base._COST_ASSUMPTIONS:
        candidate = simulations[
            NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID
        ][cost.cost_id]
        parent = simulations[_FROZEN_PARENT_ID][cost.cost_id]
        candidate_by_date = {record.date: record for record in candidate.records}
        parent_by_date = {record.date: record for record in parent.records}
        window_records: list[dict[str, object]] = []
        for window in windows:
            common_dates = sorted(set(candidate_by_date) & set(parent_by_date))
            high_vol_dates = [
                item
                for item in common_dates
                if window.start <= item <= window.end
                and regime_by_date[item] == "high_vol"
            ]
            forced_dates = [
                item
                for item in high_vol_dates
                if _target_exposure(parent_by_date[item]) > _base._WEIGHT_TOLERANCE
                and _target_exposure(candidate_by_date[item])
                <= _base._WEIGHT_TOLERANCE
            ]
            window_records.append(
                {
                    "window_id": window.window_id,
                    "high_volatility_session_count": len(high_vol_dates),
                    "parent_risk_on_high_volatility_forced_cash_session_count": (
                        len(forced_dates)
                    ),
                    "first_forced_cash_date": (
                        None if not forced_dates else forced_dates[0].isoformat()
                    ),
                    "last_forced_cash_date": (
                        None if not forced_dates else forced_dates[-1].isoformat()
                    ),
                }
            )
        diagnostics[cost.cost_id] = window_records
    return diagnostics


def _target_exposure(record: _base._DayRecord) -> Decimal:
    return sum(record.desired_target.values(), _ZERO)


def _overlay_integrity(
    candidate: _base._Simulation,
    parent: _base._Simulation,
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    candidate_by_date = {record.date: record for record in candidate.records}
    parent_by_date = {record.date: record for record in parent.records}
    changed_dates = [
        item
        for item in sorted(set(candidate_by_date) & set(parent_by_date))
        if config.oos_start <= item <= config.oos_end
        and _base._weights_differ(
            candidate_by_date[item].desired_target,
            parent_by_date[item].desired_target,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
    ]
    return {
        "passed": bool(changed_dates),
        "candidate_id": NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID,
        "frozen_parent_candidate_id": _FROZEN_PARENT_ID,
        "pairing_role": _PAIRING_ROLE,
        "oos_target_difference_session_count": len(changed_dates),
        "first_oos_target_difference_date": (
            None if not changed_dates else changed_dates[0].isoformat()
        ),
        "last_oos_target_difference_date": (
            None if not changed_dates else changed_dates[-1].isoformat()
        ),
        "oos_target_difference_dates": [
            item.isoformat() for item in changed_dates
        ],
        "parent_metadata_only": False,
    }


def _candidate_gates(
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    diagnostics: Mapping[str, Sequence[Mapping[str, object]]],
    integrity: Mapping[str, object],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    candidate_id = NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID
    oos_window_ids = (
        "oos",
        *(window.window_id for window in config.walk_forward_windows),
    )
    baseline_window_results = []
    for window_id in oos_window_ids:
        comparison = _base._metric_comparison(
            metric_book[candidate_id]["source_fee_only"][window_id],
            metric_book[_SPY_BASELINE_ID]["source_fee_only"][window_id],
        )
        baseline_window_results.append(
            {
                "window_id": window_id,
                "passed": _base._baseline_window_passed(comparison),
                **comparison,
            }
        )
    baseline_passed = all(item["passed"] for item in baseline_window_results)

    source_candidate = metric_book[candidate_id]["source_fee_only"]["oos"]
    source_baseline = metric_book[_SPY_BASELINE_ID]["source_fee_only"]["oos"]
    moderate_candidate = metric_book[candidate_id]["moderate_friction"]["oos"]
    moderate_baseline = metric_book[_SPY_BASELINE_ID]["moderate_friction"]["oos"]
    source_edge = _base._decimal(source_candidate["total_return"]) - _base._decimal(
        source_baseline["total_return"]
    )
    moderate_edge = _base._decimal(
        moderate_candidate["total_return"]
    ) - _base._decimal(moderate_baseline["total_return"])
    degradation = _base._decimal(
        source_candidate["total_return"]
    ) - _base._decimal(moderate_candidate["total_return"])
    edge_broken = source_edge > _ZERO and moderate_edge <= _ZERO
    cost_passed = (
        _base._decimal(moderate_candidate["total_return"]) > _ZERO
        and moderate_edge > _ZERO
        and not edge_broken
        and degradation < Decimal("0.02")
    )
    cost_gate = {
        "passed": cost_passed,
        "source_fee_oos_total_return": source_candidate["total_return"],
        "moderate_oos_total_return": moderate_candidate["total_return"],
        "source_fee_spy_edge": _base._decimal_text(source_edge),
        "moderate_spy_edge": _base._decimal_text(moderate_edge),
        "edge_broken_by_moderate_cost": edge_broken,
        "return_degradation": _base._decimal_text(degradation),
    }

    cross_window_results = []
    for window_id in oos_window_ids:
        candidate_return = _base._decimal(
            metric_book[candidate_id]["moderate_friction"][window_id][
                "total_return"
            ]
        )
        comparator_return = _base._decimal(
            metric_book[_STATIC_EQUAL_WEIGHT_ID]["moderate_friction"][window_id][
                "total_return"
            ]
        )
        cross_window_results.append(
            {
                "window_id": window_id,
                "candidate_total_return": _base._decimal_text(candidate_return),
                "comparator_total_return": _base._decimal_text(comparator_return),
                "return_delta": _base._decimal_text(
                    candidate_return - comparator_return
                ),
                "passed": candidate_return > comparator_return,
            }
        )
    held_symbols = list(moderate_candidate["symbols_with_nonzero_target"])
    positive_symbols = list(
        moderate_candidate["positive_contribution_symbols"]
    )
    max_share_text = moderate_candidate["max_absolute_contribution_share"]
    max_share = (
        None if max_share_text is None else _base._decimal(max_share_text)
    )
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
        "fold_two_requirement_softened": False,
    }

    parent_full = metric_book[_FROZEN_PARENT_ID]["moderate_friction"]["oos"]
    parent_comparison = _base._metric_comparison(
        moderate_candidate,
        parent_full,
    )
    full_drawdown_delta = _base._decimal(
        parent_comparison["max_drawdown_delta"]
    )
    return_delta = _base._decimal(parent_comparison["total_return_delta"])
    sharpe_text = parent_comparison["sharpe_ratio_delta"]
    sharpe_delta = (
        None if sharpe_text is None else _base._decimal(sharpe_text)
    )
    fold_drawdown_results = []
    for window_id in (
        window.window_id for window in config.walk_forward_windows
    ):
        comparison = _base._metric_comparison(
            metric_book[candidate_id]["moderate_friction"][window_id],
            metric_book[_FROZEN_PARENT_ID]["moderate_friction"][window_id],
        )
        drawdown_delta = _base._decimal(comparison["max_drawdown_delta"])
        fold_drawdown_results.append(
            {
                "window_id": window_id,
                "candidate_max_drawdown": metric_book[candidate_id][
                    "moderate_friction"
                ][window_id]["max_drawdown"],
                "parent_max_drawdown": metric_book[_FROZEN_PARENT_ID][
                    "moderate_friction"
                ][window_id]["max_drawdown"],
                "max_drawdown_delta": comparison["max_drawdown_delta"],
                "passed": drawdown_delta <= _ZERO,
            }
        )
    moderate_oos_diagnostics = next(
        item
        for item in diagnostics["moderate_friction"]
        if item["window_id"] == "oos"
    )
    forced_cash_count = int(
        moderate_oos_diagnostics[
            "parent_risk_on_high_volatility_forced_cash_session_count"
        ]
    )
    repair_passed = (
        integrity["passed"] is True
        and full_drawdown_delta <= Decimal("-0.01")
        and all(item["passed"] for item in fold_drawdown_results)
        and return_delta >= Decimal("-0.02")
        and (sharpe_delta is None or sharpe_delta >= _ZERO)
        and forced_cash_count > 0
    )
    repair_gate = {
        "passed": repair_passed,
        "integrity": dict(integrity),
        "moderate_friction_oos_comparison_to_frozen_parent": parent_comparison,
        "full_oos_drawdown_improvement_at_least_0_01": (
            full_drawdown_delta <= Decimal("-0.01")
        ),
        "full_oos_return_delta_at_least_negative_0_02": (
            return_delta >= Decimal("-0.02")
        ),
        "full_oos_sharpe_nonnegative_delta": (
            sharpe_delta is None or sharpe_delta >= _ZERO
        ),
        "fold_drawdown_results": fold_drawdown_results,
        "forced_cash_session_count": forced_cash_count,
        "forced_cash_required": True,
    }

    all_passed = (
        baseline_passed
        and cost_passed
        and cross_asset_passed
        and repair_passed
    )
    nonpositive_oos = _base._decimal(
        source_candidate["total_return"]
    ) <= _ZERO
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
            "passed": baseline_passed,
            "baseline_id": _SPY_BASELINE_ID,
            "cost_id": "source_fee_only",
            "window_results": baseline_window_results,
        },
        "cost_gate": cost_gate,
        "portfolio_level_cross_asset_gate": cross_asset_gate,
        "targeted_parent_repair_gate": repair_gate,
        "all_applicable_gates_passed": all_passed,
        "route": route,
        "paper_promotion_allowed": False,
    }


def _validate_protocol_dependencies(
    config: NexusTradeMonthlyHighVolatilityDefenseConfig,
) -> dict[str, str]:
    values = {
        "tracked_preregistration_sha256": (
            config.preregistration_path,
            config.expected_preregistration_sha256,
        ),
        "parent_protocol_sha256": (
            config.parent_preregistration_path,
            config.expected_parent_preregistration_sha256,
        ),
        "parent_engine_sha256": (
            config.parent_engine_path,
            config.expected_parent_engine_sha256,
        ),
    }
    verified: dict[str, str] = {}
    for field_name, (path, expected) in values.items():
        actual = _file_sha256(path)
        if actual != expected:
            raise ValidationError(
                f"{field_name} does not match the preregistered dependency."
            )
        verified[field_name] = actual
    return verified


def _artifact_manifest(
    config: NexusTradeMonthlyHighVolatilityDefenseConfig,
    *,
    data: _base._AlignedData,
    preregistration_path: Path,
    result_path: Path,
    summary_path: Path,
) -> dict[str, object]:
    return {
        "record_type": "nexustrade_monthly_high_volatility_defense_manifest",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "artifacts": [
            _artifact_record(preregistration_path),
            _artifact_record(result_path),
            _artifact_record(summary_path),
        ],
        "inputs": [
            _artifact_record(config.preregistration_path),
            _artifact_record(config.parent_preregistration_path),
            _artifact_record(config.parent_engine_path),
            {
                "path": str(config.data_path),
                "sha256": data.data_sha256,
                "bytes": config.data_path.stat().st_size,
            },
            {
                "path": str(config.data_manifest_path),
                "sha256": data.data_manifest_sha256,
                "bytes": config.data_manifest_path.stat().st_size,
            },
        ],
        "manifest_self_hash_embedded": False,
        "parameter_search_performed": False,
        "paper_promotion_allowed": False,
        "safety": _safety_payload(),
    }


def _artifact_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "bytes": path.stat().st_size,
    }


def _render_summary(result: Mapping[str, object]) -> str:
    candidate = _mapping(result["candidate"], "candidate")
    gates = _mapping(candidate["gates"], "candidate.gates")
    lines = [
        "# V5.65 NexusTrade Monthly High-Volatility Defense",
        "",
        f"- Protocol: `{result['protocol_id']}`",
        f"- Candidate: `{candidate['candidate_id']}`",
        f"- Route: `{candidate['route']}`",
        "- Claim: independent follow-up; not an authentic NexusTrade replay.",
        "- V5.64 frozen: `true`.",
        "- Parameter search performed: `false`.",
        "- Source metrics trust: `untrusted_external_evidence`.",
        "- Source metrics used for ranking or promotion: `false`.",
        "",
        "## Gate decisions",
        "",
        (
            "- SPY baseline OOS gate: "
            f"`{_mapping(gates['baseline_oos_gate'], 'baseline gate')['passed']}`."
        ),
        (
            "- Cost gate: "
            f"`{_mapping(gates['cost_gate'], 'cost gate')['passed']}`."
        ),
        (
            "- Portfolio-level cross-asset gate: "
            f"`{_mapping(gates['portfolio_level_cross_asset_gate'], 'cross gate')['passed']}`."
        ),
        (
            "- Targeted parent-repair gate: "
            f"`{_mapping(gates['targeted_parent_repair_gate'], 'repair gate')['passed']}`."
        ),
        "",
        "## Safety",
        "",
        "- Network access: `false`.",
        "- Credential access: `false`.",
        "- Broker access: `false`.",
        "- Paper mutation: `false`.",
        "- Live activity: `false`.",
        "- Paper promotion: `false`.",
        "",
    ]
    return "\n".join(lines)


def _safety_payload() -> dict[str, object]:
    return {
        **_base._safety_payload(),
        "v5_64_frozen": True,
        "parameter_search_performed": False,
        "paper_submission_performed": False,
        "no_submit_shadow_created": False,
        "v5_57_sleeve_ownership_unchanged": True,
        "v5_57_reconciliation_unchanged": True,
        "v5_57_auditing_unchanged": True,
        "v5_57_caps_unchanged": True,
        "max_entry_order_notional_usd": "25",
        "max_aggregate_marked_spy_entry_exposure_usd": "60",
        "max_broker_orders_per_secure_cycle": 1,
        "max_sleeve_intents_per_utc_day": 2,
    }


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file is missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str) and value.strip():
        path = Path(value.strip())
    else:
        raise ValidationError(f"{field_name} must be a path.")
    return path


def _decimal(value: Decimal | str, field_name: str) -> Decimal:
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise ValidationError(f"{field_name} must be decimal-compatible.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return parsed


def _text(value: Decimal) -> str:
    return _base._decimal_text(value)


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _config(
    value: NexusTradeMonthlyHighVolatilityDefenseConfig,
) -> NexusTradeMonthlyHighVolatilityDefenseConfig:
    if type(value) is not NexusTradeMonthlyHighVolatilityDefenseConfig:
        raise ValidationError(
            "config must be NexusTradeMonthlyHighVolatilityDefenseConfig."
        )
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the preregistered offline NexusTrade monthly high-volatility "
            "defense."
        )
    )
    parser.add_argument("--output-root", type=Path, default=_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--data-path", type=Path, default=_DEFAULT_DATA_PATH)
    parser.add_argument(
        "--data-manifest-path",
        type=Path,
        default=_DEFAULT_DATA_MANIFEST_PATH,
    )
    parser.add_argument(
        "--preregistration-path",
        type=Path,
        default=_DEFAULT_PREREGISTRATION_PATH,
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config = NexusTradeMonthlyHighVolatilityDefenseConfig(
        output_root=args.output_root,
        data_path=args.data_path,
        data_manifest_path=args.data_manifest_path,
        preregistration_path=args.preregistration_path,
    )
    result = run_nexustrade_monthly_high_volatility_defense(config)
    if args.format == "json":
        print(json.dumps(_base._json_safe(result), indent=2, sort_keys=True))
    else:
        candidate = _mapping(result["candidate"], "candidate")
        print("nexustrade_monthly_high_volatility_defense_status=completed")
        print(f"candidate_id={candidate['candidate_id']}")
        print(f"route={candidate['route']}")
        print(f"artifact_manifest_path={result['artifact_manifest_path']}")
        print(
            "artifact_manifest_sha256="
            f"{result['artifact_manifest_sha256']}"
        )
        print("parameter_search_performed=false")
        print("paper_promotion_allowed=false")
        print("network_access_attempted=false")
        print("credential_access_attempted=false")
        print("broker_access_attempted=false")
        print("paper_mutation_performed=false")
        print("live_activity_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
