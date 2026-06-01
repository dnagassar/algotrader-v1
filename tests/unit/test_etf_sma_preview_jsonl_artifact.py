from __future__ import annotations

import ast
import importlib
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import algotrader.orchestration.etf_sma_preview_jsonl_artifact as artifact
from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.orchestration.etf_sma_execution_preview_bridge import (
    ETF_SMA_EXECUTION_PREVIEW_LABELS,
    EtfSmaExecutionPreview,
    EtfSmaExecutionPreviewConfig,
    build_etf_sma_execution_preview,
)
from algotrader.signals.etf_sma_evaluator import (
    ETF_SMA_SIGNAL_LABELS,
    EtfSmaSignalConfig,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)


MODULE_PATH = Path("src/algotrader/orchestration/etf_sma_preview_jsonl_artifact.py")
_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
_AS_OF_200 = _START + timedelta(days=199)
_CONFIG = EtfSmaExecutionPreviewConfig(as_of=_AS_OF_200)
_ALLOWED_DESCRIPTOR_FIELD_NAMES = {
    "allowlist_decision",
    "broker_action_performed",
    "broker_mutated",
    "broker_preview_performed",
    "capital_mutated",
    "intended_order_style",
    "intended_side",
    "max_notional",
    "preview_notional",
    "source_bridge_mutated",
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
    "json",
    "pathlib",
    "algotrader.core.time",
    "algotrader.core.validation",
    "algotrader.errors",
    "algotrader.orchestration.etf_sma_execution_preview_bridge",
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
    "os.getenv",
    "post",
    "request",
    "socket.socket",
    "submit_order",
    "time.time",
    "urlopen",
}


def test_bullish_spy_preview_builds_accepted_jsonl_record() -> None:
    preview = _accepted_preview()

    record = artifact.build_etf_sma_preview_jsonl_record(preview)
    payload = record.to_dict()

    assert record.source_preview is preview
    assert payload["artifact_version"] == "etf_sma_preview_jsonl_artifact_v1"
    assert payload["record_type"] == "etf_sma_preview_jsonl_record"
    assert payload["symbol"] == "SPY"
    assert payload["source_signal_symbol"] == "SPY"
    assert payload["asset_class"] == "equity"
    assert payload["as_of"] == _AS_OF_200.isoformat()
    assert payload["signal_posture"] == "bullish_risk_on"
    assert payload["preview_status"] == "accepted_for_offline_preview"
    assert payload["accepted_for_offline_preview"] is True
    assert payload["skipped"] is False
    assert payload["skip_reason"] == ""
    assert payload["short_window"] == 50
    assert payload["long_window"] == 200
    assert payload["max_notional"] == "25.00"
    assert payload["allowlist"] == ["SPY"]
    assert payload["allowlist_decision"] == "allowlisted"
    assert payload["intended_side"] == "buy"
    assert payload["intended_order_style"] == "notional_market_preview"
    assert payload["preview_notional"] == "25.00"
    assert payload["source_preview"] == preview.to_dict()


def test_defensive_preview_builds_skipped_jsonl_record() -> None:
    preview = build_etf_sma_execution_preview(_signal(*(200 * ("10",))), _CONFIG)

    record = artifact.build_etf_sma_preview_jsonl_record(preview)
    payload = record.to_dict()

    assert payload["signal_posture"] == "defensive_risk_off"
    assert payload["preview_status"] == "skipped_from_offline_preview"
    assert payload["accepted_for_offline_preview"] is False
    assert payload["skipped"] is True
    assert payload["skip_reason"] == "signal_posture_not_bullish"
    assert payload["decision_reason"] == "signal_posture_not_bullish"
    assert payload["preview_notional"] is None
    assert payload["intended_side"] is None


def test_insufficient_history_preview_builds_skipped_jsonl_record() -> None:
    preview = build_etf_sma_execution_preview(
        _signal(*(149 * ("10",) + 50 * ("20",))),
        _CONFIG,
    )

    record = artifact.build_etf_sma_preview_jsonl_record(preview)
    payload = record.to_dict()

    assert payload["signal_posture"] == "insufficient_history"
    assert payload["preview_status"] == "skipped_from_offline_preview"
    assert payload["skip_reason"] == "signal_insufficient_history"
    assert payload["source_preview"]["source_signal_result"]["long_sma"] is None
    assert payload["preview_notional"] is None


