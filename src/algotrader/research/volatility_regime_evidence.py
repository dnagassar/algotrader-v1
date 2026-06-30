"""Deterministic offline volatility-regime evidence packet."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import LocalDailyBar, load_local_daily_bars_csv
from algotrader.research.multi_etf_adjusted_data_manifest import (
    APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS,
)

__all__ = [
    "VOLATILITY_REGIME_EVIDENCE_CLASSIFICATIONS",
    "VOLATILITY_REGIME_EVIDENCE_LABELS",
    "VolatilityRegimeClassification",
    "VolatilityRegimeEvidenceConfig",
    "VolatilityRegimeObservation",
    "build_volatility_regime_observations",
    "build_volatility_regime_evidence_payload",
    "classify_realized_volatility_series",
    "compute_realized_volatility_series",
    "load_volatility_regime_evidence_inputs",
    "main",
    "render_volatility_regime_evidence_markdown",
    "run_volatility_regime_evidence",
    "write_volatility_regime_evidence_artifacts",
]


VOLATILITY_REGIME_EVIDENCE_LABELS = (
    "research_only",
    "offline_only",
    "not_live_authorized",
    "paper_submit_authorized=false",
    "profit_claim=none",
    "broker_state_not_required",
    "no_strategy_promoted",
    "no_broker_access",
    "no_market_data_fetch",
)
VOLATILITY_REGIME_EVIDENCE_CLASSIFICATIONS = (
    "volatility_regime_candidate_worth_offline_backtest",
    "volatility_regime_needs_more_evidence",
    "volatility_regime_rejected_for_next_step",
    "volatility_regime_blocked_missing_artifacts",
    "volatility_regime_blocked_safety_invariant",
)

_RECORD_TYPE = "volatility_regime_evidence"
_SCHEMA_VERSION = "1"
_PHASE = "v2.18_deterministic_volatility_regime_offline_evidence_packet"
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/strategy_challengers/volatility_regime_evidence_latest"
)
_DEFAULT_DATA_MANIFEST = Path("runs/operator_input/multi_etf_adjusted_data_manifest.json")
_DEFAULT_CHALLENGER_RESULTS = Path(
    "runs/strategy_challengers/latest/challenger_results.json"
)
_DEFAULT_PREVIEW_REVIEW = Path(
    "runs/strategy_challengers/preview_review_latest/preview_candidate_review.json"
)
_DEFAULT_TRIAGE = Path(
    "runs/strategy_challengers/research_hypothesis_triage_latest/"
    "research_hypothesis_triage.json"
)
_REGIMES = ("low_vol", "normal_vol", "high_vol", "insufficient_history")
_HASH_CHUNK_SIZE = 1024 * 1024
_TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True, slots=True)
class VolatilityRegimeClassification:
    """One no-lookahead regime classification for a realized-vol observation."""

    realized_volatility: float | None
    low_vol_threshold: float | None
    high_vol_threshold: float | None
    regime: str

    def __post_init__(self) -> None:
        if self.realized_volatility is not None:
            object.__setattr__(
                self,
                "realized_volatility",
                _finite_float(self.realized_volatility, "realized_volatility"),
            )
        if self.low_vol_threshold is not None:
            object.__setattr__(
                self,
                "low_vol_threshold",
                _finite_float(self.low_vol_threshold, "low_vol_threshold"),
            )
        if self.high_vol_threshold is not None:
            object.__setattr__(
                self,
                "high_vol_threshold",
                _finite_float(self.high_vol_threshold, "high_vol_threshold"),
            )
        if self.regime not in _REGIMES:
            raise ValidationError("regime is not supported.")


@dataclass(frozen=True, slots=True)
class VolatilityRegimeObservation:
    """One daily adjusted-close return, realized volatility, and regime."""

    symbol: str
    date: date
    adjusted_close: float
    daily_return: float | None
    realized_volatility: float | None
    low_vol_threshold: float | None
    high_vol_threshold: float | None
    regime: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _approved_symbol(self.symbol))
        object.__setattr__(self, "date", _plain_date(self.date, "date"))
        object.__setattr__(
            self,
            "adjusted_close",
            _positive_float(self.adjusted_close, "adjusted_close"),
        )
        if self.daily_return is not None:
            object.__setattr__(
                self,
                "daily_return",
                _finite_float(self.daily_return, "daily_return"),
            )
        if self.realized_volatility is not None:
            object.__setattr__(
                self,
                "realized_volatility",
                _finite_float(self.realized_volatility, "realized_volatility"),
            )
        if self.low_vol_threshold is not None:
            object.__setattr__(
                self,
                "low_vol_threshold",
                _finite_float(self.low_vol_threshold, "low_vol_threshold"),
            )
        if self.high_vol_threshold is not None:
            object.__setattr__(
                self,
                "high_vol_threshold",
                _finite_float(self.high_vol_threshold, "high_vol_threshold"),
            )
        if self.regime not in _REGIMES:
            raise ValidationError("regime is not supported.")


@dataclass(frozen=True, slots=True)
class VolatilityRegimeEvidenceConfig:
    """Inputs for one offline volatility-regime evidence packet."""

    output_root: Path | str = _DEFAULT_OUTPUT_ROOT
    data_manifest: Path | str = _DEFAULT_DATA_MANIFEST
    challenger_results_path: Path | str = _DEFAULT_CHALLENGER_RESULTS
    preview_review_path: Path | str = _DEFAULT_PREVIEW_REVIEW
    triage_path: Path | str = _DEFAULT_TRIAGE
    symbols: Iterable[str] | str = APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS
    canonical_paths: Mapping[str, Path | str] | None = None
    rolling_lookback: int = 20
    quantile_min_history: int = 252
    low_quantile: float = 0.33
    high_quantile: float = 0.67

    def __post_init__(self) -> None:
        symbols = _symbol_tuple(self.symbols)
        object.__setattr__(self, "output_root", _path(self.output_root, "output_root"))
        object.__setattr__(
            self,
            "data_manifest",
            _json_path(self.data_manifest, "data_manifest"),
        )
        object.__setattr__(
            self,
            "challenger_results_path",
            _json_path(self.challenger_results_path, "challenger_results_path"),
        )
        object.__setattr__(
            self,
            "preview_review_path",
            _json_path(self.preview_review_path, "preview_review_path"),
        )
        object.__setattr__(self, "triage_path", _json_path(self.triage_path, "triage_path"))
        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(
            self,
            "canonical_paths",
            _canonical_paths(self.canonical_paths),
        )
        object.__setattr__(
            self,
            "rolling_lookback",
            _positive_int(self.rolling_lookback, "rolling_lookback"),
        )
        object.__setattr__(
            self,
            "quantile_min_history",
            _positive_int(self.quantile_min_history, "quantile_min_history"),
        )
        low_quantile = _quantile(self.low_quantile, "low_quantile")
        high_quantile = _quantile(self.high_quantile, "high_quantile")
        if low_quantile >= high_quantile:
            raise ValidationError("low_quantile must be less than high_quantile.")
        object.__setattr__(self, "low_quantile", low_quantile)
        object.__setattr__(self, "high_quantile", high_quantile)


def run_volatility_regime_evidence(
    config: VolatilityRegimeEvidenceConfig,
) -> dict[str, object]:
    """Load local evidence, build the packet, and write artifacts."""

    checked_config = _config(config)
    inputs = load_volatility_regime_evidence_inputs(checked_config)
    payload = build_volatility_regime_evidence_payload(inputs)
    manifest = write_volatility_regime_evidence_artifacts(
        payload,
        checked_config.output_root,
    )
    result = dict(payload)
    result["manifest"] = manifest
    return result


def load_volatility_regime_evidence_inputs(
    config: VolatilityRegimeEvidenceConfig,
) -> dict[str, object]:
    """Load existing local ETF data and v2.16/v2.17 artifacts only."""

    checked_config = _config(config)
    data_manifest_record, data_manifest = _read_json_artifact(
        name="multi_etf_adjusted_data_manifest",
        path=checked_config.data_manifest,
        required=True,
        required_fields=("symbol_data", "valid_symbols"),
    )
    manifest_paths = _paths_from_data_manifest(data_manifest)
    canonical_paths = dict(manifest_paths)
    canonical_paths.update(checked_config.canonical_paths)

    symbol_records: list[dict[str, object]] = []
    symbol_bars: dict[str, tuple[LocalDailyBar, ...]] = {}
    for symbol in checked_config.symbols:
        record, bars = _load_symbol_data(symbol, canonical_paths.get(symbol))
        symbol_records.append(record)
        if bars:
            symbol_bars[symbol] = bars

    artifact_specs = (
        (
            "challenger_results",
            checked_config.challenger_results_path,
            True,
            ("results", "promotion_recommendations"),
        ),
        (
            "preview_candidate_review",
            checked_config.preview_review_path,
            True,
            ("candidate_reviews", "overall_recommendation"),
        ),
        (
            "research_hypothesis_triage",
            checked_config.triage_path,
            True,
            ("failure_taxonomy", "selected_next_family", "v2_18_next_action"),
        ),
    )
    artifacts: dict[str, object] = {"multi_etf_adjusted_data_manifest": data_manifest}
    source_artifacts: list[dict[str, object]] = []
    for name, path, required, required_fields in artifact_specs:
        record, data = _read_json_artifact(
            name=name,
            path=path,
            required=required,
            required_fields=required_fields,
        )
        source_artifacts.append(record)
        artifacts[name] = data

    rule = {
        "return_input": "daily adjusted close simple returns",
        "realized_volatility": (
            f"{checked_config.rolling_lookback}-trading-day sample standard deviation "
            f"of daily adjusted-close returns, annualized by sqrt({_TRADING_DAYS_PER_YEAR})"
        ),
        "rolling_lookback": checked_config.rolling_lookback,
        "threshold_method": (
            "expanding historical nearest-rank quantiles computed from prior "
            "realized-volatility observations only"
        ),
        "low_quantile": checked_config.low_quantile,
        "high_quantile": checked_config.high_quantile,
        "quantile_min_history": checked_config.quantile_min_history,
        "lookahead_policy": (
            "thresholds for each date exclude that date's realized volatility and all "
            "future observations"
        ),
        "regimes": list(_REGIMES),
        "insufficient_history_rule": (
            "insufficient_history when the rolling volatility window is unavailable "
            "or fewer than quantile_min_history prior realized-volatility observations exist"
        ),
    }

    return {
        "config": {
            "symbols": list(checked_config.symbols),
            "output_root": str(checked_config.output_root),
        },
        "rule": rule,
        "data_manifest_record": data_manifest_record,
        "source_data": symbol_records,
        "source_artifacts": source_artifacts,
        "artifacts": artifacts,
        "symbol_bars": symbol_bars,
    }


def build_volatility_regime_evidence_payload(
    inputs: Mapping[str, object],
) -> dict[str, object]:
    """Build the deterministic v2.18 volatility-regime evidence payload."""

    input_items = dict(inputs)
    rule = _mapping(input_items.get("rule"), "rule")
    source_data = _records(input_items.get("source_data", []))
    source_artifacts = _records(input_items.get("source_artifacts", []))
    data_manifest_record = _mapping_or_empty(input_items.get("data_manifest_record"))
    artifacts = _mapping_or_empty(input_items.get("artifacts"))
    symbol_bars = _symbol_bars(input_items.get("symbol_bars", {}))
    symbols = _symbols_from_config(input_items)

    observations_by_symbol: dict[str, tuple[VolatilityRegimeObservation, ...]] = {}
    for symbol, bars in symbol_bars.items():
        observations_by_symbol[symbol] = build_volatility_regime_observations(
            bars,
            rolling_lookback=int(rule["rolling_lookback"]),
            quantile_min_history=int(rule["quantile_min_history"]),
            low_quantile=float(rule["low_quantile"]),
            high_quantile=float(rule["high_quantile"]),
        )

    required_artifact_blockers = [
        record
        for record in (data_manifest_record, *source_artifacts)
        if record.get("required") is True and record.get("status") != "available"
    ]
    missing_spy_data = not observations_by_symbol.get("SPY")
    data_blockers = [
        record
        for record in source_data
        if record.get("symbol") == "SPY" and record.get("status") != "available"
    ]
    safety_violations = _source_safety_violations(artifacts)

    data_inventory = _data_inventory(
        symbols=symbols,
        source_data=source_data,
        observations_by_symbol=observations_by_symbol,
    )
    regime_summary = _regime_summary(observations_by_symbol)
    latest_regimes = _latest_regimes(observations_by_symbol)
    failure_context_bridge = _failure_context_bridge(artifacts, source_artifacts)
    diagnostics = _regime_conditioned_diagnostics(
        observations_by_symbol=observations_by_symbol,
        symbol_bars=symbol_bars,
        artifacts=artifacts,
    )

    if safety_violations:
        classification = "volatility_regime_blocked_safety_invariant"
        decision_evidence = list(safety_violations)
        decision_inference = [
            "The packet cannot classify a next research action when source artifacts report broker, credential, network, paper-submit, or live-mutation activity."
        ]
    elif required_artifact_blockers or missing_spy_data or data_blockers:
        classification = "volatility_regime_blocked_missing_artifacts"
        decision_evidence = [
            f"{record.get('name', record.get('symbol'))}: {record.get('status')}"
            for record in (*required_artifact_blockers, *data_blockers)
        ]
        if missing_spy_data and not data_blockers:
            decision_evidence.append("SPY: unavailable")
        decision_inference = [
            "Required local ETF data or prior evidence artifacts are unavailable, malformed, or incomplete."
        ]
    else:
        assessment = _mapping(
            diagnostics.get("high_volatility_fragility_assessment"),
            "high_volatility_fragility_assessment",
        )
        if assessment.get("assessment") == "supported":
            classification = "volatility_regime_candidate_worth_offline_backtest"
        elif assessment.get("assessment") == "rejected":
            classification = "volatility_regime_rejected_for_next_step"
        else:
            classification = "volatility_regime_needs_more_evidence"
        decision_evidence = list(assessment.get("evidence", []))
        decision_inference = list(assessment.get("inference", []))

    selected_next_action = _selected_v2_19_next_action(classification)
    generated_at = _deterministic_generated_at(data_inventory, artifacts)
    payload = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "phase": _PHASE,
        "classification": classification,
        "generated_at": generated_at,
        "source_data": {
            "data_manifest": data_manifest_record,
            "symbol_data": source_data,
            "approved_symbols": list(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS),
        },
        "source_artifacts": source_artifacts,
        "regime_rule": rule,
        "data_inventory": data_inventory,
        "regime_summary": regime_summary,
        "latest_regimes": latest_regimes,
        "failure_context_bridge": failure_context_bridge,
        "regime_conditioned_diagnostics": diagnostics,
        "evidence": decision_evidence,
        "inference": decision_inference,
        "selected_v2_19_next_action": selected_next_action,
        "paper_candidate_count": 0,
        "offline_shadow_candidate_count": 0,
        "safety_labels": list(VOLATILITY_REGIME_EVIDENCE_LABELS),
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "market_data_fetch_performed": False,
        "normal_pytest_offline_credential_free": True,
        "safety": _safety_payload(),
        "limitations": [
            "offline deterministic research diagnostic only",
            "reads existing local adjusted daily ETF data and local prior evidence artifacts only",
            "does not fetch market data",
            "does not read or mutate broker state",
            "does not submit paper or live orders",
            "does not promote any strategy to paper",
            "does not make a profitability claim",
        ],
    }
    _validate_classification(str(payload["classification"]))
    return payload


def compute_realized_volatility_series(
    returns: Sequence[float],
    *,
    lookback: int,
) -> tuple[float | None, ...]:
    """Compute annualized rolling realized volatility for daily returns."""

    window = _positive_int(lookback, "lookback")
    values = tuple(_finite_float(value, "return") for value in returns)
    realized: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            realized.append(None)
            continue
        sample = values[index + 1 - window : index + 1]
        mean = sum(sample) / window
        if window == 1:
            variance = 0.0
        else:
            variance = sum((value - mean) ** 2 for value in sample) / (window - 1)
        realized.append(math.sqrt(variance) * math.sqrt(_TRADING_DAYS_PER_YEAR))
    return tuple(realized)


def classify_realized_volatility_series(
    realized_volatility: Sequence[float | None],
    *,
    quantile_min_history: int,
    low_quantile: float,
    high_quantile: float,
) -> tuple[VolatilityRegimeClassification, ...]:
    """Classify realized volatility using prior expanding quantile thresholds."""

    min_history = _positive_int(quantile_min_history, "quantile_min_history")
    low_q = _quantile(low_quantile, "low_quantile")
    high_q = _quantile(high_quantile, "high_quantile")
    if low_q >= high_q:
        raise ValidationError("low_quantile must be less than high_quantile.")

    prior_values: list[float] = []
    classifications: list[VolatilityRegimeClassification] = []
    for raw_value in realized_volatility:
        value = None if raw_value is None else _finite_float(raw_value, "realized_volatility")
        if value is None or len(prior_values) < min_history:
            classifications.append(
                VolatilityRegimeClassification(
                    realized_volatility=value,
                    low_vol_threshold=None,
                    high_vol_threshold=None,
                    regime="insufficient_history",
                )
            )
            if value is not None:
                prior_values.append(value)
            continue

        low_threshold = _nearest_rank_quantile(prior_values, low_q)
        high_threshold = _nearest_rank_quantile(prior_values, high_q)
        if value <= low_threshold:
            regime = "low_vol"
        elif value >= high_threshold:
            regime = "high_vol"
        else:
            regime = "normal_vol"
        classifications.append(
            VolatilityRegimeClassification(
                realized_volatility=value,
                low_vol_threshold=low_threshold,
                high_vol_threshold=high_threshold,
                regime=regime,
            )
        )
        prior_values.append(value)
    return tuple(classifications)


def build_volatility_regime_observations(
    bars: Sequence[LocalDailyBar],
    *,
    rolling_lookback: int,
    quantile_min_history: int,
    low_quantile: float,
    high_quantile: float,
) -> tuple[VolatilityRegimeObservation, ...]:
    """Build daily no-lookahead volatility-regime observations from local bars."""

    bar_items = tuple(bars)
    for index, bar in enumerate(bar_items):
        if type(bar) is not LocalDailyBar:
            raise ValidationError(f"bars[{index}] must be a LocalDailyBar.")
    if not bar_items:
        return ()

    daily_returns: list[float | None] = [None]
    raw_returns: list[float] = []
    for previous, current in zip(bar_items, bar_items[1:]):
        prior_close = float(previous.adjusted_close)
        current_close = float(current.adjusted_close)
        daily_return = current_close / prior_close - 1.0
        raw_returns.append(daily_return)
        daily_returns.append(daily_return)

    realized_from_returns = compute_realized_volatility_series(
        raw_returns,
        lookback=rolling_lookback,
    )
    realized_for_bars: list[float | None] = [None] * len(bar_items)
    for offset, value in enumerate(realized_from_returns, start=1):
        realized_for_bars[offset] = value
    classifications = classify_realized_volatility_series(
        realized_for_bars,
        quantile_min_history=quantile_min_history,
        low_quantile=low_quantile,
        high_quantile=high_quantile,
    )

    observations: list[VolatilityRegimeObservation] = []
    for bar, daily_return, classification in zip(
        bar_items,
        daily_returns,
        classifications,
    ):
        observations.append(
            VolatilityRegimeObservation(
                symbol=bar.symbol,
                date=bar.date,
                adjusted_close=float(bar.adjusted_close),
                daily_return=daily_return,
                realized_volatility=classification.realized_volatility,
                low_vol_threshold=classification.low_vol_threshold,
                high_vol_threshold=classification.high_vol_threshold,
                regime=classification.regime,
            )
        )
    return tuple(observations)


def write_volatility_regime_evidence_artifacts(
    payload: Mapping[str, object],
    output_root: Path | str,
) -> dict[str, object]:
    """Write required JSON, markdown, and manifest artifacts."""

    root = _path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)
    payload_dict = dict(payload)
    artifact_paths = [
        root / "volatility_regime_evidence.json",
        root / "volatility_regime_evidence.md",
    ]
    _write_text(artifact_paths[0], _json_dumps(payload_dict) + "\n")
    _write_text(artifact_paths[1], render_volatility_regime_evidence_markdown(payload_dict))
    manifest = _manifest_payload(payload_dict, root, artifact_paths)
    _write_text(root / "manifest.json", _json_dumps(manifest) + "\n")
    return manifest


def render_volatility_regime_evidence_markdown(payload: Mapping[str, object]) -> str:
    """Render a compact operator-readable volatility-regime packet."""

    payload_dict = dict(payload)
    inventory = _mapping_or_empty(payload_dict.get("data_inventory"))
    regime_summary = _mapping_or_empty(payload_dict.get("regime_summary"))
    latest_regimes = _mapping_or_empty(payload_dict.get("latest_regimes"))
    bridge = _mapping_or_empty(payload_dict.get("failure_context_bridge"))
    diagnostics = _mapping_or_empty(payload_dict.get("regime_conditioned_diagnostics"))
    action = _mapping_or_empty(payload_dict.get("selected_v2_19_next_action"))
    lines = [
        "# Volatility-Regime Evidence",
        "",
        "Labels: " + ", ".join(str(item) for item in payload_dict.get("safety_labels", [])),
        "",
        "## Summary",
        f"- phase: {payload_dict.get('phase')}",
        f"- classification: {payload_dict.get('classification')}",
        f"- generated_at: {payload_dict.get('generated_at')}",
        f"- as_of_date: {regime_summary.get('as_of_date')}",
        f"- paper_candidate_count: {payload_dict.get('paper_candidate_count')}",
        f"- offline_shadow_candidate_count: {payload_dict.get('offline_shadow_candidate_count')}",
        "- paper_submit_authorized: false",
        "- profit_claim: none",
        "",
        "## Regime Rule",
        f"- return_input: {_mapping_or_empty(payload_dict.get('regime_rule')).get('return_input')}",
        f"- realized_volatility: {_mapping_or_empty(payload_dict.get('regime_rule')).get('realized_volatility')}",
        f"- threshold_method: {_mapping_or_empty(payload_dict.get('regime_rule')).get('threshold_method')}",
        f"- lookahead_policy: {_mapping_or_empty(payload_dict.get('regime_rule')).get('lookahead_policy')}",
        "",
        "## Data Inventory",
        f"- symbols_requested: {', '.join(str(item) for item in inventory.get('symbols_requested', []))}",
        f"- symbols_found: {', '.join(str(item) for item in inventory.get('symbols_found', [])) or 'none'}",
        f"- latest_date: {inventory.get('latest_date')}",
        f"- missing_data_handling: {inventory.get('missing_data_handling')}",
        "",
        "## Latest Regimes",
        "| symbol | regime | realized_volatility | low_threshold | high_threshold |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for symbol in sorted(latest_regimes):
        record = _mapping_or_empty(latest_regimes.get(symbol))
        lines.append(
            "| {symbol} | {regime} | {rv} | {low} | {high} |".format(
                symbol=symbol,
                regime=record.get("regime"),
                rv=_markdown_number(record.get("realized_volatility")),
                low=_markdown_number(record.get("low_vol_threshold")),
                high=_markdown_number(record.get("high_vol_threshold")),
            )
        )

    lines.extend(
        [
            "",
            "## Regime Counts",
            "| symbol | low_vol | normal_vol | high_vol | insufficient_history |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    counts_by_symbol = _mapping_or_empty(regime_summary.get("regime_counts_by_symbol"))
    for symbol in sorted(counts_by_symbol):
        counts = _mapping_or_empty(counts_by_symbol.get(symbol))
        lines.append(
            "| {symbol} | {low} | {normal} | {high} | {insufficient} |".format(
                symbol=symbol,
                low=counts.get("low_vol", 0),
                normal=counts.get("normal_vol", 0),
                high=counts.get("high_vol", 0),
                insufficient=counts.get("insufficient_history", 0),
            )
        )

    lines.extend(["", "## Failure-Context Bridge", "", "Evidence:"])
    for item in bridge.get("evidence", []):
        lines.append(f"- {item}")
    lines.extend(["", "Inference:"])
    for item in bridge.get("inference", []):
        lines.append(f"- {item}")

    assessment = _mapping_or_empty(diagnostics.get("high_volatility_fragility_assessment"))
    lines.extend(["", "## High-Volatility Fragility Assessment", "", "Evidence:"])
    for item in assessment.get("evidence", []):
        lines.append(f"- {item}")
    lines.extend(["", "Inference:"])
    for item in assessment.get("inference", []):
        lines.append(f"- {item}")

    basket = _mapping_or_empty(diagnostics.get("basket"))
    basket_distribution = _mapping_or_empty(basket.get("return_distribution_by_regime"))
    lines.extend(
        [
            "",
            "## Basket Return Diagnostics",
            "| regime | count | mean_daily_return | negative_day_rate | max_drawdown_proxy |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for regime in _REGIMES:
        item = _mapping_or_empty(basket_distribution.get(regime))
        lines.append(
            "| {regime} | {count} | {mean} | {negative_rate} | {drawdown} |".format(
                regime=regime,
                count=item.get("count", 0),
                mean=_markdown_number(item.get("mean_daily_return")),
                negative_rate=_markdown_number(item.get("negative_day_rate")),
                drawdown=_markdown_number(item.get("max_drawdown_proxy")),
            )
        )

    lines.extend(
        [
            "",
            "## v2.19 Next Action",
            f"- recommendation: {action.get('recommendation')}",
            f"- title: {action.get('title')}",
            f"- implementation_prompt: {action.get('implementation_prompt')}",
            "",
        ]
    )
    return "\n".join(lines)


def _load_symbol_data(
    symbol: str,
    path: Path | None,
) -> tuple[dict[str, object], tuple[LocalDailyBar, ...]]:
    checked_symbol = _approved_symbol(symbol)
    base = {"symbol": checked_symbol, "path": "" if path is None else str(path)}
    if path is None:
        return (
            {
                **base,
                "status": "missing_data",
                "sha256": "",
                "row_count": 0,
                "earliest_date": "",
                "latest_date": "",
                "validation_error": "canonical_path_missing",
            },
            (),
        )
    if not path.is_file():
        return (
            {
                **base,
                "status": "missing_data",
                "sha256": "",
                "row_count": 0,
                "earliest_date": "",
                "latest_date": "",
                "validation_error": "canonical_csv_missing",
            },
            (),
        )
    try:
        result = load_local_daily_bars_csv(path, symbol=checked_symbol)
    except ValidationError as exc:
        return (
            {
                **base,
                "status": "invalid_data",
                "sha256": _sha256_file(path),
                "row_count": 0,
                "earliest_date": "",
                "latest_date": "",
                "validation_error": str(exc),
            },
            (),
        )
    bars = result.usable_bars
    if not bars:
        return (
            {
                **base,
                "status": "missing_data",
                "sha256": _sha256_file(path),
                "row_count": 0,
                "earliest_date": "",
                "latest_date": "",
                "source_total_row_count": result.total_row_count,
                "validation_error": "no_usable_symbol_rows",
            },
            (),
        )
    return (
        {
            **base,
            "status": "available",
            "sha256": _sha256_file(path),
            "row_count": len(bars),
            "source_total_row_count": result.total_row_count,
            "earliest_date": bars[0].date.isoformat(),
            "latest_date": bars[-1].date.isoformat(),
            "ignored_wrong_symbol_row_count": result.ignored_wrong_symbol_row_count,
            "ignored_future_bar_count": result.ignored_future_bar_count,
            "validation_error": "",
        },
        bars,
    )


def _read_json_artifact(
    *,
    name: str,
    path: Path,
    required: bool,
    required_fields: Sequence[str],
) -> tuple[dict[str, object], object]:
    base = {
        "name": name,
        "path": str(path),
        "required": required,
        "sha256": "",
        "required_fields": list(required_fields),
        "missing_required_fields": [],
    }
    if not path.is_file():
        return ({**base, "status": "missing", "error": "file_missing"}, {})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            {
                **base,
                "status": "malformed",
                "sha256": _sha256_file_if_available(path),
                "error": str(exc),
            },
            {},
        )
    missing_fields = [
        field for field in required_fields if not isinstance(data, Mapping) or field not in data
    ]
    status = "incomplete" if missing_fields else "available"
    return (
        {
            **base,
            "status": status,
            "sha256": _sha256_file(path),
            "missing_required_fields": missing_fields,
            "record_type": data.get("record_type", "") if isinstance(data, Mapping) else "",
            "schema_version": data.get("schema_version", "") if isinstance(data, Mapping) else "",
            "error": "",
        },
        data,
    )


def _paths_from_data_manifest(data: object) -> dict[str, Path]:
    if not isinstance(data, Mapping):
        return {}
    paths: dict[str, Path] = {}
    raw_records = data.get("symbol_data", [])
    if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
        return paths
    for item in raw_records:
        if not isinstance(item, Mapping):
            continue
        raw_symbol = item.get("symbol")
        raw_path = item.get("data_path")
        if not isinstance(raw_symbol, str) or not isinstance(raw_path, str):
            continue
        try:
            paths[_approved_symbol(raw_symbol)] = _path(raw_path, "data_path")
        except ValidationError:
            continue
    return paths


def _data_inventory(
    *,
    symbols: Sequence[str],
    source_data: Sequence[Mapping[str, object]],
    observations_by_symbol: Mapping[str, Sequence[VolatilityRegimeObservation]],
) -> dict[str, object]:
    rows_per_symbol = {
        str(record.get("symbol")): int(record.get("row_count", 0))
        for record in source_data
    }
    date_ranges = {
        str(record.get("symbol")): {
            "earliest_date": str(record.get("earliest_date", "")),
            "latest_date": str(record.get("latest_date", "")),
        }
        for record in source_data
    }
    latest_dates = [
        str(record.get("latest_date"))
        for record in source_data
        if str(record.get("latest_date", ""))
    ]
    return {
        "symbols_requested": list(symbols),
        "symbols_found": [
            str(record.get("symbol"))
            for record in source_data
            if record.get("status") == "available"
        ],
        "symbols_missing_or_invalid": [
            str(record.get("symbol"))
            for record in source_data
            if record.get("status") != "available"
        ],
        "rows_per_symbol": rows_per_symbol,
        "date_ranges": date_ranges,
        "latest_date": max(latest_dates) if latest_dates else "",
        "missing_data_handling": (
            "Missing or invalid symbols are recorded explicitly; SPY is required for "
            "classification and no market-data fetch is attempted."
        ),
        "insufficient_history_counts": {
            symbol: _count_regimes(observations).get("insufficient_history", 0)
            for symbol, observations in observations_by_symbol.items()
        },
    }


def _regime_summary(
    observations_by_symbol: Mapping[str, Sequence[VolatilityRegimeObservation]],
) -> dict[str, object]:
    latest = _latest_regimes(observations_by_symbol)
    return {
        "as_of_date": _latest_as_of_date(observations_by_symbol),
        "regime_counts_by_symbol": {
            symbol: _count_regimes(observations)
            for symbol, observations in observations_by_symbol.items()
        },
        "latest_regime_by_symbol": {
            symbol: _mapping_or_empty(record).get("regime")
            for symbol, record in latest.items()
        },
        "latest_realized_volatility_by_symbol": {
            symbol: _mapping_or_empty(record).get("realized_volatility")
            for symbol, record in latest.items()
        },
        "latest_threshold_values_by_symbol": {
            symbol: {
                "low_vol_threshold": _mapping_or_empty(record).get("low_vol_threshold"),
                "high_vol_threshold": _mapping_or_empty(record).get("high_vol_threshold"),
                "thresholds_as_of": _mapping_or_empty(record).get("date"),
            }
            for symbol, record in latest.items()
        },
    }


def _latest_regimes(
    observations_by_symbol: Mapping[str, Sequence[VolatilityRegimeObservation]],
) -> dict[str, dict[str, object]]:
    latest: dict[str, dict[str, object]] = {}
    for symbol, observations in observations_by_symbol.items():
        if not observations:
            continue
        item = observations[-1]
        latest[symbol] = {
            "date": item.date.isoformat(),
            "regime": item.regime,
            "realized_volatility": _round_or_none(item.realized_volatility),
            "low_vol_threshold": _round_or_none(item.low_vol_threshold),
            "high_vol_threshold": _round_or_none(item.high_vol_threshold),
        }
    return latest


def _failure_context_bridge(
    artifacts: Mapping[str, object],
    source_artifacts: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    challenger = _mapping_or_empty(artifacts.get("challenger_results"))
    preview = _mapping_or_empty(artifacts.get("preview_candidate_review"))
    triage = _mapping_or_empty(artifacts.get("research_hypothesis_triage"))
    taxonomy = _mapping_or_empty(triage.get("failure_taxonomy"))
    taxonomy_counts = {
        key: _mapping_or_empty(value).get("count", 0) for key, value in taxonomy.items()
    }
    challenger_results = _list_of_mappings(challenger.get("results", []))
    strategy_families = Counter(
        str(result.get("strategy_family", "unknown")) for result in challenger_results
    )
    spy_relevance = _existing_spy_exposure_relevance(challenger_results)
    evidence = [
        f"source_artifact_statuses={_artifact_status_summary(source_artifacts)}",
        f"challenger_result_count={len(challenger_results)}",
        f"preview_candidate_review_count={len(_list_of_mappings(preview.get('candidate_reviews', [])))}",
        f"preview_overall_recommendation={preview.get('overall_recommendation', '')}",
        f"v2_17_classification={triage.get('classification', '')}",
        f"v2_17_selected_next_family={triage.get('selected_next_family', '')}",
        f"prior_failure_taxonomy_counts={taxonomy_counts}",
        f"strategy_family_counts={dict(sorted(strategy_families.items()))}",
        f"spy_trend_momentum_existing_exposure={spy_relevance}",
    ]
    inference = [
        "Prior artifacts show SMA/trend and relative/dual momentum failures across OOS, cost-sensitivity, anti-overfit, and paper-promotion gates.",
        "A volatility-regime diagnostic is evidence-only here: it tests whether risk-state conditioning explains fragility without adding new SMA windows, relative-momentum variants, broker access, or paper promotion.",
    ]
    return {
        "evidence": evidence,
        "inference": inference,
        "prior_failure_taxonomy_counts": taxonomy_counts,
        "trend_momentum_exposure_relevance_from_existing_artifacts": spy_relevance,
    }


def _regime_conditioned_diagnostics(
    *,
    observations_by_symbol: Mapping[str, Sequence[VolatilityRegimeObservation]],
    symbol_bars: Mapping[str, Sequence[LocalDailyBar]],
    artifacts: Mapping[str, object],
) -> dict[str, object]:
    by_symbol: dict[str, object] = {}
    all_observations: list[VolatilityRegimeObservation] = []
    for symbol, observations in observations_by_symbol.items():
        all_observations.extend(observations)
        by_symbol[symbol] = {
            "return_distribution_by_regime": _return_distribution_by_regime(observations),
            "trend_momentum_exposure_relevance_by_regime": (
                _trend_momentum_exposure_relevance(
                    symbol_bars.get(symbol, ()),
                    observations,
                )
                if symbol == "SPY"
                else {"status": "not_evaluated_for_non_spy"}
            ),
        }
    basket = {
        "symbols_included": sorted(observations_by_symbol),
        "return_distribution_by_regime": _return_distribution_by_regime(all_observations),
    }
    assessment = _high_volatility_fragility_assessment(by_symbol, basket, artifacts)
    return {
        "by_symbol": by_symbol,
        "basket": basket,
        "high_volatility_fragility_assessment": assessment,
    }


def _return_distribution_by_regime(
    observations: Sequence[VolatilityRegimeObservation],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[float]] = {regime: [] for regime in _REGIMES}
    realized_grouped: dict[str, list[float]] = {regime: [] for regime in _REGIMES}
    for observation in observations:
        if observation.daily_return is not None:
            grouped[observation.regime].append(observation.daily_return)
        if observation.realized_volatility is not None:
            realized_grouped[observation.regime].append(observation.realized_volatility)
    return {
        regime: _return_distribution(grouped[regime], realized_grouped[regime])
        for regime in _REGIMES
    }


def _return_distribution(
    returns: Sequence[float],
    realized_volatility: Sequence[float],
) -> dict[str, object]:
    values = list(returns)
    negative = [value for value in values if value < 0]
    return {
        "count": len(values),
        "mean_daily_return": _round_or_none(_mean(values)),
        "median_daily_return": _round_or_none(_median(values)),
        "annualized_return_approx": _round_or_none(
            None if not values else _mean(values) * _TRADING_DAYS_PER_YEAR
        ),
        "realized_volatility_mean": _round_or_none(_mean(realized_volatility)),
        "negative_day_count": len(negative),
        "negative_day_rate": _round_or_none(None if not values else len(negative) / len(values)),
        "average_downside_return": _round_or_none(_mean(negative)),
        "worst_daily_return": _round_or_none(min(values) if values else None),
        "fifth_percentile_daily_return": _round_or_none(
            _nearest_rank_quantile(values, 0.05) if values else None
        ),
        "max_drawdown_proxy": _round_or_none(_max_drawdown(values)),
    }


def _trend_momentum_exposure_relevance(
    bars: Sequence[LocalDailyBar],
    observations: Sequence[VolatilityRegimeObservation],
) -> dict[str, object]:
    if len(bars) != len(observations) or len(bars) < 201:
        return {"status": "insufficient_spy_history_for_sma50_200_relevance"}
    closes = [float(bar.adjusted_close) for bar in bars]
    grouped: dict[str, list[tuple[bool, float]]] = {regime: [] for regime in _REGIMES}
    for index in range(1, len(bars)):
        observation = observations[index]
        if observation.daily_return is None or index < 200:
            continue
        prior_closes = closes[:index]
        sma50 = sum(prior_closes[-50:]) / 50
        sma200 = sum(prior_closes[-200:]) / 200
        trend_on = sma50 > sma200
        grouped[observation.regime].append((trend_on, observation.daily_return))

    by_regime: dict[str, object] = {}
    for regime, rows in grouped.items():
        trend_on_returns = [daily_return for trend_on, daily_return in rows if trend_on]
        trend_off_returns = [daily_return for trend_on, daily_return in rows if not trend_on]
        by_regime[regime] = {
            "count": len(rows),
            "trend_on_count": len(trend_on_returns),
            "trend_on_rate": _round_or_none(
                None if not rows else len(trend_on_returns) / len(rows)
            ),
            "trend_on_mean_daily_return": _round_or_none(_mean(trend_on_returns)),
            "trend_off_mean_daily_return": _round_or_none(_mean(trend_off_returns)),
        }
    return {
        "status": "evaluated",
        "rule": "SMA50>SMA200 as of the prior bar; grouped by current volatility regime for diagnostic context only",
        "by_regime": by_regime,
    }


def _high_volatility_fragility_assessment(
    by_symbol: Mapping[str, object],
    basket: Mapping[str, object],
    artifacts: Mapping[str, object],
) -> dict[str, object]:
    spy = _mapping_or_empty(by_symbol.get("SPY"))
    spy_distribution = _mapping_or_empty(spy.get("return_distribution_by_regime"))
    spy_high = _mapping_or_empty(spy_distribution.get("high_vol"))
    spy_normal = _mapping_or_empty(spy_distribution.get("normal_vol"))
    basket_distribution = _mapping_or_empty(basket.get("return_distribution_by_regime"))
    basket_high = _mapping_or_empty(basket_distribution.get("high_vol"))
    basket_normal = _mapping_or_empty(basket_distribution.get("normal_vol"))
    taxonomy = _mapping_or_empty(
        _mapping_or_empty(artifacts.get("research_hypothesis_triage")).get(
            "failure_taxonomy"
        )
    )
    failure_counts = {
        key: int(_mapping_or_empty(value).get("count", 0))
        for key, value in taxonomy.items()
        if key
    }

    criteria = {
        "spy_high_vol_mean_below_normal": _number(spy_high.get("mean_daily_return"))
        < _number(spy_normal.get("mean_daily_return")),
        "spy_high_vol_negative_rate_above_normal": _number(
            spy_high.get("negative_day_rate")
        )
        > _number(spy_normal.get("negative_day_rate")),
        "spy_high_vol_drawdown_worse_than_normal": _number(
            spy_high.get("max_drawdown_proxy")
        )
        < _number(spy_normal.get("max_drawdown_proxy")),
        "basket_high_vol_mean_below_normal": _number(basket_high.get("mean_daily_return"))
        < _number(basket_normal.get("mean_daily_return")),
        "prior_failures_have_oos_and_cost_fragility": (
            failure_counts.get("oos_failure", 0) > 0
            and failure_counts.get("high_cost_sensitivity", 0) > 0
        ),
    }
    supported_count = sum(1 for value in criteria.values() if value)
    if supported_count >= 4:
        assessment = "supported"
        inference = [
            "High-volatility regimes carry meaningfully weaker SPY and basket diagnostics while prior artifacts show OOS and cost fragility; one fixed offline volatility-filter backtest is justified.",
            "This remains research-only and does not authorize paper promotion.",
        ]
    elif supported_count <= 1:
        assessment = "rejected"
        inference = [
            "The fixed volatility-regime diagnostic does not explain enough of the prior fragility to justify the next offline strategy candidate.",
        ]
    else:
        assessment = "inconclusive"
        inference = [
            "The diagnostic shows partial volatility-regime relevance but not enough support for a fixed offline strategy candidate without another diagnostic pass.",
        ]
    evidence = [
        f"criteria={criteria}",
        f"supported_criteria_count={supported_count}",
        f"spy_high_vol={spy_high}",
        f"spy_normal_vol={spy_normal}",
        f"basket_high_vol={basket_high}",
        f"basket_normal_vol={basket_normal}",
        f"prior_failure_counts={failure_counts}",
    ]
    return {
        "assessment": assessment,
        "criteria": criteria,
        "supported_criteria_count": supported_count,
        "evidence": evidence,
        "inference": inference,
    }


def _selected_v2_19_next_action(classification: str) -> dict[str, object]:
    forbidden = [
        "broker reads",
        "broker mutation",
        "paper submit",
        "live endpoints",
        "live mutation",
        "paid services",
        "new credentials",
        "new market-data fetches",
        "strategy paper promotion",
        "profitability claims",
    ]
    if classification == "volatility_regime_candidate_worth_offline_backtest":
        return {
            "recommendation": "propose_fixed_offline_backtest_candidate",
            "title": "v2.19 offline volatility-regime filter backtest",
            "candidate": {
                "name": "SPY SMA50/200 baseline gated by prior-close high-volatility regime",
                "rule": (
                    "Use the existing SPY SMA50/200 trend baseline, but force cash for "
                    "the next session when the predeclared no-lookahead volatility rule "
                    "classifies SPY as high_vol. Do not add new SMA windows."
                ),
                "scope": "offline_backtest_only",
            },
            "implementation_prompt": (
                "v2.19: Add one deterministic offline backtest candidate: apply the "
                "v2.18 fixed no-lookahead volatility-regime filter to the existing SPY "
                "SMA50/200 baseline, forcing cash during high_vol regimes. Use only "
                "existing local adjusted SPY data, write ignored runs artifacts, run "
                "offline tests, do not fetch data, do not read or mutate broker state, "
                "do not submit paper orders, do not promote to paper, and make no "
                "profit claim."
            ),
            "forbidden": forbidden,
        }
    if classification == "volatility_regime_rejected_for_next_step":
        return {
            "recommendation": "reject_volatility_regime_family_for_v2_19",
            "title": "Do not backtest volatility-regime filter next",
            "implementation_prompt": (
                "v2.19: Do not add a volatility-regime strategy candidate; summarize the "
                "rejection and select a different offline-only diagnostic family without "
                "broker access, paper promotion, or market-data fetches."
            ),
            "forbidden": forbidden,
        }
    return {
        "recommendation": "collect_one_more_offline_diagnostic",
        "title": "v2.19 volatility-regime diagnostic repair",
        "implementation_prompt": (
            "v2.19: Add the smallest deterministic offline diagnostic needed to resolve "
            "the weak volatility-regime evidence, using only existing local ETF adjusted "
            "daily data and ignored runs artifacts. Do not add strategy variants, do not "
            "fetch data, do not read or mutate broker state, do not submit paper orders, "
            "do not promote to paper, and make no profit claim."
        ),
        "forbidden": forbidden,
    }


def _manifest_payload(
    payload: Mapping[str, object],
    root: Path,
    artifact_paths: Sequence[Path],
) -> dict[str, object]:
    return {
        "record_type": "volatility_regime_evidence_manifest",
        "schema_version": _SCHEMA_VERSION,
        "phase": payload.get("phase"),
        "classification": payload.get("classification"),
        "generated_at": payload.get("generated_at"),
        "artifact_root": str(root),
        "artifact_count": len(artifact_paths),
        "artifacts": [
            {
                "name": path.name,
                "path": str(path),
                "sha256": _sha256_file(path),
            }
            for path in artifact_paths
        ],
        "safety_labels": list(payload.get("safety_labels", [])),
        "broker_access_performed": payload.get("broker_access_performed"),
        "broker_mutation_performed": payload.get("broker_mutation_performed"),
        "paper_submit_performed": payload.get("paper_submit_performed"),
        "live_mutation_performed": payload.get("live_mutation_performed"),
        "market_data_fetch_performed": payload.get("market_data_fetch_performed"),
    }


def _source_safety_violations(artifacts: Mapping[str, object]) -> list[str]:
    violation_fields = (
        "broker_access_attempted",
        "broker_access_performed",
        "broker_mutation_performed",
        "credential_access_attempted",
        "live_mutation_performed",
        "network_access_attempted",
        "paper_submit_performed",
        "market_data_fetch_performed",
    )
    violations: list[str] = []
    for name, artifact in artifacts.items():
        if not isinstance(artifact, Mapping):
            continue
        safety = artifact.get("safety")
        safety_mapping = safety if isinstance(safety, Mapping) else artifact
        for field in violation_fields:
            if safety_mapping.get(field) is True:
                violations.append(f"{name}.{field}=true")
    return violations


def _existing_spy_exposure_relevance(
    challenger_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    relevant_families = {
        "sma_crossover_long_only",
        "sma_crossover_long_only_cash_risk_off",
        "time_series_momentum_long_only",
        "drawdown_filter_long_only",
    }
    rows = [
        result
        for result in challenger_results
        if result.get("symbol") == "SPY"
        and str(result.get("strategy_family")) in relevant_families
    ]
    return {
        "candidate_count": len(rows),
        "candidates": [
            {
                "candidate_id": result.get("candidate_id", ""),
                "strategy_family": result.get("strategy_family", ""),
                "exposure_percentage": result.get("exposure_percentage", ""),
                "trade_count": result.get("trade_count", ""),
                "oos_status": result.get("oos_status", ""),
                "cost_sensitivity_status": result.get("cost_sensitivity_status", ""),
                "promotion_classification": result.get("promotion_classification", ""),
            }
            for result in rows
        ],
    }


def _deterministic_generated_at(
    data_inventory: Mapping[str, object],
    artifacts: Mapping[str, object],
) -> str:
    latest_date = str(data_inventory.get("latest_date", ""))
    if latest_date:
        return f"{latest_date}T00:00:00Z"
    triage = _mapping_or_empty(artifacts.get("research_hypothesis_triage"))
    generated_at = triage.get("generated_at")
    if isinstance(generated_at, str) and generated_at:
        return generated_at
    return "1970-01-01T00:00:00Z"


def _safety_payload() -> dict[str, object]:
    return {
        "research_only": True,
        "offline_only": True,
        "not_live_authorized": True,
        "profit_claim": "none",
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "market_data_fetch_performed": False,
    }


def _config(value: object) -> VolatilityRegimeEvidenceConfig:
    if not isinstance(value, VolatilityRegimeEvidenceConfig):
        raise ValidationError("config must be a VolatilityRegimeEvidenceConfig.")
    return value


def _symbol_bars(value: object) -> dict[str, tuple[LocalDailyBar, ...]]:
    if not isinstance(value, Mapping):
        raise ValidationError("symbol_bars must be a mapping.")
    result: dict[str, tuple[LocalDailyBar, ...]] = {}
    for raw_symbol, raw_bars in value.items():
        symbol = _approved_symbol(raw_symbol)
        if not isinstance(raw_bars, Sequence):
            raise ValidationError("symbol_bars values must be sequences.")
        bars = tuple(raw_bars)
        for index, bar in enumerate(bars):
            if type(bar) is not LocalDailyBar:
                raise ValidationError(f"symbol_bars[{symbol}][{index}] must be a LocalDailyBar.")
        result[symbol] = bars
    return result


def _symbols_from_config(inputs: Mapping[str, object]) -> tuple[str, ...]:
    config = _mapping_or_empty(inputs.get("config"))
    raw_symbols = config.get("symbols", APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS)
    return _symbol_tuple(raw_symbols)


def _symbol_tuple(value: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_items = tuple(item for item in value.split(","))
    else:
        try:
            raw_items = tuple(value)
        except TypeError as exc:
            raise ValidationError("symbols must be a comma string or iterable.") from exc
    symbols: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        symbol = _approved_symbol(item)
        if symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
    if not symbols:
        raise ValidationError("symbols must contain at least one symbol.")
    return tuple(symbols)


def _approved_symbol(value: object) -> str:
    text = _required_string(value, "symbol").upper()
    if text not in APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS:
        raise ValidationError(
            "symbol must be one of "
            + ",".join(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS)
            + "."
        )
    return text


def _canonical_paths(value: Mapping[str, Path | str] | None) -> dict[str, Path]:
    if value is None:
        return {}
    paths: dict[str, Path] = {}
    for raw_symbol, raw_path in value.items():
        paths[_approved_symbol(raw_symbol)] = _path(raw_path, "canonical_path")
    return paths


def _json_path(value: Path | str, field_name: str) -> Path:
    path = _path(value, field_name)
    if path.suffix.lower() != ".json":
        raise ValidationError(f"{field_name} must reference a JSON file.")
    return path


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        if "://" in value:
            raise ValidationError(f"{field_name} must be a local path.")
        path = Path(_required_string(value, field_name))
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")
    return value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def _quantile(value: object, field_name: str) -> float:
    number = _finite_float(value, field_name)
    if number <= 0.0 or number >= 1.0:
        raise ValidationError(f"{field_name} must be between 0 and 1.")
    return number


def _finite_float(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a finite number.") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{field_name} must be a finite number.")
    return number


def _positive_float(value: object, field_name: str) -> float:
    number = _finite_float(value, field_name)
    if number <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return number


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _records(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError("records must be a sequence.")
    records: list[Mapping[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValidationError(f"records[{index}] must be a mapping.")
        records.append(item)
    return tuple(records)


def _list_of_mappings(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _count_regimes(observations: Sequence[VolatilityRegimeObservation]) -> dict[str, int]:
    counts = Counter(observation.regime for observation in observations)
    return {regime: counts.get(regime, 0) for regime in _REGIMES}


def _latest_as_of_date(
    observations_by_symbol: Mapping[str, Sequence[VolatilityRegimeObservation]],
) -> str:
    dates = [
        observations[-1].date.isoformat()
        for observations in observations_by_symbol.values()
        if observations
    ]
    return max(dates) if dates else ""


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2.0


def _max_drawdown(returns: Sequence[float]) -> float | None:
    if not returns:
        return None
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for daily_return in returns:
        equity *= 1.0 + daily_return
        peak = max(peak, equity)
        drawdown = equity / peak - 1.0
        max_drawdown = min(max_drawdown, drawdown)
    return max_drawdown


def _nearest_rank_quantile(values: Sequence[float], quantile: float) -> float:
    if not values:
        raise ValidationError("quantile values must not be empty.")
    sorted_values = sorted(_finite_float(value, "quantile_value") for value in values)
    rank = math.ceil(_quantile(quantile, "quantile") * len(sorted_values))
    index = max(0, min(len(sorted_values) - 1, rank - 1))
    return sorted_values[index]


def _number(value: object) -> float:
    if value is None:
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return number


def _round_or_none(value: float | None, digits: int = 10) -> float | None:
    if value is None:
        return None
    return round(_finite_float(value, "value"), digits)


def _markdown_number(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _artifact_status_summary(records: Sequence[Mapping[str, object]]) -> dict[str, str]:
    return {str(record.get("name")): str(record.get("status")) for record in records}


def _validate_classification(value: str) -> None:
    if value not in VOLATILITY_REGIME_EVIDENCE_CLASSIFICATIONS:
        raise ValidationError("unsupported volatility regime evidence classification.")


def _sha256_file_if_available(path: Path) -> str:
    return _sha256_file(path) if path.is_file() else ""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _json_dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(_json_safe(dict(payload)), sort_keys=True, indent=2)


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="volatility-regime-evidence")
    parser.add_argument("--output-root", default=str(_DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--data-manifest", default=str(_DEFAULT_DATA_MANIFEST))
    parser.add_argument("--challenger-results-path", default=str(_DEFAULT_CHALLENGER_RESULTS))
    parser.add_argument("--preview-review-path", default=str(_DEFAULT_PREVIEW_REVIEW))
    parser.add_argument("--triage-path", default=str(_DEFAULT_TRIAGE))
    parser.add_argument(
        "--symbols",
        default=",".join(APPROVED_MULTI_ETF_ADJUSTED_DATA_SYMBOLS),
        help="Comma-separated approved ETF symbols.",
    )
    parser.add_argument("--rolling-lookback", type=int, default=20)
    parser.add_argument("--quantile-min-history", type=int, default=252)
    parser.add_argument("--low-quantile", type=float, default=0.33)
    parser.add_argument("--high-quantile", type=float, default=0.67)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = run_volatility_regime_evidence(
            VolatilityRegimeEvidenceConfig(
                output_root=args.output_root,
                data_manifest=args.data_manifest,
                challenger_results_path=args.challenger_results_path,
                preview_review_path=args.preview_review_path,
                triage_path=args.triage_path,
                symbols=args.symbols,
                rolling_lookback=args.rolling_lookback,
                quantile_min_history=args.quantile_min_history,
                low_quantile=args.low_quantile,
                high_quantile=args.high_quantile,
            )
        )
    except ValidationError as exc:
        print(f"volatility_regime_evidence_error: {exc}")
        return 2
    print("volatility_regime_evidence_status=completed")
    print(f"classification={payload['classification']}")
    print(f"output_root={args.output_root}")
    print(f"broker_access_performed={str(payload['broker_access_performed']).lower()}")
    print(f"broker_mutation_performed={str(payload['broker_mutation_performed']).lower()}")
    print(f"paper_submit_performed={str(payload['paper_submit_performed']).lower()}")
    print(f"live_mutation_performed={str(payload['live_mutation_performed']).lower()}")
    print(
        "market_data_fetch_performed="
        f"{str(payload['market_data_fetch_performed']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
