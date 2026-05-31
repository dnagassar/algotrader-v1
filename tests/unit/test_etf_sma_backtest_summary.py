from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.research.etf_sma_backtest_summary import (
    ETF_SMA_BACKTEST_SUMMARY_LABELS,
    ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS,
    EtfSmaBacktestBar,
    EtfSmaBacktestConfig,
    EtfSmaBacktestSummary,
    build_etf_sma_backtest_summary,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_backtest_summary.py")
_CONFIG = EtfSmaBacktestConfig(
    symbol="SPY",
    strategy_name="SPY SMA offline backtest summary",
    short_window=2,
    long_window=3,
)
_REQUIRED_LABELS = {
    "research_only",
    "paper_lab_candidate",
    "not_live_authorized",
    "profit_claim=none",
}
_REQUIRED_LIMITATIONS = {
    "synthetic_or_local_input_only",
    "zero_cost_or_declared_cost_model",
    "no_slippage_model_unless_explicitly_added",
    "no_live_or_paper_authorization",
    "not_profit_evidence",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "broker",
    "credential",
    "execution_intent",
    "execution_plan",
    "fill",
    "order",
    "portfolio",
    "mutation",
    "preview",
    "stage",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.errors",
    "algotrader.research.etf_sma_research_candidate",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "numpy",
    "pandas",
    "polygon",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "urllib",
    "vectorbt",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "ExecutionIntent",
    "ExecutionPlan",
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "download",
    "getenv",
    "liquidate",
    "open",
    "os.getenv",
    "post",
    "read",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
    "write",
}


def test_bullish_trend_produces_delayed_positive_exposure_summary() -> None:
    summary = build_etf_sma_backtest_summary(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "40"),
            ("2026-01-05", "80"),
        ),
        _CONFIG,
        "2026-01-05",
    )

    assert summary.signal_count == 3
    assert summary.exposure_count == 2
    assert summary.defensive_count == 3
    assert summary.posture_change_count == 1
    assert summary.strategy_total_return == Decimal("3")
    assert summary.benchmark_total_return == Decimal("7")
    assert summary.max_drawdown == Decimal("0")
    assert summary.latest_posture == "bullish_trend_candidate"
    assert summary.to_dict() == {
        "summary_type": "etf_sma_offline_backtest_summary",
        "status": "research_measurement_only",
        "symbol": "SPY",
        "strategy_name": "SPY SMA offline backtest summary",
        "as_of": "2026-01-05",
        "start_date": "2026-01-01",
        "end_date": "2026-01-05",
        "sample_count": 5,
        "bar_count": 5,
        "ignored_future_bar_count": 0,
        "short_window": 2,
        "long_window": 3,
        "cost_bps": "0",
        "signal_count": 3,
        "exposure_count": 2,
        "defensive_count": 3,
        "posture_change_count": 1,
        "strategy_total_return": "3",
        "benchmark_total_return": "7",
        "max_drawdown": "0",
        "latest_posture": "bullish_trend_candidate",
        "labels": list(ETF_SMA_BACKTEST_SUMMARY_LABELS),
        "eligibility_status": "research_measurement_only",
        "recommended_next_operator_action": (
            "draft_or_review_local_data_snapshot_validation_before_paper_experiment"
        ),
        "limitations": list(ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS),
    }


def test_defensive_trend_produces_cash_exposure_intervals() -> None:
    summary = build_etf_sma_backtest_summary(
        _bars(
            ("2026-01-01", "80"),
            ("2026-01-02", "40"),
            ("2026-01-03", "20"),
            ("2026-01-04", "10"),
            ("2026-01-05", "5"),
        ),
        _CONFIG,
        "2026-01-05",
    )

    assert summary.signal_count == 3
    assert summary.exposure_count == 0
    assert summary.defensive_count == 5
    assert summary.posture_change_count == 0
    assert summary.strategy_total_return == Decimal("0")
    assert summary.benchmark_total_return == Decimal("-0.9375")
    assert summary.latest_posture == "defensive_or_cash_candidate"


def test_insufficient_history_produces_no_strategy_exposure() -> None:
    summary = build_etf_sma_backtest_summary(
        _bars(("2026-01-01", "10"), ("2026-01-02", "11")),
        _CONFIG,
        "2026-01-02",
    )

    assert summary.signal_count == 0
    assert summary.exposure_count == 0
    assert summary.defensive_count == 2
    assert summary.posture_change_count == 0
    assert summary.strategy_total_return == Decimal("0")
    assert summary.benchmark_total_return == Decimal("0.1")
    assert summary.latest_posture == "insufficient_history"


def test_one_bar_delay_prevents_same_bar_signal_return_capture() -> None:
    summary = build_etf_sma_backtest_summary(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
        ),
        _CONFIG,
        "2026-01-03",
    )

    assert summary.signal_count == 1
    assert summary.exposure_count == 0
    assert summary.strategy_total_return == Decimal("0")
    assert summary.benchmark_total_return == Decimal("1")
    assert summary.latest_posture == "bullish_trend_candidate"


