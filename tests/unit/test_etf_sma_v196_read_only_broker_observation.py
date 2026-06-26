import json
from pathlib import Path

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.execution.etf_sma_v195_bounded_paper_drill_approval_packet import (
    APPROVAL_PACKET_READY_NO_MUTATION,
    V195_PACKET_VERSION,
)
from algotrader.execution.etf_sma_v196_read_only_broker_observation import (
    PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE,
    PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_MISSING,
    PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_NOT_READY,
    PAPER_OBSERVATION_BLOCKED_BROKER_READ_SCOPE_VIOLATION,
    PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS,
    PAPER_OBSERVATION_BLOCKED_CREDENTIALS_UNAVAILABLE,
    PAPER_OBSERVATION_BLOCKED_DUPLICATE_CLIENT_ORDER_ID,
    PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH,
    PAPER_OBSERVATION_BLOCKED_LIVE_ENDPOINT_OR_PROFILE,
    PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT,
    PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION,
    PAPER_OBSERVATION_ELIGIBLE,
    extract_projected_future_paper_request_fields,
    locate_latest_v195_approval_packet,
    run_v196_read_only_broker_observation,
)


GENERATED_AT = "2026-06-25T12:00:00+00:00"
CLIENT_ORDER_ID = "v195-spy-buy-market-day-20260625"
EXPECTED_ACCOUNT_ID = "expected-paper-account-id"
EXPECTED_ACCOUNT_NUMBER = "paper-account-number"

_REQUIRED_ACCOUNT_AUDIT_FIELDS = (
    "observed_account_id_present",
    "observed_account_number_present",
    "expected_account_configured",
    "expected_account_id_matched",
    "expected_account_number_matched",
    "expected_account_matched",
    "expected_account_match_mode",
    "expected_account_blocker",
)
_EXPECTED_ACCOUNT_CHECK_FIELDS = tuple(
    field
    for field in _REQUIRED_ACCOUNT_AUDIT_FIELDS
    if field != "expected_account_blocker"
)


class _AccountStatusActive:
    def __str__(self) -> str:
        return "AccountStatus.ACTIVE"



def test_eligible_observation_writes_required_artifacts(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client()
    output_root = tmp_path / "runs" / "paper_lab" / "v196"

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=output_root,
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == PAPER_OBSERVATION_ELIGIBLE
    assert packet["broker_read_performed"] is True
    assert packet["broker_mutation_performed"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["paper_cancel_performed"] is False
    assert packet["live_read_performed"] is False
    assert packet["live_mutation_performed"] is False
    assert packet["paper_account_attestation"] == {
        "account_mode": "paper",
        "profile_is_paper": True,
        "profile_attestation": "paper",
        "endpoint_family": "paper",
        "endpoint_host_attestation": "paper-api.alpaca.markets",
        "paper_endpoint_detected": True,
        "live_endpoint_detected": False,
        "credentials_available": True,
        "credential_values_exposed": False,
    }
    _assert_expected_account_audit(
        packet,
        observed_account_id_present=True,
        observed_account_number_present=True,
        expected_account_configured=True,
        expected_account_id_matched=True,
        expected_account_number_matched=False,
        expected_account_matched=True,
        expected_account_match_mode="account_id",
        expected_account_blocker="none",
    )
    rendered = json.dumps(packet, sort_keys=True)
    assert EXPECTED_ACCOUNT_ID not in rendered
    assert EXPECTED_ACCOUNT_NUMBER not in rendered
    assert packet["paper_account_status"] == {
        "observed": True,
        "status": "ACTIVE",
        "trading_blocked": False,
        "account_blocked": False,
        "trade_suspended_by_user": False,
    }
    assert packet["account_status"] == "ACTIVE"
    assert packet["account_trading_blocked"] is False
    assert packet["account_blocked"] is False
    assert packet["account_tradable"] is True
    assert packet["account_blocker"] == "none"
    assert packet["projected_future_paper_request_fields"] == {
        "symbol": "SPY",
        "side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": "1.00",
        "quantity": "",
        "deterministic_client_order_id": CLIENT_ORDER_ID,
        "client_order_id": CLIENT_ORDER_ID,
        "cap": {
            "maximum_notional": "1.00",
            "maximum_quantity": "",
            "maximum_notional_or_quantity": "1.00",
            "maximum_notional_or_quantity_kind": "notional",
            "source": "operator_test_cap",
        },
    }
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
    ]
    _assert_artifacts(output_root, packet)
    _assert_no_authority(packet)


def test_expected_account_number_match_passes_with_account_number_mode(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client()

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_NUMBER,
    )

    assert packet["eligibility_classification"] == PAPER_OBSERVATION_ELIGIBLE
    _assert_expected_account_audit(
        packet,
        observed_account_id_present=True,
        observed_account_number_present=True,
        expected_account_configured=True,
        expected_account_id_matched=False,
        expected_account_number_matched=True,
        expected_account_matched=True,
        expected_account_match_mode="account_number",
        expected_account_blocker="none",
    )
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
    ]
    rendered = json.dumps(packet, sort_keys=True)
    assert EXPECTED_ACCOUNT_ID not in rendered
    assert EXPECTED_ACCOUNT_NUMBER not in rendered
    _assert_no_authority(packet)


