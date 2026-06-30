from __future__ import annotations

import ast
from datetime import UTC, datetime
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace

import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.alpaca_client import (
    AlpacaAccountResponse,
    AlpacaOrderResponse,
    AlpacaPositionResponse,
    AlpacaRecentOrderQuery,
)
from algotrader.execution.read_only_paper_broker_snapshot_reconciliation import (
    READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
    READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
    ReadOnlyPaperBrokerSnapshotObservation,
    ReadOnlyPaperBrokerSnapshotReconciliationConfig,
    build_read_only_paper_broker_snapshot_reconciliation,
    write_read_only_paper_broker_snapshot_reconciliation_jsonl,
)
from tests.fakes.alpaca import FakeAlpacaClient


MODULE_PATH = Path(
    "src/algotrader/execution/read_only_paper_broker_snapshot_reconciliation.py"
)
GENERATED_AT = "2026-06-06T00:00:00+00:00"
SENSITIVE_API_KEY = "m403-sensitive-api-key"
SENSITIVE_SECRET_KEY = "m403-sensitive-secret-key"
EXPECTED_ACCOUNT_ID = "paper-account-1"
EXPECTED_ACCOUNT_NUMBER = "paper-account-number-1"
MISMATCHED_ACCOUNT_ID = "different-paper-account"
ORDER_TIME = datetime(2026, 6, 6, 14, 30, tzinfo=UTC)
FORBIDDEN_IMPORT_PREFIXES = (
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "os",
    "requests",
    "socket",
    "subprocess",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "create_order",
    "download",
    "getenv",
    "liquidate",
    "replace_order",
    "request",
    "socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_ready_snapshot_reconciliation_writes_one_safe_record(tmp_path) -> None:  # noqa: ANN001
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "m403.jsonl"

    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(source_review_packet, run_log),
        _observation(),
    )
    result = write_read_only_paper_broker_snapshot_reconciliation_jsonl(
        payload,
        run_log,
    )

    assert result.record_count == 1
    assert _read_jsonl(run_log) == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["milestone"] == "M403"
    assert payload["record_type"] == "read_only_paper_broker_snapshot_reconciliation"
    assert payload["command"] == READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND
    assert payload["run_id"] == READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID
    assert payload["source_review_state"] == "ready_for_operator_review"
    assert payload["source_cycle_decision"] == "buy_preview"
    assert payload["paper_profile_gate_passed"] is True
    assert payload["broker_state_observed"] is True
    assert payload["broker_access_performed"] is True
    assert payload["account_read_attempted"] is True
    assert payload["positions_read_attempted"] is True
    assert payload["open_orders_read_attempted"] is True
    assert payload["account_observed"] is True
    assert payload["positions_observed"] is True
    assert payload["orders_observed"] is True
    assert payload["recent_orders_observed"] is False
    assert payload["account"]["cash"] == "100000"
    assert payload["account"]["currency"] == "USD"
    assert payload["account"]["status"] == "ACTIVE"
    assert "account_id" not in payload["account"]
    assert payload["expected_account_id_loaded"] is True
    assert payload["expected_account_matched"] is True
    assert payload["expected_account_match_mode"] == "account_id"
    assert payload["account_validation_blocker"] == "none"
    assert payload["account_status_observed"] is True
    assert payload["account_status"] == "ACTIVE"
    assert payload["cash"] == "100000"
    assert payload["buying_power"] == ""
    assert payload["currency"] == "USD"
    assert payload["position_count"] == 0
    assert payload["position_symbols"] == []
    assert payload["spy_position_observed"] is True
    assert payload["spy_position_present"] is False
    assert payload["spy_position_qty"] == "0"
    assert payload["unexpected_non_spy_positions"] == []
    assert payload["unexpected_non_spy_positions_observed"] is True
    assert payload["open_order_count"] == 0
    assert payload["spy_open_orders_observed"] is True
    assert payload["open_spy_order_count"] == 0
    assert payload["recent_order_count"] == 0
    assert payload["recent_spy_order_count"] == 0
    assert payload["broker_observation_state"] == "observed"
    assert payload["reconciliation_state"] == "ready_for_operator_review"
    assert payload["blocker_classification"] == "ready_for_operator_review"
    assert payload["blockers"] == []
    _assert_no_broker_authority(payload)


