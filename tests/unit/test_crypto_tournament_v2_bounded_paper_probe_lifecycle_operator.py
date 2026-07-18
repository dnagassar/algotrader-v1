from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import io
import json
from pathlib import Path
from typing import Any
import sys
from uuid import UUID

import pytest

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.errors import ValidationError
from algotrader.execution import (
    crypto_tournament_v2_bounded_paper_probe_lifecycle_operator
    as operator_subject,
)
from algotrader.core.crypto_bounded_probe_lifecycle import (
    SAFETY_POLICY_FINGERPRINT,
    build_ready_lifecycle_plan,
    build_dormant_lifecycle_plan,
    canonical_json_bytes,
    exact_operation_authorization_text,
    stable_hash,
)
from algotrader.core.paper_account_binding import (
    build_alpaca_paper_account_binding,
)
from algotrader.execution.crypto_tournament_v2_bounded_paper_probe_lifecycle_operator import (
    _load_canonical_plan,
    _read_exact_authorization_stdin,
    _runtime_source_bundle_sha256,
    build_parser,
    run_crypto_tournament_v2_bounded_paper_probe_lifecycle,
    validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt,
)


NOW = datetime(2026, 8, 13, 0, 5, tzinfo=UTC)
ACCOUNT_ID = "paper-account-v530"
KEY = "paper-key-value"
SECRET = "paper-secret-value"
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


VENUE_ROLES = (
    "venue_refresh_manifest",
    "venue_universe",
    "orderability_metadata",
    "venue_router_input_manifest",
    "venue_runtime_visibility_status",
    "venue_refresh_source",
    "venue_visibility_operator_source",
    "venue_supervisor_source",
)


def _candidate(symbol: str) -> dict[str, object]:
    unsigned: dict[str, object] = {
        "candidate_id": (
            f"crypto:tournament_v2:{symbol}:trend_momentum_72h"
        ),
        "symbol": symbol,
        "strategy_id": "trend_momentum_72h",
        "strategy_family": "trend_momentum",
        "elapsed_hour_parameters": {"lookback_hours": 72},
        "primary_1h_parameters": {"lookback_bars": 72},
        "robustness_4h_parameters": {"lookback_bars": 18},
        "direction": "long_or_cash",
        "signal_execution": "one_bar_lag",
        "imputed_bar_transition_policy": (
            "hold_prior_target_no_transition"
        ),
        "factory_version": "unit-test-v2",
    }
    return {
        **unsigned,
        "candidate_fingerprint": stable_hash(unsigned),
    }


def _orderability_record(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "asset_class": "crypto",
        "source_mode": "paper_read_only",
        "broker_state_mode": "alpaca_paper_observed",
        "tradable": True,
        "status": "active",
        "min_notional": "1",
        "min_order_notional": "1",
        "min_order_size": "0.000001",
        "min_trade_increment": "0.000001",
        "price_increment": "0.01",
        "qty_increment": "0.000001",
        "broker_observed_min_notional": "1",
        "broker_observed_min_order_size": "0.000001",
        "broker_observed_min_trade_increment": "0.000001",
        "broker_observed_price_increment": "0.01",
        "derived_min_order_value": "1",
        "orderability_basis": "broker_notional_and_qty_metadata",
        "metadata_status": "metadata_observed",
        "metadata_blockers": [],
        "orderability_status": "notional_orderable",
        "orderability_blockers": [],
    }


def _plan(
    symbol: str,
    account_id: str = ACCOUNT_ID,
) -> dict[str, object]:
    return build_ready_lifecycle_plan(
        symbol=symbol,
        terminal_binding={
            "selected_symbol": symbol,
            "selected_candidate": _candidate(symbol),
            "classification": (
                "evidence_complete_for_bounded_paper_probe_review"
            ),
            "preregistration_fingerprint": SHA_A,
            "activation_fingerprint": SHA_B,
            "state_fingerprint": SHA_C,
            "terminal_evidence_fingerprint": SHA_A,
            "terminal_closed_at": (NOW - timedelta(minutes=5)).isoformat(),
            "evidence_export_fingerprint": SHA_B,
            "terminal_source_sha256": SHA_C,
        },
        venue_binding={
            "target_symbol": symbol,
            "observed_at": NOW.isoformat(),
            "bundle_fingerprint": SHA_A,
            "resolved_source_digests": {
                role: SHA_B for role in VENUE_ROLES
            },
            "orderability_record": _orderability_record(symbol),
        },
        safety_binding={
            "policy_fingerprint": SAFETY_POLICY_FINGERPRINT,
            "certification_receipt_fingerprint": SHA_A,
            "certification_source_sha256": SHA_B,
            "kernel_source_sha256": SHA_C,
            "certifier_source_sha256": SHA_A,
            "focused_test_source_sha256": SHA_B,
            "runtime_source_bundle_sha256": _runtime_source_bundle_sha256(),
            "certified_at": NOW.isoformat(),
        },
        account_binding=build_alpaca_paper_account_binding(
            {"account_id": account_id},
            expected_account_configured=True,
            expected_account_matched=True,
        ),
        as_of=NOW,
    )


