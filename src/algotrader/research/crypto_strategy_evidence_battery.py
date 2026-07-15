"""Deterministic no-submit crypto strategy evidence battery.

The battery is intentionally small and research-only. It evaluates simple
long-or-flat crypto candidates against cash, buy-and-hold, and an optional
equal-weight basket benchmark without importing broker, execution, network, or
LLM dependencies.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from algotrader.errors import ValidationError

CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION = (
    "v5_20_crypto_strategy_evidence_battery_v1"
)
CRYPTO_REPAIR_FRESH_OOS_SCHEMA_VERSION = "v5_20_1_crypto_repair_fresh_oos_gate_v1"
CRYPTO_STRATEGY_CANDIDATE_FACTORY_VERSION = (
    "v5_21_crypto_fixed_candidate_factory_v1"
)
DEFAULT_CRYPTO_EVIDENCE_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD")
DEFAULT_REPAIR_DISCOVERY_CUTOFF = datetime(2026, 7, 9, 16, 0, tzinfo=UTC)
DEFAULT_FRESH_OOS_REPAIR_CANDIDATE = "crypto:ADAUSD:trend_momentum_24h_repair"
LOCAL_HISTORICAL_CRYPTO_REQUIRED_COLUMNS = (
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
)
LOCAL_HISTORICAL_CRYPTO_OPTIONAL_COLUMNS = ("volume",)
LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES: Mapping[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "datetime", "date", "t"),
    "symbol": ("symbol", "S"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "v"),
}
ACCEPTABLE_LOCAL_CRYPTO_HISTORY_FORMATS = (
    "single CSV with timestamp, symbol, open, high, low, and close columns or "
    "aliases (datetime/date/t, S, o, h, l, c)",
    "single CSV with OHLCV columns; volume/v is recorded when present but is not "
    "required because this evidence battery uses close-only strategies",
    "per-symbol CSV files with the same required timestamp, symbol, open, high, "
    "low, and close fields",
)
DEFAULT_LOCAL_CRYPTO_HISTORY_PATHS = (
    Path("runs/operator_input/crypto_paper_bars.csv"),
    Path("runs/crypto_paper_read_only_refresh/latest/crypto_paper_bars.csv"),
)
DEFAULT_LOCAL_CRYPTO_HISTORY_GLOB_PATHS = (
    Path("runs/crypto_universe_refresh/latest/history"),
    Path("runs/crypto_universe_refresh/v5_17_observed_artifact_smoke_packet/history"),
)
REAL_DATA_PROMOTION_BLOCKING_SOURCE_MARKERS = (
    "deterministic_unit_fixture",
    "offline_fixture",
    "fixture",
    "synthetic",
)

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

DIAGNOSTIC_REPAIR_PROMOTION_BLOCKER = "fresh_oos_required_for_repair_promotion"

__all__ = [
    "CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION",
    "CRYPTO_REPAIR_FRESH_OOS_SCHEMA_VERSION",
    "CRYPTO_STRATEGY_CANDIDATE_FACTORY_VERSION",
    "ACCEPTABLE_LOCAL_CRYPTO_HISTORY_FORMATS",
    "DEFAULT_CRYPTO_EVIDENCE_SYMBOLS",
    "DEFAULT_FRESH_OOS_REPAIR_CANDIDATE",
    "DEFAULT_LOCAL_CRYPTO_HISTORY_PATHS",
    "DEFAULT_LOCAL_CRYPTO_HISTORY_GLOB_PATHS",
    "DEFAULT_REPAIR_DISCOVERY_CUTOFF",
    "LOCAL_HISTORICAL_CRYPTO_OPTIONAL_COLUMNS",
    "LOCAL_HISTORICAL_CRYPTO_REQUIRED_COLUMNS",
    "NO_SUBMIT_SAFETY_FIELDS",
    "REQUIRED_NO_SUBMIT_LABELS",
    "CryptoEvidenceAssumptions",
    "CryptoEvidenceBar",
    "build_crypto_strategy_candidate_factory",
    "build_crypto_repair_fresh_oos_validation_packet",
    "build_crypto_strategy_real_data_evidence_packet",
    "classify_crypto_strategy_no_submit_packet",
    "default_existing_local_crypto_history_paths",
    "load_crypto_evidence_bars_from_csv",
    "run_crypto_strategy_evidence_battery",
    "validate_crypto_strategy_no_submit_packet",
    "write_crypto_strategy_evidence_packet",
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
    min_history_rows_per_symbol: int = 80
    min_history_span_hours: int = 72
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
            "min_history_rows_per_symbol",
            _positive_int(
                self.min_history_rows_per_symbol,
                "min_history_rows_per_symbol",
            ),
        )
        object.__setattr__(
            self,
            "min_history_span_hours",
            _positive_int(self.min_history_span_hours, "min_history_span_hours"),
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


@dataclass(frozen=True, slots=True)
class _CryptoHistoryRow:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: str
    input_path_index: int
    source_row_number: int

    def evidence_bar(self) -> CryptoEvidenceBar:
        return CryptoEvidenceBar(
            symbol=self.symbol,
            timestamp=self.timestamp,
            close=self.close,
        )


def build_crypto_strategy_candidate_factory() -> dict[str, object]:
    """Describe the battery's small, versioned, immutable candidate set.

    This is an integration descriptor over the same private strategy specs the
    evidence battery executes.  It intentionally exposes no parameter search,
    optimization, or post-hoc mutation surface.
    """

    base_candidates: list[dict[str, object]] = []
    for spec in _strategy_specs():
        candidate = _strategy_spec_payload(spec)
        candidate.update(
            {
                "candidate_origin": "current",
                "promotion_scope": "existing_evidence_battery_gates",
            }
        )
        base_candidates.append(candidate)
    repair_candidates = _diagnostic_repair_candidates_payload()
    return {
        "factory_version": CRYPTO_STRATEGY_CANDIDATE_FACTORY_VERSION,
        "evidence_policy_version": CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
        "base_candidates": base_candidates,
        "diagnostic_repair_candidates": repair_candidates,
        "fixed_candidate_count_per_symbol": len(base_candidates)
        + len(repair_candidates),
        "dynamic_parameter_optimization": False,
        "post_hoc_retuning": False,
        "candidate_set_mutation_allowed": False,
    }


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
    repair_evaluations = _diagnostic_repair_evaluations(
        bars_by_symbol=bars_by_symbol,
        assumptions=checked_assumptions,
        buy_hold_by_symbol=buy_hold_by_symbol,
        basket_record=basket_record,
        base_rank_count=len(ranked_evaluations),
    )
    selected_candidate = _selected_candidate(ranked_evaluations)
    no_submit_decision = _packet_decision(ranked_evaluations, selected_candidate)
    rejection_reasons = _packet_rejection_reasons(
        ranked_evaluations,
        selected_candidate,
    )
    diagnostics = _strategy_failure_diagnostics(
        data_source=data_source_text,
        symbol_summaries=symbol_summaries,
        benchmark_records=benchmark_records,
        ranked_evaluations=ranked_evaluations,
        repair_evaluations=repair_evaluations,
        walk_forward_windows=_walk_forward_windows(
            bars_by_symbol,
            checked_assumptions,
        ),
    )
    strategy_evidence_table_after_repairs = [
        *_evidence_table(ranked_evaluations),
        *_evidence_table(repair_evaluations),
    ]

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
        "input_history_path": "",
        "data_summary": symbol_summaries,
        "walk_forward_windows": diagnostics["train_test_windows"],
        "benchmark_comparison": {
            "benchmarks": benchmark_records,
            "cash_no_trade_return": "0",
            "equal_weight_crypto_basket_available": bool(basket_record),
        },
        "benchmark_returns": diagnostics["benchmark_returns"],
        "evidence_table": _evidence_table(ranked_evaluations),
        "strategy_evidence_table_after_repairs": strategy_evidence_table_after_repairs,
        "candidate_evaluations": ranked_evaluations,
        "diagnostic_repair_candidate_evaluations": repair_evaluations,
        "diagnostics": diagnostics,
        "candidate_failure_summary": diagnostics["candidate_failure_summary"],
        "candidate_failure_summary_by_symbol": diagnostics[
            "candidate_failure_summary_by_symbol"
        ],
        "candidate_failure_summary_by_strategy_type": diagnostics[
            "candidate_failure_summary_by_strategy_type"
        ],
        "rejection_reasons_by_candidate": diagnostics[
            "rejection_reasons_by_candidate"
        ],
        "trade_count_by_candidate": diagnostics["trade_count_by_candidate"],
        "max_drawdown_by_candidate": diagnostics["max_drawdown_by_candidate"],
        "cash_and_buy_hold_underperformance_by_candidate": diagnostics[
            "cash_and_buy_hold_underperformance_by_candidate"
        ],
        "train_test_windows": diagnostics["train_test_windows"],
        "market_regime_summary": diagnostics["market_regime_summary"],
        "drawdown_summary": diagnostics["drawdown_summary"],
        "repair_added": diagnostics["repair_added"],
        "repaired_candidates": diagnostics["repaired_candidates"],
        "repair_candidate_summary": diagnostics["repair_candidate_summary"],
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
            "must_outperform_equal_weight_crypto_basket_oos": True,
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


def load_crypto_evidence_bars_from_csv(
    path: Path | str,
    *,
    symbols: Iterable[str] | None = None,
) -> tuple[CryptoEvidenceBar, ...]:
    """Load immutable evidence bars from a local historical crypto CSV."""

    inventory, bars = _load_crypto_evidence_csv(
        Path(path),
        symbols=_optional_symbol_filter(symbols),
    )
    if inventory.get("missing_columns"):
        missing = ", ".join(_string_sequence(inventory.get("missing_columns")))
        raise ValidationError(f"crypto evidence CSV missing required columns: {missing}")
    if inventory.get("read_error"):
        detail = str(inventory.get("read_error_detail", "")).strip()
        if detail:
            raise ValidationError(f"{inventory['read_error']}: {detail}")
        raise ValidationError(str(inventory["read_error"]))
    if not bars:
        raise ValidationError("crypto evidence CSV did not include usable crypto rows.")
    return bars


def build_crypto_repair_fresh_oos_validation_packet(
    csv_paths: Iterable[Path | str] | Path | str,
    *,
    as_of: datetime | str,
    discovery_cutoff: datetime | str = DEFAULT_REPAIR_DISCOVERY_CUTOFF,
    repair_candidate: str = DEFAULT_FRESH_OOS_REPAIR_CANDIDATE,
    oos_data_source: str = "local_historical_crypto_csv",
    assumptions: CryptoEvidenceAssumptions | None = None,
    required_min_oos_rows: int | None = None,
) -> dict[str, object]:
    """Validate the ADA diagnostic repair only on bars after the discovery cutoff."""

    checked_assumptions = assumptions or CryptoEvidenceAssumptions()
    checked_paths = _path_tuple(csv_paths)
    cutoff = (
        _aware_utc_datetime(discovery_cutoff, "discovery_cutoff")
        if isinstance(discovery_cutoff, datetime)
        else _csv_datetime(str(discovery_cutoff))
    )
    required_rows = _fresh_oos_required_rows(
        checked_assumptions,
        required_min_oos_rows,
    )
    if repair_candidate != DEFAULT_FRESH_OOS_REPAIR_CANDIDATE:
        raise ValidationError(
            "fresh-OOS repair validation is scoped to "
            f"{DEFAULT_FRESH_OOS_REPAIR_CANDIDATE}."
        )

    inventories: list[dict[str, object]] = []
    history_rows: list[_CryptoHistoryRow] = []
    blocking_reasons: list[str] = []
    if not checked_paths:
        blocking_reasons.append("missing_input_path")

    for input_path_index, path in enumerate(checked_paths):
        inventory, path_rows = _load_crypto_history_rows_from_csv(
            path,
            symbols=set(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS),
            input_path_index=input_path_index,
        )
        inventories.append(inventory)
        if inventory.get("missing_columns"):
            blocking_reasons.append("missing_required_columns")
        if inventory.get("read_error"):
            blocking_reasons.append(str(inventory["read_error"]))
        if not inventory.get("missing_columns") and not inventory.get("read_error"):
            history_rows.extend(path_rows)

    normalized_rows = _normalize_crypto_history_rows(tuple(history_rows))
    strict_oos_rows = tuple(row for row in normalized_rows if row.timestamp > cutoff)
    oos_bars = tuple(row.evidence_bar() for row in strict_oos_rows)
    oos_bars_by_symbol = _bars_by_symbol(oos_bars)
    ada_bars = oos_bars_by_symbol.get("ADAUSD", ())
    oos_rows_by_symbol = _rows_per_symbol_from_bars(oos_bars_by_symbol)
    oos_range_by_symbol = _date_range_per_symbol_from_bars(oos_bars_by_symbol)

    rejection_reasons = list(dict.fromkeys(blocking_reasons))
    if not ada_bars:
        rejection_reasons.append("no_oos_rows_after_discovery_cutoff")
    elif len(ada_bars) < required_rows:
        rejection_reasons.append("insufficient_oos_rows")

    metrics: Mapping[str, object] = _zero_metrics()
    buy_hold_metrics: Mapping[str, object] = {}
    basket_metrics: Mapping[str, object] = {}
    oos_test_return = ""
    buy_hold_return = ""
    basket_return = ""
    excess_vs_cash = ""
    excess_vs_buy_hold = ""
    excess_vs_basket = ""
    max_drawdown = ""
    trade_count: int | str = ""

    if not rejection_reasons:
        spec = _diagnostic_repair_strategy_specs()[0]
        metrics = _fresh_oos_strategy_metrics(
            bars=ada_bars,
            spec=spec,
            assumptions=checked_assumptions,
        )
        buy_hold_metrics = _fresh_oos_buy_hold_metrics(
            bars=ada_bars,
            assumptions=checked_assumptions,
        )
        basket_metrics = _fresh_oos_equal_weight_basket_metrics(
            bars_by_symbol=oos_bars_by_symbol,
            assumptions=checked_assumptions,
            required_min_oos_rows=required_rows,
        )

        candidate_return = _decimal_from_text(metrics.get("total_return", "0"))
        ada_buy_hold_return = _decimal_from_text(
            buy_hold_metrics.get("total_return", "0")
        )
        basket_total_return = (
            _decimal_from_text(basket_metrics.get("total_return", "0"))
            if basket_metrics
            else None
        )
        candidate_max_drawdown = _decimal_from_text(metrics.get("max_drawdown", "0"))

        if candidate_return <= checked_assumptions.min_test_total_return:
            rejection_reasons.append("cash_underperformance")
        if (
            candidate_return - ada_buy_hold_return
            <= checked_assumptions.min_test_excess_return_vs_buy_hold
        ):
            rejection_reasons.append("buy_and_hold_underperformance")
        if basket_total_return is not None and candidate_return <= basket_total_return:
            rejection_reasons.append("basket_underperformance")
        if candidate_max_drawdown > checked_assumptions.max_test_drawdown:
            rejection_reasons.append("high_drawdown")

        oos_test_return = _decimal_text(candidate_return)
        buy_hold_return = _decimal_text(ada_buy_hold_return)
        basket_return = (
            _decimal_text(basket_total_return)
            if basket_total_return is not None
            else ""
        )
        excess_vs_cash = _decimal_text(candidate_return)
        excess_vs_buy_hold = _decimal_text(candidate_return - ada_buy_hold_return)
        excess_vs_basket = (
            _decimal_text(candidate_return - basket_total_return)
            if basket_total_return is not None
            else ""
        )
        max_drawdown = str(metrics.get("max_drawdown", ""))
        trade_count = int(metrics.get("trade_count", 0))

    if not checked_paths:
        classification = "market_data_refresh_not_configured"
    elif "no_oos_rows_after_discovery_cutoff" in rejection_reasons:
        classification = "fresh_oos_data_not_available"
    elif "insufficient_oos_rows" in rejection_reasons:
        classification = "fresh_oos_data_not_available"
    elif rejection_reasons:
        classification = "fresh_oos_rejected"
    else:
        classification = "fresh_oos_validated"

    eligible = classification == "fresh_oos_validated"
    packet: dict[str, object] = {
        "schema_version": CRYPTO_REPAIR_FRESH_OOS_SCHEMA_VERSION,
        "record_type": "crypto_repair_fresh_oos_validation_packet",
        "as_of": _as_of_text(as_of),
        "classification": classification,
        "repair_candidate": repair_candidate,
        "discovery_cutoff": cutoff.isoformat(),
        "oos_data_source": _required_text(oos_data_source, "oos_data_source"),
        "oos_rows": len(ada_bars),
        "available_oos_rows": len(ada_bars),
        "oos_rows_by_symbol": _rows_with_required_symbol_zeros(
            oos_rows_by_symbol,
            DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
        ),
        "oos_date_range": _oos_date_range(ada_bars),
        "oos_date_range_by_symbol": oos_range_by_symbol,
        "required_min_oos_rows": required_rows,
        "oos_test_return": oos_test_return,
        "cash_return": "0",
        "ADA_buy_and_hold_return": buy_hold_return,
        "equal_weight_basket_return": basket_return,
        "excess_vs_cash": excess_vs_cash,
        "excess_vs_buy_hold": excess_vs_buy_hold,
        "excess_vs_basket": excess_vs_basket,
        "max_drawdown": max_drawdown,
        "trade_count": trade_count,
        "rejection_reasons": rejection_reasons,
        "repair_promotion_eligibility": (
            "eligible_for_no_submit_plan" if eligible else "not_eligible"
        ),
        "paper_planning_eligibility": (
            "eligible_for_no_submit_plan" if eligible else "not_eligible"
        ),
        "next_safe_operator_action": _fresh_oos_next_safe_operator_action(
            classification
        ),
        "input_paths": [str(path) for path in checked_paths],
        "data_inventory": _data_inventory_payload(
            csv_paths=checked_paths,
            inventories=tuple(inventories),
            assumptions=checked_assumptions,
            blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
            normalized_rows=normalized_rows,
        ),
        "candidate_metrics": dict(metrics),
        "ADA_buy_and_hold_metrics": dict(buy_hold_metrics),
        "equal_weight_basket_metrics": dict(basket_metrics),
        "benchmark_gate_summary": {
            "must_outperform_cash": True,
            "must_outperform_ADA_buy_and_hold": True,
            "must_outperform_equal_weight_basket_when_available": True,
            "max_drawdown_allowed": _decimal_text(
                checked_assumptions.max_test_drawdown
            ),
        },
        "labels": list(REQUIRED_NO_SUBMIT_LABELS),
        "profit_claim": "none",
        "market_data_fetch_occurred": False,
        "runs_tracked": False,
        **_false_safety_flags(),
    }
    validation_errors = validate_crypto_strategy_no_submit_packet(packet)
    packet["validation_status"] = "passed" if not validation_errors else "failed"
    packet["validation_errors"] = validation_errors
    return packet

def build_crypto_strategy_real_data_evidence_packet(
    csv_paths: Iterable[Path | str] | Path | str,
    *,
    as_of: datetime | str,
    data_source: str = "local_historical_crypto_csv",
    data_freshness: str = "local_historical_snapshot",
    assumptions: CryptoEvidenceAssumptions | None = None,
    normalized_output_path: Path | str | None = None,
) -> dict[str, object]:
    """Run the battery against local CSV history and add real-data provenance gates."""

    checked_assumptions = assumptions or CryptoEvidenceAssumptions()
    checked_paths = _path_tuple(csv_paths)
    inventories: list[dict[str, object]] = []
    history_rows: list[_CryptoHistoryRow] = []
    blocking_reasons: list[str] = []
    normalized_output_text = ""

    if not checked_paths:
        blocking_reasons.append("missing_input_path")

    for input_path_index, path in enumerate(checked_paths):
        inventory, path_rows = _load_crypto_history_rows_from_csv(
            path,
            symbols=set(checked_assumptions.candidate_symbols),
            input_path_index=input_path_index,
        )
        inventories.append(inventory)
        if inventory.get("missing_columns"):
            blocking_reasons.append("missing_required_columns")
        if inventory.get("read_error"):
            blocking_reasons.append(str(inventory["read_error"]))
        if not inventory.get("missing_columns") and not inventory.get("read_error"):
            history_rows.extend(path_rows)

    normalized_rows = _normalize_crypto_history_rows(tuple(history_rows))

    preliminary_inventory = _data_inventory_payload(
        csv_paths=checked_paths,
        inventories=tuple(inventories),
        assumptions=checked_assumptions,
        blocking_reasons=tuple(blocking_reasons),
        normalized_rows=normalized_rows,
        normalized_output_path="",
    )
    blocking_reasons = _string_list(preliminary_inventory.get("blocking_reasons"))

    if (
        normalized_output_path is not None
        and normalized_rows
        and str(preliminary_inventory.get("schema_validation_status")) == "passed"
        and str(preliminary_inventory.get("missing_close_status")) == "passed"
    ):
        normalized_output_text = str(
            _write_normalized_crypto_history_csv(
                normalized_rows,
                Path(normalized_output_path),
            )
        )
        preliminary_inventory = _data_inventory_payload(
            csv_paths=checked_paths,
            inventories=tuple(inventories),
            assumptions=checked_assumptions,
            blocking_reasons=tuple(blocking_reasons),
            normalized_rows=normalized_rows,
            normalized_output_path=normalized_output_text,
        )
        blocking_reasons = _string_list(preliminary_inventory.get("blocking_reasons"))

    if blocking_reasons:
        evidence_bars: tuple[CryptoEvidenceBar, ...] = ()
    else:
        evidence_bars = tuple(row.evidence_bar() for row in normalized_rows)

    try:
        packet = run_crypto_strategy_evidence_battery(
            evidence_bars,
            as_of=as_of,
            data_source=data_source,
            data_freshness=data_freshness,
            assumptions=checked_assumptions,
        )
    except ValidationError as exc:
        blocking_reasons.append(f"invalid_local_history:{exc}")
        packet = run_crypto_strategy_evidence_battery(
            (),
            as_of=as_of,
            data_source=data_source,
            data_freshness=data_freshness,
            assumptions=checked_assumptions,
        )

    return _real_data_probe_packet(
        packet,
        csv_paths=checked_paths,
        inventories=tuple(inventories),
        assumptions=checked_assumptions,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        data_inventory=preliminary_inventory,
    )


def classify_crypto_strategy_no_submit_packet(packet: Mapping[str, object]) -> str:
    """Map a battery packet to the real-data no-submit classification vocabulary."""

    if _object_contains_source_marker(packet):
        return "insufficient_real_crypto_history"

    decision = str(packet.get("no_submit_decision", "")).strip()
    if decision == "promote_to_no_submit_plan":
        return "promote_to_no_submit_plan"
    if decision == "reject_candidate":
        return "reject_candidate"
    if decision == "insufficient_data":
        return "insufficient_real_crypto_history"
    return "keep_researching"


def default_existing_local_crypto_history_paths() -> tuple[Path, ...]:
    """Return known ignored local crypto CSV artifacts that exist in this workspace."""

    paths: list[Path] = [
        path for path in DEFAULT_LOCAL_CRYPTO_HISTORY_PATHS if path.is_file()
    ]
    for directory in DEFAULT_LOCAL_CRYPTO_HISTORY_GLOB_PATHS:
        if directory.is_dir():
            paths.extend(sorted(directory.glob("*.csv")))
    return tuple(dict.fromkeys(paths))


def write_crypto_strategy_evidence_packet(
    packet: Mapping[str, object],
    output_path: Path | str,
) -> Path:
    """Write a deterministic JSON evidence packet to a local artifact path."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(packet), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the no-submit crypto strategy evidence battery on local CSVs.",
    )
    parser.add_argument(
        "--input-csv",
        action="append",
        default=[],
        help="Local historical crypto CSV path. May be supplied multiple times.",
    )
    parser.add_argument(
        "--output-path",
        default="",
        help="Optional JSON packet path, normally under ignored runs/.",
    )
    parser.add_argument(
        "--normalized-output-path",
        default="",
        help="Optional normalized OHLC CSV path, normally under ignored runs/.",
    )
    parser.add_argument("--as-of", required=True, help="UTC ISO timestamp for the packet.")
    parser.add_argument(
        "--data-source",
        default="local_historical_crypto_csv",
        help="Data source label for non-fixture local history.",
    )
    parser.add_argument(
        "--data-freshness",
        default="local_historical_snapshot",
        help="Data freshness label for the local input snapshot.",
    )
    args = parser.parse_args(argv)

    input_paths = tuple(Path(path) for path in args.input_csv)
    if not input_paths:
        input_paths = default_existing_local_crypto_history_paths()

    packet = build_crypto_strategy_real_data_evidence_packet(
        input_paths,
        as_of=args.as_of,
        data_source=args.data_source,
        data_freshness=args.data_freshness,
        normalized_output_path=args.normalized_output_path or None,
    )
    if args.output_path:
        write_crypto_strategy_evidence_packet(packet, args.output_path)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


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