def test_open_spy_order_blocks_future_same_symbol_submit(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        _observation(open_orders=({"symbol": "SPY", "status": "accepted"},)),
    )

    assert payload["open_order_count"] == 1
    assert payload["open_spy_order_count"] == 1
    assert payload["reconciliation_state"] == "blocked_open_order_present"
    assert "open_spy_order_present" in payload["blockers"]
    _assert_no_broker_authority(payload)


def test_open_non_spy_order_blocks_future_submit(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        _observation(open_orders=({"symbol": "MSFT", "status": "accepted"},)),
    )

    assert payload["open_order_count"] == 1
    assert payload["open_order_symbols"] == ["MSFT"]
    assert payload["open_spy_order_count"] == 0
    assert payload["unexpected_non_spy_open_orders"] == [
        {"symbol": "MSFT", "status": "accepted"}
    ]
    assert payload["unexpected_non_spy_open_order_count"] == 1
    assert payload["reconciliation_state"] == "blocked_open_order_present"
    assert "open_order_present" in payload["blockers"]
    assert "unexpected_non_spy_open_order" in payload["blockers"]
    _assert_no_broker_authority(payload)


def test_unexpected_non_spy_position_blocks_review(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        _observation(positions=({"symbol": "MSFT", "quantity": "3"},)),
    )

    assert payload["position_symbols"] == ["MSFT"]
    assert payload["unexpected_non_spy_positions"] == [
        {"symbol": "MSFT", "quantity": "3"}
    ]
    assert payload["reconciliation_state"] == "blocked_unexpected_non_spy_position"
    assert "unexpected_non_spy_position" in payload["blockers"]
    _assert_no_broker_authority(payload)


def test_spy_position_is_observed_without_authorizing_close_or_sell(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        _observation(positions=({"symbol": "SPY", "quantity": "0.5"},)),
    )

    assert payload["spy_position_present"] is True
    assert payload["spy_position_qty"] == "0.5"
    assert payload["unexpected_non_spy_positions"] == []
    assert payload["reconciliation_state"] == "ready_for_operator_review"
    _assert_no_broker_authority(payload)


def test_broker_unavailable_blocks_without_submit_or_mutation(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        ReadOnlyPaperBrokerSnapshotObservation(
            paper_profile_gate_passed=True,
            unavailable_observations=("broker",),
            unavailable_reasons={"broker": {"error_type": "RuntimeError"}},
            credential_access_attempted=True,
        ),
    )

    assert payload["broker_observation_state"] == "broker_unavailable"
    assert payload["reconciliation_state"] == "blocked_broker_unavailable"
    assert "broker_observation_unavailable" in payload["blockers"]
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is True
    _assert_no_broker_authority(payload)


def test_incomplete_observation_blocks_without_forcing_ready(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        ReadOnlyPaperBrokerSnapshotObservation(
            paper_profile_gate_passed=True,
            account_read_attempted=True,
            positions_read_attempted=True,
            open_orders_read_attempted=True,
            broker_access_performed=True,
            account_observed=True,
            positions_observed=True,
            account={
                "account_id": EXPECTED_ACCOUNT_ID,
                "cash": "100000",
                "currency": "USD",
                "status": "ACTIVE",
            },
            expected_account_check={
                "observed_account_id_present": True,
                "observed_account_number_present": False,
                "expected_account_configured": True,
                "expected_account_id_matched": True,
                "expected_account_number_matched": None,
                "expected_account_matched": True,
                "expected_account_match_mode": "account_id",
            },
            positions=(),
            unavailable_observations=("open_orders",),
            network_access_attempted=True,
            credential_access_attempted=True,
        ),
    )

    assert payload["broker_observation_state"] == "observation_incomplete"
    assert payload["reconciliation_state"] == "blocked_observation_incomplete"
    assert "open_orders_observation_unavailable" in payload["blockers"]
    _assert_no_broker_authority(payload)


