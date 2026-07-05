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
from algotrader.execution.alpaca_client import (
    AlpacaOrderRequest,
    V58_CRYPTO_PAPER_CERTIFICATION_CLIENT_ORDER_ID_PREFIX,
)
from algotrader.execution.crypto_paper_submit_cancel_certification import (
    OUTCOME_BLOCKED_BEFORE_SUBMIT,
    OUTCOME_CANCEL_AMBIGUOUS,
    OUTCOME_SUBMIT_AMBIGUOUS,
    OUTCOME_SUBMIT_REJECTED,
    OUTCOME_SUBMITTED_ALREADY_FILLED,
    OUTCOME_SUBMITTED_CANCEL_CONFIRMED,
    V58_APPROVED_MAX_NOTIONAL,
    V58_APPROVED_QTY,
    V58_AUTHORIZATION_TEXT,
    V58_DRY_RUN_ID,
    V58_PRE_BROKER_ORDER_ID,
    deterministic_v58_client_order_id,
    run_crypto_paper_submit_cancel_certification,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "execution"
    / "crypto_paper_submit_cancel_certification.py"
)
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_paper_submit_cancel_certification.ps1"
GENERATED_AT = datetime(2026, 7, 5, 14, 0, tzinfo=UTC)
EXPECTED_ACCOUNT_ID = "paper-account-expected"
SENSITIVE_KEY = "v58-paper-key-value-not-for-output"
SENSITIVE_SECRET = "v58-paper-secret-value-not-for-output"


class FakeV58PaperClient:
    def __init__(
        self,
        *,
        account: object | None = None,
        asset: object | None = None,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        all_orders: tuple[dict[str, object], ...] = (),
        submit_status: str = "accepted",
        filled_qty: str = "0",
        cancel_status: str = "canceled",
        submit_raises: bool = False,
        cancel_raises: bool = False,
    ) -> None:
        self.account = account or {
            "id": EXPECTED_ACCOUNT_ID,
            "account_id": EXPECTED_ACCOUNT_ID,
            "account_number": EXPECTED_ACCOUNT_ID,
            "status": "ACTIVE",
            "currency": "USD",
        }
        self.asset = asset or _btc_asset()
        self.positions = list(positions)
        self.open_orders = list(open_orders)
        self.all_orders = list(all_orders)
        self.submit_status = submit_status
        self.filled_qty = filled_qty
        self.cancel_status = cancel_status
        self.submit_raises = submit_raises
        self.cancel_raises = cancel_raises
        self.calls: list[str] = []
        self.submitted_requests: list[object] = []
        self.cancelled_order_ids: list[str] = []
        self.current_order: dict[str, object] | None = None

    def get_account(self) -> object:
        self.calls.append("get_account")
        return _copy_model(self.account)

    def get_asset(self, symbol: str) -> object:
        self.calls.append(f"get_asset:{symbol}")
        return _copy_model(self.asset)

    def list_assets(self) -> list[object]:
        self.calls.append("list_assets")
        return [_copy_model(self.asset)]

    def get_positions(self) -> list[dict[str, object]]:
        self.calls.append("get_positions")
        return [dict(position) for position in self.positions]

    def get_orders(self, query) -> list[dict[str, object]]:  # noqa: ANN001
        self.calls.append(f"get_orders:{query.status_filter}:{query.symbol_filter}")
        orders = list(self.all_orders)
        if query.status_filter == "open":
            orders.extend(self.open_orders)
        if self.current_order is not None:
            orders.append(dict(self.current_order))
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
        if (
            self.current_order is not None
            and self.current_order.get("client_order_id") == client_order_id
        ):
            return dict(self.current_order)
        return None

    def submit_order(self, request) -> dict[str, object]:  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        if self.submit_raises:
            raise RuntimeError(
                f"submit failed token={SENSITIVE_SECRET} at https://paper.example.test"
            )
        self.current_order = {
            "id": "v58-paper-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "asset_class": "crypto",
            "side": request.side,
            "type": request.order_type,
            "time_in_force": request.time_in_force,
            "qty": str(request.qty),
            "limit_price": str(request.limit_price),
            "filled_qty": self.filled_qty,
            "filled_avg_price": "" if self.filled_qty == "0" else str(request.limit_price),
            "status": self.submit_status,
            "submitted_at": GENERATED_AT.isoformat(),
        }
        if self.submit_status == "rejected":
            self.current_order["reject_reason"] = "paper validation rejected"
        return dict(self.current_order)

    def cancel_order_by_id(self, order_id: str) -> dict[str, object]:
        self.calls.append(f"cancel_order_by_id:{order_id}")
        self.cancelled_order_ids.append(order_id)
        if self.cancel_raises:
            raise RuntimeError(
                f"cancel failed api_key={SENSITIVE_KEY} at https://paper.example.test"
            )
        if self.current_order is not None:
            self.current_order = {
                **self.current_order,
                "status": self.cancel_status,
                "canceled_at": GENERATED_AT.isoformat(),
            }
        return {"id": order_id, "status": self.cancel_status}