def test_open_spy_order_blocks_separate_drill_authorization(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        open_orders=(
            {
                "id": "open-order-1",
                "client_order_id": "other-client-order",
                "symbol": "SPY",
                "side": "buy",
                "status": "accepted",
                "type": "market",
                "time_in_force": "day",
            },
        ),
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT
    )
    assert packet["blocker"] == "open_spy_order_present"
    assert packet["open_spy_order_observed"] is True
    assert packet["open_spy_order_summary"] == [
        {
            "order_id": "open-order-1",
            "client_order_id": "other-client-order",
            "symbol": "SPY",
            "side": "buy",
            "status": "accepted",
            "order_type": "market",
            "time_in_force": "day",
        }
    ]
    _assert_no_authority(packet)


def test_unexpected_non_spy_position_blocks(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        positions=({"symbol": "MSFT", "qty": "2", "market_value": "700"},),
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION
    )
    assert packet["blocker"] == "unexpected_non_spy_position"
    assert packet["unexpected_non_spy_position_observed"] is True
    assert packet["unexpected_non_spy_position_summary"] == [
        {"symbol": "MSFT", "quantity": "2", "notional": "700"}
    ]
    _assert_no_authority(packet)


def test_duplicate_client_order_id_blocks(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        recent_orders=(
            {
                "id": "recent-order-1",
                "client_order_id": CLIENT_ORDER_ID,
                "symbol": "SPY",
                "side": "buy",
                "status": "filled",
                "type": "market",
                "time_in_force": "day",
            },
        ),
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_DUPLICATE_CLIENT_ORDER_ID
    )
    assert packet["blocker"] == "duplicate_client_order_id"
    assert packet["duplicate_client_order_id_observed"] is True
    assert packet["duplicate_client_order_id_summary"] == [
        {
            "order_id": "recent-order-1",
            "client_order_id": CLIENT_ORDER_ID,
            "symbol": "SPY",
            "side": "buy",
            "status": "filled",
            "order_type": "market",
            "time_in_force": "day",
        }
    ]
    _assert_no_authority(packet)


def test_expected_account_mismatch_blocks_without_exposing_account_id(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        account={
            "account_id": "different-account",
            "account_number": "different-number",
        }
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    rendered = json.dumps(packet, sort_keys=True)
    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH
    )
    assert packet["blocker"] == "expected_account_mismatch"
    _assert_expected_account_audit(
        packet,
        observed_account_id_present=True,
        observed_account_number_present=True,
        expected_account_configured=True,
        expected_account_id_matched=False,
        expected_account_number_matched=False,
        expected_account_matched=False,
        expected_account_match_mode="none",
        expected_account_blocker="expected_account_mismatch",
    )
    assert EXPECTED_ACCOUNT_ID not in rendered
    assert EXPECTED_ACCOUNT_NUMBER not in rendered
    assert "different-account" not in rendered
    assert "different-number" not in rendered
    _assert_no_authority(packet)


def test_expected_account_not_configured_fails_closed_before_broker_build(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH
    )
    assert packet["blocker"] == "expected_paper_account_id_not_configured"
    assert packet["broker_read_performed"] is False
    _assert_expected_account_audit(
        packet,
        observed_account_id_present=False,
        observed_account_number_present=False,
        expected_account_configured=False,
        expected_account_id_matched=None,
        expected_account_number_matched=None,
        expected_account_matched=None,
        expected_account_match_mode="none",
        expected_account_blocker="expected_paper_account_id_not_configured",
    )
    assert packet["account_tradable"] is False
    assert packet["account_blocker"] == "account_not_observed"
    _assert_no_authority(packet)


