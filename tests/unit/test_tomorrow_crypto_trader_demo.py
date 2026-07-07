from __future__ import annotations

import ast
from collections.abc import Mapping
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from algotrader.execution.tomorrow_crypto_trader_demo import (
    MAX_NOTIONAL_PER_ORDER,
    MAX_TOTAL_DEMO_EXPOSURE,
    REQUIRED_ARTIFACTS,
    REQUIRED_SAFETY_LABELS,
    STATE_ARTIFACTS,
    build_no_submit_paper_readiness_packet,
    run_tomorrow_crypto_trader_demo,
    validate_tomorrow_crypto_trader_demo,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "src" / "algotrader" / "execution" / "tomorrow_crypto_trader_demo.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_tomorrow_crypto_trader_demo.ps1"
VALIDATOR_SCRIPT_PATH = (
    PROJECT_ROOT / "scripts" / "validate_tomorrow_crypto_trader_demo.ps1"
)
AS_OF = datetime(2026, 7, 6, 14, 30, tzinfo=UTC)
SENSITIVE_KEY = "SENTINEL_ALPACA_SECRET_DO_NOT_PRINT"


class _FakeBrokerReadClient:
    def __init__(
        self,
        *,
        account: Mapping[str, object] | None = None,
        positions: list[Mapping[str, object]] | None = None,
        open_orders: list[Mapping[str, object]] | None = None,
        assets: list[Mapping[str, object]] | None = None,
    ) -> None:
        self.account = account or {"status": "ACTIVE"}
        self.positions = positions or []
        self.open_orders = open_orders or []
        self.assets = assets or [
            {
                "symbol": "BTCUSD",
                "asset_class": "crypto",
                "status": "active",
                "tradable": True,
                "orderable": True,
                "min_order_value": "1",
                "min_order_size": "0.00000001",
            }
        ]
        self.calls: list[str] = []

    def get_account(self) -> Mapping[str, object]:
        self.calls.append("get_account")
        return self.account

    def get_positions(self) -> list[Mapping[str, object]]:
        self.calls.append("get_positions")
        return self.positions

    def get_orders(self, query: object | None = None) -> list[Mapping[str, object]]:
        self.calls.append("get_orders")
        return self.open_orders

    def list_assets(self) -> list[Mapping[str, object]]:
        self.calls.append("list_assets")
        return self.assets


def test_simbroker_end_to_end_run_writes_valid_artifact_packet(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )

    assert packet["mode"] == "SimBroker"
    assert packet["broker_mode"] == "simulation_broker"
    assert packet["decision"] == "offline_simulated_trade_only"
    assert packet["selected_candidate"]["symbol"] == "BTCUSD"
    assert packet["selected_candidate"]["data_gate_passed"] is True
    assert packet["selected_candidate"]["orderability_gate_passed"] is True
    assert packet["selected_candidate"]["risk_gate_passed"] is True
    assert packet["final_blocker_status"] == "none"
    assert packet["safety"]["broker_read_occurred"] is False
    assert packet["safety"]["broker_mutation_occurred"] is False
    assert packet["safety"]["paper_submit_occurred"] is False
    assert packet["safety"]["simulation_mutation_occurred"] is True
    assert packet["safety"]["network_used"] is False
    assert set(REQUIRED_SAFETY_LABELS) <= set(packet["safety_labels"])
    readiness = packet["paper_readiness_packet"]
    assert readiness["record_type"] == "paper_readiness_packet"
    assert readiness["symbol"] == "BTCUSD"
    assert readiness["side"] == "buy"
    assert readiness["readiness_basis"] == "fixture"
    assert readiness["readiness_decision"] == "fixture_ready_preview"
    assert readiness["blocker_code"] == ""
    assert readiness["paper_submit_authorized"] is False
    assert readiness["paper_submit_occurred"] is False
    assert readiness["broker_read_occurred"] is False
    assert readiness["broker_mutation_occurred"] is False
    assert readiness["network_used"] is False
    assert readiness["min_notional_basis"]["verified"] is True
    assert readiness["quantity_increment_basis"]["verified"] is True
    assert readiness["orderability_basis"]["broker_observed"] is False

    for artifact_name in REQUIRED_ARTIFACTS:
        assert (output_root / artifact_name).is_file()
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    assert "paper_readiness_packet" in manifest["required_artifacts"]
    assert "paper_readiness_packet_markdown" in manifest["required_artifacts"]
    assert "broker_observed_readiness_packet" not in manifest["required_artifacts"]
    assert manifest["readiness_bases"]["fixture"]["decision"] == "fixture_ready_preview"
    assert (
        manifest["readiness_bases"]["broker_observed"]["decision"]
        == "broker_observed_not_attempted"
    )
    assert not (output_root / "broker_observed_readiness_packet.json").exists()
    brief = (output_root / "operating_brief.md").read_text(encoding="utf-8")
    assert "Paper readiness preview" in brief
    assert "Broker-observed readiness preview" in brief
    assert packet["broker_observed_readiness_preview"]["broker_observed_readiness_decision"] == (
        "broker_observed_not_attempted"
    )

    events = [
        json.loads(line)
        for line in (output_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_types = {event["event_type"] for event in events}
    assert "simulation_order_submitted" in event_types
    assert "simulation_order_filled" in event_types
    assert "simulation_reconciliation_checked" in event_types
    assert "paper_readiness_evaluated" in event_types

    validation = validate_tomorrow_crypto_trader_demo(output_root)
    assert validation["validation_status"] == "passed", validation["errors"]


@pytest.mark.parametrize(
    ("overrides", "expected_decision"),
    [
        ({"latest_price": None, "intent": False}, "blocked_missing_price"),
        (
            {"latest_price_timestamp": datetime(2026, 7, 6, 11, 0, tzinfo=UTC)},
            "blocked_stale_price",
        ),
        ({"orderability_verified": False}, "blocked_missing_orderability"),
        ({"min_notional_verified": False}, "blocked_min_notional_or_increment_not_verified"),
        ({"quantity_increment_verified": False}, "blocked_min_notional_or_increment_not_verified"),
        ({"quantity": "0.10"}, "blocked_exceeds_max_notional"),
        ({"portfolio_gross_exposure": "24"}, "blocked_exceeds_total_exposure"),
        ({"existing_client_order_ids": ("cid",)}, "blocked_duplicate_client_order_id"),
        ({"open_orders": ({"symbol": "BTCUSD", "status": "open"},)}, "blocked_open_order_present"),
        (
            {"positions": ({"symbol": "BTCUSD", "quantity": "0.01", "average_price": "100"},)},
            "blocked_unexpected_preexisting_position",
        ),
        ({"selected": False, "intent": False}, "blocked_no_selected_candidate"),
        ({"state_status": "failed", "state_errors": ("invalid_json:simbroker_state.json",)}, "blocked_sim_state_reconciliation_failed"),
    ],
)
def test_paper_readiness_packet_blocks_required_conditions(
    overrides: Mapping[str, object],
    expected_decision: str,
) -> None:
    packet = _paper_readiness_packet(**overrides)

    assert packet["readiness_decision"] == "fixture_blocked_preview"
    assert packet["blocker_code"] == expected_decision
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_submit_occurred"] is False
    assert packet["broker_mutation_authorized"] is False
    assert packet["broker_mutation_occurred"] is False
    assert packet["broker_read_occurred"] is False
    assert packet["broker_state_observed"] is False
    assert packet["network_used"] is False
    assert packet["credential_values_exposed"] is False


def test_simbroker_caps_are_enforced_in_selected_fill(tmp_path: Path) -> None:
    packet = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "latest",
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )

    fill = packet["fill_ledger"][0]
    portfolio = packet["portfolio_snapshot"]

    assert _decimal(fill["notional"]) <= MAX_NOTIONAL_PER_ORDER
    assert _decimal(portfolio["gross_exposure"]) <= MAX_TOTAL_DEMO_EXPOSURE
    assert len(portfolio["positions"]) == 1
    assert portfolio["positions"][0]["symbol"] == "BTCUSD"


def test_second_identical_cycle_holds_without_duplicate_buy(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    first = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        scenario="risk_on",
        write_artifacts=True,
    )
    second = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        scenario="risk_on",
        write_artifacts=True,
    )

    assert first["decision"] == "offline_simulated_trade_only"
    assert second["decision"] == "hold_noop_existing_simulated_position"
    assert second["planned_action"] == "hold_existing_position_risk_on"
    assert second["fill_ledger"] == []
    assert second["safety"]["simulation_mutation_occurred"] is False
    state = _read_state(second)
    assert len(state["fills"]) == 1
    assert len(state["cycle_history"]) == 2
    assert validate_tomorrow_crypto_trader_demo(output_root)["validation_status"] == "passed"


def test_risk_off_cycle_exits_existing_simulated_position(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        scenario="risk_on",
        write_artifacts=True,
    )

    exit_packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        scenario="risk_off",
        write_artifacts=True,
    )

    assert exit_packet["decision"] == "offline_simulated_exit_only"
    assert exit_packet["planned_action"] == "simulated_exit"
    assert exit_packet["fill_ledger"][0]["side"] == "sell"
    assert exit_packet["portfolio_snapshot"]["positions"] == []
    state = _read_state(exit_packet)
    assert state["positions"] == []
    assert len(state["fills"]) == 2
    assert validate_tomorrow_crypto_trader_demo(output_root)["validation_status"] == "passed"


