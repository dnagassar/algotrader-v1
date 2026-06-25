from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import inspect
from pathlib import Path

import algotrader.execution.etf_sma_daily_order_intent_adapter as adapter_module
from algotrader.execution.etf_sma_daily_oms_rehearsal import (
    OFFLINE_FIXTURE_BROKER_STATE_MODE,
    OFFLINE_OMS_REHEARSAL_MODE,
    OfflineOmsFixture,
    sample_daily_execution_plan_packet,
)
from algotrader.execution.etf_sma_daily_order_intent_adapter import (
    OFFLINE_APPROVAL_SOURCE,
    OfflineOrderIntentApprovalFixture,
    deterministic_v192_client_order_id,
    run_v192_order_intent_adapter,
)


def test_buy_preview_without_approval_blocks_before_fake_mutation(tmp_path: Path) -> None:
    result = run_v192_order_intent_adapter(_packet("buy_preview"), output_root=tmp_path / "run")

    assert result["oms_classification"] == "approval_required"
    assert result["blocker"] == "approval_required"
    assert result["order_intent_created"] is False
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 0
    _assert_real_and_submit_flags_false(result)


def test_buy_preview_with_offline_approval_creates_intent_and_fake_rehearsal(
    tmp_path: Path,
) -> None:
    packet = _packet("buy_preview")

    result = run_v192_order_intent_adapter(
        packet,
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["order_intent_created"] is True
    assert result["approval_granted"] is True
    assert result["approval_source"] == OFFLINE_APPROVAL_SOURCE
    assert result["paper_submit_authorized"] is False
    assert result["oms_classification"] == "submitted_cancel_confirmed"
    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    intent = result["order_intent"]
    assert intent["side"] == "buy"
    assert intent["notional"] == "25.00"
    assert intent["quantity"] == ""
    assert intent["quantity_or_notional_source"] == (
        "paper_order_policy.equity.max_notional_cap"
    )
    assert intent["order_type"] == "market"
    assert intent["time_in_force"] == "day"
    assert intent["client_order_id"] == deterministic_v192_client_order_id(packet)
    rehearsal = result["oms_rehearsal"]
    assert rehearsal["side"] == "buy"
    assert rehearsal["order_type"] == "market"
    assert rehearsal["time_in_force"] == "day"
    assert rehearsal["quantity"] == ""
    assert rehearsal["notional"] == "25.00"
    assert rehearsal["limit_price"] == ""
    assert rehearsal["fake_submitted_request_fields"]["side"] == "buy"
    assert rehearsal["fake_submitted_request_fields"]["client_order_id"] == (
        deterministic_v192_client_order_id(packet)
    )
    _assert_intent_safety_fields(intent)
    _assert_real_and_submit_flags_false(result)


def test_sell_preview_without_approval_blocks_before_fake_mutation(tmp_path: Path) -> None:
    result = run_v192_order_intent_adapter(_packet("sell_preview"), output_root=tmp_path / "run")

    assert result["oms_classification"] == "approval_required"
    assert result["order_intent_created"] is False
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 0
    _assert_real_and_submit_flags_false(result)


def test_sell_preview_with_offline_approval_creates_intent_and_fake_rehearsal(
    tmp_path: Path,
) -> None:
    packet = _packet("sell_preview")

    result = run_v192_order_intent_adapter(
        packet,
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["order_intent_created"] is True
    assert result["oms_classification"] == "submitted_cancel_confirmed"
    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    intent = result["order_intent"]
    assert intent["side"] == "sell"
    assert intent["quantity"] == "0.0001"
    assert intent["notional"] == ""
    assert intent["quantity_or_notional_source"] == (
        "paper_mutation_oms.V189_MIN_FRACTIONAL_QTY"
    )
    assert intent["order_type"] == "limit"
    assert intent["time_in_force"] == "day"
    assert intent["limit_price"] == "630.00"
    assert result["oms_rehearsal"]["side"] == "sell"
    _assert_intent_safety_fields(intent)
    _assert_real_and_submit_flags_false(result)


def test_hold_noop_produces_no_order_intent_or_fake_calls(tmp_path: Path) -> None:
    result = run_v192_order_intent_adapter(
        _packet("hold/noop", status="no_action_required", requires_approval=False),
        output_root=tmp_path / "run",
    )

    assert result["oms_classification"] == "not_submitted_hold_noop"
    assert result["order_intent_created"] is False
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 0
    _assert_real_and_submit_flags_false(result)


def test_blocked_open_order_plan_does_not_create_order_intent(tmp_path: Path) -> None:
    result = run_v192_order_intent_adapter(
        _packet("none", status="blocked", blocker="open_order_present"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["oms_classification"] == "blocked_open_order_present"
    assert result["order_intent_created"] is False
    assert result["fake_submit_call_count"] == 0


def test_unexpected_non_spy_position_fixture_blocks_before_order_intent(
    tmp_path: Path,
) -> None:
    result = run_v192_order_intent_adapter(
        _packet("sell_preview"),
        approval_fixture=_offline_approval(),
        oms_fixture=OfflineOmsFixture(positions=(_spy_position(), _position("MSFT"))),
        output_root=tmp_path / "run",
    )

    assert result["oms_classification"] == "blocked_unexpected_position"
    assert result["order_intent_created"] is False
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 0


def test_insufficient_history_preserved_without_order_intent(tmp_path: Path) -> None:
    result = run_v192_order_intent_adapter(
        _packet("none", status="blocked", blocker="insufficient_history"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    assert result["oms_classification"] == "insufficient_history"
    assert result["blocker"] == "insufficient_history"
    assert result["order_intent_created"] is False
    assert result["fake_submit_call_count"] == 0


def test_unobserved_broker_state_fails_closed_unless_offline_fixture_is_explicit(
    tmp_path: Path,
) -> None:
    blocked = run_v192_order_intent_adapter(
        _packet("buy_preview"),
        approval_fixture=OfflineOrderIntentApprovalFixture(
            approval_granted=True,
            broker_state_mode="broker_state_not_observed",
        ),
        output_root=tmp_path / "blocked",
    )
    allowed = run_v192_order_intent_adapter(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "allowed",
    )

    assert blocked["oms_classification"] == "blocked_broker_state_not_observed"
    assert blocked["order_intent_created"] is False
    assert blocked["real_broker_read_performed"] is False
    assert allowed["broker_state_mode"] == OFFLINE_FIXTURE_BROKER_STATE_MODE
    assert allowed["order_intent_created"] is True
    assert allowed["real_broker_read_performed"] is False


def test_order_intent_packet_includes_required_review_fields(tmp_path: Path) -> None:
    result = run_v192_order_intent_adapter(
        _packet("buy_preview"),
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "run",
    )

    expected_fields = {
        "run_id",
        "as_of_date",
        "symbol",
        "source_execution_plan_digest",
        "preview_decision",
        "approval_mode",
        "approval_granted",
        "approval_source",
        "order_side",
        "quantity_or_notional_source",
        "order_type",
        "time_in_force",
        "deterministic_client_order_id",
        "oms_classification",
        "blocker",
        "next_operator_action",
        "paper_submit_authorized",
        "paper_submit_performed",
        "real_broker_read_performed",
        "real_broker_mutation_performed",
        "execution_mode",
        "broker_state_mode",
        "fake_submit_call_count",
        "fake_cancel_call_count",
        "safety_labels",
    }
    assert expected_fields <= set(result)
    assert result["execution_mode"] == OFFLINE_OMS_REHEARSAL_MODE
    assert "paper_lab_only" in result["safety_labels"]
    assert "offline_only" in result["safety_labels"]
    assert "not_live_authorized" in result["safety_labels"]
    assert "profit_claim=none" in result["safety_labels"]
    assert "paper_submit_authorized=false" in result["safety_labels"]
    for artifact_path in result["artifact_paths"].values():
        assert Path(artifact_path).exists()
    _assert_real_and_submit_flags_false(result)


def test_adapter_exposes_no_real_alpaca_sdk_client_selection() -> None:
    signature = inspect.signature(run_v192_order_intent_adapter)
    source = inspect.getsource(adapter_module)

    assert "client" not in signature.parameters
    assert "broker_client" not in signature.parameters
    assert "broker_factory" not in signature.parameters
    assert "AlpacaSdkClient" not in source
    assert "alpaca_sdk_client" not in source
    assert "TradingClient" not in source


def test_same_plan_and_approval_fixture_produces_same_client_order_id(
    tmp_path: Path,
) -> None:
    packet = _packet("buy_preview")
    first = run_v192_order_intent_adapter(
        packet,
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "first",
    )
    second = run_v192_order_intent_adapter(
        packet,
        approval_fixture=_offline_approval(),
        output_root=tmp_path / "second",
    )

    assert first["client_order_id"] == second["client_order_id"]
    assert first["order_intent"]["client_order_id"] == second["order_intent"][
        "client_order_id"
    ]


def test_materially_different_plan_or_side_changes_identity() -> None:
    buy = _packet("buy_preview")
    sell = _packet("sell_preview")
    changed = _packet("buy_preview")
    changed["execution_plan"]["execution_plan_id"] = "daily_execution_plan_v192_changed"
    changed["execution_plan"]["execution_plan_reason"] = "changed_material_reason"

    assert deterministic_v192_client_order_id(buy) != deterministic_v192_client_order_id(sell)
    assert deterministic_v192_client_order_id(buy) != deterministic_v192_client_order_id(changed)


def test_runs_directory_is_ignored_for_runtime_artifacts() -> None:
    assert "runs/" in Path(".gitignore").read_text(encoding="utf-8").splitlines()


def _packet(
    action: str,
    *,
    status: str = "preview_only",
    requires_approval: bool = True,
    blocker: str = "none",
) -> dict[str, object]:
    packet = deepcopy(sample_daily_execution_plan_packet())
    packet["broker_state_mode"] = OFFLINE_FIXTURE_BROKER_STATE_MODE
    packet["broker_state_source"] = OFFLINE_APPROVAL_SOURCE
    packet["preview_decision"] = action
    plan = packet["execution_plan"]
    plan["execution_plan_id"] = f"daily_execution_plan_v192_{action.replace('/', '_')}"
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


def _assert_intent_safety_fields(intent: dict[str, object]) -> None:
    assert intent["approval_granted"] is True
    assert intent["approval_source"] == OFFLINE_APPROVAL_SOURCE
    assert intent["paper_submit_authorized"] is False
    assert intent["paper_submit_performed"] is False
    assert intent["real_broker_read_performed"] is False
    assert intent["real_broker_mutation_performed"] is False


def _assert_real_and_submit_flags_false(result: dict[str, object]) -> None:
    assert result["paper_submit_authorized"] is False
    assert result["paper_submit_performed"] is False
    assert result["real_broker_read_performed"] is False
    assert result["real_broker_mutation_performed"] is False
    assert result["broker_mutation_performed"] is False


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
