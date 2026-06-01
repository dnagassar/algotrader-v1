from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path

import pytest

from algotrader.cli import main
from algotrader.core.types import Bar
from algotrader.errors import ValidationError
import algotrader.orchestration.etf_sma_paper_broker_preview as m349
from algotrader.orchestration.etf_sma_execution_preview_bridge import (
    EtfSmaExecutionPreviewConfig,
    build_etf_sma_execution_preview,
)
from algotrader.orchestration.etf_sma_preview_jsonl_artifact import (
    EtfSmaPreviewJsonlRecord,
    build_etf_sma_preview_jsonl_record,
)
from algotrader.signals.etf_sma_evaluator import (
    EtfSmaSignalConfig,
    evaluate_etf_sma_signal,
)


MODULE_PATH = Path("src/algotrader/orchestration/etf_sma_paper_broker_preview.py")
_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
_AS_OF_200 = _START + timedelta(days=199)
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "decimal",
    "json",
    "pathlib",
    "typing",
    "algotrader.core.validation",
    "algotrader.errors",
    "algotrader.orchestration.etf_sma_preview_jsonl_artifact",
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
    "download",
    "liquidate",
    "post",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_bullish_spy_preview_creates_submit_disabled_broker_payload() -> None:
    preview = _accepted_m349_preview()
    payload = preview.to_dict()

    assert preview.run_id == "m349_etf_sma_paper_preview_only"
    assert preview.symbol == "SPY"
    assert preview.asset_class == "equity"
    assert preview.signal_posture == "bullish_risk_on"
    assert preview.preview_status == "broker_facing_local_payload_previewed"
    assert preview.accepted_for_broker_payload_preview is True
    assert preview.blocked is False
    assert preview.skipped is False
    assert preview.skip_reason == ""
    assert preview.block_reason == ""
    assert preview.side == "buy"
    assert preview.order_type == "market"
    assert preview.time_in_force == "day"
    assert preview.max_notional == Decimal("25.00")
    assert preview.notional == Decimal("25.00")
    assert preview.quantity is None
    assert preview.broker_payload_preview == {
        "asset_class": "equity",
        "notional": "25.00",
        "order_type": "market",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    assert payload["broker_payload_preview"] == preview.broker_payload_preview


def test_all_submit_and_mutation_flags_remain_false() -> None:
    preview = _accepted_m349_preview()
    payload = preview.to_dict()

    assert preview.submit_allowed is False
    assert preview.submitted is False
    assert preview.mutated is False
    assert preview.broker_action_performed is False
    assert preview.broker_preview_performed is False
    assert preview.local_payload_preview_performed is True
    assert payload["submit_allowed"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_preview_performed"] is False


def test_defensive_signal_produces_no_payload_and_skip_reason() -> None:
    preview = _m349_preview(_source_record("defensive"))

    assert preview.accepted_for_broker_payload_preview is False
    assert preview.skipped is True
    assert preview.skip_reason == "signal_posture_not_bullish"
    assert preview.notional is None
    assert preview.broker_payload_preview is None
    assert preview.local_payload_preview_performed is False


def test_insufficient_history_signal_produces_no_payload_and_skip_reason() -> None:
    preview = _m349_preview(_source_record("insufficient-history"))

    assert preview.signal_posture == "insufficient_history"
    assert preview.accepted_for_broker_payload_preview is False
    assert preview.skipped is True
    assert preview.skip_reason == "signal_insufficient_history"
    assert preview.broker_payload_preview is None


def test_non_spy_symbol_is_skipped_before_payload_preview() -> None:
    preview = _m349_preview(_source_record("bullish", symbol="IVV"))

    assert preview.symbol == "IVV"
    assert preview.accepted_for_broker_payload_preview is False
    assert preview.skipped is True
    assert preview.skip_reason == "symbol_not_allowed"
    assert preview.broker_payload_preview is None


def test_notional_above_twenty_five_is_skipped_if_source_is_unsafe() -> None:
    source = _unsafe_source_record(
        _source_record("bullish"),
        preview_notional=Decimal("25.01"),
        max_notional=Decimal("25.01"),
    )

    preview = _m349_preview(source)

    assert preview.accepted_for_broker_payload_preview is False
    assert preview.skipped is True
    assert preview.skip_reason == "notional_exceeds_m349_cap"
    assert preview.broker_payload_preview is None


def test_config_rejects_notional_cap_above_twenty_five() -> None:
    with pytest.raises(ValidationError, match="25.00"):
        m349.EtfSmaPaperBrokerPreviewConfig(max_notional=Decimal("25.01"))


def test_missing_usable_m348_revalidation_blocks_preview() -> None:
    snapshot = m349.EtfSmaPaperSnapshotEvidence(
        prior_snapshot_revalidation_state="insufficient_observation",
        fresh_snapshot_status="blocked_missing_credentials",
        usable_for_manual_review=False,
    )

    preview = _m349_preview(_source_record("bullish"), snapshot=snapshot)

    assert preview.blocked is True
    assert preview.block_reason == "prior_snapshot_not_usable"
    assert preview.broker_payload_preview is None


def test_unexpected_positions_block_preview() -> None:
    snapshot = m349.EtfSmaPaperSnapshotEvidence(
        position_count=1,
        position_symbols=("MSFT",),
    )

    preview = _m349_preview(_source_record("bullish"), snapshot=snapshot)

    assert preview.blocked is True
    assert preview.block_reason == "prior_snapshot_unexpected_positions"
    assert preview.broker_payload_preview is None


def test_recent_open_orders_block_preview() -> None:
    snapshot = m349.EtfSmaPaperSnapshotEvidence(recent_open_order_count=1)

    preview = _m349_preview(_source_record("bullish"), snapshot=snapshot)

    assert preview.blocked is True
    assert preview.block_reason == "prior_snapshot_recent_open_orders_present"
    assert preview.broker_payload_preview is None


def test_recent_order_metadata_gap_blocks_preview() -> None:
    snapshot = m349.EtfSmaPaperSnapshotEvidence(
        recent_order_query_metadata_complete=False,
    )

    preview = _m349_preview(_source_record("bullish"), snapshot=snapshot)

    assert preview.blocked is True
    assert preview.block_reason == "prior_snapshot_recent_order_metadata_incomplete"
    assert preview.broker_payload_preview is None


def test_live_or_credential_evidence_blocks_preview() -> None:
    snapshot = m349.EtfSmaPaperSnapshotEvidence(credential_leak_evidence=True)

    preview = _m349_preview(_source_record("bullish"), snapshot=snapshot)

    assert preview.blocked is True
    assert preview.block_reason == "prior_snapshot_live_or_credential_evidence"


def test_labels_and_profit_claim_are_fixed() -> None:
    preview = _accepted_m349_preview()

    assert preview.labels == m349.ETF_SMA_PAPER_BROKER_PREVIEW_LABELS
    assert "paper_lab_only" in preview.labels
    assert "signal_evaluation_only" in preview.labels
    assert "not_live_authorized" in preview.labels
    assert "profit_claim=none" in preview.labels
    assert preview.profit_claim == "none"


def test_source_live_authorized_label_is_rejected() -> None:
    source = _unsafe_source_record(
        _source_record("bullish"),
        labels=("live_authorized",),
    )

    with pytest.raises(ValidationError, match="live authorization"):
        _m349_preview(source)


def test_preview_is_frozen_slotted_and_primitive_dict() -> None:
    preview = _accepted_m349_preview()

    assert hasattr(m349.EtfSmaPaperBrokerPreview, "__slots__")
    assert not hasattr(preview, "__dict__")
    with pytest.raises(FrozenInstanceError):
        preview.skipped = True

    _assert_primitive_only(preview.to_dict())


def test_json_rendering_is_deterministic() -> None:
    preview = _accepted_m349_preview()

    first = m349.render_etf_sma_paper_broker_preview_json(preview)
    second = m349.render_etf_sma_paper_broker_preview_json(preview)

    assert first == second
    payload = json.loads(first)
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_payload_preview"]["symbol"] == "SPY"


def test_writer_creates_newline_terminated_jsonl_record(tmp_path: Path) -> None:
    output_path = tmp_path / "runs" / "paper_lab" / "m349.jsonl"
    preview = _accepted_m349_preview()

    result = m349.write_etf_sma_paper_broker_preview(
        preview,
        m349.EtfSmaPaperBrokerPreviewWriteConfig(
            output_path=output_path,
            create_parent_dirs=True,
        ),
    )

    text = output_path.read_text(encoding="utf-8")
    assert result.record_count == 1
    assert result.newline_terminated is True
    assert text.endswith("\n")
    assert len(text.splitlines()) == 1
    assert json.loads(text)["run_id"] == "m349_etf_sma_paper_preview_only"
    assert result.submitted is False
    assert result.mutated is False


def test_cli_runs_preview_only_and_writes_local_log(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    snapshot_log = tmp_path / "m348.jsonl"
    run_log = tmp_path / "m349.jsonl"
    _write_m348_snapshot_log(snapshot_log)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)

    exit_code = main(
        (
            "--profile",
            "paper",
            "etf-sma-paper-preview-only",
            "--prior-snapshot-run-log",
            str(snapshot_log),
            "--prior-snapshot-run-id",
            "m348_etf_sma_fresh_read_only_snapshot",
            "--run-log",
            str(run_log),
            "--run-id",
            "m349_etf_sma_paper_preview_only",
            "--format",
            "json",
        )
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    records = [
        json.loads(line)
        for line in run_log.read_text(encoding="utf-8").splitlines()
    ]
    assert exit_code == 0
    assert captured.err == ""
    assert payload["run_id"] == "m349_etf_sma_paper_preview_only"
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_preview_performed"] is False
    assert payload["local_payload_preview_performed"] is True
    assert payload["broker_payload_preview"]["symbol"] == "SPY"
    assert records == [payload]


def test_cli_rejects_non_paper_profile_without_writing_log(
    tmp_path: Path,
    capsys,
) -> None:
    snapshot_log = tmp_path / "m348.jsonl"
    run_log = tmp_path / "m349.jsonl"
    _write_m348_snapshot_log(snapshot_log)

    exit_code = main(
        (
            "--profile",
            "dev",
            "etf-sma-paper-preview-only",
            "--prior-snapshot-run-log",
            str(snapshot_log),
            "--run-log",
            str(run_log),
            "--format",
            "json",
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["block_reason"] == "paper_profile_required"
    assert payload["submitted"] is False
    assert not run_log.exists()


def test_module_has_no_broker_sdk_network_or_execution_imports() -> None:
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
    assert "live_authorized=true" in source


def test_module_does_not_use_execution_intent_or_execution_plan() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source

    field_names = {field.name for field in fields(m349.EtfSmaPaperBrokerPreview)}
    assert "execution_" + "intent" not in field_names
    assert "execution_" + "plan" not in field_names


def _accepted_m349_preview() -> m349.EtfSmaPaperBrokerPreview:
    return _m349_preview(_source_record("bullish"))


def _m349_preview(
    source_record: EtfSmaPreviewJsonlRecord,
    *,
    snapshot: m349.EtfSmaPaperSnapshotEvidence | None = None,
) -> m349.EtfSmaPaperBrokerPreview:
    return m349.build_etf_sma_paper_broker_preview(
        source_record,
        snapshot or m349.EtfSmaPaperSnapshotEvidence(),
        m349.EtfSmaPaperBrokerPreviewConfig(
            run_id="m349_etf_sma_paper_preview_only",
            source_record_id="m347_etf_sma_preview_jsonl_record:test",
        ),
    )


def _source_record(
    scenario: str,
    *,
    symbol: str = "SPY",
) -> EtfSmaPreviewJsonlRecord:
    closes_by_scenario = {
        "bullish": 150 * ("10",) + 50 * ("20",),
        "defensive": 200 * ("10",),
        "insufficient-history": 149 * ("10",) + 50 * ("20",),
    }
    signal = evaluate_etf_sma_signal(
        _bars(*closes_by_scenario[scenario], symbol=symbol),
        EtfSmaSignalConfig(as_of=_AS_OF_200, symbol=symbol),
    )
    preview = build_etf_sma_execution_preview(
        signal,
        EtfSmaExecutionPreviewConfig(as_of=_AS_OF_200),
    )
    return build_etf_sma_preview_jsonl_record(preview)


def _bars(*closes: str, symbol: str) -> tuple[Bar, ...]:
    return tuple(
        Bar(
            symbol=symbol,
            timestamp=_START + timedelta(days=index),
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal("100"),
        )
        for index, close in enumerate(closes)
    )


def _unsafe_source_record(
    source: EtfSmaPreviewJsonlRecord,
    **overrides: object,
) -> EtfSmaPreviewJsonlRecord:
    record = object.__new__(EtfSmaPreviewJsonlRecord)
    values = {field.name: getattr(source, field.name) for field in fields(source)}
    values.update(overrides)
    for name, value in values.items():
        object.__setattr__(record, name, value)

    return record


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


def _write_m348_snapshot_log(path: Path) -> None:
    base = {
        "account_observation_available": True,
        "command": "paper-lab-snapshot",
        "gate_summary": {
            "profile_gate": {"detail": "paper_profile_ready", "passed": True}
        },
        "mutated": False,
        "ok": True,
        "orders_observation_available": True,
        "positions_observation_available": True,
        "redaction": "credentials_redacted",
        "run_id": "m348_etf_sma_fresh_read_only_snapshot",
        "submitted": False,
        "unavailable_observations": [],
        "unavailable_reasons": {},
        "recent_order_query_attempted": True,
        "recent_order_query_available": True,
        "recent_order_query_after": None,
        "recent_order_query_asset_class_filter": "all",
        "recent_order_query_contract_version": "paper_recent_order_query_v1",
        "recent_order_query_direction": "desc",
        "recent_order_query_limit": 100,
        "recent_order_query_metadata_complete": True,
        "recent_order_query_metadata_missing_fields": [],
        "recent_order_query_nested": False,
        "recent_order_query_returned_count": 0,
        "recent_order_query_side_filter": "all",
        "recent_order_query_sort": "created_at",
        "recent_order_query_source": "alpaca_sdk_client.get_orders",
        "recent_order_query_status_filter": "open",
        "recent_order_query_symbol_filter": "all",
        "recent_order_query_until": None,
    }
    records = (
        {
            **base,
            "event_type": "paper_lab_snapshot_requested",
        },
        {
            **base,
            "account": {"cash": "1999.9", "currency": "USD"},
            "event_type": "paper_lab_snapshot_account_observed",
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_positions_observed",
            "position_count": 0,
            "position_symbols": [],
            "positions": [],
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_orders_observed",
            "recent_order_count": 0,
            "recent_orders": [],
        },
    )
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


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