def test_no_position_risk_off_cycle_holds_noop(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        scenario="risk_off",
        write_artifacts=True,
    )

    assert packet["decision"] == "hold_noop_no_simulated_position"
    assert packet["planned_action"] == "hold_no_position_risk_off"
    assert packet["fill_ledger"] == []
    assert packet["final_blocker_status"] == "none"
    assert packet["safety"]["simulation_mutation_occurred"] is False


def test_all_blocked_candidates_produce_blocked_no_trade(tmp_path: Path) -> None:
    packet = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "latest",
        mode="SimBroker",
        as_of=AS_OF,
        scenario="all_blocked",
        write_artifacts=True,
    )

    assert packet["decision"] == "blocked_no_trade_all_candidates_failed_gates"
    assert packet["planned_action"] == "blocked_no_trade"
    assert packet["fill_ledger"] == []
    assert packet["safety"]["simulation_mutation_occurred"] is False


def test_corrupted_state_blocks_safely_without_simulated_fill(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    state_root = tmp_path / "runs" / "crypto_trader_demo" / "state"
    state_root.mkdir(parents=True)
    (state_root / "simbroker_state.json").write_text("{not-json", encoding="utf-8")

    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        state_root=state_root,
        mode="SimBroker",
        as_of=AS_OF,
        scenario="risk_on",
        write_artifacts=True,
    )

    assert packet["decision"] == "blocked_state_reconciliation_failed"
    assert packet["final_blocker_status"] == "state_reconciliation_failed"
    assert packet["fill_ledger"] == []
    assert packet["safety"]["simulation_mutation_occurred"] is False