def _env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": KEY,
        "ALPACA_SECRET_KEY": SECRET,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }


def _value(value: object) -> object:
    return getattr(value, "value", value)


class StatefulLifecycleClient:
    def __init__(
        self,
        symbol: str,
        *,
        now: datetime = NOW,
        raise_after_entry_side_effect: bool = False,
        raise_after_exit_side_effect: bool = False,
        hide_lookup: bool = False,
    ) -> None:
        self.symbol = symbol
        self.now = now
        self.raise_after_entry_side_effect = raise_after_entry_side_effect
        self.raise_after_exit_side_effect = raise_after_exit_side_effect
        self.hide_lookup = hide_lookup
        self.orders: dict[str, dict[str, object]] = {}
        self.position_qty = Decimal("0")
        self.submit_calls: list[str] = []
        self.cancel_calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        return {
            "account_id": ACCOUNT_ID,
            "id": ACCOUNT_ID,
            "account_number": "redacted-account-number",
            "status": "ACTIVE",
            "cash": "1000",
            "blocked": False,
            "account_blocked": False,
            "trading_blocked": False,
        }

    def get_all_positions(self) -> list[dict[str, object]]:
        if self.position_qty == 0:
            return []
        return [
            {
                "symbol": self.symbol,
                "qty": str(self.position_qty),
                "side": "long",
                "avg_entry_price": "1000",
                "market_value": str(self.position_qty * Decimal("1000")),
                "unrealized_pl": "0",
            }
        ]

    def get_all_assets(self) -> list[dict[str, object]]:
        return [self.get_asset(self.symbol)]

    def get_asset(self, symbol: str) -> dict[str, object]:
        assert symbol == self.symbol
        return {
            "symbol": self.symbol,
            "asset_class": "crypto",
            "tradable": True,
            "status": "active",
        }

    def get_orders(self, _query: object = None) -> list[dict[str, object]]:
        return [
            order
            for order in self.orders.values()
            if order["status"] in {"accepted", "new", "partially_filled"}
        ]

    def get_order_by_client_id(
        self,
        client_order_id: str,
    ) -> dict[str, object]:
        if self.hide_lookup:
            raise RuntimeError("temporarily hidden")
        if client_order_id not in self.orders:
            raise RuntimeError("not found")
        return self.orders[client_order_id]

    def get_crypto_latest_trade(
        self,
        symbol: str,
    ) -> dict[str, dict[str, object]]:
        assert symbol == self.symbol
        return {
            symbol: {
                "symbol": symbol,
                "price": "1000",
                "timestamp": self.now,
            }
        }

    def submit_order(self, request: Any) -> dict[str, object]:
        client_order_id = str(_value(request.client_order_id))
        side = str(_value(request.side)).lower()
        self.submit_calls.append(side)
        if side == "buy":
            qty = Decimal("0.01")
            submitted_at = self.now - timedelta(seconds=3)
            filled_at = self.now - timedelta(seconds=2)
            self.position_qty = qty
        else:
            qty = Decimal(str(_value(request.qty)))
            submitted_at = self.now - timedelta(seconds=1)
            filled_at = self.now
            self.position_qty -= qty
        order = {
            "id": f"broker-{side}-{len(self.submit_calls)}",
            "client_order_id": client_order_id,
            "symbol": self.symbol,
            "side": side,
            "status": "filled",
            "asset_class": "crypto",
            "type": "market",
            "time_in_force": "gtc",
            "limit_price": "",
            "qty": "" if side == "buy" else str(qty),
            "notional": "10" if side == "buy" else "",
            "filled_qty": str(qty),
            "filled_avg_price": "1000",
            "submitted_at": submitted_at,
            "filled_at": filled_at,
        }
        self.orders[client_order_id] = order
        if side == "buy" and self.raise_after_entry_side_effect:
            self.raise_after_entry_side_effect = False
            raise RuntimeError("response lost after broker side effect")
        if side == "sell" and self.raise_after_exit_side_effect:
            self.raise_after_exit_side_effect = False
            self.hide_lookup = True
            raise RuntimeError("exit response lost after broker side effect")
        return order

    def cancel_order_by_id(self, broker_order_id: str) -> None:
        self.cancel_calls.append(broker_order_id)
        for order in self.orders.values():
            if order["id"] == broker_order_id:
                order["status"] = "canceled"
                return
        raise RuntimeError("order not found")


class LaterFillLifecycleClient(StatefulLifecycleClient):
    def submit_order(self, request: Any) -> dict[str, object]:
        quote_time = self.now
        self.now = quote_time + timedelta(seconds=4)
        try:
            return super().submit_order(request)
        finally:
            self.now = quote_time

# lifecycle operator tests


