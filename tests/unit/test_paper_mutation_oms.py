from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from algotrader.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    AlpacaPaperConfig,
)
from algotrader.execution.alpaca_client import (
    AlpacaRecentOrderQuery,
    V189_SPY_CERTIFICATION_CLIENT_ORDER_ID,
)
from algotrader.execution.paper_mutation_oms import (
    PaperCertificationRuntime,
    PaperMutationGateway,
    certification_client_order_id,
    evaluate_strategy_plan_mutation_lane,
    paper_config_from_env_aliases,
    run_paper_certification_drill,
)


NOW = datetime(2026, 6, 24, 15, 30, tzinfo=UTC)
SENSITIVE_KEY = "sensitive-v189-key-NEVER-LOG"
SENSITIVE_SECRET = "sensitive-v189-secret-NEVER-LOG"


class FakePaperClient:
    def __init__(
        self,
        *,
        account_id: str = "paper-account-1",
        positions: list[dict[str, object]] | None = None,
        open_orders: list[dict[str, object]] | None = None,
        all_orders: list[dict[str, object]] | None = None,
        asset: dict[str, object] | None = None,
        submit_status: str = "accepted",
        submit_exception_message: str = "",
        ambiguous_creates_order: bool = False,
        cancel_status: str = "canceled",
        cancel_filled_qty: str = "0",
        cancel_exception_message: str = "",
        cancel_status_on_exception: str = "",
        lookup_sequence: list[dict[str, object] | None] | None = None,
    ) -> None:
        self.account_id = account_id
        self.positions = positions if positions is not None else [_spy_position()]
        self.open_orders = open_orders if open_orders is not None else []
        self.all_orders = all_orders if all_orders is not None else []
        self.asset = asset if asset is not None else _active_spy_asset()
        self.submit_status = submit_status
        self.submit_exception_message = submit_exception_message
        self.ambiguous_creates_order = ambiguous_creates_order
        self.cancel_status = cancel_status
        self.cancel_filled_qty = cancel_filled_qty
        self.cancel_exception_message = cancel_exception_message
        self.cancel_status_on_exception = cancel_status_on_exception
        self.lookup_sequence = list(lookup_sequence or [])
        self.calls: list[str] = []
        self.submitted_requests: list[object] = []
        self.cancelled_order_ids: list[str] = []
        self.current_order: dict[str, object] | None = None

    @property
    def raw_trading_client(self) -> "FakePaperClient":
        return self

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return {
            "account_id": self.account_id,
            "status": "ACTIVE",
            "currency": "USD",
        }

    def get_positions(self) -> list[dict[str, object]]:
        self.calls.append("get_positions")
        return list(self.positions)

    def get_orders(self, query: AlpacaRecentOrderQuery) -> list[dict[str, object]]:
        self.calls.append(f"get_orders:{query.status_filter}")
        if query.status_filter == "open":
            return list(self.open_orders)
        return list(self.all_orders)

    def get_asset(self, symbol: str) -> dict[str, object]:
        self.calls.append(f"get_asset:{symbol}")
        return dict(self.asset)

    def submit_order(self, request) -> dict[str, object]:  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        if self.submit_exception_message:
            if self.ambiguous_creates_order:
                self.current_order = _order(status="accepted")
                self.all_orders = [self.current_order]
                self.open_orders = [self.current_order]
            raise RuntimeError(self.submit_exception_message)

        self.current_order = _order(
            status=self.submit_status,
            qty=str(request.qty),
            limit_price=str(request.limit_price),
        )
        self.all_orders = [self.current_order]
        self.open_orders = (
            [self.current_order] if self.submit_status not in {"rejected", "filled"} else []
        )
        return dict(self.current_order)

    def get_order_by_client_id(self, client_order_id: str) -> dict[str, object] | None:
        self.calls.append(f"get_order_by_client_id:{client_order_id}")
        if self.lookup_sequence:
            next_order = self.lookup_sequence.pop(0)
            if next_order is not None:
                self.current_order = dict(next_order)
            return next_order
        return None if self.current_order is None else dict(self.current_order)

    def cancel_order_by_id(self, order_id: str) -> dict[str, object]:
        self.calls.append(f"cancel_order_by_id:{order_id}")
        self.cancelled_order_ids.append(order_id)
        if self.cancel_exception_message:
            if self.cancel_status_on_exception and self.current_order is not None:
                self.current_order = {
                    **self.current_order,
                    "status": self.cancel_status_on_exception,
                    "filled_qty": self.cancel_filled_qty,
                }
            raise RuntimeError(self.cancel_exception_message)
        if self.current_order is not None:
            self.current_order = {
                **self.current_order,
                "status": self.cancel_status,
                "filled_qty": self.cancel_filled_qty,
            }
            self.open_orders = []
        return {"id": order_id, "status": "accepted"}