def test_duplicate_client_order_id_blocks_before_simulated_fill(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "first"
    first = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    client_order_id = first["execution_intent"]["client_order_id"]

    second = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "second",
        mode="SimBroker",
        as_of=AS_OF,
        existing_client_order_ids=(client_order_id,),
        write_artifacts=True,
    )

    assert second["decision"] == "blocked_duplicate_client_order_id"
    assert "duplicate_client_order_id" in second["final_blocker_status"]
    assert second["fill_ledger"] == []
    assert second["safety"]["simulation_mutation_occurred"] is False


def test_validator_catches_missing_and_corrupt_state_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    state_paths = {name: Path(path) for name, path in packet["state_artifact_paths"].items()}
    state_paths["positions.json"].unlink()

    missing_validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert missing_validation["validation_status"] == "failed"
    assert "missing_state_artifact:positions.json" in missing_validation["errors"]

    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        scenario="risk_on",
        reset_state=True,
        write_artifacts=True,
    )
    state_paths = {
        name: Path(path)
        for name, path in json.loads((output_root / "operating_record.json").read_text("utf-8"))[
            "state_artifact_paths"
        ].items()
    }
    state_paths["simbroker_state.json"].write_text("{bad-json", encoding="utf-8")

    corrupt_validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert corrupt_validation["validation_status"] == "failed"
    assert "invalid_json:simbroker_state.json" in corrupt_validation["errors"]


