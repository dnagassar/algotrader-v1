from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import socket

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.cancellation_reconciliation import (
    CancellationReconciliationIdentity,
)
from algotrader.execution.order_journal import (
    CancelIntent,
    CancelJournalState,
    OrderReservation,
    SqliteOrderJournal,
)
from algotrader.execution.paper_cancellation_observation import (
    PAPER_CANCELLATION_OBSERVATION_MODE,
    PAPER_CANCELLATION_OBSERVATION_OPERATION,
    build_paper_cancellation_observation_authorization,
)
from algotrader.execution.paper_cancellation_reconciliation_local import (
    paper_cancellation_reconciliation_local_target_blocker,
)
from algotrader.execution.paper_cancellation_reconciliation_readiness import (
    PaperCancellationReconciliationReadinessRequest,
    PaperCancellationReconciliationReadinessStatus,
    build_exact_paper_cancellation_reconciliation_readiness,
    main,
)


NOW = datetime(2026, 7, 14, 14, 0, tzinfo=UTC)
EXPECTED_ACCOUNT_ID = "readiness-expected-account"
SENSITIVE_VALUE = "readiness-sensitive-value-never-render"


def _authorization(**changes: object):
    values: dict[str, object] = {
        "mode": PAPER_CANCELLATION_OBSERVATION_MODE,
        "operation": PAPER_CANCELLATION_OBSERVATION_OPERATION,
        "cancel_intent_id": "cancel-intent-1",
        "client_order_id": "client-order-1",
        "broker_order_id": "broker-order-1",
        "issued_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "authorized": True,
    }
    values.update(changes)
    return build_paper_cancellation_observation_authorization(**values)


