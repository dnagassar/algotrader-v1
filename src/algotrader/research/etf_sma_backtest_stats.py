"""Offline SPY ETF/SMA 50/200 daily backtest statistics artifact."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.local_daily_bars import (
    LocalDailyBar,
    load_local_daily_bars_csv,
)

__all__ = [
    "ETF_SMA_BACKTEST_STATS_LABELS",
    "ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY",
    "EtfSmaBacktestStatsBar",
    "EtfSmaBacktestStatsConfig",
    "build_etf_sma_backtest_stats",
    "build_etf_sma_backtest_stats_from_bars",
    "render_etf_sma_backtest_stats_json",
    "render_etf_sma_backtest_stats_text",
    "write_etf_sma_backtest_stats_jsonl",
]


ETF_SMA_BACKTEST_STATS_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)
ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY = (
    "Compute SMA posture using bars available through bar t; apply that "
    "target exposure only to the next close-to-close return interval t->t+1."
)

_RECORD_TYPE = "etf_sma_backtest_stats"
_SCHEMA_VERSION = "1"
_COMMAND = "etf-sma-backtest-stats"
_STRATEGY = "spy_etf_sma_50_200_daily_long_only"
_SYMBOL = "SPY"
_DATA_BASIS = "raw_close_price_return"
_PRICE_FIELD = "close"
_FILL_MODEL_NEXT_CLOSE = "next_close"
_BENCHMARK_BUY_AND_HOLD = "buy_and_hold"
_COST_MODEL = "bps_per_exposure_change_on_strategy_equity"
_REGIME_SLICES_DEFAULT = "default"
_REGIME_SLICE_RECORD_TYPE = "etf_sma_regime_slice_evidence"
_REGIME_SLICE_MILESTONE = "M417"
_REGIME_SLICE_VERDICT_SCOPE = "raw_close_regime_risk_profile_only"
_REGIME_SLICE_POLICY = (
    "Slice already-evaluated close-to-close return intervals by interval end date; "
    "calendar-year slices use the prior trading-day close as the start boundary."
)
_RETURN_RANKING_BASIS = "provisional_raw_close_price_return_only"
_DEFAULT_REGIME_SLICE_SPECS = (
    ("full_evaluated_window", None, None),
    ("stress_2022", date(2022, 1, 1), date(2022, 12, 31)),
    ("recovery_2023", date(2023, 1, 1), date(2023, 12, 31)),
    ("bull_2024", date(2024, 1, 1), date(2024, 12, 31)),
    ("whipsaw_2025", date(2025, 1, 1), date(2025, 12, 31)),
    ("ytd_2026", date(2026, 1, 1), date(2026, 12, 31)),
)
_SHORT_WINDOW = 50
_LONG_WINDOW = 200
_DEFAULT_STARTING_EQUITY = Decimal("25.00")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_POSTURE_INSUFFICIENT = "insufficient_history"
_POSTURE_RISK_ON = "risk_on"
_POSTURE_RISK_OFF = "risk_off"


@dataclass(frozen=True, slots=True)
class EtfSmaBacktestStatsBar:
    """One validated local daily price observation."""

    date: date
    adjusted_close: Decimal
    close: Decimal | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", _plain_date(self.date, "date"))
        adjusted_close = _positive_decimal(self.adjusted_close, "adjusted_close")
        object.__setattr__(
            self,
            "adjusted_close",
            adjusted_close,
        )
        object.__setattr__(
            self,
            "close",
            _positive_decimal(
                adjusted_close if self.close is None else self.close,
                "close",
            ),
        )


@dataclass(frozen=True, slots=True)
class EtfSmaBacktestStatsConfig:
    """Explicit inputs for one offline ETF/SMA statistics artifact."""

    run_id: str
    daily_bars_csv: Path | str
    symbol: str = _SYMBOL
    starting_equity: Decimal | str = _DEFAULT_STARTING_EQUITY
    short_window: int = _SHORT_WINDOW
    long_window: int = _LONG_WINDOW
    benchmark: str = _BENCHMARK_BUY_AND_HOLD
    fill_model: str = _FILL_MODEL_NEXT_CLOSE
    cost_bps: Decimal | str = _ZERO
    regime_slices: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "daily_bars_csv",
            _path_value(self.daily_bars_csv, "daily_bars_csv"),
        )
        object.__setattr__(self, "symbol", _spy_symbol(self.symbol))
        object.__setattr__(
            self,
            "starting_equity",
            _positive_decimal(self.starting_equity, "starting_equity"),
        )
        object.__setattr__(
            self,
            "short_window",
            _positive_int(self.short_window, "short_window"),
        )
        object.__setattr__(
            self,
            "long_window",
            _positive_int(self.long_window, "long_window"),
        )
        object.__setattr__(
            self,
            "benchmark",
            _choice(
                self.benchmark,
                "benchmark",
                (_BENCHMARK_BUY_AND_HOLD,),
            ),
        )
        object.__setattr__(
            self,
            "fill_model",
            _choice(
                self.fill_model,
                "fill_model",
                (_FILL_MODEL_NEXT_CLOSE,),
            ),
        )
        object.__setattr__(
            self,
            "cost_bps",
            _non_negative_decimal(self.cost_bps, "cost_bps"),
        )
        object.__setattr__(
            self,
            "regime_slices",
            _optional_choice(
                self.regime_slices,
                "regime_slices",
                (_REGIME_SLICES_DEFAULT,),
            ),
        )
        if self.short_window >= self.long_window:
            raise ValidationError("short_window must be less than long_window.")
        if self.short_window != _SHORT_WINDOW or self.long_window != _LONG_WINDOW:
            raise ValidationError("M406 supports only SMA 50/200 windows.")


def build_etf_sma_backtest_stats(
    config: EtfSmaBacktestStatsConfig,
) -> dict[str, object]:
    """Load strict local daily bars and build one deterministic stats artifact."""

    checked_config = _config(config)
    source_path = checked_config.daily_bars_csv
    if not source_path.exists():
        return _blocked_payload(
            checked_config,
            backtest_state="blocked_missing_daily_bars_csv",
            performance_evidence_state="missing_daily_bars_csv",
            blockers=("missing_daily_bars_csv",),
        )
    if not source_path.is_file():
        raise ValidationError("daily_bars_csv must reference a local CSV file.")

    csv_result = load_local_daily_bars_csv(
        source_path,
        symbol=checked_config.symbol,
    )
    _validate_csv_result(csv_result)
    return build_etf_sma_backtest_stats_from_bars(
        tuple(_bar_from_local_daily_bar(bar) for bar in csv_result.usable_bars),
        checked_config,
        source_bar_count=csv_result.total_row_count,
    )


def build_etf_sma_backtest_stats_from_bars(
    bars: Iterable[EtfSmaBacktestStatsBar],
    config: EtfSmaBacktestStatsConfig,
    *,
    source_bar_count: int | None = None,
) -> dict[str, object]:
    """Build the SMA posture, lagged exposure path, events, and stats."""

    checked_config = _config(config)
    checked_bars = _bar_tuple(bars)
    source_count = (
        len(checked_bars)
        if source_bar_count is None
        else _non_negative_int(source_bar_count, "source_bar_count")
    )
    if source_count < len(checked_bars):
        raise ValidationError("source_bar_count must cover usable bars.")

    if not checked_bars:
        return _blocked_payload(
            checked_config,
            source_bar_count=source_count,
            backtest_state="blocked_no_usable_bars",
            performance_evidence_state="no_usable_bars",
            blockers=("no_usable_bars",),
        )

    posture_history = _posture_history(
        checked_bars,
        short_window=checked_config.short_window,
        long_window=checked_config.long_window,
    )
    equity_curve, events, path_stats = _equity_curve_and_events(
        checked_bars,
        posture_history,
        starting_equity=checked_config.starting_equity,
        cost_bps=checked_config.cost_bps,
    )
    backtest_state, performance_evidence_state, blockers = _state_fields(
        usable_bar_count=len(checked_bars),
        long_window=checked_config.long_window,
        evaluated_return_count=path_stats["evaluated_return_count"],
    )
    final_posture = str(posture_history[-1]["posture"])
    final_exposure = int(equity_curve[-1]["exposure"])

    payload = _payload(
        checked_config,
        source_bar_count=source_count,
        usable_bar_count=len(checked_bars),
        posture_history=posture_history,
        equity_curve=equity_curve,
        events=events,
        backtest_state=backtest_state,
        performance_evidence_state=performance_evidence_state,
        blockers=blockers,
        insufficient_history_count=sum(
            1 for row in posture_history if row["posture"] == _POSTURE_INSUFFICIENT
        ),
        evaluated_return_count=path_stats["evaluated_return_count"],
        evaluated_start_date=path_stats["evaluated_start_date"],
        evaluated_end_date=path_stats["evaluated_end_date"],
        starting_equity=checked_config.starting_equity,
        ending_equity=path_stats["ending_equity"],
        total_return=path_stats["total_return"],
        max_drawdown=path_stats["max_drawdown"],
        exposure_fraction=path_stats["exposure_fraction"],
        benchmark=checked_config.benchmark,
        benchmark_ending_equity=path_stats["benchmark_ending_equity"],
        benchmark_total_return=path_stats["benchmark_total_return"],
        benchmark_max_drawdown=path_stats["benchmark_max_drawdown"],
        benchmark_equity_curve=path_stats["benchmark_equity_curve"],
        fill_model=checked_config.fill_model,
        cost_bps=checked_config.cost_bps,
        total_cost=path_stats["total_cost"],
        trade_count=path_stats["trade_count"],
        entry_count=path_stats["entry_count"],
        exit_count=path_stats["exit_count"],
        final_exposure=final_exposure,
        final_posture=final_posture,
        final_decision=_final_decision(final_posture, final_exposure),
    )
    return _maybe_with_regime_slice_evidence(payload, checked_config)


def render_etf_sma_backtest_stats_json(payload: Mapping[str, object]) -> str:
    """Return one compact deterministic JSON object."""

    return json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"))


def render_etf_sma_backtest_stats_text(payload: Mapping[str, object]) -> str:
    """Render a compact operator-facing summary."""

    return "\n".join(
        (
            "ETF/SMA offline backtest statistics",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"source_daily_bars_csv: {payload.get('source_daily_bars_csv', '')}",
            f"backtest_state: {payload.get('backtest_state', '')}",
            "performance_evidence_state: "
            f"{payload.get('performance_evidence_state', '')}",
            f"usable_bar_count: {payload.get('usable_bar_count', '')}",
            f"evaluated_return_count: {payload.get('evaluated_return_count', '')}",
            f"starting_equity: {payload.get('starting_equity', '')}",
            f"ending_equity: {payload.get('ending_equity', '')}",
            f"total_return: {payload.get('total_return', '')}",
            f"max_drawdown: {payload.get('max_drawdown', '')}",
            f"data_basis: {payload.get('data_basis', '')}",
            f"fill_model: {payload.get('fill_model', '')}",
            f"cost_bps: {payload.get('cost_bps', '')}",
            f"benchmark: {payload.get('benchmark', '')}",
            f"benchmark_total_return: {payload.get('benchmark_total_return', '')}",
            f"excess_return: {payload.get('excess_return', '')}",
            f"exposure_fraction: {payload.get('exposure_fraction', '')}",
            f"trade_count: {payload.get('trade_count', '')}",
            f"final_posture: {payload.get('final_posture', '')}",
            f"final_exposure: {payload.get('final_exposure', '')}",
            f"final_decision: {payload.get('final_decision', '')}",
            f"profit_claim: {payload.get('profit_claim', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "network_access_attempted: "
            f"{_bool_text(payload.get('network_access_attempted'))}",
            "credential_access_attempted: "
            f"{_bool_text(payload.get('credential_access_attempted'))}",
        )
    )


def write_etf_sma_backtest_stats_jsonl(
    payload: Mapping[str, object],
    output_path: Path | str,
) -> None:
    """Write exactly one JSONL record, replacing any previous file."""

    path = _output_path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_etf_sma_backtest_stats_json(payload))
        stream.write("\n")


def _bar_from_local_daily_bar(bar: LocalDailyBar) -> EtfSmaBacktestStatsBar:
    return EtfSmaBacktestStatsBar(
        date=bar.date,
        adjusted_close=bar.adjusted_close,
        close=bar.close,
    )


def _validate_csv_result(result: object) -> None:
    if not hasattr(result, "input_sorted_by_date"):
        raise ValidationError("daily_bars_csv result is malformed.")
    if result.input_sorted_by_date is not True:
        raise ValidationError("daily_bars_csv rows must be ordered by ascending date.")
    if result.ignored_wrong_symbol_row_count != 0:
        raise ValidationError("daily_bars_csv must contain only SPY rows.")
    if result.ignored_future_bar_count != 0:
        raise ValidationError("daily_bars_csv must contain only usable as-of bars.")
    if result.matching_symbol_row_count == 0:
        raise ValidationError("daily_bars_csv must contain SPY rows.")


def _posture_history(
    bars: tuple[EtfSmaBacktestStatsBar, ...],
    *,
    short_window: int,
    long_window: int,
) -> list[dict[str, object]]:
    history: list[dict[str, object]] = []
    for index, bar in enumerate(bars):
        window = bars[: index + 1]
        short_sma = _sma(window, short_window)
        long_sma = _sma(window, long_window)
        if len(window) < long_window:
            posture = _POSTURE_INSUFFICIENT
        elif short_sma is not None and long_sma is not None and short_sma > long_sma:
            posture = _POSTURE_RISK_ON
        else:
            posture = _POSTURE_RISK_OFF

        history.append(
            {
                "date": bar.date.isoformat(),
                "close": _decimal_text(_bar_price(bar)),
                "adjusted_close": _decimal_text(bar.adjusted_close),
                "short_sma": _optional_decimal_text(short_sma),
                "long_sma": _optional_decimal_text(long_sma),
                "posture": posture,
                "target_exposure": 1 if posture == _POSTURE_RISK_ON else 0,
            }
        )
    return history


def _equity_curve_and_events(
    bars: tuple[EtfSmaBacktestStatsBar, ...],
    posture_history: list[dict[str, object]],
    *,
    starting_equity: Decimal,
    cost_bps: Decimal,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    equity = starting_equity
    peak = starting_equity
    max_drawdown = _ZERO
    cost_rate = cost_bps / Decimal("10000")
    total_cost = _ZERO
    benchmark_equity = starting_equity
    benchmark_peak = starting_equity
    benchmark_max_drawdown = _ZERO
    evaluated_start_date: str | None = None
    evaluated_end_date: str | None = None
    evaluated_return_count = 0
    exposed_return_count = 0
    entry_count = 0
    exit_count = 0
    previous_exposure = 0
    curve: list[dict[str, object]] = []
    benchmark_curve: list[dict[str, object]] = []
    events: list[dict[str, object]] = []

    for index, bar in enumerate(bars):
        current_exposure = (
            0 if index == 0 else int(posture_history[index - 1]["target_exposure"])
        )
        return_available = index > 0
        prior_posture = (
            "" if index == 0 else str(posture_history[index - 1]["posture"])
        )
        asset_return: Decimal | None = None
        strategy_return: Decimal | None = None
        trade_cost = _ZERO
        evaluated_return = False

        if return_available:
            asset_return = (_bar_price(bar) / _bar_price(bars[index - 1])) - _ONE
            strategy_return = _ZERO if current_exposure == 0 else asset_return
            equity *= _ONE + strategy_return
            evaluated_return = prior_posture != _POSTURE_INSUFFICIENT
            if evaluated_return:
                evaluated_return_count += 1
                if current_exposure == 1:
                    exposed_return_count += 1
                if evaluated_start_date is None:
                    evaluated_start_date = bars[index - 1].date.isoformat()
                evaluated_end_date = bar.date.isoformat()
                benchmark_equity *= _ONE + asset_return
                if benchmark_equity > benchmark_peak:
                    benchmark_peak = benchmark_equity
                benchmark_drawdown = (benchmark_equity / benchmark_peak) - _ONE
                if -benchmark_drawdown > benchmark_max_drawdown:
                    benchmark_max_drawdown = -benchmark_drawdown
                benchmark_curve.append(
                    {
                        "date": bar.date.isoformat(),
                        "start_date": bars[index - 1].date.isoformat(),
                        "close": _decimal_text(_bar_price(bar)),
                        "asset_return": _decimal_text(asset_return),
                        "equity": _decimal_text(benchmark_equity),
                        "drawdown": _decimal_text(benchmark_drawdown),
                    }
                )

        action = _event_action(previous_exposure, current_exposure)
        if action == "buy":
            entry_count += 1
        elif action == "sell":
            exit_count += 1
        if action in ("buy", "sell") and cost_rate > _ZERO:
            trade_cost = equity * cost_rate
            equity -= trade_cost
            total_cost += trade_cost

        if equity > peak:
            peak = equity
        drawdown = (equity / peak) - _ONE
        if -drawdown > max_drawdown:
            max_drawdown = -drawdown

        curve.append(
            {
                "date": bar.date.isoformat(),
                "close": _decimal_text(_bar_price(bar)),
                "adjusted_close": _decimal_text(bar.adjusted_close),
                "exposure": current_exposure,
                "asset_return": _optional_decimal_text(asset_return),
                "strategy_return": _optional_decimal_text(strategy_return),
                "trade_cost": _decimal_text(trade_cost),
                "return_available": return_available,
                "evaluated_return": evaluated_return,
                "equity": _decimal_text(equity),
                "drawdown": _decimal_text(drawdown),
            }
        )
        events.append(
            {
                "date": bar.date.isoformat(),
                "action": action,
                "exposure_before": previous_exposure,
                "exposure_after": current_exposure,
                "target_as_of": (
                    None if index == 0 else posture_history[index - 1]["date"]
                ),
                "target_posture": prior_posture,
                "evaluated_return": evaluated_return,
                "fill_model": _FILL_MODEL_NEXT_CLOSE,
                "trade_cost": _decimal_text(trade_cost),
            }
        )
        previous_exposure = current_exposure

    return_interval_count = max(len(bars) - 1, 0)
    exposure_fraction = (
        _ZERO
        if evaluated_return_count == 0
        else Decimal(exposed_return_count) / Decimal(evaluated_return_count)
    )
    return (
        curve,
        events,
        {
            "return_interval_count": return_interval_count,
            "evaluated_return_count": evaluated_return_count,
            "evaluated_start_date": evaluated_start_date,
            "evaluated_end_date": evaluated_end_date,
            "exposed_return_count": exposed_return_count,
            "ending_equity": equity,
            "total_return": (equity / starting_equity) - _ONE,
            "max_drawdown": max_drawdown,
            "exposure_fraction": exposure_fraction,
            "benchmark_ending_equity": benchmark_equity,
            "benchmark_total_return": (
                _ZERO
                if evaluated_return_count == 0
                else (benchmark_equity / starting_equity) - _ONE
            ),
            "benchmark_max_drawdown": benchmark_max_drawdown,
            "benchmark_equity_curve": benchmark_curve,
            "total_cost": total_cost,
            "trade_count": entry_count + exit_count,
            "entry_count": entry_count,
            "exit_count": exit_count,
        },
    )


def _event_action(previous_exposure: int, current_exposure: int) -> str:
    if previous_exposure == 0 and current_exposure == 1:
        return "buy"
    if previous_exposure == 1 and current_exposure == 0:
        return "sell"
    if current_exposure == 1:
        return "hold"
    return "noop"


def _state_fields(
    *,
    usable_bar_count: int,
    long_window: int,
    evaluated_return_count: object,
) -> tuple[str, str, tuple[str, ...]]:
    checked_evaluated_return_count = _non_negative_int(
        evaluated_return_count,
        "evaluated_return_count",
    )
    if usable_bar_count < long_window:
        return (
            "blocked_insufficient_history",
            "insufficient_history",
            ("insufficient_history",),
        )
    if checked_evaluated_return_count == 0:
        return (
            "blocked_insufficient_post_signal_returns",
            "insufficient_post_signal_returns",
            ("insufficient_post_signal_returns",),
        )
    return "completed", "offline_statistics_available", ()


def _payload(
    config: EtfSmaBacktestStatsConfig,
    *,
    source_bar_count: int,
    usable_bar_count: int,
    posture_history: list[dict[str, object]],
    equity_curve: list[dict[str, object]],
    events: list[dict[str, object]],
    backtest_state: str,
    performance_evidence_state: str,
    blockers: tuple[str, ...],
    insufficient_history_count: int,
    evaluated_return_count: object,
    evaluated_start_date: object,
    evaluated_end_date: object,
    starting_equity: Decimal,
    ending_equity: object,
    total_return: object,
    max_drawdown: object,
    exposure_fraction: object,
    benchmark: str,
    benchmark_ending_equity: object,
    benchmark_total_return: object,
    benchmark_max_drawdown: object,
    benchmark_equity_curve: list[dict[str, object]],
    fill_model: str,
    cost_bps: Decimal,
    total_cost: object,
    trade_count: object,
    entry_count: object,
    exit_count: object,
    final_exposure: int,
    final_posture: str,
    final_decision: str,
) -> dict[str, object]:
    strategy_total_return = _decimal_value(total_return, "total_return")
    benchmark_return = _decimal_value(
        benchmark_total_return,
        "benchmark_total_return",
    )
    strategy_max_drawdown = _decimal_value(max_drawdown, "max_drawdown")
    benchmark_drawdown = _decimal_value(
        benchmark_max_drawdown,
        "benchmark_max_drawdown",
    )
    strategy_ending_equity = _decimal_value(ending_equity, "ending_equity")
    benchmark_equity = _decimal_value(
        benchmark_ending_equity,
        "benchmark_ending_equity",
    )
    checked_evaluated_start_date = _optional_string(
        evaluated_start_date,
        "evaluated_start_date",
    )
    checked_evaluated_end_date = _optional_string(
        evaluated_end_date,
        "evaluated_end_date",
    )
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "strategy": _STRATEGY,
        "labels": list(ETF_SMA_BACKTEST_STATS_LABELS),
        "data_basis": _DATA_BASIS,
        "price_field": _PRICE_FIELD,
        "raw_close_price_return_evidence_only": True,
        "source_daily_bars_csv": str(config.daily_bars_csv),
        "source_bar_count": source_bar_count,
        "usable_bar_count": usable_bar_count,
        "short_window": config.short_window,
        "long_window": config.long_window,
        "lookahead_policy": ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY,
        "fill_model": fill_model,
        "benchmark": benchmark,
        "cost_bps": _decimal_text(cost_bps),
        "cost_model": _COST_MODEL,
        "backtest_state": backtest_state,
        "performance_evidence_state": performance_evidence_state,
        "profit_claim": "none",
        "insufficient_history_count": insufficient_history_count,
        "evaluated_return_count": _non_negative_int(
            evaluated_return_count,
            "evaluated_return_count",
        ),
        "evaluated_start_date": checked_evaluated_start_date,
        "evaluated_end_date": checked_evaluated_end_date,
        "strategy_start_date": checked_evaluated_start_date,
        "strategy_end_date": checked_evaluated_end_date,
        "benchmark_start_date": checked_evaluated_start_date,
        "benchmark_end_date": checked_evaluated_end_date,
        "starting_equity": _decimal_text(starting_equity),
        "ending_equity": _decimal_text(strategy_ending_equity),
        "total_return": _decimal_text(strategy_total_return),
        "max_drawdown": _decimal_text(strategy_max_drawdown),
        "strategy_ending_equity": _decimal_text(strategy_ending_equity),
        "strategy_total_return": _decimal_text(strategy_total_return),
        "strategy_max_drawdown": _decimal_text(strategy_max_drawdown),
        "benchmark_ending_equity": _decimal_text(benchmark_equity),
        "benchmark_total_return": _decimal_text(benchmark_return),
        "benchmark_max_drawdown": _decimal_text(benchmark_drawdown),
        "excess_return": _decimal_text(strategy_total_return - benchmark_return),
        "exposure_fraction": _decimal_text(exposure_fraction),
        "total_cost": _decimal_text(total_cost),
        "trade_count": _non_negative_int(trade_count, "trade_count"),
        "entry_count": _non_negative_int(entry_count, "entry_count"),
        "exit_count": _non_negative_int(exit_count, "exit_count"),
        "final_exposure": final_exposure,
        "final_posture": final_posture,
        "final_decision": final_decision,
        "blockers": list(blockers),
        "posture_history": posture_history,
        "equity_curve": equity_curve,
        "benchmark_equity_curve": benchmark_equity_curve,
        "events": events,
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "submit_path_allowed": False,
        "paper_submit_approved": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "credential_access": False,
        "credential_access_attempted": False,
        "broker_network_access": False,
        "network_access_attempted": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "market_data_fetch_performed": False,
        "paper_lab_only": True,
        "research_only": True,
        "signal_evaluation_only": True,
        "not_live_authorized": True,
    }


def _blocked_payload(
    config: EtfSmaBacktestStatsConfig,
    *,
    backtest_state: str,
    performance_evidence_state: str,
    blockers: tuple[str, ...],
    source_bar_count: int = 0,
) -> dict[str, object]:
    payload = _payload(
        config,
        source_bar_count=source_bar_count,
        usable_bar_count=0,
        posture_history=[],
        equity_curve=[],
        events=[],
        backtest_state=backtest_state,
        performance_evidence_state=performance_evidence_state,
        blockers=blockers,
        insufficient_history_count=0,
        evaluated_return_count=0,
        evaluated_start_date=None,
        evaluated_end_date=None,
        starting_equity=config.starting_equity,
        ending_equity=config.starting_equity,
        total_return=_ZERO,
        max_drawdown=_ZERO,
        exposure_fraction=_ZERO,
        benchmark=config.benchmark,
        benchmark_ending_equity=config.starting_equity,
        benchmark_total_return=_ZERO,
        benchmark_max_drawdown=_ZERO,
        benchmark_equity_curve=[],
        fill_model=config.fill_model,
        cost_bps=config.cost_bps,
        total_cost=_ZERO,
        trade_count=0,
        entry_count=0,
        exit_count=0,
        final_exposure=0,
        final_posture=_POSTURE_INSUFFICIENT,
        final_decision=backtest_state,
    )
    return _maybe_with_regime_slice_evidence(payload, config)


def _maybe_with_regime_slice_evidence(
    payload: dict[str, object],
    config: EtfSmaBacktestStatsConfig,
) -> dict[str, object]:
    if config.regime_slices is None:
        return payload
    if config.regime_slices != _REGIME_SLICES_DEFAULT:
        raise ValidationError("regime_slices must be default when provided.")
    return _with_default_regime_slice_evidence(payload, config)


def _with_default_regime_slice_evidence(
    payload: dict[str, object],
    config: EtfSmaBacktestStatsConfig,
) -> dict[str, object]:
    return_rows = _payload_mapping_list(payload, "benchmark_equity_curve")
    equity_rows_by_date = _mapping_rows_by_date(
        _payload_mapping_list(payload, "equity_curve"),
        "equity_curve",
    )
    events = _payload_mapping_list(payload, "events")
    slices: list[dict[str, object]] = []
    omitted: list[dict[str, object]] = []

    for name, requested_start, requested_end in _DEFAULT_REGIME_SLICE_SPECS:
        selected_rows = _selected_regime_return_rows(
            return_rows,
            requested_start=requested_start,
            requested_end=requested_end,
        )
        if not selected_rows:
            omitted.append(
                _omitted_regime_slice(
                    name,
                    requested_start=requested_start,
                    requested_end=requested_end,
                )
            )
            continue
        slices.append(
            _regime_slice_evidence(
                name,
                selected_rows,
                equity_rows_by_date=equity_rows_by_date,
                events=events,
                config=config,
                requested_start=requested_start,
                requested_end=requested_end,
            )
        )

    evidence = dict(payload)
    evidence.update(
        {
            "record_type": _REGIME_SLICE_RECORD_TYPE,
            "schema_version": _SCHEMA_VERSION,
            "milestone": _REGIME_SLICE_MILESTONE,
            "source_input_command_fields": {
                "command": _COMMAND,
                "run_id": config.run_id,
                "symbol": config.symbol,
                "daily_bars_csv": str(config.daily_bars_csv),
                "starting_equity": _decimal_text(config.starting_equity),
                "benchmark": config.benchmark,
                "cost_bps": _decimal_text(config.cost_bps),
                "fill_model": config.fill_model,
                "short_window": config.short_window,
                "long_window": config.long_window,
                "regime_slices": _REGIME_SLICES_DEFAULT,
            },
            "regime_slice_policy": _REGIME_SLICE_POLICY,
            "verdict_scope": _REGIME_SLICE_VERDICT_SCOPE,
            "return_ranking_basis": _RETURN_RANKING_BASIS,
            "regime_slice_count": len(slices),
            "regime_slices": slices,
            "omitted_regime_slices": omitted,
        }
    )
    return evidence


def _selected_regime_return_rows(
    return_rows: list[dict[str, object]],
    *,
    requested_start: date | None,
    requested_end: date | None,
) -> list[dict[str, object]]:
    if requested_start is None and requested_end is None:
        return list(return_rows)
    if requested_start is None or requested_end is None:
        raise ValidationError("regime slice start and end dates must pair.")
    return [
        row
        for row in return_rows
        if requested_start <= _mapping_date(row, "date") <= requested_end
    ]


def _omitted_regime_slice(
    name: str,
    *,
    requested_start: date | None,
    requested_end: date | None,
) -> dict[str, object]:
    reason = (
        "no_evaluated_returns"
        if requested_start is None
        else "no_evaluated_returns_in_requested_window"
    )
    return {
        "slice_name": name,
        "requested_start_date": None
        if requested_start is None
        else requested_start.isoformat(),
        "requested_end_date": None
        if requested_end is None
        else requested_end.isoformat(),
        "reason": reason,
    }


def _regime_slice_evidence(
    name: str,
    return_rows: list[dict[str, object]],
    *,
    equity_rows_by_date: dict[str, dict[str, object]],
    events: list[dict[str, object]],
    config: EtfSmaBacktestStatsConfig,
    requested_start: date | None,
    requested_end: date | None,
) -> dict[str, object]:
    slice_start_date = _mapping_text(return_rows[0], "start_date")
    slice_end_date = _mapping_text(return_rows[-1], "date")
    strategy_path = _normalized_strategy_slice_equity_path(
        return_rows,
        equity_rows_by_date=equity_rows_by_date,
        starting_equity=config.starting_equity,
        cost_bps=config.cost_bps,
    )
    benchmark_path = _normalized_benchmark_slice_equity_path(
        return_rows,
        starting_equity=config.starting_equity,
    )
    strategy_starting_equity = strategy_path[0]
    strategy_ending_equity = strategy_path[-1]
    benchmark_starting_equity = benchmark_path[0]
    benchmark_ending_equity = benchmark_path[-1]
    strategy_total_return = (strategy_ending_equity / strategy_starting_equity) - _ONE
    benchmark_total_return = (benchmark_ending_equity / benchmark_starting_equity) - _ONE
    strategy_max_drawdown = _max_drawdown_from_equity_path(strategy_path)
    benchmark_max_drawdown = _max_drawdown_from_equity_path(benchmark_path)
    strategy_exposure_fraction = _strategy_exposure_fraction(
        return_rows,
        equity_rows_by_date=equity_rows_by_date,
    )
    transition_events = _transition_events_inside_slice(return_rows, events)
    entry_count = sum(1 for event in transition_events if event["action"] == "buy")
    exit_count = sum(1 for event in transition_events if event["action"] == "sell")

    return {
        "slice_name": name,
        "requested_start_date": None
        if requested_start is None
        else requested_start.isoformat(),
        "requested_end_date": None
        if requested_end is None
        else requested_end.isoformat(),
        "slice_start_date": slice_start_date,
        "slice_end_date": slice_end_date,
        "strategy_start_date": slice_start_date,
        "strategy_end_date": slice_end_date,
        "benchmark_start_date": slice_start_date,
        "benchmark_end_date": slice_end_date,
        "evaluated_return_count": len(return_rows),
        "data_basis": _DATA_BASIS,
        "fill_model": config.fill_model,
        "lookahead_policy": ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY,
        "cost_bps": _decimal_text(config.cost_bps),
        "benchmark": config.benchmark,
        "strategy_starting_equity": _decimal_text(strategy_starting_equity),
        "strategy_ending_equity": _decimal_text(strategy_ending_equity),
        "strategy_total_return": _decimal_text(strategy_total_return),
        "benchmark_starting_equity": _decimal_text(benchmark_starting_equity),
        "benchmark_ending_equity": _decimal_text(benchmark_ending_equity),
        "benchmark_total_return": _decimal_text(benchmark_total_return),
        "excess_return": _decimal_text(
            strategy_total_return - benchmark_total_return
        ),
        "strategy_max_drawdown": _decimal_text(strategy_max_drawdown),
        "benchmark_max_drawdown": _decimal_text(benchmark_max_drawdown),
        "drawdown_delta": _decimal_text(
            strategy_max_drawdown - benchmark_max_drawdown
        ),
        "strategy_exposure_fraction": _decimal_text(strategy_exposure_fraction),
        "benchmark_exposure_fraction": _decimal_text(_ONE),
        "entry_count": entry_count,
        "exit_count": exit_count,
        "trade_count": entry_count + exit_count,
        "transition_event_dates": [
            _mapping_text(event, "date") for event in transition_events
        ],
        "transition_events": transition_events,
        "verdict_scope": _REGIME_SLICE_VERDICT_SCOPE,
        "profit_claim": "none",
    }


def _normalized_strategy_slice_equity_path(
    return_rows: list[dict[str, object]],
    *,
    equity_rows_by_date: dict[str, dict[str, object]],
    starting_equity: Decimal,
    cost_bps: Decimal,
) -> list[Decimal]:
    equity = starting_equity
    cost_rate = cost_bps / Decimal("10000")
    path = [equity]
    boundary_row = _mapping_row_for_date(
        equity_rows_by_date,
        _mapping_text(return_rows[0], "start_date"),
        "equity_curve",
    )
    previous_exposure = _mapping_int(boundary_row, "exposure")
    for return_row in return_rows:
        end_row = _mapping_row_for_date(
            equity_rows_by_date,
            _mapping_text(return_row, "date"),
            "equity_curve",
        )
        current_exposure = _mapping_int(end_row, "exposure")
        asset_return = _mapping_decimal(return_row, "asset_return")
        if current_exposure == 1:
            equity *= _ONE + asset_return
        action = _event_action(previous_exposure, current_exposure)
        if action in ("buy", "sell") and cost_rate > _ZERO:
            equity -= equity * cost_rate
        previous_exposure = current_exposure
        path.append(equity)
    return path


def _normalized_benchmark_slice_equity_path(
    return_rows: list[dict[str, object]],
    *,
    starting_equity: Decimal,
) -> list[Decimal]:
    equity = starting_equity
    path = [equity]
    for return_row in return_rows:
        equity *= _ONE + _mapping_decimal(return_row, "asset_return")
        path.append(equity)
    return path


def _max_drawdown_from_equity_path(path: list[Decimal]) -> Decimal:
    if not path:
        raise ValidationError("equity path must contain at least one value.")
    peak = path[0]
    max_drawdown = _ZERO
    for equity in path:
        if equity > peak:
            peak = equity
        drawdown = (equity / peak) - _ONE
        if -drawdown > max_drawdown:
            max_drawdown = -drawdown
    return max_drawdown


def _strategy_exposure_fraction(
    return_rows: list[dict[str, object]],
    *,
    equity_rows_by_date: dict[str, dict[str, object]],
) -> Decimal:
    exposed = sum(
        1
        for return_row in return_rows
        if _mapping_int(
            _mapping_row_for_date(
                equity_rows_by_date,
                _mapping_text(return_row, "date"),
                "equity_curve",
            ),
            "exposure",
        )
        == 1
    )
    return Decimal(exposed) / Decimal(len(return_rows))


def _transition_events_inside_slice(
    return_rows: list[dict[str, object]],
    events: list[dict[str, object]],
) -> list[dict[str, object]]:
    selected_dates = {_mapping_text(row, "date") for row in return_rows}
    transition_events: list[dict[str, object]] = []
    for event in events:
        if _mapping_text(event, "date") not in selected_dates:
            continue
        if _mapping_text(event, "action") not in ("buy", "sell"):
            continue
        transition_events.append(dict(event))
    return transition_events


def _payload_mapping_list(
    payload: Mapping[str, object],
    field_name: str,
) -> list[dict[str, object]]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list.")
    rows: list[dict[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValidationError(f"{field_name}[{index}] must be an object.")
        rows.append(dict(item))
    return rows


def _mapping_rows_by_date(
    rows: list[dict[str, object]],
    field_name: str,
) -> dict[str, dict[str, object]]:
    by_date: dict[str, dict[str, object]] = {}
    for row in rows:
        row_date = _mapping_text(row, "date")
        if row_date in by_date:
            raise ValidationError(f"{field_name} must not contain duplicate dates.")
        by_date[row_date] = row
    return by_date


def _mapping_row_for_date(
    rows_by_date: dict[str, dict[str, object]],
    row_date: str,
    field_name: str,
) -> dict[str, object]:
    try:
        return rows_by_date[row_date]
    except KeyError as exc:
        raise ValidationError(f"{field_name} is missing date {row_date}.") from exc


def _mapping_text(row: Mapping[str, object], field_name: str) -> str:
    value = row.get(field_name)
    if type(value) is not str or value == "":
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _mapping_date(row: Mapping[str, object], field_name: str) -> date:
    text = _mapping_text(row, field_name)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO date.") from exc


def _mapping_decimal(row: Mapping[str, object], field_name: str) -> Decimal:
    return _decimal_value(row.get(field_name), field_name)


def _mapping_int(row: Mapping[str, object], field_name: str) -> int:
    return _non_negative_int(row.get(field_name), field_name)


def _final_decision(final_posture: str, final_exposure: int) -> str:
    target_exposure = 1 if final_posture == _POSTURE_RISK_ON else 0
    if final_posture == _POSTURE_INSUFFICIENT:
        return "insufficient_history"
    if target_exposure == final_exposure:
        return "hold_long" if final_exposure == 1 else "hold_cash"
    if target_exposure > final_exposure:
        return "pending_entry_next_bar"
    return "pending_exit_next_bar"


def _sma(
    bars: tuple[EtfSmaBacktestStatsBar, ...],
    window: int,
) -> Decimal | None:
    if len(bars) < window:
        return None
    return sum((_bar_price(bar) for bar in bars[-window:]), _ZERO) / Decimal(
        window
    )


def _bar_price(bar: EtfSmaBacktestStatsBar) -> Decimal:
    return _positive_decimal(bar.close, "close")


def _config(value: object) -> EtfSmaBacktestStatsConfig:
    if type(value) is not EtfSmaBacktestStatsConfig:
        raise ValidationError("config must be an EtfSmaBacktestStatsConfig.")
    return value


def _bar_tuple(
    bars: Iterable[EtfSmaBacktestStatsBar],
) -> tuple[EtfSmaBacktestStatsBar, ...]:
    try:
        items = tuple(bars)
    except TypeError as exc:
        raise ValidationError(
            "bars must be an iterable of EtfSmaBacktestStatsBar values."
        ) from exc
    previous_date: date | None = None
    seen_dates: set[date] = set()
    for index, bar in enumerate(items):
        if type(bar) is not EtfSmaBacktestStatsBar:
            raise ValidationError(f"bars[{index}] must be an EtfSmaBacktestStatsBar.")
        if bar.date in seen_dates:
            raise ValidationError("bars must not contain duplicate dates.")
        if previous_date is not None and bar.date <= previous_date:
            raise ValidationError("bars must be strictly increasing by date.")
        seen_dates.add(bar.date)
        previous_date = bar.date
    return items


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _choice(value: object, field_name: str, choices: tuple[str, ...]) -> str:
    text = _required_string(value, field_name)
    if text not in choices:
        raise ValidationError(
            f"{field_name} must be one of: {', '.join(choices)}."
        )
    return text


def _optional_choice(
    value: object,
    field_name: str,
    choices: tuple[str, ...],
) -> str | None:
    if value is None:
        return None
    return _choice(value, field_name, choices)


def _spy_symbol(value: object) -> str:
    symbol = _required_string(value, "symbol")
    normalized = symbol.upper()
    if normalized != symbol:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if normalized != _SYMBOL:
        raise ValidationError("M406 etf-sma-backtest-stats supports only SPY.")
    return normalized


def _path_value(value: object, field_name: str) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError(f"{field_name} must be a path.")
    if str(path).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    if isinstance(value, str) and "://" in value:
        raise ValidationError(f"{field_name} must be a local CSV path.")
    if path.suffix.lower() != ".csv":
        raise ValidationError(f"{field_name} must reference a CSV file.")
    return path


def _output_path(value: object) -> Path:
    if type(value) is str:
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValidationError("output_path must be a path.")
    if str(path).strip() == "":
        raise ValidationError("output_path is required.")
    if path.exists() and path.is_dir():
        raise ValidationError("output_path must not be a directory.")
    return path


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a positive integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return decimal_value


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _decimal_value(value, field_name)
    if decimal_value < _ZERO:
        raise ValidationError(f"{field_name} must be greater than or equal to zero.")
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
    return str(_decimal_value(value, "decimal"))


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"
