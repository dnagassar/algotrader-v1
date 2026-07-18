from datetime import UTC, datetime, timedelta
import hashlib
import inspect
import json
from pathlib import Path
import sqlite3
import pytest

from algotrader.cli import main
from algotrader.errors import ValidationError
from algotrader.execution.order_journal import OrderReservation, SqliteOrderJournal
from algotrader.execution.paper_autopilot_control import (
    PaperAutopilotControlConfig,
    run_paper_autopilot_control,
)
from algotrader.execution.paper_cancellation_admission import (
    PaperCancellationAdmissionBlocker,
)
from algotrader.execution.paper_cancellation_candidate_selector import (
    CancellationCandidateSelectionBlocker,
)
from algotrader.execution.paper_cancellation_handoff_preview import (
    DurableCancellationHandoffBlocker,
)
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationPlanningBlocker,
)


NOW = datetime(2026, 7, 11, 15, 0, tzinfo=UTC)
CLIENT_ORDER_ID = "preview-client-1"
BROKER_ORDER_ID = "preview-broker-1"


def test_pause_status_and_resume_are_durable_and_offline(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"

    paused = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="pause",
            reason="operator stop",
        ),
        timestamp=NOW,
    )
    status = run_paper_autopilot_control(
        PaperAutopilotControlConfig(journal_path=path, action="status"),
    )
    resumed = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="resume",
            reason="operator reviewed state",
        ),
        timestamp=NOW + timedelta(minutes=5),
    )

    assert paused["operator_paused"] is True
    assert status["operator_paused"] is True
    assert resumed["trading_enabled"] is True
    assert resumed["reason"] == "operator reviewed state"
    for result in (paused, status, resumed):
        assert result["network_access_attempted"] is False
        assert result["broker_access_attempted"] is False
        assert result["broker_mutation_performed"] is False
        assert result["live_authorized"] is False


def test_status_cancellation_preview_is_default_disabled_without_record_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state" / "orders.sqlite3"

    def fail_record_scan(_journal: SqliteOrderJournal) -> tuple[object, ...]:
        raise AssertionError("default-disabled status must not scan order records")

    monkeypatch.setattr(SqliteOrderJournal, "records", fail_record_scan)

    result = run_paper_autopilot_control(
        PaperAutopilotControlConfig(journal_path=path, action="status"),
        timestamp=NOW,
    )

    assert result["cancellation_planning_preview_enabled"] is False
    assert result["cancellation_candidate_auto_selection_enabled"] is False
    assert result["cancellation_handoff_preview_enabled"] is False
    assert result["cancellation_admission_preview_enabled"] is False
    assert result["cancellation_planning_preview"] == {
        "status": "disabled",
        "no_submit": True,
        "cancel_attempted": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
    }
    assert result["cancellation_handoff_preview"] == {
        "status": "disabled",
        "no_submit": True,
        "handoff_prepared": False,
        "cancel_allowed": False,
        "execution_authorized": False,
        "broker_callback_present": False,
        "coordinator_invoked": False,
        "cancel_attempted": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "journal_mutation_performed": False,
    }
    assert result["cancellation_admission_preview"] == {
        "status": "disabled",
        "admission_ready": False,
        "operator_authorization_validated": False,
        "cancel_allowed": False,
        "execution_authorized": False,
        "execution_performed": False,
        "broker_callback_present": False,
        "coordinator_invoked": False,
        "lease_acquired": False,
        "cancel_intent_reserved": False,
        "cancel_attempted": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "journal_mutation_performed": False,
        "live_authorized": False,
        "no_submit": True,
    }


def test_status_builds_journal_backed_no_submit_cancellation_plan(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    journal = _observed_journal(path)
    before_records = tuple(record.to_dict() for record in journal.records())
    before_control = journal.get_runtime_control().to_dict()
    before_cancel_intents = tuple(
        record.to_dict() for record in journal.cancel_intents()
    )

    def fail_broker_factory(_config: object) -> object:
        raise AssertionError("status preview must not construct a broker client")

    result = run_paper_autopilot_control(
        _preview_config(path),
        timestamp=NOW + timedelta(minutes=5),
        broker_client_factory=fail_broker_factory,
    )

    preview = result["cancellation_planning_preview"]
    assert result["cancellation_planning_preview_enabled"] is True
    assert preview["status"] == "planned"
    assert preview["no_submit"] is True
    assert preview["cancel_attempted"] is False
    assert preview["broker_access_performed"] is False
    assert preview["broker_mutation_performed"] is False
    assert preview["planning_result"]["plan"]["client_order_id"] == (
        CLIENT_ORDER_ID
    )
    assert preview["planning_result"]["plan"]["broker_order_id"] == (
        BROKER_ORDER_ID
    )
    assert result["network_access_attempted"] is False
    assert result["broker_access_attempted"] is False
    assert result["broker_mutation_performed"] is False
    assert tuple(record.to_dict() for record in journal.records()) == before_records
    assert journal.get_runtime_control().to_dict() == before_control
    assert tuple(
        record.to_dict() for record in journal.cancel_intents()
    ) == before_cancel_intents


def test_status_preview_without_offline_planning_permission_fails_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)

    result = run_paper_autopilot_control(
        _preview_config(path, cancellation_planning_permitted=False),
        timestamp=NOW,
    )

    assert _preview_policy_blocker(result) == (
        CancellationPlanningBlocker.CANCELLATION_NOT_PERMITTED.value
    )


