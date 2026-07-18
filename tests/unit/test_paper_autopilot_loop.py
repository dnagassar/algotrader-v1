from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pytest

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.errors import ValidationError
from algotrader.execution.paper_autopilot_loop import (
    PaperAutopilotLoopConfig,
    paper_autopilot_client_order_id,
    run_paper_autopilot_loop,
)
from algotrader.orchestration.strategy_adapter_registry import (
    SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID,
    StrategyAdapterRegistration,
)
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
    SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
    StrategySignal,
)


GENERATED_AT = "2026-06-26T14:00:00+00:00"
PAPER_KEY = "paper-key-value"
PAPER_SECRET = "paper-secret-value"
EXPECTED_ACCOUNT_ID = "paper-account-id-should-not-serialize"


def test_paper_autopilot_noop_when_already_positioned_risk_on(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    record = _run(tmp_path, bars_csv, broker)

    assert record["sma_posture"] == "risk_on"
    assert record["strategy_route_status"] == "action_routed"
    assert record["selected_strategy_id"] == "spy_sma_50_200_training_wheel"
    assert record["strategy_route_paper_mutation_allowed"] is True
    assert (
        record["strategy_route_receipt"]["selected_signal_id"]
        == "spy_sma_50_200_training_wheel"
    )
    assert record["strategy_adapter_resolution_status"] == "resolved"
    assert record["strategy_adapter_id"] == "spy_sma_50_200_paper_mutation_adapter"
    assert record["strategy_adapter_paper_mutation_allowed"] is True
    assert record["strategy_preview_states"][0]["strategy_id"] == (
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    )
    assert record["strategy_preview_states"][0]["promotion_status"] == (
        "paper_preview_candidate"
    )
    assert record["strategy_preview_adapter_resolutions"][0]["adapter_mode"] == (
        "preview_only"
    )
    assert (
        record["strategy_preview_adapter_resolutions"][0][
            "paper_mutation_allowed"
        ]
        is False
    )
    assert record["strategy_action_disagreements"] == [
        {
            "strategy_id": SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
            "promotion_status": "paper_preview_candidate",
            "preview_intended_action": "buy",
            "paper_execution_plan_action": "hold",
            "selected_strategy_id": SMA_TRAINING_WHEEL_STRATEGY_ID,
            "selected_strategy_intended_action": "buy",
            "paper_mutation_allowed": False,
            "reason": "preview_candidate_disagrees_with_paper_execution_plan",
        }
    ]
    assert record["preview_action_decision"] == "hold/noop"
    assert record["execution_plan_status"] == "no_action_required"
    assert record["blocker_status"] == "none"
    assert record["operating_mode"] == "bounded_paper_mutation"
    assert record["pre_broker_daily_cycle_status"] == "no_refresh_required"
    assert (
        record["pre_broker_daily_cycle_classification"]
        == "pre_broker_daily_cycle_ready"
    )
    assert record["final_supervisor_status"] == "none"
    assert record["broker_observed_supervisor_status"] == "none"
    assert record["final_classification"] == "no_action_required_no_mutation"
    assert record["final_supervisor_classification"] == (
        "no_action_required_no_mutation"
    )
    assert record["final_operator_action"] == "continue_next_daily_cycle"
    assert (
        record["daily_cycle"]["daily_cycle_data_freshness_status"]
        == "accepted_data_current"
    )
    assert (
        record["daily_cycle"]["daily_cycle_data_refresh_status"]
        == "no_refresh_required"
    )
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["mutation_performed"] is False
    assert broker.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
    ]
    _assert_artifacts(record)
    _assert_no_sensitive_values(record)