def _run(
    tmp_path: Path,
    plan: dict[str, object],
    client: StatefulLifecycleClient,
    *,
    timestamp: datetime,
    clock: Any = None,
    expected_account_id: str = ACCOUNT_ID,
) -> dict[str, object]:
    return run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
        plan,
        output_root=tmp_path / "out",
        journal_path=tmp_path / "orders.sqlite3",
        safety_state_path=tmp_path / "safety.sqlite3",
        timestamp=timestamp,
        clock=(clock or (lambda: client.now)),
        env=_env(),
        broker_client_factory=lambda _config: client,
        exact_operation_authorization=exact_operation_authorization_text(plan),
        expected_paper_account_id=expected_account_id,
        paper_mutation_authorized=True,
        allow_network=True,
        reconciliation_poll_attempts=1,
        reconciliation_poll_interval_seconds=0,
        write_artifacts=True,
    )


@pytest.mark.parametrize("symbol", ("BTCUSD", "ETHUSD", "SOLUSD"))
def test_exact_winner_full_fill_entry_exit_is_one_shot_and_flat(
    tmp_path: Path,
    symbol: str,
) -> None:
    plan = _plan(symbol)
    client = StatefulLifecycleClient(symbol)

    result = _run(tmp_path, plan, client, timestamp=NOW)

    validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
        result
    )
    assert result["outcome_classification"] == "filled_exit_confirmed"
    assert result["entry_attempt_count"] == 1
    assert result["cancel_attempt_count"] == 0
    assert result["exit_attempt_count"] == 1
    assert result["entry_final_order"]["status"] == "filled"
    assert result["exit_final_order"]["status"] == "filled"
    assert result["final_position_count"] == 0
    assert result["final_open_order_count"] == 0
    assert client.submit_calls == ["buy", "sell"]
    assert client.cancel_calls == []
    rendered = (
        (tmp_path / "out" / "latest" / "lifecycle_result.json")
        .read_text(encoding="utf-8")
    )
    assert KEY not in rendered
    assert SECRET not in rendered
    assert ACCOUNT_ID not in rendered


def test_receipt_time_advances_to_latest_observed_fill(tmp_path: Path) -> None:
    plan = _plan("BTCUSD")
    client = LaterFillLifecycleClient("BTCUSD")

    result = _run(tmp_path, plan, client, timestamp=NOW)

    validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
        result
    )
    assert result["as_of"] == (NOW + timedelta(seconds=4)).isoformat()


def test_dormant_plan_returns_before_environment_or_client(
    tmp_path: Path,
) -> None:
    factory_calls: list[object] = []
    plan = build_dormant_lifecycle_plan(NOW)

    result = run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
        plan,
        output_root=tmp_path / "out",
        journal_path=tmp_path / "orders.sqlite3",
        safety_state_path=tmp_path / "safety.sqlite3",
        timestamp=NOW,
        env={
            "APP_PROFILE": "live",
            "ALPACA_API_KEY": "must-not-be-read",
            "ALPACA_SECRET_KEY": "must-not-be-read",
        },
        broker_client_factory=lambda config: factory_calls.append(config),
        write_artifacts=False,
    )

    assert result["outcome_classification"] == (
        "dormant_pending_terminal_winner"
    )
    assert result["broker_read_occurred"] is False
    assert result["broker_mutation_performed"] is False
    assert factory_calls == []
def test_authorization_denial_happens_before_client_construction(
    tmp_path: Path,
) -> None:
    plan = _plan("ETHUSD")
    factory_calls: list[object] = []

    result = run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
        plan,
        output_root=tmp_path / "out",
        journal_path=tmp_path / "orders.sqlite3",
        safety_state_path=tmp_path / "safety.sqlite3",
        timestamp=NOW,
        env={},
        broker_client_factory=lambda config: factory_calls.append(config),
        exact_operation_authorization="wrong",
        expected_paper_account_id=ACCOUNT_ID,
        paper_mutation_authorized=False,
        allow_network=False,
        write_artifacts=False,
    )

    assert result["outcome_classification"] == "blocked_before_broker_read"
    assert result["broker_read_occurred"] is False
    assert result["broker_mutation_performed"] is False
    assert "exact_operation_authorization_mismatch" in result["blockers"]
    assert factory_calls == []


def test_response_loss_restarts_by_exact_lookup_without_duplicate_entry(
    tmp_path: Path,
) -> None:
    plan = _plan("SOLUSD")
    client = StatefulLifecycleClient(
        "SOLUSD",
        raise_after_entry_side_effect=True,
        hide_lookup=True,
    )

    first = _run(tmp_path, plan, client, timestamp=NOW)

    assert first["outcome_classification"] == "entry_ambiguous"
    assert first["broker_ambiguity"] is True
    assert first["entry_attempt_count"] == 1
    assert client.submit_calls == ["buy"]

    client.hide_lookup = False
    client.now = NOW + timedelta(minutes=1)
    second = _run(
        tmp_path,
        plan,
        client,
        timestamp=NOW + timedelta(minutes=1),
    )

    assert second["outcome_classification"] == "filled_exit_confirmed"
    assert second["entry_attempt_count"] == 1
    assert second["exit_attempt_count"] == 1
    assert client.submit_calls == ["buy", "sell"]