def _fresh_oos_required_rows(
    assumptions: CryptoEvidenceAssumptions,
    required_min_oos_rows: int | None,
) -> int:
    repair_spec = _diagnostic_repair_strategy_specs()[0]
    minimum = max(assumptions.min_bars_per_symbol, repair_spec.lookback + 2)
    if required_min_oos_rows is not None:
        minimum = max(minimum, _positive_int(required_min_oos_rows, "required_min_oos_rows"))
    return minimum


def _fresh_oos_strategy_metrics(
    *,
    bars: tuple[CryptoEvidenceBar, ...],
    spec: _StrategySpec,
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    points = _evidence_points(
        bars=bars,
        asset_returns=_asset_returns_from_bars(bars),
        target_exposures=_strategy_exposures(bars, spec),
        assumptions=assumptions,
    )
    return _metrics(points, assumptions.initial_equity)


def _fresh_oos_buy_hold_metrics(
    *,
    bars: tuple[CryptoEvidenceBar, ...],
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    points = _evidence_points(
        bars=bars,
        asset_returns=_asset_returns_from_bars(bars),
        target_exposures=tuple(_ONE for _ in bars),
        assumptions=assumptions,
    )
    return _metrics(points, assumptions.initial_equity)


def _fresh_oos_equal_weight_basket_metrics(
    *,
    bars_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]],
    assumptions: CryptoEvidenceAssumptions,
    required_min_oos_rows: int,
) -> dict[str, object]:
    available_symbols = tuple(
        symbol
        for symbol in DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
        if len(bars_by_symbol.get(symbol, ())) >= required_min_oos_rows
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
    if len(common_timestamps) < required_min_oos_rows:
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
            asset_returns.append(_average(returns))
        previous_closes = {
            symbol: close_by_symbol[symbol][timestamp]
            for symbol in available_symbols
        }

    points = _points_from_returns(
        timestamps=common_timestamps,
        asset_returns=tuple(asset_returns),
        target_exposures=tuple(_ONE for _ in asset_returns),
        assumptions=assumptions,
    )
    metrics = _metrics(points, assumptions.initial_equity)
    metrics["symbols"] = list(available_symbols)
    metrics["common_oos_rows"] = len(common_timestamps)
    return metrics


def _oos_date_range(bars: Sequence[CryptoEvidenceBar]) -> dict[str, str]:
    if not bars:
        return {"start": "", "end": ""}
    timestamps = tuple(bar.timestamp for bar in bars)
    return {
        "start": min(timestamps).isoformat(),
        "end": max(timestamps).isoformat(),
    }


def _fresh_oos_next_safe_operator_action(classification: str) -> str:
    if classification == "fresh_oos_validated":
        return (
            "review the fresh-OOS packet and only then consider a separate "
            "no-submit planning packet; no broker submit or mutation is authorized"
        )
    if classification == "market_data_refresh_not_configured":
        return (
            "configure an explicitly authorized guarded read-only market-data "
            "refresh before collecting fresh OOS data"
        )
    return (
        "wait for fresh local OOS bars after the discovery cutoff or explicitly "
        "authorize the guarded read-only market-data refresh wrapper; no broker "
        "action is authorized"
    )

def _load_crypto_evidence_csv(
    path: Path,
    *,
    symbols: set[str] | None,
) -> tuple[dict[str, object], tuple[CryptoEvidenceBar, ...]]:
    inventory, rows = _load_crypto_history_rows_from_csv(
        path,
        symbols=symbols,
        input_path_index=0,
    )
    if inventory.get("missing_columns") or inventory.get("read_error"):
        return inventory, ()
    normalized_rows = _normalize_crypto_history_rows(rows)
    _apply_normalized_rows_to_inventory(inventory, normalized_rows)
    return inventory, tuple(row.evidence_bar() for row in normalized_rows)


def _load_crypto_history_rows_from_csv(
    path: Path,
    *,
    symbols: set[str] | None,
    input_path_index: int,
) -> tuple[dict[str, object], tuple[_CryptoHistoryRow, ...]]:
    inventory = _empty_csv_inventory(path)
    if not path.is_file():
        inventory["exists"] = False
        inventory["read_error"] = "path_missing"
        return inventory, ()

    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        inventory["read_error"] = "csv_read_error"
        inventory["read_error_detail"] = exc.__class__.__name__
        return inventory, ()

    reader = csv.DictReader(text.splitlines())
    fieldnames = tuple(reader.fieldnames or ())
    inventory["observed_columns"] = list(fieldnames)
    missing_columns = _missing_csv_required_columns(fieldnames)
    inventory["missing_columns"] = list(missing_columns)
    inventory["volume_status"] = _volume_status_from_fieldnames(fieldnames)
    if missing_columns:
        inventory["duplicate_timestamp_status"] = "not_checked"
        inventory["missing_close_status"] = (
            "failed" if "close" in missing_columns else "not_checked"
        )
        inventory["monotonic_timestamp_status"] = "not_checked"
        return inventory, ()

    rows: list[_CryptoHistoryRow] = []
    source_values: set[str] = set()
    skipped_non_crypto_rows = 0
    skipped_symbol_rows = 0
    rows_read = 0
    missing_close_count = 0
    duplicate_timestamp_rows = 0
    non_monotonic_timestamp_rows = 0
    rows_per_symbol_before_normalization: dict[str, int] = {}
    timestamps_by_symbol: dict[str, set[datetime]] = {}
    previous_timestamp_by_symbol: dict[str, datetime] = {}
    try:
        for row in reader:
            if None in row:
                raise ValidationError("malformed CSV row.")
            rows_read += 1
            for source_field in ("source", "basis", "source_mode", "mode"):
                source_text = _csv_first_text(row, (source_field,))
                if source_text:
                    source_values.add(source_text)

            asset_class = _csv_first_text(row, ("asset_class",))
            if asset_class and asset_class.strip().lower() != "crypto":
                skipped_non_crypto_rows += 1
                continue

            symbol = _crypto_symbol(
                _required_text(
                    _csv_first_text(row, LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["symbol"]),
                    "symbol",
                ),
                "symbol",
            )
            if symbols is not None and symbol not in symbols:
                skipped_symbol_rows += 1
                continue

            timestamp = _csv_datetime(
                _csv_first_text(
                    row,
                    LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["timestamp"],
                )
            )
            close_text = _csv_first_text(
                row,
                LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["close"],
            )
            if not close_text:
                missing_close_count += 1
                raise ValidationError("missing close price.")
            open_text = _csv_first_text(
                row,
                LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["open"],
            )
            high_text = _csv_first_text(
                row,
                LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["high"],
            )
            low_text = _csv_first_text(
                row,
                LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["low"],
            )
            volume_text = _csv_first_text(
                row,
                LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["volume"],
            )
            seen_timestamps = timestamps_by_symbol.setdefault(symbol, set())
            if timestamp in seen_timestamps:
                duplicate_timestamp_rows += 1
            previous_timestamp = previous_timestamp_by_symbol.get(symbol)
            if previous_timestamp is not None and timestamp < previous_timestamp:
                non_monotonic_timestamp_rows += 1
            seen_timestamps.add(timestamp)
            previous_timestamp_by_symbol[symbol] = timestamp

            rows_per_symbol_before_normalization[symbol] = (
                rows_per_symbol_before_normalization.get(symbol, 0) + 1
            )
            rows.append(
                _CryptoHistoryRow(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=_csv_decimal(open_text, "open"),
                    high=_csv_decimal(high_text, "high"),
                    low=_csv_decimal(low_text, "low"),
                    close=_csv_decimal(close_text, "close"),
                    volume=volume_text,
                    input_path_index=input_path_index,
                    source_row_number=rows_read,
                )
            )
    except (ArithmeticError, ValidationError, ValueError) as exc:
        inventory["read_error"] = "csv_validation_error"
        inventory["read_error_detail"] = str(exc)
        inventory["rows_read"] = rows_read
        inventory["rows_per_symbol_before_normalization"] = dict(
            rows_per_symbol_before_normalization
        )
        inventory["missing_close_count"] = missing_close_count
        inventory["missing_close_status"] = "failed" if missing_close_count else "passed"
        inventory["duplicate_timestamp_rows"] = duplicate_timestamp_rows
        inventory["duplicate_rows_removed"] = duplicate_timestamp_rows
        inventory["duplicate_timestamp_status"] = (
            "failed" if duplicate_timestamp_rows else "passed"
        )
        inventory["duplicate_timestamp_status_before_normalization"] = (
            "failed" if duplicate_timestamp_rows else "passed"
        )
        inventory["duplicate_timestamp_status_after_normalization"] = "not_checked"
        inventory["non_monotonic_timestamp_rows"] = non_monotonic_timestamp_rows
        inventory["monotonic_timestamp_status_before_normalization"] = (
            "failed" if non_monotonic_timestamp_rows else "passed"
        )
        inventory["monotonic_timestamp_status"] = (
            "failed" if non_monotonic_timestamp_rows else "passed"
        )
        return inventory, ()

    normalized_rows = _normalize_crypto_history_rows(tuple(rows))
    inventory["rows_read"] = rows_read
    inventory["skipped_non_crypto_rows"] = skipped_non_crypto_rows
    inventory["skipped_symbol_rows"] = skipped_symbol_rows
    inventory["rows_per_symbol_before_normalization"] = dict(
        rows_per_symbol_before_normalization
    )
    inventory["source_values"] = sorted(source_values)
    inventory["missing_close_count"] = missing_close_count
    inventory["missing_close_status"] = "failed" if missing_close_count else "passed"
    inventory["duplicate_timestamp_rows"] = duplicate_timestamp_rows
    inventory["duplicate_timestamp_status"] = (
        "passed"
    )
    inventory["duplicate_timestamp_status_before_normalization"] = (
        "failed" if duplicate_timestamp_rows else "passed"
    )
    inventory["duplicate_timestamp_status_after_normalization"] = "passed"
    inventory["non_monotonic_timestamp_rows"] = non_monotonic_timestamp_rows
    inventory["monotonic_timestamp_status_before_normalization"] = (
        "failed" if non_monotonic_timestamp_rows else "passed"
    )
    inventory["monotonic_timestamp_status"] = "passed"
    _apply_normalized_rows_to_inventory(inventory, normalized_rows)
    inventory["fixture_source_detected"] = _object_contains_source_marker(inventory)
    return inventory, tuple(rows)


def _normalize_crypto_history_rows(
    rows: Sequence[_CryptoHistoryRow],
) -> tuple[_CryptoHistoryRow, ...]:
    selected: dict[tuple[str, datetime], _CryptoHistoryRow] = {}
    for row in rows:
        selected[(row.symbol, row.timestamp)] = row
    return tuple(
        sorted(
            selected.values(),
            key=lambda row: (row.symbol, row.timestamp),
        )
    )


def _apply_normalized_rows_to_inventory(
    inventory: dict[str, object],
    normalized_rows: Sequence[_CryptoHistoryRow],
) -> None:
    rows_per_symbol = _rows_per_symbol_from_history_rows(normalized_rows)
    rows_before = _mapping(inventory.get("rows_per_symbol_before_normalization"))
    duplicate_rows_removed = _duplicate_rows_removed_per_symbol(
        {str(symbol): int(count or 0) for symbol, count in rows_before.items()},
        rows_per_symbol,
    )
    inventory["usable_rows"] = len(normalized_rows)
    inventory["symbols"] = sorted(rows_per_symbol)
    inventory["rows_per_symbol"] = rows_per_symbol
    inventory["rows_per_symbol_after_normalization"] = dict(rows_per_symbol)
    inventory["duplicate_rows_removed_per_symbol"] = duplicate_rows_removed
    inventory["duplicate_rows_removed"] = sum(duplicate_rows_removed.values())
    inventory["date_range_per_symbol"] = _date_range_per_symbol_from_history_rows(
        normalized_rows
    )


def _write_normalized_crypto_history_csv(
    rows: Sequence[_CryptoHistoryRow],
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=("timestamp", "symbol", "open", "high", "low", "close", "volume"),
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "timestamp": row.timestamp.isoformat(),
                "symbol": row.symbol,
                "open": str(row.open),
                "high": str(row.high),
                "low": str(row.low),
                "close": str(row.close),
                "volume": row.volume,
            }
        )
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    try:
        temporary.write_text(buffer.getvalue(), encoding="utf-8")
        temporary.replace(output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output_path


def _real_data_probe_packet(
    packet: Mapping[str, object],
    *,
    csv_paths: tuple[Path, ...],
    inventories: tuple[Mapping[str, object], ...],
    assumptions: CryptoEvidenceAssumptions,
    blocking_reasons: tuple[str, ...],
    data_inventory: Mapping[str, object] | None = None,
) -> dict[str, object]:
    probe = dict(packet)
    raw_decision = str(probe.get("no_submit_decision", ""))
    if data_inventory is None:
        data_inventory = _data_inventory_payload(
            csv_paths=csv_paths,
            inventories=inventories,
            assumptions=assumptions,
            blocking_reasons=blocking_reasons,
        )

    probe["record_type"] = "crypto_strategy_real_data_evidence_probe_packet"
    probe["battery_no_submit_decision"] = raw_decision
    probe["data_path"] = str(csv_paths[0]) if len(csv_paths) == 1 else ""
    probe["data_paths"] = [str(path) for path in csv_paths]
    probe["input_history_path"] = str(csv_paths[0]) if len(csv_paths) == 1 else ""
    probe["input_history_paths"] = [str(path) for path in csv_paths]
    probe["input_paths"] = list(data_inventory["input_paths"])
    probe["normalized_output_path"] = str(
        data_inventory.get("normalized_output_path", "")
    )
    probe["data_inventory"] = data_inventory
    probe["symbols_required"] = list(data_inventory["symbols_required"])
    probe["required_symbols"] = list(data_inventory["symbols_required"])
    probe["symbols_found"] = list(data_inventory["symbols_found"])
    probe["symbols_missing"] = list(data_inventory["symbols_missing"])
    probe["symbols_evaluated"] = list(assumptions.candidate_symbols)
    probe["rows_per_symbol"] = dict(data_inventory["rows_per_symbol"])
    probe["rows_per_symbol_before_normalization"] = dict(
        data_inventory["rows_per_symbol_before_normalization"]
    )
    probe["rows_per_symbol_after_normalization"] = dict(
        data_inventory["rows_per_symbol_after_normalization"]
    )
    probe["duplicate_rows_removed_per_symbol"] = dict(
        data_inventory["duplicate_rows_removed_per_symbol"]
    )
    probe["date_range_per_symbol"] = dict(data_inventory["date_range_per_symbol"])
    probe["missing_columns"] = _inventory_missing_columns(inventories)
    probe["required_columns"] = list(LOCAL_HISTORICAL_CRYPTO_REQUIRED_COLUMNS)
    probe["optional_columns"] = list(LOCAL_HISTORICAL_CRYPTO_OPTIONAL_COLUMNS)
    probe["required_minimum_rows"] = data_inventory["required_minimum_rows"]
    probe["required_minimum_span"] = data_inventory["required_minimum_span"]
    probe["schema_validation_status"] = data_inventory["schema_validation_status"]
    probe["duplicate_timestamp_status"] = data_inventory[
        "duplicate_timestamp_status"
    ]
    probe["duplicate_timestamp_status_after_normalization"] = data_inventory[
        "duplicate_timestamp_status_after_normalization"
    ]
    probe["missing_close_status"] = data_inventory["missing_close_status"]
    probe["monotonic_timestamp_status"] = data_inventory[
        "monotonic_timestamp_status"
    ]
    probe["volume_status"] = data_inventory["volume_status"]
    probe["required_lookback_window"] = _required_lookback_window(assumptions)
    probe["acceptable_local_input_formats"] = list(
        ACCEPTABLE_LOCAL_CRYPTO_HISTORY_FORMATS
    )
    coverage_classification = _history_coverage_classification(data_inventory)
    if coverage_classification == "sufficient_real_crypto_history":
        strategies_evaluated = _strategies_evaluated(probe)
    else:
        strategies_evaluated = []
        probe["benchmark_comparison"] = {}
        probe["evidence_table"] = []
        probe["candidate_evaluations"] = []
    probe["strategies_evaluated"] = strategies_evaluated
    probe["strategy_candidates_evaluated"] = strategies_evaluated
    probe["risk_limits_considered"] = _risk_limits_considered(assumptions)
    probe["drawdown_threshold"] = _decimal_text(assumptions.max_test_drawdown)
    probe["benchmark_underperformance_threshold"] = _decimal_text(
        assumptions.min_test_excess_return_vs_buy_hold
    )

    classification = classify_crypto_strategy_no_submit_packet(probe)
    if (
        coverage_classification == "insufficient_real_crypto_history"
        or blocking_reasons
    ):
        classification = "insufficient_real_crypto_history"
    probe["classification"] = coverage_classification
    probe["no_submit_classification"] = classification
    probe["no_submit_decision"] = classification
    probe["paper_planning_eligibility"] = _paper_planning_eligibility(
        coverage_classification=coverage_classification,
        strategy_classification=classification,
        selected_candidate=probe.get("selected_candidate"),
    )
    reason = _classification_reason(
        probe,
        coverage_classification=coverage_classification,
        classification=classification,
        blocking_reasons=tuple(_string_sequence(data_inventory.get("blocking_reasons"))),
    )
    probe["reason"] = reason
    probe["reason_for_classification"] = reason
    if coverage_classification == "insufficient_real_crypto_history":
        probe["selected_candidate"] = None
    probe["selected_candidate_if_any"] = probe.get("selected_candidate")
    probe["next_safe_ingestion_action"] = _next_safe_ingestion_action(
        coverage_classification
    )
    probe["next_safe_data_refresh_action"] = probe["next_safe_ingestion_action"]
    if coverage_classification == "insufficient_real_crypto_history":
        probe["next_safe_operator_action"] = probe["next_safe_ingestion_action"]

    validation_errors = validate_crypto_strategy_no_submit_packet(probe)
    probe["validation_status"] = "passed" if not validation_errors else "failed"
    probe["validation_errors"] = validation_errors
    return probe


def _data_inventory_payload(
    *,
    csv_paths: tuple[Path, ...],
    inventories: tuple[Mapping[str, object], ...],
    assumptions: CryptoEvidenceAssumptions,
    blocking_reasons: tuple[str, ...],
    normalized_rows: Sequence[_CryptoHistoryRow] = (),
    normalized_output_path: str = "",
) -> dict[str, object]:
    required_symbols = list(assumptions.candidate_symbols)
    normalized_row_tuple = tuple(normalized_rows)
    rows_per_symbol_before = _aggregate_rows_per_symbol_before_normalization(
        inventories
    )
    if normalized_row_tuple:
        rows_per_symbol = _rows_per_symbol_from_history_rows(normalized_row_tuple)
        date_range_per_symbol = _date_range_per_symbol_from_history_rows(
            normalized_row_tuple
        )
    else:
        rows_per_symbol = _aggregate_rows_per_symbol(inventories)
        date_range_per_symbol = _aggregate_date_range_per_symbol(inventories)
    if not rows_per_symbol_before:
        rows_per_symbol_before = dict(rows_per_symbol)
    rows_per_symbol_after = _rows_with_required_symbol_zeros(
        rows_per_symbol,
        required_symbols,
    )
    duplicate_rows_removed = _duplicate_rows_removed_per_symbol(
        rows_per_symbol_before,
        rows_per_symbol_after,
    )
    required_set = set(required_symbols)
    symbols_found = [
        symbol for symbol in required_symbols if rows_per_symbol.get(symbol, 0) > 0
    ]
    symbols_found.extend(
        symbol
        for symbol in sorted(rows_per_symbol)
        if symbol not in required_set and rows_per_symbol[symbol] > 0
    )
    symbols_missing = [
        symbol for symbol in required_symbols if symbol not in set(symbols_found)
    ]
    required_minimum_rows = assumptions.min_history_rows_per_symbol
    required_minimum_span = _required_minimum_span(assumptions)
    missing_columns = _inventory_missing_columns(inventories)
    computed_blocking_reasons: list[str] = list(blocking_reasons)
    if symbols_missing:
        computed_blocking_reasons.append("missing_required_symbols")
    if any(
        rows_per_symbol.get(symbol, 0) < required_minimum_rows
        for symbol in required_symbols
    ):
        computed_blocking_reasons.append("insufficient_rows")
    if any(
        not _symbol_span_is_sufficient(
            date_range_per_symbol.get(symbol),
            assumptions,
        )
        for symbol in required_symbols
    ):
        computed_blocking_reasons.append("insufficient_date_span")
    if missing_columns:
        computed_blocking_reasons.append("missing_required_columns")
    if _any_inventory_status(inventories, "missing_close_status", "failed"):
        computed_blocking_reasons.append("missing_close_values")
    if _object_contains_source_marker(inventories):
        computed_blocking_reasons.append("fixture_only_history")

    blocking = list(dict.fromkeys(computed_blocking_reasons))
    schema_status = "failed" if missing_columns or _inventory_read_errors(inventories) else "passed"
    duplicate_timestamp_status = (
        "passed" if normalized_row_tuple or rows_per_symbol else "not_checked"
    )
    missing_close_status = _combined_status(inventories, "missing_close_status")
    if "missing_close_values" in blocking:
        missing_close_status = "failed"
    monotonic_timestamp_status = (
        "passed" if normalized_row_tuple or rows_per_symbol else "not_checked"
    )
    return {
        "input_paths": [str(path) for path in csv_paths],
        "normalized_output_path": normalized_output_path,
        "records": [dict(inventory) for inventory in inventories],
        "symbols_required": required_symbols,
        "required_symbols": required_symbols,
        "symbols_found": symbols_found,
        "symbols_missing": symbols_missing,
        "rows_per_symbol": rows_per_symbol,
        "rows_per_symbol_before_normalization": _rows_with_required_symbol_zeros(
            rows_per_symbol_before,
            required_symbols,
        ),
        "rows_per_symbol_after_normalization": rows_per_symbol_after,
        "duplicate_rows_removed_per_symbol": duplicate_rows_removed,
        "date_range_per_symbol": date_range_per_symbol,
        "required_minimum_rows": required_minimum_rows,
        "required_minimum_span": required_minimum_span,
        "required_columns": list(LOCAL_HISTORICAL_CRYPTO_REQUIRED_COLUMNS),
        "optional_columns": list(LOCAL_HISTORICAL_CRYPTO_OPTIONAL_COLUMNS),
        "required_lookback_window": _required_lookback_window(assumptions),
        "acceptable_local_input_formats": list(ACCEPTABLE_LOCAL_CRYPTO_HISTORY_FORMATS),
        "schema_validation_status": schema_status,
        "duplicate_timestamp_status": duplicate_timestamp_status,
        "duplicate_timestamp_status_after_normalization": duplicate_timestamp_status,
        "missing_close_status": missing_close_status,
        "monotonic_timestamp_status": monotonic_timestamp_status,
        "volume_status": _combined_volume_status(inventories),
        "normalization_tie_breaker": (
            "last valid row by input path order, then CSV source row order, "
            "per normalized symbol/timestamp"
        ),
        "blocking_reasons": blocking,
        "fixture_source_detected": _object_contains_source_marker(inventories),
    }


def _classification_reason(
    packet: Mapping[str, object],
    *,
    coverage_classification: str,
    classification: str,
    blocking_reasons: tuple[str, ...],
) -> str:
    if blocking_reasons:
        return (
            "local historical crypto coverage is blocked: "
            + ", ".join(blocking_reasons)
        )
    if coverage_classification == "sufficient_real_crypto_history" and classification == "reject_candidate":
        reasons = ", ".join(_string_sequence(packet.get("rejection_reasons")))
        return f"local history is sufficient, but all evaluated candidates failed promotion gates: {reasons}"
    if _object_contains_source_marker(packet.get("data_inventory")) or _object_contains_source_marker(
        packet.get("data_source")
    ):
        return "fixture-only or synthetic data cannot support real-data promotion."
    if classification == "promote_to_no_submit_plan":
        return (
            "selected candidate passed the drawdown, cash, buy-and-hold, and "
            "equal-weight basket gates on local historical crypto data."
        )
    if classification == "reject_candidate":
        reasons = ", ".join(_string_sequence(packet.get("rejection_reasons")))
        return f"all evaluated candidates failed promotion gates: {reasons}"
    if classification == "insufficient_real_crypto_history":
        return "no non-fixture local history had enough usable rows for promotion."
    return "candidate evidence remains inconclusive; keep researching offline."


def _next_safe_ingestion_action(classification: str) -> str:
    if classification == "insufficient_real_crypto_history":
        return (
            "Add or refresh local read-only crypto OHLC CSV history for BTCUSD, "
            "ETHUSD, SOLUSD, and ADAUSD under runs/operator_input/ or a "
            "runs/crypto_universe_refresh/<label>/history/ directory, then rerun "
            "this probe; no broker read or mutation is authorized by this packet."
        )
    if classification == "sufficient_real_crypto_history":
        return "Review the local evidence packet offline before any separate planning milestone."
    if classification == "promote_to_no_submit_plan":
        return "Open a separate no-submit planning milestone using this packet."
    if classification == "reject_candidate":
        return "Keep the same small candidate set in offline research."
    return "Extend local history or adjust one offline hypothesis before rerunning."


def _empty_csv_inventory(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": True,
        "format": "csv",
        "observed_columns": [],
        "required_columns": list(LOCAL_HISTORICAL_CRYPTO_REQUIRED_COLUMNS),
        "missing_columns": [],
        "rows_read": 0,
        "usable_rows": 0,
        "skipped_non_crypto_rows": 0,
        "skipped_symbol_rows": 0,
        "symbols": [],
        "rows_per_symbol": {},
        "rows_per_symbol_before_normalization": {},
        "rows_per_symbol_after_normalization": {},
        "date_range_per_symbol": {},
        "source_values": [],
        "fixture_source_detected": False,
        "duplicate_timestamp_rows": 0,
        "duplicate_rows_removed": 0,
        "duplicate_rows_removed_per_symbol": {},
        "duplicate_timestamp_status": "not_checked",
        "duplicate_timestamp_status_before_normalization": "not_checked",
        "duplicate_timestamp_status_after_normalization": "not_checked",
        "non_monotonic_timestamp_rows": 0,
        "monotonic_timestamp_status_before_normalization": "not_checked",
        "missing_close_count": 0,
        "missing_close_status": "not_checked",
        "monotonic_timestamp_status": "not_checked",
        "volume_status": "not_checked",
        "volume_required_for_strategy": False,
        "strategies_can_run_without_volume": True,
        "read_error": "",
    }


def _missing_csv_required_columns(fieldnames: Sequence[str]) -> tuple[str, ...]:
    lookup = {field.strip().lower() for field in fieldnames if field.strip()}
    missing: list[str] = []
    for canonical, aliases in LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES.items():
        if canonical in LOCAL_HISTORICAL_CRYPTO_OPTIONAL_COLUMNS:
            continue
        if not any(alias.lower() in lookup for alias in aliases):
            missing.append(canonical)
    return tuple(missing)


def _volume_status_from_fieldnames(fieldnames: Sequence[str]) -> str:
    lookup = {field.strip().lower() for field in fieldnames if field.strip()}
    has_volume = any(
        alias.lower() in lookup
        for alias in LOCAL_HISTORICAL_CRYPTO_COLUMN_ALIASES["volume"]
    )
    if has_volume:
        return "available"
    return "absent_strategy_compatible"


def _csv_first_text(row: Mapping[str, object], aliases: Sequence[str]) -> str:
    lookup = {str(key).strip().lower(): key for key in row}
    for alias in aliases:
        key = lookup.get(alias.lower())
        if key is None:
            continue
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _csv_datetime(value: str) -> datetime:
    text = _required_text(value, "timestamp")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("timestamp must be ISO formatted.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _csv_decimal(value: str, field_name: str) -> Decimal:
    text = _required_text(value, field_name)
    try:
        return Decimal(text)
    except ArithmeticError as exc:
        raise ValidationError(f"{field_name} must be decimal text.") from exc


def _optional_symbol_filter(symbols: Iterable[str] | None) -> set[str] | None:
    if symbols is None:
        return None
    return set(_candidate_symbol_tuple(symbols))


def _path_tuple(paths: Iterable[Path | str] | Path | str) -> tuple[Path, ...]:
    if isinstance(paths, (str, Path)):
        return (Path(paths),)
    if isinstance(paths, bytes):
        raise ValidationError("csv_paths must be paths, not bytes.")
    return tuple(Path(path) for path in paths)


def _rows_per_symbol_from_bars(
    bars_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]],
) -> dict[str, int]:
    return {symbol: len(bars) for symbol, bars in sorted(bars_by_symbol.items())}


