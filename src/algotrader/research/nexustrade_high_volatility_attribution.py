"""Attribution-only diagnostic for the frozen V5.65 volatility defense."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research import nexustrade_monthly_high_volatility_defense as _defense
from algotrader.research import nexustrade_monthly_independent_replication as _base

__all__ = [
    "NexusTradeHighVolatilityAttributionConfig",
    "build_nexustrade_high_volatility_attribution_preregistration",
    "run_nexustrade_high_volatility_attribution",
]

_PROTOCOL_ID = "v5_66_nexustrade_high_volatility_attribution_v1"
_DIAGNOSTIC_ID = "nexustrade_high_volatility_defense_attribution_only"
_RECORD_TYPE = "nexustrade_high_volatility_attribution_result"
_SCHEMA_VERSION = 1
_PARENT_ID = _base.NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
_ACTUAL_ID = _defense.NEXUSTRADE_MONTHLY_HIGH_VOLATILITY_DEFENSE_ID
_DELAYED_ID = "diagnostic_high_volatility_defense_delayed_parent_state"
_IMMEDIATE_ID = "diagnostic_high_volatility_defense_immediate_parent_state"
_PATH_IDS = (_PARENT_ID, _ACTUAL_ID, _DELAYED_ID, _IMMEDIATE_ID)
_SPY = "SPY"
_ZERO = Decimal("0")
_ONE = Decimal("1")
_TOLERANCE = Decimal("1e-24")
_MATERIAL_HARM = Decimal("0.005")
_PRIMARY_SHARE = Decimal("0.50")
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/v5_66_nexustrade_high_volatility_attribution"
)
_DEFAULT_DATA_PATH = Path(
    "runs/operator_input/multi_etf_adjusted_daily_canonical.csv"
)
_DEFAULT_DATA_MANIFEST_PATH = Path(
    "runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json"
)
_DEFAULT_PREREGISTRATION_PATH = Path(
    "docs/design/v5_66_nexustrade_high_volatility_attribution.md"
)
_DEFAULT_V564_PROTOCOL_PATH = Path(
    "docs/design/v5_64_nexustrade_monthly_independent_replication.md"
)
_DEFAULT_V564_ENGINE_PATH = Path(
    "src/algotrader/research/nexustrade_monthly_independent_replication.py"
)
_DEFAULT_V565_PROTOCOL_PATH = Path(
    "docs/design/v5_65_nexustrade_monthly_high_volatility_defense.md"
)
_DEFAULT_V565_ENGINE_PATH = Path(
    "src/algotrader/research/nexustrade_monthly_high_volatility_defense.py"
)
_DEFAULT_V565_ROOT = Path(
    "runs/v5_65_nexustrade_monthly_high_volatility_defense"
)
_EXPECTED_PREREGISTRATION_SHA256 = (
    "2a2d03030b2ec74ca3a0682ca94163ea5b28218c1b452b4f10664fc182733227"
)
_EXPECTED_DATA_SHA256 = (
    "d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575"
)
_EXPECTED_DATA_MANIFEST_SHA256 = (
    "e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1"
)
_EXPECTED_V564_PROTOCOL_SHA256 = (
    "f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0"
)
_EXPECTED_V564_ENGINE_SHA256 = (
    "66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5"
)
_EXPECTED_V565_PROTOCOL_SHA256 = (
    "1b614cb9d9e310704a0f8adcda224a4c540054a70af2731bcd3ec9c9b44db0c5"
)
_EXPECTED_V565_ENGINE_SHA256 = (
    "fbc37e7c5cda052951c9406c7666cf346fa6d814edbf41d9842c80f4c2516a3c"
)
_EXPECTED_V565_PREREGISTRATION_SHA256 = (
    "8ab8fb25edf1ccb9803465fbc568b4b5348776c472b58c447a189ee677723190"
)
_EXPECTED_V565_RESULT_SHA256 = (
    "e30c9c6f9d90f0d87c33607c71d1ec3e7c0055a245b88d06a469bfbc33709611"
)
_EXPECTED_V565_SUMMARY_SHA256 = (
    "1ff76c5c3fcb840794fbcd2e501f7300976f34557dd9aad3dcea35ebdd3f936e"
)
_EXPECTED_V565_MANIFEST_SHA256 = (
    "99c52a97d2f8d6ef88df844356dbd38e88859d2804c4db9cf166ae55cad48814"
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
class NexusTradeHighVolatilityAttributionConfig:
    """Pinned local inputs for the V5.66 attribution-only diagnostic."""

    output_root: Path | str = _DEFAULT_OUTPUT_ROOT
    data_path: Path | str = _DEFAULT_DATA_PATH
    data_manifest_path: Path | str = _DEFAULT_DATA_MANIFEST_PATH
    preregistration_path: Path | str = _DEFAULT_PREREGISTRATION_PATH
    v564_protocol_path: Path | str = _DEFAULT_V564_PROTOCOL_PATH
    v564_engine_path: Path | str = _DEFAULT_V564_ENGINE_PATH
    v565_protocol_path: Path | str = _DEFAULT_V565_PROTOCOL_PATH
    v565_engine_path: Path | str = _DEFAULT_V565_ENGINE_PATH
    v565_preregistration_path: Path | str = (
        _DEFAULT_V565_ROOT / "preregistration.json"
    )
    v565_result_path: Path | str = _DEFAULT_V565_ROOT / "defense_results.json"
    v565_summary_path: Path | str = _DEFAULT_V565_ROOT / "defense_summary.md"
    v565_manifest_path: Path | str = _DEFAULT_V565_ROOT / "manifest.json"
    expected_preregistration_sha256: str = _EXPECTED_PREREGISTRATION_SHA256
    expected_data_sha256: str = _EXPECTED_DATA_SHA256
    expected_data_manifest_sha256: str = _EXPECTED_DATA_MANIFEST_SHA256
    expected_v564_protocol_sha256: str = _EXPECTED_V564_PROTOCOL_SHA256
    expected_v564_engine_sha256: str = _EXPECTED_V564_ENGINE_SHA256
    expected_v565_protocol_sha256: str = _EXPECTED_V565_PROTOCOL_SHA256
    expected_v565_engine_sha256: str = _EXPECTED_V565_ENGINE_SHA256
    expected_v565_preregistration_sha256: str = (
        _EXPECTED_V565_PREREGISTRATION_SHA256
    )
    expected_v565_result_sha256: str = _EXPECTED_V565_RESULT_SHA256
    expected_v565_summary_sha256: str = _EXPECTED_V565_SUMMARY_SHA256
    expected_v565_manifest_sha256: str = _EXPECTED_V565_MANIFEST_SHA256
    initial_equity: Decimal | str = Decimal("10000")
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

    def __post_init__(self) -> None:
        for name in (
            "output_root",
            "data_path",
            "data_manifest_path",
            "preregistration_path",
            "v564_protocol_path",
            "v564_engine_path",
            "v565_protocol_path",
            "v565_engine_path",
            "v565_preregistration_path",
            "v565_result_path",
            "v565_summary_path",
            "v565_manifest_path",
        ):
            object.__setattr__(self, name, _path(getattr(self, name), name))
        for name in (
            "expected_preregistration_sha256",
            "expected_data_sha256",
            "expected_data_manifest_sha256",
            "expected_v564_protocol_sha256",
            "expected_v564_engine_sha256",
            "expected_v565_protocol_sha256",
            "expected_v565_engine_sha256",
            "expected_v565_preregistration_sha256",
            "expected_v565_result_sha256",
            "expected_v565_summary_sha256",
            "expected_v565_manifest_sha256",
        ):
            object.__setattr__(
                self,
                name,
                _base._sha256_text(getattr(self, name), name),
            )
        equity = _base._positive_decimal(self.initial_equity, "initial_equity")
        if equity != Decimal("10000"):
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
        if not windows or any(
            type(item) is not _base.ReplicationWindow for item in windows
        ):
            raise ValidationError(
                "walk_forward_windows must contain ReplicationWindow values."
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
        self.defense_config()

    def defense_config(
        self,
    ) -> _defense.NexusTradeMonthlyHighVolatilityDefenseConfig:
        """Return the frozen V5.65 mechanics configuration."""

        return _defense.NexusTradeMonthlyHighVolatilityDefenseConfig(
            output_root=self.output_root,
            data_path=self.data_path,
            data_manifest_path=self.data_manifest_path,
            preregistration_path=self.v565_protocol_path,
            parent_preregistration_path=self.v564_protocol_path,
            parent_engine_path=self.v564_engine_path,
            expected_preregistration_sha256=self.expected_v565_protocol_sha256,
            expected_parent_preregistration_sha256=(
                self.expected_v564_protocol_sha256
            ),
            expected_parent_engine_sha256=self.expected_v564_engine_sha256,
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


def build_nexustrade_high_volatility_attribution_preregistration(
    config: NexusTradeHighVolatilityAttributionConfig,
) -> dict[str, object]:
    """Build the fixed diagnostic contract without loading prices or outcomes."""

    checked = _config(config)
    hashes = _validate_dependencies(checked)
    return {
        "record_type": "nexustrade_high_volatility_attribution_preregistration",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "diagnostic_id": _DIAGNOSTIC_ID,
        "diagnostic_only": True,
        "candidate_created": False,
        "route_created": False,
        "tracked_preregistration_path": str(checked.preregistration_path),
        "tracked_preregistration_sha256": hashes[
            "tracked_preregistration_sha256"
        ],
        "pinned_dependencies": hashes,
        "path_definitions": {
            "P": _PARENT_ID,
            "A": _ACTUAL_ID,
            "D": _DELAYED_ID,
            "I": _IMMEDIATE_ID,
            "diagnostic_counterfactuals_are_candidates": False,
        },
        "return_decomposition": {
            "classification_effect": "I-P",
            "execution_delay_effect": "D-I",
            "stateful_carry_effect": "A-D",
            "total_effect": "A-P",
            "reconciliation_tolerance": _text(_TOLERANCE),
        },
        "diagnostic_classification": {
            "material_harm_threshold": _text(_MATERIAL_HARM),
            "primary_share_threshold": _text(_PRIMARY_SHARE),
            "tie_tolerance": _text(_TOLERANCE),
            "tie_result": "mixed_harm",
            "creates_route": False,
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
        "cost_assumptions": [
            item.to_dict() for item in _base._COST_ASSUMPTIONS
        ],
        "source_metrics_trust": "untrusted_external_evidence",
        "source_metrics_used": False,
        "holdout_discrepancy_preserved": {
            "table_total_return_percent": "29.64",
            "chart_gain_percent": "29.41",
        },
        "parameter_search_performed": False,
        "paper_promotion_allowed": False,
        "safety": _safety_payload(),
    }


def run_nexustrade_high_volatility_attribution(
    config: NexusTradeHighVolatilityAttributionConfig,
) -> dict[str, object]:
    """Reproduce frozen paths and write deterministic attribution artifacts."""

    checked = _config(config)
    checked.output_root.mkdir(parents=True, exist_ok=True)
    preregistration = (
        build_nexustrade_high_volatility_attribution_preregistration(checked)
    )
    preregistration_path = checked.output_root / "preregistration.json"
    _base._write_json_atomic(preregistration_path, preregistration)

    frozen_result = _load_json(checked.v565_result_path, "v565_result_path")
    defense_config = checked.defense_config()
    base_config = defense_config.base_config()
    data = _base._load_aligned_data(base_config)
    _base._validate_chronology(data, base_config)
    result = _build_result(
        checked,
        defense_config,
        base_config,
        data,
        frozen_result,
        preregistration,
    )
    result_path = checked.output_root / "attribution_results.json"
    _base._write_json_atomic(result_path, result)
    summary_path = checked.output_root / "attribution_summary.md"
    _base._write_text_atomic(summary_path, _render_summary(result))
    manifest = _artifact_manifest(
        checked,
        preregistration_path=preregistration_path,
        result_path=result_path,
        summary_path=summary_path,
    )
    manifest_path = checked.output_root / "manifest.json"
    _base._write_json_atomic(manifest_path, manifest)

    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_path"] = str(manifest_path)
    completed["artifact_manifest_sha256"] = _sha256(manifest_path)
    return completed


def _build_result(
    config: NexusTradeHighVolatilityAttributionConfig,
    defense_config: _defense.NexusTradeMonthlyHighVolatilityDefenseConfig,
    base_config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    data: _base._AlignedData,
    frozen_result: Mapping[str, object],
    preregistration: Mapping[str, object],
) -> dict[str, object]:
    indicators = _base._build_indicators(data)
    regimes = _defense._build_volatility_regimes(data, defense_config)
    simulations: dict[str, dict[str, _base._Simulation]] = {
        path_id: {} for path_id in _PATH_IDS
    }
    for cost in _base._COST_ASSUMPTIONS:
        canonical_parent = _base._simulate_dynamic_candidate(
            data,
            indicators,
            base_config,
            cost,
            composite=True,
        )
        reproduced_parent, delayed, immediate = _simulate_stateless_paths(
            data,
            indicators,
            regimes,
            base_config,
            cost,
        )
        if reproduced_parent.records != canonical_parent.records:
            raise ValidationError(
                "diagnostic parent state machine does not reproduce frozen V5.64."
            )
        actual = _defense._simulate_defense(
            data,
            indicators,
            regimes,
            base_config,
            cost,
        )
        simulations[_PARENT_ID][cost.cost_id] = canonical_parent
        simulations[_ACTUAL_ID][cost.cost_id] = actual
        simulations[_DELAYED_ID][cost.cost_id] = delayed
        simulations[_IMMEDIATE_ID][cost.cost_id] = immediate

    windows = _base._reporting_windows(base_config)
    metric_book = _metric_book(simulations, windows)
    reproduction = _validate_frozen_reproduction(
        frozen_result,
        simulations,
        metric_book,
        windows,
        base_config,
        config.expected_v565_result_sha256,
    )
    regime_by_date = dict(zip(data.dates, regimes))
    decomposition = _build_decomposition(
        simulations,
        metric_book,
        regime_by_date,
        windows,
    )
    classification = _diagnostic_classification(decomposition)
    transition_ledger = _transition_ledger(
        data,
        regime_by_date,
        simulations,
        base_config,
    )

    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "diagnostic_id": _DIAGNOSTIC_ID,
        "diagnostic_only": True,
        "candidate_created": False,
        "route_created": False,
        "preview_review_created": False,
        "shadow_created": False,
        "preregistration": {
            "path": str(config.preregistration_path),
            "sha256": preregistration["tracked_preregistration_sha256"],
            "committed_before_diagnostic_output": True,
        },
        "pinned_dependencies": preregistration["pinned_dependencies"],
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
        "chronology": preregistration["chronology"],
        "path_definitions": preregistration["path_definitions"],
        "frozen_reproduction": reproduction,
        "path_results": [
            {
                "path_id": path_id,
                "diagnostic_counterfactual": path_id in {_DELAYED_ID, _IMMEDIATE_ID},
                "candidate": False,
                "cost_results": _base._cost_result_records(
                    path_id,
                    metric_book,
                    simulations,
                    windows,
                    base_config,
                ),
            }
            for path_id in _PATH_IDS
        ],
        "attribution": decomposition,
        "diagnostic_classification": classification,
        "volatility_transition_ledger": transition_ledger,
        "source_metrics_trust": "untrusted_external_evidence",
        "source_metrics_used": False,
        "holdout_discrepancy_preserved": {
            "table_total_return_percent": "29.64",
            "chart_gain_percent": "29.41",
        },
        "parameter_search_performed": False,
        "paper_promotion_allowed": False,
        "safety": _safety_payload(),
        "limitations": [
            "The immediate-close path is an attribution-only timing counterfactual, "
            "not an authentic fill assumption or candidate.",
            "Total-return effects reconcile additively; maximum drawdown is "
            "path-dependent and is reported without additive attribution.",
            "Gross contribution sums are arithmetic diagnostics and do not replace "
            "compounded portfolio-return attribution.",
            "The diagnostic does not resolve authentic NexusTrade data mode, "
            "slippage, warm-up, fill behavior, or lineage.",
        ],
    }


def _simulate_stateless_paths(
    data: _base._AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    regimes: Sequence[str],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    cost: _base._CostAssumption,
) -> tuple[_base._Simulation, _base._Simulation, _base._Simulation]:
    start_index = next(
        index for index, item in enumerate(data.dates) if item >= config.train_start
    )
    end_index = max(
        index for index, item in enumerate(data.dates) if item <= config.oos_end
    )
    if start_index == 0:
        raise ValidationError("training requires a prior signal session.")

    parent_weights = _base._zero_stock_weights()
    delayed_weights = _base._zero_stock_weights()
    immediate_weights = _base._zero_stock_weights()
    parent_last_buy: date | None = None
    parent_last_sell: date | None = None
    source_desired = _base._eligible_target(data, indicators, start_index - 1)
    previous_trend = _base._spy_regime_on(indicators, start_index - 1)
    previous_risk = previous_trend and regimes[start_index - 1] != "high_vol"
    parent_desired = (
        source_desired if previous_trend else _base._zero_stock_weights()
    )
    delayed_desired = (
        source_desired if previous_risk else _base._zero_stock_weights()
    )
    parent_pending: dict[str, Decimal] | None = dict(parent_desired)
    delayed_pending: dict[str, Decimal] | None = dict(delayed_desired)
    immediate_pending: dict[str, Decimal] | None = dict(delayed_desired)
    parent_records: list[_base._DayRecord] = []
    delayed_records: list[_base._DayRecord] = []
    immediate_records: list[_base._DayRecord] = []

    for index in range(start_index, end_index + 1):
        parent_step = _base._portfolio_step(
            data,
            index,
            parent_weights,
            parent_pending,
            cost,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        delayed_step = _base._portfolio_step(
            data,
            index,
            delayed_weights,
            delayed_pending,
            cost,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        immediate_step = _base._portfolio_step(
            data,
            index,
            immediate_weights,
            immediate_pending,
            cost,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        parent_weights = parent_step[6]
        delayed_weights = delayed_step[6]
        immediate_weights = immediate_step[6]
        if parent_step[2]:
            parent_last_buy = data.dates[index]
        if parent_step[3]:
            parent_last_sell = data.dates[index]

        rebalance_ready = _base._rebalance_ready(
            data.dates[index], parent_last_buy, parent_last_sell
        )
        if rebalance_ready:
            source_desired = _base._eligible_target(data, indicators, index)
        current_trend = _base._spy_regime_on(indicators, index)
        current_risk = current_trend and regimes[index] != "high_vol"
        parent_desired = (
            source_desired if current_trend else _base._zero_stock_weights()
        )
        diagnostic_desired = (
            source_desired if current_risk else _base._zero_stock_weights()
        )
        parent_scheduled = rebalance_ready or current_trend != previous_trend
        diagnostic_scheduled = parent_scheduled or current_risk != previous_risk
        parent_pending = dict(parent_desired) if parent_scheduled else None
        delayed_pending = dict(diagnostic_desired) if diagnostic_scheduled else None

        overlay_only_changed = (
            current_trend
            and current_trend == previous_trend
            and current_risk != previous_risk
        )
        immediate_pending = (
            dict(diagnostic_desired)
            if diagnostic_scheduled and not overlay_only_changed
            else None
        )

        immediate_return = immediate_step[0]
        immediate_turnover = immediate_step[1]
        immediate_buy = immediate_step[2]
        immediate_sell = immediate_step[3]
        if overlay_only_changed:
            (
                immediate_return,
                immediate_turnover,
                immediate_buy,
                immediate_sell,
                immediate_weights,
            ) = _apply_close_trade(
                immediate_return,
                immediate_weights,
                diagnostic_desired,
                cost,
            )

        parent_records.append(
            _day_record(data.dates[index], parent_step, parent_desired)
        )
        delayed_records.append(
            _day_record(data.dates[index], delayed_step, diagnostic_desired)
        )
        immediate_records.append(
            _base._DayRecord(
                date=data.dates[index],
                strategy_return=immediate_return,
                turnover=immediate_turnover,
                buy_fill_count=immediate_buy,
                sell_fill_count=immediate_sell,
                exposure=immediate_step[4],
                contributions=immediate_step[5],
                desired_target=dict(diagnostic_desired),
                posttrade_weights=dict(immediate_weights),
            )
        )
        previous_trend = current_trend
        previous_risk = current_risk

    return (
        _base._Simulation(_PARENT_ID, cost, tuple(parent_records)),
        _base._Simulation(_DELAYED_ID, cost, tuple(delayed_records)),
        _base._Simulation(_IMMEDIATE_ID, cost, tuple(immediate_records)),
    )


def _day_record(
    on_date: date,
    step: tuple[
        Decimal,
        Decimal,
        int,
        int,
        Decimal,
        dict[str, Decimal],
        dict[str, Decimal],
    ],
    desired: Mapping[str, Decimal],
) -> _base._DayRecord:
    return _base._DayRecord(
        date=on_date,
        strategy_return=step[0],
        turnover=step[1],
        buy_fill_count=step[2],
        sell_fill_count=step[3],
        exposure=step[4],
        contributions=step[5],
        desired_target=dict(desired),
        posttrade_weights=dict(step[6]),
    )


def _apply_close_trade(
    strategy_return: Decimal,
    drifted_weights: Mapping[str, Decimal],
    target: Mapping[str, Decimal],
    cost: _base._CostAssumption,
) -> tuple[Decimal, Decimal, int, int, dict[str, Decimal]]:
    symbols = _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
    _base._validate_target_weights(target, symbols)
    deltas = {
        symbol: target[symbol] - drifted_weights[symbol] for symbol in symbols
    }
    turnover = sum((abs(value) for value in deltas.values()), _ZERO)
    if turnover <= _base._WEIGHT_TOLERANCE:
        return strategy_return, _ZERO, 0, 0, dict(drifted_weights)
    buy_count = sum(
        1 for value in deltas.values() if value > _base._WEIGHT_TOLERANCE
    )
    sell_count = sum(
        1 for value in deltas.values() if value < -_base._WEIGHT_TOLERANCE
    )
    cost_fraction = turnover * cost.rate
    if cost_fraction >= _ONE:
        raise ValidationError("diagnostic transaction cost must remain below one.")
    adjusted_return = (_ONE + strategy_return) * (_ONE - cost_fraction) - _ONE
    return adjusted_return, turnover, buy_count, sell_count, dict(target)


def _metric_book(
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    windows: Sequence[_base.ReplicationWindow],
) -> dict[str, dict[str, dict[str, dict[str, object]]]]:
    return {
        path_id: {
            cost_id: {
                window.window_id: _base._metrics_for_window(
                    simulation,
                    window,
                    _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
                )
                for window in windows
            }
            for cost_id, simulation in cost_paths.items()
        }
        for path_id, cost_paths in simulations.items()
    }


def _validate_frozen_reproduction(
    frozen_result: Mapping[str, object],
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    windows: Sequence[_base.ReplicationWindow],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    frozen_result_sha256: str,
) -> dict[str, object]:
    candidate = _mapping(frozen_result.get("candidate"), "frozen candidate")
    if candidate.get("candidate_id") != _ACTUAL_ID:
        raise ValidationError("frozen V5.65 candidate identity does not match.")
    frozen_route = candidate.get("route")
    if frozen_route not in {
        "preview_review",
        "continue_local_research",
        "reject",
    }:
        raise ValidationError("frozen V5.65 route is not recognized.")
    actual_costs = _records_by_id(candidate.get("cost_results"), "cost_id")
    parent_costs = _records_by_id(
        frozen_result.get("frozen_parent_cost_results"), "cost_id"
    )
    checked_fields = 0
    for cost in _base._COST_ASSUMPTIONS:
        for path_id, frozen_costs in (
            (_ACTUAL_ID, actual_costs),
            (_PARENT_ID, parent_costs),
        ):
            frozen_cost = frozen_costs.get(cost.cost_id)
            if frozen_cost is None:
                raise ValidationError("frozen V5.65 cost result is missing.")
            frozen_windows = _records_by_id(
                frozen_cost.get("window_metrics"), "window_id"
            )
            for window in windows:
                expected = frozen_windows.get(window.window_id)
                actual = metric_book[path_id][cost.cost_id][window.window_id]
                if expected != actual:
                    raise ValidationError(
                        "recomputed frozen V5.65 window metrics do not match."
                    )
                checked_fields += len(actual)
            target_hash = _base._target_vector_sha256(
                simulations[path_id][cost.cost_id],
                config.train_start,
                config.oos_end,
            )
            if target_hash != frozen_cost.get("target_vector_sha256"):
                raise ValidationError("frozen full target vector does not match.")
            oos_target_hash = _base._target_vector_sha256(
                simulations[path_id][cost.cost_id],
                config.oos_start,
                config.oos_end,
            )
            if oos_target_hash != frozen_cost.get("oos_target_vector_sha256"):
                raise ValidationError("frozen OOS target vector does not match.")
    integrity = _defense._overlay_integrity(
        simulations[_ACTUAL_ID]["source_fee_only"],
        simulations[_PARENT_ID]["source_fee_only"],
        config,
    )
    if integrity != frozen_result.get("overlay_integrity"):
        raise ValidationError("frozen V5.65 overlay integrity does not match.")
    return {
        "passed": True,
        "frozen_result_sha256": frozen_result_sha256,
        "frozen_route": frozen_route,
        "window_metric_field_comparisons": checked_fields,
        "full_target_hash_comparisons": 8,
        "oos_target_hash_comparisons": 8,
        "overlay_integrity": integrity,
    }


def _build_decomposition(
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    regime_by_date: Mapping[date, str],
    windows: Sequence[_base.ReplicationWindow],
) -> dict[str, object]:
    costs: list[dict[str, object]] = []
    for cost in _base._COST_ASSUMPTIONS:
        window_records: list[dict[str, object]] = []
        for window in windows:
            metrics = {
                path_id: metric_book[path_id][cost.cost_id][window.window_id]
                for path_id in _PATH_IDS
            }
            returns = {
                path_id: _base._decimal(metrics[path_id]["total_return"])
                for path_id in _PATH_IDS
            }
            classification_effect = returns[_IMMEDIATE_ID] - returns[_PARENT_ID]
            delay_effect = returns[_DELAYED_ID] - returns[_IMMEDIATE_ID]
            stateful_effect = returns[_ACTUAL_ID] - returns[_DELAYED_ID]
            total_effect = returns[_ACTUAL_ID] - returns[_PARENT_ID]
            residual = total_effect - (
                classification_effect + delay_effect + stateful_effect
            )
            _require_tolerance(residual, "return attribution residual")
            contribution = _contribution_attribution(
                simulations,
                cost.cost_id,
                window,
            )
            session = _session_attribution(
                simulations,
                cost.cost_id,
                regime_by_date,
                window,
            )
            drawdowns = {
                path_id: _drawdown_detail(
                    simulations[path_id][cost.cost_id], window
                )
                for path_id in _PATH_IDS
            }
            for path_id in _PATH_IDS:
                difference = _base._decimal(
                    metrics[path_id]["max_drawdown"]
                ) - _base._decimal(drawdowns[path_id]["max_drawdown"])
                _require_tolerance(difference, "drawdown reproduction residual")
            window_records.append(
                {
                    "window_id": window.window_id,
                    "path_metrics": metrics,
                    "return_effects": {
                        "classification_effect_I_minus_P": _text(
                            classification_effect
                        ),
                        "execution_delay_effect_D_minus_I": _text(delay_effect),
                        "stateful_carry_effect_A_minus_D": _text(stateful_effect),
                        "total_effect_A_minus_P": _text(total_effect),
                        "reconciliation_residual": _text(residual),
                        "passed": abs(residual) <= _TOLERANCE,
                    },
                    "drawdown_paths": drawdowns,
                    "session_attribution": session,
                    "constituent_contribution_attribution": contribution,
                    "turnover_trade_attribution": _turnover_attribution(metrics),
                }
            )
        costs.append({"cost_id": cost.cost_id, "windows": window_records})

    degradation = []
    source = next(item for item in costs if item["cost_id"] == "source_fee_only")
    moderate = next(item for item in costs if item["cost_id"] == "moderate_friction")
    source_oos = _window_by_id(source["windows"], "oos")
    moderate_oos = _window_by_id(moderate["windows"], "oos")
    for path_id in _PATH_IDS:
        source_return = _base._decimal(
            source_oos["path_metrics"][path_id]["total_return"]
        )
        moderate_return = _base._decimal(
            moderate_oos["path_metrics"][path_id]["total_return"]
        )
        degradation.append(
            {
                "path_id": path_id,
                "source_fee_oos_return": _text(source_return),
                "moderate_oos_return": _text(moderate_return),
                "return_degradation": _text(source_return - moderate_return),
            }
        )
    return {
        "primary_cost_id": "moderate_friction",
        "reconciliation_tolerance": _text(_TOLERANCE),
        "cost_results": costs,
        "source_fee_to_moderate_degradation": degradation,
    }


def _contribution_attribution(
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    cost_id: str,
    window: _base.ReplicationWindow,
) -> dict[str, object]:
    by_path = {
        path_id: {
            item.date: item for item in simulations[path_id][cost_id].records
        }
        for path_id in _PATH_IDS
    }
    dates = [
        item
        for item in sorted(set.intersection(*(set(value) for value in by_path.values())))
        if window.start <= item <= window.end
    ]
    symbol_records = []
    aggregate = {
        "classification_effect": _ZERO,
        "execution_delay_effect": _ZERO,
        "stateful_carry_effect": _ZERO,
        "total_effect": _ZERO,
        "residual": _ZERO,
    }
    for symbol in _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS:
        parent = sum(
            (by_path[_PARENT_ID][item].contributions[symbol] for item in dates),
            _ZERO,
        )
        actual = sum(
            (by_path[_ACTUAL_ID][item].contributions[symbol] for item in dates),
            _ZERO,
        )
        delayed = sum(
            (by_path[_DELAYED_ID][item].contributions[symbol] for item in dates),
            _ZERO,
        )
        immediate = sum(
            (by_path[_IMMEDIATE_ID][item].contributions[symbol] for item in dates),
            _ZERO,
        )
        classification = immediate - parent
        delay = delayed - immediate
        stateful = actual - delayed
        total = actual - parent
        residual = total - (classification + delay + stateful)
        _require_tolerance(residual, "symbol contribution residual")
        effects = {
            "classification_effect": classification,
            "execution_delay_effect": delay,
            "stateful_carry_effect": stateful,
            "total_effect": total,
            "residual": residual,
        }
        for key, value in effects.items():
            aggregate[key] += value
        symbol_records.append(
            {
                "symbol": symbol,
                **{key: _text(value) for key, value in effects.items()},
                "classification_label": _effect_label(classification),
                "execution_delay_label": _effect_label(delay),
                "stateful_carry_label": _effect_label(stateful),
                "total_label": _effect_label(total),
            }
        )
    _require_tolerance(aggregate["residual"], "aggregate contribution residual")
    return {
        "arithmetic_gross_contribution_only": True,
        "symbols": symbol_records,
        "aggregate": {
            key: _text(value) for key, value in aggregate.items()
        },
        "passed": abs(aggregate["residual"]) <= _TOLERANCE,
    }


def _session_attribution(
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    cost_id: str,
    regime_by_date: Mapping[date, str],
    window: _base.ReplicationWindow,
) -> dict[str, object]:
    by_path = {
        path_id: {
            item.date: item for item in simulations[path_id][cost_id].records
        }
        for path_id in _PATH_IDS
    }
    dates = [
        item
        for item in sorted(set.intersection(*(set(value) for value in by_path.values())))
        if window.start <= item <= window.end
    ]
    high_vol = [item for item in dates if regime_by_date[item] == "high_vol"]
    parent_risk_on_high = [
        item
        for item in high_vol
        if _desired_exposure(by_path[_PARENT_ID][item]) > _base._WEIGHT_TOLERANCE
    ]
    total_divergence = [
        item
        for item in dates
        if _base._weights_differ(
            by_path[_ACTUAL_ID][item].desired_target,
            by_path[_PARENT_ID][item].desired_target,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
    ]
    state_divergence = [
        item
        for item in dates
        if _base._weights_differ(
            by_path[_ACTUAL_ID][item].desired_target,
            by_path[_DELAYED_ID][item].desired_target,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
    ]
    delay_divergence = [
        item
        for item in dates
        if _base._weights_differ(
            by_path[_DELAYED_ID][item].posttrade_weights,
            by_path[_IMMEDIATE_ID][item].posttrade_weights,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
    ]
    return {
        "high_volatility_sessions": _date_summary(high_vol),
        "parent_risk_on_high_volatility_sessions": _date_summary(
            parent_risk_on_high
        ),
        "actual_vs_parent_target_divergence": _date_summary(total_divergence),
        "stateful_carry_target_divergence_A_vs_D": _date_summary(
            state_divergence
        ),
        "execution_delay_posttrade_divergence_D_vs_I": _date_summary(
            delay_divergence
        ),
    }


def _drawdown_detail(
    simulation: _base._Simulation,
    window: _base.ReplicationWindow,
) -> dict[str, object]:
    records = [
        item for item in simulation.records if window.start <= item.date <= window.end
    ]
    if not records:
        raise ValidationError("drawdown window contains no records.")
    equity = Decimal("10000")
    peak_equity = equity
    current_peak_date = records[0].date
    worst = _ZERO
    worst_peak_date = current_peak_date
    trough_date = records[0].date
    worst_peak_equity = peak_equity
    curve: list[tuple[date, Decimal]] = []
    for record in records:
        equity *= _ONE + record.strategy_return
        curve.append((record.date, equity))
        if equity > peak_equity:
            peak_equity = equity
            current_peak_date = record.date
        drawdown = _ONE - equity / peak_equity
        if drawdown > worst:
            worst = drawdown
            worst_peak_date = current_peak_date
            worst_peak_equity = peak_equity
            trough_date = record.date
    recovery_date = next(
        (
            on_date
            for on_date, value in curve
            if on_date > trough_date and value >= worst_peak_equity
        ),
        None,
    )
    return {
        "max_drawdown": _text(worst),
        "peak_date": worst_peak_date.isoformat(),
        "trough_date": trough_date.isoformat(),
        "recovery_date": None if recovery_date is None else recovery_date.isoformat(),
        "recovered_within_window": recovery_date is not None,
        "window_start_equity_rebased_to": "10000",
    }


def _turnover_attribution(
    metrics: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    parent_turnover = _base._decimal(metrics[_PARENT_ID]["one_way_turnover"])
    parent_trades = int(metrics[_PARENT_ID]["trade_count"])
    paths = []
    for path_id in (_ACTUAL_ID, _DELAYED_ID, _IMMEDIATE_ID):
        turnover = _base._decimal(metrics[path_id]["one_way_turnover"])
        trades = int(metrics[path_id]["trade_count"])
        paths.append(
            {
                "path_id": path_id,
                "one_way_turnover": _text(turnover),
                "turnover_delta_vs_parent": _text(turnover - parent_turnover),
                "trade_count": trades,
                "trade_count_delta_vs_parent": trades - parent_trades,
            }
        )
    return {
        "parent_one_way_turnover": _text(parent_turnover),
        "parent_trade_count": parent_trades,
        "paths": paths,
    }


def _diagnostic_classification(
    decomposition: Mapping[str, object],
) -> dict[str, object]:
    moderate = next(
        item
        for item in decomposition["cost_results"]
        if item["cost_id"] == "moderate_friction"
    )
    oos = _window_by_id(moderate["windows"], "oos")
    metrics = oos["path_metrics"]
    parent = _base._decimal(metrics[_PARENT_ID]["total_return"])
    actual = _base._decimal(metrics[_ACTUAL_ID]["total_return"])
    delayed = _base._decimal(metrics[_DELAYED_ID]["total_return"])
    immediate = _base._decimal(metrics[_IMMEDIATE_ID]["total_return"])
    net_harm = parent - actual
    components = {
        "classification": max(_ZERO, parent - immediate),
        "execution_delay": max(_ZERO, immediate - delayed),
        "stateful_carry": max(_ZERO, delayed - actual),
    }
    shares = {
        key: (None if net_harm == _ZERO else value / net_harm)
        for key, value in components.items()
    }
    if net_harm <= _MATERIAL_HARM:
        classification = "no_material_harm"
        primary = None
    else:
        largest_value = max(components.values())
        largest = [
            key
            for key, value in components.items()
            if abs(value - largest_value) <= _TOLERANCE
        ]
        if (
            len(largest) != 1
            or largest_value < _MATERIAL_HARM
            or largest_value < _PRIMARY_SHARE * net_harm
        ):
            classification = "mixed_harm"
            primary = None
        else:
            primary = largest[0]
            classification = f"{primary}_primary"
    return {
        "classification": classification,
        "primary_driver": primary,
        "creates_route": False,
        "candidate_created": False,
        "moderate_full_oos": {
            "parent_return": _text(parent),
            "actual_return": _text(actual),
            "delayed_stateless_return": _text(delayed),
            "immediate_stateless_return": _text(immediate),
            "net_harm_P_minus_A": _text(net_harm),
            "positive_harm_components": {
                key: _text(value) for key, value in components.items()
            },
            "component_shares_of_net_harm": {
                key: None if value is None else _text(value)
                for key, value in shares.items()
            },
        },
        "material_harm_threshold": _text(_MATERIAL_HARM),
        "primary_share_threshold": _text(_PRIMARY_SHARE),
        "tie_tolerance": _text(_TOLERANCE),
    }


def _transition_ledger(
    data: _base._AlignedData,
    regime_by_date: Mapping[date, str],
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
) -> list[dict[str, object]]:
    cost_id = "moderate_friction"
    by_path = {
        path_id: {
            item.date: item for item in simulations[path_id][cost_id].records
        }
        for path_id in _PATH_IDS
    }
    data_index = {item: index for index, item in enumerate(data.dates)}
    ledger = []
    previous_high: bool | None = None
    for on_date in data.dates:
        current_high = regime_by_date[on_date] == "high_vol"
        if previous_high is None:
            previous_high = current_high
            continue
        changed = current_high != previous_high
        if changed and config.oos_start <= on_date <= config.oos_end:
            index = data_index[on_date]
            fill_date = data.dates[index + 1] if index + 1 < len(data.dates) else None
            if fill_date is not None and fill_date in by_path[_PARENT_ID]:
                path_records = {}
                for path_id in _PATH_IDS:
                    record = by_path[path_id][fill_date]
                    path_records[path_id] = {
                        "posttrade_exposure": _text(
                            sum(record.posttrade_weights.values(), _ZERO)
                        ),
                        "turnover": _text(record.turnover),
                        "trade_count": (
                            record.buy_fill_count + record.sell_fill_count
                        ),
                    }
                ledger.append(
                    {
                        "signal_date": on_date.isoformat(),
                        "scheduled_fill_date": fill_date.isoformat(),
                        "transition": (
                            "enter_high_vol" if current_high else "exit_high_vol"
                        ),
                        "parent_desired_exposure_on_signal": _text(
                            _desired_exposure(by_path[_PARENT_ID][on_date])
                        ),
                        "fill_date_paths": path_records,
                    }
                )
        previous_high = current_high
    return ledger


def _artifact_manifest(
    config: NexusTradeHighVolatilityAttributionConfig,
    *,
    preregistration_path: Path,
    result_path: Path,
    summary_path: Path,
) -> dict[str, object]:
    input_paths = (
        config.preregistration_path,
        config.data_path,
        config.data_manifest_path,
        config.v564_protocol_path,
        config.v564_engine_path,
        config.v565_protocol_path,
        config.v565_engine_path,
        config.v565_preregistration_path,
        config.v565_result_path,
        config.v565_summary_path,
        config.v565_manifest_path,
    )
    return {
        "record_type": "nexustrade_high_volatility_attribution_manifest",
        "schema_version": _SCHEMA_VERSION,
        "protocol_id": _PROTOCOL_ID,
        "diagnostic_only": True,
        "candidate_created": False,
        "artifacts": [
            _artifact_record(preregistration_path),
            _artifact_record(result_path),
            _artifact_record(summary_path),
        ],
        "inputs": [_artifact_record(path) for path in input_paths],
        "manifest_self_hash_embedded": False,
        "parameter_search_performed": False,
        "paper_promotion_allowed": False,
        "safety": _safety_payload(),
    }


def _render_summary(result: Mapping[str, object]) -> str:
    diagnostic = _mapping(
        result.get("diagnostic_classification"), "diagnostic classification"
    )
    moderate = _mapping(
        diagnostic.get("moderate_full_oos"), "moderate full OOS"
    )
    attribution = _mapping(result.get("attribution"), "attribution")
    cost_results = attribution.get("cost_results")
    if not isinstance(cost_results, list):
        raise ValidationError("attribution cost results must be a list.")
    moderate_cost = next(
        _mapping(item, "attribution cost result")
        for item in cost_results
        if _mapping(item, "attribution cost result").get("cost_id")
        == "moderate_friction"
    )
    windows = moderate_cost.get("windows")
    if not isinstance(windows, list):
        raise ValidationError("moderate attribution windows must be a list.")
    oos = _window_by_id(windows, "oos")
    fold_two = _window_by_id(windows, "oos_walk_forward_2")
    fold_three = _window_by_id(windows, "oos_walk_forward_3")
    effects = _mapping(oos.get("return_effects"), "OOS return effects")
    sessions = _mapping(oos.get("session_attribution"), "OOS sessions")
    turnover = _mapping(
        oos.get("turnover_trade_attribution"), "OOS turnover attribution"
    )
    turnover_paths = _records_by_id(turnover.get("paths"), "path_id")
    contributions = _mapping(
        oos.get("constituent_contribution_attribution"),
        "OOS constituent attribution",
    )
    symbol_contributions = contributions.get("symbols")
    if not isinstance(symbol_contributions, list):
        raise ValidationError("constituent attribution symbols must be a list.")
    largest_symbols = sorted(
        (
            _mapping(item, "constituent attribution symbol")
            for item in symbol_contributions
        ),
        key=lambda item: abs(_base._decimal(item["total_effect"])),
        reverse=True,
    )[:5]

    def count(name: str) -> object:
        return _mapping(sessions.get(name), name).get("count")

    def fold_line(window: Mapping[str, object]) -> str:
        window_effects = _mapping(
            window.get("return_effects"), "fold return effects"
        )
        drawdowns = _mapping(window.get("drawdown_paths"), "fold drawdowns")
        parent_drawdown = _mapping(drawdowns.get(_PARENT_ID), "parent drawdown")
        actual_drawdown = _mapping(drawdowns.get(_ACTUAL_ID), "actual drawdown")
        return (
            f"- `{window.get('window_id')}`: total A-P "
            f"`{window_effects.get('total_effect_A_minus_P')}`; classification "
            f"`{window_effects.get('classification_effect_I_minus_P')}`; delay "
            f"`{window_effects.get('execution_delay_effect_D_minus_I')}`; "
            f"stateful carry "
            f"`{window_effects.get('stateful_carry_effect_A_minus_D')}`; "
            f"max drawdown P/A "
            f"`{parent_drawdown.get('max_drawdown')}`/"
            f"`{actual_drawdown.get('max_drawdown')}`."
        )

    lines = [
        "# V5.66 NexusTrade High-Volatility Attribution",
        "",
        f"- Diagnostic classification: `{diagnostic.get('classification')}`.",
        f"- Primary driver: `{diagnostic.get('primary_driver')}`.",
        f"- Moderate full-OOS return P/A/D/I: "
        f"`{moderate.get('parent_return')}`/"
        f"`{moderate.get('actual_return')}`/"
        f"`{moderate.get('delayed_stateless_return')}`/"
        f"`{moderate.get('immediate_stateless_return')}`.",
        f"- Net harm P-A: `{moderate.get('net_harm_P_minus_A')}`; "
        f"classification I-P `{effects.get('classification_effect_I_minus_P')}`; "
        f"delay D-I `{effects.get('execution_delay_effect_D_minus_I')}`; "
        f"stateful carry A-D "
        f"`{effects.get('stateful_carry_effect_A_minus_D')}`.",
        f"- Full-OOS sessions: high-volatility `{count('high_volatility_sessions')}`; "
        f"parent risk-on/high-volatility "
        f"`{count('parent_risk_on_high_volatility_sessions')}`; "
        f"A-vs-P target divergence "
        f"`{count('actual_vs_parent_target_divergence')}`; stateful carry "
        f"`{count('stateful_carry_target_divergence_A_vs_D')}`; "
        f"D-vs-I posttrade delay "
        f"`{count('execution_delay_posttrade_divergence_D_vs_I')}`.",
        f"- Full-OOS one-way turnover P/A/D/I: "
        f"`{turnover.get('parent_one_way_turnover')}`/"
        f"`{turnover_paths[_ACTUAL_ID].get('one_way_turnover')}`/"
        f"`{turnover_paths[_DELAYED_ID].get('one_way_turnover')}`/"
        f"`{turnover_paths[_IMMEDIATE_ID].get('one_way_turnover')}`.",
        "- Candidate created: `false`.",
        "- Route created: `false`.",
        "- V5.64 and V5.65 frozen: `true`.",
        "- Parameter search: `false`.",
        "- Source metrics used: `false`.",
        "",
        "## Fold Attribution",
        "",
        fold_line(fold_two),
        fold_line(fold_three),
        "",
        "## Largest Absolute Constituent Effects",
        "",
        *[
            f"- `{item.get('symbol')}`: `{item.get('total_effect')}` "
            f"(`{item.get('total_label')}`)."
            for item in largest_symbols
        ],
        "",
        "Constituent effects are arithmetic gross contributions and are not "
        "the compounded portfolio return decomposition.",
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


def _validate_dependencies(
    config: NexusTradeHighVolatilityAttributionConfig,
) -> dict[str, str]:
    specs = {
        "tracked_preregistration_sha256": (
            config.preregistration_path,
            config.expected_preregistration_sha256,
        ),
        "canonical_data_sha256": (
            config.data_path,
            config.expected_data_sha256,
        ),
        "canonical_manifest_sha256": (
            config.data_manifest_path,
            config.expected_data_manifest_sha256,
        ),
        "v564_protocol_sha256": (
            config.v564_protocol_path,
            config.expected_v564_protocol_sha256,
        ),
        "v564_engine_sha256": (
            config.v564_engine_path,
            config.expected_v564_engine_sha256,
        ),
        "v565_protocol_sha256": (
            config.v565_protocol_path,
            config.expected_v565_protocol_sha256,
        ),
        "v565_engine_sha256": (
            config.v565_engine_path,
            config.expected_v565_engine_sha256,
        ),
        "v565_preregistration_sha256": (
            config.v565_preregistration_path,
            config.expected_v565_preregistration_sha256,
        ),
        "v565_result_sha256": (
            config.v565_result_path,
            config.expected_v565_result_sha256,
        ),
        "v565_summary_sha256": (
            config.v565_summary_path,
            config.expected_v565_summary_sha256,
        ),
        "v565_manifest_sha256": (
            config.v565_manifest_path,
            config.expected_v565_manifest_sha256,
        ),
    }
    verified = {}
    for name, (path, expected) in specs.items():
        actual = _sha256(path)
        if actual != expected:
            raise ValidationError(f"{name} does not match the pinned dependency.")
        verified[name] = actual
    return verified


def _safety_payload() -> dict[str, object]:
    return {
        **_base._safety_payload(),
        "diagnostic_only": True,
        "candidate_created": False,
        "route_created": False,
        "preview_review_created": False,
        "shadow_created": False,
        "v5_64_frozen": True,
        "v5_65_frozen": True,
        "parameter_search_performed": False,
        "paper_submission_performed": False,
        "v5_57_sleeve_ownership_unchanged": True,
        "v5_57_reconciliation_unchanged": True,
        "v5_57_auditing_unchanged": True,
        "v5_57_caps_unchanged": True,
        "max_entry_order_notional_usd": "25",
        "max_aggregate_marked_spy_entry_exposure_usd": "60",
        "max_broker_orders_per_secure_cycle": 1,
        "max_sleeve_intents_per_utc_day": 2,
    }


def _date_summary(values: Sequence[date]) -> dict[str, object]:
    return {
        "count": len(values),
        "first_date": None if not values else values[0].isoformat(),
        "last_date": None if not values else values[-1].isoformat(),
        "dates": [item.isoformat() for item in values],
    }


def _desired_exposure(record: _base._DayRecord) -> Decimal:
    return sum(record.desired_target.values(), _ZERO)


def _effect_label(value: Decimal) -> str:
    if value < -_TOLERANCE:
        return "missed_return"
    if value > _TOLERANCE:
        return "avoided_loss_or_benefit"
    return "neutral"


def _require_tolerance(value: Decimal, field_name: str) -> None:
    if abs(value) > _TOLERANCE:
        raise ValidationError(f"{field_name} exceeds preregistered tolerance.")


def _window_by_id(
    records: Sequence[Mapping[str, object]], window_id: str
) -> Mapping[str, object]:
    for record in records:
        if record.get("window_id") == window_id:
            return record
    raise ValidationError(f"window is missing: {window_id}")


def _records_by_id(value: object, field_name: str) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} records must be a list.")
    result = {}
    for item in value:
        record = _mapping(item, f"{field_name} record")
        key = record.get(field_name)
        if not isinstance(key, str) or not key:
            raise ValidationError(f"{field_name} record identity is missing.")
        result[key] = record
    return result


def _artifact_record(path: Path) -> dict[str, object]:
    return {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}


def _load_json(path: Path, field_name: str) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError(f"{field_name} is missing.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field_name} is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must contain an object.")
    return value


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file is missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value.strip():
        return Path(value.strip())
    raise ValidationError(f"{field_name} must be a path.")


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _text(value: Decimal) -> str:
    return _base._decimal_text(value)


def _config(
    value: NexusTradeHighVolatilityAttributionConfig,
) -> NexusTradeHighVolatilityAttributionConfig:
    if type(value) is not NexusTradeHighVolatilityAttributionConfig:
        raise ValidationError(
            "config must be NexusTradeHighVolatilityAttributionConfig."
        )
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the preregistered V5.66 attribution-only diagnostic."
    )
    parser.add_argument("--output-root", type=Path, default=_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--data-path", type=Path, default=_DEFAULT_DATA_PATH)
    parser.add_argument(
        "--data-manifest-path", type=Path, default=_DEFAULT_DATA_MANIFEST_PATH
    )
    parser.add_argument(
        "--preregistration-path", type=Path, default=_DEFAULT_PREREGISTRATION_PATH
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_nexustrade_high_volatility_attribution(
        NexusTradeHighVolatilityAttributionConfig(
            output_root=args.output_root,
            data_path=args.data_path,
            data_manifest_path=args.data_manifest_path,
            preregistration_path=args.preregistration_path,
        )
    )
    if args.format == "json":
        print(json.dumps(_base._json_safe(result), indent=2, sort_keys=True))
    else:
        diagnostic = _mapping(
            result.get("diagnostic_classification"), "diagnostic classification"
        )
        print("nexustrade_high_volatility_attribution_status=completed")
        print(f"diagnostic_classification={diagnostic['classification']}")
        print(f"primary_driver={diagnostic['primary_driver']}")
        print(f"artifact_manifest_path={result['artifact_manifest_path']}")
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
        print("candidate_created=false")
        print("route_created=false")
        print("paper_promotion_allowed=false")
        print("network_access_attempted=false")
        print("credential_access_attempted=false")
        print("broker_access_attempted=false")
        print("paper_mutation_performed=false")
        print("live_activity_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
