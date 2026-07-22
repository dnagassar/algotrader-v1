from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Any

import pytest

from algotrader.execution.secure_credential_provider import (
    CREDENTIAL_RECORD_SCHEMA,
    CredentialFamily,
    CredentialProviderError,
    CredentialReference,
    lease_from_test_record,
)
from algotrader.execution.v535_burn_in_status import (
    build_v535_burn_in_status,
    validate_completed_cycle_evidence,
)
from algotrader.execution.v535_unattended_readonly import (
    V535_TASK_ARGUMENTS,
    V535_TASK_EXECUTE,
    V535_TASK_IDENTITY,
    AcceptedWindow,
    PaperObservationFacts,
    TaskSchedulerSnapshot,
    V535CycleConfig,
    V535CycleError,
    _canonical_hash,
    run_v535_unattended_cycle,
)
from algotrader.orchestration.crypto_tournament_v2_oos_scheduler import (
    PreviewDispatcher,
    RealCommandDispatcher,
)


KEY_SENTINEL = "V535_CYCLE_KEY_SENTINEL"
SECRET_SENTINEL = "V535_CYCLE_SECRET_SENTINEL"
ACCOUNT_SENTINEL = "V535_CYCLE_ACCOUNT_SENTINEL"
MARKET_REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-market-data/offline-cycle"
)
PAPER_REFERENCE = CredentialReference(
    "wincred:algotrader/v5.35/alpaca-paper-observation/offline-cycle"
)
SAFETY_FIELDS = (
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_submit_authorized",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_authorized",
    "live_endpoint_touched",
)


class FakeProvider:
    provider_name = "windows-credential-manager"

    def __init__(self, failure: str | None = None) -> None:
        self.failure = failure
        self.validate_count = 0
        self.open_count = 0
        self._lock = Lock()

    def _record(self, family: CredentialFamily) -> dict[str, object]:
        record: dict[str, object] = {
            "schema_version": CREDENTIAL_RECORD_SCHEMA,
            "family": family.value,
            "api_key_id": KEY_SENTINEL,
            "api_secret_key": SECRET_SENTINEL,
        }
        if family is CredentialFamily.ALPACA_PAPER_OBSERVATION:
            record["expected_account_id"] = ACCOUNT_SENTINEL
        return record

    def _open(
        self,
        reference: CredentialReference,
        family: CredentialFamily | str,
    ):
        family = CredentialFamily(family)
        if self.failure:
            raise CredentialProviderError(self.failure)
        return lease_from_test_record(
            self._record(family),
            reference=reference,
            expected_family=family,
        )

    def validate(
        self,
        reference: CredentialReference,
        *,
        expected_family: CredentialFamily | str,
    ) -> None:
        with self._lock:
            self.validate_count += 1
        self._open(reference, expected_family).use(lambda *_: None)

    def open(
        self,
        reference: CredentialReference,
        *,
        expected_family: CredentialFamily | str,
    ):
        with self._lock:
            self.open_count += 1
        return self._open(reference, expected_family)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class FakePaperHttp:
    def __init__(self, *, flat: bool = True) -> None:
        self.flat = flat
        self.call_count = 0
        self._lock = Lock()

    def observe(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        expected_account_id: str,
        paper_endpoint: str,
        clock,
    ) -> PaperObservationFacts:
        assert api_key_id == KEY_SENTINEL
        assert api_secret_key == SECRET_SENTINEL
        assert expected_account_id == ACCOUNT_SENTINEL
        assert paper_endpoint == "https://paper-api.alpaca.markets"
        with self._lock:
            self.call_count += 1
        return PaperObservationFacts(
            observed_at=clock(),
            account_match=True,
            account_active=True,
            account_flat_reconciled=self.flat,
            position_count=0 if self.flat else 1,
            open_order_count=0,
            target_asset_valid=True,
            account_read_count=1,
            positions_read_count=1,
            orders_read_count=1,
            asset_read_count=1,
        )