def _date_range_per_symbol_from_bars(
    bars_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]],
) -> dict[str, dict[str, str]]:
    return {
        symbol: {
            "start": bars[0].timestamp.isoformat() if bars else "",
            "end": bars[-1].timestamp.isoformat() if bars else "",
        }
        for symbol, bars in sorted(bars_by_symbol.items())
    }


def _has_duplicate_symbol_timestamps(bars: Sequence[CryptoEvidenceBar]) -> bool:
    seen: set[tuple[str, datetime]] = set()
    for bar in bars:
        key = (bar.symbol, bar.timestamp)
        if key in seen:
            return True
        seen.add(key)
    return False


def _rows_per_symbol_from_data_summary(value: object) -> dict[str, int]:
    rows: dict[str, int] = {}
    for item in _mapping_sequence(value):
        symbol = str(item.get("symbol", "")).strip()
        if symbol:
            rows[symbol] = int(item.get("bar_count") or 0)
    return rows


def _date_range_per_symbol_from_data_summary(
    value: object,
) -> dict[str, dict[str, str]]:
    ranges: dict[str, dict[str, str]] = {}
    for item in _mapping_sequence(value):
        symbol = str(item.get("symbol", "")).strip()
        if symbol:
            ranges[symbol] = {
                "start": str(item.get("first_bar_at", "")),
                "end": str(item.get("latest_bar_at", "")),
            }
    return ranges