def test_paper_autopilot_blocks_buy_without_readiness_packet(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    record = _run(tmp_path, bars_csv, broker)

    assert record["preview_action_decision"] == "blocked"
    assert record["blocker_status"] == "blocked/paper_mutation_readiness_packet_missing"
    assert record["paper_mutation_readiness_gate_status"] == "blocked"
    assert record["paper_mutation_readiness_packet_consumed"] is False
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert "submit_order" not in broker.calls
    _assert_no_sensitive_values(record)


def test_paper_autopilot_buy_when_risk_on_without_position_or_order(
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

    record = _run(
        tmp_path,
        bars_csv,
        broker,
        readiness_packet_path=readiness_packet_path,
    )

    assert record["preview_action_decision"] == "paper_buy_allowed"
    assert record["blocker_status"] == "blocked/reconciliation_required"
    assert record["paper_mutation_readiness_gate_status"] == "authorized"
    assert record["paper_mutation_readiness_packet_consumed"] is True
    assert record["paper_mutation_readiness_status"] == "readiness_blocked_no_submit_mode"
    assert (
        record["paper_mutation_source_autonomy_status"]
        == "paper_mutation_would_be_required_no_submit_mode"
    )
    assert record["paper_submit_authorized"] is True
    assert record["paper_submit_performed"] is True
    assert record["broker_mutation_performed"] is True
    assert record["canonical_risk_allowed"] is True
    assert record["canonical_policy_accepted"] is True
    assert record["canonical_runtime_plan"]["decision_status"] == "accepted"
    assert record["live_mutation_performed"] is False
    assert record["reconciliation_status"] == (
        "reconciled_nonterminal_order_observed"
    )
    assert record["reconciliation"]["terminal_order_observed"] is False
    assert record["final_classification"] == (
        "paper_submit_nonterminal_reconciliation_required"
    )
    assert record["order_id"] == "paper-order-1"
    assert record["client_order_id"].startswith("pa-v207-spy-buy-")
    mutation_receipt = json.loads(
        Path(record["artifact_paths"]["mutation_receipt"]).read_text(encoding="utf-8")
    )
    assert mutation_receipt["submit_attempted"] is True
    assert mutation_receipt["paper_submit_performed"] is True
    assert mutation_receipt["broker_mutation_performed"] is True
    assert mutation_receipt["live_mutation_performed"] is False
    assert mutation_receipt["paper_mutation_readiness_gate_status"] == "authorized"
    assert mutation_receipt["paper_mutation_readiness_packet_consumed"] is True
    assert mutation_receipt["order_id"] == "paper-order-1"
    assert mutation_receipt["order_status"] == "accepted"
    assert mutation_receipt["reconciliation_status"] == (
        "reconciled_nonterminal_order_observed"
    )
    assert mutation_receipt["ambiguity_status"] == "not_ambiguous"
    request = broker.submitted_requests[0]
    assert request.symbol == "SPY"
    assert request.side == "buy"
    assert request.notional == Decimal("25.00")
    assert request.qty is None
    assert request.client_order_id.startswith("pa-v207-spy-buy-")
    _assert_no_sensitive_values(record)


def test_paper_autopilot_blocks_stale_readiness_packet(tmp_path: Path) -> None:
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
    packet = json.loads(readiness_packet_path.read_text(encoding="utf-8"))
    packet["latest_bar_date"] = "2026-08-07"
    readiness_packet_path.write_text(
        json.dumps(packet, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    record = _run(
        tmp_path,
        bars_csv,
        broker,
        readiness_packet_path=readiness_packet_path,
    )

    assert record["blocker_status"] == "blocked/paper_mutation_readiness_packet_stale"
    assert record["paper_mutation_readiness_gate_status"] == "blocked"
    assert record["paper_mutation_readiness_packet_consumed"] is True
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert "submit_order" not in broker.calls


def test_paper_autopilot_sell_close_when_risk_off_with_spy_position(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_off")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.04"), "market_value": "24"},)
    )
    readiness_packet_path = _write_readiness_packet(
        tmp_path,
        bars_csv,
        action="sell_close",
        side="sell",
        notional="",
        quantity="0.04",
        spy_position_observed=True,
        spy_position_quantity="0.04",
    )

    record = _run(
        tmp_path,
        bars_csv,
        broker,
        readiness_packet_path=readiness_packet_path,
    )

    assert record["sma_posture"] == "risk_off"
    assert record["preview_action_decision"] == "paper_sell_close_allowed"
    assert record["paper_mutation_readiness_gate_status"] == "authorized"
    assert record["paper_mutation_readiness_packet_consumed"] is True
    assert record["paper_submit_authorized"] is True
    assert record["paper_submit_performed"] is True
    request = broker.submitted_requests[0]
    assert request.side == "sell"
    assert request.qty == Decimal("0.04")
    assert request.notional is None
    assert request.client_order_id.startswith("pa-v207-spy-close-")
    _assert_no_sensitive_values(record)


def test_paper_autopilot_no_submit_blocks_buy_visibility_only(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )
    receipt = _latest_jsonl(record["artifact_paths"]["supervisor_receipt"])
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )

    assert record["no_submit_mode"] is True
    assert record["operating_mode"] == "visibility/no_submit"
    assert record["data_refresh_status"] == "no_refresh_required"
    assert record["data_freshness_status"] == "accepted_data_current"
    assert record["latest_bar_date"] == "2026-08-08"
    assert record["broker_read_performed"] is True
    assert record["broker_state_observed"] is True
    assert record["broker_state_mode"] == "alpaca_paper_observed"
    assert record["expected_account_matched"] is True
    assert record["selected_strategy_id"] == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert record["strategy_route_action"] == "buy"
    assert record["spy_position_observed"] is False
    assert record["spy_position_quantity"] == "0"
    assert record["open_spy_orders_observed"] == 0
    assert record["unexpected_non_spy_positions_observed"] == 0
    assert record["execution_plan_action"] == "buy"
    assert record["intended_mutation_action"] == "buy"
    assert record["mutation_would_be_required_without_no_submit"] is True
    assert record["execution_plan"]["submit_allowed"] is False
    assert record["execution_plan"]["paper_submit_authorized"] is False
    assert record["execution_plan"]["blockers"] == [
        "mutation_would_be_required_no_submit_mode"
    ]
    assert record["blocker_status"] == "blocked/mutation_would_be_required_no_submit_mode"
    assert record["final_supervisor_status"] == (
        "blocked/mutation_would_be_required_no_submit_mode"
    )
    assert record["broker_observed_supervisor_status"] == (
        "blocked/mutation_would_be_required_no_submit_mode"
    )
    assert record["final_classification"] == "mutation_would_be_required_no_submit_mode"
    assert record["final_supervisor_classification"] == (
        "mutation_would_be_required_no_submit_mode"
    )
    assert record["final_operator_action"] == (
        "review_visibility_only_intended_action_no_submit_mode"
    )
    assert record["preview_action_decision"] == "paper_buy_blocked_no_submit_mode"
    assert record["action_result"]["mutation_status"] == "blocked_no_submit_mode"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["mutation_performed"] is False
    assert record["live_mutation_performed"] is False
    assert record["vol_scaled_preview_visible"] is True
    assert record["vol_scaled_preview_intended_action"] == "buy"
    assert record["vol_scaled_preview_mutation_allowed"] is False
    assert record["vol_scaled_preview_submit_allowed"] is False
    assert (
        record["vol_scaled_preview_non_mutation_status"]
        == "preview_only_non_mutating"
    )
    assert record["reconciliation_status"] == "not_required_no_broker_mutation"
    assert broker.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
    ]
    assert broker.submitted_requests == []
    assert "submit_order" not in broker.calls

    assert receipt["no_submit_mode"] is True
    assert receipt["operating_mode"] == "visibility/no_submit"
    assert receipt["data_refresh_status"] == "no_refresh_required"
    assert receipt["data_freshness_status"] == "accepted_data_current"
    assert receipt["latest_bar_date"] == "2026-08-08"
    assert receipt["broker_read_performed"] is True
    assert receipt["broker_state_observed"] is True
    assert receipt["broker_state_mode"] == "alpaca_paper_observed"
    assert receipt["expected_account_matched"] is True
    assert receipt["selected_strategy_id"] == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert receipt["strategy_route_action"] == "buy"
    assert receipt["spy_position_quantity"] == "0"
    assert receipt["execution_plan_action"] == "buy"
    assert receipt["intended_mutation_action"] == "buy"
    assert receipt["paper_submit_authorized"] is False
    assert receipt["broker_mutation_performed"] is False
    assert receipt["paper_submit_performed"] is False
    assert receipt["live_mutation_performed"] is False
    assert receipt["final_supervisor_status"] == (
        "blocked/mutation_would_be_required_no_submit_mode"
    )
    assert receipt["broker_observed_supervisor_status"] == (
        "blocked/mutation_would_be_required_no_submit_mode"
    )
    assert receipt["final_classification"] == "mutation_would_be_required_no_submit_mode"
    assert receipt["final_supervisor_classification"] == (
        "mutation_would_be_required_no_submit_mode"
    )
    assert receipt["final_operator_action"] == (
        "review_visibility_only_intended_action_no_submit_mode"
    )
    assert receipt["preview_action_decision"] == "paper_buy_blocked_no_submit_mode"
    assert receipt["vol_scaled_trend_signal"]["strategy_id"] == (
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    )
    assert receipt["vol_scaled_trend_signal"]["submit_allowed"] is False
    assert receipt["vol_scaled_preview"]["strategy_id"] == (
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    )
    assert receipt["vol_scaled_preview"]["visible"] is True
    assert receipt["vol_scaled_preview_visible"] is True
    assert receipt["vol_scaled_preview_intended_action"] == "buy"
    assert receipt["vol_scaled_preview_mutation_allowed"] is False
    assert receipt["vol_scaled_preview_submit_allowed"] is False
    assert (
        receipt["vol_scaled_preview_non_mutation_status"]
        == "preview_only_non_mutating"
    )
    assert receipt["strategy_preview_states"][0]["strategy_id"] == (
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    )
    assert receipt["strategy_preview_states"][0]["promotion_status"] == (
        "paper_preview_candidate"
    )
    assert receipt["strategy_preview_adapter_resolutions"][0]["adapter_mode"] == (
        "preview_only"
    )
    assert (
        receipt["strategy_preview_adapter_resolutions"][0]["paper_mutation_allowed"]
        is False
    )
    assert receipt["strategy_preview_adapter_resolutions"][0]["mutation_allowed"] is False
    assert rollup["classification"] == "mutation_would_be_required_no_submit_mode"
    assert (
        rollup["autonomy_status"]
        == "paper_mutation_would_be_required_no_submit_mode"
    )
    assert rollup["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert rollup["readiness_blockers"] == [
        "no_submit_mode",
        "paper_mutation_required",
    ]
    assert rollup["readiness_packet_generated"] is True
    packet_path = Path(rollup["artifact_paths"]["paper_mutation_readiness_packet"])
    assert packet_path.is_file()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["source_visibility_run_id"] == record["run_id"]
    assert (
        packet["source_autonomy_status"]
        == "paper_mutation_would_be_required_no_submit_mode"
    )
    assert packet["source_execution_plan_id"] == record["execution_plan"][
        "execution_plan_id"
    ]
    assert packet["source_client_order_id"] == record["execution_plan"][
        "client_order_id"
    ]
    assert packet["symbol"] == "SPY"
    assert packet["selected_strategy_id"] == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert packet["strategy_adapter_id"] == "spy_sma_50_200_paper_mutation_adapter"
    assert packet["strategy_adapter_mode"] == "paper_mutation"
    assert packet["strategy_route_action"] == "buy"
    assert packet["execution_plan_action"] == "buy"
    assert packet["intended_mutation_action"] == "buy"
    assert packet["side"] == "buy"
    assert packet["notional"] == "25.00"
    assert packet["quantity"] == ""
    assert packet["notional_cap"] == "25.00"
    assert packet["no_submit_mode"] is True
    assert packet["broker_read_performed"] is True
    assert packet["broker_state_observed"] is True
    assert packet["broker_state_mode"] == "alpaca_paper_observed"
    assert packet["expected_account_matched"] is True
    assert packet["spy_position_observed"] is False
    assert packet["spy_position_quantity"] == "0"
    assert packet["open_spy_orders_observed"] == 0
    assert packet["unexpected_non_spy_positions"] == []
    assert packet["data_freshness_status"] == "accepted_data_current"
    assert packet["latest_bar_date"] == "2026-08-08"
    assert packet["vol_scaled_preview_visible"] is True
    assert packet["vol_scaled_preview_intended_action"] == "buy"
    assert packet["vol_scaled_preview_mutation_allowed"] is False
    assert packet["vol_scaled_preview_submit_allowed"] is False
    assert (
        packet["vol_scaled_preview_non_mutation_status"]
        == "preview_only_non_mutating"
    )
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["live_mutation_performed"] is False
    assert packet["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert (
        packet["readiness_status"]
        != "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert rollup["no_submit_mode"] is True
    assert rollup["operating_mode"] == "visibility/no_submit"
    assert rollup["data_refresh_status"] == "no_refresh_required"
    assert rollup["data_freshness_status"] == "accepted_data_current"
    assert rollup["latest_bar_date"] == "2026-08-08"
    assert rollup["broker_read_performed"] is True
    assert rollup["broker_state_observed"] is True
    assert rollup["expected_account_matched"] is True
    assert rollup["selected_strategy_id"] == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert rollup["execution_plan_action"] == "buy"
    assert rollup["broker_mutation_performed"] is False
    assert rollup["vol_scaled_preview_visible"] is True
    assert rollup["vol_scaled_preview_intended_action"] == "buy"
    assert rollup["vol_scaled_preview_mutation_allowed"] is False
    assert rollup["vol_scaled_preview_submit_allowed"] is False
    assert (
        rollup["vol_scaled_preview_non_mutation_status"]
        == "preview_only_non_mutating"
    )
    _assert_no_sensitive_values(record)


def test_paper_autopilot_no_submit_blocks_sell_visibility_only(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_off")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.04"), "market_value": "24"},)
    )

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )
    receipt = _latest_jsonl(record["artifact_paths"]["supervisor_receipt"])
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )
    packet = json.loads(
        Path(rollup["artifact_paths"]["paper_mutation_readiness_packet"]).read_text(
            encoding="utf-8"
        )
    )

    assert record["sma_posture"] == "risk_off"
    assert record["no_submit_mode"] is True
    assert record["operating_mode"] == "visibility/no_submit"
    assert record["selected_strategy_id"] == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert record["strategy_adapter_mode"] == "paper_mutation"
    assert record["strategy_route_action"] == "sell_close"
    assert record["spy_position_observed"] is True
    assert record["spy_position_quantity"] == "0.04"
    assert record["execution_plan_action"] == "sell_close"
    assert record["intended_mutation_action"] == "sell_close"
    assert record["mutation_would_be_required_without_no_submit"] is True
    assert record["execution_plan"]["submit_allowed"] is False
    assert record["execution_plan"]["paper_submit_authorized"] is False
    assert record["execution_plan"]["blockers"] == [
        "mutation_would_be_required_no_submit_mode"
    ]
    assert record["blocker_status"] == "blocked/mutation_would_be_required_no_submit_mode"
    assert record["preview_action_decision"] == "paper_sell_close_blocked_no_submit_mode"
    assert record["action_result"]["mutation_status"] == "blocked_no_submit_mode"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["live_mutation_performed"] is False
    assert record["vol_scaled_preview_mutation_allowed"] is False
    assert record["vol_scaled_preview_submit_allowed"] is False
    assert broker.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
    ]
    assert broker.submitted_requests == []
    assert "submit_order" not in broker.calls

    assert receipt["execution_plan_action"] == "sell_close"
    assert receipt["intended_mutation_action"] == "sell_close"
    assert receipt["paper_submit_authorized"] is False
    assert receipt["broker_mutation_performed"] is False
    assert receipt["paper_submit_performed"] is False
    assert receipt["live_mutation_performed"] is False
    assert receipt["vol_scaled_preview_mutation_allowed"] is False
    assert receipt["vol_scaled_preview_submit_allowed"] is False
    assert rollup["readiness_status"] == "readiness_blocked_no_submit_mode"
    assert (
        rollup["required_operator_action"]
        == "review_readiness_packet_then_run_explicit_authorized_bounded_paper_mutation_after_operator_approval"
    )
    assert rollup["readiness_packet_generated"] is True
    assert (
        rollup["readiness_status"]
        != "readiness_ready_for_explicit_bounded_paper_authorized_run"
    )
    assert packet["symbol"] == "SPY"
    assert packet["selected_strategy_id"] == SMA_TRAINING_WHEEL_STRATEGY_ID
    assert packet["strategy_adapter_mode"] == "paper_mutation"
    assert packet["strategy_route_action"] == "sell_close"
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
    assert packet["required_operator_action"] == (
        "review_readiness_packet_then_run_explicit_authorized_bounded_paper_mutation_after_operator_approval"
    )
    assert packet["vol_scaled_preview_mutation_allowed"] is False
    assert packet["vol_scaled_preview_submit_allowed"] is False
    _assert_no_sensitive_values(record)


