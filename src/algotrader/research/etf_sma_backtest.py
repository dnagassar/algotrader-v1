"""Deterministic offline SPY ETF/SMA backtest artifact."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from algotrader.errors import ValidationError

__all__ = [
    "ETF_SMA_BACKTEST_LABELS",
    "ETF_SMA_EXECUTION_LAG_CONTRACT",
    "EtfSmaBacktestBar",
    "EtfSmaBacktestConfig",
    "build_etf_sma_backtest",
    "build_etf_sma_backtest_from_csv",
    "render_etf_sma_backtest_json",
    "render_etf_sma_backtest_text",
    "write_etf_sma_backtest_artifact",
]


ETF_SMA_EXECUTION_LAG_CONTRACT = (
    "SMA posture is computed using bars available through as-of date T; "
    "the target position generated from that posture is eligible no earlier "
    "than the next input bar and is modeled at that next bar close."
)
ETF_SMA_BACKTEST_LABELS = (
    "research_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
)
_RECORD_TYPE = "etf_sma_backtest_artifact"
_COMMAND = "etf-sma-backtest"
_ONE = Decimal("1")
_ZERO = Decimal("0")
_POSTURE_INSUFFICIENT = "insufficient_history"
_POSTURE_RISK_ON = "risk_on"
_POSTURE_RISK_OFF = "risk_off"
_POSITION_FLAT = "flat"
_POSITION_LONG = "long"
_ZERO_DECIMAL_TEXT = "0"


@dataclass(frozen=True, slots=True)
class EtfSmaBacktestBar:
    """One local daily close bar for offline SMA research."""

    as_of: str
    close: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "as_of", _iso_date(self.as_of, "as_of"))
        object.__setattr__(self, "close", _positive_decimal(self.close, "close"))


@dataclass(frozen=True, slots=True)
class EtfSmaBacktestConfig:
    """Static parameters for the offline long-only ETF/SMA backtest."""

    run_id: str
    bars_source: str
    symbol: str = "SPY"
    initial_cash: Decimal = Decimal("1000")
    fast_window: int = 50
    slow_window: int = 200

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_string(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "bars_source",
            _required_string(self.bars_source, "bars_source"),
        )
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        object.__setattr__(
            self,
            "initial_cash",
            _positive_decimal(self.initial_cash, "initial_cash"),
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


def build_etf_sma_backtest_from_csv(
    config: EtfSmaBacktestConfig,
) -> dict[str, object]:
    """Load a local CSV and build one deterministic JSON-compatible artifact."""

    checked_config = _config(config)
    source_path = Path(checked_config.bars_source)
    if not source_path.exists():
        return _blocked_payload(
            checked_config,
            bars_input_available=False,
            block_reason="bars_csv_missing",
        )
    if not source_path.is_file():
        return _blocked_payload(
            checked_config,
            bars_input_available=True,
            block_reason="bars_csv_not_file",
        )

    bars = load_etf_sma_backtest_bars_csv(
        source_path,
        symbol=checked_config.symbol,
    )
    return build_etf_sma_backtest(
        bars,
        checked_config,
        bars_input_available=True,
    )


def build_etf_sma_backtest(
    bars: Iterable[EtfSmaBacktestBar],
    config: EtfSmaBacktestConfig,
    *,
    bars_input_available: bool = True,
) -> dict[str, object]:
    """Build the offline SMA posture, equity curve, trades, and stats."""

    checked_config = _config(config)
    checked_bars = _sorted_bars(bars)
    posture_history = _posture_history(
        checked_bars,
        fast_window=checked_config.fast_window,
        slow_window=checked_config.slow_window,
    )
    if not checked_bars:
        return _blocked_payload(
            checked_config,
            bars_input_available=bars_input_available,
            block_reason="no_usable_bars",
        )

    equity_curve, trades = _simulate_equity_curve(
        checked_bars,
        posture_history,
        initial_cash=checked_config.initial_cash,
    )
    stats = _stats(
        checked_bars,
        posture_history,
        equity_curve,
        trades,
        initial_cash=checked_config.initial_cash,
    )
    return _payload(
        checked_config,
        bars_input_available=bars_input_available,
        bar_count=len(checked_bars),
        status="completed",
        blocked=False,
        block_reason="",
        posture_history=posture_history,
        equity_curve=equity_curve,
        trades=trades,
        stats=stats,
    )


def load_etf_sma_backtest_bars_csv(
    path: Path,
    *,
    symbol: str,
) -> tuple[EtfSmaBacktestBar, ...]:
    """Read local daily bars from CSV without fetching market data."""

    checked_symbol = _symbol(symbol)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValidationError("bars_csv must contain a header row.")

        bars: list[EtfSmaBacktestBar] = []
        for row_number, row in enumerate(reader, start=2):
            if _row_symbol(row) not in ("", checked_symbol):
                continue
            bars.append(
                EtfSmaBacktestBar(
                    _row_date(row, row_number),
                    _row_close(row, row_number),
                )
            )

    return tuple(bars)


def write_etf_sma_backtest_artifact(
    payload: Mapping[str, object],
    output_path: str | Path,
) -> None:
    """Write one byte-stable JSONL record, replacing any prior file."""

    path = Path(output_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_etf_sma_backtest_json(payload))
        handle.write("\n")


def render_etf_sma_backtest_json(payload: Mapping[str, object]) -> str:
    """Return a compact deterministic JSON object for the JSONL record."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def render_etf_sma_backtest_text(payload: Mapping[str, object]) -> str:
    """Return a compact operator-readable summary of the offline artifact."""

    stats = _mapping(payload.get("stats"))
    return "\n".join(
        (
            "ETF/SMA offline backtest",
            f"status: {payload.get('status', '')}",
            f"run_id: {payload.get('run_id', '')}",
            f"symbol: {payload.get('symbol', '')}",
            f"bars_source: {payload.get('bars_source', '')}",
            f"bars_input_available: {_bool_text(payload.get('bars_input_available'))}",
            f"bar_count: {payload.get('bar_count', 0)}",
            f"final_portfolio_value: {stats.get('final_portfolio_value', '')}",
            f"total_return: {stats.get('total_return', '')}",
            f"max_drawdown: {stats.get('max_drawdown', '')}",
            f"trade_count: {stats.get('trade_count', 0)}",
            f"final_position_state: {stats.get('final_position_state', '')}",
            f"submitted: {_bool_text(payload.get('submitted'))}",
            f"mutated: {_bool_text(payload.get('mutated'))}",
            "broker_action_performed: "
            f"{_bool_text(payload.get('broker_action_performed'))}",
        )
    )