def test_exit_response_loss_reconciles_without_duplicate_submit(
    tmp_path: Path,
) -> None:
    plan = _plan("ETHUSD")
    client = StatefulLifecycleClient(
        "ETHUSD",
        raise_after_exit_side_effect=True,
    )

    first = _run(tmp_path, plan, client, timestamp=NOW)

    assert first["outcome_classification"] == "exit_ambiguous_residual_position"
    assert first["broker_ambiguity"] is True
    assert first["entry_attempt_count"] == 1
    assert first["exit_attempt_count"] == 1
    assert client.position_qty == 0
    assert client.submit_calls == ["buy", "sell"]

    client.hide_lookup = False
    client.now = NOW + timedelta(minutes=1)
    second = _run(
        tmp_path,
        plan,
        client,
        timestamp=NOW + timedelta(minutes=1),
    )

    assert second["outcome_classification"] == "filled_exit_confirmed"
    assert second["broker_ambiguity"] is False
    assert second["broker_mutation_performed"] is True
    assert second["paper_submit_performed"] is True
    assert second["entry_attempt_count"] == 1
    assert second["exit_attempt_count"] == 1
    assert client.submit_calls == ["buy", "sell"]
def test_success_receipt_tamper_fails_closed(tmp_path: Path) -> None:
    plan = _plan("BTCUSD")
    result = _run(
        tmp_path,
        plan,
        StatefulLifecycleClient("BTCUSD"),
        timestamp=NOW,
    )
    result["exit_attempt_count"] = 2

    with pytest.raises(Exception, match="fingerprint mismatch"):
        validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
            result
        )


def _resign_success_receipt_order(
    receipt: dict[str, object],
    role: str,
) -> None:
    field_name = f"{role}_final_order"
    order = dict(receipt[field_name])
    unsigned_order = dict(order)
    unsigned_order.pop("order_fingerprint", None)
    order["order_fingerprint"] = stable_hash(unsigned_order)
    receipt[field_name] = order

    unsigned_receipt = dict(receipt)
    unsigned_receipt.pop("lifecycle_fingerprint", None)
    receipt["lifecycle_fingerprint"] = stable_hash(unsigned_receipt)


@pytest.mark.parametrize(
    ("role", "field_name", "drifted_value", "expected_blocker"),
    (
        ("entry", "asset_class", "equity", "lookup_asset_class_mismatch"),
        ("entry", "order_type", "limit", "lookup_order_type_mismatch"),
        ("entry", "time_in_force", "ioc", "lookup_time_in_force_mismatch"),
        ("entry", "limit_price", "1", "lookup_unexpected_limit_price"),
        ("entry", "qty", "0.01", "lookup_order_quantity_mismatch"),
        ("entry", "type", "limit", "lookup_order_type_ambiguous"),
        ("exit", "notional", "10", "lookup_order_notional_mismatch"),
        ("exit", "qty", "0.02", "lookup_order_quantity_mismatch"),
    ),
)
def test_success_receipt_rejects_drifted_authorized_order_shape(
    tmp_path: Path,
    role: str,
    field_name: str,
    drifted_value: str,
    expected_blocker: str,
) -> None:
    result = _run(
        tmp_path,
        _plan("BTCUSD"),
        StatefulLifecycleClient("BTCUSD"),
        timestamp=NOW,
    )
    order = dict(result[f"{role}_final_order"])
    order[field_name] = drifted_value
    result[f"{role}_final_order"] = order
    _resign_success_receipt_order(result, role)

    with pytest.raises(
        ValidationError,
        match=f"{role} request shape drifted: {expected_blocker}",
    ):
        validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
            result
        )


class OpenEntryLifecycleClient(StatefulLifecycleClient):
    def submit_order(self, request: Any) -> dict[str, object]:
        client_order_id = str(_value(request.client_order_id))
        side = str(_value(request.side)).lower()
        if side != "buy":
            return super().submit_order(request)
        self.submit_calls.append(side)
        order = {
            "id": "broker-open-entry",
            "client_order_id": client_order_id,
            "symbol": self.symbol,
            "side": "buy",
            "status": "new",
            "asset_class": "crypto",
            "type": "market",
            "time_in_force": "gtc",
            "limit_price": "",
            "qty": "",
            "notional": "10",
            "filled_qty": "0",
            "filled_avg_price": "",
            "submitted_at": self.now,
            "filled_at": "",
        }
        self.orders[client_order_id] = order
        return order


def test_open_entry_is_canceled_once_only_after_exact_expiry(
    tmp_path: Path,
) -> None:
    plan = _plan("ETHUSD")
    client = OpenEntryLifecycleClient("ETHUSD")

    first = _run(tmp_path, plan, client, timestamp=NOW)

    assert first["outcome_classification"] == "entry_open_waiting_for_expiry"
    assert first["entry_attempt_count"] == 1
    assert first["cancel_attempt_count"] == 0
    assert client.submit_calls == ["buy"]
    assert client.cancel_calls == []

    after_expiry = NOW + timedelta(minutes=16)
    client.now = after_expiry
    second = _run(tmp_path, plan, client, timestamp=after_expiry)

    assert second["outcome_classification"] == "entry_terminal_no_position"
    assert second["entry_attempt_count"] == 1
    assert second["cancel_attempt_count"] == 1
    assert second["exit_attempt_count"] == 0
    assert client.submit_calls == ["buy"]
    assert client.cancel_calls == ["broker-open-entry"]