def test_paper_autopilot_no_submit_hold_remains_noop(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )

    assert record["no_submit_mode"] is True
    assert record["operating_mode"] == "visibility/no_submit"
    assert record["execution_plan_action"] == "hold"
    assert record["intended_mutation_action"] == ""
    assert record["mutation_would_be_required_without_no_submit"] is False
    assert record["preview_action_decision"] == "hold/noop"
    assert record["blocker_status"] == "none"
    assert record["final_classification"] == "no_action_required_no_mutation"
    assert record["blockers"] == []
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert rollup["readiness_status"] == "no_mutation_needed_continue"
    assert rollup["required_operator_action"] == "continue_next_daily_cycle"
    assert rollup["readiness_packet_generated"] is False


def test_paper_autopilot_no_submit_risk_off_without_position_remains_noop(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_off")
    broker = FakeAutopilotBroker()

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )

    assert record["sma_posture"] == "risk_off"
    assert record["no_submit_mode"] is True
    assert record["operating_mode"] == "visibility/no_submit"
    assert record["spy_position_observed"] is False
    assert record["spy_position_quantity"] == "0"
    assert record["execution_plan_action"] == "hold"
    assert record["intended_mutation_action"] == ""
    assert record["mutation_would_be_required_without_no_submit"] is False
    assert record["preview_action_decision"] == "hold/noop"
    assert record["blocker_status"] == "none"
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert rollup["readiness_status"] == "no_mutation_needed_continue"
    assert rollup["required_operator_action"] == "continue_next_daily_cycle"
    assert rollup["readiness_packet_generated"] is False