def _simulate_equity_curve(
    bars: tuple[EtfSmaBacktestBar, ...],
    posture_history: list[dict[str, object]],
    *,
    initial_cash: Decimal,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    cash = initial_cash
    quantity = _ZERO
    peak = initial_cash
    curve: list[dict[str, object]] = []
    trades: list[dict[str, object]] = []

    for index, bar in enumerate(bars):
        portfolio_value_override: Decimal | None = None
        prior_posture = (
            str(posture_history[index - 1]["posture"]) if index > 0 else None
        )
        previous_prior_posture = (
            str(posture_history[index - 2]["posture"]) if index > 1 else None
        )
        if prior_posture == _POSTURE_RISK_ON and quantity == _ZERO:
            cash_before = cash
            quantity = cash_before / bar.close
            cash = _ZERO
            portfolio_value_override = cash_before
            trades.append(
                _trade(
                    bar,
                    action="buy",
                    reason=_entry_reason(previous_prior_posture),
                    target_as_of=str(posture_history[index - 1]["as_of"]),
                    modeled_fill_price=bar.close,
                    quantity=quantity,
                    notional=cash_before,
                    cash_after=cash,
                    portfolio_value_after=cash_before,
                )
            )
        elif prior_posture == _POSTURE_RISK_OFF and quantity > _ZERO:
            sell_notional = quantity * bar.close
            cash += quantity * bar.close
            sold_quantity = quantity
            quantity = _ZERO
            trades.append(
                _trade(
                    bar,
                    action="sell",
                    reason=_exit_reason(previous_prior_posture),
                    target_as_of=str(posture_history[index - 1]["as_of"]),
                    modeled_fill_price=bar.close,
                    quantity=sold_quantity,
                    notional=sell_notional,
                    cash_after=cash,
                    portfolio_value_after=cash,
                )
            )

        portfolio_value = (
            portfolio_value_override
            if portfolio_value_override is not None
            else cash + (quantity * bar.close)
        )
        if portfolio_value > peak:
            peak = portfolio_value
        drawdown = (portfolio_value / peak) - _ONE
        curve.append(
            {
                "as_of": bar.as_of,
                "date": bar.as_of,
                "cash": _decimal_text(cash),
                "position_quantity": _decimal_text(quantity),
                "position_state": (
                    _POSITION_LONG if quantity > _ZERO else _POSITION_FLAT
                ),
                "exposed": quantity > _ZERO,
                "close": _decimal_text(bar.close),
                "portfolio_value": _decimal_text(portfolio_value),
                "drawdown": _decimal_text(drawdown),
            }
        )

    return curve, trades


def _posture_history(
    bars: tuple[EtfSmaBacktestBar, ...],
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
                "as_of": bar.as_of,
                "date": bar.as_of,
                "close": _decimal_text(bar.close),
                "sma_fast": _optional_decimal_text(sma_fast),
                "sma_slow": _optional_decimal_text(sma_slow),
                "posture": posture,
            }
        )

    return rows