class CashDropsAfterEntryClient(StatefulLifecycleClient):
    def get_account(self) -> dict[str, object]:
        account = super().get_account()
        account["cash"] = "0" if self.position_qty > 0 else "1000"
        return account


class ExternalOpenOrderClient(StatefulLifecycleClient):
    def __init__(self, symbol: str, *, status: str) -> None:
        super().__init__(symbol)
        self.status = status
        self.order_queries: list[object] = []

    def get_orders(self, query: object = None) -> list[dict[str, object]]:
        self.order_queries.append(query)
        return [
            *super().get_orders(query),
            {
                "id": "foreign-open-order",
                "client_order_id": "foreign-client-order",
                "symbol": "AAPL",
                "side": "buy",
                "status": self.status,
                "qty": "1",
                "notional": "",
                "filled_qty": "0",
                "filled_avg_price": "",
                "submitted_at": self.now,
                "filled_at": "",
            },
        ]


class ObservedPositionsClient(StatefulLifecycleClient):
    def __init__(
        self,
        symbol: str,
        positions: list[dict[str, object]],
    ) -> None:
        super().__init__(symbol)
        self.observed_positions = positions

    def get_all_positions(self) -> list[dict[str, object]]:
        return self.observed_positions


class ForeignAfterEntryClient(StatefulLifecycleClient):
    def get_all_positions(self) -> list[dict[str, object]]:
        positions = super().get_all_positions()
        if self.position_qty > 0:
            positions.append(
                {
                    "symbol": "ETHUSD",
                    "qty": "0.02",
                    "side": "long",
                    "avg_entry_price": "1000",
                    "market_value": "20",
                    "unrealized_pl": "0",
                }
            )
        return positions


class UuidAccountClient(StatefulLifecycleClient):
    def __init__(self, symbol: str, account_id: UUID) -> None:
        super().__init__(symbol)
        self.account_id = account_id

    def get_account(self) -> dict[str, object]:
        account = super().get_account()
        account.pop("account_id")
        account["id"] = self.account_id
        return account


class AccountEvidenceClient(StatefulLifecycleClient):
    def __init__(
        self,
        symbol: str,
        *,
        patch: dict[str, object] | None = None,
        remove: tuple[str, ...] = (),
    ) -> None:
        super().__init__(symbol)
        self.patch = patch or {}
        self.remove = remove

    def get_account(self) -> dict[str, object]:
        account = super().get_account()
        for field_name in self.remove:
            account.pop(field_name, None)
        account.update(self.patch)
        return account


class AssetEvidenceClient(StatefulLifecycleClient):
    def __init__(
        self,
        symbol: str,
        *,
        patch: dict[str, object] | None = None,
        remove: tuple[str, ...] = (),
    ) -> None:
        super().__init__(symbol)
        self.patch = patch or {}
        self.remove = remove

    def get_asset(self, symbol: str) -> dict[str, object]:
        asset = super().get_asset(symbol)
        for field_name in self.remove:
            asset.pop(field_name, None)
        asset.update(self.patch)
        return asset


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self.values = list(values)
        self.last = values[-1]

    def __call__(self) -> datetime:
        if self.values:
            self.last = self.values.pop(0)
        return self.last


def test_entry_only_cash_drop_does_not_strand_confirmed_entry(
    tmp_path: Path,
) -> None:
    plan = _plan("BTCUSD")
    client = CashDropsAfterEntryClient("BTCUSD")

    result = _run(tmp_path, plan, client, timestamp=NOW)

    validate_crypto_tournament_v2_bounded_paper_probe_lifecycle_receipt(
        result
    )
    assert result["outcome_classification"] == "filled_exit_confirmed"
    assert result["blockers"] == []
    assert client.submit_calls == ["buy", "sell"]
    assert result["final_position_count"] == 0


@pytest.mark.parametrize("status", ("new", "pending_replace"))
def test_account_wide_open_order_blocks_entry_without_status_filtering(
    tmp_path: Path,
    status: str,
) -> None:
    plan = _plan("SOLUSD")
    client = ExternalOpenOrderClient("SOLUSD", status=status)

    result = _run(tmp_path, plan, client, timestamp=NOW)

    assert result["outcome_classification"] == "blocked_before_entry"
    assert "entry_requires_account_wide_flat_no_open_orders" in (
        result["blockers"]
    )
    assert result["final_open_order_count"] == 1
    assert client.submit_calls == []
    query = client.order_queries[-1]
    assert _value(getattr(query, "status", "")) == "open"
    assert getattr(query, "limit", None) == 100
    assert getattr(query, "symbols", None) in (None, [])


