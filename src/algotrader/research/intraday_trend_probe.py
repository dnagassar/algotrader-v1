"""Offline SPY intraday SMA trend research probe.

This module is deliberately local-file only. It does not fetch market data,
inspect credentials, import broker adapters, or authorize paper/live behavior.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError

__all__ = [
    "INTRADAY_PROBE_LABELS",
    "LOCAL_INTRADAY_BARS_CSV_COLUMNS",
    "IntradayBar",
    "IntradayTrendCandidate",
    "IntradayTrendProbeBuild",
    "IntradayTrendProbeConfig",
    "LocalIntradayBarsCsvResult",
    "build_intraday_trend_probe_from_csv",
    "evaluate_intraday_trend_candidate",
    "load_local_intraday_bars_csv",
    "render_intraday_probe_summary_markdown",
    "write_intraday_probe_artifacts",
    "write_sample_spy_intraday_fixture",
]


LOCAL_INTRADAY_BARS_CSV_COLUMNS = (
    "symbol",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
)
INTRADAY_PROBE_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "no_broker_access",
    "no_paper_submit",
    "profit_claim=none",
)
DEFAULT_INTRADAY_CANDIDATES = (
    ("spy_15m_sma_8_32", 15, 8, 32),
    ("spy_30m_sma_4_16", 30, 4, 16),
)

_RECORD_TYPE = "spy_intraday_trend_probe"
_SCHEMA_VERSION = "1"
_SYMBOL = "SPY"
_SOURCE_KIND_LOCAL = "local_intraday_csv"
_SOURCE_KIND_FIXTURE = "deterministic_fixture"
_SOURCE_KIND_CHOICES = (_SOURCE_KIND_LOCAL, _SOURCE_KIND_FIXTURE)
_POSTURE_INSUFFICIENT = "insufficient_history"
_POSTURE_RISK_ON = "risk_on"
_POSTURE_RISK_OFF = "risk_off"
_DECISION_QUALITY_FIXTURE = "fixture_behavior_only"
_DECISION_QUALITY_MARKET = "decision_quality_market_evidence"
_RECOMMEND_KEEP_RESEARCHING = "keep_researching"
_RECOMMEND_REJECT = "reject"
_RECOMMEND_PROMOTE_PREVIEW = "promote_future_preview_only_lane"
_ZERO = Decimal("0")
_ONE = Decimal("1")
_BPS_DIVISOR = Decimal("10000")
_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class IntradayBar:
    """One normalized intraday OHLCV bar."""

    symbol: str
    timestamp: datetime
    open: Decimal | str
    high: Decimal | str
    low: Decimal | str
    close: Decimal | str
    volume: int | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "timestamp",
            _aware_utc_timestamp(self.timestamp, "timestamp"),
        )
        object.__setattr__(self, "open", _positive_decimal(self.open, "open"))
        object.__setattr__(self, "high", _positive_decimal(self.high, "high"))
        object.__setattr__(self, "low", _positive_decimal(self.low, "low"))
        object.__setattr__(self, "close", _positive_decimal(self.close, "close"))
        object.__setattr__(
            self,
            "volume",
            _non_negative_int(self.volume, "volume"),
        )
        _validate_ohlc(self)

    @property
    def timestamp_text(self) -> str:
        return self.timestamp.isoformat()


@dataclass(frozen=True, slots=True)
class LocalIntradayBarsCsvResult:
    """Validated local intraday CSV bars and deterministic source metadata."""

    path: Path
    symbol: str
    source_timeframe_minutes: int
    bars: tuple[IntradayBar, ...]
    total_row_count: int
    matching_symbol_row_count: int
    ignored_wrong_symbol_row_count: int
    input_sorted_by_timestamp: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path_value(self.path, "path"))
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "source_timeframe_minutes",
            _positive_int(
                self.source_timeframe_minutes,
                "source_timeframe_minutes",
            ),
        )
        object.__setattr__(self, "bars", _bar_tuple(self.bars, "bars"))
        for field_name in (
            "total_row_count",
            "matching_symbol_row_count",
            "ignored_wrong_symbol_row_count",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_negative_int(getattr(self, field_name), field_name),
            )
        if type(self.input_sorted_by_timestamp) is not bool:
            raise ValidationError("input_sorted_by_timestamp must be a bool.")
        _validate_csv_result(self)

    @property
    def observed_bar_count(self) -> int:
        return len(self.bars)

    def source_metadata(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "schema": list(LOCAL_INTRADAY_BARS_CSV_COLUMNS),
            "symbol": self.symbol,
            "source_timeframe_minutes": self.source_timeframe_minutes,
            "source_timeframe": _timeframe_text(self.source_timeframe_minutes),
            "total_row_count": self.total_row_count,
            "matching_symbol_row_count": self.matching_symbol_row_count,
            "ignored_wrong_symbol_row_count": self.ignored_wrong_symbol_row_count,
            "input_sorted_by_timestamp": self.input_sorted_by_timestamp,
            "sorted_output": True,
            "bar_count": self.observed_bar_count,
            "start_timestamp": None
            if not self.bars
            else self.bars[0].timestamp_text,
            "end_timestamp": None
            if not self.bars
            else self.bars[-1].timestamp_text,
        }


@dataclass(frozen=True, slots=True)
class IntradayTrendCandidate:
    """One long-only intraday SMA trend candidate."""

    name: str
    timeframe_minutes: int
    fast_window: int
    slow_window: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_string(self.name, "name"))
        object.__setattr__(
            self,
            "timeframe_minutes",
            _positive_int(self.timeframe_minutes, "timeframe_minutes"),
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
        if self.fast_window >= self.slow_window:
            raise ValidationError("fast_window must be less than slow_window.")


@dataclass(frozen=True, slots=True)
class IntradayTrendProbeConfig:
    """Explicit inputs for one offline SPY intraday trend probe."""

    run_id: str
    intraday_bars_csv: Path | str
    symbol: str = _SYMBOL
    source_timeframe_minutes: int = 15
    slippage_bps: Decimal | str = Decimal("2")
    data_source_kind: str = _SOURCE_KIND_LOCAL
    candidates: tuple[IntradayTrendCandidate, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "intraday_bars_csv",
            _path_value(self.intraday_bars_csv, "intraday_bars_csv"),
        )
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "source_timeframe_minutes",
            _positive_int(
                self.source_timeframe_minutes,
                "source_timeframe_minutes",
            ),
        )
        object.__setattr__(
            self,
            "slippage_bps",
            _non_negative_decimal(self.slippage_bps, "slippage_bps"),
        )
        object.__setattr__(
            self,
            "data_source_kind",
            _choice(
                self.data_source_kind,
                "data_source_kind",
                _SOURCE_KIND_CHOICES,
            ),
        )
        object.__setattr__(
            self,
            "candidates",
            _candidate_tuple(
                self.candidates
                if self.candidates is not None
                else tuple(
                    IntradayTrendCandidate(*candidate)
                    for candidate in DEFAULT_INTRADAY_CANDIDATES
                ),
                "candidates",
            ),
        )


@dataclass(frozen=True, slots=True)
class IntradayTrendProbeBuild:
    """A built probe payload plus normalized source bars for artifact output."""

    payload: dict[str, object]
    normalized_bars: tuple[IntradayBar, ...]

    def __post_init__(self) -> None:
        if type(self.payload) is not dict:
            raise ValidationError("payload must be a dict.")
        object.__setattr__(
            self,
            "normalized_bars",
            _bar_tuple(self.normalized_bars, "normalized_bars"),
        )


def load_local_intraday_bars_csv(
    path: str | Path,
    *,
    symbol: str,
    source_timeframe_minutes: int = 15,
) -> LocalIntradayBarsCsvResult:
    """Load requested-symbol bars from a strict local intraday-bars CSV."""

    csv_path = _local_csv_path(path)
    requested_symbol = _spy_symbol(symbol)
    checked_timeframe = _positive_int(
        source_timeframe_minutes,
        "source_timeframe_minutes",
    )
    bars: list[IntradayBar] = []
    total_row_count = 0
    ignored_wrong_symbol_row_count = 0
    previous_input_timestamp: datetime | None = None
    input_sorted_by_timestamp = True
    seen_timestamps: set[datetime] = set()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        _validate_csv_columns(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            total_row_count += 1
            if None in row:
                raise ValidationError(f"CSV row {row_number} has too many values.")
            row_symbol = _symbol_text(
                _required_string(row["symbol"], f"row {row_number} symbol")
            )
            if row_symbol != requested_symbol:
                ignored_wrong_symbol_row_count += 1
                continue
            bar = _bar_from_row(row, row_number=row_number, symbol=row_symbol)
            if bar.timestamp in seen_timestamps:
                raise ValidationError(
                    f"CSV row {row_number} duplicates timestamp "
                    f"{bar.timestamp_text} for symbol {requested_symbol}."
                )
            if (
                previous_input_timestamp is not None
                and bar.timestamp < previous_input_timestamp
            ):
                input_sorted_by_timestamp = False
            previous_input_timestamp = bar.timestamp
            seen_timestamps.add(bar.timestamp)
            bars.append(bar)

    sorted_bars = tuple(sorted(bars, key=lambda item: item.timestamp))
    return LocalIntradayBarsCsvResult(
        path=csv_path,
        symbol=requested_symbol,
        source_timeframe_minutes=checked_timeframe,
        bars=sorted_bars,
        total_row_count=total_row_count,
        matching_symbol_row_count=len(sorted_bars),
        ignored_wrong_symbol_row_count=ignored_wrong_symbol_row_count,
        input_sorted_by_timestamp=input_sorted_by_timestamp,
    )


def build_intraday_trend_probe_from_csv(
    config: IntradayTrendProbeConfig,
) -> IntradayTrendProbeBuild:
    """Build one deterministic offline SPY intraday trend probe."""

    checked_config = _config(config)
    csv_result = load_local_intraday_bars_csv(
        checked_config.intraday_bars_csv,
        symbol=checked_config.symbol,
        source_timeframe_minutes=checked_config.source_timeframe_minutes,
    )
    candidate_results: list[dict[str, object]] = []
    for candidate in checked_config.candidates:
        candidate_bars = _bars_for_candidate(
            csv_result.bars,
            source_timeframe_minutes=checked_config.source_timeframe_minutes,
            candidate=candidate,
        )
        candidate_results.append(
            evaluate_intraday_trend_candidate(
                candidate_bars,
                candidate,
                slippage_bps=checked_config.slippage_bps,
            )
        )

    payload = _payload(
        checked_config,
        csv_result=csv_result,
        candidate_results=tuple(candidate_results),
    )
    return IntradayTrendProbeBuild(payload=payload, normalized_bars=csv_result.bars)


def evaluate_intraday_trend_candidate(
    bars: Iterable[IntradayBar],
    candidate: IntradayTrendCandidate,
    *,
    slippage_bps: Decimal | str,
) -> dict[str, object]:
    """Evaluate one long-only SMA candidate with next-bar exposure."""

    checked_candidate = _candidate(candidate)
    checked_bars = _bar_tuple(bars, "bars")
    checked_slippage_bps = _non_negative_decimal(slippage_bps, "slippage_bps")
    signal_history = _signal_history(
        checked_bars,
        fast_window=checked_candidate.fast_window,
        slow_window=checked_candidate.slow_window,
    )
    metrics = _candidate_metrics(
        checked_bars,
        signal_history,
        timeframe_minutes=checked_candidate.timeframe_minutes,
        slippage_bps=checked_slippage_bps,
    )
    return {
        "candidate": checked_candidate.name,
        "symbol": _SYMBOL,
        "timeframe_minutes": checked_candidate.timeframe_minutes,
        "timeframe": _timeframe_text(checked_candidate.timeframe_minutes),
        "rule": (
            f"SMA({checked_candidate.fast_window}) > "
            f"SMA({checked_candidate.slow_window}) => risk_on; "
            f"otherwise risk_off"
        ),
        "fast_window": checked_candidate.fast_window,
        "slow_window": checked_candidate.slow_window,
        "bar_count": len(checked_bars),
        "start_timestamp": None
        if not checked_bars
        else checked_bars[0].timestamp_text,
        "end_timestamp": None if not checked_bars else checked_bars[-1].timestamp_text,
        "metrics": metrics,
        "churn_assessment": _churn_assessment(metrics),
        "signal_history": signal_history,
    }


def write_intraday_probe_artifacts(
    build: IntradayTrendProbeBuild,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write deterministic ignored run artifacts for one intraday probe."""

    checked_build = _build(build)
    root = _output_dir(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    normalized_path = root / "normalized_spy_intraday_15m.csv"
    _write_normalized_bars_csv(checked_build.normalized_bars, normalized_path)
    normalized_hash = _sha256_file(normalized_path)

    payload = _json_safe(checked_build.payload)
    payload["normalized_input"] = {
        "path": normalized_path.as_posix(),
        "sha256": normalized_hash,
        "schema": list(LOCAL_INTRADAY_BARS_CSV_COLUMNS),
        "bar_count": len(checked_build.normalized_bars),
    }

    results_path = root / "intraday_probe_results.json"
    _write_json(results_path, payload)

    summary_path = root / "intraday_probe_summary.md"
    summary_path.write_text(
        render_intraday_probe_summary_markdown(payload),
        encoding="utf-8",
        newline="\n",
    )

    manifest_path = root / "intraday_probe_manifest.json"
    manifest = _manifest(
        payload,
        artifact_paths=(normalized_path, results_path, summary_path),
    )
    _write_json(manifest_path, manifest)

    return {
        "summary": summary_path,
        "results": results_path,
        "normalized_input": normalized_path,
        "manifest": manifest_path,
    }


def render_intraday_probe_summary_markdown(payload: Mapping[str, object]) -> str:
    """Render a compact Markdown summary for the probe artifact."""

    candidate_lines: list[str] = []
    for result in _mapping_sequence(payload.get("candidate_results")):
        metrics = _mapping(result.get("metrics"))
        candidate_lines.extend(
            (
                f"### {result.get('candidate', '')}",
                "",
                f"- Timeframe: {result.get('timeframe', '')}",
                f"- Rule: {result.get('rule', '')}",
                f"- Bar count: {result.get('bar_count', 0)}",
                f"- Date range: {result.get('start_timestamp', '')} to "
                f"{result.get('end_timestamp', '')}",
                f"- Signal flips: {metrics.get('signal_flips', 0)}",
                f"- Average holding period: "
                f"{metrics.get('average_holding_period_bars', '0')} bars "
                f"({metrics.get('average_holding_period_hours', '0')} hours)",
                f"- Exposure percentage: {metrics.get('exposure_percentage', '0')}",
                f"- Rough turnover: {metrics.get('rough_turnover', '0')}",
                f"- Gross return: {metrics.get('gross_return', '0')}",
                f"- Slippage-adjusted return: "
                f"{metrics.get('slippage_adjusted_return', '0')}",
                f"- Max drawdown: {metrics.get('max_drawdown', '0')}",
                f"- Buy-and-hold return: {metrics.get('buy_and_hold_return', '0')}",
                f"- Churn assessment: {result.get('churn_assessment', '')}",
                "",
            )
        )

    source = _mapping(payload.get("source"))
    lines = [
        "# SPY Intraday Trend Probe",
        "",
        f"- Run ID: {payload.get('run_id', '')}",
        f"- Classification: {payload.get('classification_recommendation', '')}",
        f"- Decision quality: {payload.get('decision_quality', '')}",
        f"- Recommendation: {payload.get('recommendation', '')}",
        f"- Symbol: {payload.get('symbol', '')}",
        f"- Data source kind: {source.get('data_source_kind', '')}",
        f"- Source path: {source.get('path', '')}",
        f"- Source timeframe: {source.get('source_timeframe', '')}",
        f"- Source date range: {source.get('start_timestamp', '')} to "
        f"{source.get('end_timestamp', '')}",
        f"- Source bar count: {source.get('bar_count', 0)}",
        f"- Live market-data fetch occurred: "
        f"{_bool_text(payload.get('market_data_fetch_performed'))}",
        f"- Broker access: {_bool_text(payload.get('broker_access_performed'))}",
        f"- Broker mutation: {_bool_text(payload.get('broker_mutation_performed'))}",
        "",
        "## Candidates",
        "",
        *candidate_lines,
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_sample_spy_intraday_fixture(path: str | Path) -> Path:
    """Write a deterministic SPY 15-minute fixture for offline probe mechanics."""

    output_path = _path_value(path, "sample_fixture_path")
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)

    bars = _sample_fixture_bars()
    _write_normalized_bars_csv(bars, output_path)
    return output_path


def _payload(
    config: IntradayTrendProbeConfig,
    *,
    csv_result: LocalIntradayBarsCsvResult,
    candidate_results: tuple[dict[str, object], ...],
) -> dict[str, object]:
    source = csv_result.source_metadata()
    source["data_source_kind"] = config.data_source_kind
    source["input_sha256"] = _sha256_file(csv_result.path)
    decision_quality = (
        _DECISION_QUALITY_FIXTURE
        if config.data_source_kind == _SOURCE_KIND_FIXTURE
        else _DECISION_QUALITY_MARKET
    )
    recommendation = _overall_recommendation(
        candidate_results,
        decision_quality=decision_quality,
    )
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "labels": list(INTRADAY_PROBE_LABELS),
        "profit_claim": "none",
        "research_only": True,
        "signal_evaluation_only": True,
        "live_authorized": False,
        "paper_submit_authorized": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "market_data_fetch_performed": False,
        "network_access_attempted": False,
        "slippage_bps": _decimal_text(config.slippage_bps),
        "slippage_model": "fixed_bps_per_exposure_change_on_strategy_equity",
        "fill_model": "next_bar_close_to_close_exposure",
        "source": source,
        "timeframes_tested": [
            _timeframe_text(result["timeframe_minutes"])
            for result in candidate_results
        ],
        "candidate_results": list(candidate_results),
        "classification_recommendation": recommendation,
        "decision_quality": decision_quality,
        "recommendation": recommendation,
    }


