from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
import inspect
from pathlib import Path

import algotrader.execution.etf_sma_daily_order_intent_review_packet as review_module
from algotrader.execution.etf_sma_daily_oms_rehearsal import (
    OFFLINE_FIXTURE_BROKER_STATE_MODE,
    OfflineOmsFixture,
)
from algotrader.execution.etf_sma_daily_order_intent_adapter import (
    OFFLINE_APPROVAL_SOURCE,
    OfflineOrderIntentApprovalFixture,
    run_v192_order_intent_adapter,
    sample_v192_daily_execution_plan_packet,
)
from algotrader.execution.etf_sma_daily_order_intent_review_packet import (
    REVIEW_BLOCKED_APPROVAL_REQUIRED,
    REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED,
    REVIEW_BLOCKED_INSUFFICIENT_HISTORY,
    REVIEW_BLOCKED_INTENT_INCOMPLETE,
    REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH,
    REVIEW_BLOCKED_OPEN_ORDER_PRESENT,
    REVIEW_BLOCKED_UNEXPECTED_POSITION,
    REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION,
    REVIEW_BLOCKED_UPSTREAM_BLOCKER,
    REVIEW_READY_FAKE_ONLY,
    build_v193_order_intent_review_packet,
    run_v193_order_intent_review_packet,
)


def test_review_packet_ready_when_offline_approved_intent_and_rehearsal_match(
    tmp_path: Path,
) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_READY_FAKE_ONLY
    assert result["order_side"] == "sell"
    assert result["approval_granted"] is True
    assert result["approval_source"] == OFFLINE_APPROVAL_SOURCE
    assert result["real_operator_authorization"] is False
    assert result["fake_oms_classification"] == "submitted_cancel_confirmed"
    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    checks = result["intent_rehearsal_consistency_checks"]
    assert checks["side_matches"]["passed"] is True
    assert checks["symbol_matches"]["passed"] is True
    assert checks["deterministic_client_order_id_matches"]["passed"] is True
    assert result["intent_rehearsal_consistency_passed"] is True
    for artifact_path in result["artifact_paths"].values():
        assert Path(artifact_path).exists()
    _assert_projected_request_is_unsent(result)
    _assert_real_submit_and_live_flags_false(result)