def test_validator_catches_inconsistent_cash_exposure_arithmetic(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    state_path = Path(packet["state_artifact_paths"]["simbroker_state.json"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["cash"] = "999"
    state_path.write_text(
        json.dumps(state, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "state_cash_arithmetic_mismatch" in validation["errors"]


def test_validator_catches_missing_paper_readiness_packet(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    (output_root / "paper_readiness_packet.json").unlink()

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "missing_artifact:paper_readiness_packet.json" in validation["errors"]
    assert "selected_candidate_or_execution_plan_missing_paper_readiness_packet" in validation[
        "errors"
    ]


def test_validator_catches_inconsistent_paper_readiness_safety_flags(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    readiness_path = output_root / "paper_readiness_packet.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["paper_submit_occurred"] = True
    readiness["safety"]["paper_submit_occurred"] = True
    _write_json_fixture(readiness_path, readiness)

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "paper_readiness_flag_not_false:paper_submit_occurred" in validation["errors"]
    assert "paper_readiness_safety_flag_not_false:paper_submit_occurred" in validation[
        "errors"
    ]


def test_validator_catches_false_paper_readiness_approval_without_min_evidence(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    readiness_path = output_root / "paper_readiness_packet.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["readiness_decision"] = "fixture_ready_preview"
    readiness["final_readiness_decision"] = "fixture_ready_preview"
    readiness["blocker_code"] = ""
    readiness["min_notional_basis"]["verified"] = False
    readiness["min_notional_basis"]["status"] = "missing"
    _write_json_fixture(readiness_path, readiness)

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "paper_readiness_approved_without_min_notional_evidence" in validation["errors"]


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (
            {"max_order_notional_check": {"status": "blocked"}},
            "paper_readiness_approved_despite_max_notional_check",
        ),
        (
            {"max_total_exposure_check": {"status": "blocked"}},
            "paper_readiness_approved_despite_total_exposure_check",
        ),
        (
            {"duplicate_client_order_id_check": {"status": "blocked"}},
            "paper_readiness_approved_despite_duplicate_client_order_id_check",
        ),
        (
            {"state_reconciliation_check": {"status": "failed"}},
            "paper_readiness_approved_despite_state_reconciliation_failed",
        ),
    ],
)
def test_validator_catches_false_paper_readiness_approval_with_failed_checks(
    tmp_path: Path,
    mutation: Mapping[str, Mapping[str, object]],
    expected_error: str,
) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    readiness_path = output_root / "paper_readiness_packet.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["readiness_decision"] = "fixture_ready_preview"
    readiness["final_readiness_decision"] = "fixture_ready_preview"
    readiness["blocker_code"] = ""
    for section, values in mutation.items():
        readiness[section].update(values)
    _write_json_fixture(readiness_path, readiness)

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert expected_error in validation["errors"]


def test_simbroker_artifacts_do_not_capture_loaded_credential_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", SENSITIVE_KEY)
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", f"{SENSITIVE_KEY}_SECRET")
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    emitted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    )

    assert packet["safety"]["credential_values_exposed"] is False
    assert SENSITIVE_KEY not in emitted
    assert f"{SENSITIVE_KEY}_SECRET" not in emitted


def test_alpaca_paper_mode_refuses_without_exact_authorization() -> None:
    packet = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=False,
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert packet["decision"] == "blocked_not_authorized"
    assert packet["safety"]["paper_submit_authorized"] is False
    assert packet["safety"]["broker_mutation_authorized"] is False
    assert packet["safety"]["broker_mutation_occurred"] is False


def test_alpaca_paper_mode_blocks_bad_profile_and_missing_credentials() -> None:
    dev_packet = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment={"APP_PROFILE": "dev"},
        as_of=AS_OF,
        write_artifacts=False,
    )
    paper_no_creds = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment={"APP_PROFILE": "paper"},
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert dev_packet["decision"] == "blocked_not_paper_profile"
    assert paper_no_creds["decision"] == "blocked_credentials_not_loaded"


def test_alpaca_paper_mode_blocks_ambiguous_state_and_min_notional_uncertainty() -> None:
    env = {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": True,
        "APCA_API_SECRET_KEY": True,
    }

    preexisting = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment=env,
        alpaca_paper_snapshot={"positions": [{"symbol": "BTCUSD", "qty": "1"}]},
        as_of=AS_OF,
        write_artifacts=False,
    )
    ambiguous = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment=env,
        alpaca_paper_snapshot={"current_run_attribution_complete": False},
        as_of=AS_OF,
        write_artifacts=False,
    )
    min_notional = run_tomorrow_crypto_trader_demo(
        mode="AlpacaPaper",
        allow_alpaca_paper_mutation=True,
        paper_environment=env,
        alpaca_paper_snapshot={
            "current_run_attribution_complete": True,
            "min_notional_verified": False,
            "qty_increment_verified": True,
        },
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert preexisting["decision"] == "blocked_unexpected_preexisting_position_or_order"
    assert ambiguous["decision"] == "blocked_paper_state_ambiguous"
    assert min_notional["decision"] == "blocked_min_notional_or_increment_not_verified"


def test_default_simbroker_does_not_import_or_construct_broker_adapter(
    tmp_path: Path,
) -> None:
    sys.modules.pop("algotrader.execution.alpaca_sdk_client", None)

    def forbidden_factory() -> object:
        raise AssertionError("default SimBroker must not construct a broker adapter")

    packet = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "latest",
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_client_factory=forbidden_factory,
        write_artifacts=True,
    )

    assert packet["broker_observed_readiness_requested"] is False
    assert packet["broker_observed_readiness_preview"][
        "broker_observed_readiness_decision"
    ] == "broker_observed_not_attempted"
    assert "algotrader.execution.alpaca_sdk_client" not in sys.modules


def test_broker_observed_mode_refuses_without_explicit_read_authorization(
    tmp_path: Path,
) -> None:
    packet = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "latest",
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=False,
        write_artifacts=True,
    )

    broker = packet["broker_observed_readiness_packet"]

    assert broker["broker_observed_readiness_decision"] == (
        "broker_observed_blocked_not_authorized"
    )
    assert broker["broker_read_authorized"] is False
    assert broker["broker_read_occurred"] is False
    assert broker["broker_state_observed"] is False
    assert broker["paper_submit_authorized"] is False
    assert broker["broker_mutation_occurred"] is False
    assert (tmp_path / "runs" / "crypto_trader_demo" / "latest" / "broker_observed_readiness_packet.json").is_file()
    assert validate_tomorrow_crypto_trader_demo(
        tmp_path / "runs" / "crypto_trader_demo" / "latest"
    )["validation_status"] == "passed"


def test_broker_observed_mode_refuses_without_paper_profile() -> None:
    packet = run_tomorrow_crypto_trader_demo(
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=True,
        paper_environment={"APP_PROFILE": "dev"},
        write_artifacts=False,
    )

    broker = packet["broker_observed_readiness_packet"]

    assert broker["broker_observed_readiness_decision"] == (
        "broker_observed_blocked_not_paper_profile"
    )
    assert broker["broker_read_occurred"] is False


def test_broker_observed_mode_refuses_missing_credentials_without_exposing_values(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=True,
        paper_environment={"APP_PROFILE": "paper"},
        write_artifacts=True,
    )
    emitted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    )
    broker = json.loads(
        (output_root / "broker_observed_readiness_packet.json").read_text(
            encoding="utf-8"
        )
    )

    assert broker["broker_observed_readiness_decision"] == (
        "broker_observed_blocked_credentials_not_loaded"
    )
    assert broker["broker_read_occurred"] is False
    assert SENSITIVE_KEY not in emitted