@pytest.mark.parametrize(
    "qty",
    (None, "bogus", float("nan"), float("inf")),
)
def test_malformed_position_quantity_fails_closed_with_observed_count(
    tmp_path: Path,
    qty: object,
) -> None:
    position = {
        "symbol": "BTCUSD",
        "side": "long",
        "avg_entry_price": "1000",
        "market_value": "10",
        "unrealized_pl": "0",
    }
    if qty is not None:
        position["qty"] = qty
    client = ObservedPositionsClient("BTCUSD", [position])

    result = _run(tmp_path, _plan("BTCUSD"), client, timestamp=NOW)

    assert result["outcome_classification"] == (
        "blocked_by_broker_snapshot"
    )
    assert "account_wide_position_quantity_invalid" in result["blockers"]
    assert result["final_position_count"] == 1
    assert client.submit_calls == []


@pytest.mark.parametrize(
    ("side", "blocker"),
    (
        (None, "account_wide_position_side_invalid"),
        ("unknown", "account_wide_position_side_invalid"),
        ("short", "short_position_observed"),
    ),
)
def test_non_long_position_side_fails_closed(
    tmp_path: Path,
    side: object,
    blocker: str,
) -> None:
    position: dict[str, object] = {
        "symbol": "BTCUSD",
        "qty": "0.01",
        "avg_entry_price": "1000",
        "market_value": "10",
        "unrealized_pl": "0",
    }
    if side is not None:
        position["side"] = side
    client = ObservedPositionsClient("BTCUSD", [position])

    result = _run(tmp_path, _plan("BTCUSD"), client, timestamp=NOW)

    assert result["outcome_classification"] == (
        "blocked_by_broker_snapshot"
    )
    assert blocker in result["blockers"]
    assert result["final_position_count"] == 1
    assert client.submit_calls == []


@pytest.mark.parametrize(
    ("client", "blocker"),
    (
        (
            AccountEvidenceClient(
                "BTCUSD",
                remove=("trading_blocked",),
            ),
            "paper_account_blocking_fields_invalid",
        ),
        (
            AccountEvidenceClient(
                "BTCUSD",
                patch={"account_blocked": "false"},
            ),
            "paper_account_blocking_fields_invalid",
        ),
        (
            AccountEvidenceClient(
                "BTCUSD",
                patch={"trading_blocked": True},
            ),
            "paper_account_trading_blocked",
        ),
        (
            AssetEvidenceClient(
                "BTCUSD",
                remove=("status",),
            ),
            "selected_asset_not_tradable",
        ),
        (
            AssetEvidenceClient(
                "BTCUSD",
                patch={"asset_class": "us_equity"},
            ),
            "selected_asset_not_tradable",
        ),
    ),
)
def test_entry_requires_explicit_account_and_asset_evidence(
    tmp_path: Path,
    client: StatefulLifecycleClient,
    blocker: str,
) -> None:
    result = _run(tmp_path, _plan("BTCUSD"), client, timestamp=NOW)

    assert result["outcome_classification"] == "blocked_before_entry"
    assert blocker in result["blockers"]
    assert client.submit_calls == []


def test_target_plus_foreign_position_is_not_misreported_flat(
    tmp_path: Path,
) -> None:
    plan = _plan("BTCUSD")
    client = ForeignAfterEntryClient("BTCUSD")

    result = _run(tmp_path, plan, client, timestamp=NOW)

    assert result["outcome_classification"] == (
        "manual_reconciliation_required"
    )
    assert "entry_position_attribution_or_open_order_mismatch" in (
        result["blockers"]
    )
    assert result["final_position_count"] == 2
    assert client.submit_calls == ["buy"]


def test_future_plan_blocks_before_client_construction(tmp_path: Path) -> None:
    plan = _plan("ETHUSD")
    factory_calls: list[object] = []
    before_plan = NOW - timedelta(seconds=1)

    result = run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
        plan,
        output_root=tmp_path / "out",
        journal_path=tmp_path / "orders.sqlite3",
        safety_state_path=tmp_path / "safety.sqlite3",
        timestamp=before_plan,
        clock=lambda: before_plan,
        env=_env(),
        broker_client_factory=lambda config: factory_calls.append(config),
        exact_operation_authorization=exact_operation_authorization_text(plan),
        expected_paper_account_id=ACCOUNT_ID,
        paper_mutation_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert result["outcome_classification"] == (
        "blocked_before_broker_read"
    )
    assert result["blockers"] == ["plan_as_of_from_future"]
    assert factory_calls == []


def test_entry_expiry_is_rechecked_immediately_before_submit(
    tmp_path: Path,
) -> None:
    plan = _plan("SOLUSD")
    client = StatefulLifecycleClient("SOLUSD")
    expired = NOW + timedelta(minutes=16)
    clock = SequenceClock(NOW, NOW, expired)

    result = _run(
        tmp_path,
        plan,
        client,
        timestamp=NOW,
        clock=clock,
    )

    assert result["outcome_classification"] == "blocked_before_entry"
    assert "entry_authorization_expired_before_submit" in (
        result["blockers"]
    )
    assert client.submit_calls == []