@pytest.mark.parametrize(
    ("trading_enabled", "stop_requested", "expected"),
    [
        (False, False, CancellationPlanningBlocker.TRADING_PAUSED),
        (True, True, CancellationPlanningBlocker.STOP_REQUESTED),
    ],
)
def test_status_preview_derives_runtime_controls_from_local_journal(
    tmp_path: Path,
    trading_enabled: bool,
    stop_requested: bool,
    expected: CancellationPlanningBlocker,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _observed_journal(path)
    journal.set_runtime_control(
        trading_enabled=trading_enabled,
        reason="local runtime control",
        occurred_at=NOW + timedelta(minutes=1),
        stop_requested=stop_requested,
    )

    result = run_paper_autopilot_control(
        _preview_config(path),
        timestamp=NOW + timedelta(minutes=5),
    )

    assert _preview_policy_blocker(result) == expected.value


def test_status_preview_derives_staleness_from_record_and_explicit_as_of(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)

    result = run_paper_autopilot_control(
        _preview_config(
            path,
            cancellation_as_of=NOW + timedelta(hours=1),
            cancellation_max_record_age_seconds=60,
        ),
        timestamp=NOW,
    )

    assert _preview_policy_blocker(result) == (
        CancellationPlanningBlocker.SNAPSHOT_NOT_FRESH.value
    )


@pytest.mark.parametrize(
    ("config_changes", "expected"),
    [
        (
            {"cancellation_target_client_order_id": "missing-client"},
            CancellationPlanningBlocker.CLIENT_ORDER_ID_MISMATCH,
        ),
        (
            {"cancellation_target_broker_order_id": "other-broker"},
            CancellationPlanningBlocker.BROKER_ORDER_ID_MISMATCH,
        ),
        (
            {"cancellation_target_symbol": "BTC/USD"},
            CancellationPlanningBlocker.SYMBOL_MISMATCH,
        ),
    ],
)
def test_status_preview_fails_closed_on_target_mismatch(
    tmp_path: Path,
    config_changes: dict[str, object],
    expected: CancellationPlanningBlocker,
) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)

    result = run_paper_autopilot_control(
        _preview_config(path, **config_changes),
        timestamp=NOW,
    )

    assert _preview_policy_blocker(result) == expected.value


def test_status_preview_missing_record_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"

    result = run_paper_autopilot_control(
        _preview_config(path),
        timestamp=NOW,
    )

    assert _preview_policy_blocker(result) == (
        CancellationPlanningBlocker.OBSERVATION_MISSING.value
    )


def test_status_preview_duplicate_broker_identity_fails_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _observed_journal(path)
    _add_observed_order(
        journal,
        client_order_id="preview-client-2",
        broker_order_id=BROKER_ORDER_ID,
    )

    result = run_paper_autopilot_control(
        _preview_config(path),
        timestamp=NOW,
    )

    assert _preview_policy_blocker(result) == (
        CancellationPlanningBlocker.OBSERVATION_MISSING.value
    )


def test_status_preview_terminal_record_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path, broker_status="filled", filled_quantity="1")

    result = run_paper_autopilot_control(
        _preview_config(path),
        timestamp=NOW,
    )

    assert _preview_policy_blocker(result) == (
        CancellationPlanningBlocker.ORDER_TERMINAL.value
    )


def test_status_preview_ambiguous_journal_record_fails_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = SqliteOrderJournal(path)
    reservation = journal.reserve(
        OrderReservation(
            client_order_id=CLIENT_ORDER_ID,
            execution_plan_id="preview-plan",
            run_id="preview-run",
            symbol="SPY",
            side="buy",
            quantity=None,
            notional="25",
        ),
        NOW - timedelta(minutes=2),
    )
    journal.mark_submit_attempted(
        reservation.record.client_order_id,
        NOW - timedelta(minutes=1),
    )
    journal.mark_submit_ambiguous(
        reservation.record.client_order_id,
        NOW,
        reason="local ambiguous submit",
    )

    result = run_paper_autopilot_control(
        _preview_config(path),
        timestamp=NOW,
    )

    preview = result["cancellation_planning_preview"]
    assert preview["status"] == "blocked"
    assert preview["adapter_blocker"] == "lifecycle_inconsistent"
    assert preview["planning_result"] == {}


@pytest.mark.parametrize(
    "changes",
    [
        {"action": "pause"},
        {"cancellation_target_client_order_id": ""},
        {"cancellation_target_broker_order_id": ""},
        {"cancellation_target_symbol": ""},
        {"cancellation_reason": ""},
        {"cancellation_as_of": None},
        {"cancellation_as_of": datetime(2026, 7, 11, 15, 0)},
        {"cancellation_max_record_age_seconds": 0},
        {"cancellation_max_record_age_seconds": True},
    ],
)
def test_enabled_preview_configuration_requires_complete_offline_inputs(
    tmp_path: Path,
    changes: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "journal_path": tmp_path / "orders.sqlite3",
        "action": "status",
        "cancellation_preview_enabled": True,
        "cancellation_planning_permitted": True,
        "cancellation_target_client_order_id": CLIENT_ORDER_ID,
        "cancellation_target_broker_order_id": BROKER_ORDER_ID,
        "cancellation_target_symbol": "SPY",
        "cancellation_reason": "offline planning preview",
        "cancellation_as_of": NOW + timedelta(minutes=5),
        "cancellation_max_record_age_seconds": 900,
    }
    values.update(changes)

    with pytest.raises(ValidationError):
        PaperAutopilotControlConfig(**values)  # type: ignore[arg-type]


