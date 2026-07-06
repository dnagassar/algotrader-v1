from __future__ import annotations

import ast
from datetime import UTC, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.execution.crypto_paper_fill_exit_certification import (
    OUTCOME_BLOCKED_BEFORE_ENTRY,
    OUTCOME_ENTRY_AMBIGUOUS,
    OUTCOME_ENTRY_NO_FILL_NO_EXIT,
    OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION,
    OUTCOME_FILLED_EXIT_CONFIRMED,
    V510_APPROVED_MAX_NOTIONAL,
    V510_AUTHORIZATION_TEXT,
    V510_PRIOR_CERTIFICATION_ID,
    V510_PRIOR_CLIENT_ORDER_ID,
    deterministic_v510_client_order_ids,
    run_crypto_paper_fill_exit_certification,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "execution"
    / "crypto_paper_fill_exit_certification.py"
)
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_paper_fill_exit_certification.ps1"
GENERATED_AT = datetime(2026, 7, 5, 21, 30, tzinfo=UTC)
EXPECTED_ACCOUNT_ID = "paper-account-expected"
SENSITIVE_KEY = "v510-paper-key-value-not-for-output"
SENSITIVE_SECRET = "v510-paper-secret-value-not-for-output"


class FakeV510PaperClient:
    def __init__(
        self,
        *,
        account: object | None = None,
        asset: object | None = None,
        initial_positions: tuple[dict[str, object], ...] = (),
        position_after_entry: dict[str, object] | None = None,
        final_positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        all_orders: tuple[dict[str, object], ...] = (),
        entry_status: str = "filled",
        entry_filled_qty: str = "0.000250000",
        entry_filled_avg_price: str = "100000",
        exit_status: str = "filled",
        exit_filled_qty: str = "0.000250000",
        exit_filled_avg_price: str = "100000",
        entry_raises: bool = False,
        exit_raises: bool = False,
    ) -> None:
        self.account = account or {
            "id": EXPECTED_ACCOUNT_ID,
            "account_id": EXPECTED_ACCOUNT_ID,
            "account_number": EXPECTED_ACCOUNT_ID,
            "status": "ACTIVE",
            "currency": "USD",
        }
        self.asset = asset or _btc_asset()
        self.initial_positions = [dict(position) for position in initial_positions]
        self.position_after_entry = (
            dict(position_after_entry)
            if position_after_entry is not None
            else _position(qty=entry_filled_qty, average_entry_price=entry_filled_avg_price)
            if Decimal(entry_filled_qty) > Decimal("0")
            else {}
        )
        self.final_positions = [dict(position) for position in final_positions]
        self.open_orders = [dict(order) for order in open_orders]
        self.all_orders = [dict(order) for order in all_orders]
        self.entry_status = entry_status
        self.entry_filled_qty = entry_filled_qty
        self.entry_filled_avg_price = entry_filled_avg_price
        self.exit_status = exit_status
        self.exit_filled_qty = exit_filled_qty
        self.exit_filled_avg_price = exit_filled_avg_price
        self.entry_raises = entry_raises
        self.exit_raises = exit_raises
        self.calls: list[str] = []
        self.submitted_requests: list[object] = []
        self.orders_by_client_id: dict[str, dict[str, object]] = {}

    def get_account(self) -> object:
        self.calls.append("get_account")
        return _copy_model(self.account)

    def get_asset(self, symbol: str) -> object:
        self.calls.append(f"get_asset:{symbol}")
        return _copy_model(self.asset)

    def list_assets(self) -> list[object]:
        self.calls.append("list_assets")
        return [_copy_model(self.asset)]

    def get_latest_quote(self, symbol: str) -> dict[str, object]:
        self.calls.append(f"get_latest_quote:{symbol}")
        return {"symbol": symbol, "bid_price": "99999", "ask_price": "100001"}

    def get_positions(self) -> list[dict[str, object]]:
        self.calls.append("get_positions")
        exit_submitted = any(_request_role(request) == "exit" for request in self.submitted_requests)
        entry_submitted = any(
            _request_role(request) == "entry" for request in self.submitted_requests
        )
        if exit_submitted:
            return [dict(position) for position in self.final_positions]
        if entry_submitted and self.position_after_entry:
            return [dict(self.position_after_entry)]
        return [dict(position) for position in self.initial_positions]

    def get_orders(self, query) -> list[dict[str, object]]:  # noqa: ANN001
        self.calls.append(f"get_orders:{query.status_filter}:{query.symbol_filter}")
        orders = [*self.all_orders, *self.open_orders, *self.orders_by_client_id.values()]
        if query.symbol_filter:
            wanted = query.symbol_filter.upper()
            orders = [
                order
                for order in orders
                if str(order.get("symbol", "")).replace("/", "").upper() == wanted
            ]
        if query.status_filter == "open":
            orders = [
                order
                for order in orders
                if str(order.get("status", "")).lower()
                not in {"canceled", "cancelled", "filled", "rejected", "expired"}
            ]
        return [dict(order) for order in orders]

    def get_order_by_client_id(self, client_order_id: str) -> dict[str, object] | None:
        self.calls.append(f"get_order_by_client_id:{client_order_id}")
        for order in [*self.all_orders, *self.open_orders]:
            if order.get("client_order_id") == client_order_id:
                return dict(order)
        order = self.orders_by_client_id.get(client_order_id)
        return dict(order) if order is not None else None

    def submit_order(self, request) -> dict[str, object]:  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        role = _request_role(request)
        if role == "entry" and self.entry_raises:
            raise RuntimeError(
                f"entry failed token={SENSITIVE_SECRET} at https://paper.example.test"
            )
        if role == "exit" and self.exit_raises:
            raise RuntimeError(
                f"exit failed api_key={SENSITIVE_KEY} at https://paper.example.test"
            )
        if role == "entry":
            order = {
                "id": "v510-entry-order",
                "client_order_id": request.client_order_id,
                "symbol": request.symbol,
                "asset_class": "crypto",
                "side": request.side,
                "type": request.order_type,
                "time_in_force": request.time_in_force,
                "notional": str(request.notional),
                "qty": "",
                "filled_qty": self.entry_filled_qty,
                "filled_avg_price": self.entry_filled_avg_price,
                "status": self.entry_status,
                "submitted_at": GENERATED_AT.isoformat(),
            }
        else:
            order = {
                "id": "v510-exit-order",
                "client_order_id": request.client_order_id,
                "symbol": request.symbol,
                "asset_class": "crypto",
                "side": request.side,
                "type": request.order_type,
                "time_in_force": request.time_in_force,
                "qty": str(request.qty),
                "filled_qty": self.exit_filled_qty,
                "filled_avg_price": self.exit_filled_avg_price,
                "status": self.exit_status,
                "submitted_at": GENERATED_AT.isoformat(),
            }
        self.orders_by_client_id[request.client_order_id] = order
        return dict(order)