def _candidate_metrics(
    bars: tuple[IntradayBar, ...],
    signal_history: list[dict[str, object]],
    *,
    timeframe_minutes: int,
    slippage_bps: Decimal,
) -> dict[str, object]:
    evaluated_intervals = max(len(bars) - 1, 0)
    if not bars:
        return _empty_metrics()

    gross_equity = _ONE
    adjusted_equity = _ONE
    buy_and_hold_equity = _ONE
    peak_adjusted_equity = _ONE
    max_drawdown = _ZERO
    previous_exposure = 0
    exposure_change_count = 0
    rough_turnover = _ZERO
    exposed_intervals = 0
    holding_periods: list[int] = []
    current_holding_period = 0

    for index in range(evaluated_intervals):
        target_exposure = _target_exposure(signal_history[index]["posture"])
        exposure_change = abs(target_exposure - previous_exposure)
        if exposure_change:
            exposure_change_count += 1
            rough_turnover += Decimal(exposure_change)
            adjusted_equity -= (
                adjusted_equity
                * Decimal(exposure_change)
                * slippage_bps
                / _BPS_DIVISOR
            )

        interval_return = (bars[index + 1].close / bars[index].close) - _ONE
        buy_and_hold_equity *= _ONE + interval_return
        if target_exposure:
            exposed_intervals += 1
            current_holding_period += 1
            gross_equity *= _ONE + interval_return
            adjusted_equity *= _ONE + interval_return
        else:
            if current_holding_period:
                holding_periods.append(current_holding_period)
                current_holding_period = 0

        if adjusted_equity > peak_adjusted_equity:
            peak_adjusted_equity = adjusted_equity
        drawdown = _ONE - (adjusted_equity / peak_adjusted_equity)
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        previous_exposure = target_exposure

    if current_holding_period:
        holding_periods.append(current_holding_period)

    average_holding_period_bars = (
        _ZERO
        if not holding_periods
        else Decimal(sum(holding_periods)) / Decimal(len(holding_periods))
    )
    exposure_fraction = (
        _ZERO
        if evaluated_intervals == 0
        else Decimal(exposed_intervals) / Decimal(evaluated_intervals)
    )
    turnover_fraction = (
        _ZERO
        if evaluated_intervals == 0
        else rough_turnover / Decimal(evaluated_intervals)
    )
    return {
        "evaluated_intervals": evaluated_intervals,
        "signal_flips": _signal_flip_count(signal_history),
        "exposure_change_count": exposure_change_count,
        "average_holding_period_bars": _decimal_text(average_holding_period_bars),
        "average_holding_period_hours": _decimal_text(
            average_holding_period_bars * Decimal(timeframe_minutes) / Decimal(60)
        ),
        "exposed_intervals": exposed_intervals,
        "exposure_fraction": _decimal_text(exposure_fraction),
        "exposure_percentage": _decimal_text(exposure_fraction * Decimal(100)),
        "rough_turnover": _decimal_text(rough_turnover),
        "turnover_fraction": _decimal_text(turnover_fraction),
        "gross_return": _decimal_text(gross_equity - _ONE),
        "slippage_adjusted_return": _decimal_text(adjusted_equity - _ONE),
        "slippage_cost_return_drag": _decimal_text(gross_equity - adjusted_equity),
        "buy_and_hold_return": _decimal_text(buy_and_hold_equity - _ONE),
        "strategy_vs_buy_and_hold": _decimal_text(
            (adjusted_equity - _ONE) - (buy_and_hold_equity - _ONE)
        ),
        "max_drawdown": _decimal_text(max_drawdown),
    }