def test_paper_autopilot_labels_pre_broker_daily_cycle_context(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab_pre_broker_not_observed,
        timestamp=GENERATED_AT,
    )
    receipt = _latest_jsonl(record["artifact_paths"]["supervisor_receipt"])
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )

    assert record["daily_cycle"]["daily_cycle_blocker_status"] == (
        "blocked/broker_state_not_observed"
    )
    assert record["pre_broker_daily_cycle_status"] == (
        "blocked/broker_state_not_observed"
    )
    assert record["pre_broker_daily_cycle_classification"] == (
        "pre_broker_broker_state_not_observed_context"
    )
    assert record["broker_state_observed"] is True
    assert record["blocker_status"] == "none"
    assert record["final_supervisor_status"] == "none"
    assert record["broker_observed_supervisor_status"] == "none"
    assert record["final_supervisor_classification"] == (
        "no_action_required_no_mutation"
    )
    assert record["final_operator_action"] == "continue_next_daily_cycle"
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert receipt["pre_broker_daily_cycle_status"] == (
        "blocked/broker_state_not_observed"
    )
    assert receipt["final_supervisor_status"] == "none"
    assert receipt["broker_observed_supervisor_status"] == "none"
    assert rollup["pre_broker_daily_cycle_status"] == (
        "blocked/broker_state_not_observed"
    )
    assert rollup["classification"] == "healthy_hold_noop"
    assert rollup["final_supervisor_classification"] == (
        "no_action_required_no_mutation"
    )