def _inventory_missing_columns(
    inventories: Sequence[Mapping[str, object]],
) -> list[str]:
    missing = {
        column
        for inventory in inventories
        for column in _string_sequence(inventory.get("missing_columns"))
    }
    return [
        column for column in LOCAL_HISTORICAL_CRYPTO_REQUIRED_COLUMNS if column in missing
    ]


def _aggregate_rows_per_symbol(
    inventories: Sequence[Mapping[str, object]],
) -> dict[str, int]:
    rows: dict[str, int] = {}
    for inventory in inventories:
        for symbol, count in _mapping(inventory.get("rows_per_symbol")).items():
            symbol_text = str(symbol).strip()
            if symbol_text:
                rows[symbol_text] = rows.get(symbol_text, 0) + int(count or 0)
    return {symbol: rows[symbol] for symbol in sorted(rows)}


def _aggregate_rows_per_symbol_before_normalization(
    inventories: Sequence[Mapping[str, object]],
) -> dict[str, int]:
    rows: dict[str, int] = {}
    for inventory in inventories:
        source = _mapping(inventory.get("rows_per_symbol_before_normalization"))
        if not source:
            source = _mapping(inventory.get("rows_per_symbol"))
        for symbol, count in source.items():
            symbol_text = str(symbol).strip()
            if symbol_text:
                rows[symbol_text] = rows.get(symbol_text, 0) + int(count or 0)
    return {symbol: rows[symbol] for symbol in sorted(rows)}