def _signal_history(
    bars: tuple[IntradayBar, ...],
    *,
    fast_window: int,
    slow_window: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, bar in enumerate(bars):
        as_of_bars = bars[: index + 1]
        sma_fast = _sma(as_of_bars, fast_window)
        sma_slow = _sma(as_of_bars, slow_window)
        if len(as_of_bars) < slow_window:
            posture = _POSTURE_INSUFFICIENT
        elif sma_fast is not None and sma_slow is not None and sma_fast > sma_slow:
            posture = _POSTURE_RISK_ON
        else:
            posture = _POSTURE_RISK_OFF
        rows.append(
            {
                "timestamp": bar.timestamp_text,
                "close": _decimal_text(bar.close),
                "sma_fast": _optional_decimal_text(sma_fast),
                "sma_slow": _optional_decimal_text(sma_slow),
                "posture": posture,
                "target_exposure": _target_exposure(posture),
            }
        )
    return rows


def _bars_for_candidate(
    bars: tuple[IntradayBar, ...],
    *,
    source_timeframe_minutes: int,
    candidate: IntradayTrendCandidate,
) -> tuple[IntradayBar, ...]:
    if candidate.timeframe_minutes == source_timeframe_minutes:
        return bars
    if candidate.timeframe_minutes < source_timeframe_minutes:
        raise ValidationError("candidate timeframe must not be below source timeframe.")
    if candidate.timeframe_minutes % source_timeframe_minutes != 0:
        raise ValidationError(
            "candidate timeframe must be an integer multiple of source timeframe."
        )
    return _aggregate_intraday_bars(
        bars,
        group_size=candidate.timeframe_minutes // source_timeframe_minutes,
    )


def _aggregate_intraday_bars(
    bars: tuple[IntradayBar, ...],
    *,
    group_size: int,
) -> tuple[IntradayBar, ...]:
    checked_group_size = _positive_int(group_size, "group_size")
    if checked_group_size == 1:
        return bars

    grouped: list[IntradayBar] = []
    day_bucket: list[IntradayBar] = []
    current_day: object | None = None
    for bar in bars:
        bar_day = bar.timestamp.date()
        if current_day is None:
            current_day = bar_day
        if bar_day != current_day:
            _append_aggregated_day(grouped, day_bucket, group_size=checked_group_size)
            day_bucket = []
            current_day = bar_day
        day_bucket.append(bar)
    _append_aggregated_day(grouped, day_bucket, group_size=checked_group_size)
    return tuple(grouped)


def _append_aggregated_day(
    output: list[IntradayBar],
    day_bars: list[IntradayBar],
    *,
    group_size: int,
) -> None:
    if not day_bars:
        return
    if len(day_bars) % group_size != 0:
        raise ValidationError(
            "intraday bars must divide evenly into requested aggregate timeframe "
            "within each UTC session date."
        )
    for offset in range(0, len(day_bars), group_size):
        chunk = tuple(day_bars[offset : offset + group_size])
        output.append(
            IntradayBar(
                symbol=chunk[0].symbol,
                timestamp=chunk[0].timestamp,
                open=chunk[0].open,
                high=max(bar.high for bar in chunk),
                low=min(bar.low for bar in chunk),
                close=chunk[-1].close,
                volume=sum(bar.volume for bar in chunk),
            )
        )


def _sma(bars: tuple[IntradayBar, ...], window: int) -> Decimal | None:
    if len(bars) < window:
        return None
    return sum((bar.close for bar in bars[-window:]), _ZERO) / Decimal(window)


def _signal_flip_count(signal_history: Sequence[Mapping[str, object]]) -> int:
    flips = 0
    previous_posture: str | None = None
    for row in signal_history:
        posture = str(row.get("posture", ""))
        if posture == _POSTURE_INSUFFICIENT:
            continue
        if previous_posture is not None and posture != previous_posture:
            flips += 1
        previous_posture = posture
    return flips


def _target_exposure(posture: object) -> int:
    return 1 if posture == _POSTURE_RISK_ON else 0


def _churn_assessment(metrics: Mapping[str, object]) -> str:
    turnover_fraction = _decimal_value(metrics.get("turnover_fraction"), "turnover_fraction")
    average_holding_period_bars = _decimal_value(
        metrics.get("average_holding_period_bars"),
        "average_holding_period_bars",
    )
    if turnover_fraction > Decimal("0.10"):
        return "too_noisy_churn_heavy"
    if turnover_fraction > Decimal("0.05") and average_holding_period_bars < Decimal("4"):
        return "borderline_churn"
    return "not_churn_heavy_on_this_input"


def _overall_recommendation(
    candidate_results: tuple[dict[str, object], ...],
    *,
    decision_quality: str,
) -> str:
    if decision_quality == _DECISION_QUALITY_FIXTURE:
        return _RECOMMEND_KEEP_RESEARCHING
    if not candidate_results:
        return _RECOMMEND_REJECT
    acceptable = [
        result
        for result in candidate_results
        if result.get("churn_assessment") != "too_noisy_churn_heavy"
        and _decimal_value(
            _mapping(result.get("metrics")).get("slippage_adjusted_return"),
            "slippage_adjusted_return",
        )
        > _ZERO
    ]
    if acceptable:
        return _RECOMMEND_PROMOTE_PREVIEW
    return _RECOMMEND_REJECT


def _empty_metrics() -> dict[str, object]:
    return {
        "evaluated_intervals": 0,
        "signal_flips": 0,
        "exposure_change_count": 0,
        "average_holding_period_bars": "0",
        "average_holding_period_hours": "0",
        "exposed_intervals": 0,
        "exposure_fraction": "0",
        "exposure_percentage": "0",
        "rough_turnover": "0",
        "turnover_fraction": "0",
        "gross_return": "0",
        "slippage_adjusted_return": "0",
        "slippage_cost_return_drag": "0",
        "buy_and_hold_return": "0",
        "strategy_vs_buy_and_hold": "0",
        "max_drawdown": "0",
    }


def _bar_from_row(
    row: dict[str, str],
    *,
    row_number: int,
    symbol: str,
) -> IntradayBar:
    return IntradayBar(
        symbol=symbol,
        timestamp=_parse_timestamp(row["timestamp"], f"row {row_number} timestamp"),
        open=_parse_decimal(row["open"], f"row {row_number} open"),
        high=_parse_decimal(row["high"], f"row {row_number} high"),
        low=_parse_decimal(row["low"], f"row {row_number} low"),
        close=_parse_decimal(row["close"], f"row {row_number} close"),
        volume=_parse_volume(row["volume"], f"row {row_number} volume"),
    )


def _local_csv_path(path: str | Path) -> Path:
    csv_path = _path_value(path, "intraday_bars_csv")
    if isinstance(path, str) and "://" in path:
        raise ValidationError("intraday_bars_csv must be a local CSV path.")
    if csv_path.suffix.lower() != ".csv":
        raise ValidationError("intraday_bars_csv must reference a CSV file.")
    if not csv_path.is_file():
        raise ValidationError(
            "intraday_bars_csv must reference an existing local CSV file."
        )
    return csv_path


def _validate_csv_columns(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValidationError("intraday_bars_csv must include a header row.")
    columns = tuple(fieldnames)
    if len(set(columns)) != len(columns):
        raise ValidationError("intraday_bars_csv must not contain duplicate columns.")
    missing_columns = tuple(
        column for column in LOCAL_INTRADAY_BARS_CSV_COLUMNS if column not in columns
    )
    if missing_columns:
        raise ValidationError(
            "intraday_bars_csv is missing required columns: "
            f"{', '.join(missing_columns)}."
        )
    extra_columns = tuple(
        column for column in columns if column not in LOCAL_INTRADAY_BARS_CSV_COLUMNS
    )
    if extra_columns:
        raise ValidationError(
            "intraday_bars_csv has unsupported columns: "
            f"{', '.join(extra_columns)}."
        )


def _validate_csv_result(result: LocalIntradayBarsCsvResult) -> None:
    if result.matching_symbol_row_count != len(result.bars):
        raise ValidationError("matching_symbol_row_count must equal bars count.")
    if (
        result.ignored_wrong_symbol_row_count + result.matching_symbol_row_count
        != result.total_row_count
    ):
        raise ValidationError("symbol row counts must equal total_row_count.")
    for previous, current in zip(result.bars, result.bars[1:]):
        if current.timestamp <= previous.timestamp:
            raise ValidationError(
                "bars must be strictly increasing after timestamp sorting."
            )


def _validate_ohlc(bar: IntradayBar) -> None:
    if bar.high < bar.open or bar.high < bar.close or bar.high < bar.low:
        raise ValidationError(
            "high must be greater than or equal to open, close, and low."
        )
    if bar.low > bar.open or bar.low > bar.close or bar.low > bar.high:
        raise ValidationError(
            "low must be less than or equal to open, close, and high."
        )


def _write_normalized_bars_csv(bars: tuple[IntradayBar, ...], path: Path) -> None:
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LOCAL_INTRADAY_BARS_CSV_COLUMNS)
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "symbol": bar.symbol,
                    "timestamp": bar.timestamp_text,
                    "open": _decimal_text(bar.open),
                    "high": _decimal_text(bar.high),
                    "low": _decimal_text(bar.low),
                    "close": _decimal_text(bar.close),
                    "volume": str(bar.volume),
                }
            )


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _manifest(
    payload: Mapping[str, object],
    *,
    artifact_paths: tuple[Path, ...],
) -> dict[str, object]:
    source = _mapping(payload.get("source"))
    return {
        "record_type": "spy_intraday_trend_probe_manifest",
        "schema_version": _SCHEMA_VERSION,
        "run_id": payload.get("run_id", ""),
        "symbol": payload.get("symbol", ""),
        "labels": list(INTRADAY_PROBE_LABELS),
        "data_source_kind": source.get("data_source_kind", ""),
        "source_path": source.get("path", ""),
        "source_timeframe": source.get("source_timeframe", ""),
        "date_range": {
            "start_timestamp": source.get("start_timestamp"),
            "end_timestamp": source.get("end_timestamp"),
        },
        "bar_count": source.get("bar_count", 0),
        "timeframes_tested": list(payload.get("timeframes_tested", [])),
        "market_data_fetch_performed": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_authorized": False,
        "artifact_hashes": [
            {
                "path": path.as_posix(),
                "sha256": _sha256_file(path),
            }
            for path in artifact_paths
        ],
    }


