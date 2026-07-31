"""Preregistered offline risk-balanced allocation for the V5.64 stock filter."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research import nexustrade_monthly_independent_replication as _base

__all__ = [
    "NEXUSTRADE_MONTHLY_RISK_BALANCED_ID",
    "NexusTradeMonthlyRiskBalancedConfig",
    "build_nexustrade_monthly_risk_balanced_preregistration",
    "run_nexustrade_monthly_risk_balanced_allocation",
]


_PROTOCOL_ID = "v5_67_nexustrade_monthly_risk_balanced_allocation_v1"
_RECORD_TYPE = "nexustrade_monthly_risk_balanced_allocation_result"
_SCHEMA_VERSION = 1
NEXUSTRADE_MONTHLY_RISK_BALANCED_ID = (
    "nexustrade_monthly_independent_spy_sma_50_200_"
    "inverse_volatility_capped"
)
_FROZEN_PARENT_ID = _base.NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
_SPY_BASELINE_ID = "spy_sma_50_200_baseline"
_STATIC_EQUAL_WEIGHT_ID = "static_equal_weight_11_stock_buy_hold"
_PAIRING_ROLE = "risk_balanced_portfolio_construction"
_SPY = "SPY"
_ZERO = Decimal("0")
_ONE = Decimal("1")
_STARTING_EQUITY = Decimal("10000")
_VOLATILITY_LOOKBACK = 60
_MAX_TARGET_WEIGHT = Decimal("0.20")
_TOLERANCE = Decimal("1e-18")
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/v5_67_nexustrade_monthly_risk_balanced_allocation"
)
_DEFAULT_DATA_PATH = Path(
    "runs/operator_input/multi_etf_adjusted_daily_canonical.csv"
)
_DEFAULT_DATA_MANIFEST_PATH = Path(
    "runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json"
)
_DEFAULT_PREREGISTRATION_PATH = Path(
    "docs/design/v5_67_nexustrade_monthly_risk_balanced_allocation.md"
)
_DEFAULT_PARENT_PROTOCOL_PATH = Path(
    "docs/design/v5_64_nexustrade_monthly_independent_replication.md"
)
_DEFAULT_PARENT_ENGINE_PATH = Path(
    "src/algotrader/research/nexustrade_monthly_independent_replication.py"
)
_DEFAULT_PARENT_ROOT = Path(
    "runs/v5_64_nexustrade_monthly_independent_replication"
)
_DEFAULT_V566_PROTOCOL_PATH = Path(
    "docs/design/v5_66_nexustrade_high_volatility_attribution.md"
)
_EXPECTED_PREREGISTRATION_SHA256 = (
    "17f86b8eafd7e67e6816603cb1bf06fa96a734c7b7d9094d30e68ec85690505e"
)
_EXPECTED_PARENT_PROTOCOL_SHA256 = (
    "f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0"
)
_EXPECTED_PARENT_ENGINE_SHA256 = (
    "66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5"
)
_EXPECTED_PARENT_PREREGISTRATION_SHA256 = (
    "4c54d6c14de2579d1671a8257be6750bd49a586296d041fea95a3fe40e376e3c"
)
_EXPECTED_PARENT_RESULT_SHA256 = (
    "ca9f0177b0b42a3ec888b13799fdd3d39c5c5ae9caacedd2245a0292b42396da"
)
_EXPECTED_PARENT_SUMMARY_SHA256 = (
    "af3b527db055c4568db7125047dad97ba9492fa55d5bbf2c3a6b6cc9002f41df"
)
_EXPECTED_PARENT_MANIFEST_SHA256 = (
    "96338ea291f40ea7d9a1ea4a0d45dd17ed5a60c856333150655701f64841dcf6"
)
_EXPECTED_V566_PROTOCOL_SHA256 = (
    "2a2d03030b2ec74ca3a0682ca94163ea5b28218c1b452b4f10664fc182733227"
)
_EXPECTED_DATA_SHA256 = (
    "d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575"
)
_EXPECTED_DATA_MANIFEST_SHA256 = (
    "e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1"
)
_DEFAULT_WALK_FORWARD_WINDOWS = (
    _base.ReplicationWindow(
        "oos_walk_forward_1", date(2024, 3, 25), date(2024, 7, 24)
    ),
    _base.ReplicationWindow(
        "oos_walk_forward_2", date(2024, 7, 25), date(2024, 11, 21)
    ),
    _base.ReplicationWindow(
        "oos_walk_forward_3", date(2024, 11, 22), date(2025, 3, 28)
    ),
)


@dataclass(frozen=True, slots=True)
class NexusTradeMonthlyRiskBalancedConfig:
    """Pinned inputs for the V5.67 offline candidate."""

    output_root: Path | str = _DEFAULT_OUTPUT_ROOT
    data_path: Path | str = _DEFAULT_DATA_PATH
    data_manifest_path: Path | str = _DEFAULT_DATA_MANIFEST_PATH
    preregistration_path: Path | str = _DEFAULT_PREREGISTRATION_PATH
    parent_protocol_path: Path | str = _DEFAULT_PARENT_PROTOCOL_PATH
    parent_engine_path: Path | str = _DEFAULT_PARENT_ENGINE_PATH
    parent_preregistration_path: Path | str = (
        _DEFAULT_PARENT_ROOT / "preregistration.json"
    )
    parent_result_path: Path | str = (
        _DEFAULT_PARENT_ROOT / "replication_results.json"
    )
    parent_summary_path: Path | str = (
        _DEFAULT_PARENT_ROOT / "replication_summary.md"
    )
    parent_manifest_path: Path | str = _DEFAULT_PARENT_ROOT / "manifest.json"
    v566_protocol_path: Path | str = _DEFAULT_V566_PROTOCOL_PATH
    expected_preregistration_sha256: str = _EXPECTED_PREREGISTRATION_SHA256
    expected_parent_protocol_sha256: str = _EXPECTED_PARENT_PROTOCOL_SHA256
    expected_parent_engine_sha256: str = _EXPECTED_PARENT_ENGINE_SHA256
    expected_parent_preregistration_sha256: str = (
        _EXPECTED_PARENT_PREREGISTRATION_SHA256
    )
    expected_parent_result_sha256: str = _EXPECTED_PARENT_RESULT_SHA256
    expected_parent_summary_sha256: str = _EXPECTED_PARENT_SUMMARY_SHA256
    expected_parent_manifest_sha256: str = _EXPECTED_PARENT_MANIFEST_SHA256
    expected_v566_protocol_sha256: str = _EXPECTED_V566_PROTOCOL_SHA256
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
    max_target_weight: Decimal | str = _MAX_TARGET_WEIGHT

    def __post_init__(self) -> None:
        for name in (
            "output_root",
            "data_path",
            "data_manifest_path",
            "preregistration_path",
            "parent_protocol_path",
            "parent_engine_path",
            "parent_preregistration_path",
            "parent_result_path",
            "parent_summary_path",
            "parent_manifest_path",
            "v566_protocol_path",
        ):
            object.__setattr__(self, name, _path(getattr(self, name), name))
        for name in (
            "expected_preregistration_sha256",
            "expected_parent_protocol_sha256",
            "expected_parent_engine_sha256",
            "expected_parent_preregistration_sha256",
            "expected_parent_result_sha256",
            "expected_parent_summary_sha256",
            "expected_parent_manifest_sha256",
            "expected_v566_protocol_sha256",
            "expected_data_sha256",
            "expected_data_manifest_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _base._sha256_text(getattr(self, name), name),
            )
        equity = _base._positive_decimal(self.initial_equity, "initial_equity")
        if equity != _STARTING_EQUITY:
            raise ValidationError(
                "initial_equity must equal the preregistered value 10000."
            )
        object.__setattr__(self, "initial_equity", equity)
        for name in (
            "data_start",
            "data_end",
            "train_start",
            "train_end",
            "oos_start",
            "oos_end",
        ):
            object.__setattr__(
                self,
                name,
                _base._plain_date(getattr(self, name), name),
            )
        windows = tuple(self.walk_forward_windows)
        if len(windows) != 3 or any(
            type(item) is not _base.ReplicationWindow for item in windows
        ):
            raise ValidationError(
                "walk_forward_windows must contain three ReplicationWindow values."
            )
        object.__setattr__(self, "walk_forward_windows", windows)
        for name in (
            "required_common_session_count",
            "required_oos_session_count",
            "minimum_indicator_sessions",
        ):
            object.__setattr__(
                self,
                name,
                _base._positive_int(getattr(self, name), name),
            )
        if self.volatility_lookback != _VOLATILITY_LOOKBACK:
            raise ValidationError(
                "volatility_lookback must equal the preregistered value 60."
            )
        cap = _decimal(self.max_target_weight, "max_target_weight")
        if cap != _MAX_TARGET_WEIGHT:
            raise ValidationError(
                "max_target_weight must equal the preregistered value 0.20."
            )
        object.__setattr__(self, "max_target_weight", cap)
        self.base_config()

    def base_config(self) -> _base.NexusTradeMonthlyIndependentReplicationConfig:
        """Return the frozen V5.64 mechanics configuration."""

        return _base.NexusTradeMonthlyIndependentReplicationConfig(
            output_root=self.output_root,
            data_path=self.data_path,
            data_manifest_path=self.data_manifest_path,
            preregistration_path=self.parent_protocol_path,
            expected_preregistration_sha256=self.expected_parent_protocol_sha256,
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


def build_nexustrade_monthly_risk_balanced_preregistration(
    config: NexusTradeMonthlyRiskBalancedConfig,
) -> dict[str, object]:
    """Build the fixed protocol payload without reading bars or outcomes."""

    checked = _config(config)
    protocol_hashes = _validate_protocol_dependencies(checked)
    return {
        "record_type": "nexustrade_monthly_risk_balanced_preregistration",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "claim": "independent_candidate_not_authentic_source_replay",
        "tracked_preregistration_path": str(checked.preregistration_path),
        "tracked_preregistration_sha256": protocol_hashes[
            "tracked_preregistration_sha256"
        ],
        "candidate_id": NEXUSTRADE_MONTHLY_RISK_BALANCED_ID,
        "candidate_role": _PAIRING_ROLE,
        "frozen_parent": {
            "candidate_id": _FROZEN_PARENT_ID,
            "protocol_path": str(checked.parent_protocol_path),
            "protocol_sha256": protocol_hashes["parent_protocol_sha256"],
            "engine_path": str(checked.parent_engine_path),
            "engine_sha256": protocol_hashes["parent_engine_sha256"],
            "preregistration_path": str(checked.parent_preregistration_path),
            "preregistration_sha256": (
                checked.expected_parent_preregistration_sha256
            ),
            "result_path": str(checked.parent_result_path),
            "result_sha256": checked.expected_parent_result_sha256,
            "summary_path": str(checked.parent_summary_path),
            "summary_sha256": checked.expected_parent_summary_sha256,
            "manifest_path": str(checked.parent_manifest_path),
            "manifest_sha256": checked.expected_parent_manifest_sha256,
            "exact_structured_reproduction_required": True,
        },
        "excluded_overlay_lane": {
            "v566_protocol_path": str(checked.v566_protocol_path),
            "v566_protocol_sha256": protocol_hashes["v566_protocol_sha256"],
            "v565_or_v566_signal_reused": False,
        },
        "data_contract": {
            "data_path": str(checked.data_path),
            "data_manifest_path": str(checked.data_manifest_path),
            "expected_data_sha256": checked.expected_data_sha256,
            "expected_data_manifest_sha256": (
                checked.expected_data_manifest_sha256
            ),
            "price_field": "adjusted_close",
            "provider_source_field": "adjClose",
            "adjustment_semantics": "split_and_dividend_adjusted_eod_price",
            "adjusted_ohlcv_claimed": False,
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
                item.to_dict() for item in checked.walk_forward_windows
            ],
            "state_reset_at_window_boundary": False,
        },
        "source_rule_building_block": {
            "stock_symbols": list(_base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS),
            "eligibility_logic": "exactly_one_or_two_of_three_v564_clauses",
            "sma_window_sessions": 30,
            "minimum_window_observed_sessions": 365,
            "rsi_period_close_changes": 14,
            "stock_rsi_below": "28",
            "spy_rsi_above": "33",
            "near_minimum_ratio_at_most": "1.05",
            "rebalance_rule": (
                "30 calendar days since own last filled buy OR own last filled sell"
            ),
        },
        "allocation": {
            "method": "inverse_sample_volatility_capped_water_fill",
            "return_type": "simple_adjusted_close_return",
            "volatility_lookback_returns": checked.volatility_lookback,
            "required_adjusted_close_count": checked.volatility_lookback + 1,
            "sample_variance_denominator": checked.volatility_lookback - 1,
            "annualized_for_weighting": False,
            "volatility_floor": None,
            "max_target_weight": _text(checked.max_target_weight),
            "maximum_stock_exposure": "min(1,0.20*eligible_count)",
            "residual_held_as_cash": True,
            "canonical_symbol_order_tie_break": True,
        },
        "parent_regime": {
            "strategy_id": _SPY_BASELINE_ID,
            "rule": "SPY adjusted-close SMA50 strictly above SMA200",
            "risk_off_target": "cash",
        },
        "fill_assumptions": {
            "signal_price": "current_session_adjusted_close",
            "fill_price": "next_observed_session_adjusted_close",
            "same_close_fill_allowed": False,
            "cash_return": "0",
            "weights_drift_between_fills": True,
        },
        "cost_assumptions": [
            item.to_dict() for item in _base._COST_ASSUMPTIONS
        ],
        "comparators": [
            _FROZEN_PARENT_ID,
            _SPY_BASELINE_ID,
            _STATIC_EQUAL_WEIGHT_ID,
        ],
        "gate_policy": _gate_policy_payload(),
        "parameter_search_performed": False,
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


def run_nexustrade_monthly_risk_balanced_allocation(
    config: NexusTradeMonthlyRiskBalancedConfig,
) -> dict[str, object]:
    """Validate, replay, and write deterministic V5.67 artifacts."""

    checked = _config(config)
    preregistration = build_nexustrade_monthly_risk_balanced_preregistration(
        checked
    )
    parent_hashes = _validate_parent_artifacts(checked)
    base_config = checked.base_config()
    data = _base._load_aligned_data(base_config)
    _base._validate_chronology(data, base_config)
    parent_reproduction = _reproduce_frozen_parent(
        checked,
        base_config,
        data,
        parent_hashes,
    )

    checked.output_root.mkdir(parents=True, exist_ok=True)
    preregistration_path = checked.output_root / "preregistration.json"
    _base._write_json_atomic(preregistration_path, preregistration)
    result = _build_result(
        checked,
        base_config,
        data,
        preregistration,
        parent_reproduction,
    )
    result_path = checked.output_root / "risk_balanced_results.json"
    _base._write_json_atomic(result_path, result)
    summary_path = checked.output_root / "risk_balanced_summary.md"
    _base._write_text_atomic(summary_path, _render_summary(result))
    manifest = _artifact_manifest(
        checked,
        data,
        preregistration_path,
        result_path,
        summary_path,
    )
    manifest_path = checked.output_root / "manifest.json"
    _base._write_json_atomic(manifest_path, manifest)

    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_path"] = str(manifest_path)
    completed["artifact_manifest_sha256"] = _file_sha256(manifest_path)
    return completed


def _build_result(
    config: NexusTradeMonthlyRiskBalancedConfig,
    base_config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    data: _base._AlignedData,
    preregistration: Mapping[str, object],
    parent_reproduction: Mapping[str, object],
) -> dict[str, object]:
    indicators = _base._build_indicators(data)
    simulations: dict[str, dict[str, _base._Simulation]] = {
        NEXUSTRADE_MONTHLY_RISK_BALANCED_ID: {},
        _FROZEN_PARENT_ID: {},
        _SPY_BASELINE_ID: {},
        _STATIC_EQUAL_WEIGHT_ID: {},
    }
    for cost in _base._COST_ASSUMPTIONS:
        simulations[NEXUSTRADE_MONTHLY_RISK_BALANCED_ID][cost.cost_id] = (
            _simulate_risk_balanced_candidate(
                data,
                indicators,
                base_config,
                cost,
                volatility_lookback=config.volatility_lookback,
                max_target_weight=config.max_target_weight,
            )
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
        simulations[_SPY_BASELINE_ID][cost.cost_id] = (
            _base._simulate_spy_baseline(data, indicators, base_config, cost)
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
    integrity = _allocation_integrity(
        simulations[NEXUSTRADE_MONTHLY_RISK_BALANCED_ID]["source_fee_only"],
        simulations[_FROZEN_PARENT_ID]["source_fee_only"],
        base_config,
        config.max_target_weight,
    )
    gates = _candidate_gates(metric_book, integrity, base_config)

    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "claim": "independent_candidate_not_authentic_source_replay",
        "preregistration": {
            "path": str(config.preregistration_path),
            "sha256": preregistration["tracked_preregistration_sha256"],
            "committed_before_outcome_inspection": True,
        },
        "frozen_parent": dict(preregistration["frozen_parent"]),
        "frozen_parent_reproduction": dict(parent_reproduction),
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
            "adjustment_semantics": "split_and_dividend_adjusted_eod_price",
            "brk_b_mapping": "BRK-B->BRK-B",
        },
        "chronology": {
            "train_start": config.train_start.isoformat(),
            "train_end": config.train_end.isoformat(),
            "oos_start": config.oos_start.isoformat(),
            "oos_end": config.oos_end.isoformat(),
            "walk_forward_windows": [
                item.to_dict() for item in config.walk_forward_windows
            ],
            "state_reset_at_window_boundary": False,
        },
        "allocation": dict(preregistration["allocation"]),
        "cost_assumptions": [
            item.to_dict() for item in _base._COST_ASSUMPTIONS
        ],
        "candidate": {
            "candidate_id": NEXUSTRADE_MONTHLY_RISK_BALANCED_ID,
            "role": _PAIRING_ROLE,
            "parent_candidate_ids": [_FROZEN_PARENT_ID],
            "parent_strategy_ids": [_SPY_BASELINE_ID],
            "cost_results": _base._cost_result_records(
                NEXUSTRADE_MONTHLY_RISK_BALANCED_ID,
                metric_book,
                simulations,
                windows,
                base_config,
            ),
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
        "allocation_integrity": integrity,
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
            "The candidate is independently designed and is not an authentic "
            "NexusTrade replay or lineage claim.",
            "Local assumptions do not establish authentic historical data mode, "
            "slippage, warm-up, fill behavior, or 365-day clock semantics.",
            "Observed Tiingo SPY dates are the session reference, not an "
            "independent official exchange calendar.",
            "Cash return is zero and no tax, liquidity, lot-size, borrow, or "
            "intraday execution model is included.",
        ],
    }


def _simulate_risk_balanced_candidate(
    data: _base._AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    cost: _base._CostAssumption,
    *,
    volatility_lookback: int,
    max_target_weight: Decimal,
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
    source_desired = _risk_balanced_target(
        data,
        indicators,
        start_index - 1,
        volatility_lookback=volatility_lookback,
        max_target_weight=max_target_weight,
    )
    regime_on = _base._spy_regime_on(indicators, start_index - 1)
    actual_desired = (
        source_desired if regime_on else _base._zero_stock_weights()
    )
    pending_target: dict[str, Decimal] | None = dict(actual_desired)
    previous_regime_on = regime_on
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
            source_desired = _risk_balanced_target(
                data,
                indicators,
                index,
                volatility_lookback=volatility_lookback,
                max_target_weight=max_target_weight,
            )
        current_regime_on = _base._spy_regime_on(indicators, index)
        actual_desired = (
            source_desired
            if current_regime_on
            else _base._zero_stock_weights()
        )
        overlay_changed = current_regime_on != previous_regime_on
        pending_target = (
            dict(actual_desired)
            if rebalance_ready or overlay_changed
            else None
        )
        previous_regime_on = current_regime_on
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
        strategy_id=NEXUSTRADE_MONTHLY_RISK_BALANCED_ID,
        cost=cost,
        records=tuple(records),
    )


def _risk_balanced_target(
    data: _base._AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    index: int,
    *,
    volatility_lookback: int = _VOLATILITY_LOOKBACK,
    max_target_weight: Decimal = _MAX_TARGET_WEIGHT,
) -> dict[str, Decimal]:
    equal_weight_target = _base._eligible_target(data, indicators, index)
    eligible = tuple(
        symbol
        for symbol in _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
        if equal_weight_target[symbol] > _TOLERANCE
    )
    if not eligible:
        return _base._zero_stock_weights()
    scores = {
        symbol: _ONE
        / _sample_volatility(
            data.prices[symbol],
            index,
            volatility_lookback,
        )
        for symbol in eligible
    }
    allocated = _capped_water_fill(
        eligible,
        scores,
        max_target_weight=max_target_weight,
    )
    target = {
        symbol: allocated.get(symbol, _ZERO)
        for symbol in _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
    }
    _base._validate_target_weights(
        target,
        _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
    )
    if any(weight > max_target_weight + _TOLERANCE for weight in target.values()):
        raise ValidationError("risk-balanced target exceeds the weight cap.")
    return target


def _sample_volatility(
    prices: Sequence[Decimal],
    index: int,
    lookback: int,
) -> Decimal:
    if lookback != _VOLATILITY_LOOKBACK:
        raise ValidationError("volatility lookback must remain 60 returns.")
    start = index - lookback
    if start < 0:
        raise ValidationError("insufficient adjusted-close volatility history.")
    returns = tuple(
        prices[item] / prices[item - 1] - _ONE
        for item in range(start + 1, index + 1)
    )
    if len(returns) != lookback:
        raise ValidationError("volatility window does not contain 60 returns.")
    mean = sum(returns, _ZERO) / Decimal(lookback)
    variance = sum(((item - mean) ** 2 for item in returns), _ZERO) / Decimal(
        lookback - 1
    )
    if not variance.is_finite() or variance <= _ZERO:
        raise ValidationError("eligible symbol volatility must be finite and positive.")
    volatility = variance.sqrt()
    if not volatility.is_finite() or volatility <= _ZERO:
        raise ValidationError("eligible symbol volatility must be finite and positive.")
    return volatility


def _capped_water_fill(
    eligible: Sequence[str],
    scores: Mapping[str, Decimal],
    *,
    max_target_weight: Decimal = _MAX_TARGET_WEIGHT,
) -> dict[str, Decimal]:
    ordered = tuple(
        symbol
        for symbol in _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
        if symbol in set(eligible)
    )
    if len(ordered) != len(tuple(eligible)) or not ordered:
        raise ValidationError("eligible symbols must be unique canonical stocks.")
    for symbol in ordered:
        score = scores.get(symbol)
        if score is None or not score.is_finite() or score <= _ZERO:
            raise ValidationError("inverse-volatility scores must be finite and positive.")
    target_exposure = min(_ONE, max_target_weight * Decimal(len(ordered)))
    remaining = list(ordered)
    remaining_mass = target_exposure
    weights: dict[str, Decimal] = {}
    while remaining:
        score_sum = sum((scores[symbol] for symbol in remaining), _ZERO)
        if score_sum <= _ZERO:
            raise ValidationError("remaining inverse-volatility score is nonpositive.")
        provisional = {
            symbol: remaining_mass * scores[symbol] / score_sum
            for symbol in remaining
        }
        capped = tuple(
            symbol
            for symbol in remaining
            if provisional[symbol] > max_target_weight
        )
        if not capped:
            weights.update(provisional)
            break
        for symbol in capped:
            weights[symbol] = max_target_weight
        remaining_mass -= max_target_weight * Decimal(len(capped))
        if remaining_mass < -_TOLERANCE:
            raise ValidationError("capped allocation produced negative remaining mass.")
        remaining = [symbol for symbol in remaining if symbol not in capped]
    if any(weight < _ZERO for weight in weights.values()):
        raise ValidationError("capped allocation produced a negative weight.")
    if any(weight > max_target_weight + _TOLERANCE for weight in weights.values()):
        raise ValidationError("capped allocation exceeded the maximum weight.")
    exposure = sum(weights.values(), _ZERO)
    if abs(exposure - target_exposure) > _TOLERANCE:
        raise ValidationError("capped allocation did not conserve target exposure.")
    return {symbol: weights[symbol] for symbol in ordered}


def _allocation_integrity(
    candidate: _base._Simulation,
    parent: _base._Simulation,
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    max_target_weight: Decimal,
) -> dict[str, object]:
    parent_by_date = {record.date: record for record in parent.records}
    difference_dates: list[str] = []
    cap_violation_dates: list[str] = []
    exposure_violation_dates: list[str] = []
    cash_residual_dates: list[str] = []
    max_observed_weight = _ZERO
    for record in candidate.records:
        if not (config.oos_start <= record.date <= config.oos_end):
            continue
        weights = tuple(record.desired_target.values())
        observed = max(weights, default=_ZERO)
        max_observed_weight = max(max_observed_weight, observed)
        exposure = sum(weights, _ZERO)
        if observed > max_target_weight + _TOLERANCE:
            cap_violation_dates.append(record.date.isoformat())
        if exposure < -_TOLERANCE or exposure > _ONE + _TOLERANCE:
            exposure_violation_dates.append(record.date.isoformat())
        if _TOLERANCE < exposure < _ONE - _TOLERANCE:
            cash_residual_dates.append(record.date.isoformat())
        parent_record = parent_by_date.get(record.date)
        if parent_record is None:
            raise ValidationError("frozen parent is missing a candidate session.")
        if _base._weights_differ(
            record.desired_target,
            parent_record.desired_target,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        ):
            difference_dates.append(record.date.isoformat())
    passed = bool(difference_dates) and not cap_violation_dates and not (
        exposure_violation_dates
    )
    return {
        "passed": passed,
        "parent_candidate_id": _FROZEN_PARENT_ID,
        "candidate_role": _PAIRING_ROLE,
        "parent_metadata_only": False,
        "oos_target_difference_session_count": len(difference_dates),
        "first_oos_target_difference_date": (
            None if not difference_dates else difference_dates[0]
        ),
        "last_oos_target_difference_date": (
            None if not difference_dates else difference_dates[-1]
        ),
        "max_observed_oos_target_weight": _text(max_observed_weight),
        "max_target_weight": _text(max_target_weight),
        "cap_violation_session_count": len(cap_violation_dates),
        "exposure_violation_session_count": len(exposure_violation_dates),
        "cash_residual_session_count": len(cash_residual_dates),
    }


def _candidate_gates(
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    integrity: Mapping[str, object],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    candidate_id = NEXUSTRADE_MONTHLY_RISK_BALANCED_ID
    oos_window_ids = (
        "oos",
        *(item.window_id for item in config.walk_forward_windows),
    )
    baseline_windows = []
    for window_id in oos_window_ids:
        comparison = _base._metric_comparison(
            metric_book[candidate_id]["source_fee_only"][window_id],
            metric_book[_SPY_BASELINE_ID]["source_fee_only"][window_id],
        )
        baseline_windows.append(
            {
                "window_id": window_id,
                "passed": _base._baseline_window_passed(comparison),
                **comparison,
            }
        )
    baseline_passed = all(item["passed"] for item in baseline_windows)

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
        "source_fee_spy_edge": _text(source_edge),
        "moderate_spy_edge": _text(moderate_edge),
        "edge_broken_by_moderate_cost": edge_broken,
        "return_degradation": _text(degradation),
    }

    cross_windows = []
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
        cross_windows.append(
            {
                "window_id": window_id,
                "candidate_total_return": _text(candidate_return),
                "comparator_total_return": _text(comparator_return),
                "return_delta": _text(candidate_return - comparator_return),
                "passed": candidate_return > comparator_return,
            }
        )
    held_symbols = list(moderate_candidate["symbols_with_nonzero_target"])
    positive_symbols = list(moderate_candidate["positive_contribution_symbols"])
    max_share = _optional_decimal(
        moderate_candidate["max_absolute_contribution_share"]
    )
    cross_asset_passed = (
        all(item["passed"] for item in cross_windows)
        and len(held_symbols) >= 6
        and len(positive_symbols) >= 4
        and max_share is not None
        and max_share <= Decimal("0.50")
    )
    cross_asset_gate = {
        "passed": cross_asset_passed,
        "comparator_id": _STATIC_EQUAL_WEIGHT_ID,
        "window_results": cross_windows,
        "symbols_with_nonzero_oos_target": held_symbols,
        "symbols_with_nonzero_oos_target_count": len(held_symbols),
        "positive_contribution_symbols": positive_symbols,
        "positive_contribution_symbol_count": len(positive_symbols),
        "max_absolute_contribution_share": (
            moderate_candidate["max_absolute_contribution_share"]
        ),
    }

    parent_full = metric_book[_FROZEN_PARENT_ID]["moderate_friction"]["oos"]
    parent_comparison = _base._metric_comparison(moderate_candidate, parent_full)
    drawdown_delta = _base._decimal(parent_comparison["max_drawdown_delta"])
    return_delta = _base._decimal(parent_comparison["total_return_delta"])
    sharpe_delta = _optional_decimal(parent_comparison["sharpe_ratio_delta"])
    turnover_delta = _base._decimal(
        moderate_candidate["one_way_turnover"]
    ) - _base._decimal(parent_full["one_way_turnover"])
    parent_share = _optional_decimal(parent_full["max_absolute_contribution_share"])
    fold_drawdowns = []
    for window in config.walk_forward_windows:
        comparison = _base._metric_comparison(
            metric_book[candidate_id]["moderate_friction"][window.window_id],
            metric_book[_FROZEN_PARENT_ID]["moderate_friction"][window.window_id],
        )
        fold_delta = _base._decimal(comparison["max_drawdown_delta"])
        fold_drawdowns.append(
            {
                "window_id": window.window_id,
                "max_drawdown_delta": comparison["max_drawdown_delta"],
                "passed": fold_delta <= _ZERO,
            }
        )
    concentration_passed = (
        max_share is not None
        and parent_share is not None
        and max_share <= Decimal("0.35")
        and max_share <= parent_share
    )
    risk_balance_passed = (
        integrity["passed"] is True
        and drawdown_delta <= Decimal("-0.01")
        and all(item["passed"] for item in fold_drawdowns)
        and return_delta >= Decimal("-0.02")
        and (sharpe_delta is None or sharpe_delta >= _ZERO)
        and turnover_delta <= Decimal("2.0")
        and concentration_passed
    )
    risk_balance_gate = {
        "passed": risk_balance_passed,
        "integrity": dict(integrity),
        "moderate_friction_oos_comparison_to_frozen_parent": parent_comparison,
        "full_oos_drawdown_improvement_at_least_0_01": (
            drawdown_delta <= Decimal("-0.01")
        ),
        "fold_drawdown_results": fold_drawdowns,
        "full_oos_return_delta_at_least_negative_0_02": (
            return_delta >= Decimal("-0.02")
        ),
        "full_oos_sharpe_nonnegative_delta": (
            sharpe_delta is None or sharpe_delta >= _ZERO
        ),
        "one_way_turnover_delta": _text(turnover_delta),
        "one_way_turnover_delta_at_most_2": turnover_delta <= Decimal("2.0"),
        "candidate_max_absolute_contribution_share": (
            moderate_candidate["max_absolute_contribution_share"]
        ),
        "parent_max_absolute_contribution_share": (
            parent_full["max_absolute_contribution_share"]
        ),
        "concentration_requirement_passed": concentration_passed,
    }

    all_passed = (
        baseline_passed
        and cost_passed
        and cross_asset_passed
        and risk_balance_passed
    )
    nonpositive = _base._decimal(source_candidate["total_return"]) <= _ZERO
    failed_all_baseline_windows = not any(
        item["passed"] for item in baseline_windows
    )
    route = (
        "preview_review"
        if all_passed
        else (
            "reject"
            if nonpositive and failed_all_baseline_windows
            else "continue_local_research"
        )
    )
    return {
        "baseline_oos_gate": {
            "passed": baseline_passed,
            "baseline_id": _SPY_BASELINE_ID,
            "cost_id": "source_fee_only",
            "window_results": baseline_windows,
        },
        "cost_gate": cost_gate,
        "portfolio_level_cross_asset_gate": cross_asset_gate,
        "targeted_risk_balance_gate": risk_balance_gate,
        "all_applicable_gates_passed": all_passed,
        "route": route,
        "paper_promotion_allowed": False,
    }


def _reproduce_frozen_parent(
    config: NexusTradeMonthlyRiskBalancedConfig,
    base_config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    data: _base._AlignedData,
    artifact_hashes: Mapping[str, str],
) -> dict[str, object]:
    computed_preregistration = (
        _base.build_nexustrade_monthly_independent_preregistration(base_config)
    )
    recorded_preregistration = _load_json(
        config.parent_preregistration_path,
        "parent_preregistration_path",
    )
    if computed_preregistration != recorded_preregistration:
        raise ValidationError("frozen parent preregistration reproduction failed.")
    computed_result = _base._build_replication_result(
        base_config,
        data,
        computed_preregistration,
    )
    recorded_result = _load_json(config.parent_result_path, "parent_result_path")
    if computed_result != recorded_result:
        raise ValidationError("frozen parent result reproduction failed.")
    recorded_summary = config.parent_summary_path.read_text(encoding="utf-8")
    if _base._render_summary(computed_result) != recorded_summary:
        raise ValidationError("frozen parent summary reproduction failed.")
    manifest = _load_json(config.parent_manifest_path, "parent_manifest_path")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 3:
        raise ValidationError("frozen parent manifest artifact set is invalid.")
    return {
        "passed": True,
        "preregistration_structured_equality": True,
        "result_structured_equality": True,
        "summary_text_equality": True,
        "artifact_hashes": dict(artifact_hashes),
    }


def _validate_protocol_dependencies(
    config: NexusTradeMonthlyRiskBalancedConfig,
) -> dict[str, str]:
    dependencies = {
        "tracked_preregistration_sha256": (
            config.preregistration_path,
            config.expected_preregistration_sha256,
        ),
        "parent_protocol_sha256": (
            config.parent_protocol_path,
            config.expected_parent_protocol_sha256,
        ),
        "parent_engine_sha256": (
            config.parent_engine_path,
            config.expected_parent_engine_sha256,
        ),
        "v566_protocol_sha256": (
            config.v566_protocol_path,
            config.expected_v566_protocol_sha256,
        ),
    }
    verified = {}
    for name, (path, expected) in dependencies.items():
        actual = _file_sha256(path)
        if actual != expected:
            raise ValidationError(f"{name} does not match the preregistered dependency.")
        verified[name] = actual
    return verified


def _validate_parent_artifacts(
    config: NexusTradeMonthlyRiskBalancedConfig,
) -> dict[str, str]:
    artifacts = {
        "preregistration_sha256": (
            config.parent_preregistration_path,
            config.expected_parent_preregistration_sha256,
        ),
        "result_sha256": (
            config.parent_result_path,
            config.expected_parent_result_sha256,
        ),
        "summary_sha256": (
            config.parent_summary_path,
            config.expected_parent_summary_sha256,
        ),
        "manifest_sha256": (
            config.parent_manifest_path,
            config.expected_parent_manifest_sha256,
        ),
    }
    verified = {}
    for name, (path, expected) in artifacts.items():
        actual = _file_sha256(path)
        if actual != expected:
            raise ValidationError(f"parent {name} does not match preregistration.")
        verified[name] = actual
    return verified


def _gate_policy_payload() -> dict[str, object]:
    return {
        "baseline_full_oos_and_all_folds_required": True,
        "moderate_cost_id": "moderate_friction",
        "cross_asset_portfolio_gate_required": True,
        "target_difference_and_0_20_cap_required": True,
        "full_oos_drawdown_delta_at_most": "-0.01",
        "every_fold_drawdown_delta_at_most": "0",
        "full_oos_return_delta_at_least": "-0.02",
        "full_oos_sharpe_delta_at_least": "0",
        "one_way_turnover_delta_at_most": "2.0",
        "max_absolute_contribution_share_at_most": "0.35",
        "preview_review_requires_all_applicable_gates": True,
        "paper_promotion_allowed": False,
    }


def _safety_payload() -> dict[str, object]:
    return {
        "offline_only": True,
        "network_access_performed": False,
        "nexustrade_access_performed": False,
        "nexustrade_mutation_performed": False,
        "broker_access_performed": False,
        "paper_mutation_performed": False,
        "live_activity_performed": False,
        "third_sleeve_added": False,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "unchanged_v557_caps": {
            "entry_order_notional_usd": "25",
            "aggregate_marked_spy_entry_exposure_usd": "60",
            "broker_orders_per_secure_cycle": 1,
            "sleeve_intents_per_utc_day": 2,
        },
    }


def _artifact_manifest(
    config: NexusTradeMonthlyRiskBalancedConfig,
    data: _base._AlignedData,
    preregistration_path: Path,
    result_path: Path,
    summary_path: Path,
) -> dict[str, object]:
    return {
        "record_type": "nexustrade_monthly_risk_balanced_artifact_manifest",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "artifacts": [
            _artifact_record(path)
            for path in (preregistration_path, result_path, summary_path)
        ],
        "inputs": {
            "canonical_data": {
                "path": str(config.data_path),
                "sha256": data.data_sha256,
            },
            "canonical_manifest": {
                "path": str(config.data_manifest_path),
                "sha256": data.data_manifest_sha256,
            },
            "tracked_preregistration": {
                "path": str(config.preregistration_path),
                "sha256": config.expected_preregistration_sha256,
            },
            "frozen_parent_result": {
                "path": str(config.parent_result_path),
                "sha256": config.expected_parent_result_sha256,
            },
        },
        "safety": _safety_payload(),
    }


def _artifact_record(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "byte_count": path.stat().st_size,
    }


def _render_summary(result: Mapping[str, object]) -> str:
    candidate = _mapping(result.get("candidate"), "candidate")
    gates = _mapping(candidate.get("gates"), "candidate.gates")
    moderate = next(
        item
        for item in candidate["cost_results"]
        if item["cost_id"] == "moderate_friction"
    )
    oos = next(
        item for item in moderate["window_metrics"] if item["window_id"] == "oos"
    )
    return "\n".join(
        (
            "# V5.67 NexusTrade-Inspired Risk-Balanced Allocation",
            "",
            f"- Candidate: `{candidate['candidate_id']}`.",
            "- Claim: independent candidate; not an authentic NexusTrade replay.",
            f"- Route: `{candidate['route']}`.",
            f"- All gates passed: `{str(gates['all_applicable_gates_passed']).lower()}`.",
            f"- Moderate-cost OOS total return: `{oos['total_return']}`.",
            f"- Moderate-cost OOS maximum drawdown: `{oos['max_drawdown']}`.",
            f"- Moderate-cost OOS Sharpe ratio: `{oos['sharpe_ratio']}`.",
            f"- Moderate-cost OOS one-way turnover: `{oos['one_way_turnover']}`.",
            f"- Frozen parent reproduction passed: `{str(result['frozen_parent_reproduction']['passed']).lower()}`.",
            "- Paper promotion allowed: `false`.",
            "- Network, broker, paper mutation, and live activity: none.",
            "",
        )
    )


def _load_json(path: Path, field_name: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field_name} must be readable JSON.") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must contain a JSON object.")
    return value


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file does not exist: {path}")
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


def _optional_decimal(value: object) -> Decimal | None:
    return None if value is None else _base._decimal(value)


def _text(value: Decimal) -> str:
    return _base._decimal_text(value)


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _config(
    value: NexusTradeMonthlyRiskBalancedConfig,
) -> NexusTradeMonthlyRiskBalancedConfig:
    if not isinstance(value, NexusTradeMonthlyRiskBalancedConfig):
        raise ValidationError(
            "config must be NexusTradeMonthlyRiskBalancedConfig."
        )
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_nexustrade_monthly_risk_balanced_allocation(
        NexusTradeMonthlyRiskBalancedConfig(
            output_root=args.output_root,
            data_path=args.data_path,
            data_manifest_path=args.data_manifest_path,
            preregistration_path=args.preregistration_path,
        )
    )
    if args.format == "json":
        print(json.dumps(_base._json_safe(result), indent=2, sort_keys=True))
    else:
        candidate = _mapping(result["candidate"], "candidate")
        print(f"candidate_id={candidate['candidate_id']}")
        print(f"route={candidate['route']}")
        print(
            "all_applicable_gates_passed="
            + str(candidate["gates"]["all_applicable_gates_passed"]).lower()
        )
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
        print("paper_promotion_allowed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