def test_broker_observed_mode_refuses_live_or_unproven_endpoint() -> None:
    packet = run_tomorrow_crypto_trader_demo(
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=True,
        paper_environment={
            "APP_PROFILE": "paper",
            "ALPACA_API_KEY": True,
            "ALPACA_SECRET_KEY": True,
            "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
        },
        write_artifacts=False,
    )

    broker = packet["broker_observed_readiness_packet"]

    assert broker["broker_observed_readiness_decision"] == (
        "broker_observed_blocked_live_endpoint_detected"
    )
    assert broker["broker_endpoint_type"] == "live_or_unproven"
    assert broker["live_endpoint_touched"] is False
    assert broker["broker_read_occurred"] is False


def test_fake_broker_read_adapter_can_produce_broker_observed_ready_preview(
    tmp_path: Path,
) -> None:
    fake = _FakeBrokerReadClient()
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=True,
        paper_environment=_paper_read_env(),
        broker_observed_client=fake,
        broker_observed_network_used=False,
        write_artifacts=True,
    )
    broker = packet["broker_observed_readiness_packet"]

    assert broker["broker_observed_readiness_decision"] == "broker_observed_ready_preview"
    assert broker["broker_read_authorized"] is True
    assert broker["broker_read_occurred"] is True
    assert broker["broker_state_observed"] is True
    assert broker["live_endpoint_touched"] is False
    assert broker["paper_submit_authorized"] is False
    assert broker["paper_submit_occurred"] is False
    assert broker["broker_mutation_authorized"] is False
    assert broker["broker_mutation_occurred"] is False
    assert broker["network_used"] is False
    assert fake.calls == ["get_account", "get_positions", "get_orders", "list_assets"]
    assert validate_tomorrow_crypto_trader_demo(output_root)["validation_status"] == "passed"