class FakeProcessRunner:
    def __init__(self, *, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.call_count = 0
        self.calls: list[dict[str, object]] = []
        self._lock = Lock()

    def __call__(self, argv: list[str], **kwargs: object) -> object:
        with self._lock:
            self.call_count += 1
            self.calls.append({"argv": list(argv), "env": dict(kwargs["env"])})  # type: ignore[arg-type]
        if self.exit_code:
            return SimpleNamespace(
                returncode=self.exit_code,
                stdout=f"stdout:{SECRET_SENTINEL}",
                stderr=f"stderr:{KEY_SENTINEL}",
            )
        output_root = Path(argv[argv.index("--output-root") + 1])
        as_of = argv[argv.index("--as-of") + 1]
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "operating_packet.json").write_text(
            json.dumps({"as_of": as_of}, sort_keys=True),
            encoding="utf-8",
        )
        (output_root / "frozen_state.json").write_text(
            json.dumps({"updated_at": as_of}, sort_keys=True),
            encoding="utf-8",
        )
        output = {
            "market_data_fetch_occurred": True,
            "network_access_attempted": True,
            **{field: False for field in SAFETY_FIELDS},
        }
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(output, sort_keys=True),
            stderr=f"discarded:{SECRET_SENTINEL}",
        )


def _window(index: int = 0) -> AcceptedWindow:
    start = datetime(2026, 7, 20, 0, tzinfo=UTC) + timedelta(hours=index)
    return AcceptedWindow(start, start, start + timedelta(hours=1))


def _task_snapshot(window: AcceptedWindow) -> TaskSchedulerSnapshot:
    observed = window.provider_as_of_boundary + timedelta(minutes=5)
    return TaskSchedulerSnapshot(
        task_identity=V535_TASK_IDENTITY,
        enabled=True,
        state="Ready",
        action_execute=V535_TASK_EXECUTE,
        action_arguments=V535_TASK_ARGUMENTS,
        last_task_result=0,
        last_run_time=observed,
        observed_at=observed,
    )


def _source_provenance() -> dict[str, object]:
    manifest = {
        "src/algotrader/execution/v535_unattended_readonly.py": "1" * 64,
        "src/algotrader/execution/v535_burn_in_status.py": "2" * 64,
    }
    digest = hashlib.sha256()
    for path, file_hash in sorted(manifest.items()):
        digest.update(f"{path}:{file_hash}\n".encode("utf-8"))
    return {
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "source_worktree_clean": True,
        "source_branch_or_detached": "codex/v5.35-secure-unattended-readonly",
        "adapter_source_bundle_sha256": digest.hexdigest(),
        "source_bundle_manifest": manifest,
    }


def _config(tmp_path: Path) -> V535CycleConfig:
    root = tmp_path / "v535"
    return V535CycleConfig(
        output_root=root,
        admission_db_path=root / "admission.sqlite3",
        market_data_credential_reference=MARKET_REFERENCE,
        paper_credential_reference=PAPER_REFERENCE,
        scheduler_enabled=True,
        market_data_read_authorized=True,
        paper_broker_read_authorized=True,
        allow_network=True,
    )


def _dispatcher(provider: FakeProvider, runner: FakeProcessRunner) -> RealCommandDispatcher:
    return RealCommandDispatcher(
        scheduler_enabled=True,
        market_data_read_authorized=True,
        credential_reference=MARKET_REFERENCE,
        credential_provider=provider,
        process_runner=runner,
    )


def _run_cycle(
    *,
    config: V535CycleConfig,
    window: AcceptedWindow,
    provider: FakeProvider,
    runner: FakeProcessRunner,
    paper: FakePaperHttp,
    clock: FixedClock,
    dispatcher: RealCommandDispatcher | None = None,
    task_snapshot: TaskSchedulerSnapshot | None = None,
) -> dict[str, object]:
    return run_v535_unattended_cycle(
        config=config,
        accepted_window=window,
        dispatcher=dispatcher or _dispatcher(provider, runner),
        credential_provider=provider,
        task_scheduler_reader=lambda: task_snapshot or _task_snapshot(window),
        paper_http_boundary=paper,
        source_provenance_reader=_source_provenance,
        clock=clock,
    )