def _rows_with_required_symbol_zeros(
    rows: Mapping[str, int],
    required_symbols: Sequence[str],
) -> dict[str, int]:
    result = {str(symbol): int(rows.get(symbol, 0) or 0) for symbol in required_symbols}
    for symbol, count in rows.items():
        symbol_text = str(symbol).strip()
        if symbol_text and symbol_text not in result:
            result[symbol_text] = int(count or 0)
    return {symbol: result[symbol] for symbol in sorted(result)}


def _duplicate_rows_removed_per_symbol(
    rows_before: Mapping[str, int],
    rows_after: Mapping[str, int],
) -> dict[str, int]:
    symbols = sorted({*rows_before.keys(), *rows_after.keys()})
    return {
        symbol: max(int(rows_before.get(symbol, 0)) - int(rows_after.get(symbol, 0)), 0)
        for symbol in symbols
    }


def _rows_per_symbol_from_history_rows(
    rows: Sequence[_CryptoHistoryRow],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.symbol] = counts.get(row.symbol, 0) + 1
    return {symbol: counts[symbol] for symbol in sorted(counts)}


def _date_range_per_symbol_from_history_rows(
    rows: Sequence[_CryptoHistoryRow],
) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[_CryptoHistoryRow]] = {}
    for row in rows:
        grouped.setdefault(row.symbol, []).append(row)

    ranges: dict[str, dict[str, str]] = {}
    for symbol, symbol_rows in grouped.items():
        ordered = sorted(symbol_rows, key=lambda item: item.timestamp)
        start = ordered[0].timestamp.isoformat()
        end = ordered[-1].timestamp.isoformat()
        ranges[symbol] = {
            "start": start,
            "end": end,
            "span_hours": _span_hours_text(start, end),
        }
    return {symbol: ranges[symbol] for symbol in sorted(ranges)}