@pytest.mark.parametrize(
    ("client", "expected_blocker"),
    [
        (
            _FakeBrokerReadClient(
                open_orders=[
                    {
                        "symbol": "BTCUSD",
                        "status": "open",
                        "side": "buy",
                        "client_order_id": "existing",
                    }
                ]
            ),
            "open_order_present",
        ),
        (
            _FakeBrokerReadClient(
                positions=[{"symbol": "BTCUSD", "qty": "0.01", "side": "long"}]
            ),
            "unexpected_preexisting_position",
        ),
        (
            _FakeBrokerReadClient(
                assets=[
                    {
                        "symbol": "BTCUSD",
                        "asset_class": "crypto",
                        "status": "active",
                        "tradable": True,
                    }
                ]
            ),
            "broker_min_notional_not_verified",
        ),
    ],
)
def test_fake_broker_read_adapter_blocks_unsafe_observed_state(
    client: "_FakeBrokerReadClient",
    expected_blocker: str,
    tmp_path: Path,
) -> None:
    packet = run_tomorrow_crypto_trader_demo(
        output_root=tmp_path / "runs" / "crypto_trader_demo" / "latest",
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=True,
        paper_environment=_paper_read_env(),
        broker_observed_client=client,
        broker_observed_network_used=False,
        write_artifacts=False,
    )

    broker = packet["broker_observed_readiness_packet"]

    assert broker["broker_observed_readiness_decision"] == "broker_observed_blocked_preview"
    assert broker["blocker_code"] == expected_blocker
    assert broker["paper_submit_occurred"] is False
    assert broker["broker_mutation_occurred"] is False