def test_buy_preview_with_offline_approval_produces_review_ready_fake_only(
    tmp_path: Path,
) -> None:
    packet = _packet("buy_preview")

    result = run_v193_order_intent_review_packet(
        packet,
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_READY_FAKE_ONLY
    assert result["symbol"] == "SPY"
    assert result["preview_decision"] == "buy_preview"
    assert result["order_side"] == "buy"
    assert result["notional"] == "25.00"
    assert result["quantity"] == ""
    assert result["quantity_or_notional_source"] == (
        "paper_order_policy.equity.max_notional_cap"
    )
    assert result["order_type"] == "market"
    assert result["time_in_force"] == "day"
    assert result["client_order_id"] == result["deterministic_client_order_id"]
    assert result["fake_oms_classification"] == "submitted_cancel_confirmed"
    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    assert result["fake_submit_call_count_label"] == "simulated_fake_oms_only"
    assert result["fake_cancel_call_count_label"] == "simulated_fake_oms_only"
    checks = result["intent_rehearsal_consistency_checks"]
    assert checks["side_matches"] == {
        "passed": True,
        "intent_value": "buy",
        "rehearsal_value": "buy",
    }
    assert checks["symbol_matches"]["passed"] is True
    assert checks["deterministic_client_order_id_matches"]["passed"] is True
    assert result["intent_rehearsal_consistency_passed"] is True
    assert result["projected_broker_request_fields"] == {
        "asset_class": "equity",
        "client_order_id": result["client_order_id"],
        "notional": "25.00",
        "order_type": "market",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    _assert_projected_request_is_unsent(result)
    _assert_real_submit_and_live_flags_false(result)


def test_approval_missing_blocks_review(tmp_path: Path) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_APPROVAL_REQUIRED
    assert result["approval_granted"] is False
    assert result["real_operator_authorization"] is False
    assert result["fake_submit_call_count"] == 0
    _assert_real_submit_and_live_flags_false(result)


def test_buy_preview_without_approval_blocks_review(tmp_path: Path) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("buy_preview"),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_APPROVAL_REQUIRED
    assert result["approval_granted"] is False
    assert result["order_intent_created"] is False
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 0
    _assert_real_submit_and_live_flags_false(result)


def test_upstream_blocked_plan_blocks_review(tmp_path: Path) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("none", status="blocked", blocker="manual_review_required"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_UPSTREAM_BLOCKER
    assert result["upstream_blocker"] == "manual_review_required"
    assert result["order_intent_created"] is False


def test_insufficient_history_blocks_review(tmp_path: Path) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("none", status="blocked", blocker="insufficient_history"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_INSUFFICIENT_HISTORY
    assert result["fake_submit_call_count"] == 0


def test_unobserved_broker_state_without_explicit_offline_fixture_blocks(
    tmp_path: Path,
) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        approval_fixture=OfflineOrderIntentApprovalFixture(
            approval_granted=True,
            broker_state_mode="broker_state_not_observed",
        ),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_BROKER_STATE_UNOBSERVED
    assert result["broker_state_mode"] == "broker_state_not_observed"
    assert result["real_broker_read_performed"] is False


def test_missing_required_order_intent_fields_blocks_review(tmp_path: Path) -> None:
    v192_packet = _v192_sell_packet(tmp_path)
    intent = v192_packet["order_intent"]
    intent["side"] = ""
    intent["quantity"] = ""
    intent["notional"] = ""
    intent["order_type"] = ""
    intent["time_in_force"] = ""

    result = build_v193_order_intent_review_packet(
        v192_packet,
        daily_packet_or_execution_plan=_packet("sell_preview"),
        output_root=tmp_path / "review",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_INTENT_INCOMPLETE
    assert "invalid_or_missing_side" in result["intent_validation_issues"]
    assert "missing_quantity_or_notional" in result["intent_validation_issues"]
    assert "missing_order_type" in result["intent_validation_issues"]
    assert "missing_time_in_force" in result["intent_validation_issues"]


def test_intent_rehearsal_symbol_mismatch_blocks_review(tmp_path: Path) -> None:
    v192_packet = _v192_sell_packet(tmp_path)
    v192_packet["oms_rehearsal"]["symbol"] = "QQQ"

    result = build_v193_order_intent_review_packet(
        v192_packet,
        daily_packet_or_execution_plan=_packet("sell_preview"),
        output_root=tmp_path / "review",
    )

    assert result["final_review_classification"] == (
        REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH
    )
    assert result["intent_rehearsal_consistency_checks"]["symbol_matches"][
        "passed"
    ] is False


def test_intent_rehearsal_side_mismatch_blocks_review(tmp_path: Path) -> None:
    v192_packet = _v192_sell_packet(tmp_path)
    v192_packet["oms_rehearsal"]["side"] = "buy"

    result = build_v193_order_intent_review_packet(
        v192_packet,
        daily_packet_or_execution_plan=_packet("sell_preview"),
        output_root=tmp_path / "review",
    )

    assert result["final_review_classification"] == (
        REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH
    )
    assert result["order_side"] == "sell"
    assert result["intent_rehearsal_consistency_checks"]["side_matches"][
        "passed"
    ] is False


def test_intent_rehearsal_client_order_id_mismatch_blocks_review(
    tmp_path: Path,
) -> None:
    v192_packet = _v192_sell_packet(tmp_path)
    v192_packet["oms_rehearsal"]["client_order_id"] = "different-client-order-id"
    v192_packet["oms_rehearsal"]["deterministic_client_order_id"] = (
        "different-client-order-id"
    )

    result = build_v193_order_intent_review_packet(
        v192_packet,
        daily_packet_or_execution_plan=_packet("sell_preview"),
        output_root=tmp_path / "review",
    )

    assert result["final_review_classification"] == (
        REVIEW_BLOCKED_INTENT_REHEARSAL_MISMATCH
    )
    assert result["intent_rehearsal_consistency_checks"][
        "deterministic_client_order_id_matches"
    ]["passed"] is False


def test_unresolved_prior_mutation_blocks_review(tmp_path: Path) -> None:
    root = tmp_path / "run"
    run_v193_order_intent_review_packet(
        _packet("sell_preview", execution_plan_id="daily_execution_plan_v193_first"),
        approval_fixture=_offline_approval(),
        oms_fixture=OfflineOmsFixture(submit_exception_message="connection timed out"),
        output_root=root,
    )

    result = run_v193_order_intent_review_packet(
        _packet("sell_preview", execution_plan_id="daily_execution_plan_v193_second"),
        approval_fixture=_offline_approval(),
        output_root=root,
    )

    assert result["final_review_classification"] == (
        REVIEW_BLOCKED_UNRESOLVED_PRIOR_MUTATION
    )
    assert result["fake_submit_call_count"] == 0


def test_existing_spy_open_order_blocks_review(tmp_path: Path) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        oms_fixture=OfflineOmsFixture(
            open_orders=(_order(client_order_id="existing-spy-order", status="accepted"),),
            all_orders=(_order(client_order_id="existing-spy-order", status="accepted"),),
        ),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_OPEN_ORDER_PRESENT
    assert result["fake_submit_call_count"] == 0


def test_unexpected_non_spy_position_blocks_review(tmp_path: Path) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        oms_fixture=OfflineOmsFixture(positions=(_spy_position(), _position("MSFT"))),
        output_root=tmp_path / "run",
    )

    assert result["final_review_classification"] == REVIEW_BLOCKED_UNEXPECTED_POSITION
    assert result["fake_submit_call_count"] == 0


def test_projected_broker_request_fields_are_present_but_marked_unsent(
    tmp_path: Path,
) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    _assert_projected_request_is_unsent(result)
    assert result["projected_broker_request_fields"] == {
        "asset_class": "equity",
        "client_order_id": result["client_order_id"],
        "limit_price": "630.00",
        "order_type": "limit",
        "qty": "0.0001",
        "side": "sell",
        "symbol": "SPY",
        "time_in_force": "day",
    }


def test_real_broker_paper_submit_and_live_flags_remain_false(
    tmp_path: Path,
) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    _assert_real_submit_and_live_flags_false(result)
    assert all(item["closed"] for item in result["hard_gate_checklist"].values())


def test_fake_submit_and_cancel_counts_are_labeled_simulated(tmp_path: Path) -> None:
    result = run_v193_order_intent_review_packet(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    assert result["fake_submit_call_count_label"] == "simulated_fake_oms_only"
    assert result["fake_cancel_call_count_label"] == "simulated_fake_oms_only"


def test_runner_exposes_no_real_alpaca_sdk_client_selection() -> None:
    signature = inspect.signature(run_v193_order_intent_review_packet)
    source = inspect.getsource(review_module)

    assert "broker_client" not in signature.parameters
    assert "broker_factory" not in signature.parameters
    assert "AlpacaSdkClient" not in source
    assert "alpaca_sdk_client" not in source
    assert "TradingClient" not in source


def test_runs_directory_is_ignored_for_runtime_artifacts() -> None:
    assert "runs/" in Path(".gitignore").read_text(encoding="utf-8").splitlines()


def _packet(
    action: str,
    *,
    status: str = "preview_only",
    requires_approval: bool = True,
    blocker: str = "none",
    execution_plan_id: str | None = None,
) -> dict[str, object]:
    packet = deepcopy(sample_v192_daily_execution_plan_packet())
    packet["broker_state_mode"] = OFFLINE_FIXTURE_BROKER_STATE_MODE
    packet["broker_state_source"] = OFFLINE_APPROVAL_SOURCE
    packet["preview_decision"] = action
    plan = packet["execution_plan"]
    plan["execution_plan_id"] = execution_plan_id or (
        f"daily_execution_plan_v193_{action.replace('/', '_')}"
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


def _v192_sell_packet(tmp_path: Path) -> dict[str, object]:
    return run_v192_order_intent_adapter(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "v192",
    )


def _offline_approval() -> OfflineOrderIntentApprovalFixture:
    return OfflineOrderIntentApprovalFixture(approval_granted=True)


def _assert_projected_request_is_unsent(result: dict[str, object]) -> None:
    assert result["projected_broker_request_fields"]
    assert result["projected_broker_request_status"] == "projected_only_not_sent"
    assert result["broker_request_sent"] is False
    assert "No broker request was sent" in result["broker_request_sent_statement"]
    assert result["projected_broker_request_fields"]["client_order_id"] == (
        result["client_order_id"]
    )


def _assert_real_submit_and_live_flags_false(result: dict[str, object]) -> None:
    for key in (
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