def test_exact_authorization_and_submit_cancel_certification(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient()

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_SUBMITTED_CANCEL_CONFIRMED
    assert result["approved_authorization_text"] == V58_AUTHORIZATION_TEXT
    assert result["dry_run_id"] == V58_DRY_RUN_ID
    assert result["pre_broker_order_id"] == V58_PRE_BROKER_ORDER_ID
    assert result["symbol"] == "BTCUSD"
    assert result["approved_qty"] == "0.000396783"
    assert result["submitted_qty"] == "0.000396783"
    assert result["approved_max_notional"] == "25"
    assert result["paper_submit_authorized"] is True
    assert result["paper_submit_performed"] is True
    assert result["broker_mutation_performed"] is True
    assert result["paper_cancel_performed"] is True
    assert result["live_mutation_performed"] is False
    assert result["live_endpoint_touched"] is False
    assert result["credential_values_exposed"] is False
    assert result["broker_read_observed"] is True
    assert result["submit_attempt_count"] == 1
    assert result["cancel_attempt_count"] == 1
    assert len(fake_client.submitted_requests) == 1
    request = fake_client.submitted_requests[0]
    assert request.symbol == "BTCUSD"
    assert request.side == "buy"
    assert request.order_type == "limit"
    assert request.time_in_force == "gtc"
    assert request.notional is None
    assert Decimal(str(request.qty)) == V58_APPROVED_QTY
    estimated = Decimal(str(request.limit_price)) * Decimal(str(request.qty))
    assert estimated <= V58_APPROVED_MAX_NOTIONAL
    assert fake_client.cancelled_order_ids == ["v58-paper-order-1"]


def test_v58_alpaca_order_request_namespace_is_allowlisted() -> None:
    client_order_id = deterministic_v58_client_order_id(
        dry_run_id=V58_DRY_RUN_ID,
        pre_broker_order_id=V58_PRE_BROKER_ORDER_ID,
    )

    request = AlpacaOrderRequest(
        client_order_id=client_order_id,
        symbol="BTCUSD",
        side="buy",
        asset_class="crypto",
        qty=V58_APPROVED_QTY,
        order_type="limit",
        time_in_force="gtc",
        limit_price=Decimal("31503.35"),
    )

    assert request.client_order_id.startswith(
        V58_CRYPTO_PAPER_CERTIFICATION_CLIENT_ORDER_ID_PREFIX
    )
    assert request.symbol == "BTCUSD"


def test_mismatch_dry_run_id_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        approval_updates={"dry_run_id": "dryrun_wrong"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "approval_packet_dry_run_id_mismatch" in result["blockers"]
    assert fake_client.calls == []


def test_mismatch_pre_broker_order_id_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        dry_run_updates={"pre_broker_order_id": "prebroker_wrong"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "dry_run_pre_broker_order_id_mismatch" in result["blockers"]
    assert fake_client.calls == []


def test_qty_above_approved_qty_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        approval_updates={"exact_qty": "0.000396784", "rounded_qty": "0.000396784"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "approval_packet_qty_mismatch" in result["blockers"]
    assert "approval_packet_qty_exceeds_approved_qty" in result["blockers"]
    assert fake_client.calls == []


def test_estimated_notional_above_cap_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        dry_run_updates={"latest_price": "200000"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "estimated_submit_notional_exceeds_approved_max" in result["blockers"]
    assert fake_client.submitted_requests == []


def test_non_btcusd_symbol_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient()

    result = _run_certification(
        tmp_path,
        fake_client,
        approval_updates={"symbol": "ETHUSD", "exact_symbol": "ETHUSD"},
    )

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "approval_packet_symbol_not_BTCUSD" in result["blockers"]
    assert fake_client.calls == []


def test_existing_conflicting_btcusd_open_order_blocks_before_submit(
    tmp_path: Path,
) -> None:
    fake_client = FakeV58PaperClient(
        open_orders=(
            _order(
                client_order_id="other-btcusd-open-order",
                symbol="BTCUSD",
                status="accepted",
            ),
        )
    )

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "existing_conflicting_BTCUSD_open_order_exists" in result["blockers"]
    assert fake_client.submitted_requests == []


def test_live_endpoint_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient()
    env = _paper_env()
    env["ALPACA_PAPER_BASE_URL"] = "https://api.alpaca.markets"

    result = _run_certification(tmp_path, fake_client, env=env)

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "live_endpoint_indicator" in result["blockers"]
    assert result["live_endpoint_touched"] is False
    assert fake_client.calls == []


def test_second_submit_attempt_is_impossible_with_existing_client_order_id(
    tmp_path: Path,
) -> None:
    fake_client = FakeV58PaperClient(
        open_orders=(
            _order(
                client_order_id=deterministic_v58_client_order_id(
                    dry_run_id=V58_DRY_RUN_ID,
                    pre_broker_order_id=V58_PRE_BROKER_ORDER_ID,
                ),
                symbol="BTCUSD",
                status="accepted",
            ),
        )
    )

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_BLOCKED_BEFORE_SUBMIT
    assert "existing_v5_8_client_order_id_order_exists" in result["blockers"]
    assert result["submit_attempt_count"] == 0
    assert fake_client.submitted_requests == []


def test_submit_ambiguity_does_not_retry(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient(submit_raises=True)

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_SUBMIT_AMBIGUOUS
    assert result["submit_attempt_count"] == 1
    assert result["cancel_attempt_count"] == 0
    assert fake_client.calls.count("submit_order") == 1
    assert fake_client.cancelled_order_ids == []


def test_cancel_ambiguity_does_not_resubmit(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient(cancel_raises=True)

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_CANCEL_AMBIGUOUS
    assert result["submit_attempt_count"] == 1
    assert result["cancel_attempt_count"] == 1
    assert fake_client.calls.count("submit_order") == 1
    assert fake_client.cancelled_order_ids == ["v58-paper-order-1"]


def test_filled_before_cancel_does_not_close_or_liquidate(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient(submit_status="filled", filled_qty="0.000396783")

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_SUBMITTED_ALREADY_FILLED
    assert result["submit_attempt_count"] == 1
    assert result["cancel_attempt_count"] == 0
    assert result["close_or_liquidate_allowed"] is False
    assert "close_position" not in fake_client.calls
    assert "liquidate" not in fake_client.calls
    assert fake_client.cancelled_order_ids == []


def test_rejected_submit_does_not_cancel_or_retry(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient(submit_status="rejected")

    result = _run_certification(tmp_path, fake_client)

    assert result["outcome_classification"] == OUTCOME_SUBMIT_REJECTED
    assert result["submit_attempt_count"] == 1
    assert result["cancel_attempt_count"] == 0
    assert fake_client.calls.count("submit_order") == 1
    assert fake_client.cancelled_order_ids == []


def test_credential_values_are_not_serialized(tmp_path: Path) -> None:
    fake_client = FakeV58PaperClient(submit_raises=True)
    output_root = tmp_path / "runs" / "crypto_paper_submit_cancel_certification" / "latest"

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
    fake_client = FakeV58PaperClient()
    output_root = tmp_path / "runs" / "crypto_paper_submit_cancel_certification" / "latest"

    result = _run_certification(tmp_path, fake_client, output_root=output_root)
    artifact_paths = result["artifact_paths"]
    payload = json.loads(
        Path(artifact_paths["certification_result_json"]).read_text(encoding="utf-8")
    )
    manifest = json.loads(Path(artifact_paths["manifest"]).read_text(encoding="utf-8"))
    operating_record = json.loads(
        Path(artifact_paths["operating_record"]).read_text(encoding="utf-8")
    )

    assert payload["paper_submit_authorized"] is True
    assert payload["paper_submit_performed"] is True
    assert payload["broker_mutation_performed"] is True
    assert payload["live_mutation_performed"] is False
    assert payload["credential_values_exposed"] is False
    assert payload["outcome_classification"] == OUTCOME_SUBMITTED_CANCEL_CONFIRMED
    assert manifest["generated_under_runs"] is True
    assert set(manifest["required_artifacts"]) == {
        "certification_result_json",
        "certification_result_md",
        "operating_record",
    }
    assert operating_record["client_order_id"] == result["client_order_id"]


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
    assert "crypto_paper_submit_cancel_certification_authorized=false" in result.stdout
    assert (
        "crypto_paper_submit_cancel_certification_stop_reason="
        "v5_8_paper_submit_authorization_switch_required"
    ) in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_run_script_invokes_authorized_module(tmp_path: Path) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    output_root = tmp_path / "cert latest"
    approval_path = tmp_path / "approval packet.json"
    dry_run_path = tmp_path / "dry run.json"

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-PaperSubmitAuthorized",
            "-OutputRoot",
            str(output_root),
            "-ApprovalPacketPath",
            str(approval_path),
            "-DryRunPath",
            str(dry_run_path),
            "-ExpectedPaperAccountId",
            EXPECTED_ACCOUNT_ID,
            "-AsOfTimestamp",
            "2026-07-05T14:00:00+00:00",
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
    assert "crypto_paper_submit_cancel_certification_authorized=true" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.execution.crypto_paper_submit_cancel_certification" in args
    assert "--paper-submit-authorized" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--approval-packet-path" in args
    assert str(approval_path) in args
    assert "--dry-run-path" in args
    assert str(dry_run_path) in args
    assert "--expected-paper-account-id" in args
    assert EXPECTED_ACCOUNT_ID in args
    assert "--submit" not in args
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def _run_certification(
    tmp_path: Path,
    fake_client: FakeV58PaperClient,
    *,
    approval_updates: dict[str, object] | None = None,
    dry_run_updates: dict[str, object] | None = None,
    env: dict[str, str] | None = None,
    authorized: bool = True,
    output_root: Path | None = None,
) -> dict[str, object]:
    paths = _write_sources(
        tmp_path,
        approval_updates=approval_updates,
        dry_run_updates=dry_run_updates,
    )
    return run_crypto_paper_submit_cancel_certification(
        output_root=output_root
        or tmp_path / "runs" / "crypto_paper_submit_cancel_certification" / "latest",
        approval_packet_path=paths["approval"],
        dry_run_path=paths["dry_run"],
        timestamp=GENERATED_AT,
        env=env or _paper_env(),
        broker_client_factory=lambda _config: fake_client,
        paper_submit_authorized=authorized,
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
    )


def _write_sources(
    tmp_path: Path,
    *,
    approval_updates: dict[str, object] | None = None,
    dry_run_updates: dict[str, object] | None = None,
) -> dict[str, Path]:
    root = tmp_path / "runs" / "sources"
    root.mkdir(parents=True)
    approval_path = root / "paper_submit_approval_packet.json"
    dry_run_path = root / "paper_oms_dry_run.json"
    dry_run = _dry_run()
    if dry_run_updates:
        dry_run.update(dry_run_updates)
    approval = _approval_packet(dry_run_source=dry_run_path)
    if approval_updates:
        approval.update(approval_updates)
    _write_json(dry_run_path, dry_run)
    _write_json(approval_path, approval)
    return {"approval": approval_path, "dry_run": dry_run_path}


def _approval_packet(*, dry_run_source: Path) -> dict[str, object]:
    return {
        "schema_version": "v5_7_crypto_paper_submit_approval_packet_v1",
        "as_of": GENERATED_AT.isoformat(),
        "dry_run_source": str(dry_run_source),
        "approval_packet_status": "ready_for_operator_review",
        "approval_state": "not_authorized",
        "broker_action_permitted": False,
        "requested_future_authorization_scope": (
            "bounded_paper_submit_cancel_certification"
        ),
        "dry_run_id": V58_DRY_RUN_ID,
        "pre_broker_order_id": V58_PRE_BROKER_ORDER_ID,
        "idempotency_key": "crypto_paper_oms_dry_run:test",
        "selected_candidate_id": "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview",
        "selected_backing": "real_local_artifact_backed",
        "symbol": "BTCUSD",
        "asset_class": "crypto",
        "intended_action": "buy_preview",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "preview_cap": "25",
        "exact_candidate_id": "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview",
        "exact_symbol": "BTCUSD",
        "exact_asset_class": "crypto",
        "exact_intended_action": "buy_preview",
        "exact_qty": "0.000396783",
        "exact_preview_value": "24.999991017147",
        "exact_cap": "25",
        "required_operator_phrase": V58_AUTHORIZATION_TEXT,
        "blockers": [],
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "paper_submit_performed": False,
        "paper_cancel_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": _labels()
        + ["paper_submit_approval_packet_only", "operator_review_required"],
    }


def _dry_run() -> dict[str, object]:
    return {
        "schema_version": "v5_6_crypto_paper_oms_dry_run_v1",
        "as_of": GENERATED_AT.isoformat(),
        "dry_run_status": "blocked_not_authorized",
        "approval_state": "not_authorized",
        "broker_action_permitted": False,
        "intended_action": "buy_preview",
        "asset_class": "crypto",
        "symbol": "BTCUSD",
        "selected_candidate_id": "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview",
        "selected_strategy": "crypto_vol_adjusted_momentum_24h_preview",
        "selected_backing": "real_local_artifact_backed",
        "latest_price": "63006.709",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "preview_cap": "25",
        "dry_run_id": V58_DRY_RUN_ID,
        "pre_broker_order_id": V58_PRE_BROKER_ORDER_ID,
        "idempotency_key": "crypto_paper_oms_dry_run:test",
        "blockers": [],
        "source_blockers": [],
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": _labels(),
    }


def _labels() -> list[str]:
    return [
        "paper_lab_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "sizing_preview_only",
        "qty_orderable_notional_unobserved",
        "real_local_artifact_backed",
        "paper_oms_handoff_only",
        "approval_required",
        "paper_oms_dry_run_only",
        "pre_broker_preview_only",
        "not_submittable",
    ]


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


def _order(
    *,
    client_order_id: str,
    symbol: str,
    status: str,
) -> dict[str, object]:
    return {
        "id": "prior-order-id",
        "client_order_id": client_order_id,
        "symbol": symbol,
        "asset_class": "crypto",
        "side": "buy",
        "type": "limit",
        "time_in_force": "gtc",
        "qty": "0.000396783",
        "limit_price": "31503.35",
        "filled_qty": "0",
        "status": status,
    }


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
            "echo {\"outcome_classification\":\"submitted_cancel_confirmed\"}\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        python_cmd.write_text(
            "#!/usr/bin/env sh\n"
            f"printf '%s\\n' \"$*\" > '{capture_path}'\n"
            "printf '%s\\n' '{\"outcome_classification\":\"submitted_cancel_confirmed\"}'\n",
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