def test_validator_catches_fixture_readiness_mislabeled_as_broker_observed(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    readiness_path = output_root / "paper_readiness_packet.json"
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["readiness_decision"] = "broker_observed_ready_preview"
    readiness["final_readiness_decision"] = "broker_observed_ready_preview"
    _write_json_fixture(readiness_path, readiness)

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "fixture_readiness_labeled_as_broker_observed" in validation["errors"]


def test_validator_catches_inconsistent_broker_read_flags(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=True,
        paper_environment=_paper_read_env(),
        broker_observed_client=_FakeBrokerReadClient(),
        broker_observed_network_used=False,
        write_artifacts=True,
    )
    broker_path = output_root / "broker_observed_readiness_packet.json"
    broker = json.loads(broker_path.read_text(encoding="utf-8"))
    broker["broker_read_authorized"] = False
    broker["safety"]["broker_read_authorized"] = False
    _write_json_fixture(broker_path, broker)

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "broker_read_occurred_without_authorization" in validation["errors"]


def test_validator_catches_false_broker_observed_approval(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        broker_observed_readiness=True,
        allow_alpaca_paper_read=False,
        write_artifacts=True,
    )
    broker_path = output_root / "broker_observed_readiness_packet.json"
    broker = json.loads(broker_path.read_text(encoding="utf-8"))
    broker["broker_observed_readiness_decision"] = "broker_observed_ready_preview"
    broker["readiness_decision"] = "broker_observed_ready_preview"
    broker["final_readiness_decision"] = "broker_observed_ready_preview"
    broker["blocker_code"] = ""
    _write_json_fixture(broker_path, broker)

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "broker_observed_ready_without_broker_read" in validation["errors"]


def test_validator_fails_on_missing_required_label(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    record_path = output_root / "operating_record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["safety_labels"] = [
        label
        for label in record["safety_labels"]
        if label != "credential_values_exposed=false"
    ]
    record_path.write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    validation = validate_tomorrow_crypto_trader_demo(output_root)

    assert validation["validation_status"] == "failed"
    assert "operating_record_missing_label:credential_values_exposed=false" in validation[
        "errors"
    ]


def test_module_has_no_broker_sdk_or_network_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    forbidden_prefixes = (
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )
    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported_modules
        for prefix in forbidden_prefixes
    )


def test_scripts_expose_simbroker_and_validator_contracts() -> None:
    run_script = SCRIPT_PATH.read_text(encoding="utf-8")
    validator_script = VALIDATOR_SCRIPT_PATH.read_text(encoding="utf-8")

    for fragment in (
        '[string]$OutputRoot = "runs\\crypto_trader_demo\\latest"',
        '[ValidateSet("SimBroker", "AlpacaPaper")]',
        "[switch]$AllowAlpacaPaperMutation",
        "[switch]$BrokerObservedReadiness",
        "[switch]$AllowAlpacaPaperRead",
        "tomorrow_crypto_trader_demo_broker_mode=simulation_broker",
        "tomorrow_crypto_trader_demo_broker_observed_readiness=",
        "tomorrow_crypto_trader_demo_broker_read_authorized=",
        "tomorrow_crypto_trader_demo_status=blocked_not_authorized",
        "Credential values are never printed",
        "algotrader.execution.tomorrow_crypto_trader_demo",
        "--allow-alpaca-paper-mutation",
        "--broker-observed-readiness",
        "--allow-alpaca-paper-read",
    ):
        assert fragment in run_script
    for fragment in (
        "validate_tomorrow_crypto_trader_demo",
        "tomorrow_crypto_trader_demo_validator_network_used=false",
        "--validate-only",
    ):
        assert fragment in validator_script

    assert "close_all" not in run_script
    assert "liquidate" not in run_script
    assert "--live" not in run_script


def test_script_refuses_alpaca_paper_without_authorization_flag(tmp_path: Path) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-Mode",
            "AlpacaPaper",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    combined = result.stdout + result.stderr

    assert result.returncode == 2, combined
    assert "tomorrow_crypto_trader_demo_status=blocked_not_authorized" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )
    manifest = json.loads(Path(packet["artifact_paths"]["manifest"]).read_text("utf-8"))
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert manifest["generated_under_runs"] is True
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_state_artifacts_are_written_with_required_labels(tmp_path: Path) -> None:
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"
    packet = run_tomorrow_crypto_trader_demo(
        output_root=output_root,
        mode="SimBroker",
        as_of=AS_OF,
        write_artifacts=True,
    )

    for artifact_name in STATE_ARTIFACTS:
        assert Path(packet["state_artifact_paths"][artifact_name]).is_file()
    state = _read_state(packet)
    assert set(REQUIRED_SAFETY_LABELS) <= set(state["safety_labels"])
    assert "simulation_mutation_occurred=true" in state["safety_labels"]


