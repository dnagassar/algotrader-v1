"""Deterministic offline strategy challenger factory for SPY SMA candidates."""

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
    "STRATEGY_CHALLENGER_FACTORY_LABELS",
    "STRATEGY_CHALLENGER_PROMOTION_CLASSIFICATIONS",
    "StrategyChallengerCandidate",
    "StrategyChallengerFactoryConfig",
    "build_default_strategy_challenger_candidates",
    "build_strategy_challenger_payload",
    "build_strategy_challenger_validation_windows",
    "classify_strategy_challenger_promotion",
    "main",
    "render_strategy_challenger_summary_markdown",
    "run_strategy_challenger_factory",
    "write_strategy_challenger_artifacts",
]


STRATEGY_CHALLENGER_FACTORY_LABELS = (
    "research_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
)
STRATEGY_CHALLENGER_PROMOTION_CLASSIFICATIONS = (
    "reject",
    "keep_researching",
    "preview_only",
    "paper_candidate",
)

_RECORD_TYPE = "strategy_challenger_factory"
_SCHEMA_VERSION = "1"
_FACTORY_ID = "v2.11_strategy_challenger_factory"
_PREVIOUS_FACTORY_ID = "v2.10_strategy_challenger_factory"
_DEFAULT_SYMBOL = "SPY"
_DEFAULT_TIMEFRAME = "1d"
_DEFAULT_DATA_PATH = Path("runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv")
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
_DATA_QUALITY_VALID = "valid_local_daily_bars"
_DATA_QUALITY_MALFORMED = "malformed_or_unreadable_local_daily_bars"
_DATA_QUALITY_MISSING = "missing_local_daily_bars"
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
        if self.fast_window >= self.slow_window:
            raise ValidationError("fast_window must be less than slow_window.")

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
        }


@dataclass(frozen=True, slots=True)
class StrategyChallengerFactoryConfig:
    """Inputs for one offline strategy challenger factory run."""

    output_root: Path | str
    data_path: Path | str = _DEFAULT_DATA_PATH
    symbol: str = _DEFAULT_SYMBOL
    as_of: date | str | None = None
    initial_equity: Decimal | str = _DEFAULT_INITIAL_EQUITY
    fee_bps: Decimal | str = _DEFAULT_FEE_BPS
    slippage_bps: Decimal | str = _DEFAULT_SLIPPAGE_BPS
    candidates: tuple[StrategyChallengerCandidate, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _path(self.output_root, "output_root"))
        object.__setattr__(self, "data_path", _path(self.data_path, "data_path"))
        object.__setattr__(self, "symbol", _symbol(self.symbol))
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


