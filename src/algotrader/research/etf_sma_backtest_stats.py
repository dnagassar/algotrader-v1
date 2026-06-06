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
    """One validated local daily adjusted-close observation."""

    date: date
    adjusted_close: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", _plain_date(self.date, "date"))
        object.__setattr__(
            self,
            "adjusted_close",
            _positive_decimal(self.adjusted_close, "adjusted_close"),
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
    )
    backtest_state, performance_evidence_state, blockers = _state_fields(
        usable_bar_count=len(checked_bars),
        long_window=checked_config.long_window,
        evaluated_return_count=path_stats["evaluated_return_count"],
    )
    final_posture = str(posture_history[-1]["posture"])
    final_exposure = int(equity_curve[-1]["exposure"])

    return _payload(
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
        starting_equity=checked_config.starting_equity,
        ending_equity=path_stats["ending_equity"],
        total_return=path_stats["total_return"],
        max_drawdown=path_stats["max_drawdown"],
        exposure_fraction=path_stats["exposure_fraction"],
        trade_count=path_stats["trade_count"],
        entry_count=path_stats["entry_count"],
        exit_count=path_stats["exit_count"],
        final_exposure=final_exposure,
        final_posture=final_posture,
        final_decision=_final_decision(final_posture, final_exposure),
    )


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
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    equity = starting_equity
    peak = starting_equity
    max_drawdown = _ZERO
    evaluated_return_count = 0
    exposed_return_count = 0
    entry_count = 0
    exit_count = 0
    previous_exposure = 0
    curve: list[dict[str, object]] = []
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
        evaluated_return = False

        if return_available:
            asset_return = (bar.adjusted_close / bars[index - 1].adjusted_close) - _ONE
            strategy_return = _ZERO if current_exposure == 0 else asset_return
            equity *= _ONE + strategy_return
            evaluated_return = prior_posture != _POSTURE_INSUFFICIENT
            if evaluated_return:
                evaluated_return_count += 1
                if current_exposure == 1:
                    exposed_return_count += 1

        if equity > peak:
            peak = equity
        drawdown = (equity / peak) - _ONE
        if -drawdown > max_drawdown:
            max_drawdown = -drawdown

        action = _event_action(previous_exposure, current_exposure)
        if action == "buy":
            entry_count += 1
        elif action == "sell":
            exit_count += 1

        curve.append(
            {
                "date": bar.date.isoformat(),
                "adjusted_close": _decimal_text(bar.adjusted_close),
                "exposure": current_exposure,
                "asset_return": _optional_decimal_text(asset_return),
                "strategy_return": _optional_decimal_text(strategy_return),
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
            "exposed_return_count": exposed_return_count,
            "ending_equity": equity,
            "total_return": (equity / starting_equity) - _ONE,
            "max_drawdown": max_drawdown,
            "exposure_fraction": exposure_fraction,
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
    starting_equity: Decimal,
    ending_equity: object,
    total_return: object,
    max_drawdown: object,
    exposure_fraction: object,
    trade_count: object,
    entry_count: object,
    exit_count: object,
    final_exposure: int,
    final_posture: str,
    final_decision: str,
) -> dict[str, object]:
    return {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "strategy": _STRATEGY,
        "labels": list(ETF_SMA_BACKTEST_STATS_LABELS),
        "source_daily_bars_csv": str(config.daily_bars_csv),
        "source_bar_count": source_bar_count,
        "usable_bar_count": usable_bar_count,
        "short_window": config.short_window,
        "long_window": config.long_window,
        "lookahead_policy": ETF_SMA_BACKTEST_STATS_LOOKAHEAD_POLICY,
        "backtest_state": backtest_state,
        "performance_evidence_state": performance_evidence_state,
        "profit_claim": "none",
        "insufficient_history_count": insufficient_history_count,
        "evaluated_return_count": _non_negative_int(
            evaluated_return_count,
            "evaluated_return_count",
        ),
        "starting_equity": _decimal_text(starting_equity),
        "ending_equity": _decimal_text(ending_equity),
        "total_return": _decimal_text(total_return),
        "max_drawdown": _decimal_text(max_drawdown),
        "exposure_fraction": _decimal_text(exposure_fraction),
        "trade_count": _non_negative_int(trade_count, "trade_count"),
        "entry_count": _non_negative_int(entry_count, "entry_count"),
        "exit_count": _non_negative_int(exit_count, "exit_count"),
        "final_exposure": final_exposure,
        "final_posture": final_posture,
        "final_decision": final_decision,
        "blockers": list(blockers),
        "posture_history": posture_history,
        "equity_curve": equity_curve,
        "events": events,
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "paper_submit_approved": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "credential_access_attempted": False,
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
    return _payload(
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
        starting_equity=config.starting_equity,
        ending_equity=config.starting_equity,
        total_return=_ZERO,
        max_drawdown=_ZERO,
        exposure_fraction=_ZERO,
        trade_count=0,
        entry_count=0,
        exit_count=0,
        final_exposure=0,
        final_posture=_POSTURE_INSUFFICIENT,
        final_decision=backtest_state,
    )


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
    return sum((bar.adjusted_close for bar in bars[-window:]), _ZERO) / Decimal(
        window
    )


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