def test_account_status_active_enum_with_unblocked_flags_is_tradable(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(account={"status": _AccountStatusActive()})

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == PAPER_OBSERVATION_ELIGIBLE
    assert packet["account_status"] == "AccountStatus.ACTIVE"
    assert packet["account_trading_blocked"] is False
    assert packet["account_blocked"] is False
    assert packet["account_tradable"] is True
    assert packet["account_blocker"] == "none"
    _assert_no_authority(packet)


def test_non_active_account_status_blocks(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        account={"account_id": EXPECTED_ACCOUNT_ID, "status": "INACTIVE"}
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE
    )
    assert packet["blocker"] == "account_not_tradable_or_blocked"
    assert packet["account_tradable"] is False
    assert packet["account_blocker"] == "account_status_not_active"
    _assert_no_authority(packet)


def test_trading_blocked_account_blocks(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(account={"trading_blocked": True})

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE
    )
    assert packet["blocker"] == "account_not_tradable_or_blocked"
    assert packet["account_trading_blocked"] is True
    assert packet["account_tradable"] is False
    assert packet["account_blocker"] == "account_trading_blocked"
    _assert_no_authority(packet)


def test_account_blocked_flag_blocks(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(account={"account_blocked": True})

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE
    )
    assert packet["blocker"] == "account_not_tradable_or_blocked"
    assert packet["account_blocked"] is True
    assert packet["account_tradable"] is False
    assert packet["account_blocker"] == "account_blocked"
    _assert_no_authority(packet)


def test_classification_priority_checks_expected_account_before_account_and_broker_state(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        account={
            "account_id": "different-account",
            "status": "INACTIVE",
            "trading_blocked": True,
            "account_blocked": True,
        },
        positions=({"symbol": "MSFT", "qty": "1", "market_value": "350"},),
        open_orders=({"id": "open-order-1", "symbol": "SPY"},),
        recent_orders=(
            {"id": "recent-order-1", "client_order_id": CLIENT_ORDER_ID, "symbol": "SPY"},
        ),
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_EXPECTED_ACCOUNT_MISMATCH
    )
    assert packet["blocker"] == "expected_account_mismatch"
    _assert_no_authority(packet)


def test_classification_priority_checks_account_before_order_position_and_duplicate(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        account={"status": "INACTIVE"},
        positions=({"symbol": "MSFT", "qty": "1", "market_value": "350"},),
        open_orders=({"id": "open-order-1", "symbol": "SPY"},),
        recent_orders=(
            {"id": "recent-order-1", "client_order_id": CLIENT_ORDER_ID, "symbol": "SPY"},
        ),
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_ACCOUNT_NOT_TRADABLE
    )
    assert packet["blocker"] == "account_not_tradable_or_blocked"
    assert packet["account_blocker"] == "account_status_not_active"
    _assert_no_authority(packet)


def test_classification_priority_checks_open_spy_order_before_position_and_duplicate(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        positions=({"symbol": "MSFT", "qty": "1", "market_value": "350"},),
        open_orders=({"id": "open-order-1", "symbol": "SPY"},),
        recent_orders=(
            {"id": "recent-order-1", "client_order_id": CLIENT_ORDER_ID, "symbol": "SPY"},
        ),
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_OPEN_SPY_ORDER_PRESENT
    )
    assert packet["blocker"] == "open_spy_order_present"
    _assert_no_authority(packet)


def test_classification_priority_checks_unexpected_position_before_duplicate(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(
        positions=({"symbol": "MSFT", "qty": "1", "market_value": "350"},),
        recent_orders=(
            {"id": "recent-order-1", "client_order_id": CLIENT_ORDER_ID, "symbol": "SPY"},
        ),
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_UNEXPECTED_NON_SPY_POSITION
    )
    assert packet["blocker"] == "unexpected_non_spy_position"
    _assert_no_authority(packet)

def test_live_profile_or_endpoint_blocks_before_broker_build(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env={
            **_paper_env(),
            "APP_PROFILE": "live",
            "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
        },
        broker_client_factory=_forbidden_factory,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_LIVE_ENDPOINT_OR_PROFILE
    )
    assert packet["broker_read_performed"] is False
    assert packet["paper_account_attestation"]["live_endpoint_detected"] is True
    _assert_no_authority(packet)


def test_missing_credentials_blocks_before_broker_build(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env={
            "APP_PROFILE": "paper",
            "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
        },
        broker_client_factory=_forbidden_factory,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_CREDENTIALS_UNAVAILABLE
    )
    assert packet["broker_read_performed"] is False
    _assert_no_authority(packet)


def test_broker_read_failure_blocks_ambiguous_without_retry(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(tmp_path)
    fake_client = FakeV196Client(fail_on="recent_orders")

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_factory(fake_client),
        expected_paper_account_id=EXPECTED_ACCOUNT_ID,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_BROKER_RESPONSE_AMBIGUOUS
    )
    assert packet["blocker"] == "broker_response_ambiguous"
    assert packet["unavailable_observations"] == ["recent_client_order_id_lookup"]
    assert fake_client.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
    ]
    _assert_no_authority(packet)


def test_missing_approval_packet_blocks_without_broker_build(tmp_path: Path) -> None:
    packet = run_v196_read_only_broker_observation(
        approval_packet_path=tmp_path / "missing" / "approval_packet.json",
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_MISSING
    )
    assert packet["broker_read_performed"] is False
    _assert_no_authority(packet)


def test_not_ready_approval_packet_blocks_without_broker_build(tmp_path: Path) -> None:
    approval_path = _write_approval_packet(
        tmp_path,
        approval_packet_classification="approval_packet_blocked_broker_state_required",
    )

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_APPROVAL_PACKET_NOT_READY
    )
    assert packet["broker_read_performed"] is False
    _assert_no_authority(packet)


