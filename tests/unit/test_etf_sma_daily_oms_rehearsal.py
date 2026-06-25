from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
import inspect
import json
from pathlib import Path

import algotrader.execution.etf_sma_daily_oms_rehearsal as rehearsal_module
from algotrader.execution.etf_sma_daily_oms_rehearsal import (
    OFFLINE_FIXTURE_BROKER_STATE_MODE,
    OFFLINE_OMS_REHEARSAL_MODE,
    OfflineOmsFixture,
    deterministic_client_order_id,
    deterministic_execution_plan_digest,
    run_v191_offline_oms_rehearsal,
    sample_daily_execution_plan_packet,
)


def test_daily_hold_noop_plan_performs_no_fake_mutation(tmp_path: Path) -> None:
    packet = _packet(action="hold/noop", status="no_action_required", requires_approval=False)

    result = run_v191_offline_oms_rehearsal(packet, output_root=tmp_path / "run")

    assert result["oms_classification"] == "not_submitted_hold_noop"
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 0
    _assert_real_and_authorization_flags_false(result)


def test_same_plan_rerun_uses_same_client_order_id_and_does_not_resubmit(
    tmp_path: Path,
) -> None:
    packet = _packet()
    root = tmp_path / "run"

    first = run_v191_offline_oms_rehearsal(packet, output_root=root)
    second = run_v191_offline_oms_rehearsal(packet, output_root=root)

    assert first["client_order_id"] == second["client_order_id"]
    assert first["fake_submit_call_count"] == 1
    assert second["oms_classification"] == "blocked_duplicate_client_order_id"
    assert second["fake_submit_call_count"] == 0
    assert second["previous_lifecycle_state"]["outcome_classification"] == (
        "submitted_cancel_confirmed"
    )
    _assert_real_and_authorization_flags_false(second)


def test_materially_different_plan_changes_deterministic_identity() -> None:
    first = _packet()
    second = _packet(execution_plan_id="daily_execution_plan_v191_changed")
    second["execution_plan"]["execution_plan_reason"] = "changed_material_reason"

    assert deterministic_execution_plan_digest(first) != deterministic_execution_plan_digest(second)
    assert deterministic_client_order_id(first) != deterministic_client_order_id(second)


def test_ambiguous_simulated_submit_with_existing_order_reconciles(
    tmp_path: Path,
) -> None:
    result = run_v191_offline_oms_rehearsal(
        _packet(),
        output_root=tmp_path / "run",
        fixture=OfflineOmsFixture(
            submit_exception_message="connection dropped after submit",
            ambiguous_creates_order=True,
        ),
    )

    assert result["oms_classification"] == "ambiguous_submit_reconciled"
    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    assert result["oms_latest"]["reconciliation"]["submit_ambiguous"] is True
    _assert_real_and_authorization_flags_false(result)


