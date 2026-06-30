"""Offline SPY SMA50/200 backtest with a fixed volatility-regime filter."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import LocalDailyBar, load_local_daily_bars_csv
from algotrader.research.volatility_regime_evidence import (
    VolatilityRegimeObservation,
    build_volatility_regime_observations,
)

VOLATILITY_FILTERED_SPY_SMA_BACKTEST_LABELS: tuple[str, ...] = (
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

VOLATILITY_FILTERED_SPY_SMA_BACKTEST_CLASSIFICATIONS: tuple[str, ...] = (
    "volatility_filtered_sma_rejected",
    "volatility_filtered_sma_keep_researching",
    "volatility_filtered_sma_preview_only_research_followup",
    "volatility_filtered_sma_blocked_missing_data",
    "volatility_filtered_sma_blocked_safety_invariant",
)

_PHASE = "v2.19_spy_sma50_200_fixed_volatility_regime_filter_offline_backtest"
_SPY = "SPY"
_SHORT_WINDOW = 50
_LONG_WINDOW = 200
_VOLATILITY_LOOKBACK = 20
_QUANTILE_MIN_HISTORY = 252
_LOW_QUANTILE = 0.33
_HIGH_QUANTILE = 0.67
_TRADING_DAYS_PER_YEAR = Decimal("252")
_STARTING_EQUITY = Decimal("10000")
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/strategy_challengers/volatility_filtered_spy_sma_latest"
)
_DEFAULT_DATA_MANIFEST = Path("runs/operator_input/multi_etf_adjusted_data_manifest.json")
_DEFAULT_VOLATILITY_REGIME_EVIDENCE = Path(
    "runs/strategy_challengers/volatility_regime_evidence_latest/volatility_regime_evidence.json"
)
_DEFAULT_VALIDATION_WINDOWS = Path(
    "runs/strategy_challengers/latest/validation_windows.json"
)
_DEFAULT_COST_SENSITIVITY = Path("runs/strategy_challengers/latest/cost_sensitivity.json")
_BACKTEST_FILENAME = "volatility_filtered_spy_sma_backtest.json"
_REPORT_FILENAME = "volatility_filtered_spy_sma_backtest.md"
_MANIFEST_FILENAME = "manifest.json"
_DEFAULT_COST_ASSUMPTIONS: tuple[dict[str, Any], ...] = (
    {
        "cost_assumption_id": "zero_cost",
        "fee_bps_per_transition": "0",
        "slippage_bps_per_transition": "0",
        "total_cost_bps_per_transition": "0",
    },
    {
        "cost_assumption_id": "low_cost_1bp",
        "fee_bps_per_transition": "0",
        "slippage_bps_per_transition": "1",
        "total_cost_bps_per_transition": "1",
    },
    {
        "cost_assumption_id": "moderate_cost_5bps",
        "fee_bps_per_transition": "1",
        "slippage_bps_per_transition": "4",
        "total_cost_bps_per_transition": "5",
    },
)
_REQUIRED_BACKTEST_FIELDS: tuple[str, ...] = (
    "phase",
    "classification",
    "generated_at",
    "source_data",
    "source_artifacts",
    "baseline_rule",
    "volatility_regime_rule",
    "filtered_candidate_rule",
    "data_inventory",
    "backtest_summary",
    "baseline_metrics",
    "filtered_candidate_metrics",
    "comparison",
    "cost_sensitivity",
    "oos_or_split_summary",
    "evidence",
    "inference",
    "limitations",
    "selected_v2_20_next_action",
    "paper_candidate_count",
    "offline_shadow_candidate_count",
    "safety_labels",
    "broker_access_performed",
    "broker_mutation_performed",
    "paper_submit_performed",
    "live_mutation_performed",
    "market_data_fetch_performed",
    "normal_pytest_offline_credential_free",
)


@dataclass(frozen=True)
class VolatilityFilteredSpySmaBacktestConfig:
    """Configuration for the offline SPY volatility-filtered SMA backtest."""

    output_root: Path = _DEFAULT_OUTPUT_ROOT
    data_manifest: Path = _DEFAULT_DATA_MANIFEST
    volatility_regime_evidence_path: Path = _DEFAULT_VOLATILITY_REGIME_EVIDENCE
    validation_windows_path: Path = _DEFAULT_VALIDATION_WINDOWS
    cost_sensitivity_path: Path = _DEFAULT_COST_SENSITIVITY
    spy_data_path: Path | None = None
    symbol: str = _SPY
    starting_equity: Decimal = _STARTING_EQUITY
    short_window: int = _SHORT_WINDOW
    long_window: int = _LONG_WINDOW
    rolling_lookback: int = _VOLATILITY_LOOKBACK
    quantile_min_history: int = _QUANTILE_MIN_HISTORY
    low_quantile: float = _LOW_QUANTILE
    high_quantile: float = _HIGH_QUANTILE

    def validate_for_offline_run(self) -> None:
        if self.symbol != _SPY:
            raise ValidationError("Only SPY is allowed for the v2.19 offline backtest")
        if self.short_window != _SHORT_WINDOW or self.long_window != _LONG_WINDOW:
            raise ValidationError("The v2.19 offline run is fixed to SMA50/200")
        if self.starting_equity <= 0:
            raise ValidationError("starting_equity must be positive")
        _validate_windows(
            short_window=self.short_window,
            long_window=self.long_window,
            rolling_lookback=self.rolling_lookback,
            quantile_min_history=self.quantile_min_history,
            low_quantile=self.low_quantile,
            high_quantile=self.high_quantile,
        )


@dataclass(frozen=True)
class _SignalRow:
    index: int
    symbol: str
    date: date
    adjusted_close: Decimal
    sma_short: Decimal | None
    sma_long: Decimal | None
    baseline_posture: str
    baseline_target_exposure: int
    volatility_regime: str
    volatility_realized_annualized: float | None
    volatility_low_threshold: float | None
    volatility_high_threshold: float | None
    filtered_posture: str
    filtered_target_exposure: int


@dataclass(frozen=True)
class _BacktestPath:
    metrics: dict[str, Any]
    daily_returns: tuple[Decimal, ...]
    events: tuple[dict[str, Any], ...]


def build_volatility_filtered_spy_sma_signal_rows(
    bars: Sequence[LocalDailyBar],
    *,
    short_window: int = _SHORT_WINDOW,
    long_window: int = _LONG_WINDOW,
    rolling_lookback: int = _VOLATILITY_LOOKBACK,
    quantile_min_history: int = _QUANTILE_MIN_HISTORY,
    low_quantile: float = _LOW_QUANTILE,
    high_quantile: float = _HIGH_QUANTILE,
) -> tuple[dict[str, Any], ...]:
    """Build deterministic signal rows using adjusted closes and v2.18 regimes."""

    rows = _build_signal_rows(
        bars,
        short_window=short_window,
        long_window=long_window,
        rolling_lookback=rolling_lookback,
        quantile_min_history=quantile_min_history,
        low_quantile=low_quantile,
        high_quantile=high_quantile,
    )
    return tuple(_public_signal_row(row) for row in rows)


def compute_volatility_filtered_spy_sma_metrics(
    signal_rows: Sequence[Mapping[str, Any]],
    *,
    exposure_key: str,
    cost_bps_per_transition: Decimal | str | int = Decimal("0"),
    starting_equity: Decimal = _STARTING_EQUITY,
) -> dict[str, Any]:
    """Compute strategy metrics from public signal rows."""

    internal_rows = tuple(_signal_row_from_mapping(row) for row in signal_rows)
    path = _simulate_strategy(
        internal_rows,
        exposure_key=exposure_key,
        starting_equity=starting_equity,
        cost_bps_per_transition=_to_decimal(cost_bps_per_transition),
    )
    return path.metrics


def build_volatility_filtered_spy_sma_payload(
    config: VolatilityFilteredSpySmaBacktestConfig | None = None,
) -> dict[str, Any]:
    """Build the v2.19 offline payload without writing artifacts."""

    cfg = config or VolatilityFilteredSpySmaBacktestConfig()
    cfg.validate_for_offline_run()
    return _build_payload(cfg)


def render_volatility_filtered_spy_sma_markdown(payload: Mapping[str, Any]) -> str:
    """Render a compact operator-facing markdown report."""

    comparison = payload.get("comparison", {})
    baseline = payload.get("baseline_metrics", {})
    filtered = payload.get("filtered_candidate_metrics", {})
    lines = [
        "# v2.19 SPY SMA50/200 Volatility Filter Offline Backtest",
        "",
        f"- Classification: `{payload.get('classification')}`",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Labels: `{', '.join(payload.get('safety_labels', []))}`",
        "",
        "## Rules",
        "",
        f"- Baseline: {payload.get('baseline_rule', {}).get('summary')}",
        f"- Volatility regime: {payload.get('volatility_regime_rule', {}).get('summary')}",
        f"- Filtered candidate: {payload.get('filtered_candidate_rule', {}).get('summary')}",
        "",
        "## Full-Sample Metrics",
        "",
        "| Metric | Baseline | Filtered | Delta |",
        "| --- | ---: | ---: | ---: |",
        (
            "| Total return | "
            f"{baseline.get('total_return')} | "
            f"{filtered.get('total_return')} | "
            f"{comparison.get('total_return_delta')} |"
        ),
        (
            "| Max drawdown | "
            f"{baseline.get('max_drawdown')} | "
            f"{filtered.get('max_drawdown')} | "
            f"{comparison.get('max_drawdown_delta')} |"
        ),
        (
            "| Annualized volatility | "
            f"{baseline.get('annualized_volatility')} | "
            f"{filtered.get('annualized_volatility')} | "
            f"{comparison.get('annualized_volatility_delta')} |"
        ),
        (
            "| Sharpe-like score | "
            f"{baseline.get('sharpe_like_score')} | "
            f"{filtered.get('sharpe_like_score')} | "
            f"{comparison.get('sharpe_like_score_delta')} |"
        ),
        "",
        "## Safety",
        "",
        f"- Broker access performed: `{payload.get('broker_access_performed')}`",
        f"- Broker mutation performed: `{payload.get('broker_mutation_performed')}`",
        f"- Paper submit performed: `{payload.get('paper_submit_performed')}`",
        f"- Live mutation performed: `{payload.get('live_mutation_performed')}`",
        f"- Market data fetch performed: `{payload.get('market_data_fetch_performed')}`",
        "",
        "## Inference",
        "",
    ]
    lines.extend(f"- {item}" for item in payload.get("inference", []))
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in payload.get("limitations", []))
    lines.extend(["", "## Next Action", "", str(payload.get("selected_v2_20_next_action"))])
    lines.append("")
    return "\n".join(lines)


def write_volatility_filtered_spy_sma_artifacts(
    payload: Mapping[str, Any],
    *,
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
) -> dict[str, Path]:
    """Write JSON, markdown, and manifest artifacts under the ignored runs tree."""

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / _BACKTEST_FILENAME
    md_path = output_root / _REPORT_FILENAME
    manifest_path = output_root / _MANIFEST_FILENAME

    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_volatility_filtered_spy_sma_markdown(payload), encoding="utf-8")
    manifest = {
        "phase": payload.get("phase"),
        "classification": payload.get("classification"),
        "generated_at": payload.get("generated_at"),
        "artifacts": [
            _artifact_manifest_record(json_path),
            _artifact_manifest_record(md_path),
        ],
        "safety_labels": list(payload.get("safety_labels", [])),
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "market_data_fetch_performed": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"json": json_path, "markdown": md_path, "manifest": manifest_path}


def run_volatility_filtered_spy_sma_backtest(
    config: VolatilityFilteredSpySmaBacktestConfig | None = None,
) -> dict[str, Path]:
    """Build and write the offline v2.19 artifacts."""

    cfg = config or VolatilityFilteredSpySmaBacktestConfig()
    payload = build_volatility_filtered_spy_sma_payload(cfg)
    return write_volatility_filtered_spy_sma_artifacts(payload, output_root=cfg.output_root)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build offline SPY SMA50/200 volatility-filter backtest artifacts."
    )
    parser.add_argument("--output-root", type=Path, default=_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--data-manifest", type=Path, default=_DEFAULT_DATA_MANIFEST)
    parser.add_argument(
        "--volatility-regime-evidence-path",
        type=Path,
        default=_DEFAULT_VOLATILITY_REGIME_EVIDENCE,
    )
    parser.add_argument(
        "--validation-windows-path",
        type=Path,
        default=_DEFAULT_VALIDATION_WINDOWS,
    )
    parser.add_argument("--cost-sensitivity-path", type=Path, default=_DEFAULT_COST_SENSITIVITY)
    parser.add_argument("--spy-data-path", type=Path, default=None)
    args = parser.parse_args(argv)

    cfg = VolatilityFilteredSpySmaBacktestConfig(
        output_root=args.output_root,
        data_manifest=args.data_manifest,
        volatility_regime_evidence_path=args.volatility_regime_evidence_path,
        validation_windows_path=args.validation_windows_path,
        cost_sensitivity_path=args.cost_sensitivity_path,
        spy_data_path=args.spy_data_path,
    )
    payload = build_volatility_filtered_spy_sma_payload(cfg)
    paths = write_volatility_filtered_spy_sma_artifacts(payload, output_root=cfg.output_root)
    print("volatility_filtered_spy_sma_backtest_status=completed")
    print(f"classification={payload['classification']}")
    print(f"json_path={paths['json']}")
    print(f"markdown_path={paths['markdown']}")
    print(f"manifest_path={paths['manifest']}")
    print(f"broker_access_performed={str(payload['broker_access_performed']).lower()}")
    print(f"broker_mutation_performed={str(payload['broker_mutation_performed']).lower()}")
    print(f"paper_submit_performed={str(payload['paper_submit_performed']).lower()}")
    print(f"live_mutation_performed={str(payload['live_mutation_performed']).lower()}")
    print(f"market_data_fetch_performed={str(payload['market_data_fetch_performed']).lower()}")
    return 0


def _build_payload(cfg: VolatilityFilteredSpySmaBacktestConfig) -> dict[str, Any]:
    source_data, source_artifacts, bars, input_errors = _load_inputs(cfg)
    generated_at = _generated_at_from_bars(bars)
    if input_errors:
        return _blocked_payload(
            classification="volatility_filtered_sma_blocked_missing_data",
            generated_at=generated_at,
            source_data=source_data,
            source_artifacts=source_artifacts,
            evidence=input_errors,
        )

    safety_violations = _source_safety_violations(source_artifacts)
    if safety_violations:
        return _blocked_payload(
            classification="volatility_filtered_sma_blocked_safety_invariant",
            generated_at=generated_at,
            source_data=source_data,
            source_artifacts=source_artifacts,
            evidence=safety_violations,
        )

    assert bars is not None
    signal_rows = _build_signal_rows(
        bars,
        short_window=cfg.short_window,
        long_window=cfg.long_window,
        rolling_lookback=cfg.rolling_lookback,
        quantile_min_history=cfg.quantile_min_history,
        low_quantile=cfg.low_quantile,
        high_quantile=cfg.high_quantile,
    )
    baseline_path = _simulate_strategy(
        signal_rows,
        exposure_key="baseline_target_exposure",
        starting_equity=cfg.starting_equity,
        cost_bps_per_transition=Decimal("0"),
    )
    filtered_path = _simulate_strategy(
        signal_rows,
        exposure_key="filtered_target_exposure",
        starting_equity=cfg.starting_equity,
        cost_bps_per_transition=Decimal("0"),
    )
    comparison = _comparison(
        baseline_path.metrics,
        filtered_path.metrics,
        filtered_path.events,
    )
    cost_sensitivity = _cost_sensitivity(
        signal_rows=signal_rows,
        source_artifacts=source_artifacts,
        starting_equity=cfg.starting_equity,
    )
    oos_summary = _oos_or_split_summary(
        signal_rows=signal_rows,
        source_artifacts=source_artifacts,
        starting_equity=cfg.starting_equity,
    )
    classification = _classify_result(
        comparison=comparison,
        oos_summary=oos_summary,
    )
    evidence = _evidence_lines(
        classification=classification,
        baseline_metrics=baseline_path.metrics,
        filtered_metrics=filtered_path.metrics,
        comparison=comparison,
        cost_sensitivity=cost_sensitivity,
        oos_summary=oos_summary,
    )
    inference = _inference_lines(classification=classification, comparison=comparison)
    payload = {
        "phase": _PHASE,
        "classification": classification,
        "generated_at": generated_at,
        "source_data": source_data,
        "source_artifacts": source_artifacts,
        "baseline_rule": _baseline_rule(),
        "volatility_regime_rule": _volatility_regime_rule(cfg),
        "filtered_candidate_rule": _filtered_candidate_rule(),
        "data_inventory": _data_inventory(bars, signal_rows),
        "backtest_summary": _backtest_summary(signal_rows, baseline_path, filtered_path),
        "baseline_metrics": baseline_path.metrics,
        "filtered_candidate_metrics": filtered_path.metrics,
        "comparison": comparison,
        "cost_sensitivity": cost_sensitivity,
        "oos_or_split_summary": oos_summary,
        "evidence": evidence,
        "inference": inference,
        "limitations": _limitations(source_artifacts),
        "selected_v2_20_next_action": _selected_next_action(classification),
        "paper_candidate_count": 0,
        "offline_shadow_candidate_count": 0,
        "safety_labels": list(VOLATILITY_FILTERED_SPY_SMA_BACKTEST_LABELS),
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "market_data_fetch_performed": False,
        "normal_pytest_offline_credential_free": True,
    }
    _assert_payload_contract(payload)
    return payload


def _blocked_payload(
    *,
    classification: str,
    generated_at: str,
    source_data: Mapping[str, Any],
    source_artifacts: Mapping[str, Any],
    evidence: Sequence[str],
) -> dict[str, Any]:
    payload = {
        "phase": _PHASE,
        "classification": classification,
        "generated_at": generated_at,
        "source_data": dict(source_data),
        "source_artifacts": dict(source_artifacts),
        "baseline_rule": _baseline_rule(),
        "volatility_regime_rule": _volatility_regime_rule(
            VolatilityFilteredSpySmaBacktestConfig()
        ),
        "filtered_candidate_rule": _filtered_candidate_rule(),
        "data_inventory": {
            "symbol": _SPY,
            "usable_bar_count": 0,
            "first_date": None,
            "last_date": None,
            "usable_start_date": None,
            "latest_volatility_regime": None,
            "latest_adjusted_close": None,
        },
        "backtest_summary": {
            "status": "blocked",
            "baseline_exposure_days": 0,
            "filtered_exposure_days": 0,
            "high_vol_forced_cash_days": 0,
            "notes": list(evidence),
        },
        "baseline_metrics": _empty_metrics(),
        "filtered_candidate_metrics": _empty_metrics(),
        "comparison": _empty_comparison(),
        "cost_sensitivity": {"status": "blocked", "assumptions": [], "comparisons": []},
        "oos_or_split_summary": {"status": "blocked", "windows": []},
        "evidence": list(evidence),
        "inference": [
            "The offline backtest was not evaluated because required local inputs were missing or unsafe."
        ],
        "limitations": [
            "No paper, live, broker, or network access was attempted.",
            "Blocked packets do not imply a strategy result.",
        ],
        "selected_v2_20_next_action": (
            "Resolve the missing or unsafe local artifacts, then rerun the same fixed "
            "offline volatility-filtered SPY SMA50/200 backtest."
        ),
        "paper_candidate_count": 0,
        "offline_shadow_candidate_count": 0,
        "safety_labels": list(VOLATILITY_FILTERED_SPY_SMA_BACKTEST_LABELS),
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "market_data_fetch_performed": False,
        "normal_pytest_offline_credential_free": True,
    }
    _assert_payload_contract(payload)
    return payload


def _load_inputs(
    cfg: VolatilityFilteredSpySmaBacktestConfig,
) -> tuple[dict[str, Any], dict[str, Any], tuple[LocalDailyBar, ...] | None, list[str]]:
    errors: list[str] = []
    manifest_payload, manifest_record = _read_json_artifact(
        cfg.data_manifest,
        artifact_id="multi_etf_adjusted_data_manifest",
        required=True,
        required_fields=("symbol_data",),
    )
    source_artifacts: dict[str, Any] = {
        "multi_etf_adjusted_data_manifest": manifest_record,
        "volatility_regime_evidence_v2_18": _read_json_artifact(
            cfg.volatility_regime_evidence_path,
            artifact_id="volatility_regime_evidence_v2_18",
            required=True,
            required_fields=("classification", "latest_regimes", "regime_rule"),
        )[1],
        "validation_windows": _read_json_artifact(
            cfg.validation_windows_path,
            artifact_id="validation_windows",
            required=False,
            required_fields=("validation_windows",),
        )[1],
        "cost_sensitivity": _read_json_artifact(
            cfg.cost_sensitivity_path,
            artifact_id="cost_sensitivity",
            required=False,
            required_fields=("cost_assumptions",),
        )[1],
    }
    if manifest_payload is None:
        errors.append(f"Missing required data manifest: {cfg.data_manifest}")
        source_data = {
            "symbol": _SPY,
            "data_manifest": manifest_record,
            "spy_daily_bars": {"status": "missing_manifest"},
        }
        return source_data, source_artifacts, None, errors

    spy_record = _spy_manifest_record(manifest_payload)
    if spy_record is None:
        errors.append("Data manifest does not contain a SPY symbol_data record")
        source_data = {
            "symbol": _SPY,
            "data_manifest": manifest_record,
            "spy_daily_bars": {"status": "missing_symbol_record"},
        }
        return source_data, source_artifacts, None, errors

    data_path = cfg.spy_data_path or _spy_data_path(spy_record)
    if data_path is None:
        errors.append("SPY manifest record does not include canonical_path, data_path, or path")
    source_data = {
        "symbol": _SPY,
        "data_manifest": manifest_record,
        "spy_daily_bars": {
            "status": "pending",
            "path": str(data_path) if data_path is not None else None,
            "manifest_record": spy_record,
        },
    }
    if errors:
        return source_data, source_artifacts, None, errors

    try:
        assert data_path is not None
        result = load_local_daily_bars_csv(data_path, symbol=_SPY)
    except ValidationError as exc:
        errors.append(f"Could not load SPY local adjusted bars: {exc}")
        source_data["spy_daily_bars"] = {
            "status": "load_failed",
            "path": str(data_path),
            "manifest_record": spy_record,
        }
        return source_data, source_artifacts, None, errors

    if not result.usable_bars:
        errors.append(f"No usable SPY bars were loaded from {data_path}")
        source_data["spy_daily_bars"] = {
            "status": "empty",
            "path": str(data_path),
            "manifest_record": spy_record,
            "loader_metadata": result.source_metadata(),
        }
        return source_data, source_artifacts, None, errors

    bars = tuple(result.usable_bars)
    source_data["spy_daily_bars"] = {
        "status": "available",
        "path": str(data_path),
        "sha256": _sha256_file(data_path),
        "manifest_record": spy_record,
        "loader_metadata": result.source_metadata(),
        "usable_bar_count": len(bars),
        "first_date": bars[0].date.isoformat(),
        "last_date": bars[-1].date.isoformat(),
    }

    for artifact_id, record in source_artifacts.items():
        if record.get("required") and record.get("status") != "available":
            errors.append(f"Missing required source artifact: {artifact_id} at {record.get('path')}")
    return source_data, source_artifacts, bars, errors


def _read_json_artifact(
    path: Path,
    *,
    artifact_id: str,
    required: bool,
    required_fields: Sequence[str],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    record: dict[str, Any] = {
        "artifact_id": artifact_id,
        "path": str(path),
        "required": required,
    }
    if not path.exists():
        record["status"] = "missing"
        record["missing_required_fields"] = list(required_fields)
        return None, record
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        record["status"] = "unreadable"
        record["error"] = str(exc)
        record["missing_required_fields"] = list(required_fields)
        return None, record

    missing = tuple(field for field in required_fields if field not in payload)
    record.update(
        {
            "status": "available" if not missing else "incomplete",
            "sha256": _sha256_file(path),
            "missing_required_fields": list(missing),
            "classification": payload.get("classification"),
            "phase": payload.get("phase"),
            "generated_at": payload.get("generated_at"),
            "safety_labels": payload.get("safety_labels"),
            "broker_access_performed": payload.get("broker_access_performed"),
            "broker_mutation_performed": payload.get("broker_mutation_performed"),
            "paper_submit_performed": payload.get("paper_submit_performed"),
            "live_mutation_performed": payload.get("live_mutation_performed"),
            "market_data_fetch_performed": payload.get("market_data_fetch_performed"),
        }
    )
    if missing:
        return None, record
    record["payload"] = _small_artifact_payload(payload, artifact_id=artifact_id)
    return payload, record


def _small_artifact_payload(payload: Mapping[str, Any], *, artifact_id: str) -> dict[str, Any]:
    if artifact_id == "validation_windows":
        return {
            "validation_window_method": payload.get("validation_window_method"),
            "symbols": payload.get("symbols"),
            "window_count": len(payload.get("validation_windows", [])),
        }
    if artifact_id == "cost_sensitivity":
        return {
            "cost_assumption_count": len(payload.get("cost_assumptions", [])),
            "cost_assumptions": payload.get("cost_assumptions", []),
        }
    if artifact_id == "volatility_regime_evidence_v2_18":
        return {
            "classification": payload.get("classification"),
            "selected_v2_19_next_action": payload.get("selected_v2_19_next_action"),
            "latest_regime_for_spy": _latest_regime_for_symbol(payload, _SPY),
        }
    if artifact_id == "multi_etf_adjusted_data_manifest":
        return {
            "source": payload.get("source"),
            "generated_at": payload.get("generated_at"),
            "expected_latest_date": payload.get("expected_latest_date"),
        }
    return {}


def _spy_manifest_record(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    symbol_data = payload.get("symbol_data")
    if isinstance(symbol_data, Mapping):
        record = symbol_data.get(_SPY)
        return dict(record) if isinstance(record, Mapping) else None
    if isinstance(symbol_data, Sequence) and not isinstance(symbol_data, (str, bytes)):
        for record in symbol_data:
            if isinstance(record, Mapping) and record.get("symbol") == _SPY:
                return dict(record)
    return None


def _spy_data_path(spy_record: Mapping[str, Any]) -> Path | None:
    for field_name in ("canonical_path", "data_path", "path"):
        raw_path = spy_record.get(field_name)
        if isinstance(raw_path, str) and raw_path.strip():
            return Path(raw_path)
    return None


def _latest_regime_for_symbol(payload: Mapping[str, Any], symbol: str) -> Any:
    latest = payload.get("latest_regimes")
    if isinstance(latest, Mapping):
        return latest.get(symbol)
    if isinstance(latest, Sequence) and not isinstance(latest, (str, bytes)):
        for record in latest:
            if isinstance(record, Mapping) and record.get("symbol") == symbol:
                return dict(record)
    return None


def _build_signal_rows(
    bars: Sequence[LocalDailyBar],
    *,
    short_window: int,
    long_window: int,
    rolling_lookback: int,
    quantile_min_history: int,
    low_quantile: float,
    high_quantile: float,
) -> tuple[_SignalRow, ...]:
    if not bars:
        return tuple()
    _validate_windows(
        short_window=short_window,
        long_window=long_window,
        rolling_lookback=rolling_lookback,
        quantile_min_history=quantile_min_history,
        low_quantile=low_quantile,
        high_quantile=high_quantile,
    )
    observations = build_volatility_regime_observations(
        bars,
        rolling_lookback=rolling_lookback,
        quantile_min_history=quantile_min_history,
        low_quantile=low_quantile,
        high_quantile=high_quantile,
    )
    observations_by_date = {obs.date: obs for obs in observations}
    rows: list[_SignalRow] = []
    for index, bar in enumerate(bars):
        window = tuple(bars[: index + 1])
        sma_short = _sma_adjusted_close(window, short_window)
        sma_long = _sma_adjusted_close(window, long_window)
        baseline_posture = _baseline_posture(
            history_length=len(window),
            sma_short=sma_short,
            sma_long=sma_long,
            long_window=long_window,
        )
        baseline_target_exposure = 1 if baseline_posture == "risk_on" else 0
        observation = observations_by_date.get(bar.date)
        regime = observation.regime if observation is not None else "insufficient_history"
        filtered_target_exposure = (
            baseline_target_exposure if regime != "high_vol" else 0
        )
        filtered_posture = _filtered_posture(
            baseline_posture=baseline_posture,
            baseline_target_exposure=baseline_target_exposure,
            volatility_regime=regime,
        )
        rows.append(
            _SignalRow(
                index=index,
                symbol=bar.symbol,
                date=bar.date,
                adjusted_close=bar.adjusted_close,
                sma_short=sma_short,
                sma_long=sma_long,
                baseline_posture=baseline_posture,
                baseline_target_exposure=baseline_target_exposure,
                volatility_regime=regime,
                volatility_realized_annualized=(
                    observation.realized_volatility if observation else None
                ),
                volatility_low_threshold=(
                    observation.low_vol_threshold if observation else None
                ),
                volatility_high_threshold=(
                    observation.high_vol_threshold if observation else None
                ),
                filtered_posture=filtered_posture,
                filtered_target_exposure=filtered_target_exposure,
            )
        )
    return tuple(rows)


def _validate_windows(
    *,
    short_window: int,
    long_window: int,
    rolling_lookback: int,
    quantile_min_history: int,
    low_quantile: float,
    high_quantile: float,
) -> None:
    if short_window <= 0 or long_window <= 0:
        raise ValidationError("SMA windows must be positive")
    if short_window >= long_window:
        raise ValidationError("short_window must be less than long_window")
    if rolling_lookback <= 1:
        raise ValidationError("rolling_lookback must be greater than 1")
    if quantile_min_history <= 0:
        raise ValidationError("quantile_min_history must be positive")
    if not 0 < low_quantile < high_quantile < 1:
        raise ValidationError("Volatility quantiles must satisfy 0 < low < high < 1")


def _sma_adjusted_close(bars: Sequence[LocalDailyBar], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    total = sum((bar.adjusted_close for bar in bars[-window:]), Decimal("0"))
    return total / Decimal(window)


def _baseline_posture(
    *,
    history_length: int,
    sma_short: Decimal | None,
    sma_long: Decimal | None,
    long_window: int,
) -> str:
    if history_length < long_window or sma_short is None or sma_long is None:
        return "insufficient_history"
    if sma_short > sma_long:
        return "risk_on"
    return "risk_off"


def _filtered_posture(
    *,
    baseline_posture: str,
    baseline_target_exposure: int,
    volatility_regime: str,
) -> str:
    if baseline_posture == "insufficient_history":
        return "insufficient_history"
    if baseline_target_exposure == 1 and volatility_regime == "high_vol":
        return "forced_cash_high_vol"
    return baseline_posture


def _simulate_strategy(
    signal_rows: Sequence[_SignalRow],
    *,
    exposure_key: str,
    starting_equity: Decimal,
    cost_bps_per_transition: Decimal,
) -> _BacktestPath:
    if exposure_key not in {"baseline_target_exposure", "filtered_target_exposure"}:
        raise ValidationError("Unsupported exposure_key")
    equity = starting_equity
    peak_equity = starting_equity
    max_drawdown = Decimal("0")
    previous_exposure = 0
    strategy_returns: list[Decimal] = []
    evaluated_returns: list[Decimal] = []
    equity_curve: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    trade_count = 0
    transition_count = 0
    total_cost = Decimal("0")
    exposed_return_count = 0
    evaluated_return_count = 0
    forced_cash_days = 0
    evaluated_start_date: date | None = None
    evaluated_end_date: date | None = None

    cost_rate = cost_bps_per_transition / Decimal("10000")
    for index, row in enumerate(signal_rows):
        if index == 0:
            current_exposure = 0
            asset_return = Decimal("0")
            prior_posture = "insufficient_history"
            prior_volatility_regime = "insufficient_history"
            evaluated_return = False
            interval_start: date | None = None
        else:
            previous_row = signal_rows[index - 1]
            current_exposure = int(getattr(previous_row, exposure_key))
            asset_return = (row.adjusted_close / previous_row.adjusted_close) - Decimal("1")
            prior_posture = previous_row.baseline_posture
            prior_volatility_regime = previous_row.volatility_regime
            evaluated_return = prior_posture != "insufficient_history"
            interval_start = previous_row.date

        strategy_return_before_cost = (
            asset_return if current_exposure == 1 else Decimal("0")
        )
        equity *= Decimal("1") + strategy_return_before_cost
        transition = abs(current_exposure - previous_exposure)
        action = _exposure_action(previous_exposure, current_exposure)
        transition_cost = Decimal("0")
        if transition:
            transition_count += transition
            trade_count += 1
            transition_cost = equity * cost_rate * Decimal(transition)
            total_cost += transition_cost
            equity -= transition_cost
        if evaluated_return:
            evaluated_return_count += 1
            evaluated_returns.append(strategy_return_before_cost)
            if current_exposure == 1:
                exposed_return_count += 1
            if (
                exposure_key == "filtered_target_exposure"
                and current_exposure == 0
                and index > 0
                and signal_rows[index - 1].baseline_target_exposure == 1
                and prior_volatility_regime == "high_vol"
            ):
                forced_cash_days += 1
            if evaluated_start_date is None:
                evaluated_start_date = interval_start
            evaluated_end_date = row.date

        strategy_returns.append(strategy_return_before_cost)
        if equity > peak_equity:
            peak_equity = equity
        if peak_equity > 0:
            drawdown = (peak_equity - equity) / peak_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        event = {
            "date": row.date.isoformat(),
            "action": action,
            "current_exposure": current_exposure,
            "asset_return": _decimal_text(asset_return),
            "strategy_return": _decimal_text(strategy_return_before_cost),
            "transition_cost": _decimal_text(transition_cost),
            "equity": _decimal_text(equity),
            "evaluated_return": evaluated_return,
        }
        events.append(event)
        equity_curve.append(
            {
                "date": row.date.isoformat(),
                "equity": _decimal_text(equity),
                "drawdown": _decimal_text(drawdown if peak_equity > 0 else Decimal("0")),
                "exposure": current_exposure,
            }
        )
        previous_exposure = current_exposure

    total_return = (equity / starting_equity) - Decimal("1") if starting_equity > 0 else None
    downside_count = sum(1 for value in evaluated_returns if value < 0)
    annualized_return = _annualized_return(
        total_return=total_return,
        start_date=evaluated_start_date,
        end_date=evaluated_end_date,
    )
    annualized_volatility = _annualized_volatility(evaluated_returns)
    sharpe_like_score = _ratio_or_none(annualized_return, annualized_volatility)
    benchmark_total_return = _benchmark_total_return(signal_rows)
    metrics = {
        "starting_equity": _decimal_text(starting_equity),
        "ending_equity": _decimal_text(equity),
        "total_return": _decimal_text(total_return),
        "benchmark_buy_hold_total_return": _decimal_text(benchmark_total_return),
        "excess_return_vs_buy_hold": _decimal_text(
            total_return - benchmark_total_return
            if total_return is not None and benchmark_total_return is not None
            else None
        ),
        "annualized_return": _decimal_text(annualized_return),
        "annualized_volatility": _decimal_text(annualized_volatility),
        "sharpe_like_score": _decimal_text(sharpe_like_score),
        "max_drawdown": _decimal_text(max_drawdown),
        "downside_return_count": downside_count,
        "downside_return_rate": _decimal_text(
            Decimal(downside_count) / Decimal(evaluated_return_count)
            if evaluated_return_count
            else None
        ),
        "evaluated_return_count": evaluated_return_count,
        "exposure_days": exposed_return_count,
        "exposure_fraction": _decimal_text(
            Decimal(exposed_return_count) / Decimal(evaluated_return_count)
            if evaluated_return_count
            else None
        ),
        "trade_count": trade_count,
        "transition_count": transition_count,
        "turnover_proxy": transition_count,
        "high_vol_forced_cash_days": forced_cash_days,
        "total_transaction_cost": _decimal_text(total_cost),
        "cost_bps_per_transition": _decimal_text(cost_bps_per_transition),
        "first_date": signal_rows[0].date.isoformat() if signal_rows else None,
        "last_date": signal_rows[-1].date.isoformat() if signal_rows else None,
        "evaluated_start_date": evaluated_start_date.isoformat()
        if evaluated_start_date is not None
        else None,
        "evaluated_end_date": evaluated_end_date.isoformat()
        if evaluated_end_date is not None
        else None,
        "equity_curve_observation_count": len(equity_curve),
    }
    return _BacktestPath(
        metrics=metrics,
        daily_returns=tuple(evaluated_returns),
        events=tuple(events),
    )


def _exposure_action(previous_exposure: int, current_exposure: int) -> str:
    if previous_exposure == 0 and current_exposure == 1:
        return "buy"
    if previous_exposure == 1 and current_exposure == 0:
        return "sell"
    if current_exposure == 1:
        return "hold_long"
    return "hold_cash"


def _annualized_return(
    *,
    total_return: Decimal | None,
    start_date: date | None,
    end_date: date | None,
) -> Decimal | None:
    if total_return is None or start_date is None or end_date is None:
        return None
    day_count = (end_date - start_date).days
    if day_count <= 0:
        return None
    if total_return <= Decimal("-1"):
        return None
    value = (float(Decimal("1") + total_return) ** (365.25 / float(day_count))) - 1.0
    return _float_decimal(value)


def _annualized_volatility(returns: Sequence[Decimal]) -> Decimal | None:
    if len(returns) < 2:
        return None
    values = [float(value) for value in returns]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return _float_decimal(math.sqrt(variance) * math.sqrt(float(_TRADING_DAYS_PER_YEAR)))


def _ratio_or_none(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _benchmark_total_return(signal_rows: Sequence[_SignalRow]) -> Decimal | None:
    if len(signal_rows) < 2:
        return None
    start = signal_rows[0].adjusted_close
    end = signal_rows[-1].adjusted_close
    if start <= 0:
        return None
    return (end / start) - Decimal("1")


def _comparison(
    baseline_metrics: Mapping[str, Any],
    filtered_metrics: Mapping[str, Any],
    filtered_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    fields = (
        "ending_equity",
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "sharpe_like_score",
        "max_drawdown",
        "exposure_fraction",
        "trade_count",
        "transition_count",
        "turnover_proxy",
    )
    comparison: dict[str, Any] = {}
    for field in fields:
        comparison[f"{field}_delta"] = _decimal_text(
            _decimal_delta(filtered_metrics.get(field), baseline_metrics.get(field))
        )
    comparison["high_vol_forced_cash_days"] = filtered_metrics.get(
        "high_vol_forced_cash_days", 0
    )
    comparison["high_vol_forced_cash_event_count"] = sum(
        1
        for event in filtered_events
        if event.get("evaluated_return")
        and event.get("current_exposure") == 0
        and event.get("action") in {"sell", "hold_cash"}
    )
    comparison["return_tradeoff_summary"] = _return_tradeoff_summary(comparison)
    return comparison


def _return_tradeoff_summary(comparison: Mapping[str, Any]) -> str:
    total_delta = _to_decimal_or_none(comparison.get("total_return_delta"))
    drawdown_delta = _to_decimal_or_none(comparison.get("max_drawdown_delta"))
    sharpe_delta = _to_decimal_or_none(comparison.get("sharpe_like_score_delta"))
    parts: list[str] = []
    if total_delta is not None:
        parts.append("higher_return" if total_delta > 0 else "lower_or_equal_return")
    if drawdown_delta is not None:
        parts.append("lower_drawdown" if drawdown_delta < 0 else "higher_or_equal_drawdown")
    if sharpe_delta is not None:
        parts.append("higher_sharpe_like" if sharpe_delta > 0 else "lower_or_equal_sharpe_like")
    return ",".join(parts) if parts else "insufficient_metrics"


def _cost_sensitivity(
    *,
    signal_rows: Sequence[_SignalRow],
    source_artifacts: Mapping[str, Any],
    starting_equity: Decimal,
) -> dict[str, Any]:
    assumptions = _cost_assumptions(source_artifacts.get("cost_sensitivity"))
    comparisons: list[dict[str, Any]] = []
    for assumption in assumptions:
        bps = _to_decimal(assumption["total_cost_bps_per_transition"])
        baseline = _simulate_strategy(
            signal_rows,
            exposure_key="baseline_target_exposure",
            starting_equity=starting_equity,
            cost_bps_per_transition=bps,
        )
        filtered = _simulate_strategy(
            signal_rows,
            exposure_key="filtered_target_exposure",
            starting_equity=starting_equity,
            cost_bps_per_transition=bps,
        )
        comparison = _comparison(baseline.metrics, filtered.metrics, filtered.events)
        comparisons.append(
            {
                "cost_assumption_id": assumption["cost_assumption_id"],
                "fee_bps_per_transition": assumption["fee_bps_per_transition"],
                "slippage_bps_per_transition": assumption[
                    "slippage_bps_per_transition"
                ],
                "total_cost_bps_per_transition": assumption[
                    "total_cost_bps_per_transition"
                ],
                "baseline_metrics": baseline.metrics,
                "filtered_candidate_metrics": filtered.metrics,
                "comparison": comparison,
            }
        )
    return {
        "status": "computed",
        "source": _artifact_source_status(source_artifacts.get("cost_sensitivity")),
        "assumptions": assumptions,
        "comparisons": comparisons,
    }


def _cost_assumptions(record: Any) -> list[dict[str, Any]]:
    payload = record.get("payload") if isinstance(record, Mapping) else None
    raw_assumptions = payload.get("cost_assumptions") if isinstance(payload, Mapping) else None
    if not isinstance(raw_assumptions, Sequence) or isinstance(raw_assumptions, (str, bytes)):
        return [dict(item) for item in _DEFAULT_COST_ASSUMPTIONS]
    assumptions: list[dict[str, Any]] = []
    for item in raw_assumptions:
        if not isinstance(item, Mapping):
            continue
        cost_id = item.get("cost_assumption_id") or item.get("id")
        if cost_id is None:
            cost_id = item.get("cost_id")
        total = item.get("total_cost_bps_per_transition")
        if cost_id is None or total is None:
            continue
        assumptions.append(
            {
                "cost_assumption_id": str(cost_id),
                "fee_bps_per_transition": str(
                    item.get("fee_bps_per_transition", item.get("fee_bps", "0"))
                ),
                "slippage_bps_per_transition": str(
                    item.get(
                        "slippage_bps_per_transition",
                        item.get("slippage_bps", total),
                    )
                ),
                "total_cost_bps_per_transition": str(total),
            }
        )
    return assumptions or [dict(item) for item in _DEFAULT_COST_ASSUMPTIONS]


def _oos_or_split_summary(
    *,
    signal_rows: Sequence[_SignalRow],
    source_artifacts: Mapping[str, Any],
    starting_equity: Decimal,
) -> dict[str, Any]:
    validation_record = source_artifacts.get("validation_windows")
    windows = _validation_windows(validation_record, len(signal_rows))
    summaries: list[dict[str, Any]] = []
    for window in windows:
        start_index = int(window["start_index"])
        end_index_exclusive = int(window["end_index_exclusive"])
        sliced_rows = tuple(signal_rows[start_index:end_index_exclusive])
        baseline = _simulate_strategy(
            sliced_rows,
            exposure_key="baseline_target_exposure",
            starting_equity=starting_equity,
            cost_bps_per_transition=Decimal("0"),
        )
        filtered = _simulate_strategy(
            sliced_rows,
            exposure_key="filtered_target_exposure",
            starting_equity=starting_equity,
            cost_bps_per_transition=Decimal("0"),
        )
        summaries.append(
            {
                "window_id": window["window_id"],
                "role": window.get("role"),
                "start_date": window.get("start_date"),
                "end_date": window.get("end_date"),
                "start_index": start_index,
                "end_index_exclusive": end_index_exclusive,
                "baseline_metrics": baseline.metrics,
                "filtered_candidate_metrics": filtered.metrics,
                "comparison": _comparison(
                    baseline.metrics,
                    filtered.metrics,
                    filtered.events,
                ),
            }
        )
    primary = next(
        (item for item in summaries if item.get("window_id") == "later_test"),
        summaries[-1] if summaries else None,
    )
    return {
        "status": "computed" if summaries else "unavailable",
        "source": _artifact_source_status(validation_record),
        "validation_window_method": _validation_window_method(validation_record),
        "primary_out_of_sample_window_id": primary.get("window_id") if primary else None,
        "primary_out_of_sample_comparison": primary.get("comparison") if primary else None,
        "windows": summaries,
        "limitation": (
            "Metrics reuse existing chronological index windows when available; "
            "only this fixed candidate is evaluated, with no parameter search or promotion."
        ),
    }


def _validation_windows(record: Any, row_count: int) -> list[dict[str, Any]]:
    payload = record.get("payload") if isinstance(record, Mapping) else None
    raw_windows = None
    if isinstance(record, Mapping) and record.get("status") == "available":
        path = record.get("path")
        if path:
            try:
                full_payload = json.loads(Path(str(path)).read_text(encoding="utf-8"))
                raw_windows = full_payload.get("validation_windows")
            except (OSError, json.JSONDecodeError):
                raw_windows = None
    if not isinstance(raw_windows, Sequence) or isinstance(raw_windows, (str, bytes)):
        half = row_count // 2
        return [
            {
                "window_id": "full_sample",
                "role": "full_sample",
                "start_index": 0,
                "end_index_exclusive": row_count,
                "start_date": None,
                "end_date": None,
            },
            {
                "window_id": "early_train",
                "role": "train",
                "start_index": 0,
                "end_index_exclusive": half,
                "start_date": None,
                "end_date": None,
            },
            {
                "window_id": "later_test",
                "role": "test",
                "start_index": half,
                "end_index_exclusive": row_count,
                "start_date": None,
                "end_date": None,
            },
        ]
    windows: list[dict[str, Any]] = []
    for raw in raw_windows:
        if not isinstance(raw, Mapping):
            continue
        symbol = raw.get("symbol")
        symbols = raw.get("symbols")
        if symbol not in {None, _SPY} and _SPY not in _as_string_sequence(symbols):
            continue
        start_index = raw.get("start_index")
        end_index_exclusive = raw.get("end_index_exclusive")
        if start_index is None and raw.get("start_offset") is not None:
            start_index = raw.get("start_offset")
        if end_index_exclusive is None and raw.get("end_offset_exclusive") is not None:
            end_index_exclusive = raw.get("end_offset_exclusive")
        if end_index_exclusive is None and raw.get("end_index_inclusive") is not None:
            end_index_exclusive = int(raw["end_index_inclusive"]) + 1
        if start_index is None or end_index_exclusive is None:
            continue
        start = max(0, int(start_index))
        end = min(row_count, int(end_index_exclusive))
        if start >= end:
            continue
        windows.append(
            {
                "window_id": str(raw.get("window_id") or raw.get("id") or f"window_{len(windows)}"),
                "role": raw.get("role"),
                "start_index": start,
                "end_index_exclusive": end,
                "start_date": raw.get("start_date"),
                "end_date": raw.get("end_date"),
            }
        )
    return windows or _validation_windows(None, row_count)


def _as_string_sequence(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value)
    return tuple()


def _validation_window_method(record: Any) -> str:
    payload = record.get("payload") if isinstance(record, Mapping) else None
    if isinstance(payload, Mapping) and payload.get("validation_window_method"):
        return str(payload["validation_window_method"])
    return "full_sample_plus_chronological_half_split_fallback"


def _artifact_source_status(record: Any) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        return {"status": "fallback_default", "path": None}
    return {
        "status": record.get("status"),
        "path": record.get("path"),
        "sha256": record.get("sha256"),
        "fallback_used": record.get("status") != "available",
    }


def _classify_result(
    *,
    comparison: Mapping[str, Any],
    oos_summary: Mapping[str, Any],
) -> str:
    total_delta = _to_decimal_or_none(comparison.get("total_return_delta"))
    drawdown_delta = _to_decimal_or_none(comparison.get("max_drawdown_delta"))
    sharpe_delta = _to_decimal_or_none(comparison.get("sharpe_like_score_delta"))
    primary = oos_summary.get("primary_out_of_sample_comparison")
    oos_total_delta = (
        _to_decimal_or_none(primary.get("total_return_delta"))
        if isinstance(primary, Mapping)
        else None
    )
    oos_sharpe_delta = (
        _to_decimal_or_none(primary.get("sharpe_like_score_delta"))
        if isinstance(primary, Mapping)
        else None
    )
    if (
        total_delta is not None
        and sharpe_delta is not None
        and total_delta < Decimal("-0.05")
        and sharpe_delta < Decimal("-0.10")
    ):
        return "volatility_filtered_sma_rejected"
    if (
        total_delta is not None
        and drawdown_delta is not None
        and sharpe_delta is not None
        and oos_total_delta is not None
        and oos_sharpe_delta is not None
        and total_delta > 0
        and drawdown_delta <= 0
        and sharpe_delta > 0
        and oos_total_delta > 0
        and oos_sharpe_delta > 0
    ):
        return "volatility_filtered_sma_preview_only_research_followup"
    return "volatility_filtered_sma_keep_researching"


def _evidence_lines(
    *,
    classification: str,
    baseline_metrics: Mapping[str, Any],
    filtered_metrics: Mapping[str, Any],
    comparison: Mapping[str, Any],
    cost_sensitivity: Mapping[str, Any],
    oos_summary: Mapping[str, Any],
) -> list[str]:
    primary = oos_summary.get("primary_out_of_sample_comparison")
    primary_total_delta = (
        primary.get("total_return_delta") if isinstance(primary, Mapping) else None
    )
    moderate = next(
        (
            item
            for item in cost_sensitivity.get("comparisons", [])
            if item.get("cost_assumption_id") == "moderate_cost_5bps"
        ),
        None,
    )
    moderate_delta = (
        moderate.get("comparison", {}).get("total_return_delta")
        if isinstance(moderate, Mapping)
        else None
    )
    return [
        f"Classification is {classification}.",
        (
            "Full-sample baseline total return "
            f"{baseline_metrics.get('total_return')} versus filtered "
            f"{filtered_metrics.get('total_return')}."
        ),
        (
            "Full-sample max drawdown delta "
            f"{comparison.get('max_drawdown_delta')} and Sharpe-like delta "
            f"{comparison.get('sharpe_like_score_delta')}."
        ),
        (
            "The filter forced cash on "
            f"{comparison.get('high_vol_forced_cash_days')} evaluated high-volatility days."
        ),
        f"Primary OOS total-return delta is {primary_total_delta}.",
        f"Moderate-cost total-return delta is {moderate_delta}.",
        "No strategy was promoted to paper or live use.",
    ]


def _inference_lines(*, classification: str, comparison: Mapping[str, Any]) -> list[str]:
    if classification == "volatility_filtered_sma_rejected":
        return [
            "The fixed high-volatility cash filter did not clear the offline evidence bar.",
            "The result should remain research-only unless a later offline hypothesis shows a stronger risk-adjusted tradeoff.",
        ]
    if classification == "volatility_filtered_sma_preview_only_research_followup":
        return [
            "The fixed filter improved the offline tradeoff enough for a research follow-up packet.",
            "The result is not paper-submit authorized and should not alter any broker-facing workflow.",
        ]
    if classification == "volatility_filtered_sma_keep_researching":
        return [
            "The fixed filter produced mixed or insufficient offline evidence.",
            "The safest next step is another deterministic research slice, not paper promotion.",
        ]
    return [
        "The packet is blocked and cannot support strategy conclusions.",
    ]


def _selected_next_action(classification: str) -> str:
    if classification == "volatility_filtered_sma_rejected":
        return (
            "v2.20: Preserve this rejected research packet and return to fixed, offline "
            "hypothesis review before considering any new SPY baseline modification."
        )
    if classification == "volatility_filtered_sma_preview_only_research_followup":
        return (
            "v2.20: Build a preview-only offline research follow-up for the fixed "
            "volatility-filtered SPY SMA50/200 candidate, including stress slices and "
            "operator review artifacts, with paper_candidate_count remaining zero."
        )
    if classification == "volatility_filtered_sma_keep_researching":
        return (
            "v2.20: Add a deterministic offline follow-up that explains when the fixed "
            "high-volatility cash filter helps or hurts the SPY SMA50/200 baseline."
        )
    return (
        "v2.20: Fix the blocked local inputs and rerun the same offline-only backtest."
    )


def _source_safety_violations(source_artifacts: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    unsafe_true_fields = (
        "broker_access_performed",
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_mutation_performed",
        "market_data_fetch_performed",
    )
    for artifact_id, record in source_artifacts.items():
        if not isinstance(record, Mapping) or record.get("status") != "available":
            continue
        for field in unsafe_true_fields:
            if record.get(field) is True:
                violations.append(f"{artifact_id} has unsafe flag {field}=true")
    return violations


def _baseline_rule() -> dict[str, Any]:
    return {
        "summary": "SPY adjusted-close SMA50/200 baseline; risk_on when SMA50 > SMA200, else cash.",
        "symbol": _SPY,
        "price_basis": "adjusted_close",
        "short_sma_window": _SHORT_WINDOW,
        "long_sma_window": _LONG_WINDOW,
        "risk_on_condition": "SMA50 > SMA200",
        "risk_off_condition": "SMA50 <= SMA200",
        "insufficient_history_condition": "fewer than 200 usable as-of bars",
        "execution_timing": (
            "Posture computed through date T is applied to the next close-to-close interval."
        ),
        "allowlist": [_SPY],
    }


def _volatility_regime_rule(cfg: VolatilityFilteredSpySmaBacktestConfig) -> dict[str, Any]:
    return {
        "summary": (
            "v2.18 no-lookahead 20-day adjusted-close realized volatility regime with "
            "expanding prior-only 33/67 nearest-rank thresholds."
        ),
        "price_basis": "adjusted_close",
        "return_basis": "daily adjusted-close returns",
        "rolling_lookback": cfg.rolling_lookback,
        "annualization_factor": int(_TRADING_DAYS_PER_YEAR),
        "quantile_min_history": cfg.quantile_min_history,
        "low_quantile": cfg.low_quantile,
        "high_quantile": cfg.high_quantile,
        "classification_values": [
            "insufficient_history",
            "low_vol",
            "normal_vol",
            "high_vol",
        ],
        "lookahead_policy": (
            "Current realized volatility is compared only with prior realized-volatility "
            "observations; current and future values are excluded from thresholds."
        ),
    }


def _filtered_candidate_rule() -> dict[str, Any]:
    return {
        "summary": (
            "Risk_on only when SPY SMA50 > SMA200 and the fixed v2.18 regime is not high_vol; "
            "force cash during high_vol."
        ),
        "baseline_dependency": "SPY adjusted-close SMA50/200 baseline",
        "risk_on_condition": "SMA50 > SMA200 and volatility_regime != high_vol",
        "forced_cash_condition": "volatility_regime == high_vol",
        "unchanged_parameters": {
            "sma_short_window": _SHORT_WINDOW,
            "sma_long_window": _LONG_WINDOW,
            "volatility_lookback": _VOLATILITY_LOOKBACK,
            "low_quantile": _LOW_QUANTILE,
            "high_quantile": _HIGH_QUANTILE,
        },
        "parameter_search_performed": False,
        "strategy_promotion_performed": False,
    }


def _data_inventory(bars: Sequence[LocalDailyBar], signal_rows: Sequence[_SignalRow]) -> dict[str, Any]:
    latest = signal_rows[-1] if signal_rows else None
    first_usable = next(
        (row.date for row in signal_rows if row.baseline_posture != "insufficient_history"),
        None,
    )
    regimes = _count_by(row.volatility_regime for row in signal_rows)
    return {
        "symbol": _SPY,
        "usable_bar_count": len(bars),
        "first_date": bars[0].date.isoformat() if bars else None,
        "last_date": bars[-1].date.isoformat() if bars else None,
        "usable_start_date": first_usable.isoformat() if first_usable else None,
        "latest_adjusted_close": _decimal_text(latest.adjusted_close if latest else None),
        "latest_volatility_regime": latest.volatility_regime if latest else None,
        "volatility_regime_counts": regimes,
        "sma_insufficient_history_count": sum(
            1 for row in signal_rows if row.baseline_posture == "insufficient_history"
        ),
        "baseline_risk_on_count": sum(
            1 for row in signal_rows if row.baseline_target_exposure == 1
        ),
        "filtered_risk_on_count": sum(
            1 for row in signal_rows if row.filtered_target_exposure == 1
        ),
    }


def _backtest_summary(
    signal_rows: Sequence[_SignalRow],
    baseline_path: _BacktestPath,
    filtered_path: _BacktestPath,
) -> dict[str, Any]:
    return {
        "status": "computed",
        "row_count": len(signal_rows),
        "baseline_exposure_days": baseline_path.metrics.get("exposure_days"),
        "filtered_exposure_days": filtered_path.metrics.get("exposure_days"),
        "baseline_trade_count": baseline_path.metrics.get("trade_count"),
        "filtered_trade_count": filtered_path.metrics.get("trade_count"),
        "high_vol_forced_cash_days": filtered_path.metrics.get(
            "high_vol_forced_cash_days"
        ),
        "first_signal_date": signal_rows[0].date.isoformat() if signal_rows else None,
        "last_signal_date": signal_rows[-1].date.isoformat() if signal_rows else None,
        "sample_latest_rows": [
            _public_signal_row(row)
            for row in signal_rows[-5:]
        ],
    }


def _limitations(source_artifacts: Mapping[str, Any]) -> list[str]:
    limitations = [
        "This is an offline research backtest only; it is not a paper or live trading authorization.",
        "No broker state, broker adapter, order submission, cancellation, replacement, close, or liquidation path was touched.",
        "No market data was fetched; the test used only existing local adjusted SPY bars.",
        "Only the fixed high-volatility cash rule was evaluated; no SMA window search, volatility-threshold search, or strategy catalog promotion was performed.",
        "Execution is approximated as next close-to-close exposure after an as-of signal, matching the local SMA baseline convention.",
    ]
    validation_status = _artifact_source_status(source_artifacts.get("validation_windows"))
    if validation_status.get("fallback_used"):
        limitations.append(
            "Validation-window artifact was unavailable, so split metrics used a deterministic fallback."
        )
    cost_status = _artifact_source_status(source_artifacts.get("cost_sensitivity"))
    if cost_status.get("fallback_used"):
        limitations.append(
            "Cost-sensitivity artifact was unavailable, so built-in zero/1bp/5bp assumptions were used."
        )
    return limitations


def _empty_metrics() -> dict[str, Any]:
    return {
        "starting_equity": _decimal_text(_STARTING_EQUITY),
        "ending_equity": None,
        "total_return": None,
        "benchmark_buy_hold_total_return": None,
        "excess_return_vs_buy_hold": None,
        "annualized_return": None,
        "annualized_volatility": None,
        "sharpe_like_score": None,
        "max_drawdown": None,
        "downside_return_count": 0,
        "downside_return_rate": None,
        "evaluated_return_count": 0,
        "exposure_days": 0,
        "exposure_fraction": None,
        "trade_count": 0,
        "transition_count": 0,
        "turnover_proxy": 0,
        "high_vol_forced_cash_days": 0,
        "total_transaction_cost": "0",
        "cost_bps_per_transition": "0",
        "first_date": None,
        "last_date": None,
        "evaluated_start_date": None,
        "evaluated_end_date": None,
        "equity_curve_observation_count": 0,
    }


def _empty_comparison() -> dict[str, Any]:
    return {
        "ending_equity_delta": None,
        "total_return_delta": None,
        "annualized_return_delta": None,
        "annualized_volatility_delta": None,
        "sharpe_like_score_delta": None,
        "max_drawdown_delta": None,
        "exposure_fraction_delta": None,
        "trade_count_delta": None,
        "transition_count_delta": None,
        "turnover_proxy_delta": None,
        "high_vol_forced_cash_days": 0,
        "high_vol_forced_cash_event_count": 0,
        "return_tradeoff_summary": "blocked",
    }


def _public_signal_row(row: _SignalRow) -> dict[str, Any]:
    return {
        "index": row.index,
        "symbol": row.symbol,
        "date": row.date.isoformat(),
        "adjusted_close": _decimal_text(row.adjusted_close),
        "sma_short": _decimal_text(row.sma_short),
        "sma_long": _decimal_text(row.sma_long),
        "baseline_posture": row.baseline_posture,
        "baseline_target_exposure": row.baseline_target_exposure,
        "volatility_regime": row.volatility_regime,
        "volatility_realized_annualized": row.volatility_realized_annualized,
        "volatility_low_threshold": row.volatility_low_threshold,
        "volatility_high_threshold": row.volatility_high_threshold,
        "filtered_posture": row.filtered_posture,
        "filtered_target_exposure": row.filtered_target_exposure,
    }


def _signal_row_from_mapping(row: Mapping[str, Any]) -> _SignalRow:
    return _SignalRow(
        index=int(row["index"]),
        symbol=str(row["symbol"]),
        date=date.fromisoformat(str(row["date"])),
        adjusted_close=_to_decimal(row["adjusted_close"]),
        sma_short=_to_decimal_or_none(row.get("sma_short")),
        sma_long=_to_decimal_or_none(row.get("sma_long")),
        baseline_posture=str(row["baseline_posture"]),
        baseline_target_exposure=int(row["baseline_target_exposure"]),
        volatility_regime=str(row["volatility_regime"]),
        volatility_realized_annualized=row.get("volatility_realized_annualized"),
        volatility_low_threshold=row.get("volatility_low_threshold"),
        volatility_high_threshold=row.get("volatility_high_threshold"),
        filtered_posture=str(row["filtered_posture"]),
        filtered_target_exposure=int(row["filtered_target_exposure"]),
    )


def _assert_payload_contract(payload: Mapping[str, Any]) -> None:
    missing = [field for field in _REQUIRED_BACKTEST_FIELDS if field not in payload]
    if missing:
        raise ValidationError(f"Backtest payload missing required fields: {missing}")
    if payload["classification"] not in VOLATILITY_FILTERED_SPY_SMA_BACKTEST_CLASSIFICATIONS:
        raise ValidationError(f"Unsupported classification: {payload['classification']}")
    labels = set(payload["safety_labels"])
    missing_labels = set(VOLATILITY_FILTERED_SPY_SMA_BACKTEST_LABELS) - labels
    if missing_labels:
        raise ValidationError(f"Backtest payload missing safety labels: {sorted(missing_labels)}")
    for field in (
        "broker_access_performed",
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_mutation_performed",
        "market_data_fetch_performed",
    ):
        if payload[field] is not False:
            raise ValidationError(f"Unsafe flag must be false: {field}")
    if payload["paper_candidate_count"] != 0 or payload["offline_shadow_candidate_count"] != 0:
        raise ValidationError("v2.19 must not promote paper or offline-shadow candidates")


def _generated_at_from_bars(bars: Sequence[LocalDailyBar] | None) -> str:
    if bars:
        return f"{bars[-1].date.isoformat()}T00:00:00Z"
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_manifest_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _float_decimal(value: float) -> Decimal:
    if not math.isfinite(value):
        return Decimal("NaN")
    return Decimal(str(round(value, 12)))


def _decimal_delta(first: Any, second: Any) -> Decimal | None:
    first_decimal = _to_decimal_or_none(first)
    second_decimal = _to_decimal_or_none(second)
    if first_decimal is None or second_decimal is None:
        return None
    return first_decimal - second_decimal


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"Cannot convert value to Decimal: {value!r}") from exc


def _to_decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        converted = _to_decimal(value)
    except ValidationError:
        return None
    if converted.is_nan():
        return None
    return converted


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _count_by(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


if __name__ == "__main__":
    raise SystemExit(main())
