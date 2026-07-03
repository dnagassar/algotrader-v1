from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.execution.paper_autopilot_loop import paper_autopilot_client_order_id
from algotrader.execution.paper_autopilot_operator import (
    PaperAutopilotOperatorConfig,
    paper_autopilot_operator_exit_status,
    render_paper_autopilot_operator_summary,
    run_paper_autopilot_operator,
)
from algotrader.orchestration.strategy_adapter_registry import (
    SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID,
)
from algotrader.orchestration.strategy_router import SMA_TRAINING_WHEEL_STRATEGY_ID


GENERATED_AT = "2026-06-26T14:00:00+00:00"
PAPER_KEY = "paper-key-value"
PAPER_SECRET = "paper-secret-value"
EXPECTED_ACCOUNT_ID = "paper-account-id-should-not-serialize"


def test_operator_healthy_hold_noop_returns_zero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "healthy_hold_noop"
    assert summary["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert summary["autonomy_next_action"] == "continue_next_daily_cycle"
    assert summary["readiness_status"] == "no_mutation_needed_continue"
    assert summary["readiness_blockers"] == []
    assert summary["required_operator_action"] == "continue_next_daily_cycle"
    assert summary["readiness_packet_generated"] is False
    assert summary["changed_since_previous"] is False
    assert summary["hard_stop"] is False
    assert summary["attention_required"] is False
    assert "risk_on_spy_position_already_held" in summary["reason_codes"]
    assert summary["anomaly_classification"] == "healthy_hold_noop"
    assert summary["operating_mode"] == "bounded_paper_mutation"
    assert summary["pre_broker_daily_cycle_status"] == "no_refresh_required"
    assert (
        summary["pre_broker_daily_cycle_classification"]
        == "pre_broker_daily_cycle_ready"
    )
    assert summary["final_supervisor_status"] == "none"
    assert summary["broker_observed_supervisor_status"] == "none"
    assert summary["final_supervisor_classification"] == (
        "no_action_required_no_mutation"
    )
    assert summary["action_decision"] == "hold/noop"
    assert summary["spy_position_observed"] is True
    assert summary["spy_position_quantity"] == "0.05"
    assert summary["open_spy_orders_observed"] == 0
    assert summary["unexpected_non_spy_positions_count"] == 0
    assert summary["unexpected_non_spy_positions"] == []
    assert summary["vol_scaled_preview_intended_action"] == "buy"
    assert summary["paper_submit_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert summary["live_mutation_performed"] is False
    assert summary["final_operator_action"] == "continue_next_daily_cycle"
    assert paper_autopilot_operator_exit_status(result) == 0
    assert result["rollup"]["history_count"] == 1
    rendered = render_paper_autopilot_operator_summary(summary)
    assert "classification=healthy_hold_noop" in rendered
    assert "autonomy_status=healthy_continue_next_daily_cycle" in rendered
    assert "autonomy_next_action=continue_next_daily_cycle" in rendered
    assert "readiness_status=no_mutation_needed_continue" in rendered
    assert "readiness_packet_generated=false" in rendered
    assert "changed_since_previous=false" in rendered
    assert "operator_exit_code=0" in rendered
    _assert_history_artifacts(result)


def test_operator_healthy_paper_action_reconciled_returns_zero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()
    readiness_packet_path = _write_readiness_packet(
        tmp_path,
        bars_csv,
        action="buy",
        side="buy",
        notional="25.00",
        quantity="",
        spy_position_observed=False,
        spy_position_quantity="0",
    )

    result = _run_operator(
        tmp_path,
        bars_csv,
        broker,
        readiness_packet_path=readiness_packet_path,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "healthy_paper_action_reconciled"
    assert summary["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert summary["operating_mode"] == "bounded_paper_mutation"
    assert summary["final_supervisor_status"] == "action/submitted"
    assert summary["broker_observed_supervisor_status"] == "action/submitted"
    assert summary["action_decision"] == "paper_buy_allowed"
    assert summary["paper_mutation_readiness_packet_consumed"] is True
    assert summary["paper_mutation_readiness_gate_status"] == "authorized"
    assert summary["paper_mutation_readiness_status"] == "readiness_blocked_no_submit_mode"
    assert summary["paper_submit_performed"] is True
    assert summary["broker_mutation_performed"] is True
    assert summary["reconciliation_status"] == "reconciled_submit_observed"
    assert paper_autopilot_operator_exit_status(result) == 0


def test_operator_broker_state_not_observed_is_explicit_nonzero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={},
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "broker_state_not_observed"
    assert summary["autonomy_status"] == "blocked_configure_verified_paper_profile"
    assert summary["autonomy_next_action"] == "configure_verified_paper_profile_then_rerun"
    assert summary["readiness_status"] == "readiness_blocked_broker_state_not_observed"
    assert summary["broker_state_mode"] == "broker_state_not_observed"
    assert summary["blocker_status"] == "blocked/broker_state_not_observed"
    assert summary["final_supervisor_status"] == "blocked/broker_state_not_observed"
    assert summary["broker_observed_supervisor_status"] == "broker_state_not_observed"
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_live_safety_blocked_is_hard_stop_nonzero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={
            **_paper_env(),
            "APP_PROFILE": "live",
            "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
        },
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "live_safety_blocked"
    assert summary["autonomy_status"] == "hard_stop_safety_invariant"
    assert summary["blocker_status"] == "blocked/live_safety"
    assert result["rollup"]["hard_stop"] is True
    assert paper_autopilot_operator_exit_status(result) == 2


def test_operator_reconciliation_required_is_nonzero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(hide_submitted_order_from_reconciliation=True)
    readiness_packet_path = _write_readiness_packet(
        tmp_path,
        bars_csv,
        action="buy",
        side="buy",
        notional="25.00",
        quantity="",
        spy_position_observed=False,
        spy_position_quantity="0",
    )

    result = _run_operator(
        tmp_path,
        bars_csv,
        broker,
        readiness_packet_path=readiness_packet_path,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "reconciliation_required"
    assert summary["blocker_status"] == "blocked/reconciliation_required"
    assert summary["paper_submit_performed"] is True
    assert summary["broker_mutation_performed"] is True
    assert summary["reconciliation_status"] == "reconciliation_required"
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_unexpected_non_spy_position_is_nonzero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "QQQ", "qty": Decimal("1"), "market_value": "400"},)
    )

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "unexpected_position_blocked"
    assert summary["autonomy_status"] == "blocked_unexpected_non_spy_position"
    assert summary["blocker_status"] == "blocked/unexpected_non_spy_position"
    assert (
        summary["readiness_status"]
        == "readiness_blocked_unexpected_non_spy_position"
    )
    assert summary["required_operator_action"] == "operator_review_non_spy_position"
    assert summary["readiness_packet_generated"] is False
    assert summary["broker_mutation_performed"] is False
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_open_spy_order_conflict_is_nonzero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        open_orders=(
            {
                "id": "open-order-1",
                "client_order_id": "existing-spy-order",
                "symbol": "SPY",
                "side": "buy",
                "status": "accepted",
            },
        )
    )

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "open_order_conflict_blocked"
    assert summary["autonomy_status"] == "blocked_open_spy_order_present"
    assert summary["blocker_status"] == "blocked/open_order_present"
    assert summary["readiness_status"] == "readiness_blocked_open_spy_order_present"
    assert (
        summary["required_operator_action"]
        == "reconcile_existing_spy_open_order_before_submit"
    )
    assert summary["readiness_packet_generated"] is False
    assert summary["broker_mutation_performed"] is False
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_no_submit_hold_noop_when_risk_on_position(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    result = _run_operator(tmp_path, bars_csv, broker, no_submit=True)

    summary = result["operator_summary"]
    assert summary["classification"] == "healthy_hold_noop"
    assert summary["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert summary["readiness_status"] == "no_mutation_needed_continue"
    assert summary["required_operator_action"] == "continue_next_daily_cycle"
    assert summary["readiness_packet_generated"] is False
    assert summary["operating_mode"] == "visibility/no_submit"
    assert summary["no_submit_mode"] is True
    assert summary["execution_plan_action"] == "hold"
    assert summary["paper_submit_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert paper_autopilot_operator_exit_status(result) == 0


def test_operator_no_submit_hold_noop_when_risk_off_without_position(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_off")
    broker = FakeAutopilotBroker()

    result = _run_operator(tmp_path, bars_csv, broker, no_submit=True)

    summary = result["operator_summary"]
    assert summary["classification"] == "healthy_hold_noop"
    assert summary["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert summary["readiness_status"] == "no_mutation_needed_continue"
    assert summary["required_operator_action"] == "continue_next_daily_cycle"
    assert summary["readiness_packet_generated"] is False
    assert summary["operating_mode"] == "visibility/no_submit"
    assert summary["no_submit_mode"] is True
    assert summary["sma_posture"] == "risk_off"
    assert summary["spy_position_observed"] is False
    assert summary["spy_position_quantity"] == "0"
    assert summary["execution_plan_action"] == "hold"
    assert "risk_off_no_spy_position_noop" in summary["reason_codes"]
    assert summary["paper_submit_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert paper_autopilot_operator_exit_status(result) == 0


def test_operator_no_submit_buy_intent_is_visibility_only_nonzero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "mutation_would_be_required_no_submit_mode"
    assert (
        summary["autonomy_status"]
        == "paper_mutation_would_be_required_no_submit_mode"
    )
    assert (
        summary["autonomy_next_action"]
        == "review_visibility_only_intended_action_no_submit_mode"
    )
    assert summary["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert (
        summary["readiness_status"]
        != "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert summary["readiness_blockers"] == [
        "no_submit_mode",
        "paper_mutation_required",
    ]
    assert summary["required_operator_action"] == (
        "review_readiness_packet_then_run_explicit_authorized_bounded_paper_mutation_after_operator_approval"
    )
    assert summary["readiness_packet_generated"] is True
    assert summary["paper_mutation_readiness_packet"]
    assert summary["operating_mode"] == "visibility/no_submit"
    assert summary["latest_bar_date"] == "2026-08-08"
    assert summary["data_refresh_status"] == "no_refresh_required"
    assert summary["data_freshness_status"] == "accepted_data_current"
    assert summary["selected_strategy_id"] == "spy_sma_50_200_training_wheel"
    assert summary["broker_read_performed"] is True
    assert summary["broker_state_observed"] is True
    assert summary["broker_state_mode"] == "alpaca_paper_observed"
    assert summary["expected_account_matched"] is True
    assert summary["blocker_status"] == "blocked/mutation_would_be_required_no_submit_mode"
    assert summary["final_supervisor_status"] == (
        "blocked/mutation_would_be_required_no_submit_mode"
    )
    assert summary["broker_observed_supervisor_status"] == (
        "blocked/mutation_would_be_required_no_submit_mode"
    )
    assert summary["action_decision"] == "paper_buy_blocked_no_submit_mode"
    assert summary["no_submit_mode"] is True
    assert summary["execution_plan_action"] == "buy"
    assert summary["vol_scaled_preview_visible"] is True
    assert summary["vol_scaled_preview_intended_action"] == "buy"
    assert summary["vol_scaled_preview_mutation_allowed"] is False
    assert summary["vol_scaled_preview_submit_allowed"] is False
    assert (
        summary["vol_scaled_preview_non_mutation_status"]
        == "preview_only_non_mutating"
    )
    assert summary["paper_submit_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert result["rollup"]["broker_read_performed"] is True
    assert result["rollup"]["intended_mutation_action"] == "buy"
    assert result["rollup"]["mutation_would_be_required_without_no_submit"] is True
    packet = result["rollup"]["paper_mutation_readiness_packet"]
    assert packet["symbol"] == "SPY"
    assert packet["selected_strategy_id"] == "spy_sma_50_200_training_wheel"
    assert packet["strategy_adapter_mode"] == "paper_mutation"
    assert packet["no_submit_mode"] is True
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["live_mutation_performed"] is False
    assert packet["vol_scaled_preview_visible"] is True
    assert packet["vol_scaled_preview_mutation_allowed"] is False
    assert packet["vol_scaled_preview_submit_allowed"] is False
    assert (
        packet["readiness_status"]
        != "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert broker.submitted_requests == []
    assert "submit_order" not in broker.calls
    rendered = render_paper_autopilot_operator_summary(summary)
    assert "operating_mode=visibility/no_submit" in rendered
    assert "no_submit_mode=true" in rendered
    assert "latest_bar_date=2026-08-08" in rendered
    assert "data_refresh_status=no_refresh_required" in rendered
    assert "broker_read_performed=true" in rendered
    assert "broker_state_observed=true" in rendered
    assert "expected_account_matched=true" in rendered
    assert "selected_strategy_id=spy_sma_50_200_training_wheel" in rendered
    assert "execution_plan_action=buy" in rendered
    assert (
        "autonomy_status=paper_mutation_would_be_required_no_submit_mode"
        in rendered
    )
    assert "autonomy_next_action=review_visibility_only_intended_action_no_submit_mode" in rendered
    assert "readiness_status=readiness_blocked_no_submit_mode" in rendered
    assert "readiness_blockers=no_submit_mode,paper_mutation_required" in rendered
    assert "readiness_packet_generated=true" in rendered
    assert "broker_mutation_performed=false" in rendered
    assert "paper_submit_performed=false" in rendered
    assert "live_mutation_performed=false" in rendered
    assert "vol_scaled_preview_visible=true" in rendered
    assert "vol_scaled_preview_intended_action=buy" in rendered
    assert "vol_scaled_preview_mutation_allowed=false" in rendered
    assert "vol_scaled_preview_submit_allowed=false" in rendered
    assert "vol_scaled_preview_non_mutation_status=preview_only_non_mutating" in rendered
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_no_submit_sell_intent_is_visibility_only_nonzero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_off")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.04"), "market_value": "24"},)
    )

    result = _run_operator(tmp_path, bars_csv, broker, no_submit=True)

    summary = result["operator_summary"]
    assert summary["classification"] == "mutation_would_be_required_no_submit_mode"
    assert (
        summary["autonomy_status"]
        == "paper_mutation_would_be_required_no_submit_mode"
    )
    assert summary["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert (
        summary["readiness_status"]
        != "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert summary["readiness_blockers"] == [
        "no_submit_mode",
        "paper_mutation_required",
    ]
    assert summary["required_operator_action"] == (
        "review_readiness_packet_then_run_explicit_authorized_bounded_paper_mutation_after_operator_approval"
    )
    assert summary["readiness_packet_generated"] is True
    assert summary["paper_mutation_readiness_packet"]
    assert summary["operating_mode"] == "visibility/no_submit"
    assert summary["no_submit_mode"] is True
    assert summary["sma_posture"] == "risk_off"
    assert summary["selected_strategy_id"] == "spy_sma_50_200_training_wheel"
    assert summary["broker_state_observed"] is True
    assert summary["spy_position_observed"] is True
    assert summary["spy_position_quantity"] == "0.04"
    assert summary["execution_plan_action"] == "sell_close"
    assert summary["action_decision"] == "paper_sell_close_blocked_no_submit_mode"
    assert summary["vol_scaled_preview_mutation_allowed"] is False
    assert summary["vol_scaled_preview_submit_allowed"] is False
    assert summary["paper_submit_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert summary["live_mutation_performed"] is False

    packet = result["rollup"]["paper_mutation_readiness_packet"]
    assert packet["symbol"] == "SPY"
    assert packet["selected_strategy_id"] == "spy_sma_50_200_training_wheel"
    assert packet["strategy_adapter_mode"] == "paper_mutation"
    assert packet["execution_plan_action"] == "sell_close"
    assert packet["intended_mutation_action"] == "sell_close"
    assert packet["side"] == "sell"
    assert packet["quantity"] == "0.04"
    assert packet["notional"] == ""
    assert packet["no_submit_mode"] is True
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["live_mutation_performed"] is False
    assert packet["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert (
        packet["readiness_status"]
        != "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert packet["vol_scaled_preview_mutation_allowed"] is False
    assert packet["vol_scaled_preview_submit_allowed"] is False
    assert broker.submitted_requests == []
    assert "submit_order" not in broker.calls
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_missing_latest_status_artifact_is_nonzero(tmp_path: Path) -> None:
    def no_status_loop(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return {"run_id": "loop-returned-without-status"}

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(
            output_root=tmp_path / "out",
            bars_csv=tmp_path / "unused.csv",
        ),
        loop_runner=no_status_loop,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "stale_or_missing_status_artifact"
    assert summary["autonomy_status"] == "blocked_refresh_or_validate_daily_bars"
    assert summary["run_id"] == ""
    assert paper_autopilot_operator_exit_status(result) == 1


class FakeAutopilotBroker:
    def __init__(
        self,
        *,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        recent_orders: tuple[dict[str, object], ...] = (),
        hide_submitted_order_from_reconciliation: bool = False,
    ) -> None:
        self.positions = positions
        self.open_orders = list(open_orders)
        self.recent_orders = list(recent_orders)
        self.hide_submitted_order_from_reconciliation = (
            hide_submitted_order_from_reconciliation
        )
        self.submitted_requests = []
        self.calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return {
            "account_id": EXPECTED_ACCOUNT_ID,
            "status": "ACTIVE",
            "tradable": True,
            "cash": Decimal("100000"),
            "buying_power": Decimal("100000"),
            "currency": "USD",
        }

    def get_positions(self) -> tuple[dict[str, object], ...]:
        self.calls.append("get_positions")
        return self.positions

    def get_orders(self, query) -> tuple[dict[str, object], ...]:  # noqa: ANN001
        self.calls.append(f"get_orders:{query.status_filter}:{query.symbol_filter}")
        rows = list(self.open_orders if query.status_filter == "open" else self.recent_orders)
        if query.status_filter == "all":
            rows.extend(self.open_orders)
        if query.symbol_filter:
            rows = [
                row
                for row in rows
                if str(row.get("symbol", "")).upper() == query.symbol_filter
            ]
        return tuple(rows)

    def submit_order(self, request) -> dict[str, object]:  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        order = {
            "id": "paper-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "status": "accepted",
            "type": request.order_type,
            "time_in_force": request.time_in_force,
            "notional": request.notional,
            "qty": request.qty,
            "filled_qty": Decimal("0"),
        }
        if not self.hide_submitted_order_from_reconciliation:
            self.recent_orders.append(order)
        return order


def _run_operator(
    tmp_path: Path,
    bars_csv: Path,
    broker: FakeAutopilotBroker,
    *,
    no_submit: bool = False,
    readiness_packet_path: Path | None = None,
) -> dict[str, object]:
    return run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=no_submit,
            readiness_packet_path=readiness_packet_path,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )


def _write_readiness_packet(
    tmp_path: Path,
    bars_csv: Path,
    *,
    action: str,
    side: str,
    notional: str,
    quantity: str,
    spy_position_observed: bool,
    spy_position_quantity: str,
) -> Path:
    path = tmp_path / f"readiness_packet_{action}.json"
    as_of_date = "2026-08-08"
    data_sha256 = hashlib.sha256(bars_csv.read_bytes()).hexdigest()
    client_order_id = paper_autopilot_client_order_id(
        action=action,
        symbol="SPY",
        as_of_date=as_of_date,
        data_sha256=data_sha256,
    )
    packet = {
        "paper_mutation_readiness_packet_schema_version": (
            "v4_7_paper_mutation_readiness_packet_v1"
        ),
        "generated_at": GENERATED_AT,
        "source_visibility_run_id": "visibility-run-1",
        "source_autonomy_status": "paper_mutation_would_be_required_no_submit_mode",
        "source_execution_plan_id": "visibility-plan-1",
        "source_client_order_id": client_order_id,
        "symbol": "SPY",
        "selected_strategy_id": SMA_TRAINING_WHEEL_STRATEGY_ID,
        "strategy_adapter_id": SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID,
        "strategy_adapter_mode": "paper_mutation",
        "strategy_route_action": action,
        "execution_plan_action": action,
        "intended_mutation_action": action,
        "side": side,
        "notional": notional,
        "quantity": quantity,
        "notional_cap": "25.00",
        "no_submit_mode": True,
        "broker_read_performed": True,
        "broker_state_observed": True,
        "broker_state_mode": "alpaca_paper_observed",
        "expected_account_matched": True,
        "spy_position_observed": spy_position_observed,
        "spy_position_quantity": spy_position_quantity,
        "open_spy_orders_observed": 0,
        "unexpected_non_spy_positions": [],
        "data_freshness_status": "accepted_data_current",
        "latest_bar_date": as_of_date,
        "vol_scaled_preview_visible": True,
        "vol_scaled_preview_intended_action": "buy",
        "vol_scaled_preview_mutation_allowed": False,
        "vol_scaled_preview_submit_allowed": False,
        "vol_scaled_preview_non_mutation_status": "preview_only_non_mutating",
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "readiness_status": "readiness_blocked_no_submit_mode",
        "readiness_blockers": ["no_submit_mode", "paper_mutation_required"],
        "required_operator_action": (
            "review_readiness_packet_then_run_explicit_authorized_bounded_paper_mutation_after_operator_approval"
        ),
        "safety_labels": [
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
            "paper_autopilot_unlocked",
            "broker_state_observed",
        ],
    }
    path.write_text(
        json.dumps(packet, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": PAPER_KEY,
        "APCA_API_SECRET_KEY": PAPER_SECRET,
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": EXPECTED_ACCOUNT_ID,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }


def _factory(fake_broker: FakeAutopilotBroker):
    def build(_config):  # noqa: ANN001
        return fake_broker

    return build


def _forbidden_factory(_config):  # noqa: ANN001
    raise AssertionError("broker factory must not be called")


def _fake_daily_lab(config):  # noqa: ANN001
    return {
        "preview_decision": "fake_daily_cycle_ran",
        "blocker_status": "none",
        "next_operator_action": "none",
        "latest_bar_date": "2026-08-08",
        "data_freshness_status": "accepted_data_current",
        "data_refresh_status": "no_refresh_required",
        "expected_latest_bar_date": "2026-08-08",
        "data_freshness_plan_path": str(
            Path(config.output_root) / "data_freshness_plan.json"
        ),
        "data_refresh_bridge_path": str(
            Path(config.output_root) / "data_refresh_bridge.json"
        ),
        "data_refresh_dry_run_path": str(
            Path(config.output_root) / "data_refresh_dry_run.json"
        ),
        "output_root": str(config.output_root),
    }


def _write_bars(tmp_path: Path, *, posture: str) -> Path:
    path = tmp_path / f"{posture}.csv"
    start = date(2026, 1, 1)
    rows = ["date,symbol,open,high,low,close,adjusted_close,volume"]
    for index in range(220):
        current = start + timedelta(days=index)
        close = Decimal("100") + Decimal(index)
        if posture == "risk_off":
            close = Decimal("500") - Decimal(index)
        rows.append(
            f"{current.isoformat()},SPY,{close},{close},{close},{close},{close},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _assert_history_artifacts(result: dict[str, object]) -> None:
    artifact_paths = result["rollup"]["artifact_paths"]
    assert Path(artifact_paths["operating_history"]).is_file()
    assert Path(artifact_paths["daily_autonomy_ledger"]).is_file()
    assert Path(artifact_paths["latest_daily_autonomy"]).is_file()
    assert Path(artifact_paths["daily_autonomy_summary"]).is_file()
    assert Path(artifact_paths["latest_rollup"]).is_file()
    assert Path(artifact_paths["operating_summary"]).is_file()
    latest_rollup = json.loads(
        Path(artifact_paths["latest_rollup"]).read_text(encoding="utf-8")
    )
    assert latest_rollup["classification"] == result["operator_summary"]["classification"]
