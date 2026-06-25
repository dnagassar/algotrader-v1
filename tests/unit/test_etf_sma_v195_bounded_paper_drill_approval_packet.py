from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
import inspect
from pathlib import Path

import algotrader.execution.etf_sma_v195_bounded_paper_drill_approval_packet as packet_module
from algotrader.execution.etf_sma_daily_oms_rehearsal import (
    OFFLINE_FIXTURE_BROKER_STATE_MODE,
    OfflineOmsFixture,
)
from algotrader.execution.etf_sma_daily_order_intent_adapter import (
    OFFLINE_APPROVAL_SOURCE,
    OfflineOrderIntentApprovalFixture,
)
from algotrader.execution.etf_sma_daily_order_intent_review_packet import (
    REVIEW_READY_FAKE_ONLY,
    run_v193_order_intent_review_packet,
)
from algotrader.execution.etf_sma_v195_bounded_paper_drill_approval_packet import (
    APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED,
    APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED,
    APPROVAL_PACKET_BLOCKED_MISMATCH,
    APPROVAL_PACKET_BLOCKED_MISSING_CAP,
    APPROVAL_PACKET_BLOCKED_OPEN_ORDER_PRESENT,
    APPROVAL_PACKET_BLOCKED_ORDER_INTENT_INCOMPLETE,
    APPROVAL_PACKET_BLOCKED_REVIEW_NOT_READY,
    APPROVAL_PACKET_BLOCKED_UNEXPECTED_POSITION,
    APPROVAL_PACKET_BLOCKED_UNRESOLVED_PRIOR_MUTATION,
    APPROVAL_PACKET_READY_NO_MUTATION,
    BoundedPaperDrillCap,
    V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE,
    build_v195_bounded_paper_drill_approval_packet,
    run_v195_bounded_paper_drill_approval_packet,
    sample_v195_daily_execution_plan_packet,
)


def test_ready_buy_review_packet_produces_approval_ready_no_mutation(
    tmp_path: Path,
) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["approval_packet_classification"] == APPROVAL_PACKET_READY_NO_MUTATION
    assert result["operator_review_classification"] == REVIEW_READY_FAKE_ONLY
    assert result["order_side"] == "buy"
    assert result["notional"] == "25.00"
    assert result["quantity"] == ""
    assert result["maximum_notional_cap"] == "25.00"
    assert result["maximum_quantity_cap"] == ""
    assert result["fake_oms_classification"] == "submitted_cancel_confirmed"
    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    assert result["fake_submit_call_count_label"] == "simulated_fake_oms_only"
    assert result["fake_cancel_call_count_label"] == "simulated_fake_oms_only"
    assert result["next_operator_action"] == (
        "gpt_operator_review_packet_before_future_separately_authorized_paper_drill"
    )
    _assert_projected_request_unsent(result)
    _assert_future_prerequisites(result)
    _assert_not_authorization(result)
    _assert_real_submit_live_flags_false(result)
    _assert_artifacts_exist(result)


def test_ready_sell_review_packet_produces_approval_ready_no_mutation(
    tmp_path: Path,
) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["approval_packet_classification"] == APPROVAL_PACKET_READY_NO_MUTATION
    assert result["operator_review_classification"] == REVIEW_READY_FAKE_ONLY
    assert result["order_side"] == "sell"
    assert result["quantity"] == "0.0001"
    assert result["notional"] == ""
    assert result["maximum_quantity_cap"] == "0.0001"
    assert result["order_type"] == "limit"
    assert result["time_in_force"] == "day"
    _assert_projected_request_unsent(result)
    _assert_real_submit_live_flags_false(result)


def test_review_not_ready_blocks_approval_packet(tmp_path: Path) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("none", status="blocked", blocker="manual_review_required"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["approval_packet_classification"] == (
        APPROVAL_PACKET_BLOCKED_REVIEW_NOT_READY
    )
    assert result["upstream_blocker"] == "manual_review_required"
    assert "review_packet_not_ready" in result["stop_conditions_triggered_now"]
    _assert_real_submit_live_flags_false(result)


def test_approval_missing_blocks_approval_packet(tmp_path: Path) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("buy_preview"),
        output_root=tmp_path / "run",
    )

    assert result["approval_packet_classification"] == (
        APPROVAL_PACKET_BLOCKED_AUTHORIZATION_NOT_REQUESTED
    )
    assert result["source_v193_order_intent_review_packet"]["approval_granted"] is False
    assert result["fake_submit_call_count"] == 0
    _assert_real_submit_live_flags_false(result)