def test_paper_autopilot_no_submit_does_not_mask_stale_data(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab_stale,
        timestamp=GENERATED_AT,
    )

    assert record["no_submit_mode"] is True
    assert record["operating_mode"] == "visibility/no_submit"
    assert record["execution_plan_action"] == "buy"
    assert record["intended_mutation_action"] == "buy"
    assert record["mutation_would_be_required_without_no_submit"] is False
    assert record["blocker_status"] == "blocked/stale_data_preview_only"
    assert record["final_classification"] == "blocked_stale_data_preview_only"
    assert record["blockers"] == [
        "stale_data_preview_only",
        "canonical_risk_rejected_market_data_stale",
    ]
    assert record["action_result"]["mutation_status"] == (
        "blocked_canonical_plan_not_accepted"
    )
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []


def test_paper_autopilot_operator_pause_blocks_canonical_plan(
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

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            readiness_packet_path=readiness_packet_path,
            operator_paused=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    assert record["operator_paused"] is True
    assert record["canonical_risk_allowed"] is False
    assert record["canonical_policy_accepted"] is False
    assert record["canonical_runtime_plan"]["decision_status"] == (
        "blocked_before_risk"
    )
    assert record["blocker_status"] == "blocked/operator_paused"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert broker.submitted_requests == []
    assert broker.calls == []


def test_paper_autopilot_blocks_when_open_spy_order_present(tmp_path: Path) -> None:
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

    record = _run(tmp_path, bars_csv, broker)
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )

    assert record["blocker_status"] == "blocked/open_order_present"
    assert record["paper_submit_authorized"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert rollup["readiness_status"] == "readiness_blocked_open_spy_order_present"
    assert (
        rollup["required_operator_action"]
        == "reconcile_existing_spy_open_order_before_submit"
    )
    assert rollup["readiness_packet_generated"] is False


def test_paper_autopilot_blocks_unexpected_non_spy_position(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "QQQ", "qty": Decimal("1"), "market_value": "400"},)
    )

    record = _run(tmp_path, bars_csv, broker)
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )

    assert record["blocker_status"] == "blocked/unexpected_non_spy_position"
    assert record["paper_submit_authorized"] is False
    assert broker.submitted_requests == []
    assert (
        rollup["readiness_status"]
        == "readiness_blocked_unexpected_non_spy_position"
    )
    assert rollup["required_operator_action"] == "operator_review_non_spy_position"
    assert rollup["readiness_packet_generated"] is False


def test_paper_autopilot_blocks_when_broker_state_not_observed(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={},
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )

    assert record["blocker_status"] == "blocked/broker_state_not_observed"
    assert record["broker_state_observed"] is False
    assert "broker_state_not_observed" in record["safety_labels"]
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert rollup["readiness_status"] == "readiness_blocked_broker_state_not_observed"
    assert (
        rollup["required_operator_action"]
        == "configure_verified_paper_profile_then_rerun"
    )
    assert rollup["readiness_packet_generated"] is False