def test_exact_paper_endpoint_and_account_are_accepted(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(tmp_path)

    assert latest["outcome_classification"] == "submitted_cancel_confirmed"
    preflight = latest["preflight"]
    assert preflight["paper_endpoint_exact_match"] is True
    assert preflight["expected_paper_account_match"] is True
    assert preflight["risk_cap_passed"] is True
    assert len(client.submitted_requests) == 1


def test_live_endpoint_is_rejected_before_broker_calls(tmp_path: Path) -> None:
    client = FakePaperClient()
    config = _config(endpoint="https://api.alpaca.markets")

    latest, _root, client = _run_drill(tmp_path, client=client, config=config)

    assert latest["outcome_classification"] == "blocked_paper_endpoint_mismatch"
    assert latest["preflight"]["live_endpoint_detected"] is True
    assert client.calls == []
    assert client.submitted_requests == []


def test_expected_account_mismatch_is_rejected(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(account_id="different-paper-account"),
    )

    assert latest["outcome_classification"] == "blocked_expected_account_mismatch"
    assert latest["preflight"]["expected_paper_account_match"] is False
    assert client.submitted_requests == []


def test_missing_credentials_are_rejected_without_exposing_values(tmp_path: Path) -> None:
    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key="",
        alpaca_secret_key="",
        alpaca_paper_base_url=DEFAULT_ALPACA_PAPER_BASE_URL,
    )

    latest, root, client = _run_drill(tmp_path, config=config, env={"APP_PROFILE": "paper"})

    assert latest["outcome_classification"] == "blocked_credentials_unavailable"
    assert latest["preflight"]["paper_credentials_loaded"] is False
    assert latest["preflight"]["credential_values_exposed"] is False
    assert client.calls == []
    assert "secret" not in _artifact_text(root).lower()
    assert _artifact_names(root) >= {
        "preflight.json",
        "mutation_policy.json",
        "certification_plan.json",
        "order_lifecycle.jsonl",
        "reconciliation.json",
        "operating_brief.md",
        "manifest.jsonl",
        "latest_run.json",
    }


def test_unexpected_non_spy_position_is_rejected(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(positions=[_spy_position(), _position("MSFT", "1", "400")]),
    )

    assert latest["outcome_classification"] == "blocked_unexpected_position"
    assert latest["preflight"]["unexpected_non_spy_position_present"] is True
    assert client.submitted_requests == []


def test_existing_open_spy_order_is_rejected(tmp_path: Path) -> None:
    open_order = _order(status="accepted")

    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(open_orders=[open_order], all_orders=[open_order]),
    )

    assert latest["outcome_classification"] == "blocked_open_order_present"
    assert latest["preflight"]["open_spy_order_present"] is True
    assert client.submitted_requests == []


def test_exposure_cap_is_rejected(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(positions=[_spy_position(market_value="26.00")]),
    )

    assert latest["outcome_classification"] == "blocked_risk_cap"
    assert latest["preflight"]["risk_cap_passed"] is False
    assert client.submitted_requests == []


def test_deterministic_client_order_id_is_stable() -> None:
    assert certification_client_order_id() == V189_SPY_CERTIFICATION_CLIENT_ORDER_ID
    assert certification_client_order_id() == certification_client_order_id()


