from __future__ import annotations

import ast
from datetime import UTC, datetime
from decimal import Decimal
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.execution.alpaca_adapter import AlpacaClientAdapter
from algotrader.execution.alpaca_broker import AlpacaPaperBroker
from algotrader.execution.alpaca_client import (
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
    assert payload["account_observed"] is True
    assert payload["positions_observed"] is True
    assert payload["orders_observed"] is True
    assert payload["recent_orders_observed"] is True
    assert payload["cash"] == "100000"
    assert payload["buying_power"] == "200000"
    assert payload["currency"] == "USD"
    assert payload["position_count"] == 0
    assert payload["position_symbols"] == []
    assert payload["spy_position_present"] is False
    assert payload["spy_position_qty"] == "0"
    assert payload["unexpected_non_spy_positions"] == []
    assert payload["open_order_count"] == 0
    assert payload["open_spy_order_count"] == 0
    assert payload["recent_order_count"] == 0
    assert payload["recent_spy_order_count"] == 0
    assert payload["broker_observation_state"] == "observed"
    assert payload["reconciliation_state"] == "ready_for_operator_review"
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
            account_observed=True,
            positions_observed=True,
            account={"cash": "100000", "currency": "USD"},
            positions=(),
            unavailable_observations=("open_orders", "recent_orders"),
            network_access_attempted=True,
            credential_access_attempted=True,
        ),
    )

    assert payload["broker_observation_state"] == "observation_incomplete"
    assert payload["reconciliation_state"] == "blocked_observation_incomplete"
    assert "open_orders_observation_unavailable" in payload["blockers"]
    assert "recent_orders_observation_unavailable" in payload["blockers"]
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


def test_cli_dispatch_reads_only_account_positions_open_and_recent_orders(
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
        "get_orders",
    ]
    assert fake_client.submitted_requests == []
    assert [query.status_filter for query in fake_client.recent_order_queries] == [
        "open",
        "all",
    ]
    assert records == [payload]
    assert payload["reconciliation_state"] == "ready_for_operator_review"
    assert payload["network_access_attempted"] is True
    assert payload["credential_access_attempted"] is True
    assert SENSITIVE_API_KEY not in rendered
    assert SENSITIVE_SECRET_KEY not in rendered
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
    ) -> None:
        super().__init__(positions=positions)
        self.recent_order_queries: list[AlpacaRecentOrderQuery] = []

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
    positions: tuple[dict[str, object], ...] = (),
    open_orders: tuple[dict[str, object], ...] = (),
    recent_orders: tuple[dict[str, object], ...] = (),
) -> ReadOnlyPaperBrokerSnapshotObservation:
    return ReadOnlyPaperBrokerSnapshotObservation(
        paper_profile_gate_passed=True,
        account_observed=True,
        positions_observed=True,
        orders_observed=True,
        recent_orders_observed=True,
        account={"cash": "100000", "buying_power": "200000", "currency": "USD"},
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
) -> None:
    monkeypatch.setenv("APP_PROFILE", profile)
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_API_KEY)
    monkeypatch.setenv("ALPACA_SECRET_KEY", SENSITIVE_SECRET_KEY)
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", base_url)
    monkeypatch.delenv("ALGOTRADER_PAPER_HALT", raising=False)


def _install_fake_broker(
    monkeypatch,
    fake_client: FakeM403AlpacaClient,
) -> FakeM403AlpacaClient:
    def build_broker(paper_config):  # noqa: ANN001
        return AlpacaPaperBroker(
            adapter=AlpacaClientAdapter(fake_client),
            config=paper_config,
        )

    monkeypatch.setattr(cli_module, "_build_paper_broker", build_broker)
    return fake_client


def _forbid_broker_build(monkeypatch) -> None:
    def forbidden_build(paper_config):  # noqa: ANN001
        raise AssertionError("M403 profile gate failure must not build a broker")

    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_build)


def _run_json(argv: tuple[str, ...], capsys) -> tuple[int, dict[str, object]]:
    exit_code = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ""
    return exit_code, json.loads(captured.out.strip())


def _assert_no_broker_authority(payload: dict[str, object]) -> None:
    for field_name in (
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