def _stats(
    bars: tuple[EtfSmaBacktestBar, ...],
    posture_history: list[dict[str, object]],
    equity_curve: list[dict[str, object]],
    trades: list[dict[str, object]],
    *,
    initial_cash: Decimal,
) -> dict[str, object]:
    final_point = equity_curve[-1]
    final_portfolio_value = Decimal(str(final_point["portfolio_value"]))
    max_drawdown = max(
        (abs(Decimal(str(point["drawdown"]))) for point in equity_curve),
        default=_ZERO,
    )
    exposure_days = sum(1 for point in equity_curve if point["exposed"] is True)
    trade_count = len(trades)
    buy_count = sum(1 for trade in trades if trade["action"] == "buy")
    sell_count = sum(1 for trade in trades if trade["action"] == "sell")
    insufficient_history_days = sum(
        1
        for row in posture_history
        if row["posture"] == _POSTURE_INSUFFICIENT
    )
    return {
        "start_date": bars[0].as_of,
        "end_date": bars[-1].as_of,
        "total_return": _decimal_text((final_portfolio_value / initial_cash) - _ONE),
        "max_drawdown": _decimal_text(max_drawdown),
        "trade_count": trade_count,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "final_portfolio_value": _decimal_text(final_portfolio_value),
        "final_position_state": str(final_point["position_state"]),
        "exposure_days": exposure_days,
        "exposure_fraction": _decimal_text(
            Decimal(exposure_days) / Decimal(len(equity_curve))
        ),
        "insufficient_history_days": insufficient_history_days,
        "commission": _ZERO_DECIMAL_TEXT,
        "commission_model": "zero",
        "slippage": _ZERO_DECIMAL_TEXT,
        "slippage_model": "zero",
    }


def _blocked_payload(
    config: EtfSmaBacktestConfig,
    *,
    bars_input_available: bool,
    block_reason: str,
) -> dict[str, object]:
    stats = {
        "start_date": None,
        "end_date": None,
        "total_return": _ZERO_DECIMAL_TEXT,
        "max_drawdown": _ZERO_DECIMAL_TEXT,
        "trade_count": 0,
        "buy_count": 0,
        "sell_count": 0,
        "final_portfolio_value": _decimal_text(config.initial_cash),
        "final_position_state": _POSITION_FLAT,
        "exposure_days": 0,
        "exposure_fraction": _ZERO_DECIMAL_TEXT,
        "insufficient_history_days": 0,
        "commission": _ZERO_DECIMAL_TEXT,
        "commission_model": "zero",
        "slippage": _ZERO_DECIMAL_TEXT,
        "slippage_model": "zero",
    }
    return _payload(
        config,
        bars_input_available=bars_input_available,
        bar_count=0,
        status="blocked",
        blocked=True,
        block_reason=block_reason,
        posture_history=[],
        equity_curve=[],
        trades=[],
        stats=stats,
    )


def _payload(
    config: EtfSmaBacktestConfig,
    *,
    bars_input_available: bool,
    bar_count: int,
    status: str,
    blocked: bool,
    block_reason: str,
    posture_history: list[dict[str, object]],
    equity_curve: list[dict[str, object]],
    trades: list[dict[str, object]],
    stats: dict[str, object],
) -> dict[str, object]:
    return {
        "record_type": _RECORD_TYPE,
        "command": _COMMAND,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "bars_source": config.bars_source,
        "bars_input_available": bool(bars_input_available),
        "bar_count": bar_count,
        "fast_window": config.fast_window,
        "slow_window": config.slow_window,
        "initial_cash": _decimal_text(config.initial_cash),
        "execution_lag_contract": ETF_SMA_EXECUTION_LAG_CONTRACT,
        "execution_lag_bars": 1,
        "status": status,
        "blocked": blocked,
        "block_reason": block_reason,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
        "market_data_fetch_performed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": list(ETF_SMA_BACKTEST_LABELS),
        "posture_history": posture_history,
        "equity_curve": equity_curve,
        "trades": trades,
        "stats": stats,
    }