def test_duplicate_client_order_id_reconciles_by_lookup_and_does_not_resubmit(
    tmp_path: Path,
) -> None:
    duplicate = _order(status="canceled")

    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(all_orders=[duplicate]),
    )

    assert latest["outcome_classification"] == "blocked_duplicate_client_order_id"
    assert latest["preflight"]["duplicate_client_order_id_present"] is True
    assert "get_orders:all" in client.calls
    assert client.submitted_requests == []


def test_ambiguous_submit_queries_client_order_id_and_does_not_retry(
    tmp_path: Path,
) -> None:
    client = FakePaperClient(
        submit_exception_message="connection dropped after submit",
        ambiguous_creates_order=True,
    )

    latest, _root, client = _run_drill(tmp_path, client=client)

    assert latest["outcome_classification"] == "ambiguous_submit_reconciled"
    assert client.calls.count("submit_order") == 1
    assert any(call.startswith("get_order_by_client_id:") for call in client.calls)
    assert client.cancelled_order_ids == ["paper-order-1"]


def test_rejected_order_classification(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(submit_status="rejected"),
    )

    assert latest["outcome_classification"] == "submitted_then_rejected"
    assert client.cancelled_order_ids == []


def test_partial_fill_then_cancelled_reconciliation(tmp_path: Path) -> None:
    latest, _root, _client = _run_drill(
        tmp_path,
        client=FakePaperClient(cancel_filled_qty="0.00005"),
    )

    assert latest["outcome_classification"] == "submitted_partial_fill_then_cancelled"
    final_order = latest["reconciliation"]["final_order"]
    assert final_order["filled_quantity"] == "0.00005"


def test_filled_before_cancel_reconciliation(tmp_path: Path) -> None:
    filled_order = _order(status="filled", filled_qty="0.0001")
    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(lookup_sequence=[filled_order]),
    )

    assert latest["outcome_classification"] == "submitted_filled_before_cancel"
    assert client.cancelled_order_ids == []


def test_confirmed_cancellation_reconciliation(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(tmp_path, client=FakePaperClient())

    assert latest["outcome_classification"] == "submitted_cancel_confirmed"
    assert client.cancelled_order_ids == ["paper-order-1"]
    assert latest["reconciliation"]["final_order_status"] == "canceled"


def test_cancel_ambiguity_resolves_by_lookup_when_terminal(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(
            cancel_exception_message="cancel response lost",
            cancel_status_on_exception="canceled",
        ),
    )

    assert latest["outcome_classification"] == "submitted_cancel_confirmed"
    assert client.cancelled_order_ids == ["paper-order-1"]


def test_cancel_ambiguity_without_terminal_lookup_is_unresolved(tmp_path: Path) -> None:
    latest, _root, client = _run_drill(
        tmp_path,
        client=FakePaperClient(cancel_exception_message="cancel response lost"),
    )

    assert latest["outcome_classification"] == "unresolved_order_outcome"
    assert client.cancelled_order_ids == ["paper-order-1"]


def test_process_lock_contention_blocks_second_runner(tmp_path: Path) -> None:
    root = tmp_path / "certification"
    root.mkdir()
    (root / ".mutation.lock").write_text("locked", encoding="utf-8")
    client = FakePaperClient()

    latest, _root, client = _run_drill(tmp_path, root=root, client=client)

    assert latest["outcome_classification"] == "blocked_process_lock"
    assert latest["preflight"]["mutation_process_lock_acquired"] is False
    assert client.calls == []
    assert (root / ".mutation.lock").is_file()


def test_artifact_values_contain_no_credential_material(tmp_path: Path) -> None:
    client = FakePaperClient(
        submit_exception_message=f"submit failed with {SENSITIVE_SECRET}",
    )
    config = _config(api_key=SENSITIVE_KEY, secret_key=SENSITIVE_SECRET)
    env = _env(api_key=SENSITIVE_KEY, secret_key=SENSITIVE_SECRET)

    latest, root, _client = _run_drill(
        tmp_path,
        client=client,
        config=config,
        env=env,
    )

    assert latest["outcome_classification"] == "unresolved_order_outcome"
    artifact_text = _artifact_text(root)
    assert SENSITIVE_KEY not in artifact_text
    assert SENSITIVE_SECRET not in artifact_text
    assert "<redacted>" in artifact_text


def test_strategy_hold_noop_never_calls_mutation() -> None:
    plan = {
        "execution_plan_id": "daily_execution_plan_1",
        "execution_plan_action": "hold/noop",
        "execution_plan_submit_allowed": False,
        "execution_plan_paper_submit_authorized": False,
    }

    result = evaluate_strategy_plan_mutation_lane(plan, mutation_gateway=object())

    assert result["outcome_classification"] == "not_submitted_hold_noop"
    assert result["paper_submit_performed"] is False
    assert result["broker_mutation_performed"] is False
    assert result["mutation_gateway_touched"] is False


def test_env_secret_alias_is_accepted_without_printing_values() -> None:
    config = paper_config_from_env_aliases(
        {
            "APP_PROFILE": "paper",
            "ALPACA_API_KEY": SENSITIVE_KEY,
            "ALPACA_API_SECRET_KEY": SENSITIVE_SECRET,
            "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
        }
    )

    assert config.is_paper_profile is True
    assert config.alpaca_api_key == SENSITIVE_KEY
    assert config.alpaca_secret_key == SENSITIVE_SECRET


def _run_drill(
    tmp_path: Path,
    *,
    root: Path | None = None,
    client: FakePaperClient | None = None,
    config: AlpacaPaperConfig | None = None,
    env: dict[str, str] | None = None,
    expected_account_id: str = "paper-account-1",
) -> tuple[dict[str, object], Path, FakePaperClient]:
    output_root = root or tmp_path / "certification"
    fake_client = client or FakePaperClient()
    paper_config = config or _config()
    source_env = env or _env()
    latest = run_paper_certification_drill(
        paper_config=paper_config,
        gateway=PaperMutationGateway(fake_client),
        runtime=PaperCertificationRuntime(
            output_root=output_root,
            expected_paper_account_id=expected_account_id,
            timeout_seconds=0,
            poll_interval_seconds=0,
        ),
        env=source_env,
    )
    return latest, output_root, fake_client


def _config(
    *,
    endpoint: str = DEFAULT_ALPACA_PAPER_BASE_URL,
    api_key: str = "paper-key",
    secret_key: str = "paper-secret",
) -> AlpacaPaperConfig:
    return AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key=api_key,
        alpaca_secret_key=secret_key,
        alpaca_paper_base_url=endpoint,
    )