def build_default_strategy_challenger_candidates(
    *,
    symbol: str = _DEFAULT_SYMBOL,
) -> tuple[StrategyChallengerCandidate, ...]:
    """Return the small v2.10 deterministic candidate set."""

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
            candidate_id=_CASH_RISK_OFF_COMPARATOR_ID,
            strategy_family="sma_crossover_long_only_cash_risk_off",
            symbol=checked_symbol,
            timeframe=_DEFAULT_TIMEFRAME,
            fast_window=50,
            slow_window=200,
            role="baseline_comparator",
            risk_off_state="cash_zero_return",
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
    """Evaluate challenger candidates against the current SPY SMA 50/200 baseline."""

    checked_config = _config(config)
    data_sha256 = _file_sha256_or_none(checked_config.data_path)
    data_error: str | None = None
    data_quality_status = _DATA_QUALITY_VALID
    csv_result: LocalDailyBarsCsvResult | None = None
    validation_windows: tuple[dict[str, object], ...] = ()
    cost_assumptions = _cost_assumption_records()

    try:
        csv_result = load_local_daily_bars_csv(
            checked_config.data_path,
            symbol=checked_config.symbol,
            as_of=checked_config.as_of,
        )
    except ValidationError as exc:
        data_error = str(exc)
        data_quality_status = (
            _DATA_QUALITY_MISSING
            if not checked_config.data_path.exists()
            else _DATA_QUALITY_MALFORMED
        )

    if csv_result is None:
        results = tuple(
            _rejected_data_result(
                candidate,
                config=checked_config,
                data_sha256=data_sha256,
                data_quality_status=data_quality_status,
                data_error=data_error or data_quality_status,
            )
            for candidate in checked_config.candidates
        )
    else:
        validation_windows = build_strategy_challenger_validation_windows(
            csv_result.usable_bars
        )
        results = _evaluate_candidates(
            csv_result,
            config=checked_config,
            data_sha256=data_sha256,
            validation_windows=validation_windows,
        )

    recommendations = _build_promotion_recommendations(results)
    as_of_start, as_of_end = _payload_as_of_range(results)
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "previous_factory_id": _PREVIOUS_FACTORY_ID,
        "run_id": _run_id(checked_config.symbol, as_of_end, data_sha256),
        "labels": list(STRATEGY_CHALLENGER_FACTORY_LABELS),
        "symbol": checked_config.symbol,
        "timeframe": _DEFAULT_TIMEFRAME,
        "data_path": str(checked_config.data_path),
        "data_sha256": data_sha256,
        "data_quality_status": data_quality_status,
        "data_error": data_error,
        "as_of_start": as_of_start,
        "as_of_end": as_of_end,
        "candidate_count": len(results),
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "validation_window_method": _VALIDATION_WINDOW_METHOD,
        "validation_windows": list(validation_windows),
        "cost_assumptions": list(cost_assumptions),
        "results": [dict(result) for result in results],
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
        return "reject", ("malformed_or_missing_data",)
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
        return "paper_candidate", (
            "clear_return_improvement_without_drawdown_regression",
            "positive_absolute_return",
            "risk_adjusted_score_improved",
            "out_of_sample_validation_passed",
            "cost_sensitivity_survived",
            "sample_history_acceptable",
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
        f"- symbol: {payload_dict.get('symbol')}",
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
            "## Candidate Results",
            "| candidate_id | total_return | max_drawdown | sharpe_ratio | transitions | exposure_pct | OOS passed | moderate cost edge broken | classification |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for result in _result_list(payload_dict):
        out_of_sample = _mapping_or_empty(result.get("out_of_sample_validation"))
        cost_summary = _mapping_or_empty(result.get("cost_sensitivity_summary"))
        lines.append(
            "| {candidate_id} | {total_return} | {max_drawdown} | "
            "{sharpe_ratio} | {transition_count} | {exposure_percentage} | "
            "{out_of_sample_passed} | {edge_broken} | {promotion_classification} |".format(
                candidate_id=result.get("candidate_id"),
                total_return=_markdown_value(result.get("total_return")),
                max_drawdown=_markdown_value(result.get("max_drawdown")),
                sharpe_ratio=_markdown_value(result.get("sharpe_ratio")),
                transition_count=_markdown_value(result.get("transition_count")),
                exposure_percentage=_markdown_value(result.get("exposure_percentage")),
                out_of_sample_passed=_markdown_value(
                    out_of_sample.get("validation_passed")
                ),
                edge_broken=_markdown_value(
                    cost_summary.get("edge_broken_by_moderate_cost")
                ),
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
        _add_validation_window_baseline_comparisons(enriched, baseline)
        _add_cost_baseline_comparisons(enriched, baseline)
        enriched["out_of_sample_validation"] = _out_of_sample_validation_summary(
            enriched
        )
        enriched["cost_sensitivity_summary"] = _cost_sensitivity_summary(enriched)
        classification, reasons = classify_strategy_challenger_promotion(
            enriched,
            baseline,
        )
        enriched["promotion_classification"] = classification
        enriched["promotion_reasons"] = list(reasons)
        results.append(enriched)

    return tuple(results)


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
        "symbol": candidate.symbol,
        "timeframe": candidate.timeframe,
        "role": candidate.role,
        "fast_window": candidate.fast_window,
        "slow_window": candidate.slow_window,
        "risk_off_state": candidate.risk_off_state,
        "data_path": str(csv_result.path),
        "data_sha256": data_sha256,
        "data_quality_status": _DATA_QUALITY_VALID,
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
    base = {
        "record_type": "strategy_challenger_result",
        "schema_version": _SCHEMA_VERSION,
        "factory_id": _FACTORY_ID,
        "previous_factory_id": _PREVIOUS_FACTORY_ID,
        "candidate_id": candidate.candidate_id,
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "strategy_family": candidate.strategy_family,
        "symbol": candidate.symbol,
        "timeframe": candidate.timeframe,
        "role": candidate.role,
        "fast_window": candidate.fast_window,
        "slow_window": candidate.slow_window,
        "risk_off_state": candidate.risk_off_state,
        "data_path": str(config.data_path),
        "data_sha256": data_sha256,
        "data_quality_status": data_quality_status,
        "data_error": data_error,
        "as_of_start": None,
        "as_of_end": None,
        "total_bars": 0,
        "usable_bars": 0,
        "source_total_rows": 0,
        "ignored_wrong_symbol_row_count": 0,
        "ignored_future_bar_count": 0,
        "required_history_bars": candidate.slow_window,
        "metrics_status": "rejected_data_invalid",
        "promotion_classification": "reject",
        "promotion_reasons": ["malformed_or_missing_data"],
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
        "baseline_total_return_delta": None,
        "baseline_max_drawdown_delta": None,
        "baseline_annualized_return_delta": None,
        "baseline_volatility_delta": None,
        "baseline_sharpe_ratio_delta": None,
        "full_sample_metrics": None,
        "validation_window_metrics": [],
        "out_of_sample_metrics": {
            "primary_window_id": _LATER_TEST_WINDOW_ID,
            "windows": [],
        },
        "out_of_sample_validation": _empty_out_of_sample_validation_summary(),
        "cost_adjusted_metrics": [],
        "cost_sensitivity_summary": _empty_cost_sensitivity_summary(),
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
) -> dict[str, object]:
    if baseline is None or baseline.get("metrics_status") != "valid":
        return _empty_baseline_comparison()
    if result.get("metrics_status") != "valid":
        return _empty_baseline_comparison(baseline_available=True)

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
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "baseline_available": True,
        "total_return_delta": _decimal_text(total_return_delta),
        "max_drawdown_delta": _decimal_text(drawdown_delta),
        "annualized_return_delta": _optional_decimal_text(annualized_return_delta),
        "volatility_delta": _optional_decimal_text(volatility_delta),
        "sharpe_ratio_delta": _optional_decimal_text(sharpe_delta),
        "exposure_percentage_delta": _decimal_text(exposure_delta),
        "return_improved": total_return_delta > _ZERO,
        "drawdown_improved": drawdown_delta < _ZERO,
        "same_as_baseline": result.get("candidate_id") == _BASELINE_CANDIDATE_ID,
    }


def _empty_baseline_comparison(
    *,
    baseline_available: bool = False,
) -> dict[str, object]:
    return {
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
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


def _build_promotion_recommendations(
    results: Iterable[Mapping[str, object]],
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
        and result.get("candidate_id") != _CASH_RISK_OFF_COMPARATOR_ID
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
        "best_candidate_id": None if best is None else best.get("candidate_id"),
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
        "timeframe": payload.get("timeframe"),
        "data_path": payload.get("data_path"),
        "data_sha256": payload.get("data_sha256"),
        "validation_window_method": payload.get("validation_window_method"),
        "validation_windows": list(payload.get("validation_windows", [])),
        "safety": _safety_payload(),
    }


def _cost_sensitivity_artifact(payload: Mapping[str, object]) -> dict[str, object]:
    results = [
        {
            "candidate_id": result.get("candidate_id"),
            "baseline_candidate_id": result.get("baseline_candidate_id"),
            "cost_assumptions_evaluated": result.get("cost_assumptions_evaluated", []),
            "cost_sensitivity_summary": result.get("cost_sensitivity_summary", {}),
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
        "timeframe": payload.get("timeframe"),
        "data_path": payload.get("data_path"),
        "data_sha256": payload.get("data_sha256"),
        "cost_assumptions": list(payload.get("cost_assumptions", [])),
        "results": results,
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


def _run_id(symbol: str, as_of_end: str | None, data_sha256: str | None) -> str:
    date_part = "unknown_as_of" if as_of_end is None else as_of_end.replace("-", "")
    hash_part = "missingdata" if data_sha256 is None else data_sha256[:12]
    return f"strategy_challenger_factory_{symbol.lower()}_{date_part}_{hash_part}"


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
    print("broker_mutation_performed=false")
    print("live_mutation_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