def test_ambiguous_submit_without_order_is_unresolved_and_blocks_new_plan(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"

    first = run_v191_offline_oms_rehearsal(
        _packet(),
        output_root=root,
        fixture=OfflineOmsFixture(submit_exception_message="connection timed out"),
    )
    second = run_v191_offline_oms_rehearsal(
        _packet(execution_plan_id="daily_execution_plan_v191_new_plan"),
        output_root=root,
    )

    assert first["oms_classification"] == "unresolved_order_outcome"
    assert first["fake_submit_call_count"] == 1
    assert first["fake_cancel_call_count"] == 0
    assert second["oms_classification"] == "blocked_unresolved_prior_mutation"
    assert second["fake_submit_call_count"] == 0
    assert second["unresolved_prior_status"] == "blocked_unresolved_prior_mutation"
    _assert_real_and_authorization_flags_false(second)


def test_crash_restart_after_submit_recovers_without_duplicate_submit(
    tmp_path: Path,
) -> None:
    packet = _packet()
    root = tmp_path / "run"
    client_order_id = deterministic_client_order_id(packet)
    oms_root = root / "oms"
    oms_root.mkdir(parents=True)
    _write_crash_lifecycle(oms_root, client_order_id)
    broker_order = _order(client_order_id=client_order_id, status="accepted")

    result = run_v191_offline_oms_rehearsal(
        packet,
        output_root=root,
        fixture=OfflineOmsFixture(open_orders=(broker_order,), all_orders=(broker_order,)),
    )

    assert result["oms_classification"] == "submitted_cancel_confirmed"
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 1
    assert result["reconciled_lifecycle_state"]["restart_recovery_performed"] is True
    _assert_real_and_authorization_flags_false(result)


def test_cancel_ambiguity_reconciliation_is_represented(tmp_path: Path) -> None:
    result = run_v191_offline_oms_rehearsal(
        _packet(),
        output_root=tmp_path / "run",
        fixture=OfflineOmsFixture(
            cancel_exception_message="cancel response lost",
            cancel_status_on_exception="canceled",
        ),
    )

    assert result["oms_classification"] == "cancel_ambiguous_reconciled"
    assert result["fake_submit_call_count"] == 1
    assert result["fake_cancel_call_count"] == 1
    assert result["oms_latest"]["reconciliation"]["cancel_ambiguous"] is True
    _assert_real_and_authorization_flags_false(result)


def test_broker_local_divergence_blocks_rehearsal(tmp_path: Path) -> None:
    packet = _packet()
    root = tmp_path / "run"
    first = run_v191_offline_oms_rehearsal(packet, output_root=root)
    broker_order = _order(
        client_order_id=first["client_order_id"],
        status="accepted",
    )

    second = run_v191_offline_oms_rehearsal(
        packet,
        output_root=root,
        fixture=OfflineOmsFixture(all_orders=(broker_order,)),
    )

    assert first["oms_classification"] == "submitted_cancel_confirmed"
    assert second["oms_classification"] == "blocked_broker_local_divergence"
    assert second["fake_submit_call_count"] == 0
    assert second["blocker"] == "blocked_broker_local_divergence"
    _assert_real_and_authorization_flags_false(second)


def test_existing_spy_open_order_blocks_before_fake_submit(tmp_path: Path) -> None:
    result = run_v191_offline_oms_rehearsal(
        _packet(),
        output_root=tmp_path / "run",
        fixture=OfflineOmsFixture(
            open_orders=(_order(client_order_id="other-client-id", status="accepted"),),
            all_orders=(_order(client_order_id="other-client-id", status="accepted"),),
        ),
    )

    assert result["oms_classification"] == "blocked_open_order_present"
    assert result["fake_submit_call_count"] == 0
    _assert_real_and_authorization_flags_false(result)


def test_unexpected_non_spy_position_blocks_before_fake_submit(tmp_path: Path) -> None:
    result = run_v191_offline_oms_rehearsal(
        _packet(),
        output_root=tmp_path / "run",
        fixture=OfflineOmsFixture(positions=(_spy_position(), _position("MSFT"))),
    )

    assert result["oms_classification"] == "blocked_unexpected_position"
    assert result["fake_submit_call_count"] == 0
    _assert_real_and_authorization_flags_false(result)


def test_lock_contention_blocks_and_invokes_no_fake_mutation(tmp_path: Path) -> None:
    root = tmp_path / "run"
    oms_root = root / "oms"
    oms_root.mkdir(parents=True)
    (oms_root / ".mutation.lock").write_text("locked", encoding="utf-8")

    result = run_v191_offline_oms_rehearsal(_packet(), output_root=root)

    assert result["oms_classification"] == "blocked_lock_contention"
    assert result["classification_aliases"] == ["blocked_process_lock"]
    assert result["fake_submit_call_count"] == 0
    assert result["fake_cancel_call_count"] == 0
    _assert_real_and_authorization_flags_false(result)


def test_packet_fields_agree_with_execution_plan_and_oms_result(tmp_path: Path) -> None:
    packet = _packet()

    result = run_v191_offline_oms_rehearsal(packet, output_root=tmp_path / "run")

    assert result["as_of_date"] == packet["as_of_date"]
    assert result["symbol"] == packet["execution_plan"]["execution_plan_symbol"]
    assert result["preview_decision"] == (
        packet["execution_plan"]["execution_plan_source_preview_decision"]
    )
    assert result["execution_plan_id"] == packet["execution_plan"]["execution_plan_id"]
    assert result["execution_plan_digest"] == deterministic_execution_plan_digest(packet)
    assert result["client_order_id"] == deterministic_client_order_id(packet)
    assert result["execution_mode"] == OFFLINE_OMS_REHEARSAL_MODE
    assert result["broker_state_mode"] == OFFLINE_FIXTURE_BROKER_STATE_MODE
    assert result["oms_classification"] == "submitted_cancel_confirmed"
    assert "paper_lab_only" in result["safety_labels"]
    assert "offline_only" in result["safety_labels"]
    assert "not_live_authorized" in result["safety_labels"]
    assert "profit_claim=none" in result["safety_labels"]
    assert "paper_submit_authorized=false" in result["safety_labels"]
    for artifact_path in result["artifact_paths"].values():
        assert Path(artifact_path).exists()
    _assert_real_and_authorization_flags_false(result)


def test_new_runner_exposes_no_real_alpaca_sdk_client_selection() -> None:
    signature = inspect.signature(run_v191_offline_oms_rehearsal)
    source = inspect.getsource(rehearsal_module)

    assert "client" not in signature.parameters
    assert "broker_client" not in signature.parameters
    assert "AlpacaSdkClient" not in source
    assert "alpaca_sdk_client" not in source


def test_runs_directory_is_ignored_for_runtime_artifacts() -> None:
    assert "runs/" in Path(".gitignore").read_text(encoding="utf-8").splitlines()


def _packet(
    *,
    action: str = "buy_preview",
    status: str = "preview_only",
    requires_approval: bool = True,
    execution_plan_id: str = "daily_execution_plan_v191_unit",
) -> dict[str, object]:
    packet = deepcopy(sample_daily_execution_plan_packet())
    plan = packet["execution_plan"]
    plan["execution_plan_id"] = execution_plan_id
    plan["execution_plan_status"] = status
    plan["execution_plan_action"] = action
    plan["execution_plan_source_preview_decision"] = action
    plan["execution_plan_requires_approval"] = requires_approval
    plan["execution_plan_reason"] = (
        f"{action}_requires_explicit_authorization"
        if action in {"buy_preview", "sell_preview"}
        else "existing_spy_position_satisfies_risk_on_preview"
    )
    plan["execution_plan_blocker"] = "none"
    packet["preview_decision"] = action
    return packet


def _assert_real_and_authorization_flags_false(result: dict[str, object]) -> None:
    assert result["paper_submit_authorized"] is False
    assert result["paper_submit_performed"] is False
    assert result["real_broker_read_performed"] is False
    assert result["real_broker_mutation_performed"] is False
    assert result["broker_mutation_performed"] is False
    assert result["oms_latest"]["paper_submit_authorized"] is False
    assert result["oms_latest"]["paper_submit_performed"] is False
    assert result["oms_latest"]["real_broker_read_performed"] is False
    assert result["oms_latest"]["real_broker_mutation_performed"] is False


def _write_crash_lifecycle(oms_root: Path, client_order_id: str) -> None:
    event = {
        "event_type": "submit_attempt",
        "client_order_id": client_order_id,
        "observed_at": datetime(2026, 6, 24, 15, 30, tzinfo=UTC).isoformat(),
    }
    (oms_root / "order_lifecycle.jsonl").write_text(
        json.dumps(event, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
