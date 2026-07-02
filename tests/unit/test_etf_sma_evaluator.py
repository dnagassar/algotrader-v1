from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.signals.etf_sma_evaluator import (
    ETF_SMA_SIGNAL_LABELS,
    EtfSmaSignalConfig,
    EtfSmaSignalEvaluator,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)


MODULE_PATH = Path("src/algotrader/signals/etf_sma_evaluator.py")
_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
_AS_OF_200 = _START + timedelta(days=199)
_CONFIG = EtfSmaSignalConfig(as_of=_AS_OF_200)
_ALLOWED_SAFETY_FIELD_NAMES = {
    "broker_action_performed",
    "submit_allowed",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "buying_power",
    "cash",
    "client_order_id",
    "execution_intent",
    "execution_plan",
    "fill",
    "notional",
    "order",
    "portfolio",
    "position",
    "quantity",
    "side",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.core.time",
    "algotrader.core.types",
    "algotrader.core.validation",
    "algotrader.errors",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.execution",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
    "os",
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
    "datetime.now",
    "datetime.utcnow",
    "download",
    "environ.get",
    "getenv",
    "liquidate",
    "open",
    "os.getenv",
    "post",
    "read",
    "request",
    "socket.socket",
    "submit_order",
    "time.time",
    "urlopen",
    "write",
}


def test_bullish_posture_when_short_sma_is_above_long_sma() -> None:
    result = evaluate_etf_sma_signal(
        _bars(*(150 * ("10",) + 50 * ("20",))),
        _CONFIG,
    )

    assert result.symbol == "SPY"
    assert result.asset_class == "equity"
    assert result.strategy_type == "long_only_broad_etf_sma_trend_filter"
    assert result.timeframe == "daily"
    assert result.short_window == 50
    assert result.long_window == 200
    assert result.usable_bar_count == 200
    assert result.ignored_future_bar_count == 0
    assert result.latest_close == Decimal("20")
    assert result.short_sma == Decimal("20")
    assert result.long_sma == Decimal("12.5")
    assert result.posture == "bullish_risk_on"


def test_evaluator_object_uses_immutable_config_contract() -> None:
    evaluator = EtfSmaSignalEvaluator(_CONFIG)

    result = evaluator.evaluate(_bars(*(150 * ("10",) + 50 * ("20",))))

    assert hasattr(EtfSmaSignalEvaluator, "__slots__")
    assert not hasattr(evaluator, "__dict__")
    assert evaluator.config is _CONFIG
    assert result.posture == "bullish_risk_on"
    with pytest.raises(FrozenInstanceError):
        evaluator.config = EtfSmaSignalConfig(as_of=_AS_OF_200)


def test_defensive_posture_when_short_sma_is_equal_to_long_sma() -> None:
    result = evaluate_etf_sma_signal(
        _bars(*(200 * ("10",))),
        _CONFIG,
    )

    assert result.short_sma == Decimal("10")
    assert result.long_sma == Decimal("10")
    assert result.posture == "defensive_risk_off"


def test_insufficient_history_when_fewer_than_long_window_bars_are_available() -> None:
    result = evaluate_etf_sma_signal(
        _bars(*(149 * ("10",) + 50 * ("20",))),
        _CONFIG,
    )

    assert result.usable_bar_count == 199
    assert result.latest_close == Decimal("20")
    assert result.short_sma == Decimal("20")
    assert result.long_sma is None
    assert result.posture == "insufficient_history"
    assert result.to_dict()["long_sma"] is None


def test_future_bars_are_ignored_and_counted() -> None:
    as_of_bars = _bars(*(150 * ("10",) + 50 * ("20",)))
    with_future_bars = (
        *as_of_bars,
        _bar("SPY", _START + timedelta(days=200), "1000"),
        _bar("SPY", _START + timedelta(days=201), "1000"),
    )

    result = evaluate_etf_sma_signal(with_future_bars, _CONFIG)

    assert result.total_bar_count == 202
    assert result.usable_bar_count == 200
    assert result.ignored_future_bar_count == 2


def test_future_bars_do_not_affect_posture_or_sma_values() -> None:
    as_of_bars = _bars(*(150 * ("10",) + 50 * ("20",)))
    with_future_bars = (
        *as_of_bars,
        _bar("SPY", _START + timedelta(days=200), "1"),
        _bar("SPY", _START + timedelta(days=201), "1"),
    )

    without_future = evaluate_etf_sma_signal(as_of_bars, _CONFIG)
    with_future = evaluate_etf_sma_signal(with_future_bars, _CONFIG)

    assert with_future.latest_close == without_future.latest_close
    assert with_future.short_sma == without_future.short_sma
    assert with_future.long_sma == without_future.long_sma
    assert with_future.posture == without_future.posture


@pytest.mark.parametrize(
    "kwargs",
    (
        {"short_window": 0},
        {"long_window": 0},
        {"short_window": -1},
        {"long_window": -1},
        {"short_window": 200, "long_window": 200},
        {"short_window": 201, "long_window": 200},
        {"short_window": True},
        {"long_window": False},
    ),
)
def test_invalid_windows_are_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EtfSmaSignalConfig(as_of=_AS_OF_200, **kwargs)