def test_order_intent_incomplete_blocks_approval_packet(tmp_path: Path) -> None:
    review = _ready_review(tmp_path)
    review["order_intent"]["quantity"] = ""
    review["order_intent"]["notional"] = ""
    review["quantity"] = ""
    review["notional"] = ""

    result = build_v195_bounded_paper_drill_approval_packet(
        review,
        output_root=tmp_path / "approval",
    )

    assert result["approval_packet_classification"] == (
        APPROVAL_PACKET_BLOCKED_ORDER_INTENT_INCOMPLETE
    )
    assert "missing_quantity_or_notional" in result["approval_packet_validation"][
        "order_intent_issues"
    ]
    _assert_real_submit_live_flags_false(result)


def test_broker_state_required_is_explicit_before_future_real_paper_drill(
    tmp_path: Path,
) -> None:
    ready = run_v195_bounded_paper_drill_approval_packet(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "ready",
    )
    blocked = run_v195_bounded_paper_drill_approval_packet(
        _packet("buy_preview"),
        approval_fixture=OfflineOrderIntentApprovalFixture(
            approval_granted=True,
            broker_state_mode="broker_state_not_observed",
        ),
        output_root=tmp_path / "blocked",
    )

    assert ready["future_broker_read_required"] is True
    assert ready["broker_state_prerequisites"][
        "required_mode"
    ] == "future_explicit_alpaca_paper_read_only_observation"
    assert ready["broker_state_prerequisites"][
        "broker_read_performed_in_this_packet"
    ] is False
    assert "The broker endpoint must be the paper endpoint, not a live endpoint." in ready[
        "expected_account_profile_endpoint_checks"
    ]
    assert blocked["approval_packet_classification"] == (
        APPROVAL_PACKET_BLOCKED_BROKER_STATE_REQUIRED
    )
    _assert_real_submit_live_flags_false(ready)
    _assert_real_submit_live_flags_false(blocked)


def test_unresolved_prior_mutation_blocks_approval_packet(tmp_path: Path) -> None:
    root = tmp_path / "run"
    run_v195_bounded_paper_drill_approval_packet(
        _packet("sell_preview", execution_plan_id="daily_execution_plan_v195_first"),
        approval_fixture=_offline_approval(),
        oms_fixture=OfflineOmsFixture(submit_exception_message="connection timed out"),
        output_root=root,
    )

    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("sell_preview", execution_plan_id="daily_execution_plan_v195_second"),
        approval_fixture=_offline_approval(),
        output_root=root,
    )

    assert result["approval_packet_classification"] == (
        APPROVAL_PACKET_BLOCKED_UNRESOLVED_PRIOR_MUTATION
    )
    assert "unresolved_prior_mutation" in result["stop_conditions_triggered_now"]
    _assert_real_submit_live_flags_false(result)


def test_existing_spy_open_order_blocks_approval_packet(tmp_path: Path) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        oms_fixture=OfflineOmsFixture(
            open_orders=(_order(client_order_id="existing-spy-order", status="accepted"),),
            all_orders=(_order(client_order_id="existing-spy-order", status="accepted"),),
        ),
        output_root=tmp_path / "run",
    )

    assert result["approval_packet_classification"] == (
        APPROVAL_PACKET_BLOCKED_OPEN_ORDER_PRESENT
    )
    assert "existing_spy_open_order" in result["stop_conditions_triggered_now"]
    _assert_real_submit_live_flags_false(result)


def test_unexpected_non_spy_position_blocks_approval_packet(tmp_path: Path) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        oms_fixture=OfflineOmsFixture(positions=(_spy_position(), _position("MSFT"))),
        output_root=tmp_path / "run",
    )

    assert result["approval_packet_classification"] == (
        APPROVAL_PACKET_BLOCKED_UNEXPECTED_POSITION
    )
    assert "unexpected_non_spy_position" in result["stop_conditions_triggered_now"]
    _assert_real_submit_live_flags_false(result)