def test_cli_status_exposes_explicit_offline_cancellation_preview(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)

    exit_code = main(
        [
            "paper-autopilot-control",
            "status",
            "--order-journal-path",
            str(path),
            "--cancellation-preview",
            "--allow-offline-cancellation-planning",
            "--cancellation-target-client-order-id",
            CLIENT_ORDER_ID,
            "--cancellation-target-broker-order-id",
            BROKER_ORDER_ID,
            "--cancellation-target-symbol",
            "SPY",
            "--cancellation-reason",
            "offline planning preview",
            "--cancellation-as-of",
            (NOW + timedelta(minutes=5)).isoformat(),
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["cancellation_planning_preview_enabled"] is True
    assert payload["cancellation_planning_preview"]["status"] == "planned"
    assert payload["cancellation_planning_preview"]["no_submit"] is True


def test_status_auto_selects_one_aged_candidate_without_mutation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _observed_journal(path)
    before_records = tuple(record.to_dict() for record in journal.records())
    before_control = journal.get_runtime_control().to_dict()
    before_cancel_intents = tuple(
        record.to_dict() for record in journal.cancel_intents()
    )

    def fail_broker_factory(_config: object) -> object:
        raise AssertionError("candidate selection must not construct a broker client")

    result = run_paper_autopilot_control(
        _auto_preview_config(path),
        timestamp=NOW + timedelta(minutes=5),
        broker_client_factory=fail_broker_factory,
    )

    preview = result["cancellation_planning_preview"]
    selection = preview["candidate_selection"]
    assert result["cancellation_candidate_auto_selection_enabled"] is True
    assert preview["status"] == "planned"
    assert preview["no_submit"] is True
    assert preview["cancel_attempted"] is False
    assert preview["broker_access_performed"] is False
    assert preview["broker_mutation_performed"] is False
    assert selection["status"] == "selected"
    assert selection["candidate"]["client_order_id"] == CLIENT_ORDER_ID
    assert selection["candidate"]["broker_order_id"] == BROKER_ORDER_ID
    assert preview["planning_result"]["plan"]["client_order_id"] == CLIENT_ORDER_ID
    assert tuple(record.to_dict() for record in journal.records()) == before_records
    assert journal.get_runtime_control().to_dict() == before_control
    assert tuple(
        record.to_dict() for record in journal.cancel_intents()
    ) == before_cancel_intents
    assert result["network_access_attempted"] is False
    assert result["broker_access_attempted"] is False
    assert result["broker_mutation_performed"] is False


@pytest.mark.parametrize(
    ("duplicate_broker_identity", "expected"),
    [
        (
            True,
            CancellationCandidateSelectionBlocker.DUPLICATE_BROKER_IDENTITY,
        ),
        (
            False,
            CancellationCandidateSelectionBlocker.MULTIPLE_ELIGIBLE_CANDIDATES,
        ),
    ],
)
def test_status_auto_selection_refuses_ambiguous_candidate_sets(
    tmp_path: Path,
    duplicate_broker_identity: bool,
    expected: CancellationCandidateSelectionBlocker,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _observed_journal(path)
    _add_observed_order(
        journal,
        client_order_id="preview-client-2",
        broker_order_id=(BROKER_ORDER_ID if duplicate_broker_identity else "preview-broker-2"),
    )

    result = run_paper_autopilot_control(
        _auto_preview_config(path),
        timestamp=NOW + timedelta(minutes=5),
    )

    preview = result["cancellation_planning_preview"]
    assert preview["status"] == "blocked"
    assert preview["candidate_selection"]["blocker"] == expected.value
    assert preview["planning_result"] == {}
    assert preview["cancel_attempted"] is False
    assert preview["broker_access_performed"] is False
    assert preview["broker_mutation_performed"] is False


@pytest.mark.parametrize(
    ("config_changes", "control_changes", "expected"),
    [
        (
            {"cancellation_planning_permitted": False},
            {},
            CancellationCandidateSelectionBlocker.PLANNING_NOT_PERMITTED,
        ),
        (
            {},
            {"trading_enabled": False, "stop_requested": False},
            CancellationCandidateSelectionBlocker.TRADING_PAUSED,
        ),
        (
            {},
            {"trading_enabled": True, "stop_requested": True},
            CancellationCandidateSelectionBlocker.STOP_REQUESTED,
        ),
    ],
)
def test_status_auto_selection_derives_fail_closed_local_controls(
    tmp_path: Path,
    config_changes: dict[str, object],
    control_changes: dict[str, bool],
    expected: CancellationCandidateSelectionBlocker,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _observed_journal(path)
    if control_changes:
        journal.set_runtime_control(
            trading_enabled=control_changes["trading_enabled"],
            stop_requested=control_changes["stop_requested"],
            reason="local selector control",
            occurred_at=NOW + timedelta(minutes=1),
        )

    result = run_paper_autopilot_control(
        _auto_preview_config(path, **config_changes),
        timestamp=NOW + timedelta(minutes=5),
    )

    preview = result["cancellation_planning_preview"]
    assert preview["status"] == "blocked"
    assert preview["candidate_selection"]["blocker"] == expected.value
    assert preview["cancel_attempted"] is False


def test_status_auto_selection_blocks_young_records(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)

    result = run_paper_autopilot_control(
        _auto_preview_config(
            path,
            cancellation_candidate_minimum_open_age_seconds=600,
        ),
        timestamp=NOW + timedelta(minutes=5),
    )

    preview = result["cancellation_planning_preview"]
    assert preview["status"] == "blocked"
    assert preview["candidate_selection"]["blocker"] == (
        CancellationCandidateSelectionBlocker.NO_CANDIDATE.value
    )


def test_auto_selection_configuration_is_explicit_and_unmixed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    config = _auto_preview_config(path)
    assert config.cancellation_target_client_order_id == ""
    assert config.cancellation_target_broker_order_id == ""

    with pytest.raises(ValidationError, match="requires cancellation preview"):
        PaperAutopilotControlConfig(cancellation_auto_select_enabled=True)
    with pytest.raises(ValidationError, match="cannot be combined"):
        _auto_preview_config(
            path,
            cancellation_target_client_order_id=CLIENT_ORDER_ID,
        )
    with pytest.raises(ValidationError, match="positive integer"):
        _auto_preview_config(
            path,
            cancellation_candidate_minimum_open_age_seconds=True,
        )


@pytest.mark.parametrize("auto_select", [False, True])
def test_status_prepares_default_denied_durable_handoff_without_mutation(
    tmp_path: Path,
    auto_select: bool,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _observed_journal(path)
    before_records = tuple(record.to_dict() for record in journal.records())
    before_control = journal.get_runtime_control().to_dict()
    before_cancel_intents = tuple(
        record.to_dict() for record in journal.cancel_intents()
    )
    config_factory = _auto_preview_config if auto_select else _preview_config
    config = config_factory(
        path,
        cancellation_handoff_preview_enabled=True,
        cancellation_handoff_permitted=True,
    )

    def fail_broker_factory(_config: object) -> object:
        raise AssertionError("handoff preview must not construct a broker client")

    first = run_paper_autopilot_control(
        config,
        timestamp=NOW + timedelta(minutes=5),
        broker_client_factory=fail_broker_factory,
    )
    second = run_paper_autopilot_control(
        config,
        timestamp=NOW + timedelta(minutes=5),
        broker_client_factory=fail_broker_factory,
    )

    planning = first["cancellation_planning_preview"]
    handoff = first["cancellation_handoff_preview"]
    assert first["schema_version"] == "paper_autopilot_control_v7"
    assert first["cancellation_handoff_preview_enabled"] is True
    assert planning["status"] == "planned"
    assert handoff["status"] == "prepared"
    assert handoff["handoff_prepared"] is True
    assert handoff["source_plan_id"] == planning["planning_result"]["plan"][
        "plan_id"
    ]
    assert handoff["identity"]["client_order_id"] == CLIENT_ORDER_ID
    assert handoff["identity"]["broker_order_id"] == BROKER_ORDER_ID
    assert handoff["identity"]["reservation_run_id"] == (
        f"run-{CLIENT_ORDER_ID}"
    )
    assert handoff["coordinator_identity_inputs"] == {
        key: handoff["identity"][key]
        for key in (
            "cancel_intent_id",
            "client_order_id",
            "broker_order_id",
            "reservation_run_id",
            "reason",
        )
    }
    for field_name in (
        "cancel_allowed",
        "execution_authorized",
        "broker_callback_present",
        "coordinator_invoked",
        "cancel_attempted",
        "broker_access_performed",
        "broker_mutation_performed",
        "journal_mutation_performed",
    ):
        assert handoff[field_name] is False
    assert second["cancellation_handoff_preview"] == handoff
    assert tuple(record.to_dict() for record in journal.records()) == before_records
    assert journal.get_runtime_control().to_dict() == before_control
    assert tuple(
        record.to_dict() for record in journal.cancel_intents()
    ) == before_cancel_intents
    assert first["network_access_attempted"] is False
    assert first["broker_access_attempted"] is False
    assert first["broker_mutation_performed"] is False


@pytest.mark.parametrize("auto_select", [False, True])
def test_status_admission_preview_has_no_authorization_input_or_mutation(
    tmp_path: Path,
    auto_select: bool,
) -> None:
    path = tmp_path / "orders.sqlite3"
    journal = _observed_journal(path)
    before_records = tuple(record.to_dict() for record in journal.records())
    before_control = journal.get_runtime_control().to_dict()
    before_cancel_intents = tuple(
        record.to_dict() for record in journal.cancel_intents()
    )
    config_factory = _auto_preview_config if auto_select else _preview_config
    config = config_factory(
        path,
        cancellation_handoff_preview_enabled=True,
        cancellation_handoff_permitted=True,
        cancellation_admission_preview_enabled=True,
    )

    def fail_broker_factory(_config: object) -> object:
        raise AssertionError("admission preview must not construct a broker client")

    first = run_paper_autopilot_control(
        config,
        timestamp=NOW + timedelta(minutes=5),
        broker_client_factory=fail_broker_factory,
    )
    second = run_paper_autopilot_control(
        config,
        timestamp=NOW + timedelta(minutes=5),
        broker_client_factory=fail_broker_factory,
    )

    handoff = first["cancellation_handoff_preview"]
    admission = first["cancellation_admission_preview"]
    assert first["cancellation_admission_preview_enabled"] is True
    assert handoff["status"] == "prepared"
    assert admission["status"] == "blocked"
    assert admission["blocker"] == (
        PaperCancellationAdmissionBlocker.AUTHORIZATION_MISSING.value
    )
    assert admission["source_handoff_artifact_id"] == handoff["artifact_id"]
    assert admission["source_plan_id"] == handoff["source_plan_id"]
    assert admission["authorization_id"] == ""
    assert admission["identity"] == {}
    assert admission["evidence"] == {}
    for field_name in (
        "admission_ready",
        "operator_authorization_validated",
        "cancel_allowed",
        "execution_authorized",
        "execution_performed",
        "broker_callback_present",
        "coordinator_invoked",
        "lease_acquired",
        "cancel_intent_reserved",
        "cancel_attempted",
        "broker_access_performed",
        "broker_mutation_performed",
        "journal_mutation_performed",
        "live_authorized",
    ):
        assert admission[field_name] is False
    assert second["cancellation_admission_preview"] == admission
    assert tuple(record.to_dict() for record in journal.records()) == before_records
    assert journal.get_runtime_control().to_dict() == before_control
    assert tuple(
        record.to_dict() for record in journal.cancel_intents()
    ) == before_cancel_intents
    assert first["network_access_attempted"] is False
    assert first["broker_access_attempted"] is False
    assert first["broker_mutation_performed"] is False


def test_control_and_cli_expose_no_cancellation_authorization_channel() -> None:
    config_fields = tuple(PaperAutopilotControlConfig.__dataclass_fields__)
    run_parameters = tuple(inspect.signature(run_paper_autopilot_control).parameters)
    cli_path = Path(inspect.getsourcefile(main) or "")
    cli_source = cli_path.read_text(encoding="utf-8")

    assert all("authorization" not in field_name for field_name in config_fields)
    assert all("authorization" not in name for name in run_parameters)
    assert "--cancellation-authorization" not in cli_source
    assert "--operator-cancellation-authorization" not in cli_source
    assert "cancellation_authorization_path" not in cli_source
    assert "cancellation_authorization_file" not in cli_source


@pytest.mark.parametrize(
    ("config_changes", "expected"),
    [
        (
            {"cancellation_handoff_permitted": False},
            DurableCancellationHandoffBlocker.HANDOFF_NOT_PERMITTED,
        ),
        (
            {"cancellation_planning_permitted": False},
            DurableCancellationHandoffBlocker.PLAN_NOT_AVAILABLE,
        ),
    ],
)
def test_status_handoff_preview_fails_closed_before_identity_emission(
    tmp_path: Path,
    config_changes: dict[str, object],
    expected: DurableCancellationHandoffBlocker,
) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)
    handoff_config: dict[str, object] = {
        "cancellation_handoff_preview_enabled": True,
        "cancellation_handoff_permitted": True,
    }
    handoff_config.update(config_changes)

    result = run_paper_autopilot_control(
        _preview_config(path, **handoff_config),
        timestamp=NOW + timedelta(minutes=5),
    )

    handoff = result["cancellation_handoff_preview"]
    assert handoff["status"] == "blocked"
    assert handoff["blocker"] == expected.value
    assert handoff["identity"] == {}
    assert handoff["coordinator_identity_inputs"] == {}
    assert handoff["cancel_allowed"] is False
    assert handoff["coordinator_invoked"] is False


def test_auto_selection_blocker_cannot_reach_handoff_identity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)

    result = run_paper_autopilot_control(
        _auto_preview_config(
            path,
            cancellation_candidate_minimum_open_age_seconds=600,
            cancellation_handoff_preview_enabled=True,
            cancellation_handoff_permitted=True,
        ),
        timestamp=NOW + timedelta(minutes=5),
    )

    handoff = result["cancellation_handoff_preview"]
    assert handoff["status"] == "blocked"
    assert handoff["blocker"] == (
        DurableCancellationHandoffBlocker.PLANNING_RESULT_MISSING.value
    )
    assert handoff["identity"] == {}
    assert handoff["cancel_attempted"] is False


def test_handoff_configuration_requires_explicit_preview_chain(
    tmp_path: Path,
) -> None:
    path = tmp_path / "orders.sqlite3"
    with pytest.raises(ValidationError, match="requires cancellation preview"):
        PaperAutopilotControlConfig(
            cancellation_handoff_preview_enabled=True,
        )
    with pytest.raises(ValidationError, match="requires the handoff preview"):
        _preview_config(path, cancellation_handoff_permitted=True)
    with pytest.raises(ValidationError, match="must be a boolean"):
        _preview_config(
            path,
            cancellation_handoff_preview_enabled=1,
        )
    with pytest.raises(ValidationError, match="requires the handoff preview"):
        _preview_config(
            path,
            cancellation_admission_preview_enabled=True,
        )
    with pytest.raises(ValidationError, match="must be a boolean"):
        _preview_config(
            path,
            cancellation_handoff_preview_enabled=True,
            cancellation_admission_preview_enabled=1,
        )


def test_cli_status_exposes_auto_selection_and_handoff_without_target_ids(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "orders.sqlite3"
    _observed_journal(path)

    exit_code = main(
        [
            "paper-autopilot-control",
            "status",
            "--order-journal-path",
            str(path),
            "--cancellation-preview",
            "--auto-select-cancellation-candidate",
            "--allow-offline-cancellation-planning",
            "--cancellation-handoff-preview",
            "--allow-offline-cancellation-handoff",
            "--cancellation-admission-preview",
            "--cancellation-target-symbol",
            "SPY",
            "--cancellation-reason",
            "aged local order review",
            "--cancellation-as-of",
            (NOW + timedelta(minutes=5)).isoformat(),
            "--cancellation-candidate-minimum-open-age-seconds",
            "300",
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["cancellation_candidate_auto_selection_enabled"] is True
    assert payload["cancellation_planning_preview"]["status"] == "planned"
    assert payload["cancellation_planning_preview"]["candidate_selection"][
        "status"
    ] == "selected"
    assert payload["cancellation_planning_preview"]["no_submit"] is True
    handoff = payload["cancellation_handoff_preview"]
    assert payload["cancellation_handoff_preview_enabled"] is True
    assert handoff["status"] == "prepared"
    assert handoff["cancel_allowed"] is False
    assert handoff["execution_authorized"] is False
    assert handoff["broker_callback_present"] is False
    assert handoff["coordinator_invoked"] is False
    assert handoff["cancel_attempted"] is False
    assert handoff["broker_access_performed"] is False
    assert handoff["broker_mutation_performed"] is False
    assert handoff["journal_mutation_performed"] is False
    admission = payload["cancellation_admission_preview"]
    assert payload["cancellation_admission_preview_enabled"] is True
    assert admission["status"] == "blocked"
    assert admission["blocker"] == (
        PaperCancellationAdmissionBlocker.AUTHORIZATION_MISSING.value
    )
    assert admission["authorization_id"] == ""
    assert admission["identity"] == {}
    assert admission["evidence"] == {}
    assert admission["cancel_allowed"] is False
    assert admission["execution_authorized"] is False
    assert admission["execution_performed"] is False
    assert admission["broker_callback_present"] is False
    assert admission["coordinator_invoked"] is False
    assert admission["cancel_attempted"] is False
    assert admission["broker_access_performed"] is False
    assert admission["broker_mutation_performed"] is False
    assert admission["journal_mutation_performed"] is False


def test_control_backup_and_restore(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    backup = tmp_path / "state" / "orders.sqlite3.bak"

    run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="pause",
            reason="operator pause",
        ),
        timestamp=NOW,
    )

    res_backup = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="backup",
            backup_path=backup,
        ),
        timestamp=NOW,
    )
    assert res_backup["backup_successful"] is True
    assert backup.is_file()

    run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="resume",
            reason="resume",
        ),
        timestamp=NOW + timedelta(seconds=1),
    )

    # Pause it before restore because restore fails when trading_enabled is True
    run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="pause",
            reason="pre-restore pause",
        ),
        timestamp=NOW + timedelta(seconds=2),
    )

    res_restore = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="restore",
            backup_path=backup,
        ),
        timestamp=NOW + timedelta(seconds=3),
    )
    assert res_restore["restore_successful"] is True

    status = run_paper_autopilot_control(
        PaperAutopilotControlConfig(journal_path=path, action="status"),
    )
    assert status["operator_paused"] is True
    assert status["reason"] == "operator pause"


