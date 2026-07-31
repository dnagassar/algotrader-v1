"""Attribution-only diagnostic for the frozen V5.67 risk-balanced candidate."""

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
from algotrader.research import nexustrade_monthly_risk_balanced_allocation as _risk

__all__ = [
    "NexusTradeRiskBalancedAttributionConfig",
    "build_nexustrade_risk_balanced_attribution_preregistration",
    "run_nexustrade_risk_balanced_attribution",
]


_PROTOCOL_ID = "v5_68_nexustrade_risk_balanced_attribution_v1"
_DIAGNOSTIC_ID = "nexustrade_risk_balanced_loss_attribution_only"
_RECORD_TYPE = "nexustrade_risk_balanced_attribution_result"
_SCHEMA_VERSION = 1
_PARENT_ID = _base.NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
_RISK_SIZING_ID = "diagnostic_inverse_volatility_sizing_parent_state"
_PARTIAL_CASH_ID = "diagnostic_subfive_partial_cash_parent_state"
_ACTUAL_ID = _risk.NEXUSTRADE_MONTHLY_RISK_BALANCED_ID
_PATH_IDS = (_PARENT_ID, _RISK_SIZING_ID, _PARTIAL_CASH_ID, _ACTUAL_ID)
_COUNTERFACTUAL_IDS = {_RISK_SIZING_ID, _PARTIAL_CASH_ID}
_SPY = "SPY"
_ZERO = Decimal("0")
_ONE = Decimal("1")
_TOLERANCE = Decimal("1e-24")
_MATERIAL_HARM = Decimal("0.005")
_PRIMARY_SHARE = Decimal("0.50")
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/v5_68_nexustrade_risk_balanced_attribution"
)
_DEFAULT_DATA_PATH = Path(
    "runs/operator_input/multi_etf_adjusted_daily_canonical.csv"
)
_DEFAULT_DATA_MANIFEST_PATH = Path(
    "runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json"
)
_DEFAULT_PREREGISTRATION_PATH = Path(
    "docs/design/v5_68_nexustrade_risk_balanced_attribution.md"
)
_DEFAULT_V564_PROTOCOL_PATH = Path(
    "docs/design/v5_64_nexustrade_monthly_independent_replication.md"
)
_DEFAULT_V564_ENGINE_PATH = Path(
    "src/algotrader/research/nexustrade_monthly_independent_replication.py"
)
_DEFAULT_V567_PROTOCOL_PATH = Path(
    "docs/design/v5_67_nexustrade_monthly_risk_balanced_allocation.md"
)
_DEFAULT_V567_ENGINE_PATH = Path(
    "src/algotrader/research/nexustrade_monthly_risk_balanced_allocation.py"
)
_DEFAULT_V567_ROOT = Path(
    "runs/v5_67_nexustrade_monthly_risk_balanced_allocation"
)
_EXPECTED_PREREGISTRATION_SHA256 = (
    "d0d89a0807cf8db41cb7377a40b6af1342625b4ff32fc8e56f53b5f2d9ec5513"
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
_EXPECTED_V567_PROTOCOL_SHA256 = (
    "17f86b8eafd7e67e6816603cb1bf06fa96a734c7b7d9094d30e68ec85690505e"
)
_EXPECTED_V567_ENGINE_SHA256 = (
    "2c669051c6c3fc877cd86d482579ffa711e7d68724e5dffb117d32080aef1188"
)
_EXPECTED_V567_PREREGISTRATION_SHA256 = (
    "6ee1e62efb4b20f94896b2e29fb022081b6c762f4c7da8de7f67f631bc747d6e"
)
_EXPECTED_V567_RESULT_SHA256 = (
    "76de6eabe410c082b53ff123af31dccdf4704f78c3380bd6d6e8e8de24b2276f"
)
_EXPECTED_V567_SUMMARY_SHA256 = (
    "99fac23b5cbeae076bb0249d6741e98ca95a433b11cad994ed92abd2bcf886f1"
)
_EXPECTED_V567_MANIFEST_SHA256 = (
    "0bcf77f91d4b92a9d85f566e0e0c946fc19be4b56bd28982eeb741d23dee1519"
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
class NexusTradeRiskBalancedAttributionConfig:
    """Pinned local inputs for the V5.68 diagnostic."""

    output_root: Path | str = _DEFAULT_OUTPUT_ROOT
    data_path: Path | str = _DEFAULT_DATA_PATH
    data_manifest_path: Path | str = _DEFAULT_DATA_MANIFEST_PATH
    preregistration_path: Path | str = _DEFAULT_PREREGISTRATION_PATH
    v564_protocol_path: Path | str = _DEFAULT_V564_PROTOCOL_PATH
    v564_engine_path: Path | str = _DEFAULT_V564_ENGINE_PATH
    v567_protocol_path: Path | str = _DEFAULT_V567_PROTOCOL_PATH
    v567_engine_path: Path | str = _DEFAULT_V567_ENGINE_PATH
    v567_preregistration_path: Path | str = (
        _DEFAULT_V567_ROOT / "preregistration.json"
    )
    v567_result_path: Path | str = (
        _DEFAULT_V567_ROOT / "risk_balanced_results.json"
    )
    v567_summary_path: Path | str = (
        _DEFAULT_V567_ROOT / "risk_balanced_summary.md"
    )
    v567_manifest_path: Path | str = _DEFAULT_V567_ROOT / "manifest.json"
    expected_preregistration_sha256: str = _EXPECTED_PREREGISTRATION_SHA256
    expected_data_sha256: str = _EXPECTED_DATA_SHA256
    expected_data_manifest_sha256: str = _EXPECTED_DATA_MANIFEST_SHA256
    expected_v564_protocol_sha256: str = _EXPECTED_V564_PROTOCOL_SHA256
    expected_v564_engine_sha256: str = _EXPECTED_V564_ENGINE_SHA256
    expected_v567_protocol_sha256: str = _EXPECTED_V567_PROTOCOL_SHA256
    expected_v567_engine_sha256: str = _EXPECTED_V567_ENGINE_SHA256
    expected_v567_preregistration_sha256: str = (
        _EXPECTED_V567_PREREGISTRATION_SHA256
    )
    expected_v567_result_sha256: str = _EXPECTED_V567_RESULT_SHA256
    expected_v567_summary_sha256: str = _EXPECTED_V567_SUMMARY_SHA256
    expected_v567_manifest_sha256: str = _EXPECTED_V567_MANIFEST_SHA256
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
            "v567_protocol_path",
            "v567_engine_path",
            "v567_preregistration_path",
            "v567_result_path",
            "v567_summary_path",
            "v567_manifest_path",
        ):
            object.__setattr__(self, name, _path(getattr(self, name), name))
        for name in (
            "expected_preregistration_sha256",
            "expected_data_sha256",
            "expected_data_manifest_sha256",
            "expected_v564_protocol_sha256",
            "expected_v564_engine_sha256",
            "expected_v567_protocol_sha256",
            "expected_v567_engine_sha256",
            "expected_v567_preregistration_sha256",
            "expected_v567_result_sha256",
            "expected_v567_summary_sha256",
            "expected_v567_manifest_sha256",
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
        self.risk_config()

    def risk_config(self) -> _risk.NexusTradeMonthlyRiskBalancedConfig:
        """Return the frozen V5.67 mechanics configuration."""

        return _risk.NexusTradeMonthlyRiskBalancedConfig(
            output_root=self.output_root,
            data_path=self.data_path,
            data_manifest_path=self.data_manifest_path,
            preregistration_path=self.v567_protocol_path,
            parent_protocol_path=self.v564_protocol_path,
            parent_engine_path=self.v564_engine_path,
            expected_preregistration_sha256=self.expected_v567_protocol_sha256,
            expected_parent_protocol_sha256=self.expected_v564_protocol_sha256,
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


def build_nexustrade_risk_balanced_attribution_preregistration(
    config: NexusTradeRiskBalancedAttributionConfig,
) -> dict[str, object]:
    """Build the fixed diagnostic contract without loading bars or outcomes."""

    checked = _config(config)
    hashes = _validate_dependencies(checked)
    return {
        "record_type": "nexustrade_risk_balanced_attribution_preregistration",
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
            "R": _RISK_SIZING_ID,
            "C": _PARTIAL_CASH_ID,
            "A": _ACTUAL_ID,
            "diagnostic_counterfactuals_are_candidates": False,
        },
        "return_decomposition": {
            "pure_sizing_effect": "R-P",
            "subfive_partial_cash_effect": "C-R",
            "state_carry_effect": "A-C",
            "total_effect": "A-P",
            "identity": "(R-P)+(C-R)+(A-C)=A-P",
            "reconciliation_tolerance": _text(_TOLERANCE),
        },
        "diagnostic_classification": {
            "cost_id": "moderate_friction",
            "window_id": "oos",
            "material_harm_threshold": _text(_MATERIAL_HARM),
            "primary_share_threshold": _text(_PRIMARY_SHARE),
            "tie_tolerance": _text(_TOLERANCE),
            "tie_result": "mixed_harm",
            "creates_route": False,
        },
        "parent_state_contract": {
            "paths_using_parent_filled_state": ["R", "C"],
            "path_using_own_filled_state": "A",
            "shadow_parent_exact_reproduction_required": True,
            "diagnostic_fills_update_parent_state": False,
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


def run_nexustrade_risk_balanced_attribution(
    config: NexusTradeRiskBalancedAttributionConfig,
) -> dict[str, object]:
    """Reproduce the frozen paths and write deterministic attribution output."""

    checked = _config(config)
    preregistration = build_nexustrade_risk_balanced_attribution_preregistration(
        checked
    )
    frozen_result = _load_json(checked.v567_result_path, "v567_result_path")
    risk_config = checked.risk_config()
    base_config = risk_config.base_config()
    data = _base._load_aligned_data(base_config)
    _base._validate_chronology(data, base_config)
    frozen_structured = _reproduce_frozen_v567(
        checked,
        risk_config,
        base_config,
        data,
        frozen_result,
    )
    result = _build_result(
        checked,
        risk_config,
        base_config,
        data,
        frozen_result,
        frozen_structured,
        preregistration,
    )

    checked.output_root.mkdir(parents=True, exist_ok=True)
    preregistration_path = checked.output_root / "preregistration.json"
    _base._write_json_atomic(preregistration_path, preregistration)
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
    config: NexusTradeRiskBalancedAttributionConfig,
    risk_config: _risk.NexusTradeMonthlyRiskBalancedConfig,
    base_config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    data: _base._AlignedData,
    frozen_result: Mapping[str, object],
    frozen_structured: Mapping[str, object],
    preregistration: Mapping[str, object],
) -> dict[str, object]:
    indicators = _base._build_indicators(data)
    simulations: dict[str, dict[str, _base._Simulation]] = {
        path_id: {} for path_id in _PATH_IDS
    }
    signal_ledger: list[dict[str, object]] | None = None
    for cost in _base._COST_ASSUMPTIONS:
        canonical_parent = _base._simulate_dynamic_candidate(
            data,
            indicators,
            base_config,
            cost,
            composite=True,
        )
        reproduced_parent, risk_sizing, partial_cash, ledger = (
            _simulate_parent_state_paths(
                data,
                indicators,
                base_config,
                cost,
                volatility_lookback=risk_config.volatility_lookback,
                max_target_weight=risk_config.max_target_weight,
            )
        )
        if reproduced_parent.records != canonical_parent.records:
            raise ValidationError(
                "diagnostic shadow parent does not reproduce frozen V5.64."
            )
        actual = _risk._simulate_risk_balanced_candidate(
            data,
            indicators,
            base_config,
            cost,
            volatility_lookback=risk_config.volatility_lookback,
            max_target_weight=risk_config.max_target_weight,
        )
        simulations[_PARENT_ID][cost.cost_id] = canonical_parent
        simulations[_RISK_SIZING_ID][cost.cost_id] = risk_sizing
        simulations[_PARTIAL_CASH_ID][cost.cost_id] = partial_cash
        simulations[_ACTUAL_ID][cost.cost_id] = actual
        if cost.cost_id == "source_fee_only":
            signal_ledger = ledger
    if signal_ledger is None:
        raise ValidationError("source-fee signal ledger was not produced.")

    windows = _base._reporting_windows(base_config)
    metric_book = _metric_book(simulations, windows)
    reproduction = _validate_frozen_path_reproduction(
        frozen_result,
        simulations,
        metric_book,
        windows,
        base_config,
        frozen_structured,
    )
    attribution = _build_decomposition(simulations, metric_book, windows)
    classification = _diagnostic_classification(attribution)
    ledger_summary = _signal_ledger_summary(signal_ledger, base_config)

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
            "adjustment_semantics": "split_and_dividend_adjusted_eod_price",
            "brk_b_mapping": "BRK-B->BRK-B",
        },
        "chronology": preregistration["chronology"],
        "path_definitions": preregistration["path_definitions"],
        "frozen_reproduction": reproduction,
        "path_results": [
            {
                "path_id": path_id,
                "diagnostic_counterfactual": path_id in _COUNTERFACTUAL_IDS,
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
        "attribution": attribution,
        "diagnostic_classification": classification,
        "parent_state_signal_ledger": signal_ledger,
        "parent_state_signal_ledger_summary": ledger_summary,
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
            "R and C are diagnostic parent-state counterfactuals, not candidates.",
            "Total-return effects reconcile additively; maximum drawdown is "
            "path-dependent and is reported without additive attribution.",
            "Gross contribution sums are arithmetic diagnostics and do not "
            "replace compounded portfolio-return attribution.",
            "The diagnostic does not resolve authentic NexusTrade data mode, "
            "slippage, warm-up, fill behavior, or lineage.",
        ],
    }


def _simulate_parent_state_paths(
    data: _base._AlignedData,
    indicators: Mapping[str, Mapping[str, tuple[Decimal | None, ...]]],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    cost: _base._CostAssumption,
    *,
    volatility_lookback: int,
    max_target_weight: Decimal,
) -> tuple[
    _base._Simulation,
    _base._Simulation,
    _base._Simulation,
    list[dict[str, object]],
]:
    start_index = next(
        index for index, item in enumerate(data.dates) if item >= config.train_start
    )
    end_index = max(
        index for index, item in enumerate(data.dates) if item <= config.oos_end
    )
    if start_index == 0:
        raise ValidationError("training requires a prior signal session.")

    parent_weights = _base._zero_stock_weights()
    risk_weights = _base._zero_stock_weights()
    cash_weights = _base._zero_stock_weights()
    parent_last_buy: date | None = None
    parent_last_sell: date | None = None
    signal_index = start_index - 1
    parent_source = _base._eligible_target(data, indicators, signal_index)
    actual_source = _risk._risk_balanced_target(
        data,
        indicators,
        signal_index,
        volatility_lookback=volatility_lookback,
        max_target_weight=max_target_weight,
    )
    risk_source = _select_pure_sizing_target(parent_source, actual_source)
    previous_trend = _base._spy_regime_on(indicators, signal_index)
    parent_desired = (
        parent_source if previous_trend else _base._zero_stock_weights()
    )
    risk_desired = risk_source if previous_trend else _base._zero_stock_weights()
    cash_desired = (
        actual_source if previous_trend else _base._zero_stock_weights()
    )
    parent_pending: dict[str, Decimal] | None = dict(parent_desired)
    risk_pending: dict[str, Decimal] | None = dict(risk_desired)
    cash_pending: dict[str, Decimal] | None = dict(cash_desired)
    parent_records: list[_base._DayRecord] = []
    risk_records: list[_base._DayRecord] = []
    cash_records: list[_base._DayRecord] = []
    ledger: list[dict[str, object]] = []

    for index in range(start_index, end_index + 1):
        parent_step = _base._portfolio_step(
            data,
            index,
            parent_weights,
            parent_pending,
            cost,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        risk_step = _base._portfolio_step(
            data,
            index,
            risk_weights,
            risk_pending,
            cost,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        cash_step = _base._portfolio_step(
            data,
            index,
            cash_weights,
            cash_pending,
            cost,
            _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
        )
        parent_weights = parent_step[6]
        risk_weights = risk_step[6]
        cash_weights = cash_step[6]
        if parent_step[2]:
            parent_last_buy = data.dates[index]
        if parent_step[3]:
            parent_last_sell = data.dates[index]

        rebalance_ready = _base._rebalance_ready(
            data.dates[index],
            parent_last_buy,
            parent_last_sell,
        )
        if rebalance_ready:
            parent_source = _base._eligible_target(data, indicators, index)
            actual_source = _risk._risk_balanced_target(
                data,
                indicators,
                index,
                volatility_lookback=volatility_lookback,
                max_target_weight=max_target_weight,
            )
            risk_source = _select_pure_sizing_target(
                parent_source,
                actual_source,
            )
        current_trend = _base._spy_regime_on(indicators, index)
        parent_desired = (
            parent_source if current_trend else _base._zero_stock_weights()
        )
        risk_desired = (
            risk_source if current_trend else _base._zero_stock_weights()
        )
        cash_desired = (
            actual_source if current_trend else _base._zero_stock_weights()
        )
        scheduled = rebalance_ready or current_trend != previous_trend
        parent_pending = dict(parent_desired) if scheduled else None
        risk_pending = dict(risk_desired) if scheduled else None
        cash_pending = dict(cash_desired) if scheduled else None

        if rebalance_ready:
            eligible_count = sum(
                1
                for value in parent_source.values()
                if value > _base._WEIGHT_TOLERANCE
            )
            fill_date = (
                data.dates[index + 1]
                if index + 1 <= end_index
                else None
            )
            ledger.append(
                {
                    "signal_date": data.dates[index].isoformat(),
                    "scheduled_fill_date": (
                        None if fill_date is None else fill_date.isoformat()
                    ),
                    "in_training": (
                        config.train_start <= data.dates[index] <= config.train_end
                    ),
                    "in_oos": config.oos_start <= data.dates[index] <= config.oos_end,
                    "spy_risk_on": current_trend,
                    "eligible_count": eligible_count,
                    "pure_sizing_source_target_changed": _base._weights_differ(
                        risk_source,
                        parent_source,
                        _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
                    ),
                    "partial_cash_source_target_changed": _base._weights_differ(
                        actual_source,
                        risk_source,
                        _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
                    ),
                    "risk_gated_R_vs_P_target_changed": _base._weights_differ(
                        risk_desired,
                        parent_desired,
                        _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
                    ),
                    "risk_gated_C_vs_R_target_changed": _base._weights_differ(
                        cash_desired,
                        risk_desired,
                        _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
                    ),
                    "parent_source_exposure": _text(
                        sum(parent_source.values(), _ZERO)
                    ),
                    "risk_sizing_source_exposure": _text(
                        sum(risk_source.values(), _ZERO)
                    ),
                    "partial_cash_source_exposure": _text(
                        sum(actual_source.values(), _ZERO)
                    ),
                }
            )

        parent_records.append(_day_record(data.dates[index], parent_step, parent_desired))
        risk_records.append(_day_record(data.dates[index], risk_step, risk_desired))
        cash_records.append(_day_record(data.dates[index], cash_step, cash_desired))
        previous_trend = current_trend

    return (
        _base._Simulation(_PARENT_ID, cost, tuple(parent_records)),
        _base._Simulation(_RISK_SIZING_ID, cost, tuple(risk_records)),
        _base._Simulation(_PARTIAL_CASH_ID, cost, tuple(cash_records)),
        ledger,
    )


def _select_pure_sizing_target(
    parent_equal_weight: Mapping[str, Decimal],
    v567_target: Mapping[str, Decimal],
) -> dict[str, Decimal]:
    """Exclude the fewer-than-five cash effect from the sizing diagnostic."""

    symbols = _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS
    if set(parent_equal_weight) != set(symbols) or set(v567_target) != set(symbols):
        raise ValidationError("diagnostic targets must contain the canonical stocks.")
    eligible_count = sum(
        1
        for symbol in symbols
        if parent_equal_weight[symbol] > _base._WEIGHT_TOLERANCE
    )
    selected = parent_equal_weight if eligible_count <= 5 else v567_target
    target = {symbol: selected[symbol] for symbol in symbols}
    _base._validate_target_weights(target, symbols)
    return target


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


def _reproduce_frozen_v567(
    config: NexusTradeRiskBalancedAttributionConfig,
    risk_config: _risk.NexusTradeMonthlyRiskBalancedConfig,
    base_config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    data: _base._AlignedData,
    frozen_result: Mapping[str, object],
) -> dict[str, object]:
    parent_hashes = _risk._validate_parent_artifacts(risk_config)
    parent_reproduction = _risk._reproduce_frozen_parent(
        risk_config,
        base_config,
        data,
        parent_hashes,
    )
    computed_preregistration = (
        _risk.build_nexustrade_monthly_risk_balanced_preregistration(risk_config)
    )
    recorded_preregistration = _load_json(
        config.v567_preregistration_path,
        "v567_preregistration_path",
    )
    if computed_preregistration != recorded_preregistration:
        raise ValidationError("frozen V5.67 preregistration reproduction failed.")
    computed_result = _risk._build_result(
        risk_config,
        base_config,
        data,
        computed_preregistration,
        parent_reproduction,
    )
    if computed_result != frozen_result:
        raise ValidationError("frozen V5.67 result reproduction failed.")
    recorded_summary = config.v567_summary_path.read_text(encoding="utf-8")
    if _risk._render_summary(computed_result) != recorded_summary:
        raise ValidationError("frozen V5.67 summary reproduction failed.")
    return {
        "v567_preregistration_structured_equality": True,
        "v567_result_structured_equality": True,
        "v567_summary_text_equality": True,
        "v564_parent_reproduction": parent_reproduction,
    }


def _validate_frozen_path_reproduction(
    frozen_result: Mapping[str, object],
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    windows: Sequence[_base.ReplicationWindow],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
    frozen_structured: Mapping[str, object],
) -> dict[str, object]:
    candidate = _mapping(frozen_result.get("candidate"), "frozen candidate")
    if candidate.get("candidate_id") != _ACTUAL_ID:
        raise ValidationError("frozen V5.67 candidate identity does not match.")
    actual_costs = _records_by_id(candidate.get("cost_results"), "cost_id")
    parent_costs = _records_by_id(
        frozen_result.get("frozen_parent_cost_results"),
        "cost_id",
    )
    checked_fields = 0
    for cost in _base._COST_ASSUMPTIONS:
        for path_id, frozen_costs in (
            (_ACTUAL_ID, actual_costs),
            (_PARENT_ID, parent_costs),
        ):
            frozen_cost = frozen_costs.get(cost.cost_id)
            if frozen_cost is None:
                raise ValidationError("frozen V5.67 cost result is missing.")
            frozen_windows = _records_by_id(
                frozen_cost.get("window_metrics"),
                "window_id",
            )
            for window in windows:
                expected = frozen_windows.get(window.window_id)
                actual = metric_book[path_id][cost.cost_id][window.window_id]
                if expected != actual:
                    raise ValidationError(
                        "recomputed frozen V5.67 window metrics do not match."
                    )
                checked_fields += len(actual)
            target_hash = _base._target_vector_sha256(
                simulations[path_id][cost.cost_id],
                config.train_start,
                config.oos_end,
            )
            if target_hash != frozen_cost.get("target_vector_sha256"):
                raise ValidationError("frozen full target vector does not match.")
            oos_hash = _base._target_vector_sha256(
                simulations[path_id][cost.cost_id],
                config.oos_start,
                config.oos_end,
            )
            if oos_hash != frozen_cost.get("oos_target_vector_sha256"):
                raise ValidationError("frozen OOS target vector does not match.")
    return {
        "passed": True,
        **dict(frozen_structured),
        "frozen_v567_route": candidate.get("route"),
        "window_metric_field_comparisons": checked_fields,
        "full_target_hash_comparisons": 8,
        "oos_target_hash_comparisons": 8,
    }


def _build_decomposition(
    simulations: Mapping[str, Mapping[str, _base._Simulation]],
    metric_book: Mapping[str, Mapping[str, Mapping[str, Mapping[str, object]]]],
    windows: Sequence[_base.ReplicationWindow],
) -> dict[str, object]:
    costs = []
    for cost in _base._COST_ASSUMPTIONS:
        window_records = []
        for window in windows:
            metrics = {
                path_id: metric_book[path_id][cost.cost_id][window.window_id]
                for path_id in _PATH_IDS
            }
            returns = {
                path_id: _base._decimal(metrics[path_id]["total_return"])
                for path_id in _PATH_IDS
            }
            sizing = returns[_RISK_SIZING_ID] - returns[_PARENT_ID]
            partial_cash = returns[_PARTIAL_CASH_ID] - returns[_RISK_SIZING_ID]
            state = returns[_ACTUAL_ID] - returns[_PARTIAL_CASH_ID]
            total = returns[_ACTUAL_ID] - returns[_PARENT_ID]
            residual = total - (sizing + partial_cash + state)
            _require_tolerance(residual, "return attribution residual")
            contribution = _contribution_attribution(
                simulations,
                cost.cost_id,
                window,
            )
            session = _session_attribution(
                simulations,
                cost.cost_id,
                window,
            )
            window_records.append(
                {
                    "window_id": window.window_id,
                    "path_metrics": metrics,
                    "return_effects": {
                        "pure_sizing_effect_R_minus_P": _text(sizing),
                        "subfive_partial_cash_effect_C_minus_R": _text(
                            partial_cash
                        ),
                        "state_carry_effect_A_minus_C": _text(state),
                        "total_effect_A_minus_P": _text(total),
                        "reconciliation_residual": _text(residual),
                        "passed": abs(residual) <= _TOLERANCE,
                    },
                    "drawdown_paths": {
                        path_id: {
                            "max_drawdown": metrics[path_id]["max_drawdown"]
                        }
                        for path_id in _PATH_IDS
                    },
                    "session_attribution": session,
                    "constituent_contribution_attribution": contribution,
                    "turnover_trade_attribution": _turnover_attribution(metrics),
                }
            )
        costs.append({"cost_id": cost.cost_id, "windows": window_records})
    return {
        "primary_cost_id": "moderate_friction",
        "reconciliation_tolerance": _text(_TOLERANCE),
        "cost_results": costs,
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
    aggregate = {
        "pure_sizing_effect": _ZERO,
        "subfive_partial_cash_effect": _ZERO,
        "state_carry_effect": _ZERO,
        "total_effect": _ZERO,
        "residual": _ZERO,
    }
    symbols = []
    for symbol in _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS:
        values = {
            path_id: sum(
                (by_path[path_id][item].contributions[symbol] for item in dates),
                _ZERO,
            )
            for path_id in _PATH_IDS
        }
        sizing = values[_RISK_SIZING_ID] - values[_PARENT_ID]
        partial_cash = values[_PARTIAL_CASH_ID] - values[_RISK_SIZING_ID]
        state = values[_ACTUAL_ID] - values[_PARTIAL_CASH_ID]
        total = values[_ACTUAL_ID] - values[_PARENT_ID]
        residual = total - (sizing + partial_cash + state)
        _require_tolerance(residual, "symbol contribution residual")
        effects = {
            "pure_sizing_effect": sizing,
            "subfive_partial_cash_effect": partial_cash,
            "state_carry_effect": state,
            "total_effect": total,
            "residual": residual,
        }
        for name, value in effects.items():
            aggregate[name] += value
        symbols.append(
            {
                "symbol": symbol,
                **{name: _text(value) for name, value in effects.items()},
                "pure_sizing_label": _effect_label(sizing),
                "subfive_partial_cash_label": _effect_label(partial_cash),
                "state_carry_label": _effect_label(state),
                "total_label": _effect_label(total),
            }
        )
    _require_tolerance(aggregate["residual"], "aggregate contribution residual")
    return {
        "arithmetic_gross_contribution_only": True,
        "symbols": symbols,
        "aggregate": {name: _text(value) for name, value in aggregate.items()},
        "passed": abs(aggregate["residual"]) <= _TOLERANCE,
    }


def _session_attribution(
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

    def divergences(left: str, right: str, field_name: str) -> dict[str, object]:
        values = [
            item
            for item in dates
            if _base._weights_differ(
                getattr(by_path[left][item], field_name),
                getattr(by_path[right][item], field_name),
                _base.NEXUSTRADE_MONTHLY_STOCK_SYMBOLS,
            )
        ]
        return _date_summary(values)

    return {
        "pure_sizing_target_divergence_R_vs_P": divergences(
            _RISK_SIZING_ID, _PARENT_ID, "desired_target"
        ),
        "subfive_partial_cash_target_divergence_C_vs_R": divergences(
            _PARTIAL_CASH_ID, _RISK_SIZING_ID, "desired_target"
        ),
        "state_carry_target_divergence_A_vs_C": divergences(
            _ACTUAL_ID, _PARTIAL_CASH_ID, "desired_target"
        ),
        "total_target_divergence_A_vs_P": divergences(
            _ACTUAL_ID, _PARENT_ID, "desired_target"
        ),
        "pure_sizing_posttrade_divergence_R_vs_P": divergences(
            _RISK_SIZING_ID, _PARENT_ID, "posttrade_weights"
        ),
        "subfive_partial_cash_posttrade_divergence_C_vs_R": divergences(
            _PARTIAL_CASH_ID, _RISK_SIZING_ID, "posttrade_weights"
        ),
        "state_carry_posttrade_divergence_A_vs_C": divergences(
            _ACTUAL_ID, _PARTIAL_CASH_ID, "posttrade_weights"
        ),
    }


def _turnover_attribution(
    metrics: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    values = {
        path_id: _base._decimal(metrics[path_id]["one_way_turnover"])
        for path_id in _PATH_IDS
    }
    trades = {
        path_id: int(metrics[path_id]["trade_count"])
        for path_id in _PATH_IDS
    }
    return {
        "path_values": {
            path_id: {
                "one_way_turnover": _text(values[path_id]),
                "trade_count": trades[path_id],
            }
            for path_id in _PATH_IDS
        },
        "signed_deltas": {
            "pure_sizing_turnover_R_minus_P": _text(
                values[_RISK_SIZING_ID] - values[_PARENT_ID]
            ),
            "subfive_partial_cash_turnover_C_minus_R": _text(
                values[_PARTIAL_CASH_ID] - values[_RISK_SIZING_ID]
            ),
            "state_carry_turnover_A_minus_C": _text(
                values[_ACTUAL_ID] - values[_PARTIAL_CASH_ID]
            ),
            "total_turnover_A_minus_P": _text(
                values[_ACTUAL_ID] - values[_PARENT_ID]
            ),
            "pure_sizing_trade_count_R_minus_P": (
                trades[_RISK_SIZING_ID] - trades[_PARENT_ID]
            ),
            "subfive_partial_cash_trade_count_C_minus_R": (
                trades[_PARTIAL_CASH_ID] - trades[_RISK_SIZING_ID]
            ),
            "state_carry_trade_count_A_minus_C": (
                trades[_ACTUAL_ID] - trades[_PARTIAL_CASH_ID]
            ),
            "total_trade_count_A_minus_P": trades[_ACTUAL_ID] - trades[_PARENT_ID],
        },
    }


def _diagnostic_classification(
    attribution: Mapping[str, object],
) -> dict[str, object]:
    moderate = next(
        item
        for item in attribution["cost_results"]
        if item["cost_id"] == "moderate_friction"
    )
    oos = _window_by_id(moderate["windows"], "oos")
    metrics = oos["path_metrics"]
    effects = oos["return_effects"]
    parent = _base._decimal(metrics[_PARENT_ID]["total_return"])
    risk_sizing = _base._decimal(metrics[_RISK_SIZING_ID]["total_return"])
    partial_cash = _base._decimal(metrics[_PARTIAL_CASH_ID]["total_return"])
    actual = _base._decimal(metrics[_ACTUAL_ID]["total_return"])
    net_harm = parent - actual
    signed = {
        "pure_sizing": _base._decimal(
            effects["pure_sizing_effect_R_minus_P"]
        ),
        "subfive_partial_cash": _base._decimal(
            effects["subfive_partial_cash_effect_C_minus_R"]
        ),
        "state_carry": _base._decimal(
            effects["state_carry_effect_A_minus_C"]
        ),
    }
    harm = {name: max(_ZERO, -value) for name, value in signed.items()}
    shares = {
        name: None if net_harm == _ZERO else value / net_harm
        for name, value in harm.items()
    }
    if net_harm < _MATERIAL_HARM:
        classification = "no_material_harm"
        primary = None
    else:
        largest_value = max(harm.values())
        largest = [
            name
            for name, value in harm.items()
            if abs(value - largest_value) <= _TOLERANCE
        ]
        if len(largest) != 1 or largest_value < _PRIMARY_SHARE * net_harm:
            classification = "mixed_harm"
            primary = None
        else:
            primary = largest[0]
            labels = {
                "pure_sizing": "pure_sizing_primary",
                "subfive_partial_cash": "subfive_partial_cash_primary",
                "state_carry": "state_carry_primary",
            }
            classification = labels[primary]
    return {
        "classification": classification,
        "primary_driver": primary,
        "creates_route": False,
        "candidate_created": False,
        "moderate_full_oos": {
            "parent_return": _text(parent),
            "risk_sizing_parent_state_return": _text(risk_sizing),
            "partial_cash_parent_state_return": _text(partial_cash),
            "actual_return": _text(actual),
            "net_harm_P_minus_A": _text(net_harm),
            "signed_effects": {name: _text(value) for name, value in signed.items()},
            "positive_harm_components": {
                name: _text(value) for name, value in harm.items()
            },
            "component_shares_of_net_harm": {
                name: None if value is None else _text(value)
                for name, value in shares.items()
            },
        },
        "material_harm_threshold": _text(_MATERIAL_HARM),
        "primary_share_threshold": _text(_PRIMARY_SHARE),
        "tie_tolerance": _text(_TOLERANCE),
    }


def _signal_ledger_summary(
    ledger: Sequence[Mapping[str, object]],
    config: _base.NexusTradeMonthlyIndependentReplicationConfig,
) -> dict[str, object]:
    oos = [item for item in ledger if item.get("in_oos") is True]
    sizing = [
        item for item in oos if item.get("pure_sizing_source_target_changed") is True
    ]
    partial = [
        item for item in oos if item.get("partial_cash_source_target_changed") is True
    ]
    invalid_partial = [
        item
        for item in partial
        if int(item.get("eligible_count", -1)) not in {1, 2, 3, 4}
    ]
    if invalid_partial:
        raise ValidationError(
            "partial-cash diagnostic changed outside one-to-four eligibility."
        )
    return {
        "total_signal_count": len(ledger),
        "oos_signal_count": len(oos),
        "oos_pure_sizing_change_signal_count": len(sizing),
        "oos_subfive_partial_cash_change_signal_count": len(partial),
        "partial_cash_changes_only_for_one_to_four_eligible": True,
        "oos_signal_dates": _date_summary(
            [date.fromisoformat(str(item["signal_date"])) for item in oos]
        ),
        "oos_start": config.oos_start.isoformat(),
        "oos_end": config.oos_end.isoformat(),
    }


def _artifact_manifest(
    config: NexusTradeRiskBalancedAttributionConfig,
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
        config.v567_protocol_path,
        config.v567_engine_path,
        config.v567_preregistration_path,
        config.v567_result_path,
        config.v567_summary_path,
        config.v567_manifest_path,
    )
    return {
        "record_type": "nexustrade_risk_balanced_attribution_manifest",
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
        result.get("diagnostic_classification"),
        "diagnostic classification",
    )
    moderate = _mapping(
        diagnostic.get("moderate_full_oos"),
        "moderate full OOS",
    )
    attribution = _mapping(result.get("attribution"), "attribution")
    moderate_cost = next(
        _mapping(item, "cost result")
        for item in attribution["cost_results"]
        if item["cost_id"] == "moderate_friction"
    )
    oos = _window_by_id(moderate_cost["windows"], "oos")
    effects = _mapping(oos.get("return_effects"), "OOS return effects")
    sessions = _mapping(oos.get("session_attribution"), "OOS sessions")
    ledger = _mapping(
        result.get("parent_state_signal_ledger_summary"),
        "signal ledger summary",
    )

    def count(name: str) -> object:
        return _mapping(sessions.get(name), name).get("count")

    return "\n".join(
        (
            "# V5.68 NexusTrade-Inspired Risk-Balanced Attribution",
            "",
            f"- Classification: `{diagnostic.get('classification')}`.",
            f"- Primary driver: `{diagnostic.get('primary_driver')}`.",
            f"- Moderate full-OOS return P/R/C/A: "
            f"`{moderate.get('parent_return')}`/"
            f"`{moderate.get('risk_sizing_parent_state_return')}`/"
            f"`{moderate.get('partial_cash_parent_state_return')}`/"
            f"`{moderate.get('actual_return')}`.",
            f"- Effects R-P/C-R/A-C/total A-P: "
            f"`{effects.get('pure_sizing_effect_R_minus_P')}`/"
            f"`{effects.get('subfive_partial_cash_effect_C_minus_R')}`/"
            f"`{effects.get('state_carry_effect_A_minus_C')}`/"
            f"`{effects.get('total_effect_A_minus_P')}`.",
            f"- OOS target divergences R-P/C-R/A-C: "
            f"`{count('pure_sizing_target_divergence_R_vs_P')}`/"
            f"`{count('subfive_partial_cash_target_divergence_C_vs_R')}`/"
            f"`{count('state_carry_target_divergence_A_vs_C')}`.",
            f"- OOS parent-state signals: `{ledger.get('oos_signal_count')}`; "
            f"pure-sizing changes "
            f"`{ledger.get('oos_pure_sizing_change_signal_count')}`; "
            f"sub-five partial-cash changes "
            f"`{ledger.get('oos_subfive_partial_cash_change_signal_count')}`.",
            "- Return and constituent reconciliation: `passed`.",
            "- Candidate created: `false`.",
            "- Route created: `false`.",
            "- Parameter search: `false`.",
            "- Network, broker, paper mutation, and live activity: `false`.",
            "",
        )
    )


def _validate_dependencies(
    config: NexusTradeRiskBalancedAttributionConfig,
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
        "v567_protocol_sha256": (
            config.v567_protocol_path,
            config.expected_v567_protocol_sha256,
        ),
        "v567_engine_sha256": (
            config.v567_engine_path,
            config.expected_v567_engine_sha256,
        ),
        "v567_preregistration_sha256": (
            config.v567_preregistration_path,
            config.expected_v567_preregistration_sha256,
        ),
        "v567_result_sha256": (
            config.v567_result_path,
            config.expected_v567_result_sha256,
        ),
        "v567_summary_sha256": (
            config.v567_summary_path,
            config.expected_v567_summary_sha256,
        ),
        "v567_manifest_sha256": (
            config.v567_manifest_path,
            config.expected_v567_manifest_sha256,
        ),
    }
    hashes = {}
    for name, (path, expected) in specs.items():
        actual = _sha256(path)
        if actual != expected:
            raise ValidationError(f"{name} does not match preregistration.")
        hashes[name] = actual
    return hashes


def _safety_payload() -> dict[str, object]:
    return {
        "offline_only": True,
        "network_access_performed": False,
        "credential_access_performed": False,
        "nexustrade_access_performed": False,
        "nexustrade_mutation_performed": False,
        "broker_access_performed": False,
        "paper_mutation_performed": False,
        "live_activity_performed": False,
        "third_sleeve_added": False,
        "candidate_created": False,
        "route_created": False,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "unchanged_v557_caps": {
            "entry_order_notional_usd": "25",
            "aggregate_marked_spy_entry_exposure_usd": "60",
            "broker_orders_per_secure_cycle": 1,
            "sleeve_intents_per_utc_day": 2,
        },
    }


def _date_summary(values: Sequence[date]) -> dict[str, object]:
    ordered = sorted(set(values))
    return {
        "count": len(ordered),
        "first_date": None if not ordered else ordered[0].isoformat(),
        "last_date": None if not ordered else ordered[-1].isoformat(),
        "dates": [item.isoformat() for item in ordered],
    }


def _effect_label(value: Decimal) -> str:
    if value > _TOLERANCE:
        return "benefit"
    if value < -_TOLERANCE:
        return "harm"
    return "neutral"


def _require_tolerance(value: Decimal, field_name: str) -> None:
    if abs(value) > _TOLERANCE:
        raise ValidationError(f"{field_name} exceeds preregistered tolerance.")


def _window_by_id(
    values: object,
    window_id: str,
) -> Mapping[str, object]:
    if not isinstance(values, list):
        raise ValidationError("window records must be a list.")
    for item in values:
        mapped = _mapping(item, "window record")
        if mapped.get("window_id") == window_id:
            return mapped
    raise ValidationError(f"window record is missing: {window_id}")


def _records_by_id(
    value: object,
    field_name: str,
) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} records must be a list.")
    records = {}
    for item in value:
        mapped = _mapping(item, f"{field_name} record")
        record_id = mapped.get(field_name)
        if not isinstance(record_id, str) or not record_id:
            raise ValidationError(f"{field_name} record ID is invalid.")
        if record_id in records:
            raise ValidationError(f"duplicate {field_name}: {record_id}")
        records[record_id] = mapped
    return records


def _artifact_record(path: Path) -> dict[str, object]:
    return {"path": str(path), "sha256": _sha256(path), "byte_count": path.stat().st_size}


def _load_json(path: Path, field_name: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{field_name} must be readable JSON.") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must contain a JSON object.")
    return value


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file does not exist: {path}")
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


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _text(value: Decimal) -> str:
    return _base._decimal_text(value)


def _config(
    value: NexusTradeRiskBalancedAttributionConfig,
) -> NexusTradeRiskBalancedAttributionConfig:
    if not isinstance(value, NexusTradeRiskBalancedAttributionConfig):
        raise ValidationError(
            "config must be NexusTradeRiskBalancedAttributionConfig."
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
    result = run_nexustrade_risk_balanced_attribution(
        NexusTradeRiskBalancedAttributionConfig(
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
            result["diagnostic_classification"],
            "diagnostic classification",
        )
        print(f"classification={diagnostic['classification']}")
        print(f"primary_driver={diagnostic['primary_driver']}")
        print("candidate_created=false")
        print("route_created=false")
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
        print("paper_promotion_allowed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