def _aggregate_date_range_per_symbol(
    inventories: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, str]]:
    ranges: dict[str, dict[str, str]] = {}
    for inventory in inventories:
        for symbol, raw_range in _mapping(inventory.get("date_range_per_symbol")).items():
            symbol_text = str(symbol).strip()
            if not symbol_text:
                continue
            range_map = _mapping(raw_range)
            start = str(range_map.get("start", "")).strip()
            end = str(range_map.get("end", "")).strip()
            if not start or not end:
                continue
            existing = ranges.setdefault(
                symbol_text,
                {"start": start, "end": end, "span_hours": "0"},
            )
            if start < existing["start"]:
                existing["start"] = start
            if end > existing["end"]:
                existing["end"] = end
    for item in ranges.values():
        item["span_hours"] = _span_hours_text(item["start"], item["end"])
    return {symbol: ranges[symbol] for symbol in sorted(ranges)}


def _required_minimum_span(
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    return {
        "hours": assumptions.min_history_span_hours,
        "iso8601": f"PT{assumptions.min_history_span_hours}H",
    }


def _symbol_span_is_sufficient(
    raw_range: object,
    assumptions: CryptoEvidenceAssumptions,
) -> bool:
    range_map = _mapping(raw_range)
    start = str(range_map.get("start", "")).strip()
    end = str(range_map.get("end", "")).strip()
    if not start or not end:
        return False
    return _datetime_span(start, end) >= timedelta(
        hours=assumptions.min_history_span_hours
    )


def _span_hours_text(start: str, end: str) -> str:
    span = _datetime_span(start, end)
    hours = Decimal(str(span.total_seconds())) / Decimal("3600")
    return _decimal_text(hours)


def _datetime_span(start: str, end: str) -> timedelta:
    try:
        start_dt = _csv_datetime(start)
        end_dt = _csv_datetime(end)
    except ValidationError:
        return timedelta(0)
    return max(end_dt - start_dt, timedelta(0))


def _inventory_read_errors(
    inventories: Sequence[Mapping[str, object]],
) -> tuple[str, ...]:
    return tuple(
        str(inventory.get("read_error"))
        for inventory in inventories
        if str(inventory.get("read_error", "")).strip()
    )


def _any_inventory_status(
    inventories: Sequence[Mapping[str, object]],
    field_name: str,
    expected: str,
) -> bool:
    return any(str(inventory.get(field_name, "")) == expected for inventory in inventories)


def _combined_status(
    inventories: Sequence[Mapping[str, object]],
    field_name: str,
) -> str:
    statuses = {
        str(inventory.get(field_name, "")).strip()
        for inventory in inventories
        if str(inventory.get(field_name, "")).strip()
    }
    if "failed" in statuses:
        return "failed"
    if "passed" in statuses:
        return "passed"
    return "not_checked"


def _combined_volume_status(
    inventories: Sequence[Mapping[str, object]],
) -> str:
    statuses = {
        str(inventory.get("volume_status", "")).strip()
        for inventory in inventories
        if str(inventory.get("volume_status", "")).strip()
    }
    if not statuses:
        return "not_checked"
    if statuses == {"available"}:
        return "available"
    if statuses == {"absent_strategy_compatible"}:
        return "absent_strategy_compatible"
    if "available" in statuses and "absent_strategy_compatible" in statuses:
        return "mixed_strategy_compatible"
    if "not_checked" in statuses:
        return "not_checked"
    return sorted(statuses)[0]


def _history_coverage_classification(data_inventory: Mapping[str, object]) -> str:
    if _string_sequence(data_inventory.get("blocking_reasons")):
        return "insufficient_real_crypto_history"
    if str(data_inventory.get("schema_validation_status", "")) != "passed":
        return "insufficient_real_crypto_history"
    if str(data_inventory.get("duplicate_timestamp_status", "")) != "passed":
        return "insufficient_real_crypto_history"
    if str(data_inventory.get("missing_close_status", "")) != "passed":
        return "insufficient_real_crypto_history"
    if str(data_inventory.get("monotonic_timestamp_status", "")) != "passed":
        return "insufficient_real_crypto_history"
    return "sufficient_real_crypto_history"


def _strategies_evaluated(packet: Mapping[str, object]) -> list[str]:
    return [
        str(item.get("strategy_id"))
        for item in _mapping_sequence(packet.get("strategy_candidates"))
        if str(item.get("strategy_id", "")).strip()
    ]


def _paper_planning_eligibility(
    *,
    coverage_classification: str,
    strategy_classification: str,
    selected_candidate: object,
) -> str:
    if (
        coverage_classification == "sufficient_real_crypto_history"
        and strategy_classification == "promote_to_no_submit_plan"
        and isinstance(selected_candidate, Mapping)
    ):
        return "eligible"
    return "not_eligible"


def _required_lookback_window(
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    specs = (*_strategy_specs(), *_diagnostic_repair_strategy_specs())
    max_lookback = max(max(spec.lookback, spec.fast_window, spec.slow_window) for spec in specs)
    return {
        "min_bars_per_symbol": assumptions.min_bars_per_symbol,
        "train_fraction": (
            f"{assumptions.train_fraction_numerator}/"
            f"{assumptions.train_fraction_denominator}"
        ),
        "max_strategy_lookback_bars": max_lookback,
        "minimum_operational_window": (
            "at least min_bars_per_symbol usable rows per evaluated symbol"
        ),
    }


def _risk_limits_considered(
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    return {
        "asset_class": "crypto",
        "direction": "long_only_or_cash",
        "shorting_allowed": False,
        "leverage_allowed": False,
        "max_test_drawdown": _decimal_text(assumptions.max_test_drawdown),
        "min_test_excess_return_vs_buy_hold": _decimal_text(
            assumptions.min_test_excess_return_vs_buy_hold
        ),
        "min_test_excess_return_vs_equal_weight_basket": "0",
        "min_test_total_return": _decimal_text(assumptions.min_test_total_return),
        "paper_max_notional": _decimal_text(assumptions.paper_max_notional),
        "max_paper_allocation_fraction": _decimal_text(
            assumptions.max_paper_allocation_fraction
        ),
    }


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _object_contains_source_marker(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_object_contains_source_marker(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_object_contains_source_marker(item) for item in value)
    text = str(value).strip().lower()
    return any(marker in text for marker in REAL_DATA_PROMOTION_BLOCKING_SOURCE_MARKERS)


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
    test_excess_return_vs_basket = (
        _decimal_from_text(test_metrics["total_return"]) - basket_test_return
        if basket_test_return is not None
        else None
    )
    decision, reasons = _candidate_decision(
        test_metrics=test_metrics,
        test_excess_return=test_excess_return,
        test_excess_return_vs_basket=test_excess_return_vs_basket,
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
            "test_excess_return_vs_equal_weight_basket": _decimal_text(
                test_excess_return_vs_basket
            )
            if test_excess_return_vs_basket is not None
            else "",
        },
    }


def _candidate_decision(
    *,
    test_metrics: Mapping[str, object],
    test_excess_return: Decimal,
    test_excess_return_vs_basket: Decimal | None,
    assumptions: CryptoEvidenceAssumptions,
) -> tuple[str, tuple[str, ...]]:
    test_total_return = _decimal_from_text(test_metrics.get("total_return", "0"))
    test_max_drawdown = _decimal_from_text(test_metrics.get("max_drawdown", "0"))
    reasons: list[str] = []

    if test_max_drawdown > assumptions.max_test_drawdown:
        reasons.append("high_drawdown")
    if test_excess_return <= assumptions.min_test_excess_return_vs_buy_hold:
        reasons.append("benchmark_underperformance")
    if (
        test_excess_return_vs_basket is not None
        and test_excess_return_vs_basket <= _ZERO
    ):
        reasons.append("basket_underperformance")
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
                "strategy_family": evaluation.get("strategy_family", ""),
                "candidate_origin": evaluation.get("candidate_origin", "current"),
                "candidate_decision": evaluation.get("candidate_decision", ""),
                "gate_decision_before_repair_guard": evaluation.get(
                    "gate_decision_before_repair_guard",
                    "",
                ),
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
                "test_excess_return_vs_equal_weight_basket": comparison.get(
                    "test_excess_return_vs_equal_weight_basket",
                    "",
                ),
                "rejection_reasons": evaluation.get("rejection_reasons", []),
                "promotion_blockers": evaluation.get("promotion_blockers", []),
            }
        )
    return rows


def _diagnostic_repair_evaluations(
    *,
    bars_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]],
    assumptions: CryptoEvidenceAssumptions,
    buy_hold_by_symbol: Mapping[str, Mapping[str, object]],
    basket_record: Mapping[str, object],
    base_rank_count: int,
) -> list[dict[str, object]]:
    evaluations: list[dict[str, object]] = []
    for symbol in assumptions.candidate_symbols:
        symbol_bars = bars_by_symbol.get(symbol, ())
        for spec in _diagnostic_repair_strategy_specs():
            evaluation = _candidate_evaluation(
                symbol=symbol,
                spec=spec,
                bars=symbol_bars,
                assumptions=assumptions,
                buy_hold_record=buy_hold_by_symbol.get(symbol, {}),
                basket_record=basket_record,
            )
            evaluations.append(_repair_guarded_evaluation(evaluation))

    ranked = _ranked_evaluations(evaluations)
    for repair_rank, evaluation in enumerate(ranked, start=1):
        evaluation["repair_rank"] = repair_rank
        evaluation["rank"] = base_rank_count + repair_rank
    return ranked