def test_control_start_and_stop_does_not_report_running_before_acknowledgment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    launched: list[list[str]] = []

    class FakePopen:
        def __init__(self, args, **kwargs) -> None:
            launched.append(list(args))

    monkeypatch.setattr(
        "algotrader.execution.paper_autopilot_control.subprocess.Popen",
        FakePopen,
    )

    res_start = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="start",
            reason="operator started supervisor",
        ),
        timestamp=NOW,
    )
    assert res_start["trading_enabled"] is True
    assert res_start["lease_acquired"] is False
    assert res_start["startup_requested"] is True
    assert res_start["startup_acknowledged"] is False
    assert res_start["supervisor_running"] is False
    assert launched and "paper-autopilot-supervisor" in launched[0]

    res_stop = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="stop",
            reason="operator stopped supervisor",
        ),
        timestamp=NOW + timedelta(seconds=1),
    )
    assert res_stop["trading_enabled"] is True
    assert res_stop["lease_released"] is False
    assert res_stop["stop_requested"] is True


class FakeClient:
    def get_account(self):
        class Account:
            id = "paper-account-id"
            status = "ACTIVE"
            currency = "USD"
            cash = "1000.0"
            buying_power = "2000.0"
            equity = "1000.0"
            last_equity = "1000.0"
            tradable = True
            trading_blocked = False
        return Account()
    def get_positions(self):
        return []
    def get_orders(self, query=None):
        return []


