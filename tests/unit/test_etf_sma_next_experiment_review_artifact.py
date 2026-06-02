from __future__ import annotations

import ast
import importlib
import json
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

import algotrader.research.etf_sma_next_experiment_review_artifact as artifact
from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.research.etf_sma_next_experiment_review import (
    ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_next_experiment_review_artifact.py")
_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
_AS_OF_200 = _START + timedelta(days=199)
_RUN_ID = "m368a_offline_spy_etf_sma_next_experiment_review"
_M366_EVIDENCE_ID = "m366_fresh_paper_lab_reset_snapshot"
_SIGNAL_EVIDENCE_ID = "m368a_offline_spy_etf_sma_fixture_signal"
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
    "langchain",
    "langgraph",
    "llm",
    "numpy",
    "openai",
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
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "decimal",
    "json",
    "pathlib",
    "algotrader.errors",
    "algotrader.research.etf_sma_next_experiment_review",
}
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "datetime.now",
    "datetime.utcnow",
    "download",
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


def test_ready_m366_reset_and_offline_spy_sma_signal_materialize_review_record() -> None:
    record = _record()
    payload = record.to_dict()
    reset = payload["reset_evidence_summary"]
    signal = payload["offline_signal_evidence_summary"]

    assert payload["artifact_version"] == "etf_sma_next_experiment_review_artifact_v1"
    assert payload["record_type"] == "etf_sma_next_experiment_review_artifact_record"
    assert payload["run_id"] == _RUN_ID
    assert payload["evidence_ids"] == [_M366_EVIDENCE_ID, _SIGNAL_EVIDENCE_ID]
    assert payload["m366_evidence_id"] == _M366_EVIDENCE_ID
    assert payload["signal_evidence_id"] == _SIGNAL_EVIDENCE_ID
    assert payload["symbol"] == "SPY"
    assert payload["asset_class"] == "equity"
    assert payload["cap"] == "25.00"
    assert payload["labels"] == list(ETF_SMA_NEXT_EXPERIMENT_REVIEW_LABELS)
    assert reset["evidence_id"] == _M366_EVIDENCE_ID
    assert reset["classification"] == "paper_lab_flat_clean"
    assert reset["account_observed"] is True
    assert reset["positions_observed"] is True
    assert reset["open_orders_observed"] is True
    assert reset["cash"] == "1999.81"
    assert reset["currency"] == "USD"
    assert reset["position_count"] == 0
    assert reset["position_symbols"] == []
    assert reset["recent_order_count"] == 0
    assert reset["spy_absent_or_zero"] is True
    assert reset["no_open_orders"] is True
    assert reset["mutated"] is False
    assert reset["submitted"] is False
    assert reset["reset_blockers"] == []
    assert signal["status"] == "bullish_risk_on"
    assert signal["m367_signal_status"] == "bullish_risk_on"
    assert signal["symbol"] == "SPY"
    assert signal["asset_class"] == "equity"
    assert signal["short_window"] == 50
    assert signal["long_window"] == 200
    assert signal["total_bar_count"] == 200
    assert signal["usable_bar_count"] == 200
    assert signal["latest_close"] == "20"
    assert signal["short_sma"] == "20"
    assert signal["long_sma"] == "12.5"
    assert signal["actionable_risk_on"] is True
    assert signal["fixture_data_not_live_market_data"] is True
    assert signal["signal_blockers"] == []
    assert payload["offline_signal_status"] == "bullish_risk_on"
    assert payload["offline_signal_actionable_risk_on"] is True
    assert payload["decision"] == "ready_for_separate_broker_preview_milestone"
    assert payload["reason"].endswith("separate M368 preview-only milestone.")
    assert payload["blockers"] == []
    assert payload["required_next_milestone"] == (
        "M368 - SPY ETF/SMA broker-facing preview-only milestone"
    )
    assert payload["separate_preview_milestone_required"] is True
    assert payload["separate_broker_preview_milestone_allowed"] is True
    assert payload["submit_authorized"] is False
    assert payload["mutated"] is False
    assert payload["submitted"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_preview_performed"] is False
    assert payload["source_review"]["submit_authorized"] is False


def test_jsonl_rendering_and_writer_are_sorted_deterministic_and_safe(tmp_path) -> None:
    record = _record()
    rendered = artifact.render_etf_sma_next_experiment_review_artifact_record(record)
    path = tmp_path / "runs" / "paper_lab" / "review.jsonl"

    result = artifact.write_etf_sma_next_experiment_review_artifact(
        reset_evidence=_reset_evidence(),
        offline_signal_evidence=_risk_on_signal_evidence(),
        config=_config(path, create_parent_dirs=True),
    )

    text = path.read_text(encoding="utf-8")
    assert rendered == (
        json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
    )
    assert rendered.endswith("\n")
    assert rendered.count("\n") == 1
    assert json.loads(rendered) == record.to_dict()
    assert text == rendered
    assert result.output_path == path
    assert result.record_count == 1
    assert result.bytes_written == len(text.encode("utf-8"))
    assert result.created_parent_dirs is True
    assert result.submit_authorized is False
    assert result.mutated is False
    assert result.submitted is False
    assert result.broker_action_performed is False
    assert result.broker_preview_performed is False


def test_writer_rejects_existing_path_without_explicit_append(tmp_path) -> None:
    path = tmp_path / "review.jsonl"
    config = _config(path)

    artifact.write_etf_sma_next_experiment_review_artifact(
        reset_evidence=_reset_evidence(),
        offline_signal_evidence=_risk_on_signal_evidence(),
        config=config,
    )

    with pytest.raises(ValidationError, match="append=True"):
        artifact.write_etf_sma_next_experiment_review_artifact(
            reset_evidence=_reset_evidence(),
            offline_signal_evidence=_risk_on_signal_evidence(),
            config=config,
        )


def test_risk_off_signal_blocks_separate_preview_milestone() -> None:
    record = _record(offline_signal_evidence=_risk_off_signal_evidence())
    payload = record.to_dict()

    assert payload["decision"] == "blocked_signal_not_actionable"
    assert payload["offline_signal_status"] == "defensive_risk_off"
    assert payload["offline_signal_actionable_risk_on"] is False
    assert "signal_status_risk_off" in payload["blockers"]
    assert payload["separate_broker_preview_milestone_allowed"] is False
    assert payload["submit_authorized"] is False
    assert payload["required_next_milestone"] == (
        "resolve_m367_blocker_offline_before_paper_facing_work"
    )


def test_malformed_bullish_signal_blocks_instead_of_ready() -> None:
    signal = artifact.EtfSmaNextExperimentOfflineSignalEvidence(
        evidence_id=_SIGNAL_EVIDENCE_ID,
        symbol="SPY",
        asset_class="equity",
        as_of=_AS_OF_200.isoformat(),
        status="bullish_risk_on",
        short_window=50,
        long_window=200,
        total_bar_count=200,
        usable_bar_count=200,
        ignored_future_bar_count=0,
        latest_close=Decimal("20"),
        short_sma=None,
        long_sma=Decimal("12.5"),
        actionable_risk_on=True,
        provenance="deterministic_unit_test_fixture_bars_not_live_market_data",
        fixture_data_not_live_market_data=True,
    )

    record = _record(offline_signal_evidence=signal)
    payload = record.to_dict()

    assert payload["decision"] == "blocked_signal_not_actionable"
    assert payload["offline_signal_status"] == "malformed"
    assert "signal_short_sma_missing" in payload["blockers"]
    assert payload["separate_broker_preview_milestone_allowed"] is False
    assert payload["submit_authorized"] is False


def test_non_clean_reset_evidence_blocks_reset_readiness() -> None:
    reset = artifact.EtfSmaNextExperimentResetEvidence(
        classification="ambiguous_or_incomplete",
        position_count=1,
        position_symbols=("SPY",),
        spy_absent_or_zero=False,
    )

    record = _record(reset_evidence=reset)
    payload = record.to_dict()

    assert payload["decision"] == "blocked_reset_not_clean"
    assert payload["reset_evidence_summary"]["m367_classification"] == (
        "ambiguous_or_incomplete"
    )
    assert "reset_classification_not_paper_lab_flat_clean" in payload["blockers"]
    assert "positions_present" in payload["blockers"]
    assert "position_symbols_present" in payload["blockers"]
    assert "spy_position_not_absent_or_zero" in payload["blockers"]
    assert payload["separate_broker_preview_milestone_allowed"] is False
    assert payload["submit_authorized"] is False


def test_non_spy_signal_scope_blocks_symbol_readiness() -> None:
    signal = _risk_on_signal_evidence(symbol="QQQ")

    record = _record(offline_signal_evidence=signal)
    payload = record.to_dict()

    assert payload["decision"] == "blocked_symbol_not_allowed"
    assert "symbol_not_spy" in payload["blockers"]
    assert "signal_symbol_not_spy" in payload["blockers"]
    assert payload["symbol"] == "QQQ"
    assert payload["separate_broker_preview_milestone_allowed"] is False


def test_record_config_and_write_result_are_immutable_and_payload_is_copied(tmp_path) -> None:
    record = _record()
    config = _config(tmp_path / "review.jsonl")

    assert not hasattr(record, "__dict__")
    assert not hasattr(config, "__dict__")
    with pytest.raises(FrozenInstanceError):
        record.decision = "changed"
    with pytest.raises(FrozenInstanceError):
        config.run_id = "changed"

    payload = record.to_dict()
    payload["labels"].append("changed")
    payload["evidence_ids"].append("changed")
    payload["blockers"].append("changed")
    payload["reset_evidence_summary"]["position_symbols"].append("SPY")
    payload["offline_signal_evidence_summary"]["limitations"].append("changed")
    payload["source_review"]["allowlist"].append("QQQ")

    fresh_payload = record.to_dict()
    assert "changed" not in fresh_payload["labels"]
    assert "changed" not in fresh_payload["evidence_ids"]
    assert "changed" not in fresh_payload["blockers"]
    assert fresh_payload["reset_evidence_summary"]["position_symbols"] == []
    assert "changed" not in fresh_payload["offline_signal_evidence_summary"]["limitations"]
    assert fresh_payload["source_review"]["allowlist"] == ["SPY"]


def test_record_payload_is_primitive_only() -> None:
    _assert_primitive_only(_record().to_dict())


def test_module_import_does_not_write_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    importlib.reload(artifact)

    assert tuple(tmp_path.iterdir()) == ()


def test_module_has_no_broker_sdk_network_signal_or_trading_path_imports() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "Alpaca",
        "credential",
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source


def _config(
    path: Path,
    *,
    create_parent_dirs: bool = False,
) -> artifact.EtfSmaNextExperimentReviewArtifactConfig:
    return artifact.EtfSmaNextExperimentReviewArtifactConfig(
        output_path=path,
        create_parent_dirs=create_parent_dirs,
    )


def _record(
    *,
    reset_evidence: artifact.EtfSmaNextExperimentResetEvidence | None = None,
    offline_signal_evidence: (
        artifact.EtfSmaNextExperimentOfflineSignalEvidence | None
    ) = None,
) -> artifact.EtfSmaNextExperimentReviewArtifactRecord:
    return artifact.build_etf_sma_next_experiment_review_artifact_record(
        reset_evidence=reset_evidence or _reset_evidence(),
        offline_signal_evidence=offline_signal_evidence or _risk_on_signal_evidence(),
        config=_config(Path("runs/paper_lab/m368a_offline_spy_etf_sma_next_experiment_review.jsonl")),
    )


def _reset_evidence() -> artifact.EtfSmaNextExperimentResetEvidence:
    return artifact.EtfSmaNextExperimentResetEvidence()


def _risk_on_signal_evidence(
    *,
    symbol: str = "SPY",
) -> artifact.EtfSmaNextExperimentOfflineSignalEvidence:
    return _signal_evidence(
        _signal(*(150 * ("10",) + 50 * ("20",)), symbol=symbol),
        actionable_risk_on=True,
        fixture_data_not_live_market_data=True,
    )


def _risk_off_signal_evidence() -> artifact.EtfSmaNextExperimentOfflineSignalEvidence:
    return _signal_evidence(
        _signal(*(200 * ("10",))),
        actionable_risk_on=False,
        fixture_data_not_live_market_data=True,
    )


def _signal_evidence(
    signal: EtfSmaSignalResult,
    *,
    actionable_risk_on: bool,
    fixture_data_not_live_market_data: bool,
) -> artifact.EtfSmaNextExperimentOfflineSignalEvidence:
    return artifact.EtfSmaNextExperimentOfflineSignalEvidence(
        evidence_id=_SIGNAL_EVIDENCE_ID,
        symbol=signal.symbol,
        asset_class=signal.asset_class,
        as_of=signal.as_of.isoformat(),
        status=signal.posture,
        short_window=signal.short_window,
        long_window=signal.long_window,
        total_bar_count=signal.total_bar_count,
        usable_bar_count=signal.usable_bar_count,
        ignored_future_bar_count=signal.ignored_future_bar_count,
        latest_close=signal.latest_close,
        short_sma=signal.short_sma,
        long_sma=signal.long_sma,
        actionable_risk_on=actionable_risk_on,
        provenance="deterministic_unit_test_fixture_bars_not_live_market_data",
        fixture_data_not_live_market_data=fixture_data_not_live_market_data,
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


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal, datetime, Path))
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