def _repair_guarded_evaluation(
    evaluation: Mapping[str, object],
) -> dict[str, object]:
    item = dict(evaluation)
    gate_decision = str(item.get("candidate_decision", ""))
    gate_reasons = _string_list(item.get("rejection_reasons"))
    item["candidate_origin"] = "diagnostic_repair"
    item["repair_added"] = True
    item["repair_rationale"] = (
        "Existing one-hour and four-hour rules overtraded the positive test "
        "window; this one-day trend repair probes lower-turnover risk-on "
        "exposure without authorizing promotion on the same dataset."
    )
    item["gate_decision_before_repair_guard"] = gate_decision
    item["gate_rejection_reasons_before_repair_guard"] = gate_reasons
    item["promotion_blockers"] = [DIAGNOSTIC_REPAIR_PROMOTION_BLOCKER]
    if gate_decision == "promote_to_no_submit_plan":
        item["candidate_decision"] = "reject_candidate"
        item["rejection_reasons"] = [DIAGNOSTIC_REPAIR_PROMOTION_BLOCKER]
    return item


def _diagnostic_repair_strategy_specs() -> tuple[_StrategySpec, ...]:
    return (
        _StrategySpec(
            strategy_id="trend_momentum_24h_repair",
            strategy_family="trend_momentum",
            lookback=24,
        ),
    )


def _diagnostic_repair_candidates_payload() -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for spec in _diagnostic_repair_strategy_specs():
        payload = _strategy_spec_payload(spec)
        payload.update(
            {
                "candidate_origin": "diagnostic_repair",
                "repair_type": "one_day_trend_momentum_low_turnover",
                "repair_rationale": (
                    "Probe a 24-hour lookback after diagnostics showed short "
                    "lookbacks overtrading during a broad positive test regime."
                ),
                "promotion_scope": "diagnostic_only_until_fresh_oos",
                "promotion_blocker": DIAGNOSTIC_REPAIR_PROMOTION_BLOCKER,
            }
        )
        candidates.append(payload)
    return candidates