def test_control_reconcile(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "fake_key",
        "ALPACA_SECRET_KEY": "fake_secret",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "paper-account-id",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
    }

    # Reconcile requires a broker snapshot path offline
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_data = {
        "account": {
            "id": "paper-account-id",
            "status": "ACTIVE",
            "tradable": True,
            "trading_blocked": False,
            "cash": "1000.0",
            "buying_power": "2000.0",
        },
        "positions": [],
        "orders": [],
        "provenance": {
            "generated_at": NOW.isoformat(),
            "schema_version": "broker_snapshot_v1",
        }
    }
    snapshot_data["provenance"]["snapshot_sha256"] = _snapshot_hash(snapshot_data)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f)

    res = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="reconcile",
            broker_snapshot_path=snapshot_path,
        ),
        env=env,
        broker_client_factory=lambda cfg: FakeClient(),
        timestamp=NOW,
    )
    assert res["reconciled_count"] == 0
    assert res["unresolved_order_count"] == 0
    assert res["reconciliation"]["reconciliation_status"] == "reconciled"


def test_control_reconcile_persists_fail_closed_divergence_report(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    journal = SqliteOrderJournal(path)
    reservation = journal.reserve(
        OrderReservation(
            client_order_id="known-partial",
            execution_plan_id="plan-1",
            run_id="run-1",
            symbol="SPY",
            side="buy",
            quantity=None,
            notional="25",
        ),
        NOW,
    )
    journal.mark_submit_attempted(reservation.record.client_order_id, NOW)
    journal.record_broker_observation(
        reservation.record.client_order_id,
        NOW,
        broker_order_id="known-broker",
        broker_status="partially_filled",
        filled_quantity="0.5",
        filled_average_price="100",
    )

    snapshot_data = {
        "account": {
            "id": "paper-account-id",
            "status": "INACTIVE",
            "tradable": False,
            "trading_blocked": True,
            "cash": "-1",
            "buying_power": "",
        },
        "positions": [{"symbol": "MSFT", "quantity": "1"}],
        "orders": [
            {
                "id": "known-broker",
                "client_order_id": "known-partial",
                "status": "partially_filled",
                "filled_qty": "0.25",
                "filled_avg_price": "100",
            },
            {
                "id": "broker-only",
                "client_order_id": "broker-only",
                "status": "accepted",
                "filled_qty": "0",
            },
        ],
        "provenance": {"generated_at": NOW.isoformat(), "schema_version": "broker_snapshot_v1"},
    }
    snapshot_data["provenance"]["snapshot_sha256"] = _snapshot_hash(snapshot_data)
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot_data), encoding="utf-8")

    result = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="reconcile",
            broker_snapshot_path=snapshot_path,
        ),
        timestamp=NOW,
    )

    reconciliation = result["reconciliation"]
    assert reconciliation["reconciliation_status"] == "blocked"
    assert reconciliation["fail_closed"] is True
    assert "cumulative_fill_decreased:known-partial" in reconciliation["findings"]
    assert "broker_only_order:broker-only" in reconciliation["findings"]
    assert "unexpected_symbol:MSFT" in reconciliation["findings"]
    assert journal.last_reconciliation_result() == reconciliation


