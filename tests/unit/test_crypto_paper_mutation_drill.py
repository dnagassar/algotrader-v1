from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.execution.alpaca_client import (
    V412C_CRYPTO_PAPER_MUTATION_DRILL_CLIENT_ORDER_ID_PREFIX,
)
from algotrader.execution.crypto_paper_mutation_drill import (
    CRYPTO_PAPER_MUTATION_DRILL_DEFAULT_SYMBOL,
    OUTCOME_BLOCKED_PRE_SUBMIT,
    OUTCOME_IDEMPOTENT_EXISTING_ORDER,
    OUTCOME_SUBMITTED_CANCELLED,
    OUTCOME_SUBMITTED_PARTIAL_CANCELLED,
    OUTCOME_SUBMITTED_REJECTED,
    deterministic_crypto_paper_drill_client_order_id,
    run_crypto_paper_mutation_drill,
)
from algotrader.execution.crypto_paper_visibility_operator import (
    run_crypto_paper_visibility_cycle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_paper_mutation_drill.ps1"
GENERATED_AT = datetime(2026, 7, 3, 14, 0, tzinfo=UTC)
EXPECTED_ACCOUNT_ID = "paper-account-expected"
SENSITIVE_KEY = "script-paper-key-value-not-for-output"
SENSITIVE_SECRET = "script-paper-secret-value-not-for-output"


class FakeCryptoPaperClient:
    def __init__(
        self,
        *,
        assets: tuple[dict[str, object], ...] | None = None,
        account: dict[str, object] | None = None,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        all_orders: tuple[dict[str, object], ...] = (),
        submit_status: str = "accepted",
        filled_qty: str = "0",
        cancel_status: str = "canceled",
        submit_raises: bool = False,
    ) -> None:
        self.assets = list(assets if assets is not None else (_btc_asset(),))
        self.account = account or {
            "id": EXPECTED_ACCOUNT_ID,
            "account_id": EXPECTED_ACCOUNT_ID,
            "account_number": EXPECTED_ACCOUNT_ID,
            "status": "ACTIVE",
            "currency": "USD",
        }
        self.positions = list(positions)
        self.open_orders = list(open_orders)
        self.all_orders = list(all_orders)
        self.submit_status = submit_status
        self.filled_qty = filled_qty
        self.cancel_status = cancel_status
        self.submit_raises = submit_raises
        self.calls: list[str] = []
        self.submitted_requests: list[object] = []
        self.cancelled_order_ids: list[str] = []
        self.current_order: dict[str, object] | None = None

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return dict(self.account)

    def list_assets(self) -> list[dict[str, object]]:
        self.calls.append("list_assets")
        return [dict(asset) for asset in self.assets]

    def get_all_assets(self) -> list[dict[str, object]]:
        self.calls.append("get_all_assets")
        return [dict(asset) for asset in self.assets]

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
        status = self.submit_status
        self.current_order = {
            "id": "crypto-paper-order-1",
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
            "status": status,
            "submitted_at": GENERATED_AT.isoformat(),
        }
        if status == "rejected":
            self.current_order["reject_reason"] = "paper validation rejected"
        return dict(self.current_order)

    def cancel_order_by_id(self, order_id: str) -> dict[str, object]:
        self.calls.append(f"cancel_order_by_id:{order_id}")
        self.cancelled_order_ids.append(order_id)
        if self.current_order is not None:
            self.current_order = {
                **self.current_order,
                "status": self.cancel_status,
                "canceled_at": GENERATED_AT.isoformat(),
            }
        return {"id": order_id, "status": self.cancel_status}


def test_normal_crypto_visibility_remains_no_submit(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path)
    fake_client = FakeCryptoPaperClient()

    record = run_crypto_paper_visibility_cycle(
        output_root=tmp_path / "visibility",
        bars_csv=bars_csv,
        timestamp=GENERATED_AT,
        env=_paper_env(),
        sdk_client_factory=lambda _config: fake_client,
    )

    assert record["no_submit_mode"] is True
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["live_mutation_performed"] is False
    assert fake_client.submitted_requests == []


def test_mutation_drill_requires_explicit_authorization_flag(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient()

    packet = _run_drill(tmp_path, fake_client, authorized=False)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "crypto_paper_mutation_authorization_required" in packet["blocker"]
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_performed"] is False
    assert fake_client.calls == []


def test_stale_crypto_data_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient()
    stale_csv = _write_bars(tmp_path, latest_at=GENERATED_AT - timedelta(days=3))

    packet = _run_drill(tmp_path, fake_client, bars_csv=stale_csv)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "crypto_bars_not_current" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_insufficient_history_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient()
    bars_csv = _write_bars(tmp_path, count=20)

    packet = _run_drill(tmp_path, fake_client, bars_csv=bars_csv)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "insufficient_crypto_strategy_history" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_missing_symbol_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(assets=())

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "selected_crypto_asset_not_observed" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_non_tradable_symbol_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(assets=(_btc_asset(tradable=False),))

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "selected_symbol_not_tradable" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_missing_min_notional_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(assets=(_btc_asset(min_notional=""),))

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "min_notional_missing" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_min_notional_above_cap_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(assets=(_btc_asset(min_notional="12.00"),))

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "min_notional_exceeds_drill_cap" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_live_endpoint_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient()
    env = {**_paper_env(), "APCA_API_BASE_URL": "https://api.alpaca.markets"}

    packet = _run_drill(tmp_path, fake_client, env=env)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "live_endpoint_indicator" in packet["blocker"]
    assert fake_client.calls == []


def test_expected_paper_account_mismatch_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(
        account={
            "id": "different-paper-account",
            "account_id": "different-paper-account",
            "status": "ACTIVE",
        }
    )

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "paper_account_expected_id_mismatch" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_open_selected_symbol_order_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(
        open_orders=(
            _order(
                client_order_id="other-btcusd-open-order",
                symbol="BTCUSD",
                status="accepted",
            ),
        )
    )

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "open_selected_symbol_order_exists" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_conflicting_crypto_order_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(
        assets=(_btc_asset(), _eth_asset()),
        open_orders=(
            _order(
                client_order_id="other-ethusd-open-order",
                symbol="ETHUSD",
                status="accepted",
            ),
        ),
    )

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "open_conflicting_crypto_order_exists" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_existing_position_ambiguity_blocks_before_submit(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(
        positions=({"symbol": "BTCUSD", "qty": "0.0001", "market_value": "10"},)
    )

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "existing_selected_symbol_position_ambiguous" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_deterministic_client_order_id_behavior() -> None:
    assert deterministic_crypto_paper_drill_client_order_id("BTC/USD") == (
        f"{V412C_CRYPTO_PAPER_MUTATION_DRILL_CLIENT_ORDER_ID_PREFIX}btcusd"
    )


def test_existing_same_client_order_id_reconciles_without_duplicate_submit(
    tmp_path: Path,
) -> None:
    client_order_id = deterministic_crypto_paper_drill_client_order_id("BTCUSD")
    fake_client = FakeCryptoPaperClient(
        all_orders=(
            _order(
                client_order_id=client_order_id,
                symbol="BTCUSD",
                status="canceled",
            ),
        )
    )

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_IDEMPOTENT_EXISTING_ORDER
    assert packet["paper_submit_performed"] is False
    assert fake_client.submitted_requests == []


def test_submit_then_cancel_submits_exactly_one_bounded_limit_order(
    tmp_path: Path,
) -> None:
    fake_client = FakeCryptoPaperClient(submit_status="accepted", cancel_status="canceled")

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_SUBMITTED_CANCELLED
    assert packet["paper_submit_authorized"] is True
    assert packet["paper_submit_performed"] is True
    assert packet["broker_mutation_performed"] is True
    assert packet["live_mutation_performed"] is False
    assert len(fake_client.submitted_requests) == 1
    request = fake_client.submitted_requests[0]
    assert request.symbol == "BTCUSD"
    assert request.side == "buy"
    assert request.order_type == "limit"
    assert request.notional is None
    assert Decimal(str(request.limit_price)) < Decimal("100059")
    estimated = Decimal(str(request.limit_price)) * Decimal(str(request.qty))
    assert estimated >= Decimal("10.00")
    assert estimated <= Decimal("11.00")
    assert fake_client.cancelled_order_ids == ["crypto-paper-order-1"]


def test_rejected_submit_does_not_retry_or_cancel(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(submit_status="rejected")

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_SUBMITTED_REJECTED
    assert packet["submit_call_count"] == 1
    assert packet["paper_submit_performed"] is True
    assert packet["cancel_attempted"] is False
    assert fake_client.calls.count("submit_order") == 1
    assert fake_client.cancelled_order_ids == []


def test_partial_fill_cancels_same_order_without_flatten_order(tmp_path: Path) -> None:
    fake_client = FakeCryptoPaperClient(
        submit_status="partially_filled",
        filled_qty="0.00002",
        cancel_status="canceled",
        positions=({"symbol": "BTCUSD", "qty": "0.00002", "market_value": "2"},),
    )

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_BLOCKED_PRE_SUBMIT
    assert "existing_selected_symbol_position_ambiguous" in packet["blocker"]
    assert fake_client.submitted_requests == []


def test_partial_fill_after_submit_records_residual_without_second_submit(
    tmp_path: Path,
) -> None:
    fake_client = FakeCryptoPaperClient(
        submit_status="partially_filled",
        filled_qty="0.00002",
        cancel_status="canceled",
    )
    fake_client.positions = []

    packet = _run_drill(tmp_path, fake_client)

    assert packet["outcome_classification"] == OUTCOME_SUBMITTED_PARTIAL_CANCELLED
    assert packet["submit_call_count"] == 1
    assert fake_client.calls.count("submit_order") == 1
    assert fake_client.cancelled_order_ids == ["crypto-paper-order-1"]
    assert packet["flatten_or_close_order_allowed"] is False


def test_artifacts_are_sanitized_and_written_under_ignored_runs(
    tmp_path: Path,
) -> None:
    fake_client = FakeCryptoPaperClient(submit_raises=True)
    output_root = tmp_path / "runs" / "crypto_paper_mutation_drill" / "latest"

    packet = _run_drill(tmp_path, fake_client, output_root=output_root)

    assert packet["paper_submit_performed"] is True
    artifact_paths = packet["artifact_paths"]
    for key in ("latest_status", "drill_receipt", "operating_brief", "manifest"):
        path = Path(artifact_paths[key])
        assert path.exists(), key
        text = path.read_text(encoding="utf-8")
        assert SENSITIVE_KEY not in text
        assert SENSITIVE_SECRET not in text
        assert "https://paper.example.test" not in text


def test_run_crypto_paper_mutation_drill_script_requires_switch(
    tmp_path: Path,
) -> None:
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
    assert "crypto_paper_mutation_authorized=false" in result.stdout
    assert "crypto_paper_mutation_stop_reason=crypto_paper_mutation_authorization_required" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_run_crypto_paper_mutation_drill_script_invokes_authorized_module(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "crypto drill"
    bars_csv = tmp_path / "crypto bars.csv"
    bars_csv.write_text(
        "timestamp,symbol,open,high,low,close,volume\n"
        "2026-07-03T02:00:00+00:00,BTCUSD,1,1,1,1,1\n",
        encoding="utf-8",
    )
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
            "-CryptoPaperMutationAuthorized",
            "-OutputRoot",
            str(output_root),
            "-BarsCsv",
            str(bars_csv),
            "-ExpectedPaperAccountId",
            EXPECTED_ACCOUNT_ID,
            "-AsOfTimestamp",
            "2026-07-03T02:00:00+00:00",
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
    assert "crypto_paper_mutation_authorized=true" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.execution.crypto_paper_mutation_drill" in args
    assert "--crypto-paper-mutation-authorized" in args
    assert "--output-root" in args
    assert str(output_root) in args
    assert "--bars-csv" in args
    assert str(bars_csv) in args
    assert "--expected-paper-account-id" in args
    assert EXPECTED_ACCOUNT_ID in args
    assert "--submit" not in args
    assert SENSITIVE_KEY not in combined
    assert SENSITIVE_SECRET not in combined


def test_git_ls_files_runs_contract_has_no_tracked_runtime_artifacts() -> None:
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""


def _run_drill(
    tmp_path: Path,
    fake_client: FakeCryptoPaperClient,
    *,
    bars_csv: Path | None = None,
    env: dict[str, str] | None = None,
    authorized: bool = True,
    output_root: Path | None = None,
) -> dict[str, object]:
    return run_crypto_paper_mutation_drill(
        output_root=output_root
        or tmp_path / "runs" / "crypto_paper_mutation_drill" / "latest",
        bars_csv=bars_csv or _write_bars(tmp_path),
        timestamp=GENERATED_AT,
        env=env or _paper_env(),
        broker_client_factory=lambda _config: fake_client,
        crypto_paper_mutation_authorized=authorized,
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
    )


def _write_bars(
    tmp_path: Path,
    *,
    count: int = 60,
    latest_at: datetime = GENERATED_AT,
) -> Path:
    path = tmp_path / f"crypto_bars_{count}_{int(latest_at.timestamp())}.csv"
    start = latest_at - timedelta(hours=count - 1)
    lines = ["timestamp,symbol,open,high,low,close,volume\n"]
    for index in range(count):
        timestamp = start + timedelta(hours=index)
        close = Decimal("100000") + Decimal(index)
        lines.append(
            f"{timestamp.isoformat()},BTCUSD,{close},{close},{close},{close},1\n"
        )
    path.write_text("".join(lines), encoding="utf-8")
    return path


def _btc_asset(
    *,
    tradable: bool = True,
    fractionable: bool = True,
    min_notional: str = "10.00",
) -> dict[str, object]:
    return {
        "symbol": "BTC/USD",
        "asset_class": "crypto",
        "tradable": tradable,
        "fractionable": fractionable,
        "status": "active",
        "min_order_size": "0.000016268",
        "min_trade_increment": "0.000000001",
        "min_notional": min_notional,
    }


def _eth_asset() -> dict[str, object]:
    return {
        "symbol": "ETH/USD",
        "asset_class": "crypto",
        "tradable": True,
        "fractionable": True,
        "status": "active",
        "min_order_size": "0.0001",
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
        "qty": "0.0001",
        "limit_price": "99000",
        "filled_qty": "0",
        "status": status,
    }


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
            "echo {\"outcome_classification\":\"crypto_paper_drill_submitted_cancel_confirmed\"}\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        python_cmd.write_text(
            "#!/usr/bin/env sh\n"
            f"printf '%s\\n' \"$*\" > '{capture_path}'\n"
            "printf '%s\\n' '{\"outcome_classification\":\"crypto_paper_drill_submitted_cancel_confirmed\"}'\n",
            encoding="utf-8",
        )
        python_cmd.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    env.update(_paper_env())
    return env


def _powershell() -> str:
    return shutil.which("pwsh") or shutil.which("powershell") or "powershell"