def test_missing_cap_blocks_approval_packet(tmp_path: Path) -> None:
    review = _ready_review(tmp_path)

    result = build_v195_bounded_paper_drill_approval_packet(
        review,
        output_root=tmp_path / "approval",
        cap=BoundedPaperDrillCap(),
    )

    assert result["approval_packet_classification"] == APPROVAL_PACKET_BLOCKED_MISSING_CAP
    assert result["maximum_notional_or_quantity_cap"] == ""
    assert "missing_cap" in result["stop_conditions_triggered_now"]
    _assert_real_submit_live_flags_false(result)


def test_intent_rehearsal_mismatch_blocks_approval_packet(tmp_path: Path) -> None:
    review = _ready_review(tmp_path)
    review["intent_rehearsal_consistency_passed"] = False
    review["intent_rehearsal_consistency_checks"]["side_matches"] = {
        "passed": False,
        "intent_value": "buy",
        "rehearsal_value": "sell",
    }

    result = build_v195_bounded_paper_drill_approval_packet(
        review,
        output_root=tmp_path / "approval",
    )

    assert result["approval_packet_classification"] == APPROVAL_PACKET_BLOCKED_MISMATCH
    assert "intent_rehearsal_mismatch" in result["stop_conditions_triggered_now"]
    _assert_real_submit_live_flags_false(result)