def test_paper_autopilot_blocks_live_safety_before_broker_build(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={
            **_paper_env(),
            "APP_PROFILE": "live",
            "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
        },
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    assert record["blocker_status"] == "blocked/live_safety"
    assert record["preflight"]["live_endpoint_or_profile_detected"] is True
    assert record["paper_submit_authorized"] is False
    assert record["broker_mutation_performed"] is False


def test_paper_autopilot_blocks_duplicate_client_order_id(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    as_of_date = "2026-08-08"
    client_order_id = paper_autopilot_client_order_id(
        action="buy",
        symbol="SPY",
        as_of_date=as_of_date,
        data_sha256=hashlib.sha256(bars_csv.read_bytes()).hexdigest(),
    )
    broker = FakeAutopilotBroker(
        recent_orders=(
            {
                "id": "prior-order-1",
                "client_order_id": client_order_id,
                "symbol": "SPY",
                "side": "buy",
                "status": "filled",
            },
        )
    )

    record = _run(tmp_path, bars_csv, broker)

    assert record["execution_plan"]["client_order_id"] == client_order_id
    assert record["blocker_status"] == "blocked/duplicate_client_order_id"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert broker.submitted_requests == []


def test_paper_autopilot_restart_blocks_when_broker_forgets_accepted_order(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
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
    first_broker = FakeAutopilotBroker()

    first = _run(
        tmp_path,
        bars_csv,
        first_broker,
        readiness_packet_path=readiness_packet_path,
    )
    restarted_broker = FakeAutopilotBroker()
    restarted = _run(
        tmp_path,
        bars_csv,
        restarted_broker,
        readiness_packet_path=readiness_packet_path,
    )

    assert first["order_journal_reservation_acquired"] is True
    assert first["paper_submit_performed"] is True
    assert restarted["blocker_status"] == (
        "blocked/durable_spy_order_state_unresolved"
    )
    assert restarted["order_journal_unresolved_order_count"] == 1
    assert restarted["paper_submit_authorized"] is False
    assert restarted["paper_submit_performed"] is False
    assert restarted_broker.submitted_requests == []


def test_paper_autopilot_conflicting_strategy_route_skips_broker_factory(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
        candidate_strategy_signals=(_conflicting_promoted_signal(),),
    )

    assert record["strategy_route_status"] == "blocked"
    assert record["strategy_route_reason"] == "conflict_requires_review"
    assert record["blocker_status"] == "blocked/strategy_router_conflict_requires_review"
    assert record["broker_state_observed"] is False
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )
    assert (
        rollup["readiness_status"]
        == "readiness_blocked_strategy_not_mutation_capable"
    )


def test_paper_autopilot_records_shadow_rsi_when_sma_has_insufficient_history(
    tmp_path: Path,
) -> None:
    bars_csv = _write_rsi_shadow_bars(tmp_path)

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )
    route_receipt = record["strategy_route_receipt"]
    signals = route_receipt["signals"]

    assert record["strategy_route_status"] == "blocked"
    assert record["strategy_route_reason"] == "all_candidates_blocked"
    assert record["strategy_route_paper_mutation_allowed"] is False
    assert record["strategy_adapter_resolution_status"] == "blocked"
    assert record["strategy_adapter_reason"] == "strategy_router_all_candidates_blocked"
    assert record["blocker_status"] == "blocked/strategy_router_all_candidates_blocked"
    assert record["broker_state_observed"] is False
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert [signal["strategy_id"] for signal in signals] == [
        SMA_TRAINING_WHEEL_STRATEGY_ID,
        SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
    ]
    assert signals[0]["signal_state"] == "insufficient_evidence"
    assert signals[0]["intended_action"] == "no_action"
    assert signals[1]["signal_state"] == "trade_candidate"
    assert signals[1]["intended_action"] == "buy"
    assert signals[1]["promotion_status"] == "shadow_only"
    assert signals[1]["blockers"] == []
    assert signals[2]["signal_state"] == "insufficient_evidence"
    assert signals[2]["intended_action"] == "no_action"
    assert signals[2]["promotion_status"] == "paper_preview_candidate"
    assert "paper_preview_quarantine" in signals[2]["labels"]
    assert record["strategy_preview_states"][0]["strategy_id"] == (
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    )
    assert record["strategy_preview_adapter_resolutions"][0]["adapter_mode"] == (
        "preview_only"
    )
    assert (
        record["strategy_preview_adapter_resolutions"][0][
            "paper_mutation_allowed"
        ]
        is False
    )
    assert route_receipt["candidate_signal_ids"] == []
    assert route_receipt["blocked_signal_ids"] == [
        SMA_TRAINING_WHEEL_STRATEGY_ID,
        SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID,
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
    ]


def test_paper_autopilot_missing_strategy_adapter_skips_broker_factory(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
        strategy_adapter_registry=(),
    )

    assert record["strategy_route_status"] == "action_routed"
    assert record["strategy_adapter_resolution_status"] == "blocked"
    assert record["strategy_adapter_reason"] == "strategy_adapter_missing"
    assert record["blocker_status"] == "blocked/strategy_adapter_missing"
    assert record["broker_state_observed"] is False
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False


def test_paper_autopilot_disabled_strategy_adapter_skips_broker_factory(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
        strategy_adapter_registry=(
            StrategyAdapterRegistration(
                strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
                promotion_status="paper_mutation_candidate",
                adapter_id="disabled_sma_adapter",
                adapter_mode="paper_mutation",
                asset_class="equity",
                supported_symbols=("SPY",),
                max_order_notional=Decimal("25.00"),
                enabled=False,
                required_labels=(
                    "paper_lab_only",
                    "not_live_authorized",
                    "profit_claim=none",
                ),
                blocker="operator_disabled_strategy_adapter",
            ),
        ),
    )

    assert record["strategy_adapter_resolution_status"] == "blocked"
    assert record["strategy_adapter_id"] == "disabled_sma_adapter"
    assert record["strategy_adapter_reason"] == "operator_disabled_strategy_adapter"
    assert record["blocker_status"] == "blocked/operator_disabled_strategy_adapter"
    assert record["broker_state_observed"] is False
    assert record["paper_submit_authorized"] is False
    assert record["broker_mutation_performed"] is False
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )
    assert (
        rollup["readiness_status"]
        == "readiness_blocked_strategy_not_mutation_capable"
    )