@pytest.mark.parametrize(
    "classification",
    (
        "credential_provider_unavailable",
        "credential_record_malformed",
        "credential_family_mismatch",
        "credential_provider_denied",
    ),
)
def test_credential_failure_precedes_all_state_and_external_boundaries(
    tmp_path: Path,
    classification: str,
) -> None:
    config = _config(tmp_path)
    provider = FakeProvider(failure=classification)
    runner = FakeProcessRunner()
    paper = FakePaperHttp()
    task_calls: list[object] = []
    source_calls: list[object] = []

    with pytest.raises(V535CycleError, match=classification):
        run_v535_unattended_cycle(
            config=config,
            accepted_window=_window(),
            dispatcher=_dispatcher(provider, runner),
            credential_provider=provider,
            task_scheduler_reader=lambda: task_calls.append(True),  # type: ignore[arg-type,return-value]
            paper_http_boundary=paper,
            source_provenance_reader=lambda: source_calls.append(True),  # type: ignore[arg-type,return-value]
            clock=FixedClock(datetime(2026, 7, 20, 1, 5, tzinfo=UTC)),
        )
    assert runner.call_count == 0
    assert paper.call_count == 0
    assert task_calls == []
    assert source_calls == []
    assert not config.output_root.exists()


def test_preview_dispatcher_is_rejected_before_provider_or_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    provider = FakeProvider()
    with pytest.raises(V535CycleError, match="real_command_dispatcher_required"):
        run_v535_unattended_cycle(
            config=config,
            accepted_window=_window(),
            dispatcher=PreviewDispatcher(),  # type: ignore[arg-type]
            credential_provider=provider,
            task_scheduler_reader=lambda: _task_snapshot(_window()),
            paper_http_boundary=FakePaperHttp(),
            source_provenance_reader=_source_provenance,
            clock=FixedClock(datetime(2026, 7, 20, 1, 5, tzinfo=UTC)),
        )
    assert provider.validate_count == 0
    assert not config.output_root.exists()


def test_environment_credential_alias_is_rejected_before_provider_or_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    provider = FakeProvider()
    runner = FakeProcessRunner()
    monkeypatch.setenv("ALPACA_API_KEY", KEY_SENTINEL)
    with pytest.raises(
        V535CycleError,
        match="credential_environment_alias_rejected",
    ):
        _run_cycle(
            config=config,
            window=_window(),
            provider=provider,
            runner=runner,
            paper=FakePaperHttp(),
            clock=FixedClock(datetime(2026, 7, 20, 1, 5, tzinfo=UTC)),
        )
    assert provider.validate_count == 0
    assert runner.call_count == 0
    assert not config.output_root.exists()