def _sample_fixture_bars() -> tuple[IntradayBar, ...]:
    bars: list[IntradayBar] = []
    close = Decimal("450.00")
    daily_steps = (
        tuple(Decimal("0.18") for _ in range(26)),
        tuple(
            Decimal("0.12")
            if index % 4 in (0, 1)
            else Decimal("-0.14")
            for index in range(26)
        ),
        tuple(Decimal("-0.22") for _ in range(26)),
        tuple(Decimal("0.24") for _ in range(26)),
        tuple(
            Decimal("-0.16")
            if index % 6 in (0, 1, 2)
            else Decimal("0.10")
            for index in range(26)
        ),
    )
    session_starts = (
        "2026-06-01T13:30:00+00:00",
        "2026-06-02T13:30:00+00:00",
        "2026-06-03T13:30:00+00:00",
        "2026-06-04T13:30:00+00:00",
        "2026-06-05T13:30:00+00:00",
    )
    for day_index, session_start in enumerate(session_starts):
        start = _parse_timestamp(session_start, "sample session_start")
        for bar_index, step in enumerate(daily_steps[day_index]):
            timestamp = start + timedelta(minutes=15 * bar_index)
            open_price = close
            close = close + step
            high = max(open_price, close) + Decimal("0.05")
            low = min(open_price, close) - Decimal("0.05")
            bars.append(
                IntradayBar(
                    symbol=_SYMBOL,
                    timestamp=timestamp,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=1000000 + (day_index * 10000) + (bar_index * 100),
                )
            )
    return tuple(bars)