def _snapshot_hash(snapshot: dict[str, object]) -> str:
    payload = {
        "account": snapshot["account"],
        "positions": snapshot["positions"],
        "orders": snapshot["orders"],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_control_one_cycle(tmp_path: Path) -> None:
    path = tmp_path / "state" / "orders.sqlite3"
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "fake_key",
        "ALPACA_SECRET_KEY": "fake_secret",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": "paper-account-id",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
    }

    bars_file = tmp_path / "bars.csv"
    bars_file.write_text(
        "date,open,high,low,close,volume\n2026-07-10,100,101,99,100.5,1000\n",
        encoding="utf-8",
    )

    def dummy_lab_runner(cfg):
        return {
            "preview_decision": "hold",
            "blocker_status": "none",
            "next_operator_action": "continue",
            "latest_bar_date": "2026-07-10",
            "data_freshness_status": "accepted_data_current",
            "data_refresh_status": "no_refresh_required",
            "expected_latest_bar_date": "2026-07-10",
        }

    res = run_paper_autopilot_control(
        PaperAutopilotControlConfig(
            journal_path=path,
            action="one-cycle",
            bars_csv=bars_file,
            output_root=tmp_path / "latest",
        ),
        env=env,
        broker_client_factory=lambda cfg: FakeClient(),
        daily_lab_runner=dummy_lab_runner,
        timestamp=NOW,
    )
    assert "one_cycle_result" in res
    # Note: loop_exit_code will be tested and pass once we update run_paper_autopilot_loop signature.