def test_default_run_script_remains_backward_compatible(tmp_path: Path) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    output_root = tmp_path / "runs" / "crypto_trader_demo" / "latest"

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-OutputRoot",
            str(output_root),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    captured = capture_path.read_text(encoding="utf-8")
    assert "--output-root" in captured
    assert str(output_root) in captured
    assert "--mode SimBroker" in captured
    assert "--scenario risk_on" in captured
    assert "--state-root" not in captured
    assert "--reset-state" not in captured
    assert "--broker-observed-readiness" not in captured
    assert "--allow-alpaca-paper-read" not in captured


def _paper_readiness_packet(
    *,
    latest_price: object = "100",
    latest_price_timestamp: object = AS_OF,
    orderability_verified: object = True,
    min_notional_verified: object = True,
    quantity_increment_verified: object = True,
    quantity: object = "0.05",
    selected: bool = True,
    intent: bool = True,
    portfolio_gross_exposure: object = "0",
    positions: object = (),
    existing_client_order_ids: object = (),
    open_orders: object = (),
    state_status: str = "passed",
    state_errors: object = (),
) -> Mapping[str, object]:
    selected_candidate = None
    if selected:
        selected_candidate = {
            "symbol": "BTCUSD",
            "strategy_id": "btc_fixture_strategy",
            "latest_price": latest_price,
            "orderability_gate_passed": orderability_verified,
            "min_notional_verified": min_notional_verified,
            "qty_increment_verified": quantity_increment_verified,
            "features": {"latest_price_timestamp": latest_price_timestamp},
        }
    execution_intent = None
    if intent:
        execution_intent = {
            "symbol": "BTCUSD",
            "side": "buy",
            "quantity": quantity,
            "client_order_id": "cid",
            "status": "risk_approved",
            "note": "ExecutionIntent is not a broker order.",
        }
    return build_no_submit_paper_readiness_packet(
        run_id="test_run",
        cycle_index=0,
        as_of=AS_OF,
        selected_candidate=selected_candidate,
        execution_intent=execution_intent,
        execution_plan={
            "immutable_pre_broker": True,
            "intent_count": 1 if intent else 0,
            "intents": [{"symbol": "BTCUSD", "status": "risk_approved"}] if intent else [],
        },
        planned_action="simulated_buy" if selected else "blocked_no_trade",
        state_reconciliation={"status": state_status, "errors": list(state_errors)},
        portfolio_snapshot={
            "gross_exposure": portfolio_gross_exposure,
            "positions": list(positions),
        },
        existing_client_order_ids=tuple(existing_client_order_ids),
        open_orders=tuple(open_orders),
        readiness_basis={
            "symbol": "BTCUSD" if selected or intent else "",
            "side": "buy" if selected or intent else "",
            "client_order_id": "cid" if selected or intent else "",
            "latest_price": latest_price,
            "latest_price_timestamp": latest_price_timestamp,
            "estimated_quantity": quantity if latest_price is not None else None,
            "orderability_verified": orderability_verified,
            "min_notional_verified": min_notional_verified,
            "quantity_increment_verified": quantity_increment_verified,
            "min_notional": "1",
            "quantity_increment": "0.00000001",
        },
    )


def _write_json_fixture(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _paper_read_env() -> Mapping[str, object]:
    return {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": True,
        "ALPACA_SECRET_KEY": True,
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
    }


def _read_state(packet: Mapping[str, object]) -> Mapping[str, object]:
    state_paths = packet["state_artifact_paths"]
    assert isinstance(state_paths, Mapping)
    state_path = Path(str(state_paths["simbroker_state.json"]))
    return json.loads(state_path.read_text(encoding="utf-8"))


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"decision\":\"offline_simulated_trade_only\"}\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    env["APP_PROFILE"] = "dev"
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_tomorrow_crypto_trader_demo.ps1")
    return powershell


def _decimal(value: object):
    from decimal import Decimal

    return Decimal(str(value))