def test_options_asset_class_is_rejected_by_etf_sma_config() -> None:
    with pytest.raises(ValidationError, match="asset_class"):
        EtfSmaSignalConfig(as_of=_AS_OF_200, asset_class="option")


def test_mixed_symbol_input_is_rejected() -> None:
    bars = list(_bars(*(200 * ("10",))))
    bars[5] = _bar("IVV", _START + timedelta(days=5), "10")

    with pytest.raises(ValidationError, match="configured symbol"):
        evaluate_etf_sma_signal(bars, _CONFIG)


def test_bars_are_sorted_by_timestamp_before_sma_calculation() -> None:
    ordered = _bars(*(150 * ("10",) + 50 * ("20",)))
    shuffled = (*ordered[50:], *ordered[:50])

    result = evaluate_etf_sma_signal(shuffled, _CONFIG)

    assert result.short_sma == Decimal("20")
    assert result.long_sma == Decimal("12.5")
    assert result.posture == "bullish_risk_on"


def test_result_is_immutable_frozen_slotted_and_dict_lists_are_copied() -> None:
    result = evaluate_etf_sma_signal(_bars(*(200 * ("10",))), _CONFIG)

    assert hasattr(EtfSmaSignalResult, "__slots__")
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.posture = "changed"

    payload = result.to_dict()
    payload["labels"].append("changed")
    payload["limitations"].append("changed")

    assert "changed" not in result.labels
    assert "changed" not in result.limitations
    assert "changed" not in result.to_dict()["labels"]
    assert "changed" not in result.to_dict()["limitations"]


def test_labels_include_not_live_authorized_and_profit_claim_remains_none() -> None:
    result = evaluate_etf_sma_signal(_bars(*(200 * ("10",))), _CONFIG)

    assert result.labels == ETF_SMA_SIGNAL_LABELS
    assert "paper_lab_only" in result.labels
    assert "signal_evaluation_only" in result.labels
    assert "not_live_authorized" in result.labels
    assert "profit_claim=none" in result.labels
    assert result.profit_claim == "none"
    assert result.to_dict()["profit_claim"] == "none"


def test_result_has_only_explicit_hard_false_safety_flags() -> None:
    result = evaluate_etf_sma_signal(_bars(*(200 * ("10",))), _CONFIG)
    payload = result.to_dict()

    assert result.broker_action_performed is False
    assert result.submit_allowed is False
    assert payload["broker_action_performed"] is False
    assert payload["submit_allowed"] is False

    for field in fields(EtfSmaSignalResult):
        if field.name in _ALLOWED_SAFETY_FIELD_NAMES:
            continue
        lowered = field.name.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)

    for key in _flatten_dict_keys(payload):
        if key in _ALLOWED_SAFETY_FIELD_NAMES:
            continue
        lowered = key.lower()
        assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)


def test_evaluator_output_includes_next_offline_milestone_not_submit() -> None:
    result = evaluate_etf_sma_signal(_bars(*(200 * ("10",))), _CONFIG)

    assert result.next_action == (
        "m346_offline_etf_sma_signal_to_risk_execution_preview_bridge_no_broker_action"
    )
    assert "offline" in result.next_action
    assert "no_broker_action" in result.next_action
    assert "submit" not in result.next_action


def test_to_dict_is_primitive_only() -> None:
    result = evaluate_etf_sma_signal(_bars(*(200 * ("10",))), _CONFIG)

    _assert_primitive_only(result.to_dict())


def test_module_has_no_network_broker_credential_or_downstream_imports() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert "credential" not in MODULE_PATH.read_text(encoding="utf-8").lower()


def test_module_has_no_execution_intent_or_plan_references() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source

    field_names = {field.name for field in fields(EtfSmaSignalResult)}
    assert "execution_" + "intent" not in field_names
    assert "execution_" + "plan" not in field_names


def test_duplicate_daily_dates_are_rejected() -> None:
    duplicate_day = _START + timedelta(days=5)
    bars = (
        *_bars(*(200 * ("10",))),
        _bar("SPY", duplicate_day, "10"),
    )

    with pytest.raises(ValidationError, match="duplicate daily dates"):
        evaluate_etf_sma_signal(bars, _CONFIG)


def test_non_utc_as_of_and_bar_timestamps_are_rejected() -> None:
    with pytest.raises(ValidationError, match="as_of"):
        EtfSmaSignalConfig(as_of=datetime(2026, 1, 1))

    non_utc_bar = _bar(
        "SPY",
        datetime(2025, 1, 1, tzinfo=timezone(timedelta(hours=-5))),
        "10",
    )
    with pytest.raises(ValidationError, match="timestamp"):
        evaluate_etf_sma_signal((non_utc_bar,), _CONFIG)


def _bars(*closes: str) -> tuple[Bar, ...]:
    return tuple(
        _bar("SPY", _START + timedelta(days=index), close)
        for index, close in enumerate(closes)
    )


def _bar(symbol: str, timestamp: datetime, close: str) -> Bar:
    value = Decimal(close)
    return Bar(
        symbol=symbol,
        timestamp=timestamp,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal("100"),
    )


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal, datetime))
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

    assert value is None or type(value) in (str, int, bool)


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