def test_restore_blocked_when_trading_enabled(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    backup = tmp_path / "orders.sqlite3.bak"
    journal = SqliteOrderJournal(path)

    journal.set_runtime_control(trading_enabled=True, reason="active", occurred_at=NOW)
    journal.backup(backup)

    with pytest.raises(ValidationError, match="Restore is blocked when trading is enabled"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=backup,
            ),
            timestamp=NOW,
        )


def test_restore_blocked_when_lease_active(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    backup = tmp_path / "orders.sqlite3.bak"
    journal = SqliteOrderJournal(path)

    journal.set_runtime_control(trading_enabled=False, reason="paused", occurred_at=NOW)
    journal.backup(backup)

    journal.acquire_runtime_lease(
        lease_name="paper-autopilot",
        owner_run_id="run-1",
        occurred_at=NOW,
        ttl_seconds=60,
    )

    with pytest.raises(ValidationError, match="Restore is blocked when a valid runtime lease is active"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=backup,
            ),
            timestamp=NOW,
        )


def test_restore_rejects_corrupt_source(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    bad_backup = tmp_path / "corrupt.sqlite3.bak"
    bad_backup.write_bytes(b"garbage-data-not-a-sqlite-db")

    journal = SqliteOrderJournal(path)
    journal.set_runtime_control(trading_enabled=False, reason="paused", occurred_at=NOW)

    with pytest.raises(ValidationError, match="integrity check failed|invalid|corruption"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=bad_backup,
            ),
            timestamp=NOW,
        )

    assert journal.get_runtime_control().trading_enabled is False
    assert journal.get_runtime_control().reason == "paused"


