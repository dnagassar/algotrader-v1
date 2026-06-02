from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from decimal import Decimal
import json
from pathlib import Path

import pytest

from algotrader.cli import main
from algotrader.errors import ValidationError
import algotrader.execution.etf_sma_paper_preview as m368


MODULE_PATH = Path("src/algotrader/execution/etf_sma_paper_preview.py")
_RUN_ID = "m368_spy_etf_sma_broker_preview_only"
_M368A_RUN_ID = "m368a_offline_spy_etf_sma_next_experiment_review"
_M368A_PATH = (
    "runs/paper_lab/m368a_offline_spy_etf_sma_next_experiment_review.jsonl"
)
_SNAPSHOT_RUN_ID = "m368_fresh_read_only_paper_snapshot"
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "decimal",
    "json",
    "pathlib",
    "typing",
    "algotrader.errors",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "liquidate",
    "post",
    "request",
    "replace_order",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_ready_m368_preview_builds_tiny_spy_buy_shape() -> None:
    preview = _ready_preview()
    payload = preview.to_dict()

    assert preview.run_id == _RUN_ID
    assert preview.command == "etf-sma-m368-broker-preview-only"
    assert preview.builder_name == "build_etf_sma_m368_paper_preview"
    assert preview.source_m368a_artifact_path == str(Path(_M368A_PATH))
    assert preview.source_m368a_decision == "ready_for_separate_broker_preview_milestone"
    assert preview.decision == "ready_for_operator_review_before_tiny_spy_paper_submit"
    assert preview.required_next_milestone == (
        "M369 - Explicit operator review for tiny SPY paper submit"
    )
    assert preview.blockers == ()
    assert preview.symbol == "SPY"
    assert preview.asset_class == "equity"
    assert preview.side == "buy"
    assert preview.order_type == "market"
    assert preview.time_in_force == "day"
    assert preview.notional_cap == Decimal("25.00")
    assert preview.notional == Decimal("25.00")
    assert preview.allowlist == ("SPY",)
    assert preview.preview_order == {
        "asset_class": "equity",
        "notional": "25.00",
        "order_type": "market",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    assert payload["fresh_paper_snapshot_summary"]["cash"] == "1999.81"
    assert payload["position_count"] == 0
    assert payload["position_symbols"] == []
    assert payload["open_order_count"] == 0


def test_m368_preview_flags_remain_preview_only_and_non_mutating() -> None:
    preview = _ready_preview()
    payload = preview.to_dict()

    assert preview.labels == m368.ETF_SMA_M368_PAPER_PREVIEW_LABELS
    assert preview.preview_only is True
    assert preview.paper_only is True
    assert preview.not_live_authorized is True
    assert preview.profit_claim == "none"
    assert preview.submit_authorized is False
    assert preview.submitted is False
    assert preview.mutated is False
    assert preview.broker_action_performed is False
    assert preview.broker_preview_performed is False
    assert preview.local_payload_preview_performed is True
    assert payload["submit_authorized"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False


@pytest.mark.parametrize(
    ("field_name", "value", "expected_blocker"),
    (
        ("decision", "operator_review_required", "m368a_decision_not_ready"),
        ("submit_authorized", True, "m368a_submit_authorized_not_false"),
        ("submitted", True, "m368a_submitted_not_false"),
        ("mutated", True, "m368a_mutated_not_false"),
        ("symbol", "IVV", "m368a_symbol_not_spy"),
    ),
)
def test_m368a_source_safety_gaps_block_preview(
    field_name: str,
    value: object,
    expected_blocker: str,
) -> None:
    record = _ready_m368a_record()
    record[field_name] = value

    preview = _build_preview(record, m368.EtfSmaM368PaperSnapshotSummary())

    assert preview.decision == "blocked_before_operator_review_for_tiny_spy_paper_submit"
    assert expected_blocker in preview.blockers
    assert preview.preview_order is None
    assert preview.submit_authorized is False
    assert preview.submitted is False
    assert preview.mutated is False


@pytest.mark.parametrize(
    ("snapshot", "expected_blocker"),
    (
        (
            m368.EtfSmaM368PaperSnapshotSummary(
                account_observation_available=False,
            ),
            "account_observation_unavailable",
        ),
        (
            m368.EtfSmaM368PaperSnapshotSummary(
                position_count=1,
                position_symbols=("SPY",),
            ),
            "positions_present",
        ),
        (
            m368.EtfSmaM368PaperSnapshotSummary(
                position_count=1,
                position_symbols=("MSFT",),
            ),
            "non_spy_position_present",
        ),
        (
            m368.EtfSmaM368PaperSnapshotSummary(open_order_count=1),
            "open_orders_present",
        ),
        (
            m368.EtfSmaM368PaperSnapshotSummary(
                recent_order_query_metadata_complete=False,
            ),
            "recent_order_metadata_incomplete",
        ),
    ),
)
def test_fresh_snapshot_gaps_block_preview(
    snapshot: m368.EtfSmaM368PaperSnapshotSummary,
    expected_blocker: str,
) -> None:
    preview = _build_preview(_ready_m368a_record(), snapshot)

    assert preview.decision == "blocked_before_operator_review_for_tiny_spy_paper_submit"
    assert expected_blocker in preview.blockers
    assert preview.preview_order is None
    assert preview.local_payload_preview_performed is False


def test_m368a_reset_summary_can_be_used_as_explicit_snapshot_evidence() -> None:
    snapshot = m368.m368a_reset_summary_as_snapshot(_ready_m368a_record())

    assert snapshot.snapshot_source == "m368a_reset_evidence_summary"
    assert snapshot.snapshot_evidence_id == "m366_fresh_paper_lab_reset_snapshot"
    assert snapshot.cash == Decimal("1999.81")
    assert snapshot.currency == "USD"
    assert snapshot.position_count == 0
    assert snapshot.open_order_count == 0
    assert snapshot.blockers() == ()


def test_loader_and_writer_are_deterministic_jsonl(tmp_path: Path) -> None:
    source_path = tmp_path / "m368a.jsonl"
    output_path = tmp_path / "runs" / "paper_lab" / "m368.jsonl"
    _write_jsonl(source_path, [_ready_m368a_record()])

    record = m368.load_m368a_review_artifact_record(source_path)
    preview = _build_preview(
        record,
        m368.m368a_reset_summary_as_snapshot(record),
        source_path=source_path,
    )
    result = m368.write_etf_sma_m368_paper_preview(
        preview,
        m368.EtfSmaM368PaperPreviewWriteConfig(
            output_path=output_path,
            create_parent_dirs=True,
        ),
    )

    text = output_path.read_text(encoding="utf-8")
    first = m368.render_etf_sma_m368_paper_preview_json(preview)
    second = m368.render_etf_sma_m368_paper_preview_json(preview)
    assert first == second
    assert text.endswith("\n")
    assert len(text.splitlines()) == 1
    payload = json.loads(text)
    assert payload["run_id"] == _RUN_ID
    assert payload["submit_authorized"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert result.submit_authorized is False
    assert result.submitted is False
    assert result.mutated is False


def test_loader_rejects_missing_or_ambiguous_m368a_records(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="existing file"):
        m368.load_m368a_review_artifact_record(tmp_path / "missing.jsonl")

    source_path = tmp_path / "m368a.jsonl"
    _write_jsonl(source_path, [_ready_m368a_record(), _ready_m368a_record()])
    with pytest.raises(ValidationError, match="exactly one"):
        m368.load_m368a_review_artifact_record(source_path, run_id=None)


def test_preview_is_frozen_slotted_and_primitive() -> None:
    preview = _ready_preview()

    assert hasattr(m368.EtfSmaM368PaperPreview, "__slots__")
    assert not hasattr(preview, "__dict__")
    with pytest.raises(FrozenInstanceError):
        preview.mutated = True

    _assert_primitive_only(preview.to_dict())


def test_cli_reads_local_m368a_and_snapshot_logs_without_submit(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    m368a_path = tmp_path / "m368a.jsonl"
    snapshot_path = tmp_path / "snapshot.jsonl"
    output_path = tmp_path / "m368.jsonl"
    _write_jsonl(m368a_path, [_ready_m368a_record()])
    _write_snapshot_log(snapshot_path)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)

    exit_code = main(
        (
            "--profile",
            "paper",
            "etf-sma-m368-broker-preview-only",
            "--m368a-run-log",
            str(m368a_path),
            "--fresh-snapshot-run-log",
            str(snapshot_path),
            "--fresh-snapshot-run-id",
            _SNAPSHOT_RUN_ID,
            "--run-log",
            str(output_path),
            "--run-id",
            _RUN_ID,
            "--format",
            "json",
        )
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert exit_code == 0
    assert captured.err == ""
    assert payload["decision"] == "ready_for_operator_review_before_tiny_spy_paper_submit"
    assert payload["preview_order"]["symbol"] == "SPY"
    assert payload["preview_order"]["side"] == "buy"
    assert payload["submit_authorized"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert records == [payload]


def test_cli_rejects_non_paper_profile_without_writing_log(
    tmp_path: Path,
    capsys,
) -> None:
    m368a_path = tmp_path / "m368a.jsonl"
    snapshot_path = tmp_path / "snapshot.jsonl"
    output_path = tmp_path / "m368.jsonl"
    _write_jsonl(m368a_path, [_ready_m368a_record()])
    _write_snapshot_log(snapshot_path)

    exit_code = main(
        (
            "--profile",
            "dev",
            "etf-sma-m368-broker-preview-only",
            "--m368a-run-log",
            str(m368a_path),
            "--fresh-snapshot-run-log",
            str(snapshot_path),
            "--run-log",
            str(output_path),
            "--format",
            "json",
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["blockers"] == ["paper_profile_required"]
    assert payload["submit_authorized"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert not output_path.exists()


def test_module_has_no_broker_sdk_network_or_mutation_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _ready_preview() -> m368.EtfSmaM368PaperPreview:
    return _build_preview(
        _ready_m368a_record(),
        m368.EtfSmaM368PaperSnapshotSummary(cash=Decimal("1999.81"), currency="USD"),
    )


def _build_preview(
    record: dict[str, object],
    snapshot: m368.EtfSmaM368PaperSnapshotSummary,
    *,
    source_path: Path | str = _M368A_PATH,
) -> m368.EtfSmaM368PaperPreview:
    return m368.build_etf_sma_m368_paper_preview(
        record,
        snapshot,
        m368.EtfSmaM368PaperPreviewConfig(
            run_id=_RUN_ID,
            source_m368a_artifact_path=source_path,
        ),
    )


def _ready_m368a_record() -> dict[str, object]:
    return {
        "artifact_version": "etf_sma_next_experiment_review_artifact_v1",
        "asset_class": "equity",
        "blockers": [],
        "broker_action_performed": False,
        "broker_preview_performed": False,
        "cap": "25.00",
        "decision": "ready_for_separate_broker_preview_milestone",
        "evidence_ids": [
            "m366_fresh_paper_lab_reset_snapshot",
            "m368a_offline_spy_etf_sma_fixture_signal",
        ],
        "labels": [
            "paper_lab_only",
            "offline_only",
            "research_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "mutated": False,
        "offline_signal_actionable_risk_on": True,
        "offline_signal_evidence_summary": {
            "actionable_risk_on": True,
            "as_of": "2025-07-20T00:00:00+00:00",
            "asset_class": "equity",
            "evidence_id": "m368a_offline_spy_etf_sma_fixture_signal",
            "fixture_data_not_live_market_data": True,
            "latest_close": "20",
            "long_sma": "12.5",
            "long_window": 200,
            "short_sma": "20",
            "short_window": 50,
            "status": "bullish_risk_on",
            "symbol": "SPY",
            "usable_bar_count": 200,
        },
        "offline_signal_status": "bullish_risk_on",
        "reason": "ready for M368 preview only",
        "record_type": "etf_sma_next_experiment_review_artifact_record",
        "required_next_milestone": (
            "M368 - SPY ETF/SMA broker-facing preview-only milestone"
        ),
        "reset_evidence_summary": {
            "account_observed": True,
            "cash": "1999.81",
            "classification": "paper_lab_flat_clean",
            "currency": "USD",
            "evidence_id": "m366_fresh_paper_lab_reset_snapshot",
            "mutated": False,
            "no_open_orders": True,
            "open_orders_observed": True,
            "position_count": 0,
            "position_symbols": [],
            "positions_observed": True,
            "recent_order_count": 0,
            "spy_absent_or_zero": True,
            "submitted": False,
        },
        "run_id": _M368A_RUN_ID,
        "separate_broker_preview_milestone_allowed": True,
        "separate_preview_milestone_required": True,
        "signal_evidence_id": "m368a_offline_spy_etf_sma_fixture_signal",
        "submit_authorized": False,
        "submitted": False,
        "symbol": "SPY",
    }


def _write_snapshot_log(path: Path) -> None:
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
        "run_id": _SNAPSHOT_RUN_ID,
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
            "account": {"cash": "1999.81", "currency": "USD"},
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
    _write_jsonl(path, records)


def _write_jsonl(path: Path, records) -> None:
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal))
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