def test_non_allowlisted_preview_preserves_allowlist_decision() -> None:
    preview = build_etf_sma_execution_preview(
        _signal(*(150 * ("10",) + 50 * ("20",)), symbol="IVV"),
        _CONFIG,
    )

    payload = artifact.build_etf_sma_preview_jsonl_record(preview).to_dict()

    assert payload["symbol"] == "IVV"
    assert payload["allowlist"] == ["SPY"]
    assert payload["allowlist_decision"] == "not_allowlisted"
    assert payload["skip_reason"] == "symbol_not_allowed"


def test_record_preserves_labels_and_not_live_profit_markers() -> None:
    record = artifact.build_etf_sma_preview_jsonl_record(_accepted_preview())
    payload = record.to_dict()

    assert record.labels == artifact.ETF_SMA_PREVIEW_JSONL_ARTIFACT_LABELS
    assert "paper_lab_only" in record.labels
    assert "offline_execution_preview_only" in record.labels
    assert "local_preview_jsonl_artifact_only" in record.labels
    assert "not_live_authorized" in record.labels
    assert "profit_claim=none" in record.labels
    assert payload["source_preview_labels"] == list(ETF_SMA_EXECUTION_PREVIEW_LABELS)
    assert payload["source_signal_labels"] == list(ETF_SMA_SIGNAL_LABELS)
    assert "signal_evaluation_only" in payload["source_signal_labels"]
    assert payload["profit_claim"] == "none"
    assert payload["source_preview"]["profit_claim"] == "none"


def test_record_hard_false_broker_submit_and_capital_mutation_flags() -> None:
    payload = artifact.build_etf_sma_preview_jsonl_record(_accepted_preview()).to_dict()

    assert payload["broker_action_performed"] is False
    assert payload["broker_preview_performed"] is False
    assert payload["submit_allowed"] is False
    assert payload["capital_mutated"] is False
    assert payload["broker_mutated"] is False
    assert payload["source_bridge_mutated"] is False
    assert payload["source_preview"]["broker_action_performed"] is False
    assert payload["source_preview"]["broker_preview_performed"] is False
    assert payload["source_preview"]["submit_allowed"] is False
    assert payload["source_preview"]["mutated"] is False


def test_record_is_frozen_slotted_and_primitive_payload_lists_are_copied() -> None:
    record = artifact.build_etf_sma_preview_jsonl_record(_accepted_preview())

    assert hasattr(artifact.EtfSmaPreviewJsonlRecord, "__slots__")
    assert not hasattr(record, "__dict__")
    with pytest.raises(FrozenInstanceError):
        record.skipped = True

    payload = record.to_dict()
    payload["labels"].append("changed")
    payload["source_preview_labels"].append("changed")
    payload["source_signal_labels"].append("changed")
    payload["allowlist"].append("IVV")

    assert "changed" not in record.labels
    assert "changed" not in record.source_preview_labels
    assert "changed" not in record.source_signal_labels
    assert record.allowlist == ("SPY",)
    assert "changed" not in record.to_dict()["labels"]


def test_record_payload_is_primitive_only() -> None:
    _assert_primitive_only(
        artifact.build_etf_sma_preview_jsonl_record(_accepted_preview()).to_dict()
    )


def test_jsonl_rendering_is_sorted_deterministic_and_newline_terminated() -> None:
    record = artifact.build_etf_sma_preview_jsonl_record(_accepted_preview())

    rendered = artifact.render_etf_sma_preview_jsonl_record(record)

    assert rendered.endswith("\n")
    assert rendered.count("\n") == 1
    assert json.loads(rendered) == record.to_dict()
    assert rendered == (
        json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
    )
    assert rendered == artifact.render_etf_sma_preview_jsonl_record(record)


def test_writer_writes_exactly_one_newline_terminated_json_object(tmp_path) -> None:
    path = tmp_path / "preview.jsonl"
    preview = _accepted_preview()

    result = artifact.write_etf_sma_preview_jsonl_artifact(
        preview,
        artifact.EtfSmaPreviewJsonlArtifactConfig(output_path=path),
    )

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert text.endswith("\n")
    assert len(lines) == 1
    assert json.loads(lines[0]) == (
        artifact.build_etf_sma_preview_jsonl_record(preview).to_dict()
    )
    assert result.output_path == path
    assert result.record_count == 1
    assert result.bytes_written == len(text.encode("utf-8"))
    assert result.append is False
    assert result.newline_terminated is True
    assert result.broker_action_performed is False
    assert result.broker_preview_performed is False
    assert result.submit_allowed is False
    assert result.capital_mutated is False
    assert result.broker_mutated is False