def test_restore_rejects_schema_v4_without_cancel_tables(tmp_path: Path) -> None:
    path = tmp_path / "orders.sqlite3"
    backup = tmp_path / "orders.sqlite3.bak"
    journal = SqliteOrderJournal(path)
    journal.set_runtime_control(
        trading_enabled=False,
        reason="pre-restore pause",
        occurred_at=NOW,
    )
    journal.backup(backup)
    with sqlite3.connect(backup) as connection:
        connection.execute("DROP TABLE cancel_events")
        connection.commit()

    with pytest.raises(ValidationError, match="missing cancellation tables"):
        run_paper_autopilot_control(
            PaperAutopilotControlConfig(
                journal_path=path,
                action="restore",
                backup_path=backup,
            ),
            env={},
            timestamp=NOW,
        )


def _preview_config(
    path: Path,
    **overrides: object,
) -> PaperAutopilotControlConfig:
    values: dict[str, object] = {
        "journal_path": path,
        "action": "status",
        "cancellation_preview_enabled": True,
        "cancellation_planning_permitted": True,
        "cancellation_target_client_order_id": CLIENT_ORDER_ID,
        "cancellation_target_broker_order_id": BROKER_ORDER_ID,
        "cancellation_target_symbol": "SPY",
        "cancellation_reason": "offline planning preview",
        "cancellation_as_of": NOW + timedelta(minutes=5),
        "cancellation_max_record_age_seconds": 900,
    }
    values.update(overrides)
    return PaperAutopilotControlConfig(**values)  # type: ignore[arg-type]


def _auto_preview_config(
    path: Path,
    **overrides: object,
) -> PaperAutopilotControlConfig:
    values: dict[str, object] = {
        "journal_path": path,
        "action": "status",
        "cancellation_preview_enabled": True,
        "cancellation_auto_select_enabled": True,
        "cancellation_planning_permitted": True,
        "cancellation_target_symbol": "SPY",
        "cancellation_reason": "aged local order review",
        "cancellation_as_of": NOW + timedelta(minutes=5),
        "cancellation_max_record_age_seconds": 900,
        "cancellation_candidate_minimum_open_age_seconds": 300,
    }
    values.update(overrides)
    return PaperAutopilotControlConfig(**values)  # type: ignore[arg-type]


def _observed_journal(
    path: Path,
    *,
    broker_status: str = "accepted",
    filled_quantity: str = "0",
) -> SqliteOrderJournal:
    journal = SqliteOrderJournal(path)
    _add_observed_order(
        journal,
        client_order_id=CLIENT_ORDER_ID,
        broker_order_id=BROKER_ORDER_ID,
        broker_status=broker_status,
        filled_quantity=filled_quantity,
    )
    return journal


def _add_observed_order(
    journal: SqliteOrderJournal,
    *,
    client_order_id: str,
    broker_order_id: str,
    broker_status: str = "accepted",
    filled_quantity: str = "0",
) -> None:
    reservation = journal.reserve(
        OrderReservation(
            client_order_id=client_order_id,
            execution_plan_id=f"plan-{client_order_id}",
            run_id=f"run-{client_order_id}",
            symbol="SPY",
            side="buy",
            quantity=None,
            notional="25",
        ),
        NOW - timedelta(minutes=2),
    )
    journal.mark_submit_attempted(
        reservation.record.client_order_id,
        NOW - timedelta(minutes=1),
    )
    journal.record_broker_observation(
        reservation.record.client_order_id,
        NOW,
        broker_order_id=broker_order_id,
        broker_status=broker_status,
        filled_quantity=filled_quantity,
        filled_average_price=("100" if filled_quantity != "0" else None),
    )


def _preview_policy_blocker(result: dict[str, object]) -> str:
    preview = result["cancellation_planning_preview"]
    assert isinstance(preview, dict)
    planning_result = preview["planning_result"]
    assert isinstance(planning_result, dict)
    blocker = planning_result["blocker"]
    assert isinstance(blocker, str)
    return blocker