def test_uuid_account_identity_is_normalized_before_binding(
    tmp_path: Path,
) -> None:
    account_id = UUID("12345678-1234-5678-1234-567812345678")
    account_text = str(account_id)
    plan = _plan("BTCUSD", account_id=account_text)
    client = UuidAccountClient("BTCUSD", account_id)

    result = _run(
        tmp_path,
        plan,
        client,
        timestamp=NOW,
        expected_account_id=account_text,
    )

    assert result["outcome_classification"] == "filled_exit_confirmed"
    assert client.submit_calls == ["buy", "sell"]


class WrongClientOrderLookupClient(StatefulLifecycleClient):
    def get_order_by_client_id(
        self,
        client_order_id: str,
    ) -> dict[str, object]:
        order = dict(super().get_order_by_client_id(client_order_id))
        order["client_order_id"] = "wrong-deterministic-client-id"
        return order


class MismatchedCancelLookupClient(OpenEntryLifecycleClient):
    mismatched_lookup = False

    def get_orders(
        self,
        query: object = None,
    ) -> list[dict[str, object]]:
        orders = [dict(order) for order in super().get_orders(query)]
        if self.mismatched_lookup:
            for order in orders:
                order["id"] = "different-broker-order"
        return orders


class InvalidExitChronologyClient(StatefulLifecycleClient):
    def submit_order(self, request: Any) -> dict[str, object]:
        order = super().submit_order(request)
        if str(_value(request.side)).lower() == "sell":
            order["submitted_at"] = self.now - timedelta(minutes=2)
            order["filled_at"] = self.now - timedelta(minutes=1)
        return order


class BinaryStdin:
    def __init__(self, payload: bytes) -> None:
        self.buffer = io.BytesIO(payload)


def test_direct_lookup_rejects_wrong_deterministic_client_id(
    tmp_path: Path,
) -> None:
    client = WrongClientOrderLookupClient("BTCUSD")

    result = _run(tmp_path, _plan("BTCUSD"), client, timestamp=NOW)

    assert result["outcome_classification"] == "entry_ambiguous"
    assert "lookup_client_order_id_mismatch" in result["blockers"]
    assert result["broker_ambiguity"] is True
    assert client.submit_calls == ["buy"]
    assert client.position_qty > 0


def test_cancel_requires_same_broker_identity_as_account_snapshot(
    tmp_path: Path,
) -> None:
    client = MismatchedCancelLookupClient("ETHUSD")
    plan = _plan("ETHUSD")

    first = _run(tmp_path, plan, client, timestamp=NOW)

    assert first["outcome_classification"] == "entry_open_waiting_for_expiry"
    client.now = NOW + timedelta(minutes=16)
    client.mismatched_lookup = True

    second = _run(tmp_path, plan, client, timestamp=client.now)

    assert second["outcome_classification"] == "blocked_before_cancel"
    assert "lookup_broker_order_identity_mismatch" in second["blockers"]
    assert client.cancel_calls == []


def test_clock_regression_after_entry_mutation_is_durable(
    tmp_path: Path,
) -> None:
    client = StatefulLifecycleClient("SOLUSD")
    regressed = NOW - timedelta(seconds=1)
    clock = SequenceClock(NOW, NOW, NOW, NOW, regressed)

    result = _run(
        tmp_path,
        _plan("SOLUSD"),
        client,
        timestamp=NOW,
        clock=clock,
    )

    assert result["outcome_classification"] == (
        "manual_reconciliation_required"
    )
    assert result["blockers"] == [
        "trusted_clock_invalid_after_entry_action"
    ]
    assert result["broker_mutation_performed"] is True
    assert result["paper_submit_performed"] is True
    assert client.submit_calls == ["buy"]
    assert client.position_qty > 0
    persisted = json.loads(
        (
            tmp_path / "out" / "latest" / "lifecycle_result.json"
        ).read_bytes()
    )
    assert persisted == result


def test_invalid_success_receipt_is_never_published(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValidationError,
        match="order chronology drifted",
    ):
        _run(
            tmp_path,
            _plan("BTCUSD"),
            InvalidExitChronologyClient("BTCUSD"),
            timestamp=NOW,
        )

    latest = tmp_path / "out" / "latest"
    assert not (latest / "lifecycle_result.json").exists()
    assert not (latest / "manifest.json").exists()


def test_invalid_order_shape_success_receipt_is_never_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_public_order = operator_subject._public_order

    def drift_exit_order_shape(value: Any) -> dict[str, object]:
        payload = original_public_order(value)
        if payload.get("side") == "sell":
            payload["notional"] = "10"
            unsigned = dict(payload)
            unsigned.pop("order_fingerprint", None)
            payload["order_fingerprint"] = stable_hash(unsigned)
        return payload

    monkeypatch.setattr(
        operator_subject,
        "_public_order",
        drift_exit_order_shape,
    )

    with pytest.raises(
        ValidationError,
        match="exit request shape drifted: lookup_order_notional_mismatch",
    ):
        _run(
            tmp_path,
            _plan("BTCUSD"),
            StatefulLifecycleClient("BTCUSD"),
            timestamp=NOW,
        )

    latest = tmp_path / "out" / "latest"
    assert not (latest / "lifecycle_result.json").exists()
    assert not (latest / "manifest.json").exists()