def test_projected_broker_request_fields_are_present_but_marked_unsent(
    tmp_path: Path,
) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["projected_broker_request_fields"] == {
        "asset_class": "equity",
        "client_order_id": result["client_order_id"],
        "notional": "25.00",
        "order_type": "market",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    assert result["proposed_future_paper_action_fields"]["projected_only"] is True
    _assert_projected_request_unsent(result)


def test_required_future_authorization_phrase_is_present_exactly(
    tmp_path: Path,
) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert (
        result["required_future_authorization_phrase"]
        == V195_REQUIRED_FUTURE_AUTHORIZATION_PHRASE
    )
    assert (
        result["required_future_authorization_phrase"]
        == "AUTHORIZE_V1_95_BOUNDED_SPY_PAPER_DRILL"
    )
    assert result["future_authorization_phrase_requested_now"] is False


def test_approval_packet_clearly_states_it_is_not_authorization(
    tmp_path: Path,
) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    _assert_not_authorization(result)


def test_all_real_broker_paper_submit_and_live_flags_remain_false(
    tmp_path: Path,
) -> None:
    result = run_v195_bounded_paper_drill_approval_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    _assert_real_submit_live_flags_false(result)
    assert result["hard_gates_closed"] is True
    assert all(item["closed"] for item in result["hard_gate_checklist"].values())


def test_module_exposes_no_real_broker_client_or_sdk_selection() -> None:
    signature = inspect.signature(run_v195_bounded_paper_drill_approval_packet)
    source = inspect.getsource(packet_module)

    assert "broker_client" not in signature.parameters
    assert "broker_factory" not in signature.parameters
    assert "AlpacaSdkClient" not in source
    assert "alpaca_sdk_client" not in source
    assert "TradingClient" not in source
    assert "submit_order(" not in source
    assert "cancel_order(" not in source
    assert "replace_order(" not in source
    assert "close_position(" not in source
    assert "liquidate(" not in source


def test_runtime_artifacts_remain_untracked() -> None:
    assert "runs/" in Path(".gitignore").read_text(encoding="utf-8").splitlines()


def _ready_review(tmp_path: Path) -> dict[str, object]:
    return run_v193_order_intent_review_packet(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "review",
    )


def _packet(
    action: str,
    *,
    status: str = "preview_only",
    requires_approval: bool = True,
    blocker: str = "none",
    execution_plan_id: str | None = None,
) -> dict[str, object]:
    packet = deepcopy(sample_v195_daily_execution_plan_packet(action))
    packet["broker_state_mode"] = OFFLINE_FIXTURE_BROKER_STATE_MODE
    packet["broker_state_source"] = OFFLINE_APPROVAL_SOURCE
    packet["preview_decision"] = action
    plan = packet["execution_plan"]
    plan["execution_plan_id"] = execution_plan_id or (
        f"daily_execution_plan_v195_{action.replace('/', '_')}"
    )
    plan["execution_plan_status"] = status
    plan["execution_plan_action"] = action
    plan["execution_plan_source_preview_decision"] = action
    plan["execution_plan_requires_approval"] = requires_approval
    plan["execution_plan_blocker"] = blocker
    plan["execution_plan_reason"] = (
        blocker
        if blocker != "none"
        else (
            f"{action}_requires_explicit_authorization"
            if action in {"buy_preview", "sell_preview"}
            else "existing_spy_position_satisfies_risk_on_preview"
        )
    )
    return packet


def _offline_approval() -> OfflineOrderIntentApprovalFixture:
    return OfflineOrderIntentApprovalFixture(approval_granted=True)


def _assert_projected_request_unsent(result: dict[str, object]) -> None:
    assert result["projected_broker_request_fields"]
    assert result["projected_broker_request_status"] == "projected_only_not_sent"
    assert result["projected_broker_request_label"] == "projected_only"
    assert result["projected_fields_are_projected_only"] is True
    assert result["broker_request_sent"] is False


def _assert_future_prerequisites(result: dict[str, object]) -> None:
    assert result["future_broker_read_required"] is True
    assert result["future_paper_submit_requires_explicit_authorization"] is True
    assert result["future_authorization_phrase_required"] is True
    assert result["duplicate_client_order_id_prevention_requirements"] == [
        f"Freshly query paper orders for client_order_id={result['client_order_id']}.",
        "Block the future drill if the deterministic client_order_id already exists.",
        "Do not alter the deterministic client_order_id after GPT/operator review.",
    ]
    assert "Block if any SPY open order exists." in result[
        "open_order_blocker_requirements"
    ]
    assert "Block if any non-SPY position exists." in result[
        "unexpected_position_blocker_requirements"
    ]
    assert "Any future cancel requires separate explicit operator authorization." in result[
        "cancel_reconciliation_expectations"
    ]


def _assert_not_authorization(result: dict[str, object]) -> None:
    assert result["approval_packet_is_authorization"] is False
    assert "not authorization" in result["not_authorization_statement"].lower()
    assert "not authorization" in result["approval_packet_statement"].lower()
    assert result["paper_submit_authorized"] is False


def _assert_real_submit_live_flags_false(result: dict[str, object]) -> None:
    for key in (
        "broker_request_sent",
        "paper_submit_authorized",
        "paper_submit_performed",
        "real_broker_read_performed",
        "real_broker_mutation_performed",
        "broker_mutation_performed",
        "live_trading_authorized",
        "live_trading_performed",
        "real_broker_client_selected",
        "real_broker_client_instantiated",
    ):
        assert result[key] is False
    for label in (
        "paper_lab_only",
        "offline_only",
        "not_live_authorized",
        "profit_claim=none",
        "paper_submit_authorized=false",
        "approval_packet_only",
        "no_broker_read_performed",
        "no_broker_mutation_performed",
    ):
        assert label in result["safety_labels"]


def _assert_artifacts_exist(result: dict[str, object]) -> None:
    for artifact_path in result["artifact_paths"].values():
        if artifact_path:
            assert Path(str(artifact_path)).exists()


def _position(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "qty": Decimal("1"),
        "market_value": Decimal("400.00"),
        "average_entry_price": Decimal("400.00"),
        "side": "long",
    }


def _spy_position() -> dict[str, object]:
    return {
        "symbol": "SPY",
        "qty": Decimal("0.01"),
        "market_value": Decimal("6.00"),
        "average_entry_price": Decimal("500.00"),
        "side": "long",
    }


def _order(
    *,
    client_order_id: str,
    status: str,
    filled_qty: str = "0",
) -> dict[str, object]:
    now = datetime(2026, 6, 24, 15, 30, tzinfo=UTC)
    return {
        "id": "offline-fixture-order-1",
        "client_order_id": client_order_id,
        "symbol": "SPY",
        "asset_class": "equity",
        "side": "sell",
        "type": "limit",
        "time_in_force": "day",
        "qty": Decimal("0.0001"),
        "limit_price": Decimal("630.00"),
        "status": status,
        "filled_qty": Decimal(filled_qty),
        "filled_avg_price": Decimal("0") if filled_qty == "0" else Decimal("620.00"),
        "created_at": now,
        "submitted_at": now,
    }
