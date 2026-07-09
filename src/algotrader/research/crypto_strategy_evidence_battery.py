"""Deterministic no-submit crypto strategy evidence battery.

The battery is intentionally small and research-only. It evaluates simple
long-or-flat crypto candidates against cash, buy-and-hold, and an optional
equal-weight basket benchmark without importing broker, execution, network, or
LLM dependencies.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from algotrader.errors import ValidationError

CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION = (
    "v5_19_crypto_strategy_evidence_battery_v1"
)
DEFAULT_CRYPTO_EVIDENCE_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD")

NO_SUBMIT_SAFETY_FIELDS = (
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "broker_read_occurred",
    "broker_mutation_occurred",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_endpoint_touched",
    "credential_values_exposed",
    "network_access_attempted",
)

REQUIRED_NO_SUBMIT_LABELS = (
    "crypto_strategy_evidence_battery",
    "research_only",
    "paper_lab_only",
    "no_submit",
    "no_broker_read",
    "no_broker_mutation",
    "not_live_authorized",
    "profit_claim=none",
)

__all__ = [
    "CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION",
    "DEFAULT_CRYPTO_EVIDENCE_SYMBOLS",
    "NO_SUBMIT_SAFETY_FIELDS",
    "REQUIRED_NO_SUBMIT_LABELS",
    "CryptoEvidenceAssumptions",
    "CryptoEvidenceBar",
    "run_crypto_strategy_evidence_battery",
    "validate_crypto_strategy_no_submit_packet",
]

_ZERO = Decimal("0")
_ONE = Decimal("1")
_BPS_DENOMINATOR = Decimal("10000")
_DECIMAL_QUANTUM = Decimal("0.00000001")


@dataclass(frozen=True, slots=True)
class CryptoEvidenceBar:
    """One immutable local crypto close observation."""

    symbol: str
    timestamp: datetime
    close: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _crypto_symbol(self.symbol, "symbol"))
        object.__setattr__(
            self,
            "timestamp",
            _aware_utc_datetime(self.timestamp, "timestamp"),
        )
        object.__setattr__(self, "close", _positive_decimal(self.close, "close"))


@dataclass(frozen=True, slots=True)
class CryptoEvidenceAssumptions:
    """Deterministic assumptions for candidate evidence and promotion gates."""

    initial_equity: Decimal = Decimal("1000")
    fee_bps: Decimal = Decimal("10")
    slippage_bps: Decimal = Decimal("15")
    min_bars_per_symbol: int = 16
    train_fraction_numerator: int = 3
    train_fraction_denominator: int = 5
    max_test_drawdown: Decimal = Decimal("0.25")
    min_test_excess_return_vs_buy_hold: Decimal = Decimal("0")
    min_test_total_return: Decimal = Decimal("0")
    paper_max_notional: Decimal = Decimal("25")
    max_paper_allocation_fraction: Decimal = Decimal("0.01")
    candidate_symbols: tuple[str, ...] = DEFAULT_CRYPTO_EVIDENCE_SYMBOLS

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "initial_equity",
            _positive_decimal(self.initial_equity, "initial_equity"),
        )
        object.__setattr__(self, "fee_bps", _non_negative_decimal(self.fee_bps, "fee_bps"))
        object.__setattr__(
            self,
            "slippage_bps",
            _non_negative_decimal(self.slippage_bps, "slippage_bps"),
        )
        object.__setattr__(
            self,
            "min_bars_per_symbol",
            _positive_int(self.min_bars_per_symbol, "min_bars_per_symbol"),
        )
        object.__setattr__(
            self,
            "train_fraction_numerator",
            _positive_int(self.train_fraction_numerator, "train_fraction_numerator"),
        )
        object.__setattr__(
            self,
            "train_fraction_denominator",
            _positive_int(
                self.train_fraction_denominator,
                "train_fraction_denominator",
            ),
        )
        if self.train_fraction_numerator >= self.train_fraction_denominator:
            raise ValidationError(
                "train_fraction_numerator must be smaller than train_fraction_denominator."
            )
        object.__setattr__(
            self,
            "max_test_drawdown",
            _non_negative_decimal(self.max_test_drawdown, "max_test_drawdown"),
        )
        object.__setattr__(
            self,
            "min_test_excess_return_vs_buy_hold",
            _finite_decimal(
                self.min_test_excess_return_vs_buy_hold,
                "min_test_excess_return_vs_buy_hold",
            ),
        )
        object.__setattr__(
            self,
            "min_test_total_return",
            _finite_decimal(self.min_test_total_return, "min_test_total_return"),
        )
        object.__setattr__(
            self,
            "paper_max_notional",
            _positive_decimal(self.paper_max_notional, "paper_max_notional"),
        )
        object.__setattr__(
            self,
            "max_paper_allocation_fraction",
            _positive_decimal(
                self.max_paper_allocation_fraction,
                "max_paper_allocation_fraction",
            ),
        )
        if self.max_paper_allocation_fraction > _ONE:
            raise ValidationError("max_paper_allocation_fraction must be <= 1.")
        object.__setattr__(
            self,
            "candidate_symbols",
            _candidate_symbol_tuple(self.candidate_symbols),
        )


@dataclass(frozen=True, slots=True)
class _StrategySpec:
    strategy_id: str
    strategy_family: str
    lookback: int = 0
    fast_window: int = 0
    slow_window: int = 0
    volatility_threshold: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class _EvidencePoint:
    timestamp: datetime
    target_exposure: Decimal
    applied_exposure: Decimal
    asset_return: Decimal
    transaction_cost: Decimal
    strategy_return_after_costs: Decimal
    equity: Decimal
    turnover_delta: Decimal


def run_crypto_strategy_evidence_battery(
    bars: Iterable[CryptoEvidenceBar],
    *,
    as_of: datetime | str,
    data_source: str,
    data_freshness: str,
    assumptions: CryptoEvidenceAssumptions | None = None,
) -> dict[str, object]:
    """Rank simple crypto strategies and return a no-submit decision packet."""

    checked_assumptions = assumptions or CryptoEvidenceAssumptions()
    checked_bars = _bar_tuple(bars)
    bars_by_symbol = _bars_by_symbol(checked_bars)
    as_of_text = _as_of_text(as_of)
    data_source_text = _required_text(data_source, "data_source")
    data_freshness_text = _required_text(data_freshness, "data_freshness")

    symbol_summaries = [
        _symbol_data_summary(
            symbol,
            bars_by_symbol.get(symbol, ()),
            checked_assumptions,
        )
        for symbol in checked_assumptions.candidate_symbols
    ]
    benchmark_records = _benchmark_records(bars_by_symbol, checked_assumptions)
    buy_hold_by_symbol = {
        str(record["symbol"]): record
        for record in benchmark_records
        if record.get("benchmark_id") == "buy_and_hold"
    }
    basket_record = _first_benchmark(benchmark_records, "equal_weight_crypto_basket")

    strategy_specs = _strategy_specs()
    evaluations: list[dict[str, object]] = []
    for symbol in checked_assumptions.candidate_symbols:
        symbol_bars = bars_by_symbol.get(symbol, ())
        for spec in strategy_specs:
            evaluations.append(
                _candidate_evaluation(
                    symbol=symbol,
                    spec=spec,
                    bars=symbol_bars,
                    assumptions=checked_assumptions,
                    buy_hold_record=buy_hold_by_symbol.get(symbol, {}),
                    basket_record=basket_record,
                )
            )

    ranked_evaluations = _ranked_evaluations(evaluations)
    selected_candidate = _selected_candidate(ranked_evaluations)
    no_submit_decision = _packet_decision(ranked_evaluations, selected_candidate)
    rejection_reasons = _packet_rejection_reasons(
        ranked_evaluations,
        selected_candidate,
    )

    packet: dict[str, object] = {
        "schema_version": CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
        "record_type": "crypto_strategy_evidence_battery_packet",
        "as_of": as_of_text,
        "candidate_symbols": list(checked_assumptions.candidate_symbols),
        "strategy_candidates": [
            _strategy_spec_payload(spec) for spec in strategy_specs
        ],
        "data_source": data_source_text,
        "data_freshness": data_freshness_text,
        "data_summary": symbol_summaries,
        "walk_forward_windows": _walk_forward_windows(
            bars_by_symbol,
            checked_assumptions,
        ),
        "benchmark_comparison": {
            "benchmarks": benchmark_records,
            "cash_no_trade_return": "0",
            "equal_weight_crypto_basket_available": bool(basket_record),
        },
        "evidence_table": _evidence_table(ranked_evaluations),
        "candidate_evaluations": ranked_evaluations,
        "selected_candidate": selected_candidate,
        "rejection_reasons": rejection_reasons,
        "no_submit_decision": no_submit_decision,
        "risk_constraints": {
            "asset_class": "crypto",
            "direction": "long_only_or_cash",
            "shorting_allowed": False,
            "leverage_allowed": False,
            "max_test_drawdown_allowed": _decimal_text(
                checked_assumptions.max_test_drawdown
            ),
            "must_outperform_symbol_buy_hold_oos": True,
            "must_outperform_cash_oos": True,
            "paper_only": True,
            "fresh_operator_approval_required_for_any_broker_facing_step": True,
        },
        "max_allocation_proposal_for_paper_only": {
            "paper_only": True,
            "max_notional_usd": _decimal_text(checked_assumptions.paper_max_notional),
            "max_account_fraction": _decimal_text(
                checked_assumptions.max_paper_allocation_fraction
            ),
            "requires_separate_operator_approval": True,
            "applies_only_after_no_submit_plan_review": True,
        },
        "next_safe_operator_action": _next_safe_operator_action(no_submit_decision),
        "labels": list(REQUIRED_NO_SUBMIT_LABELS),
        "profit_claim": "none",
        **_false_safety_flags(),
    }
    validation_errors = validate_crypto_strategy_no_submit_packet(packet)
    packet["validation_status"] = "passed" if not validation_errors else "failed"
    packet["validation_errors"] = validation_errors
    return packet


def validate_crypto_strategy_no_submit_packet(
    packet: Mapping[str, object],
) -> list[str]:
    """Return no-submit packet validation errors without side effects."""

    errors: list[str] = []
    for field_name in NO_SUBMIT_SAFETY_FIELDS:
        if packet.get(field_name) is not False:
            errors.append(f"{field_name}_must_be_false")

    labels = set(_string_sequence(packet.get("labels")))
    missing_labels = tuple(
        label for label in REQUIRED_NO_SUBMIT_LABELS if label not in labels
    )
    if missing_labels:
        errors.append("required_no_submit_labels_missing")

    next_action = str(packet.get("next_safe_operator_action", "")).lower()
    forbidden_phrases = (
        "submit order",
        "place order",
        "send order",
        "cancel order",
        "replace order",
        "close position",
        "liquidate",
        "mutate broker",
        "broker mutation is authorized",
    )
    if any(phrase in next_action for phrase in forbidden_phrases):
        errors.append("next_safe_operator_action_contains_broker_mutation_instruction")
    return errors


def _candidate_evaluation(
    *,
    symbol: str,
    spec: _StrategySpec,
    bars: tuple[CryptoEvidenceBar, ...],
    assumptions: CryptoEvidenceAssumptions,
    buy_hold_record: Mapping[str, object],
    basket_record: Mapping[str, object],
) -> dict[str, object]:
    candidate_id = f"crypto:{symbol}:{spec.strategy_id}"
    if len(bars) < assumptions.min_bars_per_symbol:
        return _insufficient_candidate_record(
            candidate_id=candidate_id,
            symbol=symbol,
            spec=spec,
            observed_bars=len(bars),
            required_bars=assumptions.min_bars_per_symbol,
        )

    split_index = _split_index(len(bars), assumptions)
    if split_index <= 0 or split_index >= len(bars):
        return _insufficient_candidate_record(
            candidate_id=candidate_id,
            symbol=symbol,
            spec=spec,
            observed_bars=len(bars),
            required_bars=assumptions.min_bars_per_symbol,
        )

    exposures = _strategy_exposures(bars, spec)
    points = _evidence_points(
        bars=bars,
        asset_returns=_asset_returns_from_bars(bars),
        target_exposures=exposures,
        assumptions=assumptions,
    )
    full_metrics = _metrics(points, assumptions.initial_equity)
    train_metrics = _metrics(points[:split_index], assumptions.initial_equity)
    test_metrics = _metrics(points[split_index:], assumptions.initial_equity)

    buy_hold_test_metrics = _mapping(
        _mapping(buy_hold_record.get("windows")).get("test")
    )
    buy_hold_test_return = _decimal_from_text(
        buy_hold_test_metrics.get("total_return", "0")
    )
    basket_test_return = _basket_test_return(basket_record)
    test_excess_return = (
        _decimal_from_text(test_metrics["total_return"]) - buy_hold_test_return
    )
    decision, reasons = _candidate_decision(
        test_metrics=test_metrics,
        test_excess_return=test_excess_return,
        assumptions=assumptions,
    )

    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "strategy_id": spec.strategy_id,
        "strategy_family": spec.strategy_family,
        "parameters": _strategy_parameters(spec),
        "candidate_decision": decision,
        "rejection_reasons": list(reasons),
        "windows": {
            "full": full_metrics,
            "train": train_metrics,
            "test": test_metrics,
        },
        "benchmark_comparison": {
            "buy_and_hold_test_total_return": _decimal_text(buy_hold_test_return),
            "cash_no_trade_test_total_return": "0",
            "equal_weight_basket_test_total_return": _decimal_text(
                basket_test_return
            )
            if basket_test_return is not None
            else "",
            "test_excess_return_vs_buy_hold": _decimal_text(test_excess_return),
        },
    }


def _candidate_decision(
    *,
    test_metrics: Mapping[str, object],
    test_excess_return: Decimal,
    assumptions: CryptoEvidenceAssumptions,
) -> tuple[str, tuple[str, ...]]:
    test_total_return = _decimal_from_text(test_metrics.get("total_return", "0"))
    test_max_drawdown = _decimal_from_text(test_metrics.get("max_drawdown", "0"))
    reasons: list[str] = []

    if test_max_drawdown > assumptions.max_test_drawdown:
        reasons.append("high_drawdown")
    if test_excess_return <= assumptions.min_test_excess_return_vs_buy_hold:
        reasons.append("benchmark_underperformance")
    if test_total_return <= assumptions.min_test_total_return:
        reasons.append("cash_underperformance")

    if reasons:
        return "reject_candidate", tuple(reasons)
    return "promote_to_no_submit_plan", ()


def _benchmark_records(
    bars_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]],
    assumptions: CryptoEvidenceAssumptions,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = [
        {
            "benchmark_id": "cash_no_trade",
            "symbol": "CASH",
            "benchmark_type": "cash",
            "windows": {
                "full": _zero_metrics(),
                "train": _zero_metrics(),
                "test": _zero_metrics(),
            },
            "status": "available",
        }
    ]
    for symbol in assumptions.candidate_symbols:
        bars = bars_by_symbol.get(symbol, ())
        if len(bars) < assumptions.min_bars_per_symbol:
            records.append(
                {
                    "benchmark_id": "buy_and_hold",
                    "symbol": symbol,
                    "benchmark_type": "symbol_buy_and_hold",
                    "status": "insufficient_data",
                    "observed_bars": len(bars),
                    "required_bars": assumptions.min_bars_per_symbol,
                    "windows": {},
                }
            )
            continue
        split_index = _split_index(len(bars), assumptions)
        points = _evidence_points(
            bars=bars,
            asset_returns=_asset_returns_from_bars(bars),
            target_exposures=tuple(_ONE for _ in bars),
            assumptions=assumptions,
        )
        records.append(
            {
                "benchmark_id": "buy_and_hold",
                "symbol": symbol,
                "benchmark_type": "symbol_buy_and_hold",
                "status": "available",
                "windows": {
                    "full": _metrics(points, assumptions.initial_equity),
                    "train": _metrics(points[:split_index], assumptions.initial_equity),
                    "test": _metrics(points[split_index:], assumptions.initial_equity),
                },
            }
        )

    basket = _equal_weight_basket_record(bars_by_symbol, assumptions)
    if basket:
        records.append(basket)
    return records


def _equal_weight_basket_record(
    bars_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]],
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    available_symbols = tuple(
        symbol
        for symbol in assumptions.candidate_symbols
        if len(bars_by_symbol.get(symbol, ())) >= assumptions.min_bars_per_symbol
    )
    if len(available_symbols) < 2:
        return {}

    close_by_symbol = {
        symbol: {bar.timestamp: bar.close for bar in bars_by_symbol[symbol]}
        for symbol in available_symbols
    }
    common_timestamps = tuple(
        sorted(set.intersection(*(set(values) for values in close_by_symbol.values())))
    )
    if len(common_timestamps) < assumptions.min_bars_per_symbol:
        return {}

    asset_returns: list[Decimal] = []
    previous_closes: dict[str, Decimal] = {}
    for timestamp in common_timestamps:
        if not previous_closes:
            asset_returns.append(_ZERO)
        else:
            returns = tuple(
                (close_by_symbol[symbol][timestamp] / previous_closes[symbol]) - _ONE
                for symbol in available_symbols
            )
            asset_returns.append(sum(returns, _ZERO) / Decimal(len(returns)))
        previous_closes = {
            symbol: close_by_symbol[symbol][timestamp] for symbol in available_symbols
        }

    split_index = _split_index(len(common_timestamps), assumptions)
    points = _points_from_returns(
        timestamps=common_timestamps,
        asset_returns=tuple(asset_returns),
        target_exposures=tuple(_ONE for _ in common_timestamps),
        assumptions=assumptions,
    )
    return {
        "benchmark_id": "equal_weight_crypto_basket",
        "symbol": ",".join(available_symbols),
        "benchmark_type": "equal_weight_crypto_basket",
        "status": "available",
        "symbols": list(available_symbols),
        "windows": {
            "full": _metrics(points, assumptions.initial_equity),
            "train": _metrics(points[:split_index], assumptions.initial_equity),
            "test": _metrics(points[split_index:], assumptions.initial_equity),
        },
    }


def _strategy_specs() -> tuple[_StrategySpec, ...]:
    return (
        _StrategySpec(
            strategy_id="trend_momentum_1",
            strategy_family="trend_momentum",
            lookback=1,
        ),
        _StrategySpec(
            strategy_id="breakout_4",
            strategy_family="breakout",
            lookback=4,
        ),
        _StrategySpec(
            strategy_id="moving_average_regime_3_6",
            strategy_family="moving_average_regime",
            fast_window=3,
            slow_window=6,
        ),
        _StrategySpec(
            strategy_id="volatility_filter_4",
            strategy_family="volatility_filter",
            lookback=4,
            volatility_threshold=Decimal("0.08"),
        ),
    )


def _strategy_exposures(
    bars: tuple[CryptoEvidenceBar, ...],
    spec: _StrategySpec,
) -> tuple[Decimal, ...]:
    closes = tuple(bar.close for bar in bars)
    exposures: list[Decimal] = []
    for index, close in enumerate(closes):
        exposure = _ZERO
        if spec.strategy_family == "trend_momentum":
            if index >= spec.lookback and close > closes[index - spec.lookback]:
                exposure = _ONE
        elif spec.strategy_family == "breakout":
            if index >= spec.lookback and close > max(closes[index - spec.lookback : index]):
                exposure = _ONE
        elif spec.strategy_family == "moving_average_regime":
            if index + 1 >= spec.slow_window:
                fast = _average(closes[index - spec.fast_window + 1 : index + 1])
                slow = _average(closes[index - spec.slow_window + 1 : index + 1])
                if fast > slow:
                    exposure = _ONE
        elif spec.strategy_family == "volatility_filter":
            if index >= spec.lookback:
                returns = _trailing_returns(closes, index, spec.lookback)
                trend_ok = close > closes[index - spec.lookback]
                volatility_ok = _volatility(returns) <= spec.volatility_threshold
                if trend_ok and volatility_ok:
                    exposure = _ONE
        else:
            raise ValidationError("unknown strategy family.")
        exposures.append(exposure)
    return tuple(exposures)


def _evidence_points(
    *,
    bars: tuple[CryptoEvidenceBar, ...],
    asset_returns: tuple[Decimal, ...],
    target_exposures: tuple[Decimal, ...],
    assumptions: CryptoEvidenceAssumptions,
) -> tuple[_EvidencePoint, ...]:
    return _points_from_returns(
        timestamps=tuple(bar.timestamp for bar in bars),
        asset_returns=asset_returns,
        target_exposures=target_exposures,
        assumptions=assumptions,
    )


def _points_from_returns(
    *,
    timestamps: tuple[datetime, ...],
    asset_returns: tuple[Decimal, ...],
    target_exposures: tuple[Decimal, ...],
    assumptions: CryptoEvidenceAssumptions,
) -> tuple[_EvidencePoint, ...]:
    if not (
        len(timestamps) == len(asset_returns) == len(target_exposures)
    ):
        raise ValidationError("timestamps, returns, and exposures must align.")
    cost_rate = (assumptions.fee_bps + assumptions.slippage_bps) / _BPS_DENOMINATOR
    equity = assumptions.initial_equity
    previous_exposure = _ZERO
    points: list[_EvidencePoint] = []
    for timestamp, asset_return, target_exposure in zip(
        timestamps,
        asset_returns,
        target_exposures,
    ):
        turnover_delta = abs(target_exposure - previous_exposure)
        transaction_cost = turnover_delta * cost_rate
        strategy_return = (previous_exposure * asset_return) - transaction_cost
        equity = equity * (_ONE + strategy_return)
        points.append(
            _EvidencePoint(
                timestamp=timestamp,
                target_exposure=target_exposure,
                applied_exposure=previous_exposure,
                asset_return=asset_return,
                transaction_cost=transaction_cost,
                strategy_return_after_costs=strategy_return,
                equity=equity,
                turnover_delta=turnover_delta,
            )
        )
        previous_exposure = target_exposure
    return tuple(points)


def _metrics(
    points: Sequence[_EvidencePoint],
    initial_equity: Decimal,
) -> dict[str, object]:
    if not points:
        return _zero_metrics()

    equity = initial_equity
    peak = initial_equity
    max_drawdown = _ZERO
    returns: list[Decimal] = []
    estimated_cost_return = _ZERO
    turnover = _ZERO
    trade_count = 0
    exposure_sum = _ZERO
    for point in points:
        strategy_return = point.strategy_return_after_costs
        returns.append(strategy_return)
        equity = equity * (_ONE + strategy_return)
        if equity > peak:
            peak = equity
        drawdown = _ONE - (equity / peak)
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        estimated_cost_return += point.transaction_cost
        turnover += point.turnover_delta
        exposure_sum += point.target_exposure
        if point.turnover_delta > _ZERO:
            trade_count += 1

    total_return = (equity / initial_equity) - _ONE
    volatility = _volatility(tuple(returns))
    mean_return = sum(returns, _ZERO) / Decimal(len(returns))
    sharpe_like_ratio = _ZERO if volatility == _ZERO else mean_return / volatility
    return {
        "start": points[0].timestamp.isoformat(),
        "end": points[-1].timestamp.isoformat(),
        "bar_count": len(points),
        "total_return": _decimal_text(total_return),
        "max_drawdown": _decimal_text(max_drawdown),
        "volatility": _decimal_text(volatility),
        "sharpe_like_ratio": _decimal_text(sharpe_like_ratio),
        "trade_count": trade_count,
        "turnover": _decimal_text(turnover),
        "estimated_cost_return": _decimal_text(estimated_cost_return),
        "average_target_exposure": _decimal_text(exposure_sum / Decimal(len(points))),
    }


def _zero_metrics() -> dict[str, object]:
    return {
        "start": "",
        "end": "",
        "bar_count": 0,
        "total_return": "0",
        "max_drawdown": "0",
        "volatility": "0",
        "sharpe_like_ratio": "0",
        "trade_count": 0,
        "turnover": "0",
        "estimated_cost_return": "0",
        "average_target_exposure": "0",
    }


def _ranked_evaluations(
    evaluations: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    ranked = sorted(evaluations, key=_ranking_key)
    results: list[dict[str, object]] = []
    for rank, evaluation in enumerate(ranked, start=1):
        item = dict(evaluation)
        item["rank"] = rank
        results.append(item)
    return results


def _ranking_key(evaluation: Mapping[str, object]) -> tuple[object, ...]:
    decision = str(evaluation.get("candidate_decision", ""))
    priority = {
        "promote_to_no_submit_plan": 0,
        "reject_candidate": 1,
        "insufficient_data": 2,
    }.get(decision, 3)
    test_metrics = _mapping(_mapping(evaluation.get("windows")).get("test"))
    comparison = _mapping(evaluation.get("benchmark_comparison"))
    excess = _decimal_from_text(comparison.get("test_excess_return_vs_buy_hold", "0"))
    total_return = _decimal_from_text(test_metrics.get("total_return", "0"))
    drawdown = _decimal_from_text(test_metrics.get("max_drawdown", "0"))
    turnover = _decimal_from_text(test_metrics.get("turnover", "0"))
    return (
        priority,
        -excess,
        -total_return,
        drawdown,
        turnover,
        str(evaluation.get("candidate_id", "")),
    )


def _selected_candidate(
    ranked_evaluations: Sequence[Mapping[str, object]],
) -> dict[str, object] | None:
    for evaluation in ranked_evaluations:
        if evaluation.get("candidate_decision") == "promote_to_no_submit_plan":
            return dict(evaluation)
    return None


def _packet_decision(
    ranked_evaluations: Sequence[Mapping[str, object]],
    selected_candidate: Mapping[str, object] | None,
) -> str:
    if selected_candidate is not None:
        return "promote_to_no_submit_plan"
    decisions = tuple(str(item.get("candidate_decision", "")) for item in ranked_evaluations)
    if decisions and all(decision == "insufficient_data" for decision in decisions):
        return "insufficient_data"
    if any(decision == "reject_candidate" for decision in decisions):
        return "reject_candidate"
    return "keep_researching"


def _packet_rejection_reasons(
    ranked_evaluations: Sequence[Mapping[str, object]],
    selected_candidate: Mapping[str, object] | None,
) -> list[str]:
    if selected_candidate is not None:
        return []
    reasons: list[str] = []
    for evaluation in ranked_evaluations:
        reasons.extend(_string_sequence(evaluation.get("rejection_reasons")))
    return list(dict.fromkeys(reasons))


def _evidence_table(
    ranked_evaluations: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for evaluation in ranked_evaluations:
        test_metrics = _mapping(_mapping(evaluation.get("windows")).get("test"))
        comparison = _mapping(evaluation.get("benchmark_comparison"))
        rows.append(
            {
                "rank": evaluation.get("rank", ""),
                "candidate_id": evaluation.get("candidate_id", ""),
                "symbol": evaluation.get("symbol", ""),
                "strategy_id": evaluation.get("strategy_id", ""),
                "candidate_decision": evaluation.get("candidate_decision", ""),
                "test_total_return": test_metrics.get("total_return", ""),
                "test_max_drawdown": test_metrics.get("max_drawdown", ""),
                "test_volatility": test_metrics.get("volatility", ""),
                "test_sharpe_like_ratio": test_metrics.get("sharpe_like_ratio", ""),
                "test_trade_count": test_metrics.get("trade_count", ""),
                "test_turnover": test_metrics.get("turnover", ""),
                "test_estimated_cost_return": test_metrics.get(
                    "estimated_cost_return",
                    "",
                ),
                "buy_hold_test_total_return": comparison.get(
                    "buy_and_hold_test_total_return",
                    "",
                ),
                "test_excess_return_vs_buy_hold": comparison.get(
                    "test_excess_return_vs_buy_hold",
                    "",
                ),
                "rejection_reasons": evaluation.get("rejection_reasons", []),
            }
        )
    return rows


def _walk_forward_windows(
    bars_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]],
    assumptions: CryptoEvidenceAssumptions,
) -> list[dict[str, object]]:
    windows: list[dict[str, object]] = []
    for symbol in assumptions.candidate_symbols:
        bars = bars_by_symbol.get(symbol, ())
        if len(bars) < assumptions.min_bars_per_symbol:
            windows.append(
                {
                    "symbol": symbol,
                    "status": "insufficient_data",
                    "observed_bars": len(bars),
                    "required_bars": assumptions.min_bars_per_symbol,
                }
            )
            continue
        split_index = _split_index(len(bars), assumptions)
        windows.append(
            {
                "symbol": symbol,
                "status": "available",
                "train_start": bars[0].timestamp.isoformat(),
                "train_end": bars[split_index - 1].timestamp.isoformat(),
                "test_start": bars[split_index].timestamp.isoformat(),
                "test_end": bars[-1].timestamp.isoformat(),
                "train_bar_count": split_index,
                "test_bar_count": len(bars) - split_index,
            }
        )
    return windows


def _symbol_data_summary(
    symbol: str,
    bars: tuple[CryptoEvidenceBar, ...],
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    if not bars:
        return {
            "symbol": symbol,
            "bar_count": 0,
            "data_status": "missing_data",
            "first_bar_at": "",
            "latest_bar_at": "",
            "latest_close": "",
        }
    return {
        "symbol": symbol,
        "bar_count": len(bars),
        "data_status": "sufficient_history"
        if len(bars) >= assumptions.min_bars_per_symbol
        else "insufficient_data",
        "first_bar_at": bars[0].timestamp.isoformat(),
        "latest_bar_at": bars[-1].timestamp.isoformat(),
        "latest_close": _decimal_text(bars[-1].close),
    }


def _insufficient_candidate_record(
    *,
    candidate_id: str,
    symbol: str,
    spec: _StrategySpec,
    observed_bars: int,
    required_bars: int,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "strategy_id": spec.strategy_id,
        "strategy_family": spec.strategy_family,
        "parameters": _strategy_parameters(spec),
        "candidate_decision": "insufficient_data",
        "rejection_reasons": ["insufficient_data"],
        "observed_bars": observed_bars,
        "required_bars": required_bars,
        "windows": {
            "full": _zero_metrics(),
            "train": _zero_metrics(),
            "test": _zero_metrics(),
        },
        "benchmark_comparison": {
            "buy_and_hold_test_total_return": "",
            "cash_no_trade_test_total_return": "0",
            "equal_weight_basket_test_total_return": "",
            "test_excess_return_vs_buy_hold": "",
        },
    }


def _strategy_spec_payload(spec: _StrategySpec) -> dict[str, object]:
    return {
        "strategy_id": spec.strategy_id,
        "strategy_family": spec.strategy_family,
        "parameters": _strategy_parameters(spec),
    }


def _strategy_parameters(spec: _StrategySpec) -> dict[str, object]:
    if spec.strategy_family in {"trend_momentum", "breakout"}:
        return {"lookback": spec.lookback}
    if spec.strategy_family == "moving_average_regime":
        return {
            "fast_window": spec.fast_window,
            "slow_window": spec.slow_window,
        }
    if spec.strategy_family == "volatility_filter":
        return {
            "lookback": spec.lookback,
            "volatility_threshold": _decimal_text(spec.volatility_threshold),
        }
    return {}


def _next_safe_operator_action(no_submit_decision: str) -> str:
    if no_submit_decision == "promote_to_no_submit_plan":
        return (
            "Review the selected research candidate offline and open a separate "
            "no-submit planning milestone before any broker-facing work."
        )
    if no_submit_decision == "insufficient_data":
        return "Collect more local historical bars offline, then rerun this research battery."
    if no_submit_decision == "reject_candidate":
        return "Keep these candidates in research and change only one simple hypothesis offline."
    return "Keep researching with the same small candidate set until evidence improves."


def _split_index(length: int, assumptions: CryptoEvidenceAssumptions) -> int:
    return (length * assumptions.train_fraction_numerator) // (
        assumptions.train_fraction_denominator
    )


def _asset_returns_from_bars(
    bars: tuple[CryptoEvidenceBar, ...],
) -> tuple[Decimal, ...]:
    returns: list[Decimal] = []
    previous_close: Decimal | None = None
    for bar in bars:
        if previous_close is None:
            returns.append(_ZERO)
        else:
            returns.append((bar.close / previous_close) - _ONE)
        previous_close = bar.close
    return tuple(returns)


def _trailing_returns(
    closes: tuple[Decimal, ...],
    index: int,
    lookback: int,
) -> tuple[Decimal, ...]:
    returns: list[Decimal] = []
    first = index - lookback + 1
    for current_index in range(first, index + 1):
        previous = closes[current_index - 1]
        current = closes[current_index]
        returns.append((current / previous) - _ONE)
    return tuple(returns)


def _average(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValidationError("average requires at least one value.")
    return sum(values, _ZERO) / Decimal(len(values))


def _volatility(returns: Sequence[Decimal]) -> Decimal:
    if not returns:
        return _ZERO
    mean = sum(returns, _ZERO) / Decimal(len(returns))
    variance = sum(((value - mean) * (value - mean) for value in returns), _ZERO) / Decimal(
        len(returns)
    )
    if variance == _ZERO:
        return _ZERO
    return variance.sqrt()


def _first_benchmark(
    records: Sequence[Mapping[str, object]],
    benchmark_id: str,
) -> Mapping[str, object]:
    for record in records:
        if record.get("benchmark_id") == benchmark_id:
            return record
    return {}


def _basket_test_return(
    basket_record: Mapping[str, object],
) -> Decimal | None:
    if not basket_record:
        return None
    test_metrics = _mapping(_mapping(basket_record.get("windows")).get("test"))
    return _decimal_from_text(test_metrics.get("total_return", "0"))


def _bar_tuple(
    bars: Iterable[CryptoEvidenceBar],
) -> tuple[CryptoEvidenceBar, ...]:
    if isinstance(bars, (str, bytes)):
        raise ValidationError("bars must be an iterable of CryptoEvidenceBar values.")
    try:
        bar_items = tuple(bars)
    except TypeError as exc:
        raise ValidationError(
            "bars must be an iterable of CryptoEvidenceBar values."
        ) from exc
    for bar in bar_items:
        if not isinstance(bar, CryptoEvidenceBar):
            raise ValidationError("bars must contain CryptoEvidenceBar values.")
    return bar_items


def _bars_by_symbol(
    bars: tuple[CryptoEvidenceBar, ...],
) -> dict[str, tuple[CryptoEvidenceBar, ...]]:
    grouped: dict[str, list[CryptoEvidenceBar]] = {}
    for bar in bars:
        grouped.setdefault(bar.symbol, []).append(bar)

    result: dict[str, tuple[CryptoEvidenceBar, ...]] = {}
    for symbol, symbol_bars in grouped.items():
        ordered = tuple(sorted(symbol_bars, key=lambda item: item.timestamp))
        seen: set[datetime] = set()
        previous_timestamp: datetime | None = None
        for bar in ordered:
            if bar.timestamp in seen:
                raise ValidationError("bars must not contain duplicate symbol timestamps.")
            if previous_timestamp is not None and bar.timestamp <= previous_timestamp:
                raise ValidationError("bars must be strictly increasing by symbol.")
            seen.add(bar.timestamp)
            previous_timestamp = bar.timestamp
        result[symbol] = ordered
    return result


def _candidate_symbol_tuple(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValidationError("candidate_symbols must be an iterable of symbols.")
    symbols = tuple(_crypto_symbol(value, "candidate_symbols") for value in values)
    if not symbols:
        raise ValidationError("candidate_symbols must not be empty.")
    if len(set(symbols)) != len(symbols):
        raise ValidationError("candidate_symbols must not contain duplicates.")
    return symbols


def _crypto_symbol(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a symbol string.")
    normalized = "".join(ch for ch in value.upper().strip() if ch.isalnum())
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty symbol.")
    return normalized


def _aware_utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or type(value) is not datetime:
        raise ValidationError(f"{field_name} must be a datetime.")
    if value.tzinfo is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return value.astimezone(UTC)


def _as_of_text(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return _aware_utc_datetime(value, "as_of").isoformat()
    return _required_text(value, "as_of")


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")
    text = value.strip()
    if not text:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return text


def _positive_int(value: int, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def _finite_decimal(value: Decimal, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(f"{field_name} must be a Decimal.")
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return value


def _positive_decimal(value: Decimal, field_name: str) -> Decimal:
    checked = _finite_decimal(value, field_name)
    if checked <= _ZERO:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return checked


def _non_negative_decimal(value: Decimal, field_name: str) -> Decimal:
    checked = _finite_decimal(value, field_name)
    if checked < _ZERO:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return checked


def _decimal_from_text(value: object) -> Decimal:
    text = str(value).strip()
    if not text:
        return _ZERO
    return Decimal(text)


def _decimal_text(value: Decimal) -> str:
    checked = _finite_decimal(value, "decimal")
    if checked == _ZERO:
        return "0"
    quantized = checked.quantize(_DECIMAL_QUANTUM)
    if quantized == _ZERO:
        return "0"
    return format(quantized.normalize(), "f")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _false_safety_flags() -> dict[str, bool]:
    return {field_name: False for field_name in NO_SUBMIT_SAFETY_FIELDS}