def test_exact_authorization_and_fill_exit_certification(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient()

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_FILLED_EXIT_CONFIRMED
    assert result["approved_authorization_text"] == V510_AUTHORIZATION_TEXT
    assert result["prior_certification_id"] == V510_PRIOR_CERTIFICATION_ID
    assert result["prior_client_order_id"] == V510_PRIOR_CLIENT_ORDER_ID
    assert result["symbol"] == "BTCUSD"
    assert result["approved_max_notional"] == "25"
    assert result["entry_attempt_count"] == 1
    assert result["exit_attempt_count"] == 1
    assert result["broker_read_observed"] is True
    assert result["broker_mutation_performed"] is True
    assert result["paper_submit_performed"] is True
    assert result["live_mutation_performed"] is False
    assert result["live_endpoint_touched"] is False
    assert result["credential_values_exposed"] is False
    assert result["entry_order_type"] == "market"
    assert result["entry_side"] == "buy"
    assert result["entry_notional"] == "25"
    assert Decimal(result["estimated_entry_notional"]) <= V510_APPROVED_MAX_NOTIONAL
    assert result["exit_side"] == "sell"
    assert result["exit_qty"] == "0.00025"
    assert result["residual_position_status"] == "flat_or_no_BTCUSD_position_observed"
    assert len(fake_client.submitted_requests) == 2
    entry_request, exit_request = fake_client.submitted_requests
    assert entry_request.symbol == "BTCUSD"
    assert entry_request.order_type == "market"
    assert entry_request.time_in_force == "ioc"
    assert entry_request.notional == Decimal("25")
    assert exit_request.symbol == "BTCUSD"
    assert exit_request.side == "sell"
    assert exit_request.order_type == "market"
    assert exit_request.time_in_force == "ioc"
    assert exit_request.qty == Decimal("0.00025")


def test_mismatch_prior_certification_id_blocks_before_entry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        approval_updates={"prior_certification_id": "wrong-prior-id"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "approval_packet_prior_certification_id_mismatch" in result["blockers"]
    assert fake_client.calls == []


def test_mismatch_prior_client_order_id_blocks_before_entry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        approval_updates={"prior_client_order_id": "wrong-client-order-id"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "approval_packet_prior_client_order_id_mismatch" in result["blockers"]
    assert fake_client.calls == []


def test_non_btcusd_symbol_blocks_before_entry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        approval_updates={"proposed_symbol": "ETHUSD"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "approval_packet_symbol_not_BTCUSD" in result["blockers"]
    assert fake_client.calls == []


def test_notional_above_cap_blocks_before_entry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        approval_updates={
            "proposed_max_notional": "25.01",
            "proposed_max_notional_cap": "25.01",
        },
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "approval_packet_max_notional_mismatch" in result["blockers"]
    assert "approval_packet_max_notional_exceeds_approved_max" in result["blockers"]
    assert fake_client.submitted_requests == []


def test_existing_btcusd_open_order_blocks_before_entry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient(
        open_orders=(
            _order(
                client_order_id="other-btcusd-open-order",
                symbol="BTCUSD",
                status="accepted",
            ),
        )
    )

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "existing_conflicting_BTCUSD_open_order_exists" in result["blockers"]
    assert fake_client.submitted_requests == []


def test_pre_existing_btcusd_position_blocks_before_entry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient(
        initial_positions=(_position(qty="0.000100000"),)
    )

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "existing_BTCUSD_position_ambiguous" in result["blockers"]
    assert fake_client.submitted_requests == []


def test_live_endpoint_blocks_before_entry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient()
    env = _paper_env()
    env["ALPACA_PAPER_BASE_URL"] = "https://api.alpaca.markets"

    result = _run_certification(tmp_path, fake_client, env=env)

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "live_endpoint_indicator" in result["blockers"]
    assert result["live_endpoint_touched"] is False
    assert fake_client.calls == []


def test_second_entry_attempt_is_impossible_with_existing_client_order_id(
    tmp_path: Path,
) -> None:
    entry_client_order_id, _ = deterministic_v510_client_order_ids(
        prior_certification_id=V510_PRIOR_CERTIFICATION_ID,
        prior_client_order_id=V510_PRIOR_CLIENT_ORDER_ID,
    )
    fake_client = FakeV510PaperClient(
        open_orders=(
            _order(
                client_order_id=entry_client_order_id,
                symbol="BTCUSD",
                status="accepted",
            ),
        )
    )

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_ENTRY
    assert "existing_v5_10_entry_client_order_id_order_exists" in result["blockers"]
    assert result["entry_attempt_count"] == 0
    assert fake_client.submitted_requests == []


def test_exit_is_not_attempted_when_entry_has_no_fill(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient(
        entry_status="canceled",
        entry_filled_qty="0",
        entry_filled_avg_price="",
    )

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_ENTRY_NO_FILL_NO_EXIT
    assert result["entry_attempt_count"] == 1
    assert result["exit_attempt_count"] == 0
    assert [request.side for request in fake_client.submitted_requests] == ["buy"]


def test_exit_qty_cannot_exceed_entry_fill_or_resulting_position(
    tmp_path: Path,
) -> None:
    fake_client = FakeV510PaperClient(
        entry_filled_qty="0.000300000",
        position_after_entry=_position(qty="0.000200000"),
        exit_filled_qty="0.000200000",
    )

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_FILLED_EXIT_CONFIRMED
    assert result["entry_filled_qty"] == "0.0003"
    assert result["exit_qty"] == "0.0002"
    assert fake_client.submitted_requests[1].qty == Decimal("0.0002")


def test_entry_ambiguity_does_not_retry_or_exit(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient(entry_raises=True)

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_ENTRY_AMBIGUOUS
    assert result["entry_attempt_count"] == 1
    assert result["exit_attempt_count"] == 0
    assert fake_client.calls.count("submit_order") == 1


def test_exit_ambiguity_does_not_retry(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient(exit_raises=True)

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_EXIT_AMBIGUOUS_RESIDUAL_POSITION
    assert result["entry_attempt_count"] == 1
    assert result["exit_attempt_count"] == 1
    assert fake_client.calls.count("submit_order") == 2


def test_filled_before_exit_does_not_use_close_all_or_liquidation(
    tmp_path: Path,
) -> None:
    fake_client = FakeV510PaperClient()

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_FILLED_EXIT_CONFIRMED
    joined_calls = " ".join(fake_client.calls)
    assert "close_all" not in joined_calls
    assert "close_position" not in joined_calls
    assert "liquidate" not in joined_calls


def test_credential_values_are_not_serialized(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient(entry_raises=True)
    output_root = tmp_path / "runs" / "crypto_paper_fill_exit_certification" / "latest"

    result = _run_certification(tmp_path, fake_client, output_root=output_root)

    serialized_result = json.dumps(result, sort_keys=True)
    assert SENSITIVE_KEY not in serialized_result
    assert SENSITIVE_SECRET not in serialized_result
    assert "https://paper.example.test" not in serialized_result
    for artifact in result["artifact_paths"].values():
        text = Path(artifact).read_text(encoding="utf-8")
        assert SENSITIVE_KEY not in text
        assert SENSITIVE_SECRET not in text
        assert "https://paper.example.test" not in text


def test_generated_artifacts_include_required_flags(tmp_path: Path) -> None:
    fake_client = FakeV510PaperClient()
    output_root = tmp_path / "runs" / "crypto_paper_fill_exit_certification" / "latest"

    result = _run_certification(tmp_path, fake_client, output_root=output_root)
    artifact_paths = result["artifact_paths"]
    payload = json.loads(
        Path(artifact_paths["fill_exit_certification_result_json"]).read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads(Path(artifact_paths["manifest"]).read_text(encoding="utf-8"))
    operating_record = json.loads(
        Path(artifact_paths["operating_record"]).read_text(encoding="utf-8")
    )

    assert payload["paper_submit_performed"] is True
    assert payload["broker_mutation_performed"] is True
    assert payload["live_mutation_performed"] is False
    assert payload["live_endpoint_touched"] is False
    assert payload["credential_values_exposed"] is False
    assert payload["outcome_classification"] == OUTCOME_FILLED_EXIT_CONFIRMED
    assert manifest["generated_under_runs"] is True
    assert set(manifest["required_artifacts"]) == {
        "fill_exit_certification_result_json",
        "fill_exit_certification_result_md",
        "operating_record",
        "manifest",
    }
    assert operating_record["entry_client_order_id"] == result["entry_client_order_id"]


def test_generated_runs_artifacts_remain_untracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")


def test_normal_pytest_path_has_no_direct_network_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden_prefixes = (
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported_modules
        for prefix in forbidden_prefixes
    )


def test_run_script_requires_authorization_switch(tmp_path: Path) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "crypto_paper_fill_exit_certification_authorized=false" in result.stdout
    assert (
        "crypto_paper_fill_exit_certification_stop_reason="
        "v5_10_paper_fill_exit_authorization_switch_required"
    ) in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_run_script_invokes_authorized_module(tmp_path: Path) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    output_root = tmp_path / "cert latest"
    approval_path = tmp_path / "approval packet.json"
    prior_path = tmp_path / "prior result.json"

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-PaperFillExitAuthorized",
            "-OutputRoot",
            str(output_root),
            "-ApprovalPacketPath",
            str(approval_path),
            "-PriorCertificationPath",
            str(prior_path),
            "-ExpectedPaperAccountId",
            EXPECTED_ACCOUNT_ID,
            "-AsOfTimestamp",
            "2026-07-05T21:30:00+00:00",
            "-Format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "crypto_paper_fill_exit_certification_authorized=true" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.execution.crypto_paper_fill_exit_certification" in args
    assert "--paper-fill-exit-authorized" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--approval-packet-path" in args
    assert str(approval_path) in args
    assert "--prior-certification-path" in args
    assert str(prior_path) in args
    assert "--expected-paper-account-id" in args
    assert EXPECTED_ACCOUNT_ID in args
    assert "--submit" not in args
    assert "--cancel" not in args
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def _run_certification(
    tmp_path: Path,
    fake_client: FakeV510PaperClient,
    *,
    approval_updates: dict[str, object] | None = None,
    prior_updates: dict[str, object] | None = None,
    env: dict[str, str] | None = None,
    authorized: bool = True,
    output_root: Path | None = None,
) -> dict[str, object]:
    paths = _write_sources(
        tmp_path,
        approval_updates=approval_updates,
        prior_updates=prior_updates,
    )
    return run_crypto_paper_fill_exit_certification(
        output_root=output_root
        or tmp_path / "runs" / "crypto_paper_fill_exit_certification" / "latest",
        approval_packet_path=paths["approval"],
        prior_certification_path=paths["prior"],
        timestamp=GENERATED_AT,
        env=env or _paper_env(),
        broker_client_factory=lambda _config: fake_client,
        paper_fill_exit_authorized=authorized,
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
    )


def _write_sources(
    tmp_path: Path,
    *,
    approval_updates: dict[str, object] | None = None,
    prior_updates: dict[str, object] | None = None,
) -> dict[str, Path]:
    root = tmp_path / "runs" / "sources"
    root.mkdir(parents=True)
    approval_path = root / "paper_fill_experiment_approval_packet.json"
    prior_path = root / "certification_result.json"
    prior = _prior_certification()
    if prior_updates:
        prior.update(prior_updates)
    approval = _approval_packet(prior_source=prior_path)
    if approval_updates:
        approval.update(approval_updates)
    _write_json(prior_path, prior)
    _write_json(approval_path, approval)
    return {"approval": approval_path, "prior": prior_path}


def _approval_packet(*, prior_source: Path) -> dict[str, object]:
    return {
        "schema_version": "v5_9_crypto_paper_certification_ingestion_v1",
        "as_of": GENERATED_AT.isoformat(),
        "record_type": "paper_fill_experiment_approval_packet",
        "approval_packet_status": "ready_for_operator_review",
        "approval_state": "not_authorized",
        "requested_future_authorization_scope": (
            "bounded_btcusd_paper_fill_and_exit_certification"
        ),
        "required_operator_phrase": V510_AUTHORIZATION_TEXT,
        "prior_certification_id": V510_PRIOR_CERTIFICATION_ID,
        "prior_client_order_id": V510_PRIOR_CLIENT_ORDER_ID,
        "prior_certification_result_source": str(prior_source),
        "prior_certification_result_sha256": "unit-test-sha",
        "prior_certification_result_referenced": {
            "schema_version": "v5_8_crypto_paper_submit_cancel_certification_v1",
            "path": str(prior_source),
            "client_order_id": V510_PRIOR_CLIENT_ORDER_ID,
            "filled_qty": "0",
            "final_order_status": "canceled",
            "outcome_classification": "submitted_cancel_confirmed",
        },
        "proposed_symbol": "BTCUSD",
        "proposed_symbol_scope": "BTCUSD only",
        "proposed_max_notional": "25",
        "proposed_max_notional_cap": "25",
        "proposed_notional_no_greater_than_25": True,
        "paper_fill_authorized": False,
        "paper_entry_authorized": False,
        "paper_exit_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "live_endpoint_touched_current_run": False,
        "credential_values_exposed": False,
        "blockers": [],
        "labels": [
            "paper_lab_only",
            "signal_evaluation_only",
            "not_live_authorized",
            "profit_claim=none",
            "paper_fill_approval_packet_only",
            "btcusd_only",
        ],
    }


def _prior_certification() -> dict[str, object]:
    return {
        "schema_version": "v5_8_crypto_paper_submit_cancel_certification_v1",
        "as_of": GENERATED_AT.isoformat(),
        "approved_authorization_text": "v5.8 authorization",
        "client_order_id": V510_PRIOR_CLIENT_ORDER_ID,
        "symbol": "BTCUSD",
        "approved_max_notional": "25",
        "final_order_status": "canceled",
        "outcome_classification": "submitted_cancel_confirmed",
        "final_order": {
            "client_order_id": V510_PRIOR_CLIENT_ORDER_ID,
            "symbol": "BTCUSD",
            "status": "canceled",
            "filled_qty": "0",
        },
        "broker_mutation_performed": True,
        "paper_submit_performed": True,
        "paper_cancel_performed": True,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "residual_open_order": False,
        "reconciliation": {"filled_qty": "0", "residual_position": {}},
    }


def _btc_asset() -> dict[str, object]:
    return {
        "symbol": "BTC/USD",
        "asset_class": "crypto",
        "tradable": True,
        "fractionable": True,
        "status": "active",
        "min_order_size": "0.000016268",
        "min_trade_increment": "0.000000001",
        "min_notional": "10.00",
    }


def _position(
    *,
    qty: str,
    average_entry_price: str = "100000",
) -> dict[str, object]:
    return {
        "symbol": "BTCUSD",
        "qty": qty,
        "side": "long",
        "average_entry_price": average_entry_price,
        "market_value": str(Decimal(qty) * Decimal(average_entry_price)),
    }


def _order(
    *,
    client_order_id: str,
    symbol: str,
    status: str,
) -> dict[str, object]:
    return {
        "id": "prior-v510-order-id",
        "client_order_id": client_order_id,
        "symbol": symbol,
        "asset_class": "crypto",
        "side": "buy",
        "type": "market",
        "time_in_force": "ioc",
        "notional": "25",
        "filled_qty": "0",
        "status": status,
    }


def _request_role(request: object) -> str:
    client_order_id = str(getattr(request, "client_order_id"))
    if "entry" in client_order_id:
        return "entry"
    if "exit" in client_order_id:
        return "exit"
    return ""


def _copy_model(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    return value


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": SENSITIVE_KEY,
        "APCA_API_SECRET_KEY": SENSITIVE_SECRET,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": EXPECTED_ACCOUNT_ID,
    }


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_bin = tmp_path / "fake_bin"
    fake_bin.mkdir()
    python_cmd = fake_bin / ("python.bat" if os.name == "nt" else "python")
    if os.name == "nt":
        python_cmd.write_text(
            "@echo off\r\n"
            f"echo %* > \"{capture_path}\"\r\n"
            "echo {\"outcome_classification\":\"filled_exit_confirmed\"}\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        python_cmd.write_text(
            "#!/usr/bin/env sh\n"
            f"printf '%s\\n' \"$*\" > '{capture_path}'\n"
            "printf '%s\\n' '{\"outcome_classification\":\"filled_exit_confirmed\"}'\n",
            encoding="utf-8",
        )
        python_cmd.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    env.update(_paper_env())
    return env


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _powershell() -> str:
    return shutil.which("pwsh") or shutil.which("powershell") or "powershell"