def test_paper_autopilot_blocks_expected_account_mismatch_before_positions(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={**_paper_env(), "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "wrong-account"},
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    assert record["blocker_status"] == "blocked/expected_account_mismatch"
    assert record["expected_account_id_loaded"] is True
    assert record["expected_account_matched"] is False
    assert record["paper_submit_authorized"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.calls == ["get_account"]
    assert broker.submitted_requests == []
    rollup = json.loads(
        Path(record["artifact_paths"]["latest_rollup"]).read_text(encoding="utf-8")
    )
    assert rollup["readiness_status"] == "readiness_blocked_expected_account_mismatch"
    _assert_no_sensitive_values(record)


def test_paper_autopilot_no_new_completed_bar_never_submits(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab_no_new_bar,
        timestamp=GENERATED_AT,
    )

    assert record["blocker_status"] == "blocked/no_new_completed_bar_noop"
    assert record["final_classification"] == "no_new_completed_bar_noop"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert broker.submitted_requests == []


def test_paper_autopilot_ambiguous_submit_blocks_and_does_not_retry(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(raise_on_submit=True)
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

    record = _run(
        tmp_path,
        bars_csv,
        broker,
        readiness_packet_path=readiness_packet_path,
    )

    assert record["blocker_status"] == "blocked/reconciliation_required"
    assert (
        record["final_classification"]
        == "ambiguous_submit_response_reconciliation_required"
    )
    assert record["submit_response_ambiguous"] is True
    assert record["paper_submit_performed"] is True
    assert record["broker_mutation_performed"] is True
    assert broker.calls.count("submit_order") == 1
    assert broker.submitted_requests != []
    _assert_no_sensitive_values(record)


def test_paper_autopilot_database_kill_switch_blocks_submit(
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

    # Write pause state directly to SQLite order journal
    journal_path = tmp_path / "order_journal.sqlite3"
    from algotrader.execution.order_journal import SqliteOrderJournal
    journal = SqliteOrderJournal(journal_path)
    journal.set_runtime_control(
        trading_enabled=False,
        reason="operator manual stop",
        occurred_at=datetime.fromisoformat(GENERATED_AT),
    )

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            readiness_packet_path=readiness_packet_path,
            order_journal_path=journal_path,
            operator_paused=False, # do not override pause in config, let it load from DB
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    assert record["operator_paused"] is True
    assert record["canonical_risk_allowed"] is False
    assert record["canonical_policy_accepted"] is False
    assert record["blocker_status"] == "blocked/operator_paused"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert broker.submitted_requests == []


def test_paper_autopilot_lease_fencing_mismatch_blocks_submit(
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

    journal_path = tmp_path / "order_journal.sqlite3"
    from algotrader.execution.order_journal import SqliteOrderJournal
    journal = SqliteOrderJournal(journal_path)

    res = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="supervisor-pid-9999",
        occurred_at=datetime.fromisoformat(GENERATED_AT),
        ttl_seconds=60,
    )

    with pytest.raises(ValidationError, match="runtime_instance_already_active"):
        run_paper_autopilot_loop(
            PaperAutopilotLoopConfig(
                output_root=tmp_path / "out",
                bars_csv=bars_csv,
                readiness_packet_path=readiness_packet_path,
                order_journal_path=journal_path,
            ),
            env=_paper_env(),
            broker_client_factory=_factory(broker),
            daily_lab_runner=_fake_daily_lab,
            timestamp=GENERATED_AT,
            lease_token="mismatched-token-value",
            fencing_generation=res.fencing_generation,
            lease_owner_run_id="supervisor-pid-9999",
        )

    assert broker.submitted_requests == []


def test_paper_autopilot_fencing_generation_mismatch_blocks_submit(
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

    journal_path = tmp_path / "order_journal.sqlite3"
    from algotrader.execution.order_journal import SqliteOrderJournal
    journal = SqliteOrderJournal(journal_path)

    res = journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="supervisor-pid-9999",
        occurred_at=datetime.fromisoformat(GENERATED_AT),
        ttl_seconds=60,
    )

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            readiness_packet_path=readiness_packet_path,
            order_journal_path=journal_path,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
        lease_token=res.lease_token,
        fencing_generation=res.fencing_generation + 42,
        lease_owner_run_id="supervisor-pid-9999",
    )

    assert record["paper_submit_performed"] is False
    assert record["action_result"]["mutation_status"] == "blocked_before_submit"
    assert record["action_result"]["broker_error"] == "runtime_lease_fencing_mismatch"
    assert broker.submitted_requests == []


def test_paper_autopilot_stop_requested_blocks_submit(
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

    journal_path = tmp_path / "order_journal.sqlite3"
    from algotrader.execution.order_journal import SqliteOrderJournal
    journal = SqliteOrderJournal(journal_path)
    journal.set_runtime_control(
        trading_enabled=True,
        reason="running",
        occurred_at=datetime.fromisoformat(GENERATED_AT),
        stop_requested=True,
    )

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            readiness_packet_path=readiness_packet_path,
            order_journal_path=journal_path,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    assert record["paper_submit_performed"] is False
    assert record["action_result"]["mutation_status"] == "blocked_before_submit"
    assert record["action_result"]["broker_error"] == "stop_requested"
    assert broker.submitted_requests == []


def test_runs_artifacts_remain_gitignored() -> None:
    assert "runs/" in Path(".gitignore").read_text(encoding="utf-8")


class FakeAutopilotBroker:
    def __init__(
        self,
        *,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        recent_orders: tuple[dict[str, object], ...] = (),
        raise_on_submit: bool = False,
    ) -> None:
        self.positions = positions
        self.open_orders = list(open_orders)
        self.recent_orders = list(recent_orders)
        self.raise_on_submit = raise_on_submit
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
        if self.raise_on_submit:
            raise RuntimeError("submit failed with secret=paper-secret-value")
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
            "submitted_at": GENERATED_AT,
        }
        self.recent_orders.append(order)
        return order


def _run(
    tmp_path: Path,
    bars_csv: Path,
    broker: FakeAutopilotBroker,
    *,
    readiness_packet_path: Path | None = None,
) -> dict[str, object]:
    return run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
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


def _conflicting_promoted_signal() -> StrategySignal:
    return StrategySignal(
        strategy_id="test_conflicting_promoted_candidate",
        strategy_family="test_only_router_fixture",
        symbol="SPY",
        asset_class="equity",
        signal_state="trade_candidate",
        intended_action="sell_close",
        intended_side="sell",
        expected_holding_period="test_only",
        max_loss_model="test_only",
        risk_budget="test_only",
        data_as_of=datetime(2026, 8, 8, tzinfo=UTC),
        promotion_status="paper_mutation_candidate",
        labels=("paper_lab_only", "not_live_authorized", "profit_claim=none"),
    )


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


def _fake_daily_lab_no_new_bar(config):  # noqa: ANN001
    payload = dict(_fake_daily_lab(config))
    payload["data_refresh_status"] = "no_new_completed_bar_noop"
    return payload


def _fake_daily_lab_stale(config):  # noqa: ANN001
    payload = dict(_fake_daily_lab(config))
    payload["data_freshness_status"] = "stale_data_preview_only"
    payload["data_refresh_status"] = "stale_data_preview_only"
    return payload


def _fake_daily_lab_pre_broker_not_observed(config):  # noqa: ANN001
    payload = dict(_fake_daily_lab(config))
    payload["blocker_status"] = "blocked/broker_state_not_observed"
    payload["next_operator_action"] = "configure_verified_paper_profile_then_rerun"
    return payload


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


def _latest_jsonl(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8").splitlines()[-1])


def _write_rsi_shadow_bars(tmp_path: Path) -> Path:
    path = tmp_path / "rsi_shadow_only.csv"
    start = date(2026, 7, 25)
    rows = ["date,symbol,open,high,low,close,adjusted_close,volume"]
    for index in range(15):
        current = start + timedelta(days=index)
        close = Decimal(115 - index)
        rows.append(
            f"{current.isoformat()},SPY,{close},{close},{close},{close},{close},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _assert_artifacts(record: dict[str, object]) -> None:
    paths = record["artifact_paths"]
    assert Path(paths["operating_brief"]).is_file()
    assert Path(paths["operating_record"]).is_file()
    assert Path(paths["manifest"]).is_file()
    assert Path(paths["latest_status"]).is_file()
    assert Path(paths["supervisor_brief"]).is_file()
    assert Path(paths["supervisor_receipt"]).is_file()
    assert Path(paths["broker_snapshot"]).is_file()
    assert Path(paths["operating_history"]).is_file()
    assert Path(paths["daily_autonomy_ledger"]).is_file()
    assert Path(paths["latest_daily_autonomy"]).is_file()
    assert Path(paths["daily_autonomy_summary"]).is_file()
    assert Path(paths["latest_rollup"]).is_file()
    assert Path(paths["operating_summary"]).is_file()
    latest = json.loads(Path(paths["latest_status"]).read_text(encoding="utf-8"))
    assert latest["run_id"] == record["run_id"]
    record_lines = Path(paths["operating_record"]).read_text(encoding="utf-8").splitlines()
    assert json.loads(record_lines[-1])["run_id"] == record["run_id"]
    receipt_lines = (
        Path(paths["supervisor_receipt"]).read_text(encoding="utf-8").splitlines()
    )
    receipt = json.loads(receipt_lines[-1])
    assert receipt["final_classification"] == record["final_classification"]
    history_lines = (
        Path(paths["operating_history"]).read_text(encoding="utf-8").splitlines()
    )
    assert json.loads(history_lines[-1])["run_id"] == record["run_id"]
    rollup = json.loads(Path(paths["latest_rollup"]).read_text(encoding="utf-8"))
    assert rollup["classification"] == "healthy_hold_noop"
    assert rollup["autonomy_status"] == "healthy_continue_next_daily_cycle"
    assert rollup["readiness_status"] == "no_mutation_needed_continue"
    assert rollup["readiness_packet_generated"] is False


def _assert_no_sensitive_values(record: dict[str, object]) -> None:
    rendered = json.dumps(record, sort_keys=True)
    assert PAPER_KEY not in rendered
    assert PAPER_SECRET not in rendered
    assert EXPECTED_ACCOUNT_ID not in rendered
    assert record["credential_values_exposed"] is False