def _strategy_failure_diagnostics(
    *,
    data_source: str,
    symbol_summaries: Sequence[Mapping[str, object]],
    benchmark_records: Sequence[Mapping[str, object]],
    ranked_evaluations: Sequence[Mapping[str, object]],
    repair_evaluations: Sequence[Mapping[str, object]],
    walk_forward_windows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    repaired_candidates = _diagnostic_repair_candidates_payload()
    return {
        "data_source": data_source,
        "symbols_evaluated": [
            str(item.get("symbol", ""))
            for item in symbol_summaries
            if str(item.get("symbol", "")).strip()
        ],
        "rows_per_symbol": {
            str(item.get("symbol", "")): int(item.get("bar_count", 0))
            for item in symbol_summaries
            if str(item.get("symbol", "")).strip()
        },
        "date_range": _date_range_from_symbol_summaries(symbol_summaries),
        "benchmark_returns": _benchmark_returns(benchmark_records),
        "candidate_failure_summary": _candidate_diagnostic_summary(
            ranked_evaluations
        ),
        "candidate_failure_summary_by_symbol": _diagnostic_group_summaries(
            ranked_evaluations,
            "symbol",
        ),
        "candidate_failure_summary_by_strategy_type": _diagnostic_group_summaries(
            ranked_evaluations,
            "strategy_family",
        ),
        "rejection_reasons_by_candidate": _rejection_reasons_by_candidate(
            ranked_evaluations
        ),
        "trade_count_by_candidate": _trade_count_by_candidate(ranked_evaluations),
        "max_drawdown_by_candidate": _max_drawdown_by_candidate(ranked_evaluations),
        "cash_and_buy_hold_underperformance_by_candidate": (
            _underperformance_by_candidate(ranked_evaluations)
        ),
        "train_test_windows": [dict(window) for window in walk_forward_windows],
        "market_regime_summary": _market_regime_summary(benchmark_records),
        "drawdown_summary": _drawdown_summary(ranked_evaluations),
        "repair_added": bool(repaired_candidates),
        "repaired_candidates": repaired_candidates,
        "repair_candidate_summary": _candidate_diagnostic_summary(
            repair_evaluations
        ),
        "repair_rejection_reasons_by_candidate": _rejection_reasons_by_candidate(
            repair_evaluations
        ),
    }


def _date_range_from_symbol_summaries(
    symbol_summaries: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    ranges: dict[str, dict[str, object]] = {}
    for item in symbol_summaries:
        symbol = str(item.get("symbol", "")).strip()
        if not symbol:
            continue
        ranges[symbol] = {
            "start": item.get("first_bar_at", ""),
            "end": item.get("latest_bar_at", ""),
            "bar_count": item.get("bar_count", 0),
        }
    return ranges


def _benchmark_returns(
    benchmark_records: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    returns: dict[str, dict[str, object]] = {}
    for record in benchmark_records:
        benchmark_id = str(record.get("benchmark_id", "")).strip()
        symbol = str(record.get("symbol", "")).strip()
        if not benchmark_id:
            continue
        key = benchmark_id if benchmark_id == "cash_no_trade" else f"{benchmark_id}:{symbol}"
        windows = _mapping(record.get("windows"))
        train = _mapping(windows.get("train"))
        test = _mapping(windows.get("test"))
        returns[key] = {
            "benchmark_id": benchmark_id,
            "symbol": symbol,
            "status": record.get("status", ""),
            "train_total_return": train.get("total_return", ""),
            "test_total_return": test.get("total_return", ""),
            "test_max_drawdown": test.get("max_drawdown", ""),
        }
    return returns


def _candidate_diagnostic_summary(
    evaluations: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    decision_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for item in evaluations:
        _increment_count(decision_counts, str(item.get("candidate_decision", "")))
        for reason in _string_sequence(item.get("rejection_reasons")):
            _increment_count(reason_counts, reason)

    top = evaluations[0] if evaluations else {}
    top_test_metrics = _mapping(_mapping(top.get("windows")).get("test"))
    top_comparison = _mapping(top.get("benchmark_comparison"))
    return {
        "candidate_count": len(evaluations),
        "decision_counts": decision_counts,
        "rejection_reason_counts": reason_counts,
        "all_candidates_rejected": bool(evaluations)
        and all(
            str(item.get("candidate_decision", "")) != "promote_to_no_submit_plan"
            for item in evaluations
        ),
        "top_candidate_id": top.get("candidate_id", ""),
        "top_candidate_symbol": top.get("symbol", ""),
        "top_candidate_strategy_id": top.get("strategy_id", ""),
        "top_candidate_test_total_return": top_test_metrics.get("total_return", ""),
        "top_candidate_test_max_drawdown": top_test_metrics.get("max_drawdown", ""),
        "top_candidate_test_trade_count": top_test_metrics.get("trade_count", ""),
        "top_candidate_test_excess_return_vs_buy_hold": top_comparison.get(
            "test_excess_return_vs_buy_hold",
            "",
        ),
        "top_candidate_test_excess_return_vs_equal_weight_basket": top_comparison.get(
            "test_excess_return_vs_equal_weight_basket",
            "",
        ),
        "top_candidate_rejection_reasons": list(
            _string_sequence(top.get("rejection_reasons"))
        ),
    }


def _diagnostic_group_summaries(
    evaluations: Sequence[Mapping[str, object]],
    group_key: str,
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for item in evaluations:
        key = str(item.get(group_key, "")).strip()
        if not key:
            key = "unknown"
        grouped.setdefault(key, []).append(item)

    summaries: dict[str, dict[str, object]] = {}
    for key, items in grouped.items():
        reason_counts: dict[str, int] = {}
        total_trade_count = 0
        max_drawdown = _ZERO
        for item in items:
            metrics = _mapping(_mapping(item.get("windows")).get("test"))
            total_trade_count += int(metrics.get("trade_count", 0))
            drawdown = _decimal_from_text(metrics.get("max_drawdown", "0"))
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            for reason in _string_sequence(item.get("rejection_reasons")):
                _increment_count(reason_counts, reason)
        best = items[0]
        best_metrics = _mapping(_mapping(best.get("windows")).get("test"))
        best_comparison = _mapping(best.get("benchmark_comparison"))
        summaries[key] = {
            "candidate_count": len(items),
            "rejection_reason_counts": reason_counts,
            "total_test_trade_count": total_trade_count,
            "average_test_trade_count": _decimal_text(
                Decimal(total_trade_count) / Decimal(len(items))
            ),
            "max_test_drawdown": _decimal_text(max_drawdown),
            "best_candidate_id": best.get("candidate_id", ""),
            "best_candidate_test_total_return": best_metrics.get(
                "total_return",
                "",
            ),
            "best_candidate_test_excess_return_vs_buy_hold": best_comparison.get(
                "test_excess_return_vs_buy_hold",
                "",
            ),
        }
    return summaries


def _rejection_reasons_by_candidate(
    evaluations: Sequence[Mapping[str, object]],
) -> dict[str, list[str]]:
    return {
        str(item.get("candidate_id", "")): list(
            _string_sequence(item.get("rejection_reasons"))
        )
        for item in evaluations
        if str(item.get("candidate_id", "")).strip()
    }


def _trade_count_by_candidate(
    evaluations: Sequence[Mapping[str, object]],
) -> dict[str, int]:
    return {
        str(item.get("candidate_id", "")): int(
            _mapping(_mapping(item.get("windows")).get("test")).get("trade_count", 0)
        )
        for item in evaluations
        if str(item.get("candidate_id", "")).strip()
    }


def _max_drawdown_by_candidate(
    evaluations: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    return {
        str(item.get("candidate_id", "")): str(
            _mapping(_mapping(item.get("windows")).get("test")).get(
                "max_drawdown",
                "",
            )
        )
        for item in evaluations
        if str(item.get("candidate_id", "")).strip()
    }


def _underperformance_by_candidate(
    evaluations: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for item in evaluations:
        candidate_id = str(item.get("candidate_id", "")).strip()
        if not candidate_id:
            continue
        metrics = _mapping(_mapping(item.get("windows")).get("test"))
        comparison = _mapping(item.get("benchmark_comparison"))
        test_return = _decimal_from_text(metrics.get("total_return", "0"))
        results[candidate_id] = {
            "test_total_return": metrics.get("total_return", ""),
            "cash_no_trade_test_total_return": comparison.get(
                "cash_no_trade_test_total_return",
                "0",
            ),
            "cash_underperformance": test_return <= _ZERO,
            "buy_hold_test_total_return": comparison.get(
                "buy_and_hold_test_total_return",
                "",
            ),
            "test_excess_return_vs_buy_hold": comparison.get(
                "test_excess_return_vs_buy_hold",
                "",
            ),
            "buy_hold_underperformance": _decimal_from_text(
                comparison.get("test_excess_return_vs_buy_hold", "0")
            )
            <= _ZERO,
            "equal_weight_basket_test_total_return": comparison.get(
                "equal_weight_basket_test_total_return",
                "",
            ),
            "test_excess_return_vs_equal_weight_basket": comparison.get(
                "test_excess_return_vs_equal_weight_basket",
                "",
            ),
            "equal_weight_basket_underperformance": (
                bool(
                    str(
                        comparison.get(
                            "test_excess_return_vs_equal_weight_basket",
                            "",
                        )
                    ).strip()
                )
                and _decimal_from_text(
                    comparison.get(
                        "test_excess_return_vs_equal_weight_basket",
                        "0",
                    )
                )
                <= _ZERO
            ),
        }
    return results


def _market_regime_summary(
    benchmark_records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    buy_hold_items: list[dict[str, object]] = []
    test_returns: list[Decimal] = []
    train_returns: list[Decimal] = []
    for record in benchmark_records:
        if record.get("benchmark_id") != "buy_and_hold":
            continue
        windows = _mapping(record.get("windows"))
        train = _mapping(windows.get("train"))
        test = _mapping(windows.get("test"))
        train_return = _decimal_from_text(train.get("total_return", "0"))
        test_return = _decimal_from_text(test.get("total_return", "0"))
        train_returns.append(train_return)
        test_returns.append(test_return)
        buy_hold_items.append(
            {
                "symbol": record.get("symbol", ""),
                "train_total_return": train.get("total_return", ""),
                "test_total_return": test.get("total_return", ""),
                "train_regime": _return_regime(train_return),
                "test_regime": _return_regime(test_return),
                "test_max_drawdown": test.get("max_drawdown", ""),
            }
        )

    return {
        "by_symbol": buy_hold_items,
        "train_regime": _aggregate_return_regime(train_returns),
        "test_regime": _aggregate_return_regime(test_returns),
        "regime_transition": (
            f"{_aggregate_return_regime(train_returns)}_to_"
            f"{_aggregate_return_regime(test_returns)}"
        ),
    }


def _drawdown_summary(
    evaluations: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    high_drawdown_candidates = [
        str(item.get("candidate_id", ""))
        for item in evaluations
        if "high_drawdown" in _string_sequence(item.get("rejection_reasons"))
    ]
    worst_candidate = ""
    worst_drawdown = _ZERO
    for item in evaluations:
        drawdown = _decimal_from_text(
            _mapping(_mapping(item.get("windows")).get("test")).get(
                "max_drawdown",
                "0",
            )
        )
        if drawdown > worst_drawdown:
            worst_drawdown = drawdown
            worst_candidate = str(item.get("candidate_id", ""))
    return {
        "high_drawdown_candidate_count": len(high_drawdown_candidates),
        "high_drawdown_candidates": high_drawdown_candidates,
        "worst_drawdown_candidate_id": worst_candidate,
        "worst_test_max_drawdown": _decimal_text(worst_drawdown),
    }


def _return_regime(value: Decimal) -> str:
    if value > _ZERO:
        return "positive"
    if value < _ZERO:
        return "negative"
    return "flat"


def _aggregate_return_regime(values: Sequence[Decimal]) -> str:
    if not values:
        return "unavailable"
    positive = sum(1 for value in values if value > _ZERO)
    negative = sum(1 for value in values if value < _ZERO)
    if positive == len(values):
        return "broad_positive"
    if negative == len(values):
        return "broad_negative"
    if positive and negative:
        return "mixed"
    return "flat"


def _increment_count(counts: dict[str, int], key: str) -> None:
    clean_key = key.strip() if key.strip() else "unknown"
    counts[clean_key] = counts.get(clean_key, 0) + 1


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
            "test_excess_return_vs_equal_weight_basket": "",
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


def _string_list(value: object) -> list[str]:
    return list(dict.fromkeys(_string_sequence(value)))


def _false_safety_flags() -> dict[str, bool]:
    return {field_name: False for field_name in NO_SUBMIT_SAFETY_FIELDS}


if __name__ == "__main__":
    raise SystemExit(main())