def test_non_spy_projected_symbol_blocks_scope_before_broker_build(
    tmp_path: Path,
) -> None:
    approval_path = _write_approval_packet(tmp_path, symbol="MSFT")

    packet = run_v196_read_only_broker_observation(
        approval_packet_path=approval_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v196",
        timestamp=GENERATED_AT,
        env=_paper_env(),
        broker_client_factory=_forbidden_factory,
    )

    assert packet["eligibility_classification"] == (
        PAPER_OBSERVATION_BLOCKED_BROKER_READ_SCOPE_VIOLATION
    )
    assert packet["blocker"] == "projected_symbol_outside_authorized_spy_scope"
    assert packet["broker_read_performed"] is False
    _assert_no_authority(packet)


def test_extract_projected_request_fields_and_locate_latest(tmp_path: Path) -> None:
    older = _write_approval_packet(tmp_path / "older", timestamp="2026-06-24T00:00:00+00:00")
    newer = _write_approval_packet(tmp_path / "newer", timestamp="2026-06-25T00:00:00+00:00")

    assert locate_latest_v195_approval_packet(tmp_path) == newer
    fields = extract_projected_future_paper_request_fields(
        json.loads(older.read_text(encoding="utf-8"))
    )

    assert fields["symbol"] == "SPY"
    assert fields["side"] == "buy"
    assert fields["order_type"] == "market"
    assert fields["time_in_force"] == "day"
    assert fields["client_order_id"] == CLIENT_ORDER_ID
    assert fields["cap"]["maximum_notional_or_quantity"] == "1.00"


class FakeV196Client:
    def __init__(
        self,
        *,
        account: dict[str, object] | None = None,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        recent_orders: tuple[dict[str, object], ...] = (),
        fail_on: str = "",
    ) -> None:
        self.account = {
            "account_id": EXPECTED_ACCOUNT_ID,
            "account_number": EXPECTED_ACCOUNT_NUMBER,
            "status": "ACTIVE",
            "trading_blocked": False,
            "account_blocked": False,
            "trade_suspended_by_user": False,
            **(account or {}),
        }
        self.positions = positions
        self.open_orders = open_orders
        self.recent_orders = recent_orders
        self.fail_on = fail_on
        self.calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        if self.fail_on == "account":
            raise RuntimeError("simulated account read failure")
        return self.account

    def get_positions(self) -> tuple[dict[str, object], ...]:
        self.calls.append("get_positions")
        if self.fail_on == "positions":
            raise RuntimeError("simulated positions read failure")
        return self.positions

    def get_orders(self, query) -> tuple[dict[str, object], ...]:  # noqa: ANN001
        self.calls.append(f"get_orders:{query.status_filter}:{query.symbol_filter}")
        if query.status_filter == "open":
            if self.fail_on == "open_orders":
                raise RuntimeError("simulated open orders read failure")
            return self.open_orders
        if self.fail_on == "recent_orders":
            raise RuntimeError("simulated recent orders read failure")
        return self.recent_orders