def test_completed_cycle_is_cross_hashed_secret_free_and_real_dispatched(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = _config(tmp_path)
    window = _window()
    clock = FixedClock(window.provider_as_of_boundary + timedelta(minutes=5))
    provider = FakeProvider()
    runner = FakeProcessRunner()
    paper = FakePaperHttp()

    receipt = _run_cycle(
        config=config,
        window=window,
        provider=provider,
        runner=runner,
        paper=paper,
        clock=clock,
    )
    assert receipt["classification"] == "completed_read_only_cycle"
    assert receipt["production_dispatcher"] == "RealCommandDispatcher"
    assert runner.call_count == 1
    assert paper.call_count == 1
    assert all(receipt[field] is False for field in SAFETY_FIELDS)
    cycle_path = next((config.output_root / "cycles").glob("cycle_*.json"))
    validation = validate_completed_cycle_evidence(
        cycle_path,
        output_root=config.output_root,
    )
    assert validation.valid, validation.errors
    assert set(validation.roles) == {
        "source",
        "scheduler",
        "market_data",
        "broker",
        "readiness",
        "decision",
    }
    assert validation.roles["market_data"]["dispatch_type"] == "real"

    captured = capsys.readouterr()
    all_output = captured.out + captured.err
    persisted = b"".join(
        path.read_bytes()
        for path in config.output_root.rglob("*")
        if path.is_file()
    )
    for sentinel in (KEY_SENTINEL, SECRET_SENTINEL, ACCOUNT_SENTINEL):
        assert sentinel not in all_output
        assert sentinel.encode("utf-8") not in persisted
        assert sentinel not in json.dumps(receipt, sort_keys=True)
        assert sentinel not in json.dumps(runner.calls, sort_keys=True)
    assert not list(config.output_root.rglob("*.tmp"))
    assert not any(
        name.startswith(("ALPACA_", "APCA_"))
        for name in runner.calls[0]["env"]  # type: ignore[union-attr]
    )


def test_child_failure_output_is_discarded_and_secret_free(tmp_path: Path) -> None:
    config = _config(tmp_path)
    window = _window()
    runner = FakeProcessRunner(exit_code=7)
    receipt = _run_cycle(
        config=config,
        window=window,
        provider=FakeProvider(),
        runner=runner,
        paper=FakePaperHttp(),
        clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
    )
    assert receipt["classification"] == "blocked_market_dispatch_failed"
    persisted = b"".join(
        path.read_bytes()
        for path in config.output_root.rglob("*")
        if path.is_file()
    )
    assert KEY_SENTINEL.encode() not in persisted
    assert SECRET_SENTINEL.encode() not in persisted


def test_concurrent_same_window_has_one_owner_and_immutable_duplicate_noops(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    window = _window()
    provider = FakeProvider()
    runner = FakeProcessRunner()
    paper = FakePaperHttp()
    clock = FixedClock(window.provider_as_of_boundary + timedelta(minutes=5))
    dispatcher = _dispatcher(provider, runner)

    def invoke(_: int) -> dict[str, object]:
        return _run_cycle(
            config=config,
            window=window,
            provider=provider,
            runner=runner,
            paper=paper,
            clock=clock,
            dispatcher=dispatcher,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(invoke, range(12)))

    completed = [
        receipt
        for receipt in receipts
        if receipt["classification"] == "completed_read_only_cycle"
    ]
    duplicates = [
        receipt
        for receipt in receipts
        if receipt["classification"] == "duplicate_window_no_op"
    ]
    assert len(completed) == 1
    assert len(duplicates) == 11
    assert runner.call_count == 1
    assert paper.call_count == 1
    assert len(list((config.output_root / "duplicates").glob("duplicate_*.json"))) == 11
    assert len({receipt["invocation_id"] for receipt in duplicates}) == 11
    assert all(receipt["subprocess_created"] is False for receipt in duplicates)
    assert all(receipt["network_access_attempted"] is False for receipt in duplicates)


@pytest.mark.parametrize(
    "role",
    ("source", "scheduler", "market_data", "broker", "readiness", "decision"),
)
def test_missing_mandatory_role_binding_fails_closed(
    tmp_path: Path,
    role: str,
) -> None:
    config = _config(tmp_path)
    window = _window()
    receipt = _run_cycle(
        config=config,
        window=window,
        provider=FakeProvider(),
        runner=FakeProcessRunner(),
        paper=FakePaperHttp(),
        clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
    )
    cycle_path = next((config.output_root / "cycles").glob("cycle_*.json"))
    receipt["evidence_references"].pop(role)  # type: ignore[union-attr]
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    cycle_path.write_text(json.dumps(receipt), encoding="utf-8")
    validation = validate_completed_cycle_evidence(cycle_path, output_root=config.output_root)
    assert not validation.valid
    assert "cycle_evidence_references_malformed" in validation.errors


def test_cross_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    config = _config(tmp_path)
    window = _window()
    receipt = _run_cycle(
        config=config,
        window=window,
        provider=FakeProvider(),
        runner=FakeProcessRunner(),
        paper=FakePaperHttp(),
        clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
    )
    scheduler_ref = receipt["evidence_references"]["scheduler"]  # type: ignore[index]
    scheduler_path = config.output_root / scheduler_ref["path"]
    scheduler = json.loads(scheduler_path.read_text(encoding="utf-8"))
    scheduler["source_receipt_sha256"] = "f" * 64
    scheduler["canonical_receipt_sha256"] = _canonical_hash(scheduler)
    new_path = scheduler_path.with_name(
        f"scheduler_{scheduler['canonical_receipt_sha256']}.json"
    )
    new_path.write_text(json.dumps(scheduler), encoding="utf-8")
    scheduler_ref["path"] = new_path.relative_to(config.output_root).as_posix()
    scheduler_ref["sha256"] = scheduler["canonical_receipt_sha256"]
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    cycle_path = next((config.output_root / "cycles").glob("cycle_*.json"))
    cycle_path.write_text(json.dumps(receipt), encoding="utf-8")

    validation = validate_completed_cycle_evidence(cycle_path, output_root=config.output_root)
    assert not validation.valid
    assert "scheduler_source_receipt_sha256_mismatch" in validation.errors


@pytest.mark.parametrize(
    ("role", "field", "value", "expected_error"),
    (
        ("scheduler", "task_action_arguments", "wrong", "scheduler_task_action_mismatch"),
        ("market_data", "accepted_window", "wrong", "market_data_accepted_window_mismatch"),
        ("broker", "account_flat_reconciled", False, "broker_account_non_flat"),
        ("readiness", "blockers", ["failed"], "readiness_blocked"),
        ("decision", "decision", "submit", "decision_mismatch"),
    ),
)
def test_malformed_or_mismatched_role_evidence_fails_closed(
    tmp_path: Path,
    role: str,
    field: str,
    value: object,
    expected_error: str,
) -> None:
    config = _config(tmp_path)
    window = _window()
    receipt = _run_cycle(
        config=config,
        window=window,
        provider=FakeProvider(),
        runner=FakeProcessRunner(),
        paper=FakePaperHttp(),
        clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
    )
    reference = receipt["evidence_references"][role]  # type: ignore[index]
    role_path = config.output_root / reference["path"]
    role_receipt = json.loads(role_path.read_text(encoding="utf-8"))
    role_receipt[field] = value
    role_receipt["canonical_receipt_sha256"] = _canonical_hash(role_receipt)
    new_path = role_path.with_name(
        f"{role}_{role_receipt['canonical_receipt_sha256']}.json"
    )
    new_path.write_text(json.dumps(role_receipt), encoding="utf-8")
    reference["path"] = new_path.relative_to(config.output_root).as_posix()
    reference["sha256"] = role_receipt["canonical_receipt_sha256"]
    receipt["canonical_receipt_sha256"] = _canonical_hash(receipt)
    cycle_path = next((config.output_root / "cycles").glob("cycle_*.json"))
    cycle_path.write_text(json.dumps(receipt), encoding="utf-8")

    validation = validate_completed_cycle_evidence(cycle_path, output_root=config.output_root)
    assert not validation.valid
    assert expected_error in validation.errors


def test_real_production_control_flow_completes_24_cycles_across_restart(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    windows = tuple(_window(index) for index in range(24))
    first_provider = FakeProvider()
    first_runner = FakeProcessRunner()
    first_paper = FakePaperHttp()
    clock = FixedClock(windows[0].provider_as_of_boundary + timedelta(minutes=5))

    for window in windows[:12]:
        clock.now = window.provider_as_of_boundary + timedelta(minutes=5)
        receipt = _run_cycle(
            config=config,
            window=window,
            provider=first_provider,
            runner=first_runner,
            paper=first_paper,
            clock=clock,
        )
        assert receipt["classification"] == "completed_read_only_cycle"

    # Reconstruct every runtime dependency while preserving only durable state.
    second_provider = FakeProvider()
    second_runner = FakeProcessRunner()
    second_paper = FakePaperHttp()
    for window in windows[12:]:
        clock.now = window.provider_as_of_boundary + timedelta(minutes=5)
        receipt = _run_cycle(
            config=replace(
                config,
                output_root=Path(config.output_root),
                admission_db_path=Path(config.admission_db_path),
            ),
            window=window,
            provider=second_provider,
            runner=second_runner,
            paper=second_paper,
            clock=clock,
        )
        assert receipt["classification"] == "completed_read_only_cycle"

    assert first_runner.call_count == 12
    assert second_runner.call_count == 12
    cycle_paths = sorted((config.output_root / "cycles").glob("cycle_*.json"))
    assert len(cycle_paths) == 24
    assert all(
        validate_completed_cycle_evidence(
            path,
            output_root=config.output_root,
        ).valid
        for path in cycle_paths
    )
    latest_task = _task_snapshot(windows[-1])
    status = build_v535_burn_in_status(
        output_root=config.output_root,
        expected_windows=windows,
        task_snapshot=latest_task,
        as_of=latest_task.observed_at,
    )
    assert status["burn_in_status"] == "complete"
    assert status["valid_target_cycle_count"] == 24
    assert status["blockers"] == []
    assert status["account_flat_reconciled"] is True
    assert all(status[field] is False for field in SAFETY_FIELDS)


def test_burn_in_active_requires_every_declared_target_window(tmp_path: Path) -> None:
    config = _config(tmp_path)
    windows = tuple(_window(index) for index in range(3))
    for window in windows:
        _run_cycle(
            config=config,
            window=window,
            provider=FakeProvider(),
            runner=FakeProcessRunner(),
            paper=FakePaperHttp(),
            clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
        )
    task = _task_snapshot(windows[-1])
    active = build_v535_burn_in_status(
        output_root=config.output_root,
        expected_windows=windows,
        task_snapshot=task,
        as_of=task.observed_at,
        write_packet=False,
    )
    assert active["burn_in_status"] == "active"

    missing = build_v535_burn_in_status(
        output_root=config.output_root,
        expected_windows=windows + (_window(3),),
        task_snapshot=_task_snapshot(_window(3)),
        as_of=_window(3).provider_as_of_boundary + timedelta(minutes=5),
        write_packet=False,
    )
    assert missing["burn_in_status"] == "blocked"
    assert "target_window_evidence_missing" in missing["blockers"]


@pytest.mark.parametrize(
    ("task_change", "as_of_delta", "expected_blocker"),
    (
        ({"action_arguments": "wrong"}, timedelta(minutes=5), "scheduled_task_action_mismatch"),
        ({"last_task_result": 1}, timedelta(minutes=5), "scheduled_task_result_failed"),
        ({"enabled": False, "state": "Disabled"}, timedelta(minutes=5), "scheduled_task_disabled_or_failed"),
        ({}, timedelta(hours=3), "frontier_lag_out_of_bounds"),
    ),
)
def test_burn_in_task_failure_or_stale_frontier_blocks(
    tmp_path: Path,
    task_change: dict[str, object],
    as_of_delta: timedelta,
    expected_blocker: str,
) -> None:
    config = _config(tmp_path)
    window = _window()
    _run_cycle(
        config=config,
        window=window,
        provider=FakeProvider(),
        runner=FakeProcessRunner(),
        paper=FakePaperHttp(),
        clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
    )
    task = replace(_task_snapshot(window), **task_change)
    status = build_v535_burn_in_status(
        output_root=config.output_root,
        expected_windows=(window,),
        task_snapshot=task,
        as_of=window.provider_as_of_boundary + as_of_delta,
        write_packet=False,
    )
    assert status["burn_in_status"] == "blocked"
    assert expected_blocker in status["blockers"]


def test_non_flat_cycle_is_blocked_and_prevents_active_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    window = _window()
    receipt = _run_cycle(
        config=config,
        window=window,
        provider=FakeProvider(),
        runner=FakeProcessRunner(),
        paper=FakePaperHttp(flat=False),
        clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
    )
    assert receipt["classification"] == "blocked_broker_account_non_flat"
    task = _task_snapshot(window)
    status = build_v535_burn_in_status(
        output_root=config.output_root,
        expected_windows=(window,),
        task_snapshot=task,
        as_of=task.observed_at,
        write_packet=False,
    )
    assert status["burn_in_status"] == "blocked"
    assert "blocked_cycle_evidence_present" in status["blockers"]


def test_non_contiguous_target_windows_cannot_be_active(tmp_path: Path) -> None:
    config = _config(tmp_path)
    windows = (_window(0), _window(2))
    for window in windows:
        _run_cycle(
            config=config,
            window=window,
            provider=FakeProvider(),
            runner=FakeProcessRunner(),
            paper=FakePaperHttp(),
            clock=FixedClock(window.provider_as_of_boundary + timedelta(minutes=5)),
        )
    task = _task_snapshot(windows[-1])
    status = build_v535_burn_in_status(
        output_root=config.output_root,
        expected_windows=windows,
        task_snapshot=task,
        as_of=task.observed_at,
        write_packet=False,
    )
    assert status["burn_in_status"] == "blocked"
    assert "target_windows_non_contiguous" in status["blockers"]
