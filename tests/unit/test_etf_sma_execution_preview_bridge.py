from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.orchestration.etf_sma_execution_preview_bridge import (
    ETF_SMA_EXECUTION_PREVIEW_LABELS,
    EtfSmaExecutionPreview,
    EtfSmaExecutionPreviewConfig,
    build_etf_sma_execution_preview,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)


MODULE_PATH = Path("src/algotrader/orchestration/etf_sma_execution_preview_bridge.py")
_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
_AS_OF_200 = _START + timedelta(days=199)
_CONFIG = EtfSmaExecutionPreviewConfig(as_of=_AS_OF_200)
_ALLOWED_DESCRIPTOR_FIELD_NAMES = {
    "broker_action_performed",
    "broker_preview_performed",
    "intended_order_style",
    "intended_side",
    "max_notional",
    "mutated",
    "preview_notional",
    "submit_allowed",
}
_FORBIDDEN_FIELD_TERMS = (
    "account",
    "buying_power",
    "cash",
    "client_order_id",
    "fill",
    "portfolio",
    "position",
    "quantity",
    "venue",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "algotrader.core.time",
    "algotrader.core.validation",
    "algotrader.errors",
    "algotrader.signals.etf_sma_evaluator",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "os",
    "pandas",
    "polygon",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "subprocess",
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


def test_bullish_spy_signal_creates_accepted_offline_preview_candidate() -> None:
    source = _signal(*(150 * ("10",) + 50 * ("20",)))

    preview = build_etf_sma_execution_preview(source, _CONFIG)

    assert preview.symbol == "SPY"
    assert preview.asset_class == "equity"
    assert preview.as_of == _AS_OF_200
    assert preview.signal_posture == "bullish_risk_on"
    assert preview.signal_is_bullish_risk_on is True
    assert preview.accepted_for_offline_preview is True
    assert preview.eligible_for_future_paper_lab_preview is True
    assert preview.would_create_execution_facing_candidate_later is True
    assert preview.skipped is False
    assert preview.skip_reason == ""
    assert preview.decision_reason == (
        "bullish_spy_signal_within_offline_preview_constraints"
    )
    assert preview.intended_side == "buy"
    assert preview.intended_order_style == "notional_market_preview"
    assert preview.preview_notional == Decimal("25.00")
    assert preview.to_dict()["preview_notional"] == "25.00"


def test_defensive_spy_signal_is_skipped() -> None:
    source = _signal(*(200 * ("10",)))

    preview = build_etf_sma_execution_preview(source, _CONFIG)

    assert preview.signal_posture == "defensive_risk_off"
    assert preview.accepted_for_offline_preview is False
    assert preview.eligible_for_future_paper_lab_preview is False
    assert preview.would_create_execution_facing_candidate_later is False
    assert preview.skipped is True
    assert preview.skip_reason == "signal_posture_not_bullish"
    assert preview.decision_reason == "signal_posture_not_bullish"
    assert preview.intended_side is None
    assert preview.intended_order_style is None
    assert preview.preview_notional is None


def test_insufficient_history_spy_signal_is_skipped() -> None:
    source = _signal(*(149 * ("10",) + 50 * ("20",)))

    preview = build_etf_sma_execution_preview(source, _CONFIG)

    assert preview.signal_posture == "insufficient_history"
    assert preview.signal_is_bullish_risk_on is False
    assert preview.accepted_for_offline_preview is False
    assert preview.skipped is True
    assert preview.skip_reason == "signal_insufficient_history"
    assert preview.preview_notional is None


def test_non_allowlisted_symbol_is_skipped_deterministically() -> None:
    source = _signal(*(150 * ("10",) + 50 * ("20",)), symbol="IVV")

    preview = build_etf_sma_execution_preview(source, _CONFIG)

    assert preview.symbol == "IVV"
    assert preview.signal_posture == "bullish_risk_on"
    assert preview.accepted_for_offline_preview is False
    assert preview.skipped is True
    assert preview.skip_reason == "symbol_not_allowed"
    assert preview.allowlist == ("SPY",)
    assert preview.intended_side is None
    assert preview.preview_notional is None


@pytest.mark.parametrize("value", (Decimal("0"), Decimal("-0.01")))
def test_max_notional_must_be_positive(value: Decimal) -> None:
    with pytest.raises(ValidationError, match="positive Decimal"):
        EtfSmaExecutionPreviewConfig(as_of=_AS_OF_200, max_notional=value)


def test_max_notional_above_twenty_five_is_rejected_for_first_path() -> None:
    with pytest.raises(ValidationError, match="25.00"):
        EtfSmaExecutionPreviewConfig(
            as_of=_AS_OF_200,
            max_notional=Decimal("25.01"),
        )


def test_preview_result_is_frozen_slotted_and_dict_lists_are_copied() -> None:
    preview = _accepted_preview()

    assert hasattr(EtfSmaExecutionPreview, "__slots__")
    assert not hasattr(preview, "__dict__")
    with pytest.raises(FrozenInstanceError):
        preview.skipped = True

    payload = preview.to_dict()
    payload["allowlist"].append("IVV")
    payload["labels"].append("changed")

    assert preview.allowlist == ("SPY",)
    assert "changed" not in preview.labels
    assert "changed" not in preview.to_dict()["labels"]


def test_preview_preserves_source_signal_result_identity() -> None:
    source = _signal(*(150 * ("10",) + 50 * ("20",)))

    preview = build_etf_sma_execution_preview(source, _CONFIG)

    assert preview.source_signal_result is source
    assert preview.to_dict()["source_signal_result"] == source.to_dict()


def test_labels_include_not_live_authorized() -> None:
    preview = _accepted_preview()

    assert preview.labels == ETF_SMA_EXECUTION_PREVIEW_LABELS
    assert "paper_lab_only" in preview.labels
    assert "offline_execution_preview_only" in preview.labels
    assert "not_live_authorized" in preview.labels
    assert "profit_claim=none" in preview.labels


def test_profit_claim_remains_none() -> None:
    preview = _accepted_preview()

    assert preview.profit_claim == "none"
    assert preview.to_dict()["profit_claim"] == "none"


def test_hard_false_safety_flags_remain_false() -> None:
    preview = _accepted_preview()
    payload = preview.to_dict()

    assert preview.broker_action_performed is False
    assert preview.broker_preview_performed is False
    assert preview.submit_allowed is False
    assert preview.mutated is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_preview_performed"] is False
    assert payload["submit_allowed"] is False
    assert payload["mutated"] is False


def test_preview_exposes_no_broker_order_account_fill_or_portfolio_mutation_fields() -> None:
    preview = _accepted_preview()

    for field in fields(EtfSmaExecutionPreview):
        _assert_no_forbidden_mutation_field_name(field.name)

    for key in _flatten_dict_keys(preview.to_dict()):
        _assert_no_forbidden_mutation_field_name(key)


def test_to_dict_is_primitive_only() -> None:
    _assert_primitive_only(_accepted_preview().to_dict())


def test_module_has_no_alpaca_broker_network_credential_scheduler_llm_or_research_dependency() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "credential" not in source
    assert "paper_snapshot" not in source


def test_bridge_does_not_use_execution_intent_or_execution_plan() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source

    field_names = {field.name for field in fields(EtfSmaExecutionPreview)}
    assert "execution_" + "intent" not in field_names
    assert "execution_" + "plan" not in field_names


def test_next_action_points_to_later_offline_artifact_not_broker_submit() -> None:
    preview = _accepted_preview()

    assert preview.next_action == (
        "m347_local_etf_sma_preview_jsonl_artifact_no_broker_action"
    )
    assert "m347" in preview.next_action
    assert "jsonl_artifact" in preview.next_action
    assert "no_broker_action" in preview.next_action
    assert "submit" not in preview.next_action
    assert "order" not in preview.next_action


def _accepted_preview() -> EtfSmaExecutionPreview:
    return build_etf_sma_execution_preview(
        _signal(*(150 * ("10",) + 50 * ("20",))),
        _CONFIG,
    )


def _signal(*closes: str, symbol: str = "SPY") -> EtfSmaSignalResult:
    return evaluate_etf_sma_signal(
        _bars(*closes, symbol=symbol),
        EtfSmaSignalConfig(as_of=_AS_OF_200, symbol=symbol),
    )


def _bars(*closes: str, symbol: str) -> tuple[Bar, ...]:
    return tuple(
        _bar(symbol, _START + timedelta(days=index), close)
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


def _assert_no_forbidden_mutation_field_name(field_name: str) -> None:
    if field_name in _ALLOWED_DESCRIPTOR_FIELD_NAMES:
        return

    lowered = field_name.lower()
    assert "broker" not in lowered
    assert "order" not in lowered
    assert all(term not in lowered for term in _FORBIDDEN_FIELD_TERMS)


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