def test_future_bars_after_as_of_do_not_change_posture_or_returns() -> None:
    as_of_bars = _bars(
        ("2026-01-01", "10"),
        ("2026-01-02", "10"),
        ("2026-01-03", "20"),
        ("2026-01-04", "40"),
        ("2026-01-05", "80"),
    )
    with_future_bars = [
        *as_of_bars,
        EtfSmaBacktestBar("2026-01-06", Decimal("1")),
        EtfSmaBacktestBar("2026-01-07", Decimal("1")),
    ]

    without_future = build_etf_sma_backtest_summary(
        as_of_bars,
        _CONFIG,
        "2026-01-05",
    )
    with_future = build_etf_sma_backtest_summary(
        with_future_bars,
        _CONFIG,
        "2026-01-05",
    )

    assert with_future.sample_count == 7
    assert with_future.bar_count == 5
    assert with_future.ignored_future_bar_count == 2
    assert with_future.signal_count == without_future.signal_count
    assert with_future.exposure_count == without_future.exposure_count
    assert with_future.defensive_count == without_future.defensive_count
    assert with_future.posture_change_count == without_future.posture_change_count
    assert with_future.strategy_total_return == without_future.strategy_total_return
    assert with_future.benchmark_total_return == without_future.benchmark_total_return
    assert with_future.max_drawdown == without_future.max_drawdown
    assert with_future.latest_posture == without_future.latest_posture


def test_benchmark_return_is_independent_of_strategy_signal_parameters() -> None:
    bars = _bars(
        ("2026-01-01", "10"),
        ("2026-01-02", "20"),
        ("2026-01-03", "40"),
        ("2026-01-04", "80"),
    )

    fast_summary = build_etf_sma_backtest_summary(
        bars,
        EtfSmaBacktestConfig(short_window=1, long_window=2),
        "2026-01-04",
    )
    slow_summary = build_etf_sma_backtest_summary(
        bars,
        EtfSmaBacktestConfig(short_window=2, long_window=3),
        "2026-01-04",
    )

    assert fast_summary.benchmark_total_return == Decimal("7")
    assert slow_summary.benchmark_total_return == Decimal("7")
    assert fast_summary.strategy_total_return != slow_summary.strategy_total_return


def test_labels_eligibility_and_limitations_are_conservative() -> None:
    summary = _summary()
    payload = summary.to_dict()

    assert set(summary.labels) == _REQUIRED_LABELS
    assert payload["labels"] == list(ETF_SMA_BACKTEST_SUMMARY_LABELS)
    assert payload["eligibility_status"] == "research_measurement_only"
    assert payload["recommended_next_operator_action"] == (
        "draft_or_review_local_data_snapshot_validation_before_paper_experiment"
    )
    assert set(summary.limitations) == _REQUIRED_LIMITATIONS
    assert payload["limitations"] == list(ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS)


def test_summary_and_inputs_are_immutable_and_dict_lists_are_copied() -> None:
    summary = _summary()
    bar = EtfSmaBacktestBar("2026-01-01", Decimal("10"))

    with pytest.raises(FrozenInstanceError):
        summary.latest_posture = "changed"
    with pytest.raises(FrozenInstanceError):
        bar.close = Decimal("99")

    payload = summary.to_dict()
    payload["labels"].append("changed")
    payload["limitations"].append("changed")

    assert "changed" not in summary.labels
    assert "changed" not in summary.limitations
    assert "changed" not in summary.to_dict()["labels"]
    assert "changed" not in summary.to_dict()["limitations"]


def test_summary_dict_is_primitive_only() -> None:
    _assert_primitive_only(_summary().to_dict())


def test_summary_output_has_no_execution_or_capital_mutation_fields() -> None:
    for key in _flatten_dict_keys(_summary().to_dict()):
        lowered = key.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)


def test_module_has_no_forbidden_imports_or_runtime_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_config_requires_short_window_below_long_window() -> None:
    with pytest.raises(ValueError, match="short_window"):
        EtfSmaBacktestConfig(short_window=3, long_window=3)


def test_duplicate_bar_dates_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate dates"):
        build_etf_sma_backtest_summary(
            _bars(("2026-01-01", "10"), ("2026-01-01", "11")),
            _CONFIG,
            "2026-01-01",
        )


def test_summary_output_dataclass_validates_fixed_safety_metadata() -> None:
    with pytest.raises(ValueError, match="summary_type"):
        EtfSmaBacktestSummary(
            summary_type="changed",
            status="research_measurement_only",
            symbol="SPY",
            strategy_name="SPY SMA offline backtest summary",
            as_of="2026-01-05",
            start_date="2026-01-01",
            end_date="2026-01-05",
            sample_count=5,
            bar_count=5,
            ignored_future_bar_count=0,
            short_window=2,
            long_window=3,
            cost_bps=Decimal("0"),
            signal_count=3,
            exposure_count=2,
            defensive_count=3,
            posture_change_count=1,
            strategy_total_return=Decimal("3"),
            benchmark_total_return=Decimal("7"),
            max_drawdown=Decimal("0"),
            latest_posture="bullish_trend_candidate",
            labels=ETF_SMA_BACKTEST_SUMMARY_LABELS,
            eligibility_status="research_measurement_only",
            recommended_next_operator_action=(
                "draft_or_review_local_data_snapshot_validation_before_paper_experiment"
            ),
            limitations=ETF_SMA_BACKTEST_SUMMARY_LIMITATIONS,
        )


def _summary() -> EtfSmaBacktestSummary:
    return build_etf_sma_backtest_summary(
        _bars(
            ("2026-01-01", "10"),
            ("2026-01-02", "10"),
            ("2026-01-03", "20"),
            ("2026-01-04", "40"),
            ("2026-01-05", "80"),
        ),
        _CONFIG,
        "2026-01-05",
    )


def _bars(*values: tuple[str, str]) -> list[EtfSmaBacktestBar]:
    return [EtfSmaBacktestBar(day, Decimal(close)) for day, close in values]


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal, date))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_only(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_primitive_only(item)
        return

    assert value is None or type(value) in (str, int, float, bool)


def _flatten_dict_keys(value: object) -> tuple[str, ...]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_flatten_dict_keys(item))
        return tuple(keys)

    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_flatten_dict_keys(item))
        return tuple(keys)

    return ()


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