def test_profile_gate_failed_writes_blocked_artifact_shape(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        ReadOnlyPaperBrokerSnapshotObservation(
            paper_profile_gate_passed=False,
            profile_gate_detail="paper profile required",
        ),
    )

    assert payload["broker_observation_state"] == "profile_gate_failed"
    assert payload["reconciliation_state"] == "blocked_profile_gate_failed"
    assert payload["paper_profile_gate_passed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert "paper_profile_gate_failed" in payload["blockers"]
    _assert_no_broker_authority(payload)


def test_live_url_detected_blocks_without_broker_observation(tmp_path) -> None:  # noqa: ANN001
    payload = build_read_only_paper_broker_snapshot_reconciliation(
        _config(_write_source_review_packet(tmp_path), tmp_path / "m403.jsonl"),
        ReadOnlyPaperBrokerSnapshotObservation(
            paper_profile_gate_passed=True,
            profile_gate_detail="live Alpaca URL detected for paper snapshot",
            live_url_detected=True,
            unavailable_observations=(
                "account",
                "positions",
                "open_orders",
                "recent_orders",
            ),
            credential_access_attempted=True,
        ),
    )

    assert payload["live_url_detected"] is True
    assert payload["broker_observation_state"] == "live_url_detected"
    assert payload["reconciliation_state"] == "blocked_live_url_detected"
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is True
    assert "live_url_detected" in payload["blockers"]
    _assert_no_broker_authority(payload)


def test_cli_dispatch_reads_account_before_positions_and_open_orders(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeM403AlpacaClient(
            positions=[],
        ),
    )
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders",
    ]
    assert fake_client.submitted_requests == []
    assert [query.status_filter for query in fake_client.recent_order_queries] == [
        "open",
    ]
    assert [query.symbol_filter for query in fake_client.recent_order_queries] == [
        "SPY",
    ]
    assert records == [payload]
    assert payload["reconciliation_state"] == "ready_for_operator_review"
    assert payload["broker_state_observed"] is True
    assert payload["broker_access_performed"] is True
    assert payload["account_read_attempted"] is True
    assert payload["positions_read_attempted"] is True
    assert payload["open_orders_read_attempted"] is True
    assert payload["network_access_attempted"] is True
    assert payload["credential_access_attempted"] is True
    assert payload["account_observed"] is True
    assert payload["account"]["cash"] == "100000"
    assert payload["account"]["currency"] == "USD"
    assert payload["account"]["status"] == "ACTIVE"
    assert "account_id" not in payload["account"]
    assert payload["expected_account_id_loaded"] is True
    assert payload["expected_account_matched"] is True
    assert payload["expected_account_match_mode"] == "account_id"
    assert payload["account_validation_blocker"] == "none"
    assert payload["cash"] == "100000"
    assert payload["buying_power"] == "200000"
    assert payload["recent_orders_observed"] is False
    assert payload["recent_orders"] == []
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered
    assert EXPECTED_ACCOUNT_ID not in rendered
    _assert_no_broker_authority(payload)


def test_cli_matches_raw_sdk_account_id_alias_without_serializing_identity(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeM403AlpacaClient(
            positions=[],
            account_identity_shape="sdk_id",
            account_status="AccountStatus.ACTIVE",
        ),
    )
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_sdk_id_match.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 0
    assert fake_client.calls == ["get_account", "get_positions", "get_orders"]
    assert payload["reconciliation_state"] == "ready_for_operator_review"
    assert payload["expected_account_matched"] is True
    assert payload["expected_account_match_mode"] == "account_id"
    assert "account_id" not in payload["account"]
    assert "id" not in payload["account"]
    assert EXPECTED_ACCOUNT_ID not in rendered
    _assert_no_broker_authority(payload)


def test_cli_matches_raw_sdk_account_number_without_serializing_identity(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch, expected_account_id=EXPECTED_ACCOUNT_NUMBER)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeM403AlpacaClient(
            positions=[],
            account_id=MISMATCHED_ACCOUNT_ID,
            account_number=EXPECTED_ACCOUNT_NUMBER,
            account_identity_shape="sdk_account_number",
        ),
    )
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_account_number_match.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 0
    assert fake_client.calls == ["get_account", "get_positions", "get_orders"]
    assert payload["reconciliation_state"] == "ready_for_operator_review"
    assert payload["expected_account_matched"] is True
    assert payload["expected_account_match_mode"] == "account_number"
    assert "account_id" not in payload["account"]
    assert "account_number" not in payload["account"]
    assert MISMATCHED_ACCOUNT_ID not in rendered
    assert EXPECTED_ACCOUNT_NUMBER not in rendered
    _assert_no_broker_authority(payload)