def test_writer_appends_only_when_append_mode_is_enabled(tmp_path) -> None:
    path = tmp_path / "preview.jsonl"
    preview = _accepted_preview()

    artifact.write_etf_sma_preview_jsonl_artifact(
        preview,
        artifact.EtfSmaPreviewJsonlArtifactConfig(output_path=path),
    )
    second = artifact.write_etf_sma_preview_jsonl_artifact(
        preview,
        artifact.EtfSmaPreviewJsonlArtifactConfig(output_path=path, append=True),
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == lines[1]
    assert second.append is True


def test_writer_rejects_existing_path_without_explicit_append(tmp_path) -> None:
    path = tmp_path / "preview.jsonl"
    preview = _accepted_preview()
    config = artifact.EtfSmaPreviewJsonlArtifactConfig(output_path=path)

    artifact.write_etf_sma_preview_jsonl_artifact(preview, config)

    with pytest.raises(ValidationError, match="append=True"):
        artifact.write_etf_sma_preview_jsonl_artifact(preview, config)


def test_writer_creates_parent_only_when_configured(tmp_path) -> None:
    path = tmp_path / "runs" / "preview.jsonl"
    preview = _accepted_preview()

    with pytest.raises(ValidationError, match="parent directory"):
        artifact.write_etf_sma_preview_jsonl_artifact(
            preview,
            artifact.EtfSmaPreviewJsonlArtifactConfig(output_path=path),
        )
    assert not path.exists()

    result = artifact.write_etf_sma_preview_jsonl_artifact(
        preview,
        artifact.EtfSmaPreviewJsonlArtifactConfig(
            output_path=path,
            create_parent_dirs=True,
        ),
    )

    assert path.exists()
    assert result.created_parent_dirs is True


def test_artifact_boundary_rejects_live_authorized_source_labels() -> None:
    preview = _unsafe_preview(
        _accepted_preview(),
        labels=("paper_lab_only", "live_authorized", "profit_claim=none"),
    )

    with pytest.raises(ValidationError, match="live authorization"):
        artifact.build_etf_sma_preview_jsonl_record(preview)


def test_artifact_boundary_rejects_non_none_profit_claims() -> None:
    preview = _unsafe_preview(_accepted_preview(), profit_claim="profit_claim=positive")

    with pytest.raises(ValidationError, match="profit_claim"):
        artifact.build_etf_sma_preview_jsonl_record(preview)


def test_module_import_does_not_write_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    importlib.reload(artifact)

    assert tuple(tmp_path.iterdir()) == ()


def test_module_has_no_broker_sdk_network_execution_or_portfolio_imports() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "alpaca" not in source
    assert "credential" not in source


def test_module_does_not_use_execution_intent_or_execution_plan() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source

    field_names = {field.name for field in fields(artifact.EtfSmaPreviewJsonlRecord)}
    assert "execution_" + "intent" not in field_names
    assert "execution_" + "plan" not in field_names


def test_record_exposes_no_account_order_fill_or_portfolio_mutation_fields() -> None:
    record = artifact.build_etf_sma_preview_jsonl_record(_accepted_preview())

    for field in fields(artifact.EtfSmaPreviewJsonlRecord):
        _assert_no_forbidden_mutation_field_name(field.name)

    for key in _flatten_dict_keys(record.to_dict()):
        _assert_no_forbidden_mutation_field_name(key)


def test_next_action_points_to_fresh_read_only_snapshot_not_submit() -> None:
    record = artifact.build_etf_sma_preview_jsonl_record(_accepted_preview())

    assert record.next_action == (
        "m348_fresh_read_only_paper_snapshot_before_broker_facing_preview"
    )
    assert "m348" in record.next_action
    assert "fresh_read_only_paper_snapshot" in record.next_action
    assert "submit" not in record.next_action
    assert "order" not in record.next_action


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


def _unsafe_preview(
    source: EtfSmaExecutionPreview,
    **overrides: object,
) -> EtfSmaExecutionPreview:
    preview = object.__new__(EtfSmaExecutionPreview)
    values = {field.name: getattr(source, field.name) for field in fields(source)}
    values.update(overrides)
    for name, value in values.items():
        object.__setattr__(preview, name, value)

    return preview


def _assert_no_forbidden_mutation_field_name(field_name: str) -> None:
    if field_name in _ALLOWED_DESCRIPTOR_FIELD_NAMES:
        return

    lowered = field_name.lower()
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