def _env(
    *,
    endpoint: str = DEFAULT_ALPACA_PAPER_BASE_URL,
    api_key: str = "paper-key",
    secret_key: str = "paper-secret",
) -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": api_key,
        "ALPACA_SECRET_KEY": secret_key,
        "ALPACA_PAPER_BASE_URL": endpoint,
    }


def _spy_position(
    qty: str = "0.01",
    market_value: str = "6.00",
) -> dict[str, object]:
    return _position("SPY", qty, market_value)


def _position(symbol: str, qty: str, market_value: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "qty": Decimal(qty),
        "market_value": Decimal(market_value),
        "average_entry_price": Decimal("500.00"),
        "side": "long",
    }


def _order(
    *,
    status: str,
    qty: str = "0.0001",
    filled_qty: str = "0",
    limit_price: str = "630.00",
) -> dict[str, object]:
    return {
        "id": "paper-order-1",
        "client_order_id": V189_SPY_CERTIFICATION_CLIENT_ORDER_ID,
        "symbol": "SPY",
        "asset_class": "equity",
        "side": "sell",
        "type": "limit",
        "time_in_force": "day",
        "qty": Decimal(qty),
        "limit_price": Decimal(limit_price),
        "status": status,
        "filled_qty": Decimal(filled_qty),
        "filled_avg_price": Decimal("0") if filled_qty == "0" else Decimal("620.00"),
        "created_at": NOW,
        "submitted_at": NOW,
    }


def _active_spy_asset() -> dict[str, object]:
    return {
        "symbol": "SPY",
        "asset_class": "us_equity",
        "status": "active",
        "tradable": True,
        "fractionable": True,
    }


def _artifact_text(root: Path) -> str:
    parts = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.name != ".mutation.lock":
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _artifact_names(root: Path) -> set[str]:
    return {path.name for path in root.iterdir() if path.is_file()}