def _write_authorization(path: Path, authorization: object | None = None) -> object:
    resolved = _authorization() if authorization is None else authorization
    path.write_text(
        json.dumps(resolved.to_dict(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return resolved


def _request(
    authorization_path: Path,
    journal_path: Path,
    *,
    authorization: object | None = None,
    **changes: object,
) -> PaperCancellationReconciliationReadinessRequest:
    resolved = _authorization() if authorization is None else authorization
    values: dict[str, object] = {
        "authorization_artifact_path": authorization_path,
        "journal_path": journal_path,
        "cancel_intent_id": "cancel-intent-1",
        "client_order_id": "client-order-1",
        "broker_order_id": "broker-order-1",
        "expected_authorization_id": resolved.authorization_id,
        "occurred_at": NOW + timedelta(seconds=10),
        "expected_account_id": EXPECTED_ACCOUNT_ID,
        "offline_readiness_permitted": True,
    }
    values.update(changes)
    return PaperCancellationReconciliationReadinessRequest(**values)


def _seed_order(path: Path) -> SqliteOrderJournal:
    journal = SqliteOrderJournal(path)
    journal.reserve(
        OrderReservation(
            client_order_id="client-order-1",
            execution_plan_id="plan-1",
            run_id="order-run-1",
            symbol="BTCUSD",
            side="buy",
            quantity=None,
            notional="25",
        ),
        NOW,
    )
    journal.record_broker_observation(
        "client-order-1",
        NOW + timedelta(seconds=1),
        broker_order_id="broker-order-1",
        broker_status="accepted",
        filled_quantity="0",
    )
    return journal


def _seed_unresolved(
    path: Path,
    *,
    reconciliation_ready: bool = True,
) -> SqliteOrderJournal:
    journal = _seed_order(path)
    journal.reserve_cancel_intent(
        CancelIntent(
            cancel_intent_id="cancel-intent-1",
            client_order_id="client-order-1",
            broker_order_id="broker-order-1",
            run_id="cancel-run-1",
            reason="stale_open_order",
        ),
        NOW + timedelta(seconds=2),
    )
    if not reconciliation_ready:
        return journal
    lease = journal.acquire_runtime_lease(
        lease_name="cancel-worker",
        owner_run_id="cancel-run-1",
        occurred_at=NOW + timedelta(seconds=2),
        ttl_seconds=60,
        lease_token="lease-token-1",
    )
    journal.claim_pre_mutation_cancel(
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
        reservation_run_id="cancel-run-1",
        lease_name=lease.lease_name,
        lease_owner_run_id=lease.owner_run_id,
        lease_token=lease.lease_token,
        fencing_generation=lease.fencing_generation,
        cancel_allowed=True,
        snapshot_fresh=True,
        occurred_at=NOW + timedelta(seconds=3),
    )
    journal.release_runtime_lease(
        lease_name=lease.lease_name,
        owner_run_id=lease.owner_run_id,
        lease_token=lease.lease_token,
    )
    journal.mark_cancel_ambiguous(
        "cancel-intent-1",
        NOW + timedelta(seconds=4),
        reason="timeout_without_response",
    )
    return journal


def test_default_readiness_blocks_before_artifact_or_journal_access(
    tmp_path: Path,
) -> None:
    request = _request(
        tmp_path / "missing-authorization.json",
        tmp_path / "missing.sqlite3",
        offline_readiness_permitted=False,
    )

    result = build_exact_paper_cancellation_reconciliation_readiness(request)

    assert result.status is PaperCancellationReconciliationReadinessStatus.BLOCKED
    assert result.blocker == "offline_readiness_not_permitted"
    assert result.authorization_artifact_loaded is False
    assert result.journal_path_checked is False
    assert result.local_target_checked is False
    assert not request.authorization_artifact_path.exists()
    assert not request.journal_path.exists()


def test_invalid_artifact_is_sanitized_before_journal_access(tmp_path: Path) -> None:
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(SENSITIVE_VALUE, encoding="utf-8")

    result = build_exact_paper_cancellation_reconciliation_readiness(
        _request(authorization_path, tmp_path / "missing.sqlite3")
    )

    assert result.blocker == "authorization_artifact_invalid"
    assert result.authorization_artifact_loaded is False
    assert result.journal_path_checked is False
    assert SENSITIVE_VALUE not in str(result.to_dict())


@pytest.mark.parametrize(
    ("authorization_changes", "request_changes", "expected_blocker"),
    [
        ({"authorized": False}, {}, "authorization_not_granted"),
        ({"mode": "live"}, {}, "authorization_mode_mismatch"),
        ({"operation": "different-operation"}, {}, "authorization_operation_mismatch"),
        ({}, {"expected_authorization_id": "different-auth"}, "authorization_id_mismatch"),
        (
            {},
            {"occurred_at": NOW - timedelta(seconds=1)},
            "authorization_not_yet_valid",
        ),
        (
            {},
            {"occurred_at": NOW + timedelta(minutes=5)},
            "authorization_expired",
        ),
        ({}, {"cancel_intent_id": "different-cancel"}, "cancel_intent_id_mismatch"),
        ({}, {"client_order_id": "different-client"}, "client_order_id_mismatch"),
        ({}, {"broker_order_id": "different-broker"}, "broker_order_id_mismatch"),
    ],
)
def test_authorization_and_identity_blockers_precede_journal_access(
    tmp_path: Path,
    authorization_changes: dict[str, object],
    request_changes: dict[str, object],
    expected_blocker: str,
) -> None:
    authorization = _authorization(**authorization_changes)
    authorization_path = tmp_path / "authorization.json"
    _write_authorization(authorization_path, authorization)

    result = build_exact_paper_cancellation_reconciliation_readiness(
        _request(
            authorization_path,
            tmp_path / "missing.sqlite3",
            authorization=authorization,
            **request_changes,
        )
    )

    assert result.blocker == expected_blocker
    assert result.authorization_artifact_loaded is True
    assert result.authorization_evidence_checked is True
    assert result.authorization_evidence_matched is False
    assert result.journal_path_checked is False


def test_missing_journal_and_exact_local_records_fail_closed(tmp_path: Path) -> None:
    authorization_path = tmp_path / "authorization.json"
    _write_authorization(authorization_path)

    missing = build_exact_paper_cancellation_reconciliation_readiness(
        _request(authorization_path, tmp_path / "missing.sqlite3")
    )
    assert missing.blocker == "local_journal_path_missing"
    assert missing.authorization_evidence_matched is True
    assert missing.journal_path_checked is True
    assert missing.local_target_checked is False

    empty_path = tmp_path / "empty.sqlite3"
    empty_path.touch()
    empty = build_exact_paper_cancellation_reconciliation_readiness(
        _request(authorization_path, empty_path)
    )
    assert empty.blocker == "order_journal_record_missing"
    assert empty.local_target_checked is True

    order_only_path = tmp_path / "order-only.sqlite3"
    _seed_order(order_only_path)
    order_only = build_exact_paper_cancellation_reconciliation_readiness(
        _request(authorization_path, order_only_path)
    )
    assert order_only.blocker == "cancel_intent_missing"

    reserved_path = tmp_path / "reserved.sqlite3"
    _seed_unresolved(reserved_path, reconciliation_ready=False)
    reserved = build_exact_paper_cancellation_reconciliation_readiness(
        _request(authorization_path, reserved_path)
    )
    assert reserved.blocker == "cancel_intent_not_reconciliation_ready"


def test_shared_local_check_covers_exact_identity_terminal_and_state_rules(
    tmp_path: Path,
) -> None:
    journal = _seed_unresolved(tmp_path / "orders.sqlite3")
    order = journal.get("client-order-1")
    cancel = journal.get_cancel_intent("cancel-intent-1")
    assert order is not None and cancel is not None
    identity = CancellationReconciliationIdentity(
        cancel_intent_id="cancel-intent-1",
        client_order_id="client-order-1",
        broker_order_id="broker-order-1",
    )

    assert (
        paper_cancellation_reconciliation_local_target_blocker(
            identity,
            order_record=order,
            cancel_record=cancel,
        )
        == ""
    )
    assert (
        paper_cancellation_reconciliation_local_target_blocker(
            identity,
            order_record=replace(order, broker_order_id="different-broker"),
            cancel_record=cancel,
        )
        == "order_broker_identity_mismatch"
    )
    assert (
        paper_cancellation_reconciliation_local_target_blocker(
            identity,
            order_record=order,
            cancel_record=replace(cancel, client_order_id="different-client"),
        )
        == "cancel_client_order_identity_mismatch"
    )
    assert (
        paper_cancellation_reconciliation_local_target_blocker(
            identity,
            order_record=order,
            cancel_record=replace(cancel, broker_order_id="different-broker"),
        )
        == "cancel_broker_order_identity_mismatch"
    )
    assert (
        paper_cancellation_reconciliation_local_target_blocker(
            identity,
            order_record=order,
            cancel_record=replace(cancel, state=CancelJournalState.CANCELED),
        )
        == "cancel_intent_already_terminal"
    )
    assert (
        paper_cancellation_reconciliation_local_target_blocker(
            identity,
            order_record=order,
            cancel_record=replace(cancel, state=CancelJournalState.RESERVED),
        )
        == "cancel_intent_not_reconciliation_ready"
    )


def test_unavailable_journal_error_is_sanitized(tmp_path: Path) -> None:
    authorization_path = tmp_path / "authorization.json"
    journal_path = tmp_path / "orders.sqlite3"
    _write_authorization(authorization_path)
    journal_path.write_text(SENSITIVE_VALUE, encoding="utf-8")

    result = build_exact_paper_cancellation_reconciliation_readiness(
        _request(authorization_path, journal_path)
    )

    assert result.blocker == "local_journal_unavailable"
    assert result.error_type == "DatabaseError"
    assert SENSITIVE_VALUE not in str(result.to_dict())


@pytest.mark.parametrize(
    "field_name",
    ["authorization_artifact_path", "journal_path"],
)
def test_request_rejects_network_filesystem_paths(
    tmp_path: Path,
    field_name: str,
) -> None:
    network_path = r"\\server\share\artifact"
    authorization_path = (
        network_path
        if field_name == "authorization_artifact_path"
        else tmp_path / "authorization.json"
    )
    journal_path = (
        network_path
        if field_name == "journal_path"
        else tmp_path / "journal.sqlite3"
    )
    with pytest.raises(ValidationError):
        _request(authorization_path, journal_path)


def test_ready_receipt_is_offline_read_only_and_preserves_all_local_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_path = tmp_path / "authorization.json"
    journal_path = tmp_path / "orders.sqlite3"
    _write_authorization(authorization_path)
    journal = _seed_unresolved(journal_path)
    paused = journal.set_runtime_control(
        trading_enabled=False,
        stop_requested=True,
        reason="operator_pause",
        occurred_at=NOW + timedelta(seconds=5),
    )
    before = (
        journal.get("client-order-1"),
        journal.get_cancel_intent("cancel-intent-1"),
        journal.get_runtime_control(),
    )

    def blocked_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("network access is forbidden in this test")

    monkeypatch.setattr(socket, "socket", blocked_socket)
    result = build_exact_paper_cancellation_reconciliation_readiness(
        _request(authorization_path, journal_path)
    )

    assert result.status is PaperCancellationReconciliationReadinessStatus.READY
    assert result.blocker == ""
    assert result.order_state == "accepted"
    assert result.cancel_intent_state == "unknown"
    assert (
        journal.get("client-order-1"),
        journal.get_cancel_intent("cancel-intent-1"),
        journal.get_runtime_control(),
    ) == before
    assert journal.get_runtime_control() == paused

    payload = result.to_dict()
    assert payload["offline_inputs_ready"] is True
    assert payload["ready_for_exact_read_command"] is True
    assert payload["all_exact_read_preconditions_verified"] is False
    assert payload["external_operator_gates_satisfied"] is False
    assert payload["expected_account_verified"] is False
    for field_name in (
        "authorization_minted",
        "paper_configuration_loaded",
        "environment_read",
        "credentials_accessed",
        "credential_values_serialized",
        "network_access_authorized",
        "network_accessed",
        "broker_client_constructed",
        "broker_read_authorized",
        "broker_read_performed",
        "operator_binding_authorized",
        "operator_binding_invoked",
        "local_journal_updated",
        "runtime_control_changed",
        "retry_permitted",
        "safe_to_recancel",
        "target_selection_performed",
        "unresolved_intents_enumerated",
        "polling_performed",
        "broker_mutation_authorized",
        "broker_mutation_performed",
        "submit_attempted",
        "cancel_attempted",
        "replace_attempted",
        "close_attempted",
        "liquidation_attempted",
        "live_authorized",
    ):
        assert payload[field_name] is False
    assert EXPECTED_ACCOUNT_ID not in str(payload)


def test_request_requires_account_hides_it_and_exposes_no_active_capability(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError):
        _request(
            tmp_path / "authorization.json",
            tmp_path / "journal.sqlite3",
            expected_account_id="",
        )

    request = _request(
        tmp_path / "authorization.json",
        tmp_path / "journal.sqlite3",
        offline_readiness_permitted=False,
    )
    result = build_exact_paper_cancellation_reconciliation_readiness(request)
    assert EXPECTED_ACCOUNT_ID not in repr(request)
    assert EXPECTED_ACCOUNT_ID not in repr(result)
    with pytest.raises(FrozenInstanceError):
        result.blocker = "changed"  # type: ignore[misc]
    for capability in (
        "submit_order",
        "cancel_order",
        "replace_order",
        "close_position",
        "liquidate",
        "get_account",
        "get_order_by_id",
        "get_orders",
        "unresolved_cancel_intents",
        "retry",
    ):
        assert not hasattr(result, capability)


def test_main_sanitizes_invalid_request_without_any_access(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "--authorization-artifact",
            "missing.json",
            "--journal-path",
            "missing.sqlite3",
            "--cancel-intent-id",
            "cancel-intent-1",
            "--client-order-id",
            "client-order-1",
            "--broker-order-id",
            " ",
            "--expected-authorization-id",
            "authorization-1",
            "--expected-paper-account-id",
            EXPECTED_ACCOUNT_ID,
            "--occurred-at",
            (NOW + timedelta(seconds=10)).isoformat(),
        ]
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "invalid_request"
    assert payload["environment_read"] is False
    assert payload["broker_read_performed"] is False
    assert EXPECTED_ACCOUNT_ID not in str(payload)