def _parse_timestamp(value: object, field_name: str) -> datetime:
    if type(value) is datetime:
        return _aware_utc_timestamp(value, field_name)
    text = _required_string(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO timestamp.") from exc
    return _aware_utc_timestamp(parsed, field_name)


def _aware_utc_timestamp(value: object, field_name: str) -> datetime:
    if type(value) is not datetime:
        raise ValidationError(f"{field_name} must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    normalized = value.astimezone(UTC)
    return normalized.replace(microsecond=0)


def _parse_decimal(value: str, field_name: str) -> Decimal:
    return _positive_decimal(_required_string(value, field_name), field_name)


def _parse_volume(value: str, field_name: str) -> int:
    return _non_negative_int(_required_string(value, field_name), field_name)


def _spy_symbol(value: object) -> str:
    normalized = _symbol_text(value)
    if normalized != _SYMBOL:
        raise ValidationError("intraday trend probe supports only SPY.")
    return normalized


def _symbol_text(value: object) -> str:
    if type(value) is not str:
        raise ValidationError("symbol must be a string.")
    normalized = value.strip().upper()
    if not normalized:
        raise ValidationError("symbol must be a non-empty string.")
    return normalized


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _choice(value: object, field_name: str, choices: tuple[str, ...]) -> str:
    text = _required_string(value, field_name)
    if text not in choices:
        raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}.")
    return text


def _path_value(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return path


def _output_dir(value: str | Path) -> Path:
    path = _path_value(value, "output_dir")
    if path.exists() and not path.is_dir():
        raise ValidationError("output_dir must be a directory path.")
    return path


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is int and not isinstance(value, bool):
        parsed = value
    elif type(value) is str:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be a positive integer.") from exc
        if str(parsed) != value:
            raise ValidationError(f"{field_name} must be a positive integer.")
    else:
        raise ValidationError(f"{field_name} must be a positive integer.")
    if parsed <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return parsed


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is int and not isinstance(value, bool):
        parsed = value
    elif type(value) is str:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an integer.") from exc
        if str(parsed) != value:
            raise ValidationError(f"{field_name} must be an integer.")
    else:
        raise ValidationError(f"{field_name} must be an integer.")
    if parsed < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return parsed


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return decimal_value


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value < _ZERO:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return decimal_value


def _decimal_value(value: object, field_name: str) -> Decimal:
    if type(value) is Decimal:
        decimal_value = value
    elif type(value) is str:
        try:
            decimal_value = Decimal(value)
        except InvalidOperation as exc:
            raise ValidationError(f"{field_name} must be a Decimal.") from exc
    else:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not decimal_value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return decimal_value


def _decimal_text(value: object) -> str:
    decimal_value = _decimal_value(value, "decimal")
    text = format(decimal_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _timeframe_text(minutes: object) -> str:
    return f"{_positive_int(minutes, 'minutes')}m"


def _bar_tuple(
    bars: Iterable[IntradayBar],
    field_name: str,
) -> tuple[IntradayBar, ...]:
    try:
        items = tuple(bars)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be iterable.") from exc
    previous_timestamp: datetime | None = None
    seen_timestamps: set[datetime] = set()
    for index, bar in enumerate(items):
        if type(bar) is not IntradayBar:
            raise ValidationError(f"{field_name}[{index}] must be an IntradayBar.")
        if bar.timestamp in seen_timestamps:
            raise ValidationError(f"{field_name} must not contain duplicate timestamps.")
        if previous_timestamp is not None and bar.timestamp <= previous_timestamp:
            raise ValidationError(f"{field_name} must be strictly increasing.")
        seen_timestamps.add(bar.timestamp)
        previous_timestamp = bar.timestamp
    return items


def _candidate_tuple(
    candidates: Iterable[IntradayTrendCandidate],
    field_name: str,
) -> tuple[IntradayTrendCandidate, ...]:
    try:
        items = tuple(candidates)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be iterable.") from exc
    if not items:
        raise ValidationError(f"{field_name} must not be empty.")
    for index, candidate in enumerate(items):
        if type(candidate) is not IntradayTrendCandidate:
            raise ValidationError(
                f"{field_name}[{index}] must be an IntradayTrendCandidate."
            )
    return items


def _candidate(value: object) -> IntradayTrendCandidate:
    if type(value) is not IntradayTrendCandidate:
        raise ValidationError("candidate must be an IntradayTrendCandidate.")
    return value


def _config(value: object) -> IntradayTrendProbeConfig:
    if type(value) is not IntradayTrendProbeConfig:
        raise ValidationError("config must be an IntradayTrendProbeConfig.")
    return value


def _build(value: object) -> IntradayTrendProbeBuild:
    if type(value) is not IntradayTrendProbeBuild:
        raise ValidationError("build must be an IntradayTrendProbeBuild.")
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, list | tuple):
        return tuple(_mapping(item) for item in value)
    return ()


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"