def _write_approval_packet(
    root: Path,
    *,
    approval_packet_classification: str = APPROVAL_PACKET_READY_NO_MUTATION,
    symbol: str = "SPY",
    timestamp: str = GENERATED_AT,
) -> Path:
    packet = {
        "packet_version": V195_PACKET_VERSION,
        "run_id": "v195_bounded_paper_drill_approval_packet",
        "created_at": timestamp,
        "approval_packet_classification": approval_packet_classification,
        "approval_packet_is_authorization": False,
        "symbol": symbol,
        "order_side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": "1.00",
        "quantity": "",
        "deterministic_client_order_id": CLIENT_ORDER_ID,
        "client_order_id": CLIENT_ORDER_ID,
        "maximum_notional_cap": "1.00",
        "maximum_quantity_cap": "",
        "maximum_notional_or_quantity_cap": "1.00",
        "maximum_notional_or_quantity_cap_kind": "notional",
        "maximum_notional_or_quantity_cap_source": "operator_test_cap",
        "projected_broker_request_fields": {
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "time_in_force": "day",
            "notional": "1.00",
            "quantity": "",
            "client_order_id": CLIENT_ORDER_ID,
        },
    }
    path = root / "runs" / "paper_lab" / "v195" / "approval_packet.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, sort_keys=True), encoding="utf-8")
    return path


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": "paper-key",
        "APCA_API_SECRET_KEY": "paper-secret",
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }


def _factory(fake_client: FakeV196Client):
    def build(_config):  # noqa: ANN001
        return fake_client

    return build


def _forbidden_factory(_config):  # noqa: ANN001
    raise AssertionError("broker factory must not be called")


def _assert_expected_account_audit(
    packet: dict[str, object],
    *,
    observed_account_id_present: bool,
    observed_account_number_present: bool,
    expected_account_configured: bool,
    expected_account_id_matched: bool | None,
    expected_account_number_matched: bool | None,
    expected_account_matched: bool | None,
    expected_account_match_mode: str,
    expected_account_blocker: str,
) -> None:
    for field_name in _REQUIRED_ACCOUNT_AUDIT_FIELDS:
        assert field_name in packet

    expected_values = {
        "observed_account_id_present": observed_account_id_present,
        "observed_account_number_present": observed_account_number_present,
        "expected_account_configured": expected_account_configured,
        "expected_account_id_matched": expected_account_id_matched,
        "expected_account_number_matched": expected_account_number_matched,
        "expected_account_matched": expected_account_matched,
        "expected_account_match_mode": expected_account_match_mode,
    }
    for field_name, expected_value in expected_values.items():
        assert packet[field_name] == expected_value
    assert packet["expected_account_blocker"] == expected_account_blocker
    assert packet["expected_account_check"] == {
        field_name: expected_values[field_name]
        for field_name in _EXPECTED_ACCOUNT_CHECK_FIELDS
    }


def _assert_artifacts(output_root: Path, packet: dict[str, object]) -> None:
    paths = packet["artifact_paths"]
    assert Path(paths["broker_observation_packet"]).exists()
    assert Path(paths["broker_observation_brief"]).exists()
    assert Path(paths["broker_observation_record"]).exists()
    assert Path(paths["manifest"]).exists()
    assert json.loads(Path(paths["broker_observation_packet"]).read_text()) == packet
    assert [json.loads(line) for line in Path(paths["broker_observation_record"]).read_text().splitlines()] == [packet]


def _assert_no_authority(packet: dict[str, object]) -> None:
    for field_name in (
        "broker_mutation_performed",
        "paper_submit_performed",
        "paper_cancel_performed",
        "live_read_performed",
        "live_mutation_performed",
        "paper_submit_authorized",
        "paper_cancel_authorized",
        "broker_mutation_authorized",
    ):
        assert packet[field_name] is False
    assert packet["paper_lab_only"] is True
    assert packet["read_only_broker_observation"] is True
    assert packet["not_live_authorized"] is True
    assert packet["not_paper_submit_authorized"] is True
    assert packet["profit_claim"] == "none"
    assert set(packet["safety_labels"]) == {
        "paper_lab_only",
        "read_only_broker_observation",
        "not_live_authorized",
        "not_paper_submit_authorized",
        "broker_mutation_performed=false",
        "paper_submit_performed=false",
        "profit_claim=none",
    }