def _trade(
    bar: EtfSmaBacktestBar,
    *,
    action: str,
    reason: str,
    target_as_of: str,
    modeled_fill_price: Decimal,
    quantity: Decimal,
    notional: Decimal,
    cash_after: Decimal,
    portfolio_value_after: Decimal,
) -> dict[str, object]:
    return {
        "as_of": bar.as_of,
        "date": bar.as_of,
        "action": action,
        "reason": reason,
        "target_as_of": target_as_of,
        "modeled_fill_price": _decimal_text(modeled_fill_price),
        "quantity": _decimal_text(quantity),
        "notional": _decimal_text(notional),
        "cash_after": _decimal_text(cash_after),
        "portfolio_value_after": _decimal_text(portfolio_value_after),
    }


def _entry_reason(previous_prior_posture: str | None) -> str:
    if previous_prior_posture == _POSTURE_RISK_OFF:
        return "risk_off_to_risk_on"
    if previous_prior_posture == _POSTURE_INSUFFICIENT:
        return "insufficient_history_to_risk_on"
    return "target_risk_on_from_prior_as_of"


def _exit_reason(previous_prior_posture: str | None) -> str:
    if previous_prior_posture == _POSTURE_RISK_ON:
        return "risk_on_to_risk_off"
    return "target_risk_off_from_prior_as_of"


def _sma(
    bars: tuple[EtfSmaBacktestBar, ...],
    window: int,
) -> Decimal | None:
    if len(bars) < window:
        return None
    return sum((bar.close for bar in bars[-window:]), _ZERO) / Decimal(window)


def _row_symbol(row: Mapping[str, str],) -> str:
    for key in ("symbol", "ticker"):
        value = row.get(key)
        if value is not None:
            return value.strip().upper()
    return ""


def _row_date(row: Mapping[str, str], row_number: int) -> str:
    for key in ("date", "as_of", "timestamp"):
        value = row.get(key)
        if value is not None and value.strip():
            return _iso_date(value.strip()[:10], f"row {row_number} {key}")
    raise ValidationError(f"row {row_number} must contain date/as_of/timestamp.")


def _row_close(row: Mapping[str, str], row_number: int) -> Decimal:
    for key in ("close", "adjusted_close", "adj_close"):
        value = row.get(key)
        if value is not None and value.strip():
            try:
                return _positive_decimal(Decimal(value.strip()), f"row {row_number} {key}")
            except InvalidOperation as exc:
                raise ValidationError(f"row {row_number} {key} must be a decimal.") from exc
    raise ValidationError(f"row {row_number} must contain close/adjusted_close.")


def _sorted_bars(
    values: Iterable[EtfSmaBacktestBar],
) -> tuple[EtfSmaBacktestBar, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError("bars must be an iterable of EtfSmaBacktestBar values.")
    try:
        bars = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "bars must be an iterable of EtfSmaBacktestBar values."
        ) from exc

    seen_dates: set[str] = set()
    for index, bar in enumerate(bars):
        if type(bar) is not EtfSmaBacktestBar:
            raise ValidationError(f"bars[{index}] must be an EtfSmaBacktestBar.")
        if bar.as_of in seen_dates:
            raise ValidationError("bars must not contain duplicate dates.")
        seen_dates.add(bar.as_of)
    return tuple(sorted(bars, key=lambda bar: bar.as_of))


def _config(value: object) -> EtfSmaBacktestConfig:
    if type(value) is not EtfSmaBacktestConfig:
        raise ValidationError("config must be an EtfSmaBacktestConfig.")
    return value


def _iso_date(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be an ISO YYYY-MM-DD date string.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO YYYY-MM-DD date string."
        ) from exc
    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value


def _symbol(value: object) -> str:
    symbol = _required_string(value, "symbol").upper()
    if symbol != value:
        raise ValidationError("symbol must use uppercase deterministic text.")
    if any(character.isspace() for character in symbol):
        raise ValidationError("symbol must not contain whitespace.")
    return symbol


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 1:
        raise ValidationError(f"{field_name} must be at least 1.")
    return value


def _finite_decimal(value: object, field_name: str) -> Decimal:
    if type(value) is not Decimal:
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return value


def _positive_decimal(value: object, field_name: str) -> Decimal:
    decimal_value = _finite_decimal(value, field_name)
    if decimal_value <= _ZERO:
        raise ValidationError(f"{field_name} must be positive.")
    return decimal_value


def _decimal_text(value: Decimal) -> str:
    return str(_finite_decimal(value, "decimal"))


def _optional_decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