def test_runtime_source_drift_blocks_before_client_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan("ETHUSD")
    factory_calls: list[object] = []
    monkeypatch.setattr(
        operator_subject,
        "_runtime_source_bundle_sha256",
        lambda: "0" * 64,
    )

    result = run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
        plan,
        output_root=tmp_path / "out",
        journal_path=tmp_path / "orders.sqlite3",
        safety_state_path=tmp_path / "safety.sqlite3",
        timestamp=NOW,
        clock=lambda: NOW,
        env=_env(),
        broker_client_factory=lambda config: factory_calls.append(config),
        exact_operation_authorization=exact_operation_authorization_text(plan),
        expected_paper_account_id=ACCOUNT_ID,
        paper_mutation_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert result["outcome_classification"] == "blocked_before_broker_read"
    assert result["blockers"] == ["runtime_source_bundle_mismatch"]
    assert factory_calls == []


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("NETWORK_TESTS", "yes"),
        ("ALLOW_NETWORK_TESTS", "on"),
        ("PYTEST_ADDOPTS", "-q --allow-network"),
    ),
)
def test_direct_lifecycle_rejects_all_enabled_network_test_flags(
    tmp_path: Path,
    name: str,
    value: str,
) -> None:
    plan = _plan("BTCUSD")
    factory_calls: list[object] = []
    env = {**_env(), name: value}

    result = run_crypto_tournament_v2_bounded_paper_probe_lifecycle(
        plan,
        output_root=tmp_path / "out",
        journal_path=tmp_path / "orders.sqlite3",
        safety_state_path=tmp_path / "safety.sqlite3",
        timestamp=NOW,
        clock=lambda: NOW,
        env=env,
        broker_client_factory=lambda config: factory_calls.append(config),
        exact_operation_authorization=exact_operation_authorization_text(plan),
        expected_paper_account_id=ACCOUNT_ID,
        paper_mutation_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert result["outcome_classification"] == "blocked_before_broker_read"
    assert "network_test_flag_must_remain_disabled" in result["blockers"]
    assert factory_calls == []


@pytest.mark.parametrize(
    "legacy_args",
    (
        ("--exact-operation-authorization", "secret"),
        ("--expected-paper-account-id", "account"),
        ("--as-of", NOW.isoformat()),
        ("--paper-mutation-auth",),
    ),
)
def test_lifecycle_cli_rejects_legacy_and_abbreviated_options(
    legacy_args: tuple[str, ...],
) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--plan",
                "plan.json",
                "--exact-operation-authorization-stdin",
                *legacy_args,
            ]
        )


@pytest.mark.parametrize(
    ("payload", "expected"),
    (
        (b"operator-grant\n", "operator-grant"),
        (b"a" * 4096, "a" * 4096),
    ),
)
def test_authorization_stdin_accepts_exact_bounded_utf8(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
    expected: str,
) -> None:
    monkeypatch.setattr(sys, "stdin", BinaryStdin(payload))

    assert _read_exact_authorization_stdin() == expected


@pytest.mark.parametrize(
    "payload",
    (b"", b" \r\n", b"\x00", b"\xff", b"a" * 4097),
)
def test_authorization_stdin_rejects_invalid_or_oversized_payload(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    monkeypatch.setattr(sys, "stdin", BinaryStdin(payload))

    with pytest.raises(ValidationError):
        _read_exact_authorization_stdin()


def test_canonical_plan_loader_binds_exact_source_bytes(
    tmp_path: Path,
) -> None:
    plan = _plan("ETHUSD")
    payload = canonical_json_bytes(plan)
    path = tmp_path / "lifecycle_plan.json"
    path.write_bytes(payload)

    loaded, loaded_bytes = _load_canonical_plan(path)

    assert loaded == plan
    assert loaded_bytes == payload


@pytest.mark.parametrize("variant", ("pretty", "missing_newline", "bom"))
def test_canonical_plan_loader_rejects_equivalent_noncanonical_bytes(
    tmp_path: Path,
    variant: str,
) -> None:
    plan = _plan("ETHUSD")
    canonical = canonical_json_bytes(plan)
    if variant == "pretty":
        payload = (
            json.dumps(plan, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    elif variant == "missing_newline":
        payload = canonical[:-1]
    else:
        payload = b"\xef\xbb\xbf" + canonical
    path = tmp_path / f"{variant}.json"
    path.write_bytes(payload)

    with pytest.raises(Exception, match="not canonical JSON"):
        _load_canonical_plan(path)


def test_canonical_plan_loader_rejects_duplicate_nested_keys(
    tmp_path: Path,
) -> None:
    payload = b'{"outer":{"key":1,"key":2}}\n'
    path = tmp_path / "duplicate.json"
    path.write_bytes(payload)

    with pytest.raises(Exception, match="duplicate JSON keys"):
        _load_canonical_plan(path)