def test_cli_expected_account_missing_blocks_before_broker_build(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch, expected_account_id=None)
    _forbid_broker_build(monkeypatch)
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_expected_missing.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 1
    assert _read_jsonl(run_log) == [payload]
    assert payload["reconciliation_state"] == "blocked_expected_account_id_unavailable"
    assert payload["broker_observation_state"] == "expected_account_id_unavailable"
    assert payload["expected_account_id_loaded"] is False
    assert payload["expected_account_matched"] is None
    assert payload["account_validation_blocker"] == "blocked_expected_account_id_unavailable"
    assert payload["broker_access_performed"] is False
    assert payload["account_read_attempted"] is False
    assert payload["positions_read_attempted"] is False
    assert payload["open_orders_read_attempted"] is False
    assert payload["positions_observed"] is False
    assert payload["open_orders_observed"] is False
    _assert_no_broker_authority(payload)


def test_cli_paper_profile_without_credentials_classifies_credentials_unavailable(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    _forbid_broker_build(monkeypatch)
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_credentials_missing.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 1
    assert _read_jsonl(run_log) == [payload]
    assert payload["reconciliation_state"] == "blocked_credentials_unavailable"
    assert payload["broker_observation_state"] == "credentials_unavailable"
    assert payload["account_validation_blocker"] == "blocked_credentials_unavailable"
    assert payload["broker_access_performed"] is False
    assert payload["account_read_attempted"] is False
    assert payload["positions_read_attempted"] is False
    assert payload["open_orders_read_attempted"] is False
    _assert_no_broker_authority(payload)


def test_cli_expected_account_mismatch_stops_before_positions_and_orders(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeM403AlpacaClient(
            positions=[],
            account_id=MISMATCHED_ACCOUNT_ID,
        ),
    )
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_expected_mismatch.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    rendered = json.dumps(payload, sort_keys=True) + run_log.read_text(
        encoding="utf-8"
    )
    assert exit_code == 1
    assert fake_client.calls == ["get_account"]
    assert payload["reconciliation_state"] == "blocked_expected_account_mismatch"
    assert payload["broker_observation_state"] == "expected_account_mismatch"
    assert payload["expected_account_id_loaded"] is True
    assert payload["expected_account_matched"] is False
    assert payload["account_validation_blocker"] == "blocked_expected_account_mismatch"
    assert payload["broker_access_performed"] is True
    assert payload["account_read_attempted"] is True
    assert payload["positions_read_attempted"] is False
    assert payload["open_orders_read_attempted"] is False
    assert EXPECTED_ACCOUNT_ID not in rendered
    assert MISMATCHED_ACCOUNT_ID not in rendered
    _assert_no_broker_authority(payload)


def test_cli_account_failure_stops_before_positions_and_orders(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch)
    fake_client = _install_fake_broker(
        monkeypatch,
        FakeM403AlpacaClient(
            positions=[],
            fail_account=True,
        ),
    )
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_account_failed.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 1
    assert fake_client.calls == ["get_account"]
    assert payload["reconciliation_state"] == "blocked_account_unavailable"
    assert payload["broker_observation_state"] == "account_unavailable"
    assert payload["account_validation_blocker"] == "blocked_account_unavailable"
    assert payload["broker_access_performed"] is True
    assert payload["account_read_attempted"] is True
    assert payload["positions_read_attempted"] is False
    assert payload["open_orders_read_attempted"] is False
    assert payload["unavailable_reasons"]["account"]["operation"] == "get_account"
    _assert_no_broker_authority(payload)


def test_cli_profile_gate_failure_writes_one_blocked_record_without_broker_build(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch, profile="live")
    _forbid_broker_build(monkeypatch)
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_profile_failed.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 2
    assert _read_jsonl(run_log) == [payload]
    assert payload["reconciliation_state"] == "blocked_profile_gate_failed"
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    _assert_no_broker_authority(payload)


def test_cli_live_url_detection_writes_one_blocked_record_without_broker_build(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_env(monkeypatch, base_url="https://api.alpaca.markets")
    _forbid_broker_build(monkeypatch)
    source_review_packet = _write_source_review_packet(tmp_path)
    run_log = tmp_path / "runs" / "paper_lab" / "m403_live_url_failed.jsonl"

    exit_code, payload = _run_json(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_COMMAND,
            "--source-review-packet",
            str(source_review_packet),
            "--run-id",
            READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
            "--run-log",
            str(run_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 1
    assert _read_jsonl(run_log) == [payload]
    assert payload["live_url_detected"] is True
    assert payload["reconciliation_state"] == "blocked_live_url_detected"
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is True
    assert "live_url_detected" in payload["blockers"]
    _assert_no_broker_authority(payload)


def test_module_does_not_import_network_or_broker_mutation_dependencies() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imported_modules: list[str] = []
    call_names: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module or "")
        elif isinstance(node, ast.Call):
            call_names.append(_call_name(node.func))

    assert [
        module
        for module in imported_modules
        if any(module == prefix or module.startswith(f"{prefix}.") for prefix in FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert [name for name in call_names if name in FORBIDDEN_CALL_NAMES] == []


class FakeM403AlpacaClient(FakeAlpacaClient):
    def __init__(
        self,
        positions: list[AlpacaPositionResponse] | None = None,
        *,
        account_id: str = EXPECTED_ACCOUNT_ID,
        account_number: str = EXPECTED_ACCOUNT_NUMBER,
        account_identity_shape: str = "account_id",
        account_status: str = "ACTIVE",
        fail_account: bool = False,
    ) -> None:
        super().__init__(positions=positions)
        self.account_id = account_id
        self.account_number = account_number
        self.account_identity_shape = account_identity_shape
        self.account_status = account_status
        self.fail_account = fail_account
        self.recent_order_queries: list[AlpacaRecentOrderQuery] = []

    def get_account(self) -> object:
        self.calls.append("get_account")
        if self.fail_account:
            raise RuntimeError("fake account call failed")
        if self.account_identity_shape == "sdk_id":
            return SimpleNamespace(
                id=self.account_id,
                status=self.account_status,
                cash=Decimal("100000"),
                buying_power=Decimal("200000"),
                equity=Decimal("100000"),
                currency="USD",
            )
        if self.account_identity_shape == "sdk_account_number":
            return SimpleNamespace(
                id=self.account_id,
                account_number=self.account_number,
                status=self.account_status,
                cash=Decimal("100000"),
                buying_power=Decimal("200000"),
                equity=Decimal("100000"),
                currency="USD",
            )
        return AlpacaAccountResponse(
            account_id=self.account_id,
            status=self.account_status,
            cash=Decimal("100000"),
            buying_power=Decimal("200000"),
            equity=Decimal("100000"),
        )

    def get_orders(self, query: AlpacaRecentOrderQuery) -> list[AlpacaOrderResponse]:
        self.calls.append("get_orders")
        self.recent_order_queries.append(query)
        if query.status_filter == "open":
            return []
        return [
            AlpacaOrderResponse(
                order_id="broker-filled-1",
                client_order_id="paper-order-filled-1",
                symbol="SPY",
                side="buy",
                status="filled",
                qty=Decimal("1"),
                asset_class="equity",
                order_type="market",
                time_in_force="day",
                submitted_at=ORDER_TIME,
                filled_at=ORDER_TIME,
                filled_qty=Decimal("1"),
                filled_avg_price=Decimal("500.00"),
            )
        ]


def _config(
    source_review_packet: Path,
    run_log: Path,
) -> ReadOnlyPaperBrokerSnapshotReconciliationConfig:
    return ReadOnlyPaperBrokerSnapshotReconciliationConfig(
        run_id=READ_ONLY_PAPER_BROKER_SNAPSHOT_RECONCILIATION_RUN_ID,
        source_review_packet_path=source_review_packet,
        run_log=run_log,
        generated_at=GENERATED_AT,
    )


def _observation(
    *,
    account: dict[str, object] | None = None,
    positions: tuple[dict[str, object], ...] = (),
    open_orders: tuple[dict[str, object], ...] = (),
    recent_orders: tuple[dict[str, object], ...] = (),
) -> ReadOnlyPaperBrokerSnapshotObservation:
    checked_account = account or {
        "account_id": EXPECTED_ACCOUNT_ID,
        "cash": "100000",
        "currency": "USD",
        "status": "ACTIVE",
    }
    return ReadOnlyPaperBrokerSnapshotObservation(
        paper_profile_gate_passed=True,
        account_read_attempted=True,
        positions_read_attempted=True,
        open_orders_read_attempted=True,
        broker_access_performed=True,
        account_observed=True,
        positions_observed=True,
        orders_observed=True,
        account=checked_account,
        expected_account_check={
            "observed_account_id_present": True,
            "observed_account_number_present": False,
            "expected_account_configured": True,
            "expected_account_id_matched": True,
            "expected_account_number_matched": None,
            "expected_account_matched": True,
            "expected_account_match_mode": "account_id",
        },
        positions=positions,
        open_orders=open_orders,
        recent_orders=recent_orders,
        network_access_attempted=True,
        credential_access_attempted=True,
    )


def _write_source_review_packet(tmp_path) -> Path:  # noqa: ANN001
    path = tmp_path / "m402_review_packet.jsonl"
    _write_jsonl(
        path,
        {
            "milestone": "M402 - Offline ETF/SMA paper-lab operator review packet",
            "record_type": "etf_sma_paper_lab_review_packet",
            "command": "etf-sma-paper-lab-review-packet",
            "run_id": "m402_etf_sma_paper_lab_review_packet_200",
            "symbol": "SPY",
            "review_state": "ready_for_operator_review",
            "cycle_decision": "buy_preview",
            "paper_execution_authorized": False,
            "submit_authorized": False,
            "broker_mutation_authorized": False,
            "submitted": False,
            "mutated": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "live_authorized": False,
            "profit_claim": "none",
        },
    )
    return path


def _write_jsonl(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _read_jsonl(path) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _set_env(
    monkeypatch,
    *,
    profile: str = "paper",
    base_url: str = "https://paper.example.test",
    expected_account_id: str | None = EXPECTED_ACCOUNT_ID,
) -> None:
    monkeypatch.setenv("APP_PROFILE", profile)
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", base_url)
    if expected_account_id is None:
        monkeypatch.delenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", raising=False)
    else:
        monkeypatch.setenv("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", expected_account_id)
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)


def _install_fake_broker(
    monkeypatch,
    fake_client: FakeM403AlpacaClient,
) -> FakeM403AlpacaClient:
    def build_broker_and_client(paper_config):  # noqa: ANN001
        broker = AlpacaPaperBroker(
            adapter=AlpacaClientAdapter(fake_client),
            config=paper_config,
        )
        return broker, fake_client

    monkeypatch.setattr(
        cli_module,
        "_build_paper_broker_and_client",
        build_broker_and_client,
    )
    return fake_client


def _forbid_broker_build(monkeypatch) -> None:
    def forbidden_build(paper_config):  # noqa: ANN001
        raise AssertionError("M403 profile gate failure must not build a broker")

    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_build)
    monkeypatch.setattr(cli_module, "_build_paper_broker_and_client", forbidden_build)


def _run_json(argv: tuple[str, ...], capsys) -> tuple[int, dict[str, object]]:
    exit_code = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ""
    return exit_code, json.loads(captured.out.strip())


def _assert_no_broker_authority(payload: dict[str, object]) -> None:
    for field_name in (
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_mutation_performed",
        "paper_execution_authorized",
        "paper_submit_authorized",
        "submit_authorized",
        "broker_mutation_authorized",
        "broker_mutation_allowed",
        "submitted",
        "mutated",
        "broker_action_performed",
        "broker_actions_performed",
        "live_authorized",
        "live_endpoint_support",
    ):
        assert payload[field_name] is False
    for action in ("submit", "cancel", "replace", "close", "liquidate", "mutation"):
        assert payload["broker_action_flags"][action] is False
    assert payload["profit_claim"] == "none"


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
